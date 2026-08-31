# Harmonization Metrics Analysis Notebook — Overview
**Date:** 2026-05-17  
**Author of overview:** Claude Code review  
**Notebook:** `harmonization_metrics_analysis.ipynb`  
**Kernel:** `collagen_3_11` (Python 3.11)  
**Based on implementation plans:** `metrics_notebook_plan.md`, `metrics_notebook_plan_2.md`, `metrics_notebook_plan_3.md`

---

## 1. Purpose

This notebook is the central analysis workbench for evaluating multi-platform RNA expression harmonization strategies in the FL (Follicular Lymphoma) dissertation project. It answers three questions:

1. **Which harmonization method best removes batch effects while preserving biological signal?** (Part 1 — Metrics Analysis)
2. **How many and which genes are retained under different data preparation strategies?** (Part 2 — Gene Sets Analysis)
3. **Which FL-specific marker genes are at risk of being lost, and are the lost genes biologically important?** (Part 2 — FL Gene Retention)

---

## 2. Input Data

### Primary metrics table
- **File:** `metrics_comprehensive_260513.csv` (referenced in Cell 003; physically located in `metric_tables/` subdirectory)
- **Shape:** 1,640 rows × 205 columns
- **Rows:** all have `status == "ok"`; no failed rows in the current dataset
- **Dimensions of the benchmark:**
  - 11 removal strategies: `S0_no_removal`, `A_confirmed_bad`, `B_extended_bad`, `C_rnaseq_only`, `D_malignant_only`, `E1_iterative_r1`, `E2_iterative_r2`, `E3_iterative_r3`, `F_microarray_only`, `G_affymetrix_only`, `H_affymetrix_extended`
  - 3 imputation approaches: `strict`, `knn`, `softimpute`
  - 32 normalization methods: `01_raw` through `38_harman` (see §3 detail below)
  - 2 post-removal variants: `post_rm=False` (post0) and `post_rm=True` (post1)
- **Metric columns:** 199 numeric columns grouped into 8 groups (A–H) plus two added groups (J = PC variance %, K = NA retention)
- **Key metric ranges (across all 1,640 OK rows):**
  - `r2_RNA_BATCH`: 0.0–0.744 (lower = better; raw baseline ~95%)
  - `kbet_acceptance_rate_RNA_BATCH`: 0.0–0.867 (higher = better)
  - `n_genes`: 177–15,885

### Gene list files (Part 2)
- Per-harmonization JSON files on S3 under `FL_batch_correction/genes/`
- Format: `{strat}__{imp}__{method}__{post_rm_tag}_genes.json`
- Each file contains a list of gene symbols present after that data preparation step

---

## 3. Notebook Structure — Cell-by-Cell Walkthrough

**Total:** 161 cells — 118 code cells, 43 markdown cells.  
**Figures produced:** 247 files in `figures/` (SVG + PNG + PDF dual-format for all key figures).

---

### Part 1 — Metrics Analysis

#### §1 — Setup, Imports, and Data Loading (Cells 000–025)

**Cell 000 (markdown):** Title and part structure.

**Cell 001 — Imports and global constants:**
Sets up all Python libraries and establishes the global font size system:
```
FONT_BASE = 14   → FONT_TITLE, FONT_LABEL, FONT_TICK, FONT_LEGEND, FONT_ANNOT, FONT_SMALL, FONT_TINY
```
All downstream plot calls use these constants explicitly rather than hardcoded numbers. Changing `FONT_BASE` rescales all text globally — the key design choice from Plan 3 Feature 2. Also sets `FIGURES_DIR = Path("figures")` and S3 coordinates.

**Cell 003 — Load metrics CSV:**
- Loads `metrics_comprehensive_260513.csv`
- Constructs `run_id` as `strat__imp__method__post{0|1}` and sets as index
- Defines `META_COLS = ["strat","imp","method","post_rm","status","compute_time_s"]`
- Filters to `df_ok = df[df.status == "ok"]`
- Prints summary: total/OK/failed counts, lists of unique strats, imps, methods, post_rm values

**Cell 005 — Column taxonomy:**
Defines `GROUP_MAP` (metric group classification A–H) and `ANNOT_COLS_ORDER` (8 annotation columns in order of specificity). Implements `classify_metric_col(col)` function with a NumPy-style docstring. Also defines the coarse `METRIC_TYPE_MAP` with four types:
- `local_neighborhood`: kBET, iLISI, cLISI, graph connectivity, UMAP/tSNE entropy
- `global_distance`: R², PCR, DSC, centroid dispersion, dist_ratio, ASW, CMS
- `distribution_similarity`: KS tests, per-gene batch CV
- `other`: data quality descriptives, variancePartition, NA-related

Builds `col_meta` DataFrame (columns: `group`, `annot_col`, `metric_type`) for all metric columns. Excludes: raw ASW without normalization, r2_pc*, DSC p-values, and cohort count columns.

**Cell 007 — Polarity assignment:**
Assigns `POLARITY[c] ∈ {+1, -1, 0}` to every metric column with a full comment block explaining the biological rationale for each group (see plan notes). Key conventions:
- Group A (R², PCR, DSC): `-1` (lower = less batch variance = better)
- Group B (kBET, iLISI, CMS, ASW_bio_norm): `+1` (higher = better mixing/biology)
- Group B (ASW_batch_norm): `+1` (higher = better batch mixing after normalization)
- Group C (entropy): `+1`; centroid_disp: `-1`
- Group D (KS, per-gene CV): `-1`
- Group E (n_genes, n_samples, bimodality): `+1`; zero-inflated bimodality: `+1`; descriptive: `0`
- Group F (variancePartition): `-1` for batch columns, `+1` for biology columns
- Group G (graph connectivity): `+1`
- Group H (dist_ratio): `-1` for biology columns (tighter = better), `+1` for batch columns (more mixed = better)

