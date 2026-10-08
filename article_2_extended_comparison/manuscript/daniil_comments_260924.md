# Daniil's comments on the Article 2 manuscript — extracted 2026-09-24

Source: `manuscript/FL_metric_classes_F1000_260917_edited_Daniil.docx`. **37 comments**, all by Daniil Nikitin.

Comments are listed in document order. *Anchor* is the exact span the comment
is attached to, collected between Word's commentRangeStart/End sentinels, so
comments sharing a paragraph stay distinguishable. It is quoted from Daniil's
edited copy, so it already reflects any manual rewriting of that sentence.
The page is approximate
(~13 body paragraphs per page).


## Abstract

### C2 — p. ~1 (Daniil Nikitin, 2026-09-20)

**Anchor:**

> approach

**Comment:**

> What is this approach? This is important, add here and in the main article

### C3 — p. ~1 (Daniil Nikitin, 2026-09-20)

**Anchor:**

> two methods

**Comment:**

> Which ones?

### C4 — p. ~1 (Daniil Nikitin, 2026-09-20)

**Anchor:**

> Of the 32,746 three-class LOBO folds, 15,436 (47.1%) carried one class and reached a median macro F1 of 0.903, against 0.7334 on the rest.

**Comment:**

> Move this to Results and discussion and discuss there, its technical finding, not worth noting in the Abstract.


## Introduction

### C6 — p. ~2 (Daniil Nikitin, 2026-09-20)

**Anchor:**

> cell-of-origin assignment reinvention for formalin-fixed paraffin-embedded

**Comment:**

> Very nice pivot in the introduction, thank you! No action needed.

### C7 — p. ~2 (Daniil Nikitin, 2026-09-21)

**Anchor:**

> Local and composite metrics resulted

**Comment:**

> For the results description in Introduction, please add 2-3 sentences more explaining the major results - including the differences between harmonization methods and strategies by each metric class.

### C8 — p. ~2 (Daniil Nikitin, 2026-09-20)

**Anchor:**

> approach

**Comment:**

> What is this approach? This is important, add here and in the main article

### C9 — p. ~2 (Daniil Nikitin, 2026-09-20)

**Anchor:**

> two methods

**Comment:**

> Which ones?

### C10 — p. ~2 (Daniil Nikitin, 2026-09-20)

**Anchor:**

> Of the 32,746 three-class LOBO folds, 15,436 (47.1%) carried one class and reached a median macro F1 of 0.903, against 0.7334 on the rest.

**Comment:**

> Move this to Results and discussion and discuss there, its technical finding, not worth noting in the Abstract.


## Metric classes and the best approaches selection procedure

### C14 — p. ~2 (Daniil Nikitin, 2026-09-21)

**Anchor:**

> (Supplementary File X)

**Comment:**

> Add here the link to the proper supplementary file describing the class assignment

### C15 — p. ~2 (Daniil Nikitin, 2026-09-21)

**Anchor:**

> Supplementary File X

**Comment:**

> Add here the link to the proper supplementary file with average percentiles, if there is no such file - create it and align with the rest ones.

### C16 — p. ~2 (Daniil Nikitin, 2026-09-21)

**Anchor:**

> the full and multiclass-only LOBO three-class macro F1, the two-class LOBO macro area under the curve (AUC),

**Comment:**

> Why have you taken F1 for the three classes LOBO and AUC for the two classes one? Its illogical, they are not comparable. Take F1 for both 3 and 2 class LOBO and recalculate the generalizability and biology preservation index, rewrite the text and redraw the figma figures where appropriate.

### C17 — p. ~2 (Daniil Nikitin, 2026-09-21)

**Anchor:**

> worst multiclass fold

**Comment:**

> What is this metric? Please describe its precise name and how it was calculate.


## Statistics and software

### C20 — p. ~3 (Daniil Nikitin, 2026-09-21)

**Anchor:**

> Kruskal-Wallis H test

**Comment:**

> All the supporting references for all of statistical methods and packages listed here. Search for the initial publication introducing a certain statistical method, and for the official python module link in case of modules. Add the citation numbers here and to the md documents for references.

### C21 — p. ~3 (Daniil Nikitin, 2026-09-21)

**Anchor:**

> as their ranges and medians

**Comment:**

> If you are comparing medians between certain groups, use Mann-Whitney test. In general, all the quantitative hypothesis testings should be statistically justified, by tests appropriate or by bootstrap.


## Metric classes capture non-overlapping components of harmonization quality

### C25 — p. ~3 (Daniil Nikitin, 2026-09-21)

**Anchor:**

> 0.820 (MAD 0.063) against 0.802

**Comment:**

