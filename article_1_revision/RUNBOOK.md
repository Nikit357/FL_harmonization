# RUNBOOK — Article 1 revision pods (run from the Mac)

> **Pod names** end with the pinned instance type (the project's pod-naming rule): `fl-revision`, `fl-metrics`. Commands find the pod by its stable label `app=<name without the type>`: `$POD_REV` = `$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-revision -o name | cut -d/ -f2)`; `$POD_METRICS` = `$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-metrics -o name | cut -d/ -f2)`. Resize = edit the manifest's `node.kubernetes.io/instance-type` and the name suffix together; launch with `kubectl apply -f <manifest>`.

Plan: `article_1_revision_implementation_plan_261029.md`, §6–§7. Everything below runs **on the
Mac** in `~/FL_harmonization`, unless a block says **inside the pod**.
Namespace: `${K8S_NAMESPACE}`.

Two pods, **never at the same time** (they share the main PVC, `fl-a3-scratch-150`):

| Pod | Manifest | What runs there | How you get in |
|---|---|---|---|
| `fl-revision` (harmonization; PVC-free variant also the pilot metrics) | `article_1_revision/k8s/pod-revision.yaml` or `pod-revision-nopvc.yaml` (both 44 vCPU / 80 GiB on a 48-vCPU c6a.12xlarge since G3; the pilots ran on 14 / 24 GiB); ComboBatch image `ghcr.io/nikit357/combobatch:20260830` (environment only) + `Shambhala2_fast` @ `30ac312` | `r18_env_check.py`, `r11_run_gradient.py`, `r21_run_v1.py` (worker `r19_harmonize_one.py`); pilot: also `r12_revision_metrics.py --pilot` | `kubectl exec` + `tar` copy |
| `fl-metrics` (metrics) | `harmonization-metrics-calculation/k8s/pod-metrics.yaml` (unchanged) | full runs: `r12_revision_metrics.py`, `r30_bridging_subset_metrics.py` (pod decided at G3) | SSH through a port-forward, `rsync` |

The ECR image `fl-batch-correction:latest` is NotFound since 2026-11-01; both revision manifests
use the ComboBatch image (plan `revision_pod_combobatch_image_plan_261101.md`). The image is only
the environment: the frozen code is copied in (§3), and `20_shambhala` runs `Shambhala2_fast`
(the published implementation) through `revision_lib.shambhala_fast`.

Every input and output goes through S3
(`s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/{gradient,v1,bridging}/`),
so nothing is moved between the pods. Logs and caches live on the PVC in `/workspace/revision/`
(PVC-free pod: logs on S3 `revision_261029/pod_logs/`, caches dropped with the pod).

**While the annotation 3.0 pod holds the PVC**, start the harmonization pod from
`article_1_revision/k8s/pod-revision-nopvc.yaml` (no PVC, scratch on the node, logs saved on S3;
see §4b). It may run next to the a3 pod. Plan: `revision_pod_without_pvc_plan_261101.md`.

Order: **cycle 1 = pilots** (§1–§5), then Claude on JupyterHub builds the gate G3 report;
**cycle 2 = full runs** (§6) after G3.

---

## 1. One-time checks

```bash
kubectl get pods -n ${K8S_NAMESPACE}                                   # kubectl works
kubectl get secret aws-credentials ssh-pubkey -n ${K8S_NAMESPACE}
kubectl get pvc fl-a3-scratch-150 -n ${K8S_NAMESPACE}        # the main PVC
aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/ | head
```

Missing Secret → create it with the commands in `harmonization-scripts/k8s/CLAUDE.md` /
`harmonization-metrics-calculation/CLAUDE.md` ("Pod Operations").

## 2. Before every launch: fresh code and a free volume

```bash
cd ~/FL_harmonization
git pull --rebase origin main
ls article_1_revision/r11_run_gradient.py \
   article_1_revision/output/wp6/designs/designs.tsv \
   article_1_revision/output/wp7/fold_samples.tsv              # all three must exist

kubectl get pods -n ${K8S_NAMESPACE} | grep fl-             # nothing else may hold the PVC
kubectl describe pvc fl-a3-scratch-150 -n ${K8S_NAMESPACE} | grep -A3 "Used By"
# another pod listed and finished →  kubectl delete pod <that-pod> -n ${K8S_NAMESPACE}
# (skip the PVC check when you use pod-revision-nopvc.yaml)
```

## 3. Harmonization pod: launch and copy the code

```bash
kubectl apply -f article_1_revision/k8s/pod-revision.yaml      # rule check + kubectl apply
POD_REV=$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-revision -o name | cut -d/ -f2)
#   or, while the a3 pod holds the PVC:
#   kubectl apply -f article_1_revision/k8s/pod-revision-nopvc.yaml
kubectl get pod $POD_REV -n ${K8S_NAMESPACE} -w        # wait for Running, Ctrl-C
# start-up (seconds after the ~5 GB image pull): expect R 4.5.3,
# "[startup] Shambhala2_fast 30ac312 OK" and "[startup] ready"
kubectl logs $POD_REV -c worker -n ${K8S_NAMESPACE} | grep startup
# PVC-free pod: log saving started? expect "log-sync -> s3://…"
kubectl logs $POD_REV -c log-sync -n ${K8S_NAMESPACE}
# (the PVC-free pod has two containers: `-c worker` selects the one that runs the jobs;
#  kubectl exec without -c also opens worker, the first container)

# the revision folder (scripts, tests, inputs, designs, folds; no caches / manuscript /
# parquet), the frozen bench_shared.py (the image does not carry it) and the metrics code
tar -C ~/FL_harmonization -cf - \
    --exclude='article_1_revision/cache' --exclude='article_1_revision/Revised_manuscript' \
    --exclude='article_1_revision/figures_svg' --exclude='*.parquet' --exclude='.ipynb_checkpoints' \
    article_1_revision harmonization-scripts/bench_shared.py harmonization-metrics-calculation \
  | kubectl exec -i $POD_REV -c worker -n ${K8S_NAMESPACE} -- tar -xf - -C /app

# the copied bench_shared.py must be the frozen one → "…bench_shared.py: OK"
kubectl exec $POD_REV -c worker -n ${K8S_NAMESPACE} -- \
    sh -c 'cd /app/article_1_revision && grep bench_shared FROZEN_MD5.txt | md5sum -c -'
```

## 4. Harmonization pod: the two pilots

```bash
POD_REV=$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-revision -o name | cut -d/ -f2)
kubectl exec -it $POD_REV -c worker -n ${K8S_NAMESPACE} -- bash -l
```

**Inside the pod:**

```bash
cd /app/article_1_revision
mkdir -p /workspace/revision
python -m pytest tests/ -q                         # pytest is in the image; must pass
python r11_run_gradient.py --pilot --dry-run       # "24 harmonization jobs planned"
python r21_run_v1.py --pilot --dry-run             # "62 harmonization jobs planned"

# environment check (~10–15 min): four frozen methods + Shambhala vs the published matrices
python r18_env_check.py 2>&1 | tee /workspace/revision/env_check.log
# last line must be "ENV CHECK: OK"; on "STOP" do not start the pilots, report at G3

# gradient pilot (λ = 0 and λ = 1, replicate 1, cap 150, 12 arms); setsid + nohup survive logout
setsid nohup python r11_run_gradient.py --pilot --skip-if-exists --n-workers 4 \
    > /workspace/revision/gradient_pilot.log 2>&1 &
exit
```

Watch from the Mac:

```bash
POD_REV=$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-revision -o name | cut -d/ -f2)
kubectl exec $POD_REV -c worker -n ${K8S_NAMESPACE} -- tail -n 20 /workspace/revision/gradient_pilot.log
aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/gradient/runs/ | wc -l   # → 24
# PVC-free pod, without kubectl (≤ 60 s behind; <folder> from §4b):
aws s3 cp s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/pod_logs/<folder>/gradient_pilot.log - | tail -n 20
```

The first run downloads the raw matrix (~2 GB) once and caches it in
`/workspace/revision/cache/bench_comb_data.pkl`. The log ends with `SUMMARY harmonize: 24 jobs — …`.
A method failure (e.g. ComBat with the diagnosis covariate at λ = 1) is a **result**: it shows as
`ok` in the dispatcher (the worker exited cleanly) and the reason is in the S3 run record.

Then the leave-cohort-out pilot (strategy C, fold 1, training + test, 31 methods), the same way:

```bash
POD_REV=$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-revision -o name | cut -d/ -f2)
kubectl exec -it $POD_REV -c worker -n ${K8S_NAMESPACE} -- bash -l
cd /app/article_1_revision
setsid nohup python r21_run_v1.py --pilot --skip-if-exists --n-workers 4 \
    > /workspace/revision/v1_pilot.log 2>&1 &
exit
# … wait for "SUMMARY harmonize: 62 jobs", then:
#   PVC-free pod → the metrics pilot in the same pod (§5);
#   PVC pod      → kubectl delete pod $POD_REV -n ${K8S_NAMESPACE}, then §5b
```

The two pilots run one after the other so that their run times are measured cleanly.

## 4b. PVC-free pod: logs on S3

`pod-revision-nopvc.yaml` has a second container, `log-sync`, that mirrors `/workspace/revision`
(without `cache/`) to S3 every 60 s and once more when the pod is deleted (`kubectl delete pod`
then takes up to 90 s). One folder per pod start, `<pod>_<YYMMDD_HHMM UTC>`:

```bash
POD_REV=$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-revision -o name | cut -d/ -f2)
# list the log folders (one per pod start)
aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/pod_logs/
# read / fetch one run's logs on the Mac or on JupyterHub
aws s3 sync s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/pod_logs/<folder>/ \
    article_1_revision/cache/pod_logs/<folder>/
# deleting the pod runs a final sync; confirm it:
kubectl delete pod $POD_REV -n ${K8S_NAMESPACE}
aws s3 cp s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/pod_logs/<folder>/v1_pilot.log - | tail -n 3
```

(`article_1_revision/cache/` is git-ignored.) The caches (raw matrix, prepared subsets) die with
the pod; a relaunch downloads them again.

## 5. Pilot metrics in the same PVC-free pod (Part B)

The ComboBatch image has every metric dependency (variancePartition, umap, statsmodels), and
§3 copied `harmonization-metrics-calculation/`. After `SUMMARY harmonize: 62 jobs`:

```bash
POD_REV=$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-revision -o name | cut -d/ -f2)
kubectl exec -it $POD_REV -c worker -n ${K8S_NAMESPACE} -- bash -l
cd /app/article_1_revision
python r12_revision_metrics.py --pilot --dry-run   # "86 metric jobs planned; … have a harmonized matrix"
setsid nohup python r12_revision_metrics.py --pilot --skip-if-exists \
    --n-workers 8 --memory-limit-gb 3.0 \
    > /workspace/revision/metrics_pilot.log 2>&1 &
exit
```

When the log ends with `SUMMARY metrics`, delete the pod (§4b: the final log sync runs) and tell
Claude on JupyterHub: **"the pilots are done"**.

## 5b. Alternative: the SSH metrics pod (needs the PVC)

```bash
kubectl apply -f harmonization-metrics-calculation/k8s/pod-metrics.yaml
POD_METRICS=$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-metrics -o name | cut -d/ -f2)
kubectl logs -f $POD_METRICS -n ${K8S_NAMESPACE}
# wait for "[startup] Metrics environment ready." (10–20 min), Ctrl-C

# Terminal 2 (keep open)
kubectl port-forward pod/$POD_METRICS 2222:22 -n ${K8S_NAMESPACE}

# Terminal 1: whole folders (group L needs marker_gene_annotation.csv)
for d in harmonization-metrics-calculation article_1_revision; do
  rsync -avz --exclude='cache/' --exclude='Revised_manuscript/' --exclude='*.parquet' \
      --exclude='.ipynb_checkpoints/' \
      -e "ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
      ~/FL_harmonization/$d/ root@localhost:/app/$d/
done
ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@localhost
```

**Inside the pod:**

```bash
cd /app/article_1_revision
mkdir -p /workspace/revision
python r12_revision_metrics.py --pilot --dry-run   # "86 metric jobs planned; 86 have a harmonized matrix"
setsid nohup python r12_revision_metrics.py --pilot --skip-if-exists \
    --n-workers 8 --memory-limit-gb 8.0 \
    > /workspace/revision/metrics_pilot.log 2>&1 &
exit
```

`--n-workers` ≈ (vCPU − 8) of the node that was provisioned. Group D (KS tests) is the slowest group (~20 min per 405-sample matrix on one busy JupyterHub core); its pilot time decides at G3 whether the full runs use `--groups ABCEGHIJKLN`. (A metric job whose method failed has
no matrix and is not listed — 86 is the maximum.) When the log ends with `SUMMARY metrics`, delete
the pod (`kubectl delete pod $POD_METRICS -n ${K8S_NAMESPACE}`) and tell Claude on
JupyterHub: **"the pilots are done"**. The gate G3 report (run times per method, the decision-D8
fallback, the covariate-free wrappers, the node size for the full runs) is built there.

## 6. Full runs (gate G3 answered 2026-11-03)

G3 decisions behind these commands (`gates_review_261102.md` §5): every method kept except
exploBATCH in leave-cohort-out (fMM is not in the image; `r21` drops `36_explobatch` by default
→ 30 methods); **6 h per run** (`--timeout-s 21600`, the default; a run over it is written to S3
as a "timeout" record and never restarted by `--skip-if-exists`); **one 48-vCPU / 96-GiB node
(c6a.12xlarge) for everything**, harmonizations and metrics in the same PVC-free pod (both
manifests request 44 CPU / 80 GiB and pin `node.kubernetes.io/instance-type: c6a.12xlarge`); group D kept.

Expected job counts (dry-runs on JupyterHub, 2026-11-03, pilot runs already on S3):
gradient 540 planned / **516 to run** (43 preparations); leave-cohort-out 1,200 planned /
**1,141 to run** (C 241, K 300, J 300, S0 300); metrics 540 + up to 1,200; bridging 2,234.

### 6.1 Launch (Mac)

§2 (git pull) → §3 with **`pod-revision-nopvc.yaml`** (no PVC needed; logs on S3, §4b). Karpenter
needs a few minutes for the 48-vCPU node. Inside the pod, first:

```bash
cd /app/article_1_revision && mkdir -p /workspace/revision
python -m pytest tests/ -q                                   # 88 passed
python r11_run_gradient.py --dry-run --skip-if-exists         # "to run now: 43 preparations, 516 harmonizations"
python r21_run_v1.py --dry-run --skip-if-exists               # "1200 … planned"; "1141 harmonizations"
nproc; free -g                                               # expect 44 CPUs, ~80 GiB
```

### 6.2 Harmonizations (inside the pod, one command, leaves the shell)

```bash
setsid nohup sh -c '
  python r11_run_gradient.py --skip-if-exists --n-workers 36 --n-prep-workers 4 \
      --memory-limit-gb 4 > /workspace/revision/gradient_full.log 2>&1
  for s in C K J; do
    python r21_run_v1.py --scenario $s --skip-if-exists --n-workers 20 --n-prep-workers 4 \
        --memory-limit-gb 8 > /workspace/revision/v1_$s.log 2>&1
  done
  python r21_run_v1.py --scenario S0 --skip-if-exists --n-workers 5 --n-prep-workers 2 \
      --memory-limit-gb 20 > /workspace/revision/v1_S0.log 2>&1
' > /workspace/revision/full_runs.log 2>&1 &
exit
```

Why these numbers: the gradient designs are 405–2,068 samples (≤ 2 GB per job), so 36 workers
fit; the C / K / J training parts are ~1,800–2,500 samples; the S0 training parts ~5,700 samples
(3× the pilot) and Shambhala uses 16 threads by itself, hence 5 workers and 20 GB free memory
before each start (10 workers / 14 GB were OOMKilled at 80 GiB on 2026-11-04, 20 min into S0:
the free-memory check only gates the start, jobs grow afterwards). The dispatcher waits for memory, so a too-high `--n-workers` only slows the
start of jobs. AMDBNorm / HarmonizR / Shambhala on S0 training parts may take hours; at 6 h they
are recorded as "timeout".

Watch (Mac): `aws s3 cp s3://…/revision_261029/pod_logs/<folder>/gradient_full.log - | tail`
(then `v1_C.log` … `v1_S0.log`); each log ends with `SUMMARY harmonize: …`.

### 6.3 Metrics in the same pod (after `SUMMARY harmonize` of `v1_S0.log`)

```bash
POD_REV=$(kubectl get pod -n ${K8S_NAMESPACE} -l app=fl-revision -o name | cut -d/ -f2)
kubectl exec -it $POD_REV -c worker -n ${K8S_NAMESPACE} -- bash -l
cd /app/article_1_revision
python r12_revision_metrics.py --experiment gradient --dry-run --skip-if-exists
setsid nohup sh -c '
  python r12_revision_metrics.py --experiment gradient --skip-if-exists \
      --n-workers 36 --memory-limit-gb 3 --timeout-s 7200 > /workspace/revision/metrics_gradient.log 2>&1
  python r12_revision_metrics.py --experiment leave_cohort_out --skip-if-exists \
      --n-workers 16 --memory-limit-gb 8 --timeout-s 7200 > /workspace/revision/metrics_v1.log 2>&1
  python r30_bridging_subset_metrics.py --skip-if-exists \
      --n-workers 16 --memory-limit-gb 8 --timeout-s 7200 > /workspace/revision/bridging.log 2>&1
' > /workspace/revision/full_metrics.log 2>&1 &
exit
```

The bridging check (2,234 jobs on the published matrices, up to 7,174 samples) is the longest
step. The metrics can also be started earlier for the gradient alone, while the leave-cohort-out
harmonizations still run, if CPUs are free (`top`); they use other S3 prefixes.

### 6.4 After the runs

Delete the pod (`kubectl delete pod $POD_REV -n ${K8S_NAMESPACE}`; the final log sync
runs) and tell Claude on JupyterHub: **"the full runs are done"**. Claude then runs `r12 --concat`
(both experiments), `r30 --concat`, `r13_gradient_stats.py`, and, after the rule freeze and G2b,
`r22_v1_evaluate.py` and `r05_robustness.py` (gate G4).

Every dispatcher is restartable: re-launch the pod, copy the code again (§3) and run the same
command; `--skip-if-exists` skips every job whose output (or timeout record) is already on S3.

### 6.5 Angel and M-ComBat in the gradient (gate G4, 2026-11-07)

Daniil decided at G4 that the two selected methods missing from the gradient, Angel and M-ComBat,
are run on the same 45 designs. Only these 90 harmonizations + 90 metric jobs run: every
preparation and the 540 earlier runs are on S3, and `--skip-if-exists` skips them (dry-run on
JupyterHub 2026-11-07: "45 subsets × 14 arms = 630 planned; to run now: 0 preparations, 90
harmonizations"). Expected time: < 1 h harmonization (both methods take seconds to minutes on
405–2,068 samples) + ~1–2 h metrics (group D dominates).

1. Mac: §2 (`git pull`), then §3 with **`pod-revision-nopvc.yaml`** (same 48-vCPU node).
2. Inside the pod:

```bash
cd /app/article_1_revision && mkdir -p /workspace/revision
python r11_run_gradient.py --dry-run --skip-if-exists     # "to run now: 0 preparations, 90 harmonizations"
setsid nohup sh -c '
  python r11_run_gradient.py --skip-if-exists --n-workers 36 --n-prep-workers 4 \
      --memory-limit-gb 4 > /workspace/revision/gradient_angel_mcombat.log 2>&1
  python r12_revision_metrics.py --experiment gradient --skip-if-exists \
      --n-workers 36 --memory-limit-gb 3 --timeout-s 7200 \
      > /workspace/revision/metrics_gradient_angel_mcombat.log 2>&1
' > /workspace/revision/angel_mcombat.log 2>&1 &
exit
```

3. Watch (Mac): `aws s3 cp s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/pod_logs/<folder>/metrics_gradient_angel_mcombat.log - | tail`;
   done when it ends with `SUMMARY metrics`. M-ComBat takes the diagnosis covariate like ComBat,
   so its λ = 1 runs and the single-diagnosis control are expected to fail (a failure is a result).
4. Delete the pod (`kubectl delete pod $POD_REV -n ${K8S_NAMESPACE}`) and tell Claude on JupyterHub:
   **"the gradient pod is done"**. Claude then runs `r12 --experiment gradient --concat`, r13, nb04,
   r45 and fills the numbers.

## 7. Troubleshooting

| Symptom | Cause | What to do |
|---|---|---|
| Pod stays `Pending` | Karpenter is provisioning the pinned c6a.12xlarge (since G3), or the request is too large; if no c6a.12xlarge is available for long, switch type: set `node.kubernetes.io/instance-type: c6a.8xlarge`, rename the pod to `…-revision-c6a-8xlarge` (the rule checker refuses a mismatch) and lower `resources` to 30 CPU / 56Gi | `kubectl describe pod <pod> -n ${K8S_NAMESPACE}` → *Events*; wait, or lower `resources` |
| `Pending`, karpenter: "no instance type has enough resources … ephemeral-storage" | The ${K8S_NAMESPACE} nodes have 43.9 GiB allocatable disk; a pod request above it never schedules (45Gi did, 2026-11-03) | Keep `ephemeral-storage` requests ≤ ~40Gi (now 34Gi request, emptyDir 30Gi) |
| `ContainerCreating`, "Multi-Attach error" | Another pod holds the PVC | Delete it (§2), wait ~1 min |
| `ContainerCreating`, "secret not found" | A Secret is missing | §1 |
| `ps` shows `r19_harmonize_one.py` processes of a job already logged `timeout`, parent PID 1, 0 % CPU | The timeout killed the job's parent but not Shambhala's worker pool (2026-11-04: 17 orphans, ~13 GB, 16 h) | `pkill -f "subset-id <subset> --arm <arm>"`; the timeout record on S3 stays valid |
| Pod `NotFound`, S3 logs stop mid-run without "final sync done" | Node removed under the pod (Karpenter consolidation / expiry; 2026-11-05 08:45 UTC, before the manifest carried `karpenter.sh/do-not-disrupt`) | Relaunch (§3) and rerun the same command with `--skip-if-exists` |
| Job log: exit code 137 / `OOMKilled` / dispatcher row `failed` with -9 | Not enough memory | Lower `--n-workers` or raise the manifest memory; rerun with `--skip-if-exists` |
| Dispatcher keeps printing "waiting for memory" | `--memory-limit-gb` above what the pod has free | Lower `--memory-limit-gb` |
| `ModuleNotFoundError: revision_lib` (harmonization pod) | Folder not copied / wrong cwd | Repeat the `tar` copy (§3); run from `/app/article_1_revision` |
| `ModuleNotFoundError` (metrics pod) | Start-up not finished or a shell without the venv | Wait for "Metrics environment ready."; `bash -l` |
| `ssh: connect to host localhost port 2222` refused | Port-forward closed | Restart `kubectl port-forward …` |
| Dry-run lists another number than 24 / 62 / 86 / 540 / 1,200 | Stale designs / folds on the Mac | `git pull` (§2) and copy again |
| `[startup] WARNING: Shambhala2_fast missing` | GitHub unreachable from the node | The pilots still run, `20_shambhala` is recorded as failed; repeat the clone block of the manifest by hand: `kubectl exec … -c worker -- bash -c '<clone lines>'` |
| `r18_env_check.py` ends with `STOP — not equivalent` | The image's package versions change a published method's output | Do not start the pilots; keep the JSON (`revision_261029/env_check/`) and report at G3 |
| Per-job log of one job | — | `/workspace/revision/<gradient|v1|metrics_*|bridging>/<job>.log`; table `/workspace/revision/<…>_<stage>.tsv` (PVC-free pod: the same paths under S3 `pod_logs/<folder>/`) |
| PVC-free pod `Evicted`, reason `ephemeral local storage usage exceeds…` | Disk full on the node / emptyDir over `sizeLimit` | Relaunch (the cache re-downloads), rerun with `--skip-if-exists`; lower `--n-workers` or raise `sizeLimit`; the logs up to ~60 s before the eviction are on S3 (§4b) |
| `kubectl logs $POD_REV -c log-sync` shows S3 errors | Credentials / S3 access | Check the `aws-credentials` Secret (§1); the runs themselves are unaffected |
