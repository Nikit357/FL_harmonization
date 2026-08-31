# Implementation Plan — Publication-Grade Computational Pipeline Scheme
**Date:** 2026-06-04  
**Target file:** `figures/pipeline_scheme.svg` + `figures/pipeline_scheme.png`  
**Script:** `pipeline_scheme_figure.py`

---

## Overview

Create a single-column, top-to-bottom publication SVG figure illustrating the full harmonization benchmark pipeline, from raw data ingestion to the final clustermap and best-attempt selection. Each pipeline stage is represented as a styled box with an embedded programmatic icon (mini-chart) plus a label. Stages are connected by annotated arrows. Font size is fixed at 10pt throughout. Output is SVG (vector, Figma-editable) + PNG (200 dpi, review copy).

The figure must conform to the project's visual standard: `svg.fonttype = 'none'`, `pdf.fonttype = 'truetype'`, `figure.dpi = 200`, `sns.set_style("ticks")`.

---

## Pipeline Stages (9 main stages, each = one box)

| # | Stage label | Icon type | Key facts to show |
|---|---|---|---|
| 0 | **Raw Expression Data** | Mini heatmap, rows=batches, striped | ~7,238 samples; 95% variance = RNA_BATCH |
| 1 | **Batch Removal Strategies (14)** | Funnel shape + text list of strategy families | A_confirmed_bad, B–D_extended, E1–E3_mixes, J_ff_only, K_ffpe_only, etc. |
| 2 | **Imputation (3 methods)** | Matrix with grey missing-value cells → filled matrix | strict (no imputation / drop-NA), KNN, softimpute |
| 3 | **Log₂ Transform** | Small log-curve plot (x → log₂(x+1)) | Per-cohort log transform; threshold=30 |
| 4 | **Harmonization (39 methods)** | BEFORE PCA scatter (4 clustered batches) → arrow → AFTER PCA scatter (mixed) | Methods grouped by family (QN, ComBat, SVA, MNN, FSQN, etc.) |
| 5 | **Post-Removal (post0 / post1)** | Binary fork: two branches recombining | post0 = keep all batches; post1 = remove mono-platform batches |
| 6 | **Metrics Computation (11 groups A–K)** | Sub-box grid: 7 metric-group tiles, each with its own mini-icon | Global / Local / Biology / Embedding / Distribution / Composite / Quality |
| 7 | **Polarity Setting** | Two mini-scatter plots: batch mixing = good, biology mixing = bad | Invert metrics where lower = better (PCR, R², kBET rejection) |
| 8 | **Clustermap + Best Selection** | Mini heatmap with row+col dendrograms; top row highlighted | 3,835 attempts; top attempts highlighted in gold |

---

## Metric Group Tiles (Stage 6)

Seven coloured tiles inside a "Metrics" super-box. Each tile has a dedicated mini-icon (tiny matplotlib inset axis) plus a group letter label and short description.

| Tile | Groups | Mini-icon | Colour |
|---|---|---|---|
| **Global (PCA)** | A, J | Bar chart: PC1–PC3 variance bars, first bar tall (raw) vs first bar short (harmonized) | `#4A90D9` (steel blue) |
| **Local neighbours** | B | kNN circle graph: 4 coloured nodes (= batches), edges between same-colour nodes → inter-colour edges (mixed) | `#E05C5C` (soft red) |
| **Biology preservation** | G, H | Two-cluster scatter: two tight groups coloured by diagnosis (DLBCL red / FL blue) | `#27AE60` (green) |
| **Embedding** | C | UMAP-like scatter with centroid triangles marked on top of point cloud | `#9B59B6` (purple) |
| **Distribution** | D, F | Two overlapping KDE curves (batch 1 and batch 2) converging after harmonization | `#F39C12` (amber) |
| **Composite (WaterMelon)** | I | Donut chart: two segments labelled "Batch" (dark) and "Biology" (light) | `#1ABC9C` (teal) |
| **Data quality** | E, K | Horizontal bar chart with green/grey fill, last bar = NA rate | `#95A5A6` (grey-blue) |

