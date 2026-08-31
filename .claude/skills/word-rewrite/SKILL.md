---
name: word-rewrite
description: Rewrite, reformat, or restructure a Microsoft Word .docx file as genuine tracked changes — typically bringing a manuscript draft into a journal's required structure (adding or reordering sections, converting citations), so Accept All gives the rewritten document and Reject All restores the original exactly. Use for restructuring a manuscript; to referee one and apply corrective edits, use nar-review instead.
---

# Skill: Word Rewrite

## When to invoke

Use this skill whenever Daniil asks you to **rewrite, reformat, or restructure a Microsoft
Word `.docx` file with tracked changes** — typically to bring a manuscript draft into a
journal's format (e.g. NAR), or any edit where he wants to review your changes and
accept/reject them in Word. Recognizable triggers:

- "Rewrite this Word file according to <guidelines> … in track changes mode."
- "Reformat / restructure my manuscript draft and let me review the edits."
- "Add the missing sections and flag what I must fill in myself."
- "Save it under a new file name so I keep the original."

Core promise of this skill: **every change you make is a genuine Word tracked revision**
(`<w:ins>` / `<w:del>`), so *Accept All* produces the clean rewritten document and *Reject
All* restores Daniil's exact original. Gaps you cannot fill are left blank with a red
"[EDITOR NOTE]" so he completes them by hand.

`python-docx` has **no native track-changes support** — you must write the revision XML
yourself. A ready-made helper library lives one level up, in the `.claude/skills/` root:
`.claude/skills/word_rewrite_trackchanges.py`. Import it; do not rewrite it from scratch.

Always work inside the project venv: `source ~/venvs/collagen_3_11/bin/activate`
(`python-docx` and `lxml` are installed there).

---

## Guiding principles (learned from the NAR rewrite)

1. **Never fabricate scientific content.** Preserve the author's body text verbatim. Only
   change formatting, structure, citations style, and clearly-marked placeholders. Where
   real content is missing, insert a blank + an EDITOR NOTE saying what to add and how —
   do not invent data, references, or results.
2. **Everything is reversible.** Deletions are tracked (`<w:del>`), never hard-removed —
   even images stay inside the `.docx` archive so rejecting the deletion restores them.
3. **Read the whole document from the XML body, not just `document.paragraphs`.**
   `doc.paragraphs` indices drift out of alignment with the body when tables are present
   (each `<w:tbl>` occupies a body slot). Iterate `doc.element.body` directly to see the
   true order and to catch section bodies that look "empty" via the paragraphs API.
4. **Locate elements by matching their text, then edit via saved element references.**
   Do all lookups first, before mutating, so later insert/delete operations don't
   invalidate positional indices. lxml element references stay valid across edits elsewhere.
5. **Save to a NEW filename** (e.g. `<name>_NAR.docx`); never overwrite the original.
6. **Validate before declaring done** (see Step 6).

---

## Step 0 — Understand the target format first

If Daniil points to a style guide (a journal page, a template `.docx`, a markdown spec such
as `NAR_author_guidelines.md`), read it fully first and extract: required section list and
order, heading conventions, abstract/word limits, citation/reference style, figure rules
(formats, dpi, colour, **alt text**), table rules, and all mandatory statements (data
availability, author contributions/CRediT, conflict of interest, funding, ethics). This
becomes your rewrite checklist. For a Word template, analyse it with `python-docx`
(page size, margins, `Normal` style size, line spacing, heading styles).

## Step 1 — Extract and map the source document

```python
import docx
from docx.oxml.ns import qn
d = docx.Document(SRC)
body = d.element.body
def text_of(el): return "".join(t.text or "" for t in el.findall(".//"+qn("w:t")))
def style_of(p):
    ppr = p.find(qn("w:pPr")); ps = ppr.find(qn("w:pStyle")) if ppr is not None else None
    return ps.get(qn("w:val")) if ps is not None else ""
```

Walk `body` children (`<w:p>`, `<w:tbl>`, `<w:sectPr>`), printing index, style, text preview,
and whether a paragraph holds an image (`el.findall(".//"+qn("w:drawing"))`). Produce a full
section map. Confirm: which sections exist, which are empty stubs, where the tables and
images are, and what is missing vs the target-format checklist. **Re-verify "empty" sections
against the raw body** (principle 3) before concluding content is absent.

## Step 2 — Plan the transformation

Write down, per section: keep / reformat / delete (tracked) / insert (tracked) / add-note.
Decide the target section order. Identify:
- Planning notes / non-target-language notes / stray URLs to delete.
- Citations to convert (e.g. author-year → sequential numeric) and their numbering.
- Figure captions (keep) and figure images (tracked-delete; Daniil inserts final art).
- Missing mandatory sections to add as new tracked segments.
- Every place needing an EDITOR NOTE.

## Step 3 — Use the track-changes helper library

`from word_rewrite_trackchanges import *` (add its dir to `sys.path`). It provides:

- `ins_paragraph(text, style=None, bold, italic, color)` — a fully tracked-**inserted** paragraph.
- `ins_paragraph_runs(runs, style=None)` — inserted paragraph from custom runs (`make_run(...)`).
- `note_paragraph(text)` — red italic tracked-inserted `[EDITOR NOTE] …` paragraph.
- `heading(text, level)` — inserted `Heading{level}` paragraph.
- `delete_paragraph(p)` — convert an existing paragraph into a tracked **deletion** in place
  (wraps runs in `<w:del>`, converts `<w:t>`→`<w:delText>`, marks the paragraph mark deleted;
  handles runs that contain images).
