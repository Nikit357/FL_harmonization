# NAR review — second iteration

**Manuscript in:** `FL_harmonization_article_NAR_260802.docx`  
**Manuscript out:** `FL_harmonization_article_NAR_260802_2nd_iteration.docx` (776 revisions)  
**Supplementary out:** `supplementary_260802/Supplementary File 2.xlsx` (four sheets)  
**Scripts:** `build_supp_file2_260802.py`, `apply_nar_table_move_edits_260802.py`  
**Date:** 2026-08-02

Scope of this pass, as requested: move Tables 3 and 4 into Supplementary File 2 with full
bibliographic references, restore correct table numbering in the article, and make a final
language check. Author byline, affiliations, ORCIDs, Zenodo DOIs, the stub reference list,
the Cyrillic planning notes and the italic `{{…}}` placeholders remain outside scope and
untouched.

---

## 1. Tables moved

| Was | Now | Rows × columns |
|---|---|---|
| Main Table 3 — harmonization methods | Supplementary File 2, sheet `Table_S1_methods` | 39 × 9 |
| Main Table 4 — metric groups | Supplementary File 2, sheet `Table_S2_metrics` | 19 × 5 |

**Numeric citations replaced by full references.** Every `(20)`, `(21)` … in the methods
table now carries the complete bibliographic entry, read out of the manuscript's own
reference list: 38 of the 39 methods have one (`01_raw` is "no harmonization" and has none by
design). The metric table's `Source` column was already written out for 18 of 19 rows; the
remaining abbreviations and every `[reference list entry N]` marker were expanded against the
same list, so both sheets stand on their own.

Two structural details had to be handled. Both tables carry horizontally merged cells, so
their rows have different cell counts — 37 of 39 method rows have 9 cells against the
header's 10, because the Version cell spans the old Reference column, and 18 of 19 metric
rows have 5 against 6. `python-docx`'s `row.cells` hides this by repeating merged content, so
the extraction reads raw `w:tc` and normalises per row. The old, largely empty `Reference`
column of the methods table was dropped in favour of the filled one. Cell text was read at
accept-all, so the sheets carry the corrected wording from the tracked-change passes.

## 2. Table numbering restored

The article now runs **Table 1, Table 2, Table 3** in order of first citation:

| Table | Content | Change |
|---|---|---|
| 1 | Prior batch removal strategies | unchanged |
| 2 | Rejection reasons for harmonization methods | unchanged |
| 3 | The 15 best harmonization approaches | **was Table 5** |

