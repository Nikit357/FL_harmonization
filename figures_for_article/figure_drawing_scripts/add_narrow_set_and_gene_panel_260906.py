#!/usr/bin/env python
"""Add the Group L narrow-panel metrics and the marker gene panel sheet to
`supplementary_260824/Supplementary File 2.xlsx`.

Follow-on to `add_LMN_metrics_260824.py`. Three edits, all idempotent:

* **`Metric_polarity`** — appends the 15 `mk_*_narrow_set` scalar columns that
  `compute_group_l()` in `harmonization-metrics-calculation/compute_batch_metrics.py`
  emits since the 2026-09-04 narrow-panel change (plan:
  `harmonization-metrics-calculation/implementation_plans/
  narrow_marker_panel_metrics_plan_260904.md`), with polarity 0 like every other
  blind-check metric, group `L`, and Explanation / Calculation text at the same level of
  detail as the existing `mk_*` rows. Four are coverage counters ('Other'); eleven are
  rho aggregates ('Distributional similarity'), of which two
  (`mk_rho_mean_PGK1_only_narrow_set`, `mk_rho_marker_minus_PGK1_only_narrow_set`) exist
  only in the narrow family.
* **`Table_S2_metrics`** — appends 2 descriptive rows: the narrow-panel variant of the
  Group L aggregates, and the coverage-matched single-gene (PGK1) housekeeping control.
* **`Table_S3_gene_panel`** — new sheet, the marker gene panel itself: one row per
  (gene, signature) from `harmonization-metrics-calculation/marker_gene_annotation.csv`
  (834 rows, 633 genes, 63 signatures, 15 housekeeping controls, 56 flagged
  `in_narrow_set`), joined on gene to two further blocks — the coverage audit from
  `harmonization-metrics-calculation/gene_panel_analysis/build_marker_gene_coverage.py`
  (`marker_gene_coverage_by_attempt_260828.csv`), and the complete gene-level statistics
  of `harmonization-metrics/marker_gene_deep_analysis.ipynb` (its Table T9), rebuilt by
  `build_gene_level_stats()` so the sheet does not depend on the notebook having been
  run. 66 columns in total: provenance, coverage in three scopes, the distribution of
  each gene's Spearman rho across the 2,395 attempts that resolve it, the three gate
  outcomes (coverage / expression QC / saturation), the expression QC block
  (`zero_frac`, `frac_lt_1`, `detection_frac`, mean, SD, CV, between- and within-cohort
  variance, ICC, geNorm M) in both flavours the notebook uses — the 42 `01_raw`
  references, and every in-scope attempt — and each gene's PC1 loading inside its own
  signature.

**Provenance correction.** `build_marker_gene_annotation.py`'s comment states that the
narrow set's first gate is presence in all 42 `01_raw__post0` matrices (193 genes). It is
not: `marker_gene_deep_analysis.ipynb` cell 30 gates on `frac_ref_strategy == 1`, full
coverage of the 180 `C_rnaseq_only` attempts (61 genes). The 193-gene gate would leave
171 genes after the `frac_lt_1 < 0.20` filter, not 56. `build_gene_panel_frame()` asserts
the correct derivation reproduces the committed flag exactly, and
`retext_narrow_definition()` repairs a workbook written by the first version of this
script, which had copied the wrong criteria into the metric descriptions.

**Inputs from S3.** `build_gene_level_stats()` needs three aggregated tables that are not
in the repo (`metrics_comprehensive.csv`, `marker_gene_correlations_long.csv`,
`gene_qc_long.csv.gz`, ~240 MB). They are cached in `/tmp/fl_gene_panel_cache/`, and the
633-row result is written to
`harmonization-metrics/metric_tables/gene_level_stats_260905.csv`; delete that file to
force a rebuild.

Usage:
    source ~/venvs/collagen_3_11/bin/activate
    python figure_drawing_scripts/add_narrow_set_and_gene_panel_260906.py
"""

import copy
import os
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent.parent          # figures_for_article/
REPO = HERE.parent                                     # Follicular_lymphoma_disser/
PATH = HERE / "supplementary_260824" / "Supplementary File 2.xlsx"
ANN_CSV = REPO / "harmonization-metrics-calculation" / "marker_gene_annotation.csv"
COV_CSV = (REPO / "harmonization-metrics" / "metric_tables"
           / "marker_gene_coverage_by_attempt_260828.csv")

N_NARROW = 56           # genes flagged in_narrow_set
N_HK = 15               # housekeeping control genes
N_RAW_PAIRS = 42        # 14 strategies x 3 imputations, 01_raw__post0
N_SCOPE = 2407          # Article 1 analysis scope (Shambhala cross-product excluded)
REF_STRATEGY = "C_rnaseq_only"
N_REF_ATTEMPTS = 180    # in-scope attempts on the reference strategy
N_REF_COVERED = 61      # genes resolved in every one of them - narrow-set gate 1
SATURATION_MEDIAN_MAX = 0.99
ZERO_FRAC_MAX, LOW_FRAC_MAX, MIN_DETECTION_FRAC = 0.20, 0.50, 0.80

# ── Shared boilerplate for the Calculation column ─────────────────────────────

