# Implementation Plan: New Metrics for Harmonization Benchmark
**Date:** 2026-05-16  
**Author:** Daniil Nikitin  
**Status:** Plan — approved, not implemented yet

---

## Overview

Five changes are planned for the harmonization metrics pipeline:

| Feature | New keys in JSON | Group | Sentinel key |
|---|---|---|---|
| Incremental JSON computation | (no new keys) | `run_metrics_job.py` behavior | — |
| WaterMelon (WM) score | `wm_{col}`, `wm_mean_batch`, `wm_mean_bio`, `wm_ratio_bio_batch` | New **Group I** | `wm_RNA_BATCH` |
| PC variance explained (%) | `pct_var_pc{1..10}`, `pct_var_cum_top10` | New **Group J** | `pct_var_pc1` |
| Post-dropna gene/sample counts | `n_genes_noNA`, `pct_genes_noNA`, `n_samples_noNA`, `pct_samples_noNA`, `n_genes_allNA`, `n_samples_allNA`, `n_na_cells`, `pct_na_cells` | New **Group K** | `n_genes_noNA` |

**Why separate groups for J and K:** The incremental JSON logic skips a group if its sentinel key is already present in the stored JSON. PC variance and dropna metrics are new additions that need to be computed for jobs that already have Groups A and E completed. Creating Groups J and K with their own sentinels ensures the incremental logic will run them on the next pass without touching existing A–H results.

All additions are backward-compatible: new keys are appended to the JSON sidecar; existing keys are never overwritten.

---

## Feature 0 — Incremental JSON Computation

### Rationale

When new metric groups are added (Groups I, J, K), it is wasteful to recompute all existing groups from scratch. The worker must instead detect which groups already have valid results in the existing JSON sidecar and skip them, computing only the missing ones.

### Behavior specification

At the start of `run_metrics_job.py`, before downloading the expression matrix:

1. **Check if a metrics JSON sidecar already exists on S3** for this `(strat, imp, method, post_rm)` combination.
2. If it exists, **download and parse it** into a `prior_metrics` dict.
3. **Determine which groups need recomputation** by checking a sentinel key per group against `prior_metrics`. A group needs recomputation if its sentinel key is absent from `prior_metrics` or has a `None` value.
4. Set the `groups` argument of `compute_all_metrics()` to only the groups that need recomputing.
5. If all requested groups are already complete, exit early (no download, no computation).
6. **Merge** the new results with `prior_metrics` (new keys take precedence for recomputed groups; old keys are kept as-is for skipped groups).
7. Upload the merged dict as the new sidecar.

If the existing JSON has `status != "ok"` or is unparseable, treat it as absent (full recomputation).

### Sentinel keys per group

```python
GROUP_SENTINEL_KEYS = {
    "E": "n_samples",
    "A": "r2_RNA_BATCH",
    "B": "kbet_RNA_BATCH",
    "C": "umap_centroid_disp_RNA_BATCH",
    "D": "ks_mean_stat_RNA_BATCH",
    "F": "vp_RNA_BATCH",
    "G": "graph_conn_RNA_BATCH",
    "H": "dist_ratio_RNA_BATCH",
    "I": "wm_RNA_BATCH",
    "J": "pct_var_pc1",
    "K": "n_genes_noNA",
}
```

A group is re-run if its sentinel key is missing OR its value is `None`.

### Implementation in `run_metrics_job.py`

```python
def _load_prior_metrics(s3_client, strat, imp, method, post_rm) -> dict | None:
    """Download and parse the existing metrics JSON sidecar, or return None."""
    key = s3_key_metrics(strat, imp, method, post_rm)
    try:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        data = json.loads(obj["Body"].read())
        if data.get("status") != "ok":
            return None
        return data
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception:
        return None


def _groups_to_recompute(prior: dict | None, requested_groups: set[str]) -> set[str]:
    """Return the subset of requested_groups that are missing or None in prior."""
    if prior is None:
        return requested_groups
    missing = set()
    for g in requested_groups:
        sentinel = GROUP_SENTINEL_KEYS.get(g)
        if sentinel is None or prior.get(sentinel) is None:
            missing.add(g)
    return missing
```

The `--skip-if-exists` flag in `run_metrics_parallel.py` retains its current meaning (skip the entire job if any sidecar exists). The incremental logic applies when `--skip-if-exists` is **not** set.

