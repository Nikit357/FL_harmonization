# Article 2 reference verification (run 260919_run1)

## Status

**Complete.** All 55 references were re-resolved independently of the literature scout's `02_literature.json` and of the team lead's spot checks. Nothing in this file is inherited: every identifier was fetched again, and every supporting passage was read again in the cited article.

- Check 1, existence: 55 of 55 items exist and were reached. 48 through NCBI eSummary by PMID, 4 through Crossref by DOI ([23], [38], [54], and the correction DOI inside [27]), 1 through the bioRxiv API ([24]), 1 through DataCite ([55]), 2 at the publisher's own page ([31], [37]).
- Check 2, identifiers: all 48 PMIDs resolve to the article their entry describes, and all 48 DOIs and first authors match. Three entries carried a wrong or truncated title ([24], [23], [26]); all three are corrected in the reference list and reported as defects D1, D2 and D11. 15 PubMed-indexed entries and the 4 without a PubMed record carried '[TO CONFIRM: author list]' or partial pagination; the data were in the records all along and are now filled in (defect D10).
- Check 3, support: 49 SUPPORTS, 3 PARTIAL ([22], [34], [49]), 2 DOES NOT SUPPORT ([51], [55]), 1 UNVERIFIED ([54]). 36 were judged against the body of the cited article, 15 against the abstract and the PubMed record where no full text is reachable from this environment, 4 against a publisher or registry record.

**Not started.** Nothing. No reference was swapped, added or removed; failures are reported below and left for the writer.

The elink trap of plan section 11, issue 15, was avoided by construction: PMC identifiers were taken from the `articleids` block of the eSummary response for each PMID, so no elink call was made and no `pubmed_pmc_refs` link set could be mistaken for the article. Every retrieved full text was checked by reading its title before any passage was quoted from it.

Files written this run:

- `manuscript/references_260917.md` -- the 55-entry list, Mendeley-paste ready.
- `manuscript/reference_support_260917.md` -- the quoted supporting passage behind each citation.
- `workflow_runs/260919_run1/04_references_verified.md` and `.json` -- this record.

---

## Defects

### D1 -- [24] doi:10.1101/2025.09.24.677146 (no PMID)

**Cited at.** references_260917.md entry [24]; cited in Introduction para 3

**Defect.** The entry carried the title 'Joint analysis of human retroelements-linked histone modification profiles reveals quickly evolving loci'. The bioRxiv record for this DOI has the title 'Joint analysis of human retroelements-linked histone modification profiles reveals quickly evolving molecular processes connected with cancer'. The ending was wrong, and the record has two versions (v1 2025-09-27, v2 2025-10-02) with neither named.

**Required fix.** Use the bioRxiv title verbatim and name the version and its posting date. Corrected in the reference list this run; confirm against https://doi.org/10.1101/2025.09.24.677146 before submission.

### D2 -- [23] doi:10.1098/rsos.260639 (no PMID)

**Cited at.** references_260917.md entry [23]; cited in Introduction para 3

**Defect.** The entry carried a truncated title ending at 'multi-modal epigenomic profiling'; the published title continues 'in a telomere-to-telomere human genome reference'. The entry also carried no author, no volume and no issue, although Crossref gives Nikitin DM as sole author, R Soc Open Sci 2026;13(8), posted 2026-08-26.

**Required fix.** Use the full published title and add the author, volume and issue. Corrected in the reference list this run.

### D3 -- [55] doi:10.5281/zenodo.19052415 (no PMID)

**Cited at.** Data availability para 1 -- 'A further deposited dataset from this group is archived at https://doi.org/10.5281/ZENODO.19052415 [55].'

**Defect.** The DataCite record for this DOI is a Dissertation, not a dataset: 'Retroelements-driven regulatory evolution of human genes and molecular processes: analysis of genome binding profiles of transcription factors and histone modifications', Zenodo 2026, Nikitin D. Both the sentence ('A further deposited dataset') and the old entry label ('[dataset]') describe it wrongly, and the title in the entry stopped before the colon.

