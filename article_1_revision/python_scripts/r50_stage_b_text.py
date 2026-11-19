"""
r50_stage_b_text.py — the text of manuscript stage B (plan WP11; gate G4 answered 2026-11-07).

Data only: every new or rewritten paragraph of stage B, keyed by the baseline body index of
`inputs/baseline_dump.txt`. `r50_manuscript_tracked_edits.py --stage B` reads this module,
fills the `{{key}}` / `{{key:fmt}}` placeholders from `output/numbers.json` (r45; a missing
key stops the run, so no number is ever typed here) and writes the edits as Word tracked
changes on top of the stage-A document.

Rules followed by every text below (plan §1.1, Daniil 2026-11-07):
- plain words only: no internal labels, script or column names;
- no comparison with the submitted version of the article (no "submitted", "previously
  selected", "first version" results);
- every number is a placeholder read from numbers.json;
- no Supplementary Figure citation in the Methods (citation order starts in the Results).

Record kinds (interpreted by r50):
- REWRITES: body index → (expected opening words, [new paragraph texts]). The old paragraph
  becomes a tracked deletion; the new paragraphs are tracked insertions right after it.
- REPLACEMENTS: body index → (expected opening words, [(old, new), ...]) — tracked
  replacements inside a paragraph (citations untouched).
- INSERT_AFTER: body index → [(style, text), ...] — new paragraphs (style "Heading2" or
  None = body style of the anchor) inserted after the anchor paragraph.
- DELETIONS: body index → expected opening words — tracked deletion of the paragraph.
"""

from __future__ import annotations

# Supplementary figure renumbering, old → new (plan WP9 §9.2): S2–S4 merged into S2,
# S8 and S10 removed, S11–S17 → S7–S13, S18 → S14, S19 → S15; S16–S18 are new.
SUPPLEMENTARY_FIGURE_MAP: dict[int, int | None] = {
    1: 1, 2: 2, 3: 2, 4: 2, 5: 3, 6: 4, 7: 5, 8: None, 9: 6, 10: None,
    11: 7, 12: 8, 13: 9, 14: 10, 15: 11, 16: 12, 17: 13, 18: 14, 19: 15,
}

