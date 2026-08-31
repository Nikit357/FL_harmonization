# gene_panel_analysis — marker panel deep-analysis sub-pipeline

Produces the two data products that the marker gene deep-analysis notebook
(`../../harmonization-metrics/marker_gene_deep_analysis.ipynb`) needs and that the
metrics pipeline does not compute:

1. a **gene × gene correlation matrix per attempt**, in two flavours (all samples, and
   within-cohort Fisher-z averaged), plus a consensus across attempts;
2. a **per-gene expression QC table per attempt** — zero fraction, fraction below 1,
   mean/variance/CV, between- vs within-cohort variance, ICC and geNorm M.

Plus a coverage audit built from the gene sidecars the metrics run already produced.

**These scripts are not a metric group.** They add no column to
`metrics_comprehensive.csv`, never call `compute_all_metrics()`, and cannot invalidate
the existing metrics sidecars. They run in the same `fl-metrics` pod as
the rest of the compute pipeline; the existing sparse checkout and rsync of
`harmonization-metrics-calculation/` already include this directory, so the launch
procedure in `../README.md` needs no change.

Every command below is run from **inside this directory**.

---

## Analysis scope

The benchmark holds 3,835 attempts, of which 1,428 are Shambhala cross-product variants
excluded from Article 1. Following the convention of
`harmonization_metrics_analysis_v3.ipynb`, the default Shambhala variant
`shambhala_P0std_Q0std` is **kept** (it appears there as `20_shambhala`); the rest are
dropped.

| Scope | attempts |
|---|---|
| All attempts | 3,835 |
| Shambhala cross-product variants (dropped) | 1,428 |
| `shambhala_P0std_Q0std` (kept) | 84 |
| **Analysis scope, both post_rm** | **2,407** |
| **Analysis scope, post0 only — the default run** | **1,204** |

`--shambhala-mode {all,none,default-only}` encodes this and defaults to
`default-only` in every script here. The metrics dispatcher's `--skip-shambhala` is
deliberately **not** carried over: it would silently drop `shambhala_P0std_Q0std`,
which is in scope.

---

## Run book

```bash
# 0. Activate the environment and enter this directory
source ~/venvs/collagen_3_11/bin/activate      # locally; the pod has its own venv
cd harmonization-metrics-calculation/gene_panel_analysis

# 1. Smoke test — synthetic data only, no S3, a few seconds
python test_mock_gene_structure.py

# 2. Single job — verifies S3 access and the end-to-end path
python run_gene_corr_job.py \
    --strat C_rnaseq_only --imp softimpute --method 10_mnn --post-rm False \
    --out-npz /tmp/genecorr.npz --out-qc-json /tmp/geneqc.json

# 3. Confirm the filters select the expected number of jobs before committing hours
python run_gene_corr_parallel.py \
    --only-with-metrics --shambhala-mode default-only --post-rm-filter post0 --dry-run
#    → 1,204 jobs, broken down per strategy

# 4. Production run (~2-4 h at 20 workers; bounded by S3 bandwidth, not CPU)
nohup python run_gene_corr_parallel.py \
    --only-with-metrics --shambhala-mode default-only --post-rm-filter post0 \
    --n-workers 20 --memory-limit-gb 8.0 --timeout-s 1200 \
    > /workspace/gene_corr.log 2>&1 &

# 5. Aggregate — every table into one folder, with the date postfix
python run_gene_corr_concat.py \
    --out-dir /workspace/gene_panel_tables --date-tag 260827 --by-strat

# 6. Coverage audit — reads genes/*.json only, no expression download, ~2 min
python build_marker_gene_coverage.py \
    --out-dir /workspace/gene_panel_tables --date-tag 260827

# 7. Copy the tables to the analysis side
rsync -av /workspace/gene_panel_tables/ \
    <laptop>:Projects/FL_harmonization/harmonization-metrics/metric_tables/
```

---

## Files

| File | Role |
|---|---|
| `gene_panel_structure.py` | Library: `gene_gene_correlation()`, `gene_gene_correlation_within_cohort()`, `gene_expression_qc()`, Fisher-z helpers, upper-triangle packing. No S3, no CLI |
| `run_gene_corr_job.py` | Worker: one attempt → `gene_corr/*.npz` + `gene_qc/*.json` on S3 |
| `run_gene_corr_parallel.py` | Dispatcher: enumerates attempts, launches workers, tracks failures |
| `run_gene_corr_concat.py` | Aggregator: Fisher-z consensus matrices + `gene_qc_long.csv.gz` |
| `build_marker_gene_coverage.py` | Per-gene coverage from the `genes/*.json` sidecars |
| `test_mock_gene_structure.py` | 15 smoke tests on synthetic data |
| `failed_jobs_gene_corr.txt` | Written at runtime; distinct from the metrics run's `failed_jobs_metrics.txt` so the two can share a pod |

