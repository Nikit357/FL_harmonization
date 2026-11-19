# Figure files → panels

| file | figure / panel | notebook | status note | slot (mm) |
|---|---|---|---|---|
| fig3_reduced_panel_clustermap.{svg,pdf,png} | Figure 3 (central clustermap, 22-metric panel × 2,234 approaches; missing values black) | nb02_reduced_panel_clustermap.ipynb | G4 (2026-11-07): marks the 22 recommended approaches; named, shaded approach and metric clusters as in the original Figma figure (`output/wp9/nb02_fig3_clusters.tsv`); no submitted-version mark | — |
| figS4_metric_availability.{svg,pdf,png} | Supplementary Figure S4 (old S6): availability, panel vs 87 metrics | nb02_reduced_panel_clustermap.ipynb | final (G1 answered) | — |
| figS5_metric_correlation_clusters.{svg,pdf,png} | Supplementary Figure S5 (old S7): 33-metric \|ρ\| clusters, representatives | nb02_reduced_panel_clustermap.ipynb | final (G1 answered) |
| figS6_approach_correlation.{svg,pdf,png} | Supplementary Figure S6 (old S9): approach × approach ρ on the panel (1,993 complete) | nb02_reduced_panel_clustermap.ipynb | final (G1 answered) | — |
| fig6B_eta_squared.{svg,pdf,png} | Figure 6B: mean η² of the four design factors, reduced panel and all 87 metrics (sensitivity check) | nb03_four_scores_and_tree.ipynb | final (2026-11-07; label "All 87 metrics") | 85 × 50 |
| fig6CD_four_scores.{svg,pdf,png} | Figure 6C/D (replaces the radar): four scores + L + N of every front member after the vetoes, λ = 0 (dashed) / λ = 1 (dotted) gradient medians as lines; prediction = gate value (DLBCL vs FL for D), open marker = unharmonized | nb03 | final selection of 22 (G2b closed 2026-11-07), method colours | 180 × 110 |
| fig6F_decision_tree.{svg,pdf,png} | Figure 6F: decision tree in the layout of the submitted Figma panel (levels 1–5), 4 leaves (multi-platform leaves merged, G4.2), recommended method + alternatives, imputation of the recommended method, checks box | nb03 | data-driven draft; Daniil finishes it in Figma | 180 × 110 |
| figS14a_marker_correlation_gate.{svg,pdf,png} | Supplementary Figure S14 (old S18), panel a: L by method, 0.7 line | nb03 | final | 180 × 85 |
| figS14b_prediction_gate.{svg,pdf,png} | S14 panel b: prediction F1 minus unharmonized F1 by method, −0.05 line, permutation-null colour | nb03 | final | 180 × 85 |
| figS14c_label_leakage.{svg,pdf,png} | S14 panel c: SVA / ComBat with vs without the diagnosis covariate along the gradient | nb03 | final | 180 × 80 |
| fig6_gradient_panel.{svg,pdf,png} | Figure 6, gradient panel: batch mixing and diagnosis retention (global + local means) vs Cramér's V, methods of the 22 selected approaches only (G4.1), real-data V marked | nb04_confounding_gradient.ipynb | final 2026-11-08: SVA, ComBat, FSMVN, FSQN R, Angel, M-ComBat (pod run 2026-11-08) | 95 × 50 |
| figS17a_gradient_scores.{svg,pdf,png} | Supplementary Figure S17a: every arm (14) × 6 scores (3 × 2; fold-change agreement removed 2026-11-08) vs V, band = mean ± SD of 3 replicate draws, uncapped curve, single-diagnosis control | nb04 | final 2026-11-08 | 180 × 125 |
| figS17b_gradient_slopes.{svg,pdf,png} | S17b: slopes vs V with 95 % CI, meaningful filled | nb04 | final | 180 × 55 |
| figS17c_observational_strategies.{svg,pdf,png} | S17c: 14-strategy observational inset (V vs best biology scores), dots in `strat_pal`, code labels without overlap | nb04 | final 2026-11-08 | 180 × 45 |
| figS17d_gradient_scatter.{svg,pdf,png} | S17d (new, approved at G4 review 2026-11-07): batch mixing vs diagnosis retention (global + local means) at λ = 0 / 0.4 / 1, Pareto front labelled | nb04 | final | 180 × 58 |
| figS17e_gradient_rank_trajectories.{svg,pdf,png} | S17e: rank under the selection rule vs V; selected methods with no harmonization as reference and all arms (medians, no bands since 2026-11-08) | nb04 | final 2026-11-08 (14 arms) | 180 × 62 |
| figS17f_selected_methods_scores.{svg,pdf,png} | S17f: six scores of no harmonization + the selected methods vs V | nb04 | final 2026-11-08 (14 arms) | 180 × 105 |
| figS16a_robustness_tau.{svg,pdf,png} | Supplementary Figure S16a: Kendall τ-b, top-3 and front Jaccard by variant as faint bars (mean ± SD over the 6 pools, pool dots) | nb05_robustness_and_v1.ipynb | final 2026-11-08 | 180 × 140 |
| figS16b_front_stability.{svg,pdf,png} | S16b: share of the 8 rankings with each of the 22 selected approaches on the front, method colours | nb05 | final | 180 × 115 |
| figS18a_v1_rank_on_test.{svg,pdf,png} | Supplementary Figure S18a: rank on the test part per fold as bars, chosen (method colour) vs random method (grey, mean ± SD of the uniform rank); failed / not-evaluable folds as text; Monte Carlo p + BH FDR per scenario (`nb05_v1_rank_tests.tsv`); since 2026-11-09 also the top-1 / top-3 hit tests in the titles (former S18b, `nb05_v1_hit_tests.tsv`) | nb05 | final 2026-11-08; half height 2026-11-09 | 180 × 50 |
| figS18b_v1_regret.{svg,pdf,png} | S18b (S18c until 2026-11-09): decrease (formerly "regret") on four scores, chosen (one value per evaluable fold) vs random (every test run), bars mean ± SD, Mann–Whitney + Monte Carlo p, BH FDR (`output/wp9/nb05_v1_regret_tests.tsv`) | nb05 | final 2026-11-08 | 180 × 90 |
| fig4{A,B,C,D}_*.{svg,pdf,png} | Figure 4 (rebuilt 2026-11-08, Daniil B1 option b): A unharmonized S0; B Angel in J; C SVA in K; D SVA in C — unharmonized \| harmonized pairs, PCA + tSNE, rows batch / diagnosis | nb08_figures_4_5.ipynb | final layout; replaces the submitted MNN / SVA panels and dendrograms; numbers in `output/wp9/nb08_figure_4_5_panels.tsv` |
| fig5{A,B,C}_*.{svg,pdf,png} | Figure 5 (rebuilt 2026-11-08): A FSQN R in D; B ComBat in D; C M-ComBat in I — pairs as above, + platform row | nb08_figures_4_5.ipynb | final layout | — |
| fig1E_confounding.{svg,pdf,png} | Figure 1E (new): batch × diagnosis counts (log), single-diagnosis batches marked, diagnoses per batch; V 0.358 / AMI 0.263 in the title | nb01_confounding.ipynb | final (WP1 data); per-cell counts can be switched off (`ANNOTATE_COUNTS`) | — |
| fig2A_strategy_sankey.{svg,pdf,png} | Figure 2A (re-render): strategy map, plain-word labels | nb01_confounding.ipynb | strategy D was already under "By biology" in the submitted panel; only Table 1 needs the fix — Daniil decides whether to swap the panel; a few labels hand-placed | — |
| figS2_merged_distributions.{svg,pdf,png} | Supplementary Figure S2 (merges old S2–S4): per-cohort distributions, no imputation / KNN / softImpute, 30 cohorts | nb06_merged_distributions.ipynb | final layout; mode counts in output/wp9/figS2_cohort_modality.tsv | — |
| g2b_review/<pool>_{pca,umap,tsne}.pdf (6 pools: ff_only, ffpe_only, rna_seq_only, multi_platform_rna_seq_microarrays, microarrays_only_not_a_tree_leaf, no_batch_removal_s0_only) | Gate G2b review (Daniil 2026-11-03): every front member as an unharmonized / harmonized pair, rows batch / diagnosis (+ platform), batches removed by post-removal faint; multi-page PDFs, 3 pairs per page | nb07_selected_approaches_embeddings.ipynb (rewritten 2026-11-03) | review material for vetoes and the leaf assignment; not a publication figure | — |
| picks_*.{svg,pdf} (rows below) | **superseded** by g2b_review/ (first nb07 run, Mac) | — | kept until Daniil deletes them | — |
| picks_ff_only_{pca,umap,tsne}.{svg,pdf} | Gate G2b review; candidate replacement of Figures 4–5 / Supplementary Figures 11–17 only if decision D5 applies (count may not grow) | nb07_selected_approaches_embeddings.ipynb | rule v1 front, 8 members + unharmonized column; PNG previews are local only (git-ignored) | — |
| picks_ffpe_only_{pca,umap,tsne}.{svg,pdf} | same | nb07 | 5 members + unharmonized | — |
| picks_rna_seq_only_{pca,umap,tsne}.{svg,pdf} | same | nb07 | 8 members + unharmonized | — |
| picks_multi_platform__rna_seq___microarrays_{pca,umap,tsne}_p{1,2,3}.{svg,pdf} | same; third row coloured by platform for the leaf assignment (rule step 4c) | nb07 | 12 members on 3 pages, unharmonized column on each page | — |

