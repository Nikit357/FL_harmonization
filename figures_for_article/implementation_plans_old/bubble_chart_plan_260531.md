# Bubble Chart Implementation Plan
**Date:** 2026-05-31  
**Notebook:** `figures_for_article/Introductory_figures_for_article.ipynb`  
**Cells to add:** after the markdown cell `## Bubble chart of samples by their batches amd biology` (cell id `cd627ada`)

---

## Overview

Build a 2-level bubble chart (one circle = one sample) that mirrors the DepMap CCLE portal style:
- **Level 1 (major group):** `Platform_group` — 4 groups: Illumina NGS, Affymetrix Microarray, Illumina Microarray, Agilent Microarray
- **Level 2 (sub-group):** `RNA_BATCH` — 29 batches colored by `rna_batch_palette`
- Each sample is one equal-sized circle; within each RNA_BATCH sub-group the circles are **hexagonally packed** and the lattice is **rotated** by a distinct angle per batch
- Each sub-group gets a **white-to-transparent gradient label** (the DepMap-style shading) over the left edge of the cluster, with the batch name drawn on top
- Each major group gets a larger gradient label for its `Platform_group` name
- Global font size: **10 pt** for all text
- Output: `FIGURES_DIR / "bubble_chart_batches.svg"` and `"bubble_chart_batches.png"` (dpi=200)

---

## Background data

From the comb_ann counts observed in the notebook:

| Platform_group | Samples | RNA_BATCH count |
|---|---|---|
| Affymetrix Microarray | 3,712 | ~15 batches |
| Illumina NGS | 2,258 | ~8 batches |
| Illumina Microarray | 1,107 | ~3 batches |
| Agilent Microarray | 97 | ~3 batches |
| **Total** | **7,174** | **29 batches** |

Circle radius will be ~0.5 data units; platform groups arranged left-to-right in descending sample count order (largest first). Sub-groups within a platform group are arranged in a rectangular grid layout.

---

## Data flow

```
comb_ann
  └─ groupby(['Platform_group', 'RNA_BATCH']).size()
       └─ build_bubble_chart_data()  →  {platform: {batch: n_samples}}
            └─ for each batch:
                 hex_pack_coords(n)    →  (N, 2) local coords
                 rotate_coords(coords, angle)  →  rotated (N, 2)
                 translate to cluster position
            └─ layout_platform_clusters()  →  master (x, y, color) arrays + bboxes
  └─ plot_bubble_chart()  →  fig
       └─ scatter (one call per Platform_group for speed)
       └─ draw_gradient_label() per batch + per platform group
  └─ fig.savefig(...)
```

---

## Cells to add

All cells go **between** cell `f53a4f0a` (the existing `comb_ann[...]` display) and cell `a468ca0c` (currently empty).

### Cell A — FIGURES_DIR setup

```python
from pathlib import Path

FIGURES_DIR = Path("figures")
FIGURES_DIR.mkdir(exist_ok=True)
```

