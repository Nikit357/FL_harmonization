# Article 2 figure legends and alt text

## Status

**Complete.** Legends and alt text for main Figures 1 to 6 and Supplementary Figures 1 to 14, under the renumbering of the implementation plan: former Extended Figures 1 to 3 become main Figures 1 to 3, former Extended Figures 4 to 13 become Supplementary Figures 1 to 10, and Supplementary Figures 11 to 14 are new. Each entry names the panel source file so the Figma assembly can be checked against it.

**In progress.** None.

**Not started.** Figma frame assembly, which happens in an interactive session and is outside this run. Supplementary table descriptions live in the manuscript back matter.

Main figure legends are duplicated inside `FL_metric_classes_F1000_260917.md` at the point each figure is first cited. This file is the single place that also carries the alt text and the panel-to-file mapping.

---

## Main figures

### Figure 1. Global variance-based metrics across harmonization methods and batch-removal strategies

Source frame: Extended Figure 1 of the source document (Figma node 746:22), renamed.

(A) Biology PCReg against batch PCReg for all 2,234 approaches, coloured by harmonization method, with the 15 clustermap-selected approaches marked by black asterisks. (B) The same plane coloured by batch-removal strategy. (C) Percentage of total variance carried by each of the first ten principal components (left) and the share of it explained by the batch column (right), grouped by method and ordered by mean batch PCReg. The clustermap group appears as one composite row, marked on the harshness colour bar.

**Alt text:** Three panels of global metrics. Two scatter plots place biology principal component regression against batch principal component regression for every approach, one coloured by harmonization method and one by batch-removal strategy. A pair of heat maps beside them shows, for the first ten principal components, how much of the total variance each carries and how much of that variance the batch label explains.

### Figure 2. Local neighbourhood metrics across harmonization methods and batch-removal strategies

Source frame: Extended Figure 2 of the source document (Figma node 746:24), renamed.

(A) Biology cLISI against batch iLISI for all 2,234 approaches, coloured by method; both indices are shown in their un-normalized form. (B) The same plane coloured by strategy. (C) Heat map of tSNE entropy of the batch labels by method and strategy. (D) Heat map of tSNE centroid dispersion of the batch labels over the same grid. Clustermap-selected approaches are marked by black asterisks throughout.

**Alt text:** Four panels of local mixing metrics. Two scatter plots place the biology local inverse Simpson index against the batch local inverse Simpson index, coloured by method and by strategy. Two heat maps below them show tSNE entropy and tSNE centroid dispersion of the batch labels over the same method by strategy grid.

### Figure 3. Distributional convergence, missing values and output scale

Source frame: Extended Figure 3 of the source document (Figma node 746:25), renamed.

(A) Mean between-batch against mean within-batch Kolmogorov-Smirnov D statistic over 1,000 randomly drawn genes, coloured by method. (B) The same plane coloured by strategy. (C) Heat map of the percentage of samples with no missing expression value, by method and strategy. (D) The same heat map for genes. (E) Heat map of the minimum, the 1st, 5th, 25th, 50th, 95th and 99th percentiles, the maximum and the per-gene standard deviation of the output, averaged by method and ordered by mean batch PCReg. (F) The same heat map for the 15 clustermap-selected approaches.

**Alt text:** Six panels. Two scatter plots compare within-batch and between-batch Kolmogorov-Smirnov distances for a fixed set of 1,000 genes, coloured by method and by strategy. Two heat maps give the percentage of samples and of genes that carry no missing value. Two further heat maps summarise the distribution of output expression values by method and for the selected best approaches.

### Figure 4. Marker-gene preservation and cross-batch rank structure, metric classes L and M

Panel sources: `figures/panels_260917/a2_p14_expression_scatter_01_raw` (A); `..._13_fsmvn` (B); `a2_p1_rho_vs_margin` (C); `a2_p2_margin_ranking` (D); `a2_p3_agreement_specific` (E); `a2_p7_strategy_imputation_method` (F); `a2_p12_raw_to_harmonized` (G). The two remaining expression scatters, `..._12_scanorama` and `..._29_combat_ref`, are Supplementary Figure 14.

(A and B) Harmonized against raw expression for the marker panel, one point per sample, faceted by gene and cohort, with the identity line and a per-facet Spearman correlation: (A) the unharmonized baseline 01_raw and (B) 13_fsmvn, selected by the published clustermap. The two further representatives, 12_scanorama elected by class M and 29_combat_ref elected by class N, are drawn on the same axes in Supplementary Figure 14. (C) Class M margin against class L mean marker correlation for all 2,234 approaches, coloured by method, with the 0.75 gate drawn. (D) Methods ranked by median margin, with the clustermap-selected approaches shown as an isolated group. (E) Change in different-biology agreement against change in same-biology agreement, both relative to the unharmonized baseline at the same strategy and imputation; the 61 agreement-specific approaches occupy the lower right quadrant. (F) Median marker correlation and median margin by batch-removal strategy, by imputation and by method. (G) Same-biology agreement before and after harmonization, one line per approach, for the approaches that pass the joint gate.

