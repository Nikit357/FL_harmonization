# ComboBatch — harmonizing transcriptomes across 88 lymphoma cohorts

Code, metric tables and figures for a systematic benchmark of transcriptomic
batch-effect harmonization in follicular lymphoma (FL), diffuse large B-cell lymphoma
(DLBCL) and normal germinal-centre B cells.

**Dataset:** 7,174 samples · 88 cohorts · 29 batch levels · 19 platforms.
**Benchmark:** 39 harmonization methods implemented, 31 evaluated, across 14
sample-removal strategies × 3 imputation modes × 2 post-removal variants →
2,407 runs, **2,234 valid attempts**, each scored on **87 metrics** in 14 groups.

> **Read `DATA_AVAILABILITY.md` first.** 15 of the 88 cohorts are proprietary or under
> controlled access. The analysis used all 7,174 samples; the deposited per-sample
> tables describe 5,178. That is a redaction, not a discrepancy — and it means the
> harmonization runs cannot be reproduced bit-for-bit from the open data alone, while
> the metric tables and rankings reproduce exactly.

## The headline result

No single harmonizer wins. The right choice depends on which biomaterials and
platforms are being mixed:

| Data being combined | Recommended |
|---|---|
| Fresh-frozen only | MNN, or FSQN (R), no post-removal |
| **FFPE only** | **SVA + softimpute/KNN** — first demonstrated platform mixing for FFPE |
| **RNA-seq only** | **SVA + softimpute/KNN** — FF and FFPE fully mixed; two FL subgroups resolve |
| RNA-seq + Illumina microarrays | FSQN (R) without post-removal, or AMDBNorm/FSMVN with it |
| RNA-seq + mixed microarrays | **MNN + post-removal** |

Two findings drive that table:

1. **Most harmonizers erase the biology.** Only MNN, FSQN (R) and SVA preserve the
   FL / DLBCL / normal GC B-cell distinctions. The rest were designed for
   TCGA/GTEx-scale variation and over-correct at this one.
2. **Global metrics are necessary but not sufficient.** SVA achieves the best *local*
   mixing while scoring poorly on global correction (PCR, R²). Judging on global
   metrics alone picks the wrong method.

Impact ordering: **strategy > method > post-removal > imputation**. Softimpute beats
KNN imputation by roughly 10 percentage points.

## Layout

```
harmonization-scripts/            the benchmark itself
  bench_shared.py                 39 method implementations, filter strategies, S3 I/O
  run_prep_parallel.py            stage 1 — prepare (strategy × imputation) pairs
  run_norm_parallel.py            stage 2 — normalize every prepared pair
  run_one_job.py                  single job, for debugging
  Dockerfile, requirements.txt    the runtime; k8s/ holds the pod manifests

harmonization-metrics-calculation/  scoring
  compute_batch_metrics.py        14 metric groups (A–N); L/M/N are the blind check
  marker_gene_annotation.csv      633 genes · 63 signatures · 7 cited sources
  run_metrics_parallel.py         dispatcher; run_metrics_concat.py aggregates

harmonization-metrics/            analysis and figures
  harmonization_metrics_analysis*.ipynb   rankings over the metric tables
  correlation_prediction_metrics_analysis.ipynb   the blind marker/prediction check
  marker_gene_deep_analysis.ipynb          minimal orthogonal panel selection
  metric_tables/                  the published per-run metric tables

figures_for_article/              manuscript, figures, supplementary tables
shambhala_adoption/               pure-Python Shambhala port (excluded from Article 1)
SOM_implementation/               oposSOM pipeline on FSQN-normalized data
slides_for_project/               progress decks
plan.md, research.md, project_overview.md, */CLAUDE.md
                                  the working record — kept deliberately, this is the
                                  context needed to follow what was done and why
```

## Running it

Python 3.11, plus R 4.5 with Bioconductor for the methods reached through `rpy2`.

```bash
pip install -r harmonization-scripts/requirements.txt
```

The pipeline reads and writes object storage, and **has no default bucket** — it fails
at import rather than silently using the wrong one. Any placeholder works for offline
work (inspecting metric tables, rebuilding figures, running the mock tests):

```bash
export FL_S3_BUCKET=your-bucket        # required
export FL_S3_PREFIX=FL_batch_correction # optional, this is the default
export FL_DATA_ROOT=/path/to/prepared   # prepared expression/annotation TSVs
export FL_SHARED_ROOT=/path/to/refs     # gene-set and reference files
```

```bash
# smoke test — every method's entry point, on synthetic data
FL_S3_BUCKET=dummy python harmonization-scripts/test_mock.py
FL_S3_BUCKET=dummy python harmonization-metrics-calculation/test_mock_metrics.py

# stage 1: prepare the (strategy × imputation) pairs
python harmonization-scripts/run_prep_parallel.py --n-workers 4 --skip-if-exists

# stage 2: normalize every prepared pair
python harmonization-scripts/run_norm_parallel.py --n-workers 6 --skip-if-exists

# a single job, for debugging
python harmonization-scripts/run_one_job.py \
    --strat A_confirmed_bad --imp strict --method 16_fsqn_r --out-json result.json

# scoring, then aggregation into metrics_comprehensive.csv
python harmonization-metrics-calculation/run_metrics_parallel.py --n-workers 4
python harmonization-metrics-calculation/run_metrics_concat.py
```

The Kubernetes manifests under `harmonization-scripts/k8s/` and
`harmonization-metrics-calculation/k8s/` are templated: fill in `${K8S_NAMESPACE}`,
`${K8S_NODE_GROUP}`, `${AWS_ACCOUNT_ID}` and `${AWS_REGION}`, and supply your own SSH
public key through a Secret (the recipe is in the manifest comments).

## What will not run as-published

Parts of this work ran against an internal cohort database and an internal analysis
library, neither of which is public. Every borrowed helper is redefined on public
packages in a compatibility shim at the top of `all_cohorts_assembly.ipynb`, so the
notebook stays readable as a record — but **two of those helpers are deliberately not
faithful, and are labelled as such in the shim**:

- `median_scale` — centring is exact; the internal scale factor was never published, so
  the spread of its output may differ from the figures.
- `ssgsea_formula` — delegates to `gseapy`, whose normalization differs from the
  internal implementation the published scores came from.
- `run_progeny` — **raises**, rather than substitute a different method silently. Use
  `decoupler` with PROGENy and re-derive any figure that depends on it.

Do not treat output from those three as reproducing published values.

## Licence

- **Code** — MIT (`LICENSE`).
- **Figures, tables, supplementary files, manuscripts, documentation** — CC BY 4.0
  (`LICENSE-DATA`), which also lists third-party material under its own terms.

Both permit commercial use, modification and redistribution; both require attribution.

## Citing

See `CITATION.cff`. Please cite the article and link to this repository.
