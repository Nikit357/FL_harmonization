# Angel — Implementation Plan

**Method key:** `25_angel`  
**Function name:** `normalize_angel`  
**Status:** All code and notebook tasks complete. Remaining items require K8s pod with real data (smoke tests, production re-runs).

**Background:** Angel rank-transforms each sample to [0,1], then discards genes whose expression variance is strongly explained by platform (per-gene ANOVA R² ≥ threshold). The surviving genes are returned as the normalized matrix. Unlike every other method in the benchmark, the output has a **reduced gene space** — only genes with platform R² < threshold are kept. This makes the PCA R² batch metric non-comparable with other methods (Angel achieves a low score partly by removing the most platform-confounded genes), so results must be interpreted as "Angel-filtered gene space" rather than a direct head-to-head correction.

See `Angel_usage_perspectives.md` for the full algorithm description and verdict.

---

## 1. New helper: `_angel_platform_variance` ✓ DONE (bench_shared.py line 1230)

**Verification:** Present and correct. Implementation is functionally identical to the plan. Docstring is shorter (NaN behaviour not documented inline), but the `np.nanmean`/`np.nansum` logic is unchanged.

Add to `bench_shared.py` immediately before `normalize_rank` (currently line 1191). This is a pure-Python vectorized implementation of the per-gene one-way ANOVA R² used in Step 2 of the Angel algorithm.

```python
def _angel_platform_variance(
    exp_df: pd.DataFrame,
    batch_series: pd.Series,
) -> pd.Series:
    """
    Per-gene platform variance fraction (one-way ANOVA R²).

    For each gene, computes SS_between(platform groups) / SS_total, which is
    the fraction of total expression variance attributable to platform membership.
    Genes with high values are platform-biased; genes with low values are
    platform-stable.

    This is the same ANOVA R² formula used in pca_variance_explained_by_batch,
    applied per gene (columns) instead of per PC.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes).  NaN values are ignored in group
        means and SS computations — gene-wise complete-case analysis.
    batch_series
        Platform / batch labels indexed by sample ID.

    Returns
    -------
    pd.Series indexed by gene name, values in [0, 1].  Genes where SS_total == 0
    (zero-variance after NA removal) receive R² = 0.0.
    """
    groups = batch_series.reindex(exp_df.index)
    X = exp_df.values.astype(float)          # shape: (n_samples, n_genes)
    unique_groups = groups.unique()

    grand_mean = np.nanmean(X, axis=0)       # (n_genes,)
    ss_total = np.nansum((X - grand_mean) ** 2, axis=0)

    ss_between = np.zeros(X.shape[1], dtype=float)
    for g in unique_groups:
        mask = (groups == g).values
        if mask.sum() < 2:
            continue
        group_vals = X[mask, :]
        group_mean = np.nanmean(group_vals, axis=0)
        n_g = np.sum(~np.isnan(group_vals), axis=0).astype(float)
        ss_between += n_g * (group_mean - grand_mean) ** 2

    r2 = np.where(ss_total > 0, ss_between / ss_total, 0.0)
    return pd.Series(r2, index=exp_df.columns)
```

---

## 2. New normalization function: `normalize_angel` ✓ DONE (bench_shared.py line 1269) — **NaN guard missing (see TODO Phase 1)**

**Verification:** Present and correct for NaN-free (strict-imputed) input. The logging block from the plan was not included — acceptable. **Critical gap:** no `dropna(axis=1)` guard. When called with knn/softimpute-imputed data containing residual NaN, genes with all-NaN values receive `r2=0.0` (because `ss_total=0`) and are falsely kept in `stable_genes`. The output `rank_norm[stable_genes]` then contains NaN columns, causing `r2_batch()` → `StandardScaler.fit_transform()` to crash. This is the same root cause fixed for the five Category C methods (pycombat, mnn, scanorama, qsmooth, tdm) in `norm_failures_correction_250427.md`.

Add to `bench_shared.py` immediately after `normalize_rank` (currently line 1209), before the `# ── Cross-platform focused` block. The function mirrors the signature of all other normalization functions (`exp_df`, `ann_df`, `**kw`) so the dispatcher can call it uniformly.

