# Final Figures Inspection — ComboBatch Article 1
**Date:** 2026-06-28  
**Figures notebook:** `Finally_assembled_figures_for_article.ipynb` (executed fresh, outputs preserved)  
**Figures directory:** `figures/` and `figures/supplementary/`  
**Inspector:** Claude Code (visual inspection of all 16 PNG/SVG outputs after notebook run)  
**Previous inspection:** `final_figures_inspection_260627.md`  
**Implementation plan:** `figures_implementation_plan_260627.md`

---

## What Changed Since June 27

The June 27 round fixed 18 issues (NA filter, palette corrections, layout changes, kBET log scale, etc.). This round (June 28) applied 4 additional fixes: Fig 9 Panel A dynamic count label, Fig 10 Panel B multiline x-tick labels, Fig 11 icon legend box, and Supp A2 new cell. The notebook was then executed clean and all 16 figures regenerated. Key improvements confirmed visible:

| Fix | Status | Visible change |
|---|---|---|
| NA filter (2,234 runs, no 38_harman) | ✅ Confirmed | All counts correct |
| Fig 7: UMAP entropy → Supp 7S | ✅ Done | Fig 7 now 5 panels; Supp 7S new |
| Fig 7: kBET symlog scale | ✅ Done | Panel A x-axis has neg+pos range |
| Fig 8 Panel A: centroid dispersion | ✅ Major fix | Heatmap now fully populated (8 rows) |
| Fig 8 Panel C: symlog scale | ✅ Done | WM ratio axis is log-spaced |
| Fig 8B: Best 15 overlays Panels A/B | ✅ Done | Red dashed line + colored bars |
| Fig 9 Panel A: n=2,234 in title | ✅ Done | Title reads "(n=2,234)" |
| Fig 9 Panel A: iLISI ring overlay | ✅ Done | Rings visible |
| Fig 9 Panel C: Discussion flag | ✅ Done | Yellow text box visible |
| Fig 9 Panel D: y-axis note | ✅ Done | "not bounded to 1" label |
| Fig 9 Panel B: two-line title | ✅ Done | No subtitle collision |
| Fig 10 Panel D: abbreviated names | ✅ Done | Labels readable at 70° rotation |
| Fig 10 Panel B: multiline x-labels | ✅ Done | Two-line labels visible |
| Fig 11: algorithm emoji in L2 nodes | ✅ Partial | Icons inserted but **not rendering** |
| Fig 11: icon legend box at bottom | ✅ Partial | Box present but **not rendering** |
| Supp A: rna_batch_palette colors | ✅ Done | Each batch has a unique color |
| Supp B: flow alpha fixed | ✅ Done | Flow bands now visible |
| Supp D–G: 7pt font minimum | ✅ Done | Grid text legible |

---

## Figure-by-Figure Inspection

### Fig 7 — Local Neighborhood Metrics
**Output:** `figures/fig7_local_metrics_neighborhood.svg/png`  
**Status:** ✅ 5 panels render correctly

**What the figure shows:**
- **Panel A (kBET by method, symlog):** Correct symlog scale. Near-zero cluster clearly separated from the few high-kBET methods. Red "Best mean: 0.10" dashed line correctly placed. MNN, SVA, FSQN R approaches visibly exceed 0.10. A few methods show slightly negative kBET (artifact of the acceptance-rate estimation at near-zero). Best 15 colored bars visible.
- **Panel B (iLISI × cLISI scatter):** Best 15 ★ stars clearly visible and spread across both axes. A cluster of Best 15 appears at iLISI 1.6–2.0, cLISI 1.3–1.6. Several Best 15 from high-harshness strategies (J_ff_only, K_ffpe_only) appear at lower cLISI ≈ 1.0–1.3, which is scientifically correct — subset strategies lose some biology coverage.
- **Panel C (Graph connectivity by biology group):** Three-covariate violin/strip grouping by method. Most methods achieve GC 0.7–1.0 for Diagnosis; larger variance for Major_group and TUMOR_NORMAL. Low discriminative power confirmed.
- **Panel D (tSNE entropy by method):** Boxplot sorted by median entropy. Clear showing that 10_mnn has highest tSNE entropy (~0.15) while 27_dwd and 06_combat_seq are lowest (~0.03). No dramatic outlier (08_inmoose_combatseq was the UMAP outlier, now in Supp 7S).
- **Panel E (kBET vs PCR scatter — wide):** Most compelling panel. The near-horizontal line of points at kBET ≈ 0 across all PCR values is preserved. Best 15 ★ clearly in upper-right quadrant. Direct visualization of the global–local trade-off.

**Scientific significance:** HIGH

