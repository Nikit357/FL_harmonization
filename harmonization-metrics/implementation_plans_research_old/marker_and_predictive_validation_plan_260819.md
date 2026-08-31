# Implementation plan — Marker correlation preservation, cross-batch rank agreement and predictive validation

**Date:** 2026-08-19 (revised twice after Daniil's review)
**Author:** Claude (for Daniil Nikitin)
**Status:** DRAFT — awaiting Daniil's approval. No code written yet.

> **Path note (2026-08-20):** the compute scripts this plan describes (`compute_batch_metrics.py`,
> `run_metrics_job.py`, `run_metrics_parallel.py`, `run_metrics_concat.py`, `marker_panels.py`,
> `marker_gene_annotation.csv`) moved to `../harmonization-metrics-calculation/`. Paths written as
> `harmonization-metrics/<script>` below refer to that folder now.

---

## Overview

Colleagues reviewing the FL harmonization benchmark asked for quality checks that the current 11
metric groups (A–K) do not cover. Three new metric groups are added **inside the existing metrics
framework** — no separate library, worker, dispatcher or S3 prefix:

| Group | Name | Prefix | Question it answers |
|---|---|---|---|
| **L** | Marker gene correlation preservation | `mk_` | For each marker gene, is its expression profile across a cohort's samples the same before and after harmonization? |
| **M** | Cross-batch rank agreement | `xb_` | Within this one matrix, do samples of the *same biology* from *different batches* rank the marker genes similarly — and more so than samples of *different* biology? |
| **N** | Predictive validation | `pv_` | Can a simple 10-PC classifier predict diagnosis in a batch it has never seen, and does the score collapse under permuted labels? |

The new keys land in the **existing** `metrics/{strat}__{imp}__{method}__post{0|1}_metrics.json`
sidecars and therefore in `metrics_comprehensive.csv`. They do **not** enter the Figure 3
clustermap or the composite score: `_build_polarity()` in `figures_helpers.py` assigns polarity `0`
to every column whose prefix is not in `_GROUP_MAP`, and `scoring_cols` keeps only nonzero-polarity
columns. Two safeguards are added on top of that automatic behaviour (§8), and `_GROUP_MAP` is
deliberately **not** extended with L/M/N.

**Run scope: every attempt that already has a metrics sidecar**, so the new metrics can be compared
between the clustermap's best approaches and everything else. The incremental machinery already in
`run_metrics_job.py` makes this cheap: a re-run with `--groups L,M,N` loads the existing sidecar,
sees that A–K sentinels are already set, computes only L/M/N, and merges the result back into the
same JSON.

**Only Group L reads a second matrix.** Groups M and N are computed from the job's own matrix alone.
The unharmonized baseline for M and N is not recomputed per job — the `01_raw` attempts are
themselves rows in the run set, so the notebook obtains every baseline by joining on
`(strat, imp)`. Computing it inside each job would repeat the identical quantity ~60 times per
`(strat, imp)` pair.

---

## Background / reference data

### The cohort is 7,174 samples

**Source of truth:** `s3://$FL_S3_BUCKET/FL_batch_correction/prepared/{strat}__{imp}__ann.tsv.gz`.
Verified: `S0_no_removal__strict__ann.tsv.gz` is exactly **7,174 × 485**. The local
`comb_ann_unified.csv` has 7,238 rows — 64 annotation-only samples with no expression — and must
not be used for any count. The metrics pipeline already reads the prepared annotation, so no code
change is needed; the correction applies to every number quoted in plans, figures and the
manuscript. Recorded in project memory as `project_final_cohort_7174.md`.

Level counts in the 7,174-sample cohort:

| Column | Levels | Top levels (n) | Role in the new metrics |
|---|---|---|---|
| `RNA_BATCH` | 29 | RNASeq_FF_PolyA (1,039), GPL570_Unknown_Unknown (1,007), GPL570_FF_Unknown (994), RNASeq_FFPE_Exome_capture (939) | leave-one-batch-out folds (N); "different batch" constraint (M) |
| `COHORT_LABEL` | 88 | PUB_DLBCL_GSE117556 (810), SOM (623), PUB_DLBCL_NCICCR (567), PUB_DLBCL_GOYA (553) | correlation computed **within** each cohort (L) |
| `PLATFORM_RNA` | 19 | GPL570 (2,801), RNASeq (2,243), GPL14951 (810), GPL96+97 (305) | reported as a covariate only |
| `Major_group` | 7 | DLBCL (4,466), FL (1,687), Normal_B_cells (733), Kassandra (141), Burkitt (88), HGBCL (34), B_cells (25) | 3-class predictor target |
| `Diagnosis_cell_type_unified` | 15 | DLBCL (4,466), FL (1,697), Memory (215), Naive (194) | "same biology" constraint (M); 2-class target |
| `TUMOR_NORMAL` | 2 | Tumor (6,296), Normal (878) | `Normal_B` class definition |
| `RNASEQ_SOURCE` | 2 | FF (4,174), FFPE (3,000) | reported as a covariate only |

Class collapse for the predictor (rare entities dropped, consistent with the rest of the project):

| Class | Source | n |
|---|---|---|
| `DLBCL` | `Major_group == "Diffuse_Large_B_Cell_Lymphoma"` | 4,466 |
| `FL` | `Major_group == "Follicular_Lymphoma"` | 1,687 |
| `Normal_B` | `TUMOR_NORMAL == "Normal"` | 878 |
| *dropped* | Burkitt (88), HGBCL (34) | 122 |

### Attempts on S3

| Set | n | Note |
|---|---|---|
| Metrics sidecars on S3 | **3,835** | 1,918 post0 + 1,917 post1; 42 distinct `(strat, imp)` pairs |
| Non-Shambhala sidecars | **2,323** | the Article 1 benchmark; 84 short of the 2,407 theoretical grid (those runs never produced metrics) |
| Shambhala sidecars | **1,512** | excluded from Article 1 |
| Expression files | 3,836 | mean **304 MB** compressed, **1,165 GB** total |

**Default run set = the 2,323 non-Shambhala attempts.** Shambhala is opt-in (adds 1,512 jobs and
~65 % to the runtime for data excluded from Article 1).

### ⚠ Marker gene availability — a finding, not a nuisance

`fsqn_normalized_exp_R.tsv` (the `strict` full-coverage intersection) is samples × **3,447 genes**.
Of a 54-gene candidate panel, only **23** are present:

```
missing: MS4A1, CD3D, CD3E, CD3G, MME, FCER2, CD79A, CD79B, PRDM1, MYC, PTPRC,
         CD68, FOXP3, PDCD1, CXCR5, TOP2A, KMT2D, TNFRSF14, ACTB, GAPDH, TUBB,
         RPLP0, SDHA, UBC, YWHAZ, RPL13A, PSMB4, STAT1, ISG15, CXCL9, CXCL10
```

So **CD20 (`MS4A1`), CD3 (`CD3D/E/G`), CD10 (`MME`), CD23 (`FCER2`), CD79A/B — and even `ACTB` and
`GAPDH` — are absent from the strict intersection.** Present and usable: `BCL2`, `BCL6`, `MKI67`,
`PCNA`, `AICDA`, `CXCR4`, `LMO2`, `FN1`, `CCND2`, `EZH2`, `CREBBP`, `CD4`, `CD8A`, `CD5`, `CD163`,
`IRF4`, `B2M`, `PPIA`, `TBP`, `PGK1`, `HPRT1`, `EEF1A1`.

Handling: every gene is computed per attempt and reported individually, so a gene absent from one
`(strat, imp)` is simply `null` there. The notebook averages only genes that are non-NA across
**all** attempts (§9). The `knn` and `softimpute` matrices retain more genes than `strict`, so some
of the missing markers are likely recoverable — Phase 0 measures this per gene across all 42
`(strat, imp)` pairs, and the resulting coverage table is a manuscript panel in its own right.

---

## Resolved — final panel (Phase 0 result, 2026-08-19; re-built 2026-08-20)

`marker_gene_annotation.csv` holds **757 rows** (gene × gene_group), **548 unique genes**,
**67 gene groups**, of which 15 are the housekeeping control. Built by
`build_marker_gene_annotation.py`, which now reads the two supplementary spreadsheets Daniil
supplied instead of standing in for them. Per-gene provenance (counted on unique genes):
`kotlov_table_s1` 206, `holmes_table_s2` 193, `repo_panel` 80, `article_text` 39,
`housekeeping` 15, `canonical_marker` 15.

**Published signature lists now used verbatim.**

| Source | What was read | Groups added |
|---|---|---|
| Kotlov Table S1 | the 22 gene-based FGES (4–34 genes each) | `kotlov_FGES_LEC`, `_VEC`, `_CAF`, `_FRC`, `_ECM`, `_ECM_remodeling`, `_granulocyte_traffic`, `_IS_cytokines`, `_FDC`, `_macrophages`, `_activated_M1`, `_T_cells_traffic`, `_MHC_I`, `_MHC_II`, `_TFH`, `_Treg`, `_TIL`, `_IS_checkpoints`, `_NK`, `_B_cells_traffic`, `_B_cells`, `_cell_proliferation` |
| Kotlov Tables S2, S3 | the cell-of-origin (32 genes) and double-hit (20 genes) classifier panels | `kotlov_COO_classifier`, `kotlov_DHIT_classifier` |
| Holmes Table S2 | per-cluster up-regulated genes, already ordered by log2 fold change, truncated at `HOLMES_TOP_N_UP = 20` | `holmes_DZ_a/b/c`, `holmes_INT_a/b/c/d/e`, `holmes_LZ_a/b`, `holmes_PreM`, `holmes_PBL_a/b` |

Three Table S1 rows (NFkB, PI3K, p53) hold the literal `PROGENY` rather than a gene list and are
skipped; the corresponding pathway blocks stay as curated `canonical_marker` panels, as do the
dendritic-cell and cytolytic panels, which have no Table S1 counterpart. Only the up-regulated
Holmes lists are used — each "DWN" list describes the *other* clusters, not the cluster it is
named for. Clone IDs, mitochondrial transcripts, antisense/lncRNA entries and ribosomal
pseudogenes are filtered out by `_NON_MARKER_SYMBOL`; they never appear in an HGNC-mapped
benchmark matrix and would only depress `mk_n_panel_genes_used`.

**Two annotation judgements are stated in the script, not read from a spreadsheet.** Table S1
carries gene sets only, so `tme_subtype` per FGES comes from the paper's own definition of the
four microenvironmental subtypes (`KOTLOV_FGES_ANNOTATION`), and `prognostic_significance` stays
`none` for every FGES because Table S1 reports no per-gene outcome. The Holmes per-cluster
`prognostic_significance` strings are the paper's family-level outcome statements, carried over
unchanged from the earlier hand-built table (`HOLMES_CLUSTER_ANNOTATION`).

**Coverage audit across all 42 `(strat, imp)` pairs** (full per-gene table in
`marker_gene_coverage_audit_260819.csv`):

| Availability | Genes |
|---|---|
| Present in **all 42** pairs — the set used for cross-attempt averages | **178** |
| Present in **some** pairs (6–37 of 42) | 325 |
| Present in **no** pair | 45 |

Per-provenance breakdown of that audit:

| Provenance | none | some | all 42 |
|---|---|---|---|
| `kotlov_table_s1` | 11 | 131 | 64 |
| `holmes_table_s2` | 27 | 113 | 53 |
| `repo_panel` | 4 | 39 | 37 |
| `article_text` | 2 | 26 | 11 |
| `canonical_marker` | 1 | 7 | 7 |
| `housekeeping` | 0 | 9 | 6 |

The 45 never available are dominated by immunoglobulin and T-cell-receptor constant regions
(`IGHD`, `IGHM`, `JCHAIN`, `MZB1`, `TRAC`, `TRBC1`, `TRBC2`), secretory-pathway genes from the
Holmes plasmablast clusters (`MANF`, `MYDGF`, `P4HB`, `SELENOH/K/S`), and a handful of symbols
that predate the current HGNC nomenclature (`PRKCB1`, `NT5C3A`, `LAMTOR5`, `PCLAF`, `SMIM14`).
The previously reported 12 (`CDK1`, `CLEC9A`, `FDCSP`, `GCSAM`, `IGHD`, `IGHM`, `JCHAIN`,
`KMT2D`, `MTOR`, `MZB1`, `SUGCT`, `VSIR`) are still absent apart from `CDK1` and `VSIR`, which
left the panel when the stand-in blocks were replaced.

**The earlier concern is materially reduced.** The clinical markers the colleagues named are
absent only from the `strict` intersection, not from the benchmark as a whole:

| Marker | Pairs present | Marker | Pairs present |
|---|---|---|---|
| `CR2` (CD21), `BCL2`, `BCL6`, `MKI67`, `IRF4`, `CD4`, `CD8A`, `CD163`, `B2M` | 42/42 | `FOXP3` | 37/42 |
| `MME` (CD10), `MYC` | 33/42 | `MS4A1` (CD20), `CD3D`, `CD3E`, `FCER2` (CD23), `CD79A`, `CD79B`, `PDCD1` (PD-1), `ACTB` | 27/42 |
| `GAPDH` | 26/42 | `CD68` | 21/42 |

So CD20 and CD3 are recoverable for roughly two-thirds of attempts via the `knn` and
`softimpute` matrices. The article should state the coverage per gene rather than claiming the
markers were unavailable.

**Cost of the larger panel.** Group L is per-gene × per-cohort Spearman, so its runtime scales
with the panel: 548 genes against the previous 288 is ~1.9×. Group L is the cheap group — the
measured 4.5 min/job worst case is dominated by the 100 Group N permutations — so the profiled
per-job budget still holds.

**Not machine-readable.** Holmes supplementary `jem_20200483_tables3.xlsx` and `tables4.xlsx`
are truncated downloads (exactly 5 MiB and 6 MiB; valid local file headers, no zip central
directory) and cannot be opened. They are not needed: Table S2 is the one that carries the GC
B-cell state signatures the plan asked for. Table S5 is a per-sample sc-COO assignment table,
not a gene list.

**Outstanding, needs Daniil:** sign-off on the rebuilt gene table, in particular the
`HOLMES_TOP_N_UP = 20` truncation and the two annotation judgements above.

---

## The marker gene annotation table

A single committed CSV, `harmonization-metrics/marker_gene_annotation.csv`, is the source of truth
for every gene used by groups L and M. Schema:

| Column | Content |
|---|---|
| `gene` | HGNC primary symbol |
| `alias` | IHC / clinical alias (CD20, CD10, Ki-67, MUM1, PD-1 …), blank if none |
| `gene_group` | the signature or panel the gene belongs to |
| `cell_type` | associated cell type: centroblast (DZ), centrocyte (LZ), plasma cell, memory B, naive B, CD4 T, CD8 T, Treg, follicular dendritic, macrophage, stromal/fibroblast, endothelial, NK, none |
| `pathway` | BCR, NF-κB, PI3K-AKT, interferon, proliferation, apoptosis, epigenetic, none |
| `tme_subtype` | Kotlov LME subtype the gene marks: GC-like, mesenchymal, inflammatory, depleted, none |
| `prognostic_significance` | favourable / adverse / none, with the reported endpoint (OS, PFS, POD24) |
| `source_article` | short citation + DOI/PMCID |
| `is_housekeeping` | boolean — the negative-control group |

Gene groups to populate:

1. **Clinical / IHC markers** (new) — the diagnostic panel the colleagues named: `MS4A1` (CD20),
   `CD3D`/`CD3E`/`CD3G` (CD3), `MME` (CD10), `FCER2` (CD23), `CR2` (CD21), `CD79A`, `CD79B`,
   `BCL2`, `BCL6`, `MKI67` (Ki-67), `IRF4` (MUM1), `PRDM1`, `MYC`, `CD4`, `CD8A`, `CD5`, `PTPRC`
   (CD45), `CD68`, `CD163`, `FOXP3`, `PDCD1` (PD-1), `LAG3`, `TNFRSF9`.
2. **Kotlov et al. 2021** — *Clinical and Biological Subtypes of B-cell Lymphoma Revealed by
   Microenvironmental Signatures*, Cancer Discovery, PMC8178179. Extract the functional gene
   signatures underlying the four LME subtypes (GC-like, mesenchymal, inflammatory, depleted) from
   the paper's supplementary tables; annotate `tme_subtype` and `cell_type` per gene.
3. **Holmes et al. 2020** — *Single-cell analysis of germinal center B cells informs on lymphoma
   cell of origin and outcome*, JEM 217(10):e20200483. Extract the GC B-cell state signatures
   (dark zone, light zone, intermediate, precursor memory) and annotate `cell_type` as
   centroblast / centrocyte / memory precursor, with the reported outcome association in
   `prognostic_significance`.
4. **`FL_2025_MARKERS`, `LEGACY_GC_MARKERS`, `FL_PROG_SIGNATURES`, `FL_PATHWAY_GENES`** — lifted from
   `insert_cells.py:1611–1657` (currently a notebook cell source string, duplicated in
   `implementation_plans_research_old/metrics_notebook_plan.md`) and given full `source_article`,
   `cell_type` and `prognostic_significance` annotation in the same table.
5. **Housekeeping negative control** — `ACTB`, `GAPDH`, `TUBB`, `B2M`, `PPIA`, `RPLP0`, `TBP`,
   `PGK1`, `SDHA`, `HPRT1`, `UBC`, `YWHAZ`, `RPL13A`, `EEF1A1`, `PSMB4`, with
   `is_housekeeping = True`.

**Why housekeeping is the control, stated precisely.** Housekeeping genes sit at the same
expression level in every sample, so their within-cohort variance is near the noise floor and their
sample ranks carry little signal; a method that genuinely reshuffles samples will drive their
before/after ρ toward 0. The desired signature of a good harmonizer is therefore **high ρ on
biologically variable markers and low ρ on housekeeping genes**. One caveat to keep honest: a
harmonizer that applies a *per-batch monotone* transform preserves ranks exactly, so it scores
ρ ≈ 1 on housekeeping genes too — for that method class the housekeeping panel reads as a contrast
against the markers rather than as an absolute floor.

`marker_panels.py` is a thin loader over this CSV: `load_marker_annotation()`,
`panel_genes(group=None, include_housekeeping=False)`, `GENE_ALIASES` +
`resolve_panel(available, panel)` for alias fallback (`MME`↔`CD10`, `FCER2`↔`CD23`, `CR2`↔`CD21`,
`PTPRC`↔`CD45`, `MS4A1`↔`CD20`, `PDCD1`↔`CD279`, `FAS`↔`TNFRSF6`).

---

## Metric definitions

Shared constants in `compute_batch_metrics.py`: `RANDOM_SEED = 260819`, `N_PERM = 100`,
`MIN_COHORT_N = 20`, `MIN_TEST_N = 20`, `N_PCS = 10`, `XB_MAX_SAMPLES = 8000`.

### Group L — marker gene correlation preservation (`mk_*`)

This is the only group that needs a second matrix, because it is inherently a before/after
comparison of the same gene in the same samples.

**Reference matrix.** For a job `(strat, imp, method, post_rm)`, the reference is always
`exp/{strat}__{imp}__01_raw__post0.tsv.gz` — the unharmonized matrix for the *same* strategy and
imputation — then intersected down to the job's own sample index. For a `post1` job this
automatically restricts both matrices to the samples that survived post-removal, which is exactly
the required behaviour. Using `01_raw__post1` instead would be wrong: post-removal identifies
outlier batches on the *harmonized* matrix, so the removed batches differ per method and the two
sample sets would not match.

**Computation.** Genes = annotation panel ∩ columns(reference) ∩ columns(job matrix). Cohorts =
`COHORT_LABEL` levels with ≥ `MIN_COHORT_N` samples. For cohort *c* and gene *g*: Spearman ρ
between the gene's expression vector across the cohort's samples before and after harmonization.

**Reported keys.**

| Key | Content |
|---|---|
| `mk_rho_by_gene` | nested dict `{gene: mean ρ over cohorts}` — the per-gene picture, ~250 floats |
| `mk_rho_n_cohorts_by_gene` | nested dict `{gene: number of cohorts contributing}` |
| `mk_rho_mean_all_genes` | grand mean over genes of `mk_rho_by_gene` (**group sentinel**) |
| `mk_rho_median_all_genes`, `mk_rho_p10_all_genes`, `mk_rho_min_all_genes` | distribution over genes |
| `mk_rho_frac_genes_above_0.9` | fraction of genes with mean ρ > 0.9 |
| `mk_rho_mean_markers`, `mk_rho_mean_housekeeping` | the two panel means, for the contrast |
| `mk_rho_marker_minus_hk` | `mk_rho_mean_markers − mk_rho_mean_housekeeping` |
| `mk_rho_by_cohort` | nested dict `{cohort: mean ρ over genes}` — per-cohort view |
| `mk_rho_mean_by_cohort_mean` | mean over cohorts of the above |
| `mk_n_panel_genes_used`, `mk_panel_coverage_frac`, `mk_n_genes_null` | coverage bookkeeping |
| `mk_n_cohorts_used`, `mk_n_cohorts_skipped_small` | cohort bookkeeping |
| `mk_ref_key`, `mk_ref_n_samples`, `mk_is_self_reference` | provenance; `mk_is_self_reference = True` when the job *is* `01_raw__post0` |

**Storage of per-gene detail.** `mk_rho_by_gene` (~250 floats, ~6 KB) goes into the existing
metrics JSON. The full gene × cohort matrix (~250 × 88 = 22,000 floats, ~300 KB per job; 1.1 GB
across 3,835 jobs) is **not** stored by default; the flag `--save-gene-cohort-detail` writes it to
`marker_corr/{strat}__{imp}__{method}__post{0|1}_gene_cohort.json.gz` for the ~15 best approaches
only.

**⚠ Known ceiling — must be stated in the article.** Any harmonizer applying a *per-batch monotone
transform of each gene* (per-batch centering, scaling, z-score, median scaling, and to first order
ComBat / limma `removeBatchEffect`) leaves within-cohort Spearman correlations **exactly or nearly
unchanged**, so L sits at ~1.0 for that whole method class by construction. L discriminates only
methods that reorder samples within a cohort — quantile normalization to a reference, FSQN, MNN,
rank-based methods, SVA, and anything driven by imputation. **Group M is the metric that
discriminates across all methods** and should carry the sub-chapter's conclusion; L is the "did
anything break, and did it break the markers more than the housekeepers" guard rail. A near-1.0 L
must not be presented as evidence of quality.

### Group M — cross-batch rank agreement (`xb_*`)

The discriminative direction: after harmonization, two samples of the same biology from different
batches should rank the marker genes more similarly.

**Single-matrix by design.** Group M is computed from the job's own matrix only. The unharmonized
baseline is not recomputed here: `01_raw` is itself an attempt in the run set, so its `xb_*` values
*are* the baseline, and the notebook forms the comparison by joining on `(strat, imp)` (§9 §6).
Computing the raw quantity inside every job would repeat the identical number ~60 times per
`(strat, imp)` pair and would double both the runtime and the memory of this group.

**Computation.** Restrict to the annotation panel genes. Rank the samples × genes matrix along the
gene axis, then one matrix product yields the full sample × sample correlation matrix of those
ranks (Spearman). Two masks are then applied:

- **same-biology mask** — `RNA_BATCH[i] ≠ RNA_BATCH[j]` **and**
  `Diagnosis_cell_type_unified[i] == Diagnosis_cell_type_unified[j]`
- **different-biology mask** — `RNA_BATCH[i] ≠ RNA_BATCH[j]` **and**
  `Diagnosis_cell_type_unified[i] ≠ Diagnosis_cell_type_unified[j]`

**Reported keys.**

| Key | Content |
|---|---|
| `xb_rank_agree` | mean ρ over same-biology / different-batch pairs (**group sentinel**) |
| `xb_rank_agree_median` | median over the same pairs, robustness check |
| `xb_rank_disagree_diffbio` | mean ρ over different-biology / different-batch pairs |
| `xb_rank_disagree_diffbio_median` | median over the same pairs |
| `xb_rank_agree_ratio` | `xb_rank_agree − xb_rank_disagree_diffbio` — the within-matrix biology-specific margin |
| `xb_rank_agree_by_diagnosis` | nested dict `{diagnosis: mean ρ}` — FL, DLBCL and each normal subset separately |
| `xb_n_pairs_same_bio`, `xb_n_pairs_diff_bio`, `xb_n_samples_used`, `xb_subsampled` | bookkeeping |

`xb_rank_agree_ratio` is the number to quote. A method that squashes all samples toward a common
profile raises `xb_rank_agree` too; only the margin over different-biology pairs distinguishes real
batch correction from the over-correction the project is trying to detect. Because the margin is a
within-matrix contrast, it is meaningful even without any raw comparison.

**Memory.** At 7,174 samples the rank-correlation matrix is 7,174² × 8 B = **412 MB** — one matrix,
not two, now that the reference is gone. If `n_samples > XB_MAX_SAMPLES` the computation subsamples
stratified by `RNA_BATCH` and sets `xb_subsampled = True`.

### Group N — predictive validation (`pv_*`)

Features: **10 PCs fitted on the training batches only** and projected onto the held-out batch;
`StandardScaler` fitted on the training set. No global-PCA variant.
Model: `LogisticRegression(max_iter=2000, class_weight="balanced", random_state=RANDOM_SEED)`.

**No imputation.** The matrices are already imputed upstream (`strict` / `knn` / `softimpute`), so
Group N does **not** impute. It asserts the matrix is NA-free; should a harmonizer nevertheless have
left NAs — Group K exists because some do — the affected genes and samples are **dropped** and
counted in `pv_n_genes_dropped_na` and `pv_n_samples_dropped_na`. Filling NAs with a gene mean
would silently invent data and make the score incomparable across attempts.

**N1 — leave-one-batch-out, 3 classes** (FL / DLBCL / Normal_B). Folds: every `RNA_BATCH` level
with ≥ `MIN_TEST_N` samples, held out in turn.

**N2 — leave-one-batch-out, 2 classes** (FL vs DLBCL). Same folds and the same cached per-fold PCA,
with samples restricted to FL ∪ DLBCL.

**Fold inclusion rules** (as directed):

- **F1 uses every fold**, including single-class test batches. A predictor facing a DLBCL-only
  batch should label as many samples DLBCL as it can — that is the honest real-world test.
- **AUC uses only folds whose test batch contains ≥2 classes.** Both counts are reported so the
  means are interpretable.

**Keys** (prefix `pv_lobo3_` for N1, `pv_lobo2_` for N2):

| Key | Content |
|---|---|
| `pv_lobo3_f1_macro_mean` | mean macro-F1 over all folds (**group sentinel**) |
| `pv_lobo3_f1_macro_median`, `_std`, `_min` | distribution over folds |
| `pv_lobo3_f1_weighted_mean`, `pv_lobo3_bal_acc_mean`, `pv_lobo3_mcc_mean` | alternative summaries |
| `pv_lobo3_auc_macro_mean` | mean one-vs-rest AUC over multi-class folds only |
| `pv_lobo3_f1_per_class_FL` / `_DLBCL` / `_Normal_B` | per-class mean F1 |
| `pv_lobo3_n_folds`, `pv_lobo3_n_folds_multiclass` | fold accounting — reported alongside every mean |
| `pv_lobo3_folds` | nested dict `{batch: {n, n_classes, f1_macro, auc}}` for the per-batch plot |
| `pv_lobo2_*` | the same set for FL vs DLBCL, with `auc` binary rather than one-vs-rest |
| `pv_n_genes_dropped_na`, `pv_n_samples_dropped_na` | NA accounting (expected 0) |

**N3 — permutation negative control.** `N_PERM = 100` label shuffles (fixed seed sequence),
N1 and N2 re-run on each. This is affordable because PCA is label-independent: the per-fold PCA
projections are computed once and reused across all permutations, so each permutation costs only
the logistic fits. Keys: `pv_lobo3_f1_macro_perm_mean`, `_perm_std`, `pv_lobo3_auc_macro_perm_mean`,
`pv_lobo3_f1_macro_delta` (observed − permuted mean), `pv_lobo3_f1_perm_pvalue` (empirical, fraction
of permutations ≥ observed), and the `pv_lobo2_*_perm*` equivalents. `pv_n_perm` records the count
actually used. **The permutation control applies only to these classification metrics** — the
existing biology-preservation metrics (cLISI, ASW_bio, graph connectivity, WaterMelon) are not
recomputed on permuted labels.

If profiling shows N3 dominating the run, `--n-perm 10` is the sanctioned fallback; `pv_n_perm`
makes the choice visible in the output table.

---

## Files to change

### 1. NEW `harmonization-metrics/marker_gene_annotation.csv`

The gene annotation table described above. Built once in Phase 0 from the two new papers plus the
existing panels; committed so every downstream number is reproducible.

### 2. NEW `harmonization-metrics/marker_panels.py`

Thin loader over the CSV — `load_marker_annotation()`, `panel_genes()`, `GENE_ALIASES`,
`resolve_panel()`, `panel_summary()` (counts per `gene_group` / `cell_type`, for the supplementary
table). No gene lists hardcoded in Python; the CSV is the single source of truth.

### 3. `harmonization-metrics/compute_batch_metrics.py`

**3a — module docstring** (line 1–6). Before: `All metric computation functions …`.
After: same, noting that groups L, M, N are marker-correlation, cross-batch rank agreement and
predictive validation, and that **Group L alone** requires a raw reference matrix.

**3b — new constants** after `ALL_COLS` (line 44–47):

```python
RANDOM_SEED: int = 260819
N_PERM: int = 100
MIN_COHORT_N: int = 20
MIN_TEST_N: int = 20
N_PCS: int = 10
XB_MAX_SAMPLES: int = 8000
PRED_CLASS_COL: str = "Major_group"
PRED_BIO_COL: str = "Diagnosis_cell_type_unified"
```

**3c — new imports:** `from sklearn.linear_model import LogisticRegression`,
`from sklearn.metrics import f1_score, roc_auc_score, balanced_accuracy_score, matthews_corrcoef`,
`from scipy.stats import rankdata`, and `from marker_panels import panel_genes, resolve_panel`.

**3d — new helpers** before `compute_group_l`: `_collapse_diagnosis(ann_df)` (3-class labels),
`_rank_matrix(X)` (gene-axis ranks), `_corr_from_ranks(R)` (ranks → correlation matrix via one
matmul), `_pairwise_masks(ann_df, batch_col, bio_col)` (returns the same-biology and
different-biology boolean masks over the upper triangle),
`_fold_pca_projections(exp_df, ann_df, folds, n_pcs)` (cached per-fold train/test PC scores),
`_fit_eval_fold(...)`, `_safe_auc(...)`.

**3e — `compute_group_l(exp_df, ref_df, ann_df, panel, min_cohort_n=MIN_COHORT_N)`** — new function
after `compute_group_k` (line 1129–1155).

**3f — `compute_group_m(exp_df, ann_df, panel, max_samples=XB_MAX_SAMPLES)`** — new function.
**No `ref_df` argument**; single-matrix by design.

**3g — `compute_group_n(exp_df, ann_df, n_pcs=N_PCS, n_perm=N_PERM)`** — new function; returns N1,
N2 and N3 keys together, sharing the cached per-fold PCA. Drops NA genes/samples rather than
imputing.

**3h — `compute_all_metrics()` signature** (line 1325–1330). Before:

```python
def compute_all_metrics(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    skip_slow: bool = False,
    tmp_path: Optional[str] = None,
    groups: Optional[set] = None,
) -> dict:
```

After:

```python
def compute_all_metrics(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    skip_slow: bool = False,
    tmp_path: Optional[str] = None,
    groups: Optional[set] = None,
    ref_df: Optional[pd.DataFrame] = None,   # Group L only
    n_perm: int = N_PERM,
    panel: Optional[list[str]] = None,
) -> dict:
```

**3i — active-set literal** (line ~1367). Before `set("ABCDEFGHIJK")` → after `set("ABCDEFGHIJKLMN")`.
The docstring line `Valid values: A B C D E F G H (case-insensitive)` is already stale and becomes
`Valid values: A B C D E F G H I J K L M N (case-insensitive)`.

**3j — group dispatch,** after the `_run_group("I", …)` line (line ~1445):

```python
    _run_group("L", compute_group_l, exp_df, ref_df, ann_df, panel)
    _run_group("M", compute_group_m, exp_df, ann_df, panel)
    _run_group("N", compute_group_n, exp_df, ann_df, N_PCS, n_perm)
```

**3k — reference guard.** If `ref_df is None` and `"L" in active`, write
`error_L = "skipped: no raw reference supplied"` and drop **L only** from `active`, mirroring the
existing PCA-failure pattern. M and N never depend on the reference.

### 4. `harmonization-metrics/run_metrics_job.py`

**4a — `GROUP_SENTINEL_KEYS`** (line 43–55). Add three entries:

```python
    "L": "mk_rho_mean_all_genes",
    "M": "xb_rank_agree",
    "N": "pv_lobo3_f1_macro_mean",
```

**4b — new S3 key helper** next to `_s3_key_exp`:

```python
def _s3_key_ref_exp(strat: str, imp: str) -> str:
    return f"{S3_PREFIX}/exp/{strat}__{imp}__01_raw__post0.tsv.gz"
```

**4c — reference download with a local cache.** Before downloading, look for
`{--ref-cache-dir}/{strat}__{imp}__01_raw__post0.tsv.gz` on the PVC; download and store it there on
a miss. There are only **42 distinct `(strat, imp)` pairs** but 2,323 jobs, so this turns ~2,281
downloads of a ~304 MB file into local disk reads — the single largest runtime saving in the plan
(~30 CPU-hours). Cache footprint: 42 × 304 MB ≈ **12.8 GB** on `/workspace`.

**4d — reference alignment.** When the reference is loaded, intersect its index with the already
aligned `exp_df` / `ann_df` and assert all three have equal length. For a `post1` job this is what
restricts Group L to the post-removal-surviving samples.

**4e — reference is fetched only for Group L.** Gate the download on `"L" in groups_to_run`. A
`--groups M,N` run does no extra I/O at all.

**4f — new CLI flags:** `--ref-cache-dir` (default `/workspace/ref_cache`), `--n-perm` (default
`N_PERM`), `--save-gene-cohort-detail`, `--panel-groups` (comma-separated `gene_group` filter,
default all).

**4g — default requested-groups literal** (line ~228). Before `set("ABCDEFGHJK")` → after
`set("ABCDEFGHJKLMN")`. (Note the existing literal omits `I`, which is added separately by the
`--skip-wm` logic below it; that behaviour is unchanged.)

**4h — exit code 3** extended to cover a missing reference, but only when **L** was requested.

### 5. `harmonization-metrics/run_metrics_parallel.py`

**5a — `--groups` help text** (line ~250). Before `Valid: A B C D E F G H I J K.` → after
`Valid: A B C D E F G H I J K L M N.`

**5b — new flags forwarded to workers:** `--ref-cache-dir`, `--n-perm`,
`--save-gene-cohort-detail`, `--panel-groups`.

**5c — `--skip-shambhala`** (new, default off): drops `method.startswith("shambhala")` jobs in
`_list_exp_files()`. This is how the default 2,323-attempt run is selected.

**5d — `--only-with-metrics`** (new, default off): restricts the job list to keys that already have
a metrics sidecar on S3, i.e. "every attempt that has at least one metric calculated". Implemented
by listing the `metrics/` prefix once and intersecting.

**5e — module docstring:** add a "New metric groups L/M/N" usage block.

**5f — default `--timeout-s`** raised from 600 to 1800 in the docstring guidance for L/M/N runs
(the flag default itself stays 600 so existing A–K invocations are unaffected).

### 6. `harmonization-metrics/run_metrics_concat.py`

Six new keys are nested dicts and must not be stringified into `metrics_comprehensive.csv`:
`mk_rho_by_gene`, `mk_rho_n_cohorts_by_gene`, `mk_rho_by_cohort`, `xb_rank_agree_by_diagnosis`,
`pv_lobo3_folds`, `pv_lobo2_folds`.

**6a** — drop nested dict/list values from the wide CSV, keeping only scalars.

**6b** — emit three additional long-format CSVs alongside the wide one:

| File | Rows |
|---|---|
| `marker_gene_correlations_long.csv` | run_id × gene × rho × n_cohorts (from `mk_rho_by_gene`, `mk_rho_n_cohorts_by_gene`) |
| `marker_cohort_correlations_long.csv` | run_id × cohort × rho (from `mk_rho_by_cohort`) |
| `prediction_folds_long.csv` | run_id × batch × {n, n_classes, f1_macro, auc} × {3-class, 2-class} |

`xb_rank_agree_by_diagnosis` is small enough to be pivoted into the wide CSV as
`xb_rank_agree_{diagnosis}` columns rather than a fourth long table.

All four files uploaded to `FL_batch_correction/` and mirrored into `metric_tables/`.

### 7. `harmonization-metrics/test_mock_metrics.py`

Extend the existing smoke-test file (no new test file — the groups now live in the same library):

| Test | Assertion |
|---|---|
| `test_group_l_identity` | `ref_df is exp_df` → `mk_rho_mean_all_genes ≈ 1.0` |
| `test_group_l_per_batch_shift_preserves` | per-batch constant added per gene → ρ ≈ 1.0 (documents the ceiling) |
| `test_group_l_shuffle_destroys` | samples permuted within a cohort → ρ ≈ 0 |
| `test_group_l_per_gene_keys` | `mk_rho_by_gene` has one entry per resolved gene; absent genes are `null`, not missing |
| `test_group_l_missing_panel_genes` | panel ∩ matrix = 3 genes → coverage keys correct, no crash |
| `test_group_m_no_reference_needed` | `compute_group_m` runs from one matrix; no `ref_df` in its signature |
| `test_group_m_batch_effect_lowers_agreement` | two separate calls — a batch-offset matrix has lower `xb_rank_agree` than the same matrix with the offset removed |
| `test_group_m_overcorrection_flagged` | all samples collapsed to one profile → `xb_rank_agree` high but `xb_rank_agree_ratio ≈ 0` |
| `test_group_m_subsampling` | `n_samples > XB_MAX_SAMPLES` → `xb_subsampled is True`, no crash |
| `test_group_n_separable_high_f1` | well-separated synthetic classes → `pv_lobo3_f1_macro_mean > 0.8` |
| `test_group_n_no_imputation` | a matrix with NA cells → genes/samples dropped and counted in `pv_n_genes_dropped_na` / `pv_n_samples_dropped_na`, values not filled |
| `test_group_n_single_class_fold_counted_for_f1` | a single-class test batch contributes to `n_folds` but not `n_folds_multiclass`, and its AUC is `None` |
| `test_group_n_permutation_collapses` | `pv_lobo3_f1_macro_perm_mean` near chance and `< 0.5 ×` observed |
| `test_group_n_degenerate_single_batch` | 1 batch → `pv_lobo3_n_folds == 0`, keys `None`, no crash |
| `test_group_failure_isolation_lmn` | an exception in L leaves M and N keys intact |
| `test_missing_reference_skips_l_only` | `ref_df=None` → `error_L` set, **M, N and A–K still computed** |
| `test_incremental_groups_lmn` | `_groups_to_recompute` returns only `{L,M,N}` for a sidecar that already has A–K |

### 8. `figures_for_article/figures_helpers.py`

The new columns now genuinely reach `metrics_comprehensive.csv`, so the exclusion is no longer
merely defensive — it is what keeps Figure 3 at 2,234 × 87.

**8a — `metric_cols` comprehension** (lines 421–433). Before:

```python
        and not c.startswith("ilisi_mean")
        and c != "wm_subsampled"
    ]
```

After:

```python
        and not c.startswith("ilisi_mean")
        and not c.startswith("mk_")   # Group L — blind check, never scored/clustered
        and not c.startswith("xb_")   # Group M — blind check, never scored/clustered
        and not c.startswith("pv_")   # Group N — blind check, never scored/clustered
        and c != "wm_subsampled"
    ]
```

**8b — assertion at the end of `load_metrics_data()`**, right before the return: assert no
`scoring_cols` entry starts with `mk_`/`xb_`/`pv_`, so a future edit that adds L/M/N to `_GROUP_MAP`
fails loudly instead of silently changing Figure 3.

**8c — `_GROUP_MAP` is deliberately NOT extended.** Adding L/M/N there would give them a group
letter, pull them into `col_meta`, and surface them in the v3 notebook's per-group figures. A code
comment states this.

**8d — new `load_new_metrics_data()`** returning
`(df_lmn, df_gene_long, df_cohort_long, df_folds_long, mk_cols, xb_cols, pv_cols)`, reading the wide
CSV plus the three long CSVs, with the same `run_id` construction so everything joins on `run_id`.

**8e — new `filter_genes_complete_across_attempts(df_gene_long, min_frac=1.0)`** — returns the gene
subset that is non-NA in **every** attempt. Averages in the notebook use only this subset; the count
of genes dropped is printed and reported.

**8f — new `attach_raw_baseline(df, baseline_method="01_raw", baseline_post_rm=0)`** — for every row,
joins the value of the matching `{strat}__{imp}__01_raw__post0` row and returns `*_raw` and
`*_delta` columns for a caller-supplied metric list. This is where the Group M and Group N
before/after comparison is formed, now that it is no longer computed per job. The function records
`baseline_missing` where no `01_raw` row exists.

### 9. NEW `harmonization-metrics/correlation_prediction_metrics_analysis.ipynb`

A dedicated notebook for the three new groups, deliberately separate from
`harmonization_metrics_analysis_v3.ipynb` so Figure 3 and the composite score cannot be disturbed.

**Setup.** `load_metrics_data()` for the 2,234-row analysis set and its `is_best` flag (via the
existing `build_best_vs_rest()`), plus `load_new_metrics_data()` for the L/M/N columns and the three
long tables. `filter_genes_complete_across_attempts()` defines the averaging gene set.
`attach_raw_baseline()` produces the `xb_*_delta` and `pv_*_delta` columns.

⚠ **Baseline caveat for post-removal rows.** The baseline is always
`{strat}__{imp}__01_raw__post0`. A `post1` row therefore compares against a baseline with a
different sample set, because post-removal drops method-specific outlier batches. Since
`xb_rank_agree` and the predictive scores are means over pairs and folds rather than sample-matched
statistics, the comparison is valid, but the notebook labels post1 deltas as approximate and reports
post0 and post1 separately.

**Plot conventions.** `plt.rcParams["font.size"] = 7.5` throughout (all derived sizes — axis labels,
tick labels, legends, annotations — set explicitly relative to it so nothing falls below 7.5 pt),
`pdf.fonttype = "truetype"`, `svg.fonttype = "none"`, `figure.dpi = 200`, `sns.set_style("ticks")`.
Multipanel figures assembled with `GridSpec`. Layout follows the panel arrangement Daniil already
drew in Figma —
`https://www.figma.com/design/t8bFgusleBEwB9ht7rORCH/FL-harmonization-article?node-id=0-1`.
⚠ The Figma MCP quota is ~15 calls per session on the Starter plan, so the frames are read **once**
at the start of Phase 5 and the extracted layout is written to
`figures_for_article/correlation_prediction_figure_layout_260819.md` for reuse without further
calls. Existing notebooks in `harmonization-metrics/` and `figures_for_article/` are the reference
for palette and `save_figure()` usage.

**Sections.**

- **§1 — Setup and data load.** Row counts, gene-completeness report, baseline attachment, sanity
  check that `scoring_cols` is still 87.
- **§2 — Best vs rest (the headline comparison).** For each of `mk_rho_mean_all_genes`,
  `mk_rho_marker_minus_hk`, `xb_rank_agree`, `xb_rank_agree_ratio`, `xb_rank_agree_delta`,
  `pv_lobo3_f1_macro_mean`, `pv_lobo2_auc_macro_mean`: boxplot of best vs rest with individual
  points overlaid, Mann-Whitney p, and effect size. This is the panel that answers "do the
  clustermap winners also win on the blind check?"
- **§3 — Group L by gene group.** Boxplots of per-gene ρ grouped by `gene_group` and by
  `cell_type` (centroblast / centrocyte / plasma / T / macrophage / stromal / housekeeping), one
  panel per method family. The housekeeping group is drawn in a distinct neutral colour as the
  negative control, with the marker-vs-housekeeping contrast annotated.
- **§4 — Group L by individual gene.** Gene × approach heatmap of ρ (genes ordered by mean ρ,
  approaches ordered by the clustermap order) plus a ranked lollipop chart of the best- and
  worst-preserved genes. This is where "some genes preserve their correlation well, others do not"
  becomes visible.
- **§5 — Group L coverage.** `mk_n_panel_genes_used` per `strat × imp`, and a per-gene presence
  matrix across the 42 pairs — the panel that documents the absent CD20/CD3/CD10.
- **§6 — Group M.** Lineplot of `xb_rank_agree_raw → xb_rank_agree` per approach (slope = the gain,
  both ends produced by `attach_raw_baseline()`), same-biology vs different-biology values side by
  side to expose over-correction, `xb_rank_agree_ratio` per approach, and
  `xb_rank_agree_{diagnosis}` split by FL / DLBCL / normal subsets.
- **§7 — Group N.** `pv_lobo3_f1_macro_mean` per approach against the `01_raw` baseline as a dashed
  reference line and the permuted null as a shaded band; per-batch F1 strip plot from
  `prediction_folds_long.csv`; 3-class vs 2-class comparison; AUC restricted to multi-class folds
  with `n_folds_multiclass` annotated on every bar.
- **§8 — Permutation control.** Observed vs permuted F1 and AUC distributions, and the empirical
  p-value per approach. The expected result is a collapse to chance; §8 states plainly if it does
  not.
- **§9 — Export.** Supplementary File 5: the wide L/M/N table, the three long tables, and
  `marker_gene_annotation.csv`. All figures saved as PDF **and** SVG into
  `figures_for_article/current_figures_tables_for_article_260819/`.

### 10. `harmonization-metrics/k8s/pod-metrics.yaml`

**10a — SSH public key moves out of the manifest.** Lines 1–10 currently hold a plain-text
ConfigMap containing Daniil's key and email address. Delete that block and change the volume
(lines 145–147) from:

```yaml
  - name: ssh-pubkey
    configMap:
      name: ssh-pubkey
```

to:

```yaml
  - name: ssh-pubkey
    secret:
      secretName: ssh-pubkey
      defaultMode: 0400
```

The Secret is created once, out of band, and never committed:

```bash
kubectl create secret generic ssh-pubkey \
    --from-file=authorized_keys=$HOME/.ssh/id_ed25519.pub \
    --namespace ${K8S_NAMESPACE}
```

The startup script's `cp /etc/ssh-init/authorized_keys /root/.ssh/authorized_keys` (line 57) keeps
working unchanged, since a Secret volume mounts at the same path. A public key is not secret
material, but keeping it out of a committed manifest removes a personal identifier from the repo and
makes the manifest reusable by anyone on the team.

**10b — CPU and memory requests are left alone.** The manifest keeps its current 16 vCPU / 128 GiB
request; Daniil tunes the node size manually at run time. `--n-workers` in the run command must be
chosen to match whatever node is actually provisioned (see the runtime table).

**10c — thread pinning.** Add `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1` to
the container `env` block. With many concurrent workers, unpinned BLAS threads oversubscribe the
node and can cost more than the parallelism gains. This is independent of the node size.

**10d — PVC headroom** for the 12.8 GB reference cache: confirm the `fl-workspace` PVC has room
before the run, and document the cache path in the README.

**10e — README** (`harmonization-metrics/README.md`): replace the "Add your public key to the
ConfigMap" step (Step 2) with the `kubectl create secret` command.

### 11. `harmonization-metrics/CLAUDE.md`

**11a — Metric-groups table, after line 149** (`K — NA retention`): three new rows.

| Group | Key metrics | Speed | Default |
|---|---|---|---|
| L — Marker correlation | `mk_rho_mean_all_genes`, `mk_rho_by_gene`, `mk_rho_marker_minus_hk` | Fast; **needs the raw reference** | Yes |
| M — Cross-batch rank agreement | `xb_rank_agree`, `xb_rank_agree_ratio` | Moderate; single matrix | Yes |
| N — Predictive validation | `pv_lobo3_f1_macro_mean`, `pv_lobo2_auc_macro_mean`, `*_perm_*` | Slow (~5–6 min/job) | Yes |

**11b — line 153, "Default active set".** Before:

```
**Default active set:** `ABCDEFGHIJK`. Group F is skipped with `--skip-slow`; Group I is skipped with `--skip-wm`.
```

After:

```
**Default active set:** `ABCDEFGHIJKLMN`. Group F is skipped with `--skip-slow`; Group I is skipped
with `--skip-wm`.

Groups **L, M, N** are the blind final check. They live in the same JSON sidecars and the same
`metrics_comprehensive.csv` as A–K, but they are **excluded from `scoring_cols`** and therefore from
the Figure 3 clustermap and the composite score — enforced by the `mk_`/`xb_`/`pv_` prefix filter
and an assertion in `figures_helpers.load_metrics_data()`. Do **not** add them to `_GROUP_MAP`.

**Group L** requires the raw reference `exp/{strat}__{imp}__01_raw__post0.tsv.gz`, cached locally per
`(strat, imp)` — 42 pairs for 2,323 jobs. **Groups M and N need no reference:** `01_raw` is itself an
attempt, so the unharmonized baseline is obtained in the notebook by joining on `(strat, imp)`
(`figures_helpers.attach_raw_baseline()`).
```

**11c — File-roles table, after line 86:** rows for `marker_gene_annotation.csv`,
`marker_panels.py`, `correlation_prediction_metrics_analysis.ipynb`.

**11d — `compute_batch_metrics.py` row** (line 79): `11 metric group functions` → `14 metric group
functions (A–N)`.

**11e — S3 layout block, after line 132:** add the three long-format CSVs and the optional
`marker_corr/` prefix. `metrics/` and `metrics_comprehensive.csv` keep their existing lines — the
new metrics go **into** them.

**11f — Commands section:** an L/M/N run block (see Verification).

**11g — Memory Guidelines table:** an `L/M/N` row — ~3–4 GB peak per worker (job matrix + reference
for L + one 412 MB rank-correlation matrix for M), `--memory-limit-gb 8.0`. Worker count is
CPU-bound and should be set to roughly (vCPU − 8) on whatever node is provisioned.

**11h — Key design patterns → "Incremental computation":** note that L/M/N are the third use of
this mechanism (after J, K, I) and that the reference download happens only when Group L is
requested.

**11i — Pod Operations:** replace the ConfigMap key step with the Secret command.

### 12. `FL_harmonization/CLAUDE.md`

**12a — Commands, after line 53:** the L/M/N invocation.

**12b — line 102.** Before: `Core library: 11 metric group functions + compute_all_metrics()`.
After: `Core library: 14 metric group functions (A–N) + compute_all_metrics(); L/M/N excluded from
the clustermap`.

**12c — Key Files table, after line 103:** rows for `marker_gene_annotation.csv`,
`harmonization-metrics/marker_panels.py`,
`harmonization-metrics/correlation_prediction_metrics_analysis.ipynb`.

**12d — Dataset section:** correct the sample count to **7,174** assembled / 5,444 analysis set, and
note that the prepared S3 annotation is the source of truth.

**12e — "Next steps — Article 1":** add the L/M/N compute run and the analysis notebook. The
manuscript sub-chapters are deferred (§14) and recorded in project memory instead.

**12f — Infrastructure → K8s metrics pod:** note the SSH Secret. Leave the stated pod size as is —
Daniil tunes it manually.

### 13. `project_overview.md`

**13a** — new subsection "Blind final check (Groups L, M, N)": definitions, the run scope
(2,323 non-Shambhala attempts), the reference-matrix rule for Group L on post-removal runs, the fact
that M and N are single-matrix and get their baseline from the `01_raw` attempts in the notebook,
the L ceiling caveat, the over-correction margin in M, the fold rules in N, and an explicit
statement that the ~65 new keys are excluded from the 87 scoring metrics and from the hierarchy
A > B > J > K.

**13b** — correct the sample count to 7,174 wherever it is quoted from the 7,238-row file
(line 386 already says 7,174 — verify the rest of the document agrees).

### 14. Article edits — DEFERRED, not part of this implementation

Daniil's instruction: the manuscript sub-chapters must wait until the metric results exist. **Do not
touch `figures_for_article/FL_harmonization_article_NAR_260802_manually_edited.docx` as part of this
plan.**

The queued edits — two new RESULTS Heading 2 sections, the METHODS additions, Supplementary File 5
registration and the Figure 5/6 renumbering — are recorded in project memory as
`project_manuscript_lmn_sections_deferred.md`, together with the rule that they must be applied via
the `nar-review` skill's citation-safe `safe_tracked_replace` (plain `tracked_replace` destroys the
Mendeley `w:sdt` citations). Revisit only after Daniil has reviewed the results and says to proceed.