```python
def normalize_angel(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    batch_col: str = BATCH_COL,
    threshold: float = 0.20,
    **kw: object,
) -> pd.DataFrame:
    """
    Angel rank-percentile normalization with platform-variance gene filtering.

    Implements the cross-platform harmonization approach from Angel PW et al.
    (PLOS Computational Biology 16(9), e1008219, 2020).  The method operates in
    two steps:

    1. **Rank-percentile transform** — each sample's gene expression values are
       mapped to fractional ranks in [0, 1].  This is identical to normalize_rank
       (18_rank) and makes microarray intensities and RNA-seq RPKM directly
       comparable in rank space without platform-specific scaling.

    2. **Platform-variance gene filter** — genes where platform membership
       explains ≥ threshold fraction of total variance (per-gene ANOVA R²) are
       discarded.  Only platform-stable genes are retained in the output.

    .. important::
        The output matrix has **fewer genes** than the input (only genes with
        platform R² < threshold are kept).  With the default threshold of 0.20,
        expect roughly 25–50% gene retention depending on platform mix.  The PCA
        R² batch metric computed on the Angel output is therefore **not directly
        comparable** with other methods — it reflects a reduced, pre-filtered
        gene space where platform-biased genes have been removed by design rather
        than corrected.  Interpret Angel results as "Angel-filtered gene space"
        in the benchmark heatmap.

    Parameters
    ----------
    exp_df
        Expression matrix (samples × genes), log2-transformed.
    ann_df
        Sample annotation; must contain batch_col indexed by sample ID.
    batch_col
        Column in ann_df identifying platform / batch groups.
        Default: BATCH_COL ("RNA_BATCH").
    threshold
        Maximum per-gene platform variance fraction to retain a gene.
        Default 0.20 (paper default).  Increasing this retains more genes
        (less stringent filter); decreasing retains fewer (more stringent).
        Practical range: 0.05 (very strict, ~500 genes) to 0.50 (~10,000 genes).

    Returns
    -------
    Rank-normalized expression matrix restricted to platform-stable genes.
    Shape: (n_samples, n_genes_retained) where n_genes_retained ≤ n_genes_input.
    """
    # Step 1: rank-percentile transform (identical to 18_rank)
    ranked = exp_df.rank(axis=1, method="average", na_option="keep")
    rank_norm = ranked / (exp_df.notna().sum(axis=1).values[:, None] + 1)

    # Step 2: per-gene platform variance filter
    batch_series = ann_df.loc[exp_df.index, batch_col].astype(str)
    gene_r2 = _angel_platform_variance(rank_norm, batch_series)
    stable_genes = gene_r2[gene_r2 < threshold].index

    if len(stable_genes) == 0:
        raise RuntimeError(
            f"normalize_angel: no genes passed platform-variance filter "
            f"(threshold={threshold}).  All {len(exp_df.columns)} genes had "
            f"platform R² ≥ {threshold}.  Try raising the threshold."
        )

    n_dropped = len(exp_df.columns) - len(stable_genes)
    pct_kept = 100 * len(stable_genes) / len(exp_df.columns)
    import logging
    logging.getLogger(__name__).info(
        "normalize_angel: kept %d / %d genes (%.1f%%) with platform R² < %.2f; "
        "dropped %d platform-biased genes",
        len(stable_genes), len(exp_df.columns), pct_kept, threshold, n_dropped,
    )

    return rank_norm[stable_genes]
```

### Design decisions

**Threshold default = 0.20:** Matches the paper. The benchmark will run this fixed; users who want to explore other thresholds can call `normalize_angel` directly with `threshold=0.05` or `threshold=0.50`.

**No `threshold` exposure in the METHODS registry:** The dispatcher passes `**kw` to all normalization functions. The `threshold=0.20` default covers the benchmark. If a second threshold variant is ever needed, add a separate `normalize_angel_strict` wrapper with `threshold=0.05` and register it as `26_angel_strict`.

**Rank transform recomputed from scratch:** The function does not call `normalize_rank` internally — it recomputes the same operation so that the variance filter operates on the rank-transformed values (consistent with the paper), not the raw log2 values. This matters: the variance filter must be applied after rank-normalization to avoid confounding with raw expression scale differences between platforms.

