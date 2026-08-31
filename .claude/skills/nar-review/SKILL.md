---
name: nar-review
description: Act as a journal referee on a .docx manuscript (Nucleic Acids Research or any journal) and write the corrections back as Word tracked changes. Use when asked to review a manuscript as a reviewer, rank drawbacks as minor/major/critical, check adherence to author guidelines, audit the statistics and methodology, audit figures and supplementary files, or apply review edits in tracked-change manner. Ships nar_review_tools.py and replaces word_rewrite_trackchanges.tracked_replace with a citation-safe edit function.
---

# Skill: NAR (journal) manuscript review

## When to invoke

Use this skill whenever Daniil asks you to **act as a journal referee on a `.docx` manuscript**
and, usually in the same breath, to **write the edits back as tracked changes**. Recognisable
triggers:

- "Review my manuscript as a reviewer of *Nucleic Acids Research* / journal X."
- "Find all the drawbacks, errors, typos, incompleteness — rank them minor/major/critical."
- "Check adherence to the author guidelines."
- "Check the adequacy of the statistics and methodology."
- "Review the publication materials (figures, supplementary figures and files) too."
- "Add your edits into the manuscript in tracked-change manner, save as `<name>_<date>.docx`."

**Sibling skills.** `word-rewrite/SKILL.md` covers *reformatting* a manuscript into a journal's
structure (adding sections, reordering, converting citations). This skill covers *reviewing* one
and applying corrective edits. They share `word_rewrite_trackchanges.py`, but this skill
**overrides its `tracked_replace`** — see Step 2.

**Worked precedent.** The 2026-07-27 pass on `FL_harmonization_article_NAR.docx` produced
`figures_for_article/NAR_review_260727.md` (12 critical / 34 major / 61 minor) and
`FL_harmonization_article_NAR_260727.docx` (134 tracked edits, 53 reviewer notes) via
`figures_for_article/apply_nar_review_edits_260727.py`. Read the *Findings archive* at the bottom
before re-reviewing that manuscript — most of the work is already done.

---

## Deliverables

1. `<JOURNAL>_review_<YYMMDD>.md` — the referee report.
2. `<manuscript>_<YYMMDD>.docx` — the manuscript with tracked changes. *Accept All* must give the
   corrected text; *Reject All* must restore the original byte-for-byte.
3. `apply_<journal>_review_edits_<YYMMDD>.py` — the edit script, kept so the pass is repeatable
   after Daniil revises the source.

Never overwrite the original. Never touch references unless explicitly asked (Daniil manages them
in Mendeley).

---

## Core principle: measure, don't read

The expensive failure mode is pulling raw bytes into context — a 25 MB `.docx`, 45 figure files,
a 2,400-row metrics table. **Everything measurable is measured by a script that prints a summary.**
`nar_review_tools.py` implements every measurement below. It lives one level up, in the
`.claude/skills/` root alongside `word_rewrite_trackchanges.py` — deliberately *not* inside this
skill directory, because the 260727/260728 edit scripts import it by that path.

```bash
source ~/venvs/collagen_3_11/bin/activate
S=~/FL_harmonization/.claude/skills/nar_review_tools.py
SP=<your scratchpad dir>
```

| What | How | Cost |
|---|---|---|
| Manuscript body | `python $S extract MS.docx $SP/manuscript.txt`, then Read it **once** in 2–3 chunks | ~23k tokens for a 17k-word paper — unavoidable, you must actually read the prose |
| Citation storage | `python $S fields MS.docx` | <1k |
| Formatting / abstract / variants / placeholders | `python $S docx MS.docx` | ~1k |
| Supplementary data cross-checks | one bespoke pandas heredoc per question (Step 4) | ~1k per batch |
| All 45 figure files | `python $S figures FIGDIR/` | ~2k |
| Which figure holds which label | `python $S figtext FIGDIR/ --grep ...` | <1k |
| Visual figure inspection | `python $S render` then Read **4–6 PNGs only** | ~1.5k per image |
| Tracked-change validation | `python $S validate SRC.docx DST.docx` | <1k |

