# Implementation Plan: Fix Group M `compute_group_m` broadcast crash

> Investigated from `logs_metrics_August_Sept_2026/logs_test_metrics_260822.txt`
> (test run of `python test_mock_metrics.py` inside the running `fl-metrics` pod).
> **Do not implement yet.** This document is the design spec.

---

## Overview

`test_mock_metrics.py` crashed (non-zero exit, `sys.exit`'s final summary never printed)
during `test_group_m_rank_agreement`, with:

```
ValueError: Lengths of operands do not match: 240 != 1
```

raised from `compute_batch_metrics.py:1855` inside `compute_group_m`:

```python
diff_batch = batches[rows][:, None] != batches[None, :]
```

The traceback shows the comparison is dispatched through
`pandas/core/arrays/string_.py:1211 StringArray._cmp_method`, not plain NumPy — i.e. `batches`
is a pandas **StringArray** (an `ExtensionArray`), not a NumPy `ndarray`. `ExtensionArray`
`__getitem__` does not support NumPy's `[:, None]` newaxis-broadcasting trick the way a plain
`ndarray` does, so `batches[rows][:, None]` and `batches[None, :]` end up as mismatched
1-D shapes (240 vs 1) instead of broadcasting to a 240×240 boolean grid, and the element-wise
`!=` fails outright.

This is a **pandas string-dtype backend problem**: `ann_df[batch_col].astype(str).values` returns
a `StringArray` on this pod's pandas build (pandas 2.x/3.x with the "future string dtype"
inference enabled — either the default in a newer pandas release, or an environment-level
opt-in) instead of the classic NumPy object array pandas 1.x/older-2.x builds returned for the
same code. `requirements.txt` only pins `pandas>=2.0`, so any pandas version satisfying that
constraint is possible, and the pod evidently resolved one that infers string dtype by default.

**The fix is already precedented in this exact file.** `compute_group_h`
(pairwise-distance metrics) does the identical 2-D broadcast comparison at line 1263–1264 and
is unaffected, because it wraps the array in `np.asarray(...)` first (line 1262):

```python
lbl = np.asarray(ann_sub[col].astype(str))          # ← forces true ndarray, not StringArray
same = (lbl[:, None] == lbl[None, :]) & upper
diff = (lbl[:, None] != lbl[None, :]) & upper
```

`np.asarray()` on a `StringArray` materializes a genuine NumPy object array, which supports
`[:, None]` broadcasting normally. `compute_group_m` must adopt the same wrapping — this is a
one-line-per-array fix, not a redesign, and it matches the established style in the same module.

**Key design decision:** fix the two array constructions in `compute_group_m` (`batches`, `bios`)
by wrapping with `np.asarray(...)`, mirroring `compute_group_h`. Do **not** pin
`pandas<3` / a narrower pandas version in `requirements.txt` — that would be a much larger,
environment-wide change to work around a one-line code issue, and every other broadcast site in
the file already proves the `np.asarray()` wrap is sufficient regardless of which pandas string
backend is active.

---

## Background / reference data

Failing test excerpt (`logs_metrics_August_Sept_2026/logs_test_metrics_260822.txt:346-367`):

```
--- test_group_m_rank_agreement ---
Traceback (most recent call last):
  File "/app/harmonization-metrics-calculation/test_mock_metrics.py", line 887, in <module>
    main()
  File "/app/harmonization-metrics-calculation/test_mock_metrics.py", line 872, in main
    test_group_m_rank_agreement()
  File "/app/harmonization-metrics-calculation/test_mock_metrics.py", line 640, in test_group_m_rank_agreement
    clean = compute_group_m(clean_df, ann_df)
  File "/app/harmonization-metrics-calculation/compute_batch_metrics.py", line 1855, in compute_group_m
    diff_batch = batches[rows][:, None] != batches[None, :]
  File "/usr/local/lib/python3.12/dist-packages/pandas/core/ops/common.py", line 85, in new_method
    return method(self, other)
  File "/usr/local/lib/python3.12/dist-packages/pandas/core/arraylike.py", line 46, in __ne__
    return self._cmp_method(other, operator.ne)
  File "/usr/local/lib/python3.12/dist-packages/pandas/core/arrays/string_.py", line 1211, in _cmp_method
    raise ValueError(
ValueError: Lengths of operands do not match: 240 != 1
```

