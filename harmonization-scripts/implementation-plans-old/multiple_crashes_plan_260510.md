# Implementation Plan: Option A Fixes (qsmooth, fMM, png)

**Based on:** `multiple_crashes_research_260510.md`  
**Strategy:** Option A — stay on R 4.5.3 (Posit binary), fix the three remaining failures with targeted changes  
**Status:** Pending implementation  
**Date:** 2026-05-10

---

## Overview

| Fix | File | Lines | Risk |
|---|---|---|---|
| A1. Add `libpng-dev` + `zlib1g-dev` to step 2 | `k8s/pod-ssh.yaml` | 76 | Zero — purely additive to an existing apt list |
| A2. Fix qsmooth installation | `k8s/pod-ssh.yaml` | 123 | Low — replaces one Rscript line with two |
| A3. Remove deleted `fMM` GitHub install | `k8s/pod-ssh.yaml` | 141 | Zero — removes a line that unconditionally errors |
| A4. Guard `normalize_explobatch` with a runtime fMM check | `bench_shared.py` | 2374–2376 | Zero — raises NotImplementedError (clean SKIP), same as other unavailable methods |
| A5. Add pod startup log to PVC | `k8s/pod-ssh.yaml` | 59–60 | Zero — `tee` is additive; startup still runs normally |

All five changes are to two files. Fixes A1–A4 require a pod rebuild. Fix A5 is free since the pod is being rebuilt anyway.

---

## Fix A1 — Add `libpng-dev` and `zlib1g-dev` to step 2

### Why it is needed

The `png` R package (and its dependents, including `Hmisc` which is a dependency of `qsmooth`) uses `libpng` for C compilation. The build fails with:

```
/bin/bash: line 1: libpng-config: command not found
fatal error: png.h: No such file or directory
```

`libpng-dev` provides both `libpng-config` (the pkg-config wrapper) and `png.h` (the header). `zlib1g-dev` provides `zlib.h`, which is a transitive build dependency of several R packages that use HDF5-based I/O (including packages in the `Hmisc` → `htmlTable` → graphics chain).

Neither `png` nor `reticulate` are used directly by any normalization function in `bench_shared.py`. However, without `libpng-dev`, `Hmisc` (a dependency of `qsmooth`) may also fail to compile, which is the suspected indirect cause of the qsmooth installation failure (Fix A2 below).

### Exact change

**File:** `k8s/pod-ssh.yaml`  
**Line 76** (the `apt-get install -y -qq build-essential ...` line inside step 2):

**BEFORE:**
```yaml
        apt-get install -y -qq build-essential gfortran cmake libcurl4-openssl-dev libssl-dev libxml2-dev libhdf5-dev libblas-dev liblapack-dev libuv1-dev python3 python3-pip python3-dev python3-venv python3-full python-is-python3 git software-properties-common octave octave-statistics
```

**AFTER:**
```yaml
        apt-get install -y -qq build-essential gfortran cmake libcurl4-openssl-dev libssl-dev libxml2-dev libhdf5-dev libblas-dev liblapack-dev libuv1-dev libpng-dev zlib1g-dev python3 python3-pip python3-dev python3-venv python3-full python-is-python3 git software-properties-common octave octave-statistics
```

Two packages added in the middle of the existing list: `libpng-dev zlib1g-dev`. The line is otherwise identical.

---

## Fix A2 — Fix qsmooth installation

### Why it is needed

`BiocManager::install('qsmooth', ask=FALSE)` silently fails (the `&&` after it prevents `[startup] qsmooth OK` from printing, and the final `library(qsmooth)` at the end of step 5 confirms it is not installed). The most likely cause is that `Hmisc`, a CRAN dependency of qsmooth, fails to compile because `libpng-dev` is absent (the same missing header from Fix A1). Once Fix A1 is in place, `Hmisc` should compile correctly.

However, relying on `BiocManager::install` to resolve the full `Hmisc` + `quantreg` + `lme4` dependency chain in one shot is fragile: if any one package in the chain fails, the entire call exits and qsmooth is never reached. The fix installs qsmooth's CRAN dependencies explicitly in a separate call before attempting qsmooth itself, so failure is isolated and visible.

