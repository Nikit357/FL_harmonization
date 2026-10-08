# Article 2 revision plan — applying Daniil's review and finishing the unreviewed half, 2026-09-24

**Status:** DRAFT, revised 2026-09-25 after two rounds of Daniil's inline comments. No manuscript
text, figure or Figma node is touched until he approves.
**Base document:** `manuscript/FL_metric_classes_F1000_260917_edited_Daniil.docx` — **not** the
agentic `FL_metric_classes_F1000_260917.docx` and **not** the stale `.md`.
**Deliverable:** a new `.docx` carrying **Word tracked changes** against that base, so Accept All
gives the revised article and Reject All restores Daniil's edited copy byte for byte.
**Citations are out of scope for every agent** — the base now carries 46 Mendeley content controls
and Daniil manages them himself (§C1).

---

## Overview

Daniil reviewed the F1000Research draft and returned it with **37 comments** and **71 rewritten or
inserted paragraphs**. His review covers paragraphs 0–77 and 149–160 of 178 — the front matter,
Methods, the first five Results sub-sections and the supplementary legends he pasted in. **Paragraphs
78–148 he never reached**: the 53-paragraph `Cross-batch prediction elects a third set…` section, the
8-paragraph `The sets elected by the individual metric classes…` section, and `Conclusions`.

This plan does three things. It **applies the 37 comments** as literal instructions. It **carries his
71 silent rewrites into a standard** — recorded as `manuscript/daniil_review_principles_260924.md` —
and **edits the unreviewed 71 paragraphs to that standard** without waiting for a second review round.
And it **fixes the defects the edits themselves introduced**, of which three dissolved on
investigation: the metric counts 344 and 334 both reproduce exactly against Article 1's
Supplementary File 2, the 87 that the body already quotes is the scoring subset of the same 344
(§B5), and the "missing" reference-list entries are Mendeley-managed citations that Daniil's own
library already resolves (§C1).

The work runs on the same six-role, gated multi-agent workflow as
`f1000_article2_plan_260917.md` §6, with three changes forced by the task. A **figure-analyst** role
is added, because five of the 37 comments order figures rebuilt rather than text rewritten. **Figure
renumbering moves to the last phase**, after all content edits, because renumbering by order of first
citation is only stable once the new panels and the rewritten sections have stopped moving the
citation order. And the draft phase can **call back into the evidence phase**: rewriting the
unreviewed half will surface comparisons that need a statistic nobody has computed yet, and the
workflow has to be able to go and compute it rather than write around the gap (§W2b).

The key design decision is that the **principles document, not the comment list, drives the
unreviewed half.** A comment-by-comment plan would leave paragraphs 78–148 exactly as the agent wrote
them, which is the half Daniil has not yet objected to only because he has not yet read it.

---

## Background — what was measured

### B1. The four documents this plan rests on

