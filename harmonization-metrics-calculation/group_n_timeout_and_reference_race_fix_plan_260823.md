# Fix Group N timeout + Group L reference-cache race — plan (2026-08-23)

## Overview

The L/M/N blind-check run launched on 2026-08-23 (`logs_all_metrics_260823.txt`,
`--groups L,M,N --n-workers 20 --timeout-s 3600 --n-perm 100`) failed completely: **every job
that reached Group N in this run (58 "Starting group N" lines) was killed by the 3600s timeout
before finishing — 0 completions, 40 recorded `FAILED ... rc=-9` entries so far.** Separately,
**19 jobs hit a `FileNotFoundError` while loading the Group L reference** and had Group L silently
skipped, and **any job killed by the timeout throws away every group it had already finished**,
because the metrics JSON is currently only uploaded to S3 once, at the very end of the job. Three
independent problems, three independent fixes:

1. **Root cause of the timeout — diagnosed live on the pod, not assumed.** I connected via
   `kubectl port-forward pod/fl-metrics 2222:22 -n ${K8S_NAMESPACE}` and inspected the
   actually-running processes. Findings, in order:
   - The pod's physical node is 48 vCPU / 369 GiB RAM, confirming Daniil's correction — **but the
     container's cgroup CPU quota is capped at 32 cores** (`/sys/fs/cgroup/cpu.max` →
     `3200000 100000` = 32), matching `k8s/pod-metrics.yaml`'s `resources.limits.cpu: "32"`. The
     node has 48 cores; the container is only allowed 32 of them.
   - `OMP_NUM_THREADS` / `OPENBLAS_NUM_THREADS` / `MKL_NUM_THREADS` are declared in the manifest
     (`k8s/pod-metrics.yaml:115-120`, all set to `"1"`) but are **completely absent** from the
     environment of the actually-running `run_metrics_job.py` worker processes
     (`/proc/<pid>/environ`, filtered grep, zero matches).
   - Because those env vars never reach the worker, `threadpoolctl.threadpool_info()` (run inside
     the pod) shows numpy's OpenBLAS, scipy's OpenBLAS, and scikit-learn's OpenMP (`libgomp`) **all
     defaulting to 48 threads each** — they read `os.cpu_count()` / `sched_getaffinity()`, which
     report the *physical node's* 48 cores, not the container's 32-core quota.
   - A live worker process (`pid 41938`, mid Group-N) has **95 OS threads**. With 20 concurrent
     worker processes, that is on the order of ~900+ threads contending for a 32-core quota.
   - `uptime` on the pod: **load average 131–207**, on a container quota'd to 32 cores — 4–6x
     oversubscribed.
   - This mechanism fully explains the observed ~15x slowdown (243s isolated Group N measurement
     in `marker_and_predictive_validation_plan_260819.md` vs. >3300s and still not finishing here):
     it is not primarily about `n_perm`, worker count, or vCPU provisioning — it is unconstrained
     BLAS/OpenMP thread fan-out per process, stacked 20-deep.
   - **Most likely explanation for why the manifest's env vars don't reach the worker:** the
     dispatcher is launched from an interactive SSH session
     (`harmonization-metrics-calculation/CLAUDE.md` operational workflow — rsync + ssh port-forward
     + manual `nohup python run_metrics_parallel.py ...`). An SSH login shell does not inherit the
     container's `ENTRYPOINT`-declared environment unless `sshd` is explicitly configured to pass
     it through (`PermitUserEnvironment yes` + `~/.ssh/environment`, or similar) — the manifest's
     `env:` stanza governs the container's PID 1 process tree, not a separately-spawned SSH session.
     **Fix:** set the thread-limit env vars at the very top of `run_metrics_job.py` itself, before
     any numpy-touching import, so the limit is self-contained in the worker and does not depend on
     how the script was launched.
2. **Group L reference-cache race** (independent bug, does *not* explain the timeout — the second
   wave of jobs got clean cache hits and *still* timed out). Concurrent workers racing to fill a
   cold cache for the same `(strat, imp)` pair all write to the *same* hardcoded `.partial`
   filename; whichever finishes last wins, every other loses with `FileNotFoundError`. Fix: unique
   temp filename per process before the atomic rename.
