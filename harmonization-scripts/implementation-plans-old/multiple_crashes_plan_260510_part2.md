# Implementation Plan: Pod Startup Hardening

**Date:** 2026-05-10  
**Based on:** `multiple_crashes_research_260510_part2.md`  
**Root cause confirmed by user:** `apt-get install` in step 2 aborts with `E: Unable to locate package python3.11` because the `universe` repository is not enabled in the `ubuntu:24.04` Docker image. All packages listed after the unresolvable ones (including `git`, `libpng-dev`, `libuv1-dev`, etc.) are never installed.  
**Status:** Pending implementation

---

## Changes overview

| Fix | File | What changes | Risk |
|---|---|---|---|
| B1. Enable universe repo in step 1 | `pod-ssh.yaml` | Add `software-properties-common` to step 1 apt; add `add-apt-repository universe -y && apt-get update` at end of step 1 | Zero — additive |
| B2. Split step 2 into three sub-steps | `pod-ssh.yaml` | Separate system libs, python3.11, and octave into three apt-get calls | Low — same packages, better isolation |
| B3. Remove system Python 3.12 packages | `pod-ssh.yaml` | Drop `python3 python3-pip python3-dev python3-venv python3-full python-is-python3` from apt; keep only `python3.11 python3.11-venv python3.11-dev` | Low — these were never needed; venv provides everything |
| B4. Add missing system libs | `pod-ssh.yaml` | Add `libsodium-dev libjpeg-dev libfontconfig1-dev` to step 2a apt list | Zero — additive |
| B5. Add error guards to critical steps | `pod-ssh.yaml` | `|| { echo ...; exit 1; }` on venv creation, pip install; `|| echo WARNING` on optional R packages | Low — makes failures visible and stops cascades |
| B6. Remove `-qq` from apt-get, add timestamps | `pod-ssh.yaml` | Use `-q` in step 1 (less critical); no quiet flag in step 2 apt calls; prefix `[startup]` messages with `$(date +%H:%M:%S)` | Zero |
| B7. Add Python package version verification | `pod-ssh.yaml` | After step 4 pip install, run `python -c "import numpy, pandas, boto3, rpy2; print(...)"` | Zero — additive |
| B8. Add real R package load verification | `pod-ssh.yaml` | After each critical R package install, add a second `Rscript -e "library(X)"` call that prints PASS/FAIL | Zero — additive |
| B9. Pin harmonypy version | `pod-ssh.yaml` ConfigMap and `requirements.txt` | Change `harmonypy>=0.0.9` to `harmonypy>=0.0.9,<2.0` | Zero — avoids harmonypy 2.0 which likely requires pandas>=2.0 |

All changes are to `k8s/pod-ssh.yaml` (startup script and ConfigMap). `requirements.txt` in the repo gets a matching update. Requires pod rebuild.

---

## Fix B1 — Enable universe repo in step 1

### Why

`ubuntu:24.04` Docker image includes only `main` and `restricted` components in its apt sources. `python3.11`, `octave`, and `octave-statistics` are in `universe`. Without enabling universe, apt aborts with `E: Unable to locate package python3.11` and the entire step 2 install fails.

The fix moves `software-properties-common` into step 1 (where it can be installed from `main`) and then uses `add-apt-repository universe -y` to enable universe before step 2 runs.

### Exact change

**File:** `k8s/pod-ssh.yaml`  
**Step 1 block:**

**BEFORE:**
```yaml
        apt-get update -qq
        apt-get install -y -qq openssh-server rsync curl wget gnupg ca-certificates tmux htop
```

**AFTER:**
```yaml
        apt-get update -q
        apt-get install -y -q openssh-server rsync curl wget gnupg ca-certificates tmux htop software-properties-common
        add-apt-repository universe -y
        apt-get update -q
        echo "[startup] $(date +%H:%M:%S) Universe repo enabled"
```

`software-properties-common` provides `add-apt-repository`. It is in `main` and installs without universe.  
The second `apt-get update` refreshes the package index to include universe packages.  
`-q` instead of `-qq` still suppresses most noise but does not hide errors.