Budget for a full pass: **~60–80k tokens**. The 260727 pass used ~260k because the tools were
being written from scratch; with them in place it should be a third of that.

Do **not** use `mcp__*ctx_execute*` for the docx edits — those run in a throwaway sandbox and do
not persist file writes. Use Write + `python` via Bash.

---

## Step 0 — Read the target guidelines and inventory the submission

1. Read the guidelines file fully (`figures_for_article/NAR_author_guidelines.md` — a distilled
   NAR reference already exists; use it rather than re-fetching the web pages). Extract the hard
   numbers you will check against: abstract word cap, figure max width/height, dpi minimums,
   colour space, font rules, alt-text rule, supplementary file-count/size caps, mandatory
   back-matter sections, data-deposition rules.
2. `ls` the figures/tables folder. Note the naming scheme and anything that looks off-schema
   (files with no extension, duplicate formats of the same figure, categories the journal does
   not have — e.g. NAR has no "Extended Figure").
3. Confirm what Daniil has excluded from scope. In the 260727 pass: italic placeholder text,
   GitHub URLs, and all citation/reference formatting. **Honour exclusions strictly**, but still
   *report* a scope-excluded item if it is structurally broken (e.g. a stale stub reference list
   sitting above the real bibliography) — flag it without editing.

---

## Step 1 — Extract the manuscript once

```bash
python $S extract MS.docx $SP/manuscript.txt
```

Produces one line per body child with:

- `[N]` the **body-child index** (not the `doc.paragraphs` index — they diverge wherever a table
  exists, because each `<w:tbl>` occupies a body slot),
- `<StyleId>` so you can see the heading hierarchy,
- `{INS}` / `{DEL}` where revisions already exist,
- `{{ … }}` around **italic** runs — this is how Daniil marks unfinished text, so you can skip it
  on sight,
- full table contents inline (tables carry a large share of the reviewable content: method
  registries, metric definitions, strategy tables),
- `<IMAGE>` where a paragraph holds a drawing.

Then Read that file. Keep the body indices in your notes — they are how you refer to locations
while drafting, even though the edit script locates paragraphs by text anchor.

---

## Step 2 — Probe how citations are stored, BEFORE planning any edit

```bash
python $S fields MS.docx
```

**This is the single most important safety check in the skill.**

`word_rewrite_trackchanges.tracked_replace()` rebuilds a paragraph from its *concatenated* text
and re-emits plain runs. That silently destroys any structure inside the paragraph. In
`FL_harmonization_article_NAR.docx` the Mendeley citations are **118 `<w:sdt>` structured-document
tags** (plus one more `sdt` holding the 95-entry bibliography) and there are **zero**
`w:fldChar`/`w:instrText` — so a field-based check finds nothing and you would destroy 35
paragraphs' citations without noticing.

Use **`safe_tracked_replace(p, [(old, new), ...])`** from `nar_review_tools.py` instead. It edits
only runs that are *direct children* of the paragraph, so anything nested in `w:sdt` or
`w:hyperlink` survives byte-for-byte. Rules:

- `old` may span several runs but **must not span a citation**. Pick anchors inside one
  uninterrupted stretch of prose. When in doubt, use a shorter `old`.
- It returns `('ok' | 'not-found' | 'unsafe')` per replacement — never fails silently.
- `unsafe` means an affected run holds something that would be lost by rebuilding
  (`w:br`, `w:tab`, `w:drawing`, footnote ref). `w:lastRenderedPageBreak` is whitelisted because
  Word regenerates it; that alone accounted for 7 of 11 first-pass `unsafe` hits.
- `not-found` usually means the text is split by a superscript run. Example: `R2` is stored as
  `R` + a superscripted `2` in its own run, so `"R2 were below 1%"` does not exist as a string —
  target `"were below 1%"` instead. Superscript/subscript typography is therefore best left to a
  reviewer note rather than edited.

---

## Step 3 — Automated document checks

```bash
python $S docx MS.docx
```

