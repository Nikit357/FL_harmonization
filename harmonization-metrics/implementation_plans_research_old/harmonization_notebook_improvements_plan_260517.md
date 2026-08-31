# Implementation Plan: Harmonization Metrics Notebook v2 Improvements

**Date:** 2026-05-17  
**Author:** Daniil Nikitin  
**Target file:** `harmonization_metrics_analysis_v2.ipynb` (copy of v1)  
**Status:** ✅ IMPLEMENTED 2026-05-17 — all code changes applied to `harmonization_metrics_analysis_v2.ipynb` (194 cells)

---

## Intro: the origincal request from Daniil

Based on this overview document @harmonization_metrics_analysis_notebook_overview_260517.md and the previously implemented
  plans @implementation_plans_research_old/new_metrics_plan_260516.md , please compose a new implementation plan
  'harmoniztion_notebook_improvements_plan_260517.md' with detailed description of the following features: 1) please refactor the
  visualization functions tom heavily use seaborn and be as short as possible. For example, scatterplots in your implementation
  rely on iteration over individual strats/methods/imps with ax.scatter for each. This is inconvenient, I cant reuse extensively
  these functions. The rest logic of plotting (font sizes, axes labels, figure savings) should be preserved. Please rewrite all
  cells where a visualizations are used in this way. Preserve all my manual added cells but rewrite them so they are aligned with
  the rest notebook. 2) copy the current notebook @harmonization_metrics_analysis.ipynb as
  harmonization_metrics_analysis_v2.ipynb and implement all the requested changes there. 3) add analysis of the new metrics that
  were implemented in  @implementation_plans_research_old/new_metrics_plan_260516.md . Metrics about number and proportion of
  nas, genes and samples that have all or some nas - should be used as scoring parameters and visualized in clustermap. Also,
  metrics of percentage (~proportion) of genes/samples with all nas should be used for filtering of harmonization attempts before
  clustering and analysis. Say, I want to compare only those attempts that preserve all samples with some non-na genes (use
  percentage of samples with all na genes metrics). Then, I want the joint analysis of R2 by RNA BATCH in individual PCs (top 10)
  and of percentage of variance explained by these PCs. I want to see exactly how much variance is explained by each component
  RNA_BATCH - R2 by RNA batch by PCs weighted by their percentage of variance explained, the heatmaps by PCs that you've added to
  the notebook. Then, I want a separate analysis of WaterMelon scores - how thy correlate between each other by different
  columns (batch and biology), and whether they are closer to the local or to the global metrics. 4) I want the new strategy of
  batch removal (those about rare batches removal, look at
  @../harmonization-scripts/implementation-plans-old/rare_batch_removal_strategy_plan_260516.md to be implemented in palettes and
  clustermaps and all the rest relevant plots and comparisons. 5) I want all the shambhala methods (with different calibration
  datasets, imputations, batch removals etc) to be analyzed in the notebook (look at
  @../shambhala_adoption/Shambhala_containerized/reseach_implementation_plans/cross_product_implementation_plan_260515.md  ) 
  everywhere applicable: in clustermaps, in box, bar and scatterplots. For shambhala please prepare a separate palette that 
  visualized different calibration datasets in separate colors: try to adapt matplotlib tab 20b or related palettes to show that 
  the shambhala harmonization variants are close to each other but drastically differ from the rest ones. Maybe add an additional
  color annotation to the large clustermap: shambhala or not shambhala. Also add code cells that analyze shambhala outputs 
  quality by calibration datasets and other factors separately, without other harmonization methods. 6) Add a separate color
  palette for harmonization methods by their harshness: green is low harshness, yellow is medium and red is high harshness. Add 
  this palette and color annotation to all the clustermaps and heatmaps that compare methods of harmonization. Next, add a 
  separate section to the notebook with analysis of differences by all metrics classes (groups) between methods by their 
  harshness. Precisely, I want to know how harshness level impacts local/global metrics, or behavour in different batch removal 
  strategies: RNASeq only, Affymetrix only etc. Write the implementation plan carefully acknowledging all these requests from my side in  'harmoniztion_notebook_improvements_plan_260517.md'. Systematize my requests in the beginning of the plan. Do not 
  implement yet.

## 0. Summary of All Requests

| # | Request | Scope | New cells? |
|---|---|---|---|
| R1 | Refactor scatter/bar plots to seaborn (no manual group iteration) | All Part 1 visualization cells | No — rewrite in-place |
| R2 | Copy current notebook to `_v2.ipynb`; implement all changes there | One-time copy step | — |
| R3a | Add Group K (NA retention) to scoring and clustermaps; filter by `pct_samples_allNA` | §1, §2, §3 new subsection | Yes — §3.10 |
| R3b | Joint per-PC R² × variance-explained heatmaps (Groups A + J combined) | §3.1 extension | Yes — 2 new cells |
| R3c | WaterMelon score (Group I) analysis: correlation, local-vs-global comparison | New §3.11 | Yes — ~5 cells |
| R4 | Add `I_rare_batches_removed` strategy to all palettes, clustermaps, plots | §1 palette cell, all downstream | No — palette + rerun |
| R5 | Shambhala methods: palette, color annotation in clustermaps, separate §3.12 | §1 palette cell, §2, new §3.12 | Yes — §3.12 (~8 cells) |
| R6 | Harshness-level palette: green/yellow/red annotation; §3.13 harshness impact analysis | §1 palette cell, all clustermaps, new §3.13 | Yes — §3.13 (~6 cells) |

---

## 1. Prerequisites and Data State

### 1.1 Assumed input data

- `metric_tables/metrics_comprehensive_260513.csv` (or a refreshed version containing Groups J, K, I columns)
  - Groups J (`pct_var_pc{1..10}`, `pct_var_cum_top10`) and K (`n_genes_noNA`, `pct_genes_noNA`, `n_samples_noNA`, `pct_samples_noNA`, `n_genes_allNA`, `n_samples_allNA`, `n_na_cells`, `pct_na_cells`) are confirmed implemented on the metrics pod (all steps 1–7 of `new_metrics_plan_260516.md` marked complete).
  - Group I (`wm_*` columns) is implemented but the parallel WM pass (Step 10) may not have run yet. If absent, the §3.11 WaterMelon section should be wrapped in a try/except with a clear note.
  - `I_rare_batches_removed` strategy data: new S3 outputs generated after `bench_shared.py` update (plan `rare_batch_removal_strategy_plan_260516.md` is fully checked off). If not yet in the CSV, add a data-availability guard.
  - Shambhala methods: outputs in S3 using key pattern `{strat}__{imp}__shambhala_{p}_{q}__post{0|1}.tsv.gz`. If not yet in the CSV, add a data-availability guard.

### 1.2 Step zero: copy notebook

```bash
cp harmonization_metrics_analysis.ipynb harmonization_metrics_analysis_v2.ipynb
```

All changes described below are applied exclusively to `harmonization_metrics_analysis_v2.ipynb`. The v1 notebook is preserved unchanged as the reference baseline.

---

## 2. Request R1 — Refactor Visualization Functions to Seaborn

### 2.1 The problem

Most scatter plots in the current notebook iterate over groups manually:

```python
# Current anti-pattern (example from §3.1)
for method, grp in df_ok.groupby("method"):
    ax.scatter(grp["r2_RNA_BATCH"], grp["pcr_RNA_BATCH"],
               color=method_pal[method], label=method, s=20, alpha=0.7)
ax.legend()
```

This pattern:
- Cannot be reused across sections without copy-paste.
- Loses seaborn's built-in legend, jitter, error-bar, and hue-style handling.
- Inconsistent styling across cells because each iteration block hardcodes alpha/s/marker separately.

### 2.2 New helper functions (add to the Setup cell or a dedicated "Plotting helpers" cell)

All helpers go into a single **Cell 015b — Reusable plot helpers**, inserted after the existing `plot_multilevel_comparison` Cell 015. Each function:
- Accepts a `data=df` argument (tidy DataFrame in long format).
- Accepts `palette` as an optional dict. If `None`, falls back to seaborn default.
- Accepts `ax=None` (creates figure if not provided).
- Accepts `save_path=None` (saves to `FIGURES_DIR / save_path` when provided, both SVG and PNG).
- Uses the global font system (`FONT_LABEL`, `FONT_TICK`, `FONT_LEGEND`, `FONT_TITLE`).
- Calls `sns.despine()` before return.

#### 2.2.1 `scatter_plot`

```python
def scatter_plot(
    data: pd.DataFrame,
    x: str,
    y: str,
    hue: str,
    style: str | None = None,
    size: str | None = None,
    palette: dict | str | None = None,
    hue_order: list | None = None,
    style_order: list | None = None,
    alpha: float = 0.75,
    s: int = 30,
    ax: plt.Axes | None = None,
    figsize: tuple = (8, 6),
    xlabel: str | None = None,
    ylabel: str | None = None,
    title: str | None = None,
    legend_outside: bool = False,
    save_path: str | None = None,
) -> plt.Axes:
    """
    Scatter plot wrapping sns.scatterplot.

    Parameters
    ----------
    data : pd.DataFrame
        Tidy DataFrame with columns matching x, y, hue, style, size.
    x, y : str
        Column names for axes.
    hue : str
        Column for point color.
    style : str, optional
        Column for point marker style.
    size : str, optional
        Column for point size.
    palette : dict or str, optional
        Color mapping for hue levels. Passed to sns.scatterplot.
    hue_order : list, optional
        Order of hue levels in legend.
    style_order : list, optional
        Order of style levels.
    alpha : float
        Transparency of points.
    s : int
        Point size in points².
    ax : plt.Axes, optional
        Existing axes to draw on. Creates a new figure if None.
    figsize : tuple
        Figure size when ax is None.
    xlabel, ylabel, title : str, optional
        Axis labels and title. Default to column names if None.
    legend_outside : bool
        If True, places legend outside axes via add_legend_outside().
    save_path : str, optional
        Filename (without extension) relative to FIGURES_DIR. Saves SVG + PNG.

    Returns
    -------
    plt.Axes
    """
```

This replaces all manual `ax.scatter(grp[x], grp[y], color=pal[k])` patterns.

#### 2.2.2 `bar_plot`

