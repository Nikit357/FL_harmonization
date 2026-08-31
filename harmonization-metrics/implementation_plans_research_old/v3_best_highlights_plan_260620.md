# v3 Notebook: Best-Approach Highlight Plan
**Date:** 2026-06-20  
**Author:** Daniil Nikitin  
**File to create:** `harmonization_metrics_analysis_v3.ipynb`  
**Source:** `harmonization_metrics_analysis_v2.ipynb` (321 cells, ~23 500 lines)

---

## Overview

Create `harmonization_metrics_analysis_v3.ipynb` from v2 by doing three things:

1. **Add infrastructure early** — move the `_top_ids` definition into the early setup section and create `df_best`, best-approach constants, and helper functions there.
2. **Rewrite every major comparative plot cell** — add `"★ Best"` as a new virtual group (a new bar, a new boxplot entry, or a star overlay) **inside the same figure**. No companion cells, no separate figures. If a barplot shows 14 strategies, the v3 version shows 15 bars where the 15th is `"★ Best"`, highlighted in vivid red with hatching and a star annotation.
3. **Strip all cell outputs** — clear `outputs` arrays so the notebook stays under 100 MB for GitHub.

---

## Background: `_top_ids` Reference

```python
# Tuple order: (method, imp, strat), all with post_rm == False
_top_ids = [
    ("10_mnn",     "strict",      "S0_no_removal"),
    ("10_mnn",     "strict",      "H_affymetrix_extended"),
    ("10_mnn",     "strict",      "D_malignant_only"),
    ("04_sva",     "knn",         "C_rnaseq_only"),
    ("04_sva",     "softimpute",  "C_rnaseq_only"),
    ("16_fsqn_r",  "knn",         "C_rnaseq_only"),
    ("16_fsqn_r",  "softimpute",  "C_rnaseq_only"),
    ("16_fsqn_r",  "strict",      "C_rnaseq_only"),
    ("10_mnn",     "strict",      "J_ff_only"),
    ("16_fsqn_r",  "strict",      "J_ff_only"),
    ("04_sva",     "knn",         "K_ffpe_only"),
    ("04_sva",     "strict",      "K_ffpe_only"),
    ("04_sva",     "softimpute",  "K_ffpe_only"),
    ("13_fsmvn",   "strict",      "S0_no_removal"),
    ("33_amdbnorm","strict",      "S0_no_removal"),
]
```

Derived dimension sets (used to create the `"★ Best"` virtual group):
| Dimension | Values in `_top_ids` | Count |
|---|---|---|
| `_top_methods` | 04_sva, 10_mnn, 13_fsmvn, 16_fsqn_r, 33_amdbnorm | 5 |
| `_top_strats` | C_rnaseq_only, D_malignant_only, H_affymetrix_extended, J_ff_only, K_ffpe_only, S0_no_removal | 6 |
| `_top_imps` | knn, softimpute, strict | 3 (all) |

---

## Design Decisions

### Visual encoding for `"★ Best"` group

| Element | Value | Rationale |
|---|---|---|
| Label | `"★ Best"` | Appears as a new x-tick entry at the end of each barplot/catplot |
| Bar fill | `BEST_COLOR = "#E63946"` (vivid red) | Clearly distinct from all existing palettes |
| Bar hatch | `BEST_HATCH = "////"` | Diagonal stripe giving a "dotted" appearance |
| Bar edge | `edgecolor="black"`, `linewidth=1.5` | Dark border for contrast |
| Star annotation | `"★"` text on top of each best bar | Extra visual call-out |
| Scatter marker | `marker="*"`, `s=400`, `BEST_COLOR` | For scatterplots — overlaid directly on the same axes |
| Zorder | `10` | Stars/best bars appear on top |

### What `"★ Best"` means per plot type

| Plot type | Implementation |
|---|---|
| `bar_plot` (x=method) | Relabel df_best rows as `method="★ Best"`, concat to main data, append `"★ Best"` to `order`; style those bars post-hoc |
| `bar_plot` (x=strat) | Same but `strat="★ Best"` |
| `sns.catplot` (x=method, col=imp) | Relabel `method="★ Best"`, concat, append to `order`; style the `"★ Best"` boxes post-hoc |
| `sns.catplot` (x=strat, col=imp) | Same but `strat="★ Best"` |
| `scatter_plot` (hue=method/strat) | Call `scatter_overlay_best(ax, df_best, x, y)` on the SAME ax immediately after the scatter call — no separate figure |

