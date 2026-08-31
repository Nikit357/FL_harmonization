# Skill: python-scripts

Complete reference for the four harmonization benchmark Python scripts.

---

## Overview

The four scripts implement a systematic batch-correction benchmark: 24 methods × 10 strategies × 4 imputation approaches × 2 post-removal variants = 1,920 S3 output matrices.

```
bench_shared.py          — shared library: constants, data loading, normalization, metrics, S3 I/O
run_one_job.py           — single worker: one (strat × imp × method) combination
run_cross_product_parallel.py  — dispatcher: ThreadPoolExecutor over the full grid
load_cross_product_results.py  — notebook helper: lazy S3 download + caching
test_mock.py             — smoke test: all 24 methods + 4 imputation on synthetic data
```

---

## `bench_shared.py`

### Constants

```python
BIO_COL   = "Diagnosis_cell_type_unified"
BATCH_COL = "RNA_BATCH"
S3_BUCKET = "$FL_S3_BUCKET"
S3_PREFIX = "FL_batch_correction"

# S3 keys for input data (overridable via env vars)
S3_EXP_KEY = os.environ.get("BENCH_EXP_S3_KEY", "FL_batch_correction/exp/comb_exp.tsv")
S3_ANN_KEY = os.environ.get("BENCH_ANN_S3_KEY", "FL_batch_correction/exp/comb_ann_unified.csv")

RARE_GROUPS    = [5 subtypes excluded from all analysis]
NORMAL_GROUPS  = [11 normal B-cell types; used in strategy D]
BAD_BATCHES_A  = [3 FFPE microarray batches]     # strategy A
BAD_BATCHES_B  = BAD_BATCHES_A + [8 more]        # strategy B
BAD_COHORTS_A/B = ["SOM"]
```

### `load_data(cache_path="/tmp/bench_comb_data.pkl")`

Downloads `comb_exp.tsv` (~1.9 GB) and `comb_ann_unified.csv` (~7 MB) from S3. Auto-detects `.gz` compression. Adds derived columns (`Diagnosis_with_coo`, `Diagnosis_unified_with_coo`), patches one cohort's RNA_BATCH, intersects and deduplicates samples. Pickles to `/tmp/bench_comb_data.pkl` (~5 s reload vs ~90 s from S3).

```python
comb_exp, comb_ann = load_data()
```

### `build_filter_strategies(comb_ann, comb_exp)`

Returns `dict[str, pd.DataFrame]` — 10 named annotation subsets. Results cached to `/tmp/bench_filter_strategies.pkl`.

| Key | Description |
|---|---|
| `S0_no_removal` | All samples (after rare-group removal) |
| `A_confirmed_bad` | Exclude BAD_BATCHES_A + SOM |
| `B_extended_bad` | Exclude BAD_BATCHES_B + SOM |
| `C_rnaseq_only` | RNA-seq batches only |
| `D_malignant_only` | Tumor samples only |
| `E1_iterative_r1` | A + 1 PCA-outlier batch removed |
| `E2_iterative_r2` | E1 + 1 more |
| `E3_iterative_r3` | E2 + 1 more |
| `F_microarray_only` | Microarray batches only |
| `G_affymetrix_only` | GPL570 batches only |

### `prepare_dataset(ann_filter, exp_full)`

Strict: drops all genes with any NA. Returns `(exp, ann)` with full-coverage matrix.

### `prepare_dataset_imputed(ann_filter, exp_full, method, knn_k=5, max_na_frac=0.20)`

Imputation methods: `"knn"` (sklearn KNNImputer), `"missforest"` (R missForest via rpy2), `"softimpute"` (R softImpute via rpy2). Drops genes with > `max_na_frac` NA before imputing.

### Batch effect metric

```python
r2 = pca_variance_explained_by_batch(exp_df, batch_series, n_components=10)
# One-way ANOVA R² averaged across first 10 PCs. Range 0–1; lower is better.
# Baseline ~0.95 (raw), best achieved ~0.16 (FSQN R)

r2 = r2_batch(exp_df, ann_df, batch_col=BATCH_COL, n_pcs=10)
# Convenience wrapper
```

### S3 I/O

