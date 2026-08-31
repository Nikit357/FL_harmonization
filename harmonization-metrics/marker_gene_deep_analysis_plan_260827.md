# Marker gene deep analysis — plan (2026-08-27)

Deep structural analysis of the **Group L** marker-correlation metric, down to the level of
individual genes, gene sets, gene–gene cross-correlation, expression quality and noise, with
the goal of selecting a **minimal, orthogonal, conservative gene panel** for the correlation
quality metric.

---

## Overview

Group L (`mk_*`) currently scores every harmonization attempt with a Spearman correlation
computed over **572 marker genes × up to 51 cohorts**, averaged into a handful of scalars
(`mk_rho_mean_all_genes`, `mk_rho_median_all_genes`, `mk_rho_marker_minus_hk`, …). Those
scalars hide three problems that only a gene-level analysis can expose:

1. **The panel is not measured uniformly.** Across the 2,407 attempts in scope (all
   non-Shambhala attempts plus the default Shambhala variant, see *Analysis scope* below),
   **no** gene is present in every attempt and only 150 reach 95 % coverage. Coverage is
   driven by the filter *strategy* (platform), not by the method. The clean, harmonization-
   independent answer is to define coverage on the **unharmonized reference only**: genes
   present in all 42 `01_raw__post0` matrices (14 strategies × 3 imputations) — that is
   **193 genes**, and it is the primary gene set of this analysis.
2. **The panel is redundant.** 63 signatures drawn from overlapping publications share genes
   and share biology; many genes almost certainly carry the same information, so the panel
   mean is an unweighted average over correlated measurements — it over-weights whichever
   biology happens to be represented by the most genes. The overlap structure itself is
   shown with Venn and supervenn diagrams plus a Jaccard clustermap.
3. **Most of the panel saturates.** 333 of the 572 genes have a median ρ above 0.99 across
   attempts (109 of the 193 reference genes): any harmonizer applying a per-batch monotone
   transform scores ~1.0 by construction. Those permanently-high genes are removed from the
   working set and presented separately in an ordered per-gene quantile plot, so the
   discriminative genes are not buried by them.

The deliverable is one **new self-contained notebook** on the analysis side, plus a **new
sub-directory `harmonization-metrics-calculation/gene_panel_analysis/`** holding five
production scripts, one test module and its own README, which produce the two data products
the notebook needs and which do not exist yet: (a) a per-attempt **gene × gene correlation
matrix** with a Fisher-z consensus across attempts, and (b) a per-attempt **per-gene
expression QC table** (zero fraction, fraction below 1, mean/variance/CV, between- vs
within-cohort variance). One existing script, `run_metrics_concat.py`, gains output-path
flags.

**Key design decision:** all heavy computation (anything that requires downloading a ~300 MB
expression matrix from S3) lives in `harmonization-metrics-calculation/gene_panel_analysis/`
and runs in the same `fl-metrics` pod as the rest of the compute pipeline; the
notebook consumes only pre-aggregated tables, except for §8, where it deliberately downloads
a handful of matrices so Daniil can *see the actual expression values* behind the
correlation numbers.

### Analysis scope

The benchmark contains 3,835 attempts, of which 1,512 are Shambhala cross-product variants
that are excluded from Article 1. Following the convention already used in
`harmonization_metrics_analysis_v3.ipynb`, the **default Shambhala variant
`shambhala_P0std_Q0std` is kept and renamed `20_shambhala`**; all other Shambhala variants
are dropped.

| Scope | attempts |
|---|---|
| All attempts in `metrics_comprehensive_260826.csv` | 3,835 |
| Shambhala cross-product variants (dropped) | 1,428 |
| `shambhala_P0std_Q0std` → `20_shambhala` (kept) | 84 |
| **Analysis scope (both post_rm)** | **2,407** |
| **Analysis scope, post0 only — the default compute run** | **1,204** |

---

## Background / reference data

### What Group L computes today

`compute_batch_metrics.py:1606 compute_group_l()`:

- For every cohort with at least `MIN_COHORT_N = 20` samples
  (`compute_batch_metrics.py:86`), and every resolved panel gene, the Spearman correlation
  between that gene's profile across the cohort's samples **before** harmonization
  (`exp/{strat}__{imp}__01_raw__post0.tsv.gz`, intersected to the job's own sample index)
  and **after** (`exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz`).
- Averaged over cohorts → `mk_rho_by_gene`; averaged over genes → `mk_rho_by_cohort`;
  grand mean → `mk_rho_mean_all_genes`.
- `run_metrics_concat.py` splits the two nested dicts into
  `marker_gene_correlations_long.csv` and `marker_cohort_correlations_long.csv`.

### Current data snapshot (verified 2026-08-27)

| Table | Shape | Notes |
|---|---|---|
| `metric_tables/metrics_comprehensive_260826.csv` | 3,835 × 314 | all `status == "ok"`; 15 `mk_` columns; 14 strats × 50 methods × 3 imps × 2 post_rm |
| `metric_tables/marker_gene_correlations_long_260826.csv` | 1,482,435 × 4 | 3,835 run_ids × 572 genes; 16,478 rows (1.1 %) have null ρ |
| `metric_tables/marker_cohort_correlations_long_260826.csv` | — | run_id × cohort ρ |
| `../harmonization-metrics-calculation/marker_gene_annotation.csv` | 834 × 10 | 633 unique genes, 63 gene_groups, 15 cell_types, 7 pathways, 15 housekeeping |
| `marker_gene_coverage_audit_260819.csv` | 4.9 KB | **stale** — built before the 2026-08-26 panel regeneration; per `(strat, imp)` pair only, not per attempt |

Of the 633 annotated genes, **572** are resolved in at least one expression matrix; 61 are
never present anywhere.

### Per-gene ρ distribution (all 3,835 attempts)

| statistic | value |
|---|---|
| mean | 0.850 |
| median | 0.931 |
| Q1 / Q3 | 0.818 / 0.998 |
| min | −0.654 |
| genes with mean ρ < 0.70 | 5 (`NOS2`, `ARG1`, `ACTN2`, `WNT2B`, `ATP8B3`) |

### Coverage audit — the decisive constraint

Genes present in *every* attempt of a scope:

| Scope | attempts | genes seen | in **all** attempts | ≥ 99 % | ≥ 95 % |
|---|---|---|---|---|---|
| All attempts | 3,835 | 572 | **0** | 9 | 140 |
| **Analysis scope** (non-Shambhala + `shambhala_P0std_Q0std`) | 2,407 | 572 | **0** | 5 | 150 |
| Analysis scope, post0 | 1,204 | 572 | **0** | 5 | 150 |
| **`01_raw__post0` only, 14 strategies × 3 imputations** | **42** | **572** | **193** | 193 | 193 |
| `C_rnaseq_only`, non-Shambhala | 174 | 572 | 133 | 133 | 304 |
| `A_confirmed_bad`, non-Shambhala | 172 | 567 | 7 | 7 | 196 |
| `G_affymetrix_only`, non-Shambhala | 160 | 498 | 194 | 194 | 302 |

Genes seen per strategy: `J_ff_only` 304, `G_affymetrix_only` 498, `F_microarray_only` /
`H_affymetrix_extended` 500, `I_rare_batches_removed` / `S0_no_removal` 509,
`A/B/E1/E2/E3` 567, `C_rnaseq_only` / `D_malignant_only` / `K_ffpe_only` 572.

`mk_n_panel_genes_used` per attempt: min 8, Q1 250, median 373, Q3 509, max 572.

> **Consequence for the plan.** Coverage measured over harmonized attempts is contaminated
> by the harmonizers themselves (a method that drops genes changes the denominator). The
> **primary coverage definition is therefore the `01_raw__post0` one**: a gene qualifies if
> it is present in all 42 unharmonized reference matrices — **193 genes**, independent of
> any harmonization method. The notebook still exposes a `COVERAGE_SCOPE` switch with
> `"raw_all_pairs"` (default, 193 genes), `"reference_strategy"` (`C_rnaseq_only`, **61**
> genes at 100 % once the default Shambhala variant is in scope; 133 without it) and
> `"global"` (≥95 % over the 2,407 attempts, 150 genes) so the sensitivity of every
> downstream result to this choice can be shown.

### Saturation audit — verified 2026-08-27

| Scope / gene set | n genes | p05 of ρ > 0.95 | median ρ > 0.99 | median ρ > 0.95 | median SD of ρ |
|---|---|---|---|---|---|
| Analysis scope, all genes | 572 | **0** | 333 | 564 | 0.273 |
| Analysis scope, 193-gene reference set | 193 | **0** | 109 | 189 | 0.270 |
| `C_rnaseq_only`, all genes | 572 | 0 | 122 | 453 | 0.239 |
| `C_rnaseq_only`, 193-gene reference set | 193 | 0 | 50 | 161 | 0.243 |

> **Consequence.** "Always highly correlated" must be defined on the **median** ρ, not on a
> low quantile: no gene has a 5th-percentile ρ above 0.95, because every gene is broken by
> *some* attempt. The saturation gate is therefore `SATURATION_MEDIAN_MAX` (default 0.99),
> which removes 109 of the 193 reference genes and leaves 84 for panel selection. The
> removed genes are not discarded silently — they get their own ordered quantile figure.

---

## Design decisions (pros / cons)

### D1 — Where to compute the gene × gene correlation matrices *(approved)*

| Option | Pros | Cons |
|---|---|---|
| **(chosen)** New worker + dispatcher in `gene_panel_analysis/`, per-attempt `.npz` on S3, separate aggregator | Reuses the proven `run_metrics_*` dispatcher pattern (memory guard, timeout, failed-job tracking, `--skip-if-exists`); resumable; each matrix is retrievable per project rule 2 | One more S3 prefix; ~540 MB of new objects |
| Extend `compute_batch_metrics.py` with a Group O | No new dispatcher | Would force a full re-run of the metrics pipeline and pollute `metrics_comprehensive.csv` with a 163 k-element payload |
| Compute in the notebook | Simple | Requires downloading 1,204 × ~300 MB into the notebook — impossible on the analysis host |

### D2 — Global vs within-cohort gene–gene correlation

Computed **both**, in the same worker:

- `global` — Spearman over all samples of the matrix. Contains batch structure; useful to
  show what harmonization does to apparent co-expression.
- `within_cohort` — Spearman inside each cohort with at least `MIN_COHORT_N = 20` samples,
  averaged over cohorts via Fisher z. This is the biologically meaningful redundancy measure
  and is the one that drives the orthogonal-panel selection.

Cost of both is one extra pass over a 572-column slice — negligible next to the download.

### D3 — Averaging correlations across attempts

Fisher z-transform, average, back-transform (Fisher 1921; Silver & Dunlap 1987). Averaging
raw r under-estimates the consensus. `r = ±1` is clipped to `±(1 − 1e-6)` before `arctanh`.
The aggregator also keeps the **SD of z per gene pair**, which answers "is this gene–gene
relationship stable across harmonizers, or an artefact of one method?".

### D4 — Where the zero-fraction / below-1 filter is evaluated

On the **unharmonized reference**, i.e. the `01_raw__post0` rows of the QC table — the same
principle as the coverage gate in D-coverage above. `01_raw` is itself an attempt in the
benchmark, so this comes free from the same worker: no separate reference pass. Harmonized
matrices are shifted and rescaled, so "fraction of samples with expression below 1" is only
interpretable on raw data. The QC table still stores the value for every attempt, so the
notebook can *show* how each method changes zero inflation.

All expression is `log2(x+1)`, so `frac_lt_1` means `value < 1.0` on the log2 scale
(≈ linear value < 1). Documented in the worker docstring and in the notebook cell.

### D5 — Selecting the minimal orthogonal panel

Four complementary selectors, all implemented in the notebook (they are cheap on a
193 × 193 or 572 × 572 matrix), compared side by side rather than one chosen blind:

1. **Hierarchical clustering + medoid** on `1 − |ρ_consensus|`, average linkage, cut height
   swept over a grid; one exemplar (medoid) gene per cluster. Uses
   `scipy.cluster.hierarchy` and `sns.clustermap` directly.
2. **Greedy redundancy pruning** — the `caret::findCorrelation` algorithm (Kuhn 2008): drop
   the member of the most-correlated pair with the higher mean |ρ| to the rest.
3. **mRMR** (Peng, Long & Ding 2005) — maximize relevance (per-gene discriminative power,
   see D6) minus mean redundancy to the already-selected set.
4. **Affinity propagation exemplars** (Frey & Dueck 2007, `sklearn.cluster.AffinityPropagation`)
   on the similarity matrix, as a cluster-number-free cross-check.

### D6 — What "relevance" means for a marker gene here

Not the mean ρ (it saturates near 1 — 333 of 572 genes have median ρ > 0.99). Relevance is
the **SD of ρ across attempts within the chosen scope**: a gene that scores ~1.0 for every
harmonizer carries no information about harmonizer quality. This is combined with hard
reliability gates (raw coverage, zero fraction, ICC, geNorm M) so the final panel is
*conservative and discriminative*, not merely variable.

### D7 — How a candidate panel is validated

**The reduced panel is not required to reproduce the full panel's ranking of attempts.** The
full-panel ranking is itself dominated by the 333 near-1 genes, so agreement with it would
reward exactly the saturation the reduction is meant to remove. The full-panel comparison is
still computed and plotted, but as a **descriptive** quantity only, never as an acceptance
criterion.

Acceptance rests on four intrinsic and external criteria:

| Criterion | Definition | Pass condition |
|---|---|---|
| **Precision** | SD of the panel score for one attempt under 1,000 bootstrap resamples of cohorts and of panel genes | bootstrap SD small relative to the between-attempt spread |
| **Discriminative signal-to-noise** | between-attempt variance of the panel score ÷ mean within-attempt bootstrap variance (an F-like ratio) | maximised; reported per panel size |
| **External agreement** | Spearman of the panel's attempt ranking against *independent* metrics — Group M `xb_rank_agree_ratio`, Group A `r2_RNA_BATCH`, Group B kBET / iLISI | positive and stable across metrics |
| **Structural quality** | raw-coverage 100 %, QC gates passed, max |ρ_consensus| within the panel below the redundancy threshold, ≥ 1 gene per represented cell type | hard gate |

### D8 — Notebook implementation convention

Two standing requirements that apply to every section:

1. **Every method is explained in the notebook itself.** Each analytical block opens with a
   markdown cell giving the method, its formula, what the axes mean, the published reference,
   and how to read a high vs low value — so a result can be judged without leaving the
   notebook.
2. **Stock plotting functions only.** Figures are built with `sns.clustermap`,
   `sns.scatterplot`, `sns.boxplot`, `sns.violinplot`, `sns.histplot`, `sns.ecdfplot`,
   `sns.heatmap`, `sns.lineplot`, `plt.subplots` and — for set overlaps — `supervenn` and
   `matplotlib_venn`. No custom plotting wrappers beyond `save_figure()`, so every cell can
   be copied and modified by hand. This replaces the hand-rolled ridgeline and UpSet figures
   of the first draft (`upsetplot` is not installed in `collagen_3_11`; `supervenn` and
   `matplotlib_venn` are).

---

## Literature basis for the noise / coherence section

Each row becomes a markdown cell in §11 with the formula and reading guide, per D8.

| Topic | Reference | Use in the notebook |
|---|---|---|
| Mean–variance dependence of log-expression | Law et al. 2014, *voom*, Genome Biol 15:R29 | LOWESS trend of per-gene SD vs mean; residual = excess noise |
| Overdispersion above technical noise | Brennecke et al. 2013, Nat Methods 10:1093 | CV² vs mean plot with fitted trend; genes above the trend are variable, below are flat |
| Dispersion estimation / shrinkage | Love, Huber & Anders 2014, DESeq2, Genome Biol 15:550 | Rationale for shrinking per-gene variance towards the trend before ranking |
| Reliability across grouping factors | Shrout & Fleiss 1979; McGraw & Wong 1996 (ICC) | `icc_cohort` = between-cohort variance / total; high ICC ⇒ gene is batch-driven, poor marker |
| Reference-gene stability | Vandesompele et al. 2002, geNorm, Genome Biol 3:research0034 | geNorm **M** statistic applied to marker genes as a conservativeness ranking |
| Housekeeping gene behaviour | Eisenberg & Levanon 2013, Trends Genet 29:569 | Sanity anchor for the 15 housekeeping controls |
| Signature internal consistency | Cronbach 1951, Psychometrika 16:297 | Cronbach's α per gene_group; α ≥ 0.7 = coherent signature |
| Module eigengene, kME | Langfelder & Horvath 2008, BMC Bioinformatics 9:559 | PC1 variance explained per gene set = coherence; low-kME genes are candidates for removal |
| Redundancy pruning | Kuhn 2008, J Stat Softw 28:5 (`findCorrelation`) | Selector 2 |
| Minimum redundancy, maximum relevance | Peng, Long & Ding 2005, IEEE TPAMI 27:1226 | Selector 3 |
| Exemplar selection | Frey & Dueck 2007, Science 315:972 | Selector 4 |
| Averaging correlations | Fisher 1921; Silver & Dunlap 1987, J Appl Psychol 72:146 | Fisher-z consensus (D3) |
| Signature instability under resampling | Ein-Dor et al. 2006, PNAS 103:5923 | Motivates the bootstrap precision criterion (D7) |
| Cluster-number stability | Monti et al. 2003, Mach Learn 52:91 | Choosing the cut height in selector 1 |
| Batch effects background | Leek et al. 2010, Nat Rev Genet 11:733 | Framing paragraph |

---

## Files to add — compute side (`harmonization-metrics-calculation/gene_panel_analysis/`)

All new compute code lives in **one new sub-directory** with its own README, so it can be
reviewed, rsynced and re-run independently of the metrics pipeline. It is copied to the same
`fl-metrics` pod as everything else — the existing sparse-checkout of
`harmonization-metrics-calculation/` picks it up automatically, and the README's commands are
all run from inside `gene_panel_analysis/`.

Every script starts with

```python
sys.path.insert(0, str(Path(__file__).parent.parent))   # marker_panels, compute_batch_metrics
```

so `marker_panels.resolve_panel()` and the `S3_BUCKET` / `S3_PREFIX` / `MIN_COHORT_N`
constants are shared with the metrics pipeline rather than duplicated.

### 1. `gene_panel_analysis/gene_panel_structure.py` (new library, ~450 lines)

Sibling of `compute_batch_metrics.py`: pure functions, no S3, no CLI, fully unit-testable.

**1a — Constants**

```python
from compute_batch_metrics import MIN_COHORT_N        # 20, single source of truth
FISHER_CLIP = 1.0 - 1e-6                              # clip |r| before arctanh
LOW_EXPRESSION_THRESHOLD = 1.0                        # log2 scale; see D4
```

**1b — Public API**

```python
def gene_gene_correlation(
    exp_df: pd.DataFrame, genes: list[str], method: str = "spearman"
) -> tuple[np.ndarray, list[str]]:
    """Gene x gene correlation over all samples. Returns (matrix, gene order)."""


def gene_gene_correlation_within_cohort(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    genes: list[str],
    min_cohort_n: int = MIN_COHORT_N,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Per-cohort correlation, Fisher-z averaged over cohorts.

    Returns (mean_r, n_cohorts_per_pair, gene order). Pairs that are constant in a
    cohort contribute nothing to that pair's count, so a gene flat in one cohort is
    not penalised globally.
    """


def gene_expression_qc(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    genes: list[str],
    low_threshold: float = LOW_EXPRESSION_THRESHOLD,
    min_cohort_n: int = MIN_COHORT_N,
) -> pd.DataFrame:
    """
    Per-gene expression quality statistics.

    Columns: gene, n_samples, n_cohorts_used, zero_frac, frac_lt_1, detection_frac,
    mean, median, sd, mad, iqr, p05, p95, cv, var_total, var_between_cohort,
    var_within_cohort, icc_cohort, genorm_m.
    """


def pack_upper_triangle(mat: np.ndarray) -> np.ndarray:
    """Flatten the strict upper triangle to float16 for compact storage."""


def unpack_upper_triangle(vec: np.ndarray, n: int) -> np.ndarray:
    """Rebuild a symmetric matrix with 1.0 on the diagonal."""


def fisher_z(r: np.ndarray) -> np.ndarray: ...
def inverse_fisher_z(z: np.ndarray) -> np.ndarray: ...
```

`genorm_m` implements the Vandesompele 2002 stability measure: for gene *j*, the SD over
all other genes *k* of the per-cohort log-ratio SD of *j*/*k*. Lower M = more stable.

**Why a new file rather than an addition to `compute_batch_metrics.py`:** that module is
2,390 lines and already the single largest file in the pipeline; the group functions there
all return `dict[str, float]` sidecar payloads, while these return matrices and DataFrames.
Keeping them apart keeps `compute_all_metrics()` untouched, so the existing 3,835 sidecars
stay valid.

### 2. `gene_panel_analysis/run_gene_corr_job.py` (new worker, ~350 lines)

Direct structural copy of `run_metrics_job.py` — same BLAS thread pinning preamble (the
`os.environ.setdefault` block at lines 45–55 must be copied verbatim, it is what fixed the
Group N timeouts), same `_download_df`, `_upload_json`, `_free_gb` / `_check_memory` guards.

Reads from S3:

```
exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz
prepared/{strat}__{imp}__ann.tsv.gz
```

Writes to S3:

```
gene_corr/{strat}__{imp}__{method}__post{0|1}_genecorr.npz
gene_qc/{strat}__{imp}__{method}__post{0|1}_geneqc.json
```

`.npz` payload (compressed):

| array | dtype | shape | meaning |
|---|---|---|---|
| `genes` | `<U16` | (G,) | gene order for both matrices |
| `r_global` | float16 | (G(G−1)/2,) | packed upper triangle, all samples |
| `r_within` | float16 | (G(G−1)/2,) | packed upper triangle, Fisher-z over cohorts |
| `n_within` | uint16 | (G(G−1)/2,) | cohorts contributing to each pair |
| `meta` | json str | — | strat, imp, method, post_rm, n_samples, n_cohorts_used |

CLI:

```bash
python run_gene_corr_job.py \
    --strat C_rnaseq_only --imp softimpute --method 10_mnn --post-rm False \
    --out-npz /tmp/genecorr.npz --out-qc-json /tmp/geneqc.json \
    [--panel-groups ...] [--corr-flavors global,within] \
    [--skip-if-exists] [--memory-limit-gb 6.0]
```

The panel is resolved exactly as Group L does — `resolve_panel(set(exp_df.columns), panel)`
imported from the parent directory's `marker_panels`, so alias fallbacks (`MS4A1`/`CD20`
etc.) behave identically and the gene sets are directly comparable with
`marker_gene_correlations_long.csv`.

### 3. `gene_panel_analysis/run_gene_corr_parallel.py` (new dispatcher, ~350 lines)

Copy of `run_metrics_parallel.py` with the metric-group arguments removed. Keeps
`_list_exp_files()` semantics (`--post-rm-filter`, `--only-with-metrics`, `--strats`,
`--imps`, `--methods`), `_wait_for_memory`, `_stream_forward`, the `ThreadPoolExecutor`
pool, and a `failed_gene_corr_{pod_name}.txt` tracking file (new name so it cannot collide
with the metrics run's file).

**New argument replacing `--skip-shambhala`:**

```python
parser.add_argument(
    "--shambhala-mode",
    choices=["all", "none", "default-only"],
    default="default-only",
    help="Which Shambhala variants to include. 'default-only' keeps only "
         "shambhala_P0std_Q0std (the variant renamed 20_shambhala in the analysis "
         "notebooks) and drops the 1,428 cross-product variants. (default: default-only)",
)
```

`--skip-shambhala` from the metrics dispatcher is **not** carried over: it would silently
drop `shambhala_P0std_Q0std`, which is in scope.

Recommended production invocation:

```bash
nohup python run_gene_corr_parallel.py \
    --only-with-metrics --shambhala-mode default-only --post-rm-filter post0 \
    --n-workers 20 --memory-limit-gb 8.0 --timeout-s 1200 \
    > /workspace/gene_corr.log 2>&1 &
```

→ **1,204 jobs**. A full run (`--post-rm-filter both`) is 2,407 jobs and is not the default;
see Side effects.

### 4. `gene_panel_analysis/run_gene_corr_concat.py` (new aggregator, ~300 lines)

Streams every `gene_corr/*.npz` and `gene_qc/*.json` from S3 and accumulates on the **union
gene index** (572 genes) without ever holding more than one job's matrix in memory:

```
sum_z[G, G], sum_z2[G, G], n[G, G]   # float64, 3 x 2.6 MB — trivial
```

**All outputs go into one user-specified folder with a user-specified date postfix**, so a
re-run never overwrites a previous snapshot:

```python
parser.add_argument("--out-dir", default=".",
                    help="Directory for every output table. (default: current directory)")
parser.add_argument("--date-tag", default=None,
                    help="Postfix appended to every output filename, e.g. 260827. "
                         "Default: today's date as YYMMDD.")
parser.add_argument("--no-s3", action="store_true",
                    help="Write local files only; skip the S3 upload.")
parser.add_argument("--by-strat", action="store_true",
                    help="Also write a per-strategy consensus matrix.")
parser.add_argument("--shambhala-mode", choices=["all", "none", "default-only"],
                    default="default-only")
```

| Output (`{out_dir}/…_{date_tag}.…`) | Content |
|---|---|
| `gene_gene_consensus_within_{tag}.csv.gz` | G × G, `tanh(sum_z / n)` — the consensus redundancy matrix |
| `gene_gene_consensus_global_{tag}.csv.gz` | same, global flavour |
| `gene_gene_consensus_sd_{tag}.csv.gz` | G × G, SD of z per pair — stability of each relationship |
| `gene_gene_consensus_n_{tag}.csv.gz` | G × G, attempts contributing per pair |
| `gene_gene_consensus_by_strat_{tag}/{strat}_within.csv.gz` | per-strategy consensus (`--by-strat`) |
| `gene_qc_long_{tag}.csv.gz` | run_id × gene × the 18 QC columns from `gene_expression_qc()` |

```bash
python run_gene_corr_concat.py --out-dir /workspace/gene_panel_tables --date-tag 260827 --by-strat
```

### 5. `gene_panel_analysis/build_marker_gene_coverage.py` (new, ~180 lines)

Rebuilds the stale `marker_gene_coverage_audit_260819.csv` at **attempt** resolution, from
the `genes/*.json` sidecars that already exist for all 3,835 attempts — no expression
download at all.

Output `marker_gene_coverage_by_attempt_{tag}.csv`:

| column | meaning |
|---|---|
| `gene` | HGNC symbol (or the alias actually matched) |
| `n_raw_pairs_present` / `frac_raw_pairs_present` | over the 42 `01_raw__post0` matrices |
| `present_in_all_raw_pairs` | **the primary gate** — `True` for the 193 reference genes |
| `n_attempts_present` / `frac_attempts_present` | over all 3,835 attempts |
| `n_attempts_present_scope` / `frac_attempts_present_scope` | over the 2,407-attempt analysis scope |
| `n_strats_present` / `n_strats_total` | strategy-level coverage |
| `present_in_{strat}` | 14 boolean columns, `True` if present in **every** attempt of that strategy |
| `frac_in_{strat}` | fraction of that strategy's attempts containing the gene |

```bash
python build_marker_gene_coverage.py --out-dir /workspace/gene_panel_tables --date-tag 260827
```

### 6. `gene_panel_analysis/test_mock_gene_structure.py` (new smoke test, ~250 lines)

Synthetic-data assertions in the style of `test_mock_metrics.py`, no S3:

- `gene_gene_correlation` on two perfectly correlated genes returns 1.0.
- `gene_gene_correlation_within_cohort` on data with a cohort-specific offset but identical
  within-cohort ranks returns 1.0, while the global flavour does not — proves the two
  flavours actually differ.
- Cohorts smaller than `MIN_COHORT_N = 20` are excluded, and their exclusion is reflected in
  `n_within`.
- `pack_upper_triangle` → `unpack_upper_triangle` round-trips to within float16 precision.
- `fisher_z(inverse_fisher_z(z)) == z`; `r = 1.0` does not produce `inf`.
- `gene_expression_qc`: a gene that is all zeros gives `zero_frac == 1.0`,
  `frac_lt_1 == 1.0`, `cv` is NaN not a division error.
- `icc_cohort` is 1.0 for a gene that is constant within each cohort but differs between
  cohorts, and ~0 for a gene with no cohort structure.
- `genorm_m` ranks a deliberately unstable gene above a stable one.

### 7. `gene_panel_analysis/README.md` (new, ~180 lines)

Standalone usage guide for the sub-directory, in the style of the parent `README.md`:

- What the sub-directory produces and why it is separate from the metrics pipeline.
- The analysis scope table (2,407 / 1,204 attempts) and the `--shambhala-mode` explanation.
- Ordered run book: rsync into the pod → `test_mock_gene_structure.py` → single-job check →
  `run_gene_corr_parallel.py` → `run_gene_corr_concat.py` → `build_marker_gene_coverage.py`
  → copy tables to `../../harmonization-metrics/metric_tables/`.
- The S3 prefixes written, with the storage estimate.
- Troubleshooting: memory guard, timeouts, resuming a partial run, stale `.npz` from an
  older panel version.
- An explicit note that these scripts are **not** a metric group: they add no column to
  `metrics_comprehensive.csv` and never touch `compute_all_metrics()`.

---

## Files to change — compute side

### 8. `harmonization-metrics-calculation/run_metrics_concat.py`

Currently only `--out-csv` is configurable; the three long tables are written to hardcoded
filenames next to it. Add per-output flags plus a shared date postfix, so a re-run can be
tagged without renaming files by hand.

**Before** (argparse block, ~line 164):

```python
    parser.add_argument("--out-csv", default=None)
    parser.add_argument("--s3-key", default=f"{S3_PREFIX}/metrics_comprehensive.csv")
```

**After**:

```python
    parser.add_argument(
        "--out-dir", default=None,
        help="Directory for every local output table. Combined with --date-tag it "
             "produces metrics_comprehensive_{tag}.csv, marker_gene_correlations_long_"
             "{tag}.csv, marker_cohort_correlations_long_{tag}.csv and "
             "prediction_folds_long_{tag}.csv. (default: no local output)",
    )
    parser.add_argument(
        "--date-tag", default=None,
        help="Postfix appended to every local output filename, e.g. 260827. "
             "Default: today's date as YYMMDD.",
    )
    parser.add_argument("--out-csv", default=None,
                        help="Override the metrics_comprehensive path. Wins over --out-dir.")
    parser.add_argument("--out-gene-long", default=None,
                        help="Override the marker_gene_correlations_long path.")
    parser.add_argument("--out-cohort-long", default=None,
                        help="Override the marker_cohort_correlations_long path.")
    parser.add_argument("--out-folds-long", default=None,
                        help="Override the prediction_folds_long path.")
    parser.add_argument("--s3-key", default=f"{S3_PREFIX}/metrics_comprehensive.csv")
```

**Before** (write block, ~line 233):

```python
    out_csv = Path(args.out_csv) if args.out_csv else None
    _write(df, s3, args.s3_key, out_csv)
    ...
        local = out_csv.parent / filename if out_csv else None
```

**After**: a small `_resolve_out_path(explicit, stem, args)` helper returns
`Path(args.out_dir) / f"{stem}_{tag}.csv"` when `--out-dir` is given, the explicit override
when one is passed, and `None` otherwise. Each of the four writes calls it with its own
stem. S3 keys are unchanged (they stay undated, as they are the "latest" pointers).

Docstring header updated to show the new usage:

```bash
python run_metrics_concat.py --out-dir ../harmonization-metrics/metric_tables --date-tag 260827
```

### 9. `harmonization-metrics-calculation/CLAUDE.md`

**9a — file roles table**, one new row for the sub-directory:

```markdown
| `gene_panel_analysis/` | Marker-panel deep-analysis sub-pipeline (own `README.md`): gene x gene correlation matrices, per-gene expression QC, per-attempt gene coverage. Runs in the same pod; produces no `metrics_comprehensive.csv` column |
```

**9b — Commands section**, new block after the blind-check block:

````markdown
```bash
# ── Marker panel deep analysis (see gene_panel_analysis/README.md) ──
cd gene_panel_analysis
# 1,204 jobs = non-Shambhala + shambhala_P0std_Q0std, post0 only.
nohup python run_gene_corr_parallel.py \
    --only-with-metrics --shambhala-mode default-only --post-rm-filter post0 \
    --n-workers 20 --memory-limit-gb 8.0 --timeout-s 1200 \
    > /workspace/gene_corr.log 2>&1 &

python run_gene_corr_concat.py --out-dir /workspace/gene_panel_tables --date-tag 260827 --by-strat
python build_marker_gene_coverage.py --out-dir /workspace/gene_panel_tables --date-tag 260827
```
````

Also update the `run_metrics_concat.py` examples in the same section to the new flags:

```bash
python run_metrics_concat.py --out-dir ../harmonization-metrics/metric_tables --date-tag 260827
```

**9c — S3 layout block**, add:

```
├── gene_corr/{strat}__{imp}__{method}__post{0|1}_genecorr.npz  ← gene x gene correlation
├── gene_qc/{strat}__{imp}__{method}__post{0|1}_geneqc.json     ← per-gene expression QC
├── gene_gene_consensus_{within,global,sd,n}.csv.gz             ← Fisher-z consensus
├── gene_qc_long.csv.gz                                         ← aggregated QC
└── failed_gene_corr_{pod_name}.txt                             ← failed-job tracking
```

**9d — "What is NOT here" table**, add `marker_gene_deep_analysis.ipynb` to the
`../harmonization-metrics/` row.

**9e** — a paragraph under the metric groups table stating that `gene_panel_analysis/` is
**not** a metric group: it produces no `metrics_comprehensive.csv` columns and does not touch
`compute_all_metrics()`, so the existing 3,835 sidecars remain valid.

### 10. `harmonization-metrics-calculation/README.md`

Add a short section pointing at `gene_panel_analysis/README.md` and noting that the
sub-directory is included in the existing sparse checkout and rsync, so no launch-procedure
change is needed.

---

## Files to add — analysis side (`harmonization-metrics/`)

### 11. `create_marker_gene_deep_analysis_notebook.py` (new generator, ~2,000 lines)

Generator in the style of `create_correlation_prediction_notebook.py`: `md()` / `code()`
helpers appending to a `CELLS` list, written out with `nbformat`. Dated inputs live in
module-level constants at the top:

```python
OUTPUT   = Path(__file__).parent / "marker_gene_deep_analysis.ipynb"
DATE_TAG = "260826"          # metrics / long tables
PANEL_TAG = "260827"         # gene_panel_analysis outputs
FIG_DIR  = "../figures_for_article/current_figures_tables_for_article_260819"
```

The generated notebook is **self-contained**: it imports nothing from this repository,
manipulates no `sys.path`, does **not** import `marker_panels`, and names every input file as
a constant in its first cell.

### 12. `marker_gene_deep_analysis.ipynb` (generated, ~140 cells)

Per D8, every analytical block opens with a markdown cell explaining the method and how to
read it, and every figure uses a stock seaborn/matplotlib call.

#### §1 — Setup, paths, palettes

- rcParams block identical to the blind-check notebook (`FONT_SIZE = 7.5`,
  `pdf.fonttype = "truetype"`, `svg.fonttype = "none"`, `figure.dpi = 200`,
  `sns.set_style("ticks")`), and `save_figure()` — the only custom helper in the notebook.
- **Input constants**, every file named once:

```python
DATE_TAG        = "260826"
PANEL_TAG       = "260827"
METRIC_TABLES   = Path("metric_tables")
METRICS_CSV     = METRIC_TABLES / f"metrics_comprehensive_{DATE_TAG}.csv"
GENE_LONG_CSV   = METRIC_TABLES / f"marker_gene_correlations_long_{DATE_TAG}.csv"
COHORT_LONG_CSV = METRIC_TABLES / f"marker_cohort_correlations_long_{DATE_TAG}.csv"
MARKER_ANN_CSV  = Path("../harmonization-metrics-calculation/marker_gene_annotation.csv")
COVERAGE_CSV    = METRIC_TABLES / f"marker_gene_coverage_by_attempt_{PANEL_TAG}.csv"
GENE_QC_CSV     = METRIC_TABLES / f"gene_qc_long_{PANEL_TAG}.csv.gz"
CONSENSUS_WITHIN_CSV = METRIC_TABLES / f"gene_gene_consensus_within_{PANEL_TAG}.csv.gz"
CONSENSUS_GLOBAL_CSV = METRIC_TABLES / f"gene_gene_consensus_global_{PANEL_TAG}.csv.gz"
CONSENSUS_SD_CSV     = METRIC_TABLES / f"gene_gene_consensus_sd_{PANEL_TAG}.csv.gz"
S3_BUCKET = "$FL_S3_BUCKET"
S3_PREFIX = "FL_batch_correction"
EXP_CACHE_DIR = Path("/tmp/fl_exp_cache")     # §8 downloads land here

# Analysis scope: drop the Shambhala cross-product, keep the default variant as 20_shambhala.
SHAMBHALA_DEFAULT = "shambhala_P0std_Q0std"
SHAMBHALA_RENAMED = "20_shambhala"
```

- **Attempt palettes — copied verbatim from `harmonization_metrics_analysis_v3.ipynb`**
  (cells 4 and 34), so figures here are colour-identical to Figures 3–5: `HARSHNESS_PAL`,
  `HARSHNESS_LEVEL_MAP` (39 methods; `20_shambhala` → `"high"`), `strat_pal` (14 explicit
  entries incl. `J_ff_only` `#7ecbc4`, `K_ffpe_only` `#f2c27f`), `imp_pal`
  (`strict #2979ae`, `knn #982d22`, `softimpute #713689`), `method_pal` (tab20 + tab20b with
  the `_boost_saturation(delta=0.15)` step), `post_rm_pal`
  (`{False: "#CCCCCC", True: "#333333"}`), `annot_pal`, `make_legend_patches()`.

- **Cell-type palette — reuses v3's `lymphoma_ontogeny_palette`** (the
  `Diagnosis_cell_type_unified` palette, v3 cell 117) wherever the marker annotation's
  `cell_type` maps onto a B-cell ontogeny stage; the nine microenvironment populations, which
  have no counterpart there, are assigned by biology (adaptive lymphoid = blues/purple,
  myeloid = orange, stroma/vasculature/FDC = earth tones and pink):

| `cell_type` | colour | source |
|---|---|---|
| `centroblast (DZ)` | `#41ab5d` | v3 `Centroblast` |
| `centrocyte (LZ)` | `#a1d99b` | v3 `Centrocyte` |
| `germinal centre B` | `#006d2c` | v3 `GC` |
| `B cell` | `lawngreen` | v3 `B_cells` |
| `plasma cell` | `grey` | v3 `Plasma` |
| `memory precursor` | `#00ced1` | v3 `Memory` |
| `CD4 T` | `#4A6FE3` | new — adaptive lymphoid |
| `CD8 T` | `#1F3B99` | new — adaptive lymphoid |
| `Treg` | `#8FA9F0` | new — adaptive lymphoid |
| `NK` | `#6A3D9A` | new — innate lymphoid |
| `macrophage` | `#FF7F00` | new — myeloid |
| `follicular dendritic` | `#E6AB02` | new — antigen-presenting stroma |
| `stromal/fibroblast` | `#8C510A` | new — stroma |
| `endothelial` | `#E7298A` | new — vasculature |
| `none` | `#EEEEEE` | neutral |

- **Gene-set palette** — 63 `gene_group` values ordered by `source_article` so signatures
  from the same publication get neighbouring hues, built from tab20 + tab20b + tab20c plus
  Set2 with the same `_boost_saturation` step used for `method_pal` in v3.
- `pathway_pal` (7 pathways, `Dark2`) and `tme_subtype_pal` (`Set2`) as secondary tracks.

#### §2 — Load and assemble

- `df_metrics` (3,835 × 314) with `run_id` index built exactly as v3 does; parse
  `strat` / `imp` / `method` / `post_rm`; **apply the analysis scope**: drop Shambhala
  variants other than `shambhala_P0std_Q0std`, rename that one to `20_shambhala`; attach
  `harshness_level`. Prints the 3,835 → 2,407 reduction.
- `rho_long` → `rho_wide` (genes × attempts) restricted to the same scope.
- `ann` = marker annotation collapsed to one row per gene with list-valued
  `gene_groups` / `cell_types` plus a `primary_group` (the group with the fewest members)
  used for single-colour row annotation.
- `coverage`, `gene_qc`, the three consensus matrices.
- A printed integrity block: shapes, gene counts, attempts, NaN fraction, and an assertion
  that every gene in `rho_wide` exists in `ann`.

#### §3 — Gene set structure: Venn, supervenn, Jaccard

- Fig `l0_supervenn_top_sets` — `supervenn` over the 12 largest gene sets, showing exactly
  which genes are shared and how much of each signature is unique.
- Fig `l0_venn_sources` — `matplotlib_venn.venn3` over the three publication sources
  (Kotlov 2021, Holmes 2020, Dybkaer 2015) and, separately, `venn2` for the GC-B vs TME
  split.
- Fig `l0_jaccard_clustermap` — 63 × 63 Jaccard index between gene sets via
  `sns.clustermap`, row/col colours = `gene_group_pal` + `pathway_pal`. Blocks here are the
  signature families whose genes must not all enter the final panel.
- Fig `l0_gene_multiplicity` — `sns.histplot` of how many sets each gene belongs to;
  the multi-set genes are the ones the unweighted panel mean over-weights.
- Table `T0_gene_set_overlap.csv`.

#### §4 — Coverage analysis and the coverage filter

- `COVERAGE_SCOPE` constant with three documented settings — `"raw_all_pairs"` (default,
  193 genes, the 42 `01_raw__post0` matrices), `"reference_strategy"` (`C_rnaseq_only`),
  `"global"` (≥ `COVERAGE_MIN_FRAC` over the 2,407 attempts) — and
  `COVERAGE_MIN_FRAC = 1.0`.
- Fig `l1_coverage_histogram` — `sns.histplot` of `frac_attempts_present_scope` and
  `frac_raw_pairs_present` side by side, with the 95 / 99 / 100 % gates as `axvline`s.
- Fig `l1_coverage_by_strategy_heatmap` — `sns.clustermap` of genes × 14 strategies
  (`frac_in_{strat}`), row colours = gene set + cell type. Makes the platform-driven
  coverage blocks visible at a glance.
- Fig `l1_coverage_raw_vs_attempts` — `sns.scatterplot` of raw-pair coverage vs attempt
  coverage, coloured by cell type; shows how much apparent gene loss is caused by the
  harmonizers rather than by the platforms.
- Fig `l1_coverage_vs_rho` — `sns.scatterplot` of coverage vs mean ρ, point size = SD of ρ,
  hue = cell type.
- Fig `l1_coverage_gate_sweep` — `sns.lineplot` of surviving gene count as the threshold is
  swept 0.5 → 1.0, one line per scope. Tells Daniil what a given threshold actually costs.
- Table `T1_coverage_gate.csv`.

#### §5 — Expression quality filter

Evaluated on the `01_raw__post0` rows of `gene_qc_long` (D4).

- `ZERO_FRAC_MAX = 0.20`, `LOW_FRAC_MAX = 0.50`, `MIN_DETECTION_FRAC = 0.80` as named
  constants at the top of the section, each with a one-line justification comment.
- Fig `l2_zero_fraction_ecdf` — `sns.ecdfplot` of `zero_frac` and `frac_lt_1` with the
  thresholds marked.
- Fig `l2_qc_pairplot` — `sns.pairplot` over `zero_frac`, `frac_lt_1`, `mean`, `sd`, hue =
  housekeeping vs marker.
- Fig `l2_zero_fraction_by_strategy` — `sns.boxplot` per strategy: how much of the zero
  inflation is platform-driven.
- Fig `l2_zero_fraction_before_after` — `sns.boxplot` of `zero_frac` per method against the
  `01_raw` baseline; which methods manufacture or destroy zeros.
- Fig `l2_qc_gate_sweep` — `sns.heatmap` of surviving gene counts over a 2-D threshold grid.
- Table `T2_qc_gate.csv`.

#### §6 — Saturation: separating the permanently-high genes

- `SATURATION_MEDIAN_MAX = 0.99` as a named constant, with the audit numbers in the markdown
  cell (333 / 572 genes globally, 109 / 193 in the reference set) and the explanation that
  the gate is on the **median**, since no gene has a 5th-percentile ρ above 0.95.
- Fig `l3_gene_quantile_ordered` — the ordered per-gene quantile plot: genes on x sorted by
  median ρ, `plt.fill_between` for the p05–p95 and p25–p75 bands, `sns.lineplot` for the
  median, with the saturation threshold as an `axhline`. The single figure that shows which
  genes are informative and which are not.
- Fig `l3_saturated_genes_barplot` — `sns.barplot` of the removed (median ρ > 0.99) genes,
  ordered, coloured by cell type, so the excluded biology is explicit.
- Fig `l3_retained_vs_removed_composition` — `sns.countplot` of gene sets and cell types in
  the retained vs removed groups; checks that the gate does not delete an entire cell type.
- Table `T3_saturation_split.csv` — every gene with its ρ quantiles and its gate outcome.

#### §7 — Distributions, quantiles, moments of ρ

- Fig `l4_rho_distribution_overall` — `sns.histplot` + `sns.ecdfplot` of all ρ values in
  scope, with the saturation shoulder annotated.
- Fig `l4_rho_by_gene_set` — `sns.violinplot` (with `sns.boxplot` inset) per gene_group,
  ordered by median, coloured by `gene_group_pal`.
- Fig `l4_rho_by_cell_type` — the same by cell type, using the v3-derived `cell_type_pal`,
  housekeeping shown as a separate reference band.
- Fig `l4_rho_quantile_heatmap` — `sns.clustermap` of genes × {mean, median, p05, p25, p75,
  p95, min, IQR, SD}, z-scored per column, row colours = gene set + cell type.
- Fig `l4_rho_sd_vs_median` — the discriminative-power plot (D6): median ρ on x, SD of ρ on
  y, `sns.scatterplot`, the 25 most discriminative genes labelled with `ax.annotate`.
- Fig `l4_rho_by_attempt_facets` — `sns.catplot` of per-gene ρ faceted by strategy and by
  imputation, coloured with `strat_pal` / `imp_pal`.
- Table `T4_per_gene_rho_summary.csv` — one row per gene: all quantiles, coverage, QC, gene
  sets, cell types, gate outcomes.

#### §8 — Master clustermap and touching the data

**8a — Master clustermap: genes × attempts**

- `sns.clustermap` of the gate-filtered `rho_wide`; NaN masked; `method="average"`,
  correlation distance on columns.
- **Column colours (attempts)** — 5 tracks from the v3 palettes: `strat_pal`, `imp_pal`,
  `method_pal`, `post_rm_pal`, `HARSHNESS_PAL`.
- **Row colours (genes)** — 5 tracks: `gene_group_pal` (primary group), `cell_type_pal`,
  `pathway_pal`, housekeeping black/white, and a continuous raw-coverage track (`Greys`).
- Figures: `l5_clustermap_genes_by_attempts` (full),
  `l5_clustermap_genes_by_method_median` (attempts collapsed to a per-method median — 40
  columns, legible in print, destined for the supplementary file),
  `l5_clustermap_reference_set` (the 193 raw-covered genes only).
- Two legend panels rendered separately with `make_legend_patches`, because 63 gene-set
  entries will not fit beside the map.

**8b — Raw vs harmonized scatterplots**

Self-contained S3 loaders (boto3 → `gzip` → `pd.read_csv(sep="\t", index_col=0)`, key
patterns written out in the cell rather than imported), disk-cached under `EXP_CACHE_DIR`:

```python
def load_exp(strat, imp, method, post_rm) -> pd.DataFrame: ...
def load_ann(strat, imp) -> pd.DataFrame: ...
```

`RUN_SCATTER_SECTION = True` and `SCATTER_ATTEMPTS` — a short explicit list of run_ids,
defaulting to the decision-tree winners plus one deliberate failure:
`C_rnaseq_only__softimpute__04_sva__post0`, `C_rnaseq_only__softimpute__10_mnn__post0`,
`C_rnaseq_only__softimpute__16_fsqn_r__post0`, `G_affymetrix_only__softimpute__16_fsqn_r__post0`.

- Fig `l6_scatter_gene_cohort_grid` — `sns.relplot` over genes × cohorts, raw log2 on x,
  harmonized on y, identity line, Spearman ρ printed per panel. Genes: 3 high-ρ + 3 mid-ρ +
  3 low-ρ, so the visual range of the metric is covered.
- Fig `l6_scatter_all_cohorts_one_gene` — one gene, all cohorts, `sns.scatterplot` with
  `hue=cohort` and `sns.regplot` per cohort. Shows directly why a gene with high global
  scatter can still have ρ ≈ 1 within cohorts.
- Fig `l6_scatter_method_panel` — one gene, one cohort, one panel per attempt in
  `SCATTER_ATTEMPTS`: a like-for-like comparison of what each harmonizer did to the same
  numbers.
- Fig `l6_density_before_after` — `sns.kdeplot` of per-cohort expression before and after,
  warm = harmonized, cold = raw, per the project palette rule.
- Fig `l6_worst_genes_gallery` — the 9 genes with the lowest median ρ, each raw vs
  harmonized in its worst cohort. Diagnostic: are the low-ρ genes broken, or simply flat?

#### §9 — Gene–gene correlation structure

- Fig `l7_consensus_clustermap_within` — `sns.clustermap` of the consensus within-cohort
  matrix, `RdBu_r` centred at 0, row **and** column colours = `gene_group_pal` +
  `cell_type_pal`. The figure that answers "how much redundancy is in the panel".
- Fig `l7_consensus_clustermap_global` — the same for the global flavour; the contrast
  separates biological co-expression from batch structure.
- Fig `l7_consensus_sd_clustermap` — SD of Fisher z per pair: which gene–gene relationships
  are method-dependent.
- Fig `l7_per_attempt_examples` — 2 × 3 grid of `sns.heatmap` panels for single attempts
  (raw, SVA, MNN, FSQN R, quantile, rank) on a fixed gene order, so the structure can be
  watched changing.
- Fig `l7_within_vs_between_set_correlation` — `sns.kdeplot` of |ρ| for gene pairs inside
  the same gene_group vs across groups; a coherent signature sits clearly to the right.
- Fig `l7_redundancy_supervenn` — `supervenn` over the redundancy clusters found at
  |ρ| ≥ 0.8, showing which signatures they draw from.
- Table `T5_gene_pair_redundancy.csv` — every pair with |ρ| ≥ 0.7, with SD and n.

#### §10 — Minimal orthogonal panel selection

All four selectors from D5, run over the gate-filtered gene set (raw coverage → QC →
saturation → 84 genes by default), each preceded by a markdown cell describing the algorithm
and its reference.

- Fig `l8_dendrogram_cut_sweep` — `sns.lineplot` of cluster count and retained |ρ| as the
  cut height sweeps, with a Monti-style stability curve from 200 bootstrap resamples.
- Fig `l8_selector_overlap_supervenn` — `supervenn` over the four selectors' outputs.
- Fig `l8_selected_panel_clustermap` — `sns.clustermap` of the consensus matrix restricted
  to the selected genes, demonstrating near-block-diagonality.
- Fig `l8_panel_size_vs_signal` — **the decision plot (D7)**: panel size on x, and three
  curves — bootstrap precision, discriminative signal-to-noise, and external agreement with
  Group M / Group A — with CI ribbons and a marked knee. The full-panel agreement is drawn
  as a dashed *descriptive* line, explicitly labelled "not an acceptance criterion".
- Table `T6_candidate_panels.csv` — one row per candidate panel: n_genes, selector,
  bootstrap SD, signal-to-noise, external agreement with each independent metric, cell types
  covered, gene sets covered, max within-panel |ρ|.
- Table `T7_recommended_panel.csv` — the recommended minimal panel with, per gene: raw
  coverage, QC stats, median/SD ρ, geNorm M, ICC, cluster id, the genes it represents, and a
  one-line reason for inclusion.

#### §11 — Variance, noise, coherence (literature-grounded)

Each figure is preceded by its markdown explanation, per D8.

- Fig `l9_mean_variance_trend` — `sns.scatterplot` of per-gene SD vs mean with a LOWESS
  trend (`sns.regplot(lowess=True)`), voom-style; hue = cell type, housekeeping marked.
- Fig `l9_cv2_vs_mean` — Brennecke-style CV² vs mean on log axes with the fitted trend.
- Fig `l9_icc_distribution` — `sns.barplot` of ICC per gene, ordered, coloured by gene set;
  high-ICC genes flagged as batch-driven and therefore poor markers.
- Fig `l9_genorm_stability` — `sns.boxplot` of geNorm M, marker genes vs the 15 housekeeping
  controls; a marker with M below the housekeeping median is exceptionally stable.
- Fig `l9_signature_coherence` — per gene_group: Cronbach's α, PC1 variance explained, mean
  intra-set |ρ|, n genes; `sns.barplot` plus a `sns.scatterplot` of α vs PC1 %.
- Fig `l9_kme_by_gene` — each gene's correlation to its own set's eigengene (kME); low-kME
  genes are the ones to drop from their signature.
- Fig `l9_noise_vs_rho` — the synthesis plot: excess noise on x, median ρ on y, SD of ρ as
  point size, hue = survives the gates. Shows whether low-ρ genes are simply noisy.
- Table `T8_gene_noise_coherence.csv`.

#### §12 — Recommendation and export

- A markdown cell summarising how many genes survive each gate, which selector wins on the
  D7 criteria, and the recommended panel size.
- `T9_supplementary_marker_panel_selection.csv` — the full audit trail, one row per gene,
  every statistic and every gate outcome, formatted for a supplementary file.
- A generated snippet showing how the selected panel would be fed back into the compute
  pipeline (`--panel-groups` accepts group names; an arbitrary gene list would need a new
  `--panel-file` argument — flagged in Side effects, **not** implemented in this plan).

---

## Files to change — project documentation

### 13. `harmonization-metrics/CLAUDE.md`

**13a — file roles table**, new rows:

```markdown
| `marker_gene_deep_analysis.ipynb` | **Marker panel deep-dive notebook**: gene-set overlap (Venn/supervenn), raw-coverage and expression-quality gates, saturation split, gene x gene consensus correlation, minimal orthogonal panel selection, noise/coherence analysis |
| `create_marker_gene_deep_analysis_notebook.py` | Generator for the notebook above; regenerate rather than hand-edit |
| `marker_gene_deep_analysis_plan_260827.md` | This plan |
| `metric_tables/gene_qc_long_260827.csv.gz` | Per-attempt per-gene expression QC from `gene_panel_analysis/run_gene_corr_concat.py` |
| `metric_tables/gene_gene_consensus_{within,global,sd}_260827.csv.gz` | Fisher-z consensus gene x gene correlation matrices |
| `metric_tables/marker_gene_coverage_by_attempt_260827.csv` | Per-gene coverage over the 42 `01_raw__post0` matrices and over all attempts; supersedes `marker_gene_coverage_audit_260819.csv` |
```

**13b — Commands block**, add:

```bash
# Rebuild the marker gene deep-analysis notebook
python create_marker_gene_deep_analysis_notebook.py
```

**13c** — mark `marker_gene_coverage_audit_260819.csv` as superseded in its existing row (it
predates the 2026-08-26 panel regeneration and is per `(strat, imp)`, not per attempt).

### 14. `FL_harmonization/CLAUDE.md`

**14a — Key Files table**, two new rows after the
`harmonization-metrics/correlation_prediction_metrics_analysis.ipynb` row:

```markdown
| `harmonization-metrics/marker_gene_deep_analysis.ipynb` | Marker panel deep-dive: gene-level correlation structure, coverage/QC/saturation gates, minimal orthogonal panel selection |
| `harmonization-metrics-calculation/gene_panel_analysis/` | Sub-pipeline for the above: gene x gene correlation + per-gene QC (1,204 jobs); own README |
```

**14b — "Next steps — Article 1"**, new checklist item after the blind-check figures item:

```markdown
- [ ] **Marker panel reduction**: run `gene_panel_analysis/run_gene_corr_parallel.py`, then
      `marker_gene_deep_analysis.ipynb` → recommended minimal orthogonal gene panel for the
      Group L metric (plan: `harmonization-metrics/marker_gene_deep_analysis_plan_260827.md`)
```

### 15. `harmonization-metrics-calculation/requirements.txt`

No change required — `numpy`, `pandas`, `scipy`, `scikit-learn`, `statsmodels`, `boto3`,
`psutil` cover everything in `gene_panel_analysis/`. `supervenn`, `matplotlib_venn` and
`networkx` are used **only** in the notebook and are already installed in
`~/venvs/collagen_3_11`; they never run in the pod, so the ConfigMap in
`k8s/pod-metrics.yaml` also stays unchanged.

---

## Files that do NOT need to change

| File | Why |
|---|---|
| `compute_batch_metrics.py` | Group L stays exactly as it is; the new work is additive and lives in `gene_panel_analysis/gene_panel_structure.py`. Changing Group L would invalidate all 3,835 sidecars |
| `run_metrics_job.py`, `run_metrics_parallel.py` | The new pipeline is a parallel track with its own worker and dispatcher; the metrics run is untouched |
| `marker_panels.py` | The loader API (`panel_genes`, `resolve_panel`, `housekeeping_genes`) is already sufficient; the new worker imports it unchanged |
| `marker_gene_annotation.csv`, `build_marker_gene_annotation.py` | The panel definition is the *input* to this analysis; changing it is the possible *outcome*, in a follow-up plan |
| `test_mock_metrics.py` | New tests go into `gene_panel_analysis/test_mock_gene_structure.py` so the 169 existing assertions stay independent |
| `k8s/pod-metrics.yaml` | No new dependencies |
| `figures_for_article/figures_helpers.py` | The new notebook is self-contained and imports nothing from it; `_BLIND_CHECK_PREFIXES` needs no new entry because no new `metrics_comprehensive.csv` column is created |
| `create_correlation_prediction_notebook.py` / `correlation_prediction_metrics_analysis.ipynb` | Separate deliverable; the deep-dive notebook does not replace it |
| `harmonization-scripts/` | No harmonization output changes |

---

## Side effects and caveats

1. **"Genes covered by all attempts" returns 0 genes at global scope.** Verified over the
   2,407-attempt analysis scope. The usable definition is the raw-reference one — genes
   present in all 42 `01_raw__post0` matrices, **193 genes** — and it is the notebook
   default. Any statement in the manuscript about a "universally covered panel" must name
   the scope it was measured in.

2. **Group L saturates on the median, not on the tail.** 333 of 572 genes have median
   ρ > 0.99, but **no** gene has a 5th-percentile ρ above 0.95 — every gene is broken by
   some attempt. Selecting genes by high mean ρ would select the least informative ones;
   selection is driven by SD of ρ (D6) and gated by the median (§6). This must be stated in
   the notebook text and in any manuscript sub-chapter.

3. **The reduced panel deliberately will not reproduce the full-panel ranking**, and is not
   asked to (D7). Anyone comparing the two rankings later must read the D7 table first, or
   they will mistake a designed difference for an error.

4. **New S3 objects.** 1,204 `.npz` (~330 KB each) + 1,204 `.json` (~120 KB each) ≈
   **540 MB** under two new prefixes. A full run (2,407 jobs, both post_rm) would be
   ~1.1 GB. Not large by this bucket's standards, but new prefixes to clean up if the panel
   definition changes.

5. **Compute cost.** Each job re-downloads the same ~300 MB expression matrix the metrics run
   already downloaded — there is no local cache of harmonized matrices, only of the `01_raw`
   references. At 20 workers the 1,204-job run is bounded by S3 bandwidth, roughly 2–4 h.
   Run it on the metrics pod while it is already up.

6. **float16 storage** caps correlation precision at ~3 decimal digits. Adequate for
   clustering and redundancy thresholds; the Fisher-z consensus accumulates in float64, so
   the consensus itself is not degraded beyond the per-job quantisation.

7. **Gene order differs per attempt.** Each `.npz` carries its own `genes` array; the
   aggregator maps every job onto the union index. Any code reading a single `.npz` must use
   its own `genes` array and never assume the union order.

8. **`run_metrics_concat.py` behaviour change.** The new `--out-dir` / `--date-tag` flags are
   additive and default to the current behaviour (no local output unless a path is given), so
   existing invocations keep working. S3 keys stay undated — they remain the "latest"
   pointers that `figures_helpers.load_metrics_data()` and the pod README rely on.

9. **The stale coverage audit.** `marker_gene_coverage_audit_260819.csv` was built before the
   2026-08-26 panel regeneration and reports 178/325/45 genes over 42 `(strat, imp)` pairs.
   It is superseded by `marker_gene_coverage_by_attempt_260827.csv`. The blind-check notebook
   still reads the old file via `COVERAGE_AUDIT_CSV`; that reference is left alone here —
   changing it would alter published Supplementary File 5 numbers. Flagged for a separate
   decision.

10. **Acting on the result requires one more change.** If a reduced gene panel is adopted,
    `run_metrics_job.py` currently accepts only `--panel-groups` (gene *group* names). Using
    an arbitrary gene list needs a new `--panel-file` argument and a Group L re-run. That is
    deliberately **out of scope** here, so this analysis cannot silently change any published
    metric.

11. **Notebook size.** §8–§9 produce several large clustermaps. With outputs stored the
    `.ipynb` would exceed the 100 MB GitHub limit, so the generator writes the notebook with
    empty outputs and the project's `nbstripout` config keeps it that way; every figure is
    persisted to `FIG_DIR` as PDF/SVG/PNG instead.

12. **§8b downloads run on the analysis host.** Four attempts × ~300 MB + 4 raw references
    ≈ 2.5 GB, disk-cached under `/tmp/fl_exp_cache`. Cells are ordered so the cache is
    populated once; the section is skippable via `RUN_SCATTER_SECTION = False`.

---

## Verification commands

```bash
source ~/venvs/collagen_3_11/bin/activate
cd ~/FL_harmonization/harmonization-metrics-calculation

# 1. Existing pipeline must still pass unchanged
python test_mock_metrics.py

# 2. New library and its tests
cd gene_panel_analysis
python test_mock_gene_structure.py
python -c "
from gene_panel_structure import MIN_COHORT_N, LOW_EXPRESSION_THRESHOLD
print('MIN_COHORT_N', MIN_COHORT_N); assert MIN_COHORT_N == 20"

# 3. One real job end to end (needs S3 credentials)
python run_gene_corr_job.py \
    --strat C_rnaseq_only --imp softimpute --method 10_mnn --post-rm False \
    --out-npz /tmp/genecorr.npz --out-qc-json /tmp/geneqc.json

python - <<'PY'
import numpy as np, json
d = np.load("/tmp/genecorr.npz", allow_pickle=True)
G = len(d["genes"])
print("genes", G, "packed", d["r_within"].shape, "expected", G*(G-1)//2)
print("meta", json.loads(str(d["meta"])))
qc = json.load(open("/tmp/geneqc.json"))
print("qc genes", len(qc["genes"]), "keys", sorted(qc["genes"][0]))
PY

# 4. Dispatcher job count must be 1,204 (dry run)
python run_gene_corr_parallel.py --only-with-metrics --shambhala-mode default-only \
    --post-rm-filter post0 --dry-run

# 5. Coverage rebuild (no expression download; fast). Must report 193 reference genes.
python build_marker_gene_coverage.py --out-dir /tmp --date-tag 260827
python -c "
import pandas as pd; d=pd.read_csv('/tmp/marker_gene_coverage_by_attempt_260827.csv')
print(d.shape)
print('present in all 42 raw pairs:', d['present_in_all_raw_pairs'].sum())   # expect 193
print('present in every analysis-scope attempt:', (d.frac_attempts_present_scope==1).sum())"

# 6. Aggregation, after the dispatcher run
python run_gene_corr_concat.py --out-dir /tmp/gene_panel_tables --date-tag 260827 --by-strat
python -c "
import pandas as pd
m=pd.read_csv('/tmp/gene_panel_tables/gene_gene_consensus_within_260827.csv.gz',index_col=0)
print(m.shape, 'symmetric:', bool((m.values==m.values.T).all()), 'diag:', m.values.diagonal()[:3])"

# 7. run_metrics_concat.py new flags (writes four dated tables into one folder)
cd ..
python run_metrics_concat.py --out-dir /tmp/metrics_out --date-tag 260827 && ls /tmp/metrics_out

# 8. Notebook regeneration (analysis side)
cd ../harmonization-metrics
python create_marker_gene_deep_analysis_notebook.py
python -c "
import nbformat; nb=nbformat.read('marker_gene_deep_analysis.ipynb', as_version=4)
print(len(nb.cells), 'cells')
assert not any(c.get('outputs') for c in nb.cells if c.cell_type=='code'), 'outputs must be empty'"
```

---

## TODO

### Compute side — `harmonization-metrics-calculation/gene_panel_analysis/`

- [x] Create the `gene_panel_analysis/` sub-directory with the parent-import `sys.path` preamble convention
- [x] `gene_panel_structure.py` — module skeleton; import `MIN_COHORT_N` (= 20) from `compute_batch_metrics`, define `FISHER_CLIP`, `LOW_EXPRESSION_THRESHOLD`
- [x] `gene_panel_structure.py` — `fisher_z` / `inverse_fisher_z` with `±1` clipping
- [x] `gene_panel_structure.py` — `pack_upper_triangle` / `unpack_upper_triangle`
- [x] `gene_panel_structure.py` — `gene_gene_correlation` (global flavour)
- [x] `gene_panel_structure.py` — `gene_gene_correlation_within_cohort` (Fisher-z over cohorts ≥ 20 samples, per-pair counts)
- [x] `gene_panel_structure.py` — `gene_expression_qc` (18 columns incl. `icc_cohort`, `genorm_m`)
- [x] `run_gene_corr_job.py` — copy the BLAS/OpenMP `os.environ.setdefault` preamble verbatim from `run_metrics_job.py:45-55`
- [x] `run_gene_corr_job.py` — S3 key helpers, `_download_df`, memory guard, argparse CLI
- [x] `run_gene_corr_job.py` — panel resolution via the parent `marker_panels.resolve_panel` (identical to Group L)
- [x] `run_gene_corr_job.py` — write `.npz` (genes, r_global, r_within, n_within, meta) and `_geneqc.json`
- [x] `run_gene_corr_parallel.py` — dispatcher reusing `_list_exp_files` semantics; `--dry-run` job count
- [x] `run_gene_corr_parallel.py` — **`--shambhala-mode {all,none,default-only}`** replacing `--skip-shambhala`, default `default-only` (keeps `shambhala_P0std_Q0std`)
- [x] `run_gene_corr_parallel.py` — `failed_gene_corr_{pod_name}.txt` tracking (distinct filename from the metrics run)
- [x] `run_gene_corr_concat.py` — streaming Fisher-z accumulation on the union gene index
- [x] `run_gene_corr_concat.py` — **`--out-dir` + `--date-tag`**: every table into one folder with the date postfix; `--no-s3`, `--by-strat`, `--shambhala-mode`
- [x] `build_marker_gene_coverage.py` — coverage from `genes/*.json`: raw-pair columns (`present_in_all_raw_pairs`, expect 193), analysis-scope columns, per-strategy columns; `--out-dir` + `--date-tag`
- [x] `test_mock_gene_structure.py` — all eight assertion groups from §6, incl. the `MIN_COHORT_N = 20` exclusion test
- [x] `README.md` — run book, analysis scope table, `--shambhala-mode` explanation, S3 prefixes, troubleshooting, "not a metric group" note

### Compute side — existing files

- [x] `run_metrics_concat.py` — add `--out-dir`, `--date-tag`, `--out-gene-long`, `--out-cohort-long`, `--out-folds-long`; keep `--out-csv` as an override
- [x] `run_metrics_concat.py` — `_resolve_out_path()` helper; wire all four writes through it
- [x] `run_metrics_concat.py` — update module docstring usage examples
- [x] `CLAUDE.md` — file roles table: `gene_panel_analysis/` row (9a)
- [x] `CLAUDE.md` — Commands: new gene-panel block, and updated `run_metrics_concat.py` examples (9b)
- [x] `CLAUDE.md` — S3 layout: 5 new lines (9c)
- [x] `CLAUDE.md` — "What is NOT here": add the new notebook (9d)
- [x] `CLAUDE.md` — note that `gene_panel_analysis/` is not a metric group (9e)
- [x] `README.md` — pointer to `gene_panel_analysis/README.md`; confirm sparse checkout and rsync already cover it (10)

### Pod run

Every item below needs S3 credentials and the metrics pod, so none can be done locally.

- [ ] Launch / reuse `fl-metrics`; rsync `harmonization-metrics-calculation/` including `gene_panel_analysis/` *(requires live pod)*
- [ ] `python test_mock_gene_structure.py` inside the pod *(passes locally: 15/15)*
- [ ] Single-job verification (verification command 3) *(requires S3)*
- [ ] `--dry-run` must report **1,204 jobs** (verification command 4) *(requires S3)*
- [ ] `run_gene_corr_parallel.py` — 1,204 jobs, `--n-workers 20` *(requires live pod)*
- [ ] `run_gene_corr_concat.py --out-dir /workspace/gene_panel_tables --date-tag 260827 --by-strat` *(requires live pod)*
- [ ] `build_marker_gene_coverage.py --out-dir /workspace/gene_panel_tables --date-tag 260827` — confirm 193 reference genes *(requires S3; the 193 is already confirmed from the local long table)*
- [ ] Copy the outputs into `harmonization-metrics/metric_tables/` *(requires live pod)*

### Analysis side — `harmonization-metrics/`

- [x] `create_marker_gene_deep_analysis_notebook.py` — generator skeleton, `DATE_TAG`, `PANEL_TAG`, `FIG_DIR`, `md()`/`code()`
- [x] §1 — rcParams, `save_figure` (the only custom helper), input constants, v3 attempt palettes copied verbatim
- [x] §1 — `cell_type_pal` from v3 `lymphoma_ontogeny_palette` for the 6 mapped types + 9 biology-derived TME colours; `gene_group_pal`, `pathway_pal`, `tme_subtype_pal`
- [x] §2 — loaders, analysis-scope filter (drop Shambhala cross-product, rename `shambhala_P0std_Q0std` → `20_shambhala`), `rho_wide` pivot, integrity assertions
- [x] §3 — gene-set structure: supervenn, venn3/venn2, Jaccard clustermap, multiplicity histogram, `T0_gene_set_overlap.csv`
- [x] §4 — coverage: `COVERAGE_SCOPE` switch defaulting to `"raw_all_pairs"` (193 genes), 5 figures, `T1_coverage_gate.csv`
- [x] §5 — expression QC gates on `01_raw__post0`: 5 figures, `T2_qc_gate.csv`
- [x] §6 — saturation split: `SATURATION_MEDIAN_MAX = 0.99`, ordered quantile plot, removed-gene barplot, composition check, `T3_saturation_split.csv`
- [x] §7 — ρ distributions and quantiles: 6 figures, `T4_per_gene_rho_summary.csv`
- [x] §8a — master clustermap genes × attempts, 3 variants + separate legend panels
- [x] §8b — self-contained S3 loaders, `RUN_SCATTER_SECTION` flag, 5 scatter/density figures
- [x] §9 — gene × gene consensus structure: 6 figures, `T5_gene_pair_redundancy.csv`
- [x] §10 — four panel selectors, `l8_panel_size_vs_signal` decision plot per D7, `T6`/`T7` tables
- [x] §11 — noise and coherence: 7 figures with full markdown method explanations, `T8_gene_noise_coherence.csv`
- [x] §12 — recommendation markdown + `T9_supplementary_marker_panel_selection.csv`
- [x] Verify every figure uses a stock seaborn/matplotlib call and every method block has its markdown explanation (D8)
- [x] Run `python create_marker_gene_deep_analysis_notebook.py`; execute the notebook end to end
- [x] Confirm the `.ipynb` is < 100 MB with outputs stripped
- [x] `CLAUDE.md` — 6 new file-role rows, new command, mark the 260819 audit superseded (13a–13c)

### Project documentation

- [x] `FL_harmonization/CLAUDE.md` — 2 new Key Files rows (14a)
- [x] `FL_harmonization/CLAUDE.md` — new "Marker panel reduction" next-step item (14b)
- [x] Confirm `requirements.txt` and `k8s/pod-metrics.yaml` genuinely need no edit (15)
