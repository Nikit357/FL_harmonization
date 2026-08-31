# Implementation Plan: Fix Metrics Test Failures and Make WM Default
**Date:** 2026-05-24  
**Author:** Daniil Nikitin  
**Status:** Plan — pending approval

---

## Overview

Three distinct problems were found during today's pod run of `test_mock_metrics.py`:

| # | Problem | Root cause | Files affected |
|---|---|---|---|
| 1 | `ValueError: assignment destination is read-only` at `test_mock_metrics.py:303` | `DataFrame.copy().values` returns a read-only numpy array in newer pandas/numpy | `test_mock_metrics.py` |
| 2 | No `--skip-wm` flag in `run_metrics_parallel.py` | Flag exists in the worker (`run_metrics_job.py`) but was never wired into the dispatcher | `run_metrics_parallel.py` |
| 3 | WaterMelon score (Group I) not computed by default | Group I is currently opt-in only; user requires it to be in the default active set, just like Groups J and K | `compute_batch_metrics.py`, `run_metrics_job.py`, `test_mock_metrics.py` |

All three fixes are independent and can be applied in any order.

---

## Problem 1 — Read-only array assignment in `test_mock_metrics.py`

### Root cause

Lines 298–303 of `test_mock_metrics.py`:

```python
n_s, n_g = exp_df.shape
exp_partial_na = exp_df.copy()
na_count = n_s * n_g // 10
flat_idx = RNG.choice(n_s * n_g, na_count, replace=False)
rows, cols = flat_idx // n_g, flat_idx % n_g
exp_partial_na.values[rows, cols] = float("nan")   # ← CRASH HERE
```

`DataFrame.copy()` in pandas backed by NumPy ≥ 1.24 may return a DataFrame whose underlying numpy array has the `WRITEABLE=False` flag set. Calling `.values` on such a DataFrame returns the read-only array directly, and attempting fancy-index assignment raises `ValueError: assignment destination is read-only`.

The idiomatic fix is to extract a writable numpy array via `.to_numpy().copy()`, modify it in place, then reconstruct the DataFrame with the original index and columns.

### Fix — `test_mock_metrics.py` lines 298–304

**Current code:**
```python
n_s, n_g = exp_df.shape
exp_partial_na = exp_df.copy()
na_count = n_s * n_g // 10
flat_idx = RNG.choice(n_s * n_g, na_count, replace=False)
rows, cols = flat_idx // n_g, flat_idx % n_g
exp_partial_na.values[rows, cols] = float("nan")
result_partial = compute_group_k(exp_partial_na, ann_df)
```

**Replacement:**
```python
n_s, n_g = exp_df.shape
na_count = n_s * n_g // 10
flat_idx = RNG.choice(n_s * n_g, na_count, replace=False)
rows, cols = flat_idx // n_g, flat_idx % n_g
arr_partial = exp_df.to_numpy().copy()          # always writable
arr_partial[rows, cols] = float("nan")
exp_partial_na = pd.DataFrame(
    arr_partial, index=exp_df.index, columns=exp_df.columns
)
result_partial = compute_group_k(exp_partial_na, ann_df)
```

Key changes:
- Removed the intermediate `exp_df.copy()` DataFrame.
- `to_numpy().copy()` always returns a fresh, writable C-contiguous numpy array regardless of pandas/numpy version.
- The DataFrame is reconstructed from the modified array, preserving the original index and column labels.

### Verification

After this fix, `test_group_k_dropna_metrics()` should reach the `n_na_cells_correct_for_partial_na` assertion and pass it. No other tests are affected.

---

## Problem 2 — `--skip-wm` missing from `run_metrics_parallel.py`

### Root cause

`run_metrics_job.py` has a `--skip-wm` argument (line 187–193) that controls whether Group I is added to the requested groups. However, `run_metrics_parallel.py` never parses this flag and never forwards it to the subprocess command built in the `launch()` inner function (lines 257–272). As a result, it is impossible to control WM computation from the dispatcher.

### Fix — `run_metrics_parallel.py` (three locations)

**Location 1 — `run_dispatcher()` function signature (line 229):**

Add `skip_wm: bool = False` parameter:

```python
def run_dispatcher(
    jobs: list[tuple[str, str, str, bool]],
    skip_keys: set[str],
    skip_if_exists: bool,
    skip_slow: bool,
    n_workers: int,
    timeout_s: int,
    memory_limit_gb: float,
    tmp_dir: Path,
    groups: Optional[str] = None,
    skip_wm: bool = False,            # ← ADD THIS
) -> tuple[set[str], set[str]]:
```

**Location 2 — `launch()` subprocess command construction (after the `if skip_slow:` block, around line 270):**

```python
        if skip_slow:
            cmd.append("--skip-slow")
        if skip_wm:                                   # ← ADD THIS BLOCK
            cmd.extend(["--skip-wm", "True"])
        if groups:
            cmd.extend(["--groups", groups])
```

