# Implementation Plan: Parallel Cross-Product Script

> **Goal:** Run all 1,920 (strategy × imputation × method × post-removal) combinations in parallel as standalone Python processes, save every successful harmonized expression matrix to S3, and produce a metrics summary CSV readable back into the notebook.
>
> **Do not implement yet.** This document is the design spec.

---

## Background and motivation

The cross-product in `harmonization_benchmark.ipynb` (Section 4, cell 39) iterates over:

| Dimension | Values | Count |
|---|---|---|
| Filtering strategy | S0, A, B, C, D, E1, E2, E3, F, G | 10 |
| Imputation | strict, knn, missforest, softimpute | 4 |
| Normalization method | 01_raw … 24_peer_k10 | 24 |
| Post-harmonic outlier removal | False, True | 2 |
| **Total combinations** | | **1,920** |

Running this sequentially in the notebook takes ~8–24 h depending on method speeds. The primary bottleneck is R-based methods (ComBat, SVA, MNN, FSQN, HarmonizR), each of which takes 5–30 min per (strategy, imputation) input dataset.

**Key constraint:** rpy2 is not fork-safe — `pandas2ri.activate()` and R sessions cannot be shared across `multiprocessing.Pool` workers. Parallelism must be achieved by launching independent Python subprocesses (one per job), not via fork-based pools.

---

## File structure

```
harmonization_benchmark.ipynb          # existing notebook (unchanged)
bench_shared.py                        # extracted utility functions (shared library)
run_one_job.py                         # single-job worker: one (strat × imp × method)
run_cross_product_parallel.py          # dispatcher: launches all jobs with concurrency cap
load_cross_product_results.py          # notebook helper: downloads metrics + top-N exp from S3
```

All scripts live alongside the notebook in `~/B_cell_lymphomas/`.

---

## S3 storage layout

**Bucket:** `s3://$FL_S3_BUCKET/`  
**Prefix:** `FL_batch_correction/`

Each successful (strategy, imputation, method, post_removal) tuple writes two objects:

```
FL_batch_correction/
  exp/{strat}__{imp}__{method}__{post_rm}.tsv.gz    # expression matrix (samples × genes)
  metrics.csv                                        # all rows; rebuilt after each run
```

Expression files are written **only** when normalization succeeds (no NaN result).  
The `metrics.csv` is a flat table with one row per combination including failed ones (NaN for r2 values).

### Naming convention

`post_rm` encodes as `post0` (no removal) or `post1` (with removal).  
Example key: `FL_batch_correction/exp/A_confirmed_bad__knn__05_combat__post0.tsv.gz`

### Expression file format

- TSV, gzip-compressed
- Index: sample IDs (same as `exp_df.index`)
- Columns: gene symbols (same as `exp_df.columns`)
- Encoding: UTF-8

### Metrics CSV schema

```
strat, imp, method, post_rm, harshness, r2_batch, r2_diag, n_samples, n_genes, status
```

`status` is one of: `ok`, `failed`, `skipped` (NotImplementedError / expected skips for RNA-seq-only methods on mixed strategies).

---

## Module 1 — `bench_shared.py`

Extracts all reusable functions from the notebook into a single importable module. No notebook-specific state (no `comb_exp`, `comb_ann` globals). Everything is parameterised.

### Key contents

