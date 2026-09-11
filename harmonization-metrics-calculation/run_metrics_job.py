"""
run_metrics_job.py — Worker: compute comprehensive metrics for one expression file.

Reads from S3:
    exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz   — harmonized expression
    exp/{strat}__{imp}__01_raw__post0.tsv.gz          — reference, Group L only
    prepared/{strat}__{imp}__ann.tsv.gz               — annotation

Writes to S3:
    metrics/{strat}__{imp}__{method}__post{0|1}_metrics.json
    genes/{strat}__{imp}__{method}__post{0|1}_genes.json
    marker_corr/{strat}__{imp}__{method}__post{0|1}_gene_cohort.json
        — only with --save-gene-cohort-detail

Usage
-----
python run_metrics_job.py \\
    --strat  A_confirmed_bad \\
    --imp    strict \\
    --method 16_fsqn_r \\
    --post-rm False \\
    --out-json /tmp/metrics.json \\
    --out-genes-json /tmp/genes.json \\
    [--skip-if-exists] \\
    [--skip-slow] \\
    [--memory-limit-gb 4.0]

# Blind final check only (groups L, M, N), reusing the cached raw reference:
python run_metrics_job.py \\
    --strat C_rnaseq_only --imp softimpute --method 04_sva --post-rm False \\
    --out-json /tmp/metrics.json --out-genes-json /tmp/genes.json \\
    --groups L,M,N --ref-cache-dir /workspace/ref_cache

# Force-recompute Group N only with a higher n_perm, even though a sidecar with a
# Group N result already exists on S3 — Groups A-M are left untouched:
python run_metrics_job.py \\
    --strat C_rnaseq_only --imp softimpute --method 04_sva --post-rm False \\
    --out-json /tmp/metrics.json --out-genes-json /tmp/genes.json \\
    --groups N --force-groups N --n-perm 200

# Add the Group L `_narrow_set` aggregates to a sidecar that already has Group L. No
# --force-groups is needed: Group L's second sentinel key is missing, so the incremental
# check schedules it on its own.
python run_metrics_job.py \\
    --strat C_rnaseq_only --imp softimpute --method 04_sva --post-rm False \\
    --out-json /tmp/metrics.json --out-genes-json /tmp/genes.json \\
    --groups L --skip-wm True --ref-cache-dir /workspace/ref_cache
"""

from __future__ import annotations

import os

# Must run before numpy/scipy/scikit-learn are imported (directly, or transitively via
# pandas / compute_batch_metrics below) — BLAS and OpenMP read these once at library load
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
import uuid
from pathlib import Path

import boto3
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from compute_batch_metrics import (
    N_PERM,
    S3_BUCKET,
    S3_PREFIX,
    compute_all_metrics,
    dict_to_json_safe,
)
from marker_panels import panel_genes

# ── Incremental computation ────────────────────────────────────────────────────

# One sentinel key per group, or a tuple when a group has gained a new metric family: a
# group counts as complete only when EVERY listed key is populated. Listing the new key
# is what makes every already-finished sidecar resume that group automatically on the
# next run — no --force-groups, and no way to end up with a half-populated group.
GROUP_SENTINEL_KEYS: dict[str, str | tuple[str, ...]] = {
    "E": "n_samples",
    "A": "r2_RNA_BATCH",
    "B": "kbet_acceptance_rate_RNA_BATCH",
    "C": "umap_centroid_disp_RNA_BATCH",
    "D": "ks_mean_D_RNA_BATCH",
    "F": "vp_median_RNA_BATCH",
    "G": "graph_connectivity_Major_group",
    "H": "dist_ratio_RNA_BATCH",
    "I": "wm_RNA_BATCH",
    "J": "pct_var_pc1",
    "K": "n_genes_noNA",
    "L": ("mk_rho_mean_all_genes", "mk_rho_mean_all_genes_narrow_set"),
    "M": "xb_rank_agree",
    "N": "pv_lobo3_f1_macro_mean",
}

# Only Group L compares against a second matrix, so the reference download is
# skipped entirely for any run that does not request it.
GROUPS_NEEDING_REFERENCE: set[str] = {"L"}