---

## Infrastructure to Add (new cells in v3 setup section)

### Infra cell A — Best-approach constants and `df_best`

Insert **immediately after** the `df_ok = df[df["status"] == "ok"]` cell (identifiable by substring `'df_ok = df[df["status"] == "ok"]'`).

```python
# ── Best-approach selection: constants, lookup, filtered DataFrame ──────────
_top_ids = [
    ("10_mnn",      "strict",     "S0_no_removal"),
    ("10_mnn",      "strict",     "H_affymetrix_extended"),
    ("10_mnn",      "strict",     "D_malignant_only"),
    ("04_sva",      "knn",        "C_rnaseq_only"),
    ("04_sva",      "softimpute", "C_rnaseq_only"),
    ("16_fsqn_r",   "knn",        "C_rnaseq_only"),
    ("16_fsqn_r",   "softimpute", "C_rnaseq_only"),
    ("16_fsqn_r",   "strict",     "C_rnaseq_only"),
    ("10_mnn",      "strict",     "J_ff_only"),
    ("16_fsqn_r",   "strict",     "J_ff_only"),
    ("04_sva",      "knn",        "K_ffpe_only"),
    ("04_sva",      "strict",     "K_ffpe_only"),
    ("04_sva",      "softimpute", "K_ffpe_only"),
    ("13_fsmvn",    "strict",     "S0_no_removal"),
    ("33_amdbnorm", "strict",     "S0_no_removal"),
]
_top_ids_set = set(_top_ids)                         # O(1) lookup
_top_methods = sorted({m for m, i, s in _top_ids})
_top_strats  = sorted({s for m, i, s in _top_ids})
_top_imps    = sorted({i for m, i, s in _top_ids})

BEST_COLOR      = "#E63946"   # vivid red — reserved exclusively for "★ Best" highlights
BEST_HATCH      = "////"      # diagonal stripe
BEST_MARKER     = "*"
BEST_MARKERSIZE = 400
BEST_EDGECOLOR  = "black"
BEST_ALPHA      = 0.85
BEST_LABEL      = "★ Best"

df_ok["is_best"] = df_ok.apply(
    lambda r: (r["method"], r["imp"], r["strat"]) in _top_ids_set and not r["post_rm"],
    axis=1,
)
df_best = df_ok[df_ok["is_best"]].copy()
print(f"df_best: {len(df_best)} rows  |  methods: {df_best.method.nunique()}  "
      f"|  strats: {df_best.strat.nunique()}")
```

### Infra cell B — Helper functions

Insert **immediately after** the `scatter_plot` / `bar_plot` helper cell (identifiable by `"def scatter_plot"`).