NARROW_DEF = (
    f"The narrow panel is the QC-filtered {N_NARROW}-gene subset of the marker table "
    f"(the in_narrow_set flag in marker_gene_annotation.csv, listed with every "
    f"statistic behind it in the Table_S3_gene_panel sheet), selected in "
    f"marker_gene_deep_analysis.ipynb by two gates evaluated over the {N_SCOPE:,} "
    f"in-scope attempts: (1) the gene resolves in every one of the {N_REF_ATTEMPTS} "
    f"{REF_STRATEGY} attempts, which {N_REF_COVERED} of the 633 panel genes do; (2) its "
    f"mean frac_lt_1 across attempts is below 0.20, i.e. fewer than 20% of samples sit "
    f"in the log2 noise band. {N_NARROW} genes clear both, exactly one of them (PGK1) a "
    f"housekeeping control. All {N_NARROW} also resolve in all {N_RAW_PAIRS} "
    f"01_raw__post0 reference matrices, but that wider coverage gate (193 genes) is not "
    f"the one that was applied."
)

SHARED_CALC = (
    "Computed in the same correlation pass as the unsuffixed Group L metric of the same "
    "name: compute_group_l() resolves the full marker panel, the narrow panel and the "
    "housekeeping panel independently against the genes shared by this job's harmonized "
    "matrix and the matched unharmonized 01_raw reference, unions the three into one "
    "gene list, and computes the per-gene, cross-cohort-averaged Spearman rho vector "
    "(rho_by_gene) once. The full-panel and narrow-panel families are two reductions of "
    "that one vector by _mk_rho_aggregates(), the narrow one with suffix '_narrow_set', "
    "so any difference between a metric and its _narrow_set counterpart is purely the "
    "gene subset, never a different computation. Implemented in compute_group_l()."
)

SATURATION = (
    "The saturation caveat of the full panel still applies: any harmonizer applying a "
    "per-batch monotone transform of each gene leaves within-cohort ranks unchanged and "
    "scores near 1 here by construction, so a high value is a 'nothing broke' guard "
    "rail rather than evidence of quality."
)

# ── The 15 new Metric_polarity rows ───────────────────────────────────────────
# (metric, metric type, explanation, calculation). Order follows the emission order in
# compute_group_l(): the four coverage counters, the nine shared aggregates, then the
# two narrow-only PGK1 aggregates.

