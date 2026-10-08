# 20 — Phase 4 report (gate 4), 2026-09-25

## Status

**Phase 4 and the rule-15 density subphase are done.** Every gate passes except `check_style.py`.
Its remaining failures are:

- the section word budgets, excluded from this run by Daniil (the "length re-baseline" subphase);
- three words the rulebook flags inside Daniil's own sentences, which rule 11 keeps.

| gate | result |
|---|---|
| `tools/assemble_draft_260925.py` | exit 0 — 46 of 46 citation tokens in place, no paragraph claimed twice |
| `tools/check_principles.py` (new, the ten checks of plan §4) | **OK**. Decimals, spelling, citations, antithesis, scatter, panels, density, tables and markers: all 0. `order` has 1 (report-only until Phase 5 renumbers) |
| `tools/audit_numbers.py` | **OK** — 660 distinct numbers, all sourced |
| `tools/check_overlap.py` against Article 1 only (decision 3) | **OK** — no 8-gram shared |
| antithesis grep | clean |
| `tools/check_style.py --journal f1000` | FAIL, not in scope — see below |

Manuscript: `manuscript/FL_metric_classes_F1000_260925.md`, reassembled from the edited drafts.
Tracked-change edit list for Phase 5: `03_revision_edits.json`.

## What was done

1. **`tools/check_principles.py`** (new). This machine's copy of the scientific-review skill has
   no `stats` or `panels` subcommands, although the plan assumed them. A3, B1 and B2 are therefore
   implemented here, and `--docx` calls the skill's `citations` subcommand. The citation invariant
   is read from `03_revision_edits.json`, where Mendeley fields keep their tokens.
   - **Two rules were corrected after first use** so they measure what the principle means:
     - The decimal rule no longer flags DOIs, stated thresholds ("exceeded 0.9999") or
       permutation p-values.
     - The sentence splitter now also breaks before a digit or a method name. A sentence starting
       "10 of the 14…" had been merged into the one before it.
2. **Rule-15 density pass** by the style-editor (`17_style_editor_report.md`).
   - All 64 overloaded sentences fixed:
     - most were split;
     - dispersions (MAD) in P36–P42 were routed to Supplementary File 1, sheet `Paired_tests`;
     - Daniil's design sentences were split minimally.
   - No test was dropped, no number added, and no fifth main table created.
   - Three further fixes:
     - "grey" → "gray" three times;
     - the uncited panels `[FIG:fig_markers_lm]F` and `[FIG:sfig_marker_qc]A, C` are now cited;
     - Table 1's "—" cells are now "n/a".
3. **Figure 4F sentence corrected.** The style-editor had written it from the rendered panel: "raised
   the median … in every harshness tier". The data says the high tier's median gain is 0.000.
   - Two tests were added: A2_T10 T10-216, Kruskal–Wallis p = 1.1 × 10⁻²⁹; and T10-217-1…3,
     Fisher's exact test.
   - The sentence now reads: gain 0.113 (low tier), 0.110 (medium), unchanged (high). The high
     tier holds 100 of its 685 approaches losing more than 0.1, the low tier none.
4. **Overlap with Article 1.** Two genuine 8-gram overlaps were reworded:
   - the Methods cohort sentence;
   - the Supplementary Figure 10 legend.

   The two affiliation addresses were added to `tools/overlap_allow.txt`: legal addresses,
   identical by necessity, tokenised as "1institute" and "2<affiliation>".
5. **Reference-verifier** (`18_references_verified.md`).
   - Of the 24 citation proposals: 20 CONFIRMED, 4 CONFIRMED WITH CORRECTION, 0 NOT CONFIRMED.
     - Cox 1958 is pp. 215–232; the paper plus its discussion runs to 242.
     - Luecken is dated 2022, published online 2021.
     - Spearman's and Wilcoxon's end pages could not be verified.
     - Wilcoxon 1945 is now required, because the Methods uses the signed-rank test.
   - Citation integrity: 46 of 46 tokens, same order as the base `.docx` fields; `[38]` ×2,
     `[50,51]` and `[52]` present. **No drift.**
6. **Numbers kept from Daniil's reviewed text.** All re-derived and reproduced
   (`19_reviewed_numbers_rederived.md`).

## Questions for Daniil

1. **Software versions in Methods do not match the environment the Article 2 tables were computed
   in.** Methods says scipy 1.12.0, scikit-learn 1.3.2, statsmodels 0.14.1. `collagen_3_11` runs
   scipy **1.17.1**, scikit-learn **1.8.0** and statsmodels **0.14.6**; Python 3.11.15, pandas
   2.3.3, numpy 1.26.4, matplotlib 3.10.8 and seaborn 0.13.2 match. "1.12.0" is the pin in the root
   `CLAUDE.md`, not what is installed. The L/M/N metrics were computed on the metrics pod, whose
   environment I cannot see. Which versions should the sentence state, and should it name both
   environments? Left unchanged.
2. **P23 (Methods, metric classes).** The `(Nikitin et al. 2026 Sep 17)` citation now sits on a
   class description that changed in substance:
   - global = PCReg and DSC, after the PCReg fix;
   - per-component R² and variance explained are no longer listed as global scoring metrics;
   - the cell-specific mixing score is named under local.

   Does the source benchmark support that wording?
3. **Reference [38]** is cited both as the Mendeley field `(Nikitin et al. 2026 Sep 17)` and, in two
   places, as the plain `[38]`, which will not renumber on a Mendeley refresh. Kept verbatim per
   the citation freeze.
4. **Luecken's year:** 2021 in the text, 2022 in reference [6]. Decide in Mendeley.
5. **C37:** the proposed references support the class-count dependence for LISI and kBET, not for
   graph connectivity. Narrowing "local values" to "LISI and kBET values" would match them exactly.
6. **Tests with no proposed reference:** the Methods now also names ε², Fisher's exact,
   chi-square goodness-of-fit, binomial and hypergeometric tests. Should references be proposed?
7. **Not in scope of this run.** The section budgets of `check_style.py`: abstract 351 of 300,
   Results 12,873 of 7,425, total 20,157 of 20,000. Also the three rulebook words in Daniil's
   sentences: "robust" twice, "highlight", and "significantly" in a p-backed sentence.
