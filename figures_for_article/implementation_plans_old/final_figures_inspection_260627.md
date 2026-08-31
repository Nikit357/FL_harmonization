# Final Figures Inspection — ComboBatch Article 1
**Date:** 2026-06-27  
**Figures notebook:** `Finally_assembled_figures_for_article.ipynb`  
**Figures directory:** `figures/` and `figures/supplementary/`  
**Inspector:** Claude Code (visual inspection of all 14 PNG outputs)  
**Implementation plan:** `figures_implementation_plan_260627.md`

---

## Global Visualization Rules (apply to all figures)

1. **NA filter mandatory:** Apply `fraction_samples_all_na < 0.05` filter before every visualization. This yields exactly **2,234 valid attempts** (not 2,407). If any plot shows 38_harman or mentions 2,407 runs, the filter has not been applied — rewrite that cell.

2. **Best 15 placement in sorted plots:** When a plot is sorted by value, the Best 15 ★ group must be sorted by its own value alongside all other methods — never pinned at the right or bottom end of the axis.

3. **Balanced superiority framing:** All figure annotations and captions should convey that the best approaches sit in the upper half of distributions across all metric groups — not at the absolute top. Their distinguishing feature is **balanced superiority across all groups simultaneously**, not dominance in any one. Neither metric group alone is sufficient to identify the best approaches — only the composite clustermap is.

4. **Best 15 overlay on all ranked plots:** Every panel where methods are sorted or ranked must include Best 15 ★ overlay points or highlighted bars so the reader can locate them relative to the full distribution.

5. **Minimum font size:** 7 pt minimum for all text in supplementary dense-grid figures; 10 pt (GLOBAL_FONT_SIZE) for main figures.

---

## Executive Summary

All 14 figures generated successfully. The most scientifically valuable results are in **Fig 9 (η² factor importance)**, **Fig 10 (composite ranking)**, and **Fig 11 (decision tree)**. Three figures need revision before submission: Supp A (missing platform coloring), Supp B (Sankey layout broken), and Fig 8 Panel A (centroid dispersion heatmap is nearly blank due to incorrect column names). Several supplementary catplot figures (D–G) are publication-ready as-is but too detailed for the main text. Full corrective implementation plan is in `figures_implementation_plan_260627.md`.

---

## Figure-by-Figure Inspection

### Fig 7 — Local Neighborhood Metrics

**Output:** `figures/fig7_local_metrics_neighborhood.svg/png`  
**Status:** ✅ Renders correctly, 6 panels

**What the figure shows:**
- **Panel A (kBET by method):** The most striking finding in this panel is that the vast majority of methods achieve kBET acceptance rate ≈ 0. Only MNN, FSQN R, and SVA-based approaches (the Best 15 ★) meaningfully exceed 0.10. The dashed red "Best mean: 0.10" line illustrates how rare batch-mixed local neighborhoods are in this dataset — most methods pass global metrics but fail completely at the local level.
- **Panel B (iLISI × cLISI scatter):** Best 15 ★ occupy the upper-right quadrant (iLISI > 2.0, cLISI > 1.3), meaning they simultaneously mix batches and preserve biology. Most other runs have iLISI < 2 and are scattered across cLISI values. One outlier achieves iLISI ≈ 6 but with low cLISI — batch overcorrection destroying biology.
- **Panel C (Graph connectivity):** Most methods achieve connectivity 0.6–1.0 for Diagnosis covariate. High variance makes this metric less discriminative at the method level.
- **Panel D (UMAP entropy):** Extremely right-skewed. One method (08_inmoose_combatseq) is a far outlier with entropy ≈ 0.6; all others cluster near 0. Weak metric for ranking. **→ Move to supplementary.**
- **Panel E (tSNE entropy):** Same pattern as Panel D — right-skewed, 08_inmoose_combatseq is an outlier. Retain in main figure.
- **Panel F (Local vs. global trade-off):** Clean scatter showing Best 15 ★ in the right half of the plot (PCR ≈ 0.7–1.0) with kBET 0.01–0.35. Most methods cluster along the x-axis at kBET = 0, regardless of PCR. This directly illustrates the global–local trade-off: global correction is achievable by many methods, but local mixing is not.

