# Python 3.11 Transition Plan

**Date:** 2026-05-10  
**Status:** Pending implementation  
**Addresses:** `ModuleNotFoundError: No module named 'numpy'` — pip install fails entirely because of a pandas version conflict caused by reComBat

---

## Problem Statement

The pod runs Python 3.12 (Ubuntu 24.04 default). The pip install step fails completely, so no packages (numpy, pandas, rpy2, boto3…) are installed into the venv. This is not a missing-package error — it is a dependency resolution error that aborts the entire `pip install -r requirements.txt` run before it writes a single file.

### Root cause chain

1. Ubuntu 24.04 provides Python 3.12 as the system default
2. Step 2.5 runs `python3 -m venv /app/venv` → creates a **Python 3.12** venv
3. Step 4 runs `pip install -r /etc/fl-deps/requirements.txt` inside that venv
4. ConfigMap specifies `pandas>=2.0,<3.0`
5. `reComBat 0.1.4` (the GitHub URL in requirements.txt resolves to this version) declares `pandas>=1.3.4,<2.0.0`
6. pip cannot satisfy both constraints → `ResolutionImpossible` → entire install aborted
7. `test_mock.py` → `ModuleNotFoundError: No module named 'numpy'` (numpy was never installed)

### Why forcing pandas<2.0 on Python 3.12 also fails

Daniil tested this manually: changing the constraint to `pandas>=1.3.4,<2.0.0` on Python 3.12 fails at the wheel-build stage:

```
ModuleNotFoundError: No module named 'pkg_resources'
```

Pandas 1.5.3 has **no pre-built wheel for Python 3.12** (`cp312`). pip falls back to a source build, which requires the legacy `pkg_resources` from setuptools. Installing setuptools does not fix this — pandas 1.5.3's `setup.py` uses Cython 0.x macros that are incompatible with Python 3.12's C API changes. The source build cannot succeed on Python 3.12 regardless of setuptools version.

### Why Python 3.11 solves this

Pandas 1.5.3 ships an official pre-built wheel for Python 3.11:

```
pandas-1.5.3-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

With a Python 3.11 venv, pip downloads this binary wheel directly — no source compilation, no Cython, no `pkg_resources` needed. All other required packages (numpy 1.26.4, scikit-learn 1.5.2, rpy2 3.6.7, harmonypy, scanorama) also have Python 3.11 pre-built wheels or build cleanly on Python 3.11.

---

## Important: Two requirements.txt files

There are two separate files named `requirements.txt`. Only one is used by the startup script:

| File | Used by | How to update |
|---|---|---|
| `/app/harmonization-scripts/requirements.txt` | Manual `pip install` on pod, repo reference | Edit on JupyterHub or rsync |
| ConfigMap in `pod-ssh.yaml` (lines 20–39) | **Pod startup script** (`/etc/fl-deps/requirements.txt`) | Edit `pod-ssh.yaml` and rebuild pod |

Daniil's manual `nano requirements.txt` edit on the pod affected only the first file. After a pod restart, pip re-reads from the ConfigMap version. **All fixes below target `pod-ssh.yaml`.**

---

## Alternative (Option B): stay on Python 3.12, switch reComBat to PyPI

Instead of switching Python versions, replace the GitHub URL with the PyPI `reComBat>=0.3` package, which is a different, maintained release that supports pandas>=2.0 and Python 3.12:

```
# Instead of: git+https://github.com/BorgwardtLab/reComBat
reComBat>=0.3
```

**Pros:** No Python version change, no pandas downgrade, simpler change (one line).  
**Cons:** PyPI `reComBat>=0.3` is a different codebase from the GitHub version. The API may differ; `normalize_recombat` in `bench_shared.py` would need to be verified against it.

The plan below documents **Option A (Python 3.11)** as requested.

---

## Changes Overview

| Fix | File | Section | Risk |
|---|---|---|---|
| P1. Add `python3.11` packages to apt install | `k8s/pod-ssh.yaml` | Step 2 (line 77) | Zero — additive |
| P2. Create venv with `python3.11` | `k8s/pod-ssh.yaml` | Step 2.5 (line 84) | Zero |
| P3. Pre-install `setuptools wheel` before requirements | `k8s/pod-ssh.yaml` | Step 4 (line 107) | Zero — additive |
| P4. Update pandas constraint in ConfigMap | `k8s/pod-ssh.yaml` | ConfigMap (line 29) | Low — see Risks |

All four changes are to one file. Requires a pod rebuild.

---

## Fix P1 — Add `python3.11`, `python3.11-venv`, `python3.11-dev` to step 2

### Why

Ubuntu 24.04's `universe` repository ships Python 3.11 alongside the default Python 3.12. Installing these three packages makes `python3.11` available as a command and enables creating a 3.11 venv.

The existing `python3`, `python3-pip`, etc. packages are kept for system compatibility. Only the project venv (step 2.5) will switch to 3.11.

### Exact change

**File:** `k8s/pod-ssh.yaml`  
**Line 77** (step 2 apt-get install line):

**BEFORE:**
```yaml
        apt-get install -y -qq build-essential gfortran cmake libcurl4-openssl-dev libssl-dev libxml2-dev libhdf5-dev libblas-dev liblapack-dev libuv1-dev libpng-dev zlib1g-dev python3 python3-pip python3-dev python3-venv python3-full python-is-python3 git software-properties-common octave octave-statistics
