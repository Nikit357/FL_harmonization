# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working inside this subdirectory. It covers only what is specific to these scripts; see the root `CLAUDE.md` for project-wide context, dataset description, and general conventions.

For the full `bench_shared.py` reference (39-method registry, filter strategies, S3 key patterns, worker/dispatcher internals), see `project_overview.md`.

---

## Purpose

These scripts implement the **harmonization benchmark cross-product**: 39 batch-correction methods × 14 sample-removal strategies × 4 imputation approaches × 2 post-removal options (original 12-strategy benchmark produced 3,432 S3 outputs; J/K add ~624 more). Scripts run outside Jupyter as CLI subprocesses so each normalization job gets a fresh Python + R session, avoiding rpy2 fork-safety issues and memory accumulation.

---

## Script Roles

### `bench_shared.py` — Shared library
All constants, data-loading, filtering, metric, and normalization logic. Imported by all worker scripts and by `harmonization_benchmark.ipynb`.

### Two-stage pipeline (preferred for K8s)

Separates preparation from normalization so preparation runs once per `(strat, imp)` pair — normalization workers download a small pre-prepared file instead of the full 1.9 GB matrix.

**Stage 1 — Preparation:**
- `run_prep_parallel.py` — dispatcher: enumerates all `(strat × imp)` = 44 pairs, launches `run_prep_job.py` subprocesses, maintains `failed_jobs_prep.txt`
- `run_prep_job.py` — worker: downloads raw data, builds filter strategy, runs imputation, applies `log_transform_by_cohort`, uploads to `prepared/{strat}__{imp}__exp.tsv.gz` + `...__ann.tsv.gz`

**Stage 2 — Normalization:**
- `run_norm_parallel.py` — dispatcher: enumerates all 1,716 `(strat × imp × method)` combinations, launches `run_norm_job.py` subprocesses, maintains `failed_jobs_norm.txt`
- `run_norm_job.py` — worker: downloads the prepared pair, runs one normalization method, uploads `post0` / `post1` variants, writes JSON metrics sidecar

### Monolithic pipeline (legacy / local debugging)
- `run_cross_product_parallel.py` — dispatcher: full 1,716-job grid in one stage (each worker re-downloads and re-imputes from raw). Simpler but slower.
- `run_one_job.py` — worker: downloads raw data, builds strategy, runs imputation + normalization in one process

### Support scripts
- `load_cross_product_results.py` — notebook helper: `load_metrics()`, `load_exp()`, `load_top_k()` with lazy S3 caching via the `cross_results` global dict
- `test_mock.py` — smoke test on a synthetic 80-sample × 200-gene dataset; exit code 0 = all PASS/SKIP
- `make_slides.py` — generates `supervisor_slides_*.pptx` from a `.md` plan via python-pptx; not part of the benchmark pipeline
- `harmonization-tools-research/` — per-tool evaluation notes (Angel, COCONUT, HARP, MatchMixeR, Shambhala, etc.) that informed the method registry. Read before adding or removing methods.

---

## Local Development Machine

**Daniil's local Mac repo root:** `~/fl_subset/`

When syncing edits to the K8s pod (port-forward must be active on `localhost:2222`):

```bash
# Sync entire harmonization-scripts directory to the pod
rsync -avz --progress -e "ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" ~/fl_subset/harmonization-scripts/ root@localhost:/app/harmonization-scripts/

# Sync a single file
rsync -avz -e "ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" ~/fl_subset/harmonization-scripts/bench_shared.py root@localhost:/app/harmonization-scripts/bench_shared.py
```

Note: edits on JupyterHub (`~/FL_harmonization/harmonization-scripts/`) are **not** automatically reflected on the local Mac or the pod — sync manually.

---

## Running the Scripts

All scripts must be run from the **project root** with the project venv active, **or** from inside the Docker container (WORKDIR `/app/harmonization-scripts`).

