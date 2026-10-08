# Article 2 — team-lead verdict, Gate 1 (run 260919_run1, round 2)

Team-lead Gate 1, round 2 of at most 2. Judges workflow_runs/260919_run1/01_numbers.{json,md} (code-analyst) and 02_literature.{json,md} (literature-scout). Round 1 raised four defects; all four are re-checked here against source, not against the agents' assertions.

## Status

**Verdict: accept** · gate 1 · round 2

**Complete**

- All four round-1 defects re-checked against source. Defects 1, 2, 3 and 4 are fixed and the fixes reproduce.
- Analysis set independently re-derived from tables/A2_T1_analysis_set_census_260917.csv: 2,234 rows, 31 methods, 14 strategies, 3 imputations, 84 rows named 20_shambhala, 0 rows whose method still starts with shambhala_.
- Defect 1 re-derived from ../harmonization-metrics/metric_tables/prediction_folds_long.csv: 20,343 non-canonical Shambhala 3-class folds over 17 variants, 1,200 canonical, 648 residual (34_arsyn 324 + 38_harman 324, 96 run_ids), 20,343 + 648 = 20,991 = 53,737 - 32,746. The 74.23 pct_samples_allNA floor for both methods confirmed in Supplementary File 3.
- Defect 2 re-derived from A2_T1: Shambhala full cut median 0.745272 over 83 rows, multiclass-only median f1_mc_mean 0.700210 over 82, f1_mc_min 0.4292 over 82, n_mc 9 over 83.
- Defect 4 re-derived from A2_T7: the seven per-metric n triples reproduce exactly (344/1042/848, 344/1042/800, 344/1042/847 x3, 333/1016/825 x2).
- Nine further numbers re-derived independently of the round-1 sample and of the analyst's code path; all nine reproduce.
- audit_numbers.py on 01_numbers.md with --evidence: 184 distinct numbers, 184 sourced, 0 unsourced, exit 0.
- Random 21% PMID sample (7 of 33 distinct numeric PMIDs, python random.sample seed 20260921) re-resolved through NCBI E-utilities; metadata and quote verified for every one.
- The four requoted entries outside the random sample re-resolved as well, so all six defect-3 entries were checked: 34949812, 31948481, 26272994, 22151536, 29475724, 16504092.
- Both non-PubMed JMLR entries re-downloaded from jmlr.org and the quotes located verbatim in the PDFs.
- Panel inventory enumerated by stem, which closes the code-analyst's third open_to_confirm item.
- check_overlap.py exercised on the literature gap statement against Article 1 and the source document: exit 0, no 8-gram overlap.

**In progress**

- none

**Not started**

- Rules 1, 3 and 4 against their real subject. manuscript/ holds only .gitkeep, so no manuscript prose exists in this run. These three rules must be checked at gate 2.
- Rule 5. No read access to the Figma file's version history from this session.
- Gate 2 on the drafted manuscript.

**Environment:** `source ~/venvs/collagen_3_11/bin/activate; pandas + scipy over tables/*.csv and ../harmonization-metrics/metric_tables/prediction_folds_long.csv; urllib against eutils.ncbi.nlm.nih.gov; curl + pypdf against jmlr.org`

## Resolution of the four round-1 defects

### Round-1 defect 1 - unrestricted_fold_denominators stated 21,543

- **Agent:** code-analyst
- **Status:** FIXED, verified
- **Team-lead re-derivation:** prediction_folds_long.csv, target == '3class' -> 53,737 folds. method = run_id.split('__')[2]. All 18 Shambhala variants -> 21,543 (which is where the old number came from). Excluding shambhala_P0std_Q0std -> 20,343 over 17 variants; the canonical variant alone -> 1,200. Analysis-set restriction after the rename -> 32,746, so 20,991 are excluded. Residual excluded folds after the 17 variants: 648, entirely 34_arsyn (324) and 38_harman (324) over 96 run_ids. Supplementary File 3 (supplementary_260824) gives both methods min pct_samples_allNA = 74.234291 over 84 rows each, 0 rows below 5. 20,343 + 648 = 20,991 closes exactly.
- **Propagation:** The corrected figure is in 01_numbers.json, 01_numbers.md (entry, discrepancy table and cause line), analysis/article2_generalizability.py:317 and analysis/build_numbers_json.py:179-181. The string 21,543 survives only where it is explicitly labelled as the wrong value, which is the right treatment.

