# Daniil's review principles — inferred from his 37 comments and 71 edited paragraphs, 2026-09-24

This document is the **standard** against which the unreviewed half of
`FL_metric_classes_F1000_260917.docx` must be brought. It is derived entirely from two
sources, and every rule below cites the comment or the edit that establishes it:

- `daniil_comments_260924.md` — 37 Word comments (C2 … C74)
- `daniil_diff_260924.md` — 61 rewritten and 10 inserted paragraphs

Daniil reviewed **paragraphs 0–77 and 149–160** of 178, which is the front matter, Methods,
the first five Results sub-sections, and the Supplementary Material legends. **Paragraphs
78–148 are untouched**: `Cross-batch prediction elects a third set…` (53 paragraphs), `The
sets elected by the individual metric classes…` (8), `Conclusions` (6), and the back matter.
Those sections must be edited to the rules below without further instruction.

Where a rule is stated as *evidence*, it was inferred from what he silently changed, not from
an explicit instruction; those are marked **(inferred)** and carry slightly less authority than
a quoted comment.

---

## A. Evidence and provenance

**A1. Every named entity is named.**
A sentence may not refer to "an approach", "two methods", "some strategies" without saying
which. C2, C3, C8, C9 are four separate comments making this one demand, twice in the Abstract
and twice in the Introduction: *"What is this approach? This is important, add here and in the
main article"*, *"Which ones?"*.

**A2. Every claim of difference carries a test.**
C21: *"all the quantitative hypothesis testings should be statistically justified, by tests
appropriate or by bootstrap."* C25: *"For paired comparisons of medians here and below please
add Mann-Whitney p-values, raw and two-sided."* C40, on a sentence that asserted a
non-separation: *"Prove this statement with a statistical test, use Mann-Whitney."*
Consequences: two-group median comparison → Mann-Whitney U, two-sided, raw (uncorrected) p;
three or more groups → Kruskal-Wallis H; monotone association → Spearman.

**A3. Every scatterplot relationship carries ρ and p.**
C31: *"Add Spearman R and p-value here and everywhere else where the text describes dependency
between metrics at scatterplot."* This applies to every sentence that reads a trend off a
panel, not only where a coefficient already appears.

**A4. Every proportion carries its baseline.**
C28, on "98.5% returned a kBET acceptance rate under 0.1": *"What is this percentage for all
approaches? Add this number as a baseline here."* A subset statistic without the
all-approaches figure beside it is not interpretable.

**A5. Every dispersion is named.**
C42: *"How was the variance measured? Standard deviation? Specify this here and everywhere as
applicable."* "Varying by 0.017" is incomplete; the statistic (SD, MAD, range, IQR) must be
stated.

**A6. Every comparative has an explicit comparator.**
C43, on "the 18 biology columns separate approaches weakly": *"Weakly compared to what? Compare
them to the batch columns."*

**A7. Every metric has a precise name and a stated computation.**
C17, on "the worst multiclass fold": *"What is this metric? Please describe its precise name and
how it was calculated."*

**A8. Every statistical method and every software package is cited.**
C20: *"Search for the initial publication introducing a certain statistical method, and for the
official python module link in case of modules. Add the citation numbers here and to the md
documents for references."* Kruskal-Wallis, Mann-Whitney, Spearman, bootstrap, logistic
regression, PCA — and pandas, numpy, scipy, scikit-learn, statsmodels, matplotlib, seaborn.

---

## B. Figures, panels and supplementary material

**B1. Figure numbers follow order of first citation, with no gaps.**
C29: *"You are citing Supplementary Figure 6 immediately after Supplementary Figure 1, and no
Supplementary Figures 2-5 are cited. Please align figure naming (both main and supplementary)
with the text — change both the text and the figures, so both of these parts are changed in a
minimal but sufficient level. Do this for the entire text and all the figures."*
Note the constraint: **minimal but sufficient** — renumber, do not redesign.

