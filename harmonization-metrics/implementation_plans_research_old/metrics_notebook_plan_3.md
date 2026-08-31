    # Implementation Plan 3: Notebook Refactoring and New Features

**Date:** 2026-05-04  
**Author:** Daniil Nikitin  
**Purpose:** Detailed plan for 10 requested improvements to `harmonization_metrics_analysis.ipynb`.  
**Prerequisite reading:** `metrics_notebook_plan.md`, `metrics_notebook_plan_2.md` (Plans 1 & 2).

---

## Scope and Sequence

The 10 features below are ordered by dependency: features 2, 5, 6, 7 must come first because
they define shared constants and variable renames that all other cells reference. Then features
1, 3, 9, 10 refactor the §5 embedding section. Features 4 and 8 add new content.

| # | Feature | Touches | Prerequisite | Status |
|---|---|---|---|---|
| 2 | Font size single parameter | All plotting cells | — | ✅ Done |
| 5 | row/col colors disambiguation | §1, §2, all clustermaps | — | ✅ Done |
| 6 | Consistent palette usage | §3, §4, §5 | 5 | ✅ Done |
| 7 | Metric large-type classification + palette | §1, §2 | 5, 6 | ✅ Done |
| 1 | Expression/annotation caching | §5 | — | ✅ Done |
| 3 | Flexible, reusable functions | §1, §5 | 2, 9 | ✅ Done |
| 9 | pca_plot / umap_plot / tsne_plot | §5 | 2, 3 | ✅ Done |
| 10 | sharex / sharey in plot grids | §5 | 9 | ✅ Done |
| 4 | Adapt manual cells | §5 | 2, 6, 9, 10 | ✅ Done |
| 8 | New graphical analyses | §2.5, §3.7, §3.8, §4.9 | 2, 5, 6, 7 | ✅ Done |

---

## Daniil Nikitin's features formulation:

1) For visual inspection of PCA/UMAP/tSNE/violin plots/CV curves of the same top approaches please cash their expressions and annotations to avoid downloading of the same dataset each time for PCA, UMAP etc.

2) Make larger font size for slides, and for every plot all font sizes for all text boxes should be the same and fully customizable as a single parameter

3) The functions should be more flexible and reusable, so I can extensively edit and modify the notebook

4) Also please look at my manual cell that I've added, adapt them and my new sections to the overall pattern and style of the notebook.

5) Solve the ambiguity of row_colors and col_colors in the clustermaps. Sometimes I see the code lines row_colors=col_colors and vice versa. This is bad.

6) Use the specific palettes established in the beginning everywhere in the notebook, for all barplots, scatterplots etc. Do not use any other palettes. For example, when you are building barplots by strategies, use the corresponding palette for batch removal strategies etc.

7) In the beginning of the norebook, classify all the scoring_metrics into the three large groups: local neighbouthood (entropy, kBET, CLISI/ILISI, graph connectivity etc), global distance based (pcr, r2, distance ratio, CMS, silhouette score, asw, centroids etc), distribution similarity ones (all the KS stuff) and other (bimodal number and other unclassified ones). Add the third color palette for these groups, naming it 'metric_large_type_pal', and setting it dark and vivid, similar to the imputation palette but with different base colors, for example green, brown etc.

8) Add more graphical analysis, with an empasis on clustermaps, heatmaps, networks and other complex visualizations. Search the available literature for the popular ways of comparison between harmonization tools and implement them in the notebook.

9) Refactor PCA, UMAP and tSNE plots so they require less code for copy for the next instances of plots. Write three simple functions: pca_plot, umap_plot, tsne_plot, so I can reuse them.

10) Turn on sharey and share x in plot grids if necessary, for example UMAP and tSNE grids often do have the same x axis (UMAP1, TSNE1) and y axis (UMAP2, TSNE2) - no meaning in writing them separately multiple times.

## Feature 2 — Single-parameter font size control

### Problem
Font sizes are hardcoded scattered throughout every plotting cell: `fontsize=16` in embedding
titles, `fontsize=8` in tick labels, `fontsize=10` in boxplots, `fontsize=12` in some legends,
`fontsize=7` in some clustermap annotations. No cell can be copy-pasted for slides without
manually finding and changing every font size argument.

### Solution
Define one master constant `FONT_BASE` in the §1 setup cell (immediately after imports).
All other font sizes are derived from it. Pass these constants explicitly to every axis
call — do not rely on rcParams alone, because seaborn and clustermap ignore rcParams
in many contexts.

### Changes to §1.1 (imports cell)

Add the following block immediately after `sns.set_style("ticks")`:

```python
# ── Font size constants (change FONT_BASE to scale all text globally) ──────
FONT_BASE   = 14     # change this one number to rescale everything
FONT_TITLE  = FONT_BASE
FONT_LABEL  = FONT_BASE
FONT_TICK   = FONT_BASE - 2    # 12 by default
FONT_LEGEND = FONT_BASE - 2
FONT_ANNOT  = FONT_BASE - 4    # 10 — for in-plot annotations, tick overrides in large grids
FONT_SMALL  = FONT_BASE - 6    # 8  — for axis labels inside dense clustermaps / long tick labels
FONT_TINY   = FONT_BASE - 8    # 6  — for per-cell clustermap annotations, only when n_cols > 80

plt.rcParams.update({
    "font.size":          FONT_BASE,
    "axes.titlesize":     FONT_TITLE,
    "axes.labelsize":     FONT_LABEL,
    "xtick.labelsize":    FONT_TICK,
    "ytick.labelsize":    FONT_TICK,
    "legend.fontsize":    FONT_LEGEND,
    "figure.titlesize":   FONT_TITLE,
})
```

### Cells that require explicit fontsize updates

Every call to these matplotlib/seaborn methods must be replaced with the constant:

| Method call | Replace with |
|---|---|
| `set_title("...", fontsize=16)` | `set_title("...", fontsize=FONT_TITLE)` |
| `set_xlabel("...", fontsize=16)` | `set_xlabel("...", fontsize=FONT_LABEL)` |
| `set_ylabel("...", fontsize=16)` | `set_ylabel("...", fontsize=FONT_LABEL)` |
| `tick_params(labelsize=8)` | `tick_params(labelsize=FONT_TICK)` |
| `set_xticklabels(..., fontsize=8)` | `set_xticklabels(..., fontsize=FONT_SMALL)` |
| `set_yticklabels(..., fontsize=8)` | `set_yticklabels(..., fontsize=FONT_SMALL)` |
| `ax.text(..., fontsize=...)` | `ax.text(..., fontsize=FONT_ANNOT)` |
| `legend(fontsize=...)` | `legend(fontsize=FONT_LEGEND)` |
| `sns.catplot(..., height=...) # no fontsize` | wrap with `g.set_axis_labels(fontsize=...)` |
| `plot_multilevel_comparison(...)` — internal `fontsize=8` / `fontsize=10` | replace with `FONT_SMALL` / `FONT_ANNOT` |
| clustermap `annot_kws={"size": 6}` | `annot_kws={"size": FONT_TINY}` |

Cells most in need of updates: 15 (`plot_multilevel_comparison` definition), all §3 cells,
all §5 PCA/UMAP/tSNE plotting loops, and the clustermap cells in §2.

---

## Feature 5 — Row/col colors disambiguation

### Problem
The notebook has two pandas DataFrames:
- **`row_colors`**: indexed by harmonization attempt (run_id), columns = strat/imp/method/post_rm colors
- **`col_colors`**: indexed by metric name, columns = metric group / annot_col colors

In the **horizontal clustermap** orientation (rows = metrics, columns = attempts), seaborn's
`row_colors=` parameter needs metric-level annotations and `col_colors=` needs attempt-level
annotations. This forces the pattern `sns.clustermap(..., row_colors=col_colors, col_colors=row_colors)`
which looks like a typo and causes confusion every time a new clustermap is written.

