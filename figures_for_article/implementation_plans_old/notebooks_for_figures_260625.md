# Notebooks for Article Figures — Reference (2026-06-25)

## Purpose

This document describes the three notebooks used to generate article figures. Read it before implementing any new figure to understand data objects, palettes, helpers, and output conventions already in place.

---

## 1. `harmonization-metrics/harmonization_metrics_analysis_v3.ipynb`

**Path:** `harmonization-metrics/harmonization_metrics_analysis_v3.ipynb`  
**Size:** 353 cells · ~16 MB (outputs stripped by nbstripout before commit)  
**Data source:** `harmonization-metrics/metric_tables/metrics_comprehensive_260609.csv` (latest)

### Purpose
Main quantitative analysis of all 2,234 harmonization attempts across 87 scoring metrics. Produces the metric-level figures used for the Results section and supplementary material. Contains the draft of Figure 3 (the clustermap).

### Setup (cells 0–41)

| Cell | Contents |
|---|---|
| 1 | Imports: boto3, pandas, seaborn, sklearn, scipy, umap |
| 3 | Loads metrics CSV; creates `run_id` index; filters `df_ok` (status=="ok", 2,234 rows) |
| 6 | `_top_ids` (15 tuples), `df_best`, `is_best` column, `BEST_LABEL`/`BEST_COLOR`/`BEST_HATCH` constants — full best-approach selection infrastructure |
| 10 | `GROUP_MAP` — maps metric group letters (A–K) to column name prefixes |
| 13 | `POLARITY` — dict: +1=higher is better, -1=lower is better, 0=descriptive (87 scoring columns) |
| 17 | `normalize_for_display()` — normalizes each metric to [0,1] given polarity; returns `df_normed` |
| 21–25 | `plot_multilevel_comparison()`, scatter/bar/heatmap helpers |
| 25 | `bar_plot()`, `scatter_plot()`, `heatmap_plot()` — article-grade plot helpers |
| 28–41 | Palette definitions: `attempt_colors`, `group_pal`, `annot_pal`, `imp_pal`, `method_pal`, `harshness_pal`, `strat_pal` |

### Key Data Objects

| Variable | Shape / type | Description |
|---|---|---|
| `df` | 2,407 × ~230 | Full metrics CSV; all attempts including failed |
| `df_ok` | 2,234 × ~230 | Quality-filtered (status=="ok"); gains `is_best` bool column |
| `df_normed` | 2,234 × 87 | Polarity-normalized [0,1]; 1=best for every scoring metric |
| `scoring_cols` | list[87] | Metric columns with defined polarity (±1) |
| `col_meta` | DataFrame | Per-column: group letter, type (batch/bio/quality), polarity |
| `_top_ids` | list[15 tuples] | (method, imp, strat) for the 15 manually validated best approaches |
| `df_best` | 15 × ~230 | Subset of `df_ok` where `is_best == True` (post_rm=False only) |
| `df_best_tagged` | 15 × ~230 | Copy of `df_best` with `method` column overwritten to `BEST_LABEL` |
| `data_v3` | 2,249 × ~230 | `df_ok` + `df_best_tagged` concatenated; used in all comparison plots |
| `data_for_clustermap` | 87 × 2,234 | Transposed df_normed — used directly in `sns.clustermap()` |

### Structure and Sections

**§2 — Heatmaps and clustermaps** (Fig 3 drafts)
- §2.1: Completeness heatmap — which metrics computed for which runs
- §2.2: Clustered clustermap (rows=attempts, cols=metrics; polarity-normalized) — **Fig 3 prototype**
- §2.3: Grouped heatmap — metrics in fixed group order, attempts clustered
- §2.4: Fully ordered heatmap — no clustering, fixed row/col order
- §2.5: Method similarity — Spearman correlation clustermap, PCA/UMAP/tSNE of attempts in metric space, correlation network
- §2.6: NA genes heatmap (raw dataset)