```python
# bench_shared.py
import os, warnings, traceback
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import rpy2.robjects as ro
from rpy2.robjects import pandas2ri
from rpy2.robjects.packages import importr
pandas2ri.activate()

# ── Constants (mirrored from notebook) ────────────────────────────────────────
REMOTE_ROOT = "$FL_DATA_ROOT"
EXP_PATH    = f"{REMOTE_ROOT}/comb_exp.tsv"
ANN_PATH    = "~/B_cell_lymphomas/comb_ann_unified.csv"
BIO_COL     = "Diagnosis_cell_type_unified"
BATCH_COL   = "RNA_BATCH"
S3_BUCKET   = "$FL_S3_BUCKET"
S3_PREFIX   = "FL_batch_correction"

RARE_GROUPS = [
    "Extranodal_Marginal_Zone_Lymphoma", "Double_Hit_Lymphoma",
    "Mantle_Cell_Lymphoma", "Chronic_Lymphocytic_Leukemia", "Other",
]
NORMAL_GROUPS = [
    "Memory", "Centroblast", "Centrocyte", "Bone_marrow_CD19+",
    "Plasma", "Naive", "GC", "B_cells", "MZ", "Plasmablast", "Immature",
]
BAD_BATCHES_A = ["GPL14951_FFPE_Unknown", "GPL8432_FFPE_Unknown", "GPL13938_FFPE_Unknown"]
BAD_COHORTS_A = ["SOM"]
BAD_BATCHES_B = BAD_BATCHES_A + [
    "GPL6244_FFPE_Unknown", "GPL17586_FF_Unknown", "GPL20188_FF_Unknown",
    "GPL23541_FF_Unknown",  "GPL887_FFPE_Unknown",  "GPL26356_FF_Unknown",
    "GPL17047_FF_Unknown",  "GPL6244_FF_Unknown",
]

# ── Data loading ──────────────────────────────────────────────────────────────
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load raw expression and annotation. Returns (comb_exp, comb_ann)."""
    comb_exp = pd.read_csv(EXP_PATH, sep="\t", index_col=0)
    comb_ann = pd.read_csv(ANN_PATH, index_col=0)
    comb_ann["Diagnosis_with_coo"] = (
        comb_ann.Diagnosis_cell_type_general + "_" + comb_ann["coo_bg"].fillna("")
    )
    comb_ann["Diagnosis_unified_with_coo"] = (
        comb_ann.Diagnosis_cell_type_unified + "_" + comb_ann["coo_bg"].fillna("")
    )
    comb_ann.loc[
        comb_ann.index.isin(["PUB_Suntsova_GSE120795"]), "RNA_BATCH"
    ] = "RNASeq_FF_Unknown"
    common = comb_exp.index.intersection(comb_ann.index)
    comb_exp = comb_exp.loc[common]
    comb_exp = comb_exp.loc[~comb_exp.index.duplicated(keep="first")]
    comb_ann = comb_ann.loc[~comb_ann.index.duplicated(keep="first")]
    return comb_exp, comb_ann


# ── Log transform ─────────────────────────────────────────────────────────────
def log_transform_by_cohort(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    batch_col: str = "COHORT_LABEL",
    threshold: float = 30,
) -> pd.DataFrame:
    batches = ann_df[batch_col].value_counts().index
    df_list = []
    for batch in batches:
        samples   = ann_df.index[ann_df[batch_col] == batch]
        exp_local = exp_df.reindex(samples)
        if exp_local.max().max() > threshold:
            exp_local = np.log2(exp_local + 1)
        df_list.append(exp_local)
    return pd.concat(df_list, axis=0)


# ── R² metric ─────────────────────────────────────────────────────────────────
def pca_variance_explained_by_batch(
    exp_df: pd.DataFrame,
    batch_series: pd.Series,
    n_components: int = 10,
) -> float:
    pca    = PCA(n_components=n_components)
    coords = pca.fit_transform(StandardScaler().fit_transform(exp_df.fillna(0)))
    groups = batch_series.reindex(exp_df.index).fillna("NA")
    r2_list = []
    for pc in range(n_components):
        vals       = coords[:, pc]
        grand_mean = vals.mean()
        ss_between = sum(
            len(vals[groups == g]) * (vals[groups == g].mean() - grand_mean) ** 2
            for g in groups.unique() if (groups == g).sum() > 1
        )
        ss_total = ((vals - grand_mean) ** 2).sum()
        r2_list.append(ss_between / ss_total if ss_total > 0 else 0)
    return float(np.mean(r2_list))

def r2_batch(exp_df: pd.DataFrame, ann_df: pd.DataFrame,
             batch_col: str = BATCH_COL, n_pcs: int = 10) -> float:
    return pca_variance_explained_by_batch(exp_df, ann_df[batch_col], n_pcs)


# ── Filtering helpers ─────────────────────────────────────────────────────────
def apply_filter(
    ann: pd.DataFrame,
    ann_base: pd.DataFrame,
    bad_batches: tuple = (),
    bad_cohorts: tuple = (),
    keep_batches: list | None = None,
    keep_groups: list | None = None,
    bio_col: str = BIO_COL,
) -> pd.DataFrame:
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
    common = exp_df.index.intersection(ann_df.index)
    X      = StandardScaler().fit_transform(exp_df.loc[common].fillna(0))
    coords = PCA(n_components=n_pcs).fit_transform(X)
    coords_df = pd.DataFrame(coords, index=common)
    batches   = ann_df.loc[common, batch_col].fillna("NA")
    global_centroid = coords_df.mean(axis=0).values
    batch_centroids: dict[str, float] = {}
    for b in batches.unique():
        idx = batches[batches == b].index
        if len(idx) < min_batch_size:
            continue
        batch_centroids[b] = float(np.linalg.norm(
            coords_df.loc[idx].mean(axis=0).values - global_centroid
        ))
    ranked = sorted(batch_centroids, key=batch_centroids.get, reverse=True)
    return ranked[:n_outliers]


def prepare_dataset(
    ann_filter: pd.DataFrame,
    exp_full: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
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
        r_mat  = pandas2ri.py2rpy(exp)
        result = missforest_r.missForest(r_mat)
        imp_np = pandas2ri.rpy2py(result.rx2("ximp"))
        exp    = pd.DataFrame(imp_np, index=exp.index, columns=exp.columns)
    elif method == "softimpute":
        softimpute_r = importr("softImpute")
        base_r       = importr("base")
        r_mat   = base_r.as_matrix(pandas2ri.py2rpy(exp))
        si_obj  = softimpute_r.softImpute(r_mat, type="svd")
        imp_mat = softimpute_r.complete(r_mat, si_obj)
        imp_np  = pandas2ri.rpy2py(imp_mat)
        exp     = pd.DataFrame(imp_np, index=exp.index, columns=exp.columns)
    else:
        raise ValueError(f"Unknown imputation method: {method}")
    return exp, ann


# ── Strategy builder ──────────────────────────────────────────────────────────
def build_filter_strategies(
    comb_ann: pd.DataFrame,
    comb_exp: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """
    Reproduces Cells 12–22 of harmonization_benchmark.ipynb.
    Returns FILTER_STRATEGIES dict mapping strategy name → annotation DataFrame.
    Also returns datasets dict: strategy name → (exp_df, ann_df).
    """
    ann_base = comb_ann[~comb_ann[BIO_COL].isin(RARE_GROUPS)].copy()

    rnaseq_batches     = [b for b in ann_base[BATCH_COL].unique() if b.startswith("RNASeq")]
    microarray_batches = [b for b in ann_base[BATCH_COL].unique() if not b.startswith("RNASeq")]
    affymetrix_batches = [b for b in ann_base[BATCH_COL].unique() if b.startswith("GPL570")]
    malignant_groups   = [g for g in ann_base[BIO_COL].unique() if g not in NORMAL_GROUPS]

    def _f(**kw):
        return apply_filter(ann_base, ann_base, **kw)

    ann_S0 = ann_base.copy()
    ann_A  = _f(bad_batches=BAD_BATCHES_A, bad_cohorts=BAD_COHORTS_A)
    ann_B  = _f(bad_batches=BAD_BATCHES_B, bad_cohorts=["SOM"])
    ann_C  = _f(keep_batches=rnaseq_batches)
    ann_D  = _f(keep_groups=malignant_groups)
    ann_F  = _f(keep_batches=microarray_batches)
    ann_G  = _f(keep_batches=affymetrix_batches)

    # Iterative PCA outlier removal
    exp_A, _  = prepare_dataset(ann_A, comb_exp)
    exp_A     = log_transform_by_cohort(exp_A, ann_A.loc[exp_A.index])
    out_E1    = identify_outlier_batches(exp_A, ann_A)
    ann_E1    = _f(bad_batches=BAD_BATCHES_A + out_E1, bad_cohorts=BAD_COHORTS_A)

    exp_E1, _ = prepare_dataset(ann_E1, comb_exp)
    exp_E1    = log_transform_by_cohort(exp_E1, ann_E1.loc[exp_E1.index])
    out_E2    = identify_outlier_batches(exp_E1, ann_E1)
    ann_E2    = apply_filter(ann_E1, ann_base, bad_batches=out_E2)

    exp_E2, _ = prepare_dataset(ann_E2, comb_exp)
    exp_E2    = log_transform_by_cohort(exp_E2, ann_E2.loc[exp_E2.index])
    out_E3    = identify_outlier_batches(exp_E2, ann_E2)
    ann_E3    = apply_filter(ann_E2, ann_base, bad_batches=out_E3)

    return {
        "S0_no_removal":     ann_S0,
        "A_confirmed_bad":   ann_A,
        "B_extended_bad":    ann_B,
        "C_rnaseq_only":     ann_C,
        "D_malignant_only":  ann_D,
        "E1_iterative_r1":   ann_E1,
        "E2_iterative_r2":   ann_E2,
        "E3_iterative_r3":   ann_E3,
        "F_microarray_only": ann_F,
        "G_affymetrix_only": ann_G,
    }


# ── S3 helpers ────────────────────────────────────────────────────────────────
def s3_key_exp(strat: str, imp: str, method: str, post_rm: bool) -> str:
    pr = "post1" if post_rm else "post0"
    return f"{S3_PREFIX}/exp/{strat}__{imp}__{method}__{pr}.tsv.gz"

def s3_key_metrics() -> str:
    return f"{S3_PREFIX}/metrics.csv"

def s3_exists(s3_client, key: str) -> bool:
    import botocore
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=key)
        return True
    except botocore.exceptions.ClientError:
        return False

def upload_exp_to_s3(exp_df: pd.DataFrame, s3_client, key: str) -> None:
    import io, gzip
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        exp_df.to_csv(gz, sep="\t")
    buf.seek(0)
    s3_client.upload_fileobj(buf, S3_BUCKET, key)

def download_exp_from_s3(s3_client, key: str) -> pd.DataFrame:
    import io, gzip
    buf = io.BytesIO()
    s3_client.download_fileobj(S3_BUCKET, key, buf)
    buf.seek(0)
    with gzip.open(buf, "rb") as gz:
        return pd.read_csv(gz, sep="\t", index_col=0)
```