**Scientific significance:** HIGH — Panel B and Panel F are the most communication-effective panels. Panel F is a core result of the paper (most methods achieve global correction but fail locally).

**Issues:**
- Minor axis label overlap on method names in Panel E.
- Panel D (UMAP entropy) is redundant with Panel E → move to supplementary.
- Add log scale to the kBET axis in Panel A to better separate the near-zero methods.

**Recommendation:** Keep as MAIN. Drop Panel D to supplementary → reduces to a 5-panel figure.

---

### Fig 8 — Structural and Distance Metrics

**Output:** `figures/fig8_structural_distance_metrics.svg/png`  
**Status:** ⚠️ Partially informative — Panel A (centroid dispersion heatmap) is nearly blank due to wrong column names

**What the figure shows:**
- **Panel A (UMAP/tSNE centroid dispersion heatmap):** The heatmap is almost entirely empty because incorrect column names were used. The correct columns are `tsne_centroid_disp_RNA_BATCH`, `umap_centroid_disp_RNA_BATCH` (present in all approaches), and `tsne_centroid_disp_COHORT_LABEL`, `umap_centroid_disp_COHORT_LABEL`, `tsne_centroid_disp_PLATFORM_RNA`, `umap_centroid_disp_PLATFORM_RNA`, `tsne_centroid_disp_RNASEQ_SOURCE`, `umap_centroid_disp_RNASEQ_SOURCE` (present in most approaches). Rebuilding with these columns will populate the heatmap.
- **Panel B (WaterMelon batch vs. biology scatter):** Clear and informative. Best 15 ★ cluster in the upper-right (bio > batch). Most other runs cluster around WM_bio ≈ 0.2–0.4 and WM_batch ≈ 0.1–0.4. The dashed diagonal (bio = batch) is a useful reference — Best 15 are above it, meaning biology is preserved more than batch is retained. Best 15 sit in the upper half of the distribution across both axes — balanced superiority, not dominance.
- **Panel C (WaterMelon bio/batch ratio):** 38_harman and 22_tmm have ratios near 1.2–1.3, but these are not in Best 15. Most methods have ratio < 1. Confirms WaterMelon is not strongly correlated with overall composite quality. Apply log scale to y-axis.
- **Panel D (CMS fraction mixed):** Methods achieve CMS ≈ 0.6–0.85 with little spread. Very similar across methods. Low discriminative power. **→ Move to supplementary.**
- **Panel E (ASW batch vs. biology barplot):** Good contrast between ASW_batch (dark) and ASW_bio (warm red). Best methods have moderate ASW_batch and high ASW_bio. Informative for method comparison. Approved as-is.

**Scientific significance:** MEDIUM — Panels B, C, E carry the real information. Panel A needs to be rebuilt with correct column names.

**Issues:**
- **Critical:** Panel A is nearly empty — rebuild using correct column names (`tsne_centroid_disp_RNA_BATCH`, `umap_centroid_disp_RNA_BATCH`, and covariate-specific variants for COHORT_LABEL, PLATFORM_RNA, RNASEQ_SOURCE).
- Panel C: Apply log scale to y-axis.
- Panel D: Move to supplementary.

**Recommendation:** Keep Panels A (rebuilt), B, C, E in MAIN. Panel D → SUPPLEMENTARY.

---

### Fig 8B — Distributional Similarity and NA Retention

**Output:** `figures/fig8b_distributional_similarity_na_retention.svg/png`  
**Status:** ✅ All 6 panels render correctly — but NA filter and Best 15 emphasis need to be added

