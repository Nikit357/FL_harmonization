# Article 1 revision (NARGAB-2026-312): brainstorm result, 2026-10-28

**Input:** `reviewer_report.md` (Reviewer 1: 3 major + 5 minor comments; Reviewer 2: 2 comments),
with Daniil's inline proposals. **Manuscript baseline:** `figures_for_article/FL_manuscript_versions/FL_harmonization_article_NAR_260912.docx`
(13,456 words; 6 main figures; 19 supplementary figures; Tables 1–3; Supplementary Files 1–3, File 2 =
Tables S1–S3 + 2 sheets). **Debate log:** `.brainstorm/nargab-312-revision-strategy.md` (git-ignored).
**Hard constraint (Daniil):** the number of lines, figures and tables (main + supplementary) may go down,
never up.

---

## 1. TL;DR

Daniil's proposals hold for the metric panel and for removing the composite score. They need two
corrections. First, group N (LOBO) is **not** held-out validation of the method *selection*, for two
reasons. The held-out batch was harmonized together with the training batches. SVA and the ComBat
family were given the diagnosis labels that LOBO later predicts. Second, the paper already reports that
the best approaches do not predict better than the rest (LOBO F1 median 0.629 vs 0.717). Group N should
therefore be presented as a **non-inferiority gate with a leakage control**, and Reviewer 1's held-out
request needs one bounded new experiment, or an honest limitation statement if Daniil declines it.

---

## 2. Measured facts the debate relied on

Computed today from `Supplementary File 3.csv.gz` (2,234 approaches, `pct_samples_allNA < 5`) and the
`Metric_polarity` sheet (87 metrics with polarity ≠ 0):

| Quantity | Value |
|---|---|
| Scoring metrics by group | A 11, B 22, C 16, D 11, E 2, G 3, H 7, I 10, K 5 |
| Scoring metrics by annotation column | RNA_BATCH 15, PLATFORM_RNA 15, COHORT_LABEL 15, RNASEQ_SOURCE 12, Diagnosis 6, Major_group 6, TUMOR_NORMAL 6, no column 12 |
| Approaches with all 87 metrics defined | 1,354 / 2,234 (60.6 %) |
| Metrics on RNA_BATCH, Diagnosis or no column | **33** |
| Approaches with all 33 defined | **1,993 / 2,234 (89.2 %)**, max NA per metric 8.8 % |
| Non-redundant clusters of the 33 at \|ρ\| ≥ 0.8 (complete linkage) | **23**, covering all 9 groups (0.7 → fewer, 0.9 → more; full 87: 48 clusters at 0.8) |
| Groups without a Diagnosis metric | C, D (RNA_BATCH only); E, K (no annotation column at all) |

Two consequences follow. Dropping the PLATFORM_RNA / RNASEQ_SOURCE / COHORT_LABEL metrics removes the
main source of missing metrics in single-platform and single-biomaterial strategies (C, G, J, K), so
the reduced panel also answers R1.3 ("equivalent metric availability"). The remaining 241 incomplete
approaches are kBET / timeout failures and must be named. Daniil's rule "keep at least one metric per
group with RNA_BATCH **and** Diagnosis" cannot hold literally for C, D, E and K. The rule has to read
"with RNA_BATCH and Diagnosis where the group defines them".

From the code (`compute_batch_metrics.py::_fold_pca_projections`, lines 2120–2165): LOBO scales and
fits the PCA on the training batches of the **already harmonized** matrix. The held-out batch therefore
took part in the harmonization (transductive setting). For methods that received
`Diagnosis_cell_type_unified` as covariate (SVA, ComBat, ComBat-seq, M-ComBat, InMoose), the labels
predicted by LOBO were also used to build the corrected matrix.

---

## 3. The debate (summary; one round, three voices)

**Builder (Thesis).** Daniil's plan as written. Build the reduced panel, rebuild Figure 3 and every
downstream plot, delete the composite score, present group N as held-out validation, and describe the
selection as global + local metrics, visual embedding inspection and groups L/M/N. It is fast, reuses
existing tables, needs no new harmonization runs and shortens the paper.

