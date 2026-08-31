# Pod Startup Failure Analysis — Attempt 2 (2026-05-10)

**Log file:** `logs/pod_logs_failed_260510_attempt2.txt`  
**Symptom:** `bash: python: command not found` after `[startup] Environment ready.`

---

## What the logs show

### What started in this capture

`kubectl logs` captured only the **tail** of startup output — starting partway through step 5 (R packages, `install.packages('readr')` at line 1). Steps 1–4 (SSH, system libs, Python venv, Posit R binary, pip install) all happened before the kubectl buffer window. The full log is in `/workspace/pod_startup.log` if the pod is still alive.

### `[startup]` milestones present vs absent

| Message | Status |
|---|---|
| `[startup] SSH ready` | **ABSENT** (scrolled off kubectl buffer) |
| `[startup] System libraries installed` | **ABSENT** |
| `[startup] Python venv created at /app/venv` | **ABSENT** |
| `[startup] R 4.5.3 installed from Posit binary` | **ABSENT** |
| `[startup] Python packages installed` | **ABSENT** |
| `[startup] missForest OK`, `softImpute OK`, `FSQN OK` | **ABSENT** |
| `[startup] qsmooth CRAN deps OK` | present (line 346) |
| `[startup] qsmooth OK` | present (line 494) |
| `[startup] Shambhala2 OK` | **ABSENT** — GitHub HTTP error |
| `[startup] matrixStats OK`, `DWDLargeR+huge OK` etc. | present |
| `[startup] FSQN + qsmooth verified OK` | **ABSENT** — replaced by WARNING |
| `[startup] Environment ready.` | present (pod considered finished) |

---

## Root causes found

### Root cause 1: step 2 apt-get silently failed for multiple packages

The following packages were **confirmed not installed** (by their effects in later steps):

| Package | Evidence |
|---|---|
| `git` | `bash: line 86: git: command not found` (Procrustes clone at end of step 5) |
| `libpng-dev` | `/bin/bash: libpng-config: command not found`, `fatal error: png.h: No such file or directory` |
| `libuv1-dev` | `fatal error: uv.h: No such file or directory` |
| `python3.11` (or `python3.11-venv`) | Python venv was never created → `python: command not found` |

These packages are all explicitly listed in the step 2 `apt-get install` line. They did not get installed.

`build-essential` and `gfortran` *were* installed (R source compilation works), so the apt-get command did not fail entirely. The failure was **partial**: some packages installed, others did not.

**Most likely cause:** the single long `apt-get install` command lists `octave`, `octave-statistics`, and `python3.11` together with system libs. If even one of these is not found in the configured apt sources (e.g., universe is not enabled or temporarily unavailable), apt exits early. Packages already unpacked survive but those not yet reached are skipped. The `-qq` quiet flag suppresses the error message, so the startup log shows nothing.

'Indeed this is the case, when I ran the long line `apt-get install`, I have got the following failure:
root@fl-batch-correction:/app/harmonization-scripts# apt-get install -y -qq build-essential gfortran cmake libcurl4-openssl-dev libssl-dev libxml2-dev libhdf5-dev libblas-dev liblapack-dev libuv1-dev libpng-dev zlib1g-dev python3 python3-pip python3-dev python3-venv python3-full python-is-python3 python3.11 python3.11-venv python3.11-dev git software-properties-common octave octave-statistics
E: Unable to locate package python3.11
E: Couldn't find any package by glob 'python3.11'
E: Couldn't find any package by regex 'python3.11'
E: Unable to locate package python3.11-venv
E: Couldn't find any package by glob 'python3.11-venv'
E: Couldn't find any package by regex 'python3.11-venv'
E: Unable to locate package python3.11-dev
E: Couldn't find any package by glob 'python3.11-dev'
E: Couldn't find any package by regex 'python3.11-dev'

In the implementation plan, please use only python3.11, without python3 that can be anything and likely 3.12'

### Root cause 2: `[startup] qsmooth OK` is a false positive

The bash line:
```bash
Rscript ... "BiocManager::install('qsmooth', ask=FALSE, force=TRUE)" && echo "[startup] qsmooth OK"
```

`Rscript` exits with code 0 even when packages fail to install (R uses warnings, not exceptions). The `&&` fires regardless of whether qsmooth was actually installed. The final verification (`library(qsmooth)`) is the real check:

```
Error in library(qsmooth) : there is no package called 'qsmooth'
```

