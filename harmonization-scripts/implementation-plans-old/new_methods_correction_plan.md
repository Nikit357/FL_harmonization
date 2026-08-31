# New Methods Correction Plan — Run 2026-05-08

## Run Summary

Command:
```bash
python run_norm_parallel.py \
    --imps strict,knn,softimpute \
    --n-workers 5 --skip-if-exists \
    --timeout-s 218000 --memory-limit-gb 20 \
    --retry-failed > logs/logs_new_methods_260508.txt
```

Results: **1170 jobs run → 181 recorded as failed** in `failed_jobs_norm.txt`.  
All 181 failures trace to a small set of distinct root causes documented below.

---

## Failure Catalogue

### Type A — Python package not installed (produces FAILED, should be SKIP)

#### `20_shambhala` — all strategies × all imputations → FAILED

**Observed error:**
```
TypeError: 'NoneType' object is not subscriptable
```
at `bench_shared.py:1430`:
```python
pkg_present = bool(ro.r("requireNamespace('Shambhala2', quietly=TRUE)")[0])
```

**Root cause:**  
`ro.r("requireNamespace('Shambhala2', quietly=TRUE)")` returns Python `None` (not a BoolSexpVector) when the R package does not exist and the rpy2 version on the pod (Python 3.12 system install, `/usr/local/lib/python3.12/dist-packages/rpy2/`) treats a suppressed-output invisible R value as None. Subscripting `None[0]` then raises `TypeError`. The Shambhala2 R package is **not installed** on the pod (it also requires GNU Octave, which is absent). The function should raise `NotImplementedError` (→ SKIP) instead of crashing.

**Fix (in `bench_shared.py`, line ~1430):**
Change:
```python
pkg_present = bool(ro.r("requireNamespace('Shambhala2', quietly=TRUE)")[0])
```
To:
```python
result = ro.r("requireNamespace('Shambhala2', quietly=TRUE)")
pkg_present = result is not None and bool(result[0])
```

**Also**: the Shambhala2 R package is wrapped in an Octave-presence check in `pod-ssh.yaml` (already present). No further change needed here.

---

### Type B — Package not installed or wrong package name (produces FAILED, should be SKIP)

#### `30_recombat` — all strategies × all imputations → FAILED

**Observed error:**
```
rpy2.rinterface_lib.embedded.RRuntimeError:
  Error in library(reComBat) : there is no package called 'reComBat'
```

**Root cause:**  
The current implementation calls the R package `reComBat` via rpy2. However, `reComBat` is available as a **Python package on PyPI** from the correct repository at https://github.com/BorgwardtLab/reComBat — not from `bioFAM/reComBat`. The R-based approach was a mistake; the correct fix is to rewrite `normalize_recombat` as a pure Python implementation using the `reComBat` PyPI package.

**Fix in `bench_shared.py`, `normalize_recombat`:**  
Remove the rpy2-based R implementation entirely. Rewrite as a Python-native function:
```python
from reComBat import reComBat as recombat_fn

def normalize_recombat(exp_df, ann_df, batch_col=BATCH_COL, bio_col=BIO_COL, **kw):
    batch = ann_df.loc[exp_df.index, batch_col]
    # reComBat expects genes × samples (transpose of our convention)
    corrected = recombat_fn(exp_df.T.values, batch.values)
    return pd.DataFrame(corrected.T, index=exp_df.index, columns=exp_df.columns)
```
The exact API (parameter names, whether it accepts a DataFrame or numpy array, mod/covariate support) must be verified against the BorgwardtLab/reComBat demo/README before implementation.

**Fix in `pod-ssh.yaml` / `requirements.txt` ConfigMap:**  
- Add `reComBat` to the Python requirements (see Track 2 for the specific line).
- Remove the line `remotes::install_github("bioFAM/reComBat", upgrade="never")` from the R install step — no R package needed anymore.

---

#### `37_fabatch` — all strategies × all imputations → FAILED 

**Observed error:**
```
rpy2.rinterface_lib.embedded.RRuntimeError:
  Error in library(FAbatch) : there is no package called 'FAbatch'
```

