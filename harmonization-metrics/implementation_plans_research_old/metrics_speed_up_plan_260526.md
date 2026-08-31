# Metrics Pipeline Speed-Up Plan
**Date:** 2026-05-26  
**Author:** Daniil Nikitin  
**File:** `harmonization-metrics/metrics_speed_up_plan_260526.md`

---

## Overview

The current metrics pipeline runs each `(strat, imp, method, post_rm)` job as an
isolated subprocess. Per-job wall-clock time in fast mode (`--skip-slow`) is 9–22
minutes, dominated by sequential UMAP+tSNE computation, redundant kNN graph
construction inside `compute_group_b`, and the Python dict-based inner loop in the
WaterMelon permutation code. Additionally, every subprocess independently downloads
the annotation file even though all 39 methods in the same `(strat, imp)` group share
an identical annotation, and every subprocess waits for its expression-file download
to complete before any computation begins.

Six targeted optimizations address these bottlenecks **without changing any metric
values**. All changes preserve 100% integrity of outputs. Combined estimated speedup:
**1.5–2.0× per job in fast mode**.

---

## Background / Timing Reference

From `implementation_plans_research_old/metrics_for_batch_effect_plan.md`:

| Step | Baseline time | Bottleneck type |
|---|---|---|
| S3 expression download | ~60–90 s | I/O |
| S3 annotation download | ~5 s | I/O (× 39 redundant per group) |
| PCA (50 components, N≈5,444) | ~30 s | CPU — already shared across groups |
| UMAP | ~60–120 s | CPU (numba — releases GIL) |
| **tSNE** | **~120–600 s** | **CPU (Cython — releases GIL)** |
| Group A (PCA R²) | ~20–40 s | CPU |
| Group B (kBET + iLISI + CMS + ASW) | ~60–120 s | CPU — 12 kNN builds |
| Group D (KS tests) | ~30–120 s | CPU |
| Group G (graph connectivity) | ~20–40 s | CPU |
| Group H (pairwise distances) | ~10–30 s | CPU |
| Group I (WaterMelon, N=2,000, M=200) | ~60–180 s | CPU — dict-based inner loop |
| Groups E, K, J | ~5 s | Negligible |
| **Fast-mode total** | **~9–22 min** | |

---

## Files to Change

### 1. `harmonization-metrics/compute_batch_metrics.py`

Four optimizations touch this file (Opt-1, Opt-3, Opt-4, Opt-6).

---

#### 1a. Opt-1 — Run UMAP and tSNE concurrently (`compute_all_metrics`, lines 1414–1437)

**Why:** UMAP and tSNE are currently run sequentially despite being fully independent.
Both release the CPython GIL during their compute-heavy phases (UMAP via numba JIT;
tSNE via Cython Barnes-Hut C code), so two threads make genuine parallel progress.
Wall-clock time becomes `max(UMAP, tSNE)` instead of `UMAP + tSNE`.

**Before (lines 1414–1437):**
```python
    if pca_coords is not None:
        print(f"[{_ts()}][metrics] Computing UMAP ...", flush=True)
        try:
            umap_coords = compute_umap(pca_coords)
        except Exception:
            tb = traceback.format_exc()
            print(f"[{_ts()}][metrics] UMAP FAILED:\n{tb}", flush=True)
            result["error_umap"] = tb
            if "C" in active:
                result["error_C"] = "skipped: UMAP failed"
                active.discard("C")
            _flush()

        print(f"[{_ts()}][metrics] Computing tSNE ...", flush=True)
        try:
            tsne_coords = compute_tsne(pca_coords)
        except Exception:
            tb = traceback.format_exc()
            print(f"[{_ts()}][metrics] tSNE FAILED:\n{tb}", flush=True)
            result["error_tsne"] = tb
            if "C" in active:
                result["error_C"] = "skipped: tSNE failed"
                active.discard("C")
            _flush()
```

