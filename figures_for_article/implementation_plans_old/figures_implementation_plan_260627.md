# Implementation Plan: Figure Revisions from Inspection Round 1
**Date:** 2026-06-27  
**Source document:** `final_figures_inspection_260627.md`  
**Scope:** Post-inspection corrections to `Finally_assembled_figures_for_article.ipynb`, `figures_helpers.py`, and `fig10_metric_star_visualization.py`. No new notebooks. No infrastructure changes.

---

## Overview

The June 27 visual inspection of all 14 generated figures identified 20 issues. The single most impactful fix is applying the **NA filter** (`pct_samples_allNA < 0.05`) inside `load_metrics_data()` in `figures_helpers.py`. This filter reduces the run count from 2,407 to **2,234** valid approaches, automatically removes 38_harman and 172 other invalid runs from every figure, and restores the Fig 8 Panel A centroid dispersion heatmap (which was blank because approaches with missing tSNE/UMAP were predominantly the invalid ones). All other figures inherit the corrected data without cell-level edits.

The remaining fixes fall into three categories:
1. **Scientific content additions:** LISI overlay on Fig 9A, Discussion flag on Fig 9C, icon additions to Fig 11, Best 15 overlays on Fig 8B Panels A/B.
2. **Layout and readability:** Log scales (kBET, WaterMelon ratio), subtitle/axis label fixes, minimum 7 pt font in Supp D, Panel D removal from Fig 8 to supplementary.
3. **Data source corrections:** Supp A palette, Supp B Sankey alpha, correct centroid dispersion column selection in Fig 8A.

---

## Background / Reference Data

### NA filter derivation

The `pct_samples_allNA` column in `metrics_comprehensive_260609.csv` measures the fraction of samples with all-NA expression after a given harmonization run. The validated threshold from the article is **< 0.05** (< 5% of samples all-NA). Applying it removes exactly 173 runs, leaving **2,234 valid attempts**.

Column name: `pct_samples_allNA`  
Filter expression: `df_ok["pct_samples_allNA"] < 0.05`

### Centroid dispersion correct column names

| Available column | Present in approx. | Polarity |
|---|---|---|
| `tsne_centroid_disp_RNA_BATCH` | all approaches | −1 |
| `umap_centroid_disp_RNA_BATCH` | all approaches | −1 |
| `tsne_centroid_disp_COHORT_LABEL` | most approaches | −1 |
| `umap_centroid_disp_COHORT_LABEL` | most approaches | −1 |
| `tsne_centroid_disp_PLATFORM_RNA` | most approaches | −1 |
| `umap_centroid_disp_PLATFORM_RNA` | most approaches | −1 |
| `tsne_centroid_disp_RNASEQ_SOURCE` | most approaches | −1 |
| `umap_centroid_disp_RNASEQ_SOURCE` | most approaches | −1 |

All 8 columns are already in `_POLARITY_MANUAL` and `scoring_cols`. The original Fig 8 Panel A code searched `scoring_cols` for `"centroid_disp"` — which is correct. The blank heatmap was caused solely by the invalid approaches (those without tSNE/UMAP embeddings) being included in the data. After the NA filter, coverage improves dramatically.

### rna_batch_palette location

`rna_batch_palette` is defined in `Introductory_figures_for_article.ipynb` Cell 3 but not in `Finally_assembled_figures_for_article.ipynb`. For Supp A, we must either (a) define it inline in Cell 3 of the finally-assembled notebook, or (b) load it from the annotation after Cell 4 (S3 load). Option (b) is cleaner: derive it from `comb_ann["RNA_BATCH"]` using the same `sns.color_palette("tab20")` assignment used in the introductory notebook. Add this derivation to Cell 4 (the S3 load cell).

### GO enrichment database path

Available at:
```
~/Retroelements/T2T_genes_article/T2T_transposons_genes/
```
Look for `.obo` files (Gene Ontology) or gene annotation tables with GO terms. `gseapy.enrichr()` (already installed in `collagen_3_11` venv) can be used as fallback if `goatools` is unavailable.

---

## Files to Change

### 1. `figures_for_article/figures_helpers.py`

**Location:** `load_metrics_data()`, after the Shambhala filter block (~line 396).

**1a — Add NA filter (CRITICAL)**

```python
# BEFORE (lines ~390–398):
df_ok = df[df["status"] == "ok"].copy()

# Keep one canonical Shambhala representative only
df_ok = df_ok[
    (~df_ok["method"].str.startswith("shambhala_"))
    | (df_ok["method"] == "shambhala_P0std_Q0std")
].copy()
df_ok.loc[df_ok["method"] == "shambhala_P0std_Q0std", "method"] = "20_shambhala"
```

```python
# AFTER:
df_ok = df[df["status"] == "ok"].copy()

# Keep one canonical Shambhala representative only
df_ok = df_ok[
    (~df_ok["method"].str.startswith("shambhala_"))
    | (df_ok["method"] == "shambhala_P0std_Q0std")
].copy()
df_ok.loc[df_ok["method"] == "shambhala_P0std_Q0std", "method"] = "20_shambhala"

# NA filter: exclude approaches where >5% of all samples have all-NA expression.
# This removes 38_harman and 172 other invalid approaches, leaving 2,234 valid runs.
if "pct_samples_allNA" in df_ok.columns:
    n_before = len(df_ok)
    df_ok = df_ok[df_ok["pct_samples_allNA"] < 0.05].copy()
    print(f"NA filter: {n_before} → {len(df_ok)} rows (removed {n_before - len(df_ok)} invalid approaches)")
```

**1b — Update docstring count**

