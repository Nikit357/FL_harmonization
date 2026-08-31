# Implementation Plan: Fixes 1–3 (segfault, DWD, smoke-test)

**Based on:** `core_dumped_crash_research.md`  
**Status:** Implemented 2026-05-10  
**Date:** 2026-05-10

---

## Overview

| Fix | File(s) | Lines changed | Risk |
|---|---|---|---|
| 1a. Pin R 4.5.x in pod startup | `k8s/pod-ssh.yaml` | 83–88 (step 3 block) | Low |
| 1b. Sync ConfigMap requirements.txt | `k8s/pod-ssh.yaml` | 20–33 (ConfigMap block) | Zero |
| 2. Remove `penalty = "auto"` from DWD | `bench_shared.py` | 1843 | Zero |
| 3. Fix wrong R package names in smoke test | `test_mock.py` | 50–51 | Zero |

Fixes 2, 3 are one-line changes. Fix 1 is the only one that touches the pod manifest and requires a pod rebuild to validate.

---

## Fix 1a — Pin R to 4.5.x in `k8s/pod-ssh.yaml`

### Why it is needed

The `noble-cran40` CRAN apt repository now serves R 4.6.0 (released 2026-04-24). rpy2 3.6.7 has C-level incompatibility with R 4.6.0's changed PROTECT/GC internals, causing a segfault in `33_amdbnorm`. Installing R 4.5.x explicitly restores the tested environment without any changes to bench_shared.py.

### Strategy

Use `apt-cache madison r-base` to dynamically find the exact Debian version string for R 4.5.x in the CRAN Noble apt repository, then install that specific version and hold it with `apt-mark hold` to prevent future upgrades. A fallback branch installs the latest version if 4.5.x is no longer in the repo cache (prints a visible warning).

The CRAN Noble repo typically keeps the previous minor release alongside the current one. R 4.5.3 should still be present as of the date of this document.

### Exact change

**File:** `k8s/pod-ssh.yaml`  
**Lines 83–88** (the `# -- 3. R ...` block inside the `args` startup script):

**BEFORE:**
```yaml
        # -- 3. R 4.5 from CRAN noble-cran40 repo --
        wget -qO- https://cloud.r-project.org/bin/linux/ubuntu/marutter_pubkey.asc | gpg --dearmor -o /usr/share/keyrings/r-project.gpg
        echo "deb [signed-by=/usr/share/keyrings/r-project.gpg] https://cloud.r-project.org/bin/linux/ubuntu noble-cran40/" > /etc/apt/sources.list.d/r-project.list
        apt-get update -qq
        apt-get install -y r-base r-base-dev
        echo "[startup] R installed"
```

**AFTER:**
```yaml
        # -- 3. R 4.5.x from CRAN noble-cran40 repo (pinned: rpy2 3.6.x is incompatible with R 4.6.0) --
        wget -qO- https://cloud.r-project.org/bin/linux/ubuntu/marutter_pubkey.asc | gpg --dearmor -o /usr/share/keyrings/r-project.gpg
        echo "deb [signed-by=/usr/share/keyrings/r-project.gpg] https://cloud.r-project.org/bin/linux/ubuntu noble-cran40/" > /etc/apt/sources.list.d/r-project.list
        apt-get update -qq
        R45_VER=$(apt-cache madison r-base | awk -F'|' '/4\.5\./{gsub(/ /,""); print $2; exit}')
        if [ -n "$R45_VER" ]; then
            apt-get install -y r-base="$R45_VER" r-base-dev="$R45_VER"
            apt-mark hold r-base r-base-dev r-base-core
            echo "[startup] R $R45_VER installed and held at 4.5.x"
        else
            echo "[startup] WARNING: R 4.5.x not found in apt cache — installing latest (verify rpy2 compatibility)"
            apt-get install -y r-base r-base-dev
        fi
        echo "[startup] R installed"
```

### What each new line does

