# Foltz 2023 — Multi-Method Cross-Platform Normalization Review

**Paper:** Foltz SM, Greene CS, Taroni JN. "Cross-platform normalization enables machine learning model training on microarray and RNA-seq data simultaneously." *Communications Biology* 6:222 (2023). https://doi.org/10.1038/s42003-023-04588-6  
**PMC:** https://pmc.ncbi.nlm.nih.gov/articles/PMC9968332/  
**Review date:** 2026-05-06

**Context:** ~5,444 samples, 88 cohorts, 4 platforms (Affymetrix GPL570, Illumina NGS, Illumina microarray, Agilent microarray). Reference batch: RNASeq_FF_PolyA (n=1,039). Current benchmark winner: FSQN R (`16_fsqn_r`) at ~16% PCA variance explained by batch (raw baseline ~95%). Benchmark covers 25 methods × 10 filter strategies × 4 imputation options = 1,000 jobs.

---

## Paper Overview

This paper benchmarks eight normalization strategies for combining Agilent microarray and Illumina RNA-seq data from matched TCGA samples (BRCA n=520; GBM n=150). The experimental design uses a titration protocol: at each evaluation point, 0–100% of matched array samples are progressively replaced by their RNA-seq equivalents, simulating how researchers build cross-platform training sets. Performance is measured via Kappa statistic for supervised ML (subtype/mutation prediction), PLIER for pathway-level unsupervised analysis, and MASE for PCA reconstruction error.

**Critical limitation of this paper relative to our benchmark**: It evaluates simple distributional normalization methods rather than specialized batch correction tools. Neither ComBat, limma, FSQN, Harmony, RUV, MNN, nor any other method in our 25-entry registry appears here. The paper's "best" methods (QN, TDM) are already in our benchmark, and the paper offers only weak evidence that these outperform more specialized approaches. Additionally, the matched TCGA design means all validation was done with known ground-truth pairings — a setting fundamentally different from our 88-cohort retrospective assembly.

---

## Methods Already in the Benchmark — Excluded from Detailed Analysis

| Paper method | Our benchmark key | Notes |
|---|---|---|
| UN (Untransformed) | `01_raw` | Identical |
| LOG (Log2-transformation) | N/A (preprocessing step) | Applied during Stage 1 preparation via `log_transform_by_cohort()`; not a correction method |
| QN (Quantile Normalization) | `17_quantile` | Identical |
| TDM (Training Distribution Matching) | `19_tdm` | Identical; see `TDM_usage_perspectives.md` |

---

## Methods Not in Benchmark — Individual Assessments

### QN-CN (Quantile Normalization with CrossNorm)

**Algorithm:**
CrossNorm was originally published by Cheng et al. (*Scientific Reports* 2016;6:18898). The key distinction from standard QN is that rather than normalizing RNA-seq values to match the microarray distribution, it normalizes both platforms toward a shared middle distribution simultaneously:

1. Scale expression values from both platforms to [0,1] independently
2. Combinatorially stack paired sample columns from both platforms
3. Apply quantile normalization to the combined stacked matrix
4. The result is a shared distribution that is the QN consensus of both platforms, not a copy of either

