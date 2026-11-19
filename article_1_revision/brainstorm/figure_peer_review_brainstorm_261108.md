# Figure peer review — brainstorm, 2026-11-08

Plan `figure_review_corrections_plan_261108.md`, item 14c. Slug `figure-peer-review`, log
`article_1_revision/.brainstorm/figure-peer-review.md` (no prior log, round 1).

**How it ran.** The plan asked for three agents. The agent calls were refused by the auto-mode
check: the context-mode plugin hook rewrites every agent prompt, so auto mode cannot review it.
The three personas therefore ran inline in one voice (the brainstorm skill allows this), on the
review PDFs of 2026-11-08 and the panel PNGs after every fix of this plan. To get three
independent agents, switch the hook off or approve the agent calls outside auto mode, then
re-run this round.

- **Builder:** a reviewer sympathetic to the method.
- **Critic:** a hostile reviewer.
- **Analyst:** the handling editor, who decides what the authors must change.

## TL;DR

The figures now carry one clear message each, with one exception. The leave-cohort-out figure
(S18) shows a transfer that no test supports after FDR correction, so the abstract and the
Results must say "better than random in three of four scenarios, not significant", not
"confirmed". The other requests are mostly mechanical. The content requests are listed for
Daniil (D5): simplify S18a, decide on Figure 3's metric labels, and possibly merge S17a with S17f.

## Debate per figure

| Figure | Builder (sympathetic) | Critic (hostile; bias guarded against) | Analyst (editor's request) | Kind |
|---|---|---|---|---|
| 1E confounding | The heat map shows at a glance that 11 of 29 batches hold one diagnosis; V and AMI in the title. | 15 diagnosis columns but the analysis uses 3 major groups: the reader cannot see which grouping V refers to (*availability bias*: the striking map stands in for the number). | Add "(batch × 3 major groups)" to the V of the title, or "15 diagnoses" if that is what V uses. | mechanical |
| 2A strategy map | Codes "S0 · No removal" make the text traceable. | Labels overlap the ribbons ("By platform", "Bad batches removal"); "Bad batches removal" uses "removal", which D1 tried to keep away from scores. | Final label placement in Figma (already planned). | mechanical (Figma) |
| 3 clustermap | Shows that the reduced panel still separates the approaches into named groups. | 2,234 columns cannot be read; the metric rows carry code names (`wm_ratio_bio_batch`) in a main figure (*complexity as evidence*). | Plain metric names on the rows (needs a name table); keep the figure. | mechanical, needs Daniil's names |
| 4A–D, 5A–C embeddings | Each recommendation sits next to its unharmonized data with marker correlation and prediction in the title; now in the article palettes. | 30 batch colours cannot be told apart; the batch row of 5A–C relies on the eye; the prediction is named three ways across figures. | Same prediction name as 6C/D; keep the batch colours (the message is mixing, not identity). | mechanical |
| 6B η² | Simple and quantitative. | — | none | — |
| 6C/D four scores | Gate value + unharmonized marker answer "was it worse without harmonization?" directly; anchors visible even when they coincide. | Six columns × 22 rows is dense; "Global batch removal" next to "Batch mixing" invites the confusion D1 wanted to avoid (*naming drift*). | Rename the global bar (question to Daniil); otherwise accept. | mechanical (name) |
| 6 gradient panel | Six selected methods, real-data V marked: the confounding message in one panel. | The bands are SD of three draws, not CIs: the legend now says so. | none | — |
| 6F tree | Draft for Figma. | — | Daniil finishes it in Figma. | — |
| S2 (30 cohorts) / all-cohort version | All 88 cohorts drawn at page size. | Six panels per row at 6 pt are dense; the 30-cohort version is easier to read. | Daniil decides (D3). | content (D3) |
| S14a–c gates | Clear thresholds; leakage panel explains why covariate methods look good. | — | none | — |
| S16a–b robustness | Faint bars with SD and pool dots: "whole ranking stable, top unstable" is visible. | The text quotes medians, the bars show means: two summaries of one table (*selective reporting*). | Text and legend both say which summary is used (legend: mean ± SD; text: median, range) — acceptable as long as both are stated. | mechanical (wording) |
| S17a vs S17f | S17a = overview of 14 methods with controls; S17f = the selected methods at a readable scale; the Results sentence now explains why both exist. | 14 overlapping lines in S17a are spaghetti; S17f repeats the same axes for a subset (*more panels = more rigour*). | Keep both (Daniil asked why both exist; the answer is in the text). Optional: merge by greying the non-selected methods in S17a and dropping S17f. | content (D5) |
| S17b slopes | Forest plot with CIs and filled = both criteria. | — | none | — |
| S17c strategies | Strategy colours and code labels without overlap. | n = 14, p = 0.50 / 0.82: an inset that shows nothing (*null result kept for completeness*). | Keep: the text says it is low-power and observational. | — |
| S17d λ scatter | Shows the front moving as confounding grows. | Labels crowd at λ = 1. | none after adjustText. | — |
| S17e ranks | No-harmonization rising to the top under confounding is the key Discussion point. | The right half (14 lines) is unreadable; the left half alone carries the message. | Optional: drop the right half. | content (D5) |
| S18a ranks | Bars with random mean ± SD and vertical notes are much clearer than the scatter. | The random bar repeats in every fold; none of the scenario p-values survives FDR (q ≥ 0.072), yet the abstract says held-out cohorts "confirmed the choice in three of four scenarios" (*confirmation bias*). | (1) Text: "better than a random method in three of four scenarios; not significant after correction" — the Results paragraph now says this, the abstract does not yet. (2) Optional: one random band per scenario. | (1) content / text, (2) content (D5) |
| S18b hit rates | Exact Poisson-binomial p; S0 top-1 significant (3 of 5, FDR 0.006). | Over all 20 folds, top-3 6 of 20 vs 11.6 % expected, FDR 0.075: not significant. | The letter and Results quote the FDR; accepted. | — |
| S18c decrease | "Decrease" instead of "regret"; global / local named; random = every test run. | Nothing is significant (Mann–Whitney FDR ≥ 0.38; Monte Carlo batch mixing p 0.017, FDR 0.066). | The Results paragraph now says no difference; accepted. | — |

## Synthesis

- **Agreed by all three.** Palettes and names are consistent after this plan's fixes (r98: no
  colour mismatch left). The answer to "why both S17a and S17f" is in the text. The S18
  statistics are now honest.