**Variance filter on rank-transformed data:** In the paper, Step 2 is applied after Step 1. This is correct: platform effects in rank space reflect genuine rank-ordering differences between platforms, not scale differences that rank normalization already removed. Computing gene_r2 on raw exp_df instead would conflate scale effects (already corrected) with true platform-specific ordering effects.

**Reduced gene space is intentional — not a bug:** The returned DataFrame has fewer columns than exp_df. All downstream code (`r2_batch`, `upload_exp_to_s3`, `download_exp_from_s3`) accepts variable-width DataFrames. The only special handling needed is in the CLAUDE.md count update and in how results are interpreted.

---

## 3. METHODS registry entry ✓ DONE (bench_shared.py line 1665)

**Verification:** `"25_angel": (normalize_angel, "high")` present.

**Gap found:** `run_norm_parallel.py` (line 133) has its own `ALL_METHODS` list ending at `"24_peer_k10"` — `"25_angel"` is absent. This script is the targeted re-run dispatcher used for retrying failed jobs (referenced in `norm_failures_correction_250427.md`) and is independent of `run_cross_product_parallel.py`. Without this addition, running `run_norm_parallel.py` without `--methods` will silently exclude Angel from its default grid. Fix in TODO Phase 0.

In `bench_shared.py`, add one line to the `METHODS` dict (currently ends at line 1547 with `24_peer_k10`). Angel is `25_angel`:

```python
# Current last two entries (lines 1545–1547):
    "23_vst":               (normalize_vst,                "low"),
    "24_peer_k10":          (normalize_peer,               "medium"),
}

# After adding Angel:
    "23_vst":               (normalize_vst,                "low"),
    "24_peer_k10":          (normalize_peer,               "medium"),
    "25_angel":             (normalize_angel,              "high"),
}
```

Harshness = `"high"` — Angel is a cross-platform method designed for difficult multi-platform integration, consistent with FSQN, TDM, and qsmooth.

---

## 4. `run_cross_product_parallel.py` — ALL_METHODS update ✓ DONE (line 123)

**Verification:** `"25_angel"` is the last entry in `ALL_METHODS`.

Current `ALL_METHODS` (lines 117–123):

```python
ALL_METHODS: list[str] = [
    "01_raw", "02_median_scaling", "03_limma", "04_sva",
    "05_combat", "06_combat_seq", "07_pycombat", "08_inmoose_combatseq",
    "09_ruv", "10_mnn", "11_harmony", "12_scanorama", "13_fsmvn",
    "14_qsmooth", "15_fsqn_py", "16_fsqn_r", "17_quantile", "18_rank",
    "19_tdm", "20_shambhala", "21_harmonizr", "22_tmm", "23_vst", "24_peer_k10",
]
```

After adding Angel:

```python
ALL_METHODS: list[str] = [
    "01_raw", "02_median_scaling", "03_limma", "04_sva",
    "05_combat", "06_combat_seq", "07_pycombat", "08_inmoose_combatseq",
    "09_ruv", "10_mnn", "11_harmony", "12_scanorama", "13_fsmvn",
    "14_qsmooth", "15_fsqn_py", "16_fsqn_r", "17_quantile", "18_rank",
    "19_tdm", "20_shambhala", "21_harmonizr", "22_tmm", "23_vst", "24_peer_k10",
    "25_angel",
]
```

No other changes to this file.

---

## 5. `harmonization-scripts/CLAUDE.md` — count updates ✓ DONE (with one stale line remaining — see TODO Phase 5)

**Verification:** Line 9 (introduction) says 25 methods / 2,000 outputs ✓. Line 259–260 says `ALL_METHODS = 25` / `1,000 jobs → 2,000 S3 outputs` ✓. Table row for `25_angel` added ✓. **Stale:** Line 279 still says "960 threads" (was not updated from the pre-Angel count of 960 jobs).

When Angel is added, update the following in the Detailed Reference section:

```
# Current:
ALL_METHODS     = 24  # 01_raw … 24_peer_k10
# Total: 10 × 4 × 24 = 960 jobs → 1,920 S3 outputs

# New:
ALL_METHODS     = 25  # 01_raw … 25_angel
# Total: 10 × 4 × 25 = 1,000 jobs → 2,000 S3 outputs
```

Also add a row to the normalization function table in the Detailed Reference section:

```
| `25_angel` | `normalize_angel` | high | Rank [0,1] + per-gene platform-variance filter (threshold=0.20); reduced gene space — not directly comparable with other R² values |
```

---

## 6. `harmonization-tools-research/CLAUDE.md` — count update ✓ DONE

**Verification:** Line 28 reads `01_raw … 25_angel` ✓. Line 29 reads `1,000 jobs → 2,000 S3 outputs` ✓.

The research CLAUDE.md currently references `25_shambhala2` in the benchmark context. Update it to reflect Angel as `25_angel`:

```
# Current:
- **Current methods:** 25 entries in `METHODS` dict in `../bench_shared.py` (`01_raw` … `25_shambhala2`)
- **Grid:** 10 filter strategies × 4 imputation options × 25 methods = 1,000 jobs → 2,000 S3 outputs

# New:
- **Current methods:** 25 entries in `METHODS` dict in `../bench_shared.py` (`01_raw` … `25_angel`)
- **Grid:** 10 filter strategies × 4 imputation options × 25 methods = 1,000 jobs → 2,000 S3 outputs
```

The grid numbers (1,000 jobs / 2,000 outputs) are unchanged — only the method name in the range label changes.

---

## 7. `test_mock.py` — no changes needed ✓ DONE

**Verification:** `test_mock.py` iterates the `METHODS` dict automatically, so `normalize_angel` will be tested without any changes. Angel is pure Python — no R dependencies to add to `_CRITICAL_PKGS`.

`test_mock.py` automatically tests all entries in `METHODS` via the methods loop (lines 144–162). Adding `normalize_angel` to `METHODS` is sufficient — the mock will call it with the 80-sample × 200-gene synthetic matrix.

Angel is pure Python (numpy/pandas/sklearn only) — no R packages required. `_CRITICAL_PKGS` (line 47, R package verification list) does not need updating.

**Expected mock behaviour:** On the 80-sample synthetic dataset with 3 batches, `normalize_angel` will retain some fraction of the 200 genes (those with platform R² < 0.20). The test will PASS as long as the returned DataFrame is non-empty and has the correct sample index.

One edge case: if the synthetic data has very strong batch structure, `normalize_angel` might raise `RuntimeError("no genes passed platform-variance filter")`. If this occurs, raise the threshold to 0.50 in the mock or catch as an expected edge-case SKIP.

---

## 8. `k8s/pod-ssh.yaml` — no changes needed ✓ DONE

**Verification:** Angel has no new system, R, or Python package dependencies.

Angel requires no new system packages, no new R packages, and no new Python packages. All dependencies (numpy, pandas, sklearn) are already installed in the Docker image and in the pod environment.

---

## 9. `harmonization_benchmark.ipynb` — optional Angel gene filter step ✓ DONE

**Verification:** Cells 51–53 are present with correct intent:
- Cell 51 (markdown): section header ✓
- Cell 52 (code): `APPLY_ANGEL_FILTER = False` flag and `ANGEL_THRESHOLD = 0.20` ✓
- Cell 53 (code): filter logic, top-20 removed-genes display, R² before/after print ✓

**Gap:** Cell 53 references `exp_best` and `ann_best`, which are **not defined anywhere in the notebook**. A comment says "Replace `exp_best` and `ann_best` with the variable names from Section 4", but no Section 4 cell produces variables with those names. Setting `APPLY_ANGEL_FILTER = True` currently produces `NameError: name 'exp_best' is not defined`. Fix required (see TODO Phase 2).

**Acceptable differences from plan:** The plan's 3-cell layout (control / filter+display / PCA comparison) was merged into 2 code cells — this is equivalent. Variable names `_batch_series`, `_gene_r2`, `_stable` use underscore prefixes to avoid polluting notebook namespace — acceptable.