```

**AFTER:**
```yaml
        apt-get install -y -qq build-essential gfortran cmake libcurl4-openssl-dev libssl-dev libxml2-dev libhdf5-dev libblas-dev liblapack-dev libuv1-dev libpng-dev zlib1g-dev python3 python3-pip python3-dev python3-venv python3-full python-is-python3 python3.11 python3.11-venv python3.11-dev git software-properties-common octave octave-statistics
```

Three packages added: `python3.11 python3.11-venv python3.11-dev`.

---

## Fix P2 — Create venv with python3.11

### Why

The venv creation command determines which Python interpreter is embedded in `/app/venv`. Changing `python3` to `python3.11` makes all subsequent pip operations (step 4) target Python 3.11, which has pre-built wheels for pandas 1.5.x, numpy 1.x, scikit-learn 1.5.x, and rpy2 3.6.x.

### Exact change

**File:** `k8s/pod-ssh.yaml`  
**Line 84** (step 2.5):

**BEFORE:**
```yaml
        python3 -m venv /app/venv
```

**AFTER:**
```yaml
        python3.11 -m venv /app/venv
```

---

## Fix P3 — Pre-install `setuptools` and `wheel` before requirements

### Why

Several packages in requirements.txt use legacy `setup.py`-based builds (reComBat 0.1.4, `fbpca`, `fire`). These builds import `pkg_resources` from setuptools. A fresh Python 3.11 venv created by `python3.11 -m venv` does not include setuptools by default (PEP 668 behavior). Pre-installing it ensures that the small number of source-built packages can complete their wheel builds without `ModuleNotFoundError: No module named 'pkg_resources'`.

### Exact change

**File:** `k8s/pod-ssh.yaml`  
**Line 107** (step 4, pip install):

**BEFORE:**
```yaml
        /app/venv/bin/pip install --no-cache-dir -r /etc/fl-deps/requirements.txt
        echo "[startup] Python packages installed"
```

**AFTER:**
```yaml
        /app/venv/bin/pip install --no-cache-dir setuptools wheel
        /app/venv/bin/pip install --no-cache-dir -r /etc/fl-deps/requirements.txt
        echo "[startup] Python packages installed"
```

---

## Fix P4 — Update pandas constraint in ConfigMap

### Why

`reComBat 0.1.4` (from `git+https://github.com/BorgwardtLab/reComBat`) requires `pandas>=1.3.4,<2.0.0`. The current ConfigMap specifies `pandas>=2.0,<3.0`. These constraints are mutually exclusive; pip rejects the entire install. Changing the constraint to match reComBat's requirement resolves the conflict. With Python 3.11, `pandas-1.5.3-cp311-cp311-manylinux*.whl` installs from a binary wheel.

### Exact change

**File:** `k8s/pod-ssh.yaml`  
**ConfigMap `fl-deps`** (line 29):

**BEFORE:**
```yaml
    pandas>=2.0,<3.0
```

**AFTER:**
```yaml
    pandas>=1.3.4,<2.0.0
```

The requirements.txt file in the repo (`harmonization-scripts/requirements.txt`) should be updated to match for consistency — but it does not affect pod startup.

---

## Risks and Mitigations

### Risk 1 — pandas 2.x APIs in bench_shared.py (Low)

`bench_shared.py` is ~3,000 lines. If any code uses APIs renamed in pandas 2.0 (e.g., `DataFrame.applymap()` → `DataFrame.map()`, `Index.is_monotonic` → `Index.is_monotonic_increasing`), those calls will fail with pandas 1.5.3.

**Assessment:** Low risk. The codebase predates pandas 2.0 and uses standard indexing, `.loc`, `.groupby`, `.merge`, and column assignment throughout. No 2.0-specific APIs were introduced in this project. `test_mock.py` will surface any breakage immediately on a synthetic dataset.

**Mitigation:** Run `test_mock.py` immediately after install and before any benchmark run.

### Risk 2 — `python3.11` not in ubuntu:24.04 universe (Very Low)

If the `universe` apt repository is not enabled in the base image, `apt-get install python3.11` will report "package not found".

**Assessment:** Very low. The `ubuntu:24.04` Docker image ships with universe enabled. Python 3.11 is confirmed present in Noble's universe repo.

**Fallback:** Add `add-apt-repository universe -y && apt-get update -qq` before the step 2 apt-get install, or switch to `ppa:deadsnakes/ppa` (requires `software-properties-common`, which is already in the apt list). If either fallback is needed, it will be visible in the startup log as `E: Unable to locate package python3.11`.

