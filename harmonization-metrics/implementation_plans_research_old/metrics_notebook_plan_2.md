# Implementation Plan 2: Notebook Improvements and Remaining Sections

**Date:** 2026-05-02  
**Author:** Daniil Nikitin  
**Purpose:** Continuation of `metrics_notebook_plan.md`. Covers (1) global quality improvements
to already-written cells, (2) the clustermap orientation change, (3) §5 Visual Inspection which
is not yet implemented, and (4) all of Part 2 (§6–§11) which has not been started.

---

## Part A — Global Quality Standards to Apply Everywhere

These rules apply to **every cell** in the notebook, new and existing alike.

### A.1 — Function docstrings

Every function must have a NumPy-style docstring with `Parameters`, `Returns`, and a one-sentence
summary. The key functions that currently lack one or have a minimal stub are:

| Function | Cell | What to add |
|---|---|---|
| `classify_metric_col` | 006 | Document `GROUP_MAP` logic, return tuple semantics |
| `normalize_for_display` | 012 | Document the NaN-fill-then-MinMax-then-flip pipeline and why NaN fill uses median |
| `plot_multilevel_comparison` | 015 | Document all parameters, the `height_ratios` layout, FDR method |
| `compute_composite_score` | 073 (SCORE_WEIGHTS cell, implicit function) | Promote to a named function with full docstring |
| `plot_palette` | 021 | Short docstring; currently has no explanation |
| `_safe_get` | 077 | Explain why it is needed (NaN-safe scalar access for radar chart) |
| `is_pareto` | 078 | Document the dominance criterion and return value |

### A.2 — Palette redesign (cell 018 — Build palettes)

The current palettes are not visually distinct enough from each other. Redesign according to
these rules, preserving the **manually adjusted imputation palette** (`imp_pal`) unchanged:

```python
# imp_pal is manually tuned — do not change:
imp_pal = {
    'strict':     '#2979ae',   # Deepened Steel Blue
    'knn':        '#982d22',   # Darkened Terracotta
    'softimpute': '#713689',   # Deepened Muted Amethyst
}
```

**Strat palette — soft pastel, clearly varied across 10 strategies:**
Use `sns.color_palette("pastel")` as the base but explicitly select 10 colors that are
maximally spread across hue (not clustered in blue-green). Map to `ALL_STRATS` in order.
The pastel lightness (~0.85 L in HSL) ensures strat bars never visually compete with the
vivid method bars.

**Method palette — bright and vivid, 25 methods:**
Use `tab20` (20 colors) plus 5 supplementary colors from `tab20b`. Boost saturation
compared to the default `tab20` by remapping colors through `mcolors.rgb_to_hsv` and
increasing the S channel by 0.15 (capped at 1.0). This ensures method bars are clearly
distinguishable from both the pastel strat bars and the dark imp bars.

**Post-rm palette — neutral grayscale:**
```python
post_rm_pal = {False: "#CCCCCC", True: "#333333"}
```
Intentionally plain — does not compete with any other palette.

**Metric group palette (group_pal) — highly saturated Set1 primary colors:**
```python
# Set1 gives bold primary colors (red, blue, green, purple, orange, yellow, brown, pink).
# These must not share hue with the pastel strat colors, which are washed-out versions
# of the same hues. The saturation contrast (Set1 S≈1.0 vs pastel S≈0.4) provides
# the separation even when hues overlap.
group_pal = dict(zip("ABCDEFGH", sns.color_palette("Set1", n_colors=8)))
```

**Annotation column palette (annot_pal) — split into two visual families:**

The 8 annotation columns divide into technical/batch columns and biology columns.
Batch columns (RNA_BATCH, PLATFORM_RNA, RNASEQ_SOURCE, COHORT_LABEL) should appear in
**warm sepia/amber tones** (earthy, brownish-orange); biology columns (Major_group,
Diagnosis_cell_type_unified, TUMOR_NORMAL) should appear in **cool teal/slate tones**;
`global/all` remains neutral gray.

```python
BATCH_ANNOT_COLS  = ["RNA_BATCH", "PLATFORM_RNA", "RNASEQ_SOURCE", "COHORT_LABEL"]
BIO_ANNOT_COLS    = ["Major_group", "Diagnosis_cell_type_unified", "TUMOR_NORMAL"]
GLOBAL_ANNOT_COL  = "global/all"

# Sepia/amber scale for batch columns (4 values, warm tones)
batch_pal_colors = ["#8B4513", "#CD853F", "#DEB887", "#F5DEB3"]  # SaddleBrown → Wheat
# Cool teal/slate scale for biology columns (3 values)
bio_pal_colors   = ["#2F4F4F", "#5F9EA0", "#B0C4DE"]             # DarkSlateGray → LightSteelBlue
# Neutral for global/all
global_pal_color = "#808080"

annot_pal = dict(
    zip(BATCH_ANNOT_COLS,  batch_pal_colors) |
    dict(zip(BIO_ANNOT_COLS, bio_pal_colors)) |
    {GLOBAL_ANNOT_COL: global_pal_color}
)
# This design makes batch-related metric columns immediately distinguishable
# from biology-related ones when reading the clustermap column colorbar.
```

Update `plot_palette` calls after the redesign to visualize all six palettes and confirm
no two palette families share indistinguishable color ranges.

### A.3 — Inline rationale comments for design decisions

The following decisions are non-obvious and must be explained with a comment at the point of use:

**POLARITY dictionary (cell 008) — full rationale block:**

```python
# ── Polarity rationale ────────────────────────────────────────────────────────
# POLARITY[c] = +1  → higher raw value = better batch correction or biology
# POLARITY[c] = -1  → lower raw value = better (e.g. lower R² = less batch)
# POLARITY[c] =  0  → descriptive metric: excluded from composite scoring
#
# Group A (r2_, pcr_, dsc_):
#   R² measures fraction of variance explained by batch. Lower is better (-1).
#   PCR (variance-weighted R²): same direction (-1).
#   DSC (distance between batch centroids): lower = centroids more mixed (-1).
#
# Group B (neighbor-based):
#   asw_batch_norm: ASW of batch labels after normalization; higher = better
#     batch mixing in neighbor graph (+1 regardless of which batch column).
#   asw_bio_norm: ASW of biology labels; higher = biology clusters are tight (+1).
#   kbet, ilisi_norm: acceptance rate / local mixing score; higher = better (+1).
#   clisi_mean: local inverse Simpson index for cell type; higher = better (+1).
#   cms_fraction_mixed: fraction of neighbors from different batches; higher = better (+1).
#   avg_intra_dist, avg_inter_dist: raw distances — direction depends on context,
#     so kept as 0 (excluded from scoring). Use dist_ratio instead.
#
# Group C (embedding metrics):
#   entropy_norm: batch entropy in UMAP/tSNE neighborhood; higher = better mixing (+1).
#   centroid_disp: distance between batch centroids in embedding; lower = better (-1).
#
# Group D (distribution):
#   ks_mean_D: mean KS D-statistic; lower = distributions more aligned (-1).
#   per_gene_batch_mean_cv: per-gene CV across batches; lower = less batch CV (-1).
#
# Group E (data quality):
#   n_genes, n_samples: more is better (+1).
#   fraction_cohorts_bimodal: bimodality is a natural gene-expression property,
#     NOT an artifact. Methods that preserve it are preferred (+1).
#   fraction_cohorts_zero_inflated_bimodal: pathological zero inflation = bad (-1).
#   Other descriptive stats (n_batches, exp_*, per_batch_median): polarity 0.
#
# Group F (variancePartition):
#   vp_ for batch columns: lower variance fraction = better batch removal (-1).
#   vp_ for biology columns: higher variance fraction = biology preserved (+1).
#
# Group G (graph connectivity):
#   graph_connectivity_*: higher = biology groups form connected clusters (+1).
#
# Group H (pairwise distances):
#   dist_ratio_*: intra-group mean distance / inter-group mean distance.
#     For batch columns: lower dist_ratio = batches more mixed = better (-1).
#     For biology columns: lower dist_ratio = biology clusters tighter = better (-1).
#   avg_intra_dist, avg_inter_dist: raw distances, not normalized → polarity 0.
```

