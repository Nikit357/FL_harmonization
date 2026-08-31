# MatchMixeR — Usage Perspectives for Multi-Platform Bulk RNA Harmonization

**Full name:** MatchMixeR: Cross-platform normalization of gene expression data  
**Reference:** Du, Y. et al. *Bioinformatics* 36(8), 2486–2492 (2020). https://doi.org/10.1093/bioinformatics/btaa078  
**GitHub:** https://github.com/dy16b/Cross-Platform-Normalization  
**Implementation:** R package (freely available)

**Context:** Evaluation of MatchMixeR as a harmonization candidate for ~5,444 samples across 88 cohorts from mixed platforms (Affymetrix GPL570, Illumina NGS, Illumina microarray, Agilent microarray). Reference batch: RNASeq_FF_PolyA (n=1,039). Current benchmark winner: FSQN (R) at ~16% PCA variance explained by batch (down from ~95% raw).

---

## What MatchMixeR Actually Does — Core Concept

MatchMixeR fits a **per-gene affine transformation** that maps expression values from one platform onto another, learning the transformation parameters from a set of **matched samples** — biological specimens measured on both platforms simultaneously. Once trained, the per-gene model is applied to unmatched research samples.

The method decomposes cross-study differences into three components:

```
Cross-study difference = Sample differences + Lab differences + Platform differences
```

Its goal is to remove **platform differences** while preserving the biological sample differences. This framing is explicitly analogous to FSQN and TDM; the distinction is that the platform transformation is *learned from data* (matched samples) rather than derived analytically from quantile distributions.

---

## Algorithm — Step by Step

### Training phase (requires matched samples)

For each gene i, fit a linear mixed effects regression (LMER):

```
y_ij = β₀ + γ₀ᵢ + x_ij · β₁ + γ₁ᵢ + εᵢⱼ
```

where:
- β₀, β₁ = fixed effects shared across all genes (global intercept and slope)
- γ₀ᵢ, γ₁ᵢ = gene-specific random intercepts and slopes (the correction parameters)
- εᵢⱼ ~ N(0, σ²) = residual error
- x_ij = expression of gene i in sample j on the source platform
- y_ij = expression of gene i in sample j on the target platform

LMER shrinks the gene-specific estimates toward the shared fixed effects rather than toward zero, reducing bias for genes with few observations compared to OLS.

**Computational trick — FLMER:** To avoid the iterative EM algorithm of lme4, the authors implemented a moment-based estimator (FLMER) that is >130× faster and uses variance-ratio estimation from the data to calibrate the shrinkage magnitude, avoiding cross-validation.

### Application phase (unmatched research data)

For each gene i and each new sample j on the source platform:

```
x̂ᵢⱼ (target platform) = β̂₀ᵢ + x_ij (source platform) · β̂₁ᵢ
```

The output is a corrected genes × samples matrix with the same dimensions as the input. Per-gene confidence intervals on the transformed values are also available.

---

## Input Data Requirements

| Requirement | Details |
|---|---|
| **Matched training data** | Same biological samples measured on both platforms (mandatory) |
| **Research (test) data** | Unmatched samples to be normalized (the actual study data) |
| **Preprocessing** | Log2-transformed, within-platform normalized (e.g., frozen RMA for Affymetrix) |
| **Format** | Genes × samples matrix for both training and test sets |
| **Training sample size** | Paper uses 40–450 matched samples; n=5 tested as minimum in simulation |

---

## Validation Datasets

MatchMixeR was validated on **bulk expression data only** — no scRNA-seq:

| Dataset | Platform A | Platform B | Matched samples |
|---|---|---|---|
| NCI60 cell lines (CellMiner) | Affymetrix GPL96 (U133A) | Affymetrix GPL570 (U133 Plus 2.0) | 58 cell lines |
| NCI60 cell lines (CellMiner) | Affymetrix GPL570 | Agilent GPL4133 | 59 cell lines |
| TCGA BRCA | Agilent G4502A microarray | Illumina HiSeq 2000 (GPL11154) | 583 breast cancer patients |
| Simulation | Synthetic platform A | Synthetic platform B | 100–450 samples |

All real-data training sets use naturally matched samples (the NCI60 panel is a canonical multi-platform benchmark; TCGA measured the same patients on both platforms by design).

---

## Performance Against Competing Methods

Metrics: RMSD (expression reconstruction error), F₁-score (DE gene recovery).

**Simulation — RMSD (lower is better):**

| Method | n_test=30 | n_test=5 |
|---|---|---|
| No correction | 2.518 | 2.518 |
| MatchMixeR | **0.001** | **0.001** |
| XPN | 0.012 | 0.025 |
| ComBat | 0.024 | 0.026 |
| DWD | 0.051 | 0.046 |

**Simulation — F₁ for DE detection across imbalanced batch compositions:**

| Batch composition | MatchMixeR | ComBat | DWD |
|---|---|---|---|
| Balanced (15:15:15:15) | 0.979 | **0.980** | 0.957 |
| Moderately unbalanced (15:15:30:0) | **0.980** | 0.967 | 0.944 |
| Extreme (30:0:0:30) | **0.981** | NaN | NaN |

ComBat and DWD fail entirely (NaN) on the most imbalanced scenario; MatchMixeR remains functional.

**TCGA BRCA real data — F₁ for DE detection:**

| Test scenario | MatchMixeR | DWD | ComBat |
|---|---|---|---|
| Balanced | **0.718** | 0.717 | 0.717 |
| Unbalanced | 0.704 | 0.704 | 0.703 |
| Severe imbalance | **0.648** | 0.278 | 0.361 |
| Extreme (no overlap) | **0.658** | N/A | N/A |

