"""
gene_panel_structure.py — Library for the marker gene panel deep analysis.

Pure functions, no S3 access and no CLI, so every function can be exercised on
synthetic data by test_mock_gene_structure.py. Three products:

    gene_gene_correlation()              gene x gene correlation over all samples
    gene_gene_correlation_within_cohort() same, computed inside each cohort and
                                          Fisher-z averaged across cohorts
    gene_expression_qc()                  per-gene expression quality statistics

The within-cohort flavour is the biologically meaningful one: a global correlation
between two genes can be produced entirely by batch structure (both genes higher on
one platform than another) without the genes being co-expressed in any single cohort.
The two flavours are computed together so the difference can be shown.

This module is deliberately separate from compute_batch_metrics.py: the metric group
functions there all return dict[str, float] sidecar payloads, while these return
matrices and DataFrames, and adding them to compute_all_metrics() would invalidate the
existing metrics sidecars.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import rankdata

sys.path.insert(0, str(Path(__file__).parent.parent))
from compute_batch_metrics import MIN_COHORT_N

# ── Constants ─────────────────────────────────────────────────────────────────

# arctanh(1.0) is inf, and a Spearman correlation of exactly +-1 is common in small
# cohorts, so |r| is clipped just short of 1 before every Fisher transform.
FISHER_CLIP: float = 1.0 - 1e-6

# All expression in this project is log2(x + 1), so a value below 1.0 on that scale
# corresponds to a linear expression below 1 — the "barely detected" band.
LOW_EXPRESSION_THRESHOLD: float = 1.0

COHORT_COL_PREFERENCE: tuple[str, ...] = ("COHORT_LABEL", "RNA_BATCH")


# ── Fisher z ──────────────────────────────────────────────────────────────────


def fisher_z(r: np.ndarray) -> np.ndarray:
    """
    Fisher z-transform with clipping.

    Parameters
    ----------
    r : np.ndarray
        Correlation coefficients; NaN is propagated.

    Returns
    -------
    np.ndarray
        arctanh(r) with |r| clipped to FISHER_CLIP so +-1 does not become +-inf.
    """
    r_arr = np.asarray(r, dtype=float)
    return np.arctanh(np.clip(r_arr, -FISHER_CLIP, FISHER_CLIP))


def inverse_fisher_z(z: np.ndarray) -> np.ndarray:
    """Back-transform Fisher z to a correlation coefficient."""
    return np.tanh(np.asarray(z, dtype=float))


# ── Upper triangle packing ────────────────────────────────────────────────────


def pack_upper_triangle(mat: np.ndarray, dtype: type = np.float16) -> np.ndarray:
    """
    Flatten the strict upper triangle of a symmetric matrix.

    Storing G(G-1)/2 values instead of G^2 halves the payload, and float16 halves it
    again; correlations are only used here for clustering and thresholding, where
    three decimal digits are ample.

    Parameters
    ----------
    mat : np.ndarray
        Square symmetric matrix.
    dtype : type
        Storage dtype of the returned vector.

    Returns
    -------
    np.ndarray
        Row-major strict upper triangle, length G(G-1)/2.
    """
    n = mat.shape[0]
    iu = np.triu_indices(n, k=1)
    return np.asarray(mat, dtype=float)[iu].astype(dtype)


def unpack_upper_triangle(vec: np.ndarray, n: int) -> np.ndarray:
    """
    Rebuild a symmetric matrix from a packed strict upper triangle.

    Parameters
    ----------
    vec : np.ndarray
        Output of pack_upper_triangle.
    n : int
        Side length of the original matrix.

    Returns
    -------
    np.ndarray
        Symmetric float64 matrix with 1.0 on the diagonal.
    """
    out = np.eye(n, dtype=float)
    iu = np.triu_indices(n, k=1)
    vals = np.asarray(vec, dtype=float)
    out[iu] = vals
    out[(iu[1], iu[0])] = vals
    return out


# ── Shared helpers ────────────────────────────────────────────────────────────


def cohort_labels(ann_df: pd.DataFrame) -> np.ndarray:
    """
    Cohort assignment per sample, using the same column choice as metric group L.

    COHORT_LABEL is preferred; RNA_BATCH is the fallback for annotations that predate
    it. Falls back to a single pseudo-cohort so a matrix with neither column still
    produces a result rather than an exception.
    """
    for col in COHORT_COL_PREFERENCE:
        if col in ann_df.columns:
            return ann_df[col].astype(str).values
    return np.array(["all"] * len(ann_df))


def _resolve_genes(exp_df: pd.DataFrame, genes: list[str]) -> list[str]:
    """Panel genes present in the matrix, in the panel's own order, de-duplicated."""
    available = set(exp_df.columns)
    seen: set[str] = set()
    out: list[str] = []
    for gene in genes:
        if gene in available and gene not in seen:
            seen.add(gene)
            out.append(gene)
    return out


