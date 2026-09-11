# Project Overview — FL Harmonization Dissertation

Deep-reference document for the Follicular Lymphoma transcriptomics dissertation at BostonGene. Contains research context, full dataset details, analytical pipeline, and literature anchors. Operational guidance (commands, code standards, current status) lives in `CLAUDE.md`.

---

## Research Objective

**Central question:** Can SOM (Self-Organizing Map) gene expression patterns resolve transcriptomic subtypes of Follicular Lymphoma, align them to normal GC B-cell differentiation states (Light Zone ↔ Dark Zone axis), and predict clinical outcomes across multiple platforms (RNASeq, microarrays)?

### Three research tracks
1. **Fundamental** — Map differentiation trajectories of GC lymphomas along the LZ (inflammation/anergy) ↔ DZ (proliferation) axis
2. **Applied** — Predict OS, PFS, POD24, therapy response using SOM-derived signatures
3. **Methodological** — Develop harmonization and ML-based subtyping pipelines using SOM for multiple platforms removing batch effect

### Specific tasks
- Assemble a large multi-platform cohort (microarray + RNA-seq) and harmonize expression data
- Identify the best batch correction method for cross-platform integration
- Run oposSOM analysis; evaluate batch effect in metagene space
- Project external cohorts onto a reference SOM using the published method (MDPI 2022)
- Score samples with internal B-cell type classifiers (Naive, Centroblast, Centrocyte, Memory, Plasma)
- Compare FL transcriptomic subtypes with the GC- and MEM-like subtypes from the 2025 paper (doi: 10.1038/s41375-025-02603-9)
- Validate SOM signatures against internal B-cell typing, PCA64, and gene-embedding approaches

---

## Dataset

### Scale and composition
| Attribute | Value |
|---|---|
| Total assembled samples | **7,174** — authoritative source is `prepared/{strat}__{imp}__ann.tsv.gz` on S3 (verified 7,174 × 485). The local `comb_ann_unified.csv` has 7,238 rows because 64 samples carry annotation but no expression; never quote counts from it. |
| After bad-batch exclusion | **5,444 samples** |
| Genes (full coverage, no NA) | **3,447** |
| Cohorts | 88 |

### Diagnosis groups
- Diffuse Large B-Cell Lymphoma (DLBCL): ~3,000 samples
- Follicular Lymphoma (FL): ~2,000 samples
- Normal B cells (Normal_B_cells + Kassandra): ~1,000 samples
- Rare (excluded from SOM): MCL, Double-Hit, MZL, CLL, Other

### Data sources
1. **Internal cohort database** — 46 cohorts, retrieved with its Python client. Key DLBCL: CARTFARAMAND, GOYA, GSE117556, GSE10846. Key FL: DAVE, GSE62241, HUET, PARSA, GUO.
2. **Sorted normal B cells** — 28 sorted B-cell public datasets in `/normal_B_cells/` (GEO/ArrayExpress: GSE12195, GSE12453, GSE36907, GSE68878, GSE85289, E-MTAB-3974, and others).
3. **Kassandra** — Deconvolution-derived B cells (RNA-seq only; no GC B-cell types).
4. **Arsen GPL570** — Internal microarray data (`DLBCL_selected_samples.Rdata`); probes mapped to HGNC via `GPL570_mapping.py`. **Excluded** from SOM analysis (persistent batch effect after normalization).
5. **MDA FL Stratification** — Patient-level FL cohort (`MDA_Strati_FL_annotation.csv`) with FLIPI, FLIPI-2, PRIMA-PI, PFS, OS, POD24, treatment, response.

### RNA_BATCH distribution (major batches)
| RNA_BATCH | N | Platform |
|---|---|---|
| RNASeq_FF_PolyA | 1,039 | Illumina NGS ← **FSQN reference** |
| GPL570_Unknown_Unknown | 1,030 | Affymetrix |
| GPL570_FF_Unknown | 994 | Affymetrix |
| RNASeq_FFPE_Exome_capture | 939 | Illumina NGS |
| GPL14951_FFPE_Unknown | 810 | Illumina microarray |
| GPL570_FFPE_Unknown | 800 | Affymetrix |

Platforms total: Affymetrix microarray (3,821), Illumina NGS (2,386), Illumina microarray (940), Agilent microarray (64).

### Key annotation columns
`Diagnosis_cell_type_unified`, `RNA_BATCH`, `PLATFORM_RNA`, `RNASEQ_SOURCE` (FF/FFPE), `Major_group`, `TUMOR_NORMAL`, `OS`, `OS_FLAG`, `PFS`, `PFS_FLAG`, `RESPONSE`, `COHORT_LABEL`, `AGE`, `GENDER`

---

## Batch Effect and Normalization

### Problem magnitude
Before normalization, **~95% of PCA variance is explained by RNA_BATCH** (platform effects dominate biology entirely). After the selected normalization, this drops to **~16%**.

### Normalization methods evaluated

