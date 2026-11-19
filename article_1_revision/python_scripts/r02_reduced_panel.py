"""
r02_reduced_panel.py — reduced, non-redundant metric panel (plan WP2; decision D4).

Reanalysis only. Answers Reviewer 1, comment 3 and Reviewer 2, comment 2 (i).

Rule (plan WP2, brainstorm round 1 §5)
--------------------------------------
1. Universe: the 87 scoring metrics of `Metric_polarity` (polarity ≠ 0); keep those on
   RNA_BATCH, Diagnosis_cell_type_unified or with no annotation column → 33 metrics.
   Gate G1 (Daniil, 2026-11-03): the tSNE centroid dispersion metrics are removed from
   the universe (EXCLUDED_METRIC_PREFIXES): tSNE preserves only local neighbourhoods,
   not distances, so a distance between tSNE batch centroids has no meaning → 32.
2. Polarity-adjust; Spearman correlation over the 2,234 approaches of the analysis set
   (pairwise complete, ≥ 30 pairs); distance 1 − |ρ|; complete linkage; cut at 0.2
   (|ρ| ≥ 0.8 inside a cluster).
3. One representative per cluster, in this order: RNA_BATCH / Diagnosis column →
   lowest NA fraction → highest mean |ρ| to its cluster mates → simplest / most cited
   (SIMPLICITY_ORDER below). A tie that only the last step resolves is written to
   tiebreaks.tsv with its reason.
4. Coverage: ≥ 1 metric per metric group present in the universe (A B C D E G H I K);
   inside a group that defines both, ≥ 1 RNA_BATCH and ≥ 1 Diagnosis metric. Gate G1
   (Daniil, 2026-11-03): a group counts as covered when one of its metrics is in the
   panel OR is a cluster mate (|ρ| ≥ 0.8 to the panel representative, complete
   linkage) of a panel metric. No metric is added back; coverage_additions.tsv lists
   each group covered only through a cluster mate (group H: distance ratios, mates of
   the two PC regressions, |ρ| 0.94 / 0.83).
5. Axis of every panel metric (revision_lib.metric_axis / four_score_bar).

Outputs (output/wp2/)
---------------------
reduced_panel.tsv, cluster_membership.tsv, tiebreaks.tsv, coverage_additions.tsv,
reduced_panel_matrix.parquet (2,234 approaches × panel, polarity-adjusted, min-max
scaled), metric_abs_spearman.parquet (33 × 33), panel_variants.tsv (cut 0.1 / 0.2 / 0.3
on the 33, and cut 0.2 on all 87: the WP5 robustness inputs), panel_summary.json.

Usage
-----
python r02_reduced_panel.py            # build everything
python r02_reduced_panel.py --check    # assert coverage and the complete-approach count
"""

from __future__ import annotations

import argparse
import json

import pandas as pd

import revision_lib as rl

OUT_DIR = rl.OUTPUT_DIR / "wp2"
MAIN_CUT = 0.2
VARIANT_CUTS = (0.1, 0.2, 0.3)
# Gate G1 (2026-11-03): metrics removed from every panel universe, with the reason.
EXCLUDED_METRIC_PREFIXES: dict[str, str] = {
    "tsne_centroid_disp": "tSNE does not preserve distances; a distance between tSNE "
    "batch centroids is not meaningful (Daniil, gate G1)",
}
# Step 3, last tie-break: simpler / more widely cited statistics first (scIB, kBET,
# LISI and silhouette papers before the project-specific statistics).
SIMPLICITY_ORDER: tuple[str, ...] = (
    "ilisi_norm",
    "kbet_acceptance_rate",
    "asw_batch_norm",
    "asw_bio_norm",
    "PCReg",
    "graph_connectivity",
    "clisi_mean",
    "dist_ratio",
    "pct_",
    "ks_mean_D",
    "ks_frac_sig",
    "umap_entropy_norm",
    "tsne_entropy_norm",
    "umap_centroid_disp",
    "tsne_centroid_disp",
    "cms_fraction_mixed",
    "dsc",
    "per_gene_batch_mean_cv",
    "wm_",
    "fraction_cohorts",
    "ks_cohort",
)


def simplicity_rank(metric: str) -> int:
    """Position of the metric family in SIMPLICITY_ORDER (unknown families last)."""
    for rank, prefix in enumerate(SIMPLICITY_ORDER):
        if metric.startswith(prefix):
            return rank
    return len(SIMPLICITY_ORDER)


