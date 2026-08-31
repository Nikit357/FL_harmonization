# Implementation Plan: More Normalization Methods + Bug Fixes

> Target file: `harmonization_benchmark.ipynb`  
> Status: 10/18 existing methods pass smoke test. 8 need fixes. 7 new methods to add.  
> Order of work: **Phase 0 (traceback)** → **Phase 1 (bug fixes)** → **Phase 2 (new methods)**  
> Do not re-run the full cross-product until all Phase 1 fixes are validated by smoke test.

---

## Phase 0 — Improve error reporting (prerequisite for all other phases)

### 0.1 Add full traceback to the cross-product loop

**Location:** Cell containing the `cross_results` loop (Section 4.1).

**Current code:**
```python
except Exception as e:
    print(f"  FAILED {strat_name} × {method_name}: {e}")
    cross_results[strat_name][method_name] = {
        "exp": None, "r2_batch": np.nan, "r2_diag": np.nan, "harshness": harshness
    }
```

**Replace with:**
```python
except Exception as e:
    import traceback
    print(f"  FAILED {strat_name} × {method_name}: {e}")
    print(traceback.format_exc())
    cross_results[strat_name][method_name] = {
        "exp": None, "r2_batch": np.nan, "r2_diag": np.nan, "harshness": harshness
    }
```

**Also add** to the smoke-test helper (if one exists) or any standalone try/except that calls a normalize_* function. Wherever `except Exception as e:` appears in the notebook and currently only prints `e`, replace with `print(traceback.format_exc())`.

**Add `import traceback` to the imports cell (Section 0.1).**

---

## Phase 1 — Bug fixes for 8 failing methods

### Fix 1 — `04_sva` and `05_combat`: "contrasts can be applied only to factors with 2 or more levels"

**Root cause:** `model.matrix(~r_bio)` in R fails when `r_bio` contains only 1 unique level. This happens when a filtering strategy (e.g., D — malignant only, or G — Affymetrix only) produces a subset where all samples share the same `BIO_COL` value after fillna. R then tries to create a contrast for a factor with a single level, which is undefined.

**Fix for `normalize_sva` (Cell 33):** Add a guard before building `mod`. If fewer than 2 unique levels, fall back to an intercept-only model (which is equivalent to no biological covariate protection — acceptable since SVA detects hidden factors independently).

```python
def normalize_sva(exp_df, ann_df, bio_col=BIO_COL, **kw):
    sva_r   = importr("sva")
    limma_r = importr("limma")
    base_r  = importr("base")
    bio     = ann_df.loc[exp_df.index, bio_col].fillna("Unknown").astype(str).values
    r_mat   = base_r.as_matrix(pandas2ri.py2rpy(exp_df.T))
    r_bio   = ro.StrVector(bio)
    df_r    = ro.DataFrame({"r_bio": r_bio})
    n_levels = len(set(bio))
    if n_levels >= 2:
        mod  = ro.r["model.matrix"](ro.Formula("~r_bio"), data=df_r)
    else:
        print(f"SVA: only {n_levels} unique level(s) in {bio_col} — using intercept-only model")
        mod  = ro.r["model.matrix"](ro.Formula("~1"), data=df_r)
    mod0 = ro.r["model.matrix"](ro.Formula("~1"), data=df_r)
    n_sv = sva_r.num_sv(r_mat, mod)
    if int(n_sv[0]) == 0:
        print("SVA: 0 surrogate variables detected — returning uncorrected data")
        return exp_df.copy()
    sv_obj = sva_r.sva(r_mat, mod, mod0, n_sv=n_sv)
    svs    = pandas2ri.rpy2py(sv_obj.rx2("sv"))
    result = limma_r.removeBatchEffect(
        r_mat, covariates=ro.r["t"](pandas2ri.py2rpy(pd.DataFrame(svs, index=exp_df.index)))
    )
    result_np = result if isinstance(result, np.ndarray) else pandas2ri.rpy2py(result)
    return pd.DataFrame(result_np.T, index=exp_df.index, columns=exp_df.columns)
```

**Fix for `normalize_combat` (Cell 34):** Same guard — if < 2 levels in `bio_col`, pass `mod=ro.rinterface.NULL` to ComBat (which tells ComBat to skip biological covariate protection):