**POLARITY_MANUAL override (cell 010) — add explanation:**

```python
# ── Manual overrides to POLARITY (applied after the auto-assignment above) ─────
# These entries correct cases where the automatic logic assigns the wrong polarity:
#
# asw_batch_norm_* for non-RNA_BATCH columns:
#   The auto-logic sets asw_batch_norm = +1 only when 'asw_batch_norm' prefix is found.
#   Manual check confirmed that ALL asw_batch_norm columns (regardless of batch column)
#   use the same polarity: higher = better mixing (after normalization).
#
# asw_bio_norm_PLATFORM_RNA = 0:
#   PLATFORM_RNA is a batch/technical column, not a biology column. Measuring
#   ASW of a batch grouping as a "biology" metric is meaningless → excluded.
#
# avg_intra_dist_* = 0, avg_inter_dist_* = 0:
#   Raw distances in high-dimensional space are scale-dependent and not directly
#   comparable across methods (different gene sets → different scale). Use
#   dist_ratio (normalized ratio) for scoring instead.
POLARITY.update(POLARITY_MANUAL)
```

**SCORE_WEIGHTS (cell 073) — weights rationale block:**

```python
# ── Weight rationale ──────────────────────────────────────────────────────────
# All weights are positive because df_normed already applies polarity (1=best for all).
# Weight magnitude encodes relative importance within each component.
#
# Component split (60 / 35 / 5):
#   Mirrors the scIB benchmark (Luecken et al. 2022, Nature Methods) which assigns
#   60% to batch correction and 40% to biology preservation. We use 35/5 for biology
#   vs. data quality because gene count is upstream of normalization (not a correction
#   metric) and bimodality is a sanity check rather than a primary outcome.
#
# Within batch_mixing:
#   r2_RNA_BATCH weight=3.0: primary metric in virtually all published benchmarks;
#     platform-level PCA variance is the most interpretable summary.
#   pcr_RNA_BATCH weight=2.0: variance-weighted version; more sensitive to PCs 2–10.
#   kbet, ilisi, asw_batch weight=1.5: three independent neighbor-graph metrics;
#     collectively cover local mixing at different scales.
#   cms, umap_entropy, dsc, ks weight=1.0: supporting metrics with lower reliability
#     or narrower scope.
#   PLATFORM_RNA, RNASEQ_SOURCE variants weight=0.5: secondary batch groupings;
#     correction at RNA_BATCH level subsumes platform-level correction.
#
# Within bio_preservation:
#   Diagnosis_cell_type_unified metrics > Major_group because Diagnosis is the
#   fine-grained biology relevant to FL subtyping (C1/C2/C3 × GCB/ABC).
#   r2_TUMOR_NORMAL weight=1.5: tumor vs normal is a fundamental biology axis
#     that must be preserved; loss here = complete analysis failure.
#   clisi entries are polarity-corrected by POLARITY dict (1=better); weight
#   magnitude matches the corresponding ASW entry.
#
# Within data_quality:
#   n_genes weight=1.0: log-normalized (see compute_composite_score) so
#     differences in the 3,000–25,000 range matter more than raw count.
#   fraction_cohorts_bimodal weight=1.0: bimodal distributions are expected
#     in gene expression and indicate the normalization does not over-smooth.
#   per_gene_batch_mean_cv weight=0.5: secondary check; already captured by
#     ks and r2 metrics.
```

**Normalization NaN fill (cell 012) — add comment:**

```python
# NaN imputation before MinMax scaling: use column median (not mean) to be robust
# to outlier runs that failed partially (e.g. kBET returned NaN for one imputation).
# Median-fill ensures the scaling range is not distorted by missing values, and
# NaN-filled entries are visually indistinguishable from the median — a neutral
# rather than best/worst position.
```

### A.4 — Scratch/exploratory cells to remove or consolidate

The following cells are temporary exploration artifacts and must be cleaned up before the notebook
is considered production-quality. They should either be removed or merged into a clean cell:

| Cell | Content | Action |
|---|---|---|
| 004 | `df[df.status == 'ok']` bare display | Remove (already shown by cell 003 print) |
| 009 | `POLARITY` bare display | Replace with `pd.Series(POLARITY).value_counts()` summary + assertion that all scoring_cols have non-zero polarity |
| 013 | `df_normed` bare display | Replace with a short validation: shape, value range, NaN count |
| 019 | Empty code cell | Remove |
| 027 | `df_ok` bare display | Remove |
| 028 | `df_ok[['tsne_entropy_norm_PLATFORM_RNA', 'method']].groupby...` | Remove (was a debug check) |
| 031 | Comment-only cell (no code) | Remove or merge intent into cell 032 comment |
| 033 | `data_for_clustermap` bare display | Remove |
| 034 | `# make dictionary of metrics` stub | Remove |
| 036 | `col_order` bare display | Remove |
| 037 | `df` bare display | Remove |

### A.5 — Figure export standard

Every figure-producing cell must end with:

```python
fig.savefig(FIGURES_DIR / "section_description.svg", bbox_inches="tight")
fig.savefig(FIGURES_DIR / "section_description.png", bbox_inches="tight", dpi=200)
plt.show()
```

Many existing cells use `dpi=150` — standardize to `200` throughout. Cells that currently only
save SVG or only save PNG should save both.

---

## Part B — Clustermap Orientation: Horizontal Standard

**Requirement:** All clustermaps must use the **horizontal orientation**:
- **Rows** = metrics (~140 scoring columns)
- **Columns** = harmonization attempts (~82–1,000 run IDs)

This is the transposed form relative to the original plan. Cell 030 (transposed clustermap) and
cell 032 (transposed unnormalized clustermap) are already the correct orientation. The non-transposed
versions in cells 029, 039–043 must be updated to match.

### B.1 — row_colors / col_colors naming convention (uniform across the notebook)

The user's manual cells already established the correct convention for the horizontal layout.
Standardize it notebook-wide without exceptions:

```
row_colors  →  always assigned to col_colors  (metric-level annotations: group + annot_col)
col_colors  →  always assigned to row_colors  (attempt-level annotations: strat + imp + method + post_rm)
```

In the horizontal form `data_for_clustermap` is `(n_metrics × n_attempts)`. Therefore:
- `row_colors` describes metrics → supply `col_colors` (which contains group/annot_col per metric)
- `col_colors` describes attempts → supply `row_colors` (which contains strat/imp/method/post_rm per attempt)

This means every `sns.clustermap(...)` call must have exactly:
```python
sns.clustermap(
    data_for_clustermap,   # shape: (n_metrics, n_attempts)
    row_colors=col_colors, # metric annotations (group, annot_col)
    col_colors=row_colors, # attempt annotations (strat, imp, method, post_rm)
    ...
)
```

Any cells where these are currently swapped or inconsistent must be corrected. Cell 030 already
follows this convention — it is the reference.

### B.2 — Changes required in each clustermap cell