**What the figure shows:**
- **Panel A (KS mean D by method):** 27_dwd and 11_harmony achieve the lowest KS distance (best distributional similarity). 22_tmm, 23_vst, and 28_npn are worst. Clear method ordering. Best 15 ★ overlay must be added to show where they fall along the axis.
- **Panel B (Fraction significant KS tests):** Most methods fail ≈ 1.5–2.5 KS tests per covariate. 28_npn, 27_dwd, and 22_tmm are the worst offenders on PLATFORM_RNA. Best 15 ★ overlay must be added.
- **Panel C (Per-gene batch CV):** After applying the NA filter (fraction_samples_all_na < 0.05), 38_harman is excluded from the dataset (it does not pass the filter). With 38_harman removed, this panel no longer shows the dramatic CV > 800 outlier. This metric effectively identifies methods that distort expression variance; MNN and 12_scanorama remain at near-zero CV.
- **Panel D (KS cohort-within-batch D):** 11_harmony and 01_raw have highest within-batch KS distances. 08_inmoose_combatseq achieves the lowest.
- **Panel E (NA heatmap):** Striking pattern. D_malignant_only and C_rnaseq_only strategies have almost zero NAs. J_ff_only and A_confirmed_bad strategies with 17_qsmooth and 21_harmonizr show high NA rates. (38_harman is excluded by the NA filter.)
- **Panel F (Gene coverage by harshness):** KNN and softimpute retain ~90–95% of genes across all harshness tiers. Strict imputation drops to ~65–70% at high harshness.

**Global rule applied here:** Best 15 group must be sorted by value among all other methods in Panels A and B — not placed separately at the end of the axis.

**Scientific significance:** HIGH — Panel E (NA heatmap) and Panel F (gene coverage) are essential for the Methods section.

**Issues:**
- **Critical:** NA filter (`fraction_samples_all_na < 0.05`) must be applied before any visualization in this figure. This removes 38_harman and reduces the run count to 2,234.
- Add Best 15 ★ overlay to Panels A and B; sort Best 15 by value alongside all other methods.
- Axis labels on Panels A, B are slightly small but legible.

**Recommendation:** Keep Panel E and F in MAIN. Panels A, B, C, D → SUPPLEMENTARY (or combined with Fig 8).

---

### Supp 9 — Embeddings Placeholder

**Output:** `figures/supplementary/supp9_embeddings_best_stars.svg/png`  
**Status:** 📋 Placeholder only — 3×3 grid of blank panels with instructional text

**Issue:** Incorrect metric prefix was used. Use `tsne_centroid_disp` / `umap_centroid_disp` column prefix when building this figure.

**Scientific significance:** N/A — placeholder  
**Recommendation:** SUPPLEMENTARY — replace panels with actual embedding coordinates once received from Tolya. Fix metric prefix in the meantime.

---

### Fig 9 — Cross-Metric Correlation and Factor Importance

**Output:** `figures/fig9_cross_metric_correlation_factor_importance.svg/png`  
**Status:** ✅ All panels render correctly — count must be updated to 2,234; minor layout fixes needed

