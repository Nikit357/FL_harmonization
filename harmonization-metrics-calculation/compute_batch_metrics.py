"""
compute_batch_metrics.py — Batch effect metric library for harmonized expression datasets.

All metric computation functions, shared embedding helpers, and JSON serialization.
Imported by run_metrics_job.py; also used directly in test_mock_metrics.py.

Groups A-K measure batch removal and biology preservation and feed the Figure 3
clustermap. Groups L, M and N are the blind final check and are excluded from the
clustermap and the composite score by a prefix filter in figures_helpers.py:

    L (mk_*) marker gene correlation preservation — needs a raw reference matrix
    M (xb_*) cross-batch rank agreement          — single matrix
    N (pv_*) predictive validation               — single matrix

Only group L takes a reference; 01_raw is itself an attempt in the benchmark, so the
unharmonized baseline for M and N is obtained downstream by joining on (strat, imp)
rather than recomputed in every job.
"""

from __future__ import annotations

import itertools
import json
import math
import os
import subprocess
import tempfile
import threading
import time
import traceback
import warnings
from typing import Callable, Optional

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage as scipy_linkage
from scipy.sparse.csgraph import connected_components
from scipy.stats import anderson_ksamp, chi2, ks_2samp, kurtosis, rankdata, skew
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    balanced_accuracy_score,
    f1_score,
    matthews_corrcoef,
    pairwise_distances,
    roc_auc_score,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.neighbors import NearestNeighbors, kneighbors_graph
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.multitest import multipletests
import umap as umap_lib

from marker_panels import housekeeping_genes, panel_genes, resolve_panel

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", "All-NaN slice encountered", category=RuntimeWarning)

# ── Constants ──────────────────────────────────────────────────────────────────

# The bucket is supplied by the environment rather than hard-coded: the published
# pipeline has no default home, and a silently-wrong bucket would fail deep inside a
# worker instead of at start-up. Any placeholder works for offline use (metrics,
# figures, tests) because nothing is fetched until a job actually runs.
S3_BUCKET = os.environ.get("FL_S3_BUCKET", "")
S3_PREFIX = os.environ.get("FL_S3_PREFIX", "FL_batch_correction")
if not S3_BUCKET:
    raise RuntimeError(
        "Set FL_S3_BUCKET to the S3 bucket holding the prepared matrices "
        "(any placeholder value works for offline use)."
    )

BATCH_COLS: list[str] = ["RNA_BATCH", "PLATFORM_RNA", "RNASEQ_SOURCE", "COHORT_LABEL"]
BIO_COLS: list[str] = [
    "Major_group",
    "PLATFORM_RNA",
    "Diagnosis_cell_type_unified",
    "TUMOR_NORMAL",
]
ALL_COLS: list[str] = [
    "RNA_BATCH",
    "Major_group",
    "PLATFORM_RNA",
    "RNASEQ_SOURCE",
    "TUMOR_NORMAL",
    "COHORT_LABEL",
    "Diagnosis_cell_type_unified",
]

# ── Groups L / M / N — blind final check ──────────────────────────────────────

RANDOM_SEED: int = 260819
N_PERM: int = 20
MIN_COHORT_N: int = 20
MIN_TEST_N: int = 20
N_PCS: int = 10
XB_MAX_SAMPLES: int = 8000
PRED_CLASS_COL: str = "Major_group"
PRED_BIO_COL: str = "Diagnosis_cell_type_unified"

# ── JSON serialization ─────────────────────────────────────────────────────────


class _SafeEncoder(json.JSONEncoder):
    def default(self, obj: object) -> object:
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            v = float(obj)
            return None if (math.isnan(v) or math.isinf(v)) else v
        if isinstance(obj, float):
            return None if (math.isnan(obj) or math.isinf(obj)) else obj
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)


def dict_to_json_safe(d: dict) -> str:
    return json.dumps(d, cls=_SafeEncoder)


def _nan(x: float) -> float:
    """Return x; helper for readability."""
    return float(x)


# ── Shared helpers ─────────────────────────────────────────────────────────────


def _get_labels(ann_df: pd.DataFrame, col: str) -> Optional[pd.Series]:
    """
    Return non-NaN string labels for col, with the same index as ann_df.
    Returns None if col is absent or has fewer than 2 unique values.
    """
    if col not in ann_df.columns:
        return None
    mask = ann_df[col].notna()
    labels = ann_df.loc[mask, col].astype(str)
    if labels.nunique() < 2:
        return None
    return labels


def _row_mask(ann_df: pd.DataFrame, col: str) -> Optional[np.ndarray]:
    """Boolean numpy mask of non-NaN rows for col, or None if col unusable."""
    if col not in ann_df.columns:
        return None
    mask = ann_df[col].notna().values
    labels = ann_df.loc[ann_df[col].notna(), col].astype(str)
    if labels.nunique() < 2:
        return None
    return mask


def _ts() -> str:
    return time.strftime("%H:%M:%S")


# ── Embedding functions ────────────────────────────────────────────────────────


