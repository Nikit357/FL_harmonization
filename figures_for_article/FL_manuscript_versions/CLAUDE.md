# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this directory is

A flat archive of `.docx` snapshots of the FL harmonization ("ComboBatch") manuscript for
Nucleic Acids Research (NAR). There is no code here — every file is a Word document. The
scripts that produced these snapshots live one level up in `../edit_python_scripts/` and are
documented in `../CLAUDE.md` (manuscript-review section) and the `nar-review` skill; read
those before running a new tracked-change pass. This file's job is narrower: it maps out
**which of the eleven `.docx` files here is which**, since the names alone don't make the
lineage obvious.

Never delete or overwrite a file in this directory — each one is a distinct point in the
review history and several are cited by hash/date in prior review reports.

## Two independent draft lineages

There are two unrelated manuscripts in this folder, not one linear history. They share no
common ancestor file and were reviewed by different people.

### Lineage A — early co-author draft (superseded, pre-NAR)

Title: *"Bulk transcriptomic harmonization tools benchmarking using germinal center lymphoma
dataset: a novel computational pipeline"*. Author list still uses a personal Gmail
correspondence address. Both files share `revision=721`, `modified=2026-06-28` (same save
session, not sequential edits of one another):

| File | ins/del | Notes |
|---|---|---|
| `FL_harmonization_article_v2_suggestions.docx` | 113/1 | Suggestions mode, almost nothing accepted yet (5,734 words / 21 pp) |
| `FL_harmonization_article_v3_reviewed.docx` | 150/52 | Further reviewed copy of the same draft |

This lineage was abandoned when the manuscript was rebuilt for NAR (Lineage B). Treat both as
historical reference only — do not resume editing them.

### Lineage B — main NAR line (current)

Title: *"Benchmarking of bulk transcriptomic harmonization tools across a multi-platform
germinal center B-cell lymphoma cohort identifies mutual nearest neighbours..."* (working
title evolved over the pass history). This is the manuscript under active review.

