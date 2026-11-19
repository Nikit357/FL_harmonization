# Plan — the PVC-free revision pod on the ComboBatch image (2026-11-01)

Status: **approved and implemented 2026-11-01**; pilots run 2026-11-01/02, pod deleted, stopped at gate G3. Part B and B1 / B2 approved by
Daniil 2026-11-01.
Addendum to `revision_pod_without_pvc_plan_261101.md` (implemented: manifest + docs; its launch
TODO is blocked by the missing image).

## Overview

The PVC-free harmonization pod (`k8s/pod-revision-nopvc.yaml`) could not start:
`${ECR_URI}/fl-batch-correction:latest` answers **NotFound**
in ECR (2026-11-01, `ImagePullBackOff`). The old `pod-revision.yaml` uses the same image, so
both manifests are dead.

The change: run the pod on the **ComboBatch image**, `ghcr.io/nikit357/combobatch:20260830`.
It is public, has R 4.5.3 pinned, Bioconductor 3.22, and every R and Python package that the
frozen `bench_shared.py` and `compute_batch_metrics.py` import.

**Shambhala comes from Daniil's repository
[`Nikit357/Shambhala2_fast`](https://github.com/Nikit357/Shambhala2_fast)**, cloned at a pinned
commit when the pod starts. That repository is the pure-Python + Octave implementation. It is
not an R package (no `DESCRIPTION` / `NAMESPACE`), so it can't go through
`remotes::install_github`. It is also the implementation that produced the published
`20_shambhala` numbers: Article 1's `20_shambhala` is `shambhala_P0std_Q0std` of the Shambhala
cross-product (project memory, verified 2026-09-18). The frozen `bench_shared.py` entry
`20_shambhala`, on the other hand, calls the R package `BorisovNM/Shambhala2`, which never
produced a published number. So the revision routes `20_shambhala` to `Shambhala2_fast` with
the published settings (§3), through a wrapper in `revision_lib.py`. That is the same pattern
as the existing `04_sva_nocov` / `05_combat_nocov` wrappers, and no frozen file is touched.

The image provides **only the environment**. The code that runs is still the frozen Article 1
code (`harmonization-scripts/bench_shared.py`, MD5-checked), copied in from the Mac next to
`article_1_revision/`. ComboBatch's own re-implementation in `combobatch/` is never imported.
That keeps hard rule 1 of `article_1_revision/CLAUDE.md` (frozen baseline) intact.

Because the image also carries the metric dependencies, **Part B (approved)** runs the
**metrics pilot in the same pod**, right after the two harmonization pilots. That replaces the
SSH metrics pod and its 10–20 min start-up install, so all of cycle 1 runs in one pod.

## Background — what was checked (2026-11-01)

### The image

| Fact | Value | Source |
|---|---|---|
| Registry / visibility | `ghcr.io/nikit357/combobatch`, **public** (anonymous pull token works) | GHCR API `tags/list` |
| Tags | `latest`, `20260830`, **same digest** `sha256:47dbaed8…ac12b85` | GHCR manifest HEAD |
| Size | 5.07 GB | ComboBatch `docker/remaining_selftest_failures_plan_260830.md` |
| Base | `python:3.11-slim-bookworm`, amd64 only | ComboBatch `docker/Dockerfile` |
| R | **4.5.3** pinned (Posit build; rpy2 3.6 segfaults on 4.6) | Dockerfile §2 |
| Bioconductor | **3.22** | `docker/install_r_packages.R` |
| `ENTRYPOINT` | `entrypoint.sh`; default `CMD combobatch --help`, which **exits**, so the pod must set its own `command` | Dockerfile §7 |
| `/app` | the ComboBatch repo (`WORKDIR /app`); no `article_1_revision/` or `harmonization-scripts/` in it, so no clash | Dockerfile §6 |
| `aws` CLI, `git` | `awscli>=1.44`; `git` from apt | ComboBatch `requirements.txt`, Dockerfile §1 |
| `qnorm`, scikit-learn, numpy < 2, pandas < 2 | present: these are exactly the Python dependencies of `Shambhala2_fast` (`pyproject.toml`: pandas, numpy < 2, scikit-learn, boto3, qnorm) | ComboBatch `requirements.txt` |
| Thread pinning | `OMP/OPENBLAS/MKL_NUM_THREADS=1` in `ENV` and `/etc/environment` | Dockerfile §7 |
| Octave | `octave`, `octave-statistics`, `octave-cli` (+ a `matlab` wrapper) | Dockerfile §4 |
| Selftest | 36 / 38 pass; the 2 failures (`20_shambhala`, `21_harmonizr`) concern ComboBatch's **own** implementations on a 200-gene fixture, not the image | `remaining_selftest_failures_plan_260830.md` |

### `Nikit357/Shambhala2_fast`

| Fact | Value |
|---|---|
| Visibility | public (GitHub API, `private: false`), 65 MB (calibration CSVs, logs, a 15 MB notebook) |
| Pinned commit | `30ac312fe30ad8c6595d19023fa227163177dfe2` (HEAD of `main` on 2026-11-01) |
| Kind | Python package `shambhala` (`parallel.harmonize_parallel`, `q_rescale`, `na_handling`, `octave_bridge`) + `octave/*.m` numerical core + the cross-product worker `harmonization_scripts/run_shambhala_job.py` |
| Same as what produced the published numbers? | **Yes.** Compared with the repository's own copy `shambhala_adoption/Shambhala_containerized/` (the code of the 2026 Shambhala runs): `run_shambhala_job.py`, `shambhala/{parallel,octave_bridge,q_rescale,na_handling}.py` and `octave/Shambhala2_piped.m`, `quantilenorm.m` are byte-identical. `CuBlock.m` and `kmeans.m` differ in bytes only (`diff` shows no content change). `shambhala_bench_shared.py` differs only in reading the S3 bucket from `SHAMBHALA_S3_BUCKET` instead of a constant |
| Published settings of `shambhala_P0std_Q0std` | P = `P0_standard.csv`, Q = `Q0_standard.csv` (S3 `FL_batch_correction/calibration_datasets/`, both present); `k = 5`; NA strategy `drop`; **no** speed-up flags (`--precompute-qn-reference`, `--synthetic-cublock-p`, `--precompute-cublock-clusters`, `--python-cublock` all off); `--random-seed 42`; `--n-shambhala-workers 16` (Shambhala `CLAUDE.md` run commands) |
| Published output for a check | `exp/C_rnaseq_only__strict__shambhala_P0std_Q0std__post0.tsv.gz` (46 MB) exists. The genes are the intersection with P and Q (e.g. 2,293 genes on `J_ff_only × strict`) |
| Per-sample method | the published run harmonized S0 once and cut the strategies out of it (`run_shambhala_job.py`), so a sample's output does not depend on which other samples are in the matrix. The env check (§4) relies on this |

### Dependencies of the frozen code vs the image

`bench_shared.py` (R via `importr` / `library`, Python imports) and `compute_batch_metrics.py`:

| Dependency | Needed by | In the image? |
|---|---|---|
| limma, sva, RUVSeq, batchelor, qsmooth, edgeR, DESeq2, ruv, NOISeq, Harman | 03, 04, 05, 06, 29, 09, 10, 14, 22, 23, 31, 34, 38 | yes (bioc stage) |
| missForest, softImpute, DWDLargeR, huge | imputation (preparation), 27, 28 | yes (cran stage) |
| FSQN, TDM, HarmonizR, DBNorm, AMDBNorm | 16, 19, 21, 33 | yes (github stage) |
| reshape2 | 33_amdbnorm (`library(reshape2)`, bench_shared line ~2233) | yes (dependency of variancePartition; attached in the 2026-08-30 selftest log) |
| bapred | 37_fabatch (not a revision arm) | yes |
| **Shambhala** | **20_shambhala** (one of the 31 leave-cohort-out methods, decision D8) | **`Shambhala2_fast` cloned at pod start** (§1b), called through the `revision_lib` wrapper (§3). The R package `Shambhala2` of the frozen entry is **not** installed and not used |
| exploBATCH | 36_explobatch | no, as in the benchmark: `normalize_explobatch` raises `NotImplementedError` (dependency `fMM` deleted) → recorded as a method failure, as before |
| Procrustes (`/app/Procrustes`) | `normalize_procrustes` | not needed: not in `ANALYSED_METHODS` or `GRADIENT_ARMS` |
| rpy2, numpy < 2, pandas < 2, scikit-learn < 1.6, boto3, harmonypy, scanorama, combat, inmoose | bench_shared | yes; same constraints as `harmonization-scripts/requirements.txt` except harmonypy (`<0.2` vs `<2.0`) |
| reComBat | 30_recombat (not a revision arm) | yes (pinned commit) |
| variancePartition, BiocParallel, umap-learn, statsmodels, scipy | metric groups (Part B) | yes |

**Verdict: feasible.** One repository is cloned at start-up (seconds). Everything else is
present, in the same R and Bioconductor versions the benchmark ran on (project `CLAUDE.md`:
"R 4.5 + Bioconductor 3.22").

### What is not identical to the 2026 benchmark environment

The benchmark pod installed its packages at start-up (unpinned CRAN / Bioc 3.22 / GitHub HEAD),
so its exact versions are not recorded anywhere. The ComboBatch image froze them on 2026-08-30.
Minor versions can therefore differ (most likely harmonypy, GitHub packages, CRAN updates).
The revision experiments compare runs **within** the new environment (gradient λ vs λ,
leave-cohort-out folds vs each other), so this does not bias them. Two places do compare
against the published benchmark: `rl.bar_scaling_reference()` and the bridging check `r30`.
For those, a short **environment check** (§4, `r18_env_check.py`, approved as B2) re-runs five
published approaches in the new image (four `bench_shared` methods + Shambhala) and compares
them with the matrices on S3. Any difference is measured before the pilots, not discovered at
G4.

## Files to change

### 1. `article_1_revision/k8s/pod-revision-nopvc.yaml`

1a. Both containers: image and pull policy (the sidecar reuses the same image: one pull, `aws`
CLI included):

```yaml
# before
    image: ${ECR_URI}/fl-batch-correction:latest
    imagePullPolicy: Always
# after
    image: ghcr.io/nikit357/combobatch:20260830   # pinned: digest sha256:47dbaed8…ac12b85
    imagePullPolicy: IfNotPresent
```

1b. `worker`: an explicit start-up command. `command` overrides the image's `ENTRYPOINT`;
without it, the default `combobatch --help` would end the container at once. The start-up
clones `Shambhala2_fast` at the pinned commit into `/opt/Shambhala2_fast`. The fetch is
shallow, by commit, so the 65 MB history is not downloaded:

```yaml
# before
    # No command/args — default CMD (sleep infinity) keeps the pod alive.
    #   kubectl exec -it fl-revision -c worker -n ${K8S_NAMESPACE} -- bash -l
# after
    # The image only supplies the environment; the frozen Article 1 code is copied in
    # (RUNBOOK §3). 20_shambhala runs Daniil's Shambhala2_fast (the implementation behind
    # the published shambhala_P0std_Q0std = 20_shambhala), pinned to one commit. The
    # environment record goes to /workspace/revision/environment/, which log-sync puts on
    # S3 next to the logs.
    env:
    - name: SHAMBHALA_FAST_DIR
      value: /opt/Shambhala2_fast
    - name: SHAMBHALA_FAST_COMMIT
      value: 30ac312fe30ad8c6595d19023fa227163177dfe2
    command: ["bash", "-c"]
    args:
      - |
        set -u
        Rscript -e 'cat("[startup] R", R.version$version.string, "\n")'
        Rscript -e 'v <- R.version; if (v$major != "4" || !startsWith(v$minor, "5")) quit(status = 1)' \
          || echo "[startup] WARNING: R is not 4.5.x - rpy2 may segfault"
        mkdir -p "$SHAMBHALA_FAST_DIR" && cd "$SHAMBHALA_FAST_DIR" \
          && git init -q && git remote add origin https://github.com/Nikit357/Shambhala2_fast.git \
          && git fetch -q --depth 1 origin "$SHAMBHALA_FAST_COMMIT" \
          && git checkout -q FETCH_HEAD \
          && PYTHONPATH="$SHAMBHALA_FAST_DIR" python -c "import shambhala.parallel" \
          && octave-cli --version | head -1 \
          && echo "[startup] Shambhala2_fast $(git rev-parse --short HEAD) OK" \
          || echo "[startup] WARNING: Shambhala2_fast missing - 20_shambhala will fail"
        cd /
        mkdir -p /workspace/revision/environment
        pip freeze > /workspace/revision/environment/pip_freeze.txt
        Rscript -e 'ip <- installed.packages()[, c("Package", "Version")]; write.table(ip, "/workspace/revision/environment/r_packages.tsv", sep = "\t", quote = FALSE, row.names = FALSE)'
        printf 'image ghcr.io/nikit357/combobatch:20260830\nShambhala2_fast %s\n' \
          "$SHAMBHALA_FAST_COMMIT" > /workspace/revision/environment/image.txt
        echo "[startup] ready"
        sleep infinity
```

(`env` entries are passed to every process in the container, including `kubectl exec` shells
and the dispatcher's subprocesses, so the wrapper finds the folder without a hard-coded path.)

1c. Header comment: the image line and the reason (ECR NotFound 2026-11-01), the pinned digest,
"environment only; code copied in", and the `Shambhala2_fast` commit.

1d. **Part B (approved):** `worker` resources 8 vCPU / 16 GiB → **16 vCPU / 30 GiB** (fits a
`c6a.4xlarge`, 16 vCPU / ~30 GiB allocatable; the cluster already runs one). This serves both
pilots: harmonization `--n-workers 4`; metrics `--n-workers 8 --memory-limit-gb 3.0` on the
405–750-sample pilot matrices. Requests stay equal to limits. `ephemeral-storage` stays
25 / 30 GiB (the clone adds ~65 MB).

### 2. `article_1_revision/k8s/pod-revision.yaml`

Same image swap as 1a and the same `env` + start-up `command` as 1b (with `subPath`/PVC
unchanged), so that the PVC variant also works once the a3 pod is gone. Header line: "ECR image
NotFound 2026-11-01 → ComboBatch image". Resources stay 8 / 16 there (Part B uses the PVC-free
pod).

### 3. `article_1_revision/revision_lib.py` — `20_shambhala` → `Shambhala2_fast`

3a. New constants next to the S3 layout block:

```python
# 20_shambhala of Article 1 is shambhala_P0std_Q0std of the Shambhala cross-product
# (Shambhala2_fast), not the R package behind bench_shared's entry of the same name.
SHAMBHALA_P_FILE: str = "P0_standard.csv"
SHAMBHALA_Q_FILE: str = "Q0_standard.csv"
SHAMBHALA_SEED: int = 42  # published --random-seed
SHAMBHALA_K: int = 5  # published k-means clusters of CuBlock
SHAMBHALA_WORKERS: int = 16  # published --n-shambhala-workers
```

3b. New function `shambhala_fast(exp_df, ann_df, **kw) -> pd.DataFrame`, placed with the other
wrappers (`sva_nocov`, `combat_nocov`). It repeats the core of the published worker
`harmonization_scripts/run_shambhala_job.py` (main(), steps 3–4) for one matrix, with the
published settings and nothing else:

1. `sys.path` gets `os.environ["SHAMBHALA_FAST_DIR"]`; import `shambhala.parallel`,
   `q_rescale`, `na_handling` (a missing folder raises `RuntimeError`, which r19 records as the
   method's failure, like any other method error);
2. P and Q: `s3://…/FL_batch_correction/calibration_datasets/{P0,Q0}_standard.csv`
   (`pd.read_csv(index_col=0)`, samples × genes, the same S3 files the published run read;
   cached in-process);
3. genes × samples orientation; gene intersection of input, P and Q; `na_handling.
   apply_na_strategy(input.T, strategy="drop")`; P restricted to the kept genes;
4. `q_rescale.compute_q_statistics(Q restricted to the kept genes)` → `rm`, `rs`;
5. `parallel.harmonize_parallel(input_df=clean_T, p_df=P, rm=rm, rs=rs, k=5,
   n_workers=SHAMBHALA_WORKERS, octave_scripts_dir=<dir>/octave, octave_bin="octave",
   timeout_s=7200, random_seed=42, fixed_clusters=None, python_cublock=False)`;
6. `na_handling.restore_na_genes(result.T, na_mask)` → samples × genes, returned.

`batch_col` / `bio_col` are accepted and ignored: Shambhala uses no labels, as published.
The output has the P ∩ Q ∩ input genes (fewer than the input), exactly as the published
matrices do.

3c. `harmonizer()`:

```python
# before
    if arm == "05_combat_nocov":
        return combat_nocov
    from bench_shared import METHODS
# after
    if arm == "05_combat_nocov":
        return combat_nocov
    if arm == "20_shambhala":
        return shambhala_fast
    from bench_shared import METHODS
```

Docstring of `harmonizer` gains: "20_shambhala → `shambhala_fast` (the published
implementation, see `SHAMBHALA_*`)". `ANALYSED_METHODS` is unchanged (still 31 names).

### 4. New `article_1_revision/r18_env_check.py`

A one-off check that the new image reproduces the published benchmark (approved, B2). It runs
in the pod before the pilots, with no change to any frozen file.

Part 1, `bench_shared` methods with deterministic output: `17_quantile`, `16_fsqn_r`,
`10_mnn`, `04_sva` (two are gradient arms; together they cover rpy2, Bioconductor and a GitHub
package), on `C_rnaseq_only × strict` (the published prepared pair, ~123 MB):

1. download `prepared/C_rnaseq_only__strict__{exp,ann}.tsv.gz` with the frozen
   `bench_shared.download_exp_from_s3` / `download_ann_from_s3`;
2. call `METHODS[m][0](exp_s, ann_s, batch_col=BATCH_COL, bio_col=BIO_COL)`, the exact call of
   the frozen `run_norm_job.py` (post-removal off = the `__post0` output);
3. download the published `exp/C_rnaseq_only__strict__{m}__post0.tsv.gz` and compare.

Part 2, Shambhala: `rl.shambhala_fast` on a random **200-sample** subset (seed 0) of the same
prepared matrix, compared with those 200 rows of the published
`exp/C_rnaseq_only__strict__shambhala_P0std_Q0std__post0.tsv.gz`. Because Shambhala works per
sample, the subset rows must match the full-run rows. 200 samples keep the Octave time to
minutes.

Both parts: same samples / genes, max |Δ|, median |Δ|, Pearson r of the flattened matrices →
`revision_261029/env_check/env_check__<YYMMDD>.json` (one row per method + the pip / R version
strings of the main packages + the `Shambhala2_fast` commit) and a printed table.

Interpretation (written into the script's docstring): max |Δ| < 1e-6 → identical; r > 0.9999
→ numerically equivalent (minor version drift); anything else → stop and report at G3 before
any comparison with the main benchmark. `--methods`, `--strat`, `--shambhala-samples` flags
allow another choice. Type hints, docstrings, Black.

### 5. `article_1_revision/tests/test_revision_lib.py`

Two toy checks (no S3, no Octave): the r18 comparison function on two small frames (identical /
perturbed), and `rl.harmonizer("20_shambhala") is rl.shambhala_fast`. Expected count 85 → 87.

### 6. `article_1_revision/RUNBOOK.md`

6a. Header table, harmonization row: manifest note "ComboBatch image (environment only) +
Shambhala2_fast"; the metrics row: "pilot: the same PVC-free pod (Part B); full runs: decided
at G3".

6b. §3: the copy step now copies the frozen benchmark file too (the image no longer carries it),
and the MD5 check verifies the copy:

```bash
tar -C ~/FL_harmonization -cf - \
    --exclude='article_1_revision/cache' --exclude='article_1_revision/Revised_manuscript' \
    --exclude='article_1_revision/figures_svg' --exclude='*.parquet' --exclude='.ipynb_checkpoints' \
    article_1_revision harmonization-scripts/bench_shared.py harmonization-metrics-calculation \
  | kubectl exec -i fl-revision -c worker -n ${K8S_NAMESPACE} -- tar -xf - -C /app
kubectl exec fl-revision -c worker -n ${K8S_NAMESPACE} -- \
    sh -c 'cd /app/article_1_revision && grep bench_shared FROZEN_MD5.txt | md5sum -c -'   # → OK
```

(`harmonization-metrics-calculation/` is 6.7 MB. It is needed by Part B, and `revision_lib`
puts it on `sys.path` anyway.) The "image carries its own bench_shared.py" text and the
`kubectl cp` fallback are removed. The wait step becomes: `kubectl logs … -c worker` until
`[startup] Shambhala2_fast 30ac312 OK` and `[startup] ready` (seconds after the image pull;
the first pull of 5 GB takes ~2–4 min).

6c. §4: before the pilots, `python r18_env_check.py` (≈ 10–15 min with the Shambhala part) and
a look at its table; `pip install -q pytest` is no longer needed (pytest is in the image).

6d. §5 becomes "Metrics pilot in the same PVC-free pod" (Part B). After
`SUMMARY harmonize: 62 jobs`, in the same pod:

```bash
python r12_revision_metrics.py --pilot --dry-run     # "86 metric jobs planned; … have a harmonized matrix"
setsid nohup python r12_revision_metrics.py --pilot --skip-if-exists \
    --n-workers 8 --memory-limit-gb 3.0 > /workspace/revision/metrics_pilot.log 2>&1 &
```

then delete the pod. The old SSH metrics-pod text moves to an "alternative" sub-section.

6e. §7: row "`[startup] WARNING: Shambhala2_fast missing` → GitHub unreachable from the node;
the pilots still run, 20_shambhala is recorded as failed; repeat the clone block of the manifest
by hand with `kubectl exec … -c worker -- bash -c '…'`".

### 7. `article_1_revision/README.md`

§4.3 copy block and MD5 check as in 6b; §4.4 the metrics pilot in the same pod (Part B), the SSH
metrics pod as the alternative; §6 Layout: row for `r18_env_check.py`; manifest rows mention the
ComboBatch image and `Shambhala2_fast`.

### 8. `article_1_revision/CLAUDE.md`

Run-order table: new row `r18_env_check.py` (harmonization pod, before the pilots); the
"Pilot metrics" row: "same PVC-free pod (Part B)". Gotchas:
- "Revision pods run on `ghcr.io/nikit357/combobatch:20260830` (ECR `fl-batch-correction` is
  NotFound since 2026-11-01): environment only, frozen code copied in; `environment/` (pip
  freeze, R packages) is on S3 under `pod_logs/`."
- "`20_shambhala` in the revision = `rl.shambhala_fast` = `Shambhala2_fast` @ `30ac312`, P0std /
  Q0std, seed 42 — the published implementation. The frozen `bench_shared` entry (R
  `BorisovNM/Shambhala2`) never produced a published number and is not used."

### 9. `article_1_revision/article_1_revision_implementation_plan_261029.md`

§7 pod table (line ~982, "ECR `fl-batch-correction:latest`…") and the §6 image note (line
~1227): one dated note that points to this plan (image, `Shambhala2_fast` for `20_shambhala`,
metrics pilot in the same pod). No checklist items change.

### 10. Project `CLAUDE.md` (Infrastructure)

`**Docker image** — …fl-batch-correction:latest` → add "(NotFound in ECR since 2026-11-01; the
Article 1 revision pods use `ghcr.io/nikit357/combobatch:20260830`)".