Reports, all against the journal's numbers:

- page size and margins (the 260727 manuscript was **US Letter, not A4** — i.e. not in the
  journal template at all), line numbering, presence of any header/footer part (no footer part
  means **no page numbers**),
- `Normal` style font/size/spacing vs the template's 11 pt / 1.15,
- **abstract word count** after Accept All (was 199/200 — so every edit must be net-neutral or
  net-negative in word count; check this before proposing abstract wording),
- **spelling-variant pairs** with both counts, so you can state the inconsistency numerically
  rather than impressionistically (`neighbor 19 / neighbour 4`, `center 4 / centre 6`,
  `analyze 6 / analyse 3`, `tSNE 53 / t-SNE 3`),
- unresolved placeholders (`(ref)`, `XXXX`, `TBD`, `…`, "check later", "create a repo") and any
  **Cyrillic** paragraphs (planning notes that must not reach the journal),
- **figure/table citation coverage** with gaps — this is what exposed that 10 "Extended Figure"
  files were cited nowhere.

---

## Step 4 — Verify every number against the deposited data

**This is where a real referee report separates itself from a proofread, and it is where the
critical findings came from.** Do not trust a number in the text; recompute it from the
supplementary files. Write one pandas heredoc per batch of questions.

The sweep that paid off on the 260727 pass:

1. **Row and column counts of every supplementary file.** Do they match the sample / approach /
   metric counts asserted in the text? (Supp. File 2 had 7,238 rows against a stated 7,174-sample
   dataset; Supp. File 3 had 2,407 rows against four different totals in the text: 2,234 / 2,407 /
   2,604 / 2,409; Supp. File 4 had 165 metrics against a stated 230.)
2. **Reconstruct the stated filter.** "2,234 of 2,407 had <5% all-NA samples" — try every
   plausible threshold and column. None gave 2,234, so the analysis subset is not recoverable from
   the deposited file. That is a critical reproducibility finding, and it also explains why the
   next item disagrees.
3. **Recompute every quoted correlation, median and MAD.** Reported r = 0.527 recomputed to 0.352;
   reported r = −0.159 to −0.109. Report both numbers and the likely cause.
4. **Check the direction of every metric against the data.** The highest-value single finding of
   the pass: the manuscript defined PCR in the conventional direction, but the deposited values
   ran the opposite way (unharmonized = 0.23, best methods = 1.00), which made a whole Results
   section read as self-contradictory. **Always sanity-check a metric's polarity by looking up the
   value for the no-op / control condition.**
5. **Reconstruct the composite score and the effect sizes.** min-max scale, flip negative-polarity
   metrics, average, then one-way OLS per factor. Compare ordering *and* magnitudes to the text.
   (Ordering reproduced; the strategy R² was 0.174 vs a reported 0.256.)
6. **Check design balance.** `pd.crosstab(df.method, df.strat)` — how many cells are empty? Six of
   33 methods were not run on all strategies; two ranked 1st–2nd on 6 runs each; a method
   recommended in the decision tree had 14 of 84 runs.
7. **Check whether the response variable is comparable across groups.** Count non-NA metrics per
   group. It ranged 66.6–86.8, so a mean-of-87-metrics score was actually a mean over different
   metric subsets — and the bias favoured exactly the strategies the paper recommends.
8. **Look for saturated metrics.** A metric pinned at exactly its theoretical optimum across every
   run of a method (`pcr_RNA_BATCH == 1.0000`) is a red flag that the method destroyed structure,
   not that it succeeded.