---

## Layout Geometry

Figure dimensions: **10 cm wide × 20 cm tall** (between 1/4 and 1/2 of A4, suitable as a panel in a Nature-like multipanel figure; 90–100 mm width fits single-column Nature format).  
Coordinate system: normalised figure coordinates (0–1) for box placement.

```
┌──────────────────────────────────────┐
│  [0] Raw Expression Data (heatmap)   │  y ≈ 0.92
│              ↓                       │
│  [1] Batch Removal Strategies (14)   │  y ≈ 0.80  ← funnel icon + family list
│              ↓                       │
│  [2] Imputation (3 methods)          │  y ≈ 0.70  ← matrix before/after icon
│              ↓                       │
│  [3] Log₂ Transform per cohort       │  y ≈ 0.61  ← log curve
│              ↓                       │
│  [4] 39 Harmonization Methods        │  y ≈ 0.49  ← PCA before→after (key icon)
│              ↓                       │
│  [5] Post-Removal (post0 / post1)    │  y ≈ 0.39  ← dual-branch diagram
│              ↓                       │
│  [6] Metrics Computation (A–K)       │  y ≈ 0.22  ← 7-tile grid sub-box
│              ↓                       │
│  [7] Polarity Setting                │  y ≈ 0.12  ← batch-good / biology-bad scatters
│              ↓                       │
│  [8] Clustermap + Best Selection     │  y ≈ 0.02  ← heatmap+dendrogram icon
└──────────────────────────────────────┘
```

Box height varies by stage complexity:
- Stages 0, 2, 3, 5: compact (h ≈ 0.07)
- Stages 1, 4: medium (h ≈ 0.09)
- Stage 6: tall with sub-tiles (h ≈ 0.14)
- Stage 7: medium (h ≈ 0.09) — two side-by-side scatters need space
- Stage 8: medium-tall (h ≈ 0.09)

---

## Visual Conventions

### Box style
```python
FancyBboxPatch(
    xy=(x0, y0), width=w, height=h,
    boxstyle="round,pad=0.01",
    facecolor="#F7F9FC",       # very light blue-grey
    edgecolor="#2C3E50",       # dark navy border
    linewidth=0.8,
    zorder=2
)
```

### Icon inset axes
Each box contains one or more `fig.add_axes([x, y, w, h])` sub-axes positioned to the left third of the box.  
Icon axes have no visible spines (all `ax.spines[…].set_visible(False)`), no ticks, no labels.

### Arrow style
```python
ax_main.annotate(
    "", xy=(x_to, y_to), xytext=(x_from, y_from),
    arrowprops=dict(
        arrowstyle="-|>",
        color="#2C3E50",
        lw=1.2,
        connectionstyle="arc3,rad=0.0",
    ),
    zorder=3,
)
```

### Colours
- **Temperature-Split** from project palette: normal/cold=`#3498DB`; cancer/warm=`#E74C3C`
- **Batch colours** (5 representative batches): use tab10 palette for the PCA icon
- Box fill: `#F7F9FC`; headers: bold, `#2C3E50`

---

## Icon Specifications

### Stage 0 — Raw Data heatmap icon
```python
# 8 rows × 6 cols: horizontal stripes representing batch blocks
data = np.zeros((8, 6))
data[0:2, :] = 0.9; data[2:4, :] = 0.4; data[4:6, :] = 0.7; data[6:8, :] = 0.2
ax.imshow(data, aspect='auto', cmap='RdYlBu_r', interpolation='nearest')
# annotation: "95% variance = RNA_BATCH" in red beneath the icon
```

### Stage 1 — Funnel icon
```python
# Draw a trapezoid (funnel) using matplotlib.patches.Polygon
# Wide top, narrow bottom; light blue fill
# Then show "14 strategies" label and abbreviated list (A, B, C, D, E1-E3, F-K)
```