### 11. `revision_pod_without_pvc_plan_261101.md`

Its blocked launch TODO gets "→ unblocked by `revision_pod_combobatch_image_plan_261101.md`";
the remaining run items are carried out under this plan.

## Files that do NOT need to change

| File | Why not |
|---|---|
| `harmonization-scripts/bench_shared.py`, `run_norm_job.py`, `compute_batch_metrics.py`, every frozen file | frozen; copied as they are and MD5-checked. The `20_shambhala` swap lives in `revision_lib.harmonizer`, not in `METHODS` |
| `revision_dispatch.py`, `r11`, `r19`, `r21`, `r12` | `r19` calls `rl.harmonize(arm, …)` → `harmonizer(arm)`, so the swap reaches it without an edit; `REPO_ROOT` = parent of `article_1_revision/` = `/app`, so `BENCH_DIR` / `METRICS_CODE_DIR` resolve as before; workers run with `sys.executable` (the image's Python 3.11) |
| `Nikit357/Shambhala2_fast`, `shambhala_adoption/Shambhala_containerized/` | used as they are (pinned commit); not modified |
| ComboBatch repository | not modified; its package is installed in the image but never imported by the revision code |
| `harmonization-metrics-calculation/k8s/pod-metrics.yaml` | kept as the alternative metrics path |
| `log-sync` sidecar script | unchanged; only its image line changes (1a) |

## Side effects and caveats

- **Code ≠ image.** The image carries ComboBatch's own fixed method implementations, but they
  are not used: every harmonization goes through the copied, MD5-checked `bench_shared.py`,
  except `20_shambhala`, which goes through `Shambhala2_fast` (the published implementation).
  Metrics go through the copied frozen `compute_batch_metrics.py`.
- **`20_shambhala` differs from the frozen `METHODS` entry by design.** That entry was never the
  published method. The revision Methods text names Shambhala2_fast with P0 / Q0 standard
  calibration, as Article 1 does.
- **Shambhala output has fewer genes** (P ∩ Q ∩ input, e.g. 2,293 of 3,447 on `J_ff_only`), as
  the published matrices do. Metric jobs read whatever the matrix holds, as before.
- **Shambhala run time:** per-sample Octave runs. The published 3,167-sample `J_ff_only` run
  finished; the leave-cohort-out pilot (strategy C, fold 1) is smaller. With 16 Shambhala
  processes inside one of the 4 dispatcher workers, the pod is oversubscribed while that job
  runs. The pilot measures the time, and G3 decides on the full runs.
- **Environment drift** vs the 2026 benchmark is possible (minor versions). `r18_env_check.py`
  measures it on five methods; the pip / R package lists and the `Shambhala2_fast` commit go to
  S3 (`pod_logs/<folder>/environment/`) as the record for the revised Methods ("software
  versions").
- **Start-up needs GitHub** for `Shambhala2_fast`. If it fails, only `20_shambhala` fails, as a
  recorded method failure.
- **New S3 folder** `revision_261029/env_check/` (one JSON per run). Result folders and job
  counts (24 / 62 / 86; 540 / 1,240 / 2,234) are unchanged.
- **Part B** makes the pod 16 vCPU / 30 GiB for the harmonization part too; the cost difference
  for a few pilot hours is small. The full-run metrics pod size is still decided at G3.
- The image is pinned by tag `20260830` and `Shambhala2_fast` by commit. A future push to the tag
  would change the digest; the header records the digest so a change can be seen.

## Decisions (answered 2026-11-01)

| # | Question | Answer |
|---|---|---|
| B1 | Run the metrics pilot (cycle 1c) in the same PVC-free ComboBatch pod (Part B, 16 vCPU / 30 GiB) instead of the SSH metrics pod? | **Yes** (Daniil) |
| B2 | Run `r18_env_check.py` before the pilots? | **Yes** (Daniil) |
| B3 | Shambhala source | **`Nikit357/Shambhala2_fast`** (Daniil); pinned to `30ac312`, used through `rl.shambhala_fast` with the published P0std / Q0std settings (§3) |

## Verification commands

```bash
cd ~/FL_harmonization
kubectl apply --dry-run=server -f article_1_revision/k8s/pod-revision-nopvc.yaml -n ${K8S_NAMESPACE}
kubectl apply --dry-run=server -f article_1_revision/k8s/pod-revision.yaml -n ${K8S_NAMESPACE}
source ~/venvs/collagen_3_11/bin/activate
cd article_1_revision && python -m pytest tests/ -q        # 87 passed
python r18_env_check.py --help
python -c "import revision_lib as rl; print(rl.harmonizer('20_shambhala').__name__)"   # shambhala_fast

# after launch
kubectl logs fl-revision -c worker -n ${K8S_NAMESPACE} | grep startup
#   → R 4.5.3 / Shambhala2_fast 30ac312 OK / ready
kubectl exec fl-revision -c worker -n ${K8S_NAMESPACE} -- \
  sh -c 'cd /app/article_1_revision && grep bench_shared FROZEN_MD5.txt | md5sum -c - \
         && python -c "import revision_lib, bench_shared; print(bench_shared.__file__)"'
#   → OK, /app/harmonization-scripts/bench_shared.py
kubectl exec fl-revision -c worker -n ${K8S_NAMESPACE} -- \
  sh -c 'cd /app/article_1_revision && python r18_env_check.py'
aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/pod_logs/ --recursive | grep environment/
```

## TODO

- [x] `k8s/pod-revision-nopvc.yaml` — image → `ghcr.io/nikit357/combobatch:20260830`, `IfNotPresent` (both containers)
- [x] `k8s/pod-revision-nopvc.yaml` — `worker` `env` (`SHAMBHALA_FAST_DIR`, `SHAMBHALA_FAST_COMMIT`) + start-up command (R check, `Shambhala2_fast` clone @ `30ac312`, environment record, `sleep infinity`)
- [x] `k8s/pod-revision-nopvc.yaml` — header comment (ECR NotFound, digest, environment only, Shambhala commit)
- [x] `k8s/pod-revision-nopvc.yaml` — resources 16 vCPU / 30 GiB (Part B) — implemented as **14 vCPU / 24 GiB**: a c6a.4xlarge has 15.89 CPU / 27.8 GiB allocatable, so 16 / 30 plus log-sync and DaemonSets would not fit
- [x] `k8s/pod-revision.yaml` — same image swap + `env` + start-up command + header line
- [x] `kubectl apply --dry-run=server` passes for both manifests
- [x] `revision_lib.py` — `SHAMBHALA_*` constants
- [x] `revision_lib.py` — `shambhala_fast()` wrapper (published steps of `run_shambhala_job.py`)
- [x] `revision_lib.py` — `harmonizer()`: `20_shambhala` → `shambhala_fast`; docstring
- [x] `r18_env_check.py` — new script (part 1: four `bench_shared` methods; part 2: Shambhala on 200 samples; JSON to S3, table)
- [x] `tests/test_revision_lib.py` — comparison toy check + `harmonizer('20_shambhala')` check; `pytest tests/ -q` → 87 collected: 85 passed + 2 skipped (both pre-existing, need local data files)
- [x] `RUNBOOK.md` — header table; §3 copy + MD5 + start-up lines; §4 env check, no pip pytest; §5 metrics pilot in the same pod; §7 Shambhala2_fast row
- [x] `README.md` — §4.3 copy + MD5; §4.4 metrics pilot in the same pod; §6 Layout rows
- [x] `CLAUDE.md` (article_1_revision) — run-order rows (`r18`, pilot metrics); two gotcha lines
- [x] `article_1_revision_implementation_plan_261029.md` — dated note in §7 and §6
- [x] Project `CLAUDE.md` — Infrastructure image note
- [x] `revision_pod_without_pvc_plan_261101.md` — unblock note on its launch TODO
- [x] Launch the PVC-free pod; `[startup] Shambhala2_fast 30ac312 OK`, `[startup] ready`; copy code (§3); MD5 OK; `pytest tests/ -q`; dry-runs 24 / 62 — (2026-11-01 22:13 local: node ip-10-40-1-46, image pulled in ~70 s; R 4.5.3, Octave 7.3.0; bench_shared / compute_batch_metrics / run_metrics_job / run_metrics_concat MD5 OK; 85 passed + 2 skipped; dry-runs 2 + 24 and 2 + 62. Copied from `FL_harmonization`, not `fl_subset`)
- [x] Log-sync check (`log_sync_check.txt` on S3 within ~60 s; `environment/` on S3) — folder `pod_logs/fl-revision_261101_1812/`
- [x] `r18_env_check.py` in the pod → JSON on S3; read the table (stop and report if not equivalent) — **ENV CHECK: OK** (2026-11-01): 16_fsqn_r and 04_sva identical; 17_quantile (max |Δ| 0.0015), 10_mnn (r 0.999998) and 20_shambhala (r 0.999988, median |Δ| 0.26 on a linear scale, median value ~1,385) equivalent. The first run said STOP for 20_shambhala (r 0.993): r18 fed Shambhala the C_rnaseq_only gene set (6,797 → 4,785 genes), while the published run harmonized S0 (3,447 → 2,293); CuBlock clusters genes, so the gene set changes the values. r18 now takes the subset's samples from prepared S0 (fix + docstring); first-run log kept as `env_check_run1_C_input.log`
- [x] Gradient pilot → `SUMMARY harmonize: 24 jobs` — {'ok': 24}, 18:42–19:35 UTC (raw cache 104 s, 2 preparations 26 s; arms 12–92 s each except 33_amdbnorm ≈ 2,786 / 2,836 s)
- [x] Leave-cohort-out pilot → `SUMMARY harmonize: 62 jobs` (incl. `20_shambhala` via `Shambhala2_fast`) — {'ok': 61, 'timeout': 1}, 20:25–23:26 UTC; preparations 62 / 570 s; 20_shambhala 2,182 s (train) / 927 s (test); 21_harmonizr 2,272 s (train); 33_amdbnorm 4,060 s (test) and **timeout at 7,200 s on train** (G3 point); `r12 --pilot --dry-run`: 82 of 86 metric jobs have a matrix
- [x] Metrics pilot in the same pod (Part B) → `SUMMARY metrics` (86 jobs at most) — 82 of 86 (4 without a matrix: ComBat λ = 1, exploBATCH ×2, AMDBNorm train timeout); gradient 23 / 23 ok (05:54–06:09 UTC, 218–352 s per job, group D ≈ 285 s), leave-cohort-out 59 / 59 ok (06:09–06:33 UTC, train ≈ 270–430 s, test ≈ 85 s); 309 keys per metric record, no group error
- [x] `kubectl delete pod fl-revision -n ${K8S_NAMESPACE}`; final sync on S3; a3 pod still Running — 2026-11-02 ~06:35 UTC; `metrics_pilot.log` on S3 ends with `SUMMARY metrics: 59 jobs`; `fl-a3` Running
- [x] Stop at gate G3 (`r14_pilot_report.py` on JupyterHub; full runs wait for Daniil) — stopped; r14 and the full runs are Daniil's next step. G3 points: AMDBNorm run time (≈ 47 min per gradient matrix, timeout at 7,200 s on the C training fold), Shambhala2_fast 36 / 15 min per fold, group D ≈ 80 % of metric time