def _load_prior_metrics(
    s3_client: object, strat: str, imp: str, method: str, post_rm: bool
) -> dict | None:
    key = _s3_key_metrics_json(strat, imp, method, post_rm)
    try:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)  # type: ignore[attr-defined]
        data = json.loads(obj["Body"].read())
        if data.get("status") != "ok":
            return None
        return data
    except Exception:
        return None


def _groups_to_recompute(
    prior: dict | None,
    requested_groups: set[str],
    force_groups: set[str] = frozenset(),
) -> set[str]:
    if prior is None:
        return set(requested_groups)
    missing: set[str] = set()
    for g in requested_groups:
        if g in force_groups:
            missing.add(g)
            continue
        sentinel = GROUP_SENTINEL_KEYS.get(g)
        if sentinel is None:
            missing.add(g)
            continue
        keys = (sentinel,) if isinstance(sentinel, str) else sentinel
        if any(prior.get(k) is None for k in keys):
            missing.add(g)
    return missing


# ── S3 helpers ────────────────────────────────────────────────────────────────


def _s3_key_exp(strat: str, imp: str, method: str, post_rm: bool) -> str:
    pm = "0" if not post_rm else "1"
    return f"{S3_PREFIX}/exp/{strat}__{imp}__{method}__post{pm}.tsv.gz"


def _s3_key_ref_exp(strat: str, imp: str) -> str:
    """
    S3 key of the unharmonized reference for Group L.

    Always the post-removal-off 01_raw matrix. 01_raw__post1 would be wrong: post
    removal drops outlier batches identified on the harmonized matrix, so its removed
    batches differ per method and the two sample sets would not line up. Intersecting
    01_raw__post0 down to the job's own index gives an exact sample match instead.
    """
    return f"{S3_PREFIX}/exp/{strat}__{imp}__01_raw__post0.tsv.gz"


def _s3_key_prepared_ann(strat: str, imp: str) -> str:
    return f"{S3_PREFIX}/prepared/{strat}__{imp}__ann.tsv.gz"


def _s3_key_metrics_json(strat: str, imp: str, method: str, post_rm: bool) -> str:
    pm = "0" if not post_rm else "1"
    return f"{S3_PREFIX}/metrics/{strat}__{imp}__{method}__post{pm}_metrics.json"


def _s3_key_genes_json(strat: str, imp: str, method: str, post_rm: bool) -> str:
    pm = "0" if not post_rm else "1"
    return f"{S3_PREFIX}/genes/{strat}__{imp}__{method}__post{pm}_genes.json"


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