```bash
source ~/venvs/collagen_3_11/bin/activate

# ── Two-stage pipeline (K8s recommended) ───────────────────────────────────

# Stage 1: prepare all (strat × imp) = 44 pairs
nohup python harmonization-scripts/run_prep_parallel.py \
    --n-workers 4 --skip-if-exists \
    --timeout-s 7200 --memory-limit-gb 6.0 > prep_run.log 2>&1 &

# Stage 2: normalize all available prepared pairs (1,716 jobs)
nohup python harmonization-scripts/run_norm_parallel.py \
    --n-workers 6 --skip-if-exists > norm_run.log 2>&1 &

# Stage 2 targeted subset:
python harmonization-scripts/run_norm_parallel.py \
    --strats A_confirmed_bad --imps strict \
    --methods 01_raw,16_fsqn_r,17_quantile \
    --n-workers 4 --skip-if-exists

# ── Monolithic pipeline (local debugging) ──────────────────────────────────

nohup python harmonization-scripts/run_cross_product_parallel.py \
    --n-workers 2 --skip-if-exists > bench_run.log 2>&1 &

# Single job (debugging a specific method)
python harmonization-scripts/run_one_job.py \
    --strat A_confirmed_bad \
    --imp strict \
    --method 16_fsqn_r \
    --out-json /tmp/test_result.json \
    --memory-limit-gb 2.0

# ── Smoke test ──────────────────────────────────────────────────────────────
python harmonization-scripts/test_mock.py
```

---

## `bench_shared.py` — Key Reference

### Key constants

| Name | Value | Purpose |
|---|---|---|
| `BIO_COL` | `"Diagnosis_cell_type_unified"` | Default biology column |
| `BATCH_COL` | `"RNA_BATCH"` | Default batch column |
| `S3_BUCKET` | `"$FL_S3_BUCKET"` | S3 bucket for all I/O |
| `S3_PREFIX` | `"FL_batch_correction"` | S3 key prefix |
| `S3_EXP_KEY` | `"FL_batch_correction/exp/comb_exp.tsv"` | Expression input; overridable via `BENCH_EXP_S3_KEY` env var |
| `S3_ANN_KEY` | `"FL_batch_correction/exp/comb_ann_unified.csv"` | Annotation input; overridable via `BENCH_ANN_S3_KEY` env var |

### Key function signatures

```python
comb_exp, comb_ann = load_data(cache_path="/tmp/bench_comb_data.pkl")
exp = log_transform_by_cohort(exp_df, ann_df, batch_col="COHORT_LABEL", threshold=30)
strategies = build_filter_strategies(comb_ann, comb_exp)  # dict of 14 labeled annotation DataFrames
exp, ann = prepare_dataset(ann_filter, exp_full)           # strict: dropna → full coverage
exp, ann = prepare_dataset_imputed(ann_filter, exp_full, method="knn")  # knn / softimpute
r2 = pca_variance_explained_by_batch(exp_df, batch_series, n_components=10)
r2 = r2_batch(exp_df, ann_df, batch_col=BATCH_COL, n_pcs=10)  # convenience wrapper
key = s3_key_exp(strat, imp, method, post_rm)   # "FL_batch_correction/exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz"
key = s3_key_prepared_exp(strat, imp)           # "FL_batch_correction/prepared/{strat}__{imp}__exp.tsv.gz"
upload_exp_to_s3(exp_df, s3_client, key)
exp_df = download_exp_from_s3(s3_client, key)
exists = s3_exists(s3_client, key)              # HEAD request; no download
```

---

## Key Dependencies

