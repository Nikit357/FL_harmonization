# Article 2 - provenance of every number and every citation (run 260919_run1, delivery)

## Status

**Complete.**

- Number provenance: all 452 distinct numeric tokens of `manuscript/FL_metric_classes_F1000_260917.md` indexed against the nine `tables/A2_T*.csv` files, column by column, and against the named table/column/filter entries of `workflow_runs/260919_run1/01_numbers.json`.
- Citation provenance: all 52 reference entries mapped to their PMID (or the registry that resolved them), to the passage the reference verifier quoted, and to the manuscript sections that cite them.
- Gates re-run by the team lead on the delivered files at 2026-09-19: `audit_numbers.py` (exit 1, 6 tokens), `check_style.py` (exit 0), `check_overlap.py` (exit 0 on all three manuscript .md files).
- An independent 20% sample of the reference list (11 of 52, `random.seed(20260919)`) re-resolved against NCBI eSummary by the team lead; 11 of 11 match on title, year, volume, pagination and first author.
- The three values that rule 1 cannot cover (198, 1,359.6 and 555,004.7, standing in two sentences) were re-derived from the upstream snapshot `metrics_comprehensive_260905.csv`, so their real locus is on record.

**Not started.**

- Figma frame check (rule 5). This session has no Figma read capability and no before/after Page 2 geometry snapshot exists in the run folder, so the check was not run. See `06_open_items.md`.

**Not done by design.** Nothing in the manuscript was edited at this gate. Delivery has no revision round: every surviving defect is written into `06_open_items.md` instead of being fixed silently.

---

## 1. How this index was built

```bash
source ~/venvs/collagen_3_11/bin/activate
cd <repo>/article_2_extended_comparison
python tools/audit_numbers.py manuscript/FL_metric_classes_F1000_260917.md \
       --tables tables/ --evidence workflow_runs/260919_run1/01_numbers.json
python tools/check_style.py  manuscript/FL_metric_classes_F1000_260917.md --journal f1000
python tools/check_overlap.py manuscript/FL_metric_classes_F1000_260917.md
```

`audit_numbers.py` answers only whether a value is present somewhere in the evidence. For this index every table was additionally indexed **column by column** (each column at every rounding from 0 to 4 decimals, plus row counts and per-category value counts), so each manuscript number carries the table *and* column that holds it. Where `01_numbers.json` names the table, column and filter for a quantity, that entry is authoritative and is reproduced verbatim in the index; 142 of the 452 tokens carry such an entry.

**Read the index with one caveat.** A locus is a presence match, not a proof of meaning: a common value such as `0.810` occurs in 115 columns of `A2_T1`, and a match can be coincidental, as it is for 198 and 1,359.6 in section 3 below. A presence match plus a named evidence entry, or plus a re-derivation recorded here, is provenance; a presence match alone is only a check that the value exists in the data.

## 2. Summary

| quantity | n |
|---|---|
| distinct numbers | 452 |
| direct cell locus in tables | 428 |
| derived from a tables file under a named filter | 9 |
| locus outside tables prediction folds long | 7 |
| no locus anywhere under tables | 3 |
| not a measurement or cited fact | 5 |
| citations | 52 |
| citations with numeric pmid | 47 |
| citations resolved at another registry | 5 |
| verdict supports | 49 |
| verdict partial | 3 |

## 3. Numbers that do not sit in a single cell of `tables/` (the whole of the rule 1 exposure, classified)

