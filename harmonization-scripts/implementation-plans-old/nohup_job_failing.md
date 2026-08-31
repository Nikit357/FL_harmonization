# nohup Job Failures in Kubernetes Pods — Root Cause Analysis and Solutions

date: April 24 2026

---

## 1. Immediate Status Assessment (as of htop screenshot)

### Are the scripts actually working?

**Yes.** The htop screenshot shows:

| What you see | What it means |
|---|---|
| PIDs 44137–44179 (`python run_prep_parallel.py --n-workers 2 ...`) at 0% CPU | Dispatcher threads blocked in `subprocess.run()` — correct; waiting for workers to finish |
| PID 175671 (`run_prep_job.py --strat S0_no_removal --imp missforest`) at ~75% CPU | Active R missForest imputation on the S0 dataset |
| PID 175638 (`run_prep_job.py --strat A_confirmed_bad --imp missforest`) at high CPU | Active R missForest imputation on the A dataset |
| Load average ~23–27 across 32 CPUs | missForest uses all available CPU via `randomForest` parallel forest construction |
| 247 GB total RAM, bar nearly empty | Low absolute memory use relative to node capacity |

### Should you terminate or wait?

**Wait.** Do not kill these processes. Here is why missForest takes this long:

missForest imputes missing values by training one random forest **per gene** (3,520 genes in this dataset) iteratively until convergence. On a 3,520 × ~5,000 matrix with a 60-hour timeout (`--timeout-s 216000`), 8–15 hours per `(strat, imp)` pair is completely normal. Terminating now wastes all CPU time invested. The `--skip-if-exists` flag means completed S3 uploads will not be repeated on restart.

Both workers are CPU-bound (high CPU, low memory) — this is the expected missForest profile. They are not stuck.

### Can you add more scripts right now?

| Resource | Current state | Headroom |
|---|---|---|
| CPU | ~23–27 / 32 cores busy (75–85%) | Small. Adding another missForest worker would slow all three by 25–33%. |
| RAM | Nearly empty relative to 247 GB node | Substantial. Memory is not the bottleneck. |
| S3 bandwidth | Idle during imputation | Free to use. |

**Recommendation:** Do not add more missForest or softImpute workers now — they are CPU-bound and would compete with the running workers. You can safely add `knn` or `strict` imputation jobs (they are fast and light). After the current missForest jobs finish and upload, you can submit a second missForest batch.

---

## 2. Why Jobs Previously "Vanished" — Root Cause Analysis

The prior pattern — log goes silent after 2–3 hours, no S3 output, no error message — has several compounding causes.

### 2.1 The Critical psutil/cgroup Bug (primary mechanism)

The memory guard in `run_prep_parallel.py` is fundamentally broken inside a Kubernetes container:

```python
# run_prep_parallel.py, line 196
def _free_gb() -> float:
    try:
        import psutil
        return psutil.virtual_memory().available / 1e9
    except ImportError:
        return 999.0
```

`psutil.virtual_memory()` reads `/proc/meminfo`. In a standard Linux Kubernetes container, `/proc/meminfo` is **not cgroup-namespace-aware** — it reports the **host node's** available RAM, not the container's cgroup-enforced limit.

| What the code thinks it sees | What it actually reads |
|---|---|
| Container's available RAM | Host node's available RAM |
| Would be limited by `limits.memory: 16Gi` in pod.yaml | Reports ~230 GB free on a 247 GB node |

Consequence: `_wait_for_memory(16.0)` always sees ~230 GB available, immediately returns, and **never blocks the launch of the next worker**. The memory guard that is supposed to prevent concurrent workers from exhausting the container's 16 Gi cgroup limit does nothing.

The identical bug exists in `run_prep_job.py`:
```python
# run_prep_job.py, line 43-48
def _free_gb() -> float:
    try:
        import psutil
        return psutil.virtual_memory().available / 1e9
    except ImportError:
        return 999.0
```
The worker's own startup check (`_check_memory`) also reads node RAM, so it never aborts.

### 2.2 Container cgroup OOM Kill

