"""
create_v3_notebook.py
Generates harmonization_metrics_analysis_v3.ipynb from v2 by:
  1. Reading v2 with nbformat.
  2. Stripping all outputs.
  3. Inserting two new infrastructure cells (A and B) into the setup section.
  4. Replacing each target cell source with a modified version that embeds "★ Best"
     as a new virtual group inside the original plot (NOT a separate figure).
  5. Writing v3.
"""
import nbformat
from pathlib import Path

INPUT = Path("harmonization_metrics_analysis_v2.ipynb")
OUTPUT = Path("harmonization_metrics_analysis_v3.ipynb")

# ── Infra cell A: best-approach constants and df_best ────────────────────────
INFRA_A_SOURCE = '''\
# ── Best-approach selection: constants, lookup, filtered DataFrame ────────────
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
_top_ids_set = set(_top_ids)                       # O(1) lookup
_top_methods = sorted({m for m, i, s in _top_ids})
_top_strats  = sorted({s for m, i, s in _top_ids})
_top_imps    = sorted({i for m, i, s in _top_ids})

BEST_COLOR      = "#E63946"   # vivid red — reserved for "★ Best" highlights
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
'''

# ── Infra cell B: helper functions ───────────────────────────────────────────
INFRA_B_SOURCE = '''\
# ── Helpers for "★ Best" group embedding ─────────────────────────────────────


def style_best_bars(ax: plt.Axes, order: list, orient: str = "v") -> None:
    """
    Apply BEST_COLOR, hatching, and star annotation to the BEST_LABEL group.
    Uses ax.containers (one per hue, seaborn >= 0.12).
    orient: "v" for vertical bars (default), "h" for horizontal.
    Uses h * 1.05 for annotation offset — works for both linear and log scale.
    """
    if BEST_LABEL not in order:
        return
    best_idx = list(order).index(BEST_LABEL)
    for container in ax.containers:
        bars = list(container)
        if best_idx < len(bars):
            b = bars[best_idx]
            b.set_facecolor(BEST_COLOR)
            b.set_hatch(BEST_HATCH)
            b.set_edgecolor(BEST_EDGECOLOR)
            b.set_linewidth(1.5)
            if orient == "v":
                h = b.get_height()
                if h > 0:
                    ax.text(
                        b.get_x() + b.get_width() / 2,
                        h * 1.05,
                        "★",
                        ha="center", va="bottom",
                        color=BEST_COLOR, fontsize=FONT_BASE + 3, fontweight="bold",
                        zorder=11,
                    )
            else:  # horizontal bar
                w = b.get_width()
                if w > 0:
                    ax.text(
                        w * 1.02,
                        b.get_y() + b.get_height() / 2,
                        "★",
                        ha="left", va="center",
                        color=BEST_COLOR, fontsize=FONT_BASE + 3, fontweight="bold",
                        zorder=11,
                    )


def style_best_boxes(g: sns.FacetGrid, order: list) -> None:
    """
    Apply BEST_COLOR and hatching to the BEST_LABEL box in each FacetGrid axis.
    Works for catplot kind='box'.
    Identifies patches by x-position (best_idx = last in order).
    """
    if BEST_LABEL not in order:
        return
    best_idx = list(order).index(BEST_LABEL)
    n_groups = len(order)
    for ax_ in g.axes.flat:
        for patch in ax_.patches:
            if not hasattr(patch, "get_x"):
                continue
            x_center = patch.get_x() + patch.get_width() / 2
            # Box centers are at integer x-positions 0, 1, ..., n_groups-1
            if abs(x_center - best_idx) < 0.6:
                patch.set_facecolor(BEST_COLOR)
                patch.set_hatch(BEST_HATCH)
                patch.set_edgecolor(BEST_EDGECOLOR)
                patch.set_linewidth(1.5)


def scatter_overlay_best(
    ax: plt.Axes,
    df_best: pd.DataFrame,
    x: str,
    y: str,
    label: str = "★ Best approaches",
) -> None:
    """Overlay star markers for best approaches on an existing scatter axes."""
    valid = df_best[[x, y]].dropna()
    if valid.empty:
        return
    ax.scatter(
        valid[x], valid[y],
        marker=BEST_MARKER, s=BEST_MARKERSIZE,
        color=BEST_COLOR, edgecolors=BEST_EDGECOLOR,
        linewidths=0.7, alpha=BEST_ALPHA,
        zorder=10, label=label,
    )
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, loc="best", framealpha=0.7, fontsize=FONT_LEGEND)
'''

# ── A1: r² barplot by method × covariate ─────────────────────────────────────
A1_SOURCE = '''\
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
'''

# ── A2: PCR barplot by method × covariate ────────────────────────────────────
A2_SOURCE = '''\
pcr_cols_main = [
    "pcr_COHORT_LABEL",
    "pcr_Diagnosis_cell_type_unified",
    "pcr_RNA_BATCH",
]
pcr_cols_present = [c for c in pcr_cols_main if c in df_ok.columns]
method_order_pcr = (
    df_ok.groupby("method")["pcr_RNA_BATCH"].mean().sort_values().index.tolist()
)[::-1]

pcr_pal_covar = {col: annot_pal.get(col[4:], "#AAAAAA") for col in pcr_cols_main}
df_long_pcr = df_ok[["method"] + pcr_cols_present].melt(
    id_vars="method", var_name="covariate", value_name="pcr"
)
# v3: append "★ Best" virtual group
df_best_pcr = df_best[["method"] + pcr_cols_present].copy()
df_best_pcr["method"] = BEST_LABEL
df_long_pcr = pd.concat(
    [df_long_pcr,
     df_best_pcr.melt(id_vars="method", var_name="covariate", value_name="pcr")],
    ignore_index=True,
)
method_order_pcr_v3 = list(method_order_pcr) + [BEST_LABEL]

ax = bar_plot(
    df_long_pcr,
    x="method",
    y="pcr",
    hue="covariate",
    palette=pcr_pal_covar,
    order=method_order_pcr_v3,
    figsize=(14, 5),
    ylabel="PCR²",
    title="PCR² per covariate × method (sorted by pcr_RNA_BATCH) — ★ Best = manually selected",
    legend_outside=True,
    xtick_rotation=90,
)
style_best_bars(ax, method_order_pcr_v3)
ax.get_figure().savefig(FIGURES_DIR / "pcr_by_method_covariate.svg", bbox_inches="tight")
ax.get_figure().savefig(FIGURES_DIR / "pcr_by_method_covariate.png", bbox_inches="tight", dpi=200)
plt.show()
'''