**Cell 009 — Manual polarity overrides (`POLARITY_MANUAL`):**
~40 explicit overrides where the automatic logic is wrong, covering: ASW batch/bio columns with non-RNA_BATCH suffix, avg_intra/inter_dist (set to 0 — scale-dependent), dist_ratio direction by batch vs biology, bimodality variants, cms_mean (descriptive only), and all `exp_*` statistics.

**Cell 011 — Normalization functions:**
Three normalization variants, all with NumPy-style docstrings:
1. `normalize_for_display`: NaN→median fill → MinMax scaling → polarity flip (primary function used in scoring and clustermaps)
2. `normalize_for_display_with_dropna`: drops rows with fewer than 36 non-NaN values, fills remaining NaN with 0 (used for drop-NA clustermaps)
3. `dropna_for_display_no_normalization`: no scaling, just NaN handling (for raw value clustermaps)

**Cell 013 — Normalization validation:**
Shape check, value range [0,1] assertion, NaN count report for `df_normed`.

**Cell 015 — `plot_multilevel_comparison` helper:**
Two-panel figure function: top panel = boxplot + jittered strip per group, bottom panel = −log₁₀(FDR) pairwise Mann-Whitney heatmap (BH correction). Auto-detects palette from `group_col` (method→method_pal, strat→strat_pal, imp→imp_pal). Also defines `cluster_strip_box_plot` variant for catplot-style use.

**Cells 017–025 — Palette construction and visualization:**
Seven palettes defined with documented rationale:
- `strat_pal`: manually tuned pastels (one per strategy)
- `imp_pal`: `{'strict': '#2979ae', 'knn': '#982d22', 'softimpute': '#713689'}` — dark and vivid, manually set, never changed
- `method_pal`: tab20 + tab20b (32 colors) with +0.15 saturation boost via HSV
- `post_rm_pal`: `{False: '#CCCCCC', True: '#333333'}` neutral grayscale
- `group_pal`: Set1 (bold primary colors for A–H)
- `annot_pal`: sepia scale for batch columns (RNA_BATCH, PLATFORM_RNA, RNASEQ_SOURCE, COHORT_LABEL), cool teal/slate scale for biology (Major_group, Diagnosis_cell_type_unified, TUMOR_NORMAL), gray for `global/all`
- `metric_large_type_pal`: `{local_neighborhood: '#1a6b3c', global_distance: '#8b4a0f', distribution_similarity: '#0d5c63', other: '#5c5c1a'}` — dark, avoids blue/red/purple used in imp_pal

Two key DataFrame objects built here, named to eliminate the long-standing row_colors/col_colors confusion:
- `attempt_colors`: indexed by `run_id`; columns = strat, imp, method, post_rm (per-attempt annotations)
- `metric_colors`: indexed by metric name; columns = group, annot_col, metric_type (per-metric annotations)

Helper functions: `_safe_map`, `make_legend_patches`, `add_legend_outside`, `clustermap_std`, `strip_box_plot`.

`plot_palette` calls visualize all palettes as swatches for quick review.

---

#### §2 — Full Heatmap / Clustermap of All Metrics (Cells 026–042)

All clustermaps use the horizontal orientation: **rows = metrics, columns = harmonization attempts**. The convention is enforced: `row_colors=metric_colors`, `col_colors=attempt_colors` — always.

**Cell 027 — §2.2 Clustered clustermap:**
- `data_for_clustermap = df_normed[scoring_cols].dropna().T` — shape (n_metrics, n_attempts)
- Ward linkage, Euclidean distance on both axes
- RdYlGn colormap, center=0.5
- figsize=(210, 25) — very large for dissertation PDF quality
- Seven-group legend placed outside the figure via `add_legend_outside`
- Saved as: `clustermap_all_metrics_clustered_dropna.pdf/.png`

**Cell 028 — §2.2b Raw unnormalized clustermap:**
Same layout with raw `df_ok[scoring_cols]` values; structural reference to compare against normalized version.

**Cells 029–030:** Exploratory variants — one with all metrics including non-scoring (group E descriptives), one sorted by a secondary criterion.

**Cell 032 — §2.3 Grouped heatmap:**
Rows (metrics) fixed in `annot_col → group` sort order; columns (attempts) still clustered by Ward/Euclidean. Shows the organized group structure without dendrogram scrambling.

**Cell 033 — §2.3b Ordered clustermaps:**
Loop over three sort keys: by_strat, by_method, by_imp. Rows (metrics) clustered; columns (attempts) fixed in metadata sort order. Produces three figures.

**Cell 035 — §2.4 Fully ordered heatmap:**
No clustering on either axis. Rows sorted by `group → annot_col`; columns by `strat harshness → imp → method → post_rm`. The most readable structural overview for reading systematic patterns.

**Cell 037 — §2.5.1a Metric correlation clustermap:**
Spearman ρ between all scoring metrics (metrics × metrics). Both axes show `metric_colors` (since rows and columns are both metrics). Answers: "Which metrics are redundant?" Groups of correlated metrics form visible blocks.

**Cell 039 — §2.5.1b Attempt correlation clustermap:**
Spearman ρ between harmonization attempts (attempts × attempts). Both axes show `attempt_colors`. Answers: "Which normalization methods produce similar metric fingerprints?"

**Cell 041 — §2.5.2 Method and metric embeddings (2×3 grid):**
- Row 1: harmonization attempts in metric space (PCA · UMAP · tSNE), colored by method
- Row 2: scoring metrics in attempt space (PCA · UMAP · tSNE), colored by metric_large_type_pal
- Uses `StandardScaler` before embedding; `TSNE(perplexity=min(30, n_metrics-1))` for metric space
- Saved as: `method_metric_embeddings_2x3.pdf/.png`

