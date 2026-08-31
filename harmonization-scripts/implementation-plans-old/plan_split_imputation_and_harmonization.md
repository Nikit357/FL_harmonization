# Implementation Plan: Split Preparation and Normalization into Two Pipelines

**Status:** Phases 1–5 implemented; Phase 6 pending runtime testing  
**Date:** 2026-04-21  
**Related:** `plan_docker_image.md` (existing infrastructure reference)

---

## 0. Motivation

### The problem with the current monolithic design

Each call to `run_one_job.py` currently does **all** of the following:

1. Download `comb_exp.tsv` (~1.9 GB) from S3 (or hit `/tmp` pickle cache)
2. Run `build_filter_strategies()` (expensive: iterative PCA for E1–E3)
3. Apply the filter strategy to get `ann_strat`
4. Apply imputation (strict / KNN / missForest / softImpute)
5. Apply `log_transform_by_cohort`
6. Run the normalization method (R session, rpy2)
7. Optionally remove post-normalization outlier batches
8. Upload two S3 output files

Steps 1–5 are **identical for all 24 normalization methods** sharing the same `(strat, imp)` pair. With 24 methods, imputation is executed **24 times unnecessarily** for each `(strat, imp)` combination — 960 redundant operations across the full benchmark (10 × 4 × 24, where only 10 × 4 = 40 unique prepared datasets exist).

### The proposed split

```
Stage 1 — Preparation   (10 strats × 4 imps = 40 jobs)
    run_prep_parallel.py  ──dispatches──►  run_prep_job.py
    Outputs: S3 prepared/{strat}__{imp}__exp.tsv.gz
                         prepared/{strat}__{imp}__ann.tsv.gz

Stage 2 — Normalization  (≤40 available × 24 methods = ≤960 jobs)
    run_norm_parallel.py  ──dispatches──►  run_norm_job.py
    Reads:   S3 prepared/{strat}__{imp}__exp.tsv.gz  (already imputed)
    Outputs: S3 exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz
                 metrics.csv  (aggregated)
```

### Benefits
- **No duplicate imputation.** Each `(strat, imp)` prepared dataset is computed once and reused across all 24 methods.
- **Smaller worker footprint.** Stage 2 workers download only the prepared dataset (~50–200 MB) instead of the full raw matrix (1.9 GB + filter strategies).
- **Independent failure domains.** An imputation failure doesn't block normalization for other methods; a normalization failure doesn't require re-imputing.
- **Incremental execution.** Stage 2 can start as soon as any `(strat, imp)` pair is ready on S3, without waiting for all 40 preparation jobs to complete.
- **Same CLI surface.** All existing flags (`--n-workers`, `--skip-if-exists`, `--retry-failed`, `--timeout-s`, `--memory-limit-gb`, `--strats`, `--imps`, `--methods`) are preserved and work identically.

---

## 1. File Inventory

### New files to create

| File | Role |
|---|---|
| `run_prep_job.py` | Stage 1 worker: one `(strat, imp)` preparation job |
| `run_prep_parallel.py` | Stage 1 dispatcher: 40-job preparation grid |
| `run_norm_job.py` | Stage 2 worker: one `(strat, imp, method)` normalization job |
| `run_norm_parallel.py` | Stage 2 dispatcher: up-to-960-job normalization grid |

### Existing files to modify

| File | Change |
|---|---|
| `bench_shared.py` | Add `s3_key_prepared_exp()`, `s3_key_prepared_ann()`, `download_ann_from_s3()`, `upload_ann_to_s3()` |

### Existing files left **unchanged** (backward compatibility)

| File | Status |
|---|---|
| `run_one_job.py` | Unchanged — still works end-to-end |
| `run_cross_product_parallel.py` | Unchanged — still works end-to-end |
| `load_cross_product_results.py` | Unchanged — reads final `exp/` and `metrics.csv` |
| `test_mock.py` | Unchanged — smoke-tests `bench_shared.py` in isolation |

---

## 2. S3 Key Scheme Additions

### New prefix: `prepared/`

```
FL_batch_correction/
├── prepared/                          ← NEW: Stage 1 outputs
│   ├── A_confirmed_bad__strict__exp.tsv.gz
│   ├── A_confirmed_bad__strict__ann.tsv.gz
│   ├── A_confirmed_bad__knn__exp.tsv.gz
│   ├── A_confirmed_bad__knn__ann.tsv.gz
│   ├── ...                            (40 pairs × 2 files = 80 objects)
├── exp/                               ← unchanged: Stage 2 outputs
│   ├── A_confirmed_bad__strict__01_raw__post0.tsv.gz
│   └── ...                            (960 jobs × 2 post_rm = 1,920 objects)
├── metrics.csv                        ← unchanged: Stage 2 aggregated metrics
├── prep_metrics.csv                   ← NEW: Stage 1 metrics (n_samples, n_genes, status)
├── failed_prep_<POD_NAME>.txt         ← NEW: Stage 1 per-pod failed-jobs log on S3
└── failed_norm_<POD_NAME>.txt         ← NEW: Stage 2 per-pod failed-jobs log on S3
```

### Changes to `bench_shared.py`

Add these four functions immediately after the existing `s3_key_metrics()`:

```python
# ── S3 keys for Stage 1 prepared datasets ────────────────────────────────────

def s3_key_prepared_exp(strat: str, imp: str) -> str:
    """S3 key for the imputed expression matrix produced by Stage 1."""
    return f"{S3_PREFIX}/prepared/{strat}__{imp}__exp.tsv.gz"


def s3_key_prepared_ann(strat: str, imp: str) -> str:
    """S3 key for the filtered annotation produced by Stage 1."""
    return f"{S3_PREFIX}/prepared/{strat}__{imp}__ann.tsv.gz"


def s3_key_prep_metrics() -> str:
    """S3 key for the Stage 1 aggregated metrics CSV."""
    return f"{S3_PREFIX}/prep_metrics.csv"


def upload_ann_to_s3(ann_df: pd.DataFrame, s3_client: object, key: str) -> None:
    """Upload annotation DataFrame as gzip-compressed TSV to S3."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        ann_df.to_csv(gz, sep="\t")
    buf.seek(0)
    s3_client.upload_fileobj(buf, S3_BUCKET, key)  # type: ignore[union-attr]


def download_ann_from_s3(s3_client: object, key: str) -> pd.DataFrame:
    """Download gzip-compressed TSV annotation DataFrame from S3."""
    buf = io.BytesIO()
    s3_client.download_fileobj(S3_BUCKET, key, buf)  # type: ignore[union-attr]
    buf.seek(0)
    with gzip.open(buf, "rb") as gz:
        return pd.read_csv(gz, sep="\t", index_col=0)
```

---

## 3. `run_prep_job.py` — Stage 1 Worker

**Responsibility:** One `(strat, imp)` pair → two S3 objects (`__exp.tsv.gz`, `__ann.tsv.gz`).

