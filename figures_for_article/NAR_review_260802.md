# Referee report — *Nucleic Acids Research*

**Manuscript.** "Benchmarking of bulk transcriptomic harmonization tools across a multi-platform
germinal center B-cell lymphoma cohort identifies mutual nearest neighbors and surrogate variable
analysis as top-performing methods"

**Files reviewed**

| File | What was checked |
|---|---|
| `FL_harmonization_article_NAR_260802_manually_edited.docx` | full text, tables, formatting, abstract length, citation storage |
| `current_figures_tables_for_article_260802/` (78 files) | 6 main + 17 supplementary + 13 extended figures (PDF + JPG), graphical abstract, 4 supplementary data files |
| `Harmonization_metrics_extended.docx` | language, internal consistency, every quoted number |
| `Supplementary File 3.csv.gz` (2,407 × 93) | primary reproducibility source — every recomputation below |
| `../harmonization-metrics/metric_tables/metrics_comprehensive_260609.csv` (3,835 × 237) | un-normalized / polarity-unadjusted metric values |
| `../harmonization-scripts/bench_shared.py` (2,717 lines) | per-method parameters, model matrices, harshness tiers |
| `../harmonization-metrics-calculation/compute_batch_metrics.py` | random seeds, UMAP/t-SNE parameters |

**Date.** 2026-08-02
**Tracked-changes outputs.** `FL_harmonization_article_NAR_260802.docx`,
`Harmonization_metrics_extended_260802.docx`
**Repackaged supplementary material.** `supplementary_260802/`

