> **Public copy.** This folder is the external material for Article 2 (F1000Research):
> a one-way, sanitized copy of the authors' working folder. Some files are withheld, and the
> affiliation, funding and competing-interest statements in the Markdown drafts point to the
> published article. See [`WITHHELD.md`](WITHHELD.md). Article DOI: *to be added on publication*.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this directory is

The home of the **"Harmonization metrics extended"** document line — the long-form,
metric-by-metric companion to the main FL harmonization (ComboBatch) article. It is a
*document* directory, not a code directory: three `.docx` snapshots plus the numerical audit
behind them. Nothing here is executed.

Two things about this document drive every decision made in it:

- **It is destined for GitHub, not for a journal.** Review passes over it cover language,
  grammar and numerical precision only. Scientific claims and the figures are left alone
  except where a stated number contradicts the data.
- **It narrates the extended metric trends** (PCReg, LISI, kBET, tSNE entropy, KS, DSC, ASW,
  graph connectivity, distance ratio, watermelon, harshness tiers, composite score) across
  2,234 approaches · 31 methods · 14 strategies · 87 scoring metrics, keyed to
  Extended Figure 1–13. Any new sentence must carry a number that reproduces from the metric
  table named below.

The repo root `CLAUDE.md` tracks this under "Next steps — Article 2"; `../project_overview.md`
has the research context.

## Article 2 in progress — the F1000Research manuscript built here since 2026-09-17

The directory now has a second life. Besides holding the extended document, it is where
**Article 2 for F1000Research** is written: *a metric-class comparison of harmonization
approaches*, the paper that asks which class of quality metric elects which approach, and whether
the classes agree. The plan of record is `f1000_article2_plan_260917.md`; its §10 is the phase
checklist and its §11 is the implementation log. Read the plan before changing anything below.

**The source document is v2, never v1.** Article 2 narrates the same metric families as
`manuscript_versions/Harmonization_metrics_extended_260802_v2.docx`, so a sentence copied from v1
carries numbers the audit of §0 already rejected. The same rule applies to the four "corrections"
v1 made that were in fact right.

### The sub-directories added for it

| Path | What is there |
|---|---|
| `analysis/` | `article2_generalizability.py` (the analysis set, the election, the nine `A2_T*` tables), `build_numbers_json.py` (the evidence JSON the audit reads), `build_supplementary_workbooks.py` (Phase 6, the three workbooks) |
| `tables/` | `A2_T0`–`A2_T8`, the only tables a manuscript number may come from |
| `supplementary/` | The three `.xlsx` workbooks and `duplication_check_260917.md` |
| `manuscript/` | The `.md` and the `.docx`, the figure legends, the reference list and the claim-to-passage support document |
| `figures/panels_260917/` | The 18 Article 2 panels (`a2_p1`–`a2_p18`), each in pdf, svg and png |
| `figures/recipe_assets_260917/` | The twelve text-free SVG assets of the recipe figure |
| `figures/for_figma_upload/` | The fallback target: complete SVGs for Daniil to upload if Figma is unreachable |
| `tools/` | The three gates (`check_style.py`, `audit_numbers.py`, `check_overlap.py`) plus the docx and literature helpers |
| `workflows/`, `workflow_runs/` | The multi-agent workflow script and its run artifacts; `260919_run1/` is the run that produced the draft |

### The analysis set — 2,234, and why it is not 2,150

Supplementary File 3 of Article 1, filtered to `pct_samples_allNA < 5`, gives **2,234 approaches
over 31 methods**, 14 strategies, 3 imputations and 2 post-removal settings. Groups L, M and N are
joined onto it from `metrics_comprehensive_260905.csv`, which is pinned.

**Shambhala-2 carries two names, and the rename is the first operation of every load.** The metric
snapshot stores 18 parameter variants named `shambhala_P0std_Q0std` and so on; Article 1 kept one
representative and recorded it as `20_shambhala`. They are the same method: the 84 shared keys
agree on 78 of 79 numeric columns, the exception being wall-clock compute time. Skipping the
rename silently drops those 84 approaches and yields **2,150**, which is the wrong denominator for
every count in the manuscript. `article2_generalizability.py` asserts the 2,234 and the 31.