```python
def bar_plot(
    data: pd.DataFrame,
    x: str,
    y: str,
    hue: str | None = None,
    palette: dict | str | None = None,
    order: list | None = None,
    hue_order: list | None = None,
    estimator: str = "mean",       # "mean", "median"
    errorbar: tuple | None = ("ci", 95),
    orient: str = "v",             # "v" or "h"
    ax: plt.Axes | None = None,
    figsize: tuple = (10, 5),
    xlabel: str | None = None,
    ylabel: str | None = None,
    title: str | None = None,
    xtick_rotation: int = 45,
    legend_outside: bool = False,
    save_path: str | None = None,
) -> plt.Axes:
    """
    Bar plot wrapping sns.barplot with standard project styling.
    ...
    """
```

#### 2.2.3 `heatmap_plot`

```python
def heatmap_plot(
    data: pd.DataFrame,    # wide-format matrix, rows × columns
    cmap: str = "RdYlGn",
    center: float | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    annot: bool = False,
    fmt: str = ".2f",
    row_colors: pd.DataFrame | None = None,
    col_colors: pd.DataFrame | None = None,
    figsize: tuple = (12, 8),
    xlabel: str | None = None,
    ylabel: str | None = None,
    title: str | None = None,
    save_path: str | None = None,
) -> plt.Axes:
    """
    Thin wrapper around sns.heatmap with standard project styling.
    Does not wrap clustermap (which has its own clustermap_std function).
    ...
    """
```

### 2.3 Cells to rewrite (by section)

The following cells contain manual-iteration scatter/bar patterns and must be rewritten to call the helpers above. The surrounding logic (normalization, data filtering, axis reference lines, figure saving) must be preserved exactly.

#### §3.1 Group A — cells to rewrite

| Cell approx. | Current pattern | Replacement |
|---|---|---|
| `a_r2_multilevel_method` bar chart | Loop over covariates, `ax.bar` per group | `bar_plot(df_long, x="method", y="r2", hue="covariate", palette=annot_pal, order=method_order)` |
| R² scatter (r2 vs pcr by method) | Loop over methods, `ax.scatter` | `scatter_plot(df_ok, x="r2_RNA_BATCH", y="pcr_RNA_BATCH", hue="method", palette=method_pal)` |
| R² scatter by strat | Loop over strats | `scatter_plot(..., hue="strat", palette=strat_pal)` |
| R² scatter by post_rm | Loop over post_rm | `scatter_plot(..., hue="post_rm", palette=post_rm_pal)` |
| DSC scatter | Loop over methods | `scatter_plot(df_ok, x="dsc_RNA_BATCH", y="dsc_COHORT_LABEL", hue="method", size="r2_RNA_BATCH", palette=method_pal)` |
| PCR multi-covariate bar | Loop over covariates | `bar_plot(df_long, x="strat", y="pcr", hue="covariate", palette=annot_pal, order=HARSHNESS_ORDER)` |

#### §3.2 Group B — cells to rewrite

| Cell approx. | Current pattern | Replacement |
|---|---|---|
| kBET vs iLISI scatter | Loop over methods with optional strat marker | `scatter_plot(df_ok, x="kbet_acceptance_rate_RNA_BATCH", y="ilisi_norm_RNA_BATCH", hue="method", style="strat", palette=method_pal)` |
| Batch–biology trade-off scatter | Loop over imps | `scatter_p]=[ot(df_ok, x="asw_batch_norm_RNA_BATCH", y="asw_bio_norm_Major_group", hue="imp", palette=imp_pal)` |
| kBET by strat scatter | Loop over strats | `scatter_plot(df_ok, x="strat", y="kbet_acceptance_rate_RNA_BATCH", hue="strat", palette=strat_pal)` |

#### §3.3 Group C — cells to rewrite

| Cell approx. | Current pattern | Replacement |
|---|---|---|
| UMAP vs tSNE entropy correlation | Loop over batch columns | Use `sns.scatterplot` with `col` facet or a direct call to `scatter_plot` per batch column in a grid |

#### §3.4 Group D — cells to rewrite

| Cell approx. | Current pattern | Replacement |
|---|---|---|
| KS scatter (within-batch cohort effect) | Loop over methods | `scatter_plot(df_ok, x="ks_mean_D_RNA_BATCH", y="ks_cohort_within_batch_mean_D", hue="method", palette=method_pal)` |

#### §4 Composite scoring — cells to rewrite

| Cell approx. | Current pattern | Replacement |
|---|---|---|
| Pareto frontier scatter | Loop over methods | `scatter_plot(df_ok, x="score_batch_mixing", y="score_bio_preservation", hue="method", palette=method_pal)` with Pareto-optimal points highlighted via a separate `ax.scatter` call (acceptable since it is a post-processing overlay, not a group iteration) |

#### §2.5 Embeddings — cells to rewrite

The 2×3 embedding grid (Cell 041) currently uses `ax.scatter` per method in the PCA/UMAP/tSNE plots. Replace with:

```python
sns.scatterplot(data=embed_df, x="x", y="y", hue=hue_col,
                palette=pal, s=12, alpha=0.6, linewidth=0, ax=ax)
```

where `embed_df` has columns `x`, `y`, and all metadata columns from `df_ok`.

#### §2.5.3 Method similarity network

NetworkX plots cannot use seaborn. Retain the NetworkX drawing code unchanged — it is not a seaborn-replaceable plot.

### 2.4 What must NOT change

- Font size system: `FONT_BASE`, `FONT_TITLE`, `FONT_LABEL`, `FONT_TICK`, `FONT_LEGEND`, `FONT_ANNOT`, `FONT_SMALL`, `FONT_TINY` — keep all assignments.
- `ax.set_xlabel/ylabel/title` calls with explicit font sizes — keep these.
- `plt.savefig(..., bbox_inches="tight")` with SVG + PNG pair — keep in all helpers.
- `sns.despine()` — keep.
- `plt.rcParams["pdf.fonttype"]`, `sns.set_style("ticks")` — keep in Cell 001.
- `plot_multilevel_comparison` — keep unchanged. It already uses seaborn internally.
- All `try/except` guards around S3-dependent cells — keep.
- All markdown cells — never modify.
- All manually inserted analysis cells by Daniil — rewrite to call the new helpers with the same analysis logic, not from scratch.

---

## 3. Request R3 — Analysis of New Metrics (Groups J, K, I)

### 3.1 Group K — NA Retention in Scoring, Filtering, and Clustermap

#### 3.1.1 Add Group K to `col_meta` and `metric_colors` (§1 Cell 005)

The column taxonomy cell must recognise Group K keys:

```python
GROUP_MAP["K"] = [
    "n_genes_noNA", "pct_genes_noNA",
    "n_samples_noNA", "pct_samples_noNA",
    "n_genes_allNA", "n_samples_allNA",
    "n_na_cells", "pct_na_cells",
]
```

Group K is `metric_type = "other"` (same as Group E descriptives). It has no `annot_col` (matrix-level, not per-batch).

#### 3.1.2 Add Group K to `POLARITY` (§1 Cell 007 / 009)

```python
# Cell 007 auto-logic: add to Group K block
"pct_genes_noNA":    +1,   # more complete genes = better
"pct_samples_noNA":  +1,   # more complete samples = better
"n_genes_allNA":     -1,   # fewer completely-missing genes = better
"n_samples_allNA":   -1,
"n_na_cells":        -1,
"pct_na_cells":      -1,
# descriptive counts (not direction-comparable):
"n_genes_noNA":       0,
"n_samples_noNA":     0,
```

#### 3.1.3 Add Group K scoring metrics to `SCORE_WEIGHTS` (§4 Cell 113)

Add to the *Data Quality (5%)* component:

```python
"pct_genes_noNA":    0.8,   # reward methods that preserve gene completeness
"pct_samples_noNA":  0.5,   # reward sample completeness
"n_samples_allNA":  -1.0,   # hard penalty: any fully-NA sample is a structural failure
```

Keep the 5% component weight for Data Quality unchanged; normalise within the component.

#### 3.1.4 Add pre-clustermap filter based on `pct_samples_allNA` (§2 Cell 027)

**Goal:** allow the user to compare only harmonization attempts where no sample is completely missing (all genes are NA).

Add a filtering cell immediately before the main clustermap (after Cell 025, before Cell 027):

```python
# ── Cell 026b — Quality filter: exclude runs with fully-NA samples ──────────────
# Attempts where pct_samples_allNA > 0 have at least one completely empty sample,
# indicating a structural failure of the normalization method. Exclude them from the
# primary comparison. Set FILTER_ALLNA_SAMPLES = False to disable.

FILTER_ALLNA_SAMPLES = True   # user-editable flag

if FILTER_ALLNA_SAMPLES and "pct_samples_allNA" in df_ok.columns:
    mask_ok_na = df_ok["pct_samples_allNA"] == 0
    df_filtered = df_ok[mask_ok_na].copy()
    n_excluded = len(df_ok) - len(df_filtered)
    print(f"Quality filter: {n_excluded} attempts excluded "
          f"(pct_samples_allNA > 0), {len(df_filtered)} remain.")
else:
    df_filtered = df_ok.copy()
    print("Quality filter: disabled or pct_samples_allNA not available.")
```

All downstream clustermaps use `df_filtered` instead of `df_ok`. The main `df_ok` is preserved unchanged for Group K analysis itself (so the filtered-out attempts can be inspected).

#### 3.1.5 New §3.10 — NA Retention Analysis (5 new cells)

Add a new subsection after §3.9 Bubble Chart (after Cell 110):

**Cell §3.10.1 (markdown):** Section header: "§3.10 — Group K: NA Retention and Data Completeness"

**Cell §3.10.2 — Bar chart: `pct_genes_noNA` by method**

```python
# Horizontal bar chart: pct_genes_noNA (mean per method, sorted descending).
# Secondary y-axis: pct_na_cells (mean per method).
# Bar fill = method_pal; error bars = 95% CI across strategies.
```

Use `bar_plot(df_ok_long, x="method", y="pct_genes_noNA", hue="imp", palette=imp_pal, orient="h")`.

**Cell §3.10.3 — Heatmap: pct_na_cells per attempt**

Wide-format matrix: rows = methods, columns = strategies, values = `pct_na_cells` (mean across imputations). Annotated with actual % values. Color map: `YlOrRd` (more NA = more red). Saved as `k_na_cells_heatmap.svg`.

