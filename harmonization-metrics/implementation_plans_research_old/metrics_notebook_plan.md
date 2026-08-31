# Implementation Plan: Harmonization Metrics Analysis Notebook

**Date:** 2026-05-01  
**Author:** Daniil Nikitin  
**Purpose:** Comprehensive Jupyter notebook for analysis of batch effect metrics and gene sets across all harmonization attempts.  
**Input data:**
- `metrics_comprehensive_260501.csv` — currently 82 rows × 205 columns; will grow to ~1,000+ rows as all strat × imp × method combinations complete
- `s3://$FL_S3_BUCKET/FL_batch_correction/genes/*_genes.json` — per-harmonization gene lists
- Expression matrices on S3 (for top-N inspection): `FL_batch_correction/exp/*.tsv.gz`
- Annotation on S3: `FL_batch_correction/prepared/*__ann.tsv.gz`

---

## Notebook structure overview — these should be actual sections and subsections of the notebook

```
Part 1 — Metrics Analysis
  §1   Setup and data loading
  §2   Full heatmap / clustermap of all metrics
  §3   Group-by-group comparative analysis
  §4   Composite scoring and top-10 selection
  §5   Visual inspection of top approaches (PCA / UMAP / tSNE / distributions)

Part 2 — Gene Set Analysis
  §6   Download gene lists from S3
  §7   Gene count and overlap analysis
  §8   Progressive accumulation / depletion curves (genes)
  §9   GO enrichment analysis — setup
  §10  Progressive GO term accumulation curves
  §11  FL-specific gene retention analysis
```

---

## Part 1: Metrics Analysis

---

### §1 — Setup, imports, and data loading

**Cell 1.1 — Imports**

```python
import boto3
import json, math, re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from matplotlib.colors import ListedColormap, BoundaryNorm, Normalize, to_hex
from matplotlib.gridspec import GridSpec
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import squareform, pdist
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
import umap as umap_lib
from sklearn.manifold import TSNE

plt.rcParams.update({"pdf.fonttype": 42, "svg.fonttype": "none",
                      "figure.dpi": 200, "font.size": 10})
sns.set_style("ticks")
FIGURES_DIR = Path("figures")
FIGURES_DIR.mkdir(exist_ok=True)
```

**Cell 1.2 — Load metrics CSV and define metadata**

```python
df = pd.read_csv("metrics_comprehensive_260501.csv")

# Row identifier
df["run_id"] = df["strat"] + "__" + df["imp"] + "__" + df["method"]
df = df.set_index("run_id")

META_COLS = ["strat", "imp", "method", "post_rm", "status", "compute_time_s"]

# Keep only successful rows for metric analysis
df_ok = df[df["status"] == "ok"].copy()
print(f"Total rows: {len(df)},  successful: {len(df_ok)},  failed: {(df['status']=='failed').sum()}")
```

**Cell 1.3 — Column taxonomy**

Define the metadata needed to colour metric columns by group and by annotation column:

```python
# ── Metric group assignment ─────────────────────────────────────────────────
GROUP_MAP = {
    "A": ["r2_", "pcr_", "dsc_"],
    "B": ["kbet_", "ilisi_", "clisi_", "asw_batch", "asw_bio", "cms_"],
    "C": ["umap_", "tsne_"],
    "D": ["ks_", "per_gene_batch"],
    "E": ["n_samples","n_genes","n_batches","n_cohorts","n_diagnosis_groups",
          "n_samples_per_batch","zero_","fraction_","exp_","per_batch_median","bimodal"],
    "F": ["vp_"],
    "G": ["graph_"],
    "H": ["avg_intra_","avg_inter_","dist_ratio_"],
}

# ── Annotation column associated with each metric column ────────────────────
ANNOT_COLS = ["RNA_BATCH","PLATFORM_RNA","RNASEQ_SOURCE","COHORT_LABEL",
              "Major_group","Diagnosis_cell_type_unified","TUMOR_NORMAL","global/all"]

# Build lookup dict: metric_col -> (group, annot_col)
def classify_metric_col(col):
    grp = "?"
    for g, prefixes in GROUP_MAP.items():
        if any(col.startswith(p) or col == p.rstrip("_") for p in prefixes):
            grp = g; break
    annot = "global/all"
    for a in ANNOT_COLS[:-1]:
        if a in col:
            annot = a; break
    return grp, annot

metric_cols = [c for c in df_ok.columns if c not in META_COLS and not c.startswith("error") and not c.startswith("r2_pc")]
col_meta = pd.DataFrame(
    [classify_metric_col(c) for c in metric_cols],
    index=metric_cols, columns=["group","annot_col"]
)
```

**Cell 1.4 — Define metric polarity (higher=better or lower=better)**

This is needed for normalization so that "best" always points in one direction in heatmaps and composite scoring.

```python
# Polarity: +1 means "higher is better", -1 means "lower is better"
POLARITY = {}
for c in metric_cols:
    g, _ = classify_metric_col(c)
    if g in ("A", "D", "C"):  # r2, ks, dsc, umap/tsne dispersion: lower=better
        POLARITY[c] = -1
    elif g == "B":
        if "asw_batch" in c and "norm" not in c:   POLARITY[c] = -1
        elif "asw_bio" in c and "norm" not in c:   POLARITY[c] = +1
        elif "norm" in c and "batch" in c:         POLARITY[c] = +1
        elif "norm" in c and "bio" in c:           POLARITY[c] = +1
        elif any(x in c for x in ("kbet","ilisi","clisi","cms")):      POLARITY[c] = +1
        else:                                       POLARITY[c] = +1
    elif g == "G":   POLARITY[c] = +1
    elif g == "H":
        if "dist_ratio" in c:   POLARITY[c] = -1
        else:                    POLARITY[c] = 0
    elif g == "F":   POLARITY[c] = -1 if "RNA_BATCH" in c else +1
    else:            POLARITY[c] = 0   # group E descriptive: not used in scoring

scoring_cols  = [c for c in metric_cols if POLARITY.get(c, 0) != 0]
desc_cols     = [c for c in metric_cols if POLARITY.get(c, 0) == 0]
```

**Cell 1.5 — Normalize metrics to [0,1] where 1=best**

```python
def normalize_for_display(df_vals, cols, polarity_map):
    """MinMax normalize each column; flip negative-polarity columns so 1=best."""
    normed = df_vals[cols].copy().astype(float)
    scaler = MinMaxScaler()
    normed[cols] = scaler.fit_transform(normed[cols])
    for c in cols:
        if polarity_map.get(c, 1) == -1:
            normed[c] = 1 - normed[c]
    return normed

df_normed = normalize_for_display(df_ok, scoring_cols, POLARITY)
```

**Cell 1.6 — Reusable helper: multi-level boxplot with pairwise Mann-Whitney p-value heatmap**

This helper is used throughout §3 to compare harmonization methods, removal strategies, and imputation approaches. It produces two panels: a boxplot + strip on top, and a pairwise FDR-corrected p-value heatmap below.

```python
def plot_multilevel_comparison(df, metric_col, group_col, ax_box, ax_pval,
                               title=None, ylabel=None, ascending=True):
    """
    Top panel: boxplot + strip of metric_col grouped by group_col.
    Bottom panel: symmetric heatmap of FDR-corrected Mann-Whitney pairwise p-values.
    group_col: one of 'method', 'strat', 'imp'
    """
    groups = sorted(df[group_col].dropna().unique())
    # Collect per-group vectors
    data_by_group = {g: df.loc[df[group_col] == g, metric_col].dropna().values
                     for g in groups}
    # Boxplot
    ax_box.boxplot([data_by_group[g] for g in groups], labels=groups, patch_artist=True)
    for i, g in enumerate(groups):
        ax_box.scatter(np.full(len(data_by_group[g]), i + 1),
                       data_by_group[g], alpha=0.4, s=10)
    if title: ax_box.set_title(title, fontsize=10)
    if ylabel: ax_box.set_ylabel(ylabel)
    ax_box.set_xticklabels(groups, rotation=45, ha="right", fontsize=8)
    # Pairwise FDR-corrected Mann-Whitney
    n = len(groups)
    pmat = np.ones((n, n))
    raw_pvals, pairs = [], []
    for i in range(n):
        for j in range(i + 1, n):
            a, b = data_by_group[groups[i]], data_by_group[groups[j]]
            if len(a) > 0 and len(b) > 0:
                _, p = mannwhitneyu(a, b, alternative="two-sided")
                raw_pvals.append(p); pairs.append((i, j))
    if raw_pvals:
        _, fdr_pvals, _, _ = multipletests(raw_pvals, method="fdr_bh")
        for (i, j), p in zip(pairs, fdr_pvals):
            pmat[i, j] = p; pmat[j, i] = p
    log_pmat = -np.log10(np.clip(pmat, 1e-300, 1))
    sns.heatmap(log_pmat, ax=ax_pval, xticklabels=groups, yticklabels=groups,
                cmap="YlOrRd", vmin=0, cbar_kws={"label": "-log10(FDR p-value)"})
    ax_pval.set_xticklabels(groups, rotation=45, ha="right", fontsize=8)
    ax_pval.set_yticklabels(groups, rotation=0, fontsize=8)
```

