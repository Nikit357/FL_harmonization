"""
revision_dispatch.py — job lists and the parallel subprocess runner of the revision pods.

Used by r11_run_gradient.py, r21_run_v1.py (harmonization pod) and
r12_revision_metrics.py, r30_bridging_subset_metrics.py (metrics pod). Every job is a
separate `python <worker> …` subprocess, as in the main benchmark: an R crash, an
out-of-memory kill or a hang stops one job, never the dispatcher. A job is started only
when the free memory (cgroup limit when inside K8s) exceeds --memory-limit-gb; a job
that runs longer than --timeout-s is killed and recorded as "timeout".

Subset identifiers
------------------
gradient: the design ids of output/wp6/designs/designs.tsv (45);
v1:       v1_<scenario>_f<fold>_<part>, scenario ∈ C K J S0, fold 1–5, part train/test (40).

Logs: <log-dir>/<experiment>/<job>.log per job, and <log-dir>/<experiment>_<stage>.tsv
with one row per job (status, seconds, exit code). <log-dir> defaults to
/workspace/revision (the PVC) and falls back to ./cache/revision_logs off the pod.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

import revision_lib as rl

DESIGNS_PATH = rl.OUTPUT_DIR / "wp6/designs/designs.tsv"
FOLD_SAMPLES_PATH = rl.OUTPUT_DIR / "wp7/fold_samples.tsv"
V1_SCENARIOS: tuple[str, ...] = ("C", "K", "J", "S0")
V1_FOLDS: tuple[int, ...] = (1, 2, 3, 4, 5)
V1_PARTS: tuple[str, ...] = ("train", "test")
GRADIENT_PILOT_DESIGNS: tuple[str, ...] = ("grad_cap150_l0.0_r1", "grad_cap150_l1.0_r1")
V1_PILOT_SUBSETS: tuple[str, ...] = ("v1_C_f1_train", "v1_C_f1_test")


def default_log_dir() -> Path:
    """The PVC folder inside the pods, a local cache folder elsewhere."""
    pvc = Path("/workspace")
    return pvc / "revision" if pvc.is_dir() else rl.CACHE_DIR / "revision_logs"


# ── Subsets ───────────────────────────────────────────────────────────────────


def gradient_subsets(pilot: bool = False) -> list[str]:
    """Design ids in run order (pilot: λ = 0 and λ = 1, replicate 1, cap 150)."""
    if pilot:
        return list(GRADIENT_PILOT_DESIGNS)
    return pd.read_csv(DESIGNS_PATH, sep="\t")["design_id"].tolist()


def v1_subset_id(scenario: str, fold: int, part: str) -> str:
    """Identifier of one leave-cohort-out subset."""
    return f"v1_{scenario}_f{fold}_{part}"


def v1_subsets(
    pilot: bool = False,
    scenarios: list[str] | None = None,
    folds: list[int] | None = None,
) -> list[str]:
    """Leave-cohort-out subset ids, smallest scenario first (C → K → J → S0)."""
    if pilot:
        return list(V1_PILOT_SUBSETS)
    return [
        v1_subset_id(s, f, p)
        for s in (scenarios or V1_SCENARIOS)
        for f in (folds or V1_FOLDS)
        for p in V1_PARTS
    ]


def subset_sample_ids(experiment: str, subset_id: str) -> list[str]:
    """Sample ids of one subset, read from the committed design / fold files."""
    if experiment == "gradient":
        path = rl.OUTPUT_DIR / "wp6/designs" / f"{subset_id}.tsv"
        return pd.read_csv(path, sep="\t", index_col=0).index.tolist()
    _, scenario, fold_tag, part = subset_id.split("_")
    folds = pd.read_csv(FOLD_SAMPLES_PATH, sep="\t")
    mask = (
        (folds["scenario"] == scenario)
        & (folds["fold"] == int(fold_tag[1:]))
        & (folds["part"] == part)
    )
    return folds.loc[mask, "sample_id"].tolist()


# ── Jobs and the runner ───────────────────────────────────────────────────────


@dataclass
class Job:
    """One subprocess: a name (log file stem) and its command line."""

    name: str
    command: list[str]
    outputs: list[str] = field(default_factory=list)  # S3 keys that mark it done
    # Written to S3 when the job is killed for its time limit, so that the timeout is a
    # recorded result (gate G3: "if it fails the timeout, skip it"): --skip-if-exists
    # then does not start the same job again, and r14 / r22 see it.
    timeout_record_key: str = ""
    timeout_record: dict = field(default_factory=dict)


def free_memory_gb() -> float:
    """Available RAM in GB (cgroup v2 / v1 limit inside K8s, psutil elsewhere)."""

    def read_int(path: str) -> int | None:
        try:
            value = open(path).read().strip()
            return None if value == "max" else int(value)
        except (OSError, ValueError):
            return None

    limit = read_int("/sys/fs/cgroup/memory.max") or read_int(
        "/sys/fs/cgroup/memory/memory.limit_in_bytes"
    )
    usage = read_int("/sys/fs/cgroup/memory.current") or read_int(
        "/sys/fs/cgroup/memory/memory.usage_in_bytes"
    )
    if limit is not None and usage is not None and limit < 1 << 60:
        return (limit - usage) / 1e9
    try:
        import psutil

        return psutil.virtual_memory().available / 1e9
    except ImportError:
        return 999.0


def drop_done(jobs: list[Job], skip_if_exists: bool, existing: set[str]) -> list[Job]:
    """Remove jobs whose every output key is already on S3 (with --skip-if-exists)."""
    if not skip_if_exists:
        return jobs
    return [
        j for j in jobs if not (j.outputs and all(k in existing for k in j.outputs))
    ]


def run_jobs(
    jobs: list[Job],
    n_workers: int,
    memory_limit_gb: float,
    timeout_s: int,
    log_dir: Path,
    stage: str,
) -> pd.DataFrame:
    """
    Run jobs as parallel subprocesses; returns (and writes) the per-job status table.

    The status table is rewritten after every finished job, so a crashed dispatcher
    leaves an up-to-date record behind.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    table_path = log_dir.parent / f"{log_dir.name}_{stage}.tsv"
    pending = list(jobs)
    running: dict[str, tuple[subprocess.Popen, float, object]] = {}
    rows: list[dict] = []
    env = {
        **os.environ,
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "PYTHONUNBUFFERED": "1",
    }
    print(
        f"[{time.strftime('%H:%M:%S')}] {stage}: {len(jobs)} jobs, "
        f"{n_workers} workers",
        flush=True,
    )
    while pending or running:
        while (
            pending and len(running) < n_workers and free_memory_gb() >= memory_limit_gb
        ):
            job = pending.pop(0)
            handle = open(log_dir / f"{job.name}.log", "w")
            process = subprocess.Popen(
                job.command,
                stdout=handle,
                stderr=subprocess.STDOUT,
                cwd=rl.REVISION_DIR,
                env=env,
            )
            running[job.name] = (process, time.time(), handle)
        if pending and not running and free_memory_gb() < memory_limit_gb:
            print(f"waiting for memory: {free_memory_gb():.1f} GB free", flush=True)
        time.sleep(2)
        for name, (process, started, handle) in list(running.items()):
            elapsed = time.time() - started
            code = process.poll()
            if code is None and elapsed > timeout_s:
                process.kill()
                process.wait()
                code, status = -9, "timeout"
                job = next((j for j in jobs if j.name == name), None)
                if job is not None and job.timeout_record_key:
                    try:
                        rl.s3_put_json(
                            rl.s3_client(),
                            job.timeout_record_key,
                            {
                                **job.timeout_record,
                                "status": "timeout",
                                "seconds": round(elapsed, 1),
                                "timeout_s": timeout_s,
                            },
                        )
                    except Exception as error:  # the log line below still says timeout
                        print(f"could not write the timeout record: {error!r}")
            elif code is None:
                continue
            else:
                status = "ok" if code == 0 else "failed"
            handle.close()  # type: ignore[attr-defined]
            del running[name]
            rows.append(
                {
                    "job": name,
                    "status": status,
                    "exit_code": code,
                    "seconds": round(elapsed, 1),
                }
            )
            pd.DataFrame(rows).to_csv(table_path, sep="\t", index=False)
            done = len(rows)
            print(
                f"[{time.strftime('%H:%M:%S')}] {done}/{len(jobs)} {name}: {status} "
                f"({elapsed:.0f}s)",
                flush=True,
            )
    table = pd.DataFrame(rows, columns=["job", "status", "exit_code", "seconds"])
    counts = table["status"].value_counts().to_dict() if len(table) else {}
    print(f"SUMMARY {stage}: {len(table)} jobs — {counts}", flush=True)
    return table