```python
# BEFORE (docstring line ~376):
    df_ok : pd.DataFrame, shape (2234, ~230)
        Filtered metrics; index = run_id.
```

The docstring already says 2234 — but it will now be correct once the NA filter is in place. No text change needed here.

---

### 2. `figures_for_article/Finally_assembled_figures_for_article.ipynb`

Cells are referenced by 0-based index from the cell list.

---

#### Cell 2 (data load / `_top_ids`) — no code change needed

The NA filter is applied inside `load_metrics_data()`, so Cell 2 inherits 2,234 rows automatically. The axis label `"Rank (all 2,234 attempts)"` in Fig 10 Panel A was already written correctly in the original plan code.

---

#### Cell 6 — Fig 7: move Panel D (UMAP entropy) → Supp; add kBET log scale

**6a — Redefine GridSpec for 5 panels (remove Panel D)**

```python
# BEFORE:
gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)
ax_A = fig.add_subplot(gs[0, 0])   # Panel A — kBET acceptance rate by method (strip)
ax_B = fig.add_subplot(gs[0, 1])   # Panel B — iLISI vs cLISI scatter (trade-off)
ax_C = fig.add_subplot(gs[1, 0])   # Panel C — Graph connectivity by biology group (bar)
ax_D = fig.add_subplot(gs[1, 1])   # Panel D — UMAP entropy by method (boxplot)
ax_E = fig.add_subplot(gs[2, 0])   # Panel E — tSNE entropy by method (boxplot)
ax_F = fig.add_subplot(gs[2, 1])   # Panel F — Local (kBET) vs global (PCR) scatter
```

```python
# AFTER (5 panels; Panel D slot becomes Panel E, F becomes Panel E):
gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)
ax_A = fig.add_subplot(gs[0, 0])   # Panel A — kBET acceptance rate by method (strip)
ax_B = fig.add_subplot(gs[0, 1])   # Panel B — iLISI vs cLISI scatter (trade-off)
ax_C = fig.add_subplot(gs[1, 0])   # Panel C — Graph connectivity by biology group (bar)
ax_D = fig.add_subplot(gs[1, 1])   # Panel D — tSNE entropy by method (boxplot)
ax_E = fig.add_subplot(gs[2, :])   # Panel E — Local (kBET) vs global (PCR) scatter (wide)
# UMAP entropy (formerly Panel D) moved to Supp Fig UMAP_entropy
```

**6b — Replace Panel D content (UMAP entropy → tSNE entropy)**

Move the tSNE entropy code (formerly in Panel E) to Panel D. Remove the UMAP entropy block (formerly Panel D). The local-global scatter (formerly Panel F) moves to Panel E (wide, gs[2,:]).

**6c — Add log scale to kBET axis (Panel A)**

```python
# AFTER the kBET stripplot block, add:
ax_A.set_xscale("symlog", linthresh=0.01)
ax_A.set_xlabel("kBET acceptance rate (symlog)", fontsize=GLOBAL_FONT_SIZE)
```

**6d — Add UMAP entropy as a new Supp Figure cell**

Add a new notebook cell immediately after the Fig 7 cell:
```python
## Supplementary Figure — UMAP Entropy (moved from Fig 7 Panel D)
# [insert UMAP entropy boxplot code here, same as former Panel D]
save_figure(fig, "supplementary/supp_umap_entropy")
plt.close()
```

---

#### Cell 8 — Fig 8: fix Panel A columns; Panel C log scale; Panel D → supp

**8a — Fix Panel A column selection (use df_ok, not scoring_cols)**

```python
# BEFORE:
_disp_cols = [c for c in scoring_cols if "centroid_disp" in c]
_order_A = df_ok.groupby("method")[_disp_cols].mean().mean(axis=1).sort_values().index
_disp_pivot = df_ok.groupby("method")[_disp_cols].mean().loc[_order_A]
```

```python
# AFTER (use df_ok.columns, not scoring_cols, to also catch cols with polarity=0):
_disp_covariates = ["RNA_BATCH", "COHORT_LABEL", "PLATFORM_RNA", "RNASEQ_SOURCE"]
_disp_cols = [
    c for c in df_ok.columns
    if "centroid_disp" in c
    and any(cov in c for cov in _disp_covariates)
    and df_ok[c].notna().mean() > 0.5
]
if not _disp_cols:
    ax_A.text(0.5, 0.5, "No centroid dispersion columns with >50% coverage",
              ha="center", va="center", transform=ax_A.transAxes, fontsize=GLOBAL_FONT_SIZE)
else:
    _order_A = df_ok.groupby("method")[_disp_cols].mean().mean(axis=1).sort_values().index
    _disp_pivot = df_ok.groupby("method")[_disp_cols].mean().loc[_order_A]
    sns.heatmap(_disp_pivot.T, ax=ax_A, cmap="RdBu_r", center=0,
                cbar_kws={"shrink": 0.5, "label": "Mean centroid dispersion"},
                xticklabels=True, yticklabels=True)
    ax_A.set_title("A: UMAP/tSNE centroid dispersion by method", fontsize=GLOBAL_FONT_SIZE)
    ax_A.tick_params(labelsize=GLOBAL_FONT_SIZE - 1)
```

**8b — Add log scale to Panel C (WaterMelon ratio)**

```python
# AFTER the Panel C barh block:
ax_C.set_xscale("symlog", linthresh=0.1)
ax_C.set_xlabel("WM ratio bio/batch (symlog)", fontsize=GLOBAL_FONT_SIZE)
```

**8c — Move Panel D (CMS) to supplementary**

