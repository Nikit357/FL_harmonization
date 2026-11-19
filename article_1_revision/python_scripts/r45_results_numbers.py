"""
r45_results_numbers.py — every number quoted in the revised text → output/numbers.json.

CLAUDE.md hard rule 5: numbers in the manuscript and the response letter are read from
`output/**` by this script, never typed. r50 (tracked edits) and r60 (response letter)
format their sentences from `numbers.json`; r99 checks that each quoted value appears in
the text where it is cited.

The script is re-run whenever a work package lands. Each number is one entry:

    "key": {"value": …, "display": "0.358", "source": "output/wp1/…", "status": "ready"}

Numbers whose source does not exist yet are written with `"status": "pending"` and the
step they wait for, so that r50 / r60 can refuse to fill a sentence too early.

It also computes one table that the text needs and no other script makes: η² of the four
design factors (strategy, method, imputation, post-removal) over the reduced panel, with
the formula of the submitted Figure 6B (mean over metrics of the one-way η² on the
analysis set), plus the same on the 87 metrics as a check against the submitted values
(0.3629 / 0.2564 / 0.0155 / 0.0020; plan §3.5). → output/wp3/eta_squared.tsv

Usage
-----
python r45_results_numbers.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import revision_lib as rl

OUT = rl.OUTPUT_DIR / "numbers.json"
O = rl.OUTPUT_DIR
FACTORS: dict[str, str] = {
    "strat": "Strategy",
    "method": "Method",
    "imp": "Imputation",
    "post_rm": "Post-removal",
}

numbers: dict[str, dict] = {}


def put(key: str, value: object, source: Path, fmt: str = "{:.3f}") -> None:
    """Record a ready number with its display string and source file."""
    if isinstance(value, (np.integer, np.floating)):
        value = value.item()
    if isinstance(value, float):
        display = fmt.format(value)
    elif isinstance(value, int):
        display = f"{value:,}"
    else:
        display = str(value)
    numbers[key] = {
        "value": value,
        "display": display,
        "source": str(source.relative_to(rl.REVISION_DIR)),
        "status": "ready",
    }


def pending(key: str, waits_for: str) -> None:
    """Record a number that cannot be computed yet."""
    numbers[key] = {"value": None, "status": "pending", "waits_for": waits_for}


def eta_squared(table: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    """Mean one-way η² over the metrics for each factor (submitted Figure 6B formula)."""
    rows = []
    for factor, label in FACTORS.items():
        values = []
        for metric in metrics:
            sub = table[[factor, metric]].dropna()
            if sub[factor].nunique() < 2 or sub[metric].std() == 0:
                continue
            grand = sub[metric].mean()
            ss_total = ((sub[metric] - grand) ** 2).sum()
            ss_between = sum(
                len(g) * (g[metric].mean() - grand) ** 2 for _, g in sub.groupby(factor)
            )
            values.append(ss_between / ss_total if ss_total > 0 else 0.0)
        rows.append(
            {
                "factor": label,
                "eta2_mean": float(np.mean(values)),
                "n_metrics": len(values),
            }
        )
    return pd.DataFrame(rows)


def wp1() -> None:
    """Confounding diagnostics."""
    path = O / "wp1/confounding_by_strategy.tsv"
    table = pd.read_csv(path, sep="\t").set_index("strategy")
    s0 = table.loc["S0_no_removal"]
    put("cohort_V_batch_diagnosis", s0["V_batch_x_diagnosis"], path)
    put("cohort_AMI_batch_diagnosis", s0["AMI_batch_x_diagnosis"], path)
    put("cohort_V_batch_major_group", s0["V_batch_x_major_group"], path)
    put("n_single_dx_batches", int(s0["n_single_dx_batches"]), path)
    put("n_batches", int(s0["n_batches"]), path)
    put("n_samples_single_dx_batches", int(s0["n_samples_single_dx_batches"]), path)
    put(
        "pct_samples_single_dx_batches",
        s0["pct_samples_single_dx_batches"],
        path,
        "{:.1f}",
    )
    for strategy, row in table.iterrows():
        put(f"table1_V__{strategy}", row["V_batch_x_diagnosis"], path, "{:.2f}")
        put(
            f"table1_pct_single_dx__{strategy}",
            row["pct_samples_single_dx_batches"],
            path,
            "{:.1f}",
        )
    bridging_path = O / "wp1/bridging_batches.tsv"
    bridging = pd.read_csv(bridging_path, sep="\t")
    multi = bridging[bridging["bridging_batch"]]
    put("n_multi_dx_batches", len(multi), bridging_path)
    put("n_samples_multi_dx_batches", int(multi["n_samples"].sum()), bridging_path)
    put(
        "n_graph_components",
        int(bridging["n_components_in_graph"].iloc[0]),
        bridging_path,
    )
    vp_path = O / "wp1/variance_partition_raw.tsv"
    vp = pd.read_csv(vp_path, sep="\t").set_index("term")
    for term, value in vp["gene_median_R2"].items():
        put(f"variance_partition_median_R2__{term}", float(value), vp_path)


def wp2_wp3() -> None:
    """Reduced panel, headline metrics, η²."""
    summary_path = O / "wp2/panel_summary.json"
    summary = json.loads(summary_path.read_text())
    for key in (
        "n_universe",
        "n_panel",
        "complete_on_panel",
        "complete_on_87",
        "n_approaches",
    ):
        put(f"panel_{key}", int(summary[key]), summary_path)
    clusters = pd.read_csv(O / "wp2/cluster_membership.tsv", sep="\t")
    put(
        "panel_n_clusters",
        int(clusters["cluster_id"].nunique()),
        O / "wp2/cluster_membership.tsv",
    )
    headlines_path = O / "wp3/bar_headlines.tsv"
    for row in pd.read_csv(headlines_path, sep="\t").itertuples():
        put(f"headline__{row.bar}", row.headline_metric, headlines_path)

    table = rl.load_supp_file_3(analysis_set_only=True)
    table["post_rm"] = table["post_rm"].astype(str)
    panel = pd.read_csv(O / "wp2/reduced_panel.tsv", sep="\t")["metric"].tolist()
    polarity = rl.load_metric_polarity()
    all87 = [m for m in polarity.index[polarity["Polarity"] != 0] if m in table]
    eta = pd.concat(
        [
            eta_squared(table, panel).assign(metric_set="reduced panel"),
            eta_squared(table, all87).assign(metric_set="87 metrics (check)"),
        ]
    )
    eta_path = O / "wp3/eta_squared.tsv"
    eta.to_csv(eta_path, sep="\t", index=False)
    for row in eta.itertuples():
        tag = "panel" if row.metric_set == "reduced panel" else "all87"
        put(f"eta2_{tag}__{row.factor}", row.eta2_mean, eta_path, "{:.3f}")


def later_packages() -> None:
    """Numbers from the gates / pods: read when present, else pending."""
    # No concordance with the submitted visual picks: the revision never compares its
    # results with the pre-revision ones (Daniil, gate G4, 2026-11-07).
    lso = O / "wp4/leave_strategies_out.tsv"
    if lso.exists():
        table = pd.read_csv(lso, sep="\t")
        fsqn = table[
            (table.get("method") == "16_fsqn_r") & (table.get("pool") == "without")
        ]
        put("fsqn_on_front_without_A_B_E", int(fsqn["on_front"].sum()), lso)
    else:
        pending("fsqn_on_front_without_A_B_E", "r04 after gate G2")
    slopes = O / "wp6/gradient_slopes.tsv"
    if slopes.exists():
        table = pd.read_csv(slopes, sep="\t")
        put("gradient_n_meaningful_slopes", int(table["meaningful"].sum()), slopes)
        for row in table[
            table["score"].isin(["L", "N", "batch_removal", "biology_retention"])
        ].itertuples():
            put(f"gradient_slope__{row.arm}__{row.score}", row.slope, slopes)
    else:
        pending("gradient_slopes", "pods + r13")
    real_v = O / "wp6/real_data_v.json"
    if not real_v.exists():  # needs only the annotation, not the pods
        from r13_gradient_stats import real_data_v

        real_v.write_text(json.dumps(real_data_v(), indent=1))
    for key, value in json.loads(real_v.read_text()).items():
        put(f"real_data_V__{key}", value, real_v)
    v1 = O / "wp7/v1_fold_results.tsv"
    if v1.exists():
        results = pd.read_csv(v1, sep="\t")
        chosen = results[results["role"] == "chosen on the training part"]
        # A chosen method whose test run failed has no rank (NaN): counted as no hit.
        hit = {True: 1, False: 0, "True": 1, "False": 0}
        put("v1_n_folds", len(chosen), v1)
        put("v1_top3_hits", int(chosen["top3_hit"].map(hit).fillna(0).sum()), v1)
        put("v1_top1_hits", int(chosen["top1_hit"].map(hit).fillna(0).sum()), v1)
        put("v1_chosen_failed_on_test", int(chosen["rank_on_test"].isna().sum()), v1)
        evaluable = chosen[chosen["test_evaluable"].map(hit).fillna(0) == 1]
        put("v1_n_evaluable_folds", len(evaluable), v1)
        put(
            "v1_top3_hits_evaluable",
            int(evaluable["top3_hit"].map(hit).fillna(0).sum()),
            v1,
        )
    else:
        pending("v1_top3_hits", "pods + r22 (after gate G2b)")
    robustness = O / "wp5/robustness_summary.tsv"
    if robustness.exists():
        table = pd.read_csv(robustness, sep="\t")
        put(
            "robustness_median_tau",
            table["kendall_tau_b"].median(),
            robustness,
            "{:.2f}",
        )
        bridging = table[table["variant"] == "bridging_biology"]
        if len(bridging):
            put(
                "bridging_median_tau",
                bridging["kendall_tau_b"].median(),
                robustness,
                "{:.2f}",
            )
    else:
        pending(
            "robustness_median_tau", "r05 after gate G2b (+ r30 for the bridging tau)"
        )


def g4_numbers() -> None:
    """Numbers of the stage-B text (gate G4, 2026-11-07): selection, failures, gradient
    anchors and ranks, leave-cohort-out per scenario, robustness of the selected set."""
    selection_path = O / "wp4/selection_after_visual_check.tsv"
    selection = pd.read_csv(selection_path, sep="\t")
    selection = selection[selection["visual_check"] == "accepted"]
    put("n_selected", len(selection), selection_path)
    for leaf, count in selection["tree_leaf_name"].fillna("").value_counts().items():
        if leaf:
            put(f"n_selected__{leaf}", int(count), selection_path)
    for scenario, count in selection["scenario"].value_counts().items():
        put(f"n_selected_scenario__{scenario}", int(count), selection_path)
    visual_path = O / "wp4/visual_check.tsv"
    visual = pd.read_csv(visual_path, sep="\t")
    for (review_round, decision), count in visual.groupby(
        ["review_round", "decision"]
    ).size().items():
        put(f"visual_check_round{review_round}__{decision}", int(count), visual_path)
    put("visual_check_n_reviewed", len(visual), visual_path)

    scores_path = O / "wp3/four_scores.parquet"
    scores = pd.read_parquet(scores_path)
    scores = scores[scores["in_analysis_set"]] if "in_analysis_set" in scores else scores
    failed = scores[scores["identical_to_raw"].astype(bool)]
    put("n_identical_to_raw", len(failed), scores_path)
    for method, count in failed["method"].value_counts().items():
        put(f"n_identical_to_raw__{method}", int(count), scores_path)

    slopes_path = O / "wp6/gradient_slopes.tsv"
    slopes = pd.read_csv(slopes_path, sep="\t")
    for row in slopes.itertuples():
        put(f"gradient_at0__{row.arm}__{row.score}", row.mean_at_lambda0, slopes_path, "{:.2f}")
        put(f"gradient_at1__{row.arm}__{row.score}", row.mean_at_lambda1, slopes_path, "{:.2f}")
    main_scores = slopes[slopes["score"].isin(
        ["N", "L", "global_batch_scaled", "local_batch_scaled",
         "global_biology_scaled", "local_biology_scaled"])]
    tested = main_scores[main_scores["spearman_fdr"].notna()]
    put("gradient_main_tested", len(tested), slopes_path)
    put("gradient_main_changes", int(tested["changes_with_confounding"].sum()), slopes_path)
    ranks_path = O / "wp6/gradient_ranks.tsv"
    ranks = pd.read_csv(ranks_path, sep="\t")
    capped = ranks[ranks["cap"].astype(str) == "150"]
    raw = capped[capped["arm"] == "01_raw"]
    put("gradient_raw_rank_l0", raw.loc[raw["lambda"] == 0, "rule_rank"].median(), ranks_path, "{:.0f}")
    put("gradient_raw_rank_l05_06", raw.loc[raw["lambda"].between(0.5, 0.6), "rule_rank"].median(),
        ranks_path, "{:.0f}")
    put("gradient_n_arms", int(capped["n_ranked"].max()), ranks_path)
    # M-ComBat (added after G4) fails at λ = 1, so its high-confounding end is λ = 0.9.
    mcombat = capped[capped["arm"] == "29_combat_ref"]
    put("gradient_mcombat_rank_l05_09", mcombat.loc[mcombat["lambda"].between(0.5, 0.9),
        "rule_rank"].median(), ranks_path, "{:.0f}")
    for lam_key, lam in [("l0", 0.0), ("l09", 0.9)]:
        at_lambda = mcombat[np.isclose(mcombat["lambda"], lam)]
        for score in ["batch_removal", "biology_retention"]:
            put(f"gradient_mcombat_{score}_{lam_key}", at_lambda[score].mean(), ranks_path,
                "{:.2f}")
    # Supplementary Figure 5 (rebuilt 2026-11-08 on the 87 metrics, Daniil): medoid check, nb02.
    s5_path = O / "wp9/nb02_figS5_87_metric_clusters.tsv"
    s5 = pd.read_csv(s5_path, sep="\t")
    s5_panel = s5[s5["in_panel"]]
    holds_panel = s5.groupby("cluster")["panel_metrics_in_cluster"].first() > 0
    free = s5[~s5["cluster"].isin(holds_panel[holds_panel].index)]
    batch_or_dx = free["metric"].str.contains("RNA_BATCH|Diagnosis_cell_type_unified") | ~free[
        "metric"].str.contains("RNA_BATCH|Diagnosis_cell_type_unified|PLATFORM_RNA|RNASEQ_SOURCE|"
                               "COHORT_LABEL|TUMOR_NORMAL|Major_group")
    put("s5_n_clusters_87", int(s5["cluster"].nunique()), s5_path)
    put("s5_clusters_with_panel", int(holds_panel.sum()), s5_path)
    put("s5_clusters_without_panel", int((~holds_panel).sum()), s5_path)
    put("s5_free_clusters_batch_or_diagnosis", int(free.loc[batch_or_dx, "cluster"].nunique()), s5_path)
    put("s5_panel_medoid", int(s5_panel["is_medoid"].sum()), s5_path)
    put("s5_panel_not_medoid", int((~s5_panel["is_medoid"]).sum()), s5_path)
    gap = (s5_panel["medoid_mean_abs_rho"] - s5_panel["mean_abs_rho_to_cluster"]).max()
    put("s5_max_medoid_gap", gap, s5_path, "{:.2f}")
    # Figures 4–5 (rebuilt 2026-11-08, Daniil B1): one row per panel, written by nb08.
    panels_path = O / "wp9/nb08_figure_4_5_panels.tsv"
    panels = pd.read_csv(panels_path, sep="\t")
    for row in panels.itertuples():
        put(f"fig45__{row.panel}__n_samples", int(row.n_samples), panels_path, "{:,}")
        put(f"fig45__{row.panel}__pc1", row.pc1_variance_pct, panels_path, "{:.0f}")
        put(f"fig45__{row.panel}__pc1_raw", row.pc1_variance_pct_unharmonized, panels_path, "{:.0f}")
        put(f"fig45__{row.panel}__L", row.marker_correlation, panels_path, "{:.2f}")
        put(f"fig45__{row.panel}__N", row.prediction_f1, panels_path, "{:.2f}")
        put(f"fig45__{row.panel}__N_raw", row.prediction_f1_unharmonized, panels_path, "{:.2f}")
        put(f"fig45__{row.panel}__n_genes", int(row.n_genes), panels_path, "{:,}")
    both = capped.assign(both=capped["gate_L_pass"].astype(bool) & capped["gate_N_pass"].astype(bool))
    share = both.groupby("lambda")["both"].mean() * 100
    put("gradient_pct_pass_l0", share.loc[0.0], ranks_path, "{:.0f}")
    put("gradient_pct_pass_l1", share.loc[1.0], ranks_path, "{:.0f}")
    put("gradient_pct_pass_l05_09_min", share.loc[0.5:0.9].min(), ranks_path, "{:.0f}")
    put("gradient_pct_pass_l05_09_max", share.loc[0.5:0.9].max(), ranks_path, "{:.0f}")
    failures_path = O / "wp6/gradient_failures.tsv"
    put("gradient_n_failed", len(pd.read_csv(failures_path, sep="\t")), failures_path)

    v1_path = O / "wp7/v1_fold_results.tsv"
    v1 = pd.read_csv(v1_path, sep="\t")
    hit = {True: 1.0, False: 0.0, "True": 1.0, "False": 0.0}
    chosen = v1[v1["role"] == "chosen on the training part"]
    random = v1[v1["role"] == "random method"]
    put("v1_random_top3_pct", pd.to_numeric(random["top3_hit"]).mean() * 100, v1_path, "{:.1f}")
    for scenario, rows in chosen.groupby("scenario"):
        put(f"v1_top3_hits__{scenario}", int(rows["top3_hit"].map(hit).fillna(0).sum()), v1_path)
        put(f"v1_mean_rank__{scenario}", rows["rank_on_test"].mean(), v1_path, "{:.1f}")
    for scenario, rows in random.groupby("scenario"):
        put(f"v1_random_rank__{scenario}", rows["rank_on_test"].mean(), v1_path, "{:.1f}")
    tests_path = O / "wp9/nb05_v1_regret_tests.tsv"
    if tests_path.exists():
        for row in pd.read_csv(tests_path, sep="\t").itertuples():
            put(f"v1_regret_fdr__{row.panel}", row.q_fdr, tests_path, "{:.2g}")
            if "p_monte_carlo" in row._fields:  # nb05 since 2026-11-08 (decrease vs every test run)
                put(f"v1_regret_mc_p__{row.panel}", row.p_monte_carlo, tests_path, "{:.2g}")
                put(f"v1_regret_mc_q__{row.panel}", row.q_fdr_monte_carlo, tests_path, "{:.2g}")
    # S18a / S18b tests of nb05 (2026-11-08): random baseline as a distribution. Scenario
    # names in the tables are "code · name"; keys use the code (all = every scenario).
    scenario_code = {rl.STRATEGY_DISPLAY_NAMES[s]: rl.STRATEGY_CODES[s] for s in rl.STRATEGY_CODES}
    scenario_code["All scenarios"] = "all"
    rank_tests_path = O / "wp9/nb05_v1_rank_tests.tsv"
    if rank_tests_path.exists():
        rank_tests = pd.read_csv(rank_tests_path, sep="\t")
        for row in rank_tests.itertuples():
            code = scenario_code[row.scenario_name]
            put(f"v1_rank_p__{code}", row.p_empirical, rank_tests_path, "{:.2g}")
            put(f"v1_rank_q__{code}", row.q_fdr, rank_tests_path, "{:.2g}")
        put("v1_rank_q_min", rank_tests["q_fdr"].min(), rank_tests_path, "{:.2g}")
    hit_tests_path = O / "wp9/nb05_v1_hit_tests.tsv"
    if hit_tests_path.exists():
        for row in pd.read_csv(hit_tests_path, sep="\t").itertuples():
            code = scenario_code[row.scenario_name]
            put(f"v1_hit_p__{row.top_k}__{code}", row.p_exact, hit_tests_path, "{:.2g}")
            put(f"v1_hit_q__{row.top_k}__{code}", row.q_fdr, hit_tests_path, "{:.2g}")
            put(f"v1_hits__{row.top_k}__{code}", int(row.observed_hits), hit_tests_path, "{:d}")

    gates_path = O / "wp4/gates.tsv"
    gates = pd.read_csv(gates_path, sep="\t")
    gates = gates[gates["in_analysis_set"].astype(bool)]
    put("gate_L_pass", int(gates["gate_L_pass"].astype(bool).sum()), gates_path)
    put("gate_N_pass", int(gates["gate_N_pass"].astype(bool).sum()), gates_path)
    put("n_candidates", int(gates["candidate"].astype(bool).sum()), gates_path)
    for method in ("10_mnn", "12_scanorama", "11_harmony"):
        rows = gates[gates["method"] == method]
        put(f"gate_L_median__{method}", rows["L"].median(), gates_path, "{:.2f}")
        put(f"gate_L_pass_pct__{method}", rows["gate_L_pass"].astype(bool).mean() * 100,
            gates_path, "{:.0f}")
    leakage_path = O / "wp9/nb03_label_leakage.tsv"
    leakage = pd.read_csv(leakage_path, sep="\t")
    for _, row in leakage[leakage["lambda"].isin([0.0, 1.0])].iterrows():
        put(f"leakage_N__{row['arm']}__l{row['lambda']:.0f}", row["N_mean"], leakage_path, "{:.2f}")
    clusters_path = O / "wp9/nb02_fig3_clusters.tsv"
    clusters = pd.read_csv(clusters_path, sep="\t")
    for i, row in enumerate(clusters[clusters["axis"] == "approaches"].itertuples()):
        put(f"fig3_cluster_n__{row.cluster}", int(row.n), clusters_path)
        put(f"fig3_cluster_recommended__{row.cluster}", int(row.recommended), clusters_path)
    put("fig3_n_metric_clusters", int((clusters["axis"] == "metrics").sum()), clusters_path)
    put("fig3_n_approach_clusters", int((clusters["axis"] == "approaches").sum()), clusters_path)

    stability_path = O / "wp5/front_stability.tsv"
    stability = pd.read_csv(stability_path, sep="\t")
    selected = stability[stability["selected_after_visual_check"].astype(bool)]
    put("n_selected_stable_all_variants", int((selected["front_stability"] == 1).sum()), stability_path)
    robustness_path = O / "wp5/robustness_summary.tsv"
    robustness = pd.read_csv(robustness_path, sep="\t")
    put("robustness_median_top3_jaccard", robustness["top3_jaccard"].median(), robustness_path, "{:.2f}")
    put("robustness_min_tau", robustness["kendall_tau_b"].min(), robustness_path, "{:.2f}")
    put("robustness_max_tau", robustness["kendall_tau_b"].max(), robustness_path, "{:.2f}")


def main() -> None:
    """Collect every number and write numbers.json."""
    wp1()
    wp2_wp3()
    later_packages()
    g4_numbers()
    OUT.write_text(json.dumps(numbers, indent=1, ensure_ascii=False, default=str))
    ready = sum(v["status"] == "ready" for v in numbers.values())
    print(f"wrote {OUT}: {ready} ready, {len(numbers) - ready} pending")
    eta = pd.read_csv(O / "wp3/eta_squared.tsv", sep="\t")
    print(eta.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
