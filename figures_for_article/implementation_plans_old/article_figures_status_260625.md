# Article 1 — Figures and Writing Status
**Date:** 2026-06-25  
**Document purpose:** Complete reference for the current state of the manuscript, all figures (done and planned), and next implementation steps. Use this as the starting brief for the next figure implementation plan.

---

## Article Overview

**Title:** Bulk transcriptomic harmonization tools benchmarking using germinal center lymphoma dataset: a novel computational pipeline ComboBatch reveals MNN and SVA as top performing methods

**Authors:** Daniil Nikitin, Arsen Arakelyan, Nicolas Borisoff, Maria Savchenko, Anatoly Bobe, Alexandr Bagaev

**File:** `figures_for_article/FL_harmonization_article.docx`

**Key numbers used in the manuscript:**
| Statistic | Value |
|---|---|
| Total samples | 7,174 |
| DLBCL | 4,466 |
| FL | 1,697 |
| Normal B cells (Normal_B_cells + Kassandra) | ~1,000 |
| Cohorts | 88 |
| Platforms | 4 (Affymetrix, Illumina NGS, Illumina microarray, Agilent) |
| Batch removal strategies | 14 |
| Harmonization methods implemented | 31 (out of 33 attempted; 2 failed) |
| Harmonization attempts run | 2,407 |
| Harmonization attempts after QC filter | 2,234 (< 5% samples with fully-NA expression) |
| Scoring metrics with defined polarity | 87 (out of ~230 total computed) |

---

## Manuscript Section Status

| Section | Status | Notes |
|---|---|---|
| **Title** | Draft | ComboBatch pipeline name used |
| **Abstract** | Stub — empty | Not yet written |
| **Introduction** | Partial draft | 3 paragraphs; mentions platform axes, subtle biology differences, TCGA limitation |
| **Results — Dataset description** | Full draft | Paragraphs on sample composition, batch imbalance, gene NA statistics |
| **Results — Pipeline description** | Partial draft | Reference to Figure 1C pipeline scheme |
| **Results — Batch removal strategies** | Partial draft | 14 strategies described; references Figures 2A, 2C, 2D |
| **Results — Best approaches selection** | Partial draft | Describes clustermap build; 87-metric scoring; references Figure 3 |
| **Results — Best approaches** | Stub heading only | No text yet |
| **Results — Relative impact of factors** | Stub heading only | Strategy > method > post-removal > imputation; no text |
| **Results — Global vs local trade-off** | Stub heading only | No text |
| **Results — Final decision tree** | Stub heading only | No text |
| **Discussion — Subtle biology** | Partial notes | Dataset heterogeneity paragraph drafted |
| **Discussion — Novel pipeline** | Note only | "Describe technical limitations, timing" |
| **Discussion — Clustermap approach** | Stub heading only | |
| **Discussion — AI-driven vs human** | Note only | Mentions FSQN found by googling; MNN+SVA by AI |
| **Discussion — Comparison with other approaches** | Partial | Quartet project section partially written (3 paragraphs) |
| **Materials & Methods — Dataset assembly** | Partial draft | Core paragraph written |
| **Materials & Methods — Batch annotation** | Partial draft | Naming convention described |
| **Materials & Methods — Gene expression profiling** | Stub heading | No text |
| **Materials & Methods — Computational hardware** | Partial | 32-48 CPU, 240 GB RAM; Jupyterhub server |
| **Materials & Methods — Batch removal strategies** | Partial draft | 14 strategies reference table mentioned |
| **Materials & Methods — Imputation** | Partial draft | 4 approaches, missforest exclusion noted |
| **Materials & Methods — Harmonization methods** | Partial draft | 38 identified, 33 implemented, Shambhala note |
| **Materials & Methods — Post-removal** | Stub heading | |
| **Materials & Methods — Pipeline architecture** | Note | "Yaml files, python scripts, links to github" |
| **Materials & Methods — Harmonization quality metrics** | Partial draft | 87 scoring metrics, 4 major groups described |
| **Materials & Methods — Figures preparation** | Stub | |
| **Materials & Methods — AI usage** | Stub | |
| **Data Availability** | Partial note | Mentions Shambhala2-fast GitHub repo |
| **Funding** | Empty | |
| **Acknowledgements** | Empty | |
| **References** | Empty | To be added last |

---

## Figure Status — Main Figures

### Figure 1: Dataset Composition and Computational Pipeline

**Manuscript caption:** "Dataset composition and computational pipeline. (A) Dataset composition by batches. (B) Dataset composition by biology groups. (C) Scheme of the computational pipeline. (D) Bar plot of sample counts by batches and biology, ordered by batches. Biology groups are color coded according to the lymphoma ontogeny palette."

