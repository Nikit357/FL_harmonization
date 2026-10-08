# RUN REPORT — Article 2, revision round 1 (2026-09-24 to 2026-09-25)

## Status

**Delivered as a tracked-changes `.docx`; not yet cleared for submission.** Every gate exits 0 on
the final text. The items in "Open items" below are Daniil's decisions and block submission; none
of them is a wrong number.

- **Deliverable:** `manuscript/FL_metric_classes_F1000_260925.docx`, tracked against
  `manuscript/FL_metric_classes_F1000_260917_edited_Daniil.docx`. The base file was never modified.
  - Author of every new revision: "Claude (Article 2 revision 2026-09-25)".
  - 1,240 tracked changes: 86 paragraphs edited, 46 deleted, 27 inserted, 46 kept.
- **Markdown in step with it:** `manuscript/FL_metric_classes_F1000_260925.md`. This is what the
  gates read.
- **Plan of record:** `f1000_article2_revision_plan_260924.md`. Its TODO checklist is fully
  ticked except where it says otherwise.
- **Workflow script:** `workflows/article2_revision_260924.workflow.js`.
  - It is a copy of the 260919 script with the six-phase list, the new roles, rules 11–19 and the
    statistics-queue re-entry.
  - This round was **executed interactively**, one phase per request, with Daniil approving each
    gate. The script records that order so a rerun follows it. `node --check` passes.

## How it ran

| Phase | Request | Gate packet | Outcome |
|---|---|---|---|
| 0 Reconcile | "Phase 0 only" | `09_metric_census.md` | Census 344 / 334 / 87 reproduced; 46 Mendeley controls and 4 numeric brackets recorded as invariants; Markdown master `FL_metric_classes_F1000_260924.md` |
| 1 Evidence | "Phase 1 only" | `13_phase1_evidence_report.md` | E1 index, tables `A2_T0`–`A2_T16` (22 files stamped 260924), `01_numbers.json`, 24 citation proposals (`11_citations_to_insert.md`) |
| 2 Figures | "Phase 2 only" + Figma session | `07_panels.md`, `figures/figma_layout_260925.md` | 8 composite figures in `figures/panels_260925/` (pdf, svg, png); Figma Page 3 frames with editable Inter text |
| — PCReg fix | AskUserQuestion: "Fix and recompute" | `15_pcreg_fix.md` | `PCReg_*` → `pcr_*` on load; the global class grew back from 4 to its full size; every downstream table recomputed (pre-fix copies in `pre_pcreg_fix/`) |
| 3 Draft | "Phase 3 only" | `16_phase3_report.md` | Three writers on disjoint ranges; 17 statistics requests, all resolved, of which 8 overturned a draft claim and the sentence was corrected |
| 4 Review | "Phase 4 and the Rule-15 density subphase" | `20_phase4_report.md` | 64 overloaded sentences fixed; reference verification 20 confirmed, 4 with correction, 0 rejected |
| 5 Deliver | "Phase 5 and all remaining points" | `21_renumber_map.md`, `22_docx_build_report.md` | Renumbered, `.docx` built and verified, workbooks rebuilt, this report |

### Decisions Daniil took in this round

- **PCReg naming fix** (Phase 3): fix and recompute.
- **Length re-baseline** (Phase 5): the revision budgets `--budgets revision_260925`. Results may
  run to 13,500 words, conclusions to 900, back matter to 4,000, and the total to 21,000. The
  abstract cap stays at 300; it was trimmed to 298.
- **Software versions** (Phase 5): state the real installed versions. The Methods now reads Python
  3.11, pandas 2.3.3, numpy 1.26.4, scipy 1.17.1, scikit-learn 1.8.0, statsmodels 0.14.6,
  matplotlib 3.10.8, seaborn 0.13.2. These were checked against `~/venvs/collagen_3_11`, the
  environment every `A2_T*` table was computed in. Earlier it said scipy 1.12.0, scikit-learn
  1.3.2 and statsmodels 0.14.1.
- **P23 metric-class wording** (Phase 5): the source benchmark supports it, so the wording stays
  next to its `(Nikitin et al. 2026 Sep 17)` citation.
  - global = PCReg and DSC;
  - the cell-specific mixing score is named under local.

## Final gates (on `manuscript/FL_metric_classes_F1000_260925.md`)