**§3 — Per-group metric analysis** (supplementary figures source)
- §3.1: Group A — PCA variance (R², PCR, DSC); most developed; all multilevel/strip/scatter/catplot types; joint R²×%var heatmap
- §3.2: Group B — Neighbor-based (kBET, iLISI, cLISI, ASW, CMS); batch vs. biology trade-off
- §3.3: Group C — Embedding (UMAP/tSNE centroid dispersion)
- §3.4: Group D — Distribution (KS tests)
- §3.5: Group E — Data quality (zero fraction, bimodality, cohort-level stats)
- §3.6: Groups G/H — Graph connectivity, Euclidean distance ratios
- §3.7: Parallel coordinates for top-N methods
- §3.8: Rank stability heatmap across metric subsets
- §3.9: Bubble chart — method × metric group summary
- §3.11: Group K (NA retention) + WaterMelon Group I analysis
- §3.13: Harshness (low/medium/high) effect analysis

**§4 — Composite scoring and ranking**
- §4.1: Literature-based metric weighting; composite_score column
- §4.9: Spearman rank correlation between key metrics; Pareto frontier

**Part 2 — Gene Sets Analysis (§5–§11)**
- §5.7: Ridgeline plots — expression density by RNA_BATCH
- §7: Gene set Jaccard overlap clustermap, supervenn, concentric Sankey (in development)
- §8: Gene retention curve across harshness levels
- §10: GO enrichment analysis via goatools
- §11: FL-specific gene retention heatmap and curves

### Best vs. Rest Comparison Pattern

**This is the central visual concept used throughout all §3 plots and is the model for implementing Figure 3 and Figure 4.**

All metric comparison plots in §3.1–§3.9 contrast the 15 manually validated best approaches against the full pool of 2,234 attempts. The mechanism is:

```python
# Cell 6: define best approaches and create df_best
_top_ids = [                               # 15 manually curated (method, imp, strat) tuples
    ("10_mnn",      "strict",  "S0_no_removal"),
    ("04_sva",      "knn",     "C_rnaseq_only"),
    ("04_sva",      "softimpute", "K_ffpe_only"),
    # ... 12 more
]
df_ok["is_best"] = df_ok.apply(            # bool column added to df_ok
    lambda r: (r["method"], r["imp"], r["strat"]) in _top_ids_set and not r["post_rm"],
    axis=1,
)
df_best = df_ok[df_ok["is_best"]].copy()  # 15 rows: best approaches only

# Per-plot usage (cells 112, 120, 128, 130, 133 …):
df_best_tagged = df_best.copy()
df_best_tagged["method"] = BEST_LABEL     # BEST_LABEL = "Best"
data_v3 = pd.concat([df_ok, df_best_tagged], ignore_index=True)
```

`data_v3` embeds the best 15 attempts as a synthetic pseudo-method group called `"Best"` alongside all 31 real methods. Every strip plot, catplot, and multilevel comparison in §3.1–§3.9 uses `data_v3` as its data source and `style_best_bars()` (cell 25) to add the `★` star annotation and `BEST_COLOR = "#E63946"` (vivid red) to the Best group bar.

**Why this matters for the next figures:**
- **Figure 3 (clustermap):** best-approach rows should be highlighted / annotated in the row color bar using the same `is_best` column and `BEST_COLOR`
- **Figure 4 (decision tree):** the decision criteria at each node are derived from comparing `df_best` vs. `df_ok` metric distributions — the same split used in §3 plots
- **Supplementary:** every §3 figure using `data_v3` is already a comparison of best vs. rest and can be adapted directly

The 15 `_top_ids` tuples encode the final decision tree: MNN for all-platform strategies, SVA for RNA-seq-only and FFPE-only, FSQN R for RNA-seq and FF microarrays.

### Figure Output

Saved to `harmonization-metrics/figures/` — **613 files total** (SVG + PNG pairs):

| File prefix | Content |
|---|---|
| `a_pcr_*`, `a_r2_*`, `a_dsc_*`, `a_joint_*`, `a_per_pc_*` | Group A metrics (Article Fig 3 supplementary candidates) |
| `b_*` | Group B: kBET, LISI, ASW, CMS |
| `c_*` | Group C: UMAP/tSNE centroid dispersion |
| `clustermap_all_metrics_clustered*` | Fig 3 drafts (`.pdf`, `.svg`) |
| `clustermap_sorted_by_*` | Ordered clustermaps |
| `gene_*` | Gene set analysis |
| `k_*` | Group K: NA retention |
| `pca_grid_*`, `tsne_grid_*`, `umap_grid_*` | Visual inspection grids (see notebook 2) |
| `metric_*` | Metric correlation/similarity |