### Files affected

| File | Change |
|---|---|
| `run_metrics_job.py` | Add `GROUP_SENTINEL_KEYS`, `_load_prior_metrics()`, `_groups_to_recompute()`, merge logic, early-exit |
| `compute_batch_metrics.py` | No change needed — `groups` parameter already supports selective computation |

---

## Feature 1 — WaterMelon (WM) Score (Group I)

### Scientific background

The WaterMelon Multisection metric (Zolotovskaya et al., 2020, PMC7084891; Supplementary File 2) measures how strongly a hierarchical clustering dendrogram separates pre-defined class labels, relative to a random permutation baseline. It is an entropy-based normalized AUC metric computed over all N−1 dendrogram fork levels.

For harmonization benchmarking it is applied in two modes:

- **Batch columns** (`RNA_BATCH`, `PLATFORM_RNA`, `RNASEQ_SOURCE`, `COHORT_LABEL`): a **low** WM score means batch labels do not drive clustering → good harmonization.
- **Biology columns** (`Major_group`, `Diagnosis_cell_type_unified`, `TUMOR_NORMAL`): a **high** WM score means biology labels drive clustering → biology is preserved.
- **Ratio metric** `wm_ratio_bio_batch`: mean WM (bio cols) / (mean WM (batch cols) + 0.01). A pseudocount of 0.01 prevents explosion when batch WM ≈ 0. Higher ratio = better overall.

### Decisions

| Parameter | Decision |
|---|---|
| Permutations M | 200 |
| Subsampling | Stratified random by class label; N capped at 2000 |
| Bootstrap CI | Not computed |
| CLI flag | `--skip-wm`, default `True` (WM skipped unless `--skip-wm False`) |
| Ratio pseudocount | 0.01 |
| PLATFORM_RNA role | Batch column only |

### Algorithm (from Supplementary File 2, Zolotovskaya et al.)

**Input:** N samples, class label vector Y = (y₁,…,yN) with C unique classes.

**Step 1 — Build dendrogram.**  
Use Euclidean distance on the top 50 PCA coordinates (already computed by `compute_pca()`). Apply Ward linkage:
```python
from scipy.cluster.hierarchy import linkage
Z = linkage(pca_coords[:, :50], method="ward", metric="euclidean")
```
Linkage matrix Z has shape (N−1, 4); each row `[id_a, id_b, dist, count]` is one merge event.

**Step 2 — Precompute cluster membership snapshots.**  
Traverse Z bottom-up, tracking which sample indices belong to each cluster. Record the full partition after every merge. This gives `cluster_snapshots[l]` for l = 0..N−2 (a list of dicts mapping cluster-id → list of sample indices):

```python
clusters = {i: [i] for i in range(N)}   # N singleton clusters
cluster_snapshots = []
for merge_idx, row in enumerate(Z):
    id_a, id_b = int(row[0]), int(row[1])
    new_id = N + merge_idx
    clusters[new_id] = clusters.pop(id_a) + clusters.pop(id_b)
    cluster_snapshots.append({cid: idxs for cid, idxs in clusters.items()})
```

This runs once per job. Cluster membership is label-independent, so all M permutations reuse these snapshots.

**Step 3 — Compute IGn trajectory for a label vector.**  
Given Y (observed or permuted):

```
H(Y) = -sum_c p_c * log2(p_c)          # global entropy of Y

For each fork level l, partition = cluster_snapshots[l]:
  H_conditional = sum_k (|cluster_k| / N) * H(labels in cluster_k)
  IG_l  = H(Y) - H_conditional
  IGn_l = IG_l / H(Y)
```

By construction: IGn_0 = 0 (all samples in one cluster), IGn_{N-2} = 1 (each singleton has zero conditional entropy).

**Step 4 — Null trajectory.**  
Shuffle Y independently M=200 times. Compute IGn trajectory for each shuffle using the precomputed `cluster_snapshots`. At each level l, the null is the 95th percentile across all M permuted trajectories:
```python
null_l = np.percentile([perm_trajectories[m][l] for m in range(M)], 95)
```

**Step 5 — WM area.**  
```
WM_area = (1 / (N-1)) * sum_{l=0}^{N-2} (IGn_obs_l - null_l)
```