**Critic (Antithesis).** There are four weak points, and a reviewer will find each one.
1. *Group N is not what R1.2 asks for.* R1.2 asks whether the **recommendations** transfer to unseen
   batches or cohorts. LOBO measures whether a classifier transfers between batches *inside one
   harmonized matrix*. The held-out batch was harmonized together with the others, and for the
   covariate methods the diagnosis labels leaked into the correction (Nygaard et al. 2016, *Biostatistics*:
   batch correction with a group covariate in an unbalanced design inflates group differences). Our
   own numbers show no LOBO gain for the best approaches. *Bias: confirmation bias* (re-labelling an
   existing result as the requested validation).
2. *Post-hoc rule.* The best approaches were picked visually from the clustermap. A formal rule written
   now will tend to reproduce that pick. *Bias: anchoring.* The defence is to apply the rule blind on
   the new panel and report every disagreement with the visual pick.
3. *SVA's "biology preservation" is partly circular*, for the same covariate reason. R1.1 asks to
   temper such claims, and this is exactly the claim to temper.
4. *FSQN defined strategy A and then won.* A leave-strategies-out check (rank FSQN without A and E1–E3)
   costs nothing and must be shown. *Bias: sunk cost* in the 87-metric framework, which pushes toward
   defending it instead of replacing it.

**Analyst (Synthesis).** The page budget decides what is feasible. Removing the composite score frees
about five Results paragraphs, Figures 6A and 6E, and one Discussion paragraph. Supplementary Figures 8
and 10 (embeddings of metrics and of approaches) add little once the clustermap is rebuilt on 23
metrics, and Supplementary Figures 2–4 (per-cohort distributions under three NA modes) can become one
figure. That space pays for three things: a confounding-diagnostics panel, a robustness panel, and
one validation panel. Group N stays, reframed as a **gate**: a recommended approach must not predict
worse than the raw matrix and the permutation control. A **leakage control** sits beside it: SVA
re-run without the diagnosis covariate for the recommended scenarios, about 10 jobs. Only a bounded new
experiment gives real held-out evidence. **Option V1** is leave-cohort-out *selection* on the five
decision-tree scenarios: choose the best approach on 4/5 of the cohorts with the reduced panel, then
check it on the held-out 1/5. The `h230_01_build_cv_splits.py` / CV-B logic already exists. **Option V2**
is external cohorts from expression 2.0 that are absent from the 7,174. Its size is Daniil's decision
(B1).

**Agreed by all three voices.** Remove the composite score and every total score, which makes R2.2(iii)
moot. Build the reduced panel by the |ρ| ≥ 0.8 rule with RNA_BATCH / Diagnosis priority. State the
adjudication hierarchy in Methods. Add confounding diagnostics and temper the biology-preservation
wording. Apply all minor comments.

**Remaining trade-off.** The more credible answer to R1.2 (V1 or V2) costs pod time and one figure
panel. The cheap answer (reframing plus a limitation statement) risks a second revision round.

**Weakest surviving assumption.** That the blind rule on the reduced panel reproduces the current best
set. If it does not (for example, if FSMVN or AMDBNorm drop out, or another method enters), the decision
tree (Figure 6F) and the Abstract change. The plan must allow for that outcome, not hide it.

---

## 4. Point-by-point strategy

### Reviewer 1

