"""
Dispatcher: launches all (strategy × imputation × method) jobs as subprocesses.

Uses ThreadPoolExecutor so only n_workers threads (and subprocesses) exist at once —
unlike the old semaphore approach that created all 960 threads simultaneously.

Memory safety features:
- Pre-cached data is freed from the dispatcher after writing to disk.
- A psutil-based guard pauses dispatch when free RAM < --memory-limit-gb.
- Subprocesses are killed after --timeout-s seconds to prevent hangs.
- Workers exit early (code 2) if they start with insufficient free RAM.

Failed-job tracking:
- After every run a file 'failed_jobs.txt' is written next to this script.
  Each line holds one job key in the form  strat__imp__method.
  Jobs that fail due to a subprocess crash, timeout, OOM exit, normalization
  exception, or S3 upload error are added to this file.
  Jobs that raise NotImplementedError (RNA-seq-only methods on mixed data)
  are treated as expected skips and are NOT recorded as failures.
- On the next run the file is read and, by default, all previously failed
  combinations are skipped so the run focuses on new or untried jobs.
- Pass --retry-failed to override this behaviour and attempt every failed
  combination again. Successful retries are removed from the file; retries
  that fail again remain recorded.

Collects metric JSON sidecars from each job and uploads a single metrics.csv to S3.

Usage
-----
# Full run (default 2 workers):
nohup python run_cross_product_parallel.py --n-workers 2 --skip-if-exists \\
    --memory-limit-gb 6.0 --timeout-s 3600 > bench_run.log 2>&1 &

# Test with 3 jobs:
python run_cross_product_parallel.py --n-workers 2 \\
    --strats A_confirmed_bad --imps strict --methods 01_raw,02_median_scaling,17_quantile

# Resume after partial run (skips completed S3 outputs AND previously failed jobs):
python run_cross_product_parallel.py --n-workers 2 --skip-if-exists

# Resume and also retry previously failed combinations:
python run_cross_product_parallel.py --n-workers 2 --skip-if-exists --retry-failed

# Inspect which jobs are recorded as failed without running anything:
cat harmonization-scripts/failed_jobs.txt

--retry-failed details
----------------------
Default (omitted): jobs listed in failed_jobs.txt are excluded from the run
    grid entirely. Use this when you want to focus the run on jobs that have
    not been attempted yet or that succeeded previously.

When set (--retry-failed): the failed_jobs.txt list is ignored when building
    the run grid, so every failed combination is attempted again.
    - If a retry succeeds (status ok/cached/skipped), the key is removed from
      failed_jobs.txt.
    - If a retry fails again, the key stays in failed_jobs.txt.
    Combine with --skip-if-exists to avoid re-running jobs that already have
    S3 output from a previous partial run.

--timeout-s details
-------------------
Kills the worker subprocess after this many seconds (per job). Jobs killed by
timeout are logged as failures in failed_jobs.txt and can be retried with
--retry-failed. Increase this value when using slow imputation methods such as
missforest or softimpute (recommend --timeout-s 7200 for those).

--memory-limit-gb details
-------------------------
Controls a three-level RAM safety chain:
  Level 1 (dispatcher): blocks launch of the next subprocess until free RAM >=
      this threshold. Already-running subprocesses are not affected.
  Level 2 (worker startup): each subprocess receives threshold/2 as its own
      --memory-limit-gb and exits (code 2) before loading data if RAM is below.
  Level 3 (worker post-load): worker checks threshold/4 after load_data()
      completes and exits if headroom is too low.
Workers that exit with code 2 are logged as failures in failed_jobs.txt.
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
    s3_key_metrics,
)



# ── Full grid ─────────────────────────────────────────────────────────────────
ALL_STRATEGIES: list[str] = [
    "S0_no_removal",
    "A_confirmed_bad",
    "B_extended_bad",
    "C_rnaseq_only",
    "D_malignant_only",
    "E1_iterative_r1",
    "E2_iterative_r2",
    "E3_iterative_r3",
    "F_microarray_only",
    "G_affymetrix_only",
    "H_affymetrix_extended",
    "I_rare_batches_removed",
    "J_ff_only",
    "K_ffpe_only",
]
ALL_IMPUTATION: list[str] = ["strict", "knn", "missforest", "softimpute"]
ALL_METHODS: list[str] = [
    "01_raw", "02_median_scaling", "03_limma", "04_sva",
    "05_combat", "06_combat_seq", "07_pycombat", "08_inmoose_combatseq",
    "09_ruv", "10_mnn", "11_harmony", "12_scanorama", "13_fsmvn",
    "14_qsmooth", "15_fsqn_py", "16_fsqn_r", "17_quantile", "18_rank",
    "19_tdm", "20_shambhala", "21_harmonizr", "22_tmm", "23_vst", "24_peer_k10",
    "25_angel", "26_xpn", "27_dwd", "28_npn", "29_combat_ref", "30_recombat",
    "31_ruv3prps", "32_deepmnn", "33_amdbnorm", "34_arsyn", "35_dasc",
    "36_explobatch", "37_fabatch", "38_harman", "39_procrustes",
]

_MEM_POLL_S = 30.0  # seconds between memory-guard polls

# Path to the persistent failed-jobs log (lives next to this script)
FAILED_LOG_PATH: Path = Path(__file__).parent / "failed_jobs.txt"

# Each pod writes its own S3 object so there are no write conflicts.
# On startup every pod reads ALL failed_jobs_*.txt objects and merges them.
_POD_NAME: str = os.environ.get("POD_NAME", "local")
_S3_FAILED_PREFIX: str = f"{S3_PREFIX}/failed_jobs_"


# ── Failed-job log helpers ────────────────────────────────────────────────────

def _job_key(strat: str, imp: str, method: str) -> str:
    """Canonical string key for one (strat, imp, method) combination."""
    return f"{strat}__{imp}__{method}"


def _load_failed_log() -> set[str]:
    """
    Read the failed-jobs log and return a set of job keys.

    Returns
    -------
    Set of job key strings, or an empty set if the log does not exist.
    """
    if not FAILED_LOG_PATH.exists():
        return set()
    with open(FAILED_LOG_PATH) as fh:
        return {line.strip() for line in fh if line.strip()}


def _save_failed_log(keys: set[str]) -> None:
    """
    Overwrite the failed-jobs log with the given set of keys (sorted).

    Parameters
    ----------
    keys
        Set of job key strings to persist.
    """
    with open(FAILED_LOG_PATH, "w") as fh:
        for key in sorted(keys):
            fh.write(key + "\n")
    print(
        f"Failed-jobs log written: {FAILED_LOG_PATH} "
        f"({len(keys)} entr{'y' if len(keys) == 1 else 'ies'})",
        flush=True,
    )


def _sync_failed_log_from_s3() -> None:
    """
    Download every failed_jobs_*.txt object from S3 and merge its keys into
    the local FAILED_LOG_PATH.  Covers failures recorded by all previous pods,
    not only the current one.  Safe to call when no S3 objects exist yet.
    """
    import boto3
    import botocore.exceptions

    s3 = boto3.client("s3")
    try:
        paginator = s3.get_paginator("list_objects_v2")
        s3_keys: set[str] = set()
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=_S3_FAILED_PREFIX):
            for obj in page.get("Contents", []):
                body = s3.get_object(
                    Bucket=S3_BUCKET, Key=obj["Key"]
                )["Body"].read().decode()
                s3_keys |= {ln.strip() for ln in body.splitlines() if ln.strip()}
        if s3_keys:
            local_keys = _load_failed_log()
            merged = s3_keys | local_keys
            if merged != local_keys:
                _save_failed_log(merged)
                print(
                    f"[S3 sync] Merged {len(s3_keys)} S3 keys with "
                    f"{len(local_keys)} local → {len(merged)} total.",
                    flush=True,
                )
    except botocore.exceptions.ClientError as exc:
        print(f"[S3 sync] Could not read failed_jobs from S3: {exc}", flush=True)


def _sync_failed_log_to_s3(keys: set[str]) -> None:
    """
    Upload this pod's failed-job keys to its own S3 object.
    Deletes the object when keys is empty (clean run).

    Parameters
    ----------
    keys
        Full set of failed job keys after this run.
    """
    import boto3

    s3  = boto3.client("s3")
    key = f"{_S3_FAILED_PREFIX}{_POD_NAME}.txt"
    if keys:
        body = "\n".join(sorted(keys)).encode()
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=body)
        print(
            f"[S3 sync] Uploaded {len(keys)} failed keys to "
            f"s3://{S3_BUCKET}/{key}",
            flush=True,
        )
    else:
        try:
            s3.delete_object(Bucket=S3_BUCKET, Key=key)
            print(
                f"[S3 sync] Cleared s3://{S3_BUCKET}/{key} (no failures).",
                flush=True,
            )
        except Exception:
            pass


def _classify_job_outcome(
    rc: int,
    rows: list[dict],
) -> str:
    """
    Classify a completed job as 'failed', 'skipped', or 'ok'.

    'skipped' means NotImplementedError (RNA-seq-only method on mixed data) —
    this is expected behaviour and should NOT be recorded as a failure.
    'failed'  means subprocess crash, timeout, OOM, normalization exception, or
              S3 upload error — should be recorded in failed_jobs.txt.
    'ok'      means all rows have status ok / cached / skipped.

    Parameters
    ----------
    rc
        Subprocess return code (-9 = timeout sentinel, 2 = OOM exit).
    rows
        Metric row dicts from the JSON sidecar; may be empty on crash/timeout.

    Returns
    -------
    One of 'failed', 'skipped', 'ok'.
    """
    if rc != 0:
        return "failed"
    if not rows:
        # rc == 0 but no JSON produced — treat as failure
        return "failed"
    statuses = {r.get("status", "failed") for r in rows}
    if statuses <= {"skipped"}:
        # All rows are NotImplementedError skips — not a real failure
        return "skipped"
    if statuses & {"failed", "upload_failed"}:
        return "failed"
    return "ok"


# ── Memory helpers ────────────────────────────────────────────────────────────

def _free_gb() -> float:
    """Return available RAM in GB, or a large number if psutil is missing."""
    try:
        import psutil
        return psutil.virtual_memory().available / 1e9
    except ImportError:
        return 999.0


def _wait_for_memory(min_free_gb: float) -> None:
    """Block the calling thread until system free RAM >= min_free_gb."""
    while True:
        free = _free_gb()
        if free >= min_free_gb:
            return
        print(
            f"  [mem-guard] {free:.1f} GB free < {min_free_gb:.1f} GB threshold — "
            f"pausing {_MEM_POLL_S:.0f}s before next launch",
            flush=True,
        )
        time.sleep(_MEM_POLL_S)


# ── Dispatcher ────────────────────────────────────────────────────────────────

def run_dispatcher(
    strategies: list[str],
    imputation_methods: list[str],
    methods: list[str],
    n_workers: int,
    skip_if_exists: bool,
    tmp_dir: Path,
    skip_keys: set[str],
    timeout_s: int = 3600,
    memory_limit_gb: float = 4.0,
) -> tuple[list[dict], set[str], set[str]]:
    """
    Launch all jobs as subprocesses, at most n_workers running concurrently.

    Uses ThreadPoolExecutor — only n_workers threads exist at any time, avoiding
    the per-thread overhead of creating all jobs as threads up front.

    Parameters
    ----------
    strategies
        Filter strategy names to include.
    imputation_methods
        Imputation methods to include.
    methods
        Normalization method keys to include.
    n_workers
        Maximum parallel subprocesses.
    skip_if_exists
        Pass --skip-if-exists to each worker.
    tmp_dir
        Directory for JSON sidecar files.
    skip_keys
        Job keys to skip entirely (previously failed jobs when --retry-failed
        is not set). Pass an empty set to run all jobs.
    timeout_s
        Kill subprocess if it runs longer than this many seconds.
    memory_limit_gb
        Pause dispatch when free RAM drops below this threshold (GB).

    Returns
    -------
    tuple of (all_rows, newly_failed_keys, newly_succeeded_keys)
        all_rows            : metric row dicts from all completed workers
        newly_failed_keys   : job keys that failed in this run
        newly_succeeded_keys: job keys that completed without error this run
    """
    import subprocess

    all_jobs = [
        (strat, imp, method)
        for strat  in strategies
        for imp    in imputation_methods
        for method in methods
    ]

    # Apply the failed-log skip filter
    if skip_keys:
        jobs = [(s, i, m) for s, i, m in all_jobs if _job_key(s, i, m) not in skip_keys]
        n_skipped_failed = len(all_jobs) - len(jobs)
        if n_skipped_failed:
            print(
                f"Skipping {n_skipped_failed} previously failed job(s) "
                f"(pass --retry-failed to attempt them again).",
                flush=True,
            )
    else:
        jobs = all_jobs

    total = len(jobs)
    print(
        f"Total jobs to run: {total}  |  Workers: {n_workers}  |  "
        f"Skip-if-exists: {skip_if_exists}  |  "
        f"Timeout: {timeout_s}s  |  "
        f"Memory guard: {memory_limit_gb:.1f} GB",
        flush=True,
    )

    def launch(strat: str, imp: str, method: str) -> tuple[list[dict], float, int]:
        """Run one job as a subprocess; return (rows, elapsed_s, returncode)."""
        _wait_for_memory(memory_limit_gb)
        json_path = tmp_dir / f"{strat}__{imp}__{method}.json"
        cmd = [
            sys.executable, "run_one_job.py",
            "--strat",    strat,
            "--imp",      imp,
            "--method",   method,
            "--out-json", str(json_path),
            "--memory-limit-gb", str(memory_limit_gb / 2),  # worker gets half the threshold
        ]
        if skip_if_exists:
            cmd.append("--skip-if-exists")

        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                cwd=str(Path(__file__).parent),
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
            print(
                f"  FAILED {strat}×{imp}×{method} "
                f"exit={proc.returncode} ({elapsed:.0f}s)\n"
                f"  stderr: {proc.stderr[-800:]}",
                flush=True,
            )
        return (rows, elapsed, proc.returncode)

    all_rows: list[dict] = []
    newly_failed: set[str] = set()
    newly_succeeded: set[str] = set()
    done = 0
    failed_cnt = 0

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        future_to_job = {
            pool.submit(launch, strat, imp, method): (strat, imp, method)
            for strat, imp, method in jobs
        }
        for future in as_completed(future_to_job):
            strat, imp, method = future_to_job[future]
            key = _job_key(strat, imp, method)
            done += 1
            try:
                rows, elapsed, rc = future.result()
            except Exception as exc:
                print(f"  [{done}/{total}] EXCEPTION {strat}×{imp}×{method}: {exc}", flush=True)
                failed_cnt += 1
                newly_failed.add(key)
                continue

            outcome = _classify_job_outcome(rc, rows)

            if outcome == "failed":
                failed_cnt += 1
                newly_failed.add(key)
                code_desc = "timeout" if rc == -9 else f"exit={rc}"
                print(
                    f"  [{done}/{total}] FAILED {strat}×{imp}×{method} "
                    f"{code_desc} ({elapsed:.0f}s)",
                    flush=True,
                )
            else:
                # outcome is 'ok' or 'skipped' — not a failure
                newly_succeeded.add(key)
                if rows:
                    statuses = [r["status"] for r in rows]
                    all_rows.extend(rows)
                    print(
                        f"  [{done}/{total}] {strat}×{imp}×{method} "
                        f"({elapsed:.0f}s) → {statuses}",
                        flush=True,
                    )
                else:
                    print(
                        f"  [{done}/{total}] {strat}×{imp}×{method} "
                        f"({elapsed:.0f}s) — no JSON sidecar",
                        flush=True,
                    )

    print(
        f"\nDispatcher done. {done}/{total} jobs run. "
        f"{failed_cnt} failures this run.",
        flush=True,
    )
    return all_rows, newly_failed, newly_succeeded


def upload_metrics(rows: list[dict]) -> None:
    """
    Upload aggregated metrics CSV to S3.

    Parameters
    ----------
    rows
        List of metric row dicts from all workers.
    """
    df        = pd.DataFrame(rows)
    csv_bytes = df.to_csv(index=False).encode()
    s3        = boto3.client("s3")
    key       = s3_key_metrics()
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=csv_bytes)
    print(f"Metrics uploaded: s3://{S3_BUCKET}/{key} ({len(df)} rows)")
    ok_count     = (df["status"] == "ok").sum()
    skip_count   = (df["status"] == "skipped").sum()
    fail_count   = (df["status"] == "failed").sum()
    cached_count = (df["status"] == "cached").sum()
    print(f"  ok={ok_count}  skipped={skip_count}  failed={fail_count}  cached={cached_count}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dispatch harmonization cross-product as parallel subprocesses."
    )
    parser.add_argument("--n-workers",       type=int,   default=2,
                        help="Max parallel subprocesses (default: 2; increase only if RAM allows)")
    parser.add_argument("--skip-if-exists",  action="store_true",
                        help="Skip jobs whose S3 output already exists (for resuming)")
    parser.add_argument("--retry-failed",    action="store_true",
                        help=(
                            "Retry combinations listed in failed_jobs.txt instead of skipping "
                            "them. Successful retries are removed from the log; retries that "
                            "fail again remain. Default: False (failed jobs are skipped)."
                        ))
    parser.add_argument("--tmp-dir",         default="/tmp/bench_jobs",
                        help="Directory for JSON sidecar files (default: /tmp/bench_jobs)")
    parser.add_argument("--strats",          default=None,
                        help="Comma-separated subset of strategies (default: all 14)")
    parser.add_argument("--imps",            default=None,
                        help="Comma-separated subset of imputation methods (default: all 4)")
    parser.add_argument("--methods",         default=None,
                        help="Comma-separated subset of normalization methods (default: all 24)")
    parser.add_argument("--no-precache",     action="store_true",
                        help="Skip pre-caching data and filter strategies in dispatcher")
    parser.add_argument("--timeout-s",       type=int,   default=3600,
                        help=(
                            "Kill worker subprocess after this many seconds (default: 3600). "
                            "Timed-out jobs are recorded in failed_jobs.txt. Use --timeout-s 7200 "
                            "with missforest or softimpute imputation."
                        ))
    parser.add_argument("--memory-limit-gb", type=float, default=4.0,
                        help=(
                            "Dispatcher pauses new launches when free RAM drops below this value "
                            "(GB, default: 4.0). Workers receive half this value as their own "
                            "startup guard. Workers that exit due to low RAM are recorded in "
                            "failed_jobs.txt."
                        ))
    args = parser.parse_args()

    strategies = args.strats.split(",")  if args.strats  else ALL_STRATEGIES
    imps       = args.imps.split(",")    if args.imps    else ALL_IMPUTATION
    methods    = args.methods.split(",") if args.methods  else ALL_METHODS

    tmp_dir = Path(args.tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # ── Load failed-jobs log (merge with all previous pods' S3 records) ─────────
    _sync_failed_log_from_s3()
    previously_failed = _load_failed_log()
    if previously_failed:
        print(
            f"Failed-jobs log: {len(previously_failed)} previously failed combination(s) "
            f"found in {FAILED_LOG_PATH}.",
            flush=True,
        )
        if args.retry_failed:
            print("  --retry-failed set: all failed combinations will be attempted.", flush=True)
            skip_keys: set[str] = set()
        else:
            print(
                "  Skipping them (pass --retry-failed to attempt again).",
                flush=True,
            )
            skip_keys = previously_failed
    else:
        skip_keys = set()

    # ── Pre-cache data ────────────────────────────────────────────────────────
    if not args.no_precache:
        print("Pre-caching dataset and filter strategies (workers will reuse cache)...")
        t0 = time.time()
        comb_exp, comb_ann = load_data()
        build_filter_strategies(comb_ann, comb_exp)
        print(f"Cache ready ({time.time() - t0:.0f}s). Freeing dispatcher copies...")
        del comb_exp, comb_ann
        gc.collect()
        print(f"Dispatcher memory freed. Free RAM: {_free_gb():.1f} GB. Launching workers...")

    # ── Run jobs ──────────────────────────────────────────────────────────────
    rows, newly_failed, newly_succeeded = run_dispatcher(
        strategies=strategies,
        imputation_methods=imps,
        methods=methods,
        n_workers=args.n_workers,
        skip_if_exists=args.skip_if_exists,
        tmp_dir=tmp_dir,
        skip_keys=skip_keys,
        timeout_s=args.timeout_s,
        memory_limit_gb=args.memory_limit_gb,
    )

    # ── Update failed-jobs log ────────────────────────────────────────────────
    # Remove jobs that succeeded this run; add jobs that failed this run.
    updated_failed = (previously_failed - newly_succeeded) | newly_failed
    if updated_failed != previously_failed or newly_failed:
        _save_failed_log(updated_failed)
        if newly_failed:
            print(
                f"  Newly failed this run ({len(newly_failed)}): "
                + ", ".join(sorted(newly_failed)),
                flush=True,
            )
        removed = previously_failed & newly_succeeded
        if removed:
            print(
                f"  Removed from failed log ({len(removed)} recovered): "
                + ", ".join(sorted(removed)),
                flush=True,
            )
    _sync_failed_log_to_s3(updated_failed)

    # ── Upload metrics ────────────────────────────────────────────────────────
    if rows:
        upload_metrics(rows)
    else:
        print("No metric rows collected — metrics.csv not uploaded.")


if __name__ == "__main__":
    main()
