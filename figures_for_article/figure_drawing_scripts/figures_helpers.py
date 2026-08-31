"""
figures_helpers.py — Data preparation utilities for Finally_assembled_figures_for_article.ipynb.

Contains ONLY data loading, filtering, normalization, and S3 I/O helpers.
Plotting functions are NOT here — they live directly in figure cells.

Filtering logic mirrors harmonization_metrics_analysis_v3.ipynb cells 1–11.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler

warnings.filterwarnings("ignore")


# ── Internal constants (mirrors v3 notebook cells 1 & 6) ─────────────────────

_META_COLS = ["strat", "imp", "method", "post_rm", "status", "compute_time_s"]

# Prefixes of the blind-check metric groups L (mk_), M (xb_) and N (pv_). These are
# stripped from metric_cols in load_metrics_data(), so they never reach scoring_cols,
# the Figure 3 clustermap or the composite score.
#
# Do NOT add L/M/N to _GROUP_MAP below. Giving them a group letter would pull them into
# col_meta and surface them in the v3 notebook's per-group figures, which is exactly the
# contamination the split is there to prevent. Load them with
# load_new_metrics_data() instead.
_BLIND_CHECK_PREFIXES = ("mk_", "xb_", "pv_")

_GROUP_MAP = {
    "A": ["r2_", "pcr_", "dsc_"],
    "B": ["kbet_", "ilisi_", "clisi_", "asw_batch", "asw_bio", "cms_"],
    "C": ["umap_", "tsne_"],
    "D": ["ks_", "per_gene_batch"],
    "E": [
        "n_samples", "n_genes", "n_batches", "n_cohorts", "n_diagnosis_groups",
        "n_samples_per_batch", "zero_", "fraction_", "exp_", "per_batch_median",
        "bimodal", "below_1",
    ],
    "F": ["vp_"],
    "G": ["graph_"],
    "H": ["avg_intra_", "avg_inter_", "dist_ratio_"],
    "I": ["wm_"],
    "J": ["pct_var_pc", "pct_var_cum"],
    "K": [
        "n_genes_noNA", "pct_genes_noNA", "n_samples_noNA", "pct_samples_noNA",
        "n_genes_allNA", "n_samples_allNA", "n_na_cells", "pct_na_cells",
    ],
}

_ANNOT_COLS_ORDER = [
    "RNA_BATCH", "PLATFORM_RNA", "RNASEQ_SOURCE", "COHORT_LABEL",
    "Major_group", "Diagnosis_cell_type_unified", "TUMOR_NORMAL", "global/all",
]

# Exact column names that are unnormalized ASW variants — excluded from metric_cols
_SKIP_EXACT = {
    "asw_batch_COHORT_LABEL", "asw_batch_PLATFORM_RNA",
    "asw_batch_RNASEQ_SOURCE", "asw_batch_RNA_BATCH",
    "asw_bio_Diagnosis_cell_type_unified", "asw_bio_Major_group",
    "asw_bio_PLATFORM_RNA", "asw_bio_TUMOR_NORMAL",
}

# Manual polarity overrides — full dict from v3 notebook cell 10
_POLARITY_MANUAL: dict[str, int] = {
    "asw_batch_norm_COHORT_LABEL": 1,
    "asw_batch_norm_PLATFORM_RNA": 1,
    "asw_batch_norm_RNASEQ_SOURCE": 1,
    "asw_batch_norm_RNA_BATCH": 1,
    "asw_bio_norm_Diagnosis_cell_type_unified": 1,
    "asw_bio_norm_Major_group": 1,
    "asw_bio_norm_PLATFORM_RNA": 0,
    "asw_bio_norm_TUMOR_NORMAL": 1,
    "avg_inter_dist_COHORT_LABEL": 0,
    "avg_inter_dist_Diagnosis_cell_type_unified": 0,
    "avg_inter_dist_Major_group": 0,
    "avg_inter_dist_PLATFORM_RNA": 0,
    "avg_inter_dist_RNASEQ_SOURCE": 0,
    "avg_inter_dist_RNA_BATCH": 0,
    "avg_inter_dist_TUMOR_NORMAL": 0,
    "avg_intra_dist_COHORT_LABEL": 0,
    "avg_intra_dist_Diagnosis_cell_type_unified": 0,
    "avg_intra_dist_Major_group": 0,
    "avg_intra_dist_PLATFORM_RNA": 0,
    "avg_intra_dist_RNASEQ_SOURCE": 0,
    "avg_intra_dist_RNA_BATCH": 0,
    "avg_intra_dist_TUMOR_NORMAL": 0,
    "below_1_fraction_by_batch_max": 0,
    "below_1_fraction_by_batch_min": 0,
    "clisi_mean_Diagnosis_cell_type_unified": 1,
    "clisi_mean_Major_group": 1,
    "clisi_mean_PLATFORM_RNA": 0,
    "clisi_mean_TUMOR_NORMAL": 1,
    "cms_fraction_mixed_COHORT_LABEL": 1,
    "cms_fraction_mixed_PLATFORM_RNA": 1,
    "cms_fraction_mixed_RNASEQ_SOURCE": 1,
    "cms_fraction_mixed_RNA_BATCH": 1,
    "cms_mean_COHORT_LABEL": 0,
    "cms_mean_PLATFORM_RNA": 0,
    "cms_mean_RNASEQ_SOURCE": 0,
    "cms_mean_RNA_BATCH": 0,
    "dist_ratio_COHORT_LABEL": 1,
    "dist_ratio_Diagnosis_cell_type_unified": -1,
    "dist_ratio_Major_group": -1,
    "dist_ratio_PLATFORM_RNA": 1,
    "dist_ratio_RNASEQ_SOURCE": 1,
    "dist_ratio_RNA_BATCH": 1,
    "dist_ratio_TUMOR_NORMAL": -1,
    "dsc_COHORT_LABEL": -1,
    "dsc_PLATFORM_RNA": -1,
    "dsc_RNASEQ_SOURCE": -1,
    "dsc_RNA_BATCH": -1,
    "exp_max": 0, "exp_median": 0, "exp_min": 0, "exp_p01": 0, "exp_p05": 0,
    "exp_p25": 0, "exp_p75": 0, "exp_p95": 0, "exp_p99": 0, "exp_std": 0,
    "fraction_cohorts_bimodal": 1,
    "fraction_cohorts_zero_inflated_bimodal": 1,
    "fraction_genes_below_1": 0,
    "graph_connectivity_Diagnosis_cell_type_unified": 1,
    "graph_connectivity_Major_group": 1,
    "graph_connectivity_PLATFORM_RNA": 0,
    "graph_connectivity_TUMOR_NORMAL": 1,
    "ilisi_norm_COHORT_LABEL": 1,
    "ilisi_norm_PLATFORM_RNA": 1,
    "ilisi_norm_RNASEQ_SOURCE": 1,
    "ilisi_norm_RNA_BATCH": 1,
    "kbet_acceptance_rate_COHORT_LABEL": 1,
    "kbet_acceptance_rate_PLATFORM_RNA": 1,
    "kbet_acceptance_rate_RNASEQ_SOURCE": 1,
    "kbet_acceptance_rate_RNA_BATCH": 1,
    "ks_cohort_within_batch_frac_sig": -1,
    "ks_cohort_within_batch_mean_D": -1,
    "ks_frac_sig_COHORT_LABEL": -1,
    "ks_frac_sig_PLATFORM_RNA": -1,
    "ks_frac_sig_RNA_BATCH": -1,
    "ks_mean_D_COHORT_LABEL": -1,
    "ks_mean_D_PLATFORM_RNA": -1,
    "ks_mean_D_RNA_BATCH": -1,
    "n_batches": 0, "n_cohorts": 0, "n_diagnosis_groups": 0,
    "n_genes": 0, "n_samples": 0,
    "pcr_COHORT_LABEL": 1,
    "pcr_Diagnosis_cell_type_unified": -1,
    "pcr_Major_group": -1,
    "pcr_PLATFORM_RNA": 1,
    "pcr_RNASEQ_SOURCE": 1,
    "pcr_RNA_BATCH": 1,
    "pcr_TUMOR_NORMAL": -1,
    "per_batch_median_cv": 0,
    "pct_samples_allNA": -1,
    "pct_genes_allNA": -1,
    "pct_genes_noNA": 1,
    "pct_na_cells": -1,
    "pct_samples_noNA": 1,
    "n_na_cells": 0,
    "per_gene_batch_mean_cv_COHORT_LABEL": -1,
    "per_gene_batch_mean_cv_PLATFORM_RNA": -1,
    "per_gene_batch_mean_cv_RNA_BATCH": -1,
    "r2_COHORT_LABEL": 0, "r2_Major_group": 0, "r2_PLATFORM_RNA": 0,
    "r2_RNASEQ_SOURCE": 0, "r2_RNA_BATCH": 0, "r2_TUMOR_NORMAL": 0,
    "tsne_centroid_disp_COHORT_LABEL": -1,
    "tsne_centroid_disp_PLATFORM_RNA": -1,
    "tsne_centroid_disp_RNASEQ_SOURCE": -1,
    "tsne_centroid_disp_RNA_BATCH": -1,
    "tsne_entropy_mean_COHORT_LABEL": 0,
    "tsne_entropy_mean_PLATFORM_RNA": 0,
    "tsne_entropy_mean_RNASEQ_SOURCE": 0,
    "tsne_entropy_mean_RNA_BATCH": 0,
    "tsne_entropy_norm_COHORT_LABEL": 1,
    "tsne_entropy_norm_PLATFORM_RNA": 1,
    "tsne_entropy_norm_RNASEQ_SOURCE": 1,
    "tsne_entropy_norm_RNA_BATCH": 1,
    "umap_centroid_disp_COHORT_LABEL": -1,
    "umap_centroid_disp_PLATFORM_RNA": -1,
    "umap_centroid_disp_RNASEQ_SOURCE": -1,
    "umap_centroid_disp_RNA_BATCH": -1,
    "umap_entropy_mean_COHORT_LABEL": 0,
    "umap_entropy_mean_PLATFORM_RNA": 0,
    "umap_entropy_mean_RNASEQ_SOURCE": 0,
    "umap_entropy_mean_RNA_BATCH": 0,
    "umap_entropy_norm_COHORT_LABEL": 1,
    "umap_entropy_norm_PLATFORM_RNA": 1,
    "umap_entropy_norm_RNASEQ_SOURCE": 1,
    "umap_entropy_norm_RNA_BATCH": 1,
    "wm_COHORT_LABEL": -1,
    "wm_Diagnosis_cell_type_unified": 1,
    "wm_Major_group": 1,
    "wm_PLATFORM_RNA": -1,
    "wm_RNASEQ_SOURCE": 1,
    "wm_RNA_BATCH": -1,
    "wm_TUMOR_NORMAL": 1,
    "wm_mean_batch": -1,
    "wm_mean_bio": 1,
    "wm_ratio_bio_batch": 1,
    "zero_fraction_by_batch_max": 0,
    "zero_fraction_by_batch_min": 0,
    "zero_fraction_global": 0,
}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _classify_metric_col(col: str) -> tuple[str, str]:
    """Return (group_letter, annot_col) for a metric column name."""
    for g, prefixes in _GROUP_MAP.items():
        if any(col.startswith(p) or col == p.rstrip("_") for p in prefixes):
            grp = g
            break
    else:
        grp = "?"
    annot = "global/all"
    for a in _ANNOT_COLS_ORDER[:-1]:
        if a in col:
            annot = a
            break
    return grp, annot


def _build_polarity(metric_cols: list[str]) -> dict[str, int]:
    """Compute polarity map for all metric columns (auto + manual overrides).

    Replicates the logic in harmonization_metrics_analysis_v3.ipynb cells 8 & 10.
    POLARITY[c] = +1 → higher raw value = better
    POLARITY[c] = -1 → lower raw value = better
    POLARITY[c] =  0 → descriptive, excluded from composite scoring
    """
    polarity: dict[str, int] = {}

    for c in metric_cols:
        g, _ = _classify_metric_col(c)
        if g == "A":
            polarity[c] = -1
        elif g == "B":
            if any(x in c for x in ("asw_bio_norm", "asw_batch_norm",
                                     "kbet", "ilisi_norm", "cms_fraction_mixed",
                                     "clisi_mean")):
                polarity[c] = +1
            else:
                polarity[c] = 0
        elif g == "C":
            if "entropy_norm" in c:
                polarity[c] = +1
            elif "centroid_disp" in c:
                polarity[c] = -1
            else:
                polarity[c] = 0
        elif g == "D":
            if any(x in c for x in ("ks_mean_D", "ks_frac_sig", "ks_cohort",
                                     "per_gene_batch_mean_cv")):
                polarity[c] = -1
            else:
                polarity[c] = 0
        elif g == "E":
            polarity[c] = 0
        elif g == "F":
            polarity[c] = -1 if "RNA_BATCH" in c else +1
        elif g == "G":
            polarity[c] = +1
        elif g == "H":
            polarity[c] = -1 if "dist_ratio" in c else 0
        elif g == "I":
            _batch_keys = ("RNA_BATCH", "PLATFORM_RNA", "RNASEQ_SOURCE", "COHORT_LABEL")
            _bio_keys = ("Major_group", "Diagnosis", "TUMOR_NORMAL")
            if "mean_batch" in c or (c.startswith("wm_") and any(b in c for b in _batch_keys)):
                polarity[c] = -1
            elif ("mean_bio" in c or "ratio_bio_batch" in c
                  or (c.startswith("wm_") and any(b in c for b in _bio_keys))):
                polarity[c] = +1
            else:
                polarity[c] = 0
        elif g == "J":
            polarity[c] = 0
        elif g == "K":
            if c in ("pct_genes_noNA", "pct_samples_noNA"):
                polarity[c] = +1
            elif c in ("n_genes_allNA", "n_samples_allNA", "n_na_cells", "pct_na_cells"):
                polarity[c] = -1
            else:
                polarity[c] = 0
        else:
            polarity[c] = 0

    # pcr_ override: batch covariates → lower=better; biology covariates → higher=better
    _batch_annot = ("RNA_BATCH", "PLATFORM_RNA", "RNASEQ_SOURCE", "COHORT_LABEL")
    for c in metric_cols:
        if c.startswith("pcr_"):
            polarity[c] = -1 if any(b in c for b in _batch_annot) else +1

    # Apply manual overrides from the validated dict
    polarity.update({k: v for k, v in _POLARITY_MANUAL.items() if k in polarity})

    return polarity


def _normalize_metrics(
    df_vals: pd.DataFrame,
    cols: list[str],
    polarity: dict[str, int],
) -> pd.DataFrame:
    """Normalize metric columns to [0,1] where 1 = best.

    Pipeline: median NaN fill → MinMaxScaler → polarity flip for lower-is-better cols.

    Parameters
    ----------
    df_vals : pd.DataFrame
        Raw metric values, samples × metrics.
    cols : list[str]
        Columns to normalize; missing columns are silently skipped.
    polarity : dict[str, int]
        Maps each column to +1 or -1; 0 columns should not be in cols.

    Returns
    -------
    pd.DataFrame
        Same index as df_vals, columns = valid cols, values in [0, 1], no NaN.
    """
    valid_cols = [c for c in cols if c in df_vals.columns]
    normed = df_vals[valid_cols].copy().astype(float)
    filled = normed.fillna(normed.median())
    scaler = MinMaxScaler()
    normed[valid_cols] = scaler.fit_transform(filled)
    for c in valid_cols:
        if polarity.get(c, 1) == -1:
            normed[c] = 1.0 - normed[c]
    return normed


# ── Public API ────────────────────────────────────────────────────────────────

def save_figure(
    fig: plt.Figure,
    name: str,
    figures_dir: Path = Path("figures"),
) -> None:
    """Save figure as PDF and SVG (vector) plus PNG (dpi=200) to figures_dir.

    PDF and SVG are the project's required defaults for publication figures; the PNG is
    kept for quick previews and for slide decks.

    Parameters
    ----------
    fig : plt.Figure
    name : str
        Filename stem (no extension).
    figures_dir : Path
        Output directory; created if absent.
    """
    figures_dir = Path(figures_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(figures_dir / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(figures_dir / f"{name}.svg", bbox_inches="tight")
    fig.savefig(figures_dir / f"{name}.png", bbox_inches="tight", dpi=200)


def load_metrics_data(
    csv_path: str | Path = (
        Path("..") / "harmonization-metrics" / "metric_tables"
        / "metrics_comprehensive_260609.csv"
    ),
) -> tuple[pd.DataFrame, pd.DataFrame, list[str], pd.DataFrame]:
    """Load and filter metrics CSV; return the four objects used throughout the notebook.

    Applies the same filtering pipeline as harmonization_metrics_analysis_v3.ipynb:
      1. Build run_id index from strat/imp/method/post_rm.
      2. Filter to status == "ok".
      3. Drop all Shambhala methods except shambhala_P0std_Q0std (renamed 20_shambhala).
      4. Build metric_cols with exclusions matching v3 notebook.
      5. Classify each column into group letter + annot_col → col_meta.
      6. Build polarity map (auto + manual overrides).
      7. Normalize to [0,1] with polarity flip → df_normed.

    Parameters
    ----------
    csv_path : str or Path

    Returns
    -------
    df_ok : pd.DataFrame, shape (2234, ~230)
        Filtered metrics; index = run_id.
    df_normed : pd.DataFrame, shape (2234, n_scoring_cols)
        Polarity-normalized scores in [0,1]; 1 = best.
    scoring_cols : list[str]
        Column names with nonzero polarity (used in composite scoring).
    col_meta : pd.DataFrame
        Index = metric column name; columns = [group, annot_col, metric_type].
    """
    df = pd.read_csv(csv_path)
    df["run_id"] = (
        df["strat"] + "__" + df["imp"] + "__" + df["method"]
        + "__post" + df["post_rm"].map({False: "0", True: "1"})
    )
    df = df.set_index("run_id")

    error_cols = [c for c in df.columns if c.startswith("error")]

    df_ok = df[df["status"] == "ok"].copy()

    # Keep one canonical Shambhala representative only
    df_ok = df_ok[
        (~df_ok["method"].str.startswith("shambhala_"))
        | (df_ok["method"] == "shambhala_P0std_Q0std")
    ].copy()
    df_ok.loc[df_ok["method"] == "shambhala_P0std_Q0std", "method"] = "20_shambhala"

    # NA filter: exclude approaches where >5% of all samples have all-NA expression.
    # Uses n_samples_allNA (absolute count); threshold = 5% × 5,444 total samples.
    # Removes 38_harman and 34_arsyn (168 rows total), leaving 2,234 valid runs.
    _TOTAL_SAMPLES = 5444
    df_ok["pct_samples_allNA"] = df_ok["n_samples_allNA"] * 100 / df_ok["n_samples"]
    df_ok["pct_genes_allNA"] = df_ok["n_genes_allNA"] * 100 / df_ok["n_genes"]
    
    if "n_samples_allNA" in df_ok.columns:
        n_before = len(df_ok)
        df_ok = df_ok[df_ok["n_samples_allNA"] < _TOTAL_SAMPLES * 0.05].copy()
        print(
            f"NA filter: {n_before} → {len(df_ok)} rows "
            f"(removed {n_before - len(df_ok)} invalid approaches)"
        )
    elif "pct_samples_allNA" in df_ok.columns:
        n_before = len(df_ok)
        df_ok = df_ok[df_ok["pct_samples_allNA"] < 0.05].copy()
        print(
            f"NA filter: {n_before} → {len(df_ok)} rows "
            f"(removed {n_before - len(df_ok)} invalid approaches)"
        )

    # Build metric_cols excluding meta, error, skip-exact, and known noisy prefixes
    metric_cols = [
        c for c in df_ok.columns
        if c not in _META_COLS
        and c not in error_cols
        and c not in _SKIP_EXACT
        and not c.startswith("r2_pc")
        and not c.startswith("dsc_pvalue")
        and not c.startswith("n_cohorts_")
        and not c.startswith("n_samples_per_batch")
        and not c.startswith("ilisi_mean")
        and not c.startswith(_BLIND_CHECK_PREFIXES)
        and c != "wm_subsampled"
    ]

    # col_meta: group letter + annotation column + broad metric type
    def _classify_type(col: str) -> str:
        _type_map = {
            "local_neighborhood": ["kbet_", "ilisi_", "clisi_",
                                   "graph_connectivity_", "umap_entropy_", "tsne_entropy_"],
            "global_distance": ["r2_", "pcr_", "dsc_", "umap_centroid_disp_",
                                "tsne_centroid_disp_", "dist_ratio_", "avg_intra_dist_",
                                "avg_inter_dist_", "asw_batch_", "asw_bio_", "cms_",
                                "pct_var_pc", "pct_var_cum", "wm_"],
            "distribution_similarity": ["ks_mean_D_", "ks_frac_sig_",
                                        "ks_cohort_within_batch_", "per_gene_batch_mean_cv_"],
        }
        for type_name, prefixes in _type_map.items():
            if any(col.startswith(p) for p in prefixes):
                return type_name
        return "other"

    col_meta = pd.DataFrame(
        [_classify_metric_col(c) for c in metric_cols],
        index=metric_cols,
        columns=["group", "annot_col"],
    )
    col_meta["metric_type"] = col_meta.index.map(_classify_type)
    col_meta.index.name = "metric"

    polarity = _build_polarity(metric_cols)
    scoring_cols = [c for c in polarity.keys() if polarity.get(c, 0) != 0]

    df_normed = _normalize_metrics(df_ok, scoring_cols, polarity)

    # Structural guard: a future edit that lets a blind-check metric into the scoring
    # set would silently change Figure 3 and the composite score. Fail loudly instead.
    leaked = [c for c in scoring_cols if c.startswith(_BLIND_CHECK_PREFIXES)]
    assert not leaked, (
        f"Blind-check metrics reached scoring_cols: {leaked}. Groups L/M/N must stay out "
        f"of the clustermap — see _BLIND_CHECK_PREFIXES."
    )

    print(
        f"df_ok: {df_ok.shape}  |  scoring_cols: {len(scoring_cols)}"
        f"  |  groups: {sorted(col_meta['group'].unique())}"
    )
    return df_ok, df_normed, scoring_cols, col_meta


def build_best_vs_rest(
    df_ok: pd.DataFrame,
    top_ids: list[tuple[str, str, str]],
    best_label: str = "Best",
    best_color: str = "#E63946",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Mark the 15 best approaches in df_ok; build df_best and data_v3.

    Parameters
    ----------
    df_ok : pd.DataFrame
        Full filtered metrics table (index = run_id).
    top_ids : list of (method, imp, strat) tuples
        Identifies the best approaches; only post_rm=False rows are matched.
    best_label : str
        Method label assigned to the cloned 'Best' rows in data_v3.
    best_color : str
        Reserved for use in figure cells (returned for convenience).

    Returns
    -------
    df_best : pd.DataFrame
        Rows of df_ok matching top_ids (post_rm=False only).
    df_best_tagged : pd.DataFrame
        Copy of df_best with method column overwritten to best_label.
    data_v3 : pd.DataFrame
        Concatenation of df_ok and df_best_tagged (2,249 rows).
    """
    top_ids_set = set(top_ids)
    df_ok["is_best"] = df_ok.apply(
        lambda r: (r["method"], r["imp"], r["strat"]) in top_ids_set and not r["post_rm"],
        axis=1,
    )
    df_best = df_ok[df_ok["is_best"]].copy()

    df_best_tagged = df_best.copy()
    df_best_tagged["method"] = best_label

    data_v3 = pd.concat([df_ok, df_best_tagged], ignore_index=False)

    print(
        f"df_best: {len(df_best)} rows  |  methods in best: {sorted(df_best['method'].unique())}"
    )
    return df_best, df_best_tagged, data_v3