**Location 3 — `main()` argument parser (around line 343):**

Add the new argument:
```python
parser.add_argument("--n-workers",        type=int,   default=4)
parser.add_argument("--skip-if-exists",   action="store_true")
parser.add_argument("--retry-failed",     action="store_true")
parser.add_argument("--post-rm-filter",   choices=["post0", "post1", "both"], default="both")
parser.add_argument("--skip-slow",        action="store_true")
parser.add_argument("--skip-wm",          action="store_true",    # ← ADD THIS
                    help="Skip WaterMelon score (Group I) in each worker.")
parser.add_argument("--memory-limit-gb",  type=float, default=6.0)
# ... rest unchanged
```

**Location 4 — `run_dispatcher()` call in `main()` (around line 392):**

```python
    newly_failed, newly_succeeded = run_dispatcher(
        jobs=jobs,
        skip_keys=skip_keys,
        skip_if_exists=args.skip_if_exists,
        skip_slow=args.skip_slow,
        n_workers=args.n_workers,
        timeout_s=args.timeout_s,
        memory_limit_gb=args.memory_limit_gb,
        tmp_dir=tmp_dir,
        groups=args.groups,
        skip_wm=args.skip_wm,         # ← ADD THIS
    )
```

Also update the `--groups` help text (line 357) to reflect the full valid set:
```python
parser.add_argument("--groups", default=None,
                    help="Comma-separated metric groups to compute (e.g. A,B,E). "
                         "Valid: A B C D E F G H I J K. Default: all groups.")
```

### Verification

After this fix, the following commands should work correctly from the dispatcher:
```bash
# WM enabled (default, after Problem 3 fix)
python run_metrics_parallel.py --n-workers 2 --post-rm-filter post0

# WM explicitly skipped
python run_metrics_parallel.py --n-workers 2 --post-rm-filter post0 --skip-wm
```

---

## Problem 3 — WaterMelon score must be in the default active set

### Root cause

Group I is currently treated as opt-in only. Three places enforce this:

| Location | Current behavior |
|---|---|
| `compute_batch_metrics.py` line 1367 | Default active set is `set("ABCDEFGHJK")` — I excluded |
| `run_metrics_job.py` line 192 | `--skip-wm` defaults to `True` (WM skipped) |
| `test_mock_metrics.py` line 382 | Asserts `"wm_RNA_BATCH" not in result` for default `compute_all_metrics` call |

The required behavior: Group I is in the default active set, and `--skip-wm` (now available in both worker and dispatcher) is the opt-out mechanism, symmetric to how `--skip-slow` opts out of Group F.

### Fix A — `compute_batch_metrics.py` (lines 1364–1368)

Change the default active set and update the comment:

```python
    # Determine which groups to run
    # F is gated by skip_slow; I is in the default active set (opt-out via --skip-wm)
    active: set[str] = (
        set("ABCDEFGHIJK") if groups is None      # ← was "ABCDEFGHJK"
        else {g.upper().strip() for g in groups}
    )
```

### Fix B — `run_metrics_job.py` (lines 187–193)

Change `--skip-wm` default from `True` to `False` and update the help text:

```python
    parser.add_argument(
        "--skip-wm",
        type=lambda x: x.lower() not in ("false", "0", "no"),
        default=False,                              # ← was True
        metavar="BOOL",
        help="Skip WaterMelon score (Group I). Default: False (WM computed). Pass True to skip.",
    )
```

With this change, the logic at lines 218–219:
```python
    if not args.skip_wm:
        requested_groups.add("I")
```
now fires by default (since `args.skip_wm` is `False`), so the default `requested_groups` becomes `set("ABCDEFGHIJK")`.

### Fix C — `test_mock_metrics.py` (function `test_new_keys_in_compute_all`, lines 372–387)

The test currently asserts WM is absent from the default result (line 382) and verifies it appears only when Group I is explicitly requested (lines 384–387). Both checks must be updated to match the new default:

**Current code:**
```python
def test_new_keys_in_compute_all() -> None:
    print("\n--- test_new_keys_in_compute_all ---")
    exp_df, ann_df = _make_data(n_samples=60, n_genes=80)
    result = compute_all_metrics(exp_df, ann_df, skip_slow=True)

    for k in ["pct_var_pc1", "pct_var_pc10", "pct_var_cum_top10"]:
        _check(k in result, f"key_in_compute_all:{k}")
    for k in ["n_genes_noNA", "pct_genes_noNA", "n_samples_noNA", "pct_samples_noNA",
              "n_genes_allNA", "n_samples_allNA", "n_na_cells", "pct_na_cells"]:
        _check(k in result, f"key_in_compute_all:{k}")
    _check("wm_RNA_BATCH" not in result, "wm_not_in_default_compute_all")

    result_with_wm = compute_all_metrics(
        exp_df, ann_df, skip_slow=True, groups={"E", "J", "K", "I", "A", "B", "C", "G", "H", "D"}
    )
    _check("wm_RNA_BATCH" in result_with_wm, "wm_present_when_I_in_groups")
```

