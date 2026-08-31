# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Self-contained metrics **compute** pipeline plus everything needed to launch the K8s pod. Reads
harmonized expression files from S3 (produced by `harmonization-scripts/`) and computes
comprehensive batch effect metrics across 14 groups (A–N). Designed to run inside
`fl-metrics` (`${K8S_NAMESPACE}` namespace) with 128 GiB RAM, R 4.5, and
`variancePartition`.

This directory is deliberately small (~5 MB, no notebooks, no figures) so it can be pulled on its
own with `git sparse-checkout` and the pod launched from a laptop — see `README.md` for the
step-by-step launch guide and the sparse-checkout commands.

All scripts must be run from this directory inside the pod.

## Commands

```bash
# Smoke test — verifies Python packages, all metric groups (skips variancePartition only)
python test_mock_metrics.py

# Single-job test — verifies S3 access and end-to-end pipeline (WM computed by default)
python run_metrics_job.py \
    --strat A_confirmed_bad --imp strict --method 16_fsqn_r \
    --post-rm False \
    --out-json /tmp/test_metrics.json \
    --out-genes-json /tmp/test_genes.json \
    --skip-slow

# Single-job test with WaterMelon score explicitly skipped
python run_metrics_job.py \
    --strat A_confirmed_bad --imp strict --method 16_fsqn_r \
    --post-rm False \
    --out-json /tmp/test_metrics.json \
    --out-genes-json /tmp/test_genes.json \
    --skip-slow --skip-wm True

# Inspect single-job output
python -c "import json; d=json.load(open('/tmp/test_metrics.json')); print(d.get('status'), d.get('n_samples'), d.get('pct_var_pc1'), d.get('n_genes_noNA'), d.get('wm_RNA_BATCH'))"

# Full dispatcher — fast mode (no variancePartition, post0 only, 4 workers; WM included by default)
nohup python run_metrics_parallel.py \
    --n-workers 4 --skip-slow \
    --post-rm-filter post0 --memory-limit-gb 6.0 \
    > /workspace/metrics_fast.log 2>&1 &

# Full dispatcher — skip WM to save time (use --skip-wm to opt out of Group I)
nohup python run_metrics_parallel.py \
    --n-workers 4 --skip-slow --skip-wm \
    --post-rm-filter post0 --memory-limit-gb 6.0 \
    > /workspace/metrics_fast_nowm.log 2>&1 &

# Full dispatcher — production (variancePartition enabled, limit workers)
nohup python run_metrics_parallel.py \
    --n-workers 2 --skip-if-exists \
    --post-rm-filter post0 --memory-limit-gb 8.0 --timeout-s 3600 \
    > /workspace/metrics_full.log 2>&1 &

# Targeted subset
python run_metrics_parallel.py \
    --strats A_confirmed_bad --imps strict \
    --methods 01_raw,16_fsqn_r,17_quantile \
    --post-rm-filter post0 --skip-slow --n-workers 4

# Resume after failure (retries failed_jobs_metrics.txt entries)
python run_metrics_parallel.py --n-workers 4 --skip-slow --retry-failed --post-rm-filter post0

# ── Blind final check: groups L (marker correlation), M (rank agreement), N (prediction) ──
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

# Groups M and N only — no reference download at all
python run_metrics_job.py --strat C_rnaseq_only --imp softimpute --method 10_mnn \
    --post-rm False --out-json /tmp/mn.json --out-genes-json /tmp/g.json --groups M,N

# Regenerate the gene panel after editing build_marker_gene_annotation.py
python build_marker_gene_annotation.py

# Aggregate all JSON sidecars → metrics_comprehensive.csv + 3 long tables on S3
# The S3 keys stay undated; --out-dir + --date-tag write all four tables locally with a
# YYMMDD postfix, so a re-run never overwrites a previous snapshot.
python run_metrics_concat.py
python run_metrics_concat.py --out-dir ../harmonization-metrics/metric_tables --date-tag 260827
python run_metrics_concat.py --out-csv /workspace/metrics_comprehensive.csv

# ── Marker panel deep analysis (see gene_panel_analysis/README.md) ──
cd gene_panel_analysis
# 1,204 jobs = non-Shambhala + shambhala_P0std_Q0std, post0 only. Check the count first.
python run_gene_corr_parallel.py \
    --only-with-metrics --shambhala-mode default-only --post-rm-filter post0 --dry-run

nohup python run_gene_corr_parallel.py \
    --only-with-metrics --shambhala-mode default-only --post-rm-filter post0 \
    --n-workers 20 --memory-limit-gb 8.0 --timeout-s 1200 \
    > /workspace/gene_corr.log 2>&1 &

python run_gene_corr_concat.py --out-dir /workspace/gene_panel_tables --date-tag 260827 --by-strat
python build_marker_gene_coverage.py --out-dir /workspace/gene_panel_tables --date-tag 260827
cd ..

# Compute only specific metric groups (A, B, E, etc.) — useful for fast targeted re-runs
python run_metrics_job.py \
    --strat A_confirmed_bad --imp strict --method 16_fsqn_r \
    --post-rm False \
    --out-json /tmp/test_metrics.json \
    --out-genes-json /tmp/test_genes.json \
    --groups A,B,E
```