**Cell 029 (currently: non-transposed clustered clustermap):**
Remove. Cell 030 (horizontal, canonical) is the correct version. Having both orientations
in the same section is confusing. If a vertical reference is ever needed for comparison,
keep it in a separate exploratory subsection clearly labeled "vertical orientation (reference only)".

**Cell 030 (currently: transposed clustered clustermap — CANONICAL):**
This cell becomes the canonical §2.2 Clustered Clustermap. Clean up:
- Remove the `#scaled and polarized metrics, transposed` scratch comment
- Add a docstring-style comment block:

```python
# ── §2.2 Clustered clustermap ─────────────────────────────────────────────────
# Orientation: rows = metrics (~140), columns = harmonization attempts (~82).
# Both rows and columns are clustered (Ward linkage, Euclidean distance).
# row_colors = col_colors (metric group A–H + annotation column)
# col_colors = row_colors (strat, imp, method, post_rm)
# Color scale: RdYlGn, normalized score 0→1 where 1=best for all metrics.
```

- Figure filename: `clustermap_all_metrics_clustered.svg / .pdf / .png`

**Cell 032 (currently: raw unnormalized transposed clustermap):**
Rename to §2.2b (companion to §2.2). Add comment:

```python
# ── §2.2b Companion: raw (unnormalized) clustermap ───────────────────────────
# Same layout as §2.2 but using raw metric values (df_ok, not df_normed).
# Useful to compare whether clustering structure changes with normalization.
# Note: the RdYlGn colormap is not meaningful on raw values — use as a structural
# reference only.
```

**Cell 038 (currently: grouped heatmap — wrong orientation):**
Rewrite to horizontal form. Rows (metrics) fixed in group → annot_col order; columns
(attempts) clustered:

```python
# ── §2.3 Grouped heatmap: metrics in fixed group order, attempts clustered ────
# Rows are fixed by metric group then annotation column — no row clustering.
# This makes the group structure (A–H) readable without dendrogram scrambling.
metric_order = col_meta.loc[scoring_cols].sort_values(["group", "annot_col"]).index.tolist()

g2 = sns.clustermap(
    df_normed[scoring_cols].dropna().T.reindex(metric_order),
    method="ward", metric="euclidean",
    row_cluster=False,           # metrics fixed in group order
    col_cluster=True,            # attempts clustered
    row_colors=col_colors.loc[metric_order],
    col_colors=row_colors,
    cmap="RdYlGn", center=0.5, vmin=0, vmax=1,
    linewidths=0, figsize=(60, 20),
    dendrogram_ratio=(0.03, 0.12),
    xticklabels=False, yticklabels=True,
    colors_ratio=(0.01, 0.02),
)
```

**Cells 039–041 (reorder attempts by strat / method / imp):**
Consolidate into a single §2.3b cell with a `SORT_BY` parameter and a loop over three orderings.
In horizontal form: rows = metrics (row_cluster=False), columns = attempts in fixed sort order:

```python
# ── §2.3b Ordered clustermaps: attempts sorted by metadata ───────────────────
# Three variants: (1) by removal strategy, (2) by harmonization method,
# (3) by imputation. No clustering in any variant — pure structural overview.
for sort_keys, fname_suffix in [
    (["strat", "imp"],     "by_strat"),
    (["method", "imp"],    "by_method"),
    (["imp", "strat"],     "by_imp"),
]:
    col_order_sorted = df.reindex(data_for_clustermap.columns).sort_values(sort_keys).index.tolist()
    g_sorted = sns.clustermap(
        data_for_clustermap[col_order_sorted],
        method="ward", metric="euclidean",
        col_cluster=False,
        row_colors=col_colors,
        col_colors=row_colors.reindex(col_order_sorted),
        cmap="RdYlGn", center=0.5, vmin=0, vmax=1,
        linewidths=0, figsize=(60, 20),
        xticklabels=False, yticklabels=True,
    )
    g_sorted.fig.savefig(FIGURES_DIR / f"clustermap_sorted_{fname_suffix}.svg", ...)
```

**Cell 043 (§2.4 Ordered heatmap — no clustering):**
Update variable names to reflect the horizontal orientation:

```python
# ── §2.4 Fully ordered heatmap (no clustering) ────────────────────────────────
# Rows (metrics) ordered: metric group → annotation column.
# Columns (attempts) ordered: strat harshness → imp → method → post_rm.
# This is the most readable structural overview — no dendrograms distort the layout.
METRIC_ORDER = col_meta.loc[scoring_cols].sort_values(["group", "annot_col"]).index.tolist()

ATTEMPT_ORDER = (
    df_ok.assign(_si=pd.Categorical(df_ok.strat, categories=ALL_STRATS, ordered=True))
    .sort_values(["_si", "imp", "method", "post_rm"])
    .index.tolist()
)

fig, ax = plt.subplots(figsize=(60, 18))
sns.heatmap(
    df_normed[scoring_cols].dropna().T.reindex(METRIC_ORDER)[ATTEMPT_ORDER],
    ax=ax,
    cmap="RdYlGn", center=0.5, vmin=0, vmax=1,
    linewidths=0,
    xticklabels=False, yticklabels=True,
    cbar_kws={"shrink": 0.3, "label": "Normalized score (1=best)"},
)
ax.set_title("Ordered overview — cols: strat→imp→method→post_rm; rows: metric group→annot_col")
```

### B.3 — Legend placement for horizontal clustermaps

In the horizontal layout, `row_colors` (= metric group + annot_col) appear on the left margin;
`col_colors` (= strat + imp + method + post_rm) appear on the top margin. The current legend
code in cell 030 places patches outside the figure at fixed offsets. Rewrite to use
`bbox_to_anchor` relative to `g.ax_heatmap` so the legends appear to the right of the heatmap
without overlapping the row colorbar.

---

## Part C — Remaining Implementation: §5 Visual Inspection of Top Approaches

This section is **not yet implemented**. It requires S3 access to download expression matrices
and annotation files, then computing PCA/UMAP/tSNE and plotting comparison grids.

### §5 — Visual Inspection of Top Approaches

**Cell 5.0 — Canonical visualization palettes (imported from all_cohorts_assembly.ipynb)**

Before the S3 downloads, define a cell containing the project-canonical palettes. These are
the established palettes from `FL_harmonization/all_cohorts_assembly.ipynb` and
must be used for all embedding visualizations (PCA, UMAP, tSNE) throughout §5. Do not
build new palettes for these axes — consistency with the main analysis notebook is essential
for dissertation figures.

