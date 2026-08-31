---
name: scientific-review
description: Review and rewrite Daniil's scientific manuscript prose to his ten editing principles — delete proofless and marketing statements, make every number traceable to a named table or figure panel, renumber figures/tables/supplementary files by order of first citation, recalculate every quoted number from the source data, and enforce plain precise scientific language. Writes every change back as Word tracked changes (suggestion mode) and never touches in-text citations. Use when asked to review, edit, tighten, polish or fact-check a manuscript, a Results/Discussion section, an abstract, or a figure legend — whether the target is a .docx, a .md draft or text in the conversation.
---

# Skill: scientific review and rewriting (Daniil's principles)

## When to invoke

Whenever Daniil asks you to **improve, review, tighten, fact-check or rewrite scientific
manuscript text**. Triggers:

- "Review this manuscript / this section / this paragraph."
- "Edit my Results", "polish the Discussion", "tighten the abstract".
- "Check my numbers", "verify the statistics against the tables".
- "Apply your suggestions as tracked changes."
- Any time **you** have drafted manuscript prose and are about to hand it back — run Part B on
  your own draft before showing it. Most of the defects this skill catches were produced by
  Claude, not by Daniil.

**Sibling skills.**
`nar-review` (in `FL_harmonization/.claude/skills/`) is the *referee* skill: it produces
a journal referee report with minor/major/critical severities, audits figure legibility and
guideline compliance. `word-rewrite` reformats a manuscript into a journal's structure. **This
skill is the author-side one**: it makes Daniil's own text meet his standard. They share
`nar_review_tools.py` and the same tracked-change machinery; use `nar-review` when the ask is
"act as a reviewer", this one when the ask is "make my text good".

---

## Two hard requirements — read before doing anything

### 1. Every change is a suggestion, never a silent rewrite

Changes to a `.docx` go in as **Word tracked changes**. The contract:

- **Accept All** yields the corrected text.
- **Reject All** restores the original **byte for byte**. This is verified, not assumed —
  `nar_review_tools.py validate` proves it.

Never overwrite the source file. Output is `<name>_<YYMMDD>.docx` beside it.

For non-docx targets (a `.md` draft, text in the conversation) the same rule applies in spirit:
present each change as a **proposal with the original beside it**, one per finding, and let Daniil
accept or reject. Never hand back a silently rewritten block. Per the repository protocol, Daniil
decides at every key step.

Where a change needs a judgement only Daniil can make — a global spelling choice, renaming a
pervasive term, whether a hypothesis is worth stating — **flag it with numbers and recommend; do
not make it.** State explicitly in the report that you did not change it.

### 2. Never touch the in-text citations

Citations are **Mendeley content controls** (`<w:sdt>` tagged `MENDELEY_CITATION`). Daniil edits
and refreshes them in Mendeley; a scripted edit cannot renumber them and must not try.

Concretely:

- **Never** rebuild a paragraph from its concatenated text. That is exactly what
  `word_rewrite_trackchanges.tracked_replace()` does, and it destroys every citation in the
  paragraph without an error. Use **`nar_review_tools.safe_tracked_replace`**, which edits only
  runs that are *direct children* of the paragraph, so anything nested in `w:sdt` or `w:hyperlink`
  survives untouched.
- **Never** pick an edit anchor that spans a citation. Check first:
  `scientific_review_tools.py anchors MS.docx --anchor "..."` returns `SAFE` / `UNSAFE` /
  `NOT FOUND` / `AMBIGUOUS`.
- Reference numbering **is** governed by P3 (order of first citation), but you do not implement
  it. When a structural move invalidates the numbering, **report it and tell Daniil to refresh
  Mendeley**; do not edit reference numbers by hand.
- Record the `<w:sdt>` and `MENDELEY_CITATION` counts before you start and require them unchanged
  afterwards. `citations` prints both; `validate` re-checks them.

Deleting a passage that contains citations is allowed and normal — but it leaves the content
controls behind as **orphan citation-only paragraphs**. That happened 28 times in the G3 revision.
The `numbers` subcommand counts them; report the count and tell Daniil to delete them in Word and
refresh Mendeley.