| # | File | Modified | Words/pp | ins/del | What produced it |
|---|---|---|---|---|---|
| 1 | `FL_harmonization_article.docx` | 2026-07-16 | 13,878 / 38 | 81/28 | Full draft in non-NAR format. Contains a Russian self-note, *"Переделать под NAR, свести вместе Результаты и Обсуждение"* ("Redo for NAR, merge Results+Discussion") — the origin of Lineage B's reformat. |
| 2 | `FL_harmonization_article_NAR.docx` | 2026-07-27 | 19,039 / 52 | 5/4 | Reformatted into the NAR template. Baseline before any review pass (near-zero ins/del = template changes only). |
| 3 | `FL_harmonization_article_NAR_260727.docx` | 2026-07-27 | 19,039 / 52 | 245/138 | `apply_nar_review_edits_260727.py` applied on top of #2 (`NAR_review_260727.md`: 12 critical/34 major/61 minor). |
| 4 | `FL_harmonization_article_NAR_260727_partially_edited.docx` | 2026-07-27 | 24,132 / 72 | 214/118 | Daniil manually accepted/expanded on top of #3 (word count grew — new content added, not just accept-all). |
| 5 | `FL_harmonization_article_NAR_260728.docx` | 2026-07-27 | 24,132 / 72 | 248/150 | `apply_nar_abbrev_edits_260728.py` on top of #4: PCR→PCReg rename, first-use definitions for AUC/tSNE/UMAP/PC/PCA/GEO/PBMCs/AWS/cLISI/iLISI/TPM/DSC/FSQN/QN. |
| 6 | `FL_harmonization_article_NAR_260802.docx` | 2026-08-02 | 18,210 / 57 | 189/48 | `apply_nar_review_edits_260802.py` (`NAR_review_260802.md`: 5 critical/13 major/47 minor). Word count drop from #5 implies prior tracked changes were accepted before this pass ran — this is a fresh base, not a continuation of #5's open revisions. |
| 7a | `FL_harmonization_article_NAR_260802_manually_edited.docx` | 2026-08-02 | 18,210 / 57 (194 paras, +4 vs #6) | 6/2 | Manual side-branch off #6 — small hand touch-ups, not developed further downstream. |
| 7b | `FL_harmonization_article_NAR_260802_2nd_iteration.docx` | 2026-08-02 | 18,210 / 57 (186 paras) | 66/710 | Automated branch off #6: `apply_nar_table_move_edits_260802.py` — Tables 3/4 tracked-deleted to Supplementary File 2, figure renumbering, Supp. Fig. 9 reference fix, 22 language edits (`NAR_review_260802_2nd_iteration.md`). The `del=710` spike is the two whole tables marked deleted row-by-row, not yet accepted. |
| 8 | `FL_harmonization_article_NAR_260802_2nd_iteration_from_google_docs.docx` | 2026-08-24 | no docProps (Google export strips them); 272 paragraphs | 2/0 | **Current / most advanced version.** See below. |

7a and 7b are siblings of #6, not sequential — pick whichever matches the change you're
extending; don't assume 7b supersedes 7a.

## The current file: Google Docs round trip (2026-08-24)

`FL_harmonization_article_NAR_260802_2nd_iteration_from_google_docs.docx` was produced by
importing #7b (`_2nd_iteration.docx`) into Google Docs for co-author review, then exporting
back to `.docx`. It is ahead of every other file in this folder on manuscript content:

- The author byline and affiliations are finalized (real names/affiliations replace the
  `"Nicolas Borisoff?"` / Cyrillic placeholder notes still present in #7b), and the
  correspondence email is now the corresponding author's institutional address
  (see the manuscript title page).
- All `[NAR EDITOR NOTE]` placeholders are resolved except one (abstract word-limit note).
- It carries **14 live `w:comments.xml` threads** (`Daniil Nikitin` / `Andrey Kravets`,
  2026-08-05 to 2026-08-11) — real open scientific review discussion, not editorial markup.
  Several are unresolved TODOs that affect Methods/Discussion/Results content. Read them with
  the docProps/comments snippet below before writing new manuscript text; the condensed
  discussion and action items are in project memory (see below) rather than duplicated here.

**Gotcha — the round trip degrades structure the existing edit scripts depend on.** Compared
to #7b, this file's Mendeley-citation `w:sdt` count dropped **121 → 19**, and `w:ins`/`w:del`
collapsed to near-zero. Google Docs' own suggestion-mode export does not preserve Word's
`w:ins`/`w:del`/`w:sdt` model faithfully. Before running any `safe_tracked_replace`-based script
from `../edit_python_scripts/` against this file:

1. Confirm how many in-text citations still round-trip as `w:sdt` vs. having been flattened to
   plain text (`grep -c '<w:sdt>' <(unzip -p FILE word/document.xml)` or the Python snippet
   below) — a citation that lost its `w:sdt` wrapper needs to be re-inserted as a citation, not
   just text-matched.
2. Treat this file like "editing a manuscript that already carries tracked changes" (see
   `../CLAUDE.md`) even though its own `w:ins`/`w:del` counts are low — the *content* already
   reflects several rounds of unaccepted edits from other files, now baked in as plain text.
3. Read `word/comments.xml` first — it holds live co-author questions that may change what the
   "correct" edit is, independent of anything in the NAR review reports.

## `_3nd_iteration.docx` (2026-08-24): citations restored, fonts normalized

`FL_harmonization_article_NAR_260802_3nd_iteration.docx` merges #7b's live Mendeley fields back
into #8's content: every one of the 65 surviving in-text `MENDELEY_CITATION_v3` `w:sdt` fields
in #7b was located inside #8 by token-level `difflib` alignment of the two documents' plain text
(both share the same lineage, so ~95% of the text matches verbatim) and spliced back in as a
real `w:sdt`, splitting/truncating whatever plain-text runs Google Docs had flattened it into. 62
of 65 placed cleanly; the other 3 were citations embedded in the Table 3/4 rows that pass #7b
tracked-deleted (`w:trPr/w:del` by `"Claude (NAR review, 2nd iteration 2026-08-02)"`) — those
rows are genuinely absent from #8's accepted text, so excluding them is correct, not a gap. The
`MENDELEY_BIBLIOGRAPH` field (a **block-level** sdt — its `w:sdtContent` holds 96 `w:p` elements
directly, one per reference, and the sdt itself is a child of `w:body`, not of a paragraph) was
restored the same way, replacing 97 flattened reference paragraphs in #8 whose concatenated text
matched the old field's rendered text exactly (byte-for-byte, confirming the reference list
itself was never re-edited in Google Docs). Every direct-run `w:rFonts` outside a `MENDELEY_*`
sdt was also renormalized from Google's `Quattrocento Sans`/stray `Arial`/`Roboto` back to
`Segoe UI` (body) / `Times New Roman` (`eastAsia`) — the font #7b uses throughout; sizes and
bold/color already matched, so only the family name needed fixing. The merge changed zero
visible characters: concatenated `w:t` text is byte-identical before and after (verified
programmatically), so all of #8's resolved author list, editor-note cleanup, and 14 live
co-author comments are untouched.

**Gotcha if you rebuild this kind of merge again:** don't wrap a block-level sdt (one whose
`sdtContent` already contains `w:p` children, like `MENDELEY_BIBLIOGRAPH`) inside a new
paragraph — a `<w:p>` cannot legally contain another `<w:p>`, and `.//w:p` will silently count
the nested ones too, making a removed-97/added-1 swap look like nothing happened (both counts
end up close to the original). Insert the copied block sdt as a sibling at the same level the
paragraphs it replaces lived at (`w:body`, not inside a wrapper paragraph).