Because `test_mock_metrics.py`'s `main()` calls tests in sequence with no per-test isolation
(no `try/except` around each call), the uncaught exception aborted the whole run at
`test_group_m_rank_agreement` (test 14 of 21). Every test from `test_group_m_subsampling` onward
(`test_group_n_prediction`, `test_group_n_no_imputation`, `test_group_n_single_class_fold`,
`test_group_n_degenerate_single_batch`, `test_lmn_in_compute_all`,
`test_group_failure_isolation_lmn`) never ran, and the final `PASS/FAIL` summary line never
printed — so the true count of passing/failing assertions past that point is currently unknown.

**Confirmed NOT a problem** (already passed earlier in the same log, same log lines 1–80,
82–141): groups A, B, C, D, E, G, H, I, J, K, N, and Group M's own `xb_n_panel_genes_used`/sentinel
plumbing (`test_incremental_groups_to_recompute`) all pass. Group L passes in full
(`test_group_l_correlation_preservation`, `test_group_l_per_gene_keys`,
`test_group_l_missing_panel_genes`) — its cohort-loop comparisons only ever compare against a
scalar (`cohorts == level`) or use element-wise same-length comparisons, never the 2-D
broadcast pattern, so it is unaffected by the StringArray issue even though it uses the same
`.astype(str).values` call.

Locations of the two broken array constructions and the three lines that broadcast them,
all inside `compute_group_m` (`compute_batch_metrics.py`):

| Line | Code |
|---|---|
| 1832 | `batches = ann_df[batch_col].astype(str).values[keep]` |
| 1833 | `bios = ann_df[bio_col].astype(str).values[keep]` |
| 1855 | `diff_batch = batches[rows][:, None] != batches[None, :]` |
| 1856 | `same_bio = bios[rows][:, None] == bios[None, :]` |
| 1868 | `m_d = m_same & (bios[rows][:, None] == diag)` |

---

## Files to change

### 1. `compute_batch_metrics.py`

#### 1a. Fix `batches` construction (line 1832)

**Why:** `.values` on a `.astype(str)` Series can return a pandas `StringArray`
(`ExtensionArray`) rather than a NumPy `ndarray`, depending on the pandas build's string-dtype
backend. `StringArray` does not support NumPy-style `[:, None]`/`[None, :]` broadcasting, which
`compute_group_m` relies on at lines 1855, 1856, and 1868. Wrapping in `np.asarray(...)` forces
a true NumPy object array, matching the working pattern already used in `compute_group_h`
(line 1262).

Before:
```python
    X = exp_df[genes].values.astype(float)[keep]
    batches = ann_df[batch_col].astype(str).values[keep]
    bios = ann_df[bio_col].astype(str).values[keep]
```

After:
```python
    X = exp_df[genes].values.astype(float)[keep]
    # np.asarray(...) forces a plain ndarray instead of a pandas StringArray, which does
    # not support the [:, None] / [None, :] broadcasting used below (see compute_group_h
    # for the same pattern).
    batches = np.asarray(ann_df[batch_col].astype(str))[keep]
    bios = np.asarray(ann_df[bio_col].astype(str))[keep]
```

No changes needed at lines 1855, 1856, 1868 themselves — once `batches`/`bios` are true
`ndarray`s, the existing `[:, None]`/`[None, :]` broadcasting works unmodified.

---

## Files that do NOT need to change

- **`test_mock_metrics.py`** — the test itself and `_make_panel_data()` fixture are correct;
  the bug is entirely in `compute_group_m`'s array construction, not in how the test builds or
  calls its inputs.
- **`run_metrics_job.py`** — `GROUP_SENTINEL_KEYS["M"] = "xb_rank_agree"` and
  `GROUPS_NEEDING_REFERENCE` are unaffected; Group M already correctly needs no reference
  download, and the sentinel key is unchanged by this fix.
- **`requirements.txt` / `k8s/pod-metrics.yaml`** — no pandas/numpy version pin change. The
  `np.asarray()` wrap is robust regardless of which string-dtype backend pandas resolves to,
  so there is no need to constrain the dependency version as a workaround.