**Notes on `build_filter_strategies`:**
- The iterative removal (E1–E3) requires loading and log-transforming expression for PCA — this happens once at startup in the dispatcher, not in each worker.
- `apply_filter` is made pure by passing `ann_base` explicitly (no global state).

---

## Module 2 — `run_one_job.py`

Processes **one** (strategy, imputation, method) triple. Both post-removal options (`False`, `True`) are handled in the same process to avoid running normalization twice.

### Invocation

```bash
python run_one_job.py \
    --strat A_confirmed_bad \
    --imp   knn \
    --method 05_combat \
    [--skip-if-exists]    # skip if S3 key already exists
```

### Logic

```python
# run_one_job.py
"""
Worker: runs one normalization method on one (strategy, imputation) dataset.
Writes up to 2 expression files to S3 (post_rm=False/True) and a metrics row.
Designed to be launched as a subprocess — rpy2 initializes fresh in each process.
"""
import argparse, json, sys, traceback, io, gzip
import numpy as np
import pandas as pd
import boto3

# All normalization functions and utilities live in bench_shared
from bench_shared import (
    load_data, log_transform_by_cohort,
    build_filter_strategies, prepare_dataset, prepare_dataset_imputed,
    identify_outlier_batches, r2_batch,
    s3_key_exp, s3_key_metrics, s3_exists,
    upload_exp_to_s3,
    BIO_COL, BATCH_COL, S3_BUCKET, S3_PREFIX,
)


def get_methods() -> dict:
    """Import all normalize_* functions. Must be called after rpy2 is ready."""
    # Import normalization functions exactly as defined in the notebook
    # They are kept in bench_shared or imported from it
    from bench_shared import METHODS  # assumes METHODS is also defined in bench_shared
    return METHODS


def run_job(
    strat: str,
    imp: str,
    method_name: str,
    skip_if_exists: bool,
    comb_exp: pd.DataFrame,
    filter_strategies: dict[str, pd.DataFrame],
) -> list[dict]:
    """
    Returns a list of metric rows (one per post_rm option).
    Writes expression files to S3 on success.
    """
    import boto3
    s3 = boto3.client("s3")
    methods = get_methods()
    fn, harshness = methods[method_name]

    ann_strat = filter_strategies[strat]

    # --- Imputation ---
    if imp == "strict":
        exp_s, ann_s = prepare_dataset(ann_strat, comb_exp)
    else:
        try:
            exp_s, ann_s = prepare_dataset_imputed(ann_strat, comb_exp, method=imp)
        except Exception:
            print(f"[{strat}×{imp}×{method_name}] Imputation failed:\n{traceback.format_exc()}")
            exp_s, ann_s = prepare_dataset(ann_strat, comb_exp)

    exp_s = log_transform_by_cohort(exp_s, ann_s.loc[exp_s.index])

    # --- Normalization ---
    try:
        exp_norm = fn(exp_s, ann_s, batch_col=BATCH_COL, bio_col=BIO_COL)
    except NotImplementedError as e:
        print(f"[{strat}×{imp}×{method_name}] Skipped (NotImplementedError): {e}")
        return [
            {
                "strat": strat, "imp": imp, "method": method_name,
                "post_rm": post_rm, "harshness": harshness,
                "r2_batch": float("nan"), "r2_diag": float("nan"),
                "n_samples": len(ann_s), "n_genes": exp_s.shape[1],
                "status": "skipped",
            }
            for post_rm in [False, True]
        ]
    except Exception:
        print(f"[{strat}×{imp}×{method_name}] Normalization failed:\n{traceback.format_exc()}")
        return [
            {
                "strat": strat, "imp": imp, "method": method_name,
                "post_rm": post_rm, "harshness": harshness,
                "r2_batch": float("nan"), "r2_diag": float("nan"),
                "n_samples": len(ann_s), "n_genes": exp_s.shape[1],
                "status": "failed",
            }
            for post_rm in [False, True]
        ]

    rows = []
    for post_rm in [False, True]:
        key = s3_key_exp(strat, imp, method_name, post_rm)

        if skip_if_exists and s3_exists(s3, key):
            print(f"[{strat}×{imp}×{method_name}×post_rm={post_rm}] Already exists, skipping.")
            # Still produce a metrics row (fetch would require re-download; use nan as placeholder)
            rows.append({
                "strat": strat, "imp": imp, "method": method_name,
                "post_rm": post_rm, "harshness": harshness,
                "r2_batch": float("nan"), "r2_diag": float("nan"),
                "n_samples": float("nan"), "n_genes": float("nan"),
                "status": "cached",
            })
            continue

        exp_out = exp_norm.copy()
        ann_out = ann_s.copy()

        if post_rm:
            try:
                outliers = identify_outlier_batches(exp_out, ann_out)
                if outliers:
                    ann_out = ann_out[~ann_out[BATCH_COL].isin(outliers)]
                    exp_out = exp_out.loc[ann_out.index]
            except Exception:
                print(f"[{strat}×{imp}×{method_name}×post_rm=True] "
                      f"Post-removal failed:\n{traceback.format_exc()}")

        try:
            r2_b = r2_batch(exp_out, ann_out, batch_col=BATCH_COL)
            r2_d = r2_batch(exp_out, ann_out, batch_col=BIO_COL)
        except Exception:
            r2_b = r2_d = float("nan")

        # Upload expression
        try:
            upload_exp_to_s3(exp_out, s3, key)
            status = "ok"
        except Exception:
            print(f"[{strat}×{imp}×{method_name}] S3 upload failed:\n{traceback.format_exc()}")
            status = "upload_failed"

        rows.append({
            "strat": strat, "imp": imp, "method": method_name,
            "post_rm": post_rm, "harshness": harshness,
            "r2_batch": r2_b, "r2_diag": r2_d,
            "n_samples": len(ann_out), "n_genes": exp_out.shape[1],
            "status": status,
        })

    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strat",   required=True)
    parser.add_argument("--imp",     required=True)
    parser.add_argument("--method",  required=True)
    parser.add_argument("--skip-if-exists", action="store_true")
    parser.add_argument("--out-json", default=None,
                        help="Path to write metric rows as JSON (for dispatcher to collect)")
    args = parser.parse_args()

    comb_exp, comb_ann = load_data()
    filter_strategies  = build_filter_strategies(comb_ann, comb_exp)

    rows = run_job(
        strat=args.strat,
        imp=args.imp,
        method_name=args.method,
        skip_if_exists=args.skip_if_exists,
        comb_exp=comb_exp,
        filter_strategies=filter_strategies,
    )

    # Write metrics as JSON sidecar for the dispatcher to collect
    if args.out_json:
        import json
        with open(args.out_json, "w") as f:
            json.dump(rows, f)
    else:
        for row in rows:
            print(json.dumps(row))

    sys.exit(0)


if __name__ == "__main__":
    main()
```