Additionally, `force=TRUE` is added to the qsmooth BiocManager call to ensure reinstallation even if a partial/corrupted installation from a previous pod run is cached.

### Exact change

**File:** `k8s/pod-ssh.yaml`  
**Line 123** (the `BiocManager::install('qsmooth', ...)` line):

**BEFORE** (one line):
```yaml
        Rscript --no-save --no-restore -e "BiocManager::install('qsmooth', ask=FALSE)"         && echo "[startup] qsmooth OK"
```

**AFTER** (two lines):
```yaml
        Rscript --no-save --no-restore -e "install.packages(c('quantreg','Hmisc','lme4'), dependencies=TRUE)" && echo "[startup] qsmooth CRAN deps OK"
        Rscript --no-save --no-restore -e "BiocManager::install('qsmooth', ask=FALSE, force=TRUE)"             && echo "[startup] qsmooth OK"
```

### What each new line does

| Line | Purpose |
|---|---|
| `install.packages(c('quantreg','Hmisc','lme4'), dependencies=TRUE)` | Pre-installs all three CRAN dependencies of qsmooth explicitly. Now that `libpng-dev` is present (Fix A1), `Hmisc` will compile correctly. Each package is installed under the same `dependencies=TRUE` flag, so their own sub-dependencies pull in automatically. The `&&` echo provides a visible confirmation line in the startup log. |
| `BiocManager::install('qsmooth', ask=FALSE, force=TRUE)` | Installs qsmooth from Bioconductor 3.22 with `force=TRUE` to ensure a clean install even if a stale partial installation exists. At this point all three CRAN deps are already present, so BiocManager only needs to install qsmooth's Bioconductor dependencies (primarily `preprocessCore`, which is already installed by FSQN). |

### Verification in the startup log

After this fix, both lines should appear:
```
[startup] qsmooth CRAN deps OK
[startup] qsmooth OK
```
And the final verification line should change from:
```
[startup] WARNING: FSQN or qsmooth verification failed - check logs above
```
to:
```
[startup] FSQN + qsmooth verified OK
```

---

## Fix A3 — Remove deleted `fMM` GitHub install

### Why it is needed

The GitHub repository `maxkuhn/fMM` returns HTTP 404 and has been permanently deleted. The install line always errors and cannot succeed regardless of any other fix:

```
Error: Failed to install 'unknown package' from GitHub:
  HTTP error 404. Not Found
  Did you spell the repo owner (maxkuhn) and repo name (fMM) correctly?
```

`fMM` is an internal dependency of `exploBATCH` (the `syspremed/exploBATCH` package). With fMM absent, `36_explobatch` will fail at runtime when it calls `library(exploBATCH)` or when exploBATCH internally calls fMM functions. Fix A4 below converts this into a clean SKIP at the Python level.

Removing the line eliminates noise from the startup log and removes a dead install call that slows down pod startup.

### Exact change

**File:** `k8s/pod-ssh.yaml`  
**Line 141** — delete this line entirely:

**BEFORE:**
```yaml
        Rscript --no-save --no-restore -e "remotes::install_github('maxkuhn/fMM', upgrade='never')" && echo "[startup] fMM OK"
```

**AFTER:** *(line deleted)*

No replacement. The line is removed without substitution.

---

## Fix A4 — Guard `normalize_explobatch` with a runtime fMM check

### Why it is needed

With fMM absent (Fix A3 removes the install attempt), calling `36_explobatch` will fail inside `ro.r(...)` when `library(exploBATCH)` is called and R discovers its dependency `fMM` is missing. This failure propagates to Python as an rpy2 exception that the dispatcher records as `status="failed"` — a hard failure, not a skip. A failed status inflates the failure count and creates misleading results in `metrics.csv`.

The correct behaviour is `status="skipped"` (same as permanently unavailable methods like `24_peer_k10`, `32_deepmnn`, `35_dasc`). To achieve this, we raise `NotImplementedError` at the top of `normalize_explobatch` using the same pattern already used in other unavailable methods.

The check uses R's `requireNamespace('fMM', quietly=TRUE)` so that the function works correctly if fMM is ever restored (e.g., if the repo reappears or a CRAN archive tarball is installed manually).