def compute_pca(
    exp_df: pd.DataFrame, n_components: int = 50
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute PCA on expression data.

    Parameters
    ----------
    exp_df : pd.DataFrame
        Expression matrix (samples × genes).
    n_components : int
        Number of principal components.

    Returns
    -------
    tuple of (pca_coords, eigenvalues)
        pca_coords: ndarray of shape (n_samples, n_components)
        eigenvalues: ndarray of explained variances (not ratios)
    """
    X = exp_df.values.astype(float)
    # Drop gene columns that are entirely NaN (produced by some failed normalizations)
    col_mask = ~np.all(np.isnan(X), axis=0)
    X = np.nan_to_num(X[:, col_mask], nan=0.0)
    if X.shape[1] == 0:
        raise ValueError(
            f"Expression matrix has 0 usable gene columns after dropping all-NaN genes "
            f"(original shape: {exp_df.shape})."
        )
    n_comp = min(n_components, X.shape[0] - 1, X.shape[1])
    if n_comp < 1:
        raise ValueError(f"Cannot compute PCA: n_comp={n_comp} (shape {X.shape})")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    pca = PCA(n_components=n_comp, random_state=42)
    coords = pca.fit_transform(X_scaled)
    return coords, pca.explained_variance_


def compute_umap(pca_coords: np.ndarray) -> np.ndarray:
    """
    Compute 2D UMAP on PCA coordinates.

    Parameters
    ----------
    pca_coords : np.ndarray
        PCA coordinate matrix (n_samples, n_pcs).

    Returns
    -------
    np.ndarray of shape (n_samples, 2)
    """
    reducer = umap_lib.UMAP(
        n_neighbors=30,
        min_dist=0.3,
        n_components=2,
        metric="euclidean",
        random_state=42,
        verbose=False,
    )
    return reducer.fit_transform(pca_coords)


def compute_tsne(pca_coords: np.ndarray) -> np.ndarray:
    """
    Compute 2D tSNE on PCA coordinates (full dataset, no subsampling).

    Parameters
    ----------
    pca_coords : np.ndarray
        PCA coordinate matrix (n_samples, n_pcs).

    Returns
    -------
    np.ndarray of shape (n_samples, 2)
    """
    from sklearn.manifold import TSNE

    tsne = TSNE(
        n_components=2,
        perplexity=min(30, pca_coords.shape[0] // 4),
        random_state=42,
        method="barnes_hut",
        n_jobs=-1,
    )
    return tsne.fit_transform(pca_coords)


# ── Group E — Data Quality ─────────────────────────────────────────────────────


def compute_group_e(exp_df: pd.DataFrame, ann_df: pd.DataFrame) -> dict:
    """
    Compute Group E metrics: data quality and descriptive statistics.

    Parameters
    ----------
    exp_df : pd.DataFrame
        Expression matrix (samples × genes).
    ann_df : pd.DataFrame
        Annotation DataFrame aligned to exp_df rows.

    Returns
    -------
    dict of metric name → value
    """
    result: dict = {}
    n_samples, n_genes = exp_df.shape

    # E1
    result["n_samples"] = int(n_samples)
    result["n_genes"] = int(n_genes)

    # E2
    if "RNA_BATCH" in ann_df.columns:
        batch_counts = ann_df["RNA_BATCH"].value_counts()
        result["n_batches"] = int(ann_df["RNA_BATCH"].nunique())
        result["n_samples_per_batch_min"] = float(batch_counts.min())
        result["n_samples_per_batch_max"] = float(batch_counts.max())
        result["n_samples_per_batch_median"] = float(batch_counts.median())
        result["n_samples_per_batch_sd"] = float(
            batch_counts.std(ddof=1) if len(batch_counts) > 1 else 0.0
        )
    else:
        result.update(
            {
                k: np.nan
                for k in [
                    "n_batches",
                    "n_samples_per_batch_min",
                    "n_samples_per_batch_max",
                    "n_samples_per_batch_median",
                    "n_samples_per_batch_sd",
                ]
            }
        )

    result["n_cohorts"] = (
        int(ann_df["COHORT_LABEL"].nunique())
        if "COHORT_LABEL" in ann_df.columns
        else np.nan
    )
    result["n_diagnosis_groups"] = (
        int(ann_df["Diagnosis_cell_type_unified"].nunique())
        if "Diagnosis_cell_type_unified" in ann_df.columns
        else np.nan
    )

    # E3 — zero and below-1 fractions
    vals = exp_df.values.astype(float)
    result["zero_fraction_global"] = float(np.mean(vals == 0))
    result["fraction_genes_below_1"] = float(np.mean(vals < 1))

    if "RNA_BATCH" in ann_df.columns:
        batch_zero_fracs = []
        batch_below1_fracs = []
        for batch in ann_df["RNA_BATCH"].unique():
            bmask = (ann_df["RNA_BATCH"] == batch).values
            bvals = vals[bmask]
            batch_zero_fracs.append(float(np.mean(bvals == 0)))
            batch_below1_fracs.append(float(np.mean(bvals < 1)))
        result["zero_fraction_by_batch_max"] = float(max(batch_zero_fracs))
        result["zero_fraction_by_batch_min"] = float(min(batch_zero_fracs))
        result["below_1_fraction_by_batch_max"] = float(max(batch_below1_fracs))
        result["below_1_fraction_by_batch_min"] = float(min(batch_below1_fracs))
    else:
        result.update(
            {
                k: np.nan
                for k in [
                    "zero_fraction_by_batch_max",
                    "zero_fraction_by_batch_min",
                    "below_1_fraction_by_batch_max",
                    "below_1_fraction_by_batch_min",
                ]
            }
        )

    # E4 — expression statistics
    flat = vals.flatten()
    result["exp_min"] = float(np.nanmin(flat))
    result["exp_max"] = float(np.nanmax(flat))
    result["exp_median"] = float(np.nanmedian(flat))
    result["exp_std"] = float(np.nanstd(flat))
    for pct, name in [
        (1, "p01"),
        (5, "p05"),
        (25, "p25"),
        (75, "p75"),
        (95, "p95"),
        (99, "p99"),
    ]:
        result[f"exp_{name}"] = float(np.nanpercentile(flat, pct))

    # per_batch_median_cv
    if "RNA_BATCH" in ann_df.columns:
        batch_medians = []
        for batch in ann_df["RNA_BATCH"].unique():
            bmask = (ann_df["RNA_BATCH"] == batch).values
            batch_medians.append(float(np.nanmedian(vals[bmask])))
        # Filter out NaN medians that arise when an entire batch is all-NaN
        finite_medians = [v for v in batch_medians if not math.isnan(v)]
        if len(finite_medians) > 1:
            m = np.mean(finite_medians)
            result["per_batch_median_cv"] = (
                float(np.std(finite_medians, ddof=1) / abs(m))
                if abs(m) > 1e-9
                else np.nan
            )
        else:
            result["per_batch_median_cv"] = np.nan
    else:
        result["per_batch_median_cv"] = np.nan

    # E4 — bimodality per cohort
    if "COHORT_LABEL" in ann_df.columns:
        n_bimodal = 0
        n_zero_inf_bimodal = 0
        cohorts = ann_df["COHORT_LABEL"].unique()
        for cohort in cohorts:
            cmask = (ann_df["COHORT_LABEL"] == cohort).values
            marginal = vals[cmask].flatten()
            marginal = marginal[np.isfinite(marginal)]
            n_c = len(marginal)
            if n_c < 4:
                continue
            try:
                s = float(skew(marginal))
                k_exc = float(kurtosis(marginal, fisher=True))
                denom = k_exc + 3.0 * (n_c - 1) ** 2 / ((n_c - 2) * (n_c - 3))
                bc = (s**2 + 1) / denom if abs(denom) > 1e-9 else np.nan
                if not np.isnan(bc) and bc > 0.555:
                    n_bimodal += 1
                    try:
                        gmm = GaussianMixture(n_components=2, random_state=42)
                        gmm.fit(marginal.reshape(-1, 1))
                        lower_mean = float(min(gmm.means_.flatten()))
                        if lower_mean < 1.0:
                            n_zero_inf_bimodal += 1
                    except Exception:
                        pass
            except Exception:
                pass
        n_cohorts_total = len(cohorts)
        result["n_cohorts_bimodal"] = int(n_bimodal)
        result["fraction_cohorts_bimodal"] = (
            float(n_bimodal / n_cohorts_total) if n_cohorts_total > 0 else np.nan
        )
        result["n_cohorts_zero_inflated_bimodal"] = int(n_zero_inf_bimodal)
        result["fraction_cohorts_zero_inflated_bimodal"] = (
            float(n_zero_inf_bimodal / n_cohorts_total)
            if n_cohorts_total > 0
            else np.nan
        )
    else:
        result.update(
            {
                k: np.nan
                for k in [
                    "n_cohorts_bimodal",
                    "fraction_cohorts_bimodal",
                    "n_cohorts_zero_inflated_bimodal",
                    "fraction_cohorts_zero_inflated_bimodal",
                ]
            }
        )

    return result


# ── Group A — PCA-based Variance Decomposition ────────────────────────────────


def _r2_anova_pc(pc_values: np.ndarray, label_arr: np.ndarray) -> float:
    """One-way ANOVA R² for a single PC."""
    unique = np.unique(label_arr)
    if len(unique) < 2:
        return np.nan
    grand_mean = pc_values.mean()
    ss_total = float(((pc_values - grand_mean) ** 2).sum())
    if ss_total < 1e-12:
        return 0.0
    ss_between = sum(
        (label_arr == g).sum() * (pc_values[label_arr == g].mean() - grand_mean) ** 2
        for g in unique
    )
    return float(ss_between / ss_total)


def _dsc_score(coords_2d: np.ndarray, label_arr: np.ndarray) -> float:
    """Dispersion Separability Criterion in 2D space."""
    unique = np.unique(label_arr)
    if len(unique) < 2:
        return np.nan
    mu = coords_2d.mean(axis=0)
    sb = 0.0
    sw = 0.0
    for g in unique:
        mask = label_arr == g
        n_g = mask.sum()
        if n_g == 0:
            continue
        mu_g = coords_2d[mask].mean(axis=0)
        diff = mu_g - mu
        sb += float(n_g * np.dot(diff, diff))
        sw += float(np.sum((coords_2d[mask] - mu_g) ** 2))
    if sw < 1e-12:
        return np.nan
    return sb / sw


def compute_group_a(
    pca_coords: np.ndarray, eigenvalues: np.ndarray, ann_df: pd.DataFrame
) -> dict:
    """
    Compute Group A: PCA-based variance decomposition metrics.

    Parameters
    ----------
    pca_coords : np.ndarray
        PCA coordinate matrix (n_samples, n_pcs).
    eigenvalues : np.ndarray
        Explained variance for each PC (not normalized).
    ann_df : pd.DataFrame
        Annotation DataFrame.

    Returns
    -------
    dict of metric name → value
    """
    result: dict = {}
    n_pcs_a1 = min(10, pca_coords.shape[1])
    n_pcs_pcr = min(100, pca_coords.shape[1])

    # A1 — mean R² over first 10 PCs
    a1_cols = [
        "RNA_BATCH",
        "Major_group",
        "PLATFORM_RNA",
        "RNASEQ_SOURCE",
        "TUMOR_NORMAL",
        "COHORT_LABEL",
    ]
    for col in a1_cols:
        mask = _row_mask(ann_df, col)
        if mask is None:
            result[f"r2_{col}"] = np.nan
            continue
        labels = ann_df.loc[ann_df[col].notna(), col].astype(str).values
        r2s = [_r2_anova_pc(pca_coords[mask, i], labels) for i in range(n_pcs_a1)]
        result[f"r2_{col}"] = float(np.nanmean(r2s))

    # A2 — per-PC R² for 4 batch columns
    for col in BATCH_COLS:
        mask = _row_mask(ann_df, col)
        if mask is None:
            for i in range(1, n_pcs_a1 + 1):
                result[f"r2_pc{i}_{col}"] = np.nan
            continue
        labels = ann_df.loc[ann_df[col].notna(), col].astype(str).values
        for i in range(n_pcs_a1):
            result[f"r2_pc{i+1}_{col}"] = _r2_anova_pc(pca_coords[mask, i], labels)

    # A3 — PCR (variance-weighted R²)
    total_var = eigenvalues[:n_pcs_pcr].sum()
    for col in ALL_COLS:
        mask = _row_mask(ann_df, col)
        if mask is None or total_var < 1e-12:
            result[f"pcr_{col}"] = np.nan
            continue
        labels = ann_df.loc[ann_df[col].notna(), col].astype(str).values
        weighted_r2 = 0.0
        for i in range(n_pcs_pcr):
            r2 = _r2_anova_pc(pca_coords[mask, i], labels)
            if not np.isnan(r2):
                weighted_r2 += eigenvalues[i] * r2
        result[f"pcr_{col}"] = float(1.0 - weighted_r2 / total_var)

    # A4 — DSC with permutation p-value (in 2D PCA)
    coords_2d = pca_coords[:, :2]
    for col in BATCH_COLS:
        mask = _row_mask(ann_df, col)
        if mask is None:
            result[f"dsc_{col}"] = np.nan
            result[f"dsc_pvalue_{col}"] = np.nan
            continue
        labels = ann_df.loc[ann_df[col].notna(), col].astype(str).values
        sub_2d = coords_2d[mask]
        observed = _dsc_score(sub_2d, labels)
        if np.isnan(observed):
            result[f"dsc_{col}"] = np.nan
            result[f"dsc_pvalue_{col}"] = np.nan
            continue
        n_extreme = 0
        rng = np.random.default_rng(42)
        for _ in range(999):
            perm = rng.permutation(labels)
            d = _dsc_score(sub_2d, perm)
            if not np.isnan(d) and d >= observed:
                n_extreme += 1
        result[f"dsc_{col}"] = float(observed)
        result[f"dsc_pvalue_{col}"] = float((n_extreme + 1) / 1000)

    return result


# ── Group J — Per-PC Variance Explained ──────────────────────────────────────


def compute_group_j(pca_coords: np.ndarray, eigenvalues: np.ndarray) -> dict:
    result: dict = {}
    total_var_sum = float(eigenvalues.sum())
    if total_var_sum > 0:
        for i in range(min(10, len(eigenvalues))):
            result[f"pct_var_pc{i+1}"] = float(eigenvalues[i] / total_var_sum * 100)
        result["pct_var_cum_top10"] = float(
            eigenvalues[:10].sum() / total_var_sum * 100
        )
    else:
        for i in range(10):
            result[f"pct_var_pc{i+1}"] = np.nan
        result["pct_var_cum_top10"] = np.nan
    return result


# ── Group B — Neighbor-based Integration Metrics ─────────────────────────────


def _kbet_acceptance(pca_coords: np.ndarray, label_arr: np.ndarray) -> float:
    """kBET acceptance rate."""
    n = len(label_arr)
    if n < 10:
        return np.nan
    k = min(25, n // 4)
    if k < 2:
        return np.nan

    unique, counts = np.unique(label_arr, return_counts=True)
    if len(unique) < 2:
        return np.nan
    global_freq = {g: c / n for g, c in zip(unique, counts)}

    rng = np.random.default_rng(42)
    n_test = max(1, int(n * 0.1))
    test_idx = rng.choice(n, n_test, replace=False)

    nn = NearestNeighbors(n_neighbors=k + 1, metric="euclidean", n_jobs=-1)
    nn.fit(pca_coords)
    _, indices = nn.kneighbors(pca_coords[test_idx])

    df_chi2 = len(unique) - 1
    n_rejected = 0
    for nbrs in indices:
        nbr_labels = label_arr[nbrs[1:]]
        observed = np.array([(nbr_labels == g).sum() for g in unique], dtype=float)
        expected = np.array([global_freq[g] * k for g in unique], dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            stat = np.nansum(
                np.where(expected > 0, (observed - expected) ** 2 / expected, 0.0)
            )
        p = 1.0 - chi2.cdf(stat, df_chi2)
        if p <= 0.05:
            n_rejected += 1
    return 1.0 - n_rejected / n_test


def _lisi_values(
    pca_coords: np.ndarray, label_arr: np.ndarray, k: int = 30
) -> np.ndarray:
    """Per-sample LISI values."""
    n = len(label_arr)
    k_eff = min(k, n - 1)
    nn = NearestNeighbors(n_neighbors=k_eff + 1, n_jobs=-1)
    nn.fit(pca_coords)
    _, indices = nn.kneighbors(pca_coords)
    lisi = np.empty(n, dtype=float)
    for i in range(n):
        nbr = label_arr[indices[i, 1:]]
        _, cnts = np.unique(nbr, return_counts=True)
        p = cnts / cnts.sum()
        lisi[i] = 1.0 / float(np.dot(p, p))
    return lisi


def _centroid_dispersion(coords: np.ndarray, label_arr: np.ndarray) -> float:
    """Ratio of centroid std to overall std (averaged over dimensions)."""
    unique = np.unique(label_arr)
    if len(unique) < 2:
        return np.nan
    centroids = np.array([coords[label_arr == g].mean(axis=0) for g in unique])
    global_std = coords.std(axis=0)
    centroid_std = centroids.std(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(global_std > 1e-9, centroid_std / global_std, np.nan)
    return float(np.nanmean(ratio))


def _local_entropy(
    coords: np.ndarray, label_arr: np.ndarray, k: int = 30
) -> tuple[float, float]:
    """Mean and normalized Shannon entropy of batch labels in k-NN."""
    n = len(label_arr)
    k_eff = min(k, n - 1)
    unique = np.unique(label_arr)
    n_batches = len(unique)
    if n_batches < 2:
        return np.nan, np.nan
    nn = NearestNeighbors(n_neighbors=k_eff + 1, n_jobs=-1)
    nn.fit(coords)
    _, indices = nn.kneighbors(coords)
    entropies = np.empty(n, dtype=float)
    for i in range(n):
        nbr = label_arr[indices[i, 1:]]
        _, cnts = np.unique(nbr, return_counts=True)
        p = cnts / cnts.sum()
        entropies[i] = -float(np.sum(p * np.log(p + 1e-15)))
    mean_h = float(np.mean(entropies))
    max_h = math.log(n_batches)
    norm_h = mean_h / max_h if max_h > 1e-9 else np.nan
    return mean_h, norm_h


def compute_group_b(pca_coords: np.ndarray, ann_df: pd.DataFrame) -> dict:
    """
    Compute Group B: neighbor-based integration metrics.

    Parameters
    ----------
    pca_coords : np.ndarray
        PCA coordinates (n_samples, n_pcs).
    ann_df : pd.DataFrame
        Annotation DataFrame.

    Returns
    -------
    dict of metric name → value
    """
    result: dict = {}

    # B1 — kBET
    for col in BATCH_COLS:
        mask = _row_mask(ann_df, col)
        if mask is None:
            result[f"kbet_acceptance_rate_{col}"] = np.nan
            continue
        labels = ann_df.loc[ann_df[col].notna(), col].astype(str).values
        result[f"kbet_acceptance_rate_{col}"] = _kbet_acceptance(
            pca_coords[mask], labels
        )

    # B2 — iLISI
    for col in BATCH_COLS:
        mask = _row_mask(ann_df, col)
        if mask is None:
            result[f"ilisi_mean_{col}"] = np.nan
            result[f"ilisi_norm_{col}"] = np.nan
            continue
        labels = ann_df.loc[ann_df[col].notna(), col].astype(str).values
        lisi = _lisi_values(pca_coords[mask], labels)
        n_batches = len(np.unique(labels))
        mean_lisi = float(np.mean(lisi))
        result[f"ilisi_mean_{col}"] = mean_lisi
        result[f"ilisi_norm_{col}"] = (
            float((mean_lisi - 1.0) / (n_batches - 1)) if n_batches > 1 else np.nan
        )

    # B3 — cLISI (biology)
    for col in BIO_COLS:
        mask = _row_mask(ann_df, col)
        if mask is None:
            result[f"clisi_mean_{col}"] = np.nan
            continue
        labels = ann_df.loc[ann_df[col].notna(), col].astype(str).values
        lisi = _lisi_values(pca_coords[mask], labels)
        result[f"clisi_mean_{col}"] = float(np.mean(lisi))

    # B4 — ASW_batch
    for col in BATCH_COLS:
        mask = _row_mask(ann_df, col)
        if mask is None:
            result[f"asw_batch_{col}"] = np.nan
            result[f"asw_batch_norm_{col}"] = np.nan
            continue
        labels = ann_df.loc[ann_df[col].notna(), col].astype(str).values
        sub = pca_coords[mask]
        n = len(labels)
        if n > 2000:
            rng = np.random.default_rng(42)
            idx = rng.choice(n, 2000, replace=False)
            sub = sub[idx]
            labels = labels[idx]
        try:
            asw = float(silhouette_score(sub, labels))
        except Exception:
            asw = np.nan
        result[f"asw_batch_{col}"] = asw
        result[f"asw_batch_norm_{col}"] = (
            float(1.0 - abs(asw)) if not np.isnan(asw) else np.nan
        )

    # B5 — ASW_bio
    for col in BIO_COLS:
        mask = _row_mask(ann_df, col)
        if mask is None:
            result[f"asw_bio_{col}"] = np.nan
            result[f"asw_bio_norm_{col}"] = np.nan
            continue
        labels = ann_df.loc[ann_df[col].notna(), col].astype(str).values
        sub = pca_coords[mask]
        n = len(labels)
        if n > 2000:
            rng = np.random.default_rng(42)
            idx = rng.choice(n, 2000, replace=False)
            sub = sub[idx]
            labels = labels[idx]
        try:
            asw = float(silhouette_score(sub, labels))
        except Exception:
            asw = np.nan
        result[f"asw_bio_{col}"] = asw
        result[f"asw_bio_norm_{col}"] = (
            float((asw + 1.0) / 2.0) if not np.isnan(asw) else np.nan
        )

    # B6 — CMS
    for col in BATCH_COLS:
        mask = _row_mask(ann_df, col)
        if mask is None:
            result[f"cms_mean_{col}"] = np.nan
            result[f"cms_fraction_mixed_{col}"] = np.nan
            continue
        labels = ann_df.loc[ann_df[col].notna(), col].astype(str).values
        sub = pca_coords[mask]
        n = len(labels)
        k_cms = min(30, n // 4)
        if k_cms < 2:
            result[f"cms_mean_{col}"] = np.nan
            result[f"cms_fraction_mixed_{col}"] = np.nan
            continue
        nn = NearestNeighbors(n_neighbors=k_cms + 1, n_jobs=-1)
        nn.fit(sub)
        distances, indices = nn.kneighbors(sub)
        unique_batches = np.unique(labels)
        cms_vals: list[float] = []
        for i in range(n):
            nbr_labels = labels[indices[i, 1:]]
            nbr_dists = distances[i, 1:]
            groups = [nbr_dists[nbr_labels == b] for b in unique_batches]
            groups = [g for g in groups if len(g) > 0]
            if len(groups) < 2:
                continue
            try:
                ad_result = anderson_ksamp(groups)
                try:
                    p = float(ad_result.pvalue)
                except AttributeError:
                    p = float(ad_result.significance_level) / 100.0
                cms_vals.append(p)
            except Exception:
                pass
        if cms_vals:
            result[f"cms_mean_{col}"] = float(np.mean(cms_vals))
            result[f"cms_fraction_mixed_{col}"] = float(
                np.mean([v > 0.05 for v in cms_vals])
            )
        else:
            result[f"cms_mean_{col}"] = np.nan
            result[f"cms_fraction_mixed_{col}"] = np.nan

    return result


# ── Group C — UMAP/tSNE Embedding Metrics ─────────────────────────────────────


def compute_group_c(
    umap_coords: np.ndarray,
    tsne_coords: np.ndarray,
    ann_df: pd.DataFrame,
) -> dict:
    """
    Compute Group C: centroid dispersion and local entropy in UMAP and tSNE.

    Parameters
    ----------
    umap_coords : np.ndarray
        2D UMAP coordinates.
    tsne_coords : np.ndarray
        2D tSNE coordinates.
    ann_df : pd.DataFrame
        Annotation DataFrame.

    Returns
    -------
    dict of metric name → value
    """
    result: dict = {}
    for col in BATCH_COLS:
        mask = _row_mask(ann_df, col)
        if mask is None:
            result[f"umap_centroid_disp_{col}"] = np.nan
            result[f"umap_entropy_mean_{col}"] = np.nan
            result[f"umap_entropy_norm_{col}"] = np.nan
            result[f"tsne_centroid_disp_{col}"] = np.nan
            result[f"tsne_entropy_mean_{col}"] = np.nan
            result[f"tsne_entropy_norm_{col}"] = np.nan
            continue
        labels = ann_df.loc[ann_df[col].notna(), col].astype(str).values

        # C1: UMAP centroid dispersion
        result[f"umap_centroid_disp_{col}"] = _centroid_dispersion(
            umap_coords[mask], labels
        )

        # C2: UMAP local entropy
        h_mean, h_norm = _local_entropy(umap_coords[mask], labels)
        result[f"umap_entropy_mean_{col}"] = h_mean
        result[f"umap_entropy_norm_{col}"] = h_norm

        # C3: tSNE centroid dispersion
        result[f"tsne_centroid_disp_{col}"] = _centroid_dispersion(
            tsne_coords[mask], labels
        )

        # C2 (tSNE): tSNE local entropy
        h_mean_t, h_norm_t = _local_entropy(tsne_coords[mask], labels)
        result[f"tsne_entropy_mean_{col}"] = h_mean_t
        result[f"tsne_entropy_norm_{col}"] = h_norm_t

    return result


# ── Group D — Distribution Comparison Metrics ─────────────────────────────────


def _ks_pairwise(
    exp_sub: pd.DataFrame,
    labels: np.ndarray,
) -> tuple[float, float]:
    """All-pairwise KS test: return (mean_D, frac_significant_BH)."""
    unique = np.unique(labels)
    if len(unique) < 2:
        return np.nan, np.nan
    D_vals: list[float] = []
    p_vals: list[float] = []
    for b1, b2 in itertools.combinations(unique, 2):
        m1 = labels == b1
        m2 = labels == b2
        for gene in exp_sub.columns:
            x = exp_sub.loc[m1, gene].dropna().values
            y = exp_sub.loc[m2, gene].dropna().values
            if len(x) < 3 or len(y) < 3:
                continue
            d_stat, p = ks_2samp(x, y)
            D_vals.append(float(d_stat))
            p_vals.append(float(p))
    if not D_vals:
        return np.nan, np.nan
    _, p_adj, _, _ = multipletests(p_vals, method="fdr_bh")
    return float(np.mean(D_vals)), float(np.mean(p_adj < 0.05))


def compute_group_d(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    n_genes_max: int = 1000,
    timeout_s: int = 3600,
) -> dict:
    """
    Compute Group D: distribution comparison metrics.

    D1 uses all-pairwise KS comparisons with a hard timeout.
    D2 computes within-RNA_BATCH cohort effects.
    D3 computes per-gene batch mean CV for three grouping columns.

    Parameters
    ----------
    exp_df : pd.DataFrame
        Expression matrix (samples × genes).
    ann_df : pd.DataFrame
        Annotation DataFrame.
    n_genes_max : int
        Number of genes to sample for KS tests.
    timeout_s : int
        Hard timeout in seconds for D1 computation.

    Returns
    -------
    dict of metric name → value
    """
    result: dict = {}

    # Sample genes once
    rng = np.random.default_rng(42)
    if exp_df.shape[1] > n_genes_max:
        gene_sample = rng.choice(exp_df.columns, n_genes_max, replace=False)
        exp_sub = exp_df[gene_sample]
    else:
        exp_sub = exp_df

    # D1 — all-pairwise KS with timeout
    d1_cols = ["RNA_BATCH", "PLATFORM_RNA", "COHORT_LABEL"]
    d1_result: dict = {}
    d1_exc: Optional[str] = None

    def _run_d1() -> None:
        nonlocal d1_exc
        try:
            for col in d1_cols:
                mask = _row_mask(ann_df, col)
                if mask is None:
                    d1_result[f"ks_mean_D_{col}"] = np.nan
                    d1_result[f"ks_frac_sig_{col}"] = np.nan
                    continue
                labels = ann_df.loc[ann_df[col].notna(), col].astype(str).values
                exp_aligned = exp_sub.loc[ann_df[col].notna()]
                mean_d, frac_sig = _ks_pairwise(exp_aligned, labels)
                d1_result[f"ks_mean_D_{col}"] = mean_d
                d1_result[f"ks_frac_sig_{col}"] = frac_sig
        except Exception:
            d1_exc = traceback.format_exc()

    t = threading.Thread(target=_run_d1, daemon=True)
    t.start()
    t.join(timeout=timeout_s)

    if t.is_alive():
        print(
            f"[{_ts()}][group_d] D1 timeout after {timeout_s}s — writing null values.",
            flush=True,
        )
        for col in d1_cols:
            result[f"ks_mean_D_{col}"] = np.nan
            result[f"ks_frac_sig_{col}"] = np.nan
        result["error_D1"] = "timeout"
    elif d1_exc:
        print(f"[{_ts()}][group_d] D1 error: {d1_exc}", flush=True)
        for col in d1_cols:
            result[f"ks_mean_D_{col}"] = np.nan
            result[f"ks_frac_sig_{col}"] = np.nan
        result["error_D1"] = d1_exc
    else:
        result.update(d1_result)

    # D2 — within-RNA_BATCH cohort effects
    if "RNA_BATCH" in ann_df.columns and "COHORT_LABEL" in ann_df.columns:
        D_within: list[float] = []
        p_within: list[float] = []
        for batch in ann_df["RNA_BATCH"].unique():
            bmask = ann_df["RNA_BATCH"] == batch
            cohorts_in_batch = ann_df.loc[bmask, "COHORT_LABEL"].unique()
            if len(cohorts_in_batch) < 2:
                continue
            pooled_mask = bmask.values
            pooled_exp = exp_sub.loc[pooled_mask]
            cohort_labels = ann_df.loc[pooled_mask, "COHORT_LABEL"].astype(str).values
            for cohort in cohorts_in_batch:
                cohort_mask = cohort_labels == str(cohort)
                rest_mask = ~cohort_mask
                if cohort_mask.sum() < 3 or rest_mask.sum() < 3:
                    continue
                for gene in exp_sub.columns:
                    x = pooled_exp.loc[cohort_mask, gene].dropna().values
                    y = pooled_exp.loc[rest_mask, gene].dropna().values
                    if len(x) < 3 or len(y) < 3:
                        continue
                    d_stat, p = ks_2samp(x, y)
                    D_within.append(float(d_stat))
                    p_within.append(float(p))
        if D_within:
            _, p_adj, _, _ = multipletests(p_within, method="fdr_bh")
            result["ks_cohort_within_batch_mean_D"] = float(np.mean(D_within))
            result["ks_cohort_within_batch_frac_sig"] = float(np.mean(p_adj < 0.05))
        else:
            result["ks_cohort_within_batch_mean_D"] = np.nan
            result["ks_cohort_within_batch_frac_sig"] = np.nan
    else:
        result["ks_cohort_within_batch_mean_D"] = np.nan
        result["ks_cohort_within_batch_frac_sig"] = np.nan

    # D3 — per-gene batch mean CV for three columns
    for col in ["RNA_BATCH", "COHORT_LABEL", "PLATFORM_RNA"]:
        if col not in ann_df.columns:
            result[f"per_gene_batch_mean_cv_{col}"] = np.nan
            continue
        groups = ann_df[col].unique()
        if len(groups) < 2:
            result[f"per_gene_batch_mean_cv_{col}"] = np.nan
            continue
        group_means = np.array(
            [exp_df.loc[ann_df[col] == g].mean(axis=0).values for g in groups]
        )  # shape: (n_groups, n_genes)
        cv_per_gene = np.std(group_means, axis=0, ddof=1) / np.abs(
            np.mean(group_means, axis=0)
        )
        finite = cv_per_gene[np.isfinite(cv_per_gene)]
        result[f"per_gene_batch_mean_cv_{col}"] = (
            float(np.mean(finite)) if len(finite) > 0 else np.nan
        )

    return result


# ── Group F — variancePartition ───────────────────────────────────────────────


def compute_group_f(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame, n_genes: int = 2000
) -> dict:
    """
    Compute Group F: variancePartition via R (file-based interface).

    Parameters
    ----------
    exp_df : pd.DataFrame
        Expression matrix (samples × genes).
    ann_df : pd.DataFrame
        Annotation DataFrame.
    n_genes : int
        Number of genes to randomly sample.

    Returns
    -------
    dict of metric name → value
    """
    result: dict = {}
    available_cols = [
        c for c in ALL_COLS if c in ann_df.columns and ann_df[c].nunique() >= 2
    ]
    if not available_cols:
        return {f"vp_median_{c}": np.nan for c in ALL_COLS} | {
            "vp_p25_RNA_BATCH": np.nan,
            "vp_p75_RNA_BATCH": np.nan,
            "vp_median_residual": np.nan,
        }

    rng = np.random.default_rng(42)
    if exp_df.shape[1] > n_genes:
        gene_sample = rng.choice(exp_df.columns, n_genes, replace=False)
        exp_sub = exp_df[gene_sample]
    else:
        exp_sub = exp_df

    with tempfile.TemporaryDirectory() as tmpdir:
        exp_path = os.path.join(tmpdir, "exp.tsv")
        ann_path = os.path.join(tmpdir, "ann.tsv")
        out_path = os.path.join(tmpdir, "vp.tsv")
        r_path = os.path.join(tmpdir, "run_vp.R")

        exp_sub.T.to_csv(exp_path, sep="\t")
        ann_df[available_cols].to_csv(ann_path, sep="\t")

        fixed_cols = [c for c in available_cols if c != "COHORT_LABEL"]
        random_part = "(1|COHORT_LABEL)" if "COHORT_LABEL" in available_cols else ""
        formula_parts = ([random_part] if random_part else []) + fixed_cols
        formula_str = "~ " + " + ".join(formula_parts) if formula_parts else "~ 1"

        r_script = f"""\
library(variancePartition)
library(BiocParallel)
suppressMessages(register(MulticoreParam(2)))

exp  <- as.matrix(read.table("{exp_path}", header=TRUE, row.names=1, sep="\\t",
                              check.names=FALSE))
info <- read.table("{ann_path}", header=TRUE, row.names=1, sep="\\t",
                   check.names=FALSE)

for (col in colnames(info)) {{
  info[[col]] <- as.factor(info[[col]])
}}

f   <- as.formula("{formula_str}")
vp  <- fitExtractVarPartModel(exp, f, info)
vp_df <- as.data.frame(vp)
write.table(vp_df, "{out_path}", sep="\\t", quote=FALSE)
"""
        with open(r_path, "w") as fh:
            fh.write(r_script)

        proc = subprocess.run(
            ["Rscript", "--no-save", "--no-restore", r_path],
            capture_output=True,
            text=True,
            timeout=3600,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"variancePartition R error:\n{proc.stderr[-2000:]}")

        vp_df = pd.read_csv(out_path, sep="\t", index_col=0)

    for col in ALL_COLS:
        r_col = col.replace("_", ".")  # R may replace _ with .
        if col in vp_df.columns:
            result[f"vp_median_{col}"] = float(vp_df[col].median())
        elif r_col in vp_df.columns:
            result[f"vp_median_{col}"] = float(vp_df[r_col].median())
        else:
            result[f"vp_median_{col}"] = np.nan

    rna_col = "RNA_BATCH" if "RNA_BATCH" in vp_df.columns else "RNA.BATCH"
    if rna_col in vp_df.columns:
        result["vp_p25_RNA_BATCH"] = float(vp_df[rna_col].quantile(0.25))
        result["vp_p75_RNA_BATCH"] = float(vp_df[rna_col].quantile(0.75))
    else:
        result["vp_p25_RNA_BATCH"] = np.nan
        result["vp_p75_RNA_BATCH"] = np.nan

    for candidate in ["Residuals", "residuals"]:
        if candidate in vp_df.columns:
            result["vp_median_residual"] = float(vp_df[candidate].median())
            break
    else:
        result["vp_median_residual"] = np.nan

    return result


# ── Group G — Graph Connectivity ──────────────────────────────────────────────


def compute_group_g(pca_coords: np.ndarray, ann_df: pd.DataFrame) -> dict:
    """
    Compute Group G: kNN graph connectivity per biology column.

    Parameters
    ----------
    pca_coords : np.ndarray
        PCA coordinates (n_samples, n_pcs).
    ann_df : pd.DataFrame
        Annotation DataFrame.

    Returns
    -------
    dict of metric name → value
    """
    result: dict = {}
    for col in BIO_COLS:
        mask = _row_mask(ann_df, col)
        if mask is None:
            result[f"graph_connectivity_{col}"] = np.nan
            continue
        labels = ann_df.loc[ann_df[col].notna(), col].astype(str).values
        sub = pca_coords[mask]
        gc_vals: list[float] = []
        for g in np.unique(labels):
            g_mask = labels == g
            n_g = g_mask.sum()
            if n_g < 2:
                gc_vals.append(1.0)
                continue
            coords_g = sub[g_mask]
            k_g = min(15, n_g - 1)
            graph = kneighbors_graph(
                coords_g, n_neighbors=k_g, mode="connectivity", include_self=False
            )
            n_comp, _ = connected_components(graph, directed=False)
            gc_vals.append(1.0 / n_comp)
        result[f"graph_connectivity_{col}"] = (
            float(np.mean(gc_vals)) if gc_vals else np.nan
        )
    return result


# ── Group H — Pairwise Euclidean Distances ────────────────────────────────────


def compute_group_h(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame, subsample: int = 2000
) -> dict:
    """
    Compute Group H: average intra/inter group Euclidean distances.

    Parameters
    ----------
    exp_df : pd.DataFrame
        Expression matrix (samples × genes) — distances in full gene space.
    ann_df : pd.DataFrame
        Annotation DataFrame.
    subsample : int
        Max samples to use (subsampled randomly if exceeded).

    Returns
    -------
    dict of metric name → value
    """
    result: dict = {}
    n = len(exp_df)
    if n > subsample:
        rng = np.random.default_rng(42)
        idx = rng.choice(n, subsample, replace=False)
        X = exp_df.values[idx].astype(float)
        ann_sub = ann_df.iloc[idx]
    else:
        X = exp_df.values.astype(float)
        ann_sub = ann_df

    X = np.nan_to_num(X, nan=0.0)
    D = pairwise_distances(X, metric="euclidean")
    n_sub = len(ann_sub)
    upper = np.triu(np.ones((n_sub, n_sub), dtype=bool), k=1)

    for col in ALL_COLS:
        if col not in ann_sub.columns:
            result[f"avg_intra_dist_{col}"] = np.nan
            result[f"avg_inter_dist_{col}"] = np.nan
            result[f"dist_ratio_{col}"] = np.nan
            continue
        lbl = np.asarray(ann_sub[col].astype(str))
        same = (lbl[:, None] == lbl[None, :]) & upper
        diff = (lbl[:, None] != lbl[None, :]) & upper
        avg_intra = float(D[same].mean()) if same.any() else np.nan
        avg_inter = float(D[diff].mean()) if diff.any() else np.nan
        ratio = (
            float(avg_intra / avg_inter)
            if (
                not np.isnan(avg_intra) and not np.isnan(avg_inter) and avg_inter > 1e-9
            )
            else np.nan
        )
        result[f"avg_intra_dist_{col}"] = avg_intra
        result[f"avg_inter_dist_{col}"] = avg_inter
        result[f"dist_ratio_{col}"] = ratio

    return result


# ── Group K — NA Retention / Failure Detection ────────────────────────────────


def compute_group_k(exp_df: pd.DataFrame, ann_df: pd.DataFrame) -> dict:
    result: dict = {}
    n_samples, n_genes = exp_df.shape
    gene_any_na = exp_df.isna().any(axis=0)
    gene_all_na = exp_df.isna().all(axis=0)
    samp_any_na = exp_df.isna().any(axis=1)
    samp_all_na = exp_df.isna().all(axis=1)

    n_genes_noNA = int((~gene_any_na).sum())
    n_samples_noNA = int((~samp_any_na).sum())
    n_genes_allNA = int(gene_all_na.sum())
    n_samples_allNA = int(samp_all_na.sum())
    n_na_cells = int(exp_df.isna().sum().sum())

    result["n_genes_noNA"] = n_genes_noNA
    result["pct_genes_noNA"] = (
        float(n_genes_noNA / n_genes * 100) if n_genes > 0 else np.nan
    )
    result["n_samples_noNA"] = n_samples_noNA
    result["pct_samples_noNA"] = (
        float(n_samples_noNA / n_samples * 100) if n_samples > 0 else np.nan
    )
    result["n_genes_allNA"] = n_genes_allNA
    result["n_samples_allNA"] = n_samples_allNA
    result["n_na_cells"] = n_na_cells
    result["pct_na_cells"] = (
        float(n_na_cells / (n_samples * n_genes) * 100)
        if (n_samples * n_genes) > 0
        else np.nan
    )
    return result


# ── Group I — WaterMelon Score ────────────────────────────────────────────────

WM_BATCH_COLS: list[str] = [
    "RNA_BATCH",
    "PLATFORM_RNA",
    "RNASEQ_SOURCE",
    "COHORT_LABEL",
]
WM_BIO_COLS: list[str] = ["Major_group", "Diagnosis_cell_type_unified", "TUMOR_NORMAL"]


def _entropy_from_counts(counts: np.ndarray) -> float:
    total = float(counts.sum())
    if total <= 0:
        return 0.0
    probs = counts[counts > 0] / total
    return float(-np.sum(probs * np.log2(probs)))


def _wm_trajectory_for_labels(
    Z: np.ndarray,
    label_idx: np.ndarray,
    n_classes: int,
    N: int,
) -> tuple[np.ndarray, float]:
    """IGn trajectory (bottom-up, length N-1) via incremental conditional entropy update."""
    global_counts = np.bincount(label_idx, minlength=n_classes).astype(float)
    H_Y = _entropy_from_counts(global_counts)
    if H_Y < 1e-12:
        return np.zeros(N - 1), 0.0

    cluster_counts: dict[int, np.ndarray] = {}
    cluster_size: dict[int, int] = {}
    for i in range(N):
        cc = np.zeros(n_classes)
        cc[label_idx[i]] = 1.0
        cluster_counts[i] = cc
        cluster_size[i] = 1

    H_cond = 0.0
    traj = np.empty(N - 1)
    for merge_idx in range(N - 1):
        id_a = int(Z[merge_idx, 0])
        id_b = int(Z[merge_idx, 1])
        new_id = N + merge_idx

        counts_a = cluster_counts.pop(id_a)
        counts_b = cluster_counts.pop(id_b)
        size_a = cluster_size.pop(id_a)
        size_b = cluster_size.pop(id_b)

        H_a = _entropy_from_counts(counts_a)
        H_b = _entropy_from_counts(counts_b)
        counts_new = counts_a + counts_b
        size_new = size_a + size_b
        H_new = _entropy_from_counts(counts_new)

        H_cond = (
            H_cond - (size_a / N) * H_a - (size_b / N) * H_b + (size_new / N) * H_new
        )
        traj[merge_idx] = (H_Y - H_cond) / H_Y

        cluster_counts[new_id] = counts_new
        cluster_size[new_id] = size_new

    return traj, H_Y


def _stratified_subsample(
    n_total: int,
    strat_labels: Optional[np.ndarray],
    max_n: int,
    rng: np.random.Generator,
) -> np.ndarray:
    indices = np.arange(n_total)
    if strat_labels is None or max_n >= n_total:
        return rng.choice(indices, max_n, replace=False)
    classes = np.unique(strat_labels)
    selected: list[np.ndarray] = []
    for cls in classes:
        cls_idx = indices[strat_labels == cls]
        n_take = max(1, round(max_n * len(cls_idx) / n_total))
        n_take = min(n_take, len(cls_idx))
        selected.append(rng.choice(cls_idx, n_take, replace=False))
    result_idx = np.concatenate(selected)
    if len(result_idx) > max_n:
        result_idx = rng.choice(result_idx, max_n, replace=False)
    elif len(result_idx) < max_n:
        remaining = np.setdiff1d(indices, result_idx)
        n_extra = min(max_n - len(result_idx), len(remaining))
        if n_extra > 0:
            result_idx = np.concatenate(
                [result_idx, rng.choice(remaining, n_extra, replace=False)]
            )
    return result_idx


def compute_group_i(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    pca_coords: np.ndarray,
    n_permutations: int = 200,
    max_samples: int = 2000,
) -> dict:
    result: dict = {}
    rng = np.random.default_rng(42)
    N = len(exp_df)
    subsampled = N > max_samples
    result["wm_subsampled"] = subsampled

    if subsampled:
        strat_arr: Optional[np.ndarray] = (
            ann_df["RNA_BATCH"].values.astype(str)
            if "RNA_BATCH" in ann_df.columns
            else None
        )
        sub_idx = _stratified_subsample(N, strat_arr, max_samples, rng)
        pca_sub = pca_coords[sub_idx, :]
        ann_sub = ann_df.iloc[sub_idx]
        N_eff = len(sub_idx)
    else:
        pca_sub = pca_coords
        ann_sub = ann_df
        N_eff = N

    n_pcs = min(50, pca_sub.shape[1])
    Z = scipy_linkage(pca_sub[:, :n_pcs], method="ward", metric="euclidean")

    wm_batch_vals: list[float] = []
    wm_bio_vals: list[float] = []

    for col in WM_BATCH_COLS + WM_BIO_COLS:
        labels = _get_labels(ann_sub, col)
        if labels is None:
            result[f"wm_{col}"] = np.nan
            continue

        label_arr = (
            labels.reindex(ann_sub.index).fillna("__unknown__").values.astype(str)
        )
        classes, label_idx_raw = np.unique(label_arr, return_inverse=True)
        label_idx = label_idx_raw.astype(np.int32)
        n_classes = int(len(classes))

        obs_traj, H_Y = _wm_trajectory_for_labels(Z, label_idx, n_classes, N_eff)
        if H_Y < 1e-12:
            result[f"wm_{col}"] = np.nan
            continue

        perm_trajs = np.empty((n_permutations, N_eff - 1))
        for m in range(n_permutations):
            perm_idx = rng.permutation(label_idx)
            perm_traj, _ = _wm_trajectory_for_labels(Z, perm_idx, n_classes, N_eff)
            perm_trajs[m] = perm_traj

        null_traj = np.percentile(perm_trajs, 95, axis=0)
        wm_area = float(np.mean(obs_traj - null_traj))
        result[f"wm_{col}"] = wm_area

        if col in WM_BATCH_COLS:
            wm_batch_vals.append(wm_area)
        else:
            wm_bio_vals.append(wm_area)

    valid_batch = [v for v in wm_batch_vals if not np.isnan(v)]
    valid_bio = [v for v in wm_bio_vals if not np.isnan(v)]

    result["wm_mean_batch"] = float(np.mean(valid_batch)) if valid_batch else np.nan
    result["wm_mean_bio"] = float(np.mean(valid_bio)) if valid_bio else np.nan

    if valid_batch and valid_bio:
        mean_batch = float(np.mean(valid_batch))
        mean_bio = float(np.mean(valid_bio))
        result["wm_ratio_bio_batch"] = float(mean_bio / (mean_batch + 0.01))
    else:
        result["wm_ratio_bio_batch"] = np.nan

    return result


# ── Groups L / M / N — shared helpers ─────────────────────────────────────────


def _predictor_labels(ann_df: pd.DataFrame, n_classes: int = 3) -> Optional[pd.Series]:
    """
    Build the classification target for Group N.

    Collapses the annotation to FL / DLBCL / Normal_B (n_classes=3) or FL / DLBCL
    (n_classes=2), dropping rare entities (Burkitt, high-grade B-cell, other) by
    leaving them NaN.

    When neither the FL nor the DLBCL label is present the function falls back to
    PRED_CLASS_COL verbatim, keeping the n_classes most frequent levels. Without the
    fallback the group would be untestable on synthetic data and unusable on any
    future cohort that labels its diagnoses differently.

    Parameters
    ----------
    ann_df : pd.DataFrame
        Annotation DataFrame.
    n_classes : int
        3 for FL / DLBCL / Normal_B, 2 for FL vs DLBCL.

    Returns
    -------
    pd.Series or None
        Labels indexed like ann_df, NaN where the sample is excluded. None if
        fewer than 2 usable classes remain.
    """
    if PRED_CLASS_COL not in ann_df.columns:
        return None

    major = ann_df[PRED_CLASS_COL].astype(str)
    labels = pd.Series(np.nan, index=ann_df.index, dtype=object)
    labels[major == "Follicular_Lymphoma"] = "FL"
    labels[major == "Diffuse_Large_B_Cell_Lymphoma"] = "DLBCL"

    if n_classes >= 3 and "TUMOR_NORMAL" in ann_df.columns:
        labels[ann_df["TUMOR_NORMAL"].astype(str) == "Normal"] = "Normal_B"

    if labels.notna().sum() == 0:
        top = major.value_counts().index[:n_classes]
        labels = major.where(major.isin(top))

    if labels.dropna().nunique() < 2:
        return None
    return labels


def _rank_along(X: np.ndarray, axis: int) -> np.ndarray:
    """Average ranks along axis, with NaNs ranked last (they are masked out later)."""
    return rankdata(X, axis=axis, nan_policy="omit")


def _unit_center(R: np.ndarray, axis: int) -> np.ndarray:
    """Centre and L2-normalise along axis so a dot product equals a correlation."""
    Rc = R - R.mean(axis=axis, keepdims=True)
    norm = np.sqrt((Rc**2).sum(axis=axis, keepdims=True))
    norm[norm == 0] = np.nan  # a constant vector has no defined correlation
    return Rc / norm


def _spearman_columnwise(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Per-column Spearman correlation between two same-shaped matrices.

    Ranks each column independently, then takes the column-wise dot product of the
    centred unit vectors — one vectorised pass instead of one scipy call per column.

    Parameters
    ----------
    A, B : np.ndarray
        Matrices of identical shape (n_samples, n_genes).

    Returns
    -------
    np.ndarray of shape (n_genes,), NaN where a column is constant.
    """
    Ra = _unit_center(_rank_along(A, axis=0), axis=0)
    Rb = _unit_center(_rank_along(B, axis=0), axis=0)
    return np.nansum(Ra * Rb, axis=0) * np.where(
        np.isnan(Ra).all(axis=0) | np.isnan(Rb).all(axis=0), np.nan, 1.0
    )


def _stratified_subsample_idx(
    ann_df: pd.DataFrame, max_samples: int, strat_col: str = "RNA_BATCH"
) -> np.ndarray:
    """Positional indices of a stratified subsample, or all rows if already small."""
    n = len(ann_df)
    if n <= max_samples:
        return np.arange(n)
    rng = np.random.default_rng(RANDOM_SEED)
    if strat_col not in ann_df.columns:
        return np.sort(rng.choice(n, max_samples, replace=False))
    keep: list[int] = []
    positions = np.arange(n)
    groups = ann_df[strat_col].astype(str).values
    frac = max_samples / n
    for level in np.unique(groups):
        idx = positions[groups == level]
        take = max(1, int(round(len(idx) * frac)))
        keep.extend(rng.choice(idx, min(take, len(idx)), replace=False).tolist())
    return np.sort(np.array(keep))


# ── Group L — Marker Gene Correlation Preservation ────────────────────────────


def compute_group_l(
    exp_df: pd.DataFrame,
    ref_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    panel: Optional[list[str]] = None,
    min_cohort_n: int = MIN_COHORT_N,
    collect_detail: bool = False,
) -> dict:
    """
    Compute Group L metrics: per-gene expression profile preservation.

    For every cohort and every panel gene, the Spearman correlation between the
    gene's expression across that cohort's samples before harmonization (ref_df)
    and after (exp_df). Reported per gene (averaged over cohorts), per cohort
    (averaged over genes), and as a grand mean, plus the marker-versus-housekeeping
    contrast.

    Any harmonizer applying a per-batch monotone transform of each gene leaves
    within-cohort ranks unchanged and therefore scores ~1.0 here by construction;
    see the plan for why Group M carries the discriminative conclusion.

    Parameters
    ----------
    exp_df : pd.DataFrame
        Harmonized expression matrix (samples x genes).
    ref_df : pd.DataFrame
        Unharmonized reference matrix, already aligned to exp_df's row index.
    ann_df : pd.DataFrame
        Annotation DataFrame aligned to exp_df rows.
    panel : list of str, optional
        Gene panel. Default: every gene in the marker annotation table.
    min_cohort_n : int
        Cohorts with fewer samples than this are skipped.
    collect_detail : bool
        If True, also return the full gene x cohort correlation matrix under
        "mk_gene_cohort_detail". The caller must strip that key before writing the
        metrics sidecar — at ~300 KB per job it would add over a gigabyte across the
        benchmark, which is why it is off by default.

    Returns
    -------
    dict of mk_* metric name -> value
    """
    result: dict = {}
    full_panel = panel if panel is not None else panel_genes(include_housekeeping=True)

    shared = exp_df.columns.intersection(ref_df.columns)
    genes, missing = resolve_panel(set(shared), full_panel)

    result["mk_n_panel_genes_used"] = len(genes)
    result["mk_n_genes_null"] = len(missing)
    result["mk_panel_coverage_frac"] = (
        float(len(genes) / len(full_panel)) if full_panel else np.nan
    )
    result["mk_is_self_reference"] = bool(exp_df is ref_df)

    if not genes:
        for key in (
            "mk_rho_mean_all_genes",
            "mk_rho_median_all_genes",
            "mk_rho_p10_all_genes",
            "mk_rho_min_all_genes",
            "mk_rho_frac_genes_above_0.9",
            "mk_rho_mean_markers",
            "mk_rho_mean_housekeeping",
            "mk_rho_marker_minus_hk",
            "mk_rho_mean_by_cohort_mean",
        ):
            result[key] = np.nan
        result["mk_rho_by_gene"] = {}
        result["mk_rho_n_cohorts_by_gene"] = {}
        result["mk_rho_by_cohort"] = {}
        result["mk_n_cohorts_used"] = 0
        result["mk_n_cohorts_skipped_small"] = 0
        return result

    A = exp_df[genes].values.astype(float)
    B = ref_df[genes].values.astype(float)

    cohort_col = "COHORT_LABEL" if "COHORT_LABEL" in ann_df.columns else "RNA_BATCH"
    cohorts = ann_df[cohort_col].astype(str).values

    # rho_sums / rho_counts accumulate per gene across cohorts so a gene absent from
    # one cohort (constant expression there) still contributes from the others.
    rho_sums = np.zeros(len(genes))
    rho_counts = np.zeros(len(genes))
    per_cohort: dict[str, float] = {}
    detail: dict[str, dict[str, float]] = {}
    n_skipped = 0

    for level in np.unique(cohorts):
        mask = cohorts == level
        if mask.sum() < min_cohort_n:
            n_skipped += 1
            continue
        rho = _spearman_columnwise(A[mask], B[mask])
        valid = ~np.isnan(rho)
        rho_sums[valid] += rho[valid]
        rho_counts[valid] += 1
        if valid.any():
            per_cohort[str(level)] = float(np.mean(rho[valid]))
        if collect_detail:
            detail[str(level)] = {
                g: (float(v) if not np.isnan(v) else None) for g, v in zip(genes, rho)
            }

    with np.errstate(invalid="ignore", divide="ignore"):
        rho_by_gene = np.where(rho_counts > 0, rho_sums / rho_counts, np.nan)

    result["mk_rho_by_gene"] = {
        g: (float(v) if not np.isnan(v) else None) for g, v in zip(genes, rho_by_gene)
    }
    result["mk_rho_n_cohorts_by_gene"] = {g: int(c) for g, c in zip(genes, rho_counts)}
    result["mk_rho_by_cohort"] = per_cohort
    result["mk_n_cohorts_used"] = len(per_cohort)
    result["mk_n_cohorts_skipped_small"] = n_skipped

    finite = rho_by_gene[~np.isnan(rho_by_gene)]
    if finite.size:
        result["mk_rho_mean_all_genes"] = float(np.mean(finite))
        result["mk_rho_median_all_genes"] = float(np.median(finite))
        result["mk_rho_p10_all_genes"] = float(np.percentile(finite, 10))
        result["mk_rho_min_all_genes"] = float(np.min(finite))
        result["mk_rho_frac_genes_above_0.9"] = float(np.mean(finite > 0.9))
    else:
        for key in (
            "mk_rho_mean_all_genes",
            "mk_rho_median_all_genes",
            "mk_rho_p10_all_genes",
            "mk_rho_min_all_genes",
            "mk_rho_frac_genes_above_0.9",
        ):
            result[key] = np.nan

    hk = set(housekeeping_genes())
    is_hk = np.array([g in hk for g in genes])
    marker_vals = rho_by_gene[~is_hk & ~np.isnan(rho_by_gene)]
    hk_vals = rho_by_gene[is_hk & ~np.isnan(rho_by_gene)]
    result["mk_rho_mean_markers"] = (
        float(np.mean(marker_vals)) if marker_vals.size else np.nan
    )
    result["mk_rho_mean_housekeeping"] = (
        float(np.mean(hk_vals)) if hk_vals.size else np.nan
    )
    result["mk_rho_marker_minus_hk"] = (
        float(np.mean(marker_vals) - np.mean(hk_vals))
        if marker_vals.size and hk_vals.size
        else np.nan
    )
    result["mk_rho_mean_by_cohort_mean"] = (
        float(np.mean(list(per_cohort.values()))) if per_cohort else np.nan
    )
    if collect_detail:
        result["mk_gene_cohort_detail"] = detail
    return result


# ── Group M — Cross-Batch Rank Agreement ──────────────────────────────────────


def compute_group_m(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    panel: Optional[list[str]] = None,
    max_samples: int = XB_MAX_SAMPLES,
) -> dict:
    """
    Compute Group M metrics: cross-batch rank agreement within one matrix.

    Ranks the panel genes within each sample, then measures the mean Spearman
    correlation between sample pairs drawn from different RNA_BATCH levels. Two
    populations of pairs are contrasted: same biology (same
    Diagnosis_cell_type_unified) and different biology. The margin between them is
    the biology-specific signal — a method that merely collapses every sample toward
    a common profile raises both, leaving the margin flat.

    Computed from this matrix alone. The unharmonized baseline is not recomputed
    here: 01_raw is itself an attempt in the benchmark, so the notebook obtains the
    baseline by joining on (strat, imp) instead of repeating the same quantity in
    every job.

    Parameters
    ----------
    exp_df : pd.DataFrame
        Expression matrix (samples x genes).
    ann_df : pd.DataFrame
        Annotation DataFrame aligned to exp_df rows.
    panel : list of str, optional
        Gene panel. Default: every gene in the marker annotation table.
    max_samples : int
        Above this, subsample stratified by RNA_BATCH to bound the pair count.

    Returns
    -------
    dict of xb_* metric name -> value
    """
    result: dict = {}
    full_panel = panel if panel is not None else panel_genes(include_housekeeping=True)
    genes, _ = resolve_panel(set(exp_df.columns), full_panel)

    batch_col, bio_col = "RNA_BATCH", PRED_BIO_COL
    if (
        len(genes) < 3
        or batch_col not in ann_df.columns
        or bio_col not in ann_df.columns
    ):
        for key in (
            "xb_rank_agree",
            "xb_rank_agree_median",
            "xb_rank_disagree_diffbio",
            "xb_rank_disagree_diffbio_median",
            "xb_rank_agree_ratio",
        ):
            result[key] = np.nan
        result["xb_rank_agree_by_diagnosis"] = {}
        result["xb_n_pairs_same_bio"] = 0
        result["xb_n_pairs_diff_bio"] = 0
        result["xb_n_samples_used"] = 0
        result["xb_subsampled"] = False
        return result

    keep = _stratified_subsample_idx(ann_df, max_samples, batch_col)
    result["xb_subsampled"] = bool(len(keep) < len(ann_df))
    result["xb_n_samples_used"] = int(len(keep))

    X = exp_df[genes].values.astype(float)[keep]
    # np.asarray(...) forces a plain ndarray instead of a pandas StringArray, which does
    # not support the [:, None] / [None, :] broadcasting used below (see compute_group_h
    # for the same pattern).
    batches = np.asarray(ann_df[batch_col].astype(str))[keep]
    bios = np.asarray(ann_df[bio_col].astype(str))[keep]

    # Rank genes within each sample, so a row dot product is that pair's Spearman.
    R = _unit_center(_rank_along(X, axis=1), axis=1)
    R = np.nan_to_num(R, nan=0.0)

    n = R.shape[0]
    sums = {"same": 0.0, "diff": 0.0}
    counts = {"same": 0, "diff": 0}
    vals = {"same": [], "diff": []}
    per_diag_sum: dict[str, float] = {}
    per_diag_cnt: dict[str, int] = {}

    # Block-wise accumulation: the full n x n rank-correlation matrix would be
    # ~412 MB at n=7,174, and every worker holds two expression matrices already.
    block = 512
    for start in range(0, n, block):
        stop = min(start + block, n)
        C = R[start:stop] @ R.T  # (block, n)
        rows = np.arange(start, stop)
        # Upper triangle only, so each pair is counted once.
        upper = rows[:, None] < np.arange(n)[None, :]
        diff_batch = batches[rows][:, None] != batches[None, :]
        same_bio = bios[rows][:, None] == bios[None, :]

        m_same = upper & diff_batch & same_bio
        m_diff = upper & diff_batch & ~same_bio
        for tag, m in (("same", m_same), ("diff", m_diff)):
            if m.any():
                v = C[m]
                sums[tag] += float(v.sum())
                counts[tag] += int(v.size)
                vals[tag].append(v)

        for diag in np.unique(bios[rows]):
            m_d = m_same & (bios[rows][:, None] == diag)
            if m_d.any():
                v = C[m_d]
                per_diag_sum[diag] = per_diag_sum.get(diag, 0.0) + float(v.sum())
                per_diag_cnt[diag] = per_diag_cnt.get(diag, 0) + int(v.size)

    def _mean(tag: str) -> float:
        return float(sums[tag] / counts[tag]) if counts[tag] else np.nan

    def _median(tag: str) -> float:
        return float(np.median(np.concatenate(vals[tag]))) if vals[tag] else np.nan

    result["xb_rank_agree"] = _mean("same")
    result["xb_rank_agree_median"] = _median("same")
    result["xb_rank_disagree_diffbio"] = _mean("diff")
    result["xb_rank_disagree_diffbio_median"] = _median("diff")
    result["xb_rank_agree_ratio"] = (
        result["xb_rank_agree"] - result["xb_rank_disagree_diffbio"]
        if counts["same"] and counts["diff"]
        else np.nan
    )
    result["xb_rank_agree_by_diagnosis"] = {
        d: float(per_diag_sum[d] / per_diag_cnt[d]) for d in per_diag_sum
    }
    result["xb_n_pairs_same_bio"] = counts["same"]
    result["xb_n_pairs_diff_bio"] = counts["diff"]
    result["xb_n_panel_genes_used"] = len(genes)
    return result


# ── Group N — Predictive Validation ───────────────────────────────────────────


def _safe_auc(
    y_true: np.ndarray, proba: np.ndarray, classes: np.ndarray
) -> Optional[float]:
    """
    One-vs-rest macro AUC over the classes actually present in y_true.

    sklearn's multi_class="ovr" requires y_true to contain every class in `labels`,
    which never holds for a held-out batch, so the OvR average is assembled here.
    Returns None when no class has both positives and negatives.
    """
    present = set(np.unique(y_true))
    if len(present) < 2:
        return None
    aucs: list[float] = []
    for idx, cls in enumerate(classes):
        if cls not in present:
            continue
        binary = (y_true == cls).astype(int)
        if binary.sum() in (0, len(binary)):
            continue
        try:
            aucs.append(float(roc_auc_score(binary, proba[:, idx])))
        except ValueError:
            continue
    return float(np.mean(aucs)) if aucs else None


def _fold_pca_projections(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    min_test_n: int,
    n_pcs: int,
) -> tuple[list[dict], dict]:
    """
    Fit one PCA per leave-one-batch-out fold on the training batches only.

    The projections are label-independent, so they are computed once and reused by
    the observed run, the 2-class run and all label permutations.

    NA cells are dropped, never imputed: the matrices are already imputed upstream
    (strict / knn / softimpute), so a residual NA means the harmonizer failed and
    filling it would invent data.

    Returns
    -------
    tuple of (folds, diagnostics)
        folds: list of {"batch", "train_pos", "test_pos", "Z_train", "Z_test"}.
        diagnostics: NA-drop counts.
    """
    X = exp_df.values.astype(float)

    # Order matters: a sample that is entirely NA is a failed sample and must be
    # counted as such. Only after removing those is a gene still carrying an NA
    # genuinely unusable — dropping genes first would absorb whole failed samples
    # into the gene count and report zero dropped samples.
    sample_ok = ~np.isnan(X).all(axis=1)
    n_samples_dropped = int((~sample_ok).sum())
    positions = np.arange(len(exp_df))[sample_ok]
    X = X[sample_ok]

    gene_ok = ~np.isnan(X).any(axis=0) if X.size else np.zeros(X.shape[1], bool)
    n_genes_dropped = int((~gene_ok).sum())
    X = X[:, gene_ok]

    diagnostics = {
        "pv_n_genes_dropped_na": n_genes_dropped,
        "pv_n_samples_dropped_na": n_samples_dropped,
    }
    if X.shape[1] < n_pcs or X.shape[0] < 2 * min_test_n:
        return [], diagnostics

    batches = ann_df["RNA_BATCH"].astype(str).values[sample_ok]

    folds: list[dict] = []
    for level in np.unique(batches):
        test_mask = batches == level
        if test_mask.sum() < min_test_n or (~test_mask).sum() < n_pcs + 1:
            continue
        scaler = StandardScaler().fit(X[~test_mask])
        pca = PCA(n_components=n_pcs, svd_solver="randomized", random_state=RANDOM_SEED)
        Z_train = pca.fit_transform(scaler.transform(X[~test_mask]))
        Z_test = pca.transform(scaler.transform(X[test_mask]))
        folds.append(
            {
                "batch": str(level),
                "train_pos": positions[~test_mask],
                "test_pos": positions[test_mask],
                "Z_train": Z_train,
                "Z_test": Z_test,
            }
        )
    return folds, diagnostics


def _run_lobo(folds: list[dict], labels: pd.Series, collect_folds: bool) -> dict:
    """
    Evaluate leave-one-batch-out classification over pre-computed PCA folds.

    F1 is computed on every fold, including single-class test batches: a predictor
    facing a DLBCL-only batch should label as many of its samples DLBCL as it can,
    which is the honest deployment test. AUC is restricted to folds whose test batch
    holds at least two classes, because it is otherwise undefined.

    Returns
    -------
    dict with keys f1_macro, f1_weighted, bal_acc, mcc, auc_macro (lists over folds),
    per_class (class -> list of F1), n_folds, n_folds_multiclass, folds (optional).
    """
    y_all = labels.values
    out: dict = {
        "f1_macro": [],
        "f1_weighted": [],
        "bal_acc": [],
        "mcc": [],
        "auc_macro": [],
        "per_class": {},
        "n_folds": 0,
        "n_folds_multiclass": 0,
        "folds": {},
    }

    for fold in folds:
        y_tr = y_all[fold["train_pos"]]
        y_te = y_all[fold["test_pos"]]
        tr_ok = pd.notna(y_tr)
        te_ok = pd.notna(y_te)
        if tr_ok.sum() < 10 or te_ok.sum() < 1:
            continue
        y_tr_c = y_tr[tr_ok].astype(str)
        y_te_c = y_te[te_ok].astype(str)
        if len(set(y_tr_c)) < 2:
            continue

        model = LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=RANDOM_SEED
        )
        model.fit(fold["Z_train"][tr_ok], y_tr_c)
        Z_te = fold["Z_test"][te_ok]
        y_pred = model.predict(Z_te)

        present = sorted(set(y_te_c))
        f1_macro = float(
            f1_score(y_te_c, y_pred, labels=present, average="macro", zero_division=0)
        )
        f1_weighted = float(
            f1_score(
                y_te_c, y_pred, labels=present, average="weighted", zero_division=0
            )
        )
        auc = _safe_auc(y_te_c, model.predict_proba(Z_te), model.classes_)

        out["f1_macro"].append(f1_macro)
        out["f1_weighted"].append(f1_weighted)
        out["bal_acc"].append(float(balanced_accuracy_score(y_te_c, y_pred)))
        out["mcc"].append(float(matthews_corrcoef(y_te_c, y_pred)))
        out["n_folds"] += 1
        if len(present) >= 2:
            out["n_folds_multiclass"] += 1
        if auc is not None:
            out["auc_macro"].append(auc)

        per_class_f1 = f1_score(
            y_te_c, y_pred, labels=present, average=None, zero_division=0
        )
        for cls, val in zip(present, per_class_f1):
            out["per_class"].setdefault(cls, []).append(float(val))

        if collect_folds:
            out["folds"][fold["batch"]] = {
                "n": int(te_ok.sum()),
                "n_classes": len(present),
                "f1_macro": round(f1_macro, 4),
                "auc": round(auc, 4) if auc is not None else None,
            }
    return out