**Why both post-removal options in one worker:**
Normalization (the expensive step) runs only once. Both `post_rm=False` and `post_rm=True` variants are derived from the same `exp_norm` with cheap post-processing. This halves the number of normalization calls vs. one process per (strat, imp, method, post_rm).

---

## Module 3 — `run_cross_product_parallel.py`

Dispatcher that enumerates all `10 × 4 × 24 = 960` jobs, launches them as subprocesses with a configurable concurrency cap (`--n-workers`), and collects metric rows into a single `metrics.csv` uploaded to S3.

### Key design decisions

| Decision | Rationale |
|---|---|
| `subprocess.Popen` per job, not `multiprocessing.Pool` | rpy2 is not fork-safe; each subprocess gets a clean R session |
| Semaphore-based concurrency cap | Limits CPU/memory usage; prevents RAM OOM on large R sessions (MNN, SVA each use 2–8 GB) |
| `--n-workers 4` default | 4 parallel R sessions fit comfortably in a 32 GB server; raise to 8 for faster run |
| Resume via `--skip-if-exists` | Passes flag to `run_one_job.py`; jobs with existing S3 keys are skipped without re-running normalization |
| Metrics aggregated at the end | Each worker writes a JSON sidecar; dispatcher collects all and uploads `metrics.csv` once |