def metric_universe(
    polarity_table: pd.DataFrame, restrict_columns: bool
) -> pd.DataFrame:
    """Scoring metrics (polarity ≠ 0), optionally only RNA_BATCH / Diagnosis / none."""
    scoring = polarity_table[polarity_table["Polarity"] != 0].copy()
    scoring = scoring[
        [
            not any(m.startswith(prefix) for prefix in EXCLUDED_METRIC_PREFIXES)
            for m in scoring.index
        ]
    ]
    scoring["column"] = [rl.metric_annotation_column(m) for m in scoring.index]
    if restrict_columns:
        scoring = scoring[scoring["column"].isin(rl.PANEL_COLUMNS)]
    return scoring


def choose_representative(
    members: list[str],
    universe: pd.DataFrame,
    na_fraction: pd.Series,
    abs_rho: pd.DataFrame,
) -> tuple[str, dict | None]:
    """Representative of one cluster (rule step 3) and a tie-break record if needed."""
    if len(members) == 1:
        return members[0], None
    mean_rho = {
        m: abs_rho.loc[m, [x for x in members if x != m]].mean() for m in members
    }
    keys = pd.DataFrame(
        {
            "metric": members,
            "not_panel_column": [universe.loc[m, "column"] == "none" for m in members],
            "na_fraction": [round(float(na_fraction[m]), 4) for m in members],
            "neg_mean_rho": [-round(float(mean_rho[m]), 3) for m in members],
            "simplicity": [simplicity_rank(m) for m in members],
        }
    ).sort_values(["not_panel_column", "na_fraction", "neg_mean_rho", "simplicity"])
    best, runner_up = keys.iloc[0], keys.iloc[1]
    decisive = ["not_panel_column", "na_fraction", "neg_mean_rho"]
    if all(best[k] == runner_up[k] for k in decisive):
        return str(best["metric"]), {
            "cluster_members": ";".join(members),
            "chosen": best["metric"],
            "runner_up": runner_up["metric"],
            "reason": "tie on column type, NA fraction and mean |ρ| (3 d.p.); "
            "chosen as the simpler / more widely cited statistic",
        }
    return str(best["metric"]), None


def build_panel(universe: pd.DataFrame, scaled_input: pd.DataFrame, cut: float) -> dict:
    """Apply rule steps 2–5 at one cut; returns the panel tables."""
    metrics = list(universe.index)
    adjusted = rl.polarity_adjust(scaled_input, universe["Polarity"])
    abs_rho = rl.abs_spearman(adjusted)
    clusters = rl.complete_linkage_clusters(abs_rho, cut)
    na_fraction = scaled_input[metrics].isna().mean()

    representatives, tiebreaks = [], []
    for cluster_id, members in clusters.groupby(clusters).groups.items():
        chosen, record = choose_representative(
            list(members), universe, na_fraction, abs_rho
        )
        representatives.append((cluster_id, chosen, list(members)))
        if record:
            tiebreaks.append({"cluster_id": cluster_id, **record})

    panel = {chosen for _, chosen, _ in representatives}
    additions = []
    for group, in_group in universe.groupby("Metric group"):
        needed_columns = [
            c
            for c in ("RNA_BATCH", "Diagnosis_cell_type_unified")
            if (in_group["column"] == c).any()
        ]
        needs = needed_columns or ["any"]
        for column in needs:
            candidates = (
                in_group.index
                if column == "any"
                else in_group.index[in_group["column"] == column]
            )
            if panel.intersection(candidates):
                continue
            # covered through a cluster mate of a panel metric (gate G1)
            mates = [
                (m, p)
                for m in candidates
                for p in panel
                if clusters[m] == clusters[p]
            ]
            if mates:
                metric, representative = mates[0]
                additions.append(
                    {
                        "metric_group": group,
                        "column": column,
                        "covered_by_mate": metric,
                        "panel_representative": representative,
                        "abs_rho": round(float(abs_rho.loc[metric, representative]), 3),
                        "reason": "covered through a cluster mate (gate G1); "
                        "not added to the panel",
                    }
                )
                continue
            raise AssertionError(f"group {group} / {column} has no panel metric")

    membership = pd.DataFrame(
        {
            "metric": clusters.index,
            "cluster_id": clusters.values,
            "metric_group": universe.loc[clusters.index, "Metric group"].values,
            "column": universe.loc[clusters.index, "column"].values,
            "na_fraction": na_fraction[clusters.index].values,
        }
    )
    membership["in_reduced_panel"] = membership["metric"].isin(panel)
    rows = []
    for metric in sorted(panel, key=lambda m: (universe.loc[m, "Metric group"], m)):
        cluster_id = int(clusters[metric])
        members = list(clusters.index[clusters == cluster_id])
        scope, role = rl.metric_axis(
            metric,
            universe.loc[metric, "Metric group"],
            universe.loc[metric, "Metric type"],
        )
        rows.append(
            {
                "metric": metric,
                "metric_group": universe.loc[metric, "Metric group"],
                "column": universe.loc[metric, "column"],
                "polarity": int(universe.loc[metric, "Polarity"]),
                "axis_scope": scope,
                "axis_role": role,
                "four_score_bar": rl.four_score_bar(scope, role) or "",
                "cluster_id": cluster_id,
                "representative_of": ";".join(m for m in members if m != metric),
                "n_members": len(members),
                "na_fraction": float(na_fraction[metric]),
            }
        )
    return {
        "panel": pd.DataFrame(rows),
        "membership": membership,
        "tiebreaks": pd.DataFrame(tiebreaks),
        "additions": pd.DataFrame(additions),
        "abs_rho": abs_rho,
        "n_clusters": int(clusters.nunique()),
    }


