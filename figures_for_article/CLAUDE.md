# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This directory contains `Introductory_figures_for_article.ipynb` — the single notebook for all introductory dissertation figures (dataset overview, batch landscape, cohort composition). Figures go into `figures/` (created by the notebook on first run). `plots/` is a legacy scratch directory.

This directory and its notebooks are for the final high quality figures for the FL project articles.

## Directory layout (reorganized 2026-08-23)

Manuscripts and standalone scripts used to live flat in this directory; they are now split
into three places. **All commands and paths below assume the working directory is
`figures_for_article/` itself** — every script resolves its own sibling data (`figures/`,
`current_figures_tables_for_article_*/`, `supplementary_260802/`, etc.) relative to that root,
not relative to its own subfolder, so invoke them as `python edit_python_scripts/foo.py` /
`python figure_drawing_scripts/foo.py` from here rather than `cd`-ing into the subfolder first.

| Folder | Contents |
|---|---|
| `FL_manuscript_versions/` | Every `.docx` manuscript snapshot (`FL_harmonization_article*.docx`, NAR passes, suggestions/reviewed copies). `Harmonization_metrics_extended*.docx` stayed at the repo root — those are a separate document line, not a manuscript version. |
| `edit_python_scripts/` | The `apply_*_edits_*.py` tracked-change scripts (NAR review passes, abbreviation pass, table-move pass) plus `build_supp_file2_260802.py`. Read the manuscript-review section below before touching these. |
| `figure_drawing_scripts/` | Standalone figure/data scripts: `figures_helpers.py` (shared data-prep module), `pipeline_scheme_figure.py`, `fig10_metric_star_visualization.py`, `graphical_abstract_assets.py`, `graphical_abstract_pdfs.py`, `recompute_extended_metrics_260802.py`. |

Both `edit_python_scripts/` and `figure_drawing_scripts/` scripts that import a sibling module
(`figures_helpers`, `graphical_abstract_assets`) rely on Python auto-adding the executed
script's own directory to `sys.path`, which works unchanged after the move since the sibling
modules moved together. What did **not** move automatically: any script that located a
`.docx` or a sibling top-level folder (`supplementary_260802/`, `harmonization-metrics/`) via
`Path(__file__).parent` now needs one extra `.parent` hop, or an explicit
`.parent / "FL_manuscript_versions"` — already applied to every script that needed it as part
of the 2026-08-23 move; if you add a new `apply_*_edits_*.py` or figure script, follow the same
pattern rather than assuming `HERE` is still `figures_for_article/`.

## Environment

```bash
source ~/venvs/collagen_3_11/bin/activate
jupyter lab

# Run a standalone figure script (from figures_for_article/, not from inside the subfolder)
python figure_drawing_scripts/pipeline_scheme_figure.py
python figure_drawing_scripts/fig10_metric_star_visualization.py

# Apply a tracked-change manuscript edit pass (also from figures_for_article/)
python edit_python_scripts/apply_nar_review_edits_260802.py
```

All data is loaded live from S3 (`$FL_S3_BUCKET` bucket). No local data files exist. AWS credentials must be available in the session.

## Notebook structure

**Setup section (cells 0–8):** imports → palettes → S3 data load → `Platform_group` derivation.  
**Introductory figures section (cells 9+):** one `##` subsection per figure.

Data objects created in Setup and reused throughout:

| Variable | Shape | Source S3 key |
|---|---|---|
| `comb_exp` | 7174 × 3447 | `FL_batch_correction/exp/S0_no_removal__strict__01_raw__post0.tsv.gz` |
| `comb_ann` | 7174 × 485 | `FL_batch_correction/prepared/S0_no_removal__knn__ann.tsv.gz` |

`comb_ann` gains `Platform_group` in cell 7 via `batch_to_plaform_group` dict (cell 8).

## Canonical palettes (defined once in cell 3, used everywhere)

- `lymphoma_ontogeny_palette` — per cell type / diagnosis, Temperature-Split (Normal = cold/blue, Cancer = warm/red)
- `rna_batch_palette` — per RNA_BATCH (29 entries)
- `platform_palette` — per PLATFORM_RNA / GPL code
- `batch_to_plaform_group` — maps RNA_BATCH → one of four Platform_group strings

