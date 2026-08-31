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
Comma-separated subset of strategy names (default: all 14). Only strategies
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
    23_vst, 24_peer_k10, 25_angel, 26_xpn, 27_dwd, 28_npn, 29_combat_ref,
    30_recombat, 31_ruv3prps, 32_deepmnn, 33_amdbnorm, 34_arsyn, 35_dasc,
    36_explobatch, 37_fabatch, 38_harman, 39_procrustes.
Methods 24_peer_k10, 32_deepmnn, and 35_dasc always raise NotImplementedError
and are expected skips (not recorded as failures). Method 20_shambhala requires
Octave to be installed. Methods 22_tmm, 23_vst, and 39_procrustes skip
automatically on non-RNA-seq strategies via the RNA-seq-only guard.

--tmp-dir PATH
--------------
Directory for per-job JSON sidecar files (default: /tmp/bench_norm_jobs).
Created automatically. Each sidecar holds 2 metric rows (post_rm=False/True).
"""
from __future__ import annotations

import argparse
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
    s3_key_metrics,
    s3_key_prepared_exp,
)

ALL_STRATEGIES: list[str] = [
    "S0_no_removal", "A_confirmed_bad", "B_extended_bad",
    "C_rnaseq_only", "D_malignant_only",
    "E1_iterative_r1", "E2_iterative_r2", "E3_iterative_r3",
    "F_microarray_only", "G_affymetrix_only", "H_affymetrix_extended",
    "I_rare_batches_removed", "J_ff_only", "K_ffpe_only",
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

_MEM_POLL_S    = 30.0
FAILED_LOG_PATH: Path = Path(__file__).parent / "failed_jobs_norm.txt"
_POD_NAME: str        = os.environ.get("POD_NAME", "local")
_S3_FAILED_PREFIX     = f"{S3_PREFIX}/failed_norm_"


def _job_key(strat: str, imp: str, method: str) -> str:
    return f"{strat}__{imp}__{method}"


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
        f"Norm failed-jobs log written: {FAILED_LOG_PATH} ({len(keys)} entries)",
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
                    f"[S3 sync] Merged {len(s3_keys)} norm S3 keys → {len(merged)} total.",
                    flush=True,
                )
    except botocore.exceptions.ClientError as exc:
        print(f"[S3 sync] Could not read norm failed_jobs from S3: {exc}", flush=True)


def _sync_failed_log_to_s3(keys: set[str]) -> None:
    s3  = boto3.client("s3")
    key = f"{_S3_FAILED_PREFIX}{_POD_NAME}.txt"
    if keys:
        body = "\n".join(sorted(keys)).encode()
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=body)
        print(
            f"[S3 sync] Uploaded {len(keys)} norm failed keys to "
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


def _list_available_prep_pairs(
    strategies: list[str],
    imputation_methods: list[str],
) -> list[tuple[str, str]]:
    """
    Query S3 once with list_objects_v2 to find which (strat, imp) prepared
    datasets already exist, then filter to the requested (strategies, imps) subset.

    Returns only pairs where the __exp.tsv.gz object is present.
    """
    s3     = boto3.client("s3")
    prefix = f"{S3_PREFIX}/prepared/"

    existing_keys: set[str] = set()
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            existing_keys.add(obj["Key"])

    avail   = []
    missing = []
    for strat in strategies:
        for imp in imputation_methods:
            key = s3_key_prepared_exp(strat, imp)
            if key in existing_keys:
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
    print(
        f"[norm] {len(avail)} prepared pair(s) available for normalization.",
        flush=True,
    )
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

    Parameters
    ----------
    available_pairs
        (strat, imp) pairs confirmed present on S3.
    methods
        Normalization method keys to run.
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
    all_jobs = [
        (strat, imp, method)
        for strat, imp in available_pairs
        for method     in methods
    ]
    jobs = [(s, i, m) for s, i, m in all_jobs if _job_key(s, i, m) not in skip_keys]
    if len(all_jobs) - len(jobs):
        print(
            f"Skipping {len(all_jobs) - len(jobs)} previously failed norm job(s).",
            flush=True,
        )

    total = len(jobs)
    print(
        f"Norm jobs to run: {total}  |  Workers: {n_workers}  |  "
        f"Skip-if-exists: {skip_if_exists}  |  Timeout: {timeout_s}s  |  "
        f"Memory guard: {memory_limit_gb:.1f} GB",
        flush=True,
    )

    def launch(strat: str, imp: str, method: str) -> tuple[list[dict], float, int]:
        _wait_for_memory(memory_limit_gb)
        tag = f"{strat}×{imp}×{method}"
        t0 = time.time()
        print(
            f"[{_ts()}] START {tag} | free={_free_gb():.1f}GB",
            flush=True,
        )
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
        elif proc.returncode == 3:
            print(
                f"[{_ts()}] MISSING prepared {strat}×{imp} for {method} "
                f"(Stage 1 incomplete)",
                flush=True,
            )
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
            pool.submit(launch, strat, imp, method): (strat, imp, method)
            for strat, imp, method in jobs
        }
        for future in as_completed(future_to_job):
            strat, imp, method = future_to_job[future]
            key = _job_key(strat, imp, method)
            done += 1
            rows, elapsed, rc = future.result()
            if rc == 3:
                continue
            statuses = {r.get("status", "failed") for r in rows} if rows else set()
            if rc != 0 or not rows or statuses & {"failed", "upload_failed"}:
                newly_failed.add(key)
            elif statuses <= {"skipped"}:
                newly_succeeded.add(key)
                all_rows.extend(rows)
                print(
                    f"  [{done}/{total}] SKIP {strat}×{imp}×{method} ({elapsed:.0f}s)",
                    flush=True,
                )
            else:
                newly_succeeded.add(key)
                all_rows.extend(rows)
                print(
                    f"  [{done}/{total}] {strat}×{imp}×{method} "
                    f"({elapsed:.0f}s) → {[r['status'] for r in rows]}",
                    flush=True,
                )

    return all_rows, newly_failed, newly_succeeded


def upload_metrics(rows: list[dict]) -> None:
    df        = pd.DataFrame(rows)
    csv_bytes = df.to_csv(index=False).encode()
    s3        = boto3.client("s3")
    key       = s3_key_metrics()
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=csv_bytes)
    print(f"Metrics uploaded: s3://{S3_BUCKET}/{key} ({len(df)} rows)")


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
    methods    = args.methods.split(",") if args.methods else ALL_METHODS
    tmp_dir    = Path(args.tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    _sync_failed_log_from_s3()
    previously_failed = _load_failed_log()
    skip_keys = set() if args.retry_failed else previously_failed

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
