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
Comma-separated subset of strategy names to run (default: all 14).
Valid values: S0_no_removal, A_confirmed_bad, B_extended_bad, C_rnaseq_only,
    D_malignant_only, E1_iterative_r1, E2_iterative_r2, E3_iterative_r3,
    F_microarray_only, G_affymetrix_only, H_affymetrix_extended,
    I_rare_batches_removed, J_ff_only, K_ffpe_only.

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
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
import botocore.exceptions
import pandas as pd

from bench_shared import (
    S3_BUCKET,
    S3_PREFIX,
    build_filter_strategies,
    load_data,
    s3_key_prep_metrics,
)

ALL_STRATEGIES: list[str] = [
    "S0_no_removal", "A_confirmed_bad", "B_extended_bad",
    "C_rnaseq_only", "D_malignant_only",
    "E1_iterative_r1", "E2_iterative_r2", "E3_iterative_r3",
    "F_microarray_only", "G_affymetrix_only", "H_affymetrix_extended",
    "I_rare_batches_removed", "J_ff_only", "K_ffpe_only",
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
    print(
        f"Prep failed-jobs log written: {FAILED_LOG_PATH} ({len(keys)} entries)",
        flush=True,
    )


def _sync_failed_log_from_s3() -> None:
    s3 = boto3.client("s3")
    try:
        paginator = s3.get_paginator("list_objects_v2")
        s3_keys: set[str] = set()
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=_S3_FAILED_PREFIX):
            for obj in page.get("Contents", []):
                body = (
                    s3.get_object(Bucket=S3_BUCKET, Key=obj["Key"])["Body"]
                    .read()
                    .decode()
                )
                s3_keys |= {ln.strip() for ln in body.splitlines() if ln.strip()}
        if s3_keys:
            local_keys = _load_failed_log()
            merged = s3_keys | local_keys
            if merged != local_keys:
                _save_failed_log(merged)
                print(
                    f"[S3 sync] Merged {len(s3_keys)} prep S3 keys → {len(merged)} total.",
                    flush=True,
                )
    except botocore.exceptions.ClientError as exc:
        print(f"[S3 sync] Could not read prep failed_jobs from S3: {exc}", flush=True)


def _sync_failed_log_to_s3(keys: set[str]) -> None:
    s3  = boto3.client("s3")
    key = f"{_S3_FAILED_PREFIX}{_POD_NAME}.txt"
    if keys:
        body = "\n".join(sorted(keys)).encode()
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=body)
        print(
            f"[S3 sync] Uploaded {len(keys)} prep failed keys to "
            f"s3://{S3_BUCKET}/{key}",
            flush=True,
        )
    else:
        try:
            s3.delete_object(Bucket=S3_BUCKET, Key=key)
        except Exception:
            pass


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


def _stream_and_forward(pipe: object, prefix: str) -> None:
    """Forward lines from a subprocess pipe to stdout with a job prefix."""
    for line in pipe:  # type: ignore[union-attr]
        print(f"  [{prefix}] {line}", end="", flush=True)


