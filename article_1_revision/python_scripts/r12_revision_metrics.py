"""
r12_revision_metrics.py — metrics of the new harmonizations (plan WP6 step 6.5, WP7 7.3).

Runs on the metrics pod (label app=fl-revision, or
app=fl-metrics; RUNBOOK.md). For every harmonized
matrix of an experiment (gradient: 45 designs × 14 arms; leave_cohort_out: 40 subsets ×
31 methods), computes with the frozen `compute_all_metrics` (via
revision_lib.metrics_on_subset) the groups of revision_lib.REVISION_METRIC_GROUPS:
A B C D E G H I J K (every group of the reduced panel, so the panel chosen at gate G1
does not change what is computed) + L (marker correlation; reference = the 01_raw output
of the same subset) + N (cross-batch prediction, 100 permutations as in the blind check).
F (variancePartition, slow) and M are not computed.

Gradient only: agreement with batch-free fold changes (revision_lib.gt_logfc_concordance)
against the reference built once from the full raw data of the five gradient batches
(S0 strict 01_raw matrix, per-gene OLS with batch as a factor).

Output: revision_261029/<experiment>/metrics/<subset>__<arm>_metrics.json on S3.
`--concat` (run on JupyterHub) collects them with the run records into
output/wp6/gradient_metrics.parquet or output/wp7/v1_metrics.parquet.

Usage (inside the metrics pod, from /app/article_1_revision)
-----
python r12_revision_metrics.py --pilot --dry-run          # 86 jobs (24 gradient + 62 v1)
setsid nohup python r12_revision_metrics.py --pilot --skip-if-exists --n-workers 8 \
    --memory-limit-gb 8.0 > /workspace/revision/metrics_pilot.log 2>&1 &
python r12_revision_metrics.py --experiment gradient --skip-if-exists --n-workers 24
python r12_revision_metrics.py --experiment leave_cohort_out --concat   # JupyterHub
"""

from __future__ import annotations

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import argparse
import sys
import time
import traceback
from pathlib import Path

import pandas as pd

import revision_dispatch as rd
import revision_lib as rl

EXPERIMENT_KEYS = {"gradient": "gradient", "leave_cohort_out": "v1", "v1": "v1"}
N_PERM = 100
RAW_S0_KEY = f"{rl.S3_PREFIX}/exp/S0_no_removal__strict__01_raw__post0.tsv.gz"


def gt_reference_path(log_dir: Path) -> Path:
    """Local cache of the batch-free reference fold changes."""
    return log_dir / "cache/gt_logfc_reference.pkl"


def ensure_gt_reference(log_dir: Path) -> Path:
    """Build the reference once from the S0 strict raw matrix of the 5 gradient batches."""
    path = gt_reference_path(log_dir)
    if path.exists():
        return path
    client = rl.s3_client()
    raw = rl.s3_get_tsv_gz(client, RAW_S0_KEY)
    ann = rl.load_s0_annotation()
    keep = ann.index[ann[rl.BATCH_COL].isin(rl.GRADIENT_ASSIGNED_DIAGNOSIS)]
    reference = rl.gt_logfc_reference(raw.loc[raw.index.intersection(keep)], ann)
    path.parent.mkdir(parents=True, exist_ok=True)
    reference.to_pickle(path)
    print(
        f"batch-free reference: {reference.shape[0]} genes × {reference.shape[1]} contrasts"
    )
    return path


def planned(experiment: str, pilot: bool) -> list[tuple[str, str]]:
    """(subset, arm) pairs of an experiment."""
    if experiment == "gradient":
        return [(s, a) for s in rd.gradient_subsets(pilot) for a in rl.GRADIENT_ARMS]
    return [(s, a) for s in rd.v1_subsets(pilot) for a in rl.ANALYSED_METHODS]


def run_one(
    experiment: str, subset_id: str, arm: str, log_dir: Path, groups: str
) -> int:
    """Metrics of one harmonized matrix → S3 JSON."""
    client = rl.s3_client()
    started = time.time()
    record: dict = {"experiment": experiment, "subset_id": subset_id, "arm": arm}
    try:
        exp_df = rl.s3_get_tsv_gz(
            client, rl.s3_key_harmonized(experiment, subset_id, arm)
        )
        ann_df = rl.s3_get_tsv_gz(
            client, rl.s3_key_subset(experiment, subset_id, "ann")
        )
        ref_df = (
            exp_df
            if arm == "01_raw"
            else rl.s3_get_tsv_gz(
                client, rl.s3_key_harmonized(experiment, subset_id, "01_raw")
            )
        )
        metrics = rl.metrics_on_subset(
            exp_df, ann_df, set(groups), ref_df=ref_df, n_perm=N_PERM
        )
        record.update(metrics)
        record["metric_groups"] = groups
        if experiment == "gradient":
            reference = pd.read_pickle(gt_reference_path(log_dir))
            record.update(rl.gt_logfc_concordance(exp_df, ann_df, reference))
        record["status"] = "ok"
    except Exception:
        record.update({"status": "failed", "traceback": traceback.format_exc()[-4000:]})
        print(record["traceback"], flush=True)
    record["compute_time_s"] = round(time.time() - started, 1)
    rl.s3_put_json(
        client, rl.s3_key_revision_metrics(experiment, f"{subset_id}__{arm}"), record
    )
    print(f"{subset_id} × {arm}: {record['status']} ({record['compute_time_s']}s)")
    return 0 if record["status"] == "ok" else 1


