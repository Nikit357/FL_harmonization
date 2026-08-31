# TDM (Training Distribution Matching) — Usage Perspectives for Multi-Platform Bulk RNA Harmonization

**Reference:** Thompson, Tan & Greene. *PeerJ* 4:e1621 (2016). https://github.com/greenelab/TDM

**Context:** Evaluation of TDM as a harmonization method for ~5,444 samples across 88 cohorts from mixed platforms (Affymetrix GPL570, Illumina NGS, Illumina microarray, Agilent microarray). Reference batch: RNASeq_FF_PolyA (n=1,039). Current best method: FSQN (R) at ~16% PCA variance explained by batch.

---

## Algorithm — Step by Step

TDM performs **per-gene IQR-based distribution clipping followed by linear rescaling** to a fixed reference batch. For each gene:

1. **Extract reference statistics:** Q1, Q3, min, max from the reference batch (inverse-log first if data is log-transformed)
2. **Compute scale factors** based on how far the reference extrema sit from its quartiles:
   - `topscale = (ref_max − ref_Q3) / (IQR × tdm_factor)`
   - `bottomscale = (ref_Q1 − ref_min) / (IQR × tdm_factor)`
3. **Compute clipping thresholds** for the query batch using its own quartiles and the reference scale factors:
   - `upandout = old_Q3 + topscale × IQR × tdm_factor`
   - `downandout = old_Q1 − bottomscale × IQR × tdm_factor`
4. **Clip** query values to `[downandout, upandout]` — compresses tail distributions
5. **Linearly rescale** the clipped range onto the reference range `[ref_min, ref_max]`:
   - `transformed = (clipped − downandout) / (upandout − downandout) × (ref_max − ref_min) + ref_min`
6. **Optional log2 transform** of the result (`log_target=TRUE`)

**Key insight:** TDM uses the reference's quartile structure to define what is "normal range" vs. "outlier tail", then rescales the query to match this structure. It is fundamentally a robust quantile normalization that shapes the bulk of the distribution while clipping extremes.

---

## Data Types and Design Target

| Input | Supported |
|---|---|
| Raw RNA-seq counts | ✓ |
| RSEM expected counts | ✓ |
| Microarray intensities | ✓ |
| TPM / RPKM / FPKM | ✗ (already normalized — destroys count-space distribution) |

**Primary design target:** RNA-seq ↔ microarray harmonization (pairwise, single reference).

The method is platform-agnostic at the input level but was designed and validated in the context of cross-platform RNA-seq/microarray integration.

---

## Distribution Assumptions

TDM makes **minimal parametric assumptions** but several structural ones:

- **Quartile meaningfulness:** IQR must be a valid measure of central spread. Bimodal or heavily censored distributions may not transform well.
- **Gene-wise independence:** Transformations are applied per gene independently. Gene-gene correlations are not modeled or preserved.
- **Continuous distributions:** Very sparse or zero-inflated data causes problems (see Limitations).
- **Non-negative values:** Clips to the observed minimum; no negative expression values assumed.
- **Stable reference quantiles:** Reference batch needs sufficient sample size for stable Q1/Q3 estimates (n > 30 is safe; our reference has n=1,039).
- **Same underlying biology:** Assumes platforms measure the same signal with different technical properties (scale, offset, saturation) — not fundamentally different genes.

---

## Batch Handling: Pairwise vs. Multi-Batch

**Architecture: pairwise reference-to-query only.**

```
Reference Batch (RNASeq_FF_PolyA)
    ↓
    ├→ Query Batch 1 (GPL570_FF_Unknown)   → independently transformed to match Reference
    ├→ Query Batch 2 (GPL14951_FFPE)       → independently transformed to match Reference
    └→ Query Batch N (...)                 → independently transformed to match Reference
```

- All 88 cohorts are transformed individually to match the single reference
- No inter-cohort relationships are modeled
- Each cohort's transformation is fully independent

**Contrast with:**
- ComBat — models all batches simultaneously with shared empirical Bayes prior
- Harmony — jointly optimizes PCA-space correction across all batches
- FSQN — also pairwise reference, but uses full rank replacement (more aggressive)

---

## The Reference Batch Concept

The reference batch defines the **target distribution shape** for all query batches. Its per-gene Q1, Q3, min, and max are the fixed parameters all other batches are pulled toward. The reference itself is **not modified**.

**For this project:** RNASeq_FF_PolyA (n=1,039) is the reference.
- Largest batch — stable quantile estimates
- Highest quality RNA (fresh-frozen, PolyA selection)
- Chosen consistently across all harmonization methods in the benchmark

**Potential issue:** When the reference (RNA-seq) has higher dynamic range than the query (microarray), TDM will attempt to push query values into a range that was technically undetectable on the array platform. This is the directionality problem described below.

---

## Known Limitations and Failure Modes

### 1. Wrong harmonization direction (critical for this dataset)

TDM was designed and validated for transforming **microarray data to match RNA-seq** distributions. Our setup is the **reverse**: RNA-seq is the reference and microarrays are the query.

