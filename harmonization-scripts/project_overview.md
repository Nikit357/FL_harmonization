# Project Overview — Harmonization Scripts

Detailed reference for `bench_shared.py` internals, worker/dispatcher behavior, and the notebook helper. Operational guidance (commands, Docker, K8s) lives in `CLAUDE.md`.

---

## `bench_shared.py` — Detailed Reference

### Constants

| Name | Value | Purpose |
|---|---|---|
| `BIO_COL` | `"Diagnosis_cell_type_unified"` | Default biology column |
| `BATCH_COL` | `"RNA_BATCH"` | Default batch column |
| `S3_BUCKET` | `"$FL_S3_BUCKET"` | S3 bucket for all I/O |
| `S3_PREFIX` | `"FL_batch_correction"` | S3 key prefix |
| `S3_EXP_KEY` | `"FL_batch_correction/exp/comb_exp.tsv"` | S3 key for expression input; overridable via `BENCH_EXP_S3_KEY` env var |
| `S3_ANN_KEY` | `"FL_batch_correction/exp/comb_ann_unified.csv"` | S3 key for annotation input; overridable via `BENCH_ANN_S3_KEY` env var |
| `RARE_GROUPS` | 5 lymphoma subtypes | Always excluded before any analysis |
| `NORMAL_GROUPS` | 11 normal B-cell types | Used to define malignant-only strategy D |
| `BAD_BATCHES_A` | 3 FFPE microarray batches | Strategy A exclusions |
| `BAD_BATCHES_B` | 11 batches | Strategy B exclusions (superset of A) |
| `BAD_COHORTS_A/B` | `["SOM"]` | SOM cohort excluded from all benchmarks |

### Data loading and caching

```python
comb_exp, comb_ann = load_data(cache_path="/tmp/bench_comb_data.pkl")
```

- Downloads `comb_exp.tsv` (~1.9 GB) and `comb_ann_unified.csv` (~7 MB) from S3
- Adds derived columns: `Diagnosis_with_coo`, `Diagnosis_unified_with_coo`
- Patches one cohort's RNA_BATCH (`PUB_Suntsova_GSE120795` → `RNASeq_FF_Unknown`)
- Intersects samples between expression and annotation; deduplicates index
- Pickles to `/tmp/bench_comb_data.pkl` on first call; subsequent calls load from cache (~5 s vs ~90 s from S3)

### Log transformation

```python
exp = log_transform_by_cohort(exp_df, ann_df, batch_col="COHORT_LABEL", threshold=30)
```

Applied during Stage 1 preparation (after imputation, before upload). Applies `log2(x+1)` per cohort only when that cohort's max value exceeds `threshold=30` — cohorts already in log space are left unchanged.

### Filter strategies

`build_filter_strategies(comb_ann, comb_exp)` returns a dict of 14 named annotation DataFrames:

| Key | Description |
|---|---|
| `S0_no_removal` | All samples (after rare-group removal only) |
| `A_confirmed_bad` | Exclude `BAD_BATCHES_A` + SOM cohort |
| `B_extended_bad` | Exclude `BAD_BATCHES_B` + SOM cohort |
| `C_rnaseq_only` | RNA-seq batches only |
| `D_malignant_only` | Tumor samples only (no normal B cells) |
| `E1_iterative_r1` | A + 1 PCA-outlier batch removed |
| `E2_iterative_r2` | E1 + 1 more PCA-outlier batch removed |
| `E3_iterative_r3` | E2 + 1 more PCA-outlier batch removed |
| `F_microarray_only` | Microarray batches only |
| `G_affymetrix_only` | GPL570 batches only (`RNA_BATCH.startswith("GPL570")`); ~2,824 samples — name is a misnomer vs. actual code; left unchanged to preserve existing S3 keys |
| `H_affymetrix_extended` | All 13 Affymetrix microarray batches (~3,821 samples; excludes GPL14951 which is Illumina HumanHT-12 V3.0) |
| `J_ff_only`             | Keep only batches where `RNA_BATCH` contains `_FF_` (fresh frozen; RNA-seq and microarray) |
| `K_ffpe_only`           | Keep only batches where `RNA_BATCH` contains `_FFPE_` (FFPE; includes `RNASeq_FFPE_Exome_capture` 929 samples and microarray FFPE) |