**Required fix.** Writer to decide: either describe it as a dissertation deposit in the Data availability sentence, or drop it from Data availability, where a dissertation is not a data source for this article. The reference entry is corrected to '[dissertation]' with the full title this run; the manuscript sentence is left untouched for the writer.

### D4 -- 30484103 ([51])

**Cited at.** Results and discussion, 'Preservation of biomarker expression and of cross-batch rank structure elects a distinct set of approaches' para 8 -- 'Marker readouts are known to move with the preparation of the input material, including extracellular-vesicle and plasma-derived inputs [50,51,52]'

**Defect.** The reference does not support the sentence. Shtam 2019 reports that plasma exosomes stimulate adhesion, migration, invasion and metastatic dissemination of breast cancer cells through FAK signalling. That is a biological effect of the vesicles, not a measured readout that changes with how the input material was prepared. The full text is subscription-only, so the verdict rests on the abstract and the PubMed record; [50] and [52], cited in the same bracket, do support the sentence.

**Required fix.** Writer to drop [51] from that bracket or to rewrite the clause so that what [51] shows is what is claimed. Not patched here: the verifier reports and does not swap references.

### D5 -- [54] doi:10.1007/978-3-030-30363-1_5 (no PMID)

**Cited at.** Conclusions para 4 -- 'Stating what a measurement counts before applying it is the ordinary discipline of method development [54].'

**Defect.** The chapter exists and its identifiers now resolve in full (Nikitin D, Sorokin M, Tkachev V, Garazha A, Markov A, Buzdin A; Springer 2019; pp. 85-111; ISBN 978-3-030-30363-1), but the text is behind a paywall and could not be opened, so no passage can be quoted for the sentence. The sentence states a general point about method development, which is not a claim the chapter itself makes, so the citation is decorative.

**Required fix.** Writer to decide whether the sentence needs a citation at all; if it keeps one, quote the chapter passage that states the principle. The bibliographic [TO CONFIRM] markers are resolved in the reference list this run.

### D6 -- 28327985 ([34])

**Cited at.** Introduction para 4 -- '... the unit a cross-validation splits on has to match the generalization being claimed, so a claim about transfer between sites needs folds cut across sites [34].'

**Defect.** Partial support. Saeb 2017 establishes that the split has to match the use case, demonstrated for subject-wise against record-wise cross-validation. It says nothing about sites; the clause about transfer between sites is the authors' own extension of the principle and is not marked as theirs.

**Required fix.** Writer to attribute the site-level extension explicitly, for example by stating the principle as Saeb gives it and naming the extension to batches as this work's application of it.

### D7 -- 31357584 ([49])

**Cited at.** Materials and methods, 'The biology-facing metric classes L, M and N' para 1 -- 'the same panel logic underlies marker readouts in earlier expression work [48,49].'

**Defect.** Partial support. [48] does show panel logic, a two-gene signature that outperforms its individual genes. [49] validates two individual markers, FREM2 and SPRY1, at transcript and protein level across glioma grades; it is a marker readout but not a gene panel, so 'the same panel logic' overstates what it shows.

**Required fix.** Writer to narrow the claim for [49] or to cite it for the marker readout alone.

### D8 -- 40147445 ([22])

**Cited at.** Introduction para 3 -- 'The same transfer problem governs expression signatures outside lymphoma, including ... and T-cell lymphoma [22]'

**Defect.** Partial support. The paper is a patient-derived biorepository and PDX resource for T-cell lymphoma with transcriptomic profiling, and it does correct technical and host variation by surrogate variable analysis, but it makes no claim about signature transfer between platforms, which is the claim the sentence attaches to it.

**Required fix.** Writer to keep it only as an example of lymphoma transcriptomic profiling, or to replace the clause with one the paper supports.