Never redefine these elsewhere in the notebook. Import from cell 3's namespace.

## Figure output conventions

```python
from pathlib import Path
FIGURES_DIR = Path("figures")
FIGURES_DIR.mkdir(exist_ok=True)
GLOBAL_FONT_SIZE = 10  # all text in all plots — fixed for Figma alignment

fig.savefig(FIGURES_DIR / "my_figure.svg", bbox_inches="tight")
fig.savefig(FIGURES_DIR / "my_figure.png", bbox_inches="tight", dpi=200)
```

- Always save **both** SVG (vector, for Figma/Illustrator) and PNG (dpi=200, for quick review)
- `GLOBAL_FONT_SIZE = 10` must be used for all `fontsize=` arguments — no hard-coded font sizes

### Graphical Abstract exceptions (do NOT "fix" these back)

The NAR graphical abstract is governed by author-guideline §6.9, which overrides three of
the conventions above. `graphical_abstract_assets.py` departs from them deliberately:

| Convention | GA override | Why |
|---|---|---|
| `GLOBAL_FONT_SIZE = 10` | **12 pt floor** (`GA_FONT_PT = 12`) | §6.9 requires 12–16 pt. **10 pt is illegal in a graphical abstract.** |
| matplotlib default font | **Liberation Sans** | §6.6 wants Arial/Helvetica. Neither is installed; Liberation Sans is the Arial-metric substitute. Figma has no Arial either — use **Arimo** there, the same metric-compatible lineage. |
| PNG at `dpi=200` | **`dpi=600`** | The mosaic PNG is what gets placed in Figma and must clear 600 dpi at ~35 mm final width (§6.3). |

Two further GA-specific rules:

- **All text lives in Figma, never in the assets.** Generated SVG/PNG assets contain
  artwork only. This keeps the Figma acceptance audit authoritative — it can verify every
  character that appears in the figure, which is impossible for type baked into an SVG.
  *This rule applies to `graphical_abstract_assets.py` only.* The composed PDFs from
  `graphical_abstract_pdfs.py` deliberately carry their own type — there is no Figma audit
  to preserve, and `_report_text_fit()` plays the same role locally.
- **Never use `imshow` for the tile mosaic.** It embeds a raster at the grid's native
  47 × 48 px, about 34 dpi at final size. Use explicit `Rectangle` patches in a
  `PatchCollection` instead (2,239 vector paths, zero embedded images).

### Composing a graphical abstract as PDF (`graphical_abstract_pdfs.py`)

The PDF route exists because the Figma MCP tool-call quota blocked on-canvas assembly.
It turns out to be the better route, and is now the primary one:

- **Points are points.** The page is 5.000 × 2.000 in = 360 pt wide, so `fontsize=12`
  *is* 12 pt on paper. The §6.9 type rule is expressed directly, with none of the
  `0.4768 pt per px` arithmetic the Figma route needs.
- **Never estimate text width from character counts.** Liberation Sans is materially
  narrower than a 0.5 em-per-character guess. `_report_text_fit()` measures the rendered
  extent of every string against its zone budget and exits non-zero on overflow. It also
  asserts the per-variant text-item budget (A = 8, B = 7, C = 6).
- **Set white explicitly** on both `fig.patch` and `savefig(facecolor=...)`. A
  transparent PDF background can render black in print pipelines — the exact defect the
  v1 Figma frame had (`fills` was `[]`).
- **Horizontal text does not fit a curved band** except near the top of the arc. Labels
  for sectors at the horizontal ends must go outside the arc (`FAN_R_LABEL > 1`).
- Artwork drawers live in `graphical_abstract_assets.py` as `draw_*(ax, ...)` functions
  and are shared by both routes. Add new artwork there, not here.

Embedding coordinates are cached in `figures/ga/_embedding_cache/*.npz`. A palette or
label fix re-renders from cache; without it, recolouring re-downloads ~2.9 GB from S3.

**Diagnosis grouping gotcha:** never collapse `Diagnosis_cell_type_unified` with
substring matching. The literal value is `Diffuse_Large_B_Cell_Lymphoma`, so a test for
`"_b_"` intended to catch normal B cells silently reclassifies all 4,466 DLBCL samples as
normal. Match exact names plus the `TUMOR_NORMAL` flag. `Major_group` is not a clean
biological grouping — it mixes disease names with cohort sources (`Normal_B_cells`, `Kassandra`).