E1–E3 require running `identify_outlier_batches()` iteratively; results are cached to `/tmp/bench_filter_strategies.pkl`.

### Dataset preparation

```python
exp, ann = prepare_dataset(ann_filter, exp_full)
# Strict: drops all genes with any NA → guaranteed full-coverage matrix

exp, ann = prepare_dataset_imputed(ann_filter, exp_full, method="knn", knn_k=5, max_na_frac=0.20)
# Imputation methods: "knn" (sklearn KNNImputer), "missforest" (R missForest via rpy2),
#                    "softimpute" (R softImpute via rpy2)
# Drops genes with > max_na_frac NA before imputing
```

**KNN and softimpute may leave residual NaN** (genes where all samples in a batch are NaN). All normalization functions guard against this with `exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df`.

### Batch effect metric

```python
r2 = pca_variance_explained_by_batch(exp_df, batch_series, n_components=10)
# One-way ANOVA R² averaged across first 10 PCs
# R² = SS_between / SS_total per PC, then mean

r2 = r2_batch(exp_df, ann_df, batch_col=BATCH_COL, n_pcs=10)  # convenience wrapper
```

Ranges 0–1; lower is better. Baseline (raw) ≈ 0.95; best achieved ≈ 0.16. **Angel exception:** `25_angel` returns a reduced gene space (platform-stable genes only) — its R² is not directly comparable with other methods.

### S3 I/O

```python
# ── Normalized output keys (Stage 2) ─────────────────────────────────────────
key = s3_key_exp(strat, imp, method, post_rm)
# → "FL_batch_correction/exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz"

key = s3_key_metrics()   # → "FL_batch_correction/metrics.csv"

upload_exp_to_s3(exp_df, s3_client, key)
exp_df = download_exp_from_s3(s3_client, key)

# ── Prepared dataset keys (Stage 1) ──────────────────────────────────────────
key = s3_key_prepared_exp(strat, imp)
# → "FL_batch_correction/prepared/{strat}__{imp}__exp.tsv.gz"

key = s3_key_prepared_ann(strat, imp)
# → "FL_batch_correction/prepared/{strat}__{imp}__ann.tsv.gz"

upload_ann_to_s3(ann_df, s3_client, key)
ann_df = download_ann_from_s3(s3_client, key)

# ── Stage 1 aggregate metrics ─────────────────────────────────────────────────
key = s3_key_prep_metrics()   # → "FL_batch_correction/prep_metrics.csv"

# ── Utilities ─────────────────────────────────────────────────────────────────
exists = s3_exists(s3_client, key)   # HEAD request; no download
```

### Normalization functions — full registry

All functions share the signature `fn(exp_df, ann_df, **kw) → pd.DataFrame`.

