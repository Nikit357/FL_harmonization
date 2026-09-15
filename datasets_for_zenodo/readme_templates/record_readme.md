# ComboBatch — harmonized transcriptomic matrices and benchmark metrics for germinal-centre B-cell lymphoma

This record accompanies the ComboBatch harmonization study. It contains the expression
layer that the article's GitHub repository deliberately does not carry: the public-cohort
raw matrix, every imputed input matrix, and 911 harmonized matrices — including the
**complete method × strategy × post-removal grid at the `strict` imputation**.

## Contents

| Group | Files | What it holds |
|---|---|---|
| Metric tables | `metrics_comprehensive_260905.csv`, three `*_long_*.csv.gz` tables, `gene_qc_long_260828.csv.gz`, four `gene_gene_consensus_*` matrices, `marker_gene_coverage_by_attempt_260828.csv`, `gene_level_stats_260905.csv`, `marker_gene_annotation.csv` | Every metric for all 2,407 harmonization attempts across 33 methods, plus the marker-gene panel behind the blind check |
| Registries | `metric_dictionary.csv`, `metric_group_definitions.csv`, `methods_registry.csv`, `strategies_registry.csv` | What each metric measures and its polarity; what each method and each removal strategy is |
| Source data | `comb_exp_public.tsv.gz`, `comb_ann_public.csv`, `cohorts.csv`, `sample_selection_by_strategy.csv`, `strategy_sample_counts.csv`, `gene_selection_by_pair.csv.gz` | The unharmonized public matrix, its annotation, and which samples and genes each strategy and imputation kept |
| Imputed inputs | `prepared_inputs__{strict,softimpute,knn}.zip` | The 42 matrices the harmonization methods were given, with their annotation twins |
| Harmonized — complete strict grid | `grid_strict__<strategy>.zip` | 33 methods × 14 strategies × post0 and post1, at the imputation-free setting |
| Harmonized — method and strategy sweeps | `sweep_methods__*.zip`, `sweep_strategies__*.zip` | `softimpute` and `knn` slices through the same grid |
| Harmonized — curated sets | `best15_clustermap_approaches.zip`, `decision_tree_recommended.zip` | The 15 clustermap-derived best approaches and the outputs the article's decision tree recommends. Most of them already sit in the grid and sweep bundles, so these two archives hold only the members that appear nowhere else — use the `is_best15` and `is_decision_tree` columns of `manifest.csv` to find the complete sets |
| Index | `manifest.csv`, `SHA256SUMS.txt` | One row per deposited matrix; checksums of every top-level file |

## Naming

An archive whose name ends in `_part1`, `_part2`, … or `_part1_s1`, `_part1_s2`, … is one
piece of a larger set that was split purely to keep each uploaded file small. The pieces of
a set are disjoint and carry no meaning beyond packaging: to work with the whole set, unpack
every piece into the same directory. `manifest.csv` maps each matrix to the archive holding
it.

Every matrix is named `{strategy}__{imputation}__{method}__post{0,1}.public.tsv.gz`:

- **strategy** — which samples were excluded before harmonization (`strategies_registry.csv`)
- **imputation** — `strict` (only genes measured in every sample), `softimpute`, or `knn`
- **method** — the harmonization method (`methods_registry.csv`)
- **post0 / post1** — without and with post-normalization outlier removal
- **`.public`** — the proprietary rows have been removed; see below

<!-- INCLUDE:_common_caveats.md -->

## Licence

The data in this record are released under **CC BY 4.0** (`LICENSE-CC-BY-4.0.txt`).
The code that produced it is in the accompanying GitHub repository under the MIT
licence. Neither licence extends to the 73 source studies, which keep their own terms.
