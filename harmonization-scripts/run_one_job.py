"""
Worker script: runs one normalization method on one (strategy, imputation) dataset.

Writes up to 2 expression files to S3 (post_rm=False/True) and a metrics JSON sidecar.
Designed to be launched as a subprocess — rpy2 initialises fresh in each process,
avoiding the fork-safety issue with shared R sessions.

Memory safety:
- Checks available RAM at startup; exits with code 2 if below --memory-limit-gb.
- Explicitly deletes large intermediates and calls gc.collect() between steps.
- Calls R gc() after expensive R operations to release R heap.

Usage
-----
python run_one_job.py \\
    --strat  A_confirmed_bad \\
    --imp    knn \\
    --method 05_combat \\
    [--skip-if-exists] \\
    [--out-json /tmp/bench_jobs/A_confirmed_bad__knn__05_combat.json] \\
    [--memory-limit-gb 2.0]
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import traceback

import boto3
import pandas as pd

from bench_shared import (
    BATCH_COL,
    BIO_COL,
    METHODS,
    build_filter_strategies,
    identify_outlier_batches,
    load_data,
    log_transform_by_cohort,
    prepare_dataset,
    prepare_dataset_imputed,
    r2_batch,
    s3_exists,
    s3_key_exp,
    upload_exp_to_s3,
)


def _free_gb() -> float:
    try:
        import psutil
        return psutil.virtual_memory().available / 1e9
    except ImportError:
        return 999.0


def _check_memory(min_free_gb: float, label: str = "") -> None:
    """Exit with code 2 if free RAM is below min_free_gb."""
    free = _free_gb()
    if free < min_free_gb:
        print(
            f"[{label}] Insufficient RAM: {free:.1f} GB free < {min_free_gb:.1f} GB "
            "required — aborting to protect session.",
            file=sys.stderr,
        )
        sys.exit(2)


def run_job(
    strat: str,
    imp: str,
    method_name: str,
    skip_if_exists: bool,
    comb_exp: pd.DataFrame,
    filter_strategies: dict[str, pd.DataFrame],
) -> list[dict]:
    """
    Run one (strat, imp, method) combination and upload results to S3.

    Parameters
    ----------
    strat
        Filter strategy name (e.g. 'A_confirmed_bad').
    imp
        Imputation method: 'strict', 'knn', 'missforest', 'softimpute'.
    method_name
        Normalization method key (e.g. '05_combat').
    skip_if_exists
        Skip combinations whose S3 keys already exist.
    comb_exp
        Full expression matrix.
    filter_strategies
        Dict mapping strategy name → filtered annotation DataFrame.

    Returns
    -------
    List of metric row dicts, one per post_rm option (False, True).
    """
    s3 = boto3.client("s3")
    fn, harshness = METHODS[method_name]

    ann_strat = filter_strategies[strat]

    # ── Imputation ────────────────────────────────────────────────────────────
    if imp == "strict":
        exp_s, ann_s = prepare_dataset(ann_strat, comb_exp)
    else:
        try:
            exp_s, ann_s = prepare_dataset_imputed(ann_strat, comb_exp, method=imp)
        except Exception:
            print(
                f"[{strat}×{imp}×{method_name}] Imputation failed — "
                f"falling back to strict:\n{traceback.format_exc()}"
            )
            exp_s, ann_s = prepare_dataset(ann_strat, comb_exp)

    exp_s = log_transform_by_cohort(exp_s, ann_s.loc[exp_s.index])

    # ── Normalization ─────────────────────────────────────────────────────────
    try:
        exp_norm = fn(exp_s, ann_s, batch_col=BATCH_COL, bio_col=BIO_COL)
    except NotImplementedError as e:
        print(f"[{strat}×{imp}×{method_name}] Skipped (NotImplementedError): {e}")
        del exp_s
        gc.collect()
        return [
            {
                "strat": strat, "imp": imp, "method": method_name,
                "post_rm": post_rm, "harshness": harshness,
                "r2_batch": float("nan"), "r2_diag": float("nan"),
                "n_samples": len(ann_s), "n_genes": exp_s.shape[1] if "exp_s" in dir() else 0,
                "status": "skipped",
            }
            for post_rm in [False, True]
        ]
    except Exception:
        print(
            f"[{strat}×{imp}×{method_name}] Normalization failed:\n"
            f"{traceback.format_exc()}"
        )
        del exp_s
        gc.collect()
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

    # Free the pre-normalization matrix now that we have exp_norm
    n_genes_orig = exp_s.shape[1]
    del exp_s
    gc.collect()

    # ── Post-normalization: both post_rm variants from one normalization call ─
    rows: list[dict] = []
    for post_rm in [False, True]:
        key = s3_key_exp(strat, imp, method_name, post_rm)

        if skip_if_exists and s3_exists(s3, key):
            print(
                f"[{strat}×{imp}×{method_name}×post_rm={post_rm}] "
                "Already exists — skipping."
            )
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
            try:
                outliers = identify_outlier_batches(exp_out, ann_out)
                if outliers:
                    ann_out = ann_out[~ann_out[BATCH_COL].isin(outliers)]
                    exp_out = exp_out.loc[ann_out.index]
            except Exception:
                print(
                    f"[{strat}×{imp}×{method_name}×post_rm=True] "
                    f"Post-removal failed:\n{traceback.format_exc()}"
                )

        try:
            r2_b = r2_batch(exp_out, ann_out, batch_col=BATCH_COL)
            r2_d = r2_batch(exp_out, ann_out, batch_col=BIO_COL)
        except Exception:
            r2_b = r2_d = float("nan")

        try:
            upload_exp_to_s3(exp_out, s3, key)
            status = "ok"
        except Exception:
            print(
                f"[{strat}×{imp}×{method_name}] S3 upload failed:\n"
                f"{traceback.format_exc()}"
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
        description="Run one (strat, imp, method) normalization job."
    )
    parser.add_argument("--strat",            required=True,
                        help="Filter strategy name")
    parser.add_argument("--imp",              required=True,
                        help="Imputation method: strict, knn, missforest, softimpute")
    parser.add_argument("--method",           required=True,
                        help="Normalization method key (e.g. 05_combat)")
    parser.add_argument("--skip-if-exists",   action="store_true",
                        help="Skip if S3 output already exists")
    parser.add_argument("--out-json",         default=None,
                        help="Path to write metric rows as JSON (for dispatcher)")
    parser.add_argument("--memory-limit-gb",  type=float, default=2.0,
                        help="Abort if free RAM < this value in GB (default: 2.0)")
    args = parser.parse_args()

    # Fast-path: if both S3 outputs already exist, return cached rows and exit
    # without loading any data or running normalization.
    if args.skip_if_exists:
        keys = {
            post_rm: s3_key_exp(args.strat, args.imp, args.method, post_rm)
            for post_rm in [False, True]
        }
        s3_check = boto3.client("s3")
        if all(s3_exists(s3_check, k) for k in keys.values()):
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

    # Guard before loading large data objects
    _check_memory(args.memory_limit_gb, label=f"{args.strat}×{args.imp}×{args.method} startup")

    comb_exp, comb_ann = load_data()

    # Guard again after data is loaded (loading itself consumed RAM)
    _check_memory(args.memory_limit_gb / 2, label=f"{args.strat}×{args.imp}×{args.method} post-load")

    filter_strategies = build_filter_strategies(comb_ann, comb_exp)

    # Release the full annotation — filter_strategies holds the relevant subsets
    del comb_ann
    gc.collect()

    rows = run_job(
        strat=args.strat,
        imp=args.imp,
        method_name=args.method,
        skip_if_exists=args.skip_if_exists,
        comb_exp=comb_exp,
        filter_strategies=filter_strategies,
    )

    # Release data before writing results
    del comb_exp, filter_strategies
    gc.collect()

    if args.out_json:
        with open(args.out_json, "w") as f:
            json.dump(rows, f)
    else:
        for row in rows:
            print(json.dumps(row))

    sys.exit(0)


if __name__ == "__main__":
    main()