## Architecture

### File roles

| File | Role |
|---|---|
| `compute_batch_metrics.py` | Core library: 14 metric group functions (A–N) + shared embedding helpers + `compute_all_metrics()` |
| `run_metrics_job.py` | Worker: downloads one `(strat, imp, method, post_rm)` expression file → computes metrics → uploads JSON sidecar to S3 |
| `run_metrics_parallel.py` | Dispatcher: enumerates expression files on S3, launches worker subprocesses via `ThreadPoolExecutor` |
| `run_metrics_concat.py` | Aggregator: downloads all `*_metrics.json` sidecars from S3, builds `metrics_comprehensive.csv` + 3 long-format detail tables |
| `test_mock_metrics.py` | Smoke tests: synthetic data, correctness checks (no S3 access needed); 169 assertions |
| `marker_gene_annotation.csv` | **Gene panel source of truth** for groups L and M: 834 rows (gene × gene_group), 633 unique genes, 63 groups, 15 housekeeping. Columns include `cell_type`, `pathway`, `tme_subtype`, `prognostic_significance`, `source_article`, `provenance` |
| `build_marker_gene_annotation.py` | Regenerates `marker_gene_annotation.csv`; edit gene lists here, never in the CSV. Reads the published signature lists out of `Kotlov_et_al_2021_supplementary/` (Table S1 FGES, Tables S2/S3 classifiers) and `Holmes_et_al_2020_supplementary/` (Table S2, top `HOLMES_TOP_N_UP` up-genes per GC B-cell cluster) |
| `marker_panels.py` | Loader over the CSV: `load_marker_annotation()`, `panel_genes()`, `housekeeping_genes()`, `resolve_panel()` (alias fallback), `panel_summary()` |
| `Kotlov_et_al_2021_supplementary/` | Published supplementary tables (1 `.xlsx`) read by `build_marker_gene_annotation.py` |
| `Holmes_et_al_2020_supplementary/` | Published supplementary tables (3 `.xlsx`) read by `build_marker_gene_annotation.py` |
| `Dybkaer_et_al_2015_supplementary/` | Published Data Supplement (1 `.xls`, DS1) read by `build_marker_gene_annotation.py` |
| `gene_panel_analysis/` | Marker-panel deep-analysis sub-pipeline (own `README.md`): gene × gene correlation matrices, per-gene expression QC, per-attempt gene coverage. Runs in the same pod; produces no `metrics_comprehensive.csv` column |
| `requirements.txt` | Python dependencies; **keep in sync** with the ConfigMap in `k8s/pod-metrics.yaml` |
| `README.md` | Step-by-step pod launch guide: sparse checkout, Secrets, apply, SSH, rsync, run, teardown, troubleshooting |
| `k8s/pod-metrics.yaml` | Pod manifest: ubuntu:24.04, installs Python + R 4.5 + variancePartition at startup (~10–20 min) |

### What is NOT here

The analysis side lives in `../harmonization-metrics/` and never runs inside the pod:

| Location | Contents |
|---|---|
| `../harmonization-metrics/` | `harmonization_metrics_analysis_v3.ipynb` (primary analysis notebook), `harmonization_metrics_visual_inspection.ipynb`, `correlation_prediction_metrics_analysis.ipynb` (blind check), `marker_gene_deep_analysis.ipynb` (marker panel deep-dive), their generator scripts, `figures/`, `metric_tables/` (dated `metrics_comprehensive_*.csv` snapshots), `marker_gene_coverage_audit_260819.csv`, plan documents |
| `../figures_for_article/figures_helpers.py` | `load_metrics_data()`, `attach_raw_baseline()`, and the rest of the figure helpers used by those notebooks |

See `../harmonization-metrics/CLAUDE.md` for the notebook-by-notebook description.

The blind-check notebook imports `marker_panels` from this directory via
`sys.path.insert(0, "../harmonization-metrics-calculation")` — that is the only dependency
pointing from the analysis side into this one.

### S3 layout

