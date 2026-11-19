# Decision gates of the Article 1 revision — review document for Daniil

Date: 2026-11-02; **answered by Daniil 2026-11-03** (G1, G2, G3, the small decisions and the
follow-up questions Q1 / Q2). This version records every answer and its consequences in place of
the inline comments. Revision of NARGAB-2026-312. Plan: `article_1_revision_implementation_plan_261029.md`
(§13 lists the gates). Manual: `README.md`.

**Status after the answers (2026-11-07, second review).** G1, G2 (rule frozen 2026-11-03, MD5
`17d4fe01…`) and G3 are answered. **G2b is closed**: round 1 (2026-11-04, §4.3: 16 accepted, 35
vetoed, 2 without comment), round 2 and the leftovers (2026-11-07, §4.4–§4.5) → final selection of
**22 approaches**, no round 3. G4: the digests (§6.1–§6.5) are read and agreed; the requested
extra figures and statistics are done (§6). **G4 answered 2026-11-07 (third review, §9.1)**:
gradient panel = selected methods only; Angel and M-ComBat added to the gradient (pod run from
the Mac); the two multi-platform leaves merged; title kept on SVA and FSQN R; leave-cohort-out
reported as option (a); no-harmonization finding into the Discussion; Figure 3 and Figure 6F
redrawn after Daniil's Figma; statistical annotations on every comparison boxplot; **no
comparison with the submitted version anywhere** (§9.2); stage B written 2026-11-07 (§9.3).
**2026-11-08:** Angel / M-ComBat gradient collected, stage B re-run, review package built (§10);
P5 answered (§9.4). **2026-11-08 (fourth review):** §10.6 approved (strategy codes, Q1 b, Q2 a, harshness per method), B1–B5 answered (§9.4) → implemented (§11). Files for the final review: §11.4.
**2026-11-08 (figure-notebook review, `daniil_review_261108.md`):** answers in §12.1, decisions
D1–D5 in §12.2, plan `figure_review_corrections_plan_261108.md`. **What to review next: §12.3**
(then §11.5).

**Blindness note.** Everything here was computed without applying the selection rule. No gate pass
rate, Pareto front or pick was computed or looked at (`CLAUDE.md` hard rule 2). The numbers below
are data availability and metric structure only.

Short glossary (internal labels; none of them goes into a publication document):
- L = marker correlation preservation (`mk_rho_mean_all_genes_narrow_set`).
- N = cross-batch diagnosis prediction: leave-one-batch-out 3-class macro-F1,
  `pv_lobo3_f1_macro_mean`. N2 = the same with 2 classes (DLBCL vs FL), `pv_lobo2_f1_macro_mean`.
- "approach" = strategy × imputation × method × post-removal.
- analysis set = the 2,234 approaches with `pct_samples_allNA < 5`.
- post0 / post1 = without / with the post-harmonization removal step.

---

## 1. Overview: the gates, their status and what each one blocks

| Gate | Decide | Status (2026-11-07) | Blocks |
|---|---|---|---|
| G0 | the plan | done | — |
| G1 | the reduced metric panel and the four headline metrics | **answered** (Q1 answered: PC regression on diagnosis kept) | the bars used by the rule; final Figure 3, S4–S6 |
| G2 | the written selection rule (then frozen by MD5) | **answered and frozen** 2026-11-03 (MD5 `17d4fe01…`; `md5sum -c FROZEN_MD5.txt` passes 2026-11-07) | — |
| G2b | which approaches the rule selects; accept or amend (version 2); vetoes | **closed** 2026-11-07: 22 approaches selected; leaf assignment provisional (§4.5) | Table 3, Figure 6F, the plots of the picks (nb07) |
| G3 | pilot review | **answered** → full runs from the Mac now | — |
| G4 | the results | **answered** 2026-11-07 (§9.1); Angel / M-ComBat gradient collected 2026-11-08 (§10); open: Q1 / Q2 of §10.6 | stage B |
| G5 | the response-letter wording | draft exists; final after G4 | final letter |
| G6 | the tracked manuscript, the ledger, the label scan | after G4 + stage B | submission |

```
G1 ─┐
    ├─> G2 freeze (MD5) ─> r04 --review ─> G2b ──────────┐
    │                                                     ├─> r05, r22, r13 ─> G4 ─> stage B ─> G5, G6
G3 (answered) ─> full runs on the pods (Mac) ─────────────┘
```

The full runs do not need the rule. Start them now; the freeze can happen while they run.

---

## 2. Gate G1 — the reduced metric panel and the four headline metrics

### 2.1 Decisions (Daniil, 2026-11-03)

| Item | Decision |
|---|---|
| Panel | Approved, with one change: **the tSNE centroid dispersion on batch is removed**, because tSNE preserves only local neighbourhoods, not distances, so a distance between tSNE batch centroids means nothing. The removal applies to every panel variant (`r02` `EXCLUDED_METRIC_PREFIXES`). |
| (a) Coverage additions | **Removed** (option "23"): the two distance ratios are not added back; group H counts as represented by its cluster mates (PC regression on batch, |ρ| = 0.94; PC regression on diagnosis, |ρ| = 0.83). |
| (b) Local headlines | Accepted (kBET + graph connectivity), **plus the robustness variant "local bars = runner-up metrics"** (UMAP entropy on batch, cLISI on diagnosis), fixed now, before G2b. |
| (c) Global bars are rough summaries | Noted. |
| (d) Tie-breaks | Accepted. |
| (e) Group D | Kept. |

### 2.2 The four headline metrics ("where are they?")

They are in `output/wp3/bar_headlines.tsv` (written by `r03_four_scores.py`) and in step 3 of
`adjudication_rule_261029.md`:

| Bar | Headline | How chosen |
|---|---|---|
| Global batch removal | PC regression on batch (`PCReg_RNA_BATCH`) | medoid of the 8 Global-batch panel metrics |
| Global diagnosis retention | PC regression on diagnosis (`PCReg_Diagnosis_cell_type_unified`) | fixed by Daniil (Q1, §2.4) for symmetry with the batch bar; the medoid would be WaterMelon mean biology |
| Local batch mixing | kBET acceptance rate on batch | medoid tie with UMAP entropy; simpler statistic |
| Local diagnosis separation | graph connectivity on diagnosis | medoid tie with cLISI; simpler statistic |

### 2.3 Result of the rebuild (r02 → r03 → nb02 → r45 → r40 re-run 2026-11-03)

- Universe: 32 metrics (33 − tSNE centroid dispersion). At cut 0.2: **22 clusters → 22-metric
  panel**, with no coverage additions. 8 groups are in the panel (A, B, C, D, E, G, I, K); group H
  is covered through cluster mates (`coverage_additions.tsv` lists them). Group C stays through UMAP
  centroid dispersion and UMAP entropy.
- The KS mean D on batch joined the PC-regression-on-batch cluster (it had been the tSNE metric's
  mate).
- 1,993 of 2,234 approaches are complete on the panel (unchanged).
- Variants: cut 0.1 → 25 metrics; cut 0.3 → 22; all 87 at 0.2 → 45.
- η² on the panel: method 0.333, strategy 0.277, imputation 0.010, post-removal 0.002 (87-metric
  check unchanged: 0.3629 / 0.2564 / 0.0155 / 0.0020).
- Figure 3 / S4–S6 re-rendered (nb02; missing cells black, decision s1).

### 2.4 Question Q1 — the Global-biology headline moved (answered 2026-11-03)

The review document said that dropping the distance ratios "changes neither of the four headline
bars". **That was wrong.** PC regression on diagnosis was the medoid only because its cluster mate,
the distance ratio on diagnosis (|ρ| = 0.83), was a bar member. Without it, the summed |ρ| to the
other Global-biology metrics is:

| Metric | Summed \|ρ\| to the other 3 |
|---|---|
| WaterMelon mean biology (`wm_mean_bio`, no annotation column) | **1.255** (new medoid) |
| WaterMelon on diagnosis | 0.928 |
| PC regression on diagnosis | 0.825 |
| diagnosis ASW | 0.800 |

Options considered:

| Option | Pros | Cons |
|---|---|---|
| Keep PC regression on diagnosis (current) | the approved headline; symmetric with Global batch (PC regression on batch); one sentence in the Methods | not the medoid of its bar after the panel change: a stated exception to rule D7
| WaterMelon mean biology (the medoid) | follows D7 to the letter | averages several biology columns, not only diagnosis; less known metric; the Global batch / biology pair becomes asymmetric |
| WaterMelon on diagnosis (medoid among the Diagnosis-column metrics, as rule step 3 prefers that column) | diagnosis-specific; second-best medoid | a second rule exception |

**Decision (Daniil, 2026-11-03): keep PC regression on diagnosis.** Implemented in r03
`HEADLINE_OVERRIDES` (logged in `bar_headlines.tsv`) and step 3 of the rule. Stage B adds one
Methods sentence: the headline is fixed for symmetry with the batch bar. r05's "axis mean" variant
shows whether the choice matters.

---

## 3. Gate G2 — the selection rule

### 3.1 Decisions (Daniil, 2026-11-03)

| # | Question | Decision | Implemented |
|---|---|---|---|
| — | The rule (gates L / N, Pareto front, visual check) | approved | `adjudication_rule_261029.md` (final text) |
| 1 | Approaches without L / N (the 84 Shambhala) | **include Shambhala** (default `P0std / Q0std`, Shambhala2_fast) | No new compute was needed. The blind check already computed L / N for `shambhala_P0std_Q0std`, and those are the same matrices as `20_shambhala` (its published metrics agree exactly on all 84). `rl.load_ln_columns` maps the name: 84 / 84 have L, 83 / 84 have N (S0, KNN, with post-removal has none and is "not evaluable"). |
| 2 | N_raw: same post-removal | accepted | r04 |
| 3 | p < 0.05 with n_perm = 100 | accepted | r04 |
| 4 | Scenario pools | one multi-platform pool **with D**; for D, gate N uses the **2-class (DLBCL vs FL) N** | `rl.TWO_CLASS_N_STRATEGIES`, r04 `apply_gates` (N2 and its own null / p and the 2-class N_raw) |
| 5 | Approaches identical to raw | **a method failure**, not a candidate | `rl.flag_identical_to_raw`; r03 column `identical_to_raw`; r04 step 1b; r13 / r22 also mark such new runs |
| 3.4 | Amendment criterion in version 1 | **yes**: version 2 only for a veto-class failure or an empty scenario | rule section "When a version 2 is allowed" |
| new | PCA / UMAP / tSNE of the rule's picks, drawn like Figures 4–5 and Supplementary Figures 11–17 | requested | `nb07_selected_approaches_embeddings.ipynb`, run after G2b (it reads the picks) |

### 3.2 Gate N for strategy D

D keeps 10 Normal B samples, so its 3-class N mostly measures DLBCL vs FL. Gate N therefore uses
N2 for D (156 / 156 D approaches have N2; the D `01_raw` row gives N2_raw). The Pareto bars of D
remain those of the panel (computed on the samples D has); the rule's informativeness table says
so.

### 3.3 Question Q2 — "identical to raw" is wider than the review said (answered 2026-11-03)

The review counted only three methods. Applied to every method, the mechanical criterion (PC
regression on batch and on diagnosis plus batch and diagnosis ASW, all equal to the `01_raw` row
at the 6-decimal precision of Supplementary File 3) flags **111 approaches**:

| Method | Flagged | Strategies |
|---|---|---|
| exploBATCH | 49 | A, B, C, D, E1–E3, F, G (5 each), S0 (4) |
| RUV-III-PRPS | 27 | A, B, C, D, E1–E3, G (3 each), F (1), S0 (2) |
| DWD | 19 | J, K, I (4 each), A (3), H, S0 (2 each) |
| FSQN R | 10 | K (4), G (3), H (2), F (1) |
| SVA | 6 | G (5), C (1: strict, with post-removal) |
| ComBat (control) | 0 | — |

Why these four metrics: UMAP / tSNE metrics differ between runs of the same matrix, and coarse
metrics (kBET, % NA, bimodality fractions) agree by chance. The four chosen are deterministic.
(The marker correlation L would also be a natural test, but it is ≥ 0.99999 rather than exactly 1
for several of these approaches, so they are near-identical rather than bit-identical.)

What it means: FSQN R in K (FFPE only), DWD in J (FF only) and K, and RUV-III-PRPS in C and the
multi-platform pool returned (practically) their input in those approaches. Under the approved
rule they become "method failed (returned the input)". None of the 15 visual picks of Table 3 is
flagged (K's picks are SVA, J's are MNN and FSQN R with no imputation, and these are not flagged).

| Option | Pros | Cons |
|---|---|---|
| Apply the criterion to every method (current) | mechanical, as approved; the rule cannot recommend a method that did nothing | FSQN R (a title method) is flagged in 10 single-platform approaches: one Methods sentence, plus the G4 flag column in Supplementary File 3 |
| Apply it only to the two methods with a documented fallback (SVA, exploBATCH) | matches the review text exactly | DWD / RUV / FSQN R approaches that returned their input could reach a front |

**Decision (Daniil, 2026-11-03): apply the check to every method.** Every approach that returns
its initial matrix without actual harmonization fails (111 approaches). Implemented in
`rl.flag_identical_to_raw` (r03 column `identical_to_raw`), r04 step 1b, r13 / r22 for the new
runs, and step 1b of the rule text.

### 3.4 Freeze (done)

The rule was frozen on 2026-11-03: `FROZEN_MD5.txt` holds `17d4fe01454d3485a72434f7cec17bb6
adjudication_rule_261029.md`, and `md5sum -c FROZEN_MD5.txt --quiet` passes (checked again
2026-11-07). Daniil's "freeze" of 2026-11-07 confirms it; nothing was changed.

---

## 4. Gate G2b — review of the rule's picks

**When:** minutes after the freeze. **Read:** `output/wp4/selection_review.xlsx` (+ `.md`): one
sheet per scenario (front members in rule order, four bars, gate values, which N was used, kept /
lost / new vs Table 3), Table 3 preview, Figure 6F leaf preview, vetoes, method failures,
leave-strategies-out. **Plus** the PCA / tSNE / UMAP plots of the front members (nb07), coloured
like Figures 4–5 and S11–S17.

