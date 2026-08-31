# harmonization-scripts

Batch-correction benchmark for the FL lymphoma dissertation.
Evaluates **39 normalization methods × 12 sample-removal strategies × 4 imputation approaches × 2 post-removal options = 3,744 S3 outputs**.

All scripts must be run from the **project root** with the Python virtual environment active:

```bash
source ~/venvs/collagen_3_11/bin/activate
```

---

## Prerequisites

| Requirement | Details |
|---|---|
| Python venv | `~/venvs/collagen_3_11/` (Python 3.11) |
| AWS credentials | `~/.aws/credentials` with access to `$FL_S3_BUCKET` S3 bucket |
| Input data on S3 | `FL_batch_correction/exp/comb_exp.tsv` (~1.9 GB) and `comb_ann_unified.csv` — upload once before first run |
| R 4.5.x + Bioconductor | Required on the K8s pod; see `k8s/README.md` for setup |

---

## Script roles

| Script | Stage | Role |
|---|---|---|
| `bench_shared.py` | Library | All constants, data-loading, filter strategies, imputation, 39 normalization methods, S3 helpers, metrics |
| `run_prep_parallel.py` | Stage 1 dispatcher | Enumerates all 48 `(strategy × imputation)` pairs; launches `run_prep_job.py` workers in parallel |
| `run_prep_job.py` | Stage 1 worker | Downloads raw data → builds filter strategy → imputes → uploads prepared pair to S3 |
| `run_norm_parallel.py` | Stage 2 dispatcher | Enumerates all 1,872 `(strategy × imputation × method)` combinations; launches `run_norm_job.py` workers |
| `run_norm_job.py` | Stage 2 worker | Downloads prepared pair → runs one normalization method → uploads `post0` and `post1` variants |
| `run_cross_product_parallel.py` | Monolithic dispatcher | Legacy single-stage pipeline: each worker re-downloads raw data and runs imputation + normalization |
| `run_one_job.py` | Single-job worker | Runs one `(strategy, imputation, method)` combination; useful for debugging |
| `load_cross_product_results.py` | Notebook helper | `load_metrics()`, `load_exp()`, `load_top_k()` — lazy S3 caching for analysis notebooks |
| `test_mock.py` | Smoke test | Runs all 39 methods on a synthetic 80-sample × 200-gene dataset; exit code 0 = all PASS/SKIP |
| `make_slides.py` | Presentation | Generates `supervisor_slides_*.pptx` from a markdown plan via python-pptx |

---

## Quick start

### Two-stage pipeline (recommended for K8s)

Preparation runs once per `(strategy, imputation)` pair and uploads compact files to S3. Normalization workers download only the pre-prepared ~600 MB file for their pair.

```bash
# Stage 1 — prepare all 48 (strategy × imputation) pairs
nohup python harmonization-scripts/run_prep_parallel.py \
    --n-workers 4 --skip-if-exists \
    --timeout-s 7200 --memory-limit-gb 6.0 > prep_run.log 2>&1 &

# Stage 2 — normalize all available prepared pairs (1,872 jobs)
nohup python harmonization-scripts/run_norm_parallel.py \
    --n-workers 6 --skip-if-exists > norm_run.log 2>&1 &
```

Run a targeted subset (useful for testing a single strategy):

```bash
python harmonization-scripts/run_norm_parallel.py \
    --strats I_rare_batches_removed --imps strict \
    --methods 01_raw,16_fsqn_r,10_mnn \
    --n-workers 3 --skip-if-exists
```

### Monolithic pipeline (local debugging)

Each worker re-downloads and re-imputes from raw data. Slower but simpler for small targeted runs.

```bash
nohup python harmonization-scripts/run_cross_product_parallel.py \
    --n-workers 2 --skip-if-exists > bench_run.log 2>&1 &
```

### Single job (debugging one method)