```python
# ── Helpers for "★ Best" group embedding ────────────────────────────────────

def add_best_group_to_melted(
    df_melted: pd.DataFrame,
    df_best: pd.DataFrame,
    group_col: str,
    metric_col: str,
    value_col: str,
) -> pd.DataFrame:
    """
    Append rows where group_col == BEST_LABEL to df_melted.
    df_best must already be filtered to is_best rows.
    """
    df_best_copy = df_best.copy()
    df_best_copy[group_col] = BEST_LABEL
    melted_best = df_best_copy[[group_col] + [c for c in df_best_copy.columns
                                               if c.startswith(metric_col.split("_")[0])]
                               ].melt(id_vars=group_col,
                                      var_name=metric_col, value_name=value_col)
    return pd.concat([df_melted, melted_best], ignore_index=True)


def style_best_bars(ax: plt.Axes, order: list) -> None:
    """
    Apply BEST_COLOR, hatching, and star annotation to bars in the BEST_LABEL group.
    Assumes BEST_LABEL is in `order`; uses ax.containers (one per hue).
    """
    if BEST_LABEL not in order:
        return
    best_idx = list(order).index(BEST_LABEL)
    ymax = ax.get_ylim()[1]
    for container in ax.containers:
        bars = list(container)
        if best_idx < len(bars):
            b = bars[best_idx]
            b.set_facecolor(BEST_COLOR)
            b.set_hatch(BEST_HATCH)
            b.set_edgecolor(BEST_EDGECOLOR)
            b.set_linewidth(1.5)
            h = b.get_height()
            if h > 0:
                ax.text(
                    b.get_x() + b.get_width() / 2,
                    h + ymax * 0.005,
                    "★", ha="center", va="bottom",
                    color=BEST_COLOR, fontsize=FONT_BASE + 3, fontweight="bold",
                    zorder=11,
                )


def style_best_boxes(g: sns.FacetGrid, order: list) -> None:
    """
    Apply BEST_COLOR and hatching to the BEST_LABEL box in each FacetGrid axis.
    Works for catplot kind='box'.
    """
    if BEST_LABEL not in order:
        return
    best_idx = list(order).index(BEST_LABEL)
    for ax_ in g.axes.flat:
        boxes = [p for p in ax_.patches if hasattr(p, "get_path")]
        n_per_x = max(1, len(boxes) // len(order)) if boxes else 1
        for k in range(n_per_x):
            patch_idx = best_idx * n_per_x + k
            if patch_idx < len(boxes):
                boxes[patch_idx].set_facecolor(BEST_COLOR)
                boxes[patch_idx].set_hatch(BEST_HATCH)
                boxes[patch_idx].set_edgecolor(BEST_EDGECOLOR)
                boxes[patch_idx].set_linewidth(1.5)


def scatter_overlay_best(
    ax: plt.Axes,
    df_best: pd.DataFrame,
    x: str,
    y: str,
    label: str = "★ Best approaches",
) -> None:
    """Overlay star markers for best approaches on an existing scatter axes."""
    ax.scatter(
        df_best[x], df_best[y],
        marker=BEST_MARKER, s=BEST_MARKERSIZE,
        color=BEST_COLOR, edgecolors=BEST_EDGECOLOR,
        linewidths=0.7, alpha=BEST_ALPHA,
        zorder=10, label=label,
    )
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, loc="best", framealpha=0.7, fontsize=FONT_LEGEND)
```

---

## Cell Modification Patterns

There are three canonical patterns for modifying original cells. Each target cell is **replaced** (not followed by a companion) using `replace_cell()` in `create_v3_notebook.py`.

---

### Pattern P1 — Barplot with pre-melted data (hue=covariate)

**Example:** r2 barplot by method (target: `"a_r2_by_method_covariate"`).

**Modification to apply to the cell source:**
1. After computing `df_long_r2` (melted): add `df_best` rows with `method = BEST_LABEL`, concatenate.
2. After computing `method_order_r2`: append `BEST_LABEL` at the end.
3. Change `bar_plot(..., save_path="a_r2_by_method_covariate")` → remove `save_path`, save manually after styling.
4. After `bar_plot(...)`: call `style_best_bars(ax, method_order_r2_v3)`.
5. Save figure.

**Modified cell source for A1 (r2 barplot by method):**

```python
r2_cols_main = ["r2_RNA_BATCH", "r2_Major_group", "r2_TUMOR_NORMAL", "r2_PLATFORM_RNA"]
r2_cols_present = [c for c in r2_cols_main if c in df_ok.columns]
method_order_r2 = (
    df_ok.groupby("method")["r2_RNA_BATCH"].mean().sort_values().index.tolist()
)
r2_pal_covar = {col: annot_pal.get(col[3:], "#AAAAAA") for col in r2_cols_main}

df_long_r2 = df_ok[["method"] + r2_cols_present].melt(
    id_vars="method", var_name="covariate", value_name="r2"
)

# v3: append "★ Best" virtual group
df_best_r2 = df_best[["method"] + r2_cols_present].copy()
df_best_r2["method"] = BEST_LABEL
df_long_r2 = pd.concat(
    [df_long_r2,
     df_best_r2.melt(id_vars="method", var_name="covariate", value_name="r2")],
    ignore_index=True,
)
method_order_r2_v3 = method_order_r2 + [BEST_LABEL]

ax = bar_plot(
    df_long_r2,
    x="method",
    y="r2",
    hue="covariate",
    palette=r2_pal_covar,
    order=method_order_r2_v3,
    figsize=(20, 5),
    ylabel="Mean R²",
    title="Mean R² per covariate × method (sorted by r2_RNA_BATCH) — ★ Best = manually selected",
    legend_outside=True,
    xtick_rotation=90,
)
ax.axhline(0.20, color="red", linestyle="--", linewidth=1.0, label="Target r²=0.20")
style_best_bars(ax, method_order_r2_v3)
ax.get_figure().savefig(FIGURES_DIR / "a_r2_by_method_covariate.svg", bbox_inches="tight")
ax.get_figure().savefig(FIGURES_DIR / "a_r2_by_method_covariate.png", bbox_inches="tight", dpi=200)
plt.show()
```