### Code sketch

```python
# run_cross_product_parallel.py
import argparse, subprocess, os, json, sys, time
import threading
from pathlib import Path
import pandas as pd
import boto3

from bench_shared import S3_BUCKET, S3_PREFIX, s3_key_metrics

# Full grid
STRATEGIES = [
    "S0_no_removal", "A_confirmed_bad", "B_extended_bad", "C_rnaseq_only",
    "D_malignant_only", "E1_iterative_r1", "E2_iterative_r2", "E3_iterative_r3",
    "F_microarray_only", "G_affymetrix_only",
]
IMPUTATION_METHODS = ["strict", "knn", "missforest", "softimpute"]
METHODS = [
    "01_raw", "02_median_scaling", "03_limma", "04_sva",
    "05_combat", "06_combat_seq", "07_pycombat", "08_inmoose_combatseq",
    "09_ruv", "10_mnn", "11_harmony", "12_scanorama", "13_fsmvn",
    "14_qsmooth", "15_fsqn_py", "16_fsqn_r", "17_quantile", "18_rank",
    "19_tdm", "20_shambhala", "21_harmonizr", "22_tmm", "23_vst", "24_peer_k10",
]


def run_dispatcher(n_workers: int, skip_if_exists: bool, tmp_dir: Path):
    jobs = [
        (strat, imp, method)
        for strat  in STRATEGIES
        for imp    in IMPUTATION_METHODS
        for method in METHODS
    ]
    total = len(jobs)
    print(f"Total jobs: {total}  |  Workers: {n_workers}")

    semaphore = threading.Semaphore(n_workers)
    all_rows: list[dict] = []
    lock = threading.Lock()
    done = [0]

    def launch(strat: str, imp: str, method: str) -> None:
        json_path = tmp_dir / f"{strat}__{imp}__{method}.json"
        cmd = [
            sys.executable, "run_one_job.py",
            "--strat",  strat,
            "--imp",    imp,
            "--method", method,
            "--out-json", str(json_path),
        ]
        if skip_if_exists:
            cmd.append("--skip-if-exists")

        t0 = time.time()
        with semaphore:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                cwd=str(Path(__file__).parent),
            )
        elapsed = time.time() - t0

        if proc.returncode != 0:
            print(f"[FAILED {strat}×{imp}×{method}] exit={proc.returncode} "
                  f"({elapsed:.0f}s)\n{proc.stderr[-2000:]}")

        if json_path.exists():
            with open(json_path) as f:
                rows = json.load(f)
            with lock:
                all_rows.extend(rows)
                done[0] += 1
                print(f"  [{done[0]}/{total}] {strat}×{imp}×{method} "
                      f"({elapsed:.0f}s) → {[r['status'] for r in rows]}")

    threads = [threading.Thread(target=launch, args=j, daemon=True) for j in jobs]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return all_rows


def upload_metrics(rows: list[dict]) -> None:
    df = pd.DataFrame(rows)
    csv_bytes = df.to_csv(index=False).encode()
    s3 = boto3.client("s3")
    s3.put_object(Bucket=S3_BUCKET, Key=s3_key_metrics(), Body=csv_bytes)
    print(f"Metrics uploaded: s3://{S3_BUCKET}/{s3_key_metrics()} ({len(df)} rows)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-workers",      type=int, default=4)
    parser.add_argument("--skip-if-exists", action="store_true",
                        help="Skip jobs whose S3 output already exists (for resuming)")
    parser.add_argument("--tmp-dir",        default="/tmp/bench_jobs")
    args = parser.parse_args()

    tmp_dir = Path(args.tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    rows = run_dispatcher(
        n_workers=args.n_workers,
        skip_if_exists=args.skip_if_exists,
        tmp_dir=tmp_dir,
    )
    upload_metrics(rows)


if __name__ == "__main__":
    main()
```