NEW_METRICS: list[tuple[str, str, str, str]] = [
    (
        "mk_n_panel_genes_used_narrow_set",
        "Other",
        f"Group L bookkeeping (narrow panel): the number of the {N_NARROW} QC-filtered "
        f"narrow-panel genes actually found (directly or via an alias) in both this "
        f"job's harmonized matrix and the 01_raw reference, and therefore entering the "
        f"_narrow_set aggregates. {NARROW_DEF}",
        "narrow_genes, narrow_missing = marker_panels.resolve_panel(shared_genes, "
        "marker_panels.narrow_set_genes()); mk_n_panel_genes_used_narrow_set = "
        "len(narrow_genes). Resolved independently of any --panel-groups signature "
        "filter, so the narrow family never depends on which signatures were requested "
        "for the full-panel metrics. Implemented in compute_group_l().",
    ),
    (
        "mk_n_genes_null_narrow_set",
        "Other",
        f"Group L bookkeeping (narrow panel): the number of the {N_NARROW} narrow-panel "
        f"genes that could NOT be matched (directly or via alias) in the gene set "
        f"shared by this job's matrix and its reference, and were therefore excluded. "
        f"The narrow panel was selected to be present in every 01_raw reference, so a "
        f"non-zero value here means the harmonization method itself dropped the gene.",
        "mk_n_genes_null_narrow_set = len(narrow_missing) from the same "
        "resolve_panel(shared_genes, narrow_set_genes()) call as "
        "mk_n_panel_genes_used_narrow_set. Implemented in compute_group_l().",
    ),
    (
        "mk_panel_coverage_frac_narrow_set",
        "Other",
        f"Group L bookkeeping (narrow panel): the fraction of the {N_NARROW}-gene "
        f"narrow panel that was usable for this job.",
        f"mk_panel_coverage_frac_narrow_set = mk_n_panel_genes_used_narrow_set / "
        f"len(narrow_full), where narrow_full = marker_panels.narrow_set_genes() "
        f"({N_NARROW} genes). Reported as NaN, together with every other _narrow_set "
        f"key, if the annotation CSV predates the in_narrow_set column (the loader "
        f"degrades to an empty narrow panel rather than raising and taking all of "
        f"Group L down with it). Implemented in compute_group_l().",
    ),
    (
        "mk_n_hk_genes_used_narrow_set",
        "Other",
        f"Group L bookkeeping: the number of the {N_HK} housekeeping control genes "
        f"resolved in this job. Recorded with the narrow family because "
        f"mk_rho_mean_housekeeping_narrow_set uses the FULL housekeeping panel as its "
        f"control rather than only the housekeeping genes inside the narrow panel, so "
        f"the size and composition of that control set vary between attempts and must "
        f"be reported alongside the margin that uses it.",
        "hk_genes, _ = marker_panels.resolve_panel(shared_genes, "
        "marker_panels.housekeeping_genes()); mk_n_hk_genes_used_narrow_set = "
        "len(hk_genes). Resolved independently of any signature filter. Implemented in "
        "compute_group_l().",
    ),
    (
        "mk_rho_mean_all_genes_narrow_set",
        "Distributional similarity",
        f"Group L headline metric on the QC-filtered narrow panel (Distributional "
        f"similarity): mk_rho_mean_all_genes restricted to the {N_NARROW} narrow-panel "
        f"genes (PGK1 included). The full 633-gene panel mixes genes measured on every "
        f"platform with genes present in only part of the benchmark and genes sitting "
        f"in the log2 noise band, so the full-panel mean is partly a coverage "
        f"statistic; the narrow panel fixes the gene set across attempts and removes "
        f"low-expression genes, making the value comparable between approaches. "
        f"{SATURATION} {NARROW_DEF}",
        f"{SHARED_CALC} mk_rho_mean_all_genes_narrow_set = mean(rho_by_gene) over the "
        f"narrow-panel genes with a defined value.",
    ),
    (
        "mk_rho_median_all_genes_narrow_set",
        "Distributional similarity",
        "Group L (Distributional similarity): the median rather than the mean of the "
        "per-gene, cross-cohort-averaged Spearman correlations over the narrow panel "
        "— more robust to a small number of badly-preserved genes.",
        f"{SHARED_CALC} mk_rho_median_all_genes_narrow_set = median(rho_by_gene) over "
        f"the narrow-panel genes with a defined value.",
    ),
    (
        "mk_rho_p10_all_genes_narrow_set",
        "Distributional similarity",
        "Group L (Distributional similarity): the 10th percentile of the per-gene "
        "Spearman correlations over the narrow panel — the worst-preserved tail of the "
        "narrow panel rather than the typical gene.",
        f"{SHARED_CALC} mk_rho_p10_all_genes_narrow_set = 10th percentile (numpy) of "
        f"rho_by_gene over the narrow-panel genes with a defined value.",
    ),
    (
        "mk_rho_min_all_genes_narrow_set",
        "Distributional similarity",
        "Group L (Distributional similarity): the single worst-preserved narrow-panel "
        "gene's Spearman correlation — the narrow panel's worst case.",
        f"{SHARED_CALC} mk_rho_min_all_genes_narrow_set = min(rho_by_gene) over the "
        f"narrow-panel genes with a defined value.",
    ),
    (
        "mk_rho_frac_genes_above_0.9_narrow_set",
        "Distributional similarity",
        "Group L (Distributional similarity): the fraction of narrow-panel genes whose "
        "per-gene Spearman correlation exceeds 0.9 — a coarse 'how many genes are "
        "essentially unchanged in rank' summary on a gene set that is identical across "
        "attempts, so the fractions are directly comparable.",
        f"{SHARED_CALC} mk_rho_frac_genes_above_0.9_narrow_set = "
        f"mean(rho_by_gene > 0.9) over the narrow-panel genes with a defined value.",
    ),
    (
        "mk_rho_mean_markers_narrow_set",
        "Distributional similarity",
        f"Group L (Distributional similarity): mk_rho_mean_all_genes_narrow_set "
        f"restricted to the {N_NARROW - 1} biologically variable narrow-panel genes, "
        f"i.e. the narrow panel minus its one housekeeping member (PGK1). This is the "
        f"marker term of both narrow-panel margins.",
        f"{SHARED_CALC} mk_rho_mean_markers_narrow_set = mean(rho_by_gene) over genes "
        f"in narrow_mask & ~hk_mask with a defined value ({N_NARROW - 1} genes with "
        f"the default panel).",
    ),
    (
        "mk_rho_mean_housekeeping_narrow_set",
        "Distributional similarity",
        f"Group L (Distributional similarity): the housekeeping control term of the "
        f"primary narrow-panel margin. Deliberately NOT restricted to the narrow panel "
        f"— it is the mean per-gene rho over the full {N_HK}-gene housekeeping panel, "
        f"because only PGK1 of the {N_HK} clears the coverage bar the narrow markers "
        f"had to clear. It is therefore a larger and less noisy control, but one whose "
        f"composition varies between attempts with gene coverage; "
        f"mk_n_hk_genes_used_narrow_set records how many genes it actually used, and "
        f"mk_rho_mean_PGK1_only_narrow_set is the coverage-matched alternative.",
        f"{SHARED_CALC} mk_rho_mean_housekeeping_narrow_set = mean(rho_by_gene) over "
        f"genes in hk_mask — the full housekeeping panel, NOT intersected with the "
        f"narrow panel — with a defined value. This differs from the unsuffixed "
        f"mk_rho_mean_housekeeping, which does intersect the housekeeping panel with "
        f"the requested marker panel.",
    ),
    (
        "mk_rho_marker_minus_hk_narrow_set",
        "Distributional similarity",
        "Group L (Distributional similarity): mk_rho_mean_markers_narrow_set minus "
        "mk_rho_mean_housekeeping_narrow_set — the narrow-panel marker-versus-"
        "housekeeping contrast with the full housekeeping panel as control, and the "
        "primary margin of the narrow family. Section 3b of "
        "correlation_prediction_metrics_analysis_narrow_set.ipynb compares its noise "
        "(within-(strategy, imputation) spread, and spread of the control term itself) "
        "and its best-versus-rest discriminative power against the coverage-matched "
        "PGK1-only margin; the winner there is the one quoted in the manuscript.",
        f"{SHARED_CALC} mk_rho_marker_minus_hk_narrow_set = "
        f"mk_rho_mean_markers_narrow_set - mk_rho_mean_housekeeping_narrow_set (NaN if "
        f"either side has no genes with a defined value).",
    ),
    (
        "mk_rho_mean_by_cohort_mean_narrow_set",
        "Distributional similarity",
        "Group L (Distributional similarity): the same underlying per-cohort, per-gene "
        "Spearman correlations as mk_rho_mean_all_genes_narrow_set, but averaged the "
        "other way — first over the narrow-panel genes within each eligible cohort "
        "(>=20 samples), then over cohorts. Differs from the gene-first mean when "
        "cohorts vary in how many narrow-panel genes have a defined correlation.",
        "The per-cohort means of the narrow family are accumulated in the same cohort "
        "loop as the full-panel ones but into a separate dict (per_cohort_narrow), "
        "because a per-cohort mean cannot be recovered from rho_by_gene afterwards. "
        "per_cohort_narrow[cohort] = mean of that cohort's per-gene rho over the "
        "narrow-panel genes with a defined value there; "
        "mk_rho_mean_by_cohort_mean_narrow_set = mean(per_cohort_narrow.values()). "
        "Implemented in compute_group_l().",
    ),
    (
        "mk_rho_mean_PGK1_only_narrow_set",
        "Distributional similarity",
        f"Group L (Distributional similarity), narrow family only: the "
        f"coverage-matched housekeeping control — the mean per-gene Spearman rho over "
        f"the housekeeping genes that are themselves inside the narrow panel, which is "
        f"exactly one gene, PGK1. It cleared the same all-{N_RAW_PAIRS}-raw-pairs and "
        f"frac_lt_1 gates as the narrow markers, so it is measured on the same footing "
        f"as them, but it is a single gene and therefore the noisier of the two "
        f"controls by construction. Both controls are reported so the choice can be "
        f"made from the data rather than argued about.",
        f"{SHARED_CALC} mk_rho_mean_PGK1_only_narrow_set = mean(rho_by_gene) over genes "
        f"in narrow_mask & hk_mask with a defined value. The invariant "
        f"narrow set INTERSECT housekeeping == {{PGK1}} is asserted in "
        f"build_marker_gene_annotation.py, so the gene symbol carried in the metric "
        f"name cannot go stale silently if the panel is regenerated.",
    ),
    (
        "mk_rho_marker_minus_PGK1_only_narrow_set",
        "Distributional similarity",
        "Group L (Distributional similarity), narrow family only: "
        "mk_rho_mean_markers_narrow_set minus mk_rho_mean_PGK1_only_narrow_set — the "
        "second, coverage-matched narrow-panel margin. Marker and control genes here "
        "passed identical coverage and expression-level gates, so the contrast is not "
        "confounded by the control set changing composition between attempts; the "
        "price is a control of n = 1. Read together with "
        "mk_rho_marker_minus_hk_narrow_set, never alone.",
        f"{SHARED_CALC} mk_rho_marker_minus_PGK1_only_narrow_set = "
        f"mk_rho_mean_markers_narrow_set - mk_rho_mean_PGK1_only_narrow_set (NaN if "
        f"either side has no genes with a defined value).",
    ),
]