| Gate | Command | Result |
|---|---|---|
| Principles (the ten checks) | `python tools/check_principles.py MS.md` | OK, 0 in every blocking check |
| Numbers | `python tools/audit_numbers.py MS.md --tables tables/ --evidence workflow_runs/260924_run1/01_numbers.json` | OK, every number traced |
| Overlap, Article 1 only (decision 3) | `python tools/check_overlap.py MS.md --against ../figures_for_article/FL_manuscript_versions/FL_harmonization_article_NAR_260912.docx --ngram 8` | OK, no 8-gram shared |
| Style and length | `python tools/check_style.py MS.md --journal f1000 --budgets revision_260925` | OK. Words per section: abstract 298, introduction 888, methods 1,503, results 12,982, conclusions 814, back matter 3,673 |
| Antithesis | `grep -nEi "rather than\|, not [a-z]+\.\|it is not .*, it is" MS.md` | nothing printed |
| Main-text tables | `TABLE_REGISTRY` assertion in `analysis/article2_generalizability.py` | 4 of at most 5 |

**Gate options matter.** Run without `--evidence`, `audit_numbers.py` misses the figure-derived
counts: 257, 325, 529, 1,187 and the Zenodo record number. Those live only in `01_numbers.json`.

Likewise, run without `--against`, `check_overlap.py` also compares against the extended document.
That document is Daniil's own and may be reused (rule 17). Both invocations above are the ones
the plan's verification block prescribes.

## The `.docx` contract (from `22_docx_build_report.md`)

- **Accept All = the revised text:** 160 of 160 paragraphs.
- **Rejecting Claude's revisions = Daniil's copy:** 183 of 183 paragraphs.
- **Word's Reject All** gives the same text for the output and for the base.
- **Citations untouched:**
  - Mendeley content controls: 46 of 46, contents identical.
  - After Accept All: `[38]` ×2, `[50,51]` ×1, `[52]` ×1.
- **Orphan citation-only paragraphs:** 0. **Edit problems:** 0.
- **Why the stock validator is not the reference here.** `nar_review_tools.py validate` treats a
  deletion nested inside one of Daniil's own insertions as a Reject-All mismatch. Word discards such
  a deletion together with the insertion, so the builder checks Reject All with Word's semantics
  instead. That check passes. `lxml` is available in this environment.
- **Not yet done:** nobody has opened the file in Word; LibreOffice is not installed on this
  machine. A visual pass in Word is the one remaining check (open item 9).

## Renumbering (from `21_renumber_map.md`)

The map was computed once from the finished text, by order of first citation. It was then applied
to the Markdown, the `.docx` and the Figma frame names.

- **Figures:**
  - the three new figures are 4 (`fig_markers_lm`), 5 (`fig_prediction_n`) and 6
    (`fig_election`);
  - the recipe figure becomes **Figure 7**. Only its name changed (node `1255:4`); its content was
    not touched.
- **Supplementary Figures:**
  - old 1–10 → 3, 6, 5, 7, 8, 4, 9, 10, 11, 12;
  - new ones: 1 (`sfig_marker_qc`), 2 (`sfig_pca`), 13 (`sfig_harshness`), 14 (`sfig_lmn_scatter`),
    15 (`sfig_metric_clustermap`), 16 (`sfig_expression`), 17 (`sfig_gene_method`);
  - 6 legends were moved into order and 11 stayed in place.
- **Tables:** Tables 3 and 4 swapped. Supplementary Files 1–3 unchanged.
- **Not renumbered:** references to Article 1's Supplementary Files ("… of the source benchmark").
- **Figma:**
  - Page 2 frames were renamed only (0 geometry changes); superseded frames are prefixed
    "[superseded 260925]".
  - Snapshots: `figures/figma_snapshots/page2_{before_revision,after_revision,after_renumber}_260925.json`.
  - Final labels: `figures/figma_layout_260925.md`, last section.

## Provenance — where each deliverable comes from

