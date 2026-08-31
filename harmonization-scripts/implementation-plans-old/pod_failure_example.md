# Pod OOM Failure: run_prep_parallel.py with 8 Workers

## What happened

**Exit code 137 = SIGKILL from the Linux OOM killer** (128 + signal 9). The Kubernetes pod exceeded its memory limit and the kernel killed the entire container — not just the Python process. That is why the pod phase becomes `Failed` and you can no longer exec into it.

### Failing command

```bash
nohup python run_prep_parallel.py \
    --n-workers 8 \
    --skip-if-exists \
    --timeout-s 216000 \
    --memory-limit-gb 4.0 \
    --imps knn,missforest,softimpute \
    > nohup.out 2>&1 &
```

### Root cause chain

1. **8 workers launched simultaneously** via `ThreadPoolExecutor(max_workers=8)`
2. `--imps knn,missforest,softimpute` — missForest and softImpute are R-based and peak at **6–8 GB each** per worker
3. The memory guard (`--memory-limit-gb 4.0`) only **blocks launching the next subprocess** when free RAM < 4 GB — but with 8 workers, all 8 can be submitted to the thread pool nearly simultaneously before any finishes and frees RAM
4. The dispatcher also **pre-caches** the full expression matrix (~2–3 GB) before spawning workers
5. Worst case: dispatcher cache (3 GB) + 8 workers × 6 GB = **~51 GB** against a 16 GiB pod limit

### Memory budget breakdown

| Component | RAM usage |
|---|---|
| Dispatcher pre-cache (expression matrix) | ~3 GB |
| 8 knn workers × ~2 GB each | ~16 GB |
| 8 missforest/softimpute workers × 6–8 GB each | ~48–64 GB |
| **Pod limit** (`memory: 16Gi` in `k8s/pod.yaml`) | **16 GiB** |

Even 3 simultaneous missForest workers would burst the 16 GiB ceiling.

---

## Immediate recovery

```bash
# 1. Delete the failed pod
kubectl delete pod fl-batch-correction -n ${K8S_NAMESPACE}

# 2. Recreate it
kubectl apply -f harmonization-scripts/k8s/pod.yaml

# 3. Wait for Running
kubectl get pod fl-batch-correction -n ${K8S_NAMESPACE} -w
```

---

## How to avoid this in the future

### 1. Separate slow imputation methods from knn

missForest and softImpute are R-based and far heavier than KNN. Run them in separate invocations with conservative worker counts:

```bash
# knn is fast and light — 4 workers is safe
nohup python run_prep_parallel.py \
    --n-workers 4 \
    --skip-if-exists \
    --timeout-s 7200 \
    --memory-limit-gb 5.0 \
    --imps knn \
    > /workspace/prep_knn.log 2>&1 &

# missforest/softimpute: 2 workers max on a 16 GiB pod
# (3 GB cache + 2 × 6 GB workers ≈ 15 GB, just under the limit)
nohup python run_prep_parallel.py \
    --n-workers 2 \
    --skip-if-exists \
    --timeout-s 216000 \
    --memory-limit-gb 6.0 \
    --imps missforest,softimpute \
    > /workspace/prep_slow.log 2>&1 &
```

### 2. Match `--memory-limit-gb` to per-worker peak usage

The dispatcher blocks launching a new subprocess only when `free_RAM < memory_limit_gb`. With missForest/softImpute peaking at 6 GB, set `--memory-limit-gb 6.0` so the guard fires before the next worker would push you over the edge. Combined with `--n-workers 2`, workers effectively run serially — safe on 16 GiB.

### 3. Write logs to the persistent PVC

`nohup.out` in the working directory is lost when the pod crashes. Use `/workspace/` (the `fl-workspace` PVC) instead so logs survive pod restarts:

```bash
nohup python run_prep_parallel.py ... > /workspace/prep_slow.log 2>&1 &
tail -f /workspace/prep_slow.log
```

---

## Recommended safe parameters for a 16 GiB pod

| Imputation | `--n-workers` | `--memory-limit-gb` | `--timeout-s` |
|---|---|---|---|
| `knn` | 4 | 5.0 | 7200 |
| `missforest` | 2 | 6.0 | 216000 |
| `softimpute` | 2 | 6.0 | 216000 |
| `strict` | 6 | 4.0 | 3600 |