In the Cell 8 Fig 8 GridSpec, change from `gs = gridspec.GridSpec(3, 2)` (6 panels) to `gs = gridspec.GridSpec(3, 2)` (same, but Panel D becomes blank or is removed from Fig 8 and the code block is cut/moved to a new supplementary cell).

Specifically: delete the Panel D (CMS) code block from Cell 8 and add a new supplementary cell:
```python
## Supplementary Figure — CMS (Cell Mixing Score) — moved from Fig 8 Panel D
# [insert CMS barplot code here]
save_figure(fig_cms, "supplementary/supp_cms_by_method")
plt.close()
```

The Panel D `ax_D` subplot can be repurposed as extra whitespace or used for a concise metric like `n_genes_noNA` or ASW batch detail.

---

#### Cell 10 — Fig 8B: add Best 15 overlays (Panels A, B); NA filter note

**10a — Panel A: use `data_v3` to include Best 15 in sorted order**

```python
# BEFORE:
_ks_mean = df_ok.groupby("method")[_ks_d_cols[0]].mean().sort_values()
_colors_A = [BEST_COLOR if m == BEST_LABEL else method_pal.get(m, "gray")
             for m in _ks_mean.index]
ax_A.barh(_ks_mean.index, _ks_mean.values, color=_colors_A, height=0.7)
```

```python
# AFTER (use data_v3 which includes Best-labeled rows, sorted by value):
_ks_mean = data_v3.groupby("method")[_ks_d_cols[0]].mean().sort_values()
_colors_A = [BEST_COLOR if m == BEST_LABEL else method_pal.get(m, "gray")
             for m in _ks_mean.index]
ax_A.barh(_ks_mean.index, _ks_mean.values, color=_colors_A, height=0.7)
ax_A.axvline(_ks_mean[BEST_LABEL], color=BEST_COLOR, linestyle="--",
             linewidth=1.2, label=f"Best mean: {_ks_mean[BEST_LABEL]:.3f}")
ax_A.legend(fontsize=GLOBAL_FONT_SIZE - 1)
```

**10b — Panel B: same pattern as 10a for fraction significant KS**

```python
# BEFORE:
_ks_sig_mean = df_ok.groupby("method")[_ks_sig_cols].mean()
_ks_sig_mean.plot(kind="barh", ax=ax_B, stacked=True, colormap="Set2", legend=True)
```

```python
# AFTER:
_ks_sig_mean = data_v3.groupby("method")[_ks_sig_cols].mean()
_ks_sig_mean.plot(kind="barh", ax=ax_B, stacked=True, colormap="Set2", legend=True)
# Best row will appear sorted by its total value, not pinned at the end
```

---

#### Cell 12 — Supp 9: fix metric prefix

**12a — Replace incorrect metric prefix with `tsne_centroid_disp` / `umap_centroid_disp`**

The Supp 9 cell currently contains a placeholder with instructional text. If an incorrect column prefix was used for the `_disp_` variable, replace all occurrences of the wrong prefix with `tsne_centroid_disp_` / `umap_centroid_disp_`. Look for any variable like `_supp9_metric = "..."` and correct to use columns from `_disp_covariates` list (same as Cell 8 fix 8a).

---

#### Cell 14 — Fig 9: LISI addition; subtitle fix; Discussion flag; y-axis note

**14a — Panel A: add LISI as secondary indicator**

```python
# AFTER the existing Panel A scatter block:
# Add LISI-based coloring as secondary local-mixing indicator
_ilisi_col = next((c for c in df_ok.columns if c.startswith("ilisi_norm_RNA_BATCH")), None)
if _ilisi_col:
    # Color by iLISI quartile (4 levels) to avoid overplotting
    _ilisi_q = pd.qcut(df_ok[_ilisi_col].fillna(0), q=4,
                       labels=["q1", "q2", "q3", "q4"])
    _ilisi_sizes = _ilisi_q.map({"q1": 8, "q2": 15, "q3": 25, "q4": 40}).fillna(8)
    # Re-scatter with size ∝ iLISI quartile on top of the existing scatter
    ax_A.scatter(df_ok[_repr_global], df_ok[_repr_local],
                 s=_ilisi_sizes, c="none", edgecolors="#333333",
                 linewidths=0.5, alpha=0.4, zorder=4, label="marker size ∝ iLISI quartile")
    ax_A.legend(fontsize=GLOBAL_FONT_SIZE - 2, loc="upper left")
```

**14b — Panel B: fix subtitle overlap**

```python
# BEFORE:
ax_B.set_title("B: Composite score by strategy harshness", fontsize=GLOBAL_FONT_SIZE)
```

```python
# AFTER (remove "Factor importance" suptitle collision by using y padding):
ax_B.set_title("B: Composite score\nby strategy harshness", fontsize=GLOBAL_FONT_SIZE)
# And ensure fig.suptitle y=1.02 (slightly further from panels)
```

At the end of the cell, change:
```python
# BEFORE:
fig.suptitle("Figure 9 — Cross-Metric Correlation and Factor Importance",
             fontsize=GLOBAL_FONT_SIZE + 1, y=1.01)
```
```python
# AFTER:
fig.suptitle("Figure 9 — Cross-Metric Correlation and Factor Importance",
             fontsize=GLOBAL_FONT_SIZE + 1, y=1.04)
```

**14c — Panel C: add Discussion flag text box**

```python
# AFTER the Panel C η² barplot block, add a note text box:
ax_C.text(
    0.98, 0.02,
    "⚠ Discussion: clustermap clustering order is strategy > method;\n"
    "η² shows method > strategy — both reflect different aspects of variance structure.",
    ha="right", va="bottom", transform=ax_C.transAxes,
    fontsize=GLOBAL_FONT_SIZE - 2, color="#555555",
    bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFFDE7", edgecolor="#F4A261", alpha=0.8),
)
```

