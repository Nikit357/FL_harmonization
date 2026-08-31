# CSN — Usage Perspectives for Multi-Platform Bulk RNA Harmonization

**Full name:** CSN (Cross-Study cross-species Normalization)  
**Paper:** Feldman S, Ner-Gaon H, Treister E, Shay T. "Comparison and development of cross-study normalization methods for inter-species transcriptional analysis." *PLoS ONE* 19(9): e0307997 (2024). https://doi.org/10.1371/journal.pone.0307997  
**PMC:** https://pmc.ncbi.nlm.nih.gov/articles/PMC11386461/  
**Code:** Not publicly released (CMA-ES MATLAB implementation is referenced but not distributed with the paper)

**Context:** Evaluation of CSN as a harmonization candidate for ~5,444 samples across 88 cohorts from mixed platforms (Affymetrix GPL570, Illumina NGS, Illumina microarray, Agilent microarray). Reference batch: RNASeq_FF_PolyA (n=1,039). Current benchmark winner: FSQN (R) at ~16% PCA variance explained by batch (down from ~95% raw).

---

## What CSN Actually Does — Core Concept

CSN is a normalization method designed for **cross-species transcriptomics** — specifically to enable joint analysis of gene expression datasets from different organisms (human and mouse). The central problem it solves is fundamentally different from cross-platform batch correction: existing methods such as ComBat/EB, XPN, and DWD tend to over-correct inter-species differences by treating true biological divergence as technical noise, since both arise as broad distributional shifts affecting many genes at once.

CSN's novelty is a **loss function that simultaneously optimises two competing objectives**:
1. **CSC (Cross-Study Comparison) index** — increase overlap between DEG lists computed within-species ("condition lists") and DEG lists computed across species ("cross lists"); this drives dataset-to-dataset comparability
2. **IOU (Intersection Over Union) index** — preserve the within-dataset condition comparisons (DEG ranks and directions must not be distorted by normalization); this guards against over-correction
3. **Penalty term** — hard threshold `t` on IOU; solutions with IOU below `t` are penalised heavily, enforcing a minimum floor of biological signal preservation

The displacement model is a piecewise affine transform: genes are clustered via fuzzy k-means (k=50), and each cluster is assigned a slope and intercept. The total parameter count is 4k+4 = 204 for k=50. Parameters are optimised via **CMA-ES** (Covariance Matrix Adaptation Evolution Strategy), a derivative-free evolutionary algorithm capped at 50 iterations.

The underlying assumption is that real biological expression differences across conditions are concentrated in "a small number of genes," whereas technical batch noise affects "hundreds of genes similarly" — a heuristic specific to inter-species variation, not platform technology differences.

---

## Algorithm — Step by Step

### Step 1: Gene restriction to one-to-one orthologs
Analysis is restricted to 15,877–16,444 genes with unambiguous one-to-one orthologs between human and mouse. Non-orthologous and one-to-many genes are excluded.

### Step 2: Pre-standardisation
Each dataset is standardised using weighted means and standard deviations across datasets (not within-sample). This brings the two species' expression distributions onto a common scale before the displacement model is applied.

### Step 3: Gene clustering
All shared genes are clustered into k=50 groups using fuzzy k-means based on expression profiles across all samples. Each cluster is assigned a shared slope (β) and intercept (α).

### Step 4: Displacement model application
For gene g in cluster c, the transform is:
```
g_normalised = α_c + β_c · g_raw
```
Total parameters: 4k+4 = 204 (slope, intercept per cluster × 2 datasets + 4 global parameters).

### Step 5: CMA-ES optimisation
The 204 parameters are optimised jointly via CMA-ES to minimise the composite loss:
```
L = −CSC + λ · max(0, t − IOU)
```
where `t` is the IOU penalty threshold (tuned; paper uses t=0 and t=0.7 as ablations). 50 iterations maximum.

### Step 6: Application
The fitted displacement model is applied to both datasets; the result is a pair of normalised expression matrices over the shared ortholog gene space.

---

## Input / Output

| | Details |
|---|---|
| **Input** | Two log2-transformed RNA-seq matrices (one per species), restricted to one-to-one orthologous genes |
| **Species** | Human and mouse only (paper validation scope) |
| **Assay** | Bulk RNA-seq only |
| **Output** | Two normalised expression matrices over the ortholog gene space; dimensionality reduced to shared orthologs |
| **Hyperparameters** | k (cluster count, default 50), t (IOU threshold, tuned) |

---

## Experimental Validation

### Datasets used
Four public GEO immune cell RNA-seq datasets: mouse GSE122597 (83 samples, 5 cell types), GSE124829 (65 samples, 10 cell types); human GSE60424 (20 samples, 6 cell types), GSE107011 (28 samples, 8 cell types). All bulk RNA-seq; immune/naïve cell types only; total ~196 samples.

### Methods compared
- Empirical Bayes (EB / ComBat)
- Distance Weighted Discrimination (DWD)
- Cross-Platform Normalization (XPN)
- CSN (t=0 and t=0.7)

### Results
- CSC index (higher = better inter-species comparability): CSN(t=0) > XPN > CSN(t=0.7) > EB
- IOU index (higher = better within-dataset preservation): EB > CSN(t=0.7) > DWD > CSN(t=0) > XPN
- CSN(t=0.7) achieved the best practical trade-off: IOU never below 0.68, CSC competitive with or exceeding EB
- XPN most aggressively removes technical noise but also destroys inter-species biological signal (low IOU)