### Status for Article
- `clustermap_all_metrics_clustered.svg` is the Fig 3 prototype — needs publication-grade polish; implement in new `Harmonization_clustermap_figure.ipynb`
- Group A metric figures (`a_pcr_*`, `a_r2_*`) are publication-ready quality; candidate for supplementary
- WaterMelon, GO enrichment, and harshness sections are exploratory; not article-grade yet

---

## 2. `harmonization-metrics/harmonization_metrics_visual_inspection.ipynb`

**Path:** `harmonization-metrics/harmonization_metrics_visual_inspection.ipynb`  
**Size:** 338 cells · ~9.4 MB  
**Data source:** Same metrics CSV (`metrics_comprehensive_260609.csv`) + live S3 expression downloads

### Purpose
Interactive visual inspection of top-N harmonization attempts per strategy via PCA / UMAP / tSNE grids colored by metadata. Used to validate metric-based conclusions and discover biology. Not designed for final article figures — exploration and decision-making tool.

### Setup (cells 0–22)

| Cell | Contents |
|---|---|
| 1 | Imports; `FONT_BASE = 7.5` (scales all text globally) |
| 3 | Same metrics load as v3 → `df`, `df_ok`, `df_normed`, `scoring_cols` |
| 5–13 | `GROUP_MAP`, `POLARITY`, `normalize_for_display()` — identical to v3 |
| 16–18 | PCA/UMAP/tSNE palettes + `plot_palette()` helper |
| 20 | **`load_harmonized_exp()`** — downloads expression TSV.GZ from S3; returns samples × genes DataFrame |
| 20 | **`load_annotation()`** — downloads annotation TSV.GZ from S3 |
| 20 | **`_EXP_CACHE`** — dict caching S3 downloads within the session (key = (strat, imp, method, post_rm)) |
| 21 | **`plot_embedding_grid()`** — workhorse: given a list of run_ids, downloads data (or hits cache), computes PCA/UMAP/tSNE, draws multi-panel comparison grid |

### `plot_embedding_grid()` signature (cell 21)

```python
fig = plot_embedding_grid(
    top_ids,           # list of (method, imp, strat[, post_rm]) tuples
    n_cols=4,          # panels per row
    color_rows=[       # metadata columns to color by (one row of panels each)
        "RNA_BATCH",
        "Diagnosis_cell_type_unified",
        "PLATFORM_RNA",
    ],
    embedding="pca",   # "pca" | "umap" | "tsne"
    figsize=(20, 15),
)
fig.savefig("figures/pca_grid_example.svg", bbox_inches="tight")
```

### Structure (organized by strategy)

| Cells | Strategy | Key findings |
|---|---|---|
| 22–33 | J — FF only | MNN and FSQN R best; post0 preferred |
| 34–52 | K — FFPE only | **SVA + softimpute/KNN = first-ever platform mixing** |
| 53–70 | A/B — confirmed_bad / extended_bad | MNN confirmed best; angel looks ok but isn't |
| 71–129 | C — RNA-seq only | **SVA + knn/softimpute reveals two FL subgroups** (key biology); FSQN R; Harmony bad; TMM bad |
| 130–214 | D — Malignant only | angel, combat, limma, fsmvn, qsmooth, Shambhala explored |
| 217–232 | F — Microarray only | scanorama looks ok but fails; qsmooth bad |
| 233–257 | G — Affymetrix only | **FSQN R failed** (unreliable without poly-A as reference); MNN best |
| 258–263 | H — Affymetrix extended | MNN and FSQN R best |
| 264–278 | I — Rare batches removed | InMoose ComBat-seq best |
| 270–298 | Cross-strategy method comparisons | AMDBNorm, FSMVN, VST, FSQN R, rank norm |
| 299–328 | Metric-sorted explorations | kBET-sorted, tSNE entropy-sorted |
| 329–337 | Raw datasets | Distribution violins, per-cohort dist plots |

### Key Decisions Documented Here
- SVA + C_rnaseq_only + knn/softimpute → two FL subgroups visible in tSNE (confirms SVA as biological-preserving method)
- MNN is the only method that cleanly separates FL / DLBCL / Normal GC across multi-platform strategies
- FFPE-only + SVA: first benchmark attempt to successfully mix FFPE and FF platforms
- FSQN R fails on Affymetrix-only (no poly-A reference batch)
- arsyn/harman excluded: too many NAs post-harmonization
- angel: seemed good by LISI metrics; visual inspection showed no separation

