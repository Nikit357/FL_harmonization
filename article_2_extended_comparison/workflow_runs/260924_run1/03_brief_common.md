# 03 — Common brief for the three Phase 3 writers, 2026-09-25

Working directory: `<repo>/article_2_extended_comparison`
(all paths below are relative to it). Python: `source ~/venvs/collagen_3_11/bin/activate`.

You are one of three writers revising the Article 2 manuscript (F1000Research) after Daniil's
review. The plan of record is `f1000_article2_revision_plan_260924.md` (read §B, §C, §W3 and
§1). Daniil approved it and Phases 0–2 are done.

## What to read first (in this order)

1. `manuscript/daniil_review_principles_260924.md` — **the standard**. Its §G checklist is
   binding on every paragraph you write.
2. `manuscript/daniil_comments_260924.md` — his 37 comments, each anchored to a span.
3. `workflow_runs/260924_run1/00_paragraph_index.md` — **the base text**, paragraph by
   paragraph (`P0`…`P177`), exactly as it stands in Daniil's edited `.docx`, with every
   Mendeley citation shown as a `⟦CIT:…⟧` token and the comments anchored in each paragraph.
   This is what you revise. Do not work from `manuscript/*.md`.
4. The evidence, **the only sources a number may come from**:
   - `workflow_runs/260924_run1/13_phase1_evidence_report.md` — what reproduces, what does
     not, which claims the statistics do not support. **Read it closely**; several base
     sentences are wrong and it says which.
   - `workflow_runs/260924_run1/15_pcreg_fix.md` — a bug fixed today: every global- and
     composite-class election number in the base text is stale (e.g. local–composite is now
     Jaccard 0.464, 71 shared, not 0.333, 56).
   - `workflow_runs/260924_run1/12_index_rank_churn.md` — the index changed (C16/E1).
   - `tables/A2_T*_260924.csv` — the result tables. `A2_T10_paired_tests` (285 tests, each
     with `claim_id`, the quoted base numbers and `quoted_reproduced`), `A2_T11_scatter_
     correlations`, `A2_T9_harshness_table1`, `A2_T9b_harshness_full`, `A2_T13_lobo_summary`,
     `A2_T3b_cross_election_pairs`, `A2_T14_dispersion`, `A2_T15_class_percentile_scores`,
     `A2_T12_metric_census`, `A2_T2b_generalizability_top_eligible`.
   - `workflow_runs/260924_run1/01_numbers.md` (and `.json`) — the evidence file.
   - `workflow_runs/260924_run1/09_metric_census.md` — 344 / 334 / 87.
5. The figures: `workflow_runs/260924_run1/07_panels.md` (every panel, letter and what it
   shows) and the images `figures/panels_260925/<name>.png` — look at them.
6. `workflow_runs/260924_run1/11_citations_to_insert.md` — proposed references. You do **not**
   insert them; you may name the test or package in prose.

## HARD RULES (binding; they override any instinct to be helpful)

1. **Provenance.** No number without a table, column and filter. Every number you write must
   be findable in `tables/` or `01_numbers.json` at the precision you write it. After each
   sentence that carries a new number, add an HTML comment naming the source, e.g.
   `<!-- src: A2_T10 T10-002 -->`. Phase 5 strips these.
2. **Never invent.** No number, reference, DOI, PMID, URL, author or result that you did not
   read in the sources above. Unknown → `[TO CONFIRM: what is missing]`.
3. **Daniil's wording wins** (rule 11). Where he rewrote a sentence, keep his sentence and
   extend it; correct only the §F defects of the principles document and statements the
   evidence report proves wrong. You are extending his prose, not re-editing it.
4. **Three significant digits** (rule 13): 0.7334 → 0.733, 1.0000 → 1.000, 0.0178 → 0.018.
   Counts, natural percentages and scientific-notation p-values are exempt. p-values: two
   significant digits, written `p = 1.4 × 10⁻⁹` (Unicode superscripts), `p = 0.048` above
   0.001, and `p < 10⁻³⁰⁰` for an underflowed zero. ρ written `ρ = 0.177`.
5. **Do not touch a citation** (rule 14). Carry every `⟦CIT:…⟧` token of a paragraph through
   **verbatim, in the same order, in the same paragraph**. Never add, delete, move or merge
   one. The plain numeric citations `[38]` (twice), `[50,51]` and `[52]` also stay verbatim.
   A new reference is never written into the text — not even as a placeholder.
6. **At most three numeric values and one test result per sentence** (rule 15). Beyond that,
   the numbers go to a table and the sentence keeps the qualitative result and its mechanism.
7. **Never write around a missing number** (rule 16). If a claim needs a statistic that is not
   in the tables, append a request to YOUR stat-request file (below), write `[STAT: SR-xxx]`
   in place of the value, and continue. Do not soften or delete the claim, do not estimate.
8. **At most five main-text tables** (rule 19). The slate is fixed (below); do not create a
   sixth. Larger enumerations go to a Supplementary File sheet and the text points at it.
9. **Language.** American spelling. No "rather than". No "X, not Y" antithesis. No aphorism,
   no sentence about the article itself (D4). Abbreviations defined at first use, then used
   (KNN, not k-nearest-neighbour). "Elected" only for the elected-set concept (D9). No
   proofless adjective ("robust", "novel", "comprehensive") without its justification.
10. **Paragraph discipline** (D1, D2): a Results paragraph opens with what was done; a Results
    sub-section closes with a "Taken together" paragraph stating the consequence for
    benchmarking practice.
11. **Write to disk incrementally**, with a `## Status` block at the top of your artifact that
    you update as you go (sections done, sections left, open stat requests). A half-finished
    file on disk is worth more than a complete one lost in context.

## How figures are cited — tokens for everything that changed in Phase 2

