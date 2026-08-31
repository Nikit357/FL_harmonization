# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Directory Purpose

Kubernetes manifests for running the FL harmonization benchmark on `c6a.2xlarge` (8 vCPU / 16 GiB) in the `${K8S_NAMESPACE}` namespace. All `kubectl` commands target that namespace with `-n ${K8S_NAMESPACE}`.

---

## Two Pod Manifests — Choose Carefully

| Manifest | Base image | When to use |
|---|---|---|
| `pod.yaml` | ECR `fl-batch-correction:latest` | Production runs; image has all packages pre-installed |
| `pod-ssh.yaml` | `ubuntu:24.04` (installs at startup) | Active development; VSCode Remote-SSH, no Docker rebuild needed |

**`pod-ssh.yaml` startup is 30–40 minutes** (R/Bioconductor compile time). SSH is ready in ~2 min so you can connect early and watch logs. Do **not** run benchmark scripts until the log prints `[startup] Environment ready.`

### Python virtual environment (`pod-ssh.yaml`)

The startup script creates a venv at `/app/venv` (step 2.5, after system libs) and activates it in `/root/.bashrc` and `/root/.profile`. All Python packages from the ConfigMap `requirements.txt` are installed into this venv (step 4). SSH sessions have the venv active automatically.

`kubectl exec ... -- bash` launches a non-login, non-interactive shell that does **not** source `.bashrc`. Use `bash -l` to get a login shell with the venv active, or run `source /app/venv/bin/activate` manually.

To install a package into the pod venv without restarting:
```bash
/app/venv/bin/pip install <package>
```

---

## ConfigMap Sync Requirement (pod-ssh.yaml)

`pod-ssh.yaml` embeds both `requirements.txt` and `install_r_packages.R` content inline inside the `fl-deps` ConfigMap. If you change either source file in the repo, **also update the matching block inside `pod-ssh.yaml`** before re-applying.

---

## Other Manifest Files

| File | Purpose |
|---|---|
| `create_pvc.yaml` | 100 GiB PVC `fl-workspace` (ReadWriteOnce); apply **once** before first pod launch — the PVC persists across pod restarts and deletions |
| `aws-credentials-secret.yaml` | Reference-only — documents the Secret structure; **never apply directly**; create with `kubectl create secret generic` (see below) |
| `c6a.2xlarge-pod.yaml` | Legacy manifest using plain `python:3.11` image (pre-Docker, pre-SSH workflow); kept for reference only |

---

## Common Commands

```bash
# One-time: create PVC (100 GiB persistent storage)
kubectl apply -f harmonization-scripts/k8s/create_pvc.yaml -n ${K8S_NAMESPACE}

# One-time: create AWS credentials Secret
kubectl create secret generic aws-credentials \
    --from-file=credentials=$HOME/.aws/credentials \
    --from-file=config=$HOME/.aws/config \
    --namespace ${K8S_NAMESPACE}

# Apply (ECR image, exec-based workflow)
kubectl apply -f harmonization-scripts/k8s/pod.yaml -n ${K8S_NAMESPACE}

# Apply (SSH workflow — paste your public key into authorized_keys first)
kubectl apply -f harmonization-scripts/k8s/pod-ssh.yaml -n ${K8S_NAMESPACE}

# Watch pod come up
kubectl get pod fl-batch-correction -n ${K8S_NAMESPACE} -w

# Follow startup logs
kubectl logs -f fl-batch-correction -n ${K8S_NAMESPACE}

# Open a shell (use bash -l for a login shell so the Python venv activates automatically)
kubectl exec -it fl-batch-correction -n ${K8S_NAMESPACE} -- bash -l

# Port-forward for SSH (keep terminal open)
kubectl port-forward pod/fl-batch-correction 2222:22 -n ${K8S_NAMESPACE}

# Delete pod only (PVC and credentials Secret persist)
kubectl delete pod fl-batch-correction -n ${K8S_NAMESPACE}

# Delete everything in the manifest (still keeps PVC and Secret)
kubectl delete -f harmonization-scripts/k8s/pod-ssh.yaml -n ${K8S_NAMESPACE}
```