This differs from FSQN/TDM (which impose the reference batch's distribution on all others) and from standard QN (which imposes the cross-sample mean distribution on all samples).

**Fatal blocker — requires exactly two paired datasets:**

The paper explicitly states: "CrossNorm requires two data sets; there is no QN-CN data for training at 0 and 100% RNA-seq." The method's stacking operation requires sample-level pairing between the two input datasets. In the Foltz 2023 protocol this is satisfied because all TCGA samples have matched array and RNA-seq measurements.

Our 88-cohort FL dataset is assembled from independent retrospective studies. There are no matched samples — no cohort was profiled on two platforms simultaneously. Applying CrossNorm to our dataset would require either (a) matched samples that do not exist or (b) some form of pseudo-pairing, which is not described or validated in the paper.

This is structurally identical to the MatchMixeR blocker (see `MatchMixeR_usage_perspectives.md`). No workaround exists within the CrossNorm framework.

Additionally, CrossNorm was designed for a two-platform pairwise setting. Extending it to 4 platforms and 88 cohorts would require a sequential pairwise application strategy similar to the problem that limits standalone XPN, introducing order-dependent artifacts.

**Code availability:** No dedicated R or Python package. Code was part of the original Cheng 2016 paper's supplementary material (MATLAB-based); no maintained standalone release exists.

**Verdict: NOT APPLICABLE.** Structural blockers: requires matched samples (none available), designed for exactly 2 platforms (our dataset has 4), no maintained code.

---

### NPN (Nonparanormal Normalization)

**Algorithm:**

NPN originates from graphical model estimation in high-dimensional statistics (Liu et al. 2009; `huge` R package, Zhao et al. 2012). Its application to gene expression normalization is a rank-based inverse normal transformation:

1. For each gene g across all samples within a platform, rank the expression values (rank 1 = lowest)
2. Map each rank to the corresponding quantile of the standard normal distribution N(0,1):
   ```
   NPN(g_ij) = Φ⁻¹(rank(g_ij) / (n + 1))
   ```
   where Φ⁻¹ is the normal quantile function (probit) and n is the number of samples in the platform
3. The result: within each platform, every gene's expression values now follow a standard normal distribution N(0,1)

NPN is applied **per-platform, not per-cohort**. After transformation, all platforms share the same distributional shape (standard normal), which the authors expect to reduce cross-platform technical differences.

**Conceptual relationship to existing benchmark methods:**

| Method | Target distribution | Scope of application |
|---|---|---|
| `18_rank` (fractional rank) | Uniform [0,1] | Per sample (across genes) |
| `17_quantile` (standard QN) | Cross-sample consensus | Per sample (across genes) |
| `16_fsqn_r` (FSQN) | Reference batch per gene | Per gene per batch |
| NPN | N(0,1) per gene | Per gene per platform |

NPN's normalization scope is most similar to FSQN: both operate per-gene across samples and target a specific distribution. The difference is that FSQN uses an empirical reference batch distribution, while NPN uses the standard normal.

**Assessment for our dataset:**

*Critical mismatch in correction granularity.* Our benchmark metric measures batch effects at the `RNA_BATCH` level — 6 major batches including `GPL570_FF_Unknown`, `GPL570_FFPE_Unknown`, `RNASeq_FFPE_Exome_capture`, etc. These are sub-platform batches distinguished by tissue type (FF/FFPE), sequencing protocol, and batch-specific technical artifacts. NPN is applied per-platform (4 platforms), not per `RNA_BATCH` (6+ batches). After NPN, within-platform batch effects between e.g. `GPL570_FF_Unknown` and `GPL570_FFPE_Unknown` would remain uncorrected — two batches that share the same platform label would both be mapped to N(0,1) but with the same within-platform artifacts preserved.

FSQN (`16_fsqn_r`) operates at the cohort/batch level, not the platform level, and corrects each cohort's gene distributions to match the reference independently. This is the correct granularity for our batch structure. NPN operating at the coarser platform level would leave substantial within-platform batch effects uncorrected.

*Over-normalization risk.* The Foltz 2023 paper found that NPN caused "near-zero random forest predictions" — indicating that forcing all gene values to N(0,1) destroyed the within-class expression differences needed for supervised classification. For our downstream SOM analysis (which requires continuous expression gradients to form metagene portraits), this is a serious concern: if NPN flattens the expression landscape to a uniform normal shape, metagene cluster resolution would degrade.

*Comparison with `18_rank`.* NPN maps gene expression to normal scores; `18_rank` maps to fractional ranks in [0,1]. These are monotone transformations of each other (probit of fractional rank ≈ normal score). For the purposes of our PCA R² batch metric, the distinction between N(0,1) and [0,1] target distributions is immaterial — the variance structure is identical up to a monotone transformation. NPN is therefore functionally redundant with `18_rank` for our benchmark metric.

*Package availability.* The `huge` R package is available on CRAN and is actively maintained. `huge::npn()` would apply NPN in R via rpy2. Implementation would be straightforward — comparable in complexity to `normalize_rank()`. However, given the above issues, implementation effort is not the limiting factor.

**Verdict: NOT RECOMMENDED for benchmark addition.** Three independent reasons:

1. **Wrong granularity:** NPN corrects at the platform level (4 platforms); our batch structure requires correction at the RNA_BATCH level (6+ batches). Within-platform batch effects are not addressed.
2. **Functionally redundant with `18_rank`:** NPN and fractional-rank normalization are monotone transformations of each other. The PCA R² metric does not distinguish them.
3. **Over-normalization concern:** The paper itself found NPN destroyed ML signal. For SOM portrait analysis this would likely degrade metagene resolution.

The paper's positive finding for NPN (higher pathway detection in PLIER) is irrelevant for our downstream use case (oposSOM SOM input, not PLIER pathway analysis).

---

### QN-Z (Quantile Normalization followed by Z-scoring)

**What it is:** Not a published standalone method. The Foltz 2023 authors applied standard quantile normalization and then standardized each gene across samples (z-score: subtract mean, divide by standard deviation). It is a sequential pipeline step, not a theoretically motivated method.

**Paper's own finding:** "QN-Z showed similar results to QN without z-scoring." The z-scoring step provides negligible additional benefit over standard QN.

**In our benchmark context:** Standard QN is already implemented as `17_quantile`. Adding a post-QN z-scoring step would create a derivative method that:
- Is not published or independently motivated
- Adds minimal improvement per the paper that introduced it
- Would make the benchmark entry difficult to compare against externally validated methods
- Removes absolute expression scale information, which matters for SOM portrait intensity scaling

**Verdict: Not applicable.** QN is already in the benchmark; sequential z-scoring adds no motivated contribution.

---

### Z-scoring (Standalone)

**What it is:** Per-gene standardization: for each gene, subtract the mean across all samples and divide by the standard deviation. This is the simplest possible way to make gene expression dimensionless and mean-centered.

**Relationship to existing methods:** Z-scoring is the standardization step embedded within many batch correction pipelines. `limma::removeBatchEffect` (`03_limma`) essentially fits and removes per-batch mean shifts, which approximates z-scoring within each batch. Per-gene z-scoring across all samples without batch awareness would destroy the biological mean differences between platforms (which partly encode biological composition differences, e.g., higher baseline activity of proliferation genes in RNA-seq vs. microarray). This is the same problem that causes over-correction in methods that lack a biology covariate.

**Verdict: Not applicable.** Not a batch correction method; a preprocessing normalization step. Would remove biologically relevant scale differences between cohorts. Already implicit in several existing benchmark methods.

---

## Paper Scope and Value for This Project

The Foltz 2023 paper serves a different research audience: clinical ML researchers who have paired microarray + RNA-seq TCGA data and want to combine them for training classifiers. Their benchmark design (matched samples, titration protocol, classification Kappa metric) is not applicable to our setting (retrospective assembly, 88 unmatched cohorts, SOM unsupervised analysis, PCA R² batch metric).

**Indirect value — confirms the existing TDM and QN benchmark entries:**

The paper provides independent validation that TDM and QN are among the better normalization methods for cross-platform ML. Both are already in our benchmark (`19_tdm`, `17_quantile`). The paper's finding that TDM and QN outperform LOG, Z-scoring, and NPN for supervised classification tasks supports the existing benchmark structure.

**The paper does NOT compare against:** ComBat, limma, FSQN, RUV, Harmony, MNN, Scanorama, qsmooth, or any other method in our 25-entry registry. This limits the paper's usefulness as an external validation of our benchmark ranking.

---

## Summary Table

| Method | Paper's best use case | In benchmark? | New contribution? | Verdict |
|---|---|---|---|---|
| UN (Untransformed) | Negative control | ✅ `01_raw` | No | Already covered |
| LOG (Log2) | Preprocessing | ✅ (data prep step) | No | Already part of pipeline |
| QN | Supervised ML, dimensionality reduction | ✅ `17_quantile` | No | Already covered |
| TDM | Supervised ML, dimensionality reduction | ✅ `19_tdm` | No | Already covered; see `TDM_usage_perspectives.md` |
| QN-CN (CrossNorm) | 2-platform paired normalization | ❌ | No | **Not applicable** — requires matched samples; 2-platform only; no maintained code |
| QN-Z | Exploratory variant | ❌ | No | Not applicable — marginal by paper's own account; QN already in benchmark |
| NPN | Pathway analysis (PLIER) | ❌ | No | **Not applicable** — wrong correction granularity (platform vs. RNA_BATCH); redundant with `18_rank`; over-normalization risk for SOM |
| Z-scoring | None (negative results) | ❌ | No | Not applicable — preprocessing only; batch-unaware; implicit in `03_limma` |

---

## Overall Conclusion

No new normalization methods from Foltz 2023 warrant addition to the benchmark. All methods are either already present (`17_quantile`, `19_tdm`, `01_raw`) or are not applicable to the project's structure (QN-CN requires matched samples, NPN operates at the wrong granularity, QN-Z and Z-scoring add nothing over existing entries).

The paper is primarily valuable as an independent confirmation that TDM and QN belong in the benchmark, and as a data point that simpler normalization methods (LOG, Z-scoring, NPN) are insufficient for cross-platform integration where specialized batch correction is needed. Its scope is deliberately limited to 8 simple methods on 2 matched datasets, and it makes no comparison with the ComBat/FSQN/limma tier of tools that constitutes the core of our benchmark.

**FSQN (`16_fsqn_r`) remains the benchmark winner.** The Foltz 2023 methods are categorically weaker than FSQN for our use case, with none of them applicable or non-redundant.