With the memory guard disabled (reading node RAM), the dispatcher launches both workers with no delay. Each worker then:
1. Loads `comb_exp` (~3–4 GB RSS) from `/tmp` pickle cache
2. Runs R missForest via rpy2 — R process spins up random forests, adding another 4–8 GB RSS

Approximate worst-case container RSS (both workers concurrent, `limits.memory: 16Gi` in pod.yaml):

| Component | RSS |
|---|---|
| Dispatcher Python process | ~800 MB |
| Worker 1: Python + data + R missForest | ~6–10 GB |
| Worker 2: Python + data + R missForest | ~6–10 GB |
| **Total** | **~14–21 GB** |
| **Container cgroup limit (`pod.yaml`)** | **16 Gi ≈ 17.2 GB** |

When the container's cgroup memory limit is hit, the Linux OOM killer sends **SIGKILL to the process with the highest `oom_score`** inside the cgroup — typically the R subprocess (largest RSS). The R process dies. The `rpy2` call raises an exception inside `prepare_dataset_imputed()`. The worker falls back to `prepare_dataset()` (strict, no imputation) or exits with a non-zero code. Either way, the imputed S3 files are never uploaded.

The pod itself survives (PID 1 is `sleep infinity` — low RSS, not OOM-killed). This is why you can still `kubectl exec` into a pod after workers fail — the pod is `Running` but the Python job is gone.

**Note on the current run:** The current workers are alive at 6–7 hours, suggesting the actual missForest RSS for this dataset may be lower than worst-case estimates, or the pod is running on a node with higher effective memory headroom. Regardless, the memory guard provides no protection and cannot be relied upon.

### 2.3 `capture_output=True` Amplifies Dispatcher RSS

In the dispatcher's `launch()` function:

```python
proc = subprocess.run(
    cmd, capture_output=True, text=True,    # ← all worker stdout+stderr buffered in RAM
    timeout=timeout_s, cwd=str(Path(__file__).parent),
)
```

`capture_output=True` means every line R prints to stdout/stderr during a 6–15 hour missForest run accumulates in the dispatcher process's heap. Two concurrent workers can accumulate hundreds of megabytes of R output in the dispatcher's RAM before `subprocess.run()` returns. This directly adds to the container's cgroup RSS.

### 2.4 The Dispatcher Exits Cleanly After All Workers Fail

If both concurrent workers fail (OOM-killed or otherwise), the dispatcher records them in `failed_jobs_prep.txt`, then attempts the next batch of jobs. Eventually, if all non-cached jobs fail (e.g. all missForest jobs OOM), the dispatcher finishes the `as_completed()` loop, calls `_save_failed_log()`, `_sync_failed_log_to_s3()`, and **exits with return code 0**. From the outside, this looks like the job "vanished" with no error — the dispatcher completed normally after all workers failed silently.

This explains the log pattern previously observed: 3 cached KNN jobs complete in 2 s, then silence — the remaining non-cached missForest jobs were running (2+ hours), failed, were recorded as failures, and the dispatcher exited.

### 2.5 Karpenter Node Consolidation

When the dispatcher blocks in `_wait_for_memory()` (30-second sleep loop), the Python process uses near-zero CPU. Karpenter's consolidation logic may interpret this as an idle workload and drain the node, emitting SIGTERM to all container processes. `nohup` does **not** protect against SIGTERM from Kubernetes — it only ignores SIGHUP.

### 2.6 What `nohup` Does and Does Not Protect Against

| Signal | Source | `nohup` protection |
|---|---|---|
| SIGHUP | SSH/terminal disconnect | ✓ Protected (this is what nohup does) |
| SIGTERM | `kubectl delete pod`, Karpenter drain, Spot interruption | ✗ Not protected |
| SIGKILL | OOM killer, Karpenter forced eviction | ✗ Not protected |
| R subprocess crash | OOM inside rpy2 call | ✗ Not protected (propagates as exception) |

Session persistence after SSH disconnect is **not** the failure mode here. `nohup` correctly re-parents the process under PID 1 when you disconnect. The failures are from within the Kubernetes layer.

---

## 3. Solutions — Sorted by Feasibility in a Running Pod

### 3.1 Fix the psutil/cgroup Memory Guard (Recommended — No Install Required)