### Exact change

**File:** `bench_shared.py`  
**After line 2375** (the `import glob` line inside `normalize_explobatch`, after the docstring ends):

**BEFORE** (lines 2374–2376):
```python
    import tempfile
    import glob

```

**AFTER:**
```python
    import tempfile
    import glob

    _fmm_check = ro.r("requireNamespace('fMM', quietly=TRUE)")
    if _fmm_check is None or not bool(_fmm_check[0]):
        raise NotImplementedError(
            "fMM R package not available (GitHub repo maxkuhn/fMM deleted). "
            "exploBATCH depends on fMM at runtime; method is permanently unavailable "
            "until fMM is restored from a CRAN archive tarball."
        )

```

### Why `NotImplementedError` and not `RuntimeError`

The dispatcher in `run_one_job.py` catches `NotImplementedError` and records `status="skipped"` (not `"failed"`). A skip is the correct status for a method that is structurally unavailable — the same convention used for `24_peer_k10` (PEER removed), `32_deepmnn` (scRNA-seq only), and `35_dasc` (returns cluster labels, not expression). A `RuntimeError` would record `"failed"`, which is misleading.

### Consistency with other NotImplementedError guards

For reference, the existing pattern in bench_shared.py:

```python
# Example from normalize_fabatch (line 2463):
_bapred_check = ro.r("requireNamespace('bapred', quietly=TRUE)")
if _bapred_check is None or not bool(_bapred_check[0]):
    raise NotImplementedError(
        "bapred R package not installed. ..."
    )
```

Fix A4 follows the identical pattern.

---

## Fix A5 — Persist full startup log to PVC

### Why it is needed

The `kubectl logs` buffer holds a fixed number of lines. In the current pod startup, the first 20–25 minutes of log output (steps 1–4: SSH, system libs, Python venv, Posit R binary, pip install) are scrolled off before the capture window starts. This makes diagnosing failures in those steps impossible from `kubectl logs` alone.

The PVC at `/workspace` is mounted on the pod and persists across pod restarts. Redirecting the startup script's output to a file there preserves the complete log regardless of kubectl buffer limits.

### Exact change

**File:** `k8s/pod-ssh.yaml`  
**Lines 59–60** (the `command`/`args` block header):

**BEFORE:**
```yaml
    command: ["bash", "-c"]
    args:
      - |
        # -- 1. SSH ...
```

**AFTER:**
```yaml
    command: ["bash", "-c"]
    args:
      - |
        exec > >(tee -a /workspace/pod_startup.log) 2>&1
        # -- 1. SSH ...
```

The `exec > >(tee -a /workspace/pod_startup.log) 2>&1` line redirects all subsequent stdout and stderr from the startup script to both the terminal (so `kubectl logs` still works as before) and `/workspace/pod_startup.log` (persistent on the PVC). The `-a` flag appends rather than overwrites, so multiple pod restarts accumulate into one file (useful for comparison).

**Note:** `/workspace` is the PVC mount point. The PVC must exist before the pod starts (it is created once with `create_pvc.yaml` and persists indefinitely). If the pod starts before the PVC is bound, this line will fail silently — but that situation is not new; the PVC has been consistently available throughout this project.

### Usage after the fix

```bash
# Full startup log (all steps, including pip and Posit binary install):
kubectl exec fl-batch-correction -n ${K8S_NAMESPACE} -- cat /workspace/pod_startup.log

# Or via SSH after environment ready:
ssh fl-pod cat /workspace/pod_startup.log | less
```

---

## Deployment Sequence

### Step 1 — Apply all five changes to `pod-ssh.yaml` and `bench_shared.py`

Apply in the order listed above. All five changes are independent and can be applied in any order.

### Step 2 — Rebuild the pod

```bash
kubectl delete pod fl-batch-correction -n ${K8S_NAMESPACE}
kubectl apply -f harmonization-scripts/k8s/pod-ssh.yaml -n ${K8S_NAMESPACE}
```

### Step 3 — Watch startup log

```bash
kubectl logs -f fl-batch-correction -n ${K8S_NAMESPACE} | grep -E "\[startup\]|WARNING|ERROR|error:"
```

