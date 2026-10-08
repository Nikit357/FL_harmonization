# Article 2 — literature landscape, with verbatim support

Run `260919_run1`, literature-scout deliverable (plan §6.2). Generated from `02_literature.json`; the two files carry the same content.

## Status

**Complete**

- Spot-check of the inherited entries: all 28 re-resolved by PMID, not the 8 asked for. Title, DOI, year and PMC id agree with the stored values for all 28, and the stored quote was found verbatim in the text retrieved for that PMID for all 28.
- The §11 issue 15 failure mode (elink returning pubmed_pmc_refs, the citing articles, before pubmed_pmc) was tested for explicitly: the verification pass matched the pubmed_pmc linkname by name and recorded which linknames elink returned for each PMID. No entry is attributed to the wrong paper.
- Abstract-quoted entries audited. The count is 8, not the 2 the task text states; all 8 are correctly labelled, and for all 8 elink returns pubmed_pmc_refs only, with no pubmed_pmc link, which is the evidence that no open-access full text exists.
- Overfitting and degenerate-fold sweep reopened (§11 issue 16). Eight references added, six from PubMed with PMC full text or abstract and two from JMLR, which PubMed does not index. Every added quote was asserted verbatim against the retrieved text by the build script, which exits non-zero if a quote is not found.
- Gap statement rewritten to carry the validation arm the added references support.
- Both artifacts written to the 260919_run1 folder from one object.
- Gate 1 defect fixed for PMIDs 16504092, 22151536, 26272994, 29475724, 31948481, 34949812: quote replaced with a sentence from the same paper that states the claim, supports_claim rewritten to what that sentence says, and the superseded quote kept under verification.previous_quote. No other entry, the gap statement, the counts and the could-not-open list are unchanged.

**In progress**

- nothing outstanding

**Not started**

- Cross-check by a second agent (binding rule 3). Nothing here has been re-resolved by anyone other than this agent's own second pass.
- Assignment of each reference to a numbered position in the Article 2 reference list; that belongs to the drafting agent, which cites by order of first appearance.

**Known gaps**

- ACM Digital Library is unreachable from this environment (HTTP 403 on dl.acm.org/doi/10.1145/2382577.2382579), so Kaufman et al. on leakage in data mining is not cited. Kapoor and Narayanan 2023, which is cited, surveys that work and is open access.
- Four PMC author manuscripts carry a submitted title that differs from the PubMed title in hyphenation, capitalisation or wording (PMIDs 31740819, 29608177, 29475724, 29713087). Each was inspected; all four are the same article, and the PubMed title is the one stored.
- The two JMLR entries have no PMID and no DOI, which is a property of that journal. Both fields are written as TO CONFIRM and the PDF URL that was opened is recorded in the verification block.

## Gap statement

Cross-platform transcriptomic harmonization has been benchmarked repeatedly, and each benchmark states the criterion by which it judges success: correlation with a reference profile, downstream classifier accuracy, separation of known subtypes, or a composite of metrics imported from single-cell integration. The 2022 Borisov review sets these criteria side by side and records no agreed standard among them. In parallel, the machine-learning literature establishes that a performance estimate is biased when the batch variable is confounded with the labels, that batch correction does not remove that bias, and that a selection protocol which scores approaches under the criterion used to choose them is internally inconsistent. We found no published study that computes several metric classes over one common set of harmonization approaches and measures how far the approaches each class elects overlap. Article 2 measures that overlap on 2,234 approaches from a single benchmark, and reports leave-one-batch-out prediction on both fold cuts beside it.

## Counts

| field | value |
|---|---|
| entries | 36 |
| distinct_papers | 35 |
| note_on_counts | 36 entries cover 35 papers: Borisov 2022 (PMID 36140419) is quoted twice, on two separate claims. 33 distinct PMIDs plus the two JMLR articles, which PubMed does not index. |
| full_text_read | 26 |
| abstract_only | 10 |
| added_this_run | 8 |
| inherited_and_reverified | 28 |
| quotes_replaced_at_gate_1 | 6 |

| theme | entries |
|---|---|
| batch_effect | 11 |
| validation | 9 |
| lymphoma_biology | 7 |
| integration_metrics | 5 |
| harmonization_field | 4 |

## Could not open

- **Kaufman S, Rosset S, Perlich C, Stitelman O. Leakage in data mining: formulation, detection, and avoidance. ACM TKDD 2012, doi 10.1145/2382577.2382579** — dl.acm.org returns HTTP 403 from this environment; the article is not in PubMed and no open-access copy was reached. Not cited.
- **Full texts for the eight abstract-quoted entries (PMIDs 35617464, 22851511, 16632515, 30573817, 10676951, 12075054, 15548776, 18325927)** — elink returns no pubmed_pmc link for any of them, so PMC holds no open-access full text. Cited from the abstract, labelled as such, with full_text_read false.

## References

### harmonization_field (4)

**Transcriptomic Harmonization as the Way for Suppressing Cross-Platform Bias and Batch Effect**  
Borisov N, Buzdin A · *Biomedicines* 2022 · PMID: 36140419 · DOI: 10.3390/biomedicines10092318 · PMC9496268
- Supports: Harmonization quality is judged by a heterogeneous set of criteria — correlation, PCA inspection, clustering metrics — with no single agreed standard; this review is the field's own statement of that, and Article 2 measures what follows from it.
- Quote [3. Evaluation of the Quality of Harmonization] (PMC full text; full_text_read=True):
  > The following quantitative metrics and methods may be applied to estimate the effect of harmonization: (1) First, different statistical criteria may be used to estimate the following endpoints: (a) Correlation analysis for the gene expression profiles before and after harmonization [29,30,31,33,34];
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