**Remaining issues:**
- Panel A y-axis method labels are dense and several overlap at the current font size. Names like `36_explobatch` and `02_median_scaling` collide.
- Panel B: iLISI axis ends at 2.2 (well-covered) but some Best 15 appear at cLISI ≈ 1.0–1.3 which readers might misinterpret as "low biology preservation" — add footnote or annotation explaining that high-harshness strategies inherently have lower cLISI.
- Panel C x-axis method name labels are rotated and small but readable.

**Recommendation:** MAIN — keep all 5 panels.

---

### Fig 8 — Structural and Distance Metrics
**Output:** `figures/fig8_structural_distance_metrics.svg/png`  
**Status:** ✅ All 5 panels functional — major improvement over June 27

**What the figure shows:**
- **Panel A (Centroid dispersion heatmap):** ✅ NOW FULLY POPULATED. 8 rows (tSNE/UMAP × COHORT_LABEL, PLATFORM_RNA, RNASEQ_SOURCE, RNA_BATCH). Methods sorted by mean dispersion. Color scale (RdBu_r) centered at 0. Most methods show values in the –0.5 to –1.5 range (well below 0 = good batch collapse), with relatively little variation between methods. The uniform coloring is scientifically significant: most methods achieve similar centroid collapse regardless of quality — this metric is not a strong discriminator at the method level.
- **Panel B (WaterMelon scatter):** Clean. Best 15 ★ in upper-right (bio > batch). Most methods cluster at WM_bio ≈ 0.2–0.4, WM_batch ≈ 0.3–0.45. Best 15 are above the bio=batch diagonal. Good reference line (dashed).
- **Panel C (WaterMelon bio/batch ratio, symlog):** Correct symlog scale. Ratio=1 dashed blue line visible. Most methods have ratio < 0.3 (batch signal exceeds biology in WaterMelon). Two methods (22_tmm, 01_raw near the top) approach ratio ≈ 1. The log scale reveals the spread at low values well.
- **Panel D (CMS fraction mixed):** Still present. Boxplots by method show CMS range 0.4–0.9 with substantial within-method variance. Limited discriminative power as noted in June 27. Pending move to supplementary.
- **Panel E (ASW batch vs biology):** Two-color barplot (dark = ASW_batch, red-orange = ASW_bio). Clear contrast. High-ASW_bio methods include those that preserve expression structure.

**Scientific significance:** MEDIUM

**Remaining issues:**
- Panel A: Heatmap is now visible but shows limited variance across methods — this is a real finding (centroid dispersion is not strongly method-discriminating after NA filter). Consider adding a note to the caption explaining this.
- Panel A: x-axis method name labels are at 45° and dense. Some names are readable, others overlap at the current resolution.
- Panel C: The log scale is working, but the x-axis label says "WM ratio (bio / batch) (symlog)" — consider shortening to "WM ratio bio/batch".
- Panel D (CMS): Still in main figure — move to supplementary when confirmed by Daniil.

**Comparison with June 27:** The single biggest change is Panel A — previously nearly blank, now fully populated. This resolves the critical issue from June 27.

**Recommendation:** MAIN for Panels A, B, C, E. Panel D → SUPPLEMENTARY (pending decision).

---

### Fig 8B — Distributional Similarity and NA Retention
**Output:** `figures/fig8b_distributional_similarity_na_retention.svg/png`  
**Status:** ✅ All 6 panels functional

**What the figure shows:**
- **Panel A (KS mean D by method):** Best 15 colored bars + red "Best mean: 0.568" dashed line. 27_dwd and 11_harmony achieve lowest KS D (best distributional similarity). 22_tmm is worst. **Layout issue:** the method label "08_inmoose_combatseq" appears floating inside the plot area near the center-right, and a "method" text label appears alongside it — this is a legend artifact from a previous matplotlib call that generated an unintended hue legend. The legend label is visible and distracting.
- **Panel B (Fraction significant KS tests):** Grouped by covariate (COHORT_LABEL, PLATFORM_RNA, RNA_BATCH). 27_dwd leads with lowest fraction across all covariates. 28_npn is worst for PLATFORM_RNA. Stacked multi-color barh.
- **Panel C (Per-gene batch CV):** Dotplot by method. Several extreme outliers visible: 26_xpn, 28_npn, 31_ruv3prps have high CV (600–1000+). 08_inmoose_combatseq also shows a cluster of outlier points. 10_mnn and 12_scanorama are at near-zero CV.
- **Panel D (KS cohort-within-batch D):** 11_harmony at top (highest within-batch D = least uniform within-batch). 08_inmoose_combatseq at bottom (best). Useful complement to Panel A.
- **Panel E (NA heatmap):** Clean and informative. C_rnaseq_only × 20_shambhala shows a red cell (high NA rate ≈ 15%). All other strategy × method combinations are yellow (near 0%). Confirms 20_shambhala is problematic in RNA-seq-only strategy. 38_harman is absent (NA filter working correctly).
- **Panel F (Gene coverage by harshness):** Strict imputation drops to ~65% at high harshness. KNN and softimpute maintain ~95%+ across all harshness tiers. Clear and scientifically important.