**Computational speed (simulation, 10,000 genes):** MatchMixeR 0.9 s vs. ComBat 3.2 s vs. XPN 174 s.

---

## Stated Limitations

1. **Matched training data is mandatory.** No matched samples = no model. The paper offers no unsupervised fallback.

2. **Two-platform architecture.** The method is designed and validated for pairwise platform correction. Multi-platform extension is mentioned ("transform all datasets in the other platform") but is not benchmarked for 3+ platforms.

3. **Pre-normalization sensitivity.** The learned transformation depends on which within-platform normalization was applied. The authors recommend frozen RMA for Affymetrix as a standard but acknowledge this dependency.

4. **Linear transformation only.** The affine per-gene model cannot capture non-linear platform effects such as microarray saturation at high expression or RNA-seq length bias.

5. **Reference platform choice matters.** The larger, higher-quality platform should be the target (platform B). Using the smaller or noisier platform as target increases introduced error.

---

## Assessment for This Project

### The single fatal blocker: no matched training data exists

MatchMixeR's entire correction mechanism depends on learning per-gene transformation coefficients from biological samples **measured on both platforms simultaneously**. Without these matched samples, the model cannot be trained.

The 88-cohort FL dataset is assembled from retrospective public databases (GEO, an internal cohort database, ArrayExpress). These cohorts were generated independently by different research groups on different platforms at different times. None of them have been deliberately measured on two platforms in parallel. There is no natural matched subset.

The NCI60 cell lines (used in the paper) are not FL or lymphoma samples. The TCGA BRCA cohort (used in the paper) is breast cancer. Even if we identified a small number of samples that appear to have been profiled on two platforms in the literature, the sample size would be far too small (need ≥40 matched samples for stable per-gene estimation of 3,520 genes) and the biological context might not generalize.

**This blocker is structural — no workaround exists within the MatchMixeR framework.**

### Secondary considerations (for completeness)

**Platform scope — actually appropriate.** Unlike scBatch, MatchMixeR was validated on exactly the platforms relevant to this project: Affymetrix GPL570 (our largest microarray batch at n=994), Agilent microarray, and Illumina RNA-seq. This is the most platform-appropriate method reviewed so far, aside from FSQN and TDM.

**Handles diagnosis imbalance well.** The LMER shrinkage makes MatchMixeR robust to the kind of extreme per-batch diagnosis composition skew that characterizes our 88-cohort dataset (many cohorts are DLBCL-only or FL-only). This is a genuine advantage over ComBat and DWD in our setting — but irrelevant without matched samples.

**Multi-platform not validated.** The four-platform structure of our dataset (GPL570, RNASeq_FF, GPL14951, Agilent) exceeds MatchMixeR's tested scope. Extension to 4+ platforms would require sequential pairwise application with a reference platform, introducing order-dependent artifacts.

**Output format is correct.** MatchMixeR produces a genes × samples expression matrix — unlike HARP or MoDAmix.

**Computational cost is negligible.** 0.9 s for 10,000 genes is not a constraint.

---

## Comparison with Current Benchmark Methods

| Aspect | MatchMixeR | FSQN (current best) | TDM | ComBat |
|---|---|---|---|---|
| Design target | Bulk multi-platform | Bulk multi-platform | Bulk multi-platform | Bulk RNA-seq |
| Core mechanism | Learned per-gene affine (from matched data) | Per-gene quantile replacement to reference | IQR clipping + linear rescale to reference | Empirical Bayes location/scale |
| Requires matched samples | **Yes (mandatory)** | No | No | No |
| GPL570 + RNA-seq validated | Yes | Yes | Partial | Partial |
| Multi-platform (>2) | Not validated | Yes | Yes | Yes |
| Imbalanced batch composition | Handles well (LMER) | Not applicable | No covariate protection | Covariate supported |
| Output format | Genes × samples matrix | Genes × samples matrix | Genes × samples matrix | Genes × samples matrix |
| Residual batch R² (our data) | Unknown (cannot run) | **~16%** | ~20-30% (estimated) | ~30-40% |

---

## Potential Future Use Case

If a matched multi-platform reference panel for B-cell lymphoma were ever assembled — for example, if 40–100 FL/DLBCL samples were profiled on both Affymetrix GPL570 and RNA-seq PolyA — MatchMixeR would become directly applicable and potentially competitive with FSQN. Its per-gene learned transformation would be biologically calibrated to the actual lymphoma expression program rather than relying on distributional shape matching.

This scenario is not impossible: the TCGA programme has done exactly this for BRCA (583 matched samples). A lymphoma equivalent (e.g., 100 DLBCL patients from the internal cohort database measured on both platforms) would unlock MatchMixeR. Flagging as a longer-term methodological direction.

---

## Verdict

**MatchMixeR cannot be applied to this project.**

The matched training data requirement is a structural blocker that cannot be circumvented: no retrospective public cohort in the assembled dataset was measured simultaneously on two platforms. There is no fallback mode.

The method would otherwise be well-suited: it is validated on the relevant platforms (Affymetrix GPL570 + Illumina RNA-seq + Agilent), robust to diagnosis imbalance, fast, and produces the correct output format. It is a stronger theoretical fit than scBatch for this problem class. The practical constraint is entirely logistical.

**FSQN (R) remains the benchmark winner** for the current dataset. MatchMixeR is worth revisiting only if matched multi-platform lymphoma profiling data becomes available.
