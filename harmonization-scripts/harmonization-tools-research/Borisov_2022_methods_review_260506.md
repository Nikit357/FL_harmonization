# Borisov & Buzdin 2022 — Harmonization Methods Review

**Paper:** Borisov NM, Buzdin AA. "Transcriptomic Harmonization as the Way for Suppressing Cross-Platform Bias and Batch Effect." *Biomedicines* 2022, 10(9):2318.  
**DOI:** https://doi.org/10.3390/biomedicines10092318  
**PubMed:** https://pubmed.ncbi.nlm.nih.gov/36140419/ (PMC9496268)  
**Review date:** 2026-05-06

**Context:** ~5,444 samples, 88 cohorts, 4 platforms (Affymetrix GPL570, Illumina NGS, Illumina microarray, Agilent microarray). Reference batch: RNASeq_FF_PolyA (n=1,039). Current benchmark winner: FSQN R (`16_fsqn_r`) at ~16% PCA variance explained by batch (raw baseline ~95%). Benchmark covers 25 methods × 10 filter strategies × 4 imputation options = 1,000 jobs.

---

## Methods Already in the Benchmark — Excluded from Analysis

| Paper method | Benchmark key(s) |
|---|---|
| Quantile Normalization (QN) | `17_quantile` |
| ComBat / Empirical Bayes (EB) | `05_combat`, `07_pycombat`, `08_inmoose_combatseq` |
| ComBat-seq | `06_combat_seq` |
| TDM (Training Distribution Machine) | `19_tdm` |
| FSQN / FCQN (Feature-Specific QN) | `15_fsqn_py`, `16_fsqn_r` |
| Shambhala-2 / CuBlock | `20_shambhala` |
| DESeq2 / VST | `23_vst` |

---

## Methods Not in Benchmark — Individual Assessments

### XPN (Cross-Platform Normalization)

**Algorithm:** Piecewise linear transformation. Divides expression range into intervals and fits an affine map per interval so that the quantile distribution of dataset A matches dataset B. Flexible-format output.

**Paper verdict:** Recommended as best for 2-dataset cross-platform comparison (balanced groups). Used as the reshaping engine inside Shambhala-1.

**Pros:**
- Explicitly designed for MH ↔ MH and MH ↔ NGS normalization
- Better theoretical foundation for preserving fold-change relationships than standard QN
- R code available from original publication

**Cons / blockers:**
- Hard constraint: works on exactly 2 datasets at a time. With 88 cohorts, requires iterative pairwise application — not intended use, raises order-dependence questions
- Unbalanced group sizes degrade performance
- Shambhala-2 (already implemented) is its direct successor using a cubic kernel, applied in the one-by-one-against-reference paradigm that solves the 88-cohort problem

**Verdict:** Low priority — functionally covered by `20_shambhala`. Standalone XPN would require custom multi-cohort scaffolding and would likely underperform Shambhala-2.

---

### fRMA (Frozen Robust Microarray Analysis)

**Algorithm:** Predefined-format method. Applies frozen (pre-computed) probe-level normalization vectors derived from large public microarray collections. Each array is normalized independently against the frozen reference.

**Pros:**
- Predefined output — normalization is sample-independent, no recalculation when adding new arrays
- GPL570-specific frozen vectors are publicly available

**Cons / blockers:**
- Microarray only — no NGS counterpart; cannot harmonize RNAseq cohorts
- Requires raw probe-level CEL files; project data is already summarized at the gene level (HGNC symbols, samples × genes TSV)

**Verdict:** Not applicable. Requires probe-level MH input and has no RNA-seq extension.

---

### DWD (Distance-Weighted Discrimination)

**Algorithm:** Generalizes SVM-style hyperplane finding to high-dimensional settings. Finds a projection direction that maximally separates batch groups while minimizing within-batch variance. Linear transformation of the full expression matrix. Flexible format, requires batch labels.

**Pros:**
- Works on gene expression matrices with multiple batches
- R package available

