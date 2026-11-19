# Selection rule (adjudication hierarchy), version 1

**Status: FROZEN 2026-11-03 (gate G2).** Daniil approved the rule, answered every "[G2 choice]"
of the draft and the follow-up questions Q1 / Q2, and said "freeze" on 2026-11-03
(`gates_review_261102.md` §2.4, §3). The MD5 of this file is in `FROZEN_MD5.txt`; the file is
never edited again (an amendment is `adjudication_rule_261029_v2.md`). `r04_apply_rule.py` runs
only while this MD5 is listed. Nobody (Claude included) had seen which approaches this rule
selects when it was frozen. The picks
are first shown at gate G2b.

Inputs: `output/wp3/four_scores.parquet` (the 2,234 approaches of the analysis set,
`pct_samples_allNA < 5`) and the reduced panel `output/wp2/reduced_panel.tsv` (22 metrics, gate
G1).

---

## Step 1 — Gate L: marker correlation threshold

An approach passes when **L ≥ 0.7**. L = `mk_rho_mean_all_genes_narrow_set` is the mean per-gene
Spearman ρ of the 56 narrow-set marker genes, before vs after harmonization. 0.7 is the threshold
the submitted paper already used.

An approach without an L value is "not evaluable" and is not a candidate. Every approach of the
analysis set has L. The 84 Shambhala approaches (`20_shambhala`) take their L and N from the
blind-check rows of `shambhala_P0std_Q0std`, which hold the same matrices: the published metrics
agree exactly on all 84.

## Step 1b — Method failure: the approach returned its input

Two frozen methods catch their own failure and return the input matrix unchanged with status
"ok": SVA ("sva() failed … returning uncorrected data"), and exploBATCH when its R dependency
fMM is missing. Such an approach is unharmonized data under a method's name. It is reported as
**"method failed (returned the input)"** and is not a candidate.

The check applies to **every method** (Q2): an approach that returns its input without
harmonizing fails, whatever the method. Mechanical criterion: the four deterministic metrics PC regression on batch, PC regression on
diagnosis, batch ASW and diagnosis ASW are all equal, at the 6-decimal precision of
Supplementary File 3, to the `01_raw` row with the same strategy, imputation and post-removal
setting. The function is `revision_lib.flag_identical_to_raw`, and r03 stores the result in the
column `identical_to_raw`. These four are used because metrics on an embedding (UMAP, tSNE) vary
between runs of the same matrix, and coarse metrics (kBET, % NA) agree by chance. `01_raw` itself
is never flagged and stays a candidate: it is the honest "do nothing" option.

## Step 2 — Gate N: prediction non-inferiority

An approach passes when **both** conditions hold:

1. N ≥ N_raw − 0.05. N is the leave-one-batch-out macro-F1. N_raw is the N of `01_raw` in the
   same strategy, imputation **and post-removal setting**, so both values are computed on the
   same samples. If that `01_raw` row has no N, the gate is "not evaluable" and the approach is
   not a candidate.
2. N is above the 95th percentile of its permutation null: permutation p-value **< 0.05**
   (n_perm = 100, smallest possible p = 1/101). The fallback, if a p-value is missing, is
   N > null mean + 1.645 × null SD.

**Which N.** The 3-class F1 (DLBCL / FL / Normal B, `pv_lobo3_f1_macro_mean`) is the default.
**Strategy D (malignant only)** keeps only 10 Normal B samples. For D, gate N uses the **2-class
F1, DLBCL vs FL** (`pv_lobo2_f1_macro_mean`, its own permutation null and p-value), and N_raw is
the 2-class N of D's `01_raw`. This way D is not judged on a 3-class task with an almost empty
third class.

Gate N is a non-inferiority gate, not a ranker. The one approach without N (Shambhala, S0, KNN,
with post-removal) is "not evaluable".

## Step 3 — Rank: Pareto front within each scenario

Within each decision-tree scenario, the candidates (steps 1, 1b and 2 passed) are placed on two
axes:

- **batch removal** = mean of the min-max-scaled Global-batch and Local-batch bars;
- **diagnosis retention** = mean of the min-max-scaled Global-biology and Local-biology bars.

The four bars are the headline metrics of `output/wp3/bar_headlines.tsv` (decision D7, gate G1;
three are bar medoids, one is fixed by hand):