9. **Recompute category sums.** Do the group counts add to the stated total? (4,466 + 1,697 + 875
   + 88 + 34 = 7,160, not 7,174 — the missing 14 were plasmablasts, and confirming that against
   Supp. File 1 also confirmed that a *different* table's number was right.)
10. **Confirm claims attributed to a specific item.** The Results blamed a gene-retention failure
    on `21_harmonizr` (which the data confirmed exactly) while the Discussion blamed `25_angel`.

---

## Step 5 — Figure audit

```bash
python $S figures FIGDIR/
python $S figtext FIGDIR/ --grep <every method/label that should appear>
```

`figures` reports per file: size in MB, page count, drawn size in cm, the **scale factor forced by
the journal's max print box**, the **median font size after that scaling**, the **percentage of
text below 5 pt after scaling**, font subtypes and embedded-font count, and colour space. Plus a
raster pass (flags JPG, reports pixel dimensions and aspect ratio so you can catch a stale PNG
whose ratio disagrees with its PDF sibling) and the supplementary file-count/size tally.

What this caught on the 260727 pass — none of it visible by looking at the figures:

- every figure exceeded the max print box, needing scale 0.44–0.67;
- **Figure 3, the paper's central figure, had 100% of its text below 5 pt after scaling**
  (median 4.4 pt); Supp. Fig. 7 had a median of 3.0 pt;
- every PDF used **Type 3 fonts with zero embedded font files** — which is also why text
  extraction was corrupted (`log₂(x+1)` extracts as `log‡(x+1)`) and why screen readers cannot
  read the figures, contradicting the alt-text the manuscript supplies;
- all RGB, no CMYK;
- `Figure 4.png` ratio 1.53 vs `Figure 4.pdf` ratio 0.66 — one of the pair is stale;
- `Supplementary File 4` had no file extension.

`figtext` searches the PDF text layer. Grep it for every method / sample / group name the paper
claims to analyse. **This is how you find things silently dropped from the analysis**: `34_arsyn`
and `38_harman` were listed as implemented in the methods table and contributed 78 rows each to
the metrics file, but appeared in **none** of Figures 3, 6, 7, 8, 9.

---

## Step 6 — Visual inspection, strictly budgeted

```bash
python $S render FIGDIR/ $SP/render --only "Figure 3" "Figure 9" "Graphical Abstract" --dpi 90
```

Read **4–6 images at most** — the central multi-panel figure, the summary figure, the graphical
abstract, and whichever figure the numeric audit made suspicious. Look for what only the eye
catches:

- **panel-letter mismatches between the figure and its legend** (Figure 9's legend had D and E
  swapped relative to the figure; the main text cited them correctly, so the legend was wrong),
- **axes described the wrong way round in the legend** (Figure 3: legend said approaches = columns,
  figure had them as rows),
- **missing legends** (Figure 9C/D radar plots had no colour key at all),
- rotation (Figures 3 and 6 were rotated 90°, so all labels read sideways),
- red–green palettes on colour-carrying data,
- terminology drift between figure legends and the Methods text,
- for a graphical abstract: whether panels are **reused from main figures**, which most journals
  forbid, plus aspect ratio and minimum font size,
- items present in the figure's legend but absent from the corresponding table (Figure 3's legend
  showed a metric group "K" that the metric-definitions table omitted).

---

## Step 7 — Compose the review

Write `<JOURNAL>_review_<YYMMDD>.md` with this structure. It is a referee report, so lead with
judgement, not a list.

1. **Header** — manuscript title, every file reviewed, what was explicitly excluded from scope,
   date, name of the tracked-changes output.
2. **§0 Summary assessment** — open by crediting what is genuinely strong and specific about the
   work (this is not politeness; a referee who cannot name the strengths has not understood the
   paper). Then group your concerns into 2–4 themes in descending seriousness, state the
   recommendation, and give the issue counts.
3. **§1 Critical** — anything that makes a claim unevaluable: inverted definitions, numbers that
   disagree with the deposited data, non-reproducible filters, a response variable that is not
   comparable across groups, an illegible central figure. Use a small table for each numeric
   contradiction: *quantity | as reported | as recomputed | verdict*. Nothing is more persuasive.
4. **§2 Major** — split into "reproducibility" and "internal contradictions / cross-reference
   errors". Number them `M1…Mn` so the tracked-changes notes can refer to them.
5. **§3 Minor** — as tables, one row per issue: `# | location | issue`. Subsections:
   spelling/grammar/typographical; style and register (non-scientific wording); abbreviations;
   language-variant consistency; tool and software naming; miscellaneous.
