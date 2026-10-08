# Article 2 for F1000Research — run report

**Manuscript:** *A metric-class comparison of harmonization approaches* (working title), for
F1000Research.
**Plan of record:** `f1000_article2_plan_260917.md` (§10 is the phase checklist, §11 the
implementation log).
**Run folder:** `workflow_runs/260919_run1/` — the multi-agent half of the work.
**Report written:** 2026-09-20, at the close of Phase 8.

This report is the one place that says what was run, by whom, on what data, what came out, and
what is still open. It is written for someone who arrives after the fact and has to decide whether
to trust the manuscript. The per-number and per-citation detail is in `06_provenance.md`; the list
of unresolved items is in `06_open_items.md`; this report does not repeat either, it points at
them.

---

## 1. What was produced

| Deliverable | Where | State |
|---|---|---|
| Manuscript, Markdown | `manuscript/FL_metric_classes_F1000_260917.md` | 10,337 words, every section inside its budget |
| Manuscript, Word | `manuscript/FL_metric_classes_F1000_260917.docx` | The main state since Phase 5. Carries 22 tracked revisions from two post-delivery passes, described in §5 below |
| Figure legends and alt text | `manuscript/figure_legends_260917.md` | 6 main and 14 supplementary legends, 20 alt texts, one per legend |
| Reference list | `manuscript/references_260917.md` | 52 entries, 52 `PMID:` lines, no `[TO CONFIRM]` |
| Claim-to-passage support | `manuscript/reference_support_260917.md` | Full-text quotes, renumbered 1–52 in the post-delivery pass |
| Result tables | `tables/A2_T0` – `A2_T8` | The only tables a manuscript number may come from |
| Supplementary workbooks | `supplementary/A2_Supplementary_File_{1,2,3}_260917.xlsx` | README + 6, README + 6, README + 4 sheets |
| Duplication check | `supplementary/duplication_check_260917.md` | No Article 2 sheet reproduces a measurement column of any Article 1 supplementary file |
| Panels | `figures/panels_260917/a2_p1` – `a2_p18` | 18 panels, each in pdf, svg and png |
| Recipe figure assets | `figures/recipe_assets_260917/` | Twelve text-free SVGs, including the LOBO scheme |

## 2. The data the manuscript rests on

- **Analysis set: 2,234 approaches**, over 31 methods, 14 filter strategies, 3 imputation
  strategies and 2 post-removal settings. It is Supplementary File 3 of Article 1 filtered to
  `pct_samples_allNA < 5`, with metric groups L, M and N joined from the pinned snapshot
  `metrics_comprehensive_260905.csv`.
- **Shambhala-2 carries two names and the rename runs first.** The snapshot stores 18 parameter
  variants; Article 1 kept one representative as `20_shambhala`. The 84 shared keys agree on 78 of
  79 numeric columns, the exception being wall-clock compute time (Supplementary File 1, sheet
  `Canonical_set_reconciliation`). Omitting the rename returns 2,150 and silently loses 84
  approaches.
- **Everything is reproducible from one module.** `analysis/article2_generalizability.py` writes
  the nine tables and asserts the 2,234 and the 31 on every run; it fails loudly if a snapshot
  changes underneath the manuscript.

## 3. How the work was run

Eight phases, of which two were the multi-agent workflow and six were interactive.

| Phase | What | Agent or interactive | Done |
|---|---|---|---|
| 0 | Prerequisites and decisions | Daniil | all but the FL_harmonization release DOI |
| 1 | Scaffolding, the three gates and their fixtures | interactive | 2026-09-18 |
| 2 | Analysis code, the nine tables, the 18 panels, the recipe assets | `code-analyst` | 2026-09-19 |
| 3 | Literature, 28 references read and quoted | `literature-scout` | 2026-09-19 |
| 4 | Workflow script, 833 lines, five schemas, six prompt builders | interactive | 2026-09-19 |
| 5 | Manuscript: draft, review, delivery | `writer`, `reference-verifier`, `style-editor`, `teamlead` | 2026-09-19 |
| 6 | Supplementary workbooks | interactive | 2026-09-20 |
| 7 | Figma assembly | interactive | 2026-09-20 |
| 8 | Documentation, this report | interactive | 2026-09-20 |