```
s3://$FL_S3_BUCKET/FL_batch_correction/
├── exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz    ← input (from harmonization-scripts)
├── prepared/{strat}__{imp}__ann.tsv.gz               ← annotation aligned to exp
├── metrics/{strat}__{imp}__{method}__post{0|1}_metrics.json  ← per-job output
├── genes/{strat}__{imp}__{method}__post{0|1}_genes.json      ← gene list per job
├── metrics_comprehensive.csv                          ← aggregated output (A–N; only A–K feed the clustermap)
├── marker_gene_correlations_long.csv                  ← Group L per-gene detail (run_id × gene)
├── marker_cohort_correlations_long.csv                ← Group L per-cohort detail
├── prediction_folds_long.csv                          ← Group N per-fold detail
├── marker_corr/{strat}__{imp}__{method}__post{0|1}_gene_cohort.json
│                                                      ← Group L gene × cohort matrix (--save-gene-cohort-detail only)
├── gene_corr/{strat}__{imp}__{method}__post{0|1}_genecorr.npz  ← gene × gene correlation
├── gene_qc/{strat}__{imp}__{method}__post{0|1}_geneqc.json     ← per-gene expression QC
├── gene_gene_consensus_{within,global,sd,n}.csv.gz             ← Fisher-z consensus
├── gene_qc_long.csv.gz                                         ← aggregated QC
├── marker_gene_coverage_by_attempt.csv                         ← per-gene coverage audit
├── failed_gene_corr_{pod_name}.txt                             ← gene_panel_analysis failures
└── failed_metrics_{pod_name}.txt                     ← failed-job tracking per pod
```

The last six keys are written by `gene_panel_analysis/`, not by the metrics pipeline.

### Metric groups

This table is the single home for the metric group definitions — the analysis-side CLAUDE.md
points here rather than duplicating it.

| Group | Key metrics | Speed | Default |
|---|---|---|---|
| E — Data quality | `n_samples`, `n_batches`, `zero_fraction_global`, bimodality | Fast | Yes |
| A — PCA variance | `r2_RNA_BATCH` (mean R² over PC1–10), PCR (variance-weighted), DSC | Fast | Yes |
| J — PC variance % | `pct_var_pc{1..10}`, `pct_var_cum_top10` — % variance per PC | Fast | Yes |
| B — Neighbor-based | kBET, iLISI, cLISI, ASW_batch, ASW_bio, CMS | Moderate | Yes |
| C — Embedding | UMAP/tSNE centroid dispersion, local entropy | Moderate | Yes |
| D — Distribution | Pairwise KS tests, within-batch cohort effects, per-gene CV | Slow | Yes |
| F — variancePartition | Mixed-model variance decomposition via R | Very slow (~30 min/job) | Yes (gated by `--skip-slow`) |
| G — Graph connectivity | kNN graph per biology group | Moderate | Yes |
| H — Pairwise distances | Intra/inter group Euclidean distance ratios | Moderate | Yes |
| I — WaterMelon score | `wm_{col}`, `wm_mean_batch`, `wm_mean_bio`, `wm_ratio_bio_batch` — entropy-based clustering quality | 2–5 min | **Yes** (opt-out via `--skip-wm`) |
| K — NA retention | `n_genes_noNA`, `pct_genes_noNA`, `n_samples_noNA`, `pct_samples_noNA`, `n_genes_allNA`, `n_samples_allNA`, `n_na_cells`, `pct_na_cells` | Fast | Yes |
| L — Marker correlation | `mk_rho_mean_all_genes`, `mk_rho_by_gene`, `mk_rho_marker_minus_hk`, `mk_n_panel_genes_used` | Fast; **needs the raw reference** | Yes |
| M — Cross-batch rank agreement | `xb_rank_agree`, `xb_rank_disagree_diffbio`, `xb_rank_agree_ratio` | Moderate; single matrix | Yes |
| N — Predictive validation | `pv_lobo3_f1_macro_mean`, `pv_lobo2_auc_macro_mean`, `pv_*_perm_*`, `pv_*_n_folds` | Slow (~5–6 min/job) | Yes |

`compute_all_metrics()` runs each group in an isolated try/except block and flushes partial JSON to `tmp_path` after each group, so a group failure doesn't abort the others.

**Default active set:** `ABCDEFGHIJKLMN`. Group F is skipped with `--skip-slow`; Group I is skipped with `--skip-wm`.

`gene_panel_analysis/` is **not** a metric group. It writes its own S3 prefixes and its own
tables, adds no column to `metrics_comprehensive.csv`, and never calls
`compute_all_metrics()` — so it cannot invalidate the existing sidecars. Do not add its
outputs to `_GROUP_MAP` or to `scoring_cols` either.