### Round-1 defect 2 - Shambhala Group N reported on the full cut only (rule 7b)

- **Agent:** code-analyst
- **Status:** FIXED, verified
- **Team-lead re-derivation:** A2_T1, method == '20_shambhala' (84 rows). pv_lobo3_f1_macro_mean: 83 non-null, median 0.745272. f1_mc_mean: 82 non-null, median 0.700210. f1_mc_min: 82 non-null, median 0.4292. n_mc: 83 non-null, median 9. Both the values and the two different denominators are stated correctly in the new median_lobo3_f1_multiclass_only entry, and each cut's filter field now names the other cut.

### Round-1 defect 3 - five quotes verbatim but not claim-carrying, plus one borderline

- **Agent:** literature-scout
- **Status:** FIXED, verified
- **Team-lead re-derivation:** All six entries re-resolved independently (esummary + elink pubmed_pmc + efetch). Title, DOI and year match the stored values for all six; every new quote was located verbatim in the retrieved PMC full text after whitespace and entity normalization. Each new quote states the claim it is attached to: 34949812 names four methods that favour batch removal and two that make the opposite choice; 31948481 says the assessment metrics did not always agree with each other; 26272994 says the unbalanced group-batch distribution leads to deflated estimates of the estimation errors and over-confidence; 22151536 says it is not possible to rank the methods by either detection statistic; 29475724 states the 23-gene score separates two FL groups with markedly distinct outcomes; 16504092 says the minimum CV error estimate is not an unbiased estimate of the true error. The superseded quote and the superseded supports_claim are retained in each entry's verification block, so the change is auditable.
- **Note:** 22151536 was corrected in the right direction: the earlier claim that this benchmark ranked methods on one criterion is contradicted by the paper, and the entry now says so.

### Round-1 defect 4 - harshness tier caveat covered only two of the five per-metric shortfalls

- **Agent:** code-analyst
- **Status:** FIXED, verified
- **Team-lead re-derivation:** A2_T7_harshness_by_lmn_260917.csv read directly. n_low/n_medium/n_high per metric: mk_rho_mean_markers 344/1042/848; mk_rho_marker_minus_hk 344/1042/800; xb_rank_agree 344/1042/847; xb_margin 344/1042/847; pv_lobo3_f1_macro_mean 344/1042/847; f1_mc_mean 333/1016/825; pv_lobo2_auc_macro_mean 333/1016/825. The new harshness.per_metric_n entry carries all seven, and tier_sizes now says in its own filter field that the membership is not the denominator of any tier median.

## Numbers re-derived in round 2, independently of round 1's sample

| key | as written | team lead | source |
|---|---|---|---|
| `analysis set rows / methods / strategies / imputations` | 2,234 / 31 / 14 / 3 | 2234 / 31 / 14 / 3 | A2_T1, direct read |
| `rows named 20_shambhala; rows still prefixed shambhala_` | 84; 0 | 84; 0 | A2_T1, method value counts |
| `gates.joint_L_M_gate` | 1,686 | 1686 | A2_T1, (mk_rho_mean_markers > 0.75) & (xb_margin > 0) |
| `prediction.n_eligible_non_degenerate` | 1,527 | 1527 | A2_T2, strat not in (A_confirmed_bad, B_extended_bad) & n_mc >= 5 |
| `prediction.leading_non_degenerate` | S0_no_removal__softimpute__29_combat_ref__post0; full 0.946 / mc 0.887 / mc_min 0.462 / n_mc 11 / AUC 0.932 / rho 0.880 | same run_id; 0.946437 / 0.887082 / 0.4615 / 11 / 0.931936 / 0.880159, and it is the top row of the eligible set | A2_T2 sorted by pv_lobo3_f1_macro_mean |
| `prediction.n_zero_multiclass_folds` | 59 | 59 | A2_T1, n_mc == 0 |
| `prediction.spearman_full_vs_multiclass` | 0.810 over n = 2,174 | 0.8100, n = 2174 | A2_T2, scipy spearmanr on rows carrying both cuts |
| `prediction.spearman_min3_multiclass_folds` | 0.815 over n = 2,058 | 0.8151, n = 2058 | same, n_mc >= 3 |
| `agreement_specific n and share` | 61 rows, 2.84% of the 2,150 non-raw | 61 rows; 61/2150 = 2.84% | A2_T6 row count |
| `fold_composition.n_3class_folds and n_batches` | 32,746; 24 | 32746 summed over the three batch == '__ALL__' rows; 24 distinct batch values excluding the sentinel | A2_T8 |
| `panel inventory` | 18 panels, 21 stems, 63 files, 0 missing | 21 stems x 3 formats = 63 files; a2_p1..a2_p18 all present; a2_p14 ships as 4 method variants | ls figures/panels_260917/ |

