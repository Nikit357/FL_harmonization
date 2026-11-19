"""
r14_pilot_report.py — gate G3 report after the two pilots (plan §6.3, WP6 6.7, WP7 7.4).

Runs on JupyterHub once Daniil says "the pilots are done" (RUNBOOK.md §5). Reads only
S3 records (nothing is downloaded beyond JSONs):
- harmonization run records `revision_261029/{gradient,v1}/runs/*.json` (r19): status,
  seconds, whether the method returned its input unchanged, the method's own messages;
- metric JSONs `revision_261029/{gradient,v1}/metrics/*_metrics.json` (r12): status and
  compute time.

What Daniil decides at G3, and the table that answers it
---------------------------------------------------------
1. Run times → `pilot_harmonization_times.tsv` (per arm × subset) and the projection of
   the full runs (`pilot_projection.tsv`): the time of each arm is scaled linearly by the
   number of samples of every planned subset (an assumption: most methods are between
   linear and quadratic in n, so the S0 projection is a lower bound), summed and divided
   by the number of workers given with --workers.
2. The decision D8 fallback → `pilot_slow_methods.tsv`: methods whose pilot time on the
   1,869-sample training part exceeds --slow-minutes, with their median time in the main
   benchmark (Supplementary File 3, compute_time_s) for comparison.
3. The covariate-free wrappers → `pilot_nocov_check.tsv`: status and messages of
   `04_sva_nocov` / `05_combat_nocov` and of the covariate arms at λ = 0 and λ = 1
   (a failure at λ = 1 is an expected result, plan caveat C3).
4. Metrics → `pilot_metric_times.tsv`: compute time and status per job; how much of it
   is metric group D cannot be split from the JSON, so the report states the mean job
   time; dropping D is decided by comparing with a re-run of a few jobs `--groups
   ABCEGHIJKLN` if Daniil wants the exact share.

Outputs: output/wp6/pilot/*.tsv and output/wp6/pilot/pilot_report.md

Usage
-----
python r14_pilot_report.py [--workers 8] [--slow-minutes 30]
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

import revision_dispatch as rd
import revision_lib as rl

OUT_DIR = rl.OUTPUT_DIR / "wp6/pilot"
FOLD_SUMMARY_PATH = rl.OUTPUT_DIR / "wp7/fold_summary.tsv"


def read_records(experiment: str, folder: str) -> pd.DataFrame:
    """All JSON records under revision_261029/<experiment>/<folder>/."""
    client = rl.s3_client()
    prefix = f"{rl.REVISION_S3_PREFIX}/{experiment}/{folder}/"
    keys = sorted(k for k in rl.s3_list_keys(client, prefix) if k.endswith(".json"))
    return pd.DataFrame([rl.s3_get_json(client, k) for k in keys])


def subset_sizes() -> pd.Series:
    """Number of samples of every planned subset (gradient designs + v1 parts)."""
    designs = pd.read_csv(rd.DESIGNS_PATH, sep="\t").set_index("design_id")["n_samples"]
    folds = pd.read_csv(FOLD_SUMMARY_PATH, sep="\t")
    v1 = pd.Series(
        folds["n_samples"].to_numpy(),
        index=[
            rd.v1_subset_id(s, int(f), p)
            for s, f, p in zip(folds["scenario"], folds["fold"], folds["part"])
        ],
    )
    return pd.concat([designs, v1])


def projection(runs: pd.DataFrame, sizes: pd.Series, workers: int) -> pd.DataFrame:
    """Full-run hours per experiment, scaling each arm's seconds-per-sample linearly."""
    runs = runs.assign(n=runs["subset_id"].map(sizes))
    per_sample = (runs["seconds"] / runs["n"]).groupby(runs["arm"]).median()
    rows = []
    plans = {
        "gradient": (rd.gradient_subsets(pilot=False), rl.GRADIENT_ARMS),
        "v1": (rd.v1_subsets(pilot=False), rl.ANALYSED_METHODS),
    }
    for experiment, (subsets, arms) in plans.items():
        n_total = float(sizes.reindex(subsets).sum())
        for arm in arms:
            seconds = per_sample.get(arm, np.nan) * n_total
            rows.append(
                {
                    "experiment": experiment,
                    "arm": arm,
                    "method_display": rl.method_display_name(arm),
                    "measured_in_pilot": arm in per_sample.index,
                    "projected_cpu_hours": seconds / 3600,
                }
            )
    table = pd.DataFrame(rows)
    table.attrs["wall_hours"] = (
        table.groupby("experiment")["projected_cpu_hours"].sum() / workers
    ).to_dict()
    return table