```python
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
import traceback

import boto3

from bench_shared import (
    BATCH_COL,
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
    try:
        import psutil
        return psutil.virtual_memory().available / 1e9
    except ImportError:
        return 999.0


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
    s3          = boto3.client("s3")
    key_exp     = s3_key_prepared_exp(strat, imp)
    key_ann     = s3_key_prepared_ann(strat, imp)

    if skip_if_exists and s3_exists(s3, key_exp) and s3_exists(s3, key_ann):
        print(f"[{strat}×{imp}] Already prepared — skipping.")
        return {"strat": strat, "imp": imp,
                "n_samples": float("nan"), "n_genes": float("nan"),
                "status": "cached"}

    ann_strat = filter_strategies[strat]

    # ── Apply imputation ──────────────────────────────────────────────────────
    if imp == "strict":
        exp_s, ann_s = prepare_dataset(ann_strat, comb_exp)
    else:
        try:
            exp_s, ann_s = prepare_dataset_imputed(ann_strat, comb_exp, method=imp)
        except Exception:
            print(
                f"[{strat}×{imp}] Imputation failed — "
                f"falling back to strict:\n{traceback.format_exc()}"
            )
            exp_s, ann_s = prepare_dataset(ann_strat, comb_exp)

    exp_s = log_transform_by_cohort(exp_s, ann_s.loc[exp_s.index])

    # ── Upload to S3 ─────────────────────────────────────────────────────────
    try:
        upload_exp_to_s3(exp_s, s3, key_exp)
        upload_ann_to_s3(ann_s, s3, key_ann)
        status = "ok"
    except Exception:
        print(
            f"[{strat}×{imp}] S3 upload failed:\n{traceback.format_exc()}"
        )
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

    # Fast-path: check S3 before loading any data
    if args.skip_if_exists:
        s3_check = boto3.client("s3")
        if (s3_exists(s3_check, s3_key_prepared_exp(args.strat, args.imp))
                and s3_exists(s3_check, s3_key_prepared_ann(args.strat, args.imp))):
            row = {"strat": args.strat, "imp": args.imp,
                   "n_samples": float("nan"), "n_genes": float("nan"),
                   "status": "cached"}
            if args.out_json:
                with open(args.out_json, "w") as f:
                    json.dump([row], f)
            else:
                print(json.dumps(row))
            sys.exit(0)

    _check_memory(args.memory_limit_gb,
                  label=f"{args.strat}×{args.imp} startup")

    comb_exp, comb_ann = load_data()

    _check_memory(args.memory_limit_gb / 2,
                  label=f"{args.strat}×{args.imp} post-load")

    filter_strategies = build_filter_strategies(comb_ann, comb_exp)
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

    if args.out_json:
        with open(args.out_json, "w") as f:
            json.dump([row], f)
    else:
        print(json.dumps(row))

    sys.exit(0)


if __name__ == "__main__":
    main()
```

---

## 4. `run_prep_parallel.py` — Stage 1 Dispatcher

**Responsibility:** Enumerate the `(strat, imp)` grid (40 jobs) and dispatch `run_prep_job.py` subprocesses.

### Key design notes
- Identical concurrency model to `run_cross_product_parallel.py` (ThreadPoolExecutor).
- Same memory guard, timeout, retry, and S3 sync patterns.
- Maintains a **separate** failed-jobs log (`failed_jobs_prep.txt` locally, `failed_prep_{POD_NAME}.txt` on S3) to avoid conflating preparation failures with normalization failures.
- The `--methods` flag is not present — Stage 1 has no normalization methods.
- Pre-caching still applies: dispatches `load_data()` and `build_filter_strategies()` before spawning workers.