- WM_area ≈ 1: perfect class separation.
- WM_area ≈ 0: no better than random.
- WM_area < 0: clustering is worse than random.

### Memory and speed

The naive approach (rebuild cluster membership per permutation) is O(M × N²) — too slow for N=5,000. The optimization: precompute `cluster_snapshots` once (O(N²)); for each permutation only recompute entropy from pre-stored indices (O(N × C) per level). For N=2,000, M=200, C≈10: feasible in ~1–3 min.

**Subsampling:** If N > 2,000, apply stratified random subsampling (by class label) to 2,000 samples before building the dendrogram. The same subset is used for all columns within one job. Record `wm_subsampled = True` in the output.

### Output metrics

```
wm_{col}           float  WM area ∈ (-1, 1) — one per column in BATCH_COLS ∪ BIO_COLS
wm_mean_batch      float  mean of wm_* over batch columns (low = good harmonization)
wm_mean_bio        float  mean of wm_* over bio columns (high = biology preserved)
wm_ratio_bio_batch float  wm_mean_bio / (wm_mean_batch + 0.01)
wm_subsampled      bool   True if N > 2000 and subsampling was applied
```

Columns with fewer than 2 unique values produce NaN.

### New function signature

```python
def compute_group_i(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    pca_coords: np.ndarray,    # shared PCA (n_samples × n_pcs)
    n_permutations: int = 200,
    max_samples: int = 2000,
) -> dict:
```

### Integration into `compute_all_metrics`

1. Add `"I"` to the set of valid group letters. Default active set `"ABCDEFGH"` is unchanged; `"I"` is included only when passed via `groups=`.
2. In `run_metrics_job.py`, add `--skip-wm` (`default=True`). When `False`, append `"I"` to the groups set.
3. Pass `pca_coords` to `compute_group_i` — already in scope inside `compute_all_metrics`.
4. Gate Group I on PCA success (same pattern as A, B, C, G): skip gracefully if PCA failed.
5. Add `_run_group("I", compute_group_i, exp_df, ann_df, pca_coords)` after Group H.

---

## Feature 2 — Percentage Variance Explained per PC (Group J)

### Rationale

Group A stores `r2_RNA_BATCH` (mean R² over PC1–10) and `pcr_{col}` (variance-weighted R²). The raw percentage of variance explained by each individual PC is not stored. Extracting this into a dedicated Group J ensures:

- Jobs that already have Group A completed will have Group J computed on the next incremental run without touching A.
- The sentinel `pct_var_pc1` in `GROUP_SENTINEL_KEYS` allows the incremental logic to detect whether this new group is missing.

The per-PC variance fraction is useful for:
- Diagnosing whether one dominant PC is driven by batch (a warning sign even when mean R² appears diluted).
- Comparing variance compactness across harmonization methods.

### Algorithm

The `compute_pca()` function already returns `eigenvalues` (explained variance per PC, not normalized). The fraction per PC is:

```python
total_var = eigenvalues.sum()
pct_var_pci = eigenvalues[i] / total_var * 100   # i = 0..9 → PC1..PC10
pct_var_cum_top10 = eigenvalues[:10].sum() / total_var * 100
```

### Output metrics (Group J)

```
pct_var_pc1          float  % variance explained by PC1
pct_var_pc2          float
...
pct_var_pc10         float
pct_var_cum_top10    float  cumulative % variance in top 10 PCs
```

### New function signature

```python
def compute_group_j(
    pca_coords: np.ndarray,
    eigenvalues: np.ndarray,
) -> dict:
```

### Implementation

```python
def compute_group_j(pca_coords: np.ndarray, eigenvalues: np.ndarray) -> dict:
    result: dict = {}
    total_var_sum = float(eigenvalues.sum())
    if total_var_sum > 0:
        for i in range(min(10, len(eigenvalues))):
            result[f"pct_var_pc{i+1}"] = float(eigenvalues[i] / total_var_sum * 100)
        result["pct_var_cum_top10"] = float(eigenvalues[:10].sum() / total_var_sum * 100)
    else:
        for i in range(10):
            result[f"pct_var_pc{i+1}"] = np.nan
        result["pct_var_cum_top10"] = np.nan
    return result
```

### Integration into `compute_all_metrics`