# ── A3: PCR barplot by strat × covariate ─────────────────────────────────────
A3_SOURCE = '''\
pcr_cols_main_s = [
    "pcr_COHORT_LABEL",
    "pcr_Diagnosis_cell_type_unified",
    "pcr_RNA_BATCH",
    "pcr_RNASEQ_SOURCE",
]
pcr_cols_present_s = [c for c in pcr_cols_main_s if c in df_ok.columns]
strat_order_pcr = (
    df_ok.groupby("strat")["pcr_RNA_BATCH"].mean().sort_values().index.tolist()
)[::-1]

pcr_pal_covar_s = {col: annot_pal.get(col[4:], "#AAAAAA") for col in pcr_cols_main_s}
df_long_pcr_s = df_ok[["strat"] + pcr_cols_present_s].melt(
    id_vars="strat", var_name="covariate", value_name="pcr"
)
# v3: append "★ Best" virtual group
df_best_pcr_s = df_best[["strat"] + pcr_cols_present_s].copy()
df_best_pcr_s["strat"] = BEST_LABEL
df_long_pcr_s = pd.concat(
    [df_long_pcr_s,
     df_best_pcr_s.melt(id_vars="strat", var_name="covariate", value_name="pcr")],
    ignore_index=True,
)
strat_order_pcr_v3 = list(strat_order_pcr) + [BEST_LABEL]

ax = bar_plot(
    df_long_pcr_s,
    x="strat",
    y="pcr",
    hue="covariate",
    palette=pcr_pal_covar_s,
    order=strat_order_pcr_v3,
    figsize=(14, 5),
    ylabel="PCR²",
    title="PCR² per covariate × strategy (sorted by pcr_RNA_BATCH) — ★ Best = manually selected",
    legend_outside=True,
    xtick_rotation=90,
)
ax.axhline(0.20, color="red", linestyle="--", linewidth=1.0, label="Target=0.20")
style_best_bars(ax, strat_order_pcr_v3)
ax.get_figure().savefig(FIGURES_DIR / "pcr_by_strat_covariate.svg", bbox_inches="tight")
ax.get_figure().savefig(FIGURES_DIR / "pcr_by_strat_covariate.png", bbox_inches="tight", dpi=200)
plt.show()
'''

# ── A4: r² catplot x=method, col=imp ─────────────────────────────────────────
A4_SOURCE = '''\
method_order = (
    df_ok.groupby("method")["r2_RNA_BATCH"].mean().sort_values().index.tolist()
)
# v3: append "★ Best" virtual group
df_best_tagged = df_best.copy()
df_best_tagged["method"] = BEST_LABEL
data_v3 = pd.concat([df_ok, df_best_tagged], ignore_index=True)
method_order_v3 = method_order + [BEST_LABEL]

g = sns.catplot(
    data=data_v3,
    x="method",
    y="r2_RNA_BATCH",
    col="imp",
    kind="box",
    height=4,
    aspect=1.4,
    order=method_order_v3,
    palette=method_pal,
)
g.set_xticklabels(rotation=45, ha="right", fontsize=FONT_SMALL)
g.set_titles("{col_name}", size=FONT_TITLE)
g.set_axis_labels("Method", "r² RNA_BATCH", fontsize=FONT_LABEL)
g.figure.suptitle(
    "r² RNA_BATCH by method × imputation — ★ Best = manually selected",
    y=1.02, fontsize=FONT_TITLE
)
style_best_boxes(g, method_order_v3)
g.figure.savefig(FIGURES_DIR / "a_r2_catplot_by_imp.svg", bbox_inches="tight")
g.figure.savefig(FIGURES_DIR / "a_r2_catplot_by_imp.png", bbox_inches="tight", dpi=200)
plt.show()
'''

# ── A5: PCR catplot x=method, col=imp ────────────────────────────────────────
A5_SOURCE = '''\
method_order = (
    df_ok.groupby("method")["pcr_RNA_BATCH"].mean().sort_values().index.tolist()
)
# v3: append "★ Best" virtual group
df_best_tagged = df_best.copy()
df_best_tagged["method"] = BEST_LABEL
data_v3 = pd.concat([df_ok, df_best_tagged], ignore_index=True)
method_order_v3 = method_order + [BEST_LABEL]

g = sns.catplot(
    data=data_v3,
    x="method",
    y="pcr_RNA_BATCH",
    col="imp",
    kind="box",
    height=4,
    aspect=1.8,
    order=method_order_v3,
    palette=method_pal,
)
g.set_xticklabels(rotation=90, ha="right", fontsize=FONT_SMALL)
g.set_titles("{col_name}", size=FONT_TITLE)
g.set_axis_labels("Method", "PCR RNA_BATCH", fontsize=FONT_LABEL)
g.figure.suptitle(
    "PCR RNA_BATCH by method × imputation — ★ Best = manually selected",
    y=1.02, fontsize=FONT_TITLE
)
style_best_boxes(g, method_order_v3)
g.figure.savefig(FIGURES_DIR / "a_pcr_catplot_by_imp.svg", bbox_inches="tight")
g.figure.savefig(FIGURES_DIR / "a_pcr_catplot_by_imp.png", bbox_inches="tight", dpi=200)
plt.show()
'''