def compute_nona_genes_per_batch(
    comb_exp_raw: pd.DataFrame,
    comb_ann: pd.DataFrame,
    batch_to_platform_group: dict[str, str],
) -> pd.DataFrame:
    """Count non-NA genes per RNA_BATCH from the raw expression matrix.

    Parameters
    ----------
    comb_exp_raw : pd.DataFrame
        Samples × genes expression matrix (samples as rows).
    comb_ann : pd.DataFrame
        Sample annotation; must contain RNA_BATCH column.
    batch_to_platform_group : dict
        Maps RNA_BATCH string → platform group label.

    Returns
    -------
    pd.DataFrame
        Columns: RNA_BATCH, n_nona_genes, pct_nona_genes, platform_group.
        Sorted ascending by n_nona_genes.
    """
    merged = comb_ann[["RNA_BATCH"]].join(comb_exp_raw, how="inner")

    records = []
    total_genes = comb_exp_raw.shape[1]
    for batch, grp in merged.groupby("RNA_BATCH"):
        expr = grp.drop(columns=["RNA_BATCH"])
        n_nona = int((expr.notna().any(axis=0)).sum())
        records.append({
            "RNA_BATCH": batch,
            "n_nona_genes": n_nona,
            "pct_nona_genes": 100.0 * n_nona / total_genes if total_genes > 0 else 0.0,
            "platform_group": batch_to_platform_group.get(batch, "Unknown"),
        })

    result = pd.DataFrame(records).sort_values("n_nona_genes", ascending=True).reset_index(drop=True)
    return result