Strategy labels in every figure are "code · name" ("S0 · No removal", Daniil 2026-11-08; `revision_lib.STRATEGY_DISPLAY_NAMES`).

**Panel slots (D2, 2026-11-08).** Every panel is drawn at its true size on the full figure page:
the Figma frame "Figure 4" (file `t8bFgusleBEwB9ht7rORCH`, node 761-28) is 753 × 1150 px = the
180 × 275 mm text area. Column "slot (mm)" = axes area of the panel file (legends below it add a
few mm; the panels of one page sum to ≤ 275 mm). The notebooks copy the same dict
`PANEL_SLOTS_MM` (nb03–nb05; nb06 uses the page size); fonts 6–8 pt at that size. Slots also in
`output/wp9/figma_page_slots_261108.tsv`. Figure 6 holds unchanged submitted panels too: its slots
are a draft until the Figma assembly. S17 spans two pages (a–c, d–f).

**Review-only files (2026-11-08, not publication figures):** `figS2_merged_distributions_all_cohorts.{svg,pdf,png}`
(all 88 cohorts, nb06 §5b; replaces S2 only if Daniil decides so, D3); `../review_extras/approach_distributions/`
(nb06 §7) and `../review_extras/final_selection_embeddings/` (nb07 `REVIEW_ROUND = "final"`).

**Figma units (2026-11-09, `daniil_review_261109.md`).** Figma imports SVG pt × 4/3 as px; the
figure frame (node 1607-116664) is 756 × 1159 px for the 180 × 275 mm page (4.2 px per mm). Every
notebook draws at those units: text 7.5 pt = 10 px in Figma (S5 row labels 6 px), and the plot
area (without legends and colour bars) is fitted to the slot: the "slot (mm)" column above, else
180 mm wide with its own aspect ratio (1E, 2A, S2, S5, S6), Figure 3 180 × 200 mm, S4 130 × 62 mm,
Figures 4–5 the nb08 slots (square scatters, packed columns, so narrower than 180 mm). Check:
`python r97_figma_check.py` → `output/wp14/figma_check.tsv`.
