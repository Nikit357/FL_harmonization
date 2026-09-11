# Kubernetes Pod — FL Batch Effect Metrics

Runs the comprehensive batch effect metrics pipeline on all harmonized expression files stored in S3.
The pod starts from `ubuntu:24.04`, installs Python + R 4.5 + `variancePartition` at startup, and exposes an SSH server for code sync via rsync.

**First startup takes ~10–20 minutes** (R `variancePartition` + Bioconductor dependencies compile time). SSH becomes available within the first ~2 minutes.

---

## Prerequisites

| Tool | How to get it |
|---|---|
| `kubectl` configured for `${K8S_NAMESPACE}` | Ask DevOps for the kubeconfig |
| VSCode **Remote - SSH** extension | `ms-vscode-remote.remote-ssh` |
| An SSH key pair on your laptop | See Step 1 below |

---

## Getting just this folder (sparse checkout)

The repository is ~1.3 GB, almost all of it figures and notebooks. This folder holds everything
needed to launch the pod and run the metrics compute — ~5 MB. To clone only it:

```bash
git clone --filter=blob:none --no-checkout https://github.com/Nikit357/FL_harmonization
cd FL_harmonization
git sparse-checkout init --cone
git sparse-checkout set harmonization-metrics-calculation
git checkout main
```

To add a second directory later (for example the analysis notebooks and metric tables):

```bash
git sparse-checkout add harmonization-metrics
```

Turn it off and get everything with `git sparse-checkout disable`.

---

## One-time setup (do this once per machine)

### Step 1 — Generate an SSH key (skip if you already have one)

```bash
ssh-keygen -t ed25519 -C "author@example.com"
cat ~/.ssh/id_ed25519.pub
```

### Step 2 — Create the SSH public key Secret

The key is **not** stored in `k8s/pod-metrics.yaml` — that keeps a personal identifier out of the repository and lets anyone apply the manifest with their own key. Create the Secret once:

```bash
kubectl create secret generic ssh-pubkey \
    --from-file=authorized_keys=$HOME/.ssh/id_ed25519.pub \
    --namespace ${K8S_NAMESPACE}
```

To rotate the key, delete and recreate the Secret, then restart the pod.

### Step 3 — Create the AWS credentials Secret (skip if it already exists)

```bash
kubectl create secret generic aws-credentials \
    --from-file=credentials=$HOME/.aws/credentials \
    --from-file=config=$HOME/.aws/config \
    --namespace ${K8S_NAMESPACE}

kubectl get secret aws-credentials -n ${K8S_NAMESPACE}
```

---

## Launching the pod

### Step 4 — Apply the manifest

Run from the **repository root**:

```bash
kubectl apply -f harmonization-metrics-calculation/k8s/pod-metrics.yaml -n ${K8S_NAMESPACE}
```

### Step 5 — Wait for environment to be ready (~10–20 min)

```bash
kubectl get pod fl-metrics -n ${K8S_NAMESPACE} -w
```

Once status shows `Running`, SSH is available within ~2 minutes. R packages continue installing in the background.

Follow startup logs:

```bash
kubectl logs -f fl-metrics -n ${K8S_NAMESPACE}
```

The log prints `[startup] Metrics environment ready.` when all packages are installed. Do not run scripts until you see this message.

---

## Connecting via SSH

### Step 6 — Start port forwarding (keep this terminal open)

```bash
kubectl port-forward pod/fl-metrics 2222:22 -n ${K8S_NAMESPACE}
```

### Step 7 — Add the pod to your SSH config

Open (or create) `~/.ssh/config` and add:

```
Host metrics-pod
    HostName localhost
    Port 2222
    User root
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
```

Test the connection:

```bash
ssh metrics-pod
```

---

## Syncing scripts to the pod

### rsync (recommended)

From your local Mac (with port forwarding active on `localhost:2222`):

```bash
rsync -avz --progress \
    -e "ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
    ~/FL_harmonization/harmonization-metrics-calculation/ \
    root@localhost:/app/harmonization-metrics-calculation/
```

Re-run after any local edit to push changes.

Sync the **whole directory**, not `*py`: a `*py` glob leaves `marker_gene_annotation.csv` behind,
and metric groups L and M need it. The directory is ~5 MB, so there is nothing to gain by
narrowing the glob.

### kubectl cp (no SSH needed)

```bash
kubectl cp harmonization-metrics-calculation/. \
    ${K8S_NAMESPACE}/fl-metrics:/app/harmonization-metrics-calculation/
```