| # | Request | Response (what we do) | Where in the paper |
|---|---|---|---|
| **M1** | Formal batch–biology confounding diagnostics; temper biology-preservation claims | (a) Association: Cramér's V and adjusted mutual information between RNA_BATCH (and COHORT_LABEL, PLATFORM_RNA) and diagnosis, with Fisher–Freeman–Halton / χ² p-values. (b) Design structure: per-batch diagnosis entropy; the list of **single-diagnosis batches**; the batch × diagnosis **connectivity graph** (a batch "bridges" when it carries ≥ 2 diagnoses; covariate-based correction is identifiable only through bridging batches). (c) Variance partition: shared vs unique R² of batch and diagnosis (joint linear model on top PCs; `variancePartition` is already in the metrics pod). (d) **Stratified re-evaluation**: biology-preservation metrics recomputed on bridging batches only, and batch-mixing metrics within diagnosis (DLBCL, FL). (e) Text: replace "preserve biology" claims by "retain the diagnosis structure measured by …", plus one limitation sentence about the covariate methods (Nygaard 2016). | Methods (+1 short para), Results (rewrite of the composition paragraph), Fig 1E replaced by the contingency / connectivity panel, Supp Fig (stratified) |
| **M2** | Selection bias (FSQN screening defined strategies; one dataset for development, selection and tree); validate on held-out batches/cohorts or external data | (a) State the development timeline plainly (Table 1 "Iteration" column already shows it). (b) Leave-strategies-out check: re-rank with A and E1–E3 removed. (c) Group N as a **gate** (non-inferiority vs raw and permutation) plus the **leakage control** (SVA without covariate). (d) **New held-out experiment V1 and/or V2 (decision B1).** (e) Limitation sentence if only (a)–(c) are done. | Methods (adjudication + validation para), Results (new short sub-section replacing the composite one), Fig 6 new panel, Supp Fig 18 reworked |
| **M3** | Correlated, equally weighted metrics; unequal availability; sensitivity with a reduced non-redundant set | Reduced panel (33 → ~23, rule in §5); Figure 3 and Supplementary Figure 7 rebuilt on it; availability equalised by construction (1,993 approaches complete); robustness: the best-approach set and per-strategy method ranks under thresholds 0.7 / 0.8 / 0.9, under the full 87 and under group-balanced weighting (Kendall τ, top-k overlap). | Methods para "Metric panel", Fig 3, Supp Fig 7, Supp robustness figure, `Metric_polarity` sheet gains the columns `in_reduced_panel`, `cluster_id`, `representative_of` |
| m1 | 33 vs 31 methods | Use "33 implemented, 31 analysed" consistently (Abstract, Intro, Discussion, Conclusions, Fig 1C label). | text |
| m2 | Strategy D is biology-based | Table 1: D moved to "By biology"; also the Fig 2A arc label | Table 1, Fig 2A |
| m3 | Fig 4F caption | "SVA-harmonized, KNN-imputed C dataset (RNA-seq only)" | legend |
| m4 | Terminology | RNA-seq everywhere (batch labels keep `RNASeq_…` as identifiers, explained once); "softImpute" (package name); "2 × 2"; scripted sweep | whole text |
| m5 | Reference formatting | Fix Pedregosa, Kappal, and audit all Mendeley entries against the NAR style (field-level, `w:sdt` safe) | references |

### Reviewer 2

| # | Request | Response |
|---|---|---|
| **R2.1** | State the primary adjudication criterion and the precedence when references conflict | Formal hierarchy in Methods (new para), applied blind on the reduced panel: **Gate 1** biomarker preservation (group L, mean ρ before/after ≥ 0.7; this is where MNN exits). **Gate 2** prediction non-inferiority (group N vs raw and permutation; not a ranker, because it is transductive). **Rank** within each decision-tree scenario on the reduced panel, read as two axes: batch removal (RNA_BATCH metrics) and biology retention (Diagnosis metrics), Pareto front, no total score. **Confirm** by visual inspection of PCA / tSNE / UMAP (tie-breaker only). Report the concordance of the rule with the original visual pick, case by case. Answer honestly that the original selection was visual and clustermap-based. |
| **R2.2** | Reduce and de-redundify the metric panel; biologically interpretable axes; if a total score stays, say it is relative and robust | (i) reduced panel as in M3. (ii) Axes = **batch mixing (global / local)** × **biology retention (global / local)** + marker preservation (L) + prediction (N): six interpretable axes that replace the radar's composite axis. (iii) The total score is **removed**; say so explicitly in the response. |

---

## 5. Metric-panel rule (proposal, to be fixed in the plan)

1. Universe: the 87 scoring metrics. Keep metrics on `RNA_BATCH`, `Diagnosis_cell_type_unified` or no
   annotation column (33). Drop PLATFORM_RNA / RNASEQ_SOURCE / COHORT_LABEL / Major_group / TUMOR_NORMAL
   variants; their RNA_BATCH / Diagnosis twins carry the same statistic.
2. Polarity-adjust, compute the Spearman correlation over the 2,234 approaches (pairwise complete),
   cluster `1 − |ρ|` with complete linkage, cut at 0.2 (every pair inside a cluster has |ρ| ≥ 0.8).
3. One representative per cluster, chosen in this order: RNA_BATCH or Diagnosis column → lowest NA
   fraction → highest mean |ρ| to its cluster mates → simplest / most cited metric (tie-break by hand,
   logged).
4. Coverage check: at least one metric per group A–K; within groups that define them, at least one
   RNA_BATCH and one Diagnosis metric. Add back the best-placed metric if a group is missing.