def check(
    panel: pd.DataFrame,
    universe: pd.DataFrame,
    table: pd.DataFrame,
    membership: pd.DataFrame,
) -> dict:
    """Coverage of the metric groups (directly or via a cluster mate) and counts."""
    cluster_groups = membership.groupby("metric_group")["cluster_id"].agg(set).to_dict()
    groups_universe = sorted(universe["Metric group"].unique())
    groups_panel = sorted(panel["metric_group"].unique())
    clusters_panel = set(panel["cluster_id"])
    complete_33 = int(table[list(universe.index)].notna().all(axis=1).sum())
    complete_panel = int(table[panel["metric"]].notna().all(axis=1).sum())
    all_scoring = metric_universe(rl.load_metric_polarity(), restrict_columns=False)
    complete_87 = int(table[list(all_scoring.index)].notna().all(axis=1).sum())
    return {
        "n_universe": len(universe),
        "n_panel": len(panel),
        "groups_universe": groups_universe,
        "groups_panel": groups_panel,
        "groups_covered_through_mates": sorted(set(groups_universe) - set(groups_panel)),
        "all_groups_covered": all(
            g in groups_panel or (cluster_groups.get(g, set()) & clusters_panel)
            for g in groups_universe
        ),
        "n_approaches": len(table),
        "complete_on_33": complete_33,
        "complete_on_panel": complete_panel,
        "complete_on_87": complete_87,
    }


def main() -> None:
    """Build the reduced panel, its variants and the scaled panel matrix."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument(
        "--check",
        action="store_true",
        help="only print / assert coverage and completeness",
    )
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    polarity_table = rl.load_metric_polarity()
    table = rl.load_supp_file_3(analysis_set_only=True).reset_index(drop=True)
    universe = metric_universe(polarity_table, restrict_columns=True)
    result = build_panel(universe, table, MAIN_CUT)
    summary = check(result["panel"], universe, table, result["membership"])
    summary["n_clusters"] = result["n_clusters"]
    print(json.dumps(summary, indent=1))
    assert summary["all_groups_covered"], "a metric group is missing from the panel"
    if args.check:
        return

    result["panel"].to_csv(OUT_DIR / "reduced_panel.tsv", sep="\t", index=False)
    result["membership"].to_csv(
        OUT_DIR / "cluster_membership.tsv", sep="\t", index=False
    )
    result["tiebreaks"].to_csv(OUT_DIR / "tiebreaks.tsv", sep="\t", index=False)
    result["additions"].to_csv(
        OUT_DIR / "coverage_additions.tsv", sep="\t", index=False
    )
    result["abs_rho"].to_parquet(OUT_DIR / "metric_abs_spearman.parquet")

    panel_metrics = list(result["panel"]["metric"])
    adjusted = rl.polarity_adjust(table, universe.loc[panel_metrics, "Polarity"])
    matrix = rl.minmax_scale(adjusted)
    matrix.index = pd.MultiIndex.from_frame(table[rl.APPROACH_KEYS])
    matrix.to_parquet(OUT_DIR / "reduced_panel_matrix.parquet")

    variants = []
    all_scoring = metric_universe(polarity_table, restrict_columns=False)
    for name, variant_universe, cut in [
        (f"33_cut{c}", universe, c) for c in VARIANT_CUTS
    ] + [("87_cut0.2", all_scoring, 0.2)]:
        variant = build_panel(variant_universe, table, cut)
        for _, row in variant["panel"].iterrows():
            variants.append({"variant": name, **row.to_dict()})
        print(
            f"variant {name}: {len(variant['panel'])} metrics, "
            f"{variant['n_clusters']} clusters"
        )
    pd.DataFrame(variants).to_csv(OUT_DIR / "panel_variants.tsv", sep="\t", index=False)
    with open(OUT_DIR / "panel_summary.json", "w") as handle:
        json.dump(summary, handle, indent=1)
    print(
        result["panel"][
            [
                "metric",
                "metric_group",
                "axis_scope",
                "axis_role",
                "four_score_bar",
                "n_members",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