**After:**
```python
    if pca_coords is not None:
        _umap_result: list = []
        _tsne_result: list = []
        _umap_tb: list = []
        _tsne_tb: list = []

        def _run_umap() -> None:
            try:
                _umap_result.append(compute_umap(pca_coords))
            except Exception:
                _umap_tb.append(traceback.format_exc())

        def _run_tsne() -> None:
            try:
                _tsne_result.append(compute_tsne(pca_coords))
            except Exception:
                _tsne_tb.append(traceback.format_exc())

        print(f"[{_ts()}][metrics] Computing UMAP + tSNE concurrently ...", flush=True)
        t_umap = threading.Thread(target=_run_umap, daemon=True)
        t_tsne = threading.Thread(target=_run_tsne, daemon=True)
        t_umap.start(); t_tsne.start()
        t_umap.join(); t_tsne.join()

        if _umap_result:
            umap_coords = _umap_result[0]
        else:
            tb = _umap_tb[0] if _umap_tb else "unknown error"
            print(f"[{_ts()}][metrics] UMAP FAILED:\n{tb}", flush=True)
            result["error_umap"] = tb
            if "C" in active:
                result["error_C"] = "skipped: UMAP failed"
                active.discard("C")
            _flush()

        if _tsne_result:
            tsne_coords = _tsne_result[0]
        else:
            tb = _tsne_tb[0] if _tsne_tb else "unknown error"
            print(f"[{_ts()}][metrics] tSNE FAILED:\n{tb}", flush=True)
            result["error_tsne"] = tb
            if "C" in active:
                result["error_C"] = "skipped: tSNE failed"
                active.discard("C")
            _flush()
```

