# Numerical audit — `Harmonization_metrics_extended.docx`

**Date:** 2026-08-02  
**Output document:** `Harmonization_metrics_extended_260802_v2.docx` (673 tracked revisions)  
**Edit script:** `apply_extended_metrics_edits_v2_260802.py`  
**Evidence script:** `recompute_extended_metrics_260802.py` (run it to reproduce every row below)

This document is destined for GitHub rather than the journal, so the pass covers language,
grammar and numerical precision only. Scientific claims and the figures themselves are
unchanged, except where a stated number contradicted the data.

---

## 0. Which metric table

The request named `metrics_comprehensive_260527.csv`. That snapshot cannot reproduce the
article, for two independent reasons:

| Check | 260527 | 260609 |
|---|---|---|
| Strategies present | 11 (no I, J, K) | 14 |
| Rows shared with deposited `Supplementary File 3` | 1,822 | 2,323 |
| Numeric columns agreeing with Supp. File 3 | **0 of 66** | **79 of 79** |
| `n_samples` / `n_genes` max disagreement vs 260609 | 850 / 1,309 | — |

The 260527 values were computed on a different set of prepared matrices, so every mean,
median and interval derived from it would contradict both the main article and the deposited
supplementary file. All recomputation therefore used
`metrics_comprehensive_260609.csv` through `figures_helpers.load_metrics_data()` — the same
function the article's figure notebook calls. Where the two snapshots overlap, 260609 is the
later and internally consistent one, so nothing from 260527 is lost.

**Analysis set reproduced exactly:** 2,234 approaches · 31 methods · 14 strategies ·
87 scoring metrics · 15 clustermap best approaches.

Conventions: MAD is the plain (unscaled) median absolute deviation; per-method and
per-strategy summaries in heat-map paragraphs are means over runs, matching the figures,
which average across imputations and post-removal variants.

---

## 1. Numbers that reproduced exactly — left untouched

These were checked and are correct as written. Most of the manuscript's arithmetic is sound.

