# 11 — Citations to insert (proposal list for comments C20 and C37)

## Status

- **Done.** 24 proposal entries (P-01 to P-24):
  - 22 for C20 (Methods, "Statistics and software"). Of these, 3 are optional co-citations or alternatives (P-05, P-10, P-12) and 1 is URL-only (P-22, Python 3.11).
  - 2 for C37 (Results, local neighborhood sub-section).
- **Resolved from a real record: 23 of 24.** Records came from PubMed eSummary (by PMID), Crossref (by DOI), DataCite (the Zenodo and e-periodica DOIs), the JMLR paper pages, Open Library (the two books) and each Python package's official citing page (or, for SciPy, its CITATION.bib).
- **Unresolved: 0.** P-22 (Python 3.11) has no bibliographic record because there is no paper to cite for the language; only the official URL is given.
- **Verification levels:**
  - full text (PMC): 4 (P-16, P-17, P-23, P-24)
  - abstract: 4 (P-08, P-11, P-13, P-18)
  - book text: 1 (P-14a)
  - bibliographic record, with or without the official citing page: the rest
- **Classical statistics papers (1901–1974).** They have no abstract at Crossref and no open full text. Their verdicts rest on the bibliographic record and the paper's title, and no passage from their body text is quoted.
- **C37 first choice:** Luecken et al. 2022 (Nat Methods, cited in the manuscript as "Luecken et al. 2021"). **Alternative:** Korsunsky et al. 2019. Both are already in the manuscript's Mendeley fields.
- **Found while checking:** the manuscript text writes "Luecken et al. 2021", but `manuscript/references_260917.md` entry [6] is *Nat Methods* 2022;19(1):41-50. The paper was published online in December 2021, and the issue is dated 2022. The in-text year should follow whatever Mendeley prints for entry [6]. Daniil should check this when he inserts the citation.
- Nothing was written into the manuscript, the `.docx`, `references_260917.md` or `reference_support_260917.md`.

## Summary table