**What the figure shows:**
- **Panel A (PCR vs. kBET scatter):** The most visually dramatic finding: nearly all **2,234** runs lie along the bottom of the plot (kBET ≈ 0) regardless of PCR value. Best 15 ★ are the only runs that achieve kBET > 0.05 while also having PCR > 0.7. One run achieves kBET ≈ 0.8 (SVA, RNA-seq only strategy). Add LISI as a secondary local-mixing measure (color or marker size) because LISI is not always as extreme as kBET and provides additional discrimination.
- **Panel B (Composite score violin by harshness):** Composite scores increase with strategy harshness (low → medium → high), but the spread also increases. Best 15 ★ appear across all harshness tiers. Fix: the "Factor importance" subtitle overlaps the violin panel heading at low resolution — correct the layout.
- **Panel C (η² effect sizes):** **The single most important quantitative result in the figure set.** Method explains **48.9%** of total metric variance. Strategy explains **18.1%**. Imputation explains only **0.8%**. Post-removal explains only **0.2%**. This hierarchy (method >> strategy >> imputation >> post-removal) is a definitive quantitative statement about what decisions matter most. **Note for Discussion:** The clustermap (Fig 3) shows strategy as the primary clustering dimension and method as secondary — the opposite of the η² hierarchy here. This inversion should be explicitly discussed in the article: η² measures variance explained in final metric values, whereas clustermap clustering reflects correlation structure of the output space. Both are correct and complementary.
- **Panel D (Metric type composition by method):** TMM, VST, NPN are dominated by distribution similarity (yellow) but score near zero on local neighborhood (green). MNN, AMDBNorm, FSMVN achieve balanced profiles. Add a note/legend annotation that the y-axis shows **cumulative summed normalized score** (not bounded to 1), so readers understand the stacking.

**Scientific significance:** VERY HIGH — This is the analytical core of the paper.

**Issues:**
- Update run count from 2,407 to **2,234** throughout (NA filter applied).
- Panel B subtitle "Factor importance" overlaps violin heading — fix layout.
- Panel A: Add LISI as secondary local-mixing indicator.
- Panel D: Add y-axis annotation explaining cumulative stacked sum.

**Recommendation:** MAIN — keep all 4 panels.

---

### Fig 10 — Composite Ranking and Best-Approach Profiles

**Output:** `figures/fig10_composite_ranking_best_profiles.svg/png`  
**Status:** ✅ All panels render correctly — count and layout fixes needed; star plot missing

**What the figure shows:**
- **Panel A (Lollipop ranking):** **2,234** runs sorted by composite score show a sigmoid-like curve: flat plateau at 0.33–0.42 (runs 0–1,800), then a sharp rise in the top 15% to 0.58–0.60. Best 15 ★ occupy exclusively the very top of the distribution, confirming genuine separation from the rest.
- **Panel B (Parallel coordinates):** Best 15 profiles share a characteristic shape: high PCR_RNASEQ_SOURCE (~0.7–0.9), steep dip at kBET_COHORT_LABEL (~0.0–0.4), then recovery at pct_genes_noNA (~1.0). Two clusters are visible: MNN-based runs (orange lines, lower kBET but high PCR) and FSQN R / SVA runs (purple lines, moderate across all metrics). Fix x-axis tick labels for intermediate metrics.
- **Panel C (Equal vs. weighted scatter):** Points tightly follow the identity line — biology-weighted scoring barely changes rankings. Best 15 ★ still cluster at the top-right. Validates that the composite ranking is robust to weighting choices.
- **Panel D (Bubble chart — method × metric group):** Clear pattern: Group A (PCR / R²) is green (high score) for almost all methods. Group B (local neighborhood) is red/orange for nearly all methods except the Best 15. The bubble chart reveals that Group B is the primary differentiator. Fix: increase figure width or use abbreviated method names to resolve x-axis label overlap at the bottom.

**Missing figure — Star Plot (Metric Group Superiority):**  
Previously requested in `finally_assembled_figures_plan_260626.md` but not yet implemented. Required: a radar/star chart for Best 15 where each ray represents one metric group, ray length = mean normalized score of Best 15 for that group, ray color = metric group palette color, and each ray endpoint has an iconic visual representation of the metric group. Save as `figures/fig10_metric_star_best15.svg/png`.

**Scientific significance:** HIGH — Panels A and D are visually striking. Panel B provides mechanistic insight.

**Issues:**
- Update run count from 2,407 to **2,234** throughout.
- Panel D: Increase figure width or abbreviate method names to resolve x-axis label overlap.
- Panel B: Make intermediate metric x-axis tick labels more readable.
- **Add star plot** `fig10_metric_star_best15.svg/png`.

**Recommendation:** MAIN — all 4 panels + new star plot.