**Transcriptomic Harmonization as the Way for Suppressing Cross-Platform Bias and Batch Effect**  
Borisov N, Buzdin A · *Biomedicines* 2022 · PMID: 36140419 · DOI: 10.3390/biomedicines10092318 · PMC9496268
- Supports: Early cross-platform harmonization benchmarks judged success by eye, which is the practice Article 2's recipe replaces with a stated metric per class.
- Quote [3. Evaluation of the Quality of Harmonization] (PMC full text; full_text_read=True):
  > Thus, early approaches used visual inspection of the principal component analysis (PCA) plots and/or cluster dendrograms to assess the cross-platform harmonization benchmarks [30,31,32,33,34].
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

**Shambhala: a platform-agnostic data harmonizer for gene expression data**  
Borisov N, Shabalina I, Tkachev V, Sorokin M, Garazha A, Pulin A · *BMC bioinformatics* 2019 · PMID: 30727942 · DOI: 10.1186/s12859-019-2641-8 · PMC6366102
- Supports: Shambhala is the platform-agnostic harmonizer whose canonical variant is method 20_shambhala in this benchmark; cited for the method, not for a finding.
- Quote [Discussion] (PMC full text; full_text_read=True):
  > In this study, we developed a new method termed Shambhala suitable for the universal, platform-agnostic harmonization.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

**Shambhala-2: A Protocol for Uniformly Shaped Harmonization of Gene Expression Profiles of Various Formats**  
Borisov N, Sorokin M, Zolotovskaya M, Borisov C, Buzdin A · *Current protocols* 2022 · PMID: 35617464 · DOI: 10.1002/cpz1.444
- Supports: Shambhala-2 is the protocol form of the same harmonizer, and the reference for the uniformly shaped output the benchmark's Shambhala runs produce.
- Quote [Abstract] (PubMed abstract — full text is not open access; full_text_read=False):
  > Uniformly shaped harmonization of gene expression profiles is central for the simultaneous comparison of multiple gene expression datasets.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PubMed abstract.

### batch_effect (11)

**Tackling the widespread and critical impact of batch effects in high-throughput data**  
Leek JT, Scharpf RB, Bravo HC, Simcha D, Langmead B, Johnson WE · *Nature reviews. Genetics* 2010 · PMID: 20838408 · DOI: 10.1038/nrg2825 · PMC3880143
- Supports: Batch effects are widespread and become a major problem when correlated with the outcome of interest — the general framing of the Introduction.
- Quote [Body] (PMC full text; full_text_read=True):
  > This becomes a major problem when batch effects are correlated with an outcome of interest and lead to incorrect conclusions.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

**Methods that remove batch effects while retaining group differences may lead to exaggerated confidence in downstream analyses**  
Nygaard V, Rødland EA, Hovig E · *Biostatistics (Oxford, England)* 2016 · PMID: 26272994 · DOI: 10.1093/biostatistics/kxv027 · PMC4679072
- Supports: Removing batch effects while retaining the study-group difference leaves data that are not batch-effect free: when groups are unevenly distributed across batches the estimation errors are deflated and downstream confidence is exaggerated. Backing for trap 3 and for reporting A_confirmed_bad with its confound stated.
- Quote [Discussion] (PMC full text; full_text_read=True):
  > The use of study group, or other form of outcome, as a covariate when estimating and removing batch effects is problematic if the data are treated as “batch effect free” in subsequent analyses. When the group–batch distribution is unbalanced, i.e. where batches do not have the same composition of groups, this will lead to deflated estimates of the estimation errors, and over-confidence in the results.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.
- Quote replaced 2026-09-19 — gate 1, binding rule 1: the stored quote was a methods step from Experiment 1; it did not state the paper's central finding. Superseded quote: “Thirdly, instead of ComBat, analyses of the real data with limma blocking by batch.” Superseded claim: “When study groups are not evenly distributed across batches, batch adjustment biases group differences and inflates confidence downstream. This is the theoretical backing for trap 3 and for reporting A_confirmed_bad with its confound stated.”

**Batch effect removal methods for microarray gene expression data integration: a survey**  
Lazar C, Meganck S, Taminau J, Steenhoff D, Coletta A, Molter C · *Briefings in bioinformatics* 2013 · PMID: 22851511 · DOI: 10.1093/bib/bbs037
- Supports: A survey of batch-effect removal methods for expression data integration, cited once for the size of the method space Article 1 sampled.
- Quote [Abstract] (PubMed abstract — full text is not open access; full_text_read=False):
  > It has been acknowledged that the main source of variation between different MAGE datasets is due to the so-called 'batch effects'.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PubMed abstract.

**Adjusting batch effects in microarray expression data using empirical Bayes methods**  
Johnson WE, Li C, Rabinovic A · *Biostatistics (Oxford, England)* 2007 · PMID: 16632515 · DOI: 10.1093/biostatistics/kxj037
- Supports: ComBat, the empirical-Bayes location-scale adjustment behind the ComBat family that Article 2's prediction ranking elects.
- Quote [Abstract] (PubMed abstract — full text is not open access; full_text_read=False):
  > We propose parametric and non-parametric empirical Bayes frameworks for adjusting data for batch effects that is robust to outliers in small sample sizes and performs comparable to existing methods for large samples.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PubMed abstract.