Some existing cells have already swapped these correctly; others have not; some Plan 2 cells used
the swapped form without explanation. The user sees `row_colors=col_colors` in the actual code
and correctly flags it as a bug or bad smell.

### Solution: rename the variables to match their semantic meaning

In the **§1 palette cell** (Cell 17, currently "Build row/col color palettes"), rename:

| Old variable name | New variable name | Meaning |
|---|---|---|
| `row_colors` | `attempt_colors` | Per-attempt (run) metadata colors: strat, imp, method, post_rm |
| `col_colors` | `metric_colors` | Per-metric metadata colors: group (A–H), annot_col |

After renaming, all clustermap calls become:
```python
# Horizontal form (metrics as rows, attempts as columns) — used everywhere:
sns.clustermap(
    data_for_clustermap,         # shape: (n_metrics, n_attempts)
    row_colors=metric_colors,    # LEFT colorbar: metric group + annot_col
    col_colors=attempt_colors,   # TOP colorbar: strat + imp + method + post_rm
    ...
)
```

This is now unambiguous: the parameter name matches the variable name, and both names
match their semantic content.

### Cells to update

Search for every occurrence of `row_colors` and `col_colors` in the notebook and apply:

| Cell | Old | New |
|---|---|---|
| Cell 17 (palette construction) | `row_colors = pd.DataFrame(...)` | `attempt_colors = pd.DataFrame(...)` |
| Cell 17 (palette construction) | `col_colors = pd.DataFrame(...)` | `metric_colors = pd.DataFrame(...)` |
| Cell 25 (clustered clustermap) | `row_colors=row_colors, col_colors=col_colors` | `row_colors=metric_colors, col_colors=attempt_colors` |
| Cell 26 (raw clustermap companion) | same swap | same fix |
| Cell 30 (currently canonical horizontal) | inspect — already correct or fix | align to new names |
| Cell 31 (ordered variants) | fix variable references | same |
| Cell 33 (fully ordered heatmap) | no clustermap, but any reference to old vars | rename |
| All §5 correlation heatmaps | fix | align |
| Cell 117 (FL marker heatmap) | fix | align |

Also update `make_legend_patches` calls and any `_safe_map` calls that reference
the old variable names.

### Add a single-line comment to every clustermap call

```python
# Orientation: rows=metrics, cols=attempts → row_colors=metric annotations, col_colors=attempt annotations
```

This comment is placed directly above the `sns.clustermap(...)` call so there is no ambiguity
for future readers even after the rename.

---

## Feature 6 — Consistent palette usage

### Problem
Several cells in §3 and §5 use default matplotlib/seaborn color cycles instead of the
established palettes. Specific violations found during analysis:
- `plot_multilevel_comparison`: boxplots colored by default matplotlib cycle, not by the
  grouping variable's palette
- Catplots grouped by `method` or `strat`: use generic hue colors rather than `method_pal` / `strat_pal`
- Bar charts in §3.5, §3.6: colored by position in the array, not by the palette entry
- Scatter plots in §3.2.3 (batch–biology trade-off): colored by imputation but using
  a new ad-hoc palette instead of `imp_pal`

### Changes to `plot_multilevel_comparison` (Cell 15)

Add a `palette` parameter and a `group_col` lookup:

```python
def plot_multilevel_comparison(
    df, metric_col, group_col,
    figsize=None, title=None,
    palette=None,   # NEW: dict mapping group values → colors; auto-detected if None
):
    """..."""
    # Auto-detect palette from group_col if not provided
    if palette is None:
        _auto = {"method": method_pal, "strat": strat_pal, "imp": imp_pal}
        palette = _auto.get(group_col, {})
    
    # Use palette in boxplot colors and strip colors
    groups = sorted(df[group_col].dropna().unique())
    colors = [palette.get(g, "#AAAAAA") for g in groups]
    # ... boxplot patches: set color from colors list
    # ... strip plot: scatter with c=colors[i] per group
```

### Changes to catplots (§3 cells)

Every `sns.catplot(..., hue="method", ...)` call must pass `palette=method_pal`,
every `hue="strat"` must pass `palette=strat_pal`, every `hue="imp"` must pass
`palette=imp_pal`.

For catplots where `x` (not `hue`) is the grouping variable and x-axis items should be colored:
extract the palette colors in the correct order and pass as a list to `palette=`.

### Changes to scatter plots

For the batch–biology trade-off scatter (§3.2.3):
- Color by `imp` → use `imp_pal`
- Marker style by `strat` → no palette needed, but document explicitly

For the kBET vs iLISI scatter (§3.2.1):
- Color by `method` → use `method_pal`

For bar charts in §3.5.1 (gene count by strat):
- Set bar colors by `strat_pal` (one bar per strat value)

For bar charts in §3.6.1 (graph connectivity):
- If x-axis is `method`, color by `method_pal`

### No other palettes allowed in the analysis sections

If a plot needs a color that is not covered by {`strat_pal`, `imp_pal`, `method_pal`,
`post_rm_pal`, `group_pal`, `annot_pal`, `metric_large_type_pal`} or the canonical
project palettes (`rna_batch_palette`, `lymphoma_ontogeny_palette`, `platform_palette`),
add the needed key to the appropriate existing palette rather than creating a new one.

---

## Feature 7 — Metric large-type classification and palette

### Problem
Scoring metrics span conceptually different measurement approaches (neighbor-based local
statistics, global PCA-based statistics, distributional tests) but they are currently grouped
only by the computational group letter (A–H) and annotation column. A coarser three-way
classification helps readers understand which aspect of batch correction each metric captures.

### New classification

Add to the §1.3 (column taxonomy) cell, after the `GROUP_MAP` block:

```python
# ── Coarse metric type classification ─────────────────────────────────────────
# Three functional classes based on what the metric measures:
#
# "local_neighborhood"  — statistics computed in a local k-NN graph or embedding
#   neighborhood. Sensitive to local mixing quality at cell-type scale.
#   Prefixes / names: kbet_, ilisi_, clisi_, graph_connectivity_, umap_entropy_,
#                      tsne_entropy_
#
# "global_distance"  — statistics derived from global variance decomposition,
#   full-dataset centroids, or pairwise Euclidean distances.
#   Prefixes / names: r2_, pcr_, dsc_, umap_centroid_disp_, tsne_centroid_disp_,
#                      dist_ratio_, avg_intra_dist_, avg_inter_dist_,
#                      asw_batch_, asw_bio_, cms_
#
# "distribution_similarity"  — tests comparing the expression distribution shape
#   between batches (not just means/variances).
#   Prefixes / names: ks_mean_D_, ks_frac_sig_, ks_cohort_within_batch_,
#                      per_gene_batch_mean_cv_
#
# "other"  — descriptive data quality statistics and variancePartition (F group),
#   which fits none of the above and is used as a sanity check.
#   Prefixes / names: n_samples, n_genes, n_batches, n_cohorts, zero_fraction_,
#                      fraction_cohorts_, exp_*, per_batch_median_, vp_,
#                      n_samples_per_batch, bimodal, below_1_

METRIC_TYPE_MAP = {
    "local_neighborhood": [
        "kbet_", "ilisi_", "clisi_", "graph_connectivity_",
        "umap_entropy_", "tsne_entropy_",
    ],
    "global_distance": [
        "r2_", "pcr_", "dsc_", "umap_centroid_disp_", "tsne_centroid_disp_",
        "dist_ratio_", "avg_intra_dist_", "avg_inter_dist_",
        "asw_batch_", "asw_bio_", "cms_",
    ],
    "distribution_similarity": [
        "ks_mean_D_", "ks_frac_sig_", "ks_cohort_within_batch_",
        "per_gene_batch_mean_cv_",
    ],
    "other": [],   # catch-all; assigned to anything not matched above
}

def classify_metric_type(col: str) -> str:
    """Return the coarse metric type for a metric column name."""
    for type_name, prefixes in METRIC_TYPE_MAP.items():
        if type_name == "other":
            continue
        if any(col.startswith(p) for p in prefixes):
            return type_name
    return "other"

# Add to col_meta (after its initial construction)
col_meta["metric_type"] = col_meta.index.map(classify_metric_type)
print(col_meta["metric_type"].value_counts())
```

