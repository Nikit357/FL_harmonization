# Figma layout for the Article 2 frames — computed 2026-09-20

Every new frame goes on **Page 2 (`1013:2`)** at y = 11500, below the existing Extended
Figure block (lowest existing edge y = 11,149), on the plan's column grid. Frame width is
750 px throughout; panels are placed at 1:1 wherever they fit and scaled only to make a row
fit the 690 px content width.

Panel geometry is read from each PDF at 2 px = 1 pt, the convention the panels were exported
under. Coordinates are **relative to the frame**: padding 30 px, inter-panel gap 24 px, and
34 px reserved above each row for the panel letter (Inter Bold 20 pt). Every other label is
Inter 10 pt and must be a Figma TEXT node, never type baked into an imported SVG.

Panel letters follow the manuscript legends as they stand after the 2026-09-20 split, in
which Figure 4 keeps two `a2_p14` grids and Supplementary Figure 14 takes the other two.
Rows run in alphabetical panel order, and two panels share a row only when their letters are
adjacent.

Figure 6 (the recipe) is not in this table: it is drawn from the twelve SVG assets in
`figures/recipe_assets_260917/` rather than assembled from exported panels.

**Existing frames are renamed and nothing else.** Extended Figures 1–3 become Figures 1–3 and
Extended Figures 4–13 become Supplementary Figures 1–10, together with their title TEXT nodes.
No artwork is redrawn, moved or restyled, and the Page 2 geometry snapshot taken before and
after the session must differ only in those `name` fields.


## `Figure 4 - Biomarker expression and correlation (L, M)`

Frame at **(-8736, 11500)**, size **750 x 6229**.

| letter | panel | x | y | w | h | sx | sy |
|---|---|---|---|---|---|---|---|
| A | `a2_p14_expression_scatter_01_raw` | 30 | 64 | 690 | 1794 | 1.8158 | 1.8155 |
| B | `a2_p14_expression_scatter_13_fsmvn` | 30 | 1916 | 690 | 1826 | 1.8489 | 1.8479 |
| C | `a2_p1_rho_vs_margin` | 30 | 3800 | 417 | 363 | 2.0231 | 2.0263 |
| D | `a2_p2_margin_ranking` | 30 | 4221 | 690 | 451 | 1.8485 | 1.8562 |
| E | `a2_p3_agreement_specific` | 30 | 4730 | 395 | 375 | 2.0156 | 2.0304 |
| F | `a2_p7_strategy_imputation_method` | 30 | 5163 | 690 | 564 | 1.8800 | 1.8780 |
| G | `a2_p12_raw_to_harmonized` | 30 | 5785 | 478 | 414 | 2.0017 | 2.0074 |

## `Figure 5 - Prediction and election (N)`

Frame at **(-7827, 11500)**, size **750 x 2585**.

| letter | panel | x | y | w | h | sx | sy |
|---|---|---|---|---|---|---|---|
| A | `a2_p4_lobo_ranking` | 30 | 64 | 690 | 451 | 1.8485 | 1.8551 |
| B | `a2_p5_per_batch` | 30 | 573 | 690 | 349 | 1.7797 | 1.7884 |
| C | `a2_p6_singleclass_audit` | 30 | 980 | 403 | 363 | 2.0118 | 2.0265 |
| D | `a2_p8_generalizability_index` | 30 | 1401 | 690 | 475 | 1.8482 | 1.8460 |
| E | `a2_p9_cross_election_circos` | 30 | 1934 | 318 | 317 | 2.0008 | 1.9994 |
| F | `a2_p10_venn_supervenn` | 30 | 2309 | 426 | 246 | 1.3818 | 1.3847 |
| G | `a2_p13_election_sankey` | 480 | 2309 | 247 | 204 | 1.3798 | 1.3835 |

## `Supplementary Figure 11 - Marker panel QC`

Frame at **(-5894, 11500)**, size **750 x 1261**.

| letter | panel | x | y | w | h | sx | sy |
|---|---|---|---|---|---|---|---|
| A | `a2_p15_panel_coverage` | 30 | 64 | 384 | 436 | 1.4801 | 1.4840 |
| B | `a2_p16_qc_gate` | 438 | 64 | 288 | 357 | 1.4841 | 1.4840 |
| C | `a2_p17_rho_by_signature` | 30 | 558 | 690 | 673 | 1.9921 | 1.9877 |

## `Supplementary Figure 12 - Harshness by L, M, N`

Frame at **(-4860, 11500)**, size **750 x 356**.

| letter | panel | x | y | w | h | sx | sy |
|---|---|---|---|---|---|---|---|
| A | `a2_p11_harshness_lmn` | 30 | 64 | 690 | 262 | 1.8355 | 1.8483 |

## `Supplementary Figure 13 - Gene by method clustering`

Frame at **(-3826, 11500)**, size **750 x 1315**.

| letter | panel | x | y | w | h | sx | sy |
|---|---|---|---|---|---|---|---|
| A | `a2_p18_gene_method_clustermap` | 30 | 64 | 690 | 1221 | 1.7375 | 1.7389 |

## `Supplementary Figure 14 - Remaining expression scatters`

Frame at **(-2792, 11500)**, size **750 x 3768**.

| letter | panel | x | y | w | h | sx | sy |
|---|---|---|---|---|---|---|---|
| A | `a2_p14_expression_scatter_12_scanorama` | 30 | 64 | 690 | 1819 | 1.8414 | 1.8408 |
| B | `a2_p14_expression_scatter_29_combat_ref` | 30 | 1941 | 690 | 1797 | 1.8193 | 1.8186 |


## Editable text pass, 2026-09-20

Every panel listed above is now a `FRAME` at the same box, holding two children:

- **`artwork`** — the original panel `RECTANGLE`, keeping its node id, **locked**, filled with a
  300 dpi render of the panel with every `<text>` element removed.
- **`labels`** — a `FRAME` of Inter `TEXT` nodes, one per label, tick and annotation, imported from
  a text-only SVG whose `viewBox` is the panel's placed pixel box.

**The boxes in the tables above are unchanged**, which is why the overlay is pre-scaled offline
rather than rescaled in Figma. The layout rounded every box to whole pixels, so `sx` and `sy` differ
by up to 0.7 % (worst: `a2_p3_agreement_specific` and `a2_p6_singleclass_audit` at 1.0073), and
Figma's `rescale()` is uniform. `tools/split_panel_text_260920.py` applies `sx` to x and to font
size and `sy` to y independently, and resizes each artwork PNG to the box's exact aspect so
`scaleMode: "FILL"` crops nothing.

1,966 `TEXT` nodes across the 21 panels. `Figure 6 - Recipe` is not in this table and was already
fully vector. Procedure and pitfalls: `../tools/figma_editable_text_260920.md`.