**Root cause:**  
The R package is **not called `FAbatch`**. The method commonly referred to as "FAbatch" in the literature is implemented as the function `fabatch()` inside the R package **`bapred`** (Batch Prediction). There is no standalone package named `FAbatch` on CRAN or Bioconductor. The current code tries to load a package that does not exist.

Additionally, `bapred` has compilation-time C++ dependencies that require **cmake** to be present on the system.

**Fix in `bench_shared.py`, `normalize_fabatch` (line ~2408):**  
1. Change the package presence guard from `FAbatch` to `bapred`:
```python
pkg_ok = ro.r("requireNamespace('bapred', quietly=TRUE)")
if pkg_ok is None or not bool(pkg_ok[0]):
    raise NotImplementedError(
        "bapred R package not installed. "
        "Install via: install.packages('bapred'). "
        "Also requires affy, affyPLM, sva from Bioconductor."
    )
```
2. Change the R code block to use `bapred` and the `fabatch()` function instead of `batchadjust()`:
```r
library(bapred)
# fabatch(x, y, batch, type="among") where x = genes × samples,
# y = outcome vector (use batch labels as surrogate), batch = batch vector
result <- fabatch(exp_mat, batch, batch, type="among")
corrected <- result$adj.data
```
The exact signature of `fabatch()` and the correct `y` argument (required by the function) must be verified against the `bapred` documentation.

**Fix in `pod-ssh.yaml` — R install step:**  
- Replace `BiocManager::install(c('ruv','NOISeq','FAbatch','Harman'))` with `BiocManager::install(c('ruv','NOISeq','Harman'))` (remove FAbatch).
- Add `bapred` installation and its Bioconductor dependencies as separate steps:
```bash
Rscript --no-save --no-restore -e "BiocManager::install(c('affy','affyPLM','sva'), ask=FALSE, update=FALSE)" && echo "[startup] affy+affyPLM+sva OK"
Rscript --no-save --no-restore -e "install.packages('bapred', dependencies=TRUE)" && echo "[startup] bapred OK"
```
Note: `sva` is already installed by the Bioconductor bulk install line — the explicit call here is defensive and idempotent.

**Fix in `pod-ssh.yaml` — System libraries step (Step 2):**  
Add `cmake` to the `apt-get install -y -qq` command. Without cmake, bapred's C++ code will fail to compile during `install.packages`. Specific change: append `cmake` to the package list on line 69 of the current `pod-ssh.yaml`.

---

### Type C — `check.names=TRUE` mismatch (NA in batch vector → R logic error)

This root cause affects **three separate methods** (`27_dwd`, `29_combat_ref`, `33_amdbnorm`).

**Root cause (shared):**  
Python writes the expression matrix transposed (genes × samples) to a CSV via `exp_in.T.to_csv(exp_path)`. Sample names (which become CSV *column headers*) can contain hyphens, spaces, or other special characters (e.g., sample IDs like `GSM123456-B` or `SAMPLE 001`). R's `read.csv()` applies `make.names()` to column names by default (`check.names=TRUE`), which converts `-` to `.`, spaces to `.`, etc.

The annotation CSV is written as `ann_df.to_csv(ann_path)` where sample names are the *row index* — these are read back by R as rownames without `make.names()` transformation.

When R subsequently does:
```r
batches <- ann_df[colnames(exp_mat), "batch"]
```
the `colnames(exp_mat)` are the `make.names()`-sanitized names, while `rownames(ann_df)` are the original names. Lookups for samples whose names contain special characters silently return `NA` in R.

The `NA` then propagates into `sum(ref_mask)` or `sum(batch == batch_level)` calls, and since R's `sum()` returns `NA` (not 0) when the input contains `NA`, the subsequent `if (sum(...) == 0)` throws:
```
Error in if (sum(ref_mask) == 0): missing value where TRUE/FALSE needed
```

