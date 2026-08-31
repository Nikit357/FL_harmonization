# Notebook Cleanup & Reorganization Plan
**Date:** 2026-06-10  
**Notebooks:**
- `harmonization_metrics_analysis_v2.ipynb` — 88 MB, 259 cells (65 figure-output cells)
- `harmonization_metrics_visual_inspection.ipynb` — 127 MB, 283 cells (120 figure-output cells)

---

## Overview

Both notebooks exceed GitHub's 100 MB soft limit and are too heavy to edit in JupyterLab. The goal is:
1. **Strip all cell outputs** (figures + text) from both notebooks, keeping all code and markdown cells intact so the analysis can be re-run from scratch.
2. **Reorganize** `harmonization_metrics_visual_inspection.ipynb`: the PCA/tSNE/UMAP inspection cells are currently interleaved across strategies in an ad-hoc order. Regroup them by **strategy** (J, K, A/B, C, D, F, G, H, I) then by **method** within each strategy, with clear `##`-level markdown headers. Add a table of contents.

No code logic changes. No cells deleted.

---

## Part 1 — Output Stripping (both notebooks)

**Method:** Direct JSON manipulation via a Python helper script (`strip_and_reorganize.py`). For every `code` cell set `outputs = []` and `execution_count = null`. This is safer and faster than `nbstripout` for a one-shot bulk operation.

**Expected post-cleanup sizes:**
| Notebook | Before | After (est.) |
|---|---|---|
| `harmonization_metrics_analysis_v2.ipynb` | 88 MB | ~1.5 MB |
| `harmonization_metrics_visual_inspection.ipynb` | 127 MB | ~1.5 MB |

**What is preserved:** All cell sources (code + markdown), cell metadata, kernel info, notebook-level metadata.

---

## Part 2 — Reorganization of `harmonization_metrics_visual_inspection.ipynb`

### Current structure

Cells 0–18 are setup (imports, data loading, palettes, helper functions) — **stay in place**.

Cells 19–282 are inspection sections mixed across strategies in this order:
```
J_ff_only → K_ffpe_only → D (angel) → D (combat) → D (xpn) →
G → H → cross-method (amdbnorm/vst/fsqn_r) → F_microarray →
D (fsmvn/limma/pycombat/npn/xpn2/qsmooth/tdm/explobatch/shambhala) →
C (shambhala/kbet) → A/B (mnn) → C (fsqn_py) → D (harmony) →
I → C (kbet/harmony/tmm) → D (arsyn) → C (sva/harmony/rank) →
G (mnn10) → C (mnn10) → A/B (worst/angel) → F (scanorama) →
S0 (rank) → G (mnn10_awful) → F (qsmooth) → G (fsqn_r failed) →
generic (sort by kbet/tsne) → generic (harsh) → generic (violins)
```

### Proposed structure (after cells 0–18)

Each group gets a new `##`-level markdown header cell inserted before it. Existing `###`-level sub-headers within each group are preserved as-is.

---

#### Group 1 — Strategy: J — `J_ff_only` (Fresh-Frozen only)
**Source cells (current indices):** 20–24  
**Sections:**
- `### Best approaches for FF_only`

---

#### Group 2 — Strategy: K — `K_ffpe_only` (FFPE only)
**Source cells (current indices):** 25–35  
**Sections:**
- `### Best approaches for FFPE_only`
  - `#### By tsne_entropy_norm_RNA_BATCH`
  - `#### Worse by pcr_RNA_BATCH`

---

#### Group 3 — Strategy: A/B — `A_confirmed_bad` / `B_extended_bad`
**Source cells (current indices):** 150–155, 224–233  
**Sections:**
- `### MNN 5 top attempts - successful` (A_confirmed_bad, B_extended_bad, E1_iterative)
- `### Example of worst approaches by clustermap`
- `### Angel normalization - could be good! No`

---