| Bar | Headline metric |
|---|---|
| Global batch removal | PC regression on batch (`PCReg_RNA_BATCH`) |
| Global diagnosis retention | PC regression on diagnosis (`PCReg_Diagnosis_cell_type_unified`). Fixed by Daniil (Q1) for symmetry with the Global batch bar; the medoid of this bar would be WaterMelon mean biology. The robustness variant "bar = axis mean" shows whether the choice matters |
| Local batch mixing | kBET acceptance rate on batch (`kbet_acceptance_rate_RNA_BATCH`) |
| Local diagnosis separation | graph connectivity on diagnosis (`graph_connectivity_Diagnosis_cell_type_unified`) |

The scaling is polarity-adjusted min-max over the 2,234 approaches. The **non-dominated set
(Pareto front)** is the recommended set. Front members are ordered by the scaled Local-batch bar
(descending), following the paper's emphasis on local mixing.

**Scenario → candidate strategies** (the five leaves of Figure 6F):

| Scenario (Figure 6F leaf) | Candidate strategies | Gate N |
|---|---|---|
| FF only | J | 3-class |
| FFPE only | K | 3-class |
| RNA-seq only | C | 3-class |
| RNA-seq + Illumina microarrays | one multi-platform pool: S0, A, B, D, E1, E2, E3, I | 3-class; 2-class for D |
| RNA-seq + various microarrays | (the same pool) | (the same) |

The last two leaves are harmonized from the same matrices. The submitted paper told them apart by
looking at which platforms mixed on the UMAP / tSNE plots, and metrics alone cannot separate them.
They are therefore ranked as **one multi-platform pool**. Step 4 decides which front member fits
each leaf, using the platform colouring of the UMAP / tSNE plots. Strategies F, G and H
(microarrays only) are not a leaf of the tree. Their fronts are computed and reported in
`selection_review.xlsx` for information only.

## Step 4 — Visual check

PCA / tSNE / UMAP plots of the front members, drawn like Figures 4–5 and Supplementary Figures
11–17 of the submitted version, are used only:

- (a) as a tie-breaker between front members;
- (b) to veto an approach that is obviously broken;
- (c) to assign the members of the multi-platform front to the two multi-platform leaves, by the
  platform colouring.

Every veto is written to `output/wp4/vetoes.tsv` with its reason and is shown in the review.

## Per-scenario informativeness table (Arsen)

Bars that are not informative in a scenario are shown greyed out, not dropped:

| Scenario | Global batch | Global biology | Local batch | Local biology | Note |
|---|---|---|---|---|---|
| FF only | yes | yes | yes | yes | |
| FFPE only | yes (batch ≈ cohort) | yes | yes (batch ≈ cohort) | yes | most batches hold one cohort |
| RNA-seq only | yes | yes | yes | yes | single platform: no platform metrics |
| multi-platform | yes | yes | yes | yes | in strategy D the biology bars are measured almost only on DLBCL vs FL (10 Normal B) |

## When a version 2 is allowed (fixed now)

After the picks are seen at gate G2b, the rule may be amended **only** for one of these findings:

1. **Veto-class failure:** a front member is visibly broken on PCA / tSNE / UMAP, for example
   one diagnosis collapsed into another, or a sample cloud split by batch.
2. **Empty scenario:** a scenario has no candidate, or an empty front.

Any other wish to change the rule after G2b is not a reason for a version 2. The amendment is a
new file `adjudication_rule_261029_v2.md` with its date, the finding that justifies it, and its
own MD5. The response letter reports the version-1 picks and the change.

## Reporting (fixed now)

- The version-1 picks are always reported, whatever happens at G2b.
- Concordance with the 15 visually selected approaches of the submitted Table 3, per scenario:
  kept / lost / new (`rule_vs_visual_concordance.tsv`). Picks outside the tree leaves (H + MNN)
  are reported as "outside the tree".
- The approaches that failed step 1b are listed (`selection_review.xlsx`, sheet "Method failed").
- Leave-strategies-out check (WP4 step 4.3): the rule is re-applied without strategies A, B, E1,
  E2 and E3. It reports FSQN R's rank and front membership with and without them; the
  interpretation is fixed in plan WP4 step 4.3.
- Robustness (WP5, `r05_robustness.py`), with the variants fixed now: panel cut 0.1 / 0.3, all
  87 metrics, bar = axis mean, group-balanced weights, bridging-batch biology, and **local bars =
  runner-up metrics** (UMAP entropy on batch, cLISI on diagnosis).
- PCA / tSNE / UMAP plots of the picks in the style of Figures 4–5 and Supplementary Figures
  11–17 (`nb07_selected_approaches_embeddings.ipynb`), after G2b.
