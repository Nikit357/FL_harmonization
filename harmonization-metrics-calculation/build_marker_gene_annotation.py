"""
build_marker_gene_annotation.py — Generate marker_gene_annotation.csv.

The CSV is the single source of truth for the gene panels used by metric groups L
(marker correlation preservation) and M (cross-batch rank agreement). This script
builds it so that every gene's provenance stays reviewable and the table can be
regenerated after a correction.

Run once; commit both this script and the resulting CSV:

    python build_marker_gene_annotation.py

Provenance values
-----------------
article_text
    The gene symbol is explicitly printed in the source article's text, figures or
    tables as retrieved from PubMed Central.
canonical_marker
    An established marker for that cell type / state in the germinal centre and
    lymphoma literature. Used only where the source article publishes no explicit
    gene list for that signature (Kotlov's PROGENy pathway scores, and the
    dendritic-cell and cytolytic panels that have no counterpart in Table S1).
kotlov_table_s1
    Read verbatim from Kotlov et al. 2021 supplementary Table S1 (the FGES gene
    sets) or Tables S2/S3 (the cell-of-origin and double-hit classifier panels).
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
    Copied from the panels already defined in insert_cells.py lines 1611-1657.
housekeeping
    Invariant-expression control panel; see the note in the plan on why these are
    expected to behave differently from biologically variable markers.

A gene may appear in several signatures, so (gene, gene_group) is the table key,
not gene alone. panel_genes() in marker_panels.py de-duplicates on gene.
"""

from __future__ import annotations

import re
from pathlib import Path

import openpyxl
import pandas as pd

OUT_CSV = Path(__file__).parent / "marker_gene_annotation.csv"

# (gene_group, cell_type, pathway, tme_subtype, prognostic, source, provenance, genes)
Block = tuple[str, str, str, str, str, str, str, list[str]]

KOTLOV = "Kotlov et al. 2021 Cancer Discov, PMC8178179"
HOLMES = "Holmes et al. 2020 J Exp Med 217(10):e20200483, PMC7537389"
XOCHELLI = "Xochelli et al. 2025 Leukemia, doi:10.1038/s41375-025-02603-9"
DYBKAER = "Dybkaer et al. 2015 J Clin Oncol 33(12):1379-1388, PMC4397280"
PASTORE = "Pastore et al. 2019, PMID 29475724"
IHC = "Routine diagnostic immunohistochemistry panel (WHO B-cell lymphoma criteria)"
HK = "Standard RT-qPCR reference gene panel"