### Estimated runtime

| `--n-workers` | Estimated wall time |
|---|---|
| 1 | ~24 h |
| 4 | ~6–8 h |
| 8 | ~3–4 h |
| 16 | ~2 h |

RAM usage per worker: 2–8 GB (peak for MNN, SVA, HarmonizR). With `--n-workers 4`, expect 8–32 GB total RAM. Do not exceed available RAM.

---

## Module 4 — `load_cross_product_results.py` / notebook cell

After the parallel run completes, the notebook reconstructs `cross_results` from S3.

### What the notebook needs

The notebook cells 40–44 (heatmaps, bar charts, top-K selection, PCA/UMAP comparisons) read from `cross_results`, which maps:
```python
(strat, imp, method, post_rm) -> {
    "exp": pd.DataFrame | None,   # only loaded on demand for top-K
    "ann": pd.DataFrame,
    "r2_batch": float,
    "r2_diag":  float,
    "harshness": str,
}
```

### Lazy-loading strategy

Load metrics eagerly (one CSV, ~200 KB). Load expression DataFrames **lazily** — only when a cell explicitly requests a specific combination (e.g., for PCA/UMAP visualisation of top-K).

```python
# Notebook cell: load results from S3
import boto3, io, gzip
import pandas as pd
import numpy as np
from bench_shared import (
    S3_BUCKET, s3_key_exp, s3_key_metrics,
    download_exp_from_s3,
)

s3 = boto3.client("s3")

# 1. Load metrics summary
metrics_obj = s3.get_object(Bucket=S3_BUCKET, Key=s3_key_metrics())
metrics_df  = pd.read_csv(io.BytesIO(metrics_obj["Body"].read()))

# 2. Reconstruct cross_results dict from metrics (expressions not loaded yet)
cross_results = {}
for _, row in metrics_df.iterrows():
    key = (row["strat"], row["imp"], row["method"], bool(row["post_rm"]))
    cross_results[key] = {
        "exp":       None,               # lazy: load only when needed
        "ann":       None,               # annotation not stored in S3; rebuild from filter
        "r2_batch":  row["r2_batch"],
        "r2_diag":   row["r2_diag"],
        "harshness": row["harshness"],
        "status":    row["status"],
        "n_samples": row.get("n_samples"),
        "n_genes":   row.get("n_genes"),
    }

print(f"Loaded {len(cross_results)} combinations from S3.")
ok_count     = metrics_df[metrics_df["status"] == "ok"].shape[0]
fail_count   = metrics_df[metrics_df["status"] == "failed"].shape[0]
skip_count   = metrics_df[metrics_df["status"] == "skipped"].shape[0]
cached_count = metrics_df[metrics_df["status"] == "cached"].shape[0]
print(f"  ok={ok_count}  failed={fail_count}  skipped={skip_count}  cached={cached_count}")


# 3. Lazy expression loader (call this when a specific combination is needed)
def load_exp(strat: str, imp: str, method: str, post_rm: bool) -> pd.DataFrame | None:
    """Download and cache expression matrix for one combination."""
    key_tuple = (strat, imp, method, post_rm)
    if cross_results[key_tuple]["exp"] is not None:
        return cross_results[key_tuple]["exp"]
    s3_key = s3_key_exp(strat, imp, method, post_rm)
    try:
        exp = download_exp_from_s3(s3, s3_key)
        cross_results[key_tuple]["exp"] = exp
        return exp
    except Exception as e:
        print(f"Could not load {s3_key}: {e}")
        return None


# 4. Load top-K expressions for visualisation
flat_df = metrics_df[metrics_df["status"] == "ok"].sort_values("r2_batch")
top_k   = flat_df.head(15)

for _, row in top_k.iterrows():
    load_exp(row["strat"], row["imp"], row["method"], bool(row["post_rm"]))

print(f"Top-15 expression matrices loaded into cross_results.")
```

