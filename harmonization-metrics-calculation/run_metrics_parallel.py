"""
run_metrics_parallel.py — Dispatcher: launch metrics jobs for all expression files.

Reads:   FL_batch_correction/exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz  (list only)
Writes:  FL_batch_correction/metrics/{key}_metrics.json  (via run_metrics_job.py workers)

Usage
-----
# Full run (post0 only, fast mode):
nohup python run_metrics_parallel.py \\
    --n-workers 4 --skip-if-exists --skip-slow \\
    --post-rm-filter post0 > /workspace/metrics_fast.log 2>&1 &

# Targeted subset:
python run_metrics_parallel.py \\
    --strats A_confirmed_bad --imps strict \\
    --methods 01_raw,16_fsqn_r \\
    --post-rm-filter post0 --skip-slow --n-workers 2

# Blind final check (groups L, M, N) over every attempt that already has a sidecar.
# Do NOT pass --skip-if-exists here: every target job has a sidecar already, so it
# would skip all of them. The incremental sentinel logic inside the worker is what
# provides the resume behaviour — it recomputes only the groups that are missing.
# Set --n-workers to roughly (vCPU - 8) on whatever node is provisioned.
# n_perm=100 timed out every job at 3600s on 2026-08-23 — root cause was BLAS/OpenMP
# thread fan-out (48 threads/process x 20 processes on a 32-core cgroup quota), now
# pinned to 1 thread inside run_metrics_job.py itself; n_perm=20 is kept as a cheap
# additional safety margin (p-value floor 1/(n_perm+1) stays under 0.05). See
# group_n_timeout_and_reference_race_fix_plan_260823.md for the full diagnosis.
nohup python run_metrics_parallel.py \\
    --groups L,M,N --only-with-metrics --skip-shambhala \\
    --n-workers 20 --memory-limit-gb 8.0 --timeout-s 3600 \\
    --n-perm 20 --ref-cache-dir /workspace/ref_cache \\
    > /workspace/metrics_lmn.log 2>&1 &

# Force-recompute Group N only, with a higher n_perm, on attempts that already have a
# Group N result (e.g. rerun with more permutations for finer p-value resolution after
# the initial n_perm=20 pass). Groups A-M in each sidecar are left untouched.
nohup python run_metrics_parallel.py \\
    --groups N --force-groups N --only-with-metrics --skip-shambhala \\
    --n-workers 20 --memory-limit-gb 8.0 --timeout-s 3600 \\
    --n-perm 200 \\
    > /workspace/metrics_n_reforce.log 2>&1 &

# Resume after failure:
python run_metrics_parallel.py --n-workers 4 --skip-if-exists --retry-failed

--n-workers N
    Maximum number of parallel worker subprocesses (default: 4).

--skip-if-exists
    Skip jobs whose metrics JSON sidecar already exists on S3.

--retry-failed
    Retry jobs listed in failed_jobs_metrics.txt instead of skipping them.

--post-rm-filter {post0, post1, both}
    Which post_rm variant to process (default: both).

--skip-slow
    Skip variancePartition (Group F) in each worker.

--memory-limit-gb F
    Dispatcher-level RAM guard before launching each subprocess (default: 6.0 GB).
    Workers receive half this threshold as their own guard.

--timeout-s N
    Kill worker subprocess after N seconds (default: 600; use 3600 for full mode,
    1800 for a groups L,M,N run).

--skip-shambhala
    Drop Shambhala methods. Shambhala is excluded from Article 1, so this selects the
    2,323 non-Shambhala attempts out of the 3,835 on S3.

--only-with-metrics
    Restrict the job list to attempts that already have a metrics sidecar. Used to add
    new metric groups to completed jobs.

--ref-cache-dir PATH
    Local cache for the 01_raw reference matrices, needed by Group L only
    (default: /workspace/ref_cache). 42 (strat, imp) pairs, ~12.8 GB.

--n-perm N
    Label permutations for the Group N negative control (worker default: 20).

--force-groups LIST
    Comma-separated metric groups to recompute even if already present in a job's
    sidecar (bypasses the incremental sentinel check for these letters only). Use to
    rerun a group with different parameters, e.g. Group N with a new --n-perm. Forces
    those letters into the requested set automatically, whether or not they are also
    listed in --groups.

--save-gene-cohort-detail
    Upload the full Group L gene x cohort correlation matrix per job to
    marker_corr/. Off by default: ~300 KB per job.

--panel-groups LIST
    Comma-separated gene_group filter for Groups L and M (see marker_gene_annotation.csv).

--strats LIST
    Comma-separated list of strategy names to process (default: all found on S3).

--imps LIST
    Comma-separated list of imputation methods (default: all found on S3).

--methods LIST
    Comma-separated list of normalization methods (default: all found on S3).

--file-list PATH
    Path to a plain-text file containing one S3 key per line.
    If given, --strats/--imps/--methods filters are ignored.

--tmp-dir PATH
    Directory for per-job JSON sidecar files (default: /tmp/bench_metrics_jobs).
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import boto3
import botocore.exceptions

sys.path.insert(0, str(Path(__file__).parent))
from compute_batch_metrics import S3_BUCKET, S3_PREFIX

_MEM_POLL_S = 30.0
FAILED_LOG = Path(__file__).parent / "failed_jobs_metrics.txt"
_POD_NAME: str = os.environ.get("POD_NAME", "local")
_S3_FAILED_PFX = f"{S3_PREFIX}/failed_metrics_"


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def _free_gb() -> float:
    def _read_int(path: str) -> Optional[int]:
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


def _wait_for_memory(min_gb: float) -> None:
    while _free_gb() < min_gb:
        print(
            f"  [mem-guard] {_free_gb():.1f} GB free — pausing {_MEM_POLL_S:.0f}s",
            flush=True,
        )
        time.sleep(_MEM_POLL_S)


def _load_failed() -> set[str]:
    if not FAILED_LOG.exists():
        return set()
    return {ln.strip() for ln in FAILED_LOG.read_text().splitlines() if ln.strip()}


def _save_failed(keys: set[str]) -> None:
    FAILED_LOG.write_text("\n".join(sorted(keys)) + "\n" if keys else "")
    print(f"Failed-jobs log: {FAILED_LOG} ({len(keys)} entries)", flush=True)


def _sync_failed_from_s3() -> None:
    s3 = boto3.client("s3")
    try:
        paginator = s3.get_paginator("list_objects_v2")
        s3_keys: set[str] = set()
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=_S3_FAILED_PFX):
            for obj in page.get("Contents", []):
                body = (
                    s3.get_object(Bucket=S3_BUCKET, Key=obj["Key"])["Body"]
                    .read()
                    .decode()
                )
                s3_keys |= {ln.strip() for ln in body.splitlines() if ln.strip()}
        if s3_keys:
            merged = s3_keys | _load_failed()
            _save_failed(merged)
    except botocore.exceptions.ClientError as e:
        print(f"[S3 sync] Could not read failed_metrics from S3: {e}", flush=True)


def _sync_failed_to_s3(keys: set[str]) -> None:
    s3 = boto3.client("s3")
    key = f"{_S3_FAILED_PFX}{_POD_NAME}.txt"
    if keys:
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body="\n".join(sorted(keys)).encode())
    else:
        try:
            s3.delete_object(Bucket=S3_BUCKET, Key=key)
        except Exception:
            pass


def _job_key(strat: str, imp: str, method: str, post_rm: bool) -> str:
    pm = "post0" if not post_rm else "post1"
    return f"{strat}__{imp}__{method}__{pm}"


def _list_metrics_job_keys() -> set[str]:
    """Job keys ({strat}__{imp}__{method}__post{0|1}) that already have a sidecar."""
    s3 = boto3.client("s3")
    keys: set[str] = set()
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=f"{S3_PREFIX}/metrics/"):
        for obj in page.get("Contents", []):
            name = Path(obj["Key"]).name
            if name.endswith("_metrics.json"):
                keys.add(name[: -len("_metrics.json")])
    return keys


def _list_exp_files(
    strats: Optional[list[str]],
    imps: Optional[list[str]],
    methods: Optional[list[str]],
    post_rm_filter: str,
    skip_shambhala: bool = False,
    only_with_metrics: bool = False,
) -> list[tuple[str, str, str, bool]]:
    """List expression files on S3 and return (strat, imp, method, post_rm) tuples."""
    s3 = boto3.client("s3")
    prefix = f"{S3_PREFIX}/exp/"
    keys: list[str] = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            k = obj["Key"]
            if k.endswith(".tsv.gz"):
                keys.append(k)

    with_metrics = _list_metrics_job_keys() if only_with_metrics else set()
    if only_with_metrics:
        print(
            f"[dispatcher] {len(with_metrics)} attempts already have a metrics sidecar.",
            flush=True,
        )

    jobs: list[tuple[str, str, str, bool]] = []
    for key in keys:
        fname = Path(key).name  # e.g. A_confirmed_bad__strict__16_fsqn_r__post0.tsv.gz
        if not fname.endswith(".tsv.gz"):
            continue
        stem = fname[: -len(".tsv.gz")]
        parts = stem.split("__")
        if len(parts) != 4:
            continue
        strat, imp, method, pm_tag = parts
        if pm_tag == "post0":
            post_rm = False
        elif pm_tag == "post1":
            post_rm = True
        else:
            continue

        if strats and strat not in strats:
            continue
        if imps and imp not in imps:
            continue
        if methods and method not in methods:
            continue
        if post_rm_filter == "post0" and post_rm:
            continue
        if post_rm_filter == "post1" and not post_rm:
            continue
        if skip_shambhala and method.startswith("shambhala"):
            continue
        if only_with_metrics and stem not in with_metrics:
            continue

        jobs.append((strat, imp, method, post_rm))

    print(
        f"[dispatcher] Found {len(jobs)} expression files matching filters.", flush=True
    )
    return jobs


def _stream_forward(pipe: object, prefix: str) -> None:
    for line in pipe:  # type: ignore[union-attr]
        print(f"  [{prefix}] {line}", end="", flush=True)


def run_dispatcher(
    jobs: list[tuple[str, str, str, bool]],
    skip_keys: set[str],
    skip_if_exists: bool,
    skip_slow: bool,
    n_workers: int,
    timeout_s: int,
    memory_limit_gb: float,
    tmp_dir: Path,
    groups: Optional[str] = None,
    force_groups: Optional[str] = None,
    skip_wm: bool = False,
    ref_cache_dir: Optional[str] = None,
    n_perm: Optional[int] = None,
    save_gene_cohort_detail: bool = False,
    panel_groups: Optional[str] = None,
) -> tuple[set[str], set[str]]:
    """
    Launch metric workers for all jobs.

    Returns
    -------
    tuple of (newly_failed_keys, newly_succeeded_keys)
    """
    todo = [
        (s, i, m, p) for s, i, m, p in jobs if _job_key(s, i, m, p) not in skip_keys
    ]
    if len(jobs) - len(todo):
        print(f"Skipping {len(jobs)-len(todo)} previously failed jobs.", flush=True)

    total = len(todo)
    print(
        f"Metrics jobs to run: {total}  |  Workers: {n_workers}  |  "
        f"Timeout: {timeout_s}s  |  Memory guard: {memory_limit_gb:.1f} GB",
        flush=True,
    )

    def launch(
        strat: str, imp: str, method: str, post_rm: bool
    ) -> tuple[str, float, int]:
        _wait_for_memory(memory_limit_gb)
        tag = _job_key(strat, imp, method, post_rm)
        t0 = time.time()
        print(f"[{_ts()}] START {tag} | free={_free_gb():.1f}GB", flush=True)

        pm_tag = "False" if not post_rm else "True"
        json_path = tmp_dir / f"{tag}.json"
        genes_path = tmp_dir / f"{tag}_genes.json"
        cmd = [
            sys.executable,
            "run_metrics_job.py",
            "--strat",
            strat,
            "--imp",
            imp,
            "--method",
            method,
            "--post-rm",
            pm_tag,
            "--out-json",
            str(json_path),
            "--out-genes-json",
            str(genes_path),
            "--memory-limit-gb",
            str(memory_limit_gb / 2),
        ]
        if skip_if_exists:
            cmd.append("--skip-if-exists")
        if skip_slow:
            cmd.append("--skip-slow")
        if skip_wm:
            cmd.extend(["--skip-wm", "True"])
        if groups:
            cmd.extend(["--groups", groups])
        if force_groups:
            cmd.extend(["--force-groups", force_groups])
        if ref_cache_dir:
            cmd.extend(["--ref-cache-dir", ref_cache_dir])
        if n_perm is not None:
            cmd.extend(["--n-perm", str(n_perm)])
        if save_gene_cohort_detail:
            cmd.append("--save-gene-cohort-detail")
        if panel_groups:
            cmd.extend(["--panel-groups", panel_groups])

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(Path(__file__).parent),
            )
            reader = threading.Thread(
                target=_stream_forward, args=(proc.stdout, tag), daemon=True
            )
            reader.start()
            try:
                proc.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                proc.kill()
                reader.join(timeout=5)
                elapsed = time.time() - t0
                print(f"[{_ts()}] TIMEOUT {tag} after {elapsed:.0f}s", flush=True)
                return (tag, elapsed, -9)
            reader.join(timeout=5)
        except Exception as exc:
            elapsed = time.time() - t0
            print(f"[{_ts()}] ERROR {tag}: {exc}", flush=True)
            return (tag, elapsed, -1)

        elapsed = time.time() - t0
        return (tag, elapsed, proc.returncode)

    newly_failed: set[str] = set()
    newly_succeeded: set[str] = set()
    done = 0

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        future_map = {
            pool.submit(launch, s, i, m, p): _job_key(s, i, m, p) for s, i, m, p in todo
        }
        for future in as_completed(future_map):
            tag = future_map[future]
            tag_r, elapsed, rc = future.result()
            done += 1
            if rc in (3,):
                # Source file not on S3 — not a failure of the metrics job itself
                print(f"  [{done}/{total}] MISSING source for {tag}", flush=True)
                continue
            if rc == 0:
                newly_succeeded.add(tag)
                print(f"  [{done}/{total}] DONE {tag} ({elapsed:.0f}s)", flush=True)
            else:
                newly_failed.add(tag)
                print(
                    f"  [{done}/{total}] FAILED {tag} rc={rc} ({elapsed:.0f}s)",
                    flush=True,
                )

    return newly_failed, newly_succeeded


def main() -> None:
    signal.signal(
        signal.SIGTERM,
        lambda *_: (
            print("\n[dispatcher] SIGTERM — syncing failed-jobs log.", flush=True),
            _sync_failed_to_s3(_load_failed()),
            sys.exit(0),
        )[-1],
    )

    parser = argparse.ArgumentParser(
        description="Dispatcher: compute metrics for all harmonized expression files."
    )
    parser.add_argument("--n-workers", type=int, default=4)
    parser.add_argument("--skip-if-exists", action="store_true")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument(
        "--post-rm-filter", choices=["post0", "post1", "both"], default="both"
    )
    parser.add_argument("--skip-slow", action="store_true")
    parser.add_argument(
        "--skip-wm",
        action="store_true",
        help="Skip WaterMelon score (Group I) in each worker.",
    )
    parser.add_argument("--memory-limit-gb", type=float, default=6.0)
    parser.add_argument("--timeout-s", type=int, default=600)
    parser.add_argument("--strats", default=None)
    parser.add_argument("--imps", default=None)
    parser.add_argument("--methods", default=None)
    parser.add_argument("--file-list", default=None)
    parser.add_argument("--tmp-dir", default="/tmp/bench_metrics_jobs")
    parser.add_argument(
        "--groups",
        default=None,
        help="Comma-separated metric groups to compute (e.g. A,B,E). "
        "Valid: A B C D E F G H I J K L M N. Default: all groups.",
    )
    parser.add_argument(
        "--force-groups",
        default=None,
        help=(
            "Comma-separated metric groups to recompute even if already present in "
            "a job's sidecar (bypasses the incremental sentinel check for these "
            "letters only). Forwarded to run_metrics_job.py's --force-groups."
        ),
    )
    parser.add_argument(
        "--skip-shambhala",
        action="store_true",
        help="Drop Shambhala methods (excluded from Article 1).",
    )
    parser.add_argument(
        "--only-with-metrics",
        action="store_true",
        help="Restrict to attempts that already have a metrics sidecar on S3.",
    )
    parser.add_argument(
        "--ref-cache-dir",
        default="/workspace/ref_cache",
        help="Local cache for the 01_raw reference matrices (Group L only).",
    )
    parser.add_argument(
        "--n-perm",
        type=int,
        default=None,
        help="Label permutations for the Group N control (worker default: 20).",
    )
    parser.add_argument(
        "--save-gene-cohort-detail",
        action="store_true",
        help="Upload the full Group L gene x cohort matrix per job.",
    )
    parser.add_argument(
        "--panel-groups",
        default=None,
        help="Comma-separated gene_group filter for Groups L and M.",
    )
    args = parser.parse_args()

    tmp_dir = Path(args.tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    _sync_failed_from_s3()
    prev_failed = _load_failed()
    skip_keys = set() if args.retry_failed else prev_failed

    if args.file_list:
        file_list = Path(args.file_list).read_text().splitlines()
        jobs: list[tuple[str, str, str, bool]] = []
        for line in file_list:
            line = line.strip()
            if not line:
                continue
            fname = Path(line).name
            stem = fname[: -len(".tsv.gz")] if fname.endswith(".tsv.gz") else fname
            parts = stem.split("__")
            if len(parts) != 4:
                continue
            strat, imp, method, pm_tag = parts
            post_rm = pm_tag == "post1"
            jobs.append((strat, imp, method, post_rm))
    else:
        strats = args.strats.split(",") if args.strats else None
        imps = args.imps.split(",") if args.imps else None
        methods = args.methods.split(",") if args.methods else None
        jobs = _list_exp_files(
            strats,
            imps,
            methods,
            args.post_rm_filter,
            skip_shambhala=args.skip_shambhala,
            only_with_metrics=args.only_with_metrics,
        )

    if not jobs:
        print("No jobs found. Check S3 prefix or --file-list.", flush=True)
        sys.exit(0)

    newly_failed, newly_succeeded = run_dispatcher(
        jobs=jobs,
        skip_keys=skip_keys,
        skip_if_exists=args.skip_if_exists,
        skip_slow=args.skip_slow,
        n_workers=args.n_workers,
        timeout_s=args.timeout_s,
        memory_limit_gb=args.memory_limit_gb,
        tmp_dir=tmp_dir,
        groups=args.groups,
        force_groups=args.force_groups,
        skip_wm=args.skip_wm,
        ref_cache_dir=args.ref_cache_dir,
        n_perm=args.n_perm,
        save_gene_cohort_detail=args.save_gene_cohort_detail,
        panel_groups=args.panel_groups,
    )

    updated_failed = (prev_failed - newly_succeeded) | newly_failed
    if updated_failed != prev_failed or newly_failed:
        _save_failed(updated_failed)
    _sync_failed_to_s3(updated_failed)

    n_ok = len(newly_succeeded)
    n_fail = len(newly_failed)
    print(f"\n[dispatcher] Done: {n_ok} succeeded, {n_fail} failed.", flush=True)


if __name__ == "__main__":
    main()
