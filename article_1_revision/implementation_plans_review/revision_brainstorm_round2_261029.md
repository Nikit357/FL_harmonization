# Article 1 revision (NARGAB-2026-312): brainstorm round 2, 2026-10-29

**Input:** `reviewer_report.md` with Daniil's proposals **and Arsen's (supervisor) inline comments**,
added 2026-10-29. **Builds on:** round 1, `revision_brainstorm_261028.md`. Everything agreed there
still holds unless this file changes it (§6). **Debate log:** `.brainstorm/nargab-312-revision-strategy.md`
(git-ignored), round 2. **Hard constraint (Daniil):** the number of lines, figures and tables (main +
supplementary) may go down, never up.

---

## 1. TL;DR

Arsen's two "control" datasets and his request for a formal statistic fit together as **one bounded
experiment**: a **confounding gradient**. The same five batches are subsampled into designs that range
from perfectly balanced (positive control, Cramér's V = 0) to one diagnosis per batch (negative
control, V = 1), and a reduced set of methods is harmonized on each design. The slope of every metric
against V is the formal statistic, and the real data (V = 0.40 on the same batches) sits on that curve.
His other points (a criteria hierarchy, simple interpretable readouts, the "real-world" framing) agree
with round 1. They need two corrections. The real-world argument works only when it is backed by the
measured V values, not when it is used as a reply to the reviewers. And the "simple scores" must stay
separate side-by-side readouts in native units, not a new total.

---

## 2. Arsen's comments, read one by one

| Point | Arsen's request | Compatible with round 1? |
|---|---|---|
| R1.1 a | A formal statistic of *how* imbalance and confounding affect batch-correction performance | Partly new. In round 1 we only *described* the confounding (V, AMI, connectivity, variance partition) and did not measure its *effect* on performance |
| R1.1 b | Positive control: a uniformly balanced dataset; negative control: single-biology batches only; real data in between; re-run ComboBatch | New experiment |
| R1.1 c | Discuss imbalance as the real-life situation | Text only |
| R1.2 | Discuss why A, B and E1–E3 came from the initial manual FSQN R trial; stress that the benchmark is real-world, with no homogenization | Agrees with round 1 M2 (a) and (b); adds framing |
| R1.3 | Real-world argument: simple strategies (one platform or one biology) cannot be assembled | Text only; round 1 already equalizes metric availability through the reduced panel |
| R2.1 | A hierarchy of criteria; metrics depend on the strategy; a clustermap plus per-strategy rules; the preferred metrics shown in the decision-tree figure | Agrees with round 1 (Gate L → Gate N → rank → visual check); adds per-strategy rules and a Figure 6F change |
| R2.2 | Replace the composite by simple interpretable scores (L, N, local, global); the composite is not used for evaluation, only "as a final analysis" | Agrees on removing the composite from selection. **Ambiguous:** "only as a final analysis" can mean that a summary score is kept at the end. Round 1 ruled out any total score (decision D3 below) |

---

## 3. Measured facts (computed today from the prepared annotation, 7,174 samples)

| Quantity | Value |
|---|---|
| RNA_BATCH × Diagnosis_cell_type_unified (15 levels): Cramér's V / adjusted mutual information | **0.363 / 0.263** |
| RNA_BATCH × major group (DLBCL, FL, Normal B, BL, HGBCL): Cramér's V | **0.499** |
| Single-diagnosis batches (15-level diagnosis) | **11 of 29 batches, 2,068 samples (28.8 %)** |
| Bridging batches (≥ 2 diagnoses) | 18 batches, 5,106 samples |
| Single-diagnosis cohorts | 44 of 88 |
| Batches that contain DLBCL **and** FL **and** Normal B | 6: GPL570_FF (282 / 462 / 250), GPL570_Unknown (642 / 266 / 25), GPL96+97_FF (78 / 191 / 36), GPL96_FF (53 / 72 / 8), RNASeq_FF_PolyA (898 / 16 / 125), RNASeq_FF_Total (25 / 3 / 4); 3,436 samples, V = 0.399 |
| Largest perfectly balanced design (equal thirds per batch) on these 6 batches | **1,014 samples**, of which 750 come from GPL570_FF; the RNA-seq batches add only 57 |