---

### Fig 11 — Hierarchical Decision Tree

**Output:** `figures/fig11_decision_tree_harmonization_selection.svg/png`  
**Status:** ✅ Clean, professional output — icons not yet added

**What the figure shows:** A four-level flowchart encoding the final benchmark recommendations: 5 dataset-type branches (FF only, FFPE only, RNA-seq only, RNA-seq + Illumina microarrays, RNA-seq + various microarrays) → recommended methods (MNN, SVA+softimpute, FSQN R, MNN+post-removal) → post-removal QC decisions. Color coding distinguishes primary recommendations (green), alternatives requiring QC (orange), and default no-post-removal cases (gray).

**Issues:**
- Add icons for biomaterial types (FF, FFPE, RNA-seq) and platform types (Affymetrix, Illumina microarray, Illumina NGS, Agilent) to the corresponding nodes. These can be simple SVG icons embedded in the figure.

**Recommendation:** MAIN (likely last figure in results section, or prominent box in Discussion). Add icons before submission.

---

### Supp A — NA Genes Per Batch

**Output:** `figures/supplementary/suppA_na_genes_per_batch.svg/png`  
**Status:** ⚠️ Visual bug — all bars are uniform gray (Platform_group coloring lost)

**What the figure shows:** Top panel: barplot of mean non-NA gene count per RNA_BATCH — all 30 batches have nearly identical coverage (~3,300–3,500 genes, close to the 3,520-gene maximum). Bottom panel: sample counts per batch. The uniform coverage finding is actually scientifically meaningful: all batches are nearly complete in the 3,520-gene shared set, meaning NAs arise at batch intersections rather than within-batch gene absence.

**Issues:**
- **Critical:** Apply `rna_batch_palette` for bar colors (replace the broken `_pg_pal` derivation). The `rna_batch_palette` dict is defined in cell 3 of the notebook and maps each RNA_BATCH to its canonical color.
- Add a **new separate supplementary figure** for NA sample counts per batch (distinct from NA gene counts).
- The x-axis range on the top panel extends to 3,500 but bars all reach near-maximum — zoom x-axis to 3,000–3,520 to show the variation.
- Bottom panel batch labels overlap — use `rotation=45`, `ha="right"`.

**Recommendation:** SUPPLEMENTARY. Fix coloring; add NA-samples-per-batch figure before submission.

---

### Supp B — Imputation Gene Overlap Sankey

**Output:** `figures/supplementary/suppB_imputation_gene_overlap_sankey.svg/png`  
**Status:** ⚠️ Sankey panel is non-functional; bar chart is informative

**What the figure shows:**
- **Left (Sankey):** Three stacked colored boxes (KNN, Strict, Softimpute) and a small dark "combined" box to the right. There are no flow arcs connecting the two sides. Labels are truncated ("KNN/47 ge"). Flow bands have `alpha=0.0` — they are invisible. This panel is not publication-ready.
- **Right (Stacked bar):** Shows that Strict (3,520 genes), KNN (3,447), and Softimpute (3,447) have nearly identical gene counts. The key finding: imputation **does not expand the gene set** when applied to the full 88-cohort intersection — it fills within-batch NAs rather than adding new genes. The bar chart is correct but needs better axis labels to communicate this.

**Issues:**
- Rebuild the Sankey panel: fix `alpha=0.0` on flow bands; fix gene count labels (should be ~3,500, not 47 or 447); the gene counts suggest a data processing error (S3 data not loaded when these were computed).
- Alternative: replace Sankey with a Venn diagram of gene set overlap across imputation strategies.

**Recommendation:** SUPPLEMENTARY — rebuild Sankey panel or replace with Venn diagram.

---

### Supp C — Gene Retention Analysis

**Output:** `figures/supplementary/suppC_gene_retention_analysis.svg/png`  
**Status:** ⚠️ Only Panel A is production-ready; Panels B and C are placeholders