assert len(NEW_METRICS) == 15, len(NEW_METRICS)
assert len({m for m, *_ in NEW_METRICS}) == 15, "duplicate metric name"

# ── The 2 new Table_S2_metrics rows ───────────────────────────────────────────

KOTLOV = (
    "Kotlov,N., Bagaev,A., Revuelta,M.V., Phillip,J.M., Cacciapuoti,M.T., Antysheva,Z., "
    "Svekolkin,V., Tikhonova,E., Miheecheva,N., Kuzkina,N., et al. (2021) Clinical and "
    "Biological Subtypes of B-cell Lymphoma Revealed by Microenvironmental Signatures. "
    "Cancer Discov., 11, 1468–1489."
)
HOLMES = (
    "Holmes,A.B., Corinaldesi,C., Shen,Q., Kumar,R., Compagno,N., Wang,Z., Nitzan,M., "
    "Grunstein,E., Pasqualucci,L., Dalla-Favera,R. and Basso,K. (2020) Single-cell analysis "
    "of germinal-center B cells informs on lymphoma cell of origin and outcome. J. Exp. Med., "
    "217, e20200483."
)
NARROW_SOURCE = (
    f"This study (custom implementation); Spearman rank correlation. Marker panel from "
    f"{KOTLOV} and {HOLMES} Narrow subset derived in this study from the gene coverage "
    f"and per-gene expression QC audit in harmonization-metrics-calculation/"
    f"gene_panel_analysis/; the full panel with its coverage statistics and the "
    f"in_narrow_set flag is the Table_S3_gene_panel sheet."
)

NEW_S2_ROWS = [
    (
        "Marker gene expression profile preservation on the QC-filtered narrow panel "
        "(Spearman ρ)",
        "Distributional similarity",
        "L",
        f"The Group L aggregates recomputed over a fixed {N_NARROW}-gene subset of the "
        f"marker panel instead of all 633 genes, reported as a parallel family of "
        f"columns suffixed _narrow_set. {NARROW_DEF} Both families are reductions of "
        f"one and the same per-gene correlation pass, so they differ only by gene set. "
        f"The motivation is comparability: marker coverage varies with the "
        f"batch-removal strategy and the imputation, so a full-panel mean is partly a "
        f"coverage statistic and partly a preservation statistic, whereas the narrow "
        f"panel is present in every unharmonized reference and excludes genes sitting "
        f"in the log2 noise band. The marker-versus-housekeeping contrast is reported "
        f"twice for this panel, once against the full {N_HK}-gene housekeeping control "
        f"and once against the coverage-matched single-gene control (see the next row).",
        NARROW_SOURCE,
    ),
    (
        "Coverage-matched single-gene housekeeping control for the narrow panel (PGK1)",
        "Distributional similarity",
        "L",
        f"An alternative control term for the narrow-panel marker-versus-housekeeping "
        f"contrast. Only PGK1 of the {N_HK} housekeeping genes clears the coverage and "
        f"expression-level gates that define the narrow panel, so the default control "
        f"— the mean over all resolved housekeeping genes — is measured on genes the "
        f"narrow markers were explicitly filtered against, and its composition changes "
        f"between attempts. Subtracting PGK1 alone matches the control to the markers "
        f"on coverage and expression level at the cost of n = 1. Both margins are "
        f"reported for every attempt; §3b of "
        f"correlation_prediction_metrics_analysis_narrow_set.ipynb decides between "
        f"them on within-(strategy, imputation) dispersion, dispersion of the control "
        f"term itself, and best-versus-rest rank-biserial effect size.",
        NARROW_SOURCE,
    ),
]