**14d — Panel D: add y-axis stacked sum note**

```python
# AFTER the Panel D stacked bar block:
ax_D.set_ylabel(
    "Cumulative summed normalized score\n(stacked; not bounded to 1)",
    fontsize=GLOBAL_FONT_SIZE,
)
ax_D.annotate(
    "Note: y-axis shows cumulative sum of\nnormalized group scores — not a fraction.",
    xy=(0.01, 0.97), xycoords="axes fraction",
    fontsize=GLOBAL_FONT_SIZE - 2, color="#555555", va="top",
)
```

---

#### Cell 16 — Fig 10: fix Panel D width; fix Panel B x-axis labels

**16a — Panel D: abbreviate method names to prevent x-axis overlap**

```python
# AFTER setting ax_D x-tick labels:
_abbrev = {
    "10_mnn": "MNN", "04_sva": "SVA", "16_fsqn_r": "FSQN-R",
    "27_amdbnorm": "AMDBNorm", "29_fsmvn": "FSMVN", "13_fsmvn": "FSMVN-2",
    "33_amdbnorm": "AMDBNorm-2", "01_raw": "Raw", "08_inmoose_combatseq": "ComBatSeq",
    "11_harmony": "Harmony", "12_scanorama": "Scanorama", "22_tmm": "TMM",
    "23_vst": "VST", "28_npn": "NPN", "38_harman": "Harman",
    "17_qsmooth": "Qsmooth", "21_harmonizr": "Harmonizr",
    "20_shambhala": "Shambhala",
}
_labels_D = [_abbrev.get(t.get_text(), t.get_text()) for t in ax_D.get_xticklabels()]
ax_D.set_xticklabels(_labels_D, rotation=60, ha="right", fontsize=GLOBAL_FONT_SIZE - 1)
```

**16b — Panel B: shorten x-axis tick labels (metric names)**

```python
# AFTER setting xticks on parallel coordinates Panel B:
_short_metric = {c: c.split("_")[0] + "\n" + c.split("_")[-1] if "_" in c else c
                 for c in _key_metrics}
ax_B.set_xticklabels(
    [_short_metric.get(c, c) for c in _key_metrics],
    rotation=30, ha="right", fontsize=GLOBAL_FONT_SIZE - 1,
)
```

**16c — Panel A: verify count label reads "2,234"**

The x-axis label is `"Rank (all 2,234 attempts)"` in the plan code. After the NA filter fix, the loop variable `len(_ranked)` will equal 2,234 automatically. Also update the axis label if it still says 2,407:
```python
# BEFORE:
ax_A.set_xlabel("Rank (all 2,407 attempts)", fontsize=GLOBAL_FONT_SIZE)
```
```python
# AFTER:
ax_A.set_xlabel(f"Rank (all {len(_ranked):,} attempts, filtered)", fontsize=GLOBAL_FONT_SIZE)
```

---

#### Cell 18 — Supp A: use `rna_batch_palette`; add NA-samples figure

**18a — Use `rna_batch_palette` instead of `platform_palette`**

First, add `rna_batch_palette` derivation to **Cell 4** (S3 data load cell), after `comb_ann` is loaded:

```python
# ADD at end of Cell 4 (S3 load), after comb_ann is loaded:
_rna_batches_sorted = sorted(comb_ann["RNA_BATCH"].unique())
_palette_colors = sns.color_palette("tab20", n_colors=min(20, len(_rna_batches_sorted)))
_palette_colors += sns.color_palette("tab20b", n_colors=max(0, len(_rna_batches_sorted) - 20))
rna_batch_palette = dict(zip(_rna_batches_sorted, _palette_colors))
print(f"rna_batch_palette: {len(rna_batch_palette)} batches")
```

Then in Cell 18 (Supp A), change:
```python
# BEFORE:
ax.barh(nona_sorted["RNA_BATCH"], nona_sorted["n_nona_genes"],
        color=[platform_palette.get(pg, "gray") for pg in nona_sorted["platform_group"]],
        height=0.7)
```
```python
# AFTER:
ax.barh(nona_sorted["RNA_BATCH"], nona_sorted["n_nona_genes"],
        color=[rna_batch_palette.get(b, "gray") for b in nona_sorted["RNA_BATCH"]],
        height=0.7)
```

Also fix the bottom panel x-axis labels in Supp A:
```python
# AFTER the bottom panel barplot:
ax_bottom.set_xticklabels(ax_bottom.get_xticklabels(), rotation=45, ha="right",
                           fontsize=GLOBAL_FONT_SIZE - 1)
```

**18b — Add new supplementary cell: NA samples per batch**

