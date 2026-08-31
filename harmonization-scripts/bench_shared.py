"""
Shared utilities for the harmonization benchmark cross-product scripts.
All normalization functions and helpers extracted from harmonization_benchmark.ipynb.
"""
from __future__ import annotations

import gzip
import io
import os
import pickle
import warnings

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

import rpy2.robjects as ro
from rpy2.robjects import pandas2ri
from rpy2.robjects.conversion import localconverter
from rpy2.robjects.packages import importr

# rpy2 ≥ 3.6 removed pandas2ri.activate(); use explicit converter contexts instead.
# Store direct references before any call-site renaming touches these names.
_pandas_py2rpy = pandas2ri.py2rpy
_pandas_rpy2py = pandas2ri.rpy2py
_PD_CONVERTER = ro.default_converter + pandas2ri.converter


def _py2rpy(x: object) -> object:
    with localconverter(_PD_CONVERTER):
        return ro.conversion.py2rpy(x)


def _rpy2py(x: object) -> object:
    with localconverter(_PD_CONVERTER):
        return ro.conversion.rpy2py(x)


def _r_gc() -> None:
    """Trigger R garbage collection to release R heap after expensive operations."""
    try:
        ro.r("invisible(gc())")
    except Exception:
        pass


# ── Constants ─────────────────────────────────────────────────────────────────
BIO_COL   = "Diagnosis_cell_type_unified"
BATCH_COL = "RNA_BATCH"
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

S3_EXP_KEY = os.environ.get(
    "BENCH_EXP_S3_KEY",
    f"{S3_PREFIX}/exp/comb_exp.tsv",
)
S3_ANN_KEY = os.environ.get(
    "BENCH_ANN_S3_KEY",
    f"{S3_PREFIX}/exp/comb_ann_unified.csv",
)

RARE_GROUPS: list[str] = [
    "Extranodal_Marginal_Zone_Lymphoma",
    "Double_Hit_Lymphoma",
    "Mantle_Cell_Lymphoma",
    "Chronic_Lymphocytic_Leukemia",
    "Other",
]
NORMAL_GROUPS: list[str] = [
    "Memory", "Centroblast", "Centrocyte", "Bone_marrow_CD19+",
    "Plasma", "Naive", "GC", "B_cells", "MZ", "Plasmablast", "Immature",
]
BAD_BATCHES_A: list[str] = [
    "GPL14951_FFPE_Unknown", "GPL8432_FFPE_Unknown", "GPL13938_FFPE_Unknown",
]
BAD_COHORTS_A: list[str] = ["SOM"]
BAD_BATCHES_B: list[str] = BAD_BATCHES_A + [
    "GPL6244_FFPE_Unknown",  "GPL17586_FF_Unknown",  "GPL20188_FF_Unknown",
    "GPL23541_FF_Unknown",   "GPL887_FFPE_Unknown",   "GPL26356_FF_Unknown",
    "GPL17047_FF_Unknown",   "GPL6244_FF_Unknown",
]
BAD_COHORTS_B: list[str] = ["SOM"]
MIN_BATCH_SIZE: int = 50

# Explicit set of all Affymetrix microarray RNA_BATCH labels present in the dataset.
# Used by build_filter_strategies for H_affymetrix_extended.
# Excludes GPL14951_FFPE_Unknown (Illumina HumanHT-12 V3.0, not Affymetrix).
_AFFY_EXT_BATCHES: frozenset[str] = frozenset({
    "GPL570_Unknown_Unknown", "GPL570_FF_Unknown", "GPL570_FFPE_Unknown",
    "GPL96+97_FF_Unknown",    "GPL96_FF_Unknown",  "GPL96_FFPE_Unknown",
    "GPL6244_FF_Unknown",     "GPL6244_FFPE_Unknown",
    "GPL20188_FF_Unknown", 
    "GPL16686_FF_Unknown",    "GPL13158_FF_Unknown",
    "GPL17586_FF_Unknown", "GPL23541_FF_Unknown", 
    "GPL17047_FF_Unknown", "GPL10739_FF_Unknown", "GPL26356_FF_Unknown"

    
})