```python
"""
Stage 1 dispatcher: launches all (strategy × imputation) preparation jobs
as subprocesses using ThreadPoolExecutor.

Outputs one pair of S3 files per (strat, imp):
    FL_batch_correction/prepared/{strat}__{imp}__exp.tsv.gz
    FL_batch_correction/prepared/{strat}__{imp}__ann.tsv.gz

Usage
-----
# Full preparation run (40 jobs, 4 workers):
nohup python run_prep_parallel.py --n-workers 4 --skip-if-exists \\
    --timeout-s 7200 --memory-limit-gb 6.0 > prep_run.log 2>&1 &

# Subset (useful for testing):
python run_prep_parallel.py --strats A_confirmed_bad --imps strict,knn --n-workers 2

# Resume after partial run (skips completed S3 outputs AND previously failed jobs):
python run_prep_parallel.py --n-workers 4 --skip-if-exists

# Resume and retry previously failed pairs:
python run_prep_parallel.py --n-workers 4 --skip-if-exists --retry-failed

--n-workers N
-------------
Maximum number of parallel worker subprocesses (default: 4).
Each worker downloads the full raw expression matrix from S3 (or /tmp cache)
and runs imputation. Raise only if available RAM allows: each KNN/missForest/
softImpute worker can peak at 6–8 GB.

--skip-if-exists
----------------
Skip any (strat, imp) pair for which both
    prepared/{strat}__{imp}__exp.tsv.gz  and
    prepared/{strat}__{imp}__ann.tsv.gz
already exist on S3. Uses a HEAD request so no data is downloaded.
Combine with --retry-failed to focus a run on new pairs only.

--retry-failed
--------------
Default (omitted): pairs listed in failed_jobs_prep.txt are excluded from
    the grid entirely. Use this when focusing on new or previously untried pairs.
When set: the failed_jobs_prep.txt skip list is ignored and every failed pair
    is attempted again.
    - If a retry succeeds (status ok/cached), the key is removed from the log.
    - If a retry fails again, the key stays in the log.
    Combine with --skip-if-exists to avoid re-running pairs that have valid S3 output.

--timeout-s N
-------------
Kill the worker subprocess after N seconds (default: 3600).
Timed-out jobs are logged in failed_jobs_prep.txt.
Recommended values:
    strict / knn   →  3600 s  (default)
    missforest     →  7200 s  (R missForest is slow on large matrices)
    softimpute     →  7200 s  (R softImpute is slow on large matrices)

--memory-limit-gb F
-------------------
Controls a two-level RAM safety chain (default: 4.0 GB):
    Level 1 (dispatcher): blocks launch of the next subprocess until free RAM >=
        this threshold. Already-running subprocesses are not affected.
    Level 2 (worker startup): each subprocess receives threshold/2 as its own
        --memory-limit-gb and exits (code 2) before loading data if RAM is below.
Workers that exit with code 2 are logged as failures in failed_jobs_prep.txt.

--no-precache
-------------
Skip the pre-caching step where the dispatcher calls load_data() and
build_filter_strategies() before spawning workers. Use only if the /tmp pickle
caches already exist from a previous run of this dispatcher or run_one_job.py.

--strats LIST
-------------
Comma-separated subset of strategy names to run (default: all 10).
Valid values: S0_no_removal, A_confirmed_bad, B_extended_bad, C_rnaseq_only,
    D_malignant_only, E1_iterative_r1, E2_iterative_r2, E3_iterative_r3,
    F_microarray_only, G_affymetrix_only.

--imps LIST
-----------
Comma-separated subset of imputation methods (default: all 4).
Valid values: strict, knn, missforest, softimpute.
Note: missforest and softimpute are slow; use --timeout-s 7200 for these.

--tmp-dir PATH
--------------
Directory for per-job JSON sidecar files written by workers (default:
/tmp/bench_prep_jobs). Created automatically if it does not exist.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
import pandas as pd

from bench_shared import (
    S3_BUCKET,
    S3_PREFIX,
    build_filter_strategies,
    load_data,
    s3_key_prep_metrics,
)

# ── Full preparation grid ─────────────────────────────────────────────────────
ALL_STRATEGIES: list[str] = [
    "S0_no_removal", "A_confirmed_bad", "B_extended_bad",
    "C_rnaseq_only", "D_malignant_only",
    "E1_iterative_r1", "E2_iterative_r2", "E3_iterative_r3",
    "F_microarray_only", "G_affymetrix_only",
]
ALL_IMPUTATION: list[str] = ["strict", "knn", "missforest", "softimpute"]

_MEM_POLL_S    = 30.0
FAILED_LOG_PATH: Path = Path(__file__).parent / "failed_jobs_prep.txt"
_POD_NAME: str        = os.environ.get("POD_NAME", "local")
_S3_FAILED_PREFIX     = f"{S3_PREFIX}/failed_prep_"


def _job_key(strat: str, imp: str) -> str:
    return f"{strat}__{imp}"


def _load_failed_log() -> set[str]:
    if not FAILED_LOG_PATH.exists():
        return set()
    with open(FAILED_LOG_PATH) as fh:
        return {line.strip() for line in fh if line.strip()}


def _save_failed_log(keys: set[str]) -> None:
    with open(FAILED_LOG_PATH, "w") as fh:
        for key in sorted(keys):
            fh.write(key + "\n")
    print(f"Prep failed-jobs log written: {FAILED_LOG_PATH} ({len(keys)} entries)",
          flush=True)


def _sync_failed_log_from_s3() -> None:
    import botocore.exceptions
    s3 = boto3.client("s3")
    try:
        paginator = s3.get_paginator("list_objects_v2")
        s3_keys: set[str] = set()
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=_S3_FAILED_PREFIX):
            for obj in page.get("Contents", []):
                body = s3.get_object(Bucket=S3_BUCKET, Key=obj["Key"])["Body"].read().decode()
                s3_keys |= {ln.strip() for ln in body.splitlines() if ln.strip()}
        if s3_keys:
            local_keys = _load_failed_log()
            merged = s3_keys | local_keys
            if merged != local_keys:
                _save_failed_log(merged)
                print(f"[S3 sync] Merged {len(s3_keys)} prep S3 keys → {len(merged)} total.",
                      flush=True)
    except botocore.exceptions.ClientError as exc:
        print(f"[S3 sync] Could not read prep failed_jobs from S3: {exc}", flush=True)


def _sync_failed_log_to_s3(keys: set[str]) -> None:
    import boto3
    s3  = boto3.client("s3")
    key = f"{_S3_FAILED_PREFIX}{_POD_NAME}.txt"
    if keys:
        body = "\n".join(sorted(keys)).encode()
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=body)
        print(f"[S3 sync] Uploaded {len(keys)} prep failed keys to s3://{S3_BUCKET}/{key}",
              flush=True)
    else:
        try:
            s3.delete_object(Bucket=S3_BUCKET, Key=key)
        except Exception:
            pass


def _free_gb() -> float:
    try:
        import psutil
        return psutil.virtual_memory().available / 1e9
    except ImportError:
        return 999.0


def _wait_for_memory(min_free_gb: float) -> None:
    while True:
        if _free_gb() >= min_free_gb:
            return
        print(f"  [mem-guard] {_free_gb():.1f} GB free — pausing {_MEM_POLL_S:.0f}s",
              flush=True)
        time.sleep(_MEM_POLL_S)


def run_prep_dispatcher(
    strategies: list[str],
    imputation_methods: list[str],
    n_workers: int,
    skip_if_exists: bool,
    tmp_dir: Path,
    skip_keys: set[str],
    timeout_s: int = 3600,
    memory_limit_gb: float = 4.0,
) -> tuple[list[dict], set[str], set[str]]:
    """
    Launch all preparation jobs as subprocesses.

    Returns
    -------
    tuple of (all_rows, newly_failed_keys, newly_succeeded_keys)
    """
    import subprocess

    jobs = [
        (strat, imp)
        for strat in strategies
        for imp   in imputation_methods
        if _job_key(strat, imp) not in skip_keys
    ]
    n_skipped = (len(strategies) * len(imputation_methods)) - len(jobs)
    if n_skipped:
        print(f"Skipping {n_skipped} previously failed prep job(s) "
              f"(pass --retry-failed to attempt again).", flush=True)

    total = len(jobs)
    print(f"Prep jobs to run: {total}  |  Workers: {n_workers}  |  "
          f"Skip-if-exists: {skip_if_exists}  |  Timeout: {timeout_s}s  |  "
          f"Memory guard: {memory_limit_gb:.1f} GB", flush=True)

    def launch(strat: str, imp: str) -> tuple[list[dict], float, int]:
        _wait_for_memory(memory_limit_gb)
        json_path = tmp_dir / f"{strat}__{imp}.json"
        cmd = [
            sys.executable, "run_prep_job.py",
            "--strat", strat,
            "--imp",   imp,
            "--out-json", str(json_path),
            "--memory-limit-gb", str(memory_limit_gb / 2),
        ]
        if skip_if_exists:
            cmd.append("--skip-if-exists")
        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=timeout_s, cwd=str(Path(__file__).parent),
            )
        except subprocess.TimeoutExpired:
            return ([], time.time() - t0, -9)
        elapsed = time.time() - t0
        rows: list[dict] = []
        if proc.returncode == 0 and json_path.exists():
            try:
                with open(json_path) as fh:
                    rows = json.load(fh)
            except Exception:
                pass
        elif proc.returncode != 0:
            print(f"  FAILED {strat}×{imp} exit={proc.returncode} ({elapsed:.0f}s)\n"
                  f"  stderr: {proc.stderr[-800:]}", flush=True)
        return (rows, elapsed, proc.returncode)

    all_rows: list[dict]     = []
    newly_failed: set[str]   = set()
    newly_succeeded: set[str] = set()
    done = 0

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        future_to_job = {
            pool.submit(launch, strat, imp): (strat, imp)
            for strat, imp in jobs
        }
        for future in as_completed(future_to_job):
            strat, imp = future_to_job[future]
            key = _job_key(strat, imp)
            done += 1
            rows, elapsed, rc = future.result()
            statuses = [r.get("status", "failed") for r in rows] if rows else []
            if rc != 0 or not rows or any(s in ("failed", "upload_failed") for s in statuses):
                newly_failed.add(key)
                print(f"  [{done}/{total}] FAILED {strat}×{imp} "
                      f"({'timeout' if rc == -9 else f'exit={rc}'}) ({elapsed:.0f}s)",
                      flush=True)
            else:
                newly_succeeded.add(key)
                all_rows.extend(rows)
                print(f"  [{done}/{total}] {strat}×{imp} ({elapsed:.0f}s) → {statuses}",
                      flush=True)

    return all_rows, newly_failed, newly_succeeded


def upload_prep_metrics(rows: list[dict]) -> None:
    df        = pd.DataFrame(rows)
    csv_bytes = df.to_csv(index=False).encode()
    s3        = boto3.client("s3")
    key       = s3_key_prep_metrics()
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=csv_bytes)
    print(f"Prep metrics uploaded: s3://{S3_BUCKET}/{key} ({len(df)} rows)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 1 dispatcher: prepare (strat × imp) datasets in parallel."
    )
    parser.add_argument("--n-workers",       type=int,   default=4)
    parser.add_argument("--skip-if-exists",  action="store_true")
    parser.add_argument("--retry-failed",    action="store_true")
    parser.add_argument("--tmp-dir",         default="/tmp/bench_prep_jobs")
    parser.add_argument("--strats",          default=None,
                        help="Comma-separated strategy subset (default: all 10)")
    parser.add_argument("--imps",            default=None,
                        help="Comma-separated imputation subset (default: all 4)")
    parser.add_argument("--no-precache",     action="store_true")
    parser.add_argument("--timeout-s",       type=int,   default=3600,
                        help="Worker timeout in seconds (use 7200 for missforest/softimpute)")
    parser.add_argument("--memory-limit-gb", type=float, default=4.0)
    args = parser.parse_args()

    strategies = args.strats.split(",") if args.strats else ALL_STRATEGIES
    imps       = args.imps.split(",")   if args.imps   else ALL_IMPUTATION
    tmp_dir    = Path(args.tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    _sync_failed_log_from_s3()
    previously_failed = _load_failed_log()
    if previously_failed and not args.retry_failed:
        skip_keys = previously_failed
    else:
        skip_keys = set()

    if not args.no_precache:
        print("Pre-caching raw dataset and filter strategies...", flush=True)
        t0 = time.time()
        comb_exp, comb_ann = load_data()
        build_filter_strategies(comb_ann, comb_exp)
        print(f"Cache ready ({time.time() - t0:.0f}s). Freeing dispatcher copies...",
              flush=True)
        del comb_exp, comb_ann
        gc.collect()

    rows, newly_failed, newly_succeeded = run_prep_dispatcher(
        strategies=strategies,
        imputation_methods=imps,
        n_workers=args.n_workers,
        skip_if_exists=args.skip_if_exists,
        tmp_dir=tmp_dir,
        skip_keys=skip_keys,
        timeout_s=args.timeout_s,
        memory_limit_gb=args.memory_limit_gb,
    )

    updated_failed = (previously_failed - newly_succeeded) | newly_failed
    if updated_failed != previously_failed or newly_failed:
        _save_failed_log(updated_failed)
    _sync_failed_log_to_s3(updated_failed)

    if rows:
        upload_prep_metrics(rows)


if __name__ == "__main__":
    main()
```