Add a new notebook cell after Cell 18:
```python
## Supplementary Figure A2 — NA Samples Per Batch

# Compute NA samples per batch from df_ok Group K columns
_na_col = "pct_samples_allNA" if "pct_samples_allNA" in df_ok.columns else None
if _na_col and "RNA_BATCH" not in df_ok.columns:
    # pct_samples_allNA is a per-run metric; plot across all strategies, sorted by batch
    _na_per_batch = (
        df_ok.groupby("strat")[_na_col]
        .agg(["mean", "std"])
        .reset_index()
        .sort_values("mean", ascending=False)
    )
else:
    # Load per-batch NA sample count directly from annotation if available
    _na_per_batch = None

if _na_per_batch is not None:
    fig_na, ax_na = plt.subplots(figsize=(8.27, 5))
    _colors_na = [harshness_pal.get(HARSHNESS_MAP.get(s, "medium"), "gray")
                  for s in _na_per_batch["strat"]]
    ax_na.barh(_na_per_batch["strat"], _na_per_batch["mean"],
               xerr=_na_per_batch["std"], color=_colors_na, height=0.7,
               error_kw={"linewidth": 0.8, "ecolor": "#555555"})
    ax_na.axvline(0.05, linestyle="--", color="red", linewidth=1.2, label="5% threshold")
    ax_na.set_xlabel("Mean % samples all-NA across methods", fontsize=GLOBAL_FONT_SIZE)
    ax_na.set_title("NA sample fraction per strategy (threshold = 5%)", fontsize=GLOBAL_FONT_SIZE)
    ax_na.legend(fontsize=GLOBAL_FONT_SIZE - 1)
    ax_na.tick_params(labelsize=GLOBAL_FONT_SIZE)
    sns.despine(ax=ax_na)
    save_figure(fig_na, "supplementary/suppA2_na_samples_per_strategy")
    plt.close()
```

Note: if comb_ann (from S3) is loaded, a second version can be added that shows per-batch sample counts directly from the raw annotation.

---

#### Cell 20 — Supp B: fix Sankey alpha=0.0; fix gene count labels

**20a — Fix flow band alpha**

Search for `alpha=0.0` in the Supp B cell and replace with `alpha=0.55`:
```python
# BEFORE (somewhere in Supp B sankey drawing):
# ... alpha=0.0 ...   ← flow bands invisible
```
```python
# AFTER:
# ... alpha=0.55 ...  ← flow bands visible
```

**20b — Fix gene count label truncation**

The label truncation `"KNN/47 ge"` comes from either a data-not-loaded issue (S3 not called) or a string formatting bug. Add a guard that skips the Sankey if `gene_sets` is not populated:
```python
# BEFORE:
# Sankey drawn unconditionally
```
```python
# AFTER:
if not gene_sets:
    ax_sankey.text(0.5, 0.5, "Run Cell 4 and load gene_sets from S3 first",
                   ha="center", va="center", transform=ax_sankey.transAxes,
                   fontsize=GLOBAL_FONT_SIZE, color="red")
else:
    # Sankey drawing code
    pass
```

Also fix label format: use full gene count (not truncated):
```python
# BEFORE:
label = f"{imp}/{len(genes)} ge"
```
```python
# AFTER:
label = f"{imp}\n{len(genes):,} genes"
```

---

#### Cell 22 — Supp C: add gene set loading and GO database

**22a — Panel B: add S3 gene set loading note**

The existing placeholder text says "implement after gene list loading from S3". Replace with actual code using `gene_sets` (loaded in Cell 4):
```python
# Panel B: FL gene set accumulation curves by harshness
if gene_sets:
    # For each (strat, imp) pair, compute the count of FL-signature genes
    # that are retained; plot as accumulation curve by harshness tier
    _fl_sigs = set()  # load from dlbcl_signatures.gmt if available
    _gmt_path = Path("..") / "harmonization-metrics" / "dlbcl_signatures.gmt"
    if _gmt_path.exists():
        with open(_gmt_path) as _f:
            for _line in _f:
                _parts = _line.strip().split("\t")
                if len(_parts) > 2:
                    _fl_sigs.update(_parts[2:])
    # Compute overlap
    _overlap = {
        k: len(v & _fl_sigs) / max(len(_fl_sigs), 1) * 100
        for k, v in gene_sets.items()
    }
    _ov_df = pd.Series(_overlap).reset_index()
    _ov_df.columns = ["strat", "imp", "pct_fl_genes_retained"]
    sns.barplot(data=_ov_df, x="imp", y="pct_fl_genes_retained",
                hue="strat", ax=ax_B, palette=strat_pal)
    ax_B.set_title("B: FL gene set retention by imputation strategy", fontsize=GLOBAL_FONT_SIZE)
    ax_B.set_ylabel("% FL signature genes retained", fontsize=GLOBAL_FONT_SIZE)
    sns.despine(ax=ax_B)
else:
    ax_B.text(0.5, 0.5, "Load gene_sets from Cell 4 to populate",
              ha="center", va="center", transform=ax_B.transAxes, fontsize=GLOBAL_FONT_SIZE)
```

**22b — Panel C: add GO database path**

```python
# Panel C: GO enrichment barplot
_go_db_path = Path.home() / "Projects" / "Retroelements" / "T2T_genes_article" / "T2T_transposons_genes"
try:
    import gseapy
    # Compare KNN vs strict unique genes
    _knn_strict_unique = gene_sets.get(("S0_no_removal", "knn"), set()) - \
                         gene_sets.get(("S0_no_removal", "strict"), set())
    if _knn_strict_unique and len(_knn_strict_unique) >= 10:
        _enr = gseapy.enrichr(
            gene_list=list(_knn_strict_unique),
            gene_sets="GO_Biological_Process_2023",
            organism="Human",
            outdir=None,
        )
        _top10 = _enr.results.sort_values("Adjusted P-value").head(10)
        ax_C.barh(_top10["Term"].str[:50], -np.log10(_top10["Adjusted P-value"]),
                  color="#457B9D", height=0.7)
        ax_C.axvline(1.3, linestyle="--", color="red", linewidth=0.8,
                     label="p=0.05 threshold")
        ax_C.set_xlabel("-log10(adj. p-value)", fontsize=GLOBAL_FONT_SIZE)
        ax_C.set_title("C: GO enrichment — KNN-only recovered genes", fontsize=GLOBAL_FONT_SIZE)
        ax_C.legend(fontsize=GLOBAL_FONT_SIZE - 1)
        sns.despine(ax=ax_C)
    else:
        ax_C.text(0.5, 0.5, f"KNN-unique genes: {len(_knn_strict_unique)}\n(< 10 for enrichment)",
                  ha="center", va="center", transform=ax_C.transAxes, fontsize=GLOBAL_FONT_SIZE)
except Exception as _e:
    ax_C.text(0.5, 0.5, f"GO enrichment failed:\n{_e}",
              ha="center", va="center", transform=ax_C.transAxes, fontsize=GLOBAL_FONT_SIZE)
    ax_C.set_title("C: GO enrichment (collagen context expected)", fontsize=GLOBAL_FONT_SIZE)
```