6. **§4 Statistics and methodology — consolidated verdict** — a standalone section, because this
   is what Daniil asks for explicitly. Open with *what is sound* (name it specifically), then a
   numbered list of what must be fixed, then a paragraph on the paper's central biological claim.
7. **§5 Figures, tables and supplementary material** — a format-compliance table
   (`requirement | status`), the legibility table with measured numbers, figure-specific comments,
   supplementary-material compliance, document formatting vs the template, data availability.
8. **§6 Recommendation** — "Major revision" etc., plus the 3–4 changes that would most alter your
   assessment, ranked.
9. **Appendix — verification method** — how each number was checked. This is what makes the report
   auditable and lets the next pass skip re-derivation.

### Severity rubric

| Tier | Test |
|---|---|
| **Critical** | A stated claim cannot be evaluated or is contradicted by the authors' own data. Inverted definitions; headline counts that disagree; statistics that don't reproduce; a response variable that isn't comparable; the central figure illegible at print size; the Conclusions contradicting the Discussion. |
| **Major** | The work is probably fine but the reader cannot verify or reproduce it, or two parts of the paper disagree on a fact. Missing model specifications; no seeds on stochastic metrics; undocumented "systematic" searches; subjective scores with no stated criteria; wrong cross-references; contradictory definitions of one metric; missing controls; guideline violations that block submission. |
| **Minor** | Typos, grammar, register, abbreviation hygiene, tool naming, number formatting, language-variant mixing. |

### Issue classes to sweep deliberately

Work through these as a checklist; each one found real problems in the 260727 pass.

- **Numeric consistency** — every count that appears more than once (samples, methods, approaches,
  metrics, groups). Grep for each and compare.
- **Internal contradictions** — Abstract vs Results vs Discussion vs Conclusions vs tables vs
  figure legends. Especially: how many methods/items "worked"?
- **Cross-references** — does "Supplementary Figure 6" point at the figure that shows what the
  sentence claims? Do panel letters in the text match the legend *and* the figure?
- **Set-membership errors** — "among the five largest, the fifth and sixth…"; lists of strategies
  that differ between two adjacent paragraphs.
- **Definitions** — is each metric defined once, consistently, and in the direction the data
  actually run? Is one quantity defined two different ways in two places?
- **Statistics** — effect sizes reported alongside p-values? Pseudo-replication (are the N
  observations really independent, or re-analyses of overlapping subsets)? Multiple-comparison
  correction? Confidence intervals? Model specified? Balanced design? Outlier handling before
  normalisation? Arbitrary hyperparameters (k, number of PCs) justified or sensitivity-tested?
  Positive and negative controls (label permutation, held-out prediction)?
- **Over-claiming** — "significantly" used non-statistically; "refutes"; "largest possible";
  unsourced fold-change ratios (three different ones appeared); a quantitative claim in a section
  heading that the section does not test.
- **Register** — "supremacy", "mixed perfectly", "rejected by clustermap", "failed
  spectacularly", "exotic", "brute force", "tricky", and personal material in the
  Acknowledgements.
- **Abbreviations** — defined at first use? Redefined later? Any abbreviation that collides with a
  standard term in the target journal's field (**"PCR" for principal component regression in a
  molecular-biology journal** is a genuine comprehension hazard, not pedantry)? Used in a table
  before being defined in the text?
- **Tool and software naming** — exact package name and capitalisation (`missForest`, `kallisto`,
  `Claude Code`), correct expansion, correct role (Karpenter is a node autoscaler, it does not
  enforce job timeouts), version numbers consistent across sections, versions given for every
  dependency, commit SHA where there is no release.
- **Scientific naming** — "genome reference" for a transcriptome-indexing tool; microarrays called
  "sequencing platforms".
- **Causality** — "batch correction introduced missing values" when the missingness precedes
  correction.
- **Guideline compliance** — run the guidelines' own checklist end to end.

