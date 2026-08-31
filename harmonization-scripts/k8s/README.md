# Kubernetes Pod — FL Batch Correction

Runs the harmonization benchmark scripts on a `c6a.2xlarge` node (8 vCPU / 16 GiB).
The pod starts from `ubuntu:24.04`, installs Python + R 4.5 + all benchmark packages at startup, and exposes an SSH server so you can sync code from your local repo and connect from VSCode — no Docker image required.

**First startup takes ~30-40 minutes** while R/Bioconductor packages compile. SSH becomes available within the first ~2 minutes, so you can connect and watch the logs while it finishes.

---

## Prerequisites

| Tool | How to get it |
|---|---|
| `kubectl` configured for `${K8S_NAMESPACE}` | Ask DevOps for the kubeconfig |
| VSCode **Remote - SSH** extension | `ms-vscode-remote.remote-ssh` — install from the Extensions panel |
| An SSH key pair on your laptop | See Step 1 below |

---

## One-time setup (do this once per machine)

### Step 1 — Generate an SSH key (skip if you already have one)

```bash
ssh-keygen -t ed25519 -C "author@example.com"
# Accept the default path (~/.ssh/id_ed25519) and set a passphrase if desired.
```

Print your public key — you will paste it in Step 2:

```bash
cat ~/.ssh/id_ed25519.pub
```

### Step 2 — Add your public key to the ConfigMap

Open `k8s/pod-ssh.yaml` and replace the placeholder line inside `authorized_keys:` with the full output of the command above:

```yaml
data:
  authorized_keys: |
    ssh-ed25519 AAAA...your-actual-key... you@machine
```

> **Keep ConfigMaps in sync with the repo.**
> `pod-ssh.yaml` embeds copies of `requirements.txt` and `install_r_packages.R` in the `fl-deps` ConfigMap. If you add a Python or R package to those files, update the corresponding block in `pod-ssh.yaml` before applying the manifest.

### Step 3 — Create the AWS credentials Secret (skip if it already exists)

```bash
kubectl create secret generic aws-credentials \
    --from-file=credentials=$HOME/.aws/credentials \
    --from-file=config=$HOME/.aws/config \
    --namespace ${K8S_NAMESPACE}

# Verify:
kubectl get secret aws-credentials -n ${K8S_NAMESPACE}
```

---

## Launching the pod

### Step 4 — Apply the manifest

Run from the **repository root**:

```bash
kubectl apply -f harmonization-scripts/k8s/pod-ssh.yaml -n ${K8S_NAMESPACE}
```

This creates both the `ConfigMap` (SSH key) and the `Pod` in one command.

### Step 5 — Wait for SSH to become available (~2 min)

```bash
kubectl get pod fl-batch-correction -n ${K8S_NAMESPACE} -w
```

Once status shows `Running`, SSH is ready within ~2 minutes (apt install + sshd start).
R and Bioconductor packages continue installing in the background for another ~30-40 min.

Follow the startup log to watch progress:

```bash
kubectl logs -f fl-batch-correction -n ${K8S_NAMESPACE}
```

The log prints `[startup] Environment ready.` when all packages are installed and the pod is fully usable. You can connect via SSH before this point, but do not run benchmark scripts until you see that message.

---

## Connecting from VSCode via Remote-SSH

### Step 6 — Start port forwarding (keep this terminal open)

```bash
kubectl port-forward pod/fl-batch-correction 2222:22 -n ${K8S_NAMESPACE}
```

This maps `localhost:2222` on your laptop to port 22 inside the pod. Leave the terminal running for as long as you need the connection.

### Step 7 — Add the pod to your SSH config

Open (or create) `~/.ssh/config` and add:

```
Host fl-pod
    HostName localhost
    Port 2222
    User root
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
```

`StrictHostKeyChecking no` is intentional — the pod host key changes every time the pod restarts.

Test the connection:

```bash
ssh fl-pod
```

You should land in a root shell inside the pod. Type `exit` to return.

### Step 8 — Connect VSCode to the pod

1. Open the **Command Palette** (`Ctrl+Shift+P` / `Cmd+Shift+P`).
2. Type `Remote-SSH: Connect to Host...` and press Enter.
3. Select **fl-pod** from the list.
4. A new VSCode window opens connected to the pod.
5. Use **File → Open Folder** to open `/app/harmonization-scripts` (pre-built scripts in the image) or `/workspace` (your PVC).

### Python virtual environment

The startup script creates a virtual environment at `/app/venv` and activates it automatically in `/root/.bashrc` and `/root/.profile`. Every SSH session has the venv active without any manual step.

