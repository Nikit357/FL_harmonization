# Implementation Plan: `I_rare_batches_removed` Filter Strategy

**Date:** 2026-05-16  
**Author:** Daniil Nikitin  
**Status:** Plan — pending approval before implementation

---

## Overview

Add a new batch-correction strategy, `I_rare_batches_removed`, that removes all `RNA_BATCH`
entries with fewer than 50 samples before harmonization. The idea is to avoid distorting
cross-batch normalization with batches too small to represent a stable expression profile.
Only batches with ≥ 50 samples are kept and harmonized together.

The threshold is computed **dynamically** from the actual annotation data (using
`ann_base[BATCH_COL].value_counts()`), not from a hardcoded list. This keeps the strategy
self-describing (the rule is the threshold, not a batch enumeration) and compatible with any
future dataset updates. A new module-level constant `MIN_BATCH_SIZE = 50` encodes the
threshold.

The name `I_rare_batches_removed` follows the capital-letter-first naming convention used by
all other strategies (A, B, C, D, E1–E3, F, G, H).

---

## Batches that will be removed (reference)

These 15 entries fall below the 50-sample threshold and will be excluded by the new strategy.
Listed for reference and manual verification:

| RNA_BATCH | Platform | N samples |
|---|---|---|
| GPL16686_FF_Unknown | Affymetrix Microarray | 48 |
| GPL13158_FF_Unknown | Affymetrix Microarray | 40 |
| GPL17586_FF_Unknown | Affymetrix Microarray | 40 |
| GPL1708_FF_Unknown | Agilent Microarray | 40 |
| GPL23541_FF_Unknown | Illumina NGS | 35 |
| RNASeq_FFPE_PolyA | Illumina NGS | 35 |
| RNASeq_FF_Total | Illumina NGS | 32 |
| GPL17077_FF_Unknown | Agilent Microarray | 24 |
| GPL887_FFPE_Unknown | Agilent Microarray | 24 |
| GPL26356_FF_Unknown | Illumina NGS | 15 |
| GPL17047_FF_Unknown | Affymetrix Microarray | 12 |
| GPL570_FF_Unknown | Illumina NGS | 11 |
| GPL6244_FFPE_Unknown | Affymetrix Microarray | 11 |
| GPL10739_FF_Unknown | Affymetrix Microarray | 4 |
| RNASeq_FF_Exome_capture | Illumina NGS | 2 |

**Note on `GPL17077_FF_Unknown`:** listed twice with counts 24 and 9 — these may be
sub-cohorts merged under one batch label. The dynamic threshold will handle both correctly.

Estimated samples remaining: ~5,000–5,300 (exact count will be printed when the
strategy is first built and cached).

---

## Files to change

### 1. `bench_shared.py` — core library

#### 1a. Add constant `MIN_BATCH_SIZE` (near line 84, after `BAD_COHORTS_B`)

```python
MIN_BATCH_SIZE: int = 50
```

Place it directly after `BAD_COHORTS_B: list[str] = ["SOM"]` (line 83) and before
`_AFFY_EXT_BATCHES` (line 88).

#### 1b. Update docstring of `build_filter_strategies()` (line 447)

Change:
```
Build all 10 filter strategies from annotation and expression data.
```
To:
```
Build all 11 filter strategies from annotation and expression data.
```

Also add one line to the `Returns` section:
```
Dict mapping strategy name → filtered annotation DataFrame (11 entries).
```

#### 1c. Add strategy computation inside `build_filter_strategies()` (after line 486)

After:
```python
ann_G  = _f(keep_batches=affymetrix_batches)
```

Add:
```python
# Strategy I: keep only batches with >= MIN_BATCH_SIZE samples.
# Count sample sizes on ann_base (after rare-group exclusion, before other removals)
# so the threshold is applied uniformly to the unfiltered batch universe.
_batch_counts   = ann_base[BATCH_COL].value_counts()
_large_batches  = _batch_counts[_batch_counts >= MIN_BATCH_SIZE].index.tolist()
ann_I           = _f(keep_batches=_large_batches)
```

#### 1d. Add the new key to the `strategies` dict (after line 516)

Add to the `strategies` dict (after `"H_affymetrix_extended"`):
```python
"I_rare_batches_removed": ann_I,
```

The final dict will have 12 entries.

---

### 2. `run_prep_parallel.py` — Stage 1 dispatcher

#### 2a. Module docstring (approx. line 75–78) — update strategy count and valid values