**ComBat-seq: batch effect adjustment for RNA-seq count data**  
Zhang Y, Parmigiani G, Johnson WE · *NAR genomics and bioinformatics* 2020 · PMID: 33015620 · DOI: 10.1093/nargab/lqaa078 · PMC7518324
- Supports: ComBat-seq, the count-based variant; one of the two implementations that tie exactly on the Group M margin.
- Quote [DISCUSSION] (PMC full text; full_text_read=True):
  > ComBat-seq is able to preserve the integer nature of count data, making the analysis pipeline more compatible for RNA-seq studies.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

**Feature specific quantile normalization enables cross-platform classification of molecular subtypes using gene expression data**  
Franks JM, Cai G, Whitfield ML · *Bioinformatics (Oxford, England)* 2018 · PMID: 29360996 · DOI: 10.1093/bioinformatics/bty026 · PMC5972664
- Supports: Feature-specific quantile normalization, the method Article 1 selected for the SOM and one of the clustermap best approaches.
- Quote [Results] (PMC full text; full_text_read=True):
  > We achieve up to 98% accuracy for BRCA data and 97% accuracy for CRC data in assigning molecular subtypes to RNA-seq data normalized using FSQN and a support vector machine trained exclusively on DNA microarray data.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

**Cross-platform normalization of microarray and RNA-seq data for machine learning applications**  
Thompson JA, Tan J, Greene CS · *PeerJ* 2016 · PMID: 26844019 · DOI: 10.7717/peerj.1621 · PMC4736986
- Supports: Cross-platform normalization of microarray and RNA-seq data judged by downstream classifier accuracy — a benchmark that used one criterion, which is the practice Article 2 questions.
- Quote [Results for Dataset 1.] (PMC full text; full_text_read=True):
  > Nonparanormal transformation resulted in the best classification of Basal and LumA.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

**Merging two gene-expression studies via cross-platform normalization**  
Shabalin AA, Tjelmeland H, Fan C, Perou CM, Nobel AB · *Bioinformatics (Oxford, England)* 2008 · PMID: 18325927 · DOI: 10.1093/bioinformatics/btn083
- Supports: XPN, the cross-platform normalization that merges two expression studies; method 26_xpn in this benchmark.
- Quote [Abstract — MOTIVATION] (PubMed abstract — full text is not open access; full_text_read=False):
  > This article considers the problem of how to merge datasets arising from different gene-expression studies of a common organism and phenotype.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PubMed abstract.

**Empirical comparison of cross-platform normalization methods for gene expression data**  
Rudy J, Valafar F · *BMC bioinformatics* 2011 · PMID: 22151536 · DOI: 10.1186/1471-2105-12-467 · PMC3314675
- Supports: An empirical comparison of cross-platform normalization methods that scored them on inter-platform concordance, over-detection and under-detection separately, and states that neither detection statistic ranks the methods on its own.
- Quote [Initial evaluation] (PMC full text; full_text_read=True):
  > It is not possible to rank cross-platform normalization methods by either one of the statistics o or u described above. For example, a method may bring o to nearly zero by removing all treatment effects.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.
- Quote replaced 2026-09-19 — gate 1, binding rule 1: the stored quote was a methods sentence about detection curves, and the claim it was attached to — that the benchmark ranked methods on one criterion — is contradicted by the paper, which ranks on three and says no single one suffices. Superseded quote: “By comparing these curves we obtain statistics for over and under-detection of differentially expressed genes after cross-platform normalization as follows.” Superseded claim: “An empirical comparison of cross-platform normalization methods — a benchmark that ranked methods on one criterion, which is the practice Article 2 tests.”

**Capturing heterogeneity in gene expression studies by surrogate variable analysis**  
Leek JT, Storey JD · *PLoS genetics* 2007 · PMID: 17907809 · DOI: 10.1371/journal.pgen.0030161 · PMC1994707
- Supports: Surrogate variable analysis, the basis of method 04_sva, which Article 1's clustermap elected and Article 2 carries as a named group.
- Quote [Statistical model for SVA.] (PMC full text; full_text_read=True):
  > This justifies the use of the singular value decomposition to identify orthogonal signatures of expression heterogeneity for surrogate variable estimates.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

**Normalization of RNA-seq data using factor analysis of control genes or samples**  
Risso D, Ngai J, Speed TP, Dudoit S · *Nature biotechnology* 2014 · PMID: 25150836 · DOI: 10.1038/nbt.2931 · PMC4404308
- Supports: RUV, factor analysis of control genes; method 09_ruv in the benchmark and the reference for the housekeeping-gene control used in Group L.
- Quote [Body] (PMC full text; full_text_read=True):
  > We propose a normalization strategy, remove unwanted variation (RUV), that adjusts for nuisance technical effects by performing factor analysis on suitable sets of control genes (e.g., ERCC spike-ins) or samples (e.g., replicate libraries).
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

### validation (9)

**Bias in error estimation when using cross-validation for model selection**  
Varma S, Simon R · *BMC bioinformatics* 2006 · PMID: 16504092 · DOI: 10.1186/1471-2105-7-91 · PMC1397873
- Supports: Choosing a classifier configuration by minimizing a cross-validated error and then quoting that same minimum as the error estimate is biased downwards; an unbiased estimate needs the selection step repeated inside the resampling loop. Article 2 cites this for the validation design, not for a number.
- Quote [Conclusion] (PMC full text; full_text_read=True):
  > Our results demonstrate that although it is reasonable to optimize classifier parameters by minimizing cross validated error rates, the resulting minimum CV error estimate is not an unbiased estimate of the true error that can be expected from the final classifier on independent data.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.
