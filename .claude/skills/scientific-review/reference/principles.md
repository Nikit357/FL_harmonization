# The ten principles, in full

Distilled from Daniil's manual review of Claude's G3-2026-406828 revision output, 2026-08-09.
Every example below is a real edit. The full catalogue with all 134 edit sites is
`Retroelements/T2T_genes_article/T2T_transposons_genes/revision_G3/Daniil_review_of_Claude_examples_principles_260809.md`.

Read this once before a first pass on a new manuscript. Consult a specific principle when a
judgement call is unclear.

---

## P1 — No proofless, vague, or self-promoting statements

**Statement.** Every sentence must assert something about the data, the method, or the literature
that a reader can check. Sentences that assert something about the *quality of the work* — its
rigour, robustness, sufficiency, its having been verified — are deleted or replaced by the
measurement that would justify them.

**Why.** A reader cannot falsify "this was verified rather than assumed". They can falsify "the
running mean differs from the N = 500 value by less than 1 % by N = 140". The second carries all the
persuasive force of the first *and* is checkable. The first adds nothing except a target for a
referee.

### P1a — Banned constructions

| Construction | Real example | Replacement |
|---|---|---|
| "X rather than assumed / guessed" | "Five hundred permutations are sufficient for that purpose, and this was verified rather than assumed." | the verification number |
| "X rather than a visual statement" | "so that 'concordant' is a measured rather than a visual statement" | delete — the cited tests already say it |
| "X is what makes Y interpretable" | "The permutation background is what makes these enrichment values interpretable" | state the bias it removes, once |
| "high/strong robustness", "reliable baseline", "solid evidence" | — | the robustness statistic |
| "notably", "strikingly", "remarkably", "importantly", "interestingly" | — | delete |
| "clearly shows", "demonstrates convincingly" | — | "shows" |
| Editorial verdict about the paper | "The metal claim is now zinc-only" | the count and the terms |
| Diligence claim | "so that a silent skip is impossible" | delete from the manuscript; it belongs in code docs |
| Property the artwork does not have | "p-values that are raw are labelled as such in the figures, tables and captions" (the panels carry no such label) | narrow to what is true: "in the figure captions and tables" |

### P1b — Unsupported claims about the literature are also proofless

> "whether these elements affect innate immune gene regulation **remains untested**"

asserts a negative about an entire field. Unless a systematic search was performed and can be cited,
delete it.

The mirror image is the same defect. Five prior studies described in prose with **zero** citations:

> "A study of interferon-inducible enhancers spread by LTR elements used a 10 kb window; an analysis
> of TE content around duplicated and singleton genes used 4 kb and 20 kb windows; …"

Each clause got a citation. So did all five statistical methods in a sentence that had none
(Spearman, Pearson, Bland-Altman, overlap coefficient + hypergeometric, Kendall tau,
label-shuffling permutation).

### P1c — What is *not* banned: labelled hypotheses

This survived, and understanding why is the whole of the principle:

> "This is consistent with recent L1 activity and **could indicate** a recent evolutionary arms-race
> affecting innate immune gene regulation."

| Banned | Allowed |
|---|---|
| Unfalsifiable self-assessment of the work | Explicitly modal claim about the biology |
| "high robustness", "reliable" | "could indicate", "is consistent with", "we hypothesise" |
| Asserted with no stated limitation | Paired with an explicit statement of what the design cannot show |

**The test: would a referee know what evidence would refute it?** "could indicate an arms race,
though the design is correlative and cannot detect one" is refutable in principle and honest about
its status. "high robustness" is not.

### P1d — Detection

```bash
grep -n -i -E "rather than (assumed|guessed|a visual)|is what (makes|justifies)|robustness|reliab|\
notably|strikingly|remarkably|importantly|clearly (shows|demonstrates)|convincing|it is worth noting|\
we emphasi[sz]e|it should be noted|serves as a (solid|strong|reliable)" ms.txt
```

**Rewrite recipe.** For each hit ask: *what number would make this sentence unnecessary?* If the
number exists, put it in and delete the sentence. If it does not exist, delete the sentence.