**Cell §3.10.4 — Boxplot: pct_genes_noNA split by strategy harshness**

```python
# sns.boxplot: x=method (sorted by pct_genes_noNA median),
#              hue=strat (colored by strat_pal), showfliers=False.
# Reference line at pct_genes_noNA = 80 (threshold below which the run is unreliable).
```

**Cell §3.10.5 — Failed-sample summary table**

Pivot table: how many attempts per `(method, strat)` have `n_samples_allNA > 0`. Styled with background colour (red = any failures). Saved as `k_failed_samples_table.csv`.

---

### 3.2 Group J + Group A — Per-PC R² × Variance-Explained Joint Analysis

**Context:** Group A stores `r2_pc{1..10}_{col}` (R² of RNA_BATCH in each individual PC) and Group J stores `pct_var_pc{1..10}` (fraction of total variance per PC). The joint quantity of interest is:

```
weighted_batch_r2_pci = r2_pc{i}_RNA_BATCH × pct_var_pc{i} / 100
```

This is "how much of total expression variance is explained jointly by RNA_BATCH in PC{i}?" — the most interpretable single-PC diagnostic for batch severity.

Add the following cells to §3.1 (after the existing per-PC R² heatmaps, approximately Cell 070):

**Cell §3.1.x1 — Joint heatmap: r2_pci × pct_var_pci**

```python
# Compute weighted_batch_r2_pci for each attempt
for i in range(1, 11):
    df_ok[f"wt_r2_pc{i}"] = (
        df_ok.get(f"r2_pc{i}_RNA_BATCH", np.nan)
        * df_ok.get(f"pct_var_pc{i}", np.nan) / 100
    )

# Build wide matrix: rows = methods (sorted by sum of wt_r2_pc*),
#                    columns = PC1..10
# Two sub-heatmaps side-by-side:
# Left: r2_pc{i}_RNA_BATCH (how much batch drives each PC)
# Right: pct_var_pc{i} (how much variance each PC carries)
# Both on same row order; unified row color strip = method_pal.
```

Two-panel figure (left panel raw R², right panel raw pct_var). Row sorting by descending `sum(wt_r2_pc*)`. Save as `a_joint_r2_pct_var_heatmap.svg/.pdf`.

**Cell §3.1.x2 — Weighted batch R² heatmap**

Single heatmap: rows = methods, columns = PC1–10, values = `wt_r2_pc{i}`. Colormap `Reds` (intensity proportional to batch contribution in that PC weighted by its information content). Annotate cells with `wt_r2_pc{i}` values where > 0.01. Save as `a_weighted_batch_r2_heatmap.svg/.pdf`.

Add `sum(wt_r2_pci)` as a new derived column to `df_ok` and include it in the ranking table as an additional quality indicator (how much total variance is batch-driven, weighted by PC informativeness).

---

### 3.3 Group I — WaterMelon Score Analysis (New §3.11)

**Data guard:** Wrap all §3.11 cells in:

```python
WM_COLS = [c for c in df_ok.columns if c.startswith("wm_") and c != "wm_subsampled"]
if not WM_COLS:
    raise RuntimeError(
        "Group I (WaterMelon) columns not found in CSV. "
        "Run the WM parallel pass (run_metrics_parallel.py --skip-wm False) first."
    )
```

**Cell §3.11.1 (markdown):** Section header: "§3.11 — Group I: WaterMelon Score Analysis"

**Cell §3.11.2 — WM correlation matrix**

```python
# Spearman correlation between all wm_* columns (both batch and biology variants).
# Annotated heatmap (heatmap_plot); colormap diverging (coolwarm), center=0.
# Row/col color strip = annot_pal (batch cols = sepia, bio cols = teal).
# Expected: batch columns correlate with each other; bio columns correlate with each other;
#           low cross-correlation between batch and bio clusters.
```

Save as `i_wm_correlation_matrix.svg`.

**Cell §3.11.3 — WM vs local metrics comparison**

Two scatter plots side by side:

- Left: `wm_mean_batch` (x) vs `kbet_acceptance_rate_RNA_BATCH` (y), colored by method. Tests whether WM batch score tracks kBET (both local / neighborhood-based).
- Right: `wm_mean_batch` (x) vs `r2_RNA_BATCH` (y), colored by method. Tests whether WM batch score tracks global R² (different regime: global covariance vs hierarchical clustering).

Annotate Pearson r in each panel. Expected result: WM is closer to kBET (both capture local clustering structure) than to R² (which is a global linear decomposition metric).

Save as `i_wm_vs_local_global.svg`.

**Cell §3.11.4 — WM batch–biology trade-off scatter**

```python
scatter_plot(
    df_ok, x="wm_mean_batch", y="wm_mean_bio",
    hue="method", style="strat",
    palette=method_pal,
    xlabel="WM batch score (lower = better mixing)",
    ylabel="WM biology score (higher = biology preserved)",
    save_path="i_wm_batch_bio_tradeoff",
)
# Add diagonal reference line: wm_mean_bio = wm_mean_batch
# Points above diagonal = biology better preserved than batch is mixed (desirable).
```

**Cell §3.11.5 — wm_ratio_bio_batch vs composite_score**

```python
scatter_plot(
    df_ok, x="composite_score", y="wm_ratio_bio_batch",
    hue="method", palette=method_pal,
    xlabel="Composite score (all groups A–H)",
    ylabel="WM ratio bio/batch",
    save_path="i_wm_ratio_vs_composite",
)
# Annotate Pearson r.
# If high correlation: WM is consistent with the composite score → supports using WM as a lighter proxy.
# If low: WM captures different information (likely: WM is more sensitive to hierarchical structure).
```

**Cell §3.11.6 — Add WM to scoring (optional toggle)**

Add `WM_SCORING_ENABLED` boolean flag (default `False`). When `True`, append WM metrics to `SCORE_WEIGHTS`:

```python
WM_SCORE_ADDITIONS = {
    "wm_mean_batch":   1.5,   # lower WM batch = good (POLARITY = -1)
    "wm_mean_bio":     1.0,   # higher WM bio = good (POLARITY = +1)
    "wm_ratio_bio_batch": 1.0,  # higher ratio = good (POLARITY = +1)
}
```

This allows Daniil to see whether including WM changes the top-10 ranking. If `WM_SCORING_ENABLED = False`, the scoring is identical to v1.

---

## 4. Request R4 — Add `I_rare_batches_removed` Strategy

### 4.1 Palette update (§1 Cell 018)

Add to `strat_pal`:

```python
"I_rare_batches_removed": "#7b4f9e",  # medium purple — sits between G (blue) and H (teal) family
```

Rationale: `I_rare_batches_removed` is conceptually between `G_affymetrix_only` and `H_affymetrix_extended` in terms of selectivity: it removes rare batches regardless of platform. A distinct purple avoids confusion with the existing blue/teal cluster.

Add to `attempt_colors`: the `strat` column will automatically pick up the new color once `strat_pal` is updated, since `attempt_colors` is built by mapping `strat_pal` over `df_ok.strat`.

### 4.2 `ALL_STRATS` update

In the cell defining `ALL_STRATS`, append `"I_rare_batches_removed"` after `"H_affymetrix_extended"`:

```python
ALL_STRATS = [
    "S0_no_removal", "A_confirmed_bad", "B_extended_bad",
    "C_rnaseq_only", "D_malignant_only",
    "E1_iterative_r1", "E2_iterative_r2", "E3_iterative_r3",
    "F_microarray_only", "G_affymetrix_only", "H_affymetrix_extended",
    "I_rare_batches_removed",
]
```

### 4.3 `HARSHNESS_ORDER` update

`I_rare_batches_removed` keeps all batches with ≥ 50 samples. In terms of sample exclusion aggressiveness it is **less harsh than H_affymetrix_extended** (which restricts to Affymetrix only) but **more selective than A_confirmed_bad** (which removes only explicitly bad batches). Place it after `G_affymetrix_only` in the harshness ordering:

```python
HARSHNESS_ORDER = [
    "S0_no_removal__strict",
    "S0_no_removal__knn",
    "S0_no_removal__softimpute",
    "A_confirmed_bad__strict",
    "A_confirmed_bad__knn",
    "A_confirmed_bad__softimpute",
    ...
    "G_affymetrix_only__strict",
    "G_affymetrix_only__knn",
    "G_affymetrix_only__softimpute",
    "I_rare_batches_removed__strict",    # ← new
    "I_rare_batches_removed__knn",
    "I_rare_batches_removed__softimpute",
    "H_affymetrix_extended__strict",
    "H_affymetrix_extended__knn",
    "H_affymetrix_extended__softimpute",
]
```

### 4.4 Clustermaps

No code change is required beyond the palette update and `ALL_STRATS` extension. The clustermap `attempt_colors` DataFrame is rebuilt from `df_ok.strat`, so the new strategy will appear with its correct purple color automatically.

### 4.5 All boxplots, bar charts, scatter plots, and multilevel comparisons

The seaborn-based helpers introduced in R1 will automatically include `I_rare_batches_removed` in all group-by-strat plots since they operate on `df_ok` which includes the new strategy. No per-plot change is required.

### 4.6 Data-availability guard

If `"I_rare_batches_removed"` is not yet present in `df_ok.strat`:

```python
AVAIL_STRATS = [s for s in ALL_STRATS if s in df_ok["strat"].unique()]
if "I_rare_batches_removed" not in AVAIL_STRATS:
    import warnings
    warnings.warn(
        "I_rare_batches_removed not found in CSV. "
        "Run the preparation and normalization pipeline first, then re-aggregate."
    )
```

Use `AVAIL_STRATS` instead of `ALL_STRATS` wherever ordering is applied.

---

## 5. Request R5 — Shambhala Methods: Palette, Annotations, Separate Analysis

### 5.1 What Shambhala methods look like in the data

Method names follow the pattern `shambhala_{p_key}_{q_key}` where `p_key` ∈ {P0std, ANTE, GTExAffy, NBlegacy, NBGPL570, NBKass, NBRNAseq, NBext, Oncobox} and `q_key` ∈ {Q0std, QNBKass}. There are 18 variants. They appear in `df_ok.method` just like any other normalization method.

### 5.2 Parse Shambhala metadata from method names

Add to §1 (after the palette construction cell):