**Cell 042 — §2.5.3 Method similarity network:**
NetworkX spring layout; nodes = methods, edges = Spearman ρ > 0.75 between method mean metric profiles. Node colors from `method_pal`. Saved as: `method_similarity_network.svg`.

---

#### §3 — Group-by-Group Comparative Analysis (Cells 043–110)

Each metric group has its own subsection. The repeated pattern is: bar charts sorted by the primary metric, catplots split by imputation, `plot_multilevel_comparison` for method/strat/imp groups with FDR-corrected significance heatmaps, and scatter plots for metric relationships.

**§3.1 — Group A: PCA Variance Decomposition (Cells 044–070):**
- Grouped bar chart: mean R² per covariate (RNA_BATCH, Major_group, TUMOR_NORMAL, PLATFORM_RNA) × method, sorted by `r2_RNA_BATCH`. Reference line at R²=0.20 for the RNA_BATCH target.
- Grouped bar chart: PCR (variance-weighted R²) per covariate × method and per covariate × strat, using `annot_pal` for covariate color coding.
- Catplots: `r2_RNA_BATCH` and `pcr_RNA_BATCH` split by `imp` and by `post_rm`, ordered by method mean.
- `plot_multilevel_comparison` for both `r2_RNA_BATCH` and `pcr_RNA_BATCH` across method, strat, imp.
- Scatter: `pcr_COHORT_LABEL` vs `pcr_RNA_BATCH` by method (shows biology-batch trade-off in PCA space).
- Scatter: `r2_RNA_BATCH` vs `pcr_RNA_BATCH` by method, by strat, by post_rm (confirms PCR and R² are negatively correlated, as PCR is variance-weighted — methods that remove PC1 gain PCR but may not improve R²).
- Per-PC R² heatmaps: rows = methods (sorted by mean PCR), columns = PC1–PC10 for RNA_BATCH. Separate heatmap by strat. Shows whether batch variance is concentrated in PC1 or spread across multiple PCs.
- DSC scatter: `dsc_RNA_BATCH` vs `dsc_COHORT_LABEL`, point size ∝ R², colored by method.

**§3.2 — Group B: Neighbor-based Integration (Cells 071–090):**
- kBET vs iLISI scatter: primary batch mixing scatter, colored by method, marker style by strat. Shows methods where local mixing (kBET) and global mixing (iLISI) agree vs. diverge.
- kBET scatter by strat, with all imputations.
- Bar charts: kBET acceptance rate for RNA_BATCH, COHORT_LABEL, PLATFORM_RNA in a grouped bar, colored by annot_pal.
- Catplots: kBET by method × imp, by strat × imp.
- iLISI (filtering out `34_arsyn` and `38_harman` which have extreme outlier values): catplot by method × imp, by strat × imp.
- Pairplot of all LISI and CLISI columns (biology preservation by local inverse Simpson index).
- `plot_multilevel_comparison` for ASW_bio_norm (Major_group and Diagnosis_cell_type_unified) and CLISI metrics across method/strat/imp.
- Batch–biology trade-off scatter (§3.2.3): `asw_batch_norm_RNA_BATCH` (x) vs `asw_bio_norm_Major_group` and `asw_bio_norm_Diagnosis_cell_type_unified` (y), colored by imputation using `imp_pal`. Key dissertation figure.
- CMS (cell mixing score) grid: boxplots by method for each batch column (RNA_BATCH, PLATFORM_RNA, RNASEQ_SOURCE, COHORT_LABEL). Reference line at CMS=0.50.
- `plot_multilevel_comparison` for CMS by method/strat/imp.

**§3.3 — Group C: Embedding Metrics (Cells 091–093):**
- Centroid dispersion grid: 2 rows (UMAP, tSNE) × 4 columns (batch columns), `sharey=True`. Grouped bar by method.
- UMAP vs tSNE entropy correlation: one panel per batch column, scatter with Pearson r annotation, colored by method.

**§3.4 — Group D: Distribution Metrics (Cells 094–097):**
- KS D-statistic grid: boxplots for RNA_BATCH, PLATFORM_RNA, COHORT_LABEL by method. Methods with `ks_frac_sig > 0.5` flagged in red.
- Within-batch cohort D-statistic scatter: `ks_mean_D_RNA_BATCH` (x) vs `ks_cohort_within_batch_mean_D` (y), colored by method.
- Per-gene batch CV bar charts per batch column, sorted ascending.

**§3.5 — Group E: Data Quality (Cells 098–101):**
- Gene and sample count grouped bar: x = `(strat, imp)` ordered by harshness, bars colored by `strat_pal`, with `25_angel` shown separately as a horizontal reference line.
- Bimodality landscape scatter: `fraction_cohorts_bimodal` (x) vs `fraction_cohorts_zero_inflated_bimodal` (y), colored by method, size ∝ `n_cohorts`.
- Expression statistics clustermap: rows = methods (ordered by PCR), columns = exp_median/exp_std/exp_p01/exp_p99. Row color strips = strat and imp palette entries. Each stat column has its own color gradient.

**§3.6 — Groups G and H: Graph Connectivity and Distances (Cells 102–104):**
- Graph connectivity boxplot grid: one panel per biology column (`Major_group`, `Diagnosis_cell_type_unified`, `TUMOR_NORMAL`), `sharey=True`, colored by `method_pal`.
- Distance ratio bar charts: RNA_BATCH, PLATFORM_RNA (batch columns — lower = better mixing), Major_group, Diagnosis_cell_type_unified (biology columns — lower = tighter clusters), colored by `method_pal`.

**§3.7 — Parallel Coordinates (Cell 106):**
Draws 8–10 representative metrics simultaneously for top-N methods as polylines. Methods colored by `method_pal`, ordered by composite score. Shows at a glance which methods dominate across all metric dimensions.

