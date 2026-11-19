"""Minimalistic vector t-SNE scatter panels for the NAR graphical abstract.

Draws simplified, two-colour replacements for the four raster t-SNE panels in the
Figma frame ``Graphical Abstract`` (node 1172:6): Biology / Batch  x  Before / After.

Design contract (schematic, not a data plot):

* Point coordinates are shared **within a row**, exactly as in the real figure, where
  the two panels of a row are one embedding coloured two different ways.
* Before  -> eight tight, well-separated islands (one island == one batch).
      Biology colouring  : each island is an internal red/black mix -> biology unresolved.
      Batch   colouring  : each island is one pure colour            -> batches unmixed.
* After   -> two large coherent clusters.
      Biology colouring  : one cluster red, one black                -> biology preserved.
      Batch   colouring  : both clusters internally mixed            -> batches mixed.

Each panel is emitted as an SVG whose points are **two merged paths** (one per colour),
so a single click in Figma recolours a whole group.

Run from ``figures_for_article/``:
    python figure_drawing_scripts/ga_scatter_vectors_260912.py
Outputs ``figures/ga/scatter_*.svg`` plus a combined PNG contact sheet for review.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE.parent / "figures" / "ga"

# Panel geometry — matches the raster slots in the Figma frame exactly.
PANEL_W, PANEL_H = 146.0, 120.5
PAD = 9.0  # keep points off the axis box

# Project palette (root CLAUDE.md / graphical_abstract_assets.py).
RED = "#B2182B"     # cancer / warm
BLACK = "#1A1A1A"
BOX_STROKE = "#333333"
DOT_R = 1.45

RNG = np.random.default_rng(20260912)

ISLANDS = [  # before: one island per batch
    (30.0, 26.0), (73.0, 20.0), (117.0, 31.0), (26.0, 61.0),
    (71.0, 59.0), (116.0, 69.0), (41.0, 97.0), (93.0, 99.0),
]
ISLAND_N = 20
ISLAND_SD = 5.1
# Which batch island is which colour (batch colouring of the "before" row).
ISLAND_BATCH_RED = {0, 2, 3, 5}

# Two coherent biological clusters, deliberately offset onto different axes so a
# clear diagonal gap survives at ~35 mm final width (the "biology preserved" read).
CLUSTERS = [
    dict(centre=(42.0, 36.0), sd=(15.5, 9.0), angle=22.0, n=80),
    dict(centre=(105.0, 85.0), sd=(15.5, 9.0), angle=-18.0, n=80),
]


def _island_points() -> tuple[np.ndarray, np.ndarray]:
    """Return (xy, island_index) for the pre-harmonization embedding."""
    xy, idx = [], []
    for i, (cx, cy) in enumerate(ISLANDS):
        pts = RNG.normal((cx, cy), ISLAND_SD, size=(ISLAND_N, 2))
        xy.append(pts)
        idx.append(np.full(ISLAND_N, i))
    return np.vstack(xy), np.concatenate(idx)


def _cluster_points() -> tuple[np.ndarray, np.ndarray]:
    """Return (xy, cluster_index) for the post-harmonization embedding."""
    xy, idx = [], []
    for i, spec in enumerate(CLUSTERS):
        n = spec["n"]
        base = RNG.normal(0.0, 1.0, size=(n, 2)) * np.asarray(spec["sd"])
        # radial thinning so the blob reads as a cloud, not a filled ellipse
        theta = np.deg2rad(spec["angle"])
        rot = np.array([[np.cos(theta), -np.sin(theta)],
                        [np.sin(theta), np.cos(theta)]])
        xy.append(base @ rot.T + np.asarray(spec["centre"]))
        idx.append(np.full(n, i))
    return np.vstack(xy), np.concatenate(idx)


def _clip(xy: np.ndarray) -> np.ndarray:
    xy[:, 0] = np.clip(xy[:, 0], PAD, PANEL_W - PAD)
    xy[:, 1] = np.clip(xy[:, 1], PAD, PANEL_H - PAD)
    return xy


def circle_path(pts: Iterable[Iterable[float]], r: float = DOT_R) -> str:
    """Merge many dots into one SVG path (two arc subpaths per dot)."""
    d = []
    for x, y in pts:
        d.append(
            f"M{x - r:.1f} {y:.1f}"
            f"a{r} {r} 0 1 0 {2 * r:.1f} 0"
            f"a{r} {r} 0 1 0 {-2 * r:.1f} 0"
        )
    return "".join(d)


def panel_svg(xy: np.ndarray, is_red: np.ndarray) -> str:
    red_d = circle_path(xy[is_red])
    black_d = circle_path(xy[~is_red])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PANEL_W}" '
        f'height="{PANEL_H}" viewBox="0 0 {PANEL_W} {PANEL_H}">'
        f'<rect x="0.5" y="0.5" width="{PANEL_W - 1}" height="{PANEL_H - 1}" '
        f'fill="#FFFFFF" stroke="{BOX_STROKE}" stroke-width="1"/>'
        f'<path d="{black_d}" fill="{BLACK}"/>'
        f'<path d="{red_d}" fill="{RED}"/>'
        f"</svg>"
    )


def build() -> dict[str, str]:
    globals()["RNG"] = np.random.default_rng(20260912)
    before_xy, island = _island_points()
    before_xy = _clip(before_xy)
    after_xy, cluster = _cluster_points()
    after_xy = _clip(after_xy)

    rng = np.random.default_rng(7)
    panels = {
        # before, coloured by biology: every batch island holds both classes
        "before_biology": (before_xy, rng.random(len(before_xy)) < 0.5),
        # before, coloured by batch: each island is one pure batch
        "before_batch": (before_xy, np.isin(island, list(ISLAND_BATCH_RED))),
        # after, coloured by biology: two pure clusters
        "after_biology": (after_xy, cluster == 0),
        # after, coloured by batch: both clusters fully intermixed
        "after_batch": (after_xy, rng.random(len(after_xy)) < 0.5),
    }
    return {name: panel_svg(xy, red) for name, (xy, red) in panels.items()}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    svgs = build()
    for name, svg in svgs.items():
        (OUT_DIR / f"scatter_{name}.svg").write_text(svg)
    (OUT_DIR / "scatter_panels.json").write_text(json.dumps(svgs))
    print(json.dumps({k: len(v) for k, v in svgs.items()}, indent=2))
    print(f"written to {OUT_DIR}")


if __name__ == "__main__":
    main()
