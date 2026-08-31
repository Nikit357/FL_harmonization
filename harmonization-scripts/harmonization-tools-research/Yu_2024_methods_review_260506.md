# Yu et al. 2024 — Large-Scale Omics Batch Effect Review

**Paper:** Yu Y, Mai Y, Zheng Y, Shi L. "Assessing and mitigating batch effects in large-scale omics studies." *Genome Biology* 25:254 (2024). https://doi.org/10.1186/s13059-024-03401-9  
**PMC:** https://pmc.ncbi.nlm.nih.gov/articles/PMC11447944/  
**Review date:** 2026-05-06

**Context:** ~5,444 samples, 88 cohorts, 4 platforms (Affymetrix GPL570, Illumina NGS, Illumina microarray, Agilent microarray). Reference batch: RNASeq_FF_PolyA (n=1,039). Current benchmark winner: FSQN R (`16_fsqn_r`) at ~16% PCA variance explained by batch (raw baseline ~95%). Benchmark covers 25 methods × 10 filter strategies × 4 imputation options; `26_xpn`, `27_dwd`, `28_npn` planned.

---

## Paper Overview

This is a broad methodological review covering batch effect sources, evaluation metrics, and correction algorithms across the full spectrum of large-scale omics: bulk RNA-seq, scRNA-seq, proteomics, metabolomics, WGS, DNA methylation, miRNA-seq. The paper categorizes batch effect correction algorithms (BECAs) into four families:

- **Location-Scale (LS):** ComBat variants, ratio-based methods
- **Matrix-Factorization (MF):** SVA variants, RUV variants, EigenMS, LIMBR
- **Distance-Neighborhood (DN):** mnnCorrect, deepMNN
- **Deep-Learning (DL):** AutoClass, DESC, scGen, scVI

The paper's central empirical claim is that ratio-based profiling (scaling sample values against concurrently profiled universal reference materials, as used in the Quartet consortium) is broadly effective for prospective multi-omics integration. For retrospective datasets assembled from pre-existing studies — our situation — the paper explicitly acknowledges that ratio-based methods are "not applicable."

**Critical limitation relative to our benchmark:** This is a review paper, not a primary benchmarking study. It does not present head-to-head quantitative comparisons of the methods it surveys on a common bulk RNA-seq cross-platform dataset (microarray + NGS). The paper's own empirical data is restricted to the Quartet RNA reference materials (27 libraries across 3 batches of B-lymphoblastoid cell lines). No external cohort or multi-cohort generalization is shown. All deep learning method assessments are qualitative.

---

## Methods Already in the Benchmark — Excluded from Detailed Analysis

| Paper method | Benchmark key(s) | Notes |
|---|---|---|
| ComBat (standard) | `05_combat` | Empirical Bayes; corrects to overall mean |
| ComBat-seq | `06_combat_seq`, `08_inmoose_combatseq` | Count-data RNA-seq variant |
| pyComBat | `07_pycombat` | Python port |
| SVA and variants (dSVA, pSVA, svapls, SVAseq) | `04_sva` | Surrogate variable approach |
| RUVseq | `09_ruv` | RUVg with housekeeping negative controls |
| mnnCorrect / fastMNN | `10_mnn` | Mutual nearest neighbor |
| Harmony | `11_harmony` | PCA-space correction |
| Scanorama | `12_scanorama` | Embedding correction |
| HarmonizR | `21_harmonizr` | NA-aware ComBat/limma wrapper |
| limma `removeBatchEffect` | `03_limma` | Linear model batch subtraction |
| DESeq2 VST | `23_vst` | RNA-seq only |
| TMM (edgeR) | `22_tmm` | RNA-seq only |

---

## Methods Not in Benchmark — Individual Assessments

### M-ComBat (Modified ComBat)

**Algorithm:**

M-ComBat is ComBat with the `ref.batch` parameter set. Standard ComBat shifts each batch's feature distributions toward the overall (weighted) mean of all batches. M-ComBat instead shifts all batches toward the distribution of one pre-specified reference batch:

1. Fit the same empirical Bayes linear model as standard ComBat: for each gene g in batch b,  
   `Y_gb = α_g + X·β_g + γ_gb + δ_gb · ε_gb`  
   where γ_gb is the additive batch effect and δ_gb is the multiplicative effect.
2. Estimate γ_gb and δ_gb via empirical Bayes shrinkage (pooling information across genes).
3. **Key difference from standard ComBat:** corrected values are anchored to the reference batch's location and scale, not the global mean. The reference batch's own values are returned unchanged; all other batches are transformed to match the reference.

This is implemented in `sva::ComBat(..., ref.batch = "RNASeq_FF_PolyA")` — a single parameter change versus our existing `05_combat`.

**Relationship to existing benchmark:**

Our `normalize_combat` (`05_combat`) calls `sva::ComBat(dat, batch, mod)` without `ref.batch` — it corrects to the global mean. M-ComBat would correct to the `RNASeq_FF_PolyA` reference batch. This is a genuinely distinct method in our benchmark context, differing in target distribution.

**Assessment for this project:**

The correction mechanism (linear EB shift + scale) is the same as standard ComBat. The difference is whether to target the global mean or `RNASeq_FF_PolyA`. Since our benchmark already runs FSQN against `RNASeq_FF_PolyA` (feature-specific distribution matching to the same reference) and ComBat without ref.batch, M-ComBat would occupy the logical gap: "global EB correction toward the reference rather than the mean." Expected performance: better than `05_combat` (less distortion from targeting a concrete reference) but likely worse than FSQN (EB is batch-level, not feature-specific). Priority: low — informative to compare but unlikely to beat FSQN.

**Code:** Available in R `sva` package (Bioconductor), already installed for `05_combat`. Implementation is trivial: add `ref.batch="RNASeq_FF_PolyA"` to the existing `sva_r.ComBat()` call.

**Verdict: Low priority for benchmark addition.** Mechanistically distinct from `05_combat` but likely to underperform FSQN since it operates at the batch location/scale level, not per-gene distribution. Could be added as `29_combat_ref` with minimal implementation effort — single parameter change.

---

### reComBat (Regularized ComBat)

**Algorithm:**

reComBat replaces the ordinary least squares regression in ComBat's batch estimation step with ridge regression, specifically to handle settings where batch and biological covariates are highly correlated (batch effect is partially confounded with biology):

1. Same EB model structure as ComBat, but the batch effect estimator γ̂_gb uses ridge regression:  
   `γ̂ = (X^T X + λI)^{-1} X^T y`  
   with λ tuned to prevent overfitting in the correlated batch-biology case.
2. Shrinkage parameter λ is selected via cross-validation or BIC.
3. The EB pooling step otherwise proceeds as standard ComBat.

**Assessment for this project:**

Our benchmark metric (one-way ANOVA R² of RNA_BATCH on PCA axes) specifically targets the batch dimension. Our annotation design has batch and biology partially confounded: FFPE samples come disproportionately from certain diagnosis groups (GPL570_FFPE cohorts are enriched in DLBCL, RNASeq_FFPE in mixed diagnoses). This is exactly the setting reComBat was designed for.

However, our existing `05_combat` already uses a biology covariate (`mod=model.matrix(~bio_col)`) in the ComBat call, which partially addresses this confounding. reComBat's regularization adds robustness in extreme confounding scenarios. Given that `05_combat` achieves a reasonable but not leading R² in our benchmark, reComBat is unlikely to substantially exceed it — the confounding in our dataset is moderate, not extreme.