- Add `"J"` to valid group letters.
- Group J requires `pca_coords` and `eigenvalues` (already computed); add it to the embedding-gated block.
- Add `_run_group("J", compute_group_j, pca_coords, eigenvalues)` after Group A.
- Group J is included in the **default** active set (`"ABCDEFGHJ"`) since it is fast (< 1 s).

---

## Feature 3 — Post-dropna Gene and Sample Counts (Group K)

### Rationale

When a normalization method fails partially (SVA convergence, HarmonizR per-gene failures), the output matrix contains NaN values. Existing Group E reports full matrix dimensions without accounting for NaNs. Group K is extracted as a separate group so that jobs that already have Group E will get Group K computed on the next incremental run.

Two quantities are tracked:

1. **Any-NaN** — genes/samples with at least one NaN: identifies methods with partial failures.
2. **All-NaN** — genes/samples where every value is NaN: identifies completely failed dimensions.

Methods where `pct_genes_noNA` < 80% or `n_samples_allNA` > 0 should be flagged as unreliable.

### Output metrics (Group K)

```
n_genes_noNA        int    genes with zero NaN across all samples
pct_genes_noNA      float  n_genes_noNA / n_genes * 100
n_samples_noNA      int    samples with zero NaN across all genes
pct_samples_noNA    float  n_samples_noNA / n_samples * 100
n_genes_allNA       int    genes where every sample is NaN (completely missing)
n_samples_allNA     int    samples where every gene is NaN (completely empty)
n_na_cells          int    total count of NaN cells in the matrix
pct_na_cells        float  n_na_cells / (n_samples * n_genes) * 100
```

### New function signature

```python
def compute_group_k(exp_df: pd.DataFrame, ann_df: pd.DataFrame) -> dict:
```

### Implementation

```python
def compute_group_k(exp_df: pd.DataFrame, ann_df: pd.DataFrame) -> dict:
    result: dict = {}
    n_samples, n_genes = exp_df.shape
    gene_any_na  = exp_df.isna().any(axis=0)
    gene_all_na  = exp_df.isna().all(axis=0)
    samp_any_na  = exp_df.isna().any(axis=1)
    samp_all_na  = exp_df.isna().all(axis=1)

    n_genes_noNA    = int((~gene_any_na).sum())
    n_samples_noNA  = int((~samp_any_na).sum())
    n_genes_allNA   = int(gene_all_na.sum())
    n_samples_allNA = int(samp_all_na.sum())
    n_na_cells      = int(exp_df.isna().sum().sum())

    result["n_genes_noNA"]     = n_genes_noNA
    result["pct_genes_noNA"]   = float(n_genes_noNA / n_genes * 100)     if n_genes > 0 else np.nan
    result["n_samples_noNA"]   = n_samples_noNA
    result["pct_samples_noNA"] = float(n_samples_noNA / n_samples * 100) if n_samples > 0 else np.nan
    result["n_genes_allNA"]    = n_genes_allNA
    result["n_samples_allNA"]  = n_samples_allNA
    result["n_na_cells"]       = n_na_cells
    result["pct_na_cells"]     = float(n_na_cells / (n_samples * n_genes) * 100) if (n_samples * n_genes) > 0 else np.nan
    return result
```

### Integration into `compute_all_metrics`

- Add `"K"` to valid group letters.
- Group K takes only `exp_df` and `ann_df`; no embedding dependency.
- Add `_run_group("K", compute_group_k, exp_df, ann_df)` alongside Group E.
- Group K is included in the **default** active set (fast, < 5 s).

---

## Summary of Files to Modify

| File | Changes |
|---|---|
| `compute_batch_metrics.py` | New `compute_group_i()`, `compute_group_j()`, `compute_group_k()` functions; wire all three into `compute_all_metrics()`; add J and K to default active set |
| `run_metrics_job.py` | Add `GROUP_SENTINEL_KEYS`; add `_load_prior_metrics()`, `_groups_to_recompute()`, merge logic, early-exit; add `--skip-wm` flag |
| `test_mock_metrics.py` | Smoke tests for all new features (see Testing Plan) |
| `CLAUDE.md` (this directory) | Update Groups table to include I, J, K; document new metric keys; document `--skip-wm` flag and incremental behavior |

