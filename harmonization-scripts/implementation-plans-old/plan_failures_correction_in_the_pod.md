# Plan: Fixing test_mock.py Failures in the Pod

## Root Cause Analysis

### Bug 1 — Infinite recursion in `_py2rpy` / `_rpy2py` (affects 9 methods)

**What happened:** When adding the `_py2rpy` / `_rpy2py` helper wrappers, a `replace_all` substitution was used to replace every occurrence of `pandas2ri.py2rpy(` → `_py2rpy(` in the file. This also replaced the call **inside the helper function bodies themselves**, turning:

```python
def _py2rpy(x):
    with localconverter(_PD_CONVERTER):
        return pandas2ri.py2rpy(x)   # ← correct: calls rpy2 directly
```

into:

```python
def _py2rpy(x):
    with localconverter(_PD_CONVERTER):
        return _py2rpy(x)            # ← BUG: calls itself → RecursionError
```

Python hits the recursion limit (1000 calls) before the `localconverter` initialization can complete, which is why the traceback ends inside `functools.py`.

**Affected methods:** missforest, softimpute, 03_limma, 04_sva, 05_combat, 06_combat_seq, 10_mnn, 22_tmm, 23_vst.

**Fix:** Store the original `pandas2ri` functions under private aliases before any replacement, and call those aliases from the helper bodies:

```python
_pandas_py2rpy = pandas2ri.py2rpy   # saved reference — NOT touched by replace_all
_pandas_rpy2py = pandas2ri.rpy2py

def _py2rpy(x: object) -> object:
    with localconverter(_PD_CONVERTER):
        return _pandas_py2rpy(x)

def _rpy2py(x: object) -> object:
    with localconverter(_PD_CONVERTER):
        return _pandas_rpy2py(x)
```

---

### Bug 2 — `localconverter` + `pandas2ri.py2rpy` may not correctly dispatch in rpy2 3.6.7

**What happened:** In rpy2 3.6.x the conversion pipeline changed. The correct way to trigger full converter dispatch (including Series-within-DataFrame handling) is to call `ro.conversion.py2rpy()` inside the context, not `pandas2ri.py2rpy()` directly. `pandas2ri.py2rpy` is a `singledispatch` that only handles DataFrame; calling it directly on a DataFrame will try to convert each column (a Series), which has no handler.

**Fix:** Change the helper bodies to use `ro.conversion.py2rpy` / `ro.conversion.rpy2py` which respect the active converter context:

```python
def _py2rpy(x: object) -> object:
    with localconverter(_PD_CONVERTER):
        return ro.conversion.py2rpy(x)

def _rpy2py(x: object) -> object:
    with localconverter(_PD_CONVERTER):
        return ro.conversion.rpy2py(x)
```

---

### Bug 3 — FSQN R package not installed (affects 16_fsqn_r)

**What happened:** During interactive R package installation the user answered "none" to the "Update packages?" prompt instead of "all". The `install.packages('FSQN')` call was grouped with other packages; it either silently failed or was skipped.

**Fix:** Install manually in the running pod:
```bash
Rscript --vanilla -e "install.packages('FSQN', dependencies=TRUE, repos='https://cloud.r-project.org')"
```
Verify: `Rscript --vanilla -e "library(FSQN); cat('FSQN OK\n')"`.

---

### Bug 4 — qsmooth R package not installed (affects 14_qsmooth)

**Same cause as Bug 3.** qsmooth is a Bioconductor package.

**Fix:** Install manually:
```bash
Rscript --vanilla -e "BiocManager::install('qsmooth', ask=FALSE, update=FALSE)"
```
Verify: `Rscript --vanilla -e "library(qsmooth); cat('qsmooth OK\n')"`.

---

## To-Do List

- [ ] **1. Fix `bench_shared.py` — helper function bodies**
  - Add `_pandas_py2rpy = pandas2ri.py2rpy` and `_pandas_rpy2py = pandas2ri.rpy2py` aliases immediately after the imports (before the helper definitions).
  - Change `_py2rpy` body to call `ro.conversion.py2rpy(x)` inside the context (or `_pandas_py2rpy(x)` — test which works for rpy2 3.6.7).
  - Change `_rpy2py` body to call `ro.conversion.rpy2py(x)` (or `_pandas_rpy2py(x)`).
  - No other changes to bench_shared.py needed; all 25 call sites were correctly renamed.

- [ ] **2. Install FSQN in the running pod**
  - Run: `Rscript --vanilla -e "install.packages('FSQN', dependencies=TRUE, repos='https://cloud.r-project.org')"`
  - Verify: `Rscript --vanilla -e "library(FSQN); cat('FSQN OK\n')"`

- [ ] **3. Install qsmooth in the running pod**
  - Run: `Rscript --vanilla -e "BiocManager::install('qsmooth', ask=FALSE, update=FALSE)"`
  - Verify: `Rscript --vanilla -e "library(qsmooth); cat('qsmooth OK\n')"`

- [ ] **4. Sync fixed `bench_shared.py` to the pod**
  - `rsync -avz -e "ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" ~/fl_subset/harmonization-scripts/bench_shared.py root@localhost:/app/harmonization-scripts/bench_shared.py`

- [ ] **5. Re-run smoke test**
  - `python test_mock.py` inside the pod.
  - Expected result: 0 FAILs; only SKIP for 20_shambhala and 24_peer_k10 (both intentional).

- [ ] **6. Update pod-ssh.yaml startup script**
  - Remove the interactive update prompt risk by passing `update=FALSE` explicitly to each BiocManager call and using `--vanilla` on all Rscript invocations (already added in pod-ssh.yaml but verify the FSQN / qsmooth lines match the manual fix that worked).

---

## Notes

- tmm (22) and vst (23) will still show as SKIP after these fixes because `_assert_rnaseq_only()` raises `NotImplementedError` when mixed-batch data is present. This is correct, expected behavior.
- RUV (09) prints "only 0 control genes found — skipping" on the synthetic dataset because none of the HOUSEKEEPING genes exist in the mock 200-gene set. It returns the input unchanged; this is correct behavior.
- The `--vanilla` flag on Rscript suppresses `.Rprofile` loading and interactive prompts, making installs non-interactive. The `repos=` argument must be explicit when `--vanilla` is used since `.Rprofile` isn't loaded.