### New palette: `metric_large_type_pal`

Add immediately after the existing palette block in §1. Must be dark and vivid, using
base hues that do not overlap with `imp_pal` (steel blue, terracotta, amethyst):

```python
# ── Metric large-type palette: dark & vivid, distinct from imp_pal ─────────
# Base hues chosen to avoid steel-blue, red, and purple (used in imp_pal):
# local_neighborhood  → forest green (biological local mixing)
# global_distance     → burnt sienna / dark amber (global structural measures)
# distribution_sim    → dark teal / petrol (distributional shape comparison)
# other               → olive / dark khaki (descriptive/other)

metric_large_type_pal = {
    "local_neighborhood":    "#1a6b3c",   # deep forest green
    "global_distance":       "#8b4a0f",   # burnt sienna / dark amber
    "distribution_similarity": "#0d5c63", # dark teal / petrol
    "other":                 "#5c5c1a",   # dark olive
}
plot_palette(metric_large_type_pal, "Metric large type palette")
```

### Update metric_colors (formerly col_colors)

Add the new `metric_type` row to the `metric_colors` DataFrame in §1:

```python
metric_colors = pd.DataFrame({
    "group":       col_meta.loc[scoring_cols, "group"].map(group_pal),
    "annot_col":   col_meta.loc[scoring_cols, "annot_col"].map(annot_pal),
    "metric_type": col_meta.loc[scoring_cols, "metric_type"].map(metric_large_type_pal),  # NEW
}, index=scoring_cols)
```

All clustermaps now automatically show this third color bar alongside group and annot_col,
without any other code changes (since they all reference `metric_colors` after Feature 5 rename).

### Add `plot_palette` call for new palette

```python
plot_palette(metric_large_type_pal, "Metric large type (local / global / distribution / other)")
```

---

## Feature 1 — Expression and annotation caching

### Problem
In §5, the embedding subsections (PCA, UMAP, tSNE) for the same set of top methods each
independently call `load_harmonized_exp()` and `load_annotation()`. For a top-10 list, this
means 10 S3 downloads per embedding type × 3 types = 30 downloads of the same files.
Each download is ~50–200 MB and takes 30–120 seconds. Total overhead: ~10–30 minutes of
redundant I/O.

### Solution: module-level cache dict + `load_and_cache` wrapper

Add this block to the §5.0 (canonical palettes) or §5.1 (S3 helpers) cell:

```python
# ── Expression / annotation cache ─────────────────────────────────────────────
# Keys: (strat, imp, method, post_rm) → dict with "exp", "ann" DataFrames
# and optionally "pca", "umap", "tsne" coordinate arrays.
# Populated on first access; subsequent calls return the cached object directly.
# Clear with:  _EXP_CACHE.clear()
_EXP_CACHE: dict = {}

def load_and_cache(
    strat: str,
    imp: str,
    method: str,
    post_rm: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Return aligned (exp, ann) for the given harmonization, downloading from S3 only
    if not already in the module-level cache.

    The first call for a given (strat, imp, method, post_rm) downloads both files,
    aligns by index intersection, and stores both in ``_EXP_CACHE``. Subsequent
    calls return the cached DataFrames in O(1) time.

    Parameters
    ----------
    strat, imp, method, post_rm : str / bool
        Harmonization identifiers matching the S3 key format.

    Returns
    -------
    tuple of (exp_df, ann_df), both indexed by sample ID and pre-aligned.
    """
    key = (strat, imp, method, post_rm)
    if key not in _EXP_CACHE:
        exp = load_harmonized_exp(strat, imp, method, post_rm=post_rm)
        ann = load_annotation(strat, imp)
        exp, ann = align_exp_ann(exp, ann)
        _EXP_CACHE[key] = {"exp": exp, "ann": ann}
    entry = _EXP_CACHE[key]
    return entry["exp"], entry["ann"]
```

### Embedding coordinate caching

Extend the cache to store computed coordinates, keyed by embedding type and parameters:

```python
def get_or_compute_pca(
    strat: str, imp: str, method: str, post_rm: bool = False,
    n_components: int = 50,
) -> tuple[np.ndarray, object]:
    """Return cached PCA coords or compute and cache them."""
    key = (strat, imp, method, post_rm)
    cache_key = f"pca_{n_components}"
    if cache_key not in _EXP_CACHE.get(key, {}):
        exp, _ = load_and_cache(strat, imp, method, post_rm)
        coords, pca_obj = compute_pca_coords(exp, n_components=n_components)
        _EXP_CACHE.setdefault(key, {})["exp_"] = None  # ensure key exists
        _EXP_CACHE[key][cache_key] = (coords, pca_obj)
    return _EXP_CACHE[key][cache_key]

def get_or_compute_umap(
    strat: str, imp: str, method: str, post_rm: bool = False,
    n_pcs: int = 50, n_neighbors: int = 30, min_dist: float = 0.3,
) -> np.ndarray:
    """Return cached UMAP coords or compute and cache them."""
    key = (strat, imp, method, post_rm)
    cache_key = f"umap_{n_pcs}_{n_neighbors}_{min_dist}"
    if cache_key not in _EXP_CACHE.get(key, {}):
        exp, _ = load_and_cache(strat, imp, method, post_rm)
        coords = compute_umap_coords(exp, n_pcs=n_pcs, n_neighbors=n_neighbors, min_dist=min_dist)
        _EXP_CACHE.setdefault(key, {})[cache_key] = coords
    return _EXP_CACHE[key][cache_key]

def get_or_compute_tsne(
    strat: str, imp: str, method: str, post_rm: bool = False,
    n_pcs: int = 50, perplexity: float = 30.0,
) -> np.ndarray:
    """Return cached tSNE coords or compute and cache them."""
    key = (strat, imp, method, post_rm)
    cache_key = f"tsne_{n_pcs}_{perplexity}"
    if cache_key not in _EXP_CACHE.get(key, {}):
        exp, _ = load_and_cache(strat, imp, method, post_rm)
        coords = compute_tsne_coords(exp, n_pcs=n_pcs, perplexity=perplexity)
        _EXP_CACHE.setdefault(key, {})[cache_key] = coords
    return _EXP_CACHE[key][cache_key]
```

### Usage in §5 cells

Replace the current load-inside-loop pattern:
```python
# BEFORE (current — downloads every time):
for col_idx, (strat, imp, method) in enumerate(_top_ids):
    exp = load_harmonized_exp(strat, imp, method)
    ann = load_annotation(strat, imp)
    exp, ann = align_exp_ann(exp, ann)
    coords, _ = compute_pca_coords(exp)

# AFTER (cached — downloads only once per (strat, imp, method)):
for col_idx, (strat, imp, method) in enumerate(_top_ids):
    exp, ann = load_and_cache(strat, imp, method)
    coords, _ = get_or_compute_pca(strat, imp, method)
```

### Prefetch cell (optional)

Immediately before the PCA plot cell, add an optional prefetch cell that populates the
cache sequentially:

```python
# Optional: prefetch all top-N methods before plotting.
# Run this cell once; subsequent PCA/UMAP/tSNE cells will use cached data.
print("Prefetching expression + annotation for all top methods...")
for strat, imp, method in _top_ids:
    try:
        load_and_cache(strat, imp, method)
        print(f"  ✓ {strat} {imp} {method}")
    except Exception as e:
        print(f"  ✗ {strat} {imp} {method}: {e}")
print("Prefetch complete.")
```

---

## Feature 9 — pca_plot / umap_plot / tsne_plot functions