### Leave to the author, don't auto-edit

Global find-and-replace decisions and anything where the correct answer is a judgement only the
author can make: the British/American spelling choice, renaming a pervasive abbreviation, whether
to delete a personal acknowledgement. Flag with numbers, recommend, and say explicitly that you
did not change it.

---

## Step 8 — Apply the tracked changes

Write `apply_<journal>_review_edits_<YYMMDD>.py`. Copy the structure of
`figures_for_article/apply_nar_review_edits_260727.py`; it is the reference implementation.

```python
import sys
sys.path.insert(0, "~/FL_harmonization/.claude/skills")
from word_rewrite_trackchanges import insert_after, note_paragraph, set_revision_identity
from nar_review_tools import safe_tracked_replace          # NOT tracked_replace

set_revision_identity("Claude (NAR referee report 2026-07-27)", "2026-07-27T00:00:00Z")

EDITS = [ (anchor_text, [(old, new), ...]), ... ]   # anchor locates the paragraph
NOTES = [ (top_level_anchor_text, note_text), ... ] # red italic [REVIEWER NOTE] after it
```

Rules that matter:

1. **Short pieces.** Change only the words that change. Two altered words → a two-word `del` plus a
   two-word `ins`; the rest of the sentence stays black. Daniil asked for this explicitly, and it
   is what makes the diff reviewable. Whole-sentence replacement is justified only when the whole
   sentence is wrong (an inverted definition, a garbled clause).
2. **Locate by text anchor, never by index.** Indices shift as soon as you insert a note.
3. **Resolve every anchor to an lxml element reference *before* mutating anything.** After an edit
   the original wording lives in `<w:delText>`, which a `.//w:t` text search no longer sees, so an
   anchor looked up afterwards fails. This was 4 of 11 first-pass failures. Element references stay
   valid across all later edits.
4. **`find_p` must assert exactly one match** and raise otherwise — a silent wrong-paragraph edit
   is worse than a crash.
5. **Insert notes after all text edits**, grouping consecutive notes on the same paragraph with
   `itertools.groupby` so their order is preserved.
6. **Anchor notes to top-level body paragraphs only** — `insert_after` on a paragraph inside a
   table cell puts the note in the cell.
7. **Where the right answer needs data you don't have, insert a note instead of guessing.** Where
   you *can* fix it but the author must confirm, do both: make the edit and add a note saying what
   you assumed. Roughly one note per three edits was the right ratio.
8. **Watch word caps.** If the abstract is at 199/200, every abstract edit must be net-neutral or
   net-negative. Compute it, don't eyeball it.
9. Notes are red italic and labelled `[REVIEWER NOTE]` (the `word_rewrite` skill uses
   `[EDITOR NOTE]` for its own reformatting pass; keeping the labels distinct lets Daniil tell the
   two passes apart in one document).
10. **Table cells are editable** — they are ordinary `<w:p>` inside `<w:tc>`, so
    `safe_tracked_replace` works on them. Use a body-level anchor for any related note.
11. Print a per-replacement report and **iterate until zero `not-found` / `unsafe`**. Do not ship a
    partially applied edit list.

### Step 8b — Second pass on a document that already carries revisions

`apply_nar_abbrev_edits_260728.py` is the reference implementation for this case (input
`..._260727_partially_edited.docx`, output `..._260728.docx`). Four extra rules:

12. **Text inside an unaccepted `<w:ins>` is invisible to `safe_tracked_replace`** — those runs are
    children of the `w:ins`, not of the paragraph, so it returns `not-found`. Keep a separate
    `IN_PLACE_EDITS` list and retype the `w:t` directly, but **only after checking
    `ins.get(qn('w:author'))` is your own earlier pass**. That mirrors what Word does when you edit
    your own not-yet-accepted insertion, and reject-all still restores the original because the
    entire insertion is dropped. Never retype inside another author's revision — report it.
