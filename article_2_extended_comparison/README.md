> **Public copy.** This folder is the external material for Article 2 (F1000Research):
> a one-way, sanitized copy of the authors' working folder. Some files are withheld, and the
> affiliation, funding and competing-interest statements in the Markdown drafts point to the
> published article. See [`WITHHELD.md`](WITHHELD.md). Article DOI: *to be added on publication*.

# Article 2 — where everything lives

**Paper:** *Metric classes elect non-overlapping sets of harmonization approaches: a cross-election
analysis of 2,234 approaches in a multi-platform B-cell lymphoma benchmark*
**Target:** F1000Research · **Status:** delivered, **not yet cleared for submission**
**Last updated:** 2026-09-25 (revision round 1, see §0)

This is the map of the Article 2 deliverables: the manuscript, the figures, the tables and the
supplementary material. It says where each thing is, what state it is in, and what still needs a
decision. The plan of record is `f1000_article2_plan_260917.md` (§10 is the phase checklist, §11
the implementation log); the narrative account of how it was produced is
`workflow_runs/260919_run1/RUN_REPORT.md`.

---

## 0. Revision round 1 (2026-09-24 to 2026-09-25) — the current state

The current manuscript is **`manuscript/FL_metric_classes_F1000_260925.docx`**. It is a
tracked-changes revision of Daniil's edited copy, which is the base and is never modified:
`manuscript/FL_metric_classes_F1000_260917_edited_Daniil.docx`.

- **Accept All** gives the revised article. **Rejecting Claude's revisions** gives Daniil's copy
  back.
- There are 1,240 tracked changes, all by the author "Claude (Article 2 revision 2026-09-25)".
- The Markdown twin, which the gates read, is `manuscript/FL_metric_classes_F1000_260925.md`.

Where the rest of the round lives:

| What | Where |
|---|---|
| Plan of record, with the TODO fully ticked | `f1000_article2_revision_plan_260924.md` |
| Run report: provenance, gates, open items | `workflow_runs/260924_run1/RUN_REPORT.md` |
| Daniil's review, as used | `manuscript/daniil_comments_260924.md` (37 comments), `daniil_diff_260924.md` (61 rewritten, 10 inserted paragraphs), `daniil_review_principles_260924.md` (the standard for the unreviewed paragraphs 78–148) |
| Tables | `tables/A2_T0`–`A2_T16` stamped `260924` |
| Figures | `figures/panels_260925/` (8 composite figures, pdf/svg/png) |
| Final figure numbers | `figures/figma_layout_260925.md`, last section |
| Renumbering map | `workflow_runs/260924_run1/21_renumber_map.md` |
| Workbooks | `supplementary/A2_Supplementary_File_{1,2,3}_260925.xlsx` |
| Workflow script (copy; the 260919 one is untouched) | `workflows/article2_revision_260924.workflow.js` |

What changed in the manuscript's shape:

- **Figures:** 7 main figures. Figures 4–6 are new; the recipe figure is now **Figure 7**.
- **Supplementary figures:** 17. Numbers 1, 2 and 13–17 are new, and the old 1–10 became
  3–12 by first citation.
- **Tables:** 4 in the main text, against a budget of 5. Tables 3 and 4 swapped places.

Rules that bind later edits:

- the citation freeze (46 Mendeley fields and 4 numeric brackets, never touched);
- renumbering is always the last step;
- edits go to the drafts in the run folder, never to the assembled `.md`.

`CLAUDE.md` ("Revision round 1") has the pipeline commands.

Sections 1–8 below describe the delivery of 2026-09-19/20 and remain accurate for that version.

---

## 1. The manuscript — start here

> **The Word file is the master.** Since Phase 5 it has been the main state, and it is where
> Daniil comments. The Markdown file is kept in step with it and is what the automated gates read.

