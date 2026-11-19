"""
r03_four_scores.py — the four scores that replace the composite (plan WP3; D3, D7).

Reanalysis only. Answers Reviewer 2, comment 2 (ii) and Arsen's request.

Scores
------
- L  marker correlation preservation: `mk_rho_mean_all_genes_narrow_set` (ρ)
- N  cross-batch diagnosis prediction: `pv_lobo3_f1_macro_mean` (leave-one-batch-out
     3-class macro-F1), with its permutation null (`…_perm_mean`, `…_perm_std`,
     `pv_lobo3_f1_perm_pvalue`)
- four bars, decision D7: ONE headline metric per bar, in its native unit — the medoid
  (highest summed |ρ| to the other metrics of the bar) of the reduced-panel metrics of
  that bar (output/wp2/reduced_panel.tsv). A two-metric bar has no unique medoid; the
  tie is broken by r02's SIMPLICITY_ORDER and logged in bar_headlines.tsv.
- HEADLINE_OVERRIDES: a headline fixed by Daniil at gate G1 instead of the medoid
  (logged in bar_headlines.tsv, column `how`).
- robustness variants (WP5): bar = mean of the min-max-scaled, polarity-adjusted panel
  metrics of the bar (`*_axis_mean`); and, for the two local bars, bar = the runner-up
  metric of the medoid tie (`*_runner_up_scaled`; gate G1 (b), Daniil 2026-11-03).
- N2 = the two-class (DLBCL vs FL) version of N with its null; gate N uses it for
  rl.TWO_CLASS_N_STRATEGIES (gate G2, Daniil 2026-11-03).
- identical_to_raw: the approach returned the unharmonized matrix (gate G2 choice 5;
  rl.flag_identical_to_raw: PC regression and ASW on batch / diagnosis equal to the
  01_raw row of the same strategy, imputation and post-removal).
- `batch_removal` = mean(scaled global_batch, scaled local_batch) and `biology_retention`
  = mean(scaled global_biology, scaled local_biology): the two Pareto axes of the rule
  (WP4). These are internal; no total of the four scores is computed anywhere.

The L / N values come from metrics_comprehensive_260905.csv (blind-check concat; the
only table with them); the 87 published metrics come from Supplementary File 3.

Outputs
-------
output/wp3/four_scores.parquet   2,407 approaches (flag in_analysis_set), all columns
output/wp3/bar_headlines.tsv     headline metric of each bar, members, tie-breaks
output/wp3/ln_coverage.tsv       approaches without L or N (reported, never imputed)
output/wp1/strategy_v_vs_best_scores.tsv   WP1 step 1.4 (if WP1 output exists)

Usage
-----
python r03_four_scores.py
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import revision_lib as rl
from r02_reduced_panel import simplicity_rank

OUT_DIR = rl.OUTPUT_DIR / "wp3"
PANEL_PATH = rl.OUTPUT_DIR / "wp2/reduced_panel.tsv"
ABS_RHO_PATH = rl.OUTPUT_DIR / "wp2/metric_abs_spearman.parquet"
WP1_PATH = rl.OUTPUT_DIR / "wp1/confounding_by_strategy.tsv"


# Gate G1, question Q1 (Daniil, 2026-11-03): after the two distance ratios left the
# panel, the medoid of Global biology moved from PC regression on diagnosis to WaterMelon
# mean biology. Daniil kept PC regression on diagnosis, for symmetry with the Global
# batch bar (PC regression on batch); a stated exception to the medoid rule (D7).
HEADLINE_OVERRIDES: dict[str, tuple[str, str]] = {
    "global_biology": (
        "PCReg_Diagnosis_cell_type_unified",
        "fixed by Daniil at gate G1 (Q1, 2026-11-03) for symmetry with the batch bar",
    ),
}


def bar_headline(members: list[str], abs_rho: pd.DataFrame) -> tuple[str, str]:
    """Medoid of a bar; ties (always for two metrics) broken by simplicity order."""
    if len(members) == 1:
        return members[0], "single metric"
    block = abs_rho.loc[members, members]
    summed = block.sum(axis=1).round(6)
    best = summed[summed == summed.max()].index.tolist()
    if len(best) == 1:
        return best[0], "medoid"
    chosen = min(best, key=simplicity_rank)
    return chosen, f"medoid tie among {';'.join(best)}; simpler statistic chosen"


def scale_like_analysis_set(
    values: pd.DataFrame, polarity: pd.Series, analysis_mask: pd.Series
) -> pd.DataFrame:
    """Polarity-adjust and min-max scale with the range of the analysis set."""
    adjusted = values[polarity.index].mul(polarity, axis=1)
    low = adjusted[analysis_mask].min()
    span = (adjusted[analysis_mask].max() - low).replace(0, np.nan)
    return (adjusted - low) / span


def main() -> None:
    """Compute the four scores for all 2,407 approaches."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = pd.read_csv(PANEL_PATH, sep="\t")
    abs_rho = pd.read_parquet(ABS_RHO_PATH)
    table = rl.load_supp_file_3(analysis_set_only=False)
    ln = rl.load_ln_columns()
    merged = table.merge(ln, on=rl.APPROACH_KEYS, how="left", validate="one_to_one")
    assert len(merged) == len(table)

    polarity = panel.set_index("metric")["polarity"]
    scaled = scale_like_analysis_set(merged, polarity, merged["in_analysis_set"])

    headline_rows = []
    scores = merged[rl.APPROACH_KEYS + ["in_analysis_set"]].copy()
    scores["method_display"] = scores["method"].map(rl.method_display_name)
    scores["L"] = merged[rl.L_SCORE_COL]
    scores["N"] = merged[rl.N_SCORE_COL]
    scores["N_null_mean"] = merged[rl.N_NULL_MEAN_COL]
    scores["N_null_std"] = merged[rl.N_NULL_STD_COL]
    scores["N_perm_pvalue"] = merged[rl.N_PVALUE_COL]
    scores["N2"] = merged[rl.N2_SCORE_COL]
    scores["N2_null_mean"] = merged[rl.N2_NULL_MEAN_COL]
    scores["N2_null_std"] = merged[rl.N2_NULL_STD_COL]
    scores["N2_perm_pvalue"] = merged[rl.N2_PVALUE_COL]
    scores["identical_to_raw"] = False
    in_set = merged["in_analysis_set"]
    scores.loc[in_set, "identical_to_raw"] = rl.flag_identical_to_raw(
        merged[in_set]
    )
    for bar in rl.FOUR_SCORE_BARS:
        members = panel.loc[panel["four_score_bar"] == bar, "metric"].tolist()
        headline, how = bar_headline(members, abs_rho)
        runner_up = ""
        if how.startswith("medoid tie"):
            tied = [
                m for m in members if m != headline
            ]
            runner_up = tied[0] if len(tied) == 1 else ""
        if bar in HEADLINE_OVERRIDES:
            medoid_choice = headline
            headline, how = HEADLINE_OVERRIDES[bar]
            how = f"{how} (medoid: {medoid_choice})"
            if headline not in members:
                raise ValueError(f"override {headline} is not a {bar} panel metric")
        if runner_up:
            scores[f"{bar}_runner_up_scaled"] = scaled[runner_up]
        headline_rows.append(
            {
                "bar": bar,
                "headline_metric": headline,
                "how": how,
                "polarity": int(polarity[headline]),
                "runner_up": runner_up,
                "members": ";".join(members),
                "n_members": len(members),
            }
        )
        scores[bar] = merged[headline]
        scores[f"{bar}_scaled"] = scaled[headline]
        scores[f"{bar}_axis_mean"] = scaled[members].mean(axis=1, skipna=False)
    scores["batch_removal"] = scores[
        ["global_batch_scaled", "local_batch_scaled"]
    ].mean(axis=1, skipna=False)
    scores["biology_retention"] = scores[
        ["global_biology_scaled", "local_biology_scaled"]
    ].mean(axis=1, skipna=False)
    scores["batch_removal_axis_mean"] = scores[
        ["global_batch_axis_mean", "local_batch_axis_mean"]
    ].mean(axis=1, skipna=False)
    scores["biology_retention_axis_mean"] = scores[
        ["global_biology_axis_mean", "local_biology_axis_mean"]
    ].mean(axis=1, skipna=False)

    scores.to_parquet(OUT_DIR / "four_scores.parquet", index=False)
    headlines = pd.DataFrame(headline_rows)
    headlines.to_csv(OUT_DIR / "bar_headlines.tsv", sep="\t", index=False)

    analysis = scores[scores["in_analysis_set"]]
    coverage = pd.DataFrame(
        {
            "score": ["L", "N"] + list(rl.FOUR_SCORE_BARS),
            "n_missing_analysis_set": [
                int(analysis[c].isna().sum()) for c in ["L", "N", *rl.FOUR_SCORE_BARS]
            ],
            "n_analysis_set": len(analysis),
        }
    )
    coverage.to_csv(OUT_DIR / "ln_coverage.tsv", sep="\t", index=False)
    missing = analysis[analysis[["L", "N"]].isna().any(axis=1)][
        rl.APPROACH_KEYS + ["L", "N"]
    ]
    missing.to_csv(OUT_DIR / "ln_missing_approaches.tsv", sep="\t", index=False)
    print(
        headlines[["bar", "headline_metric", "how", "n_members"]].to_string(index=False)
    )
    print(coverage.to_string(index=False))

    if WP1_PATH.exists():
        strategy_v = pd.read_csv(WP1_PATH, sep="\t").set_index("strategy")
        best = analysis.groupby("strat")[
            ["global_biology_scaled", "local_biology_scaled"]
        ].max()
        joined = best.join(strategy_v["V_batch_x_diagnosis"], how="inner")
        rows = [
            {
                "score": c,
                "n_strategies": len(joined),
                "spearman_rho": spearmanr(
                    joined["V_batch_x_diagnosis"], joined[c]
                ).statistic,
                "pvalue": spearmanr(joined["V_batch_x_diagnosis"], joined[c]).pvalue,
            }
            for c in ["global_biology_scaled", "local_biology_scaled"]
        ]
        joined.to_csv(rl.OUTPUT_DIR / "wp1/strategy_v_vs_best_scores.tsv", sep="\t")
        pd.DataFrame(rows).to_csv(
            rl.OUTPUT_DIR / "wp1/strategy_v_vs_best_scores_spearman.tsv",
            sep="\t",
            index=False,
        )
        print(json.dumps(rows, indent=1, default=float))


if __name__ == "__main__":
    main()