---

## Files that do NOT need to change

| File | Why not |
|---|---|
| `figures_for_article/FL_harmonization_article_NAR_260802_manually_edited.docx` | Manuscript work is deferred until the results exist (§14); tracked in project memory. |
| `harmonization_metrics_analysis_v3.ipynb` | Figure 3 and the composite score must not change. The prefix filter in `figures_helpers.py` keeps `scoring_cols` at 87, and Verification step 8 asserts it. Optional cosmetic follow-up: point the inline `FL_2025_MARKERS` cell at `marker_panels.py`. |
| `harmonization_metrics_visual_inspection.ipynb` | Exploration only. |
| `metric_tables/metrics_comprehensive_260609.csv` | Kept as the frozen copy behind Supplementary File 3. The L/M/N run produces a **new** dated copy; the old one is not overwritten. |
| `requirements.txt` | All dependencies present: `scikit-learn>=1.3` (`LogisticRegression`, `PCA`, `StandardScaler`, `f1_score`, `roc_auc_score`, `balanced_accuracy_score`, `matthews_corrcoef`), `scipy>=1.9` (`rankdata`), `pandas`, `numpy`. **No requirements/ConfigMap sync needed** — only the env and SSH-volume parts of the pod YAML change. |
| `k8s/pod-metrics.yaml` resource requests | Left at 16 vCPU / 128 GiB; Daniil tunes the node manually (§10b). |
| `harmonization-scripts/*` | No new strategies, methods or imputations. The harmonized matrices on S3 are inputs, unchanged. |
| `shambhala_adoption/*` | Shambhala is excluded from Article 1; its 1,512 attempts are opt-in. |
| `Supplementary File 3.csv` | Remains the authoritative A–K metrics table; the blind check is Supplementary File 5. |
| `run_metrics_concat.py` wide-CSV schema for A–K | Existing columns keep their names and positions; only nested-dict handling and the three extra long CSVs are added. |