# ── A6: PCR catplot x=method, col=strat ──────────────────────────────────────
A6_SOURCE = '''\
method_order = (
    df_ok.groupby("method")["pcr_RNA_BATCH"].mean().sort_values().index.tolist()
)
# v3: append "★ Best" virtual group
df_best_tagged = df_best.copy()
df_best_tagged["method"] = BEST_LABEL
data_v3 = pd.concat([df_ok, df_best_tagged], ignore_index=True)
method_order_v3 = method_order + [BEST_LABEL]

g = sns.catplot(
    data=data_v3,
    x="method",
    y="pcr_RNA_BATCH",
    col="strat",
    kind="box",
    height=4,
    aspect=1.4,
    col_wrap=4,
    order=method_order_v3,
    palette=method_pal,
)
g.set_xticklabels(rotation=45, ha="right", fontsize=FONT_SMALL)
g.set_titles("{col_name}", size=FONT_TITLE)
g.set_axis_labels("Method", "PCR RNA_BATCH", fontsize=FONT_LABEL)
g.figure.suptitle(
    "PCR RNA_BATCH by method × batch removal strategy — ★ Best = manually selected",
    y=1.02, fontsize=FONT_TITLE
)
style_best_boxes(g, method_order_v3)
g.figure.savefig(FIGURES_DIR / "a_pcr_catplot_by_strat.svg", bbox_inches="tight")
g.figure.savefig(
    FIGURES_DIR / "a_pcr_catplot_by_strat.png", bbox_inches="tight", dpi=200
)
plt.show()
'''

# ── A7: PCR catplot x=method, col=post_rm ────────────────────────────────────
A7_SOURCE = '''\
method_order = (
    df_ok.groupby("method")["pcr_RNA_BATCH"].mean().sort_values().index.tolist()
)
# v3: append "★ Best" virtual group
df_best_tagged = df_best.copy()
df_best_tagged["method"] = BEST_LABEL
data_v3 = pd.concat([df_ok, df_best_tagged], ignore_index=True)
method_order_v3 = method_order + [BEST_LABEL]

g = sns.catplot(
    data=data_v3,
    x="method",
    y="pcr_RNA_BATCH",
    col="post_rm",
    kind="box",
    height=4,
    aspect=2,
    order=method_order_v3,
    palette=method_pal,
)
g.set_xticklabels(rotation=90, ha="right", fontsize=FONT_SMALL)
g.set_titles("{col_name}", size=FONT_TITLE)
g.set_axis_labels("Method", "PCR RNA_BATCH", fontsize=FONT_LABEL)
g.figure.suptitle(
    "PCR RNA_BATCH by method × post_rm — ★ Best = manually selected",
    y=1.02, fontsize=FONT_TITLE
)
style_best_boxes(g, method_order_v3)
g.figure.savefig(FIGURES_DIR / "a_pcr_catplot_by_post_rm.svg", bbox_inches="tight")
g.figure.savefig(
    FIGURES_DIR / "a_pcr_catplot_by_post_rm.png", bbox_inches="tight", dpi=200
)
plt.show()
'''

# ── A8: DSC barplot by method × covariate (log scale + harshness rects) ──────
A8_SOURCE = '''\
import matplotlib.patches as patches

cols_main = [
    "dsc_COHORT_LABEL",
    "dsc_PLATFORM_RNA",
    "dsc_RNASEQ_SOURCE",
    "dsc_RNA_BATCH",
]
cols_present = [c for c in cols_main if c in df_ok.columns]
method_order_dsc = (
    df_ok.groupby("method")["dsc_RNA_BATCH"].mean().sort_values().index.tolist()
)
pal_covar = {col: annot_pal.get(col[4:], "#AAAAAA") for col in cols_main}

df_long_dsc = df_ok[["method"] + cols_present].melt(
    id_vars="method", var_name="covariate", value_name="dsc"
)
# v3: append "★ Best" virtual group
df_best_dsc = df_best[["method"] + cols_present].copy()
df_best_dsc["method"] = BEST_LABEL
df_long_dsc = pd.concat(
    [df_long_dsc,
     df_best_dsc.melt(id_vars="method", var_name="covariate", value_name="dsc")],
    ignore_index=True,
)
method_order_dsc_v3 = method_order_dsc + [BEST_LABEL]

ax = bar_plot(
    df_long_dsc,
    x="method",
    y="dsc",
    hue="covariate",
    palette=pal_covar,
    order=method_order_dsc_v3,
    figsize=(20, 5),
    ylabel="Mean DSC",
    title="Mean DSC per covariate × method (sorted by dsc_COHORT_LABEL) — ★ Best = manually selected",
    legend_outside=True,
    xtick_rotation=90,
)
ax.set_yscale("log")
# Apply best styling after log scale (h * 1.05 works in log space)
style_best_bars(ax, method_order_dsc_v3)

trans = ax.get_xaxis_transform()
# Harshness rectangles — skip "★ Best" (last entry)
for i, method in enumerate(method_order_dsc_v3[:-1]):
    color = method_harshness_pal.get(method, "black")
    rect = patches.Rectangle(
        (i - 0.5, -0.06),
        width=1,
        height=0.04,
        transform=trans,
        clip_on=False,
        facecolor=color,
        edgecolor="none",
    )
    ax.add_patch(rect)
ax.tick_params(axis="x", pad=15)

ax.get_figure().savefig(FIGURES_DIR / "a_dsc_by_method_covariate.svg", bbox_inches="tight")
ax.get_figure().savefig(FIGURES_DIR / "a_dsc_by_method_covariate.png", bbox_inches="tight", dpi=200)
plt.show()
'''

# ── A9: DSC barplot by strat × covariate (log scale) ────────────────────────
A9_SOURCE = '''\
cols_main = [
    "dsc_COHORT_LABEL",
    "dsc_PLATFORM_RNA",
    "dsc_RNASEQ_SOURCE",
    "dsc_RNA_BATCH",
]
cols_present = [c for c in cols_main if c in df_ok.columns]
strat_order_dsc = (
    df_ok.groupby("strat")["dsc_RNA_BATCH"].mean().sort_values().index.tolist()
)
pal_covar = {col: annot_pal.get(col[4:], "#AAAAAA") for col in cols_main}

df_long_dsc = df_ok[["strat"] + cols_present].melt(
    id_vars="strat", var_name="covariate", value_name="dsc"
)
# v3: append "★ Best" virtual group
df_best_dsc = df_best[["strat"] + cols_present].copy()
df_best_dsc["strat"] = BEST_LABEL
df_long_dsc = pd.concat(
    [df_long_dsc,
     df_best_dsc.melt(id_vars="strat", var_name="covariate", value_name="dsc")],
    ignore_index=True,
)
strat_order_dsc_v3 = strat_order_dsc + [BEST_LABEL]

ax = bar_plot(
    df_long_dsc,
    x="strat",
    y="dsc",
    hue="covariate",
    palette=pal_covar,
    order=strat_order_dsc_v3,
    figsize=(8, 5),
    ylabel="Mean DSC",
    title="Mean DSC per covariate × strat (sorted by dsc_COHORT_LABEL) — ★ Best = manually selected",
    legend_outside=True,
    xtick_rotation=90,
)
ax.set_yscale("log")
style_best_bars(ax, strat_order_dsc_v3)

ax.get_figure().savefig(FIGURES_DIR / "a_dsc_by_strat_covariate.svg", bbox_inches="tight")
ax.get_figure().savefig(FIGURES_DIR / "a_dsc_by_strat_covariate.png", bbox_inches="tight", dpi=200)
plt.show()
'''