REWRITES: dict[int, tuple[str, list[str]]] = {
    # ── Abstract (≤ 200 words) ────────────────────────────────────────────────
    13: (
        "Cross-platform harmonization of bulk transcriptomic",
        [
            "Cross-platform harmonization of bulk transcriptomic datasets remains a "
            "fundamental challenge for developing cancer biomarkers because of persistent "
            "batch effects. Most tools are benchmarked on datasets with large biological "
            "differences, whereas biomarker mining requires preserving subtle distinctions "
            "between closely related diagnoses. Here we present ComboBatch, a pipeline that "
            "evaluates the full cross-product of 14 batch-removal strategies, 3 imputation "
            "methods, 33 harmonization algorithms (31 analysed) and 2 post-removal "
            "conditions across 7,174 samples from 88 germinal-center B-cell lymphoma cohorts "
            "on four transcriptomic platforms. On a non-redundant panel of {{panel_n_panel}} "
            "quality metrics over 2,234 approaches, method (η² {{eta2_panel__Method:.2f}}) and "
            "batch-removal strategy ({{eta2_panel__Strategy:.2f}}) outweighed imputation "
            "({{eta2_panel__Imputation:.2f}}) and post-removal ({{eta2_panel__Post-removal:.3f}}). "
            "A written selection rule (marker-gene correlation and cross-batch prediction "
            "thresholds, a Pareto front of batch mixing and diagnosis retention, and visual "
            "inspection) recommended {{n_selected}} approaches: Surrogate Variable Analysis "
            "for FFPE-only and RNA-seq-only data, Feature Specific Quantile Normalization, "
            "FSMVN and ComBat variants for RNA-seq combined with microarrays, and Angel for "
            "fresh-frozen data. A confounding gradient showed that the metrics stay "
            "informative up to the confounding of real cohorts but not when batch and "
            "diagnosis coincide; held-out cohorts confirmed the choice in three of four "
            "scenarios."
        ],
    ),
    # ── Methods: harmonization method harshness → one sentence ────────────────
    57: (
        "Each implemented method was assigned a qualitative harshness score",
        [
            "Supplementary Table S1 also gives each method a qualitative harshness tier "
            "(low, medium or high) from its published description; the tiers are "
            "descriptive and are not used in the analysis."
        ],
    ),
    # ── Methods: metric families → reduced panel and four scores ──────────────
    65: (
        "The 87 scoring metrics spanned four major groups",
        [
            "The 87 scoring metrics spanned global distance, local neighborhood, "
            "distributional similarity and other metrics (NA rate, bimodality, zero "
            "expression). Because many of them were correlated, and the platform, "
            "sequencing-source and cohort variants were undefined in single-platform or "
            "single-biomaterial strategies, we reduced them to a non-redundant panel. Of the "
            "{{panel_n_universe}} metrics computed on batch, on diagnosis or without an "
            "annotation column (the tSNE centroid dispersion was excluded, because tSNE does "
            "not preserve distances), metrics with an absolute Spearman correlation of at "
            "least 0.8 over the 2,234 approaches were grouped (complete linkage) and the "
            "medoid of each of the {{panel_n_clusters}} groups was kept. "
            "{{panel_complete_on_panel}} approaches are complete on this panel, against "
            "{{panel_complete_on_87}} on all 87 metrics. Four scores summarize the panel, "
            "each one headline metric in its native unit: global batch removal (principal "
            "component regression on batch), global diagnosis retention (principal "
            "component regression on diagnosis), local batch mixing (kBET acceptance rate) "
            "and local diagnosis separation (graph connectivity on diagnosis). Batch mixing "
            "(global + local mean) and diagnosis retention (global + local mean) are the "
            "means of the min–max-scaled global and local scores; no total score is computed."
        ],
    ),
    # ── Results: metric availability and the central clustermap ───────────────
    102: (
        "For each of the 2,234 successful harmonization approaches",
        [
            "For each of the 2,234 successful harmonization approaches we computed up to 344 "
            "metrics (Supplementary File 3; Supplementary Table S2). On all 87 scoring "
            "metrics only {{panel_complete_on_87}} approaches were complete, because "
            "annotation columns become invariant in single-platform or single-biomaterial "
            "strategies (C, G, J, K); on the reduced panel {{panel_complete_on_panel}} were "
            "complete and availability was nearly equal across strategies (Supplementary "
            "Figure 4). Among all 87 scoring metrics cut at the same |ρ| ≥ 0.8, the panel "
            "metrics fell into {{s5_clusters_with_panel}} of {{s5_n_clusters_87}} correlation "
            "clusters; {{s5_panel_medoid}} were the medoid of their cluster, and the other "
            "{{s5_panel_not_medoid}} sat next to a platform or major-group variant excluded "
            "from the panel by design, within {{s5_max_medoid_gap}} of its mean |ρ| "
            "(Supplementary Figure 5). Of the {{s5_clusters_without_panel}} clusters without "
            "a panel metric, {{s5_free_clusters_batch_or_diagnosis}} held batch or diagnosis "
            "metrics; the rest held cohort, sequencing-source, platform and tumour / normal "
            "variants."
        ],
    ),
    106: (
        "Using the 87 polarity-defined metrics and 2,234 qualifying",
        [
            "The clustermap of the 2,234 approaches on the {{panel_n_panel}} panel metrics "
            "(Figure 3) resolved {{fig3_n_metric_clusters}} metric clusters (global metrics, "
            "two clusters of local metrics, missing values, and bimodality with zero "
            "fraction) and {{fig3_n_approach_clusters}} approach clusters. Cross-platform "
            "approaches with good local batch mixing formed one cluster "
            "({{fig3_cluster_n__Cross-platform, good batch mixing}} approaches) and "
            "approaches of a single platform or sample type another "
            "({{fig3_cluster_n__Same platform / sample type, good batch mixing}}); two "
            "cross-platform clusters with poor batch mixing held "
            "{{fig3_cluster_n__Cross-platform, poor batch mixing A}} and "
            "{{fig3_cluster_n__Cross-platform, poor batch mixing B}} approaches. Of the "
            "{{n_selected}} recommended approaches (below), "
            "{{fig3_cluster_recommended__Cross-platform, good batch mixing}} lay in the "
            "first cluster, {{fig3_cluster_recommended__Same platform / sample type, good batch mixing}} "
            "in the single-platform cluster and "
            "{{fig3_cluster_recommended__Cross-platform, poor batch mixing B}} in a "
            "poor-mixing cluster whose bimodality and missing-value metrics were best. kBET "
            "acceptance stayed near zero for almost every approach. The correlations between "
            "approaches on the panel (Supplementary Figure 6) reproduced the separation by "
            "strategy, so sample composition, more than the method, set the range of "
            "achievable quality."
        ],
    ),
    # ── Results: Figure 3 legend and alt text ─────────────────────────────────
    114: (
        "Figure 3.",
        [
            "Figure 3. Clustermap of 2,234 harmonization approaches (columns) on the "
            "{{panel_n_panel}} metrics of the reduced panel (rows), polarity adjusted and "
            "min–max scaled (1 = best). Black cells are undefined metrics. Shaded bands name "
            "the approach and metric clusters; the column annotation gives strategy, method "
            "and imputation, and a black mark the {{n_selected}} recommended approaches. Row "
            "annotation: metric group, score and annotation column."
        ],
    ),
    115: (
        "Alt text:",
        [
            "Alt text: Clustermap of 2,234 harmonization approaches scored on 22 non-redundant "
            "quality metrics, with named clusters of approaches and metrics, black cells for "
            "missing metrics and marks for the recommended approaches."
        ],
    ),
    # ── Results: the selection rule and the visual check ──────────────────────
    118: (
        "Based on the clustermap visual inspection",
        [
            "The selection rule (Methods) was applied once, as written; its front is the "
            "Pareto front, the approaches that no other approach beats on both batch mixing "
            "and diagnosis retention. Of the 2,234 "
            "approaches, {{gate_L_pass}} passed the marker correlation threshold and "
            "{{gate_N_pass}} the prediction check; {{n_identical_to_raw}} returned their "
            "input unchanged and were method failures (exploBATCH "
            "{{n_identical_to_raw__36_explobatch}}, RUV-III-PRPS "
            "{{n_identical_to_raw__31_ruv3prps}}, DWD {{n_identical_to_raw__27_dwd}}, FSQN R "
            "{{n_identical_to_raw__16_fsqn_r}}, SVA {{n_identical_to_raw__04_sva}}). MNN, "
            "Scanorama and almost all Harmony approaches failed the marker correlation "
            "threshold (median marker correlation {{gate_L_median__10_mnn}}, "
            "{{gate_L_median__12_scanorama}} and {{gate_L_median__11_harmony}}) despite "
            "good batch mixing. Figures 4 and 5 show the recommended approach of each "
            "scenario next to the unharmonized data of the same strategy and imputation.",
            "At the visual check, an approach was rejected when batches of the same "
            "diagnosis stayed apart on PCA, UMAP and tSNE. In the FF-only scenario most "
            "front members did not differ from the unharmonized data, while Angel separated "
            "FL, DLBCL and normal B cells into three clouds with batches of the same "
            "diagnosis together. In FFPE only, SVA with softImpute was the only approach "
            "that mixed batches of the same diagnosis on all three plots. In RNA-seq only, "
            "every approach with post-removal was rejected because the removal step deleted "
            "the FFPE exome-capture batch, 939 of 2,243 samples, and ComBat-seq did not mix "
            "FF and FFPE samples; SVA did, and ComBat without imputation brought samples of "
            "the same diagnosis together on PCA. With RNA-seq and microarrays, FSQN R and "
            "FSMVN in D brought the two large DLBCL batches (RNA-seq poly-A "
            "and the Illumina FFPE array) together on UMAP and tSNE, and ComBat and M-ComBat "
            "placed FL, DLBCL and normal B cells as separate groups of batches on PCA. The "
            "approaches that entered the front after a rejection were inspected once in the "
            "same way. In total {{visual_check_n_reviewed}} front members were inspected and "
            "{{n_selected}} accepted (Table 3, Figure 6F). Without the strategies derived "
            "from the first FSQN R harmonization (A, B, E1–E3), FSQN R, ComBat and M-ComBat "
            "stayed on the multi-platform front, FSQN R in first place.",
        ],
    ),
    120: (
        "Table 3.",
        [
            "Table 3. The {{n_selected}} recommended harmonization approaches: Pareto front "
            "of the selection rule, accepted at the visual check, grouped by scenario and "
            "method."
        ],
    ),
    # ── Results: η² on the reduced panel ──────────────────────────────────────
    143: (
        "To quantify the relative contribution of each experimental factor",
        [
            "To quantify the contribution of each experimental factor, we computed the "
            "one-way η² of each factor for each of the {{panel_n_panel}} panel metrics "
            "across the 2,234 approaches and averaged it over the metrics (Figure 6B). The "
            "harmonization method explained on average {{eta2_panel__Method:.3f}} of the "
            "variance of a metric, the batch removal strategy {{eta2_panel__Strategy:.3f}}, "
            "imputation {{eta2_panel__Imputation:.3f}} and post-removal "
            "{{eta2_panel__Post-removal:.3f}}. On all 87 metrics the order was the same "
            "({{eta2_all87__Method:.3f}}, {{eta2_all87__Strategy:.3f}}, "
            "{{eta2_all87__Imputation:.3f}} and {{eta2_all87__Post-removal:.3f}}), so the "
            "hierarchy method > strategy > imputation > post-removal does not depend on the "
            "panel."
        ],
    ),
    # ── Results: four scores of the recommended approaches ────────────────────
    147: (
        "We then visualized the clustermap best approaches",
        [
            "Figure 6C and 6D show the four scores, the marker correlation and the "
            "cross-batch prediction of the front members, with the medians of the "
            "confounding gradient at λ = 0 (balanced batches) and λ = 1 (one diagnosis per "
            "batch) as reference lines, so that each value can be read against what "
            "harmonizers reach with and without confounding. The prediction column gives the "
            "value the rule used (DLBCL versus FL for strategy D, three classes otherwise) "
            "next to that of the unharmonized data of the same strategy and imputation."
        ],
    ),
    # ── Results: Figure 6 legend and alt text ─────────────────────────────────
    155: (
        "Figure 6.",
        [
            "Figure 6. Factor effects, scores of the recommended approaches, confounding "
            "gradient and decision tree. (B) Mean one-way η² of the four experimental "
            "factors over the reduced panel and over all 87 metrics. (C, D) Marker "
            "correlation, cross-batch prediction and the four scores of the front members, "
            "grouped by scenario; reference lines are the gradient medians at λ = 0 (dashed) "
            "and λ = 1 (dotted); prediction is the value used by the rule (DLBCL versus FL "
            "for strategy D, three classes otherwise), open markers the unharmonized data of "
            "the same strategy and imputation. Gradient panel: batch mixing and diagnosis "
            "retention (each the mean of the scaled global and local scores) of the "
            "recommended methods against the measured Cramér's V (lines, mean; bands, mean ± "
            "SD of three replicate draws); dashed lines mark the real data. "
            "(F) Decision tree: dataset composition, recommended method with alternatives, "
            "imputation, and the checks to run on one's own data with their pass values."
        ],
    ),
    156: (
        "Alt text:",
        [
            "Alt text: Bar plot of factor effect sizes, dot plots of the scores of the "
            "recommended approaches with reference lines, line plots of batch mixing and "
            "diagnosis retention against the confounding level, and the harmonization "
            "decision tree."
        ],
    ),
    # ── Results: the old independent-assessment section → gates, confounding, held-out ─
    157: (
        "Best approaches assessment by biomarker expression preservation",
        ["Marker correlation, cross-batch prediction and confounding"],
    ),
    158: (
        "In order to independently assess harmonization quality",
        [
            "The two thresholds of the rule behaved differently (Supplementary Figure 14). "
            "The marker correlation separated the methods sharply: all approaches of most "
            "methods passed, while MNN, Scanorama and Harmony lost the correlation of the "
            "marker genes (Supplementary Figure 14A). The prediction check removed "
            "approaches of every method (Supplementary Figure 14B). Passing the diagnosis "
            "to a method as a covariate raised its cross-batch prediction: on balanced "
            "designs SVA with the covariate reached {{leakage_N__04_sva__l0}}, without it "
            "{{leakage_N__04_sva_nocov__l0}} (Supplementary Figure 14C), so for SVA and "
            "ComBat this metric partly reflects the label given to the method. DLBCL "
            "cell-of-origin subtypes before and after harmonization are shown in "
            "Supplementary Figure 15. The rankings were robust to the panel and to the score "
            "definitions (median Kendall τ-b {{robustness_median_tau}}, range "
            "{{robustness_min_tau}}–{{robustness_max_tau}}), but the single best approach "
            "was not (median overlap of the first three {{robustness_median_top3_jaccard}}); "
            "{{n_selected_stable_all_variants}} of the {{n_selected}} recommended approaches "
            "stayed on the front under every variant (Supplementary Figure 16), so we report "
            "the front, not one winner.",
            "The confounding gradient (Figure 6, Supplementary Figure 17) gave four results. "
            "First, cross-batch prediction fell with confounding for every method, "
            "including the unharmonized data ({{gradient_at0__01_raw__N}} at λ = 0, "
            "{{gradient_at1__01_raw__N}} at λ = 1): when a batch holds one diagnosis, the "
            "left-out batch has no counterpart to learn from. Second, methods that removed "
            "the batch also removed the diagnosis when the two coincided (FSQN R, global "
            "diagnosis retention {{gradient_at0__16_fsqn_r__global_biology_scaled}} → "
            "{{gradient_at1__16_fsqn_r__global_biology_scaled}}; FSMVN "
            "{{gradient_at0__13_fsmvn__global_biology_scaled}} → "
            "{{gradient_at1__13_fsmvn__global_biology_scaled}}), while at λ = 0 they kept it "
            "at least as well as the unharmonized data. Third, methods that left the batch "
            "in place looked better on diagnosis retention as confounding grew (SVA "
            "{{gradient_at0__04_sva__global_biology_scaled}} → "
            "{{gradient_at1__04_sva__global_biology_scaled}}; M-ComBat diagnosis retention "
            "{{gradient_mcombat_biology_retention_l0}} → "
            "{{gradient_mcombat_biology_retention_l09}} at λ = 0.9, batch mixing "
            "{{gradient_mcombat_batch_removal_l0}} → {{gradient_mcombat_batch_removal_l09}}): "
            "batch was read as diagnosis. Fourth, ComBat and M-ComBat with the diagnosis "
            "covariate could not run when every batch held one diagnosis. Supplementary Figure "
            "17A shows where the recommended methods sit among all 14 methods; Supplementary "
            "Figure 17F compares the recommended methods with each other on a scale where "
            "their differences are visible. Of {{gradient_main_tested}} method × score trends, "
            "{{gradient_main_changes}} changed with confounding by both criteria. Up to the "
            "confounding of the real data (V = {{real_data_V__five_batches:.2f}} on these "
            "batches) the changes were moderate. Above it the unharmonized data rose towards "
            "the top of the rule's ranking (median rank {{gradient_raw_rank_l0}} of "
            "{{gradient_n_arms}} at λ = 0, {{gradient_raw_rank_l05_06}} at λ = 0.5–0.6), "
            "behind M-ComBat (median rank {{gradient_mcombat_rank_l05_09}} at λ = 0.5–0.9; "
            "Supplementary Figure 17), and only "
            "{{gradient_pct_pass_l05_09_min}}–{{gradient_pct_pass_l05_09_max}} % of the runs "
            "passed both thresholds. M-ComBat's first rank does not mean that it removed the "
            "batch: its diagnosis covariate keeps every batch difference that coincides with "
            "diagnosis, the diagnosis retention score rewards exactly that difference, and "
            "its batch mixing fell at the same time. The rank of a covariate method under "
            "strong confounding therefore reflects the covariate, not batch mixing.",
            "In the leave-cohort-out validation (Supplementary Figure 18), the method chosen "
            "on the training cohorts was among the three best on the unseen test cohorts in "
            "{{v1_top3_hits}} of {{v1_n_folds}} folds, against {{v1_random_top3_pct}} % "
            "expected for a random method (exact p {{v1_hit_p__3__all}}, false discovery rate "
            "{{v1_hit_q__3__all:q}}), and first in {{v1_hits__1__S0}} of 5 S0 folds (false "
            "discovery rate {{v1_hit_q__1__S0:q}}). Its rank on the test part was better than "
            "that of a random method for S0 (mean rank {{v1_mean_rank__S0}} of about 30, "
            "random {{v1_random_rank__S0}}; Angel chosen in every fold), C "
            "({{v1_mean_rank__C}} vs {{v1_random_rank__C}}) and J ({{v1_mean_rank__J}} vs "
            "{{v1_random_rank__J}}; Angel in every fold), with empirical p "
            "{{v1_rank_p__S0}}, {{v1_rank_p__C}} and {{v1_rank_p__J}} (false discovery rate "
            "{{v1_rank_q_min:q}} or above), and worse for K ({{v1_mean_rank__K}} vs "
            "{{v1_random_rank__K}}): in {{v1_chosen_failed_on_test}} folds the chosen "
            "ComBat or limma could not run on the test cohorts, where each batch held one "
            "diagnosis. The decrease of the chosen method against the best approach on the "
            "test part did not differ from that of a random method on any of the four scores "
            "(Mann–Whitney false discovery rate {{v1_regret_fdr__regret_batch_removal:q}} for "
            "batch mixing, {{v1_regret_fdr__regret_L:q}} for marker correlation).",
        ],
    ),
    # ── Results: decision tree ────────────────────────────────────────────────
    173: (
        "Based on the comprehensive benchmarking analysis",
        [
            "The recommended approaches form a decision tree conditioned on biomaterial "
            "type and platform composition (Figure 6F) with four scenarios: 1) fresh-frozen "
            "only, RNA-seq and microarrays; 2) FFPE only, RNA-seq and microarrays; 3) RNA-seq "
            "only, any biomaterial; and 4) RNA-seq combined with microarrays, any "
            "biomaterial. A single platform with a single biomaterial is not a leaf, because "
            "no benchmark strategy isolated such a dataset."
        ],
    ),
    175: (
        "For fresh-frozen only datasets",
        [
            "For fresh-frozen datasets Angel is recommended ({{n_selected__FF only}} "
            "approaches, any imputation); it was also the rule's choice in every "
            "leave-cohort-out fold of this scenario. For FFPE-only datasets, SVA with "
            "softImpute mixed FFPE Affymetrix, FFPE Illumina and FFPE RNA-seq batches while "
            "keeping FL and DLBCL apart; the leave-cohort-out validation could not confirm a "
            "choice for this scenario, so the visual check matters most here. For RNA-seq "
            "only, SVA with softImpute or KNN is recommended and ComBat without imputation "
            "is the alternative."
        ],
    ),
    177: (
        "For mixed RNA-seq and Illumina microarray datasets",
        [
            "For RNA-seq combined with microarrays, FSQN R in D (malignant samples only) "
            "with KNN imputation ranked first, with FSMVN, ComBat and M-ComBat (in I, rare "
            "batches removed) as alternatives ({{n_selected__RNA-seq + microarrays}} approaches); "
            "the recommendation did not depend on the strategies derived from the first "
            "FSQN R harmonization. Without any sample removal, only Angel was accepted, and "
            "its batches of the same diagnosis overlapped on PCA but stayed apart on tSNE. "
            "On each leaf, the user checks the marker correlation (≥ 0.70), the cross-batch "
            "prediction (not more than 0.05 below the unharmonized data) and the PCA, UMAP "
            "and tSNE plots."
        ],
    ),
    # ── Results: Figures 4–5 rebuilt (Daniil 2026-11-08, gates_review §9.4 B1 option b) ──
    123: (
        "Without harmonization, batch removal and under strict NA handling",
        [
            "Without batch removal, imputation or harmonization, the first principal "
            "component explained {{fig45__4A__pc1}} % of the variance, and on tSNE every "
            "batch formed its own cluster with no grouping by diagnosis (Figure 4A). For "
            "fresh-frozen samples (J), Angel with softImpute brought the batches together on "
            "PCA (first component {{fig45__4B__pc1_raw}} % → {{fig45__4B__pc1}} % of the "
            "variance) and ordered the samples by diagnosis, with DLBCL, FL and normal B "
            "cells as three adjacent clouds (Figure 4B); on tSNE the RNA-seq poly-A batch "
            "and the Affymetrix batches still formed separate groups. Its marker "
            "correlation was {{fig45__4B__L}}, and cross-batch prediction rose from "
            "{{fig45__4B__N_raw}} to {{fig45__4B__N}}."
        ],
    ),
    125: (
        "We next examined the second top-performing approach",
        [
            "In K (FFPE only), SVA with softImpute merged the DLBCL samples of the RNA-seq "
            "exome-capture, Affymetrix and Illumina FFPE batches into one cloud on tSNE, "
            "while FL and high-grade lymphomas stayed apart from DLBCL (Figure 4C); "
            "cross-batch prediction rose from {{fig45__4C__N_raw}} to {{fig45__4C__N}} at a "
            "marker correlation of {{fig45__4C__L}}, just above the threshold. In C "
            "(RNA-seq only), SVA with KNN mixed the fresh-frozen poly-A and the FFPE "
            "exome-capture batches of the same diagnosis on PCA and partly on tSNE, and FL "
            "and normal B cells stayed apart from DLBCL (Figure 4D; marker correlation "
            "{{fig45__4D__L}}, prediction {{fig45__4D__N}} against {{fig45__4D__N_raw}} "
            "without harmonization)."
        ],
    ),
    127: (
        "Figure 4.",
        [
            "Figure 4. Unharmonized data and the recommended approaches for a single sample "
            "type. Each panel shows PCA (first two components, share of variance in "
            "brackets) and tSNE plots coloured by batch (top row) and diagnosis (bottom "
            "row). (A) All {{fig45__4A__n_samples}} samples without batch removal, "
            "imputation or harmonization (S0). (B–D) Unharmonized data and the recommended "
            "approach of the same strategy and imputation: (B) Angel in J (FF only, "
            "softImpute); (C) SVA in K (FFPE only, softImpute); (D) SVA in C (RNA-seq only, "
            "KNN). Marker correlation and cross-batch prediction F1 (unharmonized value in "
            "brackets) are given above the harmonized PCA plot. Embeddings use the genes "
            "without missing values in each matrix ({{fig45__4B__n_genes}} genes for Angel)."
        ],
    ),
    128: (
        "Alt text:",
        [
            "Alt text: Grids of PCA and tSNE plots coloured by batch and by diagnosis. The "
            "unharmonized cohort separates by batch, while Angel on fresh-frozen data, SVA "
            "on FFPE data and SVA on RNA-seq data bring batches of the same diagnosis "
            "together and keep FL, DLBCL and normal B cells apart."
        ],
    ),
    130: (
        "The second-best approach for the RNA-seq-only strategy",
        [
            "With RNA-seq combined with microarrays (Figure 5), FSQN R with KNN in D "
            "(malignant samples only) lowered the share of the first component from "
            "{{fig45__5A__pc1_raw}} % to {{fig45__5A__pc1}} % and brought the two largest "
            "DLBCL batches, RNA-seq FFPE exome capture and the Illumina FFPE array, together "
            "on tSNE, while most Affymetrix batches kept their own clusters (Figure 5A; "
            "marker correlation {{fig45__5A__L}}, DLBCL-versus-FL prediction "
            "{{fig45__5A__N}} against {{fig45__5A__N_raw}}). ComBat without imputation in D "
            "separated FL from DLBCL on PCA and mixed the two Illumina FFPE batches, but most "
            "Affymetrix batches stayed apart on tSNE (Figure 5B; prediction "
            "{{fig45__5B__N}} against {{fig45__5B__N_raw}}). M-ComBat in I (rare batches "
            "removed) kept a large first component ({{fig45__5C__pc1}} % of the variance) "
            "and placed the diagnoses as separate groups of batches (Figure 5C): its "
            "covariate keeps the batch differences that coincide with diagnosis, which the "
            "confounding gradient below makes explicit."
        ],
    ),
    136: (
        "Finally, FSMVN and AMDBNorm methods showed promising results",
        [
            "Supplementary Figures 7–13 show PCA, UMAP and tSNE plots of further "
            "approaches: MNN in S0, H and D (Supplementary Figure 7), SVA (Supplementary "
            "Figure 8) and FSQN R (Supplementary Figure 9) in C with each imputation, MNN "
            "and FSQN R in J (Supplementary Figure 10), SVA in K with each imputation "
            "(Supplementary Figure 11), FSMVN in S0 (Supplementary Figure 12) and AMDBNorm "
            "in K, S0 and J (Supplementary Figure 13). MNN mixed batches but failed the "
            "marker correlation threshold, and SVA without imputation left the fresh-frozen "
            "and FFPE batches of C apart."
        ],
    ),
    138: (
        "Figure 5.",
        [
            "Figure 5. Recommended approaches for RNA-seq combined with microarrays. Each "
            "panel shows the unharmonized data and the harmonized result of the same "
            "strategy and imputation on PCA and tSNE, coloured by batch, diagnosis and "
            "platform: (A) FSQN R in D (malignant samples only, KNN); (B) ComBat in D (no "
            "imputation); (C) M-ComBat in I (rare batches removed, KNN; reference batch "
            "RNA-seq fresh-frozen poly-A). Marker correlation and cross-batch prediction F1 "
            "(DLBCL versus FL in D; unharmonized value in brackets) are given above the "
            "harmonized PCA plot."
        ],
    ),
    139: (
        "Alt text:",
        [
            "Alt text: Grids of PCA and tSNE plots coloured by batch, diagnosis and platform "
            "for FSQN R, ComBat and M-ComBat on RNA-seq combined with microarrays, each next "
            "to the unharmonized data of the same strategy."
        ],
    ),
    # ── Discussion ────────────────────────────────────────────────────────────
    201: (
        "Finally, the overall study design could be improved",
        [
            "Third, the recommendations were tested on held-out cohorts only once per "
            "fold, and for FFPE only the test cohorts were often single batches with one "
            "diagnosis, where covariate methods cannot run. Fourth, confounding limits every "
            "metric: at the confounding of our cohort the scores remain informative, but "
            "when batch and diagnosis coincide no metric can tell them apart, the "
            "unharmonized data rise to the top of the ranking, and the better choice is not "
            "to harmonize. Only M-ComBat ranked above the unharmonized data there, and for "
            "the same reason: a method that models the diagnosis keeps the batch differences "
            "that coincide with it, so its diagnosis retention rises while its batch mixing "
            "falls. A high rank of a covariate method under strong confounding should "
            "therefore be read as a warning sign, not as a recommendation. This is why the rule combines thresholds on marker correlation "
            "and prediction with a visual check, and why strategies that remove "
            "single-diagnosis batches matter."
        ],
    ),
    203: (
        "Clustermap on a full metrics space",
        ["A reduced metric panel and a written selection rule"],
    ),
    204: (
        "The 87-metric × 2,234-approach clustermap",
        [
            "The 2,234-approach × 344-metric evaluation is, to our knowledge, the largest "
            "systematic harmonization matrix reported in bulk transcriptomics. Its redundancy "
            "is large: {{panel_n_panel}} representatives of correlation clusters keep the "
            "structure of the clustermap, equalize metric availability across strategies "
            "and leave the factor hierarchy unchanged. A written rule with thresholds on "
            "independent readouts then turns the scores into a reproducible choice that "
            "others can apply to their own data."
        ],
    ),
    210: (
        "It should be noted that even 87 scoring metrics clustermap",
        [
            "Batch-mixing metrics alone can mislead: MNN mixed batches well but lost the "
            "marker-gene correlation (Supplementary Figure 14A), and under strong "
            "confounding the unharmonized data reached the top ranks (Supplementary Figure "
            "17). Both observations argue for integrated evaluation with thresholds, "
            "held-out validation and expert visual inspection."
        ],
    ),
    # ── Conclusions ───────────────────────────────────────────────────────────
    224: (
        "In the present study we assembled",
        [
            "We assembled a GC B-cell lymphoma cross-platform cohort of 7,174 bulk "
            "transcriptomic profiles and built the ComboBatch pipeline. Under a written "
            "selection rule, SVA was recommended for FFPE-only and RNA-seq-only data, FSQN R "
            "(with FSMVN, ComBat and M-ComBat as alternatives) for RNA-seq combined with "
            "microarrays, and Angel for fresh-frozen data; these methods kept the "
            "differences between FL, DLBCL and normal B cells while mixing batches of the "
            "same diagnosis. Under strong confounding between batch and diagnosis, no "
            "harmonization is the safer choice. The 33 harmonization and 3 imputation "
            "methods are available as the ComboBatch tool with a Docker image containing "
            "all R and Python libraries. We hope that the tool and this real-world benchmark "
            "will serve B-cell lymphoma and cancer transcriptomic biomarker research."
        ],
    ),
}

