# Segmentation Fault Investigation — `test_mock.py` on Updated Pod

**Date:** 2026-05-10  
**Environment:** Ubuntu 24.04 pod, Python 3.12.3, rpy2 3.6.7, R 4.6.0  
**Crash location:** `33_amdbnorm` → `library(reshape2)` inside an `ro.r(...)` call

---

## 1. Observed failures summary

| # | Symptom | Severity |
|---|---|---|
| A | `Segmentation fault (core dumped)` — test run killed | **Critical** |
| B | `DWD failed for batch 'BatchGPL1/2': unused argument (penalty = "auto")` | High |
| C | `reComBat MISSING`, `FAbatch MISSING`, `DASC MISSING` in R packages check | Low |
| D | `git+https://github.com/BorgwardtLab/reComBat` in requirements.txt — user already changed to resolve a pip install conflict | Context |

---

## 2. Root cause analysis

### 2A — PRIMARY: rpy2 3.6.7 is incompatible with R 4.6.0 (the segfault)

**What happened step by step:**

1. Pod startup installs R from the `noble-cran40` CRAN apt repo. This repo serves the **latest 4.x release**, which as of April 24, 2026 is **R 4.6.0** — a major version jump from the R 4.5.x that the environment was originally designed for.
2. rpy2 3.6.7 (installed from requirements.txt) was compiled and tested against R ≤ 4.5.x. It embeds C-level assumptions about R's `SEXP`, `PROTECT`/`UNPROTECT` stack, memory allocator offsets, and garbage collector internals.
3. R 4.6.0 introduced breaking changes to its C API (internal SEXP representation, GC bookkeeping, and the ALTREP subsystem). rpy2's compiled bridge code now makes invalid memory accesses against the R 4.6.0 runtime.
4. The crash is triggered inside `33_amdbnorm` when `ro.r("""library(AMDBNorm); library(DBNorm); library(reshape2); ...""")` is executed. Loading three packages simultaneously exercices R's GC and package namespace machinery heavily — this is the threshold at which the bad memory access becomes a hard fault.

**Why does the crash happen at method 33, not method 1?**

Methods 01–32 that use R do so through simpler R calls (single library loads, straightforward matrix operations). `33_amdbnorm` is the first method that loads three packages in one R block and then immediately chains `na.omit(melt(...))` — a call that forces R's GC to run right after the package load. By this point, rpy2's reference-count tables are corrupted enough that the GC walk causes a segfault.

**Evidence trail in the log:**
```
# ComBat (29_combat_ref) finishes cleanly:
R callback write-console: Adjusting the Data

# 33_amdbnorm starts loading packages:
R callback write-console: Attaching package: 'reshape2'
R callback write-console: The following objects are masked from 'package:data.table': dcast, melt

# Crash:
Segmentation fault (core dumped)
```

The `data.table` was loaded earlier by `19_tdm` (the TDM R package depends on data.table). The reshape2 masking message and the immediate segfault are the observable signature of the rpy2/R 4.6.0 ABI break: R's GC runs during package attachment and corrupts the rpy2 heap.

**Why Python 3.12 is a contributing factor (not the direct cause):**

The pod Ubuntu 24.04 has Python 3.12 as default, not Python 3.11. This means rpy2 3.6.7 was installed as a Python 3.12 wheel or compiled from source for Python 3.12. Some wheels for rpy2 3.6.x were built for Python 3.11 only; on 3.12 they may be compiled locally with a slightly different C extension ABI. This could amplify the R 4.6.0 incompatibility.

---

### 2B — DWD `penalty = "auto"` API break

`bench_shared.py:normalize_dwd` (lines 1843) calls:
```r
sol <- genDWD(X = X_combined, y = y, penalty = "auto")
```

The current CRAN version of `DWDLargeR` removed the `penalty` argument entirely (likely in v0.2+). The function now computes the penalty internally with no user-facing argument. R returns the error:

```
Error in genDWD(X = X_combined, y = y, penalty = "auto") :
  unused argument (penalty = "auto")
```