def compute_group_n(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    n_pcs: int = N_PCS,
    n_perm: int = N_PERM,
    min_test_n: int = MIN_TEST_N,
) -> dict:
    """
    Compute Group N metrics: leave-one-batch-out diagnosis prediction.

    A logistic regression on the first n_pcs principal components is trained on all
    batches but one and evaluated on the held-out batch, for a 3-class target
    (FL / DLBCL / Normal_B) and a 2-class target (FL vs DLBCL). PCA is fitted on the
    training batches only and the held-out batch projected, so no test-set structure
    leaks into the features.

    A permutation negative control shuffles the labels globally n_perm times and
    repeats both evaluations. This is cheap because the per-fold PCA is
    label-independent and therefore reused across every permutation.

    Parameters
    ----------
    exp_df : pd.DataFrame
        Expression matrix (samples x genes).
    ann_df : pd.DataFrame
        Annotation DataFrame aligned to exp_df rows.
    n_pcs : int
        Number of principal components used as features.
    n_perm : int
        Label permutations for the negative control.
    min_test_n : int
        Batches smaller than this are not used as a held-out fold.

    Returns
    -------
    dict of pv_* metric name -> value
    """
    result: dict = {"pv_n_perm": int(n_perm)}

    if "RNA_BATCH" not in ann_df.columns:
        result["pv_n_genes_dropped_na"] = 0
        result["pv_n_samples_dropped_na"] = 0
        for prefix in ("pv_lobo3", "pv_lobo2"):
            result[f"{prefix}_n_folds"] = 0
        return result

    folds, diagnostics = _fold_pca_projections(exp_df, ann_df, min_test_n, n_pcs)
    result.update(diagnostics)

    rng = np.random.default_rng(RANDOM_SEED)

    for prefix, n_classes in (("pv_lobo3", 3), ("pv_lobo2", 2)):
        labels = _predictor_labels(ann_df, n_classes=n_classes)
        if labels is None or not folds:
            result[f"{prefix}_n_folds"] = 0
            result[f"{prefix}_n_folds_multiclass"] = 0
            for suffix in (
                "f1_macro_mean",
                "f1_macro_median",
                "f1_macro_std",
                "f1_macro_min",
                "f1_weighted_mean",
                "bal_acc_mean",
                "mcc_mean",
                "auc_macro_mean",
                "f1_macro_perm_mean",
                "f1_macro_perm_std",
                "auc_macro_perm_mean",
                "f1_macro_delta",
                "f1_perm_pvalue",
            ):
                result[f"{prefix}_{suffix}"] = np.nan
            result[f"{prefix}_folds"] = {}
            continue

        obs = _run_lobo(folds, labels, collect_folds=True)

        def _agg(values: list[float], fn: object) -> float:
            return float(fn(values)) if values else np.nan  # type: ignore[operator]

        result[f"{prefix}_f1_macro_mean"] = _agg(obs["f1_macro"], np.mean)
        result[f"{prefix}_f1_macro_median"] = _agg(obs["f1_macro"], np.median)
        result[f"{prefix}_f1_macro_std"] = _agg(obs["f1_macro"], np.std)
        result[f"{prefix}_f1_macro_min"] = _agg(obs["f1_macro"], np.min)
        result[f"{prefix}_f1_weighted_mean"] = _agg(obs["f1_weighted"], np.mean)
        result[f"{prefix}_bal_acc_mean"] = _agg(obs["bal_acc"], np.mean)
        result[f"{prefix}_mcc_mean"] = _agg(obs["mcc"], np.mean)
        result[f"{prefix}_auc_macro_mean"] = _agg(obs["auc_macro"], np.mean)
        result[f"{prefix}_n_folds"] = obs["n_folds"]
        result[f"{prefix}_n_folds_multiclass"] = obs["n_folds_multiclass"]
        result[f"{prefix}_folds"] = obs["folds"]
        for cls, vals in obs["per_class"].items():
            result[f"{prefix}_f1_per_class_{cls}"] = float(np.mean(vals))

        perm_f1: list[float] = []
        perm_auc: list[float] = []
        for _ in range(max(0, n_perm)):
            shuffled = pd.Series(
                rng.permutation(labels.values), index=labels.index, dtype=object
            )
            p = _run_lobo(folds, shuffled, collect_folds=False)
            if p["f1_macro"]:
                perm_f1.append(float(np.mean(p["f1_macro"])))
            if p["auc_macro"]:
                perm_auc.append(float(np.mean(p["auc_macro"])))

        result[f"{prefix}_f1_macro_perm_mean"] = _agg(perm_f1, np.mean)
        result[f"{prefix}_f1_macro_perm_std"] = _agg(perm_f1, np.std)
        result[f"{prefix}_auc_macro_perm_mean"] = _agg(perm_auc, np.mean)

        observed = result[f"{prefix}_f1_macro_mean"]
        if perm_f1 and not np.isnan(observed):
            result[f"{prefix}_f1_macro_delta"] = float(observed - np.mean(perm_f1))
            # +1 in numerator and denominator: the observed value is one draw from
            # the null, so the p-value can never be exactly zero.
            n_ge = int(sum(1 for v in perm_f1 if v >= observed))
            result[f"{prefix}_f1_perm_pvalue"] = float((n_ge + 1) / (len(perm_f1) + 1))
        else:
            result[f"{prefix}_f1_macro_delta"] = np.nan
            result[f"{prefix}_f1_perm_pvalue"] = np.nan

    return result