---

## Runtime estimate — measured 2026-08-19

Two real jobs were run end-to-end against S3, so these are measurements, not projections.
Single-threaded timings taken with `OMP_NUM_THREADS=1`, matching how the pod runs each worker.

**Worst case** — `S0_no_removal / strict / 16_fsqn_r`, the full 7,174-sample cohort, 24 folds,
100 permutations:

| Step | 4 threads | 1 thread | Note |
|---|---|---|---|
| Download + parse harmonized matrix | 10 s | 10 s | far cheaper than the 50 s assumed |
| Raw reference (Group L) | 49 s on a cache miss | 5 s on a cache hit | 42 pairs, so 2,281 of 2,323 jobs hit the cache |
| Group L | 0.1 s | 0.1 s | |
| Group M | 1.8 s | 1.8 s | one block-wise 7,174² rank correlation |
| Group N | 164 s | 243 s | dominates; 24 per-fold PCAs plus 4,800 logistic fits |
| **Total compute** | **166 s** | **245 s** | |
| **Wall per job, cache hit** | ~3.0 min | **~4.5 min** | |

**Cheaper case** — `K_ffpe_only / softimpute / 04_sva`, 3,000 samples, 8 folds: 14 s compute at
5 permutations. Group N scales with folds × samples, so the smaller strategies cost far less than
the worst case; **~3.5 min per job is a fair average** across the 2,323 attempts.