| File | What it is |
|---|---|
| **`manuscript/FL_metric_classes_F1000_260917.docx`** | **The current manuscript.** Carries 22 tracked revisions from two approved post-delivery passes (§6 below). Accept All gives the current text; Reject All restores the delivered version exactly. |
| `manuscript/FL_metric_classes_F1000_260917.md` | The same text in Markdown, in step with the `.docx`. The three gates run against this file. 10,581 words, 300-word structured abstract, 0 em-dashes. |
| `manuscript/figure_legends_260917.md` | All 20 legends — 6 main figures and 14 supplementary — each with an alt text. Every legend names the panel source files it is built from. |
| `manuscript/references_260917.md` | 52 references, every one carrying a `PMID:` line, Mendeley-ready. |
| `manuscript/reference_support_260917.md` | The claim-to-passage document: for each reference, the sentence that cites it and the quoted passage that supports it. Numbered 1–52, in step with the reference list. |

**Two earlier `.docx` snapshots are kept beside it** so either post-delivery pass can be inspected
or reverted: `..._pre_suppfile3.docx` (before the Supplementary File 3 entry) and
`..._pre_fig4split.docx` (before the Figure 4 split). Neither is the current manuscript.

### Section structure

Abstract · Introduction · Materials and methods · Results and discussion · Conclusions · Data
availability · Software availability · Supplementary material · Reporting guidelines ·
Preregistration · Ethics and consent · Author contributions · Competing interests · Grant
information · Acknowledgements · References.

---

## 2. Figures

The figures live on **Page 2 (`1013:2`) of Figma file `t8bFgusleBEwB9ht7rORCH`**
("FL-harmonization-article"), assembled 2026-09-20. There is no exported PDF set yet — the canvas
is the current state, and it is a first pass that expects Daniil's hand correction.

### Main figures (6)

| Figure | Frame | Source |
|---|---|---|
| Figure 1 | `746:22` | Was Extended Figure 1 — approaches compared by global metrics |
| Figure 2 | `746:24` | Was Extended Figure 2 — local metrics |
| Figure 3 | `746:25` | Was Extended Figure 3 — distributional similarity, NA genes and samples |
| **Figure 4** | `1255:2` | New. Marker-gene preservation and cross-batch rank structure (classes L, M). Panels A–G |
| **Figure 5** | `1255:3` | New. Cross-batch prediction and the cross-election structure (class N). Panels A–G |
| **Figure 6** | `1255:4` | New. The recipe for selecting metrics. Fully vector, every character a TEXT node |

### Supplementary figures (14)

Supplementary Figures 1–10 are the former Extended Figures 4–13, **renamed only** — no artwork was
redrawn, moved or restyled. Supplementary Figures 11–14 are new: marker panel QC (`1255:5`),
harshness by L/M/N (`1255:6`), the gene-by-method clustermap (`1255:7`), and the two remaining
expression scatters (`1255:8`).

### The artwork on disk

| Path | What is there |
|---|---|
| `figures/panels_260917/` | The 18 Article 2 panels `a2_p1`–`a2_p18`, each as **pdf, svg and png** (21 files per format, because `a2_p14` has four method variants). The PDFs are the vector masters. |
| `figures/recipe_assets_260917/` | The 12 text-free SVG assets behind Figure 6, including `recipe_lobo_scheme.svg`. |
| `figures/figma_layout_260920.md` | The placement spec: every frame's position and size, and every panel's letter, x, y, width and height inside its frame. Regenerating a frame starts here. |
| `figures/panels_260917/editable_260920/` | Per panel: the text-free `_artwork.svg`, its `_artwork_300dpi.png` Figma fill, and the text-only `_text.svg` overlay, plus `overlay_manifest.json` (geometry, `sx`/`sy`, text counts, checksums). Built by `tools/split_panel_text_260920.py`. |
| `figures/figma_snapshots/` | `page2_{before,after}_260920.json` — the geometry proof of §5 — and `page2_{before,after}_editable_260920.json` for the editable-text pass. |