- `tracked_replace(p, [(old, new), ...])` — rebuild a paragraph applying substring
  replacements as tracked del+ins (`new=""` = pure deletion). Handles text split across
  multiple/nested runs; preserves the first run's `rPr` as base formatting.
- `insert_after(ref, [els])` / `insert_before(ref, [els])`.
- `set_revision_identity(author, date)` — set the revision author/date shown in Word.

**XML rules the helpers enforce (respect them if you hand-write any XML):**
- Deleted text uses `<w:delText>` inside `<w:del>`; inserted/normal text uses `<w:t>`.
- `<w:ins>` and `<w:del>` each need `w:id`, `w:author`, `w:date` (unique ids).
- A fully inserted/deleted paragraph also marks its **paragraph mark** via
  `<w:pPr><w:rPr><w:ins|w:del .../></w:rPr></w:pPr>`.

## Step 4 — Apply edits (typical recipes)

- **Reformat a line** (byline, correspondence): `tracked_replace(p, [("old","new")])`, or
  `delete_paragraph(old)` + `insert_after(old, [ins_paragraph("new")])` for a full rewrite.
- **Delete planning notes / stray URLs / duplicate paragraphs:** `delete_paragraph(p)`.
- **Convert citations:** `tracked_replace(p, [("(Smith et al., 2020)", "(3)"), ...])`,
  numbering by order of appearance in the FINAL section order.
- **Remove figures, keep captions:** for each image paragraph `delete_paragraph(img_p)`;
  leave the caption paragraph untouched.
- **Alt text:** after each figure-caption paragraph, `insert_after(cap, [ins_paragraph_runs(
  [make_run("Alt text: ", bold=True), make_run("<concise description of the figure>")])])`.
- **Condense an abstract:** delete the old paragraphs, insert one merged paragraph within the
  word limit; verify the count in code (`len(text.split())`). Add a note to confirm wording.
- **Add missing sections:** build a segment = `[heading("SECTION", 1), ins_paragraph(template),
  note_paragraph("...MANDATORY... complete X")]`. Add CRediT for Author Contributions, a
  default "None declared" for Conflict of Interest, a funding template ending with the
  open-access-charge line, a proper Data Availability statement, etc.
- **Empty subsections:** `insert_after(heading, [note_paragraph("Section body missing: ...")])`.

## Step 5 — Reorder sections to the target structure

Segment the body at top-level heading boundaries, key each segment, then re-emit in the
target order (keeps tables/images with their segment; keeps `<w:sectPr>` last):

```python
sectPr = body.find(qn("w:sectPr"))
children = [el for el in body if el is not sectPr]
# split into segments starting at each Heading1; assign a key from heading text
# sort segments by TARGET order (stable), detach all children, re-append in new order
for el in children: body.remove(el)
for seg in ordered:
    for el in seg["els"]:
        sectPr.addprevious(el) if sectPr is not None else body.append(el)
```

Insert new-section segments into `body` (before `sectPr`) **before** reordering, so the sort
places them correctly. Optionally add continuous line numbering for review copies:
`<w:lnNumType w:countBy="1" w:restart="continuous"/>` into `sectPr` (before `<w:cols>`).

## Step 6 — Validate (mandatory before reporting done)

Run these checks and only report success if they pass:

1. **Reopens:** `docx.Document(DST)` succeeds; `doc.paragraphs` non-empty.
2. **XML well-formed:** unzip and `xmllint --noout word/document.xml settings.xml styles.xml`.
3. **Revision integrity:** zero `<w:t>` inside any `<w:del>`; zero `<w:delText>` outside a
   `<w:del>`; every `<w:ins>`/`<w:del>` has id+author+date.
4. **Accept-all view** (all `<w:t>` not inside `<w:del>`): confirms deletions gone (planning
   notes, old duplicates), insertions present (new sections, numbered citations), key body
   text preserved, word limits met.
5. **Reject-all view** (exclude `<w:t>` inside `<w:ins>`, include `<w:delText>`): confirms the
   original content is fully restorable — proof the changes are genuinely tracked.
6. **Images:** all removed figures are inside `<w:del>` (not live) yet still present in
   `word/media/` of the archive.

LibreOffice/Word may be unavailable for a visual render — state that caveat and recommend
Daniil open the file in Word to eyeball the revision display before accepting.

## Step 7 — Report

Tell Daniil: the new filename; that Accept All = clean version and Reject All = original;
the structural changes made; and a bullet list of the `[EDITOR NOTE]` items he must complete
manually (missing data, references, accessions, figures, funding, etc.).

---

## Conventions to keep consistent across rewrites

- Revision identity: author `"Claude (<format> reformat)"`, a single fixed ISO date.
- Editor notes: red (`C00000`), italic, bold `[EDITOR NOTE]`/`[NAR EDITOR NOTE]` label.
- Alt text: black text, bold `Alt text:` prefix, placed directly under the figure legend.
- Figures never embedded unless asked — captions + alt text only; final art supplied separately.
- Heading styles reused from the source (`Heading1`/`Heading2`); do not invent new style ids.

## Gotchas

- `doc.paragraphs` index ≠ body-child index when tables exist → always use the XML body.
- Some paragraphs have 0 direct `<w:r>` children (runs nested in hyperlinks/smartTags/proofErr);
  `tracked_replace` handles this by rebuilding from concatenated text.
- Shell rule: never use `rm` in Bash here (globally blocked). Use unique output dirs instead.
- Keep unique `w:id`s across all revisions (the helper's counter does this).