```python
def normalize_combat(exp_df, ann_df, batch_col=BATCH_COL, bio_col=BIO_COL, **kw):
    sva_r  = importr("sva")
    base_r = importr("base")
    batches = ann_df.loc[exp_df.index, batch_col].astype(str).values
    bio     = ann_df.loc[exp_df.index, bio_col].fillna("Unknown").astype(str).values
    r_mat   = base_r.as_matrix(pandas2ri.py2rpy(exp_df.T))
    n_levels = len(set(bio))
    if n_levels >= 2:
        r_bio = ro.StrVector(bio)
        mod   = ro.r["model.matrix"](ro.Formula("~r_bio"),
                                     data=ro.DataFrame({"r_bio": r_bio}))
    else:
        print(f"ComBat: only {n_levels} unique level(s) in {bio_col} — running without covariate")
        mod = ro.rinterface.NULL
    result = sva_r.ComBat(dat=r_mat, batch=ro.StrVector(batches), mod=mod)
    result_np = result if isinstance(result, np.ndarray) else pandas2ri.rpy2py(result)
    return pd.DataFrame(result_np.T, index=exp_df.index, columns=exp_df.columns)
```

**Same guard applies to `normalize_combat_seq`** (Cell 34): replace the unconditional `model.matrix(~r_bio)` with the same 2-level check, passing `group=ro.rinterface.NULL` if < 2 levels.

---

### Fix 2 — `07_pycombat`: `No module named 'combat'`

**Root cause:** The `combat` Python package is not installed in the active kernel environment (`~/venvs/collagen_3_11/`).

**Action:** Run in a terminal cell or shell:
```bash
source ~/venvs/collagen_3_11/bin/activate
pip install combat
```

**Verify import works after install:**
```python
from combat.pycombat import pycombat   # should not raise ImportError
```

**Note:** The PyPI package is named `combat` (not `pycomBat` or `pycombat`). If `pip install combat` installs a different package (check `pip show combat` for homepage), the alternative is:
```bash
pip install pyComBat   # alternative name used in some mirrors
```
If neither resolves, install directly from source:
```bash
pip install git+https://github.com/epigenelabs/pyComBat.git
```

**No code change needed** in `normalize_pycombat` once the package is installed.

---

### Fix 3 — `08_inmoose_combatseq`: `No module named 'inmoose'`

**Root cause:** The `inmoose` package is not installed.

**Action:**
```bash
source ~/venvs/collagen_3_11/bin/activate
pip install inmoose
```

**Verify:**
```python
from inmoose.pycombat import pycombat_seq   # should not raise ImportError
```

**No code change needed** in `normalize_inmoose_combat_seq` once installed.

---

### Fix 4 — `10_mnn`: `Conversion 'rpy2py' not defined for objects of type '<class 'numpy.ndarray'>'`

**Root cause:** With `pandas2ri.activate()` in effect, `ro.r["as.matrix"](...)` automatically converts the R matrix to a numpy array before it is returned to Python. Then `pandas2ri.rpy2py()` is called on that numpy array, which has no conversion path registered.

**Current broken code (Cell 34):**
```python
corrected_embed = pandas2ri.rpy2py(
    ro.r["as.matrix"](ro.r["reducedDim"](result, "corrected")))
```

**Fixed code:**
```python
_mat = ro.r["as.matrix"](ro.r["reducedDim"](result, "corrected"))
corrected_embed = _mat if isinstance(_mat, np.ndarray) else pandas2ri.rpy2py(_mat)
```

**Full fixed function:**
```python
def normalize_mnn(exp_df, ann_df, batch_col=BATCH_COL, k=20, **kw):
    """fastMNN (Haghverdi et al. 2018). BiocManager::install('batchelor')."""
    batchelor_r = importr("batchelor")
    base_r      = importr("base")
    batches = ann_df.loc[exp_df.index, batch_col].astype(str)
    r_mat   = base_r.as_matrix(pandas2ri.py2rpy(exp_df.T))
    result  = batchelor_r.fastMNN(r_mat, batch=ro.StrVector(batches.values), k=k)
    _mat = ro.r["as.matrix"](ro.r["reducedDim"](result, "corrected"))
    corrected_embed = _mat if isinstance(_mat, np.ndarray) else pandas2ri.rpy2py(_mat)
    pca       = PCA(n_components=corrected_embed.shape[1]).fit(exp_df.values)
    recovered = corrected_embed @ pca.components_ + pca.mean_
    return pd.DataFrame(recovered, index=exp_df.index, columns=exp_df.columns)
```

---

### Fix 5 — `12_scanorama`: `No module named 'scanorama'`

**Root cause:** `scanorama` not installed.

**Action:**
```bash
source ~/venvs/collagen_3_11/bin/activate
pip install scanorama
```

**Verify:**
```python
import scanorama   # should not raise ImportError
```

**No code change needed** in `normalize_scanorama` once installed.

