# 07 — Panel inventory (Phase 2), 2026-09-25

## Status

**Offline work done; Figma placement pending.** 10 figures, 49 lettered panels. Every figure fits the reference frame `637:93145` (756 x 1159 px), has 0 overlapping text boxes by the automated check, and no label is under 6 px. The Figma step needs an authenticated Figma session, which this run does not have; everything it needs is in `figures/for_figma_upload/<figure>/` with the geometry in `figures/figma_layout_260925.md`.

Figure names are working names. Final numbers come from Phase 5, after the text settles the order of first citation.

## Figures

| figure | now | frame px | TEXT nodes | min px | overlaps | comments |
|---|---|---|---|---|---|---|
| `fig_markers_lm` | Figure 4 (classes L, M) | 756 x 1132 | 176 | 10.0 | 0 | C48, C50 |
| `fig_prediction_n` | Figure 5 (class N) | 756 x 840 | 148 | 10.0 | 0 | C16, C50 |
| `fig_election` | new figure: election structure (old Figure 5E-G) | 756 x 860 | 51 | 10.0 | 0 | C50 |
| `sfig_harshness` | Supplementary Figure 12 (harshness), rebuilt | 756 x 940 | 116 | 10.0 | 0 | C44 |
| `sfig_lmn_scatter` | new supplementary: L/M/N scatterplots | 756 x 1080 | 151 | 10.0 | 0 | C48 |
| `sfig_metric_clustermap` | new supplementary: metric cross-correlation clustermap | 756 x 1040 | 35 | 10.0 | 0 | C48 |
| `sfig_expression` | new supplementary: expression, linear vs non-linear (replaces Figure 4A/B and Supplementary Figure 14) | 756 x 1144 | 162 | 10.0 | 0 | C50 |
| `sfig_pca` | new supplementary: per-component PCA (Figure 1C + Supp. Figure 2F) | 756 x 1120 | 115 | 10.0 | 0 | C35 |
| `sfig_marker_qc` | Supplementary Figure 11 (marker panel QC), re-laid out | 750 x 1076 | 288 | 6.17 | n/a | C50 |
| `sfig_gene_method` | Supplementary Figure 13 (gene by method), re-laid out | 750 x 908 | 49 | 6.37 | n/a | C50 |

## Panels