# ── Data loading ──────────────────────────────────────────────────────────────
def load_data(
    cache_path: str = "/tmp/bench_comb_data.pkl",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load raw expression and annotation from S3.

    Parameters
    ----------
    cache_path
        Path for pickle cache. Populated on first call; subsequent calls load
        from cache (~5 s vs ~90 s from S3). Pass empty string to disable.

    Returns
    -------
    tuple of (comb_exp, comb_ann)
    """
    if cache_path and os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            return pickle.load(f)

    import boto3

    s3 = boto3.client("s3")

    print(f"Downloading expression from s3://{S3_BUCKET}/{S3_EXP_KEY} …", flush=True)
    obj  = s3.get_object(Bucket=S3_BUCKET, Key=S3_EXP_KEY)
    body = obj["Body"].read()
    if S3_EXP_KEY.endswith(".gz"):
        body = gzip.decompress(body)
    comb_exp = pd.read_csv(io.BytesIO(body), sep="\t", index_col=0)
    del body

    print(f"Downloading annotation from s3://{S3_BUCKET}/{S3_ANN_KEY} …", flush=True)
    obj  = s3.get_object(Bucket=S3_BUCKET, Key=S3_ANN_KEY)
    body = obj["Body"].read()
    if S3_ANN_KEY.endswith(".gz"):
        body = gzip.decompress(body)
    comb_ann = pd.read_csv(io.BytesIO(body), index_col=0)
    del body

    comb_ann["Diagnosis_with_coo"] = (
        comb_ann.Diagnosis_cell_type_general + "_" + comb_ann["coo_bg"].fillna("")
    )
    comb_ann["Diagnosis_unified_with_coo"] = (
        comb_ann.Diagnosis_cell_type_unified + "_" + comb_ann["coo_bg"].fillna("")
    )
    comb_ann.loc[comb_ann.index.isin(["PUB_Suntsova_GSE120795"]), "RNA_BATCH"] = (
        "RNASeq_FF_Unknown"
    )

    common   = comb_exp.index.intersection(comb_ann.index)
    comb_exp = comb_exp.loc[common]
    comb_exp = comb_exp.loc[~comb_exp.index.duplicated(keep="first")]
    comb_ann = comb_ann.loc[~comb_ann.index.duplicated(keep="first")]

    result = (comb_exp, comb_ann)
    if cache_path:
        with open(cache_path, "wb") as f:
            pickle.dump(result, f, protocol=4)
    return result


# ── Log transform ─────────────────────────────────────────────────────────────
def log_transform_by_cohort(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    batch_col: str = "COHORT_LABEL",
    threshold: float = 30,
) -> pd.DataFrame:
    """
    Apply log2(x+1) transform per cohort only when max value exceeds threshold.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col column.
    batch_col
        Column used to group samples (COHORT_LABEL, not RNA_BATCH).
    threshold
        Cohorts with max > threshold are log2(x+1) transformed.

    Returns
    -------
    Log2-transformed expression matrix.
    """
    batches = ann_df[batch_col].value_counts().index
    df_list = []
    for batch in batches:
        samples   = ann_df.index[ann_df[batch_col] == batch]
        exp_local = exp_df.reindex(samples)
        if exp_local.max().max() > threshold:
            exp_local = np.log2(exp_local + 1)
        df_list.append(exp_local)
    return pd.concat(df_list, axis=0)


# ── Batch-effect metrics ──────────────────────────────────────────────────────
def pca_variance_explained_by_batch(
    exp_df: pd.DataFrame,
    batch_series: pd.Series,
    n_components: int = 10,
) -> float:
    """
    Mean fraction of PCA variance explained by batch (one-way ANOVA R²).

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    batch_series
        Batch labels indexed by sample ID.
    n_components
        Number of PCs to average over.

    Returns
    -------
    Mean R² across first n_components PCs.
    """
    pca    = PCA(n_components=n_components)
    coords = pca.fit_transform(StandardScaler().fit_transform(exp_df.fillna(0)))
    groups = batch_series.reindex(exp_df.index).fillna("NA")
    r2_list = []
    for pc in range(n_components):
        vals       = coords[:, pc]
        grand_mean = vals.mean()
        ss_between = sum(
            len(vals[groups == g]) * (vals[groups == g].mean() - grand_mean) ** 2
            for g in groups.unique()
            if (groups == g).sum() > 1
        )
        ss_total = ((vals - grand_mean) ** 2).sum()
        r2_list.append(ss_between / ss_total if ss_total > 0 else 0)
    return float(np.mean(r2_list))


def r2_batch(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL,
    n_pcs: int = 10,
) -> float:
    """
    Wrapper around pca_variance_explained_by_batch for a column in ann_df.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation DataFrame with batch_col.
    batch_col
        Column name for grouping.
    n_pcs
        Number of PCs to average over.

    Returns
    -------
    Mean R² across PCs.
    """
    return pca_variance_explained_by_batch(exp_df, ann_df[batch_col], n_pcs)


# ── Filter helpers ────────────────────────────────────────────────────────────
def apply_filter(
    ann: pd.DataFrame,
    bad_batches: list[str] | tuple[str, ...] = (),
    bad_cohorts: list[str] | tuple[str, ...] = (),
    keep_batches: list[str] | None = None,
    keep_groups: list[str] | None = None,
    bio_col: str = BIO_COL,
) -> pd.DataFrame:
    """
    Apply sample-level filters to an annotation DataFrame.

    Parameters
    ----------
    ann
        Annotation DataFrame to filter.
    bad_batches
        RNA_BATCH values to exclude.
    bad_cohorts
        COHORT_LABEL values to exclude.
    keep_batches
        If provided, only samples in these RNA_BATCH values are retained.
    keep_groups
        If provided, only samples in these bio_col groups are retained.
    bio_col
        Column for group filtering.

    Returns
    -------
    Filtered annotation DataFrame.
    """
    mask = pd.Series(True, index=ann.index)
    if bad_batches:
        mask &= ~ann[BATCH_COL].isin(bad_batches)
    if bad_cohorts:
        mask &= ~ann["COHORT_LABEL"].isin(bad_cohorts)
    if keep_batches is not None:
        mask &= ann[BATCH_COL].isin(keep_batches)
    if keep_groups is not None:
        mask &= ann[bio_col].isin(keep_groups)
    return ann[mask]


def identify_outlier_batches(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL,
    n_pcs: int = 2,
    n_outliers: int = 1,
    min_batch_size: int = 20,
) -> list[str]:
    """
    Identify the batches whose PCA centroid is furthest from the global centroid.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.
    n_pcs
        Number of PCs for centroid calculation.
    n_outliers
        Number of outlier batches to return.
    min_batch_size
        Batches smaller than this are excluded from outlier detection.

    Returns
    -------
    List of outlier batch names, length <= n_outliers.
    """
    common    = exp_df.index.intersection(ann_df.index)
    X         = StandardScaler().fit_transform(exp_df.loc[common].fillna(0))
    coords    = PCA(n_components=n_pcs).fit_transform(X)
    coords_df = pd.DataFrame(coords, index=common)
    batches   = ann_df.loc[common, batch_col].fillna("NA")
    global_centroid = coords_df.mean(axis=0).values

    batch_centroids: dict[str, float] = {}
    for b in batches.unique():
        idx = batches[batches == b].index
        if len(idx) < min_batch_size:
            continue
        batch_centroids[b] = float(
            np.linalg.norm(coords_df.loc[idx].mean(axis=0).values - global_centroid)
        )

    ranked = sorted(batch_centroids, key=batch_centroids.get, reverse=True)  # type: ignore[arg-type]
    return ranked[:n_outliers]


def prepare_dataset(
    ann_filter: pd.DataFrame,
    exp_full: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Align expression to annotation with strict full-coverage (no NAs).

    Parameters
    ----------
    ann_filter
        Filtered annotation DataFrame.
    exp_full
        Full expression matrix (samples × genes).

    Returns
    -------
    Tuple of (exp, ann) with NA-free expression.
    """
    common = ann_filter.index.intersection(exp_full.index)
    exp    = exp_full.loc[common].dropna(axis=1)
    exp    = exp.loc[~exp.index.duplicated(keep="first")]
    ann    = ann_filter.loc[exp.index]
    return exp, ann


def prepare_dataset_imputed(
    ann_filter: pd.DataFrame,
    exp_full: pd.DataFrame,
    method: str = "knn",
    knn_k: int = 5,
    max_na_frac: float = 0.20,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Align expression to annotation with NA imputation.

    Parameters
    ----------
    ann_filter
        Filtered annotation DataFrame.
    exp_full
        Full expression matrix (samples × genes).
    method
        Imputation method: 'knn', 'missforest', or 'softimpute'.
    knn_k
        Number of neighbours for KNN imputation.
    max_na_frac
        Genes with more NAs than this fraction are dropped before imputation.

    Returns
    -------
    Tuple of (exp, ann) with imputed expression.
    """
    from sklearn.impute import KNNImputer

    common  = ann_filter.index.intersection(exp_full.index)
    exp     = exp_full.loc[common]
    na_frac = exp.isna().mean(axis=0)
    exp     = exp.loc[:, na_frac <= max_na_frac]
    exp     = exp.loc[~exp.index.duplicated(keep="first")]
    ann     = ann_filter.loc[exp.index]

    if not exp.isna().any(axis=None):
        return exp, ann

    if method == "knn":
        imp    = KNNImputer(n_neighbors=knn_k)
        values = imp.fit_transform(exp.values)
        exp    = pd.DataFrame(values, index=exp.index, columns=exp.columns)
    elif method == "missforest":
        missforest_r = importr("missForest")
        r_mat        = _py2rpy(exp)
        result       = missforest_r.missForest(r_mat)
        imp_np       = _rpy2py(result.rx2("ximp"))
        exp          = pd.DataFrame(imp_np, index=exp.index, columns=exp.columns)
    elif method == "softimpute":
        softimpute_r = importr("softImpute")
        base_r       = importr("base")
        r_mat        = base_r.as_matrix(_py2rpy(exp))
        si_obj       = softimpute_r.softImpute(r_mat, type="svd")
        imp_mat      = softimpute_r.complete(r_mat, si_obj)
        imp_np       = imp_mat if isinstance(imp_mat, np.ndarray) else _rpy2py(imp_mat)
        exp          = pd.DataFrame(imp_np, index=exp.index, columns=exp.columns)
    else:
        raise ValueError(f"Unknown imputation method: {method}")

    return exp, ann


def build_filter_strategies(
    comb_ann: pd.DataFrame,
    comb_exp: pd.DataFrame,
    cache_path: str = "/tmp/bench_filter_strategies.pkl",
) -> dict[str, pd.DataFrame]:
    """
    Build all 14 filter strategies from annotation and expression data.

    E1–E3 require iterative PCA-based outlier detection and take extra time.
    Results are cached to cache_path so parallel workers reuse them.

    Parameters
    ----------
    comb_ann
        Full annotation DataFrame.
    comb_exp
        Full expression matrix.
    cache_path
        Pickle cache path. Pass empty string to disable caching.

    Returns
    -------
    Dict mapping strategy name → filtered annotation DataFrame (14 entries).
    """
    if cache_path and os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            return pickle.load(f)

    ann_base = comb_ann[~comb_ann[BIO_COL].isin(RARE_GROUPS)].copy()

    rnaseq_batches     = [b for b in ann_base[BATCH_COL].unique() if b.startswith("RNASeq")]
    microarray_batches = [b for b in ann_base[BATCH_COL].unique() if not b.startswith("RNASeq")]
    affymetrix_batches = [b for b in ann_base[BATCH_COL].unique() if b.startswith("GPL570")]
    ff_batches         = [b for b in ann_base[BATCH_COL].unique() if "_FF_" in b]
    ffpe_batches       = [b for b in ann_base[BATCH_COL].unique() if "_FFPE_" in b]
    malignant_groups   = [g for g in ann_base[BIO_COL].unique() if g not in NORMAL_GROUPS]

    def _f(**kw: object) -> pd.DataFrame:
        return apply_filter(ann_base, **kw)  # type: ignore[arg-type]

    ann_S0 = ann_base.copy()
    ann_A  = _f(bad_batches=BAD_BATCHES_A, bad_cohorts=BAD_COHORTS_A)
    ann_B  = _f(bad_batches=BAD_BATCHES_B, bad_cohorts=BAD_COHORTS_B)
    ann_C  = _f(keep_batches=rnaseq_batches)
    ann_D  = _f(keep_groups=malignant_groups)
    ann_F  = _f(keep_batches=microarray_batches)
    ann_G  = _f(keep_batches=affymetrix_batches)

    _batch_counts  = ann_base[BATCH_COL].value_counts()
    _large_batches = _batch_counts[_batch_counts >= MIN_BATCH_SIZE].index.tolist()
    ann_I          = _f(keep_batches=_large_batches)
    ann_J          = _f(keep_batches=ff_batches)
    ann_K          = _f(keep_batches=ffpe_batches)

    exp_A, _ = prepare_dataset(ann_A, comb_exp)
    exp_A    = log_transform_by_cohort(exp_A, ann_A.loc[exp_A.index])
    out_E1   = identify_outlier_batches(exp_A, ann_A)
    ann_E1   = _f(bad_batches=BAD_BATCHES_A + out_E1, bad_cohorts=BAD_COHORTS_A)

    exp_E1, _ = prepare_dataset(ann_E1, comb_exp)
    exp_E1    = log_transform_by_cohort(exp_E1, ann_E1.loc[exp_E1.index])
    out_E2    = identify_outlier_batches(exp_E1, ann_E1)
    ann_E2    = apply_filter(ann_E1, bad_batches=out_E2)

    exp_E2, _ = prepare_dataset(ann_E2, comb_exp)
    exp_E2    = log_transform_by_cohort(exp_E2, ann_E2.loc[exp_E2.index])
    out_E3    = identify_outlier_batches(exp_E2, ann_E2)
    ann_E3    = apply_filter(ann_E2, bad_batches=out_E3)

    strategies = {
        "S0_no_removal":     ann_S0,
        "A_confirmed_bad":   ann_A,
        "B_extended_bad":    ann_B,
        "C_rnaseq_only":     ann_C,
        "D_malignant_only":  ann_D,
        "E1_iterative_r1":   ann_E1,
        "E2_iterative_r2":   ann_E2,
        "E3_iterative_r3":   ann_E3,
        "F_microarray_only":     ann_F,
        "G_affymetrix_only":     ann_G,
        "H_affymetrix_extended": ann_base[
            ann_base[BATCH_COL].isin(_AFFY_EXT_BATCHES)
        ].copy(),
        "I_rare_batches_removed": ann_I,
        "J_ff_only":              ann_J,
        "K_ffpe_only":            ann_K,
    }

    if cache_path:
        with open(cache_path, "wb") as f:
            pickle.dump(strategies, f, protocol=4)

    return strategies


# ── S3 helpers ────────────────────────────────────────────────────────────────
def s3_key_exp(strat: str, imp: str, method: str, post_rm: bool) -> str:
    pr = "post1" if post_rm else "post0"
    return f"{S3_PREFIX}/exp/{strat}__{imp}__{method}__{pr}.tsv.gz"


def s3_key_metrics() -> str:
    return f"{S3_PREFIX}/metrics.csv"


def s3_key_prepared_exp(strat: str, imp: str) -> str:
    return f"{S3_PREFIX}/prepared/{strat}__{imp}__exp.tsv.gz"


def s3_key_prepared_ann(strat: str, imp: str) -> str:
    return f"{S3_PREFIX}/prepared/{strat}__{imp}__ann.tsv.gz"


def s3_key_prep_metrics() -> str:
    return f"{S3_PREFIX}/prep_metrics.csv"


def upload_ann_to_s3(ann_df: pd.DataFrame, s3_client: object, key: str) -> None:
    """Upload annotation DataFrame as gzip-compressed TSV to S3."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        ann_df.to_csv(gz, sep="\t")
    buf.seek(0)
    s3_client.upload_fileobj(buf, S3_BUCKET, key)  # type: ignore[union-attr]


def download_ann_from_s3(s3_client: object, key: str) -> pd.DataFrame:
    """Download gzip-compressed TSV annotation DataFrame from S3."""
    buf = io.BytesIO()
    s3_client.download_fileobj(S3_BUCKET, key, buf)  # type: ignore[union-attr]
    buf.seek(0)
    with gzip.open(buf, "rb") as gz:
        return pd.read_csv(gz, sep="\t", index_col=0)


def s3_exists(s3_client: object, key: str) -> bool:
    """Check if an S3 key exists without downloading it."""
    import botocore.exceptions

    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=key)  # type: ignore[union-attr]
        return True
    except botocore.exceptions.ClientError:
        return False


def upload_exp_to_s3(exp_df: pd.DataFrame, s3_client: object, key: str) -> None:
    """Upload expression DataFrame as gzip-compressed TSV to S3."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        exp_df.to_csv(gz, sep="\t")
    buf.seek(0)
    s3_client.upload_fileobj(buf, S3_BUCKET, key)  # type: ignore[union-attr]


def download_exp_from_s3(s3_client: object, key: str) -> pd.DataFrame:
    """Download gzip-compressed TSV expression DataFrame from S3."""
    buf = io.BytesIO()
    s3_client.download_fileobj(S3_BUCKET, key, buf)  # type: ignore[union-attr]
    buf.seek(0)
    with gzip.open(buf, "rb") as gz:
        return pd.read_csv(gz, sep="\t", index_col=0)


# ══════════════════════════════════════════════════════════════════════════════
# NORMALIZATION FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

# ── Low harshness ─────────────────────────────────────────────────────────────

def normalize_raw(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame | None = None, **kw: object
) -> pd.DataFrame:
    """Passthrough — no normalization. Absolute baseline."""
    return exp_df.copy()


def normalize_median_scaling(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, **kw: object,
) -> pd.DataFrame:
    """
    Per-batch median centering: shift batch median to global median.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.

    Returns
    -------
    Median-scaled expression matrix.
    """
    groups        = ann_df.loc[exp_df.index, batch_col].fillna("Unknown")
    out           = exp_df.copy()
    global_median = exp_df.median(axis=0)
    for g in groups.unique():
        idx          = exp_df.index[groups == g]
        batch_median = exp_df.loc[idx].median(axis=0)
        shift        = global_median - batch_median
        out.loc[idx] = exp_df.loc[idx].add(shift, axis=1)
    return out


def normalize_limma(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, **kw: object,
) -> pd.DataFrame:
    """
    limma::removeBatchEffect (Ritchie et al. 2015).

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.

    Returns
    -------
    Batch-corrected expression matrix.
    """
    limma_r = importr("limma")
    base_r  = importr("base")
    batches   = ann_df.loc[exp_df.index, batch_col].astype(str).values
    r_mat     = base_r.as_matrix(_py2rpy(exp_df.T))
    result    = limma_r.removeBatchEffect(r_mat, batch=ro.StrVector(batches))
    result_np = result if isinstance(result, np.ndarray) else _rpy2py(result)
    out = pd.DataFrame(result_np.T, index=exp_df.index, columns=exp_df.columns)
    _r_gc()
    return out


def normalize_sva(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    bio_col: str = BIO_COL, **kw: object,
) -> pd.DataFrame:
    """
    Surrogate Variable Analysis (Leek & Storey 2012).

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with bio_col.
    bio_col
        Column for biological group (used to protect biology in model).

    Returns
    -------
    SVA-corrected expression matrix, or uncorrected if SVA fails.
    """
    from rpy2.rinterface_lib.embedded import RRuntimeError

    sva_r   = importr("sva")
    limma_r = importr("limma")
    base_r  = importr("base")
    bio      = ann_df.loc[exp_df.index, bio_col].fillna("Unknown").astype(str).values
    r_bio    = ro.StrVector(bio)
    df_r     = ro.DataFrame({"r_bio": r_bio})
    n_levels = len(set(bio))
    if n_levels >= 2:
        mod = ro.r["model.matrix"](ro.Formula("~r_bio"), data=df_r)
    else:
        print(f"SVA: only {n_levels} unique level(s) in {bio_col} — using intercept-only model")
        mod = ro.r["model.matrix"](ro.Formula("~1"), data=df_r)
    mod0   = ro.r["model.matrix"](ro.Formula("~1"), data=df_r)
    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
    if exp_in.shape[1] < exp_df.shape[1]:
        print(f"SVA: dropping {exp_df.shape[1] - exp_in.shape[1]} genes with residual NaN")
    r_mat  = base_r.as_matrix(_py2rpy(exp_in.T))
    n_sv   = sva_r.num_sv(r_mat, mod)
    if int(n_sv[0]) == 0:
        print("SVA: 0 surrogate variables detected — returning uncorrected data")
        return exp_df.copy()
    try:
        sv_obj = sva_r.sva(r_mat, mod, mod0, n_sv=n_sv)
    except RRuntimeError as e:
        print(f"SVA: sva() failed ({e}) — returning uncorrected data")
        return exp_df.copy()
    _svs = sv_obj.rx2("sv")
    svs  = _svs if isinstance(_svs, np.ndarray) else _rpy2py(_svs)
    if svs.ndim == 1:
        svs = svs.reshape(-1, 1)
    elif svs.ndim == 2 and svs.shape[0] != len(exp_df) and svs.shape[1] == len(exp_df):
        print(f"SVA: transposing svs from {svs.shape} to {svs.T.shape}")
        svs = svs.T
    try:
        result = limma_r.removeBatchEffect(
            r_mat,
            covariates=base_r.as_matrix(_py2rpy(pd.DataFrame(svs, index=exp_df.index))),
        )
    except RRuntimeError as e:
        print(f"SVA: removeBatchEffect failed ({e}) — returning uncorrected data")
        return exp_df.copy()
    result_np = result if isinstance(result, np.ndarray) else _rpy2py(result)
    out = pd.DataFrame(result_np.T, index=exp_df.index, columns=exp_in.columns)
    _r_gc()
    return out


# ── Medium harshness ──────────────────────────────────────────────────────────

def normalize_combat(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, bio_col: str = BIO_COL, **kw: object,
) -> pd.DataFrame:
    """
    ComBat Empirical Bayes batch correction (Johnson et al. 2007).

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col and bio_col.
    batch_col
        Column for batch grouping.
    bio_col
        Column for biological group covariate.

    Returns
    -------
    ComBat-corrected expression matrix.
    """
    sva_r  = importr("sva")
    base_r = importr("base")
    batches  = ann_df.loc[exp_df.index, batch_col].astype(str).values
    bio      = ann_df.loc[exp_df.index, bio_col].fillna("Unknown").astype(str).values
    r_mat    = base_r.as_matrix(_py2rpy(exp_df.T))
    n_levels = len(set(bio))
    if n_levels >= 2:
        r_bio = ro.StrVector(bio)
        mod   = ro.r["model.matrix"](ro.Formula("~r_bio"),
                                     data=ro.DataFrame({"r_bio": r_bio}))
    else:
        print(f"ComBat: only {n_levels} unique level(s) in {bio_col} — running without covariate")
        mod = ro.rinterface.NULL
    result    = sva_r.ComBat(dat=r_mat, batch=ro.StrVector(batches), mod=mod)
    result_np = result if isinstance(result, np.ndarray) else _rpy2py(result)
    out = pd.DataFrame(result_np.T, index=exp_df.index, columns=exp_df.columns)
    _r_gc()
    return out


def normalize_combat_seq(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, bio_col: str = BIO_COL, **kw: object,
) -> pd.DataFrame:
    """
    ComBat-seq (Zhang et al. 2020). Rounds values to integer counts.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col and bio_col.
    batch_col
        Column for batch grouping.
    bio_col
        Column for biological group.

    Returns
    -------
    ComBat-seq-corrected expression matrix.
    """
    sva_r  = importr("sva")
    base_r = importr("base")
    batches  = ann_df.loc[exp_df.index, batch_col].astype(str).values
    bio      = ann_df.loc[exp_df.index, bio_col].fillna("Unknown").astype(str).values
    counts   = np.round(exp_df.values).astype(int).clip(0)
    r_mat    = base_r.as_matrix(_py2rpy(
                   pd.DataFrame(counts.T, index=exp_df.columns, columns=exp_df.index)))
    n_levels = len(set(bio))
    if n_levels >= 2:
        group_arg = ro.StrVector(bio)
    else:
        print(f"ComBat-seq: only {n_levels} unique level(s) in {bio_col} — running without group")
        group_arg = ro.rinterface.NULL
    result    = sva_r.ComBat_seq(counts=r_mat, batch=ro.StrVector(batches), group=group_arg)
    result_np = result if isinstance(result, np.ndarray) else _rpy2py(result)
    out = pd.DataFrame(result_np.T, index=exp_df.index, columns=exp_df.columns)
    _r_gc()
    return out


def normalize_pycombat(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, **kw: object,
) -> pd.DataFrame:
    """
    pyComBat: Python port of ComBat (Müller et al. 2023).

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.

    Returns
    -------
    pyComBat-corrected expression matrix.
    """
    from combat.pycombat import pycombat

    batches = ann_df.loc[exp_df.index, batch_col].fillna("Unknown").tolist()
    exp_in  = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
    result  = pycombat(exp_in.T, batches)
    return result.T


def normalize_inmoose_combat_seq(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, bio_col: str = BIO_COL, **kw: object,
) -> pd.DataFrame:
    """
    pycombat_seq via InMoose (Colom-Díaz et al. 2025).

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col and bio_col.
    batch_col
        Column for batch grouping.
    bio_col
        Column for biological group covariate.

    Returns
    -------
    InMoose ComBat-seq-corrected expression matrix.
    """
    from inmoose.pycombat import pycombat_seq

    batches      = ann_df.loc[exp_df.index, batch_col].fillna("Unknown").tolist()
    bio          = ann_df.loc[exp_df.index, bio_col].fillna("Unknown").astype(str)
    clean_values = np.nan_to_num(exp_df.values, nan=0.0, posinf=0.0, neginf=0.0)
    counts       = np.round(clean_values).astype(int).clip(0)
    n_levels = bio.nunique()
    if n_levels >= 2:
        covar_mod = pd.get_dummies(bio, drop_first=True).astype(float).values
    else:
        covar_mod = None
    result = pycombat_seq(counts.T, batch=batches, covar_mod=covar_mod)
    return pd.DataFrame(result.T, index=exp_df.index, columns=exp_df.columns)


def normalize_ruv(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame, k: int = 2, **kw: object,
) -> pd.DataFrame:
    """
    RUVg (Risso et al. 2014). Uses housekeeping genes as negative controls.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation (unused; kept for API consistency).
    k
        Number of factors of unwanted variation to remove.

    Returns
    -------
    RUV-corrected expression matrix, or uncorrected if <3 control genes found.
    """
    ruvseq_r = importr("RUVSeq")
    base_r   = importr("base")
    HOUSEKEEPING = [
        "ACTB", "GAPDH", "B2M", "HPRT1", "RPL13A",
        "SDHA", "UBC", "YWHAZ", "HMBS", "TBP",
    ]
    ctrl_genes = [g for g in HOUSEKEEPING if g in exp_df.columns]
    if len(ctrl_genes) < 3:
        print(f"RUV: only {len(ctrl_genes)} control genes found — skipping")
        return exp_df.copy()
    counts   = np.round(exp_df.values).astype(int).clip(0)
    r_counts = base_r.as_matrix(_py2rpy(
                   pd.DataFrame(counts.T, index=exp_df.columns, columns=exp_df.index)))
    ctrl_idx    = ro.IntVector([list(exp_df.columns).index(g) + 1 for g in ctrl_genes])
    ruv_obj     = ruvseq_r.RUVg(r_counts, cIdx=ctrl_idx, k=k)
    norm_counts = _rpy2py(ruv_obj.rx2("normalizedCounts"))
    out = pd.DataFrame(norm_counts.T, index=exp_df.index, columns=exp_df.columns)
    _r_gc()
    return out


def normalize_mnn(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, k: int = 20, **kw: object,
) -> pd.DataFrame:
    """
    fastMNN (Haghverdi et al. 2018). Corrected embedding inverse-projected to expression space.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.
    k
        Number of mutual nearest neighbours.

    Returns
    -------
    MNN-corrected expression matrix.
    """
    batchelor_r = importr("batchelor")
    base_r      = importr("base")
    batches = ann_df.loc[exp_df.index, batch_col].astype(str)
    exp_in  = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
    exp_in  = exp_in.clip(lower=0.0)
    r_mat   = base_r.as_matrix(_py2rpy(exp_in.T))
    result  = batchelor_r.fastMNN(r_mat, batch=ro.StrVector(batches.values), k=k)
    _mat    = ro.r["as.matrix"](ro.r["reducedDim"](result, "corrected"))
    corrected_embed = _mat if isinstance(_mat, np.ndarray) else _rpy2py(_mat)
    pca       = PCA(n_components=corrected_embed.shape[1]).fit(exp_in.values)
    recovered = corrected_embed @ pca.components_ + pca.mean_
    out = pd.DataFrame(recovered, index=exp_df.index, columns=exp_in.columns)
    _r_gc()
    return out


def normalize_harmony(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, n_pcs: int = 50, **kw: object,
) -> pd.DataFrame:
    """
    Harmony (Korsunsky et al. 2019). PCA-space correction, inverse-projected back.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.
    n_pcs
        Number of PCs for Harmony correction.

    Returns
    -------
    Harmony-corrected expression matrix.
    """
    import harmonypy as hm

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(exp_df.fillna(0).values)
    pca      = PCA(n_components=min(n_pcs, exp_df.shape[1] - 1))
    coords   = pca.fit_transform(X_scaled)
    meta     = ann_df.loc[exp_df.index, [batch_col]].fillna("Unknown")
    harmony  = hm.run_harmony(coords, meta, vars_use=batch_col, max_iter_harmony=20)
    # harmonypy ≥ 0.0.9 returns Z_corr as (n_cells, n_pcs); older returned (n_pcs, n_cells)
    Z = harmony.Z_corr
    if Z.shape[0] != coords.shape[0]:
        Z = Z.T
    recovered = pca.inverse_transform(Z)
    recovered = scaler.inverse_transform(recovered)
    return pd.DataFrame(recovered, index=exp_df.index, columns=exp_df.columns)


def normalize_scanorama(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, **kw: object,
) -> pd.DataFrame:
    """
    Scanorama (Hie et al. 2019). Panoramic stitching via randomised SVD MNN.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.

    Returns
    -------
    Scanorama-corrected expression matrix.
    """
    import scanorama

    batches    = ann_df.loc[exp_df.index, batch_col].fillna("Unknown")
    exp_in     = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
    datasets_s = [exp_in.loc[batches == b].values for b in batches.unique()]
    genes_list = [list(exp_in.columns)] * len(datasets_s)
    integrated, _ = scanorama.integrate(datasets_s, genes_list, dimred=50)
    all_coords    = np.zeros((len(exp_df), integrated[0].shape[1]))
    for b_idx, b in enumerate(batches.unique()):
        all_coords[(batches == b).values] = integrated[b_idx]
    pca       = PCA(n_components=integrated[0].shape[1]).fit(exp_in.values)
    recovered = all_coords @ pca.components_ + pca.mean_
    return pd.DataFrame(recovered, index=exp_df.index, columns=exp_in.columns)


def normalize_fsmvn(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, target_group: str = "RNASeq_FF_PolyA", **kw: object,
) -> pd.DataFrame:
    """
    Feature-Specific Mean-Variance Normalization — negative control.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.
    target_group
        Reference batch whose mean/variance is the target.

    Returns
    -------
    FSMVN-corrected expression matrix.
    """
    groups = ann_df.loc[exp_df.index, batch_col]
    ref    = exp_df.loc[groups == target_group] if target_group in groups.values else exp_df
    t_mean = ref.mean(axis=0)
    t_std  = ref.std(axis=0).replace(0, 1)
    out    = exp_df.copy()
    for g in groups.unique():
        idx   = exp_df.index[groups == g]
        grp   = exp_df.loc[idx]
        g_std = grp.std(axis=0).replace(0, 1)
        out.loc[idx] = (grp - grp.mean(axis=0)) / g_std * t_std + t_mean
    return out


# ── High harshness ────────────────────────────────────────────────────────────

def normalize_qsmooth(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, **kw: object,
) -> pd.DataFrame:
    """
    Smooth quantile normalization (Hicks et al. 2018).

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.

    Returns
    -------
    qsmooth-normalized expression matrix.
    """
    qsmooth_r = importr("qsmooth")
    base_r    = importr("base")
    groups = ann_df.loc[exp_df.index, batch_col].astype(str).values
    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
    r_mat  = base_r.as_matrix(_py2rpy(exp_in.T))
    qs_obj = qsmooth_r.qsmooth(r_mat, group_factor=ro.StrVector(groups))
    _raw   = qsmooth_r.qsmoothData(qs_obj)
    result = _raw if isinstance(_raw, np.ndarray) else _rpy2py(_raw)
    out = pd.DataFrame(result.T, index=exp_df.index, columns=exp_in.columns)
    _r_gc()
    return out


def normalize_fsqn_py(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, target_group: str = "RNASeq_FF_PolyA", **kw: object,
) -> pd.DataFrame:
    """
    FSQN Python implementation (Franks et al. 2018).

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.
    target_group
        Reference batch whose per-gene distribution is the target.

    Returns
    -------
    FSQN-normalized expression matrix.
    """
    groups      = ann_df.loc[exp_df.index, batch_col]
    out         = exp_df.copy()
    target_dist = (
        np.sort(exp_df.loc[groups == target_group].values, axis=1).mean(axis=0)
        if target_group in groups.values
        else np.sort(exp_df.values, axis=1).mean(axis=0)
    )
    for g in groups.unique():
        idx = exp_df.index[groups == g]
        for sample in idx:
            vals  = exp_df.loc[sample].values
            order = np.argsort(vals)
            out.loc[sample, out.columns[order]] = target_dist
    return out


def normalize_fsqn_r(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, target_group: str = "RNASeq_FF_PolyA", **kw: object,
) -> pd.DataFrame:
    """
    FSQN via original R package (Franks et al. 2018). ★ Prior best: ~16% residual batch R².

    Each non-reference batch is normalised independently against the reference
    batch (SAMPLES × GENES orientation, which is what FSQN expects).
    The reference batch samples are kept unchanged.

    If the reference batch is absent from the strategy's data (e.g. microarray-only
    strategies), all samples are used as both query and reference, which degenerates
    to standard quantile normalisation per gene.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.
    target_group
        Reference batch (RNASeq_FF_PolyA).

    Returns
    -------
    FSQN R-normalised expression matrix (samples × genes).
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
    groups = ann_df.loc[exp_in.index, batch_col].astype(str)

    if target_group not in groups.values:
        with tempfile.TemporaryDirectory() as td:
            ref_path   = os.path.join(td, "ref.csv")
            query_path = os.path.join(td, "query.csv")
            out_path   = os.path.join(td, "out.csv")
            exp_in.to_csv(ref_path)
            exp_in.to_csv(query_path)
            ro.r(f"""
                library(FSQN)
                ref   <- as.matrix(read.csv("{ref_path}",   row.names=1, check.names=FALSE))
                query <- as.matrix(read.csv("{query_path}", row.names=1, check.names=FALSE))
                out   <- quantileNormalizeByFeature(query, ref)
                if (is.null(out)) stop("quantileNormalizeByFeature returned NULL (fallback path)")
                write.csv(out, "{out_path}", row.names=TRUE)
            """)
            if not os.path.exists(out_path):
                raise RuntimeError("FSQN R: no output file (fallback path)")
            result = pd.read_csv(out_path, index_col=0)
        if result.shape[1] == 0:
            raise RuntimeError(
                f"FSQN R: 0 genes in fallback output (shape {result.shape})"
            )
        _r_gc()
        return result.reindex(exp_df.index)

    ref_exp         = exp_in.loc[groups == target_group]
    non_ref_batches = [b for b in groups.unique() if b != target_group]

    with tempfile.TemporaryDirectory() as td:
        ref_path = os.path.join(td, "ref.csv")
        ref_exp.to_csv(ref_path)

        batch_io: list[tuple[str, str]] = []
        for i, batch in enumerate(non_ref_batches):
            qp = os.path.join(td, f"query_{i:04d}.csv")
            op = os.path.join(td, f"out_{i:04d}.csv")
            exp_in.loc[groups == batch].to_csv(qp)
            batch_io.append((qp, op))

        # Build R script with explicit paths per batch — avoids list.files discovery
        batch_r_blocks = "\n".join(
            f"""
            query <- as.matrix(read.csv("{qp}", row.names=1, check.names=FALSE))
            if (ncol(query) != n_ref_genes) stop(paste0(
                "FSQN gene count mismatch: ncol(query)=", ncol(query),
                " n_ref_genes=", n_ref_genes))
            out <- quantileNormalizeByFeature(query, ref)
            if (is.null(out)) stop("quantileNormalizeByFeature returned NULL")
            write.csv(out, "{op}", row.names=TRUE)
            """
            for qp, op in batch_io
        )
        ro.r(f"""
            library(FSQN)
            ref         <- as.matrix(read.csv("{ref_path}", row.names=1, check.names=FALSE))
            n_ref_genes <- ncol(ref)
            {batch_r_blocks}
        """)

        parts: list[pd.DataFrame] = [ref_exp]
        for i, batch in enumerate(non_ref_batches):
            out_path = os.path.join(td, f"out_{i:04d}.csv")
            if not os.path.exists(out_path):
                raise RuntimeError(f"FSQN R: no output file for batch {batch!r}")
            batch_result = pd.read_csv(out_path, index_col=0)
            if batch_result.shape[1] == 0:
                raise RuntimeError(
                    f"FSQN R: 0 genes in output for batch {batch!r} "
                    f"(shape {batch_result.shape})"
                )
            parts.append(batch_result)

    _r_gc()
    return pd.concat(parts).reindex(exp_df.index)