| Deliverable | Produced by | Inputs |
|---|---|---|
| `tables/A2_T0`–`A2_T16` (`_260924`) | `analysis/article2_generalizability.py` (default stamp 260924; `--stamp 260917` reproduces the old tables) | Supp. File 3 of Article 1 filtered to `pct_samples_allNA < 5` (2,234 rows after the Shambhala rename), `metrics_comprehensive_260905.csv`, `prediction_folds_long.csv` |
| `01_numbers.json` | `analysis/build_numbers_json.py --stamp 260924` | the tables above, statistics-request resolutions, figure-derived counts |
| `figures/panels_260925/*` | `figures/article2_figures_260925.py` | the tables above; `--prepare-expression` for the expression panels |
| Figma overlays, `figures/for_figma_upload/*` | `tools/split_figure_text_260925.py` | the panels above |
| `03a`, `03b`, `08` drafts | writer-reviewed, writer-unreviewed, legend-writer, then the style-editor | `00_paragraph_index.md`, `03_brief_common.md`, `01_numbers.json` |
| `03_revision_edits.json`, `FL_metric_classes_F1000_260925.md` | `tools/assemble_draft_260925.py` | the three drafts |
| `03_revision_edits_final.json`, `21_renumber_map.*` | `tools/renumber_260925.py` | `03_revision_edits.json` |
| `FL_metric_classes_F1000_260925.docx`, `22_docx_build_report.md` | `tools/build_tracked_revision_260924.py` | `03_revision_edits_final.json`, the base `.docx` |
| `supplementary/A2_Supplementary_File_{1,2,3}_260925.xlsx`, `duplication_check_260925.md` | `analysis/build_supplementary_workbooks.py --stamp 260924 --out-stamp 260925` | the tables above. The only duplication hit is the `Metric` join key |

Pipeline order for a rerun:

```bash
source ~/venvs/collagen_3_11/bin/activate
python analysis/article2_generalizability.py && python analysis/build_numbers_json.py
python figures/article2_figures_260925.py && python tools/split_figure_text_260925.py
python tools/assemble_draft_260925.py      # after any edit to 03a / 03b / 08
python tools/renumber_260925.py
python tools/build_tracked_revision_260924.py
python analysis/build_supplementary_workbooks.py --stamp 260924 --out-stamp 260925
```

## Hand-off — `11_citations_to_insert.md`

The citation freeze held: **no reference was inserted into the manuscript**. The proposal list is
Daniil's to insert through Mendeley.

- **24 proposals** (P-01 to P-24):
  - 22 for C20 (Methods, statistics and software);
  - 2 for C37 (the local-metrics sentence).
- **Verification** (`18_references_verified.md`): 20 CONFIRMED, 4 CONFIRMED WITH CORRECTION.
- **The four corrections:**
  - P-02 (Spearman): end page unverified.
  - P-05 (Wilcoxon 1945): end page unverified. It is now **required**, because the Methods uses
    the signed-rank test.
  - P-08 (Cox 1958): pp. 215–232.
  - P-23 (Luecken): 2022 issue, published online 2021.
- **Tests the Methods names with no proposal yet:** ε², Fisher's exact test, chi-square
  goodness-of-fit, binomial and hypergeometric tests (open item 7).

## Open items — for Daniil

| # | Item | Where |
|---|---|---|
| 1 | Acknowledgements and the employment wording for the two-author list | back matter, `[TO CONFIRM]` |
| 2 | Competing interests declaration | back matter, `[TO CONFIRM]` |
| 3 | **Publish Zenodo record 22737294** before submission; it is still a draft, so the DOI does not resolve yet | Data availability, `[TO CONFIRM]` |
| 4 | Supplementary Figure 17 (gene × method) includes `34_arsyn` and `38_harman`, two methods outside the 31. Keep, or drop the two rows | `sfig_gene_method` |
| 5 | Luecken's year: 2021 in the text, 2022 in reference [6]. Let Mendeley decide | Mendeley |
| 6 | Reference [38] appears both as a Mendeley field and, twice, as a plain `[38]`, which will not renumber on a Mendeley refresh. Kept verbatim per the freeze | Mendeley |
| 7 | References for ε², Fisher's exact, chi-square, binomial and hypergeometric tests — propose some, or leave them uncited as standard | Methods |
| 8 | C37: the proposed references support the class-count dependence for LISI and kBET, not for graph connectivity. Narrowing "local values" to "LISI and kBET values" would match them exactly | Results, local mixing |
| 9 | Open the `.docx` in Word and page through the tracked changes. LibreOffice is unavailable here, so no rendered check was possible | `FL_metric_classes_F1000_260925.docx` |
| 10 | The Figure 6 → 7 renaming of the recipe frame in Figma is a name change only; confirm it reads right on the canvas | Figma Page 2 |