| Quantity | Manuscript | Recomputed |
|---|---|---|
| PCReg batch~biology Spearman r | −0.159 | −0.1592 |
| … its p value | 3.7 × 10⁻¹⁴ | 3.73 × 10⁻¹⁴ |
| Best approaches, PCReg batch median / MAD | 0.871 / 0.122 | 0.8712 / 0.1221 |
| Best approaches, PCReg biology median / MAD | 0.820 / 0.063 | 0.8195 / 0.0627 |
| Mann–Whitney best vs rest, PCReg batch | 0.0063 | 6.26 × 10⁻³ |
| S0 / 01_raw / strict / post0 PCReg RNA_BATCH | 0.226 | 0.226495 |
| … equivalent share of PCA variance | 77.4 % | 77.35 % |
| 14_qsmooth PCReg median / MAD | 0.208 / 0.098 | 0.2079 / 0.0983 |
| Strategy PCReg biology medians, D / K / S0 | 0.939 / 0.925 / 0.883 | 0.9394 / 0.9248 / 0.8829 |
| C strategy PCReg batch median | 0.872 | 0.8717 |
| J strategy PCReg batch / biology medians | 0.529 / 0.745 | 0.5286 / 0.7451 |
| 33_amdbnorm completed runs | 14 of 84 | 14 of 84 |
| Slow-decay methods, PC1 / PC2 variance | 17.3–25.3 % / 11.3–15.3 % | 17.34–25.34 / 11.33–15.29 |
| Intermediate 8 methods + Best, PC1 variance | 26.2–43.3 % | 26.21–43.34 |
| Highest PC1 variance, 11_harmony / 27_dwd | 79.9 / 79.5 % | 79.93 / 79.47 |
| Best group PC1/PC2 variance and R² | 37.9, 11.6 / 22.9, 15.2 % | 37.90, 11.56 / 22.93, 15.17 |
| 14_qsmooth PC1/PC2 variance and R² | 53.7, 13.5 / 90.8, 67.1 % | 53.68, 13.55 / 90.85, 67.06 |
| 01_raw PC1/PC2 R² | 64.8, 65.9 % | 64.75, 65.87 |
| Mann–Whitney best vs rest, iLISI / cLISI | 2.0 × 10⁻⁷ / 0.80 | 2.03 × 10⁻⁷ / 0.795 |
| 10_mnn iLISI median / MAD | 1.72 / 0.209 | 1.7238 / 0.2093 |
| All approaches iLISI median / MAD | 1.16 / 0.103 | 1.1616 / 0.1032 |
| 14_qsmooth iLISI median / MAD | 1.07 / 0.032 | 1.0666 / 0.0323 |
| cLISI biology, K / D / J medians | 1.07 / 1.10 / 1.62 | 1.0735 / 1.1005 / 1.6209 |
| iLISI ~ cLISI Spearman r, p | 0.527, 7 × 10⁻¹⁶⁰ | 0.5270, 7.04 × 10⁻¹⁶⁰ |
| … per strategy, significant range and median | 0.374–0.815, 0.617 | 0.3744–0.8147, 0.6171 |
| … not significant in | G only | G only (FDR 0.069) |
| 10_mnn tSNE entropy median / MAD | 0.179 / 0.025 | 0.1794 / 0.0250 |
| 14_qsmooth tSNE entropy median / MAD | 0.0178 / 0.0086 | 0.01778 / 0.00860 |
| tSNE entropy, K / G medians | 0.011 / 0.015 | 0.0111 / 0.0150 |
| Best approaches, KS within-batch D median / MAD | 0.445 / 0.041 | 0.4446 / 0.0409 |
| C strategy KS within / between D | 0.439 (0.015) / 0.332 (0.052) | 0.4395 (0.0151) / 0.3315 (0.0515) |
| 20_shambhala max / median expression | 555004.7 / 1359.6 | 555004.7 / 1359.60 |
| 19_tdm median / max expression | 75.1 / 568.9 | 75.07 / 568.85 |
| 28_npn median expression | −0.01 | −0.010 |
| Remaining methods, median expression range | 1.90–7.08 | 1.902–7.077 |
| Lowest minimum expression (13_fsmvn) | −40.6 | −40.642 |
| Best approaches, expression minima by method | −10.8 to −4.98 (SVA), −8.07 to 0 (FSQN R), −19.4 (FSMVN), −6.25 (AMDBNorm), 1.61–2.44 (MNN) | all confirmed |
| Best approaches, maximum expression range | 12.6–28.6 | 12.553–28.582 |
| Methods 'good' by LISI | 6, named | 6, same names |
| Best approaches above kBET 0.10 | 5 of 15, all SVA | 5 of 15, all 04_sva (C and K) |
| MNN best approaches, LISI range | 1.9–2.1 | 1.899–2.046 |
| C strategy high-kBET group, LISI ceiling | below 1.4 | 1.239–1.380 |
| Methods with ≥ 5 approaches above kBET 0.1 | 04_sva, 10_mnn | 04_sva (10), 10_mnn (9); next 11_harmony (4) |
| Best group rank by kBET RNA_BATCH | third | third (0.0987, after 22_tmm and 23_vst) |
| Harshness panel A: low tier best | 11 of 14 strategies | 11 (exceptions C, G, J) |
| Harshness panel B: high tier worst | 9 strategies | 9 |
| Harshness panel C: low / medium best | 6 / 8 | 6 / 8 |
| Harshness panel D: low / medium best | 10 / 4 | 10 / 4 |
| Harshness panel E: low tier worst | 12 strategies | 12 |
| Harshness panel F: high tier best | 13 of 14 | 13 |
| Best group composite score | ~0.6 | 0.6019 |
| Global distance contribution to best group | 0.35 | 0.3598 |
| Methods ranked 3rd–5th by composite | 33_amdbnorm, 28_npn, 10_mnn | same, 0.5752 / 0.5736 / 0.5709 |
| G strategy GPL570 sample count | ~800 of 2801 | max n_samples in G = 2,801 |