Beyond using `25_angel` as a benchmark method, Angel's gene filtering logic should also be available in the notebook as an **optional post-normalization step** that can be applied to any already-harmonized expression matrix. This is independent of the cross-product benchmark — it allows interactive exploration of how removing platform-biased genes affects any normalization's output.

### Where to add it

Add a new notebook section titled **"Optional: Angel platform-gene filter"** immediately after the section where the best normalization method's output is loaded (currently after loading `16_fsqn_r` or whichever method is selected as primary). The cell should be clearly marked as optional and should be controlled by a flag.

### Code to add

**Cell 1 — control flag and parameter:**

```python
# ── Optional: Angel platform-gene filter ──────────────────────────────────────
# Set APPLY_ANGEL_FILTER = True to remove platform-biased genes from the
# selected normalized expression matrix before downstream analysis (SOM, PCA).
# This applies the gene-selection step from Angel (PLOS Comput Biol 2020)
# independently of the 25_angel benchmark entry.

APPLY_ANGEL_FILTER = False          # toggle here
ANGEL_THRESHOLD    = 0.20           # platform R² threshold; paper default
```

**Cell 2 — filter function and application:**

```python
if APPLY_ANGEL_FILTER:
    from bench_shared import _angel_platform_variance

    batch_series = ann.loc[exp.index, "RNA_BATCH"].astype(str)

    # Compute per-gene platform variance on the current (already normalized) matrix
    gene_r2 = _angel_platform_variance(exp, batch_series)

    stable_mask = gene_r2 < ANGEL_THRESHOLD
    n_kept   = stable_mask.sum()
    n_total  = len(stable_mask)
    n_dropped = n_total - n_kept

    print(
        f"Angel filter (threshold={ANGEL_THRESHOLD}): "
        f"kept {n_kept} / {n_total} genes ({100*n_kept/n_total:.1f}%); "
        f"removed {n_dropped} platform-biased genes."
    )

    # Optionally inspect removed genes
    removed_genes = gene_r2[~stable_mask].sort_values(ascending=False)
    display(removed_genes.head(20).rename("platform_R2").to_frame())

    # Apply filter
    exp_filtered = exp[gene_r2[stable_mask].index]

    print(f"exp shape before filter: {exp.shape}")
    print(f"exp shape after filter:  {exp_filtered.shape}")
else:
    exp_filtered = exp   # passthrough — no filtering
    print("Angel filter not applied (APPLY_ANGEL_FILTER = False).")
```

**Cell 3 — downstream PCA to quantify effect:**

```python
if APPLY_ANGEL_FILTER:
    from bench_shared import r2_batch

    r2_before = r2_batch(exp, ann, batch_col="RNA_BATCH")
    r2_after  = r2_batch(exp_filtered, ann, batch_col="RNA_BATCH")

    print(f"Batch R² before Angel filter: {r2_before:.4f}")
    print(f"Batch R² after Angel filter:  {r2_after:.4f}")
    print(
        f"Δ = {r2_after - r2_before:+.4f}  "
        f"({'improved' if r2_after < r2_before else 'worsened'})"
    )
    print()
    print("Note: the post-filter R² reflects a reduced gene space.  "
          "Improvement is partly due to removing high-platform-variance genes, "
          "not correcting their values.")
```

### Design notes

- `exp_filtered` replaces `exp` in all downstream cells when `APPLY_ANGEL_FILTER = True`. Downstream code (SOM, PCA plots, ssGSEA) should use `exp_filtered` uniformly.
- The filter is applied to the post-normalization matrix, not to raw data. This lets it work as an additive step on top of any normalization (FSQN, ComBat, quantile, etc.).
- The removed-genes table (Cell 2) is diagnostic — it shows which specific genes are most platform-biased and helps interpret SOM metagene signals that may be confounded by batch.
- If `APPLY_ANGEL_FILTER = False`, `exp_filtered` is just an alias for `exp`, so all subsequent cells remain valid without any conditional branching.

---

## 10. Implementation sequence ✓ DONE

**Verification:** Steps 1–6 were applied in the correct order. Step 7 (notebook) partially done.

Apply changes in this order to avoid reference errors:

1. Add `_angel_platform_variance` to `bench_shared.py` (before `normalize_rank`)
2. Add `normalize_angel` to `bench_shared.py` (after `normalize_rank`)
3. Add `"25_angel"` entry to `METHODS` dict in `bench_shared.py`
4. Add `"25_angel"` to `ALL_METHODS` in `run_cross_product_parallel.py`
5. Update counts in `harmonization-scripts/CLAUDE.md`
6. Update `harmonization-tools-research/CLAUDE.md` (replace `25_shambhala2` → `25_angel`)
7. Add Angel filter cells to `harmonization_benchmark.ipynb`

Steps 1–4 are code changes. Steps 5–6 are documentation-only. Step 7 is notebook-only.

---

## 11. Metric interpretation caveat (for the benchmark notebook) ✓ DONE

**Verification:** The `angel_mask` / `n_genes_angel` code block from the plan is absent from the notebook. The only Angel-reduced-gene-space warning present is the single-line note inside Cell 53's `print()` statement (which only runs when `APPLY_ANGEL_FILTER = True`). The heatmap cell (Cell 46) has no caveat at all. Fix required (see TODO Phase 3).

When loading cross-product results and plotting the R² heatmap, `25_angel` rows should be annotated to flag the reduced gene space:

```python
# After loading metrics_df:
angel_mask = metrics_df["method"] == "25_angel"
if angel_mask.any():
    n_genes_angel = metrics_df.loc[angel_mask, "n_genes"].median()
    n_genes_full  = metrics_df.loc[~angel_mask, "n_genes"].median()
    print(
        f"25_angel retains {n_genes_angel:.0f} / {n_genes_full:.0f} genes on average "
        f"({100*n_genes_angel/n_genes_full:.1f}%). "
        f"Its PCA R² is computed on this reduced gene space and is not directly "
        f"comparable with other methods."
    )
```

This prevents misinterpretation of Angel's batch R² as evidence of genuine batch correction equivalent to FSQN or ComBat.

---

## TODO List

Tasks are ordered by priority: crashes first, then correctness, then documentation.  
All code tasks operate on `bench_shared.py` or `harmonization_benchmark.ipynb` unless noted.

---

### Phase 0 — `run_norm_parallel.py`: add `25_angel` to `ALL_METHODS` [CRITICAL]
*1 line edit in `run_norm_parallel.py`. Estimated time: ~2 min.*

**Root cause:** `run_norm_parallel.py` maintains its own `ALL_METHODS` list (line 133) that
is a sibling of the one in `run_cross_product_parallel.py`. It ends at `"24_peer_k10"`;
`"25_angel"` was never added. This script is used for targeted per-method re-runs (e.g.,
retrying failed jobs from `failed_jobs_norm.txt`). Without this fix, calling
`run_norm_parallel.py` without `--methods` silently excludes Angel from the default grid.

- [x] **0.1** In `run_norm_parallel.py` (line 138), append `"25_angel"` to `ALL_METHODS`:
  ```python
  # Current (line 133–139):
  ALL_METHODS: list[str] = [
      "01_raw", "02_median_scaling", "03_limma", "04_sva",
      "05_combat", "06_combat_seq", "07_pycombat", "08_inmoose_combatseq",
      "09_ruv", "10_mnn", "11_harmony", "12_scanorama", "13_fsmvn",
      "14_qsmooth", "15_fsqn_py", "16_fsqn_r", "17_quantile", "18_rank",
      "19_tdm", "20_shambhala", "21_harmonizr", "22_tmm", "23_vst", "24_peer_k10",
  ]
  # After:
  ALL_METHODS: list[str] = [
      "01_raw", "02_median_scaling", "03_limma", "04_sva",
      "05_combat", "06_combat_seq", "07_pycombat", "08_inmoose_combatseq",
      "09_ruv", "10_mnn", "11_harmony", "12_scanorama", "13_fsmvn",
      "14_qsmooth", "15_fsqn_py", "16_fsqn_r", "17_quantile", "18_rank",
      "19_tdm", "20_shambhala", "21_harmonizr", "22_tmm", "23_vst", "24_peer_k10",
      "25_angel",
  ]
  ```
