# MoDAmix — Applicability Assessment for FL Harmonization

**Paper:** "A unified framework for correcting batch effects and integrating multi-omics data."
*Scientific Reports* (2026). DOI: https://www.nature.com/articles/s41598-026-42355-9
**Software:** https://github.com/cbi-bioinfo/MoDAmix (PyTorch 2.8.0)

**Short answer: MoDAmix is not applicable for this use case.**

---

## What MoDAmix Is

A **PyTorch adversarial domain adaptation framework** with four stages:
1. Pre-train modality-specific feature extractors + classifier on labeled source data
2. Per-modality adversarial alignment (GAN-style: extractor fools a domain discriminator)
3. Joint multi-omics adversarial alignment in a shared latent space
4. Semi-supervised class alignment using pseudo-labels + centroid matching across domains

The output is a **learned latent embedding** — not a corrected genes × samples expression matrix.

---

## Why It Does Not Fit This Problem

| Requirement of MoDAmix | Our dataset situation |
|---|---|
| **Labeled source cohort** (subtype annotations required for pre-training and pseudo-labeling) | SOM is *discovering* the subtypes — labels don't exist yet upstream of the analysis |
| **Exactly two batches** (source → target transfer; all benchmarks: 1 source + 1 target) | 88 cohorts, 6 major RNA_BATCH groups, 4 platforms |
| **Two omics modalities** (RNA-seq + methylation, or scRNA + scATAC) | Single-omics transcriptomics only |
| **Outputs a latent embedding** for downstream classification/clustering | oposSOM requires a genes × samples matrix in the original feature space |
| **~3,000 features per omics layer** after reduction | Full-coverage 3,520 genes — manageable, but irrelevant given other blockers |

---

## Benchmark Context

MoDAmix was compared against Harmony, ComBat, and Scanorama on three tasks (mouse brain sc-multiomics, AML bulk, brain cancer bulk). It won on Silhouette/DBI/F1 — but all three tasks are **two-batch RNA+methylation or scRNA+scATAC transfer problems with known labels**. The margin over Harmony/ComBat is modest on accuracy (0.72 vs. 0.70 on AML F1) and large on clustering metrics — but those metrics measure cluster compactness in the learned embedding, not residual batch variance in expression space like the PCA R² metric used in this benchmark.

---

## Bottom Line

MoDAmix solves a different problem class: **supervised subtype transfer between two multi-omics cohorts**. Our problem is **unsupervised harmonization of 88 single-omics cohorts across 4 platforms for SOM input**. There is no overlap on any of the three critical axes (supervision, modality count, output format).

FSQN-R remains the best option per the benchmark. If exploring the adversarial/deep-learning direction for this specific problem in the future, closer analogues would be **scVI** (VAE-based, single-omics, multi-batch) or **DANN** applied to expression data — but both also output embeddings rather than corrected matrices, which is the same fundamental incompatibility with oposSOM.