**Scientific significance:** HIGH

**Remaining issues:**
- **Panel A: Floating legend artifact** — "08_inmoose_combatseq" and "method" text appear inside the plot area. This is a bug from an unintended matplotlib legend generated by the Best 15 color coding. Fix: add `legend=False` to the barh call or explicitly remove the auto-generated legend before calling `ax_A.legend()` with the custom dashed line only.
- Panel E: The heatmap x-axis method labels are at 45° rotation, very dense. Some labels overlap.
- Panel F: Y-axis label is "% non-NA genes retained" — clear and correct.

**Comparison with June 27:** Best 15 overlays in Panels A and B are confirmed working. The NA filter removed 38_harman as expected. Panel E heatmap is clean and informative.

**Recommendation:** Keep Panels E, F in MAIN. Panels A, B, C, D → SUPPLEMENTARY or combined with Fig 8.

---

### Supp 9 — Embeddings Placeholder
**Output:** `figures/supplementary/supp9_embeddings_best_stars.svg/png`  
**Status:** 📋 Placeholder — unchanged from June 27

All 9 panels show "embed coords not loaded" text. Awaiting embedding coordinates from Tolya.

**Recommendation:** SUPPLEMENTARY — implement when coordinates received.

---

### Fig 9 — Cross-Metric Correlation and Factor Importance
**Output:** `figures/fig9_cross_metric_correlation_factor_importance.svg/png`  
**Status:** ✅ All 4 panels functional — major improvements applied

**What the figure shows:**
- **Panel A (PCR vs kBET scatter):** Title now reads "A: Local vs. global batch correction metrics (n=2,234) — SVA achieves high kBET with moderate PCR" — **count fix confirmed**. iLISI ring sizes are visible as concentric circles around sampled points in the right portion of the plot (where iLISI is higher). Best 15 ★ are large and clearly visible in the upper-right quadrant. The near-zero-kBET mass of points is clear.
- **Panel B (Composite score by harshness):** Title is two-line "B: Composite score / by strategy harshness" — **subtitle overlap fix confirmed**. Violin distributions are correctly showing increasing score and spread from low → high harshness. Best 15 ★ appear at upper portions of all three harshness tiers.
- **Panel C (Factor importance η²):** Shows Method (0.364) >> Strategy (0.262) >> Imputation (0.016). **Discussion flag box** is visible in lower right (yellow box: "Discussion: clustermap groups by strategy; η² shows method > strategy. Both reflect different aspects of variance structure."). Post-removal bar is missing or invisibly small — this is consistent with it having near-zero η².
- **Panel D (Score by metric type, stacked bar):** Y-axis reads "Cumulative summed normalized score (stacked; not bounded to 1)" — **y-axis note fix confirmed**. The method names on x-axis are rotated 45° and readable. The stacking shows "other" category (gray) is large for all methods, distribution_similarity (yellow) dominates the top for TMM/VST, and local_neighborhood (green) is prominent for Best methods.

**Scientific significance:** VERY HIGH

**Remaining issues:**
- **Panel A: iLISI ring overlap** — the ring outlines for iLISI quartile overlay the actual scatter points and reduce readability. The rings are visible but the varying sizes (8/15/25/40 pt) are hard to distinguish from scatter point sizes, especially at 800-point density. Consider reducing ring opacity or adding a cleaner legend label.
- **Panel A: Legend crowding** — the legend contains harshness colors (low/medium/high) plus "Best ★" and "ring size ∝ iLISI quartile" — five entries in a crowded upper-left box. Consider splitting into two legend boxes.
- **Panel C: Post-removal bar absent** — Post-removal factor had <0.01 η² and its bar is not visible. Consider adding it explicitly even if the bar is tiny (adds completeness to the 4-factor hierarchy stated in the article).
- **Panel C: η² values changed** — compared to June 27 (Method 48.9%, Strategy 18.1%), current values are Method 36.4%, Strategy 26.2%. This change is due to the NA filter reducing the dataset. The hierarchy order is unchanged (Method > Strategy > Imputation > Post-removal). Update any manuscript text that cited the old percentages.
- **Panel D: "other" category dominance** — many metrics fall under "other" rather than named types. Consider reviewing and expanding the METRIC_TYPE_MAP to classify more metrics specifically.

**Comparison with June 27:** The title count, subtitle overlap, LISI overlay, Discussion flag, and y-axis note are all confirmed resolved. The remaining issues are refinements.