### Problem
The PCA, UMAP, and tSNE grid plots repeat nearly identical scatter-plot boilerplate 9 times
across §5. Each instance differs only in: which coordinates to use, which color column to
map, which axis labels to set. Copying requires updating 6–8 hardcoded values per copy.

### Three new functions in §5.1 (S3 helpers cell)

These functions are intentionally thin wrappers — they do the minimum: draw the scatter,
set labels, set title. Grid construction (creating axes, iterating over methods) is left
to the caller.

```python
def _color_by_col(
    ann_df: pd.DataFrame,
    color_col: str,
    palette: dict,
    prefix_match: bool = False,
) -> pd.Series:
    """
    Map an annotation column to colors using a palette dict.

    Parameters
    ----------
    ann_df : pd.DataFrame
        Annotation DataFrame.
    color_col : str
        Column to map (e.g. "RNA_BATCH", "Diagnosis_cell_type_unified").
    palette : dict
        Color dictionary. If prefix_match=True, each label is matched against
        palette keys using str.startswith (used for lymphoma_ontogeny_palette
        whose keys are label prefixes, not exact labels).
    prefix_match : bool
        If True, match labels by prefix rather than exact equality.

    Returns
    -------
    pd.Series of hex color strings, indexed like ann_df.
    """
    if not prefix_match:
        return ann_df[color_col].map(palette).fillna("#AAAAAA")
    # prefix matching — used for lymphoma_ontogeny_palette
    def _match(label):
        if pd.isna(label):
            return "#AAAAAA"
        for prefix, color in palette.items():
            if str(label).startswith(prefix):
                return color
        return "#AAAAAA"
    return ann_df[color_col].apply(_match)


def pca_plot(
    coords: np.ndarray,
    ann_df: pd.DataFrame,
    color_col: str,
    palette: dict,
    ax: plt.Axes,
    title: str = "",
    xlabel: str = "PC1",
    ylabel: str = "PC2",
    s: float = 3,
    alpha: float = 0.5,
    prefix_match: bool = False,
    rasterized: bool = True,
) -> None:
    """
    Draw a single PCA scatter plot on a given Axes.

    Parameters
    ----------
    coords : np.ndarray, shape (n_samples, 2+)
        PCA coordinates; columns 0 and 1 are used.
    ann_df : pd.DataFrame
        Annotation aligned to coords rows.
    color_col : str
        Annotation column to use for color mapping.
    palette : dict
        Color dictionary.
    ax : plt.Axes
        Target axes.
    title : str
        Axes title text.
    xlabel, ylabel : str
        Axis labels (default "PC1" / "PC2").
    s, alpha : float
        Scatter marker size and transparency.
    prefix_match : bool
        If True, use prefix-based palette matching (for lymphoma_ontogeny_palette).
    rasterized : bool
        If True, rasterize the scatter layer to reduce SVG file size.
    """
    colors = _color_by_col(ann_df, color_col, palette, prefix_match=prefix_match)
    ax.scatter(
        coords[:, 0], coords[:, 1],
        c=colors.values, s=s, alpha=alpha, linewidths=0, rasterized=rasterized,
    )
    ax.set_xlabel(xlabel, fontsize=FONT_LABEL)
    ax.set_ylabel(ylabel, fontsize=FONT_LABEL)
    ax.tick_params(labelsize=FONT_TICK)
    if title:
        ax.set_title(title, fontsize=FONT_TITLE)


def umap_plot(
    coords: np.ndarray,
    ann_df: pd.DataFrame,
    color_col: str,
    palette: dict,
    ax: plt.Axes,
    title: str = "",
    s: float = 3,
    alpha: float = 0.5,
    prefix_match: bool = False,
    rasterized: bool = True,
) -> None:
    """
    Draw a single UMAP scatter plot. Interface identical to pca_plot
    except axis labels default to "UMAP1" / "UMAP2".
    """
    pca_plot(
        coords, ann_df, color_col, palette, ax,
        title=title, xlabel="UMAP1", ylabel="UMAP2",
        s=s, alpha=alpha, prefix_match=prefix_match, rasterized=rasterized,
    )


def tsne_plot(
    coords: np.ndarray,
    ann_df: pd.DataFrame,
    color_col: str,
    palette: dict,
    ax: plt.Axes,
    title: str = "",
    s: float = 3,
    alpha: float = 0.5,
    prefix_match: bool = False,
    rasterized: bool = True,
) -> None:
    """
    Draw a single tSNE scatter plot. Interface identical to pca_plot
    except axis labels default to "tSNE1" / "tSNE2".
    """
    pca_plot(
        coords, ann_df, color_col, palette, ax,
        title=title, xlabel="tSNE1", ylabel="tSNE2",
        s=s, alpha=alpha, prefix_match=prefix_match, rasterized=rasterized,
    )
```

### Refactored embedding grid builder (used in all §5 subsections)

Replace the repeated 30-line plotting loop with one shared function:

```python
def plot_embedding_grid(
    top_ids: list[tuple[str, str, str]],
    embedding_fn,         # one of: get_or_compute_pca, get_or_compute_umap, get_or_compute_tsne
    plot_fn,              # one of: pca_plot, umap_plot, tsne_plot
    color_rows: list[tuple[str, dict, bool]],
    # list of (color_col, palette_dict, prefix_match) — one tuple per subplot row
    title_fn=None,        # callable(strat, imp, method, df_ok_row) → str; or None for auto
    add_raw_baseline: bool = True,
    figsize_per_col: float = 5.0,
    figsize_per_row: float = 5.0,
    post_rm: bool = False,
    **embed_kwargs,       # forwarded to embedding_fn (n_components, n_pcs, etc.)
) -> plt.Figure:
    """
    Build a (n_rows × n_cols) grid of embedding scatter plots.

    Rows correspond to different colorings (e.g. row 0 = RNA_BATCH, row 1 = Diagnosis).
    Columns correspond to harmonization methods (top_ids), optionally with a raw baseline.

    Parameters
    ----------
    top_ids : list of (strat, imp, method)
        Methods to plot (left to right, excluding baseline).
    embedding_fn : callable
        One of get_or_compute_pca / get_or_compute_umap / get_or_compute_tsne.
    plot_fn : callable
        One of pca_plot / umap_plot / tsne_plot — used for all panels.
    color_rows : list of (color_col, palette, prefix_match)
        One tuple per subplot row. Defines the coloring for each row.
    title_fn : callable or None
        Function to build column titles. Default: shows method + key metric values.
    add_raw_baseline : bool
        If True, append the raw ("01_raw") method as the last column.
    figsize_per_col, figsize_per_row : float
        Size multipliers for dynamic figure sizing.
    post_rm : bool
        Whether to use post-normalization outlier removed data.
    **embed_kwargs
        Additional keyword arguments forwarded to embedding_fn.

    Returns
    -------
    plt.Figure
    """
    ...
```

This function replaces the three repeated plotting cells in each §5 subsection (PCA + UMAP
+ tSNE). A typical subsection becomes three short calls:

```python
fig_pca  = plot_embedding_grid(_top_ids, get_or_compute_pca,  pca_plot,  _COLOR_ROWS)
fig_umap = plot_embedding_grid(_top_ids, get_or_compute_umap, umap_plot, _COLOR_ROWS)
fig_tsne = plot_embedding_grid(_top_ids, get_or_compute_tsne, tsne_plot, _COLOR_ROWS)
```

---

## Feature 10 — sharex / sharey in plot grids

### Principle
Share axes between subplots when all panels show the same coordinate space. Do not share
axes across coordinate spaces (PCA ≠ UMAP ≠ tSNE axes are different; they should NOT be shared
with each other).

### Rules for each plot type

**Embedding grids (PCA, UMAP, tSNE):**
- Within the same embedding: all panels in the same row/column share axes, because PC1/UMAP1/tSNE1
  is the same quantity in all panels for a single method.