```python
key = s3_key_exp(strat, imp, method, post_rm)
# → "FL_batch_correction/exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz"

key = s3_key_metrics()
# → "FL_batch_correction/metrics.csv"

exists = s3_exists(s3_client, key)          # HEAD request only
upload_exp_to_s3(exp_df, s3_client, key)    # gzip TSV in-memory
exp_df = download_exp_from_s3(s3_client, key)
```

### `METHODS` registry

Dict mapping key → `(normalize_fn, harshness_tier)`. All functions have signature `fn(exp_df, ann_df, **kw) → pd.DataFrame`.

| Key | Tier | Notes |
|---|---|---|
| `01_raw` | low | Passthrough |
| `02_median_scaling` | low | Per-batch median shift |
| `03_limma` | low | `limma::removeBatchEffect` via rpy2 |
| `04_sva` | low | SVA; falls back to uncorrected if 0 SVs |
| `05_combat` | medium | ComBat EB; biology covariate |
| `06_combat_seq` | medium | ComBat-seq; rounds to integer counts |
| `07_pycombat` | medium | Python port |
| `08_inmoose_combatseq` | medium | `pycombat_seq` via inmoose |
| `09_ruv` | medium | RUVg; 10 housekeeping genes |
| `10_mnn` | medium | fastMNN; inverse-projected embedding |
| `11_harmony` | medium | Harmony; PCA-space correction |
| `12_scanorama` | medium | Scanorama; embedding inverse-projected |
| `13_fsmvn` | medium | Feature-specific mean-variance; negative control |
| `14_qsmooth` | high | qsmooth via R |
| `15_fsqn_py` | high | FSQN Python re-implementation |
| `16_fsqn_r` | high | FSQN R package ★ best result (r2≈0.16) |
| `17_quantile` | high | Standard quantile normalization |
| `18_rank` | high | Fractional rank per sample |
| `19_tdm` | high | TDM via R (file-based interface) |
| `20_shambhala` | high | `NotImplementedError` (repo unavailable) |
| `21_harmonizr` | medium | HarmonizR NA-aware ComBat/limma |
| `22_tmm` | low | TMM via edgeR; RNA-seq only |
| `23_vst` | low | DESeq2 VST; RNA-seq only |
| `24_peer_k10` | medium | `NotImplementedError` (PEER unavailable R 4.5) |

RNA-seq-only guard: `22_tmm` and `23_vst` raise `NotImplementedError` if any `GPL*` batch is present. The dispatcher treats this as a skip, not a failure.

File-based R interface (used by `fsqn_r`, `tdm`, `harmonizr`): expression written to a `tempfile.TemporaryDirectory()`, R reads/writes files inside it, Python reads back the result.

---

## `run_one_job.py`

### CLI

```
python run_one_job.py
    --strat           <strategy key>        required
    --imp             <imputation method>   required
    --method          <normalization key>   required
    --out-json        <path>                required
    --skip-if-exists                        skip if both S3 keys exist
    --memory-limit-gb <float>              startup RAM check (default: 4.0)
```

### Memory safety sequence

1. `_check_memory(min_free_gb)` at startup — exits code 2 if insufficient
2. `load_data()` from pickle cache
3. `_check_memory(min_free_gb / 2)` after load
4. `del comb_ann; gc.collect()` after building filter strategies
5. `del exp_s; gc.collect()` after normalization
6. `del exp_out, ann_out; gc.collect()` after each post_rm variant
7. `del exp_norm; gc.collect()` after both variants
8. `_r_gc()` inside each R normalization function

### Fast-path skip

If `--skip-if-exists` and both S3 keys exist, writes `status="cached"` rows to JSON and exits without loading data.

### Output JSON format

```json
[
  {"strat": "A_confirmed_bad", "imp": "strict", "method": "16_fsqn_r",
   "post_rm": false, "harshness": "high",
   "r2_batch": 0.162, "r2_diag": 0.089,
   "n_samples": 5123, "n_genes": 3520, "status": "ok"},
  {"strat": "A_confirmed_bad", "imp": "strict", "method": "16_fsqn_r",
   "post_rm": true, "harshness": "high", ...}
]
```

`status`: `"ok"`, `"skipped"` (NotImplementedError), `"failed"` (other exception), `"cached"` (S3 already existed), `"upload_failed"`.

---

## `run_cross_product_parallel.py`

### Full grid