```python
# ── Shambhala method metadata ────────────────────────────────────────────────
def _parse_shambhala_method(method: str) -> tuple[str | None, str | None]:
    """Return (p_key, q_key) for shambhala methods; (None, None) for others."""
    if not method.startswith("shambhala_"):
        return None, None
    parts = method.removeprefix("shambhala_").split("_")
    # p_key ends before the Q component; Q keys start with Q
    q_idx = next((i for i, p in enumerate(parts) if p.startswith("Q")), None)
    if q_idx is None:
        return "_".join(parts), None
    return "_".join(parts[:q_idx]), "_".join(parts[q_idx:])

df_ok["is_shambhala"] = df_ok["method"].str.startswith("shambhala_")
df_ok["shambhala_p_key"] = df_ok["method"].apply(lambda m: _parse_shambhala_method(m)[0])
df_ok["shambhala_q_key"] = df_ok["method"].apply(lambda m: _parse_shambhala_method(m)[1])
```

### 5.3 Shambhala palette design

**Goal:** colors must signal "these are Shambhala variants" (clearly clustered visually) while distinguishing 9 P-dataset variants with the 2 Q-dataset variants cross-encoded.

**Approach:** Use the `tab20b` palette for Shambhala P-dataset colors (blueish–purple family, 9 entries), with Q variant encoded by marker shape (not color) and by line-style:

```python
# Shambhala P-dataset colors (drawn from tab20b cool-tone section)
_SHAMB_P_COLORS = plt.cm.tab20b(np.linspace(0.0, 0.65, 9))   # 9 blue-purple shades
SHAMBHALA_P_KEYS = ["P0std", "ANTE", "GTExAffy", "NBlegacy", "NBGPL570",
                    "NBKass", "NBRNAseq", "NBext", "Oncobox"]
shambhala_p_pal = dict(zip(SHAMBHALA_P_KEYS, [to_hex(c) for c in _SHAMB_P_COLORS]))

# Shambhala Q-reference line style (encoded as alpha shift):
SHAMBHALA_Q_KEYS = {"Q0std": 1.0, "QNBKass": 0.55}   # full opacity vs. faded

# In method_pal (the primary method color strip), add near-black for all Shambhala
# methods. The ~30 existing method colors are preserved unchanged — only Shambhala
# entries are appended.
SHAMBHALA_METHOD_COLOR = "#1a1a1a"   # near-black: uniform identity for all Shambhala methods
for method in df_ok["method"].unique():
    if method.startswith("shambhala_"):
        method_pal[method] = SHAMBHALA_METHOD_COLOR

# Separate Shambhala detail strip — used as an ADDITIONAL col_colors column in clustermaps.
# Non-Shambhala methods = white (#ffffff); Shambhala methods = P-key color from shambhala_p_pal.
# Purpose: reveals calibration-dataset structure within the Shambhala block without
# cluttering the main method_pal annotation with 18 new hues.
shambhala_method_pal = {
    method: (
        shambhala_p_pal.get(_parse_shambhala_method(method)[0], SHAMBHALA_METHOD_COLOR)
        if method.startswith("shambhala_")
        else "#ffffff"   # white = not Shambhala
    )
    for method in df_ok["method"].unique()
}
```

In clustermaps, the existing `method_pal` is used for the main method annotation strip (Shambhala methods appear as near-black, visually clustering as one group). The `shambhala_method_pal` dict is added as a **separate additional `col_colors` column** (`shambhala_detail`) that distinguishes Shambhala P-dataset variants by color within the Shambhala block, while showing white for all non-Shambhala methods.

### 5.4 New column in `attempt_colors`: `is_shambhala`

```python
# Binary strip: shambhala = dark indigo, non-shambhala = light grey
SHAMBHALA_BINARY_PAL = {True: "#3d1a78", False: "#e8e8e8"}
attempt_colors["is_shambhala"] = df_ok["is_shambhala"].map(SHAMBHALA_BINARY_PAL)
```

This binary strip is added to **all clustermap `col_colors`** as an extra row at the top (or bottom), so the Shambhala block is immediately visually identifiable.

### 5.5 Clustermap update

In all `sns.clustermap(...)` calls, update `col_colors` to include the `is_shambhala` strip:

```python
# Also populate the shambhala_detail strip from shambhala_method_pal before concatenating
attempt_colors["shambhala_detail"] = df_ok["method"].map(shambhala_method_pal)
col_colors_extended = pd.concat(
    [attempt_colors[["strat","imp","method","post_rm"]],
     attempt_colors[["is_shambhala"]],
     attempt_colors[["shambhala_detail"]]],
    axis=1
)
```

Pass `col_colors=col_colors_extended` to every clustermap.

### 5.6 Data-availability guard for Shambhala

```python
SHAMBHALA_AVAIL = df_ok["is_shambhala"].any()
if not SHAMBHALA_AVAIL:
    import warnings
    warnings.warn(
        "No Shambhala methods found in the CSV. "
        "Sections §3.12 will be skipped. "
        "Run the Shambhala benchmark and re-aggregate metrics_comprehensive.csv."
    )
```

Wrap all §3.12 cells with `if SHAMBHALA_AVAIL:`.

### 5.7 New §3.12 — Shambhala-Only Analysis (8 new cells)

**Cell §3.12.1 (markdown):** Section header and brief description of the 18 Shambhala variants.

**Cell §3.12.2 — Shambhala mini-clustermap**

```python
df_shambhala = df_ok[df_ok["is_shambhala"]].copy()
# Clustermap: rows = scoring_cols, columns = shambhala methods only.
# Row colors = metric_colors; col colors = shambhala_p_pal × Q shape.
# Layout identical to main clustermap but restricted to Shambhala.
# Purpose: how consistent are Shambhala variants with each other?
# Save as: shambhala_clustermap.pdf
```

**Cell §3.12.3 — Shambhala ranking table**

Styled table of all 18 variants ranked by composite score, with columns:
`p_key | q_key | composite_score | score_batch_mixing | score_bio_preservation | r2_RNA_BATCH | kbet | wm_mean_batch`.

**Cell §3.12.4 — P-key impact on batch metrics**

```python
bar_plot(
    df_shambhala, x="shambhala_p_key", y="r2_RNA_BATCH",
    hue="shambhala_q_key", palette={"Q0std": "#3d7ab5", "QNBKass": "#b03d3d"},
    order=sorted(df_shambhala["shambhala_p_key"].unique()),
    title="Shambhala: batch removal (R² RNA_BATCH) by P-calibration dataset",
    ylabel="r2_RNA_BATCH (lower = better)",
    save_path="shambhala_r2_by_p_key",
)
```

**Cell §3.12.5 — P-key impact on biology preservation**

Same structure as §3.12.4 but `y="asw_bio_norm_Diagnosis_cell_type_unified"`.

**Cell §3.12.6 — Q-key comparison scatter**

```python
# For each P-key, draw a line connecting Q0std vs QNBKass results:
scatter_plot(
    df_shambhala, x="wm_mean_batch", y="wm_mean_bio",
    hue="shambhala_p_key", style="shambhala_q_key",
    palette=shambhala_p_pal,
    save_path="shambhala_wm_q_comparison",
)
# Adding line segments connecting same P-key, different Q variants.
```

**Cell §3.12.7 — Shambhala vs best non-Shambhala comparison**

Two-panel figure:
- Left: strip + box comparing `composite_score` for: Shambhala all, top-5 non-Shambhala, MNN, FSQN R, raw.
- Right: same for `r2_RNA_BATCH` only.

Uses `sns.boxplot` + `sns.stripplot`.

**Cell §3.12.8 — Shambhala batch-biology trade-off vs non-Shambhala**

```python
# Separate scatter with different alpha/s for Shambhala vs non-Shambhala.
fig, ax = plt.subplots(figsize=(10, 7))
# Non-shambhala: grey, s=15, alpha=0.3
sns.scatterplot(
    data=df_ok[~df_ok["is_shambhala"]],
    x="score_batch_mixing", y="score_bio_preservation",
    color="#aaaaaa", s=15, alpha=0.3, ax=ax, label="Other methods"
)
# Shambhala: colored by p_key, s=60, alpha=0.8
sns.scatterplot(
    data=df_shambhala,
    x="score_batch_mixing", y="score_bio_preservation",
    hue="shambhala_p_key", style="shambhala_q_key",
    palette=shambhala_p_pal, s=60, alpha=0.85, ax=ax
)
add_legend_outside(ax)
plt.savefig(...)
```

---

## 6. Request R6 — Harshness Palette and §3.13 Impact Analysis

### 6.1 Defining harshness levels

"Harshness" describes how aggressively a normalization method transforms or warps the original expression values. A low-harshness method applies a gentle global shift/scale; a high-harshness method applies sample-level corrections that can substantially alter relative gene expression.

**Notebook implementation note — markdown cell §3.13.1:** The first cell of §3.13 must be a markdown cell containing the full harshness classification table (method key | tier | one-line justification | DOI link). Use the following reference list when writing that cell:

| Method(s) | Paper | DOI |
|---|---|---|
| `03_limma` | Ritchie et al. (2015) *Nucleic Acids Res* | 10.1093/nar/gkv007 |
| `04_sva` | Leek et al. (2012) *Bioinformatics* | 10.1093/bioinformatics/bts034 |
| `05_combat` `07_pycombat` | Johnson et al. (2007) *Biostatistics* | 10.1093/biostatistics/kxl005 |
| `06_combat_seq` `08_inmoose_combatseq` | Zhang et al. (2020) *NAR Genomics Bioinform* | 10.1093/nargab/lqaa078 |
| `09_ruv` | Risso et al. (2014) *Nature Biotechnology* | 10.1038/nbt.2931 |
| `10_mnn` | Haghverdi et al. (2018) *Nature Biotechnology* | 10.1038/nbt.4091 |
| `11_harmony` | Korsunsky et al. (2019) *Nature Methods* | 10.1038/s41592-019-0619-0 |
| `12_scanorama` | Hie et al. (2019) *Nature Biotechnology* | 10.1038/s41587-019-0113-3 |
| `14_qsmooth` | Hicks & Irizarry (2018) *Biostatistics* | 10.1093/biostatistics/kxx028 |
| `15_fsqn_py` `16_fsqn_r` | Franks et al. (2018) *Bioinformatics* | 10.1093/bioinformatics/bty164 |
| `17_quantile` | Bolstad et al. (2003) *Bioinformatics* | 10.1093/bioinformatics/19.2.185 |
| `19_tdm` | Thompson et al. (2016) *BMC Bioinformatics* | 10.1186/s12859-016-1228-7 |
| `21_harmonizr` | Brombacher et al. (2022) *Cell Rep Methods* | 10.1016/j.crmeth.2022.100294 |
| `22_tmm` | Robinson & Oshlack (2010) *Genome Biology* | 10.1186/gb-2010-11-3-r25 |
| `23_vst` | Love et al. (2014) *Genome Biology* | 10.1186/s13059-014-0550-8 |
| `24_peer_k10` | Stegle et al. (2012) *PLoS Comput Biol* | 10.1371/journal.pcbi.1002240 |
| `26_xpn` | Shabalin et al. (2008) *Bioinformatics* | 10.1093/bioinformatics/btn131 |
| `27_dwd` | Benito et al. (2004) *Bioinformatics* | 10.1093/bioinformatics/btg404 |
| `29_combat_ref` | Johnson et al. (2007) *Biostatistics* | 10.1093/biostatistics/kxl005 |
| `30_recombat` | Behdenna et al. (2021) *NAR Genomics Bioinform* | 10.1093/nargab/lqab084 |
| `31_ruv3prps` | Molania et al. (2022) *Nucleic Acids Res* | 10.1093/nar/gkac101 |
| `34_arsyn` | Tarazona et al. (2012) *Bioinformatics* | 10.1093/bioinformatics/bts512 |
| `37_fabatch` | Hornung et al. (2016) *Briefings Bioinform* | 10.1093/bib/bbv027 |
| `38_harman` | Oytam et al. (2016) *BMC Bioinformatics* | 10.1186/s12859-016-1096-1 |
| WaterMelon metrics | Zolotovskaya et al. (2020) *Genes* | 10.3390/genes11030305 |

Methods `01_raw`, `02_median_scaling`, `18_rank`, `25_angel`, `28_npn`, `33_amdbnorm`, `39_procrustes` have no single defining external publication or are BostonGene-internal; substitute a brief algorithmic description instead of a DOI. Methods `32_deepmnn`, `35_dasc`, `36_explobatch` are skipped in the current benchmark — note why in the table.

**Harshness level assignment** (reviewed and approved 2026-05-17):

```python
# Levels: "low", "medium", "high"
# Tiers are cross-referenced with bench_shared.py METHODS dict (authoritative source),
# plan_more_normalization.md, and new_methods_implementation_260506.md.
# All 39 benchmark methods and the 18 Shambhala cross-product variants are listed.

HARSHNESS_LEVEL_MAP: dict[str, str] = {

    # ── Low harshness: minimal or linear per-batch transformation ─────────────
    # These methods apply a single scalar (or no) correction per batch/sample.
    # They do not reshape the distribution of expression values.

    "01_raw":               "low",
    # No transformation. Identity passthrough; absolute baseline.

    "02_median_scaling":    "low",
    # Per-batch additive shift to the global median. Single scalar per batch;
    # preserves relative gene-level variation and within-batch covariance entirely.

    "03_limma":             "low",
    # limma::removeBatchEffect: fits and subtracts batch intercepts by linear
    # regression. Preserves within-batch gene covariance; only changes cross-batch means.

    "04_sva":               "low",
    # SVA falls back to uncorrected if 0 surrogate variables detected.
    # With well-annotated batches, very few additional latent SVs are found →
    # net correction is negligible. Classified low because correction magnitude
    # is proportional to the number of unmodelled SVs, which is small here.

    "22_tmm":               "low",
    # TMM library-size factor via edgeR: per-sample multiplicative scaling only;
    # no distribution reshaping. RNA-seq only (raises NotImplementedError on mixed data).

    "23_vst":               "low",
    # DESeq2 VST: monotonic per-gene variance-stabilizing function applied uniformly;
    # does not correct batch, only stabilizes variance. RNA-seq only.

    # ── Medium harshness: batch-aware models that estimate and remove structured batch components ──
    # These methods model batch effects explicitly and subtract them, but are constrained by
    # empirical Bayes shrinkage, latent factor structure, or geometric properties.

    "05_combat":            "medium",
    # ComBat EB parametric: estimates per-gene batch means and variances with
    # empirical Bayes shrinkage. More aggressive than limma but shrinkage
    # prevents extreme per-gene corrections.

    "06_combat_seq":        "medium",
    # ComBat-seq for count data: negative-binomial model of batch effects;
    # constrained by count-data structure (no negative values).

    "07_pycombat":          "medium",
    # Python port of ComBat EB. Identical algorithm to 05_combat.

    "08_inmoose_combatseq": "medium",
    # pycombat_seq via the inmoose package. Same algorithm as 06_combat_seq.

    "09_ruv":               "medium",
    # RUVg with 10 housekeeping negative-control genes. Estimates one latent
    # unwanted variation factor; constrained by the small number of control genes.

    "10_mnn":               "medium",
    # MNN: mutual nearest-neighbor correction vectors interpolated in gene space.
    # Local correction — only nearby cells from different batches are corrected;
    # global gene-level distribution is not forced. Best overall benchmark winner (as of 2026-05-17).

    "11_harmony":           "medium",
    # Harmony: iterative PCA-space soft-clustering correction → inverse-projected.
    # Tends not to distort gene-level expression severely for bulk data.

    "12_scanorama":         "medium",
    # Scanorama: panoramic graph-stitching in PCA space → inverse-projected to
    # gene space. Correction is done in a low-dimensional embedding; gene-space
    # distortion is moderate because inverse-projection averages over many PCs.

    "13_fsmvn":             "medium",
    # Feature-specific mean-variance normalization: adjusts mean and variance per
    # gene independently toward a reference; not a full distributional transform,
    # but changes gene-level spread across batches.

    "21_harmonizr":         "medium",
    # HarmonizR: NA-aware ComBat or limma with block-averaging for multi-platform
    # NA structure. ComBat + NA interpolation = moderate distortion.

    "24_peer_k10":          "medium",
    # PEER with k=10 latent factors: estimates and removes residual technical
    # variation. Skipped in current benchmark (package unavailable for R 4.5).

    "27_dwd":               "medium",
    # Distance-weighted discrimination via DWDLargeR: finds a separation
    # hyperplane and projects each batch perpendicular to it. Iterative but
    # constrained by the geometric margin of the DWD solution.

    "29_combat_ref":        "medium",
    # ComBat with explicit reference batch (RNASeq_FF_PolyA unchanged): only
    # adjusts non-reference batches toward the reference distribution.

    "30_recombat":          "medium",
    # reComBat: robust ComBat with downweighting of outlier genes. Same EB
    # structure as ComBat but more resistant to high-leverage genes.

    "31_ruv3prps":          "medium",
    # RUV-III-PRPS: uses within-sample pseudo-replicates to estimate unwanted
    # variation. More principled than RUVg but same order of correction magnitude.

    "32_deepmnn":           "medium",
    # deepMNN. Skipped in current benchmark (scRNA-seq only; not applicable to bulk).

    "34_arsyn":             "medium",
    # ARSyNseq via NOISeq: removes systematic batch-related count-level artifacts;
    # less extreme than FSQN or quantile normalization.

    "35_dasc":              "medium",
    # DASC. Skipped in current benchmark (returns cluster assignments, not
    # corrected expression values).

    "36_explobatch":        "medium",
    # exploBATCH. Skipped in current benchmark (fMM dependency removed from GitHub).

    "37_fabatch":           "medium",
    # FAbatch batchadjust(type="among"): adjusts between-batch variation only;
    # preserves within-batch structure.

    "38_harman":            "medium",
    # Harman with limit=0.1: PCA-based correction with a conservative constraint
    # (only 10% of batch variance removed per iteration); limit prevents over-correction.

    # ── High harshness: aggressive distribution-reshaping or iterative component removal ──
    # These methods force the full or per-gene distribution to match a reference,
    # or iteratively remove variance components, substantially altering expression values.

    "14_qsmooth":           "high",
    # qsmooth: quantile normalization with batch-weighted quantile-function smoothing.
    # Reshapes the full per-sample distribution toward a weighted consensus quantile;
    # more extreme than any per-sample scaling.

    "15_fsqn_py":           "high",
    # FSQN Python re-implementation: per-gene quantile mapping of each non-reference
    # batch to the reference CDF. Forces per-gene distributional identity to reference.

    "16_fsqn_r":            "high",
    # FSQN R (Franks et al. 2018): same algorithm as 15_fsqn_py using the original
    # R package. Per-gene distributional forcing is aggressive; best visual result
    # in the benchmark when target = RNASeq_FF_PolyA.

    "17_quantile":          "high",
    # Standard quantile normalization: forces ALL samples to share an identical
    # quantile profile (rank-sorted global mean). This is NOT a linear transform —
    # it replaces each value with the mean of its rank class, completely reshaping
    # the distribution and destroying all between-sample distributional differences,
    # including biological ones.

    "18_rank":              "high",
    # Fractional rank per sample: converts all expression values to fractional
    # ranks in [0, 1]. Destroys absolute expression magnitude and any continuous
    # variation within a sample.

    "19_tdm":               "high",
    # TDM (target distribution matching): maps all samples to a target (reference
    # batch) distribution via per-sample distributional forcing; similar to FSQN
    # but applied globally per sample rather than per gene.

    "20_shambhala":         "high",
    # Original Shambhala (Octave-based): CuBlock + quantile normalization applied
    # in multiple sequential steps toward the calibration dataset distribution.

    "25_angel":             "high",
    # ANGEL: cross-platform gene-level variance filtering. Removes genes whose
    # cross-platform variance exceeds a threshold; reduces the gene space to
    # platform-invariant signal only. High: alters gene selection and rescales.

    "26_xpn":               "high",
    # XPN (cross-platform normalization): pure Python percentile interpolation
    # per gene per batch toward reference. Per-gene per-batch percentile mapping
    # fully forces each gene's CDF per batch.

    "28_npn":               "high",
    # NPN nonparanormal transform via huge::npn(func="truncation"): fits a per-gene
    # Gaussian copula via rank-based transformation. Full per-gene distributional
    # reshaping.

    "33_amdbnorm":          "high",
    # AMDBNorm 3-step (genDistData → polyFit → AMDBNorm): multi-step non-linear
    # transformation of the expression distribution.

    "39_procrustes":        "high",
    # BostonGene Procrustes: orthogonal rotation of the expression matrix to align
    # with a reference (RNA-seq only). Modifies the gene–gene correlation structure
    # globally via an estimated rotation matrix.

    # ── New Shambhala cross-product variants (all high) ───────────────────────
    # All 18 variants (9 P-datasets × 2 Q-datasets) apply per-sample calibration
    # to a reference P-dataset using quantile normalization internally — same
    # mechanism and harshness as 20_shambhala.
    **{m: "high" for m in df_ok["method"].unique() if m.startswith("shambhala_")},
}
```