---

### Pattern P2 — Catplot (kind=box, x=method or x=strat, col=imp/strat)

**Example:** kBET catplot by imp (target: `"a_kbet_catplot_by_imp.svg"`, `col="imp"`).

**Modification to apply:**
1. Tag `df_best` rows with `method = BEST_LABEL` and concatenate with `df_ok`.
2. Append `BEST_LABEL` to `method_order`.
3. After `sns.catplot(...)`: call `style_best_boxes(g, method_order_v3)`.
4. Save using `g.figure.savefig`.

**Modified cell source for B6 (kBET catplot x=method, col=imp):**

```python
method_order = (
    df_ok.groupby("method")["kbet_acceptance_rate_RNA_BATCH"]
    .mean()
    .sort_values()
    .index.tolist()
)
# v3: append "★ Best" virtual group
df_best_tagged = df_best.copy()
df_best_tagged["method"] = BEST_LABEL
data_v3 = pd.concat([df_ok, df_best_tagged], ignore_index=True)
method_order_v3 = method_order + [BEST_LABEL]

g = sns.catplot(
    data=data_v3,
    x="method",
    y="kbet_acceptance_rate_RNA_BATCH",
    col="imp",
    kind="box",
    height=4,
    aspect=1.5,
    order=method_order_v3,
    palette=method_pal,
)
g.set_xticklabels(rotation=45, ha="right", fontsize=FONT_SMALL)
g.set_titles("{col_name}", size=FONT_TITLE)
g.set_axis_labels("Method", "kBET RNA_BATCH", fontsize=FONT_LABEL)
g.figure.suptitle(
    "kBET RNA_BATCH by method × imputation — ★ Best = manually selected",
    y=1.02, fontsize=FONT_TITLE
)
style_best_boxes(g, method_order_v3)
g.figure.savefig(FIGURES_DIR / "a_kbet_catplot_by_imp.svg", bbox_inches="tight")
g.figure.savefig(FIGURES_DIR / "a_kbet_catplot_by_imp.png", bbox_inches="tight", dpi=200)
plt.show()
```

---

### Pattern P3 — Scatterplot overlay

**Example:** kBET vs iLISI scatter (target: `"b_kbet_ilisi_scatter"`).

**Modification to apply:**
1. After the `scatter_plot(...)` or `sns.scatterplot(...)` call on the same `ax`, add `scatter_overlay_best(ax, df_best, x, y)`.
2. Keep the same `save_path` or manual save.

**Modified cell source for B1 (kBET vs iLISI scatter):**

```python
ax = scatter_plot(
    df_ok,
    x="kbet_acceptance_rate_RNA_BATCH",
    y="ilisi_norm_RNA_BATCH",
    hue="method",
    style="imp",
    palette=method_pal,
    alpha=0.55,
    s=30,
    figsize=(9, 7),
    title="kBET vs iLISI — ★ stars = manually selected best approaches",
    legend_outside=True,
)
# v3: overlay best approaches as stars on same axes
scatter_overlay_best(ax, df_best,
                     x="kbet_acceptance_rate_RNA_BATCH",
                     y="ilisi_norm_RNA_BATCH")
ax.get_figure().savefig(FIGURES_DIR / "b_kbet_ilisi_scatter.svg", bbox_inches="tight")
ax.get_figure().savefig(FIGURES_DIR / "b_kbet_ilisi_scatter.png", bbox_inches="tight", dpi=200)
plt.show()
```

---

## All Cells to Modify

The table below lists every cell to modify, identified by a unique search string in its source. Each cell is **replaced** (not followed by a companion). The `Pattern` column refers to P1/P2/P3 above; `group_col` is the x-axis dimension.