```bash
python harmonization-scripts/run_one_job.py \
    --strat A_confirmed_bad --imp strict --method 16_fsqn_r \
    --out-json /tmp/test_result.json
```

### Smoke test

```bash
python harmonization-scripts/test_mock.py
```

---

## Sample-removal strategies

`build_filter_strategies()` in `bench_shared.py` produces a dict of 12 labeled annotation DataFrames.

| Key | Samples kept | Description |
|---|---|---|
| `S0_no_removal` | ~6,000 | All samples; only rare diagnosis groups excluded |
| `A_confirmed_bad` | 5,444 | Exclude 3 confirmed bad FFPE microarray batches + SOM cohort |
| `B_extended_bad` | ~4,700 | Exclude 11 batches + SOM cohort (superset of A) |
| `C_rnaseq_only` | 2,386 | RNA-seq batches only; removes cross-platform challenge |
| `D_malignant_only` | 4,444 | Tumor samples only; no normal B cells |
| `E1_iterative_r1` | 5,350 | A + 1 data-driven PCA-outlier batch removed |
| `E2_iterative_r2` | ~5,300 | E1 + 1 more PCA-outlier batch removed |
| `E3_iterative_r3` | 5,256 | E2 + 1 more PCA-outlier batch removed |
| `F_microarray_only` | 4,825 | Microarray batches only; intra-platform test |
| `G_affymetrix_only` | 2,824 | GPL570 Affymetrix batches only |
| `H_affymetrix_extended` | ~3,800 | All Affymetrix batch labels (wider than G) |
| `I_rare_batches_removed` | ~5,100 | Only batches with ≥ 50 samples (`MIN_BATCH_SIZE`); removes 15 small batches |

The threshold for `I_rare_batches_removed` is computed dynamically from `ann_base[RNA_BATCH].value_counts()`, not from a hardcoded list. Delete `/tmp/bench_filter_strategies.pkl` on the pod before running this strategy for the first time.

---

## S3 output structure

```
FL_batch_correction/
  exp/
    comb_exp.tsv                           # raw expression input (~1.9 GB)
    comb_ann_unified.csv                   # annotation input
    {strat}__{imp}__{method}__post0.tsv.gz # normalized output, no outlier removal
    {strat}__{imp}__{method}__post1.tsv.gz # normalized output, with outlier removal
  prepared/
    {strat}__{imp}__exp.tsv.gz             # Stage 1 output: imputed expression
    {strat}__{imp}__ann.tsv.gz             # Stage 1 output: filtered annotation
  metrics/
    {strat}__{imp}__{method}__post{0|1}__metrics.json  # per-job metric sidecar
```

---

## Extending the benchmark

**Adding a new normalization method:**
1. Implement `normalize_<name>(exp_df, ann_df, **kw) -> pd.DataFrame` in `bench_shared.py`.
2. Add an entry to the `METHODS` dict with a key like `"40_<name>"` and a harshness tier.
3. Append the key to `ALL_METHODS` in both `run_cross_product_parallel.py` and `run_norm_parallel.py` (these are independent lists kept in sync manually).

**Adding a new filter strategy:**
1. Compute the filtered annotation DataFrame inside `build_filter_strategies()` in `bench_shared.py`.
2. Add the key and DataFrame to the `strategies` dict.
3. Append the key to `ALL_STRATEGIES` in `run_prep_parallel.py`, `run_norm_parallel.py`, and `run_cross_product_parallel.py`.
4. Update docstrings, counts, and documentation in `CLAUDE.md` and `project_overview.md`.

**Resuming a partial run:**
Each worker checks S3 with a HEAD request (`--skip-if-exists`) and exits in under 1 second when the output already exists. Re-run the same dispatcher command to pick up where you left off.

---

## Troubleshooting

For known pod startup failures (R version mismatch, missing packages, Procrustes install issues, etc.) see the **Known startup failures** table in `CLAUDE.md`. For K8s deployment, SSH setup, and rsync workflow see `k8s/README.md`.