```python
# ── Canonical project palettes (from all_cohorts_assembly.ipynb) ──────────────
# These are the definitive color mappings for the entire dissertation.
# Use these for all sample-level scatter plots in §5.

lymphoma_ontogeny_palette = {
    # Normal B-cells: cold spectrum (blues, teals, greens)
    'Bone_marrow_CD19+_':  'blue',
    'Immature_':           '#08519c',
    'Naive_':              '#4292c6',
    'GC_':                 '#006d2c',
    'Centroblast_':        '#41ab5d',
    'Centrocyte_':         '#a1d99b',
    'B_cells_':            'lawngreen',
    'MZ_':                 'olive',
    'Memory_':             '#00ced1',
    'Plasmablast_':        '#5f9ea0',
    'Plasma_':             'grey',
    # Malignant types: warm spectrum (reds, oranges, purples)
    'Follicular_Lymphoma_':       '#6a0dad',
    'Follicular_Lymphoma_GCB':    '#9400d3',
    'Diffuse_Large_B_Cell_Lymphoma_ABC': '#ff4500',
    'Diffuse_Large_B_Cell_Lymphoma_GCB': '#d62728',
    'Diffuse_Large_B_Cell_Lymphoma_':    '#8b0000',
    'High_Grade_B_Cell_Lymphoma_':       '#ff00ff',
    'Burkitt_Lymphoma_':                 'orange',
}

rna_batch_palette = {
    "RNASeq_FF_Total":             "#1f77b4",
    "RNASeq_FF_PolyA":             "#17becf",
    "RNASeq_FFPE_Exome_capture":   "#9467bd",
    "RNASeq_FF_rRNADepletion":     "#000080",
    "RNASeq_FFPE_PolyA":           "#8c564b",
    "RNASeq_FF_Unknown":           "#bcbd22",
    "RNASeq_FF_Exome_capture":     "#2ca02c",
    "GPL96+97_FF_Unknown":         "#d62728",
    "GPL570_FF_Unknown":           "#ff7f0e",
    "GPL570_Unknown_Unknown":      "#ffbb78",
    "GPL570_FFPE_Unknown":         "#dbdb8d",
    "GPL96_FF_Unknown":            "#f7b6d2",
    "GPL96_FFPE_Unknown":          "#e377c2",
    "GPL6244_FF_Unknown":          "#e9967a",
    "GPL6244_FFPE_Unknown":        "#fa8072",
    "GPL13938_FFPE_Unknown":       "#800000",
    "GPL1708_FF_Unknown":          "#7f7f7f",
    "GPL14951_FFPE_Unknown":       "#c49c94",
    "GPL17077_FF_Unknown":         "#c5b0d5",
    "GPL13158_FF_Unknown":         "#ad494a",
    "GPL17586_FF_Unknown":         "#008b8b",
    "GPL17047_FF_Unknown":         "#4682b4",
    "GPL887_FFPE_Unknown":         "#b0c4de",
    "GPL10739_FF_Unknown":         "#9edae5",
    "GPL8432_FFPE_Unknown":        "#006400",
    "GPL20188_FF_Unknown":         "#556b2f",
    "GPL23541_FF_Unknown":         "#8fbc8f",
    "GPL16686_FF_Unknown":         "#333333",
    "GPL26356_FF_Unknown":         "#a0522d",
}

platform_palette = {
    "RNASeq":       "#4B0082",
    "RNAseq":       "#4B0082",
    "Kassandra":    "#6A5ACD",
    "GPL96+97":     "#FF4500",
    "GPL96+GPL97":  "#FF4500",
    "GPL570":       "#FF8C00",
    "GPL96":        "#B22222",
    "GPL6244":      "#E9967A",
    "GPL13938":     "#CD5C5C",
    "A-GEOD-19803": "#A52A2A",
    "GPL1708":      "#008080",
    "GPL14951":     "#4682B4",
    "GPL17077":     "#00CED1",
    "GPL13158":     "#1E90FF",
    "GPL17586":     "#20B2AA",
    "GPL17047":     "#5F9EA0",
    "GPL887":       "#B0C4DE",
    "GPL10739":     "#2E8B57",
    "GPL10739+GPL19251": "#3CB371",
    "GPL20188":     "#6B8E23",
    "GPL23541":     "#8FBC8F",
    "GPL8432":      "#006400",
    "GPL16686":     "#8B4513",
    "GPL26356":     "#A0522D",
    float("nan"):   "#D3D3D3",
    None:           "#D3D3D3",
}

# cohort_palette is defined in all_cohorts_assembly.ipynb and is very large (88 cohorts).
# Include the full dict here — copy verbatim from all_cohorts_assembly.ipynb.
# [full cohort_palette dict — insert here from all_cohorts_assembly.ipynb]
```

These palettes are used in §5.2–5.4:
- `rna_batch_palette` → RNA_BATCH coloring in PCA/UMAP/tSNE
- `lymphoma_ontogeny_palette` → `Diagnosis_cell_type_unified` coloring; match sample label
  prefixes by `str.startswith(prefix)` since labels contain trailing diagnosis details
- `platform_palette` → PLATFORM_RNA coloring
- For `COHORT_LABEL`: use `cohort_palette`

**Cell 5.1 — S3 download helpers**

```python
def load_harmonized_exp(strat: str, imp: str, method: str, post_rm: bool = False) -> pd.DataFrame:
    """
    Download a harmonized expression matrix from S3.

    The expression file is stored as TSV.gz with samples as rows and genes as columns.
    The post_rm flag selects between the two variants produced by each normalization job:
    - post0 (False): raw normalization output
    - post1 (True): post-normalization outlier removal applied

    Parameters
    ----------
    strat : str
        Removal strategy key (e.g. "A_confirmed_bad").
    imp : str
        Imputation key: "strict", "knn", or "softimpute".
    method : str
        Normalization method key (e.g. "16_fsqn_r").
    post_rm : bool
        Whether to load the post-normalization outlier-removed variant.

    Returns
    -------
    pd.DataFrame
        Expression matrix, samples × genes, index = sample IDs.
    """
    s3 = boto3.client("s3")
    pm = "1" if post_rm else "0"
    key = f"{S3_PREFIX}/exp/{strat}__{imp}__{method}__post{pm}.tsv.gz"
    body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
    return pd.read_csv(io.BytesIO(gzip.decompress(body)), sep="\t", index_col=0)


def load_annotation(strat: str, imp: str) -> pd.DataFrame:
    """
    Download the annotation file aligned to a given (strat, imp) preparation.

    Parameters
    ----------
    strat : str
        Removal strategy key.
    imp : str
        Imputation key.

    Returns
    -------
    pd.DataFrame
        Annotation DataFrame, index = sample IDs. Key columns: RNA_BATCH,
        PLATFORM_RNA, COHORT_LABEL, Major_group, Diagnosis_cell_type_unified,
        TUMOR_NORMAL.
    """
    s3 = boto3.client("s3")
    key = f"{S3_PREFIX}/prepared/{strat}__{imp}__ann.tsv.gz"
    body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
    return pd.read_csv(io.BytesIO(gzip.decompress(body)), sep="\t", index_col=0)


def align_exp_ann(exp: pd.DataFrame, ann: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Align expression and annotation to their shared sample IDs.

    Alignment is done by index intersection, not positional order. Samples present in
    exp but not in ann (or vice versa) are silently dropped. Always check
    len(exp_aligned) == len(ann_aligned) after calling this function.

    Parameters
    ----------
    exp : pd.DataFrame
        Expression matrix (samples × genes).
    ann : pd.DataFrame
        Annotation (samples × columns).

    Returns
    -------
    tuple of (exp_aligned, ann_aligned) with matching index.
    """
    common = exp.index.intersection(ann.index)
    return exp.loc[common], ann.loc[common]
```

**Cell 5.2 — PCA comparison grid for top-N methods**

For each of the top-N methods (from §4) plus the raw baseline `01_raw`, download the expression
matrix and annotation, compute PCA, and draw two scatter panels side by side:
- **Left panel:** PC1 × PC2, colored by `RNA_BATCH` using `rna_batch_palette`
- **Right panel:** PC1 × PC2, colored by `Diagnosis_cell_type_unified` using `lymphoma_ontogeny_palette`

Layout: `2 × (N_TOP + 1)` subplots (2 rows: batch coloring / biology coloring). Column titles
include the method name, `r2_RNA_BATCH`, and `r2_Diagnosis_cell_type_unified` from the metrics
table, so the PCA picture is directly annotated with the key metric values.