| Provisioned node | `--n-workers` | Wall time (100 perms) |
|---|---|---|
| 16 vCPU (current manifest) | 8 | ~17 h |
| 32 vCPU | 24 | ~5.7 h |
| **48 vCPU** | **40** | **~3.4 h** |
| 48 vCPU, incl. Shambhala (3,835 jobs) | 40 | ~5.6 h |

Peak RAM per worker ~3–4 GB, so 40 workers need ~160 GB. Worker count is CPU-bound.
`OMP_NUM_THREADS=1` (§10c) is what makes a high worker count behave.

Recommendation: **48 vCPU, 100 permutations, non-Shambhala — about 3.5 hours.** The
`--n-perm 10` fallback is no longer needed and should not be used: at 100 permutations the
empirical p-value floor is 1/101 = 0.0099, whereas 10 permutations floors it at 0.091, which is
not significant at any conventional threshold. The measured worst-case job is 4.5 min, well
inside the 1800 s timeout.


## Verified on real data (2026-08-19)

Two production jobs were run end-to-end against S3. Both merged into their existing sidecars
(227 A–K keys preserved, 296 keys after), confirming the incremental path.

| | `S0_no_removal / strict / 16_fsqn_r` | `K_ffpe_only / softimpute / 04_sva` |
|---|---|---|
| Samples / panel genes resolved | 7,174 / **108** | 3,000 / **275** |
| Group L mean ρ | **0.992** | **0.712** |
| Group L marker − housekeeping | **−0.004** | **+0.225** |
| Group M margin (`xb_rank_agree_ratio`) | +0.038 | **+0.093** |
| Group N 3-class macro-F1 | 0.504 | **0.877** |
| Group N AUC (multi-class folds) | 0.873 | 0.806 |
| Folds / multi-class folds | 24 / 11 | 8 / 3 |
| Permuted F1 → empirical p | 0.281 → **0.0099** | 0.396 → 0.167 (5 perms only) |

