# 13 — Phase 1 evidence report (gate 1), 2026-09-25

## Status

**Phase 1 is done and ready for gate 1.** Every TODO item of plan Phase 1 is implemented.

- **Script:** `analysis/article2_generalizability.py`, run at the default `--stamp 260924`,
  writes 18 tables and a tier registry to `tables/`.
- **Evidence JSON:** `analysis/build_numbers_json.py` writes `01_numbers.json` and
  `01_numbers.md` here, with 325 entries and 3-digit spellings.
- **Citations:** the literature scout wrote `11_citations_to_insert.md`, 24 proposals.
  None is written into the manuscript.
- **Nothing in the manuscript, the `.docx` or Figma was touched.** No 260917 table changed:
  `--stamp 260917` still reproduces all nine exactly.

**Gate 1 questions:**

1. *Does every new number resolve to a table?* **Yes.** Every value comes from a
   `tables/A2_T*_260924.csv` file and is mirrored in `01_numbers.json`.
   `audit_numbers.py` runs clean against the current master.
2. *Is every proposed citation resolved to a PMID or DOI and pinned to a named sentence?*
   **Yes for 23 of 24.** Python 3.11 has no paper, so only its URL is given; the
   exception is recorded in the proposal file.

Commands, from `article_2_extended_comparison/`:

```bash
source ~/venvs/collagen_3_11/bin/activate
python analysis/article2_generalizability.py          # --stamp 260924, --run-dir workflow_runs/260924_run1
python analysis/build_numbers_json.py                 # -> workflow_runs/260924_run1/01_numbers.{json,md}
python tools/audit_numbers.py manuscript/FL_metric_classes_F1000_260924.md \
    --tables tables/ --evidence workflow_runs/260924_run1/01_numbers.json
```

## The tables and their tiers (HARD_RULE 19)

`tables/A2_table_registry_260924.csv` holds the tier of each table. The script **asserts** that
there are at most five main-text tables and that none is longer than 15 rows.

| Table | File | Rows | Tier | Serves |
|---|---|---:|---|---|
| **Table 1** | `A2_T9_harshness_table1` | 11 | main | C44, C45: L/M/N by harshness tier, mean and median per tier, Kruskal–Wallis H and p, three pairwise Mann–Whitney p |
| **Table 2** | `A2_T13_lobo_summary` | 14 | main | C47: 8 named groups (medians) and 6 single approaches. LOBO3 and LOBO2, F1 on both fold cuts, AUC |
| **Table 3** | `A2_T3_cross_election_matrix` | 9 | main | the 9 × 9 Jaccard matrix. Counts and chance p for each cell are in A2_T3b |
| **Table 4** | `A2_T2b_generalizability_top_eligible` | 15 | main | C16, E1: the top 15 eligible approaches with their six components |
| Table 5 | — | — | reserve | unallocated |
| | `A2_T2_generalizability_ranking` | 2,234 | supplementary | E1 index, every approach |
| | `A2_T3b_cross_election_pairs` | 36 | supplementary | every pair: both set sizes, intersection, union, Jaccard, expected intersection, hypergeometric p (more and less than chance) |
| | `A2_T9b_harshness_full` | 186 | supplementary | every numeric L/M/N column by tier, including the permutation null; the per-metric n values C46 moves out of the text |
| | `A2_T10_paired_tests` | 285 | supplementary | every test the text relies on (see below) |
| | `A2_T11_scatter_correlations` | 97 | supplementary | Spearman ρ, p and n: 27 panels, 14 per-strategy Figure 2A cuts, 1 fold-cut subset, 55 C48 L/M/N pairs |
| | `A2_T12_metric_census` | 344 | supplementary | the registry mapped to snapshot columns, with the Article 2 class for the C48 annotation |
| | `A2_T14_dispersion` | 34 | supplementary | C42, C43: composite contribution spreads, three named statistics |

## Deviations from the plan, each a decision for Daniil

1. **Table 4 is `A2_T2b`, not `A2_T2`.** A2_T2 has 2,234 rows, which breaks the 15-row limit for
   a main table. A2_T2b is its top 15 among the 1,527 eligible approaches. A2_T2 stays
   supplementary.
2. **Table 3 is the matrix; the pair table is supplementary.** The plan's slate put "28 pairs"
   in the main text. There are 9 sets and so 36 pairs, over the 15-row limit, whereas the 9-row
   matrix fits. A cell can carry "Jaccard (n shared)" from A2_T3b.
3. **AUC has one fold cut, not two.** AUC is undefined on a single-class fold: every such fold
   in `prediction_folds_long.csv` has `auc = NaN`. `pv_lobo*_auc_macro_mean` is therefore
   already a multiclass-only mean, and the `auc_mc_mean` / `auc_mc2_mean` columns reproduce it
   (Kruskal–Wallis H 0.7168 against 0.7166). Tables 1 and 2 give F1 on both cuts and AUC once,
   labelled "multiclass folds (only)". The redundant columns stay in A2_T1 as evidence.
