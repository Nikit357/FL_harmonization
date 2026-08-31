# Implementation Plan: Fix `normalize_fsqn_r` Empty Output

**Date:** 2026-05-09  
**Source:** `fsqn_r_empty_expression_research.md`  
**Files to modify:** `bench_shared.py`, S3 cleanup + re-run

---

## 1. Summary of Root Cause

`normalize_fsqn_r` transposes both matrices before writing to CSV (`exp_df.T.to_csv(...)`), producing **GENES × SAMPLES** orientation. FSQN expects **SAMPLES × GENES** (rows = samples, columns = genes). The FSQN `ncol` check then compares the number of samples in the query (e.g. 5444) against the number of samples in the reference (e.g. 1039); they differ, and the function silently returns `NULL` via `cat()`. The output is a `(0, 0)` DataFrame that, after `.T.reindex()`, becomes `(n_samples, 0)` — sample names present, zero genes.

Three bugs to fix simultaneously in the same function:

1. **Orientation** — remove `.T` from both `to_csv()` calls and from the `return` statement.
2. **Gene name mangling** — add `check.names=FALSE` to both R `read.csv()` calls.
3. **Silent failure** — replace FSQN's `cat()` error path with explicit R `stop()` guards and add a Python-side shape assertion.

---

## 2. Implementation: Per-Batch FSQN Calls

Each non-reference batch is normalised independently against the reference batch, and the reference batch's own samples are kept unchanged. This matches the usage pattern in the FSQN paper (training dataset vs. test dataset) and produces output fully consistent with how the SOM pipeline computed its pre-normalised FSQN file.

### 2.1 Mechanism

- **Reference batch samples** are passed through as-is. They already have the target distribution, so no transformation is needed.
- **Every other batch** gets its own `query_NNNN.csv` file. A single R session loads the reference matrix once, then loops over all query files and writes `out_NNNN.csv` for each. This avoids repeated Python–R round-trips while still normalising each batch independently.
- Results for all batches are concatenated and reindexed to match `exp_df.index`.
- **Fallback:** if the reference batch (`RNASeq_FF_PolyA`) is absent from the strategy (e.g. `F_microarray_only`, `G_affymetrix_only`), the entire dataset is used as both query and reference — equivalent to standard quantile normalization per gene.

### 2.2 File naming convention inside the temp directory

