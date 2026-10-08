"""Article 2 figures, revision round 1 (plan Phase 2), 2026-09-25.

Rebuilds every Article 2 figure that Daniil's review ordered changed, each as ONE
composite drawn at the size of the Figma reference frame `637:93145` (756 x 1159 px).
The project convention is 2 px = 1 pt, so a figure is 378 pt wide and at most 579.5 pt
tall, and it drops onto a frame at exactly 2x with nothing to rescale.

    source ~/venvs/collagen_3_11/bin/activate
    cd article_2_extended_comparison
    python figures/article2_figures_260925.py --prepare-expression   # once, reads S3 cache
    python figures/article2_figures_260925.py                        # all figures
    python figures/article2_figures_260925.py --only sfig_harshness

What each comment asked for, and where it lands:

| builder | comment | what changed |
|---|---|---|
| fig_markers_lm | C48, C50 | Figure 4 without the expression grids; A/B coloured by method and strategy |
| fig_prediction_n | C16, C50 | Figure 5 A-D at half size; D redrawn on the E1 index |
| fig_election | C50 | old Figure 5E-G as their own figure, labels no longer overlap |
| sfig_harshness | C44 | Supplementary Figure 12 as a 3 x 4 grid, permutation null, no H |
| sfig_lmn_scatter | C48 | new: L/M/N pairs coloured by method and by strategy, rho and p |
| sfig_metric_clustermap | C48 | new: Spearman clustermap of every recoverable non-metadata metric |
| sfig_expression | C50 | new: raw vs harmonized for 4 linear and 4 non-linear methods, no 01_raw |
| sfig_pca | C35 | new: the per-component PCA heat maps, by method and by strategy |

Numbers printed inside panels (p, rho) are read from the Phase 1 tables
(`tables/A2_T9*`, `A2_T11`) so a panel and the text can never disagree.

Outputs go to `figures/panels_260925/`: `<name>.{pdf,svg,png}` with text, and
`editable/<name>_artwork_300dpi.png` with every text artist hidden, which
`tools/split_figure_text_260925.py` pairs with a Figma-ready text overlay.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors  # noqa: E402
import matplotlib.patheffects as pe  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.text as mtext  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch, PathPatch, Wedge  # noqa: E402
from matplotlib.path import Path as MplPath  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)  # article2_generalizability resolves its inputs relative to this folder
sys.path.insert(0, str(ROOT / "analysis"))
import article2_generalizability as a2  # noqa: E402

STAMP = "260925"
TABLE_STAMP = "260924"
METRICS_PATH = a2.METRICS_CSV.format(tag="260905")
OUT_DIR = ROOT / "figures" / "panels_260925"
EDIT_DIR = OUT_DIR / "editable"
DATA_DIR = OUT_DIR / "data"
# Only prepare_expression() reads it, and only with the full matrices at hand.
EXP_CACHE = Path(os.environ.get("FL_EXP_CACHE", "fl_exp_cache"))

# ── geometry: the reference frame 637:93145 is 756 x 1159 px, 2 px = 1 pt ─────
FRAME_W_PT, FRAME_H_PT = 378.0, 579.5
W_IN, H_MAX_IN = FRAME_W_PT / 72, FRAME_H_PT / 72
PX_PER_PT = 2.0

# At 2 px per pt: 6 pt labels are 12 px and 10 pt letters are 20 px, the Inter Bold
# 20 house style of the Figma file. 5 pt (10 px) is the smallest type used anywhere.
LABEL, TICK, SMALL, LETTER = 6.0, 5.5, 5.0, 10.0
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": LABEL,
        "axes.labelsize": LABEL,
        "axes.titlesize": LABEL,
        "xtick.labelsize": TICK,
        "ytick.labelsize": TICK,
        "legend.fontsize": SMALL,
        "legend.title_fontsize": SMALL,
        "axes.linewidth": 0.5,
        "xtick.major.width": 0.5,
        "ytick.major.width": 0.5,
        "xtick.major.size": 2.0,
        "ytick.major.size": 2.0,
        "xtick.major.pad": 1.5,
        "ytick.major.pad": 1.5,
        "axes.labelpad": 2.0,
        "lines.linewidth": 0.6,
        "patch.linewidth": 0.4,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
        "figure.dpi": 200,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)

# ── palettes: Article 1's, from Finally_assembled_figures_for_article.ipynb cell 4 ─
HARSH_PAL = {"low": "#2DC653", "medium": "#F4A261", "high": "#E63946"}
IMP_PAL = {"strict": "#2979ae", "knn": "#982d22", "softimpute": "#713689"}
STRAT_PAL = {
    "S0_no_removal": (0.631, 0.788, 0.957),
    "A_confirmed_bad": (1.000, 0.706, 0.510),
    "B_extended_bad": (0.553, 0.898, 0.631),
    "C_rnaseq_only": (1.000, 0.624, 0.608),
    "D_malignant_only": (0.816, 0.733, 1.000),
    "E1_iterative_r1": (0.871, 0.733, 0.608),
    "E2_iterative_r2": (0.980, 0.690, 0.894),
    "E3_iterative_r3": (0.812, 0.812, 0.812),
    "F_microarray_only": (1.000, 0.996, 0.639),
    "G_affymetrix_only": (0.725, 0.949, 0.941),
    "H_affymetrix_extended": (0.741, 0.718, 0.420),
    "I_rare_batches_removed": "#b095c5",
    "J_ff_only": "#7ecbc4",
    "K_ffpe_only": "#f2c27f",
}
NULL_COLOR = "#9E9E9E"
STAR = {
    "marker": "*",
    "s": 26,
    "facecolors": "none",
    "edgecolors": "k",
    "linewidths": 0.5,
    "zorder": 6,
}


def _method_palette(methods: list[str]) -> dict:
    """tab20 + tab20b with boosted saturation over the sorted methods (Article 1)."""
    raw = sns.color_palette("tab20", 20) + sns.color_palette("tab20b", 20)
    raw = raw[: max(len(methods), 25)]

    def boost(rgb, delta=0.15):
        h, s, v = mcolors.rgb_to_hsv(np.clip(rgb[:3], 0, 1))
        return tuple(mcolors.hsv_to_rgb([h, min(1.0, s + delta), v]))

    return dict(zip(sorted(methods), [boost(c) for c in raw]))


# ── formatting ────────────────────────────────────────────────────────────────

_SUP = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def fmt_p(p: float) -> str:
    """p in the prose's notation, `p = 1.4 × 10⁻⁹` (C44), in Unicode, not mathtext.

    Unicode superscripts keep each label one string, which the Figma overlay needs:
    mathtext is emitted by matplotlib as one <text> per glyph run.
    """
    if p == 0 or p < 1e-300:
        return "p < 10⁻³⁰⁰"
    if p >= 0.001:
        return f"p = {p:.2g}"
    mant, exp = f"{p:.1e}".split("e")
    return f"p = {mant} × 10{str(int(exp)).translate(_SUP)}"


def fmt_rho(rho: float, p: float) -> str:
    return f"ρ = {rho:.3f}, {fmt_p(p)}"


def short_strat(s: str) -> str:
    return s.replace("_", " ", 1).replace("_", "-")


# ── figure scaffolding ────────────────────────────────────────────────────────


def new_figure(height_pt: float) -> plt.Figure:
    """A figure exactly one frame wide; its height is capped at the frame's."""
    assert height_pt <= FRAME_H_PT + 1e-6, f"{height_pt} pt exceeds the frame"
    return plt.figure(figsize=(W_IN, height_pt / 72))