### Key limitation acknowledged by authors
Small increases in the IOU threshold (0.70 → 0.75) caused disproportionate drops in CSC, indicating sensitivity to hyperparameter tuning. The method was never tested on microarray data or on more than two datasets simultaneously.

---

## Assessment for This Project

### The fundamental mismatch: cross-species ≠ cross-platform

CSN was designed to solve a specific problem: integrating gene expression from two different organisms (human, mouse) where the question is "which genes behave consistently across species?" Our problem is the opposite: all 88 cohorts are human, but they were profiled on four measurement technologies with distinct technical signatures.

The core assumption underlying CSN's loss function — that inter-species differences affect "a small number of genes" while technical noise affects "hundreds of genes similarly" — does not hold for our data. Affymetrix microarray vs. Illumina RNA-seq differences are broad-spectrum (probe hybridisation physics differ from sequencing counts in ways that affect the majority of the transcriptome, not a minority). This is exactly the condition CSN assumes does not exist when it classifies broad-distributional shifts as biological signal to be preserved via the IOU constraint.

If CSN were applied literally to our setting, the IOU term would actively resist correcting genuine platform effects, treating them as within-dataset "biological signal" worth preserving. The method would under-correct.

### No orthologous gene concept applies

CSN's gene restriction step requires a list of one-to-one orthologous genes between species. In our single-species setting this step is vacuous — every gene is its own ortholog. The 204-parameter cluster model that follows was calibrated on datasets defined by this ortholog restriction; there is no reason its k=50 clustering or CMA-ES convergence properties would behave sensibly on a 3,520-gene single-species matrix.

### No code available

The paper references a CMA-ES MATLAB implementation but provides no code release, no GitHub repository, and no R or Python package. Reimplementation from the paper would require:
1. Implementing fuzzy k-means in Python or R
2. Wrapping a CMA-ES library (e.g., `pycma`) with the composite CSC+IOU loss
3. Implementing the CSC and IOU index calculations, both of which require DEG list computation at each optimisation step

CSC computation involves running differential expression analysis (t-test or similar) at each of the 50 CMA-ES iterations across 204 parameters — computationally expensive and not validated outside the paper's four-dataset context.

### Comparison methods in this paper are already in our benchmark

The paper benchmarks CSN against EB (ComBat: `05_combat`), DWD (planned: `27_dwd`), and XPN (planned: `26_xpn`). All three are already present or will be in our 25+ method cross-product. The CSN paper thus provides useful validation evidence for those three methods, but CSN itself is not an additional candidate.

### Scale mismatch
The paper's validation used ~196 samples total across 4 datasets. Our dataset has 5,444 samples across 88 cohorts and 4 platforms. CMA-ES with a 204-parameter model was not tested at this scale; convergence properties would likely be very different.

---

## Comparison with Current Benchmark Methods

| Aspect | CSN | FSQN (current best) | ComBat (`05`) | XPN (planned `26`) |
|---|---|---|---|---|
| Problem domain | Cross-species | Cross-platform | Cross-batch | Cross-platform |
| Input assay | RNA-seq only | Mixed platforms | Mixed platforms | Mixed platforms |
| Requires matched/ortholog data | Yes (orthologs) | No | No | No |
| Gene space altered | Yes (ortholog restriction) | No | No | No |
| Output format | Expression matrix | Expression matrix | Expression matrix | Expression matrix |
| Code availability | **Not released** | R package (CRAN) | R/Python (many) | R package |
| Tested on microarray+RNA-seq | No | Yes | Partial | Partial |
| Number of datasets validated on | 4 (196 samples) | — | Many | Multiple |
| Over-correction risk | High (IOU term resists platform correction) | Low | Moderate | Moderate |
| Applicable to this project | **No** | Yes | Yes | Yes |

---

## Indirect Value: The IOU Preservation Concept

The IOU term in CSN's loss function encodes a useful idea: normalization should not rearrange within-cohort gene rankings or alter the relative expression relationships that define the biology of a cohort. This is distinct from the standard batch-correction objective (minimize inter-batch variance) and is not measured by the PCA R² metric used in our benchmark.

A complementary evaluation of our existing benchmark methods using an IOU-style check — whether within-cohort DE relationships are preserved after normalization — would be a valid additional diagnostic. This could be computed for the top-performing methods (FSQN, QN, ComBat, limma) on a held-out cohort without invoking CSN at all.

This analysis does not require adding CSN to the benchmark but would strengthen the characterization of FSQN's biological validity.

---

## Verdict

**CSN is not applicable to this project and should not be added to the benchmark.**

The primary blocker is structural: CSN was designed for cross-species normalization where the key challenge is distinguishing inter-species biology from technical noise. Our dataset is single-species with cross-platform technical effects that CSN's IOU term would actively resist correcting.

Secondary blockers are independently fatal:
- No code is available for use without full reimplementation
- Only validated on RNA-seq, not microarray+RNA-seq mixtures
- Validated at ~200 samples across 4 datasets; our scale is 5,444 × 88 cohorts
- CMA-ES optimisation with DEG computation at each step would be computationally prohibitive

The three methods CSN was evaluated against (EB/ComBat `05_combat`, DWD `27_dwd`, XPN `26_xpn`) are already in the benchmark or planned. The paper's comparison results can be used as external evidence for those methods' relative behaviour, particularly the finding that XPN aggressively removes broad-spectrum effects at the cost of within-dataset biological signal — directly relevant to interpreting XPN's PCA R² score in our results.

**FSQN (R) remains the benchmark winner.** The IOU preservation concept from CSN is worth borrowing as a diagnostic metric for existing benchmark outputs, but CSN itself offers no path to integration.