---

### §2 — Full heatmap / clustermap of all metrics

**Goal:** One large clustermap (seaborn `clustermap`) where:
- **Rows** = harmonization attempts (~1,000 rows at full scale), clustered by Euclidean / Ward linkage
- **Columns** = all scoring metric columns (~140 cols), clustered
- **5 row color bars** (left side):
  - `strat` (all 10 strategies: S0_no_removal, A_confirmed_bad, B_extended_bad, C_rnaseq_only, D_malignant_only, E1_iterative_r1, E2_iterative_r2, E3_iterative_r3, F_microarray_only, G_affymetrix_only)
  - `imp` (3 levels: strict, knn, softimpute)
  - `method` (25 levels — bright/vivid palette)
  - `post_rm` (2 levels: False = post0, True = post1)
  - `composite_score` (continuous; diverging colormap applied after §4)
- **2 column color bars** (top):
  - `metric_group` (8 levels: A–H)
  - `annot_col` (8 levels: RNA_BATCH, PLATFORM_RNA, RNASEQ_SOURCE, COHORT_LABEL, Major_group, Diagnosis_cell_type_unified, TUMOR_NORMAL, global/all)

**Palette design philosophy:** 
Each of the 7 palettes (strat, imp, method, post_rm, metric_group, annot_col, composite_score) must be clearly distinguishable from all others. The strategy is:
- `strat` — **pastel** palette (soft, muted tones): pastel blue, pastel orange, pastel green, pastel red, etc. 10 distinct pastel colors.
- `imp` — **dark** palette (deep, saturated): dark teal, dark crimson, dark purple. 3 clearly dark colors.
- `method` — **bright and vivid** palette: `tab20` with boosted saturation, or a custom palette with pure primary/secondary colors. 25 distinct vivid colors.
- `post_rm` — **neutral grayscale**: light gray (post0=False), near-black (post1=True). Intentionally plain so it doesn't compete.
- `metric_group` — **Set1** (bold and widely used): ensures each group A–H is immediately recognizable. Must not share hues with `strat` pastel palette — use the primary-color Set1 which is distinct from pastels.
- `annot_col` — **muted/desaturated** categorical: `Set2` or similar. Must not overlap with Set1 used for metric groups or with pastel strat colors.
- `composite_score` — continuous diverging colormap (`RdYlGn`), not a categorical palette.

Within each categorical palette, internal colors are chosen to be maximally different from each other (blue, red, yellow, green variants within each palette). Across palettes, the same "hue family" is used with a different saturation/lightness so that, e.g., strat's pastel-blue, imp's dark-teal, method's vivid-cyan, and annot_col's muted-blue are all clearly distinct despite sharing a blue hue family.

**Cell 2.1 — Build row color palette DataFrames**

```python
import matplotlib.colors as mcolors

# ── Strat: pastel palette (all 10 strategies) ────────────────────────────────
ALL_STRATS = [
    "S0_no_removal", "A_confirmed_bad", "B_extended_bad",
    "C_rnaseq_only", "D_malignant_only",
    "E1_iterative_r1", "E2_iterative_r2", "E3_iterative_r3",
    "F_microarray_only", "G_affymetrix_only",
]
pastel_colors = sns.color_palette("pastel", n_colors=10)
strat_pal = dict(zip(ALL_STRATS, pastel_colors))

# ── Imp: dark palette ────────────────────────────────────────────────────────
imp_pal = {
    "strict":     "#1B4F72",   # dark navy
    "knn":        "#641E16",   # dark crimson
    "softimpute": "#4A235A",   # dark purple
}

# ── Method: bright/vivid palette (25 methods) ────────────────────────────────
ALL_METHODS = sorted(df_ok.method.unique())
vivid_colors = sns.color_palette("tab20", n_colors=20) + sns.color_palette("tab20b", n_colors=5)
method_pal = dict(zip(ALL_METHODS, vivid_colors[:len(ALL_METHODS)]))

# ── Post-rm: neutral grayscale (2 levels) ────────────────────────────────────
post_rm_pal = {False: "#CCCCCC", True: "#333333"}

row_colors = pd.DataFrame({
    "strat":   df_ok.strat.map(strat_pal),
    "imp":     df_ok.imp.map(imp_pal),
    "method":  df_ok.method.map(method_pal),
    "post_rm": df_ok.post_rm.map(post_rm_pal),
}, index=df_ok.index)
```

**Cell 2.2 — Build column color palette DataFrames**

```python
# ── Metric group: Set1 (bold primary colors) ─────────────────────────────────
group_pal = dict(zip("ABCDEFGH", sns.color_palette("Set1", n_colors=8)))

# ── Annotation column: muted/desaturated (Set2) ──────────────────────────────
# Set2 is distinct from Set1 (muted vs. bold) and from pastel (desaturated vs. soft-light)
annot_pal = dict(zip(
    ["RNA_BATCH","PLATFORM_RNA","RNASEQ_SOURCE","COHORT_LABEL",
     "Major_group","Diagnosis_cell_type_unified","TUMOR_NORMAL","global/all"],
    sns.color_palette("Set2", n_colors=8),
))

col_colors = pd.DataFrame({
    "group":     col_meta.loc[scoring_cols, "group"].map(group_pal),
    "annot_col": col_meta.loc[scoring_cols, "annot_col"].map(annot_pal),
}, index=scoring_cols)
```

**Cell 2.3 — Clustered clustermap (rows and columns clustered)**

```python
g = sns.clustermap(
    df_normed[scoring_cols],
    method="ward", metric="euclidean",
    row_colors=row_colors, col_colors=col_colors,
    cmap="RdYlGn", center=0.5, vmin=0, vmax=1,
    linewidths=0, figsize=(28, 22),
    cbar_pos=(0.02, 0.8, 0.015, 0.15),
    dendrogram_ratio=(0.15, 0.08),
    xticklabels=False, yticklabels=True,
)
g.ax_heatmap.set_xlabel("")
# Add color-bar legends for all palettes (strat, imp, method, post_rm, group, annot_col)
# ... [legend patches built with mpatches.Patch, placed outside the figure]
g.fig.savefig(FIGURES_DIR / "clustermap_all_metrics_clustered.svg", bbox_inches="tight")
```

**Cell 2.4 — Grouped heatmap (columns ordered by metric group then annot_col; no column clustering)**

Useful for reading the heatmap without dendrogram reordering scrambling the biological interpretation.

```python
col_order = col_meta.loc[scoring_cols].sort_values(["group","annot_col"]).index.tolist()
g2 = sns.clustermap(
    df_normed[col_order],
    method="ward", metric="euclidean",   # rows still clustered
    col_cluster=False,
    row_colors=row_colors, col_colors=col_colors.loc[col_order],
    cmap="RdYlGn", center=0.5, vmin=0, vmax=1,
    linewidths=0, figsize=(28, 22),
    xticklabels=False, yticklabels=True,
)
g2.fig.savefig(FIGURES_DIR / "clustermap_all_metrics_grouped_cols.svg", bbox_inches="tight")
```

**Cell 2.5 — Ordered heatmap (no clustering at all — fixed row and column order for structural overview)**

Rows sorted by: strat → imp → method → post_rm (all in their natural categorical order). Columns sorted by: metric group → annot_col. This view reveals the regular block structure of the data without any dendrogram reordering, making it easy to read the systematic variation.

```python
# Row order: sort by strat harshness, then imp, then method alphabetically, then post_rm
ROW_ORDER = (
    df_ok.assign(_si=pd.Categorical(df_ok.strat, categories=ALL_STRATS, ordered=True))
    .sort_values(["_si", "imp", "method", "post_rm"])
    .index.tolist()
)

fig, ax = plt.subplots(figsize=(28, 22))
sns.heatmap(
    df_normed.loc[ROW_ORDER, col_order],
    ax=ax,
    cmap="RdYlGn", center=0.5, vmin=0, vmax=1,
    linewidths=0,
    xticklabels=False, yticklabels=True,
    cbar_kws={"shrink": 0.3},
)
ax.set_title("Ordered overview — rows: strat/imp/method/post_rm; cols: group/annot_col")
fig.savefig(FIGURES_DIR / "heatmap_ordered_no_clustering.svg", bbox_inches="tight")
```

---