# ── B1: kBET vs iLISI scatter ────────────────────────────────────────────────
B1_SOURCE = '''\
kbet_col = "kbet_acceptance_rate_RNA_BATCH"
ilisi_col = "ilisi_norm_RNA_BATCH"
if kbet_col in df_ok.columns and ilisi_col in df_ok.columns:
    method_order_b = (
        df_ok.groupby("method")[kbet_col]
        .mean()
        .sort_values(ascending=False)
        .index.tolist()
    )
    ax = scatter_plot(
        df_ok,
        x=kbet_col,
        y=ilisi_col,
        hue="method",
        style="imp",
        palette=method_pal,
        hue_order=method_order_b,
        alpha=0.75,
        s=35,
        figsize=(10, 7),
        xlabel="kBET acceptance rate RNA_BATCH (↑ better)",
        ylabel="iLISI norm RNA_BATCH (↑ better)",
        title="kBET vs iLISI — color=method, style=imputation — ★ = best approaches",
        legend_outside=True,
    )
    # v3: overlay best approaches as stars on same axes
    scatter_overlay_best(ax, df_best, x=kbet_col, y=ilisi_col)
    ax.get_figure().savefig(FIGURES_DIR / "b_kbet_ilisi_scatter.svg", bbox_inches="tight")
    ax.get_figure().savefig(FIGURES_DIR / "b_kbet_ilisi_scatter.png", bbox_inches="tight", dpi=200)
    plt.show()
'''

# ── B2: kBET barplot by method × covariate ───────────────────────────────────
B2_SOURCE = '''\
kbet_cols_main = [
    "kbet_acceptance_rate_RNA_BATCH",
    "kbet_acceptance_rate_COHORT_LABEL",
    "kbet_acceptance_rate_PLATFORM_RNA",
]
kbet_cols_present = [c for c in kbet_cols_main if c in df_ok.columns]
method_order_kbet = (
    df_ok.groupby("method")["kbet_acceptance_rate_RNA_BATCH"]
    .mean()
    .sort_values()
    .index.tolist()
    if "kbet_acceptance_rate_RNA_BATCH" in df_ok.columns
    else method_order
)
kbet_pal_covar = {col: annot_pal.get(col[21:], "#AAAAAA") for col in kbet_cols_main}
df_long_kbet = df_ok[["method"] + kbet_cols_present].melt(
    id_vars="method", var_name="covariate", value_name="kbet"
)
# v3: append "★ Best" virtual group
df_best_kbet = df_best[["method"] + kbet_cols_present].copy()
df_best_kbet["method"] = BEST_LABEL
df_long_kbet = pd.concat(
    [df_long_kbet,
     df_best_kbet.melt(id_vars="method", var_name="covariate", value_name="kbet")],
    ignore_index=True,
)
method_order_kbet_v3 = method_order_kbet + [BEST_LABEL]

ax = bar_plot(
    df_long_kbet,
    x="method",
    y="kbet",
    hue="covariate",
    palette=kbet_pal_covar,
    order=method_order_kbet_v3,
    figsize=(14, 5),
    ylabel="kBET acceptance rate",
    title="kBET acceptance rate per covariate × method — ★ Best = manually selected",
    legend_outside=True,
)
ax.set_xticklabels(ax.get_xticklabels(), rotation=90, ha="right")
style_best_bars(ax, method_order_kbet_v3)
ax.get_figure().savefig(FIGURES_DIR / "kbet_by_method_covariate.svg", bbox_inches="tight")
ax.get_figure().savefig(FIGURES_DIR / "kbet_by_method_covariate.png", bbox_inches="tight", dpi=200)
plt.show()
'''

# ── B3: kBET barplot by strat × covariate (log scale) ────────────────────────
B3_SOURCE = '''\
kbet_cols_main = [
    "kbet_acceptance_rate_RNA_BATCH",
    "kbet_acceptance_rate_COHORT_LABEL",
    "kbet_acceptance_rate_PLATFORM_RNA",
]
kbet_cols_present = [c for c in kbet_cols_main if c in df_ok.columns]
strat_order_kbet = (
    df_ok.groupby("strat")["kbet_acceptance_rate_RNA_BATCH"]
    .mean()
    .sort_values()
    .index.tolist()
    if "kbet_acceptance_rate_RNA_BATCH" in df_ok.columns
    else method_order
)
kbet_pal_covar = {col: annot_pal.get(col[21:], "#AAAAAA") for col in kbet_cols_main}
df_long_kbet = df_ok[["strat"] + kbet_cols_present].melt(
    id_vars="strat", var_name="covariate", value_name="kbet"
)
# v3: append "★ Best" virtual group
df_best_kbet = df_best[["strat"] + kbet_cols_present].copy()
df_best_kbet["strat"] = BEST_LABEL
df_long_kbet = pd.concat(
    [df_long_kbet,
     df_best_kbet.melt(id_vars="strat", var_name="covariate", value_name="kbet")],
    ignore_index=True,
)
strat_order_kbet_v3 = strat_order_kbet + [BEST_LABEL]

ax = bar_plot(
    df_long_kbet,
    x="strat",
    y="kbet",
    hue="covariate",
    palette=kbet_pal_covar,
    order=strat_order_kbet_v3,
    figsize=(14, 5),
    ylabel="kBET acceptance rate",
    title="kBET acceptance rate per covariate × strat — ★ Best = manually selected",
    legend_outside=True,
)
ax.set_yscale("log")
style_best_bars(ax, strat_order_kbet_v3)
ax.set_xticklabels(ax.get_xticklabels(), rotation=90, ha="right")
ax.get_figure().savefig(FIGURES_DIR / "kbet_by_strat_covariate.svg", bbox_inches="tight")
ax.get_figure().savefig(FIGURES_DIR / "kbet_by_strat_covariate.png", bbox_inches="tight", dpi=200)
plt.show()
'''