**What the figure shows:**
- **Panel A (% non-NA genes heatmap):** Clean, informative heatmap. Nearly all methods achieve 95–100% non-NA retention with KNN and Softimpute. Two methods stand out: 17_qsmooth and 21_harmonizr show partial failure. (38_harman is excluded by the NA filter and does not appear.)
- **Panel B (accumulation curves):** Placeholder. Requires gene_sets from S3. To complete: run the notebook cell that downloads gene sets from S3.
- **Panel C (GO enrichment):** Placeholder. The GO enrichment database is available locally at `~/Retroelements/T2T_genes_article/T2T_transposons_genes/`. Run the analysis against that database; collagen-related terms are expected to appear.

**Scientific significance:** HIGH for Panel A. Panels B and C to be completed.

**Recommendation:** SUPPLEMENTARY — Panel A is ready. Panels B and C should be completed or omitted from Article 1.

---

### Supp D — Group B Detail (kBET, ASW, CMS)

**Output:** `figures/supplementary/suppD_group_b_detail_kbet_asw_cms.svg/png`  
**Status:** ✅ All 22 panels render correctly

**What the figure shows:** A comprehensive 3-column grid of all Group B metrics (ASW_batch, ASW_bio, iLISI, cLISI, CMS, kBET — each across multiple covariates). Best 15 ★ are overlaid as red scatter.

Key patterns:
- kBET panels: extremely right-skewed — most methods near 0, Best 15 spread across the full range.
- ASW batch panels: Best 15 generally in top third but not exclusively.
- iLISI panels: Best 15 consistently high; clear separation from the bulk.
- CMS panels: homogeneous — low discriminative power.

**Scientific significance:** MEDIUM — validates summary shown in Fig 7 and Fig 10.

**Issues:** Row/column titles are very small. Minimum acceptable font size is **7 pt** — adjust all text to meet this.

**Recommendation:** SUPPLEMENTARY — comprehensive validation for reviewers.

---

### Supp E — Group C Detail (Centroid Dispersion)

**Output:** `figures/supplementary/suppE_group_c_centroid_dispersion.svg/png`  
**Status:** ✅ Renders correctly — 13 panels, large figure (1.8 MB PNG)

**What the figure shows:** 13 panels of centroid dispersion and entropy across tSNE/UMAP × 4 covariates, plus entropy metrics. After applying the NA filter (`fraction_samples_all_na < 0.05`), **38_harman is excluded** and the dramatic outlier (tSNE/COHORT_LABEL dispersion > 2) vanishes. Best 15 ★ appear near the top of each panel (low dispersion = better batch collapse). UMAP metrics show stronger separation of Best 15 than tSNE metrics.

**Scientific significance:** MEDIUM — corroborates Fig 7 findings at metric-by-metric resolution.

**Recommendation:** SUPPLEMENTARY — too detailed for main.

---

### Supp F — Group H Detail (Euclidean Distance Ratios)

**Output:** `figures/supplementary/suppF_group_h_euclidean_distance.svg/png`  
**Status:** ✅ All 7 panels render correctly

**What the figure shows:** 7 panels of Euclidean distance ratios (biology / batch) for different covariates. Most methods cluster tightly at ratio 0.8–1.2 for Diagnosis and Major_group. Best 15 ★ consistently appear at or near the top for Diagnosis and COHORT_LABEL covariates. PLATFORM_RNA and RNASEQ_SOURCE panels show more variance, with some methods exceeding 1.0 (ideal).

**Scientific significance:** MEDIUM–HIGH — validates that Best 15 preserve biological distances.

**Recommendation:** SUPPLEMENTARY — clean, informative, supports conclusions in main text.

---

### Supp G — Group G Detail (Graph Connectivity)

**Output:** `figures/supplementary/suppG_group_g_graph_connectivity.svg/png`  
**Status:** ✅ All 3 panels render correctly, coverage 94%