### D9 -- 34837041 ([36])

**Cited at.** Introduction para 4 -- 'a form of leakage that is documented for genomics data specifically [36]'

**Defect.** Verification limitation, not a proven error. Whalen 2022 has no PMC record and the free eScholarship copy is served behind a script this environment cannot execute, so only the abstract was reachable. The abstract supports the pitfalls of supervised machine learning in genomics and that the structure of genomics data can bias performance evaluations; the word leakage does not occur in the reachable text, so the narrower claim was not verified at body level.

**Required fix.** Writer or team lead to open the published review once and confirm that it names leakage, or to soften the clause to what the abstract states.

### D10 -- 17, 18, 19, 20, 21, 22, 25, 26, 27, 28, 48, 49, 50, 51, 52

**Cited at.** references_260917.md, 15 entries

**Defect.** These 15 PubMed-indexed entries carried '[TO CONFIRM: author list]' (13 of them) or a partial author list ([27], [51]), and seven carried no volume, issue or article number. The same marker stood on the four entries with no PubMed record ([23], [24], [54], [55]). Every one of these values was available in the PubMed, Crossref, bioRxiv or DataCite record all along.

**Required fix.** Resolved in this run: author lists, volume, issue and article numbers are transcribed into the reference list from the NCBI eSummary response of 2026-09-19 and, for the four items with no PubMed record, from Crossref, the bioRxiv API and DataCite. No [TO CONFIRM] marker for an author list remains; the markers that remain say only that an item is not indexed in PubMed.

### D11 -- 31597351 ([26])

**Cited at.** references_260917.md entry [26]; cited in Introduction para 3

**Defect.** The entry carried a truncated title, 'Retroelement-linked H3K4me1 histone tags uncover regulatory evolution trends of gene enhancers'. The PubMed record continues '... and Feature Quickly Evolving Molecular Processes in Human Physiology'. It is the only PubMed-indexed entry of the 48 whose title did not match the record in full.

**Required fix.** Use the full PubMed title. Corrected in the reference list this run.

---

## Per-reference record

