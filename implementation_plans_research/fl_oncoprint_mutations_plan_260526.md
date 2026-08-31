# OncoPrint / Waterfall Plot for FL Somatic Mutations — Implementation Plan

**Date:** 2026-05-26  
**Author:** Claude Code (for review by Daniil Nikitin)

---

## Overview

Add a publication-quality OncoPrint (waterfall plot) to the FL dissertation project visualizing
somatic mutation data from a MAF file. The plot will show the most frequently mutated genes
across FL samples as a genes × samples grid with per-cell mutation-type coloring, a top-bar
for total mutation burden (TMB), a right-bar for per-gene mutation frequency (%), and optional
annotation tracks below for clinical variables from `MDA_Strati_FL_annotation.csv` (FLIPI, POD24,
FL subtype).

**Why:** OncoPrints are a standard figure in lymphoma genomics papers (used in all major FL
subtype publications, e.g., Cottereau 2023, Schmitz 2018). Including one for this dataset will
be required for the dissertation manuscript.

**Key design decision:** Python-native matplotlib implementation (vs R maftools via rpy2).
Rationale in the section below.

---

## Library / Approach Comparison

| Approach | Pros | Cons | Verdict |
|---|---|---|---|
| **Custom matplotlib** (recommended) | Full style control; native PDF/SVG; integrates with the notebook color palettes; no new dependencies | ~150 lines of plotting boilerplate | **Use this** |
| R `maftools` via rpy2 | OncoPrint built-in, co-occurrence analysis, lollipop plots included | R dependency; PDF fonts differ from project style; hard to customize exactly; rpy2 overhead | Alternative if more maftools features are needed later |
| `pyoncoprint` PyPI package | Less boilerplate | Poorly maintained; uncertain Python 3.11 compatibility; fewer annotation options | Avoid |

---

## Expected Input File Format

The MAF file is a tab-separated text file (standard TCGA/GDC format). Mandatory columns used by
this script:

| Column | Description |
|---|---|
| `Hugo_Symbol` | HGNC gene symbol |
| `Variant_Classification` | Mutation type (see colour map below) |
| `Tumor_Sample_Barcode` | Sample identifier matching annotation files |

Optional columns preserved but not plotted:
`Chromosome`, `Start_Position`, `End_Position`, `Reference_Allele`, `Tumor_Seq_Allele2`,
`t_alt_count`, `t_ref_count`, `VAF`.

**Expected file location after user upload:**
`~/FL_harmonization/data/fl_somatic_mutations.maf`
(or any path; configured via `MAF_PATH` constant at top of notebook).

---

## Plot Layout

```
┌──────────────────────────────────────────────────────────────┐
│  [Top axis: TMB bar — total mutations per sample]            │
├──────────────────────────────────────────────────────────────┤
│  [OncoPrint grid]                                │  [% bar]  │
│  rows = genes (sorted by frequency ↓)           │  (right)  │
│  cols = samples (sorted by TMB ↓)               │           │
├──────────────────────────────────────────────────────────────┤
│  [Annotation track: FLIPI score]                             │
│  [Annotation track: POD24 status]                            │
│  [Annotation track: FL grade / subtype]                      │
└──────────────────────────────────────────────────────────────┘
```

Cell encoding (within each tile):
- **One mutation type** → solid coloured rectangle spanning the cell
- **Multi-hit** (≥2 mutation types in same gene/sample) → black tile

---

## Mutation Type Colour Map

These are the standard OncoPrint colours used in cBioPortal and most FL papers:

```python
MUTATION_COLORS = {
    "Missense_Mutation":         "#008000",   # green
    "Nonsense_Mutation":         "#FF0000",   # red
    "Frame_Shift_Del":           "#FF0000",   # red
    "Frame_Shift_Ins":           "#FF69B4",   # hot pink
    "Splice_Site":               "#FFA500",   # orange
    "In_Frame_Del":              "#8B4513",   # brown
    "In_Frame_Ins":              "#ADD8E6",   # light blue
    "Translation_Start_Site":    "#800080",   # purple
    "Nonstop_Mutation":          "#CC0000",   # dark red
    "Multi_Hit":                 "#000000",   # black
    "Silent":                    "#BEBEBE",   # grey (excluded by default)
}
```

---

## Background / Reference Data

Clinical annotations available in `MDA_Strati_FL_annotation.csv`:

