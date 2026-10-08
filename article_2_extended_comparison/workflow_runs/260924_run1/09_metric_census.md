# 09 — Metric census and registry-to-snapshot map (Phase 0), 2026-09-25

## Status

**Done.** The census of plan §B5 reproduces exactly. Of the 334 non-metadata metrics, **329
are recoverable** from the pinned snapshot and **5 are not**. The citation invariants of §C1 are
recorded at the bottom of this file.

Produced by `phase0_map_registry_to_snapshot.py` (this folder); the per-metric map is
`09_registry_to_snapshot_map.csv`.

## Sources (read-only)

| Role | File |
|---|---|
| Metric registry (the authority) | `figures_for_article/supplementary_260824/Supplementary File 2.xlsx`, sheet `Metric_polarity` — 344 rows × 6 columns (`Metric`, `Polarity`, `Metric group`, `Metric type`, `Explanation`, `Calculation`) |
| Computed snapshot | `harmonization-metrics/metric_tables/metrics_comprehensive_260905.csv` — 3,835 rows × 329 columns |
| Rename check only | `figures_for_article/supplementary_260824/Supplementary File 3.csv.gz` |

## The census

| Number | Definition | Reproduces |
|---:|---|---|
| **344** | every row of `Metric_polarity`; 344 unique metric names | yes |
| **334** | 344 minus the 10 rows whose `Metric group` is `Metadata` | yes |
| **87** | metrics with non-zero `Polarity`: 51 at `+1`, 36 at `-1` | yes |
| 257 | metrics with `Polarity` 0 (descriptive) | yes, 344 − 87 |

Non-metadata metrics per group: A 61, N 46, B 40, M 35, E 30, L 30, C 24, H 21, D 11, I 11,
J 11, K 10, G 4 (sum 334). By `Metric type`: Global 135, Other 112 (incl. the 10 metadata rows),
Distributional similarity 61, Local 36.

## Registry → snapshot map for the C48 clustermap

| Route | n | What it means |
|---|---:|---|
| `direct` | **303** | the registry name is a numeric column of the snapshot |
| `rename` | **7** | `PCReg_<col>` in the registry is `pcr_<col>` in the snapshot. Checked against Supp. File 3: Spearman ρ = 1.000 for all 7 on the shared keys, so the rename points at the same quantity |
| `derived_percent` | **2** | `pct_samples_allNA` = 100 · `n_samples_allNA` / `n_samples`; `pct_genes_allNA` = 100 · `n_genes_allNA` / `n_genes`. Both inputs are snapshot columns |
| `derived_baseline` | **14** | the 6 `xb_rank_*_{raw,delta}` (group M) and 8 `pv_lobo{2,3}_{f1,auc}_macro_mean_{raw,delta}` (group N) columns. Computed downstream by `figures_helpers.attach_raw_baseline()` from the `01_raw`, `post_rm = False` row of the same (strat, imp) pair; the base metric is a snapshot column |
| `boolean_flag` | **3** | `wm_subsampled`, `xb_subsampled`, `mk_is_self_reference`: present, but boolean. `mk_is_self_reference` is `False` in all 3,835 rows (zero variance) and cannot enter a correlation |
| `absent` | **5** | `xb_rank_agree_{Double_Hit_Lymphoma, Extranodal_Marginal_Zone_Lymphoma, High_Grade_B_Cell_Lymphoma, Mantle_Cell_Lymphoma, Other}` (group M, polarity 0). No snapshot from 260501 to 260905 carries them; they are per-class columns for the rare diagnoses the final cohort excludes |
| **recoverable** | **329** | 303 + 7 + 2 + 14 + 3 |

**All 87 scoring metrics are recoverable** (78 direct, 7 rename, 2 derived percent). Every
unrecoverable metric is descriptive.

**Consequence for the C48 legend.** The clustermap cannot claim 334. The honest ceiling is **329**
columns, and **at most 328** can enter a correlation because `mk_is_self_reference` is constant;
Phase 2 must additionally drop any column that is constant or all-NaN within the 2,234-approach
analysis set, and the legend states the final number used and why.

## Citation invariants of the base document (§C1)

Measured on `manuscript/FL_metric_classes_F1000_260917_edited_Daniil.docx`:

| Object | Count |
|---|---:|
| `MENDELEY_CITATION` occurrences in `word/document.xml` | **46** |
| `w:sdt` elements whose `w:sdtPr` carries the Mendeley tag | **46** |
| Plain numeric brackets in visible text | **4**: `[50,51]`, `[52]`, `[38]`, `[38]` |

In the regenerated master `manuscript/FL_metric_classes_F1000_260924.md` all 46 content-control
texts appear verbatim as author–year strings (e.g. `(Leek et al. 2010)`), and the body carries
the same 4 numeric brackets. Any further `[n]` match in that file comes from the appended
"Comments in document" section, where Word comment ids are printed as `[2]` … `[74]`.
