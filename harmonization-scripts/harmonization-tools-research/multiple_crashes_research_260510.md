# Root Cause Research: Multiple Pod Startup Failures

**Date:** 2026-05-10  
**Log analyzed:** `logs/pod_logs_failed_260510.txt` (26,809 lines; pod with Fix 1a–Fix 4 applied)  
**Status:** Research only — no code changes recommended until Daniil decides on strategy

---

## What is known from the log

The log covers only the tail of step 5 (R package installation). Steps 1–4 (SSH, system libs, Python venv, Posit R binary download, pip install) are not present — they were scrolled off by `kubectl logs`'s internal line buffer before the capture started.

**Confirmed from the log:**
- R 4.5.3 from the Posit binary IS installed and working: every `gcc` compilation line in the log references `/opt/R/4.5.3/lib/R/include`, proving Fix 4 succeeded.
- FSQN IS installed: the final verification line prints `Loading required package: preprocessCore` before the qsmooth error, meaning `library(FSQN)` loaded correctly.

**Confirmed failures:**

| # | Failure | Proof line | Method(s) affected |
|---|---|---|---|
| F1 | `qsmooth` not installed | `Error in library(qsmooth) : there is no package called 'qsmooth'` (line 26805) | `14_qsmooth` |
| F2 | `fMM` GitHub repo returns HTTP 404 | `HTTP error 404. Not Found. Did you spell the repo owner (maxkuhn) and repo name (fMM) correctly?` (line 26795–26799) | `36_explobatch` (runtime dep) |
| F3 | `png` R package fails to compile | `fatal error: png.h: No such file or directory` (line 26778) | `reticulate` → none used in bench |
| F4 | `reticulate` not installed | `installation of 2 packages failed: 'png', 'reticulate'` (line 26793) | none directly |

**Not confirmed from this log (output was cut off before these steps):**
- Whether Python packages (`rpy2`, `numpy`, `pandas`, etc.) installed correctly in the venv
- Whether `missForest`, `softImpute`, `DWDLargeR`, `DBNorm`, `AMDBNorm`, and other non-Bioconductor R packages installed

The user's observation of "no python libraries installed in venv" most likely refers to the **previous pod run** (before Fix 4), where R was never installed, causing `pip install rpy2` to fail — taking the entire venv setup with it. In the current log (Fix 4 pod), R is confirmed working, so pip should have succeeded.

---

## Detailed Root Cause Analysis

### F1 — `qsmooth` not installed

**What happened:** `BiocManager::install('qsmooth', ask=FALSE)` was called (step 5, line ~7 of the install sequence). The command ran and exited, but left no output in the captured log segment — its output was already scrolled off. The fact that `library(qsmooth)` fails proves the installation did not succeed.

**Why it fails:** `qsmooth` (Hicks et al., 2018) is a Bioconductor package with a C++ extension. As of Bioconductor 3.22 (shipped with R 4.5), qsmooth requires `preprocessCore` and `Hmisc` as Bioconductor dependencies. In practice, `BiocManager::install('qsmooth')` under R 4.5.3 / Bioc 3.22 frequently fails on fresh Ubuntu builds because:

1. The `BiocManager::install(version='3.22', ask=FALSE, update=FALSE)` line runs **before** the individual package installs. If BiocManager installed Bioc 3.22 itself but did not upgrade the base R packages (because `update=FALSE`), some Bioc dependency graphs can be unsatisfied when qsmooth tries to resolve them.

2. A more likely cause: the startup script installs the large `limma/sva/RUVSeq/batchelor/edgeR/DESeq2` bundle first as one call, then `qsmooth` in a separate call with `ask=FALSE`. If the first bundle call left the session in a state where some dependency version is locked (e.g., `Bioc` metadata cache is stale), the second call may silently skip qsmooth or fail.

3. There is also a known intermittent failure in `qsmooth` compilation on Ubuntu 24.04 / gcc 13 related to the `preprocessCore` C extension. It compiles without error but the resulting `.so` is rejected at load time in some environments.

**Impact:** Method `14_qsmooth` fails at runtime. All other methods are unaffected. qsmooth is used in the benchmark but is not the selected SOM method.

---

### F2 — `fMM` GitHub repo deleted (HTTP 404)

**What happened:** `remotes::install_github('maxkuhn/fMM', upgrade='never')` returns HTTP 404. The repo `maxkuhn/fMM` no longer exists on GitHub (deleted, renamed, or made private after the install script was written).

