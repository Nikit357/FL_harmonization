# What this folder does not contain, and why

This folder is the public external material for Article 2 (F1000Research). It is a one-way,
sanitized copy of the authors' working folder, regenerated on every revision. Everything in the
working folder is here **except** what is listed below. No list in this file names a sample.

Fifteen of the 88 cohorts in the benchmark are proprietary or under controlled access (see
`../DATA_AVAILABILITY.md`). Their **names** and their **per-approach and per-batch metrics** appear
throughout `tables/`, `supplementary/` and the figures. Their **samples and expression values**
appear nowhere.

## Withheld files

| What | Count | Why |
|---|---:|---|
| Manuscript Word and PDF files (`manuscript/*.docx`, `manuscript/*.pdf`) | 9 | Drafts with tracked changes and reviewer comments. The published article is the text of record; the Markdown twins of the drafts are here |
| Extended-document Word snapshots (`manuscript_versions/*.docx`) | 4 | Same reason. The audit of these snapshots (`manuscript_versions/*.md`) is here |
| Vector versions of the per-sample expression scatters (`figures/panels_260917/a2_p14_expression_scatter_*.{svg,pdf}` and their `editable_260920/*_artwork.svg`) | 12 | Their point coordinates are per-sample expression values, including proprietary cohorts. The `.png` renders of the same panels are here |
| The literature cache (`tools/cache/`) | 93 | Third-party full texts. `tools/fetch_literature.py` rebuilds it |
| One workflow template and one style-rule file it produced | 2 | Internal drafting material unrelated to this study. `tools/check_style.py` carries the rules the article was checked against |

## Rows removed from one table

`figures/panels_260925/data/sfig_expression_long_260925.csv.gz` is the per-sample expression
table behind Supplementary Figure 16 (three genes, eight methods). Rows from the 15 proprietary
or controlled-access cohorts have been removed: **124,272 of 172,176 rows are
here** (47,904 removed).

Consequence: `figures/article2_figures_260925.py` plots the four largest cohorts in this table.
Re-run on the public copy, it draws the four largest **open** cohorts, not the four in the
published panel. The published panel itself is here as an image
(`figures/panels_260925/sfig_expression.*`, rasterized at render time, and
`figures/final_figures_files/Supplementary Figure 16.pdf`).

## Text replaced in the Markdown drafts and run records

Author affiliation, funding and competing-interest statements in the Markdown drafts and the
workflow run records are replaced by a pointer such as
`[Competing-interests statement: as in the published article.]`. Absolute paths on the
authors' machines are replaced by `<repo>` or `<projects>`. No number, table value, method name
or result was changed.

## Reproducing the tables

Everything under `tables/` regenerates from files that are in this repository:

```bash
cd article_2_extended_comparison
python analysis/article2_generalizability.py --date-tag 260905 \
       --out-dir <scratch> --run-dir <scratch>
```

The 22 `A2_*_260924.csv` outputs match the deposited tables to floating-point precision:
13 are byte-identical, and in the other 9 the largest absolute difference is 4.8e-5
(`A2_T15_class_percentile_scores`; 1e-8 or less everywhere else), from the numerical
libraries of the machine the deposited tables were built on. No text value differs.
(The script ends with a rank-churn comparison against the `_260917` tables; copy
`tables/*_260917.csv` into the scratch folder first, or that last step stops.)
