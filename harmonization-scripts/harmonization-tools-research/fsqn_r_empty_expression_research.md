# Root Cause Analysis: `normalize_fsqn_r` Produces Empty Expression Tables

**Date:** 2026-05-09  
**Affected methods:** `16_fsqn_r`  
**Symptom:** All strategies except `F_microarray_only` and `G_affymetrix_only` produce S3 output files containing only the sample-name index column with zero gene columns; `r2_batch = nan`.

---

## 1. Observed Behavior

| Strategy | Contains RNA-seq? | Output genes | Status |
|---|---|---|---|
| `S0_no_removal` | Yes | 0 | **Empty** |
| `A_confirmed_bad` | Yes | 0 | **Empty** |
| `B_extended_bad` | Yes | 0 | **Empty** |
| `C_rnaseq_only` | Yes | 0 | **Empty** |
| `D_malignant_only` | Yes | 0 | **Empty** |
| `E1/E2/E3_iterative` | Yes | 0 | **Empty** |
| `H_affymetrix_extended` | Yes | 0 | **Empty** |
| `F_microarray_only` | No | ~N | Appears OK |
| `G_affymetrix_only` | No | ~N | Appears OK |

The symptom is **not imputation-dependent**: strategies with strict imputation (no NAs) also produce empty output for RNA-seq-containing datasets.

---

## 2. FSQN Package Source: The Definitive Check

The `quantileNormalizeByFeature` function in the FSQN R package (jenniferfranks/FSQN, fetched from GitHub) has the following signature and dimension check:

```r
quantileNormalizeByFeature <- function(matrix_to_normalize,
                                       target_distribution_matrix) {

    if (ncol(matrix_to_normalize) != ncol(target_distribution_matrix)) {
        cat("ERROR: Data matrices are not compatible - column lengths differ!")
    }
    else {
        data.qn <- matrix(0, nrow = nrow(matrix_to_normalize),
                          ncol = ncol(matrix_to_normalize))

        for (i in 1:ncol(matrix_to_normalize)) {
            feature.to.normalize <- matrix_to_normalize[, i]
            target.feature.dist  <- target_distribution_matrix[, i]
            result <- normalize.quantiles.use.target(
                x = as.matrix(feature.to.normalize),
                target = target.feature.dist,
                copy = TRUE)
            data.qn[, i] <- result
        }
        rownames(data.qn) <- rownames(matrix_to_normalize)
        colnames(data.qn) <- colnames(matrix_to_normalize)
        return(data.qn)
    }
}
```

**Critical facts derived from this source:**

1. **Matrix orientation is SAMPLES × GENES.** The vignette shows `target(100 samples × 150 features)` and `test(30 samples × 150 features)`. Rows = samples, columns = genes/features. The function normalizes column by column (gene by gene), position-indexed.

2. **The check compares `ncol` — number of gene columns.** Both matrices must have the same gene set (same number of columns). The number of rows (samples) **can differ freely** — the function never checks `nrow`.

3. **On failure the function uses `cat()`, not `stop()`.** This is a plain console print with no R condition raised. `rpy2` does not convert `cat()` output to a Python exception. The function falls through the `if` branch and returns `NULL` implicitly (no explicit `return`).

4. **`write.csv(NULL, path)` in R writes a near-empty CSV** (`""`), which `pd.read_csv(path, index_col=0)` reads as a `(0, 0)` DataFrame. After the subsequent `.T.reindex(exp_df.index)` call, shape becomes `(n_samples, 0)` — a DataFrame with all sample rows but zero gene columns. This is exactly the "single column of sample names without any genes" observed in S3.

---

## 3. Root Cause: Wrong Matrix Orientation in `normalize_fsqn_r`

The current `bench_shared.py` implementation (lines 1186–1199):

```python
exp_df.loc[target_mask].T.to_csv(ref_path)    # writes GENES × ref_samples
exp_df.T.to_csv(query_path)                    # writes GENES × all_samples

ro.r(f"""
    library(FSQN)
    ref   <- as.matrix(read.csv(\"{ref_path}\",   row.names=1))
    query <- as.matrix(read.csv(\"{query_path}\", row.names=1))
    out   <- quantileNormalizeByFeature(query, ref)
    write.csv(out, \"{out_path}\")
""")

result = pd.read_csv(out_path, index_col=0)
return result.T.reindex(exp_df.index)
```

The `.T` transpose inverts the orientation. R receives:

| Variable | Shape | ncol value |
|---|---|---|
| `query` | genes × all_samples | `n_all_samples` (e.g. 5444) |
| `ref`   | genes × ref_samples  | `n_ref_samples` (e.g. 1039) |