> For paired comparisons of medians here and below please add Mann-Whitney p-values, raw and two-sided.

### C26 — p. ~3 (Daniil Nikitin, 2026-09-21)

**Anchor:**

> 0000

**Comment:**

> Please use the three digits conventions for all the metrics, 4 ones is too much. Change the numbers here and below accordingly.


## Global variance-based metrics saturate below the threshold of biological preservation

### C28 — p. ~4 (Daniil Nikitin, 2026-09-22)

**Anchor:**

> ), 98.5% returned a kBET acceptance rate under 0.1

**Comment:**

> What is this percentage for  all approaches? Add this number as a baseline here.

### C29 — p. ~4 (Daniil Nikitin, 2026-09-22)

**Anchor:**

> Supplementary Figure 6E

**Comment:**

> You are citing Supplementary Figure 6 immediately after Supplementary Figure 1, and no Supplementary Figures 2-5 are cited. Please align figure naming (both main and supplementary) with the text - change both the text and the figures, so both of these parts are changed in a minimal but sufficient level. Do this for the entire text and all the figures.

### C30 — p. ~4 (Daniil Nikitin, 2026-09-22)

**Anchor:**

> Supplementary Figure 3D

**Comment:**

> Some panels from Supplementary Figure 3 are not cited anywhere in the document, for example the panels F and G. Please conduct and extensive review of the document to find all such cases (for all the figures) and for all of these add the citations and descriptions of these panels - take them from the initial Extended metrics comparison document, if they are missing there - add them yourself.

### C31 — p. ~4 (Daniil Nikitin, 2026-09-22)

**Anchor:**

> in a noisy manner

**Comment:**

> Add Spearman R and p-value here and everywhere else where the text describes dependency between metrics at scatterplot.

### C32 — p. ~4 (Daniil Nikitin, 2026-09-23)

**Anchor:**

> k-nearest-neighbour

**Comment:**

> Replace by KNN abbreviation here and below.

### C33 — p. ~5 (Daniil Nikitin, 2026-09-23)

**Anchor:**

> We defined the

**Comment:**

> This and the next passages are copy and paste from the document Harmonization_metrics_extended_260920_v3 - I added them because there was no description of Supplementary File 2D - E in the main text. Please do so for all the rest cases where there is not description of supplementary or main figures panels in the text. Align the pasted text with the surrounding passages, so the main message goes smoothly and clear.


## Batch-associated variance is redistributed across principal components instead of being eliminated

### C35 — p. ~5 (Daniil Nikitin, 2026-09-23)

**Anchor:**

> (Figure 1C, Supplementary Figure 2F).

**Comment:**

> Combine all the individual principal component analysis to a separate picture so the figure and panel naming is consistent and logical. Prepare a new version of figma figures in Page 3 of the figma frame https://www.figma.com/design/t8bFgusleBEwB9ht7rORCH/FL-harmonization-article?node-id=1013-2&p=f&t=U5btArSRbXwzVpGy-0


## Local neighborhood metrics discriminate well between good and bad approaches but are vulnerable to batch composition

### C37 — p. ~5 (Daniil Nikitin, 2026-09-23)

**Anchor:**

> According to their design, local values depended on how many classes the strategy leaves in the data, which limits comparison across strategies

**Comment:**

> Add supporting reference here.

### C38 — p. ~5 (Daniil Nikitin, 2026-09-23)

**Anchor:**

> (Supplementary Figure 5B).

**Comment:**

> Again, no citations for Supplementary Figure 5E-L. Add them with the relevant text from the document Harmonization_metrics_extended_260920_v3, align with the already written text and do this for all such cases when there are figures panels not discussed in the text but present in figma


## Distributional convergence is the only axis on which the high harshness harmonization methods rank first

### C40 — p. ~5 (Daniil Nikitin, 2026-09-23)

**Anchor:**

> did not separate the clustermap group from the rest approaches

**Comment:**

> Prove this statement with a statistical test, use Mann-Whitney

### C41 — p. ~5 (Daniil Nikitin, 2026-09-23)

**Anchor:**

> (Supplementary Figure 7G to 7J),

**Comment:**

> Cite and discuss each individual panel, as I requested previously.

### C42 — p. ~5 (Daniil Nikitin, 2026-09-23)

**Anchor:**

> varying by only 0.017 across strategies and 0.030 across methods

**Comment:**

> How was the variance measured? Standard deviation? Specify this here and everywhere as applicable.

### C43 — p. ~5 (Daniil Nikitin, 2026-09-23)

**Anchor:**

> weakly

**Comment:**

> Weakly compared to what? Compare them to the batch columns.

### C44 — p. ~6 (Daniil Nikitin, 2026-09-23)

**Anchor:**

