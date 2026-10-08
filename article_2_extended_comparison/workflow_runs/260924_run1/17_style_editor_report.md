# 17 — Style-editor report, Phase 4 (rule-15 density pass), 2026-09-25

## Status

- **Done.** All 64 density hits are fixed in the draft files (`03a_draft_reviewed.md`,
  `03b_draft_unreviewed.md`, `08_legends.md`). None was fixed in the assembled manuscript.
- Also done: "grey" → "gray" three times in `08_legends.md`. `[FIG:fig_markers_lm]F` and
  `[FIG:sfig_marker_qc]A, C` are now cited in the body. The five em-dash cells of Table 1
  (`P66+1`) are now "n/a".
- No new number was introduced. No test was dropped. No fifth main-text table was created.
  Every `⟦CIT:…⟧` token and `[38]`, `[50,51]`, `[52]` is unchanged (the assembler reports 46 tokens and no problems).
- Nothing is left open. No sentence needed an exception.

## Method

- The checker counts every number except figure and table labels, method names, years and
  versions. A p-value mantissa and a MAD each count as one value. The splitter only starts a
  new sentence at a capital letter or a bracket. So a sentence that began with a method name
  (`33_amdbnorm …`, `14_qsmooth …`, `10 of the 14 …`) was fused with the sentence before it.
  Several hits were fused pairs, and the fix was to reword the sentence opening ("The
  method 13_fsmvn…", "Last came 14_qsmooth…", "Of the 14 … strategies, 10 …").
- Small counts at the start of a sentence, or in design lists, are spelled out ("three
  imputations", "Nine lost", "nine of the 15"). Daniil's wording is otherwise unchanged (rule 11).
- MADs are routed to **Supplementary File 1, sheet Paired_tests**. `A2_T10` carries `mad_a` and
  `mad_b` for every one of these tests. The median comparison and its p stay in the text, and
  the source comments moved with the MAD values.
- `sfig_marker_qc`: P27 was `[keep]` and is now `[edit]`. The full base paragraph from
  `00_paragraph_index.json` is carried verbatim with two clauses added, citing A (coverage)
  and C (per-gene ρ by signature). The three CIT tokens are unchanged.
- `fig_markers_lm` F: one qualitative sentence was added at the end of P72, with no number. It was
  read off the rendered panel: the tier medians rise in every tier and least in the high
  tier, and part of the high-tier lines fall steeply.

## Fixed sentences

Values/tests are the checker's counts before the fix. All sentences now hold ≤ 3 values and ≤ 1 test.

| # | Paragraph | Values/tests | Before (first 80 characters) | What was done |
|---|---|---|---|---|
| 1 | P8 | 6/0 | We used the 2,234 approaches of the recent real-world benchmark: 31 harmonizatio | split (design list moved to its own sentence; 3 and 2 spelled out) |
| 2 | P16 | 6/0 | To address these current issues in transcriptomic cross-platform harmonization, | split (design list moved to its own sentence; 3 and 2 spelled out) |
| 3 | P16 | 4/0 | Class N resulted in the ComBat family (05_combat, 29_combat_ref, 06_combat_seq a | split (class N / class M) |
| 4 | P20 | 4/0 | The GC B-cell lymphomas dataset, the 14 prior batch-removal strategies, the 3 im | minimal: "three imputation schemes" |
| 5 | P21 | 4/0 | This set contained 2,234 approaches over 31 methods, 14 strategies, 3 imputation | minimal: "three imputations" |
| 6 | P36 | 5/1 | The 15 clustermap-selected approaches had a higher batch PCReg than the remainin | routed MAD to Supplementary File 1, sheet Paired_tests; "15" dropped (set defined in P24) |
| 7 | P36 | 4/1 | Their biology PCReg did not differ from that of the remaining approaches, with a | routed MAD to Paired_tests (pointer sentence added) |
| 8 | P38 | 7/1 | Individual methods behaved in divergent and counterintuitive manner. 33_amdbnorm | split (three sentences; openings reworded so the splitter separates them) |
| 9 | P38 | 6/1 | Their biology PCReg spanned 0.357 to 0.823 over these strategies. 14_qsmooth was | split + routed MAD to Paired_tests |
| 10 | P38 | 4/1 | Among strategies, malignant-only, FFPE-only and no-removal were weakest on biolo | split (medians / test) |
| 11 | P39 | 5/0 | Eight further methods and the clustermap best group concentrated 26.2 to 43.3% o | split |
| 12 | P40 | 7/2 | Taking the local inverse Simpson’s index as a main local metric, 10_mnn led on b | both: split + MADs routed to Paired_tests |
| 13 | P42 | 4/1 | The clustermap group had a lower within-batch D than the remaining approaches, w | routed MAD to Paired_tests |
| 14 | P42 | 4/1 | The RNA-seq-only strategy lay at the lower left of the plane, with a within-batc | routed MAD to Paired_tests |
| 15 | P42 | 4/1 | Its between-batch median was 0.332 (MAD 0.052) against 0.628 (p = 2.0 × 10⁻⁴³). | routed MAD to Paired_tests (one pointer sentence for the three MADs) |
| 16 | P43 | 8/0 | Missing values and normalized gene expression scale separated the methods differ | split (four sentences) |
| 17 | P43 | 12/0 | At gene level the same 18 lost no genes, 10 lost 0.004 to 2.41% of genes, 15_fsq | split (six sentences) |
| 18 | P43 | 5/0 | Across the 15 clustermap best approaches the median expression varied from 2.63 | split (median / maximum) |
| 19 | P48 | 4/1 | Over all 2,234 approaches the same share was 97.0%, and the saturated approaches | minimal: "all approaches" (the 2,234 is the analysis set) |
| 20 | P49 | 4/0 | The four MNN approaches of the group lay at the boundary (0.781 to 0.957), about | split |
| 21 | P49 | 4/2 | Such behavior can be explained by the definition of DSC as between-group scatter | split (the tSNE sentence given a capital opening; the 11_harmony test in its own sentence) |
| 22 | P49 | 6/2 | The Affymetrix-only and FFPE-only strategies were worst, with means of 0.165 and | split (fused pair; opening reworded) |
| 23 | P50 | 5/1 | Strict exclusion scored below KNN imputation in the same matched comparison, by | split (matched test / means) |
| 24 | P50 | 10/1 | Post-removal raised the mean batch PCReg for 30 of the 31 methods, and over matc | split (five sentences) |
| 25 | P53 | 5/1 | The decay trajectory of the RNA_BATCH R² for the RNA-seq-only strategy and the b | split (fused pair; "Of the 14 … strategies, 10 …") |
| 26 | P56 | 6/0 | On the second component the batch R² was 15.2%, 65.9% and 67.1%, respectively, s | split (batch R² / total variance); the writer's NOTE resolved |
| 27 | P58 | 5/3 | By ranks, 14 methods exceeded the baseline and 3 fell below it (two-sided Mann-W | split (three sentences, one test each) |
| 28 | P59 | 4/1 | The malignant-only and FFPE-only strategies retained four malignant groups and r | split (three sentences) |
| 29 | P59+1 | 2/2 | The clustermap best approaches occupied local peaks of batch LISI (Supplementary | split (one test per sentence) |
| 30 | P62 | 4/0 | Only ten methods brought the mean below 0.7, ranging from 0.173 for 28_npn to 0. | split |
| 31 | P62 | 3/2 | The batch and biology distance ratios were nearly unrelated (Spearman ρ = −0.074 | split (correlation / Kruskal–Wallis) |
| 32 | P62+1 | 5/2 | On the biology column it did not differ from them (0.290 against 0.306, p = 0.08 | split (three sentences) |
| 33 | P65 | 4/1 | The tail contained 9 of the 15 clustermap selections, against 6.4% of the remain | minimal: "nine of the 15" |
| 34 | P70 | 6/0 | Class L therefore favored output that is unchanged or close to unchanged: of its | split (fused pair; census reworded with counts in words) |
| 35 | P71 | 4/1 | The median within-cohort marker correlation of those two methods was −0.001 and | split |
| 36 | P72 | 8/2 | The FFPE-only strategy passed least often, in 76 of its 164 approaches against 7 | split (four sentences) |
| 37 | P73 | 4/1 | They did separate the median margin (p = 4.4 × 10⁻⁵), which was 0.051 under soft | split |
| 38 | P74 | 4/1 | They concentrated in the FFPE-only strategy, with 21 approaches, which is 13.3% | split |
| 39 | P74 | 4/2 | The microarray-only strategy followed with 11 (p = 2.6 × 10⁻³), whereas the 7 of | split (one test per sentence) |
| 40 | P74 | 10/2 | Imputations did not differ in their share (24, 21 and 16 approaches under KNN im | split (six sentences; Paired_tests and Agreement_specific_61 pointers kept) |
| 41 | P76 | 4/1 | Across its 84 approaches its median marker correlation was 0.840, below the 0.96 | split |
| 42 | P76 | 4/1 | Its median margin was 0.005 against 0.043 (p = 7.8 × 10⁻²⁷), and none of its app | split |
| 43 | P79 | 4/1 | Single-class folds reached a median macro F1 of 0.903, against 0.733 for the 17, | split (fold count in its own sentence) |
| 44 | P80 | 4/0 | Of these, 20,343 come from the 17 non-canonical Shambhala parameter variants, an | split |
| 45 | P83 | 4/0 | Its per-batch detail shows where the two cuts come from ([FIG:fig_prediction_n]B | split |
| 46 | P127 | 4/1 | Across the analysis set, the 277 approaches of the ComBat family reached a media | split |
| 47 | P127 | 4/1 | Methods differed on the full cut (Kruskal–Wallis H = 1,425, p = 4.3 × 10⁻²⁸¹), f | split (test / range of medians) |
| 48 | P128 | 4/1 | The elected set spread over 13 of the 14 strategies and included no FFPE-only ap | split |
| 49 | P128 | 4/1 | Its imputation mix, 50 approaches with strict exclusion, 33 with softimpute and | split (test / counts) |
| 50 | P128+1 | 5/1 | Shambhala-2 (20_shambhala) sat above the other approaches on the full cut (media | split (test / medians; "Shambhala-2" counts as a value for the checker) |
| 51 | P132 | 6/0 | For two sets of 112 drawn at random from 2,234 approaches the expected overlap i | split |
| 52 | P132 | 4/1 | Among the four component classes, the local and distributional classes agreed mo | split (remaining pairs point to Table 3) |
| 53 | P132+1 | 4/0 | Each class set holds the top 5% of the 2,234 approaches by its class score (112 | split (Table 3 caption) |
| 54 | P132+1 | 6/1 | The chance expectation of a shared count is 5.6 for two sets of 112 and 0.75 for | split (Table 3 caption; "Arrows:" opens the key so the splitter separates it) |
| 55 | P134 | 4/1 | They shared 9 approaches with the local class (Jaccard 0.076, p = 5.7 × 10⁻⁹), m | minimal: "nine approaches" |
| 56 | P134 | 4/2 | Nor did the clustermap group differ from the other approaches on prediction: its | split (one test per sentence; src comments moved) |
| 57 | P135 | 5/0 | The local, distributional, structural and composite sets each spread over 20 to | split (fused pair; openings reworded) |
| 58 | P136 | 4/1 | The global class would recommend 03_limma and 13_fsmvn. 13_fsmvn reached a media | split (fused pair; "Of the two, 13_fsmvn …"; 03_limma rank in its own sentence) |
| 59 | P136 | 4/1 | Class M, read without the margin, would recommend 10_mnn and 12_scanorama, whose | split |
| 60 | P143 | 4/0 | The leading one by full-cut F1 is no removal with softimpute under 29_combat_ref | split (multiclass-only mean in its own sentence; Table 2 holds all values) |
| 61 | P144 | 9/0 | The ordering of the overlaps did not depend on it: the local and composite sets | both: split into four sentences + the 36 pairs pointed at Supplementary File 2, sheet Threshold_sensitivity |
| 62 | P146 | 5/0 | [TO CONFIRM: that Zenodo record 22737294 is published before submission; it was | minimal: date written "14 September 2026"; "Supplementary File 1 and Supplementary File 2" |
| 63 | P159+8 | 6/0 | Canonical_set_reconciliation: the reconciliation from the 2,407 completed approa | split (three sentences; [38] verbatim) |
| 64 | P159+9 | 5/0 | Threshold_sensitivity: the overlap of every pair of elected sets when the electi | split |

## Other fixes

| Where | Fix |
|---|---|
| `08_legends.md`, `[FIG:fig_markers_lm]` E, `[FIG:fig_prediction_n]`, `[FIG:sfig_harshness]` | "grey" → "gray" (3) |
| `03a` P27 (`[keep]` → `[edit]`) | cites `[FIG:sfig_marker_qc]A` (coverage) and `[FIG:sfig_marker_qc]C` (per-gene ρ by signature) |
| `03a` P72 | cites `[FIG:fig_markers_lm]F` with one qualitative sentence (no number) |
| `03a` P66+1 (Table 1) | five "—" fold-cut cells → "n/a" |

## Final gate results

```
python tools/assemble_draft_260925.py        -> Problems: none; Notes: none
python tools/check_principles.py MS.md       -> decimals 0, spelling 0, citations 0, antithesis 0,
                                                scatter 0, panels 0, density 0, tables 0, markers 0;
                                                order 1 (report-only until Phase 5); OK
python tools/audit_numbers.py MS.md ...      -> 657 distinct numbers, 657 sourced, 0 UNSOURCED; OK
```

For information only (not part of this pass): `tools/check_style.py` still fails, on problems
this pass did not create. These are the section word budgets (the results section is 12,836 words), two
"robust", one "highlight", one "significantly" in Daniil's P49 wording, and one em-dash. The
em-dash is the "—" in the assembler's own header line (line 1 of the assembled file).