#### Group 4 — Strategy: C — `C_rnaseq_only`
**Source cells (current indices):** 142–149, 156–161, 172–213, 219–223  
**Sections (in order):**
- `### Shambhala top attempts by local metrics mixing for RNASeq - bad`
- `### RNASeq only: Best ones by FSQN py and kBET`
- `### RNASeq only: More approaches by kBET`
- `### RNASeq only: Harmony. Good by kBET`
- `### RNASeq only: TMM`
- `### RNASeq only best approaches: 04_sva, C_rnaseq_only, knn & softimpute`
  - `#### Per-batch expression distribution violins + CV-vs-expression curves`
- `### RNASeq only another best approach: 11_harmony` (bad in fact)
- `### RNASeq only another best approach: 18_rank` (bad)
- `### RNASeq only average approaches: mnn10`

---

#### Group 5 — Strategy: D — `D_malignant_only`
**Source cells (current indices):** 37–47, 53–58, 91–140, 141, 162–166, 187–194  
**Sections (in order):**
- `### 25_angel in D_malignant_only`
- `### 05_combat in D_malignant_only`
- `### 26_xpn approaches` (first section — filter on D_malignant_only)
- `### Best 13_fsmvn approaches`
- `### Best 03_limma approaches`
- `### 07_pycombat best approaches`
- `### 28_npn best approaches`
- `### 26_xpn best approaches` (second/refined section)
- `### Best qsmooth attempts`
  - `#### By tsne_entropy_norm_RNA_BATCH`
  - `#### By PCR RNA_BATCH`
- `### tdm best approaches`
- `### explobatch best approaches`
- `### Shambhala top attempts for Malignant Only`
- `### SHambhala for microarrays` (empty markdown placeholder — kept as separator)
- `### Harmony in Malignant only`
- `### Arsyn Harman in Malignant only post-rm: too many nas`
  *(Note: code here loads `H_affymetrix_extended` data for cross-strategy comparison; title refers to D_malignant_only context)*

---

#### Group 6 — Strategy: F — `F_microarray_only`
**Source cells (current indices):** 86–90, 234–238, 249–253  
**Sections:**
- `### Best approaches by PCR RNA_BATCH in microarrays only`
- `### Scanorama for Microarrays only - could be good!`
- `### Microarrays with qsmooth, post0 and post1, all imputations - could be good but awful`

---

#### Group 7 — Strategy: G — `G_affymetrix_only`
**Source cells (current indices):** 59–63, 214–218, 244–248, 254–262  
**Sections:**
- `### Best G_affymetrix_only approaches`
- `### G_affymetrix_only mnn10` (mostly empty code, placeholder)
- `### Affymetrix only best approaches: knn & softimpute & strict, 10_mnn, post1 - awful`
- `### 16_fsqn_r - FAILED! Find what happened!`

---

#### Group 8 — Strategy: H — `H_affymetrix_extended`
**Source cells (current indices):** 64–68  
**Sections:**
- `### Best H_affymetrix_extended approaches` (mostly empty code — analysis pending)

---

#### Group 9 — Strategy: I — `I_rare_batches_removed`
**Source cells (current indices):** 167–171  
**Sections:**
- `### 08_inmoose_combatseq in I_rare_batches_removed and other good attempts`

---

#### Group 10 — Cross-strategy: Method-level comparisons (all strategies)
**Source cells (current indices):** 69–85, 239–243  
**Sections:**
- `### 33_amdbnorm approaches` (best across all strategies by kBET)
- `### VST best approaches` (23_vst, across all strategies)
- `### Best by 16_fsqn_r` (top-5 across all strategies)
- `### Rank normalization for RNASeq and arrays. Why the same patterns before and after the post-removal?`

---

#### Group 11 — Generic: Metric-sorted and miscellaneous
**Source cells (current indices):** 263–282  
**Sections:**
- `### Sort attempts by kbet_acceptance_rate_RNA_BATCH and look at their PCA/UMAP/tSNE`
  - `#### First 5 approaches`
- `### Sort attempts by tsne_entropy_norm_RNA_BATCH and look at their PCA/UMAP/tSNE`
- `### Try other harsh methods`
- `### Per-batch expression distribution violins + CV-vs-expression curves`