If you connect via `kubectl exec -it ... -- bash` (non-login, non-interactive shell), `.bashrc` may not be sourced. Use a login shell to get the venv automatically:

```bash
kubectl exec -it fl-batch-correction -n ${K8S_NAMESPACE} -- bash -l
```

Or activate it manually in an existing session:

```bash
source /app/venv/bin/activate
```

To install additional Python packages into the venv without restarting the pod:

```bash
/app/venv/bin/pip install <package-name>
```

---

## Syncing your local scripts to the pod

The ECR image ships a snapshot of the scripts at build time. To run your latest local edits without rebuilding the image, sync them over SSH.

### Option A — rsync (recommended for iterative development)

Run from your local machine (with port forwarding active):

```bash
rsync -avz --progress \
    -e "ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
    ~/FL_harmonization/harmonization-scripts/ \
    root@localhost:/app/harmonization-scripts/
```

local Mac:

```bash
rsync -avz --progress -e "ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no"  ~/fl_subset/harmonization-scripts/ root@localhost:/app/harmonization-scripts/
```

Re-run this command after each local edit to push changes to the pod.

### Option B — kubectl cp (no SSH needed)

```bash
# Copy a single file
kubectl cp harmonization-scripts/bench_shared.py \
    ${K8S_NAMESPACE}/fl-batch-correction:/app/harmonization-scripts/bench_shared.py

# Copy the whole directory
kubectl cp harmonization-scripts/. \
    ${K8S_NAMESPACE}/fl-batch-correction:/app/harmonization-scripts/
```

### Option C — drag-and-drop in VSCode

With the Remote-SSH window open, use the Explorer panel to drag files from your local VSCode window into the remote window.

---

## Running the benchmark scripts

All commands are run **inside the pod** — either in the VSCode integrated terminal (connected via Remote-SSH) or via `kubectl exec`. Use `-l` (login shell) so the Python venv is activated automatically:

```bash
kubectl exec -it fl-batch-correction -n ${K8S_NAMESPACE} -- bash -l
```

Once inside:

```bash
cd /app/harmonization-scripts

# Full cross-product run (960 jobs)
nohup python run_cross_product_parallel.py \
    --n-workers 6 --skip-if-exists \
    --memory-limit-gb 12.0 > /workspace/bench_run.log 2>&1 &

# Preparation-only run (Stage 1, 40 jobs)
nohup python run_prep_parallel.py \
    --n-workers 4 --skip-if-exists \
    --timeout-s 7200 --memory-limit-gb 6.0 > /workspace/prep_run.log 2>&1 &

# Follow logs (from inside the pod)
tail -f /workspace/bench_run.log

# Single job (debugging)
python run_one_job.py \
    --strat A_confirmed_bad --imp strict --method 16_fsqn_r \
    --out-json /tmp/test.json

# Smoke test (all 39 methods + 4 imputation approaches on synthetic data)
python test_mock.py
```

---

## Teardown

```bash
# Delete just the pod (keeps the ConfigMap and PVC)
kubectl delete pod fl-batch-correction -n ${K8S_NAMESPACE}

# Delete everything created by this manifest
kubectl delete -f harmonization-scripts/k8s/pod-ssh.yaml -n ${K8S_NAMESPACE}
```

The PVC (`fl-workspace`) and the `aws-credentials` Secret are **not** deleted by these commands — data and credentials persist.

---

## Troubleshooting

### Quick reference table

