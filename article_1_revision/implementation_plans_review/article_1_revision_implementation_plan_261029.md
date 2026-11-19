# Article 1 revision implementation plan: NARGAB-2026-312

**Manuscript:** "Benchmarking of bulk transcriptomic harmonization tools in a multi-platform B-cell
lymphoma cohort identifies feature-specific quantile normalization and surrogate variable analysis as
top-performing methods"
**Journal:** NAR Genomics and Bioinformatics. Decision: **major revision** (the editor asks for a
point-by-point response, with every changed or added text marked in red, and alt text under every
figure legend). **For now only the tracked-changes version is produced; the red copy is deferred**
(Daniil, 2026-10-29).
**Submitted baseline (read-only):** `figures_for_article/FL_manuscript_versions/FL_harmonization_article_NAR_260912.docx`
(13,456 words; 6 main figures; 19 supplementary figures; Tables 1–3; Supplementary Files 1–3).
**Submitted supplementary package:** `figures_for_article/supplementary_260824/` (S1–S19 PDFs, File 1
csv, File 2 xlsx, File 3 csv.gz).
**Inputs to this plan:** `reviewer_report.md` (Reviewer 1: 3 major + 5 minor comments; Reviewer 2:
2 comments, complete; inline comments by Daniil and Arsen); `revision_brainstorm_261028.md` (round 1);
`revision_brainstorm_round2_261029.md` (round 2 and Daniil's answers, §9).
**Template followed:** the revision of the T2T transposon paper (`Nikit357/T2T_transposons_genes/`,
folder `revision_G3/`, where "G3" is the name of that journal, not one of the gates of this plan):
a frozen baseline, numbered scripts, `nb*` figure notebooks that write SVGs, one `revision_lib.py`,
one tracked-edits script, a response letter, a house-style pass.
**Status:** plan written 2026-10-29; Daniil's first inline comments acknowledged 2026-10-29
(decisions D1–D9 all resolved); second round of inline comments acknowledged 2026-10-30 (λ grid in
0.1 steps, plain-word naming rule, review of the rule's picks, pod instructions for the Mac).
**Nothing is implemented until Daniil approves it.**
**Implementation (2026-10-31, `/implementation`):** Phase 0, the Phase 1 reanalysis up to gates G1 /
G2, and all pod code of Phase 2 are done (TODO §14); the pilots wait for Daniil (`RUNBOOK.md`).
**Implementation (2026-11-01, `/implementation`):** every step that needs neither a pod nor a gate answer is
done: post-pod analysis code (r13, r14, r22, r05), supplementary files (r40), numbers (r45), figure notebooks
nb01 / nb02 / nb06, manuscript stage A (r50), ledger (r90), validation (r99), response letter draft + r60.
Manual for the pods: `README.md` §3–§5.

---

## 0. Glossary of the internal labels used in this plan

The plan uses short labels so that tables stay readable. Every label is explained here, and the text
repeats the meaning in brackets where it is used. **None of these labels may appear in a publication
document** (manuscript, figures, supplementary tables and figures, response letter); §1.1 gives the
plain-word names that replace them there.

**Work packages (WP)** — the blocks of work of this plan, described in §5:

| Label | Work package |
|---|---|
| WP0 | Setup: folders, frozen-file checksums, baseline copies |
| WP1 | Confounding diagnostics: how strongly diagnosis is tied to batch in the existing data |
| WP2 | Reduced metric panel: about 23 non-redundant metrics instead of 87 |
| WP3 | The four scores (marker correlation, cross-batch prediction, Local, Global) |
| WP4 | The written selection rule, its blind application, and the leave-strategies-out check |
| WP5 | Robustness of the selection to panel and weighting choices |
| WP6 | Confounding gradient experiment with its positive and negative controls (new harmonizations) |
| WP7 | Leave-cohort-out validation of the recommendations (new harmonizations) |
| WP8 | Bridging-batch check: diagnosis metrics recomputed on multi-diagnosis batches only |
| WP9 | Figures |
| WP10 | Supplementary tables |
| WP11 | Manuscript text as tracked changes |
| WP12 | Minor comments and references |
| WP13 | Response letter |
| WP14 | House style, validation, final package |

**Decisions (D)** — Daniil's answers to the brainstorm questions, table in §2.1: D1 controls for
confounding; D2 held-out validation design; D3 the four scores replace the composite; D4 panel rule
and figure cuts; D5 what happens if the rule changes the best set; D6 completeness of Reviewer 2's
report; D7 what fills each score bar; D8 method set for leave-cohort-out validation; D9 cap of
samples per batch in the gradient.

**Gates (G)** — points where Daniil approves before work continues, table in §13: G0 the plan; G1 the
reduced panel; G2 the written selection rule; G2b the review of the rule's picks; G3 the pilot run
times; G4 the results; G5 the response wording; G6 the tracked manuscript.

**Caveats (C1–C11)** — the risks listed in §11.

**Reviewer comments** (`reviewer_report.md`):

| Label | Comment in short |
|---|---|
| R1.1 | Reviewer 1, major comment 1: diagnosis is confounded with batch; measure it and temper the biology claims |
| R1.2 | Reviewer 1, major comment 2: the best approaches were selected and tested on the same data (selection bias); provide held-out validation |
| R1.3 | Reviewer 1, major comment 3: the 87 metrics are redundant, equally weighted and not available for every approach |
| R1 m1–m5 | Reviewer 1, minor comments: m1 "33 vs 31 methods"; m2 type of strategy D; m3 Figure 4F caption; m4 terminology; m5 references |
| R2.1 | Reviewer 2, comment 1: state the primary criterion and the order of precedence of the criteria |
| R2.2 (i–iii) | Reviewer 2, comment 2: (i) a non-redundant panel, (ii) interpretable axes, (iii) no single total score |

**Data and method labels:**

| Label | Meaning |
|---|---|
| Strategy keys (Table 1 of the paper) | `S0_no_removal` all 7,174 samples, no batch removed; `A_confirmed_bad`, `B_extended_bad` confirmed / extended bad batches removed; `C_rnaseq_only` RNA-seq only; `D_malignant_only` malignant samples only; `E1/E2/E3_iterative_r1–r3` iterative batch removal rounds 1–3; `F_microarray_only`; `G_affymetrix_only`; `H_affymetrix_extended`; `I_rare_batches_removed`; `J_ff_only` fresh-frozen (FF) only; `K_ffpe_only` formalin-fixed paraffin-embedded (FFPE) only. In the text, the strategy is named by its letter plus its name (e.g. "strategy K, FFPE only") |
| Metric groups A–N | The groups of `compute_batch_metrics.py` (definitions in `harmonization-metrics-calculation/CLAUDE.md`): A PCA variance; B neighbour-based (kBET, LISI, ASW); C embedding; D distribution; E data quality; F variancePartition; G graph connectivity; H pairwise distances; I WaterMelon; J PC variance %; K missing-value retention; L marker correlation; M cross-batch rank agreement; N predictive validation |
| L score | Marker correlation preservation (metric group L): mean per-gene Spearman ρ of the marker genes before vs after harmonization |
| N score | Cross-batch prediction (metric group N): macro-F1 of a 3-class diagnosis classifier trained with one batch left out |
| LOBO | Leave-one-batch-out (the cross-validation scheme of the N score) |
| Imputation modes | `strict` = no imputation; `KNN`; `softImpute` (matrix completion) — the missing-value handling before harmonization |
| post0 / post1 | Harmonized matrix without / with the post-harmonization removal step of the main benchmark. Every new run in this plan is post0 |
| `*_nocov` arms | SVA or ComBat run **without** the diagnosis covariate, to measure label leakage |
| λ | Confounding level of a gradient design: 0 = balanced batches, 1 = one diagnosis per batch (formal definition §3.3) |
| `L11_single_dx` | The design made of the 11 real single-diagnosis batches (literal negative control) |
| V1 | Leave-cohort-out validation (option "V1" of the brainstorm; option "V2", external cohorts, was not chosen) |
| AMI | Adjusted mutual information |
| FFH test | Fisher–Freeman–Halton exact test (r × c extension of Fisher's test) |
| η² | Share of the metric variance explained by a factor (method, strategy, imputation, post-removal) |
| GT log-FC | Ground-truth log fold-change concordance, the batch-free reference metric of the gradient experiment |
| h230 CV-B | The cohort-level cross-validation of the Article 2 harmonization (`cohort_2_0/expression_2_3_0_harmonization/`), whose fold logic is reused |
| ¶[n] | Paragraph index n in `inputs/baseline_dump.txt` (the text dump of the submitted docx) |
| r00–r99, nb01–nb06 | Numbered scripts and figure notebooks of this folder (§8) |

---

## 1. Overview

The reviewers accept the data and the scale of the benchmark. Their criticism is aimed at the
**selection framework**: 87 redundant, equally weighted metrics; a composite score with no biological
meaning; a "best approach" selection that was visual and is not written down as a rule; confounding
between diagnosis and batch; and a selection made and tested on the same data. The revision therefore
**replaces the framework instead of defending it**. In this plan that means:

1. **The composite score is removed everywhere** (Figure 6A, 6E, the composite axis, five Results
   paragraphs, one Discussion paragraph). It is replaced by **four simple scores**, as Arsen asked:
   **L** (marker correlation preservation), **N** (cross-batch prediction), **Local** and **Global**.
   Local and Global are each drawn as two bars, *batch removal* and *biology retention*. No total is
   computed (decision D3, four scores instead of the composite).
2. **A reduced, non-redundant metric panel** (about 23 of the 87 metrics) replaces the 87 metrics
   in every downstream plot. It uses Daniil's rule: metrics with |ρ| ≥ 0.8 collapse to one
   representative, RNA_BATCH and Diagnosis metrics are preferred, and every metric group A–K keeps at
   least one metric. Dropping the PLATFORM_RNA / RNASEQ_SOURCE / COHORT_LABEL variants also makes
   metric availability equal across strategies (1,993 of 2,234 approaches become complete, instead of
   1,354). **The central clustermap (Figure 3) is rebuilt on this reduced panel**, and so are the
   metric-availability (S4) and approach-correlation (S6) supplementary figures.
3. **A written selection rule (adjudication hierarchy).** Gate L (marker correlation threshold), then
   Gate N (prediction non-inferiority), then a Pareto rank on batch removal and biology retention
   within each decision-tree scenario, then a visual check. The rule is frozen in a file before it is
   applied. Its picks are shown to Daniil next to the original visual picks before anything enters
   the manuscript (gate G2b), and their agreement with the original visual pick is reported case by
   case.
4. **Confounding is measured, and its effect is estimated** (reviewer comment R1.1, confounding;
   Arsen):
   - (a) **descriptive diagnostics**: Cramér's V, AMI, single-diagnosis batches, the batch–diagnosis
     connectivity graph and a variance partition;
   - (b) a **confounding gradient experiment** on fixed batches, from balanced (λ = 0, positive
     control) to one diagnosis per batch (λ = 1, negative control) **in steps of 0.1** (11 levels, so
     that the curves are smooth), plus the **literal negative control** made of the 11 real
     single-diagnosis batches (decision D1). λ is defined formally in §3.3. For each method, the slope
     of each score against Cramér's V is the formal statistic. SVA and ComBat run with and without
     the diagnosis covariate, which measures label leakage.

   All harmonizations that must be run anew for (b) and for item 5 (positive control, gradient,
   negative controls, leave-cohort-out validation) are listed in one place, **§6**, separately from
   the quick reanalysis of the existing benchmark tables. **§7** is the step-by-step instruction for
   running the pods from the Mac.
5. **Held-out validation of the recommendations** (reviewer comment R1.2, selection bias):
   **leave-cohort-out validation** (option V1 of the brainstorm) in four scenario datasets (strategy
   J FF only, K FFPE only, C RNA-seq only, S0 all samples). The rule chooses a method on 4/5 of the
   cohorts; the cohorts left out are harmonized on their own, and we check whether the chosen method
   is still among the best there (decision D2).
6. **The "real-world" argument** (Arsen, reviewer comments R1.1–R1.3) is made **once**, with measured
   numbers: two new columns in Table 1 and one Discussion paragraph. The Methods state that strategies
   A, B and E1–E3 were defined by looking at the first FSQN R harmonization. This could favour FSQN R
   in the benchmark, so a **leave-strategies-out check** (WP4 step 4.3) re-applies the selection rule
   without these five strategies and reports whether FSQN R is still recommended.
7. **All minor comments** are fixed as text edits.
8. **Hard constraint (Daniil):** the line count, the number of figures and the number of tables (main
   + supplementary) may go down, never up. A ledger script (`r90_ledger.py`, part of WP14 house style
   and validation) enforces this on the accept-all text.
9. **Plain-word naming rule (Daniil, 2026-10-30):** no internal label of this plan reaches a
   publication document (§1.1).

Deliverables:
- **(i)** a revised manuscript `.docx` in which every change is a genuine Word tracked change
  (word-rewrite skill; citation-safe `safe_tracked_replace`). **No red copy for now**;
- **(ii)** new Supplementary Files 2 and 3, built from the old ones;
- **(iii)** new and reworked main and supplementary figures, made in notebooks as SVG / PDF;
- **(iv)** a point-by-point response letter;
- **(v)** `RUNBOOK.md`, the pod instruction for the Mac (§7).

### 1.1 Plain-word naming rule for publication documents

**Rule.** The manuscript, the figures, the supplementary figures and tables (sheet names, column
headers, cell values, legends, axis labels) and the response letter use **plain-word names only**.
Internal labels of this plan (work packages, decisions, gates, caveats, reviewer-comment codes,
script names, design or variant codes, snake_case column names) never appear there. Standard field
abbreviations (PCA, SVA, FSQN, AMI, FF, FFPE, RNA-seq) are spelled out at first use, as the paper
already does. The response letter refers to the comments as "Reviewer 1, comment 1" and so on.

**Exception: strategy codes (Daniil, 2026-11-08, `gates_review_261102.md` §10.6 A).** The 14
batch-removal strategy codes of the submitted article (S0, A, B, C, D, E1–E3, F–K) are part of the
publication notation, not internal labels: figures and tables show "code · name" ("S0 · No
removal", "D · Malignant samples only"; `revision_lib.STRATEGY_DISPLAY_NAMES`), the text gives
"name (code)" at the first mention in the Methods and the Results and then the code only
(`revision_lib.STRATEGY_CODES`). S0's name is "No removal" (the submitted name). Work-package,
decision, gate and caveat codes, script names and snake_case names stay forbidden.

**Translation table** (internal label → name in publication documents). The notebooks, `r40` and `r50`
take their labels from one dictionary, `revision_lib.PUBLICATION_NAMES`, built from this table, so
that a name is defined once:

| Internal label | Plain-word name in publication documents |
|---|---|
| L score / Gate L | "Marker correlation preservation" / "marker correlation threshold (ρ ≥ 0.7)" |
| N score / Gate N | "Cross-batch diagnosis prediction (macro-F1)" / "prediction non-inferiority check" |
| Local batch / Local biology bar | "Local batch mixing" / "Local diagnosis separation" |
| Global batch / Global biology bar | "Global batch removal" / "Global diagnosis retention" |
| `rule_front` | "Selected by the rule" |
| `visual_best` | "Selected by visual inspection (submitted version)" |
| `bridging_biology` | "Diagnosis separation on multi-diagnosis batches" |
| `single_dx_batch` / `bridging_batch` | "Single-diagnosis batch" / "Multi-diagnosis batch" |
| `in_reduced_panel`, `cluster_id`, `representative_of`, `axis`, `four_score_bar` | "In the reduced metric panel", "Correlation cluster", "Represents the metrics", "Score axis", "Score bar" |
| `main_benchmark`, `confounding_gradient`, `leave_cohort_out` (sheet names) | "Main benchmark", "Confounding gradient", "Leave-cohort-out validation" |
| λ | kept as a symbol, defined in the Methods and in every legend that uses it as "confounding level λ (0 = every batch balanced, 1 = one diagnosis per batch)" |
| `L11_single_dx` | "The 11 single-diagnosis batches" |
| `04_sva_nocov`, `05_combat_nocov` | "SVA without the diagnosis covariate", "ComBat without the diagnosis covariate" |
| method IDs (`16_fsqn_r`, `10_mnn`, …) | the display names of Supplementary Table S1 (e.g. "FSQN R", "MNN") |
| `S0`, `J`, `K`, `C` scenario codes | the strategy names of Table 1 ("All samples", "FF only", "FFPE only", "RNA-seq only") |
| V1 | "Leave-cohort-out validation" |
| LOBO | "Leave-one-batch-out" |
| GT log-FC | "Agreement with batch-free fold changes" |
| post0 | not shown; the Methods say once that the new runs skip the post-harmonization removal step |
| WP*, D*, G*, C*, R1.x, R2.x, r*/nb* names | never shown |

The 87 metric columns of the old Supplementary File 3 keep their published identifiers (e.g.
`ilisi_norm_RNA_BATCH`), because they are already public and each is defined in Supplementary
File 2, sheet `Table_S2_metrics`. Every **new** column uses a plain-word header.

**Enforcement.** `r99_verify.py` scans the accept-all text of the docx, the response letter, every
sheet name and column header of Supplementary Files 1–3, and the text elements of every SVG in
`figures_svg/`:
- it **fails** on unambiguous internal tokens: `WP\d+`, `_nocov`, `rule_front`, `visual_best`,
  `bridging_biology`, `single_dx`, `L11`, `V1`, `post0`, `post1`, `four_score`, `R1\.\d`, `R2\.\d`,
  and any `r\d\d_` or `nb\d\d_` script name;
- it **lists for review** the ambiguous tokens that can be legitimate in biology text (`D\d`, `G\d`
  such as the G0 / G1 cell-cycle phases, `C\d+`, `S0`). Daniil marks each one as fine or to fix.

---

## 2. Decisions

### 2.1 Resolved (2026-10-29, λ grid updated 2026-10-30)

| ID | Decision | Answer |
|---|---|---|
| D1 | Controls for confounding (reviewer comment R1.1) | **Confounding gradient** on fixed batches, λ ∈ {0, 0.1, 0.2, …, 1} (11 levels, 0.1 steps, for smooth curves; Daniil 2026-10-30) × 3 replicates, **+ the literal 11-batch single-diagnosis negative control**. λ is defined formally in §3.3 |
| D2 | Held-out evidence for selection bias (reviewer comment R1.2) | **Leave-cohort-out validation** (option V1: select on 4/5 of the cohorts, test on 1/5) |
| D3 | Readouts that replace the composite | **Arsen's four scores** (L marker correlation, N cross-batch prediction, Local, Global); Local and Global each drawn as batch / biology bars; **no total** |
| D4 | Panel rule and figure cuts | Accepted as written: \|ρ\| ≥ 0.8, complete linkage, RNA_BATCH / Diagnosis priority, "where the group defines them" exception for metric groups C (embedding), D (distribution), E (data quality), K (missing-value retention); S8 and S10 removed, S2–S4 merged, Fig 1E replaced |
| D5 | The blind rule changes the best set | Report the new set; update Table 3, Figure 6F, the Abstract and the Conclusions |
| D6 | Is Reviewer 2's report complete? | **Yes**, 2 comments (Daniil) |
| D7 | What fills each bar of the four scores | **One named headline metric per bar, in its native unit**: the medoid of its axis in the reduced panel. The mean of the min-max-scaled panel metrics on that axis is kept as a robustness variant (WP5, robustness) |
| D8 | Method set for leave-cohort-out validation | **All 31 analysed methods, softImpute, post0 (no post-removal).** If the pilot (WP7 step 7.4) shows that this does not fit the time budget, the fallback does not depend on results: drop the methods whose median run time in the main benchmark exceeds 30 min |
| D9 | Cap of samples per batch in the gradient | 150 samples per batch; sensitivity run without the cap |
| — | Cut-off part of the request | New supplementary tables built from the old ones, **and new main and supplementary figures** |
| — | Red copy for the editor | **Not now**: only the tracked-changes version is produced (Daniil) |
| — | Composite score (brainstorm round 1) | Removed (Daniil, Arsen, both brainstorm rounds) |
| — | Metric group N (cross-batch prediction) (brainstorm round 1) | Kept and emphasised as a **gate** computed on every approach. It is *not* called held-out validation of the selection, for two reasons: it is transductive (the held-out batch was harmonized together with the others), and SVA / ComBat saw the diagnosis labels |
| — | Selection rule (2026-10-30) | Daniil agrees with the rule of WP4 step 4.1 **provisionally** and wants to see which approaches it selects before it is used in the article. This is gate G2b (§5, WP4 step 4.2b; §13) |
| — | Naming (2026-10-30) | Plain-word names only in publication documents (§1.1) |

### 2.2 Open

None. New questions that arise during implementation are raised at the gates (§13).

---

## 3. Background / reference data (measured 2026-10-28/30; use these numbers)

### 3.1 Design of the 7,174-sample cohort (prepared S3 annotation)

| Quantity | Value |
|---|---|
| Cramér's V / AMI, RNA_BATCH × `Diagnosis_cell_type_unified` (15 levels) | 0.363 / 0.263 |
| Cramér's V, RNA_BATCH × major group (DLBCL, FL, Normal B, BL, HGBCL) | 0.499 |
| Single-diagnosis batches | 11 of 29 batches, 2,068 samples (28.8 %) |
| Bridging batches (≥ 2 diagnoses) | 18 batches, 5,106 samples |
| Single-diagnosis cohorts | 44 of 88 |
| Normal B = `Major_group` ∈ {Normal_B_cells, B_cells, Kassandra} | 889 samples. **Never** collapse diagnoses by substring (figures CLAUDE.md gotcha) |

### 3.2 Batches available for the gradient (all three of DLBCL / FL / Normal B present)

| RNA_BATCH | DLBCL | FL | Normal B | Assigned diagnosis a(b) | n_b (cap 150) | n_b (no cap) |
|---|---|---|---|---|---|---|
| GPL570_FF_Unknown | 282 | 462 | 250 | Normal B | 150 | 250 |
| GPL570_Unknown_Unknown | 642 | 266 | 25 | DLBCL | 75 | 75 |
| GPL96+97_FF_Unknown | 78 | 191 | 36 | FL | 108 | 108 |
| GPL96_FF_Unknown | 53 | 72 | 8 | FL | 24 | 24 |
| RNASeq_FF_PolyA | 898 | 16 | 125 | DLBCL | 48 | 48 |
| ~~RNASeq_FF_Total~~ | 25 | 3 | 4 | dropped: one cell has fewer than 8 samples | — | — |
| **Total** | | | | | **405** | **505** |

Cramér's V of the real data on these 5 batches: 0.399.

### 3.3 Formal definition of the confounding parameter λ (text for the Methods)

**What λ is.** λ ∈ [0, 1] sets how strongly diagnosis is tied to batch in a design, that is, the
degree of **batch–diagnosis confounding**. It is **not** a measure of class imbalance. The batch sizes
are the same at every λ, and the overall number of samples per diagnosis changes only a little
(see below). What λ changes is the *diagnosis composition inside each batch*.

**Definition.** Let B be the five batches of §3.2 and G = {DLBCL, FL, Normal B}. Each batch b gets
one *assigned diagnosis* a(b) (table in §3.2). The assignments are chosen so that every diagnosis is
assigned to at least one batch, and so that the λ = 1 design can keep the full batch size. Let
c_{b,g} be the number of available samples of diagnosis g in batch b. The batch size is fixed for all
λ:

  n_b = min(cap, 3 · min_g c_{b,g}, c_{b,a(b)}),  with cap = 150 (decision D9) or no cap (sensitivity).

The target number of samples of diagnosis g in batch b is

  n_{b,g}(λ) = n_b · [ (1 − λ)/3 + λ · 𝟙{g = a(b)} ].

Equivalently, each batch is a mixture: a share 1 − λ of it has a balanced composition (one third
per diagnosis), and a share λ comes only from its assigned diagnosis. Hence:
- **λ = 0, positive control:** every batch contains the three diagnoses in equal thirds, so batch
  and diagnosis are independent (Cramér's V = 0). A good harmonizer should remove batch here without
  losing diagnosis.
- **λ = 1, negative control:** every batch contains only its assigned diagnosis, so batch and
  diagnosis are completely confounded (V = 1 without bias correction; 0.998 with it). Here no method
  can tell batch from biology. Covariate methods (SVA, ComBat with diagnosis) have a singular design.
- **0 < λ < 1:** intermediate confounding, in **steps of 0.1**: λ = 0.1, 0.2, …, 0.9 (decision D1,
  updated 2026-10-30: 11 levels in total give smooth curves).

**Diagnosis totals.** The total of diagnosis g is Σ_b n_{b,g}(λ) = (1 − λ) · N/3 + λ · N_g, where
N = Σ_b n_b and N_g = Σ_{b: a(b)=g} n_b. With the cap this is a near-linear move (after rounding)
from 135 / 135 / 135 at λ = 0 to 150 / 123 / 132 (Normal B / DLBCL / FL) at λ = 1; for example,
λ = 0.5 gives 143 / 129 / 133 (checked 2026-10-30 on the §3.2 counts). The marginal class balance
therefore stays close to constant, and the effect measured along λ comes from confounding, not from
class sizes.

**Feasibility.** n_{b,g}(λ) is linear in λ. The non-assigned cells decrease from n_b/3 and the
assigned cell increases to n_b. The definition of n_b guarantees n_b/3 ≤ min_g c_{b,g} and
n_b ≤ c_{b,a(b)}, so every cell has enough samples at every λ. `r10_build_gradient_designs.py`
asserts this for every design. Note for the pilot: at λ ≥ 0.7, the smallest batch
(GPL96_FF_Unknown, n_b = 24) keeps only 1–2 samples of each non-assigned diagnosis (0 at λ = 1). This
is intended by the design, but methods that need ≥ 2 samples per diagnosis and batch (covariate
arms) may fall back or fail there. This is recorded as a result (caveat C3).

**Rounding and sampling.** n_{b,g}(λ) is rounded by the largest-remainder method so that
Σ_g n_{b,g} = n_b exactly. The samples of each (b, g) cell are drawn at random without replacement.
The random seed is the replicate number (1–3), so the replicates differ in which samples are drawn,
not in the cell counts.

**λ and Cramér's V.** λ is the design parameter. The reported x-axis of the gradient analysis is the
**measured** Cramér's V (bias-corrected, Bergsma 2013) of each realised design (batch × major group
and batch × 15-level diagnosis), plus AMI. On the capped design, the bias-corrected V (batch × major
group) is 0, 0.010, 0.169, 0.287, 0.388, 0.490, 0.592, 0.690, 0.799, 0.897 and 0.998 for λ = 0,
0.1, …, 1 (computed 2026-10-30 from the §3.2 counts; the uncorrected V is ≈ λ). It rises strictly
monotonically; `r10` asserts this. The bias correction pulls the λ = 0.1 design almost to 0, so the
first step of the curve is flatter than the others; this is a property of the statistic, not of the
data. The real data sit at V = 0.399 on these 5 batches (≈ λ = 0.4; 0.363 for the whole cohort),
and this is where the real data are placed on the gradient plots.

### 3.4 Scenario datasets for leave-cohort-out validation

| Strategy | Scenario in Figure 6F | Samples | Cohorts | Batches | Batches with ≥ 2 cohorts |
|---|---|---|---|---|---|
| J FF only | FF only | 3,167 | 65 | 19 | 11 |
| K FFPE only | FFPE only | 3,000 | 18 | 9 | 3 |
| C RNA-seq only | RNA-seq only | 2,243 | 30 | 7 | 6 |
| S0 no removal | RNA-seq + Illumina; RNA-seq + various microarrays | 7,174 | 88 | 29 | 15 |

In strategy K, most batches contain one cohort, so for K "leave cohorts out" is close to "leave
batches out". This is stated in the Methods.

### 3.5 Metric facts (from `Supplementary File 3.csv.gz`, 2,234 approaches, `pct_samples_allNA < 5`)

| Quantity | Value |
|---|---|
| Scoring metrics by metric group | A 11, B 22, C 16, D 11, E 2, G 3, H 7, I 10, K 5 (group names in §0) |
| Metrics on RNA_BATCH, Diagnosis or with no annotation column | 33 |
| Approaches with all 33 defined | 1,993 (89.2 %), against 1,354 (60.6 %) with all 87 |
| Clusters among the 33 at \|ρ\| ≥ 0.8 (complete linkage) | 23, covering all 9 groups |
| Groups without a Diagnosis metric | C embedding, D distribution (RNA_BATCH only); E data quality, K missing-value retention (no column) |
| η² over the 87 metrics (method / strategy / imputation / post-removal) | 0.3629 / 0.2564 / 0.0155 / 0.0020 |
| Metric group N (cross-batch prediction), best vs rest (leave-one-batch-out 3-class F1, median) | 0.629 vs 0.717 |
| Model specification | SVA, ComBat, ComBat-seq, InMoose, M-ComBat receive `Diagnosis_cell_type_unified`; limma gets `batch=` only; RUV uses 10 housekeeping genes |

### 3.6 Reviewer comment → work package map

| Comment (§0) | Work package(s) | Text location (paragraph index ¶[n] in the 260912 dump) |
|---|---|---|
| R1.1 confounding diagnostics, temper biology claims | WP1 confounding diagnostics, WP6 confounding gradient, WP8 bridging-batch check | Methods new para; ¶[84]; Fig 1E; ¶[157]–[170]; Discussion ¶[185] |
| R1.2 selection bias, held-out validation | WP4 step 4.3 leave-strategies-out, WP7 leave-cohort-out validation | ¶[36], ¶[38]; new Results para; Discussion ¶[201] |
| R1.3 redundant / equally weighted / unequal availability | WP2 reduced panel, WP5 robustness | ¶[63], ¶[65], ¶[102]–[112], ¶[153]; Fig 3; S7 |
| R1 m1 33 vs 31 methods | WP12 minor comments (applied in WP11) | ¶[13], Fig 1C label, ¶[217], ¶[224] |
| R1 m2 Strategy D type | WP12 | Table 1 ¶[42], Fig 2A arc label |
| R1 m3 Fig 4F caption | WP12 | ¶[127] |
| R1 m4 terminology | WP12 | whole text |
| R1 m5 references | WP12 | bibliography (Mendeley) |
| R2.1 primary criterion and precedence | WP4 selection rule | Methods new para; ¶[118]; Table 3; Figure 6F |
| R2.2 de-redundant panel, interpretable axes, no total | WP2 reduced panel, WP3 four scores, WP5 robustness | ¶[141]–[155]; Figure 6 |
| Editor: alt text | WP9 figures, WP14 validation | every figure legend |
| Editor: changes in red | deferred (tracked version only for now) | — |

---

## 4. The frozen-baseline rule (applies to every work package)

These files are **frozen for the revision: no edits at all**. New code imports their functions and
never copies or changes them:

```
harmonization-scripts/bench_shared.py              # 39 methods, filter strategies
harmonization-scripts/run_prep_job.py  run_norm_job.py  run_*_parallel.py
harmonization-metrics-calculation/compute_batch_metrics.py  run_metrics_job.py  run_metrics_concat.py
harmonization-metrics/*.ipynb                       # analysis notebooks of the submitted version
figures_for_article/Finally_assembled_figures_for_article.ipynb
figures_for_article/Introductory_figures_for_article.ipynb
figures_for_article/FL_manuscript_versions/FL_harmonization_article_NAR_260912.docx
figures_for_article/supplementary_260824/**
```

Step 0.2 of WP0 (setup) records their MD5 sums in `article_1_revision/FROZEN_MD5.txt`, and
`r99_verify.py` checks them before submission. Why: the published numbers must stay reproducible from
the deposited code (Zenodo), and the revision must not silently change the 2,234-approach table.

Where a variant is needed (SVA without a covariate, metrics on a subset of samples), it lives in
`article_1_revision/revision_lib.py` as a thin wrapper around the frozen function.

---

## 5. Work packages

### WP0 — Setup

- **0.1** Folder layout under `article_1_revision/` (§8). Add `article_1_revision/output/**` larger
  than 50 MB, `cache/` and `.brainstorm/` to `.gitignore`.
- **0.2** `FROZEN_MD5.txt` (§4).
- **0.3** Copy the baseline docx to `Revised_manuscript/FL_harmonization_article_NARGAB_baseline_260912.docx`
  (read-only, `chmod 444`). Copy `supplementary_260824/Supplementary File 2.xlsx` and
  `Supplementary File 3.csv.gz` to `inputs/` (read-only).
- **0.4** Run `nar_review_tools.py fields` and `extract` on the baseline and save the dump as
  `inputs/baseline_dump.txt`. All edit anchors (paragraph indices ¶[n]) are taken from this dump.
  Expect 118 `w:sdt` Mendeley citations and 0 `w:fldChar`.
- **0.5** `r00_baseline_ledger.py`: words and lines per section, the number of figures, tables and
  supplementary items in the baseline → `output/ledger_baseline.tsv`. This is the "never up" reference.
- **0.6** Check what `Supplementary File 4.csv` is in `current_figures_tables_for_article_260915/`.
  (It holds metric polarity; it looks like an unsubmitted leftover.) Confirm that the submitted
  package had Files 1–3 only.
- **0.7** `revision_lib.PUBLICATION_NAMES`: the translation dictionary of §1.1, the single source of
  every plain-word label used by the notebooks, `r40` and `r50`.

### WP1 — Confounding diagnostics (reviewer comment R1.1, layers 1–3)

Script `r01_confounding_diagnostics.py` → `output/wp1/`. Reanalysis only (§6.1).

- **1.1** For S0 (all samples) and for each of the 14 strategies (strategy membership from the
  prepared S3 annotation `prepared/{strat}__strict__ann.tsv.gz`), compute:
  - Cramér's V with bias correction (Bergsma 2013) and AMI, for RNA_BATCH × Diagnosis, RNA_BATCH ×
    major group, COHORT_LABEL × Diagnosis and PLATFORM_RNA × Diagnosis;
  - χ² and Monte-Carlo Fisher–Freeman–Halton p-values (10⁴ simulations, seed 42);
  - the number and share of samples in single-diagnosis batches;
  - the per-batch diagnosis entropy (normalized).

  Output: `confounding_by_strategy.tsv` (14 rows). Two of its columns go into Table 1.
- **1.2** Batch × diagnosis bipartite graph: the connected components, and the bridging batches
  (≥ 2 diagnoses). Output: `bipartite_edges.tsv` and `bridging_batches.tsv`.
- **1.3** Variance partition on the raw S0 matrix (all samples, strict = no imputation): R² of batch
  alone, diagnosis alone and both together on the top 10 PCs. The shared part = R²(batch) + R²(dx) −
  R²(batch + dx). Run per gene and summarized (median, IQR). Use the existing statsmodels OLS;
  `variancePartition` is not needed. Output: `variance_partition_raw.tsv`.
- **1.4** Observational link (descriptive only, 14 points): Spearman ρ between the strategy V and the
  best Local-biology / Global-biology score reached in that strategy (from WP3, four scores). This
  goes to the gradient supplementary figure as a small inset; it is not a main claim.

### WP2 — Reduced non-redundant metric panel (reviewer comments R1.3 and R2.2 (i))

Script `r02_reduced_panel.py` → `output/wp2/`. Reanalysis only (§6.1). Rule (decision D4; brainstorm
round 1, §5):

1. Universe: the 87 scoring metrics (`Metric_polarity`, polarity ≠ 0). Keep the metrics on
   `RNA_BATCH`, `Diagnosis_cell_type_unified` or with no annotation column: 33 metrics. Gate G1
   (2026-11-03): the tSNE centroid dispersion is removed (tSNE does not preserve distances) → 32.
2. Polarity-adjust; Spearman correlation over the 2,234 approaches (pairwise complete); distance
   1 − |ρ|; complete linkage; cut at 0.2.
3. One representative per cluster, chosen in this order: RNA_BATCH / Diagnosis column → lowest NA
   fraction → highest mean |ρ| to its cluster mates → simplest / most cited metric. Every
   tie-break by hand is written to `tiebreaks.tsv` with a reason.
4. Coverage: ≥ 1 metric per metric group A–K; within the groups that define them, ≥ 1 RNA_BATCH and
   ≥ 1 Diagnosis metric. Gate G1 (2026-11-03): a group also counts as covered when one of its metrics
   is a cluster mate (|ρ| ≥ 0.8) of a panel metric; nothing is added back (group H, the distance
   ratios, is represented by the two PC regressions). Result: **22 metrics**.
5. Assign every panel metric to an **axis**: (Global | Local | Distributional | Coverage) ×
   (batch removal | biology retention | neither). The `Metric type` column of `Metric_polarity`
   provides the Global / Local split, and the annotation column provides batch vs biology. Metric
   groups D (distribution) and K (missing-value retention) count as "batch removal / Global" and
   "neither" respectively; say so in the Methods.

Outputs:
- `reduced_panel.tsv`: metric, group, column, axis, cluster_id, representative_of, n_members,
  NA fraction;
- `cluster_membership.tsv`: all 33 metrics with their cluster;
- `reduced_panel_matrix.parquet`: 2,234 × 22, polarity-adjusted, min-max scaled. All later work
  packages read this file, including the rebuilt central clustermap (Figure 3, WP9 figures).

These files are internal (snake_case headers are fine). Their content reaches the publication only
through `r40` and the notebooks, which rename every header with `PUBLICATION_NAMES` (§1.1).

Sensitivity (inputs for WP5, robustness): the same rule at cut 0.1, 0.3, and the panel built from all
87 metrics at 0.2.

### WP3 — The four scores (reviewer comment R2.2 (ii), Arsen; decisions D3 and D7)

Script `r03_four_scores.py` → `output/wp3/four_scores.parquet` (2,407 rows, all approaches, with an
`in_analysis_set` flag). Reanalysis only (§6.1).

| Score (internal) | Bar | Plain-word name (§1.1) | Content (decision D7: one headline metric, native unit) |
|---|---|---|---|
| **L** | — | Marker correlation preservation | `mk_rho_mean_all_genes_narrow_set` (mean per-gene Spearman ρ before / after; the unit is ρ) |
| **N** | — | Cross-batch diagnosis prediction | leave-one-batch-out 3-class macro-F1 (`pv_lobo3_f1_macro`), shown with the permutation-null median |
| **Global** | batch | Global batch removal | medoid of the panel's Global × batch metrics (expected: `PCReg_RNA_BATCH`, the share of PC variance explained by batch) |
| **Global** | biology | Global diagnosis retention | medoid of Global × biology (expected: `PCReg_Diagnosis_cell_type_unified` or `asw_bio_norm_Diagnosis…`) |
| **Local** | batch | Local batch mixing | medoid of Local × batch (expected: `ilisi_norm_RNA_BATCH` or `kbet_acceptance_rate_RNA_BATCH`) |
| **Local** | biology | Local diagnosis separation | medoid of Local × biology (expected: `clisi_mean_Diagnosis…` or `graph_connectivity_Diagnosis…`) |

The actual medoids come from WP2 (reduced panel). The "expected" names above are not decisions. Each
score also gets its **anchors** from WP6 (confounding gradient): the median value at λ = 0, at λ = 1
and on raw data. These anchors are what make "0.60" interpretable. No total, no weights.

The exact column names of L and N are checked against `metrics_comprehensive_*` / the L/M/N concat
tables in step 3.1. The L/M/N values for the 2,234 approaches already exist (blind check run). If a
column is missing for some approaches, the count is reported and nothing is imputed.

### WP4 — Selection rule, blind re-selection, review of the picks, leave-strategies-out (reviewer comments R2.1 and R1.2)

Reanalysis only (§6.1).

- **4.1 Write the rule first:** `adjudication_rule_261029.md`. Daniil approves it (gate G2), then its
  MD5 goes into `FROZEN_MD5.txt`. Only after that does `r04_apply_rule.py` run. The rule:
  1. **Gate L (marker correlation threshold):** L ≥ 0.7 (the threshold already used in the paper;
     this is where MNN exits).
  2. **Gate N (prediction non-inferiority):** the leave-one-batch-out 3-class F1 is not lower than raw
     (same strategy and imputation) by more than 0.05 **and** is above the 95th percentile of its
     permutation null. This is a non-inferiority gate, not a ranker.
  3. **Rank:** within each decision-tree scenario (strategy group of Figure 6F), take the Pareto front
     on (batch removal = mean of the Global-batch and Local-batch bars; biology retention = mean of
     the Global-biology and Local-biology bars). The front is the recommended set, and the order
     within the front is by Local-batch. This is the same orientation as the paper's emphasis on
     local mixing.
  4. **Visual check:** PCA / tSNE / UMAP of the front members (the existing plots), used only as a
     tie-breaker and to veto an approach that is obviously broken. Every veto is logged.

  Per-scenario rule (Arsen): a table states which bars are defined and informative in each
  scenario. For example, single-platform scenarios have no platform metrics, and in strategy K
  (FFPE only) the cohort and the batch nearly coincide. Bars that are not informative are shown
  greyed out, not dropped.

  Gate G2 answers (Daniil, 2026-11-03; final text in `adjudication_rule_261029.md`): the 84
  Shambhala approaches are candidates (L / N from the blind-check rows of `shambhala_P0std_Q0std`,
  the same matrices); N_raw has the same post-removal setting; p < 0.05 with n_perm = 100; one
  multi-platform pool **including D**, whose gate N uses the 2-class (DLBCL vs FL) F1; step 1b:
  an approach identical to its `01_raw` row ("method failed, returned the input") is not a
  candidate; a version 2 is allowed only for a veto-class failure or an empty scenario; the picks
  are plotted (PCA / tSNE / UMAP, like Figures 4–5 and S11–S17) in `nb07`.
- **4.2 Blind application:** `r04_apply_rule.py` → `selection_by_rule.tsv`, plus
  `rule_vs_visual_concordance.tsv` (the 15 visual best approaches of the submitted Table 3 vs the
  front, per scenario: kept / lost / new). If the set changes, decision D5 applies (report the new set
  and update Table 3, Figure 6F, the Abstract and the Conclusions).
- **4.2b Review of the rule's picks (gate G2b; Daniil, 2026-10-30: "which approaches are selected as
  best?").** Which approaches the rule selects is **not known yet**: it needs the reduced panel (WP2)
  and the four scores (WP3), which are not computed until this plan is approved. As soon as step 4.2
  has run, and **before** any figure, table or text of the article uses the result,
  `r04_apply_rule.py --review` writes `output/wp4/selection_review.xlsx` (with a short
  `selection_review.md` summary). It shows how the rule performs in the article:
  - one sheet per decision-tree scenario: the front members in rule order, with their four-score
    bars, gate values and front rank, next to the visual picks of the submitted Table 3
    (kept / lost / new);
  - a **preview of Table 3** as it would look with the rule's picks (the new columns of WP10 included);
  - a **preview of the Figure 6F leaves**: the recommended method per leaf, old vs new;
  - the vetoes of the visual check, if any, with their reason.

  Daniil (and Arsen) read it at gate G2b. **Blindness protocol:** the rule is frozen (MD5) *before*
  its picks are seen, so the version-1 picks are always reported, whatever happens next. If Daniil
  decides to amend the rule after seeing the picks, the amendment is written as
  `adjudication_rule_261029_v2.md` with its date and reason, it gets its own MD5, and the article
  uses version 2. The response letter then says plainly that the rule was amended after its first
  application, what changed and why, and gives the version-1 picks (in the letter only, so that the
  manuscript does not grow). Steps 4.3, WP5 (robustness) and WP7 (leave-cohort-out validation) use the
  version approved at gate G2b.
- **4.3 Leave-strategies-out check** (reviewer comment R1.2; FSQN R provenance).
  - *Why.* Strategies A, B, E1, E2 and E3 (confirmed bad, extended bad, iterative rounds 1–3) were not
    defined before the benchmark from the annotation alone. Their batch exclusions were chosen by
    looking at the result of the **first, manual FSQN R harmonization** (iteration 1): the batches that
    stayed separate after FSQN R were removed. These five strategies may therefore be tuned to what
    FSQN R handles well. If FSQN R then wins in them, part of its advantage could come from how the
    data were filtered and not from the method. Reviewer 1 (comment R1.2) asks exactly whether the
    selection is biased by the way it was made.
  - *What.* Re-run step 4.2 (the frozen rule, same panel, same gates) with the approaches of
    strategies A, B, E1, E2 and E3 removed from the candidate pool. Nothing is re-harmonized; this is a
    filter on the existing table.
  - *Readouts*, per scenario and overall: FSQN R's rank and its Pareto-front membership **with** and
    **without** the five strategies; the front membership of the other recommended methods (SVA, MNN)
    as a comparison; the number of approaches removed. If removing the five strategies empties a
    scenario, the scenario is reported as "not evaluable" in this check.
  - *Interpretation, fixed now.* FSQN R stays on the front without the five strategies → the
    recommendation does not depend on the FSQN R-derived strategies, and the Results say so in one
    sentence. FSQN R leaves the front → the Discussion states that its advantage is tied to the
    strategies its own first run helped define, and the decision tree is qualified accordingly.
  - Output: `leave_strategies_out.tsv`. Its result is added to `selection_review.xlsx` once it exists.

### WP5 — Robustness of the selection (reviewer comments R1.3 and R2.2 (iii))

Script `r05_robustness.py` → `output/wp5/`. Reanalysis only (§6.1). For each scenario, compare the
method ranking and the Pareto-front membership under:
- the panel at cut 0.1 / 0.2 / 0.3;
- the full 87 metrics;
- group-balanced weighting (each metric group A–K weighs 1);
- bar = mean of the axis metrics instead of the medoid (the alternative of decision D7);
- the bridging-batch-only biology metrics (from WP8, bridging-batch check).

- local bars = the runner-up metric of their medoid tie (UMAP entropy on batch, cLISI on
  diagnosis; gate G1 (b), 2026-11-03, fixed before G2b).

Statistics: Kendall τ_b between rankings, top-3 overlap (Jaccard), and a front-stability score (the
share of variants in which an approach is on the front). Output: `robustness_summary.tsv`, which
feeds the new robustness supplementary figure.

### WP6 — Confounding gradient + positive and negative controls (reviewer comment R1.1, Arsen; decisions D1 and D9)

New harmonizations; the full run list, job counts and order are in §6.2–§6.3, and the pod steps in
§7. They run on the benchmark pod image, through new dispatcher scripts that import the frozen
`bench_shared` functions.

- **6.1 Designs** `r10_build_gradient_designs.py` → `output/wp6/designs/`, following the formal
  definition in §3.3:
  - 5 batches (§3.2); λ ∈ {0, 0.1, 0.2, …, 1} (11 levels); 3 replicates (seeds 1–3); cap 150 →
    **33 designs** of 405 samples each. λ = 0 is the positive control and λ = 1 the negative control;
  - sensitivity without the cap: the same 11 λ levels × 1 replicate → **11 designs** (n = 505), so the
    capped and uncapped curves can be compared level by level;
  - `L11_single_dx`: the 11 real single-diagnosis batches (2,068 samples), as they are (literal
    negative control) → **1 design**;
  - in total **45 designs**;
  - for each design: the sample list, the measured Cramér's V (batch × major group and × 15-level
    Diagnosis) and AMI, and assertions that the batch sizes are identical across λ, that every cell
    is feasible and that V rises strictly monotonically with λ (expected values in §3.3);
  - a manifest `designs.tsv`. The design files are small and are committed to git, so that the Mac
    can copy them into the pod (§7).
- **6.2 Preparation:** the softImpute imputation of each design through the frozen prep function on
  the design subset of the S0 raw matrix (an equivalent of `run_prep_job.py` that takes a sample
  list; implemented in `revision_lib.prepare_subset`). Strict (no imputation) and KNN are not run
  (imputation explains η² = 1.6 %; this is stated in the Methods).
- **6.3 Methods** (a fixed set, decided before running): 01_raw, 03_limma, 04_sva, **04_sva_nocov**
  (SVA without the diagnosis covariate), 05_combat, **05_combat_nocov** (ComBat without it), 10_mnn,
  13_fsmvn, 16_fsqn_r, 17_quantile, 33_amdbnorm, 11_harmony = 12 arms, post0 (no post-removal).
  - `*_nocov` = the same frozen function, called through `revision_lib` with the covariate removed.
    ComBat already falls back to no covariate when `bio_col` has one level (bench_shared ~line 790).
  - SVA with a constant factor may fail in `model.matrix`. In that case `revision_lib.sva_nocov`
    runs `sva` with `mod = ~1`, a documented wrapper and not a copy of the frozen function. Check
    this in the pilot.
  - At λ = 1, the covariate arms of SVA and ComBat have a singular design, and at λ ≥ 0.7 the
    smallest batch has only 1–2 samples of its non-assigned diagnoses (§3.3). Record the failure or
    the fallback as a **result**, not as an error.
- **6.4 Jobs:** (33 + 11 + 1) = 45 designs × 12 arms = **540 harmonizations**, each on ≤ 2,068
  samples (most on 405). S3 prefix `FL_batch_correction/revision_261029/gradient/`.
- **6.5 Metrics:** the frozen `compute_all_metrics` for the reduced-panel metric groups + L (marker
  correlation) + N (cross-batch prediction) (kBET is kept; it is fast at this n), via
  `r12_revision_metrics.py --experiment gradient`. **Ground-truth metric (new, only in this
  experiment):**
  - Reference: within-batch log fold-changes, DLBCL vs FL and tumour vs Normal B, from the **full**
    raw data of the 5 batches. Use a limma-style per-gene OLS with batch as a factor and keep only the
    within-batch contrasts. Batch cancels inside a batch, so this is a batch-free reference.
  - After harmonization: the same contrasts computed *without* batch in the model.
  - Readouts: the Spearman ρ between the reference and observed fold-changes over the 3,447 genes,
    and the shrinkage slope (Deming regression).

  Implemented in `revision_lib.gt_logfc_concordance()`.
- **6.6 Statistic** (`r13_gradient_stats.py`): for each method × score, a linear mixed model
  `score ~ V + (1 | replicate)` over the 11 λ levels. Report the slope with its 95 % CI, the value at
  V = 0 and V = 1, and where the real data (V = 0.399 on these batches; 0.363 for S0 overall) falls.
  A slope is "meaningful" only if |Δ| between V = 0 and V = 1 exceeds 2 × the SD of the replicates at
  λ = 0. This criterion is fixed now; a null result is reported as a null. The 0.1 grid also allows a
  plain look at whether the score changes linearly or has a threshold; this is shown in the figure,
  not tested. The literal `L11_single_dx` control is shown as a separate point (different batches; the
  Methods state that it confounds design with platform).
- **6.7 Pilot:** λ ∈ {0, 1} × replicate 1 × cap 150 × all 12 arms (24 jobs) before the full run. Check
  the run time, the nocov wrappers and the λ = 1 failures.

### WP7 — Leave-cohort-out validation (option V1; reviewer comment R1.2; decisions D2 and D8)

New harmonizations; see §6.2–§6.3 and the pod steps in §7. Design: the same logic as the cohort-level
cross-validation of Article 2 (h230 CV-B,
`cohort_2_0/expression_2_3_0_harmonization/h230_01_build_cv_splits.py`), but on the Article 1 data
and code.

- **7.1 Splits** `r20_build_cohort_folds.py`: for strategies J (FF only), K (FFPE only), C (RNA-seq
  only) and S0 (all samples), 5 folds grouped by COHORT_LABEL and balanced (greedy) so that each test
  fold has ≥ 2 RNA_BATCH levels and ≥ 2 of DLBCL / FL / Normal B where the scenario has them. 1 repeat.
  Seed 42. Output: `output/wp7/folds.tsv` (committed to git, small), plus a fold summary (n, batches,
  diagnoses, V per fold). Folds that cannot meet the constraints are reported rather than forced.
- **7.2 Runs:** for each scenario × fold, the **train** subset (4/5 of the cohorts) and the **test**
  subset (1/5) are prepared (softImpute) and harmonized **separately** with 30 methods (decision
  D8; gate G3: all 31 analysed methods except exploBATCH, whose R dependency fMM is not in the
  image), post0 (no post-removal), 6 h per run. That gives 4 × 5 × 2 = 40 prepared subsets and
  40 × 30 = **1,200 harmonizations**. The train runs are larger (S0 train ≈ 5,700 samples); the test runs are
  small.
- **7.3 Metrics and selection:** reduced panel + L + N on every run (`r12_revision_metrics.py
  --experiment leave_cohort_out`). The frozen rule (WP4, the version approved at gate G2b) is applied
  to the **train** runs → the chosen method(s) per fold. On the **test** runs:
  - the rank of the chosen method;
  - top-1 / top-3 hit rate;
  - regret on each bar = (best on test) − (chosen on test);
  - the gate pass on test;
  - baselines: a random method and the method chosen on the full data (the paper's tree).

  Script `r22_v1_evaluate.py` → `v1_summary.tsv`.
- **7.4 Pilot:** strategy C (RNA-seq only) fold 1 (train + test, 31 methods = 62 jobs) for run time and
  for failure modes. The fallback of decision D8 (drop slow methods) is decided here.
- **7.5** Expected wording, whatever the result: "the recommendation transferred to unseen cohorts in
  x of 20 folds (top-3)". If it transfers poorly, the Discussion says so, and the decision tree is
  presented as dataset-specific guidance plus the procedure. That is the honest message.

### WP8 — Bridging-batch check on the 2,234 approaches (reviewer comment R1.1, layer 4)

`r30_bridging_subset_metrics.py` (metrics pod, §7): for all 2,234 approaches, the Diagnosis metrics
of the reduced panel (no kBET), recomputed on samples from bridging (multi-diagnosis) batches only.
Use `revision_lib.metrics_on_subset()` around the frozen functions; the matrices are read from S3 and
**nothing is re-harmonized** (§6.1). Output: one number per approach in `bridging_biology.parquet`.
It goes into WP5 (robustness) and gives one sentence in the Results ("ranking by biology retention on
multi-diagnosis batches only: Kendall τ = x with the full-sample ranking").

### WP9 — Figures (new and reworked)

All figures are made in **self-contained notebooks** (notebook_writing skill; no imported helpers
except `revision_lib`; palettes copied from `Introductory_figures_for_article.ipynb` cell 3: the
Temperature-Split `lymphoma_ontogeny_palette`, `rna_batch_palette` and `platform_palette`; and,
since the G4 review of 2026-11-07, **in every figure** the submitted `strat_pal`, `method_pal`
(hex values written out in nb03–nb05 §0c, identical to the frozen figure notebook), `imp_pal`,
`post_rm_pal`; covariate-free variants take the colour of their parent method, dashed). The
notebooks write **SVG + PDF + PNG (200 dpi)** to `figures_svg/`, `GLOBAL_FONT_SIZE = 10`, rcParams as
in the project CLAUDE.md. Daniil assembles the multi-panel pages himself (as in the T2T transposon
revision); the notebooks emit one file per panel and a `PLACEMENT.md` that maps each file to its
panel. **Every axis label, legend entry, panel title and colour-bar label comes from
`revision_lib.PUBLICATION_NAMES` (§1.1)**: no column name, method ID or design code is printed.

#### 9.1 Main figures (6, unchanged count)

| Figure | Change | Notebook |
|---|---|---|
| Fig 1 | **E replaced** by the confounding panel: batch × diagnosis heat map (log counts) with single-diagnosis batches marked, and the bipartite connectivity as a side bar; V / AMI printed. Panel C label: "33 implemented / 31 analysed" | `nb01_confounding.ipynb` |
| Fig 2 | A: strategy D arc moved to "by biology" (minor comment m2) | `nb01_confounding.ipynb` (re-render of the circos-sankey with the corrected grouping, code copied from the frozen notebook) |
| Fig 3 | **The central clustermap, rebuilt on the reduced panel**: 2,234 approaches × 22 panel metrics (instead of 87); missing cells black; column annotation = metric group, score axis, annotation column; row annotation = strategy, method, imputation; approaches selected by the rule marked (stars), approaches selected only by the original visual inspection marked separately | `nb02_reduced_panel_clustermap.ipynb` |
| Fig 4, Fig 5 | Unchanged art. Legend edits only ("2 × 2", Fig 4F caption, RNA-seq) | — |
| Fig 6 | **A and E removed.** B: η² recomputed on the reduced panel. C/D: the radar is replaced by the **four scores** of the selected approaches (marker correlation, cross-batch prediction, Local batch / diagnosis, Global batch / diagnosis), with the λ = 0 / λ = 1 anchors as reference lines. **New panel: confounding gradient** (score vs Cramér's V over the 11 λ levels for 4–5 key methods, real-data V marked). F: decision tree with, on each leaf, the recommended method plus the 2–3 readouts to check and their pass values | `nb03_four_scores_and_tree.ipynb`, `nb04_confounding_gradient.ipynb` |

#### 9.2 Supplementary figures (19 → 18)

| Old | New | Action |
|---|---|---|
| S1 | S1 | unchanged |
| S2, S3, S4 | S2 | **merged**: one grid, per-cohort distributions under strict / KNN / softImpute (one row per missing-value mode; cohorts subsampled to 30 representative ones; the full set stays in the Zenodo deposit) |
| S5 | S3 | unchanged |
| S6 | S4 | recomputed on the reduced panel (metric availability by strategy × imputation), so that equal availability is visible |
| S7 | S5 | **reworked**: 33-metric correlation clustermap with the clusters at \|ρ\| ≥ 0.8 and the chosen representatives marked (panel construction) |
| S8 | — | **removed** (metric embeddings) |
| S9 | S6 | recomputed on the reduced panel (approach × approach correlation) |
| S10 | — | **removed** (approach embeddings) |
| S11–S17 | S7–S13 | unchanged art; legends: "2 × 2", softImpute, RNA-seq |
| S18 | S14 | **reworked**: marker correlation threshold (boxplots of the marker correlation score by method, 0.7 line), prediction non-inferiority check (F1 vs raw and vs the permutation null), label-leakage panel (SVA / ComBat with and without the diagnosis covariate, from WP6 confounding gradient) |
| S19 | S15 | unchanged |
| — | S16 | **new**: robustness (WP5): Kendall τ heat map over panel variants, front-stability bars |
| — | S17 | **new**: confounding gradient in detail (WP6): every method × score vs V over the 11 λ levels, replicate spread, agreement with batch-free fold changes, the λ = 0 / λ = 1 controls and the 11-single-diagnosis-batch control point, the uncapped sensitivity curve, and the 14-strategy observational inset (WP1 step 1.4) |
| — | S18 | **new**: leave-cohort-out validation (WP7): per scenario, the rank on test of the train-chosen method, regret, and top-k hit rate against the baselines |

Net change: 19 − 2 (merge) − 2 (removed) + 3 (new) = 18. Every legend gets alt text (the editor's
reminder).

### WP10 — Supplementary tables (same file count)

`r40_build_supplementary.py` builds new files **from copies of the old ones** (inputs/), never by
editing the submitted ones. Every new sheet name, column header and categorical value is written in
plain words through `PUBLICATION_NAMES` (§1.1); the snake_case names below are the internal names,
shown here only to tie the columns to their sources.

- **Supplementary File 1** (annotation csv): unchanged; add one column "Single-diagnosis batch"
  (internal `single_dx_batch`, yes / no) and one column "Multi-diagnosis batch" (internal
  `bridging_batch`).
- **Supplementary File 2** (xlsx). The existing sheets are kept:
  - `Genes_per_sample`: unchanged.
  - `Metric_polarity`: + columns "In the reduced metric panel", "Correlation cluster", "Represents the
    metrics", "Score axis", "Score bar" (internal `in_reduced_panel`, `cluster_id`,
    `representative_of`, `axis`, `four_score_bar`).
  - `Table_S1_methods`: unchanged, except `01_raw` is labelled "no-op control" instead of a harshness
    tier, because harshness tiers are no longer used.
  - `Table_S2_metrics`: + one row for "Agreement with batch-free fold changes" and a short
    plain-word description of the four scores.
  - `Table_S3_gene_panel`: unchanged.

  The confounding diagnostics (WP1 step 1.1) are added as **columns of Table 1**, not as a new sheet.
- **Supplementary File 3** (2,407 approaches, csv.gz → **xlsx with sheets**; csv.gz kept on Zenodo):
  - "Main benchmark": the old 87 columns (published identifiers, defined in `Table_S2_metrics`) + the
    four scores + the two gate results + "Selected by the rule" + "Selected by visual inspection
    (submitted version)" + "Diagnosis separation on multi-diagnosis batches";
  - "Confounding gradient": the 540 runs × (design, confounding level λ, replicate, cap, Cramér's V,
    method in plain name, four scores, agreement with batch-free fold changes); the 11-batch control
    is labelled "The 11 single-diagnosis batches";
  - "Leave-cohort-out validation": the 1,200 runs × (scenario, fold, training / test part, method,
    four scores, gate results, "Chosen on the training part").

  The file count stays 3. Check the xlsx size; if it exceeds ~25 MB, keep File 3 as a zip of three
  csv.gz files (still one supplementary file).
- **Table 3** (main): + columns "Marker correlation threshold", "Prediction non-inferiority check",
  "Selected by the rule (yes / no)"; the column "Reason to include" is rewritten in terms of the rule.
- **Table 1** (main): strategy D → "By biology"; + columns "Cramér's V (batch × diagnosis)" and
  "% samples in single-diagnosis batches" (WP1 step 1.1), added with `append_tracked_column`.

### WP11 — Manuscript text (tracked changes)

Script `r50_manuscript_tracked_edits.py`. Pattern: `figures_for_article/edit_python_scripts/apply_nar_review_edits_260912.py`
(first pass on a clean document) together with the word-rewrite skill's
`word_rewrite_trackchanges.py`. Edits **only** through `safe_tracked_replace()` (from
`nar_review_tools.py`), which edits direct-child runs only, so the Mendeley `w:sdt` citations are
untouched. Whole paragraphs are inserted or deleted with the word-rewrite insert / delete helpers.
All anchors are resolved before any mutation. Revision ids are reserved above the input maximum.
Author: "Daniil Nikitin". Every number in the new text is read from `output/**` by
`r45_results_numbers.py` (→ `output/numbers.json`); no number is typed by hand. **Every new sentence
follows the naming rule of §1.1**: the four scores, the gates, the gradient, the controls and the
validation are named in plain words.

Edit list (paragraph indices ¶[n] from `inputs/baseline_dump.txt`; *write* = new text written from the
results; *delete* = tracked deletion):

| ¶ | Section | Edit |
|---|---|---|
| [13] | Abstract | "33 … methods" → "33 implemented, 31 analysed"; one sentence on the confounding gradient and leave-cohort-out results replacing the composite / clustermap sentence; ≤ 200 words checked |
| [36], [38] | Methods: Batch removal strategies | add: A, B and E1–E3 came from a first, manual FSQN R harmonization (iteration 1); the leave-strategies-out check (WP4 step 4.3) is in Results; one "real-world, not homogenized" sentence |
| [42] | Table 1 | D → "By biology"; 2 new columns; "RNASeq only" → "RNA-seq only" |
| new after [61] | Methods: **Confounding diagnostics and confounding gradient** | *write* (one paragraph): V, AMI, bipartite graph, variance partition, gradient design with the formal λ definition (§3.3: n_{b,g}(λ), 11 levels in 0.1 steps, λ = 0 positive / λ = 1 negative control, fixed batch sizes, V as the reported axis), agreement with batch-free fold changes, mixed model, the 11-single-diagnosis-batch control |
| [63], [65] | Methods: Harmonization quality metrics | *rewrite*: 344 computed → 87 scoring → reduced panel of 22 (rule); the four scores; remove "composite scoring" |
| new after [65] | Methods: **Selection rule and validation** | *write*: the adjudication hierarchy (gates, Pareto, visual tie-break) + leave-cohort-out validation design + leave-strategies-out check; if the rule was amended at gate G2b, one sentence says so. It replaces the composite description, so there is no net growth |
| [67] | Methods | Pedregosa citation fixed in Mendeley (WP12), not in the text |
| [80], [82] | Results | "33" consistency |
| [84] | Results: composition | *rewrite* with V / AMI, single-diagnosis batches, bridging (multi-diagnosis) batches, variance-partition shared R²; Fig 1E |
| [87] | Fig 1 legend | E replaced; alt text updated |
| [90], [92] | Results | RNA-seq; softImpute |
| [102]–[112] | Results: Best approaches selection | *rewrite*: reduced panel, equal availability (1,993 complete), central clustermap rebuilt on the panel; delete the Supp Fig 8 / 10 sentences; renumber S-figures |
| [114] | Fig 3 legend | rewritten |
| [118] | Results: Best approaches | "clustermap visual inspection combined with quantitative composite scoring" → "the selection rule (Methods), with visual inspection as a tie-breaker"; concordance with the original visual pick; leave-strategies-out result |
| [121] | Table 3 | new columns; NGS → RNA-seq |
| [127], [138] | Fig 4 / 5 legends | "2 X 2" → "2 × 2"; Fig 4F: "SVA-harmonized, KNN-imputed C (RNA-seq only) dataset" |
| [141] | Results: composite | **delete** |
| [143], [145] | Results: η² | numbers recomputed on the reduced panel; text otherwise kept |
| [147] | Results: radar | *rewrite* for the four scores with anchors |
| [149], [151], [153] | Results: composite composition, ranks, comparability | **delete** (the comparability caveat is solved by construction; one clause moves into ¶[102]) |
| [155] | Fig 6 legend | rewritten (A/E gone, gradient panel, four scores, tree with readouts) |
| [157]–[170] | Results: marker correlation (L), rank agreement (M), prediction (N) | prediction reframed as a gate; new sentences on label leakage (with / without the diagnosis covariate, from the confounding gradient); "biology preservation" → "retention of the diagnosis structure measured by …" (temper, comment R1.1) |
| new after [170] | Results: **Confounding and held-out validation** | *write* (two paragraphs): gradient slopes and position of the real data; leave-cohort-out transfer rates |
| [173]–[179] | Results: decision tree | readouts per leaf; updated if decision D5 applies (the rule changes the best set) |
| [185] | Discussion: imbalance | *rewrite* as the single "real-world benchmark" paragraph with the numbers (Arsen, comments R1.1–R1.3) |
| [200], [201] | Discussion: limitations | delete the composite limitation; replace "could be improved by LOBO selection" with the leave-cohort-out result and its limits (one fold repeat; for FFPE only it is close to leave-batch-out) |
| [203]–[210] | Discussion: clustermap section | retitle "A reduced metric panel and a written selection rule"; shorten; recompute the S7 orthogonality numbers on the panel; MNN sentence kept |
| [217], [219], [224] | Discussion / Conclusions | 31 analysed / 33 implemented; Kappal reference fixed in Mendeley |
| [232]–[256] | Supplementary data list | renumber S1–S18 (collision-safe sweep, figures CLAUDE.md gotchas), new legends, File 2 / 3 descriptions |
| all | Terminology sweep (minor comment m4) | "RNASeq" / "NGS" → "RNA-seq" in prose (not in batch identifiers such as `RNASeq_FF_PolyA`, explained once in Methods); "Softimpute" → "softImpute"; "2 X 2" / "3 X 3" → "2 × 2" / "3 × 3"; "LOBO" → "leave-one-batch-out" at first use; skip `[REVIEWER NOTE]` paragraphs |

Supplementary figure renumbering is done as **one left-to-right sweep in document order**, with the
repeated-number specials first. Replacement text is pre-renumbered. Bare "Figure N" is never used as
a key (it is a substring of "Supplementary Figure N").

### WP12 — Minor comments and references

- Minor comments m1–m4 (33 vs 31 methods; strategy D type; Figure 4F caption; terminology): applied
  in WP11 (manuscript text).
- Minor comment m5 (references): `r51_reference_audit.py` lists the bibliography entries with
  all-caps author tokens, URLs or e-mail addresses in author fields, missing years or journal names.
  The output is a checklist. **Daniil fixes them in Mendeley Desktop and refreshes the
  bibliography.** The bibliography is one Mendeley `w:sdt`; a tracked edit inside it would be
  overwritten at the next refresh. Known items: "Pedregosa FABIANPEDREGOSA", "Kappal S,
  https://independent.academia.edu/SunilKappal". After the refresh, `r51` runs again and must report
  zero items.

### WP13 — Response letter

- `r60_response_letter.py` → `Revised_manuscript/NARGAB-2026-312_response_to_reviewers_<date>.docx`.
  Point by point: each comment quoted in italics, then the response, then "Changes:" with the
  section, figure or table and the line numbers of the revised (tracked, accept-all view)
  manuscript. Comments are referred to as "Reviewer 1, comment 1" etc., and the plain-word names of
  §1.1 are used throughout (no work packages, decisions, gates or script names). The text of the
  responses is drafted in `response_letter_draft.md` first (Daniil and Arsen edit it), then converted.
  The "acknowledge-comments" skill is used for the wording pass. The letter says plainly that:
  - the composite score was removed (Reviewer 2's point on a single total score is therefore moot);
  - the original selection was visual, and how the rule reproduces / changes it;
  - if the rule was amended after its first application (gate G2b), what changed, why, and the
    first-version picks;
  - the cross-batch prediction metric is a gate, not held-out validation, and why.
- The red copy the editor asks for is **not built now** (Daniil, 2026-10-29). Only the tracked docx
  is produced; see caveat C9 (red copy).

### WP14 — House style, validation, package

- `r90_ledger.py`: words and lines of the accept-all text per section, figures, tables and
  supplementary items, against `ledger_baseline.tsv`. It **exits non-zero if any total grows**.
- `r99_verify.py`:
  - frozen MD5s (including the approved selection-rule file);
  - reject-all text == baseline text;
  - `w:sdt` count and contents unchanged;
  - no `w:t` inside `w:del`, no `w:delText` outside `w:del`;
  - unique revision ids;
  - abstract ≤ 200 words;
  - every number in `numbers.json` present in the text where it is cited;
  - every "Supplementary Figure n" for n ≤ 18 exists and is cited in order;
  - alt text present under every legend;
  - **no internal label in any publication document** (the scan of §1.1: fail list + review list).
- Package: `Revised_manuscript/`
  - tracked docx;
  - PDF render;
  - response letter;
  - `Supplementary Figures S1-S18.pdf` (one combined, recompressed file, as in 260824);
  - Supplementary Files 1–3.

  The Zenodo deposit (draft 22737294, not yet published) gets a new version with the revision code
  and outputs only on Daniil's word.

---

## 6. Compute plan: reanalysis vs new harmonizations

The revision has two kinds of work. **Reanalysis** reads the existing benchmark tables (or the
existing harmonized matrices on S3) and needs hours at most. **New harmonizations** run the
harmonization pipeline again on new sample sets and need pod time that must be planned. **None of the
2,234 existing approaches is re-harmonized** (§15).

### 6.1 Quick reanalysis (no new harmonization)

| Work package | What | Input | Where | Expected time |
|---|---|---|---|---|
| WP1 confounding diagnostics | V, AMI, Fisher–Freeman–Halton p, bipartite graph, variance partition | prepared S3 annotations; raw S0 strict matrix | JupyterHub | minutes |
| WP2 reduced panel | the panel (+ cut 0.1 / 0.3 / all-87 variants) | Supplementary File 3 | JupyterHub | minutes |
| WP3 four scores | the four scores | WP2 + L/M/N concat tables | JupyterHub | minutes |
| WP4 selection rule | blind re-selection, review of the picks, leave-strategies-out (a filter on the table) | WP2–WP3 | JupyterHub | minutes |
| WP5 robustness | robustness variants | WP2–WP4, WP8 | JupyterHub | minutes |
| WP8 bridging-batch check | Diagnosis metrics on multi-diagnosis-batch samples only | the existing 2,234 harmonized matrices on S3 (read, not recomputed) | metrics pod (§7) | hours (2,234 metric jobs, no kBET) |

Phase 1 of the TODO (WP1–WP4) can start immediately after gate G0 (plan approval). It does not wait
for any pod.

### 6.2 New harmonizations (pipeline re-runs)

All of them use softImpute and post0 (no post-removal), the frozen `bench_shared` functions (through
`revision_lib` wrappers) and the existing benchmark image. Each harmonization is followed by one
metric job (reduced-panel metric groups + L marker correlation + N cross-batch prediction).

**A. Confounding gradient with its controls (WP6; 12 arms per design, §5 WP6 step 6.3)**

| Run set | Role | Designs | Samples per design | Preparations | Harmonizations |
|---|---|---|---|---|---|
| λ = 0, cap 150, seeds 1–3 | **positive control** (no confounding) | 3 | 405 | 3 | 36 |
| λ = 0.1, 0.2, …, 0.9 (9 levels), cap 150, seeds 1–3 | gradient | 27 | 405 | 27 | 324 |
| λ = 1, cap 150, seeds 1–3 | **negative control** (complete confounding) | 3 | 405 | 3 | 36 |
| λ = 0, 0.1, …, 1 (11 levels), no cap, seed 1 | sensitivity to the cap (decision D9), including its own positive / negative control | 11 | 505 | 11 | 132 |
| `L11_single_dx` | **literal negative control** (the 11 real single-diagnosis batches) | 1 | 2,068 | 1 | 12 |
| **Total WP6** | | **45** | | **45** | **540** |

**B. Leave-cohort-out validation (WP7; 30 methods, decision D8 + gate G3)**

| Scenario | Folds | Subsets (train + test) | Train size (approx.) | Preparations | Harmonizations |
|---|---|---|---|---|---|
| C RNA-seq only | 5 | 10 | ≈ 1,800 | 10 | 300 |
| K FFPE only | 5 | 10 | ≈ 2,400 | 10 | 300 |
| J FF only | 5 | 10 | ≈ 2,500 | 10 | 300 |
| S0 all | 5 | 10 | ≈ 5,700 | 10 | 300 |
| **Total WP7** | **20** | **40** | | **40** | **1,200** |

**Grand total of new compute:** 85 preparations, **1,740 harmonizations** and 1,740 metric jobs, plus
the 2,234 reanalysis metric jobs of WP8 (bridging-batch check, §6.1).

### 6.3 Order, pilots and gates

1. **Gradient pilot** (WP6 step 6.7): λ ∈ {0, 1} × seed 1 × cap 150 × 12 arms = 24 jobs (the capped
   positive and negative controls). Checks: run time, the `*_nocov` wrappers (SVA / ComBat without
   the covariate), the singular design of the covariate arms at λ = 1.
2. **Leave-cohort-out pilot** (WP7 step 7.4): strategy C fold 1, train + test × 31 methods = 62 jobs.
   Checks: run time per method, failure modes; the fallback of decision D8 (drop the methods with a
   median main-benchmark run time > 30 min) is decided here.
3. **Pilot metrics** on the metrics pod: `r12_revision_metrics.py --pilot` for the 86 pilot runs.
4. **Gate G3** (pilot review): Daniil approves the run times, the D8 fallback and the nocov wrappers.
5. **Full gradient** (the remaining 516 harmonizations of WP6). Small n, but more than twice the jobs
   of the former 0.25 grid; expected within 1–2 days on the benchmark pod.
6. **Full leave-cohort-out validation**, smallest scenario first: C → K → J → S0 (1,200 − 59 pilot
   jobs). The S0 train folds (~5,700 × 3,447) dominate the time. The main benchmark took ~days for
   1,716 jobs, so expect 1–3 days; the pilot gives the real estimate.
7. **Metrics** on the metrics pod: `r12_revision_metrics.py` for both experiments, then WP8
   (`r30_bridging_subset_metrics.py`, does not harmonize).

Dispatchers: `r11_run_gradient.py` and `r21_run_v1.py`, both with `--pilot`, `--skip-if-exists`,
`--dry-run`, `--n-workers` and `--memory-limit-gb`; `r21` also `--scenario` and `--fold`. Metric
dispatcher: `r12_revision_metrics.py --experiment {gradient,leave_cohort_out}` with the same flags.
Pods: the benchmark pod image for preparation and harmonization, the metrics pod for metrics. Only one
pod at a time can mount the PVC `fl-a3-scratch` (project CLAUDE.md, Infrastructure), so
the two pods run **in sequence**: all harmonizations of a step first, then their metrics. Every input
and output goes through S3, so nothing has to be moved between the pods. §7 gives every command.

### 6.4 Storage

S3 prefix: `s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/{gradient,v1,bridging}/`.
The home disk is 125 GB and slow (15–20 MB/s): harmonized matrices stay on S3, and only metric tables
come back. Use `ensure_local()` for anything offloaded. Pod logs go to `/workspace/revision/` on the
PVC, so they survive a pod crash.

> **2026-11-01 note** (plan `revision_pod_without_pvc_plan_261101.md`): while the annotation 3.0 pod
> holds the PVC, the harmonization pod runs from `k8s/pod-revision-nopvc.yaml` (node-local
> `emptyDir`, may run next to the a3 pod); its `log-sync` container saves the logs on S3
> `revision_261029/pod_logs/<pod>_<start>/`. The "one pod at a time" rule below applies only to
> pods that mount the PVC.

---

## 7. Running the pods from the Mac (step by step)

This section is also written to `article_1_revision/RUNBOOK.md` during implementation, so that it
can be opened on the Mac next to the terminal. All commands run **on the Mac** in the repository clone
`~/FL_harmonization`, unless a block says "inside the pod". Namespace: `${K8S_NAMESPACE}`.

> **2026-11-01 note** (plan `revision_pod_combobatch_image_plan_261101.md`): the ECR image
> `fl-batch-correction:latest` is NotFound; both revision manifests run on
> `ghcr.io/nikit357/combobatch:20260830` (environment only, frozen code copied in), `20_shambhala`
> runs `Nikit357/Shambhala2_fast` @ `30ac312` (the published implementation) through
> `revision_lib.shambhala_fast`, and the pilot metrics run in the same PVC-free pod.

**Two pods are used, never at the same time:**

| Pod | Manifest | Image | What runs there | How you get in |
|---|---|---|---|---|
| `fl-revision` (harmonization) | `article_1_revision/k8s/pod-revision.yaml` (a copy of `harmonization-scripts/k8s/pod.yaml` with the new name) | ECR `fl-batch-correction:latest` (R + sva + batchelor + FSQN pre-installed, starts in minutes) | `r11_run_gradient.py`, `r21_run_v1.py` | `kubectl exec` (the image has no SSH server); files are copied with `kubectl cp` / `tar` |
| `fl-metrics` (metrics) | `harmonization-metrics-calculation/k8s/pod-metrics.yaml` (unchanged) | `ubuntu:24.04`, installs R packages at start-up (10–20 min) | `r12_revision_metrics.py`, `r30_bridging_subset_metrics.py` | SSH through a port-forward, files synced with `rsync` |

### 7.1 One-time checks (before the first launch)

```bash
# 1. kubectl talks to the cluster
kubectl get pods -n ${K8S_NAMESPACE}

# 2. The two Secrets exist (create them only if missing; commands in harmonization-scripts/k8s/CLAUDE.md
#    and harmonization-metrics-calculation/CLAUDE.md, "Pod Operations")
kubectl get secret aws-credentials ssh-pubkey -n ${K8S_NAMESPACE}

# 3. The PVC exists (the only one since 2026-10-29)
kubectl get pvc fl-a3-scratch -n ${K8S_NAMESPACE}

# 4. The AWS CLI works on the Mac (used only to watch the S3 outputs)
aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/ | head
```

### 7.2 Before every launch: fresh code and a free volume

```bash
cd ~/FL_harmonization
git pull --rebase origin main        # brings the revision scripts, designs.tsv and folds.tsv from JupyterHub
ls article_1_revision/r11_run_gradient.py article_1_revision/output/wp6/designs/designs.tsv

# Nothing else may mount the PVC. Look for other project pods (annotation 3.0 processing,
# metrics, the other revision pod):
kubectl get pods -n ${K8S_NAMESPACE} | grep fl-
kubectl describe pvc fl-a3-scratch -n ${K8S_NAMESPACE} | grep -A3 "Used By"
# If another pod is listed and its work is finished, delete it (the PVC data stay):
#   kubectl delete pod <that-pod> -n ${K8S_NAMESPACE}
```

### 7.3 Harmonization pod: launch and copy the code

```bash
# Node size: the manifest requests 8 vCPU / 16 GiB, enough for the gradient (405-sample designs).
# For the leave-cohort-out S0 train folds (~5,700 samples), edit `resources` in
# article_1_revision/k8s/pod-revision.yaml before applying: use the size agreed at gate G3
# (the main benchmark ran on 16 vCPU / 240 GiB).
kubectl apply -f article_1_revision/k8s/pod-revision.yaml -n ${K8S_NAMESPACE}
kubectl get pod fl-revision -n ${K8S_NAMESPACE} -w      # wait for Running, then Ctrl-C

# Copy the revision folder into the pod (scripts, k8s, tests, designs, folds; not the large outputs)
tar -C ~/FL_harmonization -cf - \
    --exclude='article_1_revision/cache' --exclude='article_1_revision/Revised_manuscript' \
    --exclude='article_1_revision/figures_svg' --exclude='*.parquet' \
    article_1_revision \
  | kubectl exec -i fl-revision -n ${K8S_NAMESPACE} -- tar -xf - -C /app

# The image carries its own copy of the frozen bench_shared.py. Check that it is the frozen version:
kubectl exec fl-revision -n ${K8S_NAMESPACE} -- md5sum /app/harmonization-scripts/bench_shared.py
grep bench_shared article_1_revision/FROZEN_MD5.txt
# If the two sums differ, copy the frozen file in:
#   kubectl cp harmonization-scripts/bench_shared.py \
#       ${K8S_NAMESPACE}/fl-revision:/app/harmonization-scripts/bench_shared.py
```

### 7.4 Harmonization pod: pilots

```bash
kubectl exec -it fl-revision -n ${K8S_NAMESPACE} -- bash -l
```

Inside the pod:

```bash
cd /app/article_1_revision
mkdir -p /workspace/revision
python -m pytest tests/test_revision_lib.py -q                 # toy checks must pass first
python r11_run_gradient.py --pilot --dry-run                   # must list 24 jobs
python r21_run_v1.py --pilot --dry-run                         # must list 62 jobs

# Start the gradient pilot in the background; setsid + nohup keep it alive after you leave the shell
setsid nohup python r11_run_gradient.py --pilot --skip-if-exists --n-workers 4 \
    > /workspace/revision/gradient_pilot.log 2>&1 &
exit
```

Back on the Mac, watch the progress:

```bash
kubectl exec fl-revision -n ${K8S_NAMESPACE} -- tail -n 20 /workspace/revision/gradient_pilot.log
aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/revision_261029/gradient/ \
    --recursive | wc -l                                         # grows as jobs finish
```

When the gradient pilot has finished (the log ends with its summary line), start the leave-cohort-out
pilot the same way (`r21_run_v1.py --pilot --skip-if-exists --n-workers 4 >
/workspace/revision/v1_pilot.log`). The two pilots are run one after the other so that their run
times are measured cleanly. Then delete the pod:

```bash
kubectl delete pod fl-revision -n ${K8S_NAMESPACE}
```

### 7.5 Metrics pod: pilot metrics

```bash
kubectl apply -f harmonization-metrics-calculation/k8s/pod-metrics.yaml -n ${K8S_NAMESPACE}
kubectl logs -f fl-metrics -n ${K8S_NAMESPACE}
# wait for "[startup] Metrics environment ready." (10–20 min), then Ctrl-C

# Terminal 2 (keep it open): SSH port-forward
kubectl port-forward pod/fl-metrics 2222:22 -n ${K8S_NAMESPACE}

# Terminal 1: sync the two folders the metrics need (whole folders, not *.py:
# group L needs marker_gene_annotation.csv)
for d in harmonization-metrics-calculation article_1_revision; do
  rsync -avz --progress --exclude='cache/' --exclude='Revised_manuscript/' --exclude='*.parquet' \
      -e "ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
      ~/FL_harmonization/$d/ root@localhost:/app/$d/
done
ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@localhost
```

Inside the pod:

```bash
cd /app/article_1_revision
mkdir -p /workspace/revision
python r12_revision_metrics.py --pilot --dry-run               # must list 86 jobs (24 + 62)
setsid nohup python r12_revision_metrics.py --pilot --skip-if-exists \
    --n-workers 8 --memory-limit-gb 8.0 \
    > /workspace/revision/metrics_pilot.log 2>&1 &
exit
```

Set `--n-workers` to about (vCPU − 8) of the node that was provisioned (metrics CLAUDE.md). The
metric tables are written to S3; the analysis scripts on JupyterHub read them from there. When the
log ends, delete the pod (`kubectl delete pod fl-metrics -n ${K8S_NAMESPACE}`) and tell
Claude on JupyterHub that the pilot is done: the pilot report for **gate G3** is built there.

### 7.6 Full runs (after gate G3)

The same two cycles, with the pilot flags removed:

1. **Harmonization pod** (§7.2 → §7.3, with the node size agreed at G3): inside the pod
   - `python r11_run_gradient.py --dry-run` → 540 jobs listed (the 24 pilot jobs are skipped by
     `--skip-if-exists`);
   - `setsid nohup python r11_run_gradient.py --skip-if-exists --n-workers <n> > /workspace/revision/gradient_full.log 2>&1 &`;
   - after it ends, the leave-cohort-out runs one scenario at a time, smallest first:
     `python r21_run_v1.py --scenario C --skip-if-exists --n-workers <n> > /workspace/revision/v1_C.log 2>&1`,
     then `K`, `J`, `S0` (`python r21_run_v1.py --dry-run` lists 1,200 jobs in total; commands with the G3 worker counts in `RUNBOOK.md` §6).
     For S0, lower `--n-workers` if the pod is killed for memory (see §7.7).
2. **Delete the harmonization pod.**
3. **Metrics pod** (§7.5): `r12_revision_metrics.py --experiment gradient`, then
   `--experiment leave_cohort_out`, then `r30_bridging_subset_metrics.py` (2,234 jobs, no kBET; the
   longest step), each with `--skip-if-exists` and its own log in `/workspace/revision/`.
4. **Delete the metrics pod.** Tell Claude on JupyterHub; `r13_gradient_stats.py`, `r22_v1_evaluate.py`
   and `r05_robustness.py` run there (gate G4).

Every dispatcher is restartable: if a pod dies, re-launch it, copy the code again and run the same
command; `--skip-if-exists` skips every job whose output is already on S3.

### 7.7 Troubleshooting

| Symptom | Cause | What to do |
|---|---|---|
| Pod stays `Pending` | No node yet (Karpenter is provisioning a `c6a` node) or the request is too large | `kubectl describe pod <pod> -n ${K8S_NAMESPACE}`, read *Events*; wait a few minutes or lower `resources` |
| Pod stuck in `ContainerCreating` with "Multi-Attach error" | Another pod still holds the PVC | Delete the other pod (§7.2), then wait ~1 min |
| `ContainerCreating` with "secret not found" | A Secret is missing | Create it (§7.1) |
| Job log shows exit code 137 / `OOMKilled` | Not enough memory | Lower `--n-workers` or raise the node memory in the manifest; re-run with `--skip-if-exists` |
| `ModuleNotFoundError` in the harmonization pod | The revision folder was not copied, or the wrong folder | Repeat the `tar` copy of §7.3; run from `/app/article_1_revision` |
| `ModuleNotFoundError` in the metrics pod | Start-up not finished or a shell without the venv | Wait for "Metrics environment ready."; use `bash -l` |
| `ssh: connect to host localhost port 2222` refused | The port-forward terminal was closed | Restart `kubectl port-forward …` |
| The pilot dry-run lists another number of jobs than 24 / 62 / 86 | The designs or folds on the Mac are stale | `git pull` again (§7.2) and copy again |

---

## 8. New files to create (all under `article_1_revision/`)

```
CLAUDE.md                                   # operating manual of this folder (hard rules, run order)
README.md                                   # human-facing summary + work-package status
RUNBOOK.md                                  # §7: pod instructions for the Mac
FROZEN_MD5.txt                              # §4
adjudication_rule_261029.md                 # WP4 step 4.1 (frozen after Daniil approves at gate G2;
                                            # a _v2 file only if amended at gate G2b)
response_letter_draft.md                    # WP13 response letter
revision_lib.py                             # wrappers: prepare_subset, sva_nocov, combat_nocov,
                                            # metrics_on_subset, gt_logfc_concordance, four_scores,
                                            # load_baseline_tables, PUBLICATION_NAMES (§1.1),
                                            # s3 helpers (thin, typed, documented)
r00_baseline_ledger.py                      # WP0 step 0.5
r01_confounding_diagnostics.py              # WP1 confounding diagnostics
r02_reduced_panel.py                        # WP2 reduced panel
r03_four_scores.py                          # WP3 four scores
r04_apply_rule.py                           # WP4 steps 4.2–4.3 (+ --review: selection_review.xlsx, gate G2b)
r05_robustness.py                           # WP5 robustness
r10_build_gradient_designs.py               # WP6 step 6.1 (§3.3 definition of λ; 45 designs)
r11_run_gradient.py                         # WP6 steps 6.2–6.4 dispatcher (harmonization pod)
r12_revision_metrics.py                     # WP6 step 6.5 + WP7 step 7.3 metrics (metrics pod;
                                            # --experiment gradient | leave_cohort_out)
r13_gradient_stats.py                       # WP6 step 6.6
r20_build_cohort_folds.py                   # WP7 step 7.1
r21_run_v1.py                               # WP7 step 7.2 dispatcher (harmonization pod)
r22_v1_evaluate.py                          # WP7 step 7.3 evaluation
r30_bridging_subset_metrics.py              # WP8 bridging-batch check (metrics pod)
r40_build_supplementary.py                  # WP10 supplementary tables
r45_results_numbers.py                      # every number quoted in the new text → numbers.json
r50_manuscript_tracked_edits.py             # WP11 manuscript text
r51_reference_audit.py                      # WP12 references (minor comment m5)
r60_response_letter.py                      # WP13 response letter
r90_ledger.py                               # WP14 "nothing grew" ledger
r99_verify.py                               # WP14 validation (incl. the internal-label scan of §1.1)
nb01_confounding.ipynb                      # Fig 1E, Fig 2A fix
nb02_reduced_panel_clustermap.ipynb         # Fig 3 (central clustermap on the panel), S4, S5, S6
nb03_four_scores_and_tree.ipynb             # Fig 6 B, C/D, F; S14
nb04_confounding_gradient.ipynb             # Fig 6 gradient panel; S17
nb05_robustness_and_v1.ipynb                # S16, S18
nb06_merged_distributions.ipynb             # S2 (merged S2–S4)
nb07_selected_approaches_embeddings.ipynb   # PCA / tSNE / UMAP of the rule's picks (G2, 2026-11-03)
k8s/pod-revision.yaml                       # copy of harmonization-scripts/k8s/pod.yaml, pod name
                                            # fl-revision
tests/test_revision_lib.py                  # design feasibility, n_{b,g}(λ) counts on the 0.1 grid and
                                            # V monotonicity (the §3.3 values), panel rule on a toy
                                            # matrix, gt_logfc on simulated data, four_scores shape,
                                            # PUBLICATION_NAMES covers every new column
inputs/  output/wp1..wp8/  figures_svg/  Revised_manuscript/  cache/
```

## 9. Existing files to change (outside the frozen set)

| File | Change |
|---|---|
| `FL_harmonization/CLAUDE.md` | Key Files: add `article_1_revision/` rows; Current Status: add the revision as the Article 1 item; Commands: the revision run order, pointer to `article_1_revision/RUNBOOK.md` |
| `figures_for_article/CLAUDE.md` | One line pointing to `article_1_revision/` as the place of the revision figures and edit script, and to the naming rule (§1.1) |
| `harmonization-metrics/CLAUDE.md` | One line: the reduced panel and the four scores live in `article_1_revision/output/wp2–3` |
| `.gitignore` | `article_1_revision/output/**/*.parquet` > 50 MB, `article_1_revision/cache/`, `.brainstorm/` (already present) |
| `s3_offload/offload_groups.tsv` | A group for the large revision outputs, if any exceed 50 MB |
| Memory | `project_nargab_revision.md`: decisions D1–D9 (λ in 0.1 steps), the λ definition, the frozen rule and gate G2b, the plain-word naming rule, the folder, tracked-only (no red copy for now) |

## 10. Files that do NOT need to change

- **All frozen files (§4).** They are imported, never edited. That includes `bench_shared.py`: no new
  methods are registered, because the `*_nocov` arms live in `revision_lib`.
- `harmonization-scripts/k8s/*`, `harmonization-metrics-calculation/k8s/pod-metrics.yaml`, the Docker
  image: the existing benchmark image has R + sva + batchelor. The revision scripts are **copied into
  the pod from the Mac** (§7.3, §7.5); the repository is private and the image holds no git
  credentials. No rebuild is needed, unless the pilot shows a missing package.
  (2026-11-01: that ECR image is NotFound; the pods use the ComboBatch image
  `ghcr.io/nikit357/combobatch:20260830` — plan `revision_pod_combobatch_image_plan_261101.md`.)
- `cohort_2_0/**`, h230 (Article 2 harmonization): only the cohort-level cross-validation logic is
  reused (by reading it), not the code. h230 targets expression 2_3_0 and the ComboBatch package, not
  the Article 1 tables.
- `harmonization-metrics/correlation_prediction_metrics_analysis*.ipynb`: their L/M/N outputs are
  read as they are.

## 11. Side effects and caveats

- **C1. Sunk cost / anchoring.** The rule is written and frozen *before* r04 runs. Daniil sees its
  picks at gate G2b; any amendment after that is versioned and reported (WP4 step 4.2b). If the set
  changes, decision D5 applies, and the abstract and the title claim (FSQN, SVA) are re-checked. The
  title itself may need to change. That is a Daniil + Arsen decision at gate G4.
- **C2.** A flat gradient slope can mean robustness or a lack of power (n = 405, 3 replicates per λ,
  11 λ levels). The criterion in WP6 step 6.6 is fixed now.
- **C3.** At λ = 1, the covariate methods fail or fall back; at λ ≥ 0.7, the smallest batch keeps only
  1–2 samples of its non-assigned diagnoses. Report this as a result.
- **C4.** Leave-cohort-out validation on strategy K (FFPE only) is close to leave-batch-out (§3.4).
  Test folds may lack a diagnosis group; then the prediction gate is "not evaluable" on that fold, not
  a failure.
- **C5.** The four scores' headline metrics are known only after WP2 (reduced panel). The names in
  WP3 are expectations.
- **C6.** Every Supplementary Figure number moves. The sweep must be collision-safe (figures
  CLAUDE.md), and the response letter refers to the **new** numbers.
- **C7.** `metrics_comprehensive_260527.csv` is unusable. Read Supplementary File 3 / 260609 through
  the documented loaders only.
- **C8.** The Mendeley bibliography is refreshed by Daniil. Run `r99` **after** that refresh.
- **C9. Red copy.** NARGAB asks for the changes in red. For now only the tracked docx is produced
  (Daniil, 2026-10-29). Before submission, Daniil decides whether a red copy is needed; it is not part
  of this plan.
- **C10.** The length constraint is checked on the accept-all text. The new Methods / Results
  paragraphs must be paid for by the deletions in WP11 (manuscript text). If `r90` fails, shorten
  before adding. A possible rule amendment at gate G2b is reported in the response letter, not in the
  manuscript, for the same reason.
- **C11.** λ changes the within-batch composition, not the batch sizes; the diagnosis totals move
  slightly (135 / 135 / 135 → 150 / 123 / 132, §3.3). The Methods state this, so that a reader does
  not take the gradient for a class-imbalance experiment.
- **C12. Compute.** The 0.1 λ grid more than doubles the gradient jobs (252 → 540). The jobs are small
  (405 samples), so the gradient still takes 1–2 days; leave-cohort-out validation remains the
  dominant cost.

## 12. Verification commands

```bash
source ~/venvs/collagen_3_11/bin/activate
cd ~/FL_harmonization/article_1_revision
md5sum -c FROZEN_MD5.txt                                   # frozen code, baseline and approved rule untouched
pytest tests/test_revision_lib.py -q                       # toy checks
python r02_reduced_panel.py --check                        # 9 groups covered; 1,993 complete approaches
python r10_build_gradient_designs.py --dry-run             # 45 designs; batch sizes equal across λ; V strictly rising (0 … 0.998, §3.3)
python r11_run_gradient.py --pilot --dry-run               # 24 pilot jobs listed
python r11_run_gradient.py --dry-run                       # 540 jobs listed
python r21_run_v1.py --pilot --dry-run                     # 62 pilot jobs listed
python r21_run_v1.py --dry-run                             # 1,200 jobs listed
python r12_revision_metrics.py --pilot --dry-run           # 86 pilot metric jobs listed
python r90_ledger.py                                       # exit 0: nothing grew
python r99_verify.py Revised_manuscript/<tracked>.docx     # full validation, incl. the internal-label scan
S=~/FL_harmonization/.claude/skills/nar_review_tools.py
python $S validate Revised_manuscript/FL_harmonization_article_NARGAB_baseline_260912.docx Revised_manuscript/<tracked>.docx
```

## 13. Gates (Daniil decides at each one)

Review document with the facts, options and an answer sheet for every gate:
`gates_review_261102.md` (2026-11-02).

| Gate | After | What Daniil (and Arsen) approve |
|---|---|---|
| G0 | this plan | the plan (decisions D1–D9 already answered) |
| G1 | WP2 reduced panel | the reduced panel (the list of metrics, the tie-breaks), the four headline metrics — **answered 2026-11-03** (22 metrics; Q1 answered) |
| G2 | WP4 step 4.1 | the written selection rule (then frozen) — **answered 2026-11-03** (incl. Q1 / Q2); **frozen 2026-11-03** |
| G2b | WP4 step 4.2b | **which approaches the rule selects** (`selection_review.xlsx`: front per scenario vs the submitted visual picks, Table 3 and Figure 6F previews, leave-strategies-out result); accept, or amend the rule as a logged version 2 |
| G3 | the two pilots (WP6 step 6.7, WP7 step 7.4) + pilot metrics | run times; the D8 fallback (drop slow methods); the nocov wrappers; the node size for the full runs — **answered 2026-11-03** |
| G4 | WP4 step 4.3 + WP5 + WP6 + WP7 | the results: is the best set unchanged? Leave-strategies-out outcome; Abstract / title / tree changes |
| G5 | `response_letter_draft.md` | the response wording (Arsen reads too) |
| G6 | WP11 output | the tracked manuscript; the ledger; the internal-label scan |

## 14. TODO

### Phase 0 — setup
- [x] Create the folder layout (§8) and `.gitignore` entries (2026-10-31; `output/wp8/*.parquet` ignored, the rest is small)
- [x] `FROZEN_MD5.txt` for the §4 files (32 files; paths relative to this folder); commit
- [x] Copy the baseline docx and Supplementary Files 1 / 2 / 3 to `inputs/` / `Revised_manuscript/` (read-only, `chmod 444`)
- [x] `nar_review_tools.py fields` + `extract` on the baseline → `inputs/baseline_dump.txt` (+ `inputs/baseline_fields.txt`). Measured: **82** `w:sdt` (not 118), 0 `w:fldChar`, 12 hyperlinks
- [x] `r00_baseline_ledger.py` → `output/ledger_baseline.tsv` + `ledger_baseline_totals.json` (16,495 words; 6 figures, 3 tables, 19 supplementary figures, 3 supplementary files; lines estimated as ceil(chars / 90))
- [x] Clarify `Supplementary File 4.csv`: an older 229-row metric-polarity table (the submitted File 2 sheet `Metric_polarity` has 344 rows); the submitted package `supplementary_260824/` holds Files 1–3 only → unsubmitted leftover, ignored
- [x] `revision_lib.py` (incl. `PUBLICATION_NAMES`, `METHOD_DISPLAY_NAMES`, `STRATEGY_DISPLAY_NAMES`) + `tests/test_revision_lib.py` (77 tests pass)
- [x] `article_1_revision/CLAUDE.md` + `README.md` + `RUNBOOK.md` (§7)

### Phase 1 — reanalysis of existing tables (no new harmonization, §6.1)
- [x] WP1 `r01_confounding_diagnostics.py` (2026-10-31; S0: bias-corrected V batch × diagnosis 0.358, AMI 0.263, V batch × major group 0.495; 11 single-diagnosis batches, 2,068 samples; 18 bridging batches, 5,106 samples, 1 connected component; variance partition median per-gene R² batch 0.743 / diagnosis 0.070 / shared 0.037; step 1.4 inset computed by r03: Spearman ρ −0.20 / 0.07, n = 14, not significant)
- [x] WP2 `r02_reduced_panel.py` (+ cut 0.1 / 0.3, all-87 variants): first build 33 metrics → 23 clusters → 25-metric panel; **gate G1 answered 2026-11-03**: tSNE centroid dispersion excluded, no coverage additions → 32 metrics → 22 clusters → **22-metric panel** (group H through cluster mates); 1,993 complete approaches (1,354 on all 87); 2 tie-breaks accepted; Figure 3 re-rendered with black missing cells
- [x] WP3 `r03_four_scores.py`: L = `mk_rho_mean_all_genes_narrow_set`, N = `pv_lobo3_f1_macro_mean` (n_perm 100); 84 approaches without L / N, all `20_shambhala`; headlines PCReg_RNA_BATCH / PCReg_Diagnosis / kBET RNA_BATCH / graph connectivity Diagnosis (the two local bars are medoid ties, broken by simplicity — part of gate G1)
- [x] WP3 re-run after G1 / G2 (2026-11-03): 22-metric panel; Global-biology headline kept as PC regression on diagnosis (`HEADLINE_OVERRIDES`; the medoid would now be WaterMelon mean biology; Q1 answered: keep PC regression); Shambhala L / N taken from the blind-check rows `shambhala_P0std_Q0std` (same matrices; 84 L, 83 N); N2 (2-class DLBCL vs FL) columns; `identical_to_raw` (111 approaches: exploBATCH 49, RUV-III-PRPS 27, DWD 19, FSQN R 10, SVA 6; Q2 answered: every method); runner-up local bars for r05
- [x] WP4 step 4.1: `adjudication_rule_261029.md` → **gate G2** → freeze (MD5) — *G2 answered 2026-11-03; final text written (Shambhala included, 2-class gate N for D, step 1b method failure, version-2 criterion, plots of the picks); Q1 / Q2 answered 2026-11-03; **frozen 2026-11-03** (MD5 `17d4fe01454d3485a72434f7cec17bb6` in `FROZEN_MD5.txt`; the Mac freeze `b192bb…` differed only in the status header — the 2026-11-03 merge kept this text and the MD5 line was corrected)*
- [x] WP4 step 4.2: `r04_apply_rule.py` → selection + concordance with the visual pick — *run 2026-11-03 on the Mac: fronts FF 8, FFPE 5, RNA-seq 8, multi-platform 12, microarrays (not a leaf) 13; vs submitted Table 3: 3 kept, 12 lost, 26 new (`output/wp4/rule_vs_visual_concordance.tsv`)*
- [x] WP4 step 4.3: leave-strategies-out check (A, B, E1–E3 removed from the pool; FSQN R rank and front membership with / without; interpretation as fixed in step 4.3) — *run inside r04 2026-11-03: multi-platform pool 1,266 → 476 candidates, FSQN R on the front in both (rank 2 → 1); `output/wp4/leave_strategies_out.tsv`*
- [ ] WP4 step 4.2b: `r04_apply_rule.py --review` → `selection_review.xlsx` (picks per scenario vs Table 3, Table 3 and Figure 6F previews) → **gate G2b** (accept, or amend as a logged v2) — *review files written 2026-11-03 (`output/wp4/selection_review.xlsx` + `.md`). G2b partly answered 2026-11-03 (`gates_review_261102.md` §4.1): picks of version 1 approved (no version 2); new information-only pool "No batch removal (S0 only)" (both post-removal settings; front 7: Angel × 5, ComBat, M-ComBat) and the leave-strategies-out sheet now lists every method on either front (r04 re-run); round-1 vetoes answered 2026-11-04 (`gates_review_261102.md` §4.3: 17 accepted, 34 vetoed, 2 without comment → `output/wp4/visual_check.tsv` + `vetoes.tsv`); r04 now keeps `selection_by_rule.tsv` blind (no veto) and writes the front without the vetoed approaches to `selection_after_visual_check.tsv` (column `visual_check`): 28 approaches entered the fronts and were never shown → nb07 round 2; open: round-2 decisions, the 2 uncommented members, the multi-platform leaf assignment; veto reasons drafted for the main text (`stage_b_text_drafts.md` D-1, r50 item 11)*

### Phase 2 — new harmonizations and pod metrics (§6.2–§6.3; commands in §7)
- [x] WP6 step 6.1: `r10_build_gradient_designs.py` (45 designs: 33 capped, 11 uncapped, 1 single-diagnosis-batch control; all assertions pass; V cap 150 r1 = 0, 0.014, 0.169, 0.287, 0.388, 0.490, 0.592, 0.690, 0.799, 0.896, 0.998; committed)
- [x] WP7 step 7.1: `r20_build_cohort_folds.py` (+ fold summary; committed). J and S0: all test folds meet the constraints; C and K: 2 test folds each are one large single-batch, single-diagnosis cohort (C 553 / 567, K 553 / 810) — reported, not forced (caveat C4)
- [x] `revision_lib.prepare_subset`, `sva_nocov`, `combat_nocov`, `metrics_on_subset`, `gt_logfc_concordance` (`sva_nocov` / `combat_nocov` need R: first real test in the gradient pilot)
- [x] `k8s/pod-revision.yaml`; `r12_revision_metrics.py`; plus the dispatchers `r11_run_gradient.py`, `r21_run_v1.py` (worker `r19_harmonize_one.py`, shared runner `revision_dispatch.py`) and `r30_bridging_subset_metrics.py`. Dry-runs: 24 / 62 / 86 pilot jobs, 540 / 1,240 (1,200 since G3) / 2,234 full jobs. End-to-end smoke test on JupyterHub (scratch S3 prefix `revision_261029_smoketest/`, R-free arms) passed: 304 metric keys, no group errors; fixed on the way: published names `PCReg_*` / `pct_*_allNA` added by `revision_lib.add_published_names`; group D took 1,197 s on one busy core → `r12 --groups` lets G3 drop it
- [x] Gradient pilot (24 jobs) and leave-cohort-out pilot (62 jobs) on the harmonization pod, pilot metrics on the same PVC-free pod (§7.4–§7.5) → **gate G3** *(done 2026-11-01/02: env check OK; gradient 24 / 24 (ComBat with covariate fails at λ = 1, expected); leave-cohort-out 62 / 62 = 59 ok + AMDBNorm timeout (train, 2 h) + exploBATCH × 2 failed (fMM gone); metrics 82 / 82 ok. `r14_pilot_report.py --workers 8` run 2026-11-02 → `output/wp6/pilot/`; G3 questions in `gates_review_261102.md` §5 (r14 misses timed-out runs in the slow list; SVA silently returned raw data in 2 runs)*
- [x] Gate G3 answered 2026-11-03: full runs; every method kept (AMDBNorm, HarmonizR, Shambhala with a **6 h timeout**, a timed-out run is written to S3 as a "timeout" record and skipped); exploBATCH dropped from leave-cohort-out (fMM missing in the image, confirmed in the pilot record); SVA fallbacks reported as method failures (r13 / r22); one **48-vCPU / 96-GiB node** (44 CPU / 80 GiB requested) for every computation; group D kept → RUNBOOK §6
- [x] WP6 full run (540: positive control, 0.1-step gradient, negative control, uncapped sensitivity, 11-batch control; 516 left after the pilot) (RUNBOOK §6) — *launched 2026-11-03 from the Mac, PVC-free pod on the 48-vCPU node; finished 2026-11-03 15:58 UTC: 516 jobs, 515 ok, 1 timeout (`L11_single_dx__33_amdbnorm`, 6 h)*
- [x] WP7 full run (1,200 = 30 methods; 1,141 left after the pilot; C → K → J → S0) (RUNBOOK §6) — *queued behind WP6 in the same pod command; C finished 2026-11-04 00:04 UTC (241: 239 ok, 2 AMDBNorm timeouts), K finished 2026-11-04 12:28 UTC (300: 292 ok, 8 timeouts = 7 AMDBNorm + 1 Shambhala), J finished 2026-11-04 ~18:50 UTC (300: 300 ok), S0 started 18:53 UTC, worker container OOMKilled 2026-11-04 20:06 UTC after 19 / 300 S0 jobs (10 concurrent S0 jobs + 13 GB of orphaned K Shambhala workers > 80 GiB; metrics chain died with it) → relaunched 2026-11-05 05:54 UTC with 5 workers / 20 GB (RUNBOOK §6.2); that pod vanished at 08:45 UTC after 81 / 300 S0 jobs (no OOM in the logs; manifest now has `karpenter.sh/do-not-disrupt`) → second relaunch 2026-11-05 ~11:56 UTC; S0 finished 2026-11-06 07:32 UTC (219 run: 211 ok, 8 AMDBNorm timeouts; every S0 AMDBNorm subset run here timed out at 6 h, the other 2 were done before this run). WP7 done; metrics chain started 07:32 UTC*
- [x] Metrics of both experiments (`r12_revision_metrics.py`) and WP8 `r30_bridging_subset_metrics.py` (2,234; no re-harmonization) on the metrics pod (§7.6) — *chained in the same pod (waits for the harmonization shell, then gradient → leave-cohort-out → bridging; gradient metrics 2026-11-06 07:32–09:51 UTC: 511 / 511 ok; leave-cohort-out metrics 09:51–20:40 UTC: 1,013 / 1,013 ok (227 of 1,240 have no matrix: timeouts); bridging 20:40–22:05 UTC: 2,234 / 2,234 ok. All pod steps done; logs on S3 `pod_logs/fl-revision_261105_1155/`. Next on JupyterHub: `r12 --concat` (both experiments), `r30 --concat`, `r13`)*
- [x] WP6 step 6.6 `r13_gradient_stats.py`; WP7 step 7.3 `r22_v1_evaluate.py`; WP5 `r05_robustness.py` — *code written and toy-tested 2026-11-01 (`tests/test_analysis_scripts.py`, 8 tests; shared helpers `revision_lib.pareto_layers / rule_order / bar_scaling_reference / score_runs`: new runs are scaled on the main-benchmark range). r05 and r22 refuse to run until the rule MD5 is frozen; r13 waits for `gradient_metrics.parquet`. Real-data V on the 5 gradient batches = 0.398*
- [x] Run r13, r22, r05 on the pod results → **gate G4** — *2026-11-07 on JupyterHub: `r12 --concat` (gradient 540: 534 ok / 6 failed; leave-cohort-out 1,202: 1,072 ok / 130 failed or timed out), `r30 --concat` (2,234 ok), r13 (105 of 184 slopes meaningful), r22 (chosen top-3 in 6 / 20 folds, 5 / 16 evaluable; random 11.6 %; submitted tree 8 / 30; chosen method failed on the test part in 4 folds), r05 incl. bridging (median τ 0.86; bridging 0.92). Facts and G4 questions: `gates_review_261102.md` §6. **2026-11-07: G2b closed after round 2** (r04 `VISUAL_CHECK_CLOSED`, 22 approaches; `leaf_assignment.tsv`) → r04, r05, r40, r45 re-run (§16)*

### Phase 3 — figures (notebooks → SVG / PDF / PNG; labels from `PUBLICATION_NAMES`)
- [x] `nb01_confounding.ipynb` (Fig 1E; Fig 2A with D under biology) — *2026-11-01*
- [x] `nb02_reduced_panel_clustermap.ipynb` (Fig 3: central clustermap rebuilt on the reduced panel; S4, S5, S6) — *2026-11-01; provisional until G1; rule marks filled on re-run after r04*
- [x] `nb03_four_scores_and_tree.ipynb` (Fig 6 B, C/D, F; S14) — *2026-11-07: 6B η², 6C/D dot matrix of the front after the vetoes with λ = 0 / 1 gradient medians, 6F tree (accepted approaches + readouts; first proposal), S14a–c; re-run after G2b round 2*
- [x] `nb04_confounding_gradient.ipynb` (Fig 6 gradient panel over 11 λ levels; S17) — *2026-11-07: `fig6_gradient_panel`, S17a (12 arms × 8 scores), S17b (slopes), S17c (14-strategy inset); `KEY_ARMS` to confirm at G4*
- [x] `nb05_robustness_and_v1.ipynb` (S16, S18) — *2026-11-07: S16a–b, S18a–c; re-run after r05 is re-run for G2b round 2*
- [ ] `nb07_selected_approaches_embeddings.ipynb` — PCA / tSNE / UMAP of the rule's picks drawn like Figures 4–5 and S11–S17 (Daniil, G2 2026-11-03) — *written 2026-11-03; first run on the Mac (4 picks × 4 leaves → `figures_svg/picks_*`, now superseded). Rewritten 2026-11-03 for G2b (Daniil): every front member of all six pools (53 approaches) as unharmonized | harmonized pairs, rows batch / diagnosis (+ platform), batches removed by post-removal faint (full pre-removal matrix embedded) → `figures_svg/g2b_review/*.pdf`, `output/wp9/nb07_removed_batches.tsv`; 2026-11-04: switch `REVIEW_ROUND` (2 = only the approaches that entered the fronts after the round-1 vetoes → `figures_svg/g2b_review_round2/`, tables `…_round2.tsv`)*
- [x] `nb06_merged_distributions.ipynb` (S2) — *2026-11-01*
- [ ] `figures_svg/PLACEMENT.md`; Daniil assembles the multi-panel pages — *started 2026-11-01 (nb01, nb02, nb06 rows); nb03–nb05 rows added 2026-11-07 (nb02 re-run: Figure 3 marks the 33 blind rule picks); assembly: Daniil*
- [ ] `nar_review_tools.py figures` legibility check on the assembled PDFs

### Phase 3b — requests of the G4 package review (Daniil, 2026-11-07; §16)
- [x] Article palettes (`method_pal`, `strat_pal`) in nb03, nb04, nb05 (gradient panel, S14, S16, S17, S18, 6C/D, 6F)
- [x] S16a as bar plots (median over the 6 pools, range, pool dots) — rank stability vs top instability
- [x] r13: Spearman ρ (score vs V), p, Benjamini–Hochberg FDR, `significant_fdr`, `changes_with_confounding` (FDR < 0.05 AND the 2 × SD criterion); S17b markers use the combined flag
- [x] r13: `gradient_ranks.tsv` (rule rank of every arm in every design) → S17e rank trajectories; S17f scores of the selected methods; S17d λ scatter (approved; added as a panel, S17a kept)
- [x] nb04 failure table with plain-word reasons (`output/wp9/nb04_gradient_failures.tsv`)
- [x] Supplementary File 3: columns "Method failed: returned its input unchanged", "Visual check of the rule's front (revision)", "Recommended (rule front, accepted at the visual check)"
- [x] Optional (Daniil decides, §9 of the review): Angel and M-ComBat as gradient arms (pod run, 2 × 45 harmonizations + metrics) *(decided yes at G4; pod run done 2026-11-08)*
- [ ] Remaining figure notebooks to the palettes on their next run: nb01 / nb06 (strategy colours already from `strat_pal`) — *nb02 done 2026-11-08: Figure 3 metric groups in the pastel Set3 `group_pal`, Post-removal + Harshness column bars (Daniil, P5 comment)*

### Phase 4 — supplementary tables
- [ ] `r40_build_supplementary.py`: File 1 (+2 plain-word columns), File 2 (new columns / row), File 3 (xlsx, 3 sheets with plain-word names: 2,407 / 540 / 1,200 rows; size check) — *script done 2026-11-01, run: File 1 (sample counts per cohort, since File 1 is per cohort), File 2, File 3 main sheet (2.3 MB) built; gate results, rule picks, bridging column, gradient and leave-cohort-out sheets fill on re-run (`output/wp10/build_status.tsv`); **re-run 2026-11-07: every part filled** (File 3 2.5 MB; fixed: the gradient sheet reads the design's `n_samples_y`)*
- [ ] Table 1 and Table 3 column contents → `numbers.json`

### Phase 5 — text
- [ ] `response_letter_draft.md` (point by point; plain-word names; rule amendment reported if any) → **gate G5** — *draft written 2026-11-01 with `{{key}}` numbers and [PENDING] markers for the pod / rule results*
- [x] `r45_results_numbers.py` → `numbers.json` — *2026-11-07: **124 ready, 0 pending** (fixed: the hit columns of `v1_fold_results.tsv` hold NaN for chosen methods that failed on the test part; new keys `v1_chosen_failed_on_test`, `v1_n_evaluable_folds`, `v1_top3_hits_evaluable`); re-run after G2b round 2. Earlier: script done 2026-11-01: 63 ready, 5 pending; also writes `output/wp3/eta_squared.tsv` (reduced panel: method 0.361, strategy 0.264, imputation 0.011, post-removal 0.002; the 87-metric check reproduces the submitted 0.3629 / 0.2564 / 0.0155 / 0.0020)*
- [ ] `r50_manuscript_tracked_edits.py` — *stage A done 2026-11-01 (results-independent: terminology sweep 71 hits, 33 / 31 methods in ¶13 + ¶82, Table 1 D → By biology, Fig 4F legend, ¶141 / 149 / 151 / 153 deleted; 184 revisions; reject-all = baseline, 82 w:sdt unchanged); stage B (23 items in the docstring) waits for results* — in this order: deletions (composite) → rewrites → new paragraphs (incl. the formal λ definition with 11 levels in Methods) → tables → legends → S-figure renumbering sweep → terminology sweep
- [x] `r90_ledger.py` passes (nothing grew) — *stage B 261108: words 16,495 → 14,913, lines 1,545 → 1,420, 18 supplementary figures, PASS*
- [ ] `r51_reference_audit.py` → checklist; Daniil fixes in Mendeley and refreshes; `r51` reports 0 — *script done 2026-10-31: 12 items on the baseline (`output/wp12/reference_audit.tsv`): Pedregosa all-caps, Kappal URL, "team T pandas development", 8 entries without a publication year, 1 without a journal; waiting for the Mendeley fix*
- [ ] `r60_response_letter.py` — *script done 2026-11-01; `--draft` builds the highlighted draft docx; final mode refuses while numbers are pending*
- [ ] `r99_verify.py` (incl. the internal-label scan) + `nar_review_tools.py validate` → **gate G6** — *script done 2026-11-01; on stage A: 9 PASS, 1 FAIL (Supplementary Figure 19 until the stage B renumbering), review list D1 × 2, S0 × 36, alt text missing under the 19 supplementary legends*

### Phase 6 — documentation and package
- [ ] Update the project `CLAUDE.md`, `figures_for_article/CLAUDE.md`, `harmonization-metrics/CLAUDE.md` (§9)
- [ ] Memory file `project_nargab_revision.md` + `MEMORY.md` pointer
- [ ] Combined `Supplementary Figures S1-S18.pdf` (recompressed) — *review draft 2026-11-08 by `r46_review_figure_pdfs.py` → `Revised_manuscript/review_package_261108/` (46 pages, 10.8 MB; panels one per page); final after Daniil assembles the multi-panel pages*
- [ ] Commit and push (no files ≥ 50 MB; large outputs to S3 offload)
- [ ] Zenodo new version: only on Daniil's word

## 15. What this plan does not do (and why)

- **No full re-run of the 2,234-approach grid.** The reviewers question the selection, not the runs.
  Every new run is bounded and listed in §6.2 (WP6 confounding gradient, WP7 leave-cohort-out
  validation).
- **No red copy of the manuscript for now.** Only the tracked-changes version (Daniil, 2026-10-29);
  see caveat C9.
- **No external expression 2.0 cohorts (option V2 of the brainstorm).** Decision D2 chose
  leave-cohort-out validation. h230 (Article 2 harmonization) will provide external evidence later;
  the Discussion may mention it in one clause.
- **No changes to Figures 4 and 5 art**, unless decision D5 applies (the rule changes the best set).
- **No new metric families** besides the ground-truth log-FC concordance, which exists only inside the
  gradient experiment, where a batch-free reference is available.
- **No internal label in any publication document** (§1.1).

## 16. Addendum 2026-11-07: G2b closed, G4 package review

Decisions of Daniil recorded in `gates_review_261102.md` §4.4–§4.5 and §6:

- **Visual check closed after round 2.** Round 1: 16 accepted, 35 vetoed, 2 without comment;
  round 2: 5 accepted, 23 vetoed; the two uncommented members: RNA-seq-only ComBat (no imputation)
  accepted, S0 M-ComBat (no imputation, post-removal) vetoed. Final selection: **22 approaches**
  (FF only 5 Angel; FFPE only 1 SVA; RNA-seq only 2 SVA + 1 ComBat; multi-platform 7; microarrays
  only 1 Angel; S0 5 Angel). No round 3: r04 writes the members that enter after the round-2 vetoes
  to `output/wp4/not_added_check_closed.tsv` and never recommends them. The version-1 file
  `selection_by_rule.tsv` stays byte-identical (MD5 `7de86b95…`).
- **Leaf assignment (provisional):** all 7 multi-platform approaches → "RNA-seq + Illumina
  microarrays" (`output/wp4/leaf_assignment.tsv`); "RNA-seq + various microarrays" has no accepted
  approach (Figure 6F says so). Revisit at G4.
- **Discussion / Methods text:** RNA-seq-only approaches whose post-removal deletes the
  `RNASeq_FFPE_Exome_capture` batch (939 of 2,243 samples) failed for that reason; method failures
  are stated plainly with a simple description of each error (WP11 stage B).
- **Gradient statistics:** Spearman + FDR besides the effect-size criterion; rank trajectories of
  the arms under the rule. λ levels confirmed: 0, 0.1, …, 1 (11 levels × 3 replicates).
- **Figures:** article palettes everywhere; S16a bars; S17d–f new panels (figure count unchanged).

## 17. Addendum 2026-11-07 (third review): G4 answered

Decisions in `gates_review_261102.md` §9.1–§9.2. TODO:

- [x] Gradient arms 12 → 14 *(code + RUNBOOK §6.5 done and pushed 2026-11-07; **pod run done 2026-11-08 from the Mac** (pod logs S3 `pod_logs/fl-revision-c6a-12xlarge_261107_2024/`): 90 / 90 harmonization jobs finished, 85 matrices (M-ComBat failed as expected at λ = 1 × 4 and on the single-diagnosis control: "covariate confounded with batch"), 85 / 85 metric jobs ok. Collected 2026-11-08 on JupyterHub: r12 --concat (630 runs, 619 ok, 11 failed), r13, nb04 (14 arms), nb03, r40, r45 (661 numbers; new `gradient_mcombat_*`), r50 --stage B → `…_stageB_261108.docx` (gradient paragraph corrected: M-ComBat ranks first at λ 0.5–0.9), r90 PASS, r99 0 FAIL; review digest `gates_review_261102.md` §10)*: `25_angel` (Angel) and `29_combat_ref` (M-ComBat, reference batch `RNASeq_FF_PolyA`, present in every gradient design) added to `rl.GRADIENT_ARMS` as a post-hoc addition (both were selected at the visual check); 90 harmonizations + 90 metric jobs on the pod from the Mac (RUNBOOK §6.4, `--skip-if-exists`); then `r12 --concat`, r13, nb04, r45
- [x] Remove the "submitted decision tree" role (r22 `TREE_METHODS`, `v1_*` tables, r45 keys, S18a–c, letter, drafts); no comparison with the submitted version in any publication output (Figure 3 annotation, 6B label, 6F leaf note, Table 3 concordance columns)
- [x] Statistical annotations: pairwise Mann–Whitney + BH FDR on every comparison boxplot (≤ 4 boxes bars with stars; > 4 boxes p-value heatmap); first S18c *(S18c done: `output/wp9/nb05_v1_regret_tests.tsv`; S14a/b show distributions against a gate line, not group comparisons, so no pairwise test — Daniil to confirm)*
- [x] Figure 6 gradient panel: only the methods of the 22 selected approaches (G4.1)
- [x] Multi-platform leaves merged into one leaf (G4.2): `leaf_assignment.tsv`, r04, 6F; 6F redrawn after Daniil's Figma layout *(layout taken from the exported submitted figure `figures_for_article/current_figures_tables_for_article_260915/Figure 6.jpg`; Figma MCP not used)*
- [x] Figure 3: no "submitted version" annotation; row / column clusters colour-coded and named as in the original clustermap (Figma node 403-22); marks = 22 selected approaches
- [x] Stage B (r50) with drafts D-1 / D-2 corrected; title kept on SVA + FSQN R (G4.3); leave-cohort-out option (a) (G4.4); Discussion sentence on no harmonization under strong confounding (G4.5) *(2026-11-07: `r50_stage_b_text.py` + `run_stage_b()` → `Revised_manuscript/FL_harmonization_article_NARGAB_tracked_stageB_261107.docx`; 107 tracked edits; r90 PASS (16,495 → 14,885 words, 1,545 → 1,418 lines; 18 supplementary figures), r99 0 FAIL, nar validate ALL PASSED; numbers from r45 (584 keys). Open: Angel / M-ComBat gradient numbers after the pod, Daniil's read (gate G6))*

## 18. Addendum 2026-11-08 (fourth review): §10.6 and B1–B5 answered

Decisions in `gates_review_261102.md` §9.4 (B1–B5) and §10.6 (A, Q1, Q2, harshness); results in §11.
TODO:

- [x] Q2 (a): r13 "meaningful" end point = mean at the last λ with a value (λ = 0.9 for ComBat /
  M-ComBat with the covariate, which fail at λ = 1); new column `end_lambda`; re-run r13, nb04
- [x] A1: `revision_lib.STRATEGY_DISPLAY_NAMES` → "code · name", S0 = "No removal"; new
  `STRATEGY_CODES`; tests updated
- [x] A2: re-run the figure notebooks that label strategies (nb01, nb02, nb03, nb04, nb05; nb07 not re-run: visual check closed, nothing to draw, internal plots only)
  and r40 (Supplementary File 3 strategy column "code · name")
- [x] B1 (b): new `nb08_figures_4_5.ipynb` (embeddings from `cache/nb07`): Figure 4 = unharmonized
  overview + the three single-sample-type leaves (FF only Angel, FFPE only SVA, RNA-seq only SVA);
  Figure 5 = the multi-platform leaf (FSQN R, ComBat, M-ComBat); each panel an unharmonized |
  harmonized pair, PCA + tSNE, rows batch / diagnosis; figure count unchanged
- [x] Q1 (b): explicit mechanism sentence on M-ComBat's rank (covariate keeps the batch) in the
  Results gradient paragraph and the Discussion
- [x] A3: stage-B text: "name (code)" at the first Methods / Results mention, then codes; Table 1 /
  Table 3 code column; B1 Results paragraphs, legends and alt text of Figures 4–5 rewritten;
  Supplementary Figures 7–13 still cited; r45 → r50 --stage B (same date tag 261108, overwrites
  the uncommented docx)
- [x] A4: r99 label scan without S0; `CLAUDE.md` hard rule 3, memory `feedback_no_internal_labels.md`,
  §1.1 (done above) record the exception
- [x] B3 (b): r46 writes an alt-text line under every supplementary figure of the review PDF
- [x] A5: r90, r99, validator, tests, frozen MD5, r46, letter draft (r60)
- [x] Review digest §11 in `gates_review_261102.md` with the Tier 1 / Tier 2 file list (Daniil)
- [x] S5 (Daniil's request after §10.6): nb02 §4 → 87-metric Spearman clustermap with the 22 panel
  metrics starred and Figure 3 colour bars, medoid table `output/wp9/nb02_figS5_87_metric_clusters.tsv`
  (15 of 22 medoids; 7 next to excluded platform / major-group variants), r45 `s5_*` keys, one
  Results sentence, new legend
- *Done 2026-11-08: Q2 trend count 34 → 43 of 78; stage B `…_stageB_261108.docx` (108 tracked edits,
  r90 PASS 14,593 words / 1,384 lines, r99 0 FAIL, validator ALL PASSED); numbers 717 keys; tests 89;
  Supplementary File 3 main sheet keeps the published identifiers (`S0_no_removal` …, they begin
  with the code), the leave-cohort-out sheet shows "code · name". Review digest and Tier 1 / Tier 2
  file list: `gates_review_261102.md` §11.*

## 19. Addendum 2026-11-08 (figure-notebook review)

Daniil's review of nb02–nb07 (`daniil_review_261108.md`) is implemented by the separate plan
`figure_review_corrections_plan_261108.md` (D1–D5 answered in `gates_review_261102.md` §12.2;
digest §12.4, next steps §12.5). In short:
- the fold-change agreement left the statistics (r13 12 scores; trend count still 43 / 78) and
  the supplement;
- panels are drawn at page size (Figma 180 × 275 mm);
- the leave-cohort-out random baseline is a distribution with empirical p and BH-FDR, and no
  rank test survives FDR;
- the text has the Pareto definition with a DOI, Methods for every new test, D1 names and
  "decrease";
- the r98 consistency audit was run, and the peer-review brainstorm's requests R1–R9 wait for
  Daniil.


## 20. Addendum 2026-11-09: Figma units and the final review package

Daniil's requests `daniil_review_261109.md` and "the final review package with all the article
materials" (digest `gates_review_261102.md` §13). TODO:

- [x] One "Figma units" cell in nb01–nb06, nb08 (frame 756 × 1159 px = 180 × 275 mm; 1 SVG pt =
  4/3 Figma px): all text 7.5 pt = 10 px (S5 row labels 6 px), plot area fitted to the slot
  without legends / colour bars, fit logged to `output/wp14/figma_fit/`
- [x] Batch names without "(n = …)" and without the microarray "Unknown" (1E, Figure 4–5 legends)
- [x] Square embedding scatters, packed columns (nb08)
- [x] S4: counts only, 130 × 62 mm
- [x] Layout repairs after the 10 px text: Figure 3 measured legends, 6C/D titles / ticks, S17c
  labels after the fit, 1E group labels, nb08 legend-only figures
- [x] `r97_figma_check.py` (33 / 33 publication SVGs pass after the S18 merge)
- [x] `r46 --tag`, `r47_build_review_package.py` → `Revised_manuscript/review_package_261109/`
  (tracked + clean manuscript, letter draft, Tables 1–3 docx / xlsx, figure PDFs, Supplementary
  Files 1–3)
- [x] Daniil's S18 additions: S18a half height; S18b merged into S18a's titles (Daniil, chat 2026-11-09), decrease panel S18c → S18b, legend / alt text, r45 → r50 stage B 261109 → r90 / r99 / validator; S18c question answered in gates_review §13.4b (random baseline per-fold mean → every run)
- [x] nb07 (review-only embeddings, Daniil 2026-11-09): square scatters + plain batch names; `review_extras/final_selection_embeddings/` re-drawn (18 PDFs, 30 pages, 0 old names)
- [ ] Final letter: 16 `[LINES]` markers need Word line numbers (Mac) → r60 final → G5
- [ ] Daniil: R1–R9, D3, Word pass, Mendeley, Figma assembly → G6
