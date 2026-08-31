# Plan: Fix R Package Installation Failures in pod-ssh.yaml

## Root Cause

Every R package installation step failed with the same error:

```
Error in contrib.url(repos, type) :
  trying to use CRAN without setting a mirror
```

The startup script writes `/root/.Rprofile` to configure the CRAN mirror:

```bash
echo 'options(repos = c(CRAN = "https://cloud.r-project.org"), ...)' > /root/.Rprofile
```

But **all** subsequent `Rscript` calls use the `--vanilla` flag:

```bash
Rscript --vanilla -e "install.packages('BiocManager')"
```

`--vanilla` is equivalent to `--no-save --no-restore --no-site-file --no-init-file --no-environ`.
The `--no-init-file` component **silently ignores `/root/.Rprofile`**, so the `repos` option is never set.
Without a mirror, every `install.packages()` and `BiocManager::install()` call exits with an error.

### Cascade from the one root cause

| Step | Command | Outcome |
|---|---|---|
| 1 | `install.packages('BiocManager')` | FAIL — no CRAN mirror |
| 2 | `BiocManager::install(version='3.22', ...)` | FAIL — BiocManager not installed |
| 3 | `install.packages('remotes', ...)` | FAIL — no CRAN mirror |
| 4 | `install.packages('missForest', ...)` | FAIL — no CRAN mirror |
| 5 | `install.packages('softImpute', ...)` | FAIL — no CRAN mirror |
| 6 | `remotes::install_github('jenniferfranks/FSQN', ...)` | FAIL — `remotes` not installed |
| 7 | `BiocManager::install(c('limma','sva',...), ...)` | FAIL — BiocManager not installed |
| 8 | `BiocManager::install('qsmooth', ...)` | FAIL — BiocManager not installed |
| 9 | `remotes::install_github('greenelab/TDM', ...)` | FAIL — `remotes` not installed |
| 10 | `remotes::install_github('HSU-HPC/HarmonizR', ...)` | FAIL — `remotes` not installed |
| 11 | `library(FSQN); library(qsmooth)` | FAIL — neither installed |

All 12 R packages (FSQN, qsmooth, missForest, softImpute, limma, sva, RUVSeq, batchelor, edgeR, DESeq2, TDM, HarmonizR) end up missing, which is exactly what `test_mock.py` reports.

Python packages installed correctly — that section of the log shows no errors.

---

## Fix

**One-line change, applied 11 times:** replace `--vanilla` with `--no-save --no-restore` in every `Rscript` call inside the startup `args` block of `pod-ssh.yaml`.

`--no-save --no-restore` prevents reading/writing the R workspace `.RData` (the only legitimate reason to use `--vanilla` here) but **does** load `/root/.Rprofile`, so the CRAN mirror is active for every install call.

### File to change: `k8s/pod-ssh.yaml`

Replace every occurrence of `Rscript --vanilla` with `Rscript --no-save --no-restore` in the startup args block. There are **11 occurrences**, all inside the `args:` block starting at the line `# -- 5. R packages (~20-40 min) --`:

| Line (approx) | Before | After |
|---|---|---|
| BiocManager bootstrap | `Rscript --vanilla -e "if (!requireNamespace('BiocManager'..."` | `Rscript --no-save --no-restore -e "if (!requireNamespace('BiocManager'..."` |
| BiocManager version pin | `Rscript --vanilla -e "BiocManager::install(version='3.22'..."` | `Rscript --no-save --no-restore -e "BiocManager::install(version='3.22'..."` |
| remotes | `Rscript --vanilla -e "install.packages('remotes'..."` | `Rscript --no-save --no-restore -e "install.packages('remotes'..."` |
| missForest | `Rscript --vanilla -e "install.packages('missForest'..."` | `Rscript --no-save --no-restore -e "install.packages('missForest'..."` |
| softImpute | `Rscript --vanilla -e "install.packages('softImpute'..."` | `Rscript --no-save --no-restore -e "install.packages('softImpute'..."` |
| FSQN (GitHub) | `Rscript --vanilla -e "remotes::install_github('jenniferfranks/FSQN'..."` | `Rscript --no-save --no-restore -e "remotes::install_github('jenniferfranks/FSQN'..."` |
| Bioc batch | `Rscript --vanilla -e "BiocManager::install(c('limma'..."` | `Rscript --no-save --no-restore -e "BiocManager::install(c('limma'..."` |
| qsmooth | `Rscript --vanilla -e "BiocManager::install('qsmooth'..."` | `Rscript --no-save --no-restore -e "BiocManager::install('qsmooth'..."` |
| TDM (GitHub) | `Rscript --vanilla -e "remotes::install_github('greenelab/TDM'..."` | `Rscript --no-save --no-restore -e "remotes::install_github('greenelab/TDM'..."` |
| HarmonizR (GitHub) | `Rscript --vanilla -e "remotes::install_github('HSU-HPC/HarmonizR'..."` | `Rscript --no-save --no-restore -e "remotes::install_github('HSU-HPC/HarmonizR'..."` |
| Verification | `Rscript --vanilla -e "library(FSQN); library(qsmooth)..."` | `Rscript --no-save --no-restore -e "library(FSQN); library(qsmooth)..."` |

No other files need to change. `install_r_packages.R` is not used by `pod-ssh.yaml` (it is only used during Docker image builds via the `Dockerfile`).

---

## Steps to apply

### 1. Edit `k8s/pod-ssh.yaml` (on JupyterHub or Mac)

Use a global find-and-replace in the file: replace `Rscript --vanilla` with `Rscript --no-save --no-restore`. There are exactly 11 matches; all are in the R-packages section of the startup script.

### 2. Delete the current failed pod

```bash
kubectl delete pod fl-batch-correction -n ${K8S_NAMESPACE}
```

### 3. Re-apply the manifest

```bash
kubectl apply -f harmonization-scripts/k8s/pod-ssh.yaml -n ${K8S_NAMESPACE}
```

### 4. Watch startup progress

```bash
kubectl logs -f fl-batch-correction -n ${K8S_NAMESPACE}
```

Expected log lines (in order, after SSH is ready):
```
[startup] SSH ready - port-forward and connect now to watch progress
[startup] System libraries installed
[startup] R installed
[startup] Python packages installed
[startup] Installing R packages - this takes 20-40 min...
[startup] missForest OK
[startup] softImpute OK
[startup] FSQN OK
[startup] qsmooth OK
[startup] FSQN + qsmooth verified OK
[startup] R packages installed
[startup] Environment ready. Sync scripts with rsync and run.
```

### 5. Verify with test_mock.py

```bash
# Connect to the pod after "Environment ready" appears
kubectl exec -it fl-batch-correction -n ${K8S_NAMESPACE} -- bash

# Sync scripts first
rsync -avz -e "ssh -p 2222 ..." harmonization-scripts/ root@localhost:/app/harmonization-scripts/

# Inside the pod:
cd /app/harmonization-scripts
python test_mock.py
```

Expected result: `RESULT: 0 FAILURE(S)` (20_shambhala and 24_peer_k10 are expected SKIPs, not failures).

---

## No changes needed in Python scripts

All failures were in the R layer. The Python scripts (`bench_shared.py`, `run_one_job.py`, `run_cross_product_parallel.py`, `run_prep_parallel.py`, `test_mock.py`) are correct and do not need modification for this issue.