| Method | Residual batch (PCA R²) | Verdict |
|---|---|---|
| None (raw) | ~95% | baseline |
| qsmooth | ~48% | partial — fails on 12/88 cohorts |
| Standard quantile normalization (QN) | ~20% | good — 5 batch outliers remain |
| **FSQN (R package, → RNASeq_FF_PolyA)** | **~16%** | **selected for SOM pipeline** |
| FSMVN (feature-specific mean-variance) | failed | distributions not aligned |
| Harmony (Python) | >95% | rejected — made things worse |
| limma `removeBatchEffect` alone | partial | not selected as primary |
| ComBat (neuroCombat / sva) | partial | tested but not selected |
| **MNN (mutual nearest neighbours)** | — | **best by comprehensive multi-metric evaluation** |
| **HarmonizR (E3×softimpute)** | **~9.9%** | best PCA R² (single metric); not used for SOM |
| SVA (RNASeq only + KNN/softimpute) | — | best visual batch removal; FF/FFPE fully mixed; two FL subgroups visible |
| **SVA (FFPE only + softimpute/KNN)** | — | **June 2026:** first-ever mixing of all three FFPE platforms (NGS + Affymetrix + Illumina); best local mixing in entire benchmark |
| **Shambhala** | — | **Bad overall.** Cannot cross-harmonize RNA-seq + microarrays; no FF/FFPE mixing even in best P/Q; worse than SVA on RNA-seq-only. Excluded from Article 1. |

The 39-method comprehensive benchmark (`metrics_comprehensive.csv`) identified **MNN as the best overall harmonization approach** across all metric clusters. 16 of 19 MNN instances cluster with >75% of metrics above 0.5. HarmonizR E3×softimpute achieves the lowest single PCA R²=0.099 but is not the multi-metric winner.

### Shambhala benchmark (May 2026)

Shambhala2 (Borisov 2022; CuBlock + quantile normalization) was containerized as a pure-Python pipeline and run at full scale.

**18 P/Q reference dataset combinations tested:**

| P dataset | Samples | Notes |
|---|---|---|
| P0std | 39 | Original Borisov 2021; diverse tissues; standard reference |
| NBKass | 141 | Normal B cells, Kassandra |
| NBRNAseq | 317 | Normal B cells, RNA-seq |
| NBGPL570 | 250 | Normal B cells, GPL570 Affymetrix; largest NP → slowest |
| ANTE | 202 | Affymetrix reference; 36k genes |
| NBlegacy | 733 | Normal B cells, Normal_B_cells |
| NBext | 878 | Normal B cells, extended set |
| Oncobox | 779 | Cancer reference; oncology-biased anchor |
| GTExAffy | 651 | GTEx Affymetrix; strict run failed (gene ID mismatch) |

| Q dataset | Samples | Notes |
|---|---|---|
| Q0std | 100 | GTEx RNA-seq; 31–69% gene loss with FL strict input |
| QNBKass | 141 | Normal B cells; **zero gene loss** — perfect gene overlap with strict FL input |

**Key Q observation:** QNBKass shares the exact gene set with FL strict-imputation input → 3,447 genes retained regardless of P choice. Q0std causes significant gene loss because it covers a different gene panel.

**Speed-up deployed (A_E flags):**
- `--precompute-qn-reference`: pre-compute QN sort order from P once; inject into all 30 Octave workers
- `--precompute-cublock-clusters`: run k-means on P once in Python; pass cluster labels to Octave via `--eval`
- Result: 8.6× lab speedup, ~10× real-world; mean relative distortion 1.39% (within natural run-to-run variability)
- Without speed-up: large-P + knn/softimpute runs projected at 2–3 days each; full benchmark ~27 days

**Benchmark scale:** 18 P/Q × 3 imputations × 12 strategies × 2 post_rm = **1,296 harmonizations** — **100% complete** as of 2026-05-26.

**Shambhala performance conclusions (confirmed June 2026):** Metrics computed for **3,835 harmonization attempts** (Shambhala 1,297 + other methods 2,538; as of 2026-06-04).
- **Best Shambhala attempts are bad overall** — cross-platform harmonization (RNA-seq + microarrays) fails regardless of P/Q choice.
- **RNA-seq-only Shambhala** (strategy C): slightly better, but FF/FFPE samples still do not mix; worse than SVA on both PCA and embeddings.
- **Malignant-only Shambhala**: same problem — no FF/FFPE mixing.
- Shambhala does not separate FL from DLBCL or normal GC B cells better than MNN or SVA.
- **Shambhala excluded from Article 1** — confirmed at supervisor meeting 2026-06-04.
- **Root cause:** Most harmonizers (including Shambhala) were designed for TCGA/GTEx-scale biological differences. Subtle transcriptomic differences between FL, DLBCL, and normal GC B cells are below their resolution.

### FF-only and FFPE-only strategy findings (June 2026)

After adding J_ff_only and K_ffpe_only strategies (14 strategies total):

- **FF only (J strategy):** MNN and FSQN R best by PCA (good centroid separation). However, <⅓ of samples mix in UMAP/tSNE — local cross-cohort separation persists.
- **FFPE only (K strategy): SVA (+ softimpute/KNN) achieves the first-ever observed mixing of all three FFPE platform groups (Illumina NGS + Affymetrix + Illumina microarray)** — previously these three batches were always separated. MNN is the worst on FFPE-only.
- This makes SVA + FFPE-only the single strongest local batch correction result in the entire benchmark; supersedes the prior assumption that FFPE samples cannot be mixed across platforms.