| figure | letter | what it shows |
|---|---|---|
| `fig_markers_lm` | A | class M margin vs class L marker correlation, by method (rho, p: A2_T11) |
| `fig_markers_lm` | B | the same plane by strategy |
| `fig_markers_lm` | C | methods ranked by median margin, clustermap group as its own row |
| `fig_markers_lm` | D | median marker correlation and median margin by strategy and imputation |
| `fig_markers_lm` | E | change in different- vs same-biology agreement; 61 agreement-specific |
| `fig_markers_lm` | F | same-biology agreement unharmonized to harmonized, gate-passing set |
| `fig_prediction_n` | A | methods by median LOBO3 F1, all folds vs multiclass folds; median folds |
| `fig_prediction_n` | B | per-batch F1, both targets, single-class folds hollow: S0_no_removal__softimpute__29_combat_ref__post0 |
| `fig_prediction_n` | C | 3-class fold counts and F1 by classes in the held-out batch |
| `fig_prediction_n` | D | E1 generalizability index vs full-cut F1; no-multiclass approaches apart |
| `fig_election` | A | chord of the nine elected sets; ribbon width = shared approaches (A2_T3b) |
| `fig_election` | B | Venn of the class N, class M and local elected sets |
| `fig_election` | C | supervenn of the N, M, L, global and local elected sets |
| `fig_election` | D | set sizes of all approaches and of the L, M, N and 2+ elected sets, with the part passing the L/M gate |
| `sfig_harshness` | A | marker correlation by harshness tier; Kruskal-Wallis p = 1.4 × 10⁻⁷⁴ |
| `sfig_harshness` | B | marker − HK correlation by harshness tier; Kruskal-Wallis p = 5.5 × 10⁻³¹ |
| `sfig_harshness` | C | same-biology agreement by harshness tier; Kruskal-Wallis p = 4.5 × 10⁻⁶³ |
| `sfig_harshness` | D | different-biology agreement by harshness tier; Kruskal-Wallis p = 2.0 × 10⁻⁴⁷ |
| `sfig_harshness` | E | margin by harshness tier; Kruskal-Wallis p = 1.4 × 10⁻²⁹ |
| `sfig_harshness` | F | margin gain over baseline by harshness tier; Kruskal-Wallis p = 2.3 × 10⁻²⁷ |
| `sfig_harshness` | G | LOBO3 F1, all folds by harshness tier; grey = permutation null (pv_lobo3_f1_macro_perm_mean); Kruskal-Wallis p = 6.1 × 10⁻¹² |
| `sfig_harshness` | H | LOBO3 F1, multiclass folds by harshness tier; Kruskal-Wallis p = 0.0028 |
| `sfig_harshness` | I | LOBO3 AUC by harshness tier; grey = permutation null (pv_lobo3_auc_macro_perm_mean); Kruskal-Wallis p = 0.7 |
| `sfig_harshness` | J | LOBO2 F1, all folds by harshness tier; grey = permutation null (pv_lobo2_f1_macro_perm_mean); Kruskal-Wallis p = 8.2 × 10⁻⁸ |
| `sfig_harshness` | K | LOBO2 F1, multiclass folds by harshness tier; Kruskal-Wallis p = 1.3 × 10⁻⁴ |
| `sfig_harshness` | L | LOBO2 AUC by harshness tier; grey = permutation null (pv_lobo2_auc_macro_perm_mean); Kruskal-Wallis p = 0.48 |
| `sfig_lmn_scatter` | A | LOBO3 F1, all folds vs class L marker correlation, by method; ρ = -0.234, p = 3.2 × 10⁻²⁹ |
| `sfig_lmn_scatter` | B | LOBO3 F1, all folds vs class L marker correlation, by strategy; ρ = -0.234, p = 3.2 × 10⁻²⁹ |
| `sfig_lmn_scatter` | C | LOBO3 F1, all folds vs class M margin, by method; ρ = 0.358, p = 2.3 × 10⁻⁶⁸ |
| `sfig_lmn_scatter` | D | LOBO3 F1, all folds vs class M margin, by strategy; ρ = 0.358, p = 2.3 × 10⁻⁶⁸ |
| `sfig_lmn_scatter` | E | LOBO3 F1, multiclass folds vs class M margin gain over baseline, by method; ρ = 0.127, p = 2.6 × 10⁻⁹ |
| `sfig_lmn_scatter` | F | LOBO3 F1, multiclass folds vs class M margin gain over baseline, by strategy; ρ = 0.127, p = 2.6 × 10⁻⁹ |
| `sfig_metric_clustermap` | A | Spearman clustermap of 325 of the 334 non-metadata metrics (4 constant or sparse over the analysis set, 5 absent from the snapshot); bars: metric group, type, Article 2 class |
| `sfig_expression` | A | 03_limma (linear), S0_no_removal/knn/post0: harmonized vs unharmonized BCL6, IRF4, EEF1A1; 4 largest cohorts |
| `sfig_expression` | B | 05_combat (linear), S0_no_removal/knn/post0: harmonized vs unharmonized BCL6, IRF4, EEF1A1; 4 largest cohorts |
| `sfig_expression` | C | 29_combat_ref (linear), S0_no_removal/knn/post0: harmonized vs unharmonized BCL6, IRF4, EEF1A1; 4 largest cohorts |
| `sfig_expression` | D | 13_fsmvn (linear), S0_no_removal/knn/post0: harmonized vs unharmonized BCL6, IRF4, EEF1A1; 4 largest cohorts |
| `sfig_expression` | E | 16_fsqn_r (non-linear), S0_no_removal/knn/post0: harmonized vs unharmonized BCL6, IRF4, EEF1A1; 4 largest cohorts |
| `sfig_expression` | F | 17_quantile (non-linear), S0_no_removal/knn/post0: harmonized vs unharmonized BCL6, IRF4, EEF1A1; 4 largest cohorts |
| `sfig_expression` | G | 10_mnn (non-linear), S0_no_removal/knn/post0: harmonized vs unharmonized BCL6, IRF4, EEF1A1; 4 largest cohorts |
| `sfig_expression` | H | 12_scanorama (non-linear), S0_no_removal/knn/post0: harmonized vs unharmonized BCL6, IRF4, EEF1A1; 4 largest cohorts |
| `sfig_pca` | A | % of total variance on PC1-PC10 by method, ordered by mean batch PCReg |
| `sfig_pca` | B | RNA_BATCH R² (%) on PC1-PC10 by method |
| `sfig_pca` | C | % of total variance on PC1-PC10 by strategy |
| `sfig_pca` | D | RNA_BATCH R² (%) on PC1-PC10 by strategy |
| `sfig_marker_qc` | A | a2_p15_panel_coverage |
| `sfig_marker_qc` | B | a2_p16_qc_gate |
| `sfig_marker_qc` | C | a2_p17_rho_by_signature |
| `sfig_gene_method` | A | a2_p18_gene_method_clustermap |

## What the text and legends must catch up on (Phase 3)

- **`fig_markers_lm`** — legend of Figure 4 must drop the old A/B scatter grids and re-letter C-G to A-F; old 4F described a panel that was never drawn and is now drawn as D
- **`fig_prediction_n`** — Figure 5 now ends at D; old E-G moved to fig_election; D is on the E1 index
- **`fig_election`** — new figure; text citing Figure 5E-5G must move to it
- **`sfig_harshness`** — 12 letters A-L to cite individually; legend must state the Kruskal-Wallis test and the permutation null
- **`sfig_lmn_scatter`** — new; cite from the harshness 'Taken together' paragraph C48 is anchored to
- **`sfig_metric_clustermap`** — new; legend states 325 of 334 metrics used and why (5 absent, 4 constant or sparse)
- **`sfig_expression`** — replaces Figure 4A/4B and Supplementary Figure 14; text citing those must be repointed
- **`sfig_pca`** — replaces Figure 1C and Supplementary Figure 2F as the place the per-component PCA is discussed; Page 2 frames stay protected
- **`sfig_marker_qc`** — unchanged panels, re-laid out to fit the frame
- **`sfig_gene_method`** — unchanged panel, re-laid out to fit the frame