**B2. Every panel is cited and described individually.**
C30: *"Some panels from Supplementary Figure 3 are not cited anywhere in the document, for
example the panels F and G. Please conduct an extensive review of the document to find all such
cases (for all the figures) and for all of these add the citations and descriptions."* Repeated
at C38 (Supplementary Figure 5E–L), C41 (*"Cite and discuss each individual panel, as I
requested previously"*), and C74.

**B3. Missing panel prose comes from the extended document first.**
C30, C33, C38, C73 all name `Harmonization_metrics_extended_260920_v3` as the source to lift
descriptions from, and C33 adds the condition: *"Align the pasted text with the surrounding
passages, so the main message goes smoothly and clear."* Where the extended document has
nothing, write it (C30: *"if they are missing there — add them yourself"*).

**B4. Supplementary legends are full legends, panel by panel.**
C73: *"Please add the analogous ones for the rest supplementary figures and tables, and remove
the short descriptions you added — they are insufficient."* He pasted ten model legends
(Supplementary Figures 1–10) into the document; they are the template. Each names every panel
letter, says what is plotted on each axis, what the colour annotation encodes, what the error
bars are, and how the clustermap-best group is marked.

**B5. Figure geometry is a first-class requirement.**
C50: panels must fit the reference frame, be reduced by a factor of 1.5–2, and wide panels
must be narrowed to sit two per row. C44: a one-row strip of seven plots becomes a 3×3 or 3×4
grid; overlapping x tick labels are a defect; `p=1.4e-9` must be typeset as p = 1.4 × 10⁻⁹ to
match the text.

**B6. Related panels are consolidated into one coherent figure.**
C35: *"Combine all the individual principal component analysis to a separate picture so the
figure and panel naming is consistent and logical."*

---

## C. What belongs in which section

**C1. The Abstract carries findings, not mechanism-of-analysis detail.**
C4 and C10, on the single-class-fold sentence: *"Move this to Results and discussion and discuss
there, it's a technical finding, not worth noting in the Abstract."*

**C2. The Introduction previews the major results in 2–3 sentences.**
C7: *"For the results description in Introduction, please add 2-3 sentences more explaining the
major results — including the differences between harmonization methods and strategies by each
metric class."*

**C3. Dense numeric passages become tables; the text keeps the qualitative result and its
mechanism.**
C45: *"There are too many numbers in this text. Please create a separate table in the text,
Table 1, and put the mean numbers for the selected metrics by harshness tiers there. Add there
also a statistic and p-value. Retain only the qualitative results in the text, add a conclusion
about why low/high harshness methods have certain metrics lower/higher."*
C46: *"Move these numbers by metric to supplementary tables, no need to overcomplicate the text
here with them."*

**C4. Superseded intermediate calculations leave the main text.**
C47: *"Put both variants of the LOBO metrics (with or without single class batches) into the
table, remove this technical part from the main text."* The paragraph explaining that an
earlier calculation gave H = 11.2 and now gives H = 11.8 is exactly the kind of audit trail that
belongs in a supplementary table, not in Results.

**C5. Methods statements about the writing process are deleted. (inferred)**
The Statistics paragraph lost *"These two are the only inferential procedures in
analysis/article2_generalizability.py: we compute no confidence interval… run no two-group
test"* and *"Every number quoted below is produced by analysis/article2_generalizability.py
from the pinned metric snapshot…"*. AI usage lost *"Every number in this article was recomputed
from the deposited tables by a gate script… and every citation was independently re-resolved…"*.
The defensive provenance narration reads as an internal QA log, and he cut all of it.

---

## D. Prose register

**D1. Each Results paragraph opens with what we did. (inferred)**
Systematic across the diff:
"We began from the two metric families" → **"We started the analysis from"**;
"On the fraction of cohort pairs" → **"We further deeply compared metrics of distributional
similarity between harmonization approaches. On the fraction…"**;
"The equally weighted composite of all 87 metrics ranked" → **"We also calculated and compared a
composite score, which was…"**;
"The harshness tiers can be compared on the raw biology-facing columns" → **"We then compared
the biology related metrics of classes L, M and N between the harshness groups"**.
Six such openings were added where the agentic text began with the result.

**D2. Each Results sub-section closes with an interpretive takeaway. (inferred)**
He added five closing paragraphs that did not exist, each beginning "Taking together" / "Taken
together" / "The initial screening … showed that", and each stating a consequence **for
benchmarking practice**, not a restatement of the numbers:

> "Taking together, global metrics in-depth analysis showed that global metrics form a weak,
> permissive criterion of harmonization quality. Both biology and batch PCReg should be
> measured, and other metric classes should be added to evaluate harmonization quality robustly."

> "Taking together, the in-depth analysis of local metrics showed that reaching the maximum of
> one local metric is not sufficient for the clustermap best selection. … a robust harmonization
> quality benchmarking pipeline should treat local metrics as necessary but not sufficient."

**D3. A reported number is followed by its mechanism. (inferred)**
"which is part of why their biology PCReg is high" → **"potentially explaining their high PCReg
by biology"**; "which its pre-quantile-normalized constituent cohort accounts for" →
**"presumably because the already quantile-normalized SOM cohort makes up a larger share"**;
"…under FFPE-only" → **"proving that feature-specific quantile normalization performs poorly in
a cross-platform FFPE-only dataset"**. He also supplies the missing mechanism himself where the
draft only reported: he added the four malignant class names (DLBCL, FL, Burkitt lymphoma, High
grade B-cell lymphoma) to explain a PCReg value.

**D4. No aphorism, no antithesis, no self-reference. (inferred)**
Deleted outright: *"A benchmark that reports one metric class reports one election."*
*"The three families ordered the same set of approaches differently. The rest of this article
makes that observation quantitative."* *"A global metric sitting at its theoretical optimum
therefore carries two readings at once."* *"Reaching the maximum of one local metric is
therefore not sufficient for selection either."* *"None of the 87 metrics above reads the
expression of a gene that anyone would act on."* *"Saturation is what makes these values hard
to read."*
Each was replaced by a plain declarative, and in three cases by a "Taking together" paragraph
that says the same thing as a finding rather than as an epigram. This is the same rule the
workflow already enforces as "no antithesis", extended to aphorism and to sentences about the
article itself.

**D5. Three significant digits.**
C26: *"Please use the three digits conventions for all the metrics, 4 ones is too much. Change
the numbers here and below accordingly."* So 0.7334 → 0.733, 1.0000 → 1.000, 0.0178 → 0.018.
Counts, percentages with a natural precision, and p-values in scientific notation are exempt.

**D6. Abbreviations are defined at first use and then used. (inferred + C32)**
C32: *"Replace by KNN abbreviation here and below."* He added at first use: NGS, PCA, SVA, MAD,
AUC, KNN, GC. The rule is both halves — define it, then stop spelling it out.

**D7. American spelling. (inferred)**
neighbourhood → neighborhood, colour → color, tumour → tumor, neighbour → neighbor,
behaviour → behavior. (He left "germinal-centre" in one clause; that is an oversight to fix,
not a counter-example.)

**D8. Citations are author–year, not numeric. (inferred, and the largest single change)**
Every `[1]`…`[52]` became `(Leek et al. 2010)`, `(Borisov and Buzdin 2022)`,
`(Nikitin et al. 2026 Sep 17)`. The source benchmark is always cited by that last form.

**D9. "Elected" is reserved for the set-election concept. (inferred)**
"Each class elected its top 112" → **"Each class resulted in top 112 approaches"**; "Class N
elected the ComBat family" → **"Class N resulted in the ComBat family"**. He keeps "elected" only
where the noun "elected set" is the object of study.

---

## E. Analysis changes he ordered

These are not style; they change numbers and figures.

**E1. The generalizability index must use F1 for both LOBO targets.**
C16: *"Why have you taken F1 for the three classes LOBO and AUC for the two classes one? It's
illogical, they are not comparable. Take F1 for both 3 and 2 class LOBO and recalculate the
generalizability and biology preservation index, rewrite the text and redraw the figma figures
where appropriate."* `pv_lobo2_f1_macro_mean` exists in the pinned snapshot, so this is a
substitution, not a new computation.

**E2. New panels: L/M/N scatterplots and an all-metric cross-correlation clustermap.**
C48: scatterplots between L, M and N metrics coloured by method or strategy, in the style of
Figure 1A/1B; and *"a clustermap of all metrics cross-correlations, taking all 334 ones excluding
the metadata — with colour annotations indicating metrics type, group and class"*, in the style
of Article 1's Supplementary Figure 7.

**E3. Supplementary Figure 12 is rebuilt.**
C44: 3×3 or 3×4 grid; add the permutation-null background for the N metrics; add both F1 and AUC
for both LOBO2 and LOBO3; add same- and different-biology cross-batch agreement; one panel letter
per plot, each cited and discussed; remove the H statistic from the panel; state the test and the
p-value derivation in the legend.

**E4. A new Table 1 in the main text.**
C45: mean values of the selected metrics by harshness tier, with the statistic and the p-value,
replacing the numeric block in the text.

**E5. Expression scatterplots move to supplementary and gain method coverage.**
C50: *"Move all the expression scatterplots to supplementary, remove the raw plots — they are
just 1 to 1 lines, nothing interesting. Add more different methods for these scatterplots, so we
can see linear and non-linear methods and how do they transform expression."*

**E6. Supplementary File placeholders must resolve.**
C14 and C15 both mark `Supplementary File X`: one needs the file describing the metric-class
assignment, one the file of average percentiles — *"if there is no such file — create it and
align with the rest ones."*

---

## F. Defects introduced by the edits themselves

Recorded here because the plan must fix them, and because they are not Daniil's principles but
slips made while applying them at speed.

| # | Defect | Where |
|---|---|---|
| F1 | **334 vs 344.** The new title says "334 harmonization quality metrics"; the Introduction says "344 quality metrics"; C48 says "all 334 ones". The pinned snapshot `metrics_comprehensive_260905.csv` has **329 columns**, of which 4 are keys and 5 are status flags. None of the three numbers reproduces. | Title, Introduction, C48 |
| F2 | The body still says "87 polarity-adjusted scoring metrics" in five places, so the article now carries two different metric totals with no sentence reconciling them. | Methods, Results |
| F3 | The sentence C47 asks to remove ("An earlier calculation of the multiclass-only test…") is still in the edited copy. | Harshness paragraph |
| F4 | "An early 2021 empirical comparison" cites `(Rudy and Valafar 2011)`. | Introduction |
| F5 | Typos: "mnatrix", "appricase", "generatability", "2,234 appricase". | Results |
| F6 | The author list dropped from 12 to 2, but Author contributions, Competing interests and Acknowledgements still describe the 12-author team. | Back matter |
| F7 | The Shambhala two-names paragraph was compressed to one sentence that no longer states the 2,234-vs-2,150 consequence, although the rename is still load-bearing for every count in the article. | Methods |
| F8 | New citations were introduced without reference-list entries: Jovčevska et al. 2019, Sorokin et al. 2020, Risso et al. 2014, Kapoor and Narayanan 2023, Saeb et al. 2017, Whalen et al. 2021, Ambroise and McLachlan 2002, Varma and Simon 2006, Soneson et al. 2014, Parker and Leek 2012, Fiore et al. 2025. | Introduction |

---

## G. The checklist, for the unreviewed sections

A paragraph in `Cross-batch prediction elects a third set…`, `The sets elected by the individual
metric classes…` or `Conclusions` is finished when all of these hold:

- [ ] It opens by saying what was done, not by stating the result (**D1**)
- [ ] Every approach, method and strategy it mentions is named (**A1**)
- [ ] Every difference it asserts carries a test and a two-sided raw p (**A2**)
- [ ] Every trend read off a scatterplot carries ρ and p (**A3**)
- [ ] Every proportion carries the all-approaches baseline (**A4**)
- [ ] Every dispersion names its statistic (**A5**)
- [ ] Every comparative names its comparator (**A6**)
- [ ] Every number is at three significant digits (**D5**)
- [ ] Every figure panel it cites exists, and every panel of every figure it cites is discussed
      somewhere (**B1, B2**)
- [ ] Citations are author–year (**D8**)
- [ ] No aphorism, no antithesis, no sentence about the article itself (**D4**)
- [ ] Numeric blocks longer than three values are in a table (**C3**)
- [ ] The sub-section ends with a "Taken together" paragraph stating the consequence for
      benchmarking practice (**D2**)