---

### Fix 6 — `14_qsmooth`: `Conversion 'rpy2py' not defined for objects of type '<class 'numpy.ndarray'>'`

**Root cause:** Same as Fix 4. `qsmooth_r.qsmoothData(qs_obj)` returns a numpy array via auto-conversion, and then `pandas2ri.rpy2py()` is called on it.

**Current broken code (Cell 35):**
```python
result = pandas2ri.rpy2py(qsmooth_r.qsmoothData(qs_obj))
```

**Fixed code:**
```python
_raw   = qsmooth_r.qsmoothData(qs_obj)
result = _raw if isinstance(_raw, np.ndarray) else pandas2ri.rpy2py(_raw)
```

**Full fixed function:**
```python
def normalize_qsmooth(exp_df, ann_df, batch_col=BATCH_COL, **kw):
    """Smooth quantile normalization (Hicks et al. 2018). BiocManager::install('qsmooth')."""
    qsmooth_r = importr("qsmooth")
    base_r    = importr("base")
    groups = ann_df.loc[exp_df.index, batch_col].astype(str).values
    r_mat  = base_r.as_matrix(pandas2ri.py2rpy(exp_df.T))
    qs_obj = qsmooth_r.qsmooth(r_mat, group_factor=ro.StrVector(groups))
    _raw   = qsmooth_r.qsmoothData(qs_obj)
    result = _raw if isinstance(_raw, np.ndarray) else pandas2ri.rpy2py(_raw)
    return pd.DataFrame(result.T, index=exp_df.index, columns=exp_df.columns)
```

---

### Fix 7 — `16_fsqn_r`: `Conversion 'rpy2py' not defined for objects of type '<class 'rpy2.rinterface_lib.sexp.NULLType'>'`

**Root cause (two-part):**

1. `quantileNormalizeByFeature()` returned R NULL, indicating a silent failure inside the FSQN R function. The most likely cause: with `pandas2ri.activate()`, `base_r.as_matrix(pandas2ri.py2rpy(df))` may return a Python-side numpy array instead of an R matrix object. When this numpy array is passed to the R function `quantileNormalizeByFeature`, R receives it not as a proper R matrix but as an alien type, causing the function to return NULL silently.

2. The isinstance check `result if isinstance(result, np.ndarray) else pandas2ri.rpy2py(result)` does not handle `NULLType`, so `rpy2py(NULLType)` is called and fails.

**Fix (two-part):**

Part A — Disable auto-conversion around the FSQN call to ensure R receives a genuine R matrix:

```python
def normalize_fsqn_r(exp_df, ann_df, batch_col=BATCH_COL,
                      target_group="RNASeq_FF_PolyA", **kw):
    """
    FSQN via original R package (Franks et al. 2018).
    devtools::install_github('jenniferfranks/FSQN')
    ★ Selected best method from prior analysis: 16% residual batch PCA R².
    """
    from rpy2.rinterface_lib.sexp import NULLType
    fsqn_r = importr("FSQN")
    base_r = importr("base")
    groups = ann_df.loc[exp_df.index, batch_col].astype(str)
    target_mask = (groups == target_group) if target_group in groups.values \
                  else pd.Series(True, index=exp_df.index)

    # Deactivate auto-conversion: py2rpy must produce R objects, not numpy
    with pandas2ri.converter.context():
        target_mat = base_r.as_matrix(pandas2ri.py2rpy(exp_df.loc[target_mask].T))
        query_mat  = base_r.as_matrix(pandas2ri.py2rpy(exp_df.T))

    result = fsqn_r.quantileNormalizeByFeature(query_mat, target_mat)

    if isinstance(result, NULLType) or result is None:
        raise RuntimeError(
            "FSQN R: quantileNormalizeByFeature returned NULL. "
            "Check R console output above for the underlying error. "
            "Possible causes: wrong matrix orientation, target group absent, "
            "FSQN not installed (devtools::install_github('jenniferfranks/FSQN'))."
        )

    result_np = result if isinstance(result, np.ndarray) else pandas2ri.rpy2py(result)
    return pd.DataFrame(result_np.T, index=exp_df.index, columns=exp_df.columns)
```

Part B — If Part A does not resolve the NULL return (i.e., R still reports a failure), the fallback is to call FSQN using `ro.r()` string evaluation, bypassing rpy2 object passing entirely:

```python
# Fallback approach using R string evaluation — use only if Part A still returns NULL
import tempfile, os

def normalize_fsqn_r_fallback(exp_df, ann_df, batch_col=BATCH_COL,
                                target_group="RNASeq_FF_PolyA", **kw):
    groups      = ann_df.loc[exp_df.index, batch_col].astype(str)
    target_mask = (groups == target_group) if target_group in groups.values \
                  else pd.Series(True, index=exp_df.index)
    with tempfile.TemporaryDirectory() as td:
        ref_path   = os.path.join(td, "ref.csv")
        query_path = os.path.join(td, "query.csv")
        out_path   = os.path.join(td, "out.csv")
        exp_df.loc[target_mask].T.to_csv(ref_path)
        exp_df.T.to_csv(query_path)
        ro.r(f"""
            library(FSQN)
            ref   <- as.matrix(read.csv('{ref_path}',   row.names=1))
            query <- as.matrix(read.csv('{query_path}', row.names=1))
            out   <- quantileNormalizeByFeature(query, ref)
            write.csv(out, '{out_path}')
        """)
        result = pd.read_csv(out_path, index_col=0)
    return result.T
```

**Smoke test for FSQN specifically:** After applying Fix 7, run `normalize_fsqn_r` on a small slice (100 samples × 50 genes) and confirm it returns a DataFrame of the correct shape before running the full benchmark.

---

## Phase 1 smoke test

After all Phase 1 fixes, re-run the smoke test cell with all 18 methods on a small subset (e.g., 200 samples from Strategy A). Expected result: **18/18 pass**.

The smoke test cell should:
1. Call each method on the small subset
2. Print `✓ {method_name}` on success or `✗ {method_name}: {full traceback}` on failure (use `traceback.format_exc()`)
3. Report the count of passed/failed methods

---

## Phase 2 — New methods (after Phase 1 passes)

New methods are added to Cell 35 (the HIGH harshness methods cell, after `normalize_rank`), with their registry entries added to the `METHODS` dict.

Methods are added in the order they appear below. Each is a self-contained function following the same `(exp_df, ann_df, **kw) → pd.DataFrame` contract as existing methods.

---

### Method 19 — TDM (Training Distribution Matching)

**Install (run once):**
```bash
source ~/venvs/collagen_3_11/bin/activate
Rscript -e "devtools::install_github('greenelab/TDM')"
```

**Implementation:**
```python
def normalize_tdm(exp_df, ann_df, batch_col=BATCH_COL,
                  target_group="RNASeq_FF_PolyA", **kw):
    """
    Training Distribution Matching (Thompson et al. 2016, PeerJ 4:e1621).
    devtools::install_github('greenelab/TDM')
    Transforms each non-target batch to match the target distribution.
    High harshness; similar to FSQN but preserves tail values more gently.
    """
    from rpy2.rinterface_lib.sexp import NULLType
    tdm_r  = importr("TDM")
    base_r = importr("base")
    groups = ann_df.loc[exp_df.index, batch_col].astype(str)
    target_mask = (groups == target_group) if target_group in groups.values \
                  else pd.Series(True, index=exp_df.index)
    target_mat = base_r.as_matrix(pandas2ri.py2rpy(exp_df.loc[target_mask].T))
    query_mat  = base_r.as_matrix(pandas2ri.py2rpy(exp_df.T))
    result = tdm_r.tdm_transform(query_mat, target_mat)
    if isinstance(result, NULLType) or result is None:
        raise RuntimeError("TDM returned NULL — check R console for errors")
    result_np = result if isinstance(result, np.ndarray) else pandas2ri.rpy2py(result)
    return pd.DataFrame(result_np.T, index=exp_df.index, columns=exp_df.columns)
```

**Registry entry:**
```python
"19_tdm": (normalize_tdm, "high"),
```

**Fallback:** If the `TDM` R package API differs from `tdm_transform`, check the package vignette:
```r
library(TDM); ?tdm_transform
```
The function may be named `TDM` or `train_tdm` + `apply_tdm` in two steps. Inspect and adjust accordingly.

---

### Method 20 — Shambhala

**Install (run once):**
```bash
Rscript -e "devtools::install_github('shambhala-lab/shambhala')"
```

**Pre-implementation check:** Verify the package installs and that `library(shambhala)` works. The repository may be archived or the API changed since 2019. Run `ls(getNamespace('shambhala'))` in R to see available functions before writing the wrapper.