# ── B4: LISI barplot by method × covariate ───────────────────────────────────
B4_SOURCE = '''\
lisi_cols_main = [
    "clisi_mean_Diagnosis_cell_type_unified",
    "clisi_mean_TUMOR_NORMAL",
    "ilisi_mean_PLATFORM_RNA",
    "ilisi_mean_RNA_BATCH",
]
lisi_cols_present = [c for c in lisi_cols_main if c in df_ok.columns]
method_order_kbet = (
    df_ok.groupby("method")["ilisi_mean_RNA_BATCH"].mean().sort_values().index.tolist()
    if "ilisi_mean_RNA_BATCH" in df_ok.columns
    else method_order
)
lisi_pal_covar = {col: annot_pal.get(col[11:], "#AAAAAA") for col in lisi_cols_main}
df_long_kbet = df_ok[["method"] + lisi_cols_present].melt(
    id_vars="method", var_name="covariate", value_name="LISI"
)
# v3: append "★ Best" virtual group
df_best_lisi = df_best[["method"] + lisi_cols_present].copy()
df_best_lisi["method"] = BEST_LABEL
df_long_kbet = pd.concat(
    [df_long_kbet,
     df_best_lisi.melt(id_vars="method", var_name="covariate", value_name="LISI")],
    ignore_index=True,
)
method_order_kbet_v3 = method_order_kbet + [BEST_LABEL]

ax = bar_plot(
    df_long_kbet,
    x="method",
    y="LISI",
    hue="covariate",
    palette=lisi_pal_covar,
    order=method_order_kbet_v3,
    figsize=(14, 5),
    ylabel="LISI",
    title="LISI per covariate × method — ★ Best = manually selected",
    legend_outside=True,
)
ax.set_xticklabels(ax.get_xticklabels(), rotation=90, ha="right")
style_best_bars(ax, method_order_kbet_v3)
ax.get_figure().savefig(FIGURES_DIR / "lisi_by_method_covariate.svg", bbox_inches="tight")
ax.get_figure().savefig(FIGURES_DIR / "lisi_by_method_covariate.png", bbox_inches="tight", dpi=200)
plt.show()
'''

# ── B5: LISI barplot by strat × covariate ────────────────────────────────────
B5_SOURCE = '''\
lisi_cols_main = [
    "clisi_mean_Diagnosis_cell_type_unified",
    "clisi_mean_TUMOR_NORMAL",
    "ilisi_mean_PLATFORM_RNA",
    "ilisi_mean_RNA_BATCH",
]
lisi_cols_present = [c for c in lisi_cols_main if c in df_ok.columns]
method_order_kbet = (
    df_ok.groupby("strat")["ilisi_mean_RNA_BATCH"].mean().sort_values().index.tolist()
)
lisi_pal_covar = {col: annot_pal.get(col[11:], "#AAAAAA") for col in lisi_cols_main}
df_long_kbet = df_ok[["strat"] + lisi_cols_present].melt(
    id_vars="strat", var_name="covariate", value_name="LISI"
)
# v3: append "★ Best" virtual group
df_best_lisi = df_best[["strat"] + lisi_cols_present].copy()
df_best_lisi["strat"] = BEST_LABEL
df_long_kbet = pd.concat(
    [df_long_kbet,
     df_best_lisi.melt(id_vars="strat", var_name="covariate", value_name="LISI")],
    ignore_index=True,
)
strat_order_lisi_v3 = method_order_kbet + [BEST_LABEL]

ax = bar_plot(
    df_long_kbet,
    x="strat",
    y="LISI",
    hue="covariate",
    palette=lisi_pal_covar,
    order=strat_order_lisi_v3,
    figsize=(14, 5),
    ylabel="LISI",
    title="LISI per covariate × strat — ★ Best = manually selected",
    legend_outside=True,
)
ax.set_xticklabels(ax.get_xticklabels(), rotation=90, ha="right")
style_best_bars(ax, strat_order_lisi_v3)
ax.get_figure().savefig(FIGURES_DIR / "lisi_by_strat_covariate.svg", bbox_inches="tight")
ax.get_figure().savefig(FIGURES_DIR / "lisi_by_strat_covariate.png", bbox_inches="tight", dpi=200)
plt.show()
'''

# ── B6: kBET catplot x=method, col=imp ───────────────────────────────────────
B6_SOURCE = '''\
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
g.figure.savefig(
    FIGURES_DIR / "a_kbet_catplot_by_imp.png", bbox_inches="tight", dpi=200
)
plt.show()
'''

# ── B7: kBET catplot x=method, col=strat ─────────────────────────────────────
B7_SOURCE = '''\
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
    col="strat",
    kind="box",
    height=4,
    aspect=1.5,
    col_wrap=4,
    order=method_order_v3,
    palette=method_pal,
)
g.set_xticklabels(rotation=45, ha="right", fontsize=FONT_SMALL)
g.set_titles("{col_name}", size=FONT_TITLE)
g.set_axis_labels("Method", "kBET RNA_BATCH", fontsize=FONT_LABEL)
g.figure.suptitle(
    "kBET RNA_BATCH by method × strat — ★ Best = manually selected",
    y=1.02, fontsize=FONT_TITLE
)
style_best_boxes(g, method_order_v3)
g.figure.savefig(FIGURES_DIR / "a_kbet_catplot_by_strat.svg", bbox_inches="tight")
g.figure.savefig(
    FIGURES_DIR / "a_kbet_catplot_by_strat.png", bbox_inches="tight", dpi=200
)
plt.show()
'''