| Package | Where used |
|---|---|
| `rpy2` | All R-based normalization methods and imputation |
| `boto3`, `botocore` | All S3 I/O |
| `psutil` | Memory guards in dispatcher and worker |
| `pandas`, `numpy` | Core data structures |
| `sklearn` (PCA, StandardScaler, KNNImputer) | Metrics, imputation, embedding methods |
| `harmonypy` | `normalize_harmony` |
| `scanorama` | `normalize_scanorama` |
| `combat.pycombat` | `normalize_pycombat` |
| `inmoose.pycombat` | `normalize_inmoose_combat_seq` |
| `reComBat` | `normalize_recombat`; PyPI `reComBat>=0.3` |
| R: `limma`, `sva`, `batchelor`, `RUVSeq`, `qsmooth`, `FSQN`, `TDM`, `HarmonizR`, `missForest`, `softImpute`, `edgeR`, `DESeq2` | Normalization and imputation |

### Procrustes import note

Procrustes (BostonGene) **cannot be installed via pip** (no `setup.py`). It is handled by:
1. `git clone https://github.com/BostonGene/Procrustes.git /app/Procrustes` at pod startup (step 5 in `pod-ssh.yaml`)
2. `bench_shared.py:normalize_procrustes` inserts `/app/Procrustes` into `sys.path` at call time

Do **not** add a `procrustes-bg @ git+...` entry to `requirements.txt` — it will fail with "does not appear to be a Python project".

---

## Docker Image

The benchmark runs in a self-contained Docker image (`fl-batch-correction`): Python 3.11, R 4.5, all Python and R packages.

| File | Purpose |
|---|---|
| `Dockerfile` | `python:3.11-slim` base + R 4.5 from CRAN apt repo (`bookworm-cran40`) + all packages |
| `requirements.txt` | Python dependency pins. **No Procrustes entry** — handled by git clone + sys.path |
| `install_r_packages.R` | R package installer run during Docker build |

```bash
cd ~/B_cell_lymphomas

docker build --tag fl-batch-correction:latest --file harmonization-scripts/Dockerfile .
docker run --rm -v "$HOME/.aws:/root/.aws:ro" fl-batch-correction:latest python test_mock.py

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/fl-batch-correction"
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin "$ECR_URI"
docker tag fl-batch-correction:latest "${ECR_URI}:latest"
docker push "${ECR_URI}:latest"
```

Key facts: CRAN apt repo `bookworm-cran40` ships R 4.5.3; GPG key `95C0FAF38DB3CCAD0C080A7BDC78B2DDEABC47B7`; `softImpute::complete()` returns a numpy array in R 4.5/rpy2 3.5.5 — handled by `isinstance` guard in `bench_shared.py`.

---

## Kubernetes Deployment

The current pod is `ubuntu:24.04`-based (no pre-built Docker image needed). Init script in `k8s/pod-ssh.yaml` installs Python + R 4.5 at startup. **First startup takes ~30–40 minutes**. SSH server starts within ~2 minutes. Pod prints `[startup] Environment ready.` when safe to run scripts.

**R version:** rpy2 3.6.x requires **R 4.5.x**. `noble-cran40` began serving R 4.6.0 on 2026-04-24; rpy2 3.6.7 has a C-level ABI incompatibility with R 4.6.0. Startup script pins R 4.5.x via Posit standalone binary (`cdn.posit.co/r/ubuntu-2404/pkgs/r-4.5.3_1_amd64.deb`). Verify: `Rscript -e "cat(R.version$version.string)"` — must report `4.5.x`.

**Python venv:** `/app/venv` is Python 3.11 (required: `reComBat 0.1.4` requires `pandas<2.0`; pandas 1.5.3 has a py3.11 wheel only). Activate manually in non-login shells: `source /app/venv/bin/activate`.

### Known startup failures and fixes