---

## Fix B2 — Split step 2 into three separate apt-get calls

### Why

One long `apt-get install` line with 25+ packages fails entirely if any package is unresolvable. Splitting into three calls with different failure modes (fatal / fatal / non-fatal) gives:
1. A clear error message identifying which sub-group failed
2. Octave as a non-fatal dependency (only needed for Shambhala2, which is already low-priority)
3. python3.11 as a dedicated call with an explicit fatal guard

### Exact change

**File:** `k8s/pod-ssh.yaml`  
**Step 2 block — full replacement:**

**BEFORE:**
```yaml
        # -- 2. System libraries for Python and R --
        apt-get install -y -qq build-essential gfortran cmake libcurl4-openssl-dev libssl-dev libxml2-dev libhdf5-dev libblas-dev liblapack-dev libuv1-dev libpng-dev zlib1g-dev python3 python3-pip python3-dev python3-venv python3-full python-is-python3 python3.11 python3.11-venv python3.11-dev git software-properties-common octave octave-statistics
        # Wrapper so Shambhala2's system("matlab ...") call finds octave,
        # stripping MATLAB-only flags that octave does not recognise
        printf '...' > /usr/local/bin/matlab && chmod +x /usr/local/bin/matlab
        echo "[startup] System libraries installed"
```

**AFTER:**
```yaml
        # -- 2a. Core system libraries (all in 'main' — no universe required) --
        apt-get install -y build-essential gfortran cmake \
            libcurl4-openssl-dev libssl-dev libxml2-dev libhdf5-dev \
            libblas-dev liblapack-dev libuv1-dev libpng-dev zlib1g-dev \
            libsodium-dev libjpeg-dev libfontconfig1-dev git \
            || { echo "[startup] $(date +%H:%M:%S) FATAL: core system libs failed — cannot continue"; exit 1; }
        echo "[startup] $(date +%H:%M:%S) Core system libraries installed"

        # -- 2b. Python 3.11 (in 'universe') --
        apt-get install -y python3.11 python3.11-venv python3.11-dev \
            || { echo "[startup] $(date +%H:%M:%S) FATAL: python3.11 not found — universe repo may not be enabled"; exit 1; }
        echo "[startup] $(date +%H:%M:%S) Python 3.11 installed: $(python3.11 --version 2>&1)"

        # -- 2c. Octave (in 'universe' — non-fatal; only needed for Shambhala2) --
        apt-get install -y octave octave-statistics \
            && echo "[startup] $(date +%H:%M:%S) Octave installed: $(octave --version 2>&1 | head -1)" \
            || echo "[startup] $(date +%H:%M:%S) WARNING: octave not installed — normalize_shambhala will SKIP"
        # Wrapper so Shambhala2's system("matlab ...") call finds octave,
        # stripping MATLAB-only flags that octave does not recognise
        printf '#!/bin/bash\nargs=()\nfor a in "$@"; do\n  case "$a" in\n    -nodesktop|-nosplash|-nodisplay) ;;\n    *) args+=("$a") ;;\n  esac\ndone\nexec octave --no-gui "${args[@]}"\n' > /usr/local/bin/matlab && chmod +x /usr/local/bin/matlab
```

---

## Fix B3 — Remove system Python 3.12 packages from apt

### Why

`python3`, `python3-dev`, `python3-venv`, etc. in Ubuntu 24.04 all point to Python 3.12. Installing them alongside `python3.11` creates two Python interpreters on the system PATH, which causes confusion (e.g., `python3` resolves to 3.12, `python` via venv resolves to 3.11 — only while venv is active). Since the venv provides all Python functionality needed at runtime, the system Python packages serve no purpose.

By removing them, the only Python interpreter on the pod is 3.11, and it is accessed exclusively through the venv.

### Exact change

This change is implicit in Fix B2: the **AFTER** block above simply does not include `python3 python3-pip python3-dev python3-venv python3-full python-is-python3 software-properties-common`. `software-properties-common` is now installed in step 1 (Fix B1). All other python3 packages are removed.

---

## Fix B4 — Add missing system libraries

