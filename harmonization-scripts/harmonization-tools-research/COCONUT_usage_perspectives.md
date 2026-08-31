# COCONUT — Usage Perspectives for Multi-Platform Bulk RNA Harmonization

**Full name:** COmbat CO-Normalization Using conTrols  
**Authors:** Sweeney TE, Wong HR, Khatri P  
**Reference:** *Science Translational Medicine* 8(346), 346ra91 (2016). https://doi.org/10.1126/scitranslmed.aaf7165  
**R package:** `COCONUT` on CRAN (`install.packages("COCONUT")`), GPL-3  
**Code/data:** http://khatrilab.stanford.edu/sepsis

**Context:** Evaluation of COCONUT as a harmonization candidate for ~5,444 samples across 88 cohorts from mixed platforms (Affymetrix GPL570, Illumina NGS, Illumina microarray, Agilent microarray). Reference batch: RNASeq_FF_PolyA (n=1,039). Current benchmark winner: FSQN (R) at ~16% PCA variance explained by batch (down from ~95% raw).

---

## What COCONUT Actually Does — Core Concept

COCONUT is a modification of ComBat that addresses one of ComBat's most important failure modes: **over-correction when biological groups are imbalanced across batches**. Standard ComBat estimates batch effect parameters from all samples together; if one batch is entirely DLBCL and another is entirely FL, ComBat mistakes some biological signal for batch effect and removes it.

COCONUT's solution: **estimate batch parameters exclusively from healthy/control samples**, then apply those parameters to the disease samples without ever using disease labels in the estimation. The batch correction applied to disease data is identical to what the controls received — so relative distances between disease samples and their matched controls are preserved exactly.

The paper's primary application was diagnosing bacterial vs. viral infections across 30 heterogeneous whole-blood microarray cohorts. COCONUT enabled pooling those cohorts without diagnosis-aware batch correction.

---

## Algorithm — Complete Step by Step

Given N cohorts, each containing both healthy controls and disease samples:

### Step 1: Partition each cohort

For cohort i, split samples into:
- **H_i** — healthy/control samples (label = 0 in `control.0.col`)
- **D_i** — disease samples

Disease labels within D_i are not used or required.

### Step 2: Run ComBat on the pooled controls only

Concatenate all H_i into a single controls-only matrix H. Apply standard ComBat (empirical Bayes) across batches using H, **without any biology covariate**:

```
Z_ijg = (Y_ijg − α̂_g − X β̂_g) / σ̂_g
```

where Y_ijg = expression of gene g in control sample j of batch i, α̂_g = mean expression, σ̂_g = SD. The additive (γ*_ig) and multiplicative (δ*_ig) batch parameters are estimated by empirical Bayes shrinkage.

### Step 3: Extract ComBat parameters

Retain from the controls-only fit:
- α̂_g, β̂_g, σ̂_g (global gene statistics)
- γ*_ig (additive batch effect per gene per batch)
- δ*_ig (multiplicative batch effect per gene per batch)

These parameters capture the batch-specific shifts in the control distribution.

### Step 4: Apply those parameters to disease samples

For disease sample k in batch i, gene g:

```
E_ikg = (D_ikg − α̂_g − X β̂_g) / σ̂_g
D*_ikg = σ̂_g × [(E_ikg − γ*_ig) / δ*_ig] + α̂_g + X β̂_g
```

The disease samples are corrected using the exact same additive and multiplicative offsets derived from the controls. Within each batch, the relative positions of disease samples with respect to their controls are unchanged — only the absolute scale shifts.

### byPlatform mode

Setting `byPlatform=TRUE` groups cohorts by GPL platform ID rather than treating each cohort as a separate batch. This allows inclusion of cohorts that lack their own control samples, as long as at least one cohort on that platform has controls. Within-platform inter-cohort differences are additionally corrected by quantile normalization before ComBat.

### Output

A list with three elements:
- `$COCONUTList` — corrected disease-only expression matrices per cohort
- `$rawDiseaseList` — pre-correction disease matrices (for comparison)
- `$controlList` — corrected controls + estimated Bayes parameters (diagnostics)

The output contains **disease samples only** — controls are used as instruments and discarded.

---

## Input Data Requirements

| Requirement | Details |
|---|---|
| Healthy/control samples | Required in every cohort (or at least one per platform in byPlatform mode) |
| Gene-level expression matrix | Log-transformed; genes × samples per cohort |
| Control homogeneity | All controls must plausibly share one distribution (same tissue type, same species, same health state) |
| R environment | Standard CRAN install; no system dependencies |
| Matched FASTQ | Not required — works on pre-processed expression matrices |
| Reference batch | Not required — ComBat learns parameters jointly across all cohorts |