| Line | Purpose |
|---|---|
| `apt-cache madison r-base \| awk -F'\|' '/4\.5\./{...}'` | Lists all available versions of r-base from all configured repos; filters the first 4.5.x line; strips spaces and extracts the version string (e.g. `4.5.3-1.2404.0`) |
| `if [ -n "$R45_VER" ]` | Guards against the fallback; if the grep found nothing, the variable is empty |
| `apt-get install -y r-base="$R45_VER" r-base-dev="$R45_VER"` | Installs exactly the 4.5.x version by its full Debian version string — prevents apt from pulling 4.6.0 |
| `apt-mark hold r-base r-base-dev r-base-core` | Freezes all three R base packages so a later `apt-get upgrade` inside the pod does not silently overwrite the version |
| fallback `else` branch | Prints a conspicuous WARNING and installs whatever is available; the pod will likely crash again but at least it is visible and auditable from the startup logs |

### Verification inside the pod (run after applying)

```bash
Rscript --no-save --no-restore -e "cat(R.version$version.string, '\n')"
# Must print: R version 4.5.3 (2026-02-28) or similar 4.5.x string
```

---

## Fix 1b — Sync ConfigMap requirements.txt in `k8s/pod-ssh.yaml`

### Why it is needed

The ConfigMap block `fl-deps` inside `pod-ssh.yaml` embeds a copy of `requirements.txt`. The repo file was updated (user changed `reComBat>=0.3` to `git+https://github.com/BorgwardtLab/reComBat` and added upper-bound pins for numpy/pandas/scikit-learn). The ConfigMap copy is out of sync; without this fix the pod will install the old PyPI `reComBat 0.3.x` which fails due to numpy ABI conflicts.

### Exact change

**File:** `k8s/pod-ssh.yaml`  
**Lines 20–33** (the `requirements.txt:` data block inside `fl-deps` ConfigMap):

**BEFORE:**
```yaml
  requirements.txt: |
    boto3>=1.28.17
    botocore>=1.31.17
    pandas>=2.0
    numpy>=1.24
    scikit-learn>=1.3
    rpy2>=3.5.5
    harmonypy>=0.0.9
    scanorama>=1.7
    combat>=0.3.3
    inmoose>=0.9.1
    psutil>=5.9
    awscli>=1.29
    reComBat>=0.3
```

**AFTER** (mirrors repo `requirements.txt` exactly, preserving YAML indentation):
```yaml
  requirements.txt: |
    # Cloud & Core
    boto3>=1.28.17
    botocore>=1.31.17
    awscli>=1.29
    psutil>=5.9

    # Science Stack (Pinned to avoid NumPy 2.x breaks)
    numpy>=1.24,<2.0
    pandas>=2.0,<3.0
    scikit-learn>=1.3,<1.6
    rpy2>=3.5.5

    # Batch Correction & Harmony
    harmonypy>=0.0.9
    scanorama>=1.7
    combat>=0.3.3
    inmoose>=0.9.1

    git+https://github.com/BorgwardtLab/reComBat
```

**YAML indentation note:** Every content line inside a block scalar (`|`) in YAML must be indented consistently relative to the key. The current indentation uses 4 spaces. Keep this — do not change indentation depth.

### What changed

| Package | Old value | New value | Reason |
|---|---|---|---|
| `numpy` | `>=1.24` | `>=1.24,<2.0` | Pin upper bound to avoid NumPy 2.0 ABI breaks |
| `pandas` | `>=2.0` | `>=2.0,<3.0` | Defensive upper bound |
| `scikit-learn` | `>=1.3` | `>=1.3,<1.6` | Defensive upper bound |
| `reComBat` | `reComBat>=0.3` | `git+https://github.com/BorgwardtLab/reComBat` | PyPI 0.3.x has numpy ABI conflict; git install builds from source against current headers |

---

## Fix 2 — Remove `penalty = "auto"` from `normalize_dwd`

### Why it is needed

`DWDLargeR::genDWD` removed the `penalty` parameter in a recent CRAN release. The call currently passes `penalty = "auto"` which R rejects with "unused argument". The `tryCatch` handler catches this per-batch — no crash — but both non-reference batches return uncorrected, making `27_dwd` produce identity output silently. The fix removes the dead argument; `genDWD` selects the penalty automatically by default.

### Exact change

**File:** `bench_shared.py`  
**Line 1843:**

**BEFORE:**
```python
                    sol <- genDWD(X = X_combined, y = y, penalty = "auto")
```

**AFTER:**
```python
                    sol <- genDWD(X = X_combined, y = y)
```

This is a single token removal inside an `ro.r(f"""...""")` string. No Python logic changes; no function signature changes.

### Verification (inside the pod, after the pod has R packages installed)