| ID | Search string (unique in v2) | Plot type | Pattern | group_col |
|---|---|---|---|---|
| A1 | `"a_r2_by_method_covariate"` | bar hue=covariate | P1 | method |
| A2 | `"pcr_by_method_covariate"` | bar hue=covariate | P1 | method |
| A3 | `"pcr_by_strat_covariate"` | bar hue=covariate | P1 | strat |
| A4 | `"a_r2_catplot_by_imp.svg"` | catplot col=imp | P2 | method |
| A5 | `"a_pcr_catplot_by_imp.svg"` | catplot col=imp | P2 | method |
| A6 | `"a_pcr_catplot_by_strat.svg"` | catplot col=strat | P2 | method |
| A7 | `"a_pcr_catplot_by_post_rm.svg"` | catplot col=post_rm | P2 | method |
| A8 | `"a_dsc_by_method_covariate"` | bar hue=covariate | P1 | method |
| A9 | `"a_dsc_by_strat_covariate"` | bar hue=covariate | P1 | strat |
| B1 | `"b_kbet_ilisi_scatter"` | scatter | P3 | — |
| B2 | `"kbet_by_method_covariate"` | bar hue=covariate | P1 | method |
| B3 | `"kbet_by_strat_covariate"` | bar hue=covariate | P1 | strat |
| B4 | `"lisi_by_method_covariate"` | bar hue=covariate | P1 | method |
| B5 | `"lisi_by_strat_covariate"` | bar hue=covariate | P1 | strat |
| B6 | `"a_kbet_catplot_by_imp.svg"` | catplot col=imp | P2 | method |
| B7 | `"a_kbet_catplot_by_strat.svg"` | catplot col=strat | P2 | method |
| B8 | `"a_kbet_catplot_by_imp_strat.svg"` | catplot col=imp | P2 | strat |
| B9 | `"a_ilisi_catplot_by_imp.svg"` | catplot col=imp | P2 | method |
| B10 | `"b_isisi_catplot_by_strat.svg"` | catplot col=strat | P2 | method |
| B11 | `"a_ilisi_catplot_by_imp_strat.svg"` | catplot col=imp | P2 | strat |
| I1 | `"i_wm_batch_bio_tradeoff"` | scatter | P3 | — |
| I2 | `"i_wm_ratio_vs_composite"` | scatter | P3 | — |
| K1 | `"k_pct_genes_nona_by_method"` | bar orient=h | P1 | method |
| K2 | `"k_pct_genes_nona_by_harshness"` | boxplot | P2-like | harshness_level |
| S1 | `"score_batch_mixing"` + Pareto scatter | scatter | P3 | — |

---

## Implementation: `create_v3_notebook.py`

Create at `harmonization-metrics/create_v3_notebook.py`.

### Key difference from a companion-cell approach

v3 REPLACES original cell sources using `replace_cell()`. No new cells are inserted after target cells. The cell count in v3 will be only slightly higher than v2 (only the two infra cells A and B are new insertions).

### Script skeleton