### §3 — Group-by-group comparative analysis

**Repeated pattern across all subsections:** For every quantitative comparison, produce three flavors of the boxplot:
1. Groups = **harmonization methods** (25 methods)
2. Groups = **removal strategies** (10 strats)
3. Groups = **imputation approaches** (strict / knn / softimpute)

Each boxplot is accompanied by a pairwise FDR-corrected Mann-Whitney p-value heatmap directly below it, using the `plot_multilevel_comparison` helper defined in §1.6. This triple-panel comparison appears consistently throughout §3.

#### §3.1 — Group A: PCA Variance Decomposition

**Cell 3.1.1 — Grouped bar chart of mean R² per covariate × method**

For each method, show a grouped bar chart with mean ± std of `r2_RNA_BATCH`, `r2_Major_group`, `r2_TUMOR_NORMAL`, `r2_PLATFORM_RNA` across imputation strategies. X-axis: method (sorted by `r2_RNA_BATCH`); y: R²; hue: covariate. Reference line at 0.20 (target for `r2_RNA_BATCH`).

**Cell 3.1.2 — catplot comparing imputations and harmonization methods on a single metric**

`sns.catplot` with `kind="box"`, `col="imp"`, `x="method"`, `y="r2_RNA_BATCH"`. This allows direct comparison of how the same method performs across different imputation strategies in a single figure.

**Cell 3.1.3 — Multi-level boxplot + p-value heatmap for r2_RNA_BATCH**

Three sub-figures using `plot_multilevel_comparison`:
- Figure A: grouped by harmonization method
- Figure B: grouped by removal strategy (strat)
- Figure C: grouped by imputation approach

Each sub-figure is a 2-row layout: boxplot + strip on top, p-value heatmap on bottom.

**Cell 3.1.4 — PCR strip plot (A3 — variance-weighted R²)**

Strip plot + box: x = method, y = `pcr_RNA_BATCH`, colored by `strat`. Separate panel for `pcr_Major_group` and `pcr_TUMOR_NORMAL` as biology preservation check. Multi-level comparison (method / strat / imp) with p-value heatmaps.

**Cell 3.1.5 — Per-PC R² heatmap (A2 — PC profiles)**

For each method, show a heatmap of r2_pc{1..10}_RNA_BATCH (rows = methods, cols = PC1–PC10). Useful to see if batch effect is concentrated in PC1 (sharp) or spread across many PCs (diffuse).

**Cell 3.1.6 — DSC scatterplot (A4)**

Scatter: x = `dsc_RNA_BATCH`, y = `dsc_COHORT_LABEL`, point color = method family (r-based, combat-based, etc.), point size ∝ `r2_RNA_BATCH`. Helps see whether global (RNA_BATCH) and local (COHORT) batch effects are jointly reduced.

#### §3.2 — Group B: Neighbor-based Integration

**Cell 3.2.1 — kBET vs iLISI scatter**

Scatter: x = `kbet_acceptance_rate_RNA_BATCH`, y = `ilisi_norm_RNA_BATCH`, hue = method, shape = strat, size = imputation (strict/knn/softimpute mapped to 3 marker sizes), additional secondary size encoding = `n_genes` (use a continuous normalization overlaid or a secondary figure). Both axes: higher = better. Multi-level comparison with p-value heatmaps.

**Cell 3.2.2 — Biology preservation: ASW_bio × cLISI**

Two-panel figure: left = `asw_bio_norm_Major_group` by method (boxplot + strip), right = `clisi_mean_Major_group` by method. These together show whether biological signal is preserved. Multi-level comparison (method / strat / imp) with pairwise p-value heatmaps as described above.

**Cell 3.2.3 — Batch–biology trade-off scatter (central diagnostic)**

For each harmonization attempt, plot two versions side by side:
- Panel A: x = `asw_batch_norm_RNA_BATCH`, y = `asw_bio_norm_Major_group`. Points labeled by method, colored by imputation.
- Panel B: x = `asw_batch_norm_RNA_BATCH`, y = `asw_bio_norm_Diagnosis_cell_type_unified`. Same layout.

Add a diagonal reference line in each panel: points above the diagonal = biology better preserved than batch mixed. This is the core trade-off plot for the dissertation. Each panel should clearly label the best-performing points.

**Cell 3.2.4 — CMS fractional mixing — subplot grid over all batch columns**

Subplots grid (one column = one batch column tested: RNA_BATCH, PLATFORM_RNA, RNASEQ_SOURCE, COHORT_LABEL). For each panel: boxplot of `cms_fraction_mixed_{batch_col}` by method, split by strat. Highlight methods above 0.50. Multi-level comparison with p-value heatmaps within each panel.

#### §3.3 — Group C: Embedding Metrics

**Cell 3.3.1 — UMAP/tSNE centroid dispersion — subplot grid over all batch columns**

Subplots grid: rows = embedding type (UMAP, tSNE), columns = batch column (RNA_BATCH, PLATFORM_RNA, RNASEQ_SOURCE, COHORT_LABEL). Each panel: grouped bar of centroid dispersion by method. Lower = better. Multi-level comparison with p-value heatmaps.

**Cell 3.3.2 — UMAP vs tSNE entropy correlation — multiple batch columns**

One scatter panel per batch column (RNA_BATCH, PLATFORM_RNA, RNASEQ_SOURCE, COHORT_LABEL): x = `umap_entropy_norm_{col}`, y = `tsne_entropy_norm_{col}`. Pearson correlation annotated in each panel. Methods far from the diagonal behave differently in UMAP vs tSNE.

#### §3.4 — Group D: Distribution Metrics

**Cell 3.4.1 — KS D-statistic — subplot grid over all batch columns**

Subplots grid: one panel per batch column (RNA_BATCH, PLATFORM_RNA, RNASEQ_SOURCE, COHORT_LABEL). Each panel: box + strip of `ks_mean_D_{col}` by method, split by imp. Lower = better. Annotate methods with `ks_frac_sig_{col} > 0.5` in red. Multi-level comparison with p-value heatmaps.

**Cell 3.4.2 — Within-batch cohort D-statistic**

Scatter: x = `ks_mean_D_RNA_BATCH` (platform-level), y = `ks_cohort_within_batch_mean_D` (within-platform cohort residuals). Shows whether correction removes cohort effects within platforms.

**Cell 3.4.3 — Per-gene batch mean CV — subplot grid over all batch columns**

Subplots grid: one panel per batch column. Bar chart of `per_gene_batch_mean_cv_{col}` by method (sorted ascending). Lower = better. Multi-level comparison with p-value heatmaps.

#### §3.5 — Group E: Data Quality

**Cell 3.5.1 — Gene and sample count by harmonization**

Grouped bar: x = (strat, imp) ordered by harshness, y = `n_genes` and `n_samples`. Show that more aggressive batch removal loses genes and samples. Also compare imputation methods (strict vs knn vs softimpute) and removal strategies side by side using the multi-level comparison with p-value heatmaps.

**Cell 3.5.2 — Bimodality landscape**

Scatter: x = `fraction_cohorts_bimodal`, y = `fraction_cohorts_zero_inflated_bimodal`, hue = method, size = `n_cohorts`. Compare how imputation methods affect bimodality — imputation has a large effect on the distribution shape and bimodality. Multi-level comparison (grouped by imputation, grouped by strat) with p-value heatmaps.

**Cell 3.5.3 — Expression statistics overview**

Table + heatmap: exp_median, exp_std, exp_p01, exp_p99 per method. Rows = methods. Color rows by removal strategy (one color palette strip on the left), imputation approach (next strip), and harmonization method (next strip) so the systematic variation is visible. Each statistics column gets its own color gradient.

#### §3.6 — Groups G and H: Graph Connectivity and Euclidean Distances

**Cell 3.6.1 — Graph connectivity by biology group**

Subplots grid: one panel per biology column (Major_group, Diagnosis_cell_type_unified, TUMOR_NORMAL). Each panel: box + strip of `graph_connectivity_{col}` by method. Higher = better. Multi-level comparison (method / strat / imp) with pairwise p-value heatmaps.

**Cell 3.6.2 — Distance ratio for batch vs biology**

Four-panel figure (2 rows × 2 columns):
- Row 1 (batch): `dist_ratio_RNA_BATCH` and `dist_ratio_PLATFORM_RNA` by method (lower = better mixing)
- Row 2 (biology): `dist_ratio_Major_group` and `dist_ratio_Diagnosis_cell_type_unified` by method (lower = tighter biology clusters = better preservation)

For each panel: strip + box, hue = strat. Multi-level comparison with p-value heatmaps.

---

### §4 — Composite Scoring and Top-10 Selection

**Cell 4.1 — Literature review: weights for batch effect metrics**