def load_gene_lists_from_s3(
    s3_client: Any,
    bucket: str,
    strategies: list[str],
    imputations: list[str] | None = None,
    method: str = "01_raw",
    post_rm: int = 0,
) -> dict[tuple[str, str], set[str]]:
    """Download gene list JSON sidecars from S3 for given (strat, imp) pairs.

    S3 key pattern: FL_batch_correction/genes/{strat}__{imp}__{method}__post{post_rm}_genes.json

    Parameters
    ----------
    s3_client : boto3 S3 client
    bucket : str
    strategies : list[str]
    imputations : list[str], optional
        Defaults to ["strict", "knn", "softimpute"].
    method : str
        Normalization method tag in the key.
    post_rm : int
        0 or 1.

    Returns
    -------
    dict keyed by (strat, imp) → set of gene symbol strings.
        Missing keys are silently skipped with a printed warning.
    """
    if imputations is None:
        imputations = ["strict", "knn", "softimpute"]

    gene_sets: dict[tuple[str, str], set[str]] = {}
    for strat in strategies:
        for imp in imputations:
            key = (
                f"FL_batch_correction/genes/{strat}__{imp}__{method}"
                f"__post{post_rm}_genes.json"
            )
            try:
                obj = s3_client.get_object(Bucket=bucket, Key=key)
                genes = json.loads(obj["Body"].read())
                gene_sets[(strat, imp)] = set(genes)
                print(f"  loaded ({strat}, {imp}): {len(gene_sets[(strat, imp)])} genes")
            except Exception as e:
                print(f"  WARNING: could not load {key}: {e}")

    return gene_sets


