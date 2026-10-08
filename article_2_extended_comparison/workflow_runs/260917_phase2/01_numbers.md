# Article 2 — numbers and their provenance

Snapshot `metrics_comprehensive_260905.csv`. Produced by `analysis/article2_generalizability.py --date-tag 260905`. Every value is read back out of `tables/A2_T*.csv`.

## analysis_set

| number | value | table | column | filter | quoted in |
|---|---|---|---|---|---|
| n_approaches | 2234 | A2_T1 | run_id | Supplementary File 3, pct_samples_allNA < 5 | Methods; Results §6 |
| n_methods | 31 | A2_T1 | method | same | Methods |
| n_strategies | 14 | A2_T1 | strat | same | Methods |
| n_imputations | 3 | A2_T1 | imp | same | Methods |
| n_shambhala_rows | 84 | A2_T1 | method == 20_shambhala | after the shambhala_P0std_Q0std rename | Methods |
| identity_columns_identical | 78 of 79 | A2_T0 | identical | 84 matched (strat, imp, post_rm) keys | Methods; Results §6 |
| identity_only_difference | ['compute_time_s'] | A2_T0 | column | identical == False | Methods |

## gates

| number | value | table | column | filter | quoted in |
|---|---|---|---|---|---|
| joint_L_M_gate | 1686 | A2_T1 | mk_rho_mean_markers, xb_margin | rho > 0.75 AND margin > 0 | Results §6 |
| rho_gate | 0.75 | — | mk_rho_mean_markers | Daniil's threshold, necessary not sufficient | Methods; Results §6 |

## shambhala

| number | value | table | column | filter | quoted in |
|---|---|---|---|---|---|
| median_rho | 0.84 | A2_T1 | mk_rho_mean_markers | method == 20_shambhala | Results §6 |
| median_margin | 0.0048 | A2_T1 | xb_margin | method == 20_shambhala | Results §6 |
| median_lobo3_f1 | 0.745 | A2_T1 | pv_lobo3_f1_macro_mean | method == 20_shambhala | Results §6 |

## agreement_specific

| number | value | table | column | filter | quoted in |
|---|---|---|---|---|---|
| n | 61 | A2_T6 | run_id | xb_rank_agree_delta > 0 AND xb_rank_disagree_diffbio_delta < 0 | Results §6 |
| pct_of_non_raw | 2.8 | A2_T6 | — | denominator = 2150 non-raw approaches | Results §6 |
| top_margin_delta | 0.457 | A2_T6 | xb_margin_delta | maximum | Results §6 |
| top_approaches_tied | ['K_ffpe_only/knn/08_inmoose_combatseq/post0', 'K_ffpe_only/knn/06_combat_seq/post0'] | A2_T6 | strat, imp, method, post_rm | xb_margin_delta == max | Results §6 |

## prediction

| number | value | table | column | filter | quoted in |
|---|---|---|---|---|---|
| leading_non_degenerate | {'run_id': 'S0_no_removal__softimpute__29_combat_ref__post0', 'full_mean_f1': 0.946, 'worst_multiclass_fold': 0.462, 'n_multiclass_folds': 11, 'auc_2class': 0.932, 'rho': 0.88} | A2_T1 | pv_lobo3_f1_macro_mean | strat not in (A_confirmed_bad, B_extended_bad) AND n_mc >= 5 | Results §7 |
| n_eligible_non_degenerate | 1527 | A2_T1 | — | same filter | Results §7 |
| n_zero_multiclass_folds | 59 | A2_T1 | n_mc | n_mc == 0 | Results §7; caveat 1 |
| spearman_full_vs_multiclass | 0.81 | A2_T1 | pv_lobo3_f1_macro_mean, f1_mc_mean | both present, n = 2174 | Results §7 |
| spearman_min3_multiclass_folds | 0.815 | A2_T1 | same | n_mc >= 3, n = 2058 | Results §7 |