```bash
python run_one_job.py \
    --strat A_confirmed_bad --imp strict --method 27_dwd \
    --out-json /tmp/dwd_test.json
cat /tmp/dwd_test.json
# Expect status "ok", not "failed"; and r2_batch < 0.95 (some correction applied)
```

Or in the smoke test log, no line containing `"DWD failed for batch"` should appear.

---

## Fix 3 — Correct wrong R package names in `test_mock.py`

### Why it is needed

`_CRITICAL_PKGS` at lines 46–52 lists R package names for `library()` smoke-checks. Two entries are wrong:

- `"reComBat"` — there is no R package with this name. `normalize_recombat` (`30_recombat`) uses the **Python** package `reComBat`. Including it here always prints `MISSING`, creating false alarm noise that obscures real missing packages.
- `"FAbatch"` — there is no R package with this name. `normalize_fabatch` (`37_fabatch`) calls `library(bapred)`; `batchadjust()` is exported by the `bapred` package. The smoke test should check `"bapred"` to verify the actual dependency.

`"DASC"` is left in place — `normalize_dasc` always raises `NotImplementedError` (DASC returns cluster labels not corrected expression), so DASC MISSING is a correct and expected result; removing it from the list would lose visibility if someone tries to fix it in future.

### Exact change

**File:** `test_mock.py`  
**Lines 50–51:**

**BEFORE:**
```python
    "DWDLargeR", "huge", "DBNorm", "reComBat", "AMDBNorm",
    "DASC", "exploBATCH", "ruv", "NOISeq", "FAbatch", "Harman",
```

**AFTER:**
```python
    "DWDLargeR", "huge", "DBNorm", "AMDBNorm",
    "DASC", "exploBATCH", "ruv", "NOISeq", "bapred", "Harman",
```

Changes: `"reComBat"` removed entirely; `"FAbatch"` replaced by `"bapred"`.

### Expected smoke test output after the fix

```
    bapred               OK        # was: FAbatch MISSING
```
`reComBat` line disappears from the R packages section entirely (correct — it is a Python package).

---

## Deployment sequence

Fixes 2 and 3 can be committed immediately and tested locally. Fix 1 requires a pod rebuild.

### Step-by-step

1. Apply fixes 2 and 3 to `bench_shared.py` and `test_mock.py` in the repo.
2. Apply fixes 1a and 1b to `k8s/pod-ssh.yaml`.
3. Sync changes to the pod using rsync (for fixes 2 and 3 only — no pod restart needed):
   ```bash
   rsync -avz -e "ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
       ~/fl_subset/harmonization-scripts/bench_shared.py \
       ~/fl_subset/harmonization-scripts/test_mock.py \
       root@localhost:/app/harmonization-scripts/
   ```
4. Delete the current pod (pod must be restarted for fix 1 to take effect):
   ```bash
   kubectl delete pod fl-batch-correction -n ${K8S_NAMESPACE}
   ```
5. Apply the updated manifest:
   ```bash
   kubectl apply -f harmonization-scripts/k8s/pod-ssh.yaml -n ${K8S_NAMESPACE}
   ```
6. Wait for `[startup] R 4.5.x installed and held` in the startup log:
   ```bash
   kubectl logs -f fl-batch-correction -n ${K8S_NAMESPACE} | grep -E "\[startup\]|WARNING"
   ```
7. After `[startup] Environment ready.`, connect and run the full smoke test:
   ```bash
   ssh fl-pod
   cd /app/harmonization-scripts
   python test_mock.py 2>&1 | tee /workspace/test_mock_after_fix.txt
   ```
8. Confirm:
   - No `Segmentation fault` line in output
   - No `DWD failed for batch ... penalty` lines in output
   - `bapred OK` instead of `FAbatch MISSING`
   - No `reComBat MISSING` in the R packages section

---

## To-do list

### Immediate (before pod rebuild)

- [x] **bench_shared.py line 1843** — remove `, penalty = "auto"` from the `genDWD(...)` call inside `normalize_dwd`
- [x] **test_mock.py line 50** — remove `"reComBat"` from `_CRITICAL_PKGS`
- [x] **test_mock.py line 51** — replace `"FAbatch"` with `"bapred"` in `_CRITICAL_PKGS`

### Pod manifest changes (require pod restart)