**Alt text:** Seven panels on marker preservation. Two grids of scatter plots show harmonized against raw expression for panel genes in each cohort, for an unharmonized baseline and for one harmonization method, with an identity line in each facet. A scatter plot places the cross-batch agreement margin against the within-cohort marker correlation, with the correlation gate drawn as a vertical line. A ranking plot orders methods by their median margin. A further scatter plot shows the change in same-biology and different-biology agreement relative to the unharmonized baseline. A grouped summary compares strategies, imputations and methods, and a slope plot links agreement before and after harmonization.

### Figure 5. Cross-batch prediction and the cross-election structure, metric class N

Panel sources: `a2_p4_lobo_ranking` (A); `a2_p5_per_batch` (B); `a2_p6_singleclass_audit` (C); `a2_p8_generalizability_index` (D); `a2_p9_cross_election_circos` (E); `a2_p10_venn_supervenn` (F); `a2_p13_election_sankey` (G).

(A) Methods ranked by median leave-one-batch-out three-class macro F1, with the full cut and the multiclass-only cut drawn side by side and the multiclass fold count beneath each method. (B) Per-batch macro F1 for the leading non-confounded approach, one ridge per batch, ordered by sample count, with single-class folds marked. (C) Fold composition of the analysis set: counts and macro F1 distributions for one-, two- and three-class folds, and the 59 approaches with no multiclass fold. (D) Generalizability index against the full-cut F1, with the approaches carrying no multiclass fold shown in a separate panel. (E) Chord diagram of the cross-election structure: each arc is one metric class, each ribbon is weighted by the number of approaches two classes jointly elect. (F) Venn and supervenn views of the elected sets of the prediction, cross-batch agreement, local, global and distributional classes. (G) Sankey diagram of the raw, gated, elected and validated funnel, from all 2,234 approaches to the approaches that survive every class.

**Alt text:** Seven panels on cross-batch prediction and metric-class agreement. A ranking plot orders methods by leave-one-batch-out macro F1 with both fold cuts side by side. A ridgeline plot gives the per-batch score distribution for the leading approach. A composition panel counts folds by the number of classes they contain. A scatter plot places the combined generalizability index against the prediction score. A chord diagram, a Venn and supervenn pair, and a Sankey flow show how far the sets elected by different metric classes overlap.

### Figure 6. A recipe for selecting metrics when benchmarking harmonization approaches

Panel sources: `figures/recipe_assets_260917/recipe_flow_spine.svg`, `recipe_icon_global.svg`, `recipe_icon_local.svg`, `recipe_icon_distribution.svg`, `recipe_icon_marker.svg`, `recipe_icon_rank.svg`, `recipe_icon_lobo.svg`, `recipe_lobo_scheme.svg`, `recipe_fold_composition.svg`, `recipe_trap_saturation.svg`, `recipe_trap_classcount.svg`, `recipe_trap_confound.svg`.

A block scheme in six steps: declare the metric classes to be computed; compute each class over the full approach set; apply class L as a gate at a stated correlation threshold; rank on the class M margin taken against the unharmonized baseline at the same strategy and imputation; validate by leave-one-batch-out prediction with the projection fitted on training batches only, reported on both fold cuts; and report the elected set of every class together with their intersections. Three named traps are drawn beside the steps they belong to: saturation of the within-cohort correlation under a monotone per-batch transform, agreement without a margin, and a batch variable confounded with the class labels. An inset draws the leave-one-batch-out scheme and the fold-composition census that the two cuts rest on.

**Alt text:** A block diagram of a six-step procedure for benchmarking harmonization approaches, running from declaring metric classes through gating, ranking and held-out validation to reporting every class. Icons mark the metric families. Three call-out boxes name failure modes: a saturated correlation metric, an agreement metric without a margin, and a batch variable confounded with the labels. An inset draws the leave-one-batch-out design and the composition of its folds.

---

## Supplementary figures

### Supplementary Figure 1. Principal component regression by method and by strategy

Was Extended Figure 4. (A) Bars give PCReg for three annotation columns by harmonization method, ordered by batch PCReg, with colour bars beneath for the harshness tier and the quality call. The clustermap-selected approaches are pooled into one composite bar. (B) The same layout for four PCReg columns by batch-removal strategy. Error bars are 95% confidence intervals. Higher values mean that the annotation column explains less of the PCA variation.

