"""
run_gene_corr_parallel.py — Dispatcher for the gene x gene correlation + QC run.

Enumerates expression files on S3 and launches one run_gene_corr_job.py subprocess per
attempt through a ThreadPoolExecutor, with the same memory guard, timeout and
failed-job tracking as run_metrics_parallel.py. The failed-job file has its own name so
a gene-correlation run and a metrics run can share a pod without corrupting each
other's resume state.

Analysis scope
--------------
The Shambhala cross-product is excluded from Article 1, but its default variant
shambhala_P0std_Q0std is kept and appears as 20_shambhala in the analysis notebooks.
--shambhala-mode default-only encodes exactly that and is the default here; the
metrics dispatcher's --skip-shambhala would drop it, so that flag is not carried over.

Usage
-----
# Production: 1,204 jobs (non-Shambhala + shambhala_P0std_Q0std, post0 only)
nohup python run_gene_corr_parallel.py \\
    --only-with-metrics --shambhala-mode default-only --post-rm-filter post0 \\
    --n-workers 20 --memory-limit-gb 8.0 --timeout-s 1200 \\
    > /workspace/gene_corr.log 2>&1 &

# Count the jobs a set of filters selects, without running anything
python run_gene_corr_parallel.py --only-with-metrics --post-rm-filter post0 --dry-run

# Targeted subset
python run_gene_corr_parallel.py --strats C_rnaseq_only --imps softimpute \\
    --methods 01_raw,04_sva,10_mnn --post-rm-filter post0 --n-workers 3
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

sys.path.insert(0, str(Path(__file__).parent.parent))
from compute_batch_metrics import S3_BUCKET, S3_PREFIX

_MEM_POLL_S = 30.0
FAILED_LOG = Path(__file__).parent / "failed_jobs_gene_corr.txt"
_POD_NAME: str = os.environ.get("POD_NAME", "local")
_S3_FAILED_PFX = f"{S3_PREFIX}/failed_gene_corr_"

# The one Shambhala variant that stays in the analysis; renamed 20_shambhala in
# harmonization_metrics_analysis_v3.ipynb and in the deep-analysis notebook.
SHAMBHALA_DEFAULT_METHOD = "shambhala_P0std_Q0std"


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
            _save_failed(s3_keys | _load_failed())
    except botocore.exceptions.ClientError as e:
        print(f"[S3 sync] Could not read failed_gene_corr from S3: {e}", flush=True)


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


def keep_shambhala(method: str, mode: str) -> bool:
    """Whether one method survives the --shambhala-mode filter."""
    if not method.startswith("shambhala"):
        return True
    if mode == "all":
        return True
    if mode == "none":
        return False
    return method == SHAMBHALA_DEFAULT_METHOD


def _list_exp_files(
    strats: Optional[list[str]],
    imps: Optional[list[str]],
    methods: Optional[list[str]],
    post_rm_filter: str,
    shambhala_mode: str = "default-only",
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
    n_shambhala_dropped = 0
    for key in keys:
        fname = Path(key).name  # e.g. A_confirmed_bad__strict__16_fsqn_r__post0.tsv.gz
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
        if not keep_shambhala(method, shambhala_mode):
            n_shambhala_dropped += 1
            continue
        if only_with_metrics and stem not in with_metrics:
            continue

        jobs.append((strat, imp, method, post_rm))

    if n_shambhala_dropped:
        print(
            f"[dispatcher] Dropped {n_shambhala_dropped} Shambhala attempts "
            f"(--shambhala-mode {shambhala_mode}).",
            flush=True,
        )
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
    n_workers: int,
    timeout_s: int,
    memory_limit_gb: float,
    tmp_dir: Path,
    corr_flavors: str,
    panel_groups: Optional[str] = None,
    min_cohort_n: Optional[int] = None,
) -> tuple[set[str], set[str]]:
    """
    Launch gene-correlation workers for all jobs.

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
        f"Gene-correlation jobs to run: {total}  |  Workers: {n_workers}  |  "
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

        cmd = [
            sys.executable,
            "run_gene_corr_job.py",
            "--strat",
            strat,
            "--imp",
            imp,
            "--method",
            method,
            "--post-rm",
            "True" if post_rm else "False",
            "--out-npz",
            str(tmp_dir / f"{tag}_genecorr.npz"),
            "--out-qc-json",
            str(tmp_dir / f"{tag}_geneqc.json"),
            "--memory-limit-gb",
            str(memory_limit_gb / 2),
            "--corr-flavors",
            corr_flavors,
        ]
        if skip_if_exists:
            cmd.append("--skip-if-exists")
        if panel_groups:
            cmd.extend(["--panel-groups", panel_groups])
        if min_cohort_n is not None:
            cmd.extend(["--min-cohort-n", str(min_cohort_n)])

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

        return (tag, time.time() - t0, proc.returncode)

    newly_failed: set[str] = set()
    newly_succeeded: set[str] = set()
    done = 0

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        future_map = {
            pool.submit(launch, s, i, m, p): _job_key(s, i, m, p) for s, i, m, p in todo
        }
        for future in as_completed(future_map):
            tag = future_map[future]
            _, elapsed, rc = future.result()
            done += 1
            if rc == 3:
                # Source file not on S3 — not a failure of the job itself.
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
        description="Dispatcher: gene x gene correlation and per-gene QC for all attempts."
    )
    parser.add_argument("--n-workers", type=int, default=4)
    parser.add_argument("--skip-if-exists", action="store_true")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument(
        "--post-rm-filter", choices=["post0", "post1", "both"], default="both"
    )
    parser.add_argument("--memory-limit-gb", type=float, default=6.0)
    parser.add_argument("--timeout-s", type=int, default=1200)
    parser.add_argument("--strats", default=None)
    parser.add_argument("--imps", default=None)
    parser.add_argument("--methods", default=None)
    parser.add_argument("--file-list", default=None)
    parser.add_argument("--tmp-dir", default="/tmp/gene_corr_jobs")
    parser.add_argument(
        "--shambhala-mode",
        choices=["all", "none", "default-only"],
        default="default-only",
        help="Which Shambhala variants to include. 'default-only' keeps only "
        f"{SHAMBHALA_DEFAULT_METHOD} (the variant renamed 20_shambhala in the "
        "analysis notebooks) and drops the cross-product variants. "
        "(default: default-only)",
    )
    parser.add_argument(
        "--only-with-metrics",
        action="store_true",
        help="Restrict to attempts that already have a metrics sidecar on S3.",
    )
    parser.add_argument(
        "--corr-flavors",
        default="global,within",
        help="Comma-separated correlation flavours forwarded to the worker.",
    )
    parser.add_argument(
        "--panel-groups",
        default=None,
        help="Comma-separated gene_group filter forwarded to the worker.",
    )
    parser.add_argument(
        "--min-cohort-n",
        type=int,
        default=None,
        help="Minimum cohort size forwarded to the worker (worker default: 20).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the job count and a breakdown, then exit without running anything.",
    )
    args = parser.parse_args()

    tmp_dir = Path(args.tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    if args.file_list:
        jobs: list[tuple[str, str, str, bool]] = []
        for line in Path(args.file_list).read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            fname = Path(line).name
            stem = fname[: -len(".tsv.gz")] if fname.endswith(".tsv.gz") else fname
            parts = stem.split("__")
            if len(parts) != 4:
                continue
            strat, imp, method, pm_tag = parts
            jobs.append((strat, imp, method, pm_tag == "post1"))
    else:
        jobs = _list_exp_files(
            args.strats.split(",") if args.strats else None,
            args.imps.split(",") if args.imps else None,
            args.methods.split(",") if args.methods else None,
            args.post_rm_filter,
            shambhala_mode=args.shambhala_mode,
            only_with_metrics=args.only_with_metrics,
        )

    if args.dry_run:
        strat_counts: dict[str, int] = {}
        for strat, _, _, _ in jobs:
            strat_counts[strat] = strat_counts.get(strat, 0) + 1
        print(f"\n[dry-run] {len(jobs)} jobs would run:", flush=True)
        for strat in sorted(strat_counts):
            print(f"  {strat:<26} {strat_counts[strat]}", flush=True)
        sys.exit(0)

    if not jobs:
        print("No jobs found. Check S3 prefix or --file-list.", flush=True)
        sys.exit(0)

    _sync_failed_from_s3()
    prev_failed = _load_failed()
    skip_keys = set() if args.retry_failed else prev_failed

    newly_failed, newly_succeeded = run_dispatcher(
        jobs=jobs,
        skip_keys=skip_keys,
        skip_if_exists=args.skip_if_exists,
        n_workers=args.n_workers,
        timeout_s=args.timeout_s,
        memory_limit_gb=args.memory_limit_gb,
        tmp_dir=tmp_dir,
        corr_flavors=args.corr_flavors,
        panel_groups=args.panel_groups,
        min_cohort_n=args.min_cohort_n,
    )

    updated_failed = (prev_failed - newly_succeeded) | newly_failed
    if updated_failed != prev_failed or newly_failed:
        _save_failed(updated_failed)
    _sync_failed_to_s3(updated_failed)

    print(
        f"\n[dispatcher] Done: {len(newly_succeeded)} succeeded, "
        f"{len(newly_failed)} failed.",
        flush=True,
    )


if __name__ == "__main__":
    main()