Two consequences follow. First, a balanced positive control exists, but it is small and dominated by
one GPL570 batch, so it must be built with a cap per batch (§4 Critic, point 2). Second, the
literal negative control "only single-biology batches" (11 real batches) uses *different batches and
platforms* from the balanced one. If the two are compared, any difference mixes the effect of design
with the effect of platform.

---

## 4. The debate (round 2; three voices)

**Builder (Thesis).** Do what Arsen asks, literally. Build three datasets: (1) balanced, equal
diagnosis proportions in every batch; (2) the 11 real single-diagnosis batches; (3) the real data. Run the
full ComboBatch grid on (1) and (2), that is 31 methods × 3 imputations × 2 post-removal, compute all
metrics, and show that the method ranking is stable from the best case to the worst case. Add a
Discussion section called "A real-world benchmark", which answers R1.1, R1.2 and R1.3 together. Replace
the composite by four scores (L, N, local, global) and print them on each leaf of the decision tree.

**Critic (Antithesis).** There are five problems.
1. *Two datasets do not give a statistic.* Arsen asked for a formal measure of how confounding *affects
   performance*. Three points (best, real, worst) on different sample sets give a picture, not an
   estimate. A dose-response needs several confounding levels on **the same batches and the same
   sample count**, with replicates. Otherwise the slope is not identifiable.
   *Bias: availability* (the two most vivid scenarios crowd out the design that would actually measure
   the effect).
2. *The literal negative control changes two things at once.* The 11 single-diagnosis batches are
   mostly small GPL / FFPE arrays. "Worse results" there could come from platform as much as from
   confounding. The control must hold the batches fixed and change only the design. The balanced design
   also has a problem: GPL570_FF provides 74 % of it, so batch-mixing metrics would mostly measure one
   batch. A per-batch cap is needed.
3. *Covariate methods break in the negative control.* When each batch carries one diagnosis, ComBat
   with `mod` and SVA with a diagnosis design have a singular design matrix. They either fail or
   silently remove the biology. This is not a nuisance: it is the clearest demonstration of the
   label-leakage point from round 1. It also forces both variants (with and without the covariate) into
   the experiment, which answers round-1 decision B2 at no extra cost.
4. *"Real-world" as a defence.* Repeating "our benchmark is real-world" three times in the response
   reads as a refusal to answer R1.1–R1.3. It becomes an argument only when it is measured: "the real
   data has V = 0.40 and lies between the controls at V = 0 and V = 1, and the ranking of methods
   changes / does not change along that axis". *Bias: motivated framing.*
5. *Four scores can become a hidden composite.* "Local" and "global" each average batch-removal
   metrics (higher = more mixing) together with biology metrics (higher = more separation). An average
   of the two sides cancels the very trade-off that R2.2 asked us to show. Also, "a composite only as a
   final analysis" brings back R2.2 (iii): we would then have to prove that it is robust to weighting.
   *Bias: sunk cost* (keeping a summary score because one already exists).

**Analyst (Synthesis).** The constraints are the page budget, pod time and a revision deadline.
1. **Confounding gradient experiment (answers R1.1 a + b, and B2).** Use the 5 batches with all three
   major groups and ≥ 8 samples per cell (RNASeq_FF_Total is dropped). Fix a cap per batch so that no
   batch dominates (for example, at most 150 samples per batch). Build designs along a mixing
   parameter λ ∈ {0, 0.25, 0.5, 0.75, 1}: λ = 0 means equal thirds in every batch (V ≈ 0), and λ = 1
   means one major group per batch, assigned so that each group appears in at least one batch
   (V = 1). Keep the total n and the batch sizes fixed, and draw 3 random replicates per λ. Harmonize
   with a **reduced method set** of about 10 methods: raw, FSQN R, SVA (with / without the diagnosis
   covariate), MNN, ComBat (with / without), limma, AMDBNorm, FSMVN, and one weak method as a contrast.
   Use softImpute and post0 only. That gives about 5 × 3 × 12 ≈ 180 jobs on about 600 samples. These
   are minutes per job, not days. Evaluate on the reduced panel + L + N, plus one **ground-truth
   metric** that only this design allows: the DLBCL-vs-FL and tumour-vs-normal log fold-changes measured
   *within* each batch of the full real data (batch cancels within a batch), compared with the
   fold-changes after harmonization (Spearman ρ and the shrinkage slope). The formal statistic is, for
   every method, the slope of each readout against Cramér's V (a linear mixed model with replicate as
   a random effect), and the real data is placed on the V axis. This one experiment gives the positive
   control, the negative control and the formal effect size. The literal 11-batch negative control is
   optional (decision D1).