| Symptom | Fix |
|---|---|
| Pod stuck in `ContainerCreating` | `kubectl describe pod fl-batch-correction -n ${K8S_NAMESPACE}` — usually an image pull error or missing Secret |
| Pod stuck in `Pending` | Same `kubectl describe` — check `Events:`. If Karpenter reports no capacity, loosen the `nodeSelector` or remove the instance-type constraint; resource requests alone constrain node size |
| Pod phase `Failed`, exit code 137 | OOM kill — see **Out-of-memory** below |
| `error: cannot exec into a container in a completed pod` | Pod has crashed; delete and re-apply the manifest |
| `ssh: connect to host localhost port 2222: Connection refused` | Port forward is not running; restart Step 6 |
| `Permission denied (publickey)` | Public key in the ConfigMap doesn't match `~/.ssh/id_ed25519`; edit the ConfigMap, re-apply, then run `kubectl exec ... -- cp /etc/ssh-init/authorized_keys /root/.ssh/authorized_keys` |
| `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED` on rsync/ssh | Pod was restarted; run `ssh-keygen -R "[localhost]:2222"` to clear the stale entry |
| `rsync: mkdir ... failed: No such file or directory` | `/app/harmonization-scripts` does not exist yet — startup step 6 creates it after R packages finish (~30-40 min); create it manually: `ssh -p 2222 root@localhost "mkdir -p /app/harmonization-scripts"` |
| `python: command not found` | Ubuntu 24.04 ships `python3` only; the startup script installs `python-is-python3`, but if you connect before step 2 completes, use `python3` directly |
| `aws: command not found` | `awscli` is a Python package installed via `requirements.txt`; verify with `python -c "import boto3; print(boto3.client('sts').get_caller_identity())"` |
| `FileNotFoundError` for `/tmp/bench_prep_jobs/...` | `--imps` or `--strats` argument has a trailing `/` (shell tab-completion artifact); remove it |
| `ModuleNotFoundError: No module named 'numpy'` (or any package) | Venv not active; run `source /app/venv/bin/activate`, or reconnect with `bash -l` (see **Python virtual environment** above) |
| `pip install` says `externally-managed-environment` | You are using system pip, not the venv pip; use `/app/venv/bin/pip install` instead |
| All R packages missing (`PackageNotInstalledError`) | The startup `Rscript` calls failed silently — see **All R packages missing** below |
| Single R package missing (`PackageNotInstalledError: "FSQN"` etc.) | Install that package manually — see **Manually installing missing R packages** below |
| `Segmentation fault (core dumped)` in `test_mock.py` around method `33_amdbnorm` | R 4.6.0 was installed; rpy2 3.6.x is ABI-incompatible with R 4.6.0 — see **R version check** below |
| `DWD failed for batch '...': unused argument (penalty = "auto")` in test or benchmark logs | Old code; fixed in `bench_shared.py` — sync the latest script to the pod with rsync |
| `[startup] WARNING: FSQN or qsmooth verification failed` | qsmooth was not installed; `libpng-dev` was missing from step 2 — rebuild pod from current manifest |
| `36_explobatch` → `FAIL` with R error about missing package `fMM` | GitHub repo `maxkuhn/fMM` deleted permanently; fixed in current manifest (fMM line removed) and `bench_shared.py` (`36_explobatch` now SKIPs cleanly) |

---

### Out-of-memory (OOMKilled / exit code 137)

The pod has a hard `memory: 16Gi` limit. missForest and softImpute workers can each peak at 6–8 GB. Running 8 workers simultaneously against these methods will burst the limit.

**Safe parameters for 16 GiB:**

```bash
# knn — light, 4 workers fine
nohup python run_prep_parallel.py \
    --n-workers 4 --skip-if-exists --timeout-s 7200 \
    --memory-limit-gb 5.0 --imps knn > /workspace/prep_knn.log 2>&1 &

# missforest / softimpute — 2 workers max
nohup python run_prep_parallel.py \
    --n-workers 2 --skip-if-exists --timeout-s 216000 \
    --memory-limit-gb 6.0 --imps missforest,softimpute > /workspace/prep_slow.log 2>&1 &

nohup python run_norm_parallel.py    --imps strict,knn,softimpute --n-workers 2 --skip-if-exists --timeout-s 218000 --memory-limit-gb 20 > norm.log 2>&1 &
```



The `--memory-limit-gb` guard blocks the next worker launch until free RAM ≥ that threshold, so with `--n-workers 2` and `--memory-limit-gb 6.0` the workers effectively run serially — safe on 16 GiB.

After an OOM crash the pod enters `Failed` phase and cannot be exec'd into. Delete and re-apply:

```bash
kubectl delete pod fl-batch-correction -n ${K8S_NAMESPACE}
kubectl apply -f harmonization-scripts/k8s/pod-ssh.yaml -n ${K8S_NAMESPACE}
```

> Redirect logs to `/workspace/` (the persistent PVC) so they survive a pod crash: `> /workspace/run.log 2>&1 &`.

---

### All R packages missing

**Symptom:** `test_mock.py` shows 12–14 failures; `Rscript -e "nrow(installed.packages())"` prints ~30 (base R only); `libraries '/usr/local/lib/R/site-library' contain no packages`.

**Root cause:** The startup script writes `/root/.Rprofile` (which sets `repos = c(CRAN = "https://cloud.r-project.org")`), but `Rscript --vanilla` ignores `.Rprofile`. Without a CRAN mirror, every `install.packages()` and `BiocManager::install()` call exits with:

```
Error in contrib.url(repos, type) :
  trying to use CRAN without setting a mirror
```