def concat(experiment: str) -> None:
    """Collect metrics JSONs and run records into one local table (JupyterHub)."""
    client = rl.s3_client()
    prefix = f"{rl.REVISION_S3_PREFIX}/{experiment}/"
    keys = rl.s3_list_keys(client, prefix)
    rows = []
    for key in sorted(k for k in keys if k.endswith("_metrics.json")):
        metrics = rl.s3_get_json(client, key)
        run_key = rl.s3_key_run_record(experiment, metrics["subset_id"], metrics["arm"])
        run = rl.s3_get_json(client, run_key) if run_key in keys else {}
        rows.append(
            {
                **{
                    f"run_{k}": v
                    for k, v in run.items()
                    if k not in ("experiment", "subset_id", "arm")
                },
                **metrics,
            }
        )
    for key in sorted(k for k in keys if "/runs/" in k):  # failed harmonizations
        run = rl.s3_get_json(client, key)
        if run.get("status") != "ok":
            rows.append(
                {
                    "experiment": experiment,
                    "subset_id": run["subset_id"],
                    "arm": run["arm"],
                    "status": "harmonization_failed",
                    **{f"run_{k}": v for k, v in run.items()},
                }
            )
    table = pd.DataFrame(rows)
    if experiment == "gradient":
        designs = pd.read_csv(rd.DESIGNS_PATH, sep="\t").rename(
            columns={"design_id": "subset_id"}
        )
        table = table.merge(designs, on="subset_id", how="left")
        out = rl.OUTPUT_DIR / "wp6/gradient_metrics.parquet"
    else:
        parts = table["subset_id"].str.split("_", expand=True)
        table["scenario"], table["fold"], table["part"] = (
            parts[1],
            parts[2].str[1:].astype(int),
            parts[3],
        )
        out = rl.OUTPUT_DIR / "wp7/v1_metrics.parquet"
    table["method_display"] = table["arm"].map(rl.method_display_name)
    out.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(out, index=False)
    print(
        f"wrote {out}: {len(table)} rows; status {table['status'].value_counts().to_dict()}"
    )


def main() -> None:
    """Dispatcher / worker / concat."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    rd.add_common_arguments(parser)
    parser.add_argument("--experiment", choices=list(EXPERIMENT_KEYS), default="")
    parser.add_argument("--run-one", action="store_true")
    parser.add_argument("--subset-id", default="")
    parser.add_argument("--arm", default="")
    parser.add_argument("--concat", action="store_true")
    parser.add_argument(
        "--groups",
        default="".join(sorted(rl.REVISION_METRIC_GROUPS)),
        help="metric groups (default ABCDEGHIJKLN); gate G3 may drop the slow D",
    )
    args = parser.parse_args()
    log_dir = Path(args.log_dir)
    experiments = (
        [EXPERIMENT_KEYS[args.experiment]]
        if args.experiment
        else ["gradient", "v1"] if args.pilot else []
    )
    if not experiments:
        parser.error("--experiment is required unless --pilot is given")
    if args.run_one:
        sys.exit(
            run_one(experiments[0], args.subset_id, args.arm, log_dir, args.groups)
        )
    if args.concat:
        for experiment in experiments:
            concat(experiment)
        return

    all_jobs, ready_jobs = [], []
    for experiment in experiments:
        try:
            existing = rl.s3_list_keys(
                rl.s3_client(), f"{rl.REVISION_S3_PREFIX}/{experiment}/"
            )
        except Exception as error:
            print(f"(S3 listing unavailable: {error!r})")
            existing = set()
        for subset_id, arm in planned(experiment, args.pilot):
            job = rd.Job(
                name=f"{subset_id}__{arm}",
                command=rd.python_command(
                    "r12_revision_metrics.py",
                    "--run-one",
                    "--experiment",
                    experiment,
                    "--subset-id",
                    subset_id,
                    "--arm",
                    arm,
                    "--log-dir",
                    str(log_dir),
                    "--groups",
                    args.groups,
                ),
                outputs=[rl.s3_key_revision_metrics(experiment, f"{subset_id}__{arm}")],
            )
            all_jobs.append((experiment, job))
            harmonized = rl.s3_key_harmonized(experiment, subset_id, arm) in existing
            if harmonized and not (args.skip_if_exists and job.outputs[0] in existing):
                ready_jobs.append((experiment, job))
    print(
        f"{len(all_jobs)} metric jobs planned; {len(ready_jobs)} have a harmonized "
        f"matrix and are to run now"
    )
    if args.dry_run or not ready_jobs:
        return
    if any(e == "gradient" for e, _ in ready_jobs):
        ensure_gt_reference(log_dir)
    for experiment in experiments:
        jobs = [j for e, j in ready_jobs if e == experiment]
        rd.run_jobs(
            jobs,
            args.n_workers,
            args.memory_limit_gb,
            args.timeout_s,
            log_dir / f"metrics_{experiment}",
            "metrics",
        )


if __name__ == "__main__":
    main()