## fold_composition

| number | value | table | column | filter | quoted in |
|---|---|---|---|---|---|
| n_3class_folds | 32746 | A2_T8 | n_folds | target == 3class, run_id in the 2,234 analysis set | Results §7 |
| n_singleclass_folds | 15436 | A2_T8 | n_folds | n_classes == 1 | Results §7 |
| pct_singleclass | 47.1 | A2_T8 | n_folds | n_classes == 1 | Results §7 |
| median_f1_by_class_count | {1: 0.903, 2: 0.629, 3: 0.804} | A2_T8 | median_f1 | per n_classes, median over batches | Results §7 |
| n_batches | 25 | A2_T8 | batch | — | Methods |

## harshness

| number | value | table | column | filter | quoted in |
|---|---|---|---|---|---|
| tier_sizes | {'medium': 1042, 'high': 848, 'low': 344} | A2_T1 | harshness_level | HARSHNESS_LEVEL_MAP, method level | Results §5b |
| kruskal | {'mk_rho_mean_markers': {'H': 340.1, 'p': 1.4323253805703997e-74, 'low': 0.998, 'medium': 0.88, 'high': 0.922}, 'mk_rho_marker_minus_hk': {'H': 139.3, 'p': 5.546808729547732e-31, 'low': -0.0, 'medium': 0.009, 'high': 0.031}, 'xb_rank_agree': {'H': 287.1, 'p': 4.4703247633956234e-63, 'low': 0.691, 'medium': 0.701, 'high': 0.507}, 'xb_margin': {'H': 132.9, 'p': 1.4006458651335526e-29, 'low': 0.054, 'medium': 0.045, 'high': 0.03}, 'pv_lobo3_f1_macro_mean': {'H': 51.6, 'p': 6.132188937881346e-12, 'low': 0.631, 'medium': 0.712, 'high': 0.715}, 'f1_mc_mean': {'H': 11.8, 'p': 0.0027580633912576, 'low': 0.657, 'medium': 0.678, 'high': 0.678}, 'pv_lobo2_auc_macro_mean': {'H': 1.5, 'p': 0.4769378448192957, 'low': 0.901, 'medium': 0.904, 'high': 0.904}} | A2_T7 | kruskal_H, kruskal_p, median_* | three method-level harshness tiers | Results §5b |

## per_batch_example

| number | value | table | column | filter | quoted in |
|---|---|---|---|---|---|
| run_id | S0_no_removal__softimpute__29_combat_ref__post0 | | | | |
| n_folds | 24 | A2_T5 | batch | target == 3class | Results §7 |
| n_singleclass | 13 | A2_T5 | n_classes | n_classes == 1 | Results §7 |
| hardest_multiclass_folds | [{'batch': 'GPL96_FFPE_Unknown', 'n': 84, 'n_classes': 2, 'f1_macro': 0.4615, 'auc': 0.5428}, {'batch': 'RNASeq_FFPE_PolyA', 'n': 35, 'n_classes': 2, 'f1_macro': 0.6983, 'auc': 0.8736}, {'batch': 'RNASeq_FF_PolyA', 'n': 1039, 'n_classes': 3, 'f1_macro': 0.7176, 'auc': 0.9722}] | A2_T5 | f1_macro | n_classes >= 2, three smallest | Results §7 |

## discrepancies

Reported, never silently corrected. Each one reaches the manuscript text.

### 1. Across the 53,737 3-class folds, 25,426 (47.3%) contain a single class

- **Source:** plan §1.5d
- **Recomputed:** 32,746 3-class folds, 15,436 single-class (47.1%)
- **Filter, source:** every run_id in prediction_folds_long.csv (3,738 run_ids, 50 method names, all 18 Shambhala P/Q variants)
- **Filter, recomputed:** run_id restricted to the 2,234-approach analysis set
- **Cause:** the published figure counted folds for approaches the article never analyses; 21,543 of the 53,737 belong to the 17 non-canonical Shambhala variants alone
- **Effect on the conclusion:** the conclusion is unchanged -- single-class folds are still about half the population -- only the counts move