DELETIONS: dict[int, str] = {
    104: "For 87 of the 344 computed metrics, we manually assigned polarity",
    108: "At the level of harmonization approaches, the clustermap revealed",
    110: "Metrics in the 'NA percentage' cluster showed uniformly",
    112: "We calculated Spearman cross-correlations between all harmonization",
    160: "Biomarker gene correlation before and after harmonization",
    162: "To measure cross-batch prediction quality",
    164: "We then compared biomarker rank concordance",
    166: "We separately investigated prediction quality by RNA batches",
    168: "As a final quality check, we visually investigated DLBCL",
    170: "Taken together, the additional assessment",
    132: "We next visualized and assessed the remaining top-performing approaches",
    134: "For the FFPE only batch removal strategy",
    206: "The practical value of the clustermap-based selection",
    208: "The metric cross-correlation structure",
}

REPLACEMENTS: dict[int, tuple[str, list[tuple[str, str]]]] = {
    67: (
        "Harmonization quality metrics were computed",
        [
            (
                "95% confidence intervals (CI) were assessed for Spearman correlations using "
                "the scipy.stats.bootstrap method, and for R2 values by harmonization "
                "parameter by T-statistic via scipy.stats.t.interval.",
                "Groups were compared by two-sided Mann–Whitney tests with "
                "Benjamini–Hochberg correction.",
            )
        ],
    ),
    90: (
        "The initial step of ComboBatch was prior batch removal",
        [
            (
                "grouped by selection criterion: platform type (RNA-seq only; "
                "Affymetrix-only microarrays, all microarrays), biomaterial (FF-only; "
                "FFPE-only), tumor biology (malignant only), and outlier batch exclusion "
                "(rare batches and those performing poorly in initial FSQN screening;",
                "grouped by selection criterion: no removal (S0); platform type (RNA-seq "
                "only, C; Affymetrix only, G; Affymetrix extended, H; all microarrays, F), "
                "biomaterial (FF only, J; FFPE only, K), tumor biology (malignant only, D), "
                "and outlier batch exclusion (rare batches, I; batches performing poorly in "
                "an initial FSQN screening, A, B and E1–E3;",
            )
        ],
    ),
    # Plain-word method names in the submitted legends of Supplementary Figures 7–13
    243: (
        'Supplementary Figure 11.',
        [
            ('10_mnn harmonized', 'MNN-harmonized'),
            ('01_raw (no harmonization)', 'unharmonized'),
        ],
    ),
    244: (
        'Supplementary Figure 12.',
        [
            ('04_sva harmonized', 'SVA-harmonized'),
            ('01_raw (no harmonization)', 'unharmonized'),
        ],
    ),
    245: (
        'Supplementary Figure 13.',
        [
            ('16_fsqn_r harmonized', 'FSQN R-harmonized'),
            ('01_raw (no harmonization)', 'unharmonized'),
        ],
    ),
    246: (
        'Supplementary Figure 14.',
        [
            ('10_mnn harmonized strict, 16_fsqn_r harmonized strict and 01_raw strict', 'MNN-harmonized, FSQN R-harmonized and unharmonized'),
        ],
    ),
    247: (
        'Supplementary Figure 15.',
        [
            ('04_sva harmonized', 'SVA-harmonized'),
            ('01_raw (no harmonization)', 'unharmonized'),
        ],
    ),
    248: (
        'Supplementary Figure 16.',
        [
            ('harmonized with 13_fsmvn', 'harmonized with FSMVN'),
            ('01_raw (no harmonization)', 'unharmonized'),
        ],
    ),
    249: (
        'Supplementary Figure 17.',
        [
            ('33_amdbnorm harmonized', 'AMDBNorm-harmonized'),
        ],
    ),
    101: ("Best approaches selection", [("Best approaches selection", "Metric panel and clustermap")]),
    117: ("Best approaches", [("Best approaches", "Recommended approaches")]),
    36: (
        "Because most harmonization algorithms process samples jointly",
        [
            (
                "rounds of pipeline refinement (Table 1).",
                "rounds of pipeline refinement (Table 1). Each strategy is named once with "
                "its code (Table 1; S0, no removal; A–K) and by the code afterwards. "
                "Strategies A, B and E1–E3 were "
                "defined from a first, manual FSQN R harmonization: the batches that stayed "
                "apart after it were removed. Diagnosis was partly confounded with batch "
                "in every strategy (Table 1).",
            )
        ],
    ),
    63: (
        "For harmonization quality assessment",
        [
            (
                "computed but not included in the composite scoring",
                "computed but not used for scoring",
            ),
            (
                "metrics (groups L, M, N) were used for the independent assessment of best "
                "approaches but were excluded from the composite scoring",
                "metrics serve as the thresholds of the selection rule (below)",
            ),
        ],
    ),
    84: (
        "The dataset was markedly imbalanced",
        [
            (
                "The dataset was markedly imbalanced with respect to both batch and biology "
                "group composition.",
                "The dataset was markedly imbalanced with respect to both batch and biology "
                "group composition, and diagnosis was partly confounded with batch "
                "(bias-corrected Cramér's V {{cohort_V_batch_diagnosis:.2f}}, adjusted mutual "
                "information {{cohort_AMI_batch_diagnosis:.2f}}; Figure 1E): "
                "{{n_single_dx_batches}} of {{n_batches}} batches "
                "({{pct_samples_single_dx_batches:.1f}} % of samples) held a single "
                "diagnosis, while the other {{n_multi_dx_batches}} connected all batches "
                "through shared diagnoses. Batch explained a median "
                "{{variance_partition_median_R2__batch:.2f}} of the per-gene variance of the "
                "unharmonized data, diagnosis {{variance_partition_median_R2__diagnosis:.2f}}.",
            ),
            ("The distribution of biological groups across batches was more uniform "
             "(Figure 1E): DLBCL", "DLBCL"),
        ],
    ),
    87: (
        "Figure 1.",
        [
            (
                "(E) Bar plot of sample counts by biology and batches, ordered by biology "
                "groups. Batches are color coded according to the A panel color legend.",
                "(E) Sample counts by batch and diagnosis (log scale); single-diagnosis "
                "batches are marked, and Cramér's V and the adjusted mutual information are "
                "given above the panel.",
            )
        ],
    ),
    145: (
        "This ordering has direct practical implications",
        [("both by R2 (Figure 6B)", "both by η² (Figure 6B)")],
    ),
    179: (
        "Notably, post-removal",
        [("(R² < 0.01 in the variance decomposition)", "(η² < 0.01)")],
    ),
    185: (
        "The dataset assembled for this study was markedly imbalanced",
        [
            (
                "The dataset assembled for this study was markedly imbalanced with respect "
                "to both batch and biology group composition (Figure 1D, 1E),",
                "The dataset was imbalanced and partly confounded: {{n_single_dx_batches}} of "
                "{{n_batches}} batches held a single diagnosis and Cramér's V between batch "
                "and diagnosis was {{cohort_V_batch_diagnosis:.2f}} (Figure 1D, 1E),",
            )
        ],
    ),
    189: (
        "Current benchmarking datasets",
        [
            (
                "Our analysis shows that among the 31 harmonization tools analyzed, only SVA "
                "and FSQN R preserved the subtle differences between FL, DLBCL and normal GC "
                "B cells under strong batch effect, both globally and locally, allowing for "
                "transcriptomic biomarkers mining. FSMVN and AMDBNorm showed promising "
                "performance under a specific context of RNA-seq and Illumina microarrays "
                "combined.",
                "Among the 31 harmonization tools analyzed, the selection rule recommended "
                "SVA, FSQN R, FSMVN, ComBat, M-ComBat and Angel, each for a defined dataset "
                "composition, as the methods that mixed batches while keeping the "
                "differences between FL, DLBCL and normal GC B cells.",
            )
        ],
    ),
    194: (
        "The ComboBatch pipeline is conceptually distinct",
        [
            (
                "providing a multi-dimensional evaluation surface rather than relying on a "
                "single metric or a small panel. Additionally, prediction quality and "
                "biomarker correlation metrics are applied as an independent evaluation, "
                "showing that MNN harmonization attained the best performance with the cost "
                "of biologically relevant correlations lost.",
                "reduced to a non-redundant panel and combined with thresholds on marker-gene "
                "correlation and cross-batch prediction in a written selection rule.",
            )
        ],
    ),
    200: (
        "We also acknowledge additional mathematical limitations",
        [
            (
                "First, although the composite score was not a decision criterion, it "
                "averages different metric subsets for different strategies – rendering them "
                "incomparable. Second, six of the 31 analyzed methods were not run on all 14 "
                "strategies, adding another layer of complexity into the comparison logic. "
                "Third, the embedding-space metrics",
                "First, the visual check is a human judgement; we report every rejection and "
                "its reason. Second, six of the 31 analyzed methods were not run on all 14 "
                "strategies, and the embedding-space metrics",
            )
        ],
    ),
    217: (
        "Among the 31 methods analyzed",
        [
            (
                "SVA and FSQN R were the only algorithms that simultaneously resolved FL, "
                "DLBCL, and normal GC B-cell transcriptional differences after cross-platform "
                "integration, with AMDBNorm and FSMVN having a narrower scope of application.",
                "SVA and FSQN R were recommended for the FFPE-only, RNA-seq-only and "
                "multi-platform scenarios.",
            )
        ],
    ),
    255: (
        "Supplementary File 2.",
        [
            (
                "the polarity coefficients, classification and explanation of the 344 "
                "harmonization quality metrics used in this study;",
                "the polarity coefficients, classification and explanation of the 344 "
                "harmonization quality metrics, with their membership in the reduced panel, "
                "correlation cluster and score;",
            )
        ],
    ),
    256: (
        "Supplementary File 3.",
        [
            (
                "Values of the 87 scoring metrics for the 2,407 harmonization approaches "
                "computed in this study; the 2,234 approaches used in the analysis are those "
                "with pct_samples_allNA < 5.",
                "Workbook with three sheets: the 87 scoring metrics, the four scores, the "
                "selection-rule results, method failures and the visual check for the 2,407 "
                "approaches (the 2,234 analysed are those with fewer than 5 % of samples "
                "without any expression value); the runs of the confounding gradient; and the "
                "runs of the leave-cohort-out validation.",
            )
        ],
    ),
}