Groups **L, M, N** are the blind final check. They live in the same JSON sidecars and the same
`metrics_comprehensive.csv` as A–K, but they are **excluded from `scoring_cols`** and therefore from
the Figure 3 clustermap and the composite score. The exclusion is enforced by the
`_BLIND_CHECK_PREFIXES = ("mk_", "xb_", "pv_")` filter in `figures_helpers.load_metrics_data()` plus
an assertion that fails loudly if one ever leaks. Do **not** add L/M/N to `_GROUP_MAP`.

**Group L** requires the raw reference `exp/{strat}__{imp}__01_raw__post0.tsv.gz`, cached locally per
`(strat, imp)` — 42 pairs, ~12.8 GB, at `--ref-cache-dir` (default `/workspace/ref_cache`).
`01_raw__post1` must never be used: post-removal drops outlier batches identified on the
*harmonized* matrix, so its removed batches differ per method. Intersecting `01_raw__post0` down to
the job's own index gives an exact sample match, which is also what restricts a `post1` job to the
post-removal-surviving samples.

**Groups M and N need no reference** and do no extra I/O — `--groups M,N` skips the cache entirely.
`01_raw` is itself an attempt in the benchmark, so the unharmonized baseline for M and N is obtained
in the notebook via `figures_helpers.attach_raw_baseline()`, joining on `(strat, imp)`. Computing it
inside each job would repeat the identical number ~60 times per pair.

### Key design patterns

**Memory guard** — both the dispatcher and workers check cgroup-aware free RAM (`/sys/fs/cgroup/memory.max`) before proceeding. The dispatcher passes `--memory-limit-gb / 2` to workers. Exit code 2 = OOM abort (not counted as a failed job).

**Failed-job tracking** — `failed_jobs_metrics.txt` persists locally (in this directory) and is synced to S3 at startup/shutdown under `failed_metrics_{POD_NAME}.txt`. `--skip-if-exists` checks S3 for the metrics JSON sidecar; `--retry-failed` ignores the failed-jobs log.

**variancePartition interface** — Group F invokes R via subprocess (not rpy2), writing TSV files to a temp directory. Column names may have `_` replaced by `.` in R output; the code handles both variants.

**Metric naming conventions** — Most metric keys are suffixed with an annotation column name. The two constant sets in `compute_batch_metrics.py` control which columns are used:
- `BATCH_COLS = ["RNA_BATCH", "PLATFORM_RNA", "RNASEQ_SOURCE", "COHORT_LABEL"]` — used for batch-removal metrics (kBET, iLISI, ASW_batch, etc.)
- `BIO_COLS = ["Major_group", "PLATFORM_RNA", "Diagnosis_cell_type_unified", "TUMOR_NORMAL"]` — used for biology-preservation metrics (cLISI, ASW_bio, graph connectivity)
- `ALL_COLS` is the union, used for PCR, variancePartition, and pairwise distances.

**Selective group computation** — `compute_all_metrics(..., groups={"A", "B"})` and the worker's `--groups A,B` flag skip all other groups. The dispatcher `run_metrics_parallel.py` exposes `--groups` and `--skip-wm` (to opt out of Group I) and forwards both to worker subprocesses.

**Incremental computation** — `run_metrics_job.py` loads any existing metrics JSON sidecar from S3 at startup and checks which groups have their sentinel key already set (non-null). Only missing/incomplete groups are recomputed. The new and old results are merged before re-upload. This enables adding new groups (J, K, I, then L, M, N) to already-completed jobs without full recomputation. Sentinel keys are defined in `GROUP_SENTINEL_KEYS` in `run_metrics_job.py`. The `--skip-if-exists` flag bypasses the entire job; incremental logic applies when it is not set — which is why an L/M/N run must **not** pass `--skip-if-exists`. `GROUPS_NEEDING_REFERENCE` in the same file gates the reference download so `--groups M,N` performs no extra I/O.

**Incremental persistence** — every group's result is uploaded to S3 as soon as it finishes (`on_group_done` callback threaded through `compute_all_metrics()` → `_upload_partial()` in `run_metrics_job.py`), not just once at the very end. A timeout or crash during a later group (e.g. Group N) no longer discards groups that already completed in the same attempt.

**Force-recompute** — `--force-groups` (both `run_metrics_parallel.py` and `run_metrics_job.py`) bypasses the sentinel check in `_groups_to_recompute` for named groups only, so an already-populated group (e.g. Group N) can be rerun with different parameters (e.g. a higher `--n-perm`) without discarding or recomputing any other group in the same sidecar. It is folded into the requested-groups set automatically, so `--force-groups N` alone is enough even without also passing `--groups N`.