```python
def compute_pca_coords(exp: pd.DataFrame, n_components: int = 50) -> tuple[np.ndarray, PCA]:
    """
    Compute PCA on a log2-scaled expression matrix.

    Data are mean-centered and unit-variance scaled before PCA (StandardScaler).
    Returns all n_components; the first two are used for scatter visualization.

    Parameters
    ----------
    exp : pd.DataFrame
        Expression matrix (samples × genes), log2-transformed values expected.
    n_components : int
        Number of PCs to compute. Default 50 (standard for transcriptomics pipelines).

    Returns
    -------
    coords : np.ndarray, shape (n_samples, n_components)
        PCA coordinates.
    pca : sklearn.decomposition.PCA
        Fitted PCA object (use .explained_variance_ratio_ for variance inspection).
    """
    from sklearn.preprocessing import StandardScaler
    X = StandardScaler().fit_transform(exp.values)
    pca = PCA(n_components=min(n_components, min(X.shape) - 1))
    coords = pca.fit_transform(X)
    return coords, pca
```

Color mapping for `Diagnosis_cell_type_unified`: match sample labels against
`lymphoma_ontogeny_palette` keys using `str.startswith(prefix)` since diagnosis labels
are stored as prefixed category names (e.g. `"Follicular_Lymphoma_GCB"` matches prefix
`"Follicular_Lymphoma_"` in the palette). Build a per-sample color array before plotting.

Save as: `figures/pca_grid_top{N_TOP}.svg`, `figures/pca_grid_top{N_TOP}.png`

**Cell 5.3 — UMAP comparison grid**

Same two-panel structure as §5.2 (RNA_BATCH / Diagnosis_cell_type_unified) but use UMAP.
Use `rna_batch_palette` and `lymphoma_ontogeny_palette` identically to §5.2.

```python
def compute_umap_coords(
    exp: pd.DataFrame,
    n_pcs: int = 50,
    n_neighbors: int = 30,
    min_dist: float = 0.3,
    random_state: int = 42,
) -> np.ndarray:
    """
    Compute UMAP embedding on the top-N PCA coordinates of an expression matrix.

    UMAP is computed on the PCA representation (not raw expression) to reduce noise
    and computation time. n_pcs=50 is standard for transcriptomics datasets.

    Parameters
    ----------
    exp : pd.DataFrame
        Expression matrix (samples × genes).
    n_pcs : int
        Number of PCA dimensions to use as UMAP input.
    n_neighbors : int
        UMAP neighborhood size. 30 is appropriate for ~1,000–10,000 samples.
    min_dist : float
        UMAP minimum distance. 0.3 balances local/global structure for bulk RNA-seq.
    random_state : int
        Random seed for reproducibility.

    Returns
    -------
    np.ndarray, shape (n_samples, 2)
        Two-dimensional UMAP coordinates.
    """
    import umap as umap_lib
    pca_coords, _ = compute_pca_coords(exp, n_components=n_pcs)
    reducer = umap_lib.UMAP(
        n_neighbors=n_neighbors, min_dist=min_dist,
        n_components=2, random_state=random_state,
    )
    return reducer.fit_transform(pca_coords)
```

Save as: `figures/umap_grid_top{N_TOP}.svg`, `figures/umap_grid_top{N_TOP}.png`

**Cell 5.4 — tSNE comparison grid**

Same two-panel structure (RNA_BATCH / Diagnosis_cell_type_unified) using t-SNE.
Use `rna_batch_palette` and `lymphoma_ontogeny_palette` identically to §5.2 and §5.3.

```python
def compute_tsne_coords(
    exp: pd.DataFrame,
    n_pcs: int = 50,
    perplexity: float = 30.0,
    random_state: int = 42,
) -> np.ndarray:
    """
    Compute t-SNE embedding on top-N PCA coordinates of an expression matrix.

    t-SNE is computed on PCA (not raw expression) for speed and noise reduction.
    Perplexity 30 is appropriate for datasets of ~1,000–5,000 samples; reduce to
    15 for smaller subsets.

    Parameters
    ----------
    exp : pd.DataFrame
        Expression matrix (samples × genes).
    n_pcs : int
        Number of PCA dimensions to use as t-SNE input.
    perplexity : float
        t-SNE perplexity. Rule of thumb: ~sqrt(n_samples).
    random_state : int
        Random seed.

    Returns
    -------
    np.ndarray, shape (n_samples, 2)
    """
    from sklearn.manifold import TSNE
    pca_coords, _ = compute_pca_coords(exp, n_components=n_pcs)
    tsne = TSNE(n_components=2, perplexity=perplexity, random_state=random_state)
    return tsne.fit_transform(pca_coords)
```

Save as: `figures/tsne_grid_top{N_TOP}.svg`, `figures/tsne_grid_top{N_TOP}.png`

**Cell 5.5 — Per-batch expression distribution violin plots + CV-vs-expression curves (top-5 only)**

This cell combines two complementary views of the same data for the top-5 methods:

**Part A — Expression distribution violins:**
For the top-5 methods plus the raw baseline, draw two sets of violin plots:
- Set 1: x = `RNA_BATCH` (colored by `rna_batch_palette`), y = marginal expression, one violin per batch
- Set 2: x = `COHORT_LABEL` (colored by `cohort_palette`), y = marginal expression, one violin per cohort

Layout: `2 rows × 6 columns` (top-5 + raw). Add vertical dotted lines between RNA_BATCH
groups in the cohort-level panel to make platform-level grouping visible.

**Part B — CV-vs-mean-expression binned curves:**
For the same top-5 methods, plot the relationship between mean gene expression and per-gene
coefficient of variation (CV) for each `RNA_BATCH` and each `COHORT_LABEL`. After successful
normalization, all curves should converge on a universal declining shape (high-expression genes
have lower CV — a property of all transcriptomics data). Divergence of these curves across
batches or cohorts is the most sensitive indicator of residual batch effect.

```python
# CV-vs-expression binning: divide genes into 20 expression-level quantile bins,
# compute median CV per bin, plot as a curve per batch/cohort group.
# All lines in one axis per method, colored by rna_batch_palette or cohort_palette.
fig, axes = plt.subplots(len(top_5), 2, figsize=(14, 4 * len(top_5)))
for i, (strat, imp, method) in enumerate(top_5_ids):
    exp, ann = load_harmonized_exp(strat, imp, method), load_annotation(strat, imp)
    exp, ann = align_exp_ann(exp, ann)
    for ax, group_col, group_pal_dict in zip(
        axes[i],
        ["RNA_BATCH", "COHORT_LABEL"],
        [rna_batch_palette, cohort_palette],
    ):
        for group_name, idx in ann.groupby(group_col).groups.items():
            sub = exp.loc[exp.index.intersection(idx)]
            gene_means = sub.mean(axis=0)
            gene_cvs = sub.std(axis=0) / gene_means.replace(0, np.nan)
            bins = np.percentile(gene_means.dropna(), np.linspace(0, 100, 21))
            bin_cvs, bin_centers = [], []
            for b0, b1 in zip(bins[:-1], bins[1:]):
                mask = (gene_means >= b0) & (gene_means < b1)
                bin_cvs.append(gene_cvs[mask].median())
                bin_centers.append((b0 + b1) / 2)
            ax.plot(bin_centers, bin_cvs, alpha=0.6, linewidth=0.8,
                    color=group_pal_dict.get(group_name, "#AAAAAA"),
                    label=group_name)
        ax.set_xlabel("Mean expression (log2)")
        ax.set_ylabel("Median gene CV")
        ax.set_title(f"{method} — {group_col}")
```

Save Part A and Part B as separate figures:
`figures/violins_top5.svg / .png` and `figures/cv_vs_exp_top5.svg / .png`

**Cell 5.6 — FL/GC marker gene correlation heatmap + housekeeping gene stability (top-5 only)**