### Risk 3 — `harmonypy 2.0.0` requires pandas>=2.0 (Medium)

`harmonypy>=0.0.9` resolved to version 2.0.0 in the previous pod run. If harmonypy 2.0.0 declares `pandas>=2.0` as a requirement, pip will again report a conflict.

**Assessment:** Medium risk. harmonypy 2.0.0 is a relatively new release. If it conflicts, the fix is to pin `harmonypy>=0.0.9,<2.0` in the ConfigMap requirements.txt to get harmonypy 0.0.9 which was written against older pandas.

**Detection:** pip will print the conflict during step 4. If step 4 fails and the log shows harmonypy as the source, apply the pin and rebuild.

### Risk 4 — `inmoose 0.9.1` source build with Python 3.11 (Low)

`inmoose` builds partially from source. With setuptools pre-installed (Fix P3) and Python 3.11, most source builds succeed. If inmoose has issues, it will appear as a build error in the startup log for step 4.

**Mitigation:** `inmoose` is used only for `normalize_inmoose_combat_seq` (`08_inmoose_combatseq`). If it fails to install, that method will raise `ImportError` and record `status="failed"` in the benchmark — acceptable, since it is a low-priority method.

---

## Deployment Sequence

### Step 1 — Apply all four changes to `pod-ssh.yaml`
All changes are independent and can be applied in any order.

### Step 2 — Rebuild the pod
```bash
kubectl delete pod fl-batch-correction -n ${K8S_NAMESPACE}
kubectl apply -f harmonization-scripts/k8s/pod-ssh.yaml -n ${K8S_NAMESPACE}
```

### Step 3 — Watch startup log, focus on step 4
```bash
kubectl logs -f fl-batch-correction -n ${K8S_NAMESPACE} | grep -E "\[startup\]|ERROR|error:|Conflict|ResolutionImpossible"
```

Expected new output in step 4:
```
[startup] Python packages installed          ← now prints (was silent before)
```

### Step 4 — Verify Python version in the venv
```bash
ssh fl-pod
python --version    # should print: Python 3.11.x
python -c "import numpy, pandas, rpy2, boto3; print('pandas', pandas.__version__); print('OK')"
# Expected: pandas 1.5.3 ... OK
```

### Step 5 — Run smoke test
```bash
cd /app/harmonization-scripts
python test_mock.py 2>&1 | tee /workspace/test_mock_after_python311.txt
```

---

## Expected Smoke Test Results After All Fixes

| Check | Expected |
|---|---|
| `python --version` | `Python 3.11.x` |
| `pandas.__version__` | `1.5.3` |
| All imports (numpy, rpy2, boto3, harmonypy) | no ImportError |
| `14_qsmooth` | `PASS` |
| `36_explobatch` | `SKIP` |
| `08_inmoose_combatseq` | `PASS` (or `SKIP` if inmoose source build failed) |
| `30_recombat` | `PASS` |
| No segmentation fault | confirmed |

---

## To-Do List

### Code changes (before pod rebuild)

- [x] **pod-ssh.yaml line 77** — add `python3.11 python3.11-venv python3.11-dev` to step 2 apt list (Fix P1)
- [x] **pod-ssh.yaml line 84** — change `python3 -m venv /app/venv` to `python3.11 -m venv /app/venv` (Fix P2)
- [x] **pod-ssh.yaml line 107** — add `pip install setuptools wheel` before requirements install (Fix P3)
- [x] **pod-ssh.yaml ConfigMap line 29** — change `pandas>=2.0,<3.0` to `pandas>=1.3.4,<2.0.0` (Fix P4)
- [x] **harmonization-scripts/requirements.txt** — update pandas constraint to `pandas>=1.3.4,<2.0.0` for consistency with ConfigMap

### Pod rebuild and validation

- [ ] Delete and re-apply pod manifest
- [ ] In startup log, confirm `[startup] Python packages installed` appears (was absent before)
- [ ] In startup log, confirm no `ResolutionImpossible` or `Conflict` errors in step 4
- [ ] Connect via SSH; confirm `python --version` reports `3.11.x`
- [ ] Confirm `python -c "import numpy, pandas, rpy2, boto3"` runs without ImportError
- [ ] Confirm `pandas.__version__` is `1.5.3`
- [ ] Sync `bench_shared.py` to the pod via rsync
- [ ] Run `python test_mock.py` and save output to `/workspace/test_mock_after_python311.txt`
- [ ] Verify `30_recombat` shows `PASS`
- [ ] Verify `14_qsmooth` shows `PASS`
- [ ] Verify `36_explobatch` shows `SKIP`
- [ ] Verify no segmentation fault

### Documentation (after validation)

- [x] Add new row to `k8s/CLAUDE.md` Known Startup Failures table (Python 3.12 / pandas conflict)
- [x] Add new row to `harmonization-scripts/CLAUDE.md` Known Startup Failures table
- [x] Update `harmonization-scripts/CLAUDE.md` Python virtual environment description to note Python 3.11 requirement and reason