> Supplementary Figure 12

**Comment:**

> The frame Supplementary Figure 12 - Harshness by L, M, N looks ugly: the plots are too narrow (very small width, large height), so x tick lables are overlapping. Convert one row of 7 plots to the 3x3 or 3x4 rectangular grid. Add more L,M,N metrics - add random background for N metrics, add both F1 and AUC for both LOBO2 and 3 for compatibility, add cross-batch agreement/diagreement of same and different biology - assign a separate panel letter (like A,B,C...) to each plot and cite & discuss them individually in the main text. Also convert the ugly looking p=1.4e-9 notation to a more beautiful one with p = 1.4*10 to the power of -9 like in the text. Remove H, its not useful. Clearly describe what statistic you are using and how p-value was calculated in the figure description.

### C45 — p. ~6 (Daniil Nikitin, 2026-09-23)

**Anchor:**

> at 0.998 against 0.880 for medium and 0.922 for high

**Comment:**

> There are too many numbers in this text. Please create a separate table in the text, Table 1, and put the mean numbers for the selected metrics by harshness tiers there. Add there also a statistic and p-value. Retain only the qualitative results in the text, add a conclusion about why low/high harshness methods have certain metrics lower/higher

### C46 — p. ~6 (Daniil Nikitin, 2026-09-23)

**Anchor:**

> n = 344 / 1,042 / 848

**Comment:**

> Move these numbers by metric to supplementary tables, no need to overcomplicate the text here with them.

### C47 — p. ~6 (Daniil Nikitin, 2026-09-23)

**Anchor:**

> An earlier calculation of the multiclass-only test

**Comment:**

> Put both variants of the LOBO metrics (with or without single class batches) into the table, remove this technical part from the main text.

### C48 — p. ~6 (Daniil Nikitin, 2026-09-23)

**Anchor:**

> This opposite trend could indicate tradeoff between biology subtype prediction and biomarker correlation preservation metrics

**Comment:**

> Add scatterplots between L, M and N metrics colored by method or strategy to figma, like I did in Figure 1A, B https://www.figma.com/design/t8bFgusleBEwB9ht7rORCH/FL-harmonization-article?node-id=746-22&t=U5btArSRbXwzVpGy-0
> Also please build a clustermap of all metrics cross-correlations, taking all 334 ones excluding the metadata - with color annotations indicating metrics type, group and class - like I did it for Supplementary figure 7 in the Article 1


## Preservation of biomarker expression and of cross-batch rank structure selects a distinct set of approaches

### C50 — p. ~6 (Daniil Nikitin, 2026-09-24)

**Anchor:**

> Figure 4A

**Comment:**

> All new figures that you added to Figma https://www.figma.com/design/t8bFgusleBEwB9ht7rORCH/FL-harmonization-article?node-id=749-38&t=zOhzRu2Lo5BsoAq0-0 , the lower row of figures, Figure 4 and beyond - they completely lack figure proportions that I established manually. They width is OK, but their height is too high - and they are very difficult to manually fit them. Use the frame via the link https://www.figma.com/design/t8bFgusleBEwB9ht7rORCH/FL-harmonization-article?node-id=637-93145&t=zOhzRu2Lo5BsoAq0-0 as strict borderline for each figure. Make each panel of the new figures smaller by a factor 1.5-2, especially Figure 5 https://www.figma.com/design/t8bFgusleBEwB9ht7rORCH/FL-harmonization-article?node-id=1255-3&t=zOhzRu2Lo5BsoAq0-0. Make larger panels twice as narrower to fit them in two columns instead of one. Figure 6 is OK, do not touch it - I will do this manually (https://www.figma.com/design/t8bFgusleBEwB9ht7rORCH/FL-harmonization-article?node-id=1255-4&t=zOhzRu2Lo5BsoAq0-0). Move all the expression scaterplots to supplementary, remove the raw plots - they are just 1 to 1 lines, nothing interesting. Add more different methods for these scatterplots, so we can see linear and non-linear methods and how do they transform expression.


## Supplementary material

### C73 — p. ~12 (Daniil Nikitin, 2026-09-23)

**Anchor:**

> Supplementary Figure 1

**Comment:**

> I pasted here Supplementary figures description from the document Harmonization_metrics_extended_260920_v3. Please add the analogous ones for the rest supplementary figures and tables, and remove the short descriptions you added - they are insufficient.

### C74 — p. ~13 (Daniil Nikitin, 2026-09-22)

**Anchor:**

> Supplementary Figures 1 to 3

**Comment:**

> Add a description to each supplementary figure and table individually, and describe individually each panel as for the main figures. You can take their descriptions from the initial Extended metrics comparison document that I wrote manually.