---

## P2 — Every number, GO term and named result is traceable to a specific source object

**Statement.** Every quantitative claim carries a pointer to exactly one object that contains it: a
named supplementary file **and sheet**, a specific figure **panel**, or a numbered table. The pointer
must be to the object that *actually holds* the number.

**Why.** It is what makes a paper auditable, and empirically it is how errors surface — the wrong
pointer below was only visible because the right one was demanded.

### P2a — Granularity

| Too coarse | Correct |
|---|---|
| "(File S3)" for a specific term | "(File S3, sheet GO_by_family)" |
| "(Figure S13B-D)" for three claims | "(Figure S1A)", "(Figure S1B)", "(Figure S1C)" — one per claim |
| "in the supplementary tables" | the filename, plus where it lives if it is not in the workbooks |
| "the checkpoint values are in the repository" | acceptable only for material supporting no numbered claim |

### P2b — The pointer must match the object type

A **figure** supports a distribution, a trend, a visible difference, a network topology.
A **table or workbook sheet** supports an exact count, an exact p-value, a set membership.

> **Wrong:** "LTR families demonstrated 33 unique GO terms compared to 22 in LTRs as a class
> **(Figure 5A)**."
> **Right:** "… **(File S3)**."

Figure 5A is the *class-level, divergence-stratified* connection map. It cannot show a family-level
term count. Verified in the source: 33 and 22 both reproduce from the GO tables.

A second instance in the same pass: "the MHC association rests on one term rather than three
**(Figure 6A)**" — Figure 6A shows up to five terms per family; "one rather than three" is a
statement about the GO table.

**Rule: if the claim contains an integer or a p-value, the pointer goes to a table.**

### P2c — Load-bearing numbers stay in the main text

Claude moved the unadjusted Fisher p-values out of the printed Table 2 into a supplementary
workbook. Daniil put them back and split `mean ± SD` into two columns.

> A supplementary file adds detail; it never becomes the only home of a number the main text argues
> from. If the text says a class is enriched, the printed table shows both the raw and the adjusted
> p. A cell reading "2.43 ± 0.009" cannot be sorted, copied or recomputed.

### P2d — Methods must cite their methods

Every statistical procedure, every software package with its version, and every AI tool with its
version. The AI-usage paragraph was expanded to name the model versions, state the human-in-the-loop
protocol with a number ("two to five review cycles"), and point at the public repository where the
prompt artefacts live. The same traceability standard applies to the AI method as to a statistical
method.

### P2e — Detection

```bash
$V $T numbers ms.txt     # section-aware: Results/Discussion hits are failures
```

Then, for every pointer that *does* exist, open the object and confirm the number is in it. Not
automatable; this is where wrong pointers are found.

---

## P3 — Sequential numbering by order of first citation

**Statement.** Figures, supplementary figures, tables, supplementary files, panels within a figure,
and references are numbered in the order the text first cites them. The rule applies recursively to
panel letters.

**Why.** A reader following the text never jumps backwards. It is also the house rule of essentially
every journal, so violations come back from the production editor.

**Evidence.** 22 citation-renumbering edits in one pass. After Materials and methods moved ahead of
Results, 24 method citations moved to the front of the paper and the whole reference list was
renumbered (Methods citations 98–123 → 12–41; Discussion 20–31 → 49–60). The convergence figure moved
S13 → S1 because it became the first supplementary figure cited; the length-distribution panels that
were S1A/S1B became S1D/S1E.

### P3a — A structural move triggers a full renumbering pass

Moving one section is a one-line decision that invalidates the numbering of the entire reference list
and usually at least one supplementary figure. Re-run the numbering audit and report the new order in
the same pass; it is not a follow-up task.

### P3b — A partial renumbering is worse than none

The G3 body was renumbered S13 → S1 and the legends were not. The Methods then cited `Figure S1A/B/C`
for convergence curves whose legend described ridge plots. **When you change a number, change it in
the body, the legend, every panel letter, and the placement notes — or change none of them.**

### P3c — Detection

```bash
$V $T numbering ms.txt
```