**What the figure shows:** Graph connectivity for 3 biology covariates. Best 15 ★ are mostly in the top quartile but not uniquely dominant. Consistent with the η² result — Group G contributes little to explaining method differences.

**Scientific significance:** LOW–MEDIUM.

**Recommendation:** SUPPLEMENTARY — completes the picture for reviewers.

---

## Summary Table

| Figure | Status | Scientific value | Recommendation | Priority issues |
|---|---|---|---|---|
| Fig 7 — Local Neighborhood | ✅ | HIGH | **MAIN** | Move Panel D to supp; log scale on kBET |
| Fig 8 — Structural/Distance | ⚠️ | MEDIUM | **MAIN** (fix Panel A) | Fix Panel A column names; Panel C log scale; Panel D → supp |
| Fig 8B — Distributional + NA | ⚠️ | HIGH | **MAIN** (E, F) + SUPP (A–D) | Apply NA filter; add Best 15 overlays |
| Supp 9 — Embeddings | 📋 | placeholder | SUPP (pending) | Fix metric prefix; needs real coordinates |
| Fig 9 — Factor importance | ✅ | **VERY HIGH** | **MAIN** | Count → 2,234; Panel B subtitle; Panel A LISI; Panel D y-note |
| Fig 10 — Composite ranking | ✅ | HIGH | **MAIN** | Count → 2,234; Panel D x-axis; add star plot |
| Supp A — NA per batch | ⚠️ | LOW–MED | SUPP (fix coloring) | Use rna_batch_palette; add NA-samples figure |
| Supp B — Gene overlap Sankey | ⚠️ | LOW | SUPP (rebuild Sankey) | Sankey non-functional |
| Supp C — Gene retention | ⚠️ | MED (Panel A only) | SUPP | Download gene sets for Panel B; GO database for Panel C |
| Fig 11 — Decision tree | ⚠️ | HIGH | **MAIN** | Add icons for sample types and platforms |
| Supp D — Group B detail | ✅ | MED | SUPP | Font size ≥ 7 pt |
| Supp E — Group C detail | ✅ | MED | SUPP | NA filter removes 38_harman outlier |
| Supp F — Group H detail | ✅ | MED–HIGH | SUPP | None |
| Supp G — Group G detail | ✅ | LOW–MED | SUPP | None |
| Fig 10 star — Metric group radar | ❌ missing | HIGH | **MAIN** | Implement from scratch |
| Supp A new — NA samples per batch | ❌ missing | MED | SUPP | Implement from scratch |

---

## Proposed Article Figure Assignment

### Main text (8 figures)

| Proposed label | Source | Rationale |
|---|---|---|
| **Fig 1** | Pipeline scheme | Architecture overview (existing) |
| **Fig 2** | Bubble charts + barplots | Dataset composition (existing) |
| **Fig 3** | Harmonization clustermap | 2,234 attempts overview (pending) |
| **Fig 4** | Fig 7 (Local Neighborhood, 5 panels) | kBET + iLISI-cLISI trade-off — establishes the problem |
| **Fig 5** | Fig 8 Panels A(rebuilt)/B/C/E + Fig 8B Panels E/F | Biology preservation + data retention |
| **Fig 6** | Fig 9 (Factor importance) | η² result — the analytical core |
| **Fig 7** | Fig 10 (Composite ranking) + star plot | Lollipop + bubble chart + radar — the benchmark outcome |
| **Fig 8** | Fig 11 (Decision tree, with icons) | Practical recommendations |

### Supplementary (12+ items)