## Plot rcParams (set globally in cell 0)

```python
plt.rcParams["pdf.fonttype"] = "truetype"
plt.rcParams["svg.fonttype"] = "none"   # text stays editable in Figma
plt.rcParams["figure.dpi"] = 200
sns.set_style("ticks")
```

Do not override these per-figure.

## Article

**Manuscript:** `FL_manuscript_versions/FL_harmonization_article.docx` (ComboBatch pipeline; MNN and SVA top methods)  
**Article status tracking:** `implementation_plans_old/article_figures_status_260625.md` — read this before starting any new figure.  
**Notebook reference:** `implementation_plans_old/notebooks_for_figures_260625.md` — detailed description of all three figure notebooks (data objects, palettes, helpers, figure inventories).

## Implemented figures (in `figures/`)

| Article figure | File(s) | Implementation | Status |
|---|---|---|---|
| Fig 1A — batches bubble chart | `comb_ann_platform_groups_bubble_chart.svg/png` | `Introductory_figures_for_article.ipynb` cells 12–17 | **Done** |
| Fig 1B — biology bubble chart | `comb_ann_biology_bubble_chart.svg/png` | `Introductory_figures_for_article.ipynb` cells 12–17 | **Done** |
| Fig 1C — pipeline scheme | `pipeline_scheme.svg/png` | `figure_drawing_scripts/pipeline_scheme_figure.py` | **Done** |
| Fig 1D — batches × diagnosis barplot | `barplot_diagnoses_by_batches.svg` | `Introductory_figures_for_article.ipynb` | **Done** |
| Fig 2A — strategies Circos-Sankey | `circos_sankey_strategies.svg/png` | `Introductory_figures_for_article.ipynb` | **Done** |
| Supp — barplot batches × cohorts | `barplot_batches_by_cohorts.svg` | `Introductory_figures_for_article.ipynb` | **Done** |
| Supp — barplot diagnoses × cohorts | `barplot_diagnoses_by_cohorts.svg` | `Introductory_figures_for_article.ipynb` | **Done** |
| Fig 7 — Local Neighborhood Metrics | `fig7_local_metrics_neighborhood.svg/png` | `Finally_assembled_figures_for_article.ipynb` | **Done** |
| Fig 8 — Structural and Distance Metrics | `fig8_structural_distance_metrics.svg/png` | `Finally_assembled_figures_for_article.ipynb` | **Done** |
| Fig 8B — Distributional Similarity + NA | `fig8b_distributional_similarity_na_retention.svg/png` | `Finally_assembled_figures_for_article.ipynb` | **Done** |
| Fig 9 — Cross-Metric Correlation + Factor Importance | `fig9_cross_metric_correlation_factor_importance.svg/png` | `Finally_assembled_figures_for_article.ipynb` | **Done (run to produce)** |
| Fig 10 — Composite Ranking + Best Profiles | `fig10_composite_ranking_best_profiles.svg/png` | `Finally_assembled_figures_for_article.ipynb` | **Done (run to produce)** |
| Fig 10 star — Metric Group Superiority Star | `fig10_metric_star_best15.svg/png` | `figure_drawing_scripts/fig10_metric_star_visualization.py` | **Done (run standalone)** |
| Supp 9 — Embeddings placeholder | `supplementary/supp9_embeddings_best_stars.svg/png` | `Finally_assembled_figures_for_article.ipynb` | **Done (placeholder)** |
| Supp A — NA genes per batch | `supplementary/suppA_na_genes_per_batch.svg/png` | `Finally_assembled_figures_for_article.ipynb` | **Done (requires Cell 3)** |
| Supp B — Imputation gene overlap Sankey | `supplementary/suppB_imputation_gene_overlap_sankey.svg/png` | `Finally_assembled_figures_for_article.ipynb` | **Done (requires Cell 3)** |
| Supp C — Gene retention analysis | `supplementary/suppC_gene_retention_analysis.svg/png` | `Finally_assembled_figures_for_article.ipynb` | **Done (Panel B/C require gene_sets; Panel C has gseapy.enrichr() stub)** |
| Supp D — Group B detail catplots | `supplementary/suppD_group_b_detail_kbet_asw_cms.svg/png` | `Finally_assembled_figures_for_article.ipynb` | **Done (run to produce)** |
| Supp E — Group C centroid dispersion | `supplementary/suppE_group_c_centroid_dispersion.svg/png` | `Finally_assembled_figures_for_article.ipynb` | **Done (run to produce)** |
| Supp F — Group H Euclidean distance | `supplementary/suppF_group_h_euclidean_distance.svg/png` | `Finally_assembled_figures_for_article.ipynb` | **Done (run to produce)** |
| Supp G — Group G graph connectivity | `supplementary/suppG_group_g_graph_connectivity.svg/png` | `Finally_assembled_figures_for_article.ipynb` | **Done (run to produce)** |
| Fig 11 — decision tree | `fig11_decision_tree_harmonization_selection.svg/png` | `Finally_assembled_figures_for_article.ipynb` | **Done (emoji icons added 2026-06-27)** |
| Supp 7s — UMAP entropy | `supplementary/supp7s_umap_entropy.svg/png` | `Finally_assembled_figures_for_article.ipynb` cell `umap_entropy_supp` | **Done (requires run)** |
| **Graphical Abstract** (NAR, mandatory) | `graphical_abstract_variant{A,B,C}_*.pdf/png` — 3 complete candidates, 127 × 50.8 mm | `figure_drawing_scripts/graphical_abstract_pdfs.py` | **Done — awaiting Daniil's choice of variant** |
| Graphical Abstract — artwork assets | `figures/ga/` — 12 assets + 9 cached embeddings | `figure_drawing_scripts/graphical_abstract_assets.py` | **Done** (also the shared `draw_*(ax)` library for the PDFs) |