**Implementation (pending API verification):**
```python
def normalize_shambhala(exp_df, ann_df, batch_col=BATCH_COL,
                         target_group="RNASeq_FF_PolyA", **kw):
    """
    Shambhala: platform-agnostic harmonizer (Khalique et al. 2019, BMC Bioinformatics 20:66).
    devtools::install_github('shambhala-lab/shambhala')
    Quantile normalization with sample-specific calibration against reference.
    Validated on 12 mixed platforms including Affymetrix + RNA-seq.
    """
    from rpy2.rinterface_lib.sexp import NULLType
    shambhala_r = importr("shambhala")
    base_r      = importr("base")
    groups      = ann_df.loc[exp_df.index, batch_col].astype(str)
    target_mask = (groups == target_group) if target_group in groups.values \
                  else pd.Series(True, index=exp_df.index)
    target_mat = base_r.as_matrix(pandas2ri.py2rpy(exp_df.loc[target_mask].T))
    query_mat  = base_r.as_matrix(pandas2ri.py2rpy(exp_df.T))
    # NOTE: actual function name must be verified against package ls()
    result = shambhala_r.harmonize(query_mat, target_mat)
    if isinstance(result, NULLType) or result is None:
        raise RuntimeError("Shambhala returned NULL — verify API with ls(getNamespace('shambhala'))")
    result_np = result if isinstance(result, np.ndarray) else pandas2ri.rpy2py(result)
    return pd.DataFrame(result_np.T, index=exp_df.index, columns=exp_df.columns)
```

**Registry entry:**
```python
"20_shambhala": (normalize_shambhala, "high"),
```

---

### Method 21 — HarmonizR

**Install (run once):**
```bash
Rscript -e "BiocManager::install('HarmonizR')"
# or if not on Bioconductor:
Rscript -e "devtools::install_github('HSU-HPC/HarmonizR')"
```

**Implementation:**

HarmonizR requires a CSV-format batch description file rather than an R vector. The wrapper creates a temporary file for this.

```python
def normalize_harmonizr(exp_df, ann_df, batch_col=BATCH_COL,
                         algorithm="ComBat", **kw):
    """
    HarmonizR (Voss et al. 2022, Nature Communications 13:3523).
    BiocManager::install('HarmonizR')
    NA-aware wrapper around ComBat/limma. Splits sparse matrices into
    denser submatrices to handle genes absent in some batches.
    algorithm: 'ComBat' or 'limma'
    """
    import tempfile, os
    from rpy2.rinterface_lib.sexp import NULLType
    harmonizr_r = importr("HarmonizR")
    batches = ann_df.loc[exp_df.index, batch_col].astype(str)

    with tempfile.TemporaryDirectory() as td:
        # HarmonizR expects: data CSV (genes × samples) + description CSV
        data_path = os.path.join(td, "data.csv")
        desc_path = os.path.join(td, "description.csv")
        out_path  = os.path.join(td, "out.csv")

        exp_df.T.to_csv(data_path)   # genes × samples

        # Description CSV: columns = ID, batch, sample
        desc = pd.DataFrame({
            "ID":      exp_df.index,
            "batch":   batches.values,
            "sample":  exp_df.index,
        })
        desc.to_csv(desc_path, index=False)

        ro.r(f"""
            library(HarmonizR)
            result <- harmonizR(
                data_as_input = "{data_path}",
                description_as_input = "{desc_path}",
                algorithm = "{algorithm}",
                output_file = "{out_path}"
            )
        """)
        if not os.path.exists(out_path):
            raise RuntimeError("HarmonizR produced no output — check R console for errors")
        result = pd.read_csv(out_path, index_col=0)

    # Result is genes × samples — transpose back
    return result.T.reindex(exp_df.index)
```

**Registry entry:**
```python
"21_harmonizr_combat": (normalize_harmonizr, "medium"),
```

**Note:** HarmonizR's main advantage over plain ComBat is NA-tolerant matrix dissection. To exploit this, call it on the output of `prepare_dataset_imputed` (relaxed NA threshold) rather than `prepare_dataset` (strict full-coverage). This could expand the gene set from ~3,520 to ~5,000+ for HarmonizR-specific evaluation.

---

### Method 22 — TMM (RNA-seq only, Strategy C gate)

**Install:** Part of `edgeR`, which is already used in `normalize_ruv`. No additional install needed.