---

## Validation

The paper validated across 30 independent whole-blood microarray cohorts spanning bacterial infections, viral infections, and SIRS. No matched data required. No reference batch.

| Validation set | N | Cohorts | AUC |
|---|---|---|---|
| Discovery (bacterial/viral) | 426 | 8 | 0.97 |
| Direct validation | 341 | 6 | 0.91 |
| COCONUT global (whole blood) | 1,040 | 24 | 0.92–0.93 |
| COCONUT global (PBMC) | 259 | 6 | 0.92 |

Key ablation finding: COCONUT clearly outperformed standard ComBat with the same gene set, because the diagnosis-imbalanced cohorts caused ComBat to partially remove true infection signal when it was confounded with batch.

---

## Why COCONUT Is Conceptually Relevant to This Project

The FL/DLBCL dataset has exactly the failure mode that COCONUT was designed to fix: **diagnosis composition is severely imbalanced across batches**. Many GPL570 cohorts are DLBCL-only; many RNASeq cohorts mix FL and DLBCL; the normal B-cell data is concentrated in a distinct set of sorted normal B-cell datasets. Standard ComBat (`05_combat`) applied to this dataset will partially conflate diagnosis with batch and remove biological signal.

COCONUT's response — estimate batch parameters from controls only, apply to disease — is the theoretically correct approach for imbalanced multi-cohort data. In the benchmark, `05_combat` achieves only ~30–40% batch R² (mediocre); COCONUT could in principle do better while causing less biological over-correction.

---

## Assessment for This Project

### What works in COCONUT's favour

- Works on gene-level expression matrices — compatible with our data format ✓
- No matched samples required ✓
- No reference batch designation required ✓
- Available as a maintained CRAN R package ✓
- Theoretically solves the diagnosis-imbalance problem that defeats standard ComBat ✓
- `byPlatform=TRUE` allows including cohorts without controls ✓
- Output is a genes × samples expression matrix ✓

### Blocker 1: Most disease cohorts have no matched controls

COCONUT's fundamental requirement is that each cohort (or at least one cohort per platform in byPlatform mode) contains healthy/control samples. Of the 88 FL/DLBCL cohorts, the vast majority are pure disease cohorts — DLBCL-only or FL-only tumor collections from GEO and an internal cohort database. They were never designed to include normal tissue.

Normal B-cell samples do exist in the dataset (Normal_B_cells: 28 sorted B-cell datasets, ~1,000 samples; Kassandra: ~some deconvolution-derived normals), but they are concentrated in **dedicated normal B-cell datasets**, not distributed as internal controls within each disease cohort. For most of the 46 internal-database DLBCL/FL cohorts, there are zero normal B-cell samples.

In `byPlatform=TRUE` mode, COCONUT would group all GPL570 cohorts together and use the sorted normal B-cell GPL570 datasets as the control source for the whole GPL570 platform group. This is a substantial stretch of the intended use — the ComBat parameters derived from sorted B cells in one study would be applied to DLBCL tumors in another, with no guarantee that the estimated batch effect reflects only technical variation and not biology.

### Blocker 2: Control population is biologically heterogeneous

COCONUT requires that all controls share "the same distribution" — same tissue, same species, same health state. The authors ran whole blood and PBMCs in **separate COCONUT instances** specifically because those two sample types have different baseline expression.

The sorted normal B-cell controls span 11 distinct cell types: Naive, Centroblast, Centrocyte, Memory, and Plasma B cells, plus intermediate states. A Centroblast (GC dark zone, high MYC/CXCR4) and a Memory B cell (post-GC, CD27+) have fundamentally different transcriptomes — the difference is larger than typical batch effects. Pooling all normal B cells as COCONUT controls would violate the equal-distribution assumption and corrupt the batch parameter estimates.

The only way to satisfy the assumption would be to restrict controls to a single cell type — for example, Naive B cells only (CD45RA+, IgD+, CD27−). Naive B cells are present in several sorted normal B-cell datasets, but:
- They are on different platforms (some on GPL570, some RNA-seq)
- The counts per platform are small (perhaps 50–100 Naive B cells per platform group)
- Most disease cohorts have zero paired Naive B cells

Restricting to Naive-only controls would give COCONUT very few samples per batch to estimate parameters from, making the empirical Bayes estimates highly unstable.

### Blocker 3: byPlatform mode does not solve the cross-platform harmonization problem

The primary challenge in the FL dataset is harmonizing RNA-seq vs. microarray data (the cross-platform gap explains ~95% of pre-normalization PCA variance). `byPlatform=TRUE` groups cohorts within the same GPL ID before running ComBat. This means:
- All GPL570 cohorts form one group
- All RNASeq_FF_PolyA cohorts form another
- Illumina microarray and Agilent remain separate groups