`run_metrics_parallel.py` and `run_metrics_concat.py` require no changes.

---

## Testing Plan

### Smoke tests in `test_mock_metrics.py`

**Incremental computation:**
- Build a fake prior dict with Group E sentinel (`n_samples`) present but Group J sentinel (`pct_var_pc1`) absent; verify `_groups_to_recompute(prior, {"E", "J"})` returns `{"J"}` only.
- Simulate a merged result: verify old E keys are preserved, new J keys are added.
- Simulate prior with `status != "ok"`: verify full recomputation is triggered.

**Group J (PC variance):**
- Verify `pct_var_pc1 >= pct_var_pc2 >= ... >= pct_var_pc10`.
- Verify `pct_var_cum_top10 == sum(pct_var_pc1 .. pct_var_pc10)`.
- Verify `pct_var_cum_top10 <= 100.0`.

**Group K (dropna metrics):**
- Matrix with no NaNs: `pct_genes_noNA == 100`, `pct_samples_noNA == 100`, `n_genes_allNA == 0`, `n_samples_allNA == 0`, `n_na_cells == 0`.
- Inject NaN into all values of one gene: `n_genes_allNA == 1`, `pct_genes_noNA < 100`.
- Inject NaN into all values of one sample: `n_samples_allNA == 1`, `pct_samples_noNA < 100`.
- Inject NaN into 10% of cells: verify `n_na_cells == round(0.1 * n_genes * n_samples)`.

**Group I (WM score):**
- Two clearly separated clusters (N=100, 2 balanced classes): verify `wm_{col} > 0.3`.
- Random data with shuffled labels: verify `wm_{col} < 0.15`.
- Perfect harmonization scenario (batch WM ≈ 0, bio WM ≈ 0.5): verify `wm_ratio_bio_batch > 1`.
- N=2100 synthetic data: verify `wm_subsampled == True` and result is not NaN.

### Integration test

Run a single job on a known-good S3 file (from inside the metrics pod):
```bash
python run_metrics_job.py \
    --strat A_confirmed_bad --imp strict --method 16_fsqn_r \
    --post-rm False \
    --out-json /tmp/test_metrics.json \
    --out-genes-json /tmp/test_genes.json \
    --skip-slow --skip-wm False
```
Verify the output JSON contains `pct_var_pc1`, `n_genes_noNA`, `wm_RNA_BATCH`.

---

## Performance Impact

| Feature | Extra time per job | Notes |
|---|---|---|
| Incremental JSON load | < 2 s | One S3 GET at job start; saves full recompute on resumed runs |
| Group I — WM score | 2–5 min | N capped at 2000 by subsampling; skipped by default |
| Group J — PC variance | < 1 s | Instant; eigenvalues already in memory |
| Group K — dropna metrics | < 5 s | Two `.isna()` passes |

**Recommended workflow for adding J and K to already-completed runs:**
```bash
# Groups J and K are in the default active set; incremental logic skips A–H automatically
nohup python run_metrics_parallel.py \
    --n-workers 6 --post-rm-filter post0 --memory-limit-gb 6.0 \
    > /workspace/metrics_jk_pass.log 2>&1 &
```

**Recommended workflow for the WM pass (run after J and K are verified):**
```bash
nohup python run_metrics_parallel.py \
    --n-workers 2 --skip-wm False \
    --post-rm-filter post0 --memory-limit-gb 8.0 \
    > /workspace/metrics_wm_pass.log 2>&1 &
```
The incremental logic ensures only Group I is computed for jobs that already have A–H, J, K.

---

## Step-by-Step Implementation To-Do List

Work in this order. Each step is self-contained and testable before the next begins.

### Step 1 — Incremental JSON logic in `run_metrics_job.py`