- Quote replaced 2026-09-19 — gate 1, binding rule 1: the stored quote was a sentence of intent from the Background; it did not state the result. Superseded quote: “In this article, we investigate the effect on the bias when using this nested CV approach.” Superseded claim: “Cross-validation used for model selection gives an optimistically biased error estimate unless the selection is inside the loop — the reason Article 2 reports the worst multiclass fold beside the mean.”

**Batch effect confounding leads to strong bias in performance estimates obtained by cross-validation**  
Soneson C, Gerster S, Delorenzi M · *PloS one* 2014 · PMID: 24967636 · DOI: 10.1371/journal.pone.0100335 · PMC4072626
- Supports: A cross-validation performance estimate is biased when the batch variable is confounded with the class labels, and removing the batch effect does not remove that bias. This is why Article 2 reports leave-one-batch-out prediction on harmonized matrices instead of random-split cross-validation, and why strategy A_confirmed_bad is reported with its confound stated.
- Quote [Discussion] (PMC full text; full_text_read=True):
  > However, the bias in the cross-validation performance estimates is not eliminated by the batch effect removal, and consequently the cross-validation performance estimates obtained after batch effect elimination are not more reliable measures of the true performance than those obtained without batch effect elimination.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

**The practical effect of batch on genomic prediction**  
Parker HS, Leek JT · *Statistical applications in genetics and molecular biology* 2012 · PMID: 22611599 · DOI: 10.1515/1544-6115.1766 · PMC3760371
- Supports: When batch and outcome are correlated, a predictor can score well inside one study and generalize poorly out of sample. This is the mechanism trap 3 of the recipe figure warns about.
- Quote [1 Introduction] (PMC full text; full_text_read=True):
  > Furthermore, prediction accuracy could be erroneously overstated if batch and outcome are highly correlated, and batch proves to be easily predicted. In this scenario, prediction models would appear highly accurate, even under cross-validation in one study. However, the out-of-sample performance of these predictors would be considerably worse.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

**The need to approximate the use-case in clinical machine learning**  
Saeb S, Lonini L, Jayaraman A, Mohr DC, Kording KP · *GigaScience* 2017 · PMID: 28327985 · DOI: 10.1093/gigascience/gix019 · PMC5441397
- Supports: The unit a cross-validation splits on has to match the generalization the claim is about; generalizing across sites requires folds cut across sites. This is the stated justification for the leave-one-batch-out design in Group N.
- Quote [Body] (PMC full text; full_text_read=True):
  > In more complex scenarios, we may want to generalize from one clinical site to another, in which case CV needs to be across these sites [19]. Therefore, the choice of the appropriate CV method depends on the application.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

**Leakage and the reproducibility crisis in machine-learning-based science**  
Kapoor S, Narayanan A · *Patterns (New York, N.Y.)* 2023 · PMID: 37720327 · DOI: 10.1016/j.patter.2023.100804 · PMC10499856
- Supports: A relationship introduced by the data collection or pre-processing strategy inflates measured model performance. Harmonization is a pre-processing step applied to train and test folds together, which places it inside the class of operations this taxonomy covers.
- Quote [Introduction] (PMC full text; full_text_read=True):
  > Data leakage is a spurious relationship between the independent variables and the target variable that arises as an artifact of the data collection, sampling, or pre-processing strategy. Because the spurious relationship will not be present in the distribution about which scientific claims are made, leakage usually leads to inflated estimates of model performance.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

**Selection bias in gene extraction on the basis of microarray gene-expression data**  
Ambroise C, McLachlan GJ · *Proceedings of the National Academy of Sciences of the United States of America* 2002 · PMID: 11983868 · DOI: 10.1073/pnas.102102699 · PMC124442
- Supports: A cross-validated error computed after the features were chosen on the same samples carries a selection bias. Cited for the general form of the bias, alongside Varma and Simon 2006.
- Quote [Abstract (the PMC record for this article carries front matter only; the quoted sentence sits in the abstract paragraph of that record)] (PubMed abstract — the PMC record for this article carries front matter only, no body text; full_text_read=False):
  > However, in these results the test error or the leave-one-out cross-validated error is calculated without allowance for the selection bias.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

**Navigating the pitfalls of applying machine learning in genomics**  
Whalen S, Schreiber J, Noble WS, Pollard KS · *Nature reviews. Genetics* 2022 · PMID: 34837041 · DOI: 10.1038/s41576-021-00434-9
- Supports: The structure of genomics data biases performance evaluation, stated for genomics specifically. Cited once where the Discussion moves from the general machine-learning result to expression data.
- Quote [Abstract] (PubMed abstract — full text is not open access; full_text_read=False):
  > We explore how the structure of genomics data can bias performance evaluations and predictions.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PubMed abstract.