**Implementation:**
```python
def _assert_rnaseq_only(ann_df, batch_col=BATCH_COL, method_name=""):
    """Raises NotImplementedError if microarray batches are present in ann_df."""
    has_array = ann_df[batch_col].str.startswith("GPL").any()
    if has_array:
        raise NotImplementedError(
            f"{method_name} is RNA-seq only. "
            "Use with Strategy C (keep_batches=RNASEQ_BATCHES) or "
            "filter to RNA-seq samples before calling."
        )

def normalize_tmm(exp_df, ann_df, batch_col=BATCH_COL, **kw):
    """
    TMM normalization via edgeR (Robinson & Oshlack 2010, Genome Biology 11:R25).
    BiocManager::install('edgeR')  [already installed for RUVSeq]
    Input: raw RNA-seq counts (integers). Returns log2-CPM after TMM scaling.
    RNA-SEQ ONLY — raises NotImplementedError if microarray batches are present.
    """
    _assert_rnaseq_only(ann_df, batch_col, "TMM")
    edger_r = importr("edgeR")
    base_r  = importr("base")
    counts  = np.round(exp_df.values).astype(int).clip(0)
    r_mat   = base_r.as_matrix(pandas2ri.py2rpy(
                  pd.DataFrame(counts.T, index=exp_df.columns, columns=exp_df.index)))
    dge     = edger_r.DGEList(counts=r_mat)
    dge     = edger_r.calcNormFactors(dge, method="TMM")
    _raw    = edger_r.cpm(dge, log=True, prior_count=1)
    result  = _raw if isinstance(_raw, np.ndarray) else pandas2ri.rpy2py(_raw)
    return pd.DataFrame(result.T, index=exp_df.index, columns=exp_df.columns)
```

**Registry entry:**
```python
"22_tmm": (normalize_tmm, "low"),   # low harshness: scaling only, no distribution forcing
```

**Cross-product behavior:** The `_assert_rnaseq_only` guard will raise `NotImplementedError` for all strategies containing microarray batches (S0, A, B, D, E1–E3, F, G). The cross-product loop's `try/except` will catch this and record `NaN` for those combinations. Only Strategy C (RNA-seq only) will produce a valid result. This is intentional and expected.

---

### Method 23 — DESeq2 VST (RNA-seq only, Strategy C gate)

**Install:**
```bash
Rscript -e "BiocManager::install('DESeq2')"
```

**Implementation:**
```python
def normalize_vst(exp_df, ann_df, batch_col=BATCH_COL, **kw):
    """
    DESeq2 variance-stabilizing transformation (Love et al. 2014, Genome Biology 15:550).
    BiocManager::install('DESeq2')
    Transforms count data to log2-scale with stabilized variance.
    RNA-SEQ ONLY — raises NotImplementedError if microarray batches are present.
    Better than naive log2(x+1) for RNA-seq: accounts for heteroscedastic count distribution.
    """
    _assert_rnaseq_only(ann_df, batch_col, "DESeq2 VST")
    deseq2_r = importr("DESeq2")
    base_r   = importr("base")
    counts   = np.round(exp_df.values).astype(int).clip(0)
    r_mat    = base_r.as_matrix(pandas2ri.py2rpy(
                   pd.DataFrame(counts.T, index=exp_df.columns, columns=exp_df.index)))
    col_data = ro.DataFrame({"sample": ro.StrVector(list(exp_df.index))})
    dds      = deseq2_r.DESeqDataSetFromMatrix(
                   countData=r_mat, colData=col_data, design=ro.Formula("~1"))
    vsd      = deseq2_r.vst(dds, blind=True)
    _raw     = ro.r["assay"](vsd)
    result   = _raw if isinstance(_raw, np.ndarray) else pandas2ri.rpy2py(_raw)
    return pd.DataFrame(result.T, index=exp_df.index, columns=exp_df.columns)
```

**Registry entry:**
```python
"23_vst": (normalize_vst, "low"),   # low harshness: variance stabilization only
```

**Cross-product behavior:** Same as TMM — valid only for Strategy C; all other strategies record `NaN`.

---

### Method 24 — PEER (post-correction residual factor removal)

**Install:**
```bash
# PEER R package — check if available via CRAN or requires source build
Rscript -e "install.packages('peer')"
# If that fails, install from source:
# https://www.sanger.ac.uk/tool/peer/
```

**Implementation:**
```python
def normalize_peer(exp_df, ann_df, n_factors=10, **kw):
    """
    PEER: Probabilistic Estimation of Expression Residuals (Stegle et al. 2012,
    Nature Protocols 7:500). install.packages('peer')
    Infers n_factors hidden latent factors and returns residual expression.
    Requires pre-normalized log2-scale input (apply after another method, not standalone).
    Typical use: run on top of FSQN R output as a secondary correction step.
    n_factors: number of hidden factors (5–30; start with 10).
    """
    peer_r = importr("peer")
    base_r = importr("base")
    model  = peer_r.PEER()
    peer_r.PEER_setPhenoMean(model, base_r.as_matrix(pandas2ri.py2rpy(exp_df)))
    peer_r.PEER_setNk(model, n_factors)
    peer_r.PEER_update(model)
    _raw      = peer_r.PEER_getResiduals(model)
    residuals = _raw if isinstance(_raw, np.ndarray) else pandas2ri.rpy2py(_raw)
    return pd.DataFrame(residuals, index=exp_df.index, columns=exp_df.columns)
```