# ── Table_S3_gene_panel column plan ───────────────────────────────────────────
# Three blocks joined on gene:
#   1. the annotation itself (one row per gene x signature) - the panel's provenance;
#   2. the coverage audit from gene_panel_analysis/build_marker_gene_coverage.py;
#   3. the gene-level statistics of marker_gene_deep_analysis.ipynb (its Table T9),
#      rebuilt here by build_gene_level_stats() so the sheet does not depend on the
#      notebook having been run.
# Per-strategy `present_in_*` booleans are dropped as redundant with their `frac_in_*`
# counterpart (present == frac equal to 1.0).

STRATEGIES = [
    "S0_no_removal", "A_confirmed_bad", "B_extended_bad", "C_rnaseq_only",
    "D_malignant_only", "E1_iterative_r1", "E2_iterative_r2", "E3_iterative_r3",
    "F_microarray_only", "G_affymetrix_only", "H_affymetrix_extended",
    "I_rare_batches_removed", "J_ff_only", "K_ffpe_only",
]

ANN_COLS = [
    ("gene", "Gene"),
    ("alias", "Alias"),
    ("gene_group", "Signature"),
    ("cell_type", "Cell type"),
    ("pathway", "Pathway"),
    ("tme_subtype", "TME subtype"),
    ("prognostic_significance", "Prognostic significance"),
    ("source_article", "Source article"),
    ("provenance", "Provenance"),
    ("is_housekeeping", "Housekeeping control"),
    ("in_narrow_set", "In narrow set"),
]
COV_COLS = [
    ("n_raw_pairs_present", f"Raw reference matrices present (n of {N_RAW_PAIRS})"),
    ("frac_raw_pairs_present", "Raw reference matrices present (fraction)"),
    ("present_in_all_raw_pairs", f"Present in all {N_RAW_PAIRS} raw reference matrices"),
    ("n_attempts_present", "Harmonization attempts present (n)"),
    ("frac_attempts_present", "Harmonization attempts present (fraction)"),
    ("n_attempts_present_scope", "Attempts present, Article 1 scope (n)"),
    ("frac_attempts_present_scope", "Attempts present, Article 1 scope (fraction)"),
    ("n_strats_present", "Strategies with full presence (n of 14)"),
] + [(f"frac_in_{s}", f"Present fraction — {s}") for s in STRATEGIES]

# Block 3. The gene-level statistics, in the order they are derived in the notebook:
# the reference-strategy coverage that gate 1 of the narrow set is read from, the
# distribution of the gene's Spearman rho across attempts, the three gate outcomes, the
# expression QC in its two flavours, and the within-signature PC1 loading.
QC_STATS = [
    ("zero_frac", "Zero-expression fraction"),
    ("frac_lt_1", "Fraction of samples with expression < 1"),
    ("detection_frac", "Detection fraction"),
    ("mean_expr", "Mean expression, log2"),
    ("sd_expr", "SD of expression, log2"),
    ("cv", "Coefficient of variation"),
    ("var_between_cohort", "Between-cohort variance"),
    ("var_within_cohort", "Within-cohort variance"),
    ("icc_cohort", "ICC across cohorts"),
    ("genorm_m", "geNorm M stability"),
    ("n_qc_attempts", "QC matrices contributing (n)"),
]
STAT_COLS = (
    [("frac_ref_strategy", f"Present fraction — {REF_STRATEGY} attempts "
                           f"(narrow-set gate 1)")]
    + [
        ("mean_rho", "Mean ρ across attempts"),
        ("median_rho", "Median ρ across attempts"),
        ("sd_rho", "SD of ρ across attempts"),
        ("p05_rho", "5th percentile of ρ across attempts"),
        ("p95_rho", "95th percentile of ρ across attempts"),
        ("n_attempts", "Attempts with a defined ρ (n)"),
        ("passes_coverage", f"Passes coverage gate (all {N_RAW_PAIRS} raw references)"),
        ("passes_qc", "Passes expression QC gate"),
        ("saturated", f"Saturated (median ρ > {SATURATION_MEDIAN_MAX})"),
    ]
    + [(f"{c}_raw", f"{h} — raw references") for c, h in QC_STATS]
    + [(f"{c}_all", f"{h} — all attempts") for c, h in QC_STATS]
    + [("kme_mean", "PC1 loading within signature (kME)")]
)

SHEET_NAME = "Table_S3_gene_panel"

# Derived gene-level table. Cached next to the other metric tables so a re-run needs no
# download; delete it to force a rebuild from S3.
GENE_STATS_CSV = REPO / "harmonization-metrics" / "metric_tables" / "gene_level_stats_260905.csv"
CACHE_DIR = Path("/tmp/fl_gene_panel_cache")
S3_INPUTS = {
    "metrics_comprehensive.csv": "metrics_comprehensive.csv",
    "marker_gene_correlations_long.csv": "marker_gene_correlations_long.csv",
    "gene_qc_long.csv.gz": "gene_qc_long.csv.gz",
}
CONSENSUS_CSV = (REPO / "harmonization-metrics" / "metric_tables"
                 / "gene_gene_consensus_within_260828.csv.gz")