- [x] **pod-ssh.yaml lines 83–88** — replace the 2-line `apt-get install -y r-base r-base-dev` block with the 8-line dynamic R 4.5.x detection and hold block (Fix 1a above)
- [x] **pod-ssh.yaml lines 20–33** — replace the ConfigMap `requirements.txt` block with the version matching the repo's `requirements.txt` exactly (Fix 1b above)
- [x] Verify the YAML indentation of the ConfigMap block is consistent (4-space indent for all content lines) — malformed YAML will be rejected by `kubectl apply`

### Deployment and validation

- [ ] Rsync `bench_shared.py` and `test_mock.py` to the currently-running pod (for testing fixes 2 and 3 independently if the pod is still alive)
- [ ] Delete and re-apply the pod manifest with the new startup script
- [ ] In the startup log, confirm the line `[startup] R 4.5.x installed and held` appears (not the WARNING fallback)
- [ ] After `[startup] Environment ready.`, run `python test_mock.py` and confirm:
  - [ ] No segmentation fault
  - [ ] No `DWD failed for batch ... penalty` messages
  - [ ] `bapred OK` in the R packages section
  - [ ] All previously-passing methods still pass
- [ ] Save `test_mock.py` output to `/workspace/test_mock_after_fix.txt` for the record

### Documentation (after validation)

- [x] Update `k8s/CLAUDE.md` — added 3 rows to Known Startup Failures: segfault/R 4.6.0, DWD penalty, reComBat/FAbatch false alarms
- [x] Update `harmonization-scripts/CLAUDE.md` — added R version requirement paragraph; added segfault and DWD rows to startup failures table
- [x] Update `k8s/README.md` — added "R version check" troubleshooting section with diagnosis steps, verification command, and fallback guidance; added segfault and DWD rows to quick reference table

---

## Fix 4 — R installation broken: `r-recommended` dependency conflict

**Status:** Discovered 2026-05-10 (pod launch after Fix 1a–1b deployment)

### Root cause

The `apt-cache madison` approach from Fix 1a finds `r-base=4.5.3-1.2404.0` in the noble-cran40 repo (the .deb file is still present) but **cannot install it**. The Debian package `r-base` 4.5.3 carries:

```
Depends: r-recommended (= 4.5.3-1.2404.0)
```

This is an **exact-version** dependency. When CRAN released R 4.6.0, the noble-cran40 apt repo removed `r-recommended=4.5.3-1.2404.0` (the old helper package) while keeping only `r-recommended=4.6.0-2.2404.0`. The `apt-get install r-base=4.5.3-1.2404.0` call therefore fails with:

```
r-base : Depends: r-recommended (= 4.5.3-1.2404.0) but 4.6.0-2.2404.0 is to be installed
E: Unable to correct problems, you have held broken packages.
```

The `if [ -n "$R45_VER" ]` guard in Fix 1a passes (the version string is non-empty) but the inner `apt-get install` exits non-zero. Because the startup script has no `set -e` and the `if` block does not propagate the exit code, execution continues normally. All subsequent echo statements print as if R were installed.

### Secondary consequences (cascade failure)

1. **`apt-mark hold` is a no-op.** R was never installed, so the hold marks a phantom package entry with no effect.
2. **`pip install rpy2` fails.** The rpy2 ≥ 3.6.x build requires `R` in PATH (it runs `R RHOME` to locate R headers for the C extension). With R absent the pip build errors out:
   ```
   Error: rpy2 in API mode cannot be built without R in the PATH or R_HOME defined.
   Unable to determine R home: [Errno 2] No such file or directory: 'R'
   ```
3. **All step 5 `Rscript` invocations fail** with `bash: Rscript: command not found`. Every R package install silently does nothing; the `echo "[startup] ... OK"` lines after each `&&` are skipped, but because step 5 as a whole has no exit guard the startup continues to `sleep infinity`.
4. The pod reaches `[startup] Environment ready.` and starts SSH without R, rpy2, or any R packages being present. `test_mock.py` would fail immediately on `import rpy2`.

### Why Fix 1a's `apt-cache madison` approach cannot be salvaged

It would be necessary to also find and install the exact matching `r-recommended` and `r-base-core` packages from the old repo — and those are not in the repo at all. CRAN deliberately removes them to prevent installation of the old dependency chain. There is no `--fix-broken` flag that can resolve a missing-from-repo package.

