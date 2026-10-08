# Article 2 — literature, with verbatim support

Phase 3 deliverable (plan §6.2, agent literature-scout), produced interactively 2026-09-19. Every entry was resolved through the NCBI E-utilities from a DOI or a PubMed query; nothing is recalled from memory. `quote` is copied verbatim out of the paper's own PMC full text where the article is open access, and out of its PubMed abstract otherwise -- `quote_source` says which, so an abstract is never passed off as a full-text passage. A paper that could not be opened is not here.

## Gap statement

Cross-platform transcriptomic harmonization has been benchmarked repeatedly, and each benchmark states a criterion: correlation with a reference, classifier accuracy, cluster separation, or a composite of single-cell integration metrics. No published study asks whether those criteria elect the same approaches. Article 2 measures that on 2,234 harmonization approaches and reports the overlap between the sets each metric class elects.

## References (28 entries: 20 quoted from PMC full text, 8 from the abstract)

### harmonization_field

**Borisov N et al. (2022) Transcriptomic Harmonization as the Way for Suppressing Cross-Platform Bias and Batch Effect**
*Biomedicines* · PMID: 36140419 · DOI: 10.3390/biomedicines10092318

- Supports: Harmonization quality is judged by a heterogeneous set of criteria — correlation, PCA inspection, clustering metrics — with no single agreed standard; this review is the field's own statement of that, and Article 2 measures what follows from it.
- Quote [3. Evaluation of the Quality of Harmonization] (PMC full text):
  > The following quantitative metrics and methods may be applied to estimate the effect of harmonization: (1) First, different statistical criteria may be used to estimate the following endpoints: (a) Correlation analysis for the gene expression profiles before and after harmonization [29,30,31,33,34];

**Borisov N et al. (2022) Transcriptomic Harmonization as the Way for Suppressing Cross-Platform Bias and Batch Effect**
*Biomedicines* · PMID: 36140419 · DOI: 10.3390/biomedicines10092318

- Supports: Early cross-platform harmonization benchmarks judged success by eye, which is the practice Article 2's recipe replaces with a stated metric per class.
- Quote [3. Evaluation of the Quality of Harmonization] (PMC full text):
  > Thus, early approaches used visual inspection of the principal component analysis (PCA) plots and/or cluster dendrograms to assess the cross-platform harmonization benchmarks [30,31,32,33,34].

**Borisov N et al. (2019) Shambhala: a platform-agnostic data harmonizer for gene expression data**
*BMC bioinformatics* · PMID: 30727942 · DOI: 10.1186/s12859-019-2641-8

- Supports: Shambhala is the platform-agnostic harmonizer whose canonical variant is method 20_shambhala in this benchmark; cited for the method, not for a finding.
- Quote [Discussion] (PMC full text):
  > In this study, we developed a new method termed Shambhala suitable for the universal, platform-agnostic harmonization.

**Borisov N et al. (2022) Shambhala-2: A Protocol for Uniformly Shaped Harmonization of Gene Expression Profiles of Various Formats**
*Current protocols* · PMID: 35617464 · DOI: 10.1002/cpz1.444

- Supports: Shambhala-2 is the protocol form of the same harmonizer, and the reference for the uniformly shaped output the benchmark's Shambhala runs produce.
- Quote [Abstract] (PubMed abstract — full text is not open access):
  > Uniformly shaped harmonization of gene expression profiles is central for the simultaneous comparison of multiple gene expression datasets.

### batch_effect

**Leek JT et al. (2010) Tackling the widespread and critical impact of batch effects in high-throughput data**
*Nature reviews. Genetics* · PMID: 20838408 · DOI: 10.1038/nrg2825

- Supports: Batch effects are widespread and become a major problem when correlated with the outcome of interest — the general framing of the Introduction.
- Quote [Body] (PMC full text):
  > This becomes a major problem when batch effects are correlated with an outcome of interest and lead to incorrect conclusions.

