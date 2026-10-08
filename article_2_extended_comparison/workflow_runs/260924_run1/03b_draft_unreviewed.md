# 03b — Draft of the unreviewed range (P78–P177), writer-unreviewed, 2026-09-25

## Status

- **Range:** P78–P129, P131–P137, P139–P148, P161–P177. P130, P138 and P149–P160 belong to the
  legend-writer and are omitted here.
- **Sections done:** all four sections of the range (P78–P129, P131–P137, P139–P148, P161–P177).
- **Sections left:** none.
- **Main-text tables inserted:** Table 2 (after P83), Table 4 (after P129), Table 3 (after P132).
- **Open stat requests:** see `10_stat_requests_unreviewed.json`.
- **Citations in range:** no `⟦CIT:…⟧` token occurs in P78–P177 outside the legend-writer's
  paragraphs. `[52]` (P82) and `[38]` (P146) are carried verbatim.

---

## Results — Cross-batch prediction (P78–P129)

### P78 [edit]
Cross-batch prediction elects a third set of approaches, led by the ComBat family on both cuts of the fold population
<!-- why: heading made specific (A1); "stable" dropped because the two cuts correlate at 0.810 and reorder the leading group (P81); "elects" kept for the elected-set concept (D9) -->

### P79 [edit]
We then evaluated class N, which asks whether a classifier fitted on the batches that are present can label the samples of a batch it has never seen. Over the 2,234 approaches, leave-one-batch-out (LOBO) prediction of the three-class target produced 32,746 held-out folds over 24 RNA batches. <!-- src: 01_numbers fold_composition n_3class_folds; A2_T8 holds 24 batch labels plus the __ALL__ summary row --> Of these folds, 15,436 (47.1%) contained a single biological class. <!-- src: A2_T8 n_classes == 1; 01_numbers pct_singleclass --> The other 17,310 folds carried two or three classes. Single-class folds reached a median macro F1 of 0.903, against 0.733 for these multiclass folds (Mann–Whitney U, p = 2.3 × 10⁻²²¹; [FIG:fig_prediction_n]C). <!-- src: A2_T10 T10-090 --> Among the multiclass folds, two-class folds were harder than three-class folds (median 0.629 against 0.804, Mann–Whitney U, p < 10⁻³⁰⁰; [FIG:fig_prediction_n]C). <!-- src: A2_T10 T10-091 (p underflows to 0) -->
<!-- why: D1 opening; C4/C10 single-class finding moved here from the Abstract with its test (A2); 0.7334 -> 0.733 (D5); LOBO defined at first use in this section (D6); Figure 5C -> token -->

### P79+1 [insert]
We then examined why a held-out batch with a single class scores higher. With one class present, the macro F1 of the fold reduces to the F1 of that class, so the fold tests whether the classifier assigns the diagnosis of the whole held-out cohort and does not test whether it separates diagnoses. The two fold types had close means (0.690 against 0.679) although their medians differed, which places the difference in the shape of the distribution. <!-- src: A2_T10 T10-090 mean_a, mean_b --> Single-class batches split into those labeled correctly in the median fold, such as several FF microarray batches at 1.000, and those that failed, such as the FFPE batches GPL887_FFPE_Unknown at 0.000 and GPL13938_FFPE_Unknown at 0.069 (Supplementary File 2, sheet Fold_composition). <!-- src: A2_T8 n_classes == 1, median_f1 per batch --> A mean over all folds therefore mixes the assignment of whole cohorts with the separation of diagnoses measured on the multiclass folds. For this reason we report every class N value on two cuts: the full cut, the mean over all held-out folds, and the multiclass-only cut, the mean over the folds that carry at least two classes.
<!-- why: C4/C10 "discuss there, it's a technical finding"; D3 mechanism after the number; A5 not needed (no dispersion quoted) -->

### P80 [edit]
Before counting the folds, we restricted the fold population to the approaches under analysis. The per-fold table holds 53,737 three-class folds, and 20,991 of them belong to approaches outside the analysis set. <!-- src: 01_numbers discrepancies §1 --> Of these, 20,343 come from the 17 non-canonical Shambhala parameter variants. The other 648 come from 34_arsyn and 38_harman, the two methods whose approaches all fail the 5% all-missing criterion. <!-- src: 01_numbers discrepancies §1 --> The canonical Shambhala-2 variant, 20_shambhala, is retained and contributes 1,200 of the 32,746 folds. <!-- src: 01_numbers discrepancies §1 -->
<!-- why: D1 opening; the superseded "An earlier count over the unrestricted table…" sentence and the conclusion sentence that compared the two counts removed (C47 spirit, C4) -- the discrepancy is recorded in 01_numbers §discrepancies 1-2; rule 15 split -->

### P81 [edit]
We then compared the two cuts across approaches. The full-cut and the multiclass-only means correlated with Spearman ρ = 0.810 over the 2,174 approaches carrying both (p < 10⁻³⁰⁰). <!-- src: A2_T11 T11-027 --> Over the 2,058 approaches with at least three multiclass folds the correlation was ρ = 0.815 (p < 10⁻³⁰⁰). <!-- src: A2_T11 T11-M01 --> This agreement is high enough for both cuts to place the same method, 29_combat_ref, first ([FIG:fig_prediction_n]A) and leaves room for the order inside the leading group to change, so both cuts are reported for every approach and group below (Table 2).
<!-- why: D1; A3 (ρ and p); superseded "an earlier value of 0.812…" removed (C4); the first-ranked method on both cuts named (A1; A2_T10 T10-093 and T10-094 top_group) -->

### P82 [edit]
We next identified the fold structures under which a high value carries no information on class separation. All 59 approaches without a multiclass fold belong to the Affymetrix-only strategy with post-removal, and 20 of them report a full-cut F1 of at least 0.999; their values rest on single-class folds alone ([FIG:fig_prediction_n]C, D). <!-- src: 01_numbers prediction n_zero_multiclass_folds; A2_T1 n_mc == 0 -> strat, post_rm; A2_T1 n_mc == 0 and pv_lobo3_f1_macro_mean >= 0.999 (evidence entry requested, SR-U05) --> The strategy that retains the known-bad batches gives the highest full-cut and multiclass-only values among all approaches with a multiclass fold. <!-- src: A2_T1 max pv_lobo3_f1_macro_mean and max f1_mc_mean over n_mc >= 1 are both A_confirmed_bad / strict / 29_combat_ref (SR-U05) --> Under this strategy, strict exclusion with 29_combat_ref and post-removal (A_confirmed_bad / strict / 29_combat_ref / post1) reaches a full-cut F1 of 0.958 and a multiclass-only mean of 0.924 over 11 multiclass folds (Table 2). <!-- src: A2_T13 row "batch-confounded" --> If a retained bad batch is also diagnosis-pure, held-out prediction measures the confounding between batch and diagnosis, so we report this approach and do not recommend it. Protecting the biological covariate during correction does not remove the problem: when groups are unevenly distributed across batches, the corrected data are not batch-effect free and the estimation errors are deflated [52].
<!-- why: D1; the 20 approaches now at ">= 0.999" (15 are 0.999 and 5 are 1.000 at three decimals, A2_T1); "highest prediction values anywhere" made precise (the degenerate approaches reach 1.000); worst fold, AUC and marker values moved to Table 2 (rule 15); [52] verbatim -->