| Ref | PMID | Cited at | PMID and DOI correct | Verdict |
|---|---|---|---|---|
| [1] | 20838408 | Introduction para 1 | yes | SUPPORTS |
| [2] | 22851511 | Introduction para 1 | yes | SUPPORTS |
| [3] | 36140419 | Introduction para 1 | yes | SUPPORTS |
| [4] | 22151536 | Introduction para 2 | yes | SUPPORTS |
| [5] | 26844019 | Introduction para 2 | yes | SUPPORTS |
| [6] | 34949812 | Introduction para 2 | yes | SUPPORTS |
| [7] | 31948481 | Introduction para 2 | yes | SUPPORTS |
| [8] | 30573817 | Introduction para 2 | yes | SUPPORTS |
| [9] | 31740819 | Introduction para 2 | yes | SUPPORTS |
| [10] | 10676951 | Introduction para 3 | yes | SUPPORTS |
| [11] | 12075054 | Introduction para 3 | yes | SUPPORTS |
| [12] | 15548776 | Introduction para 3 | yes | SUPPORTS |
| [13] | 29475724 | Introduction para 3 | yes | SUPPORTS |
| [14] | 24398326 | Introduction para 3 | yes | SUPPORTS |
| [15] | 29713087 | Introduction para 3 | yes | SUPPORTS |
| [16] | 29641966 | Introduction para 3 | yes | SUPPORTS |
| [17] | 34888350 | Introduction para 3 | yes | SUPPORTS |
| [18] | 36316649 | Introduction para 3 | yes | SUPPORTS |
| [19] | 35359606 | Introduction para 3 | yes | SUPPORTS |
| [20] | 33748479 | Introduction para 3 | yes | SUPPORTS |
| [21] | 33839309 | Introduction para 3 | yes | SUPPORTS |
| [22] | 40147445 | Introduction para 3 | yes | PARTIAL |
| [23] | not indexed in PubMed | Introduction para 3 | yes (entry metadata corrected) | SUPPORTS |
| [24] | not indexed in PubMed | Introduction para 3 | yes (entry metadata corrected) | SUPPORTS |
| [25] | 31491936 | Introduction para 3 | yes | SUPPORTS |
| [26] | 31597351 | Introduction para 3 | yes (entry metadata corrected) | SUPPORTS |
| [27] | 30736359 | Introduction para 3 | yes | SUPPORTS |
| [28] | 29441061 | Introduction para 3 | yes | SUPPORTS |
| [29] | 24967636 | Introduction para 4 | yes | SUPPORTS |
| [30] | 22611599 | Introduction para 4 | yes | SUPPORTS |
| [31] | not indexed in PubMed | Introduction para 4 | yes | SUPPORTS |
| [32] | 16504092 | Introduction para 4 | yes | SUPPORTS |
| [33] | 11983868 | Introduction para 4 | yes | SUPPORTS |
| [34] | 28327985 | Introduction para 4 | yes | PARTIAL |
| [35] | 37720327 | Introduction para 4 | yes | SUPPORTS |
| [36] | 34837041 | Introduction para 4 | yes | SUPPORTS |
| [37] | not indexed in PubMed | Introduction para 4 | yes | SUPPORTS |
| [38] | not indexed in PubMed | Introduction para 5 | yes | SUPPORTS |
| [39] | 16632515 | Materials and methods — Dataset, harmonization approaches and the analysis set para 1 | yes | SUPPORTS |
| [40] | 33015620 | Materials and methods — Dataset, harmonization approaches and the analysis set para 1 | yes | SUPPORTS |
| [41] | 17907809 | Materials and methods — Dataset, harmonization approaches and the analysis set para 1 | yes | SUPPORTS |
| [42] | 29608177 | Materials and methods — Dataset, harmonization approaches and the analysis set para 1 | yes | SUPPORTS |
| [43] | 29360996 | Materials and methods — Dataset, harmonization approaches and the analysis set para 1 | yes | SUPPORTS |
| [44] | 18325927 | Materials and methods — Dataset, harmonization approaches and the analysis set para 1 | yes | SUPPORTS |
| [45] | 30727942 | Materials and methods — Dataset, harmonization approaches and the analysis set para 1 | yes | SUPPORTS |
| [46] | 35617464 | Materials and methods — Dataset, harmonization approaches and the analysis set para 1 | yes | SUPPORTS |
| [47] | 25150836 | Materials and methods — The biology-facing metric classes L, M and N para 1 | yes | SUPPORTS |
| [48] | 32486168 | Materials and methods — The biology-facing metric classes L, M and N para 1 | yes | SUPPORTS |
| [49] | 31357584 | Materials and methods — The biology-facing metric classes L, M and N para 1 | yes | PARTIAL |
| [50] | 33187334 | Results and discussion — Preservation of biomarker expression and of cross-batch rank structure elects a distinct set of approaches para 8 | yes | SUPPORTS |
| [51] | 30484103 | Results and discussion — Preservation of biomarker expression and of cross-batch rank structure elects a distinct set of approaches para 8 | yes | DOES NOT SUPPORT |
| [52] | 32300430 | Results and discussion — Preservation of biomarker expression and of cross-batch rank structure elects a distinct set of approaches para 8 | yes | SUPPORTS |
| [53] | 26272994 | Results and discussion — Cross-batch prediction elects a third set, whose ranking is stable across two cuts of the fold population para 4 | yes | SUPPORTS |
| [54] | not indexed in PubMed | Conclusions para 4 | yes | UNVERIFIED |
| [55] | not indexed in PubMed | Data availability para 1 | yes (entry metadata corrected) | DOES NOT SUPPORT |

The quoted passage behind each row is in `manuscript/reference_support_260917.md`, which carries the same content as this file's JSON twin.
