# 12 — Rank churn of the E1 index change (Phase 1), 2026-09-25

## Status

**Done.** The generalizability index now uses macro F1 for both LOBO targets (C16, plan E1):
the third of its six components changed from `pv_lobo2_auc_macro_mean` to
`pv_lobo2_f1_macro_mean`. The other five components are unchanged.

- New ranking: `tables/A2_T2_generalizability_ranking_260924.csv`
- Old ranking, kept: `tables/A2_T2_generalizability_ranking_260917.csv`
- Per-approach comparison: `12_index_rank_churn.csv`. Summary: `12_index_rank_churn.json`.

Produced by `analysis/article2_generalizability.py` (default `--stamp 260924`).
`--stamp 260917` still reproduces every 260917 table exactly (checked 2026-09-25, all nine
tables identical up to floating-point noise).

## Summary

| Quantity | 260917 (AUC) | 260924 (F1) |
|---|---:|---:|
| Spearman ρ between the two indices, 2,234 approaches | — | 0.952 |
| Median absolute rank change | — | 111.5 |
| Largest absolute rank change | — | 750 |
| Top 15 over all approaches, shared by both | — | 15 of 15 |
| Top 40 over all approaches, shared by both | — | 26 of 40 |
| Top 15 among the 1,527 eligible, shared by both | — | **6 of 15** |
| Eligible leader | `S0_no_removal__strict__29_combat_ref__post1`, 0.8875 | **same approach**, 0.886 |
| Range of the 15 highest values over all approaches | 0.933 to 0.982 | 0.949 to 0.986 |
| The 15 highest are all Affymetrix-only, post-removal, zero multiclass folds | yes | yes |
| Rank range of the 15 clustermap-selected approaches | 323 to 2,038 | 433 to 2,022 |

"Eligible" means outside the two bad-batch-retaining strategies and with at least 5 multiclass
folds, as in the manuscript.

## What changes in identity (plan decision 4)

**The leader does not change, but the top of the eligible ranking does.**

- **Under the old index**, the top 15 eligible included five RNA-seq-only approaches with no or
  near-no harmonization: `01_raw` (3rd), `36_explobatch` and `04_sva` (tied 5th), and
  `31_ruv3prps` (11th). Its method mix was 05_combat 8, 29_combat_ref 3, and one each for
  01_raw, 04_sva, 36_explobatch and 31_ruv3prps.
- **Under E1** these fall to ranks 33, 38, 38 and 57. The top 15 eligible is now **only ComBat**:
  29_combat_ref 9 and 05_combat 6. Six FF-only (`J_ff_only`) 29_combat_ref and 05_combat
  approaches rise from ranks 25–69 to ranks 2–13.

**Consequences for the text (Phase 3):**

- Results, "Cross-batch prediction…":
  - index leader value: 0.8875 → 0.886
  - range of the top 15: 0.933–0.982 → 0.949–0.986
  - clustermap rank range: 323rd–2,038th → 433rd–2,022nd
- The Methods definition of the index (C16) must name the two-class macro F1.
- Figure 5D (`a2_p8`) must be redrawn from the 260924 table.
- The Abstract and Conclusions quote no index value, so they are unaffected. The E1 change does
  strengthen the title's ComBat claim: the top 15 eligible approaches by the index are now all
  ComBat.