| Column | Values | Used in track |
|---|---|---|
| `FLIPI` (numeric) | 0–5 | Continuous colour bar |
| `POD24` | 0 / 1 | Binary (red/blue) |
| `DIAGNOSIS` / `Diagnosis_cell_type` | FL grades | Categorical |
| `OS_FLAG`, `PFS_FLAG` | 0 / 1 | Optional |

Sample-ID matching key: `Tumor_Sample_Barcode` (MAF) ↔ `Sample ID` (annotation CSV).
This join must be verified once the MAF is available — the exact column may differ.

---

## Files to Create / Change

### 1. New notebook — `fl_somatic_mutations_oncoprint.ipynb`

**Location:** `~/FL_harmonization/`

This is a new Jupyter notebook with the following cells:

#### 1a. Configuration cell (constants)

```python
# ── Configuration ──────────────────────────────────────────────────────────
MAF_PATH = "data/fl_somatic_mutations.maf"   # adjust after upload
ANN_PATH = "MDA_Strati_FL_annotation.csv"
OUTPUT_DIR = "plots"

TOP_N_GENES = 30        # genes shown in the OncoPrint (most-mutated)
MIN_FREQ_PERCENT = 2.0  # hide genes mutated in < 2% of samples
EXCLUDE_SILENT = True   # drop Silent / 3'UTR / 5'UTR / Intron variants
SAMPLE_ID_COLUMN_MAF = "Tumor_Sample_Barcode"     # column in MAF
SAMPLE_ID_COLUMN_ANN = "Sample ID"                # column in annotation CSV

# Annotation tracks to show below the grid (must exist in ANN_PATH)
ANNOTATION_TRACKS = ["FLIPI", "POD24"]

FIGSIZE = (18, 10)
GLOBAL_FONT_SIZE = 11
```

#### 1b. Data loading and validation cell

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import seaborn as sns
from pathlib import Path

plt.rcParams["pdf.fonttype"] = "truetype"
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["figure.dpi"] = 200
sns.set_style("ticks")
plt.rcParams["font.size"] = GLOBAL_FONT_SIZE

maf_df = pd.read_csv(MAF_PATH, sep="\t", comment="#", low_memory=False)

# Validate required columns exist
required_cols = ["Hugo_Symbol", "Variant_Classification", SAMPLE_ID_COLUMN_MAF]
missing = [c for c in required_cols if c not in maf_df.columns]
if missing:
    raise ValueError(f"MAF missing required columns: {missing}")

print(f"Loaded {len(maf_df):,} mutations across "
      f"{maf_df[SAMPLE_ID_COLUMN_MAF].nunique()} samples "
      f"and {maf_df['Hugo_Symbol'].nunique()} genes")
print("\nVariant_Classification counts:")
print(maf_df["Variant_Classification"].value_counts())
```

#### 1c. Filtering and matrix building cell

```python
# Variant types classified as non-silent (standard oncoPrint convention)
SILENT_TYPES = {
    "Silent", "3'UTR", "5'UTR", "3'Flank", "5'Flank",
    "Intron", "RNA", "IGR", "lincRNA",
}

if EXCLUDE_SILENT:
    maf_filtered = maf_df[~maf_df["Variant_Classification"].isin(SILENT_TYPES)].copy()
else:
    maf_filtered = maf_df.copy()

print(f"After filtering: {len(maf_filtered):,} non-silent mutations")

# Aggregate: for each (gene, sample) pair collect all variant types
agg = (
    maf_filtered
    .groupby(["Hugo_Symbol", SAMPLE_ID_COLUMN_MAF])["Variant_Classification"]
    .apply(lambda x: "Multi_Hit" if len(set(x)) > 1 else x.iloc[0])
    .reset_index()
    .rename(columns={"Variant_Classification": "mut_type"})
)

# Pivot to genes × samples matrix (None = wild-type)
mut_matrix = agg.pivot(
    index="Hugo_Symbol",
    columns=SAMPLE_ID_COLUMN_MAF,
    values="mut_type",
)
all_samples = maf_filtered[SAMPLE_ID_COLUMN_MAF].unique()
mut_matrix = mut_matrix.reindex(columns=all_samples)

# Gene mutation frequency
gene_freq = mut_matrix.notna().mean(axis=1) * 100  # % of samples
gene_freq = gene_freq.sort_values(ascending=False)