### Comprehensive metrics findings (June 2026)

**Metric groups (11 total):**

| Group | Metrics | Status |
|---|---|---|
| A | PCA R² (batch + diagnosis) | implemented |
| B | kBET acceptance rate | implemented |
| C | iLISI, cLISI | implemented |
| D | ASW (batch + biology) | implemented |
| E | UMAP/tSNE centroid dispersion | implemented |
| F | Pairwise KS tests | implemented |
| G | variancePartition mixed-model | implemented |
| H | kNN graph connectivity, intra/inter distances | implemented |
| I | WaterMelon score (wm_mean_batch, wm_mean_bio, wm_ratio_bio_batch) | **extended** |
| J | PC variance distribution: pct_var_pc1–pc10, pct_var_cum_top10 | **new** |
| K | NA retention: pct_genes_noNA, pct_samples_noNA, n_na_cells, pct_na_cells | **new** |

Group J tracks whether batch effects (which inflate PC1) are removed — raw PC1 ≈ 95%, good normalization drops to single digits. Group K detects methods that silently reduce the gene/sample space. Group I's `wm_ratio_bio_batch` combines batch removal and biology preservation into a single ranking score.

**Metric cluster structure** (from `harmonization_metrics_analysis.ipynb` clustermap):
- **Cluster 1** — Almost always bad: local neighborhood metrics (kBET, cLISI, iLISI, entropy)
- **Cluster 2** — Mostly bad: local neighborhood + global + KS metrics
- **Cluster 3** — Mostly good: global metrics (distance ratio, KS tests, centroids, CMS, silhouette width)
- **Cluster 4** — Almost always good: global metrics (dispersion separability, PCR, centroids, silhouette width)

**Hierarchy of importance:** strategy > method > post-removal > imputation

**New metric insights (June 2026):**
- **Softimpute is ~10 pp better than KNN** by PCR metric — prefer softimpute for imputation step.
- **Global metrics (PCR, R²) are necessary but not sufficient** for good batch correction. SVA achieves top local mixing without strong global correction. Microarray-only strategies can appear good by PCR because batches merge into large meta-groups rather than actually mixing locally.
- **Batch mixing and biology mixing are correlated** (trade-off axis): stronger batch mixing → stronger biology mixing. Malignant-only and FFPE-only strategies show better biology-to-batch ratio; FF-only is the worst (more cell-type classes inflate biology mixing).
- Only **MNN and FSQN R** have biology R² higher than batch R² (5 methods acceptable by R²; only 2 by PCR). Most methods fail the stricter PCR criterion.
- **Local metrics (kBET, iLISI) always fail** for cross-platform harmonization — this is a universal limitation, not a method-specific failure. All tested methods fail local mixing when RNA-seq and microarrays are combined.

**Best approaches by group:**
- MNN (strict or KNN, strategies A/B/E1–E3): >75% metrics >0.5; best by comprehensive evaluation
- SVA + RNASeq only + KNN imputation: best visual result; no batch effect; FF/FFPE fully mixed; two FL subgroups visible
- FSQN R + Affymetrix extended: biology separates, but batch effect preserved visually
- Shambhala: bad overall; cannot cross-harmonize; slightly improves RNA-seq-only but worse than SVA

**Universal challenge:** Cross-platform harmonization between microarray and RNA-seq remains fundamentally limited. All methods handle global distance metrics well but fail local neighborhood metrics (kBET, iLISI). 60% of tested approaches are "bad" (30–40% of metrics <0.5).

**Performance by metric type (3,835 attempts as of 2026-06-04):**
- ~5 methods acceptable by PCA R² (biology higher than batch); ~2 acceptable by PCR
- Two stable clusters: local metrics (kBET/iLISI/cLISI) always bad; global metrics (distance ratios, KS, centroids, silhouette) mostly good
- Shambhala does not form a distinct cluster — no systematic performance advantage over other methods

### Composite scoring methodology and curated Best-15 (July 2026, `harmonization_metrics_analysis_v3.ipynb` §4)

**Literature-informed weighting scheme** (§4.1): a weighted composite score was formalized on top of the equal-weight score used in the article figures, citing published benchmarks:
- **Batch mixing — 60% weight**: PCA R² (Tran et al. 2020, *Nat Methods*, 14-method scRNA benchmark) + kBET (Büttner et al. 2019) + LISI (Korsunsky et al. 2019, Harmony paper). Weight directly follows the 60% batch-correction weight used by the scIB benchmark (Luecken et al. 2022, *Nat Methods*).
- **Biology preservation — 35% weight**: ASW_bio + graph connectivity + biology-covariate R² (`Major_group`, `Diagnosis_cell_type_unified`). Slightly down-weighted from scIB's 40% because batch correction is the primary objective here.
- **Data quality — 5% weight**: gene retention + bimodality; a sanity check, not a normalization outcome.

**Curated "Best-15" set** (`_top_ids` in the notebook; `df_best`, 15 rows, 5 methods × 6 strategies, `post_rm=False` only):