### The anti-plagiarism contract

Article 2 must not reuse Article 1's or the extended document's wording. `tools/check_overlap.py`
is the gate: an 8-gram shared with either document fails the run unless it is in
`tools/overlap_allow.txt`, which holds only the grant and funding wording F1000 requires to be
identical. Run it, with `check_style.py` and `audit_numbers.py`, after any edit to the manuscript.

### Figma — assembled 2026-09-20

File `t8bFgusleBEwB9ht7rORCH`, **Page 2** (`1013:2`). The renaming is done: Extended Figures 1–3
are now `Figure 1`–`Figure 3` and Extended Figures 4–13 are `Supplementary Figure 1`–`10`, frames
and title TEXT nodes alike. **Renaming is still the only edit permitted to an existing frame**, and
it is verified by diffing `figures/figma_snapshots/page2_{before,after}_260920.json`: 0 geometry
changes, 0 removals.

Seven new frames sit at y = 11500 on the existing column grid and carry the 21 Article 2 panels at
the geometry of `figures/figma_layout_260920.md`. **Every character in every Article 2 frame is a
Figma `TEXT` node.** Each panel is a `FRAME` holding a locked `artwork` rectangle — a 300 dpi render
of the panel with its text stripped out — and a `labels` group of 1,966 Inter `TEXT` nodes imported
from a pre-scaled text-only SVG. `Figure 6 - Recipe` is fully vector and was already built this way.
The pipeline is `tools/split_panel_text_260920.py` and the runbook
`tools/figma_editable_text_260920.md`; the plan is `figma_editable_text_plan_260920.md` and the
geometry proof is `figures/figma_snapshots/page2_{before,after}_editable_260920.json` — 0 geometry
changes, 0 name changes. House style is Inter 10 pt for labels and Inter Bold 20 pt for panel
letters.

Six mechanical facts hold whatever a plan says. Never call `get_metadata` on the page root, never
on a whole figure frame (Extended Figure 1 alone returns ~3.5 M characters), and rename by **node
id**, because `Extended Figure 1` is a prefix of `Extended Figure 10`. Uploaded SVGs land on the
file's **current page**, which is sticky between `use_figma` calls — pin it to Page 2 first or they
land on Page 1 and must be reparented. **Figma's SVG reader ignores `font-size` written inside a
`style=` attribute** and imports the label at its own 10 px default; matplotlib writes typography
only into `style=`, so an overlay must carry it as presentation attributes (`font-size="7.5"`),
which are honoured exactly. **Only `Inter` is available in this file** — `Arial`, `Helvetica`,
`DejaVu Sans` and `Liberation Sans` all return `no` from `listAvailableFontsAsync()`. And
`upload_assets` with `nodeIds` **stores an image without attaching it**: all 21 POSTs return
`success` while every target keeps its old fill, so the fills must then be set explicitly from the
returned `imageHash`.

### Revision round 1 — 2026-09-24 to 2026-09-25

Plan of record: `f1000_article2_revision_plan_260924.md`. Run folder: `workflow_runs/260924_run1/`,
whose `RUN_REPORT.md` has the provenance table and the open items. Workflow script:
`workflows/article2_revision_260924.workflow.js`. It is a copy; the 260919 script is untouched. The
round was run interactively, phase by phase.

**The base is Daniil's edited copy.** That is
`manuscript/FL_metric_classes_F1000_260917_edited_Daniil.docx`, and it is never modified. His wording
wins; revisions extend it. The four review documents:

| File | What it holds |
|---|---|
| `manuscript/FL_metric_classes_F1000_260917_edited_Daniil.docx` | The base: 178 paragraphs, 37 comments. Daniil reviewed paragraphs 0–77 and 149–160 |
| `manuscript/daniil_comments_260924.md` | The 37 comments, each with its exact anchor span |
| `manuscript/daniil_diff_260924.md` | Paragraph diff against the agentic draft: 61 rewritten, 10 inserted |
| `manuscript/daniil_review_principles_260924.md` | **The standard for the unreviewed half** (paragraphs 78–148), inferred from the two above; its §G checklist is binding |