| Symptom | Root cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'numpy'` | Venv not active or connected before step 4 | `source /app/venv/bin/activate`; or wait for `[startup] Environment ready.` |
| `externally-managed-environment` | Using system pip | Use `/app/venv/bin/pip install` |
| `procrustes-bg ... does not appear to be a Python project` | Old `requirements.txt` had pip entry | Removed; Procrustes installed via git clone + sys.path |
| `git clone` for Procrustes fails silently | `git` missing from step 2 | Fixed: `git` added to apt-get install list |
| Segfault in `33_amdbnorm` | R 4.6.0 / rpy2 ABI mismatch | Fixed: step 3 installs Posit `r-4.5.3_1_amd64.deb`; pins with `apt-mark hold` |
| `DWD failed: unused argument (penalty = "auto")` | `DWDLargeR::genDWD` removed `penalty` argument | Fixed: removed from `normalize_dwd` in `bench_shared.py:1843` |
| `WARNING: FSQN or qsmooth verification failed` | `Hmisc` compile failed; `libpng-dev` absent | Fixed: `libpng-dev zlib1g-dev` added; qsmooth deps pre-installed; `force=TRUE` added |
| `36_explobatch` R error: missing package `fMM` | GitHub repo `maxkuhn/fMM` deleted | Fixed: `normalize_explobatch` raises `NotImplementedError` → clean SKIP |
| `ResolutionImpossible` during pip | `reComBat` requires `pandas<2.0`; old ConfigMap had `pandas>=2.0` | Fixed: Python 3.11 venv; constraint `pandas>=1.3.4,<2.0.0` |

For full SSH setup, VSCode Remote-SSH, and rsync workflow see **`k8s/README.md`**.

### Manifest files
| File | Purpose |
|---|---|
| `k8s/pod-ssh.yaml` | Primary pod spec; embeds `requirements.txt` and `install_r_packages.R` — keep in sync |
| `k8s/aws-credentials-secret.yaml` | Reference-only Secret structure |
| `create_pvc.yaml` | 100 GiB PVC `fl-workspace` for `/workspace` |
| `k8s/pod.yaml` | Older ECR-image-based pod spec (kept for reference) |

### Deploy and run
```bash
kubectl create secret generic aws-credentials \
    --from-file=credentials=$HOME/.aws/credentials \
    --from-file=config=$HOME/.aws/config \
    --namespace ${K8S_NAMESPACE}

kubectl apply -f harmonization-scripts/k8s/pod-ssh.yaml -n ${K8S_NAMESPACE}
kubectl logs -f fl-batch-correction -n ${K8S_NAMESPACE}  # wait for "Environment ready."
ssh fl-pod  # see k8s/README.md for ~/.ssh/config setup

# Inside the pod:
cd /app/harmonization-scripts && python test_mock.py
nohup python run_prep_parallel.py --n-workers 4 --skip-if-exists \
    --timeout-s 7200 --memory-limit-gb 6.0 > /workspace/prep.log 2>&1 &
nohup python run_norm_parallel.py --n-workers 6 --skip-if-exists > /workspace/norm.log 2>&1 &
```

ECR: `${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/fl-batch-correction` (us-east-1)

S3 input data (upload before first pod run):
```bash
aws s3 cp comb_exp.tsv         s3://$FL_S3_BUCKET/FL_batch_correction/exp/comb_exp.tsv
aws s3 cp comb_ann_unified.csv s3://$FL_S3_BUCKET/FL_batch_correction/exp/comb_ann_unified.csv
```

---

## Extending the Benchmark

**Adding a new normalization method:**
1. Implement `normalize_<name>(exp_df, ann_df, **kw) -> pd.DataFrame` in `bench_shared.py`
2. Add it to `METHODS` with a key like `"40_<name>"` and a harshness tier
3. Add the key to `ALL_METHODS` in **both** `run_cross_product_parallel.py` and `run_norm_parallel.py` — independent lists that must be kept in sync

**Adding a new filter strategy:**
1. Compute the filtered `ann_df` inside `build_filter_strategies()`
2. Add it to the `strategies` dict with a descriptive key
3. Update `ALL_STRATEGIES` in both dispatcher scripts

**Resuming a partial run:**
```bash
python harmonization-scripts/run_prep_parallel.py --n-workers 4 --skip-if-exists
python harmonization-scripts/run_norm_parallel.py --n-workers 6 --skip-if-exists
```
Each worker checks S3 with a HEAD request and exits in under 1 second when output already exists.