**Note on classification decisions:** Tiers are taken directly from the `bench_shared.py` METHODS dict (the authoritative source). Key corrections versus the earlier plan draft:

- **Quantile normalization** (`17_quantile`) → **high** (not low): forces all samples to an identical rank-sorted distribution, which is not a linear transform. It completely reshapes the distribution.
- **FSQN R** (`16_fsqn_r`) → **high** (not medium): per-gene CDF forcing is distributional, not linear scaling.
- **SVA** (`04_sva`) → **low** (not high): with well-annotated batches, finds very few additional latent SVs and falls back to uncorrected when zero SVs are found.
- **HarmonizR** (`21_harmonizr`) → **medium** (not high): wraps ComBat/limma with NA-block handling; does not perform iterative variance component removal.
- **New Shambhala variants** → **high** (not medium): use quantile normalization internally, same mechanism as `20_shambhala`.

Harshness classification reviewed and approved (2026-05-17).

### 6.2 Harshness palette

```python
HARSHNESS_PAL = {
    "low":    "#2ecc71",   # green
    "medium": "#f39c12",   # amber/yellow-orange
    "high":   "#e74c3c",   # red
}
```

### 6.3 Add `harshness_level` to `attempt_colors`

```python
df_ok["harshness_level"] = df_ok["method"].map(HARSHNESS_LEVEL_MAP).fillna("medium")
attempt_colors["harshness"] = df_ok["harshness_level"].map(HARSHNESS_PAL)
```

### 6.4 Add harshness strip to all clustermaps

In all `sns.clustermap(...)` calls, add the `harshness` column to `col_colors`:

```python
col_colors_extended = pd.concat(
    [attempt_colors[["strat","imp","method","post_rm"]],
     attempt_colors[["is_shambhala"]],        # R5: binary Shambhala strip
     attempt_colors[["shambhala_detail"]],    # R5: P-key color detail strip
     attempt_colors[["harshness"]]],           # R6: harshness level strip
    axis=1
)
```

Order of strip rows (top to bottom): `strat | imp | method | post_rm | is_shambhala | shambhala_detail | harshness`.

### 6.5 Add harshness to the `attempt_colors` plot_palette visualization

In the palette swatch cell, add a horizontal swatch for `HARSHNESS_PAL` and a strip bar showing the harshness distribution across all methods.

### 6.6 New §3.13 — Harshness Impact Analysis (6 new cells)

**Cell §3.13.1 (markdown):** Section header and definition of harshness levels.

**Cell §3.13.2 — Harshness vs all metric groups: grouped boxplots**

One figure per metric group (A–H), 3-panel layout (low/medium/high):

```python
for group_name, group_cols in GROUP_MAP.items():
    df_long_group = df_ok[["harshness_level"] + [c for c in group_cols if c in df_ok.columns]]
    df_long_group = df_long_group.melt(id_vars="harshness_level", var_name="metric", value_name="value")
    g = sns.FacetGrid(df_long_group, col="metric", col_wrap=4, height=4, sharex=False)
    g.map_dataframe(sns.boxplot, x="harshness_level", y="value",
                    palette=HARSHNESS_PAL, order=["low","medium","high"],
                    showfliers=False)
    g.fig.suptitle(f"Group {group_name}: metric distributions by harshness level",
                   y=1.02, fontsize=FONT_TITLE)
    g.savefig(FIGURES_DIR / f"harshness_group_{group_name}_boxplots.svg")
```

**Cell §3.13.3 — Harshness × metric-type interaction (local vs global)**

```python
# For each run, compute mean score within local_neighborhood metrics and within
# global_distance metrics. Plot paired scatter by harshness level.
df_ok["mean_local"] = df_ok[[c for c in scoring_cols if METRIC_TYPE_MAP.get(c) == "local_neighborhood"]].mean(axis=1)
df_ok["mean_global"] = df_ok[[c for c in scoring_cols if METRIC_TYPE_MAP.get(c) == "global_distance"]].mean(axis=1)

scatter_plot(
    df_ok, x="mean_global", y="mean_local",
    hue="harshness_level", style="strat",
    palette=HARSHNESS_PAL,
    xlabel="Mean score: global distance metrics",
    ylabel="Mean score: local neighborhood metrics",
    title="Local vs global performance by harshness level",
    save_path="harshness_local_vs_global",
)
# Annotation: Pearson r per harshness group.
```

**Cell §3.13.4 — Harshness × strategy interaction**

`plot_multilevel_comparison` called twice:
1. `df_ok`, `metric_col="composite_score"`, `group_col="harshness_level"` — does harshness level matter?
2. Same restricted to `strat in ["C_rnaseq_only", "G_affymetrix_only", "I_rare_batches_removed"]` — does platform-restriction interact with harshness?

**Cell §3.13.5 — Harshness vs batch score broken down by removal strategy**

Heatmap: rows = harshness level × batch removal strategy (12 combinations), columns = key batch metrics (r2_RNA_BATCH, kbet, asw_batch_norm_RNA_BATCH). Cell values = median metric per group. Annotated with counts (n attempts). Colormap: RdYlGn. Saved as `harshness_by_strategy_heatmap.svg`.

**Cell §3.13.6 — Harshness score summary table**

Styled pivot table: rows = harshness level, columns = {mean_composite, mean_batch_mixing, mean_bio_preservation, mean_r2_RNA_BATCH, mean_kbet, n_attempts}. Background gradient. Exported as `harshness_summary_table.csv`.

---

## 7. All Changes to §1 Setup Cell (Summary)

The following items are added to or changed in existing §1 cells. All changes go into `harmonization_metrics_analysis_v2.ipynb`.

### 7.1 Cell 003 — Load CSV and build `df_ok`

- Update CSV path to `metric_tables/metrics_comprehensive_260513.csv` (fix the known path mismatch from the overview).
- Add `AVAIL_STRATS` derivation immediately after `df_ok` is built.
- Add derived columns: `is_shambhala`, `shambhala_p_key`, `shambhala_q_key`, `harshness_level`.

### 7.2 Cell 005 — Column taxonomy

- Extend `GROUP_MAP` with K entries.
- Extend `METRIC_TYPE_MAP` with K keys (`other`).
- `col_meta` will automatically include K once GROUP_MAP is extended.

### 7.3 Cell 007 — Polarity assignment

- Add Group K polarities as described in §3.1.2 above.

### 7.4 Cell 009 — Manual polarity overrides

- Add any Group K overrides needed (e.g., `n_genes_noNA` → 0 since it is a count without natural direction for scoring comparison).

### 7.5 Cell 018 — Palette construction

Add to this cell (or a new Cell 018b):
1. `strat_pal["I_rare_batches_removed"] = "#7b4f9e"`.
2. `shambhala_p_pal` dict (9 entries from tab20b cool-tone range).
3. `SHAMBHALA_METHOD_COLOR = "#1a1a1a"` added to existing `method_pal` for all Shambhala methods (existing ~30 method colors unchanged); `shambhala_method_pal` dict as a separate strip (non-Shambhala = white, Shambhala = P-key color).
4. `HARSHNESS_PAL` dict.
5. `SHAMBHALA_BINARY_PAL` dict.
6. Update `attempt_colors` to include `is_shambhala`, `shambhala_detail`, and `harshness` columns.

### 7.6 Cell 015 or new Cell 015b — Plotting helpers

Add `scatter_plot`, `bar_plot`, `heatmap_plot` helper functions as specified in §2.2.

---

## 8. Notebook Structure After All Changes

### New section map (additions to Part 1)

| Section | Cells (approx.) | Status in v2 |
|---|---|---|
| §1 Setup | 000–025 | Updated (palette, derived cols, helpers, quality filter) |
| §2 Full clustermap | 026–042 | Updated (new col_colors strips) |
| §3.1 Group A | 044–070 | Updated + 2 new joint J/A cells |
| §3.2 Group B | 071–090 | Refactored to seaborn helpers |
| §3.3 Group C | 091–093 | Refactored |
| §3.4 Group D | 094–097 | Refactored |
| §3.5 Group E | 098–101 | Unchanged |
| §3.6 Groups G, H | 102–104 | Unchanged |
| §3.7 Parallel coordinates | 106 | Unchanged |
| §3.8 Ranking stability | 108 | Unchanged |
| §3.9 Bubble chart | 110 | Unchanged |
| **§3.10 Group K: NA retention** | **5 new** | **New** |
| **§3.11 Group I: WaterMelon** | **6 new** | **New** |
| **§3.12 Shambhala analysis** | **8 new** | **New** |
| **§3.13 Harshness impact** | **6 new** | **New** |
| §4 Composite scoring | 111–122 | Updated (WM toggle, K scoring weight) |
| §5–§11 Gene / GO analysis | 123–160 | Unchanged (gene sets part) |

---

## 9. Figures to Add (new files in `figures/`)

