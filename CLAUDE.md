# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bioinformatics dissertation at **BostonGene** on transcriptomic characterization of germinal center (GC) B-cell lymphomas. Dataset spans DLBCL and FL with normal B-cell references.

**Researcher:** Daniil Nikitin (`author@example.com`) | **Target publication:** Autumn 2026  
**Working directory:** `~/FL_harmonization` | **Remote data root:** `$FL_DATA_ROOT/`

Subsystem-specific CLAUDE.md files (read before editing those directories):
- `harmonization-scripts/CLAUDE.md` — full 39-method registry, S3 API, Docker/K8s instructions
- `harmonization-metrics-calculation/CLAUDE.md` — metrics compute pipeline, 14 metric groups, pod launch and operations
- `harmonization-metrics/CLAUDE.md` — metrics analysis notebooks and figures
- `harmonization-scripts/k8s/CLAUDE.md` — K8s manifest guide for the benchmark pod
- `slides_for_project/CLAUDE.md` — supervisor slide generation with python-pptx

For full research context, dataset details, analytical pipeline, and literature anchors see `project_overview.md`.

---

## Commands

```bash
# Activate the Python environment (always required first)
source ~/venvs/collagen_3_11/bin/activate

# Run SOM pipeline (pre-normalized FSQN R data, primary)
python SOM_FSQN_R.py

# Two-stage harmonization benchmark (preferred — preparation runs once, normalization reuses it)
# Stage 1: prepare all (strategy × imputation) = 40 pairs
nohup python harmonization-scripts/run_prep_parallel.py \
    --n-workers 4 --skip-if-exists \
    --timeout-s 7200 --memory-limit-gb 6.0 > prep_run.log 2>&1 &

# Stage 2: normalize all prepared pairs (39 methods × 44 pairs = 1,716 jobs → 3,432 S3 outputs)
nohup python harmonization-scripts/run_norm_parallel.py \
    --n-workers 6 --skip-if-exists > norm_run.log 2>&1 &

# Run a single normalization job (useful for debugging)
python harmonization-scripts/run_one_job.py \
    --strat A_confirmed_bad --imp strict --method 16_fsqn_r --out-json result.json

# Map GPL570 Affymetrix probes to HGNC symbols
python GPL570_mapping.py

# ── Comprehensive metrics pipeline (run inside fl-metrics pod) ──
nohup python harmonization-metrics-calculation/run_metrics_parallel.py \
    --n-workers 4 --skip-if-exists --skip-slow \
    --post-rm-filter post0 --memory-limit-gb 6.0 > metrics_fast.log 2>&1 &

python harmonization-metrics-calculation/run_metrics_concat.py  # aggregate → metrics_comprehensive.csv

# ── Blind final check: marker correlation + prediction (metrics pod) ──
# Groups L/M/N. No --skip-if-exists: every target job already has a sidecar and the
# worker's sentinel logic is what resumes. --n-workers ≈ (vCPU − 8) on the node in use.
cd harmonization-metrics-calculation
nohup python run_metrics_parallel.py \
    --groups L,M,N --only-with-metrics --skip-shambhala \
    --n-workers 40 --memory-limit-gb 8.0 --timeout-s 1800 \
    --n-perm 100 --ref-cache-dir /workspace/ref_cache \
    > /workspace/metrics_lmn.log 2>&1 &
python run_metrics_concat.py   # → metrics_comprehensive.csv + 3 long-format tables

# ── Shambhala harmonization (run inside fl-shambhala pod) ──
# Cross-product: 18 P/Q variants × 3 imputations = 54 jobs → 1,512 S3 outputs (14 strategies)
cd shambhala_adoption/Shambhala_containerized
python run_shambhala.py --help

jupyter lab
```

There is no test suite or linter configuration. Format new Python code with Black (line length 88).

---

## Dataset

**7,174 samples** / 88 cohorts / 29 RNA_BATCH levels / 19 platforms. After bad-batch exclusion: **5,444 samples × 3,447 genes (no NA)**. The authoritative annotation is the prepared copy on S3 (`prepared/{strat}__{imp}__ann.tsv.gz`, verified 7,174 × 485) — **not** the local `comb_ann_unified.csv`, which has 7,238 rows because 64 samples carry annotation but no expression. Diagnosis groups: DLBCL ~3,000, FL ~2,000, Normal B cells ~1,000; rare subtypes excluded. Key annotation columns: `Diagnosis_cell_type_unified`, `RNA_BATCH`, `PLATFORM_RNA`, `RNASEQ_SOURCE`, `TUMOR_NORMAL`, `OS`, `PFS`, `COHORT_LABEL`.

---

## Batch Effect and Normalization

Raw data: **~95% PCA variance explained by RNA_BATCH**. Selected for SOM: **FSQN R (~16%)** — pre-computed at `$FL_DATA_ROOT/fsqn_normalized_exp_R.tsv`.