def _fetch(name: str) -> Path:
    """Download one aggregated table from S3 into CACHE_DIR if it is not there yet."""
    import boto3

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dest = CACHE_DIR / name
    if dest.exists():
        return dest
    # Same environment contract as bench_shared.py. Read here rather than at import
    # time: with gene_level_stats_260905.csv committed this function is never called,
    # so the script must stay runnable offline with no bucket configured.
    bucket = os.environ["FL_S3_BUCKET"]
    prefix = os.environ.get("FL_S3_PREFIX", "FL_batch_correction")
    key = f"{prefix}/{S3_INPUTS[name]}"
    print(f"  downloading s3://{bucket}/{key} ...")
    boto3.client("s3").download_file(bucket, key, str(dest))
    return dest


def build_gene_level_stats() -> pd.DataFrame:
    """
    Rebuild the gene-level statistics of `marker_gene_deep_analysis.ipynb` (Table T9).

    Reproduces, in the notebook's own order and with its own constants: the analysis
    scope (§2), the per-gene rho distribution over `rho_wide` (§7), the coverage
    fractions (§4), the expression QC aggregates in both flavours (§5 - the 01_raw
    references that the three-threshold gate is evaluated on, and every in-scope attempt,
    which is what the narrow set's second gate reads), the saturation flag (§6) and the
    within-signature PC1 loading (§11).

    Returns
    -------
    pd.DataFrame
        Indexed by gene, one row per annotated gene. Genes never resolved in any matrix
        (61 of the 633) carry NaN throughout - that absence is itself the result.
    """
    import numpy as np

    if GENE_STATS_CSV.exists():
        df = pd.read_csv(GENE_STATS_CSV, index_col=0)
        print(f"gene-level stats: cached ({df.shape[0]} genes x {df.shape[1]} cols)")
        return df

    print("gene-level stats: rebuilding from the S3 aggregate tables")
    dm = pd.read_csv(_fetch("metrics_comprehensive.csv"), low_memory=False)
    dm["run_id"] = (dm["strat"] + "__" + dm["imp"] + "__" + dm["method"]
                    + "__post" + dm["post_rm"].map({False: "0", True: "1"}))
    is_sh = dm["method"].str.startswith("shambhala")
    dm = dm[((~is_sh) | (dm["method"] == "shambhala_P0std_Q0std"))
            & (dm["status"] == "ok")]
    scope = set(dm["run_id"])
    assert len(scope) == N_SCOPE, f"analysis scope is {len(scope)}, expected {N_SCOPE}"

    # §2/§7 — per-gene rho distribution over the genes x attempts matrix.
    rl = pd.read_csv(_fetch("marker_gene_correlations_long.csv"))
    rl = rl[rl["run_id"].isin(scope)].copy()
    parts = rl["run_id"].str.split("__", expand=True)
    rl["strat"], rl["method"], rl["post"] = parts[0], parts[2], parts[3]
    rho_wide = rl.pivot_table(index="gene", columns="run_id", values="rho")

    # §4 — coverage, in the three scopes the notebook distinguishes.
    raw = rl[(rl["method"] == "01_raw") & (rl["post"] == "post0")]
    ref = rl[rl["strat"] == REF_STRATEGY]
    n_raw, n_ref = raw["run_id"].nunique(), ref["run_id"].nunique()
    assert (n_raw, n_ref) == (N_RAW_PAIRS, N_REF_ATTEMPTS), (n_raw, n_ref)
    cov = pd.DataFrame({
        "n_raw": raw.groupby("gene")["run_id"].nunique(),
        "n_ref": ref.groupby("gene")["run_id"].nunique(),
    }).reindex(rho_wide.index).fillna(0).astype(int)
    cov["frac_raw_pairs"] = cov["n_raw"] / n_raw
    cov["frac_ref_strategy"] = cov["n_ref"] / n_ref
    covered = set(cov.index[cov["frac_raw_pairs"] >= 1.0])

    out = pd.DataFrame({
        "frac_ref_strategy": cov["frac_ref_strategy"],
        "mean_rho": rho_wide.mean(axis=1),
        "median_rho": rho_wide.median(axis=1),
        "sd_rho": rho_wide.std(axis=1),
        "p05_rho": rho_wide.quantile(0.05, axis=1),
        "p95_rho": rho_wide.quantile(0.95, axis=1),
        "n_attempts": rho_wide.notna().sum(axis=1),
    })
    out["saturated"] = out["median_rho"] > SATURATION_MEDIAN_MAX

    # §5/§11 — expression QC, averaged over attempts. Two flavours: the 01_raw
    # references, where a threshold on the log2 scale still means what it says, and
    # every in-scope attempt, which is the flavour the narrow set's gate 2 used.
    agg = dict(
        zero_frac=("zero_frac", "mean"), frac_lt_1=("frac_lt_1", "mean"),
        detection_frac=("detection_frac", "mean"), mean_expr=("mean", "mean"),
        sd_expr=("sd", "mean"), cv=("cv", "mean"),
        var_between_cohort=("var_between_cohort", "mean"),
        var_within_cohort=("var_within_cohort", "mean"),
        icc_cohort=("icc_cohort", "mean"), genorm_m=("genorm_m", "mean"),
        n_qc_attempts=("run_id", "nunique"),
    )
    qc = pd.read_csv(_fetch("gene_qc_long.csv.gz"))
    qc = qc[qc["run_id"].isin(scope)]
    qc_raw = qc[(qc["method"] == "01_raw") & (~qc["post_rm"])].groupby("gene").agg(**agg)
    qc_all = qc.groupby("gene").agg(**agg)

    passes_qc = set(qc_raw.index[
        (qc_raw["zero_frac"] <= ZERO_FRAC_MAX)
        & (qc_raw["frac_lt_1"] <= LOW_FRAC_MAX)
        & (qc_raw["detection_frac"] >= MIN_DETECTION_FRAC)])
    out["passes_coverage"] = out.index.isin(covered)
    out["passes_qc"] = out.index.isin(passes_qc)
    out = out.join(qc_raw.add_suffix("_raw")).join(qc_all.add_suffix("_all"))

    # §11 — each gene's loading on PC1 of its own signature's consensus correlation
    # block, averaged over the signatures it belongs to. Signatures with <3 resolved
    # genes have no meaningful PC1 and are skipped, as in the notebook.
    ann_raw = pd.read_csv(ANN_CSV)
    cons = pd.read_csv(CONSENSUS_CSV, index_col=0)
    keep = [g for g in cons.index if g in set(ann_raw["gene"])]
    R = cons.loc[keep, keep]
    rows: list[dict] = []
    for grp, sub_ann in ann_raw.groupby("gene_group"):
        genes_in = [g for g in sub_ann["gene"].unique() if g in R.index]
        if len(genes_in) < 3:
            continue
        block = np.nan_to_num(R.loc[genes_in, genes_in].values, nan=0.0)
        pc1 = np.linalg.eigh(block)[1][:, -1]
        if pc1.sum() < 0:                       # eigenvector sign is arbitrary
            pc1 = -pc1
        rows.extend({"gene": g, "kme": float(v)} for g, v in zip(genes_in, pc1))
    out = out.join(pd.DataFrame(rows).groupby("gene")["kme"].mean().rename("kme_mean"))

    out = out.reindex(sorted(set(ann_raw["gene"])))
    out.index.name = "gene"
    GENE_STATS_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(GENE_STATS_CSV)
    print(f"gene-level stats: wrote {GENE_STATS_CSV} "
          f"({out.shape[0]} genes x {out.shape[1]} cols)")
    return out