| Document | What it holds | How it was produced |
|---|---|---|
| `manuscript/daniil_comments_260924.md` | All 37 comments, each with the **exact** span it is anchored to (collected between Word's `commentRangeStart`/`End` sentinels, so the four Abstract comments stay distinguishable), the section, and the approximate page | `tools/extract_daniil_review_260924.py` |
| `manuscript/daniil_diff_260924.md` | Paragraph-level diff: 110 unchanged, 61 rewritten, 10 inserted, 0 deleted | same script |
| `manuscript/daniil_review_principles_260924.md` | The standard: 8 evidence rules, 6 figure rules, 5 placement rules, 9 register rules, 6 ordered analysis changes, the introduced defects, and a per-paragraph checklist | written from the two above |
| this plan | The work | — |

Daniil edited the `.docx` directly, so **only 10 `w:ins` and 8 `w:del` are tracked revisions**. The
diff, not the revision marks, is the record of what he changed. Any tool that reads only tracked
changes will see almost nothing.

### B2. Review coverage, by section

| Paragraphs | Section | Edits | Comments | State |
|---:|---|---:|---:|---|
| 0–17 | Title, Abstract, Introduction | 14 | 3 | reviewed |
| 19–33 | Methods (5 sub-sections) | 12 | 4 | reviewed |
| 35–67 | Results 1–4 | 23 | 8 | reviewed |
| 68–77 | `Preservation of biomarker expression…` | 2 | 1 | **prose unreviewed**; the one comment (C50) is about figures |
| **78–130** | **`Cross-batch prediction elects a third set…`** | **0** | **0** | **not reviewed — 53 paragraphs** |
| **131–138** | **`The sets elected by the individual metric classes…`** | **0** | **0** | **not reviewed — 8 paragraphs** |
| **139–144** | **`Conclusions`** | **0** | **0** | **not reviewed — 6 paragraphs** |
| 145–148 | Data / Software availability | 0 | 0 | not reviewed |
| 149–160 | Supplementary material | 10 | 2 | reviewed — he pasted 10 model legends |
| 161–177 | Back matter, References | 0 | 0 | not reviewed |

### B3. The panel-citation audit — 31 declared panels are never cited

Computed from the legends in the edited copy against every figure reference in its body text, and
reproducible with `scientific_review_tools.py panels`. This is the concrete scope of principle
**B2** (*every panel is cited and described individually*).

| Figure | Panels declared | Panels cited | **Never cited** |
|---|---|---|---|
| Figure 2 | A–D | A, C, D | **B** |
| Figure 4 | A–G | A–F | **G** |
| Figure 5 | A–G | A–F | **G** |
| Supplementary Figure 3 | A–J | C, D, I, J | **A, B, E, F, G, H** |
| Supplementary Figure 4 | A–D | A, B | **C, D** |
| Supplementary Figure 5 | A–L | A, B, C | **D–L (9 panels)** |
| Supplementary Figure 6 | A–F | E | **A, B, C, D, F** |
| Supplementary Figure 7 | A–K | A, D, E, G–J | **B, C, F, K** |
| Supplementary Figure 8 | A–F | A, C, D, F | **B, E** |
| Figures 1, 3, 6; Supp. 1, 2, 9, 10 | — | — | none |
| Supplementary Figures 11–14 | **no full legend exists yet** | — | C73 orders legends written |

### B4. Supplementary figure renumbering — the map as the text stands today

Main figures 1–6 are already cited in order. Supplementary figures are not; their order of first
citation is **1, 6, 3, 2, 4, 5, 7, 8, 9, 10, 12, 14, 11, 13**, which gives:

| Old | 1 | **6** | 3 | **2** | **4** | **5** | 7 | 8 | 9 | 10 | **12** | **14** | **11** | **13** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **New** | 1 | **2** | 3 | **4** | **5** | **6** | 7 | 8 | 9 | 10 | **11** | **12** | **13** | **14** |

Eight figures move. **This map is provisional and must be recomputed in the final phase**, because
the rewritten sections and the new panels of §B6 change the citation order.

### B5. The metric census — settled, and both of Daniil's numbers are right

Investigated 2026-09-25 against
`figures_for_article/supplementary_260824/Supplementary File 2.xlsx`, sheet **`Metric_polarity`**,
which is Article 1's metric registry: one row per metric, with `Polarity`, `Metric group`,
`Metric type`, `Explanation` and `Calculation`.

| Number | Definition | Reproduces | Used for |
|---:|---|---|---|
| **344** | every row of `Metric_polarity` | **yes**, exactly 344 rows, 344 unique metric names | **the title and the Introduction** |
| **334** | 344 minus the 10 rows whose `Metric group` is `Metadata` (`group`, `is_best`, `is_raw`, `is_shambhala`, `shambhala_p_key`, `shambhala_q_key`, `harshness_level`, `baseline_missing`, `compute_time_s`, `pv_perm_comparable`) | **yes**, exactly 334 | **C48's cross-correlation clustermap** |
| **87** | the metrics carrying a **non-zero polarity**: 51 at `+1` and 36 at `-1`; the other 257 are descriptive and carry `0` | **yes**, 51 + 36 = 87 | the scoring subset the Methods and Results already quote |
| 303 | of the 334, those that are numeric columns in the pinned `metrics_comprehensive_260905.csv` | — | the set the clustermap can actually be computed on today |

**There is no contradiction to fix, only a sentence to add.** 344 is the metric registry; 87 is its
scoring subset. One clause in Methods — *"of these 344 metrics, 87 carry a scoring polarity and are
used for every ranking below"* — reconciles the title with the five existing mentions of 87, and
defect F2 closes.

My earlier reading that "no version of that number reproduces" came from counting columns in
`metrics_comprehensive_260905.csv` (329, of which 4 keys and 5 flags). That file is the computed
snapshot, not the registry, and it was the wrong object to count. The registry is the authority.

**Resolved in Phase 0 (2026-09-25): 329 of 334 recoverable, 5 absent** — see
`workflow_runs/260924_run1/09_metric_census.md`. The original note follows.

**The one open item:** 303 of the 334 non-metadata metrics are numeric columns in the pinned
snapshot; 31 are named differently there (for example `PCReg_RNA_BATCH` in the registry against the
snapshot's own spelling) or are derived downstream. The code-analyst maps the names before building
the C48 clustermap and reports how many of the 334 it recovered. If it recovers fewer than 334, the
figure legend states the number it used and why, rather than claiming 334.

### B6. The six analysis changes Daniil ordered

| # | Comment | Change | Feasible today? |
|---|---|---|---|
| E1 | C16 | Generalizability index: **F1 for both LOBO targets**, replacing LOBO2 AUC with `pv_lobo2_f1_macro_mean`; recompute, rewrite, redraw | yes |
| E2 | C48 | New: L/M/N scatterplots coloured by method and by strategy; cross-correlation clustermap over the **334 non-metadata metrics** with type/group/class annotation | yes — see the naming caveat in §B5 |
| E3 | C44 | Rebuild Supplementary Figure 12 as a **3×3 or 3×4 grid**; add the permutation null, F1 **and** AUC for LOBO2 **and** LOBO3, same/different-biology agreement; per-panel letters; drop H from the panel | yes — `pv_*_perm_mean` columns exist |
| E4 | C45 | New **Table 1**: the six harshness-tier metrics with their statistic and p, **and both AUC and F1 for both LOBO2 and LOBO3**; the full L/M/N set goes to a supplementary table | yes |
| E5 | C50 | Expression scatterplots → supplementary; drop the `01_raw` identity panels; add linear and non-linear methods | yes |
| E6 | C14, C15 | Resolve both `Supplementary File X` placeholders; create the average-percentile file if absent | yes |

**Panel reshaping is part of every one of these, not a separate task.** C44 and C50 are geometry
instructions and they bind each new or rebuilt figure: no one-row strip of seven plots, no
overlapping tick labels, every panel reduced by 1.5–2× to fit the reference frame `637:93145`, wide
panels narrowed to sit two per row, and in-panel notation matching the prose (`p = 1.4 × 10-9`,
never `p=1.4e-9`). A panel that carries the right data at the wrong geometry is not done.

**E1 and E4 are not in conflict.** The *index* uses F1 for both LOBO targets, because its six
components are averaged as rank percentiles and must be commensurable — that is exactly C16's
objection to mixing F1 with AUC. The *reported tables* (Table 1, Supplementary Figure 12) carry both
AUC and F1 for both targets, because there the two are read side by side for comparability rather
than averaged together.

---

## C. The two standing constraints

### C1. Citations — no agent touches one, ever

**Daniil's ruling:** *"Do not touch citations at all — keep the unedited ones as numbers in square
brackets, and those that I added with Mendeley — do not touch them at all, I will work with them
myself."*

Measured in the base document on 2026-09-25:

| Object | Count | Status |
|---|---:|---|
| Mendeley content controls (`w:sdt` carrying `MENDELEY_CITATION`) | **46** | Daniil's. Untouchable. The count is an **invariant**: 46 before any edit, 46 after. |
| Plain numeric citations surviving in the text | **4** — `[38]` twice, `[50,51]`, `[52]` | The "unedited ones". Carried through **verbatim**, including through a full paragraph rewrite. |
| Agentic original `FL_metric_classes_F1000_260917.docx` | 0 `w:sdt` | It had none; the content controls arrived with Daniil's pass. |

**This overturns an assumption in the previous draft of this plan**, which stated that the Article 2
line carries no Mendeley fields and that text-anchored replacement was therefore safe without
special care. It is not. The base is now a Mendeley-managed document and the hazard is live:
`word_rewrite_trackchanges.tracked_replace` rebuilds a paragraph from its concatenated text and
would destroy all 46 content controls **without raising an error**.

**Where the four numeric citations sit** — two of them are inside sections this plan rewrites, so
they need explicit protection rather than incidental survival:

| Citation | Section | Rewritten by this plan? |
|---|---|---|
| `[38]` | `Preservation of biomarker expression…` | yes (§1g) |
| `[38]` | `Cross-batch prediction elects a third set…` | yes (§1g) |
| `[50,51]` | Data availability | no |
| `[52]` | Supplementary material | no |

**Consequences, binding on every agent:**

- No agent converts a citation between styles, renumbers one, adds one to the running text, deletes
  one, or re-orders the reference list. The document stays in its current mixed state — 46
  author–year fields and 4 numeric brackets — and Daniil normalises it in Mendeley.
- Principle **D8** of the principles document ("citations are author–year") records what *Daniil
  did* in his own pass. It is **not** an instruction to agents and is superseded for this revision.
- **Defect F8 dissolves.** The 11 "citations introduced without reference-list entries" —
  Jovčevska, Sorokin, Risso, Kapoor, Saeb, Whalen, Ambroise, Varma, Soneson, Parker, Fiore — are all
  present in the body as Mendeley fields, so his library resolves them and generates the
  bibliography. The hand-maintained `manuscript/references_260917.md` is no longer the authority; it
  is a stale artefact of the pre-Mendeley draft.
- **C20 and C37 still ask for new citations**, and the only safe way to deliver them is as a
  **proposal, not an insertion**: the literature-scout resolves each reference and names the exact
  sentence it belongs to, in `11_citations_to_insert.md`, and Daniil inserts them through Mendeley.
  Agents write no placeholder and no bracket into the manuscript for these.
- Every tracked edit uses `nar_review_tools.safe_tracked_replace`, and every anchor is checked with
  `scientific_review_tools.py anchors` before use. An anchor that spans a content control is
  rejected, not worked around.

### C2. Statistics live in three places, and the main text gets at most five tables

**Daniil's ruling:** *"Add no more than 5 tables with statistics to the main text, all the rest
please move to supplementary tables. So you always prove all the numeric comparisons with
statistics, but this statistics lives in text (if it's small), in main table (if medium size) and in
supplementary tables (if large size)."*

Every numeric comparison is still proved. What changes is where the proof is printed:

| Size | Where | Definition |
|---|---|---|
| **small** | in the sentence | one comparison: at most three numeric values and one test result, which is rule 15's ceiling |
| **medium** | a **main-text table** | 2–15 comparisons the reader needs in order to follow the argument |
| **large** | a **supplementary table** | more than 15 rows, or any per-metric, per-method or per-strategy enumeration |

**Hard cap: five main-text tables.** A sixth is not created; its content goes to supplementary and
the text points at it. The provisional slate, which the team lead may re-allocate at gate 3 but may
not enlarge:

| Table | Content | Source | Serves |
|---|---|---|---|
| **Table 1** | Harshness tiers × the six metrics, with statistic and p, AUC **and** F1 for LOBO2 **and** LOBO3 | `A2_T9` | C45, C47 |
| **Table 2** | LOBO prediction summary for the named best groups: full cut and multiclass-only cut, both targets, both statistics | `A2_T13` | C47, the §78–130 rewrite |
| **Table 3** | Metric-class election overlap: Jaccard, intersection count and both set sizes for each pair of elected sets | `A2_T3` | the §131–138 rewrite, principle A1 |
| **Table 4** | Generalizability index: the top approaches with their six components under the E1 definition | `A2_T2` (260924) | C16, E1 |
| **Table 5** | *Reserve.* Allocated at gate 3 to whichever comparison set the rewrite shows the reader cannot follow without. | — | — |

Everything else — per-metric denominators (C46), the full L/M/N harshness set, the paired-test
catalogue `A2_T10`, the scatter-correlation catalogue `A2_T11`, the metric census `A2_T12` — goes to
the supplementary workbooks.

---

## The workflow

Same shape as `f1000_article2_plan_260917.md` §6 — six roles, teamlead gates between phases, two
revision rounds maximum per gate, every agent writing artifacts to disk **before** returning with a
`## Status` block at the top. The `HARD_RULES` block is inherited verbatim with eight additions (§W3).

Run directory: `workflow_runs/260924_run1/`.

### W1. Phases

```
Phase 0  RECONCILE          (sequential, blocks everything)
  └── code-analyst      → confirm the 344 / 334 / 87 census against Supplementary File 2;
                          record the citation invariants (46 Mendeley, 4 numeric);
                          the Shambhala sentence; the Markdown master regenerated from
                          Daniil's .docx

         ↓ gate 0: does the census reproduce? are the citation counts recorded?
                   is the master faithful to his edits?

Phase 1  EVIDENCE           (parallel)
  ├── code-analyst      → E1 index recompute; every missing Mann-Whitney, Spearman,
  │                       baseline and dispersion statistic; the five main tables and the
  │                       supplementary catalogues; tables A2_T9-T13
  └── literature-scout  → the C20 and C37 references resolved as a PROPOSAL LIST for
                          Daniil to insert through Mendeley; no citation is written into
                          the manuscript

         ↓ gate 1: does every new number resolve to a table? is every proposed citation
                   resolved to a PMID and pinned to a named sentence?

Phase 2  FIGURES            (sequential after gate 1; feeds Phase 3)
  └── figure-analyst    → E2, E3, E5 panels regenerated and B6 consolidated; C44/C50
                          geometry applied to every panel; panel inventory emitted

         ↓ gate 2: does every panel that exists have a letter, and every letter a home?

Phase 3  DRAFT              (parallel, three disjoint paragraph ranges)
  ├── writer-reviewed   → paragraphs 0-77 and 149-160: apply the 37 comments
  ├── writer-unreviewed → paragraphs 78-148: rewrite to the principles document
  └── legend-writer     → full legends for every figure and table; the 31 missing panel
                          citations placed in the body text
        │
        └──►  10_stat_requests.json  ──►  Phase 1 re-entry (code-analyst, figure-analyst)
              a claim that needs a statistic nobody has computed is QUEUED, not written
              around; the phase re-opens, the number is computed, the draft resumes

         ↓ gate 3: every paragraph passes the §G checklist, the density rule (r.15) and
                   the table budget (r.19); citations untouched

Phase 4  REVIEW             (parallel)
  ├── reference-verifier → the PROPOSAL LIST re-resolved from full text; the manuscript's
  │                        own citations are audited for integrity, never edited
  └── style-editor       → check_style, check_principles, check_overlap, density check,
                           table-budget check, antithesis grep

         ↓ gate 4: accept, or a specific defect list (max 2 rounds)

Phase 5  RENUMBER & DELIVER (sequential — must be last)
  └── teamlead          → recompute the figure order map, renumber text and Figma frames
                          together, build the TRACKED-CHANGES .docx against Daniil's
                          edited copy, verify the 46/4 citation invariants, provenance
                          table, open items
```

### W2. The two changes of shape, and why

**W2a. Renumbering is Phase 5, not Phase 3.** C29 asks for figure numbers aligned to citation order
"minimal but sufficient". The map in §B4 is computed from today's text; Phase 2 adds figures and
Phase 3 adds 31 panel citations and rewrites 71 paragraphs, each of which can move a figure's first
citation. Renumbering before those settle guarantees a second renumbering pass, and a second pass over
`Supplementary Figure 1` / `Supplementary Figure 10` prefixes is exactly the trap that already
corrupted one edit pass in this repository (`figures_for_article/CLAUDE.md`, the `figure_edits()`
discipline). The map is recomputed from the finished text and applied once, to the Markdown, the
`.docx` and the Figma frame names in the same commit. **Figure numbering is not citation
numbering** — C1 does not constrain it.

**W2b. Phase 3 can re-open Phase 1.** Rewriting 71 unreviewed paragraphs to principle **A2** — every
claim of difference carries a test — will surface comparisons for which no statistic exists yet, and
the same is true of **A3** (ρ and p for every scatter claim) and **A4** (a baseline beside every
subset proportion). The writer must not write around the gap, soften the claim, or invent a number.

The mechanism is a queue. A writer that needs an uncomputed statistic appends to
`workflow_runs/260924_run1/10_stat_requests.json`:

```json
{ "id": "SR-014", "requested_by": "writer-unreviewed", "paragraph": 96,
  "claim": "ComBat family leads the LOBO3 ranking over the remaining 27 methods",
  "needs": "Mann-Whitney U, two-sided raw p, pv_lobo3_f1_macro_mean, ComBat family vs rest",
  "destination": "medium -> main Table 2",
  "status": "open" }
```

and writes `[STAT: SR-014]` in place of the number. The `destination` field is filled in by the
writer against the §C2 tiers, so the team lead can see the main-table budget filling up before it
overflows. The team lead drains the queue at gate 3 by re-entering Phase 1 for the code-analyst —
and Phase 2 for the figure-analyst, where a request needs a panel rather than a number. Gate 3 does
not pass while any request is `open` or any `[STAT: …]` marker survives in the draft.

Budget: the re-entry is expected, not exceptional. It does not count against the two-revision-round
limit, because it is a request for evidence rather than a defect in the writing.

### W3. Additions to `HARD_RULES`

Appended to the inherited block, numbered to continue it:

```
11. THE BASE IS DANIIL'S EDITED COPY. FL_metric_classes_F1000_260917_edited_Daniil.docx. His
    wording wins over the agentic wording in every case where they differ, including where his
    sentence is longer or less polished. You are not re-editing his prose; you are extending it.
    The exception is the defects in §F of the principles document, which are slips.
12. THE PRINCIPLES DOCUMENT IS BINDING ON PARAGRAPHS 78-148. Every paragraph you write there
    must pass the §G checklist. An unreviewed paragraph that merely survives the style gate has
    not been edited.
13. NUMBERS ARE THREE SIGNIFICANT FIGURES. 0.7334 -> 0.733, 1.0000 -> 1.000. Counts, natural
    percentages and scientific-notation p-values are exempt. Round and re-run the number audit
    in the SAME pass; if a rounded value no longer matches its evidence spelling, add the
    rounded spelling to the evidence file -- do not loosen the audit.
14. DO NOT TOUCH A CITATION. Not one. The base carries 46 Mendeley content controls and 4 plain
    numeric brackets ([38] twice, [50,51], [52]); both counts are invariants and must be
    identical before and after your edit. Do not convert between styles, do not renumber, do
    not add, do not delete, do not reorder the reference list. When a rewritten paragraph
    contains a citation, carry it through VERBATIM. A needed new reference is PROPOSED in
    11_citations_to_insert.md with the sentence it belongs to; Daniil inserts it in Mendeley.
    Use safe_tracked_replace only, and check every anchor with `anchors` first: the ordinary
    tracked_replace destroys all 46 content controls without raising an error.
15. DO NOT OVERLOAD A SENTENCE WITH STATISTICS. A sentence carries at most THREE numeric
    values and at most ONE test result. Beyond that the structured tests move to a table --
    per rule 19 -- and the sentence keeps the qualitative result and its mechanism. Adding a
    required test is never a licence to build a nine-number sentence: if satisfying the
    statistics rule overloads the sentence, that is the signal to build a table, not to drop
    the statistic.
16. NEVER WRITE AROUND A MISSING NUMBER. If a claim needs a statistic nobody has computed,
    append a request to 10_stat_requests.json with its size tier and destination, write
    [STAT: <id>] in place of the value, and continue. Do not soften the claim, do not delete
    it, do not estimate the number. A draft returned with open [STAT: ...] markers is expected
    and correct; a draft that quietly avoided the comparison is a gate-3 failure.
17. HARMONIZATION_METRICS_EXTENDED_260920_V3.DOCX MAY BE REUSED FREELY. It is Daniil's own
    unpublished working document for Article 1, not a published source, so lifting panel
    descriptions from it is not plagiarism. Align pasted text to its new neighbours (C33).
    The verbatim-overlap gate runs against Article 1's manuscript ONLY.
18. THE DELIVERABLE IS A TRACKED-CHANGES .DOCX built against
    FL_metric_classes_F1000_260917_edited_Daniil.docx. Accept All must yield the revised
    article; Reject All must restore that base byte for byte, and this is verified with
    nar_review_tools.py validate, not asserted.
19. AT MOST FIVE TABLES IN THE MAIN TEXT. Every numeric comparison is still proved, but the
    proof is printed where its size says: one comparison in the sentence, 2-15 in a main
    table, more than 15 -- or any per-metric, per-method or per-strategy enumeration -- in a
    supplementary table. A sixth main table is not created; its content goes to supplementary
    and the text points at it.
```

### W4. The roles that change

**`code-analyst`** — unchanged brief, four new duties: confirm the §B5 census and map the 334
registry names onto the snapshot columns for the C48 clustermap; record the §C1 citation invariants;
recompute the generalizability index under E1 and report the rank churn it causes; produce every
statistic the principles demand but the draft lacks (A2–A6), **each tagged with its §C2 size tier and
destination**. It also **serves the `10_stat_requests.json` queue** on every Phase 1 re-entry,
appending to the same tables rather than creating new ones per round.

**`figure-analyst`** — new. *Reads to learn:* `figures/figma_layout_260920.md`,
`tools/figma_editable_text_260920.md` and `tools/split_panel_text_260920.py` for how the panels are
built and placed; `analysis/article2_generalizability.py` for the palettes; Article 1's
Supplementary Figure 7 for the clustermap style C48 asks to match. *Criteria:* every panel fits the
reference frame `637:93145`; reduced 1.5–2×; wide panels narrowed to two per row; no overlapping tick
labels; grids not strips; scientific notation matching the prose; every panel carries a letter.
*Artifacts:* `07_panels.{json,md}` — one row per panel with its figure, letter, source script, size
and status.

**`writer-unreviewed`** — new. *Reads to learn:* the principles document in full, then the five
Results sub-sections Daniil did edit, as worked examples of the register. *Criteria:* the §G
checklist per paragraph, plus `HARD_RULES` 14, 15, 16 and 19. *Artifact:* `03b_draft_unreviewed.md`,
written section by section, and `10_stat_requests.json` appended as it goes. **It carries the two
`[38]` citations in its range through verbatim.**

**`legend-writer`** — new. *Reads to learn:* the ten legends Daniil pasted (paragraphs 150–160) as
the template; `manuscript_versions/Harmonization_metrics_extended_260920_v3.docx` as the source of
panel prose, which rule 17 permits it to reuse freely. *Criteria:* B2 and B4. *Artifact:*
`08_legends.md` plus a patch list of the 31 body-text sentences that introduce the missing panels.

**`reference-verifier`** — **narrowed**. It no longer edits anything in the manuscript. Two duties:
re-resolve every entry of the literature-scout's `11_citations_to_insert.md` proposal list from full
text, and **audit** the manuscript's existing citations for integrity — the 46 content controls and
4 numeric brackets present and unchanged — reporting any drift as a gate-4 defect.

**`style-editor`** — extended: besides `check_style.py` and the antithesis grep it now runs
`check_principles.py --only density,tables` and is charged with **pushing back on statistic
overloading**. Where a paragraph has become a list of test results, its verdict is not "reword" but
"move these N tests to <named table>, tier <medium|large>, and keep the qualitative result". It also
enforces the five-table cap and says which table to demote when the budget is exceeded.

---

## Files to change

### 1. `manuscript/FL_metric_classes_F1000_260917.md` — the Markdown master

**1a. Regenerate from the edited `.docx` first (Phase 0).** The current `.md` predates Daniil's
edits, so every downstream gate would be run against the wrong text.

```bash
python tools/docx2md.py manuscript/FL_metric_classes_F1000_260917_edited_Daniil.docx \
    --out manuscript/FL_metric_classes_F1000_260924.md
```

Then diff it against `daniil_diff_260924.md` and confirm all 71 changed paragraphs are present, and
that the 46 Mendeley citations survive the conversion as readable author–year text. The `260917`
master is kept unchanged as the pre-review record.

**1b. Title (paragraph 0) — no change to the number.** 344 is confirmed (§B5), so Daniil's title
stands as written:

> 344 harmonization quality metrics analysis of 2,234 approaches in a multi-platform B-cell lymphoma
> bulk transcriptomic benchmark: ComBat is superior by cross-batch prediction quality

The only edit is `334` → `344` where the title currently carries the lower figure, so the title and
the Introduction agree.

**1c. Abstract (paragraphs 7–11).** C2 — name the approach. C3 — name the two methods. C4 — move the
single-class-fold sentence out to Results. Three edits, all in the Results sentence of the Abstract.

**1d. Introduction (paragraphs 12–18).** C7 — add 2–3 sentences on the differences between methods and
strategies by metric class. C8, C9 — the same naming demands as C2/C3. C10 — the same move as C4.
F4 — "An early 2021 empirical comparison" cites `(Rudy and Valafar 2011)`; **the year in the prose is
fixed, the citation field is not touched** (§C1).

**1e. Methods (paragraphs 19–33).**
**F2 — add the census sentence**: *"of these 344 metrics, 87 carry a scoring polarity (51 positive,
36 negative) and are used for every ranking below; the remaining 257 are descriptive"*, pointing at
Supplementary File 2 of the source benchmark. This one clause reconciles the title with the five
existing mentions of 87.
C14, C15 — resolve both `Supplementary File X` placeholders, creating the average-percentile file if
it does not exist. C16 — rewrite the index definition to F1 for both LOBO targets. C17 — name and
define "the worst multiclass fold". C20 — the statistics and software references are **proposed, not
inserted** (§C1); the Methods prose names each test and package, and Daniil adds the citations.
C21 — state that two-group comparisons use Mann-Whitney U, two-sided, uncorrected. F7 — restore one
sentence recording that `shambhala_P0std_Q0std` and `20_shambhala` are the same method and that
conflating them yields 2,150 instead of 2,234.

**1f. Results 1–4 (paragraphs 35–67).** C25, C40 — add Mann-Whitney p to every paired median claim,
routed by §C2: one comparison stays in the sentence, a set of them goes to Table 1–4, a large
enumeration to supplementary. C26 — three significant digits throughout. C28 — add the
all-approaches kBET baseline. C29 — figure numbering (deferred to Phase 5). C30, C38, C41 — cite and
discuss the missing panels. C31 — add ρ and p to every scatter claim, same routing. C32 — KNN.
C33 — align the pasted PCReg passages with their neighbours. C35 — consolidate the PC panels.
C37 — the reference for the class-count dependence of local metrics is **proposed, not inserted**.
C42 — name the dispersion statistic. C43 — give "weakly" its comparator. C44 — rebuild Supplementary
Figure 12. C45 — create Table 1 and strip the numbers from the text. C46 — move the per-metric n
values to a supplementary table. C47 — delete the superseded-calculation paragraph (**F3**: it is
still present) and put both LOBO variants in Table 2.

**1g. Paragraphs 68–148 — the unreviewed body.** Rewritten to the principles document. Per
sub-section:

- `Preservation of biomarker expression…` (68–77) — prose to **D1/D2**, figures per C50. **Carries
  one `[38]`** — verbatim.
- `Cross-batch prediction elects a third set…` (78–130), **53 paragraphs, the largest single task**.
  Expect: opening sentences rewritten to **D1**; every named approach spelled out (**A1**); the LOBO
  numbers routed to **Table 2** under rule 19 with the four-column full/multiclass discipline
  preserved; the permutation null reported per **E3**; a closing **D2** paragraph. **Carries one
  `[38]`** — verbatim. This section is where the `10_stat_requests.json` queue will fill fastest.
- `The sets elected by the individual metric classes…` (131–138) — the Jaccard results. Every
  overlap claim needs its intersection count and both set sizes (**A1**), which is 28 pairs and
  therefore **Table 3**, not prose. The section needs its **D2** close.
- `Conclusions` (139–144) — the six-step recipe. Check against **D4**: this is where aphorism is most
  likely to have survived.

**1h. Supplementary material (149–160).** C73, C74 — full panel-by-panel legends for Supplementary
Figures 11–14 and for every supplementary table, to the template of the ten Daniil pasted, and remove
the short descriptions. Panel prose is lifted from `Harmonization_metrics_extended_260920_v3.docx`
and aligned to its neighbours (rule 17). **Carries `[52]`** — verbatim.

**1i. Back matter (161–177).** **F6** — the two-author list is final, so this is now an edit to make,
not a question: rewrite Author contributions, Competing interests and Acknowledgements for Daniil
Nikitin and Arsen Arakelyan, and check the F1000 submission metadata for the same assumption.
Data availability **carries `[50,51]`** — verbatim.

### 2. `analysis/article2_generalizability.py`

**2a.** `GENERALIZABILITY_COMPONENTS` (or equivalent): replace `pv_lobo2_auc_macro_mean` with
`pv_lobo2_f1_macro_mean`, so both LOBO components are F1. Keep the six-component structure; only the
third component changes.

**2b.** Add the two-group test helper the principles require:

```python
def mannwhitney(a: pd.Series, b: pd.Series) -> tuple[float, float]:
    """Two-sided Mann-Whitney U for a paired-median claim in the text.

    Returns
    -------
    tuple[float, float]
        The U statistic and the raw two-sided p-value. No multiple-testing
        correction is applied: Daniil's C25 asks for raw p-values so each claim
        can be read against its own comparison.
    """
```

**2c.** Emitters, each tagged `main` or `supplementary` so the §C2 budget is machine-checkable:

| Table | Tier | Content |
|---|---|---|
| `A2_T9_harshness_table1` | **main** (Table 1) | the six metrics by harshness tier, AUC and F1 for both LOBO targets |
| `A2_T13_lobo_summary` | **main** (Table 2) | full and multiclass-only cuts, both targets, both statistics, for the named groups |
| `A2_T3_cross_election_matrix` | **main** (Table 3) | extended with intersection counts and both set sizes per pair |
| `A2_T2_generalizability_ranking_260924` | **main** (Table 4) | the E1 index with its six components |
| `A2_T9b_harshness_full` | supplementary | the full L/M/N set by tier |
| `A2_T10_paired_tests` | supplementary | every Mann-Whitney the text relies on |
| `A2_T11_scatter_correlations` | supplementary | ρ and p per scatter claim |
| `A2_T12_metric_census` | supplementary | the §B5 census |

**2d.** `A2_T2` is written to a **new dated file** (`…_260924.csv`), never overwriting the 260917
table that the current text cites.

**2e.** A loader that maps the 334 non-metadata registry names onto the snapshot columns for the C48
clustermap, reporting how many were recovered (§B5).

### 3. `analysis/build_numbers_json.py`

Extend the evidence JSON with the new tables so `audit_numbers.py` can resolve the new statistics.
It must also carry the **three-significant-digit spellings** alongside the full-precision ones, so
rule 13's rounding does not break the audit.

### 4. `tools/check_principles.py` — new

The mechanical half of the principles document, as a gate. Checks, per paragraph of the Markdown:

| Rule | Check | Blocks? |
|---|---|---|
| D5 | any decimal with four or more significant figures outside a p-value or a count | yes |
| D7 | British spellings from a fixed list | yes |
| **C1 citations** | **the 46 Mendeley fields and 4 numeric brackets are present and unchanged** | **yes** |
| D4 | the antithesis and aphorism patterns, extended from `check_style.py` | report |
| A3 | a sentence naming a scatter/plot relationship with no ρ and p in the same sentence | report |
| B2 | panels declared in a legend but never cited in the body | yes |
| B1 | supplementary figure citation order against the numbering | yes |
| r.15 density | a sentence carrying more than three numeric values or more than one test result — reported with the table it should move to | yes |
| **r.19 tables** | **more than five main-text tables, or a table whose row count contradicts its tier** | **yes** |
| r.16 markers | any surviving `[STAT: …]` marker, and any `10_stat_requests.json` entry still `open` | yes |

**The D8 check of the earlier draft — "flag bracketed numeral citations" — is removed.** Numeric
brackets are now *required* to survive, so flagging them would invert the rule.

Much of this already exists: `scientific_review_tools.py` in the `scientific-review` skill ships
`stats` (P11) and `panels` (P12) subcommands that cover A3 and B2/B1 and were validated against this
very manuscript, and `citations` for the content-control inventory. `check_principles.py` calls them
rather than reimplementing them.

### 5. Figures — `figures/panels_260917/` and the Figma frames

New or rebuilt panels for E2, E3, E5 and the B6 consolidation. Each goes through the existing
two-stage pipeline: `tools/split_panel_text_260920.py` then the runbook
`tools/figma_editable_text_260920.md`, so the text stays editable — the property restored on
2026-09-20 and which a naive re-render would destroy.

**Geometry is a requirement, not a preference (C44, C50).** Every panel reduced by 1.5–2×; wide
panels narrowed to sit two per row; every frame fits the reference frame `637:93145`; one-row strips
become 3×3 or 3×4 grids; no overlapping tick labels; in-panel notation matches the prose.
`Figure 6 - Recipe` (`1255:4`) is **not touched** — Daniil finishes it by hand.

### 6. `manuscript/references_260917.md` — demoted, not converted

The earlier draft of this plan had a task here to convert 52 numbered entries to author–year and add
new ones. **That task is deleted** (§C1). The reference list is now generated by Daniil's Mendeley
library, so:

- `references_260917.md` and `reference_support_260917.md` are **frozen** and marked in their own
  headers as pre-Mendeley artefacts, superseded as the authority. No agent edits them.
- New references required by C20 and C37 go to a new file,
  `workflow_runs/260924_run1/11_citations_to_insert.md`: one row per proposed reference with its
  PMID or DOI, the quoted supporting passage, and the exact manuscript sentence it belongs to.
- Daniil inserts them in Mendeley and refreshes the bibliography. This is recorded as a hand-off in
  the run report, not as an agent task.

### 7. `tools/build_tracked_revision_260924.py` — new, the deliverable

Builds `manuscript/FL_metric_classes_F1000_260925.docx` as **tracked changes against
`FL_metric_classes_F1000_260917_edited_Daniil.docx`**.

**The base is a Mendeley-managed document: 46 content controls.** The previous draft of this plan
asserted the opposite and would have licensed an unsafe edit path. Concretely:

- Use `nar_review_tools.safe_tracked_replace`, **never**
  `word_rewrite_trackchanges.tracked_replace`: the latter rebuilds a paragraph from its concatenated
  text and destroys every nested content control **without raising an error**.
- Run `scientific_review_tools.py citations` **before the first edit** and record the counts;
  re-run after and require them identical.
- Check every anchor with `scientific_review_tools.py anchors … --anchor "…"`. An anchor that
  returns `UNSAFE` is replaced with a different anchor, never forced.
- `set_revision_identity("Claude (Article 2 revision 2026-09-25)", …)` so the authorship of the
  revisions is unambiguous in Word.
- Deleting a passage that contains citations is allowed, but leaves orphan citation-only paragraphs
  behind. Count them and report them for Daniil to clear in Word; do not attempt to delete the
  content controls.
- Contract, verified not asserted: **Accept All** yields the revised article, **Reject All** restores
  Daniil's edited copy byte for byte.

**Note the local environment gap:** `lxml` is not installed in this Mac's `collagen_3_11`, so the
`.docx` paths of both tool modules cannot run here. Either install it or build the `.docx` on the
pod; the text-only audits run fine locally.

### 8. `workflows/article2_f1000.workflow.js`

New phase list, the three new roles, the narrowed reference-verifier, the nine appended
`HARD_RULES`, the Phase 3 → Phase 1 re-entry of §W2b, and `runDir` `workflow_runs/260924_run1`. The
existing script is copied to `workflows/article2_revision_260924.workflow.js` rather than edited in
place, so the run that produced the current draft stays reproducible.

### 9. `CLAUDE.md` and `README.md` (this directory)

A "Revision round 1" subsection under "Article 2 in progress": the base document is Daniil's edited
copy, the four review documents and what each holds, the principles document as the standard for the
unreviewed half, the metric census of §B5, **the citation freeze and the 46/4 invariants**, the
five-table budget, the renumbering-last rule, and the tracked-changes deliverable.

---

## Files that do NOT need to change

| File | Why |
|---|---|
| `manuscript/FL_metric_classes_F1000_260917.docx` and `.md` | The pre-review record. Kept for the diff; superseded as the working master. |
| `manuscript/FL_metric_classes_F1000_260917_edited_Daniil.docx` | **The base.** It is read and diffed against, never overwritten; the revision is a new file. |
| `manuscript/references_260917.md`, `reference_support_260917.md` | **Frozen** (§C1, §6). Mendeley is the authority now. |
| `manuscript/FL_metric_classes_F1000_260917_pre_fig4split.docx`, `_pre_suppfile3.docx` | Historical snapshots; the repository never chains snapshots. |
| `manuscript_versions/*.docx` | The extended-document line is a separate document. v3 is **read** and reused for panel prose (rule 17) and not edited. |
| `tables/A2_T0`, `A2_T1`, `A2_T4`–`A2_T8` | Unaffected. `A2_T2` gets a new dated file and `A2_T3` is extended; the rest stand. |
| `supplementary/A2_Supplementary_File_1/2/3_260917.xlsx` | Rebuilt by `build_supplementary_workbooks.py` at the end of the run, not hand-edited. |
| `figures_for_article/supplementary_260824/Supplementary File 2.xlsx` | Article 1's metric registry — the authority for §B5. Read-only. |
| `figures/panels_260917/editable_260920/` | Regenerated by the existing script for changed panels only. |
| `Figure 6 - Recipe` (Figma `1255:4`) | C50: *"Figure 6 is OK, do not touch it — I will do this manually."* |
| The 13 Extended Figure frames on Figma Page 2 | Protected; renaming remains the only edit ever permitted. |
| `tools/split_panel_text_260920.py`, `tools/figma_editable_text_260920.md` | The panel pipeline works; it is used, not modified. |

---

## Decisions taken and caveats

1. **Citations are frozen (§C1).** 46 Mendeley content controls and 4 numeric brackets, both counts
   invariant. No conversion, no renumbering, no insertion, no reference-list maintenance. New
   references are proposed for Daniil to insert. Principle D8 of the principles document is
   superseded as an instruction to agents. **This overturns the previous draft of this plan**, which
   planned a full author–year conversion and wrongly recorded the base as free of content controls.

2. **Statistics are routed by size, and the main text takes at most five tables (§C2).** Every
   numeric comparison is still proved; small proofs stay in the sentence, medium ones go to one of
   the five main tables, large ones to supplementary. The style-editor names the destination.

3. **Reuse from `Harmonization_metrics_extended_260920_v3.docx` is permitted and is not plagiarism.**
   It is Daniil's own unpublished working document, the source material for Article 1. Panel
   descriptions are lifted freely and aligned to their new neighbours (C33). **Consequence for the
   gate:** `check_overlap.py` runs against Article 1's manuscript only.

4. **The generalizability index uses F1 for both LOBO targets.** Replacing LOBO2 AUC with LOBO2 F1
   changes one of six components, so `A2_T2`, the top-40 ordering, the `a2_p8` panel and every
   sentence quoting an index value or rank move together. The code-analyst reports the rank churn
   explicitly; if the top approaches change identity, the Abstract and Conclusions change too.
   The reported tables still carry **both** AUC and F1 for **both** LOBO2 and LOBO3.

5. **Three significant digits, decided.** Rounding and the number audit run in the **same** pass,
   and the evidence JSON gains the rounded spellings; the audit is not loosened to accommodate the
   rounding.

6. **The metric census is settled (§B5).** 344 for the title and Introduction, 334 for the C48
   clustermap, 87 as the scoring subset — all three reproduce against Supplementary File 2. The one
   residual is the registry-to-snapshot name mapping: if fewer than 334 metrics are recoverable as
   snapshot columns, the clustermap legend states the number actually used.

7. **Renumbering touches Figma and Word in the same pass.** The figure map is applied to the
   Markdown, the `.docx` and the Figma frame names together, by node id, with the longest key first —
   `Supplementary Figure 1` is a prefix of `Supplementary Figure 10`, the trap that already corrupted
   one pass in this repository. Figure numbering is unaffected by the citation freeze.

8. **The unreviewed half is 71 paragraphs and will not survive one agent's context.** The
   `writer-unreviewed` role writes section by section, appending to `03b_draft_unreviewed.md` after
   each. Budget two Phase-3 rounds for it alone, plus at least one Phase 1 re-entry to drain the
   statistics queue.

9. **The author list is final at two.** Daniil Nikitin and Arsen Arakelyan. Author contributions,
   Competing interests, Acknowledgements and the submission metadata are rewritten to match (§1i).

10. **Word-count.** F1000Research has no hard limit, but the draft grows: 31 new panel discussions,
    2–3 new Introduction sentences, five "Taken together" paragraphs and up to five tables, against
    savings from C45, C46, C47 and rules 15 and 19. Expect net growth of 15–20%.
    `check_style.py --max-words` is re-baselined rather than allowed to fail.

11. **Rules 15 and 19 pull against the statistics rules, on purpose.** "Every claim of difference
    carries a test" adds numbers; "at most three numbers per sentence" and "at most five main tables"
    constrain where they can go. The resolution is never to drop the test — it is to move it down a
    tier. If the five main tables are full, the next medium-sized set goes to supplementary and the
    text points at it.

---

## Verification commands

```bash
source ~/venvs/collagen_3_11/bin/activate
cd <repo>/article_2_extended_comparison

# 0. Re-extract the review (idempotent; regenerates the three source documents)
python tools/extract_daniil_review_260924.py
#    expect: paragraphs A=161 B=178, comments 37, replace=61 insert=10 equal=110

# 1. The Markdown master is faithful to Daniil's .docx
python tools/docx2md.py manuscript/FL_metric_classes_F1000_260917_edited_Daniil.docx \
    --out manuscript/FL_metric_classes_F1000_260924.md
python - <<'PY'
import pathlib
md = pathlib.Path("manuscript/FL_metric_classes_F1000_260924.md").read_text()
diff = pathlib.Path("manuscript/daniil_diff_260924.md").read_text()
missing = [l[2:].strip() for l in diff.splitlines()
           if l.startswith("+ ") and len(l) > 80
           and l[2:90].split("  `[C")[0].strip() not in md]
print("\n".join(missing[:5]) or f"OK - all {diff.count(chr(10)+'+ ')} edited paragraphs present")
PY

# 2. The metric census reproduces — 344 / 334 / 87, from Article 1's registry
python - <<'PY'
import pandas as pd
d = pd.read_excel("../figures_for_article/supplementary_260824/Supplementary File 2.xlsx",
                  sheet_name="Metric_polarity")
meta = (d["Metric group"].astype(str) == "Metadata").sum()
print("total metrics          :", len(d),            "(expect 344)")
print("non-metadata (C48 set) :", len(d) - meta,     "(expect 334)")
print("scoring |polarity| = 1 :", int((d.Polarity != 0).sum()), "(expect 87 = 51 + 36)")
PY

# 3. THE CITATION INVARIANTS — run before the first edit and after the last
python - <<'PY'
import zipfile, re, sys
base = "manuscript/FL_metric_classes_F1000_260917_edited_Daniil.docx"
d = zipfile.ZipFile(base).read("word/document.xml").decode("utf-8", "ignore")
txt = " ".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", d))
print("Mendeley content controls:", d.count("MENDELEY_CITATION"), "(expect 46)")
print("numeric brackets in text :", len(re.findall(r"\[\d+(?:[,\-]\s*\d+)*\]", txt)), "(expect 4)")
PY
#    the same two numbers must come back from the revised .docx, unchanged

# 4. The gates, all of which must exit 0. check_overlap runs against Article 1 ONLY —
#    the extended document is Daniil's own unpublished source and may be reused (decision 3).
python tools/audit_numbers.py manuscript/FL_metric_classes_F1000_260924.md \
    --tables tables/ --evidence workflow_runs/260924_run1/01_numbers.json
python tools/check_style.py manuscript/FL_metric_classes_F1000_260924.md --journal f1000
python tools/check_principles.py manuscript/FL_metric_classes_F1000_260924.md   # new
python tools/check_overlap.py manuscript/FL_metric_classes_F1000_260924.md \
    --against ../figures_for_article/FL_manuscript_versions/FL_harmonization_article_NAR_260912.docx \
    --ngram 8
grep -nEi "rather than|, not [a-z]+\.|it is not .*, it is" manuscript/*.md   # must print nothing

# 5. Panel coverage: every declared panel is cited (principle B2)
python ~/.claude/skills/scientific-review/scientific_review_tools.py \
    panels manuscript/FL_metric_classes_F1000_260924.md
#    expect: 0 uncited panels and 0 citation-order inversions (baseline today: 31 and 8)

# 6. Statistical support: every claim of difference carries its test (principle A2/A3)
python ~/.claude/skills/scientific-review/scientific_review_tools.py \
    stats manuscript/FL_metric_classes_F1000_260924.md
#    baseline today: 146 advisory hits; the target is the Results sections near zero

# 7. Density, the table budget, and the statistics queue (HARD_RULES 15, 19, 16)
python tools/check_principles.py manuscript/FL_metric_classes_F1000_260924.md \
    --only density,tables
grep -cE "^\s*\*?\*?Table [1-9]" manuscript/FL_metric_classes_F1000_260924.md   # must be <= 5
grep -n "\[STAT:" manuscript/FL_metric_classes_F1000_260924.md     # must print nothing
python -c "import json;q=json.load(open('workflow_runs/260924_run1/10_stat_requests.json'));\
print('open requests:', sum(r['status']=='open' for r in q))"       # must be 0

# 8. The tracked-changes deliverable: Accept All = revised, Reject All = Daniil's copy,
#    and the citations are untouched
python ~/.claude/skills/scientific-review/scientific_review_tools.py \
    citations manuscript/FL_metric_classes_F1000_260925.docx      # expect 46 / 46
python ~/.claude/skills/nar_review_tools.py validate \
    manuscript/FL_metric_classes_F1000_260917_edited_Daniil.docx \
    manuscript/FL_metric_classes_F1000_260925.docx
#    expect: ALL CHECKS PASSED, a revision count > 0, sdt count unchanged
#    (requires lxml; not installed in this Mac's collagen_3_11 — run on the pod)
```

---

## TODO

### Phase 0 — reconcile (blocks everything)
- [x] Settle the metric total — **344 / 334 / 87 all confirmed against Supplementary File 2,
      sheet `Metric_polarity`** (§B5)
- [x] Record the citation invariants — **46 Mendeley content controls, 4 numeric brackets
      (`[38]` ×2, `[50,51]`, `[52]`)**, and locate them by section (§C1)
- [x] Regenerate the Markdown master from Daniil's `.docx` as `FL_metric_classes_F1000_260924.md`
      (2026-09-25; `docx2md.py` takes positional `SRC DST`, not `--out` as §1a and verification 1
      write it. The master also carries Word comment markers `[[COMMENT-n-START/END]]`, a
      "Comments in document" appendix, and tracked deletions as `~~…~~`)
- [x] Verify all 71 edited paragraphs survive the round trip, and that the 46 citations survive the
      Markdown conversion as readable text (verification 1) — **all 178 non-empty paragraphs of
      the base, and all 68 `+` lines of `daniil_diff_260924.md`, are present** once comment markers
      and `~~deletions~~` are stripped (the "71" counts diff operations; 68 is the number of
      non-empty added paragraphs the diff prints). All 46 Mendeley field texts appear verbatim as
      author–year strings; the body carries the same 4 numeric brackets
- [x] Write `workflow_runs/260924_run1/09_metric_census.md` recording the §B5 table
- [x] Map the 334 registry names onto the snapshot columns; report how many are recoverable —
      **329 of 334** (303 direct, 7 `PCReg_*`→`pcr_*` rename at ρ = 1.000, 2 derived percent,
      14 derived from the `01_raw` baseline, 3 boolean flags); **5 absent** (rare-diagnosis
      `xb_rank_agree_*` columns, all descriptive). All 87 scoring metrics recoverable. At most 328
      can enter a correlation (`mk_is_self_reference` is constant). Script and map:
      `workflow_runs/260924_run1/phase0_map_registry_to_snapshot.py`, `09_registry_to_snapshot_map.csv`
- [x] Freeze `references_260917.md` and `reference_support_260917.md` with a header note

### Phase 1 — evidence
Done 2026-09-25; gate-1 packet `workflow_runs/260924_run1/13_phase1_evidence_report.md`.
Default `--stamp` is now 260924; `--stamp 260917` still reproduces all nine 260917 tables.
- [x] `article2_generalizability.py` — F1 for both LOBO targets in the index (`INDEX_COLUMNS`;
      the old definition kept as `INDEX_COLUMNS_260917`)
- [x] `article2_generalizability.py` — add `mannwhitney()`; emit `A2_T10_paired_tests` (supplementary)
      — 285 tests (Mann-Whitney, Kruskal-Wallis, Fisher, Wilcoxon signed-rank, binomial), each
      with the text's quoted numbers and a `quoted_reproduced` check
- [x] `article2_generalizability.py` — emit `A2_T11_scatter_correlations` (supplementary) — 97 rows
- [x] `article2_generalizability.py` — emit `A2_T9_harshness_table1` (main, Table 1) and
      `A2_T9b_harshness_full` (supplementary) — Table 1 has 11 rows, not six: AUC has only one
      fold cut because it is undefined on single-class folds (report deviation 3–4)
- [x] `article2_generalizability.py` — emit `A2_T13_lobo_summary` (main, Table 2) — adds the new
      2-class multiclass-only columns `f1_mc2_mean/min`
- [x] `article2_generalizability.py` — extend `A2_T3` with intersection counts and set sizes
      (main, Table 3) — as `A2_T3b_cross_election_pairs` (36 pairs, + hypergeometric chance p,
      supplementary); the 9-row matrix `A2_T3` stays the main Table 3 (report deviation 2)
- [x] `article2_generalizability.py` — emit `A2_T12_metric_census` (supplementary)
- [x] `article2_generalizability.py` — the registry→snapshot name mapper for the C48 clustermap
      (`registry_snapshot_map()`: 329 of 334 recoverable, with the Article 2 class per metric)
- [x] Regenerate `A2_T2` to `…_260924.csv` (main, Table 4); report the rank churn from E1 —
      main-text form is `A2_T2b` (top 15 eligible). Churn: `12_index_rank_churn.md`; leader
      unchanged, top 15 eligible now all ComBat (6 of 15 shared with 260917)
- [x] Tag every emitted table `main` or `supplementary` so rule 19 is machine-checkable —
      `tables/A2_table_registry_260924.csv`; the script asserts ≤ 5 main and ≤ 15 rows each.
      Added `A2_T14_dispersion` (C42/C43), not named in the plan
- [x] `build_numbers_json.py` — add the new tables, and the three-digit spellings alongside the
      full-precision values (`spellings_3digit`, 325 entries; `--stamp`, default 260924)
- [x] literature-scout — `11_citations_to_insert.md`: the C20 statistics and software references and
      the C37 reference, each resolved to a PMID/DOI with its target sentence. **Proposal only — no
      citation is written into the manuscript** — 24 proposals, 0 unresolved; C37 first choice
      Luecken et al. 2022 (already cited)

### Phase 2 — figures
Done offline 2026-09-25 by `figures/article2_figures_260925.py` (8 composite figures, each drawn
at the reference frame's size, 2 px = 1 pt) and `tools/split_figure_text_260925.py` (Figma
overlays; the 260920 script is imported, not modified). The reference frame `637:93145` is
756 × 1159 px (read from `figures/figma_snapshots/`). Inventory: `workflow_runs/260924_run1/07_panels.md`.
- [x] E3 — rebuild Supplementary Figure 12 as a 3×3 or 3×4 grid with per-panel letters, permutation
      null, and AUC **and** F1 for LOBO2 **and** LOBO3; drop H from the panel — `sfig_harshness`,
      3×4, A–L; adds different-biology agreement, margin gain and the multiclass-only F1 of both
      targets; Kruskal–Wallis p from `A2_T9/T9b` as `p = 1.4 × 10⁻⁷⁴`
- [x] E2 — L/M/N scatterplots coloured by method and by strategy — `sfig_lmn_scatter` (A–F) and
      Figure 4A/B (margin vs marker correlation), ρ and p from `A2_T11`
- [x] E2 — cross-correlation clustermap over the 334 non-metadata metrics, annotated by type, group
      and class — `sfig_metric_clustermap`: **325** used (5 absent from the snapshot, 4 constant or
      sparse: `dsc_pvalue_COHORT_LABEL`, `mk_is_self_reference`, `pv_n_perm`, `xb_subsampled`)
- [x] E5 — expression scatterplots to supplementary; drop `01_raw`; add linear and non-linear methods
      — `sfig_expression`: 4 linear (03_limma, 05_combat, 29_combat_ref, 13_fsmvn) and 4 non-linear
      (16_fsqn_r, 17_quantile, 10_mnn, 12_scanorama) × BCL6, IRF4, EEF1A1, S0_no_removal/KNN/post0;
      genes persisted to `figures/panels_260925/data/sfig_expression_long_260925.csv.gz`
- [x] B6/C35 — consolidate the per-component PCA panels into one figure — `sfig_pca` (A–D). The
      Page 2 frames of Figure 1 and Supplementary Figure 2 are protected and untouched
- [x] **C44/C50 geometry on every new and changed panel** — all 10 frames ≤ 756 × 1159 (Figure 4 was
      6,229 px tall, Figure 5 2,585), 0 overlapping text boxes by an automated check, grids not
      strips, `× 10⁻ⁿ` notation, smallest label 10 px in the redrawn figures. Supp. Figs 11 and 13
      are re-laid out, not redrawn: 13 at 1/1.5; 11 at 1/1.2 only, because 1/1.5 puts its gene
      labels at 4.9 px, under the 6 px floor. Old Figure 5E–G became their own figure
      (`fig_election`) so Figure 5 fits
- [x] Re-run `split_panel_text_260920.py` for changed panels; re-apply the editable-text runbook —
      overlays and text-free artworks for all 10 frames in `figures/for_figma_upload/<figure>/`
      (driver `tools/split_figure_text_260925.py`). **Placed in Figma 2026-09-25 on Page 3
      (`1013:3`)**, frames `1321:3`–`1321:46`, 1,291 editable Inter TEXT nodes; node ids and checks
      in `figures/figma_layout_260925.md`. Page 2 untouched (58 nodes, 0 differences)
- [x] Emit `07_panels.{json,md}` — the panel inventory the legend writer consumes (10 figures, 49
      panels, with the legend and text changes each one forces)

### Phase 3 — draft
Done 2026-09-25; gate-3 packet `workflow_runs/260924_run1/16_phase3_report.md`. Three parallel
writers (`03a_draft_reviewed.md`, `03b_draft_unreviewed.md`, `08_legends.md`, brief
`03_brief_common.md`) over the paragraph index `00_paragraph_index.md`; assembled by
`tools/assemble_draft_260925.py` into **`manuscript/FL_metric_classes_F1000_260925.md`** plus the
tracked-change edit list `03_revision_edits.json`. Changed figures are cited by `[FIG:<name>]` tokens,
resolved in Phase 5. **Before drafting, a Phase 1 bug was found and fixed on Daniil's decision:**
the global class had lost its 7 PCReg metrics (`15_pcreg_fix.md`).
- [x] Abstract — C2, C3, C4 (the shared L/N approach named: 01_raw under I_rare_batches_removed /
      softimpute / post1; the two class M methods named; fold sentence moved to Results)
- [x] Introduction — C7, C8, C9, C10; fix the F4 year in the prose only; `334` → `344`
- [x] Methods — the F2 census sentence; C14, C15, C16, C17, C21; name the tests and packages for
      C20 without inserting citations; restore the Shambhala sentence (F7) — C15's file created as
      `A2_T15` (Supplementary File 1, sheet `Class_percentile_scores`)
- [x] Results 1–4 — C25, C26, C28, C30, C31, C32, C33, C35, C38, C40, C41, C42, C43 — plus every claim
      the Phase 1 evidence report proved wrong (kBET baseline, biology PCReg, Watermelon, graph
      connectivity swap, strict vs KNN, post-removal shift)
- [x] Results — C45 (Table 1), C46 (supplementary), C47 (delete the superseded paragraph F3; both
      LOBO variants to Table 2)
- [x] Paragraphs 68–77 — rewrite to D1/D2; carry `[38]` verbatim (the numeric citation in this range
      is `[50,51]`; `[38]` sits in Data availability and Supplementary material — all four carried)
- [x] Paragraphs 78–130 — rewrite `Cross-batch prediction…` to the §G checklist; route the LOBO
      numbers to Table 2; carry `[38]` verbatim (`[52]` is the citation in this range; carried)
- [x] Paragraphs 131–138 — rewrite `The sets elected…`; the 28 overlap pairs go to Table 3 (9 × 9
      matrix, 36 pairs, with hypergeometric chance expectations; PCReg-fixed values)
- [x] Paragraphs 139–144 — rewrite `Conclusions`; check hard against D4
- [x] Place the 31 missing panel citations in the body (B2) — Supp. Figs 3–8 panels cited in
      P49–P63 and the inserts P59+1…+3, P62+1; verified mechanically in Phase 4 (`panels`)
- [x] Full legends for Supplementary Figures 11–14 and every supplementary table (C73, C74),
      reusing `…extended_260920_v3.docx` prose and aligning it to its neighbours; carry `[52]` —
      7 new supplementary figure legends and 3 Supplementary File legends (P159+1…+10); P160 held
      `[38]`, carried into P159+8
- [x] Fix the typos of F5 (`mnatrix`, `appricase`, `generatability`)
- [x] Back matter — rewrite for the final two-author list (F6); carry `[50,51]` verbatim —
      acknowledgements and employment left as questions for Daniil (report §Questions)
- [x] **Drain `10_stat_requests.json`** — re-enter Phase 1/2 for every open request; no `[STAT: …]`
      marker survives — 17 requests in three per-writer files, all resolved; 8 overturned a draft
      claim and the sentence was corrected (report table)
- [x] Confirm the main-text table count is ≤ 5 before closing the phase — 4
- [x] Rule-15 density — done in Phase 4 (64 sentences; `check_principles --only density` = 0)
- [x] Length re-baseline (Results 7,088 → 12,873 words; abstract 351 of 300; total 20,157 of
      20,000) — done in Phase 5: `check_style.py --budgets revision_260925` (Results ≤ 13,500,
      conclusions ≤ 900, back matter ≤ 4,000, total ≤ 21,000; abstract cap kept at 300 and the
      abstract trimmed to 298). The rulebook words in Daniil's sentences were fixed in the drafts

### Phase 4 — review
Done 2026-09-25 together with the rule-15 density subphase; gate-4 packet
`workflow_runs/260924_run1/20_phase4_report.md`.
- [x] `tools/check_principles.py` — write it; the ten checks of §4, calling the skill's `stats`,
      `panels` and `citations` subcommands rather than reimplementing them — this machine's skill copy
      has only `citations` (and `numbering`), so A3/B1/B2 are implemented in the gate; `--docx` calls
      `citations`
- [x] style-editor — the density and table-budget pass: every overloaded sentence gets a named
      destination table and a tier — 64 sentences fixed in the drafts (split, or MADs routed to
      Supplementary File 1, sheet `Paired_tests`); `17_style_editor_report.md`
- [x] reference-verifier — re-resolve `11_citations_to_insert.md` from full text; **audit** the
      manuscript's own 46 + 4 citations for integrity without editing them — 20 confirmed, 4 with
      correction, 0 rejected; no drift; `18_references_verified.md`
- [x] Run the gates plus the antithesis grep; all exit 0. `check_overlap.py` against Article 1 only —
      assembler, `check_principles`, `audit_numbers`, `check_overlap` and the grep all pass;
      `check_style.py` passes since Phase 5, once the length re-baseline was applied. **All exit 0 on
      the final 260925 text** (RUN_REPORT §Final gates)

### Phase 5 — renumber and deliver
- [x] Recompute the figure order map from the finished text (do **not** reuse §B4) —
      `tools/renumber_260925.py` → `21_renumber_map.md`
- [x] Apply the map to the Markdown, the `.docx` and the Figma frame names, longest key first —
      placeholders in the text; Figma renamed by node id (0 geometry changes, snapshot
      `page2_after_renumber_260925.json`); recipe Figure 6 → 7, content untouched
- [x] Verify 0 citation-order inversions and 0 uncited panels (verification 5) —
      `check_principles.py`: `order` 0, `panels` 0
- [x] `tools/build_tracked_revision_260924.py` — build
      `manuscript/FL_metric_classes_F1000_260925.docx` with `safe_tracked_replace`, every anchor
      checked — 1,240 tracked changes, 0 edit problems (`22_docx_build_report.md`)
- [x] **Verify the citation invariants on the output: 46 content controls, 4 numeric brackets**
- [x] `nar_review_tools.py validate` — Accept All = revised, Reject All = the base, byte for byte —
      Accept All 160/160 and reject-Claude 183/183 paragraphs match; the stock validator's
      reject-all differs only where Claude deleted text inside one of Daniil's insertions,
      which Word discards with the insertion, so the builder checks Word's Reject All: identical
- [x] Count orphan citation-only paragraphs and report them for Daniil to clear in Word — 0
- [x] Rebuild the three supplementary workbooks — `A2_Supplementary_File_{1,2,3}_260925.xlsx`,
      `duplication_check_260925.md` (only the `Metric` join key repeats)
- [x] `workflow_runs/260924_run1/RUN_REPORT.md`, provenance table, open items, and the
      `11_citations_to_insert.md` hand-off
- [x] `CLAUDE.md` and `README.md` — the "Revision round 1" subsection (README §0)
- [x] Plan §8 — `workflows/article2_revision_260924.workflow.js`, a copy of the 260919 script;
      `node --check` passes
