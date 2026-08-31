# Referee report — *Nucleic Acids Research*

**Manuscript:** "Benchmarking of bulk transcriptomic harmonization tools across a multi-platform
germinal centre B-cell lymphoma cohort identifies mutual nearest neighbors and surrogate variable
analysis as top-performing methods"

**Files reviewed**
- `FL_harmonization_article_NAR.docx` (main text, tables, figure legends)
- `current_figures_tables_for_article_260726/` — Graphical Abstract, Figures 1–9, Extended Figures 1–10,
  Supplementary Figures 1–17, Supplementary Files 1–4, `Harmonization_metrics_extended.docx`
- `NAR_author_guidelines.md` (compliance check)

**Explicitly excluded from this review at the author's request:** all italicised placeholder text,
GitHub URLs, and reference/citation formatting (both in-text and bibliography).

**Date:** 2026-07-27
**Edited manuscript with tracked changes:** `FL_harmonization_article_NAR_260727.docx`

---

## 0. Summary assessment

This is an unusually large and genuinely useful benchmark: 7,174 samples, 88 cohorts, four platform
families, a four-factor cross-product design, and 87 scoring metrics. The central scientific question
— whether harmonizers developed on TCGA/GTEx-scale contrasts survive a subtle-biology regime — is
well posed and under-studied, and the decision tree is the kind of practical output that gets cited.
The dataset assembly, the strategy taxonomy (Table 1), the metric taxonomy, and the honest reporting
of implementation failures are all strengths.

However, in its current form the manuscript **cannot be accepted**. My concerns fall into three
groups, in descending order of seriousness:

1. **The definition of the paper's primary global metric (PCR) is stated backwards**, which makes the
   whole of the "Harmonization metrics behaviour" section read as self-contradictory (§1.1).
2. **The headline counts do not agree with each other or with the deposited data** — the number of
   harmonization methods (31 vs 33), the number of approaches (2,234 vs 2,407 vs 2,604 vs 2,409), and
   the number of metrics (230 vs 165) each take two or more values (§1.2–1.4). The primary quality
   filter and two of the reported correlation coefficients **cannot be reproduced** from
   Supplementary File 3 (§1.5).
3. **The ranking and variance-decomposition analyses are confounded by a badly unbalanced design**
   that the manuscript notes in passing but does not correct for: six of the 33 methods were not run
   on all 14 strategies, two were run on only one, and the composite score is averaged over
   *different metric subsets* for different strategies (§4).

None of these is fatal to the underlying work — they are reporting and analysis problems, and the raw
material to fix them appears to exist. But they must all be resolved before the claims can be
evaluated.

**Counts:** 12 critical, 34 major, 61 minor.

---

## 1. CRITICAL issues