- Specifically for UMAP and tSNE where the coordinate space is interpretable:
  `sharex="row", sharey="row"` so batch-vs-biology panels of the same method share axes,
  but different methods are free to have different coordinate ranges.
- For PCA: same rule. Different methods produce different PCA rotations, so do NOT share
  axes across columns.

Implementation in `plot_embedding_grid`:
```python
fig, axes = plt.subplots(
    n_rows, n_cols,
    figsize=(figsize_per_col * n_cols, figsize_per_row * n_rows),
    sharex="row",    # panels in the same row share x (same method, same embedding)
    sharey="row",    # panels in the same row share y
)
```

**Why "row" not "all":**
Row-sharing is correct because in each column (= one method), the two rows (batch vs biology
coloring) show the same embedding coordinates → same axis limits. Different columns (= different
methods) have independently computed embeddings → different coordinate ranges.

**Violin plot grids (§5.5):**
- `sharey=True` across all panels within the same set (same gene expression scale).
- `sharex=False` because the number of batches/cohorts differs per method.

**KS D-statistic subplot grids (§3.4.1):**
- `sharey=True` (all panels show D-statistic in [0, 1]).
- `sharex=False` (each panel has a different set of method labels).

**Graph connectivity subplot grids (§3.6.1):**
- `sharey=True` (all panels show connectivity in [0, 1]).

**Bar charts in §3.1.1 (R² per covariate):**
- If grouped bar charts are in a subplot grid: `sharey=True`.

**When NOT to share:**
- Radar chart (§4.7): never share; each axis is a different metric.
- Pareto frontier scatter (§4.8): x and y are different score components.
- `plot_multilevel_comparison`: top (boxplot) and bottom (p-value heatmap) panels must
  NOT share axes — they are conceptually different y-scales.

### Removing redundant axis labels after sharing

When axes are shared, only the leftmost column needs y-axis labels and only the bottom row
needs x-axis labels. After `plt.subplots(sharex=..., sharey=...)`, suppress redundant labels:

```python
for ax in axes.flat:
    if ax.get_subplotspec().is_first_col():
        ax.set_ylabel(ylabel_text, fontsize=FONT_LABEL)
    else:
        ax.set_ylabel("")
    if ax.get_subplotspec().is_last_row():
        ax.set_xlabel(xlabel_text, fontsize=FONT_LABEL)
    else:
        ax.set_xlabel("")
```

This logic is encapsulated in `plot_embedding_grid` and applied automatically.

---

## Feature 3 — Flexible and reusable functions

### Functions to add or refactor

In addition to the embedding functions from Feature 9 and cache functions from Feature 1,
add the following general-purpose helpers to §1.6 (the existing "reusable helper" cell):

**`clustermap_std`** — standardized wrapper that enforces the naming convention from
Feature 5 and applies the standard colormap / legend settings:

```python
def clustermap_std(
    data: pd.DataFrame,         # (n_rows, n_cols) matrix, already normalized [0,1]
    metric_colors: pd.DataFrame,  # row annotations (groups, annot_col, metric_type)
    attempt_colors: pd.DataFrame, # col annotations (strat, imp, method, post_rm)
    row_cluster: bool = True,
    col_cluster: bool = True,
    figsize: tuple = (60, 20),
    title: str = "",
    fname: str = None,           # save as FIGURES_DIR/fname.{svg,png} if given
    **kwargs,
) -> sns.matrix.ClusterGrid:
    """
    Standard clustermap with enforced orientation and naming.

    In this notebook all clustermaps use the horizontal orientation:
      rows = metrics, columns = harmonization attempts.
    ``metric_colors`` is always mapped to the seaborn ``row_colors`` parameter
    and ``attempt_colors`` to ``col_colors`` — never the reverse.

    Parameters
    ----------
    data : pd.DataFrame
        Normalized metric matrix, shape (n_metrics, n_attempts). Values in [0, 1].
    metric_colors, attempt_colors : pd.DataFrame
        Row and column color bars, built in §1 (see palette cell).
    row_cluster, col_cluster : bool
        Whether to cluster rows (metrics) / columns (attempts).
    figsize : tuple
        Figure size.
    title : str
        Suptitle text added above the clustermap.
    fname : str or None
        If given, save to FIGURES_DIR/{fname}.svg and FIGURES_DIR/{fname}.png.

    Returns
    -------
    sns.matrix.ClusterGrid
    """
    g = sns.clustermap(
        data,
        method="ward", metric="euclidean",
        row_cluster=row_cluster,
        col_cluster=col_cluster,
        row_colors=metric_colors.reindex(data.index),   # metric annotations on the LEFT
        col_colors=attempt_colors.reindex(data.columns), # attempt annotations on TOP
        cmap="RdYlGn", center=0.5, vmin=0, vmax=1,
        linewidths=0,
        xticklabels=False,
        yticklabels=True,
        cbar_pos=(0.02, 0.82, 0.012, 0.12),
        dendrogram_ratio=(0.03, 0.12),
        colors_ratio=(0.015, 0.025),
        **kwargs,
    )
    if title:
        g.fig.suptitle(title, fontsize=FONT_TITLE, y=1.01)
    if fname:
        g.fig.savefig(FIGURES_DIR / f"{fname}.svg", bbox_inches="tight")
        g.fig.savefig(FIGURES_DIR / f"{fname}.png", bbox_inches="tight", dpi=200)
    return g
```

**`add_legend_outside`** — place palette legends to the right of any axes:

```python
def add_legend_outside(
    fig: plt.Figure,
    ax: plt.Axes,
    palettes: dict[str, dict],   # label → {value: color}
    x_offset: float = 1.05,
    fontsize: int = None,
) -> None:
    """
    Add one legend patch group per palette dict to the right of ax.

    Parameters
    ----------
    fig : plt.Figure
    ax : plt.Axes
        Reference axes; legend is anchored to its right edge.
    palettes : dict of str → dict
        Outer key = legend title; inner dict = {label: hex_color}.
    x_offset : float
        Horizontal offset from the right edge of ax (in axes-fraction units).
    fontsize : int or None
        Legend font size. Defaults to FONT_LEGEND.
    """
```

**`strip_box_plot`** — replace repeated manual boxplot + stripplot combos in §3 cells:

```python
def strip_box_plot(
    df: pd.DataFrame,
    x: str,
    y: str,
    ax: plt.Axes,
    palette: dict = None,
    order: list = None,
    box_width: float = 0.5,
    strip_size: float = 4,
    strip_alpha: float = 0.5,
    xlabel: str = None,
    ylabel: str = None,
    title: str = "",
    rotate_x: int = 45,
) -> None:
    """
    Combined boxplot + strip plot with consistent fontsize and palette usage.

    Used throughout §3 whenever a per-group distribution is shown.
    Palette lookup is automatic: if x matches 'method', 'strat', or 'imp',
    the corresponding notebook-level palette is used; otherwise falls back
    to 'palette' argument.
    """
```

### Existing function changes (make more flexible)

**`normalize_for_display`**: add `fill_value` parameter (currently hardcoded to median fill):

```python
def normalize_for_display(
    df_vals, cols, polarity_map,
    fill_value: str = "median",  # "median", "zero", "mean"
)
```

**`plot_multilevel_comparison`**: add `color_by` parameter to pass the established palette
(as documented in Feature 6). The function should also accept `figsize` tuple directly,
rather than computing it internally from a hardcoded formula.

---

## Feature 4 — Adapt manual cells to notebook style

### Identifying the manual cells

Based on notebook structure analysis, the user's manually added cells appear to be:
- The three MNN subsection blocks (Cells ~84–90, 93–102, 105–114) with `_top_ids` lists
  that are hardcoded as Python literals rather than computed from the ranking table
- The violin + CV curve cells (Cells 102, 114) which have `# Panel A`, `# Panel B` headings
  but do not follow the docstring / fontsize / palette conventions established by the
  `insert_cells.py`-generated cells