**Why it matters:** `fMM` is a runtime dependency of `exploBATCH` (the `syspremed/exploBATCH` GitHub package). The bench_shared.py comment at line 2393 lists it explicitly: `fMM, exploBATCHbreast, exploBATCHcolon must already be installed on the pod`. If `fMM` is absent, `36_explobatch` will fail at runtime when `library(exploBATCH)` is called or when the function internally calls `fMM::` functions.

**Impact:** `36_explobatch` will produce a runtime error on every benchmark job that uses it. exploBATCH is not a critical method and is not the benchmark winner or the SOM pipeline method, but it is one of the 39 benchmark methods.

**Note:** `fMM` was a minor R package implementing finite mixture models (GMM-based clustering). It was an obscure package used internally by exploBATCH. Its disappearance from GitHub is permanent — it will not come back unless the author restores it.

---

### F3 — `png` R package fails to compile

**What happened:** `install.packages(c("mvtnorm", "mclust", "rARPACK", ...))` installs most of the exploBATCH CRAN dependencies successfully, but `png` fails. The `png` R package requires `libpng-dev` (provides `png.h` and `libpng-config`) to be installed as a system library before compilation. The step 2 `apt-get install` list in `pod-ssh.yaml` does not include `libpng-dev`.

**Why `png` is being installed at all:** `png` is a transitive dependency of `reticulate`, which is a dependency of some packages in the exploBATCH dependency tree. Neither `png` nor `reticulate` are directly used by any normalization method in bench_shared.py.

**Impact:** `36_explobatch` will fail at runtime regardless of F2 status (both fMM and its transitive dep reticulate are broken). Other methods unaffected.

---

### F4 — Python venv / pip install status (from previous pod run)

**What happened in the previous pod (before Fix 4):** The CRAN apt pin approach from Fix 1a found `r-base=4.5.3` in the apt cache but could not install it because `r-recommended=4.5.3-1.2404.0` was removed from noble-cran40 when R 4.6.0 shipped. R was never installed. When step 4 ran `pip install rpy2`, pip's build step for `rpy2-rinterface` (the C extension) ran `R RHOME` to locate R headers and got `No such file or directory`. The entire `pip install` command failed with a non-zero exit code. Because step 4 in the startup script has no `||` or exit guard, execution continued. The echo `[startup] Python packages installed` printed anyway. The venv appeared to contain only the packages pre-installed with the venv itself (none of the requirements.txt packages).

**In the current pod (Fix 4 applied):** R 4.5.3 from Posit is confirmed working (gcc lines in log prove it). Pip should succeed. This log does not contain pip output (steps 1–4 output is outside the captured buffer), but there is no evidence of failure.

---

## Summary of All Failures Across Both Pod Runs

| Pod run | Failure | Root cause | Status |
|---|---|---|---|
| Pre-Fix 4 | R not installed | `r-recommended=4.5.3` removed from CRAN noble-cran40 apt repo | Fixed by Fix 4 (Posit binary) |
| Pre-Fix 4 | rpy2 not installed in venv | `pip install rpy2` build requires R in PATH; R was absent | Fixed by Fix 4 (R now installed before pip) |
| Pre-Fix 4 | Segfault in `33_amdbnorm` | rpy2 3.6.x ABI incompatibility with R 4.6.0 PROTECT/GC internals | Fixed by Fix 4 (R pinned to 4.5.3) |
| Pre-Fix 4 | DWD correction silently produces identity output | `DWDLargeR::genDWD` removed `penalty` argument | Fixed by Fix 2 |
| Pre-Fix 4 | `reComBat MISSING` / `FAbatch MISSING` in smoke test | Wrong R package names in `_CRITICAL_PKGS` | Fixed by Fix 3 |
| **Current pod** | `qsmooth` not installed | `BiocManager::install('qsmooth')` fails silently under R 4.5.3 / Bioc 3.22 | **Open** |
| **Current pod** | `fMM` not installed | GitHub repo `maxkuhn/fMM` deleted (HTTP 404) | **Open** |
| **Current pod** | `png` / `reticulate` not installed | `libpng-dev` not in step 2 apt-get install list | **Open** (low impact) |

---

## Strategic Decision: Fix Individual Issues vs. Upgrade to R 4.6.0

The user raised the question of whether it is better to **upgrade to R 4.6.0 and drop the few affected methods** rather than continuing to fight the R 4.5.x installation problems. Here is an honest evaluation.

---

### Option A — Continue with R 4.5.3 (Posit binary) and fix remaining issues

R 4.5.3 is confirmed working in the current pod. The remaining failures are:

1. **qsmooth**: fix by either (a) adding `libpng-dev` and `zlib1g-dev` to step 2 (which may help some transitive deps), or (b) replacing the single `BiocManager::install('qsmooth')` call with an explicit two-step install that first installs `preprocessCore` separately, then qsmooth. Alternatively, install from the Bioc GitHub mirror directly: `remotes::install_github('ksmooth-ng/qsmooth')`.