Three things this establishes:

1. **The Group L ceiling is real and now demonstrated on production data.** FSQN R sits at
   ρ = 0.992 with a marker-minus-housekeeping contrast of −0.004 — it is a quantile mapping that
   largely preserves within-cohort ranks, so Group L cannot distinguish it from doing nothing.
   SVA, which removes latent factors and therefore reorders samples, scores ρ = 0.712 with a
   **+0.225** marker-over-housekeeping margin. That contrast is the informative statistic, exactly
   as the plan predicted, and it is why Group M carries the conclusion.
2. **The fold rules behave as specified.** In the SVA job, five FFPE batches are single-diagnosis:
   each contributes an F1 (0.98–1.00) and `auc: None`, and `n_folds_multiclass` (3) is well below
   `n_folds` (8). Quoting the AUC mean without the fold counts would be misleading, which is why
   both are reported.
3. **100 permutations are necessary, not optional.** The empirical p-value floor is
   1/(n_perm + 1): 0.0099 at 100 permutations, but 0.167 at the 5 used in the quick test and 0.091
   at 10. The `--n-perm 10` fallback would make the negative control unable to reach significance.

Also verified: `--groups M` performs **zero** reference I/O — a clean run on
`G_affymetrix_only / strict / 17_quantile` downloaded only its own matrix and finished Group M in
0.3 s.