# ── Blind final check — metric groups L, M, N ─────────────────────────────────

_METRIC_TABLES = Path("..") / "harmonization-metrics" / "metric_tables"


def load_new_metrics_data(
    csv_path: str | Path | None = None,
    gene_long_path: str | Path | None = None,
    cohort_long_path: str | Path | None = None,
    folds_long_path: str | Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame,
           list[str], list[str], list[str]]:
    """Load the Groups L/M/N wide table and the three long-format detail tables.

    The wide table is the same `metrics_comprehensive.csv` the clustermap reads — the
    blind-check columns live there too, they are simply excluded from `scoring_cols`.
    The long tables come from `run_metrics_concat.py`.

    Parameters
    ----------
    csv_path : str or Path, optional
        Wide metrics CSV. Default: the newest metrics_comprehensive_*.csv in
        harmonization-metrics/metric_tables/.
    gene_long_path, cohort_long_path, folds_long_path : str or Path, optional
        Long-format tables. Default: the matching filenames in the same directory.
        A missing file yields an empty DataFrame with the right columns.

    Returns
    -------
    df_lmn : pd.DataFrame
        Wide table indexed by run_id, restricted to metadata + blind-check columns.
    df_gene_long : pd.DataFrame
        run_id, gene, rho, n_cohorts.
    df_cohort_long : pd.DataFrame
        run_id, cohort, rho.
    df_folds_long : pd.DataFrame
        run_id, target, batch, n, n_classes, f1_macro, auc.
    mk_cols, xb_cols, pv_cols : list of str
        Column names per group, in the wide table.
    """
    if csv_path is None:
        candidates = sorted(_METRIC_TABLES.glob("metrics_comprehensive_*.csv"))
        if not candidates:
            raise FileNotFoundError(f"No metrics_comprehensive_*.csv in {_METRIC_TABLES}")
        csv_path = candidates[-1]
        print(f"Using wide table: {csv_path}")

    df = pd.read_csv(csv_path)
    df["run_id"] = (
        df["strat"] + "__" + df["imp"] + "__" + df["method"]
        + "__post" + df["post_rm"].map({False: "0", True: "1"})
    )
    df = df.set_index("run_id")

    mk_cols = sorted(c for c in df.columns if c.startswith("mk_"))
    xb_cols = sorted(c for c in df.columns if c.startswith("xb_"))
    pv_cols = sorted(c for c in df.columns if c.startswith("pv_"))
    keep = [c for c in _META_COLS if c in df.columns] + mk_cols + xb_cols + pv_cols
    df_lmn = df[keep].copy()

    base = Path(csv_path).parent
    specs = [
        (gene_long_path, "marker_gene_correlations_long.csv",
         ["run_id", "gene", "rho", "n_cohorts"]),
        (cohort_long_path, "marker_cohort_correlations_long.csv",
         ["run_id", "cohort", "rho"]),
        (folds_long_path, "prediction_folds_long.csv",
         ["run_id", "target", "batch", "n", "n_classes", "f1_macro", "auc"]),
    ]
    loaded: list[pd.DataFrame] = []
    for given, default_name, columns in specs:
        path = Path(given) if given is not None else base / default_name
        if path.exists():
            loaded.append(pd.read_csv(path))
        else:
            print(f"  NOTE: {path.name} not found — returning an empty table.")
            loaded.append(pd.DataFrame(columns=columns))

    print(
        f"df_lmn: {df_lmn.shape}  |  mk: {len(mk_cols)}  xb: {len(xb_cols)}  "
        f"pv: {len(pv_cols)}"
    )
    return (df_lmn, loaded[0], loaded[1], loaded[2], mk_cols, xb_cols, pv_cols)