Every one reproduces. No number in either artifact failed re-derivation in this round.

## Rule 7b sweep

Walked every string in 01_numbers.json for mentions of pv_lobo3_f1_macro_mean and checked each for a multiclass-only companion.

13 mentions. Every approach-level prediction quantity now carries both cuts: shambhala.median_lobo3_f1 is paired with shambhala.median_lobo3_f1_multiclass_only; prediction.leading_non_degenerate carries value_rule7b with multiclass_only_mean_f1 = 0.887 beside full_mean_f1 = 0.946; both Spearman entries are themselves full-versus-multiclass comparisons; the harshness table reports pv_lobo3_f1_macro_mean and f1_mc_mean as separate rows with separate n. fold_composition reports folds split by n_classes, which is the both-cuts information itself. Binding rule 7b is satisfied across the artifact.

## Literature re-resolution

**Method.** python random.sample over the 33 distinct numeric PMIDs, seed 20260921; 7 drawn = 21%. Each re-resolved with esummary, its PMC id taken only from the pubmed_pmc linkname, full text fetched with efetch (PubMed abstract where no PMC link exists), and the stored quote searched after HTML-entity, ligature and whitespace normalization. The four requoted entries that the random draw missed were checked on top of the sample.

**Random sample (21%):** 26272994, 12075054, 17907809, 36140419, 31948481, 11983868, 29713087

**Requoted entries checked on top:** 34949812, 22151536, 29475724, 16504092

**Result.** 11 of 11 pass. Title, journal, year and DOI match the stored values for every one; every stored quote was found verbatim in the text retrieved for the paper named. 36140419 is quoted twice and both quotes were located. 12075054 has no PMC full text and its full_text_read is correctly false. 11983868 resolves to PMC124442, which carries front matter only; the quote is in that record's abstract and full_text_read is correctly false.

**Non-PubMed.** Both JMLR entries re-downloaded from jmlr.org in this round. cawley10a.pdf, 29 pages, HTTP 200, 759,286 bytes: the quote is present verbatim. grandvalet04a.pdf, 17 pages, HTTP 200, 129,905 bytes: the quote is present verbatim in section 9, Conclusions (an initial miss was my own normalization stripping the fi ligature in 'significance', not a defect in the entry). The [TO CONFIRM] form on pmid and doi is the correct treatment for a journal PubMed does not index.

**Fabrication check.** No fabricated reference, DOI, PMID, PMC id or URL was found in either artifact. Every identifier I tested resolved to the record claimed. The run is not aborted.

## Panel stems enumerated

- `a2_p1_rho_vs_margin`
- `a2_p2_margin_ranking`
- `a2_p3_agreement_specific`
- `a2_p4_lobo_ranking`
- `a2_p5_per_batch`
- `a2_p6_singleclass_audit`
- `a2_p7_strategy_imputation_method`
- `a2_p8_generalizability_index`
- `a2_p9_cross_election_circos`
- `a2_p10_venn_supervenn`
- `a2_p11_harshness_lmn`
- `a2_p12_raw_to_harmonized`
- `a2_p13_election_sankey`
- `a2_p14_expression_scatter_01_raw`
- `a2_p14_expression_scatter_12_scanorama`
- `a2_p14_expression_scatter_13_fsmvn`
- `a2_p14_expression_scatter_29_combat_ref`
- `a2_p15_panel_coverage`
- `a2_p16_qc_gate`
- `a2_p17_rho_by_signature`
- `a2_p18_gene_method_clustermap`

21 stems × 3 formats = 63 files; `a2_p1` through `a2_p18` are all present, `a2_p14` as four method variants.

## Defects

None. All four round-1 defects are fixed and the fixes were re-derived from source by the team lead. No new defect was raised in round 2.

## Accepted

