"""
r05_robustness.py — robustness of the selection to panel and weighting choices (plan WP5).

Answers Reviewer 1, comment 3 and Reviewer 2, comment 2 (iii): does the selection depend
on how the metrics were reduced or weighted?

BLINDNESS: this script ranks approaches with the selection rule, so it refuses to run
until the rule version approved at gate G2b is frozen (MD5 in FROZEN_MD5.txt), exactly
like r04. Run it after r04 and after gate G2b.

Variants (each gives a full rule ranking per scenario pool of r04)
--------------------------------------------------------------------
reference            the four bars of r03 (22-metric panel at cut 0.2, headlines of
                     bar_headlines.tsv)
panel_cut0.1 / 0.3   the panel rebuilt at |ρ| ≥ 0.9 / 0.7 (output/wp2/panel_variants.tsv),
                     medoid headline per bar
all_87_metrics       the panel built from all 87 metrics at cut 0.2, medoid headline
axis_mean            bar = mean of all scaled panel metrics of the bar (decision D7
                     alternative)
group_balanced       bar = mean over metric groups of the mean scaled metric of the group
                     (each group A–K weighs 1)
local_runner_up      the two local bars = the runner-up metric of their medoid tie (UMAP
                     entropy on batch, cLISI on diagnosis) instead of kBET / graph
                     connectivity (gate G1 (b), Daniil 2026-11-03: fixed before G2b)
bridging_biology     the two diagnosis bars recomputed on multi-diagnosis batches only
                     (output/wp8/bridging_biology.parquet, metrics pod); skipped with a
                     note when that file does not exist yet

The gates (L, N) are the same in every variant; only the bars and therefore the Pareto
axes change. Ranking = `revision_lib.rule_order` (candidates first, Pareto layer, then
the scaled Local-batch bar).

Statistics per scenario × variant (against the reference)
----------------------------------------------------------
kendall_tau_b      between the two rankings of the scenario pool
top3_jaccard       overlap of the first three approaches
front_jaccard      overlap of the two Pareto fronts
and per approach: front_stability = share of variants (reference included) in which the
approach is on its scenario front.

Outputs (output/wp5/)
---------------------
robustness_summary.tsv      scenario × variant statistics (input of Supplementary Figure S16)
front_stability.tsv         approach × scenario: front membership per variant + stability,
                            column selected_after_visual_check (final G2b selection)
variant_bar_headlines.tsv   the headline metric of every bar in every variant

Usage
-----
python r05_robustness.py [--rule adjudication_rule_261029.md]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

import r04_apply_rule as rule
import revision_lib as rl
from r03_four_scores import bar_headline, scale_like_analysis_set

OUT_DIR = rl.OUTPUT_DIR / "wp5"
FOUR_SCORES_PATH = rl.OUTPUT_DIR / "wp3/four_scores.parquet"
PANEL_PATH = rl.OUTPUT_DIR / "wp2/reduced_panel.tsv"
PANEL_VARIANTS_PATH = rl.OUTPUT_DIR / "wp2/panel_variants.tsv"
BRIDGING_PATH = rl.OUTPUT_DIR / "wp8/bridging_biology.parquet"
VETOES_PATH = rl.OUTPUT_DIR / "wp4/vetoes.tsv"

PANEL_VARIANT_MAP: dict[str, str] = {
    "panel_cut0.1": "33_cut0.1",
    "panel_cut0.3": "33_cut0.3",
    "all_87_metrics": "87_cut0.2",
}
TOP_K = 3


def add_rule_axes(scores: pd.DataFrame) -> pd.DataFrame:
    """batch_removal / biology_retention from the four `_scaled` bars (as in r03)."""
    scores = scores.copy()
    scores["batch_removal"] = scores[
        ["global_batch_scaled", "local_batch_scaled"]
    ].mean(axis=1, skipna=False)
    scores["biology_retention"] = scores[
        ["global_biology_scaled", "local_biology_scaled"]
    ].mean(axis=1, skipna=False)
    return scores


def bars_from_panel(
    table: pd.DataFrame, panel: pd.DataFrame, mode: str
) -> tuple[pd.DataFrame, list[dict]]:
    """
    The four `_scaled` bars of every approach for one panel and one bar mode.

    Parameters
    ----------
    table : Supplementary File 3 (all 2,407 approaches) with `in_analysis_set`.
    panel : rows metric / metric_group / polarity / four_score_bar.
    mode : "medoid", "axis_mean" or "group_balanced".

    Returns
    -------
    (frame of the four `<bar>_scaled` columns, headline records)
    """
    polarity = panel.set_index("metric")["polarity"]
    scaled = scale_like_analysis_set(table, polarity, table["in_analysis_set"])
    adjusted = table[polarity.index].mul(polarity, axis=1)
    abs_rho = rl.abs_spearman(adjusted[table["in_analysis_set"]])
    bars, headlines = pd.DataFrame(index=table.index), []
    for bar in rl.FOUR_SCORE_BARS:
        members = panel[panel["four_score_bar"] == bar]
        names = members["metric"].tolist()
        if mode == "medoid":
            headline, how = bar_headline(names, abs_rho)
            bars[f"{bar}_scaled"] = scaled[headline]
        elif mode == "axis_mean":
            headline, how = "mean of members", "axis mean"
            bars[f"{bar}_scaled"] = scaled[names].mean(axis=1, skipna=False)
        else:
            headline, how = "mean of group means", "group balanced"
            group_means = [
                scaled[group["metric"].tolist()].mean(axis=1, skipna=False)
                for _, group in members.groupby("metric_group")
            ]
            bars[f"{bar}_scaled"] = pd.concat(group_means, axis=1).mean(
                axis=1, skipna=False
            )
        headlines.append({"bar": bar, "headline": headline, "how": how})
    return bars, headlines


def bridging_bars(reference: pd.DataFrame) -> pd.DataFrame | None:
    """Reference bars with the two diagnosis bars taken from the bridging-batch check."""
    if not BRIDGING_PATH.exists():
        return None
    bridging = pd.read_parquet(BRIDGING_PATH)
    bridging = bridging[bridging["status"] == "ok"].copy()
    bridging["post_rm"] = bridging["post_rm"].astype(bool)
    scale = rl.bar_scaling_reference()
    merged = reference.merge(
        bridging, on=rl.APPROACH_KEYS, how="left", suffixes=("", "_bridging")
    )
    for bar in ("global_biology", "local_biology"):
        row = scale.loc[bar]
        values = pd.to_numeric(merged.get(row["headline_metric"]), errors="coerce")
        merged[f"{bar}_scaled"] = (values * row["polarity"] - row["low"]) / (
            row["high"] - row["low"]
        )
    return merged


def rank_pools(gated: pd.DataFrame, vetoed: set[tuple]) -> pd.DataFrame:
    """Rule rank and front flag of every approach inside every scenario pool of r04."""
    frames = []
    for name, pool in {**rule.SCENARIOS, **rule.INFORMATION_ONLY_SCENARIOS}.items():
        part = gated[gated["strat"].isin(pool)].copy()
        part = part[[tuple(k) not in vetoed for k in part[rl.APPROACH_KEYS].to_numpy()]]
        if part.empty:
            continue
        part["rule_rank"] = rl.rule_order(part)
        candidates = part.where(part["candidate"])
        part["on_front"] = rl.pareto_front(
            candidates, ["batch_removal", "biology_retention"]
        )
        frames.append(part.assign(scenario=name))
    return pd.concat(frames, ignore_index=True)


def jaccard(a: set, b: set) -> float:
    """|a ∩ b| / |a ∪ b| (NaN when both are empty)."""
    union = a | b
    return len(a & b) / len(union) if union else np.nan


def compare(reference: pd.DataFrame, variant: pd.DataFrame, name: str) -> list[dict]:
    """Kendall τ_b, top-3 and front Jaccard per scenario."""
    rows = []
    keys = rl.APPROACH_KEYS
    for scenario, ref in reference.groupby("scenario"):
        var = variant[variant["scenario"] == scenario]
        joined = ref.merge(var, on=keys, suffixes=("_ref", "_var"))
        top = {
            label: set(map(tuple, frame.nsmallest(TOP_K, "rule_rank")[keys].to_numpy()))
            for label, frame in (("ref", ref), ("var", var))
        }
        fronts = {
            label: set(map(tuple, frame.loc[frame["on_front"], keys].to_numpy()))
            for label, frame in (("ref", ref), ("var", var))
        }
        tau = kendalltau(joined["rule_rank_ref"], joined["rule_rank_var"]).statistic
        rows.append(
            {
                "scenario": scenario,
                "variant": name,
                "n_approaches": len(joined),
                "kendall_tau_b": float(tau),
                "top3_jaccard": jaccard(top["ref"], top["var"]),
                "front_jaccard": jaccard(fronts["ref"], fronts["var"]),
                "n_front_reference": len(fronts["ref"]),
                "n_front_variant": len(fronts["var"]),
            }
        )
    return rows


def main() -> None:
    """Rank every variant, compare with the reference, write the tables."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--rule", default=str(rule.DEFAULT_RULE))
    args = parser.parse_args()
    digest = rule.assert_rule_frozen(Path(args.rule))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    vetoes = (
        pd.read_csv(VETOES_PATH, sep="\t")
        if VETOES_PATH.exists()
        else pd.DataFrame(columns=rl.APPROACH_KEYS)
    )
    vetoed = set(map(tuple, vetoes[rl.APPROACH_KEYS].to_numpy()))

    reference_scores = pd.read_parquet(FOUR_SCORES_PATH)
    table = rl.load_supp_file_3(analysis_set_only=False)
    assert (
        table[rl.APPROACH_KEYS].to_numpy()
        == reference_scores[rl.APPROACH_KEYS].to_numpy()
    ).all(), "four_scores.parquet and Supplementary File 3 are not row-aligned"
    gate_columns = [
        "L",
        "N",
        "N_null_mean",
        "N_null_std",
        "N_perm_pvalue",
        "N2",
        "N2_null_mean",
        "N2_null_std",
        "N2_perm_pvalue",
        "identical_to_raw",
    ]
    base = reference_scores[rl.APPROACH_KEYS + ["in_analysis_set", *gate_columns]]

    variant_scores: dict[str, pd.DataFrame] = {"reference": reference_scores}
    headline_rows = []
    panels = pd.read_csv(PANEL_VARIANTS_PATH, sep="\t")
    panel = pd.read_csv(PANEL_PATH, sep="\t")
    for name, key in PANEL_VARIANT_MAP.items():
        bars, heads = bars_from_panel(table, panels[panels["variant"] == key], "medoid")
        variant_scores[name] = pd.concat([base, bars], axis=1)
        headline_rows += [{"variant": name, **h} for h in heads]
    for mode in ("axis_mean", "group_balanced"):
        bars, heads = bars_from_panel(table, panel, mode)
        variant_scores[mode] = pd.concat([base, bars], axis=1)
        headline_rows += [{"variant": mode, **h} for h in heads]
    runner_up = reference_scores.copy()
    for bar in ("local_batch", "local_biology"):
        runner_up[f"{bar}_scaled"] = reference_scores[f"{bar}_runner_up_scaled"]
    variant_scores["local_runner_up"] = runner_up
    bridging = bridging_bars(reference_scores)
    if bridging is None:
        print(f"bridging_biology skipped: {BRIDGING_PATH} does not exist yet")
    else:
        variant_scores["bridging_biology"] = bridging

    ranked = {
        name: rank_pools(rule.apply_gates(add_rule_axes(scores)), vetoed)
        for name, scores in variant_scores.items()
    }
    summary = pd.DataFrame(
        [
            row
            for name, frame in ranked.items()
            if name != "reference"
            for row in compare(ranked["reference"], frame, name)
        ]
    ).assign(rule_md5=digest)
    summary.to_csv(OUT_DIR / "robustness_summary.tsv", sep="\t", index=False)
    pd.DataFrame(headline_rows).to_csv(
        OUT_DIR / "variant_bar_headlines.tsv", sep="\t", index=False
    )

    keys = [*rl.APPROACH_KEYS, "scenario"]
    membership = ranked["reference"][keys + ["on_front"]].rename(
        columns={"on_front": "reference"}
    )
    for name, frame in ranked.items():
        if name != "reference":
            membership = membership.merge(
                frame[keys + ["on_front"]].rename(columns={"on_front": name}),
                on=keys,
                how="left",
            )
    variant_names = list(ranked)
    membership["front_stability"] = (
        membership[variant_names].fillna(False).astype(float).mean(axis=1)
    )
    membership = membership[membership[variant_names].fillna(False).any(axis=1)]
    membership["method_display"] = membership["method"].map(rl.method_display_name)
    # final selection of gate G2b (accepted at the visual check, check closed 2026-11-07)
    selection_path = rl.OUTPUT_DIR / "wp4/selection_after_visual_check.tsv"
    if selection_path.exists():
        selection = rule.read_decisions(selection_path)
        selected = set(map(tuple, selection[keys].to_numpy()))
        membership["selected_after_visual_check"] = [
            tuple(k) in selected for k in membership[keys].to_numpy()
        ]
    membership.sort_values(
        ["scenario", "front_stability"], ascending=[True, False]
    ).to_csv(OUT_DIR / "front_stability.tsv", sep="\t", index=False)
    print(summary.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