Legends are excluded by default, because they sit at the end and would mask the violation. Two
categories the tool distinguishes:

- **cited only from another object's legend** — not automatically a violation; its position is that of
  the object whose legend cites it. Confirm by hand.
- **legend exists, cited nowhere** — a violation. Supplementary Figure S11 in the G3 manuscript.

### P3d — You do not renumber the references yourself

Citations are Mendeley content controls. Report that the numbering is stale and tell Daniil to
refresh Mendeley. Editing reference numbers by hand breaks the field.

---

## P4 — Scientific language: precise, plain, one subtheme per passage

### P4a — Register

| Casual / imprecise | Corrected |
|---|---|
| "makes it possible to measure where TEs **sit** relative to…" | "enables comprehensive investigation of TE contributions to…" |
| "how close each TE group **sits** to…" | "how close each TE group **locates** to…" |
| "falling **just** outside the 0.05 threshold" | "falling outside the 0.05 threshold" |
| "**again** reflecting the likely random nature" | "reflecting the likely random nature" |
| "cell adhesion **is no longer represented at all**" | "cell adhesion **was not represented**" |

### P4b — Structure, not decoration

The model rewrite, six sentences to one:

> **Before:** "The permutation background is what makes these enrichment values interpretable, because
> it removes a length bias that the Fisher exact test cannot. The probability that an element
> intersects a fixed window grows with the length of the element, so the random odds ratio scales
> almost linearly with mean element length across the 44 families (Pearson R = 0.985, …): Alu average
> 316 bp and a random OR of 1.54, whereas L1 average 6,357 bp and a random OR of 2.66. Reporting the
> observed odds ratio alone would **therefore** systematically under-call short elements and over-call
> long ones, **and** every enrichment statement in this work is consequently made on the ratio of the
> observed to the random odds ratio rather than on the observed odds ratio itself."
>
> **After:** "**Since** reporting the observed odds ratio alone would systematically under-call short
> elements and over-call long ones, every enrichment statement in this work is consequently made on
> **this enrichment score**."

What was cut and why:

* the self-assessment ("is what makes … interpretable") — **P1**;
* the R = 0.985 correlation — a real measured result, but a *result*, and Methods is not where results
  are reported; it has no figure or table, so under **P2** it cannot stand in the text;
* the restatement of a definition given three sentences earlier, in a second vocabulary — saying it
  twice invites the reader to wonder whether they are two things;
* `Reporting X would therefore …, and Y` → `Since reporting X would …, Y` — reason before consequence,
  both connectives gone.

### P4c — Terminology is single-valued

"class of gene" → "functional gene group", because "class" is reserved for TE classes. "The latter
term" → the term's name. "the choice" → "the 10kb window choice".

**Rule: a noun phrase with a technical meaning elsewhere in the paper may not be reused with a
general meaning, and a demonstrative may not reach back more than one clause.**

### P4d — One subtheme per passage

Three structural moves in one pass:

1. "Statistical tests" moved from between the permutation background and the interferon-alpha test to
   after both, so the two permutation-based methods are adjacent and generic statistics follow.
2. A concordance-methods sentence moved out of the sensitivity subsection into "Statistical tests",
   where the other test descriptions live.
3. A pseudo-heading ("Sensitivity to the window and to the gene-set cut-off") deleted and its content
   folded into the paragraph that introduces the window, removing a forward reference ("below").

**Test for a subsection: can you state, in one clause, what block of results it contains, with no "and
also"?** If not, split it or move the outlier.

### P4e — Tense and agreement

Results in past tense. "respectively" on paired lists. A bare integer in parentheses gets its unit —
`(16 terms)`, not `(16)`, which reads as a citation. `Mann-Whitney U raw p = …` with no comma, so "U"
is not read as a variable. Delete "the FDR-adjusted Fisher exact test" when the quoted value is already
an FDR and the adjustment is stated globally in Methods.

---

## P5 — Every number is recalculated from the source; no rounded ranges

**Statement.** Before a number enters the manuscript it is recomputed from the supplementary table or
the repository code that produced it. Approximations, ranges and "roughly N" are not acceptable in a
final version.