- 01_numbers.json and 01_numbers.md - the corrected unrestricted_fold_denominators entry: 53,737 unrestricted 3-class folds, 32,746 in the analysis set, 20,991 excluded, of which 20,343 are the 17 non-canonical Shambhala P/Q variants and 648 are 34_arsyn and 38_harman failing pct_samples_allNA < 5, with 1,200 canonical Shambhala folds retained. Re-derived by the team lead from prediction_folds_long.csv and Supplementary File 3; the arithmetic closes.
- 01_numbers.json - shambhala.median_lobo3_f1 and shambhala.median_lobo3_f1_multiclass_only as a rule-7b pair: 0.7453 over 83 rows beside 0.7002 / 0.4292 / 9 over 82, 82 and 83 rows, with each filter field naming the other cut's denominator.
- 01_numbers.json - harshness.per_metric_n, the seven per-metric n triples from A2_T7, and the rewritten harshness.tier_sizes filter that forbids quoting tier membership as a median denominator.
- 01_numbers.json - the analysis-set definition and census: 2,234 rows, 31 methods, 14 strategies, 3 imputations, 84 rows named 20_shambhala, 0 rows still prefixed shambhala_. Binding rule 7 is satisfied.
- 01_numbers.json - the Shambhala identity evidence (A2_T0): 78 of 79 shared numeric columns identical, the exception being compute_time_s.
- 01_numbers.json - the fold-composition block: 32,746 3-class folds, 15,436 single-class (47.1%), 17,310 multiclass, 24 batches, medians 0.903 / 0.629 / 0.804.
- 01_numbers.json - the prediction block: 1,527 eligible non-degenerate approaches, 59 with zero multiclass folds, the leading approach on both cuts, and the two Spearman correlations between the cuts.
- 01_numbers.json - the agreement-specific block: 61 rows, 2.84% of the 2,150 non-raw approaches, and the two-implementation tie at K_ffpe_only/knn/post0 that may not be quoted as a single winner.
- 01_numbers.json - the edit to analysis/build_numbers_json.py alongside analysis/article2_generalizability.py. The code-analyst asked whether this was wanted: it was. The generator produces the discrepancy string, so a fix applied only to the generated file reverts on the next run.
- 02_literature.json - the six requoted entries (34949812, 31948481, 26272994, 22151536, 29475724, 16504092). Every new quote is verbatim in the paper named and states the claim attached to it, and the superseded quote and claim are retained in the verification block.
- 02_literature.json - the gap statement. It now rests on two entries whose quotes state metric disagreement directly, so no [TO CONFIRM] marker is needed on the Article 2 novelty claim. It also passes check_overlap.py against Article 1 and the source document with zero 8-gram hits, and contains no banned construction.
- 02_literature.json - the PMID set: 36 entries over 35 papers, all carrying a numeric PMID or a literal [TO CONFIRM] string; the 21% random sample plus the four extra requoted entries all re-resolve with matching metadata and verbatim quotes.
- 02_literature.json - the two JMLR entries, re-verified from the publisher PDFs in this round.
- 02_literature.json - the could_not_open record, including the ACM 403 for Kaufman 2012 and the ten abstract-only entries.
- Panel inventory: 18 panels, 21 stems, 63 files across PDF, SVG and PNG. The code-analyst's third open_to_confirm item is closed by enumeration.

## The five rules