**Final decision tree (June 2026):**
- FF only → MNN or FSQN R (no post-removal)
- FFPE only → **SVA + softimpute/KNN** ★ first-ever platform mixing; best local result in benchmark
- RNA-seq only → **SVA + softimpute/KNN** (FF/FFPE fully mixed; two FL subgroups visible)
- RNA-seq + Illumina microarrays → FSQN R (no post-removal) or AMDBNorm/FSMVN + post-removal
- RNA-seq + various microarrays → **MNN + post-removal**

**Key conclusions:** Most harmonizers (except MNN, FSQN R, SVA) fail to preserve FL/DLBCL/normal GC B cell differences — designed for TCGA/GTEx-scale variation. Global metrics (PCR, R²) are necessary but not sufficient: SVA achieves top local mixing without strong global correction. Softimpute ~10 pp better than KNN. Shambhala excluded from Article 1.

**Critical:** Batch test fails in SOM metagene space even after FSQN. **Restrict SOM to RNA-seq only.**

Hierarchy: **strategy > method > post-removal > imputation**. Full details in `project_overview.md`.

---

## Key Files

| File | Purpose |
|---|---|
| `all_cohorts_assembly.ipynb` | Master notebook: cohort download, concatenation, normalization, ssGSEA, SOM |
| `harmonization_benchmark.ipynb` | Systematic benchmark; PCA R² heatmaps |
| `harmonization-scripts/bench_shared.py` | 39 normalization implementations, filter strategies, R² metrics, S3 I/O |
| `harmonization-scripts/run_prep_parallel.py` | Stage 1 dispatcher: 40 (strat × imp) preparation jobs |
| `harmonization-scripts/run_norm_parallel.py` | Stage 2 dispatcher: normalization jobs |
| `harmonization-scripts/run_norm_job.py` | Stage 2 worker: download prepared → normalize → upload two post_rm variants |
| `harmonization-metrics-calculation/compute_batch_metrics.py` | Core library: 14 metric group functions (A–N) + `compute_all_metrics()`; groups L/M/N are the blind check and are excluded from the clustermap |
| `harmonization-metrics-calculation/marker_gene_annotation.csv` | Gene panel source of truth for groups L/M: 633 genes, 63 signatures, cell type / pathway / TME subtype / prognosis / source per gene |
| `harmonization-metrics-calculation/marker_panels.py` | Loader over the gene annotation CSV (`panel_genes()`, `resolve_panel()`, `panel_summary()`) |
| `harmonization-metrics-calculation/k8s/pod-metrics.yaml` | Metrics pod manifest; `README.md` in the same folder is the step-by-step launch guide |
| `harmonization-metrics/correlation_prediction_metrics_analysis.ipynb` | Blind-check analysis: groups L/M/N, best-vs-rest, permutation control, Supplementary File 5 |
| `harmonization-metrics/marker_gene_deep_analysis.ipynb` | Marker panel deep-dive: gene-level correlation structure, coverage/QC/saturation gates, minimal orthogonal panel selection |
| `harmonization-metrics-calculation/gene_panel_analysis/` | Sub-pipeline for the above: gene × gene correlation + per-gene QC (1,204 jobs); own README |
| `harmonization-metrics/harmonization_metrics_analysis.ipynb` | Loads `metrics_comprehensive.csv`, visualizes rankings |
| `shambhala_adoption/Shambhala_containerized/run_shambhala.py` | Shambhala CLI entry point (pure Python, no R/rpy2) |
| `shambhala_adoption/Shambhala_containerized/harmonization_scripts/` | Cross-product benchmark: 18 P/Q × 3 imp = 54 jobs |
| `SOM_FSQN_R.py` | SOM pipeline: pre-normalized FSQN R data → limma → oposSOM |
| `bcell_typing_2022_clean.ipynb` | B-cell type classifier training |
| `comb_ann_unified.csv` | Annotation with `Diagnosis_cell_type_unified` column |
| `MDA_Strati_FL_annotation.csv` | MDA FL cohort clinical annotations (OS, PFS, POD24, FLIPI) |
| `local_copy.zarr/` | Zarr-format data store (normalized expression + obs metadata) |

---

## Code Standards

### Language and environment
- **Primary language:** Python 3.11 (Jupyter notebooks + `.py` scripts)
- **R integration:** via `rpy2` for oposSOM, limma, FSQN, sva/neuroCombat (see `project_overview.md` for `localconverter` pattern)
- **Package management:** `pip` (do not use `uv`)
- **Virtual environment / iPython kernel:** `~/venvs/collagen_3_11/`
- **Notebooks:** `nbstripout` strips outputs before commit

### Python conventions
- `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE_CASE` constants
- Type hints for all new functions; docstrings with `Parameters` / `Returns` sections
- Line length: 88 characters (Black)

### Plot defaults
```python
plt.rcParams["pdf.fonttype"] = "truetype"
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["figure.dpi"] = 200
sns.set_style("ticks")
```

