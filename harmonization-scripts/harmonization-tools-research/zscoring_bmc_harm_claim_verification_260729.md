# Do Z-scoring, Z-scaling and BMC "actively harm signal"? — Literature verification

**Date:** 2026-07-29
**Author:** Claude Code review, requested by Daniil Nikitin
**Scope:** Verification of the exclusion rationale for three methods in
`harmonization_method_acceptance_rejection_tree.md`, section **3f — "Reported to actively
harm signal (3)"**: Z-scoring (standalone), Z-scaled (per-batch), BMC (Batch Mean-Centering).

---

## 1. Executive summary

**The claim is not true as written.** For BMC it is contradicted by the primary literature;
for Z-scaled it is unsupported; for standalone Z-scoring it is an overstatement of a real
but different finding (instability, not signal destruction).

| Method | Claim in section 3f | Verdict | Basis |
|---|---|---|---|
| **BMC** (batch mean-centering) | "Reported to actively harm signal" | **False — contradicted** | Luo 2010 (79% of 120 cases better-or-equivalent to no correction); Sims 2008 (mean-centering *recovers* subtype biology); Chen 2011 (2nd best of 6 methods) |
| **Z-scaled** (per-batch z-score) | "Reported to actively harm signal" | **Unsupported** — no such report exists | Luo 2010 tests exactly this as "standardization": 75% better-or-equivalent, "generally advisable". Yu 2024 makes no performance claim |
| **Z-scoring** (standalone, global) | "Reported to actively harm signal" | **Overstated** | Foltz 2023 reports *most variable performance* (estimation instability), not signal destruction. Its QN-Z variant *performed well* |

Two separate problems were found:

1. **A citation-provenance error.** The phrase "*Reported* to actively harm signal" attributes
   the judgment to the literature. In fact it originates in this project's own internal
   assessment notes (`harmonization-tools-research/Yu_2024_methods_review_260506.md`), which
   correctly flag that no PMID exists for BMC or Z-scaled. Neither cited source (Foltz 2023,
   Yu 2024) reports harm. Yu 2024 is a narrative review and taxonomy — it tabulates BMC and
   Z-scaled among "representative BECAs" and never benchmarks them.

2. **An internal inconsistency.** The stated reason for rejection — over-correction of biology
   under unbalanced batch composition — applies *more* strongly to ComBat, limma and SVA, all
   of which are retained in the registry. Chen 2011 shows why: ComBat is arithmetically
   mean-centering **plus** variance scaling, i.e. a strict superset of BMC. Any biology BMC
   removes, ComBat removes at least as much.

3. **This project's own data contradicts the claim.** `02_median_scaling` — per-batch median
   centering, a robust BMC variant — is already in the 3,835-attempt metrics table and performs
   *well* on both axes (Section 5). It has the **best batch silhouette of any method examined**
   while *improving* diagnosis separation relative to raw.

**Recommended action:** reclassify these three, and (cheaply) run BMC and Z-scaled to convert a
contestable a priori exclusion into an empirical result. See Section 7.

---

## 2. Where the claim came from

Traced through the repository:

| File | Line | Text |
|---|---|---|
| `harmonization_method_acceptance_rejection_tree.md` | 142 | `### 3f. Reported to actively harm signal (3)` |
| same | 146 | Z-scoring (standalone) → cites Foltz et al. 2023 |
| same | 147–148 | BMC, Z-scaled → cite Yu et al. 2024; "no PMID recorded… described as standard practice" |
| `harmonization-tools-research/Yu_2024_methods_review_260506.md` | 401 | "Zero-centering is **actively harmful** for downstream absolute-scale analyses" |
| same | 467 | "Very low priority, **potentially harmful**" (Z-scaled) |
| `harmonization-tools-research/Foltz_2023_methods_review_260506.md` | 131 | "Would remove biologically relevant scale differences between cohorts" |

The wording in the two review notes is *project-internal reasoning*, argued a priori from the
method definitions and this dataset's properties. It was then promoted into a category heading
that reads as an external literature report. The notes themselves are honest about the absence
of a citation ("no PMID"); the acceptance tree lost that qualification.

---

## 3. What the literature actually reports