**Important: add a markdown cell before this cell citing the sources for all gene sets used
in the notebook.** See the citation block in §A.6 below.

**Panel A — FL/GC marker gene correlation:**
Use the gene list `FL_GENES_ALL` defined in §11.
Compute Pearson correlation of the ~40 genes across samples for each method. Show as a
clustered heatmap (genes × genes). Compare whether well-known co-regulated pairs
(BCL2/BCL6, MKI67/PCNA, AICDA/MKI67) cluster together after normalization.

**Panel B — Housekeeping gene CV stability:**
For 15 housekeeping genes (ACTB, GAPDH, B2M, HMBS, HPRT1, PPIA, RPL13A, RPLP0, TBP,
YWHAZ, UBC, VIM, LDHA, PGK1, SDHA), compute:
- CV across `RNA_BATCH` groups (batch CV — should be low after normalization)
- CV across `Major_group` groups (biology CV — should remain comparable to baseline)

Display as a 2-column table per method: baseline `01_raw` vs. the top method. Color cells by
CV magnitude (green = low, red = high).

### A.6 — Source citations markdown cell (insert before §5.6 and before §11.1)

A dedicated markdown cell must be inserted once before §5.6 Panel B (housekeeping genes) and
again before §11.1 (FL gene list assembly). It must contain DOI/URL links for every gene set
used in the notebook:

```markdown
## Gene Set Sources and Citations

| Gene set | Source | DOI / URL |
|---|---|---|
| FL transcriptomic subtypes C1/C2/C3 (FL_2025_MARKERS) | Xochelli et al. 2025, *Leukemia* | https://doi.org/10.1038/s41375-025-02603-9 |
| legacy internal GC B-cell markers (Centroblast/Centrocyte) | unpublished internal panel | superseded by the Dybkaer et al. 2015 panels |
| FL PFS prognostic signature (FL_PROG_SIGNATURES) | Pastore et al. 2019, *J Clin Oncol* | https://doi.org/10.1200/JCO.18.01545 (PMID 29475724) |
| POD24 mutation markers | Huet et al. 2018, *Blood* | https://doi.org/10.1182/blood-2018-03-837443 |
| PROGENy pathway activating genes | Schubert et al. 2018, *Nature Communications* | https://doi.org/10.1038/s41467-017-02391-6 |
| Housekeeping genes (stability reference) | Eisenberg & Levanon 2013, *Trends Genet* | https://doi.org/10.1016/j.tig.2013.05.010 |
| kBET batch metric | Büttner et al. 2019, *Nature Methods* | https://doi.org/10.1038/s41592-018-0254-1 |
| LISI / Harmony metric | Korsunsky et al. 2019, *Nature Methods* | https://doi.org/10.1038/s41592-019-0619-0 |
| scIB benchmark + ASW/kBET weighting | Luecken et al. 2022, *Nature Methods* | https://doi.org/10.1038/s41592-021-01336-8 |
| FSQN normalization | Franks et al. 2018, *Biostatistics* | https://doi.org/10.1093/biostatistics/kxx053 |
```

---

## Part D — Remaining Implementation: Part 2 Gene Set Analysis (§6–§11)

Part 2 is **not yet started**. It begins with a clear section header markdown cell and a
brief summary of what Part 2 investigates. All cells below must be written fresh.

### §6 — Download Gene Lists from S3

**Cell 6.1 — S3 gene list discovery**

```python
def list_gene_files(s3_bucket: str, s3_prefix: str) -> list[str]:
    """
    List all per-harmonization gene list JSON files on S3.

    Gene lists are stored under ``{s3_prefix}/genes/`` as
    ``{strat}__{imp}__{method}__{post_rm_tag}_genes.json``.

    Parameters
    ----------
    s3_bucket : str
        S3 bucket name.
    s3_prefix : str
        S3 path prefix (e.g. "FL_batch_correction").

    Returns
    -------
    list of str
        Full S3 keys of all gene list files found.
    """
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=s3_bucket, Prefix=f"{s3_prefix}/genes/"):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith("_genes.json"):
                keys.append(obj["Key"])
    return keys
```

Print: total files found, breakdown by strat × imp × post_rm.

**Cell 6.2 — Download and parse into dictionary**

```python
def parse_gene_key(s3_key: str) -> tuple[str, str, str, bool] | None:
    """
    Parse a gene list S3 key into its (strat, imp, method, post_rm) components.

    Expected filename format: ``{strat}__{imp}__{method}__{post_tag}_genes.json``
    where post_tag is "post0" (no post-removal) or "post1" (post-removal applied).

    Parameters
    ----------
    s3_key : str
        Full S3 key string.

    Returns
    -------
    tuple (strat, imp, method, post_rm) or None if the key cannot be parsed.
    """
    fname = s3_key.split("/")[-1].replace("_genes.json", "")
    parts = fname.split("__")
    if len(parts) != 4:
        return None
    strat, imp, method, pm_tag = parts
    return strat, imp, method, (pm_tag == "post1")
```

Build `gene_sets: dict[(strat, imp, method, post_rm), set[str]]`.

**Cell 6.3 — Summary DataFrame**

Build `gene_df` with one row per gene set: `(strat, imp, method, post_rm, n_genes)`.
Print `gene_df.groupby(["strat", "imp", "post_rm"])["n_genes"].describe()`.
Verify that methods other than `25_angel` have nearly identical gene counts within
the same `(strat, imp)` pair — gene sets are determined by data preparation, not normalization.

**Cell 6.4 — Build convenience lookups**

```python
# Aggregate gene sets by (strat, imp) — union across all methods except 25_angel.
# Used in §7, §8, §10 where we ask what genes are available for a given data
# preparation step, not what a specific normalizer produces.
# 25_angel is tracked separately because it applies its own internal gene filtering
# on top of the preparation step.
gene_sets_by_strat_imp: dict[tuple[str, str], set[str]] = {}
gene_sets_angel: dict[tuple[str, str], set[str]] = {}  # Angel-specific gene sets

for (strat, imp, method, post_rm), genes in gene_sets.items():
    if not post_rm:
        key = (strat, imp)
        if method == "25_angel":
            gene_sets_angel.setdefault(key, set()).update(genes)
        else:
            gene_sets_by_strat_imp.setdefault(key, set()).update(genes)
```

### §7 — Gene Count and Overlap Analysis

**Cell 7.1 — Gene count per (strat, imp) pre-normalization**

Bar chart: x = `(strat, imp)` ordered by `ALL_STRATS` harshness order (permissive → strict),
y = `n_genes`. Color bars by `strat` using `strat_pal`. Add a secondary panel showing the
count for `25_angel` separately (it internally filters genes). Print the delta between
`S0_no_removal` and each other strategy (how many genes are lost per filtering step).

**Cell 7.2 — Pairwise Jaccard overlap heatmap**

```python
def jaccard_matrix(sets: list[set]) -> np.ndarray:
    """
    Compute the pairwise Jaccard similarity matrix for a list of gene sets.

    Jaccard(A, B) = |A ∩ B| / |A ∪ B|. Returns 1 on the diagonal.

    Parameters
    ----------
    sets : list of set
        List of gene sets to compare.

    Returns
    -------
    np.ndarray, shape (n, n)
        Symmetric Jaccard matrix with values in [0, 1].
    """
    n = len(sets)
    mat = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            inter = len(sets[i] & sets[j])
            union = len(sets[i] | sets[j])
            mat[i, j] = mat[j, i] = inter / union if union > 0 else 0.0
    return mat
```

Display as an annotated heatmap (values shown inside cells). Row/column labels = `(strat, imp)`.