Change:
```
Comma-separated subset of strategy names to run (default: all 10).
Valid values: S0_no_removal, A_confirmed_bad, B_extended_bad, C_rnaseq_only,
    D_malignant_only, E1_iterative_r1, E2_iterative_r2, E3_iterative_r3,
    F_microarray_only, G_affymetrix_only, H_affymetrix_extended.
```
To:
```
Comma-separated subset of strategy names to run (default: all 11).
Valid values: S0_no_removal, A_confirmed_bad, B_extended_bad, C_rnaseq_only,
    D_malignant_only, E1_iterative_r1, E2_iterative_r2, E3_iterative_r3,
    F_microarray_only, G_affymetrix_only, H_affymetrix_extended,
    I_rare_batches_removed.
```

#### 2b. `ALL_STRATEGIES` list (lines 117–122)

Append `"I_rare_batches_removed"` as the last entry:
```python
ALL_STRATEGIES: list[str] = [
    "S0_no_removal", "A_confirmed_bad", "B_extended_bad",
    "C_rnaseq_only", "D_malignant_only",
    "E1_iterative_r1", "E2_iterative_r2", "E3_iterative_r3",
    "F_microarray_only", "G_affymetrix_only", "H_affymetrix_extended",
    "I_rare_batches_removed",
]
```

---

### 3. `run_norm_parallel.py` — Stage 2 dispatcher

#### 3a. Module docstring (approx. line 73–78)

Change the `--strats LIST` help text: `(default: all 10)` → `(default: all 11)`, and add
`I_rare_batches_removed` to the list of valid values.

#### 3b. `ALL_STRATEGIES` list (lines 128–133)

Append `"I_rare_batches_removed"` as the last entry (same change as in `run_prep_parallel.py`).

---

### 4. `run_cross_product_parallel.py` — monolithic pipeline dispatcher

#### 4a. argparse help string (approx. line 531)

Change:
```python
help="Comma-separated subset of strategies (default: all 10)"
```
To:
```python
help="Comma-separated subset of strategies (default: all 11)"
```

#### 4b. `ALL_STRATEGIES` list (lines 104–116)

Append `"I_rare_batches_removed"` as the last entry.

---

### 5. `project_overview.md` — developer reference document

#### 5a. Strategy table header (line 47)

Change:
```
`build_filter_strategies(comb_ann, comb_exp)` returns a dict of 11 named annotation DataFrames:
```
To:
```
`build_filter_strategies(comb_ann, comb_exp)` returns a dict of 12 named annotation DataFrames:
```

#### 5b. Strategy table body (after line 61, after `H_affymetrix_extended` row)

Add a new row:
```markdown
| `I_rare_batches_removed` | Batches with ≥ 50 samples only (`RNA_BATCH` value count ≥ `MIN_BATCH_SIZE`); removes 15 small batches including Agilent-only and niche NGS protocols |
```

#### 5c. `ALL_STRATEGIES` count comment (line 210)

Change:
```
ALL_STRATEGIES  = 11  # S0, A, B, C, D, E1, E2, E3, F, G, H
```
To:
```
ALL_STRATEGIES  = 12  # S0, A, B, C, D, E1, E2, E3, F, G, H, I
```

---

### 6. `CLAUDE.md` (harmonization-scripts subdirectory)

**One location — `bench_shared.py` key function signatures section:**

Change:
```
strategies = build_filter_strategies(comb_ann, comb_exp)  # dict of 11 labeled annotation DataFrames
```
To:
```
strategies = build_filter_strategies(comb_ann, comb_exp)  # dict of 12 labeled annotation DataFrames
```

This file is at `~/FL_harmonization/harmonization-scripts/CLAUDE.md`
inside the `bench_shared.py — Key Reference` section, under `Key function signatures`.

---

### 7. `make_slides.py` — presentation generator

#### 7a. Strategy count in slide text (approx. line 262)

Change:
```
"25 batch-correction methods  ×  10 sample-removal strategies\n"
```
To:
```
"25 batch-correction methods  ×  11 sample-removal strategies\n"
```
(or whatever the current total method count is; adjust accordingly)

#### 7b. Strategy table on slide 5 (approx. line 364)

Change the strategy count cell:
```python
["Sample-removal strategy", "10", "Which batches / cohorts to exclude before normalization"],
```
To:
```python
["Sample-removal strategy", "11", "Which batches / cohorts to exclude before normalization"],
```

#### 7c. Strategy table rows (approx. line 387 block)

