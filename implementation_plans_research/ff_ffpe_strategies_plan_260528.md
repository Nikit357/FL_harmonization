# Implementation Plan — FF-only and FFPE-only Filter Strategies

**Date:** 2026-05-28  
**Author:** plan by Claude Code, reviewed and annotated by Daniil Nikitin

---

## Overview

Add two new prior batch-removal strategies to the harmonization benchmark:

| Key | Description | Filter logic on `RNA_BATCH` |
|---|---|---|
| `J_ff_only` | Keep only Fresh-Frozen (FF) tissue samples | `"_FF_" in batch_name` |
| `K_ffpe_only` | Keep only FFPE tissue samples | `"_FFPE_" in batch_name` |

**Scientific motivation:** `RNA_BATCH` encodes tissue preservation in its second component (e.g., `RNASeq_FF_PolyA`, `GPL570_FFPE_Unknown`). Isolating FF-only or FFPE-only samples removes one major confounding axis (preservation chemistry) before batch correction, and enables a direct comparison of harmonization performance within a single preservation type.

**Design decision:**  
Use `"_FF_" in batch_name` as a simple substring check. This correctly distinguishes FF (`_FF_`) from FFPE (`_FFPE_`) because FFPE does **not** contain the substring `_FF_` (the sequence `_FFPE_` has 'P' after the two F's, not an underscore). No regex needed.

**Naming convention:** `J_ff_only` and `K_ffpe_only` follow the existing alphabetical prefix (`S0`, `A`–`I`) and lowercase snake-case description pattern. The pipeline currently has **12** strategies (S0 through I, including `I_rare_batches_removed`); adding J and K brings the total to **14**.

Note: metric groups in `compute_batch_metrics.py` also use letters J and K (PC-variance and NA-retention respectively). These are in a different namespace (`strat` column vs. metric-group identifier) and do not conflict at runtime.

---

## Background: RNA_BATCH preservation patterns

The second field in `RNA_BATCH` (split by `_`) encodes tissue preservation:

| Pattern | Example values | Meaning |
|---|---|---|
| `_FF_` | `RNASeq_FF_PolyA`, `GPL570_FF_Unknown`, `GPL96_FF_Unknown` | Fresh frozen (RNA-seq and microarray) |
| `_FFPE_` | `RNASeq_FFPE_Exome_capture` (929 samples), `GPL570_FFPE_Unknown`, `GPL14951_FFPE_Unknown` | Formalin-fixed (RNA-seq and microarray) |
| `_Unknown_` | `GPL570_Unknown_Unknown` | Unknown / not reported |

Key data points:
- `J_ff_only` retains both RNA-seq FF batches (e.g., `RNASeq_FF_PolyA`) and microarray FF batches.
- `K_ffpe_only` retains both the large RNA-seq FFPE batch (`RNASeq_FFPE_Exome_capture`, 929 samples) and microarray FFPE batches. FFPE is not rare in RNA-seq in this dataset.

**S3 output counts after adding 2 strategies:**
- `run_prep_parallel.py`: +2 strats × 4 imps = **+8 new prepared S3 pairs**
- `run_norm_parallel.py`: +2 strats × 4 imps × 39 methods × 2 post_rm = **+624 new normalized S3 files** (fewer after RNA-seq-only guard skips)
- `run_shambhala_parallel.py`: +2 strats × 18 P/Q variants × 3 imps × 2 post_rm = **+216 new Shambhala S3 files** (derived via Case B, **no Octave re-run needed**)

---

## Files to Change

### 1. `harmonization-scripts/bench_shared.py`

**1a. Docstring of `build_filter_strategies()` — update count**

The docstring currently reflects an older count (11 strategies, before `I_rare_batches_removed` was added). Update to the correct current count.

Before:
```python
    Build all 11 filter strategies from annotation and expression data.
```
After:
```python
    Build all 14 filter strategies from annotation and expression data.
```

Before:
```python
    Returns
    -------
    Dict mapping strategy name → filtered annotation DataFrame (11 entries).
```
After:
```python
    Returns
    -------
    Dict mapping strategy name → filtered annotation DataFrame (14 entries).
```

**1b. Inside `build_filter_strategies()` — add two batch lists and two filtered annotations**

After the existing `affymetrix_batches` line (line ~476), insert:
```python
    ff_batches         = [b for b in ann_base[BATCH_COL].unique() if "_FF_" in b]
    ffpe_batches       = [b for b in ann_base[BATCH_COL].unique() if "_FFPE_" in b]
```

After the existing `ann_I` line (line ~491), add:
```python
    ann_J  = _f(keep_batches=ff_batches)
    ann_K  = _f(keep_batches=ffpe_batches)
```

**1c. `strategies` dict — add two new entries**

Before:
```python
        "I_rare_batches_removed": ann_I,
    }
```
After:
```python
        "I_rare_batches_removed": ann_I,
        "J_ff_only":              ann_J,
        "K_ffpe_only":            ann_K,
    }
```

---

### 2. `harmonization-scripts/run_prep_parallel.py`

**2a. Module docstring — update "all 11" count and valid-values list (lines ~75–79)**

Before:
```
Comma-separated subset of strategy names to run (default: all 11).
Valid values: S0_no_removal, A_confirmed_bad, B_extended_bad, C_rnaseq_only,
    D_malignant_only, E1_iterative_r1, E2_iterative_r2, E3_iterative_r3,
    F_microarray_only, G_affymetrix_only, H_affymetrix_extended,
    I_rare_batches_removed.
```
After:
```
Comma-separated subset of strategy names to run (default: all 14).
Valid values: S0_no_removal, A_confirmed_bad, B_extended_bad, C_rnaseq_only,
    D_malignant_only, E1_iterative_r1, E2_iterative_r2, E3_iterative_r3,
    F_microarray_only, G_affymetrix_only, H_affymetrix_extended,
    I_rare_batches_removed, J_ff_only, K_ffpe_only.
```

**2b. `ALL_STRATEGIES` list (lines ~118–124)**

Before:
```python
ALL_STRATEGIES: list[str] = [
    "S0_no_removal", "A_confirmed_bad", "B_extended_bad",
    "C_rnaseq_only", "D_malignant_only",
    "E1_iterative_r1", "E2_iterative_r2", "E3_iterative_r3",
    "F_microarray_only", "G_affymetrix_only", "H_affymetrix_extended",
    "I_rare_batches_removed",
]
```
After:
```python
ALL_STRATEGIES: list[str] = [
    "S0_no_removal", "A_confirmed_bad", "B_extended_bad",
    "C_rnaseq_only", "D_malignant_only",
    "E1_iterative_r1", "E2_iterative_r2", "E3_iterative_r3",
    "F_microarray_only", "G_affymetrix_only", "H_affymetrix_extended",
    "I_rare_batches_removed", "J_ff_only", "K_ffpe_only",
]
```

---

### 3. `harmonization-scripts/run_norm_parallel.py`

**3a. Module docstring — update "all 12" count (line ~75)**

Before:
```
Comma-separated subset of strategy names (default: all 12). Only strategies
```
After:
```
Comma-separated subset of strategy names (default: all 14). Only strategies
```

**3b. `ALL_STRATEGIES` list (lines ~128–134)**

Before:
```python
ALL_STRATEGIES: list[str] = [
    "S0_no_removal", "A_confirmed_bad", "B_extended_bad",
    "C_rnaseq_only", "D_malignant_only",
    "E1_iterative_r1", "E2_iterative_r2", "E3_iterative_r3",
    "F_microarray_only", "G_affymetrix_only", "H_affymetrix_extended",
    "I_rare_batches_removed",
]
```
After:
```python
ALL_STRATEGIES: list[str] = [
    "S0_no_removal", "A_confirmed_bad", "B_extended_bad",
    "C_rnaseq_only", "D_malignant_only",
    "E1_iterative_r1", "E2_iterative_r2", "E3_iterative_r3",
    "F_microarray_only", "G_affymetrix_only", "H_affymetrix_extended",
    "I_rare_batches_removed", "J_ff_only", "K_ffpe_only",
]
```

---

### 4. `harmonization-scripts/run_cross_product_parallel.py`

**4a. `ALL_STRATEGIES` list (lines ~104–117)**

Before:
```python
ALL_STRATEGIES: list[str] = [
    "S0_no_removal",
    "A_confirmed_bad",
    ...
    "I_rare_batches_removed",
]
```
After (full list):
```python
ALL_STRATEGIES: list[str] = [
    "S0_no_removal",
    "A_confirmed_bad",
    "B_extended_bad",
    "C_rnaseq_only",
    "D_malignant_only",
    "E1_iterative_r1",
    "E2_iterative_r2",
    "E3_iterative_r3",
    "F_microarray_only",
    "G_affymetrix_only",
    "H_affymetrix_extended",
    "I_rare_batches_removed",
    "J_ff_only",
    "K_ffpe_only",
]
```

**4b. Argparse help text (line ~532)**

Before:
```python
                        help="Comma-separated subset of strategies (default: all 11)")
```
After:
```python
                        help="Comma-separated subset of strategies (default: all 14)")
```

---

### 5. `harmonization-scripts/CLAUDE.md`

**5a. Key function signature comment — update count**

Before:
```
strategies = build_filter_strategies(comb_ann, comb_exp)  # dict of 12 labeled annotation DataFrames
```
After:
```
strategies = build_filter_strategies(comb_ann, comb_exp)  # dict of 14 labeled annotation DataFrames
```

**5b. Benchmark cross-product description — update strategy count**

Before:
```
These scripts implement the **harmonization benchmark cross-product**: 39 batch-correction methods × 11 sample-removal strategies × 4 imputation approaches × 2 post-removal options = **3,432 S3 outputs**.
```
After:
```
These scripts implement the **harmonization benchmark cross-product**: 39 batch-correction methods × 14 sample-removal strategies × 4 imputation approaches × 2 post-removal options (original 12-strategy benchmark produced 3,432 S3 outputs; J/K add ~624 more).
```

---

### 6. `harmonization-scripts/project_overview.md`

**6a. `build_filter_strategies()` returns docstring line**

Before:
```
`build_filter_strategies(comb_ann, comb_exp)` returns a dict of 11 named annotation DataFrames:
```
After:
```
`build_filter_strategies(comb_ann, comb_exp)` returns a dict of 14 named annotation DataFrames:
```

**6b. Strategy table — add two rows after `I_rare_batches_removed`**

Before:
```
| `I_rare_batches_removed` | Exclude batches with < 50 samples |
```
After:
```
| `I_rare_batches_removed` | Exclude batches with < 50 samples |
| `J_ff_only`              | Keep only batches where `RNA_BATCH` contains `_FF_` (fresh frozen, RNA-seq + microarray) |
| `K_ffpe_only`            | Keep only batches where `RNA_BATCH` contains `_FFPE_` (FFPE, includes `RNASeq_FFPE_Exome_capture` 929 samples + microarray FFPE) |
```

**6c. `run_cross_product_parallel.py` grid defaults comment**

Before:
```
ALL_STRATEGIES  = 11  # S0, A, B, C, D, E1, E2, E3, F, G, H
```
After:
```
ALL_STRATEGIES  = 14  # S0, A, B, C, D, E1, E2, E3, F, G, H, I, J, K
```

---

### 7. `shambhala_adoption/Shambhala_containerized/harmonization_scripts/shambhala_bench_shared.py`

**7a. `ALL_STRATEGIES` list (lines ~51–64)**

Before:
```python
ALL_STRATEGIES: list[str] = [
    "S0_no_removal",
    "A_confirmed_bad",
    ...
    "I_rare_batches_removed",
]
```
After (full list):
```python
ALL_STRATEGIES: list[str] = [
    "S0_no_removal",
    "A_confirmed_bad",
    "B_extended_bad",
    "C_rnaseq_only",
    "D_malignant_only",
    "E1_iterative_r1",
    "E2_iterative_r2",
    "E3_iterative_r3",
    "F_microarray_only",
    "G_affymetrix_only",
    "H_affymetrix_extended",
    "I_rare_batches_removed",
    "J_ff_only",
    "K_ffpe_only",
]
```

---

### 8. `shambhala_adoption/Shambhala_containerized/harmonization_scripts/run_shambhala_job.py`

**8a. Module docstring — update strategy count references (lines ~1–22)**

Before:
```
Shambhala cross-product worker: runs Shambhala on the full S0 dataset for one
(imp × method) pair, then writes all 24 (strategy × post_rm) outputs to S3.

Three execution paths (selected automatically when --skip-if-exists is set):
  Case A — all 24 outputs already on S3: early exit, no downloads.
  ...
    FL_batch_correction/prepared/{strat}__{imp}__ann.tsv.gz   (×12 strategies)
    ...
    FL_batch_correction/exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz  (×24)
```
After:
```
Shambhala cross-product worker: runs Shambhala on the full S0 dataset for one
(imp × method) pair, then writes all 28 (strategy × post_rm) outputs to S3.

Three execution paths (selected automatically when --skip-if-exists is set):
  Case A — all 28 outputs already on S3: early exit, no downloads.
  ...
    FL_batch_correction/prepared/{strat}__{imp}__ann.tsv.gz   (×14 strategies)
    ...
    FL_batch_correction/exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz  (×28)
```

**8b. Worker description in `_build_parser()` (line ~103)**

Before:
```python
        description="Shambhala cross-product worker: one (imp × method) → 24 S3 outputs."
```
After:
```python
        description="Shambhala cross-product worker: one (imp × method) → 28 S3 outputs."
```

---

### 9. `shambhala_adoption/Shambhala_containerized/harmonization_scripts/CLAUDE.md`

**9a. Header counts**

Before:
```
Cross-product benchmark scripts for the Shambhala2 harmonization method. Runs 3 imputation methods × 18 P/Q calibration variants = **54 worker jobs**, each writing 24 (strategy × post_rm) outputs → **1,296 total S3 objects**.
```
After:
```
Cross-product benchmark scripts for the Shambhala2 harmonization method. Runs 3 imputation methods × 18 P/Q calibration variants = **54 worker jobs**, each writing 28 (strategy × post_rm) outputs → **1,512 total S3 objects** (original 12-strategy run produced 1,296; the 216 new objects for J/K are derived via Case B without re-running Octave).
```

**9b. Case A condition in three-case execution table**

Before:
```
| A | All 24 outputs present on S3 | Early exit | No |
```
After:
```
| A | All 28 outputs present on S3 | Early exit | No |
```

**9c. Key design insight line**

Before:
```
This collapses 54 × 12 = 648 potential Octave runs to just 54.
```
After:
```
This collapses 54 × 14 = 756 potential Octave runs to just 54.
```

**9d. S3 progress check comment**

Before:
```bash
    | grep shambhala | wc -l   # target: 1296
```
After:
```bash
    | grep shambhala | wc -l   # target: 1512 (after J/K added); 1296 for original 12-strategy run
```

---

### 10. `shambhala_adoption/Shambhala_containerized/CLAUDE.md`

**10a. Cross-product benchmark description**

Before:
```
**`harmonization_scripts/`** — cross-product benchmark: 3 imputations × 18 P/Q variants = 54 Shambhala runs → 1,296 S3 outputs (12 strategies × 2 post_rm each).
```
After:
```
**`harmonization_scripts/`** — cross-product benchmark: 3 imputations × 18 P/Q variants = 54 Shambhala runs → 1,512 S3 outputs (14 strategies × 2 post_rm each; J/K derived via Case B without Octave re-run).
```

**10b. Key insight in architecture section**

Before:
```
Key insight: Shambhala normalizes each sample independently. Run once on the full S0 (no-removal) dataset; filter post-hoc to each strategy's sample set. This reduces 54 × 12 = 648 Octave runs to just 54.
```
After:
```
Key insight: Shambhala normalizes each sample independently. Run once on the full S0 (no-removal) dataset; filter post-hoc to each strategy's sample set. This reduces 54 × 14 = 756 Octave runs to just 54.
```

---

### 11. `harmonization-metrics/harmonization_metrics_analysis_v2.ipynb`

**Cell to edit: Cell 21 (id=`cell-2-1-palettes`)**

**11a. `ALL_STRATS` list** — append two entries:

Before:
```python
ALL_STRATS = [
    "S0_no_removal",
    "A_confirmed_bad",
    "B_extended_bad",
    "C_rnaseq_only",
    "D_malignant_only",
    "E1_iterative_r1",
    "E2_iterative_r2",
    "E3_iterative_r3",
    "F_microarray_only",
    "G_affymetrix_only",
    "H_affymetrix_extended",
    "I_rare_batches_removed",
]
```
After:
```python
ALL_STRATS = [
    "S0_no_removal",
    "A_confirmed_bad",
    "B_extended_bad",
    "C_rnaseq_only",
    "D_malignant_only",
    "E1_iterative_r1",
    "E2_iterative_r2",
    "E3_iterative_r3",
    "F_microarray_only",
    "G_affymetrix_only",
    "H_affymetrix_extended",
    "I_rare_batches_removed",
    "J_ff_only",
    "K_ffpe_only",
]
```

**11b. `strat_pal` dict** — add two new color entries:

Before:
```python
    'I_rare_batches_removed': '#b095c5'#'#7b4f9e',
}
```
After:
```python
    'I_rare_batches_removed': '#b095c5',
    'J_ff_only':              '#7ecbc4',   # soft teal — fresh frozen
    'K_ffpe_only':            '#f2c27f',   # warm amber — FFPE
}
```

**Color rationale:**
- `J_ff_only` (`#7ecbc4`): teal/mint — evokes "fresh" tissue, cool hue, distinct from existing blues (S0) and greens (B).
- `K_ffpe_only` (`#f2c27f`): warm amber — evokes processed/fixed tissue, warm hue, distinct from orange-salmon (A) and yellow (F).

---

**Cell to edit: Cell 3 (id=`cell-1-2-load`)** — extend the I_rare guard to cover J and K:

Before:
```python
if "I_rare_batches_removed" not in AVAIL_STRATS:
    print("NOTE: I_rare_batches_removed strategy not in CSV — palette added, no data yet.")
```
After:
```python
for _new_strat in ["I_rare_batches_removed", "J_ff_only", "K_ffpe_only"]:
    if _new_strat not in AVAIL_STRATS:
        print(f"NOTE: {_new_strat} strategy not in CSV — palette added, no data yet.")
```

---

**Cell to edit: Cell 182 (id=`cell-47d993e6`)** — add missing `H_affymetrix_extended` and new J/K strategies to `HARSHNESS_ORDER`.

`H_affymetrix_extended` was already absent from the current list; this change adds it along with J and K.

Before (end of list):
```python
    ("I_rare_batches_removed", "strict"),
    ("I_rare_batches_removed", "knn"),
    ("I_rare_batches_removed", "softimpute"),
]
```
After:
```python
    ("I_rare_batches_removed", "strict"),
    ("I_rare_batches_removed", "knn"),
    ("I_rare_batches_removed", "softimpute"),
    ("H_affymetrix_extended", "strict"),
    ("H_affymetrix_extended", "knn"),
    ("H_affymetrix_extended", "softimpute"),
    ("J_ff_only", "strict"),
    ("J_ff_only", "knn"),
    ("J_ff_only", "softimpute"),
    ("K_ffpe_only", "strict"),
    ("K_ffpe_only", "knn"),
    ("K_ffpe_only", "softimpute"),
]
```

---

### 12. `harmonization-metrics/harmonization_metrics_visual_inspection.ipynb`

The visual inspection notebook does **not** define `strat_pal` or `ALL_STRATS`. Its cells load specific `(strat, imp, method)` combinations from S3 for embedding visualization.

The only change needed is a guard print in the data-load cell (Cell 3) so it is immediately obvious when J/K are not yet in the loaded CSV.

**Cell to edit: Cell 3 (data load and AVAIL_STRATS print)**:

Before (no guard exists):
```python
# no guard for new strategies
```
After (add after the existing AVAIL_STRATS print block):
```python
for _new_strat in ["J_ff_only", "K_ffpe_only"]:
    if _new_strat not in AVAIL_STRATS:
        print(f"NOTE: {_new_strat} not in CSV yet — will appear once metrics are computed.")
```

---

## Files That Do NOT Need to Change

| File | Reason |
|---|---|
| `run_metrics_job.py` | Accepts `--strat` as a CLI argument; no hardcoded strategy list |
| `run_metrics_parallel.py` | Discovers expression files by listing S3 objects; no `ALL_STRATEGIES` constant |
| `run_metrics_concat.py` | Aggregates all `*_metrics.json` sidecars; no strategy list |
| `compute_batch_metrics.py` | Pure metric computation; strategy-agnostic |
| `test_mock.py` (harmonization-scripts) | Tests strategies via `build_filter_strategies()` — picks up new entries automatically |
| `test_mock_metrics.py` | Uses synthetic data, no strategy enumeration |
| `run_prep_job.py` | Worker, receives `--strat` as CLI arg; no list |
| `run_norm_job.py` | Worker, receives `--strat` as CLI arg; no list |
| `run_shambhala_parallel.py` | Imports `ALL_STRATEGIES` from `shambhala_bench_shared.py`; no independent list |
| `derive_rare_batches_outputs.py` | Handles only `I_rare_batches_removed` (purpose-built fast-path). J/K are handled natively by Case B in `run_shambhala_job.py` once annotation files are on S3 |
| `k8s/pod-ssh.yaml`, `k8s/shambhala-pod.yaml` | Infrastructure only; no strategy lists |

---

## Side Effects and Caveats

### Cache invalidation (CRITICAL)
The bench filter strategies are cached to `/tmp/bench_filter_strategies.pkl`. Delete this file on both the batch-correction pod and the metrics pod before running new strategies:
```bash
rm -f /tmp/bench_filter_strategies.pkl /tmp/bench_comb_data.pkl
```

### Shambhala execution order (required before running shambhala parallel)
Case B in `run_shambhala_job.py` derives J/K outputs by row-filtering the existing `S0_no_removal__post0` matrix. For this to work, annotation files for J and K must exist on S3 first. Correct sequence:
1. Run `run_prep_parallel.py --strats J_ff_only,K_ffpe_only` to upload annotation files.
2. Run `run_shambhala_parallel.py --skip-if-exists` — each job detects 28 expected outputs (not 24). Since only 24 exist per method, Case B triggers: downloads `S0_no_removal__post0`, filters rows to J/K sample sets, uploads the 4 missing outputs per `(imp × method)`. No Octave is invoked.

### RNA-seq-only method guard
`J_ff_only` retains both RNA-seq FF and microarray FF batches — RNA-seq-only methods (22_tmm, 23_vst, 39_procrustes) will run normally.

`K_ffpe_only` retains the large RNA-seq FFPE batch (`RNASeq_FFPE_Exome_capture`, 929 samples) plus microarray FFPE batches — RNA-seq-only methods will also run normally for K. Both strategies have sufficient RNA-seq coverage; no automatic skips are expected.

### `H_affymetrix_extended` added to `HARSHNESS_ORDER`
`H_affymetrix_extended` was already absent from the existing `HARSHNESS_ORDER` list in Cell 182. This plan adds it together with J and K. Adding H does not affect any other cell in the notebook.

### S3 output count update
- Before (12 strategies): 3,432 normalized outputs (bench original) + 1,296 shambhala outputs
- After (14 strategies): ~4,056 normalized outputs (bench, +624 theoretical, fewer after platform-specific skips) + 1,512 shambhala outputs (+216 via Case B)

---

## Verification Commands

```bash
source ~/venvs/collagen_3_11/bin/activate

# 1. Smoke test — verify build_filter_strategies returns 14 entries
python -c "
import sys; sys.path.insert(0, 'harmonization-scripts')
from bench_shared import build_filter_strategies
import pickle, os
if os.path.exists('/tmp/bench_comb_data.pkl'):
    comb_exp, comb_ann = pickle.load(open('/tmp/bench_comb_data.pkl','rb'))
    strats = build_filter_strategies(comb_ann, comb_exp, cache_path='')
    print('Strategy count:', len(strats))
    print('Keys:', sorted(strats.keys()))
    print('J_ff_only samples:', len(strats['J_ff_only']))
    print('K_ffpe_only samples:', len(strats['K_ffpe_only']))
else:
    print('No cache found — run load_data() first or run on pod')
"

# 2. Import smoke test (no data needed)
cd harmonization-scripts && python test_mock.py

# 3. Check ALL_STRATEGIES consistency across all four files
python -c "
for fname in [
    'harmonization-scripts/run_prep_parallel.py',
    'harmonization-scripts/run_norm_parallel.py',
    'harmonization-scripts/run_cross_product_parallel.py',
    'shambhala_adoption/Shambhala_containerized/harmonization_scripts/shambhala_bench_shared.py',
]:
    with open(fname) as f:
        content = f.read()
    for line in content.split('\n'):
        if 'J_ff_only' in line:
            print(f'{fname}: {line.strip()}')
"

# 4. Verify new strategies in Shambhala constants
python -c "
import sys
sys.path.insert(0, 'shambhala_adoption/Shambhala_containerized')
from harmonization_scripts.shambhala_bench_shared import ALL_STRATEGIES
print('Shambhala ALL_STRATEGIES:', ALL_STRATEGIES)
assert 'J_ff_only' in ALL_STRATEGIES
assert 'K_ffpe_only' in ALL_STRATEGIES
assert len(ALL_STRATEGIES) == 14, f'Expected 14, got {len(ALL_STRATEGIES)}'
print('OK — 14 strategies')
"

# 5. After running prep jobs: confirm S3 annotation files exist
aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/prepared/ \
    | grep -E "J_ff_only|K_ffpe_only"

# 6. After running norm jobs: confirm expression files exist
aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/exp/ \
    | grep "J_ff_only" | wc -l
# Expected: up to 39 methods × 4 imps × 2 post_rm = 312 (minus platform-skip entries)
```

---

## TODO Checklist

Steps are ordered from core library → dispatchers → Shambhala → metrics → notebooks → operations.

### harmonization-scripts/

- [x] **`bench_shared.py`** — update `build_filter_strategies()` body docstring: "11" → "14" (line ~449)
- [x] **`bench_shared.py`** — update `build_filter_strategies()` Returns docstring: "11 entries" → "14 entries" (line ~466)
- [x] **`bench_shared.py`** — add `ff_batches` and `ffpe_batches` lists after `affymetrix_batches` definition (line ~476)
- [x] **`bench_shared.py`** — add `ann_J` and `ann_K` after `ann_I` definition (line ~491)
- [x] **`bench_shared.py`** — add `"J_ff_only": ann_J` and `"K_ffpe_only": ann_K` to `strategies` dict (line ~523)
- [x] **`run_prep_parallel.py`** — docstring: "all 11" → "all 14"; add `J_ff_only, K_ffpe_only` to valid values list (line ~75)
- [x] **`run_prep_parallel.py`** — `ALL_STRATEGIES`: append `"J_ff_only", "K_ffpe_only"` (line ~123)
- [x] **`run_norm_parallel.py`** — docstring: "all 12" → "all 14" (line ~75)
- [x] **`run_norm_parallel.py`** — `ALL_STRATEGIES`: append `"J_ff_only", "K_ffpe_only"` (line ~133)
- [x] **`run_cross_product_parallel.py`** — `ALL_STRATEGIES`: append `"J_ff_only", "K_ffpe_only"` (line ~116)
- [x] **`run_cross_product_parallel.py`** — argparse help: "all 11" → "all 14" (line ~532)
- [x] **`harmonization-scripts/CLAUDE.md`** — update `build_filter_strategies` comment: "dict of 12" → "dict of 14"
- [x] **`harmonization-scripts/CLAUDE.md`** — update benchmark cross-product description: strategy count and total outputs
- [x] **`harmonization-scripts/project_overview.md`** — update "dict of 11" → "dict of 14"
- [x] **`harmonization-scripts/project_overview.md`** — add `J_ff_only` and `K_ffpe_only` rows to strategy table
- [x] **`harmonization-scripts/project_overview.md`** — update `ALL_STRATEGIES = 11` → `14` in grid defaults comment

### shambhala_adoption/

- [x] **`harmonization_scripts/shambhala_bench_shared.py`** — `ALL_STRATEGIES`: append `"J_ff_only", "K_ffpe_only"` (line ~63)
- [x] **`harmonization_scripts/run_shambhala_job.py`** — module docstring: "all 24 outputs" → "all 28 outputs"; "×12 strategies" → "×14 strategies"; "×24" → "×28" (lines ~2–22)
- [x] **`harmonization_scripts/run_shambhala_job.py`** — `_build_parser()` description: "24 S3 outputs" → "28 S3 outputs" (line ~103)
- [x] **`harmonization_scripts/CLAUDE.md`** — header: "24 → 28 outputs", "1,296 → 1,512 total S3 objects"
- [x] **`harmonization_scripts/CLAUDE.md`** — Case A table row: "All 24 outputs" → "All 28 outputs"
- [x] **`harmonization_scripts/CLAUDE.md`** — key design insight: "54 × 12 = 648" → "54 × 14 = 756"
- [x] **`harmonization_scripts/CLAUDE.md`** — S3 progress check comment: update target count
- [x] **`Shambhala_containerized/CLAUDE.md`** — cross-product benchmark description: "1,296 S3 outputs (12 strategies)" → "1,512 S3 outputs (14 strategies)"
- [x] **`Shambhala_containerized/CLAUDE.md`** — key insight line: "54 × 12 = 648" → "54 × 14 = 756"

### harmonization-metrics/

- [x] **`harmonization_metrics_analysis_v2.ipynb` Cell 21** — `ALL_STRATS`: append `"J_ff_only"`, `"K_ffpe_only"`
- [x] **`harmonization_metrics_analysis_v2.ipynb` Cell 21** — `strat_pal`: add `'J_ff_only': '#7ecbc4'` and `'K_ffpe_only': '#f2c27f'`; fix trailing comment on I entry (`'#b095c5'#'...` → `'#b095c5',`)
- [x] **`harmonization_metrics_analysis_v2.ipynb` Cell 3** — replace single-strategy I guard with loop covering I, J, K
- [x] **`harmonization_metrics_analysis_v2.ipynb` Cell 182** — `HARSHNESS_ORDER`: append 3 tuples for `H_affymetrix_extended`, 3 for `J_ff_only`, 3 for `K_ffpe_only`
- [x] **`harmonization_metrics_visual_inspection.ipynb` Cell 3** — add guard print for `J_ff_only` and `K_ffpe_only` not in AVAIL_STRATS

### Operations (after all code changes)

- [ ] Delete `/tmp/bench_filter_strategies.pkl` on batch-correction pod before running (requires live pod)
- [ ] Delete `/tmp/bench_comb_data.pkl` on batch-correction pod (optional; only needed if `load_data` changed) (requires live pod)
- [x] Run `python harmonization-scripts/test_mock.py` to verify no import errors (exit code 0; 6 pre-existing R-package failures, all expected)
- [ ] Run `python harmonization-scripts/run_prep_parallel.py --strats J_ff_only,K_ffpe_only --n-workers 2 --skip-if-exists` to upload annotation files for bench (requires live pod)
- [ ] Run `python harmonization-scripts/run_norm_parallel.py --strats J_ff_only,K_ffpe_only --n-workers 4 --skip-if-exists` to normalize J/K for bench (requires live pod)
- [ ] Sync updated code to Shambhala pod (`rsync ...`) and reinstall (`pip install -e .`)
- [ ] Run `python harmonization_scripts/run_prep_parallel.py --strats J_ff_only,K_ffpe_only` on Shambhala pod (uploads annotation files needed by Case B)
- [ ] Run `python harmonization_scripts/run_shambhala_parallel.py --skip-if-exists` on Shambhala pod (Case B derives J/K automatically; no Octave re-run) (requires live pod)
- [ ] Run `python harmonization-metrics/run_metrics_parallel.py --strats J_ff_only,K_ffpe_only --skip-slow --n-workers 4` on metrics pod (requires live pod)
- [ ] Re-run `python harmonization-metrics/run_metrics_concat.py` to include J/K in `metrics_comprehensive.csv` (requires live pod)
- [ ] Re-execute analysis notebook Cells 3 and 21 to reload data and confirm new palette entries appear