**Replacement:**
```python
def test_new_keys_in_compute_all() -> None:
    print("\n--- test_new_keys_in_compute_all ---")
    exp_df, ann_df = _make_data(n_samples=60, n_genes=80)
    result = compute_all_metrics(exp_df, ann_df, skip_slow=True)

    for k in ["pct_var_pc1", "pct_var_pc10", "pct_var_cum_top10"]:
        _check(k in result, f"key_in_compute_all:{k}")
    for k in ["n_genes_noNA", "pct_genes_noNA", "n_samples_noNA", "pct_samples_noNA",
              "n_genes_allNA", "n_samples_allNA", "n_na_cells", "pct_na_cells"]:
        _check(k in result, f"key_in_compute_all:{k}")
    # WM is now default (Group I in default active set)
    _check("wm_RNA_BATCH" in result, "wm_in_default_compute_all")

    # Verify WM is absent when Group I is explicitly excluded
    result_no_wm = compute_all_metrics(
        exp_df, ann_df, skip_slow=True,
        groups={"E", "J", "K", "A", "B", "C", "G", "H", "D"}
    )
    _check("wm_RNA_BATCH" not in result_no_wm, "wm_absent_when_I_excluded_from_groups")
```

Key changes:
- Line 382: flip from "not in" to "in" — WM is now expected in the default result.
- Lines 384–387: replaced with an exclusion test that verifies the explicit `groups=` override can still suppress Group I.

### Timing impact

Synthetic data used in tests has N=60 (`_make_data(n_samples=60, n_genes=80)`). With Ward linkage on 60 samples and M=200 permutations, the WM computation takes ~1–3 seconds on the pod. Total test suite runtime is expected to increase by roughly 15–30 seconds (WM runs in `test_all_keys_present`, `test_random_batch_low_r2`, `test_strong_batch_high_r2`, `test_group_failure_isolation`, `test_degenerate_single_batch`, and `test_new_keys_in_compute_all`).

---

## Summary of Changes

| File | Lines to change | Change |
|---|---|---|
| `test_mock_metrics.py` | 298–304 | Replace read-only `.values[rows, cols]` assignment with writable `to_numpy().copy()` + DataFrame reconstruction |
| `test_mock_metrics.py` | 372–387 | Flip WM default assertion: `not in` → `in`; add exclusion test replacing the old `result_with_wm` block |
| `compute_batch_metrics.py` | 1365–1367 | Change default active set from `"ABCDEFGHJK"` to `"ABCDEFGHIJK"`; update comment |
| `run_metrics_job.py` | 190–193 | Change `--skip-wm` default from `True` to `False`; update help text |
| `run_metrics_parallel.py` | 229, 270, 343, 355–358, 392 | Add `skip_wm` param to `run_dispatcher()`; add `--skip-wm` to `launch()` cmd; add `--skip-wm` to argparse; update `--groups` help text; pass `skip_wm=args.skip_wm` |

---

## Step-by-Step To-Do List

- [x] **1.** Fix `test_mock_metrics.py` lines 298–304: replace read-only array assignment (Problem 1).
- [x] **2.** Update `test_mock_metrics.py` lines 372–387: flip WM default assertion; add exclusion test (Problem 3, test side).
- [x] **3.** Update `compute_batch_metrics.py` line 1367: change default active set to `"ABCDEFGHIJK"` (Problem 3, library side).
- [x] **4.** Update `run_metrics_job.py` line 192: change `--skip-wm` default to `False` (Problem 3, worker side).
- [x] **5.** Update `run_metrics_parallel.py`: add `skip_wm` to `run_dispatcher()`, `launch()`, argparse, and `main()` call (Problem 2 + Problem 3, dispatcher side).
- [x] **6.** Run `python test_mock_metrics.py` locally/in pod and confirm all tests pass. *(108/108 passed)*
- [ ] **7.** Run single-job integration test in pod to confirm WM is computed by default:
      ```bash
      python run_metrics_job.py \
          --strat A_confirmed_bad --imp strict --method 16_fsqn_r \
          --post-rm False \
          --out-json /tmp/test_metrics.json \
          --out-genes-json /tmp/test_genes.json \
          --skip-slow
      python -c "import json; d=json.load(open('/tmp/test_metrics.json')); print(d.get('wm_RNA_BATCH'), d.get('wm_subsampled'))"
      ```
- [ ] **8.** Sync updated scripts to pod via rsync and re-run the dispatcher:
      ```bash
      nohup python run_metrics_parallel.py \
          --n-workers 2 --post-rm-filter post0 --memory-limit-gb 8.0 \
          > /workspace/metrics_wm_default_pass.log 2>&1 &
      ```
- [x] **9.** Update `CLAUDE.md` (this directory): change Group I documentation from "opt-in" to "default"; update example commands to remove `--skip-wm False` (now redundant); add `--skip-wm` flag documentation for the dispatcher.