### 1.1 The definition of PCR is inverted, making the central Results section incoherent
**Location:** Results, PCR paragraph ("Zero PCR for an annotation column indicated that this column
explained 0% of PCA variation, whereas PCR 1 showed that a column completely explained PCA
variation"); Table 4, PCR and PCA R² rows.

The manuscript defines PCR in the conventional direction (high = column explains more variance) but
uses it throughout in the **opposite** direction. From Supplementary File 3:

| quantity | value | manuscript's verdict |
|---|---|---|
| `pcr_RNA_BATCH`, unharmonized S0 (`01_raw`) | 0.227–0.313 (6 rows) | worst |
| `pcr_RNA_BATCH`, `33_amdbnorm` / `13_fsmvn` / `03_limma` | 1.000 | best |
| `pcr_RNA_BATCH`, `14_qsmooth` | median 0.208 | "lowest batch correction performance" |

So the deposited metric is evidently **1 − (weighted fraction of variance explained)**: higher = the
column explains *less*. Every substantive statement in the section is consistent with that reading —
only the definition sentence, and Table 4's two definitions, are wrong. Consequences:

- The sentence "this baseline level is expected to be **lowered** by successful harmonization
  approaches" is exactly backwards; successful harmonization *raises* the polarity-adjusted PCR.
- Table 4 defines PCR as "Fraction of total PCA variance attributable to a column" and PCA R² in the
  same direction — but the per-PC R² values quoted in the Figure 6C paragraph ("R² below 1% for all
  PCs") are clearly *non*-inverted. **The manuscript therefore uses two opposite conventions for two
  closely related metrics without saying so.**

**Required:** state explicitly, in Methods and in Table 4, which metrics are reported raw and which
are polarity-adjusted, and give the transformation. Then re-read the entire section against the
corrected definition. *(Tracked edit proposed; please verify the exact transformation you applied.)*

### 1.2 The number of harmonization methods is inconsistent — 31 in the text, 33 in Table 3 and in the data
- Text: "We successfully implemented **31** of these methods… **Seven** methods failed implementation".
  31 + 7 = 38, not 39.
- Table 3 contains **33** rows marked "Implementation done = Yes" and **6** marked "No".
- Supplementary File 3 contains **33** distinct methods.
- All main figures (3, 6, 7, 8, 9) contain exactly **31** method labels. I checked the text layer of
  every figure PDF: **`34_arsyn` and `38_harman` appear in none of them**, yet both are listed as
  successfully implemented in Table 3 and both contribute 78 rows each to Supplementary File 3.

So two implemented methods were silently dropped from every analysis. **Required:** reconcile the
count (33 implemented / 6 failed), and either include ARSyN and Harman in the analyses or state
explicitly that they were excluded and why.

### 1.3 The number of harmonization approaches takes four different values
| value | where |
|---|---|
| 2,234 | Abstract, Results (×2), Figure 3 legend, Discussion, Supplementary Figure legends 7/9/10 |
| 2,407 | Results ("out of totally 2407 approaches"; "yielding 2,407 … in total") |
| 2,604 | Discussion ("2,604 theoretical configurations") |
| 2,409 | Supplementary File 3 legend |

Supplementary File 3 has **2,407 data rows**. The theoretical cross-product is 14 × 3 × 33 × 2 =
2,772 (or 14 × 3 × 31 × 2 = 2,604 if the two dropped methods are excluded, plus 12 rows for the
C-only TMM/VST runs). Please fix all four numbers to a single consistent set and state the
denominator each one refers to.

### 1.4 The number of computed metrics does not match the deposited polarity file
Methods states "87 polarity-defined scoring metrics together with **143** additional metrics computed
but not included in the composite scoring" and Results states "up to **230** harmonization metrics per
approach". **Supplementary File 4 contains 165 metrics in total**: 51 with polarity +1, 36 with −1
(= the 87 scoring metrics, which match Supplementary File 3's 87 metric columns exactly), and **78**
with polarity 0. 87 + 78 = 165, not 230. Either the "230/143" figures are wrong or Supplementary
File 4 is incomplete.

Related: Methods says polarity was coded "+1 … or −1"; the file actually uses a three-level code
(+1 / −1 / 0). Document the 0 level.

### 1.5 Key reported statistics cannot be reproduced from the deposited data
I recomputed directly from Supplementary File 3 (all 2,407 rows):

| reported | manuscript | recomputed | verdict |
|---|---|---|---|
| Spearman iLISI(batch) vs cLISI(biology) | r = 0.527, p = 7 × 10⁻¹⁶⁰ | **r = 0.352, p = 6 × 10⁻⁷¹** | does not reproduce |
| Spearman PCR(batch) vs PCR(biology) | r = −0.159, p = 3.7 × 10⁻¹⁴ | **r = −0.109, p = 8.7 × 10⁻⁸** | does not reproduce |
| the 2,234-approach filter ("<5% samples with all-NA expression") | 2,234 of 2,407 | `pct_samples_noNA ≥ 95` → **2,038**; `pct_na_cells < 5` → **2,186**; complete-metric rows → **1,354** | not reproducible at any threshold |

The most likely explanation is that the analysis used the 2,234-row subset while Supplementary File 3
deposits all 2,407. If so, **the subset flag must be a column in Supplementary File 3** so that
readers can reproduce every number in the paper. As deposited, none of the headline statistics can be
checked.

### 1.6 The composite score is not comparable across batch removal strategies
The composite score is "the mean of polarity-normalized values across all the 87 scoring metrics" —
but the number of *defined* metrics differs systematically by strategy, because annotation columns
become invariant in single-platform / single-biomaterial subsets. Mean non-NA metric count per
strategy (from Supplementary File 3):

```
K_ffpe_only 66.6   G_affymetrix_only 67.0   C_rnaseq_only 71.8   J_ff_only 74.8
S0_no_removal 81.4      all other strategies 85.9–86.8
```

Only **1,354 of 2,407** approaches have all 87 metrics defined. A mean over 67 metrics is not on the
same scale as a mean over 87, yet the two are ranked against each other and used as the response
variable in the effect-size analysis. This directly inflates the strategies with the fewest defined
metrics — which are exactly the strategies (C, K) that the paper concludes are best. **The
manuscript acknowledges the missing metrics (Supplementary Figure 6) but does not address the
consequence.**

**Required:** either restrict the composite to the metric subset defined for all strategies, or
compute it within strategy and compare ranks, or impute/standardise per metric before averaging —
and report the sensitivity of the conclusions to that choice.

### 1.7 Rankings are driven by methods with 7–17% strategy coverage
Runs per method in Supplementary File 3 (of a possible 84 = 14 strategies × 3 imputations × 2
post-removal):

```
22_tmm 6    23_vst 6    33_amdbnorm 14    27_dwd 34    29_combat_ref 34    36_explobatch 60
04_sva 80   05_combat 80   19_tdm 80   08_inmoose 82   06_combat_seq 83   (all others 84)
```

Consequences the manuscript does not handle:

- `22_tmm` and `23_vst` rank **1st and 2nd** by composite score on **6 runs each, all in strategy C**.
  The text notes this ("apparently because they were applied to C strategy only") but still leaves
  them at the top of Figure 9E and in the narrative ranking.
- `33_amdbnorm` is presented among the "top 5 methods by average PCR RNA_BATCH", is one of the eight
  best-approach groups in Table 5, and is **recommended in the decision tree (Figure 9F)** — on **14
  of 84 runs**. Its `pcr_RNA_BATCH` is **exactly 1.0000 in all 14 runs**, as is `13_fsmvn`'s. A global
  metric saturated at its theoretical optimum, combined with poor local mixing, is more consistent
  with the method having destroyed structure than with successful correction. This deserves explicit
  investigation before AMDBNorm and FSMVN are recommended to readers.
- `04_sva` — one of the two headline methods — is missing 4 of 84 runs, unexplained.

**Required:** report coverage per method, exclude or separately report methods with incomplete
coverage, and re-derive the rankings and Figure 9B on a balanced subset.

### 1.8 The effect-size analysis is mis-described and is not a variance decomposition
Text: "we performed a **variance decomposition** analysis using **R²** effect sizes across the full
87-metric composite scoring space". Figure 9B's axis says "Mean **η²** effect size across 87 scoring
metrics".

These are three different things. What the figure describes is the mean of per-metric one-way η²
values — four separate marginal effect sizes that do **not** partition variance, ignore the
factor imbalance documented in §1.7, and ignore interactions. My reconstruction on the composite
score over all 2,407 rows gives single-factor R² of **method 0.429, strategy 0.174, imputation 0.002,
post-removal 0.000** (additive four-factor model R² = 0.593), versus the reported 0.363 / 0.256 /
0.016 / 0.002. The *ordering* reproduces; the *magnitudes* do not, and the strategy term differs by
almost 50%.

This matters because "method (0.36) > strategy (0.26)" is an Abstract-level claim that the clustermap
analysis contradicts ("this structure was dominated by batch removal strategy rather than by
harmonization method"). **Required:** specify the model (response, estimator, whether Type II/III
sums of squares, how unbalanced cells were handled), report confidence intervals, use one notation
consistently, and reconcile the two opposite orderings explicitly rather than in a parenthesis.

### 1.9 Figure 3 — the paper's central figure — is illegible at NAR's maximum print size
Figure 3 is drawn at **39.6 × 26.8 cm**. NAR's maximum is **17.35 × 23.35 cm**, forcing a scale factor
of **0.44**. After scaling, **100% of the text falls below 5 pt** (median 4.4 pt). The same problem
affects Supplementary Figures 2, 3 and 4 (100% below 5 pt) and Supplementary Figure 7 (81% below
5 pt, median **3.0 pt**). See §5.2 for the full table.

The figure is also rendered **rotated 90°** — every label reads sideways — and uses a **red–green**
diverging metric-score palette, the single worst choice for the most common form of colour-vision
deficiency, on a figure where colour *is* the data. NAR/OUP require colour-blind-safe palettes and
that meaning not depend on colour alone.

### 1.10 Figure 3's legend describes the axes the wrong way round
Legend: "Cluster map of 2234 harmonization approaches (**columns**) in a space of 87 quality metrics
(**rows**)". In the figure, the approach dendrogram is on the left and the 87 metric names label the
vertical strips: approaches are **rows** and metrics are **columns**. Swap them.

### 1.11 The Conclusions, Discussion and Table 5 disagree on how many methods succeeded
- Conclusions: "among 31 harmonization tools, **SVA and MNN only** were able to … resolve subtle
  differences".
- Discussion: "**MNN, SVA, and FSQN R** were the only algorithms that simultaneously resolved FL,
  DLBCL, and normal GC B-cell transcriptional differences".
- Discussion, elsewhere: "only **SVA and MNN** allow to preserve the subtle FL/DLBCL/normal GC B cells
  differences".
- Table 5 and Figure 9F recommend **five** methods: MNN, SVA, FSQN R, FSMVN, AMDBNorm.

Two, three or five — the reader cannot tell what the paper concludes. This needs a single, stated
criterion for "resolved the biology" and one consistent count.

### 1.12 Supplementary File 2 does not match the stated dataset
Supplementary File 2 ("Number of genes with defined gene expression by sample in the initial
dataset") contains **7,238 rows**. The dataset throughout the manuscript is **7,174 samples**
(Supplementary File 1 has exactly 7,174 rows). Either the file is a pre-filtering version — in which
case say so and document the 64 removed samples — or it is the wrong file.

---

## 2. MAJOR issues

### 2.1 Reproducibility of the harmonization runs

**M1. The model/design matrices supplied to the supervised methods are not reported.** SVA, limma
`removeBatchEffect`, ComBat, ComBat-seq, M-ComBat and RUV all require the user to specify which
covariates are *protected*. "We used all the methods with default parameters" does not determine this,
and it is the single most consequential choice in the paper: an SVA run with no biological covariate
in `mod` can remove exactly the FL/DLBCL signal the paper is measuring. Since SVA is a headline
method, the `mod`/`mod0` (and equivalent) specifications must be given explicitly for every
supervised method.

**M2. The stochastic embeddings have no seed or replication.** UMAP and t-SNE are stochastic, and
**14 of the 87 scoring metrics** are computed in embedding space (centroid dispersion and neighbourhood
entropy in both UMAP and t-SNE, ×7 annotation columns). No random seed, no perplexity/`n_neighbors`
/`min_dist` settings, and no repeat runs are reported. Several conclusions rest on differences of
0.01–0.05 in these metrics, which is plausibly within run-to-run variability. Please report the
parameters and the seed, and quantify embedding-to-embedding variance on at least a subsample.

**M3. The KS-test metric is defined two different ways, and its gene sampling is undocumented.**
Table 4: "For each gene of a randomly selected 1000 genes, do Kolmogorov-Smirnov two-sample test
comparing expression distributions **between all pairs of batches**". Results: "mean D statistic of
Kolmogorov-Smirnov test **between all sample pairs** within batches". Batch pairs and sample pairs
are not the same comparison. Also: was the 1,000-gene subset drawn once and fixed across all 2,407
approaches, or redrawn per approach? If redrawn, the metric is not comparable between approaches.

**M4. "Systematic literature search" is asserted but not documented.** The claim that 75 methods were
reviewed and 36 rejected is one of the paper's contributions, but no databases, query strings, date
range, or inclusion/exclusion criteria are given. Either provide them (a PRISMA-style flow diagram
would suit the supplement well) or describe the search as non-systematic.

**M5. The harshness score is subjective and unattributed.** "Each implemented method was assigned a
qualitative harshness score (low, medium, or high)" — by whom, against what written criteria, and
independently of the results? Since Figure 9A tests a hypothesis about harshness, the assignment must
be pre-specified and auditable (a column in Supplementary File 4 or a supplementary table would do).

**M6. Post-removal is defined at two different granularities.** Methods: "For each of the 88
**cohorts** we calculated Euclidean distance of its centroid…". Results: "the pipeline excluded a
single PCA-outlier **batch** after harmonization". Discussion: "the exclusion of **one PCA-outlier
batch**". There are 88 cohorts and 29 batches; these are different operations. Also, Methods never
states the actual removal rule — the metric is described but not the threshold or the decision
("remove the single most distant cohort"? "any beyond k MAD"?).

**M7. Table 4 is incomplete.** It lists metric groups A, B, C, D, E, G, H, I, J — but **Figure 3's own
legend lists group K ("Samples and genes with NAs")**, and no group F appears anywhere. The "Source"
column is populated for exactly one of the 18 rows. Table 4 is the reader's only route into the
metric definitions and should be complete.

**M8. Two metrics in Table 4 appear mis-classified.** ASW and CMS are given metric type "Global",
while kBET and LISI in the same group B are "Local". CMS (a per-sample Anderson–Darling test on
k-nearest-neighbour distance distributions) is a local mixing metric by construction; ASW as computed
here (on 50 PCs) is usually treated as a global/structural measure. Please re-check the type column
against the definitions.

**M9. The kBET metric is uninformative but is still used as a decision axis.** From Supplementary
File 3, `kbet_acceptance_rate_RNA_BATCH` has median **0.000** and 75th percentile **0.0041** across
2,395 approaches. The manuscript correctly notes this in the limitations, yet kBET remains one of the
six axes of the Figure 9C/D radar plots and underpins the claim that "the top C approach had 0.43
average batch mixing by kBET". A metric that is zero for more than half the design cannot carry a
sixth of the summary figure. Either drop it or justify retaining it.

**M10. Min–max normalisation without outlier handling.** The composite score min–max scales each
metric across the whole design. Several expression-range metrics have extreme outliers (the
manuscript itself reports maxima of 5.08 × 10⁸ for `08_inmoose_combatseq` and 1.69 × 10⁶ for
`06_combat_seq`). A single such value compresses all other approaches into a negligible fraction of
that metric's [0,1] range, effectively deleting the metric from the composite. Please winsorise or
rank-transform, and report the effect.

**M11. No positive or negative control.** The standard validation for a harmonization benchmark is
(i) a label-permutation negative control — permute the biology labels and confirm the biology-
preservation metrics collapse — and (ii) a held-out predictive check, e.g. cross-cohort
classification accuracy for FL vs DLBCL before and after each harmonization. Neither is present.
Without them, "preserves subtle biology" rests entirely on visual inspection of embeddings plus
metrics whose polarity was assigned by hand. This is the single most valuable addition the authors
could make.

**M12. Neighbourhood-size parameters are arbitrary and untested.** kBET k = 25, LISI k = 30, entropy
k = 30, graph connectivity k = min(15, n), ASW on 50 PCs, dendrograms on 10 PCs. No justification and
no sensitivity analysis. Given how much of the argument rests on local metrics, a sensitivity check
over k is needed.

**M13. p-values of 10⁻¹⁶⁰ and 10⁻²⁰⁰ are reported without effect sizes.** With n = 2,234 pseudo-
replicated approaches, p-values carry almost no information. Furthermore, approaches sharing a
strategy × imputation subset are not independent observations — they are re-analyses of the same
samples — so every Mann–Whitney and correlation test in the paper is pseudo-replicated. At minimum,
report effect sizes with CIs alongside the p-values and acknowledge the dependence; better, test at
the level of the independent units (the 42 strategy × imputation subsets).

**M14. r = −0.159 is described as evidence for a trade-off.** A Spearman r of −0.159 (and −0.109 in
my recomputation) explains ~1–2.5% of the variance. It does not support the global/local trade-off
narrative on its own; the LISI correlation (r = 0.35–0.53) does. Please separate the two claims and
report confidence intervals.

**M15. A statistically significant but trivially small difference is presented as a finding.**
Composite score by harshness: medians 0.479 / 0.488 / 0.493 with MAD 0.044 — differences of ~0.01
against a dispersion four times larger, reported as "significantly differed (p = 0.041)". State the
effect size and say plainly that harshness has negligible practical impact. (Also: an FDR-corrected
p of exactly 0.041 for *both* comparisons is worth double-checking.)

### 2.2 Internal contradictions and cross-reference errors

**M16.** "Among the **five** largest RNA batches by sample count, the **fifth** largest
(GPL14951_FFPE, 810 samples) and **sixth** largest (GPL570_FFPE)…" — a set of five cannot have a
sixth member. *(Edited to "six largest".)*

**M17.** The biology counts do not sum to the dataset. Results gives 4,466 DLBCL + 1,697 FL + 875
normal B cells + 88 Burkitt + 34 high-grade = **7,160**, not 7,174. The missing 14 are the
plasmablast samples, which are mentioned two paragraphs later and are present in Supplementary File 1.
(I verified: the 10 normal-B categories in Supplementary File 1 sum to exactly 875, and 875 + 14 =
889 = the samples removed by strategy D, consistent with Table 1's 6,285.) Add the plasmablasts.

**M18.** Two different values for PC1 variance in the raw S0 dataset: **81.1%** (Figure 4 paragraph)
vs **73.5%** (Figure 6C paragraph). And a third quantity, "77.4% of PCA variance attributable to
RNA_BATCH", is derived from 1 − PCR (§1.1) and is not the same thing as either. Please give one
number per quantity and label each precisely.

**M19.** The strategies said to have undefined annotation-dependent metrics are listed as
**"C, G, J, and K"** in one paragraph and as **"(J, K) … or (H, C)"** in the next. Supplementary
File 3 supports C, G, J, K (66.6–74.8 defined metrics) with H at 86.7 — i.e. the first list is right
and H is wrong.

**M20.** The `pct_genes_noNA` failure is attributed to **`21_harmonizr`** in Results ("0% for the
strategies A, B, C, E1-E3, J and S0") — which Supplementary File 3 confirms exactly — but to **"the
Angel harmonizer"** in the Discussion. One of the two is wrong.

**M21.** Cluster naming drifts. Figure 3 labels the clusters "Same platform cluster" and "Same sample
type cluster"; the Results text refers once to "the good sub-cluster of **'same biomaterial**" (with
an unclosed quotation mark). Use one name.

**M22.** Wrong cross-reference: "we selected Local Inverse Simpson's index (LISI) as it was scattered
along the entire local metrics cluster in **Supplementary Figure 6**". Supplementary Figure 6 is the
metric-count heatmap; the metric cross-correlation clustermap is **Supplementary Figure 7**.
*(Edited.)*

**M23.** Figure 9's legend assigns panels D and E the wrong way round. The figure is C = radar (by
method), **D = enlarged radar (by strategy)**, **E = stacked bar chart**; the legend says D = stacked
bar, E = radar. The main text cites them correctly, so the legend is what needs fixing. *(Edited.)*

**M24.** The gene-with-NA counts do not add up: "All samples had all genes with defined expression
values for **19** out of 31 harmonization methods… At the level of genes with NA, **the same 10**
harmonization methods returned no NA at all, **11** more methods had 0.05–33.6%…". 19 ≠ 10, and
10 + 11 + 1 = 22 ≠ 31.

**M25.** Table 5 has no group for the "RNA-seq + Illumina microarrays" scenario, but the decision
tree (Figure 9F) and the Discussion recommend **FSQN R** as best for it with AMDBNorm/FSMVN as
alternates — while Table 5 lists FSMVN and AMDBNorm only, both under strategy S0. Table 5,
Figure 9F and the text must agree.

**M26.** Three different, unsourced estimates of the biology-to-batch effect-size ratio: the
FL/DLBCL distinction is "approximately 5-fold smaller" than the batch effects; batch effects in
TCGA/GTEx are "2–5-fold smaller in variance explained than in our dataset"; "the technical noise is
5–10-fold larger than the biology signal". Give one estimate, state how it was computed, and cite it.

**M27.** "Regardless of the recent single cell RNA-seq… approximately 65000 bulk profiled patients
compared to the 4000 single cell profiled ones" gives a ratio of ~16×, but the Discussion says bulk
"outnumbers single cell profiled patients by approximately **an order of magnitude**". *(Edited to
"more than an order of magnitude".)*

**M28.** "A **monolithic** implementation allowed to run additional combinations of all the two
steps" directly contradicts the two preceding sentences, which describe a modular
dispatcher/worker/library architecture. *(Edited to "modular" — please confirm.)*

**M29.** Contradiction in the imputation-gene-count ranges: strict NA exclusion is said to span
"3,447 genes (S0 and D) to **6,797** genes (C)", while imputation spans "**6,797** (J) to 15,885 (C)".
The same value bounds both ranges from opposite sides, and a later paragraph gives strict A = 3,520
(not ≥3,447 = S0's value, which is fine, but the reader has to reconstruct this). Please tabulate
gene counts per strategy × imputation rather than describing them in prose.

**M30.** "Multi-platform batch **correction** introduced extensive missing expression values" reverses
the causality — the missingness arises from combining platforms that interrogate different gene
sets, before any correction. *(Edited.)*

**M31.** scikit-learn version conflict: "scikit-learn package version **1.8.0**" in the imputation
Methods vs "scikit-learn (v**1.3.2**)" in both the metrics and figures Methods.

**M32.** Hardware is given three ways: "a Kubernetes pod with 32-48 CPU cores and 240 GB RAM"
(Methods), "an 8-core, 64 GB RAM server" (missForest exclusion), "32 vCPU / 240 GiB RAM"
(Discussion). Reconcile, and state which analyses ran where — the missForest exclusion in particular
rests on a timeout measured on the *smallest* machine, which weakens the justification.

**M33.** "terminated by a 3-hour CPU timeout **on Karpenter**". Karpenter is a Kubernetes node
autoscaler; it does not enforce job timeouts. *(Edited to "a 3-hour CPU-time limit imposed by the job
scheduler" — please correct if the limit came from elsewhere.)*

**M34.** The section heading "AI-driven brute force and human-based approaches: **AI enhancement leads
to ~2 times more actionable approaches**" states a quantitative result that the section does not
support. The section's content is that two of three top methods came from AI-assisted search and one
from manual search — which is not a two-fold enrichment of anything, and involves no comparison
against an all-human baseline. *(Heading edited; the "~2 times" claim should be either substantiated
or dropped.)*

---

## 3. MINOR issues

### 3.1 Spelling, grammar, typographical
Tracked edits have been applied for all of the following unless marked otherwise.

| # | Location | Issue |
|---|---|---|
| m1 | Results, pipeline paragraph | "had **less then** 5% samples" → "fewer than" |
| m2 | Conclusions | "**transcritpional** programs" → "transcriptional" |
| m3 | Figure 9 legend | "**harmonozation** method harshness" → "harmonization" |
| m4 | Supplementary Figure 7 legend | "**Sperman** cross-correlations" → "Spearman" |
| m5 | Supplementary Figure 14 legend | "color palettes in the **lefr** side" → "on the left side" |
| m6 | Results, Figure 5 paragraph | "most NGS and **Affymetrics** platforms" → "Affymetrix batches" |
| m7 | Results, Figure 5 paragraph | "FSMVN in S0 **lead** to co-clustering" → "led" (twice) |
| m8 | Results, Figure 5 paragraph | "RNASeq_FF_**&nbsp;**PolyA" — stray space inside the batch name |
| m9 | Results, Figure 5 paragraph | "First 10 PCs clustering … **resulted** two high level branches" → "produced" |
| m10 | Results, FSQN R paragraph | "3 batch-derived subclusters … and **two ones** in the FL one" |
| m11 | Discussion, ComboBatch paragraph | "approximately **5–-fold** smaller" — stray double dash |
| m12 | Discussion, clustermap paragraph | "The 87-metric × 2,234**- **approach clustermap" — stray hyphen + space |
| m13 | Discussion, limitations | "have **been failed** in implementation" → "failed" |
| m14 | Discussion, TCGA paragraph | "preserving **thousands differentially** expressed genes" → "thousands of" |
| m15 | Discussion, scRNA paragraph | "the primary FF/FFPE batch effect is **unreliable to** scRNA" → "largely irrelevant to" |
| m16 | Discussion, dataset paragraph | "renders the current … dataset inherently more challenging harmonization target" — missing "a" |
| m17 | Discussion, FL subgroups | "the established GCB**/ **memory cell like" — stray space, missing hyphens |
| m18 | Results, metric clusters | "no dominant correlation direction with the other two**, it** consisted of" — comma splice |
| m19 | Results, clustermap | "confirming cluster identity was not an artefact" — missing "that" |
| m20 | Results, Figure 6C | "which **manifest** itself in poor local mixing" → "manifests itself as" |
| m21 | Results, gene overlap | "have broadly **overlapped** transcriptome coverage" → "overlapping" |
| m22 | Results, NA metrics | "**harmonizations** methods" → "harmonization methods" |
| m23 | Results, harmonizr | "for the **rest** strategies" → "the remaining strategies" (also "the rest correlations") |
| m24 | Methods, AI usage | "wrote a research and implementation plan **according**, then…" — dangling word; run-on sentence |
| m25 | Methods, methods table | "**Github**" → "GitHub" (two occurrences) |
| m26 | Methods, harmonization | "the ComboBatch pipeline **combinatory** space" → "combinatorial" |
| m27 | Table 3 | "35_dasc: **DASC is a batch returns** semi-NMF cluster assignments" — garbled |
| m28 | Table 4 | "**Its** specifically isolates residual cohort effects" → "It" |
| m29 | Table 4 | "per-batch 30 nearest **neighbor's** distance distributions" → "neighbours'" |
| m30 | Table 1 legend | "The capital letters **in** the beginning … used as their **synonyms**" → "at the beginning … as strategy labels" |
| m31 | Introduction | "biomarker**s** detection" → "biomarker detection" |
| m32 | Introduction | "(sorted cells **etc**)" → "(e.g. sorted cells)" |
| m33 | Methods, figures | "matplotlib (v**&nbsp;**3.10.8)" — stray space; "Figma **design**" → "Figma" |
| m34 | Abstract, Results | "**7174**" / "**65000**" / "**4000**" / "**2407**" / "**2234**" — thousands separators used inconsistently |

### 3.2 Style and register (non-scientific wording)

| # | Location | Issue |
|---|---|---|
| m35 | Acknowledgements | The paragraph about the author's sons "intensively playing, crying and fighting around Daniil … asking each day 'when you daddy will complete it?'" is far outside the register of a research journal and also ungrammatical. *(Replaced with a short formal acknowledgement — please confirm, or delete entirely.)* |
| m36 | Results, Figure 5 | "this **supremacy** of biology over batch"; "biological clustering **supremacy**" → "dominance" |
| m37 | Results, Figure 5 | "resulted in a **larger success**"; "mixed **perfectly**" → "was more successful"; "were fully intermixed" |
| m38 | Results, Figure 6 | "they were **rejected by clustermap**" → "were not selected in the clustermap-based assessment" |
| m39 | Results, effect sizes | "**one third of the good harmonization is the method itself**, and one quarter more is the batch pre-selection" |
| m40 | Results, effect sizes | "this analysis **refutes** the common assumption" → "argues against" (a single R² cannot refute) |
| m41 | Results, radar | "**we had the C one** with the highest batch mixing" |
| m42 | Results, expression ranges | "methods returning **exotic** transcriptomic profiles … **failed**" → "atypical … performed poorly" |
| m43 | Discussion, orthogonality | "can simultaneously **fail spectacularly** on kBET and iLISI" → "perform poorly" |
| m44 | Discussion | "This **brute-force** approach proved critical" → "exhaustive" |
| m45 | Introduction, closing | "further advance our abilities to transform the vast amounts of omics data into biological insights, foundation AI models and successful treatment options for cancer patients" — over-claiming |
| m46 | Methods, dataset | "We assembled **the largest possible set** of publicly available cohorts" — unverifiable |
| m47 | Methods, post-removal | "based on the assumption that harmonization can fail in certain cohorts and therefore **they should be removed**" |
| m48 | Results/Discussion | "**significantly**" used non-statistically ("technical batch effects can significantly exceed the biology") |
| m49 | Discussion, subgroups | "may correspond to **the previously unknown** molecular subtypes" — self-contradictory |
| m50 | Discussion, decision tree | "the extensive and **tricky** harmonization was not needed" |

### 3.3 Abbreviations

| # | Issue |
|---|---|
| m51 | **"PCR" is used throughout for "principal component regression."** In a molecular-biology journal PCR means polymerase chain reaction. This is a real comprehension hazard, not a pedantic point — please use "PCReg", "PC regression", or spell it out. *(Not auto-edited: it appears ~30 times and the choice is yours.)* |
| m52 | **cLISI and iLISI are never defined.** They first appear in the Figure 7 legend and again in the Discussion; only "LISI" is defined, in Table 4. Note also that the two axes of Figure 7A/B are on different scales (`clisi_mean_*` vs `ilisi_norm_*` in the deposited data) without comment. |
| m53 | **DSC** is used in the Results text but defined only inside Table 4. |
| m54 | **FSQN** and **QN** appear in Table 1's strategy descriptions ("initial FSQN manual screening", "additional QN manual screening") before either is defined in Table 3. |
| m55 | Not defined at first use: **PCA**, **UMAP** (Uniform Manifold Approximation and Projection), **KNN**, **TPM**, **AUC**, **AI**, **PBMC**, **GEO**, **AWS/S3**, **NGS** (defined, but after first use in Table 1). |
| m56 | "germinal centre (GC)" is defined in the Introduction and **redefined** in the first Results paragraph. |
| m57 | "SOM cohort" — a cohort name that collides with "self-organizing map" elsewhere in the project; worth a clarifying word. |
| m58 | "MNN"/"SVA" are spelled out in the Abstract and abbreviated in the Introduction — fine — but the full forms alternate between "Mutual Nearest **Neighbors**" (Abstract, title) and "Mutual Nearest **Neighbours**" (Introduction). |

### 3.4 Language variant consistency
The manuscript mixes British and American spelling. Counts over the body text: `neighbor` 19 /
`neighbour` 4; `centre` 6 / `center` 4; `colour` 2 / `color` 51; `artefact` 1 / `artifact` 1;
`analyse` 3 / `analyze` 6; `labelled` 1 / `labeled` 0; `t-SNE` 3 / `tSNE` 53. NAR accepts either
variant but requires internal consistency. Note that **the title uses "centre" while the Abstract uses "tumor"** — the two most
visible sentences in the paper disagree. Recommendation: pick British English (OUP house style) and
apply it throughout, including "harmonisation" if you go that way — or keep "harmonization" and
American spelling everywhere and change "centre" → "center". *(Not auto-edited: this is a global
find-and-replace decision that should be made once, by you.)*

Also: "tSNE" should be "t-SNE" (the canonical form; your own alt-text already uses it).

### 3.5 Tool and software naming
| # | Issue |
|---|---|
| m59 | "Claude **code** with models Sonnet 4.8 and 5.0" → "Claude Code with the Claude Sonnet 4.8 and Sonnet 5 models". *(Edited.)* |
| m60 | "**Gemini AI**" → "Google Gemini", and give the model version. *(Partly edited.)* |
| m61 | "**MissForest**" → "missForest" (the R package name is lower-case m). *(Edited.)* |
| m62 | "the python implementation of **Biomart** package version 0.9.2" — the PyPI packages are `biomart` and `pybiomart`; state which, and note that BioMart provides identifier mapping, not probe-set summarisation. Also state the annotation release used for the GPL570 probe→HGNC mapping. |
| m63 | "using the **Genome reference** GRCh38.d1.vd1 and Kallisto" — kallisto indexes a *transcriptome*; give the transcriptome annotation (e.g. GENCODE release) and the kallisto version. Also "Kallisto" → "kallisto" (lower case, per the authors). |
| m64 | "**FoundationOneRNA**" — the Foundation Medicine assay names are FoundationOne®CDx / FoundationOne®Liquid CDx; please give the exact product name. |
| m65 | "**Karpenter**" mis-described — see M33. |
| m66 | Table 3 version column is blank for `24_peer_k10`, `30_recombat`, `38_harman` and `39_procrustes`, and says "no versioned release" for three methods. For reproducibility, give a commit SHA where there is no release. |
| m67 | Table 3's "Implementation failure reason" column contains "RNA-seq-only method" for `22_tmm` and `23_vst`, which are marked "Implementation done = Yes". That is a scope note in a failure column — move it, and note in the legend that these two methods were therefore run on strategy C only (6 of 84 runs). |
| m68 | `25_angel` ("Angel rank-percentile normalization") is listed with "Custom" implementation and no reference. If this is not an established published method, say so explicitly rather than listing it alongside published tools. |

### 3.6 Miscellaneous text points
| # | Issue |
|---|---|
| m69 | Two paragraphs are broken mid-sentence by a hard paragraph break: "…showed higher local ¶ metric values than its 'bad' counterpart", and Supplementary Figure 7's legend "…color annotated by ¶ computational group". |
| m70 | "MATERIALS AND METHODS" — the NAR template heading is "MATERIAL AND METHODS" (singular). *(Edited.)* |
| m71 | "CONCLUSIONS" is not one of NAR's prescribed sections; consider folding it into the Discussion (NAR explicitly permits combining Results and Discussion, which would also suit the block structure of your Discussion). |
| m72 | The 56% PC1 reduction quoted for SVA/FFPE ("from 87.6% raw to 38.4% post-harmonization") appears in no figure or table. Add the supporting data. |
| m73 | "the same 10 harmonizations methods" (see M24) and "87.2 – 100% for the rest strategies": Supplementary File 3 gives 99.72–100% as the per-strategy medians for `21_harmonizr`. If 87.2% is a minimum over individual runs, say so. |
| m74 | The claim that best approaches showed "0.65 – 1.0" global batch overlap and "0.07-0.7" local biology preservation is given without saying which normalised scale these are on. |
| m75 | Figure 7D: "peak values of 0.26 and 1.01" — say which value belongs to which area. |
| m76 | Supplementary File 3's legend says it holds "the 87 scoring metrics"; the file actually has 93 columns (4 design keys + `status` + `compute_time_s` + 87 metrics). Worth stating, since `compute_time_s` is useful. |
| m77 | Conflict of Interest: "where Daniil Nikitin is currently **applying as** PhD student and this article is planned as a part of **articles series** for his PhD thesis" — grammar. *(Edited.)* |
| m78 | The Funding section contains two competing statements, one of them the unfilled template ("[full official funder name] [grant number XXXX to A.B.]"), and the first one ends with a bare "Funding for open access charge:" with nothing after it. Merge into one NAR-formatted statement. |
| m79 | One Cyrillic planning note remains in the Data Availability section ("Не забыть про докер образ для ComboBatch!!!"). It is italicised, so I have left it, but it must be deleted before submission. |
| m80 | A leftover stub reference list of five placeholder entries plus a stale "[NAR EDITOR NOTE] The References list is EMPTY" note sit above the real Mendeley bibliography, which is present and complete (95 entries). Delete the stubs and the note. *(Not edited — you asked me not to touch references.)* |
| m81 | Also for your later reference pass: bibliography entries 10, 87, 90 and 91 do not appear to be cited in the text. |

---

## 4. Statistics and methodology — consolidated verdict

**What is sound.** The four-factor factorial design is the right design. Polarity-normalising metrics
before aggregation is the right instinct. Reporting failure modes (timeouts, non-convergence,
unimplementable methods) is better practice than most benchmarks manage. Using both global and local
metric families, and demonstrating their near-orthogonality, is the paper's best methodological
contribution — and the *ordering* method > strategy > imputation > post-removal does reproduce from
the deposited data, which is reassuring for the paper's main practical message.

**What must be fixed before the statistics can be believed.**

1. **Definitional (§1.1).** The direction of PCR must be stated correctly and consistently, and the
   mixture of inverted (PCR) and non-inverted (per-PC R²) conventions must be made explicit.
2. **The response variable is not comparable across the design (§1.6).** Averaging 67 metrics for one
   strategy and 87 for another and then ranking them is not valid. This is the most serious purely
   statistical problem in the paper, and it biases in favour of the strategies the paper recommends.
3. **The design is unbalanced and the imbalance is not modelled (§1.7).** Methods with 6–34 of 84
   runs are ranked against methods with 84. AMDBNorm — recommended to readers — has 14 runs and a
   global metric pinned at exactly 1.000.
4. **The "variance decomposition" is a set of four marginal effect sizes (§1.8).** It cannot support
   statements about relative contribution without a joint model, and the notation (R² vs η²) is
   inconsistent between text and figure.
5. **Pseudo-replication (M13).** 2,234 approaches are not 2,234 independent observations; they are
   repeated analyses of 42 overlapping sample subsets. Every p-value in the paper is inflated by this.
   Test at the level of the independent units, or state the limitation prominently.
6. **Stochastic metrics without seeds or replicates (M2).** 14 of the 87 metrics live in UMAP/t-SNE
   space. Differences of 0.01–0.05 in those metrics are load-bearing for several conclusions.
7. **No control experiment (M11).** A label-permutation negative control and a cross-cohort
   classification positive control would convert the central claim from "the embeddings look right"
   into a measured result. I would regard this as the difference between a descriptive benchmark and
   a definitive one.
8. **Effect sizes are missing throughout (M13–M15).** Report medians with CIs, or rank-biserial
   correlations for the Mann–Whitney comparisons.
9. **Min–max scaling without outlier handling (M10).**
10. **Arbitrary, untested neighbourhood parameters (M12).**

**On the biological claim.** The two FL transcriptional subgroups seen only under SVA + imputation are
presented cautiously, which is appropriate. But as written the finding is indistinguishable from an
imputation artefact — the same low-rank machinery that the manuscript itself reports introducing
spurious *trimodal* expression distributions in 14 cohorts. Before this is offered as a biological
result, it needs at minimum: (i) reproducibility across both imputation methods and across random
seeds, (ii) the subgroup-defining genes, and (iii) a check that they are not enriched for genes with
high missingness. Alternatively, present it purely as a hypothesis-generating observation and drop
"biologically significant finding" and "may correspond to … molecular subtypes".

---

## 5. Figures, tables and supplementary material

### 5.1 Format compliance (NAR Part 6)

| Requirement | Status |
|---|---|
| Preferred TIFF/EPS; **avoid JPG** | **Fail.** `Figure 3.jpg` is supplied (JPEG, 3040 × 4490, 72 dpi metadata ≈ 288 dpi at final size — also just under the 300 dpi minimum). Figures 4 and 5 are supplied as both PDF and PNG. |
| One master file per figure | **Fail.** Figure 3 exists as `.pdf` and `.jpg`; Figures 4 and 5 as `.pdf` and `.png`, **and the PNG and PDF versions have different aspect ratios** (Figure 4: PNG 1.53 vs PDF 0.66; Figure 5: PNG 1.39 vs PDF 0.72), so at least one of each pair is out of date. Resolve which is canonical. |
| Colour supplied as **CMYK** | **Fail.** Every figure PDF is DeviceRGB/ICCBased. |
| **Embed all fonts**; one sans-serif family throughout | **Fail.** Every figure PDF uses **Type 3 fonts with no embedded FontFile**. No `/BaseFont` name is recoverable, so the "single sans-serif font" requirement cannot even be verified, and OUP production may not accept them. Consequence I could measure: text extraction is corrupted — Figure 1's "log₂(x+1)" comes out as "log‡(x+1)" and its arrows as "‚"/"ﬁ". That also means **screen readers cannot read the figures**, which conflicts with the accessibility requirement the alt text is meant to satisfy. Re-export with `matplotlib.rcParams["pdf.fonttype"] = 42` (as your own project convention specifies) and with fonts embedded from Figma. |
| Max width 17.35 cm, max height 23.35 cm | **Fail for all 37 figures** — see 5.2. |
| Colour-blind-safe; meaning not carried by colour alone | **Fail** for Figure 3 (red–green metric-score scale) and Figure 9A; please check the remainder against a deuteranopia simulation. |
| `Alt text:` under every legend | **Pass** for Figures 1–9. **Missing for the Graphical Abstract and for all 17 Supplementary Figures.** |
| Every figure numbered and cited | **Pass** for Figures 1–9, Tables 1–5, Supplementary Figures 1–17, Supplementary Files 1–4. **Fail** for the 10 "Extended Figure" files — see 5.4. |
| Graphical Abstract: 5:2 landscape, ≥127 × 50 mm, **original**, sans-serif 12–16 pt, no logos | **Partly fail.** Size 267 × 103 mm ✓ (ratio 2.59, should be 2.50). Font: median 15 pt ✓ but the 5th percentile is 9.3 pt, below the 12 pt floor. **Originality: the t-SNE panels appear to be reused from Figures 4/5 — NAR requires the Graphical Abstract not be a copy of any main or supplementary figure.** Please also confirm the provenance of the tube/slide/array icons (if BioRender, a journal-specific licence and acknowledgement are required). |

### 5.2 Legibility at final print size

Scale factor = min(17.35/width, 23.35/height). "%<5 pt" is the fraction of text spans that fall below
5 pt after scaling.

| Figure | drawn size (cm) | scale | median pt after scaling | %<5 pt |
|---|---|---|---|---|
| **Figure 3** | 39.6 × 26.8 | **0.44** | **4.4** | **100%** |
| **Supplementary Figure 7** | 27.1 × 40.9 | 0.57 | **3.0** | **81%** |
| **Supplementary Figures 2, 3, 4** | ~28 × 41 | 0.57 | **4.5** | **100%** |
| Extended Figure 2 | 26.9 × 40.7 | 0.57 | 5.7 | 49% |
| Figure 2 | 27.2 × 41.1 | 0.57 | 5.7 | 27% |
| Extended Figure 6 | 26.9 × 40.9 | 0.57 | 5.7 | 26% |
| Figure 6 | 28.7 × 26.5 | 0.61 | 6.1 | 22% |
| Figure 4 | 26.6 × 40.6 | 0.58 | 5.8 | 14% |
| Extended Figure 3 | 27.4 × 40.4 | 0.58 | 5.8 | 11% |
| Figures 1, 5, 7, 8, 9 | 26.6–28.3 × 23.0–41.1 | 0.57–0.65 | 5.7–6.5 | 0–5% |
| Supplementary Figures 1, 5–6, 8–17 | 24.6–26.9 × 18.6–38.3 | 0.57–0.67 | 5.2–6.7 | 0% |

Even the "0%" rows sit at 5.2–6.7 pt, which is at or below the practical floor for print. **Every
figure needs to be re-laid out for a 17.35 cm canvas**, not scaled down from a 27 cm one. The
portrait figures at ~41 cm tall are 1.75× the maximum page height and will be reduced twice over.

### 5.3 Figure-specific content comments
- **Figure 3.** Rotated 90° (all text sideways). Axes described backwards in the legend (§1.10).
  Red–green palette (§1.9). The metric-group legend includes group **K**, which is absent from
  Table 4 (M7). The method colour legend appears to list 32 swatches (31 methods + "Best") — please
  confirm ARSyN and Harman are intentionally absent (§1.2). The "Good/Bad" cluster labels are set in
  italic serif while everything else is sans — inconsistent with the single-font requirement.
- **Figure 6.** Also rotated 90°. Panel C's two heatmaps share one y-axis label ("Harmonization
  method") but have separate colour bars with different scales and no panel sub-letters; consider
  labelling them C(i)/C(ii). The "Best" composite row is marked with a black cell and an exclamation
  mark on the harshness annotation — explain that glyph in the legend (NAR requires symbols to be
  explained).
- **Figure 9.** Panels C and D (the radar plots) have **no colour legend at all**, so the reader
  cannot map a line to a method (C) or a strategy (D). The axis labels differ between the two panels
  that plot the same six axes ("Global batch" vs "Global batch mixing", "Local biology" vs "Local
  biology separation"). Panel B's axis says η² while the text says R² (§1.8). Panel E's metric-type
  names ("Local neighborhood / Global distance / Distribution similarity / Other") do not match the
  four names used in Methods ("global intersection / local mixing / distributional similarity /
  other") — pick one vocabulary and use it in Methods, Figure 3 and Figure 9E. *(Methods edited to
  match the figures.)*
- **Figure 1.** Panel B appears to label 10 of the 15 diagnosis categories present in Supplementary
  File 1 (GC, MZ, Immature, Plasmablast and High-grade B-cell lymphoma are not visible in the text
  layer). Please confirm all groups are represented, and see M17.
- **Table 3** is the largest table (40 rows × 7 columns) and would sit better in the supplement, as
  your own italic note suggests. Same for Table 4. NAR requires editable Word tables with no shading
  and units in headers — Tables 1–5 satisfy the editable-Word requirement.

### 5.4 Supplementary material compliance (NAR Part 11)
- **File count and size.** NAR permits **one combined PDF**, or otherwise **at most 10 files, each
  ≤ 2 MB**. The current set is **32 files**: 17 Supplementary Figures, 10 Extended Figures,
  4 Supplementary Files, and `Harmonization_metrics_extended.docx`. Four exceed 2 MB
  (Supplementary Figure 9 at **8.37 MB**; Supplementary Figures 2, 3, 4 at ~4.4 MB). **Combine into a
  single PDF** (plus the CSVs, which can be one Excel workbook with one sheet per table, per the
  guidelines).
- **The 10 "Extended Figure" files are cited nowhere in the manuscript**, and NAR has no "Extended
  Figure" category. Either fold them into the Supplementary Figure sequence and cite each one in the
  text, or drop them.
- **`Harmonization_metrics_extended.docx`** is likewise uncited; the manuscript instead promises this
  content as a markdown file in a GitHub repository (italic placeholder). Decide on one location —
  and note that GitHub alone does not satisfy NAR's archiving policy (below).
- **Supplementary Figure legends have no `Alt text:` lines.**
- **Supplementary File 4** has no file extension (it is a CSV). Filenames must be self-explanatory;
  rename to `Supplementary File 4.csv`.
- **Supplementary File 2** row count does not match the dataset (§1.12).

### 5.5 Document formatting against the NAR template (Part 1)
| Requirement | Measured | Status |
|---|---|---|
| A4 (21.0 × 29.7 cm) | **21.59 × 27.94 cm (US Letter)** | Fail |
| 1-inch margins | 2.54 cm all round | Pass |
| Body 11 pt, 1.15 line spacing, ~10 pt after | `Normal` = Times New Roman, no explicit size, **line spacing 1.0, no space-after** | Fail — the manuscript is not in the NAR template |
| Continuous line numbers for the review copy | **absent** | Fail (recommended) |
| Page numbers | **no header/footer part in the document at all** | Fail |
| Abstract ≤ 200 words, one paragraph, no refs/figures/URLs | **199 words**, one paragraph, no citations or URLs | Pass (but with 1 word of headroom — my Abstract edit is net −1 word) |
| Top-level headings ALL CAPS bold | Pass | Pass |
| Title free of non-standard abbreviations | Pass — MNN and SVA are spelled out (the `[NAR EDITOR NOTE]` about this is stale and can be deleted) | Pass |

### 5.6 Data availability (NAR Part 8) — mandatory, currently non-compliant
- **GitHub is explicitly *not* an acceptable primary archive** (no permanent DOI). The statement
  currently points to GitHub for the pipeline, the ComboBatch tool, the extended metrics document and
  the containerised Shambhala. The sentence "All the repositories are available for peer review and
  archived with a permanent DOI at Zenodo" asserts the DOI but gives none. **Mint the Zenodo DOIs and
  cite them.**
- The statement refers to "**Supplementary Table 1**" for accession numbers; the manuscript has
  **Supplementary File 1**. Also, that file's accession column is `PUBLIC_REPOSITORY_ID` — please
  confirm it is complete for all 88 cohorts, since NAR requires GEO/ArrayExpress/SRA accessions for
  every reused dataset. *(Reference edited to "Supplementary File 1".)*
- **MIAME/MINSEQE compliance is not stated.** Required for reused microarray and sequencing data.
- The question raised in your own italic note — whether ~2,000 datasets of ~1 GB can be deposited —
  has a practical answer worth stating in the manuscript: deposit the 87-metric table, the polarity
  table, the per-strategy gene lists, and the harmonized matrices for the **eight best approaches
  only**, with the pipeline and a container image sufficient to regenerate the rest. That is
  defensible and finite.
- Software requirements not yet met: installation instructions, a manual, a worked usage example, and
  sample input/output must accompany the deposited code.
- Ethics: the "publicly available, de-identified data, no new human data" statement is present and
  appropriate. ✓

### 5.7 Other back-matter
- **Author Contributions** uses CRediT correctly and covers seven authors — but the byline lists nine
  names (several with "?" markers) including one that appears to be a database, not a person.
  The two lists must match, and every author needs an affiliation superscript and, ideally, an ORCID.
- **Conflict of Interest** is present and substantive. ✓
- **AI disclosure** is present in Methods and Acknowledgements. ✓ Well done — this is more thorough
  than most submissions. Note the guidelines also ask for disclosure in the cover letter.

---

## 6. Recommendation

**Major revision.** The dataset and the design are strong enough to support a valuable paper, and most
of what I have flagged is reporting and analysis discipline rather than lost work. The four things
that would most change my assessment, in order:

1. Fix the PCR definition and re-read the metrics section against it (§1.1).
2. Make the composite score comparable across strategies, and re-derive the rankings and Figure 9B on
   a coverage-balanced subset with a stated model (§1.6–1.8).
3. Reconcile every count — methods, approaches, metrics, samples — and deposit a Supplementary File 3
   from which every number in the paper can be recomputed (§1.2–1.5, §1.12).
4. Add a label-permutation control and a cross-cohort classification check (M11), and re-lay out the
   figures for a 17.35 cm canvas with embedded fonts and a colour-blind-safe palette (§1.9, §5.1–5.2).

---

## Appendix — verification method

All numeric cross-checks were computed directly from the submitted files, not taken from the
manuscript:

- Manuscript body, tables and legends extracted from `FL_harmonization_article_NAR.docx` via the
  OOXML body (`python-docx` + `lxml`), with italic runs flagged so that placeholder text could be
  excluded as requested.
- `Supplementary File 3.csv.gz` (2,407 rows × 93 columns) and `Supplementary File 4` (165 metrics)
  loaded with pandas; composite score reconstructed as the mean of min–max-scaled, polarity-flipped
  metric values; effect sizes via one-way OLS (`statsmodels`); correlations via `scipy.stats.spearmanr`.
- `Supplementary File 1` (7,174 rows) used to verify the diagnosis, batch and cohort counts and the
  strategy D sample number.
- Figure PDFs inspected with PyMuPDF for page geometry, font subtype/embedding, colour space, raster
  count, and per-span font sizes; the legibility table applies NAR's 17.35 × 23.35 cm limit.
  Figure text layers were searched for all 33 method labels to establish which methods appear in
  which figure.
- Document geometry, style, abstract word count and spelling-variant counts measured from the
  `.docx` directly.