---

## SSH / VSCode Workflow (pod-ssh.yaml only)

1. Replace the placeholder in `pod-ssh.yaml`'s `authorized_keys` with your `~/.ssh/id_ed25519.pub` output.
2. Apply the manifest; wait for `Running`.
3. Start port-forward on `2222:22`.
4. Add to `~/.ssh/config`:
   ```
   Host fl-pod
       HostName localhost
       Port 2222
       User root
       IdentityFile ~/.ssh/id_ed25519
       StrictHostKeyChecking no
       UserKnownHostsFile /dev/null
   ```
   (`StrictHostKeyChecking no` is intentional — host key changes on every pod restart.)
5. Sync scripts: `rsync -avz -e "ssh -p 2222 ..." harmonization-scripts/ root@localhost:/app/harmonization-scripts/`
6. VSCode → Command Palette → `Remote-SSH: Connect to Host...` → select `fl-pod`.

See `README.md` in this directory for the full setup walkthrough, OOM guidance, and troubleshooting table.

---

## aws-credentials-secret.yaml

This file is **reference-only** — it documents the Secret structure. Never apply it directly. Create the actual Secret with `kubectl create secret generic` as shown above.

---

## Inside the Pod — Running Scripts

Working directory inside both pods: `/app/harmonization-scripts`

```bash
# Smoke test (verify all 39 methods + 4 imputation approaches work)
python test_mock.py

# Two-stage pipeline (preferred — preparation runs once, normalization reuses it)
nohup python run_prep_parallel.py \
    --n-workers 4 --skip-if-exists \
    --timeout-s 7200 --memory-limit-gb 6.0 \
    > /workspace/prep.log 2>&1 &

nohup python run_norm_parallel.py \
    --n-workers 6 --skip-if-exists \
    > /workspace/norm.log 2>&1 &

# Monolithic pipeline (legacy / simpler for small targeted runs)
nohup python run_cross_product_parallel.py \
    --n-workers 6 --skip-if-exists --memory-limit-gb 12.0 \
    > /workspace/bench_run.log 2>&1 &

# Single job (debug)
python run_one_job.py \
    --strat A_confirmed_bad --imp strict --method 16_fsqn_r \
    --out-json /tmp/test.json
```

Benchmark logs and outputs go to `/workspace` (the `fl-workspace` PVC, 100 GiB) — this path persists across pod restarts.

---

## Known Startup Failures and Fixes

These bugs were encountered during pod runs. The current `pod-ssh.yaml` is pinned to commit `80adc8c` (corrected nans) — the last known-good version. Do not apply later commits from `fc761ca` onward without re-validating the startup sequence.