| Panel | File | Status | Notes |
|---|---|---|---|
| 1A — Dataset composition by batches | `comb_ann_platform_groups_bubble_chart.svg/png` | **DONE** | Hex-packed bubble chart; Platform_group → RNA_BATCH hierarchy |
| 1B — Dataset composition by biology | `comb_ann_biology_bubble_chart.svg/png` | **DONE** | Hex-packed bubble chart; biology groups coloured by lymphoma ontogeny palette |
| 1C — Computational pipeline scheme | `pipeline_scheme.svg/png` | **DONE** | 9-stage vertical diagram; run `python pipeline_scheme_figure.py` |
| 1D — Bar plot batches × biology | `barplot_diagnoses_by_batches.svg` | **DONE** | Stacked barplot; batches on x-axis; diagnosis coloured |
| 1E — Bar plot batches × cohorts | `barplot_batches_by_cohorts.svg` | **DONE** | Per-cohort counts by RNA_BATCH; needed for supplementary or Figure 1 |

**Status: FULLY IMPLEMENTED.** All Figure 1 panels are in `figures/`. Require assembly into a multipanel figure in Figma or as a matplotlib multipanel.

**Remaining work for Figure 1:**
- Compose all panels into a single multipanel SVG/PDF for journal submission
- Check that all font sizes are 10pt (GLOBAL_FONT_SIZE) across panels
- Check that the pipeline scheme labels match the 31-method count in the manuscript (currently shows "39 methods" — needs updating)

---

### Figure 2: Batch Removal Strategies, NA Genes and Imputation

**Manuscript caption:** "(A) Circos-Sankey plot showing batch removal strategies and number of samples remaining after each strategy being applied. (B) [unclear from current text]. (C) NA heterogeneity across batches — bar chart of non-NA gene counts per RNA_BATCH, coloured by Platform_group. (D) Hybrid Circos-Sankey plot showing gene overlap between strict imputation and KNN/softimpute approaches."

| Panel | File | Status | Notes |
|---|---|---|---|
| 2A — Circos-Sankey strategies | `circos_sankey_strategies.svg/png` | **DONE** | Implemented in `Introductory_figures_for_article.ipynb` |
| 2B — TBD | — | **UNKNOWN** | Caption panel B is not clearly defined in the current manuscript draft |
| 2C — NA genes per batch | — | **TODO** | Bar/violin plot of non-NA gene count per RNA_BATCH; coloured by Platform_group; from raw `comb_exp` matrix; key numbers: NGS >15,000; rare batches 6,000–7,000 |
| 2D — Imputation gene overlap Sankey | — | **TODO** | Hybrid Circos-Sankey showing gene set sizes: strict (3,520), KNN (~12,000), softimpute (~11,000) and their overlaps per strategy |

**Remaining work for Figure 2:**
1. Clarify what panel 2B should be (discuss with supervisor)
2. Implement Figure 2C: per-batch non-NA gene count plot — load `comb_exp` from S3, compute non-NA count per RNA_BATCH, barplot coloured by `batch_to_platform_group`
3. Implement Figure 2D: gene overlap Sankey — load `comb_ann` and prepared files from S3; compute gene counts per strategy × imputation combination; visualize as Sankey or upset plot
4. Compose into multipanel

---

### Figure 3: Clustermap of Harmonization Attempts

**Manuscript caption:** "Cluster map of 2234 harmonization attempts (columns) in a space of 87 quality metrics (rows)."

| Panel | File | Status | Notes |
|---|---|---|---|
| 3 — Full clustermap | — | **TODO** | Seaborn clustermap; 2234 attempts × 87 metrics; polarity-normalized; coloured column annotations by strategy, method, imputation |

**Specification:**
- Input: `metrics_comprehensive.csv` from S3 (loaded in `harmonization-metrics/harmonization_metrics_analysis.ipynb`)
- Filter: keep only attempts with < 5% samples having fully-NA gene expression (2,234 out of 2,407)
- Metrics: the 87 metrics with defined polarity; apply polarity normalization (multiply by +1 or −1 so that higher = better)
- Clustering: complete linkage or ward on both rows (metrics) and columns (attempts)
- Annotations: colour bars above columns for strategy, method family, imputation
- Colour map: diverging RdBu centred at 0.5
- Best attempts: highlight top 20 attempts with a gold frame or colour annotation
- 4 metric clusters (from analysis): local neighbourhood (always bad), mixed bag, mostly-good global, always-good global