*Why:* the Introductory notebook has no FIGURES_DIR yet; this mirrors the pattern in `harmonization_metrics_analysis_v2.ipynb` (line 83–84 of that notebook's JSON).*

---

### Cell B — Core geometry helpers

```python
import numpy as np

def hex_pack_coords(n: int, radius: float = 1.0) -> np.ndarray:
    """
    Return (n, 2) array of (x, y) coords for n circles of given radius
    arranged in a hex-close-packed lattice, sorted closest-to-origin first.
    """
    # Generate a grid large enough to hold n points
    grid_size = int(np.ceil(np.sqrt(n) * 1.5)) + 2
    coords = []
    for row in range(-grid_size, grid_size + 1):
        for col in range(-grid_size, grid_size + 1):
            x = col * 2 * radius + (row % 2) * radius
            y = row * np.sqrt(3) * radius
            coords.append((x, y))
    coords = np.array(coords)
    dists = coords[:, 0] ** 2 + coords[:, 1] ** 2
    idx = np.argsort(dists)
    return coords[idx[:n]]


def rotate_coords(coords: np.ndarray, angle_deg: float) -> np.ndarray:
    """Rotate (n, 2) coordinate array by angle_deg degrees around origin."""
    theta = np.radians(angle_deg)
    c, s = np.cos(theta), np.sin(theta)
    R = np.array([[c, -s], [s, c]])
    return coords @ R.T
```

---

### Cell C — Cluster layout engine

```python
from typing import Dict, List, Tuple

def layout_platform_group(
    batch_counts: Dict[str, int],
    rna_batch_palette: Dict[str, str],
    rotation_seed: int = 0,
    circle_radius: float = 0.5,
    cluster_pad: float = 2.5,
    row_pad: float = 4.0,
    cols_per_row: int = 4,
) -> Tuple[np.ndarray, List[str], Dict[str, Tuple[float, float, float, float]]]:
    """
    Lay out all RNA_BATCH sub-clusters for one Platform_group.

    Returns
    -------
    all_xy : (N_total_samples, 2)  absolute x/y positions of every circle
    all_colors : list of N_total_samples hex-color strings
    cluster_bboxes : {batch_name: (x_min, y_min, x_max, y_max)}
    """
    rng = np.random.default_rng(rotation_seed)
    batches = list(batch_counts.keys())
    
    all_xy = []
    all_colors = []
    cluster_bboxes = {}
    
    for idx, batch in enumerate(batches):
        n = batch_counts[batch]
        col = idx % cols_per_row
        row = idx // cols_per_row
        
        # Hex pack, rotate, and translate
        local_xy = hex_pack_coords(n, radius=circle_radius)
        angle = rng.uniform(0, 360)
        local_xy = rotate_coords(local_xy, angle)
        
        # Bounding box of this cluster (used to center within its grid cell)
        span_x = local_xy[:, 0].max() - local_xy[:, 0].min()
        span_y = local_xy[:, 1].max() - local_xy[:, 1].min()
        
        # Grid cell origin (cell size based on worst-case span across all batches)
        # We use the span of this batch for translation; inter-cluster padding added separately
        offset_x = col * (span_x + cluster_pad)
        offset_y = row * (span_y + row_pad)
        
        # Center the cluster in its grid cell
        cx = local_xy[:, 0].mean()
        cy = local_xy[:, 1].mean()
        xy = local_xy - [cx, cy] + [offset_x, offset_y]
        
        all_xy.append(xy)
        color = rna_batch_palette.get(batch, "#aaaaaa")
        all_colors.extend([color] * n)
        
        x_min, y_min = xy[:, 0].min(), xy[:, 1].min()
        x_max, y_max = xy[:, 0].max(), xy[:, 1].max()
        cluster_bboxes[batch] = (x_min, y_min, x_max, y_max)
    
    all_xy = np.vstack(all_xy)
    return all_xy, all_colors, cluster_bboxes
```

**Why `cols_per_row=4`:** the largest platform group (Affymetrix Microarray) has ~15 batches; 4 columns gives a roughly 4×4 grid, which looks balanced. This is a tuneable parameter.

---

### Cell D — Gradient label helper

```python
import matplotlib.patches as patches

def draw_gradient_label(
    ax,
    x_left: float,
    y_center: float,
    cluster_width: float,
    cluster_height: float,
    text: str,
    fontsize: int = 10,
    n_strips: int = 40,
    gradient_fraction: float = 0.45,
    text_color: str = "black",
):
    """
    Draw a white-to-transparent horizontal gradient rectangle over the left
    portion of a cluster, then write text on top (DepMap CCLE style).

    Parameters
    ----------
    ax               : matplotlib Axes
    x_left           : left edge x of the cluster bounding box
    y_center         : vertical center of the cluster
    cluster_width    : width of the cluster bounding box
    cluster_height   : height of the cluster bounding box
    text             : label text to display
    fontsize         : label font size in pt (default 10 per project standard)
    n_strips         : number of thin rectangles composing the gradient
    gradient_fraction: fraction of cluster_width covered by the gradient
    text_color       : text color (default black)
    """
    grad_width = cluster_width * gradient_fraction
    strip_w = grad_width / n_strips
    y_bot = y_center - cluster_height / 2

    for i in range(n_strips):
        alpha = (1.0 - i / n_strips) * 0.88
        rect = patches.Rectangle(
            (x_left + i * strip_w, y_bot),
            strip_w,
            cluster_height,
            color="white",
            alpha=alpha,
            linewidth=0,
            zorder=5,
        )
        ax.add_patch(rect)

    # Text slightly inset from left edge
    ax.text(
        x_left + cluster_width * 0.03,
        y_center,
        text,
        fontsize=fontsize,
        ha="left",
        va="center",
        fontweight="bold",
        color=text_color,
        zorder=6,
    )
```

**Why strip-based gradient (not `imshow`):** `imshow` inserts a rasterized bitmap into SVG, which breaks editability. Drawing N thin `Rectangle` patches is vector-native and stays crisp in Figma/Illustrator. 40 strips is invisible to the eye but fast to render.

---

### Cell E — Main plot function

```python
from matplotlib.colors import to_rgba
import matplotlib.pyplot as plt

PLATFORM_GROUP_ORDER = [
    "Affymetrix Microarray",  # largest → left
    "Illumina NGS",
    "Illumina Microarray",
    "Agilent Microarray",
]

PLATFORM_GROUP_COLORS = {
    "Affymetrix Microarray": "#ff7f0e",
    "Illumina NGS": "#1f77b4",
    "Illumina Microarray": "#9467bd",
    "Agilent Microarray": "#2ca02c",
}

GLOBAL_FONT_SIZE = 10  # pt — shared by all text in this notebook

def plot_bubble_chart(
    comb_ann: "pd.DataFrame",
    rna_batch_palette: Dict[str, str],
    platform_group_order: List[str] = PLATFORM_GROUP_ORDER,
    circle_radius: float = 0.5,
    platform_pad: float = 15.0,
    figsize: Tuple[float, float] = (20, 14),
    cols_per_row: int = 4,
) -> plt.Figure:
    """
    Build the 2-level hexagonally-packed bubble chart (Platform_group → RNA_BATCH).

    Each circle represents one sample.  Sub-groups (RNA_BATCH) are hexagonally
    packed and rotated at distinct angles.  Labels use white-to-transparent
    gradient shading (DepMap CCLE style).  All text is GLOBAL_FONT_SIZE = 10 pt.

    Parameters
    ----------
    comb_ann            : DataFrame with columns RNA_BATCH, Platform_group
    rna_batch_palette   : {batch_name: hex_color}
    platform_group_order: left-to-right order of major groups
    circle_radius       : radius of each sample circle in data units
    platform_pad        : horizontal gap between platform group clusters
    figsize             : figure size in inches
    cols_per_row        : RNA_BATCH sub-clusters per row within a platform group
    """
    # ── 1. Aggregate counts ──────────────────────────────────────────────────
    counts = (
        comb_ann.groupby(["Platform_group", "RNA_BATCH"])
        .size()
        .reset_index(name="n")
    )

    # ── 2. Layout per platform group ─────────────────────────────────────────
    platform_layouts = {}
    for seed_i, pg in enumerate(platform_group_order):
        sub = counts[counts["Platform_group"] == pg]
        if sub.empty:
            continue
        batch_counts = dict(zip(sub["RNA_BATCH"], sub["n"]))
        xy, colors, bboxes = layout_platform_group(
            batch_counts,
            rna_batch_palette,
            rotation_seed=seed_i * 42,
            circle_radius=circle_radius,
            cols_per_row=cols_per_row,
        )
        platform_layouts[pg] = {"xy": xy, "colors": colors, "bboxes": bboxes}

    # ── 3. Translate platform groups to non-overlapping horizontal positions ─
    x_cursor = 0.0
    for pg in platform_group_order:
        if pg not in platform_layouts:
            continue
        xy = platform_layouts[pg]["xy"]
        # Shift so the leftmost point of this platform cluster starts at x_cursor
        x_shift = x_cursor - xy[:, 0].min()
        xy[:, 0] += x_shift
        # Update bboxes accordingly
        for batch in platform_layouts[pg]["bboxes"]:
            bb = platform_layouts[pg]["bboxes"][batch]
            platform_layouts[pg]["bboxes"][batch] = (
                bb[0] + x_shift, bb[1], bb[2] + x_shift, bb[3]
            )
        platform_layouts[pg]["xy"] = xy
        x_cursor = xy[:, 0].max() + platform_pad

    # ── 4. Draw ──────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=figsize)

    for pg in platform_group_order:
        if pg not in platform_layouts:
            continue
        data = platform_layouts[pg]
        xy = data["xy"]
        colors = data["colors"]
        bboxes = data["bboxes"]

        # Scatter all circles for this platform group
        ax.scatter(
            xy[:, 0], xy[:, 1],
            c=colors,
            s=(circle_radius * 72) ** 2 * 0.25,  # approximate pt² from data radius
            linewidths=0,
            zorder=3,
        )

        # Per-batch gradient labels
        for batch, bb in bboxes.items():
            x_min, y_min, x_max, y_max = bb
            cluster_w = x_max - x_min
            cluster_h = y_max - y_min
            draw_gradient_label(
                ax,
                x_left=x_min,
                y_center=(y_min + y_max) / 2,
                cluster_width=cluster_w,
                cluster_height=cluster_h,
                text=batch,
                fontsize=GLOBAL_FONT_SIZE,
            )

        # Platform-group label (larger, at the top of the group bounding box)
        all_xy = xy
        pg_x_min = all_xy[:, 0].min()
        pg_x_max = all_xy[:, 0].max()
        pg_y_min = all_xy[:, 1].min()
        pg_y_max = all_xy[:, 1].max()
        draw_gradient_label(
            ax,
            x_left=pg_x_min,
            y_center=pg_y_max + 3.0,  # sit above the top of the cluster
            cluster_width=pg_x_max - pg_x_min,
            cluster_height=4.0,
            text=pg,
            fontsize=GLOBAL_FONT_SIZE,
            gradient_fraction=0.6,
            text_color=PLATFORM_GROUP_COLORS.get(pg, "black"),
        )

    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("white")
    plt.tight_layout()
    return fig
```

**Key design notes:**
- `ax.scatter` is called **once per Platform_group** (not per batch) to avoid thousands of individual scatter calls — this keeps rendering fast.
- Circle size (`s`) is set via `circle_radius`; it may need tuning after a first render. The formula `(radius * 72)^2 * 0.25` is an initial estimate — adjust if circles overlap or have gaps.
- Platform-group labels are placed **above** the bounding box of each group cluster, also with gradient shading.

---

### Cell F — Execute and save

```python
fig_bubble = plot_bubble_chart(
    comb_ann,
    rna_batch_palette=rna_batch_palette,
    platform_group_order=PLATFORM_GROUP_ORDER,
    circle_radius=0.5,
    platform_pad=15.0,
    figsize=(22, 14),
    cols_per_row=4,
)

fig_bubble.savefig(FIGURES_DIR / "bubble_chart_batches.svg", bbox_inches="tight")
fig_bubble.savefig(FIGURES_DIR / "bubble_chart_batches.png", bbox_inches="tight", dpi=200)
plt.show()
```

---

## Files that do NOT need to change

| File | Reason |
|---|---|
| `harmonization_metrics_analysis_v2.ipynb` | Only the saving pattern is referenced — no edits needed |
| `all_cohorts_assembly.ipynb` | Source of `comb_ann`; not modified |
| `CLAUDE.md` files | No new scripts, constants, or strategies added |

---

## Side effects and caveats

1. **Circle size tuning:** The `s=(circle_radius * 72)**2 * 0.25` formula is a starting estimate. After first render, `circle_radius` and `s` scaling factor may need manual adjustment. The `s` parameter in `ax.scatter` is in **points²**, while `circle_radius` is in **data units** — they are linked to the figure's DPI and axes scale, so visual sizing only matches theory at a specific zoom level. Prefer adjusting `circle_radius` (data units) and fixing `s` to a constant (e.g., `s=4`) to keep circles visually the same size.

2. **Cluster separation (`cluster_pad`, `row_pad`):** Within `layout_platform_group`, the grid cell width is computed per-batch using each batch's own span. This can cause uneven columns if batch sizes differ greatly. If the layout looks ragged, replace per-batch span with `max_span` across all batches in that platform group.

3. **Label overlap:** For small batches (few samples → small cluster), the gradient label text may overflow the circle cluster. Add a `min_cluster_width` guard in `draw_gradient_label` (e.g., `cluster_width = max(cluster_width, 8.0)`).

4. **SVG gradient strips:** 40 white rectangle patches per cluster × ~29 clusters = ~1,160 `<rect>` elements in SVG. This is small and fine for Figma/Illustrator. If SVG becomes slow, reduce `n_strips` to 20.

5. **`GLOBAL_FONT_SIZE = 10`:** This constant must be applied to **all future text in this notebook** (not just the bubble chart). Set it in Cell A as a module-level constant and reference it everywhere.

6. **`FIGURES_DIR`:** Will create `figures_for_article/figures/`. This directory is gitignored if `.gitignore` already ignores `figures/`. Verify with `git status` after first save.

---

## Verification steps

After implementation, run these checks before calling it done:

```python
# Check data aggregation
counts = comb_ann.groupby(['Platform_group', 'RNA_BATCH']).size()
print(counts)
# Should show 4 platform groups, 29 RNA_BATCH entries, totaling 7174

# Check hex packing
xy = hex_pack_coords(100, radius=0.5)
assert xy.shape == (100, 2), f"Expected (100, 2), got {xy.shape}"

# Check rotation is an isometry (preserves distances)
xy_rot = rotate_coords(xy, 45)
assert np.allclose(np.linalg.norm(xy, axis=1), np.linalg.norm(xy_rot, axis=1))

# Check FIGURES_DIR was created and file saved
assert (FIGURES_DIR / "bubble_chart_batches.svg").exists()
assert (FIGURES_DIR / "bubble_chart_batches.png").exists()
```

---

## TODO checklist

- [x] **Cell A** — Add `FIGURES_DIR = Path("figures"); FIGURES_DIR.mkdir(exist_ok=True)` and `GLOBAL_FONT_SIZE = 10` after the existing `comb_ann[...]` display cell
- [x] **Cell B** — Add `hex_pack_coords()` and `rotate_coords()` functions
- [x] **Cell C** — Add `layout_platform_group()` function
- [x] **Cell D** — Add `draw_gradient_label()` function  
- [x] **Cell E** — Add `PLATFORM_GROUP_ORDER`, `PLATFORM_GROUP_COLORS`, `GLOBAL_FONT_SIZE`, and `plot_bubble_chart()` function (also added `min_cluster_width` guard from caveats)
- [x] **Cell F** — Add execution cell: call `plot_bubble_chart()`, save SVG + PNG
- [ ] **Tune** `circle_radius`, `s` (scatter marker size), `cluster_pad`, `row_pad`, `cols_per_row` after first visual render
- [x] **Verify** all text uses `fontsize=GLOBAL_FONT_SIZE` (= 10)
- [ ] **Verify** SVG and PNG written to `figures_for_article/figures/` (requires running the notebook with live S3 data)
- [x] **Check** gradient labels do not overlap on small clusters; `max(cluster_w, 8.0)` guard added in Cell E
- [ ] **Check** platform-group label positions (currently `y_max + 3.0`) — adjust vertical offset if labels clip (requires visual render)