**Four production sidecars were written during testing** and carry partial L/M/N ahead of the
full run. Metrics merge rather than replace, so no A–K data was lost (227 keys preserved in every
case), but two need attention before the results are quoted:

| Sidecar | Groups written | `pv_n_perm` | Action |
|---|---|---|---|
| `S0_no_removal__strict__16_fsqn_r__post0` | L, M, N | 100 | none — production-grade |
| `K_ffpe_only__softimpute__04_sva__post0` | L, M, N | **5** | **must be recomputed at 100** |
| `K_ffpe_only__strict__01_raw__post0` | M only | — | none — the full run fills L and N |
| `G_affymetrix_only__strict__17_quantile__post0` | M only | — | none — the full run fills L and N |

The M-only rows self-heal: their L and N sentinels are absent, so the full run computes them. The
`K_ffpe_only / softimpute / 04_sva` row does **not** self-heal — its N sentinel is set, so the
incremental logic will skip it and leave a 5-permutation row in a 100-permutation table, where the
empirical p-value floor is 0.167 instead of 0.0099. Two safeguards:

1. Before the full run, clear that row's `pv_*` keys (or delete the sidecar's L/M/N keys so all
   three are recomputed).
2. `§1` of the analysis notebook now checks `pv_n_perm` across all attempts and prints a warning
   listing the counts if they are not uniform, so a stale row cannot pass unnoticed.

---

## Side effects and caveats

1. **Statistical ceiling of Group L.** Per-batch monotone transforms score ~1.0 by construction.
   Group M is the discriminative statistic. The article must say this; a near-1.0 L presented as
   evidence of quality would be a claim without proof.
2. **Group M's margin, not its raw value, is the answer.** A method that collapses all samples
   toward one profile raises `xb_rank_agree` too. `xb_rank_agree_ratio` — the same-biology minus
   different-biology margin, computed **within** the one matrix — is the number to quote. Because it
   needs no raw comparison, it is available for every attempt independently.
3. **Group M and N baselines are formed in the notebook, not in the job.** `01_raw` attempts are
   rows in the same table, so `attach_raw_baseline()` supplies `*_raw` and `*_delta` columns. If an
   `01_raw` row is ever missing for some `(strat, imp)`, those deltas are `NaN` and flagged by
   `baseline_missing` rather than silently zero.
4. **Post-removal baseline is approximate.** The baseline is always `01_raw__post0`, so a `post1`
   row is compared against a different sample set (post-removal drops method-specific outlier
   batches). `xb_rank_agree` and the predictive scores are means over pairs and folds rather than
   sample-matched statistics, so the comparison holds, but post0 and post1 must be reported
   separately and post1 deltas labelled approximate.
5. **Group L's reference rule is exact, unlike the above.** L intersects the reference down to the
   job's own sample index, so a `post1` job's correlations use exactly the post-removal-surviving
   samples on both sides. `01_raw__post1` must never be used as the reference.
6. **Post-removal circularity in Group N.** Post-removal is supervised by `RNA_BATCH`, so a `post1`
   leave-one-batch-out score is partly circular and the two variants must be reported separately
   and never averaged. Both are computed in full.
7. **Marker coverage — measured.** Of the 288 panel genes, **108 are present in all 42
   `(strat, imp)` pairs**, 168 in some, 12 in none. Coverage is strategy-dependent: a real
   `strict` job resolved **108** genes, a real `softimpute` job **275** (95 % of the panel).
   Per-gene nulls are expected and are the point; the notebook averages only the 108 genes
   complete across all attempts and reports how many were dropped.
8. **Housekeeping control is a contrast, not an absolute floor.** Its ρ collapses only for methods
   that actually reorder samples; monotone per-batch methods keep it at ~1.0.
9. **Confounded folds are kept on purpose.** Single-diagnosis batches (e.g. `GPL14951_FFPE_Unknown`
   = 810 DLBCL) contribute to F1 but not to AUC. `n_folds` and `n_folds_multiclass` accompany every
   mean; without them the numbers are not interpretable.
10. **Group N does not impute.** If a harmonized matrix contains NAs, the affected genes and samples
    are dropped and counted, never filled. `pv_n_genes_dropped_na` / `pv_n_samples_dropped_na` should
    be 0 for every attempt; a nonzero value means that attempt's predictive score rests on a smaller
    feature set and is not directly comparable.
11. **Metrics table grows by ~63 scalar columns.** Measured on a real job: 227 keys before,
    296 after, of which 6 are nested dicts split into the long tables. `scoring_cols` must stay at
    **87** and `df_ok` at **2,234** rows — asserted in Verification step 8 and in the notebook's
    §1 guard, both of which pass. Downstream code that assumes a fixed column count should be
    checked.
12. **Six new keys are nested dicts** and must not reach the wide CSV: `mk_rho_by_gene`,
    `mk_rho_n_cohorts_by_gene`, `mk_rho_by_cohort`, `xb_rank_agree_by_diagnosis`, `pv_lobo3_folds`,
    `pv_lobo2_folds`. Without §6a they would appear as stringified dicts.
13. **Reference cache is 12.8 GB on the PVC** and must be purged manually if `01_raw` outputs are
    ever regenerated — a stale cache would silently compare against the wrong reference. §4c logs
    the S3 `ETag` on a cache hit so a mismatch is visible in the log.
14. **The permutation control may not fully collapse.** If permuted-label macro-F1 stays well above
    chance, that means the label collapse is confounded with batch (a batch that is 100 % DLBCL),
    not a bug. Report it rather than tuning it away.
15. **`--skip-if-exists` must NOT be used for this run.** Every target job already has a sidecar, so
    `--skip-if-exists` would skip all 2,323. The incremental sentinel logic is what provides the
    resume behaviour here; use `--groups L,M,N` without `--skip-if-exists`.
16. **`--n-workers` must match the provisioned node.** The manifest no longer encodes the node size,
    so the run command carries that decision.
17. **Figma quota.** ~15 MCP calls per session on the Starter plan. Read the reference frames once
    at the start of Phase 5 and persist the layout to
    `figures_for_article/correlation_prediction_figure_layout_260819.md`.
18. **Reproducibility.** `RANDOM_SEED = 260819` and the actual `pv_n_perm` are written into every
    sidecar, so the manuscript can state both when it is eventually written.

---

## Verification commands