**WaterMelon score (Group I)** — Entropy-based hierarchical clustering quality metric (Zolotovskaya et al. 2020, PMC7084891). Applied to both batch columns (low WM = good harmonization) and biology columns (high WM = biology preserved). `wm_ratio_bio_batch = wm_mean_bio / (wm_mean_batch + 0.01)`. WM columns: `WM_BATCH_COLS = ["RNA_BATCH","PLATFORM_RNA","RNASEQ_SOURCE","COHORT_LABEL"]`, `WM_BIO_COLS = ["Major_group","Diagnosis_cell_type_unified","TUMOR_NORMAL"]`. Subsamples to N=2000 (stratified by RNA_BATCH) when N > 2000. Uses M=200 permutations for null trajectory.

**Exit codes** (worker subprocess): `0` = success or cached; `1` = metrics compute/upload failed; `2` = OOM abort (insufficient RAM before start); `3` = expression or annotation file not found on S3.

**Expression alignment** — Workers align `exp_df` and `ann_df` by index intersection after download, not by positional order. Always check `len(exp_df) == len(ann_df)` after alignment.

## Pod Operations

```bash
# Sparse checkout of just this folder on a laptop (~5 MB instead of ~1.3 GB)
git clone --filter=blob:none --no-checkout \
    https://github.com/Nikit357/FL_harmonization fl_disser
cd fl_disser
git sparse-checkout init --cone
git sparse-checkout set harmonization-metrics-calculation
git checkout main

# One-time: the SSH public key lives in a Secret, not in the manifest
kubectl create secret generic ssh-pubkey \
    --from-file=authorized_keys=$HOME/.ssh/id_ed25519.pub \
    --namespace ${K8S_NAMESPACE}

# Launch pod (run from repository root)
kubectl apply -f harmonization-metrics-calculation/k8s/pod-metrics.yaml -n ${K8S_NAMESPACE}

# Watch startup (~10–20 min for R packages)
kubectl logs -f fl-metrics -n ${K8S_NAMESPACE}
# Ready when: "[startup] Metrics environment ready." appears

# Port forward for SSH (keep terminal open)
kubectl port-forward pod/fl-metrics 2222:22 -n ${K8S_NAMESPACE}

# Sync this directory to the pod (from local Mac). Sync the whole directory, not *py:
# a *py glob leaves marker_gene_annotation.csv behind, which groups L and M need.
rsync -avz --progress \
    -e "ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
    ~/fl_subset/harmonization-metrics-calculation/ \
    root@localhost:/app/harmonization-metrics-calculation/

# Teardown (PVC and aws-credentials Secret are NOT deleted)
kubectl delete pod fl-metrics -n ${K8S_NAMESPACE}
```

**Always redirect logs to `/workspace/`** (the PVC) so they survive a pod crash.

The manifest keeps its 16 vCPU / 128 GiB request; the node size is tuned manually at launch, so the
run command's `--n-workers` carries that decision. The Group L reference cache also lives on the PVC
(`/workspace/ref_cache`, ~12.8 GB) — delete it if the `01_raw` outputs are ever regenerated, since a
stale cache would silently compare against the wrong reference.

## Memory Guidelines

| Mode | Workers | `--memory-limit-gb` | Peak per worker |
|---|---|---|---|
| Fast (skip-slow) | up to 8 | 6.0 | ~2–4 GB |
| Full (variancePartition) | 2–4 | 8.0–10.0 | ~6–8 GB |
| Blind check (L/M/N) | ~(vCPU − 8) | 8.0 | ~3–4 GB |

The blind check is CPU-bound, not memory-bound: the job matrix plus the Group L reference plus one
412 MB rank-correlation matrix for Group M. Pick `--n-workers` from the node Daniil provisioned — the
pod manifest deliberately does not set the node size. `OMP_NUM_THREADS=1` and friends are set in
`k8s/pod-metrics.yaml`; without them, unpinned BLAS threads oversubscribe the node and cost more
than the extra parallelism gains.

Exit code 137 = OOM kill — reduce `--n-workers` or increase `--memory-limit-gb`. Worker exit code 2 = OOM abort (not counted as failed job).

## Requirements Sync

`k8s/pod-metrics.yaml` embeds a copy of `requirements.txt` in a ConfigMap. When updating Python dependencies, edit **both** `harmonization-metrics-calculation/requirements.txt` and the `data.requirements.txt` block in the YAML, then re-apply the manifest.