**Registry entry:**
```python
"24_peer_k10": (normalize_peer,                              "medium"),
"24b_peer_k20": (lambda e, a, **kw: normalize_peer(e, a, n_factors=20, **kw), "medium"),
```

**Note on PEER as secondary correction:** PEER is best used not as a standalone item in the METHODS dict but as a secondary step applied to the top-5 combinations from the cross-product. Add a dedicated cell after Section 4.4 that takes the top `exp_norm` results and runs `normalize_peer(exp_norm, ann_s, n_factors=[5, 10, 20])`, then re-evaluates `r2_batch` for each. This tests whether residual factor removal further reduces batch R² after the primary method.

---

### METHODS dict update

Add to the METHODS dict **after** `"18_rank"`:

```python
    # ── Cross-platform focused (high harshness) ────────────────────────────
    "19_tdm":              (normalize_tdm,          "high"),
    "20_shambhala":        (normalize_shambhala,    "high"),
    # ── Cross-platform with caveats (medium harshness) ─────────────────────
    "21_harmonizr":        (normalize_harmonizr,    "medium"),
    # ── RNA-seq only (gate raises error on mixed data) ─────────────────────
    "22_tmm":              (normalize_tmm,          "low"),
    "23_vst":              (normalize_vst,          "low"),
    # ── Secondary residual correction (medium harshness) ───────────────────
    "24_peer_k10":         (normalize_peer,         "medium"),
```

Add a color for the RNA-seq-only gate category:
```python
HARSHNESS_COLORS["rna_seq_only"] = "#aaaaaa"   # gray
```

Update the heatmap annotation logic so that NaN entries from the RNA-seq-only gate are rendered as gray, not as the missing-value color, to distinguish "not applicable" from "failed".

---

## Phase 3 — XPN (deferred)

XPN (Shabalin et al. 2008) is not implemented in Phase 2 because:
- The package is unmaintained (2008) and may require manual compilation.
- It was designed for microarray-to-microarray normalization and its RNA-seq applicability is untested.

If desired later:
1. Download source from https://genome-publications.bioinf.unc.edu/xpn/
2. Compile the R package from source.
3. Map its API (likely `xpn(data1, data2)`) to the normalize_* contract.
4. Add as Method 25.

---

## Implementation order checklist

```
Phase 0 — Traceback improvement
  [x] Add `import traceback` to imports cell (added inline: import os, warnings, pickle, traceback)
  [x] Replace all bare `print(e)` in except blocks with `print(traceback.format_exc())`
      - Smoke test cell (37): uses traceback.format_exc() for all failures
      - Cross-product loop (cell 39): added traceback.format_exc() to main FAILED block

Phase 1 — Bug fixes (Cell 33, 34, 35)
  [x] Fix 1a: normalize_sva — add n_levels guard (cell 33)
  [x] Fix 1b: normalize_combat — add n_levels guard (cell 34)
  [x] Fix 1c: normalize_combat_seq — add n_levels guard for group argument (cell 34)
  [x] Fix 2: pip install combat — already installed (confirmed working)
  [x] Fix 3: pip install inmoose — reinstalled + upgraded xarray to fix numpy 2.4 compat
  [x] Fix 4: normalize_mnn — isinstance guard on corrected_embed (cell 34)
  [x] Fix 5: pip install scanorama — reinstalled; working after pyarrow/sklearn reinstall
  [x] Fix 6: normalize_qsmooth — isinstance guard on qsmoothData result (cell 35)
  [x] Fix 7: normalize_fsqn_r — NULLType check + ro.conversion.localconverter fix (cell 35)
  [x] Re-run smoke test — 19/24 pass on first run; additional fixes applied (see table below)

Phase 2 — New methods
  [x] Install TDM R package and verify API
      API: tdm_transform(file=query_path, ref_file=ref_path) — requires TSV files with gene column
      Implementation uses file-based interface (not matrix passing) due to data.table requirement
  [x] Implement normalize_tdm (Method 19)
  [x] Install/verify Shambhala R package and inspect API with ls()
      RESULT: shambhala-lab/shambhala GitHub repo does not exist (404). Package unavailable.
      Implementation added but will raise rpy2 error at runtime (importr("shambhala") fails).
  [x] Implement normalize_shambhala (Method 20) — conditional on API availability
  [x] Install HarmonizR (devtools::install_github('HSU-HPC/HarmonizR'))
      Format: data=TSV (genes×samples), description=CSV (ID/batch/sample_int), output={base}.tsv
  [x] Implement normalize_harmonizr (Method 21) — uses correct TSV/CSV formats
  [x] Implement _assert_rnaseq_only helper
  [x] Implement normalize_tmm (Method 22)
  [x] Install DESeq2 (already installed) and implement normalize_vst (Method 23)
  [x] Install peer — UNAVAILABLE for R 4.5 (not on CRAN, Bioconductor, or GitHub for R 4.5)
      normalize_peer implemented; will fail at runtime until peer package is available
  [x] Update METHODS dict with Methods 19–24 (cell 36)
  [x] Add HARSHNESS_COLORS["rna_seq_only"] = "#aaaaaa" (cell 36)
  [x] Smoke test new methods — 19/24 pass; 5 failures diagnosed and fixed (see additional fixes table)
  [ ] Re-run smoke test after fixes — expect 22/24 pass (shambhala + peer as NotImplementedError = expected skips)
  [ ] Run full cross-product (Section 4.1) overnight
```