def build_gene_panel_frame() -> pd.DataFrame:
    """Join the marker annotation, the coverage audit and the gene-level statistics."""
    ann = pd.read_csv(ANN_CSV)
    cov = pd.read_csv(COV_CSV)
    stats = build_gene_level_stats()

    assert "in_narrow_set" in ann.columns, f"{ANN_CSV} predates the in_narrow_set column"
    ann["is_housekeeping"] = ann["is_housekeeping"].astype(bool)
    ann["in_narrow_set"] = ann["in_narrow_set"].astype(bool)

    missing = sorted(set(ann["gene"]) - set(cov["gene"]))
    assert not missing, f"genes absent from the coverage audit: {missing}"
    assert ann.loc[ann["in_narrow_set"], "gene"].nunique() == N_NARROW
    assert ann.loc[ann["is_housekeeping"], "gene"].nunique() == N_HK

    narrow = set(ann.loc[ann["in_narrow_set"], "gene"])
    hk = set(ann.loc[ann["is_housekeeping"], "gene"])
    assert narrow & hk == {"PGK1"}, f"narrow INTERSECT housekeeping = {narrow & hk}"

    # Re-derive the narrow set from its two published gates. This is the check that
    # caught the provenance error in build_marker_gene_annotation.py's comment: the gate
    # actually applied is full coverage of the reference strategy (61 genes), not
    # presence in all 42 raw references (193 genes, which would yield 171 not 56).
    gate1 = set(stats.index[stats["frac_ref_strategy"] >= 1.0])
    assert len(gate1) == N_REF_COVERED, f"gate 1 selects {len(gate1)}, not {N_REF_COVERED}"
    rederived = gate1 & set(stats.index[stats["frac_lt_1_all"] < 0.20])
    assert rederived == narrow, (
        f"narrow set does not reproduce: missing {sorted(narrow - rederived)}, "
        f"extra {sorted(rederived - narrow)}")
    # ...and the wider gate the source comment names still holds as a superset.
    assert cov.loc[cov["gene"].isin(narrow), "present_in_all_raw_pairs"].all()

    df = (ann.merge(cov, on="gene", how="left", validate="many_to_one")
             .merge(stats.reset_index(), on="gene", how="left", validate="many_to_one"))
    df = df[[c for c, _ in ANN_COLS] + [c for c, _ in COV_COLS]
            + [c for c, _ in STAT_COLS]]
    df.columns = ([h for _, h in ANN_COLS] + [h for _, h in COV_COLS]
                  + [h for _, h in STAT_COLS])
    return df.sort_values(["Gene", "Signature"], kind="stable").reset_index(drop=True)