# Signatures whose gene lists are not read from a supplementary spreadsheet.
# alias is filled from ALIAS_MAP below.
BLOCKS: list[Block] = [
    # ── 1. Clinical / IHC diagnostic markers ──────────────────────────────────
    (
        "clinical_IHC_B_cell",
        "B cell",
        "none",
        "none",
        "none",
        IHC,
        "article_text",
        ["MS4A1", "CD19", "CD79A", "CD79B", "PAX5", "CD22"],
    ),
    (
        "clinical_IHC_GC_B_cell",
        "germinal centre B",
        "none",
        "GC-like",
        "none",
        IHC,
        "article_text",
        ["MME", "BCL6", "BCL2", "LMO2", "GCSAM"],
    ),
    (
        "clinical_IHC_post_GC",
        "plasma cell",
        "none",
        "none",
        "none",
        IHC,
        "article_text",
        ["IRF4", "PRDM1", "XBP1", "MZB1"],
    ),
    (
        "clinical_IHC_proliferation",
        "none",
        "proliferation",
        "none",
        "adverse (OS, PFS)",
        IHC,
        "article_text",
        ["MKI67", "MYC"],
    ),
    (
        "clinical_IHC_T_cell",
        "CD4 T",
        "none",
        "inflammatory",
        "none",
        IHC,
        "article_text",
        ["CD3D", "CD3E", "CD3G", "CD2", "CD5", "CD4", "CD7"],
    ),
    (
        "clinical_IHC_T_cell_cytotoxic",
        "CD8 T",
        "none",
        "inflammatory",
        "none",
        IHC,
        "article_text",
        ["CD8A", "CD8B"],
    ),
    (
        "clinical_IHC_myeloid",
        "macrophage",
        "none",
        "inflammatory",
        "none",
        IHC,
        "article_text",
        ["CD68", "CD163", "PTPRC"],
    ),
    (
        "clinical_IHC_follicular_stroma",
        "follicular dendritic",
        "none",
        "GC-like",
        "none",
        IHC,
        "article_text",
        ["CR2", "FCER2"],
    ),
    (
        "clinical_IHC_checkpoint",
        "CD8 T",
        "none",
        "inflammatory",
        "none",
        IHC,
        "article_text",
        ["PDCD1", "LAG3", "TNFRSF9", "CD274", "IDO1", "FOXP3"],
    ),
    # ── 2. Kotlov 2021 — LME functional gene expression signatures ────────────
    # The four LME subtypes (GC-like, mesenchymal, inflammatory, depleted) and the
    # 25 FGES names are stated in the article text; the constituent gene lists are
    # in supplementary Table S1 only.
    (
        "kotlov_FGES_cytolytic",
        "CD8 T",
        "none",
        "inflammatory",
        "favourable (OS)",
        KOTLOV,
        "canonical_marker",
        ["GZMA", "GZMB", "GZMH", "GZMK", "PRF1", "NKG7", "GNLY", "KLRD1"],
    ),
    (
        "kotlov_FGES_dendritic_cells",
        "macrophage",
        "none",
        "inflammatory",
        "none",
        KOTLOV,
        "canonical_marker",
        ["ITGAX", "CD1C", "LAMP3", "CLEC9A", "FLT3"],
    ),
    (
        "kotlov_FGES_interferon",
        "none",
        "interferon",
        "inflammatory",
        "none",
        KOTLOV,
        "canonical_marker",
        ["STAT1", "ISG15", "MX1", "OAS1", "IFIT1", "IFIT3", "IFI27", "IFI44", "IRF7"],
    ),
    (
        "kotlov_FGES_NFkB",
        "none",
        "NF-kB",
        "none",
        "none",
        KOTLOV,
        "canonical_marker",
        ["NFKB1", "NFKB2", "REL", "RELA", "RELB", "NFKBIA", "TNFAIP3", "BIRC3", "CD40"],
    ),
    (
        "kotlov_FGES_PI3K",
        "none",
        "PI3K-AKT",
        "none",
        "none",
        KOTLOV,
        "canonical_marker",
        [
            "PIK3CA",
            "PIK3CB",
            "PIK3CD",
            "AKT1",
            "AKT2",
            "AKT3",
            "PTEN",
            "MTOR",
            "RPS6KB1",
        ],
    ),
    (
        "kotlov_FGES_TGFB",
        "stromal/fibroblast",
        "none",
        "mesenchymal",
        "none",
        KOTLOV,
        "article_text",
        ["TGFB1", "TGFBR1", "TGFBR2", "SMAD1", "SMAD2", "SMAD3", "SMAD7", "SERPINE1"],
    ),
    (
        "kotlov_FGES_hypoxia",
        "none",
        "none",
        "mesenchymal",
        "none",
        KOTLOV,
        "canonical_marker",
        ["HIF1A", "SLC2A1", "LDHA", "CA9", "ADM"],
    ),
    (
        "kotlov_curated_alterations",
        "none",
        "epigenetic",
        "none",
        "none",
        KOTLOV,
        "article_text",
        [
            "MYD88",
            "CD79B",
            "EZH2",
            "CREBBP",
            "EP300",
            "KMT2D",
            "TP53",
            "GNA13",
            "CCND3",
            "GNAI2",
            "P2RY8",
            "CD70",
            "CDKN2A",
        ],
    ),
    # ── 3. Holmes 2020 — single-cell germinal centre B-cell states ─────────────
    # The 13 single-cell cluster signatures are read from Table S2 by
    # holmes_gc_state_blocks(); only the double-hit pair below is text-only.
    (
        "holmes_double_hit_signature",
        "centroblast (DZ)",
        "proliferation",
        "none",
        "adverse (PFS)",
        HOLMES,
        "article_text",
        ["MYC", "BCL2"],
    ),
    # ── 4. Panels already used in the project (insert_cells.py:1611-1657) ─────
    (
        "FL2025_C1_DZ_proliferative",
        "centroblast (DZ)",
        "proliferation",
        "none",
        "adverse (PFS)",
        XOCHELLI,
        "repo_panel",
        [
            "MKI67",
            "TOP2A",
            "PCNA",
            "MCM2",
            "MCM6",
            "CCND2",
            "CDK4",
            "AICDA",
            "MYBL1",
            "CENPF",
            "UBE2C",
            "RRM2",
            "TYMS",
            "GINS2",
        ],
    ),
    (
        "FL2025_C2_LZ_anergy",
        "centrocyte (LZ)",
        "apoptosis",
        "none",
        "none",
        XOCHELLI,
        "repo_panel",
        [
            "BCL2",
            "CXCR4",
            "CD83",
            "FCER2",
            "CD79A",
            "IGHM",
            "IGHD",
            "IRF4",
            "PRDM1",
            "FAS",
        ],
    ),
    (
        "FL2025_C3_inflammatory",
        "none",
        "interferon",
        "inflammatory",
        "none",
        XOCHELLI,
        "repo_panel",
        [
            "CXCL9",
            "CXCL10",
            "CXCL11",
            "STAT1",
            "IFI27",
            "IFI44",
            "IFIT1",
            "IFIT3",
            "ISG15",
            "MX1",
            "OAS1",
            "IFI16",
        ],
    ),
    (
        "FL_PFS_signature_2019",
        "none",
        "none",
        "none",
        "adverse (PFS)",
        PASTORE,
        "repo_panel",
        ["LMO2", "FN1", "CCND2", "BCL6", "CCL3", "LRMP", "MKI67", "BCL2", "CDKN2A"],
    ),
    (
        "FL_POD24_markers",
        "none",
        "epigenetic",
        "none",
        "adverse (POD24)",
        PASTORE,
        "repo_panel",
        ["EZH2", "BCL2", "CCND3", "TNFRSF14", "KMT2D", "FOXO1", "CREBBP", "EP300"],
    ),
    # ── 5. Housekeeping negative control ─────────────────────────────────────
    (
        "housekeeping",
        "none",
        "none",
        "none",
        "none",
        HK,
        "housekeeping",
        [
            "ACTB",
            "GAPDH",
            "TUBB",
            "B2M",
            "PPIA",
            "RPLP0",
            "TBP",
            "PGK1",
            "SDHA",
            "HPRT1",
            "UBC",
            "YWHAZ",
            "RPL13A",
            "EEF1A1",
            "PSMB4",
        ],
    ),
]

