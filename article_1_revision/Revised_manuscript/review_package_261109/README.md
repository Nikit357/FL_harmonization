# Review package 261109 — NARGAB-2026-312 revision (all article materials)

Read `../../gates_review_261102.md` §13 first (what changed since 261108, open decisions).

| File | MB | What it is | Made by |
|---|---|---|---|
| `1_manuscript/FL_harmonization_article_NARGAB_tracked_stageB_261109.docx` | 24.1 | manuscript with tracked changes (Reject All = submitted text) | r50 --stage B |
| `1_manuscript/FL_harmonization_article_NARGAB_clean_261109.docx` | 24.07 | same manuscript, every change accepted | r47 |
| `2_response_letter/NARGAB-2026-312_response_to_reviewers_261109_DRAFT.docx` | 0.04 | response to the reviewers (DRAFT: [LINES] markers wait for Word line numbers) | r60 --draft |
| `3_main_tables/Main Tables 1-3 261109.docx` | 3.9 | Table 1; Table 2; Table 3 with titles (clean text) | r47 |
| `3_main_tables/Main Tables 1-3 261109.xlsx` | 0.01 | same tables, one sheet each | r47 |
| `4_main_figures/Revised main-figure panels (review draft) 261109.pdf` | 1.8 | revised main-figure panels (1E, 2A, 3, 4, 5, 6B–F), one panel per page | r46 |
| `5_supplementary_figures/Supplementary Figures S1-S18 (review draft) 261109.pdf` | 10.04 | Supplementary Figures S1–S18, new numbering, alt-text line per figure | r46 |
| `6_supplementary_files/Supplementary File 1.csv` | 0.02 | per-cohort sample table (88 cohorts) | r40 |
| `6_supplementary_files/Supplementary File 2.xlsx` | 0.55 | metric definitions, polarity, panel | r40 |
| `6_supplementary_files/Supplementary File 3.xlsx` | 2.57 | metrics of every approach; gradient and leave-cohort-out sheets | r40 |

Rebuild: `python r46_review_figure_pdfs.py --tag 261109 && python r47_build_review_package.py --tag 261109`
(from `article_1_revision/`). Figure files for Figma: `../../figures_svg/` (10 px text, frame-fitted;
check `python r97_figma_check.py`).