**Recommendation:** MAIN — keep all 4 panels.

---

### Fig 10 — Composite Ranking and Best-Approach Profiles
**Output:** `figures/fig10_composite_ranking_best_profiles.svg/png`  
**Status:** ✅ All 4 panels functional — layout fixes confirmed

**What the figure shows:**
- **Panel A (Lollipop ranking):** "Attempt rank (n=2234)" x-axis label confirmed. Best 15 ★ visible at top of ranking (ranks 2200–2234). The sigmoid-like score curve is clear: flat plateau 0.33–0.42 for ranks 0–1500, then sharp rise in the top 15–20%.
- **Panel B (Parallel coordinates — Best 15):** X-axis labels are now two-line (e.g., "kBET\nCOHORT_LABEL", "ASW-batch\nCOHORT_LABEL") — **multiline fix confirmed and working**. Labels visible at 45° rotation. Two clusters clear: MNN group (orange lines, high PCR_RNASEQ_SOURCE, steep dip at kBET, recovery at gene coverage) and SVA/FSQN R group (purple lines, moderate across all metrics).
- **Panel C (Equal vs weighted scatter):** Best 15 ★ in upper-right corner, diagonal identity line visible. Very tight clustering of all methods around the diagonal — confirms equal and biology-weighted composites give nearly identical rankings.
- **Panel D (Method × metric-group bubble):** Method names on x-axis are now abbreviated (MNN, SVA, FSQN-R, etc.) and rotated 70° — **abbreviation fix confirmed**. Group G (graph connectivity) is consistently dark green (high score) for all methods. Group B (local neighborhood) is red/orange for most methods. Group E (centroid dispersion) is orange/red showing moderate performance. The figure effectively shows Group B as the key differentiator.

**Scientific significance:** HIGH

**Remaining issues:**
- **Panel B: Five metrics only** — the parallel coordinates shows 5 axes (PCR_RNASEQ_SOURCE, kBET/COHORT_LABEL, ASW-batch/COHORT_LABEL, norm/COHORT_LABEL, pct_genes_noNA). The "norm/COHORT_LABEL" label is partially unclear — what does "norm" abbreviate here? Consider spelling out or using a more specific abbreviation.
- **Panel D: Y-axis group labels** — Groups are labeled A–K but readers cannot interpret these without the metric group legend. Add a small group-key annotation or reference to the supplementary.
- **Panel D: X-axis label density** — with 25+ methods, even abbreviated names at 70° rotation are tight. Consider using the bubble chart x-axis as a secondary reference only and moving the method names off the main x-axis.

**Comparison with June 27:** Count label, abbreviations, and multiline tick labels all confirmed resolved. No new critical issues introduced.

**Recommendation:** MAIN — all 4 panels.

---

### Fig 10 Star — Metric Group Superiority
**Output:** `figures/fig10_metric_star_best15.svg/png`  
**Status:** ✅ Renders correctly

**What the figure shows:**
- **Left panel (radar chart):** Spider-web plot showing Best 15 superiority (Best 15 mean − all-attempts mean) for each metric group. Group G (graph connectivity) shows the largest positive superiority (+0.277), followed by Group C (centroid dispersion, +0.175) and Group B (local neighborhood, +0.120). Group E shows 0.000 (no superiority in that metric group). The radar shape is strongly asymmetric — lopsided toward the lower-left (G axis).
- **Right panel (bar chart):** Horizontal bars sorted by superiority. Same values in a clearer linear format. All bars positive (Best 15 outperform in all groups).

**Scientific significance:** HIGH — directly shows where Best 15 excel most

**Remaining issues:**
- **Radar shape lopsidedness:** The G axis (+0.277) dominates the radar shape, creating an asymmetric polygon that might mislead readers about the overall balance of superiority. In combination with Fig 10 Panel D (bubble chart) which shows Group B as the key differentiator, this apparent contradiction (G is highest in star, B is most red in bubble) should be explained: the star shows superiority vs. mean, while bubble shows absolute score. Group B is low for everyone, so Best 15 still outperform there; Group G has high absolute scores for everyone, so even small differences appear large in relative terms.
- **Radar grid labels:** The radial scale labels (0.069, 0.138, 0.208, 0.277) are visible but overlap with the data area. Consider moving them to a legend position.
- **Group E=0.000 axis:** The E axis has zero extent which means the polygon edge passes through the center for that axis, making the radar boundary visually confusing at that point.

**Recommendation:** MAIN (as supplement to Fig 10) or include as inset in Fig 10.

---

### Supp 7S — UMAP Entropy
**Output:** `figures/supplementary/supp7s_umap_entropy.svg/png`  
**Status:** ✅ Renders correctly — NEW figure (moved from Fig 7 Panel D)