All 12 packages then fail in a cascade. **The fix is already applied in the current `pod-ssh.yaml`** (all `Rscript --vanilla` calls have been replaced with `Rscript --no-save --no-restore`, which loads `.Rprofile` while still skipping workspace save/restore). If you are seeing this with an older pod image, delete the pod and re-apply the manifest.

To check whether the startup has finished or is still running:

```bash
# From outside the pod:
kubectl logs fl-batch-correction -n ${K8S_NAMESPACE} | grep 'startupstartup'

# Expected final line:
# [startup] Environment ready. Sync scripts with rsync and run.
```

If the pod is running but startup is not finished yet, wait — do not run `test_mock.py` until `[startup] Environment ready.` appears.

---

### Manually installing missing R packages

If one or two packages are missing in an otherwise healthy pod (e.g. a transient network error during startup), install them individually without restarting:

```bash
# Connect to the pod
ssh fl-pod
# or: kubectl exec -it fl-batch-correction -n ${K8S_NAMESPACE} -- bash -l

# Verify which packages are missing
Rscript --no-save --no-restore -e "
  pkgs <- c('missForest','softImpute','FSQN','limma','sva',
            'RUVSeq','batchelor','qsmooth','edgeR','DESeq2','TDM','HarmonizR')
  cat('Missing:', paste(pkgs[!sapply(pkgs, requireNamespace, quietly=TRUE)], collapse=', '), '\n')
"

# CRAN packages
Rscript --no-save --no-restore -e "install.packages('missForest', dependencies=TRUE)"
Rscript --no-save --no-restore -e "install.packages('softImpute', dependencies=TRUE)"

# FSQN — GitHub only (removed from CRAN)
Rscript --no-save --no-restore -e "remotes::install_github('jenniferfranks/FSQN', upgrade='never')"

# Bioconductor packages
Rscript --no-save --no-restore -e "BiocManager::install(c('limma','sva','RUVSeq','batchelor','edgeR','DESeq2'), ask=FALSE, update=FALSE)"
Rscript --no-save --no-restore -e "install.packages(c('quantreg','Hmisc','lme4'), dependencies=TRUE)"
Rscript --no-save --no-restore -e "BiocManager::install('qsmooth', ask=FALSE, force=TRUE)"

# GitHub packages
Rscript --no-save --no-restore -e "remotes::install_github('greenelab/TDM', upgrade='never')"
Rscript --no-save --no-restore -e "remotes::install_github('HSU-HPC/HarmonizR', upgrade='never')"
Rscript --no-save --no-restore -e "remotes::install_github('BorisovNM/Shambhala2', upgrade='never')"

# Verify
Rscript --no-save --no-restore -e "library(FSQN); library(qsmooth); cat('OK\n')"
```

> Use `--no-save --no-restore` (not `--vanilla`) so that `/root/.Rprofile` is loaded and the CRAN mirror is active.

---

### R version check

**Symptom:** `test_mock.py` crashes with `Segmentation fault (core dumped)` partway through the normalization methods, typically around method `33_amdbnorm`. The log shows `Attaching package: 'reshape2'` immediately before the crash.

**Root cause:** rpy2 3.6.x has a C-level ABI incompatibility with R 4.6.0's changed PROTECT/GC internals. The `noble-cran40` CRAN apt repo began serving R 4.6.0 on 2026-04-24. A previous attempt to pin R 4.5.x via `apt-cache madison` also failed because `r-recommended=4.5.3` was removed from the repo when 4.6.0 shipped, breaking the exact-version `Depends:` chain and leaving R uninstalled.

**Current fix:** The pod installs R 4.5.3 directly from a Posit-hosted standalone `.deb` (step 3), bypassing the CRAN apt repo entirely. R is installed to `/opt/R/4.5.3/` with `PATH` and `R_HOME` set persistently.

**Verify which R version is installed:**

```bash
which Rscript
# Must print: /opt/R/4.5.3/bin/Rscript
Rscript --no-save --no-restore -e "cat(R.version\$version.string, '\n')"
# Must print: R version 4.5.3 (...)
# If it prints 4.6.x or "command not found", rebuild the pod from the current manifest
```

**Rebuild the pod if needed:**

```bash
kubectl delete pod fl-batch-correction -n ${K8S_NAMESPACE}
kubectl apply -f harmonization-scripts/k8s/pod-ssh.yaml -n ${K8S_NAMESPACE}
```

Watch for this confirmation line in the startup log:
```
[startup] R 4.5.3 installed from Posit binary
```

---

### Deleting the pod

```bash
kubectl delete pod fl-batch-correction -n ${K8S_NAMESPACE}
```