- [x] **1.1** Add `GROUP_SENTINEL_KEYS` dict at module level (include all groups A–K).
- [x] **1.2** Implement `_load_prior_metrics(s3_client, strat, imp, method, post_rm) -> dict | None`: download existing JSON sidecar from S3; return `None` if absent, unparseable, or `status != "ok"`.
- [x] **1.3** Implement `_groups_to_recompute(prior, requested_groups) -> set[str]`: return only groups whose sentinel key is missing or `None` in `prior`.
- [x] **1.4** In the main job function, call `_load_prior_metrics()` before any S3 expression download. Use its result to call `_groups_to_recompute()` and narrow the `groups` set passed to `compute_all_metrics()`.
- [x] **1.5** Add early-exit: if `_groups_to_recompute()` returns an empty set, print a message and exit with code 0 (no work needed).
- [x] **1.6** After `compute_all_metrics()` returns, merge the new result dict into `prior_metrics` (new keys overwrite; old keys preserved). Upload the merged dict.
- [ ] **1.7** Verify manually: run a job whose JSON already exists → confirm it exits early without re-downloading the expression file. *(requires pod)*

### Step 2 — Group J: PC variance per PC (`compute_batch_metrics.py`)

- [x] **2.1** Write `compute_group_j(pca_coords: np.ndarray, eigenvalues: np.ndarray) -> dict` function. Compute `pct_var_pc{1..10}` and `pct_var_cum_top10` as described in Feature 2.
- [x] **2.2** Add `"J"` to the set of valid group letters in `compute_all_metrics()`.
- [x] **2.3** Add Group J to the default active set (it is fast and requires no extra inputs beyond what is already computed for Group A).
- [x] **2.4** Wire into `compute_all_metrics()`: add `_run_group("J", compute_group_j, pca_coords, eigenvalues)` inside the PCA-gated block, after Group A.
- [x] **2.5** Add `"J": "pct_var_pc1"` to `GROUP_SENTINEL_KEYS` in `run_metrics_job.py`.

### Step 3 — Group K: dropna metrics (`compute_batch_metrics.py`)

- [x] **3.1** Write `compute_group_k(exp_df: pd.DataFrame, ann_df: pd.DataFrame) -> dict` function. Compute all eight metrics: `n_genes_noNA`, `pct_genes_noNA`, `n_samples_noNA`, `pct_samples_noNA`, `n_genes_allNA`, `n_samples_allNA`, `n_na_cells`, `pct_na_cells`.
- [x] **3.2** Add `"K"` to the set of valid group letters in `compute_all_metrics()`.
- [x] **3.3** Add Group K to the default active set (fast, no embedding dependency).
- [x] **3.4** Wire into `compute_all_metrics()`: add `_run_group("K", compute_group_k, exp_df, ann_df)` alongside Group E.
- [x] **3.5** Add `"K": "n_genes_noNA"` to `GROUP_SENTINEL_KEYS` in `run_metrics_job.py`.

### Step 4 — Smoke tests for Groups J, K, and incremental logic (`test_mock_metrics.py`)

- [x] **4.1** Write test for `_groups_to_recompute()`: mock prior dicts with various sentinel combinations; verify correct group subsets are returned.
- [x] **4.2** Write test for Group J on a synthetic 50×100 expression matrix: verify ordering, sum, and range of `pct_var_*` values.
- [x] **4.3** Write test for Group K on a clean matrix (no NaNs) and on matrices with injected NaN patterns (one-gene all-NA, one-sample all-NA, 10%-cells NaN).
- [x] **4.4** Run `python test_mock_metrics.py` and confirm all new tests pass before moving to Group I.

### Step 5 — Group I: WaterMelon score (`compute_batch_metrics.py`)

- [x] **5.1** Write `_compute_entropy(label_counts: np.ndarray) -> float` helper: accepts an array of class counts for a cluster, returns Shannon entropy in bits.
- [x] **5.2** Write incremental `_wm_trajectory_for_labels()` helper (replaces snapshot approach): traverse linkage Z with O(N×C) incremental conditional entropy update.
- [x] **5.3** Write `_stratified_subsample()` helper: stratified random sample of `max_n` indices, preserving class proportions.
- [x] **5.4** Write `compute_group_i(exp_df, ann_df, pca_coords, n_permutations=200, max_samples=2000) -> dict` main function:
  - Optionally subsample if N > `max_samples` (stratified by RNA_BATCH, consistent subset across all columns).
  - Build dendrogram from top 50 PCA coords via Ward linkage.
  - For each column in WM_BATCH_COLS + WM_BIO_COLS: compute observed IGn trajectory; run M=200 permutations; compute null (95th pct); compute WM area.
  - Compute `wm_mean_batch`, `wm_mean_bio`, `wm_ratio_bio_batch` (pseudocount 0.01).
  - Record `wm_subsampled`.