### Why

Three system libraries are missing from the current apt list but required by R packages that are explicit benchmarking dependencies:

| Library | Needed for |
|---|---|
| `libsodium-dev` | R `sodium` package (pulled in by several Bioconductor deps) — absence causes `fatal error: sodium.h: No such file or directory` |
| `libjpeg-dev` | R `jpeg` package (pulled in by `Hmisc`, which is a qsmooth dependency) — absence causes `fatal error: jpeglib.h: No such file or directory` |
| `libfontconfig1-dev` | R `systemfonts` package (pulled in by `ragg` / `ggplot2` chain) — absence causes `fatal error: fontconfig/fontconfig.h: No such file or directory` |

All three are in the `main` repository and are included in the step 2a apt-get list above.

---

## Fix B5 — Add error guards to critical steps

### Why

Without `|| { ...; exit 1; }` guards, failures in critical steps produce no visible error and the script continues building on a broken foundation. The pod reaches `[startup] Environment ready.` even when Python, the venv, and all packages are missing.

### Exact changes

**Step 2.5 (venv creation):**

**BEFORE:**
```yaml
        python3.11 -m venv /app/venv
        source /app/venv/bin/activate
        echo 'source /app/venv/bin/activate' >> /root/.bashrc
        echo 'source /app/venv/bin/activate' >> /root/.profile
        echo "[startup] Python venv created at /app/venv"
```

**AFTER:**
```yaml
        python3.11 -m venv /app/venv \
            || { echo "[startup] $(date +%H:%M:%S) FATAL: venv creation failed — python3.11-venv may not be installed"; exit 1; }
        source /app/venv/bin/activate
        echo 'source /app/venv/bin/activate' >> /root/.bashrc
        echo 'source /app/venv/bin/activate' >> /root/.profile
        echo "[startup] $(date +%H:%M:%S) Python venv created: $(python --version 2>&1)"
```

**Step 4 (pip install):**

**BEFORE:**
```yaml
        /app/venv/bin/pip install --no-cache-dir setuptools wheel
        /app/venv/bin/pip install --no-cache-dir -r /etc/fl-deps/requirements.txt
        echo "[startup] Python packages installed"
```

**AFTER:**
```yaml
        /app/venv/bin/pip install --no-cache-dir setuptools wheel \
            || { echo "[startup] $(date +%H:%M:%S) FATAL: setuptools install failed"; exit 1; }
        /app/venv/bin/pip install --no-cache-dir -r /etc/fl-deps/requirements.txt \
            || { echo "[startup] $(date +%H:%M:%S) FATAL: requirements install failed — check ConfigMap requirements.txt for conflicts"; exit 1; }
        echo "[startup] $(date +%H:%M:%S) Python packages installed"
```

---

## Fix B6 — Remove `-qq`, add timestamps

### Why

`-qq` (very quiet) suppresses all output including error messages. Combined with no exit-code checking, this makes apt failures completely invisible in the log. `-q` (quiet) suppresses progress bars and informational messages but still prints errors and package counts.

Timestamps on `[startup]` messages show how long each phase takes and help identify which packages take the most time.

### Exact changes

- All `apt-get install -y -qq` → `apt-get install -y` (remove quiet for step 2, already split by Fix B2)
- Step 1: `-qq` → `-q` (keep some quiet for the less critical SSH setup)
- All `echo "[startup] ..."` → `echo "[startup] $(date +%H:%M:%S) ..."`

---

## Fix B7 — Add Python package version verification after step 4

### Why

Currently `[startup] Python packages installed` prints even if `/app/venv/bin/pip install` exited with code 0 but some packages failed silently (pip warns, exits 0). A brief import check catches any package that was listed but didn't install correctly.

### Exact change

Add after `echo "[startup] Python packages installed"`:

```yaml
        python -c "
import sys
import numpy as np
import pandas as pd
import boto3
import rpy2
import harmonypy
print('[startup] $(date +%H:%M:%S) Python import check: OK')
print('[startup]   python', sys.version.split()[0])
print('[startup]   numpy', np.__version__)
print('[startup]   pandas', pd.__version__)
print('[startup]   harmonypy', harmonypy.__version__)
" || echo "[startup] $(date +%H:%M:%S) WARNING: one or more Python imports failed — see output above"
```