After COCONUT in byPlatform mode, the RNA-seq and microarray matrices would each be internally harmonized but would **not be merged** — the cross-platform gap persists. To use the harmonized data jointly, a second cross-platform normalization step (FSQN, quantile normalization, or TDM) would still be required afterward. COCONUT would be a preprocessing step within each platform, not a complete solution.

### Where COCONUT might add value

COCONUT is not a replacement for FSQN, but it could serve as a **targeted within-platform harmonization** step for the GPL570 cohorts specifically, before cross-platform normalization:

1. Identify a homogeneous control cell type present in multiple GPL570 datasets (e.g., Naive B cells from sorted normal B-cell datasets)
2. Run COCONUT `byPlatform=TRUE` on GPL570 cohorts only, using Naive B cells as controls
3. Feed the resulting GPL570-harmonized disease matrix into FSQN for cross-platform normalization

This would potentially correct intra-GPL570 batch effects (differences between GPL570_FF_Unknown and GPL570_FFPE_Unknown cohorts) in a diagnosis-blind way, then let FSQN handle the RNA-seq vs. microarray gap. Whether this two-step approach outperforms FSQN alone is an empirical question — it would require adding a pre-processing block before the benchmark pipeline, not simply adding a new METHODS entry.

### Why this is not straightforward to benchmark

Unlike all 25 current benchmark methods, COCONUT cannot be called as a drop-in `normalize_fn(exp_df, ann_df)`. It requires:
- Pre-splitting each cohort into controls and disease samples
- Controls and disease samples processed in separate matrices
- Output contains only disease samples (controls are consumed as instruments)
- The resulting disease matrix has a different sample set than the input

This means COCONUT would need a dedicated wrapper that restructures the benchmark's data flow, not just a new function in `bench_shared.py`. The output would also be incompatible with the current R² metric framework, which requires comparing the full post-normalization matrix against annotation — but COCONUT's output drops the control samples.

---

## Comparison with Current Benchmark Methods

| Aspect | COCONUT | FSQN (current best) | 05_combat |
|---|---|---|---|
| Core mechanism | ComBat parameters estimated from controls only, applied to disease | Per-gene quantile replacement to reference batch | Empirical Bayes location/scale, all samples |
| Requires healthy controls | **Yes (in every cohort or platform group)** | No | No |
| Handles diagnosis imbalance | Yes — by design | No | Fails under extreme imbalance |
| Reference batch required | No | Yes (RNASeq_FF_PolyA) | No |
| Cross-platform capable | No (works within platform groups) | Yes | Partial |
| Multi-cohort validated | Yes (30 cohorts) | Yes | Yes |
| Output format | Genes × samples (disease only) | Genes × samples | Genes × samples |
| CRAN availability | Yes | Yes (FSQN package) | Yes (sva package) |
| Drop-in benchmark compatible | **No — restructures data flow** | Yes | Yes |
| Applicable to FL dataset as-is | **No (controls absent from most cohorts)** | Yes | Yes |

---

## Verdict

**COCONUT cannot be applied to this project in its standard form.**

The two structural blockers — absence of matched controls in most disease cohorts, and biological heterogeneity of the available normal B-cell controls — prevent a correct COCONUT run across the 88-cohort dataset. Forcing the method with `byPlatform=TRUE` and heterogeneous controls would violate the equal-distribution assumption and produce unreliable batch parameter estimates.

**What COCONUT offers that is genuinely worth noting:**

Its core design principle — estimate batch parameters from controls, apply to disease — is the theoretically correct approach for the specific failure mode that affects this dataset (diagnosis-imbalanced cohorts). Standard ComBat (`05_combat`) over-corrects when FL or DLBCL is concentrated on a single platform. COCONUT would not have this problem if controls were available.

**The conceptually correct successor to this project's ComBat limitation** is not COCONUT (which requires controls per batch) but FSQN (which avoids the biology-confounding issue entirely by using distributional shape matching from a reference rather than EB across all samples). This is consistent with FSQN being the benchmark winner.

**A niche future application:** If a prospective multi-platform lymphoma profiling study were designed with matched normal B-cell samples collected alongside tumor biopsies in every cohort, COCONUT would become directly applicable and would be the preferred method over ComBat for the intra-platform harmonization step.

**FSQN (R) remains the benchmark winner.** COCONUT is not suitable as a benchmark normalization method for the current dataset. It is worth understanding conceptually as the theoretically principled alternative to ComBat for imbalanced designs — but the dataset's structure prevents its use.