**Cons / blockers:**
- Paper positions DWD as an intra-platform MH method; cross-platform MH ↔ NGS performance is not demonstrated
- Multi-batch extension (88 RNA_BATCH labels) is non-standard
- Limma `removeBatchEffect` (`03_limma`) solves the same problem with a more standard formulation validated on large cohorts

**Verdict:** Not applicable for cross-platform use case; redundant with `03_limma` for intra-platform correction.

---

### UPC (Universal exPression Code)

**Algorithm:** Predefined-format method. Converts raw expression values to a probability of being "active" (range 0–1) using a two-component mixture model (active / inactive). Works per sample, independently, on both MH and NGS.

**Pros:**
- Predefined format — no recalculation when adding samples
- Platform-agnostic by design; validated on both MH and NGS

**Cons / blockers:**
- Output is a 0–1 binary-probability scale — loses quantitative dynamic range needed for SOM portrait generation (metagenes represent continuous activity gradients)
- SOM distance calculations in oposSOM depend on meaningful expression differences; compressing to [0,1] probabilities flattens the landscape and distorts portrait topology

**Verdict:** Not applicable for SOM input. Could be interesting for binary signature scoring tasks but not for the harmonization benchmark.

---

### QD (Quantile Discretization) and NorDi (Normalized Discretization)

**Algorithm:** Both convert continuous expression values into ordinal discrete categories (low/medium/high) after quantile normalization (QD) or direct binning (NorDi).

**Cons / blockers:**
- Categorical output is incompatible with SOM, PCA R² metric, ssGSEA, and survival regression
- Designed for classification tasks, not for preserving batch-corrected expression matrices

**Verdict:** Not applicable. Fundamentally incompatible with the analytical pipeline.

---

### PLIDA (PLatform-Independent Latent Dirichlet Allocation)

**Algorithm:** Applies LDA (topic modeling) to gene expression, representing each sample as a mixture of latent topics. Output is a low-dimensional topic-proportion vector per sample.

**Cons / blockers:**
- Output is a latent embedding (samples × topics), not a samples × genes expression matrix — incompatible with oposSOM, gene-level metrics, and ssGSEA

**Verdict:** Not applicable. Dimensionality-reduction output is incompatible with gene-level analysis.

---

### IBN (Integrative Bayesian Network)

**Algorithm:** Bayesian network model jointly inferring cross-platform normalized expression values and their uncertainty. Posterior estimates serve as the harmonized output.

**Cons / blockers:**
- No maintained software package; original implementation not publicly available
- Posterior inference at ~5,444 samples × 3,520 genes is computationally prohibitive

**Verdict:** Not applicable. No usable implementation; computationally infeasible at this scale.

---

### Rank-in

**Algorithm:** Replaces raw expression values with within-sample gene ranks, making profiles platform-independent.

**Verdict:** Redundant with `18_rank` (fractional rank per sample). Skip.

---

### ESLR (Elastic Shared LASSO Regularization)

**Algorithm:** Regularized regression learning per-gene transformation from one platform to another using elastic net. Requires matched samples from both platforms for training.

**Cons / blockers:**
- Requires matched samples (same biological specimens measured on two platforms) — same structural blocker as MatchMixeR (already ruled out; see `MatchMixeR_usage_perspectives.md`)
- No paired MH+NGS samples exist in the assembled dataset

**Verdict:** Not applicable. Same matched-sample requirement that blocked MatchMixeR.

---

### DisTran (Distribution Transformation)

**Algorithm:** Early-era flexible method transforming the empirical CDF of one dataset to match another. Predecessor of FSQN.

**Cons / blockers:**
- No maintained package
- Global distribution matching (not feature-specific) has the same known weakness as standard QN, which performs worse than FSQN on this data

**Verdict:** Not applicable. Strictly inferior to FSQN (already benchmarked).

---

### GQ (Gene Quantiles)