### Stage 2 — Matrix imputation icon
```python
# 4×4 grid; grey = missing, white/filled = present
# Left matrix: ~30% grey cells
# Right matrix: all white (no missing)
# Arrow between them labelled "KNN / softimpute / strict"
```

### Stage 3 — Log transform icon
```python
x = np.linspace(0, 100, 100)
y = np.log2(x + 1)
ax.plot(x, y, color='#2C3E50', lw=1.5)
ax.set_xlabel("x", fontsize=FONT); ax.set_ylabel("log₂(x+1)", fontsize=FONT)
```

### Stage 4 — PCA Before/After icon (KEY ICON)
Two sub-axes side by side within the box, connected by an arrow.

**Before sub-axis (left):** 4 tight clusters coloured by batch (tab10)
```python
np.random.seed(42)
centers = [(-2, -2), (2, -2), (-2, 2), (2, 2)]
for i, (cx, cy) in enumerate(centers):
    pts = np.random.randn(30, 2) * 0.4 + [cx, cy]
    ax_before.scatter(pts[:, 0], pts[:, 1], c=[colors[i]]*30, s=4, alpha=0.8)
ax_before.set_title("Before", fontsize=FONT, color='#E74C3C')
```

**After sub-axis (right):** same coloured points but scattered uniformly
```python
np.random.seed(99)
for i in range(4):
    pts = np.random.randn(30, 2) * 1.2
    ax_after.scatter(pts[:, 0], pts[:, 1], c=[colors[i]]*30, s=4, alpha=0.8)
ax_after.set_title("After", fontsize=FONT, color='#27AE60')
```

**Arrow label:** "39 methods" between the two sub-axes.  
Below the icon: a multi-column text block listing method families:
```
QN family (5)  |  ComBat family (6)  |  SVA-based (4)  |  MNN (3)
FSQN/FSMVN (3)  |  Harmony/Scanorama (3)  |  RUV-based (3)  |  Others (12)
```

### Stage 5 — Post-removal fork
```python
# Two horizontal branches from a central point:
# Left: "post0 — keep all batches"
# Right: "post1 — remove mono-platform batches"
# Both branches converge to a single point below
# Use FancyArrowPatch for each branch
```

### Stage 6 — Metric group tiles (7 tiles, each with its own mini-icon)

Seven equally-sized tiles in a 4-column grid (4 on top row, 3 on bottom row) within a larger bounding box. Each tile is a `FancyBboxPatch` with a distinct fill color, a bold group-letter label, and a tiny matplotlib inset axis showing the dedicated icon described below.

**Tile 1 — Global (PCA), groups A + J, colour `#4A90D9`:**
```python
# Bar chart with 3 bars: bar heights = [0.85, 0.3, 0.1] (PC1, PC2, PC3)
# Represents high PC1 variance = batch-dominated expression
ax.bar([0,1,2], [0.85, 0.3, 0.1], color='#4A90D9', width=0.7)
ax.set_ylabel("Var. expl.", fontsize=FONT-2)
```

**Tile 2 — Local neighbours, group B, colour `#E05C5C`:**
```python
# 4 nodes in a square arrangement, coloured by 4 batches
# Edges between adjacent nodes shown as grey lines
# Conceptual: a kNN neighbourhood graph
node_colors = ['#E74C3C','#3498DB','#27AE60','#F39C12']
for j, (nx, ny) in enumerate([(0,0),(1,0),(0,1),(1,1)]):
    ax.scatter(nx, ny, c=node_colors[j], s=30, zorder=3)
# draw edges between all 4 nodes
for (a, b) in [(0,1),(0,2),(1,3),(2,3),(0,3)]:
    ax.plot(...)
```

**Tile 3 — Biology preservation, groups G + H, colour `#27AE60`:**
```python
# Two tight clusters: DLBCL (red) and FL (blue), well-separated
np.random.seed(7)
ax.scatter(*np.random.randn(30,2).T * 0.4 + [-1, 0], c='#E74C3C', s=4, alpha=0.8)
ax.scatter(*np.random.randn(30,2).T * 0.4 + [+1, 0], c='#3498DB', s=4, alpha=0.8)
```

