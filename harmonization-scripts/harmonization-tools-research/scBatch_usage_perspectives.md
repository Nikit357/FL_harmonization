# scBatch — Usage Perspectives for Multi-Platform Bulk RNA Harmonization

**Full name:** scBatch: Batch Effect Correction of RNA-seq Data through Sample Distance Matrix Adjustment  
**Reference:** Fei, T. & Chen, T. *Bioinformatics* 36(10), 3115–3123 (2020). https://doi.org/10.1093/bioinformatics/btaa097  
**GitHub:** https://github.com/tengfei-emory/scBatch  
**Implementation:** R package (`scBatch`), backed by RcppArmadillo (C++)

**Context:** Evaluation of scBatch as a harmonization candidate for ~5,444 samples across 88 cohorts from mixed platforms (Affymetrix GPL570, Illumina NGS, Illumina microarray, Agilent microarray). Reference batch: RNASeq_FF_PolyA (n=1,039). Current benchmark winner: FSQN (R) at ~16% PCA variance explained by batch (down from ~95% raw).

---

## What scBatch Actually Does — Core Concept

scBatch corrects batch effects by adjusting the **sample-level Pearson correlation matrix** rather than transforming gene expression values directly (as ComBat, FSQN, or limma do). The intuition is: if we have a "batch-free" target for what the inter-sample similarity structure should look like, we can find a linear transformation of the expression matrix that brings the actual sample correlations as close as possible to that target.

The method runs in two conceptually separate stages:

**Stage 1 — Build a reference distance matrix D:**  
QuantNorm (a prior non-parametric method by the same authors) corrects the raw Pearson correlation matrix of the count matrix to produce the batch-free reference distance matrix **D**. This is the correction target.

**Stage 2 — Find the weight matrix W:**  
Given the reference D, scBatch finds a weight matrix **W** (p × p, where p = genes) such that the corrected expression matrix **Y = X · W** has a Pearson correlation matrix **D_Y** as close as possible to D.

The objective function is:

```
L(W) = ½ ‖D_Y − D‖²_F
```

where ‖·‖_F is the Frobenius norm. Optimization is performed via **random block coordinate descent** with Armijo line search for adaptive step sizing. In each iteration, samples are partitioned into m groups; group-specific columns of W are updated sequentially. Setting m=1 reduces to gradient descent; m=n reduces to full coordinate descent.

**Output:** Y = X · W — a corrected genes × samples matrix (non-integer values). Batch-wise standardization is applied post-correction.

---

## Algorithm — Step by Step

1. Input: p × n log-normalized expression matrix X, batch labels
2. QuantNorm adjusts the raw Pearson correlation matrix of X → reference matrix D (n × n)
3. Initialize W = I (identity matrix)
4. Random block coordinate descent loop:
   - Partition n samples into m groups
   - For each group: compute gradient of L(W) w.r.t. group columns, update W with Armijo step
   - Check convergence criterion
5. Compute Y = X · W
6. Apply batch-wise standardization to Y
7. Output Y for downstream analysis

---

## Validation Datasets

scBatch was validated **entirely on scRNA-seq data**:

| Dataset | Cells | Batches | Platforms |
|---|---|---|---|
| Mouse ESCs (E-MTAB-2600) | 469 | 2 | scRNA-seq |
| Mouse neuron (GSE59739) | 610 | multiple libraries | scRNA-seq |
| Human pancreas (GSE81608) | 651 | 12 donors | scRNA-seq |
| Simulated data | 270–1,080 | 3 | synthetic scRNA-seq |

Bulk RNA-seq (ENCODE human/mouse tissues) is mentioned in supplementary material only. Multi-protocol integration (SMART-seq2 vs. CEL-seq2) is tested — with the result explicitly noted as "unsatisfactory" (see Limitations).

---

## Performance Against Competing Methods

Metrics: adjusted Rand index (ARI) for clustering, AUC/PR-AUC for DE gene detection, kBET for batch mixing, B-CeF for biological signal preservation.

| Dataset | scBatch ARI | ComBat ARI | limma ARI | MNN ARI |
|---|---|---|---|---|
| mESCs | **0.55** | 0.26 | 0.21 | 0.10 |
| Mouse neuron | **0.64** | 0.11 | 0.13 | 0.15 |
| Human pancreas | **0.60** | 0.44 | 0.48 | 0.07 |

scBatch outperforms on scRNA-seq ARI and biological signal preservation. These results do not transfer to bulk multi-platform data.

---

## Stated Limitations (From the Paper)

1. **Cross-platform integration explicitly unsatisfactory:** The authors state that when correcting across different sequencing protocols (e.g., SMART-seq2 vs. CEL-seq2), "residual batch effects remain visible after correction." This is the most important limitation for our use case.