def python_command(script: str, *arguments: str) -> list[str]:
    """`python <script> <arguments…>` with the running interpreter."""
    return [sys.executable, str(rl.REVISION_DIR / script), *arguments]


# ── Harmonization pod: shared entry point of r11 and r21 ──────────────────────


def add_common_arguments(parser) -> None:
    """Flags shared by every dispatcher (plan §6.3)."""
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-if-exists", action="store_true")
    parser.add_argument("--n-workers", type=int, default=4)
    parser.add_argument(
        "--memory-limit-gb",
        type=float,
        default=6.0,
        help="start a job only when at least this much RAM is free",
    )
    # Gate G3 (Daniil, 2026-11-03): 6 h per harmonization; a run that exceeds it is
    # recorded as "timeout" and skipped (AMDBNorm, HarmonizR, Shambhala on S0 folds).
    parser.add_argument("--timeout-s", type=int, default=21600)
    parser.add_argument("--log-dir", default=str(default_log_dir()))


def harmonization_main(
    experiment: str, subsets: list[str], arms: list[str], args
) -> None:
    """
    Stage 0: raw-data cache; stage 1: preparation of every subset (split over
    --n-prep-workers processes, each loads the raw matrix once); stage 2: one job per
    subset × arm. With --skip-if-exists a preparation is skipped when its __prep.json
    is on S3 and a harmonization when its run record is (a failed method is a result and
    is not retried; rerun without the flag to retry).
    """
    log_dir = Path(args.log_dir)
    prep_done = {
        s: rl.s3_key_subset(experiment, s, "exp").replace("__exp.tsv.gz", "__prep.json")
        for s in subsets
    }
    harm_jobs = [
        Job(
            name=f"{s}__{a}",
            command=python_command(
                "r19_harmonize_one.py",
                "--experiment",
                experiment,
                "--subset-id",
                s,
                "--arm",
                a,
                "--cache-dir",
                str(log_dir / "cache/prepared"),
            ),
            outputs=[rl.s3_key_run_record(experiment, s, a)],
            timeout_record_key=rl.s3_key_run_record(experiment, s, a),
            timeout_record={"experiment": experiment, "subset_id": s, "arm": a},
        )
        for s in subsets
        for a in arms
    ]
    print(
        f"{experiment}: {len(subsets)} subsets × {len(arms)} arms = "
        f"{len(harm_jobs)} harmonization jobs planned"
    )
    try:
        existing = rl.s3_list_keys(
            rl.s3_client(), f"{rl.REVISION_S3_PREFIX}/{experiment}/"
        )
    except Exception as error:  # dry-run off the pod without credentials
        print(f"(S3 listing unavailable: {error!r})")
        existing = set()
    to_prepare = [
        s for s in subsets if not (args.skip_if_exists and prep_done[s] in existing)
    ]
    to_harmonize = drop_done(harm_jobs, args.skip_if_exists, existing)
    print(
        f"to run now: {len(to_prepare)} preparations, {len(to_harmonize)} harmonizations"
    )
    if args.dry_run:
        for job in to_harmonize[:2]:
            print("  e.g.", " ".join(job.command[1:]))
        return

    raw_cache = log_dir / "cache/bench_comb_data.pkl"
    if to_prepare and not raw_cache.exists():
        run_jobs(
            [
                Job(
                    "warm_raw_cache",
                    python_command(
                        "r19_harmonize_one.py",
                        "--experiment",
                        experiment,
                        "--warm-cache",
                        "--raw-cache",
                        str(raw_cache),
                    ),
                )
            ],
            1,
            0.0,
            args.timeout_s,
            log_dir / experiment,
            "warm_cache",
        )
    chunks = [to_prepare[i :: args.n_prep_workers] for i in range(args.n_prep_workers)]
    prep_jobs = [
        Job(
            f"prepare_{i}",
            python_command(
                "r19_harmonize_one.py",
                "--experiment",
                experiment,
                "--prepare",
                "--subset-ids",
                ",".join(chunk),
                "--raw-cache",
                str(raw_cache),
            ),
        )
        for i, chunk in enumerate(chunks)
        if chunk
    ]
    if prep_jobs:
        run_jobs(
            prep_jobs,
            args.n_prep_workers,
            args.memory_limit_gb,
            args.timeout_s * 4,
            log_dir / experiment,
            "prepare",
        )
    existing = rl.s3_list_keys(rl.s3_client(), f"{rl.REVISION_S3_PREFIX}/{experiment}/")
    ready = [
        j
        for j in to_harmonize
        if rl.s3_key_subset(experiment, j.name.split("__")[0], "exp") in existing
    ]
    if len(ready) < len(to_harmonize):
        print(
            f"WARNING: {len(to_harmonize) - len(ready)} jobs skipped: subset not prepared"
        )
    run_jobs(
        ready,
        args.n_workers,
        args.memory_limit_gb,
        args.timeout_s,
        log_dir / experiment,
        "harmonize",
    )