### Important Notes
- Uses `_EXP_CACHE` dict to avoid redundant S3 downloads — run cells in order within a session
- **Does not save figures systematically** — for interactive exploration only; call `fig.savefig()` manually for keepers
- Requires AWS credentials in session (`boto3`)

---

## 3. `figures_for_article/Introductory_figures_for_article.ipynb`

**Path:** `figures_for_article/Introductory_figures_for_article.ipynb`  
**Size:** 44 cells · ~8.4 MB (large because bubble chart has embedded rasterized outputs)  
**Data source:** All data loaded live from S3 — no local data files

### Purpose
The single notebook for all introductory and dataset-overview figures for Article 1 (Fig 1A–1D, Fig 2A, supplementary barplots). Every figure in `figures_for_article/figures/` is produced here or by `pipeline_scheme_figure.py`.

### Setup (cells 0–12)

| Cell | Contents |
|---|---|
| 0 | Imports: boto3, circlify, matplotlib, seaborn, umap, scipy, json |
| 7 | **Canonical palettes** — defined once; reuse everywhere in notebook |
| 9 | S3 download → `comb_exp` (7174 × 3447 samples × genes); raw expression matrix |
| 10 | S3 download → `comb_ann` (7174 × 485 annotation columns); gains `Platform_group` column |
| 10 | `batch_to_plaform_group` — maps RNA_BATCH string → one of 4 Platform_group strings |

### Canonical Palettes (cell 7) — Never Redefine Elsewhere

```python
lymphoma_ontogeny_palette   # per Diagnosis_cell_type_unified / cell type; Temperature-Split
rna_batch_palette           # per RNA_BATCH (29 entries)
platform_palette            # per PLATFORM_RNA / GPL code
strat_pal                   # per strategy (14 entries)
```

### Data Objects

| Variable | Shape | S3 key |
|---|---|---|
| `comb_exp` | 7174 × 3447 | `FL_batch_correction/exp/S0_no_removal__strict__01_raw__post0.tsv.gz` |
| `comb_ann` | 7174 × 485 | `FL_batch_correction/prepared/S0_no_removal__knn__ann.tsv.gz` |

`comb_ann` gains `Platform_group` in cell 10 via `batch_to_plaform_group` dict.

### Implemented Sections

| Cells | Section | Output files | Article figure |
|---|---|---|---|
| 14–20 | Bubble chart helper functions | — | — |
| 20 | `create_biology_bubble_chart()` | `comb_ann_biology_bubble_chart.{svg,png}` | Fig 1B |
| 20 | Platform groups bubble chart | `comb_ann_platform_groups_bubble_chart.{svg,png}` | Fig 1A |
| 22–29 | Circos-Sankey strategies | `circos_sankey_strategies.{svg,png}` | Fig 2A |
| 31–37 | Barplot diagnosis × batch | `barplot_diagnoses_by_batches.svg` | Fig 1D |
| 38–43 | Supplementary barplots | `barplot_batches_by_cohorts.svg`, `barplot_diagnoses_by_cohorts.svg` | Supp |

### Figure Output Convention (always apply)

```python
FIGURES_DIR = Path("figures")
GLOBAL_FONT_SIZE = 10  # all text — fixed for Figma alignment

fig.savefig(FIGURES_DIR / "my_figure.svg", bbox_inches="tight")
fig.savefig(FIGURES_DIR / "my_figure.png", bbox_inches="tight", dpi=200)
```

### rcParams (set in cell 0 — do not override)

```python
plt.rcParams["pdf.fonttype"] = "truetype"
plt.rcParams["svg.fonttype"] = "none"   # text stays editable in Figma
plt.rcParams["figure.dpi"] = 200
sns.set_style("ticks")
```

### Current Figures in `figures_for_article/figures/` (16 files)

| File | Source |
|---|---|
| `comb_ann_platform_groups_bubble_chart.{svg,png}` | This notebook |
| `comb_ann_biology_bubble_chart.{svg,png}` | This notebook |
| `circos_sankey_strategies.{svg,png}` | This notebook |
| `radial_sankey_strategies.svg` | This notebook (older draft) |
| `barplot_diagnoses_by_batches.svg` | This notebook |
| `barplot_batches_by_cohorts.svg` | This notebook |
| `barplot_diagnoses_by_cohorts.svg` | This notebook |
| `barplot_batches_by_diagnoses.svg` | This notebook |
| `pipeline_scheme.{svg,png}` | `pipeline_scheme_figure.py` |
| `lymphoma_ontogeny_palette.svg`, `RNA_BATCH_palette.svg` | This notebook (palettes) |
| `trial_barplot.svg` | Scratch (not for article) |