A brief inline summary (Markdown cell) reviewing how different teams and laboratories weight the three major components of batch effect evaluation:

*Batch mixing metrics (Component 1):* PCA R² (r2_RNA_BATCH) is by far the most widely reported metric; it directly quantifies the fraction of transcriptomic variance attributable to platform or batch, and is used as the primary outcome in Tran et al. 2020 (Nature Methods benchmark of 14 single-cell integration methods), Luecken et al. 2022 (OpenProblems scIB benchmark), and the original FSQN paper (Franks et al. 2018). kBET (Buttner et al. 2019) and LISI (Korsunsky et al. 2019, Harmony paper) are neighbor-based corrections that operate in reduced-dimension space and are complementary to PCA R². The scIB benchmark (Luecken et al. 2022) uses kBET as a primary batch correction score and ASW_batch as secondary. Given this consensus, high weight (×3 for R², ×1.5 for kBET and LISI) is appropriate.

*Biology preservation metrics (Component 2):* ASW_bio and graph connectivity are the two most common biology preservation metrics in scIB. The Luecken et al. 2022 benchmark assigns equal weight to batch correction (60%) and biology preservation (40%) in the overall score, which motivates the 0.60/0.35 component split used here. R² of Major_group and Diagnosis_cell_type_unified on PCA axes should be maximized (not minimized) — higher biology R² means biology still explains variance after batch removal, which is the desired outcome.

*Data quality metrics (Component 3):* Gene retention and bimodality are rarely used in published benchmarks because they are upstream properties of the data preparation (not the normalization method itself). The 0.05 weight here reflects their role as a sanity check rather than a primary selection criterion.

**Cell 4.2 — Define metric weights and sub-scores**

```python
SCORE_WEIGHTS = {
    # Component 1: Batch mixing (higher normalized score = better batch correction)
    "batch_mixing": {
        "r2_RNA_BATCH":              -3.0,   # primary metric, triple weight
        "pcr_RNA_BATCH":             +2.0,   # variance-weighted version
        "kbet_acceptance_rate_RNA_BATCH": +1.5,
        "ilisi_norm_RNA_BATCH":      +1.5,
        "asw_batch_norm_RNA_BATCH":  +1.5,
        "cms_fraction_mixed_RNA_BATCH": +1.0,
        "umap_entropy_norm_RNA_BATCH": +1.0,
        "dsc_RNA_BATCH":             -1.0,
        "ks_mean_D_RNA_BATCH":       -1.0,
        # PLATFORM_RNA and RNASEQ_SOURCE variants at 0.5×
        "r2_PLATFORM_RNA":           -0.5,
        "r2_RNASEQ_SOURCE":          -0.5,
    },
    # Component 2: Biology preservation (higher = biology intact)
    # Primary biology column: Diagnosis_cell_type_unified (fine-grained)
    # Secondary: Major_group (coarser, kept as alternative)
    "bio_preservation": {
        "r2_Diagnosis_cell_type_unified": +2.0,   # primary biology metric
        "r2_Major_group":            +1.0,          # secondary
        "r2_TUMOR_NORMAL":           +2.0,
        "asw_bio_norm_Diagnosis_cell_type_unified": +1.5,
        "asw_bio_norm_Major_group":  +0.5,
        "clisi_mean_Diagnosis_cell_type_unified":   -1.5,
        "clisi_mean_Major_group":    -0.5,
        "graph_connectivity_Diagnosis_cell_type_unified": +1.0,
        "graph_connectivity_Major_group": +0.5,
        "dist_ratio_Diagnosis_cell_type_unified":   -1.0,
        "dist_ratio_Major_group":    -0.5,
    },
    # Component 3: Data quality (descriptive, lower weight)
    "data_quality": {
        "n_genes":                        +0.5,   # more genes = better
        "fraction_cohorts_bimodal":       +1.0,   # bimodality is good (natural gene expression shape)
        "per_gene_batch_mean_cv_RNA_BATCH": -0.5,
    },
}

COMPONENT_WEIGHTS = {
    "batch_mixing":    0.60,
    "bio_preservation": 0.35,
    "data_quality":    0.05,
}
```

Note: `fraction_cohorts_bimodal` is positive (+1.0) because bimodality is a natural feature of gene expression distributions and is not an artifact. Methods that preserve bimodality are preferred. Zero-inflated bimodality (artificially inflated zero-peak from normalization artifacts) is a separate metric with negative polarity.

Note on Diagnosis_cell_type_unified vs Major_group: `Diagnosis_cell_type_unified` is the primary biology column throughout (finer-grained cell type labels), with `Major_group` as secondary backup. The weights above reflect this hierarchy. Users can toggle to Major_group-only weighting by zeroing out the Diagnosis_cell_type_unified entries.

**Cell 4.3 — Compute composite scores**

```python
def compute_composite_score(df_normed, score_weights, component_weights):
    """Weighted sum of normalized metrics within each component, then component-level weighted sum."""
    scores = {}
    for comp, metrics_dict in score_weights.items():
        comp_scores = pd.Series(0.0, index=df_normed.index)
        total_abs_weight = sum(abs(w) for w in metrics_dict.values())
        for col, weight in metrics_dict.items():
            if col in df_normed.columns:
                direction = 1 if weight > 0 else -1
                contrib = direction * df_normed[col] * abs(weight) / total_abs_weight
                comp_scores += contrib
        scores[comp] = comp_scores
    final = sum(component_weights[k] * scores[k] for k in component_weights)
    return pd.DataFrame(scores), final

component_df, composite_score = compute_composite_score(df_normed, SCORE_WEIGHTS, COMPONENT_WEIGHTS)
df_ok["composite_score"] = composite_score
df_ok["score_batch_mixing"] = component_df["batch_mixing"]
df_ok["score_bio_preservation"] = component_df["bio_preservation"]
```

**Cell 4.4 — Alternative scoring: per-rank aggregation (Borda count)**

```python
for c in scoring_cols:
    df_ok[f"rank_{c}"] = df_ok[c].rank(ascending=(POLARITY[c] == -1))

rank_cols = [f"rank_{c}" for c in scoring_cols]
df_ok["borda_score"] = df_ok[rank_cols].mean(axis=1)
```

**Cell 4.5 — Top-N selection cell (user-editable parameters)**

```python
# === USER PARAMETERS — edit these to select top N ===
N_TOP = 10
SCORE_METHOD = "composite"   # options: "composite", "borda", "batch_only", "bio_only"
# =======================================================

if SCORE_METHOD == "composite":
    sort_col, ascending = "composite_score", False
elif SCORE_METHOD == "borda":
    sort_col, ascending = "borda_score", True
elif SCORE_METHOD == "batch_only":
    sort_col, ascending = "score_batch_mixing", False
elif SCORE_METHOD == "bio_only":
    sort_col, ascending = "score_bio_preservation", False

top_n = df_ok.nlargest(N_TOP, sort_col) if not ascending else df_ok.nsmallest(N_TOP, sort_col)
print(top_n[["strat","imp","method","composite_score","score_batch_mixing",
             "score_bio_preservation","r2_RNA_BATCH",
             "r2_Diagnosis_cell_type_unified","r2_Major_group"]].to_string())
```

**Cell 4.6 — Ranking summary table**

Styled pandas DataFrame showing all methods ranked by composite score with key metrics highlighted using background gradients.

**Cell 4.7 — Radar chart for top-5 methods**

Polar plot with 6 axes:
- Batch mixing (A: r2_RNA_BATCH normalized inverted)
- Neighbor mixing (B: mean of kBET + iLISI)
- Distribution alignment (D: ks_mean_D inverted)
- Biology preservation (B+G: ASW_bio_Diagnosis_cell_type_unified + graph_connectivity)
- Data quality (E: n_genes normalized)
- Composite score

Each of top-5 methods drawn as a filled polygon. Legend shows method names.

**Cell 4.8 — Pareto frontier plot**

Scatter: x = `score_batch_mixing`, y = `score_bio_preservation`, colored by `method`. Highlight Pareto-optimal points (not dominated on both axes) with larger markers and labels.

---

### §5 — Visual Inspection of Top Approaches

For each of the top-N methods, download the expression matrix + annotation from S3 and compute PCA/UMAP/tSNE visualizations.

**Cell 5.1 — Download helper**

```python
import boto3, gzip, io

S3_BUCKET = "$FL_S3_BUCKET"
S3_PREFIX = "FL_batch_correction"

def load_top_method(strat, imp, method, post_rm=False):
    """Download expression + annotation for one harmonization attempt from S3."""
    s3 = boto3.client("s3")
    pm = "0" if not post_rm else "1"
    exp_key = f"{S3_PREFIX}/exp/{strat}__{imp}__{method}__post{pm}.tsv.gz"
    ann_key = f"{S3_PREFIX}/prepared/{strat}__{imp}__ann.tsv.gz"
    
    def _dl(key):
        body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
        return pd.read_csv(io.BytesIO(gzip.decompress(body)), sep="\t", index_col=0)
    
    return _dl(exp_key), _dl(ann_key)
```