| Key | Function | Tier | Notes |
|---|---|---|---|
| `01_raw` | `normalize_raw` | low | Passthrough; absolute baseline |
| `02_median_scaling` | `normalize_median_scaling` | low | Per-batch median shift to global median |
| `03_limma` | `normalize_limma` | low | `limma::removeBatchEffect` via rpy2 |
| `04_sva` | `normalize_sva` | low | SVA (Leek & Storey 2012); falls back to uncorrected if 0 SVs detected |
| `05_combat` | `normalize_combat` | medium | ComBat EB; uses biology covariate in model |
| `06_combat_seq` | `normalize_combat_seq` | medium | ComBat-seq; rounds to integer counts |
| `07_pycombat` | `normalize_pycombat` | medium | Python port via `combat` package |
| `08_inmoose_combatseq` | `normalize_inmoose_combat_seq` | medium | `pycombat_seq` via `inmoose` package |
| `09_ruv` | `normalize_ruv` | medium | RUVg; 10 housekeeping genes as negative controls |
| `10_mnn` | `normalize_mnn` | medium | fastMNN; corrected embedding inverse-projected |
| `11_harmony` | `normalize_harmony` | medium | Harmony; PCA-space correction, inverse-projected |
| `12_scanorama` | `normalize_scanorama` | medium | Scanorama; embedding inverse-projected |
| `13_fsmvn` | `normalize_fsmvn` | medium | Feature-specific mean-variance normalization; negative control |
| `14_qsmooth` | `normalize_qsmooth` | high | qsmooth via R |
| `15_fsqn_py` | `normalize_fsqn_py` | high | FSQN Python re-implementation |
| `16_fsqn_r` | `normalize_fsqn_r` | high | FSQN R package (Franks et al. 2018). CRITICAL: expects SAMPLES × GENES. Each non-reference batch normalised independently; reference kept unchanged. Fallback: if `RNASeq_FF_PolyA` absent, uses all samples as reference. |
| `17_quantile` | `normalize_quantile` | high | Standard quantile normalization |
| `18_rank` | `normalize_rank` | high | Fractional rank per sample (platform-independent) |
| `19_tdm` | `normalize_tdm` | high | TDM; file-based R interface |
| `20_shambhala` | `normalize_shambhala` | high | Shambhala2; CuBlock + quantile norm; file-based R + Octave |
| `21_harmonizr` | `normalize_harmonizr` | medium | HarmonizR; NA-aware ComBat/limma via temp files |
| `22_tmm` | `normalize_tmm` | low | TMM via edgeR; **RNA-seq only** (raises `NotImplementedError` on mixed data) |
| `23_vst` | `normalize_vst` | low | DESeq2 VST; **RNA-seq only** |
| `24_peer_k10` | `normalize_peer` | medium | Raises `NotImplementedError` (PEER unavailable for R 4.5) |
| `25_angel` | `normalize_angel` | high | Rank [0,1] + per-gene platform-variance filter; reduced gene space |
| `26_xpn` | `normalize_xpn` | high | XPN; pure Python percentile interpolation per-gene per-batch toward reference |
| `27_dwd` | `normalize_dwd` | medium | DWD; `DWDLargeR::genDWD`; file-based R; iterative per-batch projection |
| `28_npn` | `normalize_npn` | high | NPN nonparanormal transform; `huge::npn(func="truncation")`; file-based R |
| `29_combat_ref` | `normalize_combat_ref` | medium | ComBat with `ref.batch="RNASeq_FF_PolyA"`; preserves reference batch distribution |
| `30_recombat` | `normalize_recombat` | medium | reComBat; `reComBat::reComBat(dat, batch, mod)`; file-based R |
| `31_ruv3prps` | `normalize_ruv3prps` | medium | RUV-III-PRPS; `ruv::RUVIII()` with pseudo-samples; k_factors=5; file-based R |
| `32_deepmnn` | `normalize_deepmnn` | medium | Raises `NotImplementedError` (scRNA-seq only; not applicable to bulk) |
| `33_amdbnorm` | `normalize_amdbnorm` | high | AMDBNorm 3-step: `DBNorm::genDistData` → `polyFit` → `AMDBNorm()`; file-based R |
| `34_arsyn` | `normalize_arsyn` | medium | ARSyNseq; `NOISeq::readData()` + `ARSyNseq()`; file-based R |
| `35_dasc` | `normalize_dasc` | medium | Raises `NotImplementedError` (DASC returns cluster assignments, not expression) |
| `36_explobatch` | `normalize_explobatch` | medium | Raises `NotImplementedError` (fMM dependency deleted from GitHub) |
| `37_fabatch` | `normalize_fabatch` | medium | FAbatch `batchadjust(y, batch, type="among")`; file-based R |
| `38_harman` | `normalize_harman` | medium | Harman; `harman(data, expt=bio, batch=batch, limit=0.1)` then `reconstructData(pc)`; file-based R |
| `39_procrustes` | `normalize_procrustes` | high | Procrustes (BostonGene); RNA-seq only; `Procrustes_predict()` with V7 coefficients |

**RNA-seq-only guard**: `normalize_tmm`, `normalize_vst`, and `normalize_procrustes` call `_assert_rnaseq_only()` which raises `NotImplementedError` if any `GPL*` batch is present. Treated as a skip, not a failure.

**Permanent-skip methods**: `24_peer_k10`, `32_deepmnn`, `35_dasc`, `36_explobatch` — recorded as SKIP in metrics.

**File-based R interface pattern** (used by `fsqn_r`, `tdm`, `harmonizr`, `dwd`, `npn`, `combat_ref`, `recombat`, `ruv3prps`, `amdbnorm`, `arsyn`, `fabatch`, `harman`): expression is written to a `tempfile.TemporaryDirectory()`, R reads and writes files inside it, Python reads back the result.

---

## `run_one_job.py` — Worker Details