def normalize_quantile(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame | None = None, **kw: object,
) -> pd.DataFrame:
    """
    Standard quantile normalization (Bolstad et al. 2003).

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).

    Returns
    -------
    Quantile-normalized expression matrix.
    """
    X      = exp_df.values.copy().astype(float)
    rank   = np.argsort(np.argsort(X, axis=1), axis=1)
    target = np.sort(X, axis=1).mean(axis=0)
    return pd.DataFrame(target[rank], index=exp_df.index, columns=exp_df.columns)


def normalize_rank(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame | None = None, **kw: object,
) -> pd.DataFrame:
    """
    Rank-transforms each sample to 0–1 fractional ranks.

    Used internally by the internal B-cell classifiers for platform independence.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).

    Returns
    -------
    Rank-normalized expression matrix.
    """
    ranked = exp_df.rank(axis=1, method="average", na_option="keep")
    return ranked / (exp_df.notna().sum(axis=1).values[:, None] + 1)


def _angel_platform_variance(
    exp_df: pd.DataFrame,
    batch_series: pd.Series,
) -> pd.Series:
    """
    Per-gene platform variance fraction (one-way ANOVA R²).

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    batch_series
        Platform / batch labels indexed by sample ID.

    Returns
    -------
    pd.Series indexed by gene name, values in [0, 1].
    """
    groups = batch_series.reindex(exp_df.index)
    X = exp_df.values.astype(float)
    unique_groups = groups.unique()

    grand_mean = np.nanmean(X, axis=0)
    ss_total = np.nansum((X - grand_mean) ** 2, axis=0)

    ss_between = np.zeros(X.shape[1], dtype=float)
    for g in unique_groups:
        mask = (groups == g).values
        if mask.sum() < 2:
            continue
        group_vals = X[mask, :]
        group_mean = np.nanmean(group_vals, axis=0)
        n_g = np.sum(~np.isnan(group_vals), axis=0).astype(float)
        ss_between += n_g * (group_mean - grand_mean) ** 2

    r2 = np.where(ss_total > 0, ss_between / ss_total, 0.0)
    return pd.Series(r2, index=exp_df.columns)