---

### Table of Contents cell

A new markdown cell will be inserted at position 19 (first cell after setup) listing all groups as anchor links so you can navigate directly to any strategy section.

---

## Files to change

| File | Change |
|---|---|
| `harmonization_metrics_analysis_v2.ipynb` | Strip outputs only |
| `harmonization_metrics_visual_inspection.ipynb` | Strip outputs + reorganize cells |
| `strip_and_reorganize.py` | New helper script (not committed; run once, then delete) |

## Files NOT changing

- `compute_batch_metrics.py` — no change
- `run_metrics_parallel.py` / `run_metrics_job.py` — no change
- `CLAUDE.md` — no structural change (no new architecture to document)

---

## Implementation

The `strip_and_reorganize.py` script will:
1. Load each notebook with `json.load`.
2. Walk all code cells and set `outputs = []`, `execution_count = None`.
3. For the visual inspection notebook only: extract the 11 strategy groups defined above, build the new cell list as: `setup_cells + [new_toc_header] + [new_group_headers + group_cells for each group]`.
4. Save with `json.dump` (indent=1, same as Jupyter default).

The script will print a before/after cell count and the final file sizes.

---

## Caveats

1. **Execution dependency:** All plot cells use `top_n`, `_EXP_CACHE`, `plot_embedding_grid()` etc. that are defined in the setup section (cells 0–18) or re-initialized in each section's own `top_n = df_ok[...]` line. Physical reordering does not break execution: each section is self-contained after setup is run.
2. **Empty code cells:** Empty separator cells (cells 36, 42, 48–52, 66–68, 74–75, etc.) are kept and travel with their nearest enclosing section block. They will be placed after the last code cell of the section they follow in the original notebook.
3. **Cell 141 (SHambhala for microarrays):** This is an empty markdown placeholder. It is preserved within Group 5 (D_malignant_only) as a reminder that microarray-strategy Shambhala analysis is still missing.
4. **git:** After saving, run `nbstripout --install` is already configured. The cleaned notebooks will be commitable at ~1–2 MB each.

---

## Verification commands

```bash
source ~/venvs/collagen_3_11/bin/activate
python strip_and_reorganize.py       # run cleanup + reorganization
ls -lh harmonization_metrics_*.ipynb # verify file sizes dropped to < 5 MB
python -c "
import json
nb = json.load(open('harmonization_metrics_visual_inspection.ipynb'))
cells = nb['cells']
print('Total cells:', len(cells))
md_headers = [(i, ''.join(c['source'])[:80]) for i, c in enumerate(cells) if c['cell_type']=='markdown' and '##' in ''.join(c['source'])[:5]]
print('Strategy headers:', len([h for h in md_headers if '## Strategy' in h[1]]))
for idx, h in md_headers: print(f'  [{idx:3d}] {h}')
"
```

---

## TODO

- [x] Write `strip_and_reorganize.py` in `harmonization-metrics/`
  - [x] Strip outputs from `harmonization_metrics_analysis_v2.ipynb`
  - [x] Strip outputs from `harmonization_metrics_visual_inspection.ipynb`
  - [x] Reorder cells in `harmonization_metrics_visual_inspection.ipynb` per Groups 1–11 above
  - [x] Insert new `##`-level strategy header cells before each group
  - [x] Insert Table of Contents cell at position 19
  - [x] Print before/after cell count and file size
- [x] Run `strip_and_reorganize.py` and verify output sizes
  - `harmonization_metrics_analysis_v2.ipynb`: 88 MB → 0.4 MB, 259 cells → 259 cells
  - `harmonization_metrics_visual_inspection.ipynb`: 127 MB → 0.2 MB, 283 cells → 295 cells (+12 new header/ToC cells)
  - 0 code cells with non-empty outputs in both notebooks ✓
- [ ] Open `harmonization_metrics_visual_inspection.ipynb` in JupyterLab and confirm navigation works
- [ ] Delete `strip_and_reorganize.py` or keep as utility (your call)
