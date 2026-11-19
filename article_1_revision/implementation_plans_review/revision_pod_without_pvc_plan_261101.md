# Plan — harmonization pod of the Article 1 revision without the PVC (2026-11-01)

Status: **approved and implemented 2026-11-01** (docs + manifest); pod run: see TODO.

## Overview

The revision harmonization pod (`fl-revision`, `k8s/pod-revision.yaml`) mounts
`subPath: workspace` of the only PVC, `fl-a3-scratch` (ReadWriteOnce). Since
2026-10-29 the annotation 3.0 pod `fl-a3` holds this PVC. It is running the
hard-tier dispatcher (`run_a3_dispatcher.py --difficulty hard --retry-failed`, started Oct 29)
and the throughput pilot `pilot_throughput_matrix.py --stage AB_t1` (started 2026-11-01 08:20).
The revision pilots can't start until that pod is deleted, which would interrupt annotation 3.0.

The proposed change: a second manifest, `k8s/pod-revision-nopvc.yaml`. It is the same pod with
the PVC replaced by a node-local **`emptyDir` mounted at `/workspace`**. Every input and output
of the revision runs already goes through S3, so the PVC holds only scratch data: logs, the raw
matrix cache and the prepared-subset caches. Mounting the `emptyDir` at the same path keeps
every script, default path and RUNBOOK command unchanged.

The logs are the only thing on `/workspace` worth keeping, and they would die with an
`emptyDir`. So the pod **saves its logs on S3 itself**: a small second container (`log-sync`,
same image, `awscli` is already installed) mounts the same `emptyDir`. It mirrors
`/workspace/revision` (without `cache/`) to
`s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/pod_logs/<pod>_<start time>/`
every 60 s, and once more when the pod is deleted. No manual copy step is needed, and nothing
is lost if the Mac session ends.

**No Python file changes.** The two pods run in parallel, and nothing of annotation 3.0 is
touched.

## Feasibility assessment

### What the harmonization pod keeps on `/workspace` (code audit)

| Item | Path in the pod | Written by | Read by | Where it ends up |
|---|---|---|---|---|
| Log folder root | `/workspace/revision` | `revision_dispatch.default_log_dir()`: uses `/workspace/revision` when `/workspace` is a directory, otherwise `./cache/revision_logs` | dispatchers | — |
| Per-job logs + stage tables | `/workspace/revision/<experiment>/<job>.log`, `<experiment>_<stage>.tsv` | `revision_dispatch.run_jobs` (the table is rewritten after every finished job) | humans (debugging) | **S3 `pod_logs/…`** via `log-sync` (≤ 60 s behind) |
| Dispatcher stdout | `/workspace/revision/{gradient,v1}_pilot.log` | shell redirect (RUNBOOK §4) | humans | **S3 `pod_logs/…`** via `log-sync` |
| Raw matrix cache (~2 GB) | `/workspace/revision/cache/bench_comb_data.pkl` | `r19 --warm-cache` | `r19` preparation | dropped with the pod (excluded from the sync); rebuilt from S3 in minutes |
| Prepared-subset caches | `/workspace/revision/cache/prepared/<exp>/<subset>__{exp,ann}.pkl` | `r19.load_prepared` | `r19` harmonization | dropped (excluded); the prepared subsets are on S3 |
| **Results**: prepared subsets, harmonized matrices, run records `runs/*.json` (status, seconds, method messages) | S3 `revision_261029/{gradient,v1}/…` | `r19` | `r14_pilot_report.py`, `r12`, everything downstream | on S3, unchanged |

The gate G3 report (`r14_pilot_report.py`) reads only the S3 JSON records (`read_records()`
lists `revision_261029/<experiment>/<folder>/*.json`). `--skip-if-exists` checks S3 keys under
`revision_261029/<experiment>/`. The new `revision_261029/pod_logs/` folder sits beside both
experiment folders, never inside them, so neither the report nor the skip logic can pick up a
log file. A restart on a fresh `emptyDir` resumes correctly; only the raw cache is downloaded
again.

### Logs on S3: how `log-sync` works and why this design