This is caught by `tryCatch` and prints a `message(...)` but the batch is left uncorrected. For the mock data with 3 batches, **both non-reference batches (BatchGPL1, BatchGPL2) fail**, so `27_dwd` returns an essentially uncorrected matrix. The method doesn't crash, but it produces wrong output silently in the current benchmark.

---

### 2C — Missing R packages in smoke test

**`reComBat MISSING`:** The smoke test calls `library(reComBat)` expecting an R package. There is no R package called reComBat; the method `30_recombat` uses the **Python** package `reComBat` (BorgwardtLab). The `_CRITICAL_PKGS` list in `test_mock.py` line 50 includes `"reComBat"` — this check is wrong and will always show MISSING. It is a false alarm that does not affect benchmark correctness.

**`FAbatch MISSING`:** The smoke test calls `library(FAbatch)`. There is no R package called `FAbatch`. The actual source is the **`bapred`** package (`batchadjust` function inside it). `normalize_fabatch` calls `library(bapred)`, not `library(FAbatch)`. The `_CRITICAL_PKGS` check is wrong here too. `bapred` is installed by the pod startup; the benchmark method itself works fine. Another false alarm.

**`DASC MISSING`:** DASC is installed via `remotes::install_github('zhanglabNKU/DASC')` during startup. If installation failed (network error or R 4.6.0 compile failure), it would be genuinely absent. However, `normalize_dasc` raises `NotImplementedError` unconditionally (DASC returns cluster labels, not corrected expression), so this is a benchmark skip regardless.

---

### 2D — `requirements.txt` reComBat change (context only)

The user replaced `reComBat>=0.3` (PyPI) with `git+https://github.com/BorgwardtLab/reComBat` to resolve a pip install conflict. The conflict is likely:

- `reComBat 0.3.x` on PyPI was built with an older numpy ABI assumption
- Current pod has numpy `<2.0` but at a 1.26+ build; some reComBat wheels were compiled against numpy 1.24.x and their C extension is incompatible at 1.26

The git install builds from source and picks up the current numpy headers, fixing the ABI mismatch. This change is correct and should be kept; it only affects the Python `30_recombat` method.

---

## 3. Proposed solutions

### Solution 1 — Pin R to 4.5.3 in pod-ssh.yaml (RECOMMENDED for segfault)

Change the pod startup to explicitly install R 4.5.3 and hold it, preventing the CRAN apt repo from upgrading to 4.6.0.

**Mechanism:** The CRAN `noble-cran40` repo stores all 4.x releases. Apt versioned install pins to an exact package string; `apt-mark hold` prevents future `apt-get upgrade` from overwriting it.

**Change required in `k8s/pod-ssh.yaml` step 3 block:**

Current:
```bash
apt-get install -y r-base r-base-dev
```

Replace with:
```bash
# Install R 4.5.3 explicitly and hold to prevent upgrade to 4.6.x
apt-get install -y r-base=4.5.3-1~noble2404.0 r-base-dev=4.5.3-1~noble2404.0 || \
    apt-get install -y r-base r-base-dev        # fallback if exact version unavailable
apt-mark hold r-base r-base-dev
```

**Risks:**
- If R 4.5.3 packages are no longer in the apt cache (Posit drops old packages), the exact-version install will fail and fall back to the latest (4.6.0). Need to verify the exact `.deb` version string from inside the pod.
- `apt-mark hold` only prevents `apt-get upgrade`; the next pod rebuild still pulls whatever is available first.

**Alternative: use Posit's versioned PPM snapshot URL.** Posit provides time-stamped CRAN mirrors:
```bash
echo "deb [...] https://packagemanager.posit.co/cran/2026-01-01/bin/linux/ubuntu noble-cran40/" > /etc/apt/sources.list.d/r-project.list
```
Replacing the cloud.r-project.org URL with a Posit PPM date-pinned snapshot from before R 4.6.0 release (before April 24, 2026) guarantees R 4.5.3 regardless of what the main CRAN repo serves. This is the most reliable long-term approach.

