# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

**Analysis** side of the metrics work: notebooks, figures, and the dated
`metrics_comprehensive_*.csv` snapshots produced by the compute pipeline.

The **compute pipeline and everything needed to launch the K8s pod moved to
`../harmonization-metrics-calculation/`** (2026-08-20) so it can be sparse-checked-out on its own
— see `../harmonization-metrics-calculation/CLAUDE.md` for the metric group definitions, the S3
layout, worker/dispatcher commands, and pod operations. Nothing in this directory runs inside the
pod.

## Commands

```bash
# Rebuild the blind-check analysis notebook (groups L/M/N)
python create_correlation_prediction_notebook.py

# Rebuild the primary v3 analysis notebook
python create_v3_notebook.py

# Rebuild the marker gene deep-analysis notebook
python create_marker_gene_deep_analysis_notebook.py
```

Regenerate rather than hand-editing the `.ipynb`.

`correlation_prediction_metrics_analysis.ipynb` is **self-contained** (since 2026-08-25): it
imports nothing from this repository, manipulates no `sys.path`, and names every input file as a
constant in its first cell — including `marker_gene_annotation.csv`, which it reads directly
instead of importing `marker_panels`. To point it at a new metrics run, change `DATE_TAG` in
`create_correlation_prediction_notebook.py` and regenerate.

## Architecture

### File roles

| File | Role |
|---|---|
| `harmonization_metrics_analysis_v3.ipynb` | **Primary analysis notebook** (353 cells): quantitative comparison of 2,234 attempts × 87 metrics; clustermaps, per-group plots, composite scoring, gene set analysis |
| `create_v3_notebook.py` | Generator for the notebook above |
| `harmonization_metrics_visual_inspection.ipynb` | **Visual inspection notebook** (338 cells): PCA/UMAP/tSNE grids per strategy; interactive decision tool; uses `plot_embedding_grid()` + S3 expression downloads |
| `correlation_prediction_metrics_analysis.ipynb` | **Blind-check notebook** (29 cells): groups L/M/N, best-vs-rest comparison, per-gene and per-cell-type views, permutation control, Supplementary File 5 export |
| `create_correlation_prediction_notebook.py` | Generator for the notebook above; regenerate rather than hand-edit |
| `marker_gene_deep_analysis.ipynb` | **Marker panel deep-dive notebook**: gene-set overlap (Venn/supervenn), raw-coverage and expression-quality gates, saturation split, gene × gene consensus correlation, minimal orthogonal panel selection, noise/coherence analysis |
| `create_marker_gene_deep_analysis_notebook.py` | Generator for the notebook above; regenerate rather than hand-edit |
| `marker_gene_deep_analysis_plan_260827.md` | Plan document for the marker panel deep analysis |
| `harmonization_metrics_analysis.ipynb` | Older notebook (superseded by v3); do not use for new figures |
| `insert_cells.py` | One-time helper: programmatically inserts §5–§11 analysis cells into the notebook |
| `strip_and_reorganize.py` | Strips cell outputs from the analysis notebooks and reorganizes them |
| `metric_tables/metrics_comprehensive_260824.csv` | Latest local metrics copy (August 24 2026); the first that carries the blind-check groups L/M/N (15 `mk_`, 24 `xb_`, 38 `pv_` columns). Read by the blind-check notebook |
| `metric_tables/metrics_comprehensive_260609.csv` | June 9 2026 copy; still the input of the v3 notebook. No L/M/N columns. Earlier dated copies in the same directory |
| `metric_tables/{marker_gene,marker_cohort}_correlations_long_260824.csv`, `prediction_folds_long_260824.csv` | Long-format Group L/N detail tables from `run_metrics_concat.py` |
| `metric_tables/gene_qc_long_260827.csv.gz` | Per-attempt per-gene expression QC from `gene_panel_analysis/run_gene_corr_concat.py` |
| `metric_tables/gene_gene_consensus_{within,global,sd}_260827.csv.gz` | Fisher-z consensus gene × gene correlation matrices |
| `metric_tables/marker_gene_coverage_by_attempt_260827.csv` | Per-gene coverage over the 42 `01_raw__post0` matrices and over all attempts; **supersedes** `marker_gene_coverage_audit_260819.csv` |
| `marker_gene_coverage_audit_260819.csv` | **Superseded** (predates the 2026-08-26 panel regeneration; per `(strat, imp)` pair, not per attempt): 178 genes in all 42, 325 in some, 45 in none. Still read by the blind-check notebook, whose published numbers must not move |
| `marker_and_predictive_validation_plan_260819.md` | Plan document for the blind final check (groups L/M/N) |
| `pod_folder_reorganization_plan_260820.md` | Plan document for the 2026-08-20 split into `../harmonization-metrics-calculation/` |
| `figures/` | All exported analysis figures (PDF/SVG/PNG) |
| `implementation_plans_research_old/` | Superseded plan documents kept for provenance |
| `Supplementary File 2AB.docx` | Manuscript supplementary file drafted from these metrics |