**§3.8 — Ranking Stability Heatmap (Cell 108):**
For each metric group A–H, recomputes composite score excluding all metrics of that group, ranks all methods, and shows the rank matrix (methods × variants) as a heatmap. Rows = top 20 methods by full composite score. Color encodes rank position. Answers: "Does the top-10 change when we remove one metric group?" High column-to-column variance = group drives the ranking; low variance = robust ranking.

**§3.9 — Bubble Chart: Method × Metric Group (Cell 110):**
Grid of bubbles: rows = methods (sorted by composite score descending), columns = groups A–H. Bubble size ∝ mean normalized score for that group. Color = `group_pal`. Compact overview of per-method performance by metric class.

---

#### §4 — Composite Scoring and Top-N Selection (Cells 111–122)

**Cell 112 — Literature review (markdown):**
Justifies metric weighting by citing Tran et al. 2020, Luecken et al. 2022 (scIB), Büttner et al. 2019 (kBET), Korsunsky et al. 2019 (LISI), and Franks et al. 2018 (FSQN). Establishes the 60/35/5 component split.

**Cell 113 — SCORE_WEIGHTS and COMPONENT_WEIGHTS:**
Defines the weighted scoring scheme in three components:

*Batch mixing (60%):*
- `r2_RNA_BATCH` × 3.0 (triple weight — primary metric in all published benchmarks)
- `pcr_RNA_BATCH` × 2.0 (variance-weighted, captures PCs 2–10)
- `kbet_acceptance_rate_RNA_BATCH` × 1.5
- `ilisi_norm_RNA_BATCH` × 1.5
- `asw_batch_norm_RNA_BATCH` × 1.5
- `cms_fraction_mixed_RNA_BATCH` × 1.0
- `umap_entropy_norm_RNA_BATCH` × 1.0
- `dsc_RNA_BATCH` × 1.0
- `ks_mean_D_RNA_BATCH` × 1.0
- PLATFORM_RNA and RNASEQ_SOURCE variants × 0.5 each

*Biology preservation (35%):*
- `r2_Diagnosis_cell_type_unified` × 2.0 (fine-grained — primary biology signal)
- `r2_Major_group` × 1.0 (coarser backup)
- `r2_TUMOR_NORMAL` × 1.5 (fundamental biology axis — loss = analysis failure)
- `asw_bio_norm_Diagnosis_cell_type_unified` × 1.5
- `clisi_mean_Diagnosis_cell_type_unified` × 1.5
- `graph_connectivity_Diagnosis_cell_type_unified` × 1.0
- `dist_ratio_Diagnosis_cell_type_unified` × 1.0
- Major_group variants × 0.5 each

*Data quality (5%):*
- `n_genes` × 0.5 (more genes = more biology accessible)
- `fraction_cohorts_bimodal` × 1.0 (natural bimodal shape is preserved)
- `per_gene_batch_mean_cv_RNA_BATCH` × 0.5

The function `compute_composite_score` normalizes per-component weights, applies direction from `POLARITY`, and sums. Adds `composite_score`, `score_batch_mixing`, `score_bio_preservation` to `df_ok`.

**Cell 114 — Borda count alternative scoring:**
Rank each metric independently, average ranks (with direction from POLARITY). Adds `borda_score`. Provides a non-parametric alternative to the weighted composite.

**Cell 115 — Top-N selection (user-editable):**
Parameters: `N_TOP = 10`, `SCORE_METHOD = "composite"` (options: composite, borda, batch_only, bio_only). Produces `top_n` DataFrame with top N rows.

**Cell 116 — Styled ranking table:**
All methods ranked by composite score, showing composite, batch_mixing, bio_preservation, r2_RNA_BATCH, r2_Major_group, kBET, n_genes. Background gradients applied.

**Cells 117–118 — Helper functions:**
- `_safe_get(row, col)`: NaN-safe scalar accessor for radar chart (returns 0.0 on NaN to prevent polygon collapse)
- `is_pareto(x_vals, y_vals)`: identifies non-dominated points in batch_mixing × bio_preservation space

**Cell 119 — §4.9 Rank correlation between key metrics:**
Spearman clustermap of the ~20 metrics used in SCORE_WEIGHTS. Both axes show `metric_colors`. Visualizes which score-relevant metrics are correlated (redundant) vs. complementary. Saved as: `key_metric_rank_corr.svg/.png`.

**Cell 121 — §4.3 Radar chart:**
Polar plot with 12 axes (one representative metric per group, plus composite score). Top-N methods drawn as filled polygons, colored by `method_pal`.

**Cell 122 — §4.4 Pareto frontier:**
Scatter of `score_batch_mixing` (x) vs `score_bio_preservation` (y) for all runs. Pareto-optimal points highlighted in dark red; top-N methods highlighted with labels.

---

#### §5 — Visual Inspection (Cells 123–128)

**Cell 123 (markdown):** Section header noting that S3-dependent visual inspection (PCA/UMAP/tSNE grids) is implemented in a **separate notebook** — the heavy S3 download and embedding computation are separated from this analytical notebook. However, the structural code stubs (§5.6 and §5.7) remain here.

**Cell 126 — §5.6 FL marker gene correlation + housekeeping gene stability:**
Framework cell: defines `_HK_GENES` list (15 classical housekeeping genes: ACTB, GAPDH, B2M, etc.), references `FL_GENES_ALL` from §11 for the FL marker correlation panel. Wrapped in `try/except` — requires S3 access and `top_n` to be populated. If available: Pearson correlation clustermap of FL marker genes; boxplot CV of housekeeping genes by RNA_BATCH and by Major_group.

**Cell 127–128 — §5.7 Ridgeline plots:**
KDE-based stacked density curves per RNA_BATCH for 3 hardcoded methods: `A_confirmed_bad/strict/16_fsqn_r`, `A_confirmed_bad/strict/17_quantile`, `A_confirmed_bad/strict/01_raw` (raw baseline). Curves computed via `scipy.stats.gaussian_kde`; vertical stacking by offsetting the y-baseline. Uses `rna_batch_palette` for color. Requires `load_and_cache` to be callable (S3 access).

