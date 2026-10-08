# 16 — Phase 3 report (gate 3), 2026-09-25

## Status

**The draft is assembled and passes the mechanical half of gate 3. Two items go to Phase 4 by
design:** the sentence-density pass (rule 15) and the section-length re-baseline.

- **Revised master:** `manuscript/FL_metric_classes_F1000_260925.md`.
- **Tracked-change edit list for Phase 5:** `03_revision_edits.json`.
- **Assembly:** `tools/assemble_draft_260925.py`.

Daniil's edited `.docx` and the 260924 master are untouched.

| check | result |
|---|---|
| Base paragraphs | 178: 55 kept, 79 edited, 44 deleted (the 43 paragraphs of the old Table 1 and superseded P160), 25 inserted |
| Mendeley citation tokens | **46 of 46**, each in its original paragraph and order; none added, moved or deleted |
| Numeric citations | `[38]` ×2, `[50,51]`, `[52]` — all present verbatim |
| Main-text tables | 4 of the 5 allowed (Table 1 harshness, Table 2 LOBO, Table 3 elected-set overlap, Table 4 E1 index) |
| `[STAT: …]` markers / open requests | **0 / 0** — 17 requests raised, all resolved (below) |
| Number audit (`audit_numbers.py`) | **every number traced** to `tables/` or `01_numbers.json` |
| Antithesis grep | clean |
| Paragraph ranges | no paragraph claimed by two writers |

## How the draft was produced

Three writers worked in parallel on disjoint ranges, from the brief `03_brief_common.md`:

| Writer | Range | Output |
|---|---|---|
| writer-reviewed | P0–P76 (minus legends) | `03a_draft_reviewed.md` |
| writer-unreviewed | P78–P148, P161–P177 | `03b_draft_unreviewed.md` |
| legend-writer | all figure legends and the Supplementary material | `08_legends.md` |

Two writers were stopped once by a usage limit and resumed. The unreviewed writer's request file
was reconstructed from its markers.

## Found and fixed during Phase 3 (before drafting)

- **The global metric class had silently lost all 7 PCReg metrics**: Supplementary File 3 spells
  them `PCReg_*`, while the class definition expects `pcr_*`.
  - Fixed on Daniil's decision; old and new values are in `15_pcreg_fix.md`.
  - The headline overlap is now local–composite, Jaccard 0.464 (71 shared); it was 0.333 (56).
  - Election figure regenerated and re-placed in Figma. `--stamp 260917` still reproduces the
    old tables.
- **C15** asked for an average-percentile file; none existed. It is now `A2_T15`
  (Supplementary File 1, sheet `Class_percentile_scores`).

## The statistics queue — 17 requests, all resolved

Phase 1 re-entry, appended to the same tables:

- **Tests:** A2_T10 rows T10-110 and T10-201…T10-215. A2_T10 now holds 345 tests.
- **New tables:**
  - A2_T3c, threshold sensitivity.
  - A2_T16, per-component PCA group means.
- **Evidence:** the `stat_requests` and `figures_and_records` sections of `01_numbers.json`.

**Eight requests overturned a claim in the draft, and the sentences were rewritten to match the
test.** These are worth Daniil's attention:

| Request | Claim in the draft | What the test shows |
|---|---|---|
| SR-U04 | The clustermap group's lower full-cut F1 shows disagreement with class N | Not significant: 0.629 vs 0.709, p = 0.97 |
| SR-R02 | Post-removal shifts batch PCReg only under Affymetrix-only | It rises under all 14 strategies (p ≤ 4.3 × 10⁻⁶ each); largest under Affymetrix-only, median 0.075 |
| SR-R07 | Affymetrix-only has the highest maximum expression | Not significant, p = 0.30. Only its SD is higher, p = 6.8 × 10⁻⁶ |
| SR-R08 | Low-harshness methods have the lowest biology PCReg in most strategies | 7 of 14 strategies, which is chance level (p = 0.25) |
| SR-R10 | 11_harmony has lower dispersion within FF-only and FFPE-only | Not significant, p = 0.32 and 0.15 |
| SR-R11 | Clustermap group vs rest | Batch LISI higher (p = 2.0 × 10⁻⁷); biology LISI indistinguishable (p = 0.80) |
| SR-U03 | Does the 5% threshold decide the overlaps? | No: local–composite is the largest pair at 2.5%, 5% and 10%; ρ = 0.801 and 0.881 against 5% |
| SR-U05 | The highest full-cut value belongs to the post1 variant | The post0 variant of the confounded approach is marginally higher; both are 0.958 at three decimals |

The remaining requests supplied values that were missing:

- **SR-U01:** 2.76 × 10⁸ and 1.46 × 10¹¹.
- **SR-U02:** 1,187 approaches pass every recipe step.
- **SR-L01:** 106, 0 and 102 of the 112 elected by L, M and N pass the gate.
- **SR-R03 to R06 and R09:** p-values and effect sizes.

## Left for Phase 4 (by plan design)

- **Sentence density (rule 15).** 63 sentences carry more than three numeric values or more than
  one p-value:
  - 43 in the reviewed range, several of them Daniil's own dataset and software sentences (P8,
    P16, P20, P21, P31);
  - 20 in the unreviewed range.

  The style-editor names a destination table for each.
- **Length.** Results grew from 7,088 to 12,681 words (+79%), against the plan's expected
  15–20%. The growth comes from the 31 newly cited panels, the moved fold finding and the tests.
  The abstract is 349 words, over the 300-word budget; the base was 321.
- **Style gate.** Six em-dashes, all "—" cells of Table 1 meaning "no fold cut". Two uses of
  "robust" and one of "highlight", all in Daniil's own sentences, which rule 11 keeps.

## Questions for Daniil (from the writers)

1. **Acknowledgements.** The ten former co-authors are no longer authors. Should any of them be
   thanked? The draft does not add them.
2. **Competing interests.** Employment by affiliation 2 is left as `[TO CONFIRM]`.
3. **Zenodo.** Record 22737294 must be published before submission; it is a draft deposit.
4. **Supplementary Figure 13** (`sfig_gene_method`, reused unchanged) includes 34_arsyn and
   38_harman, which are outside the 31-method analysis set.
5. **The Supplementary File 2 README of `Agreement_specific_61`** misdescribes the sheet. This is
   fixed when Phase 5 rebuilds the workbooks.
6. **Numbers kept from your reviewed text that have no A2 table behind them:**
   - P43 missing-value and scale numbers;
   - P40 tSNE dispersion 0.24 / 1.00;
   - P49 DSC ranges;
   - P50 softimpute 1.7–9.7 percentage points;
   - P58 82.0%;
   - P62 distance-ratio method means.

   They pass the audit because the values exist in the tables at some rounding, but no specific
   row was named as their source. Phase 4's reference-verifier re-derives them.