Note: the `$(date +%H:%M:%S)` inside a Python string literal won't expand (it's not bash). Use a hardcoded label instead:

```yaml
        python -c "import sys, numpy as np, pandas as pd, boto3, rpy2, harmonypy; print('VERSIONS: python', sys.version.split()[0], '| numpy', np.__version__, '| pandas', pd.__version__, '| harmonypy', harmonypy.__version__)" \
            && echo "[startup] $(date +%H:%M:%S) Python import check PASSED" \
            || echo "[startup] $(date +%H:%M:%S) WARNING: Python import check FAILED"
```

---

## Fix B8 — Add real R package load verification for critical packages

### Why

The current pattern `Rscript -e "install.packages('X')" && echo "[startup] X OK"` is a false positive: Rscript exits 0 even when install.packages fails internally (R uses warnings not exceptions). `[startup] qsmooth OK` appeared in the log but `library(qsmooth)` failed at verification time.

The fix adds a `library()` call immediately after each install call for the four packages that have failed across multiple pod runs. If the library fails to load, the message is a WARNING (not FATAL) so the script continues to install other packages.

### Exact changes

Replace each of the four critical packages' install lines with a two-line pattern:

**qsmooth (currently two lines — Fix A2 pattern):**

**BEFORE:**
```yaml
        Rscript --no-save --no-restore -e "install.packages(c('quantreg','Hmisc','lme4'), dependencies=TRUE)" && echo "[startup] qsmooth CRAN deps OK"
        Rscript --no-save --no-restore -e "BiocManager::install('qsmooth', ask=FALSE, force=TRUE)"             && echo "[startup] qsmooth OK"
```

**AFTER:**
```yaml
        Rscript --no-save --no-restore -e "install.packages(c('quantreg','Hmisc','lme4'), dependencies=TRUE)" && echo "[startup] $(date +%H:%M:%S) qsmooth CRAN deps OK"
        Rscript --no-save --no-restore -e "BiocManager::install('qsmooth', ask=FALSE, force=TRUE)"
        Rscript --no-save --no-restore -e "library(qsmooth); cat('[startup] qsmooth verified OK\n')" \
            || echo "[startup] $(date +%H:%M:%S) WARNING: qsmooth not loadable after install"
```

**HarmonizR (requires sva which in turn requires curl/openssl — fixed by B4):**

**BEFORE:**
```yaml
        Rscript --no-save --no-restore -e "remotes::install_github('HSU-HPC/HarmonizR', upgrade='never')"
```

**AFTER:**
```yaml
        Rscript --no-save --no-restore -e "remotes::install_github('HSU-HPC/HarmonizR', upgrade='never')"
        Rscript --no-save --no-restore -e "library(HarmonizR); cat('[startup] HarmonizR verified OK\n')" \
            || echo "[startup] $(date +%H:%M:%S) WARNING: HarmonizR not loadable — normalize_harmonizr will FAIL"
```

**FSQN (previously missing `FSQN OK` message):**

**BEFORE:**
```yaml
        Rscript --no-save --no-restore -e "remotes::install_github('jenniferfranks/FSQN', upgrade='never')" && echo "[startup] FSQN OK"
```

**AFTER:**
```yaml
        Rscript --no-save --no-restore -e "remotes::install_github('jenniferfranks/FSQN', upgrade='never')"
        Rscript --no-save --no-restore -e "library(FSQN); cat('[startup] FSQN verified OK\n')" \
            || echo "[startup] $(date +%H:%M:%S) WARNING: FSQN not loadable"
```

**sva (the cascade root — must verify before HarmonizR):**

Add after the Bioconductor batch install line:
```yaml
        Rscript --no-save --no-restore -e "BiocManager::install(c('limma','sva','RUVSeq','batchelor','edgeR','DESeq2'), ask=FALSE)"
        Rscript --no-save --no-restore -e "library(sva); cat('[startup] sva verified OK\n')" \
            || echo "[startup] $(date +%H:%M:%S) WARNING: sva not loadable — HarmonizR will also fail"
```