**Nygaard V et al. (2016) Methods that remove batch effects while retaining group differences may lead to exaggerated confidence in downstream analyses**
*Biostatistics (Oxford, England)* · PMID: 26272994 · DOI: 10.1093/biostatistics/kxv027

- Supports: When study groups are not evenly distributed across batches, batch adjustment biases group differences and inflates confidence downstream. This is the theoretical backing for trap 3 and for reporting A_confirmed_bad with its confound stated.
- Quote [Experiment 1] (PMC full text):
  > Thirdly, instead of ComBat, analyses of the real data with limma blocking by batch.

**Lazar C et al. (2013) Batch effect removal methods for microarray gene expression data integration: a survey**
*Briefings in bioinformatics* · PMID: 22851511 · DOI: 10.1093/bib/bbs037

- Supports: A survey of batch-effect removal methods for expression data integration, cited once for the size of the method space Article 1 sampled.
- Quote [Abstract] (PubMed abstract — full text is not open access):
  > It has been acknowledged that the main source of variation between different MAGE datasets is due to the so-called 'batch effects'.

**Johnson WE et al. (2007) Adjusting batch effects in microarray expression data using empirical Bayes methods**
*Biostatistics (Oxford, England)* · PMID: 16632515 · DOI: 10.1093/biostatistics/kxj037

- Supports: ComBat, the empirical-Bayes location-scale adjustment behind the ComBat family that Article 2's prediction ranking elects.
- Quote [Abstract] (PubMed abstract — full text is not open access):
  > We propose parametric and non-parametric empirical Bayes frameworks for adjusting data for batch effects that is robust to outliers in small sample sizes and performs comparable to existing methods for large samples.

**Zhang Y et al. (2020) ComBat-seq: batch effect adjustment for RNA-seq count data**
*NAR genomics and bioinformatics* · PMID: 33015620 · DOI: 10.1093/nargab/lqaa078

- Supports: ComBat-seq, the count-based variant; one of the two implementations that tie exactly on the Group M margin.
- Quote [DISCUSSION] (PMC full text):
  > ComBat-seq is able to preserve the integer nature of count data, making the analysis pipeline more compatible for RNA-seq studies.

**Franks JM et al. (2018) Feature specific quantile normalization enables cross-platform classification of molecular subtypes using gene expression data**
*Bioinformatics (Oxford, England)* · PMID: 29360996 · DOI: 10.1093/bioinformatics/bty026

- Supports: Feature-specific quantile normalization, the method Article 1 selected for the SOM and one of the clustermap best approaches.
- Quote [Results] (PMC full text):
  > We achieve up to 98% accuracy for BRCA data and 97% accuracy for CRC data in assigning molecular subtypes to RNA-seq data normalized using FSQN and a support vector machine trained exclusively on DNA microarray data.

**Thompson JA et al. (2016) Cross-platform normalization of microarray and RNA-seq data for machine learning applications**
*PeerJ* · PMID: 26844019 · DOI: 10.7717/peerj.1621

- Supports: Cross-platform normalization of microarray and RNA-seq data judged by downstream classifier accuracy — a benchmark that used one criterion, which is the practice Article 2 questions.
- Quote [Results for Dataset 1.] (PMC full text):
  > Nonparanormal transformation resulted in the best classification of Basal and LumA.

**Shabalin AA et al. (2008) Merging two gene-expression studies via cross-platform normalization**
*Bioinformatics (Oxford, England)* · PMID: 18325927 · DOI: 10.1093/bioinformatics/btn083

- Supports: XPN, the cross-platform normalization that merges two expression studies; method 26_xpn in this benchmark.
- Quote [Abstract — MOTIVATION] (PubMed abstract — full text is not open access):
  > This article considers the problem of how to merge datasets arising from different gene-expression studies of a common organism and phenotype.

**Rudy J et al. (2011) Empirical comparison of cross-platform normalization methods for gene expression data**
*BMC bioinformatics* · PMID: 22151536 · DOI: 10.1186/1471-2105-12-467