# ── B8: kBET catplot x=strat, col=imp ────────────────────────────────────────
B8_SOURCE = '''\
strat_order = (
    df_ok.groupby("strat")["kbet_acceptance_rate_RNA_BATCH"]
    .mean()
    .sort_values()
    .index.tolist()
)
# v3: append "★ Best" virtual group (group_col = strat)
df_best_tagged = df_best.copy()
df_best_tagged["strat"] = BEST_LABEL
data_v3 = pd.concat([df_ok, df_best_tagged], ignore_index=True)
strat_order_v3 = strat_order + [BEST_LABEL]

g = sns.catplot(
    data=data_v3,
    x="strat",
    y="kbet_acceptance_rate_RNA_BATCH",
    col="imp",
    kind="box",
    height=4,
    aspect=1.5,
    order=strat_order_v3,
    palette=strat_pal,
)
g.set_xticklabels(rotation=45, ha="right", fontsize=FONT_SMALL)
g.set_titles("{col_name}", size=FONT_TITLE)
g.set_axis_labels("Strategy", "kBET RNA_BATCH", fontsize=FONT_LABEL)
g.figure.suptitle(
    "kBET RNA_BATCH by strat × imputation — ★ Best = manually selected",
    y=1.02, fontsize=FONT_TITLE
)
style_best_boxes(g, strat_order_v3)
g.figure.savefig(FIGURES_DIR / "a_kbet_catplot_by_imp_strat.svg", bbox_inches="tight")
g.figure.savefig(
    FIGURES_DIR / "a_kbet_catplot_by_imp_strat.png", bbox_inches="tight", dpi=200
)
plt.show()
'''

# ── B9: iLISI catplot x=method, col=imp (excludes 34_arsyn, 38_harman) ───────
B9_SOURCE = '''\
data_to_show = df_ok[~df_ok.method.isin(["34_arsyn", "38_harman"])]
# df_best does not contain 34_arsyn or 38_harman, so no extra filter needed
method_order = (
    data_to_show.groupby("method")["ilisi_mean_RNA_BATCH"]
    .mean()
    .sort_values()
    .index.tolist()
)
# v3: append "★ Best" virtual group
df_best_tagged = df_best.copy()
df_best_tagged["method"] = BEST_LABEL
data_v3 = pd.concat([data_to_show, df_best_tagged], ignore_index=True)
method_order_v3 = method_order + [BEST_LABEL]

g = sns.catplot(
    data=data_v3,
    x="method",
    y="ilisi_mean_RNA_BATCH",
    col="imp",
    kind="box",
    height=4,
    aspect=1.5,
    order=method_order_v3,
    palette=method_pal,
)
g.set_xticklabels(rotation=45, ha="right", fontsize=FONT_SMALL)
g.set_titles("{col_name}", size=FONT_TITLE)
g.set_axis_labels("Method", "ilisi RNA_BATCH", fontsize=FONT_LABEL)
g.figure.suptitle(
    "ilisi RNA_BATCH by method × imputation — ★ Best = manually selected",
    y=1.02, fontsize=FONT_TITLE
)
style_best_boxes(g, method_order_v3)
g.figure.savefig(FIGURES_DIR / "a_ilisi_catplot_by_imp.svg", bbox_inches="tight")
g.figure.savefig(
    FIGURES_DIR / "a_ilisi_catplot_by_imp.png", bbox_inches="tight", dpi=200
)
plt.show()
'''

# ── B10: iLISI catplot x=method, col=strat ───────────────────────────────────
B10_SOURCE = '''\
method_order = (
    df_ok.groupby("method")["ilisi_mean_RNA_BATCH"].mean().sort_values().index.tolist()
)
# v3: append "★ Best" virtual group
df_best_tagged = df_best.copy()
df_best_tagged["method"] = BEST_LABEL
data_v3 = pd.concat([df_ok, df_best_tagged], ignore_index=True)
method_order_v3 = method_order + [BEST_LABEL]

g = sns.catplot(
    data=data_v3,
    x="method",
    y="ilisi_mean_RNA_BATCH",
    col="strat",
    kind="box",
    height=4,
    aspect=1.5,
    col_wrap=4,
    order=method_order_v3,
    palette=method_pal,
)
g.set_xticklabels(rotation=45, ha="right", fontsize=FONT_SMALL)
g.set_titles("{col_name}", size=FONT_TITLE)
g.set_axis_labels("Method", "iLISI RNA_BATCH", fontsize=FONT_LABEL)
g.figure.suptitle(
    "iLISI RNA_BATCH by method × strat — ★ Best = manually selected",
    y=1.02, fontsize=FONT_TITLE
)
style_best_boxes(g, method_order_v3)
g.figure.savefig(FIGURES_DIR / "b_isisi_catplot_by_strat.svg", bbox_inches="tight")
g.figure.savefig(
    FIGURES_DIR / "b_lisi_catplot_by_strat.png", bbox_inches="tight", dpi=200
)
plt.show()
'''

# ── B11: iLISI catplot x=strat, col=imp (excludes 34_arsyn, 38_harman) ───────
B11_SOURCE = '''\
data_to_show = df_ok[~df_ok.method.isin(["34_arsyn", "38_harman"])]
strat_order = (
    data_to_show.groupby("strat")["ilisi_mean_RNA_BATCH"]
    .mean()
    .sort_values()
    .index.tolist()
)
# v3: append "★ Best" virtual group (group_col = strat)
df_best_tagged = df_best.copy()
df_best_tagged["strat"] = BEST_LABEL
data_v3 = pd.concat([data_to_show, df_best_tagged], ignore_index=True)
strat_order_v3 = strat_order + [BEST_LABEL]

g = sns.catplot(
    data=data_v3,
    x="strat",
    y="ilisi_mean_RNA_BATCH",
    col="imp",
    kind="box",
    height=4,
    aspect=1.5,
    order=strat_order_v3,
    palette=strat_pal,
)
g.set_xticklabels(rotation=45, ha="right", fontsize=FONT_SMALL)
g.set_titles("{col_name}", size=FONT_TITLE)
g.set_axis_labels("Strategy", "ilisi RNA_BATCH", fontsize=FONT_LABEL)
g.figure.suptitle(
    "ilisi RNA_BATCH by strat × imputation — ★ Best = manually selected",
    y=1.02, fontsize=FONT_TITLE
)
style_best_boxes(g, strat_order_v3)
g.figure.savefig(FIGURES_DIR / "a_ilisi_catplot_by_imp_strat.svg", bbox_inches="tight")
g.figure.savefig(
    FIGURES_DIR / "a_ilisi_catplot_by_imp_strat.png", bbox_inches="tight", dpi=200
)
plt.show()
'''