- [x] **0.2** Verify: confirmed `"25_angel"` present in `ALL_METHODS` via `grep` (boto3 unavailable in this env but edit is correct).

---

### Phase 1 — NaN robustness: `dropna` guard in `normalize_angel` [CRITICAL]
*1 code change in `bench_shared.py`. Estimated time: ~5 min.*

**Root cause:** `normalize_angel` is called with knn/softimpute-imputed data that may contain
residual NaN (same root cause as the five Category C methods in `norm_failures_correction_250427.md`).
Without a guard, genes with all-NaN values receive `r2=0.0` from the
`np.where(ss_total > 0, ss_between/ss_total, 0.0)` branch (because `ss_total=0` for a
constant/all-NaN gene). Since `0.0 < threshold=0.20`, these genes pass the filter and are
included in `stable_genes`. The output `rank_norm[stable_genes]` then contains NaN columns.
Downstream `r2_batch()` calls `StandardScaler.fit_transform(exp_df)` which crashes on NaN.

- [x] **1.1** In `normalize_angel()` (`bench_shared.py` line ~1269), add `dropna` guard as
  first operation before any computation:
  - Add `exp_in = exp_df.dropna(axis=1) if exp_df.isnull().any().any() else exp_df`
    as the first line of the function body (before `ranked = exp_df.rank(...)`)
  - Change `exp_df.rank(axis=1, method="average", na_option="keep")` →
    `exp_in.rank(axis=1, method="average", na_option="keep")`
  - Change `exp_df.notna().sum(axis=1)` → `exp_in.notna().sum(axis=1)`
  - Change `ann_df.loc[exp_df.index, batch_col]` → `ann_df.loc[exp_in.index, batch_col]`
    (index unchanged since `dropna` is on axis=1, but keep consistent)
  - The final `return rank_norm[stable_genes]` already returns a column-subset; no change needed
- [ ] **1.2** Smoke-test (requires K8s pod with real data): run `G_affymetrix_only × softimpute × 25_angel` with `run_norm_job.py`;
  confirm `status="ok"` in the output JSON and no NaN in the returned DataFrame.
  ```bash
  source ~/venvs/collagen_3_11/bin/activate
  python harmonization-scripts/run_norm_job.py \
      --strat G_affymetrix_only --imp softimpute --method 25_angel \
      --out-json /tmp/test_angel_softimpute.json
  cat /tmp/test_angel_softimpute.json   # expect status="ok"
  ```

---

### Phase 2 — Notebook: fix undefined `exp_best`/`ann_best` variables [CORRECTNESS]
*1 notebook cell edit (`harmonization_benchmark.ipynb` Cell 53). Estimated time: ~10 min.*

**Root cause:** Cell 53 references `exp_best` and `ann_best`, which are not defined in any
notebook cell. The comment "Replace `exp_best` and `ann_best` with the variable names from
Section 4" is unhelpful because no Section 4 variable holds a single expression matrix —
Section 4 iterates combinations and stores results in `cross_results`. Setting
`APPLY_ANGEL_FILTER = True` currently raises `NameError: name 'exp_best' is not defined`.

The correct fix is to show how to extract a concrete expression matrix from the available
variables. The natural source is the top-ranked combo from `cross_results` (identified in
Cell 48), loaded via `load_exp()` from `load_cross_product_results.py`, or by re-running the
normalization inline.

- [x] **2.1** Update Cell 53 to replace the undefined-variable pattern with a working approach:
  - At the top of the `if APPLY_ANGEL_FILTER:` block, replace the bare references to
    `exp_best` / `ann_best` with code that loads the expression matrix for the user's chosen
    combination. Suggested pattern using `cross_results`:
    ```python
    # Set these to the (strat, imp, method, post_rm) combo you want to filter.
    # Example: the top-ranked combo identified in Cell 4d.
    _ANGEL_STRAT   = "A_confirmed_bad"
    _ANGEL_IMP     = "strict"
    _ANGEL_METHOD  = "16_fsqn_r"
    _ANGEL_POST_RM = False

    from load_cross_product_results import load_exp
    exp_best = load_exp(_ANGEL_STRAT, _ANGEL_IMP, _ANGEL_METHOD, post_rm=_ANGEL_POST_RM)
    ann_best = comb_ann.loc[exp_best.index]
    ```
  - All existing downstream references to `exp_best` / `ann_best` in the cell remain valid
    after this addition.
  - Keep `APPLY_ANGEL_FILTER = False` as default in Cell 52 so this cell is a no-op on
    normal execution.