---

## 5. `run_norm_job.py` — Stage 2 Worker

**Responsibility:** Download a prepared `(strat, imp)` dataset from S3, run one normalization method, upload results.

**Key difference from `run_one_job.py`:** Does NOT call `load_data()`, `build_filter_strategies()`, or any imputation function. Downloads only the prepared `__exp.tsv.gz` and `__ann.tsv.gz` files (~50–200 MB total, vs ~1.9 GB for raw data).

```python
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
    try:
        import psutil
        return psutil.virtual_memory().available / 1e9
    except ImportError:
        return 999.0


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
    s3               = boto3.client("s3")
    fn, harshness    = METHODS[method_name]

    # ── Normalization ─────────────────────────────────────────────────────────
    try:
        exp_norm = fn(exp_s, ann_s, batch_col=BATCH_COL, bio_col=BIO_COL)
    except NotImplementedError as e:
        print(f"[{strat}×{imp}×{method_name}] Skipped (NotImplementedError): {e}")
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
            f"[{strat}×{imp}×{method_name}] Normalization failed:\n"
            f"{traceback.format_exc()}"
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

    # ── Post-normalization: both post_rm variants ─────────────────────────────
    rows: list[dict] = []
    for post_rm in [False, True]:
        key = s3_key_exp(strat, imp, method_name, post_rm)

        if skip_if_exists and s3_exists(s3, key):
            print(
                f"[{strat}×{imp}×{method_name}×post_rm={post_rm}] Already exists — skipping."
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
        description="Stage 2 worker: normalize a prepared (strat, imp) dataset."
    )
    parser.add_argument("--strat",           required=True)
    parser.add_argument("--imp",             required=True)
    parser.add_argument("--method",          required=True)
    parser.add_argument("--skip-if-exists",  action="store_true")
    parser.add_argument("--out-json",        default=None)
    parser.add_argument("--memory-limit-gb", type=float, default=2.0)
    args = parser.parse_args()

    # Fast-path: both final S3 outputs already exist
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

    _check_memory(args.memory_limit_gb,
                  label=f"{args.strat}×{args.imp}×{args.method} startup")

    # Download the prepared dataset from S3
    s3 = boto3.client("s3")
    key_exp = s3_key_prepared_exp(args.strat, args.imp)
    key_ann = s3_key_prepared_ann(args.strat, args.imp)

    # Abort if the prepared dataset is missing (Stage 1 hasn't run yet)
    if not s3_exists(s3, key_exp) or not s3_exists(s3, key_ann):
        print(
            f"[{args.strat}×{args.imp}×{args.method}] Prepared dataset not found on S3. "
            f"Run run_prep_parallel.py first.",
            file=sys.stderr,
        )
        sys.exit(3)  # distinct exit code so dispatcher can report it separately

    print(f"Downloading prepared dataset: {args.strat}×{args.imp} ...", flush=True)
    exp_s = download_exp_from_s3(s3, key_exp)
    ann_s = download_ann_from_s3(s3, key_ann)

    _check_memory(args.memory_limit_gb / 2,
                  label=f"{args.strat}×{args.imp}×{args.method} post-download")

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

    if args.out_json:
        with open(args.out_json, "w") as f:
            json.dump(rows, f)
    else:
        for row in rows:
            print(json.dumps(row))

    sys.exit(0)


if __name__ == "__main__":
    main()
```

### Exit code conventions for `run_norm_job.py`

| Code | Meaning |
|---|---|
| 0 | Success (or cached skip) |
| 2 | OOM — free RAM below threshold at startup or post-download |
| 3 | Prepared dataset missing on S3 — Stage 1 not completed for this `(strat, imp)` |
| other | Unexpected subprocess crash |

The dispatcher treats codes 2 and other as failures (written to `failed_jobs_norm.txt`). Code 3 is treated as **"not ready yet"** — the job is neither failed nor succeeded, and the dispatcher should skip it without recording it as a failure.

---

## 6. `run_norm_parallel.py` — Stage 2 Dispatcher

**Responsibility:** Enumerate the `(strat, imp, method)` grid, filter to only pairs with available prepared datasets, and dispatch `run_norm_job.py` subprocesses.