- [x] **5.5** Add `"I"` to the set of valid group letters in `compute_all_metrics()`. Do **not** add it to the default active set — it is opt-in via `groups=`.
- [x] **5.6** Wire into `compute_all_metrics()`: add `_run_group("I", compute_group_i, exp_df, ann_df, pca_coords)` inside the PCA-gated block, after Group H. Gate on `"I" in active`.
- [x] **5.7** Add `"I": "wm_RNA_BATCH"` to `GROUP_SENTINEL_KEYS` in `run_metrics_job.py`.

### Step 6 — Add `--skip-wm` flag to `run_metrics_job.py`

- [x] **6.1** Add `parser.add_argument("--skip-wm", type=lambda x: x.lower() not in ("false", "0", "no"), default=True)` (matches the `--skip-slow` pattern already in the script).
- [x] **6.2** When `--skip-wm False`, add `"I"` to the requested groups set before calling `compute_all_metrics()`.
- [x] **6.3** Log a clear message at job start: `"WM: enabled"` or `"WM: skipped"`.

### Step 7 — Smoke tests for Group I (`test_mock_metrics.py`)

- [x] **7.1** Test with two clearly separated clusters (50 samples × 2 balanced classes): verify `wm_{col} > 0.3`.
- [x] **7.2** Test with randomly shuffled labels on structured data: verify `wm_{col} < 0.15`.
- [x] **7.3** Test with N=2100 (above subsampling threshold): verify `wm_subsampled == True`.
- [x] **7.4** Test key presence: verify all expected keys (`wm_RNA_BATCH`, `wm_subsampled`, etc.) are in output dict.
- [x] **7.5** Run `python test_mock_metrics.py` and confirm all tests pass. *(108/108 passed)*

### Step 8 — Integration test (inside the metrics pod)

- [ ] **8.1** Sync updated scripts to the pod via rsync.
- [ ] **8.2** Run the single-job integration test:
  ```bash
  python run_metrics_job.py \
      --strat A_confirmed_bad --imp strict --method 16_fsqn_r \
      --post-rm False \
      --out-json /tmp/test_metrics.json \
      --out-genes-json /tmp/test_genes.json \
      --skip-slow --skip-wm False
  ```
- [ ] **8.3** Inspect the output: verify `pct_var_pc1`, `n_genes_noNA`, `wm_RNA_BATCH` are present and non-null.
- [ ] **8.4** Run the same job a second time; verify it exits early ("all groups already complete") without re-downloading the expression file.

### Step 9 — Parallel pass for Groups J and K on all completed runs

- [ ] **9.1** Launch the J/K pass (Groups J and K are in the default active set; incremental logic skips A–H automatically):
  ```bash
  nohup python run_metrics_parallel.py \
      --n-workers 6 --post-rm-filter post0 --memory-limit-gb 6.0 \
      > /workspace/metrics_jk_pass.log 2>&1 &
  ```
- [ ] **9.2** Monitor progress: `tail -f /workspace/metrics_jk_pass.log`.
- [ ] **9.3** After completion, run `run_metrics_concat.py` and verify `metrics_comprehensive.csv` contains `pct_var_pc1` and `n_genes_noNA` columns.

### Step 10 — WM parallel pass (Group I)

- [ ] **10.1** Launch the WM pass with `--skip-wm False` after J/K are verified:
  ```bash
  nohup python run_metrics_parallel.py \
      --n-workers 2 --skip-wm False \
      --post-rm-filter post0 --memory-limit-gb 8.0 \
      > /workspace/metrics_wm_pass.log 2>&1 &
  ```
- [ ] **10.2** Monitor progress; expect 2–5 min per job.
- [ ] **10.3** After completion, run `run_metrics_concat.py`; verify `wm_RNA_BATCH` and `wm_ratio_bio_batch` are present in `metrics_comprehensive.csv`.

### Step 11 — Update CLAUDE.md

- [x] **11.1** Update the Metric groups table to include Groups I, J, K with descriptions and speed estimates.
- [x] **11.2** Document the `--skip-wm` flag under the commands section.
- [x] **11.3** Document the incremental computation behavior (what `--skip-if-exists` does vs. the new incremental default).
- [x] **11.4** Add sentinel keys reference to the architecture section.