**Cell 7.3 — Set intersection: supervenn plots**

Two supervenn figures:
1. Fixed `imp="strict"`, varying strat → how harshness shrinks gene universe
2. Fixed `strat="A_confirmed_bad"`, varying imp → how imputation recovers genes

After each supervenn, print the core gene count (present in all sets) and the
strategy-specific / imputation-recovered counts.

Note: `supervenn` must be called with `sets` as a **list** (not generator) and labels
as a matching list of strings. Supervenn does not accept pandas Series or dict input directly.

### §8 — Progressive Accumulation / Depletion Curves

**Cell 8.1 — Harshness ordering (complete)**

`HARSHNESS_ORDER` covers all 10 strats × 3 imputations = 30 combinations, ordered from
most permissive to most aggressive. Within each strat, imputation order is:
`strict` (fewest genes, no imputation) → `knn` → `softimpute` (most genes restored).

```python
# HARSHNESS_ORDER: ordered from permissive (most data/genes) → aggressive (least data/genes).
# Strat harshness follows ALL_STRATS index (S0=no removal → G=Affymetrix-only).
# Within each strat, softimpute recovers the most genes (strict < knn < softimpute).
HARSHNESS_ORDER = [
    ("S0_no_removal",    "strict"),
    ("S0_no_removal",    "knn"),
    ("S0_no_removal",    "softimpute"),
    ("A_confirmed_bad",  "strict"),
    ("A_confirmed_bad",  "knn"),
    ("A_confirmed_bad",  "softimpute"),
    ("B_extended_bad",   "strict"),
    ("B_extended_bad",   "knn"),
    ("B_extended_bad",   "softimpute"),
    ("C_rnaseq_only",    "strict"),
    ("C_rnaseq_only",    "knn"),
    ("C_rnaseq_only",    "softimpute"),
    ("D_malignant_only", "strict"),
    ("D_malignant_only", "knn"),
    ("D_malignant_only", "softimpute"),
    ("E1_iterative_r1",  "strict"),
    ("E1_iterative_r1",  "knn"),
    ("E1_iterative_r1",  "softimpute"),
    ("E2_iterative_r2",  "strict"),
    ("E2_iterative_r2",  "knn"),
    ("E2_iterative_r2",  "softimpute"),
    ("E3_iterative_r3",  "strict"),
    ("E3_iterative_r3",  "knn"),
    ("E3_iterative_r3",  "softimpute"),
    ("F_microarray_only","strict"),
    ("F_microarray_only","knn"),
    ("F_microarray_only","softimpute"),
    ("G_affymetrix_only","strict"),
    ("G_affymetrix_only","knn"),
    ("G_affymetrix_only","softimpute"),
]
# Filter to only include combinations that actually exist in gene_sets_by_strat_imp.
# When running with a subset of strats/imps, this gracefully omits missing steps.
HARSHNESS_ORDER = [si for si in HARSHNESS_ORDER if si in gene_sets_by_strat_imp]

# 25_angel is tracked as a separate point: it applies the most aggressive INTERNAL
# gene-level filtering (retains only genes with low batch variance as estimated by ANGEL).
# On the gene retention curves (§8.2, §10, §11.4), Angel is plotted as a horizontal
# reference line labeled "25_angel (most restrictive)" using the most permissive
# (S0_no_removal, strict) Angel gene set as the representative.
angel_representative_genes = gene_sets_angel.get(("S0_no_removal", "strict"), set())
print(f"HARSHNESS_ORDER steps: {len(HARSHNESS_ORDER)}")
print(f"Angel gene set size (reference): {len(angel_representative_genes)}")
```

**Cell 8.2 — Gene retention curve**

Two panels side by side:
- Panel 1 (line): x = harshness step index, y1 = n_genes (solid), y2 = cumulative union (dashed).
  Add a horizontal dashed line for `len(angel_representative_genes)` labeled "25_angel".
  Secondary x-axis shows `(strat, imp)` labels rotated 45°.
- Panel 2 (stacked bar): genes lost vs. previous step (red) over genes retained (blue).

Compute separately for `post_rm=False` (solid/full) and `post_rm=True` (dashed/lighter).

**Cell 8.3 — Imputation recovery supervenn**

Fix `strat = "A_confirmed_bad"`, compare strict / knn / softimpute gene sets.
Also print `recovered_knn`, `recovered_soft`, and the overlap between them.

### §9 — GO Enrichment Analysis Setup

**Cell 9.1 — Download GO database files**

Check for existing files in:
1. Current directory (`.`)
2. `../../Retroelements/T2T_genes_article/T2T_transposons_genes/` (BG project cache)
3. Download from `http://purl.obolibrary.org/obo/go/go-basic.obo` and
   `http://geneontology.org/gene-associations/goa_human.gaf.gz` only if not found above

See `metrics_notebook_plan.md §9.1` for exact code structure.

**Cell 9.2 — Load GO DAG and associations**

```python
def load_go_database(obo_path: str, gaf_path: str) -> tuple[object, dict[str, set[str]], list[str]]:
    """
    Load the Gene Ontology DAG and human gene → GO term associations.

    The background gene list is fixed to ALL genes with GO annotations in the GAF file,
    not a subset of the current harmonization dataset. Using a dataset-specific background
    would introduce a bias: as more genes are included (less harsh filtering), the background
    grows, making GO terms harder to detect — the opposite of the expected biological signal.
    Fixing the background to the full GO universe ensures that enrichment strength correctly
    increases when more biologically relevant genes are present.

    Parameters
    ----------
    obo_path : str
        Path to go-basic.obo file.
    gaf_path : str
        Path to goa_human.gaf file (not compressed).

    Returns
    -------
    godag : GODag
        Loaded GO DAG object.
    full_assoc : dict[str, set[str]]
        Mapping gene symbol → set of GO IDs.
    GO_BACKGROUND : list[str]
        Sorted list of all gene symbols present in the GAF file.
    """
```

**Cell 9.3 — `run_goatools_enrichment` function**

See `metrics_notebook_plan.md §9.3` for full code. Key additions:
- Accept `min_study_count: int = 3` to filter GO terms with fewer than 3 study genes
- Return `pd.DataFrame` with a `study_genes_str` column (comma-separated string, not a
  Python list) so the DataFrame can be directly exported to CSV

### §10 — Progressive GO Term Accumulation Curves

**Cell 10.1 — Harshness-ordered gene sets for GO analysis**

Reuse `HARSHNESS_ORDER` from §8. For each step, the gene set is the union across all
normalization methods excluding `25_angel` (angel is tracked separately; it is plotted
as a horizontal reference line on the accumulation curves, same as in §8.2).

Cross-reference with `full_assoc` keys to get the GO-annotated subset.

**Cell 10.2 — GO enrichment at each step**

Run `run_goatools_enrichment` for each `HARSHNESS_ORDER` step. Cache results to disk
(`go_cache/{strat}_{imp}.parquet`) so the notebook can be re-run without re-computing.
Check for cached files at the start of the cell.

```python
# Cache GO results to avoid re-running expensive enrichments on notebook reload.
# Each parquet file is ~50–200 KB; loading is ~100x faster than re-running goatools.
GO_CACHE_DIR = Path("go_cache")
GO_CACHE_DIR.mkdir(exist_ok=True)
```

Also run GO enrichment on the `25_angel` representative gene set and cache separately as
`go_cache/angel_reference.parquet`. This result is plotted as a horizontal reference line
on the accumulation curve.

**Cell 10.3 — Plot GO accumulation curve**