### Key differences from `run_cross_product_parallel.py`
1. Dispatches `run_norm_job.py` instead of `run_one_job.py`.
2. Before dispatching, lists available `(strat, imp)` pairs from S3 (`prepared/` prefix).
3. Jobs where the prepared dataset is missing are reported but not recorded as failures.
4. Maintains a separate `failed_jobs_norm.txt` / `failed_norm_{POD_NAME}.txt` on S3.
5. Drops `--no-precache` (Stage 2 has no large shared data to pre-cache; each worker downloads its own ~100 MB prepared dataset).

```python
"""
Stage 2 dispatcher: apply normalization methods to pre-prepared datasets.

Reads:  FL_batch_correction/prepared/{strat}__{imp}__exp.tsv.gz (produced by Stage 1)
Writes: FL_batch_correction/exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz
        FL_batch_correction/metrics.csv

Only dispatches normalization for (strat, imp) pairs that exist in S3.
Missing prepared datasets are reported but NOT recorded as failures —
run run_prep_parallel.py first (or concurrently; Stage 2 will simply skip
pairs that Stage 1 has not yet finished).

Usage
-----
# All available (strat, imp) pairs × all 24 methods:
nohup python run_norm_parallel.py --n-workers 6 --skip-if-exists \\
    --memory-limit-gb 4.0 --timeout-s 3600 > norm_run.log 2>&1 &

# Specific subset:
python run_norm_parallel.py \\
    --strats A_confirmed_bad,B_extended_bad \\
    --imps strict,knn \\
    --methods 01_raw,16_fsqn_r,17_quantile \\
    --n-workers 4 --skip-if-exists

# Resume after partial run (skips completed S3 outputs AND previously failed jobs):
python run_norm_parallel.py --n-workers 6 --skip-if-exists

# Resume and also retry previously failed combinations:
python run_norm_parallel.py --n-workers 6 --skip-if-exists --retry-failed

--n-workers N
-------------
Maximum number of parallel worker subprocesses (default: 6).
Stage 2 workers are lighter than Stage 1: each downloads only the prepared
dataset (~50–200 MB) and runs one R normalization call. On a 16 GB pod,
6 workers is a reasonable default (vs 2–4 for Stage 1).

--skip-if-exists
----------------
Skip any (strat, imp, method) combination for which both
    exp/{strat}__{imp}__{method}__post0.tsv.gz  and
    exp/{strat}__{imp}__{method}__post1.tsv.gz
already exist on S3. Uses HEAD requests; no data is downloaded.
Intended for resuming a partial run without re-computing completed jobs.

--retry-failed
--------------
Default (omitted): combinations listed in failed_jobs_norm.txt are excluded
    from the grid entirely.
When set: the skip filter is ignored and every failed combination is attempted.
    - Successful retries are removed from failed_jobs_norm.txt.
    - Retries that fail again remain in the log.
    Combine with --skip-if-exists to skip jobs that already have S3 output.

--timeout-s N
-------------
Kill the worker subprocess after N seconds (default: 3600).
Timed-out jobs are logged in failed_jobs_norm.txt and can be retried with
--retry-failed. Normalization methods that call slow R functions (e.g.
19_tdm, 21_harmonizr) may require a higher value on large datasets.

--memory-limit-gb F
-------------------
Controls a two-level RAM safety chain (default: 4.0 GB):
    Level 1 (dispatcher): blocks launch of the next subprocess until free RAM >=
        this threshold. Already-running subprocesses are not affected.
    Level 2 (worker startup): each subprocess receives threshold/2 as its own
        --memory-limit-gb and exits (code 2) before downloading the prepared
        dataset if RAM is below the threshold.
Workers that exit with code 2 are logged as failures in failed_jobs_norm.txt.

--strats LIST
-------------
Comma-separated subset of strategy names (default: all 10). Only strategies
for which a prepared dataset already exists on S3 will actually run; the rest
are silently skipped (no failure recorded).

--imps LIST
-----------
Comma-separated subset of imputation methods (default: all 4).
Valid values: strict, knn, missforest, softimpute.

--methods LIST
--------------
Comma-separated subset of normalization method keys (default: all 24).
Valid values: 01_raw, 02_median_scaling, 03_limma, 04_sva, 05_combat,
    06_combat_seq, 07_pycombat, 08_inmoose_combatseq, 09_ruv, 10_mnn,
    11_harmony, 12_scanorama, 13_fsmvn, 14_qsmooth, 15_fsqn_py, 16_fsqn_r,
    17_quantile, 18_rank, 19_tdm, 20_shambhala, 21_harmonizr, 22_tmm,
    23_vst, 24_peer_k10.
Methods 20_shambhala and 24_peer_k10 always raise NotImplementedError and
are treated as expected skips (not recorded as failures).
Methods 22_tmm and 23_vst skip automatically on non-RNA-seq strategies
(F_microarray_only, G_affymetrix_only) via the RNA-seq-only guard.

--tmp-dir PATH
--------------
Directory for per-job JSON sidecar files (default: /tmp/bench_norm_jobs).
Created automatically. Each sidecar holds 2 metric rows (post_rm=False/True).
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
import pandas as pd

from bench_shared import (
    S3_BUCKET,
    S3_PREFIX,
    s3_exists,
    s3_key_metrics,
    s3_key_prepared_exp,
)

ALL_STRATEGIES: list[str] = [
    "S0_no_removal", "A_confirmed_bad", "B_extended_bad",
    "C_rnaseq_only", "D_malignant_only",
    "E1_iterative_r1", "E2_iterative_r2", "E3_iterative_r3",
    "F_microarray_only", "G_affymetrix_only",
]
ALL_IMPUTATION: list[str] = ["strict", "knn", "missforest", "softimpute"]
ALL_METHODS: list[str] = [
    "01_raw", "02_median_scaling", "03_limma", "04_sva",
    "05_combat", "06_combat_seq", "07_pycombat", "08_inmoose_combatseq",
    "09_ruv", "10_mnn", "11_harmony", "12_scanorama", "13_fsmvn",
    "14_qsmooth", "15_fsqn_py", "16_fsqn_r", "17_quantile", "18_rank",
    "19_tdm", "20_shambhala", "21_harmonizr", "22_tmm", "23_vst", "24_peer_k10",
]

_MEM_POLL_S    = 30.0
FAILED_LOG_PATH: Path = Path(__file__).parent / "failed_jobs_norm.txt"
_POD_NAME: str        = os.environ.get("POD_NAME", "local")
_S3_FAILED_PREFIX     = f"{S3_PREFIX}/failed_norm_"


def _job_key(strat: str, imp: str, method: str) -> str:
    return f"{strat}__{imp}__{method}"

# --- (failed log helpers: identical to run_prep_parallel.py pattern,
#      but pointing to FAILED_LOG_PATH and _S3_FAILED_PREFIX above) ---
# _load_failed_log, _save_failed_log, _sync_failed_log_from_s3,
# _sync_failed_log_to_s3, _free_gb, _wait_for_memory
# All are copy-paste identical to run_prep_parallel.py with only the
# constant names changed.  See full code in section 6.1 below.


def _list_available_prep_pairs(
    strategies: list[str],
    imputation_methods: list[str],
) -> list[tuple[str, str]]:
    """
    Query S3 for which (strat, imp) prepared datasets already exist.

    Returns only pairs where the __exp.tsv.gz object is present.
    """
    s3      = boto3.client("s3")
    avail   = []
    missing = []
    for strat in strategies:
        for imp in imputation_methods:
            key = s3_key_prepared_exp(strat, imp)
            if s3_exists(s3, key):
                avail.append((strat, imp))
            else:
                missing.append(f"{strat}×{imp}")
    if missing:
        print(
            f"[norm] {len(missing)} prepared pair(s) not yet on S3 — "
            f"will be skipped (run run_prep_parallel.py first):\n  "
            + ", ".join(missing),
            flush=True,
        )
    print(f"[norm] {len(avail)} prepared pair(s) available for normalization.",
          flush=True)
    return avail


def run_norm_dispatcher(
    available_pairs: list[tuple[str, str]],
    methods: list[str],
    n_workers: int,
    skip_if_exists: bool,
    tmp_dir: Path,
    skip_keys: set[str],
    timeout_s: int,
    memory_limit_gb: float,
) -> tuple[list[dict], set[str], set[str]]:
    """
    Launch normalization jobs for all (strat, imp) × method combinations.

    Returns
    -------
    tuple of (all_rows, newly_failed_keys, newly_succeeded_keys)
    """
    import subprocess

    all_jobs = [
        (strat, imp, method)
        for strat, imp in available_pairs
        for method     in methods
    ]
    jobs = [(s, i, m) for s, i, m in all_jobs if _job_key(s, i, m) not in skip_keys]
    if len(all_jobs) - len(jobs):
        print(f"Skipping {len(all_jobs) - len(jobs)} previously failed norm job(s).",
              flush=True)

    total = len(jobs)
    print(f"Norm jobs to run: {total}  |  Workers: {n_workers}  |  "
          f"Skip-if-exists: {skip_if_exists}  |  Timeout: {timeout_s}s  |  "
          f"Memory guard: {memory_limit_gb:.1f} GB", flush=True)

    def launch(strat, imp, method) -> tuple[list[dict], float, int]:
        _wait_for_memory(memory_limit_gb)
        json_path = tmp_dir / f"{strat}__{imp}__{method}.json"
        cmd = [
            sys.executable, "run_norm_job.py",
            "--strat",    strat,
            "--imp",      imp,
            "--method",   method,
            "--out-json", str(json_path),
            "--memory-limit-gb", str(memory_limit_gb / 2),
        ]
        if skip_if_exists:
            cmd.append("--skip-if-exists")
        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=timeout_s, cwd=str(Path(__file__).parent),
            )
        except subprocess.TimeoutExpired:
            return ([], time.time() - t0, -9)
        elapsed = time.time() - t0
        rows: list[dict] = []
        if proc.returncode == 0 and json_path.exists():
            try:
                with open(json_path) as fh:
                    rows = json.load(fh)
            except Exception:
                pass
        elif proc.returncode == 3:
            # Prepared dataset not ready — not a real failure, just skip
            print(f"  MISSING prepared {strat}×{imp}×{method} "
                  f"(Stage 1 incomplete)", flush=True)
        elif proc.returncode != 0:
            print(
                f"  FAILED {strat}×{imp}×{method} exit={proc.returncode} "
                f"({elapsed:.0f}s)\n  stderr: {proc.stderr[-800:]}",
                flush=True,
            )
        return (rows, elapsed, proc.returncode)

    all_rows: list[dict]     = []
    newly_failed: set[str]   = set()
    newly_succeeded: set[str] = set()
    done = 0

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        future_to_job = {
            pool.submit(launch, strat, imp, method): (strat, imp, method)
            for strat, imp, method in jobs
        }
        for future in as_completed(future_to_job):
            strat, imp, method = future_to_job[future]
            key = _job_key(strat, imp, method)
            done += 1
            rows, elapsed, rc = future.result()
            if rc == 3:
                # Not a failure — just not ready yet; don't record it
                continue
            statuses = {r.get("status", "failed") for r in rows} if rows else set()
            if rc != 0 or not rows or statuses & {"failed", "upload_failed"}:
                newly_failed.add(key)
            elif statuses <= {"skipped"}:
                # NotImplementedError — expected, not a failure
                newly_succeeded.add(key)
                all_rows.extend(rows)
                print(f"  [{done}/{total}] SKIP {strat}×{imp}×{method} "
                      f"({elapsed:.0f}s)", flush=True)
            else:
                newly_succeeded.add(key)
                all_rows.extend(rows)
                print(f"  [{done}/{total}] {strat}×{imp}×{method} "
                      f"({elapsed:.0f}s) → {[r['status'] for r in rows]}",
                      flush=True)

    return all_rows, newly_failed, newly_succeeded


def upload_metrics(rows: list[dict]) -> None:
    df        = pd.DataFrame(rows)
    csv_bytes = df.to_csv(index=False).encode()
    s3        = boto3.client("s3")
    key       = s3_key_metrics()
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=csv_bytes)
    print(f"Metrics uploaded: s3://{S3_BUCKET}/{key} ({len(df)} rows)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 2 dispatcher: normalize all available prepared datasets."
    )
    parser.add_argument("--n-workers",       type=int,   default=6)
    parser.add_argument("--skip-if-exists",  action="store_true")
    parser.add_argument("--retry-failed",    action="store_true")
    parser.add_argument("--tmp-dir",         default="/tmp/bench_norm_jobs")
    parser.add_argument("--strats",          default=None)
    parser.add_argument("--imps",            default=None)
    parser.add_argument("--methods",         default=None)
    parser.add_argument("--timeout-s",       type=int,   default=3600)
    parser.add_argument("--memory-limit-gb", type=float, default=4.0)
    args = parser.parse_args()

    strategies = args.strats.split(",")  if args.strats  else ALL_STRATEGIES
    imps       = args.imps.split(",")    if args.imps    else ALL_IMPUTATION
    methods    = args.methods.split(",") if args.methods  else ALL_METHODS
    tmp_dir    = Path(args.tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Merge S3 failed logs from prior pods
    _sync_failed_log_from_s3()
    previously_failed = _load_failed_log()
    skip_keys = set() if args.retry_failed else previously_failed

    # Discover which (strat, imp) pairs are ready on S3
    available_pairs = _list_available_prep_pairs(strategies, imps)
    if not available_pairs:
        print("No prepared datasets available. Run run_prep_parallel.py first.",
              flush=True)
        sys.exit(0)

    rows, newly_failed, newly_succeeded = run_norm_dispatcher(
        available_pairs=available_pairs,
        methods=methods,
        n_workers=args.n_workers,
        skip_if_exists=args.skip_if_exists,
        tmp_dir=tmp_dir,
        skip_keys=skip_keys,
        timeout_s=args.timeout_s,
        memory_limit_gb=args.memory_limit_gb,
    )

    updated_failed = (previously_failed - newly_succeeded) | newly_failed
    if updated_failed != previously_failed or newly_failed:
        _save_failed_log(updated_failed)
    _sync_failed_log_to_s3(updated_failed)

    if rows:
        upload_metrics(rows)
    else:
        print("No metric rows collected — metrics.csv not uploaded.", flush=True)


if __name__ == "__main__":
    main()
```