# Filter by minimum frequency and keep top N
gene_freq = gene_freq[gene_freq >= MIN_FREQ_PERCENT]
top_genes = gene_freq.head(TOP_N_GENES).index.tolist()
mut_matrix = mut_matrix.loc[top_genes]
gene_freq = gene_freq.loc[top_genes]

# Sample mutation burden (TMB proxy: total non-silent mutations per sample)
tmb = maf_filtered.groupby(SAMPLE_ID_COLUMN_MAF).size()
tmb = tmb.reindex(all_samples, fill_value=0)

# Sort samples by TMB descending
sample_order = tmb.sort_values(ascending=False).index.tolist()
mut_matrix = mut_matrix[sample_order]
tmb = tmb[sample_order]

print(f"\nPlotting {len(top_genes)} genes × {len(sample_order)} samples")
print(f"Top 5 mutated genes:\n{gene_freq.head()}")
```

#### 1d. Load and align sample annotations cell

```python
ann_df = pd.read_csv(ANN_PATH)

# Align annotation to sample order
ann_aligned = ann_df.set_index(SAMPLE_ID_COLUMN_ANN).reindex(sample_order)

# For each annotation track, determine if it is categorical or numeric
def classify_track(series):
    """Return 'numeric' or 'categorical'."""
    if pd.api.types.is_numeric_dtype(series) and series.nunique() > 5:
        return "numeric"
    return "categorical"

track_types = {col: classify_track(ann_aligned[col]) for col in ANNOTATION_TRACKS
               if col in ann_aligned.columns}
missing_tracks = [col for col in ANNOTATION_TRACKS if col not in ann_aligned.columns]
if missing_tracks:
    print(f"Warning: annotation tracks not found in CSV: {missing_tracks}")
```

#### 1e. Plotting cell (core OncoPrint)

```python
MUTATION_COLORS = {
    "Missense_Mutation":         "#008000",
    "Nonsense_Mutation":         "#FF0000",
    "Frame_Shift_Del":           "#FF0000",
    "Frame_Shift_Ins":           "#FF69B4",
    "Splice_Site":               "#FFA500",
    "In_Frame_Del":              "#8B4513",
    "In_Frame_Ins":              "#ADD8E6",
    "Translation_Start_Site":    "#800080",
    "Nonstop_Mutation":          "#CC0000",
    "Multi_Hit":                 "#000000",
    "Silent":                    "#BEBEBE",
}
WILDTYPE_COLOR = "#E8E8E8"  # light grey background for wild-type cells

n_genes = len(top_genes)
n_samples = len(sample_order)
n_tracks = len([t for t in ANNOTATION_TRACKS if t in ann_aligned.columns])

# GridSpec: row 0 = TMB bar, row 1 = main grid, rows 2+ = annotation tracks
height_ratios = [1.5] + [n_genes * 0.35] + [0.4] * n_tracks
fig = plt.figure(figsize=FIGSIZE)
gs = GridSpec(
    nrows=2 + n_tracks,
    ncols=2,
    height_ratios=height_ratios,
    width_ratios=[n_samples * 0.18, 2.5],
    hspace=0.05,
    wspace=0.03,
)

ax_tmb   = fig.add_subplot(gs[0, 0])   # top bar: TMB
ax_main  = fig.add_subplot(gs[1, 0])   # OncoPrint grid
ax_freq  = fig.add_subplot(gs[1, 1])   # right bar: gene frequency

# ── TMB bar ──────────────────────────────────────────────────────────────────
ax_tmb.bar(range(n_samples), tmb.values, color="#555555", width=0.9)
ax_tmb.set_xlim(-0.5, n_samples - 0.5)
ax_tmb.set_ylabel("TMB\n(mutations)", fontsize=GLOBAL_FONT_SIZE - 1)
ax_tmb.set_xticks([])
ax_tmb.spines[["bottom", "right", "top"]].set_visible(False)

# ── Main OncoPrint grid ───────────────────────────────────────────────────────
# Draw wild-type background
ax_main.imshow(
    np.zeros((n_genes, n_samples)),
    aspect="auto",
    cmap="Greys",
    vmin=0, vmax=1,
    alpha=0.08,
)

TILE_HEIGHT = 0.7  # fraction of cell height for mutation tiles
for row_idx, gene in enumerate(top_genes):
    for col_idx, sample in enumerate(sample_order):
        mut = mut_matrix.at[gene, sample]
        if pd.isna(mut):
            continue
        color = MUTATION_COLORS.get(mut, "#888888")
        rect = mpatches.FancyBboxPatch(
            (col_idx - 0.45, row_idx - TILE_HEIGHT / 2),
            width=0.9,
            height=TILE_HEIGHT,
            boxstyle="square,pad=0",
            facecolor=color,
            edgecolor="none",
            linewidth=0,
        )
        ax_main.add_patch(rect)

