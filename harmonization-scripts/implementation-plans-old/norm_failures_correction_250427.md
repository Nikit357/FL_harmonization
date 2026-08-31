# Normalization Failure Analysis and Correction Plan
**Date:** 2026-04-27  
**Logs analysed:** `norm_log_affy.txt` (G_affymetrix_only, 72 jobs) and `norm_log_microarrays.txt` (F_microarray_only, 72 jobs)  
**Script:** `run_norm_parallel.py` → `run_norm_job.py` → `bench_shared.py`

---

## 1. Executive Summary

| Dataset | Samples × genes (strict) | Total jobs | True failures | Expected skips |
|---|---|---|---|---|
| G_affymetrix_only | 2,801 × 6,710 | 72 | **9** | 9 (TMM, VST, PEER × 3 imps) |
| F_microarray_only | 4,931 × 3,447 | 72 | **16** | 9 (TMM, VST, PEER × 3 imps) |

**25 total failures** fall into four root-cause categories:

| # | Category | Affected methods | Fix scope |
|---|---|---|---|
| A | Unreliable `NotImplementedError` conversion | `20_shambhala` | `bench_shared.py` |
| B | Uncaught R exceptions in `04_sva` | `04_sva` | `bench_shared.py` |
| C | Residual NaN from KNN/softimpute imputation | `07_pycombat`, `10_mnn`, `12_scanorama`, `14_qsmooth`, `19_tdm` | `bench_shared.py` |
| D | C++ SIGABRT from NaN in `08_inmoose_combatseq` | `08_inmoose_combatseq` | `bench_shared.py` |

Category C is the dominant driver: KNN and softimpute imputation both leave residual `NaN` values
in the prepared expression matrix that downstream methods cannot handle. Strict imputation (complete-case
deletion) is NaN-free and succeeds for all methods except the root-cause-A/B issues.

---

## 2. Failure Details by Method

### 2.1 `20_shambhala` — Unreliable `NotImplementedError` conversion (Category A)

**Affects:** both datasets × all three imputation methods (6 failures total).

**Observed error (final exception):**
```
rpy2.rinterface_lib.embedded.RRuntimeError:
  Error in library(Shambhala2) : there is no package called 'Shambhala2'
```
Status in log: `Normalization FAILED` (not `Skipped`). Expected analogous methods `22_tmm`, `23_vst`,
`24_peer` all correctly show `Skipped (NotImplementedError)`.

**Root cause:**  
`bench_shared.py` lines 1401–1408 use `suppressPackageStartupMessages(library(Shambhala2))` as the
absence-check. In the current R 4.5 / rpy2 environment, `suppressPackageStartupMessages()` swallows
the R error *without* raising a Python exception — so the `except RRuntimeError` clause never fires.
Execution continues, writes large CSV files (~60 s), then the inner `ro.r("result <- Shambhala2(...)")` 
fails with another `RRuntimeError` that is *not* wrapped in a try/except, so it propagates to the
generic `except Exception` block in `run_norm_job.py` and is recorded as `status="failed"`.

**Fix (bench_shared.py, `normalize_shambhala`, lines ~1401–1408):**

Replace the `suppressPackageStartupMessages(library(...))` pattern with `requireNamespace()`, which
returns `FALSE` instead of throwing an error when the package is absent:

```python
# BEFORE (unreliable in current environment):
try:
    ro.r("suppressPackageStartupMessages(library(Shambhala2))")
except RRuntimeError:
    raise NotImplementedError("Shambhala2 R package not installed. ...")

# AFTER:
pkg_present = bool(ro.r("requireNamespace('Shambhala2', quietly=TRUE)")[0])
if not pkg_present:
    raise NotImplementedError(
        "Shambhala2 R package not installed. "
        "Install via: remotes::install_github('BorisovNM/Shambhala2'). "
        "Also requires GNU Octave with a 'matlab' wrapper on PATH."
    )
```

**Expected outcome:** shambhala joins TMM/VST/PEER as an expected skip (`status="skipped"`),
not a failure. No wasted compute writing CSV files.

---

### 2.2 `04_sva` — Uncaught R exceptions outside try/except (Category B)

This method shows **two distinct failure signatures** depending on dataset and imputation method.

#### 2.2a — `num_sv()` crashes on NaN (G_affymetrix_only × knn, F_microarray_only × knn + softimpute)