```bash
source ~/venvs/collagen_3_11/bin/activate
cd ~/FL_harmonization/harmonization-metrics

# 1 — Smoke tests (synthetic data, no S3): A-K regression plus the 17 new L/M/N tests
python test_mock_metrics.py

# 2 — Gene annotation table loads and resolves against the real strict gene set
python -c "
import pandas as pd
from marker_panels import load_marker_annotation, panel_genes, resolve_panel
ann = load_marker_annotation()
print(ann.shape); print(ann['gene_group'].value_counts().to_string())
print(ann['cell_type'].value_counts().to_string())
g = set(pd.read_csv('$FL_DATA_ROOT/fsqn_normalized_exp_R.tsv',
                    sep='\t', nrows=1, index_col=0).columns)
ok, miss = resolve_panel(g, panel_genes(include_housekeeping=True))
print(f'panel {len(ann)} -> resolved {len(ok)}, missing {len(miss)}'); print(sorted(miss))
"

# 3 — Per-gene coverage across all 42 (strat, imp) pairs  [Phase 0 audit]
python -c "
import boto3, json, collections
from marker_panels import panel_genes
s3 = boto3.client('s3'); B = '$FL_S3_BUCKET'
pg = s3.get_paginator('list_objects_v2')
pairs = set()
for page in pg.paginate(Bucket=B, Prefix='FL_batch_correction/genes/'):
    for o in page.get('Contents', []):
        p = o['Key'].split('/')[-1].split('__')
        if len(p) == 4 and p[2] == '01_raw':
            pairs.add((p[0], p[1]))
cnt = collections.Counter()
for s, i in sorted(pairs):
    k = f'FL_batch_correction/genes/{s}__{i}__01_raw__post0_genes.json'
    try:
        genes = set(json.loads(s3.get_object(Bucket=B, Key=k)['Body'].read()))
    except Exception:
        continue
    for g in panel_genes(include_housekeeping=True):
        cnt[g] += g in genes
print(f'pairs audited: {len(pairs)}')
for g, n in sorted(cnt.items(), key=lambda x: -x[1]):
    print(f'{g:10s} {n}/{len(pairs)}')
"

# 4 — Profiling sample: 20 jobs, measure the real per-job time before committing to the full run
python run_metrics_parallel.py \
    --groups L,M,N --only-with-metrics --skip-shambhala \
    --strats C_rnaseq_only,K_ffpe_only --imps softimpute \
    --n-workers 4 --memory-limit-gb 8.0 --timeout-s 1800 \
    --ref-cache-dir /workspace/ref_cache

# 5 — Single job, inspect every new key
python run_metrics_job.py \
    --strat C_rnaseq_only --imp softimpute --method 04_sva --post-rm False \
    --out-json /tmp/test_lmn.json --out-genes-json /tmp/test_genes.json \
    --groups L,M,N --ref-cache-dir /workspace/ref_cache

python -c "
import json; d = json.load(open('/tmp/test_lmn.json'))
for k in ['status','mk_rho_mean_all_genes','mk_rho_mean_markers','mk_rho_mean_housekeeping',
          'mk_rho_marker_minus_hk','mk_n_panel_genes_used','mk_is_self_reference',
          'xb_rank_agree','xb_rank_disagree_diffbio','xb_rank_agree_ratio','xb_n_pairs_same_bio',
          'pv_lobo3_f1_macro_mean','pv_lobo3_auc_macro_mean','pv_lobo3_n_folds',
          'pv_lobo3_n_folds_multiclass','pv_lobo3_f1_macro_perm_mean','pv_lobo3_f1_perm_pvalue',
          'pv_lobo2_f1_macro_mean','pv_lobo2_auc_macro_mean','pv_n_perm',
          'pv_n_genes_dropped_na','pv_n_samples_dropped_na']:
    print(f'{k:34s} {d.get(k)}')
print('per-gene entries:', len(d.get('mk_rho_by_gene') or {}))
print('A-K preserved:', d.get('r2_RNA_BATCH') is not None, d.get('n_genes_noNA') is not None)
"

# 5b — Groups M and N alone must do NO reference I/O
python run_metrics_job.py \
    --strat C_rnaseq_only --imp softimpute --method 10_mnn --post-rm False \
    --out-json /tmp/test_mn.json --out-genes-json /tmp/test_genes2.json \
    --groups M,N 2>&1 | grep -c "01_raw"      # must print 0

# 6 — Full run: 2,323 non-Shambhala attempts. Set --n-workers to match the provisioned node.
#     NOTE: no --skip-if-exists — every job already has a sidecar; the sentinel logic resumes.
nohup python run_metrics_parallel.py \
    --groups L,M,N --only-with-metrics --skip-shambhala \
    --n-workers 40 --memory-limit-gb 8.0 --timeout-s 1800 \
    --n-perm 100 --ref-cache-dir /workspace/ref_cache \
    > /workspace/metrics_lmn.log 2>&1 &

# 7 — Aggregate: wide CSV plus the three long CSVs
python run_metrics_concat.py --out-csv metric_tables/metrics_comprehensive_260819.csv

# 8 — Prove the clustermap input is unchanged after the new columns land
python -c "
import sys; sys.path.insert(0, '../figures_for_article')
from figures_helpers import load_metrics_data
df_ok, df_normed, scoring_cols, col_meta = load_metrics_data(
    'metric_tables/metrics_comprehensive_260819.csv')
assert df_ok.shape[0] == 2234, df_ok.shape
assert len(scoring_cols) == 87, len(scoring_cols)
leaked = [c for c in scoring_cols if c.startswith(('mk_','xb_','pv_'))]
assert not leaked, leaked
# The '?' group pre-exists (a few A-K columns do not match _GROUP_MAP); what matters is
# that no blind-check column reached col_meta at all.
assert not [c for c in col_meta.index if c.startswith(('mk_','xb_','pv_'))]
print('clustermap input unchanged: 2234 rows x 87 scoring metrics')
"

# 9 — Long tables, gene completeness, and baseline attachment all work
python -c "
import sys; sys.path.insert(0, '../figures_for_article')
from figures_helpers import (load_new_metrics_data, filter_genes_complete_across_attempts,
                             attach_raw_baseline)
df_lmn, gene_long, cohort_long, folds_long, mk, xb, pv = load_new_metrics_data()
print('L/M/N wide:', df_lmn.shape, '| mk:', len(mk), 'xb:', len(xb), 'pv:', len(pv))
print('gene_long:', gene_long.shape, '| cohort_long:', cohort_long.shape,
      '| folds_long:', folds_long.shape)
complete = filter_genes_complete_across_attempts(gene_long)
print(f'genes complete across all attempts: {len(complete)}')
df_b = attach_raw_baseline(df_lmn, metrics=['xb_rank_agree', 'pv_lobo3_f1_macro_mean'])
print('baseline missing rows:', int(df_b['baseline_missing'].sum()))
print(df_b[['xb_rank_agree','xb_rank_agree_raw','xb_rank_agree_delta']].describe().to_string())
"

# 10 — Pod: the SSH key is no longer in the manifest
grep -c "ssh-ed25519" k8s/pod-metrics.yaml    # must print 0
kubectl get secret ssh-pubkey -n ${K8S_NAMESPACE} -o name
```

### Pre-run sidecar cleanup

Groups L and M are both panel-dependent, so every sidecar written before the 2026-08-20 panel
rebuild holds numbers computed against the old 288-gene panel. The worker's incremental logic
skips a group whose sentinel key is already set, so those values would survive the full run and
silently mix two panels in one table. Four sidecars are affected — the two profiling jobs (`mk_`,
`xb_`, `pv_`) and two `--groups M`-only jobs (`xb_` alone). `pv_*` does not depend on the panel,
but `K_ffpe_only__softimpute__04_sva__post0` still needs it cleared because it was computed at
`n_perm = 5`.

```bash
python - <<'PYCLEAN'
import boto3, json
s3 = boto3.client("s3")
BUCKET = "$FL_S3_BUCKET"
STALE = {
    "S0_no_removal__strict__16_fsqn_r__post0":        ("mk_", "xb_"),
    "K_ffpe_only__softimpute__04_sva__post0":         ("mk_", "xb_", "pv_"),
    "G_affymetrix_only__strict__17_quantile__post0":  ("xb_",),
    "K_ffpe_only__strict__01_raw__post0":             ("xb_",),
}
for run_id, prefixes in STALE.items():
    key = f"FL_batch_correction/metrics/{run_id}_metrics.json"
    d = json.loads(s3.get_object(Bucket=BUCKET, Key=key)["Body"].read())
    kept = {k: v for k, v in d.items() if not k.startswith(prefixes)}
    print(f"{run_id}: {len(d)} -> {len(kept)} keys")
    s3.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(kept).encode())
PYCLEAN
```

Re-run the size scan afterwards to confirm no sidecar is still an outlier: any sidecar carrying
`mk_`/`xb_` keys is far larger than the ~9.8 KB A-K baseline, which is how these four were found.

---

## TODO

### Phase 0 — gene annotation table and coverage audit
- [x] Extract the LME / TME signature genes from Kotlov et al. 2021 (PMC8178179) supplementary tables — `kotlov_fges_blocks()` reads the 22 gene-based FGES from Table S1 and `kotlov_classifier_blocks()` reads the COO and DHIT panels from Tables S2/S3, all marked `kotlov_table_s1`
- [x] Extract the GC B-cell state signatures from Holmes et al. 2020 (JEM 217(10):e20200483) — `holmes_gc_state_blocks()` reads the 13 per-cluster up-regulated lists from Table S2, top 20 by log2 fold change, marked `holmes_table_s2`. Tables S3/S4 are truncated downloads and unreadable; not needed, see "Resolved — final panel"
- [x] Lift `FL_2025_MARKERS`, `LEGACY_GC_MARKERS`, `FL_PROG_SIGNATURES`, `FL_PATHWAY_GENES` out of `insert_cells.py:1611–1657`
- [x] Assemble `marker_gene_annotation.csv` with all nine columns, including `CLINICAL_IHC_MARKERS` and the housekeeping group
- [x] NEW `marker_panels.py` — `load_marker_annotation()`, `panel_genes()`, `GENE_ALIASES`, `resolve_panel()`, `panel_summary()`
- [x] Run the per-gene coverage audit across all 42 `(strat, imp)` pairs (Verification step 3) — output in `marker_gene_coverage_audit_260819.csv`, re-run 2026-08-20 against the rebuilt 548-gene panel
- [x] Record the coverage table in this plan under "Resolved — final panel"
- [ ] Daniil signs off on the final gene table *(rebuilt from the supplementary files 2026-08-20; the `HOLMES_TOP_N_UP = 20` truncation and the two annotation judgements need his call)*