The FSQN check: `ncol(query) != ncol(ref)` → `5444 != 1039` → **FAILS for every strategy where the reference batch is a subset of the full dataset** (i.e., wherever `"RNASeq_FF_PolyA"` is present in the data).

---

## 4. Why `F_microarray_only` and `G_affymetrix_only` Appear to Work

These two strategies contain no `RNASeq_FF_PolyA` samples. The fallback in the code triggers:

```python
target_mask = (
    groups == target_group
    if target_group in groups.values
    else pd.Series(True, index=exp_df.index)   # ← ALL True for F and G
)
```

With all-True mask: `exp_df.loc[target_mask].T` == `exp_df.T`. Both `ref` and `query` are the **same matrix** (same shape, same columns). The FSQN check passes because `ncol(query) == ncol(ref)`.

**However, this is not a correct FSQN result.** Normalizing every sample against all samples as the reference is equivalent to standard quantile normalization, not feature-specific reference normalization. The F/G outputs have the correct shape but represent the wrong operation semantically.

---

## 5. Failure Chain Summary

```
exp_df.T → GENES × SAMPLES → written to CSV
R reads as GENES × SAMPLES matrix

quantileNormalizeByFeature(query, ref):
  ncol(query) = n_all_samples (e.g. 5444)
  ncol(ref)   = n_ref_samples  (e.g. 1039)
  5444 ≠ 1039 → cat("ERROR...") → returns NULL implicitly

write.csv(NULL, out_path) → writes '""' to file

os.path.exists(out_path) → True (guard does not trigger)

pd.read_csv(out_path, index_col=0) → shape (0, 0)

(0, 0).T → shape (0, 0)

.reindex(exp_df.index) → shape (n_samples, 0)
                           n_samples rows, 0 gene columns
                           ↳ "empty table with only sample names"
```

---

## 6. Secondary Issue: Gene Name Mangling (`check.names`)

R's `read.csv()` applies `make.names()` to **column headers** by default (`check.names=TRUE`). With the wrong (transposed) orientation, column headers are sample IDs — mangling them affects `ncol` mismatch detection only superficially.

**With the corrected orientation (samples × genes)**, column headers become **gene names**. HGNC symbols containing `-` (e.g. `HLA-A`, `MIR-21`, `H2-Aa`) would be mangled to `HLA.A`, `MIR.21`, `H2.Aa`. Since FSQN uses **position-based** column iteration (not name matching), this does not break the normalization itself, but:

- The output CSV is written with mangled gene names
- `pd.read_csv` reads back mangled gene names as column labels
- Downstream code that accesses genes by original HGNC symbol would fail silently on mismatches

Fix: add `check.names=FALSE` to all `read.csv()` calls in the R block.

---

## 7. Tertiary Issue: Silent Failure with No Error Propagation

Because FSQN uses `cat()` instead of `stop()`:
- rpy2 receives no R condition — no Python exception is raised
- The job completes normally with `status: "ok"` in the JSON sidecar
- `r2_batch = nan` (because the empty matrix has no values to compute ANOVA on)
- An empty TSV.gz is uploaded to S3 without any warning

The `if not os.path.exists(out_path)` guard in the current code cannot catch this case because `write.csv(NULL, ...)` does create the file.

Fix: add an explicit NULL check in R before writing, or check the output dimensions in Python after reading back.

---

## 8. Proposed Fixes

### Fix A (primary): Remove `.T` transpose, correct orientation and return

```python
def normalize_fsqn_r(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL, target_group: str = "RNASeq_FF_PolyA", **kw: object,
) -> pd.DataFrame:
    import tempfile

    exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df

    groups      = ann_df.loc[exp_in.index, batch_col].astype(str)
    target_mask = (
        groups == target_group
        if target_group in groups.values
        else pd.Series(True, index=exp_in.index)
    )
    with tempfile.TemporaryDirectory() as td:
        ref_path   = os.path.join(td, "ref.csv")
        query_path = os.path.join(td, "query.csv")
        out_path   = os.path.join(td, "out.csv")

        # FSQN expects SAMPLES × GENES (rows=samples, columns=genes) — no .T
        exp_in.loc[target_mask].to_csv(ref_path)
        exp_in.to_csv(query_path)

        ro.r(f"""
            library(FSQN)
            ref   <- as.matrix(read.csv(\"{ref_path}\",   row.names=1, check.names=FALSE))
            query <- as.matrix(read.csv(\"{query_path}\", row.names=1, check.names=FALSE))
            if (ncol(query) != ncol(ref)) stop(paste0(
                "FSQN column mismatch: ncol(query)=", ncol(query),
                " ncol(ref)=", ncol(ref)))
            out <- quantileNormalizeByFeature(query, ref)
            if (is.null(out)) stop("quantileNormalizeByFeature returned NULL")
            write.csv(out, \"{out_path}\", row.names=TRUE)
        """)
        if not os.path.exists(out_path):
            raise RuntimeError("FSQN R: quantileNormalizeByFeature returned no output")
        result = pd.read_csv(out_path, index_col=0)

    if result.shape[1] == 0:
        raise RuntimeError(
            f"FSQN R: output has 0 genes (shape {result.shape}); "
            "check R logs for quantileNormalizeByFeature errors"
        )

    _r_gc()
    # result is already samples × genes — no .T needed
    return result.reindex(exp_df.index)
```