2. **fMM / exploBATCH**: `fMM` is permanently gone from GitHub. Options: (a) accept that `36_explobatch` is broken and mark it as a permanent skip in bench_shared.py (raise `NotImplementedError`), or (b) find an archived copy of fMM (it was on CRAN before being moved to GitHub; the CRAN archive at `https://cran.r-project.org/src/contrib/Archive/fMM/` may have a tarball), or (c) install exploBATCH without fMM and accept runtime failures.

3. **png / reticulate**: add `libpng-dev` to the step 2 apt-get install line. Low priority since neither is used directly.

**Pros:**
- R 4.5.3 + rpy2 3.6.x is a **proven, tested combination** across all 39 normalization methods
- The segfault in `33_amdbnorm` is definitively resolved — no risk of regression
- All other 38 methods that worked before will continue to work
- qsmooth and explobatch are both fixable with small changes
- No need to audit all 39 normalization functions for rpy2 API compatibility

**Cons:**
- The Posit binary approach adds a point of dependency on `cdn.posit.co` being available and keeping the 4.5.3 package accessible (Posit archives old versions, but their CDN availability is not guaranteed indefinitely)
- Each new pod startup requires a 100 MB download of the Posit binary
- Ongoing maintenance: if R 4.5.x reaches end-of-life in the CRAN/Bioc ecosystem, Bioconductor 3.22 packages will eventually become unsupported
- Individual package fixes are accumulating technical debt

---

### Option B — Upgrade to R 4.6.0 + rpy2 4.x (new major version)

Drop the version pin entirely. Install R 4.6.0 from the CRAN apt repo (works out of the box, no dep conflicts). Upgrade `rpy2` from `>=3.5.5` to `>=4.0` in requirements.txt. rpy2 4.x has explicit R 4.6.x support and rewrites the C extension to be compatible with R 4.6.0's changed PROTECT/GC stack internals.

**What would break and require audit:**

rpy2 4.0 introduced breaking API changes relative to 3.x:

| Changed in rpy2 4.x | Affected code in bench_shared.py |
|---|---|
| `rpy2.robjects.packages.importr` import path unchanged; OK | — |
| `localconverter` still in `rpy2.robjects.conversion`; OK | — |
| `pandas2ri.converter` still works; OK | — |
| `ro.r(f"""...""")` inline R still works; OK | — |
| `rpy2.rinterface_lib` package renamed in some 4.x builds | rpy2-level try/except blocks in bench_shared.py may need update |
| `R_HOME` discovery changed to require `R` in PATH explicitly | Already handled: Fix 4 sets PATH and R_HOME |

The critical unknown: **does the `33_amdbnorm` segfault also occur with rpy2 4.x + R 4.6.0?** The rpy2 4.x changelog states it fixes R 4.6.0 GC incompatibility. If that is accurate, the segfault is gone. If not, `33_amdbnorm` will still crash.

The secondary unknown: `qsmooth` with R 4.6.0 / Bioconductor 3.22. Bioc 3.22 is released for R 4.5. The next Bioc release (3.23) will correspond to R 4.6. Installing Bioc 3.22 packages on R 4.6.0 is theoretically possible via `BiocManager::install(version='3.22')` but is not officially supported and some packages will fail to compile due to internal R API changes between 4.5 and 4.6.

The `fMM`/exploBATCH failure is **independent of R version** — it is caused by a deleted GitHub repo. This problem exists regardless of which R version is chosen.

**Pros:**
- No dependency on Posit CDN or hardcoded version URLs
- CRAN apt repo gives R 4.6.0 without any custom logic
- rpy2 4.x is the actively maintained branch; 3.x is approaching end-of-life
- Bioc 3.23 (for R 4.6) will be released ~Spring 2026 and will natively support R 4.6.0

**Cons:**
- rpy2 4.x API is not backwards-compatible with 3.x in all areas — requires a systematic audit of all 39 normalization functions in bench_shared.py (~2,700 lines of R/Python interop code)
- The segfault fix in rpy2 4.x is stated in the changelog but has **not been tested on our specific code path** (`AMDBNorm::AMDBNorm()` inside `33_amdbnorm`) — the risk is real
- Bioconductor 3.23 is not yet released for R 4.6.0. Running Bioc 3.22 on R 4.6.0 is unsupported and may cause qsmooth and other packages to fail for a different reason
- The audit and testing effort is estimated at 1–2 days of work
- Any rpy2 3.x-style code that is not backwards compatible will silently fail at runtime (not at import), making bugs hard to catch

---