### 2. single-class folds have median macro F1 0.952; two-class 0.648; three-class 0.830

- **Source:** plan §1.5d
- **Recomputed:** 0.903 / 0.629 / 0.804 on the analysis set
- **Filter, source:** as above
- **Filter, recomputed:** as above
- **Cause:** same population difference
- **Effect on the conclusion:** the ordering is unchanged: two-class folds remain the hardest and single-class folds the easiest

### 3. Spearman between the full metric and the multiclass-only mean is 0.812 over the 1,981 approaches with at least three multiclass folds

- **Source:** plan §1.5d
- **Recomputed:** 0.815 over 2,058 such approaches; 0.810 over all 2,174 carrying both
- **Filter, source:** fold aggregates computed over the unrestricted fold table
- **Filter, recomputed:** fold aggregates over the analysis set only
- **Cause:** same population difference; the approach count rises because restricting the fold table does not remove approaches, only foreign run_ids
- **Effect on the conclusion:** unchanged conclusion: the two cuts agree closely and neither reverses the other

### 4. Per-batch detail for S0_no_removal/softimpute/29_combat_ref/post0: 10 of the 24 folds are single-class; the hard folds are GPL96_FFPE_Unknown and RNASeq_FF_PolyA

- **Source:** plan §1.5d
- **Recomputed:** 13 of 24 folds are single-class; the three hardest multiclass folds are GPL96_FFPE_Unknown (F1 0.462), RNASeq_FFPE_PolyA (0.698) and RNASeq_FF_PolyA (0.718)
- **Filter, source:** unknown; not reproducible from prediction_folds_long.csv
- **Filter, recomputed:** A2_T5, target == 3class
- **Cause:** the two quoted folds and their values reproduce exactly; the single-class count and the identity of the second-hardest fold do not
- **Effect on the conclusion:** the approach's characterisation is unchanged

### 5. multiclass-only F1 across harshness tiers: H = 11.2, p = 0.0037

- **Source:** plan §1.5e
- **Recomputed:** H = 11.8, p = 0.0028
- **Filter, source:** f1_mc_mean computed over the unrestricted fold table
- **Filter, recomputed:** f1_mc_mean over the analysis set
- **Cause:** same population difference; every other row of the tier table reproduces exactly, including the 2-class AUC result (H = 1.5, p = 0.48, not significant)
- **Effect on the conclusion:** unchanged

### 6. Top by raw-subtracted margin: K_ffpe_only / knn / 06_combat_seq / post0

- **Source:** plan §1.5c
- **Recomputed:** 06_combat_seq and 08_inmoose_combatseq are an exact tie at that (strat, imp, post_rm): margin 0.439161, gain +0.457154 for both
- **Filter, source:** A2_T6 sorted by xb_margin_delta
- **Filter, recomputed:** same
- **Cause:** two implementations of the same algorithm return identical Group M values; the sort order between them is arbitrary
- **Effect on the conclusion:** quote both, or say that the two implementations agree exactly -- which is itself a positive control worth a sentence

### 7. Cells not traceable to the generator: 8 in the main notebook, 43 in the narrow-set notebook, 29 in the deep-analysis notebook

- **Source:** plan §4.2e
- **Recomputed:** 12 / 50 / 53 hand-written, plus 6 / 12 / 52 generator cells edited in place
- **Filter, source:** unknown
- **Filter, recomputed:** tools/extract_hand_written_cells.py, generator run at the same --date-tag, normalized comparison, NEAR threshold 0.90
- **Cause:** the earlier count did not separate edited generator cells from untouched ones; an edited cell still looks like the generator's, so regeneration reverts it without saying so
- **Effect on the conclusion:** materially larger: 185 cells must survive regeneration, not 80