2. **Balanced batch composition required:** The method assumes biological groups are "roughly balanced across batches." A severe violation (one diagnosis type concentrated in a single platform) biases the QuantNorm reference matrix D and degrades correction quality.

3. **Computational cost scales super-linearly:** Running time grows faster than linearly with n. The paper reports "hours for >1,000 cells." The authors acknowledge this as a significant practical limitation.

4. **Linear transformation only:** W is a linear transformation. Complex non-linear platform effects (e.g., saturation at high expression in microarrays) are not captured.

5. **Single distance metric:** Only Pearson correlation is implemented. Robustness to outlier samples depends entirely on this choice.

---

## Assessment for This Project

### Fundamental incompatibilities

**1. Designed for scRNA-seq — not validated on bulk or microarray data.**  
Every benchmark dataset in the paper is scRNA-seq (UMI or full-length cDNA). The method was designed around scRNA-seq-specific challenges: high sparsity, UMI count distributions, dropout, and moderate inter-batch cell-type composition differences. Affymetrix microarray data has entirely different distributional properties (saturated probes, probe-specific hybridization efficiencies, no dropout). The QuantNorm Stage 1 — which builds the reference D — assumes scRNA-seq count characteristics.

**2. Cross-platform integration is explicitly called out as the method's failure mode.**  
The paper tests exactly this — correcting across two sequencing protocols (SMART-seq2 vs. CEL-seq2) — and reports unsatisfactory results. Our dataset spans four technically distinct platform families (Affymetrix GPL570 probes, Illumina NGS polyA selection, Illumina microarray, Agilent microarray). The distributional gaps between RNA-seq and microarray are far larger than between two RNA-seq protocols.

**3. Balanced batch composition assumption is severely violated.**  
The 88-cohort dataset is highly heterogeneous in diagnosis composition per batch — many microarray cohorts are DLBCL-only or FL-only, while RNA-seq cohorts are mixed. This causes the QuantNorm reference matrix D to be biased by diagnosis-specific inter-sample correlations rather than reflecting batch-free biology.

**4. Scale is prohibitive.**  
The paper validates on at most 1,080 cells and reports "hours for >1,000." With 5,444 samples and p=3,520 genes, the W matrix being optimized is 3,520 × 3,520. Memory for D_Y alone is 5,444 × 5,444 × 8 bytes ≈ 237 MB; computing its gradient at each iteration involves O(n²p) operations. Realistic runtime would be days, not hours.

**5. The weight matrix W is genes × genes — not sample × sample.**  
This is a critical structural difference from all other methods in the benchmark. scBatch modifies gene-gene relationships to bring sample correlations in line with D. This means it can destroy gene co-expression structure (pathways, regulons) as a side-effect of batch correction — problematic for SOM metagene interpretation, which relies on co-expression geometry.

### What scBatch does correctly (for reference)

- Outputs a full p × n expression matrix ✓ (not a latent embedding — unlike HARP or MoDAmix)
- Does not require biological labels ✓
- Preserves some biological signal as measured by B-CeF ✓ (on scRNA-seq)
- Reference-free: does not require a designated reference batch ✓

These properties are necessary but not sufficient for applicability here.

---

## Comparison with Current Benchmark Methods

| Aspect | scBatch | FSQN (current best) | ComBat |
|---|---|---|---|
| Primary design target | scRNA-seq | Bulk multi-platform | Bulk RNA-seq |
| Correction mechanism | Sample correlation matrix → linear gene transform | Per-gene quantile replacement to reference | Empirical Bayes location/scale shift |
| Validated on microarray | No | Yes | Yes |
| Cross-platform tested | Yes — "unsatisfactory" | Yes — ~16% R² | Partial |
| Balanced design required | Yes (strictly) | No | Partially |
| Output format | Genes × samples matrix | Genes × samples matrix | Genes × samples matrix |
| Scale (our dataset) | Prohibitive (days) | ~minutes per job | ~minutes per job |
| Biological signal preservation | High (scRNA-seq) | High | Moderate |
| Covariate protection | No | No | Yes (biology covariate) |

---

## Verdict

**scBatch is not applicable for this project.**

The three blocking reasons are:

1. **Wrong validation domain** — exclusively scRNA-seq; no demonstrated performance on bulk or microarray data
2. **Self-reported failure on cross-platform correction** — the exact use case that matters here
3. **Computational cost** — super-linear scaling makes it impractical for 5,444 samples without any guarantee of correctness on this data type

The method's core concept (adjusting sample-level correlation structure rather than gene-level distributions) is interesting, but this makes it *more* destructive of gene co-expression structure — which would directly harm SOM metagene interpretation.

**FSQN (R) remains the benchmark winner.** scBatch would not be competitive even if the platform and scale issues were resolved, because the balanced-composition assumption is structurally violated by 88 heterogeneous retrospective cohorts.