---

## Fix B9 — Pin harmonypy version; guard Shambhala2 as non-fatal

### Harmonypy pin

`harmonypy>=0.0.9` resolves to 2.0.0, which may require `pandas>=2.0`. This would conflict with `pandas>=1.3.4,<2.0.0` and abort the pip install. Pin to the 0.x line.

**ConfigMap requirements.txt (line in `pod-ssh.yaml`) and `harmonization-scripts/requirements.txt`:**

**BEFORE:**
```
harmonypy>=0.0.9
```

**AFTER:**
```
harmonypy>=0.0.9,<2.0
```

### Shambhala2 non-fatal guard

Shambhala2 is installed from GitHub and returned an HTTP error in attempt 2. It is only needed for `normalize_shambhala` (`20_shambhala`). If it fails to install, that method SKIPs — this is acceptable and already the behavior when the GitHub repo is unavailable.

The current line has no `&&` echo, so it fails silently. Add an explicit message:

**BEFORE:**
```yaml
        Rscript --no-save --no-restore -e "remotes::install_github('BorisovNM/Shambhala2', upgrade='never')" && echo "[startup] Shambhala2 OK"
```

**AFTER:**
```yaml
        Rscript --no-save --no-restore -e "remotes::install_github('BorisovNM/Shambhala2', upgrade='never')" \
            && echo "[startup] $(date +%H:%M:%S) Shambhala2 installed" \
            || echo "[startup] $(date +%H:%M:%S) WARNING: Shambhala2 GitHub install failed — normalize_shambhala will SKIP"
```

---

## Risks and mitigations

### Risk 1 — `add-apt-repository universe` not idempotent on all ubuntu:24.04 images (Very Low)

Some minimal ubuntu images may not have the right DEB822 sources format. `add-apt-repository universe -y` might print a warning but still exit 0.

**Mitigation:** If step 2b fails with `FATAL: python3.11 not found`, the log will clearly say so. The fallback is to replace `add-apt-repository universe -y` with a direct sources edit:
```bash
sed -i 's/Components: main restricted$/Components: main restricted universe/' /etc/apt/sources.list.d/ubuntu.sources 2>/dev/null || true
echo "deb http://archive.ubuntu.com/ubuntu noble universe" >> /etc/apt/sources.list
apt-get update -q
```

### Risk 2 — `libfontconfig1-dev` or `libjpeg-dev` package name different on Ubuntu 24.04 (Very Low)

Package names are well-established on Ubuntu.  
**Mitigation:** If step 2a fails, the error message will name the problematic package; trivial to fix.

### Risk 3 — Shambhala2 GitHub API may remain flaky (Low-Medium)

If the GitHub API is rate-limited or the repo becomes unavailable, Shambhala2 will not install. With Fix B9, this is now a WARNING and does not break the pod. Method `20_shambhala` will record `status="skipped"` in the benchmark.

### Risk 4 — `harmonypy<2.0` may introduce other API changes (Low)

harmonypy 0.x is the API our code is built against. Pinning to `<2.0` is safe.

---

## Deployment sequence

### Step 1 — Apply all changes to `pod-ssh.yaml` and `requirements.txt`
Apply in any order; all changes are independent.

### Step 2 — Rebuild the pod
```bash
kubectl delete pod fl-batch-correction -n ${K8S_NAMESPACE}
kubectl apply -f harmonization-scripts/k8s/pod-ssh.yaml -n ${K8S_NAMESPACE}
```

### Step 3 — Watch startup log for new messages
```bash
kubectl logs -f fl-batch-correction -n ${K8S_NAMESPACE} | grep -E "\[startup\]|FATAL|E: Unable"
```