**Cell 5.2 — PCA comparison grid for top methods**

For each top-N method and the raw baseline (`01_raw`): compute PCA (50 PCs), project to 2D.

Layout: N_TOP + 1 columns (including `01_raw` reference). Each column contains **two panels stacked horizontally in a row**:
- Left panel of the pair: PC1 vs PC2 colored by `RNA_BATCH`
- Right panel of the pair: PC1 vs PC2 colored by `Diagnosis_cell_type_unified`

These two views share the same PC coordinates and are placed side by side so the batch structure and the biological structure can be read at a glance. Title = method name + `r2_RNA_BATCH` value + `r2_Diagnosis_cell_type_unified` value.

```python
# Layout: 2 rows (batch coloring / biology coloring), N_TOP+1 columns
fig, axes = plt.subplots(2, N_TOP + 1, figsize=(4 * (N_TOP + 1), 8))
for i, (label, strat, imp, method) in enumerate([("01_raw", ..., ..., "01_raw")] + ...):
    exp, ann = load_top_method(strat, imp, method)
    pca_coords, _ = compute_pca(exp, n_components=50)
    axes[0, i].scatter(pca_coords[:, 0], pca_coords[:, 1],
                       c=ann["RNA_BATCH"].map(batch_pal), s=2, alpha=0.5)
    axes[0, i].set_title(f"{method}\nr2_batch={df_ok.loc[...,'r2_RNA_BATCH']:.2f}", fontsize=8)
    axes[1, i].scatter(pca_coords[:, 0], pca_coords[:, 1],
                       c=ann["Diagnosis_cell_type_unified"].map(celltype_pal), s=2, alpha=0.5)
```

**Cell 5.3 — UMAP comparison grid** (same two-panel structure as §5.2: RNA_BATCH coloring / Diagnosis_cell_type_unified coloring)

**Cell 5.4 — tSNE comparison grid** (same two-panel structure)

**Cell 5.5 — Per-batch and per-cohort expression distribution violin plots**

For each top-5 method, draw two sets of violin plots:
- Set 1: x = `RNA_BATCH`, y = expression (marginal distribution)
- Set 2: x = `COHORT_LABEL`, y = expression (cohort-level detail)

Plot all top-5 methods in a vertical stack of subplots within each set. Aligned axes. Shows whether distributions are properly aligned both at the platform level (Set 1) and within-platform cohort level (Set 2).

**Cell 5.6 — Gene correlation heatmap: FL/GC marker genes + housekeeping genes**

For each top-5 method:

**Panel A — FL/GC marker gene correlation:** Correlation heatmap of 30–40 known FL/GC marker genes (BCL2, MME, BCL6, LMO2, FN1, CCND2, MKI67, PCNA, AICDA, CXCR4, CXCR5 — full list in §11). Shows whether key gene–gene relationships are preserved.

**Panel B — Housekeeping gene expression stability:** Select 15–20 classical housekeeping genes (ACTB, TUBB, GAPDH, B2M, HMBS, HPRT1, PPIA, RPL13A, RPLP0, TBP, YWHAZ, UBC, VIM, LDHA, PGK1, SDHA). For each method, compute:
- Mean expression of each housekeeping gene per `RNA_BATCH` (boxplot per gene grouped by batch)
- CV of each housekeeping gene across batches
- CV of each housekeeping gene across `Major_group` groups

Ideal normalization preserves low CV across batches AND low CV across biology groups for housekeeping genes. Compare these stability metrics before and after normalization using a 2-column table (baseline `01_raw` vs. method).

**Cell 5.7 — Gene CV vs. expression level curves per batch and cohort**

For each top-5 method, plot the relationship between mean expression level and CV (coefficient of variation) for each `RNA_BATCH` and for each `COHORT_LABEL`. After successful normalization, all batches and cohorts should produce similar decaying CV-vs-expression curves (genes with high expression have lower CV — a universal feature of expression data). Divergence of these curves indicates residual batch effect.

```python
fig, axes = plt.subplots(len(top_5), 2, figsize=(14, 4 * len(top_5)))
for i, (strat, imp, method) in enumerate(top_5_ids):
    exp, ann = load_top_method(strat, imp, method)
    for ax, group_col in zip(axes[i], ["RNA_BATCH", "COHORT_LABEL"]):
        for group_name, idx in ann.groupby(group_col).groups.items():
            sub = exp.loc[exp.index.intersection(idx)]
            gene_means = sub.mean(axis=0)
            gene_cvs   = sub.std(axis=0) / (gene_means.replace(0, np.nan))
            # Bin by expression level and plot mean CV per bin
            bins = np.percentile(gene_means.dropna(), np.linspace(0, 100, 21))
            bin_centers, bin_cvs = [], []
            for b0, b1 in zip(bins[:-1], bins[1:]):
                mask = (gene_means >= b0) & (gene_means < b1)
                bin_cvs.append(gene_cvs[mask].median())
                bin_centers.append((b0 + b1) / 2)
            ax.plot(bin_centers, bin_cvs, alpha=0.6, linewidth=0.8, label=group_name)
        ax.set_xlabel("Mean expression (log2)"); ax.set_ylabel("Median gene CV")
        ax.set_title(f"{method} — {group_col}")
```

---

## Part 2: Gene Set Analysis

---

### §6 — Download Gene Lists from S3

**Cell 6.1 — List all gene JSON files on S3**

```python
s3 = boto3.client("s3")
paginator = s3.get_paginator("list_objects_v2")
gene_keys = []
for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=f"{S3_PREFIX}/genes/"):
    for obj in page.get("Contents", []):
        if obj["Key"].endswith("_genes.json"):
            gene_keys.append(obj["Key"])
print(f"Found {len(gene_keys)} gene list files on S3.")
```

**Cell 6.2 — Download and parse gene lists**

```python
gene_sets = {}   # key: (strat, imp, method, post_rm) → set of gene symbols

for key in gene_keys:
    fname = key.split("/")[-1]
    stem = fname.replace("_genes.json", "")
    parts = stem.split("__")
    if len(parts) != 4: continue
    strat, imp, method, pm_tag = parts
    post_rm = (pm_tag == "post1")
    
    body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read().decode()
    genes = set(json.loads(body))
    gene_sets[(strat, imp, method, post_rm)] = genes

print(f"Loaded {len(gene_sets)} gene sets.")
```

**Cell 6.3 — Build a summary DataFrame**

```python
gene_summary = []
for (strat, imp, method, post_rm), genes in gene_sets.items():
    gene_summary.append({
        "strat": strat, "imp": imp, "method": method,
        "post_rm": post_rm, "n_genes": len(genes),
        "genes": genes,
    })
gene_df = pd.DataFrame(gene_summary)
print(gene_df.groupby(["strat","imp","post_rm"])["n_genes"].describe())
```

---

### §7 — Gene Count and Overlap Analysis

**Cell 7.1 — Gene count by (strat, imp) pre-normalization**

Gene count is set during data preparation (not normalization), so it should be nearly identical across methods within the same (strat, imp) pair — except for `25_angel` which internally filters genes. Bar chart: x = (strat, imp) ordered by harshness, y = `n_genes`, hue = method. Highlight outlier methods including `25_angel`.

**Cell 7.2 — Pairwise Jaccard overlap between gene sets**

```python
strat_imp_pairs = gene_df.groupby(["strat","imp"])["genes"].apply(lambda gs: set.union(*gs)).reset_index()
n = len(strat_imp_pairs)
jaccard_mat = np.zeros((n, n))
for i, row_i in strat_imp_pairs.iterrows():
    for j, row_j in strat_imp_pairs.iterrows():
        inter = len(row_i.genes & row_j.genes)
        union = len(row_i.genes | row_j.genes)
        jaccard_mat[i, j] = inter / union if union > 0 else 0
```

Heatmap of Jaccard matrix annotated with values. Shows gene set compatibility between harmonization strategies.

**Cell 7.3 — Unique and lost genes — supervenn plots**

Use `supervenn` for all set intersection visualizations in this section (not UpSet or matplotlib_venn).

Produce two supervenn figures:
1. **Same imputation, different removal strategies:** Fix `imp = "strict"`, compare gene sets across all available strats (A_confirmed_bad, B_extended_bad, and any others present). Shows how progressively stricter batch removal shrinks the gene universe.
2. **Same removal strategy, different imputation approaches:** Fix `strat = "A_confirmed_bad"`, compare gene sets for strict / knn / softimpute. Shows how imputation recovers genes lost by strict filtering.