### Figures Yet to Be Added

| Article figure | What to add | Where |
|---|---|---|
| Fig 2C — NA genes per batch | New cell after §Sankey section; use `comb_exp`; bar chart colored by Platform_group | This notebook |
| Fig 2D — Imputation gene overlap | Sankey of gene counts (strict 3,520 / KNN ~12k / softimpute ~11k) per strategy | This notebook |
| Fig 1 multipanel | Compose existing 1A–1D into one publication SVG | Figma or new cell |

---

## 4. `figures_for_article/Finally_assembled_figures_for_article.ipynb`

**Path:** `figures_for_article/Finally_assembled_figures_for_article.ipynb`  
**Size:** ~92 KB (outputs stripped; 18 cells)  
**Data source:** `harmonization-metrics/metric_tables/metrics_comprehensive_260609.csv` (local); optional S3 raw expression load in Cell 3

### Purpose

Implements all remaining article metric and summary figures (Figs 7–11, Supp A–G, Supp 9). Does NOT depend on S3 for metric figures — only the gene retention supplementaries (Supp A/B) need Cell 3 (S3 load).

### Setup (cells 0–3)

| Cell | ID | Contents |
|---|---|---|
| 0 | `0` | Imports, rcParams, constants (FIGURES_DIR, GLOBAL_FONT_SIZE=10, BEST_COLOR, S3_BUCKET, METRICS_CSV_PATH, METRIC_TYPE_MAP) |
| 1 | `1` | `fh.load_metrics_data()` → df_ok, df_normed, scoring_cols, col_meta; `_top_ids` (15 tuples); `build_best_vs_rest()` → df_best, df_best_tagged, data_v3 |
| 2 | `2` | All palettes: strat_pal, method_pal (tab20+tab20b boosted), imp_pal, harshness_pal, group_pal; HARSHNESS_MAP; `get_metric_cols()`; harshness assigned to df_ok and data_v3 |
| 3 | `3` | **OPTIONAL** S3 load: comb_exp_raw (7174 × ~50k), comb_ann; required for Supp A, B only |

### Key Data Objects

| Variable | Shape | Description |
|---|---|---|
| `df_ok` | 2407 × ~238 | All valid metric runs (status=="ok"); gains `harshness` and `composite_score*` columns |
| `df_normed` | 2407 × 85 | Polarity-normalized [0,1]; 85 scoring cols with nonzero polarity |
| `scoring_cols` | list[85] | The 85 metric columns with defined polarity in df_normed |
| `col_meta` | DataFrame | Per-column: group letter (A–K), polarity, col name |
| `df_best` | 15 × ~238 | Subset of df_ok for the 15 Best approaches |
| `data_v3` | 2422 × ~238 | df_ok + df_best_tagged (Best as synthetic method) |
| `method_pal` | dict | tab20+tab20b with boosted saturation; 31 methods + Best |
| `strat_pal` | dict | 16 strategies with fixed colors from v3 notebook |
| `harshness_pal` | dict | `{"low": green, "medium": orange, "high": red}` |
| `METRIC_TYPE_MAP` | dict | 4 metric type groups → column prefix lists |
| `HARSHNESS_MAP` | dict | strat → harshness tier |

### Figure Cell Inventory (cells 4–17)