# IHC / clinical aliases, so the article can name the marker the way a pathologist does.
ALIAS_MAP: dict[str, str] = {
    "MS4A1": "CD20",
    "MME": "CD10",
    "FCER2": "CD23",
    "CR2": "CD21",
    "CR1": "CD35",
    "PTPRC": "CD45",
    "IRF4": "MUM1",
    "MKI67": "Ki-67",
    "PDCD1": "PD-1",
    "CD274": "PD-L1",
    "PDCD1LG2": "PD-L2",
    "TNFRSF9": "CD137",
    "PRDM1": "BLIMP1",
    "NCAM1": "CD56",
    "FCGR3A": "CD16",
    "ITGAX": "CD11c",
    "TNFRSF17": "BCMA",
    "HAVCR2": "TIM-3",
    "VSIR": "VISTA",
    "IL2RA": "CD25",
    "TNFRSF18": "GITR",
    "SELL": "CD62L",
    "THY1": "CD90",
    "PECAM1": "CD31",
    "CDH5": "VE-cadherin",
    "KDR": "VEGFR2",
    "FLT4": "VEGFR3",
    "PDPN": "podoplanin",
    "ACTA2": "SMA",
    "ICOS": "CD278",
    "CTLA4": "CD152",
    "TCF7": "TCF1",
    "FAS": "CD95",
    "GCSAM": "HGAL",
    "MRC1": "CD206",
    "CSF1R": "CD115",
    "ENG": "CD105",
}