4. **Table 1 has 11 rows, not "six metrics"**:
   - L: marker correlation, marker minus housekeeping
   - M: same-biology agreement, different-biology agreement, margin
   - N: LOBO3 F1 on both cuts, LOBO3 AUC, LOBO2 F1 on both cuts, LOBO2 AUC

   C44 asks for different-biology agreement and for F1 and AUC of both targets, so the table
   grew past six.
5. **`A2_T14_dispersion` is a table the plan did not name.** C42 asks which dispersion
   statistic the composite spreads are, and the answer needed its own table (below).
6. **Table 2 leaders are the best eligible approach per strategy**, top four strategies. This
   is how the manuscript's current leading-approach table reads. By raw order, three of the top
   four would be `F_microarray_only` variants of the same ComBat-Seq result.
7. **New columns.** `f1_mc2_mean`, `f1_mc2_min` and `auc_mc2_mean` give the multiclass-only cut
   of the 2-class target; C47 wants both cuts for both targets. They appear only at stamp 260924.

## Findings the Phase 3 writers must act on

Each finding cites its row in A2_T10, A2_T11 or A2_T3b. All p-values are raw and two-sided.

### Claims the statistics do not support as written

- **C28 — the kBET baseline removes the finding.**
  - Of the 198 PCReg-saturated approaches, 98.5% have kBET < 0.1. The baseline over all 2,234
    is **97.0%**, and 96.9% over the other 2,036.
  - Fisher exact p = 0.27 (T10-020).
  - Saturation does not predict poor local mixing beyond what almost every approach already
    shows. The sentence has to say this.
- **C25 — biology PCReg does not separate the clustermap group.**
  - Clustermap 0.820 against 0.802 for the rest, Mann–Whitney p = 0.69 (T10-002).
  - Batch PCReg does separate it: 0.871 against 0.626, p = 6.3 × 10⁻³ (T10-001).
- **C40 — the Watermelon score does separate the clustermap group, but only on batch
  columns.**
  - wm_mean_batch: p = 1.4 × 10⁻⁵
  - wm_RNA_BATCH: p = 5.0 × 10⁻⁴
  - wm_mean_bio: p = 0.21
  - wm_Diagnosis_cell_type_unified: p = 0.086

  Rows T10-063-1 to -4. "Did not separate" is true for biology only.
- **Graph connectivity: FFPE-only and malignant-only are swapped in the text.**
  - The text gives "FFPE-only, malignant-only … 0.646 and 0.727".
  - The strategy means are **FFPE-only 0.727** and **malignant-only 0.646** (T10-055, T10-056).
- **Strict against KNN, "0.370 against 0.390".** This does not reproduce over the 11
  lowest-PCReg methods, where the means are 0.375 and 0.394 (T10-028). The text's "affected
  methods" is not defined. The unpaired test is borderline (p = 0.054). The matched-pair test
  shows strict below KNN, median −0.020, p = 2.7 × 10⁻²² (T10-029).
- **Post-removal "median shift of 0.030".** The matched-pair median shift is 0.011, with mean
  0.025 (T10-031, Wilcoxon signed-rank). 0.030 must be a different statistic, likely the median
  over methods of the per-method mean shift, and the text should say which.
- **Table 1 (manuscript), I_rare_batches_removed row.** It quotes post1, full-cut F1 0.928.
  That strategy's best eligible approach is **post0, 0.932**. The post1 row is its second.
- **The clustermap group sharing no approach with class N is not below chance.**
  - Expected 0.75 shared, hypergeometric p = 0.46 (A2_T3b). The same holds for clustermap ∩ L.
  - These are below chance:
    - L ∩ N = 1: p = 0.020
    - L ∩ M = 0 and M ∩ N = 0: p = 0.0027 each
    - global ∩ M, global ∩ N and composite ∩ N = 0: p = 0.0027 each
- **Harshness within strategies.** The counts reproduce, from tier **means** (not medians):
  - low tier highest batch PCReg in 11 of 14 strategies
  - low tier highest iLISI in 10 of 14
  - high tier lowest tSNE entropy in 12 of 14
  - high tier lowest KS fraction in 13 of 14

  Each count beats the 1-in-3 chance level: binomial p = 6.9 × 10⁻⁴, 4.0 × 10⁻³,
  8.2 × 10⁻⁵ and 5.7 × 10⁻⁶ (T10-064-*-all). **But within any single strategy the tier
  difference is significant in only 1–2 of the 14** (Kruskal–Wallis, T10-064-*-01…14). The
  claim is about the consistent direction across strategies, and should be worded that way.
- **Post-removal on the multiclass-only cut is not significant.** 0.681 against 0.669,
  p = 0.13 (T10-100). The full cut is significant, p = 2.9 × 10⁻³ (T10-099).
- **Class N's post-removal share (63 of 112) does not differ from the analysis set** (binomial
  p = 0.22, T10-102). The imputation mix does, weakly (χ² p = 0.042, T10-101).
- **Imputations do not separate marker correlation.** Kruskal–Wallis p = 0.13 (T10-074). They
  do separate the margin (p = 4.4 × 10⁻⁵, T10-077).