2. **Real-world framing (R1.1 c, R1.2, R1.3).** One Discussion paragraph, which replaces the composite
   paragraph. It uses three measured numbers: V = 0.36 overall; 28.8 % of the samples sit in
   single-diagnosis batches; the gradient result. Table 1 gains two columns at no extra page cost:
   *Cramér's V (batch × diagnosis)* and *% samples in single-diagnosis batches* for each of the 14
   strategies. This also makes the observational link (strategy confounding vs best achievable
   metric) visible without a new figure. The response letter states the argument once, with numbers.
3. **FSQN-derived strategies (R1.2).** One Methods sentence and one Discussion sentence state that A, B
   and E1–E3 came from a manual first harmonization attempt with FSQN R (Table 1, "Iteration"). The
   round-1 leave-strategies-out check (FSQN re-ranked without A, B, E1–E3) gives the evidence. B is
   added to the round-1 list, which named only A and E1–E3.
4. **Readouts (R2.2, Arsen).** Report **six side-by-side readouts in native units, with no total**:
   global batch removal, global biology retention, local batch mixing, local biology retention, marker
   preservation (L, ρ) and prediction (N, macro-F1). Each readout is one named metric of the reduced
   panel, chosen as the medoid of its axis (the metric with the highest mean |ρ| to the others on that
   axis). Each readout is printed with its two anchors from the gradient experiment (the value at
   V = 0 and at V = 1), so that "0.60" gets a meaning. Arsen's four scores are this list with local and
   global each split into batch and biology. If Daniil and Arsen want exactly four, the alternative is
   four panels, each with two bars (decision D3).
5. **Criteria hierarchy and per-strategy rules (R2.1).** Use the round-1 hierarchy unchanged (Gate L
   ≥ 0.7 → Gate N non-inferior to raw and to the permutation → Pareto rank on batch and biology within
   the scenario → visual check), written down **before** it is applied on the reduced panel, together
   with a table that compares it with the original visual pick. The per-strategy part is limited to
   *which readouts are defined and informative* in each scenario: for example, single-platform
   scenarios have no PLATFORM_RNA metrics, and in FFPE-only data the cohort and the batch nearly
   coincide. Figure 6F gets, on each leaf, the recommended method plus the 2–3 readouts to check, with
   their pass values.
6. **Held-out evidence (R1.2, still open from round 1).** Arsen asks for discussion only, but
   Reviewer 1 explicitly asked for "held-out batches/cohorts or an external dataset". The gradient
   experiment does not answer that. Of the round-1 options, the cheapest literal answer is **V2-lite**:
   take the external cohorts in expression 2.0 that are absent from the 7,174 samples, build two
   scenarios (RNA-seq only; RNA-seq + microarrays), run the same reduced method set and check whether
   the tree's recommended method passes the gates and ranks in the top-k. This is about 25 jobs. Group
   N stays as Daniil wants and is emphasised as the gate computed on every approach. It is not called
   held-out validation of the selection (round-1 reasons: transductive, label leakage).

**Agreed by all three voices.** The gradient design (fixed batches, λ levels, replicates, cap per batch)
replaces the two-dataset version. Covariate on / off is part of it. The real-world argument is made
once, with measured V values, in Table 1 and in one Discussion paragraph. No total score of any kind.
The FSQN provenance of A, B and E1–E3 is stated in Methods and tested by the leave-strategies-out check.
The hierarchy is written before it is applied, and its concordance with the visual pick is reported.

**Remaining trade-off.** It is about scope. The gradient experiment (≈ 180 small jobs) plus V2-lite (≈ 25
jobs) is a moderate pod run and adds one main panel and two supplementary figures. That fits the
budget only if the round-1 cuts are made: −4 supplementary figures and the composite text. Doing less
(gradient only, held-out answered by a limitation statement) is cheaper, but it leaves R1.2 formally
unanswered.

