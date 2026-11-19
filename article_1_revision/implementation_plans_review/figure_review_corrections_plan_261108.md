# Figure-notebook review corrections — plan (2026-11-08)

Source of the requests: `daniil_review_261108.md` (Daniil's review of the figure notebooks
nb02–nb07, 2026-11-08). Review record: `gates_review_261102.md` §12 (12.1 answers, 12.2 decisions
D1–D5 — **answered by Daniil 2026-11-08**, 12.3 what to review next; 12.4–12.5 after the
implementation). Parent plan: `article_1_revision_implementation_plan_261029.md`.

## Overview

Daniil reviewed every figure notebook behind the Tier 1 / Tier 2 file list of
`gates_review_261102.md` §11.4. His requests fall into five kinds:

1. **Answers to questions** (no code): why FSQN R / FSMVN in strategy D show a low prediction
   score, why the λ = 0 line is missing in the local-batch panel, why nb07 lacks SVA, where the
   final embeddings are. The answers are in `gates_review_261102.md` §12.1; the code fixes they
   imply are in this plan.
2. **Figure fixes per notebook** (nb03, nb04, nb05, nb06, nb07): palettes, overlapping labels,
   messy bands, bar plots instead of scatter plots, spread of the random baseline with
   empirical p-values, panel sizes that fill the page (read from Figma, D2).