The figures directory contains many manually produced PCA, UMAP, and tSNE grid figures (e.g., `pca_grid_rna_seq_only_sva4_knn_sortimpute.svg`, `umap_grid_top5.svg`, `tsne_grid_angel_good.svg`) — these were generated interactively in the companion visual inspection notebook and saved into the shared `figures/` directory, not from this notebook's cells.

---

### Part 2 — Gene Sets Analysis

#### §6 — Download Gene Lists from S3 (Cells 129–133)

**Cell 130 — `list_gene_files`:**
S3 paginator to discover all `*_genes.json` files under `FL_batch_correction/genes/`. Wrapped in `botocore.exceptions` import for safe error handling.

**Cell 131 — `parse_gene_key`:**
Parses S3 key `{strat}__{imp}__{method}__{post_tag}_genes.json` → `(strat, imp, method, post_rm: bool)`. Returns `None` if the filename doesn't match the expected 4-part `__`-separated format.

Downloads are executed inline by calling `list_gene_files` then iterating with `parse_gene_key`, building:
```
gene_sets: dict[(strat, imp, method, post_rm), set[str]]
```

**Cell 132 — `gene_df` summary:**
One row per gene set: `(strat, imp, method, post_rm, n_genes)`. Prints `groupby(["strat","imp","post_rm"])["n_genes"].describe()` and mean by method. Expected observation: all methods except `25_angel` show nearly identical gene counts within the same `(strat, imp)` pair — gene counts are determined by data preparation, not normalization.

**Cell 133 — `gene_sets_by_strat_imp` and `gene_sets_angel`:**
Aggregates gene sets by `(strat, imp)` via set union across all methods, with `25_angel` tracked separately because it applies internal gene filtering independently of the sample removal step.

---

#### §7 — Gene Count and Overlap Analysis (Cells 134–137)

**Cell 135 — §7.1 Gene count bar chart:**
Bar chart per `(strat, imp)` ordered by `ALL_STRATS` harshness. Bar colors from `strat_pal`. Secondary panel shows `25_angel` gene count as a reference. Prints delta from `S0_no_removal` for each step.

**Cell 136 — §7.2 Jaccard overlap heatmap:**
`jaccard_matrix(sets: list[set]) → np.ndarray` function (documented). Pairwise Jaccard similarity between all `(strat, imp)` gene sets. Annotated heatmap showing compatibility between strategies.

**Cell 137 — §7.3 Supervenn plots:**
Two figures using `supervenn`:
1. Fixed `imp="strict"`, varying strat → shows gene universe contraction as removal becomes aggressive
2. Fixed `strat="A_confirmed_bad"`, varying `imp` (strict/knn/softimpute) → shows gene recovery by imputation

Prints core gene count (present in all sets) and strategy-specific / recovered counts.

---

#### §8 — Progressive Gene Accumulation / Depletion Curves (Cells 138–141)

**Cell 139 — §8.1 Harshness ordering:**
`HARSHNESS_ORDER`: full 30-step list (`S0_no_removal` → `H_affymetrix_extended`) × 3 imputations, then filtered to only steps actually present in `gene_sets_by_strat_imp`. Within each strat: `strict → knn → softimpute` (permissive to aggressive in gene count). The `25_angel` representative gene set is captured as `angel_representative_genes` for use as a reference line.

**Cell 140 — §8.2 Gene retention curve:**
Two-panel figure:
- Panel 1 (line): gene count per harshness step (solid line) + cumulative union of all genes seen so far (dashed). Horizontal reference line at `len(angel_representative_genes)` labeled "25_angel". Secondary x-axis labels = `(strat, imp)` pairs.
- Panel 2 (bar): genes lost vs. previous step.

**Cell 141 — §8.3 Imputation recovery supervenn:**
For `strat="A_confirmed_bad"`, compares strict/knn/softimpute gene sets via supervenn. Also prints:
- Genes recovered by KNN only
- Genes recovered by SoftImpute only
- Genes recovered by both

---

#### §9 — GO Enrichment Analysis Setup (Cells 142–145)

**Cell 143 — GO database download:**
Checks for `go-basic.obo` and `goa_human.gaf` in:
1. Current directory
2. BG project cache at `../../Retroelements/T2T_genes_article/T2T_transposons_genes/`
3. Downloads from official Gene Ontology URLs if not found

**Cell 144 — `load_go_database`:**
Loads the GO DAG (`GODag`) and builds `full_assoc: dict[str, set[str]]` (gene symbol → set of GO IDs) from the GAF file. Returns `(godag, full_assoc, GO_BACKGROUND)` where `GO_BACKGROUND` is the full sorted list of all GO-annotated human genes. Documented rationale: background is fixed to the full GO universe — NOT the current dataset — to prevent a statistical artifact where adding more genes makes enrichments harder to detect.

**Cell 145 — `run_goatools_enrichment`:**
Runs Fisher's exact test enrichment via `goatools`. Key parameters: `min_study_count=3` (filters GO terms with fewer than 3 study genes), `methods=["fdr_bh"]`, `alpha=0.05`. Returns a pandas DataFrame with columns: `GO_ID, term_name, namespace, p_value, FDR, fold_enrichment, n_study, n_background, study_genes_str` (comma-separated string for CSV export).

---

#### §10 — Progressive GO Term Accumulation Curves (Cells 146–151)

**Cell 147 — §10.1 GO-annotated gene sets per harshness step:**
For each `HARSHNESS_ORDER` step, intersects the union gene set with `GO_BACKGROUND` to get the GO-annotatable subset.

