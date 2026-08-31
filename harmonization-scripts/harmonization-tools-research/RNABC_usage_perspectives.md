# RNABC — Usage Perspectives for Multi-Platform Bulk RNA Harmonization

**Full name:** "Using microarray-based subtyping methods for breast cancer in the era of high-throughput RNA sequencing"  
**Authors:** Pedersen CB, Nielsen FC, Rossing M, Olsen LR  
**Reference:** *Molecular Oncology* 12(12), 2136–2146 (2018). https://doi.org/10.1002/1878-0261.12389  
**Code:** https://bitbucket.org/cbligaard/rnabc/ (R pipeline)

**Context:** Evaluation of RNABC as a harmonization candidate for ~5,444 samples across 88 cohorts from mixed platforms (Affymetrix GPL570, Illumina NGS, Illumina microarray, Agilent microarray). Reference batch: RNASeq_FF_PolyA (n=1,039). Current benchmark winner: FSQN (R) at ~16% PCA variance explained by batch (down from ~95% raw).

---

## What RNABC Actually Does — Core Concept

RNABC is **not a general-purpose batch correction method**. It is a three-step pipeline designed to enable application of a specific breast cancer classifier (CITBCMST) to RNA-seq data that was originally trained on Affymetrix HG-U133 Plus 2.0 microarray intensities.

The core innovation is in Step 1: instead of aligning RNA-seq reads to the human reference genome (producing FPKM/TPM at gene level), reads are pseudoaligned directly to the **Affymetrix probe set target sequences** using kallisto. This produces one TPM value per probe set — a measurement coordinate space directly comparable to microarray probe intensities. Steps 2 and 3 then bring the distributions into alignment with the classifier's training data.

---

## Algorithm — Step by Step

### Step 1: Pseudoalign RNA-seq reads to probe sequences (kallisto)

- Tool: kallisto (k-mer pseudoalignment)
- Reference: Affymetrix HG-U133 Plus 2.0 probe set target sequences (not hg19)
- Input: Raw FASTQ files
- Output: TPM per probe set

This step requires raw sequencing reads. It is fundamentally incompatible with pre-processed gene-level expression matrices from public repositories.

### Step 2: Quantile normalization to the training data distribution

- Tool: `normalize.quantiles.target` from R `preprocessCore` package
- Target: mean probe intensities across 355 CITBCMST training samples (Affymetrix HG-U133 Plus 2.0)
- Aligns the global TPM distribution to the reference microarray distribution

### Step 3: ComBat batch correction against the training dataset

- Tool: ComBat (`sva` R package), same as `05_combat` in the benchmark
- Corrects remaining systematic differences between platforms
- Test data and training data are corrected jointly

### Step 4: Apply CITBCMST classifier

- Distance-to-centroid classifier (diagonal LDA) on the 375-probe signature
- Assigns one of six breast cancer subtypes
- This step is the end goal — harmonization exists to serve this classifier

---

## Input Data Requirements

| Requirement | Details |
|---|---|
| Raw FASTQ files | Mandatory for Step 1 (kallisto pseudoalignment) |
| Affymetrix HG-U133 Plus 2.0 probe sequences | Provided in the Bitbucket repository |
| CITBCMST training dataset | 355 CEL files (E-MTAB-365); used as normalization target and ComBat reference |
| Disease | Breast cancer (pipeline is classifier-specific) |
| Reference platform | Affymetrix HG-U133 Plus 2.0 only |

---

## Validation

| Dataset | Samples | Platforms | Matched? |
|---|---|---|---|
| Bordet (Fumagalli et al. 2014) | 57 breast tumors | Affymetrix HG-U133+ 2.0 + Illumina HiSeq 2000 | Yes (same tissue) |
| RH (Rigshospitalet) | 9 breast tumors | Affymetrix HG-U133+ 2.0 + NextSeq 500 | Yes (same tissue) |

**Performance (Bordet, N=57):**

| Method | Spearman ρ (probe-level) | Subtype matches |
|---|---|---|
| RNABC | 0.9638 | 51/57 (89%) |
| Fumagalli (direct FPKM) | 0.8191 | — |
| TDM | 0.8206 | — |
| PREBS | 0.7306 | — |

**Ablation study — all three steps are necessary:**

| Configuration | Spearman ρ | Subtype matches |
|---|---|---|
| Probe mapping only | 0.6982 | 0/57 |
| Probe mapping + quantile norm | — | 5/57 |
| Probe mapping + ComBat only | 0.8796 | 0/57 |
| Full RNABC | 0.9638 | 51/57 |

---

## Assessment for This Project