| Figure filename | Section | Description |
|---|---|---|
| `k_na_cells_heatmap.svg` | §3.10 | pct_na_cells method × strategy heatmap |
| `k_failed_samples_table.csv` | §3.10 | n_samples_allNA pivot table |
| `a_joint_r2_pct_var_heatmap.svg/.pdf` | §3.1 | R² and pct_var side-by-side heatmap |
| `a_weighted_batch_r2_heatmap.svg/.pdf` | §3.1 | wt_r2_pc{i} heatmap |
| `i_wm_correlation_matrix.svg` | §3.11 | Spearman ρ among wm_* columns |
| `i_wm_vs_local_global.svg` | §3.11 | WM batch vs kBET and vs R² scatter |
| `i_wm_batch_bio_tradeoff.svg` | §3.11 | wm_mean_batch vs wm_mean_bio scatter |
| `i_wm_ratio_vs_composite.svg` | §3.11 | wm_ratio_bio_batch vs composite_score |
| `shambhala_clustermap.pdf` | §3.12 | Shambhala-only metric clustermap |
| `shambhala_r2_by_p_key.svg` | §3.12 | R² by P-calibration dataset bar chart |
| `shambhala_wm_q_comparison.svg` | §3.12 | WM trade-off: Q0std vs QNBKass |
| `shambhala_tradeoff_vs_others.svg` | §3.12 | Shambhala vs non-Shambhala Pareto scatter |
| `harshness_local_vs_global.svg` | §3.13 | Local vs global scores colored by harshness |
| `harshness_group_{A..H}_boxplots.svg` | §3.13 | 8 per-group harshness boxplot grids |
| `harshness_by_strategy_heatmap.svg` | §3.13 | Harshness × strategy × batch metric heatmap |
| `harshness_summary_table.csv` | §3.13 | Summary pivot table |

---

## 10. Files to Modify / Create

| File | Change type |
|---|---|
| `harmonization_metrics_analysis_v2.ipynb` | **Create** (copy + all changes above) |
| `harmonization_metrics_analysis_notebook_overview_260517.md` | No change — this plan supersedes it for v2 planning |

No changes to `compute_batch_metrics.py`, `run_metrics_job.py`, or `bench_shared.py` — all metric pipeline changes are already implemented per the existing plans.

---

## 11. Implementation Order

Work in this order to build incrementally on a stable foundation:

1. **Step 1 — Copy and smoke-test.** `cp` the notebook, verify it runs from top to bottom with no errors on the current CSV (which may still lack I, I_rare_batches_removed, and Shambhala data). All new sections guarded by data-availability checks should pass silently.

2. **Step 2 — R1 refactor (seaborn helpers).** Add the three helper functions (Cell 015b). Then rewrite each scatter/bar cell one by one. After each rewrite, run only that cell to confirm the figure looks identical to the v1 output.

3. **Step 3 — R4 (I_rare_batches_removed palette and ALL_STRATS).** These are one-cell changes; low risk.

4. **Step 4 — R3a (Group K in scoring, col_meta, filter cell).** Update Cell 005, 007, 009, the scoring cell, and add the quality filter cell.

5. **Step 5 — R3b (Group J + Group A joint heatmaps).** Add the two new cells to §3.1. Guard with `if pct_var_col_available:` check.

6. **Step 6 — R5 (Shambhala palette and annotations).** Add derived columns, palette, `attempt_colors` extension. Run the full clustermap cells to confirm layout.

7. **Step 7 — R6 (Harshness palette and annotations).** Add `HARSHNESS_LEVEL_MAP` (complete map in §6.1, approved), `HARSHNESS_PAL`, and `attempt_colors` extension. Run clustermaps.

8. **Step 8 — §3.10 Group K new section.** Add 5 cells. Guard all cells with NA-column availability check.

9. **Step 9 — §3.11 WaterMelon section.** Add 6 cells. All guarded by `WM_COLS` availability check.

10. **Step 10 — §3.12 Shambhala section.** Add 8 cells. All guarded by `SHAMBHALA_AVAIL`.

11. **Step 11 — §3.13 Harshness section.** Add 6 cells. Guard with `HARSHNESS_LEVEL_MAP` completeness check.

12. **Step 12 — Full run.** Execute the entire v2 notebook from top to bottom, fix any remaining import/reference issues.

---

## 12. Known Risks and Constraints

| Risk | Mitigation |
|---|---|
| `pct_samples_allNA` filter removes too many attempts if data has widespread NaN issues | Default `FILTER_ALLNA_SAMPLES = True` but make it a user-editable flag; print count of excluded attempts |
| Harshness level assignment is subjective | Provide an explicit `HARSHNESS_LEVEL_MAP` cell with inline comments; Daniil reviews before running §3.13 |
| Shambhala data not in CSV yet | All §3.12 cells wrapped in `if SHAMBHALA_AVAIL` guard; notebook runs clean without Shambhala data |
| Group I (WM) data not in CSV yet | All §3.11 cells wrapped in `if WM_COLS` guard |
| Seaborn refactor changes visual appearance slightly | Run v1 and v2 side-by-side on the same cell; all figures should be visually equivalent |
| `shambhala_method_pal` vs `method_pal` — two objects for same column | `method_pal` is the primary palette (near-black added for Shambhala); `shambhala_method_pal` is a separate `shambhala_detail` col_colors strip only, not a replacement |
| 18 Shambhala methods added to clustermaps will widen figures | Adjust clustermap `figsize` width proportionally: add `n_shambhala_methods × (original_width / n_all_methods)` |
| `I_rare_batches_removed` harshness ordering is approximate | Placed between G and H; Daniil can reorder `HARSHNESS_ORDER` after inspecting gene counts |

---

## TODO Checklist

### Prerequisites — verify data availability before starting any edits

- [ ] Run `python run_metrics_concat.py --out-csv metric_tables/metrics_comprehensive_NEW.csv` from inside the metrics pod to get the latest CSV with all computed groups
- [ ] Check Group J columns are present:
  ```python
  import pandas as pd; df = pd.read_csv("metric_tables/metrics_comprehensive_260513.csv")
  print([c for c in df.columns if "pct_var_pc" in c])
  # expected: ['pct_var_pc1', ..., 'pct_var_pc10', 'pct_var_cum_top10']
  ```
- [ ] Check Group K columns are present: look for `pct_genes_noNA`, `n_samples_allNA`, `pct_na_cells` in `df.columns`
- [ ] Check Group I columns: look for `wm_mean_batch` — if absent, §3.11 will be skipped silently (WM parallel pass not yet run)
- [ ] Check `I_rare_batches_removed` strategy: `print("I_rare_batches_removed" in df["strat"].unique())` — if False, R4 palette registers correctly but no rows will appear
- [ ] Check Shambhala methods: `print([m for m in df["method"].unique() if m.startswith("shambhala_")])` — if empty list, §3.12 will be skipped silently

---

### R2 — Copy notebook (Step 1)

- [x] `cp harmonization_metrics_analysis.ipynb harmonization_metrics_analysis_v2.ipynb`
- [ ] Open `harmonization_metrics_analysis_v2.ipynb` in JupyterLab
- [ ] Run all cells (`Run → Run All Cells`) — confirm zero errors in v2 before any edits
- [ ] Check `ls figures/ | wc -l` ≈ 247 (all existing figures reproduced from v1)

---

### R1 — Seaborn refactor (Step 2)

**Cell 015b — Add plotting helpers**
- [x] Insert a new code cell immediately after Cell 015 (`plot_multilevel_comparison`)
- [x] Implement `scatter_plot()` with full signature from §2.2.1 (all parameters: data, x, y, hue, style, size, palette, hue_order, style_order, alpha, s, ax, figsize, xlabel, ylabel, title, legend_outside, save_path)
- [x] Implement `bar_plot()` with full signature from §2.2.2 (estimator, errorbar, orient, xtick_rotation)
- [x] Implement `heatmap_plot()` with full signature from §2.2.3
- [ ] Run Cell 015b — confirm no import errors or NameErrors

**§3.1 Group A rewrites** (run each cell immediately after rewriting; compare figure to v1 output)
- [x] `a_r2_multilevel_method` bar chart: refactored to `bar_plot(df_long_r2, x="method", y="r2", hue="covariate", palette=r2_pal_covar, order=method_order_r2)`
- [x] R² vs PCR scatter: already used `sns.scatterplot` in v2 (no ax.scatter loop present)
- [x] R² by strat scatter: already used `sns.scatterplot` in v2 (no ax.scatter loop present)
- [x] R² by post_rm scatter: already used `sns.scatterplot` in v2 (no ax.scatter loop present)
- [x] DSC scatter: refactored to `scatter_plot(df_ok, x="dsc_RNA_BATCH", y="dsc_COHORT_LABEL", hue="method", size="r2_RNA_BATCH", palette=method_pal)`
- [x] PCR multi-covariate bar (by method + by strat): refactored to `bar_plot(df_long_pcr, x=..., y="pcr", hue="covariate", palette=pcr_pal_covar)`

**§3.2 Group B rewrites**
- [x] kBET vs iLISI scatter: refactored to `scatter_plot(df_ok, x=kbet_col, y=ilisi_col, hue="method", style="imp", palette=method_pal)`
- [x] Batch–biology trade-off scatter: refactored to `scatter_plot(df_ok, x=batch_asw, y=bio_col, hue="imp", palette=imp_pal)` (loop over bio cols)
- [x] kBET by strat scatter: `scatter_plot(df_ok, x="strat", y="kbet_acceptance_rate_RNA_BATCH", hue="strat", palette=strat_pal)`
- [x] kBET by method covariate bar: refactored to `bar_plot(df_long_kbet, x="method", y="kbet", hue="covariate", palette=kbet_pal_covar)`

**§3.3 Group C rewrites**
- [x] UMAP vs tSNE entropy correlation: refactored to `sns.scatterplot` per batch column (no more ax.scatter loop)

**§3.4 Group D rewrites**
- [x] KS scatter: refactored to `scatter_plot(df_ok, x="ks_mean_D_RNA_BATCH", y="ks_cohort_within_batch_mean_D", hue="method", palette=method_pal)`

**§4 Composite scoring rewrites**
- [x] Pareto frontier scatter: `scatter_plot(df_ok, x="score_batch_mixing", y="score_bio_preservation", hue="method", palette=method_pal)` as base; kept `ax.scatter` overlays for Pareto-optimal and top-N points

**§2.5 Embeddings (Cell 041)**
- [x] Replace per-method `ax.scatter` loop with `sns.scatterplot(data=embed_df, x=xl, y=yl, hue="method", palette=method_pal, s=30, alpha=0.7, linewidth=0, rasterized=True)` in top row; metric-type scatter with `sns.scatterplot` in bottom row
- [x] Keep NetworkX method-similarity network code unchanged (NetworkX drawing is not seaborn-replaceable)

**Group E bimodality scatter (Cell 104)**
- [x] Refactored to `scatter_plot(df_ok, x=bimod_col, y=zi_col, hue="method", palette=method_pal)`