```python
from supervenn import supervenn

# Example 1: fixed imp, varying strat
strict_strat_sets = {
    strat: gene_sets_by_strat_imp[(strat, "strict")]
    for strat in available_strats
    if (strat, "strict") in gene_sets_by_strat_imp
}
fig, ax = plt.subplots(figsize=(12, 5))
supervenn([strict_strat_sets[s] for s in sorted(strict_strat_sets)],
          sorted(strict_strat_sets.keys()), ax=ax)
ax.set_title("Gene sets: fixed imp=strict, varying strat")
fig.savefig(FIGURES_DIR / "supervenn_strats_strict_imp.svg", bbox_inches="tight")

# Example 2: fixed strat, varying imp
A_imp_sets = {imp: gene_sets_by_strat_imp[("A_confirmed_bad", imp)]
              for imp in ["strict","knn","softimpute"]
              if ("A_confirmed_bad", imp) in gene_sets_by_strat_imp}
fig, ax = plt.subplots(figsize=(10, 5))
supervenn([A_imp_sets[i] for i in sorted(A_imp_sets)],
          sorted(A_imp_sets.keys()), ax=ax)
ax.set_title("Gene sets: fixed strat=A_confirmed_bad, varying imputation")
fig.savefig(FIGURES_DIR / "supervenn_imps_A_strat.svg", bbox_inches="tight")
```

Also report core / strategy-specific / imputation-recovered gene counts:
```python
all_genes  = set.union(*[gs["genes"] for _, gs in gene_df.iterrows()])
core_genes = set.intersection(*[gs["genes"] for _, gs in gene_df.iterrows()])
print(f"All unique genes ever: {len(all_genes)}")
print(f"Core genes (always present): {len(core_genes)}")
```

---

### §8 — Progressive Accumulation / Depletion Curves

The key analysis: as batch removal becomes more aggressive (less data), how many genes are retained? As imputation is applied, how many genes are recovered?

**Cell 8.1 — Define harshness ordering**

```python
HARSHNESS_ORDER = [
    ("A_confirmed_bad", "strict"),
    ("A_confirmed_bad", "knn"),
    ("A_confirmed_bad", "softimpute"),
    ("B_extended_bad",  "strict"),
    ("B_extended_bad",  "knn"),
    # Add C, D, E1-E3 strats when available
]
HARSHNESS_LABEL = {k: i for i, k in enumerate(HARSHNESS_ORDER)}
```

**Cell 8.2 — Gene accumulation curve**

For each (strat, imp) along the harshness axis, count the number of genes. Exclude `25_angel` from the per-method averaging since it modifies the gene space. Compute separately for `post_rm=False` (post0) and `post_rm=True` (post1), and show both in the same figure (dashed line for post1, solid for post0).

```python
for post_rm_flag in [False, True]:
    baseline_genes = gene_sets_by_strat_imp_postrm[HARSHNESS_ORDER[0]][post_rm_flag]
    running_seen = set()
    curve_data = []
    for strat_imp in HARSHNESS_ORDER:
        current_genes = gene_sets_by_strat_imp_postrm[strat_imp][post_rm_flag]
        new_genes  = current_genes - running_seen
        lost_genes = baseline_genes - current_genes
        running_seen |= new_genes
        curve_data.append({...})
```

Two-panel figure: panel 1 = gene retention line (post0 solid, post1 dashed); panel 2 = genes lost vs baseline stacked bar.

**Cell 8.3 — Imputation recovery analysis (supervenn)**

For `strat = A_confirmed_bad`, compare strict / knn / softimpute gene sets using `supervenn` (not matplotlib_venn):

```python
from supervenn import supervenn

sets_by_imp = [
    gene_sets_by_strat_imp[("A_confirmed_bad", "strict")],
    gene_sets_by_strat_imp[("A_confirmed_bad", "knn")],
    gene_sets_by_strat_imp[("A_confirmed_bad", "softimpute")],
]
fig, ax = plt.subplots(figsize=(10, 5))
supervenn(sets_by_imp, ["strict", "knn", "softimpute"], ax=ax)
ax.set_title("Gene recovery by imputation method (A_confirmed_bad strategy)")
fig.savefig(FIGURES_DIR / "supervenn_imputation_recovery.svg", bbox_inches="tight")
```

Also print gene counts:
```python
recovered_knn  = knn_genes - strict_genes
recovered_soft = soft_genes - strict_genes
print(f"KNN recovered: {len(recovered_knn)} genes")
print(f"SoftImpute recovered: {len(recovered_soft)} genes")
print(f"Both methods agree: {len(recovered_knn & recovered_soft)} genes")
```

---

### §9 — GO Enrichment Analysis — Setup

**Cell 9.1 — Download GO database files**

First check if the files are already available from the T2T transposons project at `../../Retroelements/T2T_genes_article/T2T_transposons_genes/`. If present, symlink or copy rather than re-downloading.

```python
import urllib.request, os, shutil
from pathlib import Path

T2T_DIR = Path("../../Retroelements/T2T_genes_article/T2T_transposons_genes/")
GO_OBO_PATH = Path("go-basic.obo")
GO_GAF_PATH = Path("goa_human.gaf")

for fname, url in [
    ("go-basic.obo", "http://purl.obolibrary.org/obo/go/go-basic.obo"),
    ("goa_human.gaf", "http://geneontology.org/gene-associations/goa_human.gaf.gz"),
]:
    dst = Path(fname.replace(".gz",""))
    if dst.exists():
        print(f"{dst} already present.")
        continue
    t2t_candidate = T2T_DIR / fname
    if t2t_candidate.exists():
        shutil.copy(t2t_candidate, dst)
        print(f"Copied {dst} from T2T project.")
    else:
        print(f"Downloading {url}...")
        tmp = dst.with_suffix(".gz") if fname.endswith(".gz") else dst
        urllib.request.urlretrieve(url, tmp)
        if fname.endswith(".gz"):
            with gzip.open(tmp, "rb") as fi, open(dst, "wb") as fo:
                shutil.copyfileobj(fi, fo)
            tmp.unlink()
        print(f"Done: {dst}")
```

**Cell 9.2 — Load GO DAG and associations once**

```python
from goatools.obo_parser import GODag
from goatools.anno.gaf_reader import GafReader
from goatools.go_enrichment import GOEnrichmentStudy

godag = GODag(str(GO_OBO_PATH))

ogaf = GafReader(str(GO_GAF_PATH))
full_assoc = {}
for ntf in ogaf.associations:
    symbol = ntf.DB_Symbol
    if symbol not in full_assoc:
        full_assoc[symbol] = set()
    full_assoc[symbol].add(ntf.GO_ID)

# Fixed background: all genes with GO annotations (not a subset of the study)
GO_BACKGROUND = sorted(full_assoc.keys())
print(f"Loaded {len(full_assoc)} gene symbols with GO annotations.")
print(f"Background size (all GO-annotated genes): {len(GO_BACKGROUND)}")
```

**Cell 9.3 — `run_goatools_enrichment` function**

The background is fixed as all GO-annotated human genes (`GO_BACKGROUND`, defined above), not a subset of the harmonization dataset. Using a dataset-specific background would cause a bias: as we add more genes (less harsh filtering), more genes enter the background, making GO terms increasingly harder to detect — opposite to the expected biological interpretation. Fixing the background to all annotated genes ensures that the analysis correctly reflects "given these genes are present, what processes are enriched in the GO universe."

```python
def run_goatools_enrichment(
    gene_list,
    fdr_threshold=0.05,
    namespace="biological_process",   # "molecular_function" | "cellular_component" | None
):
    """
    Run GO enrichment for gene_list against the full GO-annotated human gene universe.
    Background is fixed to GO_BACKGROUND (all genes in full_assoc) — not dataset-specific.
    Returns a DataFrame of significant terms or empty DataFrame.
    Uses pre-loaded godag and full_assoc from outer scope.
    """
    goeaobj = GOEnrichmentStudy(
        GO_BACKGROUND,
        full_assoc,
        godag,
        propagate_counts=True,
        alpha=fdr_threshold,
        methods=["fdr_bh"],
    )
    results_all = goeaobj.run_study(gene_list)
    results_sig = [
        r for r in results_all
        if r.p_fdr_bh < fdr_threshold and (namespace is None or r.NS == namespace)
    ]
    rows = []
    for r in results_sig:
        fe = (r.study_count / r.study_n) / (r.pop_count / r.pop_n) if r.pop_count > 0 else float("nan")
        rows.append({
            "GO_ID": r.GO, "term_name": r.name, "namespace": r.NS,
            "p_value": r.p_uncorrected, "FDR": r.p_fdr_bh,
            "fold_enrichment": fe,
            "n_study": r.study_count, "n_background": r.pop_count,
            "study_genes": sorted(r.study_items),
        })
    return pd.DataFrame(rows).sort_values("FDR") if rows else pd.DataFrame()
```