3. **One metric removed from the paper**: "agreement with batch-free fold changes" (S17a) is a
   new metric; Daniil does not want it ("we already simplified the metric space into the 22
   medoids"). It leaves the figures, Supplementary File 2 and the gradient statistics.
4. **Text**: define and justify the Pareto front (with a DOI citation); say how the error bands
   of the gradient were made; say why S17a and S17f both exist; new legends for S16–S18;
   **every new statistical test and methodology change described in the Methods** (item 9h);
   "regret" renamed **"decrease"** in the leave-cohort-out plots and the text that describes them.
5. **A consistency review by agents**: one reviewer agent checks that palettes, notation,
   names and conventions agree across all figures; then a `/brainstorm` with three agents
   acting as peer reviewers of a bioinformatics journal judges whether each figure's message is
   clear and simple. Mechanical findings are fixed directly; content findings wait for
   Daniil's word (D5).

Key design decisions:

- **The removed metric leaves the statistics, not only the figure.** r13 runs Benjamini–Hochberg
  over every tested arm × score row; the four fold-change rows per arm are in that family. Removing
  them from `r13.SCORES` shrinks the family (16 → 12 scores × 14 arms) and can move the FDR count
  "43 of 78". r13 → r45 are re-run and the new count is reported as it comes out.
- **The random baseline becomes a distribution, not an expected value.** In leave-cohort-out the
  "random method" is today one number per fold (expected rank, expected hit share, expected
  decrease). The random rank of one draw is uniform on 1…n (n = test runs of the fold), so its
  mean, SD and the exact probability P(random rank ≤ observed rank) = observed rank / n are known
  without simulation. Combined over the folds of a scenario we use a Monte Carlo of 100,000
  draws (sum of ranks, number of hits, mean decrease; fixed seed), giving an empirical p per
  scenario, BH-FDR over the scenarios of one panel. For the decrease the random distribution is
  the decrease of every test run of the fold (the per-run test scores already exist in
  `output/wp7/v1_scores.parquet`). All of it is described in the Methods (item 9h).
- **"Decrease", not "regret" (Daniil 2026-11-08).** In every leave-cohort-out plot and in the
  text that describes those plots, the quantity "score of the best approach on the test part
  minus score of the chosen approach" is called the **decrease** ("regret is emotional, decrease
  is technical"). Internal names stay: column `regret` in `v1_fold_results.tsv`, file
  `figS18c_v1_regret.*`, tests table `nb05_v1_regret_tests.tsv`, numbers.json keys
  `v1_regret_*` (internal labels never reach a publication).
- **New citations as DOI (Daniil 2026-11-08, standing rule).** Any citation added to the
  manuscript or the letter is written in the text as "(DOI: …)"; Daniil replaces it with the
  Mendeley field. Every DOI is checked on Crossref before it is written.
- **No new compute on the pods.** Every fix uses existing tables or caches. Only nb06's
  per-approach distributions stream 22 harmonized and 12 unharmonized matrices from S3
  (≈ 30–40 min on JupyterHub).
- **Nothing grows** (r90): S17 loses two panels, S18 keeps three, the all-cohort S2 is drawn for
  Daniil to decide (D3), the per-approach distributions and the final-selection embeddings are
  internal review material; the Methods additions of 9h are rewrites of existing paragraphs.

## Background / reference data (read from the tables during the writing)

| Question | Data (file) |
|---|---|
| D: FSQN R / FSMVN prediction | `output/wp4/selection_after_visual_check.tsv`: 3-class N (shown in Figure 6C/D) FSQN R KNN 0.556, FSMVN KNN 0.534; the gate for D is DLBCL vs FL (N2, decision 2026-11-03): FSQN R 0.645, FSMVN 0.651, unharmonized D KNN 0.622, permutation null 0.470 / 0.472 (p = 0.0099) |
| D: why on the front | batch removal (axis mean) FSQN R 0.500, FSMVN 0.500 = the highest of D (ComBat 0.437 / 0.440); Global batch scaled 0.998 / 1.000; diagnosis retention 0.408 / 0.394 vs ComBat 0.456 → the two ends of D's front |
| Local-batch anchor lines | `output/wp9/nb03_four_score_anchors.tsv`: local batch (scaled) median over all arms = 0.0288 at λ = 0 **and** at λ = 1 → the two dashed lines coincide; λ = 1 is drawn last and hides λ = 0 |
| Fold-change metric | `r13.SCORES` holds `gt_rho_*`, `gt_slope_*` (4 per arm); not in the 78 trends of r45 (6 scores × 13 tested arms) but in the BH family; numbers.json has 56 `gradient_at*__*__gt_*` keys, none used in the text; Supplementary File 2 defines it (`r40` lines ≈ 157–167); `PUBLICATION_NAMES["gt_logfc"]` |
| Gradient error bands | nb04 `SPREAD = "sd"`: mean ± SD over the 3 replicate draws per λ (capped designs); not confidence intervals. The only CIs are the slope CIs of S17b (OLS) and the Spearman CIs of the Methods |
| S17c | `output/wp1/strategy_v_vs_best_scores.tsv`, 14 strategies, grey dots, labels by `annotate` (overlap) |
| Leave-cohort-out | `output/wp7/v1_fold_results.tsv` (40 rows = 4 scenarios × 5 folds × 2 roles), `v1_scores.parquet` (per test run); random role = expected values today |
| "Regret" in publication sources | figure text of `figS18c_v1_regret` (nb05 cell 19); `r50_stage_b_text.py` ≈ 321 (Results: "its regret was lower than that of a random method"), ≈ 1009 (S18 legend: "(C) Regret on four scores"); `r46_review_figure_pdfs.py` ≈ 92 (alt text); `figures_svg/PLACEMENT.md` S18c row; existing tests table `output/wp9/nb05_v1_regret_tests.tsv`, keys `v1_regret_fdr__{panel}` (r45 ≈ 354) |
| S18c names | `batch_removal` = mean of scaled Global batch and Local batch bars; `biology_retention` = mean of scaled Global and Local diagnosis bars (`revision_lib` ≈ 1013) |
| Pareto citation | Deb K, Pratap A, Agarwal S, Meyarivan T (2002) A fast and elitist multiobjective genetic algorithm: NSGA-II. IEEE Trans Evol Comput — **DOI 10.1109/4235.996017** (checked on Crossref 2026-11-08). Deb 2001 (Wiley book) has no DOI |
| Figma page size (D2) | file `t8bFgusleBEwB9ht7rORCH` ("FL-harmonization-article"), node **761-28** (link in `daniil_review_261108.md`, nb05 paragraph); the Figma connector needs Daniil's login (OAuth callback fails on the pod: paste the address-bar URL into `complete_authentication`); quota ≈ 15 calls per session |
| nb07 | `output/wp9/nb07_selected_approaches.tsv` (round 1, 53 front members) includes SVA in K and C; their PDFs are `figures_svg/g2b_review/ffpe_only_*.pdf`, `rnaseq_only_*.pdf`. The notebook was last saved in round 2 (`REVIEW_ROUND = 2`, empty selection), which is why it shows nothing. All 22 accepted approaches have a cached embedding (`cache/nb07/*__post0.pkl`, + `post1_kept.txt` for the 8 post-removal ones) |
| nb06 | per-cohort histograms of all cohorts × 3 modes already cached (`output/wp9/figS2_cohort_histograms.parquet`); S2 shows 30 of them |

## Decisions (answered by Daniil 2026-11-08, `gates_review_261102.md` §12.2)

| # | Question | Decision | Consequence in this plan |
|---|---|---|---|
| D1 | Rename the two combined axes ("Batch removal" / "Diagnosis retention" = means of the global and local bars) | **Rename everywhere**: "Batch mixing (global + local mean)", "Diagnosis retention (global + local mean)" | items 2b, 3, 6f, 9g, 11, 12 |
| D2 | Page size the panels must fill (Figma node 761-28) | **Read it from Figma**; Claude says when to log in | first step of Phase 2: Claude starts the Figma login, Daniil logs in, one read of node 761-28 (+ its child frames) → slot table (item 13) |
| D3 | Full S2 (all cohorts): replace the 30-cohort S2 or internal? | **Draw it; Daniil looks and decides** | item 7a draws it; PLACEMENT / r46 / S2 legend unchanged until his word; question listed in §12.5 |
| D4 | Figure 6C/D prediction column = gate value + open marker for the unharmonized value | **Ok** | item 4a |
| D5 | Agent-review findings that change content: only after Daniil's word? | **Yes**; mechanical fixes applied directly | item 14d |
| Tag | New date tag for the stage-B docx? | Daniil has not commented on `…_stageB_261108.docx`; he will comment on **the most recent** docx after these edits | item 15: tag = implementation date (overwriting `…_261108` is allowed if it is the same day); §11.5 text pass moves after this plan |

## Files to change

### 1. `r13_gradient_stats.py` — drop the fold-change metric from the statistics

**1a. `SCORES` (≈ line 79).** Before:

```python
    "batch_removal",
    "biology_retention",
    "gt_rho_DLBCL_vs_FL",
    "gt_rho_Tumour_vs_Normal B",
    "gt_slope_DLBCL_vs_FL",
    "gt_slope_Tumour_vs_Normal B",
)
```

After:

```python
    "batch_removal",
    "biology_retention",
)
# Agreement with batch-free fold changes (gt_*) is computed by r12 but not analysed:
# Daniil 2026-11-08 keeps the metric space at the 22-metric panel + L / N.
```

**1b. Module docstring (line 11)** — remove "plus the agreement with batch-free fold changes
(gt_rho_*, gt_slope_*)"; state the BH family = 12 scores × tested arms.

Why: the metric leaves the paper; it must also leave the FDR family, or the published q-values
would depend on a metric the paper no longer has.

### 2. `revision_lib.py`

**2a.** `PUBLICATION_NAMES["gt_logfc"]` stays (r12 still writes the columns into the internal
parquet) but gets the comment "internal; not in publications (2026-11-08)".

**2b. (D1)** `PUBLICATION_NAMES["batch_removal"]`: `"Batch removal"` → `"Batch mixing (global +
local mean)"`; `"biology_retention"`: `"Diagnosis retention"` → `"Diagnosis retention (global +
local mean)"`. Short forms for axis labels: new keys `batch_removal_short` = "Batch mixing",
`biology_retention_short` = "Diagnosis retention". New key `regret` = "Decrease" (leave-cohort-out
quantity, used by nb05 and r46).

**2c.** Tests in `tests/test_revision_lib.py`: no publication name contains "removal" except the
strategy names (guards D1); no publication name contains "regret" (guards the decrease rename).

### 3. `r40_build_supplementary.py` — Supplementary File 2

Remove the metric-definition row "Agreement with batch-free fold changes" (≈ lines 157–167).
Rename the two axis rows per D1. Re-run → `output/wp10/Supplementary File 2.xlsx`.

### 4. `nb03_four_scores_and_tree.ipynb`

**4a. Cell 15 (Figure 6C/D), prediction column (D4).** The column `N` → `N_gate`
(`selection_after_visual_check.tsv` already holds `N_gate`, `N_raw`, `gate_N_classes`). Column
title "Cross-batch prediction (DLBCL vs FL for D; 3 classes otherwise)". Open grey marker at
`N_raw` on the same row, joined to the filled dot by a thin line (before → after). Cell 14 adds
`N_gate`, `N_raw` to the saved table `nb03_front_four_scores.tsv`. Gradient anchors for the
prediction column use `N` (all gradient designs are 3-class) — legend says so.

**4b. Cell 15, coinciding anchors.** Draw λ = 0 dashed (blue, width 1.6, under) and λ = 1 dotted
(red, width 1.0, over) so that coinciding lines show both colours; when |λ0 − λ1| < 0.01 add the
note "λ = 0 and λ = 1 medians coincide" under the panel. Before:

```python
    ax.axvline(anchor["lambda0"], color=ANCHOR_COLORS["lambda0"], linestyle="--", linewidth=0.9)
    ax.axvline(anchor["lambda1"], color=ANCHOR_COLORS["lambda1"], linestyle="--", linewidth=0.9)
```

After:

```python
    ax.axvline(anchor["lambda0"], color=ANCHOR_COLORS["lambda0"], linestyle="--", linewidth=1.6, zorder=1)
    ax.axvline(anchor["lambda1"], color=ANCHOR_COLORS["lambda1"], linestyle=":", linewidth=1.0, zorder=2)
    if abs(anchor["lambda0"] - anchor["lambda1"]) < 0.01:  # e.g. local batch: both medians 0.029
        ax.text(0.5, -0.12, "λ = 0 and λ = 1 medians coincide", transform=ax.transAxes,
                ha="center", fontsize=GLOBAL_FONT_SIZE - 3)
```

**4c. §7 notes** — record the two answers (D prediction, coinciding anchors) in plain words.

**4d. Panel size** from the Figma slot table (`PANEL_SLOTS_MM`, item 13) for 6B, 6C/D, 6F,
S14a–c.

### 5. `nb04_confounding_gradient.ipynb`

**5a. Cell 4 `S17_SCORES`** — remove `gt_rho_DLBCL_vs_FL`, `gt_rho_Tumour_vs_Normal B`; S17a
becomes a 3 × 2 grid (L, N, four scaled bars). **Cell 7** — remove the two `SCORE_NAMES` entries.
**Cell 18** — `plt.subplots(3, 2, …)`.

**5b. Cell 24 (S17e)** — both halves without the min–max band (`show_band=False` on the left
too; remove the `show_band` parameter); left = selected methods (thick lines), right = all
arms; the two halves share the y axis and now differ only in the set of lines.

**5c. Cell 32 (S17c)** — colour each strategy dot by `strat_pal` (copied in §0c from nb01; the
notebook gets the full 14-entry dict), dot size 50, edge #333333; labels with the strategy
**code** only (S0, A … K; the legend maps code → name, colours as in Figure 2A); label
placement by `adjustText` if installed in `collagen_3_11`, else a fixed offset table
`S17C_LABEL_OFFSETS` checked by eye; assertion that no two label boxes overlap (bounding
boxes from the renderer).

**5d. §1b markdown + legend handle** — the band is named "mean ± SD of 3 replicate draws" (not
"confidence interval") in the notebook, the figure legend and the S17 legend (item 9c).

**5e. Panel sizes** from the Figma slot table (item 13).

**5f. §7 notes** — S17a vs S17f (item 9c), removal of the fold-change metric.

### 6. `nb05_robustness_and_v1.ipynb`

Every statistical choice of this item is written into the Methods by item 9h.

**6a. Cell 9 (S16a)** — bars at alpha 0.25 of the scenario colour (faint), dots full colour
on top; error bar = SD over the six scenarios per variant (the bar is the mean).

**6b. Cell 11 (S16b)** — figure height ÷ 2, bar height 0.35 (from 0.8), horizontal layout kept;
x axis shared across panels so bars compare directly.

**6c. Cell 13 (load)** — add a random-baseline table `random_rank_baseline` per fold:
`n_test_runs`, `expected_rank = (n + 1) / 2`, `sd_rank = sqrt((n² − 1) / 12)`,
`p_rank = rank_on_test / n` (exact probability that one random method ranks as well or better),
top-k probabilities `k / n`; decrease of every test run from `output/wp7/v1_scores.parquet`
(random decrease distribution per fold). Saved as `output/wp9/nb05_v1_random_baseline.tsv`.

**6d. Cell 15 (S18a) → bar plot.** Per scenario panel, per fold: coloured bar = rank of the
chosen method on the test part (colour = `method_pal`), grey bar next to it = random method,
mean ± SD (error bar). Fold not evaluable / method failed on the test part → no bar, vertical
text "not evaluable" / "failed" in the slot. Panel title: scenario + combined empirical p
(Monte Carlo, 100,000 draws of one random rank per fold, fixed seed: P(Σ random ranks ≤ Σ
observed ranks)) and BH-FDR over the 4 scenarios. Saved: `output/wp9/nb05_v1_rank_tests.tsv`.

**6e. Cell 17 (S18b).** Bars = observed hit share per scenario; grey bar = random expected
share with error bar = SD of the share over the folds (Poisson-binomial: sqrt(Σ p(1 − p)) / folds);
above each pair the exact empirical p = P(random hits ≥ observed hits) (Poisson-binomial
distribution of the per-fold probabilities k / n), BH-FDR over 5 groups × 2 panels; stars by the
standard rule. Saved: `output/wp9/nb05_v1_hit_tests.tsv`.

**6f. Cell 19 (S18c), "decrease" instead of "regret".** Bar = mean decrease ± SD, chosen vs
random, where random = the decreases of all test runs of the evaluable folds (not one expected
value per fold). Test: two-sided Mann–Whitney chosen vs random runs and the Monte Carlo
empirical p of the mean decrease (100,000 draws, fixed seed); BH-FDR over the four panels; both
shown, stars from the Mann–Whitney q. Panel titles per D1, global / local named:
"Decrease, batch mixing (global + local mean)", "Decrease, diagnosis retention (global + local
mean)", "Decrease, marker correlation (local, within cohort)", "Decrease, cross-batch
prediction". y-axis label "Decrease vs the best approach on the test part"; legend handles
"chosen approach" / "random approach". No figure text says "regret" (checked in item 14a).
Saved: the existing `output/wp9/nb05_v1_regret_tests.tsv` gets the Monte Carlo columns
(file name internal, kept).