Three-panel figure:
- Panel 1: n_genes (solid) and cumulative unique GO terms (dashed) vs harshness step.
  Add horizontal line for `25_angel` gene count and GO term count.
- Panel 2: new unique GO terms vs. previous step (bar chart per step).
- Panel 3: `n_new_terms / n_genes_added` (biological information density per gene added).

**Cell 10.4 — Terms lost between adjacent strategy pairs**

For each adjacent pair in `HARSHNESS_ORDER`, show top-20 GO terms lost.
For the dissertation, produce one focused figure for the pair with the largest term loss.

**Cell 10.5 — Imputation-specific term recovery: supervenn**

For `strat = A_confirmed_bad`, compare GO term sets from strict / knn / softimpute.
Use supervenn for the 3-way comparison.

### §11 — FL-Specific Gene Retention Analysis

**Cell 11.0 — Gene set source citations (markdown)**

Insert the citation table from §A.6 here again (at the start of §11, so it is directly
visible when opening Part 2 without scrolling back to §5.6).

**Cell 11.1 — Compile FL gene list**

See `metrics_notebook_plan.md §11.1` for the four sources. After assembling `FL_GENES_ALL`,
run HGNC alias validation:

```python
def validate_gene_aliases(gene_list: list[str], reference_genes: set[str]) -> dict[str, str]:
    """
    Check which genes from a curated list are absent from the expression matrices
    and propose HGNC alias resolution.

    Known aliases to check (update if expression matrix uses different symbols):
    - MME  ↔ CD10  (neprilysin; HGNC primary = MME)
    - FAS  ↔ CD95  ↔ TNFRSF6  (HGNC primary = FAS)
    - FCER2 ↔ CD23  (HGNC primary = FCER2)

    Parameters
    ----------
    gene_list : list[str]
        Curated gene symbols to validate.
    reference_genes : set[str]
        Union of all gene_sets values (not 25_angel) used as the reference universe.

    Returns
    -------
    dict[str, str]
        Mapping absent_symbol → suggested_replacement. Empty if all genes are found.
    """
```

**Cell 11.2 — FL gene presence matrix**

See `metrics_notebook_plan.md §11.2`. Build `fl_presence` binary DataFrame
(rows = FL genes, columns = harmonization attempts). Sort rows by gene category.

**Cell 11.3 — FL gene retention heatmap**

Binary heatmap (present = dark green, absent = light red):
- Rows = FL genes, grouped by category
- Columns = harmonization attempts, ordered by composite_score descending
- Add a vertical dashed line after the top-10 methods

**Cell 11.4 — FL gene progressive retention curves**

Two figures (see `metrics_notebook_plan.md §11.4` for code):
- Figure A: one subplot per FL gene category, fraction retained along harshness axis
- Figure B: overall FL gene retention curve + per-category thin lines

Both figures use the full `HARSHNESS_ORDER` (all 30 steps). Add a horizontal reference line
showing the fraction retained when using `25_angel` (plotted at the rightmost position on
the x-axis, labeled "Angel" with a distinct marker, since Angel's filtering is orthogonal
to the strat/imp axis — it is the gene-level analogue of the most aggressive sample-level
filtering).

**Cell 11.5 — GO enrichment in FL-specific gene subset**

See `metrics_notebook_plan.md §11.5`. Display two horizontal dot plots.

**Cell 11.6 — Progressive FL-genes GO accumulation curve**

Same as §11.4 but in GO space. Add `25_angel` reference line.

**Cell 11.7 — Final recommendation table**

Summary DataFrame combining composite score, n_genes, FL gene retention, key metrics, and
boolean flags. Sorted by composite_score descending. Styled with background gradients.
Export: `recommendation_table.csv` + upload to S3 under `FL_batch_correction/`.

---

## Part E — Final Notebook Cleanup (after all sections are written)

### E.1 — Restart-and-run-all validation

The notebook must execute cleanly in a single `Kernel → Restart & Run All` with no manual
intervention. Check:
- All S3 downloads are wrapped in `try/except botocore.exceptions.ClientError`
- All optional metric columns are guarded with `if col in df_ok.columns`
- GO enrichment cells check for cached parquet files before re-running
- `HARSHNESS_ORDER` is filtered to only available (strat, imp) pairs

### E.2 — Section separator pattern

Every top-level section (`§1`–`§11`) must begin with a markdown cell:

```markdown
---
## §N — Section Title

One-sentence description of what this section computes and what question it answers.
```

### E.3 — Figures directory and naming convention

| Section | Filename prefix |
|---|---|
| §2 clustermap | `clustermap_*` |
| §3.1 PCA R² | `a_r2_*`, `a_pcr_*`, `a_dsc_*` |
| §3.2 neighbor | `b_kbet_*`, `b_asw_*`, `b_cms_*` |
| §3.3 embedding | `c_umap_*`, `c_tsne_*` |
| §3.4 distribution | `d_ks_*`, `d_cv_*` |
| §3.5 data quality | `e_genes_*`, `e_bimodal_*`, `e_exp_*` |
| §3.6 graph/dist | `g_graph_*`, `h_dist_*` |
| §4 scoring | `score_radar_*`, `score_pareto_*`, `score_ranking_*` |
| §5 inspection | `pca_grid_*`, `umap_grid_*`, `tsne_grid_*`, `violins_*`, `cv_vs_exp_*` |
| §7 gene overlap | `gene_jaccard_*`, `supervenn_*` |
| §8 accumulation | `gene_retention_curve_*` |
| §10 GO | `go_accumulation_*`, `go_lost_terms_*` |
| §11 FL retention | `fl_retention_heatmap_*`, `fl_retention_curves_*`, `fl_go_dot_*` |

---

## Summary: What Is Left to Implement

| Priority | Section | Status | Key changes vs. original plan |
|---|---|---|---|
| **1** | Global docs (A.1–A.3) | ✅ DONE | Polarity rationale, SCORE_WEIGHTS rationale, NaN fill comment |
| **2** | Palette redesign (A.2) | ✅ DONE | Sepia batch annot_pal, vivid group_pal, preserve imp_pal |
| **3** | Scratch cleanup (A.4) | ✅ DONE | Remove/merge ~11 cells |
| **4** | Clustermap orientation (B.1–B.3) | ✅ DONE | Uniform row_colors/col_colors assignment per B.1 |
| **5** | §5 canonical palettes (C Cell 5.0) | ✅ DONE (cell 070) | rna_batch_palette, lymphoma_ontogeny_palette, platform_palette |
| **6** | §5.1–5.4 S3 helpers + grids | ✅ DONE (cells 071–074) | PCA/UMAP/tSNE with canonical palettes |
| **7** | §5.5 violins + CV curves | ✅ DONE (cell 075) | CV-vs-expression curves merged into cell 075 |
| **8** | §5.6 markers + citations | ✅ DONE (cells 076–077) | Citation markdown + housekeeping/marker cell |
| **9** | §6–§7 gene download + overlap | ✅ DONE (cells 078–086) | 25_angel tracked separately; Jaccard + supervenn |
| **10** | §8 accumulation curves | ✅ DONE (cells 087–090) | Full 30-step HARSHNESS_ORDER + Angel reference line |
| **11** | §9–§10 GO analysis | ✅ DONE (cells 091–100) | Angel reference line in GO accumulation plot |
| **12** | §11 FL retention | ✅ DONE (cells 101–109) | Angel reference line in FL retention curves |
| **13** | §A.6 + §11.0 citations | ✅ DONE (cells 076, 102) | Added at §5.6 and §11.0 |
| **14** | Final cleanup (E.1–E.3) | ✅ DONE | Section separators added; all sections have E.2 headers |