**Algorithm:** Per-gene quantile positioning across samples and platforms. Little detail in the paper; early-era minor variant of quantile normalization.

**Cons / blockers:**
- No published package; original citations from early 2000s with no current maintenance
- Functionally overlaps with `17_quantile` and `16_fsqn_r`

**Verdict:** Not applicable. No accessible implementation.

---

### QNR (Robust Quantile Normalization)

**Algorithm:** Variant of QN using a trimmed/robust mean of sorted values instead of arithmetic mean.

**Cons / blockers:**
- The paper explicitly reports QNR performs **worse** than standard QN in cross-platform benchmarks
- Standard QN already implemented as `17_quantile`

**Verdict:** Not worth adding. Paper itself discourages it.

---

### Shambhala-1

**Algorithm:** Same predefined-format framework as Shambhala-2 but uses XPN (piecewise linear) as the transformation engine instead of CuBlock (piecewise cubic).

**Verdict:** Superseded by Shambhala-2 (`20_shambhala`), which the paper's authors confirm outperforms Shambhala-1.

---

### Divergence Analysis

**Algorithm:** Uses conditional probability (Bayesian) models to compute how much a sample's expression diverges from a reference distribution. Used for sample classification, not normalization.

**Cons / blockers:**
- Not a normalization method — outputs sample-level divergence scores, not a harmonized expression matrix
- Cannot produce a genes × samples matrix for SOM, PCA R², or ssGSEA

**Verdict:** Not applicable. Wrong type of output for the benchmark.

---

## Summary Table

| Method | Paper's top use case | In benchmark? | Applicable? | Reason |
|---|---|---|---|---|
| QN | Intra-platform MH | ✅ `17_quantile` | — | — |
| ComBat/EB | Batch correction | ✅ `05/07/08` | — | — |
| TDM | Cross-platform predefined | ✅ `19_tdm` | — | — |
| FSQN/FCQN | Cross-platform | ✅ `15/16_fsqn` | — | — |
| Shambhala-2 | Mixed MH+NGS uniform | ✅ `20_shambhala` | — | — |
| DESeq2/VST | NGS intra-platform | ✅ `23_vst` | — | — |
| XPN | 2-dataset cross-platform | ❌ | Low | 2-dataset limit; covered by Shambhala-2 |
| fRMA | Affymetrix probe-level | ❌ | No | MH probe-level only; no NGS counterpart |
| DWD | Intra-platform MH | ❌ | No | Not validated for MH↔NGS; covered by `03_limma` |
| UPC | MH+NGS binary-active | ❌ | No | 0–1 output destroys dynamic range for SOM |
| QD / NorDi | Classification tasks | ❌ | No | Categorical output; incompatible with pipeline |
| PLIDA | Latent representation | ❌ | No | Topic embedding, not gene expression matrix |
| IBN | Bayesian integration | ❌ | No | No package; computationally infeasible |
| Rank-in | Platform-independent | ❌ | No | Covered by `18_rank` |
| ESLR | Cross-platform | ❌ | No | Requires matched samples (same as MatchMixeR) |
| DisTran | Early MH | ❌ | No | Superseded by FSQN |
| GQ | Intra-platform | ❌ | No | No maintained package; covered by QN/FSQN |
| Shambhala-1 | Mixed MH+NGS | ❌ | No | Superseded by Shambhala-2 |
| QNR | Intra-platform MH | ❌ | No | Paper reports worse performance than standard QN |
| Divergence Analysis | Sample classification | ❌ | No | Not a normalization method |

---

## Overall Conclusion

None of the methods reviewed in Borisov & Buzdin 2022 add meaningful, non-redundant coverage to the existing 25-method benchmark. The paper's own recommendation — Shambhala-2 for mixed MH+NGS multi-dataset harmonization with uniform output — is already implemented as `20_shambhala`. The only method with residual interest is standalone **XPN** if Shambhala-2 underperforms unexpectedly, but it is its algorithmic predecessor and is constrained to 2-dataset pairwise application.