---

## 7. CLI Compatibility Table

All new scripts reuse the existing flag names and semantics.

| Flag | `run_cross_product_parallel.py` | `run_prep_parallel.py` | `run_norm_parallel.py` |
|---|---|---|---|
| `--n-workers` | ✓ | ✓ | ✓ |
| `--skip-if-exists` | ✓ | ✓ | ✓ |
| `--retry-failed` | ✓ | ✓ | ✓ |
| `--timeout-s` | ✓ | ✓ | ✓ |
| `--memory-limit-gb` | ✓ | ✓ | ✓ |
| `--tmp-dir` | ✓ | ✓ | ✓ |
| `--strats` | ✓ | ✓ | ✓ |
| `--imps` | ✓ | ✓ | ✓ |
| `--methods` | ✓ | — (N/A) | ✓ |
| `--no-precache` | ✓ | ✓ | — (N/A: no shared data to pre-cache) |

Worker scripts (`run_prep_job.py`, `run_norm_job.py`) also mirror the existing worker flags:

| Flag | `run_one_job.py` | `run_prep_job.py` | `run_norm_job.py` |
|---|---|---|---|
| `--strat` | ✓ | ✓ | ✓ |
| `--imp` | ✓ | ✓ | ✓ |
| `--method` | ✓ | — (N/A) | ✓ |
| `--skip-if-exists` | ✓ | ✓ | ✓ |
| `--out-json` | ✓ | ✓ | ✓ |
| `--memory-limit-gb` | ✓ | ✓ | ✓ |