5. Output: the panel table (about 23 rows) as new columns in the `Metric_polarity` sheet, not as a new
   table.

---

## 6. Budget ledger (must net ≤ 0)

| Item | Current | Proposal | Δ |
|---|---|---|---|
| Main figures | 6 | 6 (Fig 1E → confounding panel; Fig 3 rebuilt; Fig 6: A and E removed, B recomputed on the panel, C/D radar without the composite axis, + validation panel, F updated) | 0 |
| Supplementary figures | 19 | 17: S2–S4 merged into one (−2); S8 and S10 removed (−2); S7 → panel construction; + robustness (+1); + stratified confounding check (+1); S18 reworked (gate + leakage control) | −2 |
| Main tables | 3 | 3 (Table 1 fix, Table 3 + gate / rank columns) | 0 |
| Supplementary files / tables | 3 files, Tables S1–S3 | same; new data as columns of existing sheets / File 3 | 0 |
| Text | 13,456 words | Removed: composite paragraphs [138], [146]–[148], [150]; Supp Fig 8/10 sentences; Discussion [197] first point, shorter [201]–[205]. Added: Methods ×3 short paras (confounding, panel, adjudication / validation), Results ×2 (confounding, validation). Target ≤ 13,000 words and fewer lines | < 0 |

---

## 7. Decisions for Daniil (before the implementation plan is final)

- **B1 — held-out evidence for R1.2.** (a) V1 leave-cohort-out selection on the five scenarios
  (recommended); (b) V2 external expression 2.0 cohorts; (c) both; (d) no new compute, only reframing
  plus a limitation.
- **B2 — leakage control.** Re-run SVA (and ComBat, as a contrast) without the diagnosis covariate for
  the recommended scenarios: yes / no.
- **B3 — panel rule.** Accept §5 as written (threshold 0.8, complete linkage, RNA_BATCH / Diagnosis
  priority, "where defined" exception for C, D, E, K).
- **B4 — figure cuts.** Accept the removal of Supplementary Figures 8 and 10, the merge of 2–4, and the
  replacement of Figure 1E.
- **B5 — if the blind rule changes the best set.** Report the new set and update the tree and the
  Abstract (recommended), or keep the visual set and report the disagreement.
- **B6 — Reviewer 2's report.** It contains two comments only. Is that the complete report, or was the
  paste cut off?

---

## 8. Answer to Daniil's question on M1 (how confounding is diagnosed in batch-correction studies)

The usual practice goes beyond a single Fisher test of non-random association. With 29 batches × ~5
diagnoses and many zero cells, a Fisher / χ² p-value only says "associated", which is obvious here.
Studies use four complementary layers:

1. **Effect size of the association:** Cramér's V, or (adjusted) mutual information / adjusted Rand
   index between the batch and biology labels. Unlike a p-value, these do not saturate with n.
2. **Design balance and connectivity:** the per-batch composition (entropy, the share of
   single-diagnosis batches), and whether the batch–biology bipartite graph is connected. Covariate
   models such as ComBat with `mod` or SVA with a design are identifiable only through batches that
   contain several groups; a fully confounded batch cannot be corrected without removing biology.
   Nygaard et al. 2016 and Zindler et al. 2020 (*BMC Bioinformatics*, ComBat in unbalanced designs)
   make this the standard caveat.
3. **Variance decomposition:** PVCA or variancePartition, which separate the variance explained by
   batch alone, by biology alone, and the shared (confounded) part. The shared part is the quantity the
   reviewer is really asking about.
4. **Stratified evaluation:** compute biology-preservation metrics only where batch and biology are
   crossed (bridging batches), and batch-mixing metrics within each diagnosis. Benchmarks such as
   Tran et al. 2020 and Luecken et al. 2022 report metrics that respect this structure (iLISI within
   cell type, cLISI).

The plan uses all four. Layers 1–3 are cheap; layer 4 needs a metric recomputation on subsets of the
existing harmonized matrices (no new harmonization).

---

## 9. Reasoning summary

The reviewers attack the selection framework, not the data, so the cheapest credible answer replaces
the framework rather than defending it: a de-redundant two-label panel, a stated precedence rule and no
total score. Group N cannot serve as held-out validation because it is transductive and, for covariate
methods, label-leaking. Calling it validation would invite a second round. That leaves a bounded
leave-cohort-out experiment as the only strong answer to R1.2, and its size is Daniil's decision.