### Structural blockers — why RNABC cannot be applied

**1. Requires raw FASTQ files — unavailable for this dataset.**  
The entire pipeline depends on Step 1: pseudoaligning raw sequencing reads against Affymetrix probe sequences. The ~2,386 RNA-seq samples in the FL dataset come from retrospective public repositories (GEO, ArrayExpress, an internal cohort database) where processed matrices (TPM, RPKM, or counts at gene level) are provided. Raw FASTQ files are either not deposited or not accessible for most cohorts. Without FASTQ input, the pipeline cannot run.

**2. Probe-level coordinate space is Affymetrix HG-U133 Plus 2.0 only.**  
RNABC's Step 1 produces expression estimates in the probe-set coordinate space of a single chip (GPL570 = HG-U133 Plus 2.0). This resolves the RNA-seq vs. microarray incompatibility for that one platform. The FL dataset additionally contains Illumina microarray (GPL14951) and Agilent microarray (GPL4133 equivalent) batches — these would remain unaddressed, since they use entirely different probe geometries. A four-platform dataset cannot be mapped onto a single probe coordinate space.

**3. Breast cancer classifier — not transferable to lymphoma biology.**  
RNABC exists to enable a specific classifier (CITBCMST) on a specific disease (breast cancer, 6 subtypes). Its normalization target (355 CITBCMST training samples), its ComBat reference (the same training data), and its gene set (375 probe signature) are all breast cancer–specific. There is no lymphoma equivalent of CITBCMST. The normalization pipeline cannot be decoupled from the classifier without losing its purpose.

**4. The normalization components are already represented in the benchmark.**  
Steps 2 and 3 of RNABC — quantile normalization to a reference distribution, followed by ComBat — are precisely what `17_quantile` and `05_combat` do in the benchmark, and what `16_fsqn_r` (FSQN) does in a feature-specific variant. FSQN achieves ~16% batch R² using an analogous design (per-feature quantile transform to a reference batch) and is already the benchmark winner. RNABC offers no additional normalization concept not already tested.

---

## What RNABC Does That Is Genuinely Novel

The probe-level pseudoalignment idea (Step 1) is conceptually elegant: by mapping reads to probe sequences rather than the genome, RNA-seq data is placed in the same measurement coordinate space as microarray intensities at the probe level. This sidesteps the gene-summary inconsistency (probe-to-gene aggregation differs between platforms) and directly matches the input space the classifier was trained on.

This novelty is, however, **inapplicable to retrospective datasets** where raw reads are unavailable. It would only be relevant to a prospective study where new RNA-seq samples are generated with FASTQ files retained and where the goal is to apply a specific GPL570-trained classifier.

For the FL project, the gene-level intersection (3,520 HGNC symbols common across all platforms) already provides a more appropriate common coordinate space than Affymetrix probe-level data, because it covers all four platforms simultaneously.

---

## Comparison with Current Benchmark Methods

| Aspect | RNABC | FSQN (current best) | 05_combat |
|---|---|---|---|
| Core mechanism | Probe-level mapping + QN to reference + ComBat | Per-gene quantile replacement to reference | Empirical Bayes location/scale shift |
| Input required | Raw FASTQ files | Gene-level expression matrix | Gene-level expression matrix |
| Platforms supported | Affymetrix HG-U133 Plus 2.0 only | Any (reference-batch design) | Any |
| Disease scope | Breast cancer (CITBCMST-specific) | General | General |
| Reference batch required | Yes (CITBCMST training dataset) | Yes (RNASeq_FF_PolyA) | Optional |
| Multi-platform (>2) | No | Yes | Yes |
| Output format | Probe sets × samples matrix (for classifier) | Genes × samples matrix | Genes × samples matrix |
| Applicable to FL dataset | **No** | Yes | Yes |

---

## Verdict

**RNABC is not applicable to this project.**

Three structural blockers make it unusable:

1. **Raw FASTQ input required** — not available for retrospective public cohorts
2. **Single-platform coordinate space** — Step 1 is Affymetrix HG-U133 Plus 2.0 specific; the FL dataset spans four platforms
3. **Breast cancer classifier coupling** — the entire pipeline is built around CITBCMST; there is no lymphoma analogue

The normalization components (quantile normalization to reference + ComBat) are already represented by `17_quantile`, `05_combat`, and `16_fsqn_r` in the benchmark. FSQN outperforms both individual components and is already the selected primary normalization.

**FSQN (R) remains the benchmark winner.** RNABC provides no normalization concept not already tested, and its unique contribution (probe-level pseudoalignment) is inaccessible for retrospective data.