## Figures yet to be implemented (BLOCK 4)

| Article figure | Plan / notes | Priority |
|---|---|---|
| Fig 3 — harmonization clustermap | 2,234 attempts × 87 metrics; polarity-normalized; column annotations; seaborn; new `Harmonization_clustermap_figure.ipynb` | **Highest** |
| Fig 1 multipanel assembly | Compose panels 1A–1D into one publication SVG | **Medium** |
| Supp A2 — NA samples per strategy | barplot; new cell after Supp A in `Finally_assembled_figures_for_article.ipynb` | **Low** |

## Implementation plan files

| Plan file | Figure | Status |
|---|---|---|
| `implementation_plans_old/bubble_chart_plan_260531.md` | Bubble charts (Fig 1A/B) | Done |
| `pipeline_scheme_figure_plan_260604.md` | Pipeline scheme (Fig 1C) | Done |
| `implementation_plans_old/article_figures_status_260625.md` | Full article + all figures status | Current reference |
| `finally_assembled_figures_plan_260626.md` | Full plan: Figs 7–11 + Supp A–G in 4 blocks | BLOCK 1,2,3 done; BLOCK 4 pending |
| `figma_review_260731.md` | Review of the v1 graphical abstract in Figma (4 findings) | Superseded by the plan below |
| `graphical_abstract_redesign_plan_260731.md` | GA redesign: 3 candidate variants, NAR §6.9 compliance, implementation status | All 3 variants delivered as PDFs |

When implementing a new figure, write a `*_plan_*.md` file first with exact function signatures, data sources, layout, and a TODO checklist. Then implement. Read `implementation_plans_old/article_figures_status_260625.md` for detailed specs of each pending figure.

---

## Manuscript review and tracked-change edits