def normalize_angel(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL,
    threshold: float = 0.20,
    **kw: object,
) -> pd.DataFrame:
    """
    Angel rank-percentile normalization with platform-variance gene filtering.

    Rank-transforms each sample to [0,1], then discards genes where platform
    membership explains ≥ threshold of total variance (per-gene ANOVA R²).
    Output has fewer genes than input — the PCA R² metric is not directly
    comparable with other methods because platform-biased genes are removed
    rather than corrected.

    Reference: Angel PW et al., PLOS Comput Biol 16(9), e1008219 (2020).

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes), log2-transformed.
    ann_df
        Sample annotation; must contain batch_col indexed by sample ID.
    batch_col
        Column in ann_df identifying platform / batch groups.
    threshold
        Maximum per-gene platform variance fraction to retain a gene.
        Default 0.20 (paper default). Range: 0.05 (strict) to 0.50 (lenient).

    Returns
    -------
    Rank-normalized expression matrix restricted to platform-stable genes.
    Shape: (n_samples, n_genes_retained) where n_genes_retained ≤ n_genes_input.
    """
    exp_in    = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
    ranked    = exp_in.rank(axis=1, method="average", na_option="keep")
    rank_norm = ranked / (exp_in.notna().sum(axis=1).values[:, None] + 1)

    batch_series = ann_df.loc[exp_in.index, batch_col].astype(str)
    gene_r2 = _angel_platform_variance(rank_norm, batch_series)
    stable_genes = gene_r2[gene_r2 < threshold].index

    if len(stable_genes) == 0:
        raise RuntimeError(
            f"normalize_angel: no genes passed platform-variance filter "
            f"(threshold={threshold}). All {len(exp_in.columns)} genes had "
            f"platform R² ≥ {threshold}. Try raising the threshold."
        )

    return rank_norm[stable_genes]