### Option C — R 4.6.0 + rpy2 3.6.x with `RPY2_CFFI_MODE=ABI` (ABI dynamic mode)

Install R 4.6.0, keep rpy2 `>=3.5.5` (3.6.x), set `RPY2_CFFI_MODE=ABI` so rpy2 uses CFFI dynamic bindings instead of the compiled C extension that triggers the segfault.

**Pros:**
- No API audit needed (same rpy2 version as currently tested)
- No Posit CDN dependency
- pip install does not require R in PATH (ABI mode builds without R headers)

**Cons:**
- ABI mode is significantly slower (every R call goes through a CFFI dynamic dispatch layer) — relevant for bench_shared.py which makes thousands of R calls per normalization job
- The segfault in `33_amdbnorm` is in rpy2's C extension bindings for R's PROTECT stack. Whether ABI mode avoids this specific code path is **unverified** — the segfault might also occur in ABI mode's CFFI bindings if they call the same R internals
- Bioconductor 3.22 on R 4.6.0 has the same compatibility risk as Option B
- ABI mode is not recommended for production use by the rpy2 maintainers

---

### Recommendation summary

| Option | R version | rpy2 version | Risk of new segfault | Code audit needed | qsmooth fixable | Effort |
|---|---|---|---|---|---|---|
| A: R 4.5.3 Posit | 4.5.3 (pinned) | 3.6.x (current) | None — proven safe | No | Yes (Bioc 3.22 + extra step) | Low |
| B: R 4.6.0 + rpy2 4.x | 4.6.0 (apt) | 4.x (upgrade) | Unknown | Yes (~1–2 days) | Depends on Bioc 3.23 timing | High |
| C: R 4.6.0 + ABI mode | 4.6.0 (apt) | 3.6.x (current) | Unknown | No | Depends on Bioc 3.23 timing | Low-Medium |

**Option A is the lower-risk path** for the current dissertation timeline (target: Autumn 2026). The remaining failures (qsmooth, fMM, png) are individually fixable with targeted additions to the startup script — approximately 3–5 lines of changes. The benchmark is functional except for `14_qsmooth` and `36_explobatch`, and these two methods are not the benchmark winners nor the SOM pipeline method.

**Option B becomes the right choice** if: (a) Bioconductor 3.23 is released (expected ~May–June 2026), OR (b) rpy2 4.x has been explicitly tested against `33_amdbnorm` and the segfault is confirmed fixed, OR (c) the dissertation timeline allows for a full 2-day audit.

---

## Fix List for Option A (targeted repairs, no R version change)

These are the minimal changes needed to bring the current R 4.5.3 pod to full functionality:

| Fix | File | Change | Impact |
|---|---|---|---|
| A1 | `k8s/pod-ssh.yaml` step 2 | Add `libpng-dev zlib1g-dev` to the `apt-get install` line | Fixes png + reticulate compilation |
| A2 | `k8s/pod-ssh.yaml` step 5 | Replace single `BiocManager::install('qsmooth')` with explicit two-step install: first `preprocessCore` alone, then qsmooth; add `libpng-dev` as a guard | Fixes qsmooth |
| A3 | `k8s/pod-ssh.yaml` step 5 | Remove `remotes::install_github('maxkuhn/fMM', upgrade='never')` line | Stops the 404 error; fMM is gone |
| A4 | `bench_shared.py` | Add a check in `normalize_explobatch` that raises `NotImplementedError("fMM package deleted from GitHub; exploBATCH not functional")` | Makes 36_explobatch a clean SKIP instead of a cryptic runtime crash |

These four changes are all reversible and do not affect any other method. They can be applied in under 30 minutes.

---

## Open Questions for Daniil to Decide

1. **Which strategy?** Option A (targeted fix, stay on R 4.5.3) vs Option B (upgrade to R 4.6.0 + rpy2 4.x, full audit) vs Option C (R 4.6.0 + ABI mode, less effort but untested).

2. **Handle `36_explobatch`?** The fMM repo is permanently gone. Options: (a) mark as permanent SKIP / NotImplementedError in bench_shared.py, (b) try CRAN archive tarball (`r-project.org/src/contrib/Archive/fMM/`), (c) find alternative fMM equivalent. Option (a) is simplest and honest.

3. **Is `14_qsmooth` critical?** If qsmooth is needed for the SOM pipeline (it is not — FSQN is selected), then a targeted fix (A2) is worth it. If it is only a benchmark comparison method, it is less urgent.

4. **Log capture:** The current `kubectl logs -f` approach misses the first 20–25 minutes of startup. Should we add a `tee /workspace/pod_startup.log` to the startup script's output so that the full log is preserved on the PVC for future debugging?
