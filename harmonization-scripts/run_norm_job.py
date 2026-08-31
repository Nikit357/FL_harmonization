"""
Stage 2 worker: applies one normalization method to a pre-prepared (strat, imp)
dataset and uploads the results to S3.

Reads from S3:
    prepared/{strat}__{imp}__exp.tsv.gz   — imputed + log-transformed expression
    prepared/{strat}__{imp}__ann.tsv.gz   — filtered annotation

Writes to S3:
    exp/{strat}__{imp}__{method}__post0.tsv.gz
    exp/{strat}__{imp}__{method}__post1.tsv.gz

Usage
-----
python run_norm_job.py \\
    --strat  A_confirmed_bad \\
    --imp    knn \\
    --method 05_combat \\
    [--skip-if-exists] \\
    [--out-json /tmp/norm_jobs/A_confirmed_bad__knn__05_combat.json] \\
    [--memory-limit-gb 2.0]
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
import traceback

import boto3

from bench_shared import (
    BATCH_COL,
    BIO_COL,
    METHODS,
    download_ann_from_s3,
    download_exp_from_s3,
    identify_outlier_batches,
    r2_batch,
    s3_exists,
    s3_key_exp,
    s3_key_prepared_ann,
    s3_key_prepared_exp,
    upload_exp_to_s3,
)


def _free_gb() -> float:
    """Return available RAM in GB, reading container cgroup limit when inside K8s."""
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


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def _check_memory(min_free_gb: float, label: str = "") -> None:
    free = _free_gb()
    if free < min_free_gb:
        print(
            f"[{label}] Insufficient RAM: {free:.1f} GB free < "
            f"{min_free_gb:.1f} GB required — aborting.",
            file=sys.stderr,
        )
        sys.exit(2)


def run_norm(
    strat: str,
    imp: str,
    method_name: str,
    skip_if_exists: bool,
    exp_s,
    ann_s,
) -> list[dict]:
    """
    Normalize a pre-prepared dataset and upload both post_rm variants.

    Parameters
    ----------
    strat, imp, method_name
        Job identifiers.
    skip_if_exists
        Skip S3 keys that already exist.
    exp_s
        Prepared expression matrix (imputed + log-transformed).
    ann_s
        Prepared annotation DataFrame.

    Returns
    -------
    List of 2 metric row dicts (one per post_rm option).
    """
    s3            = boto3.client("s3")
    fn, harshness = METHODS[method_name]
    label = f"{strat}×{imp}×{method_name}"

    print(
        f"[{_ts()}][{label}] Running normalization "
        f"({exp_s.shape[0]} samples × {exp_s.shape[1]} genes) ...",
        flush=True,
    )
    t0_norm = time.time()
    try:
        exp_norm = fn(exp_s, ann_s, batch_col=BATCH_COL, bio_col=BIO_COL)
        print(
            f"[{_ts()}][{label}] Normalization done ({time.time() - t0_norm:.0f}s)",
            flush=True,
        )
    except NotImplementedError as e:
        print(f"[{_ts()}][{label}] Skipped (NotImplementedError): {e}", flush=True)
        return [
            {
                "strat": strat, "imp": imp, "method": method_name,
                "post_rm": post_rm, "harshness": harshness,
                "r2_batch": float("nan"), "r2_diag": float("nan"),
                "n_samples": len(ann_s), "n_genes": exp_s.shape[1],
                "status": "skipped",
            }
            for post_rm in [False, True]
        ]
    except Exception:
        print(
            f"[{_ts()}][{label}] Normalization FAILED after "
            f"{time.time() - t0_norm:.0f}s:\n{traceback.format_exc()}",
            flush=True,
        )
        return [
            {
                "strat": strat, "imp": imp, "method": method_name,
                "post_rm": post_rm, "harshness": harshness,
                "r2_batch": float("nan"), "r2_diag": float("nan"),
                "n_samples": len(ann_s), "n_genes": 0,
                "status": "failed",
            }
            for post_rm in [False, True]
        ]

    rows: list[dict] = []
    for post_rm in [False, True]:
        key = s3_key_exp(strat, imp, method_name, post_rm)
        tag = f"{label}×post_rm={post_rm}"

        if skip_if_exists and s3_exists(s3, key):
            print(f"[{_ts()}][{tag}] Already on S3 — skipping.", flush=True)
            rows.append({
                "strat": strat, "imp": imp, "method": method_name,
                "post_rm": post_rm, "harshness": harshness,
                "r2_batch": float("nan"), "r2_diag": float("nan"),
                "n_samples": float("nan"), "n_genes": float("nan"),
                "status": "cached",
            })
            continue

        exp_out = exp_norm.copy()
        ann_out = ann_s.copy()

        if post_rm:
            print(f"[{_ts()}][{tag}] Identifying outlier batches ...", flush=True)
            try:
                outliers = identify_outlier_batches(exp_out, ann_out)
                if outliers:
                    print(
                        f"[{_ts()}][{tag}] Removing {len(outliers)} outlier batch(es): "
                        f"{outliers}",
                        flush=True,
                    )
                    ann_out = ann_out[~ann_out[BATCH_COL].isin(outliers)]
                    exp_out = exp_out.loc[ann_out.index]
                else:
                    print(f"[{_ts()}][{tag}] No outlier batches found.", flush=True)
            except Exception:
                print(
                    f"[{_ts()}][{tag}] Post-removal failed:\n{traceback.format_exc()}",
                    flush=True,
                )

        try:
            r2_b = r2_batch(exp_out, ann_out, batch_col=BATCH_COL)
            r2_d = r2_batch(exp_out, ann_out, batch_col=BIO_COL)
        except Exception:
            r2_b = r2_d = float("nan")

        print(
            f"[{_ts()}][{tag}] r2_batch={r2_b:.3f} r2_diag={r2_d:.3f} — uploading ...",
            flush=True,
        )
        try:
            upload_exp_to_s3(exp_out, s3, key)
            status = "ok"
            print(f"[{_ts()}][{tag}] Upload complete.", flush=True)
        except Exception:
            print(
                f"[{_ts()}][{tag}] S3 upload failed:\n{traceback.format_exc()}",
                flush=True,
            )
            status = "upload_failed"

        rows.append({
            "strat": strat, "imp": imp, "method": method_name,
            "post_rm": post_rm, "harshness": harshness,
            "r2_batch": r2_b, "r2_diag": r2_d,
            "n_samples": len(ann_out), "n_genes": exp_out.shape[1],
            "status": status,
        })

        del exp_out, ann_out
        gc.collect()

    del exp_norm
    gc.collect()
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 2 worker: normalize a prepared (strat, imp) dataset."
    )
    parser.add_argument("--strat",           required=True)
    parser.add_argument("--imp",             required=True)
    parser.add_argument("--method",          required=True)
    parser.add_argument("--skip-if-exists",  action="store_true")
    parser.add_argument("--out-json",        default=None)
    parser.add_argument("--memory-limit-gb", type=float, default=2.0)
    args = parser.parse_args()

    if args.skip_if_exists:
        s3_check = boto3.client("s3")
        keys = [
            s3_key_exp(args.strat, args.imp, args.method, post_rm)
            for post_rm in [False, True]
        ]
        if all(s3_exists(s3_check, k) for k in keys):
            _, harshness = METHODS[args.method]
            rows = [
                {
                    "strat": args.strat, "imp": args.imp, "method": args.method,
                    "post_rm": post_rm, "harshness": harshness,
                    "r2_batch": float("nan"), "r2_diag": float("nan"),
                    "n_samples": float("nan"), "n_genes": float("nan"),
                    "status": "cached",
                }
                for post_rm in [False, True]
            ]
            if args.out_json:
                with open(args.out_json, "w") as f:
                    json.dump(rows, f)
            else:
                for row in rows:
                    print(json.dumps(row))
            sys.exit(0)

    _check_memory(
        args.memory_limit_gb,
        label=f"{args.strat}×{args.imp}×{args.method} startup",
    )

    s3      = boto3.client("s3")
    key_exp = s3_key_prepared_exp(args.strat, args.imp)
    key_ann = s3_key_prepared_ann(args.strat, args.imp)

    if not s3_exists(s3, key_exp) or not s3_exists(s3, key_ann):
        print(
            f"[{args.strat}×{args.imp}×{args.method}] Prepared dataset not found on S3. "
            f"Run run_prep_parallel.py first.",
            file=sys.stderr,
        )
        sys.exit(3)

    label = f"{args.strat}×{args.imp}×{args.method}"
    t0_total = time.time()
    print(
        f"[{_ts()}][{label}] Downloading prepared dataset "
        f"(free={_free_gb():.1f}GB) ...",
        flush=True,
    )
    t0 = time.time()
    exp_s = download_exp_from_s3(s3, key_exp)
    ann_s = download_ann_from_s3(s3, key_ann)
    print(
        f"[{_ts()}][{label}] Dataset ready: {exp_s.shape[0]} samples × "
        f"{exp_s.shape[1]} genes ({time.time() - t0:.0f}s)",
        flush=True,
    )

    _check_memory(
        args.memory_limit_gb / 2,
        label=f"{label} post-download",
    )

    rows = run_norm(
        strat=args.strat,
        imp=args.imp,
        method_name=args.method,
        skip_if_exists=args.skip_if_exists,
        exp_s=exp_s,
        ann_s=ann_s,
    )

    del exp_s, ann_s
    gc.collect()

    total = time.time() - t0_total
    statuses = [r["status"] for r in rows]
    print(
        f"[{_ts()}][{label}] Done: {statuses} total={total:.0f}s",
        flush=True,
    )

    if args.out_json:
        with open(args.out_json, "w") as f:
            json.dump(rows, f)
    else:
        for row in rows:
            print(json.dumps(row))

    sys.exit(0)


if __name__ == "__main__":
    main()
