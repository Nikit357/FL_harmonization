# Plan: replace the legacy internal marker panels with Dybkaer et al. 2015 GC subset genes

## Overview

Metric group L (marker correlation preservation) and group M (cross-batch rank
agreement) draw their gene panel from `marker_gene_annotation.csv`, which is built by
`build_marker_gene_annotation.py`. Six gene groups in that table are currently sourced
from an internal, uncited panel (`Normal_B_cells` — "an internal, unpublished
centroblast/centrocyte panel"): two germinal-centre (GC) cell-identity panels
(`legacy_centroblast_DZ`, `legacy_centrocyte_LZ`) and four pathway panels
(`FL_pathway_BCR`, `FL_pathway_NFkB`, `FL_pathway_PI3K_AKT`, `FL_pathway_GCB_markers`).

Daniil supplied the Data Supplement tables from Dybkaer et al. 2015 (*J Clin Oncol*
33(12):1379-1388, PMC4397280 — "Diffuse Large B-Cell Lymphoma Classification System
That Associates Normal B-Cell Subset Phenotypes With Prognosis") in
`Dybkaer_et_al_2015_supplementary/`, to replace the uncited legacy internal panel content with a
published, citable gene panel.

**Decision (confirmed with Daniil):**
- **Scope:** all 6 legacy-panel-tagged blocks are removed. There is no Dybkaer-derived
  replacement for the 4 pathway panels (BCR/NF-kB/PI3K-AKT/GCB_markers) — Dybkaer DS1
  is a cell-identity classifier, not a pathway breakdown — so those pathway groupings
  are dropped from the panel entirely, not replaced 1:1.
- **Source table:** DS1 only (`supp_JCO.2014.57.7080_DS1_JCO.2014.57.7080.xls`). DS7
  (the larger GCB-CB vs GCB-CC differential list) is not used.

**What DS1 is.** `sup1` is the article's own nearest-shrunken-centroid classifier
weight matrix for five normal B-cell subsets — Centroblast, Centrocyte, Memory, Naive,
Plasmablast — one column per subset, 327 probes total. A gene is "in" a subset's panel
when its classifier weight for that subset is nonzero (this is the article's own
feature-selection result, not an arbitrary threshold chosen here). Only **Centroblast**
(dark zone) and **Centrocyte** (light zone) are germinal-centre subsets; Memory, Naive
and Plasmablast are excluded as not GC-relevant, matching the scope Daniil asked for.

Applying that rule: **Centroblast → 69 genes**, **Centrocyte → 55 genes** (14 genes
overlap; 110 unique genes total), after splitting Affymetrix multi-gene probe symbols
("`GENE1 /// GENE2`") into individual symbols and running them through the same
`_NON_MARKER_SYMBOL` filter already used for Holmes/Kotlov (drops clone IDs,
mitochondrial transcripts, `MIR`/`LINC`/`SNHG` non-coding RNAs, ribosomal pseudogenes).
This is a straight port of the existing `holmes_gc_state_blocks()` /
`kotlov_fges_blocks()` pattern: a new reader function computes the gene lists from the
spreadsheet at build time, nothing is hardcoded.

**New dependency.** DS1/DS7 are legacy `.xls` (BIFF8) files. `openpyxl` (already a
dependency) cannot read `.xls`, only `.xlsx`. Reading DS1 requires `xlrd>=2.0.1`,
which must be added to both `requirements.txt` and the `k8s/pod-metrics.yaml`
ConfigMap per the existing sync convention (`openpyxl` already lives in both for the
same reason: `build_marker_gene_annotation.py` is a build-time script, but its
dependencies are kept in sync with the pod's requirements file regardless).

---

## Background / reference data

### Current state of the 6 blocks being removed (`marker_gene_annotation.csv`)

| gene_group | source | n genes |
|---|---|---|
| `legacy_centroblast_DZ` | Normal_B_cells | 10 |
| `legacy_centrocyte_LZ` | Normal_B_cells | 9 |
| `FL_pathway_BCR` | Normal_B_cells | 7 |
| `FL_pathway_NFkB` | Normal_B_cells | 7 |
| `FL_pathway_PI3K_AKT` | Normal_B_cells | 8 |
| `FL_pathway_GCB_markers` | Normal_B_cells | 6 |

47 rows total, 42 unique genes. Of those, **9 genes disappear from the whole table**
once these blocks are removed (they don't appear in any other gene_group): `BCL10`,
`BIRC5`, `CARD11`, `DUSP5`, `DUSP6`, `IKBKB`, `IKBKG`, `MALT1`, `NR4A1`.

### New blocks being added, computed from DS1

`dybkaer_centroblast_DZ` (69 genes, Centroblast column nonzero):
```
ANLN, APOBEC3B, ASPM, ATP5S, ATP8B3, BCL2, BHLHE41, BMP3, C17orf57, C1orf115,
CASP1, CCND2, CDK1, CENPE, CENPF, CYTH4, DEPDC1, DHRS9, DLGAP5, EGOT, EGR3,
ELOVL6, ENTPD1, FCRL5, FRZB, GABARAPL1, GABARAPL3, GAS2L3, HLA-DQA1, HLA-DQB1,
HRK, IQSEC1, IRF4, KANK2, KIF14, KIF18A, KIF20A, LOC100506844, LOC100507718,
LOC100509457, LOC157740, LRRK2, MLL, MPEG1, NDE1, NEK2, NFKB2, NFRKB, PARP15,
PDE8B, PEG10, PIF1, PLK4, PMEPA1, POU2AF1, PPAPDC1B, PRDM1, PRKAR2B, PRO1483,
RHOBTB3, SKI, SLAMF1, SLAMF7, SLC41A2, SMAD1, SNX9, TOP2A, WASF3, WNT2B
```

`dybkaer_centrocyte_LZ` (55 genes, Centrocyte column nonzero):
```
ACTN2, BAIAP2L1, BCL2A1, C3orf38, CAMK2B, CCNB2, CELF2, CHPT1, COL5A1, DHRS9,
DNER, EGR3, FEZ1, FGD6, GPR82, HLA-DQA1, HLA-DQB1, IGSF10, ITGB3, JUN, KIF13A,
LIMD1, LOC100506930, LOC100507718, LOC100509457, LPL, MATR3, MED12L, MFSD4,
MGC39372, MSH6, NDE1, NFRKB, NLRP4, NOTCH2, P2RY12, PANK1, PDE4B, PDE8B, PNKD,
PRDM1, PRO1483, PTPRJ, SERPINA9, SLC41A2, SOX9, SSPN, SYCP3, SYTL4, SZT2,
TBC1D9, UEVLD, WASF3, WNT2B, ZEB2
```

These lists are shown here only as a check against the code — they are computed
dynamically by the new reader function at build time and never hardcoded in the
script.

### Table-wide totals, before → after

| | rows (gene × group) | unique genes | gene groups | housekeeping |
|---|---|---|---|---|
| Current | 757 | 548 | 67 | 15 |
| After removing 6 Normal_B_cells blocks | 710 | 539 | 61 | 15 |
| After adding 2 Dybkaer blocks | **834** | **633** | **63** | 15 |

### Assumptions carried over from the removed blocks (flag for review)

- `dybkaer_centroblast_DZ` keeps `pathway="proliferation"` (matches the new gene
  list: `ANLN`, `ASPM`, `CDK1`, `CENPE`, `CENPF`, `DLGAP5`, `KIF14/18A/20A`, `NEK2`,
  `PLK4`, `TOP2A` are all cell-cycle genes — same tag the old `legacy_centroblast_DZ`
  used, and appropriate for the article's own dark-zone-is-proliferative framing).
- `dybkaer_centrocyte_LZ` keeps `pathway="none"` (no single dominant pathway in the
  new gene list, matching the old block's value).
- Both new blocks keep `tme_subtype="none"` and `prognostic_significance="none"`,
  unchanged from the old blocks. DS1 is a classifier weight table, not an
  outcome-association table, so `"none"` for prognostic significance is consistent
  with how `kotlov_fges_blocks()` already handles the same situation (see its
  docstring: "Table S1 reports no per-gene outcome association").
- Several resolved symbols (`LOC100506844`, `LOC100507718`, `LOC100509457`,
  `LOC157740`, `LOC100506930`, `PRO1483`, `EGOT`, `MGC39372`, `C1orf115`) are
  provisional/uncharacterized locus names unlikely to be present in the HGNC-mapped
  benchmark matrices. This is not a new failure mode — `resolve_panel()` already
  tolerates unmapped panel genes by placing them in its `missing` list (same as some
  Holmes/Kotlov symbols today); it only lowers the effective coverage of the new
  blocks. No filtering beyond the existing `_NON_MARKER_SYMBOL` regex is proposed.

---

## Files to change

### 1. `harmonization-metrics-calculation/build_marker_gene_annotation.py`

#### 1a. Remove the `Normal_B_cells` source constant (line 56)

**Before:**
```python
XOCHELLI = "Xochelli et al. 2025 Leukemia, doi:10.1038/s41375-025-02603-9"
Normal_B_cells = "an internal, unpublished centroblast/centrocyte panel"
PASTORE = "Pastore et al. 2019, PMID 29475724"
```
**After:**
```python
XOCHELLI = "Xochelli et al. 2025 Leukemia, doi:10.1038/s41375-025-02603-9"
DYBKAER = "Dybkaer et al. 2015 J Clin Oncol 33(12):1379-1388, PMC4397280"
PASTORE = "Pastore et al. 2019, PMID 29475724"
```
(`Normal_B_cells` becomes unused once the 6 blocks below are removed — delete rather than
leave dead code. `DYBKAER` is the new source constant, added in the same place.)

#### 1b. Remove `legacy_centroblast_DZ` and `legacy_centrocyte_LZ` blocks

These two blocks sit between the Xochelli C1/C2/C3 panels and `FL_PFS_signature_2019`
— delete only these two, keep everything else in the surrounding list untouched.

**Before:**
```python
    (
        "legacy_centroblast_DZ",
        "centroblast (DZ)",
        "proliferation",
        "none",
        "none",
        Normal_B_cells,
        "repo_panel",
        [
            "AICDA",
            "MKI67",
            "BCL6",
            "CXCR4",
            "EZH2",
            "RGS13",
            "FOXO1",
            "LMO2",
            "CCNB1",
            "BIRC5",
        ],
    ),
    (
        "legacy_centrocyte_LZ",
        "centrocyte (LZ)",
        "none",
        "none",
        "none",
        Normal_B_cells,
        "repo_panel",
        ["CD83", "MME", "FCER2", "BCL2", "CD40", "SELL", "DUSP5", "DUSP6", "NR4A1"],
    ),
    (
        "FL_PFS_signature_2019",
        ...
```
**After:**
```python
    (
        "FL_PFS_signature_2019",
        ...
```
(the `FL_PFS_signature_2019` block itself is unchanged — only the two blocks above it
are deleted).

#### 1c. Remove the 4 `FL_pathway_*` blocks

These four sit right after `FL_POD24_markers` and are the last blocks before the
housekeeping section — delete all four, keep `FL_POD24_markers` and the housekeeping
block untouched.

**Before:**
```python
    (
        "FL_POD24_markers",
        ...
    ),
    (
        "FL_pathway_BCR",
        "B cell",
        "BCR",
        "none",
        "none",
        Normal_B_cells,
        "repo_panel",
        ["CD79A", "CD79B", "PTPN6", "PIK3CD", "CARD11", "BCL10", "MALT1"],
    ),
    (
        "FL_pathway_NFkB",
        "none",
        "NF-kB",
        "none",
        "none",
        Normal_B_cells,
        "repo_panel",
        ["NFKB1", "NFKB2", "REL", "RELA", "RELB", "IKBKB", "IKBKG"],
    ),
    (
        "FL_pathway_PI3K_AKT",
        "none",
        "PI3K-AKT",
        "none",
        "none",
        Normal_B_cells,
        "repo_panel",
        ["PIK3CA", "PIK3CB", "PIK3CD", "AKT1", "AKT2", "AKT3", "PTEN", "MTOR"],
    ),
    (
        "FL_pathway_GCB_markers",
        "germinal centre B",
        "none",
        "GC-like",
        "none",
        Normal_B_cells,
        "repo_panel",
        ["BCL6", "MYC", "BCL2", "MME", "CXCR4", "CXCR5"],
    ),
    # ── 5. Housekeeping negative control ─────────────────────────────────────
```
**After:**
```python
    (
        "FL_POD24_markers",
        ...
    ),
    # ── 5. Housekeeping negative control ─────────────────────────────────────
```

#### 1d. Add the DS1 file path constant, next to `KOTLOV_XLSX` / `HOLMES_XLSX`

**Before:**
```python
HOLMES_XLSX = (
    Path(__file__).parent
    / "Holmes_et_al_2020_supplementary"
    / "jem_20200483_tables2.xlsx"
)

HOLMES_TOP_N_UP = 20
```
**After:**
```python
HOLMES_XLSX = (
    Path(__file__).parent
    / "Holmes_et_al_2020_supplementary"
    / "jem_20200483_tables2.xlsx"
)
DYBKAER_DS1_XLS = (
    Path(__file__).parent
    / "Dybkaer_et_al_2015_supplementary"
    / "supp_JCO.2014.57.7080_DS1_JCO.2014.57.7080.xls"
)

HOLMES_TOP_N_UP = 20
```

#### 1e. Add `dybkaer_gc_subset_blocks()`, after `holmes_gc_state_blocks()`

Insert this new function directly after `holmes_gc_state_blocks()` (before
`all_blocks()`):

```python
def dybkaer_gc_subset_blocks() -> list[Block]:
    """Build the centroblast (DZ) and centrocyte (LZ) panels from Dybkaer Table DS1.

    DS1 is the nearest-shrunken-centroid classifier weight matrix for five normal
    B-cell subsets (Centroblast, Centrocyte, Memory, Naive, Plasmablast). Only the
    two germinal-centre subsets are used here; Memory, Naive and Plasmablast are not
    GC-relevant. A gene is included in a subset's panel when its classifier weight
    for that subset is nonzero — the article's own feature selection, not an
    arbitrary threshold. Affymetrix multi-gene probe symbols ("GENE1 /// GENE2") are
    split into individual symbols before the shared _NON_MARKER_SYMBOL filter runs.

    Returns
    -------
    list[Block]
        Two blocks: dybkaer_centroblast_DZ, dybkaer_centrocyte_LZ.
    """
    df = pd.read_excel(DYBKAER_DS1_XLS, sheet_name="sup1", header=0, engine="xlrd")
    df.columns = [str(c).strip() for c in df.columns]

    specs = [
        ("dybkaer_centroblast_DZ", "Centroblast", "centroblast (DZ)", "proliferation"),
        ("dybkaer_centrocyte_LZ", "Centrocyte", "centrocyte (LZ)", "none"),
    ]
    blocks: list[Block] = []
    for group, column, cell_type, pathway in specs:
        selected = df.loc[df[column] != 0, "Gene.symbol"].dropna()
        raw_symbols = [
            part.strip() for value in selected for part in str(value).split("///")
        ]
        genes = _clean_symbols(raw_symbols)
        blocks.append(
            (group, cell_type, pathway, "none", "none", DYBKAER, "dybkaer_table_ds1", genes)
        )
    return blocks
```

#### 1f. Register the new function in `all_blocks()`

**Before:**
```python
def all_blocks() -> list[Block]:
    """Static blocks plus every block read from the two supplementary spreadsheets."""
    return (
        BLOCKS
        + kotlov_fges_blocks()
        + kotlov_classifier_blocks()
        + holmes_gc_state_blocks()
    )
```
**After:**
```python
def all_blocks() -> list[Block]:
    """Static blocks plus every block read from the supplementary spreadsheets."""
    return (
        BLOCKS
        + kotlov_fges_blocks()
        + kotlov_classifier_blocks()
        + holmes_gc_state_blocks()
        + dybkaer_gc_subset_blocks()
    )
```

#### 1g. Update the module docstring's "Provenance values" section

**Before:**
```python
holmes_table_s2
    Read from Holmes et al. 2020 supplementary Table S2 - the per-cluster
    up-regulated gene list, truncated to the top HOLMES_TOP_N_UP genes by log2
    fold change.
repo_panel
```
**After:**
```python
holmes_table_s2
    Read from Holmes et al. 2020 supplementary Table S2 - the per-cluster
    up-regulated gene list, truncated to the top HOLMES_TOP_N_UP genes by log2
    fold change.
dybkaer_table_ds1
    Read from Dybkaer et al. 2015 supplementary Data Supplement 1 (DS1) - the
    nearest-shrunken-centroid classifier weight matrix for five normal B-cell
    subsets. A gene is included when its classifier weight for that subset (here,
    Centroblast or Centrocyte) is nonzero.
repo_panel
```

#### 1h. Update the "Supplementary-table readers" section comment

**Before:**
```python
# ── Supplementary-table readers ───────────────────────────────────────────────
# The two spreadsheets are committed next to this script so the CSV stays
# regenerable. Kotlov Table S1 lists the FGES gene sets verbatim; Holmes Table S2
# lists per-cluster differential genes already ordered by log2 fold change, which
# is why "top N" is a well-defined signature rather than an arbitrary slice.
```
**After:**
```python
# ── Supplementary-table readers ───────────────────────────────────────────────
# The three spreadsheets are committed next to this script so the CSV stays
# regenerable. Kotlov Table S1 lists the FGES gene sets verbatim; Holmes Table S2
# lists per-cluster differential genes already ordered by log2 fold change, which
# is why "top N" is a well-defined signature rather than an arbitrary slice. Dybkaer
# DS1 is a classifier weight matrix (Kotlov/Holmes are differential-expression
# tables), so its selection rule is "nonzero weight" rather than a fold-change cutoff.
```

---

### 2. `harmonization-metrics-calculation/marker_gene_annotation.csv`

Not edited by hand — regenerated by running `python build_marker_gene_annotation.py`
after the changes in file 1 land (see Verification commands). Expected result: 834
rows, 633 unique genes, 63 gene groups, 15 housekeeping (see totals table above).

### 3. `harmonization-metrics-calculation/requirements.txt`

**Before:**
```
awscli>=1.29
openpyxl>=3.1
```
**After:**
```
awscli>=1.29
openpyxl>=3.1
xlrd>=2.0.1
```

### 4. `harmonization-metrics-calculation/k8s/pod-metrics.yaml`

Mirror the same addition inside the embedded `data.requirements.txt` ConfigMap block
(around line 31), per the file's own "keep in sync" comment at the top.

**Before:**
```yaml
    awscli>=1.29
    openpyxl>=3.1
```
**After:**
```yaml
    awscli>=1.29
    openpyxl>=3.1
    xlrd>=2.0.1
```

### 5. `~/FL_harmonization/project_overview.md`

#### 5a. Gene panel summary (lines 352–357)

**Before:**
```
**Gene panel.** `marker_gene_annotation.csv` — 548 unique genes across 67 signatures (757
gene × signature rows), 15 housekeeping controls, annotated with cell type, pathway, Kotlov LME
subtype, prognostic significance, source article and provenance. The signature memberships are
read verbatim from the published supplementary tables: Kotlov Table S1 (22 FGES gene sets) and
Tables S2/S3 (cell-of-origin and double-hit classifier panels), and Holmes Table S2 (the 13
single-cell GC B-cell clusters, top 20 up-regulated genes per cluster by log2 fold change).
```
**After:**
```
**Gene panel.** `marker_gene_annotation.csv` — 633 unique genes across 63 signatures (834
gene × signature rows), 15 housekeeping controls, annotated with cell type, pathway, Kotlov LME
subtype, prognostic significance, source article and provenance. The signature memberships are
read verbatim from the published supplementary tables: Kotlov Table S1 (22 FGES gene sets) and
Tables S2/S3 (cell-of-origin and double-hit classifier panels), Holmes Table S2 (the 13
single-cell GC B-cell clusters, top 20 up-regulated genes per cluster by log2 fold change), and
Dybkaer Data Supplement 1 (nonzero-weight genes from the Centroblast and Centrocyte columns of
the normal B-cell subset classifier).
```

#### 5b. Curated gene sets list (line 377)

**Before:**
```
**Curated gene sets used in §11** (with citations — new literature anchors, see below): FL transcriptomic subtype markers C1/C2/C3 (Xochelli et al. 2025, *Leukemia*), legacy internal GC B-cell markers (Centroblast/Centrocyte; internal), FL PFS prognostic signature (Pastore et al. 2019 — same reference already tracked as "FL PFS signature 2019"), POD24 mutation markers (Huet et al. 2018, *Blood*), PROGENy pathway-activating genes (Schubert et al. 2018), housekeeping genes as a stability reference (Eisenberg & Levanon 2013).
```
**After:**
```
**Curated gene sets used in §11** (with citations — new literature anchors, see below): FL transcriptomic subtype markers C1/C2/C3 (Xochelli et al. 2025, *Leukemia*), GC B-cell markers (Centroblast/Centrocyte; Dybkaer et al. 2015, *J Clin Oncol*, PMC4397280, Data Supplement 1), FL PFS prognostic signature (Pastore et al. 2019 — same reference already tracked as "FL PFS signature 2019"), POD24 mutation markers (Huet et al. 2018, *Blood*), PROGENy pathway-activating genes (Schubert et al. 2018), housekeeping genes as a stability reference (Eisenberg & Levanon 2013).
```

Note: this line does not currently mention the 4 removed `FL_pathway_*` panels
(BCR/NF-kB/PI3K-AKT) at all — that's a pre-existing gap in this summary, not
something introduced by this change, so no further edit is needed here.

### 6. `~/FL_harmonization/CLAUDE.md`

**Before (line 115):**
```
| `harmonization-metrics-calculation/marker_gene_annotation.csv` | Gene panel source of truth for groups L/M: 548 genes, 67 signatures, cell type / pathway / TME subtype / prognosis / source per gene |
```
**After:**
```
| `harmonization-metrics-calculation/marker_gene_annotation.csv` | Gene panel source of truth for groups L/M: 633 genes, 63 signatures, cell type / pathway / TME subtype / prognosis / source per gene |
```

### 7. `harmonization-metrics-calculation/CLAUDE.md`

**Before (line 116):**
```
| `marker_gene_annotation.csv` | **Gene panel source of truth** for groups L and M: 757 rows (gene × gene_group), 548 unique genes, 67 groups, 15 housekeeping. Columns include `cell_type`, `pathway`, `tme_subtype`, `prognostic_significance`, `source_article`, `provenance` |
```
**After:**
```
| `marker_gene_annotation.csv` | **Gene panel source of truth** for groups L and M: 834 rows (gene × gene_group), 633 unique genes, 63 groups, 15 housekeeping. Columns include `cell_type`, `pathway`, `tme_subtype`, `prognostic_significance`, `source_article`, `provenance` |
```

Also add a row (or extend the existing bullet list under "What is NOT here" /
architecture section) noting `Dybkaer_et_al_2015_supplementary/` alongside the
existing `Kotlov_et_al_2021_supplementary/` and `Holmes_et_al_2020_supplementary/`
entries in the "File roles" table:

**Before:**
```
| `Holmes_et_al_2020_supplementary/` | Published supplementary tables (3 `.xlsx`) read by `build_marker_gene_annotation.py` |
| `requirements.txt` | Python dependencies; **keep in sync** with the ConfigMap in `k8s/pod-metrics.yaml` |
```
**After:**
```
| `Holmes_et_al_2020_supplementary/` | Published supplementary tables (3 `.xlsx`) read by `build_marker_gene_annotation.py` |
| `Dybkaer_et_al_2015_supplementary/` | Published Data Supplement (1 `.xls`, DS1) read by `build_marker_gene_annotation.py` |
| `requirements.txt` | Python dependencies; **keep in sync** with the ConfigMap in `k8s/pod-metrics.yaml` |
```

---

## Files that do NOT need to change

- **`marker_panels.py`** — a generic loader (`panel_genes()`, `resolve_panel()`,
  `housekeeping_genes()`) driven entirely by the CSV's `gene_group`/`is_housekeeping`
  columns. It never hardcodes a gene_group name, so it needs no edits.
- **`compute_batch_metrics.py`** — Group L/M call `panel_genes(include_housekeeping=True)`
  with no group filter (confirmed at lines 1650, 1803), i.e. they consume the whole
  table generically. No edits needed.
- **`run_metrics_job.py`, `run_metrics_parallel.py`, `run_metrics_concat.py`** — none
  of these reference gene_group names or the marker CSV directly.
- **`GENE_ALIASES` in `marker_panels.py`** — none of the new Dybkaer genes need an
  alias fallback; they are already HGNC-standard symbols (`HLA-DQA1`, `HLA-DQB1`,
  etc.) with no legacy CD-name mismatch to bridge.
- **`_NON_MARKER_SYMBOL` regex** — reused unchanged. It already handles the
  non-coding-RNA / clone-ID / pseudogene classes that appear in DS1's "///"-joined
  entries (e.g. `MIR155`, `SNHG4`).
- **Any notebook or script in `harmonization-metrics/`, `figures_for_article/`, or the
  internal B-cell typing submodule** — grepped for the 6 exact removed gene_group names
  and for `panel_genes(group=...)` calls; none exist. The many other repo-wide "Normal_B_cells"
  hits are all references to the unrelated `calc_bcell_type_one_vs_all()` B-cell type
  classifier (a different system entirely, not touched by this change).
- **`figures_for_article/current_figures_tables_for_article_260819/supplementary_file_5/S5_5_marker_gene_annotation.csv`
  and `S5_6_marker_panel_summary.csv`** — these are generated snapshots exported by
  `correlation_prediction_metrics_analysis.ipynb`, not source files. They go stale
  once the CSV changes and must be regenerated by re-running that notebook after
  Group L/M metrics are recomputed (see Side effects below) — not hand-edited.

---

## Side effects and caveats

- **Metric values change.** Every previously computed `mk_*` (Group L) and `xb_*`
  (Group M) metric in `metrics_comprehensive.csv`, `marker_gene_correlations_long.csv`,
  `marker_cohort_correlations_long.csv` and any `marker_corr/*_gene_cohort.json`
  sidecar was computed against the old 548-gene panel. They are now stale and must be
  recomputed. Because the sentinel-based incremental logic in `run_metrics_job.py`
  treats a populated `mk_*`/`xb_*` key as "already done," a plain re-run will **not**
  recompute them — use `--force-groups L,M` (or delete the sidecars) when re-running
  the blind check, exactly as the existing `--force-groups` mechanism was designed for.
- **Group L reference cache is unaffected.** `--ref-cache-dir` caches the raw
  `01_raw__post0` expression matrices per `(strat, imp)`, not the gene panel — no
  cache invalidation needed there.
- **Coverage audit goes stale.** `project_overview.md` §"Gene panel" also quotes a
  coverage audit ("178 genes present in every pair... 325 in some, 45 in none") from
  `marker_gene_coverage_audit_260819.csv` in `harmonization-metrics/`. That audit was
  run against the old 548-gene panel and is now out of date. This plan does not
  attempt to hand-compute new coverage numbers (they require the real S3 expression
  matrices, not just the gene list) — flag it as a follow-up: re-run the coverage
  audit and update that paragraph once the new panel is regenerated.
- **Supplementary File 5 regeneration.** The two generated snapshots under
  `figures_for_article/current_figures_tables_for_article_260819/supplementary_file_5/`
  must be regenerated from `correlation_prediction_metrics_analysis.ipynb` after the
  new panel and recomputed metrics land — not part of this code change, but a
  necessary downstream step before the article's Supplementary File 5 is next updated.
- **9 genes vanish from the whole table**: `BCL10`, `BIRC5`, `CARD11`, `DUSP5`,
  `DUSP6`, `IKBKB`, `IKBKG`, `MALT1`, `NR4A1` — these only appeared in the removed
  `FL_pathway_*` blocks and have no Dybkaer counterpart. If any downstream analysis
  queries these symbols directly against `marker_gene_annotation.csv` (rather than
  through `panel_genes()`), it will silently get zero rows back — grepped for this
  above and found none, but flagging for awareness.
- **`xlrd` install.** `xlrd>=2.0.1` only supports legacy `.xls`, not `.xlsx` — it
  does not conflict with or replace `openpyxl`, which still handles the Kotlov/Holmes
  `.xlsx` files. Both are needed simultaneously by `build_marker_gene_annotation.py`.

---

## Verification commands

```bash
source ~/venvs/collagen_3_11/bin/activate
pip install xlrd  # if not already present locally; already added to requirements.txt

cd harmonization-metrics-calculation

# Regenerate the CSV and check the printed summary matches the totals table above
python build_marker_gene_annotation.py
# Expect: rows (gene x gene_group): 834 / unique genes: 633 / gene groups: 63 / housekeeping genes: 15

# Confirm the old blocks are gone and the new ones are present
python -c "
import pandas as pd
df = pd.read_csv('marker_gene_annotation.csv')
old = {'legacy_centroblast_DZ','legacy_centrocyte_LZ','FL_pathway_BCR','FL_pathway_NFkB','FL_pathway_PI3K_AKT','FL_pathway_GCB_markers'}
assert not (set(df.gene_group) & old), 'old Normal_B_cells groups still present'
assert {'dybkaer_centroblast_DZ','dybkaer_centrocyte_LZ'} <= set(df.gene_group)
assert (df.source_article == 'an internal, unpublished centroblast/centrocyte panel').sum() == 0
print('OK:', df.gene_group.nunique(), 'groups,', df.gene.nunique(), 'genes')
"

# marker_panels.py loader smoke test
python -c "
from marker_panels import panel_genes, panel_summary
cb = panel_genes('dybkaer_centroblast_DZ')
cc = panel_genes('dybkaer_centrocyte_LZ')
print('centroblast:', len(cb), 'centrocyte:', len(cc))
assert len(cb) == 69 and len(cc) == 55
print(panel_summary().query(\"gene_group.str.startswith('dybkaer')\"))
"

# Existing smoke test still passes (no group-L/M-specific asserts broken)
python test_mock_metrics.py

# Single-job Group L/M check against the new panel (fast, no full pipeline run)
python run_metrics_job.py \
    --strat A_confirmed_bad --imp strict --method 16_fsqn_r \
    --post-rm False \
    --out-json /tmp/test_metrics_dybkaer.json \
    --out-genes-json /tmp/test_genes.json \
    --groups L,M --force-groups L,M
python -c "import json; d=json.load(open('/tmp/test_metrics_dybkaer.json')); print(d.get('mk_n_panel_genes_used'), d.get('mk_rho_mean_all_genes'))"
```

---

## TODO

- [x] `build_marker_gene_annotation.py` — remove the `Normal_B_cells` constant; add `DYBKAER` constant
- [x] `build_marker_gene_annotation.py` — remove `legacy_centroblast_DZ` and `legacy_centrocyte_LZ` blocks
- [x] `build_marker_gene_annotation.py` — remove `FL_pathway_BCR`, `FL_pathway_NFkB`, `FL_pathway_PI3K_AKT`, `FL_pathway_GCB_markers` blocks
- [x] `build_marker_gene_annotation.py` — add `DYBKAER_DS1_XLS` path constant
- [x] `build_marker_gene_annotation.py` — add `dybkaer_gc_subset_blocks()` function
- [x] `build_marker_gene_annotation.py` — register `dybkaer_gc_subset_blocks()` in `all_blocks()`
- [x] `build_marker_gene_annotation.py` — add `dybkaer_table_ds1` to the module docstring's provenance list
- [x] `build_marker_gene_annotation.py` — update the "Supplementary-table readers" section comment ("two" → "three" spreadsheets)
- [x] `requirements.txt` — add `xlrd>=2.0.1`
- [x] `k8s/pod-metrics.yaml` — add `xlrd>=2.0.1` to the embedded ConfigMap `requirements.txt` block
- [x] `project_overview.md` — update gene panel summary counts (548→633 genes, 67→63 signatures, 757→834 rows) and cite Dybkaer DS1
- [x] `project_overview.md` — update the §11 curated gene sets line to cite Dybkaer instead of "Normal_B_cells ... internal"
- [x] `CLAUDE.md` (root) — update marker_gene_annotation.csv row in Key Files table (548→633, 67→63)
- [x] `harmonization-metrics-calculation/CLAUDE.md` — update marker_gene_annotation.csv row (757→834 rows, 548→633 genes, 67→63 groups)
- [x] `harmonization-metrics-calculation/CLAUDE.md` — add `Dybkaer_et_al_2015_supplementary/` row to the File roles table
- [x] Run `python build_marker_gene_annotation.py` to regenerate `marker_gene_annotation.csv`; confirm printed summary is 834/633/63/15 (matched exactly: 834 rows / 633 genes / 63 groups / 15 housekeeping)
- [x] Run the verification script confirming old groups absent, new groups present, gene counts match (all assertions passed)
- [x] Run `python test_mock_metrics.py` (requires live pod/venv — this machine has no `~/venvs/collagen_3_11` and lacks scipy/sklearn/statsmodels entirely, a pre-existing local environment gap unrelated to this change since `compute_batch_metrics.py` was not touched; ran the equivalent local checks instead: CSV rebuild, old-group-absence/new-group-presence assertions, and the `marker_panels.panel_genes()`/`panel_summary()` loader smoke test, all passing)
- [ ] Run a single Group L/M job with `--force-groups L,M` against the new panel and sanity-check `mk_n_panel_genes_used` (requires live pod: S3 access + boto3 + full R/Python metrics environment, none of which exist on this machine)
- [ ] Flag as follow-up (not part of this change): re-run the marker gene coverage audit and refresh the "178 genes present in every pair" paragraph in `project_overview.md`
- [ ] Flag as follow-up (not part of this change): recompute Group L/M metrics with `--force-groups L,M` for the full blind-check job set and regenerate Supplementary File 5