---

### R4 — `I_rare_batches_removed` strategy (Step 3)

- [x] In Cell 018 (palette construction), add: `strat_pal["I_rare_batches_removed"] = "#7b4f9e"`
- [x] In the `ALL_STRATS` list cell, append `"I_rare_batches_removed"` after `"H_affymetrix_extended"`
- [x] In the `HARSHNESS_ORDER` list cell, inserted `("I_rare_batches_removed","strict")`, `("I_rare_batches_removed","knn")`, `("I_rare_batches_removed","softimpute")` after `G_affymetrix_only` entries
- [x] Add immediately after `df_ok` is built (Cell 003): `AVAIL_STRATS = [s for s in ALL_STRATS if s in df_ok["strat"].unique()]`
- [x] Add data-availability warning block (see §4.6) — guard in Cell 003
- [ ] Run the palette visualization cell — confirm `I_rare_batches_removed` appears in the strat color swatch in medium purple

---

### R3a — Group K: NA retention (Step 4)

**Cell 005 — column taxonomy**
- [x] Add `GROUP_MAP["K"] = ["n_genes_noNA", "pct_genes_noNA", "n_samples_noNA", "pct_samples_noNA", "n_genes_allNA", "n_samples_allNA", "n_na_cells", "pct_na_cells"]`
- [x] wm_subsampled excluded from metric_cols
- [ ] Run Cell 005 and verify `col_meta` now includes K columns without error

**Cell 007 — POLARITY assignment**
- [x] Add all Group K polarities: `pct_genes_noNA: +1`, `pct_samples_noNA: +1`, `n_genes_allNA: -1`, `n_samples_allNA: -1`, `n_na_cells: -1`, `pct_na_cells: -1`, `n_genes_noNA: 0`, `n_samples_noNA: 0`
- [ ] Run Cell 007 — verify no KeyError or missing column warning

**Cell 009 — manual polarity overrides**
- [x] (K auto-polarity is correct; no manual overrides needed)

**Cell 113 — SCORE_WEIGHTS**
- [x] Add `"pct_genes_noNA": 0.8, "pct_samples_noNA": 0.5, "n_samples_allNA": -1.0` to the Data Quality (5%) component

**Cell 026b — quality filter (new cell)**
- [x] Insert new code cell after Cell 025 and before Cell 027
- [x] Add `FILTER_ALLNA_SAMPLES = True` flag and the filtering logic (see §3.1.4)
- [ ] Run Cell 026b — print shows N attempts excluded (pct_samples_allNA > 0)

**§3.10 — 5 new cells** (add after §3.9 Bubble Chart, approx. after Cell 110)
- [x] §3.10.1 markdown cell: section header "§3.10 — Group K: NA Retention and Data Completeness"
- [x] §3.10.2 bar chart: `bar_plot(df_ok, x="pct_genes_noNA", y="method", hue="imp", palette=imp_pal, orient="h")`, sorted
- [x] §3.10.3 heatmap: wide matrix (methods × strategies, values = mean `pct_na_cells`); `cmap="YlOrRd"`, annotated
- [x] §3.10.4 boxplot: `sns.boxplot(x="harshness_level", y="pct_genes_noNA", palette=HARSHNESS_PAL)` with 80% reference line
- [x] §3.10.5 pivot table: failed-sample summary; styled red; saved as `k_failed_samples_table.csv`
- [ ] Run all 5 cells — verify figures and CSV are saved to `figures/`

---

### R3b — Group J × A joint analysis (Step 5)

- [x] GROUP_MAP["J"] added with `["pct_var_pc", "pct_var_cum"]` prefixes; POLARITY J = 0 (descriptive)
- [x] Insert Cell §3.1.x1 after the existing per-PC R² heatmaps (after Cell 070):
  - [x] Guard `pct_var_col_available` and `r2_pc_available` flags
  - [x] Compute `wt_r2_pc{i}` derived columns and `wt_r2_sum`
  - [x] Two-panel figure: left = `r2_pc{i}_RNA_BATCH` heatmap, right = `pct_var_pc{i}` heatmap; same row order (descending `wt_r2_sum`)
  - [x] Save as `a_joint_r2_pct_var_heatmap.svg`
- [x] Insert Cell §3.1.x2 immediately after §3.1.x1:
  - [x] Single heatmap: rows = methods, columns = PC1–10, values = `wt_r2_pc{i}`; `cmap="Reds"`; mask cells where < 0.01
  - [x] Save as `a_weighted_batch_r2_heatmap.svg`
- [ ] Run both cells — verify two new figure files appear in `figures/`

---

### R3c — Group I WaterMelon (Step 9)

- [x] GROUP_MAP["I"] = ["wm_"] added; POLARITY: batch cols = -1, bio cols / ratio = +1
- [x] wm_subsampled excluded from metric_cols
- [x] **§3.11 — 6 new cells** (all body cells wrapped in `if WM_AVAIL:`):
  - [x] §3.11.1 markdown header
  - [x] §3.11.2 WM correlation matrix: Spearman clustermap with row/col color strip
  - [x] §3.11.3 WM vs local/global: two-panel scatter (kBET and r²), Pearson r annotated
  - [x] §3.11.4 WM trade-off scatter with diagonal reference line
  - [x] §3.11.5 WM ratio vs composite scatter, Pearson r annotated
  - [x] §3.11.6 WM scoring toggle (`WM_SCORING_ENABLED = False`)
- [ ] Test all §3.11 cells — confirm skip silently when WM columns absent

---

### R5 — Shambhala palette and analysis (Step 6)

**Cell 003 — data loading and derived columns**
- [x] Add `_parse_shambhala_method()` function
- [x] Add `df_ok["is_shambhala"]`, `df_ok["shambhala_p_key"]`, `df_ok["shambhala_q_key"]`
- [x] Add `SHAMBHALA_AVAIL` flag with guard message

**Cell 018 — palette construction**
- [x] Build `shambhala_p_pal` (tab20b blue-purple, 9 P-keys)
- [x] Add `SHAMBHALA_METHOD_COLOR = "#1a1a1a"` loop for method_pal
- [x] Build `shambhala_method_pal` dict (non-Shambhala = `"#ffffff"`, Shambhala = P-key color)
- [x] Build `SHAMBHALA_BINARY_PAL = {True: "#3d1a78", False: "#e8e8e8"}`
- [x] Add `attempt_colors["is_shambhala"]`, `["shambhala_detail"]`
- [x] Build `col_colors_extended` with all 7 strips

**All clustermap cells**
- [x] All 5 main clustermap cells (27, 28, 30, 32, 33 → now 29, 30, 32, 34, 35) updated to `col_colors_extended`

**§3.12 — 9 new cells** (all body cells wrapped in `if SHAMBHALA_AVAIL:`)
- [x] §3.12.1 markdown: section header
- [x] §3.12.2 Shambhala mini-clustermap
- [x] §3.12.3 ranking table (styled DataFrame)
- [x] §3.12.4 P-key impact on batch (bar_plot)
- [x] §3.12.5 P-key impact on biology (bar_plot)
- [x] §3.12.6 Q-key comparison scatter (scatter_plot)
- [x] §3.12.7 Shambhala vs top non-Shambhala (boxplot + stripplot)
- [x] §3.12.8 Shambhala batch-biology tradeoff vs all methods
- [ ] Test all §3.12 cells — confirm skip silently when SHAMBHALA_AVAIL=False

---

### R6 — Harshness palette and analysis (Step 7)

**Cell 003 — HARSHNESS_LEVEL_MAP**
- [x] Add complete `HARSHNESS_LEVEL_MAP` dict (all 39 methods + Shambhala variants → high)
- [x] Add `df_ok["harshness_level"]` derived column

**Cell 018 — palette construction**
- [x] Add `HARSHNESS_PAL = {"low": "#4caf50", "medium": "#ff9800", "high": "#f44336"}`
- [x] Add `attempt_colors["harshness"]` strip
- [x] `col_colors_extended` includes harshness as 7th strip: `strat | imp | method | post_rm | is_shambhala | shambhala_detail | harshness`

**All clustermap cells**
- [x] All 5 main clustermap cells include harshness via `col_colors_extended`

**§3.13 — 7 new cells**
- [x] §3.13.1 markdown: section header + harshness level table (low/medium/high with method examples)
- [x] §3.13.2 FacetGrid boxplots per metric group (GROUP_MAP loop, melt, sns.FacetGrid + sns.boxplot)
- [x] §3.13.3 mean_local/mean_global computed, scatter_plot with harshness hue + Pearson r per group
- [x] §3.13.4 harshness impact by strategy (bar_plot by strat × harshness_level)
- [x] §3.13.5 heatmap pivot (harshness × strat) for each batch metric, annotated with n attempts
- [x] §3.13.6 harshness vs data quality (boxplot + stripplot per K metric)
- [x] §3.13.7 harshness summary: violin plot of composite_score and r²
- [ ] Run all cells — verify figures saved

---

### Final validation

- [ ] **Full notebook run**: restart kernel → `Run → Run All Cells` — target: zero errors from top to bottom
- [ ] **Guard verification**: temporarily set `SHAMBHALA_AVAIL = False` and `WM_AVAIL = False`; confirm §3.11 and §3.12 cells are all skipped silently (no errors, no stale output)
- [ ] **Figure inventory**: `ls figures/ | wc -l` should be ≥ 263 (247 existing + 16 new from §9); spot-check that all new SVG/PDF filenames listed in §9 exist
- [ ] **Scoring consistency check**: set `WM_SCORING_ENABLED = False` and `FILTER_ALLNA_SAMPLES = False`; compare v2 top-10 ranking table to v1 — results must be identical (same methods, same scores)
- [ ] **Seaborn visual check**: open v1 and v2 side by side; compare one scatter and one bar figure per section (§3.1, §3.2, §3.3, §3.4, §4) to confirm visual equivalence after the seaborn refactor
- [ ] **File size check**: `du -sh harmonization_metrics_analysis_v2.ipynb` — must be < 100 MB; strip outputs first with `nbstripout harmonization_metrics_analysis_v2.ipynb`
- [ ] **Commit**: stage only `harmonization_metrics_analysis_v2.ipynb`; confirm `harmonization_metrics_analysis.ipynb` (v1) is unchanged in `git diff`