| Symptom | Root cause | Status |
|---|---|---|
| `ModuleNotFoundError: No module named 'numpy'` when running `python test_mock.py` | Python packages not yet installed (startup still running), or venv not active | Fixed: venv auto-activates in `.bashrc`; use `bash -l` for exec sessions |
| `pip install` → `error: externally-managed-environment` | Ubuntu 24.04 enforces PEP 668 on system Python; `--break-system-packages` is fragile | Fixed: all packages installed into `/app/venv` (no flag needed) |
| `pip install -r requirements.txt` → `procrustes-bg ... does not appear to be a Python project` | `requirements.txt` had `procrustes-bg @ git+...` but Procrustes has no `setup.py`/`pyproject.toml` | Fixed: entry removed from `requirements.txt`; Procrustes is a git clone at `/app/Procrustes`; `bench_shared.py:normalize_procrustes` adds it to `sys.path` at call time |
| `git clone` for Procrustes fails silently (no error message, module absent at runtime) | `git` was not installed in step 2; clone ran but failed; `&&` on echo meant log showed nothing | Fixed: `git` added to step 2 apt-get install |
| `pip3 install --break-system-packages --no-cache-dir -r /etc/fl-metrics-deps/requirements.txt` → `No such file` | Wrong ConfigMap mount path (`fl-metrics-deps` instead of `fl-deps`); user confusion from the metrics pod docs | Not a code bug; ConfigMap is mounted at `/etc/fl-deps/requirements.txt` |
| `Segmentation fault (core dumped)` during `test_mock.py` in method `33_amdbnorm` | `noble-cran40` CRAN apt repo now serves R 4.6.0 (released 2026-04-24); rpy2 3.6.7 has C-level ABI incompatibility with R 4.6.0's changed PROTECT/GC internals | Fixed: step 3 uses `apt-cache madison` to detect and install R 4.5.x by exact version string, then `apt-mark hold` prevents upgrade to 4.6.x |
| `DWD failed for batch '...': unused argument (penalty = "auto")` — all non-reference batches uncorrected | `DWDLargeR::genDWD` removed the `penalty` argument in a recent CRAN release | Fixed: `penalty = "auto"` removed from `normalize_dwd` call in `bench_shared.py:1843`; penalty is now computed internally by default |
| `reComBat MISSING` and `FAbatch MISSING` in `test_mock.py` R packages section | Wrong package names in `_CRITICAL_PKGS`: `reComBat` is a Python package (not R); `FAbatch` does not exist — the actual R package is `bapred` | Fixed: `reComBat` removed; `FAbatch` replaced with `bapred` in `test_mock.py` |
| R installation fails: `r-base : Depends: r-recommended (= 4.5.3-1.2404.0) but 4.6.0-2.2404.0 is to be installed` followed by `rpy2 in API mode cannot be built without R in the PATH` | CRAN noble-cran40 removes `r-recommended=4.5.3` when a new minor version ships; `r-base=4.5.3` has an exact-version dependency on it, so apt cannot satisfy the dependency chain — R is never installed, rpy2 build fails, all `Rscript` calls fail | Fixed: step 3 replaced with Posit standalone binary (`wget cdn.posit.co/r/ubuntu-2404/pkgs/r-4.5.3_1_amd64.deb`); installs to `/opt/R/4.5.3/`, bypasses CRAN apt entirely |
| `[startup] WARNING: FSQN or qsmooth verification failed` — `qsmooth` not installed | `Hmisc` (a qsmooth dep) failed to compile because `libpng-dev` was absent from step 2; BiocManager silently skipped qsmooth | Fixed: `libpng-dev zlib1g-dev` added to step 2 apt list; `quantreg`/`Hmisc`/`lme4` pre-installed before BiocManager qsmooth call; `force=TRUE` added |
| `36_explobatch` runtime error about missing `fMM` package | GitHub repo `maxkuhn/fMM` deleted (HTTP 404); fMM is a hard runtime dep of exploBATCH | Fixed: fMM install line removed from step 5; `normalize_explobatch` raises `NotImplementedError` → clean SKIP |
| `ModuleNotFoundError: No module named 'numpy'` — pip install aborted entirely | `reComBat 0.1.4` (GitHub URL) requires `pandas<2.0`; ConfigMap had `pandas>=2.0,<3.0`; pip `ResolutionImpossible` aborts before writing any package. Forcing `pandas<2.0` on Python 3.12 also fails — no pre-built wheel for py3.12, source build fails with Cython incompatibilities | **DEAD END — do not try**: step 2 installs `python3.11 python3.11-venv python3.11-dev` but python3.11 is NOT in Ubuntu 24.04's universe repo — `apt-get` fails with `E: Unable to locate package python3.11`. This caused 22+ CrashLoopBackOff restarts (2026-05-10, attempt 3). Root cause: only python3.12 ships in noble/main and noble/universe; python3.11 requires the `deadsnakes` PPA which was not added. **Reverted to 80adc8c which uses system python3 (3.12) with `--break-system-packages`.** |
