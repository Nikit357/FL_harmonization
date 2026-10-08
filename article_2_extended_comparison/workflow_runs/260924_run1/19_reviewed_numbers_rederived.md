# 19 — Numbers kept from Daniil's reviewed text, re-derived (Phase 4), 2026-09-25

## Status

**All re-derived; every one reproduces.**

The writer-reviewed draft kept 13 groups of numbers from Daniil's reviewed text or his extended
document. It marked each "base text, not in A2_T*", because no source row had been named for it.
Each value below was recomputed from the analysis set (2,234 approaches, the pinned snapshot
joined as in `analysis/article2_generalizability.py`). Where a group mean is involved, it was
checked against `tables/A2_T16_pca_component_means_260924.csv`.

| Paragraph | Value in the text | Recomputed | Source |
|---|---|---|---|
| P38 | 05_combat + 29_combat_ref biology PCReg 0.357 to 0.823, strategies A, B, I, J, E1–E3 | 0.357, 0.823 | `pcr_Diagnosis_cell_type_unified`, min/max |
| P38 | 33_amdbnorm 1.000 in 14 runs; 13_fsmvn minimum 0.997 | 14 runs at 1.0; 0.997 | `pcr_RNA_BATCH` |
| P39 | five slow-decay methods, 17.3 to 25.3% on PC1 | 17.3, 25.3 | A2_T16 method rows, `pct_var_pc1` |
| P40 | tSNE centroid dispersion, method means 0.24 (13_fsmvn) to 1.00 (27_dwd) | 0.24, 1.00 (the extremes) | `tsne_centroid_disp_RNA_BATCH`, method mean |
| P49 | MNN clustermap approaches 0.781 to 0.957; FSQN R 0.001 to 0.010 | 0.781–0.957; 0.0013–0.0098 | `dsc_RNA_BATCH`, clustermap group |
| P50 | softimpute − KNN 1.7 to 9.7 pp, mean 4.8, 11 lowest-PCReg methods | 1.7, 9.7, 4.8 | per-method mean `pcr_RNA_BATCH` × 100 |
| P53 | RNA_BATCH R² on PC1: RNA-seq-only 0.29, clustermap best 0.23 | 0.288, 0.229 | A2_T16 |
| P56 | PC1 batch R²: clustermap 22.9%, unharmonized 64.8%, 14_qsmooth 90.8% | 22.9, 64.8, 90.8 | A2_T16 (**unharmonized = the 01_raw method row, all strategies**; 01_raw under no removal alone gives 77.1) |
| P56 | PC1 variance 37.9%, 73.5%, 53.7% | 37.9, 73.5, 53.7 | A2_T16 |
| P56 | PC2 batch R² 15.2%, 65.9%, 67.1%; PC2 variance 11.6%, 9.7%, 13.5% | 15.2, 65.9, 67.1; 11.6, 9.7, 13.5 | A2_T16 |
| P58 | kBET < 0.01 for 82.0% of the 2,234 | 82.0 | `kbet_acceptance_rate_RNA_BATCH` |
| P59+3 | only 04_sva and 10_mnn above kBET 0.1 in a sizable number of approaches | 04_sva 10, 10_mnn 9; next 11_harmony 4 | count per method |
| P62 | distance ratio below unharmonized (0.566): 27_dwd 0.508, 14_qsmooth 0.531 | 0.508, 0.531, 0.566 | `dist_ratio_RNA_BATCH`, method mean |

**One wording point for Phase 5.** P56 calls the 01_raw rows "the unharmonized data". These
values are the mean over all 84 01_raw approaches across the 14 strategies, not the single
no-removal matrix. The sentence is correct, but a reader could take it as the no-removal
baseline, which gives different values (PC1 variance 82.5%, PC1 batch R² 77.1%).