| Option | Covers | Survives | Code change | Verdict |
|---|---|---|---|---|
| **A. Sidecar container `log-sync` (chosen)**: `aws s3 sync` every 60 s + once more on SIGTERM | everything under `/workspace/revision` (job logs, stage tables, dispatcher stdout) | `kubectl delete pod` (final sync in the grace period); a crash of the main container; hard eviction loses at most the last 60 s | manifest only | simplest, covers every log, starts by itself |
| B. Upload each job log from `revision_dispatch.run_jobs` when the job ends | job logs + stage tables only; **not** the dispatcher stdout (a shell redirect) | every finished job, instantly | `revision_dispatch.py` (shared with the metrics pod's `r12` / `r30`) | misses the dispatcher log; changes code the metrics pod also runs |
| C. A manual `nohup` sync loop typed inside the pod | as A | as A, if it was started | none | easy to forget; dies if the pod's shell session is killed |

Facts behind A (checked 2026-11-01):
- The image installs `awscli>=1.29` and `boto3` (`harmonization-scripts/requirements.txt`, line
  4; `Dockerfile` line 28 `pip install -r`), so the `aws` command exists in both containers.
- The credentials are the same `aws-credentials` Secret, mounted read-only at `/root/.aws`, as
  in the main container.
- Kubernetes sends SIGTERM to every container on `kubectl delete pod` and waits up to
  `terminationGracePeriodSeconds` (set to 90 s). The loop sleeps as `sleep 60 & wait $!`, so the
  `trap` fires at once and runs the final sync.
- The pod already sets `shareProcessNamespace: true`, so the sidecar's shell is not PID 1 and
  handles its trapped signal normally.
- The S3 folder name carries the container start time (`<pod>_<YYMMDD_HHMM>`, UTC), so a
  relaunch writes a new folder instead of overwriting the previous run's logs.

### Cluster facts (checked 2026-11-01)

| Fact | Value | Consequence |
|---|---|---|
| Node family of the manifest | `c6a` (nodeSelector); a running node is `c6a.12xlarge` | — |
| Node root disk (ephemeral storage) | capacity 52,350,956 Ki ≈ 50 GiB, allocatable ≈ 44 GiB, shared with container images | enough for the image plus a 20 GiB `emptyDir` |
| `fl-batch-correction:latest` image size | not measurable (no `ecr:DescribeImages` permission; not cached on any node); R + Bioconductor images of this kind are ~3–8 GB; pulled **once** for both containers | fits next to 20 GiB |
| LimitRange `main-limit` | only memory defaults and the PVC minimum; no ephemeral-storage limit | an explicit `ephemeral-storage` request / limit is allowed; the sidecar gets explicit memory so the 256 Mi default limit does not apply |
| ResourceQuota | only secrets and EBS storage | an `emptyDir` uses no quota |
| PVC policy | ${K8S_NAMESPACE} admins reduced Daniil to **one PVC** on 2026-10-29 | rules out a second PVC and a generic ephemeral volume (which creates a PVC) |

### Disk need

| Run | Raw cache | Prepared caches | Logs | Total |
|---|---|---|---|---|
| Pilots (2 gradient designs ≤ 750 samples, 2 leave-cohort-out subsets of C) | ~2 GB | < 0.1 GB | < 0.1 GB | **~2–3 GB** |
| Full runs (45 gradient designs; 40 v1 subsets, S0 training ≈ 5,700 × 3,447 float64 ≈ 160 MB each) | ~2 GB | ~3–4 GB | < 0.5 GB | **~6–7 GB** |

`sizeLimit: 20Gi` gives about 3× headroom for both cycles. The logs on S3 are a few MB per
cycle.

**Verdict: feasible, with no Python change.** The pod saves its own logs on S3, so deleting the
pod, an eviction or a closed Mac session loses at most the last minute of log lines. The S3 run
records carry each method's last 4,000 characters of output anyway.

## Pros and cons

| | Without the PVC (`emptyDir` + `log-sync`) | With the PVC (current manifest) |
|---|---|---|
| Annotation 3.0 | keeps running: the hard tier and the AB_t1 throughput pilot are not interrupted | must be stopped; it re-runs with `--retry-failed`, and the interrupted pilot stage is lost |
| Start time | now | when a3 is idle, or after deleting it |
| Code change | none (manifest only; same path `/workspace`) | none |
| Logs after the pod ends | on S3 `revision_261029/pod_logs/<pod>_<start>/`, readable from the Mac **and** JupyterHub | on the PVC, readable only from a pod that mounts it |
| Caches after the pod ends | gone | kept on the PVC |
| Results | on S3 (identical) | on S3 (identical) |
| Restart after a crash or eviction | re-download of the raw cache (~2 GB, minutes); `--skip-if-exists` resumes from S3; the logs of the previous run stay in their own S3 folder | the cache is reused |
| Disk throughput | node NVMe/EBS root disk, usually faster than the gp3 PVC | gp3 PVC |
| Failure mode | if the `emptyDir` exceeds `sizeLimit` (or the node disk fills), kubelet **evicts the pod**: all running jobs end; S3 outputs and the logs synced so far stay | PVC full → write errors in single jobs |
| Cost | two pods at once (a3 + revision; 8.25 vCPU / 16.25 GiB more for the pilot's few hours); S3 PUTs every 60 s, negligible | one pod |
| Fit with "one pod at a time" (README §3, RUNBOOK header) | the rule exists only because of the PVC, so this pod falls outside it; docs must say so | as documented |

**Recommendation: use the PVC-free pod for the harmonization pilots and the harmonization full
runs.** The metrics pod is out of scope here. Its manifest belongs to the frozen benchmark side
(`harmonization-metrics-calculation/k8s/pod-metrics.yaml`), and its `/workspace/ref_cache` is
reused across runs. Whether the metrics pod should also go PVC-free (with the same `log-sync`
sidecar) is a separate question for §5 of the RUNBOOK. Answer it before cycle 1c, when the a3
pod may still be running.

## Files to change

### 1. `article_1_revision/k8s/pod-revision-nopvc.yaml` — new file

This is a copy of `k8s/pod-revision.yaml` with the same pod name, image and main-container
resources. Keeping the same pod name means every `kubectl exec / delete` command in RUNBOOK and
README stays valid. The two manifests must never be applied at the same time. Differences:

1a. The main container's resources gain an ephemeral-storage request / limit, so the scheduler
picks a node with room and eviction is predictable:

```yaml
# before
    resources:
      requests:
        cpu: "8"
        memory: "16Gi"
      limits:
        cpu: "8"
        memory: "16Gi"
# after
    resources:
      requests:
        cpu: "8"
        memory: "16Gi"
        ephemeral-storage: "25Gi"
      limits:
        cpu: "8"
        memory: "16Gi"
        ephemeral-storage: "30Gi"
```

(The limit covers the `emptyDir` plus the container's writable layer: `/app` copy, pip, `/tmp`.)

1b. The main container's volume mount loses `subPath`:

```yaml
# before
    - name: work
      mountPath: /workspace
      # the only PVC since 2026-10-29 (...)
      subPath: workspace
# after
    - name: work
      mountPath: /workspace
      # node-local scratch (plan revision_pod_without_pvc_plan_261101.md): results are on
      # S3; the log-sync container mirrors /workspace/revision to S3 pod_logs/
```

1c. New second container `log-sync`, after the `worker` container, in the same `containers:` list:

```yaml
  # Saves the logs on S3 (plan revision_pod_without_pvc_plan_261101.md): the emptyDir dies
  # with the pod. Mirrors /workspace/revision (not cache/) every 60 s and once more on
  # SIGTERM (kubectl delete pod). One folder per start, so a relaunch never overwrites.
  - name: log-sync
    image: ${ECR_URI}/fl-batch-correction:latest
    imagePullPolicy: Always
    env:
    - name: POD_NAME
      valueFrom:
        fieldRef:
          fieldPath: metadata.name
    command: ["/bin/sh", "-c"]
    args:
    - |
      DEST="s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/pod_logs/${POD_NAME}_$(date -u +%y%m%d_%H%M)"
      mkdir -p /workspace/revision
      sync_once() {
        aws s3 sync /workspace/revision "$DEST" --exclude "cache/*" --only-show-errors
      }
      trap 'sync_once; echo "final sync done"; exit 0' TERM INT
      echo "log-sync -> $DEST"
      while true; do sleep 60 & wait $!; sync_once; done
    resources:
      requests:
        cpu: "250m"
        memory: "256Mi"
      limits:
        cpu: "500m"
        memory: "512Mi"
    volumeMounts:
    - name: work
      mountPath: /workspace
    - name: aws-credentials
      mountPath: /root/.aws
      readOnly: true
```

1d. Pod spec: `terminationGracePeriodSeconds: 90` (next to `restartPolicy: Never`), so the
final sync has time to finish on `kubectl delete pod`.

1e. The volume becomes an `emptyDir`:

```yaml
# before
  - name: work
    persistentVolumeClaim:
      claimName: fl-a3-scratch
# after
  - name: work
    emptyDir:
      sizeLimit: 20Gi
```

1f. The header comment states the PVC-free variant, links to this plan, names the S3 log folder,
and notes that it may run next to `fl-a3`.

### 2. `article_1_revision/RUNBOOK.md`

2a. Header table and the line "Two pods, **never at the same time** (they share the only PVC…)"
gain one sentence: *"While the annotation 3.0 pod holds the PVC, start the harmonization pod
from `k8s/pod-revision-nopvc.yaml` (no PVC, scratch on the node, logs saved on S3; see §4b). It
may run next to the a3 pod."* The line "Logs and caches live on the PVC in
`/workspace/revision/`" gets the PVC-free alternative: *"(PVC-free pod: logs on S3
`revision_261029/pod_logs/`, caches dropped with the pod)"*.

2b. §2 "free volume" check: add *"skip the PVC check when you use `pod-revision-nopvc.yaml`"*.

2c. §3 launch: show the alternative
`kubectl apply -f article_1_revision/k8s/pod-revision-nopvc.yaml -n ${K8S_NAMESPACE}`, and the check
that log saving started: `kubectl logs fl-revision -c log-sync -n ${K8S_NAMESPACE}`
(expect `log-sync -> s3://…`). With two containers, `kubectl exec` picks the first one
(`worker`, as before); add `-c worker` to the documented commands to be explicit.

2d. New §4b "PVC-free pod: logs on S3":

```bash
# list the log folders (one per pod start)
aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/pod_logs/
# read / fetch one run's logs on the Mac or on JupyterHub
aws s3 sync s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/pod_logs/<folder>/ \
    article_1_revision/cache/pod_logs/<folder>/
# deleting the pod runs a final sync (up to 90 s); confirm it:
kubectl delete pod fl-revision -n ${K8S_NAMESPACE}
aws s3 ls --recursive s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/pod_logs/<folder>/ | tail -3
```

(`article_1_revision/cache/` is git-ignored: `.gitignore:126`.)

2e. §4 "Watch from the Mac": add the alternative
`aws s3 cp s3://…/pod_logs/<folder>/gradient_pilot.log - | tail -n 20`, which works without
`kubectl`.

2f. §7 troubleshooting: two new rows.
- *"Pod `Evicted`, reason `ephemeral local storage usage exceeds…` → disk full on the node;
  relaunch (cache re-downloads), rerun with `--skip-if-exists`; lower `--n-workers` or raise
  `sizeLimit`; the logs up to ~60 s before the eviction are on S3."*
- *"`kubectl logs … -c log-sync` shows S3 errors → check the `aws-credentials` Secret (§1); the
  runs themselves are unaffected."*

### 3. `article_1_revision/README.md`

3a. §3 (line ~110, "**Only one pod at a time**…"): add that the harmonization pod has a PVC-free
manifest, can run while the annotation 3.0 pod holds the PVC, and saves its logs on S3.

3b. §4.3 launch block (line ~151): the same alternative `kubectl apply` line and the
`kubectl logs … -c log-sync` check; at `kubectl delete pod` (line ~211, "# free the PVC") a note
that the PVC-free pod writes its last logs to S3 before it ends.

3c. §6 Layout (line ~355): new row `k8s/pod-revision-nopvc.yaml | harmonization pod manifest
without the PVC (emptyDir scratch; log-sync container saves the logs on S3 pod_logs/)`.

### 4. `article_1_revision/CLAUDE.md`

One gotcha line in "Skills / gotchas": *"Harmonization pod without the PVC:
`k8s/pod-revision-nopvc.yaml` (emptyDir at `/workspace`, so `default_log_dir()` and every path
stay the same). Results are on S3; the `log-sync` container mirrors `/workspace/revision`
(without `cache/`) to S3 `revision_261029/pod_logs/<pod>_<start UTC>/` every 60 s and on
deletion; read pod logs from there."*

### 5. `article_1_revision/article_1_revision_implementation_plan_261029.md`

§7 (line ~959 "pod at a time can mount the PVC", ~968 "logs … on the PVC, so they survive a pod
crash", and ~978 "Two pods are used, never at the same time"): add one note that refers to this
plan (PVC-free harmonization pod, logs on S3 `pod_logs/`). No checklist items change.

## Files that do NOT need to change

| File | Why not |
|---|---|
| `revision_dispatch.py` | `default_log_dir()` tests `Path("/workspace").is_dir()`; the `emptyDir` is mounted there, so the PVC path logic is reused as is. Log saving lives in the manifest (option A), not in `run_jobs` (option B), so the code the metrics pod also runs is untouched |
| `r11_run_gradient.py`, `r21_run_v1.py`, `r19_harmonize_one.py` | paths come from `default_log_dir()` / `--log-dir`; results go to S3 |
| `r14_pilot_report.py` | reads only S3 JSON records under `<experiment>/runs|prepared`; `pod_logs/` is outside them |
| `k8s/pod-revision.yaml` | kept for the case where the a3 pod is gone (persistent cache on the PVC) |
| `harmonization-scripts/Dockerfile`, `requirements.txt` | `awscli` is already installed; no image rebuild |
| `harmonization-metrics-calculation/k8s/pod-metrics.yaml`, `r12`, `r30` | metrics pod out of scope (see Recommendation) |
| `FROZEN_MD5.txt` and all frozen files | untouched; manifests are not frozen |
| Project `CLAUDE.md`, `harmonization-scripts/k8s/CLAUDE.md` | the PVC policy itself does not change; the new manifest is local to `article_1_revision/` |

## Side effects and caveats

- **One new S3 folder**, `revision_261029/pod_logs/<pod>_<YYMMDD_HHMM>/` (text logs and stage
  tables, a few MB). The result folders are unchanged: same prefix `revision_261029/`, the same
  24 / 62 pilot jobs and the same 540 / 1,240 full jobs.
- **Log loss is bounded at ~60 s.** On a hard eviction (no grace period) the last minute of log
  lines may be missing; on `kubectl delete pod` the final sync covers everything. The S3 run
  records keep each method's last 4,000 characters of output regardless.
- **Two containers.** `kubectl exec` without `-c` still opens `worker` (the first container),
  so existing commands work; `kubectl logs` without `-c` will ask for a container name.
  `kubectl delete pod` waits up to 90 s (the final sync) instead of ~30 s.
- **Eviction is all-or-nothing.** A full disk or memory pressure on the node evicts the whole pod.
  With ~3 GB used against a 20 GiB limit, this is unlikely for the pilots. For S0 full runs,
  watch `du -sh /workspace` once.
- **Two pods at once.** The node pool must provision a second `c6a` node (or fit the pod beside
  the a3 pod on the `c6a.12xlarge`). `Pending` for a few minutes is normal (RUNBOOK §7).
- The a3 pod and its dispatcher are not touched; the PVC stays attached to it.
- If the a3 pod is deleted later, the PVC manifest can be used again for the next cycle; the two
  variants produce identical S3 outputs.

## Verification commands

```bash
cd ~/FL_harmonization
# manifest is valid and server-side accepted (nothing created)
kubectl apply --dry-run=server -f article_1_revision/k8s/pod-revision-nopvc.yaml -n ${K8S_NAMESPACE}
diff article_1_revision/k8s/pod-revision.yaml article_1_revision/k8s/pod-revision-nopvc.yaml

# after launch: /workspace is the emptyDir and the scripts see it
kubectl exec fl-revision -c worker -n ${K8S_NAMESPACE} -- df -h /workspace
kubectl exec fl-revision -c worker -n ${K8S_NAMESPACE} -- sh -c \
  'cd /app/article_1_revision && python -c "import revision_dispatch as rd; print(rd.default_log_dir())"'
# expect: /workspace/revision

# log saving works: a test file appears on S3 within ~60 s
kubectl logs fl-revision -c log-sync -n ${K8S_NAMESPACE}      # "log-sync -> s3://…"
kubectl exec fl-revision -c worker -n ${K8S_NAMESPACE} -- \
  sh -c 'echo ok > /workspace/revision/log_sync_check.txt'
sleep 70
aws s3 ls --recursive s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/pod_logs/ \
  | grep log_sync_check

# a3 untouched
kubectl get pod fl-a3 -n ${K8S_NAMESPACE}     # still Running, same RESTARTS

# pilot dry-runs: 24 and 62 jobs
kubectl exec fl-revision -c worker -n ${K8S_NAMESPACE} -- sh -c \
  'cd /app/article_1_revision && python r11_run_gradient.py --pilot --dry-run && python r21_run_v1.py --pilot --dry-run'

# after kubectl delete pod: the final sync wrote the dispatcher summaries
aws s3 cp s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/pod_logs/<folder>/v1_pilot.log - | tail -n 3
# expect: "SUMMARY harmonize: 62 jobs — …"
```

## TODO

- [x] `k8s/pod-revision-nopvc.yaml` — new file: copy of `pod-revision.yaml`, header comment
- [x] `k8s/pod-revision-nopvc.yaml` — `worker`: `ephemeral-storage` request 25Gi / limit 30Gi
- [x] `k8s/pod-revision-nopvc.yaml` — `worker`: volume mount without `subPath`
- [x] `k8s/pod-revision-nopvc.yaml` — new `log-sync` container (sync every 60 s + on SIGTERM, own resources, `work` + `aws-credentials` mounts)
- [x] `k8s/pod-revision-nopvc.yaml` — `terminationGracePeriodSeconds: 90`
- [x] `k8s/pod-revision-nopvc.yaml` — volume `work` → `emptyDir: {sizeLimit: 20Gi}`
- [x] `kubectl apply --dry-run=server` of the new manifest passes
- [x] `RUNBOOK.md` — header: PVC-free variant may run next to the a3 pod; logs on S3
- [x] `RUNBOOK.md` — §2 note: PVC check not needed for the PVC-free pod
- [x] `RUNBOOK.md` — §3 alternative `kubectl apply` line + `kubectl logs -c log-sync` check + `-c worker`
- [x] `RUNBOOK.md` — §4 watch-from-S3 alternative
- [x] `RUNBOOK.md` — new §4b: logs on S3 (list, fetch, confirm the final sync after deletion)
- [x] `RUNBOOK.md` — §7 eviction row + log-sync error row
- [x] `README.md` — §3 one-pod-at-a-time note amended
- [x] `README.md` — §4.3 alternative launch line, log-sync check, final-sync note at deletion
- [x] `README.md` — §6 Layout row for the new manifest
- [x] `CLAUDE.md` (article_1_revision) — gotcha line
- [x] `article_1_revision_implementation_plan_261029.md` — §7 note referring to this plan
- [ ] Launch the PVC-free pod, copy the code (RUNBOOK §3), check the frozen `bench_shared.py` MD5,
      run `pytest tests/test_revision_lib.py -q` and both pilot dry-runs (24 / 62)
      — **BLOCKED 2026-11-01**: the pod was scheduled, but both containers stayed in
      `ImagePullBackOff`: `fl-batch-correction:latest` → `NotFound` in ECR (`failed to resolve
      reference`). This also breaks `pod-revision.yaml`; it does not come from this plan.
      `harmonization-scripts/CLAUDE.md` calls the ECR pod spec "older (kept for reference)"; the
      current benchmark pod is `harmonization-scripts/k8s/pod-ssh.yaml` (`ubuntu:24.04`, R 4.5 +
      Python installed at start-up, ~30–40 min). Daniil cannot list or push ECR images
      (`ecr:ListImages` / `GetAuthorizationToken` denied). The failed pod was deleted; the a3 pod is
      untouched. → **Unblocked** by `revision_pod_combobatch_image_plan_261101.md` (ComboBatch image);
      the remaining run items are carried out under that plan.
- [ ] Log-sync check: `log_sync_check.txt` appears under S3 `pod_logs/` within ~60 s
- [ ] Gradient pilot → wait for `SUMMARY harmonize: 24 jobs`; 24 run records on S3
- [ ] Leave-cohort-out pilot → wait for `SUMMARY harmonize: 62 jobs`; run records on S3
- [ ] `kubectl delete pod fl-revision -n ${K8S_NAMESPACE}`; confirm the final sync
      (`v1_pilot.log` on S3 ends with the SUMMARY line) and that the a3 pod is still Running
- [ ] Stop at gate G3: metrics pilot (metrics pod) and full runs wait for Daniil