### 3.1 Luo et al. 2010 — the decisive counter-evidence

*A comparison of batch effect removal methods for enhancement of prediction performance using
MAQC-II microarray gene expression data.* **Pharmacogenomics J** 10(4):278–291.
PMID [20676067](https://pubmed.ncbi.nlm.nih.gov/20676067/) ·
[full text](https://www.nature.com/articles/tpj201057)

The largest dedicated cross-batch prediction benchmark of its era: 120 cases, three microarray
platforms, SVM + KNN classifiers, MCC as the metric, plus cross-tissue and cross-platform
datasets. Verbatim from the abstract:

> "…we find that Ratio-G, Ratio-A, EJLR, **mean-centering** and **standardization** methods
> perform better or equivalent to no batch effect removal in 89, 85, 83, **79** and **75%** of
> the cases, respectively, suggesting that **the application of these methods is generally
> advisable** and ratio-based methods are preferred."

Mapping to the three methods under review:

- "**mean-centering**" **is** BMC → 79% better-or-equivalent.
- "**standardization**" **is** per-batch z-scoring → 75% better-or-equivalent, i.e. **Z-scaled**.

Both are explicitly declared "generally advisable." From the Results (Meta-analysis section):
"for each batch effect removal method, the number of cases with increased predictive performance
is greater than that with decreased predictive performance." This is the opposite of the
section-3f claim, from the single most relevant benchmark, on the exact two operations.

The honest reading of Luo 2010 is that BMC and Z-scaled are **mid-tier but net-positive** —
ranked 4th and 5th of five, behind ratio-based methods that this project cannot use (they
require concurrently profiled reference material; see Yu 2024's own caveat that ratio methods
are "not applicable when combining already-existing datasets").

### 3.2 Sims et al. 2008 — mean-centering *recovers* subtype biology

*The removal of multiplicative, systematic bias allows integration of breast cancer gene
expression datasets – improving meta-analysis and prediction of prognosis.*
**BMC Med Genomics** 1:42. [DOI](https://doi.org/10.1186/1755-8794-1-42)

Directly relevant because it is a retrospective multi-cohort integration, like ours:

- Batch mean-centering "was found to **dramatically increase** the correspondence comparison
  *across* the datasets, with 100% of probesets having fold changes within two-fold."
- SAM-derived significant-probeset overlap between datasets increased after mean-centering.
- "Combining two published studies **without** mean-centering clearly demonstrated how
  dataset-specific biases can **mask the biological differences** between breast cancer tumour
  subtypes."
- "mean-centering appears to reconcile the data and leads to the identification of
  **biologically plausible relationships not found when combining uncorrected data**."
- Median-centering "also performed similarly (data not shown)" — which is the project's
  `02_median_scaling`.

So in the closest published analogue to our design, mean-centering *unmasked* subtype biology
rather than harming it.

### 3.3 Chen et al. 2011 — BMC ranks 2nd of 6

*Removing batch effects in analysis of expression microarray data: an evaluation of six batch
adjustment methods.* **PLoS ONE** 6(2):e17238.
[DOI](https://doi.org/10.1371/journal.pone.0017238)

The method labelled **PAMR** in this paper "sets the mean of each probe set within a given batch
to zero" — that is BMC exactly, including the zero-centering the internal note objects to.
Findings:

- "It **did very well** in our measures of accuracy because of this simple transformation."
- "**PAMR was a close second** [to ComBat], but its performance suffered when batch size was
  small; only ComBat performed robustly when adjusting small batches."
- Mechanism for ComBat's win: "ComBat … is basically a mixture of a mean-centering algorithm
  like PAMR, and a scale-based algorithm similar to Ratio_G. This dual approach probably
  explains ComBat's superior overall performance."
- Genuine limitation: "PAMR does treat all samples equally, so it can **over- or under-correct
  particular samples**."

This yields the correct characterisation: BMC is **incomplete** (additive-only) and **unstable
in small batches** — not harmful. And it establishes BMC ⊂ ComBat, which is why rejecting BMC
for over-correction while retaining ComBat does not hold together.

### 3.4 Foltz et al. 2023 — the actual finding for standalone Z

*Cross-platform normalization enables machine learning model training on microarray and RNA-seq
data simultaneously.* **Commun Biol** 6:222.
[DOI](https://doi.org/10.1038/s42003-023-04588-6)

This is the paper cited in section 3f for "Z-scoring (standalone)." Verbatim:

> "Log-transformation demonstrated among the worst performance. This is expected as we consider
> this method to be a negative control… We also saw that **z-scoring data resulted in the most
> variable performance**. This is not unexpected because the calculation of the standard
> deviation and mean will be **highly dependent on which samples are selected** from each
> platform and the random selection of RNA-seq samples to be included in the training set does
> not consider subtype distribution, **which may not be known in practice**. We found that NPN,
> QN, **QN-Z**, and TDM **all performed well** when moderate… amounts of RNA-seq data were
> incorporated."

Three points follow:

1. The finding is **estimation instability**, not signal destruction. High variance across
   repeats ≠ active harm. LOG, not Z, was singled out as "among the worst."
2. **QN-Z performed well.** Z-scoring applied after quantile normalization was in the
   good-performer group. This flatly contradicts a blanket "z-scoring harms signal."
3. The stated mechanism — mean/SD estimates depend on the unknown subtype composition of the
   selected samples — is *the same composition-confound argument* the internal note makes. So
   Foltz 2023 supports the project's *mechanism* while not supporting its *conclusion*. That
   distinction is worth preserving in the manuscript, because the mechanism is citable and the
   conclusion is not.

### 3.5 Yu et al. 2024 — cannot support the claim at all

*Assessing and mitigating batch effects in large-scale omics studies.* **Genome Biol** 25:254.
[DOI](https://doi.org/10.1186/s13059-024-03401-9)

A narrative review that catalogues batch-effect correction algorithms (BECAs) by category
(location-scale, matrix factorization, deep learning) and tabulates them in Additional File 1,
"Detailed descriptions of representative BECAs." It runs **no head-to-head benchmark** of BMC
or Z-scaled and issues no performance verdict on either. Both appear without a PMID because
they are textbook operations, not published methods.

Citing Yu 2024 as the source for "reported to actively harm signal" misrepresents it. Yu 2024
*can* legitimately be cited for: (a) the taxonomy placing BMC/Z-scaled as location-scale
methods; (b) the caveat that ratio-based methods, though best-performing, are "not applicable
when combining already-existing datasets" — which is a useful justification for why this project
cannot simply adopt the Luo 2010 winners.

### 3.6 The valid over-correction literature — and why it cuts the other way

The canonical over-correction reference is **Nygaard, Rødland & Hovig 2016**, *Methods that
remove batch effects while retaining group differences may lead to exaggerated confidence in
downstream analyses*, **Biostatistics** 17(1):29–39,
PMID [26272994](https://pubmed.ncbi.nlm.nih.gov/26272994/) ·
[DOI](https://doi.org/10.1093/biostatistics/kxv027).

Its argument: when the batch–group design is unbalanced, batch differences are partly driven by
group differences, so batch correction shrinks group differences and inflates apparent
significance. This is real, and it applies squarely to our unbalanced DLBCL/FL/normal
composition across `RNA_BATCH`.

But note what it targets: **ComBat and limma-style two-step correction** — methods that estimate
and subtract batch means, optionally while protecting a group covariate. It is not a BMC-specific
or Z-specific critique. Using it to reject BMC and Z-scaled while retaining `03_limma`,
`04_sva`, `05_combat`, `07_pycombat` is not a defensible asymmetry.

> **Verification note:** Nygaard 2016 could not be retrieved in full during this review
> (Oxford Academic returned HTTP 403; PMC and PubMed served CAPTCHA challenges). The
> characterisation above rests on the title, abstract and widely-quoted core argument, plus
> secondary citation in Chen 2011 and the drug-response study below. **Read the primary text
> before citing it in the manuscript.** Likewise Lazar et al. 2013 (*Brief Bioinform*
> 14(4):469–490, [DOI](https://doi.org/10.1093/bib/bbs037)) could not be fetched (HTTP 403)
> and is listed here only as a pointer.

### 3.7 The strongest *legitimate* criticism of mean/scale centering

Not that it harms signal, but that it is **insufficient at second order**. Location-scale
correction guarantees conditional independence of each gene's *mean and variance* from batch,
but leaves batch structure in the **covariance**:

*Higher-order correction of persistent batch effects in correlation networks* (COBRA), bioRxiv
2023.12.28.573533. [Preprint](https://doi.org/10.1101/2023.12.28.573533)

> "…these methods do not address the potential for spurious differential co-expression (DC)
> between groups. Consequently, uncorrected, artifactual DC can skew the correlation structure,
> leading network inference methods that use gene co-expression to identify false, nonbiological
> associations, **even when the input data is corrected using standard batch correction**."

This is directly relevant to our downstream use: oposSOM metagenes are built from co-expression
structure, and the project has already observed that the **batch test fails in SOM metagene space
even after FSQN** (root `CLAUDE.md`). That observation is exactly what this literature predicts,
and it is a much better-supported argument than "BMC harms signal" — but it indicts *all*
location-scale methods in the registry equally, including ComBat, limma and median scaling.

---

## 4. A technical correction: "Z-scoring" and "Z-scaled" are not one thing

Section 3f lumps two mathematically different operations. This matters because the objection
raised applies to only one of them.

**Global (batch-blind) per-gene z-scoring** — what Foltz 2023 calls Z, and what section 3f calls
"Z-scoring (standalone)":

$$z_{ig} = \frac{x_{ig} - \mu_g}{\sigma_g}, \qquad \mu_g, \sigma_g \text{ computed over \emph{all} samples}$$

For any two samples $i, j$: $z_{ig} - z_{jg} = (x_{ig} - x_{jg})/\sigma_g$. Every pairwise
difference is preserved up to a positive per-gene constant, and every per-gene sample ordering
is preserved exactly. Consequences:

- It **cannot over-correct biology**, because it is batch-unaware — it has no batch term to
  subtract.
- It **removes no batch effect either**, for the same reason. It is a gene-weighting choice, not
  a batch correction.
- Its only real effect on downstream analysis is to equalise gene variances, which reweights
  genes in distance- and PCA-based methods.

So the internal note's statement that global z-scoring "would destroy the biological mean
differences between platforms" is not correct — those differences survive intact, rescaled. The
genuine objections to global z-scoring are (i) it is not a batch-correction method at all, and
(ii) Foltz 2023's instability finding.

**Per-batch z-scaling** — Yu 2024's "Z-scaled", Luo 2010's "standardization":

$$z_{ig} = \frac{x_{ig} - \mu_{g,b(i)}}{\sigma_{g,b(i)}}$$

This *is* a batch correction: BMC plus per-batch variance equalisation. Here the
over-correction concern is legitimate in principle — forcing unit within-batch variance removes
genuine biological variance wherever batch composition is unbalanced. But Luo 2010 tested it
empirically and found it net-positive in 75% of 120 cases.

**Recommendation:** split these into two rows with separate rationales. Merging them produces an
argument that is wrong for one and unsupported for the other.

---

## 5. This project's own data already tests the claim

`02_median_scaling` in `bench_shared.py:624` is *per-batch median centering, shifting each batch
median to the global median* — a robust BMC variant. It differs from textbook BMC in exactly the
two ways that answer the internal note's objections: it uses a robust location statistic, and it
centers to the global median rather than to zero, so absolute expression scale is preserved.

It is in the benchmark with full metrics. From `metrics_comprehensive_260609.csv`
(3,835 attempts, all `status == ok`), averaged over all strategies × imputations × post_rm:

| method | n | `asw_bio_Diagnosis` ↑ | `asw_bio_norm_Diagnosis` ↑ | `asw_batch_RNA_BATCH` ↓ | `per_gene_batch_mean_cv` ↓ |
|---|---|---|---|---|---|
| `01_raw` | 84 | −0.186 | 0.407 | 0.119 | 0.528 |
| **`02_median_scaling`** | 84 | **−0.140** | **0.430** | **−0.286** | **0.112** |
| `03_limma` | 84 | −0.138 | 0.431 | −0.229 | 0.000 |
| `04_sva` | 80 | −0.133 | 0.434 | 0.076 | 0.477 |
| `05_combat` | 80 | 0.008 | 0.504 | −0.114 | 0.300 |
| `10_mnn` | 84 | −0.100 | 0.450 | −0.106 | 0.000 |
| `16_fsqn_r` | 84 | −0.078 | 0.461 | −0.047 | 0.349 |
| `17_quantile` | 84 | −0.017 | 0.491 | 0.147 | 0.256 |

Reading (higher `asw_bio` = better biology separation; lower `asw_batch` = better batch mixing):

- Median scaling **improves** diagnosis separation over raw (−0.186 → −0.140). It does not
  destroy biological signal.
- It achieves the **lowest (best) batch silhouette of all eight methods** — better than limma,
  ComBat, MNN, FSQN and SVA.
- Its per-gene batch-mean CV (0.112) is third-best, far ahead of ComBat (0.300), FSQN (0.349)
  and SVA (0.477).
- It is mid-tier on biology preservation — comparable to limma (−0.138), below ComBat (0.008) and
  quantile (−0.017). Consistent with Luo 2010 and Chen 2011: **solid, not best, not harmful.**

Caveat: median-centering is a proxy, not BMC itself. It does not test the specific
"zero-centering destroys absolute scale" objection, because it avoids zero-centering by design.
But it does test the core operation — a per-batch additive location shift — and finds it benign.

---

## 6. Direct answer: are the conclusions true?

**No, not as stated.** Point by point:

| Sub-claim | True? | Correct statement |
|---|---|---|
| BMC actively harms signal | **No** | BMC is net-positive in 79% of 120 MAQC-II cases (Luo 2010), 2nd of 6 in Chen 2011, and *recovers* masked subtype biology in Sims 2008. Its real limitations: additive-only, unstable in small batches, leaves covariance structure uncorrected |
| Z-scaled actively harms signal | **No report exists** | Luo 2010 tests it as "standardization": net-positive in 75% of cases, "generally advisable." The over-correction concern is theoretically sound but untested here and applies equally to retained methods |
| Z-scoring (standalone) actively harms signal | **Overstated** | Foltz 2023 reports the *most variable* performance, attributed to sample-selection-dependent mean/SD estimates. QN-Z performed well. LOG, not Z, was the worst performer |
| The literature reports these harms | **No** | The wording originates in this project's own a priori notes. Yu 2024 does not benchmark BMC or Z-scaled; Foltz 2023 reports instability, not harm |
| Zero-centering breaks absolute-scale downstream analysis (ssGSEA, SOM) | **Yes, but** | Valid *project-specific* engineering constraint, correctly reasoned. Not a literature finding, and it argues for using median-centering (which the project already does) rather than for excluding the method class |
| These methods over-correct biology under unbalanced batch composition | **Plausible, unproven, and non-selective** | Nygaard 2016 supports the mechanism, but targets ComBat/limma — all retained. Cannot justify excluding BMC while keeping ComBat, which per Chen 2011 is BMC + variance scaling |

The underlying *decision* — not spending benchmark slots on BMC and Z-scaled — remains
defensible on redundancy grounds. The **stated justification** is what fails.

---

## 7. Recommendations

### 7.1 Minimum fix — reclassify (required before NAR submission)

Delete section 3f. Redistribute:

- **BMC** → §3d "Redundant with / inferior to / superseded by an adopted method." Rationale:
  functionally subsumed by `02_median_scaling` (robust variant, retained) and by `05_combat`
  (BMC + variance scaling; Chen 2011). Cite Luo 2010 and Chen 2011 accurately — as reporting
  BMC to be *net-positive but incomplete*, correcting additive effects only while the dominant
  problem in this dataset is multiplicative/platform scale.
- **Z-scaled** → §3d, same reasoning: it is BMC + per-batch variance equalisation, and
  `05_combat` implements the same two-moment correction with empirical-Bayes shrinkage that
  stabilises small batches.
- **Z-scoring (standalone)** → a new, honest category: *"Preprocessing step, not a
  batch-correction method."* It is batch-unaware and removes no batch effect (Section 4). Cite
  Foltz 2023 for the instability finding.

**Why this matters for NAR.** A benchmark paper's exclusion table is exactly what a
methods-oriented reviewer audits. Section 3f currently attributes a strong negative claim to two
papers that do not make it, about two operations that the largest relevant benchmark calls
"generally advisable." A reviewer who opens Luo 2010 will find the abstract contradicting the
table. The reclassified version is both accurate and easier to defend.

### 7.2 Better fix — run them (recommended)

BMC and per-batch Z-scaled are a handful of lines each, and the two-stage pipeline makes the
marginal cost near zero (prepared pairs already exist on S3; only Stage 2 needs to run):

```python
def normalize_bmc(exp_df, ann_df, batch_col=BATCH_COL, **kw):
    """Batch mean-centering: set each gene's within-batch mean to zero."""
    groups = ann_df.loc[exp_df.index, batch_col].fillna("Unknown")
    return exp_df.groupby(groups).transform(lambda block: block - block.mean())


def normalize_zscaled(exp_df, ann_df, batch_col=BATCH_COL, **kw):
    """Per-batch z-scaling: zero mean, unit variance per gene within each batch."""
    groups = ann_df.loc[exp_df.index, batch_col].fillna("Unknown")
    return exp_df.groupby(groups).transform(
        lambda block: (block - block.mean()) / block.std(ddof=0).replace(0, np.nan)
    ).fillna(0.0)
```

Registry keys `40_bmc` and `41_zscaled`; add to `ALL_METHODS` in **both**
`run_norm_parallel.py` and `run_cross_product_parallel.py` per `CLAUDE.md`.

Three reasons this is worth doing:

1. **It removes the citation liability entirely.** "Excluded because our own benchmark showed X"
   needs no external support and cannot be contradicted by a reviewer's reading of Luo 2010.

2. **It is a direct test of the paper's own central claim.** The manuscript already argues that
   *global metrics are necessary but not sufficient* — SVA is cited as achieving top local mixing
   without strong global correction. Per-batch Z-scaled is the ideal worked demonstration of the
   converse failure mode: it sets per-batch per-gene mean to 0 and variance to 1 **by
   construction**, so PCA R²-by-batch and per-gene batch-mean CV must collapse to ~0 whatever
   happens to the biology. If the 87-metric battery then shows biology preservation collapsing
   alongside, that is a clean, quantitative, single-panel argument that global batch metrics are
   gameable. This is a genuinely useful figure, not a defensive addition.

3. **It closes an inconsistency.** Two methods excluded on a stated over-correction ground would
   be measured on the same footing as ComBat, limma and SVA, which are retained despite the same
   theoretical exposure.

The prediction to test — worth stating in advance, so the result is a real test rather than a
post-hoc narrative: **Z-scaled will look excellent on global batch metrics and poor on local
biology metrics; BMC will land near `02_median_scaling`.** If BMC instead lands near
`02_median_scaling` on both axes, as Section 5 suggests, that is a publishable negative result:
one of the simplest possible corrections is competitive on batch removal in a 5,444-sample
multi-platform assembly.

### 7.3 Sources to read before citing

| Source | Status | Action |
|---|---|---|
| Luo et al. 2010 | Abstract + Results verified | Safe to cite |
| Sims et al. 2008 | Full text verified | Safe to cite |
| Chen et al. 2011 | Full text verified | Safe to cite |
| Foltz et al. 2023 | Full text verified | Safe to cite — quote the "most variable performance" wording precisely |
| Yu et al. 2024 | Full text verified; Additional File 1 (XLSX) not opened | Do **not** cite for performance claims. Open the supplementary table to confirm the BMC/Z-scaled entries before citing even descriptively |
| Nygaard et al. 2016 | **Not retrieved** (403 / CAPTCHA) | Read primary text before citing |
| Lazar et al. 2013 | **Not retrieved** (403) | Read before citing |
| COBRA preprint 2023 | Abstract + Introduction verified | Check for peer-reviewed version before citing |

---

## 8. References

1. **Luo J, Schumacher M, Scherer A, et al.** A comparison of batch effect removal methods for
   enhancement of prediction performance using MAQC-II microarray gene expression data.
   *Pharmacogenomics J.* 2010;10(4):278–291. PMID
   [20676067](https://pubmed.ncbi.nlm.nih.gov/20676067/) ·
   [nature.com/articles/tpj201057](https://www.nature.com/articles/tpj201057)

2. **Sims AH, Smethurst GJ, Hey Y, et al.** The removal of multiplicative, systematic bias allows
   integration of breast cancer gene expression datasets – improving meta-analysis and prediction
   of prognosis. *BMC Med Genomics.* 2008;1:42.
   [doi:10.1186/1755-8794-1-42](https://doi.org/10.1186/1755-8794-1-42)

3. **Chen C, Grennan K, Badner J, et al.** Removing batch effects in analysis of expression
   microarray data: an evaluation of six batch adjustment methods. *PLoS ONE.* 2011;6(2):e17238.
   [doi:10.1371/journal.pone.0017238](https://doi.org/10.1371/journal.pone.0017238)

4. **Foltz JN, Greene CS, Taroni JN.** Cross-platform normalization enables machine learning
   model training on microarray and RNA-seq data simultaneously. *Commun Biol.* 2023;6:222.
   [doi:10.1038/s42003-023-04588-6](https://doi.org/10.1038/s42003-023-04588-6)

5. **Yu Y, Mai Y, Zheng Y, Shi L.** Assessing and mitigating batch effects in large-scale omics
   studies. *Genome Biol.* 2024;25:254.
   [doi:10.1186/s13059-024-03401-9](https://doi.org/10.1186/s13059-024-03401-9)

6. **Nygaard V, Rødland EA, Hovig E.** Methods that remove batch effects while retaining group
   differences may lead to exaggerated confidence in downstream analyses. *Biostatistics.*
   2016;17(1):29–39. PMID [26272994](https://pubmed.ncbi.nlm.nih.gov/26272994/) ·
   [doi:10.1093/biostatistics/kxv027](https://doi.org/10.1093/biostatistics/kxv027)
   *(not directly verified — see §7.3)*

7. **Lazar C, Meganck S, Taminau J, et al.** Batch effect removal methods for microarray gene
   expression data integration: a survey. *Brief Bioinform.* 2016;14(4):469–490.
   [doi:10.1093/bib/bbs037](https://doi.org/10.1093/bib/bbs037)
   *(not directly verified — see §7.3)*

8. **Johnson WE, Li C, Rabinovic A.** Adjusting batch effects in microarray expression data using
   empirical Bayes methods. *Biostatistics.* 2007;8(1):118–127. PMID
   [16632515](https://pubmed.ncbi.nlm.nih.gov/16632515/) — cited for the ComBat = mean-centering +
   scaling decomposition established in ref. 3.

9. **Higher-order correction of persistent batch effects in correlation networks** (COBRA).
   *bioRxiv* 2023.12.28.573533.
   [doi:10.1101/2023.12.28.573533](https://doi.org/10.1101/2023.12.28.573533)

10. **Nygaard V, et al. / drug-response batch correction context:** Influence of batch effect
    correction methods on drug induced differential gene expression profiles.
    *BMC Bioinformatics.* 2019;20:437.
    [doi:10.1186/s12859-019-3028-6](https://doi.org/10.1186/s12859-019-3028-6)

---

## 9. Files to update if recommendations are accepted

| File | Change |
|---|---|
| `harmonization_method_acceptance_rejection_tree.md` | Delete §3f; move BMC + Z-scaled to §3d; new category for standalone Z-scoring; update the Stage-1 counts in the ASCII tree at lines 21–25 (currently "(3) Reported to actively harm signal") |
| `methods_table_for_manuscript.md` | Same reclassification; correct any inherited "actively harm" wording |
| `harmonization-tools-research/Yu_2024_methods_review_260506.md` | Add a note at lines 401 and 467 marking those verdicts as project-internal a priori reasoning, and cross-reference Luo 2010 as counter-evidence |
| `harmonization-tools-research/Foltz_2023_methods_review_260506.md` | Correct line 129: global z-scoring preserves pairwise differences up to a per-gene scale factor (§4) |
| `bench_shared.py`, `run_norm_parallel.py`, `run_cross_product_parallel.py` | Only if §7.2 is adopted: add `40_bmc`, `41_zscaled` |