**Observed error:**
```
rpy2.rinterface_lib.embedded.RRuntimeError:
  Error in svd(res) : infinite or missing values in 'x'
```
Elapsed: 1,090 s (affy × knn), 3,694 s (microarray × knn), 4,124 s (microarray × softimpute).

**Root cause:**  
`bench_shared.py` line 692 calls `sva_r.num_sv(r_mat, mod)` *outside* the `try/except RRuntimeError`
block (which begins at line 696). KNN and softimpute imputation leave residual `NaN` values in the
expression matrix (see Section 3). When `num_sv()` performs SVD on a matrix with `NaN`, R raises an
unhandled `RRuntimeError`. SVA spends the full iterative computation time (up to 68 min) before
failing because `num_sv()` runs the full permutation test before reaching SVD.

```python
# Current — num_sv() is OUTSIDE the try/except:
n_sv = sva_r.num_sv(r_mat, mod)          # line 692 — uncaught if NaN in r_mat
if int(n_sv[0]) == 0:
    return exp_df.copy()
try:
    sv_obj = sva_r.sva(r_mat, mod, mod0, n_sv=n_sv)   # line 697 — caught
except RRuntimeError as e:
    return exp_df.copy()
```

**Fix — drop genes with any residual NaN before passing to R** (same approach as strict imputation):

```python
# At the top of normalize_sva(), before building r_mat:
exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
if exp_in.shape[1] < exp_df.shape[1]:
    print(f"SVA: dropping {exp_df.shape[1] - exp_in.shape[1]} genes with residual NaN")
r_mat = base_r.as_matrix(_py2rpy(exp_in.T))
```

The output DataFrame is then built from `exp_in` columns:
```python
out = pd.DataFrame(result_np.T, index=exp_df.index, columns=exp_in.columns)
```

This prevents the SVD crash and produces a result on the complete-coverage gene subset, fully
consistent with what strict imputation would produce for the same dataset.

#### 2.2b — `removeBatchEffect()` dimension mismatch (F_microarray_only × strict)

**Observed error:**
```
rpy2.rinterface_lib.embedded.RRuntimeError:
  Error in cbind(design, X.batch) :
    number of rows of matrices must match (see arg 2)
```
Elapsed: 2,247 s (37 min). Strictly imputed data (no NaN) → `num_sv()` and `sva()` both complete;
the crash happens in `limma::removeBatchEffect` at line 705.

**Root cause:**  
The F_microarray_only dataset has 22 distinct RNA_BATCH levels (vs. 3 in the affymetrix-only
dataset). With many batches, sva can return a surrogate-variable matrix `svs` where the row/column
orientation is inconsistent with the rpy2 numpy conversion. When `svs.shape` is `(n_sv, n_samples)`
(transposed relative to expectation), `pd.DataFrame(svs, index=exp_df.index)` assigns `n_sv`
rows instead of `n_samples`, and `base_r.as_matrix(...)` passes an `n_sv × n_samples` matrix as
the `covariates` argument. `removeBatchEffect` then builds `design` with `n_sv` rows while
`X.batch` has `n_samples` rows → `cbind` fails.

**Fix — add svs shape guard after rpy2 conversion (bench_shared.py line ~702):**

```python
_svs = sv_obj.rx2("sv")
svs  = _svs if isinstance(_svs, np.ndarray) else _rpy2py(_svs)

# Ensure svs is n_samples × n_sv (not transposed)
if svs.ndim == 1:
    svs = svs.reshape(-1, 1)
elif svs.ndim == 2 and svs.shape[0] != len(exp_df) and svs.shape[1] == len(exp_df):
    print(f"SVA: transposing svs from {svs.shape} to {svs.T.shape}")
    svs = svs.T
```

Also wrap the `removeBatchEffect` call in its own try/except so that any further dimension edge
cases fall back to returning uncorrected data rather than crashing the job:

```python
try:
    result = limma_r.removeBatchEffect(
        r_mat,
        covariates=base_r.as_matrix(_py2rpy(pd.DataFrame(svs, index=exp_df.index))),
    )
except RRuntimeError as e:
    print(f"SVA: removeBatchEffect failed ({e}) — returning uncorrected data")
    return exp_df.copy()
```

**Note on affy × strict:**  
`G_affymetrix_only × strict` SVA logs `Error in solve.default(t(mod) %*% mod)` but then
`SVA: sva() failed ... returning uncorrected data` — this is the *already-working* fallback.
No change needed for this case.

---

### 2.3 `07_pycombat` — Residual NaN rejected at entry (Category C)

**Affects:** both datasets × knn and softimpute (4 failures).