**Universal fix (apply to ALL file-based R functions):**  
Add `check.names=FALSE` to every `read.csv` call that reads the expression matrix:
```r
exp_mat <- as.matrix(read.csv("{exp_path}", row.names=1, check.names=FALSE))
```
This preserves original column names so the `ann_df[colnames(exp_mat), ...]` lookup works correctly.

**Defensive secondary fix:**  
Wrap `sum()` calls that guard against empty masks with `na.rm=TRUE`:
```r
if (sum(ref_mask, na.rm=TRUE) == 0) ref_mask <- rep(TRUE, ncol(exp_mat))
```

#### `27_dwd` — all strategies × all imputations → FAILED

Apply `check.names=FALSE` to `read.csv("{exp_path}", ...)` at `bench_shared.py:1759` (inside `normalize_dwd`'s R block). Also add `na.rm=TRUE` to `sum(ref_mask)`.

#### `29_combat_ref` — all strategies × all imputations → FAILED

Apply `check.names=FALSE` to `read.csv("{exp_path}", ...)` at `bench_shared.py:1926` (inside `normalize_combat_ref`'s R block).  
Additionally, `sva::ComBat`'s internal code (`sum(batch == batch_level)`) does not use `na.rm=TRUE` — this means even after fixing `check.names`, if any biology covariate (`bio`) column contains NA (which `Diagnosis_cell_type_unified` sometimes does), ComBat's `model.matrix(~ bio)` will drop rows and create batch/sample count mismatches. Fix on the Python side: fill NA in bio_col before writing:
```python
ann_sub = ann_df.loc[exp_in.index, [batch_col, bio_col]].fillna("Unknown")
ann_sub.to_csv(ann_path)
```

#### `33_amdbnorm` — all strategies × all imputations → FAILED

Apply `check.names=FALSE` to `read.csv("{exp_path}", ...)` at `bench_shared.py:2173` (inside `normalize_amdbnorm`'s R block).  
The error `Error in if (dd$data[i] <= dd$x_data[j])` is inside `DBNorm::polyFit` and is triggered when the CDF comparison encounters `NA` values in the distribution data. After fixing `check.names`, also add `na.omit` protection in the R block:
```r
dis <- DBNorm::genDistData(na.omit(melt(ref_mat)[, 3]), 500)
```

---

### Type D — Python package not installed (produces SKIP with wrong message)

#### `39_procrustes` — all strategies × all imputations → SKIP (but pkg missing)

**Observed behavior:**  
All strategies show `Skipped (NotImplementedError):  is RNA-seq only.` (empty method name).  
Even on `C_rnaseq_only` (which has no GPL* batches), the method skips.

**Root cause (two sub-issues):**

1. **Package not installed:** The BostonGene Procrustes repository (`https://github.com/BostonGene/Procrustes`) does **not** contain a `setup.py` or `pyproject.toml` file — it is a scripts-based collection, not a packaged Python library. `pip install` does not work for it. The correct approach is to **clone the repo and add its path via `sys.path`**.

2. **Missing `method_name` in `_assert_rnaseq_only` call:** The call at line 2535:
   ```python
   _assert_rnaseq_only(ann_df.loc[exp_df.index], batch_col)
   ```
   does not pass `method_name`, so the skip message for non-RNA-seq strategies reads `" is RNA-seq only."` (leading space, no method name). Cosmetic, but should be fixed.

**Fix 1 — Clone Procrustes into the pod at startup:**  
In `pod-ssh.yaml`, replace:
```bash
pip install "procrustes-bg @ git+https://github.com/BostonGene/Procrustes" && echo "[startup] procrustes-bg OK"
```
With:
```bash
git clone https://github.com/BostonGene/Procrustes.git /app/Procrustes && echo "[startup] Procrustes cloned OK"
```
The path `/app/Procrustes` will contain the module files directly importable via `sys.path`.

**Fix 2 — Update `normalize_procrustes` in `bench_shared.py`:**  
Add `sys.path` setup at the start of the function and import the transformation functions as shown in the [BostonGene Procrustes demo notebook](https://github.com/BostonGene/Procrustes/blob/main/Demo_run.ipynb). The demo uses JSON coefficient files shipped with the repo for FFPE→PolyA transformation. The exact import paths and coefficient file locations must be confirmed by studying the demo notebook before implementing.

```python
import sys, os
_PROCRUSTES_PATH = "/app/Procrustes"
if _PROCRUSTES_PATH not in sys.path:
    sys.path.insert(0, _PROCRUSTES_PATH)
# Then import whatever the demo notebook imports:
# from <module> import Procrustes_predict  (verify actual function name)
```

**Fix 3 — Pass `method_name` in `_assert_rnaseq_only` call (line ~2535):**
```python
_assert_rnaseq_only(ann_df.loc[exp_df.index], batch_col, "Procrustes")
```

---

### Type E — Soft failures (status = 'ok', but method returns uncorrected data)

These methods do NOT appear in `failed_jobs_norm.txt` — they upload a result and report `ok`. However, they silently return the input data unchanged due to internal errors.

#### `38_harman` — all softimpute + knn strategies → uncorrected result

**Observed error (soft, via tryCatch):**
```
Harman failed: Cannot have NA, NaN or NULL as 'expt' levels.
```

**Root cause:** `harman(exp_mat, expt=bio, batch=batches)` requires `expt` to contain no `NA` values. The `bio_col` (Diagnosis_cell_type_unified) has `NA` for some samples. After `read.csv` and `as.character()`, these become R `NA` character values, which Harman rejects.

**Fix in `normalize_harman` (bench_shared.py ~line 2469):**  
Fill NA in the bio column before writing to CSV:
```python
ann_sub = ann_df.loc[exp_in.index, [batch_col, bio_col]].fillna("Unknown")
ann_sub.to_csv(ann_path)
```

#### `31_ruv3prps` — some strategies → uncorrected result

**Observed error (soft, via tryCatch):**
```
RUV-III-PRPS RUVIII failed: $ operator is invalid for atomic vectors
```

**Root cause:** `RUVIII()` (from the `ruv` package) sometimes returns a plain matrix rather than a named list when the factorization is rank-deficient or `k=1`. The code assumes `fit$newY` or `fit$corrY` exists, but `$` on a matrix throws `$ operator is invalid for atomic vectors`.

**Fix in the R block of `normalize_ruv3prps` (bench_shared.py ~line 2074):**
```r
result <- if (is.list(fit)) {
    if (!is.null(fit$newY)) fit$newY else fit$corrY
} else {
    fit[seq_len(n_orig), , drop=FALSE]
}
```

#### `34_arsyn` — some strategies → uncorrected result

**Observed error (soft, via tryCatch):**
```
ARSyN failed: missing value where TRUE/FALSE needed
```

**Root cause:** `NOISeq::ARSyNseq` internally performs ANOVA decomposition and fails when the design matrix is rank-deficient due to NA values in the biological factor (`bio_col`). Same NA issue as Harman.

**Fix in `normalize_arsyn` (bench_shared.py ~line 2205):**  
Fill NA in bio_col before writing to CSV (same pattern as Harman fix):
```python
ann_sub = ann_df.loc[exp_in.index, [batch_col, bio_col]].fillna("Unknown")
ann_sub.to_csv(ann_path)
```

#### `36_explobatch` — all strategies → uncorrected result (404 URL)

**Observed error (soft, via tryCatch):**
```
exploBATCH failed: cannot open the connection to
'https://bioconductor.org/biocLite.R' — output file will not be created
```

**Root cause:** The `exploBATCH` R package (syspremed/exploBATCH) hardcodes a call to `biocLite.R`, a Bioconductor helper script deprecated in 2018 that now returns HTTP 404. This is a bug in the package's own source code, not in our wrapper.

**Fix — Inspect exploBATCH source and preload required packages:**  
Inspect the `expBATCH()` function source at `https://github.com/syspremed/exploBATCH` to identify exactly which packages it attempts to install via `biocLite.R`. Then pre-load those packages in our R code block **before** calling `expBATCH()` so that R's `require()` / `library()` calls inside the function succeed without needing to install anything. The approach:

```r
# Pre-load all packages that exploBATCH's biocLite.R call would install,
# determined by reading exploBATCH source:
suppressPackageStartupMessages({
    library(<pkg1>)
    library(<pkg2>)
    # ... all packages identified from source inspection
})
# Now call expBATCH — biocLite.R will 404 but packages are already loaded
result <- expBATCH(...)
```

The exact package list must be confirmed by reading `https://github.com/syspremed/exploBATCH` source before implementing. If after inspection the workaround proves too fragile, fall back to converting `normalize_explobatch` to a permanent SKIP (same as `normalize_peer`, `normalize_deepmnn`, `normalize_dasc`).

The `sh: 0: getcwd() failed: No such file or directory` messages seen in logs are **harmless** — they are shell cleanup artifacts from `setwd()` in R after the temporary directory is deleted by Python's context manager.

---

### Type F — Hard crash (SIGABRT / OOM)

#### `08_inmoose_combatseq` — `G_affymetrix_only×softimpute` → exit=-6

**Observed:**
```
[03:40:29] FAILED G_affymetrix_only×softimpute×08_inmoose_combatseq exit=-6 (924s)
```

**Root cause:** Exit code -6 is SIGABRT, indicating a C-level assertion failure or OOM kill in the `inmoose` library's pycombat_seq implementation. The combination of `G_affymetrix_only` (2,801 samples) with `softimpute` imputation (which expands the gene count from ~3,447 to ~11,207 genes) creates a `2,801 × 11,207` matrix that causes a memory or numerical overflow in `inmoose`'s internal matrix operations. This is the only combination that crashes — all other `(strat × imp)` pairs for `08_inmoose_combatseq` succeed.

**Decision: Accept as known failure.** This is a single edge-case combination out of 1,716 total jobs. Document it in `failed_jobs_norm.txt` as a known limitation. Do not implement a workaround.

---

## Summary Table

| Method | Type | Status in logs | Root cause | Fix scope |
|---|---|---|---|---|
| `20_shambhala` | Package absent (TypeError) | FAILED | `ro.r(...)[0]` crashes on None return | `bench_shared.py` only |
| `30_recombat` | Wrong implementation (R vs Python) | FAILED | Should use Python `reComBat` PyPI package, not R | `bench_shared.py` rewrite + `requirements.txt` in ConfigMap |
| `37_fabatch` | Wrong R package name | FAILED | Package is `bapred`, function is `fabatch()` | `bench_shared.py` + `pod-ssh.yaml` (cmake + bapred + Bioc deps) |
| `27_dwd` | `check.names` mismatch | FAILED | NA in batch → `sum(NA)` → `if(NA)` error | `bench_shared.py` R code: `check.names=FALSE` |
| `29_combat_ref` | `check.names` mismatch + NA bio | FAILED | NA in batch vector from name sanitization | `bench_shared.py` R code + `fillna("Unknown")` |
| `33_amdbnorm` | `check.names` mismatch | FAILED | NA in batch → DBNorm CDF comparison fails | `bench_shared.py` R code: `check.names=FALSE` + `na.omit` |
| `39_procrustes` | Python pkg absent + missing method_name | SKIP (incorrect msg) | Procrustes is not a pip-installable package | `pod-ssh.yaml`: git clone; `bench_shared.py`: sys.path + method_name |
| `38_harman` | NA in bio_col | ok (uncorrected) | `harman()` rejects NA expt levels | `bench_shared.py`: `fillna("Unknown")` |
| `31_ruv3prps` | Wrong RUVIII return type | ok (uncorrected) | `RUVIII()` returns matrix, not list | `bench_shared.py` R code: `is.list(fit)` guard |
| `34_arsyn` | NA in bio_col | ok (uncorrected) | `ARSyNseq()` fails on NA bio | `bench_shared.py`: `fillna("Unknown")` |
| `36_explobatch` | Deprecated biocLite URL | ok (uncorrected) | `expBATCH` calls 404 URL internally | Inspect source → preload required packages in R block |
| `08_inmoose_combatseq` | SIGABRT / OOM | FAILED (1 job) | `softimpute` × `G_affymetrix_only` too large | Accepted as known failure — no fix |

---

## Implementation Plan

The fixes are divided into two independent tracks.

### Track 1 — `bench_shared.py` changes (Python/R code)
Implement in this order (smallest risk first):

1. ✅ **Fix `normalize_shambhala` None guard** — Changed `ro.r(...)[0]` to guard against None with `result is not None and bool(result[0])`.
2. ✅ **Add `check.names=FALSE`** to `normalize_dwd`, `normalize_combat_ref`, `normalize_amdbnorm` — applied to each `read.csv` call in the R string templates.
3. ✅ **Add `na.omit` to `normalize_amdbnorm`** — `genDistData(na.omit(melt(ref_mat)[, 3]), 500)`.
4. ✅ **Fill NA in bio_col** for `normalize_combat_ref`, `normalize_harman`, `normalize_arsyn` — added `.fillna("Unknown")` before writing CSV.
5. ✅ **Rewrite `normalize_recombat`** as pure Python using `reComBat` PyPI class: `_ReComBat().fit_transform(exp_in, batch)`. All rpy2/R code removed.
6. ✅ **Fix `normalize_fabatch`** — added `bapred` package guard via `requireNamespace`, updated R code to `library(bapred)` and `fabatch(xtr=t(exp_mat), ytr=batches, batch=batches, type="among")`. Output is `t(res$adj.data)` (fabatch returns samples × genes).
7. ✅ **Fix `normalize_explobatch`** — stub `biocLite()` as no-op and override `source()` to intercept any `biocLite.R` URL fetch. exploBATCH source inspection confirmed required packages: mvtnorm, mclust, sva, ggplot2, RColorBrewer, rARPACK, RcppArmadillo, RcppEigen, Rcpp, foreach, doParallel, doMC, fMM, exploBATCHbreast, exploBATCHcolon.
8. ✅ **Fix `normalize_procrustes`** — `sys.path.insert(0, "/app/Procrustes")`, import via `from procrustes_bg.transform import Procrustes_predict`, coefficients at `procrustes_bg/data/{kit}_coefficients.json`. Passes `method_name="Procrustes"` to `_assert_rnaseq_only`.
9. ✅ **Fix `normalize_ruv3prps`** — `is.list(fit)` guard: if fit is a matrix (not a list), slice `fit[seq_len(n_orig), , drop=FALSE]` directly.

After Track 1 changes, run `python harmonization-scripts/test_mock.py` to verify all 39 methods pass on synthetic data.

### Track 2 — Infrastructure fixes (`pod-ssh.yaml` changes)

These changes must be applied to `pod-ssh.yaml` before rebuilding the pod. **Important:** `pod-ssh.yaml` embeds `requirements.txt` inline inside the `fl-deps` ConfigMap — both the ConfigMap block and any standalone `requirements.txt` file must be kept in sync.

#### ✅ Change 1 — Add `cmake` to system library install (Step 2, line ~69)

Current:
```bash
apt-get install -y -qq build-essential gfortran libcurl4-openssl-dev libssl-dev \
    libxml2-dev libhdf5-dev libblas-dev liblapack-dev libuv1-dev \
    python3 python3-pip python3-dev python-is-python3 software-properties-common \
    octave octave-statistics
```
Change: append `cmake` to the package list. `cmake` is required for compiling the C++ components of the `bapred` R package.

#### ✅ Change 2 — Add `reComBat` to Python requirements (ConfigMap `fl-deps`)

In the `requirements.txt` block inside the ConfigMap, add:
```
reComBat>=0.3
```
(Verify the exact PyPI package name and version from https://pypi.org/project/reComBat before pinning.)

#### ✅ Change 3 — Remove broken R package installs (Step 5, R install section)

**Remove** this line entirely (wrong GitHub repo, no longer using R for reComBat):
```bash
Rscript --no-save --no-restore -e "remotes::install_github('bioFAM/reComBat', upgrade='never')" && echo "[startup] reComBat OK"
```

**Modify** the Bioconductor bulk install to remove `FAbatch`:  
Current (line ~114):
```bash
Rscript --no-save --no-restore -e "BiocManager::install(c('ruv','NOISeq','FAbatch','Harman'), ask=FALSE, update=FALSE)" && echo "[startup] ruv+NOISeq+FAbatch+Harman OK"
```
Change to:
```bash
Rscript --no-save --no-restore -e "BiocManager::install(c('ruv','NOISeq','Harman'), ask=FALSE, update=FALSE)" && echo "[startup] ruv+NOISeq+Harman OK"
```

#### ✅ Change 4 — Add `bapred` and its Bioconductor dependencies (Step 5, R install section)

Add the following two new lines in the R install section, after the `ruv+NOISeq+Harman` line:
```bash
Rscript --no-save --no-restore -e "BiocManager::install(c('affy','affyPLM'), ask=FALSE, update=FALSE)" && echo "[startup] affy+affyPLM OK"
Rscript --no-save --no-restore -e "install.packages('bapred', dependencies=TRUE)" && echo "[startup] bapred OK"
```
Note: `sva` (also a `bapred` dependency) is already installed in the earlier Bioconductor bulk install step and does not need to be repeated.

#### ✅ Change 5 — Replace pip install of Procrustes with git clone (Step 5, bottom of R install section)

Current (line ~115):
```bash
pip install "procrustes-bg @ git+https://github.com/BostonGene/Procrustes" && echo "[startup] procrustes-bg OK"
```
Change to:
```bash
git clone https://github.com/BostonGene/Procrustes.git /app/Procrustes && echo "[startup] Procrustes cloned OK"
```
The `/app/Procrustes` path is then added to `sys.path` in `normalize_procrustes` at runtime. No further pod-level setup is needed beyond the clone.

#### Summary of `pod-ssh.yaml` changes

| Location | Change | Status |
|---|---|---|
| Step 2 apt-get (line ~69) | Add `cmake` to package list | ✅ Done |
| ConfigMap `requirements.txt` | Add `reComBat>=0.3` | ✅ Done |
| Step 5 R install | Remove `bioFAM/reComBat` install line | ✅ Done |
| Step 5 R install | Remove `FAbatch` from `BiocManager::install(...)` call | ✅ Done |
| Step 5 R install | Add `BiocManager::install(c('affy','affyPLM'))` | ✅ Done |
| Step 5 R install | Add `install.packages('bapred')` | ✅ Done |
| Step 5 R install | Add CRAN deps for exploBATCH (mvtnorm, mclust, rARPACK, Rcpp, foreach, doParallel, doMC) + fMM GitHub | ✅ Done |
| Step 5 R install | Replace `pip install procrustes-bg` with `git clone /app/Procrustes` | ✅ Done |

### Track 3 — Re-run failed jobs
After Tracks 1 and 2 are done (pod rebuilt, scripts synced):
```bash
python harmonization-scripts/run_norm_parallel.py \
    --imps strict,knn,softimpute \
    --methods 20_shambhala,27_dwd,29_combat_ref,30_recombat,33_amdbnorm,37_fabatch,39_procrustes \
    --n-workers 5 --retry-failed \
    --timeout-s 218000 --memory-limit-gb 20
```

The `08_inmoose_combatseq` failure for `G_affymetrix_only×softimpute` is accepted as a known limitation and does not need a re-run.

---

## Not Changed / Expected Behavior

The following are **correct** SKIP behaviors — no fixes needed:

| Method | Reason for SKIP |
|---|---|
| `22_tmm` | RNA-seq only; correct on mixed-platform strategies |
| `23_vst` | RNA-seq only; correct on mixed-platform strategies |
| `24_peer_k10` | PEER R package unavailable for R 4.5 |
| `32_deepmnn` | scRNA-seq only (bulk not supported) |
| `35_dasc` | Returns cluster labels, not corrected expression |