---

## The ten principles

Full statements, worked before/after examples and rationale: **`reference/principles.md`**, beside
this file. Read it before a first pass on a new manuscript. The one-line versions, in the priority
order to apply them (P10):

| | Principle | Applied by |
|---|---|---|
| **P5** | Every number recalculated from the source. No rounded ranges. | Part A |
| **P2** | Every number, GO term and named result points at the object that holds it. | Part A |
| **P3** | Figures, tables, supplementary files, panels and references numbered by first citation. | Part A |
| **P1** | No proofless, vague or self-promoting statements. | Part B |
| **P6** | The paper reports the current analysis, never its revision history. | Part B |
| **P7** | No editor notes, TODOs or placeholders survive into the document. | Part B |
| **P4** | Plain precise language; one subtheme per passage; single-valued terminology. | Part C |
| **P8** | Caveats once, in the place the reader expects, subordinate clause first. | Part C |
| **P9** | House style enforced mechanically (US spelling, plain-text exponents, lower-case p). | Part C |
| **P10** | Under time pressure do P5→P2→P3→P1/P6/P7 completely, and P4/P9 partially. Never the reverse. | — |

**The governing test for every sentence:** *would a referee know what evidence would refute it?*

---

## Tooling

```bash
source ~/venvs/collagen_3_11/bin/activate      # the ONLY venv with python-docx + lxml
V=~/venvs/collagen_3_11/bin/python
T=~/.claude/skills/scientific-review/scientific_review_tools.py
N=~/.claude/skills/nar_review_tools.py
SP=<your scratchpad dir>
```

| What | Command | Cost |
|---|---|---|
| Accept-all text (the object under review) | `$V $T extract MS.docx $SP/ms.txt` | free |
| Reject-all text (must equal the original) | `$V $T extract MS.docx $SP/ms0.txt --mode orig` | free |
| Citation inventory — **run this first** | `$V $T citations MS.docx` | <1k |
| Is my edit anchor citation-safe? | `$V $T anchors MS.docx --anchor "..."` | <1k |
| P1/P4/P5/P6/P7/P9 language audit | `$V $T prose $SP/ms.txt` | ~2k |
| P2/P5 untraceable-number audit | `$V $T numbers $SP/ms.txt` | ~2k |
| P3 sequential-numbering audit | `$V $T numbering $SP/ms.txt` | ~1k |
| All three at once | `$V $T audit $SP/ms.txt` | ~5k |
| What changed between two versions | `$V $T diff a.txt b.txt` / `--words` | ~3k |
| Body dump with indices and styles | `$V $N extract MS.docx $SP/body.txt` | ~23k for 17k words |
| Formatting, abstract cap, variants | `$V $N docx MS.docx` | ~1k |
| Tracked-change integrity | `$V $N validate MS.docx OUT.docx` | <1k |

**Do not use `mcp__*ctx_execute*` for docx edits** — those run in a throwaway sandbox and do not
persist file writes. Use Write + `python` via Bash. **Never use `rm`** (globally blocked); write to
unique paths in the scratchpad.

---

## Part A — Correctness, traceability, numbering (P5, P2, P3)

This is the part that finds real defects. Do it completely, always.

### A1. Inventory before touching anything

```bash
$V $T citations MS.docx          # record sdt / MENDELEY_CITATION counts
$V $T extract MS.docx $SP/ms.txt
$V $T audit $SP/ms.txt
```

Read the manuscript text once. Then locate the source of truth: the `output/` or
`supplementary/` directory, the scripts that wrote it, and the project `CLAUDE.md`.

### A2. Recompute every number (P5)

For each quantitative claim, in a fresh interpreter:

```python
import pandas as pd
fam = pd.read_csv('output/GO_families_fdr005.csv')
assert fam[fam.class_name=='LTR']['Term ID'].nunique() == 33
```

Rules learned the hard way:

1. **Never trust a previously printed value**, a `results.md`, or a `CLAUDE.md` "numbers worth not
   re-deriving" table. The Retroelements `CLAUDE.md` recorded a correlation as R = 0.661 for months
   when the measured value was R = 0.985.