```python
ALL_STRATEGIES = 10   # S0, A, B, C, D, E1, E2, E3, F, G
ALL_IMPUTATION = 4    # strict, knn, missforest, softimpute
ALL_METHODS    = 24   # 01_raw … 24_peer_k10
# → 960 jobs × 2 post_rm = 1,920 S3 outputs
```

### CLI

| Flag | Default | Description |
|---|---|---|
| `--n-workers` | 2 | Max parallel subprocesses |
| `--skip-if-exists` | False | Skip jobs with existing S3 output |
| `--retry-failed` | False | Ignore failed_jobs.txt skip filter; remove successful retries |
| `--timeout-s` | 3600 | Kill subprocess after N seconds; use 7200 for missforest/softimpute |
| `--memory-limit-gb` | 4.0 | Dispatcher pause threshold (workers get threshold/2) |
| `--no-precache` | False | Skip pre-caching dispatcher copies |
| `--tmp-dir` | `/tmp/bench_jobs` | JSON sidecar directory |
| `--strats` | all | Comma-separated strategy subset |
| `--imps` | all | Comma-separated imputation subset |
| `--methods` | all | Comma-separated method subset |

### Key functions

```python
run_dispatcher(strategies, imputation_methods, methods, n_workers, skip_if_exists,
               tmp_dir, skip_keys, timeout_s, memory_limit_gb)
    → tuple[list[dict], set[str], set[str]]
    # Returns (all_rows, newly_failed_keys, newly_succeeded_keys)

_classify_job_outcome(rc, rows) → "ok" | "skipped" | "failed"
    # "skipped" = NotImplementedError only (not a real failure)
    # "failed"  = crash, timeout (rc=-9), OOM (rc=2), exception, upload error

_sync_failed_log_from_s3()   # merge all previous pods' failed_jobs_*.txt from S3
_sync_failed_log_to_s3(keys) # upload this pod's log; delete object if empty
upload_metrics(rows)         # aggregate to DataFrame → S3 metrics.csv
```

### Failed-jobs log

- Local: `failed_jobs.txt` next to script; one `strat__imp__method` per line
- S3: `FL_batch_correction/failed_jobs_{POD_NAME}.txt` per pod
- On startup: S3 files from all prior pods are merged into the local log
- On shutdown: local log uploaded to S3 (object deleted on clean run)
- `POD_NAME` from `$POD_NAME` env var (default: `"local"`)

---

## `load_cross_product_results.py`

### Global state

```python
cross_results: dict[tuple[str, str, str, bool], dict] = {}
# key = (strat, imp, method, post_rm)
# value = {r2_batch, r2_diag, harshness, status, n_samples, n_genes, exp=None}
```

### Functions

```python
metrics_df = load_metrics()
# Downloads FL_batch_correction/metrics.csv; populates cross_results

exp_df = load_exp(strat, imp, method, post_rm=False)
# Downloads expression matrix; cached in cross_results[key]["exp"]

top_k_df = load_top_k(metrics_df, k=15, sort_by="r2_batch")
# Loads top-k ok-status combinations by ascending r2_batch; returns metrics subset
```

Module-level `_s3` boto3 client created at import time.

---

## `test_mock.py`

Synthetic dataset: 80 samples × 200 genes, 3 batches, 2 diagnoses. Uses `+2.0` offset to ensure non-zero values for `normalize_vst`. Runs all 24 normalization methods and 4 imputation methods. Exit code 0 on all PASS/SKIP (expected: 22 PASS, 2 SKIP for shambhala/PEER).

```bash
# Run inside Docker container or local venv:
python test_mock.py
```

---

## Data flow

```
S3 (comb_exp.tsv, comb_ann_unified.csv)
    ↓ load_data()  [cache: /tmp/bench_comb_data.pkl]
    ↓ build_filter_strategies()  [cache: /tmp/bench_filter_strategies.pkl]
    ↓ prepare_dataset() / prepare_dataset_imputed()
    ↓ normalize_*(exp_df, ann_df)
    ↓ [optional] post-normalization outlier removal
    ↓ upload_exp_to_s3()  → S3 {strat}__{imp}__{method}__post{0|1}.tsv.gz
    ↓ r2_batch() metric
    ↓ JSON sidecar  →  metrics.csv on S3
```
