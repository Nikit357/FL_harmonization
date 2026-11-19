"""
r22_v1_evaluate.py — leave-cohort-out validation of the recommendations (plan WP7 7.3).

Answers Reviewer 1, comment 2 (selection bias): is the method the rule chooses on 4/5 of
the cohorts still among the best on the 1/5 of cohorts it never saw?

Runs on JupyterHub after the pods: needs `output/wp7/v1_metrics.parquet`, written by
`python r12_revision_metrics.py --experiment leave_cohort_out --concat`.

BLINDNESS: the selection rule is applied here, so the rule version approved at gate G2b
must be frozen (its MD5 in FROZEN_MD5.txt) — the same check as r04. Pass the approved
file with --rule (version 1 by default, `adjudication_rule_261029_v2.md` if amended).

Procedure (fixed in the plan before the runs)
---------------------------------------------
For every scenario (C RNA-seq only, K FFPE only, J FF only, S0 all samples) × fold:
1. Training part: the 31 methods are scored (`revision_lib.score_runs`, scaled on the
   main-benchmark range), gated exactly as in r04 (gate L: L ≥ 0.7; gate N: N ≥ N of the
   unharmonized arm of the same part − 0.05 and above the permutation null), and ranked
   in rule order (`revision_lib.rule_order`: candidates first, Pareto layer on batch
   removal × diagnosis retention, then the scaled Local-batch bar). Chosen method = rank 1;
   the whole training front is kept as the "recommended set".
2. Test part: the same scoring, gates and ranking on the test runs. Readouts of the
   chosen method: rank on test, top-1 / top-3 hit, gate pass on test, and regret on each
   bar and axis = best value on test − value of the chosen method on test (scaled units;
   0 = no regret).
3. Baseline: a random method — expected top-k hit rate k / n_ranked and the mean regret
   over all methods. (No baseline from the submitted version: Daniil 2026-11-07, the
   revision never compares its results with the pre-revision ones.)
4. Folds whose test part has a single batch or a single diagnosis (plan caveat C4) get
   `test_evaluable = False`: batch bars and gate N are undefined there; the row is kept
   and reported, never dropped silently.

Outputs (output/wp7/)
---------------------
v1_scores.parquet       every run scored, gated and ranked (per scenario × fold × part)
v1_fold_results.tsv     one row per scenario × fold × evaluated role (chosen / random)
v1_summary.tsv          per scenario and overall: top-1 / top-3 hit rates of the chosen
                        method vs a random method, median rank, median regret

Usage
-----
python r22_v1_evaluate.py [--rule adjudication_rule_261029.md]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import r04_apply_rule as rule
import revision_lib as rl

OUT_DIR = rl.OUTPUT_DIR / "wp7"
METRICS_PATH = OUT_DIR / "v1_metrics.parquet"
FOLD_SUMMARY_PATH = OUT_DIR / "fold_summary.tsv"

REGRET_COLUMNS: tuple[str, ...] = (
    "batch_removal",
    "biology_retention",
    *(f"{bar}_scaled" for bar in rl.FOUR_SCORE_BARS),
    "L",
    "N",
)
TOP_K: tuple[int, ...] = (1, 3)


def gate_and_rank(part: pd.DataFrame) -> pd.DataFrame:
    """
    Gates of r04 and the full rule order inside one scenario × fold × part.

    r04.apply_gates keys the unharmonized N on (strat, imp, post_rm); here the part id
    plays the role of the strategy, so the reference is the 01_raw run of the same part.
    """
    frame = part.assign(
        strat=part["subset_id"],
        imp="softimpute",
        method=part["arm"],
        post_rm=False,
        in_analysis_set=True,
    )
    # A run that returned its input is a method failure (gate G2 choice 5).
    frame["identical_to_raw"] = rl.flag_identical_to_raw(frame)
    gated = rule.apply_gates(frame)
    gated["rule_rank"] = rl.rule_order(gated)
    gated["n_ranked"] = len(gated)
    return gated


def regret(test: pd.DataFrame, method: str) -> dict:
    """best on test − method on test, for every regret column (NaN if not run)."""
    row = test[test["method"] == method]
    result = {}
    for column in REGRET_COLUMNS:
        best = test[column].max()
        value = row[column].iloc[0] if len(row) else np.nan
        result[f"regret_{column}"] = best - value
    return result


def evaluate_method(test: pd.DataFrame, method: str) -> dict:
    """Rank, top-k hits and gate pass of one method on a test part."""
    row = test[test["method"] == method]
    if row.empty:
        return {"rank_on_test": np.nan, "gate_pass_on_test": np.nan}
    rank = int(row["rule_rank"].iloc[0])
    return {
        "rank_on_test": rank,
        **{f"top{k}_hit": rank <= k for k in TOP_K},
        "gate_pass_on_test": bool(row["candidate"].iloc[0]),
        **regret(test, method),
    }


def random_baseline(test: pd.DataFrame) -> dict:
    """Expected readouts of a method drawn at random among the test runs."""
    n = len(test)
    out = {f"top{k}_hit": min(k, n) / n for k in TOP_K}
    out["rank_on_test"] = (n + 1) / 2
    out["gate_pass_on_test"] = float(test["candidate"].mean())
    for column in REGRET_COLUMNS:
        out[f"regret_{column}"] = float((test[column].max() - test[column]).mean())
    return out


def test_evaluable(fold_summary: pd.DataFrame, scenario: str, fold: int) -> bool:
    """False when the test part has one batch or one diagnosis (plan caveat C4)."""
    row = fold_summary[
        (fold_summary["scenario"] == scenario)
        & (fold_summary["fold"] == fold)
        & (fold_summary["part"] == "test")
    ]
    if row.empty:
        return False
    row = row.iloc[0]
    n_dx = sum(int(row[f"n_{g.replace(' ', '_')}"] > 0) for g in rl.DIAGNOSIS_ORDER)
    return bool(row["n_batches"] >= 2 and n_dx >= 2)


def evaluate(scored: pd.DataFrame, fold_summary: pd.DataFrame) -> pd.DataFrame:
    """One row per scenario × fold × evaluated role (chosen, random)."""
    rows = []
    for (scenario, fold), runs in scored.groupby(["scenario", "fold"]):
        train = runs[runs["part"] == "train"]
        test = runs[runs["part"] == "test"]
        base = {
            "scenario": scenario,
            "fold": int(fold),
            "test_evaluable": test_evaluable(fold_summary, scenario, int(fold)),
            "n_train_runs": len(train),
            "n_test_runs": len(test),
        }
        if train.empty or test.empty:
            rows.append({**base, "role": "missing part"})
            continue
        chosen = train.sort_values("rule_rank").iloc[0]
        front = train[(train["candidate"]) & (train["_front"])]["method"].tolist()
        rows.append(
            {
                **base,
                "role": "chosen on the training part",
                "method": chosen["method"],
                "chosen_was_candidate": bool(chosen["candidate"]),
                "training_front": ";".join(front),
                **evaluate_method(test, chosen["method"]),
            }
        )
        rows.append({**base, "role": "random method", **random_baseline(test)})
    table = pd.DataFrame(rows)
    table["method_display"] = table["method"].map(
        lambda m: rl.method_display_name(m) if isinstance(m, str) else ""
    )
    return table


def summarise(results: pd.DataFrame) -> pd.DataFrame:
    """Hit rates, median rank and median regret per scenario × role, plus overall."""
    numeric = [
        c
        for c in results.columns
        if c.startswith(("top", "regret_"))
        or c in ("rank_on_test", "gate_pass_on_test")
    ]
    frames = []
    for label, subset in (
        ("all folds", results),
        ("evaluable test folds only", results[results["test_evaluable"]]),
    ):
        data = subset.copy()
        data[numeric] = data[numeric].astype(float)
        per = data.groupby(["scenario", "role"])[numeric].agg("mean")
        per["n_folds"] = data.groupby(["scenario", "role"]).size()
        overall = data.groupby("role")[numeric].agg("mean")
        overall["n_folds"] = data.groupby("role").size()
        overall.index = pd.MultiIndex.from_product([["overall"], overall.index])
        frames.append(pd.concat([per, overall]).assign(fold_set=label))
    return pd.concat(frames).reset_index()


def main() -> None:
    """Score, gate and rank the leave-cohort-out runs; evaluate the transfer."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--rule", default=str(rule.DEFAULT_RULE))
    args = parser.parse_args()
    digest = rule.assert_rule_frozen(Path(args.rule))
    if not METRICS_PATH.exists():
        raise SystemExit(
            f"{METRICS_PATH} is missing: run `python r12_revision_metrics.py "
            "--experiment leave_cohort_out --concat` after the pod runs (RUNBOOK.md)."
        )
    metrics = pd.read_parquet(METRICS_PATH)
    metrics = metrics[metrics["status"] == "ok"]
    scored = rl.score_runs(metrics, rl.bar_scaling_reference())
    parts = []
    for _, part in scored.groupby("subset_id"):
        gated = gate_and_rank(part)
        gated["_front"] = rl.pareto_front(
            gated.where(gated["candidate"]), ["batch_removal", "biology_retention"]
        )
        parts.append(gated)
    ranked = pd.concat(parts, ignore_index=True)
    ranked.assign(rule_md5=digest).to_parquet(OUT_DIR / "v1_scores.parquet")

    results = evaluate(ranked, pd.read_csv(FOLD_SUMMARY_PATH, sep="\t"))
    results.to_csv(OUT_DIR / "v1_fold_results.tsv", sep="\t", index=False)
    summary = summarise(results)
    summary.to_csv(OUT_DIR / "v1_summary.tsv", sep="\t", index=False)
    chosen = results[results["role"] == "chosen on the training part"]
    print(
        f"top-3 transfer: {int(chosen['top3_hit'].sum())} of {len(chosen)} folds "
        f"({int(chosen.loc[chosen['test_evaluable'], 'top3_hit'].sum())} of "
        f"{int(chosen['test_evaluable'].sum())} evaluable)"
    )
    print(summary.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