### Solution: Posit standalone R binary (Option A — Recommended)

Posit (formerly RStudio) publishes standalone self-contained `.deb` files for specific R versions at:

```
https://cdn.posit.co/r/ubuntu-2404/pkgs/r-X.Y.Z_1_amd64.deb
```

These files install R to `/opt/R/X.Y.Z/` and carry **no dependency on the CRAN apt repo at all** — they bundle their own `r-base-core` equivalent. The only external dependencies are standard Ubuntu shared libraries (`libc6`, `libgcc-s1`, `libgomp1`, etc.) which are already present on `ubuntu:24.04`. Installing with `apt-get install -f` after `dpkg -i` fixes any missing shared-lib deps automatically.

This approach:
- Encodes the exact version in the URL — no ambiguity, no apt resolution
- Cannot be broken by CRAN repo housekeeping
- Persists across future apt upgrades (the binary lives in `/opt/R/`, not `/usr/`)
- Is the standard method used by Posit's own Docker images and GitHub Actions

### Exact change to `k8s/pod-ssh.yaml`

**File:** `k8s/pod-ssh.yaml`  
**Replace the entire `# -- 3. R ...` block** (lines 89–104 in the current file):

**BEFORE** (the broken apt-pin approach from Fix 1a):
```yaml
        # -- 3. R 4.5.x from CRAN noble-cran40 repo (pinned: rpy2 3.6.x is incompatible with R 4.6.0) --
        wget -qO- https://cloud.r-project.org/bin/linux/ubuntu/marutter_pubkey.asc | gpg --dearmor -o /usr/share/keyrings/r-project.gpg
        echo "deb [signed-by=/usr/share/keyrings/r-project.gpg] https://cloud.r-project.org/bin/linux/ubuntu noble-cran40/" > /etc/apt/sources.list.d/r-project.list
        apt-get update -qq
        R45_VER=$(apt-cache madison r-base | awk -F'|' '/4\.5\./{gsub(/ /,""); print $2; exit}')
        if [ -n "$R45_VER" ]; then
            apt-get install -y r-base="$R45_VER" r-base-dev="$R45_VER"
            apt-mark hold r-base r-base-dev r-base-core
            echo "[startup] R $R45_VER installed and held at 4.5.x"
        else
            echo "[startup] WARNING: R 4.5.x not found in apt cache — installing latest (verify rpy2 compatibility)"
            apt-get install -y r-base r-base-dev
        fi
        echo "[startup] R installed"
        echo 'export R_HOME=/usr/lib/R' >> /root/.bashrc
        echo 'export R_HOME=/usr/lib/R' >> /root/.profile
```

**AFTER** (Posit standalone binary):
```yaml
        # -- 3. R 4.5.3 from Posit standalone binary (bypasses CRAN apt dependency chain) --
        # Posit bundles a self-contained .deb that installs to /opt/R/4.5.3/ with no CRAN apt deps.
        # This is immune to CRAN repo housekeeping (r-recommended removal when 4.6.0 shipped).
        wget -q "https://cdn.posit.co/r/ubuntu-2404/pkgs/r-4.5.3_1_amd64.deb" -O /tmp/r-4.5.3.deb
        dpkg -i /tmp/r-4.5.3.deb || apt-get install -f -y
        rm /tmp/r-4.5.3.deb
        export PATH="/opt/R/4.5.3/bin:$PATH"
        export R_HOME="/opt/R/4.5.3/lib/R"
        echo 'export PATH="/opt/R/4.5.3/bin:$PATH"' >> /root/.bashrc
        echo 'export PATH="/opt/R/4.5.3/bin:$PATH"' >> /root/.profile
        echo 'export R_HOME="/opt/R/4.5.3/lib/R"' >> /root/.bashrc
        echo 'export R_HOME="/opt/R/4.5.3/lib/R"' >> /root/.profile
        Rscript --no-save --no-restore -e "cat(R.version\$version.string, '\n')"
        echo "[startup] R 4.5.3 installed from Posit binary"
```

### What each new line does