# ── Cross-platform focused ────────────────────────────────────────────────────

def normalize_tdm(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, target_group: str = "RNASeq_FF_PolyA", **kw: object,
) -> pd.DataFrame:
    """
    Training Distribution Matching (Thompson et al. 2016).

    Uses file-based interface because TDM requires a data.table with a gene column.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.
    target_group
        Reference batch whose distribution is the training target.

    Returns
    -------
    TDM-normalized expression matrix.
    """
    import tempfile

    groups      = ann_df.loc[exp_df.index, batch_col].astype(str)
    exp_in      = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
    target_mask = (
        groups == target_group
        if target_group in groups.values
        else pd.Series(True, index=exp_in.index)
    )
    with tempfile.TemporaryDirectory() as td:
        ref_path   = os.path.join(td, "ref.tsv")
        query_path = os.path.join(td, "query.tsv")
        out_path   = os.path.join(td, "out.tsv")
        ref_dt              = exp_in.loc[target_mask].T.copy()
        ref_dt.index.name   = "gene"
        ref_dt.reset_index().to_csv(ref_path, sep="\t", index=False)
        query_dt            = exp_in.T.copy()
        query_dt.index.name = "gene"
        query_dt.reset_index().to_csv(query_path, sep="\t", index=False)
        ro.r(f"""
            library(TDM)
            result <- tdm_transform(file=\"{query_path}\", ref_file=\"{ref_path}\", log_target=FALSE)
            write.table(result, \"{out_path}\", sep="\\t", row.names=FALSE, quote=FALSE)
        """)
        if not os.path.exists(out_path):
            raise RuntimeError("TDM produced no output — check R console for errors")
        result_df = pd.read_csv(out_path, sep="\t")
    gene_col  = result_df.columns[0]
    result_df = result_df.drop(columns=[gene_col])
    result_np = result_df.values.T.astype(float)
    _r_gc()
    return pd.DataFrame(result_np, index=exp_df.index, columns=exp_in.columns)


def normalize_shambhala(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, target_group: str = "RNASeq_FF_PolyA", **kw: object,
) -> pd.DataFrame:
    """
    Shambhala2 (Borisov 2022). Cross-platform harmonization: CuBlock + quantile norm.

    Uses file-based interface via the BorisovNM/Shambhala2 R package, which
    internally calls Octave (or MATLAB) via system(). Requires:
      - GNU Octave installed and a 'matlab' wrapper on PATH
      - R package Shambhala2 (remotes::install_github("BorisovNM/Shambhala2"))
      - R package matrixStats

    Input format: genes × samples CSV, SYMBOL as first column.
    P and Q calibration references both use the target_group batch
    (RNASeq_FF_PolyA by default) — same single-reference strategy as FSQN/TDM.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.
    target_group
        Reference batch for both calibration (P) and definitive (Q) references.

    Returns
    -------
    Shambhala2-harmonized expression matrix (samples × genes).
    """
    import tempfile

    _shambhala_check = ro.r("requireNamespace('Shambhala2', quietly=TRUE)")
    pkg_present = _shambhala_check is not None and bool(_shambhala_check[0])
    if not pkg_present:
        raise NotImplementedError(
            "Shambhala2 R package not installed. "
            "Install via: remotes::install_github('BorisovNM/Shambhala2'). "
            "Also requires GNU Octave with a 'matlab' wrapper on PATH."
        )

    groups = ann_df.loc[exp_df.index, batch_col].astype(str)
    target_mask = (
        groups == target_group
        if target_group in groups.values
        else pd.Series(True, index=exp_df.index)
    )

    def _write_shambhala_csv(df: pd.DataFrame, path: str) -> None:
        mat = df.T.reset_index()
        mat.columns = ["SYMBOL"] + list(df.index)
        mat.to_csv(path, index=False)

    with tempfile.TemporaryDirectory() as td:
        input_path = os.path.join(td, "input.csv")
        p_path     = os.path.join(td, "P.csv")
        q_path     = os.path.join(td, "Q.csv")
        out_path   = os.path.join(td, "output.csv")

        _write_shambhala_csv(exp_df, input_path)
        _write_shambhala_csv(exp_df.loc[target_mask], p_path)
        _write_shambhala_csv(exp_df.loc[target_mask], q_path)

        ro.r(f"""
            library(Shambhala2)
            result <- Shambhala2(
                InputFileName       = "{input_path}",
                PFileName           = "{p_path}",
                QFileName           = "{q_path}",
                delete_buffer_files = TRUE,
                k                   = 5
            )
            write.csv(result, "{out_path}")
        """)

        if not os.path.exists(out_path):
            raise RuntimeError(
                "Shambhala2 produced no output — check that octave is installed "
                "and the 'matlab' wrapper script is on PATH"
            )
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    # result_df is genes × samples; transpose to samples × genes
    return result_df.T.reindex(exp_df.index)


def normalize_harmonizr(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, algorithm: str = "ComBat", **kw: object,
) -> pd.DataFrame:
    """
    HarmonizR (Voss et al. 2022). NA-aware wrapper around ComBat/limma.

    Data format: TSV (genes × samples). Description: CSV with ID/batch/sample(int).
    Output written to {out_base}.tsv by the R package.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.
    algorithm
        'ComBat' or 'limma'.

    Returns
    -------
    HarmonizR-corrected expression matrix.
    """
    import tempfile

    batches        = ann_df.loc[exp_df.index, batch_col].astype(str)
    unique_batches = batches.unique().tolist()
    batch_int_map  = {b: i + 1 for i, b in enumerate(unique_batches)}
    batch_ints     = batches.map(batch_int_map)
    with tempfile.TemporaryDirectory() as td:
        data_path = os.path.join(td, "data.tsv")
        desc_path = os.path.join(td, "description.csv")
        out_base  = os.path.join(td, "out")
        out_path  = out_base + ".tsv"
        exp_df.T.to_csv(data_path, sep="\t")
        desc = pd.DataFrame({
            "ID":     exp_df.index,
            "batch":  batches.values,
            "sample": batch_ints.values,
        })
        desc.to_csv(desc_path, index=False)
        ro.r(f"""
            library(HarmonizR)
            harmonizR(
                data_as_input        = \"{data_path}\",
                description_as_input = \"{desc_path}\",
                algorithm            = \"{algorithm}\",
                output_file          = \"{out_base}\",
                plot                 = FALSE,
                verbosity            = 0
            )
        """)
        if not os.path.exists(out_path):
            raise RuntimeError("HarmonizR produced no output — check R console for errors")
        result = pd.read_csv(out_path, sep="\t", index_col=0)
    _r_gc()
    return result.T.reindex(exp_df.index)


def _assert_rnaseq_only(
    ann_df: pd.DataFrame, batch_col: str = BATCH_COL, method_name: str = ""
) -> None:
    """Raise NotImplementedError if microarray batches (GPL*) are present."""
    if ann_df[batch_col].str.startswith("GPL").any():
        raise NotImplementedError(
            f"{method_name} is RNA-seq only. "
            "Use strategy C_rnaseq_only or filter to RNA-seq samples before calling."
        )


def normalize_tmm(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, **kw: object,
) -> pd.DataFrame:
    """
    TMM normalization via edgeR (Robinson & Oshlack 2010). RNA-seq only.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes, integer counts).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping (used to detect microarray batches).

    Returns
    -------
    log2-CPM after TMM normalization.

    Raises
    ------
    NotImplementedError
        If microarray (GPL*) batches are present in ann_df.
    """
    _assert_rnaseq_only(ann_df, batch_col, "TMM")
    edger_r = importr("edgeR")
    base_r  = importr("base")
    counts  = np.round(exp_df.values).astype(int).clip(0)
    r_mat   = base_r.as_matrix(_py2rpy(
                  pd.DataFrame(counts.T, index=exp_df.columns, columns=exp_df.index)))
    dge     = edger_r.DGEList(counts=r_mat)
    dge     = edger_r.calcNormFactors(dge, method="TMM")
    _raw    = edger_r.cpm(dge, log=True, prior_count=1)
    result  = _raw if isinstance(_raw, np.ndarray) else _rpy2py(_raw)
    out = pd.DataFrame(result.T, index=exp_df.index, columns=exp_df.columns)
    _r_gc()
    return out