# ── Orchestrator ───────────────────────────────────────────────────────────────


def compute_all_metrics(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    skip_slow: bool = False,
    tmp_path: Optional[str] = None,
    groups: Optional[set] = None,
    ref_df: Optional[pd.DataFrame] = None,
    n_perm: int = N_PERM,
    panel: Optional[list[str]] = None,
    collect_gene_cohort_detail: bool = False,
    on_group_done: Optional[Callable[[dict], None]] = None,
) -> dict:
    """
    Compute all metric groups for one expression/annotation pair.

    Each group is run independently inside a try/except block.
    On failure, null values and a full traceback are written and computation
    continues for all remaining groups.
    After each group, the partial result dict is flushed to tmp_path (if given).
    Shared embeddings are computed lazily: PCA is computed when any of A, B, C, G, I, J
    are active; UMAP and tSNE are computed only when C is active. If PCA fails, all
    embedding-dependent groups are skipped gracefully; groups E, D, H, F still run.

    Parameters
    ----------
    exp_df : pd.DataFrame
        Expression matrix (samples × genes).
    ann_df : pd.DataFrame
        Annotation DataFrame aligned to exp_df rows.
    skip_slow : bool
        If True, skip Group F (variancePartition).
    tmp_path : str, optional
        Path to write incremental JSON after each group.
    groups : set of str, optional
        Subset of groups to compute, e.g. {"A", "B", "E"}.
        Valid values: A B C D E F G H I J K L M N (case-insensitive).
        Default: all groups. Group F is also gated by skip_slow.
    ref_df : pd.DataFrame, optional
        Unharmonized reference matrix (01_raw, post-removal off) aligned to exp_df's
        row index. Required by Group L only; Group L is skipped if it is absent.
    n_perm : int
        Label permutations for the Group N negative control.
    panel : list of str, optional
        Marker gene panel for Groups L and M. Default: the full annotation table.
    collect_gene_cohort_detail : bool
        Pass through to Group L; see compute_group_l.
    on_group_done : callable, optional
        Called with a shallow copy of the accumulated result dict after every group
        finishes (success or failure). Intended for durable incremental persistence
        (e.g. re-uploading the merged sidecar to S3) so a later group's crash or
        timeout cannot discard groups that already completed. Exceptions raised by
        this callback are caught and logged, never allowed to abort metric
        computation.

    Returns
    -------
    dict of all metric name → value
    """
    assert len(exp_df) == len(
        ann_df
    ), "exp_df and ann_df must have the same number of rows"

    # Determine which groups to run
    # F is gated by skip_slow; I is in the default active set (opt-out via --skip-wm)
    active: set[str] = (
        set("ABCDEFGHIJKLMN") if groups is None else {g.upper().strip() for g in groups}
    )

    result: dict = {}

    def _flush() -> None:
        if tmp_path:
            with open(tmp_path, "w") as fh:
                fh.write(dict_to_json_safe(result))
        if on_group_done is not None:
            try:
                on_group_done(dict(result))
            except Exception:
                print(
                    f"[{_ts()}][metrics] on_group_done callback FAILED:\n"
                    f"{traceback.format_exc()}",
                    flush=True,
                )

    def _run_group(name: str, fn: object, *args: object) -> None:
        if name not in active:
            return
        print(f"[{_ts()}][metrics] Starting group {name} ...", flush=True)
        t0 = time.time()
        try:
            group_result = fn(*args)  # type: ignore[operator]
            result.update(group_result)
            print(
                f"[{_ts()}][metrics] Group {name} done ({time.time()-t0:.1f}s)",
                flush=True,
            )
        except Exception:
            tb = traceback.format_exc()
            print(f"[{_ts()}][metrics] Group {name} FAILED:\n{tb}", flush=True)
            result[f"error_{name}"] = tb
        _flush()

    # Shared embeddings — PCA needed by A, B, G, I, J; UMAP and tSNE needed by C only.
    # Wrapped so a failure never prevents E, D, H, F from running.
    pca_coords: Optional[np.ndarray] = None
    eigenvalues: Optional[np.ndarray] = None
    umap_coords: Optional[np.ndarray] = None
    tsne_coords: Optional[np.ndarray] = None

    embedding_groups = active & {"A", "B", "C", "G", "I", "J"}
    if embedding_groups:
        print(f"[{_ts()}][metrics] Computing PCA ...", flush=True)
        try:
            pca_coords, eigenvalues = compute_pca(exp_df)
        except Exception:
            tb = traceback.format_exc()
            print(f"[{_ts()}][metrics] PCA FAILED:\n{tb}", flush=True)
            result["error_embeddings"] = tb
            for g in embedding_groups:
                result[f"error_{g}"] = "skipped: PCA failed"
            active -= embedding_groups
            _flush()

    if pca_coords is not None and "C" in active:
        print(f"[{_ts()}][metrics] Computing UMAP ...", flush=True)
        try:
            umap_coords = compute_umap(pca_coords)
        except Exception:
            tb = traceback.format_exc()
            print(f"[{_ts()}][metrics] UMAP FAILED:\n{tb}", flush=True)
            result["error_umap"] = tb
            if "C" in active:
                result["error_C"] = "skipped: UMAP failed"
                active.discard("C")
            _flush()

        print(f"[{_ts()}][metrics] Computing tSNE ...", flush=True)
        try:
            tsne_coords = compute_tsne(pca_coords)
        except Exception:
            tb = traceback.format_exc()
            print(f"[{_ts()}][metrics] tSNE FAILED:\n{tb}", flush=True)
            result["error_tsne"] = tb
            if "C" in active:
                result["error_C"] = "skipped: tSNE failed"
                active.discard("C")
            _flush()

    _run_group("E", compute_group_e, exp_df, ann_df)
    _run_group("K", compute_group_k, exp_df, ann_df)
    _run_group("A", compute_group_a, pca_coords, eigenvalues, ann_df)
    _run_group("J", compute_group_j, pca_coords, eigenvalues)
    _run_group("B", compute_group_b, pca_coords, ann_df)
    _run_group("C", compute_group_c, umap_coords, tsne_coords, ann_df)
    _run_group("D", compute_group_d, exp_df, ann_df)
    _run_group("G", compute_group_g, pca_coords, ann_df)
    _run_group("H", compute_group_h, exp_df, ann_df)
    _run_group("I", compute_group_i, exp_df, ann_df, pca_coords)

    # Group L is the only group that compares against a second matrix. Skipping it
    # when no reference was supplied must not affect M, N or A-K.
    if "L" in active and ref_df is None:
        result["error_L"] = "skipped: no raw reference supplied"
        active.discard("L")
        _flush()

    _run_group(
        "L",
        compute_group_l,
        exp_df,
        ref_df,
        ann_df,
        panel,
        MIN_COHORT_N,
        collect_gene_cohort_detail,
    )
    _run_group("M", compute_group_m, exp_df, ann_df, panel)
    _run_group("N", compute_group_n, exp_df, ann_df, N_PCS, n_perm)

    if not skip_slow:
        _run_group("F", compute_group_f, exp_df, ann_df)

    return result