### P5a — Quote the crossing point, not the nearest grid row

The convergence checkpoint file had rows at N = 50/100/200/250/300/400. Claude quoted N = 250 and
N = 100 because those rows exist. Daniil quoted N = 140, 250 and 315 — where the curves actually cross
1 %, 6 % and 10 %. **A checkpoint table is a summary of a curve; quote the curve.**

### P5b — Quote in the unit the reader can verify

The same edit converted "0.06 standard deviations of drift" into "less than 1 % of the N = 500 value",
because the panel's y-axis is a fraction of the N = 500 value with a ±1 % band. **The unit in the text
must be the unit on the axis of the figure it cites.**

### P5c — A cut-off is not a count

"(2,872 genes)" → "(2,872 genes **at maximum**)". The top-10 % cut is a ceiling; ties at the boundary
make the realised set smaller for some groups.

### P5d — Counts are stated, and therefore checkable

"The metal claim is now zinc-only" → "6 GO terms with FDR between 0.05 and 0.1 were rejected". This is
the principle working: stating the count made it auditable, and the audit showed the true count is 10.
A vague sentence would have hidden the error indefinitely.

The two errors this check found in the G3 pass, both surviving a human edit:

| Claim | As written | As recomputed | Source |
|---|---|---|---|
| MIR GO terms with 0.05 < FDR ≤ 0.1 | 6 | **10** | `output/GO_families_fdr01_reference.csv` |
| LTR class GO terms in the same band | 2 | **3** (`nucleotide binding`, FDR = 0.076) | `output/GO_classes_count_fdr01_reference.csv` |

### P5e — The recalculation protocol

1. Identify the file that produced the number.
2. Recompute it in a fresh interpreter. **Do not trust a previously printed value, a `results.md`, or a
   `CLAUDE.md` "numbers worth not re-deriving" table.** The Retroelements `CLAUDE.md` recorded a
   correlation as R = 0.661 for months when the measured value was R = 0.985.
3. Reconstruct enumerated sets **by query**, never by counting the items written in the sentence.
4. Confirm the rounding matches the manuscript's convention.
5. Confirm the same number in every other place it appears — abstract, results, caption, table,
   supplementary sheet.
6. Check polarity: look up the value for the no-op or control condition and confirm the metric runs the
   direction the text claims.

---

## P6 — The manuscript reports the current state of the analysis, not its history

**Statement.** The published paper describes one analysis with one set of thresholds. It never refers
to a previous draft, a previous threshold, a term that "no longer" qualifies, or a claim that is "no
longer made".

**Why.** A reader of the published version has never seen the previous threshold. "Dong-R4 no longer
reaches significance" is meaningless to them and reads, to a referee, as an admission that results were
unstable across drafts. The revision history belongs in the response-to-reviewers letter.

**Evidence.** The largest single class of edit in the pass:

| Phrase | Before | After |
|---|---|---|
| "no longer" | 6 | 0 |
| "not retained" | 2 | 0 |
| "previous threshold" | 3 | 0 |
| "at the tightened threshold" | 3 | 1 |

Deleted outright:

> "Two associations that were significant at the previous threshold do not survive at 0.05 and are no
> longer claimed: …"
> "Dong-R4, whose single term the previous threshold retained, no longer reaches significance …"
> "the metals metabolism association of MIR elements, significant at the previous threshold
> (FDR = 0.045), is not retained at 0.05."

**The one legitimate use** — a comparison to an alternative threshold, stated as a property of the data
rather than of the draft:

> "…(both FDR = 0.086), which would be significant under a more relaxed FDR threshold of 0.1 but are
> rejected here."

Information content is *higher* than the version it replaced: the reader learns what a different
analytical choice would have produced, without being told a story about a draft they never saw.

**Rewrite recipe.** *Would this sentence make sense to a reader who has never seen another version of
this paper?* If no — delete it, or restate it as a property of the data under a named alternative
threshold.

---

## P7 — No process scaffolding survives into the manuscript

