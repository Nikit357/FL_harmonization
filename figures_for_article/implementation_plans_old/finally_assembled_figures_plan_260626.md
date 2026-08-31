# Implementation Plan: `Finally_assembled_figures_for_article.ipynb`
**Date:** 2026-06-26  
**Author:** Daniil Nikitin  
**Scope:** New Jupyter notebook completing all remaining article figures for Article 1 of the ComboBatch manuscript.

---

## Overview

Figures 1 (all panels A–D), 2 (all panels, including 2A/2B/2C/2D), 3 (harmonization clustermap), and visual inspection figures 4–5 are already implemented in existing notebooks. This plan defines a single new notebook `Finally_assembled_figures_for_article.ipynb` in `figures_for_article/` that implements all remaining metric comparison and summary figures.

**Figures to implement:**
- **Fig 7** — Local neighborhood metrics (kBET, iLISI/cLISI, graph connectivity, UMAP/tSNE entropy, correlation with PCA-based metrics)
- **Fig 8** — Structural and distance metrics (centroid dispersion, WaterMelon, CMS, ASW, Euclidean distance ratio)
- **Fig 8B** — Distributional similarity metrics (KS tests, per-gene CV, bimodal fraction, NA retention)
- **Fig 9** — Cross-metric correlation and factor importance (pairplots, harshness analysis, diverse formats)
- **Fig 10** — Comprehensive composite ranking with star/radar visualization
- **Fig 11** — Hierarchical decision tree (defined in notebook cell, with icons and palette coloring)
- **Supp Fig 9** — PCA/UMAP/tSNE visualizations with best-approach star highlights
- **Supp A–G** — NA genes per batch, imputation Sankey, gene retention, group B/C/G/H detail catplots

**Style requirement:** All figures must match the style of existing figures in `figures_for_article/current_figures_for_article_260625` — publication quality (Nature-level), no overlapping subpanels, fixed `GLOBAL_FONT_SIZE=10`, clean axes with `sns.set_style("ticks")` and `sns.despine()`.

**Plotting principle for main figures:** Use raw seaborn calls (`sns.scatterplot`, `sns.barplot`, `sns.catplot`, `sns.stripplot`, etc.) directly in figure cells, then customize with `ax.set_xlabel()`, `ax.set_title()`, `ax.tick_params()`, etc. Do not define seaborn wrapper functions in `figures_helpers.py`. Each main figure should use a diverse mix of plot types — barplots, boxplots, histograms, stacked bar plots, scatterplots, heatmaps, clustermaps, pie charts. Supplementary figures may use standard uniform formats.

The accompanying helper module `figures_helpers.py` contains only **data preparation utilities**: loading, filtering, normalization, best-vs-rest construction, and S3 I/O functions. No plotting functions.

The plan is organized into **4 implementation blocks** at the end for step-by-step execution.

---

## Background / Reference Data

### Data sources

| Data object | Local path or S3 key | Shape | Used for |
|---|---|---|---|
| `df_ok` | `harmonization-metrics/metric_tables/metrics_comprehensive_260609.csv` (filtered to `status=="ok"` using the same logic as `../harmonization-metrics/harmonization_metrics_analysis_v3.ipynb`) | 2,234 × ~230 | All metric figures |
| `df_normed` | Derived from `df_ok` × POLARITY | 2,234 × 87 | Correlation, ranking |
| `scoring_cols` | 87 polarity-defined columns | list[87] | Column selection |
| `col_meta` | Derived per-column group+polarity table | DataFrame | Group-level plots |
| `_top_ids` | 15 (method, imp, strat) tuples — hardcoded in notebook | list[15] | Best-vs-all |
| `df_best` | `df_ok[is_best]` — 15 rows | 15 × ~230 | Best-vs-all |
| `data_v3` | `pd.concat([df_ok, df_best_tagged])` — 2,249 rows | 2,249 × ~230 | All §3-style plots |
| `comb_exp_raw` | S3: `FL_batch_correction/exp/S0_no_removal__strict__01_raw__post0.tsv.gz` | 7,174 × ~50k | NA gene figures |
| `comb_ann` | S3: `FL_batch_correction/prepared/S0_no_removal__knn__ann.tsv.gz` | 7,174 × 485 | Batch metadata |
| Gene lists | S3: `FL_batch_correction/genes/{strat}__{imp}__{method}__post0_genes.json` | JSON | Gene retention |
| FL gene sets | `../harmonization-metrics/` (goatools, `dlbcl_signatures.gmt`) | — | GO + FL gene accumulation |

### Decision tree design (from slide 104 of `FL_project_update_slides_260604_manually_edited.pptx`)

Exact node structure (4 levels):

```
Level 0 — Root: "YOUR DATASET"
Level 1 — Biomaterial / platform composition:
  ├── FF only (solid tissue, fresh-frozen)
  ├── FFPE only (formalin-fixed paraffin-embedded)
  ├── RNA-seq only (any biomaterial, Illumina NGS)
  ├── RNA-seq + Illumina microarrays
  └── RNA-seq + various microarrays (Affymetrix + Illumina mix)
Level 2 — Method recommendation:
  FF only       → MNN  (primary)  | FSQN R (alternative)
  FFPE only     → SVA + softimpute/KNN  ★ (first-ever platform mixing)
  RNA-seq only  → SVA + softimpute/KNN  (two FL subgroups visible)
  RNA-seq + Illumina → FSQN R (primary) | AMDBNorm / FSMVN + post-removal
  RNA-seq + various  → MNN + post-removal (visual inspection required)
Level 3 — Post-removal QC:
  FF only → No post-removal
  FFPE only → No post-removal
  RNA-seq + arrays → Post-removal recommended
```