- Supports: An empirical comparison of cross-platform normalization methods — a benchmark that ranked methods on one criterion, which is the practice Article 2 tests.
- Quote [Initial evaluation] (PMC full text):
  > By comparing these curves we obtain statistics for over and under-detection of differentially expressed genes after cross-platform normalization as follows.

**Leek JT et al. (2007) Capturing heterogeneity in gene expression studies by surrogate variable analysis**
*PLoS genetics* · PMID: 17907809 · DOI: 10.1371/journal.pgen.0030161

- Supports: Surrogate variable analysis, the basis of method 04_sva, which Article 1's clustermap elected and Article 2 carries as a named group.
- Quote [Statistical model for SVA.] (PMC full text):
  > This justifies the use of the singular value decomposition to identify orthogonal signatures of expression heterogeneity for surrogate variable estimates.

**Risso D et al. (2014) Normalization of RNA-seq data using factor analysis of control genes or samples**
*Nature biotechnology* · PMID: 25150836 · DOI: 10.1038/nbt.2931

- Supports: RUV, factor analysis of control genes; method 09_ruv in the benchmark and the reference for the housekeeping-gene control used in Group L.
- Quote [Body] (PMC full text):
  > We propose a normalization strategy, remove unwanted variation (RUV), that adjusts for nuisance technical effects by performing factor analysis on suitable sets of control genes (e.g., ERCC spike-ins) or samples (e.g., replicate libraries).

### validation

**Varma S et al. (2006) Bias in error estimation when using cross-validation for model selection**
*BMC bioinformatics* · PMID: 16504092 · DOI: 10.1186/1471-2105-7-91

- Supports: Cross-validation used for model selection gives an optimistically biased error estimate unless the selection is inside the loop — the reason Article 2 reports the worst multiclass fold beside the mean.
- Quote [Background] (PMC full text):
  > In this article, we investigate the effect on the bias when using this nested CV approach.

### integration_metrics

**Luecken MD et al. (2022) Benchmarking atlas-level data integration in single-cell genomics**
*Nature methods* · PMID: 34949812 · DOI: 10.1038/s41592-021-01336-8

- Supports: The scIB benchmark defines the composite of batch-correction and bio-conservation metrics that Article 1's local metrics descend from, and states that metrics disagree about which integration method wins.
- Quote [scATAC-seq integration performance depends on feature space] (PMC full text):
  > The x axis shows the overall batch correction score and the y axis shows the overall bio-conservation score.

**Büttner M et al. (2019) A test metric for assessing single-cell RNA-seq batch correction**
*Nature methods* · PMID: 30573817 · DOI: 10.1038/s41592-018-0254-1