def axes_pt(fig, x, y, w, h):
    """Axes placed in points from the TOP-left corner, the way Figma measures."""
    fw, fh = fig.get_size_inches() * 72
    return fig.add_axes([x / fw, 1 - (y + h) / fh, w / fw, h / fh])


def letter(fig, x_pt, y_pt, s):
    """Panel letter at a point position from the top-left, Bold 10 pt (20 px)."""
    fw, fh = fig.get_size_inches() * 72
    fig.text(
        x_pt / fw,
        1 - y_pt / fh,
        s,
        fontsize=LETTER,
        fontweight="bold",
        ha="left",
        va="top",
    )


def text_overlaps(fig) -> list[tuple[str, str]]:
    """Pairs of visible text artists whose rendered boxes overlap (C44 gate).

    Boxes are shrunk by one pixel so labels that merely touch are not counted.
    """
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    # Tick labels outside the view interval exist as Text objects but are never drawn,
    # so the candidates are collected axis by axis rather than with findobj().
    texts = list(fig.texts) + [t for lg in fig.legends for t in lg.get_texts()]
    for ax in fig.axes:
        texts += [
            ax.title,
            ax._left_title,
            ax._right_title,
            ax.xaxis.label,
            ax.yaxis.label,
        ] + list(ax.texts)
        if ax.get_legend():
            texts += list(ax.get_legend().get_texts())
        for axis, (lo, hi) in (
            (ax.xaxis, sorted(ax.get_xlim())),
            (ax.yaxis, sorted(ax.get_ylim())),
        ):
            texts += [
                tick.label1
                for tick in axis.get_major_ticks()
                if tick.label1.get_visible()
                and lo - 1e-9 <= tick.get_loc() <= hi + 1e-9
            ]
    boxes = []
    for t in texts:
        if t.get_visible() and t.get_text().strip():
            bb = t.get_window_extent(r)
            if bb.width > 2 and bb.height > 2:
                boxes.append((t.get_text(), bb.padded(-1)))
    hits = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if boxes[i][1].overlaps(boxes[j][1]):
                hits.append((boxes[i][0][:30], boxes[j][0][:30]))
    return hits


REPORT: dict[str, dict] = {}


