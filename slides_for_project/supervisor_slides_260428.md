# Supervisor Slides Plan — FL Harmonization Benchmark Progress
**Date:** 2026-04-28  
**Author:** Daniil Nikitin  
**Audience:** Scientific supervisor  
**Format:** ~23 slides, ~30 min presentation

---

## SLIDE 1 — Title

**Title:** Cross-Platform Transcriptomic Harmonization of B-Cell Lymphomas: Benchmark Progress  
**Subtitle:** Systematic evaluation of 25 batch-correction methods × 10 sample-removal strategies × 4 imputation approaches × 2 post-removal options  
**Author, date, affiliation**

---

## SLIDE 2 — Project Context (1 min)

**Title:** Research objective and why harmonization matters

**Content:**
- Central question: can SOM gene-expression patterns resolve FL transcriptomic subtypes, align them to normal GC B-cell states (LZ ↔ DZ), and predict clinical outcomes across mixed platforms?
- Data span: Affymetrix microarray, Illumina NGS, Illumina microarray, Agilent microarray — four fundamentally incompatible measurement technologies
- Problem magnitude: **~95% of PCA variance is explained by RNA_BATCH** (platform) in raw data — biology is entirely hidden
- Goal for harmonization: reduce batch R² below 20% while preserving biological signal (diagnosis, cell type)
- Metric used: one-way ANOVA R² of `RNA_BATCH` on first 10 PCA components (lower = better)

---

## SLIDE 3 — Dataset Overview

**Title:** Multi-platform cohort: ~5,444 samples, 88 cohorts

**Table: Dataset composition**

| Attribute | Value |
|---|---|
| Total assembled samples (initial) | 7,174 |
| After bad-batch / rare-group exclusion | **5,444** |
| Genes (full coverage, no NA) | **3,520** |
| Cohorts | 88 |
| Platforms | 4 |

**Table: Major RNA batches**

| RNA_BATCH | N | Platform |
|---|---|---|
| RNASeq_FF_PolyA | 1,039 | Illumina NGS ← **reference** |
| GPL570_Unknown_Unknown | 1,030 | Affymetrix |
| GPL570_FF_Unknown | 994 | Affymetrix |
| RNASeq_FFPE_Exome_capture | 939 | Illumina NGS |
| GPL14951_FFPE_Unknown | 810 | Illumina microarray |
| GPL570_FFPE_Unknown | 800 | Affymetrix |

**Diagnosis groups:**
- DLBCL: ~3,000 samples
- FL: ~2,000 samples
- Normal B cells (Normal_B_cells + Kassandra): ~1,000 samples
- Rare subtypes (MCL, DHL, MZL, CLL, Other): excluded before any analysis

---

## SLIDE 4 — Design Philosophy: Why a Full Cross-Product?

**Title:** Benchmark design: exhaustive cross-product of all methodological choices

**Key argument:**  
Each methodological dimension (sample exclusion strategy, imputation, normalization, post-normalization outlier removal) interacts with the others in non-obvious ways. A partial factorial design cannot identify the best combination. A full cross-product is the only way to:
1. Compare methods under identical data conditions (same samples, same genes)
2. Identify which method is most robust across imputation choices
3. Quantify the marginal effect of each dimension independently

**Dimensions:**

| Dimension | N options | Description |
|---|---|---|
| Sample-removal strategy | 10 | Which batches/cohorts to exclude before normalization |
| Imputation approach | 4 | How to handle missing genes |
| Normalization method | 25 | Batch-correction algorithm |
| Post-normalization outlier removal | 2 | With / without removing residual outlier batches |

**Total jobs:** 10 × 4 × 25 = **1,000** normalization runs → **2,000 output matrices** stored on S3  
**Metric per output:** one-way ANOVA R² (batch) + one-way ANOVA R² (diagnosis)

---

## SLIDE 5 — The 10 Sample-Removal Strategies

**Title:** Dimension 1 — Sample-removal strategies

**Table:**

| Key | Description | Samples | Rationale |
|---|---|---|---|
| `S0_no_removal` | All samples (after rare-group exclusion only) | ~6,000 | Baseline; maximum data |
| `A_confirmed_bad` | Exclude 3 confirmed FFPE microarray batches + SOM cohort | 5,444 | Removes known bad-quality batches |
| `B_extended_bad` | Exclude 11 batches + SOM cohort (superset of A) | ~4,700 | More aggressive known-bad removal |
| `C_rnaseq_only` | RNA-seq batches only | 2,386 | Removes cross-platform challenge entirely |
| `D_malignant_only` | Tumor samples only (no normal B cells) | 4,444 | Tests normalization without normal/tumor mixing |
| `E1_iterative_r1` | A + 1 data-driven PCA-outlier batch removed | 5,350 | Iterative PCA-based outlier detection round 1 |
| `E2_iterative_r2` | E1 + 1 more PCA-outlier batch removed | ~5,300 | Round 2 |
| `E3_iterative_r3` | E2 + 1 more PCA-outlier batch removed | 5,256 | Round 3 |
| `F_microarray_only` | Microarray batches only | 4,825 | Intra-platform normalization test |
| `G_affymetrix_only` | GPL570 batches only | 2,824 | Single-technology normalization test |

**Note:** E1–E3 are computed by running `identify_outlier_batches()` iteratively on the PCA-corrected data — the most computationally expensive preparation step.

---

## SLIDE 6 — The 4 Imputation Approaches