2. **Reconstruct enumerated sets by query, never by counting the items in the sentence.** "6 GO
   terms with FDR between 0.05 and 0.1" — run the filter. In the G3 pass the true count was 10.
   This single check found two errors that had survived a human pass.
3. **Quote the crossing point, not the nearest checkpoint row.** A checkpoint table is a summary of
   a curve; if the claim is "converges by N", find where the curve actually crosses.
4. **Quote in the unit the reader can verify** — the unit on the axis of the figure being cited,
   not the unit the analysis script happened to emit.
5. **A cut-off is not a count.** "top 5 % = 1,436 genes" is a ceiling; ties at the boundary make the
   realised set smaller. Write "1,436 genes at maximum".
6. **Check every place the number appears** — abstract, results, caption, table, supplementary
   sheet. They drift.
7. **Check polarity.** Look up the value for the no-op or control condition and confirm the metric
   runs the direction the text claims.

### A3. Check every pointer (P2)

`$V $T numbers` lists claims with no pointer. Then, for each pointer that *does* exist, **open the
object and confirm the number is in it.** This is not automatable and it is where wrong pointers
are found.

- **If the claim contains an integer or a p-value, the pointer goes to a table or workbook sheet**,
  never to a figure. A figure supports a distribution, a trend, a topology.
- Give the sheet, not just the file: `(File S3, sheet GO_by_family)`.
- One pointer per claim, not one range for three claims.
- Nothing the main text argues from may live *only* in a supplementary workbook. If the text says a
  class is enriched, the printed table carries both the raw and the adjusted p.
- Every method — statistical, computational, AI — is cited with a version.

### A4. Audit the numbering (P3)

`$V $T numbering $SP/ms.txt` prints, per series, the order of first citation and the violations.
Read the output carefully:

- Legend lines are excluded by default, because legends sit at the end and would mask the
  violation.
- An object cited **only from another object's legend** is reported as `[REVIEW]`, not a violation:
  its position is the position of the object whose legend cites it. Confirm by hand.
- An object with a legend and **no citation anywhere** is a violation.

**A structural move triggers a full renumbering pass.** Moving Materials and methods ahead of
Results invalidates the numbering of the entire reference list and usually at least one
supplementary figure. Report the new order; do not treat it as a follow-up task. You do not renumber
references yourself — that is Mendeley's job (requirement 2).

**A partial renumbering is worse than none.** In the G3 pass the body was renumbered S13→S1 and the
legends were not, so the text cited `Figure S1A/B/C` for panels whose legend described something
else. Whenever you change a number, change it in the body, the legend, every panel letter, and the
figure-placement notes, or change none of them.

---

## Part B — Deletions (P1, P6, P7)

Deletions are always safe to propose and carry the highest ratio of improvement to risk.

`$V $T prose $SP/ms.txt` flags every construction. For each hit:

**P1 — ask: *what number would make this sentence unnecessary?*** If the number exists, put the
number in and delete the sentence. If it does not exist, delete the sentence.

| Delete on sight | Replace with |
|---|---|
| "verified rather than assumed", "measured rather than a visual statement" | the verification number |
| "X is what makes Y interpretable" | the bias it removes, stated once |
| "high robustness", "reliable baseline", "solid evidence" | the robustness statistic |
| "notably", "strikingly", "importantly", "remarkably", "clearly shows" | nothing |
| "The metal claim is now zinc-only" (a verdict about the paper) | the count and the terms |
| "so that a silent skip is impossible" (a diligence claim) | nothing — it belongs in code docs |

**Also proofless: unsupported claims about the literature.** "whether X affects Y remains untested"
asserts a negative about an entire field. Unless a systematic search was performed and can be cited,
delete it. The mirror image — describing five prior studies with zero citations — is the same defect.

**Not banned: labelled hypotheses.** "could indicate", "is consistent with", "we hypothesise" survive
*when paired with an explicit statement of what the design cannot show*. The distinction is
falsifiability, not confidence.