**Remaining work for Figure 3:**
1. Load `metrics_comprehensive.csv` from S3 in a new notebook cell or script
2. Filter to 2,234 attempts; select 87 scoring metrics
3. Apply polarity normalization
4. Build publication-grade clustermap with seaborn
5. Add column annotation bars (strategy, method family, imputation type, harshness tier)
6. Highlight best attempt group
7. Save as SVG + PNG to `figures/`

---

### Figure 4: Decision Tree for Harmonization Method Selection

**Manuscript caption:** (not yet written in the docx)

**Design (from CLAUDE.md and supervisor meeting 2026-06-04):**
- Hierarchical, not circular
- 4 levels: biomaterial type → platform type → harmonization method → QC approach
- Key paths:
  - FF only → MNN or FSQN R (no post-removal)
  - FFPE only → SVA + softimpute/KNN (★ first-ever FFPE platform mixing)
  - RNA-seq only → SVA + softimpute/KNN (FF/FFPE mixed; two FL subgroups)
  - RNA-seq + Illumina arrays → FSQN R or AMDBNorm/FSMVN + post-removal
  - RNA-seq + various arrays → MNN + post-removal (visual inspection required)
- Format: Python matplotlib tree with boxes, arrows, colour coded by outcome quality

| Panel | File | Status | Notes |
|---|---|---|---|
| 4 — Decision tree | — | **TODO** | Hierarchical decision tree; 4 levels; see design spec above |

**Remaining work for Figure 4:**
1. Write `decision_tree_figure.py` (standalone script, same pattern as `pipeline_scheme_figure.py`)
2. Each decision node as FancyBboxPatch, edges as annotated arrows
3. Colour leaf nodes: green=best, yellow=good, orange=marginal
4. Save to `figures/decision_tree.svg/png`
5. Write an implementation plan file `decision_tree_figure_plan_260625.md` before implementing

---

## Supplementary Figures — Planned

| Figure | Description | Status |
|---|---|---|
| Supp. 1 — NA gene statistics | Per-batch and per-gene NA rate distribution in the raw dataset before any filtering | TODO |
| Supp. 2 — Harmonization method table | Table of all 31 methods with algorithm family, R/Python, harshness tier, reference | Referenced in manuscript M&M; exists as table in CLAUDE.md |
| Supp. 3 — Metric groups table | All 87 scoring metrics with group, formula, polarity | Referenced in manuscript M&M |
| Supp. 4 — Visual inspection PCA/UMAP/tSNE | Best approaches: MNN, SVA, FSQN R; worst examples | Images from `harmonization-metrics/` |
| Supp. 5 — Strategy comparison barplots | PCR/R² by strategy, method, imputation (catplots) | Exists in `harmonization-metrics/figures/` |
| Supp. 6 — Shambhala comparison | Best Shambhala P/Q variant vs. MNN vs. SVA | TODO if Shambhala excluded from main figures |
| Supp. 7 — Gene retention analysis | Genes retained per strategy × imputation combination | Mentioned in CLAUDE.md next steps |

---

## Figures Already in `figures/` Directory (Full Inventory)

| File | Purpose | Article figure | Status |
|---|---|---|---|
| `pipeline_scheme.svg/png` | 9-stage computational pipeline | Figure 1C | DONE |
| `comb_ann_platform_groups_bubble_chart.svg/png` | Platform groups bubble chart | Figure 1A | DONE |
| `comb_ann_biology_bubble_chart.svg/png` | Biology groups bubble chart | Figure 1B | DONE |
| `barplot_diagnoses_by_batches.svg` | Samples per batch × diagnosis | Figure 1D | DONE |
| `barplot_batches_by_diagnoses.svg` | Samples per diagnosis × batch | Supplementary | DONE |
| `barplot_batches_by_cohorts.svg` | Samples per cohort × batch | Supplementary | DONE |
| `barplot_diagnoses_by_cohorts.svg` | Samples per cohort × diagnosis | Supplementary | DONE |
| `circos_sankey_strategies.svg/png` | Batch removal strategies Circos-Sankey | Figure 2A | DONE |
| `radial_sankey_strategies.svg` | Alternative radial Sankey (rejected) | — | Legacy/unused |
| `RNA_BATCH_palette.svg` | Palette reference swatch | — | Reference only |
| `lymphoma_ontogeny_palette.svg` | Palette reference swatch | — | Reference only |
| `trial_barplot.svg` | Exploratory draft | — | Legacy/unused |

---

## Figures Implemented in `Finally_assembled_figures_for_article.ipynb` (2026-06-27)

All figures below are cells in `Finally_assembled_figures_for_article.ipynb`.
Run cells 0–2 first (setup: imports, data load, palettes). Cell 3 (S3 expression load) is optional — required only for Supp A and B.