**6g. Panel sizes** from the Figma slot table (item 13).

### 7. `nb06_merged_distributions.ipynb`

**7a. New §5b "Supplementary Figure S2, all cohorts" (D3: draw, Daniil decides).** All cohorts
of the cached histograms, ordered as in S2 (platform, then size); two large columns, each three
narrow mode panels (strict, KNN, softImpute) → 6 panel columns × ⌈n/2⌉ rows; ridge height
reduced, font ≥ 6 pt at page size. Output
`figures_svg/figS2_merged_distributions_all_cohorts.{svg,pdf,png}`. PLACEMENT, r46 and the S2
legend are **not** changed: the figure is shown to Daniil in the §12.4 digest; if he decides to
replace, a follow-up points PLACEMENT / r46 / the S2 legend ("all N cohorts") to the new file.

**7b. New §7 "Before / after distributions of the 22 selected approaches" (internal).**
Switch `MAKE_APPROACH_DISTRIBUTIONS = True`; per accepted approach: stream the harmonized matrix
(`rl.main_benchmark_matrix_key`, post0 or post1) and its unharmonized counterpart (same strategy
and imputation, `01_raw`), per-cohort histograms (same bins), cached in
`output/wp9/nb06_approach_histograms.parquet`; one page per approach: ridgelines per cohort,
unharmonized (grey outline) under harmonized (platform colour). Output:
`review_extras/approach_distributions/<scenario>__<approach>.pdf` + one merged PDF
`review_extras/approach_distributions/all_22_approaches.pdf`. Not in `figures_svg/`, not in
PLACEMENT, not in r46 — "for my interest".