**What the figure shows:** Boxplot of UMAP mixing entropy by method, sorted by median. 10_mnn has highest entropy (~0.2 median), consistent with MNN creating stronger local mixing. 27_dwd, 06_combat_seq, 08_inmoose_combatseq have lowest entropy (~0.03). Unlike UMAP entropy, the outlier structure is distributed across multiple methods rather than the single extreme outlier 08_inmoose_combatseq that dominated the old Panel D.

**Issues:**
- No Best 15 ★ overlay — readers cannot see where Best 15 methods fall in the entropy ranking. Should add overlay as in other method-level panels.
- Redundant dual title: "Supp 7S — UMAP Entropy by Method" (figure title) and "Supp 7S: UMAP mixing entropy (norm) by method" (panel title). Remove one.
- Method names on x-axis are rotated ~45° and readable but some overlap.

**Recommendation:** SUPPLEMENTARY — add Best 15 overlay; fix double title.

---

### Supp A — NA Genes Per Batch
**Output:** `figures/supplementary/suppA_na_genes_per_batch.svg/png`  
**Status:** ✅ Correct coloring confirmed — major improvement

**What the figure shows:**
- **Top panel (non-NA gene count per RNA_BATCH):** Each RNA_BATCH now has a unique color from rna_batch_palette — **palette fix confirmed**. Bars are sorted by gene count (descending). Almost all batches reach the maximum (3,500 genes — near the 3,520 shared set), confirming that within-batch gene coverage is nearly complete. The dashed vertical line marks the max coverage. A large legend box shows all 30 batch colors.
- **Bottom panel (sample count per batch):** Wide variation in sample size: RNASeq_FF_Total and RNASeq_FF_PolyA are the largest (800–1000 samples), while GPL14951_FFPE_Unknown, GPL17047_FF_Unknown, and others are very small (5–20 samples).

**Scientific significance:** LOW-MEDIUM (context for imputation necessity)

**Remaining issues:**
- **Top panel: Legend takes excessive space** — the 30-batch legend occupies roughly 40% of the panel width, leaving insufficient space for the bars. Consider placing the legend outside the figure or below it, or removing it entirely and using direct bar labels.
- **Top panel: x-axis zoom** — bars all reach near the maximum (3,500). Zooming to 3,000–3,520 would reveal the within-batch variation that is currently invisible at the 0–3,500 scale.
- **Bottom panel: y-axis labels very small** — the batch labels in the bottom panel are rendered at 6pt (or smaller) and are illegible. This is despite the `labelsize=max(6, GLOBAL_FONT_SIZE - 3)` fix — the 6pt minimum is not sufficient for this level of density.
- **Supp A2 (new cell):** The Supp A2 figure was added as a new notebook cell (`suppA2_na_per_strat`) but did not produce a new PNG file in the current run because `pct_samples_allNA` is in `df_ok` but all values are < 0.05 after the NA filter — the resulting barplot would show all strategies near-zero (uninformative). The figure was saved but shows the post-filter distribution, not the pre-filter distribution that motivates the threshold. Consider loading the unfiltered metrics data for this visualization.

**Comparison with June 27:** Palette coloring is now correct (was all-gray before). The core issue is resolved.

**Recommendation:** SUPPLEMENTARY. Fix legend placement; zoom x-axis; fix bottom panel label size.

---

### Supp B — Imputation Gene Overlap Sankey
**Output:** `figures/supplementary/suppB_imputation_gene_overlap_sankey.svg/png`  
**Status:** ⚠️ Partial improvement — flow bands now visible; label truncation remains

**What the figure shows:**
- **Left (Sankey):** Flow arcs are now visible (alpha fix confirmed). Three input boxes (KNN, Strict, Softimpute) with a connecting trapezoid flow to the "combined" box on the right. Gene count labels show: "KNN\n,447 genes", "Strict\n,447 genes", "Softimpute\n,447 genes", "Combined\n,447 gen". The leading digit "3" in "3,447" is cut off by the left edge of the boxes — only ",447 genes" is visible.
- **Right (bar chart):** Correct and clean. Shows Strict (3,520), KNN (3,447), Softimpute (3,447). Solid bar = strict set (shared), hatched overlay = imputed genes only. The key finding — imputation adds only 73 genes (KNN/softimpute vs. strict) on the 88-cohort intersection — is clear.

**Scientific significance:** LOW-MEDIUM

