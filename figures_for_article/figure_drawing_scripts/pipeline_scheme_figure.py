"""
pipeline_scheme_figure.py

Publication-grade SVG pipeline scheme for the FL harmonization benchmark.
Produces 10 × 20 cm figures suitable as a panel in a Nature-like multipanel layout.
Run from figures_for_article/:
    python pipeline_scheme_figure.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle

# ── Global constants ──────────────────────────────────────────────────────────
FONT = 10
FIGURES_DIR = Path("figures")
FIGURES_DIR.mkdir(exist_ok=True)

FIG_W_IN = 10 / 2.54   # 10 cm in inches
FIG_H_IN = 20 / 2.54   # 20 cm in inches

# Temperature-Split palette + structural colours
COLD_BLUE  = "#3498DB"
WARM_RED   = "#E74C3C"
DARK_NAVY  = "#2C3E50"
GREY_SUB   = "#7F8C8D"
GREEN_GOOD = "#27AE60"
BOX_FACE   = "#F7F9FC"
BOX_EDGE   = "#2C3E50"

# Metric tile colours (one per group family)
TILE_COLORS = {
    "global":       "#4A90D9",
    "local":        "#E05C5C",
    "biology":      "#27AE60",
    "embedding":    "#9B59B6",
    "distribution": "#F39C12",
    "composite":    "#1ABC9C",
    "quality":      "#95A5A6",
}

# ── rcParams ─────────────────────────────────────────────────────────────────
plt.rcParams["pdf.fonttype"] = 42       # TrueType embedding in PDF
plt.rcParams["svg.fonttype"] = "none"   # text stays editable in Figma
plt.rcParams["figure.dpi"]   = 200
sns.set_style("ticks")


# ── Stage layout ─────────────────────────────────────────────────────────────
# Each entry: (x0, y0, width, height, title, subtitle)
# y0 is the matplotlib bottom edge (lower y = lower on page).
# Boxes are ordered from top of page (highest y) to bottom (lowest y).
# All coordinates are in the [0, 1] data range of ax_main.

MARGIN_X = 0.04
BOX_W    = 1.0 - 2 * MARGIN_X   # 0.92

STAGES = [
    # box 0 — Raw Data
    (MARGIN_X, 0.90, BOX_W, 0.07,
     "Raw Expression Data",
     "~7,238 samples · 95% variance = RNA_BATCH"),

    # box 1 — Strategies
    (MARGIN_X, 0.80, BOX_W, 0.08,
     "Batch Removal Strategies",
     "14 strategies: A–K (confirmed-bad, extended, mixed platforms, FF/FFPE only, rare batches)"),

    # box 2 — Imputation
    (MARGIN_X, 0.71, BOX_W, 0.07,
     "Imputation",
     "strict (drop-NA)  ·  KNN  ·  softimpute"),

    # box 3 — Log transform
    (MARGIN_X, 0.62, BOX_W, 0.07,
     "Log₂ Transform",
     "per cohort  ·  threshold = 30  ·  log₂(x + 1)"),

    # box 4 — Harmonization (key stage)
    (MARGIN_X, 0.51, BOX_W, 0.09,
     "Harmonization  —  39 Methods",
     "QN · ComBat · SVA · MNN · FSQN · Harmony · Scanorama · RUV · others"),

    # box 5 — Post-removal
    (MARGIN_X, 0.42, BOX_W, 0.07,
     "Post-Removal",
     "post0 (keep all)  ·  post1 (remove mono-platform batches)"),

    # box 6 — Metrics (tall: holds 7 sub-tiles)
    (MARGIN_X, 0.25, BOX_W, 0.15,
     "Metrics Computation",
     "11 groups A–K · Global · Local · Biology · Embedding · Distribution · Composite · Quality"),

    # box 7 — Polarity
    (MARGIN_X, 0.14, BOX_W, 0.09,
     "Polarity Setting",
     "Invert: kBET, PCR, R²(batch)   ·   Keep: iLISI, ASW_bio, WM ratio"),

    # box 8 — Clustermap
    (MARGIN_X, 0.02, BOX_W, 0.10,
     "Clustermap + Best Selection",
     "3,835 attempts  ·  top methods highlighted in gold"),
]

# Pre-compute arrow positions: tail = bottom of box i, head = top of box i+1.
# In matplotlib coordinates, bottom of box = y0, top of box = y0 + h.
ARROWS = [
    (STAGES[i][1],                            # y_from = bottom of box i (lower y)
     STAGES[i + 1][1] + STAGES[i + 1][3])     # y_to   = top of box i+1  (higher y)
    for i in range(len(STAGES) - 1)
]
ARROW_X = 0.50   # horizontal centre of all inter-stage arrows


# ── Helper: stage box ────────────────────────────────────────────────────────

def draw_stage_box(ax, x0, y0, w, h, title, subtitle=""):
    """Render one pipeline stage box on ax.

    The left 40% of the box width is reserved for an icon sub-axis (added
    separately). Title and subtitle are rendered in the right 60%.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Full-figure axis with xlim = ylim = (0, 1).
    x0, y0 : float
        Bottom-left corner in data coordinates.
    w, h : float
        Width and height in data coordinates.
    title : str
        Bold label at FONT size.
    subtitle : str
        Grey annotation at FONT - 2 size placed below the title.
    """
    ax.add_patch(FancyBboxPatch(
        xy=(x0, y0), width=w, height=h,
        boxstyle="round,pad=0.004",
        facecolor=BOX_FACE,
        edgecolor=BOX_EDGE,
        linewidth=0.8,
        zorder=2,
    ))

    text_x = x0 + w * 0.40
    mid_y  = y0 + h / 2

    if subtitle:
        v = h * 0.15
        ax.text(text_x, mid_y + v, title,
                fontsize=FONT, fontweight="bold", color=DARK_NAVY,
                va="center", ha="left", zorder=3)
        ax.text(text_x, mid_y - v, subtitle,
                fontsize=FONT - 2, color=GREY_SUB,
                va="center", ha="left", zorder=3)
    else:
        ax.text(text_x, mid_y, title,
                fontsize=FONT, fontweight="bold", color=DARK_NAVY,
                va="center", ha="left", zorder=3)


# ── Helper: connecting arrow ─────────────────────────────────────────────────

def draw_connecting_arrow(ax, x, y_from, y_to, label=""):
    """Draw a downward-pointing arrow between two consecutive stage boxes.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Full-figure axis (xlim = ylim = 0–1).
    x : float
        Horizontal centre of the arrow in data coordinates.
    y_from : float
        Tail Y (bottom edge of the upper box, so the tail sits below it).
    y_to : float
        Head Y (top edge of the lower box, so the head points into it).
    label : str
        Short annotation placed to the right of the arrow midpoint.
    """
    ax.annotate(
        "",
        xy=(x, y_to),
        xytext=(x, y_from),
        arrowprops=dict(
            arrowstyle="-|>",
            color=DARK_NAVY,
            lw=1.2,
            connectionstyle="arc3,rad=0.0",
        ),
        zorder=3,
    )
    if label:
        ax.text(
            x + 0.015, (y_from + y_to) / 2,
            label,
            fontsize=FONT - 2, color=GREY_SUB,
            va="center", ha="left", zorder=4,
        )


# ── Icon stubs (placeholders until individual icon functions are added) ───────

def _icon_rect(fig, stage_idx):
    """Return [left, bottom, width, height] in figure coordinates for the icon area."""
    x0, y0, w, h = STAGES[stage_idx][:4]
    icon_w = w * 0.32
    icon_h = h * 0.75
    icon_x = x0 + w * 0.03
    icon_y = y0 + h * 0.125
    # Convert data coords (= figure fraction for full-figure axes) directly
    fig_w_data = 1.0   # xlim spans 0→1
    fig_h_data = 1.0   # ylim spans 0→1
    return [icon_x / fig_w_data, icon_y / fig_h_data,
            icon_w / fig_w_data, icon_h / fig_h_data]


# ── Icon functions ───────────────────────────────────────────────────────────

def draw_raw_data_icon(fig, rect):
    """Stage 0: 8×6 striped heatmap — horizontal batch blocks show batch dominance."""
    ax = fig.add_axes(rect)
    data = np.zeros((8, 6))
    data[0:2, :] = 0.90
    data[2:4, :] = 0.35
    data[4:6, :] = 0.65
    data[6:8, :] = 0.15
    ax.imshow(data, aspect='auto', cmap='RdYlBu_r', interpolation='nearest',
              vmin=0, vmax=1)
    ax.set_axis_off()
    ax.text(0.5, -0.22, "95% var = RNA_BATCH",
            transform=ax.transAxes, fontsize=FONT - 4,
            color=WARM_RED, ha='center', va='top', clip_on=False)


def draw_strategies_icon(fig, rect):
    """Stage 1: Trapezoid funnel + abbreviated strategy family labels inside."""
    ax = fig.add_axes(rect)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_axis_off()
    funnel = Polygon(
        [[0.08, 0.95], [0.92, 0.95], [0.68, 0.10], [0.32, 0.10]],
        closed=True,
        facecolor=COLD_BLUE, alpha=0.22,
        edgecolor=DARK_NAVY, linewidth=0.8,
        zorder=2,
    )
    ax.add_patch(funnel)
    ax.text(0.50, 0.72, "A   B   C–D",
            fontsize=FONT - 3, ha='center', va='center',
            color=DARK_NAVY, zorder=3)
    ax.text(0.50, 0.38, "E1–E3   F–K",
            fontsize=FONT - 3, ha='center', va='center',
            color=DARK_NAVY, zorder=3)


def draw_imputation_icon(fig, rect):
    """Stage 2: Two 4×4 matrices — left has grey missing cells, right is fully filled."""
    l, b, w, h = rect
    mat_w = w * 0.38
    gap_w = w * 0.24

    MISSING = {(0, 2), (1, 0), (2, 3), (3, 1)}

    ax_l = fig.add_axes([l, b, mat_w, h])
    ax_l.set_xlim(0, 4)
    ax_l.set_ylim(0, 4)
    ax_l.set_axis_off()
    for r in range(4):
        for c in range(4):
            fc = '#B0B0B0' if (r, c) in MISSING else '#F0F0F0'
            ax_l.add_patch(Rectangle((c, 3 - r), 1, 1,
                           facecolor=fc, edgecolor=DARK_NAVY, linewidth=0.5))

    ax_r = fig.add_axes([l + mat_w + gap_w, b, mat_w, h])
    ax_r.set_xlim(0, 4)
    ax_r.set_ylim(0, 4)
    ax_r.set_axis_off()
    for r in range(4):
        for c in range(4):
            ax_r.add_patch(Rectangle((c, 3 - r), 1, 1,
                           facecolor='#F0F0F0', edgecolor=DARK_NAVY, linewidth=0.5))

    # Transparent overlay axis to draw the inter-matrix arrow in rect coordinates
    ax_mid = fig.add_axes(rect)
    ax_mid.set_xlim(0, 1)
    ax_mid.set_ylim(0, 1)
    ax_mid.set_axis_off()
    ax_mid.patch.set_visible(False)
    x0_arr = (mat_w + gap_w * 0.15) / w
    x1_arr = (mat_w + gap_w * 0.85) / w
    ax_mid.annotate(
        "",
        xy=(x1_arr, 0.5), xytext=(x0_arr, 0.5),
        arrowprops=dict(arrowstyle="-|>", color=DARK_NAVY, lw=0.8),
    )


def draw_log_transform_icon(fig, rect):
    """Stage 3: log₂(x+1) curve with minimal left+bottom spines, no ticks."""
    ax = fig.add_axes(rect)
    x = np.linspace(0, 100, 200)
    y = np.log2(x + 1)
    ax.plot(x, y, color=DARK_NAVY, lw=1.5)
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)
    for sp in ['left', 'bottom']:
        ax.spines[sp].set_linewidth(0.6)
        ax.spines[sp].set_color(GREY_SUB)
    ax.set_xlabel("x", fontsize=FONT - 3, labelpad=1, color=GREY_SUB)
    ax.set_ylabel("log₂(x+1)", fontsize=FONT - 3, labelpad=1, color=GREY_SUB)


def draw_harmonization_icon(fig, rect):
    """Stage 4: PCA before (4 tight clusters) → after (mixed), arrow labelled '39 methods'."""
    l, b, w, h = rect
    scatter_w = w * 0.40
    gap_w = w * 0.20

    tab10 = plt.cm.tab10
    colors = [tab10(i * 0.1) for i in range(4)]
    centers = [(-1.5, -1.5), (1.5, -1.5), (-1.5, 1.5), (1.5, 1.5)]

    # Before: 4 tight batch clusters
    ax_before = fig.add_axes([l, b, scatter_w, h])
    ax_before.set_axis_off()
    np.random.seed(42)
    for i, (cx, cy) in enumerate(centers):
        pts = np.random.randn(20, 2) * 0.30 + [cx, cy]
        ax_before.scatter(pts[:, 0], pts[:, 1], color=colors[i], s=3, alpha=0.9)
    ax_before.set_xlim(-3, 3)
    ax_before.set_ylim(-3, 3)
    ax_before.text(0.5, 0.93, "Before", transform=ax_before.transAxes,
                   fontsize=FONT - 4, ha='center', va='top', color=WARM_RED)

    # After: same colors, uniformly scattered (batch effect removed)
    ax_after = fig.add_axes([l + scatter_w + gap_w, b, scatter_w, h])
    ax_after.set_axis_off()
    np.random.seed(99)
    for i in range(4):
        pts = np.random.randn(20, 2) * 1.2
        ax_after.scatter(pts[:, 0], pts[:, 1], color=colors[i], s=3, alpha=0.9)
    ax_after.set_xlim(-3, 3)
    ax_after.set_ylim(-3, 3)
    ax_after.text(0.5, 0.93, "After", transform=ax_after.transAxes,
                  fontsize=FONT - 4, ha='center', va='top', color=GREEN_GOOD)

    # Transparent overlay: inter-scatter arrow + "39 methods" label
    ax_mid = fig.add_axes(rect)
    ax_mid.set_xlim(0, 1)
    ax_mid.set_ylim(0, 1)
    ax_mid.set_axis_off()
    ax_mid.patch.set_visible(False)
    x0_arr = scatter_w / w + (gap_w * 0.12) / w
    x1_arr = scatter_w / w + (gap_w * 0.88) / w
    ax_mid.annotate(
        "",
        xy=(x1_arr, 0.50), xytext=(x0_arr, 0.50),
        arrowprops=dict(arrowstyle="-|>", color=DARK_NAVY, lw=0.8),
    )
    ax_mid.text(
        (x0_arr + x1_arr) / 2, 0.74,
        "39\nmethods",
        fontsize=FONT - 4, ha='center', va='center', color=DARK_NAVY,
    )


def draw_post_removal_icon(fig, rect):
    """Stage 5: Y-fork — stem splits into post0 (blue) and post1 (red) branches."""
    ax = fig.add_axes(rect)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_axis_off()

    # Vertical stem into the fork point
    ax.plot([0.50, 0.50], [0.95, 0.68], color=DARK_NAVY, lw=1.0,
            solid_capstyle='round')
    ax.plot(0.50, 0.68, 'o', color=DARK_NAVY, ms=2.5, zorder=3)

    # Left branch → post0 (keep all batches)
    ax.annotate(
        "",
        xy=(0.12, 0.22), xytext=(0.50, 0.68),
        arrowprops=dict(arrowstyle="-|>", color=COLD_BLUE, lw=1.0,
                        connectionstyle="arc3,rad=0.0"),
    )
    # Right branch → post1 (remove mono-platform batches)
    ax.annotate(
        "",
        xy=(0.88, 0.22), xytext=(0.50, 0.68),
        arrowprops=dict(arrowstyle="-|>", color=WARM_RED, lw=1.0,
                        connectionstyle="arc3,rad=0.0"),
    )
    ax.text(0.12, 0.18, "post0", fontsize=FONT - 3, ha='center', va='top',
            color=COLD_BLUE)
    ax.text(0.88, 0.18, "post1", fontsize=FONT - 3, ha='center', va='top',
            color=WARM_RED)


def draw_metrics_icon(fig, rect):
    """Stage 6: 4+3 tile grid — each tile is a coloured FancyBboxPatch with a mini-icon."""
    l, b_r, w, h = rect   # b_r avoids collision with loop variables

    OUTER  = 0.004   # outer padding (figure fraction)
    GAP_X  = 0.005   # horizontal gap between tiles
    GAP_Y  = 0.008   # vertical gap between rows

    tile_w = (w - 2 * OUTER - 3 * GAP_X) / 4
    tile_h = (h - 2 * OUTER - GAP_Y) / 2

    row1_y  = b_r + OUTER + tile_h + GAP_Y   # top row: bottom edge y
    row2_y  = b_r + OUTER                    # bottom row: bottom edge y
    col0_x  = l + OUTER
    row2_x0 = col0_x + (tile_w + GAP_X) / 2  # bottom row centred in 4-col space

    # (x, y, colour, short_label)
    TILES = [
        (col0_x + 0 * (tile_w + GAP_X), row1_y, "#4A90D9", "Global"),
        (col0_x + 1 * (tile_w + GAP_X), row1_y, "#E05C5C", "Local"),
        (col0_x + 2 * (tile_w + GAP_X), row1_y, "#27AE60", "Biology"),
        (col0_x + 3 * (tile_w + GAP_X), row1_y, "#9B59B6", "Embed."),
        (row2_x0 + 0 * (tile_w + GAP_X), row2_y, "#F39C12", "Distrib."),
        (row2_x0 + 1 * (tile_w + GAP_X), row2_y, "#1ABC9C", "WM"),
        (row2_x0 + 2 * (tile_w + GAP_X), row2_y, "#95A5A6", "Quality"),
    ]

    # Transparent full-figure overlay axis for tile backgrounds and labels
    ax_bg = fig.add_axes([0, 0, 1, 1])
    ax_bg.set_xlim(0, 1)
    ax_bg.set_ylim(0, 1)
    ax_bg.set_axis_off()
    ax_bg.patch.set_visible(False)

    LABEL_H_FRAC = 0.28    # fraction of tile_h for the name label at bottom
    ICON_MARGIN  = 0.003   # inner padding around each mini-icon axis

    mi_w = tile_w - 2 * ICON_MARGIN
    mi_h = tile_h * (1 - LABEL_H_FRAC) - 2 * ICON_MARGIN

    for tx, ty, color, label in TILES:
        ax_bg.add_patch(FancyBboxPatch(
            (tx, ty), tile_w, tile_h,
            boxstyle="round,pad=0.002",
            facecolor=color, alpha=0.18,
            edgecolor=color, linewidth=0.8,
            zorder=2,
        ))
        ax_bg.text(
            tx + tile_w / 2, ty + tile_h * 0.13,
            label, fontsize=FONT - 4,
            ha='center', va='center', color='#333333', zorder=3,
        )

    def add_mini_ax(tx, ty):
        return fig.add_axes([
            tx + ICON_MARGIN,
            ty + tile_h * LABEL_H_FRAC + ICON_MARGIN,
            mi_w,
            mi_h,
        ])

    # Tile 0 — Global: bar chart PC1–PC3 variance
    ax0 = add_mini_ax(*TILES[0][:2])
    ax0.bar([0, 1, 2], [0.85, 0.30, 0.10], color='#4A90D9', width=0.7)
    ax0.set_xlim(-0.5, 2.5)
    ax0.set_ylim(0, 1)
    ax0.set_axis_off()

    # Tile 1 — Local: 4-node kNN neighbourhood graph
    ax1 = add_mini_ax(*TILES[1][:2])
    nodes    = [(0.10, 0.10), (0.90, 0.10), (0.10, 0.90), (0.90, 0.90)]
    node_clr = ['#E74C3C', '#3498DB', '#27AE60', '#F39C12']
    for ai, bi in [(0, 1), (0, 2), (1, 3), (2, 3), (0, 3)]:
        ax1.plot([nodes[ai][0], nodes[bi][0]], [nodes[ai][1], nodes[bi][1]],
                 color='#AAAAAA', lw=0.7, zorder=1)
    for j, (nx, ny) in enumerate(nodes):
        ax1.scatter(nx, ny, color=node_clr[j], s=18, zorder=3)
    ax1.set_xlim(-0.15, 1.15)
    ax1.set_ylim(-0.15, 1.15)
    ax1.set_axis_off()

    # Tile 2 — Biology: two tight clusters (DLBCL red / FL blue)
    ax2 = add_mini_ax(*TILES[2][:2])
    np.random.seed(7)
    pts_dlbcl = np.random.randn(20, 2) * 0.30 + np.array([-0.7, 0])
    pts_fl    = np.random.randn(20, 2) * 0.30 + np.array([+0.7, 0])
    ax2.scatter(pts_dlbcl[:, 0], pts_dlbcl[:, 1], color='#E74C3C', s=4, alpha=0.85)
    ax2.scatter(pts_fl[:, 0],    pts_fl[:, 1],    color='#3498DB', s=4, alpha=0.85)
    ax2.set_axis_off()

    # Tile 3 — Embedding: UMAP-like scatter + centroid triangle
    ax3 = add_mini_ax(*TILES[3][:2])
    np.random.seed(11)
    pts_umap = np.random.randn(40, 2)
    ax3.scatter(pts_umap[:, 0], pts_umap[:, 1], color='#9B59B6', s=3, alpha=0.55)
    ax3.scatter([0], [0], marker='^', color='#2C3E50', s=18, zorder=4)
    ax3.set_axis_off()

    # Tile 4 — Distribution: two overlapping Gaussian fill_between curves
    ax4 = add_mini_ax(*TILES[4][:2])
    x_kde = np.linspace(-3, 3, 80)
    ax4.fill_between(x_kde, 0, np.exp(-0.5 * (x_kde - 0.8) ** 2),
                     alpha=0.55, color='#E74C3C')
    ax4.fill_between(x_kde, 0, np.exp(-0.5 * (x_kde + 0.8) ** 2),
                     alpha=0.55, color='#3498DB')
    ax4.set_axis_off()

    # Tile 5 — Composite: donut chart (Batch dark / Biology light)
    ax5 = add_mini_ax(*TILES[5][:2])
    ax5.pie([0.35, 0.65], colors=['#2C3E50', '#1ABC9C'], startangle=90,
            wedgeprops=dict(width=0.5))
    ax5.set_axis_off()

    # Tile 6 — Quality: horizontal bars (samples green / genes green / NA rate red)
    ax6 = add_mini_ax(*TILES[6][:2])
    ax6.barh([0, 1, 2], [0.90, 0.80, 0.05],
             color=[GREEN_GOOD, GREEN_GOOD, WARM_RED], height=0.6)
    ax6.set_xlim(0, 1)
    ax6.set_ylim(-0.5, 2.5)
    ax6.set_axis_off()


def draw_polarity_icon(fig, rect):
    """Stage 7: Two scatter plots — batch mixing (GOOD ↑, green) vs biology mixing (BAD ↓, red)."""
    l, b_r, w, h = rect
    scatter_w = w * 0.42
    gap_w     = w * 0.16

    # Left: 4 batch colours uniformly scattered → batch mixing is GOOD
    ax_batch = fig.add_axes([l, b_r, scatter_w, h])
    ax_batch.set_axis_off()
    np.random.seed(13)
    for col in [WARM_RED, COLD_BLUE, GREEN_GOOD, '#F39C12']:
        pts = np.random.randn(15, 2) * 1.2
        ax_batch.scatter(pts[:, 0], pts[:, 1], color=col, s=3, alpha=0.75)
    ax_batch.set_xlim(-3.5, 3.5)
    ax_batch.set_ylim(-3.5, 3.5)
    ax_batch.text(0.50, 0.95, "Batch ↑", transform=ax_batch.transAxes,
                  fontsize=FONT - 4, ha='center', va='top', color=GREEN_GOOD)

    # Right: 3 diagnosis colours uniformly scattered → biology preservation lost = BAD
    ax_bio = fig.add_axes([l + scatter_w + gap_w, b_r, scatter_w, h])
    ax_bio.set_axis_off()
    np.random.seed(17)
    for col in [WARM_RED, COLD_BLUE, GREY_SUB]:
        pts = np.random.randn(15, 2) * 1.2
        ax_bio.scatter(pts[:, 0], pts[:, 1], color=col, s=3, alpha=0.75)
    ax_bio.set_xlim(-3.5, 3.5)
    ax_bio.set_ylim(-3.5, 3.5)
    ax_bio.text(0.50, 0.95, "Biology ↓", transform=ax_bio.transAxes,
                fontsize=FONT - 4, ha='center', va='top', color=WARM_RED)


def draw_clustermap_icon(fig, rect):
    """Stage 8: 8×12 heatmap (RdYlBu_r) with gold highlight on top 2 rows + stub dendrograms."""
    l, b_r, w, h = rect

    DENDRO_W_FRAC = 0.18   # left dendrogram: fraction of icon width
    DENDRO_H_FRAC = 0.22   # top dendrogram: fraction of icon height

    dw = w * DENDRO_W_FRAC
    dh = h * DENDRO_H_FRAC
    hw = w - dw
    hh = h - dh

    np.random.seed(5)
    data = np.random.rand(8, 12)

    # Main heatmap
    ax_hmap = fig.add_axes([l + dw, b_r, hw, hh])
    ax_hmap.imshow(data, aspect='auto', cmap='RdYlBu_r', interpolation='nearest',
                   vmin=0, vmax=1)
    # Gold overlay on top 2 rows (origin='upper': row 0 → y ∈ [-0.5, 0.5]; row 1 → [0.5, 1.5])
    ax_hmap.add_patch(Rectangle((-0.5, -0.5), 12, 2,
                      facecolor='#FFD700', alpha=0.45,
                      edgecolor='#DAA520', linewidth=0.8, zorder=3))
    ax_hmap.set_axis_off()

    # Top dendrogram — ∩-shaped bracket stubs above the heatmap
    ax_dtop = fig.add_axes([l + dw, b_r + hh, hw, dh])
    ax_dtop.set_xlim(-0.5, 11.5)
    ax_dtop.set_ylim(0, 1)
    ax_dtop.set_axis_off()
    for x1, x2, y_top in [(0.5, 2.5, 0.40), (3.5, 5.5, 0.36), (7.5, 9.5, 0.44),
                           (1.5, 4.5, 0.65), (8.5, 10.5, 0.68), (3.0, 9.0, 0.88)]:
        ax_dtop.plot([x1, x1, x2, x2], [0.0, y_top, y_top, 0.0],
                     color=DARK_NAVY, lw=0.6)

    # Left dendrogram — ⊏-shaped bracket stubs to the left of the heatmap
    ax_dleft = fig.add_axes([l, b_r, dw, hh])
    ax_dleft.set_xlim(0, 1)
    ax_dleft.set_ylim(-0.5, 7.5)
    ax_dleft.set_axis_off()
    for y1, y2, x_reach in [(0.5, 1.5, 0.58), (2.5, 3.5, 0.52), (5.5, 6.5, 0.60),
                             (1.0, 3.0, 0.80), (5.0, 7.0, 0.82)]:
        ax_dleft.plot([1.0, x_reach, x_reach, 1.0], [y1, y1, y2, y2],
                      color=DARK_NAVY, lw=0.6)


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN))

    # Full-figure axis: data coordinates (0,1)×(0,1) = figure fraction
    ax_main = fig.add_axes([0, 0, 1, 1])
    ax_main.set_xlim(0, 1)
    ax_main.set_ylim(0, 1)
    ax_main.set_axis_off()

    # Draw all stage boxes
    for x0, y0, w, h, title, subtitle in STAGES:
        draw_stage_box(ax_main, x0, y0, w, h, title, subtitle)

    # Draw all connecting arrows
    for y_from, y_to in ARROWS:
        draw_connecting_arrow(ax_main, ARROW_X, y_from, y_to)

    # Draw all stage icons (stages 0–8)
    draw_raw_data_icon(fig, _icon_rect(fig, 0))
    draw_strategies_icon(fig, _icon_rect(fig, 1))
    draw_imputation_icon(fig, _icon_rect(fig, 2))
    draw_log_transform_icon(fig, _icon_rect(fig, 3))
    draw_harmonization_icon(fig, _icon_rect(fig, 4))
    draw_post_removal_icon(fig, _icon_rect(fig, 5))
    draw_metrics_icon(fig, _icon_rect(fig, 6))
    draw_polarity_icon(fig, _icon_rect(fig, 7))
    draw_clustermap_icon(fig, _icon_rect(fig, 8))

    fig.savefig(FIGURES_DIR / "pipeline_scheme.svg", bbox_inches="tight")
    fig.savefig(FIGURES_DIR / "pipeline_scheme.png", bbox_inches="tight", dpi=200)
    plt.close(fig)
    print("Saved figures/pipeline_scheme.svg and figures/pipeline_scheme.png")