def save(fig, name: str, panels: dict[str, str]) -> None:
    """Write the figure with text (pdf, svg, png) and a text-free 300 dpi artwork.

    No `bbox_inches="tight"`: the figure must keep the frame's exact size, or the
    text overlay and the artwork stop lining up.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EDIT_DIR.mkdir(parents=True, exist_ok=True)
    overlaps = text_overlaps(fig)
    for ext in ("pdf", "svg"):
        fig.savefig(OUT_DIR / f"{name}.{ext}")
    fig.savefig(OUT_DIR / f"{name}.png", dpi=200)
    for t in fig.findobj(mtext.Text):
        t.set_visible(False)
    fig.savefig(EDIT_DIR / f"{name}_artwork_300dpi.png", dpi=300)
    w_pt, h_pt = fig.get_size_inches() * 72
    REPORT[name] = {
        "size_pt": [round(w_pt, 2), round(h_pt, 2)],
        "size_px": [round(w_pt * PX_PER_PT), round(h_pt * PX_PER_PT)],
        "fits_frame": bool(w_pt <= FRAME_W_PT + 0.01 and h_pt <= FRAME_H_PT + 0.01),
        "panels": panels,
        "n_text_overlaps": len(overlaps),
        "overlaps": overlaps[:10],
    }
    plt.close(fig)
    print(
        f"  {name}: {w_pt:.0f} x {h_pt:.0f} pt, {len(panels)} panels, "
        f"{len(overlaps)} text overlaps"
    )


# ── data ──────────────────────────────────────────────────────────────────────


def load_data() -> dict:
    """The 260924 analysis frame plus the Phase 1 tables the panels quote."""
    df = a2.load_analysis_set(a2.SUPP_FILE_3, METRICS_PATH)
    df = a2.add_raw_deltas(df)
    df, fold_comp = a2.add_fold_metrics(df, a2.FOLDS_CSV)
    folds = a2.load_restricted_folds(df, a2.FOLDS_CSV)
    df = a2.add_twoclass_fold_metrics(df, folds)
    df["generalizability_index"] = a2.generalizability_index(df)
    _, sets = a2.cross_election_matrix(df)
    full = a2.attach_snapshot_columns(df, METRICS_PATH)
    t = lambda n: pd.read_csv(ROOT / "tables" / f"{n}_{TABLE_STAMP}.csv")
    return {
        "df": df,
        "full": full,
        "folds": folds,
        "sets": sets,
        "t9": t("A2_T9_harshness_table1"),
        "t9b": t("A2_T9b_harshness_full"),
        "t11": t("A2_T11_scatter_correlations"),
        "t3b": t("A2_T3b_cross_election_pairs"),
        "t12": t("A2_T12_metric_census"),
        "t13": t("A2_T13_lobo_summary"),
        "method_pal": _method_palette(list(df.method.unique())),
    }


def _rho_row(t11, x, y):
    """rho and p of an (x, y) pair from A2_T11, in either order."""
    r = t11[((t11.x == x) & (t11.y == y)) | ((t11.x == y) & (t11.y == x))]
    r = r[r.subset == "all approaches"].iloc[0]
    return float(r.spearman_rho), float(r.p_value)


def _scatter(ax, d, x, y, color_col, pal, s=3):
    """All approaches as small dots, the clustermap group as hollow black stars."""
    for key, sub in d.groupby(color_col):
        ax.scatter(
            sub[x],
            sub[y],
            s=s,
            color=pal.get(key, "#888888"),
            alpha=0.6,
            linewidths=0,
            rasterized=True,
        )
    best = d[d.is_clustermap_best]
    ax.scatter(best[x], best[y], **STAR)


def _legend_block(ax, pal, title, ncol, marker="o"):
    handles = [
        Line2D([], [], ls="", marker=marker, ms=3.2, color=c, label=k)
        for k, c in pal.items()
    ]
    ax.legend(
        handles=handles,
        title=title,
        ncol=ncol,
        frameon=False,
        loc="upper left",
        handletextpad=0.1,
        columnspacing=0.6,
        labelspacing=0.25,
        borderaxespad=0.0,
    )
    ax.axis("off")


# ══ Figure 4 — classes L and M ═══════════════════════════════════════════════


def fig_markers_lm(D) -> None:
    """Figure 4, the expression grids moved out (C50), A/B coloured two ways (C48).

    A/B margin against marker correlation by method and by strategy; C methods ranked
    by median margin with the clustermap group as its own row; D strategy and
    imputation medians of both class columns; E the agreement-specific plane; F
    same-biology agreement before and after harmonization for the gate-passing
    approaches; plus the shared colour legends.
    """
    df, pal = D["df"], D["method_pal"]
    fig = new_figure(566)
    rho, p = _rho_row(D["t11"], "mk_rho_mean_markers", "xb_margin")
    for i, (col, cpal, lab) in enumerate(
        ((("method"), pal, "A"), ("strat", STRAT_PAL, "B"))
    ):
        ax = axes_pt(fig, 30 + i * 180, 18, 150, 118)
        _scatter(ax, df, "mk_rho_mean_markers", "xb_margin", col, cpal)
        ax.axvline(a2.RHO_GATE, color="k", lw=0.5, ls="--")
        ax.axhline(0, color="k", lw=0.5, ls=":")
        ax.set_xlabel("class L mean marker correlation")
        ax.set_ylabel("class M margin")
        ax.set_title(fmt_rho(rho, p), fontsize=SMALL, pad=2)
        letter(fig, 2 + i * 180, 6, lab)

    # C — methods ranked by median margin, the clustermap group as one more row.
    d = df.assign(row=df.method)
    best = df[df.is_clustermap_best].assign(row="clustermap best")
    stack = pd.concat([d, best], ignore_index=True)
    order = stack.groupby("row").xb_margin.median().sort_values(ascending=False).index
    ax = axes_pt(fig, 78, 170, 102, 232)
    colors = [pal.get(m, "#E63946") for m in order]
    sns.boxplot(
        data=stack,
        y="row",
        x="xb_margin",
        order=order,
        palette=colors,
        orient="h",
        fliersize=0.6,
        linewidth=0.35,
        width=0.7,
        ax=ax,
    )
    ax.axvline(0, color="k", lw=0.4, ls=":")
    ax.set_ylabel("")
    ax.set_xlabel("class M margin")
    ax.tick_params(axis="y", labelsize=SMALL, length=0)
    for tl in ax.get_yticklabels():
        if tl.get_text() == "clustermap best":
            tl.set_fontweight("bold")
    letter(fig, 2, 158, "C")

    # D — strategy and imputation medians, both class columns side by side.
    med = [
        (
            "strategy",
            df.groupby("strat")[["mk_rho_mean_markers", "xb_margin"]]
            .median()
            .rename(index=short_strat),
        ),
        (
            "imputation",
            df.groupby("imp")[["mk_rho_mean_markers", "xb_margin"]].median(),
        ),
    ]
    rows = pd.concat([m for _, m in med])
    kinds = ["strategy"] * len(med[0][1]) + ["imputation"] * len(med[1][1])
    y = np.arange(len(rows))
    for j, (col, xl) in enumerate(
        (("mk_rho_mean_markers", "median marker corr."), ("xb_margin", "median margin"))
    ):
        ax = axes_pt(fig, 262 + j * 60, 170, 50, 122)
        ax.scatter(
            rows[col],
            y,
            s=6,
            c=["#2979ae" if k == "strategy" else "#982d22" for k in kinds],
            linewidths=0,
        )
        ax.set_yticks(y)
        ax.set_yticklabels(rows.index if j == 0 else [], fontsize=SMALL)
        ax.set_ylim(len(rows) - 0.5, -0.5)
        ax.axhline(len(med[0][1]) - 0.5, color="#BBBBBB", lw=0.4)
        ax.set_xlabel(xl, fontsize=SMALL)
        ax.tick_params(axis="x", labelsize=SMALL)
        ax.locator_params(axis="x", nbins=3)
    letter(fig, 196, 158, "D")

    # E — agreement-specific plane.
    spec = a2.agreement_specific(df)
    nonraw = df[~df.is_raw]
    ax = axes_pt(fig, 222, 322, 148, 90)
    ax.scatter(
        nonraw.xb_rank_agree_delta,
        nonraw.xb_rank_disagree_diffbio_delta,
        s=2,
        c="#CCCCCC",
        linewidths=0,
        rasterized=True,
    )
    ax.scatter(
        spec.xb_rank_agree_delta,
        spec.xb_rank_disagree_diffbio_delta,
        s=7,
        c=[STRAT_PAL[s] for s in spec.strat],
        edgecolors="k",
        linewidths=0.2,
    )
    ax.axhline(0, color="k", lw=0.4)
    ax.axvline(0, color="k", lw=0.4)
    ax.set_xlabel("Δ same-biology agreement")
    ax.set_ylabel("Δ different-biology agr.")
    ax.set_title(
        f"{len(spec)} agreement-specific of {len(nonraw):,} non-raw",
        fontsize=SMALL,
        pad=2,
    )
    letter(fig, 196, 312, "E")

    # F — same-biology agreement, unharmonized baseline to harmonized, gated set.
    gate = df[(df.mk_rho_mean_markers > a2.RHO_GATE) & (df.xb_margin > 0) & ~df.is_raw]
    ax = axes_pt(fig, 30, 444, 150, 110)
    # Thin, faint lines per approach; the bold line per tier is its median start and
    # end, so the tier drawn last cannot hide the other two.
    for tier in ("high", "medium", "low"):
        g = gate[gate.harshness_level == tier]
        segs = np.stack(
            [
                np.column_stack([np.zeros(len(g)), g.xb_rank_agree_raw]),
                np.column_stack([np.ones(len(g)), g.xb_rank_agree]),
            ],
            axis=1,
        )
        ax.add_collection(
            LineCollection(
                segs, colors=HARSH_PAL[tier], lw=0.2, alpha=0.12, rasterized=True
            )
        )
    for tier in ("high", "medium", "low"):
        g = gate[gate.harshness_level == tier]
        ax.plot(
            [0, 1],
            [g.xb_rank_agree_raw.median(), g.xb_rank_agree.median()],
            color=HARSH_PAL[tier],
            lw=1.6,
            marker="o",
            ms=2.5,
            path_effects=[pe.withStroke(linewidth=2.4, foreground="k")],
        )
    ax.set_xlim(-0.08, 1.08)
    ax.set_ylim(
        min(gate.xb_rank_agree.min(), gate.xb_rank_agree_raw.min()) - 0.02,
        max(gate.xb_rank_agree.max(), gate.xb_rank_agree_raw.max()) + 0.02,
    )
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["unharmonized", "harmonized"])
    ax.set_ylabel("same-biology agreement")
    ax.set_title(
        f"{len(gate):,} non-raw approaches passing the L/M gate", fontsize=SMALL, pad=2
    )
    ax.legend(
        handles=[
            Line2D([], [], color=c, lw=1.4, label=k) for k, c in HARSH_PAL.items()
        ],
        title="harshness (bold: tier median)",
        frameon=False,
        loc="lower left",
        ncol=3,
        handlelength=1.0,
        columnspacing=0.6,
        borderaxespad=0.1,
    )
    letter(fig, 2, 432, "F")

    # Shared legends: methods and strategies, for A, B and C.
    _legend_block(axes_pt(fig, 196, 430, 180, 76), pal, "method (A, C)", ncol=3)
    _legend_block(
        axes_pt(fig, 196, 510, 180, 50),
        STRAT_PAL,
        "strategy (B, E)",
        ncol=2,
        marker="s",
    )
    save(
        fig,
        "fig_markers_lm",
        {
            "A": "class M margin vs class L marker correlation, by method (rho, p: A2_T11)",
            "B": "the same plane by strategy",
            "C": "methods ranked by median margin, clustermap group as its own row",
            "D": "median marker correlation and median margin by strategy and imputation",
            "E": "change in different- vs same-biology agreement; 61 agreement-specific",
            "F": "same-biology agreement unharmonized to harmonized, gate-passing set",
        },
    )


# ══ Figure 5 — class N ═══════════════════════════════════════════════════════


def fig_prediction_n(D) -> None:
    """Figure 5 A-D at about half the previous size (C50); D on the E1 index (C16).

    A methods ranked by median LOBO3 macro F1, both fold cuts, with the median
    multiclass-fold count; B per-batch F1 of the leading non-confounded approach; C
    fold composition; D generalizability index against the full-cut F1.
    """
    df, folds = D["df"], D["folds"]
    fig = new_figure(420)

    # A — methods, full cut and multiclass-only cut side by side.
    d = pd.concat(
        [
            df.assign(row=df.method),
            df[df.is_clustermap_best].assign(row="clustermap best"),
        ],
        ignore_index=True,
    )
    stats = d.groupby("row").agg(
        full=("pv_lobo3_f1_macro_mean", "median"),
        mc=("f1_mc_mean", "median"),
        n_mc=("n_mc", "median"),
    )
    stats = stats.sort_values("full", ascending=False)
    y = np.arange(len(stats))
    ax = axes_pt(fig, 80, 18, 70, 250)
    ax.hlines(y, stats.mc, stats.full, color="#BBBBBB", lw=0.6)
    ax.scatter(stats.full, y, s=8, c="#2979ae", label="all folds", zorder=3)
    ax.scatter(stats.mc, y, s=8, c="#E63946", label="multiclass folds", zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(stats.index, fontsize=SMALL)
    ax.set_ylim(len(stats) - 0.5, -0.5)
    ax.set_xlabel("median LOBO3 macro F1")
    ax.legend(
        frameon=False,
        loc="upper left",
        handletextpad=0.1,
        labelspacing=0.2,
        borderaxespad=0.1,
    )
    for tl in ax.get_yticklabels():
        if tl.get_text() == "clustermap best":
            tl.set_fontweight("bold")
    ax_n = axes_pt(fig, 154, 18, 22, 250)
    for yi, n in zip(y, stats.n_mc):
        ax_n.text(0.5, yi, f"{n:.0f}", ha="center", va="center", fontsize=SMALL)
    ax_n.set_ylim(len(stats) - 0.5, -0.5)
    ax_n.set_xlim(0, 1)
    ax_n.set_title("folds", fontsize=SMALL, pad=2)
    ax_n.axis("off")
    letter(fig, 2, 6, "A")

    # B — per-batch detail of the leading non-confounded approach.
    lead = D["t13"]
    lead_id = (
        lead[lead.label.str.startswith("best eligible")].label.iloc[0].split(": ")[1]
    )
    f = folds[folds.run_id == lead_id].copy()
    order = f[f.target == "3class"].sort_values("n", ascending=False).batch.tolist()
    yb = {b: i for i, b in enumerate(order)}
    ax = axes_pt(fig, 294, 18, 76, 250)
    for tgt, mk, off in (("3class", "o", -0.15), ("2class", "s", 0.15)):
        g = f[f.target == tgt]
        multi = g.n_classes >= 2
        yy = g.batch.map(yb) + off
        ax.scatter(
            g.f1_macro[multi],
            yy[multi],
            s=7,
            marker=mk,
            c="#2979ae",
            linewidths=0,
            label=f"{tgt[0]}-class target, multiclass fold",
        )
        ax.scatter(
            g.f1_macro[~multi],
            yy[~multi],
            s=7,
            marker=mk,
            facecolors="none",
            edgecolors="#2979ae",
            linewidths=0.4,
            label=f"{tgt[0]}-class target, single-class fold",
        )
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(
        [
            f"{b} (n={int(n)})"
            for b, n in f[f.target == "3class"]
            .set_index("batch")
            .loc[order, "n"]
            .items()
        ],
        fontsize=SMALL,
    )
    ax.set_ylim(len(order) - 0.5, -0.5)
    ax.set_xlabel("macro F1 in the held-out batch")
    strat_, imp_, meth_, post_ = lead_id.split("__")
    ax.set_title(f"{meth_}\n{strat_} / {imp_} / {post_}", fontsize=SMALL, pad=2)
    ax.legend(
        frameon=False,
        loc="upper right",
        bbox_to_anchor=(1.0, -0.075),
        ncol=2,
        handletextpad=0.1,
        labelspacing=0.2,
        columnspacing=0.6,
        borderaxespad=0.0,
    )
    letter(fig, 184, 6, "B")

    # C — fold composition over the analysis set.
    three = folds[folds.target == "3class"]
    ax = axes_pt(fig, 30, 318, 60, 84)
    counts = three.n_classes.value_counts().sort_index()
    ax.bar(counts.index.astype(str), counts.values, color="#2979ae", width=0.6)
    for k, v in counts.items():
        ax.text(str(k), v, f"{v:,}", ha="center", va="bottom", fontsize=SMALL)
    ax.set_ylim(0, counts.max() * 1.18)
    ax.set_xlabel("classes in held-out batch")
    ax.set_ylabel("3-class LOBO folds")
    ax.ticklabel_format(axis="y", style="plain")
    ax2 = axes_pt(fig, 116, 318, 64, 84)
    sns.boxplot(
        data=three,
        x="n_classes",
        y="f1_macro",
        color="#9ecae1",
        fliersize=0,
        linewidth=0.35,
        width=0.6,
        ax=ax2,
    )
    ax2.set_xlabel("classes in held-out batch")
    ax2.set_ylabel("macro F1")
    n0 = int((df.n_mc == 0).sum())
    ax2.set_title(f"{n0} approaches: no multiclass fold", fontsize=SMALL, pad=2)
    letter(fig, 2, 306, "C")

    # D — the E1 index against the full-cut F1, zero-multiclass approaches apart.
    rho, p = _rho_row(D["t11"], "pv_lobo3_f1_macro_mean", "generalizability_index")
    has = df[df.n_mc > 0]
    none = df[df.n_mc == 0]
    ax = axes_pt(fig, 222, 318, 110, 84)
    ax.scatter(
        has.pv_lobo3_f1_macro_mean,
        has.generalizability_index,
        s=2,
        c=["#E63946" if b else "#9E9E9E" for b in has.is_confirmed_bad],
        linewidths=0,
        rasterized=True,
    )
    ax.scatter(
        has[has.is_clustermap_best].pv_lobo3_f1_macro_mean,
        has[has.is_clustermap_best].generalizability_index,
        **STAR,
    )
    ax.set_xlabel("full-cut LOBO3 macro F1")
    ax.set_ylabel("generalizability index")
    ax.set_title(fmt_rho(rho, p), fontsize=SMALL, pad=2)
    ax0 = axes_pt(fig, 340, 318, 30, 84)
    ax0.scatter(
        np.random.default_rng(0).uniform(-0.3, 0.3, len(none)),
        none.generalizability_index,
        s=2,
        c="#2979ae",
        linewidths=0,
    )
    ax0.set_ylim(ax.get_ylim())
    ax0.set_xticks([0])
    ax0.set_xticklabels(["no mc\nfold"], fontsize=SMALL)
    ax0.set_yticklabels([])
    ax.legend(
        handles=[
            Line2D([], [], ls="", marker="o", ms=2.5, color="#9E9E9E", label="other"),
            Line2D(
                [],
                [],
                ls="",
                marker="o",
                ms=2.5,
                color="#E63946",
                label="bad-batch strategies",
            ),
            Line2D(
                [],
                [],
                ls="",
                marker="*",
                ms=4,
                mfc="none",
                mec="k",
                label="clustermap best",
            ),
        ],
        frameon=False,
        loc="upper left",
        handletextpad=0.1,
        labelspacing=0.2,
        borderaxespad=0.1,
    )
    letter(fig, 196, 306, "D")
    save(
        fig,
        "fig_prediction_n",
        {
            "A": "methods by median LOBO3 F1, all folds vs multiclass folds; median folds",
            "B": f"per-batch F1, both targets, single-class folds hollow: {lead_id}",
            "C": "3-class fold counts and F1 by classes in the held-out batch",
            "D": "E1 generalizability index vs full-cut F1; no-multiclass approaches apart",
        },
    )


# ══ The election figure — old Figure 5E-G ════════════════════════════════════


def fig_election(D) -> None:
    """The cross-election structure as its own figure, so no label overlaps (C50).

    A chord of the nine elected sets; B Venn of classes N, M and local; C supervenn of
    five sets; D the election funnel. Final numbering is Phase 5's.
    """
    sets, t3b = D["sets"], D["t3b"]
    classes = a2.ELECTION_CLASSES
    names = {"clustermap_best": "clustermap best"}
    colr = dict(zip(classes, sns.color_palette("husl", len(classes))))
    fig = new_figure(430)

    # A — chord: ribbon width follows the shared count.
    ax = axes_pt(fig, 20, 14, 160, 160)
    ang = {c: np.pi / 2 - 2 * np.pi * i / len(classes) for i, c in enumerate(classes)}
    for c in classes:
        a0 = np.degrees(ang[c]) - 15
        ax.add_patch(Wedge((0, 0), 1.0, a0, a0 + 30, width=0.09, color=colr[c]))
        ax.text(
            1.2 * np.cos(ang[c]),
            1.2 * np.sin(ang[c]),
            names.get(c, c),
            ha="center",
            va="center",
            fontsize=SMALL,
        )
    for r in t3b.itertuples():
        if not r.n_intersection:
            continue
        p0 = (0.9 * np.cos(ang[r.set_a]), 0.9 * np.sin(ang[r.set_a]))
        p1 = (0.9 * np.cos(ang[r.set_b]), 0.9 * np.sin(ang[r.set_b]))
        ax.add_patch(
            PathPatch(
                MplPath(
                    [p0, (0, 0), p1], [MplPath.MOVETO, MplPath.CURVE3, MplPath.CURVE3]
                ),
                fill=False,
                lw=0.3 + r.n_intersection / 8,
                edgecolor=colr[r.set_a],
                alpha=0.55,
            )
        )
    ax.set_xlim(-1.45, 1.45)
    ax.set_ylim(-1.45, 1.45)
    ax.set_aspect("equal")
    ax.axis("off")
    letter(fig, 2, 6, "A")

    # B — Venn of N, M and local, the labels moved into a legend.
    from matplotlib_venn import venn3

    ax = axes_pt(fig, 214, 20, 150, 120)
    v = venn3(
        [sets["N"], sets["M"], sets["local"]],
        set_labels=("", "", ""),
        set_colors=(colr["N"], colr["M"], colr["local"]),
        alpha=0.45,
        ax=ax,
    )
    for t in v.subset_labels:
        if t is not None:
            t.set_fontsize(SMALL)
    ax.legend(
        handles=[
            Patch(
                color=colr[c], alpha=0.6, label=f"class {c}" if c in ("N", "M") else c
            )
            for c in ("N", "M", "local")
        ],
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=3,
        handlelength=0.9,
        columnspacing=0.8,
    )
    letter(fig, 196, 6, "B")

    # C — supervenn of five sets; chunks too narrow to label stay unlabelled.
    five = ["N", "M", "L", "global", "local"]
    ax = axes_pt(fig, 44, 204, 326, 92)
    _chunk_plot(ax, {c: sets[c] for c in five}, colr)
    letter(fig, 2, 192, "C")

    # D — parallel bars, not a funnel: every class elects from all 2,234 approaches,
    # so the sets are not nested stages. Each bar is one set; its dark part is the
    # approaches of that set that pass the L/M gate.
    df = D["df"]
    gate = (df.mk_rho_mean_markers > a2.RHO_GATE) & (df.xb_margin > 0)
    multi = {i for i in df.index if sum(i in sets[c] for c in ("L", "M", "N")) >= 2}
    rows = [
        ("all approaches", set(df.index)),
        ("class L elected", sets["L"]),
        ("class M elected", sets["M"]),
        ("class N elected", sets["N"]),
        ("elected by 2+ of L, M, N", multi),
    ]
    ax = axes_pt(fig, 118, 334, 190, 80)
    for yi, (lab, ids) in enumerate(rows):
        n, k = len(ids), int(gate.loc[list(ids)].sum())
        ax.barh(yi, 100, color="#E3EAF2", height=0.62)
        ax.barh(yi, 100 * k / n, color="#2979ae", height=0.62)
        ax.text(102, yi, f"{k:,} of {n:,}", va="center", fontsize=SMALL)
    ax.set_xlim(0, 100)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=SMALL)
    ax.set_ylim(len(rows) - 0.5, -0.5)
    ax.set_xlabel("% of the set passing the L/M gate", fontsize=SMALL)
    ax.tick_params(axis="x", labelsize=SMALL)
    letter(fig, 2, 322, "D")
    save(
        fig,
        "fig_election",
        {
            "A": "chord of the nine elected sets; ribbon width = shared approaches (A2_T3b)",
            "B": "Venn of the class N, class M and local elected sets",
            "C": "supervenn of the N, M, L, global and local elected sets",
            "D": "set sizes of all approaches and of the L, M, N and 2+ elected sets, with the part passing the L/M gate",
        },
    )


def _chunk_plot(ax, sets: dict, colr: dict) -> None:
    """A supervenn-style chunk plot drawn directly, so every label is placed by hand.

    Each column is one membership pattern (which of the sets an approach is in); its
    width is the number of approaches with that pattern, widened to a floor so the
    one-approach chunks stay visible. Counts are printed under chunks wide enough.
    """
    names = list(sets)
    ids = set().union(*sets.values())
    pattern = pd.Series({i: tuple(i in sets[n] for n in names) for i in ids})
    chunks = pattern.value_counts()
    floor = chunks.sum() * 0.012
    x = 0.0
    for pat, n in chunks.items():
        w = max(n, floor)
        for r, (name, inside) in enumerate(zip(names, pat)):
            ax.add_patch(
                plt.Rectangle(
                    (x, r), w, 0.86, color=colr[name] if inside else "#F0F0F0", lw=0
                )
            )
        if n >= 8:
            ax.text(x + w / 2, -0.25, f"{n}", ha="center", va="top", fontsize=SMALL)
        x += w
    ax.set_xlim(0, x)
    ax.set_ylim(-0.9, len(names))
    ax.set_yticks(np.arange(len(names)) + 0.43)
    ax.set_yticklabels(
        [f"class {n}" if n in "LMN" else n for n in names], fontsize=SMALL
    )
    ax.tick_params(axis="y", length=0)
    ax.set_xticks([])
    ax.spines[["bottom", "left"]].set_visible(False)
    ax.set_xlabel(
        f"{len(ids)} approaches in at least one set; column width = "
        "approaches with that membership",
        fontsize=SMALL,
    )


# ══ Supplementary Figure 12 — harshness tiers, 3 x 4 grid (C44) ═══════════════

HARSH_GRID = [
    ("mk_rho_mean_markers", "marker correlation", None),
    ("mk_rho_marker_minus_hk", "marker − HK correlation", None),
    ("xb_rank_agree", "same-biology agreement", None),
    ("xb_rank_disagree_diffbio", "different-biology agreement", None),
    ("xb_margin", "margin", None),
    ("xb_margin_delta", "margin gain over baseline", None),
    ("pv_lobo3_f1_macro_mean", "LOBO3 F1, all folds", "pv_lobo3_f1_macro_perm_mean"),
    ("f1_mc_mean", "LOBO3 F1, multiclass folds", None),
    ("pv_lobo3_auc_macro_mean", "LOBO3 AUC", "pv_lobo3_auc_macro_perm_mean"),
    ("pv_lobo2_f1_macro_mean", "LOBO2 F1, all folds", "pv_lobo2_f1_macro_perm_mean"),
    ("f1_mc2_mean", "LOBO2 F1, multiclass folds", None),
    ("pv_lobo2_auc_macro_mean", "LOBO2 AUC", "pv_lobo2_auc_macro_perm_mean"),
]


def sfig_harshness(D) -> None:
    """Supplementary Figure 12 rebuilt: 12 panels A-L, one metric each (C44).

    Boxes are the three method harshness tiers; for the N metrics a grey box beside
    each tier is the label-permutation null (100 permutations). The p on each panel
    is the Kruskal-Wallis test across the tiers, raw, from A2_T9 / A2_T9b; H is no
    longer printed.
    """
    df = D["df"]
    kw = pd.concat([D["t9"], D["t9b"]]).drop_duplicates("metric").set_index("metric")
    fig = new_figure(470)
    tiers = ["low", "medium", "high"]
    for k, (col, lab, null) in enumerate(HARSH_GRID):
        r, c = divmod(k, 4)
        ax = axes_pt(fig, 30 + c * 88, 22 + r * 150, 62, 104)
        long = (
            df[["harshness_level", col]]
            .rename(columns={col: "v"})
            .assign(kind="observed")
        )
        if null:
            long = pd.concat(
                [
                    long,
                    df[["harshness_level", null]]
                    .rename(columns={null: "v"})
                    .assign(kind="permutation null"),
                ]
            )
        long = long.reset_index(drop=True)
        pal = {"observed": "#FFFFFF", "permutation null": NULL_COLOR}
        sns.boxplot(
            data=long,
            x="harshness_level",
            y="v",
            hue="kind" if null else None,
            order=tiers,
            palette=pal if null else None,
            color=None if null else "#FFFFFF",
            fliersize=0.5,
            linewidth=0.35,
            width=0.7,
            ax=ax,
            legend=False,
        )
        # Colour the observed boxes by tier after drawing: seaborn cannot hue by one
        # column and colour by another at the same time.
        observed = [p for p in ax.patches if p.get_facecolor()[:3] == (1.0, 1.0, 1.0)]
        for patch, t in zip(observed, tiers):
            patch.set_facecolor(HARSH_PAL[t])
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_title(f"{lab}\n{fmt_p(kw.loc[col, 'kruskal_p'])}", fontsize=SMALL, pad=2)
        ax.set_xticks(range(3))
        ax.set_xticklabels(["low", "med.", "high"], fontsize=SMALL)
        ax.tick_params(axis="y", labelsize=SMALL)
        ax.locator_params(axis="y", nbins=4)
        letter(fig, 6 + c * 88, 10 + r * 150, "ABCDEFGHIJKL"[k])
    fig.legend(
        handles=[
            Patch(fc=HARSH_PAL[t], ec="k", lw=0.3, label=f"{t} harshness")
            for t in tiers
        ]
        + [
            Patch(
                fc=NULL_COLOR,
                ec="k",
                lw=0.3,
                label="label-permutation null (100 permutations)",
            )
        ],
        loc="lower center",
        ncol=4,
        frameon=False,
        bbox_to_anchor=(0.5, 0.0),
        handlelength=1.0,
        columnspacing=1.0,
    )
    save(
        fig,
        "sfig_harshness",
        {
            "ABCDEFGHIJKL"[k]: f"{lab} by harshness tier"
            + (f"; grey = permutation null ({null})" if null else "")
            + f"; Kruskal-Wallis {fmt_p(kw.loc[col, 'kruskal_p'])}"
            for k, (col, lab, null) in enumerate(HARSH_GRID)
        },
    )


# ══ New supplementary figure — L/M/N scatterplots (C48) ══════════════════════

LMN_PAIRS = [
    (
        "mk_rho_mean_markers",
        "pv_lobo3_f1_macro_mean",
        "class L marker correlation",
        "LOBO3 F1, all folds",
    ),
    ("xb_margin", "pv_lobo3_f1_macro_mean", "class M margin", "LOBO3 F1, all folds"),
    (
        "xb_margin_delta",
        "f1_mc_mean",
        "class M margin gain over baseline",
        "LOBO3 F1, multiclass folds",
    ),
]


def sfig_lmn_scatter(D) -> None:
    """L/M/N metrics against each other, by method (left) and strategy (right).

    In the style of Figure 1A/1B (C48). rho and p on every panel are the A2_T11 rows.
    """
    df, pal = D["df"], D["method_pal"]
    fig = new_figure(540)
    for r, (x, y, xl, yl) in enumerate(LMN_PAIRS):
        rho, p = _rho_row(D["t11"], x, y)
        for c, (col, cpal) in enumerate((("method", pal), ("strat", STRAT_PAL))):
            ax = axes_pt(fig, 34 + c * 180, 18 + r * 140, 146, 106)
            _scatter(ax, df, x, y, col, cpal)
            ax.set_xlabel(xl)
            ax.set_ylabel(yl)
            ax.set_title(fmt_rho(rho, p), fontsize=SMALL, pad=2)
            letter(fig, 4 + c * 180, 6 + r * 140, "ABCDEF"[2 * r + c])
    _legend_block(axes_pt(fig, 10, 440, 180, 96), pal, "method (A, C, E)", ncol=3)
    _legend_block(
        axes_pt(fig, 200, 440, 176, 96),
        STRAT_PAL,
        "strategy (B, D, F)",
        ncol=2,
        marker="s",
    )
    panels = {}
    for r, (x, y, xl, yl) in enumerate(LMN_PAIRS):
        rho, p = _rho_row(D["t11"], x, y)
        for c, by in enumerate(("method", "strategy")):
            panels["ABCDEF"[2 * r + c]] = f"{yl} vs {xl}, by {by}; {fmt_rho(rho, p)}"
    save(fig, "sfig_lmn_scatter", panels)


# ══ New supplementary figure — all-metric cross-correlation clustermap (C48) ═══

CLASS_PAL = {
    "global": "#1b9e77",
    "local": "#d95f02",
    "distributional": "#7570b3",
    "structural": "#e7298a",
    "L": "#66a61e",
    "M": "#e6ab02",
    "N": "#a6761d",
    "unassigned": "#BBBBBB",
}
TYPE_PAL = {
    "Global": "#8c510a",
    "Local": "#01665e",
    "Distributional similarity": "#35978f",
    "Other": "#6b6b3a",
}


def _metric_matrix(D) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """The recoverable non-metadata registry metrics as columns over the 2,234.

    Routes from A2_T12: direct and renamed snapshot columns, the two derived
    percentages, the baseline-derived L/M/N columns (from add_raw_deltas), and the
    boolean flags as 0/1. Columns constant over the analysis set are dropped, since a
    constant has no correlation; the drop is reported.
    """
    full, reg = D["full"], D["t12"]
    reg = reg[~reg.is_metadata & reg.recoverable].copy()
    cols = {}
    for r in reg.itertuples():
        if r.route == "derived_percent":
            num, den = PERCENT_SRC[r.Metric]
            cols[r.Metric] = 100 * full[num] / full[den]
        else:
            src = r.snapshot_source if r.route == "rename" else r.Metric
            if src in full.columns:
                cols[r.Metric] = full[src].astype(float)
            elif r.route == "boolean_flag":
                snap = pd.read_csv(
                    METRICS_PATH, usecols=a2.KEY + [r.Metric], low_memory=False
                )
                snap = a2._canonicalize_shambhala(snap)
                snap.index = (
                    snap.strat
                    + "__"
                    + snap.imp
                    + "__"
                    + snap.method
                    + "__post"
                    + snap.post_rm.astype(int).astype(str)
                )
                cols[r.Metric] = snap[r.Metric].reindex(full.index).astype(float)
    m = pd.DataFrame(cols, index=full.index)
    keep = m.columns[(m.nunique(dropna=True) > 1) & (m.notna().sum() >= 100)]
    dropped = sorted(set(reg.Metric) - set(keep))
    return m[keep], reg.set_index("Metric").loc[keep], dropped


PERCENT_SRC = {
    "pct_samples_allNA": ("n_samples_allNA", "n_samples"),
    "pct_genes_allNA": ("n_genes_allNA", "n_genes"),
}


def sfig_metric_clustermap(D) -> None:
    """Spearman cross-correlation of every usable non-metadata metric (C48).

    Pairwise-complete Spearman over the 2,234 approaches, average-linkage clustering
    on 1 - rho, with color bars for the registry metric group and metric type and
    for the Article 2 metric class. Too many metrics to label individually; the names
    and their order are written to data/sfig_metric_clustermap_order.csv.
    """
    m, meta, dropped = _metric_matrix(D)
    corr = m.corr(method="spearman", min_periods=100).fillna(0.0)
    groups = sorted(meta["Metric group"].astype(str).unique())
    group_pal = dict(zip(groups, sns.color_palette("tab20", len(groups))))
    bars = pd.DataFrame(
        {
            "group": meta["Metric group"].astype(str).map(group_pal),
            "type": meta["Metric type"].map(TYPE_PAL),
            "class": meta["article2_class"].replace("", "unassigned").map(CLASS_PAL),
        },
        index=corr.index,
    )
    from scipy.cluster.hierarchy import linkage
    from scipy.spatial.distance import squareform

    # Average linkage on the distance 1 - rho itself. seaborn's metric="correlation"
    # would instead correlate the rows of the rho matrix with each other.
    dist = squareform(np.clip(1 - corr.values, 0, 2), checks=False)
    link = linkage(dist, method="average")
    g = sns.clustermap(
        corr,
        row_linkage=link,
        col_linkage=link,
        cmap="RdBu_r",
        vmin=-1,
        vmax=1,
        row_colors=bars,
        col_colors=bars,
        xticklabels=False,
        yticklabels=False,
        figsize=(W_IN, 520 / 72),
        dendrogram_ratio=0.09,
        colors_ratio=0.012,
        cbar_pos=(0.03, 0.9, 0.018, 0.08),
        rasterized=True,
    )
    g.ax_heatmap.set_rasterized(True)
    g.ax_heatmap.set_position([0.16, 0.13, 0.8, 0.72])
    for axn in (g.ax_row_colors, g.ax_col_colors):
        axn.tick_params(labelsize=SMALL, length=0)
    g.ax_cbar.set_title("Spearman ρ", fontsize=SMALL, pad=2)
    g.ax_cbar.tick_params(labelsize=SMALL)
    # Re-place the colour bars and dendrograms around the moved heat map.
    hm = g.ax_heatmap.get_position()
    g.ax_row_colors.set_position([hm.x0 - 0.045, hm.y0, 0.04, hm.height])
    g.ax_row_dendrogram.set_position([0.02, hm.y0, hm.x0 - 0.07, hm.height])
    g.ax_col_colors.set_position([hm.x0, hm.y1 + 0.004, hm.width, 0.03])
    g.ax_col_dendrogram.set_position([hm.x0, hm.y1 + 0.038, hm.width, 0.06])
    handles = (
        [Patch(color=c, label=f"group {k}") for k, c in group_pal.items()]
        + [Patch(color=c, label=k) for k, c in TYPE_PAL.items()]
        + [Patch(color=c, label=f"class {k}") for k, c in CLASS_PAL.items()]
    )
    g.fig.legend(
        handles=handles,
        loc="lower center",
        ncol=5,
        frameon=False,
        bbox_to_anchor=(0.5, 0.0),
        handlelength=0.9,
        columnspacing=0.8,
        labelspacing=0.25,
    )
    g.ax_col_colors.set_yticks([])
    g.fig.text(
        0.56,
        0.115,
        f"{corr.shape[0]} metrics; color bars, outer to inner: " "group, type, class",
        ha="center",
        va="top",
        fontsize=SMALL,
    )
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    order = corr.index[g.dendrogram_row.reordered_ind]
    meta.loc[order].assign(position=range(len(order))).to_csv(
        DATA_DIR / "sfig_metric_clustermap_order.csv"
    )
    (DATA_DIR / "sfig_metric_clustermap_dropped.json").write_text(
        json.dumps(
            {"n_used": int(corr.shape[0]), "dropped_constant_or_sparse": dropped},
            indent=1,
        )
    )
    save(
        g.fig,
        "sfig_metric_clustermap",
        {
            "A": f"Spearman clustermap of {corr.shape[0]} of the 334 non-metadata metrics "
            f"({len(dropped)} constant or sparse over the analysis set, 5 absent from "
            "the snapshot); bars: metric group, type, Article 2 class"
        },
    )


# ══ New supplementary figure — expression, linear vs non-linear methods (C50) ══

EXPR_STRATEGY, EXPR_IMP = "S0_no_removal", "knn"
EXPR_METHODS = [
    ("03_limma", "linear"),
    ("05_combat", "linear"),
    ("29_combat_ref", "linear"),
    ("13_fsmvn", "linear"),
    ("16_fsqn_r", "non-linear"),
    ("17_quantile", "non-linear"),
    ("10_mnn", "non-linear"),
    ("12_scanorama", "non-linear"),
]
EXPR_GENES = ["BCL6", "IRF4", "EEF1A1"]  # GC marker, post-GC marker, housekeeping
EXPR_CSV = DATA_DIR / "sfig_expression_long_260925.csv.gz"


def prepare_expression() -> None:
    """Read the three genes from the cached S3 matrices into one long table.

    Only three columns are read from each ~600 MB matrix; the result is persisted so
    the figure never needs S3 again. The raw reference is 01_raw at the same strategy
    and imputation, intersected on samples -- the rule class L itself uses.
    """
    read = lambda m: pd.read_csv(
        EXP_CACHE / f"{EXPR_STRATEGY}__{EXPR_IMP}__{m}__post0.tsv.gz",
        sep="\t",
        index_col=0,
        usecols=["Unnamed: 0"] + EXPR_GENES,
    )
    ann = pd.read_csv(
        EXP_CACHE / f"{EXPR_STRATEGY}__{EXPR_IMP}__ann.tsv.gz",
        sep="\t",
        index_col=0,
        usecols=["Unnamed: 0", "COHORT_LABEL"],
    )
    raw = read("01_raw")
    rows = []
    for method, kind in EXPR_METHODS:
        harm = read(method)
        s = harm.index.intersection(raw.index)
        for gene in EXPR_GENES:
            rows.append(
                pd.DataFrame(
                    {
                        "sample": s,
                        "cohort": ann.reindex(s).COHORT_LABEL.values,
                        "method": method,
                        "kind": kind,
                        "gene": gene,
                        "raw": raw.loc[s, gene].values,
                        "harmonized": harm.loc[s, gene].values,
                    }
                )
            )
        print(f"  {method}: {len(s)} samples")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pd.concat(rows).to_csv(EXPR_CSV, index=False)
    print(f"  wrote {EXPR_CSV}")


def sfig_expression(D) -> None:
    """Raw against harmonized expression, 8 methods x 3 genes, 4 largest cohorts.

    Replaces Figure 4A/4B and Supplementary Figure 14 (C50): no 01_raw panel, and four
    linear against four non-linear methods under one strategy and imputation, so the
    shape of each transformation can be compared directly. The label on each cell is
    the median over the four cohorts of the within-cohort Spearman rho, the quantity
    class L averages.
    """
    long = pd.read_csv(EXPR_CSV)
    cohorts = (
        long[long.method == EXPR_METHODS[0][0]]
        .drop_duplicates("sample")
        .cohort.value_counts()
        .head(4)
        .index.tolist()
    )
    long = long[long.cohort.isin(cohorts)]
    cpal = dict(zip(cohorts, ["#1b9e77", "#d95f02", "#7570b3", "#e7298a"]))
    fig = new_figure(572)
    for r, (method, kind) in enumerate(EXPR_METHODS):
        for c, gene in enumerate(EXPR_GENES):
            d = long[(long.method == method) & (long.gene == gene)]
            ax = axes_pt(fig, 74 + c * 102, 16 + r * 64, 86, 48)
            for co in cohorts:
                e = d[d.cohort == co]
                ax.scatter(
                    e.raw,
                    e.harmonized,
                    s=0.8,
                    c=cpal[co],
                    linewidths=0,
                    alpha=0.6,
                    rasterized=True,
                )
            lo, hi = (
                d[["raw", "harmonized"]].min().min(),
                d[["raw", "harmonized"]].max().max(),
            )
            ax.plot([lo, hi], [lo, hi], color="k", lw=0.4, ls="--")
            rhos = [
                spearmanr(
                    d[d.cohort == co].raw,
                    d[d.cohort == co].harmonized,
                    nan_policy="omit",
                ).statistic
                for co in cohorts
            ]
            ax.text(
                0.03,
                0.97,
                f"ρ = {np.nanmedian(rhos):.3f}",
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=SMALL,
            )
            ax.tick_params(labelsize=SMALL)
            ax.locator_params(nbins=3)
            if r == 0:
                ax.set_title(gene, fontsize=LABEL, pad=3)
            if r == len(EXPR_METHODS) - 1:
                ax.set_xlabel("unharmonized", fontsize=SMALL)
            if c == 0:
                ax.set_ylabel("harmonized", fontsize=SMALL)
        fig.text(
            4 / FRAME_W_PT,
            1 - (16 + r * 64 + 26) / 572,
            f"{method}\n{kind}",
            fontsize=SMALL,
            va="center",
            ha="left",
        )
        letter(fig, 4, 6 + r * 64, "ABCDEFGH"[r])
    fig.legend(
        handles=[
            Line2D([], [], ls="", marker="o", ms=3, color=c, label=k)
            for k, c in cpal.items()
        ],
        loc="lower center",
        ncol=4,
        frameon=False,
        bbox_to_anchor=(0.55, 0.0),
        columnspacing=1.0,
    )
    save(
        fig,
        "sfig_expression",
        {
            "ABCDEFGH"[
                r
            ]: f"{m} ({k}), {EXPR_STRATEGY}/{EXPR_IMP}/post0: harmonized vs "
            f"unharmonized {', '.join(EXPR_GENES)}; 4 largest cohorts"
            for r, (m, k) in enumerate(EXPR_METHODS)
        },
    )


# ══ New supplementary figure — per-component PCA, consolidated (C35) ══════════


def sfig_pca(D) -> None:
    """The per-component PCA heat maps in one figure (C35).

    Variance explained by PC1-PC10 and the share of it explained by RNA_BATCH (R²),
    by method (A, B) and by strategy (C, D), each with the clustermap-selected group
    as its own row, rows ordered by mean batch PCReg. Replaces the split between
    Figure 1C and Supplementary Figure 2F.
    """
    full = D["full"]
    pcs = range(1, 11)
    var_cols = [f"pct_var_pc{i}" for i in pcs]
    r2_cols = [f"r2_pc{i}_RNA_BATCH" for i in pcs]
    best = full[full.is_clustermap_best]

    def table(key):
        g = full.groupby(key)[var_cols + r2_cols + ["pcr_RNA_BATCH"]].mean()
        g.loc["clustermap best"] = best[var_cols + r2_cols + ["pcr_RNA_BATCH"]].mean()
        return g.sort_values("pcr_RNA_BATCH", ascending=False)

    fig = new_figure(560)
    blocks = [
        ("method", table("method"), 18, 300),
        ("strategy", table("strat"), 370, 150),
    ]
    for b, (key, tab, y0, h) in enumerate(blocks):
        labels = [short_strat(i) if key == "strategy" else i for i in tab.index]
        for c, (cols, cmap, cl, vmax) in enumerate(
            (
                (var_cols, "Blues", "% variance", None),
                (r2_cols, "Reds", "batch R² (%)", 100),
            )
        ):
            ax = axes_pt(fig, 92 + c * 148, y0, 110, h)
            vals = tab[cols] * (100 if c == 1 else 1)
            im = ax.imshow(vals.values, aspect="auto", cmap=cmap, vmin=0, vmax=vmax)
            ax.set_xticks(range(10))
            ax.set_xticklabels([f"PC{i}" for i in pcs], rotation=90, fontsize=SMALL)
            ax.set_yticks(range(len(tab)))
            ax.set_yticklabels(labels if c == 0 else [], fontsize=SMALL)
            if c == 0:
                for tl in ax.get_yticklabels():
                    if tl.get_text() == "clustermap best":
                        tl.set_fontweight("bold")
            cax = axes_pt(fig, 92 + c * 148 + 113, y0, 4, 60)
            cb = fig.colorbar(im, cax=cax)
            cb.ax.tick_params(labelsize=SMALL, length=1.5)
            cb.set_label(cl, fontsize=SMALL)
            letter(fig, 2 if c == 0 else 226, y0 - 12, "ABCD"[2 * b + c])
    save(
        fig,
        "sfig_pca",
        {
            "A": "% of total variance on PC1-PC10 by method, ordered by mean batch PCReg",
            "B": "RNA_BATCH R² (%) on PC1-PC10 by method",
            "C": "% of total variance on PC1-PC10 by strategy",
            "D": "RNA_BATCH R² (%) on PC1-PC10 by strategy",
        },
    )


BUILDERS = {
    "fig_markers_lm": fig_markers_lm,
    "fig_prediction_n": fig_prediction_n,
    "fig_election": fig_election,
    "sfig_harshness": sfig_harshness,
    "sfig_lmn_scatter": sfig_lmn_scatter,
    "sfig_metric_clustermap": sfig_metric_clustermap,
    "sfig_expression": sfig_expression,
    "sfig_pca": sfig_pca,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default="", help="comma-separated builder names")
    ap.add_argument(
        "--prepare-expression",
        action="store_true",
        help="extract the scatter genes from the S3 cache and exit",
    )
    args = ap.parse_args()
    if args.prepare_expression:
        prepare_expression()
        return 0
    names = [n.strip() for n in args.only.split(",") if n.strip()] or list(BUILDERS)
    D = load_data()
    for n in names:
        BUILDERS[n](D)
    report = OUT_DIR / "figure_report_260925.json"
    old = json.loads(report.read_text()) if report.exists() else {}
    report.write_text(json.dumps(old | REPORT, indent=1))
    print(f"wrote {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