**Explicitly out of scope** (author's instruction): reference and bibliography formatting (Mendeley),
the author byline and affiliations, funding and data-availability text, and the italic
`{{…}}` placeholders that mark the author's own unfinished passages.

---

## §0 Summary assessment

This is the largest systematic bulk-transcriptomic harmonization benchmark I am aware of, and the
central design decision — evaluating the full cross-product of batch-removal strategy × imputation ×
algorithm × post-removal under *subtle* biological contrast rather than TCGA-scale contrast — is both
novel and correctly motivated. The FFPE-only result (SVA mixing FFPE Affymetrix, FFPE Illumina and
FFPE RNA-seq in one harmonized lymphoma dataset) is, as far as I can tell, genuinely new.

**The reproducibility of this revision is materially better than the previous one.** I recomputed the
paper's headline statistics from the deposited Supplementary File 3 and they now reproduce
*exactly*:

| Quantity | As reported | As recomputed | Verdict |
|---|---|---|---|
| Approaches passing the < 5 % all-NA filter | 2,234 of 2,407 | `pct_samples_allNA < 5` → **2,234** | ✅ exact |
| Methods surviving that filter | 31 (34_arsyn, 38_harman dropped) | **31**; arsyn/harman = 0 of 168 rows pass | ✅ exact |
| Mean R² (η²), harmonization method | 0.363 | **0.3629** | ✅ exact |
| Mean R² (η²), batch-removal strategy | 0.256 | **0.2564** | ✅ exact |
| Mean R² (η²), imputation | 0.016 | **0.0155** | ✅ exact |
| Mean R² (η²), post-removal | 0.002 | **0.0020** | ✅ exact |
| PCReg RNA_BATCH, S0 / 01_raw / strict / post0 | 0.226 | **0.226495** | ✅ exact |
| PCReg Diagnosis, same run | 0.923 | **0.922850** | ✅ exact |
| Approaches with all 87 metrics defined | 1,354 | **1,354** | ✅ value correct, denominator wrong (§2 M1) |
| Metric inventory | 87 scoring + 142 other = 229 | Supp. File 4: **51 (+1) + 36 (−1) = 87**, 142 zero, 229 rows | ✅ exact |
| Abstract length | ≤ 200 | **198** | ✅ |

Every one of the twelve critical findings of the 2026-07-27 pass that concerned *numbers* has been
resolved. What remains falls into four themes, in descending seriousness:

1. **Two deposited-data defects that break the link between the tables** (§1 C1, C2) — both are
   mechanical and I have fixed them in the repackaged supplementary set.
2. **One statement in Methods that the source code contradicts** (§1 C3) — the biological covariate
   was *not* supplied to limma or RUV. This matters because the paper's central claim is about
   preserving subtle biology.
3. **Figure legibility and supplementary-file limits still fail NAR's production rules** (§1 C4, C5),
   unchanged from the previous pass and not fixable from the manuscript.
4. **Descriptive precision** — a scatter of numbers in the Extended Metrics document that do not
   reproduce, plus the usual typographical layer (§3).

**Recommendation: minor-to-moderate revision.** The science is sound and now checkable; what is left
is production compliance and a handful of corrections, most of which are applied in the accompanying
tracked-changes files.

Issue counts: **5 critical, 13 major, 47 minor.**

---

## §1 Critical

### C1. Supplementary Files 3 and 4 name the same seven metrics differently

Supplementary File 4 (polarity) lists the principal-component-regression metrics as
`pcr_COHORT_LABEL`, `pcr_RNA_BATCH`, … Supplementary File 3 (values) names the identical columns
`PCReg_COHORT_LABEL`, `PCReg_RNA_BATCH`, …

```
scoring metrics (polarity ≠ 0) in Supp. File 4 : 87
   … of which found in Supp. File 3 by name    : 80
   … unmatched                                 :  7   (all pcr_*)
```

A reader who joins the two files — the only way to reproduce the composite score — silently loses
seven of the 87 scoring metrics, including PCReg, the metric the Results and the Extended document
treat as the canonical global measure. **Fixed** in `supplementary_260802/Supplementary File 2.xlsx`
(sheet `Metric_polarity`): after renaming, 87 of 87 resolve.

### C2. Supplementary File 2 does not match the dataset it describes

| | |
|---|---|
| Rows in Supplementary File 2 | 7,238 |
| Samples in Supplementary File 1 | 7,174 |
| Sample identifiers in File 2 absent from File 1 | **63** |
| Duplicated identifiers in File 2 | **1** |

The manuscript states a 7,174-sample dataset throughout. This is the same defect flagged on
2026-07-27 and it has not been corrected. **Fixed** in `supplementary_260802/Supplementary File 2.xlsx`
(sheet `Genes_per_sample`): deduplicated and restricted to the 7,174 annotated samples.

### C3. The stated model specification is contradicted by the code

Methods, "Harmonization methods":

> For SVA, limma removeBatchEffect, ComBat, ComBat-seq, M-ComBat and RUV we selected the annotation
> column 'Diagnosis_cell_type_unified' as the biology covariate to protect its variance in the gene
> expression space.

`bench_shared.py` supplies a biological covariate to four of those six:

| Method | Call in `bench_shared.py` | Biology covariate? |
|---|---|---|
| `04_sva` | `sva(dat, mod = model.matrix(~bio), mod0 = model.matrix(~1), n.sv = num.sv(dat, mod))` | **yes** |
| `05_combat` | `ComBat(dat, batch, mod = model.matrix(~bio))` | **yes** |
| `06_combat_seq` | `ComBat_seq(counts, batch, group = bio)` | **yes** |
| `29_combat_ref` | `ComBat(dat, batch, mod = model.matrix(~bio), ref.batch=…)` | **yes** |
| `03_limma` | `removeBatchEffect(mat, batch = batches)` — **no `design=` argument** | **no** |
| `09_ruv` | `RUVg(counts, cIdx = <10 housekeeping genes>, k = 2)` — no biology term at all | **no** |

This is not pedantry. limma's `removeBatchEffect` without `design` removes *all* between-batch
variation including any biology confounded with batch, and the paper's own conclusion is that limma
"failed to preserve local biology structure". Reporting that limma was protected when it was not
makes that failure look like a property of the algorithm rather than of the configuration.
**Corrected in the tracked-changes manuscript**, and a full per-method parameter column has been
added to Table 3 so the point is auditable.

### C4. Figures remain illegible at NAR print size

Measured after scaling each figure into NAR's 17.35 × 23.35 cm maximum print box:

| Figure | Drawn size (cm) | Scale forced | Median font (pt) | Text < 5 pt |
|---|---|---|---|---|
| Supplementary Figure 2 | 27.6 × 40.9 | 0.57 | **4.6** | **100 %** |
| Supplementary Figure 3 | 28.0 × 41.2 | 0.57 | **4.5** | **100 %** |
| Supplementary Figure 4 | 28.3 × 41.2 | 0.57 | **4.5** | **100 %** |
| Supplementary Figure 7 | 27.1 × 40.9 | 0.57 | **3.0** | **81 %** |
| Supplementary Figure 1 | 26.8 × 39.1 | 0.60 | **4.8** | **54 %** |
| Figure 2 | 27.2 × 41.1 | 0.57 | 5.7 | 27 % |
| Figure 3 | 26.8 × 39.6 | 0.59 | 5.9 | 27 % |
| Figure 4 | 26.6 × 40.6 | 0.58 | 5.8 | 14 % |

*Every* figure in the submission exceeds the print box and needs 0.56–0.66 scaling. All 37 PDFs use
**Type 3 fonts with zero embedded font files**, and all are **RGB, none CMYK**. The Type 3 issue also
explains why text extraction from the figures is corrupted, and it means screen readers cannot read
them — which contradicts the alt text the manuscript correctly supplies.

The remedy is not in the manuscript: the figure-generating notebooks must lay out to the final print
width (`figsize` in inches equal to 8.5 cm or 17.35 cm) with `GLOBAL_FONT_SIZE` ≥ 7 pt at that size,
save with `plt.rcParams["pdf.fonttype"] = 42` and an embedded Type 1/TrueType face, and convert to
CMYK at export.

### C5. Supplementary material still exceeds NAR's limits

NAR accepts **one combined PDF**, or otherwise at most **10 files of ≤ 2 MB each**. The submission
folder holds 78 files, 15 of them over 2 MB.

I have repackaged the material into `supplementary_260802/` (see §5 for the full accounting). Two
honest caveats:

- The 17 supplementary figures total **19.2 MB as vector PDFs after maximal recompression**
  (`garbage=4, deflate, deflate_images, deflate_fonts, clean` — this alone cut them from 33 MB).
  Seven bundles therefore average 2.75 MB; the smallest is 1.31 MB and the largest 3.89 MB.
  **The requested target of seven files under 1.5 MB each is not reachable without rasterizing**,
  because 10.5 MB of budget cannot hold 19.2 MB of vector artwork.
- I have therefore also produced the single combined file
  `Supplementary Figures S1-S17.pdf` (19.17 MB, 17 pages, each page labelled and bookmarked), which
  is NAR's *preferred* route and sidesteps the per-file cap entirely. I recommend submitting that one.

---

## §2 Major

### Reproducibility and specification

**M1. "1,354 of 2,407" uses the wrong denominator.** Results, "Relative impact…": the composite score
is defined only on the 2,234-approach analysis set, and all 1,354 complete approaches lie inside it.
Recomputed: 1,354 of 2,234 (60.6 %), not of 2,407. *Corrected.*

**M2. Figure 6B is described as a decomposition of the composite score, which it is not.** The text
says harmonization method explains "36.3 % of variance in composite harmonization quality". The
quantity plotted is the **mean of 87 per-metric η² values**, computed metric by metric and then
averaged — as the notebook code confirms and as my recomputation reproduces to four decimals. The
number is right; the sentence attributes it to the wrong response variable. *Corrected.*

**M3. Random seeds and embedding parameters were absent.** Fourteen of the 87 scoring metrics are
computed in stochastic embedding space and several conclusions rest on differences of 0.01–0.05.
From `compute_batch_metrics.py`: PCA, UMAP and t-SNE all use `random_state = 42`; UMAP uses
`n_neighbors = 30`, `min_dist = 0.3`, Euclidean metric, 2 components; t-SNE uses
`perplexity = min(30, n_samples // 4)`, Barnes–Hut. *These are now stated in Methods.* What is still
missing is any **replication** — run-to-run variability of the embedding metrics on even a subsample
would let the reader judge whether the reported differences exceed the noise. Recommended for the
revision; not fixable by editing.

**M4. Harshness assignment was unauditable.** The tier is a hard-coded string in the `METHODS`
registry of `bench_shared.py`, whose source is organised into three commented blocks (low / medium /
high harshness). *Table 3 now carries an explicit "Harshness justification" column giving the
transformation class for each method*, and Methods now states the criterion, who assigned it, and
that it was assigned before results were seen.

**M5. Table 3 gave no parameters.** *A "Parameters used" column has been added for all 39 methods*,
taken from the function signatures and call sites in `bench_shared.py` (reference batch
`RNASeq_FF_PolyA`, MNN `k = 20`, RUV `k = 2` on ten housekeeping genes, Harmony `n_pcs = 50`,
RUV-III-PRPS `k = 5`, Harman `limit = 0.1`, exploBATCH `maxdim = 9`, XPN `n_quantiles = 50`,
Angel `threshold = 0.20`, DWD `min_batch_size = 5`, and the design matrices in C3).

**M6. Table 4 gave author-year sources only.** *A "Full citation" column has been added*, populated
from the manuscript's own Mendeley bibliography so the two agree exactly.

**M7. The 13 Extended Figures are cited nowhere in the manuscript and NAR has no such category.**
They belong to the Extended Metrics document, which the author intends to deposit separately. The
manuscript needs one sentence saying so, otherwise a reviewer receiving the folder sees 13
uncited figures. *A sentence has been added to Data Availability.*

**M8. A five-entry stub reference list sits above the real bibliography.** Body children 289–293
contain "1. Yu … et al. [Full title]. [Journal abbrev.] 2024; [vol]: [pages]. [DOI]." and four
similar. The genuine 95-entry Mendeley bibliography follows immediately. Reference formatting is out
of scope, but this is a structural defect rather than a formatting one — *flagged, not edited*.

**M9. Unresolved placeholders and planning notes remain in the body.** `XXXX` (1), `[full official`
(1), "check later" (1), "correct it" (1), "create a repo" (1), "add link" (1), "maybe move" (2),
ellipsis placeholders (5), and **30 paragraphs containing Cyrillic text**, including two internal
planning notes that must not reach the journal. *Flagged, not edited* — these are the author's own
`{{…}}` markers.

**M10. Author metadata is incomplete.** The byline carries four `?` marks and a parenthetical
Cyrillic note; only author 1 has an affiliation superscript; one affiliation is listed for eight
named authors; no ORCID iDs. The CRediT statement names eight authors, the byline nine.
*Flagged, out of scope.*

### Design and interpretation

**M11. The ranking is still driven by methods with very unequal run counts.** Recomputed from
Supplementary File 3 (2,234 subset):

| Method | Runs | Rank by composite |
|---|---|---|
| `22_tmm` | 6 of 84 | 1st after the best group |
| `23_vst` | 6 of 84 | 2nd |
| `33_amdbnorm` | **14 of 84** | 3rd |
| `10_mnn` | 84 of 84 | 5th |

The manuscript now says this for `22_tmm`/`23_vst` and for `33_amdbnorm`, which is the right
correction, and the Discussion's limitations paragraph acknowledges it. It would be stronger to
report the composite score restricted to the strategies each method actually ran on.

**M12. `33_amdbnorm` reaches the theoretical optimum on the metric it is ranked by.**
`PCReg_RNA_BATCH == 1.0000` in **all 14** of its runs. The Extended document correctly reads this as
suspicious rather than excellent. (Note the paired claim about `13_fsmvn` is wrong — see §3.)

**M13. No positive or negative control.** Still no label-permutation control and no cross-cohort
FL-vs-DLBCL classification before and after harmonization. The Discussion now names this as the
single most valuable addition, which I endorse; it would convert the paper's central claim from
"metrics improve" to "biology is recoverable".

---

## §3 Minor

### 3.1 Main manuscript — factual and numerical

| # | Location | Issue |
|---|---|---|
| 1 | Results, best approaches | "eight best-performing harmonization approach groups (15 **indiviual** approaches)" — typo |
| 2 | Discussion, limitations | "First, **lbeit** the composite score…" → *albeit* |
| 3 | Discussion, limitations | "Second, **fix** of the 33 implemented methods were not run…" → *six* |
| 4 | Table 4, group K | "Sparsity metrics: **umber** and percentage…" → *number* |
| 5 | Table 2, row 3 | "Output is not a corrected expression matrix - **its** embedding…" → *it is an* |
| 6 | Table 2, row 4 | trailing comma after "Z-scaling," in the methods list |
| 7 | Methods, metrics | "we assembled a set of 87 polarity-defined scoring metrics together with 142 additional metrics" — consistent with Supp. File 4 ✅ (no change) |
| 8 | Results, clustermap | "two-sided Mann-Whitney p-value < 10-200" — superscript lost in the source; set as 10⁻²⁰⁰ |
| 9 | Discussion | "batch effects are typically 2–5 smaller in variance explained" — missing "-fold" |
| 10 | throughout | `tSNE` 43 × vs `t-SNE` 2 × — normalise to `tSNE` |
| 11 | throughout | `analyze` 5 × vs `analyse` 3 × — normalise to US spelling (consistent with *neighbor* 27, *tumor* 8, *color* 44) |
| 12 | Methods, imputation | "32-48-core" → "32–48-core" (en dash) |
| 13 | Results | "Figures 6 and 7" cross-reference points at figures that have been moved out of the manuscript |

### 3.2 Extended Metrics document — numbers that do not reproduce

All recomputed on the 2,234-approach analysis set (Supplementary File 3 for polarity-adjusted PCReg,
`metrics_comprehensive_260609.csv` for un-normalized LISI and expression statistics; the latter lacks
`20_shambhala`, so 2,150 rows where noted).

| # | As written | As recomputed | Action |
|---|---|---|---|
| 14 | 95 % CI "−0.21, **−11**" | −0.203, **−0.115** | typo — corrected |
| 15 | "33_amdbnorm **and 13_fsmvn** both have pcr_RNA_BATCH of exactly 1.0000 in every run" | only `33_amdbnorm` (14/14). `13_fsmvn` ranges **0.9967–1.0000**, median 1.0000 | corrected |
| 16 | LISI, all approaches: "median 1.16 and MAD **0.103**" | median 1.1669, MAD **0.1089** | corrected |
| 17 | iLISI ~ cLISI "Spearman r = **0.527**, p = 7×10⁻¹⁶⁰" | r = **0.523**, p = 1.8×10⁻¹⁵¹ (n = 2,150; `20_shambhala` absent from the metric snapshot) | corrected, n stated |
| 18 | per-strategy r "**0.374 to 0.815** with median **0.617**" | **0.355 to 0.820**, median **0.650**; 13 of 14 significant, G the exception ✅ | corrected |
| 19 | Mann-Whitney best vs rest, LISI batch "p = 2.0×10⁻⁷" | p = **8.5×10⁻⁹** | corrected |
| 20 | "**8 more** methods had a minor percentage of **0.44 – 2.3 %** samples with at least one NA" | **9** methods, **0.003 – 1.4 %** | corrected |
| 21 | "**4 methods** (20_shambhala, 26_xpn, 15_fsqn_py, 17_quantile) had **26–67 %** samples with at least one NA" | 3 verifiable methods, **30.2 – 38.1 %**; `20_shambhala` is absent from the metric snapshot and could not be checked | corrected + caveat |
| 22 | "**19 out of 31**" methods with no missing values | **18** of the 30 verifiable methods (`20_shambhala` unverifiable) | corrected |
| 23 | "08_inmoose_combatseq and 06_combat_seq had outliers above 1 million (**5.08×10⁸, 1.69 million**), whereas their 99th percentiles were only **18.5 and 17.9**" | means per method: inmoose **1.46×10¹¹** (p99 **17.9**), combat-seq **2.76×10⁸** (p99 **18.5**) — the two percentile values are **swapped** relative to the methods | corrected |
| 24 | "**20 out of 31**" methods with minimum expression below zero | **19** of the 30 verifiable methods; lowest −40.64 (`13_fsmvn`) ✅ | corrected |
| 25 | "05_combat and 29_combat_ref … (PCReg **0.357 – 0.465**)" | across A, B, I, J, E1–E3 the range is **0.357 – 0.823** | flagged; the lower bound is right, the upper is not the range maximum |
| 26 | "gradual decrease of local composite impact from **0.1 to 0.7** (in 28_npn)" | 0.7 > 0.1, so "decrease" is impossible — intended **0.07** | corrected |

Numbers that **do** reproduce exactly and were left alone: best-approach PCReg batch median 0.871 /
MAD 0.122 and biology 0.820 / 0.063; Mann-Whitney p = 0.0063; `14_qsmooth` PCReg median 0.208 /
MAD 0.098; strategy medians D 0.939, K 0.925, S0 0.883, C 0.872, J 0.529 / 0.745; `10_mnn` iLISI
1.72 / 0.209 and `14_qsmooth` 1.07 / 0.032; strategy cLISI K 1.07, D 1.10, J 1.62, C 1.39, H 1.41;
`33_amdbnorm` 14 of 84 runs; `21_harmonizr` zero gene retention in 8 of 14 strategies; KS best-group
median 0.445 / MAD 0.041 and strategy C 0.439 / 0.015 and 0.325 / 0.055; `19_tdm` median 75.1,
maximum 568.9; `28_npn` median −0.010; range 1.90 (`23_vst`) – 7.08 (`22_tmm`); every one of the
best-approach expression bounds (SVA −10.8…−4.98, FSQN R −8.07…0, FSMVN −19.4, AMDBNorm −6.25,
MNN 1.61…2.44, medians 2.89…6.70, maxima 12.6…28.6).

### 3.3 Extended Metrics document — language

`sameslow` → "same slow" · `consentingly` → "consistently" · `Surprizingly` → "Surprisingly" ·
`malingnant` → "malignant" · `pefromance` → "performance" · `reveal's` → "reveals" ·
`presumable explained` → "presumably explained" · `the fast that` → "the fact that" (×2) ·
`PLATFROM_RNA` → "PLATFORM_RNA" · `inversed pattern` → "inverse pattern" · `raising to` → "rising to" ·
`it's true` → "it is true" · `DCS` → "DSC" · duplicated clause "As in the case of LISI, 10_mnn was
the best approachAs in the case of LISI, 10_mnn was the best method" (already inside a deletion) ·
"There is no royal way in the field of…" — informal register, replaced with "There is no shortcut in".

### 3.4 Register

"supremacy of the clustermap best approaches", "brute force", "rejected by clustermap",
"failed spectacularly" and similar were checked; only *supremacy* survives in the Extended document
and has been replaced with "the highest values". The main manuscript's register is now appropriate.

---

## §4 Statistics and methodology — consolidated verdict

**What is sound.** The four-factor effect-size analysis is correctly specified and exactly
reproducible; I recovered 0.3629 / 0.2564 / 0.0155 / 0.0020 from the deposited file using the same
per-metric η² definition the notebook implements. Confidence intervals are now reported for both the
Spearman correlations (bootstrap) and the R² values (t-interval), and the method is named. The
polarity table is complete and internally consistent (229 metrics, 87 non-zero). The analysis-set
filter is stated as an explicit, checkable predicate (`pct_samples_allNA < 5`) and it reproduces to
the row. The decision to treat the clustermap rather than the composite score as the selection
instrument is correct and is now stated as such, which removes the previous version's most serious
inferential problem.

**What must still be fixed.**

1. **Model specification (C3).** State the design matrix for every supervised method. Two of the six
   named methods did not receive the biological covariate the text claims.
2. **Stochastic metrics have no replication (M3).** Seeds are now reported, which makes the result
   reproducible, but not robust. Report run-to-run spread for the 14 embedding metrics.
3. **Unequal design (M11).** Six of 33 methods did not run on all 14 strategies, and three of the top
   five ranked methods ran on ≤ 14 of 84 combinations. The composite score should be reported
   restricted to a common strategy set, or the ranking should be presented per strategy only.
4. **No controls (M13).** A label-permutation negative control and a cross-cohort classification
   positive control remain the highest-value additions available to this study.
5. **kBET.** The median acceptance rate over all 2,234 approaches is **0.0000** for RNA_BATCH and
   COHORT_LABEL, 0.0056 for PLATFORM_RNA and 0.0255 for RNASEQ_SOURCE. The manuscript now
   acknowledges kBET's small-batch sensitivity in the limitations, which is the right treatment, but
   kBET is still one of the six axes of the Figure 6C/6D radar plots. Consider stating there that the
   axis is near-degenerate for RNA_BATCH.

**On the central biological claim.** The assertion that only MNN, SVA and FSQN R preserve the
FL / DLBCL / normal-GC-B distinction is supported by the metric evidence and by the embedding
figures, and the paper is appropriately careful to call the two FL subgroups a hypothesis requiring
survival and enrichment follow-up. The one-order-of-magnitude batch-to-biology ratio that frames the
whole paper (PCReg 0.226 vs 0.923) checks out exactly against the deposited data.

---

## §5 Figures, tables and supplementary material

### Format compliance

| Requirement | Status |
|---|---|
| Page size A4 | ❌ US Letter (21.59 × 27.94 cm) |
| NAR Word template | ❌ not applied (Normal = Times New Roman, single spacing) |
| Line numbering | ✅ present |
| Page numbers | ✅ two footer parts present |
| Abstract ≤ 200 words | ✅ 198 |
| Graphical abstract | ✅ present, 26.7 × 10.3 cm, median 9.8 pt — the only figure that is legible after scaling |
| Figures ≤ 17.35 × 23.35 cm | ❌ all 37 exceed it |
| Fonts embedded | ❌ Type 3, zero embedded, all 37 files |
| CMYK | ❌ all RGB |
| No JPG for line art | ❌ JPG siblings supplied for every figure |
| Alt text, main figures | ✅ all six carry an `Alt text:` line |
| Alt text, supplementary figures | ❌ none of the 17 |
| Alt text, graphical abstract | ❌ absent |
| Supplementary ≤ 10 files ≤ 2 MB | ❌ 78 files, 15 over 2 MB — see repackaging below |

### Repackaged supplementary set (`supplementary_260802/`)

Three data files plus seven figure bundles = **10 files**, matching the author's plan:

| File | Size | Contents |
|---|---|---|
| `Supplementary File 1.csv` | 1.41 MB | cohort annotation, 7,174 samples — unchanged |
| `Supplementary File 2.xlsx` | 0.10 MB | **new workbook**: sheet `Genes_per_sample` (former File 2, deduplicated to 7,174) + sheet `Metric_polarity` (former File 4, `pcr_*` → `PCReg_*`) |
| `Supplementary File 3.csv.gz` | 1.40 MB | 87 metrics × 2,407 approaches — unchanged |
| `Supplementary Figures S1-S2.pdf` | 3.30 MB | pages titled and bookmarked |
| `Supplementary Figures S3-S4.pdf` | 3.89 MB | |
| `Supplementary Figures S5-S7.pdf` | 3.49 MB | |
| `Supplementary Figures S8-S9.pdf` | 2.87 MB | |
| `Supplementary Figures S10-S12.pdf` | 2.20 MB | |
| `Supplementary Figures S13-S15.pdf` | 2.21 MB | |
| `Supplementary Figures S16-S17.pdf` | 1.31 MB | |

Also produced: `Supplementary Figures S1-S17.pdf` (19.17 MB, 17 titled and bookmarked pages) — the
single-PDF route, which is what I recommend submitting.

Supplementary figure **numbering is unchanged**, as instructed. The supplementary **table**
nomenclature changes from four files to three, so every "Supplementary File 4" reference in the
manuscript becomes "Supplementary File 2" and the two file legends have been rewritten.

### Figure-specific comments

- **Figure 6** (formerly Figure 9) is the composite-score / decision-tree figure and is present in the
  folder under its new number; the manuscript still called it Figure 9 throughout. *Renumbered.*
- **Figure 6** and **Extended Figure 8** still print the string `PCR` in axis labels, from before the
  PCReg rename. Not fixable from the manuscript — regenerate.
- The Extended Metrics document's own **Figures 6, 7 and 8** correspond to the delivered
  `Extended Figure 1`, `2` and `3`, and its **Extended Figures 1–10** correspond to the delivered
  `Extended Figure 4–13`. The document's internal numbering was three behind the files.
  *Renumbered throughout.*
- **Supplementary Figure 15** legend and the FFPE claim agree with the artwork: PC1 87.6 % → 38.4 %,
  a 56 % relative reduction. Verified against the figure's own text layer. (The metric table's
  `pct_var_pc1` differs because it is computed on standardized data over 50 PCs; the figure's PCA is
  the authority for the number quoted, so I did **not** change it.)