3. **No incremental persistence** — `run_metrics_job.py` only uploads a job's metrics JSON to S3
   *after* `compute_all_metrics()` returns in full (`main()`,
   `run_metrics_job.py:479-539`). A `SIGKILL` mid-Group-N — whether from a genuine timeout or any
   future group failure — throws away every group that job had *already* successfully computed in
   that attempt (Groups L and M in this run's case), and every retry recomputes them from scratch,
   which also re-triggers the reference-cache race for that `(strat, imp)` pair. Fix: upload the
   merged metrics to S3 after **every** group completes, not just at the very end, so a group that
   fails or times out never destroys the groups that already succeeded.

**Design decision:** fix the thread-oversubscription bug first — it is the dominant, now-measured
cause and fixing it should alone bring Group N back under the 243s ballpark even at `n_perm=100`
(32-core quota ÷ 20 single-threaded processes ≈ 1.6x contention, not ~15x). On top of that, still
lower the default `n_perm` from 100 to 20 as a cheap, statistically-justified safety margin (the
empirical p-value floor `1/(n_perm+1)` stays under the conventional 0.05 threshold, unlike
`n_perm=10`) — this costs nothing and protects against the thread-pinning fix not being perfectly
effective everywhere it needs to be, or against a future run with more workers. Fix the reference
cache race and add incremental per-group upload as independent correctness/robustness
improvements; both are worth doing regardless of the thread-pinning outcome.

---

## Background / reference data

| Quantity | Value | Source |
|---|---|---|
| Jobs launched this run | 2,318 | `logs_all_metrics_260823.txt:6` |
| Workers | 20 | `logs_all_metrics_260823.txt:6` |
| Timeout | 3600s | `logs_all_metrics_260823.txt:6` |
| `n_perm` used | 100 | launch command (confirmed live: `ps aux` on the pod shows `--n-perm 100` on every current worker) |
| Jobs timed out so far | 40 (2 full waves of 20) | `grep -c TIMEOUT` |
| "Starting group N" count | 58 | `grep -c "Starting group N"` |
| "Group N done" count | **0** | `grep -c "Group N done"` — no job has ever finished Group N in this run |
| Reference-cache race errors | 19 (`FileNotFoundError`) | `grep -c "Reference load failed"` |
| Pod physical node | 48 vCPU / 369 GiB RAM | live `nproc` + `free -h` on the pod |
| **Pod container cgroup CPU quota** | **32 cores** | live `/sys/fs/cgroup/cpu.max` → `3200000 100000`; matches `k8s/pod-metrics.yaml:124` `resources.limits.cpu: "32"` |
| Thread-limit env vars in manifest | `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1` | `k8s/pod-metrics.yaml:115-120` |
| Same env vars in the live running worker process | **absent (0 matches)** | live `/proc/<pid>/environ`, filtered grep, pid 41938 |
| BLAS/OpenMP thread count actually in effect | **48 threads**, ×3 libraries (numpy OpenBLAS, scipy OpenBLAS, sklearn OpenMP/libgomp) | live `threadpoolctl.threadpool_info()` on the pod |
| OS thread count of one live worker process | **95** | live `ls /proc/<pid>/task \| wc -l`, pid 41938 |
| Load average during the run | **131 – 207** | live `uptime` on the pod (32-core quota) |
| Profiled worst-case Group N (isolated, 1 thread, `n_perm=100`, 24 folds) | ~243s | `marker_and_predictive_validation_plan_260819.md` "Runtime estimate" table |
| Profiled recommendation | 48 vCPU / 40 workers, ~3.4h total batch | same doc |
| p-value floor formula | `1/(n_perm+1)` | `compute_batch_metrics.py:2177-2199`, `_f1_perm_pvalue` |

**Fold/permutation cost model** (`compute_group_n`, `compute_batch_metrics.py:2081-2213`): for each
of 2 label sets (`lobo3`, `lobo2`), `_run_lobo` is called once for the observed labels and once per
permutation — `2 × (1 + n_perm)` full leave-one-batch-out passes, each fitting one
`LogisticRegression` per surviving `RNA_BATCH` fold. At `n_perm=100` that is up to `2×101×24 ≈
4,848` fits for the worst-case strategy. Runtime is linear in `n_perm`, and — per the live
diagnosis above — each of those fits was also fanning out into up to 48 BLAS/OpenMP threads with
20 processes doing so simultaneously.

| `n_perm` | LOBO passes (`2×(n_perm+1)`) | p-value floor | Isolated est. (scaled from 243s @ 100) |
|---|---|---|---|
| 100 (current) | 202 | 0.0099 | 243s single-threaded; **>3300s and non-completing under the diagnosed thread storm** |
| 20 (recommended) | 42 | 0.048 | ~51s single-threaded; expected low-single-digit minutes even with the thread-pinning fix only partially effective |
| 10 | 22 | 0.091 (not significant at conventional thresholds) | ~27s |

`n_perm=20` keeps the p-value floor under the conventional 0.05 significance threshold (unlike
`n_perm=10`, which the existing plan document already rejected for this reason) while giving a
large safety margin on top of the thread-pinning fix, for both the documented worst-case strategy
(`S0_no_removal`, 24 folds) and the smaller `A_confirmed_bad` cohort that is failing right now.

---

## Files to change

### 1. `harmonization-metrics-calculation/run_metrics_job.py` — pin BLAS/OpenMP threads at the top of the file

**Why this file and not just the k8s manifest:** the manifest already declares the right env vars,
but they do not reach the worker process in practice (diagnosed live, see Overview). Setting them
in `os.environ` at the very top of the script — before `boto3`, `pandas`, or
`compute_batch_metrics` (which pulls in numpy/scipy/scikit-learn) are imported — makes the limit
self-contained in the worker itself, independent of whether it was launched from the pod's declared
environment, an SSH shell, cron, or anything else. `setdefault` (not a hard overwrite) is used so an
operator can still raise the limit deliberately by exporting a different value before launching.

**1a. Add the thread-pinning guard immediately after `from __future__ import annotations`, and add
`import os` / `import uuid` to the stdlib import block**

Before (`run_metrics_job.py:35-48`):
```python
from __future__ import annotations

import argparse
import gc
import gzip
import io
import json
import sys
import time
import traceback
from pathlib import Path

import boto3
import pandas as pd
```

After:
```python
from __future__ import annotations

import os

# Must run before numpy/scipy/scikit-learn are imported (directly, or transitively via
# pandas / compute_batch_metrics below) — BLAS and OpenMP read these once at library load
# time. The k8s manifest also sets these, but this worker is launched from an interactive
# SSH session in practice, which does not inherit the container's declared environment, so
# the manifest's values never reach this process. setdefault() keeps a manual override
# possible without weakening the safety net.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import argparse
import gc
import gzip
import io
import json
import sys
import time
import traceback
import uuid
from pathlib import Path

import boto3
import pandas as pd
```

---

### 2. `harmonization-metrics-calculation/run_metrics_job.py` — fix the reference-cache race

**2a. Give each process a unique temp file before the atomic rename**

Why: `cache_path` is deterministic from `(strat, imp)` alone, so every worker process racing to
fill a cold cache computes the *same* `tmp_path = cache_path.with_suffix(".partial")`
(`run_metrics_job.py:208`, pre-edit numbering). Concurrent `gzip.open(tmp_path, "wb")` calls from
different processes write to the same path; whichever process calls `tmp_path.replace(cache_path)`
first "wins," and every other process's `tmp_path.replace(...)` then fails with
`FileNotFoundError` because the shared path it wrote to no longer exists under that name (log line:
`'/workspace/ref_cache/....tsv.partial' -> '....tsv.gz'`). `os.replace()` is atomic and silently
overwrites an existing destination, so making the source path unique per-process is sufficient —
whichever process finishes last simply overwrites the file with byte-identical content (all
processes downloaded the same S3 object).

Before (`run_metrics_job.py:202-213`, pre-edit numbering):
```python
    print(
        f"[{_ts()}][{label}] Reference cache miss — downloading {key} ...", flush=True
    )
    body = gzip.decompress(
        s3_client.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()  # type: ignore[attr-defined]
    )
    tmp_path = cache_path.with_suffix(".partial")
    with gzip.open(tmp_path, "wb") as fh:
        fh.write(body)
    tmp_path.replace(
        cache_path
    )  # atomic, so concurrent workers never read a partial file
```

After:
```python
    print(
        f"[{_ts()}][{label}] Reference cache miss — downloading {key} ...", flush=True
    )
    body = gzip.decompress(
        s3_client.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()  # type: ignore[attr-defined]
    )
    # Unique per-process suffix: cache_path is deterministic from (strat, imp), so
    # concurrent cache misses on the same pair must not share one temp filename —
    # os.replace() is atomic and overwrites cleanly, so only the *source* needs to
    # be unique, not the destination.
    tmp_path = cache_path.with_suffix(f".partial.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    with gzip.open(tmp_path, "wb") as fh:
        fh.write(body)
    tmp_path.replace(
        cache_path
    )  # atomic, so concurrent workers never read a partial file
```

No other change is needed in this function: `cache_path.exists()` still short-circuits for any
worker that starts *after* the winner has renamed its file into place, so this only affects the
thundering-herd window when many workers miss the cache at the same instant for a brand-new
`(strat, imp)` pair.

---

### 3. `harmonization-metrics-calculation/compute_batch_metrics.py` — upload after every group, not just at the end

**Why:** today, `compute_all_metrics()`'s internal `_flush()` (`compute_batch_metrics.py:2270-2273`)
only writes the accumulated result to the **local** `tmp_path` after each group finishes; nothing
reaches S3 until `run_metrics_job.py::main()` calls `_upload_json()` once, after
`compute_all_metrics()` returns in full. If the process is killed mid-group (a timeout, an OOM, or
any future failure), every group computed earlier in that same attempt — already correct, already
paid for — is discarded, and the next retry recomputes all of it from scratch. This is exactly what
happened to Groups L and M in every one of the 40 timed-out jobs in this run. Making each group
durable the moment it finishes means a Group N timeout only ever costs Group N.

**3a. Add an `on_group_done` callback parameter to `compute_all_metrics()`**

Before (`compute_batch_metrics.py`, function signature — locate via
`def compute_all_metrics(`):
```python
def compute_all_metrics(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    *,
    skip_slow: bool = False,
    tmp_path: Optional[str] = None,
    groups: Optional[set[str]] = None,
    ref_df: Optional[pd.DataFrame] = None,
    n_perm: int = N_PERM,
    panel: Optional[object] = None,
    collect_gene_cohort_detail: bool = False,
) -> dict:
```

After:
```python
def compute_all_metrics(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    *,
    skip_slow: bool = False,
    tmp_path: Optional[str] = None,
    groups: Optional[set[str]] = None,
    ref_df: Optional[pd.DataFrame] = None,
    n_perm: int = N_PERM,
    panel: Optional[object] = None,
    collect_gene_cohort_detail: bool = False,
    on_group_done: Optional[Callable[[dict], None]] = None,
) -> dict:
```

Add `Callable` to the existing `from typing import Optional` import (→ `from typing import Callable, Optional`).

Document the new parameter in the docstring's `Parameters` section:
```
    on_group_done : callable, optional
        Called with a shallow copy of the accumulated result dict after every group
        finishes (success or failure). Intended for durable incremental persistence
        (e.g. re-uploading the merged sidecar to S3) so a later group's crash or
        timeout cannot discard groups that already completed. Exceptions raised by
        this callback are caught and logged, never allowed to abort metric
        computation.
```

**3b. Call it from `_flush()`**

Before (`compute_batch_metrics.py:2270-2273`, pre-edit numbering):
```python
    def _flush() -> None:
        if tmp_path:
            with open(tmp_path, "w") as fh:
                fh.write(dict_to_json_safe(result))
```

After:
```python
    def _flush() -> None:
        if tmp_path:
            with open(tmp_path, "w") as fh:
                fh.write(dict_to_json_safe(result))
        if on_group_done is not None:
            try:
                on_group_done(dict(result))
            except Exception:
                print(
                    f"[{_ts()}][metrics] on_group_done callback FAILED:\n"
                    f"{traceback.format_exc()}",
                    flush=True,
                )
```

`_flush()` already runs after every `_run_group(...)` call (including the PCA/UMAP/tSNE embedding
steps and the Group L skip-path), so no other call site needs to change.

---

### 4. `harmonization-metrics-calculation/run_metrics_job.py` — wire the callback to an incremental S3 upload

**4a. Define the incremental-upload closure and pass it into `compute_all_metrics()`**

Locate the `compute_all_metrics(...)` call in `main()` (`run_metrics_job.py:481-492`, pre-edit
numbering):

Before:
```python
    try:
        new_metrics = compute_all_metrics(
            exp_df,
            ann_df,
            skip_slow=args.skip_slow,
            tmp_path=args.out_json,
            groups=groups_to_run,
            ref_df=ref_df,
            n_perm=args.n_perm,
            panel=panel,
            collect_gene_cohort_detail=args.save_gene_cohort_detail,
        )
        status = "ok"
```

After:
```python
    def _upload_partial(partial: dict) -> None:
        merged: dict = dict(prior_metrics) if prior_metrics else {}
        merged.update(partial)
        merged["strat"] = args.strat
        merged["imp"] = args.imp
        merged["method"] = args.method
        merged["post_rm"] = post_rm
        merged["status"] = "ok"
        _upload_json(s3, metrics_key, dict_to_json_safe(merged))

    try:
        new_metrics = compute_all_metrics(
            exp_df,
            ann_df,
            skip_slow=args.skip_slow,
            tmp_path=args.out_json,
            groups=groups_to_run,
            ref_df=ref_df,
            n_perm=args.n_perm,
            panel=panel,
            collect_gene_cohort_detail=args.save_gene_cohort_detail,
            on_group_done=_upload_partial,
        )
        status = "ok"
```

`status="ok"` is deliberate on every incremental upload, not just the final one: `_load_prior_metrics`
discards the entire sidecar if `status != "ok"` (`run_metrics_job.py:87`), and the per-group resume
decision is already made correctly at the sentinel-key level in `_groups_to_recompute` regardless of
which groups are present yet — an intermediate upload with, say, L and M present but N's sentinel
key still missing is exactly the state the incremental resume logic is designed to read. The final
upload at the end of `main()` (unchanged) still runs after this and additionally stamps
`compute_time_s`.

Note the exception handling inside `_upload_partial` is intentionally left to `compute_batch_metrics.py`'s
`on_group_done` wrapper (§3b) — `_upload_partial` itself can raise and it will be caught and logged
there, never propagating up to abort a group's computation.

---

### 5. `harmonization-metrics-calculation/compute_batch_metrics.py` — lower the default `N_PERM`

**5a. Change the module-level constant**

Before (line 85):
```python
N_PERM: int = 100
```

After:
```python
N_PERM: int = 20
```

Why here and not only on the CLI: `run_metrics_job.py`'s `--n-perm` argparse default is
`default=N_PERM` (imported from this module), so a single-job smoke test or ad-hoc invocation that
forgets to pass `--n-perm` explicitly no longer risks reproducing the failure. `test_mock_metrics.py`
always passes an explicit `n_perm=` value to `compute_group_n` (2, 10, 20, or 50 — grepped, none
rely on the module default), so this does not change smoke-test behavior.

---

### 6. `harmonization-metrics-calculation/run_metrics_parallel.py` — update the stale example command

**6a. Module docstring launch example** (this is the block `harmonization-metrics-calculation/CLAUDE.md`
and `README.md` both mirror)

Before (lines 19-27):
```python
# Blind final check (groups L, M, N) over every attempt that already has a sidecar.
# Do NOT pass --skip-if-exists here: every target job has a sidecar already, so it
# would skip all of them. The incremental sentinel logic inside the worker is what
# provides the resume behaviour — it recomputes only the groups that are missing.
# Set --n-workers to roughly (vCPU - 8) on whatever node is provisioned.
nohup python run_metrics_parallel.py \\
    --groups L,M,N --only-with-metrics --skip-shambhala \\
    --n-workers 40 --memory-limit-gb 8.0 --timeout-s 1800 \\
    --n-perm 100 --ref-cache-dir /workspace/ref_cache \\
    > /workspace/metrics_lmn.log 2>&1 &
```

After:
```python
# Blind final check (groups L, M, N) over every attempt that already has a sidecar.
# Do NOT pass --skip-if-exists here: every target job has a sidecar already, so it
# would skip all of them. The incremental sentinel logic inside the worker is what
# provides the resume behaviour — it recomputes only the groups that are missing.
# Set --n-workers to roughly (vCPU - 8) on whatever node is provisioned.
# n_perm=100 timed out every job at 3600s on 2026-08-23 — root cause was BLAS/OpenMP
# thread fan-out (48 threads/process x 20 processes on a 32-core cgroup quota), now
# pinned to 1 thread inside run_metrics_job.py itself; n_perm=20 is kept as a cheap
# additional safety margin (p-value floor 1/(n_perm+1) stays under 0.05). See
# group_n_timeout_and_reference_race_fix_plan_260823.md for the full diagnosis.
nohup python run_metrics_parallel.py \\
    --groups L,M,N --only-with-metrics --skip-shambhala \\
    --n-workers 20 --memory-limit-gb 8.0 --timeout-s 3600 \\
    --n-perm 20 --ref-cache-dir /workspace/ref_cache \\
    > /workspace/metrics_lmn.log 2>&1 &
```

**6b. `--n-perm` help string** (line 70)

Before:
```
    Label permutations for the Group N negative control (worker default: 100).
```

After:
```
    Label permutations for the Group N negative control (worker default: 20).
```

**6c. `--n-perm` argparse help text** (line 487)

Before:
```python
        help="Label permutations for the Group N control (worker default: 100).",
```

After:
```python
        help="Label permutations for the Group N control (worker default: 20).",
```

---

### 7. `harmonization-metrics-calculation/README.md` — same stale example (Step 10e)

Before (lines 260-267):
```
```bash
# Do NOT pass --skip-if-exists: every target job already has a sidecar, so it would skip
# all of them. The worker's incremental sentinel logic provides the resume behaviour.
# Set --n-workers to roughly (vCPU - 8) on the node you provisioned.
nohup python run_metrics_parallel.py \
    --groups L,M,N --only-with-metrics --skip-shambhala \
    --n-workers 40 --memory-limit-gb 8.0 --timeout-s 1800 \
    --n-perm 100 --ref-cache-dir /workspace/ref_cache \
    > /workspace/metrics_lmn.log 2>&1 &
```
```

After:
```
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
```

---

### 8. `harmonization-metrics-calculation/CLAUDE.md` — same stale example command

Before:
```
# ── Blind final check: metric groups L (marker correlation), M (rank agreement), N (prediction) ──
# Do NOT pass --skip-if-exists: every target job already has a sidecar, so it would skip
# all of them. The worker's incremental sentinel logic provides the resume behaviour.
# Set --n-workers to roughly (vCPU - 8) on whatever node is provisioned.
nohup python run_metrics_parallel.py \
    --groups L,M,N --only-with-metrics --skip-shambhala \
    --n-workers 40 --memory-limit-gb 8.0 --timeout-s 1800 \
    --n-perm 100 --ref-cache-dir /workspace/ref_cache \
    > /workspace/metrics_lmn.log 2>&1 &
python run_metrics_concat.py   # → metrics_comprehensive.csv + 3 long-format tables
```

After:
```
# ── Blind final check: metric groups L (marker correlation), M (rank agreement), N (prediction) ──
# Do NOT pass --skip-if-exists: every target job already has a sidecar, so it would skip
# all of them. The worker's incremental sentinel logic provides the resume behaviour.
# Set --n-workers to roughly (vCPU - 8) on whatever node is provisioned.
# n_perm=20 (not 100): n_perm=100 timed out every job at 3600s on 2026-08-23 — diagnosed as
# BLAS/OpenMP thread fan-out (declared-but-not-inherited env vars), now pinned inside
# run_metrics_job.py itself; n_perm=20 is kept as a belt-and-suspenders margin. See
# harmonization-metrics-calculation/group_n_timeout_and_reference_race_fix_plan_260823.md.
nohup python run_metrics_parallel.py \
    --groups L,M,N --only-with-metrics --skip-shambhala \
    --n-workers 20 --memory-limit-gb 8.0 --timeout-s 3600 \
    --n-perm 20 --ref-cache-dir /workspace/ref_cache \
    > /workspace/metrics_lmn.log 2>&1 &
python run_metrics_concat.py   # → metrics_comprehensive.csv + 3 long-format tables
```

Also add one line to the "Key design patterns" section documenting the new incremental-upload
behavior, immediately after the existing "**Incremental computation**" paragraph:

```
**Incremental persistence** — every group's result is uploaded to S3 as soon as it finishes
(`on_group_done` callback threaded through `compute_all_metrics()` → `_upload_partial()` in
`run_metrics_job.py`), not just once at the very end. A timeout or crash during a later group
(e.g. Group N) no longer discards groups that already completed in the same attempt.
```

---

## Files that do NOT need to change

| File | Why not |
|---|---|
| `k8s/pod-metrics.yaml` | The env vars it declares are correct in principle; the fix is making the worker self-sufficient regardless of whether they arrive, since the live pod demonstrates they currently don't. Raising `resources.limits.cpu` from `"32"` to `"48"` to use the full physical node is a legitimate follow-up infra decision, but is not required for correctness once threads are pinned to 1 — flagged under Side effects, not made part of this fix. |
| `test_mock_metrics.py` | All 10 `compute_group_n` call sites pass an explicit `n_perm=` value; none rely on the `N_PERM` module default, so lowering it does not change test behavior or coverage. The new `on_group_done` parameter defaults to `None`, so none of the existing `compute_all_metrics(...)` calls in this file need updating. |
| `marker_gene_annotation.csv`, `marker_panels.py`, `build_marker_gene_annotation.py` | Unrelated to Group N, thread pinning, or the reference-cache path. |
| `run_metrics_concat.py` | Aggregation only; `pv_n_perm` is recorded per-job from whatever value each job actually ran with, so historical rows keep their true `n_perm` regardless of the new default. It reads whatever is on S3 at the time it is run (after the dispatcher finishes), so intermediate partial uploads mid-run are not a concern for it. |
| `figures_helpers.py` | The `_BLIND_CHECK_PREFIXES` exclusion (`mk_`, `xb_`, `pv_`) is unaffected — L/M/N stay out of the Figure 3 clustermap either way. |
| `harmonization-metrics/marker_and_predictive_validation_plan_260819.md` | Historical planning document; left as-is. Its 48-vCPU/40-worker recommendation remains a valid alternative lever, referenced above, not superseded. |
| `failed_jobs_metrics.txt` | Runtime artifact on the pod, not in the repo; see Verification below for how it interacts with the retry. |

---

## Side effects and caveats

- **`/workspace/ref_cache` does not need to be deleted.** The race fix only changes the *temp*
  filename; the final cached file at `cache_path` is byte-identical to what any single winning
  process would have produced today, so an already-successfully-cached reference file is still
  valid.
- **Every job that failed in this run (40 timeouts, and likely more accumulating while this pod
  keeps running unfixed code) needs to be retried** with the corrected worker. Since these jobs
  never uploaded a metrics JSON before this fix (killed before `main()` reaches the upload step), a
  plain re-run of the same dispatcher command will naturally pick them back up —
  `--only-with-metrics` still matches them (their *prior* A–K sidecar is untouched) and the
  incremental sentinel logic in `_groups_to_recompute` will see `mk_rho_mean_all_genes` /
  `xb_rank_agree` / `pv_lobo3_f1_macro_mean` all still missing and recompute L, M, and N fresh.
  **Do not pass `--retry-failed`** unless you also want to bypass `failed_jobs_metrics.txt`'s
  dedup — the incremental logic alone is sufficient here, consistent with the existing
  "do NOT pass `--skip-if-exists`" guidance for this command.
- **The live pod should be relaunched (or at minimum, the current dispatcher process killed and
  restarted) after this fix lands**, not just have new code rsynced in — the currently-running
  worker processes already have the broken (unthreaded-pinned, `n_perm=100`) code loaded in memory
  and will keep running that way until they are stopped. Kill the dispatcher and any live
  `run_metrics_job.py` children before re-syncing and relaunching.
- **Incremental S3 uploads add write traffic:** up to one `PUT` per completed group per job instead
  of one per job — for a full A–N run that is up to 14 extra small JSON `PUT`s instead of 1. Each
  payload is a dict of scalar metrics (tens of KB), so this is negligible added latency/cost, not a
  performance concern, and is exactly the durability this fix is for.
- **`pv_n_perm` will legitimately vary across `metrics_comprehensive.csv` rows** going forward —
  any job that completes under the corrected code will show `pv_n_perm=20`; nothing in the failed
  run has ever recorded `pv_n_perm=100` successfully (0 "Group N done" lines), so there is no
  mixed-`n_perm` legacy data to reconcile in the N-group columns yet.
- **Statistical resolution:** `n_perm=20` caps the smallest possible empirical p-value at
  `1/21 ≈ 0.048`. This is enough to call a result "significant at p<0.05" but not enough to report
  a highly significant value like the `0.0099` seen in the one real `S0_no_removal` measurement
  from 2026-08-19. If a specific attempt's Group N result needs finer p-value resolution for the
  manuscript, that one job can be re-run standalone with a higher `--n-perm` (e.g. via
  `run_metrics_job.py` directly, `--groups N`) without affecting the rest of the batch — and with
  threads now actually pinned to 1, a much higher `n_perm` becomes affordable again if wanted.
  `pv_n_perm` in the output records exactly which count was used per job, so this is auditable.
- **The manifest's 32-core cgroup limit vs. the 48-core physical node is a separate, optional
  lever.** Once threads are genuinely pinned to 1 per process, 20 or even 40 workers within a
  32-core quota is reasonable contention (not the ~30x thread-count-to-core oversubscription
  diagnosed above). Raising `resources.requests/limits.cpu` to `"48"` in `k8s/pod-metrics.yaml` and
  correspondingly raising `--n-workers` toward the documented `(vCPU − 8)` guidance (≈40) would let
  the batch use the full node and finish faster, matching the original 48-vCPU/40-worker
  recommendation in `marker_and_predictive_validation_plan_260819.md` — but this is a throughput
  optimization, not required to stop the timeouts.

---

## Verification commands

```bash
# 1. Smoke test — confirms the lowered N_PERM default and the new on_group_done parameter
#    don't break any assertion
source ~/venvs/collagen_3_11/bin/activate   # or the pod's environment
cd harmonization-metrics-calculation
python test_mock_metrics.py

# 2. Confirm the new default is picked up
python -c "from compute_batch_metrics import N_PERM; print(N_PERM)"   # expect: 20

# 3. Confirm thread pinning takes effect BEFORE any job runs (run this on the pod, after
#    rsyncing the fixed run_metrics_job.py, before launching the dispatcher)
python -c "
import subprocess
# Runs just the top-of-file guard + a trivial import, no S3 access needed
subprocess.run(['python', '-c', '''
import runpy, sys
sys.argv = [\"run_metrics_job.py\", \"--help\"]
try:
    runpy.run_path(\"run_metrics_job.py\", run_name=\"__main__\")
except SystemExit:
    pass
import os
for k in (\"OMP_NUM_THREADS\", \"OPENBLAS_NUM_THREADS\", \"MKL_NUM_THREADS\", \"NUMEXPR_NUM_THREADS\"):
    print(k, os.environ.get(k))
'''])
"
# Simpler equivalent: just check the process env of a live worker once one job is running
PID=$(pgrep -f run_metrics_job.py | head -1)
cat /proc/$PID/environ | tr '\0' '\n' | grep -E '^(OMP|OPENBLAS|MKL|NUMEXPR)_NUM_THREADS'
# expect all four printed as =1

# 4. Confirm threadpoolctl now reports 1 thread per library while a job is running
python -c "import threadpoolctl, json; print(json.dumps(threadpoolctl.threadpool_info(), indent=2))"
# expect num_threads: 1 for every entry (previously: 48)

# 5. Single-job timed test on the pod — the fastest way to confirm the fix actually
#    finishes Group N within budget before committing to the full 2,318-job run again.
#    Run this for the SAME strat/imp/method that timed out (A_confirmed_bad/knn/03_limma)
#    so it is a like-for-like comparison against the failed run.
time python run_metrics_job.py \
    --strat A_confirmed_bad --imp knn --method 03_limma \
    --post-rm True \
    --out-json /tmp/test_lmn.json --out-genes-json /tmp/test_genes.json \
    --groups L,M,N --n-perm 20 --ref-cache-dir /workspace/ref_cache
python -c "
import json
d = json.load(open('/tmp/test_lmn.json'))
print('status:', d.get('status'))
print('pv_n_perm:', d.get('pv_n_perm'))
print('pv_lobo3_n_folds:', d.get('pv_lobo3_n_folds'))
print('pv_lobo3_f1_macro_mean:', d.get('pv_lobo3_f1_macro_mean'))
print('mk_rho_mean_all_genes:', d.get('mk_rho_mean_all_genes'))
print('xb_rank_agree:', d.get('xb_rank_agree'))
print('compute_time_s:', d.get('compute_time_s'))
"

# 6. Confirm incremental persistence: kill a job mid-Group-N on purpose and check the
#    sidecar on S3 already has L and M filled in even though the job never finished.
time python run_metrics_job.py \
    --strat A_confirmed_bad --imp knn --method 04_sva \
    --post-rm True \
    --out-json /tmp/test_partial.json --out-genes-json /tmp/test_partial_genes.json \
    --groups L,M,N --n-perm 20 --ref-cache-dir /workspace/ref_cache &
JOB_PID=$!
sleep 20   # let L and M finish, N still running
kill -9 $JOB_PID
python -c "
import boto3, json
s3 = boto3.client('s3')
key = 'FL_batch_correction/metrics/A_confirmed_bad__knn__04_sva__post1_metrics.json'
obj = s3.get_object(Bucket='$FL_S3_BUCKET', Key=key)
d = json.loads(obj['Body'].read())
print('mk_rho_mean_all_genes (Group L):', d.get('mk_rho_mean_all_genes'))
print('xb_rank_agree (Group M):', d.get('xb_rank_agree'))
print('pv_lobo3_f1_macro_mean (Group N, expect None — job was killed):', d.get('pv_lobo3_f1_macro_mean'))
"

# 7. Reference-cache race — reproduce and confirm the fix under real concurrency by
#    launching several single jobs for the SAME (strat, imp) pair against a cold cache
#    at the same time (delete the cached file first) and checking none raise FileNotFoundError.
rm -f /workspace/ref_cache/A_confirmed_bad__knn__01_raw__post0.tsv.gz
for m in 03_limma 04_sva 05_combat; do
  python run_metrics_job.py --strat A_confirmed_bad --imp knn --method "$m" \
    --post-rm True --out-json /tmp/race_$m.json --out-genes-json /tmp/race_g_$m.json \
    --groups L --ref-cache-dir /workspace/ref_cache &
done
wait
grep -l "Reference load failed" /tmp/race_*.json 2>/dev/null || echo "no race errors"

# 8. Stop the currently-running (unfixed) dispatcher and worker processes on the pod
#    before relaunching with the fixed code.
pkill -f run_metrics_parallel.py
pkill -f run_metrics_job.py

# 9. Full re-run with the fix
nohup python run_metrics_parallel.py \
    --groups L,M,N --only-with-metrics --skip-shambhala \
    --n-workers 20 --memory-limit-gb 8.0 --timeout-s 3600 \
    --n-perm 20 --ref-cache-dir /workspace/ref_cache \
    > /workspace/metrics_lmn_260823_retry.log 2>&1 &
tail -f /workspace/metrics_lmn_260823_retry.log   # watch for "Group N done (..s)" lines this time
```

---

## TODO

- [x] `run_metrics_job.py` — add `import os` immediately after `from __future__ import annotations`, plus the four `os.environ.setdefault(...)` thread-pinning lines, before any other import
- [x] `run_metrics_job.py` — add `import uuid` to the stdlib import block
- [x] `run_metrics_job.py` — make the Group L reference cache temp filename unique per process (`_load_reference_cached`)
- [x] `compute_batch_metrics.py` — add `Callable` to the `typing` import
- [x] `compute_batch_metrics.py` — add `on_group_done` parameter to `compute_all_metrics()` + docstring entry
- [x] `compute_batch_metrics.py` — call `on_group_done(dict(result))` inside `_flush()`, wrapped in try/except
- [x] `compute_batch_metrics.py` — lower `N_PERM` default from `100` to `20`
- [x] `run_metrics_job.py` — define `_upload_partial()` closure in `main()` and pass it as `on_group_done=` to `compute_all_metrics(...)`
- [x] `run_metrics_parallel.py` — update module docstring example command (n-perm, timeout-s, n-workers, add explanatory comment referencing the diagnosis)
- [x] `run_metrics_parallel.py` — update `--n-perm` help text in the docstring block
- [x] `run_metrics_parallel.py` — update `--n-perm` argparse `help=` string
- [x] `README.md` — update Step 10e example command + add explanatory note
- [x] `CLAUDE.md` (harmonization-metrics-calculation) — update the blind-check example command + add explanatory note + add the "Incremental persistence" line to Key design patterns
- [x] Run `test_mock_metrics.py` to confirm no regressions (run on the pod with threads explicitly pinned in the shell, in an isolated `/tmp/verify_fix_260823` copy so the live run was not touched: **169 passed, 0 failed**)
- [x] Confirm thread pinning takes effect (verification commands 3–4), reproduced live on the pod with the manifest's env vars deliberately stripped from the shell first: `threadpoolctl.threadpool_info()` now reports `num_threads: 1` for numpy's OpenBLAS, scipy's OpenBLAS, and scikit-learn's OpenMP — down from 48 before the fix
- [x] Run the single-job timed verification (command 5) against the pod for the exact job that timed out (`A_confirmed_bad/knn/03_limma/post1`), run in the isolated copy against the real S3 sidecar: `status: ok`, `Group N done (305.9s)` — **the first successful Group N completion in this entire run (0/58 before)** — exit code 0, well under the 3600s timeout despite the still-running unfixed production dispatcher competing for the same CPU quota throughout
- [x] Run the incremental-persistence verification (command 6 equivalent): checked the real S3 sidecar for the job above *while Group N was still computing* — `mk_rho_mean_all_genes` (Group L) and `xb_rank_agree` (Group M) were already durably on S3 with `status: ok`, and the prior Group A key (`r2_RNA_BATCH`) was correctly preserved, confirming a kill at that point would not have lost L or M
- [x] Run the reference-cache race reproduction (command 7) against a genuinely cold cache (`/tmp/ref_cache_race_test`, never populated before): launched 4 concurrent jobs for the same `(strat, imp)` pair; **zero `FileNotFoundError`** — one process (`06_combat_seq`) won and uploaded successfully (`status: ok`), the other three's uniquely-named partial files coexisted without collision
- [ ] Stop the currently-running dispatcher and worker processes on the pod (they are running the unfixed `n_perm=100` code) — **not done; this stops Daniil's live/shared process and needs his explicit go-ahead, not a unilateral action**
- [ ] Rsync the fixed code from the local repo to the pod's live `/app/harmonization-metrics-calculation` (verification above ran from an isolated `/tmp/verify_fix_260823` copy on the pod, deliberately never touching the live directory or the running processes)
- [ ] Relaunch the full dispatcher with `--n-perm 20` (command 9) and watch for `"Group N done"` log lines at scale — the fix is verified on one representative job; the full 2,318-job retry is still pending Daniil's go-ahead per the point above
- [ ] After the run completes, run `run_metrics_concat.py` and spot-check `pv_n_perm == 20` and non-null `pv_*`/`mk_*`/`xb_*` columns for a sample of rows
- [ ] Decide separately (not part of this fix) whether to raise `k8s/pod-metrics.yaml`'s `resources.limits.cpu` from `"32"` to `"48"` and `--n-workers` toward ~40 to use the full physical node for a faster batch, now that threads are genuinely pinned