**Each panel is a Figma frame holding locked raster artwork and editable text.** The artwork is a
300 dpi render of the panel with every `<text>` element stripped out; the text is a `labels` group
of Inter `TEXT` nodes imported from a text-only SVG pre-scaled to the panel's placed pixel box. That
is 1,966 editable nodes across the 21 panels, against the 93,824 vector nodes a full SVG import
would have cost — one expression scatter alone is 23,357. The vector originals stay in
`figures/panels_260917/`. Figure 6 was already fully vector.

---

## 3. Tables — the nine that every number comes from

`tables/` holds the only tables a manuscript number may be quoted from. All nine are written by one
script, `analysis/article2_generalizability.py`, which asserts the analysis set on every run.

| Table | Rows × cols | What it holds |
|---|---|---|
| `A2_T0_shambhala_identity_260917.csv` | 79 × 6 | Column-by-column proof that `shambhala_P0std_Q0std` and `20_shambhala` are the same method |
| `A2_T1_analysis_set_census_260917.csv` | 2,234 × 293 | The analysis set: every approach with its flags and its class L, M and N metrics in harmonized, raw and difference form |
| `A2_T2_generalizability_ranking_260917.csv` | 2,234 × 27 | All approaches ordered by the generalizability index, with the six metrics it averages |
| `A2_T3_cross_election_matrix_260917.csv` | 9 × 10 | Jaccard overlap between the elected sets of every pair of metric classes |
| `A2_T4_method_census_by_class_260917.csv` | 121 × 4 | Which methods each class elects, counted |
| `A2_T5_per_batch_folds_260917.csv` | 3,521 × 9 | Per-batch F1 and AUC for the prediction-best and clustermap-best approaches, both targets |
| `A2_T6_agreement_specific_260917.csv` | 61 × 15 | The 61 approaches only the cross-batch agreement class elects |
| `A2_T7_harshness_by_lmn_260917.csv` | 7 × 9 | Seven biology-facing metrics across the three method harshness tiers, with Kruskal–Wallis |
| `A2_T8_fold_composition_260917.csv` | 33 × 6 | The census of held-out batches: class count, fold count, median size and score |

Reproduce them all with:

```bash
source ~/venvs/collagen_3_11/bin/activate
cd article_2_extended_comparison
python analysis/article2_generalizability.py --date-tag 260905 --out-dir tables/
```

---

## 4. Supplementary material

### Supplementary files (3 workbooks, in `supplementary/`)

Built by `analysis/build_supplementary_workbooks.py`. **Every workbook opens with a plain-language
README sheet** listing each following sheet, what it holds, its row count and its source table, and
**every data sheet carries a provenance line in row 1** naming the source table and the filter, so a
sheet lifted out of the workbook is still self-describing. Column headers are on row 2, data from
row 3.

| Workbook | Sheets | Size |
|---|---|---|
| **`A2_Supplementary_File_1_260917.xlsx`** — the analysis set and its metrics | README · `Analysis_set` · `Canonical_set_reconciliation` · `Generalizability_ranking` · `Method_census_by_class` · `Strategy_and_imputation_summary` · `Harshness_by_LMN` | 5.4 MB |
| **`A2_Supplementary_File_2_260917.xlsx`** — cross-batch structure and prediction | README · `Cross_election_matrix` · `Elected_sets_by_class` · `Agreement_specific_61` · `Margin_raw_and_delta` · `Per_batch_folds` · `Fold_composition` | 0.6 MB |
| **`A2_Supplementary_File_3_260917.xlsx`** — the marker gene panel | README · `Panel_coverage_by_attempt` · `QC_gate_sweep` · `Rho_by_signature` · `Narrow_set_56_genes` | 0.1 MB |

Two sheets are not stored as an `A2_T*` table and are derived in the builder from the same module
the tables came from, so a workbook cannot disagree with a table: `Elected_sets_by_class`, which
needs the election itself, and `Strategy_and_imputation_summary`, an aggregate over `A2_T1`. Two
sheets carry a second table underneath the first, each with its own provenance line:
`Canonical_set_reconciliation` (the 12-step 2,407 → 2,234 ledger, with the Shambhala identity check
below it) and `Strategy_and_imputation_summary` (the method-by-strategy medians behind panel
`a2_p7`).