- **Irreducible trade-off.** Completeness versus readability: S17a with S17e, and S2 with all
  88 cohorts, show everything but are dense. The editor accepts density in the supplement when
  the main text quotes only what the figure supports.
- **Weakest surviving assumption.** The abstract's "held-out cohorts confirmed the choice in
  three of four scenarios". After FDR correction no scenario's rank test is significant
  (q 0.072–0.98), and only S0 top-1 is (q 0.006). A hostile reviewer would quote this first.

## Requests for the authors, by kind

| # | Request | Kind | Decision |
|---|---|---|---|
| R1 | Abstract: replace "held-out cohorts confirmed the choice in three of four scenarios" with wording supported by S18 (e.g. "on held-out cohorts the chosen method ranked above a random one in three of four scenarios") | content (text) | Daniil |
| R2 | Plain metric names on the rows of Figure 3 / S5 | mechanical, needs names | Daniil |
| R3 | Rename the global bar "Global batch removal" → "Global batch mixing" (D1 logic) | mechanical (name) | Daniil |
| R4 | One prediction name in Figures 4–5 titles (as 6C/D / S14) | mechanical | **applied** 2026-11-08 ("cross-batch prediction (macro-F1)"; nb08 re-run) |
| R5 | V in the Figure 1E title: say which diagnosis grouping | mechanical | **applied** 2026-11-08 ("batch × 15 diagnoses"; nb01 re-run) |
| R6 | S18a: one random band per scenario instead of a bar per fold | content | Daniil (D5) |
| R7 | S17a + S17f merge (grey non-selected methods in S17a) | content | Daniil (D5) |
| R8 | S17e: drop the all-methods half | content | Daniil (D5) |
| R9 | S2: replace the 30-cohort figure with the all-cohort one | content | Daniil (D3) |

## Reasoning summary

The figure-level problems that remained after the corrections were naming and density, which are
cheap to fix or acceptable in a supplement. The one claim a reviewer would attack is a text claim:
the abstract's "confirmed" is stronger than the corrected statistics of S18. That is why R1 heads
the list, even though it concerns the text rather than a figure.