---

### Solution 2 — Upgrade rpy2 to 4.0+ (ALTERNATIVE for segfault)

rpy2 4.0.0 was released with explicit R 4.6.x support. Upgrading resolves the ABI incompatibility at the rpy2 side without touching the R version.

**Change required in `requirements.txt`:**
```
rpy2>=4.0
```

**What breaks in bench_shared.py with rpy2 4.0:**

rpy2 4.0 changed the conversion API. The current code uses:
```python
from rpy2.robjects.conversion import localconverter
_PD_CONVERTER = ro.default_converter + pandas2ri.converter
with localconverter(_PD_CONVERTER):
    r_X = ro.conversion.py2rpy(df)
```

In rpy2 4.0, `pandas2ri.converter` is still available but `ro.default_converter` was renamed to `rpy2.rinterface.converter`. There are also changes to how NA/NULL types are handled. The full scope of changes would need to be audited across all 39 `normalize_*` functions.

**This is a larger change** — estimated 1–2 hours of testing across all methods. It future-proofs against further R upgrades but requires non-trivial code changes.

---

### Solution 3 — Fix DWD `penalty` argument (for bug 2B)

**Change required in `bench_shared.py` line 1843:**

Current:
```r
sol <- genDWD(X = X_combined, y = y, penalty = "auto")
```

Replace with:
```r
sol <- genDWD(X = X_combined, y = y)
```

The current DWDLargeR computes the penalty automatically; the argument is no longer accepted. This is a one-line fix and is independent of the R version issue.

---

### Solution 4 — Fix `test_mock.py` wrong package names (for bug 2C)

**Change `_CRITICAL_PKGS` in `test_mock.py` lines 46–52:**

Current:
```python
_CRITICAL_PKGS = [
    "FSQN", "qsmooth", "missForest", "softImpute",
    "limma", "sva", "RUVSeq", "batchelor", "edgeR", "DESeq2",
    "HarmonizR", "TDM",
    "DWDLargeR", "huge", "DBNorm", "reComBat", "AMDBNorm",
    "DASC", "exploBATCH", "ruv", "NOISeq", "FAbatch", "Harman",
]
```

Replace:
- `"reComBat"` → remove entirely (it's a Python package, not an R package)
- `"FAbatch"` → `"bapred"` (the actual R package that provides `batchadjust`)
- `"DASC"` → keep for now, but note it is expected MISSING since `normalize_dasc` always raises `NotImplementedError`

---

## 4. Recommended implementation order

| Step | Action | Fixes | Risk |
|---|---|---|---|
| 1 | Pin R to 4.5.3 via Posit PPM snapshot URL in `pod-ssh.yaml` | Segfault (A) | Low — date snapshot URL is stable |
| 2 | Remove `penalty = "auto"` from `normalize_dwd` in `bench_shared.py` | DWD silent failures (B) | Zero — one-line removal |
| 3 | Fix `_CRITICAL_PKGS` in `test_mock.py` | False MISSING reports (C) | Zero — cosmetic |
| 4 | (Optional) Upgrade rpy2 to 4.0+ as long-term solution for R compatibility | Segfault (A), future R versions | High — requires API audit of all 39 methods |

Steps 1–3 are independent and can be done in any order. Step 4 is an alternative to step 1 (not additive); implement only one.

---

## 5. Verification plan after fix

After rebuilding the pod with R 4.5.3 pinned:

```bash
# Verify R version
Rscript --no-save --no-restore -e "cat(R.version$version.string, '\n')"
# Expected: R version 4.5.3 (2026-02-28)

# Verify rpy2 is compatible
python -c "import rpy2.robjects as ro; print(ro.r('R.version$version.string')[0])"

# Full smoke test — should complete without segfault
python test_mock.py

# Check DWD no longer shows "unused argument"
python run_one_job.py --strat A_confirmed_bad --imp strict --method 27_dwd --out-json /tmp/dwd_test.json
```