---

## Module 5 — METHODS definition in `bench_shared.py`

All normalization functions (currently defined in notebook cells 33–35) must be reproduced verbatim in `bench_shared.py`. The `METHODS` dict is defined at module level so both `run_one_job.py` and the notebook can import it.

```python
# bench_shared.py (continued)

# ... (all normalize_* functions, copied verbatim from cells 33–35) ...

METHODS: dict[str, tuple] = {
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
}
```

**Important:** `bench_shared.py` imports `pandas2ri.activate()` at module level. In each subprocess, this runs fresh — no shared R session with the parent.

---

## Data flow diagram

```
run_cross_product_parallel.py
│
├─ [startup] load_data() + build_filter_strategies()   # once, in dispatcher
│            → writes filter_strategies pickle to /tmp for workers? No.
│            Each worker calls load_data() independently (data is on /uftp, shared)
│
├─ for each (strat, imp, method):
│   └─ subprocess: run_one_job.py --strat A --imp knn --method 05_combat
│       │
│       ├─ load_data()                                 # worker loads data fresh
│       ├─ build_filter_strategies()                   # worker builds strategies
│       ├─ prepare_dataset[_imputed](ann_strat, comb_exp)
│       ├─ log_transform_by_cohort(exp_s, ann_s)
│       ├─ normalize_*(exp_s, ann_s) → exp_norm
│       ├─ [post_rm=False] r2_batch + r2_diag → metrics row
│       ├─ upload_exp_to_s3(exp_norm, key=...post0...)
│       ├─ [post_rm=True]  identify_outlier_batches → remove → r2_batch + r2_diag
│       └─ upload_exp_to_s3(exp_out, key=...post1...)
│
└─ collect all JSON sidecars → upload metrics.csv to S3

harmonization_benchmark.ipynb  (analysis side)
│
├─ [new cell] download metrics.csv from S3 → cross_results dict (lazy exp)
├─ [cell 40] heatmap from cross_results r2_batch/r2_diag values
├─ [cell 41] bar chart
├─ [cell 42] top-K selection → load_exp() for top-15 combinations
└─ [cells 43–44] PCA/UMAP/tSNE on loaded expression matrices
```

---

## Performance notes

### Data loading bottleneck

Each subprocess calls `load_data()` — reading ~7,000 × 18,000 TSV from `/uftp`. This takes ~60–90 s per worker and is the single biggest overhead. With 4 workers, total data-reading time = 4 × 90 s = 6 min (amortized across 240 jobs per worker, negligible).

**Optimization (optional):** Pre-serialize `comb_exp` and `comb_ann` as parquet or pickle to `/tmp/bench_comb_exp.pkl` once in the dispatcher, and have workers load from `/tmp` instead of `/uftp`. This reduces per-worker load time from ~90 s to ~5 s.