### Phase 1 — metric library (`compute_batch_metrics.py`)
- [x] Module docstring — groups L, M, N; note that only L needs a raw reference (3a)
- [x] New constants block: `RANDOM_SEED`, `N_PERM`, `MIN_COHORT_N`, `MIN_TEST_N`, `N_PCS`, `XB_MAX_SAMPLES`, `PRED_CLASS_COL`, `PRED_BIO_COL` (3b)
- [x] New imports: `LogisticRegression`, sklearn metrics, `rankdata`, `marker_panels` (3c)
- [x] Helpers: `_collapse_diagnosis`, `_rank_matrix`, `_corr_from_ranks`, `_pairwise_masks`, `_fold_pca_projections`, `_fit_eval_fold`, `_safe_auc` (3d)
- [x] `compute_group_l()` — per-gene per-cohort Spearman, per-gene dict + aggregates (3e)
- [x] `compute_group_l()` — marker vs housekeeping contrast keys
- [x] `compute_group_l()` — coverage and provenance keys incl. `mk_is_self_reference`
- [x] `compute_group_m()` — signature without `ref_df`; single-matrix rank-correlation (3f)
- [x] `compute_group_m()` — same-biology and different-biology masks, `xb_rank_agree_ratio`
- [x] `compute_group_m()` — `xb_rank_agree_by_diagnosis`
- [x] `compute_group_m()` — stratified subsampling above `XB_MAX_SAMPLES`
- [x] `compute_group_n()` — cached per-fold train-only PCA projections (3g)
- [x] `compute_group_n()` — NA genes/samples dropped and counted, **no imputation**
- [x] `compute_group_n()` — N1 3-class leave-one-batch-out; F1 all folds, AUC multi-class folds only
- [x] `compute_group_n()` — N2 FL-vs-DLBCL on the same folds and cached PCA
- [x] `compute_group_n()` — N3 permutation control, 100 perms reusing the cached PCA, empirical p-value
- [x] `compute_all_metrics()` — new `ref_df`, `n_perm`, `panel` parameters (3h)
- [x] `compute_all_metrics()` — active-set literal `ABCDEFGHIJK` → `ABCDEFGHIJKLMN` and docstring valid-values list (3i)
- [x] `compute_all_metrics()` — `_run_group` calls for L, M, N with the corrected argument lists (3j)
- [x] `compute_all_metrics()` — missing-reference guard that skips **L only** (3k)

### Phase 2 — pipeline
- [x] `run_metrics_job.py` — three new `GROUP_SENTINEL_KEYS` entries, `M` → `xb_rank_agree` (4a)
- [x] `run_metrics_job.py` — `_s3_key_ref_exp()` helper (4b)
- [x] `run_metrics_job.py` — reference download with the `(strat, imp)` local cache and ETag logging (4c)
- [x] `run_metrics_job.py` — reference alignment to the already aligned `exp_df` / `ann_df` (4d)
- [x] `run_metrics_job.py` — fetch the reference only when `"L" in groups_to_run` (4e)
- [x] `run_metrics_job.py` — new flags `--ref-cache-dir`, `--n-perm`, `--save-gene-cohort-detail`, `--panel-groups` (4f)
- [x] `run_metrics_job.py` — default requested-groups literal `ABCDEFGHJK` → `ABCDEFGHJKLMN` (4g)
- [x] `run_metrics_job.py` — extend exit code 3 to a missing reference when **L** requested (4h)
- [x] `run_metrics_parallel.py` — `--groups` help text valid-values list (5a)
- [x] `run_metrics_parallel.py` — forward the four new worker flags (5b)
- [x] `run_metrics_parallel.py` — `--skip-shambhala` (5c)
- [x] `run_metrics_parallel.py` — `--only-with-metrics` (5d)
- [x] `run_metrics_parallel.py` — docstring L/M/N usage block and timeout guidance (5e, 5f)
- [x] `run_metrics_concat.py` — drop the six nested dict values from the wide CSV (6a)
- [x] `run_metrics_concat.py` — pivot `xb_rank_agree_by_diagnosis` into wide columns (6b)
- [x] `run_metrics_concat.py` — emit `marker_gene_correlations_long.csv` (6b)
- [x] `run_metrics_concat.py` — emit `marker_cohort_correlations_long.csv` (6b)
- [x] `run_metrics_concat.py` — emit `prediction_folds_long.csv` (6b)
- [x] `test_mock_metrics.py` — all 17 new L/M/N tests from the table in §7
- [x] Run `test_mock_metrics.py` — A–K regression plus the new tests all green
- [x] Format every edited file with Black (line length 88)

### Phase 3 — infrastructure
- [ ] Create the `ssh-pubkey` Secret out of band (10a) *(requires live cluster)*
- [x] `pod-metrics.yaml` — delete the plain-text SSH ConfigMap block (lines 1–10) (10a)
- [x] `pod-metrics.yaml` — switch the `ssh-pubkey` volume to `secret` with `defaultMode: 0400` (10a)
- [x] `pod-metrics.yaml` — add `OMP_NUM_THREADS` / `OPENBLAS_NUM_THREADS` / `MKL_NUM_THREADS` = 1 (10c)
- [ ] Confirm PVC headroom for the 12.8 GB reference cache (10d) *(requires live pod)*
- [x] `README.md` — replace the ConfigMap key step with the `kubectl create secret` command (10e)
- [ ] Re-apply the manifest and confirm SSH still works with the Secret-mounted key *(requires live cluster)*
- [x] *(Resource requests intentionally untouched — Daniil tunes the node manually)*

### Phase 4 — compute
- [x] Profiling: two real end-to-end jobs measured (`S0_no_removal/strict/16_fsqn_r` worst case, `K_ffpe_only/softimpute/04_sva`); see the Runtime section
- [x] Verify a `--groups M,N` run does no reference I/O (Verification step 5b) — gated by `GROUPS_NEEDING_REFERENCE`
- [x] Decide `--n-perm` — **100**. Measured worst case is 4.5 min/job, and 10 permutations would floor the empirical p-value at 0.091.
- [x] Single-job key inspection (Verification step 5) — 296 keys, all A-K preserved, all L/M/N present
- [ ] Set `--n-workers` to match the provisioned node
- [ ] **Before the full run:** clear the stale panel-dependent keys on the four sidecars that already carry them — see "Pre-run sidecar cleanup" below *(mutates S3; run it immediately before the full run)*
- [ ] Full run: 2,323 non-Shambhala attempts, `--groups L,M,N`, **without** `--skip-if-exists`
- [ ] Optional Shambhala extension (1,512 more jobs)
- [ ] `run_metrics_concat.py` → `metric_tables/metrics_comprehensive_260819.csv` + three long CSVs
- [ ] Optional `--save-gene-cohort-detail` re-run for the ~15 best approaches

### Phase 5 — analysis and figures
- [x] `figures_helpers.py` — `mk_`/`xb_`/`pv_` prefix filter in `metric_cols` (8a)
- [x] `figures_helpers.py` — assertion that no `scoring_cols` entry is a new-metric column (8b)
- [x] `figures_helpers.py` — comment stating `_GROUP_MAP` must not gain L/M/N (8c)
- [x] `figures_helpers.py` — `load_new_metrics_data()` (8d)
- [x] `figures_helpers.py` — `filter_genes_complete_across_attempts()` (8e)
- [x] `figures_helpers.py` — `attach_raw_baseline()` for the M and N before/after comparison (8f)
- [x] Verify 2,234 rows × 87 scoring metrics on the new CSV (Verification step 8)
- [ ] Read the Figma reference frames once; persist the layout to `correlation_prediction_figure_layout_260819.md` *(deferred: notebook uses GridSpec multipanel at 7.5 pt; refine against Figma when the real data exists, to spend the capped MCP quota on final layout)*
- [x] NEW `correlation_prediction_metrics_analysis.ipynb` — §1 setup, font size 7.5, gene-completeness report, baseline attachment
- [x] Notebook — §2 best vs rest for all seven headline metrics, with Mann-Whitney and effect size
- [x] Notebook — §3 Group L by `gene_group` and by `cell_type`, housekeeping as the control
- [x] Notebook — §4 Group L by individual gene: gene × approach heatmap + ranked lollipop
- [x] Notebook — §5 Group L coverage: `mk_n_panel_genes_used` and the per-gene presence matrix
- [x] Notebook — §6 Group M: raw→harmonized lineplot from `attach_raw_baseline()`, same-bio vs diff-bio, ratio, by diagnosis
- [x] Notebook — §7 Group N: F1 per approach vs raw baseline and permuted band, per-batch strip plot, 3-class vs 2-class, AUC with fold counts
- [x] Notebook — §8 permutation control: observed vs permuted distributions and p-values
- [x] Notebook — §9 Supplementary File 5 export
- [x] Notebook — label post1 deltas as approximate and report post0/post1 separately
- [x] Save every figure as PDF **and** SVG into `figures_for_article/current_figures_tables_for_article_260819/` (`save_figure()` now emits PDF + SVG + PNG)

### Phase 6 — documentation
- [x] `harmonization-metrics/CLAUDE.md` — metric-groups table: L, M, N rows (11a)
- [x] `harmonization-metrics/CLAUDE.md` — "Default active set" paragraph → `ABCDEFGHIJKLMN`, exclusion note, L-only reference note (11b)
- [x] `harmonization-metrics/CLAUDE.md` — file-roles rows for the annotation CSV, `marker_panels.py`, `correlation_prediction_metrics_analysis.ipynb` (11c)
- [x] `harmonization-metrics/CLAUDE.md` — `compute_batch_metrics.py` row: 11 → 14 metric groups (11d)
- [x] `harmonization-metrics/CLAUDE.md` — S3 layout: three long CSVs + optional `marker_corr/` (11e)
- [x] `harmonization-metrics/CLAUDE.md` — Commands: L/M/N run block (11f)
- [x] `harmonization-metrics/CLAUDE.md` — Memory Guidelines row, workers as a function of node size (11g)
- [x] `harmonization-metrics/CLAUDE.md` — Incremental-computation pattern note (11h)
- [x] `harmonization-metrics/CLAUDE.md` — Pod Operations: SSH Secret (11i)
- [x] `FL_harmonization/CLAUDE.md` — Commands block (12a)
- [x] `FL_harmonization/CLAUDE.md` — line 102: 11 → 14 metric groups (12b)
- [x] `FL_harmonization/CLAUDE.md` — Key Files rows (12c)
- [x] `FL_harmonization/CLAUDE.md` — Dataset section: 7,174 samples, prepared S3 annotation authoritative (12d)
- [x] `FL_harmonization/CLAUDE.md` — Article 1 next steps: compute run + notebook; manuscript deferred (12e)
- [x] `FL_harmonization/CLAUDE.md` — K8s metrics pod: SSH Secret note only, size unchanged (12f)
- [x] `project_overview.md` — "Blind final check (Groups L, M, N)" subsection (13a)
- [x] `project_overview.md` — verify every sample count says 7,174 (13b)
- [x] Fill the "Resolved — final panel" section of this plan with the Phase 0 result (rewritten 2026-08-20 after the supplementary-file rebuild)

### Deferred — manuscript (do not start)
- [ ] Manuscript sub-chapters, METHODS additions, Supplementary File 5 registration and Figure 5/6
      renumbering are **deferred until the results exist** (§14). Recorded in project memory as
      `project_manuscript_lmn_sections_deferred.md`. Revisit only on Daniil's explicit go-ahead.