Replace the broken `_free_gb()` with a cgroup-aware implementation. Apply to **both** `run_prep_parallel.py` (line 193) and `run_prep_job.py` (line 43):

```python
def _free_gb() -> float:
    """Return available RAM in GB, cgroup-aware for Kubernetes containers."""
    # cgroup v2 (systemd default on modern kernels)
    cg2_limit = "/sys/fs/cgroup/memory.max"
    cg2_usage = "/sys/fs/cgroup/memory.current"
    # cgroup v1 (older kernels, some K8s distros)
    cg1_limit = "/sys/fs/cgroup/memory/memory.limit_in_bytes"
    cg1_usage = "/sys/fs/cgroup/memory/memory.usage_in_bytes"

    def _read_int(path: str):
        try:
            val = open(path).read().strip()
            return None if val == "max" else int(val)
        except (OSError, ValueError):
            return None

    limit = _read_int(cg2_limit) or _read_int(cg1_limit)
    usage = _read_int(cg2_usage) or _read_int(cg1_usage)

    if limit is not None and usage is not None:
        return (limit - usage) / 1e9

    # Fallback to node-level psutil when cgroup files unavailable
    try:
        import psutil
        return psutil.virtual_memory().available / 1e9
    except ImportError:
        return 999.0
```

To verify which cgroup version the pod uses:
```bash
ls /sys/fs/cgroup/memory.max 2>/dev/null && echo "cgroup v2" || echo "cgroup v1"
```

---

### 3.2 Fix `capture_output=True` — Stream Worker Output Instead

Replace the blocking `subprocess.run(capture_output=True)` in `run_prep_parallel.py` with `Popen` that streams output directly to the dispatcher's stdout:

```python
import subprocess, sys, threading

def _stream_output(pipe, prefix: str) -> None:
    for line in pipe:
        sys.stdout.write(f"  [{prefix}] {line}")
        sys.stdout.flush()

def launch(strat: str, imp: str) -> tuple[list[dict], float, int]:
    _wait_for_memory(memory_limit_gb)
    json_path = tmp_dir / f"{strat}__{imp}.json"
    cmd = [
        sys.executable, "run_prep_job.py",
        "--strat", strat, "--imp", imp,
        "--out-json", str(json_path),
        "--memory-limit-gb", str(memory_limit_gb / 2),
    ]
    if skip_if_exists:
        cmd.append("--skip-if-exists")
    t0 = time.time()
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,   # merge stderr into stdout
            text=True,
            cwd=str(Path(__file__).parent),
        )
        prefix = f"{strat}x{imp}"
        t = threading.Thread(
            target=_stream_output, args=(proc.stdout, prefix), daemon=True
        )
        t.start()
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            t.join(timeout=5)
            return ([], time.time() - t0, -9)
        t.join(timeout=5)
    except Exception:
        return ([], time.time() - t0, -1)
    elapsed = time.time() - t0
    rows: list[dict] = []
    if proc.returncode == 0 and json_path.exists():
        try:
            with open(json_path) as fh:
                rows = json.load(fh)
        except Exception:
            pass
    return (rows, elapsed, proc.returncode)
```

Benefits: worker output is forwarded line-by-line instead of buffered → dramatically lower dispatcher RSS; R progress messages visible in `nohup.out` in real time.

---

### 3.3 Separate Workers by Imputation Method

Run light and heavy imputation in separate invocations, and use `--n-workers 1` for missForest/softImpute to eliminate concurrent RSS:

```bash
# Light imputation — 4 workers, short timeout
nohup python run_prep_parallel.py \
    --n-workers 4 \
    --skip-if-exists \
    --timeout-s 7200 \
    --memory-limit-gb 5.0 \
    --imps strict,knn \
    > /workspace/prep_fast.log 2>&1 &

# missForest — 1 worker at a time, long timeout
nohup python run_prep_parallel.py \
    --n-workers 1 \
    --skip-if-exists \
    --timeout-s 216000 \
    --memory-limit-gb 8.0 \
    --imps missforest \
    > /workspace/prep_missforest.log 2>&1 &

# softImpute — 1 worker at a time
nohup python run_prep_parallel.py \
    --n-workers 1 \
    --skip-if-exists \
    --timeout-s 216000 \
    --memory-limit-gb 8.0 \
    --imps softimpute \
    > /workspace/prep_softimpute.log 2>&1 &
```

