"""
marker_panels.py — Loader for the marker gene annotation table.

Thin accessor over marker_gene_annotation.csv, which is the single source of truth
for the gene panels used by metric group L (marker correlation preservation) and
group M (cross-batch rank agreement). Regenerate the CSV with
build_marker_gene_annotation.py; never hardcode gene lists here.

The table key is (gene, gene_group): a gene may belong to several signatures, so the
CSV has one row per membership. panel_genes() de-duplicates on gene.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

ANNOTATION_CSV = Path(__file__).parent / "marker_gene_annotation.csv"

# Alias fallbacks tried when the HGNC primary symbol is absent from an expression
# matrix. Older array platforms and some legacy annotations still carry the CD name.
GENE_ALIASES: dict[str, list[str]] = {
    "MS4A1": ["CD20"],
    "MME": ["CD10"],
    "FCER2": ["CD23"],
    "CR2": ["CD21"],
    "CR1": ["CD35"],
    "PTPRC": ["CD45"],
    "PDCD1": ["CD279"],
    "CD274": ["PDL1", "PD-L1"],
    "FAS": ["TNFRSF6", "CD95"],
    "GCSAM": ["HGAL"],
    "NCAM1": ["CD56"],
    "IL2RA": ["CD25"],
    "SELL": ["CD62L"],
    "THY1": ["CD90"],
    "PECAM1": ["CD31"],
    "TNFRSF17": ["BCMA"],
    "HAVCR2": ["TIM3"],
    "VSIR": ["VISTA", "C10orf54"],
    "EBI3": ["IL27B"],
}


@lru_cache(maxsize=1)
def load_marker_annotation() -> pd.DataFrame:
    """
    Load the marker gene annotation table.

    Returns
    -------
    pd.DataFrame
        One row per (gene, gene_group) with columns: gene, alias, gene_group,
        cell_type, pathway, tme_subtype, prognostic_significance, source_article,
        provenance, is_housekeeping.
    """
    df = pd.read_csv(ANNOTATION_CSV)
    df["is_housekeeping"] = df["is_housekeeping"].astype(bool)
    return df


def panel_genes(
    group: Optional[str | Iterable[str]] = None,
    include_housekeeping: bool = False,
) -> list[str]:
    """
    Return the sorted unique gene symbols of a panel.

    Parameters
    ----------
    group : str or iterable of str, optional
        Restrict to these gene_group values. Default: every group.
    include_housekeeping : bool
        Whether to include the housekeeping control genes. They are excluded by
        default because most callers want the biologically variable markers only.

    Returns
    -------
    list of str
    """
    df = load_marker_annotation()
    if group is not None:
        groups = {group} if isinstance(group, str) else set(group)
        df = df[df["gene_group"].isin(groups)]
    if not include_housekeeping:
        df = df[~df["is_housekeeping"]]
    return sorted(df["gene"].unique().tolist())


def housekeeping_genes() -> list[str]:
    """Return the sorted housekeeping control gene symbols."""
    df = load_marker_annotation()
    return sorted(df.loc[df["is_housekeeping"], "gene"].unique().tolist())


def gene_to_groups() -> dict[str, list[str]]:
    """Return {gene: [gene_group, ...]} for every gene in the table."""
    df = load_marker_annotation()
    return df.groupby("gene")["gene_group"].apply(lambda s: sorted(set(s))).to_dict()


def gene_to_cell_types() -> dict[str, list[str]]:
    """Return {gene: [cell_type, ...]} excluding the 'none' placeholder."""
    df = load_marker_annotation()
    df = df[df["cell_type"] != "none"]
    return df.groupby("gene")["cell_type"].apply(lambda s: sorted(set(s))).to_dict()


def resolve_panel(
    available: set[str], panel: Optional[list[str]] = None
) -> tuple[list[str], list[str]]:
    """
    Match a panel against the genes actually present in an expression matrix.

    Falls back to GENE_ALIASES when the HGNC primary symbol is absent, so a matrix
    that still carries a legacy CD name is not silently penalised.

    Parameters
    ----------
    available : set of str
        Gene symbols present in the expression matrix.
    panel : list of str, optional
        Genes to resolve. Default: every gene in the annotation table, housekeeping
        genes included.

    Returns
    -------
    tuple of (resolved, missing)
        resolved: the symbols to use, as they appear in `available`.
        missing:  panel entries with no match under any alias.
    """
    if panel is None:
        panel = panel_genes(include_housekeeping=True)

    resolved: list[str] = []
    missing: list[str] = []
    for gene in panel:
        if gene in available:
            resolved.append(gene)
            continue
        hit = next((a for a in GENE_ALIASES.get(gene, []) if a in available), None)
        if hit is not None:
            resolved.append(hit)
        else:
            missing.append(gene)
    return sorted(set(resolved)), sorted(set(missing))


def panel_summary() -> pd.DataFrame:
    """
    Per-gene_group counts for the article's supplementary table.

    Returns
    -------
    pd.DataFrame
        Columns: gene_group, n_genes, cell_type, pathway, tme_subtype,
        prognostic_significance, source_article.
    """
    df = load_marker_annotation()
    agg = (
        df.groupby("gene_group")
        .agg(
            n_genes=("gene", "nunique"),
            cell_type=("cell_type", lambda s: sorted(set(s))[0]),
            pathway=("pathway", lambda s: sorted(set(s))[0]),
            tme_subtype=("tme_subtype", lambda s: sorted(set(s))[0]),
            prognostic_significance=(
                "prognostic_significance",
                lambda s: sorted(set(s))[0],
            ),
            source_article=("source_article", lambda s: sorted(set(s))[0]),
        )
        .reset_index()
    )
    return agg.sort_values("gene_group").reset_index(drop=True)