```python
"""
create_v3_notebook.py
Generates harmonization_metrics_analysis_v3.ipynb from v2 by:
  1. Reading v2 with nbformat.
  2. Stripping all outputs.
  3. Inserting two new infrastructure cells (A and B) after the data-loading cell.
  4. Replacing each target cell source with a modified version that embeds "★ Best".
  5. Writing v3.
"""
import nbformat
from pathlib import Path

INPUT  = Path("harmonization_metrics_analysis_v2.ipynb")
OUTPUT = Path("harmonization_metrics_analysis_v3.ipynb")

with open(INPUT) as f:
    nb = nbformat.read(f, as_version=4)

# ── Step 1: strip all outputs ────────────────────────────────────────────────
for cell in nb.cells:
    if cell.cell_type == "code":
        cell.outputs = []
        cell.execution_count = None

# ── Step 2: utility functions ────────────────────────────────────────────────
def find_idx(cells, search: str) -> int:
    for i, c in enumerate(cells):
        if search in c.source:
            return i
    raise ValueError(f"Not found: {search!r}")

def replace_cell(cells, search: str, new_source: str) -> None:
    """Replace source of the first cell whose source contains `search`."""
    idx = find_idx(cells, search)
    cells[idx].source = new_source

def new_code_cell(source: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_code_cell(source=source)

# ── Step 3: insert infra cells (A then B) AFTER data-loading cell ────────────
# Insert B first (to keep insertion order correct when inserting after same idx)
helpers_idx = find_idx(nb.cells, "def scatter_plot")
nb.cells.insert(helpers_idx + 1, new_code_cell(INFRA_B_SOURCE))

df_ok_idx = find_idx(nb.cells, 'df_ok = df[df["status"] == "ok"]')
nb.cells.insert(df_ok_idx + 1, new_code_cell(INFRA_A_SOURCE))

# ── Step 4: replace each target cell ─────────────────────────────────────────
# (Each replace_cell call is independent — order does not matter)
replace_cell(nb.cells, "a_r2_by_method_covariate",   A1_SOURCE)
replace_cell(nb.cells, "pcr_by_method_covariate",    A2_SOURCE)
replace_cell(nb.cells, "pcr_by_strat_covariate",     A3_SOURCE)
replace_cell(nb.cells, "a_r2_catplot_by_imp.svg",    A4_SOURCE)
replace_cell(nb.cells, "a_pcr_catplot_by_imp.svg",   A5_SOURCE)
replace_cell(nb.cells, "a_pcr_catplot_by_strat.svg", A6_SOURCE)
replace_cell(nb.cells, "a_pcr_catplot_by_post_rm.svg", A7_SOURCE)
replace_cell(nb.cells, "a_dsc_by_method_covariate",  A8_SOURCE)
replace_cell(nb.cells, "a_dsc_by_strat_covariate",   A9_SOURCE)
replace_cell(nb.cells, "b_kbet_ilisi_scatter",       B1_SOURCE)
replace_cell(nb.cells, "kbet_by_method_covariate",   B2_SOURCE)
replace_cell(nb.cells, "kbet_by_strat_covariate",    B3_SOURCE)
replace_cell(nb.cells, "lisi_by_method_covariate",   B4_SOURCE)
replace_cell(nb.cells, "lisi_by_strat_covariate",    B5_SOURCE)
replace_cell(nb.cells, "a_kbet_catplot_by_imp.svg",  B6_SOURCE)
replace_cell(nb.cells, "a_kbet_catplot_by_strat.svg", B7_SOURCE)
replace_cell(nb.cells, "a_kbet_catplot_by_imp_strat.svg", B8_SOURCE)
replace_cell(nb.cells, "a_ilisi_catplot_by_imp.svg", B9_SOURCE)
replace_cell(nb.cells, "b_isisi_catplot_by_strat.svg", B10_SOURCE)
replace_cell(nb.cells, "a_ilisi_catplot_by_imp_strat.svg", B11_SOURCE)
replace_cell(nb.cells, "i_wm_batch_bio_tradeoff",    I1_SOURCE)
replace_cell(nb.cells, "i_wm_ratio_vs_composite",    I2_SOURCE)
replace_cell(nb.cells, "k_pct_genes_nona_by_method", K1_SOURCE)
replace_cell(nb.cells, "k_pct_genes_nona_by_harshness", K2_SOURCE)
# For S1 (Pareto scatter), identify the correct unique search string at runtime
# replace_cell(nb.cells, "score_batch_mixing",         S1_SOURCE)

# ── Step 5: validate and write ───────────────────────────────────────────────
nbformat.validate(nb)
with open(OUTPUT, "w") as f:
    nbformat.write(nb, f)

print(f"Written: {OUTPUT}  ({OUTPUT.stat().st_size / 1e6:.1f} MB)")
print(f"Total cells: {len(nb.cells)}")
```

### Key implementation notes

1. **`replace_cell` is order-independent**: replacing cell sources does not change cell indices, so any order is fine. Only the two `insert` calls (infra A and B) are order-sensitive — insert B first, then A (both after the helpers cell), or insert A after data-loading and B after helpers in that exact order.

2. **`"★ Best"` rows in melted DataFrames**: For P1 cells, the key lines to add before the `bar_plot` call are:
   ```python
   df_best_copy = df_best.copy()
   df_best_copy[group_col] = BEST_LABEL
   df_long = pd.concat([df_long,
       df_best_copy[[group_col] + metric_cols].melt(id_vars=group_col, ...)],
       ignore_index=True)
   order_v3 = original_order + [BEST_LABEL]
   ```

3. **Removing `save_path` from `bar_plot`**: When we need post-hoc styling (P1 cells), remove `save_path` from the `bar_plot` call and add explicit `ax.get_figure().savefig(...)` calls after styling.

4. **`ax.containers` reliability**: `style_best_bars()` uses `ax.containers`, which seaborn ≥ 0.12 populates. If the environment uses an older seaborn, fall back to a positional patch approach. Check seaborn version during smoke testing.