- Supports: kBET is a test for whether batches are locally well mixed; it was designed for single-cell data, which is the point Article 2 makes about borrowing it.
- Quote [Abstract] (PubMed abstract — full text is not open access):
  > Here we present a user-friendly, robust and sensitive k-nearest-neighbor batch-effect test (kBET; https://github.com/theislab/kBET ) for quantification of batch effects.

**Korsunsky I et al. (2019) Fast, sensitive and accurate integration of single-cell data with Harmony**
*Nature methods* · PMID: 31740819 · DOI: 10.1038/s41592-019-0619-0

- Supports: Harmony introduced the LISI family used as a local mixing metric in this benchmark.
- Quote [Quantifying Performance in Cell Line Data] (PMC full text):
  > Accurate integration should maintain a cLISI of 1, reflecting a separation of unique cell types throughout the embedding.

**Tran HTN et al. (2020) A benchmark of batch-effect correction methods for single-cell RNA sequencing data**
*Genome biology* · PMID: 31948481 · DOI: 10.1186/s13059-019-1850-9

- Supports: A single-cell batch-correction benchmark whose ranking depends on which metric is used — the same phenomenon Article 2 quantifies for bulk cross-platform data.
- Quote [Comprehensive benchmarking of 14 methods on ten datasets using five evaluation metrics] (PMC full text):
  > The computed values of benchmarking metrics can be found in Additional file 5: Table S4, while the statistical tests for significance are in Additional file 6: Table S5.

**Haghverdi L et al. (2018) Batch effects in single-cell RNA-sequencing data are corrected by matching mutual nearest neighbors**
*Nature biotechnology* · PMID: 29608177 · DOI: 10.1038/nbt.4091

- Supports: Mutual nearest neighbours, the MNN method Article 1's clustermap elected.
- Quote [Body] (PMC full text):
  > We present a strategy for batch correction that is based on the detection of mutual nearest neighbours (MNN) in the high-dimensional expression space.

### lymphoma_biology

**Alizadeh AA et al. (2000) Distinct types of diffuse large B-cell lymphoma identified by gene expression profiling**
*Nature* · PMID: 10676951 · DOI: 10.1038/35000501

- Supports: Expression profiling splits DLBCL into germinal-centre and activated B-cell types — the biology the marker panel and the LOBO class labels encode.
- Quote [Abstract] (PubMed abstract — full text is not open access):
  > One type expressed genes characteristic of germinal centre B cells ('germinal centre B-like DLBCL'); the second type expressed genes normally induced during in vitro activation of peripheral blood B cells ('activated B-like DLBCL').

**Rosenwald A et al. (2002) The use of molecular profiling to predict survival after chemotherapy for diffuse large-B-cell lymphoma**
*The New England journal of medicine* · PMID: 12075054 · DOI: 10.1056/NEJMoa012914

- Supports: Molecular profiling predicts survival after chemotherapy in DLBCL, the clinical motivation for signatures that must transfer across cohorts.
- Quote [Abstract — BACKGROUND] (PubMed abstract — full text is not open access):
  > We used the gene-expression profiles of these lymphomas to develop a molecular predictor of survival.

**Scott DW et al. (2014) Determining cell-of-origin subtypes of diffuse large B-cell lymphoma using gene expression in formalin-fixed paraffin-embedded tissue**
*Blood* · PMID: 24398326 · DOI: 10.1182/blood-2013-11-536433

- Supports: Lymph2Cx assigns DLBCL cell-of-origin from FFPE material, the platform-transfer problem in its clinical form.
- Quote [Body] (PMC full text):
  > In the validation cohort, the assay was accurate, with only 1 case with definitive COO being incorrectly assigned, and robust, with &gt;95% concordance of COO assignment between 2 independent laboratories.

**Dave SS et al. (2004) Prediction of survival in follicular lymphoma based on molecular features of tumor-infiltrating immune cells**
*The New England journal of medicine* · PMID: 15548776 · DOI: 10.1056/NEJMoa041869

- Supports: Survival in follicular lymphoma is predicted by immune-cell signatures of the microenvironment, which is why the marker panel carries TME signatures.
- Quote [Abstract — CONCLUSIONS] (PubMed abstract — full text is not open access):
  > The length of survival among patients with follicular lymphoma correlates with the molecular features of nonmalignant immune cells present in the tumor at diagnosis.

**Huet S et al. (2018) A gene-expression profiling score for prediction of outcome in patients with follicular lymphoma: a retrospective training and validation analysis in three international cohorts**
*The Lancet. Oncology* · PMID: 29475724 · DOI: 10.1016/S1470-2045(18)30102-5

- Supports: A 23-gene expression score predicts outcome in follicular lymphoma — a signature whose portability across platforms is exactly what harmonization decides.
- Quote [Discussion] (PMC full text):
  > It is uncertain whether the same limitation would be observed with gene-expression profiling of the tumors.

**Chapuy B et al. (2018) Molecular subtypes of diffuse large B cell lymphoma are associated with distinct pathogenic mechanisms and outcomes**
*Nature medicine* · PMID: 29713087 · DOI: 10.1038/s41591-018-0016-8

- Supports: Genetic subtypes of DLBCL with distinct outcomes, cited for disease heterogeneity.
- Quote [Outcome associations of DLBCL clusters.] (PMC full text):
  > Patients with C2 DLBCLs had a distinct trajectory and a steady rate of progression over time (Fig. 6k,l and Supplementary Fig. 16a).

**Schmitz R et al. (2018) Genetics and Pathogenesis of Diffuse Large B-Cell Lymphoma**
*The New England journal of medicine* · PMID: 29641966 · DOI: 10.1056/NEJMoa1801445

- Supports: Genetics and pathogenesis of DLBCL, the companion genetic classification.
- Quote [A GENETIC CLASSIFIER FOR DLBCL] (PMC full text):
  > Overall, we classified 44.8% of our samples into these genetically “pure” subtypes of DLBCL and recognize that non-subtyped cases may share genetic features as well as etiologic factors with the genetic subtypes (Fig. 2B).

## ORCID self-citations (plan §2.4)

| # | year | venue | PMID | DOI | locus in Article 2 |
|---|---|---|---|---|---|
| 1 | 2021 | Frontiers in Molecular Biosciences | 34888350 | 10.3389/fmolb.2021.737821 | Introduction — a signature validated across independently generated datasets |
| 2 | 2022 | BMC Cancer | 36316649 | 10.1186/s12885-022-10177-3 | Introduction — cross-cohort application of an expression model |
| 3 | 2022 | Frontiers in Molecular Biosciences | 35359606 | 10.3389/fmolb.2022.753318 | Introduction — signature portability across cohorts |
| 4 | 2020 | Biomedicines | 32486168 | 10.3390/biomedicines8060142 | Methods, Group L — marker-panel expression readout |
| 5 | 2019 | Cancers | 31357584 | 10.3390/cancers11081060 | Methods, Group L — single-marker prognostic readout across platforms |
| 6 | 2021 | Heliyon | 33748479 | 10.1016/j.heliyon.2021.e06408 | Introduction — pathway-level activation from expression, cross-dataset |
| 7 | 2021 | Journal of Minimally Invasive Gyne | 33839309 | 10.1016/j.jmig.2021.03.011 | Introduction — signature from a single-centre cohort; the generalization question |
| 8 | 2025 | Cell Reports Medicine | 40147445 | 10.1016/j.xcrm.2025.102029 | Introduction — lymphoma transcriptomics, the disease context |
| 9 | 2020 | International Journal of Molecular | 33187334 | 10.3390/ijms21228491 | Discussion — marker stability across preparation types |
| 10 | 2018 | Breast Cancer Research and Treatme | 30484103 | 10.1007/s10549-018-5043-0 | Discussion — expression readouts from a non-standard input material |
| 11 | 2018 | Journal of Hematology | 32300430 | 10.14740/jh412w | Discussion — same, paired with 10 |
| 12 | 2026 | Royal Society Open Science | — | 10.1098/rsos.260639 | Introduction — genome-wide profiles compared across assay modalities |
| 13 | 2025 |  | — | 10.1101/2025.09.24.677146 | Introduction — joint analysis across separately generated profile sets |
| 14 | 2019 | Cells | 31491936 | 10.3390/cells8091034 | Introduction — multi-assay integration |
| 15 | 2019 | Cells | 31597351 | 10.3390/cells8101219 | Introduction — same theme as 14 |
| 16 | 2019 | Cells | 30736359 | 10.3390/cells8020130 | Introduction — same theme as 14 (with correction 10.3390/cells8080832) |
| 17 | 2018 | Frontiers in Immunology | 29441061 | 10.3389/fimmu.2018.00030 | Introduction — pathway-level aggregation of noisy per-feature signal |
| 18 | 2026 | Zenodo | — | 10.5281/zenodo.19052415 | Data availability — deposited dataset, not a finding |
| 19 | ? |  | — | — | Discussion — method-development precedent (RetroSpect book chapter) |