def normalize_vst(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, **kw: object,
) -> pd.DataFrame:
    """
    DESeq2 variance-stabilizing transformation (Love et al. 2014). RNA-seq only.

    Uses vst() for >=1000 genes, varianceStabilizingTransformation() otherwise
    (vst() requires nsub=1000 genes minimum).

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes, integer counts).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping (used to detect microarray batches).

    Returns
    -------
    Variance-stabilized expression matrix.

    Raises
    ------
    NotImplementedError
        If microarray (GPL*) batches are present in ann_df.
    """
    _assert_rnaseq_only(ann_df, batch_col, "DESeq2 VST")
    deseq2_r = importr("DESeq2")
    base_r   = importr("base")
    counts   = np.round(exp_df.values).astype(int).clip(0)
    r_mat    = base_r.as_matrix(_py2rpy(
                   pd.DataFrame(counts.T, index=exp_df.columns, columns=exp_df.index)))
    col_data = ro.DataFrame({"sample": ro.StrVector(list(exp_df.index))})
    dds      = deseq2_r.DESeqDataSetFromMatrix(
                   countData=r_mat, colData=col_data, design=ro.Formula("~1"))
    if exp_df.shape[1] >= 1000:
        vsd = deseq2_r.vst(dds, blind=True)
    else:
        vsd = deseq2_r.varianceStabilizingTransformation(dds, blind=True)
    _raw   = ro.r["assay"](vsd)
    result = _raw if isinstance(_raw, np.ndarray) else _rpy2py(_raw)
    out = pd.DataFrame(result.T, index=exp_df.index, columns=exp_df.columns)
    _r_gc()
    return out


def normalize_peer(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame | None = None,
    n_factors: int = 10, **kw: object,
) -> pd.DataFrame:
    """PEER — unavailable for R 4.5."""
    raise NotImplementedError(
        "PEER R package not available for R 4.5: not on CRAN, Bioconductor, or GitHub."
    )


def normalize_xpn(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, target_group: str = "RNASeq_FF_PolyA",
    n_quantiles: int = 50, **kw: object,
) -> pd.DataFrame:
    """
    XPN: per-gene piecewise linear quantile matching (Shabalin et al. 2008).

    Applies iteratively: each non-reference RNA_BATCH is mapped gene-by-gene
    onto the reference batch distribution via K-breakpoint piecewise linear
    interpolation (numpy.interp). Reference batch samples are unchanged.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.
    target_group
        Reference batch. Falls back to all samples if absent in data.
    n_quantiles
        Number of interior quantile breakpoints (K). Default 50.

    Returns
    -------
    XPN-normalized expression matrix.
    """
    groups = ann_df.loc[exp_df.index, batch_col].astype(str)
    ref_present = target_group in groups.values
    ref_mask = groups == target_group if ref_present else pd.Series(True, index=exp_df.index)

    ref_vals = exp_df.loc[ref_mask].values.astype(float)
    quantile_levels = np.linspace(0, 100, n_quantiles + 2)
    ref_q = np.percentile(ref_vals, quantile_levels, axis=0)  # (K+2) × n_genes

    out = exp_df.copy().astype(float)

    for batch in groups.unique():
        if ref_present and batch == target_group:
            continue
        batch_idx = exp_df.index[groups == batch]
        batch_vals = exp_df.loc[batch_idx].values.astype(float)
        src_q = np.percentile(batch_vals, quantile_levels, axis=0)

        transformed = np.empty_like(batch_vals)
        for j in range(batch_vals.shape[1]):
            transformed[:, j] = np.interp(
                batch_vals[:, j],
                src_q[:, j],
                ref_q[:, j],
            )
        out.loc[batch_idx] = transformed

    return out


def normalize_dwd(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, target_group: str = "RNASeq_FF_PolyA",
    min_batch_size: int = 5, **kw: object,
) -> pd.DataFrame:
    """
    DWD iterative per-batch correction via DWDLargeR (Qing & Marron 2018).

    For each non-reference RNA_BATCH, runs DWD against the reference batch to
    find the discriminant direction w, then shifts all batch samples along w
    until their centroid projection matches the reference centroid.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.
    target_group
        Reference batch. Falls back to first-listed batch if absent.
    min_batch_size
        Batches with fewer samples are skipped (DWD direction unstable).

    Returns
    -------
    DWD-corrected expression matrix.
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
    groups = ann_df.loc[exp_in.index, batch_col].astype(str)
    ref_present = target_group in groups.values
    ref_label = target_group if ref_present else groups.iloc[0]

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.T.to_csv(exp_path)
        groups.rename("batch").to_csv(ann_path)

        ro.r(f"""
            library(DWDLargeR)

            exp_mat   <- as.matrix(read.csv("{exp_path}", row.names=1, check.names=FALSE))
            ann_df    <- read.csv("{ann_path}", row.names=1)
            batches   <- ann_df[colnames(exp_mat), "batch"]
            ref_label <- "{ref_label}"

            ref_mask  <- batches == ref_label
            if (sum(ref_mask, na.rm=TRUE) == 0) ref_mask <- rep(TRUE, ncol(exp_mat))
            X_ref     <- exp_mat[, ref_mask, drop=FALSE]
            result    <- exp_mat

            unique_batches <- setdiff(unique(batches), ref_label)
            for (b in unique_batches) {{
                batch_mask <- batches == b
                n_batch    <- sum(batch_mask)
                if (n_batch < {min_batch_size}) {{
                    message("DWD: skipping batch '", b, "' (n=", n_batch,
                            " < min_batch_size={min_batch_size})")
                    next
                }}
                X_batch    <- exp_mat[, batch_mask, drop=FALSE]
                X_combined <- cbind(X_ref, X_batch)
                y          <- c(rep(1, ncol(X_ref)), rep(-1, ncol(X_batch)))

                tryCatch({{
                    sol <- genDWD(X = X_combined, y = y)
                    w <- if (!is.null(sol$beta)) sol$beta else sol$w
                    w <- as.numeric(w)

                    d_ref   <- mean(as.numeric(t(X_ref)   %*% w))
                    d_batch <- mean(as.numeric(t(X_batch) %*% w))
                    shift   <- d_ref - d_batch

                    result[, batch_mask] <- X_batch + shift * w
                }}, error = function(e) {{
                    message("DWD failed for batch '", b, "': ", conditionMessage(e))
                }})
            }}

            write.csv(result, "{out_path}")
        """)

        if not os.path.exists(out_path):
            raise RuntimeError(
                "DWD (DWDLargeR) produced no output — check that "
                "the R package is installed: install.packages('DWDLargeR')"
            )
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.T.reindex(exp_df.index)


def normalize_npn(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, **kw: object,
) -> pd.DataFrame:
    """
    NPN: Nonparanormal Normalization via huge::npn() (Liu et al. 2009).

    Applies rank-based inverse normal transformation per gene within each
    RNA_BATCH independently:
        NPN(g_ij) = Φ⁻¹(rank_b(g_ij) / (n_b + 1))
    where Φ⁻¹ is the probit function. After transformation, every gene's
    marginal distribution is N(0,1) within each batch, removing between-batch
    mean and variance shifts. No reference batch required.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    batch_col
        Column for batch grouping.

    Returns
    -------
    NPN-normalized expression matrix (same shape as input).
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.to_csv(exp_path)
        ann_df.loc[exp_in.index, [batch_col]].to_csv(ann_path)

        ro.r(f"""
            library(huge)

            exp_mat <- as.matrix(read.csv("{exp_path}", row.names=1))
            ann_df  <- read.csv("{ann_path}", row.names=1)
            batches <- as.character(ann_df[rownames(exp_mat), "{batch_col}"])
            result  <- exp_mat

            for (b in unique(batches)) {{
                mask <- batches == b
                X_b  <- exp_mat[mask, , drop=FALSE]
                result[mask, ] <- huge.npn(X_b, npn.func = "truncation",
                                           verbose = FALSE)
            }}

            write.csv(as.data.frame(result), "{out_path}")
        """)

        if not os.path.exists(out_path):
            raise RuntimeError(
                "NPN (huge) produced no output — check that "
                "the R package is installed: install.packages('huge')"
            )
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.reindex(exp_df.index)


def normalize_combat_ref(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, bio_col: str = BIO_COL,
    target_group: str = "RNASeq_FF_PolyA", **kw: object,
) -> pd.DataFrame:
    """
    M-ComBat: ComBat anchored to a reference batch (sva::ComBat ref.batch).

    Same empirical Bayes location-scale model as 05_combat but shifts all
    batches toward the reference batch distribution (RNASeq_FF_PolyA) rather
    than the global mean. Reference batch samples are returned unchanged.
    Falls back to standard ComBat (no ref.batch) when the reference is absent.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col and bio_col.
    batch_col
        Batch column (RNA_BATCH).
    bio_col
        Biology covariate column used in model matrix.
    target_group
        Reference batch. Falls back to global-mean ComBat if absent.

    Returns
    -------
    M-ComBat corrected expression matrix.
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
    groups = ann_df.loc[exp_in.index, batch_col].astype(str)
    ref_present = target_group in groups.values

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.T.to_csv(exp_path)
        ann_df.loc[exp_in.index, [batch_col, bio_col]].fillna("Unknown").to_csv(ann_path)

        ref_arg = f', ref.batch="{target_group}"' if ref_present else ""
        ro.r(f"""
            library(sva)
            exp_mat <- as.matrix(read.csv("{exp_path}", row.names=1, check.names=FALSE))
            ann_df  <- read.csv("{ann_path}", row.names=1)
            batches <- as.character(ann_df[colnames(exp_mat), "{batch_col}"])
            bio     <- as.character(ann_df[colnames(exp_mat), "{bio_col}"])
            mod     <- model.matrix(~ bio)
            result  <- ComBat(dat=exp_mat, batch=batches, mod=mod{ref_arg})
            write.csv(as.data.frame(result), "{out_path}")
        """)

        if not os.path.exists(out_path):
            raise RuntimeError("M-ComBat produced no output — check sva package.")
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.T.reindex(exp_df.index)


def normalize_recombat(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, **kw: object,
) -> pd.DataFrame:
    """
    reComBat: regularized ComBat with ridge regression (BorgwardtLab/reComBat PyPI).

    Python re-implementation of ComBat that replaces OLS batch estimation with
    ridge regression to handle partial batch-biology confounding. Lambda selected
    via cross-validation. Operates natively in Python without R.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.

    Returns
    -------
    reComBat-corrected expression matrix.
    """
    try:
        from reComBat import reComBat as _ReComBat
    except ModuleNotFoundError:
        raise NotImplementedError(
            "reComBat Python package not installed. "
            "Install via: pip install reComBat"
        )

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
    batch = ann_df.loc[exp_in.index, batch_col]

    combat = _ReComBat()
    corrected: pd.DataFrame = combat.fit_transform(exp_in, batch)
    return corrected.reindex(exp_df.index)


def normalize_ruv3prps(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, bio_col: str = BIO_COL,
    k_factors: int = 5, min_cell_size: int = 2, **kw: object,
) -> pd.DataFrame:
    """
    RUV-III-PRPS: RUV-III with Pseudo-Replicate Pseudo-Samples
    (Molania et al. 2022; Bioconductor: ruv).

    For each (bio_col × batch_col) cell with >= min_cell_size samples,
    computes the cell mean as a pseudo-replicate. Stacks pseudo-samples
    with original data and runs ruv::RUVIII() to estimate unwanted variation.
    Falls back to uncorrected data if no valid pseudo-replicate cells exist.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col and bio_col.
    k_factors
        Number of RUV unwanted variation factors (default 5).
    min_cell_size
        Minimum samples per (bio × batch) cell to form a pseudo-replicate.

    Returns
    -------
    RUV-III-PRPS corrected expression matrix (same shape as input).
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.to_csv(exp_path)
        ann_df.loc[exp_in.index, [batch_col, bio_col]].to_csv(ann_path)

        ro.r(f"""
            library(ruv)
            Y       <- as.matrix(read.csv("{exp_path}", row.names=1))
            ann_df  <- read.csv("{ann_path}", row.names=1)
            batches <- as.character(ann_df[rownames(Y), "{batch_col}"])
            bio     <- as.character(ann_df[rownames(Y), "{bio_col}"])
            cells   <- paste(bio, batches, sep="__")
            valid_cells <- names(which(table(cells) >= {min_cell_size}))

            if (length(valid_cells) == 0) {{
                message("RUV-III-PRPS: no valid pseudo-replicates — returning uncorrected")
                write.csv(as.data.frame(Y), "{out_path}")
            }} else {{
                pseudo_Y <- do.call(rbind, lapply(valid_cells, function(cell) {{
                    colMeans(Y[cells == cell, , drop=FALSE])
                }}))
                rownames(pseudo_Y) <- paste0("pseudo__", valid_cells)
                Y_aug    <- rbind(Y, pseudo_Y)
                n_orig   <- nrow(Y)
                n_groups <- length(valid_cells)

                M <- matrix(0L, nrow=nrow(Y_aug), ncol=n_groups)
                for (j in seq_len(n_groups)) {{
                    orig_idx   <- which(cells == valid_cells[j])
                    pseudo_idx <- n_orig + j
                    M[c(orig_idx, pseudo_idx), j] <- 1L
                }}

                k <- min({k_factors}, n_groups - 1L)
                if (k < 1L) k <- 1L

                tryCatch({{
                    ctl    <- rep(TRUE, ncol(Y_aug))
                    fit    <- RUVIII(Y=Y_aug, M=M, ctl=ctl, k=k)
                    newY   <- if (is.list(fit)) {{
                        if (!is.null(fit$newY)) fit$newY else fit$corrY
                    }} else {{
                        fit[seq_len(n_orig), , drop=FALSE]
                    }}
                    result <- newY[seq_len(n_orig), , drop=FALSE]
                    rownames(result) <- rownames(Y)
                    write.csv(as.data.frame(result), "{out_path}")
                }}, error = function(e) {{
                    message("RUV-III-PRPS RUVIII failed: ", conditionMessage(e),
                            " — returning uncorrected data")
                    write.csv(as.data.frame(Y), "{out_path}")
                }})
            }}
        """)

        if not os.path.exists(out_path):
            raise RuntimeError("RUV-III-PRPS produced no output — check ruv package.")
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.reindex(exp_df.index)