**Statement.** Editor notes, TODOs, placeholders, instructions to the typesetter, and explanations of
how a script performed an edit do not belong in a document that will be submitted.

**Evidence.** Nine `[EDITOR NOTE]` blocks were left in the G3 revision. Daniil consumed two by
**replacing them with the content they described** — a note saying "Tables 1 and 2 replace the original
Table 1" became the two actual tables; a note about a section move became the scope sentence the
Introduction needed. Seven remained.

**The correct resolution of an editor note is almost always *do the thing*, not *leave a note about the
thing*.**

**Two further artefacts in this class:**

- **Orphan citation-only paragraphs.** 28 paragraphs consisting of nothing but citation markers —
  `(9)(10)(11)(8)(5,6,18,42,45,46)` — left where moved passages were deleted. The Mendeley content
  controls were not inside the tracked deletions, so accepting the deletions left them behind. Count
  them, report them, tell Daniil to delete them in Word and refresh Mendeley.
- **Truncated insertions.** "Claude Code Opus 5.0 (ref)" and an Ethical statement ending mid-clause.

**Corollary for agents.** If you must leave an instruction, put it in the run report, the
implementation plan or a separate markdown file — never in the `.docx`. If a note must temporarily live
in the document, make it findable by one unambiguous string and report the count at the end of the run.

Expected count at submission: **0**.

---

## P8 — Caveats are stated once, in the place the reader expects, and scoped forward

**Statement.** A limitation is stated in Limitations. A statement of scope goes at the end of the
Introduction. Neither is repeated defensively in the middle of a paragraph doing other work.

**Evidence.** Claude wrote the arms-race caveat twice — once mid-paragraph in the Introduction's
*opening*, between the definition and the mechanism sentence, and once in Limitations. Daniil deleted
the mid-paragraph one, left Limitations untouched, and added a scope sentence at the *end* of the
Introduction:

> "Albeit the current analysis is purely correlative and cannot detect the ongoing evolutionary arms
> race, it points at genome loci and molecular processes that could be impacted by it for future
> investigation."

**The caveat was not weakened — it was de-duplicated and moved to the section that exists for caveats.**

The grammar carries the distinction: **the limitation is in the subordinate clause, the contribution in
the main clause.** A defensive disclaimer inverts that and reads as an apology.

**Recipe.** `Although [what the design cannot do], [what it does do and what that enables].` Never the
reverse, never twice, never mid-paragraph.

---

## P9 — House style is enforced mechanically

| Item | Convention |
|---|---|
| Spelling | US English (`neighborhood`, `characterized`, `signaling`, `randomized`, `co-localized`, `visualization`) |
| Exponents | plain text, `2.3 × 10-91` — **never** Unicode superscript |
| p-value | lower-case `p` everywhere, including `p-value`, `raw p` |
| Bare integers in parentheses | give the unit: `(16 terms)`, never `(16)` |
| Test names | `Mann-Whitney U raw p = …`, no comma between test and `raw p` |
| Paired lists | close with `respectively` |
| Tables | placed at first citation, carrying both raw and adjusted p |

**Unicode superscripts are the most damaging of these**: they do not survive typesetting reliably and
they make the number unfindable by a plain-text search for `10-91`, which defeats P5's verification
protocol.

---

## P10 — Priority order when principles conflict

1. **Correctness** (P5) — a wrong number outranks everything.
2. **Traceability** (P2) — a right number with no source is not usable.
3. **Numbering** (P3) — a right, sourced number the reader cannot navigate to is not usable either.
4. **No proofless statements** (P1) and **no history** (P6) — deletions, always safe to apply.
5. **Language** (P4) and **house style** (P9) — last: most text touched, least risk reduced.

An agent short of time does 1–4 completely and 5 partially, never the reverse.

---

## The one-paragraph version

Write only what a reader can check. Every number points at the table or panel that holds it, and was
recomputed from that source before it was typed. Everything is numbered in the order the text first
mentions it. Say it once, plainly, in the section where it belongs. Never tell the reader what the
paper used to say, and never tell them how careful you were — show them the number that makes the
question moot.