- **The clustermap group does not differ from the rest on the E1 index** (p = 0.95, T10-107).

### Claims that reproduce and now carry their test

These are all in A2_T10; `quoted_reproduced` gives the match per row.

- Batch PCReg differs far more across methods than across strategies: Kruskal–Wallis
  ε² = 0.74 against 0.10 (T10-009, T10-010). This supports "method above strategy".
- Most per-group median claims of Results 1–7 reproduce exactly and now carry a Mann–Whitney p.
  Examples:
  - 10_mnn iLISI 1.72 (T10-011)
  - tSNE entropy 0.179 against 0.0178 (T10-013, after switching to `tsne_entropy_norm_*`)
  - distance ratio 0.914 against 0.757, p = 1.0 × 10⁻³ (T10-062)
  - composite 0.602, p = 1.8 × 10⁻⁸ (T10-065)
  - single-class against multiclass folds, 0.903 against 0.7334, p = 2.3 × 10⁻²²¹ (T10-090)
- **The harshness table, C45:**
  - L and M differ strongly across tiers.
  - LOBO3 F1 differs on both cuts (full H = 51.6; multiclass-only H = 11.8, p = 2.8 × 10⁻³).
    Medium against high is not significant on the multiclass cut (p = 0.66).
  - LOBO2 F1 differs (H = 32.6 full; H = 17.9 multiclass-only).
  - **Neither AUC differs**: LOBO3 p = 0.70, LOBO2 p = 0.48.
  - Mechanism for the C45 conclusion: low-harshness methods apply per-batch monotone
    transforms. They keep within-cohort ranks (marker correlation 0.998), and so they also
    keep batch structure, which is why they predict worst on held-out batches. High-harshness
    methods reshape distributions and destroy cross-batch rank agreement (0.507).
- **C42 and C43 are resolved.** Every published spread reproduces as the **range (max − min)
  of the group means, with the 15 clustermap-selected approaches counted as one more group**
  (A2_T14, column `range_with_clustermap_group`):

  | Published | Reproduces as |
  |---|---|
  | 0.017 across strategies | group A, 0.0172 |
  | 0.030 across methods | group A, 0.0295 |
  | 0.043 across strategies | group B, 0.0427 |
  | 0.049 across methods | group B, 0.0488 |
  | 0.053 across strategies | biology columns, 0.0533 |
  | 0.122 across strategies | batch columns, 0.1215 |

  **One inconsistency to fix:** the sentence reports "47 of the 87 columns and 0.360" by
  **metric type** (global_distance), but the 0.017 and 0.030 spreads that follow are by
  **metric group A**. Under metric type, global_distance spreads by 0.066 across strategies and
  0.085 across methods.
- **C48, all 55 L/M/N scatter pairs have ρ and p** (A2_T11, `T11-L*`).
  - Marker correlation against full-cut LOBO3 F1: ρ = −0.234, p = 3.2 × 10⁻²⁹, n = 2,233
    (T11-L06). This is the negative association behind the "trade-off" sentence C48 is
    anchored to.
  - Margin against marker correlation: ρ = 0.177, p = 3.2 × 10⁻¹⁷ (Figure 4C, T11-024).
- **Figure 2A per strategy:** ρ = 0.374 to 0.815 across 13 strategies. **Affymetrix-only is not
  significant** (ρ = 0.147, p = 0.069, T11-S09). This supports the text's exception.

### Columns chosen, where the text was ambiguous

| Text quantity | Column that reproduces it |
|---|---|
| batch tSNE entropy (0.179, 0.0178) | `tsne_entropy_norm_RNA_BATCH` (the `_mean_` column gives 0.488) |
| batch LISI (1.72, 1.16) | `ilisi_mean_RNA_BATCH` |
| KS fraction significant (0.948 raw) | `ks_frac_sig_RNA_BATCH`, **method mean** (the raw median is 0.961) |
| kBET raw baseline 0.027 | `kbet_acceptance_rate_RNA_BATCH`, **mean** of 01_raw (the median is 0.000) |
| "fraction of cohort pairs … by KS test" | `ks_frac_sig_RNA_BATCH` |

## Hand-offs

- **Citations:** `11_citations_to_insert.md`, 24 proposals, for Daniil to insert through
  Mendeley.
  - C37 first choice: Luecken et al. 2022, *Nat Methods*, already cited.
  - The scout also found that the in-text "Luecken et al. 2021" is dated 2022 in the reference
    list.
- **Figures (Phase 2):**
  - Figure 5D is redrawn from `A2_T2_…_260924`.
  - Supplementary Figure 12 is rebuilt from A2_T9 and A2_T9b; the permutation-null columns
    `pv_*_perm_mean` are in A2_T9b.
  - The C48 clustermap uses A2_T12. The 329 recoverable metrics are the ceiling; at most 328
    can enter a correlation, because `mk_is_self_reference` is constant.
- **Statistics queue:** `10_stat_requests.json` is Phase 3's to create. A2_T10 is appended to on
  each re-entry, never replaced.