- Likewise **Figure 4A**'s "81.1 % of the total variance explained by the first PC" matches the
  figure exactly and was left alone.

---

## §6 Recommendation

**Minor-to-moderate revision.**

The four changes that would most alter my assessment, ranked:

1. **Regenerate the figures at final print width** with embedded fonts and ≥ 7 pt type. Five figures
   are currently unreadable in print, one of them the paper's central clustermap. This is the single
   largest remaining obstacle to acceptance and it is purely mechanical.
2. **Add the label-permutation and cross-cohort-classification controls.** They would turn the
   metric ranking into evidence about biology.
3. **State every design matrix** and re-run limma and RUV with the biological covariate, or say
   plainly that they were run without one and that this is part of why they fail.
4. **Report run-to-run variability of the 14 embedding-space metrics** and restrict the composite
   ranking to a common strategy set.

---

## Appendix — verification method

| Claim | How checked |
|---|---|
| 2,234 / 2,407 / 31 methods | `pandas` on `Supplementary File 3.csv.gz`; `pct_samples_allNA < 5`; `set(all) − set(passing)` |
| 87 / 142 / 229 metrics | row and value counts of `Supplementary File 4.csv`; set-intersection of its index with File 3's columns |
| η² 0.363 / 0.256 / 0.016 / 0.002 | per-metric one-way `SS_between / SS_total` over the 87 scoring columns on the 2,234 subset, then averaged — the definition implemented in `Finally_assembled_figures_for_article.ipynb` cell 17 |
| PCReg 0.226 / 0.923 | direct lookup, `metrics_comprehensive_260609.csv`, row `S0_no_removal / 01_raw / strict / post_rm=False` |
| Model matrices | regex extraction of every `normalize_*` body from `bench_shared.py`, filtered for `model.matrix`, `mod`, `mod0`, `design`, `batch=`, `k=` |
| Seeds and embedding parameters | `compute_batch_metrics.py:142` (PCA), `:161-165` (UMAP), `:187-188` (t-SNE) |
| Spearman / Mann-Whitney / MAD | `scipy.stats.spearmanr`, `mannwhitneyu`, `median_abs_deviation`, `bootstrap` (2,000 resamples, seed 0) |
| Figure geometry, fonts, colour space, font size after scaling | PyMuPDF via `nar_review_tools.py figures` |
| PC1 percentages quoted in the text | PDF text layer of `Figure 4.pdf`, `Figure 5.pdf`, `Supplementary Figure 15.pdf` |
| Extended Figure ↔ file mapping | PDF text layer of all 13 `Extended Figure *.pdf`, matched against the document's own legends |
| Supplementary sizes | recompression with PyMuPDF `garbage=4, deflate, deflate_images, deflate_fonts, clean` |
