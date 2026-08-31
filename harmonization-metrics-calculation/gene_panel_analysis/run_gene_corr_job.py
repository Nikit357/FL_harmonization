"""
run_gene_corr_job.py — Worker: gene x gene correlation and per-gene QC for one attempt.

Reads from S3:
    exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz   — expression matrix
    prepared/{strat}__{imp}__ann.tsv.gz              — annotation

Writes to S3:
    gene_corr/{strat}__{imp}__{method}__post{0|1}_genecorr.npz
    gene_qc/{strat}__{imp}__{method}__post{0|1}_geneqc.json

No reference matrix is downloaded: unlike metric group L this job describes one
matrix on its own terms. 01_raw is itself an attempt in the benchmark, so the
unharmonized baseline arrives as an ordinary job.

Usage
-----
python run_gene_corr_job.py \\
    --strat  C_rnaseq_only \\
    --imp    softimpute \\
    --method 10_mnn \\
    --post-rm False \\
    --out-npz /tmp/genecorr.npz \\
    --out-qc-json /tmp/geneqc.json \\
    [--skip-if-exists] [--panel-groups ...] [--corr-flavors global,within] \\
    [--memory-limit-gb 6.0]
"""

from __future__ import annotations

import os

# Must run before numpy/scipy/scikit-learn are imported (directly, or transitively via
# pandas / gene_panel_structure below) — BLAS and OpenMP read these once at library load
# time. The k8s manifest also sets these, but this worker is launched from an interactive
# SSH session in practice, which does not inherit the container's declared environment, so
# the manifest's values never reach this process. setdefault() keeps a manual override
# possible without weakening the safety net.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import argparse
import gc
import gzip
import io
import json
import sys
import time
import traceback
from pathlib import Path

import boto3
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from compute_batch_metrics import MIN_COHORT_N, S3_BUCKET, S3_PREFIX, dict_to_json_safe
from gene_panel_structure import (
    LOW_EXPRESSION_THRESHOLD,
    QC_COLUMNS,
    gene_expression_qc,
    gene_gene_correlation,
    gene_gene_correlation_within_cohort,
    pack_upper_triangle,
)
from marker_panels import panel_genes, resolve_panel

ALL_FLAVORS: tuple[str, ...] = ("global", "within")


# ── S3 helpers ────────────────────────────────────────────────────────────────


def _s3_key_exp(strat: str, imp: str, method: str, post_rm: bool) -> str:
    pm = "0" if not post_rm else "1"
    return f"{S3_PREFIX}/exp/{strat}__{imp}__{method}__post{pm}.tsv.gz"


def _s3_key_prepared_ann(strat: str, imp: str) -> str:
    return f"{S3_PREFIX}/prepared/{strat}__{imp}__ann.tsv.gz"


def _s3_key_gene_corr(strat: str, imp: str, method: str, post_rm: bool) -> str:
    pm = "0" if not post_rm else "1"
    return f"{S3_PREFIX}/gene_corr/{strat}__{imp}__{method}__post{pm}_genecorr.npz"


def _s3_key_gene_qc(strat: str, imp: str, method: str, post_rm: bool) -> str:
    pm = "0" if not post_rm else "1"
    return f"{S3_PREFIX}/gene_qc/{strat}__{imp}__{method}__post{pm}_geneqc.json"


def _s3_exists(s3_client: object, key: str) -> bool:
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=key)  # type: ignore[attr-defined]
        return True
    except Exception:
        return False


def _download_df(s3_client: object, key: str, index_col: int = 0) -> pd.DataFrame:
    obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)  # type: ignore[attr-defined]
    body = obj["Body"].read()
    if key.endswith(".gz"):
        body = gzip.decompress(body)
    sep = "\t" if (key.endswith(".tsv") or key.endswith(".tsv.gz")) else ","
    return pd.read_csv(io.BytesIO(body), sep=sep, index_col=index_col, low_memory=False)


def _upload_bytes(
    s3_client: object, key: str, payload: bytes, content_type: str
) -> None:
    s3_client.put_object(  # type: ignore[attr-defined]
        Bucket=S3_BUCKET, Key=key, Body=payload, ContentType=content_type
    )


# ── Memory guard ──────────────────────────────────────────────────────────────