---

## Running the metrics pipeline

All commands run **inside the pod** (via SSH or `kubectl exec`):

```bash
kubectl exec -it fl-metrics -n ${K8S_NAMESPACE} -- bash
cd /app/harmonization-metrics-calculation
```

### Step 8 — Smoke test (verify the environment)

```bash
python test_mock_metrics.py
```

Expected output: all tests pass, exit code 0. This confirms Python packages, `compute_batch_metrics.py`, and R (`variancePartition` is skipped by `skip_slow=True`) are working correctly.

### Step 9 — Single-job test (verify S3 access and end-to-end pipeline)

Run one job manually before launching the full dispatcher:

```bash
python run_metrics_job.py \
    --strat A_confirmed_bad \
    --imp strict \
    --method 16_fsqn_r \
    --post-rm False \
    --out-json /tmp/test_metrics.json \
    --out-genes-json /tmp/test_genes.json \
    --skip-slow
```

Inspect the output:

```bash
python -c "import json; d=json.load(open('/tmp/test_metrics.json')); print(list(d.keys())[:20])"
python -c "import json; d=json.load(open('/tmp/test_metrics.json')); print(d.get('status'), d.get('n_samples'), d.get('r2_RNA_BATCH'))"
```

### Step 10 — Full dispatcher run (post0 only, fast mode)

```bash
nohup python run_metrics_parallel.py \
    --n-workers 4 \
    --skip-if-exists \
    --skip-slow \
    --post-rm-filter post0 \
    --memory-limit-gb 6.0 \
    > /workspace/metrics_fast.log 2>&1 &

tail -f /workspace/metrics_fast.log
```

### Step 10b — Full run with variancePartition (slow, production)

```bash
nohup python run_metrics_parallel.py \
    --n-workers 2 \
    --skip-if-exists \
    --post-rm-filter post0 \
    --memory-limit-gb 8.0 \
    --timeout-s 3600 \
    > /workspace/metrics_full.log 2>&1 &
```

Use `--n-workers 2` with `--timeout-s 3600` for variancePartition runs — each job can take up to 30 minutes.

### Step 10c — Targeted subset

```bash
python run_metrics_parallel.py \
    --strats A_confirmed_bad \
    --imps strict \
    --methods 01_raw,16_fsqn_r,17_quantile \
    --post-rm-filter post0 \
    --skip-slow \
    --n-workers 4
```

### Step 10d — Resume after failure

```bash
# Retry only previously failed jobs
python run_metrics_parallel.py \
    --n-workers 4 --skip-slow --retry-failed --post-rm-filter post0
```

Failed jobs are tracked in `failed_jobs_metrics.txt` and synced to S3 at startup/shutdown.

### Step 10e — Blind final check (metric groups L, M, N)

Groups L (marker correlation preservation), M (cross-batch rank agreement) and N (predictive
validation) are added to attempts that already have a metrics sidecar. Their keys land in the
same JSON files and the same `metrics_comprehensive.csv`, but are excluded from the Figure 3
clustermap and the composite score by a prefix filter in `figures_helpers.py`.

```bash
# Do NOT pass --skip-if-exists: every target job already has a sidecar, so it would skip
# all of them. The worker's incremental sentinel logic provides the resume behaviour.
# Set --n-workers to roughly (vCPU - 8) on the node you provisioned.
# n_perm=100 timed out every job at 3600s on 2026-08-23. Root cause: BLAS/OpenMP threads
# were not actually pinned in the live worker process (the k8s manifest's env vars don't
# reach an SSH-launched process), so each worker fanned out to ~48 threads; 20 workers on
# a 32-core cgroup quota meant severe oversubscription. Thread pinning now happens inside
# run_metrics_job.py itself. n_perm=20 is kept as an additional safety margin. See
# group_n_timeout_and_reference_race_fix_plan_260823.md for the full diagnosis.
nohup python run_metrics_parallel.py \
    --groups L,M,N --only-with-metrics --skip-shambhala \
    --n-workers 20 --memory-limit-gb 8.0 --timeout-s 3600 \
    --n-perm 20 --ref-cache-dir /workspace/ref_cache \
    > /workspace/metrics_lmn.log 2>&1 &
```