```python
# Dispatcher: cache to /tmp before launching workers
import pickle
comb_exp, comb_ann = load_data()
with open("/tmp/bench_comb_exp.pkl", "wb") as f:
    pickle.dump((comb_exp, comb_ann), f, protocol=4)
# Workers: detect and use cache
if os.path.exists("/tmp/bench_comb_exp.pkl"):
    with open("/tmp/bench_comb_exp.pkl", "rb") as f:
        comb_exp, comb_ann = pickle.load(f)
else:
    comb_exp, comb_ann = load_data()
```

### Memory per worker

| Method category | Approx. RAM |
|---|---|
| Pure Python (raw, median, quantile, rank, fsqn_py) | ~0.5 GB |
| Light R (limma, ComBat, qsmooth) | ~1–2 GB |
| Heavy R (SVA, MNN, HarmonizR, TDM) | ~4–8 GB |
| Python ML (harmony, scanorama, inmoose) | ~1–3 GB |

With `--n-workers 4`, peak RAM ~ 4 × 8 GB = 32 GB. Use `--n-workers 2` on machines with <32 GB RAM.

### S3 storage estimate

- Mean expression file: ~5,000 samples × 3,500 genes, float64 → ~140 MB raw, ~30 MB gzip
- Successful combinations: ~1,000–1,200 of 1,920 (after skipping RNA-seq-only + failed methods)
- Total S3 usage: ~1,200 × 30 MB = **~36 GB**

---

## Implementation checklist

```
[x] Create bench_shared.py
    [x] Copy all utility functions from notebook cells 9, 12–17, 22, 30
    [x] Copy all normalize_* functions from cells 33–35
    [x] Define METHODS dict
    [x] Add load_data(), build_filter_strategies()
    [x] Add s3_key_exp(), s3_key_metrics(), upload_exp_to_s3(), download_exp_from_s3(), s3_exists()
    [ ] Test: python -c "from bench_shared import load_data; e, a = load_data(); print(e.shape)"

[x] Create run_one_job.py
    [x] Implement CLI (argparse: --strat, --imp, --method, --skip-if-exists, --out-json)
    [x] Implement run_job() logic
    [ ] Test: python run_one_job.py --strat A_confirmed_bad --imp strict --method 01_raw --out-json /tmp/test.json
    [ ] Verify S3 upload: aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/exp/

[x] Create run_cross_product_parallel.py
    [x] Implement dispatcher with threading.Semaphore
    [x] Implement metrics collection and S3 upload
    [ ] Test with 3 jobs: --n-workers 2 --strats A_confirmed_bad --imps strict --methods 01_raw,02_median_scaling,17_quantile
    [ ] Full run: nohup python run_cross_product_parallel.py --n-workers 4 --skip-if-exists > bench_run.log 2>&1 &

[x] Create load_cross_product_results.py (notebook helper module)
    [x] load_metrics() populates cross_results from S3 metrics.csv
    [x] load_exp() lazy-loads expression matrices on demand
    [x] load_top_k() loads top-K by r2_batch
    [ ] Test: load top-5 combinations, verify shapes match expected
    [ ] Verify heatmap cell works with reconstructed cross_results

[ ] Validate end-to-end
    [ ] Run 1 job manually, check S3 output
    [ ] Load that 1 result in notebook, check r2_batch metric matches notebook output
    [ ] Run all 960 jobs in parallel, check metrics.csv completeness
```

---

## AWS credentials

The scripts use `boto3.client("s3")` which reads credentials from the environment:

```bash
# Ensure these are set before running the dispatcher
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1  # or whichever region the bucket is in
```

Check access:
```bash
aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/ || echo "No prefix yet"
```

---

## Open questions before implementation

1. **Filter strategies are stateful (E1–E3 depend on prior PCA):** `build_filter_strategies()` must run once and produce deterministic annotation DataFrames. The dispatcher should run it once and save the resulting annotation DataFrames (not just the strategy names) so workers get identical filtered sets. Options: pickle the filter_strategies dict to `/tmp`; or have each worker call `build_filter_strategies()` independently (should be deterministic since PCA is seeded and data is fixed).

2. **AWS region and IAM role:** Confirm that the machine running the dispatcher has IAM permissions for `s3:PutObject`, `s3:GetObject`, `s3:HeadObject` on `s3://$FL_S3_BUCKET/FL_batch_correction/*`.

3. **`missforest` and `softimpute` R packages:** Confirm they are installed in the R environment accessible to subprocess workers. Run `Rscript -e "library(missForest); library(softImpute)"` to verify.

4. **Notebook integration:** Decide whether the notebook should continue to support both modes (run cross-product in-notebook OR load from S3). The recommended approach is to keep the original cell 39 but add a new cell before the heatmap that offers to load from S3 if the `--from-s3` flag is set.