---

### §10 — Progressive GO Term Accumulation Curves

The central question: as we include more genes (less aggressive batch removal + more imputation), how many new biological processes become visible?

**Cell 10.1 — Build harshness-ordered gene sets**

Already defined in §8.1. Use the same `HARSHNESS_ORDER`. For each step, the gene set is the union of that (strat, imp) gene sets across **all** normalization methods, including `25_angel` — it is interesting to observe whether ANGEL's aggressive gene selection removes biologically relevant genes or retains them efficiently.

**Cell 10.2 — Compute GO enrichment at each step**

The background is fixed to `GO_BACKGROUND` (all GO-annotated human genes), independent of the harmonization step. This ensures that enrichment significance correctly increases as more relevant genes enter the study list — consistent with the expected behavior of adding more genes from a less aggressive filtering strategy.

```python
go_results_by_step = {}
cumulative_terms = set()
accumulation_curve = []

for strat_imp in HARSHNESS_ORDER:
    gene_set = gene_sets_by_strat_imp[strat_imp]
    study_genes = sorted(gene_set & set(full_assoc.keys()))
    
    go_df = run_goatools_enrichment(study_genes, namespace="biological_process")
    go_results_by_step[strat_imp] = go_df
    
    new_terms = set(go_df["GO_ID"]) - cumulative_terms if not go_df.empty else set()
    cumulative_terms |= new_terms
    
    accumulation_curve.append({
        "strat_imp": str(strat_imp),
        "n_genes": len(study_genes),
        "n_go_terms": len(go_df) if not go_df.empty else 0,
        "n_new_terms": len(new_terms),
        "n_cumulative_terms": len(cumulative_terms),
    })

acc_df = pd.DataFrame(accumulation_curve)
```

**Cell 10.3 — Plot GO term accumulation curve**

```python
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

ax1.plot(acc_df.n_genes, acc_df.n_go_terms, "o-", color="steelblue", label="Enriched terms at step")
ax1.plot(acc_df.n_genes, acc_df.n_cumulative_terms, "s--", color="darkorange", label="Cumulative unique terms")
ax1.set_xlabel("Number of genes in dataset")
ax1.set_ylabel("Number of GO:BP terms enriched")
ax1_twin = ax1.twinx()
ax1_twin.set_ylabel("Harshness step")
ax1.legend()

ax2.bar(range(len(acc_df)), acc_df.n_new_terms)
ax2.set_xticks(range(len(acc_df)))
ax2.set_xticklabels(acc_df.strat_imp, rotation=45, ha="right")
ax2.set_ylabel("New unique GO:BP terms vs previous step")

fig.savefig(FIGURES_DIR / "go_accumulation_curve.svg", bbox_inches="tight")
```

**Cell 10.4 — Analyze terms lost with progressive batch removal — all strategy pairs**

For each pair of strategies along the harshness axis (not just the two extremes), identify GO terms that are present in the more permissive strategy and lost in the more aggressive one. This provides a complete picture of the biological cost of each filtering step.

```python
# All pairwise comparisons along harshness axis
for idx_permissive, idx_strict in [(i, j) for i in range(len(HARSHNESS_ORDER))
                                           for j in range(i+1, len(HARSHNESS_ORDER))]:
    key_p = HARSHNESS_ORDER[idx_permissive]
    key_s = HARSHNESS_ORDER[idx_strict]
    
    if go_results_by_step[key_p].empty or go_results_by_step[key_s].empty:
        continue
    
    permissive_terms = set(go_results_by_step[key_p]["GO_ID"])
    strict_terms     = set(go_results_by_step[key_s]["GO_ID"])
    lost_terms       = permissive_terms - strict_terms
    
    if len(lost_terms) == 0:
        continue
    
    lost_df = (
        go_results_by_step[key_p]
        .set_index("GO_ID")
        .loc[[t for t in lost_terms if t in go_results_by_step[key_p].set_index("GO_ID").index]]
        .sort_values("fold_enrichment", ascending=False)
        .head(30)
    )
    # Horizontal bar chart of top-30 lost GO terms (x=fold_enrichment, color=FDR)
    ...
```

Focus the dissertation plot on the most informative pair (most permissive vs. most aggressive) and show top-30 lost terms as a horizontal bar chart.

**Cell 10.5 — Imputation-specific term recovery**

For the same strategy (A_confirmed_bad), compare which GO terms are unique to knn vs softimpute imputation vs strict (no imputation). Use supervenn for the 3-way comparison of term sets.

---

### §11 — FL-Specific Gene Retention Analysis

**Cell 11.1 — Compile the FL-relevant gene list**

Assemble a curated gene list from four sources:

**Source 1: FL transcriptomic subtype markers (C1/C2/C3, from doi:10.1038/s41375-025-02603-9)**

```python
FL_2025_MARKERS = {
    "C1_DZ_proliferative": [
        "MKI67", "TOP2A", "PCNA", "MCM2", "MCM6", "CCND2", "CDK4", "AICDA",
        "MYBL1", "CENPF", "UBE2C", "RRM2", "TYMS", "GINS2",
    ],
    "C2_LZ_anergy": [
        "BCL2", "CXCR4", "CD83", "FCER2", "CD79A", "IGHM", "IGHD",
        "IRF4", "PRDM1", "BLIMP1", "FAS", "CD95",
    ],
    "C3_inflammatory": [
        "CXCL9", "CXCL10", "CXCL11", "STAT1", "IFI27", "IFI44",
        "IFIT1", "IFIT3", "ISG15", "MX1", "OAS1", "IFI16",
    ],
}
```

**Source 2: legacy internal GC B-cell markers (Centroblast / Centrocyte)**

```python
LEGACY_GC_MARKERS = {
    "Centroblast_DZ": [
        "AICDA", "MKI67", "BCL6", "CXCR4", "EZH2", "RGS13", "FOXO1",
        "LMO2", "CCNB1", "BIRC5",
    ],
    "Centrocyte_LZ": [
        "CD83", "MME", "FCER2", "CD10", "BCL2", "CD40", "SELL",
        "DUSP5", "DUSP6", "NR4A1",
    ],
}
```

**Source 3: FL prognostic / clinical genes from published signatures**

```python
FL_PROG_SIGNATURES = {
    "FL_PFS_signature_2019": [
        "LMO2", "FN1", "CCND2", "BCL6", "SCYA3", "HGAL",
        "LRMP", "MKI67", "BCL2", "CDKN2A",
        # complete list from pubmed 29475724
    ],
    "POD24_markers": [
        "EZH2", "BCL2", "CCND3", "TNFRSF14", "KMT2D",
        "FOXO1", "CREBBP", "EP300",
    ],
}
```

**Source 4: PROGENy pathway-activating genes**

```python
FL_PATHWAY_GENES = {
    "BCR_signaling": ["CD79A","CD79B","PTPN6","PIK3CD","CARD11","BCL10","MALT1"],
    "NF_kB": ["NFKB1","NFKB2","REL","RELA","RELB","IKBKB","IKBKG"],
    "PI3K_AKT": ["PIK3CA","PIK3CB","PIK3CD","AKT1","AKT2","AKT3","PTEN","MTOR"],
    "GCB_markers": ["BCL6","MYC","BCL2","CD10","MME","CXCR4","CXCR5"],
}
```

**Final combined FL gene set:**

```python
FL_GENES_ALL = sorted(set(
    sum(FL_2025_MARKERS.values(), []) +
    sum(LEGACY_GC_MARKERS.values(), []) +
    sum(FL_PROG_SIGNATURES.values(), []) +
    sum(FL_PATHWAY_GENES.values(), [])
))
print(f"Total FL-relevant genes: {len(FL_GENES_ALL)}")

fl_gene_meta = []
for cat, genes in {**FL_2025_MARKERS, **LEGACY_GC_MARKERS, **FL_PROG_SIGNATURES, **FL_PATHWAY_GENES}.items():
    for g in genes:
        fl_gene_meta.append({"gene": g, "category": cat})
fl_gene_df = pd.DataFrame(fl_gene_meta).drop_duplicates("gene")
```

Pre-run cross-check: validate all symbols in `FL_GENES_ALL` against the HGNC symbols used in the expression matrices (e.g., `MME` vs `CD10`, `FAS` vs `CD95`). Resolve aliases using `mygene` or a manual lookup table before proceeding to §11.2.

**Cell 11.2 — FL gene presence matrix**