**Invoke the `nar-review` skill first** (`.claude/skills/nar-review/SKILL.md`) — it is the full
procedure (measure-don't-read workflow, issue taxonomy, severity rubric, validation gates) plus a
findings archive for the 260727 pass. Its tool module is `.claude/skills/nar_review_tools.py`,
which stays in the `skills/` root rather than inside the skill directory, because the edit scripts
below import it from there:

```bash
S=~/FL_harmonization/.claude/skills/nar_review_tools.py
python $S extract MS.docx out.txt   # body dump: indices, styles, italic markers, revisions
python $S docx    MS.docx           # template compliance, abstract words, spelling variants
python $S fields  MS.docx           # how citations are stored — RUN BEFORE ANY EDIT
python $S figures FIGDIR/           # size, legibility at print size, fonts, colour space
python $S figtext FIGDIR/ --grep X  # which figure contains which label
python $S validate SRC.docx DST.docx
```

| File | Purpose |
|---|---|
| `NAR_review_260727.md` | Full referee-style review of `FL_manuscript_versions/FL_harmonization_article_NAR.docx` (12 critical / 34 major / 61 minor + statistics verdict + figure and NAR-compliance audit) |
| `edit_python_scripts/apply_nar_review_edits_260727.py` | Applies that review to the manuscript as Word tracked changes → `FL_manuscript_versions/FL_harmonization_article_NAR_260727.docx`. Reference implementation for the edit-script pattern. |
| `edit_python_scripts/apply_nar_abbrev_edits_260728.py` | Second pass on Daniil's partly-revised copy: renames the metric PCR → **PCReg** (22 occurrences) and defines AUC, tSNE, UMAP, PC, PCA, GEO, PBMCs, AWS, cLISI, iLISI, TPM, DSC, FSQN, QN at first use → `FL_manuscript_versions/FL_harmonization_article_NAR_260728.docx`. Reference implementation for editing a document that **already** carries revisions. |
| `NAR_review_260802.md` | Third referee pass (5 critical / 13 major / 47 minor). Every headline number now reproduces exactly from the deposited data — see its §0 table. |
| `edit_python_scripts/apply_nar_review_edits_260802.py` | Applies that review → `FL_manuscript_versions/FL_harmonization_article_NAR_260802.docx`. Reference implementation for **adding tracked table columns** (`append_tracked_column`). |
| `edit_python_scripts/apply_extended_metrics_edits_260802.py` | ~~Language, numbers and figure renumbering for `Harmonization_metrics_extended.docx`~~ **Superseded — do not run.** Four of its "corrections" were wrong (it used a 2,150-row subset) and its figure sweep corrupted `Supplementary Figure 6`. |
| `edit_python_scripts/apply_extended_metrics_edits_v2_260802.py` | The full pass on `Harmonization_metrics_extended.docx` → `..._260802_v2.docx`: 328 anchored edits + 112 figure references + an appended "Summary of metric trends" section. Runs from the **original** document, so it re-applies the renumbering; never chain it after the v1 script. |
| `figure_drawing_scripts/recompute_extended_metrics_260802.py` | Recomputes every statistic quoted in the Extended document from the 2,234-approach set. Run `python figure_drawing_scripts/recompute_extended_metrics_260802.py snapshots` (from `figures_for_article/`) to re-derive the metric-table comparison below. |
| `Harmonization_metrics_extended_audit_260802.md` | The audit behind that pass: ~60 numbers that reproduced exactly, 54 that did not, and why. |
| `NAR_review_260802_2nd_iteration.md` | Second manuscript iteration: Tables 3 and 4 moved to Supplementary File 2, table numbering restored to 1–3, a corrupted Supplementary Figure 9 reference fixed, 22 language edits. |
| `figure_drawing_scripts/build_supp_file2_260802.py` | Rebuilds `supplementary_260802/Supplementary File 2.xlsx` with `Table_S1_methods` and `Table_S2_metrics`, swapping every `(N)` citation for the full bibliographic entry read out of the manuscript's own reference list. |
| `edit_python_scripts/apply_nar_table_move_edits_260802.py` | Applies that move to the manuscript → `FL_manuscript_versions/FL_harmonization_article_NAR_260802_2nd_iteration.docx`. Reference implementation for **tracked deletion of a whole table**, for **editing your own unaccepted insertion**, and for **reserving revision ids**. |
| `figure_drawing_scripts/add_LMN_metrics_260824.py` | Adds metric groups L/M/N (marker correlation preservation, cross-batch rank agreement, predictive validation — see `harmonization-metrics/marker_and_predictive_validation_plan_260819.md`) to `supplementary_260824/Supplementary File 2.xlsx`: 5 new `Table_S2_metrics` description rows, 82 new `Metric_polarity` rows (polarity 0), and new `Metric group`/`Metric type` columns classifying all 311 rows. Run again if L/M/N naming ever changes in `compute_batch_metrics.py`. |
| `figure_drawing_scripts/add_linearity_column_260825.py` | Adds `Linear` + `Linearity justification` columns to `Table_S1_methods` in `supplementary_260824/Supplementary File 2.xlsx`, classifying all 39 `harmonization-scripts/bench_shared.py` methods by the functional form of the *applied* correction (affine vs. not), independent of how its parameters are estimated — e.g. ComBat and SVA are Linear despite non-linear (empirical-Bayes / iterative) parameter estimation, because the correction they apply to the data is affine. `13_fsmvn` (per-gene, per-batch Z-score rescaled to a reference batch) is the pipeline's own designed proxy for plain Z-scaling; no implemented method performs pure per-gene-per-batch division by the batch mean — `02_median_scaling` is the closest analogue (a location-only, no-variance-term shift, matching what batch-mean division becomes on the log2 scale this pipeline works in). |

### The 260802 pass: what carried over

**Supplementary File 3 is the authoritative reproducibility source, not `metrics_comprehensive_*.csv`.**
Supp. File 3 (2,407 × 93) is the only table that holds all 14 strategies, all 33 methods *and*
`20_shambhala`. The newest full snapshot, `metrics_comprehensive_260609.csv`, is a proper subset
missing exactly the 84 `20_shambhala` rows, and `metrics_comprehensive_260527.csv` predates the
I/J/K strategies entirely (11 strategies only). Use Supp. File 3 for anything polarity-adjusted, and
260609 only for the **un-normalized** metrics Supp. File 3 omits (`ilisi_mean_*`, `exp_*`,
`pct_var_pc*`, `r2_*`) — stating n = 2,150 when you do.

**The analysis-set filter is `pct_samples_allNA < 5`** → exactly 2,234 rows, and it is what drops
`34_arsyn` and `38_harman` (0 of their 168 rows pass), leaving 31 methods.

**Figure 6B/9B is a mean of 87 per-metric η², not a decomposition of the composite score.**
Reproduce it by computing `SS_between / SS_total` per scoring column on the 2,234 subset and
averaging: 0.3629 / 0.2564 / 0.0155 / 0.0020 for method / strategy / imputation / post-removal.
A one-way OLS **on the composite score** gives 0.49 / 0.25 / 0.002 / 0.001 — different numbers, and
not what the figure shows.

**Numbers printed inside a figure beat the metric table.** `pct_var_pc1` in the metric table is
computed on standardized data over 50 PCs and disagrees with the PCA drawn in the figures
(83.3 % vs the 81.1 % printed in Figure 4A). The figure's own text layer is the authority for any
percentage the manuscript quotes from it — check it with `figtext` before "correcting" anything.

**Model specification, from `bench_shared.py`:** SVA, ComBat, ComBat-seq, InMoose, M-ComBat, ARSyN
and Harman receive `Diagnosis_cell_type_unified`; **limma `removeBatchEffect` gets `batch=` only, and
RUV gets `RUVg(cIdx=<10 housekeeping genes>, k=2)`** — neither protects biology.
Seeds live in `harmonization-metrics-calculation/compute_batch_metrics.py`: `random_state=42` everywhere,
UMAP `n_neighbors=30, min_dist=0.3`, t-SNE `perplexity=min(30, n//4)`, Barnes-Hut.

### Gotcha: adding a tracked column to a table with merged cells

`append_tracked_column()` in `apply_nar_review_edits_260802.py` appends a `w:gridCol` plus one
`w:tc` per `w:tr`, marks each new cell `w:cellIns` and wraps its text in `w:ins`. Two things to know:

- **`cell.text` from python-docx cannot see text inside `w:ins`,** so a new column reads as empty
  when you verify with `.text`. Verify by iterating raw `w:t` instead, or you will "fix" a column
  that was already correct.
- **Merged rows are the norm, not the exception.** In Table 3, 34 of 39 rows have the Version cell
  spanning the Reference column, so those rows have 9 cells where the header has 10 — which is why
  filling the existing Reference column in place silently does nothing and a new column is the only
  workable route. python-docx's `row.cells` repeats merged content and hides this; count
  `tr.findall(qn('w:tc'))` to see the real shape.

### `metrics_comprehensive_260527.csv` cannot reproduce anything in the article

It is not merely older than 260609 — it was computed on a **different set of prepared
matrices**. Merged against the deposited `Supplementary File 3` on
`(strat, imp, method, post_rm)` it shares 1,822 rows and agrees on **0 of 66** numeric
columns; `n_samples` and `n_genes` themselves differ by up to 850 and 1,309. The same merge
against `metrics_comprehensive_260609.csv` agrees on **79 of 79**. It also predates
strategies I, J and K (11 strategies, 2,626 rows).

**Always recompute through `figures_helpers.load_metrics_data()`** on
`metrics_comprehensive_260609.csv`. That is the function the figure notebook calls, and it
reproduces the analysis set exactly: 2,234 rows · 31 methods · 14 strategies · 87 scoring
columns. Its NA filter is `n_samples_allNA < 5% × 5,444`, and it keeps one canonical
Shambhala representative — `shambhala_P0std_Q0std`, renamed `20_shambhala`, confirmed by an
exact value match against Supp. File 3's `20_shambhala` rows (mean abs. diff ~1e-18).

The 15 clustermap best approaches (`top_ids`) and `HARSHNESS_LEVEL_MAP` live in
`Finally_assembled_figures_for_article.ipynb` cells 2 and 4; both are copied into
`recompute_extended_metrics_260802.py` so the recomputation runs without the notebook.

Two conventions matter for matching the figures: heat-map paragraphs summarise **means over
runs** (the figures average across imputations and post-removal), and MAD is the **plain,
unscaled** median absolute deviation.

### Gotcha: a bare figure number is not a safe search key

`"Figure 6"` is a substring of `"Supplementary Figure 6"`. A renumbering sweep that searches
for the bare reference rewrites the wrong one — silently producing
`"Supplementary Extended Figure 1"` and leaving a genuine reference unconverted, which is
exactly what `apply_extended_metrics_edits_260802.py` did. `figure_edits()` in the v2 script
grows each key leftwards until it is the first match in the text the replacer can still see
(earlier claimed spans blanked), and raises rather than guessing.

Two related traps in the same sweep:

- **Replacement text must be pre-renumbered.** It lands inside `w:ins`, which
  `safe_tracked_replace` deliberately cannot see, so the sweep will never reach it. Write
  replacements against the document's original numbering and pass them through `renum_text()`.
- **Drive the sweep from direct-child run text, not from `visible()`.** After an anchored
  edit, `visible()` includes your own inserted text; generating pairs from it produces
  searches that either miss or, worse, land on an unrelated live occurrence in the same
  paragraph.

Bare panel letters that repeat the number (`"Extended Figure 2D, 2E"`) carry no `Figure`
token on the second reference and need an explicit `SPECIALS` entry.

### Gotcha: deleting a whole table, and re-editing a document you already edited

`apply_nar_table_move_edits_260802.py` is the reference for three operations the earlier
scripts did not need:

- **Tracked deletion of a table.** Give every `w:tr` a `w:trPr/w:del` and wrap each surviving
  run in `w:del`, converting `w:t` → `w:delText`. Columns *you* added in a still-unaccepted
  pass are better withdrawn outright (remove the `w:ins`) than marked inserted-then-deleted:
  reject-all is identical either way and the XML stays readable.
- **Reserve revision ids.** `nid()` restarts from a fixed base (1000) on every run, so a
  second pass over a document that already carries revisions produces duplicate `w:id`s —
  78 of them here, which breaks Word's revision pane. Scan the input for the highest existing
  id and set `word_rewrite_trackchanges._rid[0]` above it before editing.
- **A search string must not cross an insertion boundary.** `retype_in_own_ins` edits text
  inside your own earlier `w:ins`, but only within a single `w:ins` element. An insertion
  often ends mid-sentence (`w:ins` holding `First, albeit the composite score`, with
  ` was not a decision criterion` continuing as a plain run), so the `old` string has to stop
  where the insertion does. The same applies to `safe_tracked_replace` around Mendeley `sdt`
  citations: text either side of `(90–93)` cannot be matched as one string.

### Gotcha: renumbering figures without collisions

When a renumbering maps N → N+k, a naive per-string sweep rewrites its own output
(`Extended Figure 5` → `8`, then the pass for `8` → `11` lands on it). `safe_tracked_replace` makes a
plain left-to-right sweep collision-proof for free: after each call the replaced text sits inside
`w:del`/`w:ins`, which `_direct_runs` no longer returns, so the next search only ever sees text that
has not been touched. Generate the `(old, new)` pairs in document order and apply them in that order.
Handle references that repeat the number (`Extended Figure 5G, 5H, 5K, 5L`) as explicit whole-string
specials **first**, and blank them out of the text before generating the generic pairs.

**Numbering established 2026-08-02** — the delivered artwork is one continuous `Extended Figure`
sequence and the Extended document was three behind it: document `Figure 6/7/8` → `Extended Figure
1/2/3`, document `Extended Figure 1–10` → `Extended Figure 4–13`. Main manuscript `Figure 9` →
`Figure 6`. Confirmed by matching every delivered PDF's text layer to the document's own legends.

### Supplementary packaging reality

17 supplementary figures are **19.2 MB of vector PDF after maximal recompression**
(`doc.save(garbage=4, deflate=True, deflate_images=True, deflate_fonts=True, clean=True)` — that
alone takes them from 33 MB). Seven bundles therefore cannot be under 1.5 MB each; they land at
1.31–3.89 MB. NAR's single-combined-PDF route is the only one that fits, so
`supplementary_260802/Supplementary Figures S1-S17.pdf` (17 titled, bookmarked pages) is the
recommended submission. Do not re-attempt the 7 × 1.5 MB target without rasterizing.

### Gotcha: Mendeley citations are `w:sdt`, not fields

This manuscript stores all 95 in-text citations as **118 `<w:sdt>` structured-document-tag
elements**, and the bibliography as one more `sdt`. There are **zero** `w:fldChar`/`w:instrText`
elements, so the usual field-detection check misses them.

`word_rewrite_trackchanges.tracked_replace()` rebuilds a paragraph from its *concatenated* text and
re-emits plain runs — **this silently destroys every Mendeley citation in that paragraph** (34 body
paragraphs are affected). Use `safe_tracked_replace()` in
`apply_nar_review_edits_260727.py` instead: it edits only runs that are **direct children** of the
paragraph, so anything nested in `w:sdt` or `w:hyperlink` is left byte-for-byte intact.

Two further practical points from that script:

- Runs containing `w:lastRenderedPageBreak` are safe to rebuild (Word regenerates the hint); any
  other non-`w:t` child (breaks, tabs, drawings) is not — skip and report.
- Resolve **all** anchor lookups to lxml element references *before* mutating anything. After an
  edit the original wording lives in `w:delText`, which a `.//w:t` text search no longer sees, so a
  later anchor lookup on edited text fails.

### Gotcha: editing a manuscript that already carries tracked changes

When the input `.docx` is a previous pass's output (as `..._260727_partially_edited.docx` is), the
text you want to change may sit **inside** an unaccepted `w:ins`. Such runs are not direct children
of the paragraph, so `safe_tracked_replace()` reports `not-found` — it cannot see them and must not
touch them. Two rules from `apply_nar_abbrev_edits_260728.py`:

- Split the work: a sweep over **plain direct-child runs** (real del/ins pairs) plus an explicit
  `IN_PLACE_EDITS` list for text inside your *own* earlier `w:ins`, retyped in place after checking
  `w:author`. That is what Word does when you edit your own not-yet-accepted insertion, and
  reject-all still restores the original because the whole insertion disappears. Never retype inside
  another author's revision — report it instead.
- Skip `[REVIEWER NOTE]` / `[NAR EDITOR NOTE]` paragraphs in any global search-and-replace: they
  quote the old wording deliberately, and they also break "first occurrence" scans (a note about an
  abbreviation contains that abbreviation long before its real first use).

For a repeated rename, call `safe_tracked_replace(p, [(old, new)])` once per occurrence counted in
the direct-child text — after each call the replaced text has moved into `w:del`/`w:ins`, so the
next call lands on the following occurrence.

Validation to run before declaring done (`scratchpad/validate.py` pattern): reject-all text must
equal the original exactly; `w:sdt` count and contents must be unchanged; zero `w:t` inside `w:del`;
zero `w:delText` outside `w:del`; abstract still ≤200 words after accept-all.