def main() -> None:
    """Build the gate G3 tables and the markdown summary."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--slow-minutes", type=float, default=30.0)
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    runs = pd.concat(
        [read_records(e, "runs").assign(experiment=e) for e in ("gradient", "v1")],
        ignore_index=True,
    )
    if runs.empty:
        raise SystemExit(
            "no run records on S3 yet: run the pilots first (RUNBOOK.md §4)"
        )
    runs["method_display"] = runs["arm"].map(rl.method_display_name)
    columns = [
        "experiment",
        "subset_id",
        "arm",
        "method_display",
        "status",
        "seconds",
        "n_samples_in",
        "returned_input_unchanged",
    ]
    runs[[c for c in columns if c in runs]].to_csv(
        OUT_DIR / "pilot_harmonization_times.tsv", sep="\t", index=False
    )

    sizes = subset_sizes()
    projected = projection(runs[runs["status"] == "ok"], sizes, args.workers)
    projected.to_csv(OUT_DIR / "pilot_projection.tsv", sep="\t", index=False)

    main_times = (
        rl.load_supp_file_3(analysis_set_only=True)
        .groupby("method")["compute_time_s"]
        .median()
        / 60
    )
    train = runs[runs["subset_id"] == rd.v1_subset_id("C", 1, "train")]
    slow = train.assign(
        pilot_minutes=train["seconds"] / 60,
        main_benchmark_median_minutes=train["arm"].map(main_times),
    )
    slow["slow"] = slow["pilot_minutes"] > args.slow_minutes
    slow.sort_values("pilot_minutes", ascending=False)[
        [
            "arm",
            "method_display",
            "status",
            "pilot_minutes",
            "main_benchmark_median_minutes",
            "slow",
        ]
    ].to_csv(OUT_DIR / "pilot_slow_methods.tsv", sep="\t", index=False)

    covariate_arms = ["04_sva", "04_sva_nocov", "05_combat", "05_combat_nocov"]
    nocov = runs[(runs["experiment"] == "gradient") & runs["arm"].isin(covariate_arms)]
    nocov[[c for c in [*columns, "method_messages", "traceback"] if c in nocov]].to_csv(
        OUT_DIR / "pilot_nocov_check.tsv", sep="\t", index=False
    )

    metrics = pd.concat(
        [read_records(e, "metrics").assign(experiment=e) for e in ("gradient", "v1")],
        ignore_index=True,
    )
    if not metrics.empty:
        metrics[["experiment", "subset_id", "arm", "status", "compute_time_s"]].to_csv(
            OUT_DIR / "pilot_metric_times.tsv", sep="\t", index=False
        )

    failed = runs[runs["status"] != "ok"]
    lines = [
        "# Pilot report (gate G3)",
        "",
        f"Harmonization runs: {len(runs)} ({len(failed)} failed: "
        + ", ".join(f"{r.subset_id} × {r.arm}" for r in failed.itertuples())
        + ")",
        "",
        f"Projected wall time with {args.workers} workers (linear-in-n scaling, a lower "
        "bound for the S0 training folds):",
        *[f"- {k}: {v:.1f} h" for k, v in projected.attrs["wall_hours"].items()],
        "",
        f"Methods slower than {args.slow_minutes:g} min on the 1,869-sample training "
        "part (decision D8 fallback candidates): "
        + (", ".join(slow.loc[slow["slow"], "method_display"]) or "none"),
        "",
        "Metric jobs: "
        + (
            f"{len(metrics)}; status {metrics['status'].value_counts().to_dict()}; "
            f"median {metrics['compute_time_s'].median() / 60:.1f} min per job"
            if not metrics.empty
            else "none yet (RUNBOOK.md §5)"
        ),
        "",
        "Covariate arms: see pilot_nocov_check.tsv (status and method messages).",
    ]
    (OUT_DIR / "pilot_report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