---

## 2. Numbers that did not reproduce — corrected

| # | Location | As written | As recomputed | Cause |
|---|---|---|---|---|
| 1 | PCReg §, CI | 95 % CI −0.21, **−11** | −0.20 to −0.11 | typographical |
| 2 | PCReg §, ComBat | PCReg **0.357 – 0.465** | median 0.568, range 0.357–0.823 | upper bound not in the data |
| 3 | PCReg §, saturation | 33_amdbnorm **and 13_fsmvn** both exactly 1.0000 in every run | only 33_amdbnorm (14/14); 13_fsmvn median 1.0000, min 0.9967 | 13_fsmvn is not pinned |
| 4 | PCReg §, classes | D and K have **4** classes | 4 in every D run and in 163 of 164 K runs | one K run has 2 |
| 5 | PC profile | max R² **0.0013, 28_npn PC1** | 0.0024, 07_pycombat PC2 | wrong cell |
| 6 | PC profile | **14** of 31 methods, PC1 R² below later PCs | 19 of 31 | undercount |
| 7 | PC profile | 01_raw PC2 variance **9.8 %** | 9.73 % | rounding |
| 8 | Global §, quality | **10** of 31 methods batch > biology | 12 of 31 | undercount |
| 9 | Global §, optimum | 5 methods at PCReg **exactly 1** | mean ≥ 0.999; only 33_amdbnorm exactly 1.0000 | overstated |
| 10 | Imputation | softimpute **7–10 %** better | +1.7 to +9.7 pp (mean 4.8); KNN also beats strict by ~2 pp | overstated |
| 11 | Strategy floors | C > **0.62**, G > **0.55**, H > **0.4** | 0.76, 0.72, 0.46 | all three low |
| 12 | 16_fsqn_r | 0.77 (G), 0.6 (H), 0.84 mean, **0.11** (K) | 0.76, 0.58, 0.83, 0.08; also 0.30 in F | rounding + F omitted |
| 13 | Post-removal | 22_tmm **0.83**; 25_angel better **without** post-removal (0.77) | 22_tmm 0.70 → 0.88; 25_angel improves *with* it (0.783 → 0.792); 12_scanorama is the only method post-removal harms | direction reversed |
| 14 | Strategy PC heat map | C and Best PC1 variance **20 and 22 %** | 30.4 and 37.9 % | both low |
| 15 | Strategy PC heat map | G highest at **50 %** | 66.0 % | low |
| 16 | Strategy PC heat map | R² decay starts **0.27 / 0.22** | 0.288 / 0.229 | rounding |
| 17 | Strategy PC heat map | **8** of 14 strategies, PC1 R² < PC2 | 10 of 14 | undercount |
| 18 | DSC | only **2 of 15** best approaches in the lower half | all 15 below the median DSC of 0.962; MNN's four at the boundary (0.781–0.957) vs FSQN R (0.0013–0.0098) | claim inverted |
| 19 | tSNE dispersion | 11_harmony 0.55–0.75 vs expected **1.1** (K) and **1.0** (J) | 0.55–0.78 vs K median 0.87; 0.62–0.68 vs J median 0.81 | reference values high |
| 20 | Post-removal, G | **0.7–0.9 → 0.9–1** PCReg | median 0.78 → 0.88 | range vs median |
| 21 | ASW | **K** worst | G worst (0.165), K second (0.078) | wrong strategy |
| 22 | ASW | G zone **−0.05 – 0.3**, PCReg **0.68 – 1** | 0.02–0.34, 0.65–1.00 | rounding |
| 23 | ASW | top methods 02_median_scaling and **11_harmony** | 02_median_scaling (−0.286) and 33_amdbnorm (−0.276); 11_harmony is fifth | wrong method |
| 24 | tSNE dispersion peaks | **0.26 and 1.01** | 0.24 (13_fsmvn) and 1.00 (27_dwd) | rounding |
| 25 | Missing values, samples | **19** clean / **8** at 0.44–2.3 % / **4** at 26–67 % | 18 / 9 at 0.003–1.4 % / 4 at 30.2–38.1 % | all three tiers |
| 26 | Missing values, genes | **19** clean / **11** at 0.05–33.6 % | 18 clean / 10 at 0.004–2.41 % / 15_fsqn_py 13.0 % / 17_quantile 16.2 % | tiers merged |
| 27 | Expression outliers | **5.08 × 10⁸ and 1.69 million** maxima | those are the mean standard deviations; the mean maxima are 1.46 × 10¹¹ and 2.76 × 10⁸ | wrong column |
| 28 | Expression outliers | 99th percentiles 18.5 and 17.9 | 17.9 (inmoose) and 18.5 (combat_seq) | methods swapped |
| 29 | Expression minima | **20** of 31 methods below zero | 19 of 31 | overcount |
| 30 | Best expression | median **2.89**–6.70 | 2.63–6.70 | low end |
| 31 | kBET vs raw | **3** methods better, **14** worse | 8 better, 22 worse (01_raw mean 0.027) | undercount |
| 32 | kBET by platform | above 0.1 for all but 36_explobatch; **28 of 31** | 27 of the 29 methods for which it is defined; 05_combat also below | undefined for 22_tmm, 23_vst |
| 33 | PCReg = 1 group | named 14_qsmooth, 16_fsqn_r, 06_combat_seq | the 198 such approaches come from 03_limma, 07_pycombat, 13_fsmvn, 21_harmonizr, 28_npn, 33_amdbnorm; 98.5 % below kBET 0.1 | wrong methods |
| 34 | KS fraction significant | **15** of 31 below 01_raw | 29 of 31 (01_raw is second worst at 0.948) | badly undercounted |
| 35 | KS fraction significant | above 0.7 for all but 22_tmm and 23_vst; "70–80 % of cohorts" | below 0.7 for ten methods (0.173–0.691); the best approaches still leave 56.0 % | both wrong |
| 36 | Graph connectivity | best > 0.8 / > 0.65 | 0.832–1.000 / 0.688–1.000 | imprecise |
| 37 | Graph connectivity | D and K at **0.53–0.65** | means 0.646 and 0.727 vs 0.799–0.854 elsewhere | range vs mean |
| 38 | Distance ratio | best **above 0.8** | 0.845–1.032, median 0.914 vs 0.757 overall | imprecise |
| 39 | Distance ratio | poorest: 14_qsmooth, **11_harmony**, 19_tdm | 27_dwd (0.508) and 14_qsmooth (0.531), both below 01_raw (0.566) | wrong methods |
| 40 | Distance ratio | S0 and K highest by biology (0.8–1.1), J lowest (0.5–0.8) | D 0.931, S0 0.921, K 0.912 highest; G 0.756 and J 0.760 lowest | D and G omitted |
| 41 | Watermelon | C lowest by batch (**0.12–0.25**), G highest (0.4–0.5) | C mean 0.335 (0.213–0.392), second to J (0.320); G 0.434 (0.372–0.471) | range and rank |
| 42 | Harshness panel B | low tier best in **8** strategies | 7 | miscount |
| 43 | Harshness panel F | worst: low in **5**, medium in **9** | low in 4, medium in 10 | miscount |
| 44 | Composite | next strategy C at **0.57** | 0.5778 | rounding |
| 45 | Composite | local contribution to best group **0.12** | 0.109 | rounding |
| 46 | Composite | local score C **0.9**, J **0.6**, rest **0.4–0.5**, G **0.3** | 0.095, 0.064, 0.047–0.052, 0.037 | out by a factor of ten |
| 47 | Composite | local impact **from 0.1 to 0.7** then to 0.11 | 0.083 → 0.072 → 0.106 | 0.7 is an increase, not a decrease |
| 48 | Metric groups | PCA group impact **0.02** | 0.017 across strategies, 0.030 across methods | one figure for two quantities |
| 49 | Metric groups | local groups **0.04** / **0.03** | 0.043 and 0.039 across strategies; 0.049 and 0.054 across methods | as above |
| 50 | Metric groups | remaining three add **0.04** | 0.036, 0.022, 0.019 across methods | aggregated |
| 51 | Metric columns | biology columns are **a quarter** of the metrics | 18 of 87, about a fifth | overstated |
| 52 | Composite summary | local metrics **10–15 %** of the score | 22 of 87 columns, 8.1–18.1 % of the composite | both bounds |
| 53 | Composite summary | batch metrics **¾** of the score | 57 of 87 columns, 60.7–67.4 % | overstated |
| 54 | Composite tail | **10 of 15** best approaches above 0.6; tail is **1–5 %** | 9 of 15; 150 of 2,234, 6.7 % | both |