| rule | passed | evidence |
|---|---|---|
| 1. Every number in the manuscript resolves to a row in a table in tables/. | **no** | Cannot be checked against its subject: manuscript/ holds only .gitkeep, so no manuscript exists in this run. Checked against the evidence artifact instead, and there it passes: `python tools/audit_numbers.py workflow_runs/260919_run1/01_numbers.md --tables tables/ --evidence workflow_runs/260919_run1/01_numbers.json` reports 184 distinct numbers, 184 sourced, 0 unsourced, exit 0. Tables-only leaves 12 unsourced, all of them filter-produced row counts, values from prediction_folds_long.csv (which is not under tables/), date tags and plan line numbers; I re-derived 20 numbers myself across both rounds and every one reproduces, including the three round-1 corrections. Must be re-checked at gate 2 against the manuscript. |
| 2. Every citation has a PMID or an explicit [TO CONFIRM], and 20% of them re-resolve. | yes | All 36 entries carry either a numeric PMID or a literal [TO CONFIRM: ...] string in both the pmid and doi fields; 0 carry neither. A random 21% sample of the 33 distinct numeric PMIDs (python random.sample seed 20260921: 26272994, 12075054, 17907809, 36140419, 31948481, 11983868, 29713087) was re-resolved individually through esummary, elink and efetch; title, journal, year and DOI match the stored values for all 7 and every stored quote was located verbatim. The four requoted entries the draw missed (34949812, 22151536, 29475724, 16504092) were checked on top, so 11 of 35 papers (31%) were re-resolved by the team lead this round. Both JMLR entries were re-verified from jmlr.org PDFs. Binding rule 3's cross-check of the literature-scout's citations by a second agent is satisfied by this pass. Round-1 defect 3 is closed: all six quotes now carry their claims. |
| 3. The overlap gate passes with zero 8-gram hits outside tools/overlap_allow.txt. | **no** | Could not be checked against its subject. check_overlap.py compares manuscript prose against FL_harmonization_article_NAR_260912.docx and the source document, and no manuscript exists: manuscript/ holds only .gitkeep. I exercised the gate on the one piece of prose this gate produced that will reach the manuscript, the literature gap statement (161 tokens): exit 0, no verbatim overlap against either source. That is not the manuscript, so the rule stands unchecked and must be run at gate 2. |
| 4. check_style.py exits 0. | **no** | Could not be checked, for the same reason as rule 3: check_style.py takes the manuscript markdown and enforces the six F1000 section word budgets, and no manuscript markdown exists in this run. Partial negative evidence only: neither 01_numbers.md nor 02_literature.md contains the banned phrase 'rather than' (grep count 0 in both), and the gap statement contains no banned antithesis. Must be run at gate 2. |
| 5. No Figma frame was modified beyond the §3.4 renaming. | **no** | Could not be verified independently. This session has no read access to the Figma file's version history; the only Figma tool exposed is the unauthenticated mcp__plugin_figma_figma__authenticate, so this session could not itself have written to Figma. The negative evidence available is the agents' own declaration: neither 01_numbers nor 02_literature records a Figma node id or a write, and 01_numbers.md lists 'Any Figma write' under work deliberately not done. A declaration is not confirmation. Binding rule 8 also states Figma assembly happens in an interactive session, not in this workflow. Confirming the rule needs the file version history from that session. |

## Instructions to the drafter

- Quote prediction.leading_non_degenerate from its value_rule7b field, which carries multiclass_only_mean_f1 = 0.887 beside full_mean_f1 = 0.946. The plain value field omits the multiclass mean and would breach rule 7b if quoted alone.
- Never quote a harshness tier median against the tier membership 344 / 1,042 / 848. Take the denominator from harshness.per_metric_n for the metric being quoted.
- Do not write '59 approaches report F1 = 1.000'. 59 approaches have zero multiclass folds; 5 of them report F1 = 1.000, and the 59 span 0.0100 to 1.000.
- The K_ffpe_only/knn/post0 result is a tie between 08_inmoose_combatseq and 06_combat_seq to six decimals. Neither may be named as the single winner.
- Audit the finished manuscript with `python tools/audit_numbers.py manuscript/DRAFT.md --tables tables/ --evidence workflow_runs/260919_run1/01_numbers.json`. Tables-only will fail on the filter-produced counts, which are legitimate and recorded in the evidence JSON.

## Open items for Daniil

- Rules 1, 3 and 4 were not exercised against a manuscript in this run, because the drafting phase had not produced one when gate 1 ran. They carry over to gate 2 in full.
- Rule 5 cannot be confirmed from any workflow session. If it matters for the record, check the Figma file's version history from the interactive session that owns the document and confirm that the only change since 2026-09-17 is the §3.4 frame renaming.
- The method-harshness composite direction remains the open defect recorded in article_2_extended_comparison/CLAUDE.md. Article 2 quotes the harshness tier medians from A2_T7, which are recomputed, so the manuscript must not also quote the published low/medium/high ordering until you re-derive it from Finally_assembled_figures_for_article.ipynb Figure 6A.
- Kaufman 2012 on data leakage could not be opened from this environment (ACM returns HTTP 403, and the paper is not in PubMed). It is not cited. If you want it, it has to be fetched from a network that can reach the ACM Digital Library.
- Reference numbering is still unassigned; the literature-scout left it to the drafter, which is correct, but nothing has done it yet.
