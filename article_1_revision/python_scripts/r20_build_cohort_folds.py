"""
r20_build_cohort_folds.py — cohort-level folds of the leave-cohort-out validation
(plan WP7 step 7.1; decision D2; same idea as h230_01_build_cv_splits.py of Article 2).

For each scenario dataset (strategy J FF only, K FFPE only, C RNA-seq only, S0 all
samples; membership from the prepared S3 annotation of the strategy) the cohorts
(COHORT_LABEL) are split into 5 folds, 1 repeat, seed 42. Fold k is the TEST part of
split k; the other four folds are its TRAINING part.

Balancing: greedy — cohorts in decreasing size go to the fold with the fewest samples,
with random tie order. 5,000 random restarts (seed 42) are scored; the assignment kept
is the one that meets the most constraints and then has the smallest spread of test
sizes. Constraints per test fold: ≥ 2 RNA_BATCH levels, and ≥ 2 of DLBCL / FL / Normal B
whenever the scenario has ≥ 2 of them. Folds that still miss a constraint are reported
in fold_summary.tsv (`meets_constraints = False`), not forced.

Outputs (output/wp7/, small, committed): folds.tsv (scenario, cohort, fold, n),
fold_samples.tsv (scenario, fold, part, sample_id), fold_summary.tsv (n, batches,
diagnoses, Cramér's V per scenario × fold × part).

Usage
-----
python r20_build_cohort_folds.py [--dry-run]
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

import revision_lib as rl

OUT_DIR = rl.OUTPUT_DIR / "wp7"
SCENARIO_STRATEGIES: dict[str, str] = {
    "C": "C_rnaseq_only",
    "K": "K_ffpe_only",
    "J": "J_ff_only",
    "S0": "S0_no_removal",
}
N_FOLDS = 5
SEED = 42
N_RESTARTS = 5_000


def scenario_annotation(strategy: str) -> pd.DataFrame:
    """Prepared softImpute annotation of one strategy (cached)."""
    path = rl.CACHE_DIR / "annotations" / f"{strategy}__softimpute__ann.tsv.gz"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        rl.s3_client().download_file(  # type: ignore[attr-defined]
            rl.S3_BUCKET,
            f"{rl.S3_PREFIX}/prepared/{strategy}__softimpute__ann.tsv.gz",
            str(path),
        )
    ann = pd.read_csv(path, sep="\t", index_col=0, low_memory=False)
    ann["diagnosis_3class"] = rl.major_group(ann, n_classes=3)
    return ann


def fold_violations(
    ann: pd.DataFrame, cohort_fold: dict[str, int]
) -> tuple[int, float]:
    """(number of test folds missing a constraint, SD of test-fold sizes)."""
    fold = ann[rl.COHORT_COL].map(cohort_fold)
    n_dx_scenario = ann["diagnosis_3class"].nunique()
    violations = 0
    for k in range(N_FOLDS):
        test = ann[fold == k]
        if test[rl.BATCH_COL].nunique() < 2:
            violations += 1
        elif n_dx_scenario >= 2 and test["diagnosis_3class"].nunique() < 2:
            violations += 1
    sizes = fold.value_counts().reindex(range(N_FOLDS), fill_value=0)
    return violations, float(sizes.std())


def greedy_assignment(
    cohort_sizes: pd.Series, rng: np.random.Generator
) -> dict[str, int]:
    """Largest cohort first to the smallest fold, ties in random order."""
    jitter = rng.random(len(cohort_sizes))
    order = (
        cohort_sizes.to_frame("n")
        .assign(j=jitter)
        .sort_values(["n", "j"], ascending=[False, True])
        .index
    )
    totals = np.zeros(N_FOLDS)
    assignment = {}
    for cohort in order:
        smallest = np.flatnonzero(totals == totals.min())
        k = int(rng.choice(smallest))
        assignment[cohort] = k
        totals[k] += cohort_sizes[cohort]
    return assignment


def best_folds(ann: pd.DataFrame) -> dict[str, int]:
    """Best of N_RESTARTS greedy assignments (fewest violations, then most balanced)."""
    rng = np.random.default_rng(SEED)
    sizes = ann[rl.COHORT_COL].value_counts()
    best, best_key = None, None
    for _ in range(N_RESTARTS):
        assignment = greedy_assignment(sizes, rng)
        key = fold_violations(ann, assignment)
        if best_key is None or key < best_key:
            best, best_key = assignment, key
    return best  # type: ignore[return-value]


def summarize(
    ann: pd.DataFrame, scenario: str, cohort_fold: dict[str, int]
) -> pd.DataFrame:
    """n, batches, diagnoses and V for the test and training part of every split."""
    fold = ann[rl.COHORT_COL].map(cohort_fold)
    n_dx_scenario = ann["diagnosis_3class"].nunique()
    rows = []
    for k in range(N_FOLDS):
        for part, mask in (("test", fold == k), ("train", fold != k)):
            sub = ann[mask]
            counts = sub["diagnosis_3class"].value_counts()
            rows.append(
                {
                    "scenario": scenario,
                    "fold": k + 1,
                    "part": part,
                    "n_samples": len(sub),
                    "n_cohorts": sub[rl.COHORT_COL].nunique(),
                    "n_batches": sub[rl.BATCH_COL].nunique(),
                    **{
                        f"n_{g.replace(' ', '_')}": int(counts.get(g, 0))
                        for g in rl.DIAGNOSIS_ORDER
                    },
                    "cramers_v_major_group": rl.cramers_v(
                        sub[rl.BATCH_COL], rl.major_group(sub, 5)
                    ),
                    "meets_constraints": bool(
                        sub[rl.BATCH_COL].nunique() >= 2
                        and (
                            n_dx_scenario < 2 or sub["diagnosis_3class"].nunique() >= 2
                        )
                    ),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    """Build the folds of the four scenarios."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    fold_rows, sample_rows, summaries = [], [], []
    for scenario, strategy in SCENARIO_STRATEGIES.items():
        ann = scenario_annotation(strategy)
        cohort_fold = best_folds(ann)
        sizes = ann[rl.COHORT_COL].value_counts()
        fold_rows += [
            {
                "scenario": scenario,
                "strategy": strategy,
                "cohort": c,
                "fold": k + 1,
                "n_samples": int(sizes[c]),
            }
            for c, k in sorted(cohort_fold.items(), key=lambda x: (x[1], x[0]))
        ]
        fold = ann[rl.COHORT_COL].map(cohort_fold)
        for k in range(N_FOLDS):
            for part, mask in (("test", fold == k), ("train", fold != k)):
                sample_rows += [
                    {"scenario": scenario, "fold": k + 1, "part": part, "sample_id": s}
                    for s in ann.index[mask]
                ]
        summaries.append(summarize(ann, scenario, cohort_fold))
    summary = pd.concat(summaries, ignore_index=True)
    print(summary[summary["part"] == "test"].to_string(index=False))
    print(
        f"test folds missing a constraint: "
        f"{int((~summary.loc[summary.part == 'test', 'meets_constraints']).sum())} of 20"
    )
    if args.dry_run:
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(fold_rows).to_csv(OUT_DIR / "folds.tsv", sep="\t", index=False)
    pd.DataFrame(sample_rows).to_csv(
        OUT_DIR / "fold_samples.tsv", sep="\t", index=False
    )
    summary.to_csv(OUT_DIR / "fold_summary.tsv", sep="\t", index=False)
    print(f"wrote folds.tsv, fold_samples.tsv, fold_summary.tsv to {OUT_DIR}")


if __name__ == "__main__":
    main()