| Method | Imputation | Strategy |
|---|---|---|
| `10_mnn` | strict | `S0_no_removal`, `H_affymetrix_extended`, `D_malignant_only` |
| `04_sva` | knn, softimpute | `C_rnaseq_only` |
| `04_sva` | knn, strict, softimpute | `K_ffpe_only` |
| `16_fsqn_r` | knn, softimpute, strict | `C_rnaseq_only` |
| `10_mnn`, `16_fsqn_r` | strict | `J_ff_only` |
| `13_fsmvn` | strict | `S0_no_removal` |
| `33_amdbnorm` | strict | `S0_no_removal` |

This list is the manually curated reference set overlaid (★) on Fig 7–10 and the new Supp D–G detail plots; it is distinct from, and narrower than, whichever method the automated composite/Borda ranking below picks as the numeric top-10.

**⚠ Open discrepancy — composite-score ranking vs. the MNN/SVA/FSQN R decision (flag for Daniil, not silently resolved):**
- By the **literature-weighted composite score** (§4, cell 403/405), the actual top-ranked runs are **not** MNN/SVA/FSQN R: `C_rnaseq_only__strict__shambhala_P0std_Q0std__post1` scores highest (0.732), followed by two `11_harmony` runs (0.730, 0.725) and `23_vst` (0.724). This ranking is restricted to `post1` (post-removal applied) within `C_rnaseq_only` and puts a **Shambhala** run and **Harmony** runs above the methods selected for the decision tree.
- By **Borda count** (rank-sum aggregation across all 87 metrics, cell 404) — a rank-based alternative to the weighted mean — the top-10 is dominated by **FSQN R** (`16_fsqn_r`) across `A_confirmed_bad` and `E1/E2_iterative` strategies, consistent with the existing decision tree.
- **Interpretation needed:** the weighted composite score appears sensitive to a small number of runs that score extremely well on a narrow subset of metrics (single-strategy, single-post-removal-state outliers), while Borda count rewards consistent performance across the full metric set. This directly affects the "Shambhala excluded from Article 1" claim, since Shambhala's *best single run* outranks MNN/SVA by composite score even though its aggregate profile (Borda, visual inspection) is worse. Recommend deciding — before Fig 10/Table 1 are finalized in the manuscript — whether the article reports the equal-weight score (current figure default), the literature-weighted score, or Borda count, since they disagree on the #1 approach.

**Pareto-front analysis** (cell 414, batch-mixing vs. bio-preservation): 26 of 31 harmonization methods are Pareto-optimal somewhere in this 2D trade-off space (only `05_combat`-family variants and a few others are strictly dominated) — reinforces that no single method dominates and method choice must stay strategy-dependent.

### Harmonization decision tree (final, 2026-06-04)

Two complexity levels. Choose the simplest level your data allows.

**Level 1 — by biomaterial (single preservation type; fewer platform conflicts):**
```
FF only         → MNN or FSQN R     (good PCA mixing; no post-removal needed)
FFPE only       → SVA + softimpute/KNN  ★ best local mixing in entire benchmark
RNA-seq only    → SVA + softimpute/KNN  (FF/FFPE fully mixed; two FL subgroups visible)
```

**Level 2 — by platform (mixed preservation types; harder):**
```
RNA-seq + Illumina microarrays   → FSQN R (no post-removal)
                                   or AMDBNorm / FSMVN + post-removal
RNA-seq + various microarrays    → MNN + post-removal (visual inspection required)
```

**Key caveats for the manuscript:**
- Most harmonizers fail for subtle biological differences (FL vs DLBCL vs normal GC B cells) — designed for TCGA/GTEx-scale variation.
- Global metrics (PCR, R²) are necessary but insufficient: good PCR can coexist with locally-separated batches.
- Softimpute ~10 pp better than KNN.
- Do NOT mix FF and FFPE without a preservation-type sub-strategy.

### Selected normalization: FSQN from R package
**Feature-Specific Quantile Normalization** (Franks et al., *Biostatistics* 2018) transforms each gene's distribution within each batch to match the reference batch distribution — unlike standard QN which forces one global distribution.

- Reference batch: **RNASeq_FF_PolyA** (1,039 samples; highest quality, largest batch)
- Applied via the official `FSQN` R package through `rpy2`
- Pre-computed output: `$FL_DATA_ROOT/fsqn_normalized_exp_R.tsv`
- Corresponding annotation: `$FL_DATA_ROOT/ann_normalized_fsqn_R.tsv`

### Critical SOM batch effect finding
Even after FSQN, **the formal batch test fails in SOM metagene space**:
> Different cell types from the same platform cluster together more tightly than the same cell type across platforms.

**Current recommendation: restrict SOM analysis to RNA-seq samples only.**

---

## Analytical Pipeline

### 1. Cohort assembly (`all_cohorts_assembly.ipynb`)
```
Internal cohort database (46 cohorts) + Normal_B_cells (28 datasets) + Kassandra + Arsen GPL570
→ Concatenate expressions + annotations
→ Filter genes (>5,000 non-NA samples)
→ Save: comb_exp.tsv, comb_ann.tsv
```

### 2. Harmonization benchmark (`harmonization_benchmark.ipynb` + scripts)
The benchmark evaluates **39 normalization methods × 14 filter strategies × 4 imputation options = 2,184 jobs → 4,368 S3 outputs** (each job produces two variants: with and without post-normalization outlier removal).