**On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation**  
Cawley GC, Talbot NLC · *Journal of Machine Learning Research 11:2079-2107* 2010 · PMID: [TO CONFIRM: not indexed in PubMed — no PMID exists for this article] · DOI: [TO CONFIRM: JMLR assigns no DOI — the article was opened at https://www.jmlr.org/papers/volume11/cawley10a/cawley10a.pdf]
- Supports: A benchmark that selects a model and reports its score under the same protocol is internally inconsistent, and the inconsistency favours the procedures most prone to over-fitting the selection criterion. This is the theoretical statement of what Article 2 measures empirically when it asks which approaches each metric class elects.
- Quote [5. Bias in Performance Estimation] (Publisher PDF full text (JMLR, open access); full_text_read=True):
  > This means that studies based on potentially biased protocols are not internally consistent, even if it is acknowledged that a bias with respect to other studies may exist.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from JMLR PDF.

**No Unbiased Estimator of the Variance of K-Fold Cross-Validation**  
Bengio Y, Grandvalet Y · *Journal of Machine Learning Research 5:1089-1105* 2004 · PMID: [TO CONFIRM: not indexed in PubMed — no PMID exists for this article] · DOI: [TO CONFIRM: JMLR assigns no DOI — the article was opened at https://www.jmlr.org/papers/volume5/grandvalet04a/grandvalet04a.pdf]
- Supports: The folds of a K-fold cross-validation produce dependent errors whose variance has no unbiased estimator, so a difference between two cross-validated scores carries an uncertainty that cannot be read off the fold spread. This is why Article 2 reports the two leave-one-batch-out fold cuts side by side and does not rank approaches on a fold-level significance test.
- Quote [9. Conclusions] (Publisher PDF full text (JMLR, open access); full_text_read=True):
  > These experiments illustrate thus that the assessment of the significance of observed differences in cross-validation scores should be treated with much caution.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from JMLR PDF.

### integration_metrics (5)

**Benchmarking atlas-level data integration in single-cell genomics**  
Luecken MD, Büttner M, Chaichoompu K, Danese A, Interlandi M, Mueller MF · *Nature methods* 2022 · PMID: 34949812 · DOI: 10.1038/s41592-021-01336-8 · PMC8748196
- Supports: The scIB benchmark defines the composite of batch-correction and bio-conservation metrics from which Article 1's local metrics descend, and reports that named methods favour one of the two metric families at the expense of the other, so the two families do not elect the same methods.
- Quote [Balancing batch removal and biological variance conservation] (PMC full text; full_text_read=True):
  > Particularly in more complex integration tasks, we observed a tradeoff between batch effect removal and bio-conservation (Fig. 3a and Supplementary Data 1). While methods such as SAUCIE, LIGER, BBKNN and Seurat v3 tend to favor the removal of batch effects over conservation of biological variation, DESC and Conos make the opposite choice, and Scanorama, scVI and FastMNN (gene) balance these two objectives. Other methods strike different balances per task (Extended Data Fig. 4).
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.
- Quote replaced 2026-09-19 — gate 1, binding rule 1: the stored quote was a figure-axis legend naming the two score axes; it did not state that the metric families favour different methods. Superseded quote: “The x axis shows the overall batch correction score and the y axis shows the overall bio-conservation score.” Superseded claim: “The scIB benchmark defines the composite of batch-correction and bio-conservation metrics that Article 1's local metrics descend from, and states that metrics disagree about which integration method wins.”

**A test metric for assessing single-cell RNA-seq batch correction**  
Büttner M, Miao Z, Wolf FA, Teichmann SA, Theis FJ · *Nature methods* 2019 · PMID: 30573817 · DOI: 10.1038/s41592-018-0254-1
- Supports: kBET is a test for whether batches are locally well mixed; it was designed for single-cell data, which is the point Article 2 makes about borrowing it.
- Quote [Abstract] (PubMed abstract — full text is not open access; full_text_read=False):
  > Here we present a user-friendly, robust and sensitive k-nearest-neighbor batch-effect test (kBET; https://github.com/theislab/kBET ) for quantification of batch effects.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PubMed abstract.

**Fast, sensitive and accurate integration of single-cell data with Harmony**  
Korsunsky I, Millard N, Fan J, Slowikowski K, Zhang F, Wei K · *Nature methods* 2019 · PMID: 31740819 · DOI: 10.1038/s41592-019-0619-0 · PMC6884693
- Supports: Harmony introduced the LISI family used as a local mixing metric in this benchmark.
- Quote [Quantifying Performance in Cell Line Data] (PMC full text; full_text_read=True):
  > Accurate integration should maintain a cLISI of 1, reflecting a separation of unique cell types throughout the embedding.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

**A benchmark of batch-effect correction methods for single-cell RNA sequencing data**  
Tran HTN, Ang KS, Chevrier M, Zhang X, Lee NYS, Goh M · *Genome biology* 2020 · PMID: 31948481 · DOI: 10.1186/s13059-019-1850-9 · PMC6964114
- Supports: A single-cell batch-correction benchmark that reports its five assessment metrics disagreeing with one another, and with visual inspection of the embeddings, across its first four scenarios — the phenomenon Article 2 quantifies for bulk cross-platform data.
- Quote [Batch integration assessment methods] (PMC full text; full_text_read=True):
  > In the first four scenarios, the assessment metrics did not always agree with each other, nor did the metrics always agree with our visual inspections of t-SNE and UMAP plots.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.
- Quote replaced 2026-09-19 — gate 1, binding rule 1: the stored quote was a pointer to a supplementary table; it did not state that the ranking depends on the metric. Superseded quote: “The computed values of benchmarking metrics can be found in Additional file 5: Table S4, while the statistical tests for significance are in Additional file 6: Table S5.” Superseded claim: “A single-cell batch-correction benchmark whose ranking depends on which metric is used — the same phenomenon Article 2 quantifies for bulk cross-platform data.”

**Batch effects in single-cell RNA-sequencing data are corrected by matching mutual nearest neighbors**  
Haghverdi L, Lun ATL, Morgan MD, Marioni JC · *Nature biotechnology* 2018 · PMID: 29608177 · DOI: 10.1038/nbt.4091 · PMC6152897
- Supports: Mutual nearest neighbours, the MNN method Article 1's clustermap elected.
- Quote [Body] (PMC full text; full_text_read=True):
  > We present a strategy for batch correction that is based on the detection of mutual nearest neighbours (MNN) in the high-dimensional expression space.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

### lymphoma_biology (7)

**Distinct types of diffuse large B-cell lymphoma identified by gene expression profiling**  
Alizadeh AA, Eisen MB, Davis RE, Ma C, Lossos IS, Rosenwald A · *Nature* 2000 · PMID: 10676951 · DOI: 10.1038/35000501
- Supports: Expression profiling splits DLBCL into germinal-centre and activated B-cell types — the biology the marker panel and the LOBO class labels encode.
- Quote [Abstract] (PubMed abstract — full text is not open access; full_text_read=False):
  > One type expressed genes characteristic of germinal centre B cells ('germinal centre B-like DLBCL'); the second type expressed genes normally induced during in vitro activation of peripheral blood B cells ('activated B-like DLBCL').
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PubMed abstract.

**The use of molecular profiling to predict survival after chemotherapy for diffuse large-B-cell lymphoma**  
Rosenwald A, Wright G, Chan WC, Connors JM, Campo E, Fisher RI · *The New England journal of medicine* 2002 · PMID: 12075054 · DOI: 10.1056/NEJMoa012914
- Supports: Molecular profiling predicts survival after chemotherapy in DLBCL, the clinical motivation for signatures that must transfer across cohorts.
- Quote [Abstract — BACKGROUND] (PubMed abstract — full text is not open access; full_text_read=False):
  > We used the gene-expression profiles of these lymphomas to develop a molecular predictor of survival.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PubMed abstract.

**Determining cell-of-origin subtypes of diffuse large B-cell lymphoma using gene expression in formalin-fixed paraffin-embedded tissue**  
Scott DW, Wright GW, Williams PM, Lih CJ, Walsh W, Jaffe ES · *Blood* 2014 · PMID: 24398326 · DOI: 10.1182/blood-2013-11-536433 · PMC3931191
- Supports: Lymph2Cx assigns DLBCL cell-of-origin from FFPE material, the platform-transfer problem in its clinical form.
- Quote [Body] (PMC full text; full_text_read=True):
  > In the validation cohort, the assay was accurate, with only 1 case with definitive COO being incorrectly assigned, and robust, with &gt;95% concordance of COO assignment between 2 independent laboratories.
- Note: The PMC XML encodes the greater-than sign as the entity &gt;. The quote is stored exactly as retrieved; when it is set in the manuscript the entity renders as '>' — 'with >95% concordance'.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

**Prediction of survival in follicular lymphoma based on molecular features of tumor-infiltrating immune cells**  
Dave SS, Wright G, Tan B, Rosenwald A, Gascoyne RD, Chan WC · *The New England journal of medicine* 2004 · PMID: 15548776 · DOI: 10.1056/NEJMoa041869
- Supports: Survival in follicular lymphoma is predicted by immune-cell signatures of the microenvironment, which is why the marker panel carries TME signatures.
- Quote [Abstract — CONCLUSIONS] (PubMed abstract — full text is not open access; full_text_read=False):
  > The length of survival among patients with follicular lymphoma correlates with the molecular features of nonmalignant immune cells present in the tumor at diagnosis.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PubMed abstract.

**A gene-expression profiling score for prediction of outcome in patients with follicular lymphoma: a retrospective training and validation analysis in three international cohorts**  
Huet S, Tesson B, Jais JP, Feldman AL, Magnano L, Thomas E · *The Lancet. Oncology* 2018 · PMID: 29475724 · DOI: 10.1016/S1470-2045(18)30102-5 · PMC5882539
- Supports: A 23-gene expression score separates patients with follicular lymphoma into two groups with markedly different outcomes under immunochemotherapy — outcome-linked FL biology of the kind the Article 2 marker panel encodes.
- Quote [Discussion] (PMC full text; full_text_read=True):
  > In conclusion, we have established a 23-gene predictive score able to identify in routine practice two groups of patients with FL with markedly distinct outcomes when treated with immunochemotherapy.
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.
- Quote replaced 2026-09-19 — gate 1, binding rule 1: the stored quote was a Discussion caveat about an unrelated limitation; it did not state that the score predicts outcome. The cross-platform half of the old claim is dropped from supports_claim and kept as a second verbatim sentence in the verification block, so a drafter who needs that point quotes the sentence that carries it. Superseded quote: “It is uncertain whether the same limitation would be observed with gene-expression profiling of the tumors.” Superseded claim: “A 23-gene expression score predicts outcome in follicular lymphoma — a signature whose portability across platforms is exactly what harmonization decides.”
- Second verbatim sentence from the same paper [Predictive model of progression-free survival], not this entry's quote, supporting the 23 genes were retained only where microarray and NanoString measurements of them agreed, i.e. cross-platform reproducibility used as a gene-selection criterion: “To build a PFS predictive model applicable to FFPE samples, the expression of those 95 curated genes was measured using NanoString technology on 53 FFPE tissues derived from the same biopsies as in the training set. Twenty-three genes with correlation coefficients &gt;0.75 between the two technologies and sample types (microarray on FFT versus NanoString on FFPE samples) were retained (appendix p 12).” (the greater-than sign appears in the retrieved PMC text as the XML entity &gt;; quote it as > when it is set in the manuscript)

**Molecular subtypes of diffuse large B cell lymphoma are associated with distinct pathogenic mechanisms and outcomes**  
Chapuy B, Stewart C, Dunford AJ, Kim J, Kamburov A, Redd RA · *Nature medicine* 2018 · PMID: 29713087 · DOI: 10.1038/s41591-018-0016-8 · PMC6613387
- Supports: Genetic subtypes of DLBCL with distinct outcomes, cited for disease heterogeneity.
- Quote [Outcome associations of DLBCL clusters.] (PMC full text; full_text_read=True):
  > Patients with C2 DLBCLs had a distinct trajectory and a steady rate of progression over time (Fig. 6k,l and Supplementary Fig. 16a).
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.

**Genetics and Pathogenesis of Diffuse Large B-Cell Lymphoma**  
Schmitz R, Wright GW, Huang DW, Johnson CA, Phelan JD, Wang JQ · *The New England journal of medicine* 2018 · PMID: 29641966 · DOI: 10.1056/NEJMoa1801445 · PMC6010183
- Supports: Genetics and pathogenesis of DLBCL, the companion genetic classification.
- Quote [A GENETIC CLASSIFIER FOR DLBCL] (PMC full text; full_text_read=True):
  > Overall, we classified 44.8% of our samples into these genetically “pure” subtypes of DLBCL and recognize that non-subtyped cases may share genetic features as well as etiologic factors with the genetic subtypes (Fig. 2B).
- Verified 2026-09-19: quote found verbatim in the retrieved text = True; retrieved from PMC full text.


## Reading list — what was read

```json
{
 "borisov_reviews_read_in_full": [
  {
   "pmid": "36140419",
   "note": "Section 3, 'Evaluation of the Quality of Harmonization', is the field's own list of harmonization criteria and the anchor for Article 2's thesis"
  },
  {
   "pmid": "30727942",
   "note": "Shambhala, the method behind 20_shambhala"
  },
  {
   "pmid": "35617464",
   "note": "Shambhala-2 protocol"
  }
 ],
 "analysis_notebooks_read_for_convention": [
  {
   "notebook": "harmonization_metrics_analysis.ipynb",
   "cells": 161,
   "convention": "sns.set_style('ticks'); strat_pal, method_pal, imp_pal, group_pal, post_rm_pal"
  },
  {
   "notebook": "harmonization_metrics_analysis_v2.ipynb",
   "cells": 321,
   "convention": "same palette set; metric taxonomy and polarity table"
  },
  {
   "notebook": "harmonization_metrics_analysis_v3.ipynb",
   "cells": 571,
   "convention": "same palette set; best-approach selection and the 'best bars' helpers; the source of CLUSTERMAP_BEST"
  },
  {
   "notebook": "marker_gene_deep_analysis.ipynb",
   "cells": 103,
   "convention": "FONT_SIZE = 7.5; sns.set_style('ticks'); strat_pal, imp_pal, post_rm_pal"
  }
 ],
 "note": "Read for method and plotting convention only. Every number in Article 2 is recomputed by analysis/article2_generalizability.py."
}
```

## ORCID 0000-0003-1029-1174 — self-citations, resolved

```json
{
 "orcid": "0000-0003-1029-1174",
 "note": "The 19 distinct works of plan §2.4, each verified against Crossref (or DataCite for the Zenodo record) on 2026-09-19, with the locus §2.4 assigns it.",
 "works": [
  {
   "n": 1,
   "doi": "10.3389/fmolb.2021.737821",
   "resolved": true,
   "title": "Experimental and Meta-Analytic Validation of RNA Sequencing Signatures for Predicting Status of Microsatellite Instability",
   "year": "2021",
   "venue": "Frontiers in Molecular Biosciences",
   "type": "journal-article",
   "pmid": "34888350",
   "locus": "Introduction — a signature validated across independently generated datasets"
  },
  {
   "n": 2,
   "doi": "10.1186/s12885-022-10177-3",
   "resolved": true,
   "title": "Personalized targeted therapy prescription in colorectal cancer using algorithmic analysis of RNA sequencing data",
   "year": "2022",
   "venue": "BMC Cancer",
   "type": "journal-article",
   "pmid": "36316649",
   "locus": "Introduction — cross-cohort application of an expression model"
  },
  {
   "n": 3,
   "doi": "10.3389/fmolb.2022.753318",
   "resolved": true,
   "title": "Gene Expression-Based Signature Can Predict Sorafenib Response in Kidney Cancer",
   "year": "2022",
   "venue": "Frontiers in Molecular Biosciences",
   "type": "journal-article",
   "pmid": "35359606",
   "locus": "Introduction — signature portability across cohorts"
  },
  {
   "n": 4,
   "doi": "10.3390/biomedicines8060142",
   "resolved": true,
   "title": "RNA Sequencing-Based Identification of Ganglioside GD2-Positive Cancer Phenotype",
   "year": "2020",
   "venue": "Biomedicines",
   "type": "journal-article",
   "pmid": "32486168",
   "locus": "Methods, Group L — marker-panel expression readout"
  },
  {
   "n": 5,
   "doi": "10.3390/cancers11081060",
   "resolved": true,
   "title": "High FREM2 Gene and Protein Expression Are Associated with Favorable Prognosis of IDH-WT Glioblastomas",
   "year": "2019",
   "venue": "Cancers",
   "type": "journal-article",
   "pmid": "31357584",
   "locus": "Methods, Group L — single-marker prognostic readout across platforms"
  },
  {
   "n": 6,
   "doi": "10.1016/j.heliyon.2021.e06408",
   "resolved": true,
   "title": "DNA repair pathway activation features in follicular and papillary thyroid tumors, interrogated using 95 experimental RNA sequencing profiles",
   "year": "2021",
   "venue": "Heliyon",
   "type": "journal-article",
   "pmid": "33748479",
   "locus": "Introduction — pathway-level activation from expression, cross-dataset"
  },
  {
   "n": 7,
   "doi": "10.1016/j.jmig.2021.03.011",
   "resolved": true,
   "title": "Gene Expression Signature of Endometrial Samples from Women with and without Endometriosis",
   "year": "2021",
   "venue": "Journal of Minimally Invasive Gynecology",
   "type": "journal-article",
   "pmid": "33839309",
   "locus": "Introduction — signature from a single-centre cohort; the generalization question"
  },
  {
   "n": 8,
   "doi": "10.1016/j.xcrm.2025.102029",
   "resolved": true,
   "title": "A patient-derived T cell lymphoma biorepository uncovers pathogenetic mechanisms and host-related therapeutic vulnerabilities",
   "year": "2025",
   "venue": "Cell Reports Medicine",
   "type": "journal-article",
   "pmid": "40147445",
   "locus": "Introduction — lymphoma transcriptomics, the disease context"
  },
  {
   "n": 9,
   "doi": "10.3390/ijms21228491",
   "resolved": true,
   "title": "Analysis of miR-9-5p, miR-124-3p, miR-21-5p, miR-138-5p, and miR-1-3p in Glioblastoma Cell Lines and Extracellular Vesicles",
   "year": "2020",
   "venue": "International Journal of Molecular Sciences",
   "type": "journal-article",
   "pmid": "33187334",
   "locus": "Discussion — marker stability across preparation types"
  },
  {
   "n": 10,
   "doi": "10.1007/s10549-018-5043-0",
   "resolved": true,
   "title": "Plasma exosomes stimulate breast cancer metastasis through surface interactions and activation of FAK signaling",
   "year": "2018",
   "venue": "Breast Cancer Research and Treatment",
   "type": "journal-article",
   "pmid": "30484103",
   "locus": "Discussion — expression readouts from a non-standard input material"
  },
  {
   "n": 11,
   "doi": "10.14740/jh412w",
   "resolved": true,
   "title": "Functional Properties of Circulating Exosomes Mediated by Surface-Attached Plasma Proteins",
   "year": "2018",
   "venue": "Journal of Hematology",
   "type": "journal-article",
   "pmid": "32300430",
   "locus": "Discussion — same, paired with 10"
  },
  {
   "n": 12,
   "doi": "10.1098/rsos.260639",
   "resolved": true,
   "title": "Transposable element-host genome evolutionary arms race revealed by multi-modal epigenomic profiling in a telomere-to-telomere human genome reference",
   "year": "2026",
   "venue": "Royal Society Open Science",
   "type": "journal-article",
   "pmid": null,
   "locus": "Introduction — genome-wide profiles compared across assay modalities"
  },
  {
   "n": 13,
   "doi": "10.1101/2025.09.24.677146",
   "resolved": true,
   "title": "Joint analysis of human retroelements-linked histone modification profiles reveals quickly evolving molecular processes connected with cancer",
   "year": "2025",
   "venue": "",
   "type": "posted-content",
   "pmid": null,
   "locus": "Introduction — joint analysis across separately generated profile sets"
  },
  {
   "n": 14,
   "doi": "10.3390/cells8091034",
   "resolved": true,
   "title": "H3K4me3, H3K9ac, H3K27ac, H3K27me3 and H3K9me3 Histone Tags Suggest Distinct Regulatory Evolution of Open and Condensed Chromatin Landmarks",
   "year": "2019",
   "venue": "Cells",
   "type": "journal-article",
   "pmid": "31491936",
   "locus": "Introduction — multi-assay integration"
  },
  {
   "n": 15,
   "doi": "10.3390/cells8101219",
   "resolved": true,
   "title": "Retroelement-Linked H3K4me1 Histone Tags Uncover Regulatory Evolution Trends of Gene Enhancers and Feature Quickly Evolving Molecular Processes in Human Physiology",
   "year": "2019",
   "venue": "Cells",
   "type": "journal-article",
   "pmid": "31597351",
   "locus": "Introduction — same theme as 14"
  },
  {
   "n": 16,
   "doi": "10.3390/cells8020130",
   "resolved": true,
   "title": "Retroelement—Linked Transcription Factor Binding Patterns Point to Quickly Developing Molecular Pathways in Human Evolution",
   "year": "2019",
   "venue": "Cells",
   "type": "journal-article",
   "pmid": "30736359",
   "locus": "Introduction — same theme as 14 (with correction 10.3390/cells8080832)"
  },
  {
   "n": 17,
   "doi": "10.3389/fimmu.2018.00030",
   "resolved": true,
   "title": "Profiling of Human Molecular Pathways Affected by Retrotransposons at the Level of Regulation by Transcription Factor Proteins",
   "year": "2018",
   "venue": "Frontiers in Immunology",
   "type": "journal-article",
   "pmid": "29441061",
   "locus": "Introduction — pathway-level aggregation of noisy per-feature signal"
  },
  {
   "n": 18,
   "doi": "10.5281/zenodo.19052415",
   "resolved": true,
   "title": "Retroelements-driven regulatory evolution of human genes and molecular processes",
   "year": "2026",
   "venue": "Zenodo",
   "type": "dataset",
   "pmid": null,
   "locus": "Data availability — deposited dataset, not a finding",
   "error": null,
   "registry": "DataCite"
  },
  {
   "n": 19,
   "doi": null,
   "resolved": false,
   "locus": "Discussion — method-development precedent (RetroSpect book chapter)",
   "note": "book chapter; no DOI found — [TO CONFIRM: chapter DOI or ISBN]"
  }
 ]
}
```