# HARP — Usage Perspectives for Multi-Platform Bulk RNA Harmonization

**Full name:** Harmonized Approach for Reference Profiles  
**Reference:** Nozari et al. (2025). *Bioinformatics* 41(9), btaf455. https://doi.org/10.1093/bioinformatics/btaf455  
**GitHub:** https://github.com/spang-lab/harp  
**Companion package:** https://github.com/spang-lab/harplication

**Context:** Evaluation of HARP as a harmonization method for ~5,444 samples across 88 cohorts from mixed platforms (Affymetrix GPL570, Illumina NGS, Illumina microarray, Agilent microarray). Reference batch: RNASeq_FF_PolyA (n=1,039). Current best batch correction: FSQN (R) at ~16% PCA variance explained by batch.

---

## What HARP Actually Does — Core Concept

HARP is a **computational tissue deconvolution accuracy improvement tool**, not a batch effect correction tool. This distinction is critical and immediately relevant to applicability.

The standard bulk deconvolution linear model is:

```
Y = X · C
```

where:
- **Y** (genes × samples) — bulk expression matrix (the data you have)
- **X** (genes × cell types) — reference cell-type signature matrix (e.g., from sorted RNA-seq)
- **C** (cell types × samples) — cell type proportion matrix (what deconvolution estimates)

The problem HARP solves: when Y comes from a different platform than X (e.g., bulk RNA-seq vs. microarray-derived reference), the model breaks down because platform-specific biases make X and Y incompatible. HARP learns a harmonized reference **X'** that is adapted to match the bulk platform.

**HARP moves X toward Y. It does NOT move Y toward a common space.** The bulk expression matrix Y enters HARP as input and exits unchanged.

---

## Algorithm — Step by Step

**Objective function (training mode):**

```
L(φ*, α) = ||Y − φ* · diag(α) · C*||² + λ · R(X*, φ*)
```

where:
- `φ*` — the harmonized reference profile being optimized (starts from X)
- `α` — vector of cell-type-specific scaling factors correcting systematic measurement bias per cell type
- `C*` — composition matrix augmented with an extra "unidentified cell type" row
- `λ` — regularization strength (tuned via cross-validation over log range [0, 2¹⁵])

**Regularization term** — soft-hinge log-sigmoid penalty keeping φ* close to original X*:

```
R(X*, φ*) = Σᵢⱼ [ ln(1 + exp((φ − x)ᵢⱼ)) + ln(1 + exp((−φ + x)ᵢⱼ)) ]
```

Higher λ keeps X' close to the original reference; lower λ allows more adaptation toward the bulk data.

**Alternating optimization loop:**

1. **Initial reference estimation** — estimate X from training bulk Y and measured compositions C via gradient descent (Armijo backtracking line search)
2. **Initial DTD model training** — train a Digital Tissue Deconvolution (DTD) model using estimated X to generate initial C predictions
3. **Alpha estimation** — for each cell type, fit linear regression `C_measured ~ α · C_estimated`; extract slope as correction factor α; reset non-positive values to 1
4. **Composition adjustment** — apply: `C_corrected = α × C_measured`
5. **Re-estimate reference** — re-optimize φ* using C_corrected to produce harmonized X'
6. **Final DTD training** — train final model on X'; apply to test bulk samples for cell proportion output

**Output:**
- **X'** — the harmonized reference profile (genes × cell types)
- **C'** — estimated cell compositions for input bulk samples
- **Reconstructed bulk** Y ≈ X'·C' — model artifact, not a cleaned expression matrix

The "unidentified cell type" extension adds an extra column to X and X' to absorb signal from cell types present in the tissue but absent from the reference, preventing composition misattribution.

---

## Data Types and Design Target

| Input | Role in HARP |
|---|---|
| Bulk RNA-seq | Primary bulk platform (Y matrix) |
| Microarray bulk | Supported but peripheral; peripheral validation only |
| scRNA-seq | Source for initial reference profiles (X) |
| Sorted bulk RNA-seq | Alternative reference source |
| Flow cytometry / FACS measurements | **Mandatory training data** — experimental cell compositions C |

**Primary design target:** Improving deconvolution accuracy when bulk data and the cell-type reference come from different platforms or experimental contexts.

**NOT designed for:** Removing batch effects from bulk expression matrices, producing harmonized expression data, or operating without experimental cell composition ground truth.