Add a row for the new strategy after `H_affymetrix_extended`:
```python
["I_rare_batches_removed", "Batches ≥ 50 samples only (removes 15 small batches)", "~5,100", "Avoids distortion from under-represented batches"],
```

#### 7d. Pipeline overview text (approx. line 581–584)

Change:
```
│  40 jobs: 10 strategies × 4 imputation approaches  |  4 workers     │
```
To:
```
│  44 jobs: 11 strategies × 4 imputation approaches  |  4 workers     │
```
And add `I_rare_batches_removed` to the listed filter strategies.

---

### 8. `README.md` — new human-readable folder guide

Create a new file `harmonization-scripts/README.md` describing the folder content and
providing a usage guide. Contents should include:

- **Purpose:** what this directory does (harmonization benchmark cross-product: 39 methods ×
  11+ strategies × 4 imputation × 2 post-removal options → S3 outputs)
- **Prerequisites:** Python venv (`~/venvs/collagen_3_11/`), AWS credentials, S3 input data
  already uploaded
- **Script roles table:** one-line description of every `.py` file in the directory
- **Quick-start:** how to run the two-stage pipeline (Stage 1 prep, Stage 2 norm) and the
  monolithic fallback, with copy-paste commands
- **Filter strategies table:** all named strategies with a brief description of what each
  removes
- **Output structure:** S3 key patterns for prepared pairs and normalized outputs
- **Extending the benchmark:** how to add a new normalization method or a new filter strategy
- **Troubleshooting:** pointer to the Known startup failures table in `CLAUDE.md`

---

## Cache invalidation note

The filter strategies are cached at `/tmp/bench_filter_strategies.pkl`. Because the new
strategy is added to the dict, **any existing cache from a previous run will be stale** —
it will be missing the `I_rare_batches_removed` key. Workers calling
`build_filter_strategies()` will load the old cache and not find the new strategy.

**Before running the new strategy:** delete the cache on the pod and on any local
machine where benchmarks are run:

```bash
rm -f /tmp/bench_filter_strategies.pkl
```

The dispatcher scripts do not auto-invalidate the cache; this must be done manually.

---

## Impact on S3 outputs

The new strategy adds **4 new prepared pairs** to Stage 1 (one per imputation method):
```
FL_batch_correction/prepared/I_rare_batches_removed__strict__exp.tsv.gz
FL_batch_correction/prepared/I_rare_batches_removed__knn__exp.tsv.gz
FL_batch_correction/prepared/I_rare_batches_removed__missforest__exp.tsv.gz
FL_batch_correction/prepared/I_rare_batches_removed__softimpute__exp.tsv.gz
```

And **156 new normalized outputs** in Stage 2 (39 methods × 4 imputation × 2 post_rm):
```
FL_batch_correction/exp/I_rare_batches_removed__{imp}__{method}__post{0|1}.tsv.gz
```

Total cross-product remains consistent with the existing naming convention.

---

## Files that do NOT need to change

| File | Reason |
|---|---|
| `k8s/README.md` | No direct strategy enumeration |
| `run_prep_job.py` | Worker receives strategy name as CLI argument; no hardcoded list |
| `run_norm_job.py` | Same as above |
| `run_one_job.py` | Same as above |
| `load_cross_product_results.py` | Strategy-agnostic; reads from S3 by key pattern |
| `test_mock.py` | Smoke test; strategy-agnostic |
| `harmonization-metrics/` | Metrics pipeline is downstream; strategy name is passed as `--strat` argument |

---

## Verification commands

After implementation, verify with:
```bash
source ~/venvs/collagen_3_11/bin/activate
python harmonization-scripts/test_mock.py
```
The smoke test does not exercise `build_filter_strategies()` but will catch any import
errors introduced by the changes to `bench_shared.py`.

To manually verify the new strategy key is present:
```python
from bench_shared import build_filter_strategies, load_data
comb_exp, comb_ann = load_data()
strats = build_filter_strategies(comb_ann, comb_exp, cache_path="")
print(list(strats.keys()))
print(f"I_rare_batches_removed: {len(strats['I_rare_batches_removed'])} samples")
```

---

## Summary of all files and changes