- Any cell in §5 that loads data without using `load_and_cache`

### Changes needed

**Hardcoded `_top_ids` lists:**  
Keep the magic literals exactly as written — these tuples were chosen by visual inspection
of the PCA/UMAP portraits for specific publication-worthy comparisons and must not be
replaced by computed ranking. The only adaptation is to add a one-line comment directly
above each `_top_ids` list stating which specific subset is shown and why it was chosen
manually, for example:
```python
# Manually selected: best-performing MNN variants on A_confirmed_bad/strict
# (chosen by visual inspection of PCA batch-variance plots, not computed ranking)
_top_ids = [("A_confirmed_bad", "strict", "10_mnn"), ...]
```

**Violin / CV cells (Panel A / Panel B):**  
Refactor into the function-based pattern:
- Panel A (violins): call a shared `violin_per_batch(exp, ann, color_col, palette, ax)` helper
- Panel B (CV curves): call a shared `cv_vs_exp_curve(exp, ann, color_col, palette, ax)` helper
- Both helpers use `FONT_*` constants and the established palettes

**Replace bare `load_harmonized_exp` + `load_annotation` + `align_exp_ann` calls** with
`load_and_cache` (Feature 1).

**Font size in manual cells:**  
Search for all `fontsize=N` literals and replace with `FONT_TITLE`, `FONT_LABEL`, etc.

**Saving figures in manual cells:**  
Keep all existing filenames unchanged — they reflect the plot content naturally and were
chosen intentionally. The only change is to add a `fig.savefig(...)` call to manual cells
that currently save nothing at all. Do **not** rename files that already have a save call.

---

## Feature 8 — New graphical analyses

These are all **new cells** to be appended to existing sections. Do not modify existing cells;
add new subsections labeled §2.5, §3.7, §3.8, §4.9.

### §2.5 — Method similarity network and embedding

**Cell 2.5.1a — Metric correlation clustermap**  
A clustermap where both rows and columns are **metrics**. The color scale shows Spearman
correlation between metric columns across all runs. Strongly correlated metrics (redundant)
appear as blocks; anti-correlated metrics show which measures are complements.
This answers: "Can we reduce the metric set?"

```python
# §2.5.1a — Spearman correlation between scoring metrics
# Shape: (n_metrics × n_metrics). Each cell = Spearman ρ between two metric series.
metric_corr = df_ok[scoring_cols].corr(method="spearman")

g = sns.clustermap(
    metric_corr,
    method="ward", metric="euclidean",
    row_colors=metric_colors,   # metric metadata on left
    col_colors=metric_colors,   # same metadata on top (same index)
    cmap="RdBu_r", center=0, vmin=-1, vmax=1,
    linewidths=0, figsize=(28, 26),
    ...
)
# Note: both axes are metrics, so the same metric_colors object is reused for
# row_colors and col_colors. This is the only clustermap with this pattern.
```

**Cell 2.5.1b — Attempt correlation clustermap**  
A companion clustermap where both rows **and** columns are **harmonization attempts**
(i.e. each (strat, imp, method, post_rm) combination = one row/column). Cell values show
the Spearman correlation between two attempts' metric profiles across all scoring metrics.
This answers: "Which normalization methods produce similar metric fingerprints?"
Both `row_colors` and `col_colors` receive `attempt_colors` (strat / imp / method / post_rm
color strips), so the method grouping is visible on both axes simultaneously.

```python
# §2.5.1b — Spearman correlation between harmonization attempts
# Shape: (n_attempts × n_attempts). Each cell = Spearman ρ between two attempt profiles.
attempt_corr = df_ok.set_index("attempt_id")[scoring_cols].T.corr(method="spearman")

# attempt_colors must be aligned to the same attempt_id index
g = sns.clustermap(
    attempt_corr,
    method="ward", metric="euclidean",
    row_colors=attempt_colors,   # strat / imp / method / post_rm strips on left
    col_colors=attempt_colors,   # same strips on top
    cmap="RdBu_r", center=0, vmin=-1, vmax=1,
    linewidths=0, figsize=(28, 26),
    xticklabels=False, yticklabels=False,
)
g.fig.suptitle("Attempt similarity (Spearman ρ across all metrics)",
               fontsize=FONT_TITLE, y=1.01)
fig.savefig("figures/attempt_correlation_clustermap.pdf", bbox_inches="tight")
```

**Cell 2.5.2 — Embedding attempts and metrics in each other's space (6-panel 2×3 grid)**  

Two complementary perspectives, three embedding methods each:

- **Row 1 — Attempts in metric space** (each point = one (strat, imp, method, post_rm) run,
  position determined by its vector of scoring metric values). Color by method (`method_pal`).
  Panels: PCA · UMAP · tSNE.
- **Row 2 — Metrics in attempt space** (each point = one scoring metric, position determined
  by its vector of values across all runs). Color by `metric_large_type_pal` (primary) with
  `group_pal` as a second coloring variant shown in a separate legend or second row.
  Panels: PCA · UMAP · tSNE.

```python
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import umap as umap_lib
from sklearn.manifold import TSNE

# ── Data matrices ──────────────────────────────────────────────────────────────
X_att  = StandardScaler().fit_transform(df_ok[scoring_cols].fillna(0))
# attempts × metrics  →  row = one attempt

X_met  = StandardScaler().fit_transform(df_ok[scoring_cols].fillna(0).T)
# metrics × attempts  →  row = one metric

# ── Compute embeddings ─────────────────────────────────────────────────────────
pca_att   = PCA(n_components=2, random_state=42).fit_transform(X_att)
umap_att  = umap_lib.UMAP(n_neighbors=10, min_dist=0.2, random_state=42).fit_transform(X_att)
tsne_att  = TSNE(n_components=2, perplexity=30, random_state=42).fit_transform(X_att)

pca_met   = PCA(n_components=2, random_state=42).fit_transform(X_met)
umap_met  = umap_lib.UMAP(n_neighbors=10, min_dist=0.2, random_state=42).fit_transform(X_met)
tsne_met  = TSNE(n_components=2, perplexity=min(30, len(scoring_cols)-1), random_state=42).fit_transform(X_met)

# ── Plot 2×3 grid ──────────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 3, figsize=(24, 14))

ATT_COORDS = [pca_att,  umap_att,  tsne_att]
ATT_LABELS = [("PC1","PC2"), ("UMAP1","UMAP2"), ("tSNE1","tSNE2")]
MET_COORDS = [pca_met,  umap_met,  tsne_met]
MET_LABELS = [("PC1","PC2"), ("UMAP1","UMAP2"), ("tSNE1","tSNE2")]

# Row 0 — attempts colored by method
for col, (coords, (xl, yl)) in enumerate(zip(ATT_COORDS, ATT_LABELS)):
    ax = axes[0, col]
    for method, grp in df_ok.groupby("method"):
        rows = [df_ok.index.get_loc(i) for i in grp.index]
        ax.scatter(coords[rows, 0], coords[rows, 1],
                   c=method_pal.get(method, "#AAAAAA"),
                   label=method, s=30, alpha=0.7, linewidths=0, rasterized=True)
    ax.set_xlabel(xl, fontsize=FONT_LABEL)
    ax.set_ylabel(yl, fontsize=FONT_LABEL)
    ax.set_title(f"Attempts / method  ({xl[:3]})", fontsize=FONT_TITLE)

# Row 1 — metrics colored by metric_large_type_pal
metric_types = [
    next((t for t, prefixes in METRIC_TYPE_MAP.items()
          if any(m.startswith(p) for p in prefixes)), "other")
    for m in scoring_cols
]
for col, (coords, (xl, yl)) in enumerate(zip(MET_COORDS, MET_LABELS)):
    ax = axes[1, col]
    for i, (m, mt) in enumerate(zip(scoring_cols, metric_types)):
        ax.scatter(coords[i, 0], coords[i, 1],
                   c=metric_large_type_pal[mt],
                   s=60, alpha=0.8, linewidths=0, zorder=3)
        ax.text(coords[i, 0], coords[i, 1], m, fontsize=FONT_TINY, alpha=0.75)
    ax.set_xlabel(xl, fontsize=FONT_LABEL)
    ax.set_ylabel(yl, fontsize=FONT_LABEL)
    ax.set_title(f"Metrics / type  ({xl[:3]})", fontsize=FONT_TITLE)

fig.suptitle("Method and metric similarity embeddings", fontsize=FONT_TITLE + 2)
fig.tight_layout()
fig.savefig("figures/method_metric_embeddings_2x3.pdf", bbox_inches="tight")
```