INSERT_AFTER: dict[int, list[tuple[str | None, str]]] = {
    # Methods: two new subsections after "Harmonization pipeline architecture".
    61: [
        ("Heading2", "Confounding diagnostics and confounding gradient"),
        (
            None,
            "Confounding between batch and diagnosis was measured by the bias-corrected "
            "Cramér's V and the adjusted mutual information, for all samples and for every "
            "strategy (Table 1). We listed single-diagnosis batches and the multi-diagnosis "
            "batches that connect batches through shared diagnoses, and split the per-gene "
            "variance of the unharmonized data into batch, diagnosis and shared parts with "
            "linear models. To measure how confounding changes each score, we built a "
            "confounding gradient on the five batches that hold all three main diagnoses "
            "({{real_data_V__five_batches_n}} samples). Each batch b was assigned one "
            "diagnosis a(b), and its size n_b was the same in every design (at most 150 "
            "samples). The number of samples of diagnosis g in batch b was "
            "n_{b,g}(λ) = n_b · [(1 − λ)/3 + λ · 1{g = a(b)}], rounded by the "
            "largest-remainder method, with λ from 0 to 1 in steps of 0.1 and three random "
            "draws per level. λ = 0 (equal thirds in every batch) is the positive control "
            "and λ = 1 (one diagnosis per batch) the negative control; the "
            "{{n_single_dx_batches}} real single-diagnosis batches form a further negative "
            "control, and one series without the size cap tests the cap. The measured V of "
            "each design is the reported axis. Every design was harmonized by "
            "{{gradient_n_arms}} arms (no harmonization, limma, SVA and ComBat with and "
            "without the diagnosis covariate, MNN, Harmony, FSMVN, FSQN R, quantile "
            "normalization, AMDBNorm, and Angel and M-ComBat, added after the selection rule "
            "recommended them). Lines show the mean of the three replicate draws per level "
            "and bands their standard deviation, not confidence intervals; the slope of "
            "each score on V (linear mixed model with the replicate as random effect, "
            "ordinary least squares when it could not be fitted) is given with its 95 % "
            "confidence interval. A score changed with confounding when its Spearman "
            "correlation with V had a Benjamini–Hochberg false discovery rate below 0.05 "
            "(over every arm and score, 12 scores per arm) and its change from λ = 0 to "
            "λ = 1 (to λ = 0.9 for the arms that cannot run at λ = 1) exceeded twice the "
            "replicate standard deviation.",
        ),
    ],
    65: [
        ("Heading2", "Selection rule and validation"),
        (
            None,
            "The recommended approaches were chosen by a written rule, fixed before it was "
            "applied: (1) the mean per-gene Spearman correlation of 56 marker genes before "
            "and after harmonization had to reach 0.7; (2) an approach that returned its "
            "input unchanged (principal component regression and silhouette values equal "
            "to those of the unharmonized data) was a method failure; (3) the "
            "leave-one-batch-out macro-F1 of diagnosis prediction could not fall more than "
            "0.05 below that of the unharmonized data with the same strategy, imputation and "
            "post-removal, and had to exceed its permutation null (p < 0.05, 100 "
            "permutations; DLBCL versus FL for strategy D); (4) within each scenario of the "
            "decision tree the approaches passing (1)–(3) formed the Pareto front of batch "
            "mixing and diagnosis retention: an approach is on the front when no other "
            "approach is at least as good on both and better on one (DOI: "
            "10.1109/4235.996017). We used the front instead of a weighted sum because the "
            "two axes conflict (removing more batch signal removes diagnosis signal; Figure 6, "
            "gradient panel) and no data justify a weight; the front keeps every best "
            "trade-off instead of one winner. Front members were ordered by local batch "
            "mixing; (5) "
            "every front member was inspected on PCA, UMAP and tSNE next to the "
            "unharmonized data, and rejected when batches of the same diagnosis did not "
            "mix. Approaches that entered the front after a rejection were inspected once; "
            "the front was not recomputed again. Robustness was measured by Kendall's τ-b "
            "against seven variants of the panel and the scores (mean ± SD over the six "
            "scenario pools). For selection bias, the "
            "rule was re-applied without strategies A, B and E1–E3, and in a "
            "leave-cohort-out validation the cohorts of four strategies (J, K, C and S0) "
            "were split into five folds; every method was run "
            "separately on the training cohorts and on the test cohorts, the rule chose a "
            "method on the training part, and its rank among all methods on the test part "
            "was compared with that of a random method. The rank of a method drawn at random "
            "among the n test runs is uniform on 1 to n (mean (n + 1)/2, standard deviation "
            "√((n² − 1)/12)); per scenario, the summed ranks of the chosen methods were "
            "compared with 100,000 Monte Carlo draws of one random rank per fold, and the "
            "number of top-1 and top-3 hits with its exact Poisson-binomial distribution "
            "(probability k/n per fold). The decrease of a method on a score is the best "
            "value among the test runs minus its own value; the decreases of the chosen "
            "methods were compared with those of every test run of the same folds by a "
            "two-sided Mann–Whitney test and by a Monte Carlo test of the mean (100,000 "
            "draws of one run per fold). P-values were corrected by the Benjamini–Hochberg "
            "method within each family (four scenarios; ten hit comparisons; four scores). "
            "Folds whose test part held "
            "one batch or one diagnosis, or where the chosen method failed, were left out of "
            "the rank and decrease tests and counted as misses in the hit test. In the "
            "FFPE-only dataset most "
            "batches hold one cohort, so leaving cohorts out is close to leaving batches "
            "out. Failed runs were recorded, not imputed: ComBat with the diagnosis "
            "covariate and limma cannot run when every batch holds one diagnosis (singular "
            "design), AMDBNorm exceeded the 6-hour limit on the largest inputs, and "
            "exploBATCH could not run in the validation because its R dependency is no "
            "longer available.",
        ),
    ],
    # Discussion: one "real-world benchmark" sentence block after the imbalance paragraph.
    185: [
        (
            None,
            "Rather than homogenize the cohort, we measured the confounding and its effect: "
            "on the five batches of the gradient the real data sit at "
            "V = {{real_data_V__five_batches:.2f}}, where the scores remain informative, "
            "and diagnosis separation recomputed on multi-diagnosis batches only gave nearly "
            "the same ranking (median Kendall τ-b {{bridging_median_tau}}).",
        )
    ],
}