### Memory safety sequence
1. `_check_memory(min_free_gb)` at startup — exits with code 2 if RAM insufficient
2. `load_data()` — loads from pickle cache if available
3. `_check_memory(min_free_gb / 2)` after load
4. `del comb_ann; gc.collect()` after building filter strategies
5. `del exp_s; gc.collect()` after normalization
6. `del exp_out, ann_out; gc.collect()` after each post_rm variant
7. `del exp_norm; gc.collect()` after both variants are done
8. R heap freed via `_r_gc()` inside each normalization function

### Fast-path skip
If `--skip-if-exists` is set and **both** S3 keys (post_rm=False and post_rm=True) already exist, the worker writes cached-status rows to the JSON sidecar and exits without loading any data.

### Output format
The `--out-json` file contains a JSON array with **2 rows** (one per post_rm option):
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

`status` is one of: `"ok"`, `"skipped"` (NotImplementedError), `"failed"` (other exception), `"cached"` (S3 already existed), `"upload_failed"`.

---

## `run_cross_product_parallel.py` — Dispatcher Details

### Grid defaults
```python
ALL_STRATEGIES  = 14  # S0, A, B, C, D, E1, E2, E3, F, G, H, I, J, K
ALL_IMPUTATION  = 4   # strict, knn, missforest, softimpute
ALL_METHODS     = 39  # 01_raw … 39_procrustes
# Total: 14 × 4 × 39 = 2,184 jobs → 4,368 S3 outputs (before SKIPs)
```

### CLI arguments
| Flag | Default | Description |
|---|---|---|
| `--n-workers` | 2 | Max parallel subprocesses |
| `--skip-if-exists` | False | Skip jobs whose S3 output already exists |
| `--retry-failed` | False | Retry jobs in `failed_jobs.txt`; remove from log on success |
| `--timeout-s` | 3600 | Kill subprocess after N seconds; use 7200 for missforest/softimpute |
| `--memory-limit-gb` | 4.0 | Three-level RAM safety guard |
| `--no-precache` | False | Skip pre-caching (useful when cache already exists) |
| `--tmp-dir` | `/tmp/bench_jobs` | Directory for JSON sidecar files |
| `--strats` / `--imps` / `--methods` | all | Comma-separated subsets of the full grid |

### Concurrency model
`ThreadPoolExecutor(max_workers=n_workers)` — each thread calls `subprocess.run(["python", "run_one_job.py", ...])`. This avoids rpy2 fork-safety issues; each subprocess has its own R session.

### Memory guard (three-level)
| Level | Where | Threshold | Action on breach |
|---|---|---|---|
| 1 | Dispatcher | `--memory-limit-gb` | Block next launch; poll every 30 s |
| 2 | Worker startup | threshold / 2 | Exit code 2 before loading data |
| 3 | Worker post-load | threshold / 4 | Exit code 2 after `load_data()` |

### Failed-jobs log
- Local file `failed_jobs.txt` — one `strat__imp__method` key per line
- **Recorded** when: subprocess crash, timeout (rc=-9), OOM (rc=2), normalization exception, S3 upload error
- **Not recorded** when: `NotImplementedError` — treated as expected skip
- S3 per-pod sync: on startup merges all `failed_jobs_*.txt` objects from S3; on shutdown uploads this pod's log to `{S3_PREFIX}/failed_jobs_{POD_NAME}.txt`

### Metrics aggregation
All JSON sidecars from completed workers are collected, converted to a `pd.DataFrame`, and uploaded as `FL_batch_correction/metrics.csv` to S3 at the end of the run.

---

## `load_cross_product_results.py` — Notebook Helper Details

### Global state
```python
cross_results: dict[tuple[str, str, str, bool], dict] = {}
```
Populated by `load_metrics()`. Each value holds `r2_batch`, `r2_diag`, `harshness`, `status`, `n_samples`, `n_genes`, and `exp=None` (filled lazily by `load_exp()`).

### Usage pattern
```python
metrics_df = load_metrics()                        # populates cross_results from S3
exp = load_exp("A_confirmed_bad", "strict", "16_fsqn_r", post_rm=False)
# Second call returns cached DataFrame without re-downloading

top15 = load_top_k(metrics_df, k=15, sort_by="r2_batch")
# Loads top-15 ok-status combinations ranked by ascending r2_batch
```

The `_s3` boto3 client is module-level, created at import time. If AWS credentials are not configured, `load_metrics()` will fail at runtime.