Eleven in-text references were repointed — seven to Supplementary Table S1, four to
Supplementary Table S2 — with the full pointer ("Supplementary Table S1 in Supplementary
File 2") at first use in each case. Both table captions and both table bodies are marked as
tracked deletions, so *Reject All* still restores them.

The description of Supplementary File 2 in the back matter now lists four sheets instead of
two.

## 3. A defect from the previous pass, corrected

**The 2026-08-02 figure renumbering corrupted three references to Supplementary Figure 9.**
That pass renumbered the main article's Figure 9 to Figure 6 by searching for the bare string
`"Figure 9"`, which also matches inside `"Supplementary Figure 9"`. Three references were
rewritten to a figure that shows something else entirely:

| Location | Was | Became | Now |
|---|---|---|---|
| Results, approach cross-correlation clustermap | Supplementary Figure 9 | Supplementary Figure 6 | **Supplementary Figure 9** |
| Discussion, cluster reproducibility | Supplementary Figure 9 | Supplementary Figure 6 | **Supplementary Figure 9** |
| Supplementary Figure 9 legend | Supplementary Figure 9 | Supplementary Figure 6 | **Supplementary Figure 9** |

All three are restored. The genuine main-article rewrites in the same paragraphs — including
"unlike the R² analysis in Figure 6B" — are untouched: the revert only fires where the
preceding text ends in "Supplementary ". Supplementary Figures 1–17 and main Figures 1–6 are
now each cited exactly once in a complete sequence, with no gaps and no duplicates.

The same class of bug was found and fixed in the Extended Metrics document earlier today; the
guard is now written up in `CLAUDE.md`.

## 4. Language, grammar and meaning

Twenty-two further edits. The ones that change meaning rather than style:

| Location | Issue | Fix |
|---|---|---|
| Discussion, comparison with other approaches | "failed to preserve local biology structure **and locally separate batches**" states the opposite of the finding — these methods failed to *mix* batches locally | "failed both to preserve local biology structure and to mix batches locally" |
| Results, composite score | "33_amdbnorm, run only for 14 of 84 runs, which also impacted its **compatibility**" | "completed only 14 of its 84 possible runs, again limiting its **comparability**" |
| Results, composite score | "accompanied **with** the decrease of global and distributional performance" | "accompanied **by** a decrease in global and distributional performance" |
| Discussion, AI-assisted evaluation | "the best ones MNN and SVA were identified" — reads as three methods then names two | "the two best — MNN and SVA — were identified" |

The rest: `homogenous` → `homogeneous`; `neighbour` → `neighbor` (the document is otherwise
consistently US); `t-SNE` → `tSNE` in the seeds paragraph (41 `tSNE` against 3 `t-SNE`, all
three remaining inside reviewer notes); `albeit` → `although`; sentence-initial `But` →
`However`; `(Figures 4, 5)` → `(Figures 4 and 5)`; `etc)` → a written-out example pair;
"rapidly expanding including the recent diffusion model-based ones" → "expanding rapidly,
including recent diffusion-model-based methods"; "more limited application scale" → "a
narrower scope of application"; a stray double space; and `2234` → `2,234` and `7174` →
`7,174` in five places, matching the thousands separator used everywhere else.

After these edits the automated variant check is clean on live text: `neighbor` 21/0,
`analyse` 0, `tumor` 8, `center` 8 — and the abstract is still 198 words.

## 5. Four spent reviewer notes removed

Two of your inline notes asked for work that is now complete, and the two RESOLVED notes I
added in reply say on their face that they can be deleted. All four are removed as tracked
deletions, so rejecting those four changes brings them back:

- the model-specification note (the `Parameters used` column now exists);
- its RESOLVED reply;
- the harshness-auditability note (the criteria are in Methods and the
  `Harshness justification` column exists);
- its RESOLVED reply.

Five reviewer notes remain, all on matters still open: seeds/parameters, supplementary
packaging, data availability, and the two NAR editor notes on the byline and affiliations.

## 6. Validation

```
revisions 776 | w:t in w:del 0 | stray delText 0 | missing attrs 0 | dup ids 0
reject-all restores the original: True
citation fields: sdt 121 (was 121), hyperlinks 9 (was 9), contents identical: True
abstract after Accept All: 198 words (limit 200)
ALL CHECKS PASSED
```

All 121 Mendeley citation tags and 9 hyperlinks survive byte-for-byte. Revision ids were
started above the highest id already in the document — `nid()` restarts from a fixed base on
every run, and without reserving a range this pass produced 78 duplicate ids, which breaks
Word's revision pane.

## 7. Still open, for you

- Author byline `?` marks, affiliation numbering, ORCID iDs.
- Zenodo DOIs and the Data Availability statement; NAR does not accept GitHub as a primary
  archive.
- The five stub reference entries above the real Mendeley bibliography.
- Thirty Cyrillic planning paragraphs and the italic `{{…}}` placeholders.
- **Figure regeneration** — every figure still exceeds NAR's print box and uses Type 3
  unembedded fonts; Supplementary Figures 2–4 and 7 are 81–100 % below 5 pt at print size.
  This remains the largest obstacle to acceptance.
- `Figure 6.pdf` and `Extended Figure 8.pdf` still print `PCR` in axis labels, from before the
  PCReg rename.
- One reference-list artefact visible in the new sheet: entry 65 reads
  "Knapp,T.R. and Knapp,T.R. (2007)". That is Mendeley's, not mine — I do not edit the
  bibliography.