**Invariants that hold for every later pass:**

- **Metric census 344 / 334 / 87.** That is 344 registry metrics, 334 non-metadata and 87
  scoring. It comes from Article 1's `Supplementary File 2.xlsx`, sheet `Metric_polarity`
  (`09_metric_census.md`).
- **Citation freeze.**
  - Never add, move or edit a citation.
  - The 46 Mendeley content controls and the 4 numeric brackets are checked on every output:
    `[38]` ×2, `[50,51]`, `[52]`.
  - New references go to a proposal list (`11_citations_to_insert.md`) for Daniil to insert
    through Mendeley.
- **Supplementary File 3 naming.** It spells the PCReg columns `PCReg_*`. `load_analysis_set()`
  renames them to `pcr_*`; without the rename the global class shrinks to four DSC metrics
  (`15_pcreg_fix.md`).
- **At most five main-text tables** (currently 4). This is asserted by `TABLE_REGISTRY` in
  `analysis/article2_generalizability.py`. Anything beyond goes to a Supplementary File sheet.
- **Renumbering is the last step.**
  - Drafts cite new figures by token (`[FIG:fig_election]`).
  - `tools/renumber_260925.py` numbers everything once, by first citation in the finished text.
  - Never renumber by hand, and never reuse an older map.
- **The deliverable is a tracked-changes `.docx`** against the base.
  - Accept All gives the revision.
  - Rejecting Claude's revisions gives Daniil's copy.
  - The stock `nar_review_tools.py validate` misreports a deletion nested inside one of Daniil's
    insertions. The builder checks Reject All with Word's semantics instead.

**Pipeline order after any edit.** Edit the drafts `03a_draft_reviewed.md`,
`03b_draft_unreviewed.md` and `08_legends.md`. Never edit the assembled manuscript. Then:

```bash
python tools/assemble_draft_260925.py        # drafts → 03_revision_edits.json + the .md
python tools/renumber_260925.py              # → 03_revision_edits_final.json, 21_renumber_map.md
python tools/build_tracked_revision_260924.py  # → manuscript/FL_metric_classes_F1000_260925.docx
M=manuscript/FL_metric_classes_F1000_260925.md
python tools/check_principles.py $M
python tools/audit_numbers.py $M --tables tables/ --evidence workflow_runs/260924_run1/01_numbers.json
python tools/check_overlap.py $M --ngram 8 \
    --against ../figures_for_article/FL_manuscript_versions/FL_harmonization_article_NAR_260802_3rd_iteration.docx
python tools/check_style.py $M --journal f1000 --budgets revision_260925
```

**Gate options matter.**

- Without `--evidence`, the audit misses the figure-derived counts: 325, 529, 1,187 and the Zenodo
  record number.
- Without `--against`, the overlap gate also compares against the extended document. That is
  Daniil's own and may be reused (rule 17).

**New tools of this round:**

- `tools/check_principles.py`: the ten checks of the principles document.
- `tools/assemble_draft_260925.py`, `tools/renumber_260925.py` and
  `tools/build_tracked_revision_260924.py`: the delivery pipeline above.
- `tools/split_figure_text_260925.py`: the Figma text overlays.
- `figures/article2_figures_260925.py`: the eight composite figures.

**Software versions stated in Methods.** These are the real versions of `~/venvs/collagen_3_11`,
where the tables are computed: Python 3.11, pandas 2.3.3, numpy 1.26.4, scipy 1.17.1,
scikit-learn 1.8.0, statsmodels 0.14.6, matplotlib 3.10.8, seaborn 0.13.2. The scipy 1.12.0 pin in
the root `CLAUDE.md` is not what is installed.

## Moved here 2026-09-15 — paths in the producing scripts are now stale

These files lived in `../figures_for_article/` until 2026-09-15 (git still shows them as
deleted there, and this directory as untracked). The scripts that produced them did **not**
move and were never updated for the move. Two concrete breakages to fix before re-running
anything:

| Script (in `../figures_for_article/edit_python_scripts/` or `figure_drawing_scripts/`) | What breaks |
|---|---|
| `apply_extended_metrics_edits_v2_260802.py` | `SRC`/`DST` are bare filenames (`Harmonization_metrics_extended.docx`), resolved against the cwd. It only works if run from `manuscript_versions/` here, or with both constants repointed. |
| `recompute_extended_metrics_260802.py` | `SUPP_FILE_3` points at `current_figures_tables_for_article_260802/Supplementary File 3.csv.gz`; that whole folder has since been deleted. Use `../figures_for_article/supplementary_260802/Supplementary File 3.csv.gz` (same date, same content) or the newer `supplementary_260824/` copy, and say which one you used. |

The Extended Figure artwork the document references also no longer lives in the deleted
`current_figures_tables_for_article_260802/` — the current set is
`../figures_for_article/current_figures_tables_for_article_260915/Extended Figure 1–13.{pdf,jpg}`.
The local `figures/` folder here is empty and reserved for this document's own artwork.

## The four snapshots

The first three share the same docProps (`revision=1813`, `modified=2026-08-01`) — Word metadata was
never rewritten by the edit scripts, so **only the tracked-change counts distinguish them.**

| File | ins/del | What it is |
|---|---|---|
| `manuscript_versions/Harmonization_metrics_extended.docx` | 0/1 | The original, 8,819 words / 31 pp. Both edit scripts read *this* file as their source. |
| `manuscript_versions/Harmonization_metrics_extended_260802.docx` | 155/156 | **Superseded — do not use, do not extend.** First, narrower pass (`apply_extended_metrics_edits_260802.py`): it ran on a 2,150-row subset, so four of its "corrections" changed numbers that were in fact right (all-approach LISI median and MAD, the best-vs-rest Mann–Whitney p, both LISI correlation figures), and its figure sweep corrupted `Supplementary Figure 6` into `Supplementary Extended Figure 1`. |
| `manuscript_versions/Harmonization_metrics_extended_260802_v2.docx` | 344/329 (673 revisions) | **Current.** `apply_extended_metrics_edits_v2_260802.py`: 328 anchored edits + 112 figure-reference rewrites + an appended "Summary of metric trends" section. Validated: 0 `w:t` inside `w:del`, 0 stray `w:delText`, 0 duplicate revision ids, reject-all restores the original exactly. |
| `manuscript_versions/Harmonization_metrics_extended_260920_v3.docx` | 691 revisions | **Article 2's numbering.** Built by `tools/apply_extended_doc_v3_260920.py` **from the original**, not from v2: all 123 of v2's "Extended Figure" references live inside v2's own unaccepted `w:ins`, which no tracked-change tool can safely edit. It reuses every anchored number and language edit of the v2 pass and replaces only the figure map — original Figures 6–8 become Figures 1–3, original Extended Figures 1–10 become Supplementary Figures 1–10, and every borrowed reference gains "of the source benchmark" so no label means two things. Validated: reject-all restores the original exactly. |
| `manuscript_versions/Harmonization_metrics_extended_audit_260802.md` | — | The audit behind v2: ~60 numbers that reproduced exactly, 54 that did not (with cause), the figure renumbering, and the new section. Read it before touching any number in the document. |

**Never chain snapshots.** Every pass starts from the original — v3 does too, for the reason its row gives. **Never chain v1 and v2.** Both start from the original and both re-apply the figure
renumbering; running v2 on top of v1's output double-renumbers. Never delete or overwrite a
snapshot either — the audit cites them by name.

## Reproducing or adding a number

The metric table choice is the single most error-prone step, and the audit's §0 settles it:

- Use `metrics_comprehensive_260609.csv` (via `figures_helpers.load_metrics_data()`) or
  `Supplementary File 3.csv.gz`. Supp. File 3 (2,407 × 93) is authoritative for anything
  polarity-adjusted; 260609 is a proper subset of it missing the 84 `20_shambhala` rows, and is
  the only source for the un-normalized metrics Supp. File 3 omits (`ilisi_mean_*`, `exp_*`,
  `pct_var_pc*`, `r2_*`) — state n = 2,150 when quoting those.