5. **`_top_ids` duplication**: Defined twice — in infra cell A (for `df_best`) and in v2's original cell ~259 (for `top_n` in Part 2). Both stay. If the kernel runs linearly, cell 259 will redefine `_top_ids` without breaking anything (it's the same list).

6. **Unique search strings**: Two cells in v2 have nearly identical save paths (e.g., `kbet_by_method_covariate` appears in cell 159 for §3.2 and possibly in cell 217 as a duplicate). `find_idx` returns the FIRST match — verify the correct cell is targeted in smoke testing.

---

## Files That Do NOT Need to Change

| File | Reason |
|---|---|
| `compute_batch_metrics.py` | Core metrics library — no changes |
| `run_metrics_parallel.py`, `run_metrics_job.py`, `run_metrics_concat.py` | Pipeline runners — notebook-only change |
| `harmonization_metrics_analysis_v2.ipynb` | Read-only source |
| Any `k8s/` manifest | No infrastructure change |
| `CLAUDE.md` (harmonization-metrics) | Update to note v3 as the active analysis notebook |

---

## Side Effects and Caveats

1. **Figure overwrite**: v3 cells save to the **same file names** as v2 (e.g., `a_r2_by_method_covariate.svg`). This is intentional — v3 figures are the updated versions that include `"★ Best"`. The old v2 figures will be overwritten when v3 is run.

2. **All `_top_ids` use `post_rm == False`**: For cells that filter `df_ok` to `post_rm == False` before plotting, `df_best` is already so filtered, so concatenation is consistent.

3. **`style_best_boxes` fragility**: For catplot kind=box, box patches are stored differently than bar patches. The implementation uses a size-based heuristic. Smoke testing should verify that the "★ Best" boxes are correctly colored. If not, fall back to an alternative: overlay a colored scatter strip on the "★ Best" x-position after the catplot.

4. **Palette for `"★ Best"` in catplots**: When `palette=method_pal` is passed to catplot, `"★ Best"` won't be in `method_pal` (it's a new label). seaborn will assign a default color. `style_best_boxes()` overrides this to `BEST_COLOR` post-hoc. This is expected and correct behavior.

5. **Notebook size**: v3 has outputs cleared. Cell count increases by only 2 (infra A and B). File size will be similar to or smaller than v2.

6. **Duplicate search key `kbet_by_method_covariate`**: This string appears in cells 159 and 217. `find_idx` returns the FIRST occurrence (cell 159). Cell 217 is a duplicate plot and does not need modification. If cell 217 should also be modified, use a more specific search string (e.g., include adjacent code context).

---

## Verification Commands

```bash
cd ~/FL_harmonization/harmonization-metrics
source ~/venvs/collagen_3_11/bin/activate

# Generate v3
python create_v3_notebook.py

# Verify valid notebook and zero outputs
python -c "
import nbformat
nb = nbformat.read('harmonization_metrics_analysis_v3.ipynb', as_version=4)
with_out = [i for i, c in enumerate(nb.cells) if c.cell_type == 'code' and c.get('outputs')]
print(f'Total cells: {len(nb.cells)}')
print(f'Cells with outputs (should be 0): {len(with_out)}')
"

# Verify key strings exist
grep -c 'BEST_COLOR'            harmonization_metrics_analysis_v3.ipynb
grep -c 'BEST_LABEL'            harmonization_metrics_analysis_v3.ipynb
grep -c 'style_best_bars'       harmonization_metrics_analysis_v3.ipynb
grep -c 'style_best_boxes'      harmonization_metrics_analysis_v3.ipynb
grep -c 'scatter_overlay_best'  harmonization_metrics_analysis_v3.ipynb

# File size (<100 MB)
ls -lh harmonization_metrics_analysis_v3.ipynb

# Smoke test: run one modified cell end-to-end (requires kernel)
# Open in JupyterLab and run cell A1 (r2 barplot) to verify "★ Best" bar appears
```

---

## TODO Checklist