---

#### Cell 24 — Fig 11: add icons for sample types and platforms

The existing `L1_nodes` already uses emoji icons (🧊, 🟫, 🔬, 🔬📊, 🔬📈). The inspection asks for additional icons on **Level 2 method recommendation** nodes. Add algorithm-representative icons to `L2_nodes`:

```python
# BEFORE:
L2_nodes = [
    (0.6, 3.3, "MNN\n(primary)", method_pal.get("10_mnn", "#D62828"), "#2DC653"),
    (1.4, 3.3, "FSQN R\n(alternative)", method_pal.get("16_fsqn_r", "#FCBF49"), "#F4A261"),
    ...
]
```

```python
# AFTER — add icon unicode to text:
L2_nodes = [
    (0.6,  3.3, "MNN\n(primary)\n⛓", method_pal.get("10_mnn", "#D62828"), "#2DC653"),
    (1.4,  3.3, "FSQN R\n(alt.)\n📐", method_pal.get("16_fsqn_r", "#FCBF49"), "#F4A261"),
    (2.5,  3.3, "SVA +\nsoftimpute/KNN\n★ FFPE mix\n🔗", method_pal.get("04_sva", "#F77F00"), "#2DC653"),
    (5.0,  3.3, "SVA +\nsoftimpute/KNN\n(2 FL subgroups)\n🔗", method_pal.get("04_sva", "#F77F00"), "#2DC653"),
    (7.0,  3.3, "FSQN R\n(primary)\n📐", method_pal.get("16_fsqn_r", "#FCBF49"), "#2DC653"),
    (7.9,  3.3, "AMDBNorm /\nFSMVN + post-rm\n📊", method_pal.get("27_amdbnorm", "#A8DADC"), "#F4A261"),
    (9.0,  3.3, "MNN +\npost-removal\n⛓🔧", method_pal.get("10_mnn", "#D62828"), "#AAAAAA"),
]
```

Also add a legend box for L1 platform icons:
```python
# ADD after the main tree drawing, below the last level:
_icon_legend = [
    ("🧊", "Fresh-frozen (FF)"), ("🟫", "FFPE"), ("🔬", "RNA-seq (Illumina NGS)"),
    ("📊", "Illumina microarray"), ("📈", "Affymetrix microarray"),
    ("⛓", "MNN (graph-based)"), ("📐", "FSQN R (quantile norm.)"),
    ("🔗", "SVA (surrogate vars.)"), ("🔧", "post-removal QC"),
]
for i, (icon, label) in enumerate(_icon_legend):
    ax.text(0.2 + (i % 5) * 2.0, 0.6 - (i // 5) * 0.4,
            f"{icon} = {label}", fontsize=GLOBAL_FONT_SIZE - 1, va="top")
```

---

#### Cell 26 — Supp D: enforce minimum 7 pt font

**26a — Add `fontsize` enforcement to all Supp D panels**

At the end of the Supp D cell, after building the FacetGrid or loop of axes:
```python
# AFTER all panel creation — enforce minimum font size 7 pt:
_min_fs = max(7, GLOBAL_FONT_SIZE - 3)
for _ax in fig_suppD.axes:
    _ax.tick_params(labelsize=_min_fs)
    _ax.set_xlabel(_ax.get_xlabel(), fontsize=_min_fs)
    _ax.set_ylabel(_ax.get_ylabel(), fontsize=_min_fs)
    _ax.set_title(_ax.get_title(), fontsize=_min_fs)
    for _item in ([_ax.title, _ax.xaxis.label, _ax.yaxis.label]
                  + _ax.get_xticklabels() + _ax.get_yticklabels()):
        _item.set_fontsize(_min_fs)
```

Apply the same pattern to Supp E, F, G cells.

---

### 3. `figures_for_article/fig10_metric_star_visualization.py`

**No code change needed.** The script calls `fh.load_metrics_data()` which will pick up the NA filter automatically once `figures_helpers.py` is patched. The `TOP_IDS` list in the script is slightly different from the notebook's `_top_ids` — this is acceptable (it was a development version). The NA filter ensures the data is correct regardless.

---

## Files That Do NOT Need to Change

| File | Reason |
|---|---|
| `Introductory_figures_for_article.ipynb` | Introductory figures (Figs 1A–2A) unaffected |
| `pipeline_scheme_figure.py` | Standalone pipeline diagram; no metric data |
| `harmonization-metrics/compute_batch_metrics.py` | Metrics already computed and saved to CSV |
| `harmonization-metrics/harmonization_metrics_analysis_v3.ipynb` | Source of analysis logic; never edited directly |
| `article_figures_status_260625.md` | Status tracker; update manually after running |
| `notebooks_for_figures_260625.md` | Reference document; update manually after running |

---

## Side Effects and Caveats

1. **NA filter changes `df_ok` shape permanently.** All assertion counts (`assert len(df_best) == 15`) should still pass because the Best 15 approaches are valid runs that pass the filter. Verify this explicitly after patching `figures_helpers.py`.