`threading` is already in the import list (used by Group D's timeout).

**Estimated saving:** 60–120 s per job.

---

#### 1b. Opt-3 — Shared kNN index in `compute_group_b` (lines 561–698)

**Why:** For each of the 4 `BATCH_COLS`, the function currently builds three separate
`NearestNeighbors` objects on the same `pca_coords[mask]`:
- `_kbet_acceptance`: `NearestNeighbors(n_neighbors=26)`, queried on `test_idx` subset
- `_lisi_values` (iLISI): `NearestNeighbors(n_neighbors=31)`, queried on all rows
- CMS loop: `NearestNeighbors(n_neighbors=k_cms+1)`, queried on all rows

One kNN fit with `n_neighbors=31` per column covers all three. kBET uses the first 25
neighbor columns; CMS uses `k_cms` columns. Indices and distances are sliced — values
are identical to the separate builds.

**Change pattern for each BATCH_COL loop body:**

```python
# Before (three separate fits inside _kbet_acceptance, _lisi_values, CMS block)
result[f"kbet_acceptance_rate_{col}"] = _kbet_acceptance(pca_coords[mask], labels)
...
lisi = _lisi_values(pca_coords[mask], labels)
...
nn = NearestNeighbors(n_neighbors=k_cms + 1, n_jobs=-1)
nn.fit(sub)
distances, indices = nn.kneighbors(sub)

# After (single fit, sliced for each consumer)
sub = pca_coords[mask]
n = len(labels)
k_shared = 31
nn_shared = NearestNeighbors(n_neighbors=k_shared, metric="euclidean", n_jobs=-1)
nn_shared.fit(sub)
shared_distances, shared_indices = nn_shared.kneighbors(sub)

result[f"kbet_acceptance_rate_{col}"] = _kbet_acceptance_precomputed(
    labels, shared_indices, k=25
)
...
lisi = _lisi_values_precomputed(labels, shared_indices, k=30)
...
k_cms = min(30, n // 4)
cms_distances = shared_distances[:, :k_cms + 1]
cms_indices   = shared_indices[:, :k_cms + 1]
# (CMS loop uses cms_distances, cms_indices directly — no nn.kneighbors call)
```

Add two new internal helpers `_kbet_acceptance_precomputed` and
`_lisi_values_precomputed` that accept pre-computed `(indices,)` instead of building
their own `NearestNeighbors`. Their logic is unchanged; the kNN build is simply moved
out. Existing helper signatures `_kbet_acceptance` and `_lisi_values` can be kept as
thin wrappers that call the new functions, so `test_mock_metrics.py` does not require
changes.

**Estimated saving:** 40–80 s per job (8 kNN builds eliminated, each ~5–10 s on
N≈4,000–5,000 samples × 50 PCs).

---

#### 1c. Opt-4 — Vectorize kBET chi-squared inner loop (`_kbet_acceptance`, lines 473–506)

**Why:** The inner loop over `n_test ≈ 544` test cells computes chi-squared statistics
one-by-one in Python. Vectorizing with numpy broadcasting replaces the loop with
array operations.

**Before (lines 492–506):**
```python
    n_rejected = 0
    for nbrs in indices:
        nbr_labels = label_arr[nbrs[1:]]
        observed = np.array([(nbr_labels == g).sum() for g in unique], dtype=float)
        expected = np.array([global_freq[g] * k for g in unique], dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            stat = np.nansum(np.where(expected > 0, (observed - expected) ** 2 / expected, 0.0))
        p = 1.0 - chi2.cdf(stat, df_chi2)
        if p <= 0.05:
            n_rejected += 1
    return 1.0 - n_rejected / n_test
```

**After:**
```python
    # indices shape: (n_test, k+1) — column 0 is self, columns 1: are neighbors
    nbr_label_matrix = label_arr[indices[:, 1:1 + k]]            # (n_test, k)
    expected = np.array([global_freq[g] * k for g in unique], dtype=float)  # (n_classes,)
    # observed counts per test cell per class
    observed = np.stack(
        [(nbr_label_matrix == g).sum(axis=1) for g in unique], axis=1
    ).astype(float)                                               # (n_test, n_classes)
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2_stats = np.where(
            expected > 0, (observed - expected) ** 2 / expected, 0.0
        ).sum(axis=1)                                             # (n_test,)
    p_vals = 1.0 - chi2.cdf(chi2_stats, df_chi2)
    n_rejected = int((p_vals <= 0.05).sum())
    return 1.0 - n_rejected / n_test
```

Note: if `_kbet_acceptance_precomputed` is added in Opt-3, this vectorization lives
there; the function receives `indices` (already computed by the shared kNN) directly.

**Estimated saving:** 10–30 s per job (10–50× faster inner computation for kBET).

---

#### 1d. Opt-6 — Array-based cluster tracking in `_wm_trajectory_for_labels` (lines 1168–1212)

**Why:** The incremental merge simulation uses Python `dict` objects for
`cluster_counts` and `cluster_size`. With N=2,000 leaf nodes and 200 permutations ×
7 columns = 1,400 trajectory calls, dict overhead dominates. Replacing with
pre-allocated numpy arrays reduces memory allocation and lookup overhead by 5–20×.

**Before (lines 1182–1212):**
```python
    cluster_counts: dict[int, np.ndarray] = {}
    cluster_size: dict[int, int] = {}
    for i in range(N):
        cc = np.zeros(n_classes)
        cc[label_idx[i]] = 1.0
        cluster_counts[i] = cc
        cluster_size[i] = 1

    H_cond = 0.0
    traj = np.empty(N - 1)
    for merge_idx in range(N - 1):
        id_a = int(Z[merge_idx, 0])
        id_b = int(Z[merge_idx, 1])
        new_id = N + merge_idx

        counts_a = cluster_counts.pop(id_a)
        counts_b = cluster_counts.pop(id_b)
        size_a = cluster_size.pop(id_a)
        size_b = cluster_size.pop(id_b)

        H_a = _entropy_from_counts(counts_a)
        H_b = _entropy_from_counts(counts_b)
        counts_new = counts_a + counts_b
        size_new = size_a + size_b
        H_new = _entropy_from_counts(counts_new)

        H_cond = H_cond - (size_a / N) * H_a - (size_b / N) * H_b + (size_new / N) * H_new
        traj[merge_idx] = (H_Y - H_cond) / H_Y

        cluster_counts[new_id] = counts_new
        cluster_size[new_id] = size_new

    return traj, H_Y
```

**After:**
```python
    # Pre-allocate: rows 0..N-1 are leaves; rows N..2N-2 are merged nodes.
    counts_arr = np.zeros((2 * N, n_classes), dtype=np.float32)
    size_arr   = np.zeros(2 * N, dtype=np.int32)
    counts_arr[np.arange(N), label_idx] = 1.0
    size_arr[:N] = 1

    H_cond = 0.0
    traj = np.empty(N - 1)
    for merge_idx in range(N - 1):
        id_a   = int(Z[merge_idx, 0])
        id_b   = int(Z[merge_idx, 1])
        new_id = N + merge_idx

        ca = counts_arr[id_a]
        cb = counts_arr[id_b]
        sa = int(size_arr[id_a])
        sb = int(size_arr[id_b])

        H_a = _entropy_from_counts(ca)
        H_b = _entropy_from_counts(cb)
        counts_arr[new_id] = ca + cb
        size_arr[new_id]   = sa + sb
        H_new = _entropy_from_counts(counts_arr[new_id])

        H_cond = H_cond - (sa / N) * H_a - (sb / N) * H_b + ((sa + sb) / N) * H_new
        traj[merge_idx] = (H_Y - H_cond) / H_Y

    return traj, H_Y
```

No logic changes — only data structure. `_entropy_from_counts` already accepts
`np.ndarray` and is unchanged.

**Estimated saving:** 60–120 s per job.

---

### 2. `harmonization-metrics/run_metrics_job.py`

Two optimizations add optional arguments (Opt-2, Opt-5).

---

#### 2a. Opt-2 — Accept `--exp-path` (local pre-fetched expression file)

**Why:** When the dispatcher has pre-fetched the expression file to local disk, the
worker should use it directly and skip the S3 download. This hides ~60–90 s of
network I/O behind the previous job's compute time.

**Change:** Add one optional argument to the `argparse` block (near line 186) and
branch in the download section (near lines 261–272).

```python
# Add to argparse (after --memory-limit-gb):
parser.add_argument(
    "--exp-path", default=None,
    help="Local path to pre-fetched expression TSV.gz. If provided, skip S3 download."
)
```

In the download section, replace the unconditional S3 download:
```python
# Before:
print(f"[{_ts()}][{label}] Downloading expression ({exp_key}) ...", flush=True)
t_dl = time.time()
try:
    exp_df = _download_df(s3, exp_key)
    ann_df = _download_df(s3, ann_key)
except Exception:
    ...

# After:
print(f"[{_ts()}][{label}] Loading expression ...", flush=True)
t_dl = time.time()
try:
    if args.exp_path and Path(args.exp_path).exists():
        exp_df = _load_local_df(args.exp_path)
        print(f"[{_ts()}][{label}] Loaded from local cache ({args.exp_path})", flush=True)
    else:
        exp_df = _download_df(s3, exp_key)
    ann_df = _download_df(s3, ann_key)  # annotation still from S3 unless Opt-5 also active
except Exception:
    ...
```

Add the helper:
```python
def _load_local_df(path: str, index_col: int = 0) -> pd.DataFrame:
    import gzip as _gzip
    with _gzip.open(path, "rb") as fh:
        return pd.read_csv(fh, sep="\t", index_col=index_col, low_memory=False)
```

---

#### 2b. Opt-5 — Accept `--ann-path` (locally cached annotation file)

**Why:** The annotation file is the same for all 39 methods in a `(strat, imp)` group.
When the dispatcher has pre-downloaded it, the worker should use the local copy.

**Change:** Add one optional argument (after `--exp-path`):
```python
parser.add_argument(
    "--ann-path", default=None,
    help="Local path to pre-fetched annotation TSV.gz. If provided, skip S3 download."
)
```

In the download section:
```python
    if args.ann_path and Path(args.ann_path).exists():
        ann_df = _load_local_df(args.ann_path)
    else:
        ann_df = _download_df(s3, ann_key)
```

---

### 3. `harmonization-metrics/run_metrics_parallel.py`

Two optimizations add pre-fetch logic to the dispatcher (Opt-2, Opt-5).

---

#### 3a. Opt-5 — Pre-download annotation once per `(strat, imp)` group

**Why:** Groups jobs by `(strat, imp)` before launching. Download each annotation file
once to a local path and pass `--ann-path` to all workers in the group.

**Change:** In `run_dispatcher()`, before submitting jobs:

```python
# Group jobs by (strat, imp) key
from collections import defaultdict
ann_cache_dir = tmp_dir / "ann_cache"
ann_cache_dir.mkdir(parents=True, exist_ok=True)
ann_local: dict[tuple[str, str], Path] = {}

groups: dict[tuple[str, str], list] = defaultdict(list)
for strat, imp, method, post_rm in todo:
    groups[(strat, imp)].append((strat, imp, method, post_rm))

def _prefetch_ann(strat: str, imp: str) -> Path:
    key = _s3_key_prepared_ann(strat, imp)   # reuse existing helper
    local = ann_cache_dir / f"{strat}__{imp}__ann.tsv.gz"
    if not local.exists():
        s3 = boto3.client("s3")
        obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
        local.write_bytes(obj["Body"].read())
    return local

# Pre-fetch all annotation files upfront (fast — one per group, not per method)
with ThreadPoolExecutor(max_workers=min(8, len(groups))) as ann_pool:
    ann_futures = {
        ann_pool.submit(_prefetch_ann, s, i): (s, i)
        for s, i in groups
    }
    for f in as_completed(ann_futures):
        s, i = ann_futures[f]
        ann_local[(s, i)] = f.result()
```

Then pass `--ann-path` in the `cmd` list inside `launch()`:
```python
ann_path = ann_local.get((strat, imp))
if ann_path:
    cmd.extend(["--ann-path", str(ann_path)])
```

Clean up annotation cache files after all jobs in the group finish (or at dispatcher
shutdown).

---

#### 3b. Opt-2 — Expression file pre-fetch with lookahead

**Why:** While a worker is computing (9–22 min), the next job's expression file
(~60–90 s download) can be fetched in a background thread, hiding I/O latency.

**Change:** Add a pre-fetch thread pool in `run_dispatcher()`. Maintain a local cache
dict and directory. Submit download tasks one `n_workers` steps ahead of execution.

```python
exp_cache_dir = tmp_dir / "exp_cache"
exp_cache_dir.mkdir(parents=True, exist_ok=True)
exp_local: dict[str, Path] = {}   # exp_s3_key → local path
prefetch_executor = ThreadPoolExecutor(max_workers=n_workers)

def _prefetch_exp(strat: str, imp: str, method: str, post_rm: bool) -> tuple[str, Path]:
    s3_key = _s3_key_exp(strat, imp, method, post_rm)   # reuse existing helper
    local  = exp_cache_dir / Path(s3_key).name
    if not local.exists():
        s3  = boto3.client("s3")
        obj = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
        local.write_bytes(obj["Body"].read())
    return s3_key, local
```

In `launch()`, check the cache before building `cmd`:
```python
exp_path = exp_local.get(_s3_key_exp(strat, imp, method, post_rm))
if exp_path and exp_path.exists():
    cmd.extend(["--exp-path", str(exp_path)])
```

After each job finishes, delete its cached expression file to keep disk usage bounded
to `n_workers × max_file_size` (~4 × 200 MB = ~800 MB peak).

In the `with ThreadPoolExecutor(max_workers=n_workers) as pool:` block, pre-submit
the next `n_workers` downloads whenever a job completes:
```python
# Before submitting job i, ensure jobs i..i+n_workers are pre-fetching
for lookahead_job in todo[i : i + n_workers]:
    key = _s3_key_exp(*lookahead_job)
    if key not in exp_local:
        prefetch_executor.submit(_prefetch_exp, *lookahead_job)
```

Shut down `prefetch_executor` at the end of `run_dispatcher()` with
`prefetch_executor.shutdown(wait=False)`.

---

## Files That Do NOT Need to Change

| File | Reason |
|---|---|
| `compute_batch_metrics.py` — `compute_group_a`, `compute_group_c`, `compute_group_d`, `compute_group_e`, `compute_group_f`, `compute_group_g`, `compute_group_h`, `compute_group_k`, `compute_group_j` | These group functions are not touched by any optimization. |
| `run_metrics_concat.py` | Aggregation only; no compute logic. |
| `test_mock_metrics.py` | All group functions keep the same external signatures; tests remain valid. Run after each optimization to verify. |
| `insert_cells.py` | Notebook helper; unrelated. |
| `harmonization_metrics_analysis.ipynb` | Reads `metrics_comprehensive.csv`; metric column names are unchanged. |
| `k8s/pod-metrics.yaml` | No new Python dependencies introduced. |
| `requirements.txt` | No new packages. `threading` is stdlib. |
| `CLAUDE.md` (this directory) | No new commands, metric groups, or key patterns are added. |
| All `harmonization-scripts/` files | Separate pipeline; no overlap. |

---

## Side Effects and Caveats

1. **Disk usage on pod:** Opt-2 adds `n_workers × expression_file_size` of temporary
   disk usage in `tmp_dir/exp_cache/`. At 4 workers and ~200 MB per file, peak usage is
   ~800 MB. The pod has a PVC (`/workspace`); use `tmp_dir` on the PVC, not `/tmp`, if
   ephemeral storage is limited.

2. **Thread safety in `compute_all_metrics`:** Opt-1 adds two daemon threads inside a
   worker subprocess. The subprocess is single-threaded until this point, so there is no
   shared mutable state outside the closures. `result` dict is not touched inside the
   threads — safe.

3. **kBET output identity (Opt-4):** `chi2.cdf` called with a 1D array vs. a scalar
   produces identical float values. Verify with `test_mock_metrics.py` that
   `kbet_acceptance_rate_RNA_BATCH` is within floating-point tolerance of the old value
   on synthetic data.

4. **WaterMelon float32 vs float64 (Opt-6):** `counts_arr` is declared `float32` for
   memory efficiency. `_entropy_from_counts` receives a `float32` slice. Verify that
   entropy values match `float64` within 1e-5 tolerance. If not, change to `float64`.

5. **Incremental job logic unchanged:** Opt-2 and Opt-5 only add `--exp-path` and
   `--ann-path` as optional arguments with `default=None`. All existing dispatcher
   invocations without these flags continue to work identically.

6. **No S3 key changes, no new metric columns, no count changes.** `metrics_comprehensive.csv`
   schema is unchanged.

---

## Verification Commands

```bash
source ~/venvs/collagen_3_11/bin/activate
cd ~/FL_harmonization

# 1. Smoke test — verifies all metric groups on synthetic data
python harmonization-metrics/test_mock_metrics.py

# 2. Single-job end-to-end test (verifies S3 download fallback still works)
python harmonization-metrics/run_metrics_job.py \
    --strat A_confirmed_bad --imp strict --method 16_fsqn_r \
    --post-rm False \
    --out-json /tmp/test_metrics.json \
    --out-genes-json /tmp/test_genes.json \
    --skip-slow

# 3. Verify key metric values are present and non-null
python -c "
import json
d = json.load(open('/tmp/test_metrics.json'))
keys = ['r2_RNA_BATCH', 'kbet_acceptance_rate_RNA_BATCH', 'pct_var_pc1',
        'wm_RNA_BATCH', 'n_genes_noNA']
for k in keys:
    print(k, '=', d.get(k))
"

# 4. Test new --exp-path argument (pass the file downloaded in step 2's cache)
python harmonization-metrics/run_metrics_job.py \
    --strat A_confirmed_bad --imp strict --method 16_fsqn_r \
    --post-rm False \
    --exp-path /tmp/test_exp_cache.tsv.gz \
    --out-json /tmp/test_metrics_cached.json \
    --out-genes-json /tmp/test_genes_cached.json \
    --skip-slow

# 5. Confirm kBET and WM values match between cached and non-cached run
python -c "
import json
a = json.load(open('/tmp/test_metrics.json'))
b = json.load(open('/tmp/test_metrics_cached.json'))
for k in ['kbet_acceptance_rate_RNA_BATCH', 'wm_RNA_BATCH', 'r2_RNA_BATCH']:
    match = abs(a[k] - b[k]) < 1e-5 if (a[k] and b[k]) else (a[k] == b[k])
    print(k, 'MATCH' if match else f'MISMATCH: {a[k]} vs {b[k]}')
"
```

---

## TODO

- [ ] `compute_batch_metrics.py` — Opt-1: replace sequential UMAP/tSNE block in `compute_all_metrics` (lines ~1414–1437) with concurrent thread-based execution
- [ ] `compute_batch_metrics.py` — Opt-3: add `_kbet_acceptance_precomputed(labels, indices, k)` helper that accepts pre-computed indices
- [ ] `compute_batch_metrics.py` — Opt-3: add `_lisi_values_precomputed(labels, indices, k)` helper that accepts pre-computed indices
- [ ] `compute_batch_metrics.py` — Opt-3: refactor `compute_group_b` BATCH_COLS loop to build one `NearestNeighbors(n_neighbors=31)` per column and pass sliced indices to new helpers
- [ ] `compute_batch_metrics.py` — Opt-4: vectorize inner loop in `_kbet_acceptance` (or its `_precomputed` variant) with numpy broadcasting
- [ ] `compute_batch_metrics.py` — Opt-6: replace dict-based `cluster_counts`/`cluster_size` in `_wm_trajectory_for_labels` with pre-allocated 2D numpy array (lines ~1182–1212)
- [ ] `compute_batch_metrics.py` — Opt-6: verify float32 vs float64 entropy parity on synthetic data (tolerance 1e-5); upgrade to float64 if needed
- [ ] `run_metrics_job.py` — Opt-2: add `--exp-path` optional argument to argparse block
- [ ] `run_metrics_job.py` — Opt-2: add `_load_local_df()` helper; branch in download section to use local file when `--exp-path` is provided and exists
- [ ] `run_metrics_job.py` — Opt-5: add `--ann-path` optional argument; branch in download section to use local file when provided
- [ ] `run_metrics_parallel.py` — Opt-5: add annotation pre-fetch logic: group jobs by `(strat, imp)`, download each annotation to `tmp_dir/ann_cache/` before launching jobs, pass `--ann-path` in worker `cmd`
- [ ] `run_metrics_parallel.py` — Opt-2: add expression pre-fetch thread pool with `n_workers` lookahead; pass `--exp-path` in worker `cmd` when cache hit; delete cached file after job completes
- [ ] Run `test_mock_metrics.py` after each optimization and confirm all tests pass
- [ ] Run single-job end-to-end test and confirm key metric values match pre-optimization baseline
