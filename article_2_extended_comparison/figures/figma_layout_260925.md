# Figma layout for the revision-round figures — computed 2026-09-25

Every frame must fit the reference frame `637:93145`, **756 x 1159 px** (C50). 2 px = 1 pt. Each composite is one artwork + one `labels` overlay filling the frame; the re-laid figures place the 260920 panels at 1/1.5 of their old boxes. Final figure numbers are assigned in Phase 5, so the frames below are named by working name. Written by `tools/split_figure_text_260925.py`.

## `fig_markers_lm` — Figure 4 (classes L, M)

Frame **756 x 1132**, 176 TEXT nodes, smallest label 10.0 px.

| letter | panel | x | y | w | h |
|---|---|---|---|---|---|
| all | `fig_markers_lm` | 0 | 0 | 756 | 1132 |

## `fig_prediction_n` — Figure 5 (class N)

Frame **756 x 840**, 148 TEXT nodes, smallest label 10.0 px.

| letter | panel | x | y | w | h |
|---|---|---|---|---|---|
| all | `fig_prediction_n` | 0 | 0 | 756 | 840 |

## `fig_election` — new figure: election structure (old Figure 5E-G)

Frame **756 x 860**, 51 TEXT nodes, smallest label 10.0 px.

| letter | panel | x | y | w | h |
|---|---|---|---|---|---|
| all | `fig_election` | 0 | 0 | 756 | 860 |

## `sfig_harshness` — Supplementary Figure 12 (harshness), rebuilt

Frame **756 x 940**, 116 TEXT nodes, smallest label 10.0 px.

| letter | panel | x | y | w | h |
|---|---|---|---|---|---|
| all | `sfig_harshness` | 0 | 0 | 756 | 940 |

## `sfig_lmn_scatter` — new supplementary: L/M/N scatterplots

Frame **756 x 1080**, 151 TEXT nodes, smallest label 10.0 px.

| letter | panel | x | y | w | h |
|---|---|---|---|---|---|
| all | `sfig_lmn_scatter` | 0 | 0 | 756 | 1080 |

## `sfig_metric_clustermap` — new supplementary: metric cross-correlation clustermap

Frame **756 x 1040**, 35 TEXT nodes, smallest label 10.0 px.

| letter | panel | x | y | w | h |
|---|---|---|---|---|---|
| all | `sfig_metric_clustermap` | 0 | 0 | 756 | 1040 |

## `sfig_expression` — new supplementary: expression, linear vs non-linear (replaces Figure 4A/B and Supplementary Figure 14)

Frame **756 x 1144**, 162 TEXT nodes, smallest label 10.0 px.

| letter | panel | x | y | w | h |
|---|---|---|---|---|---|
| all | `sfig_expression` | 0 | 0 | 756 | 1144 |

## `sfig_pca` — new supplementary: per-component PCA (Figure 1C + Supp. Figure 2F)

Frame **756 x 1120**, 115 TEXT nodes, smallest label 10.0 px.

| letter | panel | x | y | w | h |
|---|---|---|---|---|---|
| all | `sfig_pca` | 0 | 0 | 756 | 1120 |

## `sfig_marker_qc` — Supplementary Figure 11 (marker panel QC), re-laid out

Frame **750 x 1076**, 288 TEXT nodes, smallest label 6.17 px.

| letter | panel | x | y | w | h |
|---|---|---|---|---|---|
| A | `a2_p15_panel_coverage` | 30 | 64 | 320 | 363 |
| B | `a2_p16_qc_gate` | 374 | 64 | 240 | 298 |
| C | `a2_p17_rho_by_signature` | 30 | 485 | 575 | 561 |

## `sfig_gene_method` — Supplementary Figure 13 (gene by method), re-laid out

Frame **750 x 908**, 49 TEXT nodes, smallest label 6.37 px.

| letter | panel | x | y | w | h |
|---|---|---|---|---|---|
| A | `a2_p18_gene_method_clustermap` | 30 | 64 | 460 | 814 |

## Placed in Figma, 2026-09-25

File `t8bFgusleBEwB9ht7rORCH`, **Page 3** (`1013:3`, empty before), frames in one row at y = 0, 150 px apart, a title TEXT node above each. Each panel is a `FRAME` holding a locked `artwork` rectangle (text-free 300 dpi image fill) and a `labels` frame of Inter TEXT nodes imported from `<panel>_text.svg`. Checked at placement: overlay within 1 px of its box, TEXT count equal to the SVG, every label Inter, every artwork an IMAGE fill. Page 2: 58 top-level nodes before and after, 0 geometry or child-count differences (`figma_snapshots/page2_{before,after}_revision_260925.json`).

| frame | Figma node |
|---|---|
| `fig_markers_lm` | `1321:3` |
| `fig_prediction_n` | `1321:7` |
| `fig_election` | `1321:11` |
| `sfig_harshness` | `1321:15` |
| `sfig_lmn_scatter` | `1321:19` |
| `sfig_metric_clustermap` | `1321:23` |
| `sfig_expression` | `1321:27` |
| `sfig_pca` | `1321:31` |
| `sfig_marker_qc` | `1321:35` |
| `sfig_gene_method` | `1321:46` |

## Final numbers after Phase 5 renumbering (2026-09-25)

The headings above use the working names of Phase 2. `tools/renumber_260925.py` numbered
everything by first citation in the finished text (`workflow_runs/260924_run1/21_renumber_map.md`),
and the Figma frames and their title TEXT nodes now carry these numbers.

| working name | final label |
|---|---|
| `fig_markers_lm` | Figure 4 |
| `fig_prediction_n` | Figure 5 |
| `fig_election` | Figure 6 |
| Recipe (old Figure 6, node `1255:4`, content untouched) | Figure 7 |
| `sfig_marker_qc` | Supplementary Figure 1 |
| `sfig_pca` | Supplementary Figure 2 |
| old Supplementary Figures 1, 2, 3, 4, 5, 6 | 3, 6, 5, 7, 8, 4 |
| old Supplementary Figures 7, 8, 9, 10 | 9, 10, 11, 12 |
| `sfig_harshness` | Supplementary Figure 13 |
| `sfig_lmn_scatter` | Supplementary Figure 14 |
| `sfig_metric_clustermap` | Supplementary Figure 15 |
| `sfig_expression` | Supplementary Figure 16 |
| `sfig_gene_method` | Supplementary Figure 17 |
