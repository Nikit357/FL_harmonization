"""
Stage 1 worker: applies one (strategy, imputation) combination and saves the
prepared expression + annotation to S3 for reuse by all normalization methods.

This worker downloads the raw data, builds filter strategies, applies the filter,
runs imputation, applies log_transform_by_cohort, then uploads two files:
    prepared/{strat}__{imp}__exp.tsv.gz   — imputed expression matrix
    prepared/{strat}__{imp}__ann.tsv.gz   — filtered annotation

Usage
-----
python run_prep_job.py \\
    --strat A_confirmed_bad \\
    --imp   knn \\
    [--skip-if-exists] \\
    [--out-json /tmp/prep_jobs/A_confirmed_bad__knn.json] \\
    [--memory-limit-gb 4.0]
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
    build_filter_strategies,
    load_data,
    log_transform_by_cohort,
    prepare_dataset,
    prepare_dataset_imputed,
    s3_exists,
    s3_key_prepared_ann,
    s3_key_prepared_exp,
    upload_ann_to_s3,
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


def run_prep(
    strat: str,
    imp: str,
    skip_if_exists: bool,
    comb_exp,
    filter_strategies: dict,
) -> dict:
    """
    Prepare one (strat, imp) dataset and upload to S3.

    Parameters
    ----------
    strat
        Filter strategy name.
    imp
        Imputation method: 'strict', 'knn', 'missforest', 'softimpute'.
    skip_if_exists
        If True and both S3 keys exist, skip without re-computing.
    comb_exp
        Full expression matrix.
    filter_strategies
        Dict mapping strategy name → filtered annotation DataFrame.

    Returns
    -------
    Metric row dict with keys: strat, imp, n_samples, n_genes, status.
    """
    s3      = boto3.client("s3")
    key_exp = s3_key_prepared_exp(strat, imp)
    key_ann = s3_key_prepared_ann(strat, imp)

    if skip_if_exists and s3_exists(s3, key_exp) and s3_exists(s3, key_ann):
        print(f"[{strat}×{imp}] Already prepared — skipping.")
        return {
            "strat": strat, "imp": imp,
            "n_samples": float("nan"), "n_genes": float("nan"),
            "status": "cached",
        }

    ann_strat = filter_strategies[strat]
    n_strat = len(ann_strat)

    if imp == "strict":
        print(
            f"[{_ts()}][{strat}×{imp}] Applying strict filter "
            f"({n_strat} samples) ...",
            flush=True,
        )
        exp_s, ann_s = prepare_dataset(ann_strat, comb_exp)
        print(
            f"[{_ts()}][{strat}×{imp}] Strict done: "
            f"{exp_s.shape[0]} samples × {exp_s.shape[1]} genes",
            flush=True,
        )
    else:
        print(
            f"[{_ts()}][{strat}×{imp}] Running {imp} imputation "
            f"({n_strat} samples) — R output follows ...",
            flush=True,
        )
        t0_imp = time.time()
        try:
            exp_s, ann_s = prepare_dataset_imputed(ann_strat, comb_exp, method=imp)
            print(
                f"[{_ts()}][{strat}×{imp}] Imputation done: "
                f"{exp_s.shape[0]} samples × {exp_s.shape[1]} genes "
                f"({time.time() - t0_imp:.0f}s)",
                flush=True,
            )
        except Exception:
            print(
                f"[{_ts()}][{strat}×{imp}] Imputation failed after "
                f"{time.time() - t0_imp:.0f}s — falling back to strict:\n"
                f"{traceback.format_exc()}",
                flush=True,
            )
            exp_s, ann_s = prepare_dataset(ann_strat, comb_exp)

    print(f"[{_ts()}][{strat}×{imp}] Applying log transform by cohort ...", flush=True)
    exp_s = log_transform_by_cohort(exp_s, ann_s.loc[exp_s.index])

    print(
        f"[{_ts()}][{strat}×{imp}] Uploading to S3 "
        f"({exp_s.shape[0]} samples × {exp_s.shape[1]} genes) ...",
        flush=True,
    )
    try:
        upload_exp_to_s3(exp_s, s3, key_exp)
        upload_ann_to_s3(ann_s, s3, key_ann)
        status = "ok"
        print(f"[{_ts()}][{strat}×{imp}] Upload complete.", flush=True)
    except Exception:
        print(f"[{strat}×{imp}] S3 upload failed:\n{traceback.format_exc()}")
        status = "upload_failed"

    return {
        "strat": strat, "imp": imp,
        "n_samples": len(exp_s), "n_genes": exp_s.shape[1],
        "status": status,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 1 worker: prepare one (strat, imp) dataset and upload to S3."
    )
    parser.add_argument("--strat",           required=True,
                        help="Filter strategy name (e.g. A_confirmed_bad)")
    parser.add_argument("--imp",             required=True,
                        help="Imputation method: strict, knn, missforest, softimpute")
    parser.add_argument("--skip-if-exists",  action="store_true",
                        help="Skip if both S3 prepared files already exist")
    parser.add_argument("--out-json",        default=None,
                        help="Path to write metric row as JSON (for dispatcher)")
    parser.add_argument("--memory-limit-gb", type=float, default=4.0,
                        help="Abort if free RAM < this value in GB (default: 4.0)")
    args = parser.parse_args()

    if args.skip_if_exists:
        s3_check = boto3.client("s3")
        if (s3_exists(s3_check, s3_key_prepared_exp(args.strat, args.imp))
                and s3_exists(s3_check, s3_key_prepared_ann(args.strat, args.imp))):
            row = {
                "strat": args.strat, "imp": args.imp,
                "n_samples": float("nan"), "n_genes": float("nan"),
                "status": "cached",
            }
            if args.out_json:
                with open(args.out_json, "w") as f:
                    json.dump([row], f)
            else:
                print(json.dumps(row))
            sys.exit(0)

    label = f"{args.strat}×{args.imp}"
    _check_memory(args.memory_limit_gb, label=f"{label} startup")

    t0_total = time.time()
    print(f"[{_ts()}][{label}] Loading raw data (free={_free_gb():.1f}GB) ...", flush=True)
    t0 = time.time()
    comb_exp, comb_ann = load_data()
    print(
        f"[{_ts()}][{label}] Data loaded: {comb_exp.shape[0]} samples × "
        f"{comb_exp.shape[1]} genes ({time.time() - t0:.0f}s)",
        flush=True,
    )

    _check_memory(args.memory_limit_gb / 2, label=f"{label} post-load")

    print(f"[{_ts()}][{label}] Building filter strategies ...", flush=True)
    t0 = time.time()
    filter_strategies = build_filter_strategies(comb_ann, comb_exp)
    print(
        f"[{_ts()}][{label}] Filter strategies ready ({time.time() - t0:.0f}s)",
        flush=True,
    )
    del comb_ann
    gc.collect()

    row = run_prep(
        strat=args.strat,
        imp=args.imp,
        skip_if_exists=args.skip_if_exists,
        comb_exp=comb_exp,
        filter_strategies=filter_strategies,
    )

    del comb_exp, filter_strategies
    gc.collect()

    total = time.time() - t0_total
    print(
        f"[{_ts()}][{label}] Finished: status={row['status']} "
        f"total={total:.0f}s",
        flush=True,
    )

    if args.out_json:
        with open(args.out_json, "w") as f:
            json.dump([row], f)
    else:
        print(json.dumps(row))

    sys.exit(0)


if __name__ == "__main__":
    main()