def _load_reference_cached(
    s3_client: object, strat: str, imp: str, cache_dir: str, label: str
) -> pd.DataFrame:
    """
    Load the 01_raw reference matrix, caching it on local disk per (strat, imp).

    There are 42 distinct (strat, imp) pairs but thousands of jobs, so downloading the
    ~300 MB reference once per pair instead of once per job is the single largest
    saving in the run. The ETag is logged on every hit so a cache left stale by a
    regenerated 01_raw output shows up in the log rather than silently changing the
    comparison.

    Parameters
    ----------
    s3_client : boto3 S3 client
    strat, imp : str
    cache_dir : str
        Directory on a persistent volume; created if absent.
    label : str
        Job label for log lines.

    Returns
    -------
    pd.DataFrame
        Reference expression matrix (samples x genes).
    """
    key = _s3_key_ref_exp(strat, imp)
    cache_path = Path(cache_dir) / f"{strat}__{imp}__01_raw__post0.tsv.gz"
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        etag = s3_client.head_object(Bucket=S3_BUCKET, Key=key)["ETag"]  # type: ignore[attr-defined]
    except Exception:
        etag = "unknown"

    if cache_path.exists():
        print(
            f"[{_ts()}][{label}] Reference cache hit: {cache_path.name} (S3 ETag {etag})",
            flush=True,
        )
        return pd.read_csv(cache_path, sep="\t", index_col=0, low_memory=False)

    print(
        f"[{_ts()}][{label}] Reference cache miss — downloading {key} ...", flush=True
    )
    body = gzip.decompress(
        s3_client.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()  # type: ignore[attr-defined]
    )
    # Unique per-process suffix: cache_path is deterministic from (strat, imp), so
    # concurrent cache misses on the same pair must not share one temp filename —
    # os.replace() is atomic and overwrites cleanly, so only the *source* needs to
    # be unique, not the destination.
    tmp_path = cache_path.with_suffix(f".partial.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    with gzip.open(tmp_path, "wb") as fh:
        fh.write(body)
    tmp_path.replace(
        cache_path
    )  # atomic, so concurrent workers never read a partial file
    return pd.read_csv(io.BytesIO(body), sep="\t", index_col=0, low_memory=False)


def _upload_json(s3_client: object, key: str, payload: str) -> None:
    s3_client.put_object(  # type: ignore[attr-defined]
        Bucket=S3_BUCKET,
        Key=key,
        Body=payload.encode(),
        ContentType="application/json",
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
        description="Worker: compute comprehensive batch effect metrics for one expression file."
    )
    parser.add_argument("--strat", required=True)
    parser.add_argument("--imp", required=True)
    parser.add_argument("--method", required=True)
    parser.add_argument("--post-rm", required=True, help="True or False")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-genes-json", required=True)
    parser.add_argument("--memory-limit-gb", type=float, default=4.0)
    parser.add_argument("--skip-if-exists", action="store_true")
    parser.add_argument("--skip-slow", action="store_true")
    parser.add_argument(
        "--skip-wm",
        type=lambda x: x.lower() not in ("false", "0", "no"),
        default=False,
        metavar="BOOL",
        help="Skip WaterMelon score (Group I). Default: False (WM computed). Pass True to skip.",
    )
    parser.add_argument(
        "--groups",
        default=None,
        help="Comma-separated metric groups to compute (e.g. A,B,E). Default: all.",
    )
    parser.add_argument(
        "--force-groups",
        default=None,
        help=(
            "Comma-separated metric groups to recompute even if their sentinel key "
            "already exists in the prior sidecar (e.g. rerun Group N with a new "
            "--n-perm). Automatically added to the requested set if --groups omits "
            "them; every other requested group still uses the normal incremental "
            "skip."
        ),
    )
    parser.add_argument(
        "--ref-cache-dir",
        default="/workspace/ref_cache",
        help="Local cache for the 01_raw reference matrices (Group L only).",
    )
    parser.add_argument(
        "--n-perm",
        type=int,
        default=N_PERM,
        help=f"Label permutations for the Group N control (default: {N_PERM}).",
    )
    parser.add_argument(
        "--save-gene-cohort-detail",
        action="store_true",
        help="Also upload the full Group L gene x cohort matrix to S3.",
    )
    parser.add_argument(
        "--panel-groups",
        default=None,
        help="Comma-separated gene_group filter for Groups L and M. Default: all.",
    )
    args = parser.parse_args()

    post_rm = args.post_rm.lower() in ("true", "1", "yes")
    label = f"{args.strat}×{args.imp}×{args.method}×post_rm={post_rm}"

    s3 = boto3.client("s3")
    metrics_key = _s3_key_metrics_json(args.strat, args.imp, args.method, post_rm)
    genes_key = _s3_key_genes_json(args.strat, args.imp, args.method, post_rm)

    # Fast-path skip (entire job)
    if args.skip_if_exists and _s3_exists(s3, metrics_key):
        print(f"[{_ts()}][{label}] Metrics sidecar already on S3 — cached.", flush=True)
        cached = {"status": "cached"}
        with open(args.out_json, "w") as fh:
            json.dump(cached, fh)
        sys.exit(0)

    # Determine requested groups
    if args.groups:
        requested_groups: set[str] = {g.upper().strip() for g in args.groups.split(",")}
    else:
        requested_groups = set("ABCDEFGHJKLMN")
    if not args.skip_wm:
        requested_groups.add("I")
    if args.skip_slow:
        requested_groups.discard("F")

    # --force-groups letters are always in play, even if --groups was narrower or
    # omitted them entirely; this line runs after the skip_slow/skip_wm adjustments
    # above so an explicit --force-groups F still forces F even under --skip-slow.
    force_groups: set[str] = (
        {g.upper().strip() for g in args.force_groups.split(",")}
        if args.force_groups
        else set()
    )
    requested_groups |= force_groups

    # Incremental: load any prior metrics and skip already-complete groups, except
    # any group named in --force-groups, which is always recomputed regardless of
    # its existing sentinel value.
    prior_metrics = _load_prior_metrics(s3, args.strat, args.imp, args.method, post_rm)
    groups_to_run = _groups_to_recompute(prior_metrics, requested_groups, force_groups)

    wm_status = "enabled" if "I" in requested_groups else "skipped"
    print(
        f"[{_ts()}][{label}] Requested groups: {sorted(requested_groups)} | "
        f"WM: {wm_status} | Force: {sorted(force_groups) or 'none'} | "
        f"Need to compute: {sorted(groups_to_run)}",
        flush=True,
    )

    if not groups_to_run:
        print(
            f"[{_ts()}][{label}] All groups already complete — nothing to do.",
            flush=True,
        )
        cached = {"status": "cached"}
        with open(args.out_json, "w") as fh:
            json.dump(cached, fh)
        sys.exit(0)

    if prior_metrics:
        print(
            f"[{_ts()}][{label}] Incremental: reusing {len(prior_metrics)} existing keys from S3.",
            flush=True,
        )

    _check_memory(args.memory_limit_gb, label=f"{label} startup")

    # Locate source expression file
    exp_key = _s3_key_exp(args.strat, args.imp, args.method, post_rm)
    if not _s3_exists(s3, exp_key):
        print(
            f"[{_ts()}][{label}] Expression file not found on S3: {exp_key}",
            file=sys.stderr,
        )
        sys.exit(3)

    ann_key = _s3_key_prepared_ann(args.strat, args.imp)
    if not _s3_exists(s3, ann_key):
        print(
            f"[{_ts()}][{label}] Annotation file not found on S3: {ann_key}",
            file=sys.stderr,
        )
        sys.exit(3)

    needs_reference = bool(GROUPS_NEEDING_REFERENCE & groups_to_run)
    ref_key = _s3_key_ref_exp(args.strat, args.imp)
    if needs_reference and not _s3_exists(s3, ref_key):
        print(
            f"[{_ts()}][{label}] Raw reference not found on S3: {ref_key}",
            file=sys.stderr,
        )
        sys.exit(3)

    # Download data
    print(f"[{_ts()}][{label}] Downloading expression ({exp_key}) ...", flush=True)
    t_dl = time.time()
    try:
        exp_df = _download_df(s3, exp_key)
        ann_df = _download_df(s3, ann_key)
    except Exception:
        print(
            f"[{_ts()}][{label}] Download failed:\n{traceback.format_exc()}", flush=True
        )
        err = {"status": "failed", "error": traceback.format_exc()}
        with open(args.out_json, "w") as fh:
            json.dump(err, fh)
        sys.exit(1)

    print(
        f"[{_ts()}][{label}] Downloaded ({time.time()-t_dl:.0f}s): "
        f"{exp_df.shape[0]} samples × {exp_df.shape[1]} genes",
        flush=True,
    )

    _check_memory(args.memory_limit_gb / 2, label=f"{label} post-download")

    # Align annotation to expression by index intersection
    common = exp_df.index.intersection(ann_df.index)
    exp_df = exp_df.loc[common]
    ann_df = ann_df.loc[common]
    assert len(exp_df) == len(ann_df), "Index alignment failed"
    print(f"[{_ts()}][{label}] Aligned: {len(exp_df)} samples", flush=True)

    # Group L reference. Intersecting it with the already aligned index is what
    # restricts a post_rm=True job to the samples that survived post-removal.
    ref_df: pd.DataFrame | None = None
    if needs_reference:
        try:
            ref_raw = _load_reference_cached(
                s3, args.strat, args.imp, args.ref_cache_dir, label
            )
            shared = exp_df.index.intersection(ref_raw.index)
            exp_df = exp_df.loc[shared]
            ann_df = ann_df.loc[shared]
            ref_df = ref_raw.loc[shared]
            del ref_raw
            assert (
                len(exp_df) == len(ref_df) == len(ann_df)
            ), "Reference alignment failed"
            print(
                f"[{_ts()}][{label}] Reference aligned: {len(ref_df)} samples "
                f"x {ref_df.shape[1]} genes",
                flush=True,
            )
        except Exception:
            print(
                f"[{_ts()}][{label}] Reference load failed, Group L will be skipped:\n"
                f"{traceback.format_exc()}",
                flush=True,
            )
            ref_df = None

    panel = (
        panel_genes(group=args.panel_groups.split(","), include_housekeeping=True)
        if args.panel_groups
        else None
    )

    # Write gene list to S3
    genes_payload = json.dumps(sorted(exp_df.columns.tolist()))
    try:
        _upload_json(s3, genes_key, genes_payload)
        print(
            f"[{_ts()}][{label}] Gene list uploaded ({exp_df.shape[1]} genes).",
            flush=True,
        )
    except Exception:
        print(
            f"[{_ts()}][{label}] Gene list upload failed:\n{traceback.format_exc()}",
            flush=True,
        )
    with open(args.out_genes_json, "w") as fh:
        fh.write(genes_payload)

    # Compute metrics for the required groups only
    def _upload_partial(partial: dict) -> None:
        merged: dict = dict(prior_metrics) if prior_metrics else {}
        merged.update(partial)
        merged["strat"] = args.strat
        merged["imp"] = args.imp
        merged["method"] = args.method
        merged["post_rm"] = post_rm
        merged["status"] = "ok"
        _upload_json(s3, metrics_key, dict_to_json_safe(merged))

    t0 = time.time()
    try:
        new_metrics = compute_all_metrics(
            exp_df,
            ann_df,
            skip_slow=args.skip_slow,
            tmp_path=args.out_json,
            groups=groups_to_run,
            ref_df=ref_df,
            n_perm=args.n_perm,
            panel=panel,
            collect_gene_cohort_detail=args.save_gene_cohort_detail,
            on_group_done=_upload_partial,
        )
        status = "ok"
    except Exception:
        tb = traceback.format_exc()
        print(f"[{_ts()}][{label}] compute_all_metrics FAILED:\n{tb}", flush=True)
        new_metrics = {"status": "failed", "error": tb}
        status = "failed"

    compute_time = time.time() - t0

    # The gene x cohort detail goes to its own S3 prefix, never into the metrics
    # sidecar, so metrics_comprehensive.csv stays a table of scalars.
    detail = new_metrics.pop("mk_gene_cohort_detail", None)
    if detail:
        detail_key = (
            f"{S3_PREFIX}/marker_corr/{args.strat}__{args.imp}__{args.method}"
            f"__post{'1' if post_rm else '0'}_gene_cohort.json"
        )
        try:
            _upload_json(s3, detail_key, dict_to_json_safe(detail))
            print(
                f"[{_ts()}][{label}] Gene x cohort detail uploaded → {detail_key}",
                flush=True,
            )
        except Exception:
            print(
                f"[{_ts()}][{label}] Detail upload failed:\n{traceback.format_exc()}",
                flush=True,
            )

    # Merge with prior metrics (new keys take precedence)
    metrics: dict = dict(prior_metrics) if prior_metrics else {}
    metrics.update(new_metrics)
    metrics["strat"] = args.strat
    metrics["imp"] = args.imp
    metrics["method"] = args.method
    metrics["post_rm"] = post_rm
    metrics["status"] = status
    metrics["compute_time_s"] = round(compute_time, 1)

    # Write final JSON locally
    payload = dict_to_json_safe(metrics)
    with open(args.out_json, "w") as fh:
        fh.write(payload)

    # Upload to S3
    try:
        _upload_json(s3, metrics_key, payload)
        print(
            f"[{_ts()}][{label}] Metrics uploaded ({compute_time:.0f}s) → {metrics_key}",
            flush=True,
        )
    except Exception:
        print(
            f"[{_ts()}][{label}] Metrics upload failed:\n{traceback.format_exc()}",
            flush=True,
        )
        metrics["status"] = "upload_failed"
        with open(args.out_json, "w") as fh:
            fh.write(dict_to_json_safe(metrics))
        sys.exit(1)

    del exp_df, ann_df, ref_df
    gc.collect()
    sys.exit(0)


if __name__ == "__main__":
    main()