13. **Skip `[REVIEWER NOTE]` / `[NAR EDITOR NOTE]` paragraphs in every sweep.** They quote the old
    wording on purpose. They also poison "first occurrence" scans: a note *about* an undefined
    abbreviation contains that abbreviation thousands of characters before its real first use — scan
    with the notes filtered out or every answer is wrong.
14. **Repeated rename:** call `safe_tracked_replace(p, [(old, new)])` once per occurrence counted in
    the direct-child text. Each call moves the replaced text into `w:del`/`w:ins`, so the next call
    lands on the following occurrence — no offset bookkeeping needed.
15. **Anchors must match *visible* text** (original + insertions, deletions excluded), i.e. what
    `"".join(t.text for t in p.findall(".//w:t"))` returns. Anchoring on wording the previous pass
    deleted will never match.

### Renaming an abbreviation across a manuscript

Checklist, in order — from the PCR → PCReg rename:

- Count the true occurrences first, splitting plain / `w:ins` / `w:del` / notes; the totals must
  reconcile at the end (22 real = 19 tracked + 2 retyped + 1 folded into a larger rewording).
- Use a word-boundary regex, `(?<![A-Za-z0-9])PCR(?![A-Za-z0-9])`, or you will hit `PCReg` on a
  re-run and mangle plurals.
- **Check the figures and the deposited tables too** — `figtext FIGDIR/ --grep PCR` found the old
  name in 5 PDFs, and `head -1` on the metrics CSV found `pcr_*` column names. Neither is fixable
  from the `.docx`; say so in a note so the author regenerates them.
- Verify after accept-all that the old token count is **0** outside notes and the new count equals
  the expected total.

### Defining abbreviations at first use

- "First use" means first occurrence **in document order including table cells**, so build the scan
  over `body` children with `w:tbl` paragraphs inlined at their true position.
- When the first occurrence is a table cell and the acronym is never reused inside that table,
  spell the term out **without** the parenthetical acronym in the cell and let the first prose use
  carry the definition. That avoids defining the same abbreviation twice a few paragraphs apart.
- Avoid pulling superscript runs into a replacement: for `log2(TPM)` target `"(TPM)"`, never
  `"log2(TPM)"` — the `2` is its own run and rebuilding it loses the superscript.
- A case-sensitive definition check will report false failures where a table row already spells the
  term with a leading capital (`Dispersion separability criterion (DSC)`); compare case-insensitively
  before believing the report.

---

## Step 9 — Validate (mandatory)

```bash
python $S validate MS.docx MS_260727.docx --absent "typo1" "old phrasing" ...
```

Must all pass:

1. `document.xml` / `styles.xml` / `settings.xml` parse.
2. Zero `<w:t>` inside a `<w:del>`; zero `<w:delText>` outside one; every revision has
   `w:id` + `w:author` + `w:date`; no duplicate ids.
3. **Reject-all text equals the original exactly** — the proof that the changes are genuinely
   tracked. If it diverges, the tool prints the first differing characters.
4. **`w:sdt` count and contents unchanged, hyperlink count unchanged** — the proof that the
   citations survived.
5. Abstract still within the word cap after Accept All.
6. `--absent` strings gone. Note the false positive: a string will still be found if your own
   reviewer note *quotes* it. Check which paragraph it is in before believing the failure.

LibreOffice/Word are not available here, so state the caveat: recommend Daniil open the file in
Word to eyeball the revision display before accepting anything.

---

## Step 10 — Report and accumulate

Report to Daniil: the three filenames; that Accept All = corrected and Reject All = original; the
2–4 headline findings with their numbers; what you deliberately left for him to decide; and
confirmation that the citations are intact.

Per the repository protocol, write anything non-obvious and durable into the relevant
sub-directory `CLAUDE.md` and, if it will matter across sessions, into the auto-memory directory.
The 260727 pass added a "Manuscript review and tracked-change edits" section to
`figures_for_article/CLAUDE.md` and the memory file `project_docx_mendeley_sdt.md`.

---

## Gotchas

- `doc.paragraphs` index ≠ body-child index whenever tables exist. Always iterate
  `doc.element.body`.