2. **`data_v3` will have 2,249 rows** (2,234 + 15 Best-tagged rows) after the filter. The old value was 2,422 rows. Update any hardcoded count checks.

3. **Fig 8 Panel A** may still show some NA cells after the filter (not all approaches have tSNE/UMAP centroid dispersion). The `notna().mean() > 0.5` guard in the updated `_disp_cols` selection ensures only well-populated columns are shown.

4. **Supp A requires Cell 4 to run first.** `rna_batch_palette` is defined in Cell 4 (S3 load cell). If Cell 4 is skipped, Supp A will fail. Add a guard:
   ```python
   if "rna_batch_palette" not in dir():
       rna_batch_palette = {b: "gray" for b in df_ok.index}
   ```

5. **Supp B Sankey fix** only works when `gene_sets` dict is populated (Cell 4 run). Without S3 access, the panel shows a placeholder message instead of failing.

6. **Supp C Panel C** uses `gseapy.enrichr()` which requires internet access. If running on a pod without outbound internet, use the local `_go_db_path` with `goatools` instead.

7. **Fig 7 cell changes Panel numbering.** If any downstream code (e.g., slide generation scripts) references "Panel D = UMAP entropy", update those references to "Supp".

8. **`fig10_metric_star_visualization.py`** uses a different `TOP_IDS` list (slightly different from the notebook's `_top_ids`). After validation, the two lists should be reconciled — but this is not blocking for submission.

---

## Verification Commands

```bash
source ~/venvs/collagen_3_11/bin/activate
cd ~/FL_harmonization/figures_for_article

# 1. Verify NA filter works: expect df_ok shape (2234, ~230)
python -c "
import figures_helpers as fh
from pathlib import Path
df_ok, df_normed, scoring_cols, col_meta = fh.load_metrics_data(
    Path('..') / 'harmonization-metrics' / 'metric_tables' / 'metrics_comprehensive_260609.csv'
)
assert len(df_ok) == 2234, f'Expected 2234 rows, got {len(df_ok)}'
assert '38_harman' not in df_ok['method'].values, '38_harman should be filtered out'
print(f'OK: df_ok={df_ok.shape}, methods={df_ok[\"method\"].nunique()}')
print(f'Methods removed: harman present = {\"38_harman\" in df_ok[\"method\"].values}')
"

# 2. Verify Best 15 assertion still passes after filter
python -c "
import figures_helpers as fh
from pathlib import Path
df_ok, *_ = fh.load_metrics_data(
    Path('..') / 'harmonization-metrics' / 'metric_tables' / 'metrics_comprehensive_260609.csv'
)
top_ids = [
    ('10_mnn','strict','S0_no_removal'), ('10_mnn','strict','H_affymetrix_extended'),
    ('10_mnn','strict','D_malignant_only'), ('04_sva','knn','C_rnaseq_only'),
    ('04_sva','softimpute','C_rnaseq_only'), ('16_fsqn_r','knn','C_rnaseq_only'),
    ('16_fsqn_r','softimpute','C_rnaseq_only'), ('16_fsqn_r','strict','C_rnaseq_only'),
    ('10_mnn','strict','J_ff_only'), ('16_fsqn_r','strict','J_ff_only'),
    ('04_sva','knn','K_ffpe_only'), ('04_sva','strict','K_ffpe_only'),
    ('04_sva','softimpute','K_ffpe_only'), ('13_fsmvn','strict','S0_no_removal'),
    ('33_amdbnorm','strict','S0_no_removal'),
]
top_set = set(top_ids)
df_ok['is_best'] = df_ok.apply(lambda r: (r['method'],r['imp'],r['strat']) in top_set and not r['post_rm'], axis=1)
n_best = df_ok['is_best'].sum()
print(f'Best 15 found: {n_best}')
assert n_best == 15, f'Expected 15, got {n_best}'
"

# 3. Verify centroid dispersion columns available
python -c "
import pandas as pd
from pathlib import Path
df = pd.read_csv(Path('..') / 'harmonization-metrics' / 'metric_tables' / 'metrics_comprehensive_260609.csv')
df_ok = df[df['status'] == 'ok']
df_ok = df_ok[df_ok['pct_samples_allNA'] < 0.05]
disp_cols = [c for c in df_ok.columns if 'centroid_disp' in c]
print(f'centroid_disp columns: {len(disp_cols)}')
for c in disp_cols:
    pct = df_ok[c].notna().mean()
    print(f'  {c}: {pct:.1%} non-null')
"

# 4. Run star visualization script
python fig10_metric_star_visualization.py

# 5. Check output files exist
ls -lh figures/fig*.{svg,png} figures/supplementary/supp*.{svg,png} 2>/dev/null | head -40
```

---

## TODO Checklist

Items are ordered: Critical → High → Medium → Low. Each item is independent and can be checked off separately.

### Critical (prerequisite for all other fixes)

- [x] `figures_helpers.py` — add NA filter using `n_samples_allNA < 5444 * 0.05` after Shambhala filter block (actual column is `n_samples_allNA`, not `pct_samples_allNA`; removes 38_harman + 34_arsyn = 173 rows)
- [x] `figures_helpers.py` — add debug print: `f"NA filter: {n_before} → {len(df_ok)} rows"`
- [x] Verify `python -c "import figures_helpers as fh; ..."` returns 2,234 rows and no 38_harman — CONFIRMED
- [ ] Verify Best 15 assertion passes: `assert len(df_best) == 15` (requires live notebook run)

### Critical (blocking figure correctness)

- [x] Notebook Cell 8 (Fig 8) — replace `_disp_cols` selection with `df_ok.columns` scan using `_disp_covariates` list and `notna().mean() > 0.5` guard — 8 columns found (tSNE + UMAP × 4 covariates)
- [x] Notebook Cell 18 (Supp A) — change bar color source from `_pg_pal` to `rna_batch_palette`
- [x] Notebook Cell 4 (S3 load) — add `rna_batch_palette` derivation from `comb_ann["RNA_BATCH"]`
- [x] Notebook Cell 20 (Supp B) — fix `alpha=0.0` → `alpha=0.55` on flow bands
- [x] Notebook Cell 20 (Supp B) — add `if not gene_sets:` guard with placeholder message
- [x] Notebook Cell 20 (Supp B) — fix label format `f"{imp}\n{len(genes):,} genes"` (label already correct in cell source — verified by reading cell content)

### High (scientific correctness)

- [x] Notebook Cell 6 (Fig 7) — redefine GridSpec: ax_D = tSNE entropy, ax_E = wide local-global scatter (5 panels)
- [x] Notebook Cell 6 (Fig 7) — add `ax_A.set_xscale("symlog", linthresh=0.01)` after kBET strip plot
- [x] Notebook Cell 6 (Fig 7) — add new Supp cell `supp7s_umap_entropy` after Cell 6
- [x] Notebook Cell 8 (Fig 8) — add `ax_C.set_xscale("symlog", linthresh=0.1)` to WaterMelon ratio Panel C
- [ ] Notebook Cell 8 (Fig 8) — remove CMS Panel D from Fig 8; add new Supp cell for CMS (deferred — CMS present in Fig 8D; remove only if Daniil confirms)
- [x] Notebook Cell 10 (Fig 8B) — change Panel A `df_ok.groupby(...)` → `data_v3.groupby(...)` for sorted Best 15
- [x] Notebook Cell 10 (Fig 8B) — change Panel B `df_ok.groupby(...)` → `data_v3.groupby(...)` for sorted Best 15
- [x] Notebook Cell 10 (Fig 8B) — add `ax_A.axvline(Best mean)` reference line
- [x] Notebook Cell 14 (Fig 9) — add LISI-sized scatter overlay to Panel A (iLISI quartile ring sizes)
- [x] Notebook Cell 14 (Fig 9) — add Discussion flag text box to Panel C
- [x] Notebook Cell 14 (Fig 9) — update x-axis count label in Panel A to use `f"{len(df_ok):,}"` dynamically

### Medium (readability and layout)

- [x] Notebook Cell 14 (Fig 9) — fix Panel B title: add `\n` to prevent subtitle overlap; raise suptitle `y=1.04`
- [x] Notebook Cell 14 (Fig 9) — add cumulative sum y-axis note to Panel D (updated y-label text)
- [x] Notebook Cell 16 (Fig 10) — add `_abbrev` dict and replace x-tick labels in Panel D with short names
- [x] Notebook Cell 16 (Fig 10) — fix Panel B x-axis tick labels with line-break formatting (`\n` separator, rotation=45)
- [x] Notebook Cell 16 (Fig 10) — verify Panel A x-axis label uses dynamic `len(_ranked_run_ids)` — CONFIRMED already dynamic
- [x] Notebook Cell 24 (Fig 11) — add algorithm emoji icons to `_L2_LABELS` text strings (⛓ MNN, 🔗 SVA, 📐 FSQN R)
- [x] Notebook Cell 24 (Fig 11) — add icon legend box at bottom of tree (biomaterial + algorithm icons)
- [x] Notebook Cell 18 (Supp A) — add new cell `suppA2_na_samples_per_strategy` barplot (id: suppA2_na_per_strat)
- [x] Notebook Cell 18 (Supp A) — fix bottom panel y-axis `labelsize=max(6, GLOBAL_FONT_SIZE - 3)` (RNA_BATCH tick labels)
- [x] Notebook Cell 22 (Supp C) — add Panel B gene-set accumulation curve code with `gene_sets` guard (done in previous session)
- [x] Notebook Cell 22 (Supp C) — add Panel C GO enrichment code using `gseapy.enrichr()` with local fallback path

### Low (polish)

- [x] Notebook Cell 26 (Supp D) — add post-hoc font enforcement loop: `_ax.tick_params(labelsize=max(7, ...))`
- [x] Notebook Cell 28 (Supp E) — same 7 pt minimum font enforcement
- [x] Notebook Cell 30 (Supp F) — same 7 pt minimum font enforcement
- [x] Notebook Cell 32 (Supp G) — same 7 pt minimum font enforcement
- [x] Notebook Cell 12 (Supp 9) — find incorrect metric prefix; replace with `tsne_centroid_disp_` / `umap_centroid_disp_` (N/A — cell is a pure placeholder with no metric columns used; no prefix to fix)
- [x] Run `python fig10_metric_star_visualization.py` to regenerate star plot with filtered data — 2,234 rows, df_best=15 confirmed
- [x] Confirm all output files saved as both `.svg` and `.png` — all 14 figures have both formats (supp7s_umap_entropy pending live run)
- [x] Verify notebook size stays < 100 MB — notebook is 106 KB (source only, no outputs)
- [x] Update `CLAUDE.md` "Implemented figures" table — added Supp D/E/F/G, Fig 11, Supp 7s; removed from BLOCK 4; added Supp A2 + Fig 1 multipanel as remaining
- [ ] Update `final_figures_inspection_260627.md` Summary Table — mark ⚠️ items as ✅ after fixes verified

---

**Please review and approve before I implement.**
