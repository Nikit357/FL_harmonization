"""Artwork for the Article 2 recipe figure ("How to choose a harmonization approach").

Artwork only -- no text. Every label is a Figma TEXT node in the frame
"Figure 6 - Recipe" on Page 2 (1013:2) of file t8bFgusleBEwB9ht7rORCH. Keeping type out
of the SVG is what makes the Figma acceptance audit authoritative: it can read every
character that appears in the figure, which it could not do for type baked into a path.

Mirrors figures_for_article/figure_drawing_scripts/graphical_abstract_assets.py: black
line art on a transparent ground, connected by arrows, no fills except where a filled
mark carries meaning.

Canvas: 750 x 1000 px at 2 px = 1 pt, matching the Page 2 frames. Each asset is drawn on
its own canvas at the size it occupies in that layout.

    source ~/venvs/collagen_3_11/bin/activate
    cd article_2_extended_comparison
    python figures/recipe_figure_assets.py --out-dir figures/recipe_assets_260917
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, PathPatch, Polygon, Rectangle
from matplotlib.path import Path as MplPath

PX_PER_PT = 2.0
LW = 1.0
INK = "black"
RNG = np.random.default_rng(42)     # seed 42, as everywhere else in this project


def canvas(w_px: float, h_px: float):
    """A transparent axes in pixel coordinates, so sizes match the Figma frame."""
    fig, ax = plt.subplots(figsize=(w_px / PX_PER_PT / 72, h_px / PX_PER_PT / 72))
    ax.set_xlim(0, w_px)
    ax.set_ylim(0, h_px)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    return fig, ax


def arrow(ax, p0, p1, rad=0.0, lw=LW):
    ax.add_patch(FancyArrowPatch(
        p0, p1, arrowstyle="-|>", mutation_scale=7, lw=lw, color=INK,
        connectionstyle=f"arc3,rad={rad}", shrinkA=2, shrinkB=2))


def box(ax, x, y, w, h, lw=LW, dashed=False, fill=None):
    ax.add_patch(Rectangle((x, y), w, h, fill=fill is not None, facecolor=fill or "none",
                           edgecolor=INK, lw=lw,
                           linestyle=(0, (3, 2)) if dashed else "solid"))


def diamond(ax, cx, cy, w, h, lw=LW):
    ax.add_patch(Polygon([(cx, cy + h / 2), (cx + w / 2, cy),
                          (cx, cy - h / 2), (cx - w / 2, cy)],
                         closed=True, fill=False, edgecolor=INK, lw=lw))


def cloud(ax, cx, cy, n=40, spread=18, filled=False):
    pts = RNG.normal((cx, cy), spread, size=(n, 2))
    ax.scatter(pts[:, 0], pts[:, 1], s=3.5, facecolors=INK if filled else "none",
               edgecolors=INK, linewidths=0.5)
    return pts


def save(fig, out_dir: Path, name: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.svg"
    fig.savefig(path, transparent=True, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(f"  {path}")


# ── the six metric-class icons ────────────────────────────────────────────────

def icon_global(out_dir):
    """PCA scatter: two batch clouds, one separated and one overlapping."""
    fig, ax = canvas(220, 120)
    cloud(ax, 60, 78, spread=14)
    cloud(ax, 60, 38, spread=14, filled=True)
    cloud(ax, 165, 58, spread=17)
    cloud(ax, 168, 58, spread=17, filled=True)
    arrow(ax, (105, 58), (130, 58))
    save(fig, out_dir, "recipe_icon_global")


def icon_local(out_dir):
    """A kNN neighbourhood, unmixed on the left and mixed on the right."""
    fig, ax = canvas(220, 120)
    for cx, mixed in ((58, False), (162, True)):
        ax.add_patch(Circle((cx, 60), 34, fill=False, edgecolor=INK, lw=LW,
                            linestyle=(0, (3, 2))))
        ang = np.linspace(0, 2 * np.pi, 11)[:-1]
        for k, a in enumerate(ang):
            x, y = cx + 22 * np.cos(a), 60 + 22 * np.sin(a)
            solid = (k % 2 == 0) if mixed else (a < np.pi)
            ax.scatter([x], [y], s=14, facecolors=INK if solid else "none",
                       edgecolors=INK, linewidths=0.6)
        ax.scatter([cx], [60], s=6, c=INK)
    arrow(ax, (100, 60), (124, 60))
    save(fig, out_dir, "recipe_icon_local")


def icon_distribution(out_dir):
    """Two density curves, apart and converged."""
    fig, ax = canvas(220, 120)
    x = np.linspace(0, 90, 200)
    for base, (m1, m2) in ((6, (28, 62)), (124, (44, 50))):
        for m in (m1, m2):
            y = 30 + 52 * np.exp(-0.5 * ((x - m) / 11) ** 2)
            ax.plot(base + x, y, color=INK, lw=LW)
        ax.plot([base, base + 90], [30, 30], color=INK, lw=0.6)
    arrow(ax, (102, 60), (120, 60))
    save(fig, out_dir, "recipe_icon_distribution")


def icon_marker(out_dir):
    """Gene x cohort correlation strip: a grid whose cells carry a value."""
    fig, ax = canvas(220, 120)
    nx, ny = 8, 5
    cw, ch = 22, 18
    x0, y0 = 20, 16
    vals = RNG.uniform(0.35, 1.0, size=(ny, nx))
    for i in range(ny):
        for j in range(nx):
            v = vals[i, j]
            box(ax, x0 + j * cw, y0 + i * ch, cw, ch, lw=0.5)
            # a filled bar inside each cell reads as a value without a colour scale
            ax.add_patch(Rectangle((x0 + j * cw + 2, y0 + i * ch + 2),
                                   (cw - 4) * v, ch - 4, facecolor=INK,
                                   edgecolor="none", alpha=0.85))
    save(fig, out_dir, "recipe_icon_marker")


def icon_rank(out_dir):
    """Two ranked gene lists, with ties drawn between agreeing positions."""
    fig, ax = canvas(220, 140)
    n = 7
    left = np.arange(n)
    right = RNG.permutation(n)
    for k in range(n):
        y = 124 - k * 17
        ax.plot([34, 68], [y, y], color=INK, lw=LW)
        ax.plot([152, 186], [y, y], color=INK, lw=LW)
    for k in range(n):
        y0 = 124 - left[k] * 17
        y1 = 124 - int(np.where(right == k)[0][0]) * 17
        path = MplPath([(68, y0), (110, y0), (110, y1), (152, y1)],
                       [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4])
        ax.add_patch(PathPatch(path, fill=False, edgecolor=INK, lw=0.6))
    save(fig, out_dir, "recipe_icon_rank")


def icon_lobo(out_dir):
    """Batch strip with one fold held out, feeding a confusion matrix."""
    fig, ax = canvas(220, 120)
    for k in range(6):
        box(ax, 14 + k * 22, 74, 20, 26, dashed=(k == 3))
    arrow(ax, (86, 70), (86, 50))
    for i in range(3):
        for j in range(3):
            box(ax, 130 + j * 20, 20 + i * 20, 20, 20, lw=0.6)
            if i == j:
                ax.add_patch(Rectangle((130 + j * 20, 20 + i * 20), 20, 20,
                                       facecolor=INK, edgecolor="none", alpha=0.8))
    arrow(ax, (100, 40), (124, 40))
    save(fig, out_dir, "recipe_icon_lobo")


# ── the three traps and the fold-composition rule ─────────────────────────────

def trap_saturation(out_dir):
    """Trap 1: a Group L metric pinned at its ceiling beside a failing local metric."""
    fig, ax = canvas(240, 130)
    ax.plot([20, 110], [18, 18], color=INK, lw=0.8)
    ax.plot([20, 20], [18, 112], color=INK, lw=0.8)
    x = np.linspace(0, 88, 100)
    ax.plot(20 + x, 18 + 88 * (1 - np.exp(-x / 9)), color=INK, lw=LW)
    ax.plot([20, 110], [106, 106], color=INK, lw=0.6, ls=(0, (3, 2)))
    ax.plot([140, 230], [18, 18], color=INK, lw=0.8)
    ax.plot([140, 140], [18, 112], color=INK, lw=0.8)
    for k, h in enumerate((10, 14, 9, 12, 8)):
        box(ax, 148 + k * 16, 18, 11, h, lw=0.8, fill=INK)
    save(fig, out_dir, "recipe_trap_saturation")


def trap_classcount(out_dir):
    """Trap 2: the same local metric read off two different class compositions."""
    fig, ax = canvas(240, 130)
    for base, parts in ((14, (1,)), (134, (0.34, 0.33, 0.33))):
        ax.add_patch(Circle((base + 46, 74), 34, fill=False, edgecolor=INK, lw=LW))
        start = 90
        for frac in parts:
            ang = np.linspace(np.radians(start), np.radians(start + 360 * frac), 40)
            ax.plot(base + 46 + 34 * np.cos(ang), 74 + 34 * np.sin(ang),
                    color=INK, lw=2.4)
            start += 360 * frac + 6
        box(ax, base + 18, 14, 56, 16, lw=0.8)
        ax.add_patch(Rectangle((base + 20, 16), 52 if base == 14 else 22, 12,
                               facecolor=INK, edgecolor="none"))
    save(fig, out_dir, "recipe_trap_classcount")


def trap_confound(out_dir):
    """Trap 3: batch and label are the same partition, so the classifier reads the batch."""
    fig, ax = canvas(240, 130)
    for k, (cx, filled) in enumerate(((60, True), (180, False))):
        ax.add_patch(Rectangle((cx - 48, 60), 96, 50, fill=False, edgecolor=INK,
                               lw=LW, linestyle=(0, (3, 2))))
        cloud(ax, cx, 85, n=26, spread=13, filled=filled)
    ax.add_patch(Rectangle((12, 18), 216, 26, fill=False, edgecolor=INK, lw=LW))
    ax.plot([120, 120], [18, 44], color=INK, lw=LW)
    ax.add_patch(Rectangle((12, 18), 108, 26, facecolor=INK, edgecolor="none",
                           alpha=0.85))
    arrow(ax, (60, 58), (60, 46))
    arrow(ax, (180, 58), (180, 46))
    save(fig, out_dir, "recipe_trap_confound")


def fold_composition(out_dir):
    """Not a trap: one batch strip split into single-class and multiclass folds.

    Each half feeds its own metric box and both boxes survive -- the two cuts are
    reported side by side, and neither corrects the other.
    """
    fig, ax = canvas(260, 150)
    for k in range(8):
        single = k in (0, 2, 5)
        box(ax, 12 + k * 28, 112, 26, 28, lw=LW, fill=INK if single else None)
    arrow(ax, (70, 108), (58, 74), rad=-0.15)
    arrow(ax, (180, 108), (196, 74), rad=0.15)
    box(ax, 14, 38, 88, 34)
    box(ax, 152, 38, 88, 34)
    for x0 in (14, 152):
        for j in range(3):
            ax.plot([x0 + 12 + j * 22, x0 + 12 + j * 22], [46, 64], color=INK, lw=0.8)
    arrow(ax, (58, 34), (110, 16))
    arrow(ax, (196, 34), (146, 16))
    box(ax, 104, 4, 48, 12, lw=LW)
    save(fig, out_dir, "recipe_fold_composition")


# ── the two schemes ───────────────────────────────────────────────────────────

def flow_spine(out_dir):
    """The block-scheme spine: five stages, two decision diamonds, arrows only."""
    fig, ax = canvas(300, 620)
    ys = [560, 450, 340, 205, 80]
    for y in ys:
        box(ax, 60, y, 180, 52)
    for a, b in zip(ys, ys[1:]):
        arrow(ax, (150, a), (150, b + 52))
    diamond(ax, 150, 290, 92, 46)
    diamond(ax, 150, 155, 92, 46)
    arrow(ax, (196, 290), (268, 290), rad=0.0)
    arrow(ax, (268, 290), (268, 586), rad=0.0)
    arrow(ax, (268, 586), (240, 586), rad=0.0)
    save(fig, out_dir, "recipe_flow_spine")


def lobo_scheme(out_dir):
    """The LOBO procedure drawn out, as Daniil asked.

    Batch strip with one batch lifted, PCA fit on the rest, logistic regression, the
    held-out batch projected onto those components, prediction, metric box, and the
    return arrow that closes the loop over batches.
    """
    fig, ax = canvas(560, 300)

    # 1. the batch strip, one batch lifted clear of the row
    for k in range(7):
        if k == 4:
            continue
        box(ax, 14 + k * 30, 232, 26, 40)
    box(ax, 14 + 4 * 30, 186, 26, 40, dashed=True)

    # 2. PCA fit on the remaining batches
    arrow(ax, (120, 228), (150, 190))
    ax.add_patch(Circle((196, 168), 34, fill=False, edgecolor=INK, lw=LW))
    cloud(ax, 196, 168, n=26, spread=13)
    ax.annotate("", xy=(222, 190), xytext=(170, 146),
                arrowprops=dict(arrowstyle="-", lw=0.8, color=INK))
    ax.annotate("", xy=(172, 190), xytext=(220, 146),
                arrowprops=dict(arrowstyle="-", lw=0.8, color=INK, ls=":"))

    # 3. logistic regression trained on those components
    arrow(ax, (232, 168), (276, 168))
    box(ax, 280, 138, 78, 60)
    xs = np.linspace(0, 70, 80)
    ax.plot(284 + xs, 152 + 32 / (1 + np.exp(-(xs - 35) / 7)), color=INK, lw=LW)

    # 4. the held-out batch projected onto the training components. The arrow starts at
    # the lifted box itself, so the reader sees which batch is being projected.
    arrow(ax, (160, 200), (186, 186), rad=-0.25)
    cloud(ax, 196, 168, n=10, spread=20, filled=True)

    # 5. prediction, then the metric box
    arrow(ax, (358, 168), (400, 168))
    for i in range(3):
        for j in range(3):
            box(ax, 404 + j * 22, 140 + i * 22, 22, 22, lw=0.6)
            if i == j:
                ax.add_patch(Rectangle((404 + j * 22, 140 + i * 22), 22, 22,
                                       facecolor=INK, edgecolor="none", alpha=0.8))
    arrow(ax, (436, 134), (436, 100))
    box(ax, 388, 56, 96, 42)
    for j in range(3):
        ax.plot([404 + j * 28, 404 + j * 28], [64, 90], color=INK, lw=1.4)

    # 6. the return arrow: the loop runs once per batch
    ax.add_patch(FancyArrowPatch((388, 77), (40, 77), arrowstyle="-|>",
                                 mutation_scale=8, lw=LW, color=INK,
                                 connectionstyle="arc3,rad=0.12"))
    arrow(ax, (40, 77), (40, 226))
    save(fig, out_dir, "recipe_lobo_scheme")


ASSETS = [icon_global, icon_local, icon_distribution, icon_marker, icon_rank,
          icon_lobo, trap_saturation, trap_classcount, trap_confound,
          fold_composition, flow_spine, lobo_scheme]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default="figures/recipe_assets_260917")
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    print(f"recipe_figure_assets -> {out_dir}")
    for fn in ASSETS:
        fn(out_dir)
    print(f"{len(ASSETS)} assets written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