| File | Change type | Detail |
|---|---|---|
| `bench_shared.py` | Code + docstring | Add `MIN_BATCH_SIZE = 50` constant; add `ann_I` computation; add `"I_rare_batches_removed"` to `strategies` dict; update docstring count 10 → 11 |
| `run_prep_parallel.py` | Code + docstring | Add to `ALL_STRATEGIES`; update `--strats` help text count and valid-values list |
| `run_norm_parallel.py` | Code + docstring | Add to `ALL_STRATEGIES`; update `--strats` help text count and valid-values list |
| `run_cross_product_parallel.py` | Code + docstring | Add to `ALL_STRATEGIES`; update argparse help count |
| `project_overview.md` | Documentation | Update strategy table header count; add new table row; update `ALL_STRATEGIES` comment |
| `CLAUDE.md` (harmonization-scripts) | Documentation | Update `build_filter_strategies` signature comment count |
| `make_slides.py` | Presentation | Update strategy count cells; add row to strategy table; update pipeline overview counts |
| `README.md` (harmonization-scripts) | New file | Human-readable folder guide: purpose, script roles, quick-start, strategies, S3 outputs, extending |

---

## TODO

### `bench_shared.py`
- [x] Add `MIN_BATCH_SIZE: int = 50` constant after `BAD_COHORTS_B: list[str] = ["SOM"]` (near line 83)
- [x] Update `build_filter_strategies()` docstring: change `"Build all 10 filter strategies"` → `"Build all 11 filter strategies"`
- [x] Update `build_filter_strategies()` Returns section: add `"Dict mapping strategy name → filtered annotation DataFrame (11 entries)."`
- [x] Add `_batch_counts`, `_large_batches`, `ann_I` computation after `ann_G = _f(keep_batches=affymetrix_batches)` (near line 486)
- [x] Add `"I_rare_batches_removed": ann_I` to the `strategies` dict after `"H_affymetrix_extended"` (near line 516)

### `run_prep_parallel.py`
- [x] Update `--strats LIST` help text: `"(default: all 10)"` → `"(default: all 11)"`
- [x] Add `I_rare_batches_removed` to the valid-values list in the docstring (near line 75–78)
- [x] Append `"I_rare_batches_removed"` to `ALL_STRATEGIES` list (near line 117–122)

### `run_norm_parallel.py`
- [x] Update `--strats LIST` help text: `"(default: all 10)"` → `"(default: all 11)"`
- [x] Add `I_rare_batches_removed` to the valid-values list in the docstring (near line 73–78)
- [x] Append `"I_rare_batches_removed"` to `ALL_STRATEGIES` list (near line 128–133)

### `run_cross_product_parallel.py`
- [x] Update argparse help: `"(default: all 10)"` → `"(default: all 11)"` (near line 531)
- [x] Append `"I_rare_batches_removed"` to `ALL_STRATEGIES` list (near line 104–116)

### `project_overview.md`
- [x] Update benchmark job count and `build_filter_strategies()` label count (11→12 labeled datasets, keys list updated)

### `CLAUDE.md` (harmonization-scripts)
- [x] Update `build_filter_strategies` signature comment: `"dict of 11 labeled"` → `"dict of 12 labeled"`

### `make_slides.py`
- [x] Update slide strategy count text: `"10 sample-removal strategies"` → `"11 sample-removal strategies"` (near line 262)
- [x] Update strategy table count cell: `"10"` → `"11"` (near line 364)
- [x] Add `["I_rare_batches_removed", ...]` row after `G_affymetrix_only` (near line 387)
- [x] Update pipeline overview job count: `"40 jobs: 10 strategies"` → `"44 jobs: 11 strategies"` (near line 581–584)
- [x] Add `I_rare_batches_removed` to the listed filter strategies in the pipeline overview text

### `README.md` (harmonization-scripts) — new file
- [x] Created `harmonization-scripts/README.md` with: purpose, prerequisites, script roles table, quick-start commands (two-stage + monolithic), filter strategies table, S3 output structure, instructions for extending the benchmark, troubleshooting pointer

### Post-implementation checks
- [ ] Delete `/tmp/bench_filter_strategies.pkl` on the K8s pod before running the new strategy
- [x] Run `python harmonization-scripts/test_mock.py` — exit code 0, all PASS/SKIP (6 pre-existing R-package failures: 27_dwd, 28_npn, 31_ruv3prps, 33_amdbnorm, 34_arsyn, 38_harman — unrelated to this change)
- [ ] Manually verify new key: `print(list(strats.keys()))` and `len(strats['I_rare_batches_removed'])` (requires live S3 data)
- [ ] Confirm sample count is in expected range ~5,000–5,300 (requires live S3 data)