ax_main.set_xlim(-0.5, n_samples - 0.5)
ax_main.set_ylim(-0.5, n_genes - 0.5)
ax_main.set_yticks(range(n_genes))
ax_main.set_yticklabels(top_genes, fontsize=GLOBAL_FONT_SIZE - 1)
ax_main.set_xticks([])
ax_main.invert_yaxis()
ax_main.spines[["bottom", "right", "top", "left"]].set_visible(False)

# ── Gene frequency bar ────────────────────────────────────────────────────────
ax_freq.barh(
    range(n_genes),
    gene_freq.values,
    color="#444444",
    height=0.65,
)
ax_freq.set_ylim(-0.5, n_genes - 0.5)
ax_freq.invert_yaxis()
ax_freq.set_yticks([])
ax_freq.set_xlabel("% mutated", fontsize=GLOBAL_FONT_SIZE - 1)
ax_freq.spines[["left", "top"]].set_visible(False)
ax_freq.xaxis.set_label_position("bottom")

# ── Annotation tracks ─────────────────────────────────────────────────────────
ANNOT_CMAPS = {
    "FLIPI":  "YlOrRd",
    "POD24":  {0: "#4393C3", 1: "#D6604D", np.nan: "#CCCCCC"},  # binary
}

for track_idx, col in enumerate([t for t in ANNOTATION_TRACKS
                                  if t in ann_aligned.columns]):
    ax_ann = fig.add_subplot(gs[2 + track_idx, 0])
    series = ann_aligned[col]

    if track_types[col] == "numeric":
        cmap = plt.get_cmap(ANNOT_CMAPS.get(col, "viridis"))
        vmin, vmax = series.min(), series.max()
        colors = [cmap((v - vmin) / (vmax - vmin)) if not pd.isna(v)
                  else (0.8, 0.8, 0.8, 1.0)
                  for v in series.values]
    else:
        palette = ANNOT_CMAPS.get(col, {})
        uniq = series.dropna().unique()
        if not palette:
            tab_colors = plt.get_cmap("tab10").colors
            palette = {v: tab_colors[i % 10] for i, v in enumerate(uniq)}
        colors = [palette.get(v, (0.8, 0.8, 0.8, 1.0)) for v in series.values]

    for x_idx, c in enumerate(colors):
        ax_ann.add_patch(
            mpatches.Rectangle((x_idx - 0.5, 0), 1, 1,
                                facecolor=c, edgecolor="none")
        )
    ax_ann.set_xlim(-0.5, n_samples - 0.5)
    ax_ann.set_ylim(0, 1)
    ax_ann.set_yticks([0.5])
    ax_ann.set_yticklabels([col], fontsize=GLOBAL_FONT_SIZE - 1)
    ax_ann.set_xticks([])
    ax_ann.spines[:].set_visible(False)

# ── Legend ────────────────────────────────────────────────────────────────────
present_types = set(agg.loc[agg["Hugo_Symbol"].isin(top_genes), "mut_type"].unique())
legend_patches = [
    mpatches.Patch(color=MUTATION_COLORS.get(t, "#888888"), label=t.replace("_", " "))
    for t in MUTATION_COLORS
    if t in present_types
]
fig.legend(
    handles=legend_patches,
    loc="lower right",
    fontsize=GLOBAL_FONT_SIZE - 1,
    frameon=False,
    title="Mutation type",
    title_fontsize=GLOBAL_FONT_SIZE,
    ncol=2,
)

plt.suptitle(
    f"FL Somatic Mutations — Top {len(top_genes)} genes "
    f"({n_samples} samples, non-silent only)",
    fontsize=GLOBAL_FONT_SIZE + 1,
    y=1.01,
)