**Alt text:** Two grouped bar charts of principal component regression, one by harmonization method and one by batch-removal strategy, each with confidence intervals and with colour bars showing method harshness and an overall quality call.

### Supplementary Figure 2. Global metrics stratified by imputation, strategy and post-removal

Was Extended Figure 5. (A) Box plots of batch PCReg by method, split by imputation, with methods ordered by their mean across all other factors and the clustermap selections set in bold. (B) The same box plots split by batch-removal strategy. (C) The same box plots split by post-removal. (D) Batch PCReg against the batch R^2 of the first principal component, coloured by method. (E) The same plane coloured by strategy. (F) Heat maps of the percentage of variance and of the batch-explained share for the first ten principal components, grouped by strategy.

**Alt text:** Six panels. Three sets of box plots show batch principal component regression by method, split in turn by imputation, by batch-removal strategy and by post-removal. Two scatter plots relate that metric to the batch variance of the first principal component. Two heat maps decompose the variance across the first ten components by strategy.

### Supplementary Figure 3. Further global metrics against principal component regression

Was Extended Figure 6. (A) PCReg for the platform column against PCReg for the batch column. (B) PCReg for the cohort column against the same. (C) Batch DSC against batch PCReg. (D) Platform DSC against batch DSC. (E) Cohort DSC against batch DSC. Panels A to E are coloured by batch-removal strategy. (F) tSNE centroid dispersion against batch PCReg, coloured by strategy. (G) The same plane coloured by method. (H) The same plane coloured by post-removal, with a line joining each pair of approaches that differ only in that step. (I) Average silhouette width against batch PCReg, coloured by strategy. (J) The same plane coloured by method. Clustermap selections are drawn as open black stars in every panel.

**Alt text:** Ten scatter plots comparing global metrics against principal component regression for the batch label: the same metric for the platform and cohort labels, the dispersion separability criterion, average silhouette width and tSNE centroid dispersion, each coloured by strategy or by method, with one panel joining approaches that differ only in the post-removal step.

### Supplementary Figure 4. Local inverse Simpson index by method and by strategy

Was Extended Figure 7. (A) Bars give the index for three annotation columns by method, ordered by the batch index, with harshness and quality colour bars beneath. (B) The same layout for four columns by strategy. Error bars are 95% confidence intervals. (C) Heat map of the batch index clustered by method along the columns and by strategy along the rows, each cell averaged over imputations and post-removal. (D) The same heat map for the biology column. Clustermap selections are marked by black asterisks in C and D.

**Alt text:** Two grouped bar charts of the local inverse Simpson index, by method and by strategy, with confidence intervals, and two heat maps of the same index for the batch label and for the biology label over a method by strategy grid.

### Supplementary Figure 5. A wider set of local mixing metrics

Was Extended Figure 8. (A) Batch LISI against the kBET acceptance rate, coloured by method. (B) The same plane coloured by strategy. (C) Bars give kBET for three annotation columns by method, ordered by the batch value, with harshness and quality colour bars. (D) The same layout by strategy. (E) tSNE entropy against LISI, coloured by method. (F) The same plane coloured by strategy. (G) tSNE entropy against tSNE centroid dispersion, coloured by method. (H) The same plane coloured by strategy. (I) UMAP entropy against tSNE entropy, coloured by method. (J) The same plane coloured by strategy. (K) UMAP centroid dispersion against tSNE centroid dispersion, coloured by method. (L) The same plane coloured by strategy. All metrics are computed on the batch label.

**Alt text:** Twelve panels of local mixing metrics for the batch label: scatter plots relating the local inverse Simpson index, the kBET acceptance rate, tSNE and UMAP entropy and their centroid dispersions, each shown once coloured by method and once by strategy, together with two grouped bar charts of kBET.

### Supplementary Figure 6. kBET and LISI against principal component regression

Was Extended Figure 9. (A) Batch LISI against batch PCReg, coloured by method. (B) The same plane coloured by strategy. (C) Biology LISI against biology PCReg, coloured by method. (D) The same plane coloured by strategy. (E) kBET acceptance rate against batch PCReg, coloured by method. (F) The same plane coloured by strategy. Clustermap selections are drawn as open black stars in every panel.

**Alt text:** Six scatter plots placing local metrics against principal component regression, for the batch label and for the biology label, each coloured once by harmonization method and once by batch-removal strategy.

### Supplementary Figure 7. Distributional, structural and expression-scale metrics

Was Extended Figure 10. (A) Bars give the fraction of pairs with a significant Kolmogorov-Smirnov difference for three annotation columns by method, ordered by the batch value. (B) The same layout by strategy. (C) Biology graph connectivity against platform graph connectivity, coloured by method. (D) The same plane coloured by strategy. (E) Biology distance ratio against batch distance ratio, coloured by method. (F) The same plane coloured by strategy. (G) Biology Watermelon score against batch Watermelon score, coloured by method. (H) The same plane coloured by strategy. (I) Mean Watermelon score over biology columns against the mean over batch columns, coloured by method. (J) The same plane coloured by strategy. (K) Heat map of expression quantiles and the per-gene standard deviation by strategy.