**Title:** Dimension 2 — Handling missing genes (imputation)

**Context:** Not all genes are measured in all platforms. In the raw dataset ~13,000 genes pass a 5,000-sample presence threshold; full-coverage genes (no NA) number only 3,520.

**Table:**

| Key | Method | Gene count (S0) | Missing-data assumption | Key limitation |
|---|---|---|---|---|
| `strict` | No imputation; drop all genes with any NA | ~3,520 | Complete case | Smallest gene space; zero NaN guarantee |
| `knn` | sklearn KNNImputer ([Troyanskaya et al. 2001](https://academic.oup.com/bioinformatics/article/17/6/520/272365), k=5); drop genes >20% NA | ~12,000 | MAR within neighborhood | Residual NaN for genes absent from entire batches (BEAMs) |
| `missforest` | R missForest ([Stekhoven & Bühlmann 2012](https://academic.oup.com/bioinformatics/article/28/1/112/219101), Random Forest) | — | MAR across all samples | **FAILED**: ran for >24 hours on 16 CPUs / 240 GB RAM; Kubernetes pod was killed with no restart |
| `softimpute` | R softImpute ([Hastie et al. 2015](https://jmlr.org/papers/v16/hastie15a.html), matrix completion) | ~11,000 | Low-rank MAR | Residual NaN when no low-rank signal; same BEAM limitation |

**Key methodological decision — `dropna` for residual NaN:**  
After KNN/softImpute, genes still missing are **BEAMs** ([Goh et al. 2023](https://doi.org/10.1093/bib/bbad055)) — absent from entire batches, MNAR by mechanism. Global median imputation of these genes:
- Creates artificial cross-batch homogenization
- Inflates intra-sample variance irreversibly ([Hui et al. 2023](https://doi.org/10.1038/s41598-023-35823-7): M1 imputation 21.3% higher RMSE vs within-batch)
- Biases ComBat/SVA EB priors
- Produces artificially lower PCA R² (apparent improvement that is an artifact)

**Decision:** `dropna(axis=1)` for residual NaN before all normalization methods except HarmonizR (which handles BEAMs internally by design).

**Literature support:** [Rubin 1976](https://doi.org/10.1093/biomet/63.3.581) (MNAR theory), [Goh et al. 2025](https://doi.org/10.1093/bib/bbae583) (*Briefings in Bioinformatics*): "none of the MVI methods evaluated are suitable for handling BEAMs effectively" — primary recommendation: remove severe BEAM features prior to imputation.

---

## SLIDE 7A — The 25 Normalization Methods (Part 1: methods 01–13)

**Title:** Dimension 3 — Batch-correction methods evaluated (1/2)

| # | Key | Algorithm family | R/Python | Harshness | Notes |
|---|---|---|---|---|---|
| 01 | `01_raw` | Passthrough | — | L | Absolute baseline |
| 02 | `02_median_scaling` | Per-batch median shift | Python | L | Simple, interpretable baseline |
| 03 | `03_limma` | Linear model (additive) | R | L | [`removeBatchEffect`](https://bioconductor.org/packages/limma/); classic microarray method |
| 04 | `04_sva` | Surrogate variable analysis | R | L | [Leek & Storey 2012](https://doi.org/10.1038/nmeth.2237); falls back to uncorrected if 0 SVs detected |
| 05 | `05_combat` | Empirical Bayes (ComBat) | R | M | [Johnson et al. 2007](https://doi.org/10.1093/biostatistics/kxj037); additive + multiplicative; biology covariate |
| 06 | `06_combat_seq` | ComBat-seq (NB counts) | R | M | [Zhang et al. 2020](https://doi.org/10.1093/nargab/lqaa078); designed for count data; rounds to integers |
| 07 | `07_pycombat` | ComBat Python port | Python | M | `combat` package |
| 08 | `08_inmoose_combatseq` | ComBat-seq Python port | Python | M | `inmoose.pycombat` |
| 09 | `09_ruv` | Factor analysis (RUVg) | R | M | [Risso et al. 2014](https://doi.org/10.1038/nbt.2931); 10 housekeeping negative-control genes |
| 10 | `10_mnn` | Mutual nearest neighbours | R | M | [Haghverdi et al. 2018](https://doi.org/10.1038/nbt.4091) fastMNN; corrected embedding inverse-projected |
| 11 | `11_harmony` | PCA-space clustering | Python | M | [Korsunsky et al. 2019](https://doi.org/10.1038/s41592-019-0619-0) Harmony; inverse-projected back to gene space |
| 12 | `12_scanorama` | Panoramic alignment | Python | M | [Hie et al. 2019](https://doi.org/10.1038/s41587-019-0113-3) Scanorama; gene intersection |
| 13 | `13_fsmvn` | Feature mean-variance norm. | Python | M | Negative control for distributional methods |

**Harshness tiers:** L = Low (minimal correction), M = Medium (parametric/subspace), H = High (distributional)

---

## SLIDE 7B — The 25 Normalization Methods (Part 2: methods 14–25)

**Title:** Dimension 3 — Batch-correction methods evaluated (2/2)

| # | Key | Algorithm family | R/Python | Harshness | Notes |
|---|---|---|---|---|---|
| 14 | `14_qsmooth` | Smooth quantile norm. | R | H | [Hicks et al. 2018](https://doi.org/10.1093/biostatistics/kxx028) qsmooth; group-aware quantile normalization |
| 15 | `15_fsqn_py` | FSQN Python re-impl. | Python | H | Per-gene quantile matching to reference batch |
| 16 | `16_fsqn_r` | FSQN R package | R | H | **★ Best known result; [Franks et al. 2018](https://doi.org/10.1093/biostatistics/kxx028)** |
| 17 | `17_quantile` | Standard quantile norm. | Python | H | [Bolstad et al. 2003](https://doi.org/10.1093/bioinformatics/19.2.185); forces single distribution |
| 18 | `18_rank` | Fractional rank | Python | H | Platform-independent; monotone transform |
| 19 | `19_tdm` | Training distribution match | R | H | [Thompson et al. 2016](https://doi.org/10.1371/journal.pone.0161551) |
| 20 | `20_shambhala` | CuBlock + quantile norm. | R+Octave | H | [Borisov 2022](https://doi.org/10.1093/bib/bbab458) Shambhala2; CuBlock |
| 21 | `21_harmonizr` | BEAM-aware ComBat/limma | R | M | [Voss et al. 2022](https://doi.org/10.1038/s41467-022-31214-6) HarmonizR; dissection-based; handles NA |
| 22 | `22_tmm` | TMM (edgeR) | R | L | [Robinson & Oshlack 2010](https://doi.org/10.1186/gb-2010-11-3-r25); RNA-seq only; skipped on mixed strategies |
| 23 | `23_vst` | DESeq2 VST | R | L | [Love et al. 2014](https://doi.org/10.1186/s13059-014-0550-8); RNA-seq only; skipped on mixed strategies |
| 24 | `24_peer_k10` | PEER hidden factors | — | M | Unavailable for R 4.5; always skipped |
| 25 | `25_angel` | Rank + platform-variance filter | Python | H | Reduced gene space; R² not directly comparable |

---

## SLIDE 8 — Known Results: Method Comparison (PCA R² Batch)

**Title:** Dimension 3 — Partial results table (A_confirmed_bad × strict)

*Note: This table is from pre-benchmark exploration runs (`harmonization_benchmark.ipynb`, pre-2026-04-19). The formal benchmark `metrics.csv` currently tracks E3-strategy results only. Full cross-product table pending all 1,000 jobs.*

**Table (best-known results, strategy A_confirmed_bad, imp=strict):**

| Method | R² batch (post0) | R² diag (post0) | Notes |
|---|---|---|---|
| `01_raw` (no normalization) | ~0.95 | — | Baseline; platform dominates |
| `03_limma` | ~0.45 | — | Partial; additive correction only |
| `05_combat` | ~0.35 | — | Better; EB + biology covariate |
| `07_pycombat` | ~0.35 | — | Comparable to ComBat |
| `11_harmony` | >0.95 | — | **Rejected** — worsened batch |
| `14_qsmooth` | ~0.48 | — | Partial; fails 12/88 cohorts |
| `15_fsqn_py` | ~0.20–0.25 | — | Good |
| `16_fsqn_r` | **~0.16** | ~0.09 | **Current best** |
| `17_quantile` | ~0.20 | — | Good; 5 batch outliers remain |
| `21_harmonizr` | ~0.10 | ~0.14 | Competitive (E3×softimpute result, `metrics.csv`) |

**How to read the metric columns:**
- **R² batch (post0)** — one-way ANOVA R² of `RNA_BATCH` on first 10 PCA components, *without* post-normalization outlier removal. This is the primary quality metric: fraction of PCA variance explained by platform/batch. Lower is better (target < 0.20).
- **R² diag (post0)** — same formula applied to `Diagnosis_cell_type_unified`. Measures biological signal preserved after normalization. Higher is better.

**Example row from `metrics.csv` (E3_iterative_r3 × softimpute × HarmonizR):**

| strat | imp | method | post_rm | r2_batch | r2_diag | n_samples | n_genes | status |
|---|---|---|---|---|---|---|---|---|
| E3_iterative_r3 | softimpute | 21_harmonizr | False | **0.099** | 0.141 | 5,256 | 15,226 | ok |

**Key findings so far:**
- FSQN R is the only method achieving R² < 0.20 on the full mixed-platform dataset with strategy A
- HarmonizR achieves R² ~0.10 on E3×softimpute (more samples retained + imputation expands gene space)
- Harmony made batch variance worse — an important negative result
- RNA-seq-only methods (TMM, VST) are automatically skipped on mixed strategies

*Full comparison heatmap (10 strategies × 25 methods) to be generated once all 1,000 jobs complete.*

---

## SLIDE 9 — Dimension 4: Post-Normalization Outlier Removal

**Title:** Dimension 4 — Post-normalization batch outlier removal

**What it does:**  
After applying a normalization method, identify batches whose centroid in PCA space is a >2σ outlier from the global mean, remove those samples, and recompute the matrix.

| Variant | Key suffix | Description |
|---|---|---|
| `post_rm=False` | `__post0` | Normalized output as-is |
| `post_rm=True` | `__post1` | Normalized output with outlier batches removed |

**Purpose:** Test whether residual outlier batches after normalization can be remediated by exclusion without re-normalizing. Adds a "second-chance" dimension to methods that partially correct but leave outlier batches.

**Examples from `logs/norm_log_e3_260428.txt` (E3_iterative_r3 × strict strategy):**

| Method | post0 R² | post1 R² | Batch removed | Effect |
|---|---|---|---|---|
| `19_tdm` | 0.548 | 0.518 | GPL1708_FF_Unknown | −0.030 — meaningful improvement |
| `09_ruv` | 0.383 | 0.380 | GPL1708_FF_Unknown | −0.003 — negligible |
| `06_combat_seq` | 0.336 | 0.337 | GPL1708_FF_Unknown | +0.001 — no improvement |
| `21_harmonizr` (strict) | 0.101 | 0.101 | GPL1708_FF_Unknown | 0 — already optimal |
| `21_harmonizr` (softimpute) | 0.099 | 0.099 | — | 0 — no outliers detected |

**Key observation:** post_rm consistently flags `GPL1708_FF_Unknown` (Illumina microarray batch) as the residual outlier across most methods on E3. For well-performing methods like HarmonizR, post_rm has no effect — the batch is already integrated.

---

## SLIDE 10 — Computational Pipeline Diagram

**Title:** Two-stage computational pipeline architecture

```
RAW DATA (S3)
  comb_exp.tsv (~1.9 GB, ~7,174 samples × ~50,000 genes)
  comb_ann_unified.csv (~7 MB)
         │
         ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  STAGE 1 — PREPARATION  (run_prep_parallel.py)              │
  │  40 jobs: 10 strategies × 4 imputation approaches           │
  │                                                              │
  │  For each (strategy, imputation) pair:                       │
  │                                                              │
  │  load_data()            build_filter_strategies()            │
  │  [cache: /tmp pkl]      ┌──────────────────────┐            │
  │                         │ S0_no_removal         │            │
  │                         │ A_confirmed_bad  ◄──  │            │
  │                         │ B_extended_bad        │            │
  │                         │ C_rnaseq_only         │            │
  │                         │ D_malignant_only      │ PCA-based  │
  │                         │ E1_iterative_r1  ◄──  │ outlier    │
  │                         │ E2_iterative_r2  ◄──  │ detection  │
  │                         │ E3_iterative_r3  ◄──  │ (iterative)│
  │                         │ F_microarray_only     │            │
  │                         │ G_affymetrix_only     │            │
  │                         └──────────────────────┘            │
  │                                   │                          │
  │                                   ▼                          │
  │         ┌─────────────────────────────────────────┐         │
  │         │  IMPUTATION                              │         │
  │         │  strict:     dropna(axis=1) → 3,520 genes│         │
  │         │  knn:        KNNImputer(k=5) → ~12,000   │         │
  │         │              genes (S0) / ~15,000 (E3)   │         │
  │         │  missforest: R missForest → FAILED        │         │
  │         │              (>24h on 16 CPUs/240 GB,     │         │
  │         │               pod killed, no restart)     │         │
  │         │  softimpute: R softImpute → ~11,000 genes │         │
  │         │              (S0) / ~15,000 (E3)          │         │
  │         │  [residual NaN → dropna(axis=1)]          │         │
  │         └─────────────────────────────────────────┘         │
  │                                   │                          │
  │                   log_transform_by_cohort()                  │
  │                   [log2(x+1) where max > 30]                 │
  │                                   │                          │
  │                                   ▼                          │
  │         UPLOAD to S3: prepared/{strat}__{imp}__exp.tsv.gz   │
  │                        prepared/{strat}__{imp}__ann.tsv.gz   │
  └──────────────────────────────────────────────────────────────┘
                              │
                              │  40 prepared pairs on S3
                              ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  STAGE 2 — NORMALIZATION  (run_norm_parallel.py)            │
  │  1,000 jobs: 40 pairs × 25 normalization methods             │
  │                                                              │
  │  For each (strategy, imputation, method):                    │
  │                                                              │
  │  download prepared (strat, imp) pair from S3                │
  │                                                              │
  │         ┌────────────────────────────────────────┐          │
  │         │  NORMALIZATION METHOD (one of 25)       │          │
  │         │  Low tier:   raw, median_scaling,       │          │
  │         │              limma, sva, tmm*, vst*     │          │
  │         │  Medium tier: combat, combat_seq,       │          │
  │         │               pycombat, inmoose,        │          │
  │         │               ruv, mnn, harmony,        │          │
  │         │               scanorama, fsmvn,         │          │
  │         │               harmonizr, peer**         │          │
  │         │  High tier:  qsmooth, fsqn_py, fsqn_r,  │          │
  │         │              quantile, rank, tdm,        │          │
  │         │              shambhala, angel            │          │
  │         └────────────────────────────────────────┘          │
  │                              │                               │
  │         * RNA-seq only (TMM/VST) → skipped on mixed strats  │
  │         ** PEER unavailable in R 4.5 → always skipped       │
  │                              │                               │
  │                              ▼                               │
  │         ┌──────────────────────────────────────────┐        │
  │         │  POST-REMOVAL DECISION                    │        │
  │         │  post_rm=False → exp as normalized        │        │
  │         │  post_rm=True  → identify outlier batches │        │
  │         │                  remove them; recompute   │        │
  │         └──────────────────────────────────────────┘        │
  │                              │                               │
  │              compute metrics: r2_batch, r2_diag             │
  │              n_samples, n_genes, status                      │
  │                              │                               │
  │  UPLOAD post0, post1 TSV.GZ to S3                           │
  │  WRITE JSON metrics sidecar                                  │
  └──────────────────────────────────────────────────────────────┘
                              │
                              ▼
              metrics.csv (aggregated; S3)
              load_cross_product_results.py
              harmonization_benchmark.ipynb
              → heatmaps, ranking tables, top-K analysis
```

**Infrastructure:**
- Runs on Kubernetes pod (`ubuntu:24.04`, 16 vCPU / 240 GiB RAM)
- Parallelism: ThreadPoolExecutor (4 workers per stage)
- Memory guard: three-level RAM check; workers exit code 2 on OOM
- Pre-caching: dispatcher pre-populates `/tmp` pickle caches before launching workers
- Each worker is an isolated subprocess — separate Python + R session (avoids rpy2 fork-safety issues)

---

## SLIDE 11 — Selected Normalization Method: FSQN R

**Title:** Selected method: Feature-Specific Quantile Normalization (FSQN R package)

**Reference:** [Franks, Cai & Whitfield, *Biostatistics* 2018](https://doi.org/10.1093/biostatistics/kxx028)

**Algorithm:**  
For each gene independently:
1. Compute the empirical quantile distribution in the reference batch (RNASeq_FF_PolyA, n=1,039)
2. For each non-reference batch, map every sample's value for that gene to the corresponding quantile in the reference distribution
3. Apply the quantile mapping function to each sample's value

**Why it outperforms standard quantile normalization:**  
Standard QN forces all genes to the same global distribution across batches. FSQN respects that different genes have different biological variance and expression ranges — it only aligns the distribution *shape* within each gene, not across genes.

**Configuration in this project:**
- Reference batch: `RNASeq_FF_PolyA` (1,039 samples; highest quality, largest RNA-seq batch)
- Applied via R package through rpy2 file-based interface (expression written to tempfile → R reads/writes → Python reads result)
- Genes used: intersection of genes present in reference batch and test set

**Current limitation:**  
Even after FSQN, the formal SOM-space batch test **fails**: different cell types from the same platform cluster together more tightly than the same cell type across platforms. This motivates restricting SOM analysis to RNA-seq-only samples.

**Pre-computed output available at:**  
`$FL_DATA_ROOT/fsqn_normalized_exp_R.tsv`

---

## SLIDE 12 — FSQN vs. Other Top Methods: Comparison

**Title:** Comparison of top normalization approaches

*Note: All values below are from the pre-benchmark exploration phase (`harmonization_benchmark.ipynb`). Formal tracked metrics are not yet available for the A_confirmed_bad × strict combination in `metrics.csv`. Numerical R² values are omitted here — they will be sourced from the full benchmark output.*

**Table (summary of pre-benchmark exploration + early benchmark results):**

| Method | Residual batch R² | Biology preserved (R² diag) | Limitations | Verdict |
|---|---|---|---|---|
| Raw (no normalization) | — | Reference | — | Baseline only |
| limma removeBatchEffect | — | Partial | Additive only; leaves multiplicative platform effects | Partial |
| ComBat ([Johnson et al. 2007](https://doi.org/10.1093/biostatistics/kxj037)) | — | Good | Requires complete matrix; fails with BEAM genes in large gene space | Not selected |
| SVA ([Leek & Storey 2012](https://doi.org/10.1038/nmeth.2237)) | — | Good | 0 SVs detected on full data; fall-through | Not selected |
| qsmooth ([Hicks et al. 2018](https://doi.org/10.1093/biostatistics/kxx028)) | — | Partial | Fails on 12/88 cohorts; partial improvement only | Partial |
| Standard QN ([Bolstad et al. 2003](https://doi.org/10.1093/bioinformatics/19.2.185)) | — | Good | Forces one global distribution; 5 outlier batches remain | Good, not selected |
| **FSQN R ([Franks et al. 2018](https://doi.org/10.1093/biostatistics/kxx028))** | — | **Best** | **Requires reference batch; gene-space restricted to intersection** | **Selected** |
| FSQN Python re-impl. | — | Good | Slightly weaker than R package | Alternative |
| Harmony ([Korsunsky et al. 2019](https://doi.org/10.1038/s41592-019-0619-0)) | — | Worsened | Embedding-based; projection back to gene space loses information | **Rejected** |
| HarmonizR ([Voss et al. 2022](https://doi.org/10.1038/s41467-022-31214-6)) | 0.099* | 0.141* | *Only in E3×softimpute; needs imputation to expand gene space; slow (~14 min) | Promising |
| TMM / VST | — | — | RNA-seq only; not applicable to mixed-platform data | Inapplicable |

*HarmonizR E3×softimpute result from `metrics.csv` (2026-04-28 run).

---

## SLIDE 13 — Batch Effect Metric: Design and Interpretation

**Title:** How we measure batch effect: PCA R² (ANOVA)

**Formula:**  
For each of the first 10 PCA components, compute one-way ANOVA of `RNA_BATCH`:

```
R²_PC = SS_between_batches / SS_total

where SS = Sum of Squares:
  SS_between = variance in that PC attributable to batch group membership
  SS_total   = total variance in that PC across all samples

mean R² = (1/10) × Σ R²_PC   (averaged over first 10 PCs)
```

- **R² = 1.0**: all variance in that PC explained by batch assignment — pure technical noise
- **R² = 0.0**: batch has no predictive power for that PC — ideal for biology-preserving normalization
- **Baseline (raw data)**: R² ≈ 0.95 (from initial PCA visualization in `harmonization_benchmark.ipynb`)
- **Current best (HarmonizR, E3×softimpute)**: R² ≈ 0.099 (source: `metrics.csv`)

**Complementary metric: R² diagnosis**  
Same formula applied to `Diagnosis_cell_type_unified` — measures biological signal preservation. We want batch R² low AND diagnosis R² preserved.

**Known limitation — Angel exception:**  
Method `25_angel` returns a reduced gene space (platform-stable genes only). Its R² is computed on fewer genes and is **not directly comparable** with other methods.

---

## SLIDE 14 — Current Progress: Run Status

**Title:** Benchmark run status as of 2026-04-28

**Stage 1 (Preparation) — 40 pairs total:**
- Files on S3: ~31 prepared pairs (62 files: exp + ann per pair)
- Missing ~9 pairs: all involve `missforest` imputation, which failed — ran for >24 hours on 16 CPUs / 240 GB RAM before the Kubernetes pod was killed with no automated restart. missforest pairs will not be completed; this imputation approach is removed from the active benchmark.
- Status: substantially complete; 3 active imputations (strict, knn, softimpute) fully prepared

**Stage 2 (Normalization) — 1,000 jobs total → 2,000 output files:**
- Output files on S3: **1,116** (as of 2026-04-28 evening)
- Completed job combos: 558 (each successful job produces 2 files: post0 + post1)
- Skipped (expected — RNA-seq-only methods on mixed data, PEER): included in total
- Failed entries in `failed_jobs_norm.txt`: 31 entries (to be retried)

**Timeline of outputs by production date (source: `current_normalized_files_260428.txt`):**

| Date | Outputs produced | Phase |
|---|---|---|
| 2026-04-19 | 309 | Initial run (early strategies/methods) |
| 2026-04-20 | 38 | Continued initial run |
| 2026-04-26 | 179 | After refactoring + pod relaunch |
| 2026-04-27 | 408 | Large batch — E3 strategies |
| 2026-04-28 | 133 | E3 × softimpute completion (source: `logs/norm_log_e3_260428.txt`) |

**Recent milestone:** E3_iterative_r3 × softimpute × HarmonizR completed (2026-04-28): R² batch = **0.099** — new lowest batch score across all completed runs. Source: `metrics.csv`, row `E3_iterative_r3,softimpute,21_harmonizr,False,medium,0.09861,0.14055,5256,15226,ok`.

---

## SLIDE 15A — Technical Challenges Solved (Part 1)

**Title:** Technical problems solved during benchmark development (1/2)

**1. rpy2 fork-safety issues**  
Problem: running multiple R sessions via rpy2 in a multiprocessing pool caused memory corruption and crashes.  
Solution: each normalization job runs as an **isolated subprocess** (fresh Python + R session). The dispatcher uses `ThreadPoolExecutor` to launch subprocesses — threads manage processes, processes own R sessions.

**2. Two-stage pipeline design**  
Problem: each of 1,000 workers re-downloading the 1.9 GB expression matrix and re-running imputation was prohibitively slow and redundant.  
Solution: separated **Stage 1** (preparation, 40 jobs) from **Stage 2** (normalization, 1,000 jobs). Workers in Stage 2 download only the ~600 MB pre-prepared file for their (strategy, imputation) pair.

**3. Residual NaN handling (BEAM genes)**  
Problem: KNN and softImpute leave residual NaN in genes absent from entire batches. Early implementations used `fillna(median)` which is statistically incorrect ([Hui et al. 2023](https://doi.org/10.1038/s41598-023-35823-7) — inflates noise irreversibly before batch correction).  
Solution: documented with literature review; confirmed `dropna(axis=1)` is correct for all 24 methods, except HarmonizR which handles BEAMs internally.

---

## SLIDE 15B — Technical Challenges Solved (Part 2)

**Title:** Technical problems solved during benchmark development (2/2)

**4. Memory management on K8s pod (16 CPU / 240 GB RAM)**  
Problem: OOM crashes when running high-memory methods (HarmonizR, missForest) with large softimpute gene spaces (~15,000 genes × 5,256 samples). missForest additionally failed to complete in >24 hours.  
Solution: three-level memory guard in dispatcher (free RAM threshold) + worker-level checks + explicit `gc.collect()` + R garbage collection calls between steps. missForest removed from active benchmark.

**5. Shambhala2 R package environment issue**  
Problem: `library(Shambhala2)` throws "there is no package called 'Shambhala2'" in the pod environment (source: `logs/norm_log_e3_260428.txt`), even though installation was attempted.  
Status: all shambhala jobs fail; to be investigated (possible GitHub package installation failure during pod init).

**6. Kubernetes deployment**  
Infrastructure: pod deployed from `ubuntu:24.04` with 30–40 min init script installing R 4.5 + Bioconductor 3.22 + all 12 R packages + Python 3.11 packages. VSCode Remote-SSH workflow via port-forward. Scripts synced by rsync.

---

## SLIDE 16 — Batch Effect Testing: What Has Been Done

**Title:** Batch effect testing — completed assessments

**1. Primary benchmark metric (PCA R² batch)**  
- Computed for all completed E3-strategy jobs and stored in `harmonization-scripts/metrics.csv` (local partial copy; full version on S3)
- Currently tracks E3 strategy combinations: 136 rows, covering E3 × {strict, knn, softimpute} × all applicable methods
- Provides a single scalar for each output matrix; enables ranking across methods

**2. Visual QC (PCA/UMAP/tSNE)** — *to be done*  
- Planned for top 10 normalization outputs; will be run in `harmonization_benchmark.ipynb`
- To be colored by: RNA_BATCH, Diagnosis, platform, FF/FFPE, tumor/normal

**3. SOM metagene space batch test** — *previously shown to supervisor*  
- Ran oposSOM on FSQN R output and QN output (results already presented)
- Result: **batch test fails in metagene space** — different cell types from the same platform cluster together more tightly than the same cell type across platforms
- Interpretation: FSQN corrects well in gene-expression PCA space but platform-specific gene-set activation patterns remain

**4. Strategy-level comparison** — *to be done*  
- Strategies C (RNA-seq only), G (Affymetrix only), F (microarray only) establish within-platform baselines
- Comparing against S0/A/B tests the cross-platform normalization benefit

---

## SLIDE 17A — Batch Effect Testing: What Needs to Be Done (Part 1)

**Title:** Remaining batch effect assessment approaches (1/2)

**1. PCA R² heatmap across full cross-product**  
- Pending: all 1,000 jobs complete
- Will produce 10 strategies × 25 methods heatmap for each of 3 active imputations × 2 post variants = **6 heatmaps total**
- Key question: is FSQN R consistently best, or does it interact with strategy/imputation?

**2. Visual inspection of PCA/UMAP/tSNE plots for top 10 approaches**  
- To be done manually in `harmonization_benchmark.ipynb` after loading top-10 expression matrices
- Colored by RNA_BATCH, Diagnosis, platform, FF/FFPE, tumor/normal
- Will include comparison against 10 representative bad-normalization cases to visualize the contrast

**3. Distribution plots by cohort after normalization**  
- Visual inspection of per-cohort expression distributions before/after normalization
- To be done for top-10 methods; box plots or violin plots colored by RNA_BATCH
- Will reveal residual cohort-level shifts not captured by PCA R²

**4. kBET ([Büttner et al. 2019](https://doi.org/10.1038/s41592-018-0254-1)) (k-nearest neighbor batch effect test)**  
- Formal statistical test: are k nearest neighbors of each sample enriched for same-batch samples?
- More sensitive than PCA R²; operates at individual sample level
- Status: **not yet implemented**; planned addition to benchmark pipeline

---

## SLIDE 17B — Batch Effect Testing: What Needs to Be Done (Part 2)

**Title:** Remaining batch effect assessment approaches (2/2)

**5. LISI ([Korsunsky et al. 2019](https://doi.org/10.1038/s41592-019-0619-0)) (Local Inverse Simpson's Index)**  
- iLISI (integration) — higher = better batch mixing
- cLISI (cell-type) — higher = better biology preservation
- Directly applicable to PCA/UMAP embeddings already computed
- Status: **not yet implemented**; planned as supplementary metric

**6. SOM-space batch test (quantitative)**  
- The qualitative SOM portrait comparison (shown previously) showed platform clustering
- Needed: quantify R² of `RNA_BATCH` on SOM metagene matrix (not raw genes)
- Apply across multiple normalization outputs to find which achieves best SOM-space integration
- Status: **planned** — requires running oposSOM on top-5 normalization outputs

**7. Silhouette score (batch vs. biology)**  
- Batch silhouette (RNA_BATCH as labels) — want low/negative
- Biology silhouette (Diagnosis as labels) — want high
- Ratio: biology / batch silhouette = composite quality metric
- Status: **planned**; straightforward to add to `bench_shared.py`

**8. Variance partition ([Hoffman & Bhatt 2021](https://doi.org/10.1186/s13059-022-02767-2))**  
- Quantifies contribution of batch, diagnosis, platform, FF/FFPE simultaneously to gene-level variance
- More informative than single-covariate PCA R²
- Status: **planned** for top-3 normalization methods comparison

---

## SLIDE 18 — Next Steps: Analysis After Benchmark Completion

**Title:** What comes next after the benchmark

**Immediate (when all 1,000 jobs complete):**
1. Load full `metrics.csv` → generate R² heatmaps (10 strategies × 25 methods, per imputation × per post_rm variant)
2. Identify top-10 combinations by R² batch across the full grid
3. Load their expression matrices; run PCA/UMAP visual QC and per-cohort distribution plots; compare against 10 representative poor-normalization cases to verify visually
4. Run oposSOM on top-5 normalization outputs to assess SOM-space batch effect
5. Retry 31 failed jobs (`--retry-failed`)

**Short term (2–4 weeks):**
1. Proceed with top-method downstream analysis in parallel with remaining benchmark jobs
2. Implement kBET and LISI metrics in `bench_shared.py`
3. Run variancePartition on top-3 outputs
4. SOM projection of external FL cohorts onto reference (MDPI 2022 method)
5. Analyze metagene cluster enrichment for FL biological programs (Centroblast vs. Centrocyte axis)

**Dissertation-level:**
1. Write technical article on harmonization and imputation comparison as a first deliverable
2. Compare SOM signatures vs. PCA64 vs. internal B-cell typing vs. embeddings for OS/PFS prediction
3. Validate FL biological subtypes against published literature

---

## SLIDE 19 — Infrastructure Summary

**Title:** Computational infrastructure

| Component | Details |
|---|---|
| **K8s pod** | `fl-batch-correction`, `ubuntu:24.04`, 16 vCPU / 240 GiB RAM |
| **Python** | 3.11, venv `collagen_3_11` |
| **R** | 4.5.3, Bioconductor 3.22 |
| **Key R packages** | limma, sva, batchelor, RUVSeq, qsmooth, FSQN, TDM, HarmonizR, missForest, softImpute, edgeR, DESeq2 |
| **Key Python packages** | rpy2, boto3, pandas, numpy, scikit-learn, harmonypy, scanorama, combat, inmoose, psutil |
| **Storage** | AWS S3 (`$FL_S3_BUCKET/FL_batch_correction/`) |
| **Persistent volume** | 100 GiB PVC `fl-workspace` for logs and workspace |
| **Job dispatch** | ThreadPoolExecutor, 4 workers per stage |
| **Memory guard** | Three-level: dispatcher → worker startup → worker post-load |
| **Docker image** | `${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/fl-batch-correction:latest` |
| **Smoke test** | `test_mock.py` — 25 methods × 4 imputation approaches on synthetic 80×200 data |

**Total compute estimate:** ~1,000 jobs × avg ~10–30 min/job = ~200–500 CPU-hours for a complete benchmark run

---

## SLIDE 20 — Summary and Open Questions

**Title:** Summary and questions for supervisor

**Completed in the last 2 weeks:**
- ✅ Two-stage K8s pipeline operational (preparation + normalization separated)
- ✅ 25 normalization methods × 4 imputation strategies fully implemented and tested
- ✅ ~558 out of 1,000 normalization jobs completed; ~1,116 output matrices on S3
- ✅ E3×softimpute×HarmonizR: R² batch = 0.099 — new best result (source: `metrics.csv`)
- ✅ Literature-backed decision for `dropna` vs. `fillna(median)` for residual BEAM NaN values
- ✅ Dockerfile + K8s pod with R 4.5 + Bioconductor 3.22 fully reproducible

**Key results so far:**
- FSQN R is best on strategy A × strict (pre-benchmark exploration; formal metrics pending)
- HarmonizR competitive when paired with softimpute + iterative outlier removal: R² = 0.099 (source: `metrics.csv`, E3×softimpute×21_harmonizr)
- Harmony (Python embedding-based) is anti-optimal — worsens batch
- SOM metagene space fails formal batch test even after FSQN — cross-platform SOM requires RNA-seq restriction (or microarray-only track)

**Open questions for discussion:**
1. Is the SOM analysis feasible on the full mixed-platform data, or should we restrict to RNA-seq only — or is a separate microarray-only SOM track also worth pursuing?
2. Should imputation be performed **after** log-transformation by cohort (the current order is impute → log-transform)? Performing imputation on already log-transformed data is more statistically honest: if a gene is missing in a log-scale cohort, an imputed value would be in log scale; imputing on raw data and then log-transforming may artificially correct the log offset for imputed values.
3. Should imputation be limited to **within-batch** rather than across all samples? Within-batch imputation would impute far fewer genes but produce less artificial noise — consistent with the `dropna` reasoning for BEAMs (genes missing from an entire batch cannot be honestly imputed from other batches).

---

## APPENDIX SLIDES (optional, as backup)

### A1 — Literature Anchors for Method Selection

| Reference | Relevance |
|---|---|
| [Loeffler-Wirth et al. 2019](https://doi.org/10.1038/s41467-019-12197-9) | oposSOM predicts OS in B-lymphomas |
| [Loeffler-Wirth et al. 2022](https://doi.org/10.3390/cells11010005) | Continuous LZ↔DZ transitions via SOM |
| [Franks et al. 2018](https://doi.org/10.1093/biostatistics/kxx028) | FSQN algorithm |
| [Voss et al. 2022](https://doi.org/10.1038/s41467-022-31214-6) | HarmonizR BEAM-aware harmonization |
| [Goh et al. 2023](https://doi.org/10.1093/bib/bbad055) / [2025](https://doi.org/10.1093/bib/bbae583) | BEAM missing data framework |
| [Hui et al. 2023](https://doi.org/10.1038/s41598-023-35823-7) | Batch-sensitized imputation (M1 vs M2 vs M3) |
| [Hie et al. 2019](https://doi.org/10.1038/s41587-019-0113-3) | Scanorama gene intersection philosophy |
| [Büttner et al. 2019](https://doi.org/10.1038/s41592-018-0254-1) | kBET batch effect test |
| [Korsunsky et al. 2019](https://doi.org/10.1038/s41592-019-0619-0) | Harmony + LISI metrics |
| [Troyanskaya et al. 2001](https://academic.oup.com/bioinformatics/article/17/6/520/272365) | KNN imputation |
| [Stekhoven & Bühlmann 2012](https://doi.org/10.1093/bioinformatics/btr597) | missForest imputation |
| [Hastie et al. 2015](https://jmlr.org/papers/v16/hastie15a.html) | softImpute matrix completion |
| [Rubin 1976](https://doi.org/10.1093/biomet/63.3.581) | MNAR missing data theory |

### A2 — Full Method Decision Table
(extended version of imputation × method × NaN handling from `harmonization-tools-research/imputation_and_batch_effect_research.md`)

### A3 — Example SOM Portraits
(GCB-DLBCL vs. ABC-DLBCL vs. FL vs. Normal B cells, from existing oposSOM runs under QN and FSQN R)

### A4 — K8s Architecture Diagram
(pod spec, PVC, AWS credentials secret, port-forward SSH workflow)

### A5 — Failed Jobs Analysis
(31 failed entries in `failed_jobs_norm.txt`; breakdown by method and strategy; Shambhala2 root cause investigation)