**Key changes:**
1. `exp_in.loc[target_mask].to_csv(ref_path)` — no `.T` (samples × genes)
2. `exp_in.to_csv(query_path)` — no `.T` (samples × genes)
3. `check.names=FALSE` in both `read.csv()` calls — preserves HGNC gene names with `-`
4. `stop()` instead of `cat()` for dimension mismatch — raises catchable R error
5. Explicit NULL guard with `stop()` before `write.csv`
6. Python-side shape guard after reading back
7. `return result.reindex(exp_df.index)` — no `.T` (result is already samples × genes)
8. `exp_in = exp_df.dropna(axis=1) ...` — defensive NA guard for imputed data

### Fix B (optional enhancement): Per-batch normalization

The current approach normalizes all non-reference samples at once in a single FSQN call. An alternative is to call FSQN per non-reference batch, which matches the usage pattern described in the FSQN paper:

```python
batches  = groups.unique()
parts    = [exp_in.loc[target_mask]]   # reference batch unchanged
for batch in batches:
    if batch == target_group:
        continue
    batch_idx = exp_in.index[groups == batch]
    # write batch and ref, call FSQN, collect result
    normalized_batch = _fsqn_r_one_batch(exp_in.loc[batch_idx], ref_exp, td)
    parts.append(normalized_batch)
result = pd.concat(parts).reindex(exp_df.index)
```

This approach is more conservative (each batch processed independently) and makes debugging easier. However it is much slower for 88 cohorts. Fix A (single call) is mathematically equivalent and preferred.

### Fix C: Verify consistency with the working SOM pipeline

The pre-computed FSQN result at `$FL_DATA_ROOT/fsqn_normalized_exp_R.tsv` was produced outside the benchmark pipeline (presumably using the correct orientation). After applying Fix A, the benchmark output for `A_confirmed_bad × strict × 16_fsqn_r × post_rm=False` should closely match the SOM pipeline's FSQN output. Checking Pearson correlation of overlapping samples/genes between the two would confirm Fix A is correct.

---

## 9. Impact on Existing S3 Results

All S3 keys matching `*__16_fsqn_r__*.tsv.gz` for non-microarray strategies currently contain empty matrices (0 genes). They must be deleted and re-run after applying Fix A:

```bash
# List affected keys (preview, do not delete yet)
aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/exp/ \
    | grep "16_fsqn_r" \
    | grep -v "F_microarray_only\|G_affymetrix_only"

# Re-run after fix (in the pod)
python run_norm_parallel.py \
    --methods 16_fsqn_r \
    --n-workers 4
```

Note: the `--skip-if-exists` flag must be **omitted** (or the existing empty files must be deleted) for the re-run to overwrite them.

The `F_microarray_only` and `G_affymetrix_only` results for `16_fsqn_r` are also semantically wrong (they normalised all samples against themselves, not against RNASeq_FF_PolyA) — but since no PolyA reference exists in those datasets, the fallback behavior (all-samples quantile normalization) is arguably reasonable. These can optionally be re-run with Fix A to verify the fallback path still works correctly.

---

## 10. Summary Table

| # | Issue | Root cause | Fix |
|---|---|---|---|
| 1 | **Empty output for RNA-seq strategies** | `.T` in Python produces wrong GENES×SAMPLES orientation for FSQN which requires SAMPLES×GENES; `ncol` check fails when `ncol(ref) ≠ ncol(query)` | Remove `.T` from both `to_csv()` calls and from the `return` statement |
| 2 | **Silent failure** | FSQN uses `cat()` not `stop()`; rpy2 ignores it; `write.csv(NULL)` writes a `(0,0)` CSV | Add R-side `stop()` guards and Python-side shape assertion |
| 3 | **Gene name mangling** | Default `check.names=TRUE` converts HGNC names with `-` to `.` | Add `check.names=FALSE` to both `read.csv()` calls |
| 4 | **F/G produce wrong-semantics output** | Fallback makes `ref = query` (no reference batch present), equivalent to standard QN not FSQN | No data loss; acceptable fallback; document in code |