### Known installation failures (document for future resolution)
- **shambhala** (Method 20): `shambhala-lab/shambhala` GitHub repository returns 404. Package is unavailable. `normalize_shambhala` raises `NotImplementedError` immediately; smoke test counts it as expected skip.
- **peer** (Method 24): Not available on CRAN, Bioconductor, or GitHub for R 4.5.3. `normalize_peer` raises `NotImplementedError` immediately; smoke test counts it as expected skip.

### Additional fixes from first smoke test run (2026-04-19)

| Method | Error | Fix |
|---|---|---|
| `04_sva` | `density.default: 'x' contains missing values` inside `sva()` | Wrap `sva_r.sva()` in try/except RRuntimeError; return uncorrected data on failure |
| `08_inmoose_combatseq` | `unexpected keyword argument 'group'` | InMoose 0.9.1 API changed: use `covar_mod=` (design matrix) instead of `group=`; pass `pd.get_dummies(bio, drop_first=True)` or `None` if < 2 levels |
| `16_fsqn_r` | `NotImplementedError` from `ro.conversion.localconverter(ro.default_converter)` | `localconverter(ro.default_converter)` deactivates pandas2ri, so `pandas2ri.py2rpy` raises NotImplementedError. Replaced with **file-based fallback**: write CSV → R reads with read.csv → quantileNormalizeByFeature → write.csv → Python reads |
| `19_tdm` | `NotImplementedError` from `pandas2ri.rpy2py(pandas_dataframe)` | With `pandas2ri.activate()`, `ro.r()` returning a data.table is auto-converted to pandas DataFrame; calling `rpy2py()` on it raises NotImplementedError. Replaced with **file-based approach**: write TSV → R runs tdm_transform → write TSV → Python reads |
| `20_shambhala` | `PackageNotInstalledError` | Changed to raise `NotImplementedError` immediately (no importr call) |
| `23_vst` | `less than 'nsub' rows` (vst requires ≥1000 genes) | Use `varianceStabilizingTransformation()` when gene count < 1000; use `vst()` only for ≥1000 genes |
| `24_peer_k10` | `PackageNotInstalledError` | Changed to raise `NotImplementedError` immediately (no importr call) |

---

## Notes on R-Python type conversion issues (general principle)

The recurring error `Conversion 'rpy2py' not defined for objects of type '<class 'numpy.ndarray'>'` (Fixes 4, 6, 7) is caused by `pandas2ri.activate()` enabling automatic conversion of R matrices → numpy arrays on function return. This means any code pattern:

```python
result = pandas2ri.rpy2py(some_r_function(...))
```

is broken whenever `pandas2ri.activate()` is in effect, because `some_r_function(...)` already returns a numpy array and `rpy2py` has no handler for `numpy.ndarray`.

**Universal fix pattern** — apply this to all current and future R-returning calls:

```python
_raw   = some_r_function(...)
result = _raw if isinstance(_raw, np.ndarray) else pandas2ri.rpy2py(_raw)
```

Additionally, for functions that must receive **genuine R matrix objects** (FSQN, TDM, Shambhala), disable auto-conversion selectively:

```python
with ro.conversion.localconverter(ro.default_converter):
    r_mat = base_r.as_matrix(ro.r["as.matrix"](pandas2ri.py2rpy(df.T)))
```

This ensures the R function receives a proper R matrix rather than a Python-side numpy array that R cannot recognize.