`supplementary/duplication_check_260917.md` is the uniqueness check against Article 1's three
supplementary files. **Verdict: no Article 2 sheet reproduces a measurement column of any Article 1
supplementary file** — the only shared columns are join keys.

### The extended-comparison document

This directory's original purpose. `manuscript_versions/` holds four snapshots; **never delete or
overwrite one**, the audit cites them by name.

| Snapshot | State |
|---|---|
| `Harmonization_metrics_extended.docx` | The original. Every edit pass starts from this file. |
| `Harmonization_metrics_extended_260802.docx` | Superseded — do not use, do not extend. |
| `Harmonization_metrics_extended_260802_v2.docx` | 673 revisions. The current *extended-document* line, on its own numbering. |
| **`Harmonization_metrics_extended_260920_v3.docx`** | 691 revisions. **Article 2's numbering**, and a proposal awaiting Daniil's decision (§7). |

---

## 5. How the work is verified

Run from this directory with `source ~/venvs/collagen_3_11/bin/activate` first. All four pass as of
2026-09-20.

```bash
# every number in the draft traces to a table or the evidence file
python tools/audit_numbers.py manuscript/FL_metric_classes_F1000_260917.md \
       --tables tables/ --evidence workflow_runs/260919_run1/01_numbers.json

# register, section budgets, em-dash and banned-phrase gate
python tools/check_style.py manuscript/FL_metric_classes_F1000_260917.md --journal f1000

# no 8-gram shared with Article 1 or the extended document
python tools/check_overlap.py manuscript/FL_metric_classes_F1000_260917.md \
       --against ../figures_for_article/FL_manuscript_versions/FL_harmonization_article_NAR_260802_3rd_iteration.docx \
       --against manuscript_versions/Harmonization_metrics_extended_260802_v2.docx --ngram 8

# tracked changes are well-formed and reject-all restores the original
python ../.claude/skills/nar_review_tools.py validate \
       manuscript/FL_metric_classes_F1000_260917_pre_fig4split.docx \
       manuscript/FL_metric_classes_F1000_260917.docx
```

**Read the number audit for what it is.** It tests presence, not meaning: a value can match a column
it did not come from. Provenance is a presence match *plus* a named filter or a recorded
re-derivation, and `workflow_runs/260919_run1/06_provenance.md` marks which numbers have that.

**The Figma geometry check** is the diff between the two snapshots in `figures/figma_snapshots/`.
It passes: **0 geometry changes, 0 removed nodes**; 26 names changed (13 frames and their 13 title
TEXT nodes) and 14 nodes are new (7 frames, 7 titles).

---

## 6. What changed after delivery, and who approved it

The workflow delivered the manuscript on 2026-09-19. Two changes were made afterwards, both on
Daniil's explicit decision on 2026-09-20, and both applied to the `.md` and to the `.docx` as Word
tracked changes:

1. **Supplementary File 3 named in the manuscript** (`tools/apply_supp_file3_entry.py`). The
   marker-panel figures are used, so plan §7's condition for building a third workbook was met, and
   the Supplementary material section had to name it.
2. **The Figure 4 split** (`tools/apply_figure4_split_edits.py`). Figure 4 keeps two of its four
   expression-scatter grids and the other two become Supplementary Figure 14. Four full-width grids
   would make the Figma frame about 9,500 px tall; a 2×2 arrangement would drop the facet labels to
   roughly 4 pt. Figure 4 is relettered A–G throughout.

A third script, `tools/apply_extended_doc_v3_260920.py`, built the v3 extended document from the
original.

---

## 7. Open items — what still needs Daniil