def _rank_columns(mat: np.ndarray) -> np.ndarray:
    """Rank each column independently, averaging ties. NaN columns stay NaN."""
    ranked = np.empty_like(mat, dtype=float)
    for j in range(mat.shape[1]):
        col = mat[:, j]
        finite = np.isfinite(col)
        if not finite.all():
            # A gene with any NaN in this slice cannot be ranked meaningfully; it is
            # marked NaN so every pair involving it drops out of the accumulation.
            ranked[:, j] = np.nan
            continue
        ranked[:, j] = rankdata(col)
    return ranked


def _corr_from_columns(mat: np.ndarray) -> np.ndarray:
    """
    Column-wise Pearson correlation of an already rank-transformed matrix.

    np.corrcoef is not used directly because a constant column makes it emit a
    warning and fill an entire row with NaN; here constant columns are detected up
    front and only their own row and column become NaN.
    """
    n_genes = mat.shape[1]
    centered = mat - mat.mean(axis=0, keepdims=True)
    sd = centered.std(axis=0)
    valid = np.isfinite(sd) & (sd > 0)

    out = np.full((n_genes, n_genes), np.nan, dtype=float)
    if valid.sum() < 2:
        np.fill_diagonal(out, 1.0)
        return out

    sub = centered[:, valid] / sd[valid]
    cov = (sub.T @ sub) / mat.shape[0]
    idx = np.where(valid)[0]
    out[np.ix_(idx, idx)] = np.clip(cov, -1.0, 1.0)
    np.fill_diagonal(out, 1.0)
    return out


# ── Gene x gene correlation ───────────────────────────────────────────────────


def gene_gene_correlation(
    exp_df: pd.DataFrame, genes: list[str], method: str = "spearman"
) -> tuple[np.ndarray, list[str]]:
    """
    Gene x gene correlation over all samples of one expression matrix.

    Parameters
    ----------
    exp_df : pd.DataFrame
        Expression matrix, samples x genes.
    genes : list of str
        Panel genes; those absent from the matrix are dropped.
    method : {"spearman", "pearson"}
        Spearman ranks each gene first, matching metric group L.

    Returns
    -------
    tuple of (np.ndarray, list of str)
        Square correlation matrix and the gene order it is indexed by.
    """
    resolved = _resolve_genes(exp_df, genes)
    if len(resolved) < 2:
        return np.full((len(resolved), len(resolved)), np.nan), resolved

    mat = exp_df[resolved].to_numpy(dtype=float)
    if method == "spearman":
        mat = _rank_columns(mat)
    elif method != "pearson":
        raise ValueError(f"Unknown correlation method: {method}")
    return _corr_from_columns(mat), resolved