**Reference cache.** Group L compares each attempt against its unharmonized
`01_raw__post0` matrix. Those are cached at `--ref-cache-dir` (default
`/workspace/ref_cache`) — 42 `(strat, imp)` pairs, roughly **12.8 GB** on the PVC. Check the
PVC has room before starting, and delete the cache directory if the `01_raw` outputs are ever
regenerated: a stale cache would silently compare against the wrong reference. Each cache hit
logs the S3 ETag so a mismatch is visible in the log.

Groups M and N need no reference and do no extra I/O; `--groups M,N` skips the cache entirely.

### Step 10f — Force-recompute a single group with different parameters

To rerun a group that already has a result in every target sidecar — for example, redoing
Group N with a higher `--n-perm` for finer p-value resolution — pass `--force-groups` alongside
`--groups` for the same letters. Every other group already in each sidecar (A–M) is left exactly
as-is; only the forced group's keys are overwritten.

```bash
nohup python run_metrics_parallel.py \
    --groups N --force-groups N --only-with-metrics --skip-shambhala \
    --n-workers 20 --memory-limit-gb 8.0 --timeout-s 3600 \
    --n-perm 200 \
    > /workspace/metrics_n_reforce.log 2>&1 &
```

Do not pass `--skip-if-exists` here either, for the same reason as Step 10e: every target job
already has a sidecar, so it would skip the job before `--force-groups` ever gets a chance to act.

### Step 10g — Add the Group L narrow-panel aggregates

Group L reports a second family of integrative aggregates over the 56-gene QC-filtered narrow
panel (`in_narrow_set` in `marker_gene_annotation.csv`), every key suffixed `_narrow_set`. It is
computed from the same correlation pass as the full-panel family, so this run costs no more than
a plain Group L run. Sidecars written before 2026-09-04 have the full-panel keys only.

```bash
nohup python run_metrics_parallel.py \
    --groups L --skip-wm --only-with-metrics --skip-shambhala \
    --n-workers 20 --memory-limit-gb 8.0 --timeout-s 1800 \
    --ref-cache-dir /workspace/ref_cache \
    > /workspace/metrics_l_narrow.log 2>&1 &
```

Three flag notes, all of which matter:

- **No `--skip-if-exists`**, for the same reason as Steps 10e and 10f — every target job already
  has a sidecar and would be skipped whole.
- **No `--force-groups`** either. Group L's sentinel is now the *pair*
  (`mk_rho_mean_all_genes`, `mk_rho_mean_all_genes_narrow_set`), and a group counts as complete
  only when both keys are populated, so the incremental check schedules Group L on its own and
  stops scheduling it once the narrow keys land. Forcing would re-run finished jobs on a restart.
- **Pass `--skip-wm`.** Without it the worker adds Group I to the requested set
  (`if not args.skip_wm: requested_groups.add("I")`); harmless where `wm_RNA_BATCH` already
  exists, but it would spend 2–5 min computing a WaterMelon score on any job that lacks it.

The reference cache is needed exactly as in Step 10e (~12.8 GB at `--ref-cache-dir`). Runtime is
dominated by downloading each harmonized matrix, roughly 1–3 min per job, so about 2–4 h at
20 workers over the 2,323 non-Shambhala attempts.

After Step 11, `metrics_comprehensive.csv` carries **30** `mk_` columns (15 full-panel + 15
narrow). The long tables must come out unchanged — the narrow family is integrative only, and
`mk_rho_by_gene` / `mk_rho_by_cohort` stay restricted to the requested panel. Diff the
regenerated `marker_gene_correlations_long_*.csv` against the previous snapshot and stop to
investigate if it moved.

### Step 11 — Aggregate results

After all (or most) jobs complete, aggregate all JSON sidecars into a single CSV:

```bash
python run_metrics_concat.py
```

This uploads `FL_batch_correction/metrics_comprehensive.csv` to S3, plus three long-format
tables once groups L/M/N have run: `marker_gene_correlations_long.csv`,
`marker_cohort_correlations_long.csv` and `prediction_folds_long.csv`. Those hold the per-gene,
per-cohort and per-fold detail that cannot be a scalar column in the wide table.

To also save a local copy:

```bash
python run_metrics_concat.py --out-csv /workspace/metrics_comprehensive.csv
```

Or write all four tables into one folder with a date postfix, which is the form the
analysis side expects (`metrics_comprehensive_260827.csv` and so on):

```bash
python run_metrics_concat.py --out-dir /workspace/metric_tables --date-tag 260827
```

### Step 11b — Marker panel deep analysis (optional)