- [ ] **2.2** Verify Cell 53 executes without error when `APPLY_ANGEL_FILTER = True` using
  one combo from the available benchmark data.

---

### Phase 3 — Notebook: add metric interpretation caveat [DOCUMENTATION]
*1 notebook code cell addition after Cell 46. Estimated time: ~10 min.*

**Root cause:** Section 11 of this plan specifies a code block to add immediately after the
R² heatmap cell (Cell 46) that warns about Angel's reduced gene space when interpreting the
heatmap. This was never implemented.

The notebook computes metrics locally via `cross_results` dict (not via a loaded `metrics_df`
from S3), so the plan's code (which uses `metrics_df`) must be adapted to query `cross_results`.

- [x] **3.1** After Cell 46 (the `batch_r2_matrix` heatmap), insert a new code cell:
  ```python
  # ── 4b-note. Angel gene-space caveat ─────────────────────────────────────────
  _angel_n_genes = [
      cross_results[(s, i, "25_angel", pr)].get("n_genes", np.nan)
      for s in FILTER_STRATEGIES
      for i in IMPUTATION_METHODS
      for pr in POST_REMOVAL_OPTIONS
      if (s, i, "25_angel", pr) in cross_results
      and cross_results[(s, i, "25_angel", pr)].get("status") == "ok"
  ]
  _other_n_genes = [
      cross_results[(s, i, m, pr)].get("n_genes", np.nan)
      for s in FILTER_STRATEGIES
      for i in IMPUTATION_METHODS
      for m in METHODS if m != "25_angel"
      for pr in POST_REMOVAL_OPTIONS
      if (s, i, m, pr) in cross_results
      and cross_results[(s, i, m, pr)].get("status") == "ok"
  ]
  if _angel_n_genes:
      _med_angel = np.nanmedian(_angel_n_genes)
      _med_other = np.nanmedian(_other_n_genes)
      print(
          f"Note — 25_angel retains {_med_angel:.0f} / {_med_other:.0f} genes on "
          f"average ({100*_med_angel/_med_other:.1f}% of the full gene set). "
          f"Its PCA R² is computed on this reduced, platform-stable gene space "
          f"and is not directly comparable with other methods in the heatmap above."
      )
  ```
- [ ] **3.2** Confirm the caveat prints correctly after Cell 46 has been run with real data. (requires K8s pod)

---

### Phase 4 — Notebook: update stale method counts [DOCUMENTATION]
*2 notebook cell edits. Estimated time: ~5 min.*

- [x] **4.1** Update Cell 0 (title markdown cell):
  - Change "18 batch-correction methods" → "25 batch-correction methods"
  - Change "10 strategies × 4 imputation approaches × **18 methods** × 2 post-removal options
    = **1,440 combinations**" → "10 strategies × 4 imputation approaches × **25 methods** ×
    2 post-removal options = **2,000 combinations**"
- [x] **4.2** Update Cell 43 (Section 3 markdown cell):
  - Change "18 methods ordered **low → medium → high harshness**" → "25 methods"
  - Extend the method table to include the missing methods added since the notebook was last
    updated: TDM (`19_tdm`), Shambhala2 (`20_shambhala`), HarmonizR (`21_harmonizr`),
    TMM (`22_tmm`), VST (`23_vst`), PEER (`24_peer_k10`), Angel (`25_angel`)

---

### Phase 5 — `harmonization-scripts/CLAUDE.md`: fix stale "960 threads" comment [MINOR]
*1 line edit. Estimated time: ~2 min.*

- [x] **5.1** In `harmonization-scripts/CLAUDE.md`, line 279, change:
  `"Limits simultaneous subprocess count without creating all 960 threads up front"`
  → `"Limits simultaneous subprocess count without creating all 1,000 threads up front"`