| Line | Purpose |
|---|---|
| `wget ... r-4.5.3_1_amd64.deb` | Downloads the self-contained Posit package for R 4.5.3 on Ubuntu 24.04 |
| `dpkg -i ... \|\| apt-get install -f -y` | Installs the .deb; if dpkg complains about missing shared libs, `apt-get install -f` satisfies them automatically (all are standard Ubuntu packages already on the image) |
| `rm /tmp/r-4.5.3.deb` | Frees ~100 MB from the container's ephemeral layer |
| `export PATH=...` (inline) | Makes `R` and `Rscript` available immediately for the rest of the startup script (pip install rpy2, all Rscript calls in step 5) |
| `export R_HOME=...` (inline) | Tells rpy2's C extension build where R headers are; also needed at runtime for `import rpy2` |
| `echo ... >> .bashrc / .profile` | Persists PATH and R_HOME for all SSH sessions; also for `kubectl exec -- bash -l` login shells |
| `Rscript ... R.version\$version.string` | Immediately validates the install; if this line fails with "command not found" the problem is visible in logs before any R package installs start |

### Verification inside the pod (run after applying)

```bash
# Confirm R binary location and version
which Rscript        # must print /opt/R/4.5.3/bin/Rscript
Rscript --no-save --no-restore -e "cat(R.version\$version.string, '\n')"
# Must print: R version 4.5.3 (2026-02-28) or similar 4.5.x string

# Confirm rpy2 can load R
python -c "import rpy2.robjects as ro; print(ro.r('R.version\$version.string')[0])"
# Must print the same R version string
```

### Alternative: Option B — `RPY2_CFFI_MODE=ABI` + R 4.6.0

If the Posit CDN URL changes or becomes unavailable, a fallback approach is to allow R 4.6.0 to install from CRAN normally and force rpy2 into ABI (dynamic-linking) mode, which avoids the compile-time C API binding that causes the segfault:

```bash
apt-get install -y r-base r-base-dev
export RPY2_CFFI_MODE=ABI
/app/venv/bin/pip install --no-cache-dir "rpy2>=3.5.5"
echo 'export RPY2_CFFI_MODE=ABI' >> /root/.bashrc
echo 'export RPY2_CFFI_MODE=ABI' >> /root/.profile
```

Risk: ABI mode may still encounter the same PROTECT/GC segfault at runtime in method `33_amdbnorm` because the segfault is in rpy2's dynamic CFFI bindings, not only the compiled C extension. This approach has not been tested and is documented here only as a fallback if Option A fails.

---

## Updated To-Do List

### Fix 4 implementation (required before pod rebuild)

- [ ] **pod-ssh.yaml step 3 block** — replace the entire `apt-cache madison` / CRAN apt block with the Posit binary download block (Fix 4 above)
- [ ] Verify the Posit download URL is reachable before deploying: `curl -I https://cdn.posit.co/r/ubuntu-2404/pkgs/r-4.5.3_1_amd64.deb` (expect HTTP 200)

### Pod rebuild and validation (Fix 4)

- [ ] Delete and re-apply pod manifest:
  ```bash
  kubectl delete pod fl-batch-correction -n ${K8S_NAMESPACE}
  kubectl apply -f harmonization-scripts/k8s/pod-ssh.yaml -n ${K8S_NAMESPACE}
  ```
- [ ] In startup log, confirm `[startup] R 4.5.3 installed from Posit binary` (not any ERROR or "command not found" line)
- [ ] In startup log, confirm `[startup] FSQN + qsmooth verified OK` (step 5 sanity check)
- [ ] In startup log, confirm `[startup] Environment ready.`
- [ ] After pod ready, connect and run full smoke test:
  ```bash
  ssh fl-pod
  cd /app/harmonization-scripts
  python test_mock.py 2>&1 | tee /workspace/test_mock_after_fix4.txt
  ```
- [ ] Confirm smoke test results:
  - [ ] No `Segmentation fault` in output
  - [ ] No `DWD failed for batch ... penalty` messages
  - [ ] `bapred OK` in R packages section
  - [ ] No `reComBat MISSING` in R packages section
  - [ ] R version printed at top of test_mock.py output shows `4.5.x`
  - [ ] All previously-passing normalization methods still PASS or SKIP

### Documentation (after Fix 4 validation)

- [ ] Add row to `k8s/CLAUDE.md` Known Startup Failures: `r-recommended dependency conflict` → Posit binary fix
- [ ] Update `k8s/README.md` R version check section to document the Posit binary approach