| Cell ID | Figure | Output file(s) | Status |
|---|---|---|---|
| `4` | Fig 7 — Local Neighborhood Metrics (kBET, LISI, graph connectivity, UMAP/tSNE entropy) | `fig7_local_metrics_neighborhood.{svg,png}` | **Done — run to produce** |
| `604abb86` | Fig 8 — Structural/Distance Metrics (centroid dispersion, WaterMelon, CMS, ASW) | `fig8_structural_distance_metrics.{svg,png}` | **Done** |
| `97309549` | Fig 8B — Distributional Similarity + NA Retention (KS, per-gene CV, NA heatmap) | `fig8b_distributional_similarity_na_retention.{svg,png}` | **Done** |
| `bb35f9f6` | Fig 9 — Cross-Metric Correlation + Factor Importance (η² barplot, composite violin) | `fig9_cross_metric_correlation_factor_importance.{svg,png}` | **Done** |
| `99c0a4f7` | Fig 10 — Composite Ranking + Best Profiles (lollipop, parallel coords, bubble chart) | `fig10_composite_ranking_best_profiles.{svg,png}` | **Done** |
| `a6f56239` | Fig 11 — Decision Tree (4-level FancyBboxPatch; biomaterial → method → QC) | `fig11_decision_tree_harmonization_selection.{svg,png}` | **Done** |
| `ce9f79af` | Supp 9 — Embeddings placeholder (PCA/UMAP/tSNE grid) | `supplementary/supp9_embeddings_best_stars.{svg,png}` | **Placeholder** |
| `66ef50af` | Supp A — NA genes per batch (requires Cell 3) | `supplementary/suppA_na_genes_per_batch.{svg,png}` | **Done (run Cell 3 first)** |
| `f852f76e` | Supp B — Imputation gene overlap Sankey (requires Cell 3) | `supplementary/suppB_imputation_gene_overlap_sankey.{svg,png}` | **Done (run Cell 3 first)** |
| `e6b12210` | Supp C — Gene retention: noNA heatmap + accumulation curves + GO placeholder | `supplementary/suppC_gene_retention_analysis.{svg,png}` | **Done (Panel A always; B/C require gene_sets)** |
| `c001d736` | Supp D — Group B detail: kBET, ASW, CMS boxplot grid | `supplementary/suppD_group_b_detail_kbet_asw_cms.{svg,png}` | **Done** |
| `d56a2eb2` | Supp E — Group C detail: centroid dispersion stripplot grid | `supplementary/suppE_group_c_centroid_dispersion.{svg,png}` | **Done** |
| `32d6cbc1` | Supp F — Group H detail: Euclidean distance ratio boxplot grid | `supplementary/suppF_group_h_euclidean_distance.{svg,png}` | **Done** |
| `1bdfee3d` | Supp G — Group G detail: graph connectivity barplot grid (guarded) | `supplementary/suppG_group_g_graph_connectivity.{svg,png}` | **Done (guarded)** |

Standalone scripts:
- `fig10_metric_star_visualization.py` → `figures/fig10_metric_star_best15.{svg,png}` — radar star of Best 15 superiority per metric group

**Note on MAIN vs SUPPLEMENTARY assignment:** Not yet assigned — requires running the notebook and Daniil's visual review of the saved outputs. Cells are currently tagged as `[MAIN or SUPPLEMENTARY — inspect output]` pending review.

---

## Currently Missing / Highest Priority Figures

Ordered by article section priority:

1. **Figure 3 (Clustermap)** — the central result figure; requires `metrics_comprehensive.csv` on S3; build in a new `Harmonization_clustermap_figure.ipynb` or as a standalone script
2. **Figure 2C (NA genes per batch)** — straightforward; requires loading raw `comb_exp` from S3; implement as a new cell in `Introductory_figures_for_article.ipynb`
3. **Figure 2D (Imputation gene overlap Sankey)** — moderate complexity; requires prepared files from S3
4. **Figure 4 (Decision tree)** — needs design approval first; write `decision_tree_figure_plan_260625.md`
5. **Multipanel assembly** — Figures 1 and 2 panels need to be composed into publication-ready multipanel SVGs

---

## Next Implementation Steps (Ordered)

### Step 1 — Figure 2C: NA Genes Per Batch (Easy win, ~2h)
- New notebook cell in `Introductory_figures_for_article.ipynb` after the existing barplots section
- Load `comb_exp` (already in memory as `comb_exp` 7174 × 3447)
- Compute `(comb_exp != 0).sum(axis=1)` or count non-NA per RNA_BATCH group
- Horizontal barplot sorted by count, coloured by `batch_to_platform_group`
- Save to `figures/barplot_nona_genes_per_batch.svg/png`