Final figure numbers are assigned in Phase 5 by order of first citation, so **new and
changed figures are cited by token**, `[FIG:<name>]` followed by the panel letter(s):
`[FIG:sfig_harshness]C`, `[FIG:fig_markers_lm]A, B`. Unchanged figures keep their current
numbers.

| token | what it is | replaces |
|---|---|---|
| `[FIG:fig_markers_lm]` | classes L, M; A–F | Figure 4. Old 4C → A (by method) and B (by strategy); old 4D → C; old 4F → D; old 4E → E; old 4G → F. Old 4A/4B are gone |
| `[FIG:fig_prediction_n]` | class N; A–D | Figure 5 A–D (same meaning; D is now on the E1 index) |
| `[FIG:fig_election]` | election structure; A chord, B Venn, C chunk plot, D funnel | old Figure 5E (→A), 5F (→B, C), 5G (→D) |
| `[FIG:sfig_harshness]` | harshness tiers, A–L | Supplementary Figure 12 |
| `[FIG:sfig_lmn_scatter]` | L/M/N scatterplots, A–F | new (C48) |
| `[FIG:sfig_metric_clustermap]` | metric cross-correlation clustermap | new (C48) |
| `[FIG:sfig_expression]` | expression, 4 linear + 4 non-linear methods, A–H | old Figure 4A/4B and Supplementary Figure 14 |
| `[FIG:sfig_pca]` | per-component PCA, A–D | new (C35); Figure 1C and Supplementary Figure 2F remain and may be cited once where they are first introduced |
| `[FIG:sfig_marker_qc]` | marker panel QC, A–C | Supplementary Figure 11 |
| `[FIG:sfig_gene_method]` | gene by method clustering | Supplementary Figure 13 |

Unchanged, cite as now: Figures 1, 2, 3, 6 and Supplementary Figures 1–10.

## Tables (main text: exactly these four; Table 5 is a reserve — do not use it)

| table | source | content |
|---|---|---|
| **Table 1** | `A2_T9` | L/M/N by method harshness tier: mean and median per tier, Kruskal–Wallis H and p, pairwise Mann–Whitney p (C45) |
| **Table 2** | `A2_T13` | LOBO summary for the named groups and the leading approaches, both fold cuts and both targets (C47). The base text's "Table 1" (leading approaches) becomes Table 2 |
| **Table 3** | `A2_T3` + counts from `A2_T3b` | elected-set overlap matrix, cells "Jaccard (n shared)" |
| **Table 4** | `A2_T2b` | E1 generalizability index, top 15 eligible approaches, six components |

## Supplementary Files (Article 2's own workbooks; Phase 5 builds them)

Cite as "Supplementary File 1, sheet <name>". Sheet names:

| file | sheet | source |
|---|---|---|
| Supplementary File 1 | `Metric_class_assignment` | `A2_T12` — resolves C14 |
| Supplementary File 1 | `Class_percentile_scores` | `A2_T15` — resolves C15 |
| Supplementary File 1 | `Paired_tests` | `A2_T10` |
| Supplementary File 1 | `Scatter_correlations` | `A2_T11` |
| Supplementary File 1 | `Harshness_full` | `A2_T9b` — the per-metric n of C46 |
| Supplementary File 1 | `Composite_dispersion` | `A2_T14` — C42, C43 |
| Supplementary File 1 | `Generalizability_ranking` | `A2_T2` (260924) |
| Supplementary File 1 | `Method_census_by_class` | `A2_T4` (existing sheet, now recomputed) |
| Supplementary File 1 | `PCA_component_means` | `A2_T16` (added in the Phase 3 re-entry) |
| Supplementary File 2 | `Cross_election_pairs` | `A2_T3b` |
| Supplementary File 2 | `LOBO_summary` | `A2_T13` |
| Supplementary File 2 | `Cross_election_matrix` | `A2_T3` (existing sheet) |
| Supplementary File 2 | `Threshold_sensitivity` | `A2_T3c` — overlaps at 2.5 / 5 / 10% (added in the Phase 3 re-entry) |

The existing sheet names already cited in the base text stay valid. "Supplementary File 2 of
the source benchmark" means Article 1's registry (`Metric_polarity`, 344 metrics).

## Output format (all three writers)

Your artifact is a Markdown file with one block per base paragraph in your range, in order:

```
### P35 [keep]

### P36 [edit]
<the full revised paragraph; inline Markdown for bold/italic only; ⟦CIT:…⟧ tokens verbatim>
<!-- why: C25, C26, A2; src: A2_T10 T10-001, T10-002 -->

### P36+1 [insert]
<a new paragraph inserted after P36>

### P37 [delete]
<!-- why: C47 superseded calculation -->
```

- `[keep]` carries no text. `[edit]` carries the complete new paragraph (not a diff).
  `[delete]` removes the paragraph. `[insert]` adds a new paragraph after the numbered one
  (`P36+1`, `P36+2`, …). A new table is an `[insert]` block holding a Markdown table with its
  caption line above it (`**Table 1. …**`).
- A paragraph that contains a `⟦CIT:…⟧` token may be `[edit]`ed but should not be
  `[delete]`d unless the evidence forces it; if you must, say so in the `why` comment.
- End the file with a `## Change log` table: paragraph, action, comments/principles served.

## Your stat-request file

If you need a number that is not in the tables, append to your own JSON list (the three
writers write separate files so none overwrites another):

```json
{ "id": "SR-R01", "requested_by": "writer-reviewed", "paragraph": "P44",
  "claim": "…", "needs": "test, column, groups", "destination": "small -> in text",
  "status": "open" }
```

Before requesting, **search `A2_T10` and `A2_T11` first** — 285 tests and 97 correlations
already exist, most claims of Results 1–7 are covered.