### P83 [edit]
We then defined the eligible set by excluding the two bad-batch-retaining strategies, A_confirmed_bad and B_extended_bad, and the approaches with fewer than five multiclass folds, which left 1,527 approaches. <!-- src: 01_numbers prediction n_eligible_non_degenerate --> Table 2 gives the named groups as medians and the leading approaches individually, with the F1 of both targets on both fold cuts and the AUC of both targets. The best eligible approach of each of the four leading strategies used 29_combat_ref, except under the microarray-only strategy, where 08_inmoose_combatseq led (Table 2). The leading approach, no removal with softimpute under 29_combat_ref without post-removal (S0_no_removal / softimpute / 29_combat_ref / post0), reached a full-cut F1 of 0.946 and a multiclass-only mean of 0.887 over 11 multiclass folds. <!-- src: A2_T13 --> Its per-batch detail shows where the two cuts come from ([FIG:fig_prediction_n]B). Of its 24 folds, 13 are single-class. These single-class folds score between 0.986 and 1.000. <!-- src: A2_T5 run_id == S0_no_removal__softimpute__29_combat_ref__post0, target == 3class --> Its hardest multiclass fold was GPL96_FFPE_Unknown, an FFPE microarray batch of 84 samples and two classes (F1 0.462, AUC 0.543). <!-- src: A2_T5; 01_numbers per_batch_example --> The next two were the RNA-seq batches RNASeq_FFPE_PolyA (F1 0.698) and RNASeq_FF_PolyA (F1 0.718; Supplementary File 2, sheet Per_batch_folds). <!-- src: A2_T5; 01_numbers per_batch_example --> Two of the three hardest folds are therefore FFPE batches, presumably because degraded FFPE material shifts expression profiles away from those of the training batches.
<!-- why: D1; A1 (strategies and approach named); the I_rare_batches_removed leader is now its post0 approach at 0.932 (evidence report, Table 1 row); the superseded "An earlier reading of the same approach…" sentence removed (C4); two-class AUC and marker correlation moved to Table 2; rule 15 splits; Figure 5B -> token; D3 mechanism hedged with "presumably" -->

### P83+1 [insert]
**Table 2. Leave-one-batch-out prediction for the named groups and the leading approaches, on both fold cuts and for both targets.** LOBO3, the three-class target (DLBCL, FL and normal B cells); LOBO2, the two-class target (FL against DLBCL). Full cut, the mean macro F1 over all held-out folds; multiclass-only, the mean over the held-out folds that carry at least two classes. The AUC is undefined on a single-class fold and is therefore a mean over the multiclass folds only. The worst multiclass fold is the lowest three-class macro F1 over an approach's multiclass folds. Marker correlation, the class L mean within-cohort marker correlation before and after harmonization. Generalizability index, the E1 index of Table 4. Group rows give medians over the approaches of the group; approach rows are named strategy / imputation / method / post-removal (post0 without, post1 with post-removal). Eligible approaches exclude the two strategies that retain known-bad batches (A_confirmed_bad, B_extended_bad) and approaches with fewer than five multiclass folds. The best eligible approach is given for the four strategies with the highest full-cut LOBO3 F1. The batch-confounded approach is listed separately and is not recommended. The 20_shambhala group has 84 approaches, of which 83 carry the full-cut LOBO3 F1 and 82 the multiclass-only mean. Source: Supplementary File 2, sheet LOBO_summary.
<!-- src: A2_T13_lobo_summary_260924.csv, every cell; 20_shambhala counts from base P128 and A2_T10 T10-105 (n_a = 83), T10-106 (n_a = 82) -->

| Group or approach | n | LOBO3 F1, full cut | LOBO3 F1, multiclass-only | LOBO3 AUC | LOBO2 F1, full cut | LOBO2 F1, multiclass-only | LOBO2 AUC | Worst multiclass fold | Multiclass folds | Marker correlation | Generalizability index |
|---|---|---|---|---|---|---|---|---|---|---|---|
| All approaches | 2,234 | 0.709 | 0.675 | 0.888 | 0.706 | 0.742 | 0.904 | 0.332 | 9 | 0.944 | 0.475 |
| Eligible approaches | 1,527 | 0.720 | 0.690 | 0.892 | 0.702 | 0.753 | 0.905 | 0.328 | 9 | 0.938 | 0.475 |
| Clustermap-selected | 15 | 0.629 | 0.690 | 0.878 | 0.655 | 0.737 | 0.913 | 0.410 | 5 | 0.778 | 0.466 |
| Class N elected set | 112 | 0.898 | 0.817 | 0.939 | 0.891 | 0.840 | 0.938 | 0.529 | 10 | 0.907 | 0.814 |
| Class L elected set | 112 | 0.759 | 0.710 | 0.884 | 0.762 | 0.764 | 0.930 | 0.427 | 9 | 1.000 | 0.718 |
| Class M elected set | 112 | 0.682 | 0.696 | 0.893 | 0.694 | 0.726 | 0.912 | 0.346 | 10 | −0.006 | 0.350 |
| ComBat family (05_combat, 06_combat_seq, 08_inmoose_combatseq, 29_combat_ref) | 277 | 0.873 | 0.771 | 0.920 | 0.836 | 0.809 | 0.932 | 0.462 | 9 | 0.868 | 0.737 |
| 20_shambhala (Shambhala-2) | 84 | 0.745 | 0.700 | 0.895 | 0.761 | 0.744 | 0.918 | 0.429 | 9 | 0.840 | 0.441 |
| S0_no_removal / softimpute / 29_combat_ref / post0 (best eligible, no removal) | 1 | 0.946 | 0.887 | 0.943 | 0.921 | 0.860 | 0.932 | 0.462 | 11 | 0.880 | 0.826 |
| F_microarray_only / strict / 08_inmoose_combatseq / post0 (best eligible, microarray-only) | 1 | 0.945 | 0.838 | 0.930 | 0.935 | 0.832 | 0.927 | 0.592 | 6 | 0.829 | 0.844 |
| J_ff_only / softimpute / 29_combat_ref / post0 (best eligible, FF-only) | 1 | 0.935 | 0.863 | 0.984 | 0.930 | 0.881 | 0.912 | 0.639 | 7 | 0.944 | 0.886 |
| I_rare_batches_removed / softimpute / 29_combat_ref / post0 (best eligible, rare batches removed) | 1 | 0.932 | 0.889 | 0.934 | 0.915 | 0.877 | 0.932 | 0.541 | 9 | 0.884 | 0.858 |
| S0_no_removal / strict / 29_combat_ref / post1 (index leader among eligible) | 1 | 0.934 | 0.866 | 0.980 | 0.936 | 0.894 | 0.980 | 0.541 | 11 | 0.953 | 0.886 |
| A_confirmed_bad / strict / 29_combat_ref / post1 (batch-confounded, not recommended) | 1 | 0.958 | 0.924 | 0.993 | 0.954 | 0.931 | 0.998 | 0.643 | 11 | 0.957 | 0.900 |