def retext_narrow_definition(wb) -> int:
    """
    Replace the superseded narrow-set provenance sentence wherever it was written.

    The first version of this script described the narrow set with the criteria in
    `build_marker_gene_annotation.py`'s comment, which name the wrong coverage gate.
    Any cell still carrying that sentence is rewritten with the corrected NARROW_DEF, so
    re-running the script repairs a workbook produced by the earlier version.
    """
    stale = (
        f"genes that resolve in all {N_RAW_PAIRS} 01_raw__post0 reference matrices "
        f"(14 strategies x 3 imputations) and whose mean frac_lt_1 on those references "
        f"is below 0.20, i.e. fewer than 20% of samples sit in the log2 noise band. "
        f"193 of the 633 panel genes clear the coverage gate and {N_NARROW} clear both; "
        f"exactly one of them (PGK1) is a housekeeping control."
    )
    old_head = (
        f"The narrow panel is the QC-filtered {N_NARROW}-gene subset of the marker "
        f"table (the in_narrow_set flag in marker_gene_annotation.csv, listed in the "
        f"Table_S3_gene_panel sheet): "
    )
    n = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and stale in cell.value:
                    cell.value = cell.value.replace(old_head + stale, NARROW_DEF)
                    n += 1
    return n


def main() -> None:
    wb = openpyxl.load_workbook(PATH)

    # ── 1. Metric_polarity ────────────────────────────────────────────────────
    ws1 = wb["Metric_polarity"]
    existing = {ws1.cell(row=r, column=1).value for r in range(2, ws1.max_row + 1)}
    to_add = [m for m in NEW_METRICS if m[0] not in existing]
    if to_add:
        data_font = copy.copy(ws1["A2"].font)
        data_align = copy.copy(ws1["A2"].alignment)
        row = ws1.max_row + 1
        for name, mtype, expl, calc in to_add:
            for col, val in enumerate((name, 0, "L", mtype, expl, calc), start=1):
                cell = ws1.cell(row=row, column=col, value=val)
                cell.font = data_font
                cell.alignment = data_align
            row += 1
        print(f"Metric_polarity: appended {len(to_add)} rows (now {ws1.max_row})")
    else:
        print("Metric_polarity: all 15 narrow-set rows already present, skipped")

    # ── 2. Table_S2_metrics ───────────────────────────────────────────────────
    ws2 = wb["Table_S2_metrics"]
    existing_s2 = {ws2.cell(row=r, column=1).value for r in range(2, ws2.max_row + 1)}
    to_add_s2 = [r for r in NEW_S2_ROWS if r[0] not in existing_s2]
    if to_add_s2:
        data_font = copy.copy(ws2["A2"].font)
        data_align = copy.copy(ws2["A2"].alignment)
        row = ws2.max_row + 1
        for entry in to_add_s2:
            for col, val in enumerate(entry, start=1):
                cell = ws2.cell(row=row, column=col, value=val)
                cell.font = data_font
                cell.alignment = data_align
            row += 1
        print(f"Table_S2_metrics: appended {len(to_add_s2)} rows (now {ws2.max_row})")
    else:
        print("Table_S2_metrics: narrow-panel rows already present, skipped")

    # ── 2b. Repair the superseded narrow-set wording, if present ──────────────
    n_retext = retext_narrow_definition(wb)
    print(f"Narrow-set definition: corrected in {n_retext} cells")

    # ── 3. Table_S3_gene_panel ────────────────────────────────────────────────
    df = build_gene_panel_frame()
    if SHEET_NAME in wb.sheetnames:
        del wb[SHEET_NAME]
        print(f"{SHEET_NAME}: existing sheet removed, rebuilding")
    ws3 = wb.create_sheet(SHEET_NAME)

    hdr_font = copy.copy(wb["Table_S1_methods"]["A1"].font)
    hdr_align = copy.copy(wb["Table_S1_methods"]["A1"].alignment)
    body_font = copy.copy(wb["Table_S1_methods"]["A2"].font)

    for col, header in enumerate(df.columns, start=1):
        cell = ws3.cell(row=1, column=col, value=header)
        cell.font = hdr_font
        cell.alignment = hdr_align

    for r, record in enumerate(df.itertuples(index=False, name=None), start=2):
        for col, val in enumerate(record, start=1):
            if val is None or (isinstance(val, float) and pd.isna(val)):
                val = None
            elif hasattr(val, "item"):          # numpy scalar -> Python scalar
                val = val.item()
            cell = ws3.cell(row=r, column=col, value=val)
            cell.font = body_font

    # Long free-text columns get room; everything numeric stays narrow. Data cells are
    # deliberately not wrapped: 834 rows of wrapped source-article strings would make
    # the sheet unreadable.
    WIDTHS = {
        "Gene": 12, "Alias": 10, "Signature": 30, "Cell type": 24, "Pathway": 20,
        "TME subtype": 16, "Prognostic significance": 22, "Source article": 60,
        "Provenance": 20, "Housekeeping control": 12, "In narrow set": 12,
    }
    for col, header in enumerate(df.columns, start=1):
        ws3.column_dimensions[get_column_letter(col)].width = WIDTHS.get(header, 18)
    ws3.row_dimensions[1].height = 60
    ws3.freeze_panes = "B2"
    ws3.auto_filter.ref = f"A1:{get_column_letter(df.shape[1])}{df.shape[0] + 1}"
    n_stats = df["Mean ρ across attempts"].notna().sum()
    print(f"{SHEET_NAME}: {df.shape[0]} rows x {df.shape[1]} columns "
          f"({df['Gene'].nunique()} genes, {df['Signature'].nunique()} signatures, "
          f"{df.loc[df['In narrow set'], 'Gene'].nunique()} narrow-set; "
          f"{n_stats} rows carry gene-level statistics)")

    wb.save(PATH)
    print("Saved:", PATH)


if __name__ == "__main__":
    main()