| Cell ID | Cell contents | Output |
|---|---|---|
| `4` | Fig 7 — Local Neighborhood (kBET, LISI, graph connectivity, UMAP/tSNE entropy, local-vs-global) | `fig7_local_metrics_neighborhood.{svg,png}` |
| `604abb86` | Fig 8 — Structural/Distance (centroid dispersion heatmap, WaterMelon, CMS, ASW) | `fig8_structural_distance_metrics.{svg,png}` |
| `97309549` | Fig 8B — Distributional Similarity + NA (KS, CV, NA heatmap, noNA% by harshness) | `fig8b_distributional_similarity_na_retention.{svg,png}` |
| `ce9f79af` | Supp 9 — Embeddings placeholder (3×3 grid with text; real coords not loaded) | `supplementary/supp9_embeddings_best_stars.{svg,png}` |
| `bb35f9f6` | Fig 9 — Cross-metric correlation (PCR vs kBET scatter, composite violin, η² barplot, stacked bar) | `fig9_cross_metric_correlation_factor_importance.{svg,png}` |
| `99c0a4f7` | Fig 10 — Composite ranking (lollipop all runs, parallel coords Best 15, equal vs weighted scatter, bubble chart method×group) | `fig10_composite_ranking_best_profiles.{svg,png}` |
| `66ef50af` | Supp A — NA genes per batch (requires Cell 3); guarded | `supplementary/suppA_na_genes_per_batch.{svg,png}` |
| `f852f76e` | Supp B — Gene overlap Sankey (requires Cell 3 or gene_sets); guarded | `supplementary/suppB_imputation_gene_overlap_sankey.{svg,png}` |
| `e6b12210` | Supp C — Gene retention: noNA heatmap (always), accumulation curves (guarded), GO placeholder | `supplementary/suppC_gene_retention_analysis.{svg,png}` |
| `a6f56239` | Fig 11 — Decision tree (FancyBboxPatch 4-level; biomaterial → method → QC; 14×9 in landscape) | `fig11_decision_tree_harmonization_selection.{svg,png}` |
| `c001d736` | Supp D — Group B detail boxplot grid (kBET, ASW, CMS) | `supplementary/suppD_group_b_detail_kbet_asw_cms.{svg,png}` |
| `d56a2eb2` | Supp E — Group C centroid dispersion stripplot grid | `supplementary/suppE_group_c_centroid_dispersion.{svg,png}` |
| `32d6cbc1` | Supp F — Group H distance ratio boxplot grid | `supplementary/suppF_group_h_euclidean_distance.{svg,png}` |
| `1bdfee3d` | Supp G — Group G graph connectivity barplot grid (guarded, null-value safe) | `supplementary/suppG_group_g_graph_connectivity.{svg,png}` |

### Important Implementation Notes

- All figures use `GLOBAL_FONT_SIZE = 10` for every `fontsize=` argument.
- All composite scores (`composite_score_equal`, `composite_score_weighted`) are computed inside figure cells (Fig 9/10); `composite_score` (simple mean, no suffix) is also added in Fig 9 for Panel B.
- `df_ok["post_rm_str"]` is added in Fig 9 cell (cast to str for groupby safety).
- Bubble chart in Fig 10 Panel D converts categorical method/group to numeric positions before passing to `ax.scatter()` — this is intentional (matplotlib scatter requires numeric x/y).
- Supp D/E/F/G auto-scale grid: `_ncols = min(3, n_cols)`, `_nrows = ceil(n_cols / _ncols)`.
- `col_meta.groupby("group")["col"].apply(list)` — use this pattern to get per-group column lists from `col_meta`.

---

## Quick Reference: Data Paths Across Notebooks

| Data | S3 key | Used in |
|---|---|---|
| Raw expression (all platforms) | `FL_batch_correction/exp/S0_no_removal__strict__01_raw__post0.tsv.gz` | Introductory notebook |
| Annotation | `FL_batch_correction/prepared/S0_no_removal__knn__ann.tsv.gz` | Introductory notebook |
| Harmonized expression | `FL_batch_correction/exp/{strat}__{imp}__{method}__post{0\|1}.tsv.gz` | Visual inspection notebook |
| Comprehensive metrics | `FL_batch_correction/metrics_comprehensive.csv` | Both analysis notebooks |
| Latest local metrics copy | `harmonization-metrics/metric_tables/metrics_comprehensive_260609.csv` | Both analysis notebooks |

---

## Implementation Checklist for New Figures

When adding a new figure to any of these notebooks:

1. **Check palette** — use the canonical palette from `Introductory_figures_for_article.ipynb` cell 7 or `harmonization_metrics_analysis_v3.ipynb` cells 28–41; never redefine
2. **Font size** — use `GLOBAL_FONT_SIZE = 10` for all `fontsize=` args
3. **Save both formats** — SVG (vector for Figma) and PNG (dpi=200 for review)
4. **rcParams** — `svg.fonttype='none'`, `pdf.fonttype='truetype'`, `figure.dpi=200`
5. **Document the cell** — add a `##` markdown header with the figure number and description
