## What is withheld, and why the counts differ from the article

The analysis behind this article used **7,174 samples from 88 cohorts**. This record
contains **5,178 samples from 73 cohorts**. Fifteen cohorts are proprietary or under
controlled access, and for those neither expression values nor per-sample annotation —
*including the sample identifiers* — may be redistributed. All 88 cohorts are still
**named**, with the sample count each contributed, in `cohorts.csv`.

This is a redaction of the deposited files, not a discrepancy in the science: every
statistic, figure and metric in the article was computed on the full 7,174 samples.

## These matrices are subsets, not re-runs

Each deposited matrix is the **exact** matrix the article's metrics were computed on,
with the proprietary rows deleted. It is *not* the result of re-harmonizing the 5,178
open samples. Because batch correction is a function of the whole matrix, re-running
the pipeline on the open subset is a different experiment, not a replication, and its
metrics will not match the published tables.

## Withheld fractions are not uniform

| Strategy | Total | In this record | % |
|---|---:|---:|---:|
| `C_rnaseq_only` | 2,243 | 878 | 39% |
| `J_ff_only` | 3,167 | 2,203 | 70% |
| `S0_no_removal` | 7,174 | 5,178 | 72% |
| `A_confirmed_bad` | 5,444 | 4,071 | 75% |
| `K_ffpe_only` | 3,000 | 2,591 | 86% |
| `F_microarray_only` | 4,931 | 4,300 | 87% |

`C_rnaseq_only` loses 61% of its samples because the RNA-seq arm is dominated by
cohorts that cannot be redistributed. Treat any reanalysis of that strategy on this
record as a study of 878 samples. The full table is `strategy_sample_counts.csv`.

## Annotation schema

The deposited annotation has **192 columns** — a sample identifier and 191 annotation
fields. The internal schema has 486, of which 293 are empty for every public sample and
one identifies a colleague by e-mail; all 294 are removed. Two columns are renamed to say what they contain rather than which
internal system produced them — `bcell_type_call` and `treatment_regimen_detail` —
and their values are unchanged.

## Shambhala

One Shambhala configuration is included: the default `P0std × Q0std` calibration pair,
named **`20_shambhala`** — the same name used in the article's Supplementary File 3.
Seventeen further P/Q variants were run during the benchmark and are not deposited;
they are excluded from the article, and their matrices are available from the authors
on request.

## Numeric precision

Every value is rounded to **4 decimal places**, so the absolute error is at most
5·10⁻⁵ whatever the method's scale. The unrounded values differ only in float64 noise —
the sources store 17 significant digits, of which roughly 13 are noise. On a log2 scale
that bound is far below any biological signal; on the one linear-scale method
(`20_shambhala`, values up to ~10⁵) it is a relative error near 10⁻⁹.

## Two methods produce mostly-empty matrices

`34_arsyn` and `38_harman` return matrices that are roughly **87% missing values** in
every one of their 84 runs. That is what the benchmark actually produced — the two
methods did not complete normally — and the matrices are deposited as they are, so the
record matches the metric tables run for run. They are **not** usable as harmonized
expression data. The article's rankings exclude them.

`manifest.csv` carries `pct_na_cells` for every matrix so this is visible without a
join; `metrics_comprehensive` carries the same figure alongside `pct_samples_noNA` and
`pct_genes_noNA`. Note that the `status` column of the metric tables reads `ok` for
these runs — it records that the job exited, not that the output is sound.

## `post1` matrices have fewer samples than `post0`

`post0` and `post1` are the same harmonization run without and with post-normalization
outlier removal, so a `post1` matrix is **not** a row-aligned twin of its `post0`
sibling — it is a subset, sometimes a small one. `C_rnaseq_only__strict__01_raw__post1`
keeps 325 of that strategy's 878 public samples. Every matrix's own row count is in
`manifest.csv` (`n_samples`); do not take it from `strategy_sample_counts.csv`, which is
the `post0` figure.

## Two `post0` matrices are also short, by 118 samples

`19_tdm` and `20_shambhala` are reference-based: each batch is mapped onto a reference
distribution, and a batch that cannot be mapped is dropped rather than harmonized. In
`H_affymetrix_extended` both discard the same 118 samples — three single-cohort
Affymetrix batches, `GPL20188` (68 samples), `GPL23541` (35) and `GPL26356` (15) — so
`H_affymetrix_extended__strict__19_tdm__post0` and
`H_affymetrix_extended__strict__20_shambhala__post0` hold 2,978 rows where that
strategy's other `post0` matrices hold 3,096. These are the only two `post0` matrices in
the record that are short of their strategy; every other one is full size. As always,
the row count that applies to a given matrix is the one in `manifest.csv`.

## Orientation and conventions

Matrices are **samples × genes** (rows = samples). Gene symbols are HGNC. The first
column holds the sample identifier under an empty header cell.

**The value scale is the method's, not a single convention.** The *input* matrices —
`comb_exp_public.tsv.gz` and everything in `prepared_inputs__*.zip` — are
log2(x+1)-transformed per cohort. A harmonization method is free to change that, and
several do. Measured on `grid_strict__C_rnaseq_only`: `18_rank` and `25_angel` return
ranks in [0, 1]; `23_vst` returns a variance-stabilised scale (~0.4–3.8); `28_npn`
returns a z-like scale (~−2.4–3.7); `19_tdm` maps onto a target range (~1–92); and
`20_shambhala` is **linear, not log** (~15–110,000). Methods that mean-centre
(`02`, `03`, `05`, `07`, `11`, `13`, `21`) return negative values. Check the range of a
matrix before comparing it with another method's, and never concatenate two methods'
outputs without rescaling.

**Gene sets differ by method too.** Most methods return the strategy's full gene set,
but `20_shambhala` and `25_angel` return their own reduced spaces (2,293 and 3,582
genes for `C_rnaseq_only__strict`). `manifest.csv` records `n_genes` per matrix.

ZIP members are *stored*, not deflated, so a single matrix can be streamed out without
expanding the archive:

```python
import zipfile, gzip, io, pandas as pd
with zipfile.ZipFile("grid_strict__A_confirmed_bad.zip") as zf:
    name = "A_confirmed_bad__strict__10_mnn__post0.public.tsv.gz"
    with gzip.open(io.BytesIO(zf.read(name)), "rt") as fh:
        exp = pd.read_csv(fh, sep="\t", index_col=0)
print(exp.shape)   # (4071, 3520)
```

## Where to start

`manifest.csv` indexes every one of the deposited matrices — which bundle it is in,
its shape, its checksum, and whether it is one of the 15 clustermap-derived best
approaches (`is_best15`) or a decision-tree recommendation (`is_decision_tree`).

## Attribution

These matrices are derived from 73 publicly deposited studies. Please cite the
original studies as well as this deposit; accessions are in `cohorts.csv`.