`gene_panel_analysis/` is a separate sub-pipeline that computes gene × gene correlation
matrices and per-gene expression QC for the marker panel. It runs in this same pod and is
already covered by the sparse checkout and the rsync above — no extra setup. It writes its
own S3 prefixes and adds no column to `metrics_comprehensive.csv`.

```bash
cd gene_panel_analysis
python test_mock_gene_structure.py
python run_gene_corr_parallel.py --only-with-metrics --post-rm-filter post0 --dry-run
```

See `gene_panel_analysis/README.md` for the full run book, the analysis scope, the `.npz`
payload layout and troubleshooting.

### Step 12 — Download results to local machine

From your local Mac:

```bash
aws s3 cp \
    s3://$FL_S3_BUCKET/FL_batch_correction/metrics_comprehensive.csv \
    ~/FL_harmonization/metrics_comprehensive.csv
```

Or via rsync from the pod (if you saved a local copy in Step 11):

```bash
rsync -avz --progress \
    -e "ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
    root@localhost:/workspace/metrics_comprehensive.csv \
    ~/FL_harmonization/
```

---

## Teardown

```bash
# Delete just the pod (keeps ConfigMap and PVC)
kubectl delete pod fl-metrics -n ${K8S_NAMESPACE}

# Delete everything in the manifest (still keeps PVC and credentials Secret)
kubectl delete -f harmonization-metrics-calculation/k8s/pod-metrics.yaml -n ${K8S_NAMESPACE}
```

The PVC (`fl-workspace`) and `aws-credentials` Secret are **not** deleted — data and credentials persist.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Pod stuck in `Pending` | `kubectl describe pod fl-metrics -n ${K8S_NAMESPACE}` — check `Events:` for capacity or missing Secret errors |
| Pod phase `Failed`, exit code 137 | OOM kill — reduce `--n-workers` or increase `--memory-limit-gb` |
| `ssh: connect to host localhost port 2222: Connection refused` | Port forward is not running; restart Step 6 |
| `Permission denied (publickey)` | Public key in the `ssh-pubkey` Secret doesn't match `~/.ssh/id_ed25519`; recreate the Secret, then run `kubectl exec ... -- cp /etc/ssh-init/authorized_keys /root/.ssh/authorized_keys` |
| `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED` | Pod restarted; run `ssh-keygen -R "[localhost]:2222"` |
| `rsync: mkdir ... failed: No such file or directory` | Working directory not yet created — startup is still running. Create manually: `ssh -p 2222 root@localhost "mkdir -p /app/harmonization-metrics-calculation"` |
| `variancePartition` R errors | Check `kubectl logs fl-metrics` for `[startup] variancePartition verified OK`; if missing, reinstall manually (see below) |
| All metrics return `null` with no error | Check that `[startup] Metrics environment ready.` appears in logs before running scripts |

### Manually installing missing R packages

```bash
ssh metrics-pod
Rscript --no-save --no-restore -e "
  pkgs <- c('variancePartition', 'BiocParallel')
  cat('Missing:', paste(pkgs[!sapply(pkgs, requireNamespace, quietly=TRUE)], collapse=', '), '\n')
"
Rscript --no-save --no-restore -e "BiocManager::install(c('variancePartition', 'BiocParallel'), ask=FALSE, update=FALSE)"
Rscript --no-save --no-restore -e "library(variancePartition); cat('OK\n')"
```

### Out-of-memory (OOMKilled / exit code 137)

With `--skip-slow` (no variancePartition), each worker uses ~2–4 GB. With variancePartition enabled, each worker can peak at 6–8 GB.

**Safe parameters for 128 GiB pod:**

```bash
# Fast mode — up to 8 workers
nohup python run_metrics_parallel.py \
    --n-workers 8 --skip-if-exists --skip-slow \
    --memory-limit-gb 6.0 > /workspace/metrics_fast.log 2>&1 &

# Full mode with variancePartition — limit concurrency
nohup python run_metrics_parallel.py \
    --n-workers 4 --skip-if-exists \
    --memory-limit-gb 10.0 --timeout-s 3600 \
    > /workspace/metrics_full.log 2>&1 &
```

After an OOM crash, delete and re-apply the pod:

```bash
kubectl delete pod fl-metrics -n ${K8S_NAMESPACE}
kubectl apply -f harmonization-metrics-calculation/k8s/pod-metrics.yaml -n ${K8S_NAMESPACE}
```

> Redirect logs to `/workspace/` (the persistent PVC) so they survive a pod crash.