### Data conventions
- Expression matrices: **samples × genes** in Python (transposed to genes × samples for R)
- Index: `Unnamed: 0` in TSV files; set as index on load
- All expression values: log2-transformed (log2(x+1) for non-negative input)
- NaN handling: drop genes with >5,000 NA for global analysis; full-coverage subset (no NA) for SOM
- Gene symbols: HGNC throughout; probes must be mapped first
- S3 key pattern: `FL_batch_correction/exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz`

---

## Infrastructure

- **Cohort database** — the cohorts were assembled from an internal cohort database;
  see `DATA_AVAILABILITY.md` for the public accession or application route for each
- **S3** — `boto3`; bucket `$FL_S3_BUCKET/FL_batch_correction/`
- **K8s benchmark pod** — `fl-batch-correction`, `ubuntu:24.04`, 16 vCPU / 240 GiB RAM, R 4.5 + Bioconductor 3.22
- **K8s metrics pod** — `fl-metrics`, 128 GiB, R + variancePartition. SSH public key lives in the `ssh-pubkey` Secret, not in the manifest; node size is tuned manually at launch
- **K8s Shambhala pod** — `fl-shambhala`, 32 vCPU / 240 GiB RAM, Octave + Python 3.11
- **Docker image** — `${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/fl-batch-correction:latest`
- **Gene set databases** — DLBCL signatures (27, `dlbcl_signatures.gmt`), HALLMARK, KEGG, PROGENy

---

## Current Status (June 2026)

### Completed
- [x] Multi-platform cohort assembly (88 cohorts, ~7,174 samples); FSQN R selected for SOM
- [x] Benchmark: 31 methods × 14 strategies × 3 imputation × 2 post_rm = 2,407 runs → 2,234 valid attempts
- [x] Comprehensive metrics: **87 scoring metrics** (of ~230) on 2,234 attempts; hierarchy A > B > J > K
- [x] Visual inspection done; SVA+FFPE-only is best local; MNN best multi-metric overall
- [x] oposSOM runs; SOM portraits generated; AnnData passed to Tolya for embeddings
- [x] Shambhala containerized (pure-Python, 69 tests, A_E 8.6× speed-up); 1,296 harmonizations (excluded from Article 1)
- [x] **Final decision tree approved** 2026-06-04; only MNN, FSQN R, SVA resolve FL/DLBCL/Normal GC B cell differences
- [x] **Article draft started** (`figures_for_article/FL_manuscript_versions/FL_harmonization_article.docx`); pipeline named **ComboBatch**
- [x] **Introductory figures done**: pipeline scheme, bubble charts, barplots, Circos-Sankey strategies

### Next steps — Article 1 (short timeline)

- [ ] **Blind final check compute run**: metric groups L/M/N over the 2,323 non-Shambhala attempts (plan: `harmonization-metrics/marker_and_predictive_validation_plan_260819.md`)
- [ ] **Blind check figures**: run `correlation_prediction_metrics_analysis.ipynb` once the metrics land; export Supplementary File 5
- [ ] **Marker panel reduction**: run `harmonization-metrics-calculation/gene_panel_analysis/run_gene_corr_parallel.py`, then `marker_gene_deep_analysis.ipynb` → recommended minimal orthogonal gene panel for the Group L metric (plan: `harmonization-metrics/marker_gene_deep_analysis_plan_260827.md`)
- [ ] Manuscript sub-chapters for the blind check — **deferred until the results exist** (see `project_manuscript_lmn_sections_deferred.md` in project memory)
- [ ] **Figure 2C/2D**: NA genes per batch barplot; imputation gene-overlap Sankey (see `article_figures_status_260625.md`)
- [ ] **Figure 3**: publication-grade clustermap (2,234 attempts × 87 metrics); new `Harmonization_clustermap_figure.ipynb`
- [ ] **Figure 4**: hierarchical decision tree (4 levels: biomaterial → platform → method → QC)
- [ ] Complete gene retention analysis across imputation strategies
- [ ] Fill stub sections in Results (best approaches, relative impact, global/local trade-off, decision tree)
- [ ] Materials & Methods: fill in harmonization methods table, metric groups table, imputation parameters
- [ ] Update pipeline scheme label to "31 methods" (not 39)

### Next steps — Article 2 (long timeline, Shambhala_3)

- [ ] Reliably pythonify CuBlock (replace Octave dependency; speed + reproducibility)
- [ ] Shambhala_3: replace CuBlock with MNN (proven for FL; catches subtle biology)
- [ ] Transfer learning metrics: 5-fold CV within cohort → accuracy/AUC/MCC; cross-cohort generalization
- [ ] Random permutation baseline (permute class labels → verify metrics drop)
- [ ] Study Borisov 2023 (doi:10.3389/fmolb.2023.1237129)
- [ ] Classifiers: KNN, SVM, DNN (PyTorch) for cross-cohort class prediction