Expected milestones in order:
```
[startup] SSH ready - port-forward and connect now to watch progress
[startup] System libraries installed
[startup] Python venv created at /app/venv
[startup] R 4.5.3 installed from Posit binary
[startup] Python packages installed
[startup] Installing R packages - this takes 20-40 min...
[startup] missForest OK
[startup] softImpute OK
[startup] FSQN OK
[startup] qsmooth CRAN deps OK      ← new
[startup] qsmooth OK                ← new (was WARNING before)
...
[startup] DWDLargeR+huge OK
[startup] DBNorm OK
...
[startup] exploBATCH CRAN deps OK
                                    ← fMM line gone (Fix A3)
[startup] Procrustes cloned OK
[startup] FSQN + qsmooth verified OK  ← was WARNING before
[startup] R packages installed
[startup] Environment ready. Sync scripts with rsync and run.
```

### Step 4 — Sync bench_shared.py to the pod

```bash
rsync -avz -e "ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
    harmonization-scripts/bench_shared.py \
    root@localhost:/app/harmonization-scripts/bench_shared.py
```

(Port-forward must be active: `kubectl port-forward pod/fl-batch-correction 2222:22 -n ${K8S_NAMESPACE}`)

### Step 5 — Run smoke test

```bash
ssh fl-pod
cd /app/harmonization-scripts
python test_mock.py 2>&1 | tee /workspace/test_mock_after_option_a.txt
```

### Expected smoke test results after all five fixes

| Check | Expected result |
|---|---|
| R version printed at top | `R version 4.5.3` |
| `qsmooth` in R packages section | `OK` (was `MISSING`) |
| `bapred` in R packages section | `OK` (unchanged) |
| No `reComBat` in R packages section | absent (unchanged) |
| `36_explobatch` in normalization methods | `SKIP` (was `FAIL`) |
| `14_qsmooth` in normalization methods | `PASS` |
| `33_amdbnorm` | `PASS` (no segfault) |
| `27_dwd` | `PASS` (no penalty error) |
| All other methods | same as before |
| No segmentation fault anywhere | confirmed |

---

## To-Do List

### Code changes (before pod rebuild)

- [x] **pod-ssh.yaml line 76** — add `libpng-dev zlib1g-dev` to the step 2 apt-get install list (Fix A1)
- [x] **pod-ssh.yaml lines 59–60** — add `exec > >(tee -a /workspace/pod_startup.log) 2>&1` as first line of the startup script (Fix A5)
- [x] **pod-ssh.yaml line 123** — replace single qsmooth BiocManager line with two-line explicit deps + force install (Fix A2)
- [x] **pod-ssh.yaml line 141** — delete the `remotes::install_github('maxkuhn/fMM', ...)` line (Fix A3)
- [x] **bench_shared.py after line 2375** — add fMM `requireNamespace` check + `NotImplementedError` (Fix A4)

### Pod rebuild and validation

- [ ] Delete and re-apply pod manifest
- [ ] In startup log, confirm `[startup] qsmooth CRAN deps OK` and `[startup] qsmooth OK` both appear
- [ ] In startup log, confirm no `[startup] fMM OK` line (expected — line was deleted)
- [ ] In startup log, confirm `[startup] FSQN + qsmooth verified OK` (not WARNING)
- [ ] In startup log, confirm `[startup] Environment ready.`
- [ ] Confirm `/workspace/pod_startup.log` is written and contains steps 1–4 output
- [ ] Sync `bench_shared.py` to the pod via rsync
- [ ] Run `python test_mock.py` and save output to `/workspace/test_mock_after_option_a.txt`
- [ ] Verify `14_qsmooth` shows `PASS`
- [ ] Verify `36_explobatch` shows `SKIP` (not `FAIL`)
- [ ] Verify no segmentation fault
- [ ] Verify no `DWD failed for batch ... penalty` messages

### Documentation (after validation)

- [x] Add rows for A1–A4 to `k8s/CLAUDE.md` Known Startup Failures table
- [x] Update `harmonization-scripts/CLAUDE.md` Known Startup Failures table (qsmooth + fMM rows)
- [x] Update `k8s/README.md` troubleshooting section