# ── Save ──────────────────────────────────────────────────────────────────────
out = Path(OUTPUT_DIR)
out.mkdir(exist_ok=True)
fig.savefig(out / "fl_oncoprint_mutations.pdf", bbox_inches="tight")
fig.savefig(out / "fl_oncoprint_mutations.svg", bbox_inches="tight")
plt.show()
print("Saved to plots/fl_oncoprint_mutations.pdf and .svg")
```

---

### 2. New directory — `data/`

**Location:** `~/FL_harmonization/data/`

Create this directory for the MAF file (and any future genomic data files).
Add a `.gitignore` entry for large genomic files to stay below the 100 MB GitHub limit.

---

### 3. Update `.gitignore`

**Location:** `~/FL_harmonization/.gitignore`

Add:
```
# Genomic data files (too large for GitHub)
data/*.maf
data/*.vcf
data/*.maf.gz
```

---

### 4. Update `CLAUDE.md`

**Location:** `~/FL_harmonization/CLAUDE.md`

Add to the "Key Files" table:

```
| `fl_somatic_mutations_oncoprint.ipynb` | OncoPrint / waterfall plot for FL somatic mutations from MAF file |
| `data/fl_somatic_mutations.maf` | FL somatic mutation data (MAF format; git-ignored) |
```

---

## Files That Do NOT Need to Change

| File | Reason |
|---|---|
| `all_cohorts_assembly.ipynb` | Expression-only pipeline; no mutation data |
| `harmonization-scripts/*.py` | Normalization pipeline; unrelated |
| `SOM_FSQN_R.py` / `SOM.py` | SOM pipeline; no mutation input |
| `MDA_Strati_FL_annotation.csv` | Read-only input; not modified |

---

## Side Effects and Caveats

1. **Sample ID matching**: The `Tumor_Sample_Barcode` in the MAF must match the `Sample ID`
   column in `MDA_Strati_FL_annotation.csv`. The join must be verified once the MAF is
   available — the identifier format may differ (e.g., `FL001_IN1` vs `FLSP36`). A diagnostic
   cell printing unmatched IDs is included.

2. **Annotation tracks are optional**: If the MAF samples have no match in the annotation CSV
   (e.g., the MAF is from a different cohort than MDA), the annotation tracks will be silently
   skipped via `ANNOTATION_TRACKS = []`.

3. **Gene panel size**: `TOP_N_GENES = 30` and `MIN_FREQ_PERCENT = 2.0` are starting defaults.
   For FL genomics (CREBBP/EP300/EZH2 are typically top-hit genes), adjustments may be needed
   based on the actual data.

4. **Silent variant exclusion**: By default `EXCLUDE_SILENT = True`. If the MAF contains only
   coding variants, this filter will have no effect.

5. **File size**: PDF OncoPrints with many samples can be large (>10 MB). If the sample count
   is very large (>500), consider rasterizing the main grid (`imshow` mode instead of patches).

---

## Verification Steps

After uploading the MAF file and placing it at `data/fl_somatic_mutations.maf`:

```bash
source ~/venvs/collagen_3_11/bin/activate
# Quick MAF column check
python -c "
import pandas as pd
df = pd.read_csv('data/fl_somatic_mutations.maf', sep='\t', comment='#', nrows=5)
print(df.columns.tolist())
print(df[['Hugo_Symbol','Variant_Classification','Tumor_Sample_Barcode']].head())
"
# Then open the notebook and run all cells
jupyter lab fl_somatic_mutations_oncoprint.ipynb
```

Expected output:
- `plots/fl_oncoprint_mutations.pdf` — publication-ready OncoPrint
- `plots/fl_oncoprint_mutations.svg` — vector format for editing

---

## TODO

- [ ] Upload MAF file and place at `data/fl_somatic_mutations.maf` (Daniil)
- [ ] Create `data/` directory: `mkdir -p data`
- [ ] Add `.gitignore` entries for `data/*.maf`, `data/*.vcf`, `data/*.maf.gz`
- [ ] Create new notebook `fl_somatic_mutations_oncoprint.ipynb` with all 5 cells above
- [ ] Verify MAF columns match expected (`Hugo_Symbol`, `Variant_Classification`, `Tumor_Sample_Barcode`)
- [ ] Confirm `SAMPLE_ID_COLUMN_MAF` and `SAMPLE_ID_COLUMN_ANN` align between MAF and annotation CSV
- [ ] Adjust `ANNOTATION_TRACKS` list to match available columns in annotation CSV
- [ ] Run notebook end-to-end; inspect gene list and frequencies
- [ ] Tune `TOP_N_GENES` and `MIN_FREQ_PERCENT` based on actual data
- [ ] Verify PDF/SVG outputs saved to `plots/`
- [ ] Update `CLAUDE.md` Key Files table with new notebook and data file entries