---

## 3. Other corrections

**Figure renumbering.** The delivered artwork is one continuous `Extended Figure` sequence and
the document was three behind it: `Figure 6/7/8` → `Extended Figure 1/2/3`, and
`Extended Figure 1–10` → `Extended Figure 4–13`. 112 references rewritten; the legends now
read Extended Figure 1 to 13 in order. `Figure 3`, `Figure 4`, `Supplementary Figure 6/7/17`
point at the main article and were left alone.

**Legend panel letters.** `Extended Figure 6` (formerly Extended Figure 3) labelled three
different panels `(E)`; the second and third are now `(G)` and `(J)`, matching the order of
the panels described.

**Language.** Roughly 120 wording changes: `pefromance`, `scatteplot`, `PLATFROM_RNA`,
`malingnant`, `Surprizingly`, `consentingly`, `the fast that`, `DCS`, `inversed`, `reveal's`,
`residing it it`, `sameslow`, an unclosed parenthesis, and a large number of register and
agreement repairs (`revealed a supremacy of`, `there is no royal way`, `we build`,
`less cancers`, `analyzed ... by group`). US spelling was kept throughout, matching the
source.

**Internal contradiction.** One passage stated that only MNN mixes batches well and then
referred to "these three methods"; it now reads consistently.

---