The compute scripts, the gene panel CSV, `requirements.txt`, `README.md`, and `k8s/` all live in
`../harmonization-metrics-calculation/` — see its `CLAUDE.md` for their roles.

### Analysis notebooks — detailed description

**`harmonization_metrics_analysis_v3.ipynb`** (primary; 353 cells)

Data loaded from `metric_tables/metrics_comprehensive_260609.csv`. Setup cells produce these shared objects used throughout:

| Variable | Description |
|---|---|
| `df_ok` | 2,234 rows (status=="ok"); index = `run_id` string |
| `df_normed` | Polarity-normalized [0,1]; 1=best for all 87 scoring metrics |
| `scoring_cols` | 87 metric columns with defined polarity (±1) |
| `col_meta` | Per-column metadata: group letter, type, polarity |
| `_top_ids` | Manually curated list of (method, imp, strat) best approaches |

Section structure: §2 clustermaps (Fig 3 draft in `clustermap_all_metrics_clustered.svg`); §3 per-group metric plots (Groups A–K; `figures/a_*`, `b_*`, `c_*`, `k_*`); §4 composite scoring; Part 2 gene set analysis (§5–§11). Full section map in `figures_for_article/notebooks_for_figures_260625.md`.

**`harmonization_metrics_visual_inspection.ipynb`** (exploration; 338 cells)

Same metrics CSV as v3. Key additional objects:

| Object | Description |
|---|---|
| `load_harmonized_exp(strat, imp, method, post_rm)` | Downloads expression TSV.GZ from S3; returns samples × genes DataFrame |
| `load_annotation(strat, imp)` | Downloads annotation TSV.GZ from S3 |
| `_EXP_CACHE` | In-session cache (key = (strat, imp, method, post_rm)); run cells in order |
| `plot_embedding_grid(top_ids, n_cols, color_rows, embedding)` | Main workhorse: multi-panel PCA/UMAP/tSNE grid for a list of run IDs |

Organized by strategy (J, K, A/B, C, D, F, G, H, I → cross-strategy → metric-sorted). **Does not save figures systematically** — interactive exploration only. Key decisions documented: SVA+C_rnaseq_only reveals two FL subgroups; FSQN R fails on G_affymetrix_only; arsyn/harman excluded (too many NAs).


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
└── failed_metrics_{pod_name}.txt                     ← failed-job tracking per pod
```


Producers of these keys live in `../harmonization-metrics-calculation/`; the notebooks here are
consumers only.

### Metric groups

Defined once, in `../harmonization-metrics-calculation/CLAUDE.md` — including which groups are
fast/slow, which are on by default, and why groups L/M/N are excluded from `scoring_cols` and the
Figure 3 clustermap. Not duplicated here, so the two files cannot drift apart.
