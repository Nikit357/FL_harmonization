# Skip unnecessary UMAP/tSNE in incremental mode — implementation plan

**Date:** 2026-05-30  
**File:** `harmonization-metrics/skip_umap_tsne_plan_260530.md`

---

## Overview

When a metrics job runs in incremental mode and only groups I, J, and/or K are missing,
`compute_all_metrics()` still computes both UMAP and tSNE before touching those groups.
UMAP takes ~1–2 min and tSNE ~1–2 min per job, so each incremental job wastes ~3–4 min
of CPU+memory before it even starts the work it was called for.

The root cause is a single misplaced guard in `compute_all_metrics()` (line ~1414 of
`compute_batch_metrics.py`): UMAP and tSNE are unconditionally triggered whenever PCA
succeeds, rather than only when group C (the only consumer of those embeddings) is in the
active set.

The fix is a one-line condition change: `if pca_coords is not None:` →
`if pca_coords is not None and "C" in active:`. One docstring also needs updating.

---

## Background — which groups use which embeddings

| Embedding | Groups that actually consume it |
|-----------|--------------------------------|
| PCA       | A, B, G, I, J                  |
| UMAP      | **C only**                     |
| tSNE      | **C only**                     |

The existing guard for PCA already correctly enumerates the dependent groups
(`active & {"A", "B", "C", "G", "I", "J"}`). The UMAP/tSNE guard does not mirror this
discipline — it fires on every job that managed to compute PCA, regardless of whether C
needs to run.

---

## Files to change

### 1. `harmonization-metrics/compute_batch_metrics.py`

#### 1a. Fix the UMAP/tSNE computation guard (line ~1414)

**Before** (lines 1414–1437):
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

**After** — add `and "C" in active` to the outer guard:
```python
    if pca_coords is not None and "C" in active:
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

#### 1b. Fix the inline comment above the embedding block (line ~1393–1394)

**Before:**
```python
    # Shared embeddings (needed by A, B, C, G) — wrapped so a failure never
    # prevents E, D, H, F from running.
```

**After:**
```python
    # Shared embeddings — PCA needed by A, B, G, I, J; UMAP and tSNE needed by C only.
    # Wrapped so a failure never prevents E, D, H, F from running.
```

#### 1c. Fix the `compute_all_metrics` docstring (line ~1339–1341)

**Before** (in the docstring body):
```
    Shared embeddings (PCA, UMAP, tSNE) are computed once and shared by groups
    A, B, C, G. If the embedding computation fails, those groups are skipped
    gracefully and the error is recorded; groups E, D, H, F still run.
```

**After:**
```
    Shared embeddings are computed lazily: PCA is computed when any of A, B, C, G, I, J
    are active; UMAP and tSNE are computed only when C is active. If PCA fails, all
    embedding-dependent groups are skipped gracefully; groups E, D, H, F still run.
```

---

## Files that do NOT need to change

| File | Reason |
|------|--------|
| `run_metrics_job.py` | Already passes `groups_to_run` correctly; the bug is entirely inside `compute_all_metrics`. |
| `run_metrics_parallel.py` | Dispatcher is unaffected — it passes `--groups` to worker subprocesses unchanged. |
| `test_mock_metrics.py` | No test currently asserts that UMAP/tSNE are skipped; existing tests still pass. |
| `CLAUDE.md` (this directory) | Group descriptions remain accurate; no counts or keys change. |

---

## Side effects and caveats

- **No S3 output changes.** The JSON sidecar keys and values are identical. A job that
  computes only I, J, K will still write the same `wm_*`, `pct_var_*`, and `n_genes_noNA`
  keys it would have before.
- **No cache invalidation needed.** There are no pkl caches in the metrics pipeline.
- **Speed-up per incremental job:** ~3–4 min saved (UMAP ~1–2 min + tSNE ~1–2 min) per
  job that needs only I, J, K. With 3,254 incremental jobs in this run, the saving can be
  substantial.
- **Group C behaviour unchanged.** When C is in the active set (new jobs, or jobs where C
  previously failed), UMAP and tSNE are computed as before.
- **Edge case — C already done, A/B/G also already done, only I/J/K missing:**
  This is the exact observed scenario. After the fix: PCA fires (needed by I and J), UMAP
  and tSNE are skipped, I/J/K compute, job completes ~4 min faster.

---

## Verification commands

After applying the fix (on any machine with the venv active):

```bash
source ~/venvs/collagen_3_11/bin/activate
cd ~/FL_harmonization/harmonization-metrics

# 1. Smoke-test — verifies import and basic group logic
python test_mock_metrics.py

# 2. Confirm UMAP/tSNE are skipped when groups = {I, J, K}
python - <<'EOF'
import pandas as pd, numpy as np
from compute_batch_metrics import compute_all_metrics

rng = np.random.default_rng(0)
n, g = 200, 50
exp = pd.DataFrame(rng.random((n, g)), columns=[f"G{i}" for i in range(g)])
ann = pd.DataFrame({
    "RNA_BATCH": rng.integers(0, 5, n).astype(str),
    "PLATFORM_RNA": rng.integers(0, 2, n).astype(str),
    "RNASEQ_SOURCE": rng.integers(0, 3, n).astype(str),
    "COHORT_LABEL": rng.integers(0, 8, n).astype(str),
    "Major_group": rng.integers(0, 3, n).astype(str),
    "Diagnosis_cell_type_unified": rng.integers(0, 4, n).astype(str),
    "TUMOR_NORMAL": rng.integers(0, 2, n).astype(str),
})
result = compute_all_metrics(exp, ann, groups={"I", "J", "K"})
# Must be present
assert "pct_var_pc1" in result, "J missing"
assert "n_genes_noNA" in result, "K missing"
assert "wm_RNA_BATCH" in result, "I missing"
# Must NOT be present (C not requested, UMAP/tSNE should not have run)
assert "umap_centroid_disp_RNA_BATCH" not in result, "C unexpectedly computed"
print("All assertions passed — UMAP/tSNE correctly skipped.")
EOF
```

---

## TODO

- [x] `compute_batch_metrics.py` — change `if pca_coords is not None:` to
      `if pca_coords is not None and "C" in active:` at line ~1414
- [x] `compute_batch_metrics.py` — update inline comment above the embedding block
      (~line 1393) to state that UMAP/tSNE are only needed by C
- [x] `compute_batch_metrics.py` — update `compute_all_metrics` docstring (~line 1339)
      to reflect lazy UMAP/tSNE computation
- [x] Run `python test_mock_metrics.py` to confirm no import errors — 108 passed, 0 failed
- [x] Run the verification snippet above to confirm UMAP/tSNE are skipped for groups={I,J,K} — confirmed
- [ ] Rsync updated file to the pod and restart the metrics dispatcher (requires live pod)
