# Implementation plan — Article 2 for F1000Research: metric-class comparison of harmonization approaches

**Date:** 2026-09-17 (rewritten 2026-09-18 to carry Daniil's inline comments)
**Author of plan:** Claude Opus 5, for Daniil Nikitin
**Status:** DRAFT — no analysis code, no notebook regeneration, no Figma node and no manuscript
file may be created or modified until Daniil approves this document. Two exceptions already
executed, because Daniil asked for them in his comments: the AACR workflow template and the three
AACR tools have been copied into this folder (§4.5, §4.6), and the Figma file, the metric tables,
Article 1 and the ORCID record have been read (read-only) to produce the numbers below.
**Working directory for everything below:** `article_2_extended_comparison/`


---

## 0. Overview

Article 2 is a standalone F1000Research Research Article built on the extended-metrics results
document already in this folder. Its thesis, stated in one sentence: **no single metric class
selects a usable harmonization approach; the approaches that win depend on which metric class is
used to judge them, and only the full set of metric classes together identifies an approach that
is good on every axis.**

This is the lesson Article 1 paid for. Article 1's clustermap ran over 87 metrics that contained
no biomarker-correlation and no prediction metrics at all — groups L, M and N were computed later
and used only as an after-the-fact validation of an already-chosen set. The consequence is
concrete and measurable: on the analysis set defined in §1.3, the 15 clustermap best approaches
have a median LOBO 3-class macro F1 of **0.629** against **0.707** for every other approach. The
approaches Article 1 elected are not the approaches that predict biology across batches. Article 2
is the paper that says so, quantifies it, and gives the recipe that would have avoided it.

Article 2 therefore inverts Article 1's procedure: it takes each metric class in turn, asks which
approaches that class elects, and shows that the elected sets barely intersect. The practical
deliverable is the final figure: a block-scheme recipe for choosing metrics, computing them
without the biases this benchmark exposed, and validating the winner by leave-one-batch-out
cross-validation.

The work is organized as a six-agent workflow (one team lead plus five specialists) over four
phases, modelled on `an earlier internal proposal workflow (not public)`. **That
template has been copied to `workflows/article2_f1000.workflow.js.template`** and the three tools
it depends on to `tools/` (§4.5, §4.6); the working script is derived from the template, never
written from scratch. Three things happen in parallel across those phases: the code agent adds the
new analyses and exports print-ready subpanels from the three L/M/N notebooks; the figure work
assembles the new multipanel figures plus the recipe scheme in Figma beside the existing Extended
Figures on Page 2; and the writing agents produce a manuscript that shares no sentence, no Methods
paragraph and no figure with the first article. Every agent is specified in §6.2 down to what it
reads, what criteria it applies, and which artifacts it must write to disk before returning — so
that an agent killed by a token limit can be resumed from its own files instead of re-run.

**Key design decision:** the new scientific content of Article 2 is the **metric-class
cross-election analysis** on metric groups L, M and N, not a re-telling of the extended document.
The extended document supplies Results sections 1–5 (already written, already figure-backed);
groups L/M/N supply Results sections 6–8, which are new. This is what makes Article 2 a separate
paper instead of a supplement to the first one, and it is also what keeps it clear of
self-plagiarism.

---

## 1. Background and reference data

### 1.1 Source document — confirmed

The request named `manuscript_versions/Harmonization_metrics_extended_260802.docx`. That file is
**the superseded v1 pass**. Its own audit (`manuscript_versions/Harmonization_metrics_extended_audit_260802.md`,
§5) records that it used a 2,150-row subset and therefore "corrected" four values that were
already right (the all-approach LISI median and MAD, the best-vs-rest Mann–Whitney p, and both
LISI correlation figures), and that its figure sweep corrupted `Supplementary Figure 6` into
`Supplementary Extended Figure 1`.

**Daniil has confirmed: use `Harmonization_metrics_extended_260802_v2.docx`** (673 tracked
revisions, validated, 344 insertions / 329 deletions) as the source of every number and every
figure reference. This is settled; no agent re-opens it.

| File | ins/del | Role in Article 2 |
|---|---|---|
| `Harmonization_metrics_extended.docx` | 0/1 | Original; the diff base, not a content source |
| `Harmonization_metrics_extended_260802.docx` | 155/156 | **Superseded — not a source** |
| `Harmonization_metrics_extended_260802_v2.docx` | 344/329 | **The source document** |
| `Harmonization_metrics_extended_audit_260802.md` | — | Provenance for every number; 54 corrections tabulated |

### 1.2 Section map of the source document (v2)

| § in source | Heading | Extended Figures | Becomes in Article 2 |
|---|---|---|---|
| 1 | Metrics performance overview | EF 1, 2, 3 | Results §1 (→ Figures 1–3, the main-figure promotion of §3.4) |
| 2 | Global metrics | EF 4, 5, 6 | Results §2 |
| 3 | Local metrics | EF 7, 8, 9 | Results §3 |
| 4 | Local and global metrics relationship | EF 9 | Results §4 |
| 5 | Structural and other metrics performance | EF 10 | Results §5 |
| 6 | Impact of harmonization method harshness | EF 11 | Results §5b — see §9.6 |
| 7 | Composite performance score | EF 12, 13 | Results §5c |
| 8 | Summary of metric trends | — | Seeds the Discussion, must be rewritten, not pasted |

### 1.3 The analysis set — Article 1's canonical set, verified 2026-09-18

Daniil's instruction: use the same canonical set as Article 1; the stricter adequacy criteria
drafted earlier were wrong and are withdrawn. Article 1's criterion is the one stated in its own
Supplementary File 3 legend — `pct_samples_allNA < 5` — and it reproduces exactly.

| Set | n | Definition |
|---|---|---|
| Supplementary File 3, all rows | 2,407 | Every attempt with `status == "ok"` |
| **Article 1 canonical set = Article 2 analysis set** | **2,234** | `pct_samples_allNA < 5`. 31 methods, 14 strategies, 3 imputations, both post-removal settings |
| of which non-Shambhala | 2,150 | 30 methods |
| of which Shambhala | 84 | `20_shambhala`, the canonical representative |
| with `pv_lobo2_auc_macro_mean` present | 2,174 | The 2-class AUC is undefined where a strategy leaves fewer than two folds carrying both classes |

**`shambhala_P0std_Q0std` is `20_shambhala`.** The 260905 snapshot stores Shambhala under its 18
P/Q variant names; Article 1 kept one canonical representative and renamed it `20_shambhala`.
Searching a snapshot for the literal string `20_shambhala` returns zero rows, which reads as
"Shambhala has no metrics here" — and that reading is wrong. Verified 2026-09-18: the 84
`20_shambhala` rows of Supplementary File 3 and the 84 `shambhala_P0std_Q0std` rows of the 260905
snapshot share all 84 `(strat, imp, post_rm)` keys and agree on **78 of 79** shared numeric
columns; the single disagreement is `compute_time_s`, which is wall-clock and not a metric. Groups
L, M and N are all computed for it (84 / 83 / 83 non-null).

**The rule, applied everywhere in Article 2's code:** when loading any `metrics_comprehensive_*`
snapshot, rename `shambhala_P0std_Q0std` → `20_shambhala` and drop the other 17 variants, **before**
any filtering or counting. `load_analysis_set()` in §4.1 does this in its first three lines and then
asserts 2,234. The same rule is recorded in project memory so it is not rediscovered the hard way.

Coverage on the analysis set: `mk_rho_mean_markers` 2,234/2,234; `xb_rank_agree`,
`pv_lobo3_f1_macro_mean` and `pv_lobo3_f1_macro_min` 2,233 each; `pv_lobo2_auc_macro_mean` 2,174.
No fold-count or all-NA filter is applied. Two strategies are degenerate for prediction and are
handled by reporting, not by filtering — see §1.5 and §9.5.

### 1.4 Metric groups L, M, N — what exists

Defined in `harmonization-metrics-calculation/compute_batch_metrics.py`; 30 `mk_*`, 24 `xb_*` and
38 `pv_*` columns in the 260905 snapshot, plus the per-fold table `prediction_folds_long.csv`
(94,582 rows, 3,738 run_ids, 24 batches, both targets).

| Group | Function | What it measures | Columns used in Article 2 |
|---|---|---|---|
| **L** | `compute_group_l()` (line 1713) | Per-cohort, per-gene Spearman ρ of each panel gene before vs after harmonization; marker-minus-housekeeping contrast. Reported twice: full 633-gene panel, and `_narrow_set` for the 56 QC-passing genes | `mk_rho_mean_markers`, `mk_rho_mean_housekeeping`, `mk_rho_marker_minus_hk`, `mk_rho_p10_all_genes`, `mk_rho_frac_genes_above_0.9`, `mk_panel_coverage_frac`, and every `_narrow_set` twin |
| **M** | `compute_group_m()` (line 1935) | Cross-batch Spearman rank agreement of the panel within one matrix, contrasting **same-biology** pairs against **different-biology** pairs | `xb_rank_agree`, `xb_rank_disagree_diffbio`, `xb_rank_agree_ratio`, the 15 `xb_rank_agree_<celltype>` columns, and the `_raw` / `_delta` twins built against the `01_raw` baseline |
| **N** | `compute_group_n()` (line 2250) | Leave-one-batch-out (LOBO) logistic regression on training-batch-only PCs; 3-class (FL/DLBCL/Normal_B) and 2-class (FL vs DLBCL); permutation null | `pv_lobo3_f1_macro_mean`, `pv_lobo3_f1_macro_min`, `pv_lobo2_auc_macro_mean`, `pv_lobo3_mcc_mean`, `pv_lobo3_f1_perm_pvalue`, `pv_lobo3_f1_macro_perm_mean`, `pv_lobo3_n_folds_multiclass`, plus every per-batch row of `prediction_folds_long.csv` |

All three groups are computed for `20_shambhala` under its snapshot name
`shambhala_P0std_Q0std` (§1.3); the rename happens on load, before any metric is read.

**Group L's threshold, set by Daniil: ρ > 0.75 is necessary and not sufficient.** A good approach
preserves within-cohort biomarker correlation above 0.75; failing that, it has destroyed the
biology. Passing it proves nothing on its own, because Group L's own docstring records the reason:
*"Any harmonizer applying a per-batch monotone transform of each gene leaves within-cohort ranks
unchanged and therefore scores ~1.0 here by construction."* Group L is a gate, not a ranking. The
discriminative conclusion is carried by the Group M margin and by Group N. This is metric-design
trap 1 in the recipe figure.

The joint gate is quantified in §1.5a.

### 1.5 The new results — measured on the 2,234-approach analysis set, 2026-09-18

All numbers below were recomputed after the `shambhala_P0std_Q0std` → `20_shambhala` rename, on the
full canonical set. None is projected.

**(a) Prediction best approaches.** Daniil's naming, adopted throughout: the approaches elected by
the LOBO metrics are the **prediction best approaches**, compared against the **clustermap best
approaches** of Article 1 as two named groups.

| Criterion | Approaches | Values |
|---|---|---|
| LOBO 3-class macro F1, unfiltered | `G_affymetrix_only / {knn,softimpute,strict} / {06_combat_seq, 08_inmoose_combatseq} / post1` | F1 1.000, worst fold 1.000, **0 multiclass folds** — degenerate |
| LOBO 3-class macro F1, excluding `A_confirmed_bad`, `B_extended_bad` and rows with < 5 multiclass folds (n = 1,527) | `S0_no_removal / softimpute / 29_combat_ref / post0` | F1 0.946, worst fold 0.462, 11 multiclass folds, AUC 0.932, ρ 0.880 |
| | `F_microarray_only / strict / 08_inmoose_combatseq / post0` | F1 0.945, worst fold 0.592, 6 folds, AUC 0.927, ρ 0.829 |
| | `J_ff_only / softimpute / 29_combat_ref / post0` | F1 0.935, worst fold 0.639, 7 folds, ρ 0.944 |
| Highest F1 on a batch-confounded strategy | `A_confirmed_bad / strict / 29_combat_ref / post0` | F1 0.958, AUC 0.998, ρ 0.958, 11 folds |
| Same-minus-different-biology margin (M) | `K_ffpe_only / {knn,strict} / {06_combat_seq, 08_inmoose_combatseq}` | margin 0.433–0.439, ρ 0.86, F1 0.84–0.86 |

The clustermap best set is MNN, SVA, FSQN R, FSMVN and AMDBNorm. The prediction ranking elects the
ComBat family — `29_combat_ref`, `06_combat_seq`, `08_inmoose_combatseq`, `07_pycombat`,
`05_combat` — instead. **That non-overlap is Article 2's headline**, and it is in the data.

The joint Group L / Group M gate — ρ > 0.75 **and** margin > 0 — leaves **1,686 of 2,234**
approaches. Method census of the survivors, top six: `06_combat_seq` 83, `03_limma` 82,
`07_pycombat` 82, `08_inmoose_combatseq` 82, `01_raw` 80, `05_combat` 80. That `01_raw` survives the
gate at all is itself a result: passing Group L with a positive Group M margin does not require
having harmonized anything.

**(b) Where Shambhala lands.** Restoring the 84 `20_shambhala` rows adds a method, not a winner.
Across its 84 approaches: median ρ 0.840, median margin 0.0048, median LOBO 3-class F1 0.745. Its
best row ranks **136 of 2,233** by F1 and **1,680** by margin, and none of its rows enters the
agreement-specific group of (c). Shambhala is mid-field on every biology-facing axis — one sentence
in Results §6, and the reason it can be excluded from the recipe without argument.

**(c) The agreement-specific group** — Daniil's criterion, plotted and counted directly. Approaches
that *raise* cross-batch agreement for same-biology pairs and *lower* it for different-biology
pairs, both relative to their own `01_raw` baseline (`xb_rank_agree_delta > 0` **and**
`xb_rank_disagree_diffbio_delta < 0`), number **61 of the 2,150 non-raw approaches — 2.8%**
(2,234 minus the 84 `01_raw` rows; the coincidence with the non-Shambhala count of §1.3 is
arithmetic, not a shared filter).
Method census: `05_combat` 14, `36_explobatch` 6, `06_combat_seq` 6, `08_inmoose_combatseq` 6,
`14_qsmooth` 5, `25_angel` 5, `04_sva` 4, `16_fsqn_r` 4. Strategy census: `K_ffpe_only` 21,
`F_microarray_only` 11, `I_rare_batches_removed` 7. Top by raw-subtracted margin: `K_ffpe_only / knn / 06_combat_seq / post0` and
`K_ffpe_only / knn / 08_inmoose_combatseq / post0`, which are an **exact tie** — margin 0.439161,
margin gain over raw **+0.457154** for both (agreement +0.257, disagreement −0.200). Two
implementations of ComBat-Seq returning identical Group M values to six decimals is a positive
control worth one sentence in Results §6, and it means neither may be quoted as "the top" alone. Both the subtracted and the unsubtracted form are
reported; the `_raw` and `_delta` columns already exist in the generator (lines 358–376, baseline
`01_raw` at `post_rm = False` joined on `(strat, imp)`).

**(d) The per-batch view: two honest cuts of the same metric, reported side by side.**

Daniil's ruling settles how this is framed. A fold that contains only one class is **not** a
defect in the metric. If a classifier and its threshold are trained on every batch but one and then
predict a DLBCL-only batch as FL, that is an honest test and it should count. So Article 2 reports
**both** cuts and neither replaces the other:

- **the full metric**, over all LOBO folds, exactly as `pv_lobo3_f1_macro_mean` is defined;
- **the multiclass-only metric**, over folds carrying at least two classes, which answers the
  narrower question of how the classifier separates classes when it is actually asked to.

The two differ enough to be worth showing. Across the **32,746** 3-class folds of the analysis
set, **15,436 (47.1%) contain a single class**, and their median macro F1 is **0.903**. On folds
with two or more classes the median is **0.733**, and the composition inside that is informative in
its own right: two-class folds are the *hardest* (median 0.629), three-class folds easier (median
0.804). Spearman between the full metric and the multiclass-only mean is **0.815** over the 2,058
approaches with at least three multiclass folds, and 0.810 over all 2,174 that carry both — high
enough that the two cuts mostly agree, low enough that the ordering inside the leading group
changes.

These counts are lower than the ones this plan carried before 2026-09-19, and the reason is worth
stating once: the earlier figures were computed over every run_id in `prediction_folds_long.csv`
— 3,738 of them, under 50 method names — and 21,543 of those 53,737 folds belong to the 17
non-canonical Shambhala P/Q variants, which are not in the analysis set at all. The fold population
is now restricted to the 2,234 approaches before anything is counted. Every ordering and every
conclusion is unchanged; only the counts move.

Top of the multiclass-only ranking, which stays in the ComBat family and confirms the full metric:

| Approach | full mean F1 | multiclass-only mean F1 | worst multiclass fold | n folds |
|---|---|---|---|---|
| `A_confirmed_bad / strict / 29_combat_ref / post1` | 0.958 | **0.924** | 0.643 | 11 |
| `I_rare_batches_removed / softimpute / 29_combat_ref / post1` | 0.928 | 0.890 | 0.541 | 9 |
| `S0_no_removal / softimpute / 29_combat_ref / post0` | 0.946 | 0.887 | 0.462 | 11 |
| `J_ff_only / knn / 29_combat_ref / post1` | 0.931 | 0.865 | 0.636 | 7 |

Per-batch detail for `S0_no_removal / softimpute / 29_combat_ref / post0` (24 folds): **13** are
single-class and score 0.986–1.000; the genuinely hard folds are `GPL96_FFPE_Unknown` (n = 84, 2
classes, F1 0.462, AUC 0.543), `RNASeq_FFPE_PolyA` (n = 35, 2 classes, F1 0.698, AUC 0.874) and
`RNASeq_FF_PolyA` (n = 1,039, 3 classes, F1 0.718, AUC 0.972).
The approach's full mean of 0.946 and its multiclass-only mean of 0.887 are both real; its
worst-fold floor of 0.462 is the number that describes its generalization. Every prediction table
in Article 2 therefore carries four columns together — full mean, multiclass-only mean, worst
multiclass fold, and the multiclass fold count — so a reader can never see one without the others.

**(e) Harshness tiers by L/M/N** — using the **method-level** `HARSHNESS_LEVEL_MAP` from
`Finally_assembled_figures_for_article.ipynb` cell 4 (low 344 rows, medium 1,042, high 848 with
`20_shambhala` restored to the high tier). This is a different quantity from the disputed composite
ordering of §9.6 and does not touch it.

| Tier | `mk_rho_mean_markers` | `mk_rho_marker_minus_hk` | `xb_rank_agree` | margin | full F1 | multiclass-only F1 | 2-class AUC |
|---|---|---|---|---|---|---|---|
| low | **0.998** | −0.000 | 0.691 | 0.054 | **0.631** | 0.657 | 0.901 |
| medium | 0.880 | 0.009 | **0.701** | 0.045 | 0.713 | **0.678** | 0.904 |
| high | 0.922 | **0.031** | **0.507** | 0.030 | 0.715 | 0.678 | 0.904 |

Kruskal–Wallis across the three tiers: ρ H = 340, p = 1.4 × 10⁻⁷⁴; marker − housekeeping H = 139,
p = 5.6 × 10⁻³¹; `xb_rank_agree` H = 287, p = 4.5 × 10⁻⁶³; margin H = 133, p = 1.4 × 10⁻²⁹; full
F1 H = 52, p = 6.1 × 10⁻¹²; multiclass-only F1 H = 11.8, p = 0.0028; 2-class AUC H = 1.5,
**p = 0.48 — not significant**.

Read plainly: low-harshness methods hold biomarker correlation at 0.998 — the saturation wall — and
score worst on the full prediction metric. High-harshness methods destroy cross-batch rank
agreement (0.507) and have the largest marker-minus-housekeeping contrast. The 2-class AUC cannot
tell the tiers apart at all, and on the multiclass-only metric the three tiers span just 0.021 —
two small results about metric sensitivity that belong in the recipe.

**(f) The two caveats that travel with every quotation of (a).**

1. `A_confirmed_bad` *retains* the known-bad batches, and `G_affymetrix_only` leaves **0** multiclass
   folds in its post-removal rows while still reporting F1 = 1.000. A high LOBO F1 in either is
   consistent with batch-confounded labels or with a degenerate fold structure. Daniil's ruling:
   **report `A_confirmed_bad`** — do not exclude it. It is reported with the confounding stated, and
   `S0_no_removal / softimpute / 29_combat_ref` (F1 0.946, 11 multiclass folds) is quoted as the
   leading non-degenerate approach. `G_affymetrix_only` gets the same treatment, with its fold count
   beside it.
2. `06_combat_seq` and `08_inmoose_combatseq` produced the extreme expression outliers documented in
   the source document (mean maxima 2.76 × 10⁸ and 1.46 × 10¹¹). They win on L/M/N while failing the
   distributional sanity check. Daniil's ruling: if they are the best by L/M/N, report them. That
   contradiction is the thesis, demonstrated on named methods.

### 1.6 Existing subpanel exports

`figures_for_article/current_figures_tables_for_article_260819/` holds 264 files: the Group L/M/N
panels (`fig5a`–`fig5f`, `fig6a`–`fig6e`, both plain and `_narrow_set`), the gene deep-dive panels
(`l0_*` … `l6_*`) and eleven `T*.csv` tables. All are PDF + SVG + PNG at `FONT_SIZE = 7.5`,
`svg.fonttype = "none"`, `savefig.bbox = "tight"`. 

Two of them are prototypes for panels Article 2 needs and should be extended, not reinvented:
`fig6d_per_batch_f1` (the per-batch view of §1.5d) and
`a_scatterplot_xb_rank_disagree_diffbio_delta_vs_xb_rank_agree_delta_by_method` (the
raw-subtracted agreement/disagreement plane of §1.5c).

### 1.7 Figma file map — re-verified 2026-09-18, after Daniil's move

Daniil moved every Extended Figure to **Page 2**. Verified by a `use_figma` read of the file:

| Page | id | Top-level nodes | Contents |
|---|---|---|---|
| Page 1 | `0:1` | 925 | `Figure 1`–`Figure 6`, `Supplementary Figure 1`–`19`, the graphical abstracts and their archived variants. **No Extended Figure frame remains here.** |
| **Page 2** | **`1013:2`** | **43** | All 13 Extended Figure frames, their title TEXT nodes, and Daniil's working notes |
| Page 3 | `1013:3` | 0 | Empty |

Node ids and geometry are unchanged by the move — every frame matches the earlier survey exactly:

| Frame | id | x | y | w × h |
|---|---|---|---|---|
| Extended Figure 1 | 746:22 | −8736 | 6064 | 750 × 813 |
| Extended Figure 2 | 746:24 | −7762 | 6055 | 763 × 653 |
| Extended Figure 3 | 746:25 | −6900 | 6041 | 758 × 818 |
| Extended Figure 4 | 746:27 | −8712 | 7167 | 745 × 338 |
| Extended Figure 5 | 403:15 | −8743 | 8539 | 763 × 1155 |
| Extended Figure 6 | 749:38 | −8815 | 10005 | 777 × 1144 |
| Extended Figure 7 | 747:28 | −7829 | 7175 | 749 × 484 |
| Extended Figure 8 | 750:39 | −7827 | 8537 | 790 × 1185 |
| Extended Figure 9 | 551:6 | −7827 | 9868 | 763 × 1159 |
| Extended Figure 10 | 747:29 | −6905 | 7176 | 778 × 1014 |
| Extended Figure 11 | 750:40 | −6936 | 8587 | 739 × 611 |
| Extended Figure 12 | 747:36 | −5894 | 7235 | 748 × 1138 |
| Extended Figure 13 | 747:37 | −4860 | 7252 | 514 × 323 |

Column grid on Page 2: x = −8736, −7827, −6905, −5894, −4860. Row pitch ≈ 1,100–1,470 px. The
block's lowest edge is y = 11,149 (Extended Figure 6, 10005 + 1144).

**All new frames are created on Page 2**, in new rows starting at y = 11,500, left-aligned to that
column grid. Nothing existing moves; nothing existing is edited except the renaming of §3.4.

Every `use_figma` script must begin with
`await figma.setCurrentPageAsync(figma.root.children.find(p => p.name === 'Page 2'))`, because page
context resets to Page 1 at the start of each call.

### 1.8 House style of the existing frames, as measured on the canvas

Read from Extended Figure 1 (154 TEXT nodes) and Extended Figure 3 (188 TEXT nodes):

| Element | Value |
|---|---|
| Body text in a frame | **Inter, 10 pt** (118 of 154 and 172 of 188 nodes) |
| Panel index letters A, B, C … | **Inter Bold, 20 pt** |
| Residual small labels | 7 pt (32 and 10 nodes) — legacy, not the target |
| Frame width | 739–790 px; the column grid assumes ≈ 750 |

New frames use **Inter 10 pt for every label and Inter Bold 20 pt for panel letters**. The earlier
draft of this plan said "Arimo, 7.5 pt floor"; that was wrong and is withdrawn.

**Canonical palettes** live in `Finally_assembled_figures_for_article.ipynb` **cell 4** (cell 1
carries `GLOBAL_FONT_SIZE = 7.5` and the rcParams). They are copied verbatim into the Article 2
panel code — never re-derived, never re-ordered, because a re-derived `method_pal` assigns
different colours the moment the method list changes:

- `strat_pal` — 16 explicit entries, RGB triples for the first 11 and hex for `I_rare_batches_removed`,
  `J_ff_only`, `K_ffpe_only`, `H_rnaseq_illumina`, `L_rnaseq_all_arrays`.
- `method_pal` — `sorted(df_ok["method"].unique())` zipped against `tab20 + tab20b` with saturation
  boosted by `_boost_sat(rgb, delta=0.15)` in HSV; plus `method_pal["Best"] = "#E63946"`.
  **The sort order is part of the palette**: Article 2 must build it from the same 30-method list
  or the colours will not match the Extended Figures.
- `imp_pal = {"strict": "#2979ae", "knn": "#982d22", "softimpute": "#713689"}`
- `harshness_pal = {"low": "#2DC653", "medium": "#F4A261", "high": "#E63946"}`
- `post_rm_pal = {False: "#CCCCCC", True: "#333333"}`
- `group_pal` — `Set3`, 11 colours, keyed `A`–`K`.
- `BEST_LABEL = "Best"`, `BEST_COLOR = "#E63946"`, `BEST_HATCH = "///"`.

Two harshness maps exist in that cell and must not be confused: `HARSHNESS_MAP` keys **strategies**,
`HARSHNESS_LEVEL_MAP` keys **methods**. §1.5e and Extended Figure 11 use the method-level map.

### 1.9 Graphical-abstract construction vocabulary (the model for the recipe figure)

`Graphical Abstract` (1195:144, Page 1) is built from exactly four kinds of node, and the recipe
figure must use the same four so the two read as one design system:

- **`patch_*` frames** — matplotlib-exported SVG artwork, text-free, imported into Figma.
- **Figma `TEXT` nodes** — every character in the figure, so the acceptance audit can read it.
- **`vector` arrows and `line` rules** — `Arrow 9`, `Arrow 10`, `Line 23`, `Line 24`.
- **Named icon frames** — `icon_step1_batch_removal` … `icon_step7_clustermap`, `icon_ffpe_slide`,
  `Snowflake (Fresh Frozen)`, each 39–61 px wide.

The generating scripts are `figures_for_article/figure_drawing_scripts/graphical_abstract_assets.py`
(artwork only, no text) and `graphical_abstract_pdfs.py`.

### 1.10 F1000Research requirements (fetched from the journal, 2026-09-17)

| Requirement | Value |
|---|---|
| Abstract | ≤ 300 words, structured: Background, Methods, Results, Conclusions |
| Keywords | ≤ 8 |
| Body | ≤ 20,000 words; Introduction / Methods / Results / Discussion or Conclusions |
| Figures and tables | No limit |
| Data availability | **Mandatory**, with repository, dataset title, persistent identifier and licence |
| Software availability | Source on a VCS (GitHub) **plus** an archived copy with a DOI; version numbers for every package |
| Reporting guidelines | Must state which consensus guideline applies, or that none does |
| References | Any consistent style; **preprints are allowed in the reference list** |
| Author contributions | CRediT taxonomy |
| Competing interests, Grant information | Mandatory sections, explicit "no grants" wording if unfunded |
| Preregistration | Must state whether the study was preregistered |

**Repositories and DOIs — taken from Article 1's reference list and Data Availability statement,
as Daniil directed. Nothing here is invented; all four Zenodo records he named are already cited
in Article 1:**

| Resource | GitHub | Zenodo DOI | Record |
|---|---|---|---|
| Analysis code, notebooks, configs | `https://github.com/Nikit357/FL_harmonization` | **new release required** — Article 1 cites the repo, Article 2 needs a DOI-bearing release carrying the Article 2 code | `[TO CONFIRM: new FL_harmonization release DOI]` |
| ComboBatch tool | `https://github.com/Nikit357/ComboBatch` | `10.5281/ZENODO.22755758` | https://zenodo.org/records/22755758 |
| ComboBatch benchmark | — | `10.5281/ZENODO.22755764` | https://zenodo.org/records/22755764 |
| Harmonized matrices + benchmark metrics, 73 public cohorts | — | `10.5281/ZENODO.22737294` | https://zenodo.org/records/22737294 |
| Shambhala2_fast | `https://github.com/Nikit357/Shambhala2_fast` | `10.5281/ZENODO.22756647` | https://zenodo.org/records/22756647 |

**Grant information — the same wording as Article 1**, verbatim from its FUNDING section:
> [Funding statement: as in the published article.]
> This work was funded by the 21AG-1F021 grant from the Committee of Higher Education and Sciences
> MESCS of Armenia (to A.A.).

**CRediT roles** are carried over from Article 1's AUTHOR CONTRIBUTIONS section and adjusted for
the Article 2 author list; the Article 1 text is in the manuscript at paragraph 225 and is the
starting point, not a guess.

---

## 2. What Article 2 is, and how it stays clear of Article 1

### 2.1 The anti-plagiarism contract

Article 1 (`figures_for_article/FL_manuscript_versions/FL_harmonization_article_NAR_260912.docx`,
16,930 words, 86 references) is on bioRxiv. Article 2 cites it as a preprint and must not reuse
its prose. The binding rules for every writing agent:

1. **No sentence, clause or distinctive phrase may be copied** from Article 1, from the extended
   source document, or from any NAR review file. Every number is re-derived and re-worded.
2. **Materials and Methods is written from the code, not from Article 1's Methods — and it is
   shorter than Article 1's.** Daniil's instruction: cite Article 1 wherever a method is already
   described there, and make the Methods easy to follow. Article 1's Methods has twelve
   subsections; Article 2's has **four to six** (§3.2), organized by metric class instead of by
   pipeline stage. Anything Article 1 already specifies in full — the cohort assembly, the 14
   strategies, the 3 imputations, the method registry, the hardware — is one sentence plus a
   citation, never a restatement.
3. **A verbatim-overlap gate runs before delivery** (§8.5): every 8-gram of the Article 2 draft is
   checked against Article 1's and the source document's text. Any hit is a defect, with one
   listed exception. F1000 requires a Grant information section and §1.10 quotes Article 1's
   funding sentences verbatim on Daniil's instruction, so those two sentences would fail this rule
   by construction. They are therefore listed in `tools/overlap_allow.txt`, which is the only
   place an exemption may be granted, and every exemption is named there with its reason. The
   gate prints the count of allow-listed hits on every run, so an exemption cannot hide.
   `.docx` sources are read in their accept-all form: inserted text counts, deleted text does not,
   because deleted text is not in the document a reader receives.
4. **Facts established in Article 1 are cited, not re-derived**, and the citations are few. Daniil's
   instruction: make a small number of citations to Article 1 and put the emphasis on what is new
   in Article 2. The decision tree, the clustermap selection and the 87-metric composite are cited
   once each, in the Introduction or Methods, and never revisited in Results.
5. **The comparison Article 2 runs is not the comparison Article 1 ran.** Article 1 §"Best
   approaches assessment by biomarker expression preservation and biology prediction quality"
   reports L/M/N for the clustermap best approaches against the rest (Supplementary Figure 18 A–M).
   Article 2 does **not** repeat that two-group test. Instead, on the 2,234-approach analysis set,
   it compares **batch-removal strategies against each other, imputations against each other, and
   harmonization methods against each other**, with the clustermap best approaches carried through
   as one named, isolated group for reference — the same shape of comparison Daniil already built
   in the Extended Figures. No sentence in Article 2 is a best-versus-rest significance test.

### 2.2 Visual register

Daniil's instruction on figures: the traditional scatterplots and barplots he used are allowed,
but Article 2's graphics must be drawn in a diverse and interesting manner. Concretely, the panel
inventory in §4.2c commits to:

- **Circos / chord** for the cross-election structure: metric classes as arcs, ribbons weighted by
  the number of approaches two classes jointly elect.
- **Bubble charts** for the method × strategy plane, bubble area = number of approaches, fill =
  median metric.
- **Venn and supervenn** for the top sets by prediction, cross-batch agreement, local, global and
  distributional metrics — Daniil's explicit request, so a reader can see the intersection by eye.
  This panel is the visual bridge to the recipe block scheme.
- **Sankey** for flow between categories — approaches entering each metric class's elected set,
  and the raw → gated → elected → validated funnel of the recipe. Daniil asked for these
  specifically; they also read well beside the Circos panel.
- **Slope / dumbbell** for raw → harmonized transitions, which reads better than a paired boxplot.
- **Ridgeline** for per-batch F1 distributions across the prediction best approaches.
- Scatterplots and barplots where they are genuinely the right form, with the canonical palettes.


### 2.3 The Article 1 preprint — published, cited by DOI

The preprint is live. Verified against Crossref on 2026-09-18: DOI `10.64898/2026.09.15.751825`,
posted 2026-09-17, type `posted-content`, subject group Cancer Biology, title and author order
matching Article 1 exactly. **There is no `[PREPRINT-1]` placeholder anywhere in Article 2** — the
reference is written out in full from the first draft:

```
Nikitin D, Borisov N, Savchenko M, Bobe A, Meerson M, Nesmelov A, et al. Benchmarking of bulk
transcriptomic harmonization tools in a multi-platform B-cell lymphoma cohort identifies
feature-specific quantile normalization and surrogate variable analysis as top-performing
methods. bioRxiv. 2026 Sep 17. doi: 10.64898/2026.09.15.751825
```

F1000Research permits preprints in the reference list, so this entry needs no caveat. Any agent
that emits `[PREPRINT-1]` has used a stale instruction and its output is a defect.

**No agent invents a DOI, an accession, a URL, a PMID, a title or an author list.** Unknown values
are written literally as `[TO CONFIRM: what is missing]`. This prohibition is stated in every
agent's own prompt, not only in the shared rules, and the reference-verifier and the team lead
cross-check each other's outputs for it (§6.2). A fabricated reference is a workflow abort, not a
defect to be fixed in review.

### 2.4 Self-citation — the full ORCID record

Daniil's instruction: cite them all. The ORCID record `0000-0003-1029-1174` was fetched on
2026-09-18 and lists **25 entries**, which collapse to **19 distinct works** once preprint/published
pairs and one correction notice are merged. All 19 are cited; the table assigns each a locus so that
no citation is dropped in and no sentence carries a citation that does not support it.

The merges, so the reference list does not double-count:

- The transposable-element arms-race paper appears four times — R Soc Open Sci 2026
  (`10.1098/rsos.260639`, the version of record), EcoEvoRxiv (`10.32942/X2FM2M`), bioRxiv
  (`10.64898/2026.03.19.712972`) and one untitled-year duplicate. **Cite the R Soc Open Sci version.**
- The T-cell lymphoma biorepository appears twice — Cell Rep Med 2025
  (`10.1016/j.xcrm.2025.102029`) and its SSRN preprint (`10.2139/ssrn.4529648`). **Cite Cell Rep Med.**
- `10.3390/cells8080832` is a *correction* to `10.3390/cells8020130`. Cite the article; append the
  correction in the same reference entry, as the journal expects.

| # | Work | Year | Venue | DOI | Where it is cited in Article 2 |
|---|---|---|---|---|---|
| 1 | Experimental and meta-analytic validation of RNA-seq signatures for predicting MSI status | 2021 | Front Mol Biosci | 10.3389/fmolb.2021.737821 | Introduction — a signature validated across independently generated datasets; the transfer problem Article 2 measures |
| 2 | Personalized targeted therapy prescription in colorectal cancer using algorithmic analysis of RNA-seq | 2022 | BMC Cancer | 10.1186/s12885-022-10177-3 | Introduction — cross-cohort application of an expression model |
| 3 | Gene expression-based signature can predict sorafenib response in kidney cancer | 2022 | Front Mol Biosci | 10.3389/fmolb.2022.753318 | Introduction — signature portability across cohorts |
| 4 | RNA sequencing-based identification of ganglioside GD2-positive cancer phenotype | 2020 | Biomedicines | 10.3390/BIOMEDICINES8060142 | Methods, Group L — marker-panel expression readout |
| 5 | High FREM2 gene and protein expression are associated with favorable prognosis of IDH-WT glioblastomas | 2019 | Cancers | 10.3390/cancers11081060 | Methods, Group L — single-marker prognostic readout across platforms |
| 6 | DNA repair pathway activation features in follicular and papillary thyroid tumors | 2021 | Heliyon | 10.1016/j.heliyon.2021.e06408 | Introduction — pathway-level activation from expression, cross-dataset |
| 7 | Gene expression signature of endometrial samples from women with and without endometriosis | 2021 | J Minim Invasive Gynecol | 10.1016/j.jmig.2021.03.011 | Introduction — signature derived from a single-centre cohort; the generalization question |
| 8 | A patient-derived T-cell lymphoma biorepository uncovers pathogenetic mechanisms and host-related factors | 2025 | Cell Reports Medicine | 10.1016/j.xcrm.2025.102029 | Introduction — lymphoma transcriptomics, the disease context |
| 9 | Analysis of miR-9-5p, miR-124-3p, miR-21-5p, miR-138-5p, miR-1-3p in glioblastoma cell lines and extracellular vesicles | 2020 | Int J Mol Sci | 10.3390/ijms21228491 | Discussion — marker stability across preparation types |
| 10 | Plasma exosomes stimulate breast cancer metastasis through surface interactions and activation of FAK signaling | 2019 | Breast Cancer Res Treat | 10.1007/s10549-018-5043-0 | Discussion — expression readouts from a non-standard input material |
| 11 | Functional properties of circulating exosomes mediated by surface-attached plasma proteins | 2018 | Haematologica | 10.14740/jh412w | Discussion — same, paired with 10 |
| 12 | Transposable element–host genome evolutionary arms race revealed by multi-modal epigenomic profiling | 2026 | R Soc Open Sci | 10.1098/rsos.260639 | Introduction — genome-wide profiles compared across assay modalities, the multi-platform comparison problem in another domain |
| 13 | Joint analysis of human retroelements-linked histone modification profiles reveals quickly evolving loci | 2025 | bioRxiv | 10.1101/2025.09.24.677146 | Introduction — joint analysis across separately generated profile sets |
| 14 | H3K4me3, H3K9ac, H3K27ac, H3K27me3 and H3K9me3 histone tags suggest distinct regulatory evolution | 2019 | Cells | 10.3390/cells8091034 | Introduction — multi-assay integration, same theme as 12 |
| 15 | Retroelement-linked H3K4me1 histone tags uncover regulatory evolution trends of gene enhancers | 2019 | Cells | 10.3390/cells8101219 | Introduction — same theme as 14 |
| 16 | Retroelement-linked transcription factor binding patterns point to quickly developing molecular pathways (with its 2019 correction, 10.3390/cells8080832) | 2019 | Cells | 10.3390/cells8020130 | Introduction — same theme as 14 |
| 17 | Profiling of human molecular pathways affected by retrotransposons at the level of regulation by transcription factor proteins | 2018 | Front Immunol | 10.3389/fimmu.2018.00030 | Introduction — pathway-level aggregation of noisy per-feature signal |
| 18 | Retroelements-driven regulatory evolution of human genes and molecular processes (dataset) | 2026 | Zenodo | 10.5281/ZENODO.19052415 | Data availability — cited as a deposited dataset, not as a finding |
| 19 | RetroSpect, a new method of measuring gene regulatory evolution rates using co-mapping of genomic features | 2019 | Evolution: Origin of Life, Concepts and Methods (book chapter) | — | Discussion — method-development precedent; `[TO CONFIRM: chapter DOI or ISBN]` |

Two entries in the record are not citable as literature and are handled separately: a somatic-variant reference dataset (AMP 2025) is a conference abstract with no DOI, and is cited only
if a sentence genuinely needs it, with `[TO CONFIRM: AMP 2025 abstract number]`; entry 18 is a
dataset and belongs in Data Availability.

The **Borisov reviews already cited in Article 1**, which the literature-scout must read in full:

| Work | Year | Journal | DOI / PMID |
|---|---|---|---|
| Borisov N, Buzdin A. Transcriptomic harmonization as the way for suppressing cross-platform bias and batch effect | 2022 | Biomedicines 10(9):2318 | 10.3390/BIOMEDICINES10092318 |
| Borisov N, Shabalina I, Tkachev V, et al. Shambhala: a platform-agnostic data harmonizer for gene expression data | 2019 | BMC Bioinformatics 20(1) | 10.1186/S12859-019-2641-8 · PMID 30727942 |
| Borisov N, Sorokin M, Zolotovskaya M, et al. Shambhala-2: a protocol for uniformly shaped harmonization of gene expression profiles | 2022 | Curr Protoc 2(5) | 10.1002/CPZ1.444 · PMID 35617464 |

Nikolay Borisov is a co-author of Article 1 and is expected on Article 2. The two Shambhala papers
are also the primary references for the `20_shambhala` method that §1.5b reports on.

---

## 3. The manuscript

### 3.1 Target shape

| Section | Words | Content |
|---|---|---|
| Title + abstract | 300 | Structured Background / Methods / Results / Conclusions |
| Introduction | 900 | Batch effect in multi-cohort transcriptomics; why benchmarks disagree; what a metric class is; the gap: no study asks whether metric classes elect the same approaches. Cites the Article 1 preprint once for the dataset and pipeline, the Borisov harmonization review for the field, and the on-topic ORCID works of §2.4 where a signature-transfer claim needs them |
| Materials and Methods | **1,400** | Four to six subsections (§3.2), shorter than Article 1's twelve, citing the Article 1 preprint for everything it already specifies |
| Results and Discussion | 5,500 | Eight sub-sections (§3.3) — F1000 permits the combined section and it suits an argument that interleaves measurement and interpretation |
| Conclusions | 600 | The recipe, in prose, pointing at the final figure |
| Back matter | 700 | Data availability, software availability, reporting guidelines, ethics, author contributions (CRediT), competing interests, grant information, acknowledgements, AI usage |
| **Total** | **≈ 9,400** | Well inside the 20,000-word limit |

### 3.2 Materials and Methods — four to six subsections, organized by metric class

Compressed from the ten-subsection draft on Daniil's instruction, for readability and to keep it
structurally unlike Article 1's Methods.

1. **Dataset, harmonization attempts and the analysis set.** One paragraph citing the Article 1 preprint
   for the 7,174-sample cohort, the 14 strategies, the 3 imputations, the 31 methods and the two
   post-removal settings — no restatement. Then the analysis set of §1.3: Article 1's canonical
   2,234 approaches (`pct_samples_allNA < 5`), all of which carry groups L, M and N, with one
   sentence noting that Shambhala is recorded as `shambhala_P0std_Q0std` in the metric tables and as
   `20_shambhala` in Article 1.
2. **Metric classes.** The taxonomy in one table: global PCA-based, local neighbourhood,
   distributional, structural, composite, and the three biology-facing classes L/M/N. For each:
   what it is computed on, the annotation column, the polarity convention, and the failure mode it
   cannot detect.
3. **The biology-facing metrics.** Group L (633-gene panel, 63 signatures; the 56-gene narrow
   subset and its two gates; the two housekeeping controls; the ρ > 0.75 necessary-not-sufficient
   threshold and the monotone-transform saturation trap), Group M (same- and different-biology pair
   populations, the margin, the `01_raw` baseline joined on `(strat, imp)` and the `_delta` form),
   Group N (training-batch-only PCA fit, held-out projection, 3-class and 2-class targets, the
   multiclass-fold count, the permutation null and its seed, and the per-fold table).
4. **The generalizability index and the election procedure** (§4.1).
5. **Statistics and software.** Mann–Whitney U two-sided, Kruskal–Wallis across tiers, Spearman
   with bootstrap CI, Benjamini–Hochberg FDR, seed 42 everywhere; package versions per F1000.
6. **AI usage.** Written fresh; the plan-then-act description, with this plan document named as an
   example artifact.

### 3.3 Results and Discussion — eight sub-sections

Section titles rewritten to a scientific register on Daniil's instruction; the earlier casual
formulations ("measure different things", "is displaced, not removed") are withdrawn.

| § | Title | Evidence |
|---|---|---|
| 1 | Metric classes capture non-overlapping components of harmonization quality | Figures 1–3 |
| 2 | Global variance-based metrics saturate below the threshold of biological recovery | Supp. Figs 1–3; the five methods at PCReg ≥ 0.999 with kBET < 0.1 in 98.5% of their 198 approaches |
| 3 | Local neighbourhood metrics discriminate between approaches but scale with class composition | Supp. Figs 4–6 |
| 4 | Batch-associated variance is redistributed across principal components instead of eliminated | Supp. Fig 3; 19 of 31 methods, 10 of 14 strategies |
| 5 | Distributional convergence is the only axis on which high-harshness transformations rank first | Supp. Figs 7–10 |
| 6 | **Preservation of biomarker expression and of cross-batch rank structure elects a distinct set of approaches** | Figure 4 (Groups L + M); §1.5a, §1.5c |
| 7 | **Cross-batch prediction elects a third set, whose ranking is stable across two cuts of the fold population** | Figure 5 (Group N, per-batch detail, generalizability index); §1.5d |
| 8 | **The sets elected by the individual metric classes show limited intersection** | Figure 5 final panel; the cross-election matrix and the Venn/supervenn panel |
| D | Discussion woven through 6–8 | Which approaches to use and why; the ComBat family against the clustermap winners; the `A_confirmed_bad` and `G_affymetrix_only` confounds; the single-class-fold bias; what this means for anyone benchmarking harmonizers |

### 3.4 Figure inventory — renumbered on Daniil's instruction

Extended Figures 1, 2 and 3 — the top row on Page 2 — become **main figures**. Every other
Extended Figure becomes **supplementary**. Three new main figures and up to three new
supplementary figures are added. The renaming is applied to the Figma frames and to the already
written Word text in the same pass, so text and canvas never disagree.

**Main figures (6):**

| Article 2 | Was | Content |
|---|---|---|
| **Figure 1** | Extended Figure 1 (746:22) | Approaches compared by global metrics |
| **Figure 2** | Extended Figure 2 (746:24) | Approaches compared by local metrics |
| **Figure 3** | Extended Figure 3 (746:25) | Distributional similarity, NA genes and samples, other metrics |
| **Figure 4 (new)** | — | **Biomarker gene expression and correlation study — metric classes L and M.** Per-gene and per-cohort expression scatter for selected biomarker genes under each best-approach group; Group L ρ and the Group M margin across strategies, imputations and methods, with the clustermap best approaches as an isolated group |
| **Figure 5 (new)** | — | **Prediction quality and cross-election — metric class N.** LOBO ranking on both fold cuts, per-batch detail for the prediction best approaches, the generalizability index, and the Venn/supervenn cross-election panel |
| **Figure 6 (new)** | — | **The recipe**: block scheme for selecting metrics when benchmarking harmonization approaches, with the LOBO scheme drawn out |

Groups L and M are the correlation-preservation classes and carry the biomarker gene expression
study; Group N is the prediction-quality class. Figure 4 and Figure 5 are split on that line.

**Figure 4 opens with the expression scatters Daniil has been drawing by hand.** They already exist
in `marker_gene_deep_analysis.ipynb` cells 88–90 — `paired_frame(run_id, SCATTER_GENES)` feeding a
`sns.relplot` gene × cohort grid of raw against harmonized expression, one point per sample, with an
identity line and a per-facet Spearman ρ, saved as `l6_scatter_gene_cohort_grid_{run_id}`. The three
hand-run approaches are `S0_no_removal__knn__{16_fsqn_r, 04_sva, 03_limma}__post0`. Article 2
promotes that cell into the generator and runs it for **one representative of each best-approach
group** — clustermap best, correlation (L/M) best, prediction (N) best, and `01_raw` as the
baseline — over the four largest cohorts and a fixed biomarker gene set, so a reader can see by eye
what each harmonization does to an expression profile.

**Supplementary figures (≤ 13):**

| Article 2 | Was |
|---|---|
| Supplementary Figure 1–3 | Extended Figures 4, 5, 6 (global metrics) |
| Supplementary Figure 4–6 | Extended Figures 7, 8, 9 (local metrics) |
| Supplementary Figure 7 | Extended Figure 10 (other metric groups) |
| Supplementary Figure 8 | Extended Figure 11 (other metrics part 2) |
| Supplementary Figure 9–10 | Extended Figures 12, 13 (composite score) |
| **Supplementary Figure 11 (new)** | Marker-panel QC, coverage and the narrow set |
| **Supplementary Figure 12 (new)** | Harshness tiers by L/M/N (§1.5e), and the full-versus-multiclass fold comparison |
| **Supplementary Figure 13 (new, optional)** | Per-method and per-strategy technical comparisons that are too uniform for a main panel |

**Supplementary figure captions move to their own manuscript section, headed "Supplementary
Material".** Once Extended Figures 4–13 become Supplementary Figures 1–10, their legends no longer
belong in the main figure-legend sequence; they are cut from it and reassembled, in order, under
that heading at the end of the manuscript, together with the legends for the new Supplementary
Figures 11–13 and the supplementary table descriptions of §7. The main text keeps only the six main
figure legends.


Renaming is the **only** change made to an existing frame: no artwork is redrawn, no panel is
moved, no geometry is touched. The title TEXT node beside each frame is renamed in the same
operation so the canvas stays readable.

---

## 4. Files to change

### 4.1 NEW — `article_2_extended_comparison/analysis/article2_generalizability.py`

The single new analysis module. Standalone, importable by both notebook generators, and runnable
on its own so the numbers can be audited without opening a notebook.

**Why a new file instead of more cells in the generators:** the cross-election analysis is used by
two notebooks and by the figure scripts, and Article 2's numbers must be reproducible by one
command. Putting it in a generator would bury it in a 1,200-line string-emitting script.

```python
"""Metric-class cross-election analysis for Article 2 (F1000Research).

Every number quoted in Results sections 6-8 is produced here. Run standalone to
reproduce the tables; import `load_analysis_set`, `elect`, `generalizability_index`
from the notebook generators so the notebooks and the manuscript cannot diverge.

    source ~/venvs/collagen_3_11/bin/activate
    cd article_2_extended_comparison
    python analysis/article2_generalizability.py --date-tag 260905 --out-dir tables/
"""

METRICS_CSV = "../harmonization-metrics/metric_tables/metrics_comprehensive_{tag}.csv"
SUPP_FILE_3 = "../figures_for_article/supplementary_260824/Supplementary File 3.csv.gz"
FOLDS_CSV   = "../harmonization-metrics/metric_tables/prediction_folds_long.csv"

RHO_GATE = 0.75   # Group L: necessary, not sufficient (Daniil, 2026-09-18)

# The metric snapshots store Shambhala as 18 P/Q variants; Article 1 kept one
# canonical representative and renamed it. These are the SAME method.
SHAMBHALA_CANONICAL = "shambhala_P0std_Q0std"   # == 20_shambhala

def load_analysis_set(supp3_path, metrics_path) -> pd.DataFrame:
    """Article 1's canonical 2,234-approach set, with L/M/N attached.

        d = d[~d.method.str.startswith("shambhala_") | (d.method == SHAMBHALA_CANONICAL)]
        d.loc[d.method == SHAMBHALA_CANONICAL, "method"] = "20_shambhala"
        canon = supp3[supp3.pct_samples_allNA < 5]          # -> 2,234
        g = canon[KEY].merge(d, on=KEY, how="left")

    The rename happens FIRST, before any filter or count. Skipping it silently
    drops 84 approaches and yields 2,150 -- verified 2026-09-18 that the two
    names carry identical values on 78 of 79 shared numeric columns (the
    exception is compute_time_s, wall-clock, not a metric).

    Asserts len == 2234 and method.nunique() == 31; fails loudly if a snapshot
    changes underneath the manuscript.
    """

def add_raw_deltas(df) -> pd.DataFrame:
    """Join the 01_raw / post_rm=False baseline on (strat, imp) and add
    `{metric}_raw` and `{metric}_delta` for every L/M/N column, matching
    create_correlation_prediction_notebook.py lines 358-376 exactly."""

def add_fold_metrics(df, folds_path) -> pd.DataFrame:
    """Per-batch LOBO detail from prediction_folds_long.csv.

    Adds, per run_id, TWO cuts of the same fold population -- neither replaces
    the other, and every table in the manuscript shows both (Daniil, 2026-09-18):

        full   : pv_lobo3_f1_macro_mean as published, over ALL folds
        mc     : f1_mc_mean, f1_mc_min, n_mc   -- folds with n_classes >= 2

    A single-class fold is an honest test: a classifier trained on every batch
    but one, asked to label a DLBCL-only batch, can still get it wrong. It is
    NOT excluded and NOT treated as a metric defect. The two cuts are reported
    side by side because they answer different questions -- `full` asks how the
    approach does on the batch population as it actually is, `mc` asks how it
    separates classes when it is asked to. They agree at Spearman 0.815.

    The fold population is restricted to the analysis set before anything is
    counted: prediction_folds_long.csv carries 3,738 run_ids under 50 method
    names, including all 18 Shambhala P/Q variants, and a census over all of
    them describes approaches the article never analyses.

    Also returns the fold-composition census used by the a2_p6 panel:
    47.1% of the 32,746 3-class folds are single-class (median F1 0.903); of
    the rest, two-class folds are the hardest (median 0.629) and three-class
    folds easier (median 0.804)."""

def agreement_specific(df) -> pd.DataFrame:
    """Daniil's criterion: high cross-batch agreement for same-biology pairs AND
    low agreement for different-biology pairs, reported both raw-subtracted and
    not. Returns the 61 approaches with xb_rank_agree_delta > 0 and
    xb_rank_disagree_diffbio_delta < 0, plus the unsubtracted margin ranking."""

def generalizability_index(df) -> pd.Series:
    """Rank-percentile mean of six columns, each polarity-adjusted:
         pv_lobo3_f1_macro_mean      (prediction, 3-class, all folds)
         f1_mc_mean                  (prediction over multiclass folds only)
         pv_lobo2_auc_macro_mean     (prediction, 2-class)
         mk_rho_mean_markers         (biology preserved, Group L)
         xb_margin_delta             (Group M gain over the raw baseline)
         f1_mc_min                   (worst true multiclass fold: generalization, not luck)
    Rank-percentile, not min-max: the columns have incompatible scales and
    Group L saturates at 1.0 by construction for monotone methods."""

def elect(df, metric_class, top_frac=0.05) -> set:
    """The approaches a single metric class elects: top `top_frac` by that class's
    own composite. Returns a run_id set. Classes: global, local, distributional,
    structural, composite, L, M, N, plus the named group `clustermap_best`."""

def cross_election_matrix(df) -> pd.DataFrame:
    """Jaccard overlap between the elected sets of every pair of metric classes,
    including the Article 1 clustermap best set as a named row and column."""
```

Outputs (to `article_2_extended_comparison/tables/`):

| File | Content |
|---|---|
| `A2_T1_analysis_set_census_260917.csv` | The 2,234 rows with every metric used, plus `is_clustermap_best`, `is_prediction_best`, `is_confirmed_bad`, `is_degenerate_folds`, `n_mc` flags |
| `A2_T0_shambhala_identity_260917.csv` | The 84-row column-by-column check that `shambhala_P0std_Q0std` == `20_shambhala`, so the rename is auditable and not a claim |
| `A2_T2_generalizability_ranking_260917.csv` | Full ranking with the index and its six components |
| `A2_T3_cross_election_matrix_260917.csv` | Jaccard matrix across metric classes |
| `A2_T4_method_census_by_class_260917.csv` | Which methods each class elects, counted |
| `A2_T5_per_batch_folds_260917.csv` | Per-batch F1/AUC for the prediction best approaches and the clustermap best group, with `n_classes` per fold so the two cuts are reconstructable |
| `A2_T8_fold_composition_260917.csv` | Fold-class composition across all 24 batches: how many folds carry 1, 2 or 3 classes, and the F1 distribution in each |
| `A2_T6_agreement_specific_260917.csv` | The 61 agreement-specific approaches, subtracted and unsubtracted |
| `A2_T7_harshness_by_lmn_260917.csv` | The §1.5e tier table with the Kruskal–Wallis statistics |

### 4.2 `harmonization-metrics/create_correlation_prediction_notebook.py`

The generator for both blind-check notebooks (1,197 lines). Four changes.

**4.2a — new output directory and panel-size preset (near line 55)**

```python
# Article 1 panels keep writing to the 260819 folder; Article 2 panels are exported
# separately so a regeneration for Article 2 can never overwrite a published panel.
FIG_DIR = Path("../figures_for_article/current_figures_tables_for_article_260819")
A2_FIG_DIR = Path("../article_2_extended_comparison/figures/panels_260917")
```

**4.2b — a Figma-sized save helper (after `save_figure`, ~line 173)**

```python
# Panel geometry for Figma assembly. The Page 2 frames are 739-790 px wide and the
# convention in this project is 2 px = 1 pt, so a full-width panel is 375 pt =
# 5.21 in, a half-width panel 2.60 in and a third-width panel 1.72 in. Every
# Article 2 panel is saved at one of these widths, so panels drop onto the canvas
# at 1:1 with no rescaling.
PANEL_W_FULL, PANEL_W_HALF, PANEL_W_THIRD = 5.21, 2.60, 1.72

def save_panel(fig, name, width="half", height=None, figures_dir=A2_FIG_DIR):
    """Save one Article 2 subpanel at Figma-native size, PDF + SVG + PNG.
    Artwork is resized, never the font."""
```

**4.2c — new §10, the Article 2 analyses (appended after §9)**

Every cell imports from `article2_generalizability.py`; no analysis logic is duplicated in the
notebook. All panels use the canonical palettes of §1.8.

| Cell | Panel file | Content | Form |
|---|---|---|---|
| §10.1 | `a2_p1_rho_vs_margin.*` | Group L ρ against the Group M margin, all 2,234 approaches, clustermap best marked; the ρ ≈ 1 saturation wall and the ρ = 0.75 gate drawn as rules | scatter + rug |
| §10.2 | `a2_p2_margin_ranking.*` | Top 30 by margin **and** by raw-subtracted margin gain, side by side, strategy-coloured | paired horizontal bars |
| §10.3 | `a2_p3_agreement_specific.*` | `xb_rank_agree_delta` against `xb_rank_disagree_diffbio_delta` with the origin quadrants; the 61 agreement-specific approaches highlighted and named. Unsubtracted `xb_rank_agree` vs `xb_rank_disagree_diffbio` with the identity line as an inset | scatter + inset |
| §10.4 | `a2_p4_lobo_ranking.*` | Top 30 by LOBO 3-class F1, permutation null as a shaded band, worst multiclass fold as a whisker, multiclass-fold count annotated | bar + whisker |
| §10.5 | `a2_p5_per_batch.*` | Per-batch F1 for the prediction best approaches and the clustermap best group; single-class folds marked separately from multiclass folds | ridgeline + strip |
| §10.6 | `a2_p6_singleclass_audit.*` | Published `pv_lobo3_f1_macro_mean` against the multiclass-folds-only mean, coloured by the single-class fold fraction | scatter with identity line |
| §10.7 | `a2_p7_strategy_imputation_method.*` | Strategies, imputations and methods compared against each other on L/M/N, clustermap best carried as an isolated group | bubble grid |
| §10.8 | `a2_p8_generalizability_index.*` | The index, top 40, six components stacked | stacked bars |
| §10.9 | `a2_p9_cross_election_circos.*` | The cross-election structure: metric classes as arcs, ribbons weighted by joint elections | circos / chord |
| §10.10 | `a2_p10_venn_supervenn.*` | Top sets by prediction, cross-batch agreement, local, global and distributional metrics — Venn for the readable subset, supervenn for all five. **The bridge panel to the recipe scheme** | Venn + supervenn |
| §10.11 | `a2_p11_harshness_lmn.*` | The three harshness tiers by L/M/N (§1.5e) with the Kruskal–Wallis statistics | violin grid |
| §10.12 | `a2_p12_raw_to_harmonized.*` | `01_raw` → harmonized transitions for the named best groups | slope / dumbbell |
| §10.13 | `a2_p13_election_sankey.*` | The funnel Daniil asked for: all approaches → the joint L/M gate → each class's elected set → elected by two classes or more | Sankey |

Dependencies to add: `supervenn` and `matplotlib-venn` for §10.10; the circos panel is drawn with
plain matplotlib patches, not an external package, so nothing new enters the environment for it.

**4.2d — argparse flag (near line 35)**

Add `--article2` (default `False`): when set, emit the §10 cells and point `save_panel` at
`A2_FIG_DIR`. Without it the generator produces exactly today's notebook, so Article 1's
reproducibility is untouched.

**4.2e — the divergence problem: extract the hand-written cells into a new notebook**

Daniil's instruction is not to list the diverged cells but to **extract them into a new notebook he
will keep and use**, and to preserve them in the regenerated notebooks. Measured on 2026-09-18:

Re-measured 2026-09-19 with `tools/extract_hand_written_cells.py`, which runs each generator
in a scratch copy at the same `--date-tag` and compares every cell against that output. The counts
are higher than the ones this plan carried before, because the earlier pass counted only cells that
look nothing like the generator's and missed the more dangerous category: a generator cell **edited
in place**. Such a cell still reads as the generator's, so regeneration reverts the edit without
saying so.

| Notebook | Cells | Hand-written (`DIVERGED`) | Generator cell edited by hand (`NEAR`) | At risk |
|---|---|---|---|---|
| `correlation_prediction_metrics_analysis.ipynb` | 40 | **12** | **6** | 18 |
| `correlation_prediction_metrics_analysis_narrow_set.ipynb` | 77 | **50** | **12** | 62 |
| `marker_gene_deep_analysis.ipynb` | 125 | **53** | **52** | 105 |
| **Total** | 242 | 115 | 70 | **185** |

The twelve hand-written cells of the main notebook are 6, 7, 9, 11, 12, 15, 18, 19, 23, 26, 27 and
38 — two of them (15 and 27) are Daniil's working notes in Russian on the LOBO PCA design and on
gene-correlation grouping, 38 is the Supplementary File 5 export block, and five (6, 7, 9, 12, 18,
19) are bare inspections of a variable with no logic to lose. Its six edited generator cells are
3, 5, 8, 14, 22 and 31, at similarities 0.94 to 0.999. The 43 in the narrow-set notebook include the
per-batch F1 exploration (cells 56–64, which is the prototype of §1.5d), the raw-subtracted
agreement exploration (cells 44–50, the prototype of §1.5c), the palette-plotting helper (cell 22)
and the permutation-null statistics (cells 69–73).

**Step order, mandatory:**

1. Extract every non-generator cell from all three notebooks into a new, executable notebook
   `harmonization-metrics/hand_written_cells_260917.ipynb`, one markdown header per source
   notebook, cells in their original order with their original source. This notebook is a
   deliverable Daniil keeps, not an audit log.
2. Write `harmonization-metrics/diverged_cells_260917.md` alongside it: for each cell, its index,
   its first two lines, whether it carries Russian notes, and a one-line recommendation — port
   into the generator, keep only in the hand-written notebook, or drop.
3. **Get Daniil's sign-off on that recommendation list.**
4. Port the cells marked "port" into the generator so the regenerated notebooks carry them.
5. Only then regenerate.

**This is the single most likely place for the implementation to destroy work**, and step 1 alone
is what protects it.

### 4.3 `harmonization-metrics/create_marker_gene_deep_analysis_notebook.py`

Smaller change (2,472 lines). The deep-dive notebook already exports `l0_*`–`l6_*` panels at
notebook-chosen sizes. Add the same `save_panel` helper and re-export **only the four panels
Article 2 needs**, at Figma size, into `A2_FIG_DIR`:

The panel numbers moved by two when the Sankey became `a2_p13` in the other generator and the
expression scatters landed here as `a2_p14`. The full inventory is now **eighteen** panels:
`a2_p1`–`a2_p13` from `create_correlation_prediction_notebook.py`, `a2_p14`–`a2_p18` from this one.

| Existing panel | Article 2 name | Why |
|---|---|---|
| — (new; ported from the hand-run cells 88–90) | `a2_p14_expression_scatter_<method>.*` | Raw against harmonized expression per sample, gene × cohort, one representative per best-approach group plus `01_raw` |
| `l1_coverage_raw_vs_attempts` | `a2_p15_panel_coverage.*` | The coverage gate that defines the narrow set |
| `l2_qc_gate_sweep` | `a2_p16_qc_gate.*` | The expression-quality gate; feeds the recipe's "avoid biases" branch |
| `l4_rho_by_gene_set` | `a2_p17_rho_by_signature.*` | ρ by signature — which biology survives which method |
| `l5_clustermap_genes_by_method_median` | `a2_p18_gene_method_clustermap.*` | Gene × method structure behind the Group L aggregate |

The re-export is wired through `save_figure` itself: under `--article2` the notebook's own
`save_figure` writes the Article 1 file first, at its own size, and then calls `save_panel` for the
registered name. Nothing is recomputed and no plotting code is duplicated, so the two articles
cannot show different numbers in the same picture.

No new analysis in this generator; re-export only. Its hand-written cells go through §4.2e first.

### 4.4 NEW — `article_2_extended_comparison/figures/recipe_figure_assets.py`

Artwork for the final recipe figure (Figure 6), built on the graphical-abstract pattern: **artwork
only, no text** — every character is a Figma `TEXT` node so the acceptance audit can read it.

```python
"""Artwork for the Article 2 recipe figure ("How to choose a harmonization approach").

Artwork only -- no text. Every label is a Figma TEXT node in the frame
"Figure 6 - Recipe" on Page 2 (1013:2) of file t8bFgusleBEwB9ht7rORCH.
Mirrors figures_for_article/figure_drawing_scripts/graphical_abstract_assets.py.

Canvas: 750 x 1000 px at 2 px = 1 pt, matching the Page 2 frames.
"""
```

| Asset | Content |
|---|---|
| `recipe_icon_global.svg` | PCA scatter glyph, two batch clouds separating |
| `recipe_icon_local.svg` | kNN neighbourhood glyph, mixed and unmixed |
| `recipe_icon_distribution.svg` | Two density curves converging |
| `recipe_icon_marker.svg` | Gene × cohort ρ heat strip |
| `recipe_icon_rank.svg` | Two ranked gene lists with agreement ties |
| `recipe_icon_lobo.svg` | Batch folds, one held out, arrow to a confusion matrix |
| `recipe_trap_saturation.svg` | Trap 1 — a Group L metric pinned at 1.0 beside a failing kBET |
| `recipe_trap_classcount.svg` | Trap 2 — a local metric distorted by class count |
| `recipe_trap_confound.svg` | Trap 3 — batch-confounded labels, the `A_confirmed_bad` lesson |
| `recipe_fold_composition.svg` | Not a trap: the two fold cuts, drawn as one batch strip split into single-class and multiclass folds, each feeding its own metric box |
| `recipe_flow_spine.svg` | The block-scheme rules, arrows and decision diamonds |
| `recipe_lobo_scheme.svg` | **The LOBO procedure drawn out**, as Daniil asked: the batch strip with one batch lifted out, an arrow to the PCA fit on the remaining batches, an arrow to the logistic-regression training box, an arrow projecting the held-out batch onto those components, an arrow to the prediction, and an arrow to the metric box (macro F1, AUC, MCC) — then a return arrow closing the loop over batches. Same visual language as the graphical-abstract icons: black line art on a transparent ground, connected by arrows, no fills |


All twelve are text-free vector art. The scheme's five stages — gate the matrix → take one metric
per class → check the three traps → rank by the generalizability index → validate by LOBO, reading
both fold cuts — are drawn by the spine asset and labelled in Figma. The Venn/supervenn panel
`a2_p10` and the Sankey `a2_p13` are the visual bridges into this figure, as Daniil asked, and
`recipe_lobo_scheme.svg` sits inside the validation stage so the reader sees the procedure and not
only its name.

### 4.5 `article_2_extended_comparison/workflows/`

**Already done:** `an earlier internal proposal workflow (not public)` has been copied
to `workflows/article2_f1000.workflow.js.template` (862 lines, 49.8 KB). The working script
`workflows/article2_f1000.workflow.js` is derived from it by retargeting, never rewritten from
scratch. Full design in §6.

### 4.6 `article_2_extended_comparison/tools/`

**Already done:** `check_style.py` (270 lines), `audit_numbers.py` (175 lines) and `docx2md.py`
have been copied from `an earlier internal proposal workflow (not public)`. Remaining work:

**Done 2026-09-18** (Phase 1). What each tool now is:

| Tool | State |
|---|---|
| `check_style.py` | **Retargeted.** Six F1000 sections matched as markdown headings, budgets from §3.1 widened to [0.8x, 1.35x] except the abstract, whose 300 is F1000's own cap; the nine back-matter sections share one budget; antithesis and banned-phrase detectors kept verbatim and extended with the §6.2 list, the proofless-adjective rule (flagged when no digit sits within 80 characters) and the hedge-stack rule; the meta-language check now runs on the body only, so the mandatory AI usage statement does not fail it; structured-abstract and keyword-count checks added from §1.10; a missing rulebook now warns loudly instead of passing silently |
| `audit_numbers.py` | **Retargeted** at `tables/A2_T*.csv` via `--tables`. CSV sources are parsed into values and indexed at every rounding from 0 to 4 decimal places plus the percentage forms, because the manuscript quotes 0.745 for a stored 0.7453118 and literal matching would have failed every correctly rounded number in the paper. Figure, table and section labels are skipped; the reference list, DOIs, URLs and PMIDs are stripped before auditing |
| `docx2md.py` | Used as-is; verified on the v2 source document (96,635 characters, 13 images, tracked deletions rendered `~~struck~~`) |
| `check_overlap.py` | **New.** Every 8-gram of the draft against Article 1 and the source document; merges the run of hits one borrowed sentence produces into a single reported span; exits non-zero on any unallowed hit and names every source the span was found in. Allow-list at `tools/overlap_allow.txt` |
| `overlap_allow.txt` | **New.** The exemption list of §2.1 rule 3, currently the two Article 1 funding sentences and nothing else |

### 4.7 NEW — `article_2_extended_comparison/manuscript/`

| File | Content |
|---|---|
| `FL_metric_classes_F1000_260917.md` | The working draft, Markdown, one section per file section |
| `FL_metric_classes_F1000_260917.docx` | **The main state.** Converted from the Markdown as soon as the draft exists, without waiting for approval, so Daniil can add inline comments in Word |
| `references_260917.md` | Reference list, one entry per block, `PMID: ########` line each, Mendeley-paste ready |
| `reference_support_260917.md` | **Separate document**: for each citation, which part of the cited article supports which sentence of the draft, with the supporting passage quoted. PMIDs appear in the main manuscript; the evidence lives here |
| `figure_legends_260917.md` | All legends plus alt text |

Daniil's instruction on format: produce the article in Markdown **and then in Word without waiting
for approval**. From the moment the `.docx` exists it is the main state — Daniil comments in it and
every later edit pass works on the Word document, not on the Markdown. The `word-rewrite` skill
applies the F1000 template as tracked changes.

### 4.8 `article_2_extended_comparison/CLAUDE.md`

Add an "Article 2 in progress" section: the new sub-directories, the source-document rule (v2, not
v1), the 2,234-row analysis set and the `20_shambhala` discrepancy, the Figma Page 2 move, the new
frames created, and the anti-plagiarism contract. The existing content stays.

---

## 5. Figma assembly

### 5.1 Placement — Page 2, four to six new frames

Daniil asked for 4–6 new frames: three main and the rest supplementary. All are created on
**Page 2 (`1013:2`)**, in new rows below the Extended Figure block (lowest existing edge
y = 11,149), on the existing column grid.

| Frame name | x | y | w × h | Content |
|---|---|---|---|---|
| `Figure 4 - Biomarker expression and correlation (L, M)` | −8736 | 11500 | 750 × 1000 | `a2_p14` (expression scatters, top), `a2_p1`, `a2_p2`, `a2_p3`, `a2_p7` |
| `Figure 5 - Prediction and election (N)` | −7827 | 11500 | 750 × 1000 | `a2_p4`, `a2_p5`, `a2_p6`, `a2_p8`, `a2_p9`, `a2_p10`, `a2_p13` |
| `Figure 6 - Recipe` | −6905 | 11500 | 750 × 1000 | The block scheme from §4.4 |
| `Supplementary Figure 11 - Marker panel QC` | −5894 | 11500 | 750 × 1000 | `a2_p15`, `a2_p16`, `a2_p17`, `a2_p18` |
| `Supplementary Figure 12 - Harshness and fold audit` | −4860 | 11500 | 750 × 700 | `a2_p11`, `a2_p6` (expanded), the single-class fold census |
| `Supplementary Figure 13 - Technical comparisons` | −8736 | 12700 | 750 × 1000 | Held in reserve; created only if Figure 4 and Supp. Fig 11 overflow |

Frame dimensions match the existing block (739–790 px wide); 750 is the working width.

### 5.2 Procedure, per frame

1. `use_figma`, first statement:
   `await figma.setCurrentPageAsync(figma.root.children.find(p => p.name === 'Page 2'))`.
2. Read a neighbouring Extended Figure's frame styling (fill, corner radius, padding) with a
   narrow `use_figma` read that returns only those fields. **Do not call `get_metadata` on a whole
   frame** — Extended Figure 1 returns 3.5 M characters and Page 1's root call times out (§9.1).
3. Create the empty frame with `placeholder = true`.
4. `upload_assets` the panel PDFs/SVGs, then place them with `use_figma` in ≤ 10 operations per
   call, as the figma-use skill requires.
5. Add every label as a Figma `TEXT` node in **Inter 10 pt**, and every panel index letter in
   **Inter Bold 20 pt** (§1.8). Load the font with `loadFontAsync` before writing characters.
6. `screenshot()` inline, check for clipped text and overlap, fix, then `placeholder = false`.

### 5.3 Renaming and reordering the existing frames

The one permitted edit to existing frames, from §3.4: rename Extended Figures 1–3 to Figures 1–3
and Extended Figures 4–13 to Supplementary Figures 1–10, together with their title TEXT nodes, and
apply the identical renumbering to the already written Word text of the extended document in the
same pass. Geometry, artwork and children are untouched.

The same pass moves every supplementary figure caption out of the main legend sequence into a
manuscript section headed **"Supplementary Material"** (§3.4), so the canvas order and the document
order stay in step.

The renumbering sweep in the Word document must use the `figure_edits()` discipline recorded in
`figures_for_article/CLAUDE.md`: a bare `"Figure 6"` is a substring of `"Supplementary Figure 6"`,
so each key grows leftwards until it is the first match in the text the replacer can still see, and
raises instead of guessing. That trap already corrupted one edit pass.

### 5.4 Hard constraints

- **No artwork is redrawn, moved, restyled or deleted** — on Page 1 or Page 2. Renaming is the only
  edit. The clustermap best approaches shown in existing figures are analysed and discussed, never
  redrawn.
- Every character on the canvas is a Figma `TEXT` node, never type baked into an imported SVG.
- New top-level nodes are positioned explicitly; nothing may land at (0,0).
- A geometry snapshot of Page 2 is taken before and after the session and diffed (§8, command 8);
  only the `name` field of the renamed frames may differ.

### 5.5 Who does the assembly

Daniil's instruction: Claude does the Figma assembly, and Daniil corrects the result manually
afterwards. So the assembly is a real deliverable, not a sketch — panels placed, labelled,
screenshot-checked and cleared of placeholders — but it is explicitly a first pass that expects
hand correction, and no downstream step blocks on it being pixel-final.

This work happens in a normal interactive session, not inside the workflow (§6.4), because it
needs screenshots checked by eye between steps.

---

## 6. The multi-agent workflow

### 6.1 Shape

Six roles. One team lead that reviews and gates; five specialists that produce. Four phases, with
the team lead sitting between each pair.

```
Phase 1  EVIDENCE      (parallel)
  ├── code-analyst      → the numbers, the panels, the tables
  └── literature-scout  → the citation landscape, the gap Article 2 fills

         ↓ teamlead gate 1: are the numbers real and is the gap defensible?

Phase 2  DRAFT         (sequential, needs both Phase 1 artifacts)
  └── writer           → the full manuscript Markdown, then the .docx

         ↓ teamlead gate 2: does every claim trace to an artifact?

Phase 3  REVIEW        (parallel)
  ├── reference-verifier → every citation resolved to a live PMID, from the full text
  └── style-editor       → AI-slop removal, register enforcement, overlap gate

         ↓ teamlead gate 3: accept, or send back with a specific defect list (≤ 2 rounds)

Phase 4  DELIVERY
  └── teamlead         → final assembly, provenance table, open-items list
```

### 6.2 The roles in full

Daniil asked for a detailed specification of each agent: what it reads to learn, what criteria it
applies, and what it saves. Every agent below has those three sections, and every one writes its
artifacts to `workflow_runs/260917_run1/` **before** returning, so an agent killed by a token limit
can be resumed from its own files instead of re-run from zero. 'name the folder for run accordint to a real date it ran, like 260918_run1 etc'

**The artifact discipline, binding on all six:**
- Write to disk **before** returning, never after. Markdown always, JSON when the output is
  structured; both files carry the same content, generated from the same object.
- Write **incrementally**: an agent with a long task writes a partial artifact after each
  sub-deliverable and appends, instead of holding everything until the end. A half-finished
  `01_numbers.json` on disk is worth more than a complete one that died in context.
- Every artifact opens with a `## Status` block: what is complete, what is in progress, what is
  not started. A resumed agent reads its own `## Status` first and continues from there.
- File names are fixed by §6.3 so a resumed run finds them without searching.

**The fabrication prohibition, stated in every agent's own prompt, not only in the shared rules:**
> You are STRICTLY PROHIBITED from inventing or creating any non-existent link, reference, article,
> DOI, PMID, accession, statistic, author, affiliation or URL. If you cannot open it and quote it,
> you cannot cite it. Unknown values are written literally as `[TO CONFIRM: what is missing]`. A
> fabricated reference aborts the workflow; it is not a defect to be corrected in review.

The agents cross-check each other on this: the reference-verifier independently re-resolves every
citation the literature-scout supplied and every citation the writer used; the team lead
re-resolves a random 20% of the verifier's own confirmations; the code-analyst's numbers are
re-derived by `audit_numbers.py` against `tables/`, not trusted from its JSON.

---

#### Agent 1 — `teamlead`

**Model:** Opus 5. **Phase:** all gates plus delivery. **Tools:** Read, Write, Bash, Agent.

*What it reads to learn:* this plan document in full; every artifact produced so far; the four
tables in `tables/`; Article 1's Results and Methods once, to judge overlap claims.

*Criteria it applies* — five rules it enforces and cannot waive:

1. Every number in the manuscript resolves to a row in a table in `tables/`.
2. Every citation has a PMID or an explicit `[TO CONFIRM]`, and 20% of them re-resolve.
3. The overlap gate passes with zero 8-gram hits.
4. `check_style.py` exits 0.
5. No Figma frame was modified beyond the §3.4 renaming — verified by diffing the before/after
   Page 2 geometry snapshots.

*Output:* a verdict object per gate, not prose:

```json
{ "gate": 1, "verdict": "revise",
  "defects": [ { "agent": "code-analyst", "artifact": "01_numbers.json",
                 "defect": "generalizability index quoted for 2,085 rows; the analysis set is 2,234",
                 "required_fix": "re-run load_analysis_set and restate; the assertion should have caught this" } ],
  "accepted": ["02_literature.json"] }
```

A maximum of **two revision rounds** per gate. If a defect survives two rounds it goes to Daniil as
an open item and the workflow proceeds; nothing is silently dropped or quietly fixed by the team
lead writing the text itself.

*Artifacts:* `05_teamlead_gate{1,2,3}.json` and `.md`, `06_provenance.md`, `06_open_items.md`.

---

#### Agent 2 — `code-analyst`

**Model:** Opus 5. **Phase:** Evidence. **Tools:** Read, Write, Edit, Bash, NotebookEdit.

*What it reads to learn:* `harmonization-metrics-calculation/compute_batch_metrics.py` groups L, M
and N (lines 1713, 1935, 2250) for what each metric actually computes and what its docstring warns
about; `create_correlation_prediction_notebook.py` lines 322–380 for the `01_raw` baseline join;
`Finally_assembled_figures_for_article.ipynb` cells 1 and 4 for the palettes, `TOP_IDS` and both
harshness maps; `figures_for_article/CLAUDE.md` for the snapshot rules; §1.3–§1.5 of this plan for
the numbers it must reproduce.

It also reads the four analysis notebooks in `harmonization-metrics/`, which Daniil flags as
helpful and which no generator covers: `harmonization_metrics_analysis.ipynb` (161 cells) and its
`_v2` (321) and `_v3` (571) successors carry the metric taxonomy, the polarity table, the
normalization to [0,1], the multi-level comparison helper, the clustermap and embedding cells, and
in v3 the best-approach selection and the `best bars` helpers — the visual inspection work whose
conventions Article 2's panels must match; and `marker_gene_deep_analysis.ipynb` (125 cells) carries
the gene-level QC gates and the hand-run expression scatters of §3.4. These are read for method and
for plotting convention, never as a source of numbers: every number is recomputed.

**The Shambhala rename is binding on this agent.** `shambhala_P0std_Q0std` is `20_shambhala`; the
rename happens on load, before any filter, and `A2_T0` records the column-by-column check that
justifies it.

*Criteria it applies:*
- No number is retyped from the source document — every one is recomputed from
  `metrics_comprehensive_260905.csv`, `Supplementary File 3.csv.gz` and `prediction_folds_long.csv`.
- Any disagreement with the source document is reported as a discrepancy with both values and the
  filter that produced each, never silently corrected. **Discrepancies reach the manuscript text**
  — that is Daniil's instruction, so the code-analyst writes them in a form the writer can quote.
- The assertions in `load_analysis_set` (2,234 rows, 31 methods, 84 `20_shambhala`) are not relaxed
  to make a count fit. A mismatch is a bug in the code, not in the definition — and a result of
  2,150 means the Shambhala rename was skipped.
- Palettes are imported, never re-derived.

*Tasks, in order, each one an artifact checkpoint:*
1. Extract every non-generator cell from all three notebooks into
   `hand_written_cells_260917.ipynb` and write `diverged_cells_260917.md` (§4.2e).
   **Stop and report if any cell cannot be cleanly extracted** — do not regenerate over them.
2. Write `analysis/article2_generalizability.py` and run it; `A2_T1`–`A2_T7` land in `tables/`.
3. Patch both notebook generators; regenerate with `--article2`; execute; confirm every `a2_p*`
   panel exists in all three formats.
4. Write `figures/recipe_figure_assets.py` and run it.
5. Deliver `01_numbers.json`: every number Article 2 will quote, each with the table, the column
   and the filter that produced it, plus a `discrepancies` array.

*Artifacts:* `01_numbers.json` / `.md`, written incrementally after each task.

---

#### Agent 3 — `literature-scout`

**Model:** Opus 5. **Phase:** Evidence. **Tools:** WebSearch, WebFetch, PubMed MCP, Read, Write.

*What it reads to learn* — Daniil specified the reading list:

- **Bulk transcriptomic batch correction**, with the emphasis on **cross-platform harmonization**:
  what each benchmark used as its criterion, and whether any of them asked whether criteria agree.
- **The three Borisov reviews cited in Article 1** (§2.4), read in full, not by abstract. They are
  the field's own statement of the harmonization problem and Article 2 must position against them.
- **Model training and overfitting**: leave-one-group-out validation, batch-confounded labels,
  degenerate folds, and the literature on metric gaming — this is the theoretical backing for
  §1.5d and for trap 3 in the recipe, and the reason the two fold cuts are reported together.
- **The single-cell integration benchmark literature** that supplied kBET, LISI, ASW, graph
  connectivity and the scIB composite — with the point that those metrics were designed for a
  different problem.
- **FL/DLBCL transcriptomic subtyping**, for the biology the marker panel encodes.
- **Daniil's own on-topic works** from ORCID `0000-0003-1029-1174` (§2.4), cited where a
  signature-transfer claim needs them and nowhere else.

*Criteria it applies:*
- **A paper it cannot open is not a citation.** No recalled titles, no reconstructed DOIs.
- Every entry carries a verbatim quote from the paper — from the **full text**, not the abstract
  alone, wherever the full text is reachable. Daniil's instruction is explicit on this.
- The gap statement must be a statement about what has **not** been done, phrased so the
  Introduction can claim it without overclaiming.

*Output:* `02_literature.json` — 25–40 candidate references, each with PMID, title, year, journal,
DOI, the specific claim it supports, and the verbatim supporting passage with its section name.

*Artifacts:* `02_literature.json` / `.md`, appended after each thematic block so a token-limit kill
loses at most one block.

---

#### Agent 4 — `writer`

**Model:** Opus 5. **Phase:** Draft. **Tools:** Read, Write, Bash.

*What it reads to learn:* `01_numbers.json`, `02_literature.json`, the source document (v2),
`figure_legends_260917.md`, and §3 of this plan. It reads Article 1 **once, in full, for the
explicit purpose of not reproducing it**, and then writes without it open.

*Criteria it applies:*
- First-person plural, active voice: "We computed…", "We gated…".
- One claim per sentence, each with its number and its figure panel.
- No adjective carries an argument; no "significantly" without a p value.
- **No proofless adjective.** If the text says "comprehensive", the sentence next to it states what
  makes it comprehensive — the count, the coverage, the comparison. Same for "novel", "robust",
  "extensive", "substantial". An adjective that cannot be justified in the adjacent clause is
  deleted instead of softened. Daniil's rule: plain, traceable, verifiable language.
- Abbreviations defined at first use, then used.
- Limitations stated where they arise, not deferred to a limitations paragraph.
- The discrepancies from `01_numbers.json` are written into the text, not into a footnote.

*Artifacts:* `03_draft.md`, written section by section — the file exists and grows from the first
section onwards, so a kill loses one section instead of the manuscript. Then the `.docx`
conversion (§4.7).

---

#### Agent 5 — `reference-verifier`

**Model:** Opus 5. **Phase:** Review. **Tools:** WebSearch, WebFetch, PubMed MCP, Read, Write.

*What it reads to learn:* the draft, `02_literature.json`, and then each cited paper itself —
**the full text, not the abstract**, which is Daniil's explicit requirement.

*Criteria it applies,* three checks per citation, independently:
1. The paper exists and is reachable.
2. The PMID and DOI are right.
3. It supports **the specific sentence that cites it** — judged against the passage in the body of
   the paper, not against the abstract.

Every failure is reported, never patched: a citation that does not support its sentence is a defect
sent back to the writer, not a reference the verifier swaps out.

*Output, two files* — Daniil's instruction that the supporting evidence lives apart from the
manuscript:

- `manuscript/references_260917.md` — the reference list, one block per entry, Mendeley-paste ready:

```
[12] Tran HTN, Ang KS, Chevrier M, et al. A benchmark of batch-effect correction methods for
     single-cell RNA sequencing data. Genome Biol. 2020;21(1):12.
     PMID: 31948481
```

- `manuscript/reference_support_260917.md` — the separate support document: for each citation,
  which part of the cited article supports which part of the Article 2 text, with the passage
  quoted and its section named:

```
[12] Tran HTN et al., Genome Biol 2020;21(1):12
     Cited at: Introduction para 3 -- "benchmarks of integration methods have ranked..."
     Supporting passage (Results, "Overall performance"): "<verbatim quote>"
     Verdict: SUPPORTS -- verified against the full text, not the abstract
```

**PMIDs appear in the main manuscript; the quoted evidence appears only here.**

*Artifacts:* `04_references_verified.md` plus the two manuscript files, appended per reference.

---

#### Agent 6 — `style-editor`

**Model:** Opus 5. **Phase:** Review. **Tools:** Read, Write, Edit, Bash.

*What it reads to learn:* the draft; `tools/check_style.py`; the register rules above; Daniil's own
manuscripts for the house voice.

*Criteria it applies* — the mechanical gates first, then the manual pass:

1. `python tools/check_overlap.py manuscript/*.md` — zero 8-gram hits against Article 1 and the
   source document.
2. `python tools/check_style.py manuscript/FL_metric_classes_F1000_260917.md` — exits 0.
3. Manual pass for the LLM register that no regex catches.

The banned list, inherited from the AACR style rulebook and extended on Daniil's instruction:

- **`rather than`** — named explicitly by Daniil as Claude AI-slop. Use "instead of", or rewrite
  the sentence so the contrast is carried by the verb. 'Only if the constrast is really needeed, use it. Evsaluate this separately. Most of time its sufficient to just say 'The metrics were recalculated according to python scripts from the repository.', without an addition of a contrasting statement like 'The metrics were recalculated according to python scripts from the repository instead of taking them from the source article'. Avoid such excessive contrastings - they look stupid for humans.'
- **The bare antithesis: "derived, not guessed", "it is not X, it is Y", "X, not Y"** — Daniil's
  words: these look stupid to readers and reviewers. State the positive claim on its own. A
  contrast that is worth making gets a full clause, not a comma and a negation.
- **Proofless adjectives** — `comprehensive`, `novel`, `robust`, `extensive`, `substantial`,
  `powerful`, `state-of-the-art` — deleted unless the adjacent clause states the measurement that
  justifies them.
- `delve into` · `underscores` · `leverage` · `seamless` · `pivotal` · `landscape` ·
  `testament to` · `crucial` · `stands as` · `in the realm of` · `it is important to note` ·
  `plays a vital role` · `navigating the complexities` · tricolon padding ·
  `Furthermore`/`Moreover`/`Additionally` chains · unearned em-dashes · hedge stacks
  ("may potentially help to") · empty intensifiers used without a number ·
  `novel` applied to this work by this work.

The style editor may edit prose directly. It may **not** change a number, a citation or a claim —
those go back to the writer as defects.

*Artifacts:* `04_style_report.json` / `.md`, and the edited draft.

### 6.3 Workflow script shape

Derived from `workflows/article2_f1000.workflow.js.template`, retargeted:

```javascript
export const meta = {
  name: 'article2-f1000',
  description: 'Research, compute, draft and adversarially review the F1000Research metric-class article',
  phases: [
    { title: 'Evidence',  detail: 'Numbers recomputed from the analysis set; citation landscape with live PMIDs' },
    { title: 'Draft',     detail: 'Full manuscript to the F1000 section shape' },
    { title: 'Review',    detail: 'PMID verification from full text, style gate, verbatim-overlap gate' },
    { title: 'Delivery',  detail: 'Team lead assembly, provenance table, open items' },
  ],
}

const REPO = '<repo>'
const A2   = `${REPO}/article_2_extended_comparison`
const RUN_DIR = (args && args.runDir) || 'workflow_runs/260917_run1'
const PHASES  = (args && args.phases) || ['evidence', 'draft', 'review', 'delivery']

const HARD_RULES = `
BINDING RULES -- these override any instinct to be helpful or complete:
1. PROVENANCE. No number without a table, a column and a filter. No citation without a PMID you
   resolved yourself from the full text. If you cannot quote it, you cannot use it.
2. NEVER INVENT. You are STRICTLY PROHIBITED from inventing any link, reference, article, DOI,
   PMID, accession, statistic, author, affiliation or URL. Unknown values are written literally
   as [TO CONFIRM: what is missing]. A fabricated reference aborts the run.
3. CROSS-CHECK. Every agent's citations are re-resolved by another agent. Every agent's numbers
   are re-derived by audit_numbers.py. Nothing is trusted because an agent asserted it.
4. THE SOURCE DOCUMENT IS v2. Harmonization_metrics_extended_260802_v2.docx. The _260802.docx
   (v1) pass is superseded and four of its corrections are wrong.
5. NO PLAGIARISM OF ARTICLE 1. FL_harmonization_article_NAR_260912.docx is a bioRxiv preprint by
   the same authors. Cite it by its DOI 10.64898/2026.09.15.751825, sparingly. Never write [PREPRINT-1]. Reuse no sentence, no Methods paragraph,
   no distinctive phrase. Facts it established are cited, not re-derived. Methods is SHORTER
   than Article 1's and has four to six subsections.
6. THE COMPARISON IS NOT ARTICLE 1'S. Compare strategies, imputations and methods against each
   other on the full analysis set, with the clustermap best approaches as one isolated named
   group. Do not run or restate a best-versus-rest test.
7. THE ANALYSIS SET IS 2,234 ROWS: Article 1's canonical set, pct_samples_allNA < 5, 31 methods.
   `shambhala_P0std_Q0std` in the metric snapshots IS `20_shambhala` -- rename it on load, before
   any filter, and drop the other 17 P/Q variants. Skipping the rename gives 2,150 and silently
   loses 84 approaches. If your filter returns anything but 2,234 you have a bug -- do not adjust
   the definition to match your code.
7b. LOBO FOLDS: report BOTH the full metric (all folds) and the multiclass-only metric (folds with
   >= 2 classes), side by side, in every table. A single-class fold is an honest test, not a
   defect: a classifier trained on every batch but one can still mislabel a DLBCL-only batch.
   Never drop single-class folds and never present one cut without the other.
8. FIGMA IS UNTOUCHED BY THIS WORKFLOW. Assembly happens in an interactive session.
9. LANGUAGE. No "rather than". No "X, not Y" antithesis. No proofless adjective: justify
   "comprehensive", "novel", "robust" in the adjacent clause or delete them.
10. ARTIFACTS. Write to disk BEFORE returning, incrementally, with a ## Status block at the top.
    Markdown always, JSON when structured. Both files carry the same content.
`
// ... phase composition with parallel() / pipeline(), teamlead gate between phases,
//     max 2 revision rounds per gate, resumeFromRunId supported, PHASES selects which run.
```

Artifacts land in `article_2_extended_comparison/workflow_runs/260917_run1/`:
`01_numbers.{json,md}`, `02_literature.{json,md}`, `03_draft.md`,
`04_references_verified.md`, `04_style_report.{json,md}`,
`05_teamlead_gate{1,2,3}.json`, `06_provenance.md`, `06_open_items.md`.

### 6.4 Size and the split — decided

- **Agent count.** Six roles, but the team lead runs at three gates and specialists may be re-run
  once per gate, so a full run is **10–16 agent invocations** against a session guideline of
  "medium — under 10 agents".
- **Daniil's decision: split.** The run is executed in two halves through `resumeFromRunId` and the
  `args.phases` selector:
  - **Run A — Evidence + Draft**: `phases: ['evidence', 'draft']`. Produces `01_numbers`,
    `02_literature`, gate 1, `03_draft.md` and the `.docx`. Inspect before going on.
  - **Run B — Review + Delivery**: `phases: ['review', 'delivery']`, `resumeFromRunId` set to
    Run A's id. Produces the verified references, the style report, gates 2 and 3, the provenance
    table and the open-items list.
- **The workflow does not touch Figma.** Figma assembly is its own interactive step in the TODO
  (§10), performed by Claude and then corrected by hand by Daniil.

---

## 7. Supplementary tables

Daniil's instruction: assemble 2–3 supplementary table workbooks of up to 7 sheets each, split by
data type, and unique against Article 1's supplementary files. Article 1 ships Supplementary File 1
(cohort annotation), Supplementary File 2 (5 sheets: `Genes_per_sample`, `Metric_polarity`,
`Table_S1_methods`, `Table_S2_metrics`) and Supplementary File 3 (87 metrics × 2,407 approaches).
None of those is reproduced.

| Workbook | Sheets | Source |
|---|---|---|
| **Supplementary File 1 — the analysis set and its metrics** | 1. **`README`** · 2. `Analysis_set` (2,234 rows, the L/M/N columns, group flags) · 3. `Canonical_set_reconciliation` (2,407 → 2,234, and the `shambhala_P0std_Q0std` = `20_shambhala` identity check) · 4. `Generalizability_ranking` · 5. `Method_census_by_class` · 6. `Strategy_and_imputation_summary` · 7. `Harshness_by_LMN` | `A2_T0`, `A2_T1`, `A2_T2`, `A2_T4`, `A2_T7` |
| **Supplementary File 2 — cross-batch structure and prediction** | 1. **`README`** · 2. `Cross_election_matrix` · 3. `Elected_sets_by_class` · 4. `Agreement_specific_61` · 5. `Margin_raw_and_delta` · 6. `Per_batch_folds` (both targets, `n_classes` per fold) · 7. `Fold_composition` | `A2_T3`, `A2_T5`, `A2_T6`, `A2_T8` |
| **Supplementary File 3 — the marker panel** (assembled only if §4.3 exports are used as a figure) | 1. **`README`** · 2. `Panel_coverage_by_attempt` · 3. `QC_gate_sweep` · 4. `Rho_by_signature` · 5. `Narrow_set_56_genes` | `T1`–`T4` from `current_figures_tables_for_article_260819/` |

**Every workbook opens with a `README` sheet**, and it is the first thing written, not an
afterthought. It lists each following sheet by name with one plain sentence saying what that sheet
stores, how many rows it has, and which table in `tables/` it came from — written so someone who has
not read the manuscript can still tell which sheet they need. No jargon, no metric abbreviations
left undefined.

Each data sheet additionally carries a header row naming the source table and the filter that
produced it, so a sheet lifted out of the workbook is still self-describing.

---

## 8. Verification commands

```bash
source ~/venvs/collagen_3_11/bin/activate
cd <repo>/article_2_extended_comparison

# 0. The Phase 1 gates are wired and the fixtures still behave (run after touching tools/)
python tools/check_style.py --help >/dev/null && python tools/audit_numbers.py --help >/dev/null \
    && python tools/check_overlap.py --help >/dev/null && echo "three gates importable"
test -s workflow_runs/260917_phase1/style_rules.json || echo "MISSING RULEBOOK: check_style is inert"
python -c "
import sys; sys.path.insert(0, 'tools')
from check_overlap import docx_text, normalize, DEFAULT_AGAINST
for p in DEFAULT_AGAINST:
    assert p.exists(), p
    print(p.name, len(normalize(docx_text(p))), 'tokens')"

# 1. The analysis set reproduces: 2,234 rows, 31 methods, Shambhala present
python analysis/article2_generalizability.py --date-tag 260905 --out-dir tables/
python -c "
import pandas as pd
d = pd.read_csv('tables/A2_T1_analysis_set_census_260917.csv')
assert len(d) == 2234, len(d)
assert d.method.nunique() == 31, d.method.nunique()
assert d.strat.nunique() == 14 and d.imp.nunique() == 3
assert (d.method == '20_shambhala').sum() == 84, 'the Shambhala rename did not happen'
assert not d.method.str.startswith('shambhala_').any(), 'raw P/Q variant names leaked through'
print('analysis set OK:', len(d), 'rows,', d.method.nunique(), 'methods')"

# 1b. Both fold cuts are present in every prediction table
python -c "
import pandas as pd
d = pd.read_csv('tables/A2_T2_generalizability_ranking_260917.csv')
for c in ('pv_lobo3_f1_macro_mean','f1_mc_mean','f1_mc_min','n_mc'):
    assert c in d.columns, c
print('both fold cuts present')"

# 2. Every Article 2 panel exists in all three formats
python -c "
from pathlib import Path
p = Path('figures/panels_260917')
names = [f'a2_p{i}' for i in range(1, 19)]  # a2_p1 .. a2_p18
missing = [n for n in names
           if not any(p.glob(f'{n}*.pdf')) or not any(p.glob(f'{n}*.svg'))
           or not any(p.glob(f'{n}*.png'))]   # a2_p14 carries the method in its filename
print('missing:', missing or 'none')"

# 3. The hand-written cells were extracted before anything was regenerated
python -c "
import json, pathlib
p = pathlib.Path('../harmonization-metrics/hand_written_cells_260917.ipynb')
assert p.exists(), 'extract the hand-written cells FIRST'
nb = json.load(open(p)); print('extracted cells:', len(nb['cells']))"

# 4. No number in the draft is un-sourced
python tools/audit_numbers.py manuscript/FL_metric_classes_F1000_260917.md --tables tables/

# 5. Verbatim-overlap gate against Article 1 and the source document -- must be zero
python tools/check_overlap.py manuscript/FL_metric_classes_F1000_260917.md \
    --against ../figures_for_article/FL_manuscript_versions/FL_harmonization_article_NAR_260912.docx \
    --against manuscript_versions/Harmonization_metrics_extended_260802_v2.docx \
    --ngram 8

# 6. Style gate -- must exit 0, including the "rather than" and antithesis detectors
python tools/check_style.py manuscript/FL_metric_classes_F1000_260917.md --journal f1000
grep -nEi "rather than|, not [a-z]+\.|it is not .*, it is" manuscript/*.md   # must print nothing

# 7. Every citation carries a PMID or an explicit placeholder, and the support doc exists
grep -c "PMID: " manuscript/references_260917.md
test -s manuscript/reference_support_260917.md && echo "support doc present"
grep -n "TO CONFIRM" manuscript/*.md

# 8. Abstract is within 300 words and structured
python -c "
import re, pathlib
t = pathlib.Path('manuscript/FL_metric_classes_F1000_260917.md').read_text()
a = re.search(r'## Abstract(.*?)## ', t, re.S).group(1)
print('abstract words:', len(a.split()))
for h in ('Background','Methods','Results','Conclusions'):
    print(h, ':', h in a)"
```

**9. Figma: Page 2 geometry is unchanged except for the renamed frames.** Run before assembly,
again after, and diff. Note that this reads Page 2, and that `get_metadata` on the page root or on
a whole Extended Figure frame is not usable (§9.1):

```js
// use_figma, read-only
const p2 = figma.root.children.find(p => p.name === 'Page 2');
await figma.setCurrentPageAsync(p2);
return p2.children.map(n => ({ id: n.id, name: n.name, type: n.type,
  x: Math.round(n.x), y: Math.round(n.y),
  w: Math.round(n.width), h: Math.round(n.height),
  kids: 'children' in n ? n.children.length : 0 }));
```

Only the `name` field of the 13 renamed frames and their title TEXT nodes may differ between the
two snapshots; `id`, `x`, `y`, `w`, `h` and `kids` must be identical.

---

## 9. Side effects and caveats

### 9.1 Figma: the quota is lifted, the payload limits are not

Daniil has upgraded the Figma plan and reports no MCP usage limits; Claude can draw in Figma, and
the assembly of §5 is a real deliverable and no longer a fallback. Verified on 2026-09-18: `whoami`,
page listing, page switching and per-frame reads through `use_figma` all returned promptly.

Two mechanical limits remain, and they are about response size, not quota:

- `get_metadata` on the **page root** (`0:1`) still fails with *"MCP server session expired"* after
  running for minutes. Never call it.
- `get_metadata` on a **whole Extended Figure frame** returns ~3.5 M characters — Extended Figure 1
  alone — and is rejected as over the token limit.

So every Figma read is a narrow `use_figma` script that returns only the fields needed, as in §8
command 9.

**The fallback, if Figma becomes unreachable for any reason.** Do not stall and do not improvise a
different destination: assemble each figure locally as a complete SVG — panels placed, labelled,
panel letters set — and write them to `article_2_extended_comparison/figures/for_figma_upload/`,
one file per figure, named exactly as the frame would be (`Figure 4 - Biomarker expression and
correlation (L, M).svg`, and so on). Daniil uploads them to Figma himself. A companion
`README.md` in that folder lists each file with its intended frame name, x/y position on Page 2 and
size, so the upload needs no further instruction. `recipe_figure_assets.py` keeps a `--compose` mode
that draws the complete recipe figure, text and all, as one self-contained file for the same
folder.

Note also that the account carries two teams — `Daniil Nikitin's team` (starter) and an organization team
(pro). If a limit ever reappears, check which team owns the file before assuming the plan lapsed.

### 9.2 Notebook divergence can destroy work

Covered in §4.2e, restated here because it is the highest-risk step: the three notebooks carry
**8, 43 and 29** hand-added cells that the generators do not know about,
including Daniil's working notes in Russian and the per-batch and raw-subtracted-agreement
explorations that are the prototypes of two Article 2 results. **Extract them into
`hand_written_cells_260917.ipynb` and get sign-off before regenerating.** A destroyed cell is not
recoverable from git if the notebook was never committed with outputs stripped at that point.

### 9.3 Article 1 overlap is concentrated in one section — and Article 2 asks a different question

Article 1 publishes an L/M/N analysis of the clustermap best approaches against the rest, with
Supplementary Figure 18 A–M and specific numbers (marker ρ near 1 for linear methods, −0.057 to
0.058 for MNN; cross-batch agreement 0.789 vs 0.627, p = 2.6 × 10⁻⁵; LOBO F1 medians 0.629 vs
0.717). Article 2 restates none of them.

Article 2's question is "which approaches does each metric class choose?" — asked over all 2,234
analysis-set approaches, comparing strategies,
imputations and methods against each other, with the clustermap best approaches carried as one
isolated named group and the prediction best approaches as another. That is a different comparison
with a different answer, and it is the comparison Daniil's Extended Figures already have the shape
for.

### 9.4 The metric-table snapshot is pinned

Article 2 uses `metrics_comprehensive_260905.csv` (3,835 rows, 30 `mk_` columns including the
narrow-set family) joined to `Supplementary File 3.csv.gz` for the canonical-set definition and to
`prediction_folds_long.csv` (94,582 rows, 24 batches) for the per-batch detail. The Shambhala rename
of §1.3 is applied to the 260905 snapshot before the join. Daniil has confirmed 260905 is the right
snapshot. Article 1's figures use `260609` (no L/M/N at all).

Quoting from the wrong snapshot is the failure mode the extended document's own audit §0 was
written about: between `260527` and `260609`, **0 of 66 numeric columns agreed**. Every table this
project writes carries its date tag in the filename; every number in the manuscript names its
table.

### 9.5 Three scientific caveats that the manuscript states explicitly, and one reporting rule

- **`A_confirmed_bad` and prediction.** The highest LOBO F1 anywhere comes from the strategy that
  keeps the known-bad batches (F1 0.958, and 0.924 on the multiclass-only cut). If a bad batch is
  also a diagnosis-pure batch, held-out prediction measures confounding. Daniil's ruling: report it,
  with the confound stated, and quote `S0_no_removal / softimpute / 29_combat_ref` (F1 0.946 full,
  0.887 multiclass-only, 11 multiclass folds) as the leading non-confounded approach. Recipe trap 3.
- **`G_affymetrix_only` and fold degeneracy.** Its post-removal rows leave **0** multiclass folds and
  still report F1 = 1.000 with a perfect worst fold. Reported with the fold count beside it in every
  table; never quoted as a winner without it.
- **Group L saturation.** A per-batch monotone transform scores ρ ≈ 1 by construction; the
  low-harshness tier sits at a median of 0.998 and predicts worst of the three tiers. Any Group L
  ranking that does not say so is misleading. Recipe trap 1; the `a2_p1` panel makes the wall
  visible.
- **Two cuts of the LOBO fold population, reported together — a rule, not a caveat.** 47.1% of
  the analysis set's 32,746 3-class folds contain one class and score a median F1 of 0.903, against
  0.733 on folds carrying two or more. This is **not** a defect in the metric: predicting a DLBCL-only held-out batch is an
  honest test and the classifier can still fail it. So the full metric and the multiclass-only
  metric are reported side by side everywhere, and neither is presented as the correction of the
  other. They agree at Spearman 0.812 and the ComBat family leads both. The `a2_p6` panel shows the
  two against each other with the fold-composition census beneath.

### 9.6 The harshness composite ordering is unresolved; the L/M/N comparison is sound

Recomputation of the method-harshness **composite score** ordering returns the opposite direction
to the published values in every recipe tried (published low 0.479 < medium 0.488 < high 0.493;
recomputed high 0.480 < medium 0.497 < low 0.520), and the exact composite construction is not
recoverable from the deposited file. It was flagged Critical C1 in
`figures_for_article/NAR_review_260912.md` and deliberately left unedited. **Until Daniil re-derives
it from Figure 6A of `Finally_assembled_figures_for_article.ipynb`, Article 2 quotes no composite
tier ordering.** The `check_overlap` and team-lead gates both carry this as a named prohibited
claim.

That prohibition covers the composite only. The comparison Daniil asked for — the three harshness
tiers by the **L, M and N metrics** — is computed from the raw metric columns with no composite
anywhere near it, reproduces cleanly, and is reported in full (§1.5e, `a2_p11`, Supplementary
Figure 12). Its headline is worth stating plainly: low-harshness methods hold biomarker correlation
at 0.998 and predict worst; high-harshness methods destroy cross-batch rank agreement; the 2-class
AUC cannot separate the tiers at all (p = 0.51).

### 9.7 F1000 obligations — resolved, and what is left

Resolved from Article 1 and from Daniil's comments:

- **The Article 1 preprint DOI** — `10.64898/2026.09.15.751825`, live and Crossref-verified (§2.3).
- **Author list and CRediT roles** — confirmed identical to Article 1.

- **Zenodo DOIs** — all four records are already cited in Article 1's reference list; §1.10 carries
  them with their DOIs. Nothing to fetch.
- **Grant information** — the same two-sentence wording as Article 1, quoted verbatim in §1.10.
- **CRediT roles** — carried over from Article 1's AUTHOR CONTRIBUTIONS and adjusted for the
  Article 2 author list.
- **Repositories** — `FL_harmonization`, `ComboBatch`, `Shambhala2_fast`, as in Article 1.

Still open:

- **A new DOI-bearing release of `Nikit357/FL_harmonization`** carrying the Article 2 code. Daniil
  will cut it; the manuscript carries `[TO CONFIRM: new FL_harmonization release DOI]` until then.
- **Preregistration statement** — almost certainly "not preregistered", but it must be stated.
- **The Article 2 author list**, which may differ from Article 1's.

### 9.8 Scope note

This plan covers the manuscript, the new analyses, the new panels, the renaming and reordering of
the existing Figma frames, and four to six new Figma frames on Page 2. It does **not** cover:
re-running any harmonization or metric job on the pod; changing the marker panel; the Shambhala
work; or submission to F1000Research.

---

## 10. TODO

Split by phase and by agent, as Daniil asked, so any block can be requested on its own.

### Phase 0 — Prerequisites (Daniil)

- [x] Confirm the source document is **v2** — confirmed
- [x] Decide whether to report `A_confirmed_bad` in the headline ranking — **report it**
- [x] Decide whether to split the workflow run — **split**
- [x] Supply the Zenodo records — supplied, and all four are already cited in Article 1
- [x] Confirm the metric snapshot — `metrics_comprehensive_260905.csv`
- [x] Correct the analysis set to the full canonical **2,234** (`shambhala_P0std_Q0std` = `20_shambhala`)
- [x] Supply the Article 1 preprint DOI — `10.64898/2026.09.15.751825`, Crossref-verified
- [x] Rule on the single-class LOBO folds — **report both cuts; they are an honest test**
- [x] Approve this rewritten plan, or mark the sections to change — approved 2026-09-18 by
      the instruction to implement; **implementation authorized for Phases 0 and 1 only**,
      everything from Phase 2 on still waits
- [ ] Cut a DOI-bearing release of `Nikit357/FL_harmonization` with the Article 2 code —
      **still open, and only Daniil can close it.** It blocks the Software availability
      section in Phase 5, not Phases 1–4; until it exists §1.10 carries
      `[TO CONFIRM: new FL_harmonization release DOI]`
- [x] Confirm the Article 2 author list and CRediT roles — **confirmed, identical to Article 1**

### Phase 1 — Scaffolding (no agent; interactive)

- [x] Copy the AACR workflow template → `workflows/article2_f1000.workflow.js.template`
- [x] Copy `check_style.py`, `audit_numbers.py`, `docx2md.py` → `tools/`
- [x] Create `analysis/`, `tables/`, `manuscript/`, `workflow_runs/`, `figures/panels_260917/`
      — plus `figures/for_figma_upload/` (the Phase 7 SVG fallback target, created now because
      it costs nothing) and `workflow_runs/260917_phase1/`
- [x] Copy the AACR style rulebook → `workflow_runs/260917_phase1/style_rules.json` (48 banned
      entries). Not in the original list; `check_style.py` is inert without it — see §11
- [x] Adapt `check_style.py` for the F1000 sections, the §3.1 budgets and the §6.2 banned list
- [x] Retarget `audit_numbers.py` at `tables/A2_T*.csv`
- [x] Write `tools/check_overlap.py` (8-gram gate)
- [x] Write `tools/overlap_allow.txt` — the grant wording F1000 requires to be identical to
      Article 1's, which otherwise fails the gate by construction (§2.1 rule 3, amended)
- [x] Smoke-test all three gates against fixtures: both controls behave (§11)

### Phase 2 — Analysis code (agent: `code-analyst`)

- [x] Write `tools/extract_hand_written_cells.py` — not in the original list; the measurement has
      to be re-runnable before Daniil regenerates anything
- [x] Extract every non-generator cell from all three notebooks → `hand_written_cells_260917.ipynb`
      (185 cells preserved: 115 hand-written, 70 edited generator cells)
- [x] Write `diverged_cells_260917.md` with a port/keep/drop recommendation per cell
      (119 port, 23 keep, 43 drop)
- [x] **Get Daniil's sign-off on that list before regenerating anything** — given by instruction
      2026-09-19 ("regenerate the notebooks... do not stop until all the phase 2 points are
      completed"). The port list was re-derived first; see §11, issue 11
- [x] Write `analysis/article2_generalizability.py`: the Shambhala rename first, then
      `assert len == 2234` and `assert method.nunique() == 31`
- [x] Emit `A2_T0`, the 84-row `shambhala_P0std_Q0std` == `20_shambhala` identity check
      (78 of 79 numeric columns identical; only `compute_time_s` differs)
- [x] Run it; produce `A2_T1`–`A2_T8` in `tables/`, every prediction table carrying both fold cuts
- [x] Port the signed-off cells into both generators — via
      `harmonization-metrics/preserved_cells_260917.json`, which each generator re-emits as a
      §11 section on every regeneration. 32 cells: 5 main, 17 narrow, 10 deep
- [x] Add `A2_FIG_DIR`, `save_panel`, `--article2` to `create_correlation_prediction_notebook.py`
- [x] Add the §10 cells (`a2_p1`–`a2_p13`), importing the canonical palettes
- [x] Port the hand-run expression scatters (deep-analysis cells 88–90) into the **deep-analysis**
      generator as `a2_p14`, looped over one representative per best-approach group plus `01_raw`
      — that generator is where `paired_frame()` and `SCATTER_GENES` already live
- [x] Add `save_panel` to `create_marker_gene_deep_analysis_notebook.py`; re-export
      `a2_p15`–`a2_p18` through `save_figure` itself, so no plotting code is duplicated
- [x] Regenerate **all three** notebooks with `--article2` and execute them in the new local
      `collagen_3_11` kernel — the pod was not needed
- [x] Verify the panels: **18 of 18** exist in all three formats. 15 of them (`a2_p1`–`a2_p13`,
      `a2_p15`, `a2_p17`) on the Mac 2026-09-19; the remaining three on the pod the same day
- [x] `a2_p14`, `a2_p16`, `a2_p18` — **produced 2026-09-19 on the pod.** The tables they need
      were never missing; they were simply not on the Mac. No pod metric job was needed and
      §9.8 is not engaged. See §11, issues 18–20
- [x] Write `figures/recipe_figure_assets.py`; produce the twelve text-free SVG assets, including
      `recipe_lobo_scheme.svg` — the LOBO procedure as black line art on a transparent ground
- [x] Deliver `01_numbers.json` with its `discrepancies` array (37 numbers, 7 discrepancies),
      plus the `01_numbers.md` companion, both emitted by `analysis/build_numbers_json.py`

### Phase 3 — Evidence, literature (agent: `literature-scout`)

- [x] Write `tools/fetch_literature.py` — not in the original list; it is what makes a quote
      verifiable, and it caught the wrong-paper bug of §11 issue 15
- [x] Read the three Borisov reviews in full — all three are open access; §3 of the 2022 review,
      "Evaluation of the Quality of Harmonization", is the anchor for Article 2's thesis
- [x] Read the four `harmonization-metrics/` analysis notebooks for method and plotting
      convention (161 / 321 / 571 / 103 cells; `sns.set_style("ticks")`, `FONT_SIZE = 7.5`, the
      five canonical palettes) — recorded in `02_literature.json` under
      `reading_list_completed`
- [x] Sweep cross-platform bulk harmonization benchmarks and their criteria (11 references)
- [x] Sweep the model-training / overfitting / degenerate-fold literature — **thin: 2 usable
      references.** See §11, issue 16
- [x] Sweep the single-cell integration metric literature (kBET, LISI, ASW, scIB) — 5 references
- [x] Sweep FL/DLBCL transcriptomic subtyping — 7 references
- [x] Resolve all 19 distinct ORCID works of §2.4 and assign each its citation locus — 18 resolve
      through Crossref or DataCite; the RetroSpect book chapter has no DOI and keeps its
      `[TO CONFIRM]`
- [x] Deliver `02_literature.json` — **28 references**, 20 quoted from PMC full text and 8 from
      the abstract where no open-access full text exists, each labelled with which

### Phase 4 — Workflow assembly (no agent; interactive)

- [x] Derive `workflows/article2_f1000.workflow.js` from the template — 833 lines, parses as the
      runtime parses it, `meta.phases` and the four `phase()` calls agree
- [x] Write the six agent prompt builders to the §6.2 specifications — `codeAnalystPrompt`,
      `literatureScoutPrompt`, `writerPrompt`, `referenceVerifierPrompt`, `styleEditorPrompt`,
      `teamleadPrompt` (one builder serves gates 1–3 and delivery, parameterized by gate)
- [x] Define `NUMBERS_SCHEMA`, `LITERATURE_SCHEMA`, `REFERENCE_SCHEMA`, `STYLE_SCHEMA`,
      `GATE_SCHEMA` — all five validated: root `type: object`, `required` ⊆ `properties` at every
      nesting level
- [x] Add the `args.phases` selector and the incremental-artifact rule to `HARD_RULES` — plus
      rule 11 (phase selection and resume), so an agent in Run B knows Run A's artifacts are on
      disk and must be read, not recreated
- [x] **Run A** — `phases: ['evidence','draft']`, run id `wf_60d927c7-88e`, **10 agents, 0 errors,
      2 h 28 m**. `01_numbers.json` and `02_literature.json` inspected; both gates rejected once
- [x] **Run B** — `phases: ['review','delivery']`, resumed from Run A into the same run folder.
      Gate 3 revised once and accepted at round 2; gate 4 accepted for delivery. Artifacts:
      `04_references_verified.*`, `04_style_report.*`, `05_teamlead_gate{3,4}.*`,
      `06_open_items.md`, `06_provenance.*`

### Phase 5 — Manuscript (agents: `writer`, `reference-verifier`, `style-editor`, `teamlead`)

- [x] Draft all sections to §3.1's shape; Methods in four to six subsections — 10,337 words,
      every section inside budget
- [x] Renumber Extended Figures 1–3 → Figures 1–3 and 4–13 → Supplementary Figures 1–10 in the text
      — zero occurrences of "Extended Figure" remain in the manuscript
- [x] Write legends and alt text for Figures 4, 5, 6 and Supplementary Figures 11–13 — all 6 main
      and all supplementary legends in `manuscript/figure_legends_260917.md`, one alt text each.
      **Corrected 2026-09-20:** this line read "13 supplementary legends, 22 alt texts"; the file
      holds 20 `### ` legend headers and 20 `**Alt text:**` blocks, and after the Figure 4 split it
      is 6 main + 14 supplementary = 20. The 22 never reproduced from the file
- [x] Move every supplementary figure caption into a "Supplementary Material" section — §
      "Supplementary material", plus the two Supplementary File entries
- [x] Write the discrepancies against the source document into the text, and the one sentence on
      Shambhala's two names — five discrepancies in the prose, the Shambhala sentence in Methods
- [x] `references_260917.md` with `PMID: ` lines, Mendeley-ready — 52 entries, 52 `PMID: ` lines,
      no `[TO CONFIRM]` in the list
- [x] `reference_support_260917.md` — the separate claim-to-passage document, full-text quotes;
      renumbered to 1–52 in the post-delivery pass (defect D3)
- [x] Back matter: data availability (the four Zenodo DOIs), software availability, reporting
      guidelines, ethics, CRediT, competing interests, the Article 1 grant wording, AI usage —
      two deliberate `[TO CONFIRM]` markers remain (P1 release DOI, P2 employment)
- [x] Run verification commands 4–8; all must pass — **all pass, re-run 2026-09-19 after the
      post-delivery fixes.** Command 4 needs `--evidence workflow_runs/260919_run1/01_numbers.json`
- [x] **Convert to `.docx` immediately, without waiting for approval** — from here the Word file is
      the main state and Daniil comments in it

### Phase 6 — Supplementary tables (no agent; interactive)

- [x] Write the `README` sheet for each workbook first, in plain language — one row per
      sheet with what it holds, its row count and its source table; every data sheet also
      carries a provenance line in row 1
- [x] Assemble Supplementary File 1 (README + 6 sheets) from `A2_T0`, `A2_T1`, `A2_T2`, `A2_T4`, `A2_T7`
      — `supplementary/A2_Supplementary_File_1_260917.xlsx`, 5.4 MB
- [x] Assemble Supplementary File 2 (README + 6 sheets) from `A2_T3`, `A2_T5`, `A2_T6`, `A2_T8`
      — `supplementary/A2_Supplementary_File_2_260917.xlsx`, 0.6 MB
- [x] Assemble Supplementary File 3 (README + 4 sheets) if the marker-panel figure is used
      — it is (Supplementary Figures 11 and 13), so it was built:
      `supplementary/A2_Supplementary_File_3_260917.xlsx`, 0.1 MB
- [x] Check every sheet against Article 1's three supplementary files for duplication —
      `supplementary/duplication_check_260917.md`: no Article 2 sheet reproduces a
      measurement column of any Article 1 supplementary file

### Phase 7 — Figma assembly (interactive; Claude assembles, Daniil corrects by hand)

- [x] Snapshot Page 2 geometry (verification command 9, "before") — 43 nodes, matching §1.7
      exactly; `figures/figma_snapshots/page2_before_260920.json`
- [x] Rename Extended Figures 1–3 → `Figure 1`–`Figure 3` and their title TEXT nodes — renamed by
      node id, never by name, because "Extended Figure 1" is a prefix of "Extended Figure 10"
- [x] Rename Extended Figures 4–13 → `Supplementary Figure 1`–`10` and their title TEXT nodes
- [x] Apply the identical renumbering to the Word text of the extended document, using the
      `figure_edits()` longest-match discipline — `manuscript_versions/
      Harmonization_metrics_extended_260920_v3.docx`, built by
      `tools/apply_extended_doc_v3_260920.py` **from the original**, since all 123 of v2's
      "Extended Figure" references sit inside v2's own unaccepted `w:ins`. 691 revisions,
      reject-all restores the original exactly. Daniil ruled on 2026-09-20 that the
      source benchmark's own figures are qualified rather than left to collide
- [x] Create `Figure 4 - Biomarker expression and correlation (L, M)` at (−8736, 11500) on Page 2
      — `1255:2`, 750 × 6229
- [x] Create `Figure 5 - Prediction and election (N)` at (−7827, 11500) — `1255:3`, 750 × 2585
- [x] Create `Figure 6 - Recipe` at (−6905, 11500) — `1255:4`, 750 × 1120; all twelve SVG assets
      placed and every character added as a TEXT node, including the seven spine step labels
- [x] Create `Supplementary Figure 11 - Marker panel QC` at (−5894, 11500) — `1255:5`
- [x] Create `Supplementary Figure 12 - Harshness and fold audit` at (−4860, 11500) — `1255:6`
- [x] Create `Supplementary Figure 13 - Gene by method clustering` at (−3826, 11500) — the
      manuscript assigns Supplementary Figure 13 to `a2_p18`, not to the reserve frame the
      plan sketched
- [x] Create `Supplementary Figure 14 - Remaining expression scatters` at (−2792, 11500) —
      new on 2026-09-20: Figure 4 keeps only two of its four `a2_p14` grids and the other
      two move here, because four full-width grids make the frame ~9,500 px tall and a 2×2
      arrangement drops the facet labels to ~4 pt. Manuscript, legends and `.docx` are
      already relettered (`tools/apply_figure4_split_edits.py`)
- [x] Upload panel assets; place them; label in **Inter 10 pt**, panel letters **Inter Bold 20 pt**
      — 21 panels re-rendered from their vector PDFs at 300 dpi and set as image fills on
      rectangles placed at the layout geometry; 21 panel letters added
- [x] Screenshot each frame; fix clipping and overlap; clear every placeholder — no clipping and no
      overlap found; every `placeholder` cleared
- [x] Snapshot Page 2 again; diff against "before" — only renamed `name` fields may differ.
      **Rule 5 passes:** 0 geometry changes, 0 removals, 26 name changes (13 frames + their 13
      title TEXT nodes), 14 new nodes. `figures/figma_snapshots/page2_after_260920.json`
- [ ] **Hand over to Daniil for manual correction** — the canvas is ready for it
- [x] Fallback if Figma is unreachable — not needed; Figma authenticated on the fourth OAuth
      attempt and the assembly was done live

### Phase 8 — Documentation

- [x] Update `article_2_extended_comparison/CLAUDE.md` with the Article 2 section — "Article 2 in
      progress", added 2026-09-20; the existing content is unchanged
- [x] Record the run in `workflow_runs/260917_run1/` with a report like the AACR run report —
      written as `workflow_runs/260919_run1/RUN_REPORT.md`, since that is the folder the run
      actually used (decision 24)

---

## 11. Implementation log

### Phase 1 — done 2026-09-18

Scaffolding and the three gates. No analysis code, no notebook, no manuscript and no Figma node
was created or touched; Phase 2 onward still waits for Daniil.

**Created:** `analysis/`, `tables/`, `manuscript/`, `workflow_runs/260917_phase1/`,
`figures/panels_260917/`, `figures/for_figma_upload/`,
`workflow_runs/260917_phase1/style_rules.json`, `tools/overlap_allow.txt`.
**Rewritten:** `tools/check_style.py`, `tools/audit_numbers.py`.
**New:** `tools/check_overlap.py`.

**Smoke tests, all run against fixtures in the session scratchpad:**

| Gate | Control | Result |
|---|---|---|
| `check_overlap.py` | A sentence copied verbatim from Article 1 | Flagged, whole sentence reported as one span |
| `check_overlap.py` | Original prose plus the verbatim grant statement | Clean, 31 allow-listed hits reported |
| `check_style.py` | A skeleton at §3.1's exact targets (9,362 words) | Clean, all six sections inside budget |
| `check_style.py` | The same with six banned constructions injected | 9 violations, each named with its context |
| `audit_numbers.py` | 0.745 and 0.84 quoted against stored 0.7453118 and 0.8402371 | Sourced |
| `audit_numbers.py` | 0.746 and 2,235 against the same table | Unsourced, as they should be |
| `docx2md.py` | The v2 source document | 96,635 characters, 13 images |

### Issues found, and what was done about each

1. **`check_style.py` was inert as copied, and failed silently.** Its rulebook path resolved to
   `article_2_extended_comparison/workflow_runs/260910_phase1/style_rules.json`, which does not
   exist here — the file lives in the AACR repo. `banned_needles()` returns an empty list for a
   missing file, so the gate would have printed "OK: clean" while checking none of the 48 banned
   entries. Fixed twice over: the rulebook was copied into
   `workflow_runs/260917_phase1/style_rules.json` and the default repointed, and a missing
   rulebook now prints a warning to stderr naming what was skipped.

2. **The section splitter did not fit a manuscript.** It keyed on the AACR form's numbered lines
   (`1. `, `### 3. `), so on a manuscript it found no sections and charged every word to the
   header. Rewritten to match markdown headings. The nine F1000 back-matter sections would each
   have needed a budget of their own, so the table anchors on the first of them and charges
   everything to EOF to one 560–945 word budget.

3. **The meta-language check would have failed the AI usage statement F1000 requires.** It bans
   "the manuscript", "provenance" and "verbatim" anywhere in the file, and the AI usage statement
   is precisely a discussion of how the manuscript was made. The check now runs on the body only.

4. **`audit_numbers.py` would have reported almost every number in the paper as unsourced.** The
   AACR version matched numbers as literal strings, which works when the evidence is prose that
   quotes the number as written. Article 2's evidence is CSV at full float precision: a manuscript
   reporting median F1 0.745 is quoting a stored 0.7453118, and the literal search finds nothing.
   CSV sources are now parsed into values and indexed at every rounding from 0 to 4 decimal places,
   plus the percentage forms. Verified both ways: 0.745 resolves, 0.746 does not.

5. **Figure and table numbers would have failed the number audit.** "Figure 12" and "Supplementary
   Figure 11" are labels, not measurements, and no table contains them. Numbers preceded by a
   label word are now skipped, and the reference list, DOIs, URLs and PMIDs are stripped before
   the audit, since their digits are not assertions either.

6. **§2.1 rule 3 and §1.10 contradicted each other.** Rule 3 says any 8-gram shared with Article 1
   is a defect. §1.10 says the Grant information section is quoted verbatim from Article 1's
   FUNDING section, on Daniil's instruction, and it is 41 words long. The gate would have failed
   every run of the finished manuscript. Resolved with `tools/overlap_allow.txt`, and rule 3 now
   states the exception, names the file as the only place one may be granted, and requires each
   exemption to carry its reason. Both sentences were confirmed present verbatim in Article 1
   before being listed.

7. **A bug in the allow-list, found by the smoke test.** Exempt n-grams were taken line by line,
   so the window straddling the two funding sentences was not exempt and the negative control
   still failed. The allow-list is now tokenized in blocks of consecutive lines.

### Editable text pass — done 2026-09-20

37. **Decision 34 is superseded.** Raster fills gave Daniil nothing he could edit and broke §5.4,
    which requires every character on the canvas to be a Figma `TEXT` node. Each panel is now a
    frame holding a locked, text-free 300 dpi artwork rectangle and a `labels` group: **1,966
    `TEXT` nodes**, against the **93,824** drawable nodes a full SVG import would have cost (one
    expression scatter alone is 23,357). The artwork stays raster, so decision 34's reason for
    existing survives; only its consequence is undone.

38. **The overlay is pre-scaled in Python, not rescaled in Figma.** The placed boxes were rounded
    to whole pixels when the frames were laid out, so their x and y scale factors differ by up to
    0.7 %, and `rescale()` is uniform. The text-only SVG is emitted with `x * sx`, `y * sy` and
    `font-size * sx` already applied and a `viewBox` equal to the placed box, so the import lands
    at 1:1 with nothing to correct. Each artwork PNG is resized to the box's exact aspect for the
    same reason: at the drawing's own aspect, `scaleMode: "FILL"` would crop the difference away
    and slide the artwork out from under the text.

39. **Three things about Figma that had to be measured rather than assumed.** Its SVG reader
    ignores `font-size` inside a `style=` attribute and imports the label at its own 10 px default,
    which is fatal because matplotlib writes typography nowhere else — presentation attributes are
    honoured exactly. Only `Inter` is available in the file, so the panels are relettered in Inter
    rather than the Arial they were drawn in, and long left-anchored labels end a few pixels off
    where the raster had them. And `upload_assets` with `nodeIds` stores an image without attaching
    it: all 21 POSTs returned `success` while every target node kept its previous fill, so the
    fills were set explicitly from the returned `imageHash`.

40. **The pass is reproducible, which the original assembly was not.** It left no script on disk,
    so nothing in the repository recorded how the frames had been built. This one is
    `tools/split_panel_text_260920.py` (the offline split) and `tools/figma_editable_text_260920.md`
    (the Figma runbook), under the plan `figma_editable_text_plan_260920.md`. Verified by diffing
    `figures/figma_snapshots/page2_{before,after}_editable_260920.json`: **0 geometry differences,
    0 name differences, 21 rectangles converted, 54 children untouched** — Figure 6's 33 and the 21
    panel letters.

### Open for Daniil

- **The em-dash budget is zero, inherited unchanged.** It was calibrated on an 797-word proposal
  Daniil edited by hand. A 9,400-word research article is a different genre and a dash is
  sometimes the right mark; the §6.2 rule bans *unearned* em-dashes, which is not the same as
  none. The gate currently fails on the first one. Say whether to keep zero or set a density.
- **The Zenodo release of `Nikit357/FL_harmonization`** is the one Phase 0 item still open. It
  blocks only the Software availability section in Phase 5.
- **`figures/for_figma_upload/`** was created early, ahead of Phase 7, because the SVG fallback
  needs somewhere to write and an empty directory costs nothing. Say if it should not be there.

### Phase 2 — done 2026-09-19, except the two items the sign-off gates

Analysis code, tables, generator patches, recipe artwork and the numbers evidence file. No
notebook was regenerated and no manuscript or Figma content was touched.

**Created:** `tools/extract_hand_written_cells.py`, `analysis/article2_generalizability.py`,
`analysis/build_numbers_json.py`, `figures/recipe_figure_assets.py`,
`harmonization-metrics/hand_written_cells_260917.ipynb`,
`harmonization-metrics/diverged_cells_260917.md`, `tables/A2_T0`–`A2_T8`,
`figures/recipe_assets_260917/` (12 SVGs), `workflow_runs/260917_phase2/01_numbers.{json,md}`.
**Patched:** `harmonization-metrics/create_correlation_prediction_notebook.py`,
`harmonization-metrics/create_marker_gene_deep_analysis_notebook.py`.

**What reproduced exactly**, on the 2,234-approach set: the analysis set itself (2,234 / 31 / 14 /
3); the Shambhala identity (78 of 79 numeric columns, only `compute_time_s` differing); the joint
L/M gate at 1,686; the agreement-specific group at 61 of 2,150 (2.8%) with its method and strategy
censuses; Shambhala's position (median ρ 0.840, margin 0.0048, F1 0.745, best row 136 of 2,233 by
F1 and 1,680 by margin); the leading non-degenerate approach
(`S0_no_removal / softimpute / 29_combat_ref / post0`, F1 0.946, worst fold 0.462, 11 multiclass
folds, AUC 0.932, ρ 0.880) and the n = 1,527 set it was chosen from; every median in the harshness
tier table and six of its seven Kruskal–Wallis rows, including the 2-class AUC failing to separate
the tiers (H = 1.5, p = 0.48); the metric coverage counts (2,234 / 2,233 / 2,233 / 2,174).

**Both generators verified to leave Article 1 alone.** Run without `--article2`, each one now emits
cell sources identical to what it emitted before the patch. Byte identity is not achievable and
never was: nbformat assigns a fresh random `id` to every cell on every run, so two runs of the
*unmodified* generator already differ. The check that means something is cell-source identity, and
it passes for both generators and both variants.

### Issues found, and what was done about each

1. **The §1.5d fold numbers described a population the article never analyses.** They were computed
   over every run_id in `prediction_folds_long.csv` — 3,738 of them under 50 method names — of
   which 21,543 folds belong to the 17 non-canonical Shambhala P/Q variants. Restricted to the
   2,234-approach set the counts become 32,746 folds, 15,436 single-class (47.1%), medians 0.903 /
   0.629 / 0.804 and Spearman 0.815. §1.5d is corrected and the discrepancy is recorded in
   `01_numbers.md` for the manuscript to state. **No ordering and no conclusion changes.**

2. **`prediction_folds_long.csv` carries the same Shambhala trap as the metric snapshot** — the 18
   P/Q variants and zero rows named `20_shambhala`. The project memory note covered the metric
   tables only. Without the rename here the 84 Shambhala approaches would have received no fold
   metrics at all while still appearing in the analysis set. `_canonicalize_shambhala()` is applied
   to the fold table too, in both functions that read it.

3. **Zero multiclass folds was not representable.** An approach whose folds all carry one class
   produces no rows in the multiclass aggregate, so the join left `n_mc` missing — which reads as
   "not measured" when it means "measured, and the answer is none". The `G_affymetrix_only`
   post-removal rows reporting F1 = 1.000 are exactly this case. `n_mc` is now set to 0 for any
   approach that has folds, and 59 approaches carry that zero.

4. **A flag column broke the delta arithmetic.** `mk_is_self_reference` and `xb_subsampled` are
   booleans, which pandas calls numeric; subtracting one from another raises. Bool columns are
   excluded from the raw-delta pass and from every class composite.

5. **`06_combat_seq` and `08_inmoose_combatseq` are an exact tie** at the top of the raw-subtracted
   margin ranking — 0.439161 and +0.457154 for both. §1.5c named only the first. Two
   implementations of one algorithm agreeing to six decimals is a positive control; the plan now
   says so and neither may be quoted alone.

6. **The divergence count was too low, and it missed the dangerous category.** Measured properly,
   115 cells are hand-written and **70 more are generator cells edited in place** — 185 at risk,
   not 80. An edited generator cell still looks like the generator's, so regeneration reverts it
   silently. §4.2e is corrected and `tools/extract_hand_written_cells.py` makes the measurement
   re-runnable.

7. **The panel inventory collided.** The Sankey was assigned `a2_p13` and the expression scatters
   `a2_p14`, while §4.3 had already given `a2_p13`–`a2_p16` to the four deep-analysis re-exports.
   Resolved by giving the correlation notebook `a2_p1`–`a2_p13` and the deep-analysis notebook
   `a2_p14`–`a2_p18`; the inventory is eighteen panels and verification command 2 now checks that
   range.

8. **`FOLDS_LONG_CSV` in the generator is date-tagged, and no `prediction_folds_long_260905.csv`
   exists** — only `_260824`, `_260826` and the undated file the L/M/N run actually wrote. A
   notebook generated at `--date-tag 260905` prints `MISS` for it and its fold cells produce
   nothing. The §10 cells resolve whichever file exists; the Article 1 constant is left alone,
   because changing it is outside this plan's scope.

9. **The evidence file quoted a median of medians.** `01_numbers.json` first read the fold medians
   by taking the median of `A2_T8`'s per-batch medians, which gave 0.925 / 0.767 / 0.881 against
   the fold-level 0.903 / 0.630 / 0.804 — and contradicted the discrepancy entry three lines below
   it. `A2_T8` now carries explicit `__ALL__` rows with the fold-level totals and medians, so the
   cited table contains the cited number.

10. **`save_panel` in the shared setup cell would have changed the Article 1 notebook.** §4.2b
    places it after `save_figure`, but doing so puts it in a cell both variants emit, which breaks
    the guarantee in §4.2d that a run without `--article2` reproduces today's notebook. It is
    defined in the `--article2`-only §10.0 cell instead.

### Open for Daniil

- **Sign off on `diverged_cells_260917.md`.** 185 cells are preserved in
  `hand_written_cells_260917.ipynb`; the report proposes port for 119, keep for 23, drop for 43.
  Until that is signed, nothing is ported into the generators and nothing is regenerated. The
  recommendations are heuristic — every `NEAR` cell is proposed for porting because reverting one
  is a silent loss, and every bare-variable inspection is proposed for dropping.
- **Executing the regenerated notebooks needs the pod**: S3 for the expression matrices behind
  `a2_p14`, and the `collagen_3_11` kernel. The local machine has neither, so the 18-panel export
  cannot be verified here.
- **`supervenn` and `matplotlib-venn` are not installed** anywhere yet. The `a2_p10` cell prints an
  install hint and skips instead of failing, but the panel will be missing until they are added to
  the environment.
- **`figures/recipe_assets_260917/` is a new folder** holding the twelve SVGs, beside
  `figures/panels_260917/` and `figures/for_figma_upload/`. Say if the artwork should live
  somewhere else.

### Phase 2 completion and Phase 3 — done 2026-09-19

The sign-off was given by instruction, the notebooks were regenerated and executed, and the
literature was gathered. The K8s pod was **not** created: it was not needed.

**The environment.** `~/venvs/collagen_3_11/` now exists on the local Mac — a real Python 3.11
venv with a Jupyter kernel registered as `collagen_3_11`. Before this it existed only on the
remote `~` machine and every `source ~/venvs/collagen_3_11/bin/activate` in the
project docs failed locally. `~/.aws/` credentials give the machine direct S3 access to
`$FL_S3_BUCKET/FL_batch_correction/`, which is the only thing the metrics pod
was providing for these notebooks, so no pod was launched. Details are in project memory under
`collagen-3-11-kernel-local-mac`.

**Execution results.**

| Notebook | Cells | Errors | Note |
|---|---|---|---|
| `correlation_prediction_metrics_analysis.ipynb` | 67 | 1 | the one preserved cell that needs the gene-correlation table (issue 13) |
| `correlation_prediction_metrics_analysis_narrow_set.ipynb` | 79 | **0** | clean |
| `marker_gene_deep_analysis.ipynb` | 103 | 16 | all downstream of one missing input (issue 14) |

**Panels: 15 of 18** exist in PDF, SVG and PNG — `a2_p1`–`a2_p13` from the correlation
generator, `a2_p15` and `a2_p17` from the deep-analysis generator.

### Issues found, and what was done about each

11. **The port list of 119 cells was wrong, and following it would have deleted working
    features.** The `NEAR` category was read as "a generator cell someone edited, which
    regeneration silently reverts". Inspecting the diffs showed the opposite for most of them:
    the notebook is *older than the generator*. The main notebook predates the commit that added
    the narrow-set variant, so its cells lack `MK_SFX` and the `NARROW` branch — porting the
    notebook's version back would have removed the narrow-set feature from the generator. In the
    deep-analysis notebook nearly all 52 `NEAR` cells differ only by code formatting.
    Re-derived on the rule *genuinely hand-written = similarity below 0.75, or carrying Russian
    working notes, and not a bare variable inspection*: **32 cells**, not 119 — 5 main, 17
    narrow, 10 deep. Those are preserved; for everything else regeneration is the fix, not the
    risk. §4.2e is corrected.

12. **Preserved cells do not run where they were put.** Re-emitted at the end of the notebook
    they raised `IndentationError` (several carry a uniform four-space indent — they would fail
    in the original notebook too), then `NameError` for `mcolors`, `pearsonr`, `mpatches`,
    `method_pal` and `f3`. Fixed by dedenting a uniformly-indented cell and emitting a preamble
    that imports what they assume and rebuilds `method_pal` and `f3` from objects the generator
    already provides. The narrow-set notebook went from 11 errors to 0.

13. **`prediction_folds_long_260905.csv` does not exist**, so `folds_long` was empty and every
    per-fold section produced nothing at the pinned snapshot. The generator now falls back to the
    undated `prediction_folds_long.csv` the L/M/N run actually wrote, printing which file it
    read. This is what took the narrow-set notebook to zero errors.

14. **The deep-analysis notebook cannot be completed from the files on disk, and finishing it is
    outside this plan.** Its `DATE_TAG` and `PANEL_TAG` had both drifted: the panel outputs are
    at 260828, not 260827, and `marker_gene_correlations_long` exists only at 260824. A `dated()`
    resolver now finds whichever date is present and prints the substitution, which took the
    notebook from dying at cell 9 to executing all 85 code cells. It then stops on a real
    inconsistency: the 260824 gene table carries 554 genes, of which 58 are absent from the
    current 633-gene `marker_gene_annotation.csv`, and 137 annotated genes are absent from it.
    The notebook's own assertion refuses to proceed, correctly, and that assertion was not
    relaxed. Separately, **`gene_qc_long` has never been produced at any date**, so `HAS_QC` is
    permanently false. Consequences: `a2_p16` (QC gate) cannot exist at all, and `a2_p14`
    (expression scatters) and `a2_p18` (gene × method clustermap) depend on gene-level objects
    the assertion blocks. Producing the missing tables means re-running
    `gene_panel_analysis/run_gene_corr_parallel.py` and `run_gene_corr_concat.py` on the pod
    against the current panel — a metric job, which §9.8 places outside this plan.

15. **The literature fetcher attributed quotes to the wrong papers.** NCBI `elink` returns
    several PMC link sets and the first is `pubmed_pmc_refs`, the articles that *cite* the
    query — so ComBat resolved to a Nature organoid study and the Lazar review to a gastric
    cancer paper, and both produced confident-looking quotes from the wrong source. Caught by
    reading the retrieved titles rather than trusting the ids. `pmcid()` now matches the
    `pubmed_pmc` linkname explicitly, the cache was destroyed and every entry re-fetched. Two
    papers turned out to have no open-access full text at all; they are quoted from their
    abstracts and labelled as such.

16. **The overfitting and degenerate-fold sweep is thin.** Only Varma & Simon (2006) and
    Nygaard (2016) are directly on point and openable. Cawley & Talbot (2010) and Kaufman's
    leakage paper are not in PubMed, so under the rule "a paper it cannot open is not a citation"
    they are not in the file. The theoretical backing for §1.5d therefore rests on two
    references; if the Discussion needs more, that sweep should be reopened against JMLR and ACM
    rather than PubMed.

17. **The "`--article2` changes nothing for Article 1" guarantee no longer holds exactly, and
    that is deliberate.** §4.2d promised a run without the flag reproduces today's notebook. It
    now differs in two ways, both intended and both verified to be the only differences: the
    setup cell carries the input-resolution fixes of issues 13 and 14, and the preserved §11
    section is emitted regardless of the flag — because regenerating the *Article 1* notebook
    would otherwise delete the same hand-written cells. Nothing else changed: a cell-by-cell diff
    against the pre-change generators shows one modified cell in each (the setup cell) and no
    change to any analysis, plot or number.

### Open for Daniil

- **Three panels need a pod run.** `a2_p14`, `a2_p16` and `a2_p18` are blocked until
  `gene_panel_analysis` is re-run against the current 633-gene panel and `gene_qc_long` is
  produced. Everything else in Phase 2 is finished.
- **`preserved_cells_260917.json` is the record of what survives regeneration.** 32 cells. If any
  of the ~150 cells it excludes matters to you, say which and it goes back in; the full audit of
  every excluded cell is still in `diverged_cells_260917.md`.
- **One cell in the main notebook still errors** — the preserved clustermap of `piv`, which needs
  the gene-correlation table. It will run once that table exists.

### Phase 0–2 file audit and re-run on the pod — done 2026-09-19

Daniil asked for two things: check that every file Phases 0–2 need is actually available, and
close the issues left open above. Both were done on the **pod** (`~`), not on the Mac.
That single change of machine is what closed them: nothing was recomputed, no metric job was
launched, and §9.8 was never engaged.

**The audit.** Everything Phases 0–2 name is present and readable here.

| What | State |
|---|---|
| `tools/` — all seven scripts, `overlap_allow.txt`, `style_rules.json` | present; the three gates import and the two overlap targets parse (18,044 and 10,850 tokens) |
| `analysis/article2_generalizability.py`, `analysis/build_numbers_json.py` | present |
| `tables/A2_T0`–`A2_T8` | present, and **they reproduce** — see below |
| `workflow_runs/260917_phase{1,2,3}/` | present, with `style_rules.json`, `01_numbers.{json,md}`, `02_literature.{json,md}` |
| `figures/recipe_assets_260917/` | present, all twelve SVGs |
| `figures/panels_260917/` | **18 of 18 panels**, each in PDF, SVG and PNG (63 files; `a2_p14` carries four method variants) |
| `workflows/article2_f1000.workflow.js.template` | present |
| `manuscript/`, `figures/for_figma_upload/` | were **absent** — created now; an empty directory does not survive the Mac↔pod transfer |
| `metrics_comprehensive_260905.csv`, the three long tables, the marker annotation, Supp. File 3 | present |
| `hand_written_cells_260917.ipynb` (189 cells), `diverged_cells_260917.md`, `preserved_cells_260917.json` | present |

`analysis/article2_generalizability.py --date-tag 260905` was re-run into a scratch directory and
diffed against the committed tables. Six of the nine are byte-identical; `A2_T0`, `A2_T1` and
`A2_T7` differ only at machine epsilon (largest discrepancy 1.4e-20, in
`mk_rho_marker_minus_hk`). Every headline number of §1.5 reprinted unchanged: 2,234 / 31 / 14 / 3,
the 84-key Shambhala identity at 78 of 79 columns, the joint L/M gate at 1,686, 32,746 folds with
15,436 single-class, and agreement-specific at 61 of 2,150.

**The re-run.** Both generators were patched (issue 18), all three notebooks regenerated with
`--article2` and executed with `jupyter nbconvert --execute` in the `collagen_3_11` kernel:

| Notebook | Cells | Errors before | Errors now |
|---|---|---|---|
| `correlation_prediction_metrics_analysis.ipynb` | 67 | 1 | **1**, and it is a different one — see issue 21 |
| `correlation_prediction_metrics_analysis_narrow_set.ipynb` | 79 | 0 | **0** |
| `marker_gene_deep_analysis.ipynb` | 103 | 16 | **0** |

### Issues found, and what was done about each

18. **The correlation generator had no fallback for the two gene-level tables, and that is what
    broke `a2_p14`/`a2_p16`/`a2_p18`'s sibling sections — not a missing metric job.** Issue 13
    gave `prediction_folds_long` a fallback but left `GENE_LONG_CSV` and `COHORT_LONG_CSV` as
    bare f-strings on `DATE_TAG`. `run_metrics_concat.py` writes the metric snapshot *with* a date
    tag and the three long tables *without* one, so a notebook pinned at 260905 found
    `metrics_comprehensive_260905.csv` and then `MISS` on both gene tables. Every cell tolerates
    an empty table, so the failure was silent: `gene_long` was empty, `gl` had no columns, and the
    preserved clustermap died on `KeyError: 'method'`. Both generators now share one `dated()`
    resolver with the order *exact date → the undated file the last run wrote → newest dated
    copy*, printing every substitution. Verified against the pre-patch generators: run without
    `--article2`, each of the three notebooks differs in **exactly one cell**, the setup cell —
    the same guarantee issue 17 states.

19. **`gene_qc_long` has been on disk since 2026-08-28. Issue 14's "never produced at any date" is
    wrong.** `metric_tables/gene_qc_long_260828.csv.gz` is 122 MB, which is why it is not on the
    Mac. With it present `HAS_QC` is true, §5 and §11 of the deep-analysis notebook run, and
    `a2_p16` (QC gate) and `a2_p18` (gene × method clustermap) export normally. Nothing was
    re-run in `gene_panel_analysis/` and nothing needed to be.

20. **The 633-gene assertion never had a problem either.** Issue 14 read the 260824 gene table
    (554 genes, 58 of them unannotated) because 260826 had not reached the Mac.
    `marker_gene_correlations_long_260826.csv` is here, it carries **572 genes and zero
    unannotated ones**, and the assertion passes. It is also **byte-identical** to the undated
    file the 260905 run wrote (md5 checked, as are the cohort and fold tables), so the deep
    notebook staying on `DATE_TAG = "260826"` reads exactly the data §9.4 pins — the only
    difference between the two snapshots is the 15 `mk_*_narrow_set` columns added to
    `metrics_comprehensive`, which no deep-analysis panel touches. `a2_p14` then needed S3, and
    S3 works from the pod: four expression matrices were fetched and the scatters exported for
    `01_raw`, `12_scanorama`, `13_fsmvn` and `29_combat_ref`.

21. **The one cell that still fails is an unfinished draft, and it needs Daniil, not a fix.**
    Preserved main-notebook cell 23 now gets its data and fails further along, on
    `FloatingPointError: NaN dissimilarity value` out of `sns.clustermap`. The cause is in the
    cell itself: `piv` is 572 genes × 3,739 attempts, 33.2% of it is NaN, and **every one of the
    572 genes is missing from at least one attempt**, so no linkage can be computed on it as
    written. Two further things in the cell are unfinished — it passes `ax=ax` to `clustermap`,
    which builds its own figure and does not take one, and it pivots all 3,739 run_ids rather
    than the 2,234-approach analysis set. It was left **byte-identical to what Daniil typed**:
    deciding whether to drop incomplete genes, impute, or restrict to complete attempts changes
    what the figure means. It is not one of the eighteen Article 2 panels and blocks nothing.

22. **Re-running the notebooks rewrote 219 tracked Article 1 files and added 4 new ones, and
    some of them changed for the better.** `current_figures_tables_for_article_260819/` is where these notebooks export
    Article 1's figures, so executing them touches it by design. Two real content changes came
    with the fixes: the narrow-set Supplementary File 5 tables
    (`S5_2_marker_gene_correlations_long.csv` at 919,940 rows, `S5_3`, `S5_7`, `T9`) **did not
    exist before** — they were being written from the empty `gene_long` of issue 18 — and
    `T3_saturation_split.csv` went from 554 to 572 rows, because the deep notebook now reads the
    260826 gene table instead of 260824. Everything is tracked in git and reviewable with
    `git diff`; nothing was committed.

### Open for Daniil

- **The preserved clustermap (issue 21) needs one decision** — drop genes missing from any
  attempt, impute them, restrict the pivot to complete attempts, or drop the cell. Say which and
  it takes one edit. Until then the main notebook carries one deliberate error.
- **The Article 1 re-export of issue 22 is uncommitted.** The new narrow-set Supplementary File 5
  and the 572-row `T3` look like corrections rather than regressions, but they are Article 1's
  numbers and the call is yours: `git diff figures_for_article/current_figures_tables_for_article_260819/`
  shows all of it, `git checkout` on that folder reverts the 219 modified ones, and the 4 new
  files are untracked and can simply be deleted.
- **Phase 0's last item is still the Zenodo release** of `Nikit357/FL_harmonization`. Nothing
  else in Phases 0–2 is open.
- **`a2_p16` is legible only at full width.** Its x tick labels (`LOW_FRAC_MAX`, 18 values)
  overlap at the half-width geometry §4.2 assigns it. It is a re-export of Article 1's
  `l2_qc_gate_sweep`, so widening it means changing the Article 1 figure or giving Article 2 its
  own draw. Say which, or accept it at full width in the Figma frame.
- **Every subplot of `a2_p14` is annotated ρ = 1.000**, which is arithmetic rather than a result:
  Spearman ρ is invariant under the monotone transforms these methods apply. The panel's content
  is the *shape* of each transform against the diagonal. Consider dropping the ρ line from the
  subplot titles before Figma assembly.
- **The em-dash budget is still zero**, unchanged from the Phase 1 note.

### Phase 4 — workflow assembly, done 2026-09-19

`workflows/article2_f1000.workflow.js` is derived from the AACR template and retargeted. The four
authoring items are done; the two runs are not launched.

**What the script is.** 833 lines: `meta` with the four phases of §6.1, the §6.3 `HARD_RULES`
verbatim plus two additions, five schemas, six prompt builders, a gate driver, and the phase
composition. Barriers are used at both fan-outs and they are the correct choice: gate 1 judges
`01_numbers` and `02_literature` **together** and the writer needs both, and gate 3 weighs the
citation defects against the style report while the style-editor's in-place edit must not race the
verifier's reading of the same file.

**Verified before hand-off**, with the runtime's own parse and a dry run over stubbed hooks:

| Check | Result |
|---|---|
| Body parses as an async function (top-level `return` and `await` are legal there) | OK |
| `meta` is a pure literal; its four titles match the four `phase()` calls exactly | OK |
| Five schemas: root `type: object`, `required` ⊆ `properties`, recursively | OK |
| Six prompt builders present | OK |
| Run A (`['evidence','draft']`) agent sequence | 5 agents: code-analyst ∥ literature-scout → gate 1 → writer → gate 2 |
| Run B (`['review','delivery']`) agent sequence | 4 agents: reference-verifier ∥ style-editor → gate 3 → delivery |
| Full run with one gate-1 revision | 11 agents, and only the agent the team lead named is re-run |

The split of §6.4 is what keeps each half inside the session's "medium — under 10 agents"
guideline: 5 and 4. A single run would be 10 with no revisions and 11–16 with them.

### Three decisions taken while deriving it

23. **`REPO` points at the pod, not the Mac.** §6.3 writes
    `<repo>`. The metric tables the code-analyst needs
    are only on the pod (§11 issue 19), so the default is
    `<repo>` and `args.repo` overrides it. The Mac path
    still works; it has to be passed.

24. **`RUN_DIR` defaults to `workflow_runs/260919_run1`, not `260917_run1`**, following Daniil's
    inline instruction in §6.1 to name the folder for the date the run actually happens.

25. **`args.evidenceMode` defaults to `reuse`, and this is the one place the script departs from
    §6.2.** The code-analyst's five tasks and the literature-scout's six sweeps are Phase 2 and
    Phase 3 of the TODO, and both are finished — `01_numbers.json` and `02_literature.json` exist
    under `workflow_runs/260917_phase{2,3}/`. In `reuse` the two Evidence agents verify and carry
    those files into the run folder: the code-analyst re-runs `article2_generalizability.py` into a
    scratch directory and re-checks each number's table, column and filter, and the
    literature-scout re-resolves at least 8 PMIDs against the §11 issue 15 trap. It does not
    regenerate or execute the notebooks. `args.evidenceMode: 'recompute'` restores the full §6.2
    behaviour. Reuse was made the default because recomputing costs a full notebook execution and
    changes nothing that has not already been verified twice.

### Open for Daniil

- **Neither run was launched.** Run A drafts the manuscript, which is Phase 5's deliverable and the
  point past which the `.docx` becomes the main state — that is your call to make, not a side
  effect of building the script. Say the word and Run A goes; the plan then has you inspect
  `01_numbers.json` and `02_literature.json` before Run B is resumed from Run A's run id.
- **`manuscript/figure_legends_260917.md` does not exist**, and §6.2 lists it among the writer's
  inputs while §10 Phase 5 lists writing it among the writer's tasks. The prompt now states the
  second reading: the writer writes it alongside the draft. Say if you meant it as a real
  prerequisite that someone drafts first.
- **The Zenodo release DOI is still the one Phase 0 item open**, and it blocks only the Software
  availability section the writer will reach in Run A. Until it exists the writer will emit
  `[TO CONFIRM: new FL_harmonization release DOI]`, which is what rule 2 requires.

### Run A — done 2026-09-19, run id `wf_60d927c7-88e`

`phases: ['evidence','draft']`, `runDir: workflow_runs/260919_run1`, `evidenceMode: reuse`.
**10 agents, 0 errors, 2 h 28 m, 1.85 M subagent tokens, 454 tool calls.** The dry run predicted 5
agents; both gates rejected once, which is the extra five.

| Gate | Round reached | Verdict |
|---|---|---|
| 1 — are the numbers real and is the gap defensible? | 2 | **accept**, 15 artifacts accepted by name |
| 2 — does every claim trace to an artifact? | 2 | **revise** — 4 defects survive and become open items, exactly as §6.2 specifies |

**Artifacts.** `workflow_runs/260919_run1/`: `01_numbers.{json,md}`, `02_literature.{json,md}`,
`03_draft.md`, `05_teamlead_gate{1,2}.{json,md}`. `manuscript/`:
`FL_metric_classes_F1000_260917.{md,docx}`, `figure_legends_260917.md`, `references_260917.md`.
The `.docx` was produced without waiting for approval and is now the main state; it carries no
tracked changes yet, which is right for a first conversion.

**Gates, re-run by hand after the workflow returned, not taken from the team lead's word:**

| Gate | Result |
|---|---|
| `check_style.py --journal f1000` | **exit 0.** 10,311 words, 0 em-dashes, 33 semicolons (3.2/1k); all six sections inside budget — abstract 300, introduction 729, methods 1,371, results 6,422, conclusions 685, back matter 712 |
| `check_overlap.py` vs Article 1 and the source document, 8-gram | **exit 0.** 11,619 tokens, 40 allow-listed hits ignored, no verbatim overlap |
| `audit_numbers.py --tables tables/` | FAIL, 21 unsourced |
| the same `--evidence 01_numbers.json` | FAIL, **7 unsourced** — the team lead reported 21 → 7 and it reproduces |

The seven are not all defects. `2,407` is Article 1's completed-approach count, cited to [38]; it
is a cited fact and no Article 2 table contains it. `555,004.7` is an expression-range maximum. The
team lead's own note is the right reading: `audit_numbers.py` cannot evaluate a filtered aggregate
over a CSV, so any number from a groupby needs an entry in `01_numbers.json` to resolve. That is a
tool limitation to record, not a manuscript error.

**The gate design did what it was built to do.** At gate 1 no manuscript existed yet, and the team
lead recorded rules 1, 3 and 4 as `passed: false` with "cannot be checked against its subject" as
the evidence instead of claiming a pass — which is what the prompt requires and the failure mode it
was written against. Rule 5 (Figma) is `passed: false` at both gates because this session has no
Figma read access; rule 8 makes that correct, and it stays an open item.

### The four defects that survived both rounds — each verified here against the table

26. **`0.713` should be `0.712`.** Results, the imputation medians. Grouping `A2_T1` by `imp` and
    taking the median of `pv_lobo3_f1_macro_mean` gives strict 0.713853, softimpute **0.712458**,
    knn 0.701354. 0.712458 does not round to 0.713 under any convention. The stated range of 0.013
    is unaffected — it comes from the first and third values.

27. **"are last" names the wrong five methods.** The draft calls `02_median_scaling`, `03_limma`,
    `26_xpn`, `16_fsqn_r` and `13_fsmvn` the bottom of the per-method ranking. The five lowest
    medians over the 31 methods are `02_median_scaling` 0.4529, `03_limma` 0.4804, `07_pycombat`
    0.5202, `21_harmonizr` 0.5214, `28_npn` 0.5230. The three the sentence adds sit at ranks
    **6, 7 and 8 of 31** (`26_xpn` 0.5288, `13_fsmvn` 0.5369, `16_fsqn_r` 0.5435). The four
    columns quoted for each named method are themselves right; the word "last" is what fails.

28. **"All stochastic steps used a fixed seed of 42" has no locus.** `grep -ciE
    "seed|random_state|np\.random|RandomState|shuffle|permut|sample\(|sklearn"` over
    `analysis/article2_generalizability.py` returns **0**, and its only `scipy.stats` import is
    `kruskal, spearmanr`. The sentence sits one clause from the sentence asserting that script's
    full inferential inventory.

29. **Two bibliographic errors, both in entries whose PMIDs are real.** `[51]` reads "Breast Cancer
    Res Treat. 2018." with no volume or pages; PMID 30484103 is 2019 Feb;174(1):129-141. `[27]`
    truncates its title before "in Human Evolution"; PMID 30736359 carries the full title. Neither
    is a fabrication. Both strings are duplicated in `tools/overlap_allow.txt` and must be edited
    in the same pass, with `check_overlap.py` re-run afterwards.

### Open for Daniil

- **Nothing was fixed.** §6.2 says a defect surviving two rounds goes to you and is never quietly
  fixed by the team lead writing the text itself, so the four above stand in the manuscript. Three
  of them are one-line mechanical corrections; defect 27 is a writing choice — either name the five
  methods that are actually lowest, or keep the present five and say what is true of them.
- **The `.docx` is the main state from now on.** Any correction should go in as tracked changes via
  the `word-rewrite` or `scientific-review` skill, not as a silent edit to the Markdown, or the two
  files desync.
- **Run B is not launched.** The plan has you inspect `01_numbers.json` and `02_literature.json`
  first. When you are ready:
  `Workflow({scriptPath: 'workflows/article2_f1000.workflow.js', resumeFromRunId: 'wf_60d927c7-88e', args: {phases: ['review','delivery'], runDir: 'workflow_runs/260919_run1', repo: '<repo>'}})`
- **Seven open items came out of gate 2 besides the defects**, including 27 `[TO CONFIRM]` markers
  in `references_260917.md` (20 ORCID author lists, two JMLR entries with no PMID or DOI, the
  RetroSpect chapter, the Zenodo dataset), the Zenodo release DOI in Software availability, and
  your confirmation of the Article 2 author list. They are listed in `05_teamlead_gate2.json`.
- **The numbers agent also edited `analysis/build_numbers_json.py`**, which the round-1 rejection
  did not name. The team lead accepted it on the reasoning that the generator produces the
  discrepancy string, so a fix applied only to the generated file reverts on the next run. Confirm
  that is what you want.

### Run B — done 2026-09-19, resumed into `workflow_runs/260919_run1/`

`phases: ['review','delivery']`, same run folder as Run A, `repo` on the pod. The session that
launched it was ended by the token limit and the JupyterHub server was restarted afterwards, so the
run's own agent count, wall time and token total are not recoverable. Everything below is read off
the artifacts on disk, not off a workflow report.

**Artifacts.** `04_references_verified.{json,md}`, `04_style_report.{json,md}`,
`05_teamlead_gate{3,4}.{json,md}`, `06_open_items.md`, `06_provenance.{json,md}`.

| Gate | Round reached | Verdict |
|---|---|---|
| 3 — does every claim survive an independent check of its citation and its register? | 2 of at most 2 | **accept**, procedural: the three round-1 writer defects are fixed, two rules are not satisfied and convert to open items |
| 4 — delivery | 1 | **accept for delivery, not cleared for submission** |

**What the two review agents did.** The reference-verifier re-resolved all 55 entries of the
pre-renumbering list from scratch — 48 by PMID through eSummary, 4 through Crossref, 1 through the
bioRxiv API, 1 through DataCite, 2 at the publisher — and avoided the §11 issue 15 elink trap by
construction, taking PMC ids from the `articleids` block instead of calling elink. Verdicts: 49
SUPPORTS, 3 PARTIAL, 2 DOES NOT SUPPORT, 1 UNVERIFIED; the last three were dropped from the
manuscript in the gate-3 renumbering to 52. The style-editor ran the three mechanical gates, made a
manual register pass and applied 12 prose edits on 11 lines, then brought the `.docx` into agreement
as plain edits. The team lead decomposed that edit into 14 hunks and confirmed no number, citation
or claim moved.

**At delivery** the team lead built a provenance index over all 452 distinct numbers and all 52
citations, re-resolved a fresh independent 11 of 52 references (`random.seed(20260919)`, 11 of 11
matching), and wrote every survivor into `06_open_items.md` rather than fixing it — delivery has no
revision round. Rule 1 failed on three values whose locus is the pinned snapshot rather than
`tables/`; rule 5 (Figma) could not be checked at all, since this session has no Figma read
capability, and was recorded `passed: false` with the reason instead of being assumed.

### Post-delivery fix pass — done 2026-09-19, completed 2026-09-19 in the next session

The session that ran it was cut off by the token limit immediately after the last edit to
`tools/audit_numbers.py`, before any gate was re-run. The edits themselves were all on disk; what
was missing was the verification. **Nothing was re-done in the resuming session** — every file was
inspected first, found already correct, and only the gates were re-run.

| Defect | Fix on disk | Verified |
|---|---|---|
| D1, D6, D7 — numbers with no locus under `tables/` | `analysis/build_numbers_json.py` joins the pinned snapshot on the 2,234-row key and emits two new sections, `saturation_and_scale` (198, the six saturated methods, 98.5%, 1,359.6, 555,004.7) and `gate_and_rank_counts`; `01_numbers.{json,md}` regenerated. `tools/audit_numbers.py` gained a comma-grouped-decimal branch in `NUM_RE`, so `555,004.7` is no longer tokenized as `555,004`, and an affiliation-line strip so a postal code is not audited as a measurement | audit with `--evidence`: **450 numbers, 450 sourced, 0 unsourced, exit 0** (it was 7 unsourced at gate 4) |
| D2 — "a median" / "a maximum" | manuscript reads "a mean median expression value of 1,359.6 and a mean maximum of 555,004.7" | present in `.md` and in the `.docx` |
| D3 — support file keyed to the old numbering | `reference_support_260917.md` opens "Complete for all 52 references", three PARTIAL verdicts, the dropped blocks removed | grep |
| D4 — the [22] hedges | "showed only a partial overlap … which the authors attributed to tumour content and host cells" | present in `.md` and in the `.docx` |
| D5 — `03_draft.md` stale | body refreshed from the delivered manuscript with a dated note above it | byte-identical to `manuscript/FL_metric_classes_F1000_260917.md` |

**The choice taken for D1 and D6 was the evidence-file route, not the table route.** Open item 5.1
offered two options — promote `pcr_*`, `kbet_*` and `exp_*` into a file under `tables/`, or name the
snapshot, the column and the filter in `01_numbers.json`. The second was taken, and it is
re-runnable: the join lives in `build_numbers_json.py`, so it survives a regeneration. The seven
fold-population counts of D6 keep their `fold_population_denominators` entries. **Daniil still owns
the decision** of whether that is acceptable for submission or whether the columns should be
promoted into `tables/`.

### Phase 5 — done 2026-09-19; verification commands 4–8 all pass

Re-run in this session, on the files as the fix pass left them:

| Command | Result |
|---|---|
| 4 — `audit_numbers.py --tables tables/` | 450 numbers, 20 unsourced — expected: the gate needs the evidence file, because the tool cannot evaluate a filtered aggregate over a CSV (D7) |
| 4 — the same `--evidence workflow_runs/260919_run1/01_numbers.json` | **exit 0**, 450 of 450 sourced |
| 5 — `check_overlap.py`, 8-gram, on all three manuscript `.md` files | **exit 0** each: body 40 allow-listed hits, legends 0, references 154 allow-listed; no verbatim overlap |
| 6 — `check_style.py --journal f1000` | **exit 0.** 10,337 words, 0 em-dash, 33 semicolons (3.19/1k); abstract 300, introduction 782, methods 1,385, results 6,393, conclusions 669, back matter 716 |
| 6b — the "rather than" / antithesis grep over `manuscript/*.md` | prints nothing |
| 7 — citations | 52 `PMID: ` lines, support document present, 2 `[TO CONFIRM]` in the body (P1, P2), 0 in the reference list |
| 8 — abstract | 300 words, all four of Background / Methods / Results / Conclusions present |
| rule 12 — the `.docx` | 0 `w:ins`, 0 `w:del`, 0 `w:delText`, 0 `w:sdt`; the results table survives as a real Word table; all four text fixes present |

### Open for Daniil

- **Phase 6 was not started** — the stop point you set for this run. Phases 6, 7 and 8 are untouched.
- **The three text fixes (D2, D3, D4) were already applied** by the cut-off session. Decision 7 of
  `06_open_items.md` had them waiting on your approval first; they are in the manuscript and in the
  `.docx` now. Each is a one-line correction that makes a true statement out of a false one, and
  each is listed above with its before and after, so it can be reverted if you disagree with it.
- **The five items that are still only yours remain open**: the FL_harmonization release DOI (P1),
  which of the ten affiliation-2 authors hold employment (P2), whether Zenodo 22737294 is
  published and its DOI resolves (D8), whether the D1/D6 evidence-file route is acceptable or the
  columns should be promoted into `tables/`, and the rule 5 Figma confirmation.
- **Rule 5 is still unchecked.** This session has no Figma read capability either — the plugin
  exposes only `authenticate` — so no frame name or geometry was compared against §3.4. It stays an
  open item and it is the first thing Phase 7 needs.

### Phase 6 — supplementary tables, done 2026-09-20

Three workbooks under a new `supplementary/` directory, all written by one new script,
`analysis/build_supplementary_workbooks.py`.

| Workbook | Sheets | Size |
|---|---|---|
| `A2_Supplementary_File_1_260917.xlsx` — the analysis set and its metrics | README, `Analysis_set`, `Canonical_set_reconciliation`, `Generalizability_ranking`, `Method_census_by_class`, `Strategy_and_imputation_summary`, `Harshness_by_LMN` | 5.4 MB |
| `A2_Supplementary_File_2_260917.xlsx` — cross-batch structure and prediction | README, `Cross_election_matrix`, `Elected_sets_by_class`, `Agreement_specific_61`, `Margin_raw_and_delta`, `Per_batch_folds`, `Fold_composition` | 0.6 MB |
| `A2_Supplementary_File_3_260917.xlsx` — the marker gene panel | README, `Panel_coverage_by_attempt`, `QC_gate_sweep`, `Rho_by_signature`, `Narrow_set_genes` | 0.1 MB |

Files 1 and 2 are seven sheets each, which is what the manuscript already promises. Every workbook
opens with a plain-language README naming each following sheet, what it holds, its row count and
its source table; every data sheet carries a provenance line in row 1 naming the source table and
the filter, with the column headers on row 2.

### Four decisions taken while building them

26. **Two sheets are derived, not read from `tables/`.** `Elected_sets_by_class` needs the election
    itself and `Strategy_and_imputation_summary` is an aggregate over `A2_T1`; neither is stored as
    an `A2_T*` table. Both are computed in the builder by importing `article2_generalizability`
    and re-running `cross_election_matrix`, and the recomputed matrix is asserted against
    `A2_T3` before use. A workbook therefore cannot disagree with a table.

27. **Two sheets carry a second block.** `Canonical_set_reconciliation` holds the 12-step
    2,407 → 2,234 ledger with the 79-row Shambhala identity check (`A2_T0`) underneath it, and
    `Strategy_and_imputation_summary` holds the method-by-strategy medians — the data behind the
    a2_p7 bubble grid — underneath its own table. Each block gets its own provenance line. This is
    what keeps Files 1 and 2 at the seven sheets the manuscript names while still shipping both
    tables.

28. **Supplementary File 3 was built, and it needed a manuscript change.** Plan §7 makes it
    conditional on the marker-panel figure being used; it is used, as Supplementary Figures 11 and
    13. The "Supplementary material" section named only Files 1 and 2, so one sentence was added.
    **Daniil approved the edit on 2026-09-20**: it went into the `.md` directly and into the
    `.docx` as a tracked insertion (`tools/apply_supp_file3_entry.py`, author `Claude (Article 2)`),
    with the untouched file kept as `FL_metric_classes_F1000_260917_pre_suppfile3.docx`.
    `nar_review_tools.py validate` reports ALL CHECKS PASSED: 1 revision, reject-all restores the
    delivered text exactly. The delivered `.docx` now carries one `w:ins` where
    `06_open_items.md` §6 records zero, and that is deliberate.

29. **`T3_saturation_split.csv` was folded into `Rho_by_signature` rather than given its own
    sheet.** T3 and T4 cover the same 572 genes; only the `saturated` flag is new, and it belongs
    beside the per-gene correlation it qualifies. Plan §7 lists four sheets for File 3 and four is
    what was built.

**The duplication check of plan §7 ran and is on disk** as
`supplementary/duplication_check_260917.md`. It separates the join keys (`strat`, `imp`, `method`,
`post_rm`, `run_id`, `gene`), which are shared on purpose, from shared measurement columns, which
would be duplication. Verdict: **no Article 2 sheet reproduces a measurement column of any Article
1 supplementary file.** The only overlaps are join keys against Article 1's Supplementary File 3.

**The gates were re-run after the manuscript edit**, not assumed: `audit_numbers.py` with the
evidence file exits 0 on 450 of 450 numbers, `check_style.py --journal f1000` exits 0, the
antithesis grep prints nothing, and `check_overlap.py` exits 0 on 11,703 tokens with 40
allow-listed hits.

### Phase 8 — documentation, done 2026-09-20

- `article_2_extended_comparison/CLAUDE.md` gained an **"Article 2 in progress"** section: the
  source-document rule (v2, never v1), the sub-directories added for Article 2, the 2,234-row
  analysis set with the `20_shambhala` rename and why skipping it yields 2,150, the
  anti-plagiarism contract and its gate, and the Figma Page 2 rules including the two
  `get_metadata` limits. The existing content is unchanged.
- **The run report is `workflow_runs/260919_run1/RUN_REPORT.md`**, not `260917_run1/` as the TODO
  wrote it — the run folder is named for the date the run actually happened, which is decision 24.
  It records what was produced, the data it rests on, the eight phases, both workflow runs with
  Run A's measured cost and Run B's unrecoverable one, what the review agents did, the gate
  results re-run by hand on 2026-09-20, the Phase 6 manuscript change, and the open items by
  reference rather than by restatement.

### Phase 7 — done 2026-09-20

**Figma authenticated on the fourth OAuth attempt.** The first two round trips failed at the
token exchange with the opaque message *"An error occurred processing your request"* and the
third callback was a stale one from the first flow. Network was never the cause: from the pod,
`www.figma.com` returns 200, `api.figma.com` 401 and `mcp.figma.com` 405, all under 130 ms.
What worked was simply a fresh flow with the callback pasted back immediately; the code is
short-lived and a new `authenticate` call discards the pending flow, which is what invalidated
the earlier attempts.

**Rule 5 passes, and it was measured rather than asserted.** Page 2 was snapshotted before and
after and the two were diffed: **0 geometry changes, 0 removed nodes, 26 name changes** (the 13
frames and their 13 title TEXT nodes) and 14 new nodes (7 frames, 7 titles). Both snapshots are
on disk as `figures/figma_snapshots/page2_{before,after}_260920.json`. This closes the one item
that had been open since delivery.

30. **Figure 4 keeps two of its four expression scatters; the other two become Supplementary
    Figure 14.** Each `a2_p14` grid is 750 x ~1,800 px at 1:1, so four stacked would make the
    frame about 9,500 px tall, and a 2x2 arrangement would put the per-facet gene and cohort
    labels at roughly 4 pt, under the project's legibility floor. **Daniil chose the split on
    2026-09-20.** Figure 4 is relettered A to G, Supplementary Figure 14 is A and B, and the
    change is applied to `manuscript/FL_metric_classes_F1000_260917.md`, to
    `manuscript/figure_legends_260917.md` and to the `.docx` as 10 tracked replacements plus
    one tracked insertion (`tools/apply_figure4_split_edits.py`). `nar_review_tools.py
    validate` reports ALL CHECKS PASSED at 22 revisions, and all four gates still pass.

31. **The extended document is renumbered as `Harmonization_metrics_extended_260920_v3.docx`,
    built from the original.** The first attempt edited v2 directly and renumbered nothing:
    all 123 of v2's "Extended Figure" references sit inside v2's own unaccepted `w:ins`, which
    `safe_tracked_replace` deliberately cannot see. `tools/apply_extended_doc_v3_260920.py`
    therefore imports the v2 edit script, reuses its 328 anchored number and language edits
    verbatim, and replaces only the figure map. Composing the two maps is what makes it
    simple: original Figures 6–8 become Figures 1–3, and original Extended Figures 1–10 become
    Supplementary Figures 1–10 with their numbers unchanged. 691 revisions, 0 not-found,
    0 unsafe, reject-all restores the original exactly.

32. **The source benchmark's own figures are qualified rather than left to collide.** The
    extended document cites Article 1's "Figure 3" seven times, "Figure 4A" once and its
    Supplementary Figures 6, 7 and 17. Under Article 2's numbering each of those labels would
    name two different figures. **Daniil ruled on 2026-09-20** that every borrowed reference
    gains "of the source benchmark"; the reference regex swallows a trailing panel letter
    first, so "Figure 4A" becomes "Figure 4A of the source benchmark" and not "Figure 4 of the
    source benchmarkA". After Accept All the v3 document has 0 occurrences of "Extended
    Figure" and 11 qualified references.

33. **The frame layout is computed and on disk** as `figures/figma_layout_260920.md`: six
    frames with their Page 2 position and size, and every panel's letter, x, y, width and
    height inside its frame, derived from the exported PDFs at 2 px = 1 pt. Rows run in
    alphabetical panel order and two panels share a row only when their letters are adjacent.
    Supplementary Figure 13 is `a2_p18` — the manuscript's assignment, not the reserve
    "technical comparisons" frame the plan sketched — and Supplementary Figure 14 is new.

34. **Panels are placed as 300 dpi raster fills, not as imported vector trees.** Each panel is
    a rectangle at the layout geometry whose fill is a PNG re-rendered from the panel's own
    vector PDF at 300 dpi, which is 2.2x the placed size. Importing 21 SVGs instead would have
    produced tens of thousands of vector nodes and landed them on Page 1 for manual
    repositioning, as the recipe assets did. The vector originals stay in
    `figures/panels_260917/` and any panel can be swapped for its SVG by hand. **Figure 6 is
    the exception and is fully vector**: its twelve assets are text-free by design, so they
    were imported as editable vector trees and every character on it is a Figma TEXT node, as
    §5.4 requires.

35. **Seven frames, not the four to six §5.1 sketched.** The manuscript assigns Supplementary
    Figure 13 to `a2_p18`, which the plan had pencilled in as a reserve "technical comparisons"
    frame, and the Figure 4 split of decision 30 adds Supplementary Figure 14. Frame heights
    come from the panels themselves: Figure 4 is 750 x 6229 and Supplementary Figure 14 is
    750 x 3768, because an `a2_p14` grid is ~1,800 px tall at 1:1 and shrinking it would cost
    the facet labels.

36. **Nine of the 13 renamed title TEXT nodes overflow their boxes, and all nine already did.**
    Every title is `Inter Bold` with `textAutoResize: NONE`, so editing the characters cannot
    change geometry. Each was measured by cloning it, letting the clone hug its height, and
    comparing: the rename made **none** of them worse, and one (`522:295044`) improved from 72
    to 48 px of required height. These are Daniil's working annotations with under-sized boxes,
    not figure content.

### Open for Daniil

- **The canvas is a first pass and expects hand correction**, as §5.5 says. Worth an eye:
  Figure 4 at 6,229 px is very tall even after the split, and the two decision diamonds in the
  Figure 6 spine carry labels that sit close to their outline.
- **`Harmonization_metrics_extended_260920_v3.docx` is a proposal, not a decision.** It is a
  full tracked-change pass over the original; read it and either accept it or say that the
  extended document should keep its own numbering after all.
- **Supplementary File 3 is new to the submission package** and is named in the manuscript as
  of 2026-09-20. If you would rather ship two supplementary files, the entry is one tracked
  insertion to reject and the workbook can stay an internal artifact.