### Step 2 — Figure 2D: Imputation Gene Overlap Sankey (Moderate, ~4h)
- Load prepared S3 files: `prepared/{strat}__strict__exp.tsv.gz`, `prepared/{strat}__knn__exp.tsv.gz`, `prepared/{strat}__softimpute__exp.tsv.gz` for representative strategies (A, C, S0)
- Count genes in each; compute pairwise overlaps using sets
- Implement as a Sankey diagram using plotly or a custom matplotlib implementation
- Save to `figures/sankey_imputation_genes.svg/png`

### Step 3 — Figure 3: Publication Clustermap (Complex, ~1 day)
- New notebook: `Harmonization_clustermap_figure.ipynb` in `figures_for_article/`
- Load `metrics_comprehensive.csv` from S3 (`FL_batch_correction/metrics/metrics_comprehensive.csv`)
- Filter to 2234 attempts; select 87 scoring metrics; apply polarity normalization
- Build seaborn clustermap with column annotations (strategy, method family, imputation, harshness)
- Add best-attempt highlight; annotate 4 metric clusters
- Save to `figures/clustermap_harmonization_attempts.svg/png`

### Step 4 — Figure 1 Multipanel Assembly (Easy, ~2h)
- New cell in `Introductory_figures_for_article.ipynb` or standalone `figure1_assembly.py`
- Use `matplotlib.gridspec` or `matplotlib.figure` to compose 4 panels
- Read existing SVGs from `figures/` and compose into a single figure
- Fix pipeline scheme label "39 methods" → "31 methods" (or show 39 tested, 31 successfully run)

### Step 5 — Figure 4: Decision Tree (Moderate, ~4h)
- Write implementation plan first: `decision_tree_figure_plan_260625.md`
- Standalone script `decision_tree_figure.py`, same structure as `pipeline_scheme_figure.py`
- 4-level hierarchy: biomaterial → platform → method → QC
- Colour leaf nodes by recommendation strength

### Step 6 — Supplementary metrics comparison figures
- Use existing figures from `harmonization-metrics/figures/` (catplots, multilevel plots)
- Adapt them to publication font sizes and colour scheme
- Save publication-ready copies to `figures/supplementary/`

---

## Notebook Structure — What Is in `Introductory_figures_for_article.ipynb`

| Cell range | Section | Implemented figures |
|---|---|---|
| 0–8 | Setup: imports, palettes, S3 load, Platform_group | Data objects (`comb_exp`, `comb_ann`), palettes, `batch_to_platform_group` |
| 9–11 | Palette swatches | `RNA_BATCH_palette.svg`, `lymphoma_ontogeny_palette.svg` |
| 12–17 | Bubble charts (Platform_group → RNA_BATCH) | `comb_ann_platform_groups_bubble_chart.svg`, `comb_ann_biology_bubble_chart.svg` |
| 18+ | Barplots (diagnoses × batches, batches × cohorts) | `barplot_diagnoses_by_batches.svg`, `barplot_batches_by_cohorts.svg`, etc. |
| Last cells | Circos-Sankey strategies | `circos_sankey_strategies.svg/png` |

---

## Key Data Sources for New Figures

| Data | S3 key | Purpose |
|---|---|---|
| Raw expression (7174 × ~50k genes) | `FL_batch_correction/exp/S0_no_removal__strict__01_raw__post0.tsv.gz` | Figure 2C (NA genes) |
| Annotation | `FL_batch_correction/prepared/S0_no_removal__knn__ann.tsv.gz` | All figures |
| Prepared expression (imputed) | `FL_batch_correction/prepared/{strat}__{imp}__exp.tsv.gz` | Figure 2D (gene overlap) |
| Comprehensive metrics | `FL_batch_correction/metrics/metrics_comprehensive.csv` | Figure 3 (clustermap) |

---

## Article Writing Priorities

Based on figures readiness, the writing can proceed in this order:

1. **Figure 1 text** — dataset description paragraph is mostly written; finalize Figure 1 caption once panels assembled
2. **Figure 2 text (2A)** — Circos-Sankey strategies section mostly written; needs 2C and 2D to complete
3. **Figure 3 text** — "Best approaches selection" section partially drafted; needs clustermap to be built first
4. **Materials & Methods** — most sections have outline; can be expanded from CLAUDE.md context
5. **Figure 4 + Results decision tree text** — last; needs finalized supervisor-approved tree
6. **Abstract** — write last after all results sections are complete
7. **Discussion** — external collaborators (Masha S) reviewing