---

## Training Data Requirement — The Hard Constraint

Training HARP requires **paired calibration samples** with both:

1. **Bulk gene expression** (Y_train, genes × n_calibration_samples)
2. **Experimentally measured cell type proportions** (C_train, cell types × n_calibration_samples) — obtained from flow cytometry, FACS sorting, or equivalent

This is non-negotiable. There is no unsupervised mode or workaround.

**Scale used in the paper:**
- Simulated data: 20 training bulk samples
- PBMC real data: 150 training samples (out of 250 total with paired flow cytometry)

**Why this is prohibitive for 88 retrospective cohorts:** Virtually all samples in the assembled B-cell lymphoma dataset are archival (FFPE, frozen biopsies, GEO public data). None have paired flow cytometry measurements of cell type proportions at the sample level. Collecting such data prospectively for even a fraction of cohorts would require new wet-lab experiments.

---

## Assumptions

- **Cell type anchor:** Cell types maintain relatively consistent gene expression programs across datasets; only a small subset of genes ("local inconsistencies") strongly violate this
- **Linear mixing model holds:** Y ≈ X·C at least approximately
- **Systematic bias is cell-type-specific and sample-constant:** The α correction factors are scalars per cell type, constant across samples in the cohort
- **Regularization prevents reference drift:** λ controls how far X' can deviate from original X; tuned by cross-validation
- **Calibration data is representative:** Harmonization transfers to unseen test samples from the same tissue context — degrades if target samples are biologically or technically very different from the training set

---

## Validation in the Paper

**Datasets used:**
- Simulated bulk: constructed from two non-Hodgkin lymphoma scRNA-seq studies (Roider et al. 2020: 35,284 cells; Steen et al. 2021: 28,416 cells)
- Real bulk: 250 PBMC RNA-seq samples (Zimmermann et al. 2016) with flow cytometry ground truth
- References: sorted RNA-seq (Monaco et al. 2019)
- Microarray: LM22 signature and GSE65133 data appear only in the harplication benchmarking code, not in the main validation

**Competing methods:** BayesPrism, CIBERSORT, CIBERSORTx, MuSiC, DTD

**Key results:**
- Simulated data: HARP "significantly outperformed its competitors across all performance metrics" (combined R, sample-level Rs, cell-type-level Rc)
- PBMC real data: statistically significant improvement in sample-level (Rs) performance; cell-type-level (Rc) improvement was **NOT statistically significant**
- When competing methods were given HARP's harmonized X' instead of the original reference, their performance also improved substantially — the harmonized reference is portable

**What the paper does NOT test:**
- Large-scale multi-platform cohorts (88 cohorts, >5,000 samples)
- Affymetrix microarray data as bulk input
- Multi-platform harmonization without paired experimental compositions
- Batch effect removal evaluated by PCA variance metrics

---

## Known Limitations (From Authors and Analysis)

1. **Mandatory wet-lab calibration data** — flow cytometry ground truth is required; retrospective cohorts cannot use HARP in training mode without new experiments
2. **RNA-seq-centric validation** — core benchmarks use RNA-seq bulk + RNA-seq reference; microarray is peripheral
3. **Cross-platform generalization not demonstrated** — large platform divergence (Affymetrix GPL570 vs. PolyA RNA-seq) exceeds the validated scope
4. **Scale not demonstrated** — maximum validation cohort is 250 samples; 5,444 samples across 88 cohorts is untested
5. **No unsupervised mode** — strict requirement for paired experimental proportions; no workaround
6. **Cell-type-level Rc improvement not significant on real data** — only sample-level Rs was significant
7. **scRNA-seq reference artifacts** — zero inflation and lack of ribosomal depletion in scRNA-seq references are known issues that motivated HARP, but these are downstream of the platform problem
8. **Context transfer limitation** — performance degrades when target tissue or disease state differs from the calibration cohort

---

## What HARP Produces vs. What This Project Needs

| | HARP output | This project needs |
|---|---|---|
| **Expression matrix** | Y unchanged (input = output) | Harmonized genes × 5,444 samples matrix |
| **Harmonized reference** | X' (genes × cell types) | Not relevant |
| **Cell compositions** | C' proportions per sample | Useful downstream, but not the harmonization step |
| **Batch correction** | Not performed | Central objective (reduce RNA_BATCH R² from 95% → ~16%) |