qsmooth depends on `Hmisc`, which depends on `png`. `png` requires `libpng-dev` (which wasn't installed). So the failure chain is: **libpng-dev missing → png fails → Hmisc fails → qsmooth fails**.

### Root cause 3: `sva` failed (dependency cascade for HarmonizR)

```
ERROR: dependency 'sva' is not available for package 'HarmonizR'
```

`sva` depends on `curl` and `openssl` R packages. Both require system libraries (`libcurl4-openssl-dev`, `libssl-dev`) that may also not have been installed (same apt-get failure). Result: sva → HarmonizR → the entire HarmonizR normalization method is broken.

### Root cause 4: Shambhala2 GitHub URL returned HTTP error

```
Error: Failed to install 'unknown package' from GitHub:
  cannot open URL 'https://api.github.com/repos/BorisovNM/Shambhala2/contents/DESCRIPTION?ref=HEAD'
```

This is a transient or persistent network/API error on the GitHub side. The repo exists (used in previous pod runs) but the API call failed this time. This is an example of the general problem: GitHub-hosted R packages are unreliable. If any network request fails, the package is not installed and methods depending on it fail silently at runtime.

### Root cause 5: No error propagation in the bash script

The startup script runs as a single bash session without `set -e`. When any command fails, the script continues as if nothing happened. The result:
- apt-get fails → no packages installed → no output → script proceeds to step 3
- `python3.11 -m venv /app/venv` fails (python3.11 not installed) → no venv → no Python
- `/app/venv/bin/pip install ...` fails (venv doesn't exist) → no Python packages
- R package failures → warnings printed, R exits 0 → `[startup] X OK` fires anyway

The pod prints `[startup] Environment ready.` regardless of what actually worked.

---

## Why `python: command not found`

The complete chain:
1. `apt-get install ... python3.11 python3.11-venv python3.11-dev ...` — **partially fails**; python3.11 is not installed
2. `python3.11 -m venv /app/venv` — fails with `command not found`, no venv created
3. `/app/venv/bin/pip install setuptools wheel` — fails, `/app/venv/bin/pip` does not exist
4. `/app/venv/bin/pip install -r /etc/fl-deps/requirements.txt` — fails the same way
5. `echo 'source /app/venv/bin/activate' >> /root/.bashrc` — runs (the echo is separate from the failed source), adds a broken activation line
6. On SSH login: `.bashrc` sources `/app/venv/bin/activate` → `No such file or directory` → continues silently
7. `python` is not in PATH; `python-is-python3` also not installed (same apt failure)

---

## Evaluation: is the installation too complex?

**Yes. Daniil's diagnosis is correct.** The current approach is structurally fragile in ways that cannot be fixed by adding more packages to the same script.

### Specific fragility points

1. **One apt-get command, 25+ packages, no error checking.** A single unresolvable package silently aborts package installation for everything that follows it in the dependency graph. Packages not installed → all downstream steps build on a broken foundation.

2. **`-qq` hides errors.** Quiet mode is fine for clean runs but makes debugging nearly impossible. The only way to see what failed is to check `/workspace/pod_startup.log` from inside a running pod.

3. **R package `&&` echo trick is misleading.** `Rscript ... && echo "OK"` fires on any Rscript exit 0, which is the default even on install failure. No `[startup] X OK` message reliably confirms a package is actually loadable.

4. **GitHub URLs are unreliable.** Shambhala2, FSQN, HarmonizR, TDM, AMDBNorm, DBNorm, DASC, exploBATCH — eight packages installed from GitHub `HEAD`. Any of them can fail due to: rate limiting, temporary 404, repo deletion (`fMM` already deleted), API changes. There is no version pinning.

5. **30–40 minute install time per pod restart.** Every iterative fix requires a full pod rebuild. Diagnosing one error, fixing it, rebuilding, and hitting the next error is the current workflow. This is slow and discouraging.

6. **No `set -e`.** The script continues silently after every failure. The pod reaches `[startup] Environment ready.` regardless of what is broken. There is no way to tell from the log alone whether the environment is actually usable.

### What "radical simplification" means in practice

There are three options, ordered from highest impact to lowest:

---

**Option A (Recommended): Pre-built Docker image**

All packages are baked into the image once. Pod startup takes 2 min instead of 30–40 min. Build-time failures are caught during image build and fixed before deployment. This is what `pod.yaml` already does with `fl-batch-correction:latest`.

The blocker identified previously was ECR admin access to create the repository. Once the repo exists (one-time setup by admin), all subsequent image pushes work without admin access.

Pros: zero startup failures from package installation; fully reproducible; fast iteration; no apt/R fragility.  
Cons: requires Docker build access and ECR repo creation (one-time admin action).

---

**Option B: Fix the current bash script structurally**

This is the minimal fix that would make the current approach less likely to silently break:

1. **Enable universe before step 2:**
   ```bash
   add-apt-repository universe -y && apt-get update -qq
   ```

2. **Split apt-get into stable-packages + optional-packages:**
   ```bash
   apt-get install -y build-essential gfortran libcurl4-openssl-dev libssl-dev libxml2-dev libhdf5-dev libblas-dev liblapack-dev libuv1-dev libpng-dev zlib1g-dev libsodium-dev cmake git
   apt-get install -y python3.11 python3.11-venv python3.11-dev python3 python3-pip python3-dev python3-venv python3-full python-is-python3
   apt-get install -y software-properties-common octave octave-statistics || echo "[startup] WARNING: octave not installed"
   ```

3. **Remove `-qq` from apt-get calls.** The noise is useful for diagnosis.

4. **Add `|| exit 1` after critical steps** (venv creation, pip install).

5. **Add `libsodium-dev`** to the apt list (missing; needed by R `sodium` package, which is a dependency chain).

Pros: no Docker requirement; stays in pod-ssh.yaml approach.  
Cons: still 30–40 min per rebuild; GitHub URL failures still unpredictable; still fragile compared to a pre-built image.

---

**Option C: Pre-built environment tarball on PVC**

Build the R library and Python venv once in a dedicated pod, tar them up, and save to `/workspace/r_library.tar.gz` and `/workspace/venv.tar.gz`. Subsequent pod startups just extract the tarballs. Extraction takes ~3 min vs 30–40 min installation.

Pros: fast; works without Docker or ECR; environment is consistent across restarts.  
Cons: requires an initial "build pod" run; OS must stay on Ubuntu 24.04 x86_64 for binary compatibility; tarballs must be rebuilt when packages change.

---

### Recommendation

**Immediate fix:** implement Option B (split apt-get, remove `-qq`, add universe, add `libsodium-dev`, add `|| exit 1` guards). This unblocks the current pod without requiring Docker access.

**Long-term fix:** Option A (pre-built Docker image), once ECR repo access is available. Every hour spent debugging pod startup is a direct argument for pre-baking the environment.