**P6 — ask: *would this sentence make sense to a reader who has never seen another version of this
paper?*** If no, delete it. "no longer significant", "at the previous threshold", "does not survive"
all go. The one legitimate form is a sensitivity statement phrased as a property of the data under a
**named** alternative threshold: *"(both FDR = 0.086), which would be significant under a more
relaxed FDR threshold of 0.1 but are rejected here."*

**P7 — resolve every editor note by doing the thing it describes, then delete the note.** Expected
count at submission: 0. If you must leave an instruction for Daniil, put it in the run report or a
separate markdown file, never in the `.docx`.

---

## Part C — Language and style (P4, P8, P9)

Last, because it touches the most text for the least risk reduction.

**P4a register.** No casual verbs ("TEs *sit* near genes" → "locate"), no editorial nudges ("falling
*just* outside the threshold"), no "at all", "again", "a lot of".

**P4b structure.** Reason before consequence: `Since [reason], [consequence]` beats `[consequence]
therefore [reason], and …`. Delete "therefore", "and so", "thus" when the clause order already
carries the logic. State a definition once, in one vocabulary.

**P4c terminology is single-valued.** A noun phrase with a technical meaning elsewhere in the paper
may not be reused generally ("class of gene" when "class" means TE class → "functional gene group").
A demonstrative may not reach back more than one clause — "the latter term" → the term's name.

**P4d one subtheme per passage.** Test for a subsection: *can you state, in one clause, what block of
results it contains, with no "and also"?* If not, split it or move the outlier. Keep methods that
share a null model adjacent.

**P4e tense and agreement.** Results in past tense. "respectively" on paired lists. A bare integer in
parentheses gets its unit — `(16 terms)`, not `(16)`, which reads as a citation.

**P8 caveats.** One statement, in Limitations or at the end of the Introduction, never mid-paragraph
and never twice. Form: `Although [what the design cannot do], [what it does do and what that
enables].` Never the reverse — a defensive disclaimer reads as an apology.

**P9 house style.** US spelling. Plain-text exponents (`2.3 × 10-91`, never Unicode superscript —
they break typesetting *and* make the number ungreppable, which defeats P5). Lower-case `p`
everywhere. Tables at first citation carrying both raw and adjusted p.

---

## Part D — Apply the changes as tracked changes

Write `apply_review_edits_<YYMMDD>.py` beside the manuscript.

```python
import sys
sys.path.insert(0, "~/.claude/skills")
from word_rewrite_trackchanges import insert_after, note_paragraph, set_revision_identity
from nar_review_tools import safe_tracked_replace          # NOT tracked_replace

set_revision_identity("Claude (scientific review 2026-08-09)", "2026-08-09T00:00:00Z")

EDITS = [ (anchor_text, [(old, new), ...]), ... ]
NOTES = [ (top_level_anchor_text, note_text), ... ]
```

Rules that matter, in order of how often they bite:

1. **Change only the words that change.** Two altered words → a two-word `del` plus a two-word
   `ins`; the rest of the sentence stays black. Daniil asked for this explicitly and it is what makes
   the diff reviewable. Whole-sentence replacement is justified only when the whole sentence is
   wrong.
2. **Check every anchor with `$T anchors` before writing the script.** `UNSAFE` means it crosses a
   citation — shorten it.
3. **Locate by text anchor, never by index.** Indices shift the moment you insert a note.
4. **Resolve every anchor to an lxml element reference *before* mutating anything.** After an edit
   the original wording lives in `<w:delText>`, which a `.//w:t` search no longer finds.
5. **`find_p` must assert exactly one match** and raise otherwise. A silent wrong-paragraph edit is
   worse than a crash.
6. **Anchors must match *visible* text** — original plus insertions, deletions excluded.
7. **Text inside an unaccepted `<w:ins>` is invisible to `safe_tracked_replace`.** Keep a separate
   in-place list and retype the `w:t` directly, but **only** after checking
   `ins.get(qn('w:author'))` is your own earlier pass. Never retype inside another author's
   revision — report it instead.
8. **Skip `[EDITOR NOTE]` / `[REVIEWER NOTE]` paragraphs in every sweep.** They quote old wording on
   purpose and poison first-occurrence scans.
9. **Insert notes after all text edits**, anchored to top-level body paragraphs only —
   `insert_after` on a paragraph inside a table cell puts the note in the cell.
10. **Where the right answer needs data you don't have, insert a note instead of guessing.** Where
    you can fix it but Daniil must confirm, do both. Roughly one note per three edits is right.
11. **Watch word caps.** If the abstract is at 199/200, compute the delta; don't eyeball it.
12. **Print a per-replacement report and iterate until zero `not-found` / `unsafe`.** Never ship a
    partially applied edit list.

### Mandatory validation

```bash
$V $N validate MS.docx MS_<YYMMDD>.docx
$V $T citations MS_<YYMMDD>.docx        # sdt and MENDELEY_CITATION must be UNCHANGED
$V $T extract MS_<YYMMDD>.docx $SP/reject.txt --mode orig
diff $SP/ms_original.txt $SP/reject.txt  # must be empty
```

All must pass:

1. XML parses; zero `<w:t>` inside a `<w:del>`; zero `<w:delText>` outside one; every revision has
   `w:id` + `w:author` + `w:date`, no duplicate ids.
2. **Reject-all equals the original exactly** — the proof the changes are genuinely tracked.
3. **`w:sdt` count and contents unchanged, hyperlink count unchanged** — the proof the citations
   survived.
4. Abstract still within the word cap after Accept All.

Word and LibreOffice are not available here. State that caveat and recommend Daniil open the file in
Word to eyeball the revision display before accepting anything.

---

## Part E — Report

Report to Daniil, in this order:

1. **The filenames** — original untouched, `<name>_<YYMMDD>.docx`, the edit script.
2. **Accept All = corrected, Reject All = original**, and that this was verified, not assumed.
3. **Citations intact**: the `<w:sdt>` / `MENDELEY_CITATION` counts before and after, and the count
   of orphan citation-only paragraphs he needs to clear in Word.
4. **The numeric findings first** — every number that did not reproduce, as a table:
   *quantity | as written | as recomputed | source file*. Nothing else in the report matters as
   much.
5. **The audit counts** — P1/P4/P5/P6/P7/P9 hits before and after, the numbering verdict.
6. **What you deliberately left for him**, and why.

Then accumulate: write anything durable into the sub-directory `CLAUDE.md` and, if it will matter
across sessions, into the auto-memory directory.

---

## Gotchas

- `~/venvs/collagen_3_11` is the **only** venv with `python-docx` + `lxml`. The analysis venv
  (`Retroelements_3_11`, etc.) does not have them, on purpose.
- `doc.paragraphs` index ≠ body-child index whenever tables exist. Iterate `doc.element.body`.
- Superscripts and subscripts sit in their own runs, so `R2`, `10-14`, `η2` do not exist as
  contiguous text. Target the surrounding words and leave the typography to a note.
- Word stores every table cell as its own `<w:p>`, so an inlined table floods a prose scan. The
  `numbers` subcommand filters short unpunctuated fragments; a bespoke scan must too.
- A flat word count is not evidence that little changed. The G3 pass moved 5 words net and made
  134 edits.
- `pdfinfo` / `pdffonts` / ImageMagick / Ghostscript are not installed. Use PyMuPDF.
- Never `rm`. Write to unique scratchpad paths.

---

## Worked precedent

`Retroelements/T2T_genes_article/T2T_transposons_genes/revision_G3/Daniil_review_of_Claude_examples_principles_260809.md`
is the full catalogue: 134 edit sites from Daniil's manual pass over Claude's G3 revision output,
every one classified by principle, with before/after text. `reference/principles.md` beside this
file is the distilled version. Read the catalogue when a judgement call is unclear — the answer is
usually already there as a worked example.

Headline defects that pass produced, as a calibration of what this skill is for: a figure cited for
a count it could not show; two enumerated GO-term counts that disagreed with the source table by 4
and by 1; a supplementary figure renumbered in the body but not in its legend; a supplementary
figure with a legend and no citation anywhere; 28 orphan citation paragraphs; seven editor notes
left in a document being prepared for submission.