---

## Arguments FOR Using HARP in This Project

- **Biologically relevant to FL research:** The built-in example dataset is B-cell lymphoma (non-Hodgkin); the tool was developed in a lymphoma-adjacent context
- **Harmonized reference is portable:** If a HARP-trained X' for B-cell types exists (or can be obtained from the spang-lab), it could improve reference-based B-cell deconvolution quality across platforms
- **Handles unknown cell types:** The unidentified cell type extension is relevant for tumor microenvironment heterogeneity in FL
- **DTD foundation is sound:** The underlying Digital Tissue Deconvolution framework has published performance in lymphoma contexts

All of these arguments apply to HARP as a **downstream deconvolution quality improvement tool**, not as a harmonization method.

---

## Arguments AGAINST Using HARP for Multi-Platform Harmonization

1. **Wrong problem:** HARP solves reference-bulk compatibility for deconvolution. The project problem is batch effect removal across 88 platform-heterogeneous bulk expression cohorts. These are fundamentally different problems.

2. **No bulk expression output:** HARP does not produce a harmonized genes × samples matrix. It cannot replace or supplement FSQN, ComBat, or quantile normalization in the harmonization pipeline.

3. **Mandatory training data is unavailable:** None of the 88 assembled cohorts have paired flow cytometry / FACS measurements. Running HARP in training mode is not possible without new wet-lab experiments.

4. **Platform scope mismatch:** Core validation is RNA-seq only. Affymetrix GPL570 microarray as bulk input is outside the validated range.

5. **Scale mismatch:** Validated on ~250 samples, 1 cohort. The 88-cohort, 5,444-sample setup is entirely outside demonstrated scope.

6. **No PCA/UMAP batch metric:** HARP has no mechanism to evaluate or minimize RNA_BATCH explained variance in PCA space, which is the primary benchmark metric in this project.

---

## Potential Downstream Use (After Harmonization)

HARP could be relevant **after** the harmonization problem is solved, in a different analytical context:

> Once the FSQN-normalized expression matrix exists, use HARP to improve reference-based B-cell cell type proportion estimation across platforms — specifically to learn a harmonized B-cell reference profile X' adapted to the mixed-platform bulk data.

This would require:
1. A calibration subset with both bulk expression AND flow cytometry cell type measurements (not currently available)
2. Or: using the spang-lab's pre-trained HARP reference if it covers centroblast/centrocyte/naive/memory/plasma B-cell types — worth checking

This is a different use case from the harmonization benchmark and would be a post-SOM analysis step.

---

## Comparison with Methods in the Benchmark

| Aspect | HARP | FSQN (current best) | ComBat |
|---|---|---|---|
| Output | Harmonized reference + cell proportions | Harmonized expression matrix | Harmonized expression matrix |
| Supervised | Yes (flow cytometry required) | No | Partially (biology covariate optional) |
| Multi-platform | RNA-seq centric | RNA-seq + microarray validated | RNA-seq + microarray validated |
| Scale validated | ~250 samples | ~5,000+ (our benchmark) | Large cohorts routinely |
| PCA batch R² metric | Not applicable | ~16% | ~30-40% |
| Applicable to this project | No (wrong output type) | Yes (benchmark winner) | Yes (in benchmark) |

---

## Verdict

**HARP cannot be applied to the multi-platform harmonization objective of this project.**

It is the wrong tool for the wrong problem. HARP harmonizes a cell-type reference profile toward a bulk dataset to improve deconvolution accuracy. This project needs to harmonize 88 bulk expression cohorts across platforms to reduce RNA_BATCH-driven variance in PCA space. These goals are mechanistically incompatible.

**Definitive blockers:**
1. No harmonized expression matrix output
2. No unsupervised mode — requires experimental cell proportion ground truth unavailable for retrospective cohorts
3. RNA-seq-centric validation does not cover the Affymetrix + mixed-platform scope

**Possible future use:** Post-harmonization, HARP could be explored to refine B-cell deconvolution quality across platforms if calibration data can be assembled — but this is a different analytical question from batch effect removal.

The relevant tools for the current harmonization objective remain the 24 methods evaluated in the 960-job cross-product benchmark (`bench_shared.py`), with FSQN (R) as the current winner at ~16% residual batch variance.