```python
fl_presence = pd.DataFrame(
    {(s,i,m): [g in gene_sets[(s,i,m,False)] for g in FL_GENES_ALL]
     for (s,i,m,pr) in gene_sets if not pr},
    index=FL_GENES_ALL,
)
print(f"FL genes always present: {fl_presence.all(axis=1).sum()}")
print(f"FL genes sometimes absent: {(~fl_presence.all(axis=1)).sum()}")
```

**Cell 11.3 — FL gene retention heatmap**

Binary heatmap: rows = FL genes (grouped by category), columns = harmonization attempts (ordered by composite score). Color: present (dark green) / absent (light red). Side color bar = gene category. Bottom color bar = composite_score of that harmonization attempt.

This answers: "Which normalization methods lose FL-relevant genes, and which ones preserve them?"

**Cell 11.4 — FL gene progressive retention curves**

Two figures:

**Figure A — Per-category retention curves:** One subplot per FL gene category (C1_DZ_proliferative, C2_LZ_anergy, C3_inflammatory, Centroblast_DZ, Centrocyte_LZ, FL_PFS_signature_2019, POD24_markers, BCR_signaling, NF_kB, PI3K_AKT, GCB_markers). For each category, plot the fraction of genes retained along the harshness axis (HARSHNESS_ORDER on x, fraction 0–1 on y). Add horizontal reference line at 0.90 (90% retention threshold).

**Figure B — Overall FL gene retention curve:** Single plot showing the fraction of all `FL_GENES_ALL` genes retained at each harshness step. Also show curves for each category superimposed (as thinner lines) with the overall curve in bold. Add vertical lines at the steps where imputation is introduced (strict → knn → softimpute transition). This single plot is the most informative summary for the dissertation.

```python
fig, axes = plt.subplots(1, len(all_fl_categories) + 1, figsize=(20, 4), sharey=True)

# Per-category curves
for ax, cat in zip(axes[:-1], all_fl_categories):
    cat_genes = [g for g in fl_gene_df[fl_gene_df.category == cat]["gene"] if g in all_genes]
    fractions = [len(set(cat_genes) & gene_sets_by_strat_imp[si]) / max(len(cat_genes), 1)
                 for si in HARSHNESS_ORDER]
    ax.plot(range(len(HARSHNESS_ORDER)), fractions, "o-")
    ax.set_title(cat, fontsize=8)
    ax.axhline(0.9, color="gray", linestyle="--", linewidth=0.7)

# Overall FL gene retention curve (last panel)
ax_all = axes[-1]
fl_all_fractions = [len(set(FL_GENES_ALL) & gene_sets_by_strat_imp[si]) / len(FL_GENES_ALL)
                    for si in HARSHNESS_ORDER]
ax_all.plot(range(len(HARSHNESS_ORDER)), fl_all_fractions, "o-", linewidth=2, color="black", label="All FL genes")
for cat in all_fl_categories:
    cat_genes = [g for g in fl_gene_df[fl_gene_df.category == cat]["gene"] if g in all_genes]
    fracs = [len(set(cat_genes) & gene_sets_by_strat_imp[si]) / max(len(cat_genes), 1)
             for si in HARSHNESS_ORDER]
    ax_all.plot(range(len(HARSHNESS_ORDER)), fracs, alpha=0.4, linewidth=0.8)
ax_all.set_title("All FL genes combined", fontsize=8)
ax_all.axhline(0.9, color="gray", linestyle="--", linewidth=0.7)
ax_all.legend(fontsize=7)

for ax in axes:
    ax.set_xticks(range(len(HARSHNESS_ORDER)))
    ax.set_xticklabels([str(x) for x in HARSHNESS_ORDER], rotation=45, ha="right", fontsize=7)
    ax.set_ylim(0, 1.05)

fig.savefig(FIGURES_DIR / "fl_gene_retention_curves.svg", bbox_inches="tight")
```

**Cell 11.5 — GO enrichment in FL-specific gene subset**

```python
fl_genes_in_go = [g for g in FL_GENES_ALL if g in full_assoc]

# Context enrichment: all FL genes
go_fl_all = run_goatools_enrichment(fl_genes_in_go, namespace="biological_process")

# At-risk FL genes: absent in the most aggressive strategy
fl_at_risk = [g for g in fl_genes_in_go
              if g not in gene_sets_by_strat_imp[("B_extended_bad","strict")]]
go_fl_at_risk = run_goatools_enrichment(fl_at_risk, namespace="biological_process")
```

Display enriched GO terms as horizontal dot plots (x = fold enrichment, size = n_study, color = FDR).

**Cell 11.6 — Progressive accumulation curve for FL genes in GO space**

X-axis: harshness step. Y-axis: cumulative unique FL genes and cumulative unique GO terms enriched in FL genes. Show separately for each FL category and overall. Add vertical lines at imputation introduction steps.

This directly answers: "How many FL-relevant biological processes do we preserve, and at what cost in batch correction, as we tune the data preparation strategy?"

**Cell 11.7 — Final recommendation table**

A summary table combining:
- `composite_score` (Part 1)
- `n_genes` and `fraction_fl_genes_retained` (Part 2)
- `r2_RNA_BATCH` and `r2_Diagnosis_cell_type_unified` (direct key metrics)
- Boolean flag: all FL gene categories ≥ 90% retained

Sorted by composite_score descending. Styled with background gradients. Export as CSV for dissertation appendix:

```python
rec_table.to_csv("recommendation_table.csv", index=True)
```

---

## Implementation Notes

### File and directory layout

```
harmonization-metrics/
├── metrics_notebook_plan.md                  ← this file
├── metrics_comprehensive_260501.csv          ← input metrics CSV
├── harmonization_metrics_analysis.ipynb      ← the notebook to be created
├── go-basic.obo                              ← downloaded once (or symlinked from T2T project)
├── goa_human.gaf                             ← downloaded once (or symlinked from T2T project)
└── figures/                                  ← all exported figures
    ├── clustermap_all_metrics_clustered.svg
    ├── clustermap_all_metrics_grouped_cols.svg
    ├── heatmap_ordered_no_clustering.svg
    ├── composite_score_rankings.svg
    ├── pca_grid_top10.svg
    ├── umap_grid_top10.svg
    ├── go_accumulation_curve.svg
    ├── fl_gene_retention_heatmap.svg
    └── fl_gene_retention_curves.svg
```

**Figure export standard:** All figures saved as SVG (vector, for dissertation) and PNG (raster, for quick preview). Font size 10 pt throughout (set in §1.1). Use `fig.savefig(FIGURES_DIR / "name.svg", bbox_inches="tight")` and `fig.savefig(FIGURES_DIR / "name.png", bbox_inches="tight", dpi=200)` for every key figure.

### Key libraries required

```
# Already available in collagen_3_11 venv:
boto3, pandas, numpy, matplotlib, seaborn, sklearn, scipy, umap-learn, statsmodels, supervenn

# Needed additionally:
goatools     # GO enrichment analysis — pip install goatools
```

Check: `from supervenn import supervenn` — supervenn is used in B-cell typing notebooks and should already be present. If not: `pip install supervenn`.

### GO analysis performance notes

- `GODag` and `GafReader` should be loaded **once** at the top of Part 2 (Cell 9.2), then reused in all enrichment calls via the module-level `godag`, `full_assoc`, and `GO_BACKGROUND` variables
- For the accumulation curve (§10.2), there are at most ~6 `run_study()` calls — each takes ~10–30 seconds → total ~3 minutes
- Use `propagate_counts=True` for proper hierarchical GO propagation

### Metric polarity edge cases

For Group H distance metrics (`dist_ratio_*`):
- **Batch columns** (RNA_BATCH, PLATFORM_RNA, RNASEQ_SOURCE, COHORT_LABEL): lower dist_ratio = better (within-batch not tighter than between-batch)
- **Biology columns** (Major_group, TUMOR_NORMAL, Diagnosis_cell_type_unified): lower dist_ratio = better biology (within-biology tighter)

Both directions use polarity −1 for different reasons. Keep them in separate score components (batch_mixing vs. bio_preservation) to avoid confusion.

### Currently missing strats

Only `A_confirmed_bad` and `B_extended_bad` × `knn` are in the current CSV. The accumulation curves in §8 and §10 will have limited resolution (4–5 harshness points). When more strats are computed (S0, C, D, E1–E3), add them to `HARSHNESS_ORDER` in §8.1 and re-run §8–§11.

### FL gene symbol aliases

Before §11, validate `FL_GENES_ALL` against actual HGNC symbols in the expression matrices. Known aliases to resolve:
- `MME` = `CD10` (neprilysin)
- `FAS` = `CD95` = `TNFRSF6`
- `FCER2` = `CD23`
- `CD79A`, `CD79B` — check HGNC vs probe mapping