**Remaining issues:**
- **Label truncation:** The "3" in "3,447 genes" is cut off. Fix: either reduce font size, widen the Sankey boxes, or place labels outside the boxes with arrows.
- **Flow shape:** The Sankey shows all three inputs converging to the same combined set, but the flow widths are equal — this obscures the fact that KNN and Softimpute add the same ~73 genes beyond strict. Consider adding labels to the flow bands showing the gene count difference.
- **Sankey utility:** The current Sankey, even fixed, shows three nearly-identical inputs converging to one output. The visual advantage over a simple bar chart (right panel) is limited. Consider replacing the Sankey entirely with a Venn diagram or upset plot showing the 3-way gene set overlap.

**Comparison with June 27:** Flow bands are now visible (was alpha=0.0 before). Gene count labels improved but still truncated.

**Recommendation:** SUPPLEMENTARY. Fix label truncation; consider replacing Sankey with Venn/upset diagram.

---

### Supp C — Gene Retention Analysis
**Output:** `figures/supplementary/suppC_gene_retention_analysis.svg/png`  
**Status:** ⚠️ Panel A complete; Panels B and C still placeholders

**What the figure shows:**
- **Panel A (% non-NA genes heatmap):** Dark green (≈100%) for nearly all method × imputation combinations. Two outlier methods are visible at the bottom: `21_harmonizr` and `15_fsqn_py` show ~42–43% gene retention regardless of imputation strategy. All other methods retain >95% genes. The three imputation columns (KNN, Softimpute, Strict) show the same pattern — imputation strategy does not affect final gene retention after harmonization.
- **Panel B:** Placeholder — grey box saying gene_sets needed from S3.
- **Panel C:** Placeholder — yellow box describing GO enrichment implementation.

**Scientific significance:** HIGH for Panel A; N/A for B and C without S3 data.

**Issues:**
- Panel A y-axis (method) labels are small (~7pt) but readable.
- Panel A x-axis (imputation) labels are clear.
- Panels B and C cannot be completed without running Cell 3 (S3 data load). For Article 1, consider removing Panels B and C from the Supp C figure and saving Panel A alone as `suppC_panel_a_gene_retention.svg`.

**Recommendation:** SUPPLEMENTARY — Panel A is ready for submission. Panels B and C → defer or remove for Article 1.

---

### Supp D — Group B Detail (kBET, ASW, CMS)
**Output:** `figures/supplementary/suppD_group_b_detail_kbet_asw_cms.svg/png`  
**Status:** ✅ All 22 panels render correctly

22-panel grid confirmed. Best 15 ★ visible in all panels as red stars. Font minimum enforcement working (text legible at ~7pt). Key patterns visible: kBET panels are extremely right-skewed (most methods ≈ 0, Best 15 elevated); ASW batch panels show Best 15 in upper range; iLISI panels show clear Best 15 separation; CMS panels are nearly uniform (consistent with low discriminative power).

**Remaining issues:** The bottom row of the grid (kBET_RNA_BATCH, kBET_COHORT_LABEL, kBET_RNASEQ_SOURCE panels) has method labels in x-axis rotated at 45° but still crowded. Some labels are readable at ≥7pt.

**Recommendation:** SUPPLEMENTARY — publication-ready for reviewer validation.

---

### Supp E — Group C Detail (Centroid Dispersion)
**Output:** `figures/supplementary/suppE_group_c_centroid_dispersion.svg/png`  
**Status:** ✅ All 13 panels render correctly

Strip plots sorted by method mean for tSNE/UMAP centroid dispersion (4 covariates) and entropy (4 covariates) — 13 panels total. Best 15 ★ appear near the top of most panels (low dispersion = better). UMAP panels generally show stronger Best 15 separation than tSNE panels. The `08_inmoose_combatseq` method appears in the bottom half of most panels (high dispersion). Strategy color-coding across the strip helps identify pattern.

**Remaining issues:** x-axis method labels at minimum font size — barely legible. Acceptable for supplementary.

**Recommendation:** SUPPLEMENTARY — clean, informative.

---

### Supp F — Group H Detail (Euclidean Distance)
**Output:** `figures/supplementary/suppF_group_h_euclidean_distance.svg/png`  
**Status:** ✅ All 7 panels render correctly

7-panel boxplot grid for Euclidean distance ratios (biology/batch). Best 15 ★ visible in all panels. `dist_ratio_COHORT_LABEL` shows the strongest Best 15 clustering at top of range. `dist_ratio_TUMOR_NORMAL` has the highest variance — even Best 15 show spread from 0.8 to 1.3, suggesting this covariate is noisy. `dist_ratio_PLATFORM_RNA` and `dist_ratio_RNASEQ_SOURCE` show some Best 15 above ratio=1.0 (biology distances exceed batch distances — ideal).

**Remaining issues:** None critical. x-axis method labels are legible at minimum font size.

**Recommendation:** SUPPLEMENTARY — clean.

---