**Weakest surviving assumption.** That the gradient result is clean enough to report. With about 600
samples and three replicates, a flat slope could mean "robust" or "underpowered". The plan must fix in
advance what counts as a meaningful slope: for example, a change in a readout larger than the spread of
the replicates at λ = 0. It must also report a null result as such.

---

## 5. Budget ledger after round 2 (must net ≤ 0)

| Item | Current | After round 2 | Δ |
|---|---|---|---|
| Main figures | 6 | 6. Fig 1E → confounding panel (contingency / connectivity + V); Fig 3 rebuilt on the reduced panel; Fig 6: A and E removed, the radar replaced by the six readouts, **+ gradient panel**, F with readouts per leaf | 0 |
| Supplementary figures | 19 | S2–S4 merged (−2); S8 and S10 removed (−2); robustness (+1); **gradient per method and readout, including the stratified check of round 1** (+1); **V2-lite external check** (+1); S18 reworked (gate + leakage) | −1 |
| Main tables | 3 | 3. Table 1: D moved + **2 confounding columns**; Table 3: gate / readout columns | 0 |
| Supplementary files / tables | 3 files | Same files. New sheets in File 2 *replace* old ones where possible (`Metric_polarity` gains the panel columns); gradient and external results go as new rows / columns in File 3 or as one sheet that replaces `Genes_per_sample` if Daniil agrees | 0 |
| Text | 13,456 words | Removed: composite Results (≈ 5 paragraphs), Supp Fig 8 / 10 sentences, composite Discussion. Added: Methods (confounding + gradient; panel; adjudication + external check), Results (confounding + gradient; external check), Discussion (one real-world paragraph). Target ≤ 13,000 words and fewer lines | < 0 |

---

## 6. Changes to round 1

- **B2 (leakage control)** is now part of the gradient experiment (covariate on / off) and no longer a
  separate decision.
- **The stratified evaluation** (round 1, M1 d) moves into the gradient supplementary figure. The
  bridging-batch recomputation on the 2,234 approaches is kept as a single robustness number, not as a
  separate figure.
- **The leave-strategies-out check** now drops A, **B**, E1–E3.
- **B6 (Reviewer 2 report complete?):** still unanswered.

---

## 7. Decisions for Daniil (and Arsen) before the implementation plan is final

- **D1 — controls.** (a) Confounding gradient on fixed batches, λ ∈ {0, .25, .5, .75, 1} × 3 replicates
  (recommended); (b) (a) + the literal 11-batch single-diagnosis negative control; (c) Arsen's literal
  two datasets only.
- **D2 — held-out evidence (round-1 B1).** (a) V2-lite external expression 2.0 cohorts, 2 scenarios
  (recommended); (b) V1 leave-cohort-out selection; (c) limitation statement only.
- **D3 — readouts.** (a) Six side-by-side readouts, no total (recommended); (b) Arsen's four scores,
  each drawn as batch / biology bars; (c) four scores plus a final total marked "relative index", with a
  weighting robustness check.
- **D4 — the round-1 panel rule and figure cuts** (B3, B4): accept as written?
- **D5 — if the blind rule changes the best set** (B5): report the new set and update the tree
  (recommended), or keep the visual set and report the disagreement.
- **D6 — Reviewer 2 report** (B6): complete, or cut off after comment 2?

---

## 8. Reasoning summary

Arsen's best and worst cases measure the effect of confounding only if everything else is held fixed.
The gradient on the same batches turns his idea into an effect size, and the covariate-on / off arms
answer the leakage concern from round 1 inside the same run. The real-world argument and the simple
readouts are kept, but each is tied to a measured number, so that the reviewers read them as evidence
and not as a defence. That keeps every new item within the space that the round-1 cuts free.

---

## 9. Daniil's answers (2026-10-29)

- **D1 → (b)** confounding gradient **plus** the literal 11-batch single-diagnosis negative control.
- **D2 → (b)** V1 leave-cohort-out selection (select on 4/5 of the cohorts, test on 1/5) for the
  decision-tree scenarios.
- **D3 → (b)** Arsen's four scores (L, N, local, global), local and global each drawn as batch /
  biology bars; no total.
- **D4–D6:** not answered; the plan uses the recommended defaults (round-1 panel rule and cuts; report
  the new best set if the blind rule changes it) and lists them as open gates.
- The cut-off request reads: "…new supplementary tables based on the old ones and new main and
  supplementary **figures**".