# ── I1: WaterMelon batch-biology tradeoff scatter ────────────────────────────
I1_SOURCE = '''\
if WM_AVAIL and "wm_mean_batch" in df_ok.columns and "wm_mean_bio" in df_ok.columns:
    # §3.11.4 — WM batch-biology tradeoff
    ax = scatter_plot(
        df_ok,
        x="wm_mean_batch",
        y="wm_mean_bio",
        hue="method",
        style="strat" if df_ok["strat"].nunique() <= 12 else None,
        palette=method_pal,
        alpha=0.65,
        s=30,
        figsize=(9, 6),
        xlabel="WM batch score (↓ better mixing)",
        ylabel="WM biology score (↑ biology preserved)",
        title="WaterMelon: batch-biology tradeoff — ★ = best approaches",
        legend_outside=True,
    )
    lims = [
        min(ax.get_xlim()[0], ax.get_ylim()[0]),
        max(ax.get_xlim()[1], ax.get_ylim()[1]),
    ]
    ax.plot(lims, lims, "k--", linewidth=0.7, alpha=0.5, label="diagonal")
    # v3: overlay best approaches as stars on same axes
    scatter_overlay_best(ax, df_best, x="wm_mean_batch", y="wm_mean_bio")
    ax.get_figure().savefig(FIGURES_DIR / "i_wm_batch_bio_tradeoff.svg", bbox_inches="tight")
    ax.get_figure().savefig(FIGURES_DIR / "i_wm_batch_bio_tradeoff.png", bbox_inches="tight", dpi=200)
    plt.show()
'''

# ── I2: WaterMelon ratio vs composite score scatter ──────────────────────────
I2_SOURCE = '''\
if (
    WM_AVAIL
    and "wm_ratio_bio_batch" in df_ok.columns
    and "composite_score" in df_ok.columns
):
    # §3.11.5 — wm_ratio vs composite score
    ax = scatter_plot(
        df_ok,
        x="composite_score",
        y="wm_ratio_bio_batch",
        hue="method",
        palette=method_pal,
        alpha=0.65,
        s=25,
        figsize=(8, 6),
        xlabel="Composite score (Groups A–H, K)",
        ylabel="WM ratio bio/batch",
        title="WaterMelon ratio vs composite score — ★ = best approaches",
        legend_outside=True,
    )
    plot_df = df_ok[["composite_score", "wm_ratio_bio_batch"]].dropna()
    if len(plot_df) >= 3:
        r, p = pearsonr(plot_df["composite_score"], plot_df["wm_ratio_bio_batch"])
        ax.set_title(
            f"WM ratio vs composite — r={r:.2f}, p={p:.3f} — ★ = best approaches",
            fontsize=FONT_TITLE,
        )
    # v3: overlay best approaches as stars on same axes
    scatter_overlay_best(ax, df_best, x="composite_score", y="wm_ratio_bio_batch")
    ax.get_figure().savefig(FIGURES_DIR / "i_wm_ratio_vs_composite.svg", bbox_inches="tight")
    ax.get_figure().savefig(FIGURES_DIR / "i_wm_ratio_vs_composite.png", bbox_inches="tight", dpi=200)
    plt.show()
'''

# ── K1: Gene completeness horizontal barplot by method ───────────────────────
K1_SOURCE = '''\
if K_AVAIL and "pct_genes_noNA" in df_ok.columns:
    # §3.10.2 — Horizontal bar chart: pct_genes_noNA by method
    method_order_k = (
        df_ok.groupby("method")["pct_genes_noNA"]
        .mean()
        .sort_values(ascending=True)
        .index.tolist()
    )
    df_long_k = df_ok[["method", "imp", "pct_genes_noNA"]].copy()
    # v3: append "★ Best" virtual group
    df_best_k = df_best[["method", "imp", "pct_genes_noNA"]].copy()
    df_best_k["method"] = BEST_LABEL
    df_long_k = pd.concat([df_long_k, df_best_k], ignore_index=True)
    method_order_k_v3 = method_order_k + [BEST_LABEL]

    ax = bar_plot(
        df_long_k,
        x="pct_genes_noNA",
        y="method",
        hue="imp",
        palette=imp_pal,
        order=method_order_k_v3,
        orient="h",
        figsize=(9, max(7, len(method_order_k_v3) * 0.35)),
        xlabel="% genes with no NA",
        ylabel="Method",
        title="Gene completeness by method (pct_genes_noNA) — ★ Best = manually selected",
        legend_outside=True,
    )
    ax.axvline(
        80, color="red", linestyle="--", linewidth=1, alpha=0.7, label="80% threshold"
    )
    style_best_bars(ax, method_order_k_v3, orient="h")
    ax.get_figure().savefig(FIGURES_DIR / "k_pct_genes_nona_by_method.svg", bbox_inches="tight")
    ax.get_figure().savefig(FIGURES_DIR / "k_pct_genes_nona_by_method.png", bbox_inches="tight", dpi=200)
    plt.show()
'''