def normalize_deepmnn(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, **kw: object,
) -> pd.DataFrame:
    """
    deepMNN: NOT APPLICABLE to this benchmark.

    deepMNN (Luo et al. 2021, PMID 34616432; GitHub: zoubin-ai/deepMNN)
    is a scRNA-seq-only method. Its entry point correct_scanpy() requires a
    list of AnnData objects with HVG selection and PCA already computed
    (adata.obsm['X_pca']) — standard scRNA-seq preprocessing incompatible
    with bulk RNA-seq / microarray expression matrices. The package is not
    on PyPI and cannot be pip-installed. This function raises NotImplementedError
    and is recorded as SKIP by the dispatcher.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.

    Returns
    -------
    Never returns — always raises NotImplementedError.
    """
    raise NotImplementedError(
        "deepMNN (zoubin-ai/deepMNN) is NOT APPLICABLE: scRNA-seq-only method "
        "that requires AnnData + HVG + PCA preprocessing. Not compatible with "
        "bulk RNA-seq / microarray matrices. Reference: Luo et al. 2021, "
        "PMID 34616432."
    )


def normalize_amdbnorm(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, target_group: str = "RNASeq_FF_PolyA", **kw: object,
) -> pd.DataFrame:
    """
    AMDBNorm: Adjustment Mean Distribution-Based Normalization
    (PMID 34958674; GitHub: JoevVan/AMDBNorm; depends on mengqinxue/DBNorm).

    Fits a degree-9 polynomial to the reference batch distribution, then
    corrects each non-reference batch individually using that fit. Results are
    combined into a single output matrix. Falls back to first batch as reference
    if RNASeq_FF_PolyA is absent.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.
    target_group
        Reference batch (default: RNASeq_FF_PolyA).

    Returns
    -------
    AMDBNorm-corrected expression matrix.
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
    groups = ann_df.loc[exp_in.index, batch_col].astype(str)
    ref_label = target_group if target_group in groups.values else groups.iloc[0]

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.T.to_csv(exp_path)
        groups.rename("batch").to_csv(ann_path)

        ro.r(f"""
            library(AMDBNorm)
            library(DBNorm)
            library(reshape2)

            exp_mat   <- as.matrix(read.csv("{exp_path}", row.names=1, check.names=FALSE))
            batches   <- read.csv("{ann_path}", row.names=1)[colnames(exp_mat), "batch"]
            ref_label <- "{ref_label}"
            ref_mask  <- batches == ref_label
            ref_mat   <- exp_mat[, ref_mask, drop=FALSE]

            dis <- DBNorm::genDistData(na.omit(melt(ref_mat)[, 3]), 500)
            fit <- DBNorm::polyFit(dis, 9)

            result <- ref_mat
            for (b in setdiff(unique(batches), ref_label)) {{
                batch_mask  <- batches == b
                batch_mat   <- exp_mat[, batch_mask, drop=FALSE]
                corrected   <- AMDBNorm(data=batch_mat, ref_batch=ref_mat, fit=fit)
                result      <- cbind(result, corrected)
            }}
            result <- result[, colnames(exp_mat)]
            write.csv(as.data.frame(result), "{out_path}")
        """)

        if not os.path.exists(out_path):
            raise RuntimeError(
                "AMDBNorm produced no output. "
                "Install: remotes::install_github('JoevVan/AMDBNorm') and "
                "remotes::install_github('mengqinxue/DBNorm')"
            )
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.T.reindex(exp_df.index)


def normalize_arsyn(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, bio_col: str = BIO_COL, **kw: object,
) -> pd.DataFrame:
    """
    ARSyN: ANOVA-ASCA Removal of Systematic Noise (PMID 22085896; NOISeq).

    Decomposes expression into biology + batch + residual via ANOVA-ASCA,
    subtracts the batch PCA component. Validated for microarray; applied here
    to all strategies. Requires NOISeq data container wrapping.
    tryCatch guard returns uncorrected data on failure.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col and bio_col.

    Returns
    -------
    ARSyN-corrected expression matrix.
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.T.to_csv(exp_path)
        ann_df.loc[exp_in.index, [batch_col, bio_col]].fillna("Unknown").to_csv(ann_path)

        ro.r(f"""
            library(NOISeq)
            exp_mat <- as.matrix(read.csv("{exp_path}", row.names=1))
            ann_df  <- read.csv("{ann_path}", row.names=1)
            factors <- data.frame(
                Batch     = as.character(ann_df[colnames(exp_mat), "{batch_col}"]),
                Condition = as.character(ann_df[colnames(exp_mat), "{bio_col}"]),
                row.names = colnames(exp_mat)
            )
            mydata <- readData(data=exp_mat, factors=factors)
            tryCatch({{
                myresult <- ARSyNseq(mydata, factor="Batch", norm="n",
                                     logtransf=FALSE)
                result   <- assayData(myresult)$exprs
                write.csv(as.data.frame(result), "{out_path}")
            }}, error = function(e) {{
                message("ARSyN failed: ", conditionMessage(e),
                        " — returning uncorrected data")
                write.csv(as.data.frame(exp_mat), "{out_path}")
            }})
        """)

        if not os.path.exists(out_path):
            raise RuntimeError("ARSyN produced no output — check NOISeq package.")
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.T.reindex(exp_df.index)


def normalize_dasc(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, **kw: object,
) -> pd.DataFrame:
    """
    DASC: NOT APPLICABLE to this benchmark.

    DASC (Chen et al. 2018, PMID 29617963; GitHub: zhanglabNKU/DASC) is a
    batch detection / sample classification tool, not a batch correction tool.
    It returns semi-NMF cluster assignments (batch factor groupings), not a
    corrected expression matrix. The fn(exp_df, ann_df) -> pd.DataFrame
    interface is architecturally incompatible. Recorded as SKIP.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.

    Returns
    -------
    Never returns — always raises NotImplementedError.
    """
    raise NotImplementedError(
        "DASC (zhanglabNKU/DASC) is NOT APPLICABLE: batch detection tool that "
        "returns cluster assignments, not a corrected expression matrix. "
        "Reference: Chen et al. 2018, PMID 29617963."
    )


def normalize_explobatch(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, bio_col: str = BIO_COL,
    maxdim: int = 9, **kw: object,
) -> pd.DataFrame:
    """
    exploBATCH: PPCCA-based batch detection and correction
    (PMID 28883548; GitHub: syspremed/exploBATCH).

    Tests for batch significance via Probabilistic PCA with Covariates
    Analysis (PPCCA) then subtracts the estimated batch component.
    Output is written to disk by expBATCH(); read back after the call.
    Computationally intensive — tryCatch returns uncorrected on failure.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col and bio_col.
    maxdim
        Maximum number of pPCA dimensions to search (default 9).

    Returns
    -------
    exploBATCH-corrected expression matrix.
    """
    import tempfile
    import glob

    _fmm_check = ro.r("requireNamespace('fMM', quietly=TRUE)")
    if _fmm_check is None or not bool(_fmm_check[0]):
        raise NotImplementedError(
            "fMM R package not available (GitHub repo maxkuhn/fMM deleted). "
            "exploBATCH depends on fMM at runtime; method is permanently unavailable "
            "until fMM is restored from a CRAN archive tarball."
        )

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_dir  = os.path.join(td, "correctBATCH")

        # expBATCH expects samples × genes (rows=samples)
        exp_in.to_csv(exp_path)
        ann_df.loc[exp_in.index, [batch_col, bio_col]].to_csv(ann_path)

        ro.r(f"""
            # Intercept source("https://bioconductor.org/biocLite.R") inside expBATCH.
            # The URL returns 404 since biocLite was deprecated in 2018. We stub both
            # source() and biocLite() so the package's dependency check becomes a no-op.
            # All required packages (mvtnorm, mclust, sva, ggplot2, RColorBrewer,
            # rARPACK, Rcpp, foreach, doParallel, doMC, fMM, exploBATCHbreast,
            # exploBATCHcolon) must already be installed on the pod.
            biocLite <- function(...) invisible(NULL)
            .source_orig <- base::source
            source <- function(file, ...) {{
                if (is.character(file) && grepl("biocLite\\.R", file, fixed=FALSE)) {{
                    message("Skipping deprecated biocLite.R URL: ", file)
                    invisible(NULL)
                }} else {{
                    .source_orig(file, ...)
                }}
            }}

            library(exploBATCH)
            setwd("{td}")
            exp_mat <- as.matrix(read.csv("{exp_path}", row.names=1))
            ann_df  <- read.csv("{ann_path}", row.names=1)
            batches <- as.character(ann_df[rownames(exp_mat), "{batch_col}"])
            bio     <- as.character(ann_df[rownames(exp_mat), "{bio_col}"])

            tryCatch({{
                expBATCH(D=exp_mat, batchCL=batches, Conf=bio,
                         mindim=2, maxdim=min({maxdim}, nrow(exp_mat) - 3),
                         method="ppcca", scale="unit", SDselect=0)
            }}, error = function(e) {{
                message("exploBATCH failed: ", conditionMessage(e),
                        " — output file will not be created")
            }})
        """)

        # expBATCH writes to {td}/correctBATCH/{date}_ppccaCorrectedData.txt
        pattern = os.path.join(out_dir, "*ppccaCorrectedData.txt")
        matches = glob.glob(pattern)
        if not matches:
            # Fallback: return uncorrected data
            return exp_df.copy()
        result_df = pd.read_csv(matches[0], sep="\t", index_col=0)

    _r_gc()
    # expBATCH output is samples × genes; reindex to preserve original index
    return result_df.reindex(exp_df.index)