| # | Item | Blocks |
|---|---|---|
| 1 | **Cut a DOI-bearing release of `Nikit357/FL_harmonization`.** The manuscript carries `[TO CONFIRM: new FL_harmonization release DOI]` until it exists | Software availability |
| 2 | **Which of the ten affiliation-2 authors hold employment.** The declaration asks the question explicitly rather than guessing | Competing interests |
| 3 | **Is Zenodo record 22737294 published?** Project memory records it as fully uploaded 2026-09-14 but **not published**, so the DOI quoted in Data availability may not resolve | Data availability |
| 4 | **D1 / D6** — three values and seven fold-population counts whose locus is the pinned snapshot or `prediction_folds_long.csv` rather than a file under `tables/`. Promote the columns into a table, or accept the exception knowingly | A stated rule, not a wrong number |
| 5 | **Accept or reject `Harmonization_metrics_extended_260920_v3.docx`**, the renumbering proposal for the extended document | The extended-document line |
| 6 | **Hand-correct the Figma canvas.** Worth an eye: Figure 4 is 6,229 px tall even after the split, and the two decision diamonds in the Figure 6 spine carry labels close to their outline | Figure delivery |

Items 1–4 are recorded in full, with their evidence, in
`workflow_runs/260919_run1/06_open_items.md`.

**Article 2 is delivered, not cleared for submission.** That is gate 4's own verdict and nothing
since has changed it.

---

## 8. Directory map

```
article_2_extended_comparison/
├── README.md                      ← you are here
├── f1000_article2_plan_260917.md  the plan of record: §10 checklist, §11 log
├── f1000_article2_revision_plan_260924.md  the plan of revision round 1
├── CLAUDE.md                      working rules for this directory
├── manuscript/                    the manuscript, legends, references, support doc
├── manuscript_versions/           the four extended-document snapshots
├── supplementary/                 the three .xlsx workbooks + the duplication check
├── tables/                        A2_T0–A2_T8, the only quotable tables
├── figures/
│   ├── panels_260925/             revision round 1: the 8 composite figures
│   ├── panels_260917/             the 18 panels in pdf, svg, png
│   │   └── editable_260920/       text-free artwork + text-only overlays for Figma
│   ├── recipe_assets_260917/      the 12 text-free SVGs behind Figure 6
│   ├── figma_snapshots/           before/after Page 2 geometry
│   ├── figma_layout_260920.md     the frame and panel placement spec
│   └── recipe_figure_assets.py    the script that draws the recipe assets
├── analysis/
│   ├── article2_generalizability.py     the analysis set, the election, the nine tables
│   ├── build_supplementary_workbooks.py the three workbooks
│   └── build_numbers_json.py            the evidence file the audit reads
├── tools/                         the three gates + the docx edit scripts
├── workflows/                     the multi-agent workflow script
└── workflow_runs/
    ├── 260917_phase1|2|3/         scaffolding, numbers, literature
    ├── 260919_run1/               the run that produced the draft, + RUN_REPORT.md
    └── 260924_run1/               revision round 1, + RUN_REPORT.md
```

---

## 9. The data the paper rests on

**2,234 approaches** — 31 harmonization methods × 14 filter strategies × 3 imputations × 2
post-removal settings, over 7,174 B-cell lymphoma transcriptomes. The set is Supplementary File 3
of Article 1 filtered to `pct_samples_allNA < 5`, with metric groups L, M and N joined from the
pinned snapshot `metrics_comprehensive_260905.csv`.

**Shambhala-2 carries two names, and the rename is the first operation of every load.** The metric
snapshot stores 18 parameter variants named `shambhala_P0std_Q0std` and so on; the benchmark kept
one representative as `20_shambhala`. They are the same method — the 84 shared keys agree on 78 of
79 numeric columns, the exception being wall-clock compute time. **Skipping the rename silently
drops those 84 approaches and yields 2,150**, which is the wrong denominator for every count in the
paper. `article2_generalizability.py` asserts the 2,234 and the 31 on every run and fails loudly if
a snapshot changes underneath the manuscript.