**Alt text:** Eleven panels. Two grouped bar charts give the fraction of cohort pairs whose expression distributions still differ. Eight scatter plots compare graph connectivity, the intra- to inter-group distance ratio and the Watermelon score between biology and batch labels, coloured by method and by strategy. A heat map summarises expression quantiles by strategy.

### Supplementary Figure 8. Metric families across the three method harshness tiers

Was Extended Figure 11. Bars give, for each batch-removal strategy, the value of one metric in each harshness tier: (A) batch PCReg, (B) biology PCReg, (C) batch tSNE entropy, (D) batch LISI, (E) biology LISI, (F) batch KS fraction significant. Strategies are ordered by the metric shown, and the clustermap-selected approaches are drawn as an additional pseudo-strategy.

**Alt text:** Six grouped bar charts, one per metric, comparing low, medium and high harshness harmonization methods within each batch-removal strategy.

### Supplementary Figure 9. Composition of the equally weighted composite score

Was Extended Figure 12. Stacked bars give the contribution of each component to the composite: (A) metric type by strategy, (B) metric type by method, (C) metric computational group by strategy, (D) metric computational group by method, (E) annotation column by strategy, (F) annotation column by method. Bars are ordered by the total, descending.

**Alt text:** Six stacked bar charts decomposing the composite score by metric type, by metric computational group and by annotation column, each shown once across batch-removal strategies and once across harmonization methods.

### Supplementary Figure 10. All approaches ordered by the composite score

Was Extended Figure 13. Every approach is drawn as one point, ordered by its composite score, with colour bars beneath giving its harshness tier, batch-removal strategy, imputation, harmonization method and post-removal setting. The clustermap selections are marked by black stars.

**Alt text:** A single ordered curve of composite scores for every harmonization approach, with parallel colour bars showing the harshness tier, strategy, imputation, method and post-removal setting of each point.

### Supplementary Figure 11. Marker panel coverage and per-gene quality

New. Panel sources: `a2_p15_panel_coverage`, `a2_p16_qc_gate`, `a2_p17_rho_by_signature`. (A) Fraction of the 633-gene panel retained by each approach, by strategy and imputation. (B) Effect of the per-gene quality gates on the panel, from the full panel down to the 56-gene subset. (C) Distribution of the within-cohort marker correlation by signature of origin.

**Alt text:** Three panels describing the marker panel: how much of it each approach retains, how the per-gene quality gates reduce it to a smaller subset, and how the within-cohort correlation is distributed across the signatures the genes were drawn from.

### Supplementary Figure 12. Metric classes L, M and N across the three method harshness tiers

New. Panel source: `a2_p11_harshness_lmn`. One panel per metric, giving the distribution within the low, medium and high harshness tiers for the mean marker correlation, the marker-minus-housekeeping contrast, cross-batch rank agreement, the margin, the full-cut and multiclass-only leave-one-batch-out three-class macro F1 and the two-class AUC. Each panel carries its own Kruskal-Wallis statistic, its p value and the number of approaches contributing to each tier, which differs between metrics.

**Alt text:** A row of distribution plots, one per biology-facing metric, comparing low, medium and high harshness harmonization methods, each annotated with a Kruskal-Wallis test and the number of approaches in each tier.

### Supplementary Figure 13. Gene by method structure of the marker correlations

New. Panel source: `a2_p18_gene_method_clustermap`. Clustermap of the within-cohort correlation of each panel gene, genes along one axis and harmonization methods along the other, with genes annotated by their signature of origin and methods by their harshness tier.

**Alt text:** A clustered heat map of within-cohort marker correlations, with panel genes on one axis and harmonization methods on the other, annotated by signature of origin and by method harshness.

### Supplementary Figure 14. Marker expression under the two remaining best-approach representatives

New. Panel sources: `figures/panels_260917/a2_p14_expression_scatter_12_scanorama` (A); `..._29_combat_ref` (B). Harmonized against raw expression for the marker panel on the axes of Figure 4A and 4B, one point per sample, faceted by gene and cohort, with the identity line and a per-facet Spearman correlation: (A) 12_scanorama, elected by class M, which returns a cloud with no relation to the input, and (B) 29_combat_ref, elected by class N, which shifts the cohorts onto a common scale while keeping the within-cohort spread.

**Alt text:** Two grids of scatter plots showing harmonized against raw expression for panel genes in each cohort, with an identity line in each facet, for the method elected by the cross-batch agreement class and the method elected by the prediction class.