**Cell 2.5.3 — Method correlation network (graph visualization)**  
Build a network where nodes = harmonization methods, edge weight = mean Spearman correlation
between their metric profiles across all (strat, imp) pairs. Show only edges above a threshold
(e.g. ρ > 0.7). Draw with `networkx` + spring layout, nodes colored by `method_pal`. 

```python
import networkx as nx

# Build Spearman ρ between methods (averaged across strat × imp)
method_profiles = df_ok.groupby("method")[scoring_cols].mean()
method_corr = method_profiles.T.corr(method="spearman")

G = nx.Graph()
threshold = 0.7
for i, m1 in enumerate(method_corr.index):
    G.add_node(m1)
    for j, m2 in enumerate(method_corr.columns):
        if i < j and method_corr.loc[m1, m2] > threshold:
            G.add_edge(m1, m2, weight=float(method_corr.loc[m1, m2]))

pos = nx.spring_layout(G, seed=42, weight="weight")
fig, ax = plt.subplots(figsize=(12, 10))
nx.draw_networkx_nodes(G, pos, ax=ax,
    node_color=[method_pal.get(n, "#AAAAAA") for n in G.nodes],
    node_size=600, alpha=0.9)
nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.4, width=1.5)
nx.draw_networkx_labels(G, pos, ax=ax, font_size=FONT_SMALL)
ax.set_title(f"Method similarity network (Spearman ρ > {threshold})", fontsize=FONT_TITLE)
ax.axis("off")
```

### §3.7 — Parallel coordinates plot for top-N methods

**Cell 3.7.1**  
Parallel coordinates show all key metrics simultaneously for each method.
X-axis: metric name. Y-axis: normalized score [0, 1]. Each method = one polyline.
Lines colored by `method_pal`. Ordered by composite score.

Include only 8–10 representative metrics (one per group A–H, chosen as the primary
metric per group: `r2_RNA_BATCH`, `kbet_acceptance_rate_RNA_BATCH`,
`umap_entropy_norm_RNA_BATCH`, `ks_mean_D_RNA_BATCH`,
`n_genes`, `vp_median_RNA_BATCH`, `graph_connectivity_Diagnosis_cell_type_unified`,
`dist_ratio_Diagnosis_cell_type_unified`).

```python
from pandas.plotting import parallel_coordinates

display_metrics = [
    "r2_RNA_BATCH", "kbet_acceptance_rate_RNA_BATCH",
    "umap_entropy_norm_RNA_BATCH", "ks_mean_D_RNA_BATCH",
    "n_genes", "graph_connectivity_Diagnosis_cell_type_unified",
    "dist_ratio_Diagnosis_cell_type_unified", "composite_score",
]
top_methods = df_ok.nlargest(N_TOP, "composite_score")["method"].unique()
plot_df = (
    df_normed
    .loc[df_ok.method.isin(top_methods)]
    .assign(method=df_ok.method)
    [display_metrics + ["method"]]
)
fig, ax = plt.subplots(figsize=(14, 6))
parallel_coordinates(plot_df, "method",
    color=[method_pal.get(m, "#AAAAAA") for m in plot_df.method.unique()],
    ax=ax, linewidth=1.5, alpha=0.7)
ax.set_ylabel("Normalized score (1 = best)", fontsize=FONT_LABEL)
ax.tick_params(axis="x", labelsize=FONT_SMALL, rotation=30)
```

### §3.8 — Rank stability heatmap

**Cell 3.8.1 — Ranking stability across metric subsets**  
Ask: "Does the top-10 ranking change when we remove one metric group?"
For each group A–H, recompute the composite score excluding all metrics of that group,
rank methods, and compare to the full ranking. Display as a heatmap: rows = methods
(ranked by full composite score), columns = "full" + "without group A" ... "without group H".
Cell color = rank position. Low variance across columns = robust ranking; high variance = ranking
depends heavily on that metric group.

```python
# Rank stability: columns = full + one-group-removed variants
rank_variants = {"full": df_ok[["composite_score"]].rank(ascending=False)}

for excluded_group in "ABCDEFGH":
    excl_cols = [c for c in scoring_cols
                 if col_meta.loc[c, "group"] == excluded_group]
    remaining = [c for c in scoring_cols if c not in excl_cols]
    # Recompute composite without that group (using existing weights on remaining cols)
    ...
    rank_variants[f"no_{excluded_group}"] = reranked

rank_df = pd.DataFrame({k: v.squeeze() for k, v in rank_variants.items()})
rank_df = rank_df.loc[df_ok.nlargest(20, "composite_score").index]  # top 20 only

fig, ax = plt.subplots(figsize=(14, 8))
sns.heatmap(rank_df, annot=True, fmt=".0f", cmap="YlOrRd_r",
            ax=ax, annot_kws={"size": FONT_TINY},
            linewidths=0.3, linecolor="#DDDDDD",
            cbar_kws={"label": "Rank (lower = better)"})
ax.set_title("Ranking stability: which metric group drives the ranking?", fontsize=FONT_TITLE)
```

### §3.9 — Bubble chart: method × metric group summary

**Cell 3.9.1**  
A grid where rows = harmonization methods (sorted by composite_score), columns = metric groups (A–H).
Each bubble: size ∝ normalized score (mean over metrics in that group), color = metric group
using `group_pal`. This provides a compact overview of how each method performs per group —
a different view of the same information as the full clustermap.

```python
# Average normalized score per method × group
group_means = df_normed.assign(
    method=df_ok.method
).groupby("method")[scoring_cols].mean()

# For each method and group, compute mean of that group's metrics
bubble_df = pd.DataFrame({
    grp: group_means[[c for c in scoring_cols if col_meta.loc[c, "group"] == grp]].mean(axis=1)
    for grp in "ABCDEFGH"
})

method_order = df_ok.groupby("method")["composite_score"].mean().sort_values(ascending=False).index

fig, ax = plt.subplots(figsize=(12, 9))
for col_idx, grp in enumerate("ABCDEFGH"):
    for row_idx, method in enumerate(method_order):
        score = bubble_df.loc[method, grp] if method in bubble_df.index else 0
        ax.scatter(
            col_idx, -row_idx,
            s=score * 500,     # size ∝ score
            c=group_pal[grp],
            alpha=0.8, linewidths=0,
        )
ax.set_xticks(range(8))
ax.set_xticklabels([f"Group {g}" for g in "ABCDEFGH"], fontsize=FONT_LABEL)
ax.set_yticks(-np.arange(len(method_order)))
ax.set_yticklabels(method_order, fontsize=FONT_SMALL)
ax.set_title("Normalized score by method × metric group (bubble size = mean score)",
             fontsize=FONT_TITLE)
```

### §4.9 — Rank correlation between metrics (which metrics agree?)

**Cell 4.9.1**  
Spearman rank correlation matrix among the 20 most important scoring metrics. Display as a
clustermap (metrics × metrics), colored by `metric_large_type_pal` on both color bars (since
both rows and columns are metrics). Groups of highly correlated metrics = redundancy candidates.