**Cell 148 — §10.2 GO enrichment with parquet caching:**
Runs `run_goatools_enrichment` for each step, caching results in `go_cache/{strat}_{imp}.parquet`. Also runs enrichment on the Angel representative gene set and caches as `go_cache/angel_reference.parquet`. On re-run, loads cached parquets instead of recomputing (~10–30 sec/step; total ~3 min for 6 steps).

**Cell 149 — §10.3 GO accumulation curve (3-panel figure):**
- Panel 1: n_genes (solid) and cumulative unique GO terms (dashed) vs harshness step. Angel reference line.
- Panel 2: new unique GO terms per step (bar chart, shows biological information added per filtering step).
- Panel 3: `n_new_terms / n_genes_added` (biological information density per gene added — diminishing returns curve).

**Cell 150 — §10.4 Terms lost between adjacent pairs:**
For each adjacent step pair, identifies GO terms present in the more permissive step but absent in the stricter one. Reports top-20 lost terms sorted by fold enrichment. Dissertation figure: most informative adjacent pair gets a focused horizontal bar chart.

**Cell 151 — §10.5 Imputation-specific GO recovery:**
For `strat="A_confirmed_bad"`, compares GO term sets from strict/knn/softimpute via supervenn.

---

#### §11 — FL-Specific Gene Retention Analysis (Cells 152–160)

**Cell 152–153 (markdown):** Section header and citation table repeated from §5.6 (placed here so citations are visible when opening Part 2 directly without scrolling back).

**Cell 154 — §11.1 Compile FL gene list:**
Four sources assembled into `FL_GENES_ALL` and `FL_GENE_CATEGORIES`:
1. **FL_2025_MARKERS** (Xochelli et al. 2025, *Leukemia*, doi:10.1038/s41375-025-02603-9): Simplified list from the FL C1/C2/C3 subtype paper — BCL2, BCL6, MKI67, PCNA, AICDA, IRF4, FOXP1, MYC, CD10, CD19, CD20, and others.
2. **LEGACY_GC_MARKERS** (BostonGene internal): Centroblast DZ markers (AICDA, MKI67, BCL6, CXCR4, EZH2...) and Centrocyte LZ markers (CD83, MME, FCER2, BCL2, CD40...).
3. **FL_PROG_SIGNATURES** (Pastore et al. 2019, PMID 29475724): FL PFS prognostic signature genes; POD24 mutation markers (EZH2, BCL2, CCND3, TNFRSF14, KMT2D...).
4. **FL_PATHWAY_GENES** (PROGENy, Schubert et al. 2018): BCR signaling, NF-κB, PI3K/AKT, GCB markers.

Also runs HGNC alias validation via `validate_gene_aliases` to resolve known alias pairs (MME/CD10, FAS/CD95, FCER2/CD23).

**Cell 155 — §11.2 FL gene presence matrix:**
Binary DataFrame `fl_presence`: rows = FL genes (grouped by category), columns = `{strat}__{imp}` combinations. Value = 1 if gene present in that preparation step's gene set.

**Cell 156 — §11.3 FL gene retention heatmap:**
Binary heatmap (present = dark green, absent = light red). Columns (harmonization attempts) ordered by composite_score descending. Side color bar = FL gene category. Vertical dashed line after top-10 methods. Answers: "Which normalization methods lose FL marker genes?"

**Cell 157 — §11.4 FL gene progressive retention curves:**
Two figures:
- **Figure A:** One subplot per FL gene category, fraction retained along harshness axis (HARSHNESS_ORDER on x, fraction 0–1 on y). `sharey=True`. Horizontal reference line at 0.90 (90% retention threshold). Angel reference point.
- **Figure B:** Overall FL gene retention curve (bold black) + per-category thin lines superimposed. Vertical lines at imputation introduction steps (strict→knn→softimpute transitions). The most informative single plot for the dissertation chapter on data preparation trade-offs.

**Cell 158 — §11.5 GO enrichment in FL gene subset:**
Runs enrichment on FL genes present at each of the first 6 harshness steps (tractable subset). Caches to `go_cache/fl_{strat}_{imp}.parquet`. Displays enriched terms as horizontal dot plots (x = fold enrichment, size = n_study, color = FDR).

**Cell 159 — §11.6 Progressive FL-gene GO accumulation:**
Same structure as §10.3 but restricted to FL genes only. Shows cumulative unique GO terms enriched as FL gene retention changes along the harshness axis. Angel reference line.

**Cell 160 — §11.7 Final recommendation table:**
Joins `composite_score` with `fraction_FL_genes_retained` per `(strat, imp)`, adds boolean flags for each FL gene category achieving ≥90% retention, and displays as a styled table sorted by composite_score. Exported to `recommendation_table.csv`. This is the actionable output of the entire notebook.

---

## 4. Key Design Decisions and Their Rationale

### 4.1 Metric normalization
All metrics are MinMax-normalized to [0,1] with 1=best before composite scoring. NaN values (from failed sub-computations like kBET returning NaN for one imputation) are filled with the column median rather than 0 or 1. Median fill places NaN-imputed entries at a neutral position — not penalized, not rewarded.

### 4.2 Polarity system
The `POLARITY` dictionary + `POLARITY_MANUAL` overrides handle the mixed direction of raw metrics. After normalization, all columns are in the same direction (1=best), so SCORE_WEIGHTS can be purely positive. This separation of direction logic from weighting logic is the key architectural decision.

### 4.3 Composite score weighting
The 60/35/5 component split mirrors the scIB benchmark (Luecken et al. 2022). Within batch mixing, R² gets triple weight because it is the most universally reported metric and directly interpretable as fraction of transcriptomic variance attributable to batch. Within biology preservation, `Diagnosis_cell_type_unified` gets double the weight of `Major_group` because it is the fine-grained FL subtype label relevant to the dissertation.

