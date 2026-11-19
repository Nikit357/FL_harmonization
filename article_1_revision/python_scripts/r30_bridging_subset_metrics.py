"""
r30_bridging_subset_metrics.py — bridging-batch check on the 2,234 approaches (plan WP8).

Runs on the metrics pod (RUNBOOK.md). Nothing is re-harmonized: for every approach of
the analysis set (Supplementary File 3, pct_samples_allNA < 5) the existing matrix
`FL_batch_correction/exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz` is read from S3 and
restricted to the samples of its multi-diagnosis batches (RNA_BATCH levels holding ≥ 2
Diagnosis_cell_type_unified levels among the samples of that matrix). The Diagnosis
metrics of the panel are recomputed there with the frozen groups A, B, G, H, I. The
annotation handed to them holds the Diagnosis column ONLY, so that every batch-column
metric (kBET included) is skipped by the frozen code itself (its `_row_mask` returns None
for an absent column) — that is how "no kBET" is obtained without editing frozen code.

Output: revision_261029/bridging/metrics/<strat>__<imp>__<method>__post<0|1>_metrics.json;
`--concat` (JupyterHub) → output/wp8/bridging_biology.parquet (one row per approach).

Usage (inside the metrics pod)
-----
python r30_bridging_subset_metrics.py --dry-run           # 2,234 jobs
setsid nohup python r30_bridging_subset_metrics.py --skip-if-exists --n-workers 24 \
    --memory-limit-gb 8.0 > /workspace/revision/bridging.log 2>&1 &
python r30_bridging_subset_metrics.py --concat            # JupyterHub
"""

from __future__ import annotations

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import argparse
import sys
import time
import traceback

import pandas as pd

import revision_dispatch as rd
import revision_lib as rl

EXPERIMENT = "bridging"


def approach_id(strat: str, imp: str, method: str, post_rm: bool) -> str:
    """Key stem of one approach, as in the benchmark (post0 / post1)."""
    return f"{strat}__{imp}__{method}__post{int(post_rm)}"


def approaches() -> pd.DataFrame:
    """The 2,234 approaches of the analysis set."""
    return rl.load_supp_file_3(analysis_set_only=True)[rl.APPROACH_KEYS]


def bridging_samples(ann: pd.DataFrame) -> pd.Index:
    """Samples of the batches with ≥ 2 diagnoses (within this matrix)."""
    n_dx = ann.groupby(rl.BATCH_COL)[rl.BIO_COL].nunique()
    return ann.index[ann[rl.BATCH_COL].isin(n_dx.index[n_dx >= 2])]


def run_one(strat: str, imp: str, method: str, post_rm: bool) -> int:
    """Diagnosis metrics of one approach on its multi-diagnosis batches → S3 JSON."""
    client = rl.s3_client()
    job = approach_id(strat, imp, method, post_rm)
    started = time.time()
    record: dict = {"strat": strat, "imp": imp, "method": method, "post_rm": post_rm}
    try:
        exp_df = rl.s3_get_tsv_gz(
            client, rl.main_benchmark_matrix_key(strat, imp, method, post_rm)
        )
        ann = rl.s3_get_tsv_gz(
            client, f"{rl.S3_PREFIX}/prepared/{strat}__{imp}__ann.tsv.gz"
        )
        ann = ann.loc[exp_df.index.intersection(ann.index)]
        keep = bridging_samples(ann)
        record.update(
            {
                "n_samples_matrix": int(len(ann)),
                "n_samples_bridging": int(len(keep)),
                "n_bridging_batches": int(ann.loc[keep, rl.BATCH_COL].nunique()),
            }
        )
        metrics = rl.metrics_on_subset(
            exp_df, ann[[rl.BIO_COL]], rl.BRIDGING_METRIC_GROUPS, sample_ids=keep
        )
        record.update(
            {
                k: v
                for k, v in metrics.items()
                if k.endswith(rl.BIO_COL) or k.startswith("error_")
            }
        )
        record["status"] = "ok"
    except Exception:
        record.update({"status": "failed", "traceback": traceback.format_exc()[-4000:]})
        print(record["traceback"], flush=True)
    record["compute_time_s"] = round(time.time() - started, 1)
    rl.s3_put_json(client, rl.s3_key_revision_metrics(EXPERIMENT, job), record)
    print(f"{job}: {record['status']} ({record['compute_time_s']}s)")
    return 0 if record["status"] == "ok" else 1


def concat() -> None:
    """All JSONs → output/wp8/bridging_biology.parquet."""
    client = rl.s3_client()
    keys = rl.s3_list_keys(client, f"{rl.REVISION_S3_PREFIX}/{EXPERIMENT}/metrics/")
    table = pd.DataFrame([rl.s3_get_json(client, k) for k in sorted(keys)])
    out = rl.OUTPUT_DIR / "wp8/bridging_biology.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(out, index=False)
    print(
        f"wrote {out}: {len(table)} rows; status {table['status'].value_counts().to_dict()}"
    )


def main() -> None:
    """Dispatcher / worker / concat."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    rd.add_common_arguments(parser)
    parser.add_argument("--run-one", action="store_true")
    parser.add_argument("--strat", default="")
    parser.add_argument("--imp", default="")
    parser.add_argument("--method", default="")
    parser.add_argument("--post-rm", default="False")
    parser.add_argument("--concat", action="store_true")
    args = parser.parse_args()
    if args.run_one:
        sys.exit(run_one(args.strat, args.imp, args.method, args.post_rm == "True"))
    if args.concat:
        concat()
        return
    jobs = [
        rd.Job(
            name=approach_id(s, i, m, p),
            command=rd.python_command(
                "r30_bridging_subset_metrics.py",
                "--run-one",
                "--strat",
                s,
                "--imp",
                i,
                "--method",
                m,
                "--post-rm",
                str(bool(p)),
            ),
            outputs=[rl.s3_key_revision_metrics(EXPERIMENT, approach_id(s, i, m, p))],
        )
        for s, i, m, p in approaches().itertuples(index=False)
    ]
    try:
        existing = rl.s3_list_keys(
            rl.s3_client(), f"{rl.REVISION_S3_PREFIX}/{EXPERIMENT}/"
        )
    except Exception as error:
        print(f"(S3 listing unavailable: {error!r})")
        existing = set()
    to_run = rd.drop_done(jobs, args.skip_if_exists, existing)
    print(f"{len(jobs)} bridging jobs planned; {len(to_run)} to run now")
    if args.dry_run:
        return
    rd.run_jobs(
        to_run,
        args.n_workers,
        args.memory_limit_gb,
        args.timeout_s,
        rd.default_log_dir() / "bridging",
        "metrics",
    )


if __name__ == "__main__":
    main()