`--n-workers 1` forces strictly serial execution — only one missForest process runs at a time, eliminating the concurrent RSS problem. Combined with the cgroup-aware `_free_gb()` fix, this is the safest configuration on a 16 Gi pod.

Always write logs to `/workspace/` (the persistent PVC) so they survive pod failures.

---

### 3.4 Add Graceful SIGTERM Handling to the Dispatcher

`nohup` ignores SIGHUP but the dispatcher has no handler for SIGTERM (Karpenter drain, `kubectl delete pod`). Adding one ensures `failed_jobs_prep.txt` is synced to S3 before the process is killed:

```python
import signal

def _sigterm_handler(signum, frame):
    print("\n[dispatcher] SIGTERM received — flushing logs and exiting.", flush=True)
    sys.exit(0)  # triggers atexit/finally hooks

# Add near the top of main():
signal.signal(signal.SIGTERM, _sigterm_handler)
```

With this in place, Karpenter's 30-second drain window is enough to sync the failed-jobs log, ensuring `--skip-if-exists --retry-failed` on the next pod picks up correctly.

---

### 3.5 Use `screen` or `tmux` for Live Monitoring

`nohup` already handles SSH disconnection correctly. However, `tmux`/`screen` adds the ability to reconnect and watch live output without reading a log file:

```bash
# Install inside the pod
apt-get install -y tmux

# Start a named session with the dispatcher running inside it
tmux new-session -d -s prep
tmux send-keys -t prep \
    "python run_prep_parallel.py --n-workers 1 --skip-if-exists \
     --timeout-s 216000 --memory-limit-gb 8.0 --imps missforest \
     2>&1 | tee /workspace/prep_missforest.log" Enter

# Reattach from any subsequent SSH session
kubectl exec -it fl-batch-correction -n ${K8S_NAMESPACE} -- tmux attach -t prep
```

---

### 3.6 Convert to a Kubernetes Job (Full Restart Robustness)

For long-running batch workloads, a Kubernetes `Job` is more robust than a bare `Pod` with `restartPolicy: Never` because the Job controller automatically restarts failed/evicted pods. With `--skip-if-exists`, each restart resumes from the last successfully uploaded S3 file.

Create `k8s/prep-job.yaml`:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: fl-prep-missforest
  namespace: ${K8S_NAMESPACE}
spec:
  backoffLimit: 5
  activeDeadlineSeconds: 259200   # 72-hour hard ceiling
  template:
    spec:
      restartPolicy: OnFailure
      tolerations:
        - key: karpenter.sh/disruption
          operator: Exists
          effect: NoSchedule
      nodeSelector:
        karpenter.k8s.aws/instance-family: c6a
      containers:
        - name: prep
          image: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/fl-batch-correction:latest
          command: ["python"]
          args:
            - "run_prep_parallel.py"
            - "--n-workers"
            - "1"
            - "--skip-if-exists"
            - "--timeout-s"
            - "216000"
            - "--memory-limit-gb"
            - "8.0"
            - "--imps"
            - "missforest"
          env:
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
          resources:
            requests:
              cpu: "8"
              memory: "14Gi"
            limits:
              cpu: "8"
              memory: "16Gi"
          volumeMounts:
            - name: workspace
              mountPath: /workspace
            - name: aws-credentials
              mountPath: /root/.aws
              readOnly: true
      volumes:
        - name: workspace
          persistentVolumeClaim:
            claimName: fl-workspace
        - name: aws-credentials
          secret:
            secretName: aws-credentials