def gene_gene_correlation_within_cohort(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    genes: list[str],
    min_cohort_n: int = MIN_COHORT_N,
    method: str = "spearman",
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Gene x gene correlation computed inside each cohort and averaged across cohorts.

    Correlations are averaged on the Fisher z scale, not the r scale. A pair that is
    undefined in one cohort — either gene constant there — contributes nothing to that
    pair's count, so a gene that is flat in a single cohort is not penalised globally.

    Parameters
    ----------
    exp_df : pd.DataFrame
        Expression matrix, samples x genes.
    ann_df : pd.DataFrame
        Annotation aligned to exp_df's row index.
    genes : list of str
        Panel genes; those absent from the matrix are dropped.
    min_cohort_n : int
        Cohorts with fewer samples than this are skipped entirely.
    method : {"spearman", "pearson"}

    Returns
    -------
    tuple of (np.ndarray, np.ndarray, list of str)
        Fisher-z averaged correlation matrix, the count of contributing cohorts per
        pair, and the gene order both are indexed by.
    """
    resolved = _resolve_genes(exp_df, genes)
    n_genes = len(resolved)
    if n_genes < 2:
        empty = np.full((n_genes, n_genes), np.nan)
        return empty, np.zeros((n_genes, n_genes), dtype=int), resolved

    mat_all = exp_df[resolved].to_numpy(dtype=float)
    cohorts = cohort_labels(ann_df)

    sum_z = np.zeros((n_genes, n_genes), dtype=float)
    counts = np.zeros((n_genes, n_genes), dtype=int)

    for level in np.unique(cohorts):
        mask = cohorts == level
        if mask.sum() < min_cohort_n:
            continue
        block = mat_all[mask]
        if method == "spearman":
            block = _rank_columns(block)
        r = _corr_from_columns(block)
        finite = np.isfinite(r)
        sum_z[finite] += fisher_z(r[finite])
        counts[finite] += 1

    with np.errstate(invalid="ignore", divide="ignore"):
        mean_r = np.where(
            counts > 0, inverse_fisher_z(sum_z / np.maximum(counts, 1)), np.nan
        )
    np.fill_diagonal(mean_r, 1.0)
    return mean_r, counts, resolved


# ── Per-gene expression QC ────────────────────────────────────────────────────


def _icc_one_way(values: np.ndarray, group_codes: np.ndarray, n_groups: int) -> float:
    """
    One-way random-effects ICC(1) of one gene across cohorts (Shrout & Fleiss 1979).

    High ICC means most of the gene's variance sits between cohorts rather than
    between samples of the same cohort — the signature of a batch-driven gene.
    """
    n_total = values.size
    if n_groups < 2 or n_total <= n_groups:
        return np.nan

    sums = np.bincount(group_codes, weights=values, minlength=n_groups)
    sizes = np.bincount(group_codes, minlength=n_groups).astype(float)
    means = sums / np.maximum(sizes, 1)
    grand = values.mean()

    ms_between = float((sizes * (means - grand) ** 2).sum()) / (n_groups - 1)
    ms_within = float(((values - means[group_codes]) ** 2).sum()) / (n_total - n_groups)

    # Average group size correction for unbalanced designs.
    n0 = (n_total - (sizes**2).sum() / n_total) / (n_groups - 1)
    denom = ms_between + (n0 - 1) * ms_within
    if denom <= 0:
        return np.nan
    return float((ms_between - ms_within) / denom)


def _genorm_m(
    exp_values: np.ndarray, cohorts: np.ndarray, min_cohort_n: int
) -> np.ndarray:
    """
    geNorm stability measure M per gene (Vandesompele et al. 2002), batch-aware.

    For a gene pair (j, k), V_jk is the SD of the log-ratio x_j - x_k; the data is
    already log2, so the ratio is a difference. V is computed inside each cohort and
    averaged over cohorts, which keeps a between-cohort shift from being mistaken for
    instability. M_j is the mean of V_jk over all other genes; lower M = more stable.

    Var(x_j - x_k) = Var(x_j) + Var(x_k) - 2 Cov(x_j, x_k), so the whole G x G matrix
    comes from one covariance matrix per cohort instead of G^2 explicit differences.
    """
    n_genes = exp_values.shape[1]
    if n_genes < 2:
        return np.full(n_genes, np.nan)

    sum_v = np.zeros((n_genes, n_genes), dtype=float)
    n_used = 0
    for level in np.unique(cohorts):
        mask = cohorts == level
        if mask.sum() < min_cohort_n:
            continue
        block = exp_values[mask]
        if not np.isfinite(block).all():
            continue
        cov = np.cov(block, rowvar=False)
        var = np.diag(cov)
        pair_var = var[:, None] + var[None, :] - 2.0 * cov
        sum_v += np.sqrt(np.maximum(pair_var, 0.0))
        n_used += 1

    if n_used == 0:
        return np.full(n_genes, np.nan)

    mean_v = sum_v / n_used
    np.fill_diagonal(mean_v, np.nan)
    return np.nanmean(mean_v, axis=1)


def gene_expression_qc(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    genes: list[str],
    low_threshold: float = LOW_EXPRESSION_THRESHOLD,
    min_cohort_n: int = MIN_COHORT_N,
) -> pd.DataFrame:
    """
    Per-gene expression quality statistics for one expression matrix.

    Intended to be read from the 01_raw rows: zero inflation and the low-expression
    fraction are properties of the unharmonized measurement, and most harmonizers
    shift and rescale the values so the thresholds stop meaning the same thing. The
    statistics are still computed for every attempt so the change itself can be shown.

    Parameters
    ----------
    exp_df : pd.DataFrame
        Expression matrix, samples x genes, on the log2(x + 1) scale.
    ann_df : pd.DataFrame
        Annotation aligned to exp_df's row index.
    genes : list of str
        Panel genes; those absent from the matrix are dropped.
    low_threshold : float
        Values strictly below this count towards frac_lt_1.
    min_cohort_n : int
        Cohorts smaller than this are excluded from the cohort-structure statistics.

    Returns
    -------
    pd.DataFrame
        One row per gene with columns: gene, n_samples, n_cohorts_used, zero_frac,
        frac_lt_1, detection_frac, mean, median, sd, mad, iqr, p05, p95, cv,
        var_total, var_between_cohort, var_within_cohort, icc_cohort, genorm_m.
    """
    resolved = _resolve_genes(exp_df, genes)
    if not resolved:
        return pd.DataFrame(columns=["gene"])

    values = exp_df[resolved].to_numpy(dtype=float)
    n_samples = values.shape[0]
    cohorts = cohort_labels(ann_df)

    finite = np.isfinite(values)
    n_finite = finite.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        zero_frac = np.nansum(values == 0, axis=0) / np.maximum(n_finite, 1)
        low_frac = np.nansum(values < low_threshold, axis=0) / np.maximum(n_finite, 1)
        detection = np.nansum(values > 0, axis=0) / np.maximum(n_finite, 1)

    mean = np.nanmean(values, axis=0)
    median = np.nanmedian(values, axis=0)
    sd = np.nanstd(values, axis=0, ddof=1)
    p05 = np.nanpercentile(values, 5, axis=0)
    p25 = np.nanpercentile(values, 25, axis=0)
    p75 = np.nanpercentile(values, 75, axis=0)
    p95 = np.nanpercentile(values, 95, axis=0)
    mad = np.nanmedian(np.abs(values - median), axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        cv = np.where(np.abs(mean) > 0, sd / mean, np.nan)

    # Cohort-structure statistics use only the cohorts large enough to estimate a
    # within-cohort variance, matching the min_cohort_n rule of metric group L.
    levels, counts = np.unique(cohorts, return_counts=True)
    big_levels = levels[counts >= min_cohort_n]
    keep = np.isin(cohorts, big_levels)
    n_cohorts_used = int(len(big_levels))

    var_between = np.full(len(resolved), np.nan)
    var_within = np.full(len(resolved), np.nan)
    icc = np.full(len(resolved), np.nan)
    genorm = np.full(len(resolved), np.nan)

    if n_cohorts_used >= 2 and keep.sum() > n_cohorts_used:
        sub = values[keep]
        codes = pd.Categorical(cohorts[keep], categories=list(big_levels)).codes
        sizes = np.bincount(codes, minlength=n_cohorts_used).astype(float)

        for j in range(sub.shape[1]):
            col = sub[:, j]
            if not np.isfinite(col).all():
                continue
            sums = np.bincount(codes, weights=col, minlength=n_cohorts_used)
            means = sums / np.maximum(sizes, 1)
            grand = col.mean()
            var_between[j] = float((sizes * (means - grand) ** 2).sum() / col.size)
            var_within[j] = float(((col - means[codes]) ** 2).sum() / col.size)
            icc[j] = _icc_one_way(col, codes, n_cohorts_used)

        genorm = _genorm_m(sub, cohorts[keep], min_cohort_n)

    return pd.DataFrame(
        {
            "gene": resolved,
            "n_samples": n_samples,
            "n_cohorts_used": n_cohorts_used,
            "zero_frac": zero_frac,
            "frac_lt_1": low_frac,
            "detection_frac": detection,
            "mean": mean,
            "median": median,
            "sd": sd,
            "mad": mad,
            "iqr": p75 - p25,
            "p05": p05,
            "p95": p95,
            "cv": cv,
            "var_total": np.nanvar(values, axis=0),
            "var_between_cohort": var_between,
            "var_within_cohort": var_within,
            "icc_cohort": icc,
            "genorm_m": genorm,
        }
    )


QC_COLUMNS: tuple[str, ...] = (
    "gene",
    "n_samples",
    "n_cohorts_used",
    "zero_frac",
    "frac_lt_1",
    "detection_frac",
    "mean",
    "median",
    "sd",
    "mad",
    "iqr",
    "p05",
    "p95",
    "cv",
    "var_total",
    "var_between_cohort",
    "var_within_cohort",
    "icc_cohort",
    "genorm_m",
)