Expected new sequence (with timestamps):
```
[startup] HH:MM:SS Universe repo enabled
[startup] HH:MM:SS Core system libraries installed
[startup] HH:MM:SS Python 3.11 installed: Python 3.11.x
[startup] HH:MM:SS Octave installed: ...   ← or WARNING if unavailable
[startup] HH:MM:SS Python venv created: Python 3.11.x
[startup] HH:MM:SS R 4.5.3 installed from Posit binary
[startup] HH:MM:SS Python packages installed
[startup] HH:MM:SS Python import check PASSED
[startup] HH:MM:SS Installing R packages - this takes 20-40 min...
[startup] HH:MM:SS qsmooth CRAN deps OK
[startup] HH:MM:SS qsmooth verified OK        ← new real check
[startup] HH:MM:SS sva verified OK            ← new real check
[startup] HH:MM:SS HarmonizR verified OK      ← new real check
[startup] HH:MM:SS Shambhala2 installed       ← or WARNING
[startup] HH:MM:SS FSQN verified OK           ← new real check
[startup] HH:MM:SS FSQN + qsmooth verified OK
[startup] HH:MM:SS R packages installed
[startup] HH:MM:SS Environment ready. Sync scripts with rsync and run.
```

If any FATAL message appears, the pod exits immediately. Check `/workspace/pod_startup.log` for the full context.

### Step 4 — Connect and verify
```bash
ssh fl-pod
python --version         # must print: Python 3.11.x
python -c "import numpy, pandas, rpy2, boto3, harmonypy; print('pandas', pandas.__version__)"
# Expected: pandas 1.5.3
```

### Step 5 — Run smoke test
```bash
cd /app/harmonization-scripts
python test_mock.py 2>&1 | tee /workspace/test_mock_attempt3.txt
```

---

## To-Do List

### Code changes (before pod rebuild)

- [x] **pod-ssh.yaml step 1** — add `software-properties-common` to apt list; add `add-apt-repository universe -y && apt-get update -q`; remove `-qq` → `-q`; add timestamps (Fix B1, B6)
- [x] **pod-ssh.yaml step 2** — replace single apt-get with three sub-steps (2a system libs, 2b python3.11, 2c octave); add `libsodium-dev libjpeg-dev libfontconfig1-dev`; add fatal guards on 2a and 2b (Fix B2, B3, B4, B5)
- [x] **pod-ssh.yaml step 2.5** — add `|| exit 1` guard on venv creation; log `$(python --version)` (Fix B5)
- [x] **pod-ssh.yaml step 4** — add `|| exit 1` guards on both pip calls; add Python import verification block (Fix B5, B7)
- [x] **pod-ssh.yaml step 5** — add `sva verified` check after Bioconductor block; fix qsmooth, HarmonizR, FSQN with real `library()` verification; add Shambhala2 non-fatal guard; add timestamps everywhere (Fix B8, B9, B6)
- [x] **pod-ssh.yaml ConfigMap** — change `harmonypy>=0.0.9` to `harmonypy>=0.0.9,<2.0` (Fix B9)
- [x] **harmonization-scripts/requirements.txt** — same harmonypy pin (Fix B9)

### Pod rebuild and validation

- [ ] Delete and re-apply pod manifest
- [ ] In startup log, confirm `[startup] Universe repo enabled` appears
- [ ] In startup log, confirm `[startup] Python 3.11 installed: Python 3.11.x` appears
- [ ] In startup log, confirm `[startup] Python packages installed` appears (was missing in attempt 2)
- [ ] In startup log, confirm `[startup] Python import check PASSED`
- [ ] In startup log, confirm `[startup] qsmooth verified OK` (not just `qsmooth OK`)
- [ ] In startup log, confirm `[startup] sva verified OK`
- [ ] In startup log, confirm `[startup] FSQN + qsmooth verified OK` (not WARNING)
- [ ] SSH in; confirm `python --version` prints `Python 3.11.x`
- [ ] Confirm `pandas.__version__` is `1.5.x`
- [ ] Sync `bench_shared.py` to pod via rsync
- [ ] Run `python test_mock.py` → save to `/workspace/test_mock_attempt3.txt`
- [ ] Verify `30_recombat` PASS, `14_qsmooth` PASS, `36_explobatch` SKIP
- [ ] Verify no segmentation fault