- A "systematic" claim (literature search, screening funnel) needs a documented protocol or it is
  a major issue, however good the underlying work.
- Superscripts and subscripts sit in their own runs, so strings like `R2`, `η2`, `10-14` do not
  exist as contiguous text. Target the surrounding words; leave the typography to a note.
- `pdfinfo` / `pdffonts` / `pdftoppm` / ImageMagick / Ghostscript are **not installed**. Use
  PyMuPDF (`pip install pymupdf` — it installs cleanly into `~/venvs/collagen_3_11`). A raw
  regex scan of PDF bytes miscounts pages and MediaBoxes; use PyMuPDF for geometry.
- Never use `rm` in Bash here (globally blocked). Write to unique paths in the scratchpad.
- A figure's PDF and PNG siblings can disagree in aspect ratio. Check, and say which is canonical.
- Do not assume a supplementary file is empty because a size print rounds to 0.00 MB — `ls -la` it.

---

## Findings archive — `FL_harmonization_article_NAR.docx`, 2026-07-27

Read `figures_for_article/NAR_review_260727.md` for the full report. Headlines, so a later pass can
check whether they were addressed rather than rediscovering them:

**Critical.** PCR defined in the inverted direction, making the metrics Results section
self-contradictory · method count 31 (text) vs 33 (table and data), with `34_arsyn` and
`38_harman` implemented but absent from every figure · approach count 2,234 / 2,407 / 2,604 /
2,409 · metric count 230 (text) vs 165 (Supp. File 4) · the 2,234 filter and two Spearman
coefficients not reproducible from Supp. File 3 · composite score averages different metric
subsets per strategy (66.6–86.8 defined metrics; only 1,354 of 2,407 complete) · rankings driven
by methods with 6–34 of 84 runs · Figure 9B is four marginal η², not a variance decomposition ·
Figure 3 illegible at print size, rotated 90°, red–green palette, axes reversed in its legend ·
Conclusions/Discussion/Table 5 disagree on 2 vs 3 vs 5 successful methods · Supp. File 2 has
7,238 rows against a 7,174-sample dataset.

**Recurring major themes.** Model/design matrices for SVA, limma, ComBat, RUV never stated · no
seeds or replication for 14 embedding-space metrics · KS metric defined two ways, gene sampling
undocumented · harshness score subjective and unattributed · post-removal scoped to cohorts in
Methods but batches in Results, with no stated threshold · Table 4 missing metric group K and its
Source column · kBET median 0.000 yet used as a decision axis · min-max scaling with 5.08 × 10⁸
outliers unhandled · no permutation or predictive control · p-values to 10⁻²⁰⁰ on pseudo-replicated
units, no effect sizes.

**Guideline compliance.** US Letter not A4, not in the template, no page or line numbers · all 37
figures over the print box · Type 3 fonts, none embedded · RGB not CMYK · JPG supplied for
Figure 3 · alt text missing for the graphical abstract and all 17 supplementary figures · 32
supplementary files against a cap of 10 × 2 MB · 10 uncited "Extended Figures", a category NAR
does not have · graphical abstract reuses main-figure panels · GitHub cited as the primary archive
with no Zenodo DOI · MIAME/MINSEQE not stated · byline lists nine names (one of them a database)
against seven in the CRediT statement.

**Left to the author by design.** British/American spelling choice · renaming "PCR" · whether to
delete the personal acknowledgement · all reference and bibliography formatting.

**Resolved 2026-07-28** (`apply_nar_abbrev_edits_260728.py`, second pass on Daniil's partly-revised
copy). He chose PCReg: 22 occurrences renamed, and AUC, tSNE, UMAP, PC, PCA, GEO, PBMCs, AWS, cLISI,
iLISI, TPM, DSC, FSQN and QN are now defined at first use. KNN was already defined and needed no
change. Still open for him: Figure 6 and Extended Figures 2, 3, 6 and 8 print "PCR"/"pcr" in axis
labels, and every principal-component-regression column of Supplementary File 3 is named `pcr_*`.