### 8. `nb07_selected_approaches_embeddings.ipynb`

**8a. Cell 4** — `REVIEW_ROUND` accepts `"final"`: the selection is the 22 accepted rows of
`selection_after_visual_check.tsv`; output folder `review_extras/final_selection_embeddings/`;
the round-2 assertion "nothing to draw" applies only to round 2.

**8b.** Re-run with `REVIEW_ROUND = "final"` (cache only, no new embedding: all 22 are cached) →
one PDF per scenario × embedding (PCA / UMAP / tSNE), unharmonized | harmonized, colour by
batch, diagnosis, platform. Table `output/wp9/nb07_figure_files_final.tsv`.

**8c. §5 markdown** — where each round's PDFs are (`g2b_review/` round 1 incl. SVA in K and C,
`g2b_review_round2/`, `review_extras/final_selection_embeddings/` final).

### 9. `r50_stage_b_text.py` — text

**9a. Pareto front, Methods (rewrite of the existing sentence ≈ line 854, no new paragraph).**
Definition: "an approach is on the Pareto front of its scenario when no other candidate is at
least as good on both axes and better on one (DOI: 10.1109/4235.996017)"; justification: the two
axes conflict (removing more batch signal removes diagnosis signal, Figure 6 gradient panel), a
weighted sum would need a weight that no data justify, and the front returns every best
trade-off instead of one winner; ordering inside the front by local batch mixing (as in the
rule). The citation is Deb et al. 2002 (NSGA-II, non-dominated sorting), written as a DOI for
Daniil to replace via Mendeley (standing rule). The DOI is plain text, outside any Mendeley
field, so the stage-B citation guard is not touched.