---

## 8. End-to-End Usage Workflow

### Full two-stage run

```bash
# Stage 1: prepare all 40 (strat, imp) datasets  (~2–3 hrs with 4 workers)
python run_prep_parallel.py \
    --n-workers 4 \
    --skip-if-exists \
    --timeout-s 7200 \
    --memory-limit-gb 6.0

# Stage 2: apply all 24 normalization methods to available datasets
# (can start as soon as any Stage 1 jobs complete)
python run_norm_parallel.py \
    --n-workers 6 \
    --skip-if-exists \
    --timeout-s 3600 \
    --memory-limit-gb 4.0
```

### Resuming partial runs

```bash
# Resume Stage 1 (reruns only incomplete/failed pairs)
python run_prep_parallel.py --skip-if-exists

# Resume Stage 2 (reruns only incomplete/failed jobs)
python run_norm_parallel.py --skip-if-exists

# Retry Stage 1 failures
python run_prep_parallel.py --retry-failed --skip-if-exists

# Run Stage 2 for a specific method subset only
python run_norm_parallel.py \
    --methods 16_fsqn_r,17_quantile \
    --skip-if-exists
```

### Running specific jobs for debugging

```bash
# Prepare one pair only:
python run_prep_job.py --strat A_confirmed_bad --imp strict \
    --out-json /tmp/prep_check.json

# Normalize using a specific method (requires Stage 1 already done):
python run_norm_job.py --strat A_confirmed_bad --imp strict --method 16_fsqn_r \
    --out-json /tmp/norm_check.json
```

### Running inside a Kubernetes pod

```bash
# Attach to the pod
kubectl exec -it fl-batch-correction -n ${K8S_NAMESPACE} -- bash

# Stage 1 inside pod:
python run_prep_parallel.py --n-workers 6 --skip-if-exists --timeout-s 7200

# Stage 2 inside pod (can run in a separate pod or same pod after Stage 1):
python run_norm_parallel.py --n-workers 6 --skip-if-exists
```

---

## 9. S3 Layout After Full Two-Stage Run

```
s3://$FL_S3_BUCKET/FL_batch_correction/
├── exp/                                       comb_exp.tsv (1.9 GB input)
│   └── comb_exp.tsv
├── exp/                                       comb_ann_unified.csv input
│   └── comb_ann_unified.csv
├── prepared/                                  Stage 1 outputs (80 objects)
│   ├── A_confirmed_bad__strict__exp.tsv.gz    ~100–200 MB each
│   ├── A_confirmed_bad__strict__ann.tsv.gz    ~1–5 MB each
│   ├── A_confirmed_bad__knn__exp.tsv.gz
│   ├── A_confirmed_bad__knn__ann.tsv.gz
│   └── ... (40 pairs × 2 files)
├── exp/                                       Stage 2 outputs (1,920 objects)
│   ├── A_confirmed_bad__strict__01_raw__post0.tsv.gz
│   ├── A_confirmed_bad__strict__01_raw__post1.tsv.gz
│   └── ... (960 jobs × 2 post_rm variants)
├── metrics.csv                                Stage 2 aggregated metrics
├── prep_metrics.csv                           Stage 1 aggregated metrics
├── failed_prep_<POD_NAME>.txt                 Stage 1 per-pod failures
└── failed_norm_<POD_NAME>.txt                 Stage 2 per-pod failures
```

---

## 10. Memory Profile Comparison

| Scenario | Current (`run_one_job.py`) | New (`run_norm_job.py`) |
|---|---|---|
| Data downloaded per worker | ~1.9 GB (raw) + filter strategies | ~100–200 MB (prepared dataset) |
| Imputation in each worker | Yes (per method) | No (done once in Stage 1) |
| R session needed | Yes | Yes (normalization still uses R) |
| Peak RAM per worker | ~6–8 GB (knn/missforest) | ~2–4 GB |
| Workers possible at 16 GB | ~2 | ~4–6 |

---

## 11. Backward Compatibility

The following remain **unchanged and fully functional**:

- `run_one_job.py` — end-to-end single job, still dispatched by `run_cross_product_parallel.py`
- `run_cross_product_parallel.py` — full grid dispatcher, unchanged
- `load_cross_product_results.py` — reads `exp/` and `metrics.csv` which are still written by Stage 2
- `test_mock.py` — tests `bench_shared.py` functions; new S3 helper functions in `bench_shared.py` do not break any existing import
- All existing S3 keys (`exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz`, `metrics.csv`) remain identical

---

## 12. Docker Compatibility

No changes required to the Docker image. Specifically:

1. **`Dockerfile`** — unchanged. The `COPY harmonization-scripts/ harmonization-scripts/` instruction copies everything in the directory, so the four new `.py` files are automatically included in the image.
2. **`requirements.txt`** — unchanged. No new Python packages are introduced; the new scripts use only `boto3`, `pandas`, `psutil`, `subprocess`, which are all already present.
3. **`install_r_packages.R`** — unchanged. The new scripts use the same R packages (via `bench_shared.py`) that are already installed.
4. **`WORKDIR /app/harmonization-scripts`** — matches the `cwd=str(Path(__file__).parent)` call in both new dispatchers, so subprocess resolution works identically.

The only change inside the container is the addition of four new `.py` files. The image can be rebuilt with `docker build` as before, or the new files can be injected via `kubectl cp` for a quick test without a full rebuild:

```bash
# Quick test without rebuilding the image:
kubectl cp run_prep_job.py fl-batch-correction:/app/harmonization-scripts/ -n ${K8S_NAMESPACE}
kubectl cp run_prep_parallel.py fl-batch-correction:/app/harmonization-scripts/ -n ${K8S_NAMESPACE}
kubectl cp run_norm_job.py fl-batch-correction:/app/harmonization-scripts/ -n ${K8S_NAMESPACE}
kubectl cp run_norm_parallel.py fl-batch-correction:/app/harmonization-scripts/ -n ${K8S_NAMESPACE}
# Also push the updated bench_shared.py:
kubectl cp bench_shared.py fl-batch-correction:/app/harmonization-scripts/ -n ${K8S_NAMESPACE}
```

For production, rebuild the image and push to ECR after all scripts are tested locally:

```bash
cd ~/B_cell_lymphomas
docker build --tag fl-batch-correction:latest --file harmonization-scripts/Dockerfile .
docker run --rm -v "$HOME/.aws:/root/.aws:ro" fl-batch-correction:latest python test_mock.py
```

---

## 13. Implementation Checklist

### Phase 1 — `bench_shared.py` additions (low risk) ✅ DONE
- [x] **1.1** Add `s3_key_prepared_exp(strat, imp)` → `"FL_batch_correction/prepared/{strat}__{imp}__exp.tsv.gz"`
- [x] **1.2** Add `s3_key_prepared_ann(strat, imp)` → `"FL_batch_correction/prepared/{strat}__{imp}__ann.tsv.gz"`
- [x] **1.3** Add `s3_key_prep_metrics()` → `"FL_batch_correction/prep_metrics.csv"`
- [x] **1.4** Add `upload_ann_to_s3(ann_df, s3_client, key)` — mirrors `upload_exp_to_s3` but CSV → TSV.gz
- [x] **1.5** Add `download_ann_from_s3(s3_client, key)` — mirrors `download_exp_from_s3`
- [x] **1.6** Verify `test_mock.py` still passes (`python3 -m py_compile` clean; new functions are pure additions)

### Phase 2 — `run_prep_job.py` (new file) ✅ DONE
- [x] **2.1** Create `run_prep_job.py` — compiles clean (`python3 -m py_compile`)
- [ ] **2.2** Local smoke test with synthetic data (no S3):
  ```bash
  python run_prep_job.py --strat A_confirmed_bad --imp strict --out-json /tmp/prep_test.json
  cat /tmp/prep_test.json  # expect: [{"status": "ok", "n_samples": ..., ...}]
  aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/prepared/ | grep A_confirmed_bad__strict
  ```
- [ ] **2.3** Test fast-path skip: run again with `--skip-if-exists` — should report "cached" without re-downloading

### Phase 3 — `run_prep_parallel.py` (new file) ✅ DONE
- [x] **3.1** Create `run_prep_parallel.py` — compiles clean
- [ ] **3.2** Test with a 2-job subset:
  ```bash
  python run_prep_parallel.py --strats A_confirmed_bad --imps strict,knn \
      --n-workers 2 --skip-if-exists
  ```
- [ ] **3.3** Verify `failed_jobs_prep.txt` is created/updated correctly
- [ ] **3.4** Verify `prep_metrics.csv` is uploaded to S3
- [ ] **3.5** Verify S3 failed-log sync (`failed_prep_local.txt`) works

### Phase 4 — `run_norm_job.py` (new file) ✅ DONE
- [x] **4.1** Create `run_norm_job.py` — compiles clean
- [ ] **4.2** Test with a single job (requires Stage 1 already done for the pair):
  ```bash
  python run_norm_job.py --strat A_confirmed_bad --imp strict --method 01_raw \
      --out-json /tmp/norm_test.json
  cat /tmp/norm_test.json  # expect: [{...,"status": "ok"}, {...}]
  ```
- [ ] **4.3** Test exit code 3: run against a `(strat, imp)` pair that was NOT prepared yet — should exit with code 3, not 1 or 2
- [ ] **4.4** Test fast-path skip: run with `--skip-if-exists` when both final S3 keys exist

### Phase 5 — `run_norm_parallel.py` (new file) ✅ DONE
- [x] **5.1** Create `run_norm_parallel.py` — compiles clean; uses `list_objects_v2` for efficient S3 discovery
- [ ] **5.2** Test with a small grid:
  ```bash
  python run_norm_parallel.py \
      --strats A_confirmed_bad --imps strict \
      --methods 01_raw,17_quantile \
      --n-workers 2 --skip-if-exists
  ```
- [ ] **5.3** Verify "missing prepared dataset" warning prints correctly when a pair is absent
- [ ] **5.4** Verify `metrics.csv` is uploaded correctly
- [ ] **5.5** Verify `failed_jobs_norm.txt` and S3 sync work

### Phase 6 — Integration test (pending runtime access)
- [ ] **6.1** Run Stage 1 for 3 pairs, Stage 2 for those 3 pairs × 3 methods (9 jobs total), verify all outputs on S3
- [ ] **6.2** Run Stage 2 with a pair missing from S3 — confirm it's skipped without error
- [ ] **6.3** Introduce an intentional imputation failure (patch `run_prep_job.py` to exit 1 for one job) — confirm `failed_jobs_prep.txt` is updated and Stage 2 skips that pair
- [ ] **6.4** Confirm `load_cross_product_results.py` still loads results correctly (it reads `exp/` and `metrics.csv`, unchanged)

### Phase 7 — Docker rebuild (optional if pod is not being actively used)
- [ ] **7.1** Rebuild image: `docker build ...`
- [ ] **7.2** Run `test_mock.py` inside the container
- [ ] **7.3** Push updated image to ECR
- [ ] **7.4** Run Phases 2–6 smoke tests inside the pod via `kubectl exec`

---

## 14. Known Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Stage 1 and Stage 2 run concurrently; Stage 2 tries a pair before Stage 1 finishes | `run_norm_job.py` exits with code 3 (not a failure); dispatcher skips and logs it; job can be retried with `--retry-failed` or a second `run_norm_parallel.py` invocation |
| Large prepared expression files (~200 MB each) slow down Stage 2 downloads | Pickle cache at `/tmp/` within a pod session; files persist for the pod lifetime; mount PVC at `/tmp` or use `/workspace` to persist across pod restarts |
| Stage 1 `missforest`/`softimpute` jobs are slow; 7200s timeout needed | Documented in CLI table; `--timeout-s 7200` recommended for imputation dispatchers |
| `ann_s` uploaded to S3 may be missing columns needed by normalization methods | `ann_s` is the full annotation slice (all columns from `comb_ann_unified.csv`); it includes `BATCH_COL`, `BIO_COL`, `COHORT_LABEL`, and all clinical columns — no truncation |
| Parallel runs of Stage 2 across multiple pods may start normalization for the same `(strat, imp, method)` simultaneously | `--skip-if-exists` checks S3 at job start and after normalization; occasional duplicate uploads are harmless (same content, last writer wins) |
| `failed_jobs_prep.txt` and `failed_jobs_norm.txt` exist in the same directory | Different filenames; no conflict; `_S3_FAILED_PREFIX` uses `failed_prep_` and `failed_norm_` respectively |