**You decide:** (1) accept version 1, or (2) amend, only for a veto-class failure or an empty
scenario (rule section "When a version 2 is allowed") → `adjudication_rule_261029_v2.md`; (3) the
leaf assignment of the multi-platform front members (platform colouring); (4) vetoes, each with a
reason.

### 4.1 Answers (Daniil, 2026-11-03, first part of G2b)

| # | Item | Decision | Consequence |
|---|---|---|---|
| G2b-1 | Version 1 picks | **approved**; no version 2 | `selection_by_rule.tsv` (rule MD5 `17d4fe01…`) is the selection; vetoes still open (G2b-3) |
| G2b-2 | "No batch removal" pool | **new information-only scenario**: the frozen rule applied to S0 (no removal) alone — which imputations and methods are best when no batch may be removed (question raised on the sheet "Multi-platform (RNA-seq + micro…") | r04: one more information-only pool, like "Microarrays only"; the rule text is unchanged (pools that are not tree leaves are reporting only). Reported as a question asked after the freeze, not as a rule pick |
| G2b-3 | Plots for the visual check | **every selected approach**, PCA / UMAP / tSNE, coloured by diagnosis and by RNA batch, **next to the unharmonized data of the same strategy and imputation**; with post-removal, the removed batches drawn faint | nb07 rewritten (approach-by-approach raw vs harmonized pairs); vetoes decided by Daniil after reading them ("do batches mix within the same biology?") → `output/wp4/vetoes.tsv` |
| G2b-4 | Title | Daniil reads the leave-strategies-out sheet as "only FSQN R and SVA are robust and generalizable; the rest depend on the assembled cohort set" → **keep the title on SVA and FSQN R** | position recorded; final at G4 (title claim) together with the leave-cohort-out and gradient results; see the caveats in §4.2 |

### 4.2 Facts behind G2b-4 (from `output/wp4/`, for the G4 discussion)

- The leave-strategies-out check removes A, B, E1–E3 only from the **multi-platform** pool; the
  three single-type pools have no such strategies, so their "with" and "without" rows are equal by
  construction. The sheet therefore tests FSQN R's robustness (multi-platform front in both pools,
  rank 2 → 1), not SVA's.
- SVA is on two leaf fronts: FFPE only (rank 1) and RNA-seq only (rank 4). It is on no
  multi-platform front.
- The sheet lists only FSQN R, SVA and MNN. **ComBat and M-ComBat also stay on the multi-platform
  front without A, B, E1–E3** (front 12 → 8 members: FSQN R and FSMVN on D, ComBat on D and I,
  M-ComBat on I), so "robust to removing the FSQN-derived strategies" holds for them as well.
- **MNN is on no front** (submitted Table 3 has 4 MNN picks; the approved tree names MNN for FF only
  and for RNA-seq + various microarrays). FSQN R is not on the FF-only or RNA-seq-only fronts.
  Stage B must reconcile the tree and Table 3 with the fronts (G4).
- Generalizability is tested directly by the leave-cohort-out experiment (r22, full run on the pod)
  and the gradient (r13); the title decision uses them at G4.

### 4.3 Visual check, round 1 (Daniil, 2026-11-04)

Daniil read the nb07 pair plots of the 53 version-1 front members (`figures_svg/g2b_review/`).
Every decision, with its reason, is in `output/wp4/visual_check.tsv`; the vetoed rows are also in
`output/wp4/vetoes.tsv` (the file r04 / r05 read). Daniil asked that the main text explain why each
approach was rejected → draft D-1 in `stage_b_text_drafts.md` (r50 stage-B item 11).

| # | Scenario | Accepted | Vetoed (reason) |
|---|---|---|---|
| 1 | RNA-seq only | — | Shambhala-2, all three imputations, with post-removal: the post-removal deletes the whole `RNASeq_FFPE_Exome_capture` batch (939 of 2,243 samples) and keeps only FF; an RNA-seq-only approach must mix FF and FFPE |
| 2 | RNA-seq only | SVA, KNN and SoftImpute, no post-removal: FF and FFPE mix (as shown in the submitted version) | — |
| 3 | RNA-seq only | — | ComBat-seq and InMoose ComBat-seq, no imputation: FF and FFPE do not mix on tSNE |
| 4 | No batch removal (S0 only) | Angel, all five members: PCA overlaps batches of the same biology; UMAP moderate (same biology close); tSNE only moderate (batches remain isolated groups). **To be noted in the text** | ComBat (SoftImpute, post-removal): no different from the unharmonized matrix on tSNE, PCA and UMAP |
| 5 | Multi-platform | FSQN R and FSMVN, Malignant only, KNN (tSNE / UMAP bring the two large DLBCL batches, RNA-seq FF poly-A and GPL14951 FFPE, together with minor batches; top on PCA); ComBat, Malignant only, no imputation, post-removal; M-ComBat, Rare batches removed, all three members (PCA: FL, DLBCL, normal B as separate constellations of batches, same biology closer) | the other six: M-ComBat on Confirmed bad, ComBat on Extended bad / Iterative r2 / Iterative r3 / Rare batches removed (× 2): no biology separation and no batch mixing on PCA / UMAP / tSNE |
| 6 | Microarrays only (information) | Angel, Affymetrix extended, SoftImpute, post-removal (UMAP: some DLBCL co-localization, FL scattered) | the other 12: tSNE isolated batch groups, no co-localization of the same biology; PCA no overlap |
| 7 | FFPE only | SVA, SoftImpute, no post-removal | the other four: batches of the same biology do not mix, or batches of different biology mix |
| 8 | FF only | Angel, SoftImpute, no post-removal (PCA: three distinct clouds FL / DLBCL / normal B) | the other seven: tSNE identical to the unharmonized matrix |

Totals (counted from `output/wp4/visual_check_round1_261104.tsv`; the earlier text said 17 / 34
by mistake): 16 accepted, 35 vetoed, 2 without a comment (RNA-seq only ComBat, no imputation; S0
M-ComBat, no imputation, post-removal) — decided in §4.5.

**How the vetoes were applied (as planned, rule step 4 and nb07 §5).** `r04_apply_rule.py` was
changed so that the blind version-1 picks are never touched by a veto: `selection_by_rule.tsv`
stays byte-identical to the file reviewed on 2026-11-03. A second front, without the vetoed
approaches, is written to `selection_after_visual_check.tsv` (column `visual_check`: accepted / no
veto given / not reviewed) with its own Table 3 concordance file. Removing a front member lets
approaches it dominated enter the front, so **28 approaches entered that were never shown**:
FF only 8 (Angel × 4, ComBat × 2, M-ComBat × 2), FFPE only 4 (NPN × 2, pyComBat, FSMVN), RNA-seq
only 6 (all with post-removal: VST, no harmonization, rank normalization × 2, qsmooth, TMM),
multi-platform 4 (M-ComBat on Confirmed bad; ComBat on Malignant only, Extended bad, Iterative r1),
microarrays only 5, S0 1 (ComBat, SoftImpute, no post-removal). nb07 round 2 (`REVIEW_ROUND = 2`)
draws only these → `figures_svg/g2b_review_round2/`, removed batches in
`output/wp9/nb07_removed_batches_round2.tsv`.

Two facts for round 2:
- The six new RNA-seq-only entrants all use post-removal, and one of them is **"no harmonization"**
  itself; if their post-removal also deletes the FFPE exome-capture batch, veto reason 1 applies to
  all of them (the round-2 removed-batches table says which).
- Robustness (r05, run 2026-11-04 with the round-1 vetoes; bridging variant still waits for the
  pod): FF-only Angel SoftImpute, FFPE-only SVA SoftImpute, multi-platform FSQN R Malignant only KNN
  and S0 Angel no imputation with post-removal are on the front in 7 / 7 variants; FSMVN and
  M-ComBat (no imputation, post-removal) 5 / 7; RNA-seq-only SVA only 2–3 / 7.
  `output/wp5/robustness_summary.tsv`, `front_stability.tsv`.

### 4.4 Visual check, round 2 (Daniil, 2026-11-07)

**Answer to "why is SVA missing now?"** SVA is not missing. The round-2 plots
(`figures_svg/g2b_review_round2/`) show **only the 28 approaches that newly entered the front**
because you vetoed some round-1 members. Everything you accepted in round 1 stays selected and was
not drawn again. In `output/wp4/selection_after_visual_check.tsv` (column `visual_check`):

| Scenario | Accepted in round 1, still selected |
|---|---|
| RNA-seq only | SVA + KNN, SVA + SoftImpute (no post-removal) |
| FFPE only | SVA + SoftImpute (no post-removal) |
| FF only | Angel + SoftImpute (no post-removal) |
| Multi-platform | FSQN R and FSMVN (Malignant only, KNN); ComBat (Malignant only, no imputation, post-removal); M-ComBat (Rare batches removed, × 3) |
| Microarrays only | Angel (Affymetrix extended, SoftImpute, post-removal) |
| No batch removal (S0) | Angel × 5 |

Every non-vetoed round-1 approach goes into the final tables and text (r04 marks them
`accepted`; Table 3, Figure 6C/D and 6F read that column).

**Round-2 decisions** (written to `output/wp4/visual_check.tsv` with `review_round = 2`, vetoed
rows also to `vetoes.tsv`, 2026-11-07; round-1 copies kept as `*_round1_261104.tsv`):

| Scenario | New members | Accepted | Vetoed (reason) |
|---|---|---|---|
| RNA-seq only | 6 | — | all 6 (VST, no harmonization, rank normalization × 2, qsmooth, TMM): every one uses post-removal that deletes the whole `RNASeq_FFPE_Exome_capture` batch (939 of 2,243 samples, confirmed in `output/wp9/nb07_removed_batches_round2.tsv`); losing almost half of the samples is not a success. **Discussion text:** these approaches failed because the post-removal step removed a major batch (draft D-1) |
| No batch removal (S0) | 1 | — | ComBat, SoftImpute: batches scattered, no co-grouping by biology, no structure |
| Multi-platform | 4 | ComBat, Malignant only, no imputation, **no** post-removal: marginal success on PCA (FL mostly right, DLBCL mostly left); UMAP / tSNE poor | M-ComBat (Confirmed bad), ComBat (Extended bad), ComBat (Iterative round 1): batches scattered, no biology co-grouping |
| Microarrays only | 5 | — | all 5: batches completely isolated even on PCA, no biology structure |
| FFPE only | 4 | — | all 4 (NPN × 2, pyComBat, FSMVN): isolated batch clouds whose structure prevails over biology |
| FF only | 8 | Angel × 4 (SoftImpute + post-removal; KNN; no imputation + post-removal; KNN + post-removal): batches of the same biology co-localize | ComBat × 2, M-ComBat × 2: no batch correction visible |

Totals of round 2: 5 accepted, 23 vetoed.

**No round 3.** You asked not to add more approaches: vetoing round-2 members would again let
weaker, dominated approaches enter the front, and they are presumably worse. Decision: the visual
check is **closed after round 2**; the final selection is the set of accepted approaches (plus
the two members of §4.5 if you do not veto them). The frozen rule text allows this: step 4 only
says a front member may be vetoed, it does not require refilling the front. The Methods will say
it plainly: "Approaches vetoed at the visual check were removed; the front was recomputed once and
its new members were checked the same way; it was not recomputed again." Implemented in r04
(`VISUAL_CHECK_CLOSED = True`): `selection_after_visual_check.tsv` now holds only the accepted
approaches; the 20 approaches that would enter after the round-2 vetoes are listed in
`output/wp4/not_added_check_closed.tsv` and never recommended. `selection_by_rule.tsv` (blind
version 1) is byte-identical to the file reviewed on 2026-11-03 (MD5 `7de86b95…`).

**Final selection** (after §4.5): FF only 5 (Angel × 5); FFPE only 1 (SVA); RNA-seq only 3
(SVA × 2, ComBat); multi-platform 7 (FSQN R, FSMVN, ComBat × 2, M-ComBat × 3); microarrays only 1
(Angel; information only); S0 5 (Angel × 5). **Total 22.** Agreed by Daniil.

Note on the FF-only Angel approaches with post-removal: they drop only one small batch each
(`RNASeq_FF_Unknown`, 79 samples, or `GPL17586_FF_Unknown`, 40 samples), unlike the RNA-seq case.
Agreed.

