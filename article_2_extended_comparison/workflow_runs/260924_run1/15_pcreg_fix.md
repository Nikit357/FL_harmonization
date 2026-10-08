# 15 — The PCReg column-name fix and what it changed, 2026-09-25

## Status

**Fixed and recomputed on Daniil's decision (2026-09-25).** Supplementary File 3 spells the seven PCReg columns `PCReg_<col>`; `METRIC_CLASS_PREFIXES` and Article 1's polarity map (`figures_helpers._build_polarity`) expect `pcr_<col>`. Unrenamed, the seven columns matched no class prefix and carried polarity 0, so the **global class used 4 DSC metrics instead of 11**, and the composite (mean of four classes) inherited it. `load_analysis_set()` now renames them on load (values identical). `--stamp 260917` keeps the old behaviour and still reproduces the nine 260917 tables exactly.

Unaffected: classes L, M, N and their elected sets, the E1 index, A2_T1, A2_T2, A2_T9–A2_T14. Changed: A2_T3, A2_T3b, A2_T4, A2_T15 and the election figure.

## Pairs whose overlap changed (A2_T3b)

| pair | shared old | shared new | Jaccard old | Jaccard new |
|---|---:|---:|---:|---:|
| global – local | 15 | 8 | 0.072 | 0.037 |
| global – distributional | 27 | 14 | 0.137 | 0.067 |
| global – structural | 15 | 18 | 0.072 | 0.087 |
| global – composite | 40 | 20 | 0.217 | 0.098 |
| global – L | 4 | 1 | 0.018 | 0.004 |
| global – clustermap_best | 4 | 0 | 0.033 | 0.000 |
| local – composite | 56 | 71 | 0.333 | 0.464 |
| distributional – composite | 55 | 50 | 0.325 | 0.287 |
| composite – L | 9 | 7 | 0.042 | 0.032 |
| composite – M | 3 | 6 | 0.014 | 0.028 |
| composite – N | 0 | 2 | 0.000 | 0.009 |
| composite – clustermap_best | 4 | 7 | 0.033 | 0.058 |

**global elected set, leading methods.** Old: 13_fsmvn 59, 03_limma 27, 33_amdbnorm 10, 16_fsqn_r 9, 07_pycombat 6. New: 03_limma 42, 13_fsmvn 42, 07_pycombat 13, 21_harmonizr 5, 28_npn 3.

**composite elected set, leading methods.** Old: 16_fsqn_r 18, 13_fsmvn 18, 26_xpn 11, 33_amdbnorm 9, 21_harmonizr 9. New: 16_fsqn_r 12, 13_fsmvn 11, 26_xpn 10, 10_mnn 9, 21_harmonizr 8.

## Sentences in the base text this makes wrong

- Abstract and Introduction: "Local and composite metrics resulted in the largest overlap of best approaches (0.333, 56 shared)".
- Results, "The sets elected…": every global and composite Jaccard and count; "The global class puts 86 of its 112 places into two methods, 13_fsmvn (59) and 03_limma (27)"; the clustermap-group overlaps with global and composite.
- Conclusions: "The largest agreement between any two elected sets of 112 approaches was 56 approaches (Jaccard 0.333)".