### 4.4 Horizontal clustermap orientation
All clustermaps use rows = metrics, columns = attempts (the transposed orientation relative to the original plan). This makes the metric label text readable on the row y-axis without squishing, and places the sample-level annotations (strat/imp/method) on the top color bar where they are more informative for grouping.

### 4.5 Fixed GO background
The GO enrichment background is always the full set of GO-annotated human genes, not the dataset's current gene list. This ensures that enrichment strength correctly increases as more biologically relevant genes are retained — the expected signal when moving from aggressive to permissive data preparation. A dataset-specific background would create an artifact where adding more genes makes enrichments statistically harder to detect.

### 4.6 25_angel separation
`25_angel` applies internal gene-level filtering (retaining only genes with low estimated batch variance), independent of the sample removal strategy. It is tracked in a separate `gene_sets_angel` dictionary and displayed as a reference line rather than a curve point on accumulation plots. This prevents Angel from distorting the systematic harshness ordering.

---

## 5. Implementation Status vs. Plans

### What is fully implemented
| Section | Status | Notes |
|---|---|---|
| §1 — Setup, imports, font constants | Complete | FONT_BASE system fully applied |
| §1 — Palette system | Complete | 7 palettes, `attempt_colors`/`metric_colors` naming resolved |
| §1 — `plot_multilevel_comparison` | Complete | Palette auto-detection, FDR heatmap |
| §2 — All clustermap variants | Complete | Clustered, grouped, ordered, raw companion |
| §2.5 — Method similarity network, embeddings | Complete | 6-panel 2×3 grid + NetworkX network |
| §3.1 — Group A (PCA R², PCR, DSC) | Complete | Bar charts, catplots, multilevel, scatter, per-PC heatmap |
| §3.2 — Group B (kBET, iLISI, ASW, CMS) | Complete | All planned plots + batch-biology trade-off scatter |
| §3.3 — Group C (embedding metrics) | Complete | Centroid dispersion grid, UMAP/tSNE entropy correlation |
| §3.4 — Group D (KS, per-gene CV) | Complete | KS grid, within-batch scatter, CV bars |
| §3.5 — Group E (data quality) | Complete | Gene/sample count, bimodality, expression stats clustermap |
| §3.6 — Groups G, H (graph, distances) | Complete | Connectivity boxplots, dist_ratio bars |
| §3.7 — Parallel coordinates | Complete | Top-N methods on 8 representative metrics |
| §3.8 — Ranking stability heatmap | Complete | A–H group-removal variants |
| §3.9 — Bubble chart | Complete | Method × group bubble size = mean score |
| §4 — Composite scoring | Complete | SCORE_WEIGHTS, COMPONENT_WEIGHTS, Borda count alternative |
| §4.4 — Pareto frontier | Complete | Batch_mixing vs bio_preservation |
| §4.9 — Rank correlation (key metrics) | Complete | Spearman clustermap of SCORE_WEIGHTS metrics |
| §5.6 — FL marker correlation (stub) | Partial | Framework present; requires S3 access |
| §5.7 — Ridgeline plots (stub) | Partial | Framework present; requires `load_and_cache` |
| §6 — Gene list download | Complete | S3 discovery, parsing, `gene_sets` dict |
| §7 — Gene count and Jaccard overlap | Complete | Bar charts, Jaccard heatmap, supervenn |
| §8 — Gene accumulation curves | Complete | Retention line, stacked bar, imputation supervenn |
| §9 — GO database setup | Complete | Download, `load_go_database`, `run_goatools_enrichment` |
| §10 — GO accumulation curves | Complete | 3-panel figure, lost-terms analysis, imputation supervenn |
| §11 — FL gene retention | Complete | FL gene list (4 sources), presence matrix, heatmap, retention curves |
| §11.7 — Final recommendation table | Complete | Joins metrics + FL retention; CSV export |

### Planned but not yet present in the notebook
| Section from plans | Status | Notes |
|---|---|---|
| §5.1–5.4 — Full S3 download helpers + PCA/UMAP/tSNE grids | In separate notebook | The main notebook references this as "separate notebook"; figure files exist in `figures/` from interactive sessions |
| §5.5 — Violin plots + CV-vs-expression curves | In separate notebook | Code was designed here (Plan 2 Cell 5.5) but not present in current cells |
| §3.1 — vp_ (variancePartition) group F analysis | Not implemented | Group F metrics are in the data but not plotted separately |
| Caching functions (`load_and_cache`, `get_or_compute_pca/umap/tsne`) | Not in notebook | Referenced by §5.6/5.7 stubs but function definitions not present |
| `clustermap_std` wrapper function | Not present | Plan 3 Feature 3 was planned but `add_legend_outside` and `strip_box_plot` exist; `clustermap_std` is missing |

---

## 6. Figures Inventory

The `figures/` directory contains 247 files. Key categories:

| Category | File pattern | Count |
|---|---|---|
| PCA grids | `pca_grid_*.svg` | ~20 |
| UMAP grids | `umap_grid_*.svg` | ~20 |
| tSNE grids | `tsne_grid_*.svg` | ~20 |
| Clustermaps | `clustermap_*.{svg,pdf}` | ~12 |
| Group A (R², PCR) | `a_r2_*`, `a_pcr_*`, `a_per_pc_*` | ~20 |
| Group B (kBET, ASW, CMS) | `b_*` | ~20 |
| Group C (embedding) | `c_*` | 2 |
| Groups G, H | `h_dist_ratio_*` | 1 |
| Method similarity | `method_metric_embeddings_2x3.pdf`, `method_similarity_network.svg`, `metric_correlation_clustermap.svg`, `attempt_correlation_clustermap.pdf` | 4 |
| Composite scoring | `rank_stability_heatmap.svg` | 1 |
| Violin / CV curves | `violins_*.svg`, `cv_vs_exp_*.svg` | 2 |

All key figures are saved in both SVG (vector, dissertation quality) and PNG (raster, 200 dpi, for preview). Clustermaps with extreme size requirements (e.g., figsize=(210,25)) are also saved as PDF.