| File | Content |
|---|---|
| `ref.csv` | Reference batch only — samples × genes; written once |
| `query_0000.csv`, `query_0001.csv`, … | One file per non-reference batch (zero-padded index so R's `sort()` gives deterministic order) |
| `out_0000.csv`, `out_0001.csv`, … | FSQN output per batch; produced by R using `sub("/query_", "/out_", qf)` |

### 2.3 New `normalize_fsqn_r` implementation

Replace the function body in `bench_shared.py` at lines ~1150–1199:

```python
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

    # ── Fallback: no reference batch present in this strategy ──────────────
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

    # ── Main path: per-batch normalisation ─────────────────────────────────
    ref_exp         = exp_in.loc[groups == target_group]   # kept unchanged
    non_ref_batches = [b for b in groups.unique() if b != target_group]

    with tempfile.TemporaryDirectory() as td:
        ref_path = os.path.join(td, "ref.csv")
        ref_exp.to_csv(ref_path)   # written once; R reads it for every batch

        for i, batch in enumerate(non_ref_batches):
            exp_in.loc[groups == batch].to_csv(os.path.join(td, f"query_{i:04d}.csv"))

        ro.r(f"""
            library(FSQN)
            ref         <- as.matrix(read.csv("{ref_path}", row.names=1, check.names=FALSE))
            n_ref_genes <- ncol(ref)
            query_files <- sort(list.files("{td}", pattern="^query_.*\\.csv$",
                                           full.names=TRUE))
            for (qf in query_files) {{
                out_file <- sub("/query_", "/out_", qf)
                query    <- as.matrix(read.csv(qf, row.names=1, check.names=FALSE))
                if (ncol(query) != n_ref_genes) stop(paste0(
                    "FSQN gene count mismatch for ", qf,
                    ": ncol(query)=", ncol(query), " n_ref_genes=", n_ref_genes))
                out <- quantileNormalizeByFeature(query, ref)
                if (is.null(out)) stop(paste0(
                    "quantileNormalizeByFeature returned NULL for ", qf))
                write.csv(out, out_file, row.names=TRUE)
            }}
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
```

### 2.4 Summary of changes vs. current code

| Location | Old | New |
|---|---|---|
| `ref_path` write | `exp_df.loc[target_mask].T.to_csv(ref_path)` | `ref_exp.to_csv(ref_path)` (no `.T`) |
| `query_path` write | `exp_df.T.to_csv(query_path)` | one `query_NNNN.csv` per batch (no `.T`) |
| R `read.csv` calls | `check.names` default (TRUE) | `check.names=FALSE` everywhere |
| R error handling | none (`cat()` in FSQN swallowed) | `stop()` guards on mismatch and NULL |
| Python shape guard | none | `result.shape[1] == 0` → `RuntimeError` |
| return statement | `result.T.reindex(exp_df.index)` | `pd.concat(parts).reindex(exp_df.index)` |
| NA guard | none | `exp_in = exp_df.dropna(axis=1) if ...` |
| Reference batch handling | included in query (slight artefact) | kept unchanged, excluded from query |

---

## 3. Verification Plan

### 3.1 Local smoke test

After applying the fix, run `test_mock.py` with a synthetic mixed dataset (RNA-seq + microarray batches) to confirm `16_fsqn_r` no longer produces empty output:

```bash
source ~/venvs/collagen_3_11/bin/activate
python harmonization-scripts/test_mock.py 2>&1 | grep -E "fsqn_r|PASS|FAIL|ERROR"
```

Expected: `16_fsqn_r ... PASS` for all 4 imputation variants (strict, knn, missforest, softimpute).

### 3.2 Single-job validation against SOM pipeline output

Run `16_fsqn_r` on the standard benchmark strategy and compare gene-level correlations with the pre-computed SOM pipeline FSQN file at `$FL_DATA_ROOT/fsqn_normalized_exp_R.tsv`:

```bash
python harmonization-scripts/run_one_job.py \
    --strat A_confirmed_bad --imp strict --method 16_fsqn_r \
    --out-json /tmp/fsqn_r_check.json
```

Download the output from S3, intersect overlapping samples and genes with the SOM file, and compute Spearman correlation per gene. Expected: median gene correlation > 0.99 (the SOM pipeline FSQN was computed with the same R package and the same reference batch).

### 3.3 Shape and gene-name checks

```python
exp = download_exp_from_s3(s3_client, s3_key_exp("A_confirmed_bad", "strict", "16_fsqn_r", False))
assert exp.shape[1] > 0,                           "Expected non-zero genes"
assert not exp.isnull().all(axis=1).any(),          "All-NaN sample rows detected"
assert set(exp.columns) == set(original_gene_list), "Gene name mismatch (check.names mangling?)"
```

---

## 4. S3 Cleanup and Re-Run Plan

### 4.1 Identify affected keys

All `16_fsqn_r` S3 outputs for non-microarray strategies are currently empty and must be overwritten. The microarray-only outputs (F, G) are semantically wrong (they normalised against all samples, not the absent reference) and should also be re-run.

```bash
aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/exp/ \
    | awk '{print $4}' \
    | grep "16_fsqn_r"
```

### 4.2 Delete existing results

```bash
aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/exp/ \
    | awk '{print $4}' | grep "16_fsqn_r" \
    | xargs -I{} aws s3 rm \
        "s3://$FL_S3_BUCKET/FL_batch_correction/exp/{}"
```

Run this **only after** the fix is deployed to the pod and `test_mock.py` passes.

### 4.3 Re-run normalisation

In the pod, after syncing the fixed `bench_shared.py`:

```bash
python run_norm_parallel.py \
    --methods 16_fsqn_r \
    --n-workers 4
# Do NOT pass --skip-if-exists — the old keys were deleted in step 4.2
```

The per-batch approach processes ~88 cohorts per job inside a single R session. Estimated wall time: 10–20 min per `(strategy, imputation)` pair. With 4 workers: ~44 pairs ÷ 4 workers × 15 min ≈ ~3 h total.

---

## 5. To-Do List

### Track 1 — Code fix in `bench_shared.py` ✅

- [x] **1.1** Open `bench_shared.py`, locate `normalize_fsqn_r` (lines ~1150–1199).
- [x] **1.2** Replace the entire function body with the per-batch implementation. Used explicit path embedding per batch instead of `list.files` (more reliable; avoids R file-discovery issues).
- [x] **1.3** Confirm the docstring correctly describes the per-batch approach and the `samples × genes` orientation requirement.
- [x] **1.4** Verify no other code in `bench_shared.py` calls `normalize_fsqn_r` in a way that assumes the old (genes × samples) return orientation.
- [x] **1.5** `normalize_fsqn_py` returns correct `(n_samples, n_genes)` shape; no orientation bug. Note: its algorithm is standard QN (not per-gene FSQN) — pre-existing issue, out of scope.
- [x] **1.6** `AST OK` — no syntax errors.
- [x] **1.7** `import OK` — module loads cleanly.

### Track 2 — Local smoke test ✅

- [x] **2.1** `test_mock.py`: `16_fsqn_r PASS` for all 4 imputation variants (strict, knn, missforest, softimpute).
- [x] **2.2** Additional unit tests confirmed: (a) main path output shape `(30, 50)` with 2 non-ref batches; (b) reference batch preserved exactly; (c) gene names with hyphens (`HLA-A`, `MIR-21`) preserved unchanged — `check.names=FALSE` working.

### Track 3 — Sync to pod and validate (requires pod access)

- [ ] **3.1** Sync fixed `bench_shared.py` to the pod (port-forward must be active on `localhost:2222`):
  ```bash
  rsync -avz -e "ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
      ~/fl_subset/harmonization-scripts/bench_shared.py \
      root@localhost:/app/harmonization-scripts/bench_shared.py
  ```
- [ ] **3.2** In the pod, run the single-job validation (section 3.2 above) for `A_confirmed_bad × strict × 16_fsqn_r`.
- [ ] **3.3** Download the output and compute Spearman correlation against the SOM pipeline FSQN file. Confirm median gene correlation > 0.99.
- [ ] **3.4** Run a second single-job test for an imputed strategy — e.g. `A_confirmed_bad × knn × 16_fsqn_r` — to confirm the fix works with KNN-imputed data.
- [ ] **3.5** Run a microarray-only strategy test — e.g. `F_microarray_only × strict × 16_fsqn_r` — to confirm the fallback path (no reference batch) still produces non-empty output.

### Track 4 — S3 cleanup and re-run (requires pod access)

- [ ] **4.1** List all existing `16_fsqn_r` S3 keys (section 4.1) and review the list before deleting.
- [ ] **4.2** Delete all `16_fsqn_r` S3 outputs (section 4.2).
- [ ] **4.3** Launch `run_norm_parallel.py --methods 16_fsqn_r --n-workers 4` in the pod (section 4.3).
- [ ] **4.4** Monitor `failed_jobs_norm.txt` and the pod log during the run.
- [ ] **4.5** After completion, spot-check outputs from at least 3 different strategies (one RNA-seq, one mixed, one microarray-only) to confirm non-zero gene counts and plausible value ranges.
- [ ] **4.6** Re-run `run_metrics_concat.py` to regenerate `metrics_comprehensive.csv` with corrected `16_fsqn_r` results.

### Track 5 — Documentation ✅

- [x] **5.1** Updated `16_fsqn_r` entry in `harmonization-scripts/CLAUDE.md` with: SAMPLES × GENES orientation requirement, per-batch approach, fallback behaviour, and CRITICAL orientation warning.
- [x] **5.2** Tracks 1 and 2 completed. Tracks 3 and 4 require pod access (Daniil to run after rsync).
