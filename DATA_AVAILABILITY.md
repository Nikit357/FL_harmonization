# Data availability

## The short version

The analysis behind this article used **7,174 samples from 88 cohorts**. The tables
deposited in this repository describe **5,178 samples from 73 cohorts**.

**That gap is a redaction, not a discrepancy in the science.** Every statistic, figure
and metric in the article was computed on the full 7,174 samples. Fifteen of the 88
cohorts are proprietary or under controlled access, and for those neither expression
values nor per-sample annotation — *including the sample identifiers* — may be
redistributed here.

The withheld cohorts are still **named** throughout the repository and the article,
with the sample count each contributed, so every number quoted remains traceable and
readers know where to apply for the underlying data.

## What is in this repository

| Kind | Where | Coverage |
|---|---|---|
| Per-sample annotation | `figures_for_article/supplementary_*/Supplementary File 1.csv` | 5,178 samples (73 open cohorts), full annotation |
| Full per-sample annotation | `comb_ann_public.csv` | the same 5,178 samples with the complete annotation set — 192 columns. See the note below: this is the one table redacted column-wise as well as row-wise |
| Cohort summary | `…/Supplementary File 1 short.csv` | **all 88 cohorts**, including the 15 withheld, with counts and provenance |
| Genes per sample | `…/Supplementary File 2.csv` and `.xlsx` | open cohorts only |
| Per-run harmonization metrics | `…/Supplementary File 3.csv.gz`, `harmonization-metrics/metric_tables/metrics_comprehensive_*.csv` | **all 2,234 attempts** — keyed on run, not on sample, so nothing is withheld |
| Marker-correlation and prediction tables | `harmonization-metrics/metric_tables/*_long_*.csv` | **complete** — they carry a `cohort` column but no sample column |
| Marker gene panel | `harmonization-metrics-calculation/marker_gene_annotation.csv` | complete; 633 genes, 63 signatures, 7 cited source articles, plus the 56-gene `in_narrow_set` QC-filtered subset |
| Marker gene panel, with per-gene statistics | `…/Supplementary File 2.xlsx`, sheet `Table_S3_gene_panel` | complete; 834 (gene, signature) rows × 66 columns — the panel joined to its coverage audit and per-gene ρ/QC statistics |

Expression matrices are **not** in this repository for any cohort, open or withheld —
they are large, and for the open cohorts they are already available from their public
repositories under the accessions listed in `Supplementary File 1 short.csv`.

## The 15 withheld cohorts

| Cohort | Samples withheld | Where to apply |
|---|---:|---|
| SOM | 623 | contact the originating group |
| PUB_DLBCL_NCICCR | 567 | **dbGaP phs001444.v2.p1** (controlled access) |
| PUB_FL_TOBIN | 224 | contact the originating group |
| Kassandra | 140 | contact the originating group |
| PUB_DLBCL_DLC1 | 133 | contact the originating group |
| COLL_DLBCL_UMLOSSOSTRANSL | 75 | contact the originating group |
| PUB_DLBCL_LYMPHOMICS | 73 | contact the originating group |
| MDA_Strati_FL | 35 | contact the originating group |
| CRON3 | 27 | contact the originating group |
| PUB_FL_NCIFFPEREBUILT | 25 | contact the originating group |
| PUB_DLBCL_NCIACALA | 23 | contact the originating group |
| PUB_FL_NCISTAUDT | 19 | contact the originating group |
| Leandro-Normals | 16 | contact the originating group |
| PUB_DLBCL_YANCART | 8 | contact the originating group |
| E-MTAB-3974 | 8 | contact the originating group |
| **Total** | **1,996** | 27.8% of the 7,174 analyzed samples |

For `PUB_DLBCL_NCICCR`, apply through dbGaP study **phs001444.v2.p1**. For the rest,
contact the originating group; `Supplementary File 1 short.csv` records what is known
about each cohort's provenance.

## Consequences for reproduction

- **Metric tables and rankings reproduce exactly.** They are keyed on
  `(strategy, imputation, method, post_rm)`, contain no sample-level data, and are
  published in full.
- **Harmonization runs do not reproduce exactly** from the open data alone: 27.8% of
  the input samples are missing, and batch-effect correction is a function of the whole
  matrix. Re-running on the 5,178 open samples is a *different* experiment, not a
  replication.
- **Five Shambhala calibration matrices are withheld** because they are derived from
  proprietary cohorts. Their registry entries are kept in
  `shambhala_adoption/Shambhala_containerized/harmonization_scripts/shambhala_bench_shared.py`
  and marked in place, so the run identifiers in the published metric tables still
  resolve.
- **The internal cohort database and analysis library are not public.** The notebooks
  that used them carry a public compatibility shim; see the README's "What will not run"
  section for the two helpers that are explicitly *not* numerically identical.

## Sample-identifier redaction, precisely

Redaction is **row-wise** for every deposited table but one. A deposited table keeps
every column, including `COHORT_LABEL`; it simply loses the rows belonging to the 15
withheld cohorts. No pseudonymization is used anywhere — an identifier is either
published as-is or withheld entirely.

`comb_ann_public.csv` is the exception, and it is worth stating plainly because it shows
why a row filter is not by itself a redaction. That table arrives already filtered to the
73 open cohorts, yet 76 of its surviving open-cohort rows still named a withheld sample
in a *column* (`PUBLIC_SAMPLE_LABEL`). Those 76 cells are blanked. Three further
column-wise edits were made to the same file, none of which changes a single row or any
analytical value:

- the `AUTHOR` column was dropped — it carried a colleague's work address in every
  populated row and holds no analytical information;
- 293 columns that were empty across all 5,178 rows were dropped, leaving **192**. They
  were internal-database schema with no content;
- `avicennaid` was renamed `treatment_regimen_detail`, which is what it holds — 1,271
  chemotherapy regimen names, and the deposit's only source of regimen detail
  (`TREATMENT_REGIMEN` records only whether a sample is pre- or post-treatment).

`bags_class` is deliberately **kept** under its own name: it holds the published
B-cell Associated Gene Signatures call of Dybkaer et al. 2015 for the 55 samples of the
open `PUB_DLBCL_BAGS` cohort (GSE56313), whose supplementary tables this repository
already cites. Every edit above is reproducible by re-running
`make_public_supplementary.py`.

Two files retain redacted placeholders rather than dropped rows, because they are logs
whose structure would otherwise be destroyed:
`shambhala_adoption/Shambhala_containerized/logs/shambhala_pod_logs_2605{16,17}.txt`,
where 26,775 withheld identifiers were replaced with `<redacted-sample>` while 2,350
public `GSM…` identifiers were kept, so the files still read as a debugging record.