```
bench_shared.py
├─ build_filter_strategies() → 14 labeled datasets
│    Keys: S0_no_removal, A_confirmed_bad, B_extended_bad, C_rnaseq_only,
│          D_malignant_only, E1_iterative_r1, E2_iterative_r2, E3_iterative_r3,
│          F_microarray_only, G_affymetrix_only, H_affymetrix_extended,
│          I_rare_batches_removed, J_ff_only, K_ffpe_only
├─ prepare_dataset() / prepare_dataset_imputed() → strict / KNN / MissForest / SoftImpute
└─ 39 normalization methods (01_raw … 39_procrustes)
```

### 3. SOM analysis (`SOM_FSQN_R.py`)
```
Load FSQN-normalized expression
→ limma::removeBatchEffect (RNA_BATCH) via rpy2
→ oposSOM (automatic grid size, k-means spots)
→ Extract: metagene matrix, gene→BMU map, GSZ scores (HALLMARK + KEGG)
→ Cluster metagenes: AgglomerativeClustering(n=15, euclidean, ward)
→ Generate SOM portraits
```

### 4. Comprehensive metrics pipeline (`harmonization-metrics-calculation/` compute, `harmonization-metrics/` analysis)
```
S3 expression files → compute_batch_metrics.py
→ 11 metric groups (A–K): PCA R², kBET, iLISI/cLISI, ASW, UMAP/tSNE dispersion,
  pairwise KS tests, variancePartition (R), graph connectivity, pairwise distances,
  WaterMelon score, PC variance distribution, NA retention
→ 3 blind-check groups (L–N): marker correlation preservation, cross-batch rank
  agreement, predictive validation — excluded from the clustermap (see below)
→ JSON sidecars per job → run_metrics_concat.py → metrics_comprehensive.csv on S3
  + marker_gene_correlations_long.csv, marker_cohort_correlations_long.csv,
    prediction_folds_long.csv
→ A–K visualized in harmonization_metrics_analysis_v3.ipynb (353 cells; supersedes the
  older harmonization_metrics_analysis.ipynb)
→ L–N visualized in correlation_prediction_metrics_analysis.ipynb, plus its
  _narrow_set variant for the 56-gene QC-filtered panel
```

### 4b. Blind final check — metric groups L, M, N (August 2026)

Added at the colleagues' request as a final, independent check on the harmonization
approaches the clustermap had already selected. Plan:
`harmonization-metrics/marker_and_predictive_validation_plan_260819.md`.

| Group | Prefix | What it measures |
|---|---|---|
| **L** | `mk_` | For each marker gene and each cohort, the Spearman correlation between the gene's expression across that cohort's samples before and after harmonization. Reported per gene, per cohort, and as a grand mean, plus a marker-versus-housekeeping contrast. Since 2026-09-04 the integrative aggregates are reported **twice**: over the full 633-gene panel, and over the 56-gene QC-filtered narrow panel with every key suffixed `_narrow_set` (both from one correlation pass). |
| **M** | `xb_` | Mean Spearman correlation between sample pairs from *different* `RNA_BATCH` levels, split by whether they share `Diagnosis_cell_type_unified`. `xb_rank_agree_ratio` is the same-biology minus different-biology margin. |
| **N** | `pv_` | Leave-one-`RNA_BATCH`-out logistic regression on 10 PCs (PCA fitted on training batches only), for a 3-class (FL / DLBCL / Normal_B) and a 2-class (FL vs DLBCL) target, with a 100-permutation label-shuffle control. |

**Run scope.** Every attempt that already has a metrics sidecar: **2,323 non-Shambhala**
attempts by default (S3 holds 3,835 sidecars in total, 1,512 of them Shambhala, which is
excluded from Article 1). Added to completed jobs via the existing incremental sentinel
mechanism, so A–K are never recomputed.

**Excluded from the clustermap and the composite score.** The ~80 new scalar columns live in
the same `metrics_comprehensive.csv` as A–K but are stripped from `metric_cols` by
`_BLIND_CHECK_PREFIXES = ("mk_", "xb_", "pv_")` in `figures_helpers.load_metrics_data()`, with
an assertion that fails if one ever leaks. `scoring_cols` stays at **87** and the analysis set
at **2,234** rows. They are not part of the A > B > J > K hierarchy.

**Reference rule.** Only Group L reads a second matrix: `exp/{strat}__{imp}__01_raw__post0.tsv.gz`,
intersected down to the job's own sample index. `01_raw__post1` would be wrong because
post-removal drops outlier batches identified on the *harmonized* matrix, so its removed
batches differ per method; intersecting the post0 reference is also what restricts a `post1`
job to the post-removal-surviving samples. Groups M and N read one matrix and get their
baseline from the `01_raw` attempts downstream via `attach_raw_baseline()`.

**Known ceiling of Group L (must be stated in the manuscript).** Any harmonizer applying a
per-batch monotone transform of each gene — per-batch centering, scaling, z-score, median
scaling, and to first order ComBat / limma `removeBatchEffect` — leaves within-cohort Spearman
correlations unchanged, so Group L sits at ~1.0 for that whole method class by construction.
Verified empirically in `test_mock_metrics.test_group_l_correlation_preservation`
(per-batch shift → ρ = 1.0000). Group L is a "nothing broke" guard rail; **Group M's margin
carries the discriminative conclusion.**