- **Never `metrics_comprehensive_260527.csv`.** It predates strategies I/J/K (11 strategies
  only) and was computed on a different set of prepared matrices: 0 of 66 numeric columns agree
  with Supp. File 3. Every mean, median and interval derived from it contradicts the article.

Conventions the document already follows: MAD is the plain (unscaled) median absolute
deviation; per-method and per-strategy summaries in heat-map paragraphs are means over runs,
matching the figures, which average across imputations and post-removal variants.

**Open defect — don't quote the harshness direction.** The method-harshness composite ordering
(low/medium/high tiers) recomputes opposite to the published values in every recipe tried; it
is unresolved pending Daniil's own re-derivation from
`../figures_for_article/Finally_assembled_figures_for_article.ipynb` (Figure 6A). This affects
finding 4 of the appended "Summary of metric trends" section. Do not "fix" the numbers to the
recomputed ones.

```bash
source ~/venvs/collagen_3_11/bin/activate
cd ../figures_for_article
python figure_drawing_scripts/recompute_extended_metrics_260802.py            # all sections
python figure_drawing_scripts/recompute_extended_metrics_260802.py snapshots  # 260527 vs 260609
```

## Inspecting a snapshot without opening Word

```bash
python3 - manuscript_versions/Harmonization_metrics_extended_260802_v2.docx <<'PY'
import sys, zipfile
from xml.etree import ElementTree as ET
z = zipfile.ZipFile(sys.argv[1])
ns = {'cp':'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
      'dc':'http://purl.org/dc/elements/1.1/', 'dcterms':'http://purl.org/dc/terms/'}
root = ET.fromstring(z.read('docProps/core.xml'))
for tag in ('dc:creator','cp:lastModifiedBy','dcterms:modified','cp:revision'):
    e = root.find(tag, ns); print(tag, ":", e.text if e is not None else None)
doc = z.read('word/document.xml').decode('utf-8','ignore')
print("ins:", doc.count('<w:ins '), "del:", doc.count('<w:del '), "sdt:", doc.count('<w:sdt>'))
PY
```

These files carry **no** Mendeley `w:sdt` citation fields and no `comments.xml`, which makes
them much simpler to edit than the NAR manuscript snapshots in
`../figures_for_article/FL_manuscript_versions/` — a plain text-anchored `safe_tracked_replace`
is safe here. For full text/tables use `python-docx` from `~/venvs/collagen_3_11`.

## Related directories

| Path | What is there |
|---|---|
| `../figures_for_article/CLAUDE.md` | The tracked-change edit-script pattern, the review-pass registry, and the supplementary-file builders. Read it before writing a new `apply_*_edits_*.py`. |
| `../figures_for_article/FL_manuscript_versions/` | The main NAR manuscript line — a *separate* document, not a version of this one. |
| `../harmonization-metrics/metric_tables/` | `metrics_comprehensive_*.csv` snapshots. |
| `../.claude/skills/` (`nar-review`, `scientific-review`, `word-rewrite`) | The review/tracked-change skills, plus `nar_review_tools.py` — run `python ../.claude/skills/nar_review_tools.py validate SRC.docx DST.docx` after any new edit pass here (v2 passed it: 673 revisions, ALL CHECKS PASSED). |

## Public mirror

This folder is published as `article_2_extended_comparison/` in the public `FL_harmonization`
repository, the article's external material. The copy is one-way and regenerated by
`../public_sync/sync_article2_public.py`: a dry run stages, sanitizes and gates; `--apply`
writes the mirror; committing and pushing stay manual. The public copy is never edited by hand.

The gate fails closed. A new file that carries an affiliation, a funding or competing-interest
statement, an absolute path, or any per-sample value stops the sync until it has a row in
`../public_sync/article2_scrub_map.tsv` or a line in `../public_sync/article2_exclude.txt`.
Two habits keep it passing:

- **Rasterize per-sample scatters** (`rasterized=True`). A vector scatter with thousands of
  point marks fails gate G5.
- **Save workbooks from code, not from Excel.** Excel records the save folder inside
  `xl/workbook.xml`; the sync strips it, but only from `.xlsx` files.