**Tile 4 — Embedding, group C, colour `#9B59B6`:**
```python
# UMAP-like scatter: 2 interleaved clouds with triangle centroid markers
np.random.seed(11)
ax.scatter(*np.random.randn(40,2).T, c='#9B59B6', s=3, alpha=0.5)
ax.scatter([0], [0], marker='^', c='#2C3E50', s=20, zorder=4)  # centroid
```

**Tile 5 — Distribution, groups D + F, colour `#F39C12`:**
```python
# Two overlapping KDE-like curves (batch 1 and batch 2)
x = np.linspace(-3, 3, 80)
ax.fill_between(x, 0, np.exp(-0.5*(x-0.8)**2), alpha=0.5, color='#E74C3C')
ax.fill_between(x, 0, np.exp(-0.5*(x+0.8)**2), alpha=0.5, color='#3498DB')
```

**Tile 6 — Composite (WaterMelon), group I, colour `#1ABC9C`:**
```python
# Donut chart: two segments "Batch" (small, dark) and "Biology" (large, light)
ax.pie([0.35, 0.65], colors=['#2C3E50','#1ABC9C'], startangle=90,
       wedgeprops=dict(width=0.5))
```

**Tile 7 — Data quality, groups E + K, colour `#95A5A6`:**
```python
# Horizontal bars: samples, genes, NA fraction
ax.barh([0,1,2], [0.9, 0.8, 0.05], color=['#27AE60','#27AE60','#E74C3C'])
```

### Stage 7 — Polarity setting (two conceptual mini-scatter plots)

The polarity stage uses **two side-by-side mini-scatter plots** to visually explain which direction is good for batch metrics vs biology metrics.

**Left sub-axis — "Batch mixing = GOOD":**
```python
# Points coloured by batch (4 colours), uniformly scattered → no clustering
# Green checkmark annotation in the corner
np.random.seed(13)
for i, col in enumerate(['#E74C3C','#3498DB','#27AE60','#F39C12']):
    pts = np.random.randn(20, 2) * 1.3
    ax_batch.scatter(pts[:,0], pts[:,1], c=col, s=4, alpha=0.7)
ax_batch.set_title("Batch mixing\n= GOOD ↑", fontsize=FONT-1, color='#27AE60')
```

**Right sub-axis — "Biology loss = BAD":**
```python
# Points coloured by diagnosis (DLBCL red / FL blue / Normal grey), uniformly scattered
# No separation visible between groups → biology destroyed → red cross annotation
np.random.seed(17)
for col in ['#E74C3C','#3498DB','#95A5A6']:
    pts = np.random.randn(20, 2) * 1.3
    ax_bio.scatter(pts[:,0], pts[:,1], c=col, s=4, alpha=0.7)
ax_bio.set_title("Biology mixing\n= BAD ↓", fontsize=FONT-1, color='#E74C3C')
```

**Text block below both sub-axes:**
```
Inverted (↑ = better):  kBET rejection rate, PCR, R²(batch)
As-is (↑ = better):     iLISI, ASW_bio, cLISI, graph connectivity, WM ratio
```

### Stage 8 — Clustermap icon
```python
# Mini heatmap: 8 rows × 12 cols
# Colour: RdYlBu, values random in [0,1]
# Top 2 rows coloured gold/yellow to mark "best attempts"
# Horizontal dendrogram above, vertical dendrogram to left (stub lines only)
# Annotation: "3,835 attempts → top N highlighted"
```

---

## Script Structure