# ── Supplementary-table readers ───────────────────────────────────────────────
# The three spreadsheets are committed next to this script so the CSV stays
# regenerable. Kotlov Table S1 lists the FGES gene sets verbatim; Holmes Table S2
# lists per-cluster differential genes already ordered by log2 fold change, which
# is why "top N" is a well-defined signature rather than an arbitrary slice. Dybkaer
# DS1 is a classifier weight matrix (Kotlov/Holmes are differential-expression
# tables), so its selection rule is "nonzero weight" rather than a fold-change cutoff.

KOTLOV_XLSX = (
    Path(__file__).parent
    / "Kotlov_et_al_2021_supplementary"
    / "NIHMS1669159-supplement-2.xlsx"
)
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

# Symbols in Holmes Table S2 that are clone IDs, mitochondrial transcripts,
# non-coding RNAs or obvious pseudogenes. They never appear in the benchmark's
# HGNC-mapped matrices, so keeping them would only depress mk_n_panel_genes_used.
_NON_MARKER_SYMBOL = re.compile(
    r"""
    ^7SK$                        # small nuclear RNA
    | \.                         # versioned Ensembl clone IDs (AC034236.1)
    | ^(AC|AL|AP|AF|BX|CH507)\d  # unnamed clone IDs
    | ^MT-                       # mitochondrial transcripts
    | ^SNHG\d | ^LINC\d | ^MIR   # non-coding RNA families
    | -AS\d+$                    # antisense transcripts
    | ^RP[LS]\d+[A-Z]*P\d+$      # ribosomal protein pseudogenes
    """,
    re.VERBOSE,
)

# Which LME subtype each Kotlov FGES is enriched in, as (cell_type, pathway,
# tme_subtype). Table S1 carries only the gene sets, so the subtype assignment
# comes from the paper's definition of the four microenvironmental subtypes and
# not from a spreadsheet column. prognostic_significance stays "none" because
# Table S1 reports no per-gene outcome association.
KOTLOV_FGES_ANNOTATION: dict[str, tuple[str, str, str]] = {
    "LEC": ("endothelial", "none", "mesenchymal"),
    "VEC": ("endothelial", "none", "mesenchymal"),
    "CAF": ("stromal/fibroblast", "none", "mesenchymal"),
    "FRC": ("stromal/fibroblast", "none", "mesenchymal"),
    "ECM": ("stromal/fibroblast", "none", "mesenchymal"),
    "ECM remodeling": ("stromal/fibroblast", "none", "mesenchymal"),
    "granulocyte traffic": ("none", "none", "inflammatory"),
    "IS cytokines": ("none", "none", "inflammatory"),
    "FDC": ("follicular dendritic", "none", "GC-like"),
    "macrophages": ("macrophage", "none", "inflammatory"),
    "activated M1": ("macrophage", "none", "inflammatory"),
    "T cells traffic": ("none", "interferon", "inflammatory"),
    "MHC-II": ("none", "none", "GC-like"),
    "MHC-I": ("none", "none", "inflammatory"),
    "TFH": ("CD4 T", "none", "GC-like"),
    "Treg": ("Treg", "none", "inflammatory"),
    "TIL": ("CD4 T", "none", "inflammatory"),
    "IS checkpoints": ("none", "none", "inflammatory"),
    "NK": ("NK", "none", "inflammatory"),
    "B cells traffic": ("B cell", "none", "GC-like"),
    "B cells": ("B cell", "none", "GC-like"),
    "cell proliferation": ("none", "proliferation", "depleted"),
}