# Table 3 (rebuilt): one row per scenario × method; the cell texts are built by r50 from
# output/wp4/selection_after_visual_check.tsv (numbers read, not typed).
TABLE3_HEADER = [
    "Scenario",
    "Method",
    "Approaches (strategy; imputation; post-removal)",
    "Marker correlation (pass ≥ 0.70)",
    "Cross-batch prediction F1 (unharmonized)",
    "Visual check",
]
TABLE3_SCENARIO_NAMES = {
    "FF only": "FF only",
    "FFPE only": "FFPE only",
    "RNA-seq only": "RNA-seq only",
    "Multi-platform (RNA-seq + microarrays)": "RNA-seq + microarrays",
    "Microarrays only (not a tree leaf)": "Microarrays only (information only)",
    "No batch removal (S0 only)": "No sample removal (information only)",
}
# Plain-word summary of Daniil's visual-check reasons (output/wp4/visual_check.tsv).
TABLE3_VISUAL = {
    ("FF only", "25_angel"): "FL, DLBCL and normal B cells as three clouds; batches of the same diagnosis together",
    ("FFPE only", "04_sva"): "Batches of the same diagnosis mix on PCA, UMAP and tSNE",
    ("RNA-seq only", "04_sva"): "FF and FFPE samples mix",
    ("RNA-seq only", "05_combat"): "Same diagnosis together on PCA, moderately on tSNE",
    ("Multi-platform (RNA-seq + microarrays)", "16_fsqn_r"): "The two large DLBCL batches mix on UMAP and tSNE",
    ("Multi-platform (RNA-seq + microarrays)", "13_fsmvn"): "The two large DLBCL batches mix on UMAP and tSNE",
    ("Multi-platform (RNA-seq + microarrays)", "05_combat"): "FL and DLBCL apart on PCA",
    ("Multi-platform (RNA-seq + microarrays)", "29_combat_ref"): "Diagnoses as separate groups of batches on PCA",
    ("Microarrays only (not a tree leaf)", "25_angel"): "DLBCL batches partly together on UMAP",
    ("No batch removal (S0 only)", "25_angel"): "Same diagnosis overlaps on PCA; batches apart on tSNE",
}