def _free_gb() -> float:
    def _read_int(path: str) -> int | None:
        try:
            val = open(path).read().strip()
            return None if val == "max" else int(val)
        except (OSError, ValueError):
            return None

    limit = _read_int("/sys/fs/cgroup/memory.max") or _read_int(
        "/sys/fs/cgroup/memory/memory.limit_in_bytes"
    )
    usage = _read_int("/sys/fs/cgroup/memory.current") or _read_int(
        "/sys/fs/cgroup/memory/memory.usage_in_bytes"
    )
    if limit is not None and usage is not None:
        return (limit - usage) / 1e9
    try:
        import psutil

        return psutil.virtual_memory().available / 1e9
    except ImportError:
        return 999.0


def _check_memory(min_free_gb: float, label: str = "") -> None:
    free = _free_gb()
    if free < min_free_gb:
        print(
            f"[{label}] Insufficient RAM: {free:.1f} GB free < {min_free_gb:.1f} GB — aborting.",
            file=sys.stderr,
        )
        sys.exit(2)


def _ts() -> str:
    return time.strftime("%H:%M:%S")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Worker: gene x gene correlation and per-gene QC for one attempt."
    )
    parser.add_argument("--strat", required=True)
    parser.add_argument("--imp", required=True)
    parser.add_argument("--method", required=True)
    parser.add_argument("--post-rm", required=True, help="True or False")
    parser.add_argument("--out-npz", required=True)
    parser.add_argument("--out-qc-json", required=True)
    parser.add_argument("--memory-limit-gb", type=float, default=4.0)
    parser.add_argument(
        "--skip-if-exists",
        action="store_true",
        help="Exit immediately if both S3 outputs already exist.",
    )
    parser.add_argument(
        "--corr-flavors",
        default=",".join(ALL_FLAVORS),
        help=f"Comma-separated correlation flavours. Valid: {' '.join(ALL_FLAVORS)}. "
        f"(default: both)",
    )
    parser.add_argument(
        "--panel-groups",
        default=None,
        help="Comma-separated gene_group filter. Default: the whole marker panel.",
    )
    parser.add_argument(
        "--min-cohort-n",
        type=int,
        default=MIN_COHORT_N,
        help=f"Minimum cohort size for the within-cohort statistics "
        f"(default: {MIN_COHORT_N}, the value metric group L uses).",
    )
    parser.add_argument(
        "--low-threshold",
        type=float,
        default=LOW_EXPRESSION_THRESHOLD,
        help="Values strictly below this count towards frac_lt_1, on the log2 scale "
        f"(default: {LOW_EXPRESSION_THRESHOLD}).",
    )
    args = parser.parse_args()

    post_rm = args.post_rm.lower() in ("true", "1", "yes")
    label = f"{args.strat}__{args.imp}__{args.method}__post{'1' if post_rm else '0'}"
    flavors = [f.strip() for f in args.corr_flavors.split(",") if f.strip()]
    unknown = set(flavors) - set(ALL_FLAVORS)
    if unknown:
        print(f"[{label}] Unknown --corr-flavors: {sorted(unknown)}", file=sys.stderr)
        sys.exit(4)

    s3 = boto3.client("s3")
    corr_key = _s3_key_gene_corr(args.strat, args.imp, args.method, post_rm)
    qc_key = _s3_key_gene_qc(args.strat, args.imp, args.method, post_rm)

    if args.skip_if_exists and _s3_exists(s3, corr_key) and _s3_exists(s3, qc_key):
        print(f"[{_ts()}][{label}] Outputs already on S3 — skipping.", flush=True)
        Path(args.out_qc_json).write_text(json.dumps({"status": "cached"}))
        sys.exit(0)

    exp_key = _s3_key_exp(args.strat, args.imp, args.method, post_rm)
    ann_key = _s3_key_prepared_ann(args.strat, args.imp)
    for key in (exp_key, ann_key):
        if not _s3_exists(s3, key):
            print(f"[{_ts()}][{label}] Not found on S3: {key}", file=sys.stderr)
            sys.exit(3)

    _check_memory(args.memory_limit_gb, label)

    print(f"[{_ts()}][{label}] Downloading expression ({exp_key}) ...", flush=True)
    t_dl = time.time()
    try:
        exp_df = _download_df(s3, exp_key)
        ann_df = _download_df(s3, ann_key)
    except Exception:
        print(
            f"[{_ts()}][{label}] Download failed:\n{traceback.format_exc()}", flush=True
        )
        Path(args.out_qc_json).write_text(
            json.dumps({"status": "failed", "error": traceback.format_exc()})
        )
        sys.exit(1)

    ann_df = ann_df.reindex(exp_df.index)
    print(
        f"[{_ts()}][{label}] Downloaded ({time.time()-t_dl:.0f}s): "
        f"{exp_df.shape[0]} samples x {exp_df.shape[1]} genes",
        flush=True,
    )

    full_panel = (
        panel_genes(group=args.panel_groups.split(","), include_housekeeping=True)
        if args.panel_groups
        else panel_genes(include_housekeeping=True)
    )
    # resolve_panel() applies the same alias fallbacks as metric group L, so the gene
    # sets of the two pipelines line up and can be joined gene-by-gene downstream.
    genes, missing = resolve_panel(set(exp_df.columns), full_panel)
    print(
        f"[{_ts()}][{label}] Panel: {len(genes)} resolved, {len(missing)} missing "
        f"of {len(full_panel)}.",
        flush=True,
    )

    if len(genes) < 2:
        print(
            f"[{_ts()}][{label}] Fewer than 2 panel genes present — nothing to do.",
            flush=True,
        )
        Path(args.out_qc_json).write_text(
            json.dumps({"status": "failed", "error": "panel too small"})
        )
        sys.exit(1)

    t0 = time.time()
    arrays: dict[str, np.ndarray] = {"genes": np.array(genes, dtype="<U32")}
    n_cohorts_used = 0

    try:
        if "global" in flavors:
            _check_memory(args.memory_limit_gb, label)
            mat_global, _ = gene_gene_correlation(exp_df, genes)
            arrays["r_global"] = pack_upper_triangle(mat_global)
            del mat_global
            gc.collect()
            print(f"[{_ts()}][{label}] Global correlation done.", flush=True)

        if "within" in flavors:
            _check_memory(args.memory_limit_gb, label)
            mat_within, counts, _ = gene_gene_correlation_within_cohort(
                exp_df, ann_df, genes, min_cohort_n=args.min_cohort_n
            )
            arrays["r_within"] = pack_upper_triangle(mat_within)
            arrays["n_within"] = pack_upper_triangle(counts, dtype=np.uint16)
            n_cohorts_used = int(counts.max()) if counts.size else 0
            del mat_within, counts
            gc.collect()
            print(f"[{_ts()}][{label}] Within-cohort correlation done.", flush=True)

        _check_memory(args.memory_limit_gb, label)
        qc_df = gene_expression_qc(
            exp_df,
            ann_df,
            genes,
            low_threshold=args.low_threshold,
            min_cohort_n=args.min_cohort_n,
        )
        print(
            f"[{_ts()}][{label}] Expression QC done ({len(qc_df)} genes).", flush=True
        )
    except Exception:
        print(
            f"[{_ts()}][{label}] Computation failed:\n{traceback.format_exc()}",
            flush=True,
        )
        Path(args.out_qc_json).write_text(
            json.dumps({"status": "failed", "error": traceback.format_exc()})
        )
        sys.exit(1)

    elapsed = time.time() - t0
    meta = {
        "strat": args.strat,
        "imp": args.imp,
        "method": args.method,
        "post_rm": post_rm,
        "n_samples": int(exp_df.shape[0]),
        "n_genes_matrix": int(exp_df.shape[1]),
        "n_panel_genes_used": len(genes),
        "n_panel_genes_missing": len(missing),
        "n_cohorts_used": n_cohorts_used,
        "min_cohort_n": int(args.min_cohort_n),
        "low_threshold": float(args.low_threshold),
        "flavors": flavors,
        "compute_time_s": round(elapsed, 1),
    }
    arrays["meta"] = np.array(json.dumps(meta))

    # Write the .npz locally first, then upload the same bytes — np.savez_compressed
    # needs a seekable target, which an S3 body is not.
    out_npz = Path(args.out_npz)
    out_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_npz, **arrays)

    qc_payload = dict(meta)
    qc_payload["status"] = "ok"
    qc_payload["genes"] = qc_df[list(QC_COLUMNS)].to_dict(orient="records")
    qc_json = dict_to_json_safe(qc_payload)
    Path(args.out_qc_json).write_text(qc_json)

    try:
        _upload_bytes(s3, corr_key, out_npz.read_bytes(), "application/octet-stream")
        _upload_bytes(s3, qc_key, qc_json.encode(), "application/json")
    except Exception:
        print(
            f"[{_ts()}][{label}] Upload failed:\n{traceback.format_exc()}", flush=True
        )
        sys.exit(1)

    print(
        f"[{_ts()}][{label}] OK in {elapsed:.0f}s — "
        f"{len(genes)} genes, {n_cohorts_used} cohorts, "
        f"npz {out_npz.stat().st_size/1e3:.0f} KB.",
        flush=True,
    )


if __name__ == "__main__":
    main()