**Decision tree (stage B, item 18):** FF only → Angel (not MNN / FSQN R as in the submitted
tree); FFPE only and RNA-seq only stay SVA; MNN is on no front. **Accepted by Daniil** ("it is
honest").

### 4.5 The last G2b items (answered 2026-11-07)

| Item | Decision (Daniil) | Implemented |
|---|---|---|
| RNA-seq only, ComBat, no imputation, no post-removal | **accepted**: converges biology and separates batches on PCA, moderately on tSNE | `visual_check.tsv` |
| S0, M-ComBat, no imputation, with post-removal | **vetoed**: does not mix or overlap batches of the same biology; no biology co-clustering structure | `visual_check.tsv`, `vetoes.tsv` |
| Leaf of the 7 multi-platform approaches | **all to "RNA-seq + Illumina microarrays" for now** | `output/wp4/leaf_assignment.tsv` → r04 column `tree_leaf_name` → Figure 6F |

Consequence: the leaf **"RNA-seq + various microarrays" has no accepted approach** (the submitted
tree had MNN + post-removal there; MNN is on no front). Figure 6F shows the leaf with "No approach
accepted at the visual check". To revisit at G4 (§9, P3.5).

---

## 5. Gate G3 — pilot review (answered 2026-11-03)

Pilot facts: `output/wp6/pilot/pilot_report.md` (gradient 24 / 24 run; leave-cohort-out 62 / 62 =
59 ok + AMDBNorm timeout at 2 h + exploBATCH × 2 failed; metrics 82 / 82 ok, median 4 min per job).

| Item | Decision | Implemented |
|---|---|---|
| Proceed to the full runs | **yes** | RUNBOOK §6 rewritten |
| (a) AMDBNorm | keep in both experiments, **6 h timeout**; a run over 6 h is skipped | default `--timeout-s 21600` (`revision_dispatch`); a timed-out run now writes a "timeout" run record on S3, so `--skip-if-exists` does not restart it and r14 / r22 see it (it was the r14 gap) |
| (b) HarmonizR, Shambhala | keep, 6 h timeout | same |
| (c) exploBATCH | remove if the ComboBatch image lacks it → **it does**: the pilot record says "fMM R package not available"; removed from leave-cohort-out | `r21 --exclude-methods` defaults to `36_explobatch` → 30 methods, 1,200 runs |
| (d) SVA fallbacks | accept and report; the gradient slope of SVA uses the remaining λ levels | r13 marks runs identical to their `01_raw` as `method_returned_input`; r22 as method failures |
| (e) covariate-free wrappers | accepted | — |
| (f) Node | **32–48 vCPU, ≥ 64 GiB for every computation** | both manifests: worker 44 CPU / 80 GiB, `karpenter.k8s.aws/instance-cpu: "48"` (c6a.12xlarge, 48 vCPU / 96 GiB); emptyDir 40 GiB |
| (g) Group D metrics | kept | — |

Remaining full-run work (dry-runs on 2026-11-03): gradient 516 harmonizations (43 preparations);
leave-cohort-out 1,141 (C 241, K 300, J 300, S0 300; 38 preparations); then the metrics of both
experiments (540 + ≤ 1,200) and the bridging check (2,234, Shambhala matrices read under their
stored name).

---

## 6. Gate G4 — the results (after the full runs and G2b)

**Read:** the three digests below (§6.1–§6.3) instead of the raw tables; the raw tables stay the
source: `output/wp5/robustness_summary.tsv`, `output/wp6/`, `output/wp7/v1_summary.tsv`, and the
leave-strategies-out result (§4.2). Daniil read and agreed with the digests on 2026-11-07. r05,
r40, r45, nb03–nb05 were re-run with the closed G2b (round 2); the conclusions did not change.

### 6.1 Robustness: what the column `variant` means

Each row asks: "if we had built the four bars a little differently, would the rule still rank
the approaches of this scenario the same way?" The **reference** is the frozen rule (22-metric
panel at cut 0.2, one headline metric per bar). A variant changes one thing:

| `variant` | What is changed | What it tests |
|---|---|---|
| `panel_cut0.1` | metric panel built with a stricter correlation cut (25 metrics) | the panel cut. Gives exactly the reference (τ = 1) because every bar keeps the same headline metric |
| `panel_cut0.3` | looser cut (22 metrics, other clusters); the Global-biology headline becomes WaterMelon mean biology | the panel cut and the headline choice of Q1 |
| `all_87_metrics` | no reduced panel: all 87 published metrics; Global-biology headline becomes diagnosis ASW | whether the panel reduction matters |
| `axis_mean` | each bar = mean of all panel metrics of that bar, not one headline | "one headline" vs "average of the bar" |
| `group_balanced` | each bar = mean of the metric-group means (each group A–K weighs the same) | whether large metric groups dominate |
| `local_runner_up` | the two local bars use the runner-up metrics (UMAP entropy on batch, cLISI on diagnosis) | the kBET / graph-connectivity choice (G1 b) |
| `bridging_biology` | the two diagnosis bars recomputed only on batches that hold ≥ 2 diagnoses | whether "biology" is just batch in disguise |

Columns: `kendall_tau_b` = agreement of the whole ranking with the reference (1 = identical,
0 = unrelated); `top3_jaccard` = overlap of the three best (1 = same three, 0 = none shared);
`front_jaccard` = overlap of the Pareto fronts; `n_front_reference` / `n_front_variant` = front
sizes.

**What it says.** Whole rankings are stable (τ 0.65–0.98, most ≥ 0.8). The very top is not: top-3
overlap is often 0.2, i.e. which approach is "number 1" depends on how the bars are built. Least
stable: RNA-seq only (τ 0.65–0.76 except bridging). The selected approaches that survive most
variants (`front_stability.tsv`, 7 / 7): FF-only Angel SoftImpute, FFPE-only SVA SoftImpute,
multi-platform FSQN R Malignant only KNN, S0 Angel. Suggested text: "the rankings are robust, the
single best approach is not; we therefore report the front, not a winner."

After the round-2 re-run: τ 0.65–1.00 (median 0.86), top-3 Jaccard median 0.5, lowest for the bar
definitions (axis mean, group-balanced, local runner-up: median top-3 Jaccard 0.20). Of the 22
selected approaches, 4 stay on the front in all 8 rankings (FF-only Angel SoftImpute, FSQN R
Malignant only KNN, S0 Angel no imputation + post-removal, microarray Angel) and FFPE-only SVA and
FF-only Angel KNN in 7 / 8; the RNA-seq-only approaches in 3–4 / 8 (`front_stability.tsv`, column
`selected_after_visual_check`).

**Daniil (2026-11-07): agrees with the results and the conclusion; asked for a bar plot of the
statistics by variant.** Done: `figures_svg/figS16a_robustness_tau.pdf` is now three bar panels
(Kendall τ-b, top-3 Jaccard, front Jaccard): bar = median over the 6 pools, line = range, dots =
pools coloured by strategy. The high τ bars next to the low top-3 bars show "stable ranking,
unstable top" at a glance. `figS16b_front_stability.pdf` now shows the 22 selected approaches,
coloured by method. **Daniil (2026-11-07, third review): the figures are OK, no more requests.**

### 6.2 Confounding gradient (`output/wp6/`): digest

**λ steps confirmed:** λ = 0, 0.1, 0.2, …, 1.0 (11 levels) × 3 replicates (capped, 33 designs of 405
samples) + the same 11 levels × 1 replicate without the cap (505 samples) + the 11 single-diagnosis
batches = 45 designs (`output/wp6/designs/designs.tsv`). Measured V of the capped replicate 1: 0,
0.014, 0.169, 0.287, 0.388, 0.490, 0.592, 0.690, 0.799, 0.896, 0.998.

**What was done.** From 5 real batches (3,404 samples) we built artificial cohorts in which the
link between batch and diagnosis grows step by step (λ = 0 → 1, Cramér's V 0 → 1; 0 = every batch
has the same diagnosis mix, 1 = every batch is one diagnosis). 3 replicates per step, 12 method
arms (no harmonization, limma, SVA and ComBat with and without the diagnosis covariate, MNN,
Harmony, FSMVN, FSQN R, quantile, AMDBNorm), the same metrics as the benchmark. The real cohort
sits at V = 0.36 (all samples) / 0.40 (the 5 batches).

**Files:** `gradient_slopes.tsv` (main result: change of each score from V = 0 to V = 1, slope,
"meaningful" = change > 2 × replicate SD; **new:** `spearman_rho`, `spearman_p`, `spearman_fdr`,
`significant_fdr`, `changes_with_confounding`); **new** `gradient_ranks.tsv` (rank of every arm
under the selection rule in every design); `gradient_anchors.tsv` (medians at λ 0 / 1);
`gradient_scores.parquet` (every run); `gradient_failures.tsv` (6 failed runs; plain-word reasons in
`output/wp9/nb04_gradient_failures.tsv`); `gradient_cap_sensitivity.tsv` and
`gradient_single_dx_control.tsv` (checks); `designs/` (inputs). **Agreed (2026-11-07), no more
requests.**

**What "cap sensitivity" is and why it matters.** The cap limits every batch to 150 samples. Only
one of the 5 gradient batches is larger (GPL570 FF, 250 samples available); without the cap it would
hold half of every design (250 of 505) and dominate every metric. The cap keeps the batches
comparable but makes the design less like the real data. The uncapped series (same 11 λ levels,
replicate 1) checks that the cap does not create the result: `gradient_cap_sensitivity.tsv` compares
the slope of each arm × score with and without the cap (e.g. no harmonization, N: −0.23 capped vs
−0.24 uncapped). Small differences mean the conclusions do not depend on the cap. **Agreed.**