```
pipeline_scheme_figure.py
├── Constants (FONT, figure dims, colors)
├── Helper functions:
│   ├── draw_stage_box(fig, ax_main, x0, y0, w, h, title, subtitle)
│   ├── draw_connecting_arrow(ax_main, x_from, y_from, x_to, y_to, label="")
│   ├── draw_raw_data_icon(fig, rect)
│   ├── draw_strategies_icon(fig, rect)
│   ├── draw_imputation_icon(fig, rect)
│   ├── draw_log_transform_icon(fig, rect)
│   ├── draw_harmonization_icon(fig, rect)   ← PCA before/after
│   ├── draw_post_removal_icon(fig, rect)
│   ├── draw_metrics_icon(fig, rect)         ← 7-tile grid, each tile with own icon
│   ├── draw_polarity_icon(fig, rect)        ← two mini-scatters: batch-good/bio-bad
│   └── draw_clustermap_icon(fig, rect)
├── Main:
│   ├── Set rcParams (svg.fonttype='none', pdf.fonttype='truetype', dpi=200)
│   ├── fig = plt.figure(figsize=(10/2.54, 20/2.54))  # 10 × 20 cm → inches
│   ├── ax_main = fig.add_axes([0, 0, 1, 1])          # full-figure axis for boxes/arrows
│   ├── Draw all 9 stage boxes (top → bottom)
│   ├── Draw all 8 connecting arrows
│   └── Save: figures/pipeline_scheme.svg + figures/pipeline_scheme.png
```

---

## Files to Create / Change

### New file: `pipeline_scheme_figure.py`
- Location: `~/FL_harmonization/figures_for_article/pipeline_scheme_figure.py`
- Standalone script; no Jupyter required.
- Dependencies: `matplotlib`, `numpy`, `pathlib` — all available in the project venv.

### Outputs (created by the script)
- `figures/pipeline_scheme.svg` — vector output for Figma / journal submission
- `figures/pipeline_scheme.png` — 200 dpi raster for quick review

### No changes needed
- `Introductory_figures_for_article.ipynb` — separate notebook, not modified
- Any harmonization-scripts files — this is a visualisation-only script
- `CLAUDE.md` (this dir) — updated: pipeline_scheme row added to figure table

---

## Side Effects and Caveats

1. **Font availability**: The script uses matplotlib's default font. If BostonGene requires Arial or Helvetica specifically, a `plt.rcParams['font.family'] = 'Arial'` line should be added and verified on the rendering machine.
2. **SVG size**: A rich figure with 9 embedded sub-axes may produce a ~500 KB SVG. This is acceptable for Figma but may slow down text editors.
3. **Reproducibility**: All random data in icons must use `np.random.seed(N)` to ensure stable renders across runs.
4. **Figure dimensions**: 10 cm × 20 cm targets the 1/4–1/2 A4 range for a Nature-like multipanel figure. Rescale `figsize` proportionally if the journal requires a different panel width.
5. **GLOBAL_FONT_SIZE = 10**: Applied to every `fontsize=` argument, including icon axis labels and tile text. Tile sub-labels may use `FONT - 2` = 8pt where space is tight.

---

## Verification

```bash
source ~/venvs/collagen_3_11/bin/activate
cd ~/FL_harmonization/figures_for_article
python pipeline_scheme_figure.py
# Expected: no errors; figures/pipeline_scheme.svg and .png created
ls -lh figures/pipeline_scheme.*
# Check SVG is valid XML:
python -c "import xml.etree.ElementTree as ET; ET.parse('figures/pipeline_scheme.svg'); print('SVG OK')"
```

---

## TODO Checklist

### Done (in pipeline_scheme_figure.py as of 2026-06-05)

- [x] Create `pipeline_scheme_figure.py` with rcParams block, FONT constant (`= 10`), and FIGURES_DIR
- [x] Set `figsize=(10/2.54, 20/2.54)` (10 cm × 20 cm for Nature-like multipanel)
- [x] Implement `draw_stage_box()` helper using `FancyBboxPatch`
- [x] Implement `draw_connecting_arrow()` helper using `ax.annotate`
- [x] Define `STAGES` list — all 9 entries with (x0, y0, w, h, title, subtitle)
- [x] Define `TILE_COLORS` dict — one colour per metric group family
- [x] Pre-compute `ARROWS` — tail = bottom of box i, head = top of box i+1 (correct direction)
- [x] Implement `_icon_rect()` helper — returns [left, bottom, w, h] in figure fractions for a given stage index
- [x] Assemble main figure: draw all 9 boxes + 8 arrows in correct vertical positions
- [x] Add stage subtitles (sample counts, method counts) in smaller grey text — encoded in STAGES, rendered by draw_stage_box
- [x] Save both SVG and PNG outputs to `figures/`