**9b. Results first mention** (≈ line 54) — "a Pareto front (approaches that no other approach
beats on both batch mixing and diagnosis retention)".

**9c. S17 legend + one Results sentence:** S17a = every one of the 14 methods on six scores
(overview, with uncapped and single-diagnosis controls); S17f = only the methods of the final
selection on the same scores, without controls, on a scale where their differences are
visible — "S17a shows where the selected methods sit among all methods; S17f compares the
selected methods with each other". Bands: "mean ± SD of three replicate draws per λ".
S17e: "medians over the three replicates".

**9d. Methods, gradient statistics** — one sentence on the bands (SD over replicates, not
CIs) and on the slope CIs (OLS 95 % CI, S17b); the BH family now 12 scores × tested arms; the
fold-change sentence, if any in stage A, deleted.

**9e. S16 / S18 legends** — rewritten for the bar plots, the grey random bars ± SD, empirical
p (exact per fold, Monte Carlo per scenario), Mann–Whitney for the decrease, BH-FDR; D1 names;
S18 legend panel C: "(C) Decrease vs the best approach on the test part, four scores" (was
"Regret on four scores", ≈ line 1009).

**9f. Figure 6 legend C/D** — prediction column = gate value; open marker = unharmonized.

**9g. D1 rename** in every REWRITE / REPLACEMENT that says "batch removal" for the axis
(Table 3 legend ≈ line 203, Methods ≈ 854, S17d legend, letter). **Decrease rename** in the
Results sentence ≈ line 321 ("its regret was lower than that of a random method" → "its
decrease was smaller than that of a random approach"); no "regret" left in any publication text.

**9h. Methods: every new statistical test and methodology change (Daniil 2026-11-08).**
Rewrite of the existing Methods paragraphs on robustness, leave-cohort-out validation and the
gradient (no new paragraph; r90 word / line totals must not rise), so that each item below is
stated with its test, its null and its multiple-testing family:

| Methodology change | Methods wording (content) | Source item |
|---|---|---|
| Robustness bars (S16a) | bar = mean over the six scenarios, error bar = SD | 6a |
| Random rank per fold | the rank of a random approach is uniform on 1…n; exact p = observed rank / n | 6c |
| Random rank per scenario | Monte Carlo, 100,000 draws of one random rank per fold, empirical p of the summed ranks; BH-FDR over the 4 scenarios | 6d |
| Hit rates | exact Poisson-binomial p of the number of hits (per-fold probabilities k / n); SD of the random share; BH-FDR over 5 groups × 2 panels | 6e |
| Decrease | definition (best test-run score minus the chosen approach's score); random = all test runs of the evaluable folds; two-sided Mann–Whitney + Monte Carlo p of the mean; BH-FDR over the four scores | 6f |
| Not-evaluable / failed folds | excluded from the tests, shown as text in S18a | 6d |
| Gradient bands and slopes | bands = mean ± SD of 3 replicate draws; slope CIs = OLS 95 %; BH family = 12 scores × tested arms (fold-change agreement no longer analysed) | 1, 9d |
| Pareto front | definition + justification + DOI | 9a |
| Figure 6C/D prediction | gate value (DLBCL vs FL for D, 3 classes otherwise), unharmonized value shown | 4a, 9f |

### 10. `r45_results_numbers.py`

Keys from the new nb05 tables: `v1_rank_p__{scenario}`, `v1_rank_q__{scenario}`,
`v1_hit_p__{k}__{scenario}`, `v1_hit_q__{k}__{scenario}`; the existing decrease keys
`v1_regret_fdr__{panel}` (Mann–Whitney q, ≈ line 357, internal name kept) plus a new
`v1_regret_mc_p__{panel}` (Monte Carlo p). Re-read `gradient_main_changes` after r13. Drop the
`gt_*` keys (r13 no longer writes them). Re-run → numbers.json.

### 11. `response_letter_draft.md`

Pareto definition sentence (with the DOI, standing rule) where the letter mentions the front
(lines ≈ 177, 216); the trend count if r13 moves it; the S18 statistics; D1 names; "decrease",
never "regret", if the letter mentions the leave-cohort-out loss.

### 12. `r46_review_figure_pdfs.py`

S17 titles / alt text (S17a 3 × 2, S17c colours), S18 alt text (bars, random ± SD, "decrease"
instead of "regret", ≈ line 92), new figure sizes. S2 entry unchanged until Daniil's D3 word.

### 13. `figures_svg/PLACEMENT.md` and the Figma page size (D2)

**13a. Figma read (first step of Phase 2).** Claude calls the Figma `authenticate` tool and
tells Daniil to log in; the localhost callback fails on the pod, so Daniil pastes the
address-bar URL, which Claude passes to `complete_authentication`. Then one metadata read of
node 761-28 in file `t8bFgusleBEwB9ht7rORCH` (and, in the same call where possible, its child
frames = the figure pages), ≤ 3 calls in total (quota). The frame sizes (px → mm) are saved in
`output/wp9/figma_page_slots_261108.tsv`.

**13b.** New column `slot (mm)` in `PLACEMENT.md`: width × height of every panel inside its full
figure page, from 13a; the notebooks read the slot from a copied dict `PANEL_SLOTS_MM`
(self-contained rule) and set `figsize` from it. The S18c row description says "decrease"
instead of "regret".

### 14. Consistency review by agents (after items 1–13)

**14a. Deterministic audit script `r98_figure_consistency.py` (new, Tier 2 check).** Parses
every figure notebook (nb01–nb08): palette dicts (`strat_pal`, `method_pal`, `imp_pal`,
`lymphoma_ontogeny_palette`, `rna_batch_palette`, `platform_palette`, metric-group palettes)
compared key by key with the canonical copies (nb01 for `strat_pal`, nb04 §0c for `method_pal`,
nb02 for the metric palettes); figure text in the SVGs (`svg.fonttype = none` keeps text) scanned
for internal labels, snake_case, non-canonical names of methods / strategies / scores (against
`PUBLICATION_NAMES`, `METHOD_DISPLAY_NAMES`, `STRATEGY_DISPLAY_NAMES`), the words "regret" and
"Batch removal" as an axis name, grey dots where a palette exists. Output
`output/wp14/figure_consistency.tsv` (figure, element, found, expected).

**14b. Reviewer agent (1, general-purpose).** Brief: the review PDFs, `PLACEMENT.md`, the audit
table, the palette rules of the project CLAUDE.md; task: list every contradiction in palettes,
notation (S0 · No removal, λ, V, ρ), names, axis directions, scales (scaled vs raw), legend
wording between figures; output `output/wp14/consistency_review_agent.md`.

**14c. `/brainstorm` with three agents as peer reviewers** of a bioinformatics journal
(Builder = reviewer sympathetic to the method, Adversarial critic = hostile reviewer,
Pragmatic analyst = handling editor): per main and supplementary figure, "is the visual message
clear and simple; what would you ask the authors to change". Saved
`brainstorm/figure_peer_review_brainstorm_<date>.md` and logged in `.brainstorm/` (skill rule).

**14d. Fixes (D5).** Mechanical findings (palette, label, name, overlap, size) applied in the
notebooks and re-run; content findings (drop / merge a panel, change a plot type) listed in
`gates_review_261102.md` §12.4 and applied only after Daniil's word.

### 15. Re-run chain

nb02 (only if a palette changes) → r13 → nb03 → nb04 → nb05 → nb06 → nb07 (final) → nb08 (if
the audit touches palettes) → r40 → r45 → `r50 --stage B --date <tag>` → r90 / r99 /
`nar_review_tools.py validate` → r60 draft → r46. Tag = the implementation date. Daniil has not
commented on `…_stageB_261108.docx` and will comment on the most recent docx after these edits,
so an implementation on 2026-11-08 overwrites the 261108 file and a later one writes a new tag;
§11.5 item 1 (his single Word pass) moves after this plan.

### 16. Documentation

`gates_review_261102.md` §12 (digest after implementation: 12.4 results, consistency findings,
the all-cohort S2 for the D3 decision; 12.5 what to review next; §11.4 file list updated: new
S18 / S17 panels, `review_extras/` as Tier 2, r98 + reports as checks); `CLAUDE.md`
(article_1_revision: run-order rows for r98 and nb07 final mode; gotchas: gt metric excluded,
random baseline as distribution, "decrease" not "regret" in publications, new citations as DOI,
Figma file / node of the page sizes); parent plan §19 pointer to this plan; project memory:
notebook_writing rule note (bar plots with error bars, random baseline with spread, empirical
p + FDR); the DOI rule is already in memory (2026-11-08).

## Files that do NOT need to change

| File | Why |
|---|---|
| Frozen files (`FROZEN_MD5.txt`) | nothing here touches them |
| `adjudication_rule_261029.md` | the rule already defines the front ("non-dominated set"); the text change is in the manuscript only; D1 renames the axes in publications, the frozen rule keeps its internal words |
| `r12_revision_metrics.py`, `output/wp6/gradient_metrics.parquet` | the fold-change columns stay in the internal metric table; they are only no longer analysed or shown |
| `r04_apply_rule.py`, selection tables | the selection does not change |
| `r22_v1_evaluate.py`, `output/wp7/v1_fold_results.tsv` | per-run test scores already in `v1_scores.parquet`; the random distribution is built in nb05; the internal column `regret` keeps its name |
| `nb01`, `nb02`, `nb08` | only if the audit (item 14) finds a contradiction in them |
| `daniil_review_261108.md` | Daniil's own file; answered in `gates_review_261102.md` §12 |

## Side effects and caveats

- **FDR family shrinks** (item 1): "43 of 78" may change; reported as it comes out, the text
  reads the number from numbers.json.
- **D1 rename touches the frozen-rule wording only outside the rule** (manuscript, letter,
  figures); the rule file keeps "batch removal" (frozen, MD5).
- **"Decrease" rename** reaches the S18c figure, the S18 legend, one Results sentence, r46 alt
  text and PLACEMENT; internal names (`regret` column, file names, numbers.json keys) stay, so
  r45 and the stage-B placeholders need no key change.
- **Methods rewrite (9h)** adds content without adding paragraphs; if r90 reports more words /
  lines than the baseline, older Methods sentences are shortened in the same paragraphs.
- **DOI in the text** is a placeholder for Mendeley; r99 must not flag it (it scans for internal
  labels, not DOIs) — checked in Phase 5.
- **S17 loses 2 panels**, S18 changes plot type; S16–S18 legends are rewritten → new tracked
  edits in stage B; r90 must stay PASS.
- **Stage-B tag**: same-day implementation overwrites `…_stageB_261108.docx` (Daniil has not
  commented on it).
- **nb06 §7 streams ≈ 34 matrices** (≈ 30–40 min; the home disk is slow); the histogram cache
  makes re-runs instant. The full S2 needs no S3.
- **Figma (D2)** needs Daniil at the keyboard for the login at the start of Phase 2; the quota
  (≈ 15 calls per session) allows the read; if the login fails, panels keep their size and
  `PLACEMENT.md` gets the slot column with "pending".
- The brainstorm and the reviewer agent cost tokens (4 agents, one round each); Daniil asked
  for them explicitly.
- `adjustText` may be missing in `collagen_3_11`; installing it needs Daniil's OK (pip, small,
  pure Python) — otherwise the fixed offset table.

## Verification commands

```bash
cd ~/FL_harmonization/article_1_revision
source ~/venvs/collagen_3_11/bin/activate
md5sum -c FROZEN_MD5.txt --quiet
python -m pytest tests/ -q                                   # existing + the D1 and "regret" name tests
python -c "import r13_gradient_stats as r; assert not any(s.startswith('gt_') for s in r.SCORES)"
python -c "import pandas as pd; s=pd.read_csv('output/wp6/gradient_slopes.tsv',sep='\t'); assert not s.score.str.startswith('gt_').any()"
grep -il "regret" figures_svg/figS18*.svg                   # expect nothing
grep -n -i "regret" r50_stage_b_text.py | grep -v "{{"       # expect nothing outside placeholders
grep -c "10.1109/4235.996017" r50_stage_b_text.py            # ≥ 1
python r98_figure_consistency.py && grep -c . output/wp14/figure_consistency.tsv
python r90_ledger.py Revised_manuscript/FL_harmonization_article_NARGAB_tracked_stageB_<tag>.docx
python r99_verify.py Revised_manuscript/FL_harmonization_article_NARGAB_tracked_stageB_<tag>.docx
grep -c "fold change" output/wp10/*.csv; python -c "import json; n=json.load(open('output/numbers.json')); assert not [k for k in n if '__gt_' in k]"
ls review_extras/final_selection_embeddings review_extras/approach_distributions output/wp9/figma_page_slots_261108.tsv
```

## TODO

Phase 0 — decisions
- [x] Daniil answers D1–D5 and the tag question (`gates_review_261102.md` §12.2, 2026-11-08)
- [x] Daniil approves this plan (`/implementation`, 2026-11-08)

Phase 1 — statistics and names
- [x] `r13_gradient_stats.py` — remove the four `gt_*` scores from `SCORES`; docstring (BH family)
- [x] Re-run r13; note the new `gradient_main_changes` (unchanged: 43 of 78; slope table 224 → 168 rows, FDR family 216 → 160 tested rows; no main trend flips)
- [x] `revision_lib.py` — `gt_logfc` comment; D1 names + short forms; `regret` → "Decrease"
- [x] `tests/test_revision_lib.py` — D1 name test, "regret" name test; run tests (91 passed; the D1 test covers the two combined axes — the global bar keeps its name "Global batch removal")
- [x] `r40_build_supplementary.py` — drop the fold-change row, D1 names; re-run r40 (also the two fold-change columns of the File 3 gradient sheet)

Phase 2 — Figma page size and figure notebooks
- [x] Figma login (Claude asks Daniil) → read node 761-28 → `output/wp9/figma_page_slots_261108.tsv` (node 761-28 = frame "Figure 4", 753 × 1150 px = 180 × 275 mm; 4 Figma calls, the page-level read was too large for the connector, so every figure uses this page)
- [x] `figures_svg/PLACEMENT.md` — slot column (D2); S18c row "decrease"
- [x] nb03 cell 14 — `N_gate`, `N_raw` in the saved table
- [x] nb03 cell 15 — prediction column = gate value + unharmonized marker (D4)
- [x] nb03 cell 15 — visible coinciding anchors + note
- [x] nb03 — panel sizes, §7 notes; run (fonts 7 / 6 pt at page size; 6F boxes resized)
- [x] nb04 — `S17_SCORES`, `SCORE_NAMES`, S17a 3 × 2
- [x] nb04 — S17e without bands on both halves
- [x] nb04 — S17c `strat_pal`, code labels without overlap (+ check) (adjustText 1.3.0 was installed; also used for the S17d front labels)
- [x] nb04 — band named "mean ± SD of 3 replicate draws"; panel sizes; §7 notes; run (S17 spans two pages: a–c, d–f)
- [x] nb05 — S16a faint bars + SD error bars; S16b flat, thin bars
- [x] nb05 — random baseline table (`nb05_v1_random_baseline.tsv`) (+ `nb05_v1_random_decreases.tsv`, per test run; mean checked against r22)
- [x] nb05 — S18a bar plot, text for not evaluable / failed, empirical p + FDR (`nb05_v1_rank_tests.tsv`) (FDR 0.072–0.98: none < 0.05)
- [x] nb05 — S18b random spread + exact empirical p + FDR (`nb05_v1_hit_tests.tsv`) (S0 top-1 3/5, FDR 0.006; all top-3 6/20, FDR 0.075)
- [x] nb05 — S18c "decrease": bars ± SD, random = all test runs, Mann–Whitney + Monte Carlo p, D1 / global-local names (Mann–Whitney FDR ≥ 0.38; Monte Carlo batch mixing p 0.017, FDR 0.066)
- [x] nb05 — panel sizes; run
- [x] nb06 — §5b full S2 (two columns × three modes); run; shown to Daniil for D3 (no PLACEMENT / r46 change) (r46 now matches the exact file name, so the all-cohort file never enters the S2 slot)
- [x] nb06 — §7 per-approach before / after distributions → `review_extras/approach_distributions/`; run (22 pages + merged PDF; 34 matrices streamed once, cache `nb06_approach_histograms.parquet`)
- [x] nb07 — `REVIEW_ROUND = "final"` mode; run → `review_extras/final_selection_embeddings/`; §5 markdown (18 PDFs, cache only)

Phase 3 — text
- [x] `r50_stage_b_text.py` — Pareto definition + justification + DOI 10.1109/4235.996017 (Methods rewrite, Results first mention)
- [x] `r50_stage_b_text.py` — S17a vs S17f sentence + S17 legend (bands, medians, 3 × 2)
- [x] `r50_stage_b_text.py` — Methods (9h): every new statistical test and methodology change, in the existing paragraphs
- [x] `r50_stage_b_text.py` — S16 / S18 legends; Figure 6 C/D legend; D1 names everywhere; "decrease" instead of "regret" (the leave-cohort-out Results paragraph rewritten to the new statistics: no test < 0.05 after FDR except S0 top-1; the abstract's "confirmed" left for Daniil, brainstorm R1)
- [x] `r45_results_numbers.py` — new S18 test keys (+ `v1_regret_mc_p__*`), drop `gt_*`; run (652 keys; `v1_rank_*`, `v1_hit_*`, `v1_hits_*`, `v1_regret_mc_*`)
- [x] `response_letter_draft.md` — Pareto (+ DOI), trend count, S18 statistics, D1 names, "decrease" (also the typed "11.6 %" replaced by its key; trend count unchanged)
- [x] `r46_review_figure_pdfs.py` — S17, S18 titles / alt text ("decrease"), sizes (+ exact-file lookup so the S2 slot keeps the 30-cohort file)

Phase 4 — consistency review by agents
- [x] `r98_figure_consistency.py` — write and run → `output/wp14/figure_consistency.tsv` (14 findings left: 13 metric code names in Figure 3 / S5, nb07 review-only palette)
- [x] Reviewer agent → `output/wp14/consistency_review_agent.md` (written inline: the agent call was refused by auto mode because the context-mode hook rewrites agent prompts)
- [x] `/brainstorm`, three peer-reviewer agents → `brainstorm/figure_peer_review_brainstorm_<date>.md` + `.brainstorm/` log (personas inline, same reason; `brainstorm/figure_peer_review_brainstorm_261108.md`, `.brainstorm/figure-peer-review.md`)
- [x] Apply the mechanical findings; list the content findings in `gates_review_261102.md` §12.4 (D5) (fixed: nb02 method colours, nb08 platform colours, diagnosis / batch / S0 names, prediction name, V grouping in 1E)

Phase 5 — rebuild and checks
- [x] Re-run chain (item 15) with tag = implementation date (261108; the 261108 docx had no Word comments)
- [x] `md5sum -c FROZEN_MD5.txt`, tests, r90 PASS, r99 0 FAIL, validator ALL PASSED; no "regret" in S18 SVGs / text; DOI present (91 tests; r99 first flagged S18 cited before S1 in the new Methods sentence → reworded)
- [x] r60 letter draft; r46 review PDFs

Phase 6 — documentation
- [x] `gates_review_261102.md` §12.4–12.5 digest (incl. the all-cohort S2 for D3); §11.4 file list updated
- [x] `CLAUDE.md` (article_1_revision) — run-order rows (r98, nb07 final), gotchas (gt excluded, random distribution, "decrease", DOI rule, Figma node)
- [x] parent plan §19 pointer; project memory (figure statistics rule)
