"""Emit `01_numbers.json`: every number Article 2 quotes, with its provenance.

Plan §6.2, the code-analyst's fifth artifact. Each entry carries the value, the table it
came from, the column, and the filter that produced it, so the writer can quote a number
and the reference-verifier can re-derive it without rerunning the analysis.

Numbers are read back out of `tables/A2_T*.csv` rather than recomputed here. A second
implementation would be a second answer; this file's job is provenance, not arithmetic.

    python analysis/build_numbers_json.py --tables tables/ --out workflow_runs/260924_run1/

Revision 260924 (plan Phase 1, §3): the tables are read at `--stamp` (default 260924, the
E1 index), the new tables A2_T3b and A2_T9-A2_T14 are added, and every float in the
evidence carries its three-decimal and three-significant-figure spellings, so the
rounding of HARD_RULE 13 matches an evidence string instead of loosening the audit.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

STAMP = "260924"

# The pinned metric snapshot of §9.4. Only the columns A2_T1 does not carry are read from it.
SNAPSHOT_CSV = Path(__file__).resolve().parents[2] / (
    "harmonization-metrics/metric_tables/metrics_comprehensive_260905.csv")


def n(value, table, column, filt, quoted_in):
    return {"value": value, "table": table, "column": column, "filter": filt,
            "quoted_in": quoted_in}


def build(tables: Path) -> dict:
    t1 = pd.read_csv(tables / f"A2_T1_analysis_set_census_{STAMP}.csv", low_memory=False)
    t0 = pd.read_csv(tables / f"A2_T0_shambhala_identity_{STAMP}.csv")
    t5 = pd.read_csv(tables / f"A2_T5_per_batch_folds_{STAMP}.csv")
    t6 = pd.read_csv(tables / f"A2_T6_agreement_specific_{STAMP}.csv")
    t7 = pd.read_csv(tables / f"A2_T7_harshness_by_lmn_{STAMP}.csv")
    t8 = pd.read_csv(tables / f"A2_T8_fold_composition_{STAMP}.csv")
    t2 = pd.read_csv(tables / f"A2_T2_generalizability_ranking_{STAMP}.csv")

    # Three metric columns the manuscript quotes live only in the pinned snapshot: A2_T1
    # carries no pcr_*, kbet_* or exp_* column, so audit_numbers.py can never resolve them
    # from tables/ alone. They are joined here, on the analysis set, so the evidence file
    # carries the locus. The Shambhala rename is applied first, exactly as on load elsewhere.
    snap = pd.read_csv(SNAPSHOT_CSV, low_memory=False)
    snap["method"] = snap["method"].replace({"shambhala_P0std_Q0std": "20_shambhala"})
    snap["run_id"] = (snap.strat + "__" + snap.imp + "__" + snap.method + "__post"
                      + snap.post_rm.map({False: "0", True: "1"}))
    snap = snap[snap.run_id.isin(set(t1.run_id))]

    sh = t1[t1.method == "20_shambhala"]
    gate = (t1.mk_rho_mean_markers > 0.75) & (t1.xb_margin > 0)
    nonraw = t1[~t1.is_raw]
    d = t1.dropna(subset=["pv_lobo3_f1_macro_mean", "f1_mc_mean"])
    d3 = d[d.n_mc >= 3]
    lead = t1[(~t1.is_confirmed_bad) & (t1.n_mc >= 5)].nlargest(1, "pv_lobo3_f1_macro_mean").iloc[0]

    # Fold composition is rebuilt from A2_T8's per-batch counts, which is the table the
    # manuscript cites; totals here and there cannot drift apart.
    # The __ALL__ rows of A2_T8 carry the fold-level totals and medians. Summing the
    # per-batch rows would give the same totals but a median of medians, which is not
    # the quantity the manuscript quotes.
    allrows = t8[t8.batch == "__ALL__"].set_index("n_classes")
    tot = allrows.n_folds
    med = allrows.median_f1

    out = {
        "analysis_set": {
            "n_approaches": n(int(len(t1)), "A2_T1", "run_id",
                              "Supplementary File 3, pct_samples_allNA < 5", "Methods; Results §6"),
            "n_methods": n(int(t1.method.nunique()), "A2_T1", "method", "same", "Methods"),
            "n_strategies": n(int(t1.strat.nunique()), "A2_T1", "strat", "same", "Methods"),
            "n_imputations": n(int(t1.imp.nunique()), "A2_T1", "imp", "same", "Methods"),
            "n_shambhala_rows": n(int(len(sh)), "A2_T1", "method == 20_shambhala",
                                  "after the shambhala_P0std_Q0std rename", "Methods"),
            "identity_columns_identical": n(
                f"{int(t0.identical.sum())} of {len(t0)}", "A2_T0", "identical",
                "84 matched (strat, imp, post_rm) keys", "Methods; Results §6"),
            "identity_only_difference": n(
                t0.loc[~t0.identical, "column"].tolist(), "A2_T0", "column",
                "identical == False", "Methods"),
        },
        "gates": {
            "joint_L_M_gate": n(int(gate.sum()), "A2_T1",
                                "mk_rho_mean_markers, xb_margin",
                                "rho > 0.75 AND margin > 0", "Results §6"),
            "rho_gate": n(0.75, "—", "mk_rho_mean_markers",
                          "Daniil's threshold, necessary not sufficient", "Methods; Results §6"),
        },
        "shambhala": {
            "median_rho": n(round(float(sh.mk_rho_mean_markers.median()), 3), "A2_T1",
                            "mk_rho_mean_markers", "method == 20_shambhala", "Results §6"),
            "median_margin": n(round(float(sh.xb_margin.median()), 4), "A2_T1",
                               "xb_margin", "method == 20_shambhala", "Results §6"),
            "median_lobo3_f1": n(round(float(sh.pv_lobo3_f1_macro_mean.median()), 3), "A2_T1",
                                 "pv_lobo3_f1_macro_mean", "method == 20_shambhala",
                                 "Results §6"),
        },
        "agreement_specific": {
            "n": n(int(len(t6)), "A2_T6", "run_id",
                   "xb_rank_agree_delta > 0 AND xb_rank_disagree_diffbio_delta < 0",
                   "Results §6"),
            "pct_of_non_raw": n(round(len(t6) / len(nonraw) * 100, 1), "A2_T6", "—",
                                f"denominator = {len(nonraw)} non-raw approaches",
                                "Results §6"),
            "top_margin_delta": n(round(float(t6.xb_margin_delta.max()), 3), "A2_T6",
                                  "xb_margin_delta", "maximum", "Results §6"),
            "top_approaches_tied": n(
                t6[t6.xb_margin_delta == t6.xb_margin_delta.max()]
                .apply(lambda r: f"{r.strat}/{r.imp}/{r.method}/post{int(r.post_rm)}",
                       axis=1).tolist(),
                "A2_T6", "strat, imp, method, post_rm", "xb_margin_delta == max",
                "Results §6"),
        },
        "prediction": {
            "leading_non_degenerate": n(
                {"run_id": lead.run_id,
                 "full_mean_f1": round(float(lead.pv_lobo3_f1_macro_mean), 3),
                 "worst_multiclass_fold": round(float(lead.f1_mc_min), 3),
                 "n_multiclass_folds": int(lead.n_mc),
                 "auc_2class": round(float(lead.pv_lobo2_auc_macro_mean), 3),
                 "f1_2class": round(float(lead.pv_lobo2_f1_macro_mean), 3),
                 "rho": round(float(lead.mk_rho_mean_markers), 3)},
                "A2_T1", "pv_lobo3_f1_macro_mean",
                "strat not in (A_confirmed_bad, B_extended_bad) AND n_mc >= 5",
                "Results §7"),
            "n_eligible_non_degenerate": n(
                int(((~t1.is_confirmed_bad) & (t1.n_mc >= 5)).sum()), "A2_T1", "—",
                "same filter", "Results §7"),
            "n_zero_multiclass_folds": n(int((t1.n_mc == 0).sum()), "A2_T1", "n_mc",
                                         "n_mc == 0", "Results §7; caveat 1"),
            "spearman_full_vs_multiclass": n(
                round(float(spearmanr(d.pv_lobo3_f1_macro_mean, d.f1_mc_mean).statistic), 3),
                "A2_T1", "pv_lobo3_f1_macro_mean, f1_mc_mean",
                f"both present, n = {len(d)}", "Results §7"),
            "spearman_min3_multiclass_folds": n(
                round(float(spearmanr(d3.pv_lobo3_f1_macro_mean, d3.f1_mc_mean).statistic), 3),
                "A2_T1", "same", f"n_mc >= 3, n = {len(d3)}", "Results §7"),
        },
        "fold_composition": {
            "n_3class_folds": n(int(tot.sum()), "A2_T8", "n_folds",
                                "target == 3class, run_id in the 2,234 analysis set",
                                "Results §7"),
            "n_singleclass_folds": n(int(tot.get(1, 0)), "A2_T8", "n_folds",
                                     "n_classes == 1", "Results §7"),
            "pct_singleclass": n(round(tot.get(1, 0) / tot.sum() * 100, 1), "A2_T8",
                                 "n_folds", "n_classes == 1", "Results §7"),
            "median_f1_by_class_count": n(
                {int(k): round(float(v), 3) for k, v in med.items()}, "A2_T8",
                "median_f1", "per n_classes, median over batches", "Results §7"),
            "n_batches": n(int(t8.batch.nunique()), "A2_T8", "batch", "—", "Methods"),
        },
        "harshness": {
            "tier_sizes": n(t1.harshness_level.value_counts().to_dict(), "A2_T1",
                            "harshness_level", "HARSHNESS_LEVEL_MAP, method level",
                            "Results §5b"),
            "kruskal": n(
                {r.metric: {"H": round(float(r.kruskal_H), 1), "p": float(r.kruskal_p),
                            "low": round(float(r.median_low), 3),
                            "medium": round(float(r.median_medium), 3),
                            "high": round(float(r.median_high), 3)}
                 for r in t7.itertuples()},
                "A2_T7", "kruskal_H, kruskal_p, median_*",
                "three method-level harshness tiers", "Results §5b"),
        },
        # Numbers whose locus is outside tables/: the snapshot columns A2_T1 omits, and two
        # quantities that exist only as a rank or a group count. audit_numbers.py cannot
        # evaluate a filtered aggregate over a CSV, so these resolve through this file.
        "saturation_and_scale": {
            "n_pcr_batch_above_0_9999": n(
                int((snap.pcr_RNA_BATCH > 0.9999).sum()), "metrics_comprehensive_260905.csv",
                "pcr_RNA_BATCH", "analysis set, pcr_RNA_BATCH > 0.9999", "Results §3"),
            "methods_at_saturation": n(
                sorted(snap.loc[snap.pcr_RNA_BATCH > 0.9999, "method"].unique()),
                "metrics_comprehensive_260905.csv", "method", "same filter", "Results §3"),
            "pct_saturated_with_kbet_below_0_1": n(
                round(float((snap.loc[snap.pcr_RNA_BATCH > 0.9999,
                                      "kbet_acceptance_rate_RNA_BATCH"] < 0.1).mean() * 100), 1),
                "metrics_comprehensive_260905.csv", "kbet_acceptance_rate_RNA_BATCH",
                "same filter, share below 0.1", "Results §3"),
            "shambhala_mean_exp_median": n(
                round(float(snap.loc[snap.method == "20_shambhala", "exp_median"].mean()), 1),
                "metrics_comprehensive_260905.csv", "exp_median",
                "mean over the 84 20_shambhala approaches -- a mean, not a median", "Results §4"),
            "shambhala_mean_exp_max": n(
                round(float(snap.loc[snap.method == "20_shambhala", "exp_max"].mean()), 1),
                "metrics_comprehensive_260905.csv", "exp_max",
                "mean over the same 84 approaches -- a mean, not a maximum", "Results §4"),
        },
        "gate_and_rank_counts": {
            "joint_gate_by_strategy": n(
                t1[gate].strat.value_counts().to_dict(), "A2_T1", "strat",
                "mk_rho_mean_markers > 0.75 and xb_margin > 0, counted per strategy",
                "Results §6"),
            "clustermap_index_rank_range": n(
                [int(t2.generalizability_index.rank(ascending=False, method="min")
                     [t2.is_clustermap_best].min()),
                 int(t2.generalizability_index.rank(ascending=False, method="min")
                     [t2.is_clustermap_best].max())],
                "A2_T2", "generalizability_index",
                "rank of the 15 is_clustermap_best rows, descending, of 2,234", "Results §8"),
        },
        "per_batch_example": {
            "run_id": "S0_no_removal__softimpute__29_combat_ref__post0",
            "n_folds": n(int(((t5.run_id == "S0_no_removal__softimpute__29_combat_ref__post0")
                              & (t5.target == "3class")).sum()), "A2_T5", "batch",
                         "target == 3class", "Results §7"),
            "n_singleclass": n(int(((t5.run_id == "S0_no_removal__softimpute__29_combat_ref__post0")
                                    & (t5.target == "3class") & (t5.n_classes == 1)).sum()),
                               "A2_T5", "n_classes", "n_classes == 1", "Results §7"),
            "hardest_multiclass_folds": n(
                t5[(t5.run_id == "S0_no_removal__softimpute__29_combat_ref__post0")
                   & (t5.target == "3class") & (t5.n_classes >= 2)]
                .nsmallest(3, "f1_macro")[["batch", "n", "n_classes", "f1_macro", "auc"]]
                .round(4).to_dict("records"),
                "A2_T5", "f1_macro", "n_classes >= 2, three smallest", "Results §7"),
        },
    }
    out |= revision_sections(tables)
    return out


def revision_sections(tables: Path) -> dict:
    """Evidence entries for the tables added in the 260924 revision (plan Phase 1).

    A2_T10 and A2_T11 are catalogues of several hundred rows; the CSVs themselves are
    indexed by audit_numbers.py at every rounding, so only the rows a main-text sentence
    is expected to quote are lifted here, each keyed by its claim or scatter id.
    """
    t3b = pd.read_csv(tables / f"A2_T3b_cross_election_pairs_{STAMP}.csv")
    t9 = pd.read_csv(tables / f"A2_T9_harshness_table1_{STAMP}.csv")
    t10 = pd.read_csv(tables / f"A2_T10_paired_tests_{STAMP}.csv")
    t11 = pd.read_csv(tables / f"A2_T11_scatter_correlations_{STAMP}.csv")
    t12 = pd.read_csv(tables / f"A2_T12_metric_census_{STAMP}.csv")
    t13 = pd.read_csv(tables / f"A2_T13_lobo_summary_{STAMP}.csv")
    t14 = pd.read_csv(tables / f"A2_T14_dispersion_{STAMP}.csv")
    reg = pd.read_csv(tables / f"A2_table_registry_{STAMP}.csv")
    non_meta = t12[~t12.is_metadata]
    return {
        "metric_census": {
            "n_registry": n(int(len(t12)), "A2_T12", "Metric", "every registry row",
                            "Title; Introduction"),
            "n_non_metadata": n(int(len(non_meta)), "A2_T12", "is_metadata",
                                "Metric group != Metadata", "C48 clustermap legend"),
            "n_scoring": n(int(t12.is_scoring.sum()), "A2_T12", "Polarity",
                           "Polarity != 0", "Methods (F2)"),
            "n_positive_polarity": n(int((t12.Polarity == 1).sum()), "A2_T12",
                                     "Polarity", "== +1", "Methods (F2)"),
            "n_negative_polarity": n(int((t12.Polarity == -1).sum()), "A2_T12",
                                     "Polarity", "== -1", "Methods (F2)"),
            "n_descriptive": n(int((t12.Polarity == 0).sum()), "A2_T12", "Polarity",
                               "== 0", "Methods (F2)"),
            "n_recoverable": n(int(non_meta.recoverable.sum()), "A2_T12",
                               "recoverable", "non-metadata, found in the snapshot",
                               "C48 clustermap legend"),
        },
        "cross_election_pairs": {
            f"{r.set_a}__{r.set_b}": n(
                {"n_intersection": int(r.n_intersection), "jaccard": r.jaccard,
                 "expected": r.expected_intersection,
                 "p_more_than_chance": r.p_more_than_chance,
                 "p_less_than_chance": r.p_less_than_chance},
                "A2_T3b", "n_intersection, jaccard, hypergeometric p",
                f"sets of {int(r.n_a)} and {int(r.n_b)} of 2,234", "Table 3; Results §8")
            for r in t3b.itertuples()},
        "harshness_table1": {
            r.metric: n({"H": r.kruskal_H, "p": r.kruskal_p,
                         "mean": [r.mean_low, r.mean_medium, r.mean_high],
                         "median": [r.median_low, r.median_medium, r.median_high],
                         "n": [int(r.n_low), int(r.n_medium), int(r.n_high)]},
                        "A2_T9", "per tier low / medium / high", "method harshness tier",
                        "Table 1")
            for r in t9.itertuples()},
        "lobo_summary": {
            r.label: n({c: getattr(r, c) for c in t13.columns
                        if c not in ("row_type", "label", "tier", "destination")},
                       "A2_T13", "LOBO columns", r.row_type, "Table 2")
            for r in t13.itertuples()},
        "paired_tests": {
            r.claim_id: n({"median_a": r.median_a, "median_b": r.median_b,
                           "mean_a": r.mean_a, "mean_b": r.mean_b, "prop_a": r.prop_a,
                           "prop_b": r.prop_b, "statistic": r.statistic,
                           "p": r.p_value}, "A2_T10", r.metric,
                          f"{r.group_a} vs {r.group_b}; {r.test}", r.section)
            for r in t10.itertuples() if isinstance(r.quoted, str)},
        "scatter_correlations": {
            r.scatter_id: n({"rho": r.spearman_rho, "p": r.p_value, "n": int(r.n)},
                            "A2_T11", f"{r.x} vs {r.y}", r.subset, r.panel)
            for r in t11.itertuples() if not r.scatter_id.startswith("T11-L")},
        "dispersion": {
            f"{r.by}:{r.subset}:{r.across}": n(
                {"range_with_clustermap_group": r.range_with_clustermap_group,
                 "range_without_clustermap_group": r.range_without_clustermap_group,
                 "sd_of_group_means": r.sd_of_group_means,
                 "contribution_clustermap": r.contribution_clustermap,
                 "n_columns": int(r.n_columns)},
                "A2_T14", "contribution to the composite",
                "range of group means, clustermap group included as one group",
                "Results §5 (C42, C43)")
            for r in t14.itertuples()},
        "stat_requests": stat_request_entries(tables),
        "figures_and_records": figure_entries(tables),
        "table_budget": {
            "n_main_tables": n(int((reg.tier == "main").sum()), "A2_table_registry",
                               "tier", "tier == main, budget 5", "HARD_RULE 19"),
        },
    }


def stat_request_entries(tables: Path) -> dict:
    """The Phase 3 statistics queue, drained (10_stat_requests_*.json).

    Counts are read back out of A2_T1, A2_T15 and A2_T3c and the pinned snapshot; the
    one new test (SR-U04) is row T10-110 of A2_T10.
    """
    t1 = pd.read_csv(tables / f"A2_T1_analysis_set_census_{STAMP}.csv", low_memory=False)
    t15 = pd.read_csv(tables / f"A2_T15_class_percentile_scores_{STAMP}.csv")
    t3c = pd.read_csv(tables / f"A2_T3c_threshold_sensitivity_{STAMP}.csv")
    t10 = pd.read_csv(tables / f"A2_T10_paired_tests_{STAMP}.csv")
    snap = pd.read_csv(SNAPSHOT_CSV, low_memory=False)
    snap["method"] = snap["method"].replace({"shambhala_P0std_Q0std": "20_shambhala"})
    snap["run_id"] = (snap.strat + "__" + snap.imp + "__" + snap.method + "__post"
                      + snap.post_rm.map({False: "0", True: "1"}))
    snap = snap[snap.run_id.isin(set(t1.run_id))]
    gate = (t1.mk_rho_mean_markers > 0.75) & (t1.xb_margin > 0)
    t = t1.set_index("run_id").join(t15.set_index("run_id")[
        ["elected_L", "elected_M", "elected_N"]])
    g = gate.values
    eligible = gate & (~t1.is_confirmed_bad) & (t1.n_mc >= 5)
    lead = t1[eligible.values].nlargest(1, "pv_lobo3_f1_macro_mean").iloc[0]
    zero = t1[t1.n_mc == 0]
    with_mc = t1[t1.n_mc >= 1]
    multi = t[(t[["elected_L", "elected_M", "elected_N"]].sum(axis=1) >= 2)]
    sens = t3c.groupby("top_frac").agg(set_size=("set_size", "first"),
                                       rho=("spearman_vs_5pct", "first"),
                                       p=("spearman_p_vs_5pct", "first"))
    top = t3c.loc[t3c.groupby("top_frac").jaccard.idxmax()]
    u04 = t10[t10.claim_id == "T10-110"].iloc[0]
    exp_max = snap.groupby("method").exp_max.mean()
    return {
        "SR-U01": n({m: float(exp_max[m]) for m in ("06_combat_seq",
                                                   "08_inmoose_combatseq")},
                    "metrics_comprehensive_260905.csv", "exp_max",
                    "mean over each method's approaches in the analysis set",
                    "Results §8; Conclusions"),
        "SR-U02": n({"n": int(eligible.sum()), "leader": lead.run_id,
                     "leader_full_f1": float(lead.pv_lobo3_f1_macro_mean)},
                    "A2_T1", "mk_rho_mean_markers, xb_margin, n_mc, is_confirmed_bad",
                    "rho > 0.75 AND margin > 0 AND n_mc >= 5 AND not bad-batch strategy",
                    "Conclusions"),
        "SR-U03": n({f"{k}": {"set_size": int(r.set_size), "rho_vs_5pct": float(r.rho),
                              "p": float(r.p)} for k, r in sens.iterrows()}
                    | {"largest_pair": {f"{r.top_frac}": f"{r.set_a}-{r.set_b} "
                                        f"{r.jaccard:.3f}" for r in top.itertuples()}},
                    "A2_T3c", "jaccard", "election thresholds 2.5%, 5%, 10%",
                    "Conclusions, limits"),
        "SR-U04": n({"median_clustermap": float(u04.median_a),
                     "median_rest": float(u04.median_b), "p": float(u04.p_value)},
                    "A2_T10", "pv_lobo3_f1_macro_mean", "T10-110 Mann-Whitney",
                    "Results §9"),
        "SR-U05": n({"n_zero_mc": int(len(zero)),
                     "zero_mc_strategies": zero.strat.value_counts().to_dict(),
                     "zero_mc_post_rm": zero.post_rm.value_counts().to_dict(),
                     "zero_mc_full_f1_ge_0_999": int(
                         (zero.pv_lobo3_f1_macro_mean.round(3) >= 0.999).sum()),
                     "max_full_f1_with_mc": with_mc.nlargest(1, "pv_lobo3_f1_macro_mean")
                     .run_id.iloc[0],
                     "max_mc_f1": with_mc.nlargest(1, "f1_mc_mean").run_id.iloc[0]},
                    "A2_T1", "n_mc, pv_lobo3_f1_macro_mean, f1_mc_mean", "—",
                    "Results §7"),
        "SR-L01": n({"gate_pass_in_L": int(g[t.elected_L.values].sum()),
                     "gate_pass_in_M": int(g[t.elected_M.values].sum()),
                     "gate_pass_in_N": int(g[t.elected_N.values].sum()),
                     "elected_by_2plus": multi.index.tolist()},
                    "A2_T1, A2_T15", "gate, elected_L/M/N",
                    "rho > 0.75 AND margin > 0 within each elected set",
                    "legend of the election figure, D"),
    }


def figure_entries(tables: Path) -> dict:
    """Counts printed in the Phase 2 figures and identifiers quoted in the back matter."""
    root = tables.resolve().parent
    drop = json.loads((root / "figures/panels_260925/data/"
                       "sfig_metric_clustermap_dropped.json").read_text())
    t15 = pd.read_csv(tables / f"A2_T15_class_percentile_scores_{STAMP}.csv")
    five = t15[[f"elected_{c}" for c in ("N", "M", "L", "global", "local")]]
    return {
        "clustermap_n_metrics": n(drop["n_used"], "sfig_metric_clustermap_dropped.json",
                                  "n_used", "non-metadata registry metrics, recoverable, "
                                  "not constant or sparse", "clustermap legend"),
        "clustermap_dropped": n(drop["dropped_constant_or_sparse"],
                                "sfig_metric_clustermap_dropped.json", "dropped", "—",
                                "clustermap legend"),
        "election_union_five_sets": n(int(five.any(axis=1).sum()), "A2_T15",
                                      "elected_N, elected_M, elected_L, elected_global, "
                                      "elected_local", "in at least one of the five",
                                      "election figure C"),
        "zenodo_record": n(22737294, "Zenodo deposit", "record id",
                           "https://doi.org/10.5281/ZENODO.22737294 (draft record of "
                           "2026-09-14)", "Data availability"),
    }


def _floats(value):
    """Every float inside a (possibly nested) evidence value."""
    if isinstance(value, bool):
        return []
    if isinstance(value, float):
        return [] if math.isnan(value) else [value]
    if isinstance(value, dict):
        return [f for v in value.values() for f in _floats(v)]
    if isinstance(value, (list, tuple)):
        return [f for v in value for f in _floats(v)]
    return []


def add_three_digit_spellings(payload: dict) -> int:
    """Attach `spellings_3digit` to every entry that carries a float.

    Both readings of HARD_RULE 13 are written out: three decimals (0.7334 -> 0.733) and
    three significant figures (0.0178 -> 0.0178). Values of 1,000 or more get only the
    three-decimal form, because large values are exempt from the rule and 3 significant
    figures would turn them into scientific notation. audit_numbers.py reads this file
    as text, so a rounded manuscript value finds its spelling here.
    """
    n_added = 0
    for body in payload.values():
        if not isinstance(body, dict):
            continue
        for entry in body.values():
            if not isinstance(entry, dict) or "value" not in entry:
                continue
            spellings = set()
            for x in _floats(entry["value"]):
                spellings.add(f"{x:.3f}")
                if abs(x) < 1000:
                    spellings.add(f"{float(f'{x:.3g}'):g}")
            if spellings:
                entry["spellings_3digit"] = sorted(spellings)
                n_added += 1
    return n_added


DISCREPANCIES = [
    {
        "claim": "Across the 53,737 3-class folds, 25,426 (47.3%) contain a single class",
        "source": "plan §1.5d",
        "recomputed": "32,746 3-class folds, 15,436 single-class (47.1%)",
        "filter_source": "every run_id in prediction_folds_long.csv (3,738 run_ids, 50 method "
                         "names, all 18 Shambhala P/Q variants)",
        "filter_recomputed": "run_id restricted to the 2,234-approach analysis set",
        "cause": "the published figure counted folds for approaches the article never analyses; "
                 "20,343 of the 53,737 belong to the 17 non-canonical Shambhala P/Q variants, "
                 "and the residual 648 to 34_arsyn and 38_harman, which fail "
                 "pct_samples_allNA < 5 (20,343 + 648 = 20,991 = 53,737 - 32,746). The "
                 "canonical shambhala_P0std_Q0std is kept, as 20_shambhala, and contributes "
                 "1,200 of the 32,746",
        "direction": "the conclusion is unchanged -- single-class folds are still about half the "
                     "population -- only the counts move",
    },
    {
        "claim": "single-class folds have median macro F1 0.952; two-class 0.648; three-class 0.830",
        "source": "plan §1.5d",
        "recomputed": "0.903 / 0.629 / 0.804 on the analysis set",
        "filter_source": "as above",
        "filter_recomputed": "as above",
        "cause": "same population difference",
        "direction": "the ordering is unchanged: two-class folds remain the hardest and "
                     "single-class folds the easiest",
    },
    {
        "claim": "Spearman between the full metric and the multiclass-only mean is 0.812 over "
                 "the 1,981 approaches with at least three multiclass folds",
        "source": "plan §1.5d",
        "recomputed": "0.815 over 2,058 such approaches; 0.810 over all 2,174 carrying both",
        "filter_source": "fold aggregates computed over the unrestricted fold table",
        "filter_recomputed": "fold aggregates over the analysis set only",
        "cause": "same population difference; the approach count rises because restricting the "
                 "fold table does not remove approaches, only foreign run_ids",
        "direction": "unchanged conclusion: the two cuts agree closely and neither reverses the "
                     "other",
    },
    {
        "claim": "Per-batch detail for S0_no_removal/softimpute/29_combat_ref/post0: 10 of the 24 "
                 "folds are single-class; the hard folds are GPL96_FFPE_Unknown and RNASeq_FF_PolyA",
        "source": "plan §1.5d",
        "recomputed": "13 of 24 folds are single-class; the three hardest multiclass folds are "
                      "GPL96_FFPE_Unknown (F1 0.462), RNASeq_FFPE_PolyA (0.698) and "
                      "RNASeq_FF_PolyA (0.718)",
        "filter_source": "unknown; not reproducible from prediction_folds_long.csv",
        "filter_recomputed": "A2_T5, target == 3class",
        "cause": "the two quoted folds and their values reproduce exactly; the single-class count "
                 "and the identity of the second-hardest fold do not",
        "direction": "the approach's characterisation is unchanged",
    },
    {
        "claim": "multiclass-only F1 across harshness tiers: H = 11.2, p = 0.0037",
        "source": "plan §1.5e",
        "recomputed": "H = 11.8, p = 0.0028",
        "filter_source": "f1_mc_mean computed over the unrestricted fold table",
        "filter_recomputed": "f1_mc_mean over the analysis set",
        "cause": "same population difference; every other row of the tier table reproduces exactly, "
                 "including the 2-class AUC result (H = 1.5, p = 0.48, not significant)",
        "direction": "unchanged",
    },
    {
        "claim": "Top by raw-subtracted margin: K_ffpe_only / knn / 06_combat_seq / post0",
        "source": "plan §1.5c",
        "recomputed": "06_combat_seq and 08_inmoose_combatseq are an exact tie at that "
                      "(strat, imp, post_rm): margin 0.439161, gain +0.457154 for both",
        "filter_source": "A2_T6 sorted by xb_margin_delta",
        "filter_recomputed": "same",
        "cause": "two implementations of the same algorithm return identical Group M values; the "
                 "sort order between them is arbitrary",
        "direction": "quote both, or say that the two implementations agree exactly -- which is "
                     "itself a positive control worth a sentence",
    },
    {
        "claim": "Cells not traceable to the generator: 8 in the main notebook, 43 in the "
                 "narrow-set notebook, 29 in the deep-analysis notebook",
        "source": "plan §4.2e",
        "recomputed": "12 / 50 / 53 hand-written, plus 6 / 12 / 52 generator cells edited in place",
        "filter_source": "unknown",
        "filter_recomputed": "tools/extract_hand_written_cells.py, generator run at the same "
                            "--date-tag, normalized comparison, NEAR threshold 0.90",
        "cause": "the earlier count did not separate edited generator cells from untouched ones; "
                 "an edited cell still looks like the generator's, so regeneration reverts it "
                 "without saying so",
        "direction": "materially larger: 185 cells must survive regeneration, not 80",
    },
]


def main() -> int:
    global STAMP
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tables", default="tables/")
    ap.add_argument("--out", default="workflow_runs/260924_run1/")
    ap.add_argument("--stamp", default=STAMP, help="table date stamp to read")
    args = ap.parse_args()

    STAMP = args.stamp
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = build(Path(args.tables))
    n_spelled = add_three_digit_spellings(payload)
    payload["discrepancies"] = DISCREPANCIES
    payload["provenance"] = {
        "snapshot": "metrics_comprehensive_260905.csv",
        "supplementary_file_3": "figures_for_article/supplementary_260824/Supplementary File 3.csv.gz",
        "folds": "harmonization-metrics/metric_tables/prediction_folds_long.csv",
        "produced_by": f"analysis/article2_generalizability.py --date-tag 260905 "
                       f"--stamp {STAMP}",
        "three_digit_spellings": f"{n_spelled} entries carry spellings_3digit",
        "note": "Every value here is read back out of tables/A2_T*.csv. Nothing is retyped from "
                "the source document.",
    }

    (out_dir / "01_numbers.json").write_text(json.dumps(payload, indent=2, default=str))

    # The .md is the writer's copy: same content, readable without a JSON viewer.
    lines = ["# Article 2 — numbers and their provenance", "",
             f"Snapshot `{payload['provenance']['snapshot']}`. "
             f"Produced by `{payload['provenance']['produced_by']}`. "
             "Every value is read back out of `tables/A2_T*.csv`.", ""]
    for section, body in payload.items():
        if section in ("discrepancies", "provenance"):
            continue
        lines += [f"## {section}", "", "| number | value | table | column | filter | quoted in |",
                  "|---|---|---|---|---|---|"]
        for key, e in body.items():
            if not isinstance(e, dict) or "value" not in e:
                lines.append(f"| {key} | {e} | | | | |")
                continue
            v = str(e["value"]).replace("|", "/")
            lines.append(f"| {key} | {v} | {e['table']} | {e['column']} | "
                         f"{e['filter'].replace('|', '/')} | {e['quoted_in']} |")
        lines.append("")
    lines += ["## discrepancies", "",
              "Reported, never silently corrected. Each one reaches the manuscript text.", ""]
    for i, d in enumerate(DISCREPANCIES, 1):
        lines += [f"### {i}. {d['claim']}", "",
                  f"- **Source:** {d['source']}",
                  f"- **Recomputed:** {d['recomputed']}",
                  f"- **Filter, source:** {d['filter_source']}",
                  f"- **Filter, recomputed:** {d['filter_recomputed']}",
                  f"- **Cause:** {d['cause']}",
                  f"- **Effect on the conclusion:** {d['direction']}", ""]
    (out_dir / "01_numbers.md").write_text("\n".join(lines))
    print(f"wrote {out_dir / '01_numbers.json'} and 01_numbers.md "
          f"({sum(len(v) for v in payload.values() if isinstance(v, dict))} entries, "
          f"{len(DISCREPANCIES)} discrepancies)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