### P84 [delete]
<!-- why: old "Table 1" caption; replaced by Table 2 (P83+1), rebuilt from A2_T13 (C47, brief) -->

### P85 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P86 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P87 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P88 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P89 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P90 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P91 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P92 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P93 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P94 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P95 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P96 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P97 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P98 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P99 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P100 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P101 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P102 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P103 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P104 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P105 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P106 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P107 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P108 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P109 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P110 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P111 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P112 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P113 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P114 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P115 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P116 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P117 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P118 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P119 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P120 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P121 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P122 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P123 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P124 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P125 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 -->

### P126 [delete]
<!-- why: old Table 1 cell; replaced by Table 2 (the old I_rare_batches_removed row quoted its post1 approach at 0.928; the strategy's best eligible approach is post0 at 0.932) -->

### P127 [edit]
We then examined the elected set of class N, its 112 highest-scoring approaches. Class N resulted in the ComBat family: four implementations of that algorithm, 05_combat, 29_combat_ref, 06_combat_seq and 08_inmoose_combatseq, took 84 of the 112 places, and eight further methods shared the rest (Supplementary File 1, sheet Method_census_by_class). <!-- src: A2_T4 metric_class == N --> Across the analysis set, the ComBat family holds 277 approaches. They reached a median full-cut F1 of 0.873 against 0.669 for the other methods (Mann–Whitney U, p = 2.9 × 10⁻¹⁰⁵). <!-- src: A2_T10 T10-092-1 --> The difference held on the multiclass-only cut (0.771 against 0.665, Mann–Whitney U, p = 1.0 × 10⁻⁴⁴). <!-- src: A2_T10 T10-092-2 --> Methods differed on the full cut (Kruskal–Wallis H = 1,425, p = 4.3 × 10⁻²⁸¹; [FIG:fig_prediction_n]A). Their medians ran from 0.898 for 29_combat_ref to 0.453 for 02_median_scaling. <!-- src: A2_T10 T10-093 --> The same two methods were first and last on the multiclass-only cut (0.827 against 0.571, Kruskal–Wallis p = 3.2 × 10⁻¹⁶⁹). <!-- src: A2_T10 T10-094 --> The five last methods on the full cut, 02_median_scaling, 03_limma, 07_pycombat, 21_harmonizr and 28_npn, include four of the six methods that drive batch PCReg to saturation ([FIG:fig_prediction_n]A), consistent with the removal of diagnosis-associated variance together with the batch-associated one. <!-- src: fig_prediction_n panel A order; 01_numbers saturation_and_scale methods_at_saturation --> 07_pycombat, a Python implementation of ComBat, is one of these four and received no place in the class N elected set (Supplementary File 1, sheet Method_census_by_class). <!-- src: A2_T4 metric_class == N has no 07_pycombat row -->
<!-- why: D1; D9 ("resulted in"); A2 (MW for the family, KW across methods); the per-method four-number lists moved to the figure panel (rule 15, C3); D3 mechanism hedged ("consistent with") -->

### P127+1 [insert]
Two fold structures described above carry into the class N elected set. Twenty of its approaches use a bad-batch-retaining strategy, 15 of them A_confirmed_bad, which is more than that strategy's share of the analysis set (Fisher exact test, p = 0.024). <!-- src: A2_T1 is_prediction_best by strat; A2_T10 T10-104 --> Five further elected approaches have fewer than five multiclass folds, and three of these have none. <!-- src: A2_T1 is_prediction_best and n_mc (SR-U05) --> In total, 25 of the 112 elected places rest on these fold structures. <!-- src: A2_T1 is_prediction_best and (strat in A/B or n_mc < 5) (SR-U05) -->
<!-- why: split from the old P127 "Two limitations travel with that election" (rule 15); the old "5 have no multiclass fold" was wrong: 5 have fewer than five and 3 have none (A2_T1); A4 baseline via the Fisher test -->

### P128 [edit]
The elected set spread over 13 of the 14 strategies. It included no FFPE-only approach, although that strategy holds 164 approaches of the analysis set (Fisher exact test, p = 2.7 × 10⁻⁴). <!-- src: A2_T1 is_prediction_best by strat; A2_T10 T10-103 --> Its imputation mix departed weakly from that of the analysis set (χ² goodness-of-fit test, p = 0.042). It held 50 approaches with strict exclusion, 33 with softimpute and 29 with KNN imputation. <!-- src: A2_T1 is_prediction_best by imp; A2_T10 T10-101 --> Its 63 approaches with post-removal did not differ from the half expected from the analysis set (two-sided binomial test, p = 0.22). <!-- src: A2_T10 T10-102 -->
<!-- why: D1 carried by P127; A2 tests for every composition claim; A4 baselines (FFPE-only 164 of 2,234; imputation and post-removal shares); "k-nearest-neighbour" -> KNN (C32); the old "favours" claim for post-removal is not supported (p = 0.22, evidence report) and is now stated as no difference; strategy counts beyond the three named moved to Supplementary File 2, sheet Elected_sets_by_class -->

### P128+1 [insert]
We then compared the pipeline factors on both cuts across all approaches (Supplementary File 1, sheet Paired_tests). Strategies separated the full-cut F1 (Kruskal–Wallis p = 1.5 × 10⁻¹⁷), with group medians from 0.763 for Affymetrix-extended to 0.561 for FFPE-only. <!-- src: A2_T10 T10-095 --> Imputations separated it less (Kruskal–Wallis p = 1.7 × 10⁻⁴), with group medians spanning 0.012. <!-- src: A2_T10 T10-097 range_of_group_medians 0.0125 --> The effect sizes order the three factors: ε² was 0.634 across methods, 0.044 across strategies and 0.007 across imputations. <!-- src: A2_T10 T10-093, T10-095, T10-097 effect_size --> On the multiclass-only cut, strategy medians ran from 0.724 for microarray-only to 0.462 for Affymetrix-only (Kruskal–Wallis p = 3.7 × 10⁻⁸⁰). <!-- src: A2_T10 T10-096 --> The Affymetrix-only median rests on the 95 of its 154 approaches that carry a multiclass fold at all. <!-- src: A2_T1 strat == G_affymetrix_only, n_mc > 0 (SR-U05) --> Imputation medians spanned 0.050 on that cut, from strict exclusion down to KNN imputation (Kruskal–Wallis p = 1.2 × 10⁻¹⁴). <!-- src: A2_T10 T10-098 --> Post-removal raised the full-cut median from 0.692 to 0.719 (Mann–Whitney U, p = 2.9 × 10⁻³). <!-- src: A2_T10 T10-099 --> It did not change the multiclass-only median (0.669 against 0.681, Mann–Whitney U, p = 0.13), which places its gain in the single-class folds. <!-- src: A2_T10 T10-100 --> Shambhala-2 (20_shambhala) sat above the other approaches on the full cut (Mann–Whitney U, p = 0.012). Its median over 83 approaches was 0.745, against 0.707 for the other approaches. <!-- src: A2_T10 T10-105 --> It did not differ from them on the multiclass-only cut (0.700 against 0.674, Mann–Whitney U, p = 0.10; Table 2). <!-- src: A2_T10 T10-106 -->
<!-- why: split from old P128 (rule 15); every factor comparison now carries its test (A2); ε² used as the comparator for "separate more" (A6); the post-removal claim on the multiclass cut corrected to not significant (evidence report); Shambhala-2 "in the middle" corrected: it is above the rest on the full cut (p = 0.012) and not different on the multiclass-only cut; imputation range 0.013 -> 0.012 at three decimals (A2_T10 T10-097 0.0125); per-strategy and per-imputation median lists moved to Supplementary File 1 (rule 15) -->

### P128+2 [insert]
We controlled every class N value with 100 permutations of the biological labels. <!-- src: A2_T1 pv_n_perm == 100 for 2,233 approaches --> Under permutation, the full-cut three-class macro F1 fell to tier medians between 0.237 and 0.261, against an observed median of 0.709 over all approaches ([FIG:sfig_harshness]G). <!-- src: A2_T9b pv_lobo3_f1_macro_perm_mean median_low/medium/high; A2_T13 all approaches --> The permuted two-class F1 fell to tier medians between 0.393 and 0.441 ([FIG:sfig_harshness]J). <!-- src: A2_T9b pv_lobo2_f1_macro_perm_mean --> The permuted AUC stayed at 0.500 for both targets in every tier, the value expected from a classifier without information ([FIG:sfig_harshness]I, L). <!-- src: A2_T9b pv_lobo3_auc_macro_perm_mean, pv_lobo2_auc_macro_perm_mean --> The observed full-cut three-class F1 exceeded its permutation distribution at p ≤ 0.05 in 2,197 of the 2,233 approaches carrying the column. <!-- src: A2_T1 pv_lobo3_f1_perm_pvalue <= 0.05 (SR-U05) --> The median permutation p was 0.0099 in each tier, the smallest value that 100 permutations can give. <!-- src: A2_T9b pv_lobo3_f1_perm_pvalue median_low/medium/high = 0.00990 --> The differences between methods in class N are therefore differences between classifiers that almost all predict above chance.
<!-- why: E3 / plan §1g "the permutation null reported"; each panel of sfig_harshness that carries the null (G, I, J, L) cited (B2); numbers per sentence <= 3 (rule 15) -->

### P129 [edit]
We then combined six prediction and preservation columns into the generalizability index, the mean of six rank percentiles: the full-cut and multiclass-only three-class macro F1, the full-cut two-class macro F1, the class L marker correlation, the class M margin gain over the unharmonized baseline and the worst multiclass fold. Over the whole analysis set, the 15 highest index values, from 0.949 to 0.986, all belong to Affymetrix-only approaches with post-removal and no multiclass fold. <!-- src: 12_index_rank_churn.md summary --> A missing column leaves the mean over the columns that remain, and the prediction columns of these approaches rest on single-class folds alone ([FIG:fig_prediction_n]D). Restricted to the 1,527 eligible approaches, the index is led by no removal with strict exclusion under 29_combat_ref with post-removal (S0_no_removal / strict / 29_combat_ref / post1) at 0.886 (Table 4). <!-- src: A2_T2b row 1 --> All 15 leading eligible approaches are ComBat implementations, nine under 29_combat_ref and six under 05_combat, and nine of the 15 use the FF-only strategy (Table 4). <!-- src: A2_T2b method, strat counts; 12_index_rank_churn.md --> The index followed the full-cut three-class F1 closely (Spearman ρ = 0.829, p < 10⁻³⁰⁰, n = 2,233; [FIG:fig_prediction_n]D). <!-- src: A2_T11 T11-026 --> The 15 clustermap-selected approaches ranked between 433rd and 2,022nd of 2,234 on the index. <!-- src: 01_numbers gate_and_rank_counts clustermap_index_rank_range --> Their median index did not differ from that of the other approaches (0.466 against 0.476, Mann–Whitney U, p = 0.95). <!-- src: A2_T10 T10-107 -->
<!-- why: E1/C16 (index now uses the two-class F1; values 0.8875 -> 0.886, 0.933-0.982 -> 0.949-0.986, 323-2,038 -> 433-2,022 per 12_index_rank_churn); D1; the leader's component values moved to Table 4 (rule 15); A3 ρ and p for panel D; A2 test for the clustermap group -->

### P129+1 [insert]
**Table 4. The 15 eligible approaches with the highest generalizability index and its six components.** The index is the mean of six rank percentiles over the 2,234 approaches: the full-cut and multiclass-only three-class (LOBO3) macro F1, the full-cut two-class (LOBO2) macro F1, the class L mean within-cohort marker correlation, the class M margin gain over the unharmonized baseline at the same strategy and imputation, and the worst multiclass fold (the lowest three-class macro F1 over the approach's multiclass folds). The table gives the raw value of each component. Eligible approaches exclude the two strategies that retain known-bad batches and approaches with fewer than five multiclass folds (n = 1,527). Ranks are among the eligible approaches. The full ranking of all 2,234 approaches is in Supplementary File 1, sheet Generalizability_ranking.
<!-- src: A2_T2b_generalizability_top_eligible_260924.csv, every cell -->

| Rank | Strategy | Imputation | Method | Post-removal | Index | LOBO3 F1, full cut | LOBO3 F1, multiclass-only | LOBO2 F1, full cut | Marker correlation | Margin gain over baseline | Worst multiclass fold | Multiclass folds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | S0_no_removal | strict | 29_combat_ref | yes | 0.886 | 0.934 | 0.866 | 0.936 | 0.953 | 0.076 | 0.541 | 11 |
| 2 | J_ff_only | softimpute | 29_combat_ref | no | 0.886 | 0.935 | 0.863 | 0.930 | 0.944 | 0.044 | 0.639 | 7 |
| 3 | J_ff_only | knn | 29_combat_ref | no | 0.885 | 0.932 | 0.856 | 0.929 | 0.944 | 0.045 | 0.637 | 7 |
| 4 | J_ff_only | strict | 29_combat_ref | no | 0.885 | 0.934 | 0.861 | 0.934 | 0.942 | 0.044 | 0.637 | 7 |
| 5 | E3_iterative_r3 | strict | 05_combat | no | 0.883 | 0.908 | 0.838 | 0.876 | 0.956 | 0.080 | 0.586 | 10 |
| 6 | J_ff_only | strict | 29_combat_ref | yes | 0.883 | 0.930 | 0.862 | 0.926 | 0.941 | 0.042 | 0.637 | 7 |
| 7 | J_ff_only | softimpute | 29_combat_ref | yes | 0.883 | 0.930 | 0.863 | 0.921 | 0.942 | 0.042 | 0.637 | 7 |
| 8 | E3_iterative_r3 | strict | 05_combat | yes | 0.882 | 0.903 | 0.837 | 0.880 | 0.955 | 0.080 | 0.586 | 10 |
| 9 | J_ff_only | knn | 29_combat_ref | yes | 0.882 | 0.931 | 0.865 | 0.921 | 0.942 | 0.042 | 0.636 | 7 |
| 10 | I_rare_batches_removed | strict | 29_combat_ref | no | 0.879 | 0.906 | 0.843 | 0.922 | 0.943 | 0.073 | 0.541 | 9 |
| 11 | J_ff_only | knn | 05_combat | no | 0.878 | 0.929 | 0.850 | 0.910 | 0.944 | 0.035 | 0.601 | 7 |
| 12 | J_ff_only | strict | 05_combat | no | 0.878 | 0.928 | 0.850 | 0.912 | 0.942 | 0.038 | 0.596 | 7 |
| 13 | J_ff_only | strict | 05_combat | yes | 0.876 | 0.924 | 0.851 | 0.904 | 0.941 | 0.035 | 0.596 | 7 |
| 14 | C_rnaseq_only | softimpute | 05_combat | no | 0.875 | 0.847 | 0.827 | 0.837 | 0.983 | 0.114 | 0.646 | 5 |
| 15 | I_rare_batches_removed | strict | 29_combat_ref | yes | 0.875 | 0.889 | 0.828 | 0.922 | 0.947 | 0.071 | 0.541 | 9 |

### P129+2 [insert]
Taken together, cross-batch prediction elected a set dominated by the ComBat family, and the leading approaches kept that composition on both fold cuts and under the generalizability index. Nearly half of the held-out batches carry a single diagnosis, so a mean over all folds mixes the assignment of whole cohorts with the separation of diagnoses, and strategies that retain batches confounded with diagnosis reach the highest values. A benchmark that uses held-out prediction should therefore report the multiclass-only cut and the multiclass fold count beside every full-cut value, exclude the strategies that retain confounded batches before ranking, and compare the observed values with a label-permutation null.
<!-- why: D2 closing paragraph stating the consequence for benchmarking practice; no new number -->

---

## Results — The sets elected by the individual metric classes (P131–P137)

### P131 [keep]

### P132 [edit]
We then ran the election once per class over the same 2,234 approaches, which gave eight sets of 112 approaches, and compared them with each other and with the 15 approaches of the published clustermap selection (Table 3; Supplementary File 2, sheet Cross_election_pairs). For two sets of 112 drawn at random from 2,234 approaches the expected overlap is 5.6 approaches. For a set of 112 against the 15 clustermap approaches it is 0.75. <!-- src: A2_T3b expected_intersection 5.615, 0.752 --> Every overlap below was tested against this expectation with a one-sided hypergeometric test in the direction observed. The largest agreement was between the local class and the composite, 71 shared approaches (Jaccard 0.464, p = 9.5 × 10⁻⁷⁵). <!-- src: A2_T3b local–composite --> The composite is the mean of the four component classes, and the local metrics spread the approaches most widely (Supplementary Figure 9C, 9D), which presumably lets the local class dominate its ranking. The composite also shared 51 approaches with the structural class, 50 with the distributional class and 20 with the global class (Table 3). <!-- src: A2_T3b --> Among the four component classes, the local and distributional classes agreed most, with 51 shared approaches (p = 4.9 × 10⁻⁴¹). The other five pairs shared between 8 and 18 approaches (Table 3). <!-- src: A2_T3b local–distributional; min global–local 8, max global–structural 18 --> Of the ten pairs formed by the four component classes and the composite, only the global and local classes did not agree above chance (8 shared against 5.6 expected, p = 0.20). <!-- src: A2_T3b p_more_than_chance; global–local 0.196 --> [FIG:fig_election]A draws all 36 pairwise overlaps of the nine sets as a chord diagram, with one arc per set and ribbon widths proportional to the shared approaches.
<!-- why: D1; every global and composite number replaced after the PCReg fix (15_pcreg_fix.md: local–composite 0.333/56 -> 0.464/71; global–local 15 -> 8; global–distributional 27 -> 14; global–structural 15 -> 18; global–composite 40 -> 20; distributional–composite 55 -> 50; structural–composite 51 unchanged); chance expectation and hypergeometric p added for every overlap claim (brief); Figure 5E -> [FIG:fig_election]A (B2); "No pair of metric classes agrees on even a third of its choices" deleted: local–composite now exceeds a third (0.464) and the sentence is an aphorism (D4); pair-by-pair numbers moved to Table 3 (rule 15) -->

### P132+1 [insert]
**Table 3. Overlap between the elected sets of the metric classes and the clustermap selection.** Each cell gives the Jaccard index of two sets and, in parentheses, the number of approaches they share; the diagonal gives the set size. Each class set holds the top 5% of the 2,234 approaches by its class score (112 approaches). The clustermap set holds the 15 approaches selected in the source benchmark. The chance expectation of a shared count is 5.6 for two sets of 112. It is 0.75 for a set of 112 against the 15 clustermap approaches. Arrows: ↑, more shared approaches than expected by chance; ↓, fewer than expected (one-sided hypergeometric test, p < 0.05, uncorrected). Global and composite values are computed with all seven PCReg columns assigned to the global class. Set sizes, intersections, unions, expectations and both one-sided p-values for all 36 pairs are in Supplementary File 2, sheet Cross_election_pairs; the elected approaches themselves are in Supplementary File 2, sheet Elected_sets_by_class.
<!-- src: A2_T3_cross_election_matrix_260924.csv (Jaccard) and A2_T3b_cross_election_pairs_260924.csv (n_intersection, expected_intersection, p_more_than_chance, p_less_than_chance) -->

| | Global | Local | Distributional | Structural | Composite | Class L | Class M | Class N | Clustermap |
|---|---|---|---|---|---|---|---|---|---|
| Global | (112) | 0.037 (8) | 0.067 (14)↑ | 0.087 (18)↑ | 0.098 (20)↑ | 0.004 (1)↓ | 0.000 (0)↓ | 0.000 (0)↓ | 0.000 (0) |
| Local | | (112) | 0.295 (51)↑ | 0.082 (17)↑ | 0.464 (71)↑ | 0.028 (6) | 0.057 (12)↑ | 0.014 (3) | 0.076 (9)↑ |
| Distributional | | | (112) | 0.057 (12)↑ | 0.287 (50)↑ | 0.032 (7) | 0.018 (4) | 0.014 (3) | 0.050 (6)↑ |
| Structural | | | | (112) | 0.295 (51)↑ | 0.018 (4) | 0.042 (9) | 0.047 (10) | 0.024 (3)↑ |
| Composite | | | | | (112) | 0.032 (7) | 0.028 (6) | 0.009 (2) | 0.058 (7)↑ |
| Class L | | | | | | (112) | 0.000 (0)↓ | 0.004 (1)↓ | 0.000 (0) |
| Class M | | | | | | | (112) | 0.000 (0)↓ | 0.024 (3)↑ |
| Class N | | | | | | | | (112) | 0.000 (0) |
| Clustermap | | | | | | | | | (15) |

### P133 [edit]
We then compared the three biology-facing classes with each other and with the remaining sets. Classes L and M shared no approach, and neither did classes M and N, against 5.6 expected by chance (hypergeometric p = 0.0027 for each pair). <!-- src: A2_T3b L–M, M–N p_less_than_chance --> Classes L and N shared a single approach, which is also fewer than expected (p = 0.020). <!-- src: A2_T3b L–N --> That approach is the unharmonized output of the rare-batches-removed strategy with softimpute and post-removal (I_rare_batches_removed / softimpute / 01_raw / post1; Supplementary File 2, sheet Elected_sets_by_class). <!-- src: Supplementary File 2 (260917) Elected_sets_by_class, L ∩ N; classes L and N are unaffected by the PCReg fix (15_pcreg_fix.md) --> Class N shared no approach with the global class (p = 0.0027). <!-- src: A2_T3b global–N --> It shared two approaches with the composite, which is not below chance (p = 0.071), and its largest overlap was 10 approaches with the structural class (Jaccard 0.047). <!-- src: A2_T3b composite–N p_less 0.071; structural–N --> Class M shared 12 approaches with the local class, more than chance (p = 0.0088). <!-- src: A2_T3b local–M --> Class L shared at most 7 approaches with any other class, and the only one of its overlaps that departed from chance was the single approach shared with the global class (p = 0.020 for fewer than expected). <!-- src: A2_T3b L rows; global–L p_less 0.0196 --> [FIG:fig_election]B shows the class N, class M and local sets as a Venn diagram: the local set meets class N at 3 approaches and class M at 12, and classes N and M do not meet. <!-- src: A2_T3b local–N 3, local–M 12, M–N 0 --> [FIG:fig_election]C adds class L and the global class in a supervenn plot, in which each column is one combination of set memberships and its width is the number of approaches that carry it.
<!-- why: D1; A1 (the one L ∩ N approach named); chance expectation and p for every overlap (brief); composite–N changed 0 -> 2 and is no longer "nothing" (15_pcreg_fix.md); the old "L reaches 9 with the composite" is now 7 (A2_T3b); "Class M ... 9 with the structural class" dropped as not different from chance (p = 0.10) -- it stays in Table 3; Figure 5F -> [FIG:fig_election]B, C (B2) -->

### P134 [edit]
We then compared the 15 clustermap-selected approaches with the eight elected sets. They shared nine approaches with the local class (Jaccard 0.076, p = 5.7 × 10⁻⁹), more than the 0.75 expected by chance. <!-- src: A2_T3b local–clustermap_best --> They also shared 7 approaches with the composite and 6 with the distributional class, both above chance (Table 3). <!-- src: A2_T3b composite–clustermap 7 (p = 3.1e-6), distributional–clustermap 6 (p = 4.8e-5) --> They shared 3 approaches each with the structural class and class M (p = 0.036 for each), and none with the global class, class L or class N. <!-- src: A2_T3b --> For a set of 15, sharing no approach with a random set of 112 has a probability of 0.46 (hypergeometric test), so the empty overlaps with classes L and N do not by themselves show disagreement. <!-- src: A2_T3b p_less_than_chance 0.461 for global, L, N against clustermap_best --> Nor did the clustermap group differ from the other approaches on prediction: its median full-cut F1 of 0.629 against 0.709 was not a significant difference (Mann–Whitney U, p = 0.97; Table 2). <!-- src: A2_T10 T10-110 (SR-U04) --> Neither was its generalizability index (p = 0.95). <!-- src: A2_T10 T10-107 --> <!-- src: A2_T13 clustermap_best and all approaches; A2_T10 T10-107 -->
<!-- why: D1; global and composite overlaps updated after the PCReg fix (global 4 -> 0, composite 4 -> 7); the old claim that the clustermap set "has no member in common with the set that cross-batch prediction elects" is kept as a count but no longer read as a finding, because zero is not below chance (p = 0.46, evidence report); the test for the clustermap group against the rest on full-cut F1 is not in A2_T10 -> SR-U04 -->

### P135 [edit]
We then counted the methods inside each elected set (Supplementary File 1, sheet Method_census_by_class). Four classes concentrated at least three quarters of their places in two to four methods, and each of the four names different methods. <!-- src: A2_T4: global 84/112, L 93/112, M 112/112, N 84/112 --> The global class gave 84 of its 112 places to 03_limma and 13_fsmvn, which took 42 each. <!-- src: A2_T4 metric_class == global --> Both are among the six methods that drive batch PCReg to saturation, so the global class elects saturated output. <!-- src: 01_numbers saturation_and_scale methods_at_saturation --> Class L gave 93 places to 01_raw and 36_explobatch, class M gave all 112 to 10_mnn and 12_scanorama, and class N gave 84 to the four ComBat implementations. <!-- src: A2_T4 metric_class in (L, M, N) --> The local, distributional, structural and composite sets each spread over 20 to 25 methods. <!-- src: A2_T4: local 24, distributional 22, structural 20, composite 25 methods --> Three of them, the distributional, structural and composite sets, were led by 16_fsqn_r with 12 to 18 places. The local set was led by 10_mnn with 19 places. <!-- src: A2_T4 --> [FIG:fig_election]D follows the approaches through the class L and M gate and the three biology-facing elections. Of the 2,234 approaches, 1,686 pass the joint gate of a marker correlation above 0.75 and a positive margin. <!-- src: 01_numbers gates joint_L_M_gate, rho_gate --> Classes L, M and N each elect 112 approaches, and one approach is elected by more than one of the three ([FIG:fig_election]D). <!-- src: A2_T3b L–N 1, L–M 0, M–N 0 -->
<!-- why: D1; the global census replaced after the PCReg fix (13_fsmvn 59 + 03_limma 27 = 86 -> 03_limma 42 + 13_fsmvn 42 = 84, 15_pcreg_fix.md); the local set is led by 10_mnn (19), not by 16_fsqn_r (9), and the composite now spans 25 methods (A2_T4); "Four of the nine groups are therefore single-method verdicts" was wrong (they hold two to four methods) and is replaced; Figure 5F, 5G -> [FIG:fig_election]C, D (B2); D3 mechanism for the global census -->

### P136 [edit]
We then asked which methods each class would recommend if a benchmark reported that class alone. The global class would recommend 03_limma and 13_fsmvn. Of the two, 13_fsmvn reached a median full-cut F1 of 0.537 against 0.715 for the other approaches (Mann–Whitney U, p = 3.6 × 10⁻¹⁸). On the same cut, 03_limma was second to last of the 31 methods ([FIG:fig_prediction_n]A). <!-- src: A2_T10 T10-108; fig_prediction_n panel A order --> Class M, read without the margin, would recommend 10_mnn and 12_scanorama, whose median marker correlations were −0.001 and −0.008. The other approaches had a median of 0.969 (Mann–Whitney U, p = 1.7 × 10⁻⁵⁰ for 10_mnn). <!-- src: A2_T10 T10-070-1a, T10-070-2a (−0.000655, −0.00816 at three decimals) --> Class N would recommend the ComBat family, whose count-based implementations 06_combat_seq and 08_inmoose_combatseq returned mean maximum expression values of 2.76 × 10⁸ and 1.46 × 10¹¹ <!-- src: 01_numbers stat_requests SR-U01 --> (Figure 3E). Class L would recommend unharmonized or near-unharmonized output, 01_raw and 36_explobatch (Supplementary File 1, sheet Method_census_by_class). In each of the four cases, the recommended methods scored poorly on at least one quantity measured by another class.
<!-- why: D1; A2 tests for each recommendation; the claim that 13_fsmvn is "in the bottom five methods" on both cuts does not hold on the 260924 tables (fig_prediction_n A) and is replaced by its test; D4 aphorisms deleted ("Each recommendation is correct under its own criterion and fails under the next one"; "The choice of metric class therefore determines the recommendation more than the data do"); the expression maxima 2.76 × 10⁸ and 1.46 × 10¹¹ are not in tables/ or 01_numbers -> SR-U01 -->

### P137 [edit]
Taken together, the four batch-facing classes and the composite agreed above chance in nine of their ten pairs, whereas the three biology-facing classes shared fewer approaches than chance with each other and elected sets built on different methods (Table 3). A benchmark that selects harmonization approaches should therefore declare its metric classes, its gates and its held-out test before ranking, and report the elected set of every class with the intersections and their chance expectation. Class L then serves as a gate, because a per-batch monotone transform keeps within-cohort marker ranks: the low-harshness tier holds a median marker correlation of 0.998 while predicting worst of the three tiers on the full cut (Table 1). <!-- src: 01_numbers harshness kruskal mk_rho_mean_markers low 0.998; pv_lobo3_f1_macro_mean low 0.631 (Table 1, A2_T9) --> Class M is read as the margin against the unharmonized baseline at the same strategy and imputation, because agreement alone rewards algorithms that make all profiles alike. Class N is reported on both fold cuts with the multiclass fold count, because 47.1% of the held-out batches carry one class, and with the bad-batch-retaining strategies excluded, because they reach the highest values of all (Table 2). <!-- src: A2_T8, 01_numbers pct_singleclass --> Figure 6 draws these steps as a recipe.
<!-- why: D2 "Taken together" close stating the consequence for benchmarking practice; numbers reduced to those needed for the mechanism (rule 15), the rest pointed at Tables 1 and 2; "We have drawn these three traps…" reworded without self-reference (D4) -->

---

## Conclusions (P139–P144)

### P139 [keep]

### P140 [edit]
We elected the top 5% of 2,234 harmonization approaches once for each of eight metric classes, changing only the class that ranked them, and compared the elected sets with the 15 approaches selected by the published clustermap. The largest overlap between two elected sets of 112 approaches was 71 shared approaches (Jaccard 0.464), between the local class and the composite that contains it (Table 3). <!-- src: A2_T3b local–composite --> The three biology-facing classes shared one approach in total, the unharmonized I_rare_batches_removed / softimpute / 01_raw / post1 elected by classes L and N, and each of their three pairwise overlaps was below the 5.6 approaches expected by chance. <!-- src: A2_T3b L–M, M–N, L–N; Supplementary File 2 Elected_sets_by_class --> The clustermap selection shared no approach with classes L and N, which a set of 15 does by chance with probability 0.46. <!-- src: A2_T3b p_less_than_chance --> On the generalizability index its approaches ranked between 433rd and 2,022nd of 2,234. <!-- src: 01_numbers clustermap_index_rank_range -->
<!-- why: 0.333/56 -> 0.464/71 (15_pcreg_fix.md); chance expectations added (brief); the L ∩ N approach named (A1); "The 15 approaches … shared none of the 112 that prediction elected" kept as a count with its chance probability, because zero is not below chance (p = 0.46); rule 15 splits -->

### P141 [edit]
Each class elected the approaches that maximize the quantity it measures. Marker preservation (class L) elected unharmonized and near-unharmonized output, because a per-batch monotone transform leaves within-cohort ranks unchanged. Cross-batch rank agreement (class M) elected 10_mnn and 12_scanorama, which make profiles alike and return median marker correlations of −0.001 and −0.008. <!-- src: A2_T10 T10-070-1a, T10-070-2a --> The global class elected 03_limma and 13_fsmvn, two of the six methods that drive batch PCReg to saturation, and 13_fsmvn predicted held-out batches worse than the other methods (median full-cut F1 0.537 against 0.715, Mann–Whitney U, p = 3.6 × 10⁻¹⁸). <!-- src: A2_T4 global; 01_numbers methods_at_saturation; A2_T10 T10-108 --> Cross-batch prediction (class N) elected four ComBat implementations, two of which, 06_combat_seq and 08_inmoose_combatseq, return mean maximum expression values of 2.76 × 10⁸ and 1.46 × 10¹¹ <!-- src: 01_numbers stat_requests SR-U01 --> (Figure 3E).
<!-- why: D4 aphorism deleted ("Every one of these verdicts is defensible inside its own class and indefensible outside it"); the global census updated after the PCReg fix (03_limma and 13_fsmvn, 42 each); "ranks in the bottom five on prediction" replaced by its test (A2); A1 (methods named); expression maxima -> SR-U01 -->

### P142 [edit]
Three properties of the metrics themselves caused most of this behavior, and each can be handled at the reporting stage. A within-cohort correlation metric saturates, so it works as a gate at a stated threshold and does not order the approaches that pass it: the low-harshness tier holds a median marker correlation of 0.998 while returning the lowest full-cut prediction F1 of the three tiers, 0.631 (Table 1). <!-- src: 01_numbers harshness kruskal low 0.998, 0.631 --> An agreement metric rises whenever an algorithm makes profiles alike, so it has to be read as the margin between same-biology and different-biology agreement, taken against the unharmonized baseline at the same strategy and imputation. Requiring both directions of that margin leaves 61 of the 2,150 non-raw approaches (2.8%). <!-- src: 01_numbers agreement_specific n, pct_of_non_raw --> A prediction metric depends on the composition of the held-out batch, so it has to be cut by batch and reported on both fold cuts: 15,436 of the 32,746 three-class folds carry one class. <!-- src: A2_T8; 01_numbers fold_composition --> These single-class folds reach a median macro F1 of 0.903 against 0.733 for the rest (Mann–Whitney U, p = 2.3 × 10⁻²²¹). <!-- src: A2_T10 T10-090 --> The highest prediction values among approaches with a multiclass fold come from a strategy that keeps the known-bad batches (full-cut F1 0.958, multiclass-only mean 0.924; Table 2). <!-- src: A2_T13 batch-confounded row -->
<!-- why: 0.7334 -> 0.733 (D5); test added to the fold comparison (A2); "behaviour" -> "behavior" (D7); rule 15 splits; "anywhere" made precise (the degenerate Affymetrix-only approaches reach 1.000 with no multiclass fold) -->

### P143 [edit]
We set these steps out as a recipe (Figure 6). First, declare the metric classes before computing them. Second, compute every class over the full approach set. Third, use the within-cohort marker correlation as a gate at a stated threshold. Fourth, rank on the class M margin taken against the unharmonized baseline at the same strategy and imputation. Fifth, validate by leave-one-batch-out prediction whose projection is fitted on the training batches only, reported on both fold cuts with the multiclass fold count beside each value. Sixth, report the elected set of every class together with their intersections, so that a reader can see which recommendation depends on which criterion. Applied to this dataset, 1,187 approaches <!-- src: 01_numbers stat_requests SR-U02 --> pass the gate with a positive margin and carry at least five multiclass folds outside the bad-batch-retaining strategies. The leading one by full-cut F1 is no removal with softimpute under 29_combat_ref without post-removal (S0_no_removal / softimpute / 29_combat_ref / post0), with a full-cut F1 of 0.946 and a marker correlation of 0.880 (Table 2). Its multiclass-only mean was 0.887 over 11 multiclass folds. <!-- src: A2_T13; the approach passes rho > 0.75 and xb_margin > 0 in A2_T1 -->
<!-- why: the six steps kept in the order and wording of Figure 6 (legend P138), which is not changed; "instead of a shortlist" removed (antithesis, rule 9); "a small set of approaches that pass every step" had no count behind it -> SR-U02; the leading approach named in full (A1) -->

### P144 [edit]
The limits of this work follow from its design. All 2,234 approaches come from one dataset of germinal-center B-cell lymphomas, so the numbers are specific to a setting in which the biological contrast is small and the technical contrast is large. The election threshold of 5% is a choice, and a different threshold changes the set sizes. The ordering of the overlaps did not depend on it, and all 36 pairs at each threshold are listed in Supplementary File 2, sheet Threshold_sensitivity. The local and composite sets overlapped most at thresholds of 2.5%, 5% and 10%. At the 2.5% threshold, the pairwise Jaccard values correlated with those at 5% (Spearman ρ = 0.801). At the 10% threshold, they correlated with ρ = 0.881. <!-- src: A2_T3c; 01_numbers stat_requests SR-U03 --> Classes L and M rest on one 633-gene panel, and a different panel would change their elected sets. The prediction class uses three diagnostic classes and 24 batches, and nearly half of its held-out folds carry one class, so its folds are coarse. Because every class was elected from the same 2,234 approaches by the same procedure, the differences between the elected sets arise from the metric classes themselves.
<!-- why: "germinal-centre" -> "germinal-center" (D7); the unverified claim that a different threshold does not change the ordering of the overlaps -> SR-U03 (rule 16); the closing antithesis ("What does not depend on these choices is…") replaced by a plain declarative (D4) -->

---

## Data and Software availability (P145–P148)

### P145 [keep]

### P146 [edit]
The expression matrices, cohort annotation and harmonization metric tables analyzed here are deposited at Zenodo, https://doi.org/10.5281/ZENODO.22737294 (harmonized expression matrices and benchmark metric tables covering 73 public cohorts, CC-BY-4.0). [TO CONFIRM: that Zenodo record 22737294 is published before submission; it was uploaded as a draft on 14 September 2026.] The derived tables behind every number in this article (A2_T0 to A2_T16) are provided as Supplementary File 1 and Supplementary File 2 and in the same record. Source accession numbers for the public cohorts are listed in Supplementary File 1 of the source benchmark [38].
<!-- why: the derived tables are now A2_T0–A2_T15 (brief); "analysed" -> "analyzed" (D7); [38] verbatim; the draft status of the Zenodo record comes from the project memory and is flagged for Daniil -->

### P147 [keep]

### P148 [edit]
Analysis code, the election module analysis/article2_generalizability.py and the panel scripts are in https://github.com/Nikit357/FL_harmonization, archived at [TO CONFIRM: new FL_harmonization release DOI]. The ComboBatch harmonization tool is at https://github.com/Nikit357/ComboBatch, archived at https://doi.org/10.5281/ZENODO.22755758, with its benchmark record at https://doi.org/10.5281/ZENODO.22755764. The containerized Shambhala-2 implementation is at https://github.com/Nikit357/Shambhala2_fast, archived at https://doi.org/10.5281/ZENODO.22756647. License: MIT. Package versions are given in Materials and methods.
<!-- why: "Licence" -> "License" (D7); the release-DOI placeholder is genuinely unknown and stays -->

---

## Back matter (P161–P177)

### P161 [keep]

### P162 [edit]
No consensus reporting guideline covers a re-analysis of benchmark metric tables. We followed the general principle that every quoted value names the table, column and filter that produced it, and those assignments are listed in Supplementary Files 1 and 2.
<!-- why: unchanged in wording; kept as [edit] only to confirm it was checked against C5 -- it states a reporting principle for the reader, not an internal QA log. May be treated as [keep]. -->

### P163 [keep]

### P164 [keep]

### P165 [keep]

### P166 [keep]

### P167 [keep]

### P168 [edit]
CRediT roles, by author. Daniil Nikitin: conceptualization, methodology, software, formal analysis, investigation, data curation, validation, visualization, writing – original draft, writing – review and editing. Arsen Arakelyan: conceptualization, methodology, supervision, project administration, funding acquisition, writing – review and editing.
<!-- why: F6 -- the author list is final at two; each author keeps the roles the base assigned to them, named with the CRediT terms -->

### P169 [keep]

### P170 [edit]
[Competing-interests statement: as in the published article.] [TO CONFIRM: competing-interest detail, resolved in the published article] Arsen Arakelyan directs the institute given as affiliation 1, where Daniil Nikitin is a PhD candidate, and this article forms part of that thesis. [TO CONFIRM: whether Arsen Arakelyan declares any competing interest.]
<!-- why: F6 -- rewritten for the two authors; the affiliation-2 funding link is taken from P172; no employment fact invented -->

### P171 [keep]

### P172 [keep]

### P173 [keep]

### P174 [keep]

### P175 [keep]
<!-- note: kept verbatim. The ten co-authors removed from the author list (Nikolay Borisov, Maria Savchenko, Anatoly Bobe, Mark Meerson, Alexander Nesmelov, Nazar Harutyunyan, Svetlana Paponova, Andrey Kravets, Alexandr Zaitsev, Alexandr Bagaev) are not added here; whether to acknowledge them is a question for Daniil (change log) -->

### P176 [keep]

### P177 [edit]
The reference list is generated from the citation fields of the manuscript.
<!-- why: the list is now generated by Mendeley (plan §C1); the frozen references_260917.md and reference_support_260917.md are not part of the submission and are no longer named -->