The authors explicitly recommend against the RNA-seq → microarray direction because:
- Microarrays saturate at high expression — their upper tail is compressed
- TDM will try to push array values upward into an expression range that was physically undetectable on the array
- The result is biologically implausible inflated values in formerly-saturated genes

This is the primary reason TDM is unlikely to outperform FSQN for this dataset.

### 2. IQR degeneracy in sparse genes

Any gene where Q1 = Q3 = 0 (IQR = 0) in a query batch causes division-by-zero or a degenerate transformation. GPL570 microarray batches have dropout genes that RNA-seq cohorts do not. This is a real risk for ~hundreds of genes in microarray cohorts.

### 3. No covariate protection

TDM has no mechanism to model biological covariates. If a batch is enriched for one diagnosis group, TDM may remove biologically real variance alongside batch effects. ComBat and SVA both support a `bio_col` covariate model to protect against this.

### 4. Non-linear batch effects

TDM assumes batch effects are multiplicative/additive in scale. Complex interactions (e.g., platform-specific saturation at certain expression levels) are not captured.

### 5. Gene correlation not preserved

Per-gene independence means co-expression structure (pathways, regulons) may be subtly distorted post-TDM. This is acceptable for single-gene ML features but potentially problematic for network-based analyses.

### 6. No multi-batch information sharing

Pairwise transformation cannot leverage information about batch structure across all 88 cohorts simultaneously. Methods like ComBat or Harmony that model all batches jointly can borrow statistical strength across cohorts.

---

## TDM vs. FSQN Comparison

| Aspect | TDM | FSQN |
|---|---|---|
| Algorithm | IQR-based clipping + linear rescaling | Full rank-based quantile replacement |
| Aggression | Medium | High |
| Tail handling | Clips before scaling | Assigns quantile directly from reference |
| Directionality | Designed for array→RNA-seq | Works well in both directions |
| Covariate modeling | No | No |
| Gene correlation preservation | Slightly better | Slightly worse |
| Cross-platform robustness | Moderate | High |
| Expected residual batch R² | Likely > 16% for this data | ~16% (benchmark winner) |

FSQN's more aggressive quantile replacement is better suited for the large dynamic range gap between Affymetrix GPL570 microarray and RNA-seq PolyA data.

---

## Implementation Notes

Current implementation in `bench_shared.py` (`19_tdm`):

```python
# File-based R interface (avoids rpy2 matrix conversion issues)
# R call is approximately:
# library(TDM)
# result <- tdm_transform(file="query.tsv", ref_file="ref.tsv", log_target=FALSE)
```

**Note:** `log_target=FALSE` means output is not log-transformed. TDM documentation suggests log-transformed data should use `log_target=TRUE`. Worth verifying whether input data is in log2 space before calling TDM.

---

## Arguments FOR TDM in This Pipeline

- No parametric distribution assumptions — robust for heterogeneous RNA-seq/microarray mixtures
- Pairwise reference model matches the project design (canonical RNASeq_FF_PolyA reference)
- Per-gene specificity — respects each gene's distribution (unlike global QN)
- Platform-agnostic for supported input types
- Already implemented as `19_tdm` in `bench_shared.py` with full benchmark results in S3

---

## Arguments AGAINST TDM as Primary Method

- **Directionality mismatch** — reference is RNA-seq, queries include microarrays; the authors explicitly discourage this direction
- **Mechanistically weaker than FSQN** for large platform dynamic range gaps (gentler clipping vs. full quantile replacement)
- **No covariate protection** — risk of removing biological variance in diagnosis-enriched batches
- **IQR degeneracy risk** — sparse/dropout genes in microarray batches cause degenerate transformations
- **No cross-batch information sharing** — cannot leverage structure across all 88 cohorts simultaneously
- **Benchmark already settled this** — `19_tdm` results exist in `metrics.csv` on S3; empirical comparison against `16_fsqn_r` is directly accessible

---

## Recommendation

**TDM is not suitable as the primary harmonization method for this dataset.**

The directionality mismatch (RNA-seq reference + microarray queries) is the fundamental structural incompatibility. FSQN remains the benchmark winner.

**TDM may be relevant only in:**
- A RNA-seq-only subset (`C_rnaseq_only` strategy), where dynamic range differences are smaller and the directionality issue disappears
- Scenarios where an external RNA-seq dataset must be matched to an array-based reference (opposite of our setup)

**Practical next step:** Query `metrics.csv` from S3 for `19_tdm` rows under strategy `A_confirmed_bad` with `strict` imputation and compare `r2_batch` directly to `16_fsqn_r`. This gives the definitive empirical answer for this dataset.

```python
import pandas as pd
metrics = pd.read_csv("metrics.csv")  # or load via load_cross_product_results.py
compare = metrics[
    (metrics["strat"] == "A_confirmed_bad") &
    (metrics["imp"] == "strict") &
    (metrics["method"].isin(["16_fsqn_r", "19_tdm"])) &
    (metrics["post_rm"] == False)
][["method", "r2_batch", "r2_diag", "n_samples", "status"]]
print(compare)
```