### The two workflow runs

The workflow was split in two so each half stayed inside the session's agent-count guideline.

**Run A** — `phases: ['evidence','draft']`, run id `wf_60d927c7-88e`. **10 agents, 0 errors,
2 h 28 m, 1.85 M subagent tokens, 454 tool calls.** The dry run predicted 5 agents; both gates
rejected once, which is the other five. Gate 1 accepted at round 2 with 15 artifacts named; gate 2
returned *revise* and its 4 surviving defects became open items, which is what the role
specification asks for.

**Run B** — `phases: ['review','delivery']`, resumed into the same run folder. The launching
session was ended by the token limit and the JupyterHub server restarted afterwards, so the run's
own agent count, wall time and token total are **not recoverable**; everything recorded about it
is read off the artifacts on disk. Gate 3 accepted at round 2 after the three round-1 writer
defects were fixed; gate 4 accepted **for delivery, not for submission**.

### What the review agents actually did

The reference-verifier re-resolved all 55 entries of the pre-renumbering list from scratch — 48 by
PMID through eSummary, 4 through Crossref, 1 through the bioRxiv API, 1 through DataCite, 2 at the
publisher — and took PMC ids from the `articleids` block instead of calling elink, which is the
trap that produced a wrong-paper quotation earlier in Phase 3. Verdicts: 49 SUPPORTS, 3 PARTIAL,
2 DOES NOT SUPPORT, 1 UNVERIFIED; the last three were dropped in the gate-3 renumbering to 52.

The style-editor ran the three mechanical gates, made a manual register pass, applied 12 prose
edits on 11 lines and brought the `.docx` into agreement. The team lead decomposed that edit into
14 hunks and confirmed that no number, citation or claim moved.

At delivery the team lead built a provenance index over all 452 distinct numbers and all 52
citations, re-resolved a fresh independent 11 of 52 references (`random.seed(20260919)`, 11 of 11
matching) and wrote every survivor into `06_open_items.md` instead of fixing it. Delivery has no
revision round by design.

## 4. Gate results, re-run by hand on 2026-09-20

These were re-run after the Phase 6 edit to the manuscript, not carried over from the workflow's
own report.

| Gate | Command | Result |
|---|---|---|
| Numbers | `audit_numbers.py … --evidence workflow_runs/260919_run1/01_numbers.json` | **exit 0** — 450 distinct numbers, 450 sourced, 0 unsourced, against 13 sources |
| Style | `check_style.py --journal f1000` | **exit 0** — all six section budgets satisfied |
| Antithesis | `grep -nEi "rather than\|, not [a-z]+\.\|it is not .*, it is"` | no hit |
| Overlap | `check_overlap.py` vs Article 1 and the source document, 8-gram | **exit 0** — 11,703 tokens, 40 allow-listed hits ignored, no verbatim overlap |
| Tracked changes | `nar_review_tools.py validate` on the pre/post pair | **ALL CHECKS PASSED** — 22 revisions, 0 `w:t` in `w:del`, 0 stray `delText`, 0 duplicate ids, reject-all restores the delivered text exactly |

**Read the number audit for what it is.** It tests presence, not meaning: a value can match a
column it did not come from. Provenance is a presence match plus a named filter or a recorded
re-derivation, and `06_provenance.md` marks which of the numbers have that.

## 5. Phase 6 and the one manuscript change made after delivery

Three workbooks were assembled by `analysis/build_supplementary_workbooks.py`. Two sheets are not
stored as an `A2_T*` table and are derived in that script from the same module the tables came
from, so a workbook cannot disagree with a table: `Elected_sets_by_class`, which needs the
election itself, and `Strategy_and_imputation_summary`, which is an aggregate over `A2_T1`.