---

## 7. Known Issues and Gaps to Address

1. **CSV path mismatch:** Cell 003 loads `metrics_comprehensive_260513.csv` from the working directory, but the file lives in `metric_tables/`. This causes a `FileNotFoundError` on fresh kernel start unless the working directory is set correctly or a symlink exists. The notebook should be run from `harmonization-metrics/` with `metrics_comprehensive_260513.csv` symlinked there, or the path should be updated to `metric_tables/metrics_comprehensive_260513.csv`.

2. **Scratch cells remain:** Cells 062 (`df_ok` bare display), 066 (`df_ok` bare display), 049 (`annot_pal` bare display), 050 (`r2_cols_main[0][4:]` bare display), 075 (`len('kbet_acceptance_rate_')` bare display), 077/080 (column name inspection), 086 (empty cell) are exploratory artifacts that were not cleaned up as specified in Plan 2 §A.4.

3. **S3-dependent cells not isolated:** Cells 126–128 (§5.6, §5.7) reference `load_and_cache` and `top_n` that depend on prior S3 downloads and scoring. These cells fail silently (wrapped in try/except) but add dead weight when S3 is unavailable. The function `load_and_cache` defined in Plan 3 is not present in the notebook.

4. **iLISI outlier handling:** Cells 081–082 manually exclude `34_arsyn` and `38_harman` from iLISI plots with no comment. The reason (extreme outlier values in iLISI for these methods) should be documented.

5. **Group F (variancePartition) not plotted:** VP metrics exist in the data (`vp_` prefix columns are included in col_meta) but §3 has no subsection for Group F analysis. The planned §3.5 in Plan 1 (now renumbered) should still be implemented.

6. **`H_affymetrix_extended` strategy added but not in original `ALL_STRATS`:** Cell 018 defines `ALL_STRATS` with 11 entries including `H_affymetrix_extended`, but the original plans specified 10 strategies (S0 through G). The strat_pal has a manually assigned color for it. This is correct — it reflects an extension of the benchmark — but the implementation plans do not document this strategy.

7. **Duplicate bare-display cells for early exploration:** Several sequential cells (053–070) represent variations of the same plot idea (e.g., multiple versions of R² grouped bar) that were iterated manually. These could be consolidated into a single parametric cell.

8. **`clustermap_std` missing:** Plan 3 Feature 3 specifies `clustermap_std` as a standardized wrapper that enforces the orientation and naming conventions. The function is not in the notebook; clustermaps are called directly with `sns.clustermap(...)` each time.

---

## 8. Data Flow Summary

```
metrics_comprehensive_260513.csv (1640 × 205)
    │
    ├─ df (all rows, indexed by run_id)
    │   ├─ df_ok (status==ok, 1640 rows)
    │   ├─ df_normed (scoring_cols normalized to [0,1], 1=best)
    │   ├─ attempt_colors (per-run palette DataFrame)
    │   └─ df_ok.composite_score, .score_batch_mixing, .score_bio_preservation
    │
    ├─ col_meta (per-metric DataFrame: group A–H, annot_col, metric_type)
    │   ├─ metric_colors (per-metric palette DataFrame)
    │   └─ scoring_cols (metrics with POLARITY ≠ 0)
    │
    └─ top_n (N_TOP best runs by SCORE_METHOD)

S3 gene JSONs
    │
    ├─ gene_sets: dict[(strat,imp,method,post_rm), set[str]]
    ├─ gene_sets_by_strat_imp: dict[(strat,imp), set[str]]  (union, excl. angel)
    ├─ gene_sets_angel: dict[(strat,imp), set[str]]
    ├─ FL_GENES_ALL + FL_GENE_CATEGORIES
    └─ fl_presence: DataFrame (FL genes × strat__imp combinations)

GO database (go-basic.obo + goa_human.gaf)
    │
    ├─ godag, full_assoc, GO_BACKGROUND
    ├─ go_results: dict[(strat,imp), DataFrame]  (cached to go_cache/*.parquet)
    └─ _fl_go_results: dict[(strat,imp), DataFrame]  (FL genes specifically)
```

---

## 9. Research Questions the Notebook Answers

| Question | Where answered | Key metric / figure |
|---|---|---|
| Which methods reduce batch variance the most? | §3.1 + §4 ranking | `r2_RNA_BATCH`, `pcr_RNA_BATCH`; `a_r2_multilevel_method.svg` |
| Which methods achieve local batch mixing? | §3.2 | `kbet_acceptance_rate_RNA_BATCH`, `ilisi_norm_RNA_BATCH`; `b_kbet_ilisi_scatter.svg` |
| Is biology preserved after correction? | §3.2 + §4 | `asw_bio_norm_Diagnosis_cell_type_unified`; `b_batch_biology_tradeoff.svg` |
| Which methods are most similar to each other? | §2.5 | `attempt_correlation_clustermap.pdf`, `method_similarity_network.svg` |
| Which metrics are redundant? | §2.5.1a + §4.9 | `metric_correlation_clustermap.svg`, `key_metric_rank_corr.svg` |
| Which methods rank best overall? | §4 | `composite_score`; styled ranking table |
| Is the top-10 ranking robust to metric choice? | §3.8 | `rank_stability_heatmap.svg` |
| How many genes are lost per removal strategy? | §7–§8 | Gene retention curves; `gene_retention_curve_*.svg` |
| Does imputation recover lost genes? | §8.3 + §7.3 | Supervenn figures |
| Which biological processes are gained/lost? | §10 | `go_accumulation_*.svg`, lost-term bar charts |
| Are FL marker genes retained? | §11 | `fl_retention_heatmap_*.svg`, `fl_retention_curves_*.svg` |
| What is the optimal strategy overall? | §11.7 | `recommendation_table.csv` |