The gene panel itself comes from `../marker_gene_annotation.csv` through
`../marker_panels.py`; `MIN_COHORT_N` (20) and the S3 configuration come from
`../compute_batch_metrics.py`, so nothing is duplicated.

---

## S3 layout

```
s3://$FL_S3_BUCKET/FL_batch_correction/
├── exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz              ← input
├── prepared/{strat}__{imp}__ann.tsv.gz                         ← input
├── genes/{strat}__{imp}__{method}__post{0|1}_genes.json        ← input (coverage)
├── gene_corr/{strat}__{imp}__{method}__post{0|1}_genecorr.npz  ← output
├── gene_qc/{strat}__{imp}__{method}__post{0|1}_geneqc.json     ← output
├── gene_gene_consensus_{within,global,sd,n}.csv.gz             ← aggregated
├── gene_qc_long.csv.gz                                         ← aggregated
├── marker_gene_coverage_by_attempt.csv                         ← aggregated
└── failed_gene_corr_{pod_name}.txt                             ← failed-job tracking
```

Storage: 1,204 `.npz` at ~330 KB plus 1,204 `.json` at ~120 KB ≈ **540 MB**. A full run
(2,407 jobs, both post_rm) is ~1.1 GB.

### `.npz` payload

| array | dtype | shape | meaning |
|---|---|---|---|
| `genes` | `<U32` | (G,) | gene order for both matrices — **per job**, not the union |
| `r_global` | float16 | (G(G−1)/2,) | packed strict upper triangle, all samples |
| `r_within` | float16 | (G(G−1)/2,) | packed strict upper triangle, Fisher-z over cohorts |
| `n_within` | uint16 | (G(G−1)/2,) | cohorts contributing to each pair |
| `meta` | json str | — | strat, imp, method, post_rm, sample and gene counts, timings |

Read one with:

```python
import numpy as np, json
from gene_panel_structure import unpack_upper_triangle

with np.load("genecorr.npz", allow_pickle=True) as npz:
    genes = [str(g) for g in npz["genes"]]
    mat = unpack_upper_triangle(npz["r_within"], len(genes))
    meta = json.loads(str(npz["meta"]))
```

Gene order **differs between jobs**, because coverage differs by strategy and platform.
Always use the file's own `genes` array; never assume the union order.

---

## Design notes

**Two correlation flavours.** A global correlation between two genes can be produced
entirely by batch structure — both genes higher on one platform than another — without
the genes being co-expressed inside any single cohort. The within-cohort flavour is the
biologically meaningful redundancy measure and drives the panel selection; the global
one is kept so the difference can be shown.

**Fisher z.** Correlations are averaged as `arctanh(r)`, not as `r` (Fisher 1921;
Silver & Dunlap 1987). `|r|` is clipped to `1 − 1e-6` first, because a Spearman
correlation of exactly ±1 is common in small cohorts and `arctanh(1)` is infinite.

**float16 storage.** Correlations are used here for clustering and thresholding, where
three decimal digits are ample. The consensus accumulates in float64, so the average is
not degraded beyond the per-job quantisation.

**Where the QC thresholds apply.** Zero inflation and the fraction below 1 are
properties of the *unharmonized* measurement: most harmonizers shift and rescale the
values, so a threshold of 1 on the log2 scale stops meaning the same thing afterwards.
Read those columns from the `01_raw` rows. They are computed for every attempt anyway,
so the change each method causes can itself be plotted.

**Coverage.** Measured over harmonized attempts, coverage is contaminated by the
harmonizers — a method that drops genes changes the denominator. The primary column is
`present_in_all_raw_pairs`, over the 42 `01_raw__post0` matrices alone.

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Worker exits with code 2 | Memory guard tripped. Lower `--n-workers` or raise the node size; the worker aborts rather than being OOM-killed mid-write |
| Worker exits with code 3 | Expression or annotation file missing on S3. Counted as MISSING, not as a failure, and not retried |
| Worker exits with code 4 | Unknown `--corr-flavors` value; valid ones are `global` and `within` |
| Many TIMEOUTs | Raise `--timeout-s`. The 1,200 s default is generous for a ~300 MB matrix; a run of timeouts usually means the node is thread-oversubscribed — check that the BLAS pinning at the top of `run_gene_corr_job.py` survived any edit |
| Resuming after a kill | Just relaunch. Add `--skip-if-exists` to skip attempts whose two S3 outputs already exist; `--retry-failed` re-attempts the entries in `failed_jobs_gene_corr.txt` |
| Consensus matrix smaller than expected | The union gene index is built from the jobs actually on S3. Check the dispatcher log for MISSING and FAILED lines before reading the matrix as complete |
| Stale `.npz` after a panel change | `marker_gene_annotation.csv` defines the panel; regenerating it changes the gene set. Delete the `gene_corr/` and `gene_qc/` prefixes and re-run — the job does not version the panel |