**Spearman + FDR (Daniil's request).** For every arm × score: Spearman ρ between the score and V
over the 33 capped runs, two-sided p, Benjamini–Hochberg FDR over all 184 tested rows. A score now
"changes with confounding" only when **both** FDR < 0.05 **and** the change is > 2 × replicate SD.
On the six main scores (4 scaled bars, L, N; 66 tested of 72 rows, 6 constant): 43 FDR-significant,
35 meaningful, **30 both**. Over all scores: 120 significant, 105 meaningful, 89 both. S17b now
fills a marker only when both hold.

**Trajectories with my own eyes (Daniil's request), new panels of Supplementary Figure S17:**
- `figS17e_gradient_rank_trajectories.pdf`: rank of each method under the selection rule (1 = best)
  in every design, median over the replicates with a min–max band, against V; left the selected
  methods that are in the gradient (SVA, ComBat, FSMVN, FSQN R) with no harmonization as
  reference, right all 12 arms; dashed line = the real data. Main observation: **as V grows, no
  harmonization climbs to rank 1–2** (median rank 7 at λ = 0, 1 at λ = 0.5–0.6), quantile
  normalization reaches rank 1 at λ = 0.7–0.9, while AMDBNorm falls from rank 1 (λ ≤ 0.2) to 10–11
  and the covariate-free ComBat from 2 to 5–8: when batch and diagnosis coincide the rule can no
  longer reward batch removal. Only 19–25 % of the runs pass both gates at λ = 0.5–0.9 (58 % at
  λ = 0, 45 % at λ = 1). **Daniil's reading (2026-11-07):** above V ≈ 0.4 no harmonization is
  almost the best approach; under strong confounding it is better not to harmonize at all. This
  is the Discussion sentence of G4.5 (§9.1).
- `figS17f_selected_methods_scores.pdf`: the four scaled bars, L and N of the same selected
  methods, one panel per score, mean ± SD.
- `figS17d_gradient_scatter.pdf` (approved in §6.4): batch removal vs diagnosis retention at λ = 0,
  0.4 (≈ real data) and 1, Pareto-front methods labelled.
- Angel and M-ComBat are selected too, but they were not in the fixed gradient method set (plan
  WP6 6.3, decided before running); see §9 P2 for adding them.

**Failures (Daniil: "report them").** 6 runs: ComBat with the diagnosis covariate stopped with an
error in all 4 runs at λ = 1 and on the single-diagnosis control (covariate = batch, singular
design); AMDBNorm exceeded the 6-hour limit on the 2,068-sample single-diagnosis control. Methods
text: draft D-2 in `stage_b_text_drafts.md`.

**Digest format saved (Daniil's request):** section "Presenting results for Daniil's review" in the
project `CLAUDE.md` and the memory `feedback_review_digest_format.md`. **Agreed.**

**Results (score at V = 0 → V = 1, * = meaningful):**

| Finding | Evidence |
|---|---|
| 1. Cross-batch diagnosis prediction (N) falls for **every** method, including no harmonization | N 0.75 → 0.44* (none), 0.73 → 0.52* (FSQN R), 0.87 → 0.50* (MNN). When a batch holds one diagnosis, the left-out batch has no training examples to learn from: N partly measures the design, not the method |
| 2. Methods that remove the batch also remove the diagnosis when the two coincide — and keep it when they do not | Global biology 0.44 → 0.20* (FSMVN), 0.44 → 0.19* (FSQN R), 0.36 → 0.12* (limma), 0.45 → 0.26* (ComBat without covariate), 0.35 → 0.11* (AMDBNorm). At λ = 0 (biology independent of batch) the same methods keep the diagnosis at least as well as no harmonization (global biology 0.44 / 0.44 / 0.45 vs 0.37) while removing the batch (global batch 1.00 vs 0.47) |
| 3. Methods that leave the batch in place look **better** on biology as confounding grows | Global biology 0.37 → 0.60* (none), 0.38 → 0.64* (SVA), 0.37 → 0.73* (Harmony): the batch signal is read as diagnosis |
| 4. Giving the diagnosis to the method leaks it | ComBat with the diagnosis covariate cannot run when every batch is one diagnosis (V = 1 and the single-diagnosis control: 5 of the 6 failed runs; the 6th is an AMDBNorm timeout); SVA without the covariate loses N (0.30–0.33) |
| 5. Up to the real level (V ≈ 0.4) the changes are moderate; the large ones start at V ≈ 0.6–0.8 | `fig6_gradient_panel`: e.g. FSQN R diagnosis retention 0.72 → 0.66 by V = 0.4, → 0.59 at V = 1; SVA / no harmonization flat until 0.6, then rise |

Message for the paper: at the confounding of our cohort the metrics are still informative, but
no metric can tell batch from biology when the two coincide; this is why the rule uses gates
plus a visual check, and why strategies that remove single-diagnosis batches matter. **Agreed by
Daniil (2026-11-07).**

### 6.3 Leave-cohort-out (`output/wp7/`): digest

**What was done.** For 4 scenarios (RNA-seq only, FFPE only, FF only, all samples) the cohorts
were split into 5 folds. In each fold the rule chose an approach on 4/5 of the cohorts
("training part"); then every method was run on the unseen 1/5 ("test part") and ranked there.
Question: does the approach chosen on some cohorts stay good on new cohorts?

**Columns of `v1_summary.tsv`:**
- `level_0` = scenario (C RNA-seq only, J FF only, K FFPE only, S0 all samples, overall).
- `role` = whose choice is evaluated: **chosen on the training part** (the rule's pick) or
  **random method** (expected value of picking any method at random — the baseline). The former
  third role, the method of the submitted decision tree, is removed everywhere (§9.2).
- `rank_on_test` = rank of that choice among ~30 methods on the test cohorts (1 = best).
- `top1_hit` / `top3_hit` = share of folds where it was the best / among the 3 best.
- `gate_pass_on_test` = share of folds where it still passed gates L and N.
- `regret_<score>` = **how much worse than the best method on the test part** it scored (best −
  chosen; 0 = it was the best). Lower is better.
- `fold_set` = all folds, or only the evaluable ones (the 4 folds that are one cohort with one
  batch and one diagnosis cannot be scored).

**Results (all folds):**

| Scenario | Rule pick, mean rank | Random | Rule pick top-3 | Comment |
|---|---|---|---|---|
| All samples | 7.2 | 13.3 | 60 % | Angel chosen in all 5 folds; best on the test part in 3 |
| RNA-seq only | 5.5 | 14.1 | 50 % | rule better than random |
| FF only | 8.2 | 13.7 | 20 % | Angel chosen in all 5 folds, in the top ~6 in 4 of 5 |
| FFPE only | 25.0 | 13.0 | 0 % | **rule fails**: in 3 folds the pick (ComBat × 2, limma) cannot run on the test cohorts (singular design), in 2 it ranks 22 and 28 |
| Overall | 9.3 | 13.5 | 37.5 % (random 11.6 %) | |

Message for the paper: in 3 of 4 scenarios the approach chosen on part of the cohorts stays
better than chance on new cohorts; in FFPE only it does not (the methods the rule picks there
need a design the small FFPE test cohorts cannot provide). Figures: `figS18a_v1_rank_on_test`,
`figS18b_v1_hit_rates`, `figS18c_v1_regret`.

**Daniil (2026-11-07, third review) — statistical annotations.** S18c gets pairwise
Mann–Whitney tests with Benjamini–Hochberg FDR and stars. General rule for every boxplot that
compares groups: **≤ 4 boxes → horizontal significance bars with stars above the boxes; > 4
boxes → a pairwise heatmap of FDR-adjusted p-values with stars** (as in Daniil's transposon
article, Figure 3D–E). Implemented in nb03–nb05 (§9.2) and saved in the `notebook_writing` skill.

**Daniil (2026-11-07, third review) — no "submitted decision tree".** The role is removed from
r22, `numbers.json`, S18a–c, Figure 6F, the letter and the text. Rule for the whole revision
(saved to memory `feedback_no_pre_revision_comparison.md` and to the skills scientific-review,
nar-review, word-rewrite, notebook_writing): **never compare the results after the revision with
those before it** in any plot, table or text of the revision — the reader does not care about
the earlier, weaker result. The same applies to Figure 3 ("submitted version" annotation), the
"All 87 metrics (submitted)" label of 6B and the Table 3 concordance with the old picks (§9.2).

**Daniil (2026-11-07): figures acceptable, conclusions good; make them more visually appealing,
article palettes in every figure, update the plan.** Done: S18a colours each point by the method
(`method_pal`) and uses the shape for the role (circle = chosen on the training part, diamond =
random); S18b carries value labels; light grids everywhere. Palettes now in nb03, nb04, nb05
(plan WP9, Phase 3b and §16).

### 6.4 Plots requested: "scatterplot of metrics and best approaches by λ"

**Palette error fixed.** `fig6_gradient_panel` used ad-hoc method colours. Every revision figure
now takes the article palettes: `method_pal` (the exact colours of the submitted figures, rebuilt
from `figures_for_article/Finally_assembled_figures_for_article.ipynb` cell 4 and written out as hex
in nb03–nb05 §0c), `strat_pal`, `imp_pal`, `post_rm_pal`; SVA / ComBat without the diagnosis
covariate share their parent's colour with a dashed line. The embedding palettes
(`lymphoma_ontogeny_palette`, `rna_batch_palette`, `platform_palette`) were already used in nb01 and
nb07.

**Scatter approved → done, as an added panel.** Because you liked S17a ("very nice figures"), it is
kept and the scatter became panel **S17d** (`figS17d_gradient_scatter.pdf`): the figure count does
not grow, only S17 gains panels (d scatter, e rank trajectories, f selected methods). The second
option (main-benchmark scatter per scenario) got no answer and was not made.

### 6.5 Method failures (answered 2026-11-07)

Decision: "just honestly state that some methods failed, with a simple description of the
error." Stage B writes one Methods paragraph listing, per method, what happened in plain words:
returned its input unchanged (exploBATCH 49, RUV-III-PRPS 27, DWD 19, FSQN R 10, SVA 6 approaches;
§3.3); package not available in the container (exploBATCH, leave-cohort-out); over the 6 h limit
(AMDBNorm, gradient single-diagnosis control and one leave-cohort-out pilot run); cannot run when every batch has one diagnosis
(ComBat with the diagnosis covariate, limma: singular design). Plus the flag column in Supplementary
File 3.

**Interpretations already fixed in the plan:** gradient slope meaningful only if |Δ| (V 0 → 1) >
2 × replicate SD at λ = 0 (C2), real data at V = 0.398; leave-strategies-out FSQN R stays / leaves
the front → one Results sentence / Discussion qualifies the tree; leave-cohort-out "transferred in
x of 20 folds (top-3)", with 4 single-batch single-diagnosis test folds "not evaluable" (C4).

**Items for G4:** how the manuscript reports the method failures (approaches that returned their
input; §3.3 counts) — e.g. one Methods sentence plus a flag column in Supplementary File 3; the
best set, the Abstract / Conclusions / tree edits (D5), the title claim (FSQN, SVA), the stage-B
paragraphs (23 items in the `r50` docstring). Known from WP1: strategy confounding (Cramér's V
0.28–0.49) does not predict the best biology scores (Spearman ρ 0.31, p = 0.27 global; 0.07,
p = 0.82 local; n = 14, low power; global value recomputed with the 22-metric panel). Method failures: answered, §6.5.

---

## 7. Gates G5 and G6 — letter and manuscript

**G5:** `response_letter_draft.md` (6 `[PENDING]` sentences wait for results); you and Arsen read
it; a G2b amendment, if any, is reported there; red copy: not now (C9).

**G6:** stage A passes every integrity check; open: Supplementary Figure 19 numbering (stage B), "D1"
× 2 / "S0" × 36 in the text (s3), alt text under the 19 supplementary legends. Mendeley: Daniil
fixes the 12 items himself (s4, s10); Claude does not touch the Mendeley fields.

---

## 8. Small decisions (answered 2026-11-03)

| # | Question | Decision | Implemented |
|---|---|---|---|
| s1 | Figure 3 missing cells | **black**, as in the first article version | nb02 `NA_CELL_COLOR = "#000000"`, re-rendered |
| s2 | Group letters on figures | OK, **always with the short group name** ("A · PCA variance") | nb02 `GROUP_NAMES` already does; kept as the rule for nb03–nb07 |
| s3 | "D1" / "S0" in the text | OK: S0 only if Table 1 defines it; D1 checked one by one (stage B) | stage B |
| s4 | Empty Mendeley field (Leek 2010) | Daniil checks it; **Claude does not touch Mendeley references** | — |
| s5 | Abstract | stage-B Abstract is a rewrite | stage B |
| s6 | Figure 2A | submitted art | — |
| s7 | Supp. Figure S2 mode counts | not answered → the recommendation stands: automatic counts (`output/wp9/figS2_cohort_modality.tsv`) | stage B |
| s8 | Figure 1E per-cell counts | **off** | nb01 `ANNOTATE_COUNTS = False`, re-rendered |
| s9 | Supplementary File 1 counts | OK | — |
| s10 | 12 bibliography items | Daniil fixes them in Mendeley | — |

---

## 9. G4 answers (third review, 2026-11-07) and what to review next

### 9.1 Answers to the review packages P1–P3

| # | Question | Decision (Daniil, 2026-11-07) | Consequence |
|---|---|---|---|
| P1 | Reworked figures | accepted, except **Figure 6F: "awful and ugly" → redraw it after Daniil's Figma design** (file `FL-harmonization-article`, node 0-1) | nb03 6F redrawn in the Figma layout; G4.2 merges the leaves; Daniil finishes the tree by hand in Figma |
| P2 | Angel and M-ComBat in the gradient | **yes**: they are among the best, so they must be tested under confounding; Daniil runs the pod from the Mac | `rl.GRADIENT_ARMS` 12 → 14 arms; 2 × 45 = 90 new harmonizations + 90 metric jobs (`--skip-if-exists` runs only these); then r13, nb04, r45 re-run. The Methods state that the two arms were added after the main gradient run because the visual check selected them. M-ComBat anchors on `RNASeq_FF_PolyA`, which is one of the 5 gradient batches; like ComBat it takes the diagnosis covariate, so it is expected to fail at λ = 1 |
| G4.1 | Methods of the Figure 6 gradient panel | **only the methods of the 22 selected approaches**: SVA, ComBat, FSMVN, FSQN R, and Angel and M-ComBat once their runs exist. No harmonization, limma, MNN, Harmony, quantile, AMDBNorm and the covariate-free arms stay in Supplementary Figure S17 only | nb04 `KEY_ARMS` = selected methods |
| G4.2 | Empty leaf "RNA-seq + various microarrays" | **merge the two multi-platform leaves for now**; Daniil redraws the tree manually in Figma | `leaf_assignment.tsv` → one leaf "RNA-seq + microarrays" (7 approaches); 6F has 4 leaves; stage-B tree text says the same |
| G4.3 | Title claim | **keep SVA and FSQN R in the title**; Daniil reviews the revised text and may add Angel or ComBat | stage B keeps the title; the Abstract names Angel (FF only, all samples) and ComBat / M-ComBat (multi-platform) as further selected methods |
| G4.4 | Leave-cohort-out reporting | **(a)** "transferred in x of 20 folds (top-3)", the 4 folds where the chosen method failed on the test part counted as no hit and named | r45 key `v1_top3_hits` / `v1_chosen_failed_on_test`; stage B |
| G4.5 | No harmonization rises to the top under confounding | **(a)** one Discussion sentence: above V ≈ 0.4 no harmonization is almost the best approach under the rule; under strong confounding it is better not to harmonize | stage B Discussion; S17e |
| G4.6 | Figure 3 marks | **remove the "submitted version" colour annotation; colour-code and name the row and column clusters as in the original clustermap** (Figma node 403-22). The mark choice (a) / (b) was not answered → the recommendation (a) stands: the 22 selected approaches | nb02 re-rendered |
| G4.7 | Stage-B items and drafts D-1, D-2 | **yes, read and correct** | drafts corrected; stage B written |
| — | Timing | **"I want the final deliverables sooner"** | stage B is written now with the 12-arm gradient; the Angel / M-ComBat numbers are filled in when the pod run is back (r45 keys, no retyping) |

### 9.2 New standing rules from this review

1. **No comparison with the submitted version** in any plot, table or text of the revision
   ("the reader does not care about the earlier, weaker result"). Removed:
   - r22 role "submitted decision tree" (`TREE_METHODS`), its rows in `v1_fold_results.tsv` /
     `v1_summary.tsv`, the r45 keys built on it, its shape / colour in S18a–c;
   - Figure 6F "(submitted tree: MNN + post-removal)";
   - Figure 3 "submitted version" annotation; Figure 6B label "All 87 metrics (submitted)" →
     "All 87 metrics" (the 87-metric bar stays: it is a sensitivity check of the panel, not an
     old result);
   - Table 3 / Figure 6C–D: no kept / lost / new columns against the old picks;
   - response letter and stage-B drafts: no "the submitted tree recommended …" sentences. Where
     a reviewer asks what changed, the letter says what the revised article now reports.
   - Saved: memory `feedback_no_pre_revision_comparison.md`; skills scientific-review, nar-review,
     word-rewrite, notebook_writing.
   - Internal review files (this document, `selection_review.*`, the concordance tables in
     `output/wp4/`) may keep the comparison: they are not publication documents.
2. **Statistical annotations on comparison boxplots.** Pairwise two-sided Mann–Whitney U tests,
   Benjamini–Hochberg FDR within the panel, stars (* < 0.05, ** < 0.01, *** < 0.001, ns). ≤ 4
   boxes → horizontal bars with stars above the boxes; > 4 boxes → a lower-triangle heatmap of
   FDR-adjusted p-values with stars in the cells, beside the boxplot. Saved in the
   `notebook_writing` skill.

### 9.3 Done on 2026-11-07 after the third review

| Item | Result | Files |
|---|---|---|
| Submitted-tree role removed | r22 re-run (roles: chosen, random); r45 drops the concordance keys; S18a–c, 6F, letter, drafts clean | `output/wp7/v1_*.tsv`, `figures_svg/figS18*.pdf` |
| Statistical annotations | S18c: chosen vs random, Mann–Whitney + BH FDR over the 4 panels: batch removal * (FDR 0.012), marker correlation *** (< 0.001), diagnosis retention ns, prediction ns. S14a/b were **not** annotated: they show distributions against a gate line, not a comparison between groups (31 methods would give 465 pairs) — say if you want a p-value heatmap there | `figures_svg/figS18c_v1_regret.pdf`, `output/wp9/nb05_v1_regret_tests.tsv` |
| Figure 6 gradient panel | selected methods only (SVA, ComBat, FSMVN, FSQN R; Angel and M-ComBat after the pod) | `figures_svg/fig6_gradient_panel.pdf` |
| Figure 6F | redrawn in the layout of your Figma panel (taken from the exported submitted Figure 6, `figures_for_article/current_figures_tables_for_article_260915/Figure 6.jpg`; the Figma MCP needs your login and its quota is capped, so it was not used): 5 numbered levels, 4 leaves (multi-platform merged), recommended method + alternatives, imputation of the recommended method, checks box, optional post-removal | `figures_svg/fig6F_decision_tree.pdf` |
| Figure 3 | no submitted-version row; the 22 recommended approaches marked (option a); 4 approach and 5 metric clusters cut from the Ward trees, shaded and named from the data (cross-platform good / poor mixing A, B; same platform / sample type; global, local A / B, missing values, bimodality) as in your original clustermap | `figures_svg/fig3_reduced_panel_clustermap.pdf`, `output/wp9/nb02_fig3_clusters.tsv` |
| Angel / M-ComBat in the gradient | code + RUNBOOK §6.5 pushed (commit `173e11a`); dry-run: 90 harmonizations to run | **needs the pod from the Mac** |
| Letter | every [PENDING] filled with numbers keys (gradient, bridging τ, robustness, leave-cohort-out, leave-strategies-out); no submitted-version comparison | `response_letter_draft.md` |
| **Stage B (tracked manuscript)** | 107 tracked edits on stage A. Words 16,495 → 14,885, lines 1,545 → 1,418, 18 supplementary figures (r90 PASS); r99 0 FAIL; validator ALL PASSED; abstract 188 words; every number from `numbers.json` (584 keys) | `Revised_manuscript/FL_harmonization_article_NARGAB_tracked_stageB_261107.docx`; text source `r50_stage_b_text.py` |

What stage B changed (accept-all view): Abstract rewritten; Methods: strategies A, B, E1–E3
origin, harshness paragraph → one sentence, two new subsections ("Confounding diagnostics and
confounding gradient" with the formal λ definition; "Selection rule and validation" with the
method failures), metric families → reduced panel + four scores; Table 1 + 2 columns (V, % in
single-diagnosis batches); Results: confounding numbers in the composition paragraph, Figure 1E
legend, metric panel and clustermap (old 87-metric cluster paragraphs deleted), selection-rule
results and the visual check (draft D-1, shortened), Table 3 rebuilt (10 rows = scenario ×
method of the 22 approaches, marker correlation, prediction with the unharmonized value, visual
check), Figures 4–5 text neutral (MNN shown as failing the marker threshold), η² on the panel,
Figure 6 legend, new section "Marker correlation, cross-batch prediction and confounding" (gates,
label leakage, robustness, gradient, leave-cohort-out), decision tree (4 scenarios, Angel for FF,
SVA for FFPE / RNA-seq, FSQN R + alternatives for RNA-seq + microarrays); Discussion: real-world
confounding sentence, tempered method claims, limitations with the leave-cohort-out and the
"do not harmonize under strong confounding" finding (G4.5), section retitled "A reduced metric
panel and a written selection rule"; Conclusions rewritten; Supplementary list renumbered S1–S18
with new legends S2, S4–S6, S14, S16–S18.

### 9.4 What to review next

**P4 — done 2026-11-08 (pod run from the Mac):** 90 / 90 harmonization jobs, 85 matrices (the 5 M-ComBat runs at λ = 1 and on the single-diagnosis control failed with "covariate confounded with batch", as expected, like ComBat with the covariate), 85 / 85 metric jobs ok; logs in S3 `pod_logs/fl-revision-c6a-12xlarge_261107_2024/`. Remaining on JupyterHub: r12 --concat, r13, nb04, r45, `r50 --stage B`. Original instructions:

**P4 — Mac + pod: Angel and M-ComBat in the gradient (≈ 15 min of your time, ≈ 2–3 h pod).**
`git pull` on the Mac → `RUNBOOK.md` §6.5 → tell me "the gradient pod is done". I then collect,
re-run r13 / nb04 / r45 and `r50 --stage B` (the numbers fill themselves).

**P5 — figures. Answered by Daniil 2026-11-08:**

| Figure | Daniil's answer | Consequence |
|---|---|---|
| `fig3_reduced_panel_clustermap.pdf` | Cluster names OK. The metric-group palette must be the pastel one of his notebooks and the Figma Figure 3 ([node 403-22](https://www.figma.com/design/t8bFgusleBEwB9ht7rORCH/FL-harmonization-article?node-id=403-22)); the column side colours must include Post-removal and Harshness, as in Figma | **Done 2026-11-08** (nb02): metric groups use the pastel Set3 `group_pal` over the letters A–K of the submitted notebook (`Finally_assembled_figures_for_article.ipynb` cell 4); new column bars Post-removal (`post_rm_pal`, light / dark grey) and Harshness (per method: `HARSHNESS_LEVEL_MAP` + `HARSHNESS_PAL`, green / orange / red, same cell). Clusters and the 22 marks unchanged. **Check:** that notebook also has a per-strategy `harshness_pal`; if the Figma bar was per strategy, say so and I switch |
| Strategy names in every figure and in the text | **Keep the code next to every strategy name** ("S0 · No removal", "D · Malignant only"). In the article text, give code + name together at the start of Methods and Results, then use **only the codes** (readers learn the notation and space is saved) | **Planned, not done yet** (§10.6, item A): it reverses hard rule 3 of `CLAUDE.md` for strategy codes and decision s3, and touches every figure and the stage-B text. Waits for your approval of §10.6 |
| `fig6F_decision_tree.pdf` | "It's better, I approve" | closed |
| `fig6_gradient_panel.pdf` | "Beautiful, OK" | closed (re-drawn 2026-11-08 with Angel and M-ComBat, same style) |
| `figS18c_v1_regret.pdf` | "Nice plot" | closed |
| `figS16a/b` | no comment | as is; the strategy-code rule above also applies to their pool names |

**P6 — the tracked manuscript.** Daniil (2026-11-08): he reviews the text **once, at the end**,
after every automatic step is done, and writes his comments as **Word comments in the docx**;
Claude reads them from there. Consequence: no text review before that. B1–B5 were answered inline on 2026-11-08 (table below). The docx to comment is the newest
`Revised_manuscript/FL_harmonization_article_NARGAB_tracked_stageB_<tag>.docx` (now
`…_261108.docx`; a new tag after the strategy-code change, §10.6).
Decisions inside it:

| # | Question | Options (recommendation first) |
|---|---|---|
| B1 | **Figures 4 and 5 (decision D5)** still show MNN, FSMVN and AMDBNorm next to SVA; the recommended Angel, FSQN R and ComBat approaches have no main-figure panel. | (a) keep the art, text neutral (as now: MNN shown as failing the marker threshold); (b) replace panels with the nb07 raw / harmonized pairs of the recommended approaches (FF Angel, multi-platform FSQN R / ComBat), same figure count | **Answered 2026-11-08: (b), now** ("do not wait for my review of the text") → new notebook `nb08_figures_4_5.ipynb`, Results text and legends of Figures 4–5 rewritten (§11)
| B2 | **Title claim on SVA.** The gradient shows that SVA's cross-batch prediction depends on the diagnosis covariate (0.75 with, 0.30 without on balanced designs); the text says so. FSQN R loses diagnosis retention under strong confounding. | (a) keep the title (your G4.3 answer) with these caveats in the text; (b) soften "top-performing" in the title | **Answered 2026-11-08: (a) keep the title**
| B3 | **Alternative text under the 18 supplementary legends** (r99 review item). The word budget allows it (1,610 words below the submitted text). | (a) add one alt-text line per legend; (b) put alt text only in the supplementary PDF | **Answered 2026-11-08: (b)** → `r46` writes one alt-text line under every supplementary figure in the review PDF; none in the manuscript
| B4 | Paragraphs deleted to keep the text focused: method harshness (→ one sentence), metric polarity (Results), the 87-metric cluster description, the old biomarker / prediction "clustermap best vs rest" section, the clustermap-selection and metric-orthogonality Discussion paragraphs. | accept, or name any to restore | **Answered 2026-11-08: accepted for now**; Daniil re-checks them in the tracked docx
| B5 | The frozen rule's reporting section asks for the concordance with the submitted Table 3; by your G4 rule it stays in the internal review files only, not in the article or letter. | confirm | **Confirmed 2026-11-08**

Then G5 (letter, with Arsen) and G6 (final checks). Independent: the 12 Mendeley items
(`output/wp12/reference_audit.tsv`).

## 10. Review package 2026-11-08 (after the Angel / M-ComBat gradient run)

*Restored 2026-11-08: this section was lost when the document was saved over on the Mac; its text
is the version written on JupyterHub the same day, with §10.6 extended by Daniil's new P5 / P6
answers.*

### 10.1 What was done

The pod added Angel and M-ComBat (reference batch "RNA-seq FF poly-A") as arms 13 and 14 of the
confounding gradient: the same 45 designs (33 capped = 11 λ levels × 3 replicates, 11 uncapped,
1 single-diagnosis control with 2,068 samples), 90 new harmonizations → **630 runs, 619 with
scores, 11 failed** (ComBat and M-ComBat with the diagnosis covariate at λ = 1 × 3 replicates
+ uncapped + single-diagnosis control: "the diagnosis covariate is identical to the batch";
AMDBNorm 6 h timeout on the single-diagnosis control). On JupyterHub: `r12 --concat` → `r13` →
nb04 (now 14 arms; its hard-coded "540 runs" check replaced by 45 × number of arms) → nb03 →
`r40` → `r45` (661 numbers, 0 pending; 5 new M-ComBat keys) → `r50 --stage B` → r90 / r99 /
validator → letter draft; nb02 re-drawn for the P5 comment; new `r46_review_figure_pdfs.py`
builds the review PDFs.

### 10.2 Files (the package)

| File | What it holds |
|---|---|
| `Revised_manuscript/FL_harmonization_article_NARGAB_tracked_stageB_261108.docx` | **main result**: tracked manuscript (107 tracked edits on stage A; Reject All = submitted text). Supersedes `…stageB_261107.docx` |
| `Revised_manuscript/NARGAB-2026-312_response_to_reviewers_261108_DRAFT.docx` | letter draft (yellow = 16 `[LINES]` markers, filled after the manuscript and its line numbers are final) |
| `Revised_manuscript/review_package_261108/Revised main-figure panels (review draft) 261108.pdf` | 7 revised main-figure panels (1E, 2A, 3, 6B, 6C/D, 6 gradient, 6F), one per page after a title page; Figures 4–5 unchanged |
| `Revised_manuscript/review_package_261108/Supplementary Figures S1-S18 (review draft) 261108.pdf` | all 18 supplementary figures in the **new numbering** (unchanged ones = the submitted pages; new / rebuilt = revision panels; 10.8 MB); bookmarks per figure |
| `Revised_manuscript/review_package_261108/figure_sources.tsv` | which file / submitted page is behind every figure |
| `output/wp10/Supplementary File 1.csv`, `Supplementary File 2.xlsx`, `Supplementary File 3.xlsx` | supplementary files; File 3 sheets: main benchmark 2,407, confounding gradient **630** (was 540), leave-cohort-out 1,202 |
| `output/numbers.json` | every number in the text (661 keys); new: `gradient_mcombat_*` |
| `output/wp14/verify_report.md` | r99 report (0 FAIL; review items in §10.6) |
| `figures_svg/PLACEMENT.md` | file → panel map for the Figma assembly |

Plain words for the columns used below: *rank* = position under the frozen selection rule among
the 14 arms of one design (1 = best); *both gates* = marker correlation ≥ 0.7 and prediction not
worse than no harmonization − 0.05 and above its permutation null; *changes with confounding* =
Spearman ρ with V at FDR < 0.05 **and** change λ 0 → 1 > 2 × replicate SD.

### 10.3 Results

*Daniil 2026-11-08: every finding below "ok".*

| Finding | Evidence (`output/wp6/gradient_slopes.tsv`, `gradient_ranks.tsv`) |
|---|---|
| Angel behaves like the batch-removing methods: prediction and global diagnosis retention fall with confounding | N 0.90 → 0.35*, global diagnosis retention 0.46 → 0.28* (ρ −0.98, FDR < 0.001); batch removal stable 0.47 → 0.44; both gates in 58 % of capped runs
| **M-ComBat reads the batch as diagnosis** as confounding grows (same mechanism as SVA / ComBat with the covariate) | diagnosis retention 0.78 → 0.99 at λ = 0.9 (ρ +0.85, FDR < 0.001), batch removal 0.50 → 0.30 (ρ −0.99); fails at λ = 1
| Under the rule, M-ComBat ranks first from λ = 0.5 on, ahead of no harmonization | median rank M-ComBat 1 at λ = 0.5–0.9; no harmonization 9 of 14 at λ = 0 → 3 at λ = 0.5–0.6 (was 7 → 1 with 12 arms); both gates in 97 % of M-ComBat runs
| Overall counts with 14 arms | trends tested 66 → 78, changing by both criteria 30 → 34; runs passing both gates 64 % at λ = 0, 26–29 % at λ = 0.5–0.9, 42 % at λ = 1
| Text changes caused by this (r50 stage B + letter) | Results gradient paragraph: "rose to the top" → "rose towards the top (… 9 of 14 …), behind M-ComBat (median rank 1 at λ = 0.5–0.9)"; M-ComBat added to the "batch read as diagnosis" result and to the "could not run at λ = 1" result; Methods: 14 arms listed. r90 PASS (16,495 → 14,913 words, 1,545 → 1,420 lines, 18 supplementary figures); r99 0 FAIL; validator ALL PASSED; 88 tests pass; frozen MD5s match |
| Opposite case, for reference | had M-ComBat behaved like Angel (diagnosis retention falling), the "unharmonized data reach the top" sentence would have stood unchanged

### 10.4 Message for the paper

With confounding, methods that model the diagnosis (SVA, ComBat, M-ComBat) score better on
diagnosis retention because they keep the batch; methods that remove the batch (FSQN R, FSMVN,
Angel) lose the diagnosis. Neither is safe above the real-data confounding level. Figures:
`fig6_gradient_panel.pdf`, `figS17a`–`f` (Supplementary Figure 17 in the S1–S18 review PDF).

### 10.5 Decisions recorded on 2026-11-08

| Decision (Daniil) | Consequence |
|---|---|
| Figure 3: pastel metric-group palette + Post-removal / Harshness bars | done (§9.4 P5) |
| Strategy codes next to the names in figures; codes in the text after a first joint definition | reverses `CLAUDE.md` hard rule 3 and decision s3 **for strategy codes only** (WP / D / G codes, snake_case names stay forbidden); implementation in §10.6 A after approval |
| 6F, gradient panel, S18c approved | closed |
| Text reviewed once, at the end, as Word comments | Claude collects the comments from the docx; B1–B5 nevertheless answered inline on 2026-11-08 (§9.4) |

### 10.6 What to review next

**A — strategy codes (needs your "go", ≈ 1–2 h of my work, nothing for you to do except approve):**
1. `revision_lib.STRATEGY_DISPLAY_NAMES` → "code · name" for figures ("S0 · All samples", "A · Confirmed bad batches removed", …, "E1 · Iterative removal, round 1", "K · FFPE only"), as the metric groups already are ("A · PCA variance"); a second dictionary `STRATEGY_CODES` (S0, A, B, C, D, E1–E3, F–K) for the text. Question: S0's plain name is "All samples" in the revision but "no removal" in your comment — **which name do you want next to S0?** **Answered 2026-11-08: go; S0 = "No removal"** (the name of the submitted manuscript) → "S0 · No removal".
2. Re-run every figure notebook that labels strategies (nb01, nb02, nb03, nb04, nb05, nb07) and `r40` (Supplementary File 3 strategy column: "code · name"). **Approved 2026-11-08.**
3. Stage B text (`r50_stage_b_text.py`): Methods first paragraph on the strategies and the first Results paragraph give "name (code)"; afterwards only the code. Table 1 and Table 3 carry the code column. Then r50 → `…_stageB_<new tag>.docx`. **Approved 2026-11-08.**
4. `r99_verify.py`: drop `S0` from the label scan (the 36 "S0" hits become intended); `CLAUDE.md` hard rule 3, memory `feedback_no_internal_labels.md` and the plan §1.1 record the exception. **Approved 2026-11-08.**
5. Re-run r90 (the word count should fall), r99, the validator, r46 (review PDFs). **Approved 2026-11-08.**

**Q1 — M-ComBat in the "do not harmonize under strong confounding" sentence.** M-ComBat now outranks no harmonization above V ≈ 0.4, but only because the covariate keeps the batch. (a) keep the sentence with the clause "behind M-ComBat" as written now (recommended; the mechanism sentence before it explains it); (b) state explicitly "M-ComBat's rank reflects the covariate, not batch removal"; (c) drop M-ComBat from the rank sentence. Files: `figS17e_gradient_rank_trajectories.pdf`; Results paragraph "The confounding gradient … gave four results". **Answered 2026-11-08: (b)** ("I like more explanations and discussions") → explicit mechanism sentence in the Results and the Discussion.

**Q2 — the effect-size criterion for arms that fail at λ = 1.** ComBat and M-ComBat have no λ = 1 value, so "changes with confounding" is always *no* for them even when Spearman is strong (M-ComBat N ρ −0.91, FDR < 0.001). (a) use λ = 0.9 as their end point (recommended; the count 34 / 78 would rise); (b) keep as is and say so in the S17 legend. **Answered 2026-11-08: (a)** → r13 end point = last λ with a value.

**Harshness bar of Figure 3:** per method (as drawn) or per strategy (if that was the Figma bar)? **Answered 2026-11-08: per method** (as drawn) — closed.

**Then (your single text pass, P6):** after A, Q1, Q2 are applied, open the newest stage-B docx and the two review PDFs; write every comment as a Word comment (B1–B5 already answered, §9.4). Then G5 (letter, with Arsen), G6 (final checks; r99 review items: alt text under the 18 supplementary legends = B3, 2 label groups). Independent: the 12 Mendeley items (`output/wp12/reference_audit.tsv`) **Daniil 2026-11-08:** after all remaining edits, list every file for the final review as Tier 1 (submission materials: text, figures, supplementary materials) and Tier 2 (repository notebooks and files behind them, not submitted) → §11.4.

**Daniil, 2026-11-08 (added after §10.6; recorded here in place of the comment):** in
`nb02_reduced_panel_clustermap.ipynb`, draw the Spearman cross-correlation clustermap of all 87
scoring metrics with the 22 selected metrics starred, and use it to replace
`figS5_metric_correlation_clusters`. Goal: show that the 22 metrics are the correlation-cluster
centres (medoids) of the 87, as in the submitted Supplementary Figure 7 (Figma node 401-3) plus a
colour bar "in the final 22", with the metric colours of the new Figure 3 (metric group, score
bar, annotation column). → **Done 2026-11-08, §11.3.**

## 11. Fourth review package 2026-11-08 (§10.6 approved, B1–B5 answered, new S5)

### 11.1 What was done

Every answer of §9.4 / §10.6 and the S5 request was implemented on JupyterHub the same day:

| Decision | Implementation |
|---|---|
| A: strategy codes ("S0 · No removal") | `revision_lib.STRATEGY_DISPLAY_NAMES` = "code · name" (+ `STRATEGY_CODES`, `STRATEGY_PLAIN_NAMES`, new test); nb01–nb05, nb08 and r40 re-run (nb07 not: the visual check is closed, its round-2 selection is empty, and its plots are internal review material); text: Methods names the codes once (Table 1, "S0, no removal; A–K"), the first Results paragraph gives "name, code" for all 14 strategies, then codes (S0, C, J, K, D, I …); Table 1 / Table 3 already carry the codes; r99 no longer scans S0; `CLAUDE.md` rule 3, plan §1.1 and memory record the exception |
| Q1 (b) | Results gradient paragraph: "M-ComBat's first rank does not mean that it removed the batch …"; Discussion limitations: "A high rank of a covariate method under strong confounding should therefore be read as a warning sign, not as a recommendation"; letter the same |
| Q2 (a) | r13: end point = last λ with a value (`end_lambda` = 0.9 for ComBat / M-ComBat); Methods, S17 legend and letter say so |
| B1 (b) | new `nb08_figures_4_5.ipynb` (embeddings from `cache/nb07`, no new compute) → Figures 4 and 5 rebuilt; Results paragraphs, legends and alt text of both rewritten; Supplementary Figures 7–13 cited in one sentence; their legends now name methods in plain words (`10_mnn` → MNN …) |
| B2 / B4 / B5 | no change (title kept; deletions accepted for now; concordance internal only) |
| B3 (b) | `r46`: one alt-text line under every supplementary figure title in the review PDF; r99 records the decision (PASS) |
| Harshness per method | closed |
| S5 request | nb02 §4 rewritten: 87-metric clustermap + medoid table (§11.3) |

Then r45 (numbers 661 → 717 keys) → `r50 --stage B` (same tag 261108, overwrites the uncommented
docx) → r90 / r99 / validator → r60 letter draft → r46 review PDFs. Tests 89 pass; frozen MD5s match.

### 11.2 Files

| File | What it holds |
|---|---|
| `Revised_manuscript/FL_harmonization_article_NARGAB_tracked_stageB_261108.docx` | **main result**: tracked manuscript, 108 tracked edits on stage A |
| `figures_svg/fig4{A–D}_*.pdf`, `fig5{A–C}_*.pdf` | new Figures 4 and 5 (one file per panel) |
| `output/wp9/nb08_figure_4_5_panels.tsv` | per panel: samples, genes used, marker correlation, prediction (gate value; DLBCL vs FL for D), first-PC variance before / after |
| `figures_svg/figS5_metric_correlation_clusters.pdf` | new Supplementary Figure 5 (87 metrics) |
| `output/wp9/nb02_figS5_87_metric_clusters.tsv` | per metric: cluster at \|ρ\| ≥ 0.8, cluster size, `in_panel`, `is_medoid`, medoid, mean \|ρ\| to the cluster (own vs medoid) |
| `output/wp6/gradient_slopes.tsv` | + column `end_lambda` (end point of the effect-size criterion) |
| `Revised_manuscript/review_package_261108/*.pdf` | rebuilt: main panels now with Figures 4–5; supplementary PDF with alt text |

### 11.3 Results

| Finding | Evidence |
|---|---|
| Strategy notation is consistent | every figure / table label "code · name"; text "name, code" in the first Results paragraph, codes afterwards |
| Q2 changes the trend count | method × score trends changing by both criteria **34 → 43** of 78 (ComBat and M-ComBat now evaluated to λ = 0.9: e.g. M-ComBat batch removal −0.20, ρ −0.98) |
| Figure 4: the single-type recommendations mix batches of the same diagnosis | S0 unharmonized: PC1 81 %, one tSNE cluster per batch; J Angel: PC1 69 % → 8 %, DLBCL / FL / normal B as three clouds on PCA, prediction 0.67 → 0.79, marker correlation 0.95 (Angel's embedding uses 345 genes without missing values); K SVA: DLBCL batches merge on tSNE, prediction 0.50 → 0.88, marker correlation 0.71; C SVA: FF poly-A and FFPE exome capture mix, 0.74 → 0.75, 0.82 |
| Figure 5: multi-platform recommendations | D FSQN R: PC1 80 % → 22 %, the two large DLBCL batches merge on tSNE, Affymetrix batches stay apart, DLBCL-vs-FL 0.62 → 0.65, marker correlation 1.00; D ComBat: FL / DLBCL apart on PCA, 0.74 → 0.80; I M-ComBat: PC1 still 50 %, diagnoses as groups of batches (its covariate keeps the batch) |
| S5: the 22 are cluster centres **in part** | 87 metrics → 48 clusters at \|ρ\| ≥ 0.8; the 22 panel metrics fall into 22 of them; **15 of 22 are the medoid (or alone)**; the other 7 sit next to a platform or major-group variant that the panel rule excluded by design, ≤ 0.01 below its mean \|ρ\|; 26 clusters hold no panel metric — 24 are cohort / RNA-seq source / platform / tumour-normal variants, 2 hold batch metrics (tSNE centroid dispersion, excluded because tSNE does not preserve distances; KS mean D on batch, which joined the PC-regression cluster in the 33-metric universe of the rule) |
| Manuscript checks | r90 PASS: words 16,495 → 14,593, lines 1,545 → 1,384, 6 figures, 3 tables, 18 supplementary figures; r99 0 FAIL (review: "D1" × 2, pre-existing); validator ALL PASSED; abstract 188 words |

Opposite case, for reference: had a panel metric sat in a cluster with a *batch* medoid outside the
panel, the "medoid" claim of the Methods would have needed a correction; it does not (the
non-medoid cases are all platform / 3-class variants).

### 11.4 Files for the final review (Daniil 2026-11-08)

Paths relative to `article_1_revision/` unless they start with `../`. Repository files only.

**Tier 1 — the revision submission materials**

| What | File |
|---|---|
| Manuscript (tracked) | `Revised_manuscript/FL_harmonization_article_NARGAB_tracked_stageB_261108.docx` |
| Response letter (draft; 16 `[LINES]` markers wait for final line numbers) | `Revised_manuscript/NARGAB-2026-312_response_to_reviewers_261108_DRAFT.docx` |
| Main figures, revised panels (review PDF) | `Revised_manuscript/review_package_261108/Revised main-figure panels (review draft) 261108.pdf` |
| Main figures, panel files for the Figma assembly | `figures_svg/fig1E_confounding.pdf`, `fig2A_strategy_sankey.pdf`, `fig3_reduced_panel_clustermap.pdf`, `fig4A_unharmonized_no_removal.pdf`, `fig4B_ff_only_angel.pdf`, `fig4C_ffpe_only_sva.pdf`, `fig4D_rnaseq_only_sva.pdf`, `fig5A_malignant_only_fsqn_r.pdf`, `fig5B_malignant_only_combat.pdf`, `fig5C_rare_batches_removed_mcombat.pdf`, `fig6B_eta_squared.pdf`, `fig6CD_four_scores.pdf`, `fig6_gradient_panel.pdf`, `fig6F_decision_tree.pdf` (+ `.svg` / `.png`); unchanged panels of Figures 1, 2 and 6 from `../figures_for_article/current_figures_tables_for_article_260915/` |
| Supplementary figures S1–S18 (review PDF, with alt text) | `Revised_manuscript/review_package_261108/Supplementary Figures S1-S18 (review draft) 261108.pdf` |
| Supplementary figure panel files | `figures_svg/figS2_merged_distributions.pdf`, `figS4_metric_availability.pdf`, `figS5_metric_correlation_clusters.pdf`, `figS6_approach_correlation.pdf`, `figS14a/b/c_*.pdf`, `figS16a/b_*.pdf`, `figS17a–f_*.pdf`, `figS18a/b/c_*.pdf`; unchanged S1, S3, S7–S13, S15 = pages of `../figures_for_article/supplementary_260824/Supplementary Figures S1-S19.pdf` |
| Supplementary files 1–3 | `output/wp10/Supplementary File 1.csv`, `output/wp10/Supplementary File 2.xlsx`, `output/wp10/Supplementary File 3.xlsx` |
| Assembly maps | `figures_svg/PLACEMENT.md`, `Revised_manuscript/review_package_261108/figure_sources.tsv` |

**Tier 2 — repository files behind them (not submitted)**

| What | File |
|---|---|
| Figure notebooks | `nb01_confounding.ipynb` (1E, 2A), `nb02_reduced_panel_clustermap.ipynb` (3, S4–S6), `nb03_four_scores_and_tree.ipynb` (6B, 6C/D, 6F, S14), `nb04_confounding_gradient.ipynb` (6 gradient, S17), `nb05_robustness_and_v1.ipynb` (S16, S18), `nb06_merged_distributions.ipynb` (S2), `nb07_selected_approaches_embeddings.ipynb` (visual check, embedding cache), `nb08_figures_4_5.ipynb` (4, 5) |
| Text sources | `r50_stage_b_text.py` (every new paragraph), `r50_manuscript_tracked_edits.py`, `response_letter_draft.md`, `r60_response_letter.py` |
| Numbers in the text | `output/numbers.json` (652 keys since 2026-11-08: fold-change keys dropped, S18 test keys added) by `r45_results_numbers.py` |
| Analysis scripts | `revision_lib.py`, `r01`–`r05`, `r13_gradient_stats.py`, `r22_v1_evaluate.py`, `r40_build_supplementary.py`, `r46_review_figure_pdfs.py` |
| Selection rule and decisions | `adjudication_rule_261029.md` (frozen), `output/wp4/selection_after_visual_check.tsv`, `output/wp4/visual_check.tsv`, `output/wp4/leaf_assignment.tsv` |
| Key result tables | `output/wp2/reduced_panel.tsv`, `output/wp3/four_scores.parquet`, `output/wp6/gradient_slopes.tsv`, `output/wp6/gradient_ranks.tsv`, `output/wp7/v1_fold_results.tsv`, `output/wp9/nb08_figure_4_5_panels.tsv`, `output/wp9/nb02_figS5_87_metric_clusters.tsv` |
| Checks | `output/wp14/verify_report.md` (r99), `output/wp14/ledger_FL_harmonization_article_NARGAB_tracked_stageB_261108.tsv` (r90), `output/wp14/figure_consistency.tsv` (r98), `output/wp14/consistency_review_agent.md`, `brainstorm/figure_peer_review_brainstorm_261108.md` |
| Review extras (2026-11-08, not submitted) | `figures_svg/figS2_merged_distributions_all_cohorts.pdf` (D3), `review_extras/approach_distributions/`, `review_extras/final_selection_embeddings/`, `output/wp9/figma_page_slots_261108.tsv` |
| Review record and plan | `gates_review_261102.md` (this file), `article_1_revision_implementation_plan_261029.md` |

### 11.5 What to review next

1. **Your single text pass (P6), ≈ 2–3 h:** open the stage-B docx and the two review PDFs; write
   every remark as a Word comment (Figures 4–5 text and legends, the strategy-code wording, the
   S5 sentence and the Q1 sentences are new). I collect the comments from the docx.
2. **Figma assembly, ≈ 1 h:** Figures 4 and 5 now come as 7 panel files (`PLACEMENT.md`); the
   submitted dendrogram panels are gone.
3. **G5 letter (with Arsen)** after the text pass; the 16 `[LINES]` markers fill from the final
   line numbers.
4. **G6 final checks**; independent: the 12 Mendeley items (`output/wp12/reference_audit.tsv`).


## 12. Figure-notebook review 2026-11-08 (`daniil_review_261108.md`)

Daniil reviewed nb02–nb07 and wrote his requests into `daniil_review_261108.md` (his file is
kept as written). Every question is answered below with the numbers read from the tables; every
request is a step of the plan `figure_review_corrections_plan_261108.md` (item numbers in
brackets). Nothing is implemented yet.

### 12.1 Answers to the questions

| Request / question | Answer (evidence) | Plan |
|---|---|---|
| nb02: S5 = 87-metric clustermap, 22 starred, Figure 3 colours | done 2026-11-08 (§11.3); "the new Supplementary Figure 6 is ok" | — |
| General: palettes, notations, names and conventions universal across all figures; one reviewer agent + `/brainstorm` with three peer-reviewer agents | planned after the per-notebook fixes, so the reviewers see the corrected figures: a deterministic audit script (palettes key by key against the canonical copies, figure text against the publication names), one reviewer agent, then the brainstorm (sympathetic reviewer, hostile reviewer, handling editor). Mechanical findings fixed directly, content findings listed for you (D5) | [14] |
| Pareto front clearly defined, explained and justified | today the text says only "a Pareto front of batch removal and diagnosis retention". New Methods wording (rewrite, no new paragraph): an approach is on the front when no other candidate of its scenario is at least as good on both axes and better on one; used because the two axes conflict (more batch removed → less diagnosis kept, gradient panel), a weighted sum would need a weight no data justify, and the front returns every best trade-off instead of one winner; front members ordered by local batch mixing. Short definition also at the first Results mention and in the letter | [9a, 9b, 11] |
| nb03: FSQN R and FSMVN in D have macro-F1 ≈ 0.5 — why, and why did they enter? | Figure 6C/D shows the **3-class** score (FSQN R 0.556, FSMVN 0.534), but D is malignant-only and its gate uses **DLBCL vs FL** (decision 2026-11-03): FSQN R 0.645, FSMVN 0.651, permutation null 0.470 / 0.472 (p = 0.0099). **Without harmonization** (D, KNN) the same score is 0.622 → not worse, slightly better (+0.02 / +0.03). They are on the front because they have the highest batch removal of D (axis mean 0.500 vs ComBat 0.437 / 0.440; global batch scaled 0.998 / 1.000) at a lower diagnosis retention (0.408 / 0.394 vs 0.456): the batch end of D's front, ComBat is the diagnosis end. Fix: the prediction column shows the gate value, with an open marker for the unharmonized value (D4) | [4a] |
| nb03: the local-batch panel has no λ = 0 median line | it is there but hidden: the median of local batch mixing (scaled) over all gradient arms is **0.029 at λ = 0 and 0.029 at λ = 1** (kBET accepts almost no neighbourhood in most arms even with balanced batches), so the λ = 1 line is drawn on top of the λ = 0 line. Fix: two line styles that show both colours when they coincide + the note "medians coincide" | [4b] |
| nb04: S17a "agreement with batch-free fold changes, DLBCL vs FL" — a new metric? | yes: the Spearman ρ between the fold change computed on the harmonized gradient design and the reference fold change computed inside each batch of the unharmonized data. It is in S17a (two panels), Supplementary File 2 (definition row) and the gradient statistics (4 rows per method in the FDR family); not in the text and not in the "43 of 78" trend count. Removed from all three; since it leaves the FDR family, r13 is re-run and the trend count re-read (it may move) | [1, 3, 5a] |
| nb04: how the "confidence intervals" of the gradient points were defined | they are not confidence intervals: each band is **mean ± SD over the 3 replicate draws** of the design at that λ (capped designs, `SPREAD = "sd"`). The only CIs are the OLS 95 % CIs of the slopes (S17b) and the Spearman CIs. The Methods, the S17 legend and the figure legend will say so | [5d, 9c, 9d] |
| nb04: S17e left half bands messy | removed; both halves show medians only and differ only in the set of methods | [5b] |
| nb04: S17a vs S17f — what differs, why both | S17a = all 14 methods on every score with the uncapped and single-diagnosis controls (where the selected methods sit among all); S17f = only the methods of the final selection, without controls, on a scale where their differences are visible (how the selected methods compare with each other). One Results sentence + the legend | [9c] |
| nb04: S17c messy, no `strat_pal`, labels overlap | my error: the dots were grey although the standard palettes are the rule. Fix: `strat_pal` colours, code labels (S0, A … K) placed without overlap, with a check | [5c] |
| nb05: S16a bars faint; S16b flatter, thinner bars | bars at 25 % opacity under full-colour dots (+ SD error bar over the six scenarios); S16b half height, bar height 0.35, shared x axis | [6a, 6b] |
| nb05: panels must fill their full figure page (Figma 761-28) | panel sizes will come from a slot table (`PLACEMENT.md`, width × height in mm per panel). read from Figma after your login (D2 answered: "read from Figma") | [13, D2] |
| nb05: S18a scatter → bar plot, random as grey bars ± SD, failed / not evaluable as vertical text | yes. The random method's rank on a fold with n test runs is uniform on 1…n: mean (n + 1)/2, SD √((n² − 1)/12), and P(random ≤ observed) = observed rank / n exactly; per scenario a Monte Carlo of 100,000 draws gives the empirical p of the summed ranks, BH-FDR over the 4 scenarios | [6c, 6d] |
| nb05: S18b with the spread of the random data and significance | grey bar = expected random hit share ± SD (Poisson-binomial over the folds); exact empirical p = P(random hits ≥ observed hits); BH-FDR over 5 groups × 2 panels | [6e] |
| nb05: always error bars on bar plots; empirical p / FDR or Mann–Whitney vs expected | applied to S16a, S18a–c; recorded as a standing rule for the figure notebooks | [6, 16] |
| nb05: S18c — say whether "diagnosis retention" and "batch removal" are global or local; "batch removal" confused with the strategies | both are means of a global and a local bar. Proposed names everywhere (D1): "Batch mixing (global + local mean)", "Diagnosis retention (global + local mean)"; the other two panels named "marker correlation (local, within cohort)" and "cross-batch prediction". S18c random = the decreases (formerly "regret") of every test run (a distribution, not one expected value), bars ± SD, Mann–Whitney + Monte Carlo p, BH-FDR | [2b, 6f, 9g] |
| nb06: full S2 for all cohorts, two large columns × three modes | the per-cohort histograms of all cohorts are already cached, no S3 needed; new figure `figS2_merged_distributions_all_cohorts`. Whether it replaces the 30-cohort S2 → D3 | [7a, D3] |
| nb06: before / after distributions for each of the 22 approaches, for your interest | new internal section (streams 22 harmonized + ≈ 12 unharmonized matrices, ≈ 30–40 min, cached) → `review_extras/approach_distributions/` (one page per approach + one merged PDF); not part of the article | [7b] |
| nb07: SVA in FFPE only and RNA-seq only are missing | they are drawn, in the round-1 PDFs: `figures_svg/g2b_review/ffpe_only_{pca,umap,tsne}.pdf` (SVA = front rank 1) and `rnaseq_only_*.pdf` (SVA KNN / softImpute = ranks 4–5). The notebook was last saved in round 2, whose selection is empty after the visual check closed, so its inline output shows nothing; inline it only ever showed the first page of each PDF | [8c] |
| nb07: where are the final PCA / UMAP / tSNE plots of the best approaches only? | they do not exist yet as one set. New mode `REVIEW_ROUND = "final"`: the 22 accepted approaches, unharmonized \| harmonized, by batch / diagnosis / platform, from the embedding cache (all 22 are cached, no new compute) → `review_extras/final_selection_embeddings/` | [8a, 8b] |

### 12.2 Decisions (answered 2026-11-08)

| # | Question | Decision (2026-11-08) | Consequence |
|---|---|---|---|
| D1 | Rename the two combined axes in every publication output (S17d, S18c, Methods, Table 3 legend, letter): "Batch mixing (global + local mean)" and "Diagnosis retention (global + local mean)"? The frozen rule file keeps its words | **Rename everywhere** | plan items 2b, 3, 6f, 9g, 11, 12; the frozen rule keeps "batch removal" |
| D2 | Page size the panels must fill (Figma node 761-28) | **Read it from Figma; Claude says when to log in** | first step of Phase 2: I start the Figma login and ask you to log in (on the pod you paste the address-bar URL back to me); one read of node 761-28 in file `t8bFgusleBEwB9ht7rORCH` (≤ 3 calls) → `output/wp9/figma_page_slots_261108.tsv` → slot column of `PLACEMENT.md` (plan item 13) |
| D3 | Full S2 (all cohorts): replace the 30-cohort S2 in the supplement, or internal only? | **Draw it; you look and decide** | plan item 7a draws `figS2_merged_distributions_all_cohorts`; PLACEMENT / r46 / S2 legend unchanged until your word (question in §12.5) |
| D4 | Figure 6C/D prediction column = gate value (DLBCL vs FL for D) + open marker for the unharmonized value? | **Ok** | plan items 4a, 9f |
| D5 | Agent-review findings that change content (drop / merge a panel, change a plot type): apply only after your word? | **Yes**; mechanical fixes (palette, label, overlap, size) applied directly | plan item 14d; content findings listed in §12.4 |
| Tag | New date tag for the stage-B docx? | You have not commented on `…_stageB_261108.docx`; you will edit **the most recent** docx after the edits of this plan | the rebuild uses the implementation date as tag (same day → the 261108 file is overwritten); your single Word pass (§11.5 item 1) comes after this plan |

Further requests written into the plan the same day (2026-11-08):

| Request | Consequence |
|---|---|
| Describe every new statistical test and methodology change in the Methods | plan item 9h: exact random-rank p, Monte Carlo of the summed ranks, Poisson-binomial hit test, decrease test (Mann–Whitney + Monte Carlo), each BH-FDR family, SD error bars, gradient bands / slope CIs, Pareto definition, gate value in 6C/D — rewritten into the existing Methods paragraphs (nothing grows) |
| Rename "regret" → **"decrease"** in every leave-cohort-out plot ("regret is emotional, decrease is technical") | S18c titles / axis / legend, the S18 legend, the Results sentence that describes it, r46 alt text, PLACEMENT; internal names (`regret` column, file names, numbers.json keys) stay (plan items 2b, 6f, 9e, 9g, 12, 13b) |
| Pareto citation: add the DOI to the text; **standing rule: every new citation is written as a DOI** for Mendeley | Deb, Pratap, Agarwal, Meyarivan 2002, NSGA-II, *IEEE Trans Evol Comput*, **DOI 10.1109/4235.996017** (checked on Crossref; Deb 2001 is a book without DOI) — Methods (plan item 9a) and letter (item 11); rule saved in memory and in the CLAUDE.md gotchas |

### 12.3 What to review next

1. **Approve the corrected plan** `figure_review_corrections_plan_261108.md` (TODO at its end),
   ≈ 10 min. D1–D5 are answered.
2. **Figma login, ≈ 2 min**, when I ask at the start of Phase 2 (D2).
3. After the implementation: the digest §12.4–12.5 (consistency-review findings, new S16–S18,
   trend count after the fold-change metric leaves the FDR family, the all-cohort S2 for your
   D3 decision), then your Word pass on the newest stage-B docx (§11.5).

### 12.4 Done on 2026-11-08: the figure-review corrections (digest)

**What was done.** Everything of plan `figure_review_corrections_plan_261108.md` (your
`/implementation`), no pod. The fold-change agreement left the statistics and the supplement.
Every panel was redrawn at its true size on the 180 × 275 mm page read from Figma (D2). The
leave-cohort-out random baseline became a distribution with empirical p-values and BH-FDR. The
text, letter and legends were rewritten (Pareto definition with a DOI, Methods for every new
test, D1 names, "decrease"). The consistency review and the peer-review brainstorm ran inline:
auto mode refused the agent calls because the context-mode hook rewrites agent prompts.

**Files.**

| File | What it holds |
|---|---|
| `Revised_manuscript/FL_harmonization_article_NARGAB_tracked_stageB_261108.docx` | **main result**: rebuilt stage B (108 tracked edits; same tag, it had no Word comments) |
| `Revised_manuscript/review_package_261108/*.pdf` | both review PDFs rebuilt (main 23 pages, supplementary 46) |
| `figures_svg/fig6CD_four_scores`, `fig6F_decision_tree`, `fig6_gradient_panel`, `fig6B_eta_squared`, `figS14a–c`, `figS16a–b`, `figS17a–f`, `figS18a–c`, `fig1E_confounding`, `fig3_*`, `figS6_*`, `fig4*`, `fig5*` | redrawn panels (page size; palette / name fixes) |
| `figures_svg/figS2_merged_distributions_all_cohorts.{svg,pdf,png}` | all 88 cohorts, two columns × three modes — **for your D3 decision** |
| `review_extras/approach_distributions/` (22 pages + `all_22_approaches.pdf`) | before / after distributions of the 22 selected approaches ("for your interest") |
| `review_extras/final_selection_embeddings/` (18 PDFs) | PCA / UMAP / tSNE of the 22 accepted approaches, unharmonized \| harmonized |
| `output/wp9/figma_page_slots_261108.tsv`, `figures_svg/PLACEMENT.md` (new column `slot (mm)`) | page frame and panel slots (D2) |
| `output/wp9/nb05_v1_random_baseline.tsv`, `nb05_v1_random_decreases.tsv` | random baseline per fold (expected rank, SD, exact p) and per test run (decreases) |
| `output/wp9/nb05_v1_rank_tests.tsv`, `nb05_v1_hit_tests.tsv`, `nb05_v1_regret_tests.tsv` | S18a / b / c tests (p, FDR) |
| `output/wp14/figure_consistency.tsv` (r98), `output/wp14/consistency_review_agent.md` | consistency audit and review |
| `brainstorm/figure_peer_review_brainstorm_261108.md` | peer-review brainstorm, requests R1–R9 |

Plain words: *decrease* = best value among the test-part methods minus the chosen method's value
(internal column `regret`); *empirical p* = share of random draws at least as good as the
observation; *slot* = width × height of a panel on the page.

**Results.**

| Finding | Evidence |
|---|---|
| Removing the fold-change agreement does not change the trend count | BH family 216 → 160 tested rows; trends changing by both criteria **43 of 78** before and after, no main trend flips |
| Page size | Figma frame "Figure 4" (node 761-28) = 753 × 1150 px = 180 × 275 mm; fonts 7 / 6 pt at that size; S17 needs two pages (a–c 276 mm, d–f 270 mm with legends) |
| S18a: rank on the test part vs random | Monte Carlo p: S0 0.034, C 0.036, J 0.058, K 0.98; **FDR 0.072–0.98, none < 0.05** |
| S18b: hits vs random (exact Poisson-binomial) | top-1 S0 3 / 5, **FDR 0.006 \***; all scenarios top-3 6 / 20 vs 11.6 % expected, p 0.023, FDR 0.075 |
| S18c: decrease vs every test run | Mann–Whitney FDR 0.38 (batch mixing), 0.58, 0.98, 0.97; Monte Carlo of the mean: batch mixing p 0.017, FDR 0.066 |
| Consequence for the text | the earlier sentence "its regret was lower than random for batch removal and marker correlation (FDR …)" no longer holds; the Results paragraph now says "better than random in S0, C, J (p 0.03–0.06, FDR ≥ 0.072), worse in K; decrease not different from random" |
| Palette bugs found by the audit (fixed) | nb02 built `method_pal` over 31 instead of 33 methods → exploBATCH had ARSyN's colour in Figure 3 / S6; nb08 used tab20 platform colours in Figures 4–5 |
| Naming fixed across figures | diagnosis names (1E vs 4–5), batch IDs with spaces, the S0 pool "S0 · No removal", "cross-batch prediction (macro-F1)" in 4–5, V in 1E "batch × 15 diagnoses" |
| Checks | r90 PASS (words 16,495 → 14,573), r99 0 FAIL, validator ALL PASSED (abstract 188 words), 91 tests, frozen MD5 OK; no "regret" in figures or text; DOI 10.1109/4235.996017 present |

**Message for the paper.** The rule's choice on training cohorts beats a random method in three
of four leave-cohort-out scenarios, but not significantly after correction. Only S0's top-1 hit
rate is significant. The text now says exactly that, and the abstract still needs your word (R1).

### 12.5 What to review next

1. **Content decisions from the brainstorm (D5), ≈ 15 min** —
   `brainstorm/figure_peer_review_brainstorm_261108.md`, table "Requests":
   - **R1:** the abstract says held-out cohorts "confirmed the choice in three of four
     scenarios"; S18 does not support "confirmed". Proposed: "ranked the chosen method above a
     random one in three of four scenarios".
   - **R2:** plain metric names on the rows of Figure 3 / S5 (needs a name table).
   - **R3:** rename the bar "Global batch removal" to "Global batch mixing".
   - **R6–R8:** S18a one random band per scenario; merge S17a and S17f; drop the all-methods half
     of S17e.
2. **D3, ≈ 5 min:** does `figures_svg/figS2_merged_distributions_all_cohorts.pdf` replace the
   30-cohort S2?
3. **Your single Word pass on the newest docx (§11.5 item 1), ≈ 2–3 h:**
   `Revised_manuscript/FL_harmonization_article_NARGAB_tracked_stageB_261108.docx` plus the two
   review PDFs. The new citation is written as "(DOI: 10.1109/4235.996017)" in the Methods and
   the letter, ready for Mendeley.
4. **For your interest:** `review_extras/approach_distributions/all_22_approaches.pdf` and
   `review_extras/final_selection_embeddings/`.
5. **Figma assembly** with the slot column of `PLACEMENT.md`.

## 13. Final review package 2026-11-09 (`daniil_review_261109.md` + all article materials)

### 13.1 What was done

- **Figma units in every figure notebook** (nb01–nb06, nb08; one identical "Figma units" cell
  after the plot-settings cell). Figma reads an SVG with 1 pt = 4/3 px; your frame (node
  1607-116664) is 756 × 1159 px for the 180 × 275 mm page. So every text is now 7.5 pt in the
  file = **10 px in Figma** (before: 13.33 px in nb01 / nb02 / nb06, 9.33 / 9 / 8 px in nb03–nb05,
  nb08). Only the 87 row labels of S5 stay small (6 px), as you allowed.
- **Plot area fitted to the slot, palettes ignored.** After the fonts are set, each panel is
  resized until its plot area (axes, tick labels, titles; without legends and colour bars) has the
  slot size in Figma px. Slots: the `PLACEMENT.md` column for Figure 6 / S14 / S16–S18 (unchanged
  mm); full width (180 mm, own aspect ratio) for 1E, 2A, S2, S5, S6; 180 × 200 mm for Figure 3;
  130 × 62 mm for S4. Figure 1E: 1,018 px wide before → plot area 756 px now.
- **Batch names:** no "(n = …)" in 1E; microarray batches drop the last "Unknown" (library
  preparation is never known for arrays): `GPL570_FF_Unknown` → "GPL570 FF",
  `GPL570_Unknown_Unknown` → "GPL570 Unknown" (biomaterial unknown); RNA-seq keeps its library
  type ("RNASeq FF PolyA", "RNASeq FF Unknown"). Same function in 1E and the Figure 4–5 legends.
- **Square scatter plots** in Figures 4–5 (every embedding axis has a 1:1 box); the four columns of
  a panel are packed next to each other (panel width 418–515 px of the 756 px frame), PCA titles
  in whole percent, the score line split over two lines.
- **S4:** counts only ("54/58"), no percentages; 130 × 62 mm instead of 241 × 157 mm.
- **Layout fixes forced by the larger text:** Figure 3 legends are stacked by measuring each one
  (they overlapped), cluster names wrapped; 6C/D titles wrapped without splitting words, two
  one-decimal ticks per narrow axis; S17c labels placed after the slot fit (adjustText, no overlap
  checked); 1E group labels moved clear of the bars.
- **New checks / scripts:** `r97_figma_check.py` (every publication SVG: font sizes in Figma px,
  plot area vs slot and frame → `output/wp14/figma_check.tsv`); `r46 --tag`; `r47_build_review_package.py`
  (package below, clean accept-all manuscript, Tables 1–3 cut out of it).

### 13.2 Files (the package)

`Revised_manuscript/review_package_261109/` (its `README.md` lists each file with size and source):

| Folder | Content |
|---|---|
| `1_manuscript/` | tracked docx (stage B 261109: S18 legend after the merge) + clean copy with every change accepted (checked: same text as the accept-all view r90 / r99 read) |
| `2_response_letter/` | response letter 261109, **draft**: all numbers filled, 16 `[LINES]` markers wait for Word line numbers |
| `3_main_tables/` | Tables 1–3 with titles (docx) + one sheet per table (xlsx) |
| `4_main_figures/` | revised main-figure panels (1E, 2A, 3, 4A–D + legend, 5A–C + legend, 6B–F), one per page |
| `5_supplementary_figures/` | Supplementary Figures S1–S18 (46 pages, 10.1 MB, alt-text line per figure) |
| `6_supplementary_files/` | Supplementary Files 1–3 |

Column names of `output/wp14/figma_check.tsv`: `file_w_px` / `file_h_px` = whole file incl.
legends; `plot_w_px` / `plot_h_px` = plot area only; `slot_*` = target; `font_sizes_px` = every
distinct text size in Figma px.

### 13.3 Results

| Finding | Evidence |
|---|---|
| Every publication text is 10 px in Figma | `figma_check.tsv`: 33 / 33 SVGs pass (34 before the S18b merge); the only other size is S5's 6 px row labels |
| Every plot area fits its slot and the frame | 33 / 33 within 2 px of the slot; widest plot area 757 px, tallest 840 px (Figure 3; frame 1,159) |
| No microarray batch name ends in "Unknown", no "(n = …)" in 1E | grep of `fig1E*.svg`, `fig4*.svg`, `fig5*.svg`: 0 hits |
| Data and numbers unchanged; text changed only in the S18 legend | figure notebooks re-drawn; `FROZEN_MD5.txt` OK; 91 tests pass; r90 PASS, r99 0 FAIL |
| Left for you (r98) | Figure 3 / S5 rows still carry metric code names (`wm_RNA_BATCH` …): request R2 of §12.5 (name table) is not decided |

### 13.4 Message for the paper

None new: this round changes presentation only. Open the package README, then `4_main_figures/`
and `5_supplementary_figures/`; the SVGs for Figma are in `figures_svg/`.

### 13.4b Your three S18 requests (added to `daniil_review_261109.md` during this round)

**(a) S18a half height** — done: slot 180 × 100 → 180 × 50 mm; plot area 756 × 210 px.

**(b) S18a and S18b answer the same question** — yes: a top-1 / top-3 hit is the S18a rank with a
threshold (rank = 1, rank ≤ 3). Your decision (2026-11-09, chat): **merge**. S18b is gone as a
panel; each S18a panel title now carries the rank test and the two hit tests, e.g. S0:
"rank: p 0.034, FDR 0.072 ns / top-1: 3/5, FDR 0.0057 ** / top-3: 3/5, FDR 0.067 ns". So the only
significant leave-cohort-out result (S0 first in 3 of 5 folds) stays visible. The decrease panel
moved from S18c to **S18b**; the legend (r50 stage B), the alt text (r46) and nb05 were updated;
the Results / Methods sentences on the hits are unchanged (they cite Supplementary Figure 18 without
a panel letter). Old files in `figures_svg/superseded/`.

**(c) Why S18c (now S18b) lost its significant differences** — the random baseline changed, not
the data. Until 2026-11-07 the "random method" was **one expected-value row per fold** (the mean
decrease over all test runs of that fold), so the random group had 16–20 numbers with almost no
spread; on 2026-11-08 your rule "random baselines are distributions" replaced it with **every test
run of the same folds** (399–403 runs). The means are the same, only the spread became visible:

| Score | chosen mean (n) | random, old: per-fold expected value (n, SD) | random, now: every run (n, SD) | FDR old → now |
|---|---|---|---|---|
| Batch mixing (global + local) | 0.176 (15) | 0.275 (16, SD 0.075) | 0.271 (403, SD 0.186) | 0.012 * → 0.38 ns (Monte Carlo of the mean: p 0.017, FDR 0.066) |
| Marker correlation | 0.064 (15) | 0.135 (20, SD 0.013) | 0.137 (401, SD 0.255) | < 0.001 *** → 0.98 ns |
| Diagnosis retention, prediction | 0.316, 0.307 | ≈ same as now | 0.264, 0.316 | ns → ns |

(old column recomputed today from `output/wp7/v1_fold_results.tsv` role "random method"; now column
from `output/wp9/nb05_v1_regret_tests.tsv`.) A Mann–Whitney test against per-fold means compares the
chosen method with an average, whose spread shrinks with the number of runs, so it overstated the
evidence; the comparison with the single runs is the right one for "a method picked at random". The
direction is unchanged: the chosen method loses less batch mixing and marker correlation than a
random one, but with 15 folds the difference is not significant after correction.

**Text and checks after the merge:** r45, r50 stage B → `…_tracked_stageB_261109.docx` (108 edits),
r90 PASS (nothing grew), r99 0 FAIL, validator ALL PASSED, frozen MD5 OK, 91 tests; the review
package was rebuilt (S1–S18 PDF 45 pages).

**Review-only embeddings (your follow-up, 2026-11-09):** nb07 now draws square scatters and the same
plain batch names; the 18 PDFs of `review_extras/final_selection_embeddings/` were re-drawn from the
cache (30 pages, no old batch name left).

### 13.5 What to review next

1. **Figma import check, ≈ 10 min:** import `figures_svg/fig1E_confounding.svg` and one Figure 6
   panel; text should read 10 and the plot fit the frame width. If Figma still shows another size,
   tell me the number (the conversion factor is one constant, `FIGMA_PX_PER_PT`).
2. **Open content decisions of §12.5, ≈ 15 min:** R1 (abstract "confirmed"), R2 (plain metric
   names in Figure 3 / S5), R3 ("Global batch mixing"), R6–R8; D3 (all-cohort S2).
3. **Your Word pass, ≈ 2–3 h:** `review_package_261109/1_manuscript/` (tracked) with the two
   figure PDFs, the tables folder and the letter draft.
4. **Line numbers for the letter:** after the Word pass, give me the line numbers (or fill the 16
   `[LINES]` markers in `response_letter_draft.md`); then `r60` builds the final letter → G5.
5. **Mendeley:** the 12 reference items of `output/wp12/reference_audit.tsv` and the DOI citation
   10.1109/4235.996017 → G6.