Every workbook opens with a plain-language README sheet naming each following sheet, its row count
and its source table. Every data sheet carries a provenance line in row 1 naming the source table
and the filter, so a sheet lifted out of the workbook is still self-describing.

A second post-delivery pass made the Figure 4 split: Figure 4 keeps two of its four expression
scatter grids and the other two become Supplementary Figure 14, because four full-width grids would
make the Figma frame about 9,500 px tall and a 2x2 arrangement would drop the facet labels to about
4 pt. **Daniil chose the split on 2026-09-20.** Figure 4 is relettered A to G in the `.md`, the
legends and the `.docx`, the last as 10 tracked replacements plus one tracked insertion
(`tools/apply_figure4_split_edits.py`).

Supplementary File 3 was built because the marker-panel figures are used (Supplementary Figures 11
and 13), which is the condition plan §7 sets. The manuscript's "Supplementary material" section
named only Files 1 and 2, so one sentence was added to it. **Daniil approved this edit on
2026-09-20**, and it is the only change made to the manuscript after delivery. It went into the
`.md` directly and into the `.docx` as a Word tracked insertion by `Claude (Article 2)`
(`tools/apply_supp_file3_entry.py`), with the untouched file kept beside it as
`FL_metric_classes_F1000_260917_pre_suppfile3.docx`. The delivered `.docx` therefore now carries
one `w:ins`, where `06_open_items.md` §6 records zero; that is deliberate and reject-all still
restores the delivered text exactly.

## 6. Phase 7 — Figma

**Done 2026-09-20, and rule 5 now passes on a measurement rather than an assertion.** At delivery
the check had never been run at all: no session until then had Figma read capability and no
before/after Page 2 geometry snapshot existed. Both snapshots now exist as
`figures/figma_snapshots/page2_{before,after}_260920.json`, and the diff between them shows
**0 geometry changes and 0 removed nodes**. What differs is 26 names — the 13 renamed frames and
their 13 title TEXT nodes — plus 14 nodes that are new (7 frames and their 7 titles).

On the canvas: Extended Figures 1 to 3 are now Figures 1 to 3 and Extended Figures 4 to 13 are
Supplementary Figures 1 to 10, renamed by node id rather than by name because "Extended Figure 1"
is a prefix of "Extended Figure 10". Seven new frames carry the 21 Article 2 panels as 300 dpi
image fills at the geometry of `figures/figma_layout_260920.md`, with 21 panel letters in Inter
Bold 20 pt. Figure 6, the recipe, is fully vector: its twelve text-free assets were imported as
editable vector trees and all 21 of its characters are Figma TEXT nodes.

The canvas is explicitly a first pass that expects Daniil's hand correction (plan §5.5).

## 7. What is still open

`06_open_items.md` is the authoritative list and is not restated here. In short:

- **P1** the FL_harmonization release DOI, and **P2** which authors hold employment by affiliation 2 —
  both are deliberate `[TO CONFIRM]` markers; only Daniil can close them.
- **D1 / D6** three values and seven fold-population counts whose locus is the pinned snapshot or
  `prediction_folds_long.csv` rather than a file under `tables/`. Daniil decides whether to promote
  the columns into a table or to accept the exception knowingly.
- **D8** whether Zenodo record 22737294 is published and its DOI resolves. Project memory records
  it as fully uploaded on 2026-09-14 but **not published**.
- Article 2 is **delivered, not cleared for submission**. That distinction is gate 4's own verdict
  and nothing since has changed it.
- **Rule 5 / Figma is no longer open.** `06_open_items.md` §4 records it as not started and
  decision 6 of its §5 asks Daniil to confirm by hand that no frame changed beyond the renaming.
  Both are now answered by the snapshot diff in §6 above.