### `create_v3_notebook.py`
- [ ] Write `find_idx(cells, search)` — returns first matching cell index
- [ ] Write `replace_cell(cells, search, new_source)` — replaces source in place
- [ ] Write `new_code_cell(source)` — creates nbformat code cell node
- [ ] Implement output stripping loop
- [ ] Write `INFRA_A_SOURCE` — full source for infra cell A (constants + `df_best`)
- [ ] Write `INFRA_B_SOURCE` — full source for infra cell B (helpers: `style_best_bars`, `style_best_boxes`, `scatter_overlay_best`)
- [ ] Write modified cell sources for Pattern P1 cells:
  - [ ] `A1_SOURCE` — r2 barplot by method (search: `"a_r2_by_method_covariate"`)
  - [ ] `A2_SOURCE` — pcr barplot by method (search: `"pcr_by_method_covariate"`)
  - [ ] `A3_SOURCE` — pcr barplot by strat (search: `"pcr_by_strat_covariate"`)
  - [ ] `A8_SOURCE` — dsc barplot by method (search: `"a_dsc_by_method_covariate"`)
  - [ ] `A9_SOURCE` — dsc barplot by strat (search: `"a_dsc_by_strat_covariate"`)
  - [ ] `B2_SOURCE` — kBET barplot by method (search: `"kbet_by_method_covariate"`)
  - [ ] `B3_SOURCE` — kBET barplot by strat (search: `"kbet_by_strat_covariate"`)
  - [ ] `B4_SOURCE` — LISI barplot by method (search: `"lisi_by_method_covariate"`)
  - [ ] `B5_SOURCE` — LISI barplot by strat (search: `"lisi_by_strat_covariate"`)
  - [ ] `K1_SOURCE` — NA retention barplot (search: `"k_pct_genes_nona_by_method"`)
- [ ] Write modified cell sources for Pattern P2 cells:
  - [ ] `A4_SOURCE` — r2 catplot col=imp (search: `"a_r2_catplot_by_imp.svg"`)
  - [ ] `A5_SOURCE` — pcr catplot col=imp (search: `"a_pcr_catplot_by_imp.svg"`)
  - [ ] `A6_SOURCE` — pcr catplot col=strat (search: `"a_pcr_catplot_by_strat.svg"`)
  - [ ] `A7_SOURCE` — pcr catplot col=post_rm (search: `"a_pcr_catplot_by_post_rm.svg"`)
  - [ ] `B6_SOURCE` — kBET catplot col=imp (search: `"a_kbet_catplot_by_imp.svg"`)
  - [ ] `B7_SOURCE` — kBET catplot col=strat (search: `"a_kbet_catplot_by_strat.svg"`)
  - [ ] `B8_SOURCE` — kBET catplot x=strat col=imp (search: `"a_kbet_catplot_by_imp_strat.svg"`)
  - [ ] `B9_SOURCE` — iLISI catplot col=imp (search: `"a_ilisi_catplot_by_imp.svg"`)
  - [ ] `B10_SOURCE` — iLISI catplot col=strat (search: `"b_isisi_catplot_by_strat.svg"`)
  - [ ] `B11_SOURCE` — iLISI catplot x=strat col=imp (search: `"a_ilisi_catplot_by_imp_strat.svg"`)
  - [ ] `K2_SOURCE` — harshness boxplot (search: `"k_pct_genes_nona_by_harshness"`)
- [ ] Write modified cell sources for Pattern P3 cells:
  - [ ] `B1_SOURCE` — kBET vs iLISI scatter (search: `"b_kbet_ilisi_scatter"`)
  - [ ] `I1_SOURCE` — WM batch vs bio scatter (search: `"i_wm_batch_bio_tradeoff"`)
  - [ ] `I2_SOURCE` — WM ratio vs composite (search: `"i_wm_ratio_vs_composite"`)
  - [ ] `S1_SOURCE` — Pareto frontier scatter (verify unique search string for score_batch_mixing scatter)
- [ ] Insert infra cell B after `scatter_plot` definition cell
- [ ] Insert infra cell A after `df_ok` creation cell
- [ ] Call `nbformat.validate(nb)` before writing
- [ ] Write to `harmonization_metrics_analysis_v3.ipynb`

### Verification
- [ ] Run `python create_v3_notebook.py` — zero errors
- [ ] Verify 0 cells with outputs in v3
- [ ] Verify file size < 100 MB
- [ ] Run cell A1 (r2 barplot) in JupyterLab — confirm `"★ Best"` bar appears red + hatched
- [ ] Run cell B6 (kBET catplot) — confirm `"★ Best"` box appears red + hatched
- [ ] Run cell B1 (scatter) — confirm star markers appear on top of existing points
- [ ] Update `CLAUDE.md` (harmonization-metrics) — note v3 is the active analysis notebook