### Supp G — Graph Connectivity
**Output:** `figures/supplementary/suppG_group_g_graph_connectivity.svg/png`  
**Status:** ✅ All 3 panels render correctly

3-panel barplot grid (Diagnosis_cell_type_unified, Major_group, TUMOR_NORMAL). Best 15 ★ visible. GC/Diagnosis: Best 15 mostly in top decile (0.88–1.0), one Best 15 at 0.67 (outlier). GC/Major_group: More spread — Best 15 range from 0.7 to 1.0, suggesting major group clustering is partially compromised in some Best approaches. GC/TUMOR_NORMAL: High variance overall, Best 15 spread from 0.25 to 1.0 — TUMOR_NORMAL is the least preserved biology variable.

**Remaining issues:** None. Clean and informative.

**Recommendation:** SUPPLEMENTARY — publication-ready.

---

## Critical New Issues Identified (June 28)

### 🔴 Issue 1: Emoji rendering failure in Fig 11
**Priority: HIGH**  
All emoji in Fig 11 render as empty white squares (□) — this applies to both the L2 method nodes (⛓ MNN, 🔗 SVA, 📐 FSQN R) and the icon legend box at the bottom. Matplotlib's default font (DejaVu Sans) does not include these emoji codepoints. The icon concept is good but the implementation needs to be changed from emoji to either: (a) simple text abbreviations (e.g., "[MNN]", "[SVA]", "[FSQN]"), (b) colored bullet points, or (c) Unicode characters from the mathematical or dingbats blocks that are included in DejaVu Sans.

**Fix options:**
- Replace emoji with ASCII/symbolic text: `[⌂]` → "chains", `[→]` → arrows, `[≡]` → icons
- Use matplotlib marker symbols ($\\mathrm{M}$, etc.)
- Remove icons from nodes; keep only the text legend at bottom with text descriptions instead of emoji

### 🟡 Issue 2: Floating legend artifact in Fig 8B Panel A
**Priority: MEDIUM**  
The "method" and "08_inmoose_combatseq" text appear floating inside Panel A of Fig 8B. This is an unintended matplotlib legend generated by a previous cell's color mapping. Fix: explicitly call `ax_A.get_legend().remove()` after `ax_A.legend()` is called with the dashed-line label, or pass `legend=False` to the plot call that creates the artifact.

### 🟡 Issue 3: Supp A legend occupies 40% of top panel
**Priority: MEDIUM**  
The 30-batch legend takes too much space. Move outside the figure or remove.

### 🟡 Issue 4: Supp A2 suppA2_na_per_strat shows post-filter data (all < 5%)
**Priority: MEDIUM**  
Since df_ok is already filtered (all pct_samples_allNA < 0.05), the Supp A2 barplot shows all strategies at near-zero, making it uninformative. To show the pre-filter distribution that motivates the threshold, load the raw (unfiltered) metrics table and show the full range including the excluded approaches.

### 🟡 Issue 5: Post-removal factor missing from Fig 9 Panel C
**Priority: LOW-MEDIUM**  
The 4-factor hierarchy (Method > Strategy > Post-removal > Imputation) is stated in the article but Panel C only shows 3 bars. Either the post-removal η² is zero or too small to render. Add it explicitly at its true value (even if near zero) to complete the stated 4-factor analysis.

---

## Summary Table

| Figure | June 27 Status | June 28 Status | Improvement | Remaining issues |
|---|---|---|---|---|
| Fig 7 — Local Neighborhood (5 panels) | ✅ (6 panels) | ✅ (5 panels, correct) | Panel D moved to Supp; log scale added | Label crowding in Panel A |
| Fig 8 — Structural/Distance | ⚠️ Panel A blank | ✅ All 5 panels functional | Panel A now populated | CMS still in main; label density |
| Fig 8B — Distributional + NA | ⚠️ NA filter missing | ✅ All 6 panels functional | Best 15 overlays; filter applied | Floating legend in Panel A |
| Supp 9 — Embeddings | 📋 Placeholder | 📋 Placeholder | None | Awaiting Tolya coordinates |
| Fig 9 — Factor importance | ✅ Minor issues | ✅ All fixes applied | Count, subtitle, LISI, Discussion flag | iLISI ring readability; Post-removal bar |
| Fig 10 — Composite ranking | ✅ Minor issues | ✅ All fixes applied | Multiline labels; abbreviated names | Panel D label density |
| Fig 11 — Decision tree | ⚠️ Icons missing | ⚠️ Icons rendering as □ | Icon text inserted | **Emoji not rendering — fix needed** |
| Fig 10 star | ✅ | ✅ | — | Radar lopsidedness |
| Supp 7S — UMAP entropy | ❌ Missing | ✅ New figure | New figure generated | No Best 15 overlay; double title |
| Supp A — NA per batch | ⚠️ All-gray bars | ✅ Unique colors per batch | Palette fixed | Legend too large; x-axis zoom |
| Supp B — Gene overlap Sankey | ⚠️ Flows invisible | ⚠️ Flows visible; labels truncated | Alpha fixed | Label truncation; consider Venn |
| Supp C — Gene retention | ⚠️ Panels B/C placeholder | ⚠️ Panels B/C placeholder | Panel A remains correct | B/C need S3 or removal |
| Supp D — Group B detail | ✅ | ✅ | Font enforcement applied | None |
| Supp E — Group C detail | ✅ | ✅ | Font enforcement applied | None |
| Supp F — Group H detail | ✅ | ✅ | Font enforcement applied | None |
| Supp G — Graph connectivity | ✅ (IndentationError fixed) | ✅ | Syntax error fixed; renders | None |