- **All other metric-group functions** (A, B, C, D, E, F, G, H, I, J, K, L, N) — none of them
  construct a label array with `.astype(str).values` and then apply 2-D
  `[:, None]`/`[None, :]` broadcasting on it. `compute_group_h`'s equivalent broadcast already
  uses `np.asarray()` (line 1262) and is unaffected. `compute_group_l`'s `cohorts` array
  (line 1686, same `.astype(str).values` pattern) is only ever compared against a scalar
  (`cohorts == level`) or used for masking — no broadcast — so it does not trigger this bug and
  needs no change.

---

## Side effects and caveats

- This is a pure bugfix with no output-schema or S3-key changes: `compute_group_m`'s return
  dict (`xb_rank_agree`, `xb_rank_agree_ratio`, `xb_rank_agree_by_diagnosis`, etc.) is unchanged.
- No cache invalidation needed — Group M's sentinel key (`xb_rank_agree`) and its place in
  `GROUP_SENTINEL_KEYS` are untouched, so incremental recompute logic for already-completed jobs
  is unaffected.
- **Any live blind-check job (`--groups L,M,N` or the default full run) that already attempted
  Group M on this pod's pandas build would have failed with this same `ValueError`** and been
  recorded in `failed_jobs_metrics.txt` / `failed_metrics_{pod_name}.txt`. After this fix lands,
  re-run those jobs (they are not skipped by `--skip-if-exists` logic issues — they simply never
  wrote a valid `xb_rank_agree` sentinel, so the incremental-recompute logic in
  `run_metrics_job.py` will pick Group M back up automatically on the next run of any job that
  previously failed there).
- Because `test_mock_metrics.py`'s `main()` has no per-test isolation, this single crash hid the
  results of the 6 tests listed above (`test_group_m_subsampling` through
  `test_group_failure_isolation_lmn`). Re-running the full suite after the fix is the only way
  to know whether they pass — do not assume they are fine.

---

## Verification commands

```bash
source ~/venvs/collagen_3_11/bin/activate   # or, inside the pod, the pod's system Python
cd harmonization-metrics-calculation

# 1. Confirm which pandas build the pod resolved (context for the root cause, not required
#    for the fix to work — np.asarray() is robust to either backend).
python -c "import pandas as pd; print(pd.__version__)"

# 2. Full smoke test — must reach the final summary line and reach test_group_m_subsampling
#    through test_group_failure_isolation_lmn (previously never executed).
python test_mock_metrics.py

# 3. Targeted re-check of the exact previously-failing assertion path
python -c "
from test_mock_metrics import test_group_m_rank_agreement, test_group_m_subsampling
test_group_m_rank_agreement()
test_group_m_subsampling()
print('Group M tests OK')
"
```

Exit code 0 and a final `Results: N passed, 0 failed.` line = safe to consider this fixed.

---

## TODO checklist

- [x] `compute_batch_metrics.py` — wrap `batches` construction in `np.asarray(...)` (line 1832)
- [x] `compute_batch_metrics.py` — wrap `bios` construction in `np.asarray(...)` (line 1833)
- [x] Run `python test_mock_metrics.py` in the pod; confirm exit code 0 and full summary line
      prints (i.e. the run no longer aborts partway through) — `Results: 169 passed, 0 failed.`
      (also confirmed the pod's pandas build is 3.0.5, which defaults to the StringDtype
      backend, matching the root-cause hypothesis)
- [x] Confirm `test_group_m_rank_agreement`, `test_group_m_subsampling` pass
- [x] Confirm the 6 previously-unreached tests (`test_group_n_prediction`,
      `test_group_n_no_imputation`, `test_group_n_single_class_fold`,
      `test_group_n_degenerate_single_batch`, `test_lmn_in_compute_all`,
      `test_group_failure_isolation_lmn`) now run and pass
- [ ] `(requires live pod)` Re-run any previously-failed blind-check (`L,M,N`) jobs whose
      `failed_metrics_{pod_name}.txt` entry corresponds to a Group M crash, once this fix is
      deployed to the pod