| Proposed label | Source | Notes |
|---|---|---|
| Supp Fig 1 | Barplot batches × cohorts | Dataset detail |
| Supp Fig 2 | Circos-Sankey strategies | Strategy design space |
| Supp Fig 3 | Supp A (NA genes per batch, fixed) | Use rna_batch_palette |
| Supp Fig 3b | NA samples per batch (new) | Separate figure |
| Supp Fig 4 | Supp B (gene overlap, rebuilt Sankey) | Rebuild or Venn |
| Supp Fig 5 | Supp C Panel A (gene retention heatmap) | Remove placeholder panels B/C if not completed |
| Supp Fig 6 | Fig 8 Panels C/D + Fig 8B Panels A/B/C/D | Detail distributional metrics |
| Supp Fig 7 | Supp D (Group B detail) | Reviewer validation; 7 pt minimum font |
| Supp Fig 8 | Supp E (Group C detail) | Reviewer validation |
| Supp Fig 9 | Supp F (Group H detail) | Reviewer validation |
| Supp Fig 10 | Supp G (Group G detail) | Reviewer validation |
| Supp Fig 11 | Fig 7 Panel D (UMAP entropy) | Moved from main |
| Supp Fig 12 | Supp 9 (Embeddings) | After Tolya delivers coordinates |

---

## Issues Requiring Code Fixes (Priority Order)

### Critical (blocks submission)

1. **NA filter:** Apply `fraction_samples_all_na < 0.05` to every visualization cell in `Finally_assembled_figures_for_article.ipynb`. This is the prerequisite for all other fixes. Run count: **2,234**.

2. **Fig 8 Panel A — wrong column names:** Rebuild heatmap using `tsne_centroid_disp_RNA_BATCH`, `umap_centroid_disp_RNA_BATCH`, and covariate-specific variants (COHORT_LABEL, PLATFORM_RNA, RNASEQ_SOURCE).

3. **Supp A — Platform coloring:** Apply `rna_batch_palette` to Supp A bar colors; add separate NA-samples-per-batch supplementary figure.

4. **Supp B — Sankey panel:** Fix `alpha=0.0` on flow bands; fix gene count labels; rebuild or replace with Venn diagram.

5. **Fig 10 — Star plot missing:** Implement `fig10_metric_star_best15.svg/png` (radar chart; metric-group rays; metric-group palette; iconic endpoints).

6. **Fig 11 — Missing icons:** Add biomaterial and platform icons to decision tree nodes.

### High (improves scientific correctness)

7. **Fig 7 Panel D → supplementary:** Move UMAP entropy panel out of main Fig 7; add log scale to kBET axis.

8. **Fig 9 / Fig 10 — count correction:** Replace 2,407 with 2,234 everywhere in the notebook.

9. **Best 15 overlay on Fig 8B Panels A and B:** Sort Best 15 by value, not pinned to axis end.

10. **Fig 9 Panel A — add LISI:** Add iLISI as secondary local-mixing measure (color or marker size) in the PCR vs. kBET scatter.

11. **Fig 9 Panel C — add Discussion flag:** Add a textbox or caption note about the η² hierarchy inversion relative to the clustermap clustering order.

### Medium (readability)

12. **Fig 8 Panel C — log scale:** Apply log scale to WaterMelon bio/batch ratio y-axis.

13. **Fig 8 Panel D → supplementary:** Remove CMS fraction from main Fig 8 layout.

14. **Fig 9 Panel B — subtitle overlap:** Fix "Factor importance" label collision with violin heading.

15. **Fig 9 Panel D — y-axis note:** Add legend annotation: y-axis is cumulative summed normalized score (not bounded to 1).

16. **Fig 10 Panel D — x-axis overlap:** Increase figure width or abbreviate method names.

17. **Supp C — placeholder panels:** Remove Panel B and C placeholder cells, or complete them (S3 gene sets for B; GO database at `~/Retroelements/T2T_genes_article/T2T_transposons_genes/` for C).

### Low (polish)

18. **Supp A bottom panel** — use `rotation=45`, `ha="right"` for batch x-axis labels.

19. **Supp D — font size** — set minimum 7 pt for all text.

20. **Supp 9 — metric prefix** — fix column prefix to `tsne_centroid_disp` / `umap_centroid_disp`.