**Fold rules in Group N.** F1 is computed on every fold, single-class test batches included —
a predictor facing a DLBCL-only batch should label as many of its samples DLBCL as it can,
which is the honest deployment test. AUC is restricted to folds whose test batch holds ≥2
classes. `n_folds` and `n_folds_multiclass` must accompany every quoted mean. Group N never
imputes: residual NA genes and all-NA samples are dropped and counted in
`pv_n_genes_dropped_na` / `pv_n_samples_dropped_na`.

**Gene panel.** `marker_gene_annotation.csv` — 633 unique genes across 63 signatures (834
gene × signature rows), 15 housekeeping controls, annotated with cell type, pathway, Kotlov LME
subtype, prognostic significance, source article and provenance. The signature memberships are
read verbatim from the published supplementary tables: Kotlov Table S1 (22 FGES gene sets) and
Tables S2/S3 (cell-of-origin and double-hit classifier panels), Holmes Table S2 (the 13
single-cell GC B-cell clusters, top 20 up-regulated genes per cluster by log2 fold change), and
Dybkaer Data Supplement 1 (nonzero-weight genes from the Centroblast and Centrocyte columns of
the normal B-cell subset classifier).
**Narrow panel (2026-09-04).** A `in_narrow_set` flag in the same CSV marks the **56 genes**
that both resolve in all 42 `01_raw__post0` matrices (193 genes pass that alone) and sit out of
the log2 noise band (mean `frac_lt_1` < 0.20 on those references). Group L reports its integrative
aggregates over this subset as well, suffixed `_narrow_set`, so a panel mean is available that
does not mix reliably measured genes with barely detected ones. Exactly one of the 56 (`PGK1`) is
a housekeeping control, and only **6 of the 15** housekeeping genes clear the same all-42-pairs
coverage bar (`ACTB`, `GAPDH`, `PSMB4`, `RPL13A`, `RPLP0`, `SDHA`, `TUBB`, `UBC`, `YWHAZ` do not,
resolving in 26–33 pairs). The marker-versus-housekeeping margin is therefore reported against
both controls — the full panel (`mk_rho_marker_minus_hk_narrow_set`, a variable-composition
control set) and `PGK1` alone (`mk_rho_marker_minus_PGK1_only_narrow_set`, coverage-matched but
n = 1) — and which is less noisy is settled empirically in §3b of
`correlation_prediction_metrics_analysis_narrow_set.ipynb`, not by argument.

Coverage audited across all 42 `(strat, imp)` pairs: **178 genes present in every pair** (the
set used for cross-attempt averages), 325 in some, 45 in none. CD20 (`MS4A1`), CD3
(`CD3D`/`CD3E`), CD10 (`MME`), CD23 (`FCER2`), CD79A/B, PD-1 and even `ACTB`/`GAPDH` are absent
from the `strict` full-coverage intersection but present in 26–33 of the 42 pairs via the `knn`
and `softimpute` matrices — so the article must report coverage per gene rather than claiming
the markers were unavailable.

### 5. Gene set analysis — new "Part 2" of `harmonization_metrics_analysis_v3.ipynb` (§5–§11, July 2026)

A second analytical layer added on top of the metrics comparison, tracking gene-level cost of each batch-removal strategy rather than sample-level batch metrics:

```
Per-job gene lists (S3 `genes/*.json`) → §6 download & structure
→ §7 gene count / pairwise overlap (Jaccard clustermap, Supervenn, Sankey by strategy × imputation)
→ §8 progressive gene accumulation/depletion curves (gene count vs. strategy harshness)
→ §9–§10 GO enrichment setup + progressive GO-term accumulation curves across the harshness axis
→ §11 FL-specific marker gene retention: which curated gene sets survive each strategy
```

**Curated gene sets used in §11** (with citations — new literature anchors, see below): FL transcriptomic subtype markers C1/C2/C3 (Xochelli et al. 2025, *Leukemia*), GC B-cell markers (Centroblast/Centrocyte; Dybkaer et al. 2015, *J Clin Oncol*, PMC4397280, Data Supplement 1), FL PFS prognostic signature (Pastore et al. 2019 — same reference already tracked as "FL PFS signature 2019"), POD24 mutation markers (Huet et al. 2018, *Blood*), PROGENy pathway-activating genes (Schubert et al. 2018), housekeeping genes as a stability reference (Eisenberg & Levanon 2013).

**Purpose:** answers "what is the biological cost of aggressive sample removal?" — a question the batch-metrics pipeline (groups A–K) does not address, since those metrics only see genes that survive filtering, not which genes are lost.

---

## Internal B-Cell Classifier

### Five cell types
| Type | Marker phenotype |
|---|---|
| Naive | CD45RA+, IgD+, CD27− |
| Centroblast | GC dark zone (DZ), proliferating |
| Centrocyte | GC light zone (LZ), undergoing selection |
| Memory | CD27+, post-GC |
| Plasma | Antibody-secreting, post-GC |

- Input: rank-transformed expression (platform-independent)
- Model: `LogisticRegression(penalty='l2')`, one-vs-all; `C` tuned via `GridSearchCV`
- Feature selection: SHAP + holdout stability across 8 held-out GEO cohorts; ~30–50 genes per type

```python
scores = calc_bcell_type_one_vs_all(expression_matrix)
# Returns DataFrame [samples × 5 cell types], probability scores
```

---

## Implementation Patterns

### R interop (use `localconverter` for all new code)
```python
from rpy2.robjects.conversion import localconverter
_PD_CONVERTER = ro.default_converter + pandas2ri.converter

with localconverter(_PD_CONVERTER):
    r_X = ro.conversion.py2rpy(df)
    result = ro.conversion.rpy2py(r_result)
```

### SOM configuration
```python
pref = ro.ListVector({
    'dataset.name': 'MyCohort',
    'dim.1stLvlSom': 'automatic',
    'standard.spot.modules': 'kmeans',
    'adjust.expression.values': False,  # data is pre-corrected
    'feature.centralization': True,
    'sample.quantile.normalization': True,
})
# Metagene clustering: AgglomerativeClustering(n_clusters=15, metric='euclidean', linkage='ward')
```
Never apply `adjust.expression.values=True` in oposSOM if data is batch-corrected. Apply `limma::removeBatchEffect` on `RNA_BATCH` before SOM input.

### S3 data management
```python
# Key pattern: "FL_batch_correction/exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz"
s3_key = s3_key_exp(strat, imp, method, post_rm)
upload_exp_to_s3(exp_df, s3_client, key)
exp_df = download_exp_from_s3(s3_client, key)
# bench_shared.py caches expression + filter strategies in /tmp as pickle for fast reload
```

---

## Article 1 — Manuscript Status (July 2026)

**Title:** Bulk transcriptomic harmonization tools benchmarking using germinal center lymphoma dataset: a novel computational pipeline ComboBatch reveals MNN and SVA as top performing methods  
**File:** `figures_for_article/FL_harmonization_article.docx` (working draft); `_v2_suggestions.docx` (reviewer pass); `_v3_reviewed.docx` (latest)  
**Authors:** Daniil Nikitin, Arsen Arakelyan, Nicolas Borisoff, Maria Savchenko, Anatoly Bobe, Alexandr Bagaev

**Key article statistics:**
- 7,174 samples; 88 cohorts; 4 platforms; 4,466 DLBCL + 1,697 FL + ~1,000 normal B cells
- 14 batch removal strategies; 3 imputations (strict, KNN, softimpute); 31 harmonization methods
- 2,407 harmonization attempts run → 2,234 passing QC filter (< 5% fully-NA samples)
- 87 scoring metrics (of ~230 computed); polarity defined for each

**⚠ Manuscript regression — flag for Daniil:** `FL_harmonization_article_v3_reviewed.docx` (latest, 2026-06-27) has the same section headings as v1/v2 but only **585 words** total vs. **4,392 words** in the working draft — most narrative prose in Abstract, Introduction, Results, and Discussion has been stripped back to figure/table captions and placeholder text (e.g. "We ran KNN imputation using the parameters … according to …", "Table N. Harmonization methods utilized in this study."). It also carries a different title-page affiliation ("Institute of Molecular Biology, National Academy of Science of the Republic of Armenia", `danya.nikitin.orel@gmail.com`) instead of the BostonGene affiliation used elsewhere. Unclear whether this is an intentional skeleton reset (to rebuild prose around finalized figures) or an accidental content loss — worth checking before further edits build on top of v3.
- New content visible in the v3 skeleton: **Figure 3** caption now reads "Cluster map of 2234 harmonization attempts (columns) in a space of 87 quality metrics (rows)" and **Table 1** is captioned "Best harmonization approaches groups identified via the integrative clustermap assessment" — both now anchored to concrete figures rather than stubs.

**Section status (per working draft, `FL_harmonization_article.docx`):**
- Introduction: 3 paragraphs drafted; dataset description paragraphs written
- Results: batch removal + imputation section mostly written; clustermap section partial; best approaches/decision tree = stubs
- Materials & Methods: dataset assembly + batch annotation + hardware written; imputation/methods/metrics = stubs
- Discussion: Quartet project comparison partially written; rest = stubs (external reviewer: Masha S)
- Abstract: not written

**Figures for article** (status tracking file moved to `figures_for_article/implementation_plans_old/article_figures_status_260625.md`; the top-level planning `.md` files referenced by `figures_for_article/CLAUDE.md` — `article_figures_status_260625.md`, `notebooks_for_figures_260625.md`, `finally_assembled_figures_plan_260626.md`, `pipeline_scheme_figure_plan_260604.md`, etc. — were archived into `implementation_plans_old/` on 2026-07-03; `CLAUDE.md`'s paths to these files are now stale and should be repointed):
- Fig 1 (dataset + pipeline): all 4 panels done
- Fig 2A (Circos-Sankey strategies): done; Fig 2C (NA genes) and 2D (imputation Sankey): done (Supp A/B)
- Fig 3 (harmonization clustermap, 2,234 × 87): done
- Fig 7–9 (local/structural/distribution metrics, cross-metric correlation): done
- **Fig 10 (composite ranking + best profiles): now fully done**, including 6 new decomposition barplots (`barplot_composite_score_by_{method,strat}_metric_{column,group,type}.svg`) and a refined ranking lollipop (`ranking_composite_score_all_approaches.svg/pdf`) with strategy/imputation/method color-coded annotation bars beneath each point
- Fig 11 (decision tree, 4 levels): done
- **Supp A2 (NA samples per strategy): now done** (`suppA2_na_samples_per_strategy.svg/png`) — barplot motivating the `pct_samples_allNA < 0.05` QC filter used to build `df_ok`; confirms all 14 strategies stay under the 5% threshold after filtering
- Remaining gap: Supp 9 (embeddings) is still a placeholder pending Tolya's external PCA/UMAP/tSNE coordinates; Supp C panel C (GO enrichment) still has a `gseapy.enrichr()` stub

---

## Key Conclusions (June 2026)

1. **Most harmonizers fail subtle biology**: Only MNN, FSQN R, and SVA can preserve FL/DLBCL/normal GC B cell differences. All other methods were designed for TCGA/GTEx-scale variation — their resolution is insufficient for lymphoma subtype differences.
2. **Strategy is the dominant factor** (strategy > method > post-removal > imputation).
3. **FFPE-only + SVA is a new breakthrough**: for the first time, all three FFPE platform types (NGS, Affymetrix, Illumina microarray) mix locally. Previously considered impossible.
4. **Global metrics can be misleading**: good PCR/R² does not guarantee local mixing. Microarray-only strategies produce artificially good global metrics by grouping batches into large meta-clusters.
5. **Shambhala excluded from Article 1**: confirmed not useful for cross-platform harmonization of this lymphoma dataset.
6. **FSQN R** (adopted before the AI-assisted benchmark) was already among the best methods; the systematic benchmark confirmed and refined this choice.
7. **AI-assisted discovery**: FSQN R was found manually; MNN and SVA were identified with AI assistance — the benchmark confirmed both approaches.

## Known Issues and Limitations

1. **Mixed-platform SOM is unreliable**: microarray and RNA-seq data cannot be fully harmonized for SOM — platform effect dominates cell-type biology in metagene space even after FSQN. Restrict SOM to RNA-seq only if possible.
2. **Normal_B_cells vs Kassandra**: residual platform batch effect after FSQN. GC B-cell types (Centroblast, Centrocyte) are only present in Normal_B_cells.
3. **Gene coverage trade-off**: full-coverage genes (no NA) limits analysis to ~3,520 genes; relaxing to >5,000 non-NA gives ~5,000+ genes but requires NaN handling.
4. **FFPE vs FF**: tissue preservation type creates visible separation in mixed-platform datasets; handle with preservation-type sub-strategies.
5. **Large B-cell P/Q references**: NBlegacy (733), NBext (878) are larger than most FL cohort subgroups — risk of over-calibrating toward normal B-cell baseline and compressing tumor subtype signal.
6. **Local metrics universally fail for cross-platform**: kBET, iLISI, cLISI all fail when RNA-seq and microarrays are combined — this is a fundamental limitation, not method-specific.

---

## Literature Anchors

| Reference | Relevance |
|---|---|
| Loeffler-Wirth et al. 2019 | oposSOM: SOM patterns predict OS in B-lymphomas |
| Loeffler-Wirth et al. 2022 | Continuous LZ↔DZ transitions between lymphoma subtypes via SOM |
| Franks et al. 2018, *Biostatistics* | FSQN algorithm |
| Borisov 2022, *Briefings in Bioinformatics* | Shambhala2: CuBlock + quantile normalization |
| FL subtypes 2025 | C1/C2/C3 molecular subtypes: doi:10.1038/s41375-025-02603-9 |
| FL PFS signature 2019 | ~20-gene PFS predictor: https://pubmed.ncbi.nlm.nih.gov/29475724/ |
| SOM projection method | Projecting onto reference SOM: https://www.mdpi.com/2673-7426/2/1/4 |
| Büttner et al. 2019 | kBET batch effect test |
| Korsunsky et al. 2019 | Harmony + LISI metrics |
| Voss et al. 2022 | HarmonizR: BEAM-aware harmonization |
| Goh et al. 2023 / 2025 | BEAM missing data framework |
| Tran et al. 2020, *Nat Methods* | 14-method scRNA-seq integration benchmark; motivates PCA R² as primary composite-score metric |
| Luecken et al. 2022, *Nat Methods* (scIB) | Batch/biology 60/40 weighting scheme; motivates the 60/35/5 composite score weights (§4.1) |
| Xochelli et al. 2025, *Leukemia* | FL transcriptomic subtypes C1/C2/C3 marker genes (doi:10.1038/s41375-025-02603-9 — same paper as "FL subtypes 2025" above); used as a curated gene set in gene-retention analysis (§11) |
| Huet et al. 2018, *Blood* | POD24 mutation marker genes; curated gene set in §11 (doi:10.1182/blood-2018-03-837443) |
| Schubert et al. 2018, *Nat Commun* | PROGENy pathway-activating genes; curated gene set in §11 (doi:10.1038/s41467-017-02391-6) |
| Eisenberg & Levanon 2013, *Trends Genet* | Housekeeping gene reference set for expression stability; curated gene set in §11 (doi:10.1016/j.tig.2013.05.010) |