**Code:** R package `reComBat` available on GitHub (https://github.com/bioFAM/reComBat). Not on CRAN or Bioconductor; would require `remotes::install_github("bioFAM/reComBat")` in `install_r_packages.R`.

**Verdict: Low priority.** Addresses a real issue (batch-biology confounding) present in our dataset, but the improvement over `05_combat` is likely marginal. Could be added if a targeted analysis of confounded batches becomes relevant.

---

### RUV-III-PRPS (Remove Unwanted Variation III — Pseudo-Replicate Pseudo-Samples)

**Algorithm:**

Standard RUV-III requires technical replicates (the same sample measured twice) or spike-in negative controls to estimate the unwanted variation subspace. RUV-III-PRPS removes this requirement by constructing pseudo-replicates from samples sharing the same biological label:

1. Partition samples into homogeneous biological groups using known labels (e.g., diagnosis, cell type).
2. Within each biological group × batch cell, compute the within-group mean expression vector. This mean is the pseudo-replicate for that cell.
3. Construct a pseudo-sample matrix: each pseudo-replicate represents a "virtual technical replicate" of the biological group in that batch.
4. Apply standard RUV-III to the pseudo-replicate matrix to estimate the unwanted variation factors W.
5. Regress W out of the original expression matrix: `Y_corrected = Y - W·α̂`

The key innovation is that no actual matched samples are required — pseudo-replicates are derived analytically from the label structure.

**Assessment for this project:**

Our dataset has a clear biological label structure: `Diagnosis_cell_type_unified` with DLBCL GCB, DLBCL ABC, FL, normal B-cell subtypes. These could serve as the homogeneous biological groups for pseudo-replicate construction, provided each group has sufficient representation across multiple batches to build meaningful pseudo-replicates.

*Practical constraint: sparse group × batch cells.* With 88 cohorts and 6+ RNA_BATCH labels, many (group × batch) combinations will have very few samples. For example, Centroblasts (Normal_B_cells normal cells) may exist in only 1–2 batches. Sparse cells produce noisy pseudo-replicates that degrade RUV-III estimation. This is a genuine concern at our scale (88 cohorts) that was not encountered in the original RUV-III-PRPS validation (which used small, well-balanced datasets).

*Comparison with existing `09_ruv`.* Our `09_ruv` (RUVg) uses 10 housekeeping genes as negative controls and does not require biological group labels — it relies on genes assumed to be unaffected by biology. RUV-III-PRPS uses a complementary assumption: that within-group mean expression is biology and across-group variance is batch. Both assumptions are imperfect for our mixed-diagnosis, mixed-platform data.

**Code:** R package `ruv` on Bioconductor (`BiocManager::install("ruv")`) implements the full RUV family including RUV-III. RUV-III-PRPS as described in the paper may require the development version or manual implementation of the pseudo-sample construction step. The `ruv::RUVIII()` function accepts a pseudo-replicate indicator matrix M.

**Verdict: Medium priority, implementation non-trivial.** Conceptually compelling — avoids the negative-control gene assumption — but requires careful construction of the pseudo-replicate matrix from our diagnosis labels. Sparse group × batch cells could degrade performance at 88-cohort scale. Worth exploring if `09_ruv` and `05_combat` tier results remain insufficient after the full benchmark completes.

---

### Neural Network Methods — Group Assessment

The paper surveys four deep learning methods: **AutoClass**, **DESC**, **scGen**, and **scVI**, plus the distance-neighborhood hybrid **deepMNN**. All five share the same fundamental scope limitation for this project. They are assessed together because the verdict for each follows the same logic.

#### AutoClass

A neural network-based clustering and classification method. The paper provides no algorithmic details; the name suggests it is a deep classifier for cell type assignment with implicit batch correction. Designed for scRNA-seq; no bulk application described. No package details given in the review.

#### DESC (Deep Embedded Single-cell Clustering)

Li et al. DESC uses a deep autoencoder with a self-supervised clustering objective. The architecture compresses the expression matrix to a low-dimensional embedding, then iteratively refines cluster assignments. The corrected output is the low-dimensional embedding, not a reconstructed expression matrix in the original gene space. Even if applied to bulk data, DESC's output format (embedding) is incompatible with our pipeline's requirement for a genes × samples matrix for oposSOM and ssGSEA. This is the same blocker that excludes HARP (`HARP_usage_perspectives.md`) and MoDAmix (`MoDAmix_not_useful.md`).

#### scGen (Single-Cell Generation)

Lotfollahi et al. scGen uses a Variational Autoencoder (VAE) conditioned on batch identity to learn a correction vector via latent arithmetic. The architecture:

1. Encoder: maps cell expression to mean + variance of Gaussian latent space (z-dim ~10–100)
2. Batch conditioning: batch label encoded as one-hot input to encoder and decoder
3. Correction: the "batch vector" is estimated as the mean latent code of source batch minus target batch for biologically matched cells
4. Decoder: reconstructs corrected expression matrix from shifted latent code

scGen's correction is applied in latent space and decoded back to the original gene space — so technically it does output a genes × samples expression matrix. However, it requires biologically matched cell populations across batches (the batch vector estimation assumes cells from both batches with the same cell type exist) and was designed and validated exclusively on scRNA-seq.

For our dataset, the VAE decoder re-generates expression values in the original 3,520-gene space. However, the model requires substantial training data per batch (typically >1,000 cells per cell type per batch), which our mixed-platform cohorts do not satisfy. More critically, the Gaussian encoder model is designed for count data (negative binomial distributed in scRNA-seq); our already-log2-normalized bulk microarray values violate this distributional assumption. No published validation of scGen on bulk microarray + RNA-seq integration exists.

#### scVI (Single-Cell Variational Inference)

Lopez et al. scVI uses a hierarchical VAE with a negative binomial output distribution (modeling scRNA-seq count data):

1. Encoder: x → z (latent + library size scaling factor s)
2. Latent space: batch label injected as auxiliary variable  
3. Decoder: (z, s, batch_label) → normalized expression (via NB likelihood)
4. Batch correction: sampling z without batch label and decoding gives "batch-corrected" expression

scVI outputs both a latent embedding AND a normalized expression matrix (via `get_normalized_expression()` in the `scvi-tools` Python package). Technically it could be run on bulk RNA-seq count data. However:
- The NB model is designed for sparse integer counts; log2-normalized microarray values are not valid inputs.
- No cross-platform (microarray + RNA-seq) validation exists.
- The `scvi-tools` package explicitly targets scRNA-seq.
- Applying scVI to 5,444 bulk samples across 88 cohorts would require treating each cohort as a "batch," which the model can handle numerically, but the biological assumptions (each cohort contains the same cell type composition) are violated for our mixed-diagnosis dataset.

#### deepMNN

deepMNN extends the mutual nearest neighbor approach by using a deep neural network to refine the MNN correction step for scRNA-seq. It is a more powerful variant of our existing `10_mnn`. It requires finding mutual nearest neighbors between batches — an assumption that biologically matched populations exist in each batch. For our mixed-platform bulk data, this is the same alignment assumption that already limits `10_mnn`'s performance. deepMNN adds a neural network on top of an already-underperforming baseline for our data type.

#### Structural blockers common to all five neural network methods

| Blocker | scGen | scVI | DESC | AutoClass | deepMNN |
|---|---|---|---|---|---|
| Designed for scRNA-seq, not bulk | ✗ | ✗ | ✗ | ✗ | ✗ |
| Count data model (NB/Poisson); our data is log2 | ✗ | ✗ | — | — | — |
| No cross-platform (microarray+NGS) validation | ✗ | ✗ | ✗ | ✗ | ✗ |
| Output format incompatible (embedding only) | — | Partial | ✗ | ✗ | — |
| Over-correction risk on bulk data | ✗ | ✗ | ✗ | ✗ | ✗ |

The paper itself states: *"DL-based BECAs are often used in scRNA-seq because scRNA-seq data are high-dimensional and highly heterogeneous"* and *"investigators should be aware of the risk of overfitting when DL-based BECAs are applied."* No evidence is presented that any DL method outperforms classical methods on bulk multi-platform data.

The scBatch precedent (`scBatch_usage_perspectives.md`) already establishes the verdict for scRNA-seq-specific methods applied to bulk data. All five neural network methods are NOT APPLICABLE for the same reason.

---

### Ratio-Based Method (Quartet Reference Material Approach)

**What it is:** Scales each sample's feature values by the concurrently profiled universal reference material (same-run control) rather than correcting absolute expression levels. If sample S and reference R are measured in the same sequencing run, the ratio S/R is compared across platforms instead of the absolute values.

**Fatal blocker:** The paper explicitly acknowledges this method "is not applicable when combining already-existing datasets." Our 88 cohorts were assembled retrospectively from 46+ independent studies; no concurrent reference material was profiled alongside any of them. There is no R-value to divide by.

**Verdict: NOT APPLICABLE.** Requires prospective study design with concurrent reference materials; not applicable to retrospective multi-cohort assembly.

---

## Paper Scope and Value for This Project

Despite the large number of methods reviewed, this paper's primary empirical contribution (Quartet RNA-seq reference data) is a 3-batch balanced design with 27 libraries — very different from our 88-cohort retrospective assembly. The paper's method taxonomy is a useful reference but does not contain comparative benchmarking results on multi-platform bulk data.

**Indirect value — confirms existing benchmark structure:**

1. The paper validates that SVA, ComBat, and RUV variants are the established tools for bulk RNA-seq batch correction, matching our existing `04_sva`, `05_combat`, `09_ruv` entries.
2. The paper's description of M-ComBat highlights that reference-batch targeting is a distinct and valid variant of ComBat — relevant to understanding why FSQN (reference-batch distribution matching) outperforms standard ComBat (global-mean targeting) in our benchmark.
3. The explicit acknowledgment that DL methods are scRNA-seq-specific confirms that the entire DL family can be excluded from bulk harmonization benchmarks without detailed per-method investigation.

**Note on method naming:** The paper's "M-ComBat" (ref.batch targeting) is distinct from the acronym "M-ComBat" used in other literature for "multi-dataset ComBat" — the paper's usage is `sva::ComBat(..., ref.batch=...)`.

---

## Comparison Table — New Methods vs. Current Benchmark

| Method | Category | Bulk applicable | Cross-platform (MH+NGS) | Output format | Code available | Priority |
|---|---|---|---|---|---|---|
| FSQN R (`16_fsqn_r`) | Reference | ✅ | ✅ | Expression matrix | R CRAN | — (current best) |
| ComBat (`05_combat`) | LS | ✅ | ✅ | Expression matrix | R Bioconductor | — (in benchmark) |
| M-ComBat | LS | ✅ | ✅ (not validated) | Expression matrix | R Bioconductor (sva) | Low — easy to add |
| reComBat | LS | ✅ | Not validated | Expression matrix | GitHub only | Low |
| RUV-III-PRPS | MF | ✅ | Not validated | Expression matrix | R Bioconductor (ruv) | Medium — non-trivial |
| scGen | DL | ❌ scRNA-seq | ❌ | Decoded matrix (bulk: untested) | Python (scvi-tools) | **Not applicable** |
| scVI | DL | ❌ scRNA-seq | ❌ | Matrix + embedding | Python (scvi-tools) | **Not applicable** |
| DESC | DL | ❌ scRNA-seq | ❌ | Embedding only | Python | **Not applicable** |
| AutoClass | DL | ❌ scRNA-seq | ❌ | Unknown | Unknown | **Not applicable** |
| deepMNN | DN/DL | ❌ scRNA-seq | ❌ | Expression matrix | Unknown | **Not applicable** |
| Ratio-based | Reference | ✅ (prospective) | ✅ | Expression matrix | Quartet tools | **Not applicable** |

---

## Summary Table

| Method | In benchmark? | New contribution? | Applicable? | Verdict |
|---|---|---|---|---|
| ComBat, ComBat-seq, pyComBat | ✅ `05–08` | No | — | Already covered |
| SVA variants | ✅ `04_sva` | No | — | Already covered |
| RUVseq | ✅ `09_ruv` | No | — | Already covered |
| mnnCorrect | ✅ `10_mnn` | No | — | Already covered |
| M-ComBat | ❌ | Yes (ref.batch variant) | Low priority | **Low priority add** — trivial implementation; likely underperforms FSQN |
| reComBat | ❌ | Yes | Low priority | **Low priority** — handles confounding; GitHub only |
| RUV-III-PRPS | ❌ | Yes | Medium priority | **Medium priority** — pseudo-replicate approach; sparse batches may limit performance |
| scGen | ❌ | No | **No** | **Not applicable** — scRNA-seq VAE; bulk not validated |
| scVI | ❌ | No | **No** | **Not applicable** — scRNA-seq NB model; bulk microarray violates distributional assumptions |
| DESC | ❌ | No | **No** | **Not applicable** — embedding output; scRNA-seq only |
| AutoClass | ❌ | No | **No** | **Not applicable** — scRNA-seq; no package details |
| deepMNN | ❌ | No | **No** | **Not applicable** — scRNA-seq extension of MNN |
| Ratio-based | ❌ | No | **No** | **Not applicable** — requires concurrent reference materials; not applicable to retrospective datasets |

---

## Overall Conclusion

No high-priority new normalization methods emerge from this paper for immediate benchmark addition. The paper's main contribution for our project is taxonomy and confirmation, not new tools.

**The five neural network / deep learning methods (scGen, scVI, DESC, AutoClass, deepMNN) are all NOT APPLICABLE.** They are designed for scRNA-seq, assume count data distributions incompatible with log2-normalized bulk microarray+RNA-seq data, lack cross-platform bulk validation, and in some cases (DESC) produce embedding outputs incompatible with oposSOM. The paper itself explicitly restricts DL method recommendations to scRNA-seq. See `scBatch_usage_perspectives.md` for the established precedent.

Two classical methods have residual interest:
- **M-ComBat** (`sva::ComBat` with `ref.batch="RNASeq_FF_PolyA"`) is a trivial parameter change from `05_combat` and could be added as `29_combat_ref`. Expected to improve on `05_combat` but remain well above FSQN's ~16% R². Low priority.
- **RUV-III-PRPS** avoids negative-control gene requirements by using biological group pseudo-replicates. Non-trivial to implement correctly for 88 cohorts and sparse group × batch cells, but conceptually sound for our diagnosis-labeled dataset. Medium priority if FSQN-tier improvements are still being sought.

**FSQN (`16_fsqn_r`) remains the benchmark winner.** The DL methods reviewed here represent the frontier for scRNA-seq integration but have no demonstrated relevance to bulk multi-platform omics harmonization at this time.

---

## Supplementary Table S1 — Complete Coverage of All 76 BECAs

This section systematically covers all 76 Batch Effect Correction Algorithms listed in Table S1 of Yu et al. 2024, providing pros and cons for each relative to this project. Methods already individually assessed in earlier sections of this document are cross-referenced. This section adds new individual assessments for methods not previously covered and provides group assessments for those outside the project's scope.

---

### Full Overview Table

| # | Method | Cat | Data type (abbreviated) | Rep | Benchmark status | Verdict |
|---|---|---|---|---|---|---|
| 1 | AMDBNorm | LS | RNA-seq/microarray | Y | Not in benchmark | Low — reference-batch distribution adjustment; conceptually redundant with FSQN |
| 2 | batchCorr | LS | LC-MS metabolomics | Y | Not applicable | NOT APPLICABLE — metabolomics only |
| 3 | BMC | LS | RNA-seq/microarray, scRNA-seq, LC-MS, DNA methylation | N | Not in benchmark | Very low — mean-centering; functionally covered by `02_median_scaling` |
| 4 | B-MIS | LS | LC-MS metabolomics | N | Not applicable | NOT APPLICABLE — metabolomics only |
| 5 | BRIDGE | LS | RNA-seq/microarray | Y | Not in benchmark | NOT APPLICABLE — requires bridge replicate samples across batches |
| 6 | ComBat | LS | RNA-seq/microarray, scRNA-seq, LC-MS | N | `05_combat`, `07_pycombat` | **In benchmark** |
| 7 | ComBat-seq | LS | RNA-seq | N | `06_combat_seq`, `08_inmoose_combatseq` | **In benchmark** |
| 8 | DWD | LS | microarray | N | Planned `27_dwd` | **Planned** |
| 9 | M-ComBat | LS | microarray | N | Not in benchmark | Low (see M-ComBat section) |
| 10 | PEER | LS | RNA-seq/microarray, scRNA-seq | N | `24_peer_k10` — blocked | **Blocked**: R 4.5 incompatible |
| 11 | QC-RLSC | LS | MS metabolomics | Y | Not applicable | NOT APPLICABLE — metabolomics only |
| 12 | Ratio | LS | RNA-seq/microarray, scRNA-seq, LC-MS, DNA methylation | Y | Not in benchmark | NOT APPLICABLE — requires prospective concurrent reference (see Ratio section) |
| 13 | reComBat | LS | RNA-seq/microarray | N | Not in benchmark | Low (see reComBat section) |
| 14 | Remeasure | LS | RNA-seq | Y | Not in benchmark | NOT APPLICABLE — requires matched samples across batches |
| 15 | XPN | LS | RNA-seq/microarray | N | Planned `26_xpn` | **Planned** |
| 16 | Z-scaled | LS | RNA-seq/microarray, scRNA-seq, LC-MS, DNA methylation | N | Not in benchmark | Very low — per-batch z-score; over-corrects biology |
| 17 | ARSyN | MF | microarray | N | Not in benchmark | Low — microarray only |
| 18 | cFIT | MF | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 19 | DASC | MF | RNA-seq/microarray, scRNA-seq | N | Not in benchmark | Low — semi-NMF; no cross-platform bulk validation |
| 20 | dSVA | MF | RNA-seq/microarray | N | `04_sva` (variant) | **In benchmark** (SVA family) |
| 21 | EigenMS | MF | LC-MS proteomics/metabolomics | N | Not applicable | NOT APPLICABLE — proteomics/metabolomics only |
| 22 | exploBATCH | MF | microarray | N | Not in benchmark | Low — microarray only |
| 23 | FAbatch | MF | microarray, DNA methylation | N | Not in benchmark | Low — microarray focus; covered by ComBat + SVA separately |
| 24 | Harman | MF | RNA-seq/microarray, LC-MS proteomics, DNA methylation | N | Not in benchmark | **Medium** — explicit overcorrection constraint; bulk-applicable; Bioconductor available |
| 25 | Harmony | MF | scRNA-seq | N | `11_harmony` | **In benchmark** |
| 26 | LIMBR | MF | LC-MS proteomics | N | Not applicable | NOT APPLICABLE — proteomics only |
| 27 | iNMF | MF | RNA-seq, miRNA-seq, DNA methylation | N | Not in benchmark | Low — multiomics NMF framework; designed for multi-data-type integration |
| 28 | LIGER | MF | scRNA-seq, scDNA methylation | N | Not applicable | NOT APPLICABLE — scRNA-seq/epigenomics only |
| 29 | limma | MF | RNA-seq/microarray, scRNA-seq, LC-MS proteomics | N | `03_limma` | **In benchmark** |
| 30 | mixEMM | MF | LC-MS proteomics | Y | Not applicable | NOT APPLICABLE — proteomics only |
| 31 | MultiBaC | MF | multiomics | N | Not in benchmark | NOT APPLICABLE — requires multiple concurrent omics data types |
| 32 | mvMISE | MF | LC-MS proteomics | Y | Not applicable | NOT APPLICABLE — proteomics only |
| 33 | POIBM | MF | RNA-seq | Y | Not in benchmark | NOT APPLICABLE for cross-platform — Poisson count model; microarray incompatible |
| 34 | PRPS (RUV-III-PRPS) | MF | RNA-seq | Y | Not in benchmark | Medium (see RUV-III-PRPS section) |
| 35 | pSVA | MF | microarray | N | `04_sva` (variant) | **In benchmark** (SVA family) |
| 36 | RUV-2 | MF | RNA-seq/microarray, LC-MS metabolomics | Y | `09_ruv` (ancestor) | **In benchmark** — RUVseq subsumes RUV-2 |
| 37 | RUV-III | MF | RNA-seq | Y | Related to `09_ruv` | Covered by PRPS/RUV-III-PRPS section |
| 38 | RUV-III-C | MF | LC-MS proteomics | Y | Not applicable | NOT APPLICABLE — proteomics only |
| 39 | RUV-III-NB | MF | scRNA-seq | Y | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 40 | RUV-random | MF | LC-MS metabolomics | Y | Not applicable | NOT APPLICABLE — metabolomics only |
| 41 | RUVseq | MF | RNA-seq | Y | `09_ruv` | **In benchmark** |
| 42 | scBatch | MF | RNA-seq, scRNA-seq | N | See file | NOT APPLICABLE (see `scBatch_usage_perspectives.md`) |
| 43 | scMC | DN | scRNA-seq, ATAC-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq/ATAC-seq only |
| 44 | scMerge | MF | scRNA-seq | Y | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 45 | scPLS | MF | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 46 | Seurat v2 (MultiCCA) | MF | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 47 | SVA | MF | RNA-seq/microarray, DNA methylation | N | `04_sva` | **In benchmark** |
| 48 | svapls | MF | RNA-seq/microarray | N | `04_sva` (variant) | **In benchmark** (SVA family) |
| 49 | SVAseq | MF | RNA-seq | N | `04_sva` (variant) | **In benchmark** (SVA family) |
| 50 | WaveICA / WaveICA 2.0 | MF | LC-MS metabolomics | N | Not applicable | NOT APPLICABLE — metabolomics only |
| 51 | ZINB-WaVE | MF | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 52 | BATMAN | DN | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 53 | BBKNN | DN | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 54 | BEER | DN | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 55 | deepMNN | DN | scRNA-seq | N | Not in benchmark | NOT APPLICABLE (see Neural Network section) |
| 56 | fastMNN | DN | scRNA-seq | N | `10_mnn` | **In benchmark** |
| 57 | IMGG | DN | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 58 | iSMNN | DN | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 59 | mnnCorrect | DN | scRNA-seq | N | `10_mnn` | **In benchmark** |
| 60 | Scanorama | DN | scRNA-seq | N | `12_scanorama` | **In benchmark** |
| 61 | Seurat v3 | DN | transcriptomic/epigenomic/proteomic/spatially resolved single-cell | N | Not applicable | NOT APPLICABLE — single-cell only |
| 62 | Seurat v4 | DN | multimodal single-cell (CITE-seq, SHARE-seq, ASAP-seq) | N | Not applicable | NOT APPLICABLE — single-cell only |
| 63 | SMNN | DN | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 64 | SSBER | DN | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 65 | AutoClass | DL | scRNA-seq | N | Not in benchmark | NOT APPLICABLE (see Neural Network section) |
| 66 | BERMUDA | DL | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 67 | CBA | DL | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 68 | Cell BLAST | DL | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 69 | DESC | DL | scRNA-seq | N | Not in benchmark | NOT APPLICABLE (see Neural Network section) |
| 70 | MAT2 | DL | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 71 | MMD-ResNet | DL | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 72 | NormAE | DL | LC-MS metabolomics | N | Not applicable | NOT APPLICABLE — metabolomics only |
| 73 | SAUCIE | DL | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 74 | scDML | DL | scRNA-seq | N | Not applicable | NOT APPLICABLE — scRNA-seq only |
| 75 | scGen | DL | scRNA-seq | N | Not in benchmark | NOT APPLICABLE (see Neural Network section) |
| 76 | scVI | DL | scRNA-seq | N | Not in benchmark | NOT APPLICABLE (see Neural Network section) |

---

### LS Methods — New Individual Assessments

Methods already covered in earlier sections or in the benchmark: ComBat (`05`, `07`), ComBat-seq (`06`, `08`), DWD (planned `27_dwd`), M-ComBat (see M-ComBat section), PEER (`24_peer_k10` — blocked by R 4.5 incompatibility), reComBat (see reComBat section), Ratio (see Ratio-Based section), XPN (planned `26_xpn`). New assessments follow.

---

#### AMDBNorm

**Full name:** Adjustment Mean Distribution-Based Normalization  
**Category:** LS | **Data type:** RNA-seq/microarray | **Replicate-based:** Yes | **PMID:** 34958674

**Algorithm:** Designates one batch as the reference and aligns the mean expression of each gene in non-reference batches to match the reference batch's mean, additionally adjusting the distributional shape of each feature. Combines mean-level adjustment (analogous to M-ComBat) with partial distribution matching (analogous to FSQN), operating feature-by-feature.

**Pros:**
- Applicable to bulk RNA-seq and microarray — consistent with our data types and cross-platform scope.
- Reference-batch targeting is conceptually aligned with our FSQN approach; using `RNASeq_FF_PolyA` as the reference is a natural fit.
- Works on retrospective data as long as a reference batch is defined — no concurrent reference material required (unlike the Ratio method).
- Corrects both mean and distributional shape at the feature level, which is stronger than BMC or median scaling alone.

**Cons:**
- Listed as replicate-based (Y): designed or validated with reference samples physically co-profiled alongside other batches. Without actual reference replicates, the "reference distribution" is approximated — which is what FSQN already does more rigorously via quantile matching.
- Functionally occupies the space between M-ComBat (mean-only EB) and FSQN (full feature-specific quantile distribution matching). FSQN is the stronger implementation of the same idea and is already our benchmark winner.
- No cross-platform (microarray + RNA-seq) benchmarking evidence in the original publication.
- Less established than FSQN (2021 vs. Franks et al. 2018); no independent large-cohort validation.
- No maintained R/Python package found in the original paper; implementation effort unclear.

**Verdict: Low priority.** AMDBNorm addresses the same problem as FSQN (reference-batch, feature-specific distribution alignment) but with a less rigorous adjustment. Since FSQN at `16_fsqn_r` already achieves ~16% PCA R², AMDBNorm is unlikely to improve on this. Not worth adding unless a maintained package is identified. 'here is a maintained package, use it https://github.com/JoevVan/AMDBNorm'

---

#### BMC (Batch Mean-Centering)

**Full name:** Batch Mean-Centering  
**Category:** LS | **Data type:** RNA-seq/microarray, scRNA-seq, DNA methylation, LC-MS proteomics/metabolomics | **Replicate-based:** No | **PMID:** — (no PMID; described as standard practice)

**Algorithm:** For each gene in each batch, subtracts the within-batch mean expression, setting every gene's mean to zero within every batch. Purely additive correction — removes mean-level batch shift per gene, leaves variance differences between batches untouched.

**Pros:**
- Completely parameter-free; no EB shrinkage, no reference batch, no negative controls required.
- Applicable to any omics data type in log2 space.
- Zero risk of model fitting failure (unlike ComBat on small batches).
- Deterministic and reproducible.

**Cons:**
- Corrects only additive (mean) batch effects. Multiplicative effects — variance and scale differences between platforms — are the dominant problem in our cross-platform dataset and remain untouched.
- Zero-centering destroys absolute expression level comparability: downstream methods relying on absolute expression (ssGSEA, FSQN-based comparisons, SOM input scaling) lose their biological reference scale.
- Strictly inferior to our existing `02_median_scaling`, which centers each batch to the global median rather than zero, preserving a meaningful cross-batch expression scale.
- The batch-composition confound in our data means different batches contain different diagnosis mixes; centering to zero conflates the batch mean shift with the biological composition difference.

**Verdict: Not worth adding.** BMC is a weaker variant of what `02_median_scaling` already provides. Zero-centering is actively harmful for downstream absolute-scale analyses. Already conceptually covered.

---

#### BRIDGE

**Full name:** Batch effect Reduction of mIcroarray data with Dependent samples usinG Empirical bayes  
**Category:** LS | **Data type:** RNA-seq/microarray | **Replicate-based:** Yes | **PMID:** 34905304

**Algorithm:** A three-step parametric empirical Bayes approach requiring "bridge samples" — the same physical specimens profiled across multiple batches. The bridge samples provide direct empirical cross-batch measurements; EB shrinkage pools information across genes for stable estimation of the batch transformation.

**Pros:**
- The most statistically principled LS method for multi-batch bulk integration: uses actual cross-batch replicate measurements to estimate batch effects without assumptions about biology.
- Applicable to bulk RNA-seq/microarray.
- EB shrinkage stabilizes estimation with a small number of bridge samples.
- No negative-control genes required; correction is data-driven from the bridge measurements.

**Cons:**
- **Fatal blocker:** Requires bridge samples — the same biological specimens measured in multiple batches. Our 88 cohorts were assembled retrospectively from independent studies; no sample was profiled in more than one batch. Identical blocker as COCONUT (`COCONUT_usage_perspectives.md`) and Remeasure.
- Even if bridge samples existed, they would need to span all 6 RNA_BATCH categories to enable full cross-platform correction.

**Verdict: NOT APPLICABLE.** Requires cross-batch replicate samples; retrospective assembly makes this structurally impossible.

---

#### Remeasure

**Full name:** (no full name given)  
**Category:** LS | **Data type:** RNA-seq | **Replicate-based:** Yes | **PMID:** 38177326

**Algorithm:** Uses a subset of samples measured in both batches to estimate the systematic batch offset, then applies the correction to all samples. The matched subset provides a direct within-study estimate of the batch transformation; no distributional or biological assumptions are required.

**Pros:**
- Statistically direct: learns the batch transformation from actual matched measurements, not distributional assumptions.
- No negative-control genes or reference distribution required.
- Reportedly does not require matched samples for every sample — learns from a representative subset.

**Cons:**
- **Fatal blocker:** Requires matched samples — the same biological specimens sequenced in at least two different batches. Identical blocker as BRIDGE and COCONUT.
- RNA-seq only per the table; our dataset includes microarray platforms.
- Even in RNA-seq-only analyses (strategy C), none of the 88 cohorts contributed samples to two different RNA_BATCH categories.
- Published 2024 (PMID 38177326); very limited independent validation.

**Verdict: NOT APPLICABLE.** Matched-sample requirement cannot be satisfied by our retrospective multi-cohort assembly.

---

#### Z-scaled

**Full name:** (no full name given; standard z-score normalization per batch)  
**Category:** LS | **Data type:** RNA-seq/microarray, scRNA-seq, DNA methylation, LC-MS proteomics/metabolomics | **Replicate-based:** No | **PMID:** — (standard practice)

**Algorithm:** For each gene within each batch: subtract the within-batch mean and divide by the within-batch standard deviation, yielding zero-mean, unit-variance expression within every batch. Standard z-scoring applied per batch per feature.

**Pros:**
- Extremely simple; no model fitting, no parameters, no prerequisites.
- Makes each gene's distribution identical across batches by construction: all batches have mean=0, sd=1 per gene.
- Cannot fail numerically (assuming non-zero variance).
- Applicable to any omics modality.

**Cons:**
- **Overcorrects biology:** Forcing unit variance within each batch eliminates all batch-specific variance — including genuine biological variance that co-varies with batch composition. Our batches are not biologically balanced (DLBCL/FL/normal cell proportions differ across batches), so z-scaling removes true biological signal along with the batch effect.
- Does not target any biologically meaningful reference distribution; z-scaled values lose absolute expression meaning and are incompatible with ssGSEA, SOM, or FSQN-based downstream analyses.
- Effectively a stronger version of BMC (corrects variance in addition to mean) with the same fundamental problem of destroying inter-batch absolute comparability.
- Our `02_median_scaling` preserves the global median reference point; z-scaling does not.

**Verdict: Very low priority, potentially harmful.** Z-scaling is expected to over-correct biology in our mixed-diagnosis dataset and produce misleading downstream results. The PCA R² metric may appear good (batch variance is forcibly set to zero) while biological signal is destroyed. Not worth adding.

---

### MF Methods — New Individual Assessments

Methods already covered in the benchmark or in earlier sections: SVA family (`04_sva`; includes dSVA, pSVA, svapls, SVAseq), limma (`03_limma`), Harmony (`11_harmony`), RUVseq (`09_ruv`), reComBat (see reComBat section), PRPS/RUV-III-PRPS (see RUV-III-PRPS section), scBatch (see `scBatch_usage_perspectives.md`). RUV-2 is the ancestor of RUVseq and is addressed briefly below. PEER is in the benchmark as `24_peer_k10` but raises NotImplementedError on R 4.5. New assessments follow.

---

#### ARSyN

**Full name:** ANOVA-simultaneous components analysis Removal of Systematic Noise  
**Category:** MF | **Data type:** microarray | **Replicate-based:** No | **PMID:** 22085896

**Algorithm:** Decomposes the expression matrix into experimental effects (biology), batch effects, and residuals using ANOVA-ASCA (Analysis of Variance — Simultaneous Component Analysis). PCA is applied specifically to the batch-effect component to identify directions of systematic noise; these directions are subtracted from the original data.

**Pros:**
- Explicitly models biological covariates and batch effects jointly using ANOVA, reducing risk of removing biology along with batch — a genuine advantage over unconstrained corrections.
- No negative-control genes required.
- The ANOVA decomposition is conceptually transparent: biology and batch are separated before any correction is applied.
- R package available on Bioconductor (`ARSyN`).

**Cons:**
- **Scope blocker:** Validated and implemented for microarray data only. RNA-seq (NGS batches) is not described or validated. Our 2,386 NGS samples would be excluded, leaving a microarray-only analysis — non-comparable to the full cross-platform benchmark.
- ANOVA decomposition assumes complete factorial balance (all biology × batch combinations represented), which is strongly violated in our sparse 88-cohort design with many (diagnosis × batch) cells having fewer than 5 samples.
- Bioconductor package compatibility with R 4.5 needs verification; the original package dates from 2012.
- The PCA correction step is a lower-dimensional approximation — batch effects outside the leading PCs may persist.

**Verdict: Low priority.** Microarray-specific scope prevents application to the full cross-platform dataset. Could be evaluated on `G_affymetrix_only` or `F_microarray_only` strategies, but this would yield non-comparable metrics to the primary benchmark.

---

#### DASC

**Full name:** Data-Adaptive Shrinkage and Clustering  
**Category:** MF | **Data type:** RNA-seq/microarray, scRNA-seq | **Replicate-based:** No | **PMID:** 29617963

**Algorithm:** Applies semi-Non-Negative Matrix Factorization (semi-NMF) to the expression matrix to estimate hidden batch factors (a loadings matrix W capturing batch variation). The coefficients of W are penalized with shrinkage regularization to stabilize estimation. Once W is estimated, batch effects captured in W are regressed out from the original expression matrix.

**Pros:**
- Applicable to both bulk RNA-seq and microarray — consistent with our cross-platform dataset.
- Fully unsupervised: no negative-control genes, no biological labels, no matched samples required.
- Semi-NMF coefficients are non-negative, making factor interpretations biologically plausible (factors represent "batch mixing proportions" rather than abstract directions).
- Output is a corrected genes × samples expression matrix — fully pipeline-compatible.

**Cons:**
- Semi-NMF is non-convex; results depend on initialization and may not be reproducible across runs without fixed random seeds.
- With 6 named RNA_BATCH labels known in advance, fully unsupervised hidden-factor estimation (SVA/DASC) has no advantage over explicitly supervised methods (ComBat, limma, FSQN) that use the known batch structure. The additional complexity of NMF is unnecessary when batch identity is available.
- No cross-platform (microarray + RNA-seq) validation evidence in the original paper; benchmarked primarily in scRNA-seq contexts.
- R package status unclear; not found in standard CRAN or Bioconductor repositories. 'the package is available at https://github.com/zhanglabNKU/DASC'

**Verdict: Low priority.** The semi-NMF approach offers no clear advantage over existing SVA and ComBat entries given our known batch labels. The unsupervised estimation adds implementation complexity without evidence of improved PCA R² on cross-platform bulk data.

---

#### exploBATCH

**Full name:** exploring batch effect  
**Category:** MF | **Data type:** microarray | **Replicate-based:** No | **PMID:** 28883548

**Algorithm:** Two-stage pipeline: (1) uses Probabilistic PCA with Covariates Analysis (PPCCA) to statistically test whether batch effects are significant in the principal subspace; (2) if significant, subtracts the estimated batch effect component from the original expression matrix.

**Pros:**
- Includes a formal statistical test for batch effect presence before correction — useful for studies where batch effect significance is uncertain.
- PPCCA handles missing values naturally, relevant for microarray data with probe-level NAs.
- Detection and correction are unified in a single workflow.

**Cons:**
- **Scope blocker:** Microarray only. RNA-seq samples are not supported.
- PPCCA is computationally intensive on large matrices (5,444 samples × 3,520 genes across 88 cohorts); the original validation used small datasets.
- The batch-detection step adds no value in our setting: we already know batch effects are severe (~95% PCA variance before correction).
- Package availability and R 4.5 compatibility are unclear. 'its available here https://github.com/syspremed/exploBATCH'

**Verdict: Low priority.** Microarray-only scope and high computational cost for our dataset scale. Not applicable to the full cross-platform benchmark.

---

#### FAbatch

**Full name:** Factor Adjustment batch correction  
**Category:** MF | **Data type:** microarray, DNA methylation | **Replicate-based:** No | **PMID:** 26753519

**Algorithm:** Integrates two correction layers sequentially: (1) location-and-scale adjustment using the same EB model as ComBat (corrects mean and variance per gene per batch); (2) latent factor adjustment using SVA-derived surrogate variables to remove residual unmodeled variation. FAbatch is conceptually ComBat + SVA applied in a unified model.

**Pros:**
- Combines the strengths of ComBat (known batch EB correction) and SVA (latent factor removal) in a single integrated framework.
- No negative-control genes required.
- R Bioconductor package available (`FAbatch`).

**Cons:**
- **Scope blocker:** Validated for microarray and DNA methylation only. RNA-seq extension is not described or validated.
- Since our benchmark already evaluates ComBat (`05_combat`) and SVA (`04_sva`) as separate entries, FAbatch would add a third combination of the same two mechanisms without a distinct algorithmic contribution.
- Our `21_harmonizr` (HarmonizR) uses a ComBat/limma combination with NA-awareness — functionally similar in spirit.
- Bioconductor package `FAbatch` was submitted in 2016; R 4.5 compatibility needs verification.

**Verdict: Low priority.** Conceptually covered by the combination of existing `05_combat` and `04_sva`. Microarray focus limits applicability to the full cross-platform benchmark.

---

#### Harman

**Full name:** (no full name given; Harman is the package/method name)  
**Category:** MF | **Data type:** RNA-seq/microarray, LC-MS proteomics, DNA methylation | **Replicate-based:** No | **PMID:** 27585881

**Algorithm:** PCA-based batch correction with an explicit statistical constraint on overcorrection. Harman: (1) computes PCA on the full expression dataset; (2) identifies PC axes driven by batch; (3) applies batch correction in PC space with a user-specified bound `limit` on the probability of over-removing biological signal (default `limit=0.05`); (4) projects corrected data back to the original gene space. The overcorrection constraint is computed from the within-batch distribution of each PC — if correction would cause excessive batch-independent variance reduction, the correction is automatically damped.

**Pros:**
- **Cross-platform applicable:** explicitly validated on RNA-seq/microarray bulk data — consistent with our cross-platform dataset.
- The overcorrection constraint directly addresses our key concern: that aggressive batch correction (e.g., FSQN) might remove the biological variation (DLBCL vs FL vs normal B-cell differences) that SOM analysis aims to detect. No other method in the current 25-method benchmark provides a formal overcorrection guard.
- No negative-control genes, matched samples, or reference batch required.
- Output is a genes × samples expression matrix — fully pipeline-compatible with oposSOM and ssGSEA.
- R Bioconductor package `Harman` is actively maintained (Bioconductor 3.22): `BiocManager::install("Harman")`.
- Validated on real multi-batch bulk RNA-seq and microarray datasets in the original paper (PMID 27585881).

**Cons:**
- PCA-based correction is inherently approximate: batch effects in PC dimensions not captured by the retained components (beyond those corrected) will persist. For our 88-cohort dataset with diverse batch structures, leading PCs may not capture all batch variation.
- The `limit` parameter (overcorrection probability bound) requires interpretation: the formal definition of "over-removal" is computed relative to the within-batch variance structure, which in our mixed-diagnosis dataset includes both batch and biology. Tuning `limit` for our specific biology-preservation goal may require empirical evaluation.
- Not specifically benchmarked on large-scale cross-platform integration (88 cohorts, 4 platforms). Original validation used smaller, more balanced datasets.
- FSQN operates feature-specifically rather than in a low-dimensional PC space, giving FSQN a potential accuracy advantage for platform-dominant effects where leading PCs don't fully capture between-platform differences.

**Verdict: Medium priority.** The overcorrection constraint is a genuinely distinct feature absent from all 25 current benchmark methods. If FSQN or other leading methods are observed to over-correct biology in SOM metagene space (a known concern), Harman offers a principled alternative. Proposed benchmark key: `29_harman`. Installation: `BiocManager::install("Harman")` in `install_r_packages.R`.

---

#### iNMF

**Full name:** integrative Non-Negative Matrix Factorization  
**Category:** MF | **Data type:** RNA-seq, miRNA-seq, DNA methylation | **Replicate-based:** No | **PMID:** 26377073

**Algorithm:** Jointly factorizes multiple data matrices (from different omics types or datasets) into shared and dataset-specific factor matrices using NMF. Shared factors capture cross-dataset biology; dataset-specific factors capture platform/batch effects. The batch-corrected representation is the reconstruction using shared factors only.

**Pros:**
- Handles bulk RNA-seq data (nominally applicable to the RNA-seq-only strategy C subset).
- NMF factors are non-negative and interpretable as "transcriptional programs."
- Designed specifically for multi-dataset integration; handles heterogeneous sources.

**Cons:**
- **Design mismatch:** iNMF was designed for integrating multiple concurrent omics types (RNA-seq + miRNA-seq + DNA methylation from the same samples). Our use case is single-omics (gene expression only) across multiple platforms and cohorts. Removed from the multi-omics context, iNMF reduces to a standard single-matrix NMF without the design's core strength.
- NMF requires non-negative input; our log2-transformed expression values can be negative (log2 of values < 1). Pre-transformation (e.g., shift to non-negative) is required and may distort the data.
- LIGER (entry 28 in this table), the modern maintained implementation of iNMF, explicitly targets scRNA-seq integration — its documentation and defaults assume single-cell data.
- No cross-platform (microarray + RNA-seq) validation; not a standard bulk omics tool.

**Verdict: Low priority.** The multiomics design motivation does not match our single-expression-type, cross-platform use case. The core NMF approach is not distinct enough from existing MF methods (SVA, RUV) to justify addition.

---

#### MultiBaC

**Full name:** Multiomics Batch-effect Correction  
**Category:** MF | **Data type:** multiomics data | **Replicate-based:** No | **PMID:** 32131696

**Algorithm:** Combines PLS (Partial Least Squares) regression with ARSyN batch effect correction. Requires at least one shared data type — an omics assay measured in all batches — to predict missing data types across datasets via PLS cross-prediction, then applies ARSyN to the assembled multi-omics matrix.

**Pros:**
- Principled cross-omics cohort harmonization when multiple data types are available.
- Can leverage relationships between omics types to impute and correct simultaneously.

**Cons:**
- **Fatal blocker:** Requires at least one shared data type across all batches. Our dataset is expression-only (transcriptomics). No matched proteomics or methylation data exists for any cohort. MultiBaC cannot be applied to a single-omics matrix.
- Even the ARSyN component (which would work on microarray data alone) is restricted to the microarray subset.

**Verdict: NOT APPLICABLE.** Requires multiple concurrent omics data types; our dataset is single-omics.

---

#### POIBM

**Full name:** POIsson Batch correction through sample Matching  
**Category:** MF | **Data type:** RNA-seq | **Replicate-based:** Yes | **PMID:** 35199138

**Algorithm:** For each source sample, POIBM learns a virtual target (reference) sample by optimization under a Poisson count likelihood. The batch coefficients are estimated from the difference between observed counts and the learned virtual reference. Unlike other replicate-based methods, matched replicates are not required — virtual reference samples are learned from the data.

**Pros:**
- Theoretically does not require actual matched replicates; learns virtual reference samples from the expression data.
- The count-based model is appropriate for integer RNA-seq data.
- Addresses the reference-free limitation of many other correction methods.

**Cons:**
- **Platform blocker:** RNA-seq only. Uses a Poisson count model that is fundamentally incompatible with microarray intensity data (log2-normalized values are not integer counts). Inapplicable to the 3,821 microarray samples in our dataset.
- Even for RNA-seq strategy C, our data is pre-processed (log2 TPM/FPKM-like values from the internal cohort database), not raw integer counts. The Poisson likelihood assumes integer counts and would be misspecified on pre-normalized log2 values.
- Published 2022 (PMID 35199138); limited independent validation on large multi-cohort datasets.

**Verdict: NOT APPLICABLE for current pipeline.** The Poisson count model requires raw integer counts; our expression matrices are pre-normalized. Potentially applicable if a counts-based sub-study with RNA-seq raw counts is undertaken, but outside the current benchmark's scope.

---

#### RUV-2

**Full name:** Remove Unwanted Variation, 2-step  
**Category:** MF | **Data type:** RNA-seq/microarray, LC-MS metabolomics | **Replicate-based:** Yes | **PMID:** 22101192; 25692814

**Algorithm:** Applies factor analysis to a set of negative-control genes (genes known a priori to be non-differentially expressed) to estimate the "unwanted variation" subspace W, then regresses W out of the full expression matrix as a two-step procedure.

**Pros:**
- Applicable to RNA-seq/microarray bulk data.
- Negative-control-based estimation is biologically grounded (housekeeping gene controls).
- Well-validated and foundational for the entire RUV family.

**Cons:**
- Our existing `09_ruv` (RUVseq) is the modern, maintained implementation that directly subsumes RUV-2. RUVseq uses 10 housekeeping genes as negative controls and calls the RUV-2 algorithm internally.
- RUV-2 with actual replicate-based estimation (the stronger variant listed as "Replicate-based: Y") requires matched samples across batches — not available for our retrospective data. The version we apply (via RUVg in `09_ruv`) uses negative-control genes rather than replicates.
- RUV-2 is the 2012 ancestor; the 2014 RUVseq paper (PMID 25150836) superseded it for RNA-seq and microarray applications.

**Verdict: Already covered by `09_ruv`.** RUVseq implements and extends RUV-2. No additional benchmark value from adding RUV-2 separately.

---

### Group Assessments — Methods Not Applicable to This Project

---

#### Metabolomics- and Proteomics-Specific Methods (11 methods)

The following methods are designed exclusively for mass spectrometry-based metabolomics or proteomics data. They model MS-specific artifacts (injection-order signal drift, isotope-labeled internal standards, ionization variability, abundance-dependent detection thresholds) that have no analog in microarray hybridization or RNA-seq sequencing. Applying them to log2-normalized gene expression data would be technically incorrect.

| Method | Cat | Data type | Key blocker |
|---|---|---|---|
| batchCorr | LS | LC-MS metabolomics | Between-batch MS feature alignment + within-batch LOESS drift correction; no expression analog |
| B-MIS | LS | LC-MS metabolomics | Requires isotope-labeled internal standards co-profiled with samples |
| QC-RLSC | LS | MS metabolomics | LOESS correction over QC sample injection-order sequence; assumes sequential MS injection drift |
| EigenMS | MF | LC-MS proteomics/metabolomics | SVD-based MS drift correction; the "systematic noise" model targets MS ionization variability, not platform batch effects |
| LIMBR | MF | LC-MS proteomics | SVA-based proteomics normalization with KNN imputation for missing peptides; not applicable to expression data |
| mixEMM | MF | LC-MS proteomics | Mixed-effects model explicitly modeling Batch-level Abundance-Dependent Missing-data Mechanism (BADMM); this missingness structure does not occur in bulk expression data |
| mvMISE | MF | LC-MS proteomics | Multivariate mixed-effects for labeled proteomics with replicate-required estimation; peptide correlation structure differs fundamentally from gene expression |
| WaveICA / WaveICA 2.0 | MF | LC-MS metabolomics | Wavelet + ICA decomposition for metabolomics temporal batch drift |
| NormAE | DL | LC-MS metabolomics | Autoencoder + adversarial learning for metabolomics normalization; trained on MS spectral patterns |
| RUV-III-C | MF | LC-MS proteomics | RUV-III variant handling missing values specific to proteomics data; replicate-based |
| RUV-random | MF | LC-MS metabolomics | RUV-2 variant applied to metabolomics; metabolomics-specific control variable assumptions |

All 11 methods are **NOT APPLICABLE** to RNA expression data.

---

#### Additional scRNA-seq Matrix Factorization Methods (7 methods)

The following MF methods are exclusively designed for scRNA-seq data. They assume count data distributions (negative binomial, zero-inflated NB, Poisson), dropout-driven sparsity structures, and cell-level resolution — none of which apply to our log2-normalized bulk expression matrices:

| Method | Key algorithmic assumption | Why not applicable |
|---|---|---|
| cFIT | Shared common factor space across scRNA-seq datasets with dataset-specific location-scale shifts; NMF framework | NMF model tuned for sparse scRNA-seq counts; no cross-platform bulk validation |
| LIGER | Jointly factorizes scRNA-seq and scDNA methylation using iNMF | Requires single-cell resolution and concurrent methylation data |
| RUV-III-NB | NB count model variant of RUV-III for scRNA-seq dropouts | NB likelihood requires integer counts; bulk log2 data violates distributional assumptions |
| scMerge | Gamma-Gaussian mixture model for identifying "stably expressed genes" (scSEGs) as pseudo-negative controls | Gamma-Gaussian model assumes scRNA-seq count distributions; pseudo-replicate construction assumes cell-type purity available in scRNA-seq |
| scPLS | Joint PLS model for control vs target gene sets in scRNA-seq | Control/target gene set structure and PLS model designed for scRNA-seq covariance structure |
| Seurat v2 (MultiCCA) | CCA dimensionality reduction for cell population alignment across scRNA-seq batches | CCA model assumes cell-level variation structure; designed for cell-type integration, not bulk sample integration |
| ZINB-WaVE | Zero-Inflated Negative Binomial WaVE model for scRNA-seq dropouts | Zero-inflation assumption is specific to scRNA-seq dropouts; bulk expression data has no zero-inflation from this mechanism |

All 7 methods are **NOT APPLICABLE**. Applying them to our log2-normalized bulk expression data would violate fundamental distributional assumptions of each model.

---

#### Additional scRNA-seq Distance-Neighborhood Methods (10 methods)

All remaining DN-category methods beyond the existing `10_mnn` (mnnCorrect/fastMNN) and `12_scanorama` are scRNA-seq-specific. They extend MNN or graph-based cell alignment frameworks that require single-cell resolution (thousands of cells per dataset) and cell-type-level biological overlap across batches:

| Method | Key approach | Key blocker |
|---|---|---|
| scMC | Variance analysis to learn biological vs technical variation; shared cell embedding | Designed for scRNA-seq / ATAC-seq cell populations; requires cell-level clustering |
| BATMAN | Parsimonious one-to-one cell matching in high-dimensional gene space | Cell-level matching assumes thousands of cells per type per batch |
| BBKNN | Batch-balanced KNN graph for cell integration | Graph structure assumes cell-level resolution with many cells of the same type per batch |
| BEER | MNN-based PCA subspace identification for scRNA-seq | MNN at cell level; the same fundamental limitation as `10_mnn` but with added scRNA-seq tuning |
| IMGG | MNN + generative adversarial network for scRNA-seq | GAN training requires large cell counts and cell-type-level matching |
| iSMNN | Iterative supervised MNN; requires within-batch scRNA-seq cell type clustering | Clustering at scRNA-seq resolution not applicable to bulk samples |
| SMNN | Supervised MNN with per-cell-type marker genes | Requires scRNA-seq resolution and known cell-type marker genes for cell-level matching |
| SSBER | Supervised anchor-based correction; anchors are cells sharing the same cell type | Anchor detection requires single-cell resolution |
| Seurat v3 | Diagonalized CCA with MNN anchors for single-cell multi-modal data | Anchor/cell-type CCA framework designed for scRNA-seq populations |
| Seurat v4 | Weighted nearest neighbor for multimodal single-cell data (CITE-seq, SHARE-seq, ASAP-seq) | Specifically for concurrent multimodal single-cell measurements |

At the bulk sample level (5,444 samples across 88 cohorts), the "cell" in DN algorithms maps to a bulk tumor or cell preparation. This provides far too little resolution for MNN-based alignment that requires cell-type-level resolution — the same fundamental issue that limits `10_mnn` and `12_scanorama` performance in our benchmark. All 10 are **NOT APPLICABLE**.

---

#### Additional scRNA-seq Deep Learning Methods (7 methods)

Beyond the five DL methods individually assessed in the Neural Network section (AutoClass, DESC, scGen, scVI, deepMNN), seven additional DL methods appear in the supplementary table. All are scRNA-seq-specific:

| Method | Architecture | Key blocker |
|---|---|---|
| BERMUDA | Deep autoencoder; trained to minimize reconstruction loss between original and reconstructed scRNA-seq values | Autoencoder reconstruction objective trained on scRNA-seq count data; log2 bulk expression is out-of-distribution |
| CBA | Cluster-driven deep learning; pre-clustering step preserves within-dataset structure before alignment | Pre-clustering assumes scRNA-seq count data; cluster-level loss functions tuned for single-cell distributions |
| Cell BLAST | Neural network generative model for single-cell transcriptome referencing against scRNA-seq atlases | Built on scRNA-seq reference atlas; no bulk RNA-seq reference atlas equivalent |
| MAT2 | Manifold alignment with contrastive learning via deep neural network | Contrastive learning strategy designed for scRNA-seq cell embedding manifolds |
| MMD-ResNet | Residual network minimizing Maximum Mean Discrepancy between scRNA-seq batch distributions | Originally validated on replicates of the same cell line (HEK293T); bulk tumor heterogeneity violates this assumption |
| SAUCIE | Sparse autoencoder for scRNA-seq clustering, imputation, and embedding | Designed for high-dropout scRNA-seq data; regularizations assume zero-inflated count structure |
| scDML | Deep metric learning for scRNA-seq batch correction guided by within-batch cluster structure | Cluster guidance assumes scRNA-seq-resolution cell populations |

All 7 are **NOT APPLICABLE**. The distributional mismatch between scRNA-seq count data model assumptions and our log2-normalized bulk expression applies identically here as for the five individually-detailed methods. The paper's explicit restriction of DL recommendations to scRNA-seq covers all 12 DL entries collectively.

---

### Supplementary Table — Revised Summary

Combining all assessments above with those from the main sections of this document:

| Method | New to document? | Bulk applicable? | Verdict |
|---|---|---|---|
| AMDBNorm | Yes | Yes | Low — reference-batch distribution adjustment; redundant with FSQN |
| BMC | Yes | Yes | Not worth adding — covered by `02_median_scaling` |
| BRIDGE | Yes | Yes (but needs bridge samples) | NOT APPLICABLE — matched-sample blocker |
| Remeasure | Yes | No (RNA-seq only + matched samples) | NOT APPLICABLE — matched-sample blocker |
| Z-scaled | Yes | Yes | Very low — likely harmful; over-corrects biology |
| ARSyN | Yes | Microarray only | Low — microarray scope limits cross-platform use |
| DASC | Yes | Yes | Low — unsupervised NMF adds no advantage over SVA/ComBat with known batch labels |
| exploBATCH | Yes | Microarray only | Low — microarray scope |
| FAbatch | Yes | Microarray only | Low — conceptually covered by `05_combat` + `04_sva` |
| **Harman** | **Yes** | **Yes** | **Medium — overcorrection constraint is a genuinely distinct feature; proposed `29_harman`** |
| iNMF | Yes | RNA-seq subset only | Low — multiomics design mismatch |
| MultiBaC | Yes | No (multi-omics only) | NOT APPLICABLE |
| POIBM | Yes | No (count model) | NOT APPLICABLE for current pipeline |
| RUV-2 | Yes | Yes | Already covered by `09_ruv` |
| 11 metabolomics/proteomics methods | Yes | No | NOT APPLICABLE |
| 7 scRNA-seq MF methods | Yes | No | NOT APPLICABLE |
| 10 scRNA-seq DN methods | Yes | No | NOT APPLICABLE |
| 7 additional DL methods | Yes | No | NOT APPLICABLE |

**Single actionable new addition identified from full supplementary table review: Harman.** Of 76 BECAs reviewed: 16 are already in the benchmark or planned; 4 are assessed as medium or low priority in earlier sections (M-ComBat, reComBat, RUV-III-PRPS, and now Harman); 56 are NOT APPLICABLE due to domain mismatch (metabolomics, proteomics, scRNA-seq) or structural blockers (matched samples required, multi-omics required); and the remaining new low-priority entries (AMDBNorm, BMC, Z-scaled, ARSyN, DASC, exploBATCH, FAbatch, iNMF) are all either redundant with existing methods, microarray-only, or lack evidence of improving on FSQN's ~16% R².

Harman is the only method in the supplementary table that: (a) is not already in the benchmark, (b) is applicable to bulk RNA-seq/microarray, (c) offers a functionally distinct capability — the overcorrection constraint — absent from all 25 current methods, and (d) has a maintained Bioconductor package. Its medium priority is contingent on the SOM overcorrection concern identified in the main CLAUDE.md being a limiting factor after the `26_xpn`/`27_dwd`/`28_npn` additions complete.