# Holmes single-cell clusters grouped into the five GC B-cell states, as
# (cell_type, pathway, tme_subtype, prognostic_significance). The prognostic
# strings are the paper's family-level outcome statements.
HOLMES_CLUSTER_ANNOTATION: dict[str, tuple[str, str, str, str]] = {
    **{
        cluster: (
            "centroblast (DZ)",
            "proliferation",
            "GC-like",
            "adverse (PFS; DZ signature enriched in MYC/BCL2 double-hit)",
        )
        for cluster in ("DZ-a", "DZ-b", "DZ-c")
    },
    **{
        cluster: (
            "centrocyte (LZ)",
            "none",
            "GC-like",
            "mixed (INT-b/INT-e associate with the EZB genetic group)",
        )
        for cluster in ("INT-a", "INT-b", "INT-c", "INT-d", "INT-e")
    },
    **{
        cluster: (
            "centrocyte (LZ)",
            "NF-kB",
            "GC-like",
            "favourable (PFS; late-LZ/INT Group IV best PFS)",
        )
        for cluster in ("LZ-a", "LZ-b")
    },
    "PreM": ("memory precursor", "none", "GC-like", "favourable (PFS, Group V)"),
    **{
        cluster: ("plasma cell", "none", "none", "mixed (Group V)")
        for cluster in ("PBL-a", "PBL-b")
    },
}


def _clean_symbols(raw: list) -> list[str]:
    """Strip whitespace, drop blanks and non-marker symbols, de-duplicate in order."""
    seen: set[str] = set()
    out: list[str] = []
    for value in raw:
        gene = str(value).strip()
        if not gene or gene in seen or _NON_MARKER_SYMBOL.search(gene):
            continue
        seen.add(gene)
        out.append(gene)
    return out


def _sheet_rows(xlsx: Path, sheet: str) -> list[tuple]:
    """Read one worksheet of an .xlsx file into a list of value tuples."""
    workbook = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    try:
        return list(workbook[sheet].iter_rows(values_only=True))
    finally:
        workbook.close()


def kotlov_fges_blocks() -> list[Block]:
    """Build one block per gene-based FGES in Kotlov Table S1.

    Returns
    -------
    list[Block]
        22 blocks. The three PROGENy rows (NFkB, PI3K, p53) hold the literal
        "PROGENY" instead of a gene list and are skipped.
    """
    rows = _sheet_rows(KOTLOV_XLSX, "Table S1")
    sheet_fges = {str(r[0]).strip() for r in rows[1:] if r[0]}
    unknown = set(KOTLOV_FGES_ANNOTATION) - sheet_fges
    if unknown:
        raise ValueError(f"FGES annotated here but absent from Table S1: {unknown}")

    blocks: list[Block] = []
    for row in rows[1:]:
        fges = str(row[0]).strip() if row[0] else ""
        genes = _clean_symbols([c for c in row[2:] if c is not None])
        if fges not in KOTLOV_FGES_ANNOTATION or genes == ["PROGENY"]:
            continue
        cell_type, pathway, tme = KOTLOV_FGES_ANNOTATION[fges]
        group = "kotlov_FGES_" + fges.replace("-", "_").replace(" ", "_")
        blocks.append(
            (group, cell_type, pathway, tme, "none", KOTLOV, "kotlov_table_s1", genes)
        )
    return blocks