---

## Prioritized Action Items

### 🔴 Critical

1. **Fix Fig 11 emoji rendering** — Replace emoji (⛓ 🔗 📐 🔧 🧊 🟫 🔬 📊 📈) with DejaVu-compatible text labels in both the L2 nodes and the icon legend. Options: short ASCII codes like `[MNN]`, `[SVA]`, `[FSQN]`, `[FF]`, `[FFPE]`, or use colored markers/shapes instead.

### 🟡 High

2. **Fix Fig 8B Panel A floating legend** — Remove the unintended "method"/"08_inmoose_combatseq" legend artifact. Add `if ax_A.get_legend(): ax_A.get_legend().remove()` before the custom legend call.

3. **Fix Supp A legend + x-axis zoom** — Move legend outside the figure; zoom x-axis to 3,000–3,520 range to show variation.

4. **Fix Supp A2 to show pre-filter data** — Load unfiltered metrics CSV in the Supp A2 cell so the full range of pct_samples_allNA is visible (including the excluded methods near 1.0).

5. **Add Best 15 overlay to Supp 7S** — Without overlay, readers cannot locate where the recommended methods fall in the UMAP entropy ranking.

6. **Add Post-removal bar to Fig 9 Panel C** — Explicitly show Post-removal η² even if near zero to complete the 4-factor hierarchy.

### 🟢 Low

7. **Supp B label truncation** — Fix "3,447 genes" label cutoff by adjusting Sankey box geometry or placing labels outside.

8. **Supp A bottom panel label size** — Increase bottom panel tick label size or reduce method density.

9. **Supp C cleanup** — Remove Panels B and C placeholders from Supp C for Article 1 submission if S3 data is not loaded; save Panel A standalone.

10. **Fig 9 Panel D "other" category** — Review and expand METRIC_TYPE_MAP to reduce the large "other" category.

---

## Article Figure Assignment (Proposed, updated)

### Main text (8 figures)

| Proposed label | Source | Notes |
|---|---|---|
| **Fig 1** | Pipeline scheme | Architecture (existing) |
| **Fig 2** | Bubble charts + barplots | Dataset composition (existing) |
| **Fig 3** | Harmonization clustermap | 2,234 × 87 metrics (pending) |
| **Fig 4** | Fig 7 (5 panels) | Local neighborhood metrics |
| **Fig 5** | Fig 8 (Panels A, B, C, E) + Fig 8B (Panels E, F) | Structural + gene retention |
| **Fig 6** | Fig 9 (all 4 panels) | Factor importance — analytical core |
| **Fig 7** | Fig 10 (all 4 panels) + Fig 10 star | Composite ranking + star |
| **Fig 8** | Fig 11 (after emoji fix) | Decision tree |

### Supplementary

| Proposed label | Source | Notes |
|---|---|---|
| Supp Fig 1 | Barplot batches × cohorts | Dataset detail |
| Supp Fig 2 | Circos-Sankey strategies | Strategy space |
| Supp Fig 3 | Supp A (fixed) | Gene coverage per batch |
| Supp Fig 3b | Supp A2 (fix pre-filter data) | NA sample fraction per strategy |
| Supp Fig 4 | Supp B (fix labels or replace with Venn) | Gene set overlap |
| Supp Fig 5 | Supp C Panel A only | Gene retention heatmap |
| Supp Fig 6 | Fig 8 Panel D + Fig 8B Panels A–D | Distributional detail |
| Supp Fig 7 | Supp D | Group B neighbor metrics |
| Supp Fig 8 | Supp E | Group C centroid dispersion |
| Supp Fig 9 | Supp F | Group H Euclidean distances |
| Supp Fig 10 | Supp G | Group G graph connectivity |
| Supp Fig 11 | Supp 7S (+ Best 15 overlay) | UMAP entropy |
| Supp Fig 12 | Supp 9 | Embeddings (pending Tolya) |