```

```bash
kubectl apply -f harmonization-scripts/k8s/prep-job.yaml -n ${K8S_NAMESPACE}
kubectl logs -f job/fl-prep-missforest -n ${K8S_NAMESPACE}
```

On OOM kill or Spot interruption the Job controller starts a new pod; `--skip-if-exists` skips already-uploaded results.

---

### 3.7 Pin to On-Demand Instances (Prevents Spot Interruption)

If Karpenter provisions Spot instances, AWS can reclaim them with a 2-minute SIGTERM warning — not enough time to finish a 6-hour missForest job. Force On-Demand by adding a label to the pod or Job spec:

```yaml
nodeSelector:
  karpenter.k8s.aws/instance-family: c6a
  karpenter.k8s.aws/capacity-type: on-demand
```

---

## 4. Summary: Cause → Solution Mapping

| Root cause | Impact | Primary fix |
|---|---|---|
| `psutil` reads node `/proc/meminfo`, not container cgroup | Memory guard never fires; OOM possible | §3.1: cgroup-aware `_free_gb()` |
| `capture_output=True` buffers all R output in dispatcher heap | Amplifies dispatcher RSS over hours | §3.2: `Popen` + streaming |
| Concurrent missForest workers (n_workers=2) exceed 16 Gi cgroup | R subprocess OOM-killed, no S3 upload | §3.3: `--n-workers 1` per heavy method |
| Dispatcher exits cleanly after all workers fail | Silent disappearance with no visible error | §3.4: SIGTERM handler + §3.3 |
| No SIGTERM handler | failed_jobs log not synced on Karpenter drain | §3.4: signal handler |
| `restartPolicy: Never` — no retry on failure | Manual restart required every time | §3.6: Kubernetes Job |
| Spot instance reclamation | 2-minute warning, job cannot finish | §3.7: On-Demand node pinning |

---

## 5. Recommended Minimal Fix for Next Run

After the current missForest jobs finish, restart subsequent batches with the two highest-leverage changes applied (cgroup fix + serial workers):

```bash
# 1. First finish and upload the currently running jobs — just wait.

# 2. Then run remaining missforest strategies (--retry-failed picks up failed ones):
nohup python run_prep_parallel.py \
    --n-workers 1 \
    --skip-if-exists \
    --retry-failed \
    --timeout-s 216000 \
    --memory-limit-gb 8.0 \
    --imps missforest,softimpute \
    > /workspace/prep_slow_retry.log 2>&1 &

# 3. Light imputation can run in parallel with the above:
nohup python run_prep_parallel.py \
    --n-workers 4 \
    --skip-if-exists \
    --timeout-s 7200 \
    --memory-limit-gb 5.0 \
    --imps strict,knn \
    > /workspace/prep_fast.log 2>&1 &

# Monitor:
tail -f /workspace/prep_slow_retry.log
```

Apply the cgroup-aware `_free_gb()` fix (§3.1) to both scripts before the next run so the memory guard actually reflects container-level RAM.

---

## 6. Implementation Status

| Task | File(s) | Status |
|---|---|---|
| Fix `_free_gb()` — cgroup-aware memory reading | `run_prep_parallel.py`, `run_prep_job.py`, `run_norm_parallel.py`, `run_norm_job.py` | ✅ Done |
| Fix `capture_output=True` — stream worker output via `Popen` | `run_prep_parallel.py`, `run_norm_parallel.py` | ✅ Done |
| Add SIGTERM handler (sync failed-jobs log on Karpenter drain) | `run_prep_parallel.py`, `run_norm_parallel.py` | ✅ Done |
| Move `import subprocess` to top level in dispatchers | `run_prep_parallel.py`, `run_norm_parallel.py` | ✅ Done |
| Add `import signal, threading` to dispatchers | `run_prep_parallel.py`, `run_norm_parallel.py` | ✅ Done |
| Add `_stream_and_forward()` helper (real-time worker output) | `run_prep_parallel.py`, `run_norm_parallel.py` | ✅ Done |
| Add `_ts()` timestamp helper | all 4 Python files | ✅ Done |
| Add detailed progress logging in prep worker | `run_prep_job.py` | ✅ Done |
| Add detailed progress logging in norm worker | `run_norm_job.py` | ✅ Done |
| Add job-start log line with free RAM in dispatchers | `run_prep_parallel.py`, `run_norm_parallel.py` | ✅ Done |
| Install `tmux` and `htop` in pod-ssh.yaml | `k8s/pod-ssh.yaml` | ✅ Done |