# ── K2: Gene completeness boxplot by harshness level ────────────────────────
K2_SOURCE = '''\
if K_AVAIL and "pct_genes_noNA" in df_ok.columns:
    # §3.10.4 — Boxplot: pct_genes_noNA by harshness
    harshness_order = ["low", "medium", "high"]
    harshness_order_v3 = harshness_order + [BEST_LABEL]
    HARSHNESS_PAL_V3 = {**HARSHNESS_PAL, BEST_LABEL: BEST_COLOR}

    # v3: append "★ Best" virtual group
    df_best_k2 = df_best.copy()
    df_best_k2["harshness_level"] = BEST_LABEL
    data_k2_v3 = pd.concat([df_ok, df_best_k2], ignore_index=True)

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.boxplot(
        data=data_k2_v3,
        x="harshness_level",
        y="pct_genes_noNA",
        order=harshness_order_v3,
        palette=HARSHNESS_PAL_V3,
        width=0.6,
        showfliers=False,
        ax=ax,
    )
    sns.stripplot(
        data=data_k2_v3,
        x="harshness_level",
        y="pct_genes_noNA",
        order=harshness_order_v3,
        hue="strat",
        palette=strat_pal,
        alpha=0.5,
        s=4,
        ax=ax,
        legend=False,
    )
    # Apply hatch and thick edge to the "★ Best" box (at x-position 3)
    best_x_pos = len(harshness_order)
    for patch in ax.patches:
        if not hasattr(patch, "get_x"):
            continue
        x_center = patch.get_x() + patch.get_width() / 2
        if abs(x_center - best_x_pos) < 0.6:
            patch.set_hatch(BEST_HATCH)
            patch.set_edgecolor(BEST_EDGECOLOR)
            patch.set_linewidth(1.5)

    ax.axhline(
        80, color="red", linestyle="--", linewidth=1, alpha=0.7, label="80% threshold"
    )
    ax.set_xlabel("Harshness level", fontsize=FONT_LABEL)
    ax.set_ylabel("% genes with no NA", fontsize=FONT_LABEL)
    ax.set_title(
        "Gene completeness by normalization harshness — ★ Best = manually selected",
        fontsize=FONT_TITLE,
    )
    ax.tick_params(labelsize=FONT_TICK)
    ax.legend(fontsize=FONT_SMALL)
    sns.despine()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "k_pct_genes_nona_by_harshness.svg", bbox_inches="tight")
    fig.savefig(
        FIGURES_DIR / "k_pct_genes_nona_by_harshness.png", bbox_inches="tight", dpi=200
    )
    plt.show()
'''


# ── Script entrypoint ─────────────────────────────────────────────────────────

def find_idx(cells: list, search: str) -> int:
    """Return index of first cell whose source contains `search`."""
    for i, c in enumerate(cells):
        if search in c.source:
            return i
    raise ValueError(f"Not found in any cell: {search!r}")


def replace_cell(cells: list, search: str, new_source: str) -> None:
    """Replace source of the first cell whose source contains `search`."""
    idx = find_idx(cells, search)
    cells[idx].source = new_source
    print(f"  replaced cell {idx} (matched: {search!r})")


def new_code_cell(source: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_code_cell(source=source)


def main() -> None:
    print(f"Reading {INPUT} …")
    with open(INPUT) as f:
        nb = nbformat.read(f, as_version=4)
    print(f"  {len(nb.cells)} cells loaded")

    # ── Step 1: strip all outputs ────────────────────────────────────────────
    stripped = 0
    for cell in nb.cells:
        if cell.cell_type == "code":
            if cell.get("outputs"):
                stripped += 1
            cell["outputs"] = []
            cell["execution_count"] = None
    print(f"  stripped outputs from {stripped} cells")

    # ── Step 2: insert infra cells ───────────────────────────────────────────
    # Insert B after the scatter_plot / bar_plot helper cell
    helpers_idx = find_idx(nb.cells, "def scatter_plot")
    nb.cells.insert(helpers_idx + 1, new_code_cell(INFRA_B_SOURCE))
    print(f"  inserted INFRA_B after cell {helpers_idx}")

    # Insert A after the df_ok creation cell (indices shifted by 1 after B insert)
    df_ok_idx = find_idx(nb.cells, 'df_ok = df[df["status"] == "ok"]')
    nb.cells.insert(df_ok_idx + 1, new_code_cell(INFRA_A_SOURCE))
    print(f"  inserted INFRA_A after cell {df_ok_idx}")

    # ── Step 3: replace target cells ────────────────────────────────────────
    print("Replacing target cells …")
    replacements = [
        ("a_r2_by_method_covariate",      A1_SOURCE),
        ("pcr_by_method_covariate",        A2_SOURCE),
        ("pcr_by_strat_covariate",         A3_SOURCE),
        ("a_r2_catplot_by_imp.svg",        A4_SOURCE),
        ("a_pcr_catplot_by_imp.svg",       A5_SOURCE),
        ("a_pcr_catplot_by_strat.svg",     A6_SOURCE),
        ("a_pcr_catplot_by_post_rm.svg",   A7_SOURCE),
        ("a_dsc_by_method_covariate",      A8_SOURCE),
        ("a_dsc_by_strat_covariate",       A9_SOURCE),
        ("b_kbet_ilisi_scatter",           B1_SOURCE),
        ("kbet_by_method_covariate",       B2_SOURCE),
        ("kbet_by_strat_covariate",        B3_SOURCE),
        ("lisi_by_method_covariate",       B4_SOURCE),
        ("lisi_by_strat_covariate",        B5_SOURCE),
        ("a_kbet_catplot_by_imp.svg",      B6_SOURCE),
        ("a_kbet_catplot_by_strat.svg",    B7_SOURCE),
        ("a_kbet_catplot_by_imp_strat.svg", B8_SOURCE),
        ("a_ilisi_catplot_by_imp.svg",     B9_SOURCE),
        ("b_isisi_catplot_by_strat.svg",   B10_SOURCE),
        ("a_ilisi_catplot_by_imp_strat.svg", B11_SOURCE),
        ("i_wm_batch_bio_tradeoff",        I1_SOURCE),
        ("i_wm_ratio_vs_composite",        I2_SOURCE),
        ("k_pct_genes_nona_by_method",     K1_SOURCE),
        ("k_pct_genes_nona_by_harshness",  K2_SOURCE),
    ]

    for search, source in replacements:
        try:
            replace_cell(nb.cells, search, source)
        except ValueError as e:
            print(f"  WARNING: {e}")

    # ── Step 4: validate and write ───────────────────────────────────────────
    print("Validating …")
    nbformat.validate(nb)
    with open(OUTPUT, "w") as f:
        nbformat.write(nb, f)

    size_mb = OUTPUT.stat().st_size / 1e6
    print(f"\nWritten: {OUTPUT}  ({size_mb:.1f} MB)")
    print(f"Total cells: {len(nb.cells)}")
    print("Done.")


if __name__ == "__main__":
    main()