Every number in this section was re-derived by the team lead this run, so each value is known to be right. Only the three rows marked **NO LOCUS under tables/** (198, 1,359.6, 555,004.7) are rule 1 failures: their locus is the upstream snapshot `metrics_comprehensive_260905.csv`, which is not under `tables/`. Seven rows have their locus in `prediction_folds_long.csv`, also outside `tables/`, and are named in `01_numbers.json` with column and filter. Nine are ordinary derived statistics over a `tables/` file under a filter that is named here. Five are not measurements at all (two postal codes, the 633-gene panel and the 2,407 pre-filter approaches cited to [38], and the 1,000-gene KS design constant).

| number | section | class | where it really comes from |
|---|---|---|---|
| 02453 | Metric classes elect non-overlapping sets of h | not a measurement | Postal code in the affiliation block (affiliation 2, postal code 02453). Audit artefact. |
| 0014 | Metric classes elect non-overlapping sets of h | not a measurement | Postal code in the affiliation block (Yerevan, 0014, Armenia). It carries a presence match in 134 table columns, all of them coincidental - the same over-reading of a presence match as in D7. |
| 32,746 | Abstract | derived from tables/A2_T8 | A2_T8, column n_folds, the three batch == "__ALL__" rows: 15,436 + 9,821 + 7,489 = 32,746. Re-derived by the team lead this run. |
| 633 | The biology-facing metric classes L, M and N | cited fact, source benchmark [38] | Size of the marker panel of the source benchmark; attributed in text to [38], whose record the reference verifier confirmed. Not a value this article computes. |
| 1,000 | Metric classes capture non-overlapping compone | design constant of the source metric | Number of randomly drawn genes in the KS distributional metric of the source benchmark. A parameter, not a result. |
| 1,359 | Metric classes capture non-overlapping compone | NO LOCUS under tables/ | The manuscript value is 1,359.6; the only match under tables/ is the unrelated fold count 1359 in A2_T8.n_folds, so the match is spurious. Re-derived from metrics_comprehensive_260905.csv, column exp_median, over the 84 rows with method == 20_shambhala: mean 1,359.6 (median 1,348.7, max 1,401.8). The value is right, the sentence calls the mean a median, and the file is not under tables/. |
| 555,004 | Metric classes capture non-overlapping compone | NO LOCUS under tables/ | Re-derived by the team lead 2026-09-19 from metrics_comprehensive_260905.csv, column exp_max, over the 84 rows with method == 20_shambhala: mean 555,004.7 (median 335,452.2, max 1,873,593.6). The companion 1,359.6 is the mean of exp_median over the same 84 rows (median 1,348.7, max 1,401.8). Correct values, wrong statistic named in the sentence, and the file is not under tables/. |
| 198 | Global variance-based metrics saturate below t | NO LOCUS under tables/ | The only match under tables/ is a group count in A2_T5 that means something else, so the match is spurious. Re-derived by the team lead 2026-09-19 from metrics_comprehensive_260905.csv, column pcr_RNA_BATCH > 0.9999, after the shambhala_P0std_Q0std -> 20_shambhala rename and an inner join to the 2,234-row (strat, imp, method, post_rm) key of A2_T1: n = 198, from exactly 03_limma, 07_pycombat, 13_fsmvn, 21_harmonizr, 28_npn and 33_amdbnorm, of which 98.5% have kbet_acceptance_rate_RNA_BATCH < 0.1. The value is right; the file is not under tables/. |
| 1,686 | Preservation of biomarker expression and of cr | derived from tables/A2_T1 | A2_T1, columns mk_rho_mean_markers and xb_margin, filter rho > 0.75 AND margin > 0: 1,686 of 2,234 = 75.5%. Re-derived this run. |
| 141 | Preservation of biomarker expression and of cr | derived from tables/A2_T1 | A2_T1, same joint filter, grouped by strat: C_rnaseq_only 141 of 168, J_ff_only 130 of 164, S0_no_removal 130 of 165, K_ffpe_only 76 of 164, 01_raw 80 of 84. Re-derived this run. |
| 17,310 | Cross-batch prediction elects a third set, who | derived from tables/A2_T8 | A2_T8, column n_folds, batch == "__ALL__" AND n_classes >= 2: 9,821 + 7,489 = 17,310. Re-derived this run. |
| 53,737 | Cross-batch prediction elects a third set, who | locus outside tables/ | prediction_folds_long.csv, column target == "3class", no run_id restriction. Named in 01_numbers.json (fold_population_denominators.unrestricted_3class_folds). Upstream file, not under tables/. |
| 3,738 | Cross-batch prediction elects a third set, who | locus outside tables/ | prediction_folds_long.csv, column run_id, whole table (94,582 rows, 50 method names). Named in 01_numbers.json. |
| 20,991 | Cross-batch prediction elects a third set, who | locus outside tables/ | prediction_folds_long.csv, target == "3class" folds whose run_id is outside the 2,234-approach analysis set. Named in 01_numbers.json (unrestricted_fold_denominators). |
| 20,343 | Cross-batch prediction elects a third set, who | locus outside tables/ | prediction_folds_long.csv, the part of the 20,991 belonging to the 17 non-canonical Shambhala P/Q variants. Named in 01_numbers.json; corrected at gate 1 from 21,543. |
| 648 | Cross-batch prediction elects a third set, who | locus outside tables/ | prediction_folds_long.csv, the residual of 20,991 - 20,343, belonging to 34_arsyn and 38_harman. Named in 01_numbers.json. |
| 1,200 | Cross-batch prediction elects a third set, who | locus outside tables/ | prediction_folds_long.csv, folds contributed by the retained canonical Shambhala variant. Named in 01_numbers.json. |
| 25,426 | Cross-batch prediction elects a third set, who | locus outside tables/ | prediction_folds_long.csv, target == "3class" AND n_classes == 1, no run_id restriction (47.3%). Named in 01_numbers.json and labelled in the manuscript as the earlier unrestricted count. |
| 2,174 | Cross-batch prediction elects a third set, who | derived from tables/A2_T2 | A2_T2, rows with both pv_lobo3_f1_macro_mean and f1_mc_mean present: n = 2,174, Spearman 0.810. Re-derived this run. |
| 2,058 | Cross-batch prediction elects a third set, who | derived from tables/A2_T2 | A2_T2, same pair of columns with n_mc >= 3: n = 2,058, Spearman 0.815. Re-derived this run. |
| 1,527 | Cross-batch prediction elects a third set, who | derived from tables/A2_T2 | A2_T2, strat not in (A_confirmed_bad, B_extended_bad) AND n_mc >= 5: n = 1,527. Re-derived this run. |
| 323 | Cross-batch prediction elects a third set, who | derived from tables/A2_T2 | A2_T2, rank of generalizability_index (descending, method="min") over the 15 is_clustermap_best rows: min 323, max 2,038 of 2,234. Re-derived this run. |
| 2,038 | Cross-batch prediction elects a third set, who | derived from tables/A2_T2 | A2_T2, as 323: the maximum rank of the 15 clustermap rows. Re-derived this run. |
| 2,407 | Supplementary material | cited fact, source benchmark [38] | Completed approaches of the source benchmark before the pct_samples_allNA < 5 cut; attributed in text to [38]. |

## 4. Citation provenance (52 entries)

Verdicts are the reference verifier's, re-keyed here from the pre-gate-3 numbering (former [51], [54] and [55] removed; former [52] and [53] became [51] and [52]). Three PARTIAL verdicts were raised against sentences that the writer then narrowed at gate 3; the narrowed sentence is what stands in the manuscript.

| # | PMID / registry | first author, journal, year | verdict | passage section | cited in |
|---|---|---|---|---|---|
| 1 | 20838408 | Leek JT, Scharpf RB, Bravo HC, et al. Tackling the widesprea | SUPPORTS -- verified against the body of the cited article, not the abstract | Introduction | Introduction |
| 2 | 22851511 | Lazar C, Meganck S, Taminau J, et al. Batch effect removal m | SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment | Abstract | Introduction |
| 3 | 36140419 | Borisov N, Buzdin A. Transcriptomic Harmonization as the Way | SUPPORTS -- verified against the body of the cited article, not the abstract | Section 4, "Application Notes" | Introduction |
| 4 | 22151536 | Rudy J, Valafar F. Empirical comparison of cross-platform no | SUPPORTS -- verified against the body of the cited article, not the abstract | Results and Discussion, "Initial evaluat | Introduction |
| 5 | 26844019 | Thompson JA, Tan J, Greene CS. Cross-platform normalization  | SUPPORTS -- verified against the body of the cited article, not the abstract | Methods, "Evaluation of TDM for supervis | Introduction |
| 6 | 34949812 | Luecken MD, Büttner M, Chaichoompu K, et al. Benchmarking at | SUPPORTS -- verified against the body of the cited article, not the abstract | Results, "Balancing batch removal and bi | Introduction |
| 7 | 31948481 | Tran HTN, Ang KS, Chevrier M, et al. A benchmark of batch-ef | SUPPORTS -- verified against the body of the cited article, not the abstract | Discussion, "Batch integration assessmen | Introduction |
| 8 | 30573817 | Büttner M, Miao Z, Wolf FA, et al. A test metric for assessi | SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment | Abstract | Introduction |
| 9 | 31740819 | Korsunsky I, Millard N, Fan J, et al. Fast, sensitive and ac | SUPPORTS -- verified against the body of the cited article, not the abstract | Results (definition of the metric) | Introduction |
| 10 | 10676951 | Alizadeh AA, Eisen MB, Davis RE, et al. Distinct types of di | SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment | Abstract | Introduction |
| 11 | 12075054 | Rosenwald A, Wright G, Chan WC, et al. The use of molecular  | SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment | Abstract, Results | Introduction |
| 12 | 15548776 | Dave SS, Wright G, Tan B, et al. Prediction of survival in f | SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment | Abstract, Results and Conclusions | Introduction |
| 13 | 29475724 | Huet S, Tesson B, Jais JP, et al. A gene-expression profilin | SUPPORTS -- verified against the body of the cited article, not the abstract | Results, "Predictive model of progressio | Introduction |
| 14 | 24398326 | Scott DW, Wright GW, Williams PM, et al. Determining cell-of | SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment | Abstract | Introduction |
| 15 | 29713087 | Chapuy B, Stewart C, Dunford AJ, et al. Molecular subtypes o | SUPPORTS -- verified against the body of the cited article, not the abstract | Methods, "Patient samples" | Introduction |
| 16 | 29641966 | Schmitz R, Wright GW, Huang DW, et al. Genetics and Pathogen | SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment | Abstract, Methods and Results | Introduction |
| 17 | 34888350 | Sorokin M, Rabushko E, Efimov V, et al. Experimental and Met | SUPPORTS -- verified against the body of the cited article, not the abstract | Abstract / Results | Introduction |
| 18 | 36316649 | Sorokin M, Zolotovskaia M, Nikitin D, et al. Personalized ta | SUPPORTS -- verified against the body of the cited article, not the abstract | Background | Introduction |
| 19 | 35359606 | Gudkov A, Shirokorad V, Kashintsev K, et al. Gene Expression | SUPPORTS -- verified against the body of the cited article, not the abstract | Abstract / Results | Introduction |
| 20 | 33748479 | Vladimirova U, Rumiantsev P, Zolotovskaia M, et al. DNA repa | SUPPORTS -- verified against the body of the cited article, not the abstract | Discussion | Introduction |
| 21 | 33839309 | Adamyan L, Aznaurova Y, Stepanian A, et al. Gene Expression  | SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment | Abstract, Study objective (full text not | Introduction |
| 22 | 40147445 | Fiore D, Cappelli LV, Zhaoqi L, et al. A patient-derived T c | PARTIAL -- verified against the body of the cited article, not the abstract | Results, "PDXs preserve the transcriptom | Introduction |
| 23 | none | Nikitin DM. Transposable element-host genome evolutionary ar | SUPPORTS -- verified against the publisher or registry record; the full text is not reachable from this environment | Abstract (publisher record; article full | Introduction |
| 24 | none | Nikitin D. Joint analysis of human retroelements-linked hist | SUPPORTS -- verified against the publisher or registry record; the full text is not reachable from this environment | Abstract (bioRxiv record, version 2) | Introduction |
| 25 | 31491936 | Igolkina AA, Zinkevich A, Karandasheva KO, et al. H3K4me3, H | SUPPORTS -- verified against the body of the cited article, not the abstract | Materials and Methods, "Gene Expression  | Introduction |
| 26 | 31597351 | Nikitin D, Kolosov N, Murzina A, et al. Retroelement-Linked  | SUPPORTS -- verified against the body of the cited article, not the abstract | Materials and Methods, "Identification o | Introduction |
| 27 | 30736359 | Nikitin D, Garazha A, Sorokin M, et al. Retroelement-Linked  | SUPPORTS -- verified against the body of the cited article, not the abstract | Results | Introduction |
| 28 | 29441061 | Nikitin D, Penzar D, Garazha A, et al. Profiling of Human Mo | SUPPORTS -- verified against the body of the cited article, not the abstract | Results, "Mapping of RE-Specific Human T | Introduction |
| 29 | 24967636 | Soneson C, Gerster S, Delorenzi M. Batch effect confounding  | SUPPORTS -- verified against the body of the cited article, not the abstract | Introduction (statement of findings) | Introduction; The biology-facing metric classes  |
| 30 | 22611599 | Parker HS, Leek JT. The practical effect of batch on genomic | SUPPORTS -- verified against the body of the cited article, not the abstract | Introduction | Introduction; The biology-facing metric classes  |
| 31 | none | Cawley GC, Talbot NLC. On over-fitting in model selection an | SUPPORTS -- verified against the body of the cited article, not the abstract | Section 1, Introduction | Introduction |
| 32 | 16504092 | Varma S, Simon R. Bias in error estimation when using cross- | SUPPORTS -- verified against the body of the cited article, not the abstract | Results / Abstract-Conclusion section of | Introduction |
| 33 | 11983868 | Ambroise C, McLachlan GJ. Selection bias in gene extraction  | SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment | Abstract | Introduction |
| 34 | 28327985 | Saeb S, Lonini L, Jayaraman A, et al. The need to approximat | PARTIAL -- verified against the body of the cited article, not the abstract | Introduction | Introduction; The biology-facing metric classes  |
| 35 | 37720327 | Kapoor S, Narayanan A. Leakage and the reproducibility crisi | SUPPORTS -- verified against the body of the cited article, not the abstract | Results, "Toward a solution: A taxonomy  | Introduction |
| 36 | 34837041 | Whalen S, Schreiber J, Noble WS, et al. Navigating the pitfa | SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment | Abstract | Introduction |
| 37 | none | Bengio Y, Grandvalet Y. No unbiased estimator of the varianc | SUPPORTS -- verified against the body of the cited article, not the abstract | Section 4, "No Unbiased Estimator of Var | Introduction |
| 38 | none | Nikitin D, Borisov NM, Savchenko M, et al. Benchmarking of b | SUPPORTS -- verified against the body of the cited article, not the abstract | Results, analysis-set definition (verifi | Data availability; Dataset, harmonization approaches ; Global variance-based metrics satu; |
| 39 | 16632515 | Johnson WE, Li C, Rabinovic A. Adjusting batch effects in mi | SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment | Abstract | Dataset, harmonization approaches  |
| 40 | 33015620 | Zhang Y, Parmigiani G, Johnson WE. ComBat-seq: batch effect  | SUPPORTS -- verified against the body of the cited article, not the abstract | Abstract / Results | Dataset, harmonization approaches  |
| 41 | 17907809 | Leek JT, Storey JD. Capturing heterogeneity in gene expressi | SUPPORTS -- verified against the body of the cited article, not the abstract | Introduction | Dataset, harmonization approaches  |
| 42 | 29608177 | Haghverdi L, Lun ATL, Morgan MD, et al. Batch effects in sin | SUPPORTS -- verified against the body of the cited article, not the abstract | Introduction | Dataset, harmonization approaches  |
| 43 | 29360996 | Franks JM, Cai G, Whitfield ML. Feature specific quantile no | SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment | Abstract, Results | Dataset, harmonization approaches  |
| 44 | 18325927 | Shabalin AA, Tjelmeland H, Fan C, et al. Merging two gene-ex | SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment | Abstract, Results | Dataset, harmonization approaches  |
| 45 | 30727942 | Borisov N, Shabalina I, Tkachev V, et al. Shambhala: a platf | SUPPORTS -- verified against the body of the cited article, not the abstract | Abstract / Background | Dataset, harmonization approaches  |
| 46 | 35617464 | Borisov N, Sorokin M, Zolotovskaya M, et al. Shambhala-2: A  | SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment | Abstract | Dataset, harmonization approaches  |
| 47 | 25150836 | Risso D, Ngai J, Speed TP, et al. Normalization of RNA-seq d | SUPPORTS -- verified against the body of the cited article, not the abstract | Results, "Removing unwanted variation th | The biology-facing metric classes  |
| 48 | 32486168 | Sorokin M, Kholodenko I, Kalinovsky D, et al. RNA Sequencing | SUPPORTS -- verified against the body of the cited article, not the abstract | Results / Abstract | The biology-facing metric classes  |
| 49 | 31357584 | Jovčevska I, Zottel A, Šamec N, et al. High FREM2 Gene and P | PARTIAL -- verified against the body of the cited article, not the abstract | Results / Abstract | The biology-facing metric classes  |
| 50 | 33187334 | Zottel A, Šamec N, Kump A, et al. Analysis of miR-9-5p, miR- | SUPPORTS -- verified against the body of the cited article, not the abstract | Abstract / Results | Preservation of biomarker expressi |
| 51 | 32300430 | Shtam T, Naryzhny S, Kopylov A, et al. Functional Properties | SUPPORTS -- verified against the body of the cited article, not the abstract | Conclusion | Preservation of biomarker expressi |
| 52 | 26272994 | Nygaard V, Rødland EA, Hovig E. Methods that remove batch ef | SUPPORTS -- verified against the body of the cited article, not the abstract | Discussion | Cross-batch prediction elects a th |

### 4b. The supporting passage behind each citation

**[1]** Leek JT, Scharpf RB, Bravo HC, et al. Tackling the widespread and critical impact of batch effects in high-throughput data. Nat Rev Genet. 2010;11(10):733-9. doi:10.1038/nrg2825  
PMID line: `20838408` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Introduction): "This becomes a major problem when batch effects are correlated with an outcome of interest and lead to incorrect conclusions. Using both published studies and our own analyses, we argue that batch effects (as well as other technical and biological artefacts) are widespread and critical to address. We review experimenta"

**[2]** Lazar C, Meganck S, Taminau J, et al. Batch effect removal methods for microarray gene expression data integration: a survey. Brief Bioinform. 2013;14(4):469-90. doi:10.1093/bib/bbs037  
PMID line: `22851511` · verdict: SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment. The entry is cited only for the existence of a catalogue of microarray batch-effe  
Passage (Abstract): "It has been acknowledged that the main source of variation between different MAGE datasets is due to the so-called 'batch effects'. The methods reviewed here perform data integration by removing (or more precisely attempting to remove) the unwanted variation associated with batch effects. They are presented in a unifie"

**[3]** Borisov N, Buzdin A. Transcriptomic Harmonization as the Way for Suppressing Cross-Platform Bias and Batch Effect. Biomedicines. 2022;10(9):2318. doi:10.3390/biomedicines10092318  
PMID line: `36140419` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract. Cited twice; the second citing sentence, on the absence of an agreed standard, is carried by the same Application Notes pa  
Passage (Section 4, "Application Notes"): "However, for the cross-platform harmonization, dozens of methods were developed for both MH and NGS types of gene expression data, but none of them was so far recognized as the gold standard."

**[4]** Rudy J, Valafar F. Empirical comparison of cross-platform normalization methods for gene expression data. BMC Bioinformatics. 2011;12:467. doi:10.1186/1471-2105-12-467  
PMID line: `22151536` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Results and Discussion, "Initial evaluation"): "Inspection of the ROC-like curves shows that the lower levels of over-detection among MRS, DisTran, and QN can be understood in terms of lower total detection of differentially expressed genes. By all three measurements, the seven methods cluster into two groups. The first group, made up of DWD, EB, GQ, and XPN, is cha"

**[5]** Thompson JA, Tan J, Greene CS. Cross-platform normalization of microarray and RNA-seq data for machine learning applications. PeerJ. 2016;4:e1621. doi:10.7717/peerj.1621  
PMID line: `26844019` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Methods, "Evaluation of TDM for supervised model construction using LASSO-logistic regression"): "For a supervised machine learning approach, we performed LASSO multinomial logistic regression to train models (on microarray datasets) for predicting tumor subtype in breast cancer and CIMP status in colon and rectal cancer, using the glmnet package (Friedman, Hastie & Tibshirani, 2010) in the R statistical environmen"

**[6]** Luecken MD, Büttner M, Chaichoompu K, et al. Benchmarking atlas-level data integration in single-cell genomics. Nat Methods. 2022;19(1):41-50. doi:10.1038/s41592-021-01336-8  
PMID line: `34949812` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Results, "Balancing batch removal and biological variance conservation"): "Particularly in more complex integration tasks, we observed a tradeoff between batch effect removal and bio-conservation (Fig. 3a and Supplementary Data 1). While methods such as SAUCIE, LIGER, BBKNN and Seurat v3 tend to favor the removal of batch effects over conservation of biological variation, DESC and Conos make "

**[7]** Tran HTN, Ang KS, Chevrier M, et al. A benchmark of batch-effect correction methods for single-cell RNA sequencing data. Genome Biol. 2020;21(1):12. doi:10.1186/s13059-019-1850-9  
PMID line: `31948481` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Discussion, "Batch integration assessment methods"): "In the first four scenarios, the assessment metrics did not always agree with each other, nor did the metrics always agree with our visual inspections of t-SNE and UMAP plots."

**[8]** Büttner M, Miao Z, Wolf FA, et al. A test metric for assessing single-cell RNA-seq batch correction. Nat Methods. 2019;16(1):43-49. doi:10.1038/s41592-018-0254-1  
PMID line: `30573817` · verdict: SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment. kBET is cited as a metric contributed by the single-cell literature, which the ab  
Passage (Abstract): "The success of batch-effect correction is often evaluated by visual inspection of low-dimensional embeddings, which are inherently imprecise. Here we present a user-friendly, robust and sensitive k-nearest-neighbor batch-effect test (kBET; https://github.com/theislab/kBET ) for quantification of batch effects."

**[9]** Korsunsky I, Millard N, Fan J, et al. Fast, sensitive and accurate integration of single-cell data with Harmony. Nat Methods. 2019;16(12):1289-1296. doi:10.1038/s41592-019-0619-0  
PMID line: `31740819` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Results (definition of the metric)): "In order to quantify integration and accuracy of this embedding we defined an objective metric: the Local Inverse Simpson's Index (LISI, online methods) in the local neighborhood of each cell. To assess integration, we employ “integration LISI” (iLISI, Figure 2A), which defines the effective number of datasets in a nei"

**[10]** Alizadeh AA, Eisen MB, Davis RE, et al. Distinct types of diffuse large B-cell lymphoma identified by gene expression profiling. Nature. 2000;403(6769):503-11. doi:10.1038/35000501  
PMID line: `10676951` · verdict: SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment.  
Passage (Abstract): "We identified two molecularly distinct forms of DLBCL which had gene expression patterns indicative of different stages of B-cell differentiation. One type expressed genes characteristic of germinal centre B cells ('germinal centre B-like DLBCL'); the second type expressed genes normally induced during in vitro activat"

**[11]** Rosenwald A, Wright G, Chan WC, et al. The use of molecular profiling to predict survival after chemotherapy for diffuse large-B-cell lymphoma. N Engl J Med. 2002;346(25):1937-47. doi:10.1056/NEJMoa01  
PMID line: `12075054` · verdict: SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment.  
Passage (Abstract, Results): "We used 17 genes to construct a predictor of overall survival after chemotherapy. This gene-based predictor and the international prognostic index were independent prognostic indicators."

**[12]** Dave SS, Wright G, Tan B, et al. Prediction of survival in follicular lymphoma based on molecular features of tumor-infiltrating immune cells. N Engl J Med. 2004;351(21):2159-69. doi:10.1056/NEJMoa041  
PMID line: `15548776` · verdict: SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment.  
Passage (Abstract, Results and Conclusions): "Flow cytometry showed that these signatures reflected gene expression by nonmalignant tumor-infiltrating immune cells. Conclusions The length of survival among patients with follicular lymphoma correlates with the molecular features of nonmalignant immune cells present in the tumor at diagnosis."

**[13]** Huet S, Tesson B, Jais JP, et al. A gene-expression profiling score for prediction of outcome in patients with follicular lymphoma: a retrospective training and validation analysis in three internatio  
PMID line: `29475724` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Results, "Predictive model of progression-free survival"): "The 23-gene expression signature scores ranged from 0.621 to 1.504 in the training cohort. The C-statistic was 0.709 (95% confidence interval [CI]: 0.644-0.773), outperforming FLIPI-1 (0.578, 95%CI: 0.501-0.655). A score of 1.075 was determined as the optimal threshold (appendix p 13) to separate patients into high-"

**[14]** Scott DW, Wright GW, Williams PM, et al. Determining cell-of-origin subtypes of diffuse large B-cell lymphoma using gene expression in formalin-fixed paraffin-embedded tissue. Blood. 2014;123(8):1214-  
PMID line: `24398326` · verdict: SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment.  
Passage (Abstract): "The Lymphoma/Leukemia Molecular Profiling Project's Lymph2Cx assay is a parsimonious digital gene expression (NanoString)-based test for COO assignment in formalin-fixed paraffin-embedded tissue (FFPET)."

**[15]** Chapuy B, Stewart C, Dunford AJ, et al. Molecular subtypes of diffuse large B cell lymphoma are associated with distinct pathogenic mechanisms and outcomes. Nat Med. 2018;24(5):679-690. doi:10.1038/s4  
PMID line: `29713087` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Methods, "Patient samples"): "Our multi-institutional, international group assembled a cohort of 351 patient samples diagnosed with a previously untreated, primary diffuse large B-cell lymphoma (DLBCL) of which 304 passed all below described quality controls. This 304 sample dataset was obtained from 4 sources"

**[16]** Schmitz R, Wright GW, Huang DW, et al. Genetics and Pathogenesis of Diffuse Large B-Cell Lymphoma. N Engl J Med. 2018;378(15):1396-1407. doi:10.1056/NEJMoa1801445  
PMID line: `29641966` · verdict: SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment. Supports "genetic subtypes of DLBCL are defined". The "cohorts assembled from sev  
Passage (Abstract, Methods and Results): "We studied 574 DLBCL biopsy samples using exome and transcriptome sequencing, array-based DNA copy-number analysis, and targeted amplicon resequencing of 372 genes to identify genes with recurrent aberrations. We developed and implemented an algorithm to discover genetic subtypes based on the co-occurrence of genetic a"

**[17]** Sorokin M, Rabushko E, Efimov V, et al. Experimental and Meta-Analytic Validation of RNA Sequencing Signatures for Predicting Status of Microsatellite Instability. Front Mol Biosci. 2021;8:737821. doi  
PMID line: `34888350` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Abstract / Results): "They had 25, 15, and 14 gene products with only one common gene. However, they were developed and tested on the incomplete literature of The Cancer Genome Atlas (TCGA) sampling and never validated experimentally on independent RNAseq samples. In this study, we, for the first time, systematically validated these three R"

**[18]** Sorokin M, Zolotovskaia M, Nikitin D, et al. Personalized targeted therapy prescription in colorectal cancer using algorithmic analysis of RNA sequencing data. BMC Cancer. 2022;22(1):1113. doi:10.1186  
PMID line: `36316649` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract. The strongest of the six: its Background states the cross-platform comparability problem explicitly.  
Passage (Background): "However, RNA sequencing profiles can be obtained using different equipment, reagents and protocols and sometimes can be poorly compatible thus making their direct comparison problematic [31, 32]. In order to obtain comparable results, ideally the same experimental platform should be used for all biosamples in a given s"

**[19]** Gudkov A, Shirokorad V, Kashintsev K, et al. Gene Expression-Based Signature Can Predict Sorafenib Response in Kidney Cancer. Front Mol Biosci. 2022;9:753318. doi:10.3389/fmolb.2022.753318  
PMID line: `35359606` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract. The signature is carried across sample sets and across assay types (RNA sequencing to qRT-PCR), which is the transfer sett  
Passage (Abstract / Results): "We validated these findings on another set of 13 experimental annotated FFPE RCC samples (for 2 PR, 1 SD, and 10 PD patients) that were profiled by RNA sequencing and observed AUC 0.97 for 8-gene signature as the response classifier."

**[20]** Vladimirova U, Rumiantsev P, Zolotovskaia M, et al. DNA repair pathway activation features in follicular and papillary thyroid tumors, interrogated using 95 experimental RNA sequencing profiles. Heliy  
PMID line: `33748479` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract. Topical support plus one Discussion sentence that names harmonization of expression profile formats as the route to combin  
Passage (Discussion): "However, these datasets can be combined with the previously published or future data collections e.g. using harmonization of gene expression profiles data formats"

**[21]** Adamyan L, Aznaurova Y, Stepanian A, et al. Gene Expression Signature of Endometrial Samples from Women with and without Endometriosis. J Minim Invasive Gynecol. 2021;28(10):1774-1785. doi:10.1016/j.j  
PMID line: `33839309` · verdict: SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment. Topical support only: the paper builds an endometrial expression signature. It ma  
Passage (Abstract, Study objective (full text not reachable: subscription-only, no PMC record)): "To develop a prototype of a complex gene expression biomarker for the diagnosis of endometriosis on the basis of differences between the molecular signatures of the endometrium from women with and without endometriosis. Design Prospective observational cohort study. Evidence obtained from a well-designed, controlled tr"

**[22]** Fiore D, Cappelli LV, Zhaoqi L, et al. A patient-derived T cell lymphoma biorepository uncovers pathogenetic mechanisms and host-related therapeutic vulnerabilities. Cell Rep Med. 2025;6(4):102029. do  
PMID line: `40147445` · verdict: PARTIAL -- verified against the body of the cited article, not the abstract. The paper is a biorepository and PDX resource for T-cell lymphoma, not a signature-transfer study. It supports the topic na  
Passage (Results, "PDXs preserve the transcriptomic landscape of primary lymphomas"): "We first compared the transcriptomic profiles of primary (n = 79) and matched PDX (n = 140; Table S2) by principal-component analysis (PCA), demonstrating a partial overlap (Figure S3A), likely due to the tumor content (Figures S3B and S3C) and host human cells (Figures S3C–S3E). Hence, we performed a surrogate variabl"

**[23]** Nikitin DM. Transposable element-host genome evolutionary arms race revealed by multi-modal epigenomic profiling in a telomere-to-telomere human genome reference. R Soc Open Sci. 2026;13(8). doi:10.10  
PMID line: `none; not indexed in PubMed (searched by DOI and by title on 2026-09-19)` · verdict: SUPPORTS -- verified against the publisher or registry record; the full text is not reachable from this environment. Supports the clause it is cited for: seven epigenomic modalities analysed together   
Passage (Abstract (publisher record; article full text not reachable from this environment)): "Using the newly released telomere-to-telomere ENCODE dataset, I quantified the epigenetic impact of 3.7 million TEs across evolutionary time by analysing seven epigenomic modalities in twelve human cell lines."

**[24]** Nikitin D. Joint analysis of human retroelements-linked histone modification profiles reveals quickly evolving molecular processes connected with cancer. bioRxiv [preprint]. Posted 2025 Oct 2 (version  
PMID line: `none; not indexed in PubMed (searched by DOI and by title on 2026-09-19)` · verdict: SUPPORTS -- verified against the publisher or registry record; the full text is not reachable from this environment. Supports the clause: six histone-mark ChIP-seq profiles analysed jointly. See defec  
Passage (Abstract (bioRxiv record, version 2)): "Here, leveraging ChIP-seq profiles of histone modifications (H3K4me1, H3K4me3, H3K9ac, H3K27ac, H3K27me3, and H3K9me3) from five human cell lines deposited in the ENCODE database, we systematically ranked the regulatory impact of REs across 25,075 human genes."

**[25]** Igolkina AA, Zinkevich A, Karandasheva KO, et al. H3K4me3, H3K9ac, H3K27ac, H3K27me3 and H3K9me3 Histone Tags Suggest Distinct Regulatory Evolution of Open and Condensed Chromatin Landmarks. Cells. 20  
PMID line: `31491936` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract. Supports the setting named in the clause (five histone marks plus RNA sequencing from ENCODE analysed together). The paper  
Passage (Materials and Methods, "Gene Expression Data" / Results): "We ranked regulatory evolution rates of human genes and molecular pathways by using high throughput data on five histone marks from the ENCODE project [30] for five human cell lines. Based on H3K4me3, H3K9ac, H3K27ac, H3K27me3 and H3K9me3 histone tags, respectively, we investigated 25,075 human genes and 3121 molecular"

**[26]** Nikitin D, Kolosov N, Murzina A, et al. Retroelement-Linked H3K4me1 Histone Tags Uncover Regulatory Evolution Trends of Gene Enhancers and Feature Quickly Evolving Molecular Processes in Human Physiol  
PMID line: `31597351` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract. As [25]: supports the multi-assay setting, not the transfer problem.  
Passage (Materials and Methods, "Identification of RE-Linked H3K4me1 Modification Tags"): "Whole genome H3K4me1 ChIP-seq profiles for were extracted from the ENCODE database [34] for five human cell lines (K562, HepG2, GM12878, MCF-7, HeLa-S3) according to the standard ENCODE histone ChIP-seq protocol"

**[27]** Nikitin D, Garazha A, Sorokin M, et al. Retroelement-Linked Transcription Factor Binding Patterns Point to Quickly Developing Molecular Pathways in Human Evolution. Cells. 2019;8(2):130. doi:10.3390/c  
PMID line: `30736359` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract. As [25]: 563 transcription factor profiles over 13 cell lines from eight tissues, analysed together.  
Passage (Results): "in this study we investigated into the distributions of RE-linked hits for all 13 human cell lines TFBS-profiled for 563 DNA-binding proteins during ENCODE project [40] and representing eight different tissues/organs from the different individuals"

**[28]** Nikitin D, Penzar D, Garazha A, et al. Profiling of Human Molecular Pathways Affected by Retrotransposons at the Level of Regulation by Transcription Factor Proteins. Front Immunol. 2018;9:30. doi:10.  
PMID line: `29441061` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract. As [25]: ENCODE TFBS profiles from immunoprecipitation sequencing, analysed together.  
Passage (Results, "Mapping of RE-Specific Human TFBS"): "From the ENCODE database, we extracted TFBS information for the human myelogenous leukemia cell line K562. The TFBS data for different transcription factor proteins were based on the sequencing of immunoprecipitated DNA fragments"

**[29]** Soneson C, Gerster S, Delorenzi M. Batch effect confounding leads to strong bias in performance estimates obtained by cross-validation. PLoS One. 2014;9(6):e100335. doi:10.1371/journal.pone.0100335  
PMID line: `24967636` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract. Both citing sentences are supported by the same passage.  
Passage (Introduction (statement of findings)): "We find that in data sets where there are no genes that are truly differentially expressed between the two groups, the internal cross-validation performance estimate is only approximately unbiased when the batch effect is completely non-confounded with the class labels. Eliminating the batch effects can not correct the"

**[30]** Parker HS, Leek JT. The practical effect of batch on genomic prediction. Stat Appl Genet Mol Biol. 2012;11(3):Article 10. doi:10.1515/1544-6115.1766  
PMID line: `22611599` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract. Cited twice; the second citing sentence, on cutting folds by batch, rests on the same result.  
Passage (Introduction): "Furthermore, prediction accuracy could be erroneously overstated if batch and outcome are highly correlated, and batch proves to be easily predicted. In this scenario, prediction models would appear highly accurate, even under cross-validation in one study. However, the out-of-sample performance of these predictors wou"

**[31]** Cawley GC, Talbot NLC. On over-fitting in model selection and subsequent selection bias in performance evaluation. J Mach Learn Res. 2010;11(70):2079-2107. [JMLR assigns no DOI; opened at https://www.  
PMID line: `none; not indexed in PubMed (searched by title on 2026-09-19)` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Section 1, Introduction): "We show that some, apparently quite benign, performance evaluation protocols in common use by the machine learning community are susceptible to this form of bias, and thus potentially give spurious results. In order to avoid this bias, model selection must be treated as an integral part of the model fitting process and"

**[32]** Varma S, Simon R. Bias in error estimation when using cross-validation for model selection. BMC Bioinformatics. 2006;7:91. doi:10.1186/1471-2105-7-91  
PMID line: `16504092` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Results / Abstract-Conclusion section of the body): "The CV error estimate for the classifier with the optimal parameters was found to be a substantially biased estimate of the true error that the classifier would incur on independent data."

**[33]** Ambroise C, McLachlan GJ. Selection bias in gene extraction on the basis of microarray gene-expression data. Proc Natl Acad Sci U S A. 2002;99(10):6562-6. doi:10.1073/pnas.102102699  
PMID line: `11983868` · verdict: SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment. The PMC record for this article carries no body; the abstract states the selectio  
Passage (Abstract): "There is no allowance because the rule is either tested on tissue samples that were used in the first instance to select the genes being used in the rule or because the cross-validation of the rule is not external to the selection process; that is, gene selection is not performed in training the rule at each stage of t"

**[34]** Saeb S, Lonini L, Jayaraman A, et al. The need to approximate the use-case in clinical machine learning. Gigascience. 2017;6(5):1-9. doi:10.1093/gigascience/gix019  
PMID line: `28327985` · verdict: PARTIAL -- verified against the body of the cited article, not the abstract. The paper establishes that the cross-validation split has to match the use case, demonstrated for subject-wise against reco  
Passage (Introduction): "For CV to be valid, training and test sets need to be independent [30]. The definition of independence, however, depends on the use-case scenario. If the use-case is diagnosis, i.e., we want to develop global models that can be used for new subjects, CV must be subject-wise, meaning that the training and test sets cont"

**[35]** Kapoor S, Narayanan A. Leakage and the reproducibility crisis in machine-learning-based science. Patterns (N Y). 2023;4(9):100804. doi:10.1016/j.patter.2023.100804  
PMID line: `37720327` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Results, "Toward a solution: A taxonomy of data leakage" [L1.2]): "[L1.2] Pre-processing on training and test set. Using the entire dataset for any pre-processing steps, such as imputation or over/under sampling, results in leakage."

**[36]** Whalen S, Schreiber J, Noble WS, et al. Navigating the pitfalls of applying machine learning in genomics. Nat Rev Genet. 2022;23(3):169-181. doi:10.1038/s41576-021-00434-9  
PMID line: `34837041` · verdict: SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment. Full text not reachable here: no PMC record, and the free eScholarship copy is se  
Passage (Abstract): "We explore how the structure of genomics data can bias performance evaluations and predictions."

**[37]** Bengio Y, Grandvalet Y. No unbiased estimator of the variance of K-fold cross-validation. J Mach Learn Res. 2004;5:1089-1105. [JMLR assigns no DOI; opened at https://www.jmlr.org/papers/v5/grandvalet0  
PMID line: `none; not indexed in PubMed (searched by title on 2026-09-19)` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Section 4, "No Unbiased Estimator of Var[mu-hat] Exists"): "Lemma 4 There is no universal unbiased estimator of Var[ˆµ] that involves the ei in a non-quadratic way."

**[38]** Nikitin D, Borisov NM, Savchenko M, et al. Benchmarking of bulk transcriptomic harmonization tools in a multi-platform B-cell lymphoma cohort identifies feature-specific quantile normalization and sur  
PMID line: `none; preprint, not indexed in PubMed (searched by DOI on 2026-09-19)` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract. Ten citing sentences. Every number Article 2 attributes to the source benchmark was re-checked in the manuscript of the ci  
Passage (Results, analysis-set definition (verified in the local manuscript of the cited preprint, FL_harmonization_article_NAR_260912.docx)): "The full cross-product of these four factors yielded 2,234 successfully completed harmonization approaches that had fewer than 5% of samples with entirely missing gene expression values (by the condition pct_samples_allNA < 5), out of 2,407 approaches with harmonization completed with any resulting gene expression matr"

**[39]** Johnson WE, Li C, Rabinovic A. Adjusting batch effects in microarray expression data using empirical Bayes methods. Biostatistics. 2007;8(1):118-27. doi:10.1093/biostatistics/kxj037  
PMID line: `16632515` · verdict: SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment.  
Passage (Abstract): "We propose parametric and non-parametric empirical Bayes frameworks for adjusting data for batch effects that is robust to outliers in small sample sizes and performs comparable to existing methods for large samples."

**[40]** Zhang Y, Parmigiani G, Johnson WE. ComBat-seq: batch effect adjustment for RNA-seq count data. NAR Genom Bioinform. 2020;2(3):lqaa078. doi:10.1093/nargab/lqaa078  
PMID line: `33015620` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Abstract / Results): "We developed a batch correction method, ComBat-seq, using a negative binomial regression model that retains the integer nature of count data in RNA-seq studies, making the batch adjusted data compatible with common differential expression software packages that require integer counts."

**[41]** Leek JT, Storey JD. Capturing heterogeneity in gene expression studies by surrogate variable analysis. PLoS Genet. 2007;3(9):1724-35. doi:10.1371/journal.pgen.0030161  
PMID line: `17907809` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Introduction): "Here, we introduce “surrogate variable analysis” (SVA) to identify, estimate, and utilize the components of EH."

**[42]** Haghverdi L, Lun ATL, Morgan MD, et al. Batch effects in single-cell RNA-sequencing data are corrected by matching mutual nearest neighbors. Nat Biotechnol. 2018;36(5):421-427. doi:10.1038/nbt.4091  
PMID line: `29608177` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Introduction): "Here, we propose a new method for removal of discrepancies between biologically related batches based on the presence of mutual nearest neighbours (MNNs) between batches, which are considered to define the most similar cells of the same type across batches."

**[43]** Franks JM, Cai G, Whitfield ML. Feature specific quantile normalization enables cross-platform classification of molecular subtypes using gene expression data. Bioinformatics. 2018;34(11):1868-1874. d  
PMID line: `29360996` · verdict: SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment. The PMC record carries no body; the abstract establishes FSQN as the method named  
Passage (Abstract, Results): "Multiple analyses show that feature specific quantile normalization (FSQN) successfully removes platform-based bias from RNA-seq data, regardless of feature scaling or machine learning algorithm."

**[44]** Shabalin AA, Tjelmeland H, Fan C, et al. Merging two gene-expression studies via cross-platform normalization. Bioinformatics. 2008;24(9):1154-60. doi:10.1093/bioinformatics/btn083  
PMID line: `18325927` · verdict: SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment.  
Passage (Abstract, Results): "The first is a simple cross-study normalization method, which is based on linked gene/sample clustering of the given datasets."

**[45]** Borisov N, Shabalina I, Tkachev V, et al. Shambhala: a platform-agnostic data harmonizer for gene expression data. BMC Bioinformatics. 2019;20(1):66. doi:10.1186/s12859-019-2641-8  
PMID line: `30727942` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Abstract / Background): "Here we present a new bioinformatic tool termed Shambhala for harmonization of multiple human gene expression datasets obtained using different experimental methods and platforms of microarray hybridization and RNA sequencing."

**[46]** Borisov N, Sorokin M, Zolotovskaya M, et al. Shambhala-2: A Protocol for Uniformly Shaped Harmonization of Gene Expression Profiles of Various Formats. Curr Protoc. 2022;2(5):e444. doi:10.1002/cpz1.44  
PMID line: `35617464` · verdict: SUPPORTS -- verified against the abstract and the PubMed record; the full text is not reachable from this environment. Cited twice, once as the origin of the method and once for the identity of the Sh  
Passage (Abstract): "We propose here a new method termed Shambhala-2 that can transform multi-platform expression data into a universal format that is identical for all harmonizations made using this technique. Shambhala-2 is based on sample-by-sample cubic conversion of the initial expression dataset into a preselected shape of the refere"

**[47]** Risso D, Ngai J, Speed TP, et al. Normalization of RNA-seq data using factor analysis of control genes or samples. Nat Biotechnol. 2014;32(9):896-902. doi:10.1038/nbt.2931  
PMID line: `25150836` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Results, "Removing unwanted variation through normalization"): "We propose three alternative approaches for estimating the factors of unwanted variation: (i) RUVg uses negative control genes, assumed not to be DE with respect to the covariates of interest (e.g., ERCC spike-ins)"

**[48]** Sorokin M, Kholodenko I, Kalinovsky D, et al. RNA Sequencing-Based Identification of Ganglioside GD2-Positive Cancer Phenotype. Biomedicines. 2020;8(6):142. doi:10.3390/biomedicines8060142  
PMID line: `32486168` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract. A two-gene signature that outperforms its individual genes is the panel logic the sentence claims.  
Passage (Results / Abstract): "We identified a 2-gene expression signature combining ganglioside synthase genes ST8SIA1 and B4GALNT1 that serves as a more efficient predictor of GD2-positive phenotype (Matthews Correlation Coefficient (MCC) 0.32, 0.88, and 0.98 in three independent comparisons) compared to the individual ganglioside biosynthesis gen"

**[49]** Jovčevska I, Zottel A, Šamec N, et al. High FREM2 Gene and Protein Expression Are Associated with Favorable Prognosis of IDH-WT Glioblastomas. Cancers (Basel). 2019;11(8):1060. doi:10.3390/cancers1108  
PMID line: `31357584` · verdict: PARTIAL -- verified against the body of the cited article, not the abstract. The paper validates two individual markers, FREM2 and SPRY1, at transcript and protein level across glioma grades. It is a   
Passage (Results / Abstract): "we performed a pilot study where we examined the expression of FREM2 and SPRY1 at the proteomic and transcriptomic levels in different grades of gliomas and nonmalignant brain-tissue samples. FREM2 showed notable differences in expression at both levels, while SPRY1 showed differential changes in expression mostly at t"

**[50]** Zottel A, Šamec N, Kump A, et al. Analysis of miR-9-5p, miR-124-3p, miR-21-5p, miR-138-5p, and miR-1-3p in Glioblastoma Cell Lines and Extracellular Vesicles. Int J Mol Sci. 2020;21(22):8491. doi:10.3  
PMID line: `33187334` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract.  
Passage (Abstract / Results): "We also demonstrated that miR-9-5p and miR-124-3p were overexpressed in the sEVs of GBM stem cell lines (NCH421k or NCH644, respectively) compared to the sEVs of all other GBM cell lines and astrocytes."

**[51]** Shtam T, Naryzhny S, Kopylov A, et al. Functional Properties of Circulating Exosomes Mediated by Surface-Attached Plasma Proteins. J Hematol. 2018;7(4):149-153. doi:10.14740/jh412w  
PMID line: `32300430` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract. Supports the input-material half of the sentence: surface-attached plasma proteins mask the tissue-specific character of t  
Passage (Conclusion): "Taken together, our results demonstrate that a surface of circulating exosomes is decorated by plasma proteins, and these proteins can mask tissue-specific characteristic of the exosomal surface membrane and provide exosomes with new and uniform properties."

**[52]** Nygaard V, Rødland EA, Hovig E. Methods that remove batch effects while retaining group differences may lead to exaggerated confidence in downstream analyses. Biostatistics. 2016;17(1):29-39. doi:10.1  
PMID line: `26272994` · verdict: SUPPORTS -- verified against the body of the cited article, not the abstract. Both halves of the citing sentence are in the same Discussion passage, including the phrase "batch effect free".  
Passage (Discussion): "The use of study group, or other form of outcome, as a covariate when estimating and removing batch effects is problematic if the data are treated as “batch effect free” in subsequent analyses. When the group–batch distribution is unbalanced, i.e. where batches do not have the same composition of groups, this will lead"

## 5. Independent re-resolution of a 20% sample (team lead, 2026-09-19)

`random.seed(20260919)`, sample of 11 of the 47 PubMed-indexed entries: [4], [5], [7], [9], [18], [22], [25], [28], [41], [46], [47]. One `esummary.fcgi` call, `db=pubmed`, `retmode=json`. Title, publication year, volume, pagination and first author match the reference entry in 11 of 11. This sample is drawn independently of the one the team lead used at gate 3 (seed 2609192) and of the reference verifier's own pass.

## 6. Full per-number index (452 distinct numbers, in order of first appearance)

`locus` names the table and column that hold the value; `named filter` is the filter from `01_numbers.json` where one exists. `n loci` is how many table columns carry the value at all - a high count means the value is common, not that it is well sourced.

| number | section | locus | n loci | named table.column | named filter |
|---|---|---|---|---|---|
| 2,234 | Metric classes elect non-overlapping set | A2_T1_analysis_set_census.(row/group counts), A2_T2_generalizability_ranki | 2 | A2_T1.run_id | Supplementary File 3, pct_samples_allNA < 5 |
| 0014 | Metric classes elect non-overlapping set | A2_T5_per_batch_folds.n | 134 | A2_T1.strat | same |
| 02453 | Metric classes elect non-overlapping set | - not a measurement | 0 |  |  |
| 31 | Abstract | A2_T1_analysis_set_census.method, A2_T2_generalizability_ranking.method | 124 | A2_T1.method | same |
| 14 | Abstract | A2_T1_analysis_set_census.method, A2_T2_generalizability_ranking.method | 134 | A2_T1.strat | same |
| 7,174 | Abstract | A2_T1_analysis_set_census.xb_n_samples_used, A2_T1_analysis_set_census.xb_ | 2 |  |  |
| 87 | Abstract | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 108 | A2_T5.f1_macro | n_classes >= 2, three smallest |
| 112 | Abstract | A2_T1_analysis_set_census.(row/group counts), A2_T2_generalizability_ranki | 3 |  |  |
| 0.333 | Abstract | A2_T3_cross_election_matrix.local, A2_T3_cross_election_matrix.composite | 52 |  |  |
| 56 | Abstract | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 128 |  |  |
| 15 | Abstract | A2_T1_analysis_set_census.method, A2_T1_analysis_set_census.n_folds_total | 122 |  |  |
| 84 | Abstract | A2_T5_per_batch_folds.n | 121 | A2_T1.method == 20_shambhala | after the shambhala_P0std_Q0std rename |
| 93 | Abstract | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 95 | A2_T2.pv_lobo3_f1_macro_mean | strat not in (A_confirmed_bad, B_extended_bad) AND n_mc >= 5 |
| 0.0007 | Abstract | A2_T3_cross_election_matrix.M | 152 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.0082 | Abstract | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 167 | not a measurement.mk_rho_mean_markers | Daniil's threshold, necessary not sufficient |
| 32,746 | Abstract | - derived from tables/A2_T8 | 0 | A2_T8.n_folds | sum of the three batch == '__ALL__' rows (15,436 + 9,821 + 7,489) |
| 15,436 | Abstract | A2_T8_fold_composition.n_folds | 1 | A2_T8.n_folds | batch == '__ALL__' AND n_classes == 1 |
| 47.1 | Abstract | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 49 | A2_T8.n_folds | batch == '__ALL__'; 15,436 / 32,746 = 47.14% |
| 0.903 | Abstract | A2_T1_analysis_set_census.mk_rho_mean_PGK1_only_narrow_set, A2_T1_analysis | 47 | A2_T8.median_f1 | batch == '__ALL__'; fold-level median over all 3-class folds of the analysis set |
| 0.7334 | Abstract | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 60 | prediction_folds_long.csv.f1_macro | target == '3class' AND n_classes >= 2, run_id restricted to the 2,234 analysis set after the Shambhala rename; |
| 11 | Introduction | A2_T1_analysis_set_census.method, A2_T1_analysis_set_census.n_mc | 134 | A2_T2.pv_lobo3_f1_macro_mean | strat not in (A_confirmed_bad, B_extended_bad) AND n_mc >= 5 |
| 12 | Introduction | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 133 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 23 | Introduction | A2_T1_analysis_set_census.method, A2_T1_analysis_set_census.n_folds_total | 109 |  |  |
| 13 | Introduction | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 131 | A2_T5.n_classes | n_classes == 1 |
| 16 | Introduction | A2_T1_analysis_set_census.method, A2_T1_analysis_set_census.n_folds_total | 120 |  |  |
| 17 | Introduction | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 118 | prediction_folds_long.csv.target, run_id, n_classes | prediction_folds_long.csv, target == '3class'. Unrestricted: 53,737 folds over 3,738 run_ids and 50 method nam |
| 18 | Introduction | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 128 |  |  |
| 19 | Introduction | A2_T1_analysis_set_census.method, A2_T1_analysis_set_census.n_folds_total | 120 |  |  |
| 20 | Introduction | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 171 |  |  |
| 21 | Introduction | A2_T1_analysis_set_census.method, A2_T1_analysis_set_census.n_folds_total | 126 |  |  |
| 22 | Introduction | A2_T1_analysis_set_census.method, A2_T1_analysis_set_census.generalizabili | 122 |  |  |
| 24 | Introduction | A2_T5_per_batch_folds.n | 125 | A2_T8.batch | batch != '__ALL__' |
| 25 | Introduction | A2_T1_analysis_set_census.method, A2_T1_analysis_set_census.generalizabili | 122 |  |  |
| 26 | Introduction | A2_T1_analysis_set_census.method, A2_T1_analysis_set_census.generalizabili | 114 |  |  |
| 27 | Introduction | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 124 |  |  |
| 28 | Introduction | A2_T5_per_batch_folds.n | 127 |  |  |
| 29 | Introduction | A2_T1_analysis_set_census.method, A2_T1_analysis_set_census.generalizabili | 123 | A2_T2.pv_lobo3_f1_macro_mean | strat not in (A_confirmed_bad, B_extended_bad) AND n_mc >= 5 |
| 30 | Introduction | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 167 |  |  |
| 32 | Introduction | A2_T5_per_batch_folds.n | 129 |  |  |
| 33 | Introduction | A2_T5_per_batch_folds.n | 127 |  |  |
| 34 | Introduction | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 127 |  |  |
| 35 | Introduction | A2_T5_per_batch_folds.n | 122 | A2_T5.f1_macro | n_classes >= 2, three smallest |
| 36 | Introduction | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 129 |  |  |
| 37 | Introduction | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 123 |  |  |
| 38 | Introduction | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 130 |  |  |
| 88 | Dataset, harmonization approaches and th | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 103 | A2_T2.pv_lobo3_f1_macro_mean | strat not in (A_confirmed_bad, B_extended_bad) AND n_mc >= 5 |
| 39 | Dataset, harmonization approaches and th | A2_T1_analysis_set_census.frac_singleclass, A2_T1_analysis_set_census.gene | 124 |  |  |
| 40 | Dataset, harmonization approaches and th | A2_T3_cross_election_matrix.L, A2_T3_cross_election_matrix.N | 187 | A2_T1.f1_mc_mean, f1_mc_min, n_mc | method == 20_shambhala; multiclass-only cut (folds with >= 2 classes). 82 of the 84 rows carry f1_mc_mean and  |
| 41 | Dataset, harmonization approaches and th | A2_T1_analysis_set_census.frac_singleclass, A2_T1_analysis_set_census.gene | 122 |  |  |
| 42 | Dataset, harmonization approaches and th | A2_T1_analysis_set_census.frac_singleclass, A2_T1_analysis_set_census.gene | 127 |  |  |
| 43 | Dataset, harmonization approaches and th | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 135 | A2_T1.f1_mc_mean, f1_mc_min, n_mc | method == 20_shambhala; multiclass-only cut (folds with >= 2 classes). 82 of the 84 rows carry f1_mc_mean and  |
| 44 | Dataset, harmonization approaches and th | A2_T1_analysis_set_census.frac_singleclass, A2_T1_analysis_set_census.gene | 132 |  |  |
| 45 | Dataset, harmonization approaches and th | A2_T3_cross_election_matrix.L, A2_T3_cross_election_matrix.N | 137 |  |  |
| 46 | Dataset, harmonization approaches and th | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 148 | A2_T6.xb_margin_delta | maximum |
| 74.23 | Dataset, harmonization approaches and th | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 14 |  |  |
| 78 | Dataset, harmonization approaches and th | A2_T0_shambhala_identity.(row/group counts), A2_T1_analysis_set_census.gen | 122 | A2_T0.identical | 84 matched (strat, imp, post_rm) keys |
| 79 | Dataset, harmonization approaches and th | A2_T5_per_batch_folds.n | 135 | A2_T0.identical | 84 matched (strat, imp, post_rm) keys |
| 2,150 | Dataset, harmonization approaches and th | A2_T1_analysis_set_census.(row/group counts), A2_T2_generalizability_ranki | 2 |  |  |
| 1.0 | Metric classes and the election procedur | A2_T3_cross_election_matrix.L, A2_T3_cross_election_matrix.M | 254 | not a measurement.mk_rho_mean_markers | Daniil's threshold, necessary not sufficient |
| 633 | The biology-facing metric classes L, M a | - cited fact, source benchmark [38] | 0 |  |  |
| 47 | The biology-facing metric classes L, M a | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 129 | A2_T8.n_folds | batch == '__ALL__'; 15,436 / 32,746 = 47.14% |
| 48 | The biology-facing metric classes L, M a | A2_T5_per_batch_folds.n | 132 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 49 | The biology-facing metric classes L, M a | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 125 |  |  |
| 0.75 | The biology-facing metric classes L, M a | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 123 | not a measurement.mk_rho_mean_markers | Daniil's threshold, necessary not sufficient |
| 01 | The biology-facing metric classes L, M a | A2_T3_cross_election_matrix.M, A2_T3_cross_election_matrix.N | 127 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 3.11 | Statistics and software | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 22 |  |  |
| 2.3 | Statistics and software | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 81 |  |  |
| 1.26 | Statistics and software | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 24 |  |  |
| 1.12 | Statistics and software | A2_T1_analysis_set_census.mk_rho_marker_minus_hk, A2_T1_analysis_set_censu | 28 |  |  |
| 1.3 | Statistics and software | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 69 |  |  |
| 0.14 | Statistics and software | A2_T5_per_batch_folds.n | 134 | A2_T1.strat | same |
| 3.10 | Statistics and software | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 76 |  |  |
| 0.13 | Statistics and software | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 131 | A2_T5.n_classes | n_classes == 1 |
| 0.159 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 52 |  |  |
| 3.7 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 61 |  |  |
| 0.871 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_mean_PGK1_only_narrow_set, A2_T1_analysis | 50 |  |  |
| 0.122 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 67 |  |  |
| 0.626 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 55 |  |  |
| 0.820 | Metric classes capture non-overlapping c | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 123 |  |  |
| 0.063 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 71 |  |  |
| 0.802 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 61 |  |  |
| 1.0000 | Metric classes capture non-overlapping c | A2_T3_cross_election_matrix.global, A2_T3_cross_election_matrix.L | 254 | not a measurement.mk_rho_mean_markers | Daniil's threshold, necessary not sufficient |
| 0.9967 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_mean_PGK1_only_narrow_set, A2_T1_analysis | 26 |  |  |
| 05 | Metric classes capture non-overlapping c | A2_T3_cross_election_matrix.N | 121 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.568 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 42 |  |  |
| 0.778 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 62 |  |  |
| 0.357 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.frac_singleclass, A2_T1_analysis_set_census.gene | 53 |  |  |
| 0.823 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 63 |  |  |
| 0.208 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 49 |  |  |
| 0.098 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 56 |  |  |
| 0.939 | Metric classes capture non-overlapping c | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 42 |  |  |
| 0.925 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 40 |  |  |
| 0.883 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 51 |  |  |
| 0.872 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_mean_all_genes, A2_T1_analysis_set_census | 52 |  |  |
| 164 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_n_genes_null_delta, A2_T1_analysis_set_census | 3 |  |  |
| 17.3 | Metric classes capture non-overlapping c | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 48 |  |  |
| 25.3 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 45 |  |  |
| 11.3 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_marker_minus_hk, A2_T1_analysis_set_censu | 58 |  |  |
| 15.3 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 47 |  |  |
| 26.2 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 44 |  |  |
| 43.3 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 40 |  |  |
| 79.9 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_mean_PGK1_only_narrow_set, A2_T1_analysis | 54 |  |  |
| 79.5 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 58 |  |  |
| 03 | Metric classes capture non-overlapping c | A2_T3_cross_election_matrix.L | 121 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 07 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 117 |  |  |
| 0.0024 | Metric classes capture non-overlapping c | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 155 |  |  |
| 0.226 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 50 |  |  |
| 77.4 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 59 |  |  |
| 1.72 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 26 |  |  |
| 0.209 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 42 |  |  |
| 1.16 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 30 |  |  |
| 0.103 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 69 |  |  |
| 1.07 | Metric classes capture non-overlapping c | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 35 |  |  |
| 0.032 | Metric classes capture non-overlapping c | A2_T3_cross_election_matrix.L | 79 |  |  |
| 0.527 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 56 |  |  |
| 160 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.pv_n_genes_dropped_na, A2_T1_analysis_set_census | 3 |  |  |
| 0.374 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 41 |  |  |
| 0.815 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9_narrow_set, A2_T1_an | 56 | A2_T2.pv_lobo3_f1_macro_mean, f1_mc_mean | n_mc >= 3, n = 2058 |
| 0.617 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 56 |  |  |
| 0.179 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 57 |  |  |
| 0.025 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 85 |  |  |
| 0.0178 | Metric classes capture non-overlapping c | A2_T3_cross_election_matrix.global, A2_T3_cross_election_matrix.L | 83 |  |  |
| 0.0086 | Metric classes capture non-overlapping c | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 157 | A2_T2.pv_lobo3_f1_macro_mean | strat not in (A_confirmed_bad, B_extended_bad) AND n_mc >= 5 |
| 0.24 | Metric classes capture non-overlapping c | A2_T5_per_batch_folds.n | 125 | A2_T8.batch | batch != '__ALL__' |
| 1.00 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.method, A2_T2_generalizability_ranking.method | 254 | not a measurement.mk_rho_mean_markers | Daniil's threshold, necessary not sufficient |
| 1,000 | Metric classes capture non-overlapping c | - design constant of the source metric | 0 |  |  |
| 0.445 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 55 |  |  |
| 0.041 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 68 |  |  |
| 0.439 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 52 |  |  |
| 0.015 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 79 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.332 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 55 |  |  |
| 0.052 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 73 |  |  |
| 0.003 | Metric classes capture non-overlapping c | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 163 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 1.4 | Metric classes capture non-overlapping c | A2_T3_cross_election_matrix.M, A2_T3_cross_election_matrix.N | 78 |  |  |
| 30.2 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 41 |  |  |
| 38.1 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 40 |  |  |
| 0.004 | Metric classes capture non-overlapping c | A2_T3_cross_election_matrix.L, A2_T3_cross_election_matrix.N | 179 | A2_T1.f1_mc_mean, f1_mc_min, n_mc | method == 20_shambhala; multiclass-only cut (folds with >= 2 classes). 82 of the 84 rows carry f1_mc_mean and  |
| 2.41 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 20 |  |  |
| 13.0 | Metric classes capture non-overlapping c | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 125 | A2_T5.n_classes | n_classes == 1 |
| 16.2 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 52 |  |  |
| 06 | Metric classes capture non-overlapping c | A2_T3_cross_election_matrix.M | 110 | A2_T6.strat, imp, method, post_rm (A2_T6 has no run_id colum | xb_margin_delta == max |
| 08 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 116 | A2_T6.strat, imp, method, post_rm (A2_T6 has no run_id colum | xb_margin_delta == max |
| 2.76 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 24 |  |  |
| 1.46 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 30 |  |  |
| 99 | Metric classes capture non-overlapping c | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 84 |  |  |
| 18.5 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 45 |  |  |
| 17.9 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 50 |  |  |
| 1,359 | Metric classes capture non-overlapping c | A2_T8_fold_composition.n_folds | 1 |  |  |
| 555,004 | Metric classes capture non-overlapping c | - NO LOCUS under tables/ | 0 |  |  |
| 40.6 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 59 |  |  |
| 2.63 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 24 |  |  |
| 6.70 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 72 |  |  |
| 12.6 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 59 |  |  |
| 28.6 | Metric classes capture non-overlapping c | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 46 |  |  |
| 50 | Metric classes capture non-overlapping c | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 191 | A2_T6.xb_margin_delta | maximum |
| 95 | Metric classes capture non-overlapping c | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 92 | A2_T2.pv_lobo3_f1_macro_mean | strat not in (A_confirmed_bad, B_extended_bad) AND n_mc >= 5 |
| 0.999 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.mk_rho_mean_PGK1_only_narrow_set, A2_T1_analysis | 45 |  |  |
| 198 | Global variance-based metrics saturate b | A2_T5_per_batch_folds.(row/group counts) | 1 |  |  |
| 0.9999 | Global variance-based metrics saturate b | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 70 |  |  |
| 98.5 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 27 |  |  |
| 0.1 | Global variance-based metrics saturate b | A2_T3_cross_election_matrix.global, A2_T3_cross_election_matrix.M | 170 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.962 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.mk_rho_mean_PGK1_only_narrow_set, A2_T1_analysis | 41 |  |  |
| 0.781 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 63 |  |  |
| 0.957 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 50 |  |  |
| 0.0013 | Global variance-based metrics saturate b | A2_T3_cross_election_matrix.M | 152 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.0098 | Global variance-based metrics saturate b | A2_T3_cross_election_matrix.L, A2_T3_cross_election_matrix.M | 254 | not a measurement.mk_rho_mean_markers | Daniil's threshold, necessary not sufficient |
| 0.165 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 45 |  |  |
| 0.078 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 70 |  |  |
| 0.066 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 76 |  |  |
| 0.019 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 76 |  |  |
| 02 | Global variance-based metrics saturate b | A2_T3_cross_election_matrix.L, A2_T3_cross_election_matrix.M | 121 |  |  |
| 0.286 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 51 |  |  |
| 0.276 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 55 |  |  |
| 1.7 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 78 |  |  |
| 9.7 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 59 |  |  |
| 4.8 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 68 |  |  |
| 0.020 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.method, A2_T2_generalizability_ranking.method | 151 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.370 | Global variance-based metrics saturate b | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 123 |  |  |
| 0.390 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.frac_singleclass, A2_T1_analysis_set_census.gene | 124 |  |  |
| 0.030 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.method, A2_T2_generalizability_ranking.method | 148 | A2_T1.imp | same |
| 0.70 | Global variance-based metrics saturate b | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 177 | A2_T1.pv_lobo3_f1_macro_mean | method == 20_shambhala; full cut (all LOBO folds). 83 of the 84 rows carry pv_lobo3_f1_macro_mean. Rule 7b: re |
| 0.88 | Global variance-based metrics saturate b | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 103 | A2_T2.pv_lobo3_f1_macro_mean | strat not in (A_confirmed_bad, B_extended_bad) AND n_mc >= 5 |
| 0.83 | Global variance-based metrics saturate b | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 119 |  |  |
| 0.49 | Global variance-based metrics saturate b | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 125 |  |  |
| 0.48 | Global variance-based metrics saturate b | A2_T5_per_batch_folds.n | 132 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.76 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 113 |  |  |
| 0.72 | Global variance-based metrics saturate b | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 111 | A2_T5.f1_macro | n_classes >= 2, three smallest |
| 0.46 | Global variance-based metrics saturate b | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 148 | A2_T6.xb_margin_delta | maximum |
| 0.30 | Global variance-based metrics saturate b | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 167 |  |  |
| 0.08 | Global variance-based metrics saturate b | A2_T1_analysis_set_census.method, A2_T1_analysis_set_census.n_mc | 134 |  |  |
| 0.01 | Local neighbourhood metrics discriminate | A2_T3_cross_election_matrix.L, A2_T3_cross_election_matrix.M | 254 | not a measurement.mk_rho_mean_markers | Daniil's threshold, necessary not sufficient |
| 82.0 | Local neighbourhood metrics discriminate | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 92 |  |  |
| 0.10 | Local neighbourhood metrics discriminate | A2_T3_cross_election_matrix.M | 170 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 97.0 | Local neighbourhood metrics discriminate | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 61 |  |  |
| 0.027 | Local neighbourhood metrics discriminate | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 76 |  |  |
| 0.331 | Local neighbourhood metrics discriminate | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 43 |  |  |
| 0.230 | Local neighbourhood metrics discriminate | A2_T1_analysis_set_census.method, A2_T2_generalizability_ranking.method | 109 |  |  |
| 0.044 | Local neighbourhood metrics discriminate | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 68 |  |  |
| 04 | Local neighbourhood metrics discriminate | A2_T3_cross_election_matrix.L, A2_T3_cross_election_matrix.M | 116 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.036 | Local neighbourhood metrics discriminate | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 83 |  |  |
| 0.035 | Local neighbourhood metrics discriminate | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 73 |  |  |
| 0.029 | Local neighbourhood metrics discriminate | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 78 |  |  |
| 0.028 | Local neighbourhood metrics discriminate | A2_T3_cross_election_matrix.L | 78 | A2_T6.derived: len(A2_T6) / (len(A2_T1) - rows where method  | denominator = 2150 non-raw approaches |
| 1.10 | Local neighbourhood metrics discriminate | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 70 |  |  |
| 1.62 | Local neighbourhood metrics discriminate | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 31 |  |  |
| 0.646 | Local neighbourhood metrics discriminate | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 54 |  |  |
| 0.727 | Local neighbourhood metrics discriminate | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 62 |  |  |
| 0.799 | Local neighbourhood metrics discriminate | A2_T1_analysis_set_census.mk_rho_mean_PGK1_only_narrow_set, A2_T1_analysis | 56 |  |  |
| 0.854 | Local neighbourhood metrics discriminate | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 54 |  |  |
| 0.654 | Local neighbourhood metrics discriminate | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 62 |  |  |
| 0.867 | Local neighbourhood metrics discriminate | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 62 |  |  |
| 1.24 | Local neighbourhood metrics discriminate | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 32 |  |  |
| 1.38 | Local neighbourhood metrics discriminate | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 39 |  |  |
| 37.9 | Batch-associated variance is redistribut | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 41 |  |  |
| 11.6 | Batch-associated variance is redistribut | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 47 |  |  |
| 22.9 | Batch-associated variance is redistribut | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 44 |  |  |
| 15.2 | Batch-associated variance is redistribut | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 52 |  |  |
| 53.7 | Batch-associated variance is redistribut | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 46 |  |  |
| 13.5 | Batch-associated variance is redistribut | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 49 |  |  |
| 90.8 | Batch-associated variance is redistribut | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 48 |  |  |
| 67.1 | Batch-associated variance is redistribut | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 48 |  |  |
| 73.5 | Batch-associated variance is redistribut | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 48 |  |  |
| 64.8 | Batch-associated variance is redistribut | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 58 |  |  |
| 65.9 | Batch-associated variance is redistribut | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 50 |  |  |
| 30.4 | Batch-associated variance is redistribut | A2_T1_analysis_set_census.mk_panel_coverage_frac_narrow_set, A2_T1_analysi | 43 |  |  |
| 66.0 | Batch-associated variance is redistribut | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 95 |  |  |
| 0.948 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 46 |  |  |
| 0.965 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 33 |  |  |
| 0.7 | Distributional convergence is the only a | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 177 | A2_T1.pv_lobo3_f1_macro_mean | method == 20_shambhala; full cut (all LOBO folds). 83 of the 84 rows carry pv_lobo3_f1_macro_mean. Rule 7b: re |
| 0.173 | Distributional convergence is the only a | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 59 |  |  |
| 0.217 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 64 |  |  |
| 0.691 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 60 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.560 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 128 |  |  |
| 56.0 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 100 |  |  |
| 0.845 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_mean_PGK1_only_narrow_set, A2_T1_analysis | 58 |  |  |
| 1.032 | Distributional convergence is the only a | A2_T1_analysis_set_census.pv_lobo2_auc_macro_mean_delta, A2_T1_analysis_se | 9 |  |  |
| 0.914 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 48 |  |  |
| 0.757 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 63 |  |  |
| 0.508 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 56 |  |  |
| 0.531 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 41 |  |  |
| 0.566 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 51 |  |  |
| 0.602 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 50 |  |  |
| 0.578 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 53 |  |  |
| 0.360 | Distributional convergence is the only a | A2_T1_analysis_set_census.method, A2_T2_generalizability_ranking.method | 129 |  |  |
| 0.017 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 82 |  |  |
| 0.109 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 70 |  |  |
| 0.043 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 75 |  |  |
| 0.049 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 76 |  |  |
| 57 | Distributional convergence is the only a | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 130 |  |  |
| 60.7 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 55 |  |  |
| 67.4 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 53 |  |  |
| 0.053 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 68 |  |  |
| 0.6 | Distributional convergence is the only a | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 178 | A2_T8.median_f1 | batch == '__ALL__'; fold-level median over all 3-class folds of the analysis set |
| 150 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_n_genes_null_delta | 1 |  |  |
| 6.7 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 72 |  |  |
| 344 | Distributional convergence is the only a | A2_T1_analysis_set_census.(row/group counts), A2_T2_generalizability_ranki | 3 | A2_T1.harshness_level | HARSHNESS_LEVEL_MAP, method level. 344 / 1,042 / 848 is the tier membership; it is NOT the denominator of ever |
| 1,042 | Distributional convergence is the only a | A2_T1_analysis_set_census.(row/group counts), A2_T2_generalizability_ranki | 3 | A2_T1.harshness_level | HARSHNESS_LEVEL_MAP, method level. 344 / 1,042 / 848 is the tier membership; it is NOT the denominator of ever |
| 848 | Distributional convergence is the only a | A2_T1_analysis_set_census.(row/group counts), A2_T2_generalizability_ranki | 3 | A2_T1.harshness_level | HARSHNESS_LEVEL_MAP, method level. 344 / 1,042 / 848 is the tier membership; it is NOT the denominator of ever |
| 0.998 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 35 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.880 | Distributional convergence is the only a | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 103 | A2_T2.pv_lobo3_f1_macro_mean | strat not in (A_confirmed_bad, B_extended_bad) AND n_mc >= 5 |
| 0.922 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 44 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 340.1 | Distributional convergence is the only a | A2_T7_harshness_by_lmn.kruskal_H | 1 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 74 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 114 |  |  |
| 0.000 | Distributional convergence is the only a | A2_T3_cross_election_matrix.L, A2_T3_cross_election_matrix.M | 269 | A2_T1.xb_margin | method == 20_shambhala |
| 0.009 | Distributional convergence is the only a | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 157 | A2_T2.pv_lobo3_f1_macro_mean | strat not in (A_confirmed_bad, B_extended_bad) AND n_mc >= 5 |
| 0.031 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 80 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 139.3 | Distributional convergence is the only a | A2_T7_harshness_by_lmn.kruskal_H | 1 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 5.5 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_marker_minus_hk, A2_T1_analysis_set_censu | 60 |  |  |
| 800 | Distributional convergence is the only a | A2_T5_per_batch_folds.n | 3 | A2_T7.n_low, n_medium, n_high | one row per metric; the n behind each tier median and each kruskal_H. Only mk_rho_mean_markers uses the full t |
| 0.507 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 56 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.701 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 57 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 287.1 | Distributional convergence is the only a | A2_T7_harshness_by_lmn.kruskal_H | 1 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 4.5 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 71 |  |  |
| 63 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 120 | A2_T8.median_f1 | batch == '__ALL__'; fold-level median over all 3-class folds of the analysis set |
| 847 | Distributional convergence is the only a | A2_T7_harshness_by_lmn.n_high | 1 | A2_T7.n_low, n_medium, n_high | one row per metric; the n behind each tier median and each kruskal_H. Only mk_rho_mean_markers uses the full t |
| 0.054 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_panel_coverage_frac_narrow_set, A2_T1_analysi | 76 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.045 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 75 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 132.9 | Distributional convergence is the only a | A2_T7_harshness_by_lmn.kruskal_H | 1 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.631 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 62 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.712 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 59 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.715 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 59 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 51.6 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 59 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 6.1 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_marker_minus_hk, A2_T1_analysis_set_censu | 63 |  |  |
| 0.021 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 76 |  |  |
| 0.657 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 58 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.678 | Distributional convergence is the only a | A2_T5_per_batch_folds.auc | 56 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 11.8 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 57 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 2.8 | Distributional convergence is the only a | A2_T3_cross_election_matrix.L | 74 | A2_T6.derived: len(A2_T6) / (len(A2_T1) - rows where method  | denominator = 2150 non-raw approaches |
| 333 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_n_panel_genes_used, A2_T5_per_batch_folds.(ro | 3 | A2_T7.n_low, n_medium, n_high | one row per metric; the n behind each tier median and each kruskal_H. Only mk_rho_mean_markers uses the full t |
| 1,016 | Distributional convergence is the only a | A2_T7_harshness_by_lmn.n_medium | 1 | A2_T7.n_low, n_medium, n_high | one row per metric; the n behind each tier median and each kruskal_H. Only mk_rho_mean_markers uses the full t |
| 825 | Distributional convergence is the only a | A2_T7_harshness_by_lmn.n_high | 1 | A2_T7.n_low, n_medium, n_high | one row per metric; the n behind each tier median and each kruskal_H. Only mk_rho_mean_markers uses the full t |
| 0.901 | Distributional convergence is the only a | A2_T5_per_batch_folds.auc | 54 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.904 | Distributional convergence is the only a | A2_T5_per_batch_folds.auc | 54 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 1.5 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 77 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 11.2 | Distributional convergence is the only a | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 59 |  |  |
| 0.0037 | Distributional convergence is the only a | A2_T3_cross_election_matrix.L, A2_T3_cross_election_matrix.N | 179 | A2_T1.f1_mc_mean, f1_mc_min, n_mc | method == 20_shambhala; multiclass-only cut (folds with >= 2 classes). 82 of the 84 rows carry f1_mc_mean and  |
| 0.713 | Distributional convergence is the only a | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 60 |  |  |
| 55 | Preservation of biomarker expression and | A2_T1_analysis_set_census.frac_singleclass, A2_T1_analysis_set_census.gene | 118 |  |  |
| 61 | Preservation of biomarker expression and | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 118 | A2_T6.row count; keyed by (strat, imp, method, post_rm) | xb_rank_agree_delta > 0 AND xb_rank_disagree_diffbio_delta < 0 |
| 51 | Preservation of biomarker expression and | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 130 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.0000 | Preservation of biomarker expression and | A2_T3_cross_election_matrix.L, A2_T3_cross_election_matrix.M | 269 | A2_T1.xb_margin | method == 20_shambhala |
| 0.0489 | Preservation of biomarker expression and | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 72 |  |  |
| 1,686 | Preservation of biomarker expression and | - derived from tables/A2_T1 | 0 | A2_T1.mk_rho_mean_markers, xb_margin | rho > 0.75 AND margin > 0 |
| 75.5 | Preservation of biomarker expression and | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 60 |  |  |
| 83 | Preservation of biomarker expression and | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 119 |  |  |
| 82 | Preservation of biomarker expression and | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 123 |  |  |
| 80 | Preservation of biomarker expression and | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 170 | not a measurement.mk_rho_mean_markers | Daniil's threshold, necessary not sufficient |
| 141 | Preservation of biomarker expression and | - derived from tables/A2_T1 | 0 |  |  |
| 130 | Preservation of biomarker expression and | A2_T5_per_batch_folds.n | 3 |  |  |
| 76 | Preservation of biomarker expression and | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 113 |  |  |
| 0.0647 | Preservation of biomarker expression and | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 70 |  |  |
| 0.9791 | Preservation of biomarker expression and | A2_T1_analysis_set_census.mk_rho_mean_all_genes, A2_T1_analysis_set_census | 32 |  |  |
| 0.9753 | Preservation of biomarker expression and | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 34 |  |  |
| 0.9145 | Preservation of biomarker expression and | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 49 |  |  |
| 0.9144 | Preservation of biomarker expression and | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 44 |  |  |
| 0.0667 | Preservation of biomarker expression and | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 73 |  |  |
| 0.0757 | Preservation of biomarker expression and | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 66 |  |  |
| 0.0090 | Preservation of biomarker expression and | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 157 | A2_T2.pv_lobo3_f1_macro_mean | strat not in (A_confirmed_bad, B_extended_bad) AND n_mc >= 5 |
| 0.0180 | Preservation of biomarker expression and | A2_T3_cross_election_matrix.L, A2_T3_cross_election_matrix.M | 86 |  |  |
| 0.0077 | Preservation of biomarker expression and | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 167 | not a measurement.mk_rho_mean_markers | Daniil's threshold, necessary not sufficient |
| 0.9586 | Preservation of biomarker expression and | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 44 |  |  |
| 0.9471 | Preservation of biomarker expression and | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 39 |  |  |
| 0.9343 | Preservation of biomarker expression and | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 46 |  |  |
| 0.0243 | Preservation of biomarker expression and | A2_T3_cross_election_matrix.M | 76 |  |  |
| 0.0513 | Preservation of biomarker expression and | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 68 |  |  |
| 0.0432 | Preservation of biomarker expression and | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 72 |  |  |
| 0.0364 | Preservation of biomarker expression and | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 78 |  |  |
| 0.1263 | Preservation of biomarker expression and | A2_T1_analysis_set_census.mk_panel_coverage_frac, A2_T1_analysis_set_censu | 61 |  |  |
| 0.439161 | Preservation of biomarker expression and | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 46 |  |  |
| 0.457154 | Preservation of biomarker expression and | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 52 |  |  |
| 0.257 | Preservation of biomarker expression and | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 47 |  |  |
| 0.200 | Preservation of biomarker expression and | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 171 |  |  |
| 0.840 | Preservation of biomarker expression and | A2_T5_per_batch_folds.n | 121 | A2_T1.method == 20_shambhala | after the shambhala_P0std_Q0std rename |
| 0.0048 | Preservation of biomarker expression and | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 186 | A2_T1.xb_margin | method == 20_shambhala |
| 17,310 | Cross-batch prediction elects a third se | - derived from tables/A2_T8 | 0 | A2_T8.n_folds | batch == '__ALL__' AND n_classes >= 2 (9,821 + 7,489) |
| 0.629 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 51 | A2_T8.median_f1 | batch == '__ALL__'; fold-level median over all 3-class folds of the analysis set |
| 0.804 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 65 | A2_T8.median_f1 | batch == '__ALL__'; fold-level median over all 3-class folds of the analysis set |
| 53,737 | Cross-batch prediction elects a third se | - locus outside tables/ | 0 | prediction_folds_long.csv.target | target == '3class', no run_id restriction |
| 3,738 | Cross-batch prediction elects a third se | - locus outside tables/ | 0 | prediction_folds_long.csv.run_id | whole table (94,582 rows, 50 method names) |
| 20,991 | Cross-batch prediction elects a third se | - locus outside tables/ | 0 | prediction_folds_long.csv.target, run_id, n_classes | prediction_folds_long.csv, target == '3class'. Unrestricted: 53,737 folds over 3,738 run_ids and 50 method nam |
| 20,343 | Cross-batch prediction elects a third se | - locus outside tables/ | 0 | prediction_folds_long.csv.target, run_id, n_classes | prediction_folds_long.csv, target == '3class'. Unrestricted: 53,737 folds over 3,738 run_ids and 50 method nam |
| 648 | Cross-batch prediction elects a third se | - locus outside tables/ | 0 | prediction_folds_long.csv.target, run_id, n_classes | prediction_folds_long.csv, target == '3class'. Unrestricted: 53,737 folds over 3,738 run_ids and 50 method nam |
| 1,200 | Cross-batch prediction elects a third se | - locus outside tables/ | 0 | prediction_folds_long.csv.target, run_id, n_classes | prediction_folds_long.csv, target == '3class'. Unrestricted: 53,737 folds over 3,738 run_ids and 50 method nam |
| 25,426 | Cross-batch prediction elects a third se | - locus outside tables/ | 0 | prediction_folds_long.csv.n_classes | target == '3class' AND n_classes == 1, no run_id restriction (47.3%) |
| 47.3 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 49 |  |  |
| 0.952 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 41 |  |  |
| 0.648 | Cross-batch prediction elects a third se | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 62 |  |  |
| 0.830 | Cross-batch prediction elects a third se | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 119 |  |  |
| 0.810 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 115 | A2_T2.pv_lobo3_f1_macro_mean, f1_mc_mean | both present, n = 2174 |
| 2,174 | Cross-batch prediction elects a third se | - derived from tables/A2_T2 | 0 |  |  |
| 2,058 | Cross-batch prediction elects a third se | - derived from tables/A2_T2 | 0 |  |  |
| 0.812 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 61 |  |  |
| 1.000 | Cross-batch prediction elects a third se | A2_T3_cross_election_matrix.L, A2_T3_cross_election_matrix.M | 254 | not a measurement.mk_rho_mean_markers | Daniil's threshold, necessary not sufficient |
| 0.958 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.mk_rho_mean_PGK1_only_narrow_set, A2_T1_analysis | 47 |  |  |
| 0.924 | Cross-batch prediction elects a third se | A2_T5_per_batch_folds.auc | 49 |  |  |
| 0.643 | Cross-batch prediction elects a third se | A2_T5_per_batch_folds.auc | 50 |  |  |
| 52 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.frac_singleclass, A2_T1_analysis_set_census.gene | 124 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 1,527 | Cross-batch prediction elects a third se | - derived from tables/A2_T2 | 0 | A2_T1.strat, n_mc | same filter |
| 0.946 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9_narrow_set, A2_T1_an | 44 | A2_T2.pv_lobo3_f1_macro_mean | strat not in (A_confirmed_bad, B_extended_bad) AND n_mc >= 5 |
| 0.887 | Cross-batch prediction elects a third se | A2_T5_per_batch_folds.auc | 55 |  |  |
| 0.462 | Cross-batch prediction elects a third se | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 67 | A2_T2.pv_lobo3_f1_macro_mean | strat not in (A_confirmed_bad, B_extended_bad) AND n_mc >= 5 |
| 0.932 | Cross-batch prediction elects a third se | A2_T5_per_batch_folds.auc | 45 | A2_T2.pv_lobo3_f1_macro_mean | strat not in (A_confirmed_bad, B_extended_bad) AND n_mc >= 5 |
| 0.986 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 34 |  |  |
| 0.543 | Cross-batch prediction elects a third se | A2_T5_per_batch_folds.auc | 57 | A2_T5.f1_macro | n_classes >= 2, three smallest |
| 0.698 | Cross-batch prediction elects a third se | A2_T5_per_batch_folds.auc | 52 | A2_T5.f1_macro | n_classes >= 2, three smallest |
| 0.874 | Cross-batch prediction elects a third se | A2_T5_per_batch_folds.auc | 57 | A2_T5.f1_macro | n_classes >= 2, three smallest |
| 1,039 | Cross-batch prediction elects a third se | A2_T5_per_batch_folds.n | 2 | A2_T5.f1_macro | n_classes >= 2, three smallest |
| 0.718 | Cross-batch prediction elects a third se | A2_T5_per_batch_folds.auc | 52 | A2_T5.f1_macro | n_classes >= 2, three smallest |
| 0.972 | Cross-batch prediction elects a third se | A2_T5_per_batch_folds.auc | 34 | A2_T5.f1_macro | n_classes >= 2, three smallest |
| 0.945 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.mk_rho_mean_PGK1_only_narrow_set, A2_T1_analysis | 44 |  |  |
| 0.838 | Cross-batch prediction elects a third se | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 64 |  |  |
| 0.592 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 60 |  |  |
| 0.927 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.mk_rho_mean_PGK1_only_narrow_set, A2_T1_analysis | 44 |  |  |
| 0.829 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9_narrow_set, A2_T1_an | 63 |  |  |
| 0.935 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 50 |  |  |
| 0.863 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.mk_rho_mean_PGK1_only_narrow_set, A2_T1_analysis | 51 |  |  |
| 0.639 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 52 |  |  |
| 0.912 | Cross-batch prediction elects a third se | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 48 |  |  |
| 0.944 | Cross-batch prediction elects a third se | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 51 |  |  |
| 0.928 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 53 |  |  |
| 0.890 | Cross-batch prediction elects a third se | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 109 |  |  |
| 0.541 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 49 |  |  |
| 0.931 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 47 |  |  |
| 0.898 | Cross-batch prediction elects a third se | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 58 |  |  |
| 0.827 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 62 |  |  |
| 0.877 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 57 |  |  |
| 0.771 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 52 |  |  |
| 0.876 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 58 |  |  |
| 0.772 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 57 |  |  |
| 0.464 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 44 |  |  |
| 0.858 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 59 |  |  |
| 0.755 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 64 |  |  |
| 0.409 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 41 |  |  |
| 0.453 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 52 |  |  |
| 0.571 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.frac_singleclass, A2_T1_analysis_set_census.gene | 58 |  |  |
| 0.233 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 47 |  |  |
| 0.480 | Cross-batch prediction elects a third se | A2_T5_per_batch_folds.n | 132 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.614 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 59 |  |  |
| 0.154 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.mk_rho_marker_minus_PGK1_only_narrow_set, A2_T1_ | 57 |  |  |
| 0.520 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.frac_singleclass, A2_T1_analysis_set_census.gene | 124 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.624 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 55 |  |  |
| 0.168 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 61 |  |  |
| 0.521 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 53 |  |  |
| 0.576 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 48 |  |  |
| 0.124 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 59 |  |  |
| 0.523 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 47 |  |  |
| 0.606 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 55 |  |  |
| 0.296 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 38 |  |  |
| 0.763 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 50 |  |  |
| 0.561 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 54 |  |  |
| 0.202 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.mk_rho_frac_genes_above_0.9, A2_T1_analysis_set_ | 61 |  |  |
| 0.604 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 49 |  |  |
| 0.724 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 68 |  |  |
| 0.262 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 48 |  |  |
| 154 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.(row/group counts), A2_T2_generalizability_ranki | 3 |  |  |
| 0.714 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.frac_singleclass, A2_T1_analysis_set_census.gene | 55 |  |  |
| 0.013 | Cross-batch prediction elects a third se | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 70 |  |  |
| 0.688 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 58 |  |  |
| 0.050 | Cross-batch prediction elects a third se | A2_T3_cross_election_matrix.N | 145 | A2_T7.kruskal_H, kruskal_p, median_* | three method-level harshness tiers |
| 0.692 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 57 |  |  |
| 0.719 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 61 |  |  |
| 0.669 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 59 |  |  |
| 0.681 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 53 |  |  |
| 0.7453 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 56 | A2_T1.pv_lobo3_f1_macro_mean | method == 20_shambhala; full cut (all LOBO folds). 83 of the 84 rows carry pv_lobo3_f1_macro_mean. Rule 7b: re |
| 0.7002 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 92 | A2_T1.f1_mc_mean, f1_mc_min, n_mc | method == 20_shambhala; multiclass-only cut (folds with >= 2 classes). 82 of the 84 rows carry f1_mc_mean and  |
| 0.4292 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.frac_singleclass, A2_T1_analysis_set_census.gene | 43 | A2_T1.f1_mc_mean, f1_mc_min, n_mc | method == 20_shambhala; multiclass-only cut (folds with >= 2 classes). 82 of the 84 rows carry f1_mc_mean and  |
| 0.933 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 47 |  |  |
| 0.982 | Cross-batch prediction elects a third se | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 26 |  |  |
| 0.8875 | Cross-batch prediction elects a third se | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 56 |  |  |
| 0.866 | Cross-batch prediction elects a third se | A2_T5_per_batch_folds.auc | 57 |  |  |
| 0.980 | Cross-batch prediction elects a third se | A2_T5_per_batch_folds.auc | 78 |  |  |
| 0.953 | Cross-batch prediction elects a third se | A2_T5_per_batch_folds.auc | 43 |  |  |
| 323 | Cross-batch prediction elects a third se | - derived from tables/A2_T2 | 0 |  |  |
| 2,038 | Cross-batch prediction elects a third se | - derived from tables/A2_T2 | 0 |  |  |
| 59 | Cross-batch prediction elects a third se | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 118 | A2_T1.n_mc | n_mc == 0 |
| 0.325 | The sets elected by the individual metri | A2_T3_cross_election_matrix.distributional, A2_T3_cross_election_matrix.co | 39 |  |  |
| 0.295 | The sets elected by the individual metri | A2_T3_cross_election_matrix.distributional, A2_T3_cross_election_matrix.st | 56 |  |  |
| 0.137 | The sets elected by the individual metri | A2_T3_cross_election_matrix.global, A2_T3_cross_election_matrix.distributi | 51 |  |  |
| 0.082 | The sets elected by the individual metri | A2_T3_cross_election_matrix.local, A2_T3_cross_election_matrix.structural | 68 |  |  |
| 0.072 | The sets elected by the individual metri | A2_T3_cross_election_matrix.global, A2_T3_cross_election_matrix.local | 81 |  |  |
| 0.057 | The sets elected by the individual metri | A2_T3_cross_election_matrix.local, A2_T3_cross_election_matrix.distributio | 74 |  |  |
| 0.0045 | The sets elected by the individual metri | A2_T3_cross_election_matrix.L, A2_T3_cross_election_matrix.N | 179 | A2_T1.f1_mc_mean, f1_mc_min, n_mc | method == 20_shambhala; multiclass-only cut (folds with >= 2 classes). 82 of the 84 rows carry f1_mc_mean and  |
| 0.047 | The sets elected by the individual metri | A2_T3_cross_election_matrix.structural, A2_T3_cross_election_matrix.N | 71 |  |  |
| 0.042 | The sets elected by the individual metri | A2_T3_cross_election_matrix.structural, A2_T3_cross_election_matrix.compos | 75 |  |  |
| 0.076 | The sets elected by the individual metri | A2_T3_cross_election_matrix.local | 69 |  |  |
| 0.033 | The sets elected by the individual metri | A2_T3_cross_election_matrix.global, A2_T3_cross_election_matrix.composite | 73 |  |  |
| 0.024 | The sets elected by the individual metri | A2_T3_cross_election_matrix.structural, A2_T3_cross_election_matrix.M | 79 |  |  |
| 86 | The sets elected by the individual metri | A2_T0_shambhala_identity.median_20_shambhala, A2_T0_shambhala_identity.med | 115 |  |  |
| 0.537 | The sets elected by the individual metri | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 53 |  |  |
| 73 | Data availability | A2_T1_analysis_set_census.generalizability_index, A2_T1_analysis_set_censu | 108 | prediction_folds_long.csv.f1_macro | target == '3class' AND n_classes >= 2, run_id restricted to the 2,234 analysis set after the Shambhala rename; |
| 4.0 | Data availability | A2_T3_cross_election_matrix.L, A2_T3_cross_election_matrix.M | 127 |  |  |
| 2,407 | Supplementary material | - cited fact, source benchmark [38] | 0 |  |  |

## 7. Figures and tables the manuscript quotes

18 panels under `figures/panels_260917/` in PDF, SVG and PNG (inventory confirmed in `01_numbers.md`, §8 verification command 2); 12 recipe SVGs under `figures/recipe_assets_260917/`; nine result tables `tables/A2_T0..A2_T8_*_260917.csv`. No panel and no table was regenerated at this gate.