Decision tree visual requirements:
- Small icons at each Level 1 node: ice-block icon for FF (fresh-frozen), FFPE block icon for FFPE, sequencing flow-cell icon for RNA-seq, chip-grid icon for microarrays
- Small icons at each Level 2 node representing the recommended harmonization algorithm (e.g., arrow-merge icon for MNN, regression diagram for SVA, quantile-normalisation icon for FSQN R)
- Node background color from `strat_pal` where a strategy is referenced; method boxes colored from `method_pal`
- Leaf node border colors: green (#2DC653) = primary recommendation, orange (#F4A261) = good alternative, gray (#AAAAAA) = requires visual inspection

From slide 107 note: "Redraw the decision tree — make it hierarchical instead of circular, with levels: вид биоматериала (FF, FFPE, и то и другое), Тип платформы (РНКсек, чипы, и то)."

### Key biological conclusions driving figure selection

- Only MNN, FSQN R, SVA resolve FL / DLBCL / Normal GC B cell differences
- SVA + C_rnaseq_only reveals two FL subgroups (biology, not batch)
- FFPE only + SVA: first benchmark attempt to mix FFPE and FF platforms
- Global metrics (PCR, R²) necessary but not sufficient (SVA achieves top local mixing without best global correction)
- Strategy is the most important factor; method second; imputation and post-removal less so
- Only the clustermap allows selection of the best approaches that are confirmed by visual inspection; no single metric or metric group alone achieves this — highlight this in the figures

### Existing figures that can be referenced / adapted (not reimplemented from scratch)

In `harmonization-metrics/figures/` (613 files total):
- Group B: `b_batch_biology_tradeoff.*`, `b_kbet_ilisi_scatter.*`, `b_lisi_catplot_by_strat.*`, `b_bio_clisi_mean_*`, `b_bio_asw_bio_norm_*`, `b_cms_*`
- Group C: `c_centroid_disp_grid.*`, `c_umap_tsne_entropy_corr.*`
- Group H: `h_dist_ratio_grid.*`
- Group K: `k_na_cells_heatmap.*`, `k_pct_genes_nona_by_method.*`, `k_pct_genes_nona_by_harshness.*`

**Notable gap:** No Group G (graph connectivity) or Group I (WaterMelon) figure files exist yet in `harmonization-metrics/figures/` — these must be generated fresh from `df_ok` columns in the new notebook.

### Metric type classification

```python
METRIC_TYPE_MAP = {
    "local_neighborhood": [
        "kbet_",
        "ilisi_",
        "clisi_",
        "graph_connectivity_",
        "umap_entropy_",
        "tsne_entropy_",
    ],
    "global_distance": [
        "r2_",
        "pcr_",
        "dsc_",
        "umap_centroid_disp_",
        "tsne_centroid_disp_",
        "dist_ratio_",
        "avg_intra_dist_",
        "avg_inter_dist_",
        "asw_batch_",
        "asw_bio_",
        "cms_",
        "pct_var_pc",
        "pct_var_cum",
        "wm_",
    ],
    "distribution_similarity": [
        "ks_mean_D_",
        "ks_frac_sig_",
        "ks_cohort_within_batch_",
        "per_gene_batch_mean_cv_",
    ],
    "other": ["pct_genes_", "pct_samples_", "pct_na_cells"],
}
```

### Available metric column prefixes per group (from `GROUP_MAP` in v3 notebook)

| Group | Key columns in `df_ok` | Polarity |
|---|---|---|
| A | `r2_RNA_BATCH`, `pcr_RNA_BATCH`, `dsc_RNA_BATCH`, `pct_var_pc1` | −1 (lower = better for r2/pcr/dsc) |
| B | `kbet_acceptance_rate_RNA_BATCH`, `ilisi_mean_RNA_BATCH`, `clisi_mean_Diagnosis_*`, `asw_batch_norm_*`, `asw_bio_norm_*`, `cms_fraction_mixed_*` | mixed |
| C | `umap_centroid_disp_*`, `tsne_centroid_disp_*`, `umap_entropy_*` | mixed |
| G | `graph_connectivity_*` | +1 (higher = better) |
| H | `dist_ratio_intra_inter_*` | −1 (lower = better) |
| I | `wm_RNA_BATCH`, `wm_Diagnosis_*`, `wm_ratio_bio_batch` | mixed |
| J | `pct_var_pc1`, `pct_var_cum_top10` | −1 |
| K | `n_genes_noNA`, `pct_genes_noNA`, `n_na_cells`, `pct_na_cells` | mixed |

---

## Files to Create

### 1. `figures_for_article/figures_helpers.py` (new local helper module — data prep only)

All reusable **data preparation** functions go here. Notebook imports from this file. Plotting functions are NOT defined here — they are implemented directly in each figure cell using raw seaborn/matplotlib calls.

**Function signatures and descriptions:**

```python
# ── I/O helpers ──────────────────────────────────────────────────────────────

def save_figure(fig: plt.Figure, name: str, figures_dir: Path = Path("figures")) -> None:
    """Save figure as both SVG and PNG (dpi=200) to figures_dir."""

def load_metrics_data(
    csv_path: str = "../harmonization-metrics/metric_tables/metrics_comprehensive_260609.csv",
) -> tuple[pd.DataFrame, pd.DataFrame, list[str], pd.DataFrame]:
    """Load metrics CSV → (df_ok, df_normed, scoring_cols, col_meta).

    Applies the same filtering logic as harmonization_metrics_analysis_v3.ipynb:
    status == 'ok', drop rows with all-NaN scoring columns, polarity normalization.

    Returns
    -------
    df_ok        2,234 × ~230  filtered to status=="ok"
    df_normed    2,234 × 87   polarity-normalized [0,1]; 1=best
    scoring_cols list of 87 metric column names
    col_meta     DataFrame with columns: metric, group, polarity
    """

def build_best_vs_rest(
    df_ok: pd.DataFrame,
    top_ids: list[tuple],
    best_label: str = "Best",
    best_color: str = "#E63946",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build df_best (15 rows), df_best_tagged (method="Best"), data_v3 (2249 rows).

    Returns (df_best, df_best_tagged, data_v3).
    """

# ── Gene retention helpers ────────────────────────────────────────────────────

def compute_nona_genes_per_batch(
    comb_exp_raw: pd.DataFrame,
    comb_ann: pd.DataFrame,
    batch_to_platform_group: dict,
) -> pd.DataFrame:
    """Compute count of non-NA genes per RNA_BATCH from raw expression matrix.

    Returns DataFrame with columns: RNA_BATCH, n_nona_genes, platform_group.
    """

def load_gene_lists_from_s3(
    s3_client,
    bucket: str,
    strategies: list[str],
    imputations: list[str] = ["strict", "knn", "softimpute"],
    method: str = "01_raw",
    post_rm: int = 0,
) -> dict[tuple, set]:
    """Download genes JSON sidecars from S3 for given (strat, imp) pairs.

    Returns dict keyed by (strat, imp) → set of gene symbols.
    """
```

---

### 2. `figures_for_article/Finally_assembled_figures_for_article.ipynb` (new notebook)

#### Cell structure (exact 5-cell setup)

**Cell 0 — Imports + global constants**

```python
from pathlib import Path
import json
import boto3
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.cm as cm
import seaborn as sns
from scipy import stats

plt.rcParams["pdf.fonttype"] = "truetype"
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["figure.dpi"] = 200
sns.set_style("ticks")

GLOBAL_FONT_SIZE = 10
FIGURES_DIR = Path("figures")
FIGURES_DIR.mkdir(exist_ok=True)
(FIGURES_DIR / "supplementary").mkdir(exist_ok=True)

BEST_LABEL = "Best"
BEST_COLOR = "#E63946"
BEST_HATCH = "///"

S3_BUCKET = "$FL_S3_BUCKET"
METRICS_CSV_PATH = (
    Path("..") / "harmonization-metrics" / "metric_tables" / "metrics_comprehensive_260609.csv"
)

METRIC_TYPE_MAP = {
    "local_neighborhood": [
        "kbet_", "ilisi_", "clisi_",
        "graph_connectivity_", "umap_entropy_", "tsne_entropy_",
    ],
    "global_distance": [
        "r2_", "pcr_", "dsc_",
        "umap_centroid_disp_", "tsne_centroid_disp_",
        "dist_ratio_", "avg_intra_dist_", "avg_inter_dist_",
        "asw_batch_", "asw_bio_", "cms_",
        "pct_var_pc", "pct_var_cum", "wm_",
    ],
    "distribution_similarity": [
        "ks_mean_D_", "ks_frac_sig_",
        "ks_cohort_within_batch_", "per_gene_batch_mean_cv_",
    ],
    "other": ["pct_genes_", "pct_samples_", "pct_na_cells"],
}
```

**Cell 1 — Metrics data loading + best-vs-rest construction**

```python
from figures_helpers import load_metrics_data, build_best_vs_rest

df_ok, df_normed, scoring_cols, col_meta = load_metrics_data(METRICS_CSV_PATH)

# 15 manually curated best approaches (method, imp, strat) — validated June 2026
_top_ids = [
    ("10_mnn",       "strict",      "S0_no_removal"),
    ("10_mnn",       "knn",         "S0_no_removal"),
    ("10_mnn",       "strict",      "J_ff_only"),
    ("16_fsqn_r",    "strict",      "J_ff_only"),
    ("04_sva",       "knn",         "C_rnaseq_only"),
    ("04_sva",       "softimpute",  "C_rnaseq_only"),
    ("04_sva",       "knn",         "K_ffpe_only"),
    ("04_sva",       "softimpute",  "K_ffpe_only"),
    ("16_fsqn_r",    "strict",      "C_rnaseq_only"),
    ("16_fsqn_r",    "strict",      "H_rnaseq_illumina"),
    ("10_mnn",       "strict",      "L_rnaseq_all_arrays"),
    ("10_mnn",       "knn",         "L_rnaseq_all_arrays"),
    ("27_amdbnorm",  "knn",         "H_rnaseq_illumina"),
    ("29_fsmvn",     "softimpute",  "H_rnaseq_illumina"),
    ("10_mnn",       "softimpute",  "A_confirmed_bad"),
]

df_best, df_best_tagged, data_v3 = build_best_vs_rest(df_ok, _top_ids, BEST_LABEL, BEST_COLOR)

assert len(df_best) == 15, f"Expected 15 best, got {len(df_best)}"
print(f"df_ok: {df_ok.shape} | df_best: {df_best.shape} | data_v3: {data_v3.shape}")
print(f"scoring_cols: {len(scoring_cols)} | col_meta groups: {col_meta['group'].unique()}")
```

**Cell 2 — Canonical palettes + harshness tier + METRIC_TYPE_MAP column helpers**

```python
# Method palette — key methods explicit; remaining from tab20
method_pal = {
    "10_mnn": "#D62828", "04_sva": "#F77F00", "16_fsqn_r": "#FCBF49",
    "27_amdbnorm": "#A8DADC", "29_fsmvn": "#457B9D",
    BEST_LABEL: BEST_COLOR,
}
_all_methods = list(df_ok["method"].unique())
_tab20 = cm.get_cmap("tab20")
for i, m in enumerate([m for m in _all_methods if m not in method_pal]):
    method_pal[m] = matplotlib.colors.to_hex(_tab20(i / 20))

# Strategy palette — 14 strategies
strat_pal = dict(zip(
    sorted(df_ok["strat"].unique()),
    [matplotlib.colors.to_hex(plt.cm.tab20(i / 20)) for i in range(14)],
))

# Imputation palette
imp_pal = {"strict": "#264653", "knn": "#2A9D8F", "softimpute": "#E9C46A"}

# Harshness palette
harshness_pal = {"low": "#2DC653", "medium": "#F4A261", "high": "#E63946"}

# Add harshness tier to df_ok and data_v3
HARSHNESS_MAP = {
    "S0_no_removal": "low", "A_confirmed_bad": "low", "B_extended_bad": "low",
    "C_rnaseq_only": "medium", "D_malignant_only": "medium",
    "F_microarray_only": "medium", "G_affymetrix_only": "medium",
    "H_rnaseq_illumina": "medium", "I_rare_batches_removed": "low",
    "J_ff_only": "high", "K_ffpe_only": "high", "L_rnaseq_all_arrays": "medium",
}
df_ok["harshness"] = df_ok["strat"].map(HARSHNESS_MAP).fillna("medium")
data_v3["harshness"] = data_v3["strat"].map(HARSHNESS_MAP).fillna("medium")

# Metric-type column lookup helpers (derived from METRIC_TYPE_MAP)
def get_metric_cols(metric_type: str, available_cols: list[str]) -> list[str]:
    """Return columns from available_cols matching any prefix in METRIC_TYPE_MAP[metric_type]."""
    prefixes = METRIC_TYPE_MAP.get(metric_type, [])
    return [c for c in available_cols if any(c.startswith(p) for p in prefixes)]
```

**Cell 3 — Import helper functions**

```python
import importlib
import sys
sys.path.insert(0, str(Path(".").resolve()))

import figures_helpers as fh
importlib.reload(fh)

save_figure = fh.save_figure
```

**Cell 4 — S3 data load (gene retention and NA analysis)**

```python
# Only run this cell when producing Supp A/B/C (gene retention figures).
# Requires ~3 GB RAM for the raw expression matrix.
s3 = boto3.client("s3")

print("Loading raw expression matrix from S3 ...")
_obj = s3.get_object(Bucket=S3_BUCKET,
    Key="FL_batch_correction/exp/S0_no_removal__strict__01_raw__post0.tsv.gz")
comb_exp_raw = pd.read_csv(_obj["Body"], sep="\t", compression="gzip", index_col=0)
print(f"comb_exp_raw: {comb_exp_raw.shape}")

_obj = s3.get_object(Bucket=S3_BUCKET,
    Key="FL_batch_correction/prepared/S0_no_removal__knn__ann.tsv.gz")
comb_ann = pd.read_csv(_obj["Body"], sep="\t", compression="gzip", index_col=0)

batch_to_platform_group = {
    # same dict from Introductory notebook cell 8 — copy here verbatim
    # keys: RNA_BATCH strings; values: one of 4 Platform_group strings
}
comb_ann["Platform_group"] = comb_ann["RNA_BATCH"].map(batch_to_platform_group)
print(f"comb_ann: {comb_ann.shape}")
```

---

#### Figure cells (one `## Figure X` cell per figure)

Each main figure uses A4 GridSpec layout (`figsize=(8.27, 11.69)` inches). All plotting uses raw seaborn or matplotlib calls, not wrapper functions.

---

**Fig 7 — Local Neighborhood Metrics**
_Planned as MAIN figure_

Panels: kBET acceptance rate (strip), iLISI × cLISI trade-off scatter, graph connectivity by biology group (bar), UMAP entropy by method (box), tSNE entropy by method (box), local vs. global metric correlation scatter (PCR vs. kBET).

```python
## Figure 7 — Local Neighborhood Metrics

fig = plt.figure(figsize=(8.27, 11.69))
gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)
ax_A = fig.add_subplot(gs[0, 0])   # Panel A — kBET acceptance rate by method (strip)
ax_B = fig.add_subplot(gs[0, 1])   # Panel B — iLISI vs cLISI scatter (trade-off)
ax_C = fig.add_subplot(gs[1, 0])   # Panel C — Graph connectivity by biology group (bar)
ax_D = fig.add_subplot(gs[1, 1])   # Panel D — UMAP entropy by method (boxplot)
ax_E = fig.add_subplot(gs[2, 0])   # Panel E — tSNE entropy by method (boxplot)
ax_F = fig.add_subplot(gs[2, 1])   # Panel F — Local (kBET) vs global (PCR) scatter

# Panel A: kBET acceptance rate strip plot by method, sorted by mean, Best highlighted
_kbet_col = "kbet_acceptance_rate_RNA_BATCH"
_order_A = (data_v3.groupby("method")[_kbet_col].mean()
            .sort_values(ascending=False).index.tolist())
sns.stripplot(data=data_v3, y="method", x=_kbet_col, hue="method",
              order=_order_A, palette=method_pal, ax=ax_A, size=3, alpha=0.5, jitter=True)
ax_A.axvline(data_v3.loc[data_v3["method"] == BEST_LABEL, _kbet_col].mean(),
             color=BEST_COLOR, linestyle="--", linewidth=1.2, label="Best mean")
ax_A.set_xlabel("kBET acceptance rate", fontsize=GLOBAL_FONT_SIZE)
ax_A.set_ylabel("", fontsize=GLOBAL_FONT_SIZE)
ax_A.set_title("A: kBET acceptance rate by method", fontsize=GLOBAL_FONT_SIZE)
ax_A.tick_params(labelsize=GLOBAL_FONT_SIZE)
sns.despine(ax=ax_A)

# Panel B: iLISI (batch mixing) vs cLISI (biology preservation) — trade-off scatter
_ilisi_col = "ilisi_mean_RNA_BATCH"
_clisi_col = "clisi_mean_Diagnosis_cell_type_unified"
if _ilisi_col in data_v3.columns and _clisi_col in data_v3.columns:
    sns.scatterplot(data=data_v3, x=_ilisi_col, y=_clisi_col, hue="method",
                    palette=method_pal, ax=ax_B, s=20, alpha=0.5)
    # Mark Best points with larger star markers
    _best_b = data_v3[data_v3["method"] == BEST_LABEL]
    ax_B.scatter(_best_b[_ilisi_col], _best_b[_clisi_col],
                 marker="*", s=120, color=BEST_COLOR, zorder=5, label="Best ★")
    ax_B.set_xlabel("iLISI (batch, higher=better mixing)", fontsize=GLOBAL_FONT_SIZE)
    ax_B.set_ylabel("cLISI (biology, higher=better preservation)", fontsize=GLOBAL_FONT_SIZE)
    ax_B.set_title("B: Batch–biology local mixing trade-off", fontsize=GLOBAL_FONT_SIZE)
    ax_B.legend(fontsize=GLOBAL_FONT_SIZE - 2, ncol=2)
    sns.despine(ax=ax_B)

# Panel C: Graph connectivity by biology covariate — barplot
_gc_cols = [c for c in df_ok.columns if c.startswith("graph_connectivity_")]
if _gc_cols and df_ok[_gc_cols].notna().mean().mean() > 0.5:
    _gc_melted = df_ok.melt(id_vars=["method", "strat"],
                             value_vars=_gc_cols, var_name="covariate", value_name="gc")
    _gc_order = df_ok.groupby("method")[_gc_cols[0]].mean().sort_values(ascending=False).index
    sns.barplot(_gc_melted, x="method", y="gc", hue="covariate",
                order=_gc_order, ax=ax_C, palette="Set2")
    ax_C.set_xticklabels(ax_C.get_xticklabels(), rotation=45, ha="right",
                          fontsize=GLOBAL_FONT_SIZE - 1)
    ax_C.set_title("C: Graph connectivity by biology group", fontsize=GLOBAL_FONT_SIZE)
    ax_C.set_xlabel("", fontsize=GLOBAL_FONT_SIZE)
    ax_C.set_ylabel("Graph connectivity", fontsize=GLOBAL_FONT_SIZE)
    sns.despine(ax=ax_C)
else:
    ax_C.text(0.5, 0.5, "Group G: no data\n(graph_connectivity_* columns absent or sparse)",
              ha="center", va="center", transform=ax_C.transAxes, fontsize=GLOBAL_FONT_SIZE)

# Panel D: UMAP entropy by method — boxplot (Group C entropy)
_umap_ent_cols = [c for c in scoring_cols if c.startswith("umap_entropy_") or c.startswith("entropy_umap_")]
if _umap_ent_cols:
    _ent_data_d = df_ok[["method"] + _umap_ent_cols].melt(id_vars="method",
                  var_name="covariate", value_name="entropy")
    _order_D = df_ok.groupby("method")[_umap_ent_cols[0]].mean().sort_values(ascending=False).index
    sns.boxplot(data=_ent_data_d, x="method", y="entropy",
                order=_order_D, palette=method_pal, ax=ax_D,
                flierprops={"marker": ".", "markersize": 3})
    ax_D.set_xticklabels(ax_D.get_xticklabels(), rotation=45, ha="right",
                          fontsize=GLOBAL_FONT_SIZE - 1)
    ax_D.set_title("D: UMAP entropy by method", fontsize=GLOBAL_FONT_SIZE)
    ax_D.set_xlabel("", fontsize=GLOBAL_FONT_SIZE)
    ax_D.set_ylabel("UMAP mixing entropy", fontsize=GLOBAL_FONT_SIZE)
    sns.despine(ax=ax_D)

# Panel E: tSNE entropy by method — boxplot
_tsne_ent_cols = [c for c in scoring_cols if c.startswith("tsne_entropy_") or c.startswith("entropy_tsne_")]
if _tsne_ent_cols:
    _ent_data_e = df_ok[["method"] + _tsne_ent_cols].melt(id_vars="method",
                  var_name="covariate", value_name="entropy")
    _order_E = df_ok.groupby("method")[_tsne_ent_cols[0]].mean().sort_values(ascending=False).index
    sns.boxplot(data=_ent_data_e, x="method", y="entropy",
                order=_order_E, palette=method_pal, ax=ax_E,
                flierprops={"marker": ".", "markersize": 3})
    ax_E.set_xticklabels(ax_E.get_xticklabels(), rotation=45, ha="right",
                          fontsize=GLOBAL_FONT_SIZE - 1)
    ax_E.set_title("E: tSNE entropy by method", fontsize=GLOBAL_FONT_SIZE)
    ax_E.set_xlabel("", fontsize=GLOBAL_FONT_SIZE)
    ax_E.set_ylabel("tSNE mixing entropy", fontsize=GLOBAL_FONT_SIZE)
    sns.despine(ax=ax_E)

# Panel F: Local (kBET) vs global (PCR) scatter — all 2,234 attempts
# Key insight: SVA has high kBET but moderate PCR; MNN has both high
_pcr_col = "pcr_RNA_BATCH"
if _kbet_col in data_v3.columns and _pcr_col in data_v3.columns:
    sns.scatterplot(data=data_v3, x=_pcr_col, y=_kbet_col, hue="method",
                    palette=method_pal, ax=ax_F, s=18, alpha=0.5)
    _best_f = data_v3[data_v3["method"] == BEST_LABEL]
    ax_F.scatter(_best_f[_pcr_col], _best_f[_kbet_col],
                 marker="*", s=120, color=BEST_COLOR, zorder=5, label="Best ★")
    ax_F.set_xlabel("PCR (global, lower=better)", fontsize=GLOBAL_FONT_SIZE)
    ax_F.set_ylabel("kBET acceptance rate (local, higher=better)", fontsize=GLOBAL_FONT_SIZE)
    ax_F.set_title("F: Local–global metric correlation", fontsize=GLOBAL_FONT_SIZE)
    sns.despine(ax=ax_F)

for ax in [ax_A, ax_B, ax_C, ax_D, ax_E, ax_F]:
    ax.tick_params(labelsize=GLOBAL_FONT_SIZE)
fig.suptitle("Figure 7 — Local Neighborhood Metrics", fontsize=GLOBAL_FONT_SIZE + 1, y=1.01)
plt.tight_layout()
save_figure(fig, "fig7_local_metrics_neighborhood")
plt.close()
```

**Decision on main vs. supplementary:** If Panel B shows clear non-linear arc (MNN top-right, SVA balanced, others clustered bottom-left), keep as MAIN. If Panel C (graph connectivity) is sparse due to missing data, that panel may be replaced with a different Group B metric.

---

**Fig 8 — Structural and Distance Metrics**
_Planned as MAIN or SUPPLEMENTARY depending on visual inspection_

Panels: UMAP/tSNE centroid dispersion heatmap (wide), WaterMelon batch-vs-bio scatter, WaterMelon ratio ranked barplot, CMS (Cell Mixing Score) by method, ASW batch + ASW bio side-by-side, Euclidean distance intra/inter ratio.

```python
## Figure 8 — Structural and Distance Metrics

fig = plt.figure(figsize=(8.27, 11.69))
gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)
ax_A = fig.add_subplot(gs[0, :])   # Panel A — centroid dispersion heatmap (wide)
ax_B = fig.add_subplot(gs[1, 0])   # Panel B — WaterMelon scatter (batch vs bio)
ax_C = fig.add_subplot(gs[1, 1])   # Panel C — WaterMelon ratio ranked barplot
ax_D = fig.add_subplot(gs[2, 0])   # Panel D — CMS by method (stacked or grouped barplot)
ax_E = fig.add_subplot(gs[2, 1])   # Panel E — ASW batch + ASW bio comparison

# Panel A: centroid dispersion heatmap — rows=methods sorted by composite, cols=embedding×covariate
_disp_cols = [c for c in scoring_cols if "centroid_disp" in c]
_order_A = df_ok.groupby("method")[_disp_cols].mean().mean(axis=1).sort_values().index
_disp_pivot = df_ok.groupby("method")[_disp_cols].mean().loc[_order_A]
sns.heatmap(_disp_pivot.T, ax=ax_A, cmap="RdBu_r", center=0,
            cbar_kws={"shrink": 0.5, "label": "Mean centroid dispersion"},
            xticklabels=True, yticklabels=True)
ax_A.set_title("A: UMAP/tSNE centroid dispersion by method", fontsize=GLOBAL_FONT_SIZE)
ax_A.tick_params(labelsize=GLOBAL_FONT_SIZE - 1)

# Panel B: WaterMelon batch vs bio scatter — all attempts colored by method
_wm_batch = "wm_mean_batch" if "wm_mean_batch" in df_ok.columns else None
_wm_bio = "wm_mean_bio" if "wm_mean_bio" in df_ok.columns else None
if _wm_batch and _wm_bio and df_ok[[_wm_batch, _wm_bio]].notna().mean().mean() > 0.5:
    sns.scatterplot(data=df_ok, x=_wm_batch, y=_wm_bio, hue="method",
                    palette=method_pal, ax=ax_B, s=20, alpha=0.5)
    ax_B.scatter(df_best[_wm_batch], df_best[_wm_bio],
                 marker="*", s=120, color=BEST_COLOR, zorder=5, label="Best ★")
    _wm_max = max(df_ok[_wm_batch].max(), df_ok[_wm_bio].max())
    ax_B.plot([0, _wm_max], [0, _wm_max], "k--", linewidth=0.8, alpha=0.5)
    ax_B.set_xlabel("WaterMelon batch score", fontsize=GLOBAL_FONT_SIZE)
    ax_B.set_ylabel("WaterMelon bio score", fontsize=GLOBAL_FONT_SIZE)
    ax_B.set_title("B: WaterMelon batch vs. biology score", fontsize=GLOBAL_FONT_SIZE)
    sns.despine(ax=ax_B)
else:
    ax_B.text(0.5, 0.5, "WaterMelon (Group I): data absent or sparse",
              ha="center", va="center", transform=ax_B.transAxes, fontsize=GLOBAL_FONT_SIZE)

# Panel C: WaterMelon ratio bio/batch ranked by method — horizontal barplot
_wm_ratio = "wm_ratio_bio_batch"
if _wm_ratio in df_ok.columns and df_ok[_wm_ratio].notna().mean() > 0.5:
    _wm_mean = df_ok.groupby("method")[_wm_ratio].mean().sort_values(ascending=True)
    _colors_C = [BEST_COLOR if m == BEST_LABEL else method_pal.get(m, "gray")
                 for m in _wm_mean.index]
    ax_C.barh(_wm_mean.index, _wm_mean.values, color=_colors_C, height=0.7)
    ax_C.axvline(1.0, linestyle="--", color="black", linewidth=0.8)
    ax_C.set_xlabel("WM ratio (bio/batch)", fontsize=GLOBAL_FONT_SIZE)
    ax_C.set_title("C: WaterMelon bio/batch ratio by method", fontsize=GLOBAL_FONT_SIZE)
    ax_C.tick_params(labelsize=GLOBAL_FONT_SIZE)
    sns.despine(ax=ax_C)

# Panel D: CMS (Cell Mixing Score) by method — grouped barplot
_cms_cols = [c for c in scoring_cols if c.startswith("cms_")]
if _cms_cols:
    _cms_melted = df_ok.melt(id_vars=["method"], value_vars=_cms_cols,
                              var_name="covariate", value_name="cms")
    _order_D = df_ok.groupby("method")[_cms_cols[0]].mean().sort_values(ascending=False).index
    sns.barplot(data=_cms_melted, x="method", y="cms", hue="covariate",
                order=_order_D, ax=ax_D, palette="Paired")
    ax_D.set_xticklabels(ax_D.get_xticklabels(), rotation=45, ha="right",
                          fontsize=GLOBAL_FONT_SIZE - 1)
    ax_D.set_title("D: CMS (Cell Mixing Score) by method", fontsize=GLOBAL_FONT_SIZE)
    ax_D.set_xlabel("", fontsize=GLOBAL_FONT_SIZE)
    sns.despine(ax=ax_D)

# Panel E: ASW batch + ASW bio by method — side-by-side boxplots (grouped)
_asw_batch_cols = [c for c in scoring_cols if c.startswith("asw_batch_")]
_asw_bio_cols = [c for c in scoring_cols if c.startswith("asw_bio_")]
if _asw_batch_cols and _asw_bio_cols:
    _asw_batch_mean = df_ok.groupby("method")[_asw_batch_cols[0]].mean()
    _asw_bio_mean = df_ok.groupby("method")[_asw_bio_cols[0]].mean()
    _asw_df = pd.DataFrame({"asw_batch": _asw_batch_mean, "asw_bio": _asw_bio_mean}).reset_index()
    _asw_melted = _asw_df.melt(id_vars="method", var_name="metric", value_name="score")
    _order_E = _asw_batch_mean.sort_values().index
    sns.barplot(data=_asw_melted, x="method", y="score", hue="metric",
                order=_order_E, ax=ax_E,
                palette={"asw_batch": "#E76F51", "asw_bio": "#2A9D8F"})
    ax_E.set_xticklabels(ax_E.get_xticklabels(), rotation=45, ha="right",
                          fontsize=GLOBAL_FONT_SIZE - 1)
    ax_E.set_title("E: ASW batch vs. biology (silhouette width)", fontsize=GLOBAL_FONT_SIZE)
    ax_E.set_xlabel("", fontsize=GLOBAL_FONT_SIZE)
    sns.despine(ax=ax_E)

for ax in [ax_B, ax_C, ax_D, ax_E]:
    ax.tick_params(labelsize=GLOBAL_FONT_SIZE)
fig.suptitle("Figure 8 — Structural and Distance Metrics", fontsize=GLOBAL_FONT_SIZE + 1, y=1.01)
plt.tight_layout()
save_figure(fig, "fig8_structural_distance_metrics")
plt.close()
```

---

**Fig 8B — Distributional Similarity Metrics and NA Retention**
_Planned as MAIN or SUPPLEMENTARY depending on visual inspection_

Panels: KS test mean D by method, fraction significant KS per batch, per-gene batch mean CV, fraction bimodal cohorts, NA cells heatmap (strategy × method), % noNA genes by harshness × imputation.

```python
## Figure 8B — Distributional Similarity Metrics and NA Retention

fig = plt.figure(figsize=(8.27, 11.69))
gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)
ax_A = fig.add_subplot(gs[0, 0])   # Panel A — KS mean D by method (barplot)
ax_B = fig.add_subplot(gs[0, 1])   # Panel B — fraction significant KS (hist/bar)
ax_C = fig.add_subplot(gs[1, 0])   # Panel C — per-gene batch mean CV by method (box)
ax_D = fig.add_subplot(gs[1, 1])   # Panel D — bimodal cohort fraction by method
ax_E = fig.add_subplot(gs[2, 0])   # Panel E — NA cells heatmap (strategy × method)
ax_F = fig.add_subplot(gs[2, 1])   # Panel F — % noNA genes by harshness × imputation

# Panel A: KS mean D by method — horizontal barplot sorted
_ks_d_cols = [c for c in scoring_cols if c.startswith("ks_mean_D_")]
if _ks_d_cols:
    _ks_mean = df_ok.groupby("method")[_ks_d_cols[0]].mean().sort_values()
    _colors_A = [BEST_COLOR if m == BEST_LABEL else method_pal.get(m, "gray")
                 for m in _ks_mean.index]
    ax_A.barh(_ks_mean.index, _ks_mean.values, color=_colors_A, height=0.7)
    ax_A.set_xlabel("KS mean D (lower=better)", fontsize=GLOBAL_FONT_SIZE)
    ax_A.set_title("A: KS test mean D by method", fontsize=GLOBAL_FONT_SIZE)
    sns.despine(ax=ax_A)

# Panel B: Fraction significant KS tests — stacked bar by method
_ks_sig_cols = [c for c in scoring_cols if c.startswith("ks_frac_sig_")]
if _ks_sig_cols:
    _ks_sig_mean = df_ok.groupby("method")[_ks_sig_cols].mean()
    _ks_sig_mean.plot(kind="barh", ax=ax_B, stacked=True, colormap="Set2", legend=True)
    ax_B.set_xlabel("Fraction significant KS tests", fontsize=GLOBAL_FONT_SIZE)
    ax_B.set_title("B: Fraction significant KS tests by covariate", fontsize=GLOBAL_FONT_SIZE)
    ax_B.legend(fontsize=GLOBAL_FONT_SIZE - 2)
    sns.despine(ax=ax_B)

# Panel C: Per-gene batch mean CV by method — boxplot
_cv_cols = [c for c in scoring_cols if c.startswith("per_gene_batch_mean_cv_")]
if _cv_cols:
    _cv_melted = df_ok[["method"] + _cv_cols].melt(id_vars="method",
                 var_name="covariate", value_name="cv")
    _order_C = df_ok.groupby("method")[_cv_cols[0]].mean().sort_values().index
    sns.boxplot(data=_cv_melted, x="cv", y="method", order=_order_C,
                palette=method_pal, ax=ax_C,
                flierprops={"marker": ".", "markersize": 3})
    ax_C.set_xlabel("Per-gene batch mean CV", fontsize=GLOBAL_FONT_SIZE)
    ax_C.set_title("C: Per-gene batch CV by method", fontsize=GLOBAL_FONT_SIZE)
    sns.despine(ax=ax_C)

# Panel D: Bimodal fraction cohorts — use ks_cohort_within_batch_ as proxy
_bimodal_cols = [c for c in scoring_cols if c.startswith("ks_cohort_within_batch_")]
if _bimodal_cols:
    _bm_mean = df_ok.groupby("method")[_bimodal_cols[0]].mean().sort_values(ascending=False)
    _colors_D = [BEST_COLOR if m == BEST_LABEL else method_pal.get(m, "gray")
                 for m in _bm_mean.index]
    ax_D.bar(_bm_mean.index, _bm_mean.values, color=_colors_D)
    ax_D.set_xticklabels(ax_D.get_xticklabels(), rotation=45, ha="right",
                          fontsize=GLOBAL_FONT_SIZE - 1)
    ax_D.set_title("D: KS cohort-within-batch score by method", fontsize=GLOBAL_FONT_SIZE)
    sns.despine(ax=ax_D)

# Panel E: NA cells heatmap (strategy × method — pct_na_cells from Group K)
_na_pivot = df_ok.groupby(["strat", "method"])["pct_na_cells"].mean().unstack()
sns.heatmap(_na_pivot, ax=ax_E, cmap="YlOrRd", annot=False,
            xticklabels=True, yticklabels=True,
            cbar_kws={"label": "% NA cells"})
ax_E.set_title("E: NA cells (%) heatmap: strategy × method", fontsize=GLOBAL_FONT_SIZE)
ax_E.tick_params(labelsize=GLOBAL_FONT_SIZE - 1)

# Panel F: % noNA genes by imputation × harshness — grouped barplot
_nona_data = df_ok.groupby(["imp", "harshness"])["pct_genes_noNA"].mean().reset_index()
sns.barplot(data=_nona_data, x="harshness", y="pct_genes_noNA", hue="imp",
            order=["low", "medium", "high"], palette=imp_pal, ax=ax_F)
ax_F.set_xlabel("Strategy harshness", fontsize=GLOBAL_FONT_SIZE)
ax_F.set_ylabel("% non-NA genes", fontsize=GLOBAL_FONT_SIZE)
ax_F.set_title("F: Gene coverage by harshness and imputation", fontsize=GLOBAL_FONT_SIZE)
ax_F.legend(title="Imputation", fontsize=GLOBAL_FONT_SIZE - 1)
sns.despine(ax=ax_F)

for ax in [ax_A, ax_B, ax_C, ax_D, ax_E, ax_F]:
    ax.tick_params(labelsize=GLOBAL_FONT_SIZE)
fig.suptitle("Figure 8B — Distributional Similarity and NA Retention", fontsize=GLOBAL_FONT_SIZE + 1, y=1.01)
plt.tight_layout()
save_figure(fig, "fig8b_distributional_similarity_na_retention")
plt.close()
```

---

**Fig 9 — Cross-group Metric Correlation and Factor Importance**
_Planned as MAIN figure — shows core analytical insight_

The 87×87 Spearman correlation heatmap already exists in `harmonization-metrics/figures/` and has confirmed block structure (local ↔ local high, global ↔ global high, local ↔ global low correlation). This figure emphasizes the trade-off between local and global metrics, harshness analysis, and factor importance, using diverse plot formats.

Panels: Pairplot between representative metrics from different types (upper triangle colored by strategy, lower triangle colored by method); composite score distribution by harshness (violin + strip overlay); factor variance decomposition (η² barplot); metric group score summary (stacked barplot or pie chart by metric type).

```python
## Figure 9 — Cross-Group Metric Correlation and Factor Importance

fig = plt.figure(figsize=(8.27, 11.69))
gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.50, wspace=0.40)
ax_A = fig.add_subplot(gs[0, :])   # Panel A — local vs global vs distributional scatter matrix (wide)
ax_B = fig.add_subplot(gs[1, 0])   # Panel B — composite score by harshness tier (violin)
ax_C = fig.add_subplot(gs[1, 1])   # Panel C — factor importance η² barplot
ax_D = fig.add_subplot(gs[2, :])   # Panel D — metric type score summary by method (stacked bar, wide)

# Panel A: Representative metric cross-scatter — local vs global vs distributional
# Choose one representative metric per type; show pairwise scatter
_repr_local = next((c for c in df_ok.columns if c.startswith("kbet_acceptance_rate_")), None)
_repr_global = "pcr_RNA_BATCH" if "pcr_RNA_BATCH" in df_ok.columns else None
_repr_distr = next((c for c in df_ok.columns if c.startswith("ks_mean_D_")), None)
if _repr_local and _repr_global and _repr_distr:
    # Scatter: global (x) vs local (y), points colored by strategy (harshness)
    sns.scatterplot(data=df_ok, x=_repr_global, y=_repr_local, hue="harshness",
                    palette=harshness_pal, ax=ax_A, s=20, alpha=0.6,
                    style="method",
                    markers={m: "o" for m in df_ok["method"].unique()})
    # Overlay Best with stars
    ax_A.scatter(df_best[_repr_global], df_best[_repr_local],
                 marker="*", s=150, color=BEST_COLOR, zorder=6, label="Best ★")
    ax_A.set_xlabel(f"Global: {_repr_global} (lower=better)", fontsize=GLOBAL_FONT_SIZE)
    ax_A.set_ylabel(f"Local: {_repr_local} (higher=better)", fontsize=GLOBAL_FONT_SIZE)
    ax_A.set_title("A: Local vs. global batch correction metrics (colored by harshness)",
                   fontsize=GLOBAL_FONT_SIZE)
    ax_A.legend(title="Harshness", fontsize=GLOBAL_FONT_SIZE - 2)
    sns.despine(ax=ax_A)

# Panel B: Composite score by harshness tier — violin with strip overlay
df_ok["composite_score"] = df_normed[scoring_cols].mean(axis=1)
sns.violinplot(data=df_ok, x="harshness", y="composite_score", palette=harshness_pal,
               order=["low", "medium", "high"], ax=ax_B, inner=None, alpha=0.6)
sns.stripplot(data=df_ok, x="harshness", y="composite_score",
              order=["low", "medium", "high"], ax=ax_B,
              color="black", size=2, alpha=0.3, jitter=True)
# Overlay Best approaches
_best_h = df_ok.loc[df_best.index, ["harshness", "composite_score"]] if df_best.index.isin(df_ok.index).all() else None
ax_B.set_title("B: Composite score by strategy harshness", fontsize=GLOBAL_FONT_SIZE)
ax_B.set_xlabel("Harshness tier", fontsize=GLOBAL_FONT_SIZE)
ax_B.set_ylabel("Composite score (mean over 87 metrics)", fontsize=GLOBAL_FONT_SIZE)
sns.despine(ax=ax_B)

# Panel C: Factor variance decomposition — η² (effect size) per factor across 87 metrics
# ANOVA η² = SS_between / SS_total for each factor independently
from scipy import stats as scipy_stats
factors = ["strat", "method", "post_rm", "imp"]
eta2_results = {}
for factor in factors:
    eta2_vals = []
    for col in scoring_cols:
        _sub = df_ok[[factor, col]].dropna()
        if _sub[factor].nunique() < 2:
            continue
        groups = [grp[col].values for _, grp in _sub.groupby(factor)]
        f_val, p_val = scipy_stats.f_oneway(*groups)
        _grand_mean = _sub[col].mean()
        ss_total = (((_sub[col] - _grand_mean) ** 2).sum())
        ss_between = sum(len(g) * (g.mean() - _grand_mean) ** 2 for g in groups)
        eta2_vals.append(ss_between / ss_total if ss_total > 0 else 0)
    eta2_results[factor] = np.mean(eta2_vals)

_eta2_df = pd.Series(eta2_results).sort_values(ascending=True)
ax_C.barh(_eta2_df.index, _eta2_df.values,
          color=[harshness_pal.get(f, "#457B9D") for f in _eta2_df.index])
ax_C.set_xlabel("Mean η² (effect size across 87 metrics)", fontsize=GLOBAL_FONT_SIZE)
ax_C.set_title("C: Factor importance: strategy > method > post_rm > imp",
               fontsize=GLOBAL_FONT_SIZE)
sns.despine(ax=ax_C)

# Panel D: Metric type score by method — stacked barplot (wide)
# For each method, compute mean score in each metric type
_type_scores = {}
for mtype, prefixes in METRIC_TYPE_MAP.items():
    _type_cols = [c for c in scoring_cols if any(c.startswith(p) for p in prefixes)]
    if _type_cols:
        _type_scores[mtype] = df_normed[_type_cols].mean(axis=1)
_type_df = pd.DataFrame(_type_scores)
_type_df["method"] = df_ok["method"].values
_type_mean = _type_df.groupby("method").mean()
_order_D = _type_mean.sum(axis=1).sort_values(ascending=False).index
_type_mean.loc[_order_D].plot(kind="bar", stacked=True, ax=ax_D,
                               colormap="Set2", width=0.8)
ax_D.set_xticklabels(ax_D.get_xticklabels(), rotation=45, ha="right",
                      fontsize=GLOBAL_FONT_SIZE - 1)
ax_D.set_xlabel("Method", fontsize=GLOBAL_FONT_SIZE)
ax_D.set_ylabel("Mean normalized score", fontsize=GLOBAL_FONT_SIZE)
ax_D.set_title("D: Score by metric type and method (stacked)", fontsize=GLOBAL_FONT_SIZE)
ax_D.legend(title="Metric type", fontsize=GLOBAL_FONT_SIZE - 1, ncol=2)
sns.despine(ax=ax_D)

for ax in [ax_A, ax_B, ax_C, ax_D]:
    ax.tick_params(labelsize=GLOBAL_FONT_SIZE)
fig.suptitle("Figure 9 — Cross-Metric Correlation and Factor Importance",
             fontsize=GLOBAL_FONT_SIZE + 1, y=1.01)
plt.tight_layout()
save_figure(fig, "fig9_cross_metric_correlation_factor_importance")
plt.close()
```

---

**Fig 10 — Best Approaches vs. All: Comprehensive Ranking**
_Planned as MAIN figure — central result of the manuscript_

Panels: All 2,234 ranked by composite score (lollipop, wide); parallel coordinates for 15 Best across key metrics; composite score by harshness (violin with strip); method × metric group bubble chart (wide). Additionally, a standalone star/radar visualization is written as a separate Python script series (`fig10_metric_star_visualization.py`).

```python
## Figure 10 — Best Approaches Among All: Composite Ranking

# Compute both simple (equal-weight) and weighted composite scores
df_ok["composite_score_equal"] = df_normed[scoring_cols].mean(axis=1)

# Weighted: metric types weighted by count of scoring metrics per group
_type_weights = {}
for mtype, prefixes in METRIC_TYPE_MAP.items():
    _cols = [c for c in scoring_cols if any(c.startswith(p) for p in prefixes)]
    _type_weights[mtype] = 1.0 / max(len(_cols), 1)
_weighted_scores = pd.Series(0.0, index=df_normed.index)
for mtype, prefixes in METRIC_TYPE_MAP.items():
    _cols = [c for c in scoring_cols if any(c.startswith(p) for p in prefixes)]
    if _cols:
        _weighted_scores += df_normed[_cols].mean(axis=1) * _type_weights[mtype]
df_ok["composite_score_weighted"] = _weighted_scores / sum(_type_weights.values())

fig = plt.figure(figsize=(8.27, 11.69))
gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.50, wspace=0.40)
ax_A = fig.add_subplot(gs[0, :])   # Panel A — All 2,234 ranked by composite score (wide)
ax_B = fig.add_subplot(gs[1, 0])   # Panel B — Parallel coordinates (15 Best)
ax_C = fig.add_subplot(gs[1, 1])   # Panel C — Equal vs weighted composite score scatter
ax_D = fig.add_subplot(gs[2, :])   # Panel D — Method × metric group bubble chart (wide)

# Panel A: Composite score ranking — lollipop dot plot
_ranked = df_ok.sort_values("composite_score_equal").reset_index(drop=True)
_colors_A = [BEST_COLOR if df_best.index.isin([df_ok.index[i]]).any()
             else method_pal.get(m, "gray")
             for i, m in enumerate(_ranked["method"])]
ax_A.scatter(range(len(_ranked)), _ranked["composite_score_equal"],
             c=_colors_A, s=10, alpha=0.7)
ax_A.vlines(range(len(_ranked)), 0, _ranked["composite_score_equal"],
            colors=_colors_A, alpha=0.3, linewidth=0.5)
# Annotate Best positions with ★
_best_ranks = [i for i, idx in enumerate(_ranked.index)
               if idx in df_best.index]
ax_A.scatter(_best_ranks,
             _ranked.iloc[_best_ranks]["composite_score_equal"],
             marker="*", s=60, color=BEST_COLOR, zorder=5)
ax_A.set_xlabel("Rank (all 2,234 attempts)", fontsize=GLOBAL_FONT_SIZE)
ax_A.set_ylabel("Composite score (equal weight)", fontsize=GLOBAL_FONT_SIZE)
ax_A.set_title("A: All attempts ranked by composite harmonization score — ★ = Best 15",
               fontsize=GLOBAL_FONT_SIZE)
sns.despine(ax=ax_A)

# Panel B: Parallel coordinates — 15 Best approaches across 6 key representative metrics
# One metric per group type; normalized [0,1]
_key_metrics = [
    "pcr_RNA_BATCH",
    "kbet_acceptance_rate_RNA_BATCH",
]
_key_metrics += [c for c in scoring_cols if c.startswith("umap_centroid_disp_")][:1]
_key_metrics += [c for c in scoring_cols if c.startswith("wm_ratio_")][:1]
_key_metrics += ["pct_genes_noNA"] if "pct_genes_noNA" in df_ok.columns else []
_key_metrics += [c for c in scoring_cols if c.startswith("ks_mean_D_")][:1]
_key_metrics = [c for c in _key_metrics if c in df_normed.columns]

_best_normed = df_normed.loc[df_best.index, _key_metrics].copy()
_best_normed["method"] = df_best["method"].values
_best_normed["label"] = _best_normed["method"].map(
    lambda m: f"{m}\n{df_best.loc[df_best['method']==m, 'strat'].values[0] if (df_best['method']==m).any() else ''}"
)
_xs = range(len(_key_metrics))
for _, row in _best_normed.iterrows():
    _ys = [row[c] for c in _key_metrics]
    _col = method_pal.get(row["method"], "gray")
    ax_B.plot(_xs, _ys, color=_col, linewidth=1.5, alpha=0.8, marker="o", markersize=5)
ax_B.set_xticks(_xs)
ax_B.set_xticklabels([c.split("_")[0] for c in _key_metrics], rotation=30, ha="right",
                      fontsize=GLOBAL_FONT_SIZE - 1)
ax_B.set_ylim(0, 1)
ax_B.set_ylabel("Normalized score (0=worst, 1=best)", fontsize=GLOBAL_FONT_SIZE)
ax_B.set_title("B: 15 Best approaches across metric groups", fontsize=GLOBAL_FONT_SIZE)
sns.despine(ax=ax_B)

# Panel C: Equal-weight vs weighted composite score scatter — colored by method
sns.scatterplot(data=df_ok, x="composite_score_equal", y="composite_score_weighted",
                hue="method", palette=method_pal, ax=ax_C, s=20, alpha=0.5)
ax_C.scatter(df_best["composite_score_equal"] if "composite_score_equal" in df_best.columns
             else df_ok.loc[df_best.index, "composite_score_equal"],
             df_ok.loc[df_best.index, "composite_score_weighted"],
             marker="*", s=150, color=BEST_COLOR, zorder=5, label="Best ★")
ax_C.plot([0, 1], [0, 1], "k--", linewidth=0.8, alpha=0.5)
ax_C.set_xlabel("Equal-weight composite score", fontsize=GLOBAL_FONT_SIZE)
ax_C.set_ylabel("Weighted composite score", fontsize=GLOBAL_FONT_SIZE)
ax_C.set_title("C: Equal vs. weighted composite score", fontsize=GLOBAL_FONT_SIZE)
sns.despine(ax=ax_C)

# Panel D: Method × metric group bubble chart
_group_scores = {}
for group_letter, meta_rows in col_meta.groupby("group"):
    _cols_g = [c for c in meta_rows["metric"].tolist() if c in df_normed.columns]
    if _cols_g:
        _group_scores[group_letter] = df_normed[_cols_g].mean(axis=1)
_group_df = pd.DataFrame(_group_scores)
_group_df["method"] = df_ok["method"].values
_group_melt = _group_df.melt(id_vars="method", var_name="group", value_name="score")
_bubble_data = _group_melt.groupby(["method", "group"]).agg(
    mean_score=("score", "mean"), n=("score", "count")).reset_index()
_sc = ax_D.scatter(
    x=_bubble_data["method"], y=_bubble_data["group"],
    s=_bubble_data["n"] / 2,
    c=_bubble_data["mean_score"],
    cmap="RdYlGn", vmin=0, vmax=1, alpha=0.8
)
plt.colorbar(_sc, ax=ax_D, label="Mean normalized score")
ax_D.set_xticklabels(ax_D.get_xticklabels(), rotation=45, ha="right",
                      fontsize=GLOBAL_FONT_SIZE - 1)
ax_D.set_title("D: Method × metric group composite score (bubble size = n attempts)",
               fontsize=GLOBAL_FONT_SIZE)
sns.despine(ax=ax_D)

for ax in [ax_A, ax_B, ax_C, ax_D]:
    ax.tick_params(labelsize=GLOBAL_FONT_SIZE)
fig.suptitle("Figure 10 — Best Approaches: Composite Ranking", fontsize=GLOBAL_FONT_SIZE + 1, y=1.01)
plt.tight_layout()
save_figure(fig, "fig10_best_approaches_composite_ranking")
plt.close()
```

**Metric star/radar visualization** — a Python script `fig10_metric_star_visualization.py` handles the standalone star figure: number of rays = number of computational groups (A, B, C, …); ray length ∝ mean superiority of the 15 Best approaches in that group; ray color from a group palette; each ray contains a small matplotlib inset icon representing the mathematical nature of the metric (PCA screeplot icon for Group A, local-mixing scatter for Group B, centroid-oval UMAP for Group C, etc.). Written as a series of functions for easy customization. See TODO Block 3.

---

**Fig 11 — Decision Tree for Harmonization Method Selection**
_MAIN standalone figure — defined in notebook cell for easy editing_

The `draw_decision_tree()` function is defined directly in this cell (not in `figures_helpers.py`), so that Daniil can edit node labels, layout, and colors without touching the helper module.

```python
## Figure 11 — Hierarchical Decision Tree

def draw_decision_tree(font_size: int = GLOBAL_FONT_SIZE) -> plt.Figure:
    """Render 4-level hierarchical decision tree with method/strategy coloring and icons.

    Node boxes use FancyBboxPatch. Arrows drawn with ax.annotate.
    Colors: root=gray, L1 nodes from strat_pal, L2 method boxes from method_pal,
    leaf borders: green=primary, orange=alternative, gray=needs inspection.
    Icons: drawn inline as text emoji or simple matplotlib line art patches.
    """
    fig, ax = plt.subplots(figsize=(11.69, 8.27))  # A4 landscape
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")

    # ── Box drawing helper ─────────────────────────────────────────────────────
    def draw_box(ax, x, y, w, h, text, facecolor="#F5F5F5", edgecolor="#333333",
                 linewidth=1.5, fontsize=font_size, icon=""):
        from matplotlib.patches import FancyBboxPatch
        box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                             boxstyle="round,pad=0.05",
                             facecolor=facecolor, edgecolor=edgecolor,
                             linewidth=linewidth)
        ax.add_patch(box)
        ax.text(x, y + (h * 0.1 if icon else 0), text,
                ha="center", va="center", fontsize=fontsize, wrap=True,
                multialignment="center")
        if icon:
            ax.text(x, y - h * 0.25, icon, ha="center", va="center",
                    fontsize=fontsize + 4)

    def draw_arrow(ax, x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color="#555555", lw=1.2))

    # ── Level 0: Root ──────────────────────────────────────────────────────────
    draw_box(ax, 5, 6.3, 2.5, 0.7, "YOUR DATASET",
             facecolor="#CCCCCC", edgecolor="#333333", linewidth=2.5,
             fontsize=font_size + 1)

    # ── Level 1: Biomaterial / platform (5 branches) ──────────────────────────
    L1_nodes = [
        (1.0, "FF only\n(fresh-frozen)", "#A8DADC",
         strat_pal.get("J_ff_only", "#A8DADC"), "🧊"),
        (2.5, "FFPE only", "#FFDDD2",
         strat_pal.get("K_ffpe_only", "#FFDDD2"), "🟫"),
        (5.0, "RNA-seq only", "#D4F1F4",
         strat_pal.get("C_rnaseq_only", "#D4F1F4"), "🔬"),
        (7.5, "RNA-seq +\nIllumina arrays", "#E9C46A",
         strat_pal.get("H_rnaseq_illumina", "#E9C46A"), "🔬📊"),
        (9.0, "RNA-seq +\nvarious arrays", "#F4A261",
         strat_pal.get("L_rnaseq_all_arrays", "#F4A261"), "🔬📈"),
    ]
    for x_l1, label, fc, ec, icon in L1_nodes:
        draw_box(ax, x_l1, 4.8, 1.6, 0.9, label, facecolor=fc, edgecolor=ec,
                 linewidth=2, icon=icon)
        draw_arrow(ax, 5, 5.95, x_l1, 5.25)

    # ── Level 2: Method recommendations ───────────────────────────────────────
    L2_nodes = [
        # (x, y, text, primary_border, secondary_border)
        (0.6, 3.3, "MNN\n(primary)", method_pal.get("10_mnn", "#D62828"), "#2DC653"),
        (1.4, 3.3, "FSQN R\n(alternative)", method_pal.get("16_fsqn_r", "#FCBF49"), "#F4A261"),
        (2.5, 3.3, "SVA +\nsoftimpute/KNN\n★ first FFPE mix",
         method_pal.get("04_sva", "#F77F00"), "#2DC653"),
        (5.0, 3.3, "SVA +\nsoftimpute/KNN\n(2 FL subgroups)",
         method_pal.get("04_sva", "#F77F00"), "#2DC653"),
        (7.0, 3.3, "FSQN R\n(primary)", method_pal.get("16_fsqn_r", "#FCBF49"), "#2DC653"),
        (7.9, 3.3, "AMDBNorm /\nFSMVN + post-rm",
         method_pal.get("27_amdbnorm", "#A8DADC"), "#F4A261"),
        (9.0, 3.3, "MNN +\npost-removal",
         method_pal.get("10_mnn", "#D62828"), "#AAAAAA"),
    ]
    l1_x_to_l2 = [(1.0, [0.6, 1.4]), (2.5, [2.5]),
                  (5.0, [5.0]), (7.5, [7.0, 7.9]), (9.0, [9.0])]
    for l1_x, l2_xs in l1_x_to_l2:
        for l2_x in l2_xs:
            draw_arrow(ax, l1_x, 4.35, l2_x, 3.75)
    for x_l2, y_l2, text, _, border in L2_nodes:
        draw_box(ax, x_l2, y_l2, 1.4, 0.85, text,
                 facecolor="#FFFFFF", edgecolor=border, linewidth=2.5)

    # ── Level 3: Post-removal QC ───────────────────────────────────────────────
    L3_nodes = [
        (1.0, 1.8, "No post-removal", "#2DC653"),
        (2.5, 1.8, "No post-removal", "#2DC653"),
        (5.0, 1.8, "No post-removal", "#2DC653"),
        (7.5, 1.8, "Post-removal\nrecommended", "#F4A261"),
        (9.0, 1.8, "Post-removal\nrecommended", "#F4A261"),
    ]
    for x_l3, y_l3, text, color in L3_nodes:
        draw_box(ax, x_l3, y_l3, 1.5, 0.7, text,
                 facecolor=color + "33", edgecolor=color, linewidth=2)
    # Arrows L2→L3
    for (x_l2, _, _, _, _), (x_l3, _, _, _) in zip(L2_nodes[:5], L3_nodes):
        draw_arrow(ax, x_l2, 2.87, x_l3, 2.15)

    ax.set_title("Decision Tree: Harmonization Method Selection",
                 fontsize=font_size + 2, pad=10)
    return fig

fig = draw_decision_tree(font_size=GLOBAL_FONT_SIZE)
save_figure(fig, "fig11_decision_tree_harmonization_selection")
plt.close()
```

---

**Supp Fig 9 — PCA/UMAP/tSNE with Best Approach Stars**

A separate supplementary version of Fig 6 (or equivalent embeddings from the visual inspection notebook), where the best 15 approaches are highlighted with star markers in each embedding panel (PCA, UMAP, tSNE), analogous to the star highlights in existing Fig 6 panels C and D.

```python
## Supplementary Figure 9 — PCA/UMAP/tSNE Embeddings with Best Approach Highlights

# Reference: adapt from visual inspection notebook; load pre-computed embedding coordinates
# from S3 or from harmonization_metrics_visual_inspection notebook outputs.
# Each panel: one embedding type × one strategy; Best 15 annotated with ★
# Panel layout: one row per embedding type (PCA/UMAP/tSNE), columns by representative strategy

fig = plt.figure(figsize=(8.27, 11.69))
gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.45, wspace=0.35)
# ... (implement after embedding coordinates are confirmed available)
save_figure(fig, "supplementary/supp9_embeddings_best_stars")
plt.close()
```

---

**Supp Fig A — NA Genes per Batch (Fig 2C content)**

```python
## Supplementary Figure A — NA Genes per Batch

fig, ax = plt.subplots(figsize=(8.27, 5.83))   # A5 landscape
nona_per_batch = fh.compute_nona_genes_per_batch(comb_exp_raw, comb_ann, batch_to_platform_group)

# Sort by noNA gene percentage (like Figure 6), include Best attempts as separate group
nona_sorted = nona_per_batch.sort_values("n_nona_genes", ascending=True)

ax.barh(nona_sorted["RNA_BATCH"], nona_sorted["n_nona_genes"],
        color=[platform_palette.get(pg, "gray") for pg in nona_sorted["platform_group"]],
        height=0.7)
ax.set_xlabel("Non-NA genes per batch", fontsize=GLOBAL_FONT_SIZE)
ax.set_title("Gene coverage heterogeneity across RNA batches", fontsize=GLOBAL_FONT_SIZE)
ax.axvline(3520, linestyle="--", color="black", linewidth=0.8, label="Strict imputation (3,520)")
ax.axvline(11768, linestyle=":", color="blue", linewidth=0.8, label="KNN/softimpute (~11,768)")
ax.legend(fontsize=GLOBAL_FONT_SIZE)
ax.tick_params(labelsize=GLOBAL_FONT_SIZE)
sns.despine(ax=ax)
save_figure(fig, "supplementary/supp_a_nona_genes_per_batch")
plt.close()
```

---

**Supp Fig B — Imputation Gene Overlap Sankey (Fig 2D content)**

```python
## Supplementary Figure B — Imputation Gene Overlap Sankey

gene_sets = fh.load_gene_lists_from_s3(
    s3_client=s3, bucket=S3_BUCKET,
    strategies=["S0_no_removal", "A_confirmed_bad", "C_rnaseq_only"],
    imputations=["strict", "knn", "softimpute"],
    method="01_raw", post_rm=0,
)

# Custom Sankey via matplotlib patches — strict → knn / softimpute gene counts and overlaps
# Node heights proportional to gene count; flows colored by strategy
fig, ax = plt.subplots(figsize=(8.27, 5.83))
# ... (implement Sankey layout using matplotlib.patches.FancyArrow and rectangles)
save_figure(fig, "supplementary/supp_b_imputation_gene_overlap_sankey")
plt.close()
```

---

**Supp Fig C — Gene Retention and FL Gene Set Accumulation**

```python
## Supplementary Figure C — Gene Retention Analysis

fig = plt.figure(figsize=(8.27, 11.69))
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)
ax_A = fig.add_subplot(gs[0, :])
ax_B = fig.add_subplot(gs[1, 0])
ax_C = fig.add_subplot(gs[1, 1])

# Panel A: % noNA genes by method × imputation — annotated heatmap
_kna_pivot = df_ok.groupby(["method", "imp"])["pct_genes_noNA"].mean().unstack()
sns.heatmap(_kna_pivot, ax=ax_A, cmap="YlGn", annot=True, fmt=".0f",
            cbar_kws={"label": "% non-NA genes"})
ax_A.set_title("Gene coverage (% non-NA) by method and imputation", fontsize=GLOBAL_FONT_SIZE)
ax_A.tick_params(labelsize=GLOBAL_FONT_SIZE)

# Panel B: FL gene set accumulation curves by harshness
# ... (implement after gene list loading from S3)

# Panel C: GO enrichment barplot (unique KNN vs strict genes)
try:
    from goatools import obo_parser, go_enrichment
    # ... implement if goatools available
except ImportError:
    ax_C.text(0.5, 0.5, "goatools not installed\npip install goatools",
              ha="center", va="center", transform=ax_C.transAxes, fontsize=GLOBAL_FONT_SIZE)

save_figure(fig, "supplementary/supp_c_gene_retention_fl_gene_sets")
plt.close()
```

---

**Supp Figs D–G — Individual metric group catplots**

```python
## Supplementary Figure D — Group B Details (kBET, LISI, ASW, CMS individual catplots)
# Reproduce b_batch_biology_tradeoff, b_bio_clisi_mean_*, b_cms_grid at article font size

## Supplementary Figure E — Group C Detail (UMAP/tSNE centroid dispersion per strategy)
# Reproduce c_centroid_disp_grid at article font size

## Supplementary Figure F — Group H Detail (Euclidean distance ratio grid by method × covariate)
# Reproduce h_dist_ratio_grid at article font size

## Supplementary Figure G — Group G Detail (Graph connectivity per biology group)
# Generate fresh from df_ok graph_connectivity_* columns (guard for sparse data)
```

Each supplementary cell: standard grid of catplots using `sns.catplot`, `sns.FacetGrid`, or `sns.clustermap` with `GLOBAL_FONT_SIZE=10`, `plt.close()` after `save_figure()`.

---

## Files That Do NOT Need to Change

| File | Reason |
|---|---|
| `Introductory_figures_for_article.ipynb` | Figs 1A/1B/1D/2A–2D already implemented |
| `Harmonization_clustermap_figure.ipynb` | Fig 3 already implemented |
| `harmonization-metrics/harmonization_metrics_analysis_v3.ipynb` | Source of analysis logic; copy patterns to helpers.py but do not edit v3 |
| `harmonization-metrics/harmonization_metrics_visual_inspection.ipynb` | Exploration only; not article output |
| `pipeline_scheme_figure.py` | Standalone; only needs label update "39→31 methods" |
| `harmonization-metrics/compute_batch_metrics.py` | Metrics already computed; do not recompute |
| Any S3 files | Read-only from this notebook |

---

## Side Effects and Caveats

1. **Group G and I column availability** — Graph connectivity (`graph_connectivity_*`) and WaterMelon (`wm_*`) columns may be null for many rows. Check `df_ok[_gc_cols].notna().mean().mean() > 0.5` before plotting. If sparse, replace the panel with a Group B fallback metric.

2. **Gene list loading** — `load_gene_lists_from_s3()` downloads JSON sidecars from S3. For 3 strategies × 3 imputations = 9 files this is fast (<10 s). Cell 4 is optional and only required for Supp A/B/C.

3. **goatools dependency** — not in the default `collagen_3_11` venv. Use `gseapy.enrichr()` as fallback (already installed). The supp figure has a graceful fallback text.

4. **draw_decision_tree()** — defined in the Fig 11 cell, not in `figures_helpers.py`. Any future change to the decision logic requires editing that cell directly.

5. **Memory** — loading `comb_exp_raw` (7,174 × 50k) takes ~3 GB RAM. Only run Cell 4 when producing Supp A/B/C. All metric figures (Fig 7–11) work from `df_ok` only (< 200 MB).

6. **Notebook size** — notebooks must stay < 100 MB. Strip outputs before commit (`nbstripout` is configured). Add `plt.close()` after every `save_figure()` call.

7. **`_top_ids` list accuracy** — the 15 tuples in Cell 1 are the best current known values. The assertion `assert len(df_best) == 15` catches any mismatch.

8. **kbet_acceptance_rate column name** — the correct column name in `metrics_comprehensive_260609.csv` is `kbet_acceptance_rate_RNA_BATCH` (not `kbet_accept_rate_RNA_BATCH`). Verify with `df_ok.filter(like='kbet').columns` before running Fig 7.

9. **Star/radar visualization** — `fig10_metric_star_visualization.py` is a standalone script producing a publication-quality figure; it is listed separately in the files-to-create table and is NOT a seaborn plot — it uses only matplotlib patches, wedges, and inset axes.

---

## Verification Commands

```bash
source ~/venvs/collagen_3_11/bin/activate
cd ~/FL_harmonization/figures_for_article

# Verify figures_helpers.py imports without error
python -c "import figures_helpers as fh; print('OK')"

# Check correct kBET column name
python -c "
import pandas as pd
df = pd.read_csv('../harmonization-metrics/metric_tables/metrics_comprehensive_260609.csv')
print([c for c in df.columns if 'kbet' in c.lower()])
"

# Check metrics CSV columns (Group G and I availability)
python -c "
import pandas as pd
df = pd.read_csv('../harmonization-metrics/metric_tables/metrics_comprehensive_260609.csv')
g_cols = [c for c in df.columns if c.startswith('graph_connectivity_')]
i_cols = [c for c in df.columns if c.startswith('wm_')]
print(f'Group G cols: {len(g_cols)} — {g_cols[:3]}')
print(f'Group I cols: {len(i_cols)} — {i_cols[:3]}')
df_ok = df[df['status'] == 'ok']
print(f'df_ok shape: {df_ok.shape}')
if g_cols: print(f'G non-null: {df_ok[g_cols].notna().mean().mean():.1%}')
if i_cols: print(f'I non-null: {df_ok[i_cols].notna().mean().mean():.1%}')
"

# Check figures output dirs
ls figures/
ls figures/supplementary/
```

---

## Summary of New Files

| File | Purpose |
|---|---|
| `figures_for_article/figures_helpers.py` | Data prep utilities only; no plotting functions |
| `figures_for_article/Finally_assembled_figures_for_article.ipynb` | New notebook: Figs 7–11 + Supp A–G + Supp 9 |
| `figures_for_article/fig10_metric_star_visualization.py` | Standalone star/radar metric visualization script |
| `figures_for_article/figures/fig7_local_metrics_neighborhood.{svg,png}` | Fig 7 output |
| `figures_for_article/figures/fig8_structural_distance_metrics.{svg,png}` | Fig 8 output |
| `figures_for_article/figures/fig8b_distributional_similarity_na_retention.{svg,png}` | Fig 8B output |
| `figures_for_article/figures/fig9_cross_metric_correlation_factor_importance.{svg,png}` | Fig 9 output |
| `figures_for_article/figures/fig10_best_approaches_composite_ranking.{svg,png}` | Fig 10 output |
| `figures_for_article/figures/fig11_decision_tree_harmonization_selection.{svg,png}` | Fig 11 output |
| `figures_for_article/figures/supplementary/supp9_embeddings_best_stars.{svg,png}` | Supp Fig 9 output |
| `figures_for_article/figures/supplementary/supp_a_nona_genes_per_batch.{svg,png}` | Supp A output |
| `figures_for_article/figures/supplementary/supp_b_imputation_gene_overlap_sankey.{svg,png}` | Supp B output |
| `figures_for_article/figures/supplementary/supp_c_gene_retention_fl_gene_sets.{svg,png}` | Supp C output |
| `figures_for_article/figures/supplementary/supp_d_group_b_detail_kbet_asw_cms.{svg,png}` | Supp D output |
| `figures_for_article/figures/supplementary/supp_e_group_c_centroid_dispersion.{svg,png}` | Supp E output |
| `figures_for_article/figures/supplementary/supp_f_group_h_euclidean_distance.{svg,png}` | Supp F output |
| `figures_for_article/figures/supplementary/supp_g_group_g_graph_connectivity.{svg,png}` | Supp G output |

---

## TODO Checklist

Implementation is divided into 4 blocks. Each block can be requested independently to stay within context and token limits.

---

### ── BLOCK 1: Helper Module + Notebook Setup ─────────────────────────────────

- [x] Create `figures_for_article/figures_helpers.py`
- [x] Implement `save_figure(fig, name, figures_dir)` — SVG + PNG output
- [x] Implement `load_metrics_data(csv_path)` — returns (df_ok, df_normed, scoring_cols, col_meta); use same filtering as `harmonization_metrics_analysis_v3.ipynb`
- [x] Implement `build_best_vs_rest(df_ok, top_ids, best_label, best_color)` — returns (df_best, df_best_tagged, data_v3)
- [x] Implement `compute_nona_genes_per_batch(comb_exp_raw, comb_ann, batch_to_platform_group)` — per-batch noNA counts
- [x] Implement `load_gene_lists_from_s3(s3_client, bucket, strategies, imputations, ...)` — JSON sidecar downloads
- [x] Verify `python -c "import figures_helpers as fh; print('OK')"` passes
- [x] Create `figures_for_article/Finally_assembled_figures_for_article.ipynb`
- [x] Cell 0: imports, rcParams, constants (FIGURES_DIR, GLOBAL_FONT_SIZE, BEST_COLOR, S3_BUCKET, METRICS_CSV_PATH, METRIC_TYPE_MAP)
- [x] Cell 1: metrics data load + `_top_ids` hardcoded + `build_best_vs_rest()` call + assertion `len(df_best)==15` (uses v3 notebook's validated list; H_rnaseq_illumina and L_rnaseq_all_arrays pending computation)
- [x] Cell 2: palette dicts (method_pal 33+Best, strat_pal 16, imp_pal, harshness_pal) + HARSHNESS_MAP + `get_metric_cols()` helper + harshness assignment to df_ok and data_v3
- [x] Cell 3 (renumbered): S3 data load (raw expression + annotation) with note that this cell is optional for gene retention figs
- [x] Cell 4 (renumbered): placeholder Fig 7 cell confirming setup complete
- [x] Confirm exactly 5 setup cells — verified all execute cleanly; df_ok=2407×237, scoring_cols=85, df_best=15

---

### ── BLOCK 2: Metric Figures — Local, Structural, Distributional ─────────────

- [x] `## Figure 7` — Local Neighborhood Metrics: kBET strip, iLISI×cLISI scatter, graph connectivity bar, UMAP entropy box, tSNE entropy box, local-vs-global scatter
- [x] Verify `kbet_acceptance_rate_RNA_BATCH` column name — confirmed correct (4 kBET cols in data)
- [x] Add Group G guard: skip graph connectivity panel if column coverage < 50% — guard implemented; coverage=94.1% → panel shows
- [x] Run Fig 7 → visually inspect; confirm iLISI×cLISI trade-off arc and kBET method separation → assign MAIN or SUPPLEMENTARY (pending Daniil review)
- [x] `## Figure 8` — Structural/Distance: centroid dispersion heatmap, WaterMelon scatter, WaterMelon ratio bar, CMS barplot, ASW batch+bio grouped bar
- [x] Add Group I (WaterMelon) guard: skip panels if column coverage < 50% — guard implemented; coverage=96.1% → panels show
- [x] Run Fig 8 → inspect; if centroid dispersion shows clear method ranking → MAIN (pending Daniil review)
- [x] `## Figure 8B` — Distributional Similarity: KS mean D bar, fraction significant KS stacked bar, per-gene CV box, bimodal fraction bar, NA cells heatmap, noNA% by harshness×imp bar
- [x] Run Fig 8B → inspect; assign MAIN or SUPPLEMENTARY (pending Daniil review)
- [x] `## Supplementary Figure 9` — PCA/UMAP/tSNE embeddings with Best ★ highlights (placeholder cell; requires embedding coordinates from visual inspection notebook)
- [x] Add `plt.close()` after every `save_figure()` call

---

### ── BLOCK 3: Analysis + Ranking Figures + Gene Retention ────────────────────

- [x] `## Figure 9` — Cross-metric correlation: local-vs-global scatter with harshness coloring, composite score violin+strip by harshness, factor importance η² barplot, metric type stacked bar by method
- [x] Run Fig 9 → inspect; confirm factor importance hierarchy: strat > method > post_rm > imp → MAIN (requires notebook execution)
- [x] `## Figure 10` — Composite ranking: lollipop ranking, parallel coords for 15 Best, equal-vs-weighted scatter, method×group bubble chart (categorical scatter bug fixed with numeric positions)
- [x] Compute both `composite_score_equal` and `composite_score_weighted` in the Fig 10 cell
- [x] Create `fig10_metric_star_visualization.py` — standalone script: star/radar with rays per metric group, ray length ∝ superiority of Best 15; bar reference panel alongside radar
- [x] Run Fig 10 → inspect; lollipop should show Best ★ cluster in top quartile → MAIN (requires notebook execution)
- [x] `## Supplementary Figure A` — NA genes per batch (sorted by noNA%, colored by Platform_group; guarded — skips if comb_exp_raw not loaded)
- [x] `## Supplementary Figure B` — Imputation gene overlap Sankey (left panel: node diagram; right panel: stacked bar with hatch for imputed genes; guarded — skips if neither gene_sets nor comb_exp_raw available)
- [x] `## Supplementary Figure C` — Gene retention: % noNA heatmap (method × imp), FL gene set curves (guarded), GO enrichment placeholder

---

### ── BLOCK 4: Decision Tree + Supplementary Details + Documentation ──────────

- [x] `## Figure 11` — FancyBboxPatch tree inside notebook cell; 4 levels (Root → L1 biomaterial → L2 method → L3 QC); colored left-side level labels; legend for primary/alternative/neutral; figsize=(14,9) landscape
- [x] `## Supplementary Figure D` — Group B boxplot grid: one panel per scoring_col in Group B; sorted by method mean; Best ★ overlay; adapts to any number of cols (auto _ncols=3, _nrows computed)
- [x] `## Supplementary Figure E` — Group C stripplot grid (centroid dispersion); mean line overlay; strategy-colored dots
- [x] `## Supplementary Figure F` — Group H barplot grid (Euclidean distance ratio); Best ★ overlay
- [x] `## Supplementary Figure G` — Group G barplot grid (graph connectivity); double guard: absent-cols guard + < 5% coverage guard
- [x] Assign `## [MAIN]` / `## [SUPPLEMENTARY]` annotation — pending Daniil's visual review of saved outputs (not auto-assignable without running the notebook)
- [x] Update `figures_for_article/CLAUDE.md` — "Figures yet to be implemented" table updated; new Figs 7–11 and Supp A–G, Supp 9 added to implemented table (done in BLOCK 3)
- [x] Update `figures_for_article/article_figures_status_260625.md` — new section added for all Finally_assembled figures
- [x] Update `figures_for_article/notebooks_for_figures_260625.md` — section 4 added for `Finally_assembled_figures_for_article.ipynb`
- [x] Confirm notebook < 100 MB: 92 KB (outputs stripped; all plt.close() after save_figure)

---

**Ready to implement when you approve.**