def _wait_for_memory(min_free_gb: float) -> None:
    while True:
        if _free_gb() >= min_free_gb:
            return
        print(
            f"  [mem-guard] {_free_gb():.1f} GB free — pausing {_MEM_POLL_S:.0f}s",
            flush=True,
        )
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

    Parameters
    ----------
    strategies
        Strategy names to process.
    imputation_methods
        Imputation method names to process.
    n_workers
        Maximum number of parallel subprocesses.
    skip_if_exists
        Forward --skip-if-exists to each worker.
    tmp_dir
        Directory for per-job JSON sidecar files.
    skip_keys
        Set of job keys to skip entirely (previously failed).
    timeout_s
        Worker timeout in seconds.
    memory_limit_gb
        Dispatcher-level memory guard; workers receive threshold/2.

    Returns
    -------
    Tuple of (all_rows, newly_failed_keys, newly_succeeded_keys).
    """
    jobs = [
        (strat, imp)
        for strat in strategies
        for imp   in imputation_methods
        if _job_key(strat, imp) not in skip_keys
    ]
    n_skipped = (len(strategies) * len(imputation_methods)) - len(jobs)
    if n_skipped:
        print(
            f"Skipping {n_skipped} previously failed prep job(s) "
            f"(pass --retry-failed to attempt again).",
            flush=True,
        )

    total = len(jobs)
    print(
        f"Prep jobs to run: {total}  |  Workers: {n_workers}  |  "
        f"Skip-if-exists: {skip_if_exists}  |  Timeout: {timeout_s}s  |  "
        f"Memory guard: {memory_limit_gb:.1f} GB",
        flush=True,
    )

    def launch(strat: str, imp: str) -> tuple[list[dict], float, int]:
        _wait_for_memory(memory_limit_gb)
        tag = f"{strat}×{imp}"
        t0 = time.time()
        print(
            f"[{_ts()}] START {tag} | free={_free_gb():.1f}GB",
            flush=True,
        )
        json_path = tmp_dir / f"{strat}__{imp}.json"
        cmd = [
            sys.executable, "run_prep_job.py",
            "--strat",   strat,
            "--imp",     imp,
            "--out-json", str(json_path),
            "--memory-limit-gb", str(memory_limit_gb / 2),
        ]
        if skip_if_exists:
            cmd.append("--skip-if-exists")
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(Path(__file__).parent),
            )
            reader = threading.Thread(
                target=_stream_and_forward,
                args=(proc.stdout, tag),
                daemon=True,
            )
            reader.start()
            try:
                proc.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                proc.kill()
                reader.join(timeout=5)
                elapsed = time.time() - t0
                print(
                    f"[{_ts()}] TIMEOUT {tag} after {elapsed:.0f}s",
                    flush=True,
                )
                return ([], elapsed, -9)
            reader.join(timeout=5)
        except Exception as exc:
            elapsed = time.time() - t0
            print(f"[{_ts()}] ERROR {tag}: {exc}", flush=True)
            return ([], elapsed, -1)
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
                f"[{_ts()}] FAILED {tag} exit={proc.returncode} ({elapsed:.0f}s)",
                flush=True,
            )
        return (rows, elapsed, proc.returncode)

    all_rows: list[dict]      = []
    newly_failed: set[str]    = set()
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
                print(
                    f"  [{done}/{total}] FAILED {strat}×{imp} "
                    f"({'timeout' if rc == -9 else f'exit={rc}'}) ({elapsed:.0f}s)",
                    flush=True,
                )
            else:
                newly_succeeded.add(key)
                all_rows.extend(rows)
                print(
                    f"  [{done}/{total}] {strat}×{imp} ({elapsed:.0f}s) → {statuses}",
                    flush=True,
                )

    return all_rows, newly_failed, newly_succeeded


def upload_prep_metrics(rows: list[dict]) -> None:
    df        = pd.DataFrame(rows)
    csv_bytes = df.to_csv(index=False).encode()
    s3        = boto3.client("s3")
    key       = s3_key_prep_metrics()
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=csv_bytes)
    print(f"Prep metrics uploaded: s3://{S3_BUCKET}/{key} ({len(df)} rows)")


def main() -> None:
    signal.signal(
        signal.SIGTERM,
        lambda signum, frame: (
            print("\n[dispatcher] SIGTERM — syncing failed-jobs log to S3.", flush=True),
            _sync_failed_log_to_s3(_load_failed_log()),
            sys.exit(0),
        )[-1],
    )

    parser = argparse.ArgumentParser(
        description="Stage 1 dispatcher: prepare (strat × imp) datasets in parallel."
    )
    parser.add_argument("--n-workers",       type=int,   default=4)
    parser.add_argument("--skip-if-exists",  action="store_true")
    parser.add_argument("--retry-failed",    action="store_true")
    parser.add_argument("--tmp-dir",         default="/tmp/bench_prep_jobs")
    parser.add_argument("--strats",          default=None,
                        help="Comma-separated strategy subset (default: all 14)")
    parser.add_argument("--imps",            default=None,
                        help="Comma-separated imputation subset (default: all 4)")
    parser.add_argument("--no-precache",     action="store_true")
    parser.add_argument("--timeout-s",       type=int,   default=3600,
                        help="Worker timeout in seconds (use 7200 for missforest/softimpute)")
    parser.add_argument("--memory-limit-gb", type=float, default=4.0)
    args = parser.parse_args()

    strategies = [s.strip("/").strip() for s in args.strats.split(",")] if args.strats else ALL_STRATEGIES
    imps       = [i.strip("/").strip() for i in args.imps.split(",")]   if args.imps   else ALL_IMPUTATION
    tmp_dir    = Path(args.tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    _sync_failed_log_from_s3()
    previously_failed = _load_failed_log()
    skip_keys = set() if args.retry_failed else previously_failed

    if not args.no_precache:
        print("Pre-caching raw dataset and filter strategies...", flush=True)
        t0 = time.time()
        comb_exp, comb_ann = load_data()
        build_filter_strategies(comb_ann, comb_exp)
        print(
            f"Cache ready ({time.time() - t0:.0f}s). Freeing dispatcher copies...",
            flush=True,
        )
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