def filter_genes_complete_across_attempts(
    df_gene_long: pd.DataFrame, min_frac: float = 1.0
) -> list[str]:
    """Genes with a non-NA correlation in every attempt.

    Marker coverage differs by batch-removal strategy and imputation, so averaging over
    all genes would compare different gene sets between approaches. Restricting to genes
    present everywhere makes the cross-approach means comparable.

    Parameters
    ----------
    df_gene_long : pd.DataFrame
        Output of load_new_metrics_data()[1].
    min_frac : float
        Fraction of attempts in which the gene must be non-NA. 1.0 = every attempt.

    Returns
    -------
    list of str
        Sorted gene symbols meeting the threshold.
    """
    if df_gene_long.empty:
        return []
    n_runs = df_gene_long["run_id"].nunique()
    counts = df_gene_long.dropna(subset=["rho"]).groupby("gene")["run_id"].nunique()
    complete = sorted(counts[counts >= min_frac * n_runs].index.tolist())
    n_total = df_gene_long["gene"].nunique()
    print(
        f"Genes complete in >= {min_frac:.0%} of {n_runs} attempts: "
        f"{len(complete)} / {n_total} (dropped {n_total - len(complete)})"
    )
    return complete


def attach_raw_baseline(
    df: pd.DataFrame,
    metrics: list[str],
    baseline_method: str = "01_raw",
    baseline_post_rm: int = 0,
) -> pd.DataFrame:
    """Join each attempt to its unharmonized baseline and add *_raw / *_delta columns.

    Groups M and N are computed from one matrix, so the before/after comparison is made
    here rather than inside every job: 01_raw is itself an attempt in the benchmark, and
    recomputing it per job would repeat the same number about sixty times per
    (strat, imp) pair.

    The baseline is always 01_raw with post-removal off. A post_rm=True row therefore
    compares against a baseline with a different sample set, because post-removal drops
    method-specific outlier batches. These metrics are means over sample pairs and folds
    rather than sample-matched statistics, so the comparison holds — but post0 and post1
    must be reported separately and post1 deltas treated as approximate.

    Parameters
    ----------
    df : pd.DataFrame
        Wide table indexed by run_id, with strat / imp columns.
    metrics : list of str
        Columns to compare against the baseline.
    baseline_method : str
        Method tag of the baseline attempt.
    baseline_post_rm : int
        0 or 1; the baseline's post-removal variant.

    Returns
    -------
    pd.DataFrame
        Copy of df with `{metric}_raw`, `{metric}_delta` and `baseline_missing` added.
    """
    out = df.copy()
    base = df[df["method"] == baseline_method]
    base = base[base["post_rm"] == bool(baseline_post_rm)]
    lookup = base.set_index([base["strat"], base["imp"]])

    pair_index = pd.MultiIndex.from_arrays([out["strat"], out["imp"]])
    out["baseline_missing"] = ~pair_index.isin(lookup.index)

    for metric in metrics:
        if metric not in df.columns:
            print(f"  NOTE: {metric} absent from the table — skipped.")
            continue
        raw = pd.Series(lookup[metric].reindex(pair_index).values, index=out.index)
        out[f"{metric}_raw"] = raw
        out[f"{metric}_delta"] = out[metric] - raw

    n_missing = int(out["baseline_missing"].sum())
    if n_missing:
        print(f"  WARNING: {n_missing} rows have no {baseline_method} baseline.")
    return out