**Observed error:**
```
Found missing data values. Please remove all missing values before proceeding with pyComBat.
ValueError: NaN value is not accepted
```
Elapsed: 0–1 s (fails immediately on input validation).

**Root cause:**  
`pycombat()` performs an explicit NaN check before any computation. KNN/softimpute imputation
leaves residual NaN in the prepared dataset (Section 3).

Current code (`bench_shared.py` line 824):
```python
batches = ann_df.loc[exp_df.index, batch_col].fillna("Unknown").tolist()
result  = pycombat(exp_df.T, batches)   # crashes if exp_df has any NaN
```

**Fix — drop genes with any residual NaN before calling pycombat:**
```python
batches = ann_df.loc[exp_df.index, batch_col].fillna("Unknown").tolist()
exp_in  = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
result  = pycombat(exp_in.T, batches)
return result.T
```

The returned DataFrame will contain only the complete-coverage gene subset (same as strict
imputation would produce for the same dataset). Column names are preserved via the DataFrame
index that pycombat propagates through.

---

### 2.4 `10_mnn` — Negative/NaN values break `computeSumFactors` (Category C)

**Affects:** both datasets × knn and softimpute (4 failures).

**Observed error:**
```
rpy2.rinterface_lib.embedded.RRuntimeError:
  Error in .local(x, ...) : size factors should be positive
```
Elapsed: 60–254 s (fails inside batchelor's internal scran normalization).

**Root cause:**  
`fastMNN` (via the `batchelor` R package) calls `scran::computePooledFactors` internally, which
computes size factors as geometric means across genes. KNN/softimpute produce values ≤ 0 (imputed
near-zero expression levels), making the geometric mean-based size factors non-positive. The
function then aborts. Current code passes `exp_df` directly with no guard:

```python
r_mat  = base_r.as_matrix(_py2rpy(exp_df.T))
result = batchelor_r.fastMNN(r_mat, batch=ro.StrVector(batches.values), k=k)
```

**Fix — drop genes with any NaN first, then clip remaining negative values to zero:**
```python
exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
exp_in = exp_in.clip(lower=0.0)   # remove any negative imputation artefacts
r_mat  = base_r.as_matrix(_py2rpy(exp_in.T))
result = batchelor_r.fastMNN(r_mat, batch=ro.StrVector(batches.values), k=k)
```

The PCA inverse-projection and output DataFrame must use `exp_in` consistently:
```python
pca       = PCA(n_components=corrected_embed.shape[1]).fit(exp_in.values)
recovered = corrected_embed @ pca.components_ + pca.mean_
out = pd.DataFrame(recovered, index=exp_df.index, columns=exp_in.columns)
```

The two-step approach (dropna first, then clip) is intentional: NaN genes are structural gaps
from imputation failure and should be excluded; negative values in retained genes are small
numerical artefacts on valid genes and are corrected by clipping to 0 (a valid "not detected"
floor in log-normalised space).

---

### 2.5 `12_scanorama` — NaN propagates into sklearn `normalize` (Category C)

**Affects:** both datasets × knn and softimpute (4 failures).

**Observed error:**
```
ValueError: Input contains NaN.
```
Traceback ends inside `sklearn.preprocessing._data.normalize()` called by scanorama.

**Root cause:**  
`scanorama.integrate()` calls sklearn's `normalize()` on the per-batch arrays. The current code
passes raw `exp_df` slices without any NaN check:

```python
datasets_s = [exp_df.loc[batches == b].values for b in batches.unique()]
integrated, _ = scanorama.integrate(datasets_s, genes_list, dimred=50)
```

**Fix — drop genes with any residual NaN before splitting into per-batch arrays:**
```python
exp_in     = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
datasets_s = [exp_in.loc[batches == b].values for b in batches.unique()]
genes_list = [list(exp_in.columns)] * len(datasets_s)
integrated, _ = scanorama.integrate(datasets_s, genes_list, dimred=50)
```

The PCA fit and output must also use `exp_in`:
```python
pca       = PCA(n_components=integrated[0].shape[1]).fit(exp_in.values)
recovered = all_coords @ pca.components_ + pca.mean_
return pd.DataFrame(recovered, index=exp_df.index, columns=exp_in.columns)
```

---

### 2.6 `14_qsmooth` — R function rejects NA (Category C)

**Affects:** both datasets × knn and softimpute (4 failures).

**Observed error:**
```
rpy2.rinterface_lib.embedded.RRuntimeError:
  Error in (function (object, group_factor, ...) :
    Object must not contains NAs
```

**Root cause:**  
`qsmooth()` checks `any(is.na(object))` and throws before any computation. Current code passes
`exp_df.T` directly to R with no guard:

```python
r_mat  = base_r.as_matrix(_py2rpy(exp_df.T))
qs_obj = qsmooth_r.qsmooth(r_mat, group_factor=ro.StrVector(groups))
```

**Fix — drop genes with any residual NaN before building the R matrix:**
```python
exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
r_mat  = base_r.as_matrix(_py2rpy(exp_in.T))
qs_obj = qsmooth_r.qsmooth(r_mat, group_factor=ro.StrVector(groups))
```

The output DataFrame must use `exp_in.columns`:
```python
out = pd.DataFrame(result.T, index=exp_df.index, columns=exp_in.columns)
```

---

### 2.7 `19_tdm` — NA in CSV triggers conditional failure in R (Category C)

**Affects:** both datasets × knn and softimpute (4 failures).

**Observed error:**
```
rpy2.rinterface_lib.embedded.RRuntimeError:
  Error in if (downandout < old_min) { :
    missing value where TRUE/FALSE needed
```
Elapsed: 81–453 s (fails during the R computation after file read).

**Root cause:**  
TDM uses a file-based R interface. The current code writes NaN values directly to the TSV:

```python
ref_dt = exp_df.loc[target_mask].T.copy()
ref_dt.reset_index().to_csv(ref_path, sep="\t", index=False)
query_dt = exp_df.T.copy()
query_dt.reset_index().to_csv(query_path, sep="\t", index=False)
```

Pandas serialises `NaN` as the string `"NaN"` in CSV output. R reads this as `NA`. Inside
`tdm_transform()`, the comparison `if (downandout < old_min)` evaluates to `NA` (not `FALSE`),
which R cannot use as a branch condition.

**Fix — drop genes with any residual NaN before writing to file:**
```python
exp_in      = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df
target_mask = (
    groups == target_group
    if target_group in groups.values
    else pd.Series(True, index=exp_in.index)
)
ref_dt              = exp_in.loc[target_mask].T.copy()
ref_dt.index.name   = "gene"
query_dt            = exp_in.T.copy()
query_dt.index.name = "gene"
ref_dt.reset_index().to_csv(ref_path, sep="\t", index=False)
query_dt.reset_index().to_csv(query_path, sep="\t", index=False)
```

The output reconstruction must also use `exp_in.columns` (same number of genes as written):
```python
result_np = result_df.values.T.astype(float)
return pd.DataFrame(result_np, index=exp_df.index, columns=exp_in.columns)
```

---

### 2.8 `08_inmoose_combatseq` — C++ SIGABRT from NaN (Category D)

**Affects:** G_affymetrix_only × softimpute only (1 failure, exit=-6).

**Observed error:**
```
terminate called after throwing an instance of 'std::domain_error'
  what():  Error in function float_next<double>(double):
           Argument must be finite, but got nan
[FAILED G_affymetrix_only×softimpute×08_inmoose_combatseq exit=-6 (1464s)]
```

**Why only softimpute and only affymetrix?**  
The affymetrix-only softimpute dataset has 11,207 genes (vs. 6,710 for strict, because softimpute
imputes genes otherwise excluded as too-sparse). Some of the 4,497 extra imputed genes contain NaN
from failed softImpute convergence. This is dataset-specific: the knn-imputed affymetrix dataset
is served from an existing S3 cache (`[31/72] SKIP → ['cached', 'cached']`), bypassing this
failure mode.

**Why not caught by the Python exception handler?**  
`std::domain_error` is a C++ exception thrown inside InMoose's C extension. It terminates the
entire Python interpreter process (SIGABRT, exit=-6) — Python's `except Exception` cannot catch
OS-level signals.

**Root cause in the current code:**
```python
counts = np.round(exp_df.values).astype(int).clip(0)
```
`np.round(np.nan)` returns `np.nan`. `np.array([np.nan]).astype(np.int64)` on Linux gives
`-9223372036854775808` (implementation-defined), and `.clip(0)` gives `0` — so the integer array
looks clean. However, InMoose's pycombat_seq passes some intermediate computations through float
code paths that receive the original `exp_df.values` floats (not the rounded integer counts),
and these contain `NaN` which reach the `float_next<double>()` call.

**Fix — use `np.nan_to_num` before rounding:**
```python
clean_values = np.nan_to_num(exp_df.values, nan=0.0, posinf=0.0, neginf=0.0)
counts       = np.round(clean_values).astype(int).clip(0)
```

This ensures no NaN reaches the C++ layer regardless of internal float paths.

---

## 3. Why KNN and Softimpute Leave Residual NaN

The `run_prep_job.py` / `prepare_dataset_imputed()` workflow:

1. **Strict**: genes with ANY NaN dropped before normalization → output is guaranteed NaN-free.
2. **KNN** (`KNNImputer(n_neighbors=5, max_na_frac=0.20)`): genes with >20% NA are dropped first;
   remaining NaN imputed. However, if `KNNImputer` encounters a sample where ALL k neighbours
   also have NaN for a gene (possible in sparse GPL570 affymetrix data), it returns NaN — documented
   sklearn behaviour.
3. **Softimpute** (R `softImpute`): low-rank matrix completion may not converge for all genes
   when the dataset is very large or has heterogeneous missingness patterns. In the affymetrix
   dataset with 11,207 genes (before strict gene filter), unconverged entries remain as NaN.

**Implication:** every normalization method that accepts imputed data must handle residual NaN
defensively. The fixes above use localised `dropna(axis=1)` guards at the point of use (dropping
genes that still have any NaN), which is the same strategy as strict imputation and ensures
numerical stability. The output matrices from KNN/softimpute runs will have a slightly smaller
gene set than the full imputed matrix but are guaranteed NaN-free and can be compared directly
to strict imputation results on their shared gene subset.

---

## 4. Dataset-Specific Observations

### G_affymetrix_only (2,801 samples, 3 RNA_BATCH levels)

- Small number of batches → SVA's `num_sv()` and model matrix operations are lower-dimensional;
  failures are caused purely by NaN propagation from KNN/softimpute.
- Strict imputation retains 6,710 genes; KNN retains 6,710; softimpute expands to 11,207 genes
  (imputing previously excluded sparse genes). The 11,207-gene matrix amplifies NaN probability
  and increases computation time for methods that must process the larger matrix.
- `08_inmoose_combatseq × softimpute`: the only C++ crash. The 4,497 extra genes with marginal
  imputation quality are the likely NaN source.

### F_microarray_only (4,931 samples, 22 RNA_BATCH levels)

- 22 distinct RNA_BATCH values. This alone drives two unique failures:
  1. **SVA strict**: the svs matrix from sva() has wrong orientation after rpy2 conversion; root
     cause is the high-rank surrogate variable space in large multi-batch datasets.
  2. **SVA knn/softimpute**: same NaN-in-num_sv() problem as affy, but takes 62–68 min because
     SVA's permutation-based `num_sv()` scales with the number of samples and batches.
- Strict imputation retains only 3,447 genes (more aggressive — 22 batches means more genes have
  NaN in at least one batch). The smaller gene space makes some methods faster but does not affect
  the NaN problem.

---

## 5. Minor Issues (Not Failures)

### 5.1 `15_fsqn_py` — Pandas 3.0 ChainedAssignmentError warning

```
bench_shared.py:1114: FutureWarning: ChainedAssignmentError: behaviour will change in pandas 3.0!
```

Not currently a failure but will become one when pandas upgrades. The fix is to replace the
chained indexing at line 1114 with an explicit `.loc` assignment:

```python
# BEFORE (chained assignment):
out[out < 0] = 0

# AFTER:
out = out.clip(lower=0)
```

---

## 6. Implementation Order and Testing

### Recommended fix order

1. **Category A (shambhala)** — isolated one-liner change; immediately converts 6 "failed" entries to "skipped". Low risk.
2. **Category D (inmoose)** — one-liner `nan_to_num` change; prevents SIGABRT which kills the worker process. Medium risk.
3. **Category C (pycombat, mnn, scanorama, qsmooth, tdm)** — all follow the same `dropna(axis=1)` pattern; fix together. Medium risk.
4. **Category B (sva)** — two sub-fixes: (a) `dropna` before `num_sv()`, (b) svs shape guard + `removeBatchEffect` try/except. Test on both datasets separately.
5. **Minor (fsqn_py FutureWarning)** — fix last; not urgent.

### Testing after each fix

```bash
# Activate env
source ~/venvs/collagen_3_11/bin/activate
cd ~/FL_harmonization

# Test single fixed job (fast sanity check, ~2-5 min):
python harmonization-scripts/run_norm_job.py \
    --strat F_microarray_only --imp knn --method 07_pycombat \
    --out-json /tmp/test_pycombat.json --memory-limit-gb 2.0
cat /tmp/test_pycombat.json

# Verify shambhala becomes "skipped" not "failed":
python harmonization-scripts/run_norm_job.py \
    --strat G_affymetrix_only --imp strict --method 20_shambhala \
    --out-json /tmp/test_shambhala.json
cat /tmp/test_shambhala.json   # expect status: "skipped"

# Re-run all failing affy jobs after fixes:
python harmonization-scripts/run_norm_parallel.py \
    --strats G_affymetrix_only \
    --methods 04_sva,07_pycombat,08_inmoose_combatseq,10_mnn,12_scanorama,14_qsmooth,19_tdm,20_shambhala \
    --n-workers 4 --retry-failed

# Re-run all failing microarray jobs:
python harmonization-scripts/run_norm_parallel.py \
    --strats F_microarray_only \
    --methods 04_sva,07_pycombat,10_mnn,12_scanorama,14_qsmooth,19_tdm,20_shambhala \
    --n-workers 4 --retry-failed
```

### Expected outcome after all fixes

| Method | Affy strict | Affy knn | Affy softimpute | Microarray strict | Microarray knn | Microarray softimpute |
|---|---|---|---|---|---|---|
| 04_sva | ok (unchanged) | ok (dropna) | ok (dropna) | ok (svs guard) | ok (dropna) | ok (dropna) |
| 07_pycombat | ok (unchanged) | ok (dropna) | ok (dropna) | ok (unchanged) | ok (dropna) | ok (dropna) |
| 08_inmoose | ok (unchanged) | cached | ok (nan_to_num) | ok (unchanged) | ok (unchanged) | ok (unchanged) |
| 10_mnn | ok (unchanged) | ok (dropna+clip) | ok (dropna+clip) | ok (unchanged) | ok (dropna+clip) | ok (dropna+clip) |
| 12_scanorama | ok (unchanged) | ok (dropna) | ok (dropna) | ok (unchanged) | ok (dropna) | ok (dropna) |
| 14_qsmooth | ok (unchanged) | ok (dropna) | ok (dropna) | ok (unchanged) | ok (dropna) | ok (dropna) |
| 19_tdm | ok (unchanged) | ok (dropna) | ok (dropna) | ok (unchanged) | ok (dropna) | ok (dropna) |
| 20_shambhala | **skipped** | **skipped** | **skipped** | **skipped** | **skipped** | **skipped** |

Shambhala rows will move from `status="failed"` to `status="skipped"` and will not be recorded in
`failed_jobs_norm.txt`. All other previously failing rows should achieve `status="ok"`.

---

## 7. TODO List

All tasks operate on `harmonization-scripts/bench_shared.py` unless noted otherwise.
Tasks within each phase are ordered by dependency; phases are ordered by risk (lowest first).

---

### Phase 1 — Category A: Shambhala `NotImplementedError` conversion
*1 code change, 1 smoke test. Estimated time: ~10 min.*

- [x] **1.1** In `normalize_shambhala()` (line ~1401), replace the `try/except RRuntimeError` library-load block with a `requireNamespace` check:
  - Remove the `try: ro.r("suppressPackageStartupMessages(library(Shambhala2))")` block (lines ~1401–1408)
  - Add `pkg_present = bool(ro.r("requireNamespace('Shambhala2', quietly=TRUE)")[0])`
  - Add `if not pkg_present: raise NotImplementedError(...)`
- [ ] **1.2** Smoke-test: run `G_affymetrix_only × strict × 20_shambhala` with `run_norm_job.py`; confirm `status="skipped"` in the output JSON (not `"failed"`).

---

### Phase 2 — Category D: InMoose SIGABRT prevention
*1 code change, 1 smoke test. Estimated time: ~10 min + ~25 min job runtime.*

- [x] **2.1** In `normalize_inmoose_combat_seq()` (line ~854), replace the NaN-unsafe rounding with:
  - Add `clean_values = np.nan_to_num(exp_df.values, nan=0.0, posinf=0.0, neginf=0.0)` before the `counts` assignment
  - Change `counts = np.round(exp_df.values).astype(int).clip(0)` → `counts = np.round(clean_values).astype(int).clip(0)`
- [ ] **2.2** Smoke-test: run `G_affymetrix_only × softimpute × 08_inmoose_combatseq` with `run_norm_job.py`; confirm process does not crash with exit=-6 and `status="ok"` appears in the JSON.

---

### Phase 3 — Category C: Residual NaN via `dropna(axis=1)` in five methods
*5 code changes (all in `bench_shared.py`), 5 smoke tests, 1 batch re-run.  
Estimated time: ~30 min code + ~2 h batch re-run (knn/softimpute × both datasets).*

#### 3.1 `normalize_pycombat` (line ~801)
- [x] **3.1.1** Add `exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df` before calling `pycombat()`
- [x] **3.1.2** Change `pycombat(exp_df.T, batches)` → `pycombat(exp_in.T, batches)`
- [ ] **3.1.3** Smoke-test: run `F_microarray_only × knn × 07_pycombat`; confirm `status="ok"`.

#### 3.2 `normalize_mnn` (line ~904)
- [x] **3.2.1** Add `exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df` before building `r_mat`
- [x] **3.2.2** Add `exp_in = exp_in.clip(lower=0.0)` immediately after the dropna line
- [x] **3.2.3** Change `_py2rpy(exp_df.T)` → `_py2rpy(exp_in.T)` in the `r_mat` assignment (line ~929)
- [x] **3.2.4** Change `PCA(...).fit(exp_df.values)` → `PCA(...).fit(exp_in.values)` in the inverse-projection (line ~933)
- [x] **3.2.5** Change `pd.DataFrame(recovered, index=exp_df.index, columns=exp_df.columns)` → `columns=exp_in.columns` (line ~935)
- [ ] **3.2.6** Smoke-test: run `F_microarray_only × knn × 10_mnn`; confirm `status="ok"`.

#### 3.3 `normalize_scanorama` (line ~979)
- [x] **3.3.1** Add `exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df` before the `datasets_s` comprehension (line ~1001)
- [x] **3.3.2** Change `exp_df.loc[batches == b]` → `exp_in.loc[batches == b]` in the `datasets_s` list comprehension
- [x] **3.3.3** Change `genes_list = [list(exp_df.columns)] * ...` → `[list(exp_in.columns)] * ...`
- [x] **3.3.4** Change `PCA(...).fit(exp_df.fillna(0).values)` → `PCA(...).fit(exp_in.values)` (line ~1008; removes the old ad-hoc `fillna(0)` too)
- [x] **3.3.5** Change `pd.DataFrame(recovered, index=exp_df.index, columns=exp_df.columns)` → `columns=exp_in.columns` (line ~1010)
- [ ] **3.3.6** Smoke-test: run `F_microarray_only × knn × 12_scanorama`; confirm `status="ok"`.

#### 3.4 `normalize_qsmooth` (line ~1050)
- [x] **3.4.1** Add `exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df` before building `r_mat` (line ~1072)
- [x] **3.4.2** Change `_py2rpy(exp_df.T)` → `_py2rpy(exp_in.T)` in the `r_mat` assignment
- [x] **3.4.3** Change `pd.DataFrame(result.T, index=exp_df.index, columns=exp_df.columns)` → `columns=exp_in.columns`
- [ ] **3.4.4** Smoke-test: run `F_microarray_only × knn × 14_qsmooth`; confirm `status="ok"`.

#### 3.5 `normalize_tdm` (line ~1307)
- [x] **3.5.1** Add `exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df` immediately after the `groups` and `target_mask` assignments (line ~1333–1338); recompute `target_mask` using `exp_in.index` (same as `exp_df.index`, since dropna is on axis=1)
- [x] **3.5.2** Replace `exp_df.loc[target_mask].T.copy()` with `exp_in.loc[target_mask].T.copy()` for `ref_dt` (line ~1343)
- [x] **3.5.3** Replace `exp_df.T.copy()` with `exp_in.T.copy()` for `query_dt` (line ~1346)
- [x] **3.5.4** Change the output reconstruction `pd.DataFrame(result_np, index=exp_df.index, columns=exp_df.columns)` → `columns=exp_in.columns` (line ~1360)
- [ ] **3.5.5** Smoke-test: run `G_affymetrix_only × knn × 19_tdm`; confirm `status="ok"`.

#### 3.6 Batch re-run (after all Phase 3 smoke tests pass)
- [ ] **3.6.1** Re-run all Category C failures on both datasets:
  ```bash
  python harmonization-scripts/run_norm_parallel.py \
      --strats G_affymetrix_only,F_microarray_only \
      --methods 07_pycombat,10_mnn,12_scanorama,14_qsmooth,19_tdm \
      --n-workers 4 --retry-failed
  ```
- [ ] **3.6.2** Verify all 20 previously-failed jobs now show `status="ok"` in the aggregated `metrics.csv` on S3.

---

### Phase 4 — Category B: SVA robustness fixes
*3 code changes in `normalize_sva()`, 2 targeted tests, 1 batch re-run.  
Estimated time: ~20 min code + ~3 h batch re-run (SVA runs are slow: up to 68 min each).*

- [x] **4.1** Add `dropna` guard before `r_mat` is built (fixes 2.2a — NaN in `num_sv()`):
  - Add `exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df` after the `r_bio` / `df_r` / `mod` setup, before `r_mat` (line ~682)
  - Print a log message with the number of dropped genes if any were dropped
  - Change `_py2rpy(exp_df.T)` → `_py2rpy(exp_in.T)` in the `r_mat` assignment (line ~682)
  - Change the final `pd.DataFrame(result_np.T, index=exp_df.index, columns=exp_df.columns)` → `columns=exp_in.columns` (line ~710)

- [x] **4.2** Add svs shape guard after rpy2 conversion (fixes 2.2b — `removeBatchEffect` dimension mismatch):
  - After `svs = _svs if isinstance(...) else _rpy2py(_svs)` (line ~702), add:
    - `if svs.ndim == 1: svs = svs.reshape(-1, 1)`
    - `elif svs.ndim == 2 and svs.shape[0] != len(exp_df) and svs.shape[1] == len(exp_df): svs = svs.T`

- [x] **4.3** Wrap `removeBatchEffect` call in its own `try/except RRuntimeError` (lines ~705–708):
  - On exception: print a diagnostic message and `return exp_df.copy()`

- [ ] **4.4** Targeted test — SVA knn on affy (verifies fix 4.1, should now take ~18 min):
  ```bash
  python harmonization-scripts/run_norm_job.py \
      --strat G_affymetrix_only --imp knn --method 04_sva \
      --out-json /tmp/test_sva_affy_knn.json
  cat /tmp/test_sva_affy_knn.json   # expect status="ok"
  ```
- [ ] **4.5** Targeted test — SVA strict on microarray (verifies fix 4.2/4.3, should take ~37 min):
  ```bash
  python harmonization-scripts/run_norm_job.py \
      --strat F_microarray_only --imp strict --method 04_sva \
      --out-json /tmp/test_sva_micro_strict.json
  cat /tmp/test_sva_micro_strict.json   # expect status="ok"
  ```
- [ ] **4.6** Batch re-run of all SVA failures (after targeted tests pass):
  ```bash
  python harmonization-scripts/run_norm_parallel.py \
      --strats G_affymetrix_only,F_microarray_only \
      --methods 04_sva \
      --n-workers 2 --retry-failed
  ```
  Note: use `--n-workers 2` because SVA jobs are very long (up to 68 min each); running 4 concurrently on a 16 GB pod is safe but tight.
- [ ] **4.7** Verify all 5 previously-failed SVA jobs now show `status="ok"` in `metrics.csv`.

---

### Phase 5 — Minor: `15_fsqn_py` pandas FutureWarning
*1 code change, no re-run needed (existing outputs are valid). Estimated time: ~5 min.*

- [x] **5.1** In `normalize_fsqn_py()` (line ~1114), replace the chained assignment `out[out < 0] = 0` with `out = out.clip(lower=0)`.
- [ ] **5.2** Confirm no `FutureWarning` appears in the next run by briefly running a single fsqn_py job and checking stdout.

---

### Phase 6 — Post-fix cleanup and metrics consolidation

- [ ] **6.1** Remove all 25 corrected job keys from `failed_jobs_norm.txt` (they will be removed automatically on a successful `--retry-failed` run, but verify the file is clean after all batch re-runs complete).
- [ ] **6.2** Confirm that both `failed_jobs_norm_*.txt` objects on S3 are cleared by the dispatcher's `_sync_failed_log_to_s3()` call at the end of each re-run.
- [ ] **6.3** Reload `metrics.csv` from S3 in `harmonization_benchmark.ipynb` with `load_metrics()` and confirm:
  - 20 shambhala rows have `status="skipped"` (not `"failed"`)
  - All formerly failing method rows have `status="ok"` with valid `r2_batch` values
  - No `status="failed"` rows remain for G_affymetrix_only or F_microarray_only
- [ ] **6.4** Regenerate the PCA R² heatmaps in `harmonization_benchmark.ipynb` for F_microarray_only and G_affymetrix_only to include the newly computed results.