def kotlov_classifier_blocks() -> list[Block]:
    """Build the cell-of-origin (Table S2) and double-hit (Table S3) classifier panels.

    Returns
    -------
    list[Block]
        Two blocks; the Shapley-importance column is not carried into the CSV.
    """
    specs = [
        ("Table S2", "kotlov_COO_classifier", "germinal centre B", "GC-like"),
        ("Table S3", "kotlov_DHIT_classifier", "centroblast (DZ)", "none"),
    ]
    blocks: list[Block] = []
    for sheet, group, cell_type, tme in specs:
        rows = _sheet_rows(KOTLOV_XLSX, sheet)
        genes = _clean_symbols([r[0] for r in rows[1:] if r and r[0]])
        blocks.append(
            (group, cell_type, "none", tme, "none", KOTLOV, "kotlov_table_s1", genes)
        )
    return blocks


def holmes_gc_state_blocks() -> list[Block]:
    """Build one block per Holmes GC B-cell cluster from the Table S2 "UP" columns.

    Only the up-regulated lists are used: they define what the cluster expresses,
    whereas each "DWN" list describes the other clusters. Genes are already ordered
    by log2 fold change, so the first HOLMES_TOP_N_UP surviving symbols are the
    strongest markers of that state.

    Returns
    -------
    list[Block]
        13 blocks, one per single-cell cluster (DZ-a/b/c, INT-a-e, LZ-a/b, PreM,
        PBL-a/b).
    """
    rows = _sheet_rows(HOLMES_XLSX, "Table_S2")
    header = rows[2]
    blocks: list[Block] = []
    for col, label in enumerate(header):
        if not label or not str(label).endswith(" UP"):
            continue
        cluster = str(label)[: -len(" UP")].strip()
        cell_type, pathway, tme, prognostic = HOLMES_CLUSTER_ANNOTATION[cluster]
        column = [r[col] for r in rows[4:] if col < len(r) and r[col] is not None]
        genes = _clean_symbols(column)[:HOLMES_TOP_N_UP]
        group = "holmes_" + cluster.replace("-", "_")
        blocks.append(
            (
                group,
                cell_type,
                pathway,
                tme,
                prognostic,
                HOLMES,
                "holmes_table_s2",
                genes,
            )
        )
    return blocks


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


def all_blocks() -> list[Block]:
    """Static blocks plus every block read from the supplementary spreadsheets."""
    return (
        BLOCKS
        + kotlov_fges_blocks()
        + kotlov_classifier_blocks()
        + holmes_gc_state_blocks()
        + dybkaer_gc_subset_blocks()
    )


def build() -> pd.DataFrame:
    """Expand every block into one row per (gene, gene_group) and attach aliases."""
    rows: list[dict] = []
    for group, cell_type, pathway, tme, prog, source, provenance, genes in all_blocks():
        for gene in genes:
            rows.append(
                {
                    "gene": gene,
                    "alias": ALIAS_MAP.get(gene, ""),
                    "gene_group": group,
                    "cell_type": cell_type,
                    "pathway": pathway,
                    "tme_subtype": tme,
                    "prognostic_significance": prog,
                    "source_article": source,
                    "provenance": provenance,
                    "is_housekeeping": provenance == "housekeeping",
                }
            )
    df = pd.DataFrame(rows)
    # A gene may legitimately sit in several signatures, but never twice in one.
    df = df.drop_duplicates(subset=["gene", "gene_group"]).reset_index(drop=True)
    return df.sort_values(["gene_group", "gene"]).reset_index(drop=True)


def main() -> None:
    df = build()
    df.to_csv(OUT_CSV, index=False)
    print(f"Wrote {OUT_CSV}")
    print(f"  rows (gene x gene_group): {len(df)}")
    print(f"  unique genes:             {df['gene'].nunique()}")
    print(f"  gene groups:              {df['gene_group'].nunique()}")
    print(f"  housekeeping genes:       {int(df['is_housekeeping'].sum())}")
    print("\nprovenance:")
    print(df["provenance"].value_counts().to_string())
    print("\ncell_type:")
    print(df["cell_type"].value_counts().to_string())


if __name__ == "__main__":
    main()