## Inspecting a `.docx` without opening Word

No build/lint/test commands apply to this directory. The one recurring task is comparing
snapshots. Quick metadata + tracked-change footprint (no dependencies beyond stdlib):

```bash
python3 - "FILE.docx" <<'EOF'
import sys, zipfile
from xml.etree import ElementTree as ET
z = zipfile.ZipFile(sys.argv[1])
try:
    ns = {'cp':'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
          'dc':'http://purl.org/dc/elements/1.1/', 'dcterms':'http://purl.org/dc/terms/'}
    root = ET.fromstring(z.read('docProps/core.xml'))
    for tag in ('dc:creator','cp:lastModifiedBy','dcterms:created','dcterms:modified','cp:revision'):
        e = root.find(tag, ns); print(tag, ":", e.text if e is not None else None)
except KeyError:
    print("no docProps/core.xml (likely a Google Docs export)")
doc = z.read('word/document.xml').decode('utf-8','ignore')
print("ins:", doc.count('<w:ins '), "del:", doc.count('<w:del '), "sdt:", doc.count('<w:sdt>'))
print("has comments.xml:", 'word/comments.xml' in z.namelist())
EOF
```

For full paragraph/table text, use `python-docx` (`~/venvs/collagen_3_11/bin/activate`):
`docx.Document("FILE.docx").paragraphs` / `.tables`. To read live comment threads, parse
`word/comments.xml` for `w:comment` elements (`w:author`, `w:date`, nested `w:t`).

**Note:** `../CLAUDE.md` references a `nar_review_tools.py` module at
`.claude/skills/nar_review_tools.py` for these same inspections (`extract`/`docx`/`fields`/
`validate`) plus citation-safe tracked-edit helpers (`word_rewrite_trackchanges`,
`safe_tracked_replace`). That path does not currently exist in this checkout — the file was
found only under `~/Downloads/nar_review_tools.py`. Confirm it's present before invoking the
`nar-review` skill's documented commands, or ask Daniil where the checked-in copy went.