## 4. New section

A closing **"Summary of metric trends"** was appended (7 paragraphs), organising the results
around five findings, each carrying its own recomputed figures:

1. Global and local metrics disagree; a saturated global metric is not evidence of success
   (five methods at PCReg ≥ 0.999 yield kBET < 0.1 in 98.5 % of their 198 approaches).
2. Batch variance is displaced rather than removed (19 of 31 methods, 10 of 14 strategies).
3. The mixing/preservation trade-off is real but modest and is dominated by class
   composition, not by method.
4. Harsher transformations do not win, except on distributional convergence — precisely the
   axis that cannot distinguish real from apparent success.
5. The composite score is decided by its smallest component: local metrics are 22 of 87
   columns and 8.1–18.1 % of the score but carry its largest between-group spread.

---

## 5. Reproducing this audit

```bash
source ~/venvs/collagen_3_11/bin/activate
cd ~/FL_harmonization/figures_for_article

python recompute_extended_metrics_260802.py                # all sections
python recompute_extended_metrics_260802.py snapshots      # the 260527 vs 260609 comparison
python apply_extended_metrics_edits_v2_260802.py           # rebuild the tracked-change docx
python ../.claude/skills/nar_review_tools.py validate \
    Harmonization_metrics_extended.docx \
    Harmonization_metrics_extended_260802_v2.docx
```

Validation on the delivered file: 673 revisions · 0 `w:t` inside `w:del` · 0 stray
`w:delText` · 0 duplicate revision ids · reject-all restores the original exactly ·
ALL CHECKS PASSED.

`apply_extended_metrics_edits_260802.py` and `Harmonization_metrics_extended_260802.docx`
(the first, narrower pass) are **superseded** by the v2 pair. The earlier pass used a
restricted row subset and consequently "corrected" four values that were in fact right
(the all-approach LISI median and MAD, the best-vs-rest Mann–Whitney p, and both LISI
correlation figures); it also corrupted `Supplementary Figure 6` into
`Supplementary Extended Figure 1`. Do not chain the two scripts.