def normalize_fabatch(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, **kw: object,
) -> pd.DataFrame:
    """
    FAbatch via bapred: Factor Adjustment batch correction (PMID 26753519).

    The method referred to as "FAbatch" in the literature is implemented as the
    function fabatch() inside the R package bapred (Batch Prediction). There is
    no standalone package named FAbatch on CRAN. bapred::fabatch() applies a
    factor model to adjust batch effects in the expression matrix. The batch
    vector is used as a surrogate class label (required by the function interface).
    Output extracted from result$adj.data.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col.

    Returns
    -------
    bapred fabatch-corrected expression matrix.
    """
    import tempfile

    _bapred_check = ro.r("requireNamespace('bapred', quietly=TRUE)")
    if _bapred_check is None or not bool(_bapred_check[0]):
        raise NotImplementedError(
            "bapred R package not installed. "
            "Install via: install.packages('bapred'). "
            "Also requires affy, affyPLM, sva from Bioconductor and cmake system dependency."
        )

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.T.to_csv(exp_path)
        ann_df.loc[exp_in.index, [batch_col]].to_csv(ann_path)

        ro.r(f"""
            library(bapred)
            exp_mat <- as.matrix(read.csv("{exp_path}", row.names=1, check.names=FALSE))
            ann_df  <- read.csv("{ann_path}", row.names=1)
            batches <- as.factor(ann_df[colnames(exp_mat), "{batch_col}"])
            tryCatch({{
                res    <- fabatch(xtr=t(exp_mat), ytr=batches, batch=batches,
                                  type="among")
                result <- if (!is.null(res$adj.data)) t(res$adj.data) else exp_mat
                write.csv(as.data.frame(result), "{out_path}")
            }}, error = function(e) {{
                message("bapred fabatch failed: ", conditionMessage(e),
                        " — returning uncorrected data")
                write.csv(as.data.frame(exp_mat), "{out_path}")
            }})
        """)

        if not os.path.exists(out_path):
            raise RuntimeError("bapred fabatch produced no output — check bapred package.")
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.T.reindex(exp_df.index)


def normalize_harman(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, bio_col: str = BIO_COL,
    limit: float = 0.1, **kw: object,
) -> pd.DataFrame:
    """
    Harman: PCA-based batch correction with overcorrection constraint
    (PMID 27585881; Bioconductor: Harman).

    Corrects batch effects in PCA space with a formal bound on the probability
    of over-removing biological signal. limit=0.1: 10% overcorrection
    probability allowed. Cross-platform validated (RNA-seq + microarray).

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).
    ann_df
        Annotation with batch_col and bio_col.
    limit
        Overcorrection probability bound (default 0.1). Lower values are
        more conservative (less correction); 1.0 is unconstrained.

    Returns
    -------
    Harman-corrected expression matrix.
    """
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df

    with tempfile.TemporaryDirectory() as td:
        exp_path = os.path.join(td, "exp.csv")
        ann_path = os.path.join(td, "ann.csv")
        out_path = os.path.join(td, "out.csv")

        exp_in.T.to_csv(exp_path)
        ann_df.loc[exp_in.index, [batch_col, bio_col]].fillna("Unknown").to_csv(ann_path)

        ro.r(f"""
            library(Harman)
            exp_mat <- as.matrix(read.csv("{exp_path}", row.names=1))
            ann_df  <- read.csv("{ann_path}", row.names=1)
            batches <- as.character(ann_df[colnames(exp_mat), "{batch_col}"])
            bio     <- as.character(ann_df[colnames(exp_mat), "{bio_col}"])
            tryCatch({{
                pc     <- harman(exp_mat, expt=bio, batch=batches, limit={limit})
                result <- reconstructData(pc)
                write.csv(as.data.frame(result), "{out_path}")
            }}, error = function(e) {{
                message("Harman failed: ", conditionMessage(e),
                        " — returning uncorrected data")
                write.csv(as.data.frame(exp_mat), "{out_path}")
            }})
        """)

        if not os.path.exists(out_path):
            raise RuntimeError("Harman produced no output — check Harman package.")
        result_df = pd.read_csv(out_path, index_col=0)

    _r_gc()
    return result_df.T.reindex(exp_df.index)


def normalize_procrustes(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL,
    ec_batch_substr: str = "Exome_capture",
    coeffs_kit: str = "V7_UTR",
    **kw: object,
) -> pd.DataFrame:
    """
    Procrustes: per-gene linear EC→polyA RNA-seq correction
    (Kotlov et al. 2024, Commun Biol; GitHub: BostonGene/Procrustes).

    Applies pre-fitted per-gene linear coefficients (slope + intercept,
    kit-specific JSON: V4 / V7 / V7_UTR) to exome-capture RNA-seq batches
    to convert them to polyA-equivalent expression. Non-EC RNA-seq batches
    are left unchanged. RNA-seq only: raises NotImplementedError on any
    GPL* (microarray) batch. Designed for C_rnaseq_only; SKIP elsewhere.
    Genes absent from the coefficient JSON keep their original values.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes), log2(TPM+1).
    ann_df
        Annotation with batch_col.
    batch_col
        Batch column (RNA_BATCH).
    ec_batch_substr
        Substring identifying exome-capture batches in RNA_BATCH values.
        Default: "Exome_capture" (matches RNASeq_FFPE_Exome_capture).
    coeffs_kit
        Kit identifier for Procrustes coefficient file.
        One of "V4", "V7", "V7_UTR". Default: "V7_UTR".

    Returns
    -------
    Procrustes-corrected expression matrix (same shape as input).
    """
    import sys

    _assert_rnaseq_only(ann_df.loc[exp_df.index], batch_col, "Procrustes")

    groups = ann_df.loc[exp_df.index, batch_col].astype(str)
    ec_mask = groups.str.contains(ec_batch_substr, case=False)

    if not ec_mask.any():
        return exp_df.copy()

    _PROCRUSTES_PATH = "/app/Procrustes"
    if _PROCRUSTES_PATH not in sys.path:
        sys.path.insert(0, _PROCRUSTES_PATH)

    try:
        from procrustes_bg.transform import Procrustes_predict  # type: ignore[import]
        coeffs_path = os.path.join(
            _PROCRUSTES_PATH, "procrustes_bg", "data", f"{coeffs_kit}_coefficients.json"
        )
    except (ModuleNotFoundError, ImportError):
        raise NotImplementedError(
            "Procrustes module not found at /app/Procrustes. "
            "Clone the repo: git clone https://github.com/BostonGene/Procrustes.git /app/Procrustes"
        )

    out = exp_df.copy().astype(float)
    ec_exp = exp_df.loc[ec_mask]

    corrected = Procrustes_predict(ec_exp, path_to_coeffs=coeffs_path)
    corrected_aligned = corrected.reindex(columns=exp_df.columns)
    no_coeff_genes = corrected_aligned.columns[corrected_aligned.isna().all()]
    if len(no_coeff_genes):
        corrected_aligned[no_coeff_genes] = ec_exp[no_coeff_genes].values

    out.loc[ec_mask] = corrected_aligned.values
    return out


# ── Methods registry ──────────────────────────────────────────────────────────
METHODS: dict[str, tuple[object, str]] = {
    "01_raw":               (normalize_raw,               "low"),
    "02_median_scaling":    (normalize_median_scaling,     "low"),
    "03_limma":             (normalize_limma,              "low"),
    "04_sva":               (normalize_sva,                "low"),
    "05_combat":            (normalize_combat,             "medium"),
    "06_combat_seq":        (normalize_combat_seq,         "medium"),
    "07_pycombat":          (normalize_pycombat,           "medium"),
    "08_inmoose_combatseq": (normalize_inmoose_combat_seq, "medium"),
    "09_ruv":               (normalize_ruv,                "medium"),
    "10_mnn":               (normalize_mnn,                "medium"),
    "11_harmony":           (normalize_harmony,            "medium"),
    "12_scanorama":         (normalize_scanorama,          "medium"),
    "13_fsmvn":             (normalize_fsmvn,              "medium"),
    "14_qsmooth":           (normalize_qsmooth,            "high"),
    "15_fsqn_py":           (normalize_fsqn_py,            "high"),
    "16_fsqn_r":            (normalize_fsqn_r,             "high"),
    "17_quantile":          (normalize_quantile,           "high"),
    "18_rank":              (normalize_rank,               "high"),
    "19_tdm":               (normalize_tdm,                "high"),
    "20_shambhala":         (normalize_shambhala,          "high"),
    "21_harmonizr":         (normalize_harmonizr,          "medium"),
    "22_tmm":               (normalize_tmm,                "low"),
    "23_vst":               (normalize_vst,                "low"),
    "24_peer_k10":          (normalize_peer,               "medium"),
    "25_angel":             (normalize_angel,              "high"),
    "26_xpn":               (normalize_xpn,                "high"),
    "27_dwd":               (normalize_dwd,                "medium"),
    "28_npn":               (normalize_npn,                "high"),
    "29_combat_ref":        (normalize_combat_ref,         "medium"),
    "30_recombat":          (normalize_recombat,           "medium"),
    "31_ruv3prps":          (normalize_ruv3prps,           "medium"),
    "32_deepmnn":           (normalize_deepmnn,            "medium"),
    "33_amdbnorm":          (normalize_amdbnorm,           "high"),
    "34_arsyn":             (normalize_arsyn,              "medium"),
    "35_dasc":              (normalize_dasc,               "medium"),
    "36_explobatch":        (normalize_explobatch,         "medium"),
    "37_fabatch":           (normalize_fabatch,            "medium"),
    "38_harman":            (normalize_harman,             "medium"),
    "39_procrustes":        (normalize_procrustes,         "high"),
}

HARSHNESS_COLORS: dict[str, str] = {
    "low":          "#4da6ff",
    "medium":       "#ff9933",
    "high":         "#cc0000",
    "rna_seq_only": "#aaaaaa",
}