This plot is the analytic companion to §2.5.1 (which shows the same correlation for all
~140 metrics, but is harder to read). This version focuses on the 20 hand-selected metrics
that appear in `SCORE_WEIGHTS`, making it immediately interpretable.

### §5.7 — Ridgeline plots for expression distribution per batch

**Cell 5.7.1**  
For the top-3 methods and the raw baseline, draw ridgeline (joy plot) plots showing the
distribution of expression values per RNA_BATCH. Each ridge = one batch. After successful
normalization, ridges should overlap significantly; before (raw baseline), they are spread.

Use `matplotlib` manually (no external ridgeline library — avoid new dependencies):

```python
# Ridgeline plot: stacked density curves per RNA_BATCH, one panel per method
from scipy.stats import gaussian_kde

methods_to_plot = [("A_confirmed_bad", "strict", "16_fsqn_r"),
                   ("A_confirmed_bad", "strict", "17_quantile"),
                   ("A_confirmed_bad", "strict", "01_raw")]

fig, axes = plt.subplots(1, len(methods_to_plot), figsize=(6 * len(methods_to_plot), 8))
for ax, (strat, imp, method) in zip(axes, methods_to_plot):
    exp, ann = load_and_cache(strat, imp, method)
    batches = ann["RNA_BATCH"].unique()
    x_range = np.linspace(exp.values.min(), exp.values.max(), 300)
    for i, batch in enumerate(batches):
        sub = exp.loc[ann.RNA_BATCH == batch].values.flatten()
        sub = sub[np.isfinite(sub)]
        if len(sub) < 20:
            continue
        kde = gaussian_kde(sub, bw_method=0.1)
        y = kde(x_range)
        y_offset = -i * (y.max() * 0.8)  # vertical stacking
        ax.fill_between(x_range, y_offset, y_offset + y,
                        color=rna_batch_palette.get(batch, "#AAAAAA"), alpha=0.6)
        ax.plot(x_range, y_offset + y, color="white", linewidth=0.5)
        ax.text(x_range[-1], y_offset + y.max() * 0.5, batch,
                fontsize=FONT_TINY, ha="left", va="center")
    ax.set_title(method, fontsize=FONT_TITLE)
    ax.set_xlabel("Expression (log2)", fontsize=FONT_LABEL)
    ax.set_yticks([])
```

---

## Summary: Cells to modify vs. cells to add

### Cells to **modify** (existing cells, specific changes)

| Cell(s) | Feature(s) | Change description |
|---|---|---|
| §1.1 imports | 2 | Add `FONT_BASE` block and `plt.rcParams.update(...)` |
| §1.3 column taxonomy | 7 | Add `METRIC_TYPE_MAP`, `classify_metric_type`, extend `col_meta` |
| §1.6 multilevel comparison function | 2, 3, 6 | Add `palette` param; replace hardcoded fontsizes |
| §1 palette construction (Cell 17) | 5, 6, 7 | Rename `row_colors→attempt_colors`, `col_colors→metric_colors`; add `metric_large_type_pal`; add `metric_type` to metric_colors |
| All §2 clustermap cells | 5 | Replace old variable names with `metric_colors` / `attempt_colors` |
| §3.1–3.6 catplot / bar / scatter cells | 6 | Add `palette=method_pal` / `strat_pal` / `imp_pal` to all groupby plots |
| §5.1 S3 helpers | 1, 3 | Add `_EXP_CACHE`, `load_and_cache`, `get_or_compute_{pca,umap,tsne}` |
| §5.1 embedding functions | 9 | Add `pca_plot`, `umap_plot`, `tsne_plot`, `_color_by_col` |
| §5.2–5.14 all embedding loops | 1, 4, 9, 10 | Replace load + scatter boilerplate with `load_and_cache` + `plot_embedding_grid`; add `sharex="row", sharey="row"` |
| §5.5 violin / CV cells | 4, 2, 6 | Align to notebook style (fontsizes, palettes, figure saving) |
| All `plt.subplots(...)` in §3 | 10 | Add `sharey=True` where y-scale is the same across panels |

### Cells to **add** (new content)

| New location | Feature | Content |
|---|---|---|
| §1.6 (append) | 3 | `clustermap_std`, `add_legend_outside`, `strip_box_plot` helpers |
| §2.5 (new subsection) | 8 | Metric correlation clustermap (Cell 2.5.1) |
| §2.5 (new subsection) | 8 | Method similarity UMAP (Cell 2.5.2) |
| §2.5 (new subsection) | 8 | Method correlation network (Cell 2.5.3) |
| §3.7 (new subsection) | 8 | Parallel coordinates (Cell 3.7.1) |
| §3.8 (new subsection) | 8 | Ranking stability heatmap (Cell 3.8.1) |
| §3.9 (new subsection) | 8 | Bubble chart method × group (Cell 3.9.1) |
| §4.9 (new subsection) | 8 | Rank correlation between key metrics (Cell 4.9.1) |
| §5.0 or §5.1 prefetch | 1 | Optional prefetch cell for cache warmup |
| §5.7 (new subsection) | 8 | Ridgeline plots (Cell 5.7.1) |

---

## Implementation order (recommended)

1. **Feature 5** (rename `row_colors`/`col_colors`) — find-and-replace in all cells; verify
   all clustermaps still render; this is a pure rename with no functional change.

2. **Feature 2** (font constants) — add `FONT_BASE` block in §1.1; then do a search for
   `fontsize=` throughout the notebook and replace with constants. Verify plots render.

3. **Feature 7** (metric type classification) — add `METRIC_TYPE_MAP` in §1.3 and the
   new palette in §1 palette cell; add `metric_type` column to `metric_colors`. Verify
   clustermaps show three color bars instead of two.

4. **Feature 6** (consistent palettes) — update `plot_multilevel_comparison` and all §3
   catplots. Verify colors match the palette dicts.

5. **Feature 1** (caching) — add cache dict and helpers in §5.1. Replace all `load_harmonized_exp`
   + `load_annotation` + `align_exp_ann` calls with `load_and_cache`.

6. **Feature 9** (pca_plot/umap_plot/tsne_plot) — add function definitions in §5.1.
   Replace loop bodies with function calls. Test with one method first.

7. **Feature 10** (sharex/sharey) — add `sharex="row", sharey="row"` to all `plt.subplots`
   calls inside `plot_embedding_grid`. Test that tick labels are suppressed correctly.

8. **Feature 3** (more flexible functions) — add `clustermap_std`, `add_legend_outside`,
   `strip_box_plot` in §1.6. Update §2 clustermaps to call `clustermap_std`.

9. **Feature 4** (adapt manual cells) — replace hardcoded `_top_ids`, fix fontsizes,
   fix palette usage, add figure saving in all manual §5 cells.

10. **Feature 8** (new visualizations) — add all new §2.5, §3.7, §3.8, §3.9, §4.9, §5.7
    cells. Each is self-contained and does not break existing cells.

---

## Notes and cautions

- **Do not change cell IDs** during edits — this breaks cell-level references and the
  `insert_cells.py` script.
- **Feature 1 caching is per kernel session**: if the kernel is restarted, `_EXP_CACHE` is
  cleared and data must be re-downloaded. Add a `print(f"Cache: {len(_EXP_CACHE)} entries")`
  at the top of any cell that uses `load_and_cache` so the user can tell if the cache is warm.
- **`metric_large_type_pal` colors**: the four colors above were chosen to be dark and vivid,
  distinct from `imp_pal`. If they are too dark for the slide theme, increase L in HSL by
  0.10 (e.g., forest green `#1a6b3c` → `#2d8c55`). `FONT_BASE = 14` is suitable for
  Keynote/PowerPoint slides; reduce to `12` for notebooks intended for screen-only reading.
- **networkx** may not be installed in `collagen_3_11` venv. Check with `python -c "import networkx"`;
  install with `pip install networkx` if absent. Do not add to `requirements.txt` (it is
  analysis-only, not part of the metrics pipeline).