| id | target | reference | PMID / DOI | already cited? | verification | verdict |
|---|---|---|---|---|---|---|
| P-01 | Kruskal-Wallis H test | Kruskal & Wallis 1952, JASA | doi:10.1080/01621459.1952.10483441 | no | bibliographic record | SUPPORTS |
| P-02 | Spearman correlation | Spearman 1904, Am J Psychol | doi:10.2307/1412159 | no | bibliographic record | SUPPORTS |
| P-03 | MAD | Hampel 1974, JASA | doi:10.1080/01621459.1974.10482962 | no | bibliographic record | PARTIALLY SUPPORTS (who first proposed the MAD is disputed) |
| P-04 | Mann-Whitney U (Phase 3 sentence) | Mann & Whitney 1947, Ann Math Stat | doi:10.1214/aoms/1177730491 | no | bibliographic record | SUPPORTS |
| P-05 | Mann-Whitney, optional co-citation | Wilcoxon 1945, Biometrics Bulletin | doi:10.2307/3001968 | no | bibliographic record | SUPPORTS (as a co-citation only) |
| P-06 | PCA | Pearson 1901, Phil Mag | doi:10.1080/14786440109462720 | no | bibliographic record | SUPPORTS |
| P-07 | PCA (name "principal components") | Hotelling 1933, J Educ Psychol | doi:10.1037/h0071325 | no | bibliographic record | SUPPORTS |
| P-08 | logistic regression | Cox 1958, JRSS B | doi:10.1111/j.2517-6161.1958.tb00292.x | no | abstract (Crossref) | SUPPORTS |
| P-09 | Jaccard index | Jaccard 1901, Bull Soc Vaudoise Sci Nat | doi:10.5169/seals-266450 | no | bibliographic record (DataCite) | SUPPORTS |
| P-10 | Jaccard index, English alternative | Jaccard 1912, New Phytologist | doi:10.1111/j.1469-8137.1912.tb05611.x | no | bibliographic record | SUPPORTS |
| P-11 | label-permutation control | Ojala & Garriga 2010, JMLR | JMLR 11(62):1833-1863 (no DOI) | no | abstract (JMLR page) | SUPPORTS |
| P-12 | permutation test, classical alternative | Pitman 1937, JRSS Suppl. / Fisher 1935 (book) | doi:10.2307/2984124 | no | bibliographic record | PARTIALLY SUPPORTS |
| P-13 | AUC (ROC) | Hanley & McNeil 1982, Radiology | PMID 7063747, doi:10.1148/radiology.143.1.7063747 | no | abstract | SUPPORTS |
| P-14 | F1 / macro F1 | van Rijsbergen 1979 (book) + Sokolova & Lapalme 2009 | ISBN 0408709294; doi:10.1016/j.ipm.2009.03.002 | no | book text (author's site) / bibliographic record | SUPPORTS / PARTIALLY SUPPORTS |
| P-15 | pandas 2.3.3 | pandas dev team, Zenodo v2.3.3 + McKinney 2010 | doi:10.5281/zenodo.17229934; doi:10.25080/Majora-92bf1922-00a | no | DataCite/Zenodo + Crossref + official page | SUPPORTS |
| P-16 | numpy 1.26.4 | Harris et al. 2020, Nature | PMID 32939066, doi:10.1038/s41586-020-2649-2 | no | full text (PMC7759461) + official page | SUPPORTS |
| P-17 | scipy 1.12.0 | Virtanen et al. 2020, Nat Methods | PMID 32015543, doi:10.1038/s41592-019-0686-2 | no | full text (PMC7056644) + official CITATION.bib | SUPPORTS |
| P-18 | scikit-learn 1.3.2 | Pedregosa et al. 2011, JMLR | JMLR 12(85):2825-2830 (no DOI) | no | abstract (JMLR page) + official page | SUPPORTS |
| P-19 | statsmodels 0.14.1 | Seabold & Perktold 2010, SciPy Proc. | doi:10.25080/Majora-92bf1922-011 | no | bibliographic record + official page | SUPPORTS |
| P-20 | matplotlib 3.10.8 | Hunter 2007, CiSE | doi:10.1109/MCSE.2007.55 | no | bibliographic record + official page | SUPPORTS |
| P-21 | seaborn 0.13.2 | Waskom 2021, JOSS | doi:10.21105/joss.03021 | no | bibliographic record + official page | SUPPORTS |
| P-22 | Python 3.11 | no paper; official URL only | https://www.python.org/ | no | none needed | optional (URL only) |
| **P-23** | **C37, first choice** | **Luecken et al. 2022, Nat Methods** | **PMID 34949812, doi:10.1038/s41592-021-01336-8** | **yes ([6])** | **full text (PMC8748196)** | **SUPPORTS (for LISI); PARTIALLY for kBET and graph connectivity** |
| P-24 | C37, alternative | Korsunsky et al. 2019, Nat Methods | PMID 31740819, doi:10.1038/s41592-019-0619-0 | yes ([9]) | full text (PMC6884693) | PARTIALLY SUPPORTS |

(P-05, P-10 and P-12 are optional co-citations or alternatives, and P-22 is a URL, not a reference.)

---

## C20 — Methods, "Statistics and software"

The paragraph (line 69 of `manuscript/FL_metric_classes_F1000_260924.md`), quoted without the comment markers:
"Group comparisons across three or more groups used the Kruskal-Wallis H test, and monotone associations used the Spearman correlation coefficient. Per-strategy coefficients were analyzed as their ranges and medians and selected groups were reported by their medians and median absolute deviations (MAD). We ran the analyses under Python 3.11 with pandas 2.3.3, numpy 1.26.4, scipy 1.12.0, scikit-learn 1.3.2, statsmodels 0.14.1, matplotlib 3.10.8 and seaborn 0.13.2."

### P-01 — Kruskal-Wallis H test
- Target sentence: "Group comparisons across three or more groups used the Kruskal-Wallis H test, and monotone associations used the Spearman correlation coefficient."
- Where to insert: after "Kruskal-Wallis H test"
- Reference: Kruskal WH, Wallis WA. Use of Ranks in One-Criterion Variance Analysis. *Journal of the American Statistical Association*. 1952;47(260):583-621.
- PMID / DOI: no PMID | doi:10.1080/01621459.1952.10483441
- Already in the manuscript's Mendeley fields: no
- Supporting passage: Crossref has no abstract. The record's title, "Use of Ranks in One-Criterion Variance Analysis", describes the test: a rank-based one-way (one-criterion) analysis of variance across k groups.
- Verification level: bibliographic record only (Crossref)
- Verdict: SUPPORTS. This is the original publication of the test. The computation itself runs through `scipy.stats.kruskal` (P-17).

### P-02 — Spearman correlation coefficient
- Target sentence: as in P-01
- Where to insert: after "the Spearman correlation coefficient"
- Reference: Spearman C. The Proof and Measurement of Association between Two Things. *The American Journal of Psychology*. 1904;15(1):72-101.
- PMID / DOI: no PMID | doi:10.2307/1412159
- Already in the manuscript's Mendeley fields: no
- Supporting passage: Crossref has no abstract. The record gives the title and the first page (72) only; the end page 101 is the usual pagination and is not in the Crossref record.
- Verification level: bibliographic record only (Crossref)
- Verdict: SUPPORTS. This is the paper that introduced rank correlation. The later name "Spearman's rho" comes from it.

### P-03 — Median absolute deviation (MAD)
- Target sentence: "Per-strategy coefficients were analyzed as their ranges and medians and selected groups were reported by their medians and median absolute deviations (MAD)."
- Where to insert: after "median absolute deviations (MAD)"
- Reference: Hampel FR. The Influence Curve and its Role in Robust Estimation. *Journal of the American Statistical Association*. 1974;69(346):383-393.
- PMID / DOI: no PMID | doi:10.1080/01621459.1974.10482962
- Already in the manuscript's Mendeley fields: no
- Supporting passage: Crossref has no abstract. No open full text was available, so the passage on the MAD inside the paper could not be read and is not quoted.
- Verification level: bibliographic record only (Crossref)
- Verdict: PARTIALLY SUPPORTS. Hampel 1974 is the paper usually cited for the MAD as a robust scale estimator. Two limits apply. (1) Who first proposed the MAD is disputed, and it is often traced back to Gauss; that attribution could not be checked from a primary text here, so it is not proposed. (2) The manuscript uses the plain, unscaled MAD (no 1.4826 factor; see the directory CLAUDE.md). Any citation should keep the word "unscaled" in Methods so the reference is not read as implying the normal-consistent version. Another option was checked and rejected: Leys et al. 2013, *J Exp Soc Psychol* 49(4):764-766, doi:10.1016/j.jesp.2013.03.013. It resolves at Crossref, but its text could not be read (the publisher page is behind a paywall), so it is not proposed.

### P-04 — Mann-Whitney U test (sentence to be added in Phase 3, comment C21)
- Target sentence: not yet written. Phase 3 adds a sentence saying that two-group median comparisons use the two-sided, uncorrected Mann-Whitney U test.
- Where to insert: after "Mann-Whitney U test" in that new sentence
- Reference: Mann HB, Whitney DR. On a Test of Whether one of Two Random Variables is Stochastically Larger than the Other. *The Annals of Mathematical Statistics*. 1947;18(1):50-60.
- PMID / DOI: no PMID | doi:10.1214/aoms/1177730491
- Already in the manuscript's Mendeley fields: no
- Supporting passage: Crossref has no abstract. The title states the test's null hypothesis, stochastic ordering of two random variables.
- Verification level: bibliographic record only (Crossref)
- Verdict: SUPPORTS. This is the original publication of the U statistic. One wording point: Mann-Whitney tests stochastic dominance, which amounts to a difference in medians only when the two distributions have the same shape. For that reason, "compared the two distributions" would be more exact wording for the Phase 3 sentence than "compared medians".

### P-05 — Wilcoxon rank-sum (optional co-citation for P-04)
- Target / where: same place as P-04, cited together with it ("Wilcoxon 1945; Mann and Whitney 1947")
- Reference: Wilcoxon F. Individual Comparisons by Ranking Methods. *Biometrics Bulletin*. 1945;1(6):80-83.
- PMID / DOI: no PMID | doi:10.2307/3001968
- Already in the manuscript's Mendeley fields: no
- Supporting passage: Crossref has no abstract, and the record gives only the first page (80).
- Verification level: bibliographic record only (Crossref)
- Verdict: SUPPORTS as a co-citation only. Wilcoxon introduced the rank-sum test for equal group sizes, and Mann and Whitney generalised it and gave the U statistic. Cite Mann & Whitney alone if the text says "Mann-Whitney U"; add Wilcoxon only if the text says "Wilcoxon rank-sum / Mann-Whitney".

### P-06 — Principal component analysis (geometric origin)
- Target sentence (line 65): "For each approach and each of the 24 RNA batches we excluded this batch and fitted logistic regression in principal components on the training batches alone for the three-class target (DLBCL, FL and normal B cells) and for the two-class target (FL against DLBCL)." PCA is also named in the statistics paragraph if Daniil lists it there.
- Where to insert: after "principal components"
- Reference: Pearson K. LIII. On lines and planes of closest fit to systems of points in space. *The London, Edinburgh, and Dublin Philosophical Magazine and Journal of Science*. 1901;2(11):559-572.
- PMID / DOI: no PMID | doi:10.1080/14786440109462720
- Already in the manuscript's Mendeley fields: no
- Supporting passage: Crossref has no abstract. The title, "lines and planes of closest fit", describes the least-squares subspace that PCA finds.
- Verification level: bibliographic record only (Crossref)
- Verdict: SUPPORTS. Credit for PCA is shared. Pearson (1901) gave the geometric construction, and Hotelling (1933, P-07) gave the statistical formulation and the name "principal components". Citing both is the standard way to handle this.

### P-07 — Principal component analysis (statistical formulation, name)
- Target / where: same place as P-06, cited together with it
- Reference: Hotelling H. Analysis of a complex of statistical variables into principal components. *Journal of Educational Psychology*. 1933;24(6):417-441.
- PMID / DOI: no PMID | doi:10.1037/h0071325
- Already in the manuscript's Mendeley fields: no
- Supporting passage: Crossref has no abstract. The title introduces the term "principal components".
- Verification level: bibliographic record only (Crossref)
- Verdict: SUPPORTS. See P-06 for why both are cited.

### P-08 — Logistic regression
- Target sentence (line 65): as in P-06 ("... fitted logistic regression in principal components ...")
- Where to insert: after "logistic regression"
- Reference: Cox DR. The Regression Analysis of Binary Sequences. *Journal of the Royal Statistical Society Series B: Statistical Methodology*. 1958;20(2):215-232.
- PMID / DOI: no PMID | doi:10.1111/j.2517-6161.1958.tb00292.x
- Already in the manuscript's Mendeley fields: no
- Supporting passage (Crossref abstract, "Summary"): "A sequence of 0's and 1's is observed and it is suspected that the chance that a particular trial is a 1 depends on the value of one or more independent variables. Tests and estimates for such situations are considered, dealing first with problems in which the independent variable is preassigned and then with independent variables that are functions of the sequence."
- Verification level: abstract (Crossref)
- Verdict: SUPPORTS. This is the standard original reference for logistic regression of a binary outcome. The pages are 215-232 as the Crossref record gives them; some reference lists print 215-242, which is wrong. The three-class target uses the multinomial extension, and Cox 1958 covers the binary case only. If Daniil wants the multiclass case covered as well, the scikit-learn citation (P-18) documents the implementation.

### P-09 — Jaccard index (original, French)
- Target sentences: line 55, "Overlap between each two elected sets was calculated as Jaccard index." (also used in the Abstract, line 23)
- Where to insert: after "Jaccard index" in the Methods sentence
- Reference: Jaccard P. Étude comparative de la distribution florale dans une portion des Alpes et du Jura. *Bulletin de la Société Vaudoise des Sciences Naturelles*. 1901;37(142):547-579.
- PMID / DOI: no PMID | doi:10.5169/seals-266450 (DataCite; resolves to e-periodica.ch, pid bsv-002:1901:37::790)
- Already in the manuscript's Mendeley fields: no
- Supporting passage: none quoted. DataCite gives title, creator (Jaccard, Paul) and year 1901 only. The volume, issue and pages above are the usual citation and are not part of the DataCite record.
- Verification level: bibliographic record only (DataCite)
- Verdict: SUPPORTS. This is the original publication of the coefficient (*coefficient de communauté*). P-10 is an English alternative.

### P-10 — Jaccard index (English alternative)
- Target / where: same as P-09, used instead of it
- Reference: Jaccard P. The distribution of the flora in the alpine zone. *New Phytologist*. 1912;11(2):37-50.
- PMID / DOI: no PMID | doi:10.1111/j.1469-8137.1912.tb05611.x
- Already in the manuscript's Mendeley fields: no
- Supporting passage: Crossref has no abstract.
- Verification level: bibliographic record only (Crossref)
- Verdict: SUPPORTS. This is the English account of the same coefficient. It is easier for readers to obtain, but it is not the first publication. Cite 1901 when the original is wanted, 1912 when an English source is wanted, or both.

### P-11 — Label-permutation control (100 permutations)
- Target sentence (line 65): "We also controlled this calculation using 100 biological label permutations and averaged all the N class metrics separately on multiclass batches (having more than one biology class) and on all batches."
- Where to insert: after "100 biological label permutations"
- Reference: Ojala M, Garriga GC. Permutation Tests for Studying Classifier Performance. *Journal of Machine Learning Research*. 2010;11(62):1833-1863. https://jmlr.org/papers/v11/ojala10a.html
- PMID / DOI: none (JMLR does not issue DOIs)
- Already in the manuscript's Mendeley fields: no
- Supporting passage (abstract, JMLR page): "We explore the framework of permutation-based p-values for assessing the performance of classifiers. In this paper we study two simple permutation tests. The first test assess whether the classifier has found a real class structure in the data; the corresponding null distribution is estimated by permuting the labels in the data. This test has been used extensively in classification problems in computational biology."
- Verification level: abstract (JMLR page)
- Verdict: SUPPORTS. The paper describes exactly this control: permute the class labels and measure classifier performance under the null. It fits the sentence better than a generic permutation-test reference. Original, classical sources are in P-12.

### P-12 — Permutation test (classical alternative)
- Target / where: same as P-11, if Daniil prefers a classical source over the classifier-specific one
- Reference (a): Pitman EJG. Significance Tests Which May be Applied to Samples from Any Populations. *Supplement to the Journal of the Royal Statistical Society* (Crossref container: *JRSS Series B*). 1937;4(1):119-130. doi:10.2307/2984124
- Reference (b): Fisher RA. *The Design of Experiments*. Edinburgh: Oliver and Boyd; 1935. This is a book with no DOI; the 1935 Oliver and Boyd edition was confirmed at Open Library (work OL1153859W).
- Already in the manuscript's Mendeley fields: no
- Supporting passage: none quoted (no abstract, no open text).
- Verification level: bibliographic record only (Crossref / Open Library)
- Verdict: PARTIALLY SUPPORTS. Fisher 1935 is the usual attribution for randomization tests, and Pitman 1937 gave the first general treatment. Neither deals with permuting labels to control a classifier, so they support only the general idea. P-11 is recommended.

### P-13 — AUC (ROC)
- Target sentence (line 65): "Then we projected the PCA coordinates at the held-out batch and predicted its biology labels using the previously fitted logistic regression, calculating Area Under Curve (AUC) and F1 scores."
- Where to insert: after "Area Under Curve (AUC)"
- Reference: Hanley JA, McNeil BJ. The meaning and use of the area under a receiver operating characteristic (ROC) curve. *Radiology*. 1982;143(1):29-36.
- PMID / DOI: PMID 7063747 | doi:10.1148/radiology.143.1.7063747
- Already in the manuscript's Mendeley fields: no
- Supporting passage (PubMed abstract): "A representation and interpretation of the area under a receiver operating characteristic (ROC) curve obtained by the "rating" method, or by mathematical predictions based on patient characteristics, is presented. It is shown that in such a setting the area represents the probability that a randomly chosen diseased subject is (correctly) rated or ranked with greater suspicion than a randomly chosen non-diseased subject."
- Verification level: abstract (PubMed; no PMC full text)
- Verdict: SUPPORTS for the two-class AUC, which is the only AUC the manuscript reports (FL against DLBCL). If a multiclass or macro AUC is ever reported, the matching reference is Hand DJ, Till RJ. A Simple Generalisation of the Area Under the ROC Curve for Multiple Class Classification Problems. *Machine Learning*. 2001;45(2):171-186, doi:10.1023/A:1010920819831 (bibliographic record only, Crossref). It is not proposed for the current text.

### P-14 — F1 score / macro F1
- Target sentence: as in P-13 ("... calculating Area Under Curve (AUC) and F1 scores."); macro F1 is also named in the Abstract and Results
- Where to insert: after "F1 scores"
- Reference (a), the original: van Rijsbergen CJ. *Information Retrieval*. 2nd ed. London: Butterworths; 1979. ISBN 0408709294. This is **a book**, with no DOI and no PMID. The edition was confirmed at Open Library (work OL130436W, 2nd ed., 1979, Butterworths). The author's own site has the full text, Chapter 7 "Evaluation": https://www.dcs.gla.ac.uk/Keith/Chapter.7/Ch.7.html
- Reference (b), for macro-averaging: Sokolova M, Lapalme G. A systematic analysis of performance measures for classification tasks. *Information Processing & Management*. 2009;45(4):427-437. doi:10.1016/j.ipm.2009.03.002
- Already in the manuscript's Mendeley fields: no
- Supporting passage, (a), book text, Chapter 7: "Finally, we incorporate into our measurement procedure the fact that users may attach different relative importance to precision and recall. What we want is therefore a parameter (ß) to characterise the measurement function in such a way that we can say: it measures the effectiveness of retrieval with respect to a user who attaches ß times as much importance to recall as precision." The formula for the effectiveness measure E (F = 1 − E) is an image on that page and could not be copied as text.
- Verification level: (a) book text (author-hosted HTML); (b) bibliographic record only (Crossref, no abstract)
- Verdict: (a) SUPPORTS. It is the usual origin of the F-measure; the text defines the weighted effectiveness measure E, and F1 = 1 − E at ß = 1. (b) PARTIALLY SUPPORTS. By its title it is a systematic review of classification measures, including macro-averaged ones, but its text was not read.

### P-15 — pandas 2.3.3
- Target sentence: "We ran the analyses under Python 3.11 with pandas 2.3.3, numpy 1.26.4, scipy 1.12.0, scikit-learn 1.3.2, statsmodels 0.14.1, matplotlib 3.10.8 and seaborn 0.13.2."
- Where to insert: after "pandas 2.3.3"
- Reference (a), version-specific software record, as the project asks: The pandas development team. pandas-dev/pandas: Pandas, v2.3.3. Zenodo; 2025-09-30. doi:10.5281/zenodo.17229934 (concept DOI for all versions: 10.5281/zenodo.3509134)
- Reference (b), paper: McKinney W. Data Structures for Statistical Computing in Python. In: *Proceedings of the 9th Python in Science Conference*. 2010:56-61. doi:10.25080/Majora-92bf1922-00a
- Official URL: https://pandas.pydata.org/ | citing page: https://pandas.pydata.org/about/citing.html
- Already in the manuscript's Mendeley fields: no
- Supporting passage (official citing page): "If you use pandas for a scientific publication, we would appreciate citations to the published software and the following paper: pandas on Zenodo, Please find us on Zenodo and replace with the citation for the version you are using."
- Verification level: official page + Zenodo API (the v2.3.3 record) + Crossref (McKinney)
- Verdict: SUPPORTS. The project asks for both the Zenodo record of the version used and the McKinney paper.

### P-16 — numpy 1.26.4
- Target sentence: as in P-15; insert after "numpy 1.26.4"
- Reference: Harris CR, Millman KJ, van der Walt SJ, et al. Array programming with NumPy. *Nature*. 2020;585(7825):357-362.
- PMID / DOI: PMID 32939066 | doi:10.1038/s41586-020-2649-2 | Official URL: https://numpy.org/ | citing page: https://numpy.org/citing-numpy/
- Already in the manuscript's Mendeley fields: no
- Supporting passage (official citing page): "... and you would like to acknowledge the project in your academic publication, we suggest citing the following paper: Harris, C.R., Millman, K.J., van der Walt, S.J. et al. Array programming with NumPy. Nature 585, 357–362 (2020)." Article (PMC7759461): "NumPy is the primary array programming library for Python; here its fundamental concepts are reviewed and its evolution into a flexible interoperability layer between increasingly specialized computational libraries is discussed."
- Verification level: full text (PMC7759461) + official page
- Verdict: SUPPORTS

### P-17 — scipy 1.12.0
- Target sentence: as in P-15; insert after "scipy 1.12.0". SciPy also runs the Kruskal-Wallis, Mann-Whitney and Spearman computations.
- Reference: Virtanen P, Gommers R, Oliphant TE, et al. SciPy 1.0: fundamental algorithms for scientific computing in Python. *Nature Methods*. 2020;17(3):261-272.
- PMID / DOI: PMID 32015543 | doi:10.1038/s41592-019-0686-2 | Official URL: https://scipy.org/ | citing page: https://scipy.org/citing-scipy/ (the page is JavaScript-rendered, so the official `CITATION.bib` in the scipy repository was read instead: https://github.com/scipy/scipy/blob/main/CITATION.bib, entry `2020SciPy-NMeth`)
- Already in the manuscript's Mendeley fields: no
- Supporting passage (article, PMC7056644): "This Perspective describes the development and capabilities of SciPy 1.0, an open source scientific computing library for the Python programming language."
- Verification level: full text (PMC7056644) + official CITATION.bib
- Verdict: SUPPORTS

### P-18 — scikit-learn 1.3.2
- Target sentence: as in P-15; insert after "scikit-learn 1.3.2"
- Reference: Pedregosa F, Varoquaux G, Gramfort A, Michel V, Thirion B, Grisel O, Blondel M, Prettenhofer P, Weiss R, Dubourg V, Vanderplas J, Passos A, Cournapeau D, Brucher M, Perrot M, Duchesnay É. Scikit-learn: Machine Learning in Python. *Journal of Machine Learning Research*. 2011;12(85):2825-2830. https://jmlr.org/papers/v12/pedregosa11a.html
- PMID / DOI: none (JMLR) | Official URL: https://scikit-learn.org/ | citing: https://scikit-learn.org/stable/about.html#citing-scikit-learn
- Already in the manuscript's Mendeley fields: no
- Supporting passage (official page): "If you use scikit-learn in a scientific publication, we would appreciate citations to the following paper: Scikit-learn: Machine Learning in Python, Pedregosa et al., JMLR 12, pp. 2825-2830, 2011." Abstract (JMLR): "Scikit-learn is a Python module integrating a wide range of state-of-the-art machine learning algorithms for medium-scale supervised and unsupervised problems."
- Verification level: abstract (JMLR page) + official page
- Verdict: SUPPORTS

### P-19 — statsmodels 0.14.1
- Target sentence: as in P-15; insert after "statsmodels 0.14.1"
- Reference: Seabold S, Perktold J. Statsmodels: Econometric and Statistical Modeling with Python. In: *Proceedings of the 9th Python in Science Conference*. 2010:92-96.
- PMID / DOI: none | doi:10.25080/Majora-92bf1922-011 | Official URL: https://www.statsmodels.org/
- Already in the manuscript's Mendeley fields: no
- Supporting passage (official documentation index page, "Citation"): "Please use following citation to cite statsmodels in scientific publications: Seabold, Skipper, and Josef Perktold. "statsmodels: Econometric and statistical modeling with python." Proceedings of the 9th Python in Science Conference. 2010."
- Verification level: bibliographic record (Crossref) + official page
- Verdict: SUPPORTS

### P-20 — matplotlib 3.10.8
- Target sentence: as in P-15; insert after "matplotlib 3.10.8"
- Reference: Hunter JD. Matplotlib: A 2D Graphics Environment. *Computing in Science & Engineering*. 2007;9(3):90-95.
- PMID / DOI: none | doi:10.1109/MCSE.2007.55 | Official URL: https://matplotlib.org/ | citing: https://matplotlib.org/stable/project/citing.html
- Already in the manuscript's Mendeley fields: no
- Supporting passage (official citing page): "If Matplotlib contributes to a project that leads to a scientific publication, please acknowledge this fact by citing J. D. Hunter, "Matplotlib: A 2D Graphics Environment", Computing in Science & Engineering, vol. 9, no. 3, pp. 90-95, 2007."
- Verification level: bibliographic record (Crossref) + official page
- Verdict: SUPPORTS. The same page also lists version-specific Zenodo DOIs; the matplotlib 3.10.8 DOI was not looked up and can be added if the journal wants version records.

### P-21 — seaborn 0.13.2
- Target sentence: as in P-15; insert after "seaborn 0.13.2"
- Reference: Waskom ML. seaborn: statistical data visualization. *Journal of Open Source Software*. 2021;6(60):3021.
- PMID / DOI: none | doi:10.21105/joss.03021 | Official URL: https://seaborn.pydata.org/ | citing: https://seaborn.pydata.org/citing.html
- Already in the manuscript's Mendeley fields: no
- Supporting passage (official citing page): "If seaborn is integral to a scientific publication, please cite it. A paper describing seaborn has been published in the Journal of Open Source Software: Waskom, M. L., (2021). seaborn: statistical data visualization. Journal of Open Source Software, 6(60), 3021."
- Verification level: bibliographic record (Crossref) + official page
- Verdict: SUPPORTS

### P-22 — Python 3.11 (optional, URL only)
- Target sentence: as in P-15, after "Python 3.11"
- Reference: none proposed. The Python Software Foundation does not publish a paper to cite for the language. A URL in the text ("Python 3.11, https://www.python.org/") is enough. The Python reference manual is sometimes cited as a book, but no record of it was resolved, so it is not proposed.
- Verdict: optional

---

## C37 — Results, local neighborhood sub-section

Target sentence (line 131), without the comment markers: "According to their design, local values depended on how many classes the strategy leaves in the data, which limits comparison across strategies."

### P-23 — C37 first choice: Luecken et al. 2022 (manuscript: "Luecken et al. 2021")
- Target sentence (quote exactly): "According to their design, local values depended on how many classes the strategy leaves in the data, which limits comparison across strategies."
- Where to insert: at the end of the sentence, before the full stop
- Reference: Luecken MD, Büttner M, Chaichoompu K, Danese A, Interlandi M, Mueller MF, et al. Benchmarking atlas-level data integration in single-cell genomics. *Nat Methods*. 2022;19(1):41-50.
- PMID / DOI: PMID 34949812 | doi:10.1038/s41592-021-01336-8 | PMC8748196
- Already in the manuscript's Mendeley fields: **yes**. This is reference [6] in `references_260917.md`, cited in the text as "Luecken et al. 2021". Daniil can re-use the existing Mendeley entry.
- Supporting passages (full text, Methods):
  - Section "Graph LISI": "Thus, LISI scores range from 1 to N, where N is the total number of batches in the dataset."
  - Section "Graph LISI": "As LISI scores range from 1 to B (where B denotes the number of batches), indicating perfect separation and perfect mixing, respectively, we rescaled them to the range 0 to 1."
  - Section "kBET": "The kBET algorithm (v.0.99.6, release 4c9dafa) determines whether the label composition of a k nearest neighborhood of a cell is similar to the expected (global) label composition."
  - Section "kBET": "To test for technical effects and to account for cell-type frequency shifts across datasets, we applied kBET separately on the batch variable for each cell identity label."
- Verification level: full text (PMC8748196)
- Verdict: **SUPPORTS** for LISI, which is the metric the next sentence quotes (biology LISI medians 1.10, 1.07 and 1.62). The paper states that the LISI ceiling equals the number of labels, and it rescales by that number precisely so that scores can be compared between tasks with different numbers of labels. Raw values from strategies that keep different numbers of classes therefore sit on different scales. The support is PARTIAL for kBET and graph connectivity. For kBET, the passages show that the result depends on the expected global label composition, and that the authors had to stratify to handle composition shifts. For graph connectivity, the formula is a mean over the label set C, but the paper does not state that it depends on how many labels there are.

### P-24 — C37 alternative: Korsunsky et al. 2019
- Target sentence / where: as in P-23. It can be cited instead of Luecken, or together with it.
- Reference: Korsunsky I, Millard N, Fan J, Slowikowski K, Zhang F, Wei K, et al. Fast, sensitive and accurate integration of single-cell data with Harmony. *Nat Methods*. 2019;16(12):1289-1296.
- PMID / DOI: PMID 31740819 | doi:10.1038/s41592-019-0619-0 | PMC6884693
- Already in the manuscript's Mendeley fields: **yes** (reference [9])
- Supporting passages (full text):
  - Section "Quantifying Performance in Cell Line Data": "Neighborhoods represented by only a single dataset get an iLISI of 1, while neighborhoods with an equal number of cells from 2 datasets get an iLISI of 2. Note that even under ideal mixing, if the datasets have different numbers of cells, iLISI would be less than 2."
  - Same section: "Thus, we expect the average iLISI to range from 1, reflecting no integration, to 1.8 (...) for Jurkat cells and 1.5 (...) for 293T cells, reflecting maximal accurate integration."
  - Same section: "A potential pitfall of LISI is that it is sensitive to datasets of vastly different sizes. In such a situation, most neighborhoods can be dominated by a single dataset and LISI values become difficult to interpret."
  - Section "LISI Metric": "Thus, this index reports the effective number of batches in a local neighborhood."
- Verification level: full text (PMC6884693)
- Verdict: **PARTIALLY SUPPORTS.** This is the paper that defines LISI, and it states that the maximum achievable value depends on the number of labels and on their proportions (1.8 against 1.5 for the two cell lines). It does not state the consequence the sentence draws, that values cannot be compared across subsets with different numbers of classes. It is best cited together with P-23 ("Korsunsky et al. 2019; Luecken et al. 2021"), since it gives the definition and Luecken gives the rescaling argument.

Other candidates checked and not proposed:
- **Büttner et al. 2018/2019** (kBET, PMID 30573817, already cited [8]). There is no PMC full text. The abstract (checked) describes the test but does not mention a dependence on the number of labels.
- **Tran et al. 2020** (PMID 31948481, PMC6964114, already cited [7]). The full text defines LISI as "the effective number of types present in this neighborhood" and says that "a score close to the expected number of batches denotes good mixing". This implies the dependence but states it more weakly than P-23 or P-24.

---

## Hand-off

Daniil inserts these references himself through Mendeley; P-23 and P-24 re-use existing entries [6] and [9]. Nothing was written into the manuscript `.md` or `.docx`, `references_260917.md` or `reference_support_260917.md`. The only other files written are the `tools/cache/` entries that `tools/fetch_literature.py` creates by itself.