### Still to implement

- [x] **`draw_raw_data_icon(fig, rect)`** — Stage 0: 8×6 striped heatmap (horizontal batch blocks), `RdYlBu_r` cmap, no axes, annotation "95% variance = RNA_BATCH"
- [x] **`draw_strategies_icon(fig, rect)`** — Stage 1: trapezoid funnel (Polygon patch, wide-top narrow-bottom) + abbreviated strategy family labels (A, B, C–D, E1–E3, F–K) inside or beside funnel
- [x] **`draw_imputation_icon(fig, rect)`** — Stage 2: two 4×4 grid matrices side by side; left ~30% grey (missing) cells; right all white; small arrow between them; transparent overlay axis used for the inter-matrix arrow
- [x] **`draw_log_transform_icon(fig, rect)`** — Stage 3: single log₂(x+1) curve (x 0–100), minimal left+bottom spines, no ticks, grey axis labels
- [x] **`draw_harmonization_icon(fig, rect)`** — Stage 4: two sub-axes (before: 4 tight clusters by tab10 colours; after: same colours uniformly scattered); transparent overlay with arrow + "39\nmethods" label; method-family text already in box subtitle
- [x] **`draw_post_removal_icon(fig, rect)`** — Stage 5: Y-fork — stem + dot at fork point; left arrow (COLD_BLUE) → "post0"; right arrow (WARM_RED) → "post1"
- [x] **`draw_metrics_icon(fig, rect)`** — Stage 6: 7 coloured tiles in a 4+3 grid; each tile is a FancyBboxPatch with its own `fig.add_axes` mini-icon:
  - Tile 1 Global (A,J) `#4A90D9`: bar chart PC1–PC3 heights [0.85,0.3,0.1]
  - Tile 2 Local (B) `#E05C5C`: 4 coloured nodes + edges (kNN neighbourhood)
  - Tile 3 Biology (G,H) `#27AE60`: two-cluster scatter (DLBCL red / FL blue)
  - Tile 4 Embedding (C) `#9B59B6`: UMAP-like scatter + centroid triangle marker
  - Tile 5 Distribution (D,F) `#F39C12`: two overlapping filled KDE curves
  - Tile 6 Composite (I) `#1ABC9C`: donut chart ("Batch" dark / "Biology" light)
  - Tile 7 Quality (E,K) `#95A5A6`: horizontal bars (samples, genes, NA rate)
  - Layout: transparent full-figure overlay `ax_bg` for backgrounds+labels; `add_mini_ax` inner helper; bottom row centred with `(tile_w + GAP_X) / 2` offset
- [x] **`draw_polarity_icon(fig, rect)`** — Stage 7: two scatter sub-axes side by side (42%/16%gap/42% split); left = 4 batch colours uniformly scattered, "Batch ↑" green label; right = 3 diagnosis colours uniformly scattered, "Biology ↓" red label
- [x] **`draw_clustermap_icon(fig, rect)`** — Stage 8: 8×12 `RdYlBu_r` heatmap + `#FFD700` Rectangle overlay on top 2 rows (alpha=0.45) + ∩-bracket stubs in `ax_dtop` + ⊏-bracket stubs in `ax_dleft`
- [x] **Wire all icon functions into `main`** — all 9 stages wired
- [x] Verify SVG is well-formed XML — `SVG OK` confirmed
- [x] Update `CLAUDE.md` figure table to include `pipeline_scheme.svg`