# Table 1: two new columns (values from numbers.json, keys table1_V__<strategy>,
# table1_pct_single_dx__<strategy>); rows are found by the strategy letter code.
TABLE1_HEADERS = ("Cramér's V (batch × diagnosis)", "% samples in single-diagnosis batches")
TABLE1_ROW_STRATEGIES = {
    "S0": "S0_no_removal", "F": "F_microarray_only", "G": "G_affymetrix_only",
    "C": "C_rnaseq_only", "D": "D_malignant_only", "A": "A_confirmed_bad",
    "B": "B_extended_bad", "E1": "E1_iterative_r1", "E2": "E2_iterative_r2",
    "E3": "E3_iterative_r3", "H": "H_affymetrix_extended", "I": "I_rare_batches_removed",
    "K": "K_ffpe_only", "J": "J_ff_only",
}

# Supplementary figure legends (the list after "SUPPLEMENTARY DATA"): old legends that are
# deleted, renumbered or rewritten, and the new legends of S16–S18 (inserted after S15).
SUPP_LEGEND_DELETIONS: dict[int, str] = {
    234: "Supplementary Figure 3.",
    235: "Supplementary Figure 4.",
    240: "Supplementary Figure 8.",
    242: "Supplementary Figure 10.",
}
SUPP_LEGEND_REWRITES: dict[int, tuple[str, list[str]]] = {
    233: (
        "Supplementary Figure 2.",
        [
            "Supplementary Figure 2. Gene expression distributions (log2) of 30 "
            "representative cohorts of the S0 strategy without imputation, with KNN and "
            "with softImpute imputation (one row per mode); each plot shows all samples of "
            "a cohort."
        ],
    ),
    237: (
        "Supplementary Figure 6.",
        [
            "Supplementary Figure 4. Share of approaches with every metric defined, per "
            "strategy and imputation: the reduced panel against all 87 scoring metrics."
        ],
    ),
    238: (
        "Supplementary Figure 7.",
        [
            "Supplementary Figure 5. Spearman correlation between the 87 scoring metrics "
            "(polarity-adjusted, so a positive value means that two metrics agree on which "
            "approach is better) over the 2,234 approaches. Complete-linkage tree on "
            "1 − |ρ|; dashed line, |ρ| = 0.8. Colour bars: membership in the "
            "{{panel_n_panel}}-metric panel (also marked ★), metric group, score bar, "
            "annotation column and metric type."
        ],
    ),
    241: (
        "Supplementary Figure 9.",
        [
            "Supplementary Figure 6. Spearman correlation between the "
            "{{panel_complete_on_panel}} approaches complete on the reduced panel, "
            "annotated by strategy, method and imputation."
        ],
    ),
    250: (
        "Supplementary Figure 18.",
        [
            "Supplementary Figure 14. The thresholds of the selection rule. (A) Marker "
            "correlation (mean per-gene Spearman ρ of 56 marker genes before and after "
            "harmonization) of the 2,234 approaches by method; dashed line, 0.7. (B) "
            "Cross-batch prediction F1 minus that of the unharmonized data, by method; "
            "dashed line, −0.05; colour, above the permutation null or not. (C) SVA and "
            "ComBat with and without the diagnosis covariate along the confounding "
            "gradient: prediction and diagnosis retention (mean ± SD of three replicates)."
        ],
    ),
}
SUPP_LEGEND_ORPHANS: dict[int, str] = {
    # the S7 legend is split over two paragraphs; the second half is deleted with it
    239: "computational group, annotation column and type.",
    251: "before vs after harmonization (metric name mk_rho_mean_all_genes_narrow_set)",
}
SUPP_NEW_LEGENDS_AFTER_S15: list[str] = [
    "Supplementary Figure 16. Robustness of the selection. (A) Kendall τ-b of the ranking, "
    "and overlap (Jaccard index) of the first three and of the Pareto front, between the "
    "reference rule and seven variants of the panel and the scores; bars, mean over the six "
    "scenario pools; error bars, SD; dots, pools. (B) Share of the variants in which each "
    "recommended approach stays on the front.",
    "Supplementary Figure 17. Confounding gradient. (A) Every one of the 14 methods on six "
    "scores against the measured Cramér's V (lines, mean; bands, mean ± SD of three "
    "replicate draws), with the uncapped series and the single-diagnosis batches. (B) Slope "
    "of each score on V with its 95 % confidence interval, filled when the score changes "
    "with confounding by both criteria (to λ = 0.9 for ComBat and M-ComBat with the "
    "diagnosis covariate, which cannot run at λ = 1). (C) Confounding against the best "
    "diagnosis scores of the 14 strategies, coloured as in Figure 2A. (D) Batch mixing "
    "against diagnosis retention (global + local means) at λ = 0, 0.4 and 1; labelled, the "
    "Pareto front. (E) Rank of each method under the selection rule against V (medians over "
    "the three replicates). (F) The recommended methods and the unharmonized data on the "
    "scores of (A), without the controls: (A) shows where the recommended methods sit among "
    "all methods, (F) compares them with each other.",
    "Supplementary Figure 18. Leave-cohort-out validation. (A) Rank on the test cohorts of "
    "the method chosen on the training cohorts (coloured by method) and of a random method "
    "(grey, mean ± SD), per fold; folds without a bar are named; panel titles: Monte Carlo p "
    "and Benjamini–Hochberg false discovery rate (FDR) of the ranks per scenario, and the "
    "number of folds in which the chosen method was first (top-1) or among the first three "
    "(top-3) with the exact Poisson-binomial p, FDR over the ten hit comparisons. (B) "
    "Decrease against the best approach on the test part "
    "(0 = best) for batch mixing and diagnosis retention (global + local means), marker "
    "correlation (local) and cross-batch prediction; bars, mean ± SD of the chosen method "
    "per fold (dots) and of every test run of the same folds; two-sided Mann–Whitney tests, "
    "FDR over the four scores (* < 0.05, ** < 0.01, *** < 0.001, ns not significant).",
]
