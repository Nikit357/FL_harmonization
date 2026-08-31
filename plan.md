# Plan: Harmonization Benchmark Notebook

## Objective

Build a Jupyter notebook `collagen_3_11mark.ipynb` that:

1. Applies **all available harmonization tools** to the assembled multi-platform lymphoma dataset
2. Evaluates batch effect **before SOM** (expression space) and **after SOM** (metagene space) using PCA/UMAP/tSNE and quantitative metrics
3. Compares **SOM portrait grids** across methods to visually confirm biological fidelity vs. batch removal
4. Tests **all combinations of sample-removal strategies and normalization methods** (full cross-product) with the constraint that ≤ 1/3 of all samples may be removed (~2,413 samples; ≥ 4,825 retained from 7,238 total)

---

## 0 — Setup

### 0.1 — Imports and global config

Single large cell. All imports and global config. 'I need a set of cells for imports depending on their priority'

```python
# ── Standard ────────────────────────────────────────────────────────────────
import os, warnings, pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns
from tqdm.notebook import tqdm
warnings.filterwarnings("ignore")

# ── Dimensionality reduction ─────────────────────────────────────────────────
from sklearn.manifold import TSNE
from umap import UMAP

# ── R bridge ─────────────────────────────────────────────────────────────────
import rpy2.robjects as ro
from rpy2.robjects import pandas2ri
from rpy2.robjects.packages import importr
pandas2ri.activate()

# ── sklearn ──────────────────────────────────────────────────────────────────
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors

# ── Global plot config ───────────────────────────────────────────────────────
plt.rcParams.update({"pdf.fonttype": "truetype", "svg.fonttype": "none", "figure.dpi": 150})
sns.set_style("ticks")

# ── Paths ─────────────────────────────────────────────────────────────────────
REMOTE_ROOT   = "$FL_DATA_ROOT"
EXP_PATH      = f"{REMOTE_ROOT}/comb_exp.tsv"
ANN_PATH      = "comb_ann_unified.csv"
FSQN_R_PATH   = f"{REMOTE_ROOT}/fsqn_normalized_exp_R.tsv"
ANN_NORM_PATH = f"{REMOTE_ROOT}/ann_normalized_fsqn_R.tsv"
OUT_DIR       = "harmonization_results"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Global annotation column config — change here to affect the whole notebook ──
BIO_COL   = "Diagnosis_cell_type_unified"   # main biology grouping column
BATCH_COL = "RNA_BATCH"                     # batch variable for metrics and correction
```

### 0.2 — Color palettes

The following palettes are defined in Section 0 (notebook cell-4) and passed via
the `palette=` argument to `pca_plot`, `umap_plot`, and `tsne_plot`.

**Grouped legend requirement:** When rendering `rna_batch_palette` or
`lymphoma_ontogeny_palette` legends next to a PCA/UMAP/tSNE plot, display entries
grouped by their in-dictionary comment headings (e.g., *RNASeq Group*,
*Affymetrix Family*, *Agilent Family*, *Illumina Family* for `rna_batch_palette`;
*Normal B-Cells* and *Malignant Types* for `lymphoma_ontogeny_palette`). Each
group is preceded by a bold subtitle; entries within a group are contiguous,
separated from adjacent groups by a visual divider.

The four palettes used across the notebook:

| Variable | Purpose |
|---|---|
| `lymphoma_ontogeny_palette` | Biology grouping: normal B-cell types and lymphoma diagnoses |
| `rna_batch_palette` | RNA_BATCH values: grouped by technology family |
| `cohort_palette` | COHORT_LABEL values: one color per cohort |
| `platform_palette` | PLATFORM_RNA values: one color per platform |

Full palette definitions are maintained in notebook **cell-4**. They must be kept
in sync between the plan and cell-4. The `platform_palette` contains a
`float("nan")` key which requires special handling in `_scatter_grouped` (use
`.get(str(g), ...)` or pre-convert NaN group labels to the string `"nan"`
before lookup).


### 0.3 — Custom plot helpers

Custom dimensionality reduction plot helpers (replaces the internal plotting utilities):

```python
def _scatter_grouped(coords, grouping, palette, legend, ax, title):
    """Shared scatter logic for PCA/UMAP/tSNE plots."""
    ax = ax or plt.gca()
    groups = grouping.values
    unique = pd.unique(groups)
    colors = (palette if isinstance(palette, dict)
              else dict(zip(unique, sns.color_palette("tab20", len(unique)))))
    for g in unique:
        mask = groups == g
        ax.scatter(coords[mask, 0], coords[mask, 1],
                   c=[colors.get(g, "#888888")], s=4, alpha=0.6,
                   label=str(g), linewidths=0)
    if legend != "off" and legend is not False:
        ax.legend(fontsize=5, markerscale=2, bbox_to_anchor=(1.01, 1), loc="upper left")
    if title:
        ax.set_title(title, fontsize=8)
    ax.set_xticks([]); ax.set_yticks([])
    return ax

The `pca_plot` function must label the x-axis as `PC1 (X.X%)` and the y-axis as
`PC2 (X.X%)` where the percentage is the fraction of variance explained by that
principal component. Compute via `pca.explained_variance_ratio_`.

def pca_plot(exp_df, grouping, palette=None, legend=None, ax=None, title=None,
             n_components=2):
    """PCA scatter plot (PC1 vs PC2), colored by grouping."""
    X = StandardScaler().fit_transform(exp_df.fillna(0).values)
    coords = PCA(n_components=n_components, random_state=42).fit_transform(X)
    grouping = grouping.reindex(exp_df.index).fillna("NA")
    return _scatter_grouped(coords, grouping, palette, legend, ax, title)

def umap_plot(exp_df, grouping, palette=None, legend=None, ax=None, title=None,
              n_neighbors=15, min_dist=0.3):
    """UMAP scatter plot, colored by grouping."""
    X = StandardScaler().fit_transform(exp_df.fillna(0).values)
    coords = UMAP(n_neighbors=n_neighbors, min_dist=min_dist,
                  random_state=42).fit_transform(X)
    grouping = grouping.reindex(exp_df.index).fillna("NA")
    return _scatter_grouped(coords, grouping, palette, legend, ax, title)

def tsne_plot(exp_df, grouping, palette=None, legend=None, ax=None, title=None,
              perplexity=30):
    """t-SNE scatter plot, colored by grouping. Runs PCA50 first for speed."""
    X = StandardScaler().fit_transform(exp_df.fillna(0).values)
    n_comp = min(50, X.shape[1] - 1, X.shape[0] - 1)
    X_pca  = PCA(n_components=n_comp, random_state=42).fit_transform(X)
    coords = TSNE(n_components=2, perplexity=min(perplexity, len(X) - 1),
                  random_state=42, init="pca").fit_transform(X_pca)
    grouping = grouping.reindex(exp_df.index).fillna("NA")
    return _scatter_grouped(coords, grouping, palette, legend, ax, title)
```

### 0.4 — Install check

Install check cell (run once):

```python
# ── R packages ───────────────────────────────────────────────────────────────
# BiocManager::install(c("sva","limma","batchelor","RUVSeq","qsmooth","preprocessCore","missForest","softImpute"))
# devtools::install_github("immunogenomics/harmony")
# devtools::install_github("jenniferfranks/FSQN")

# ── Python packages ──────────────────────────────────────────────────────────
# pip install harmonypy combat inmoose scanorama bbknn fancyimpute
```

---

## 1 — Data Loading and Baseline Description
### 1.1 — Data loading

One cell for loading, one for statistics.

```python
# ── Load raw expressions and annotations ─────────────────────────────────────
comb_exp = pd.read_csv(EXP_PATH, sep="\t", index_col=0)
comb_ann = pd.read_csv(ANN_PATH, index_col=0)

print(f"Raw: {comb_exp.shape[0]} samples × {comb_exp.shape[1]} genes")
print(comb_ann[BATCH_COL].value_counts().to_string())
print(comb_ann[BIO_COL].value_counts().to_string())
```

### 1.2 — Baseline batch effect quantification

Baseline batch effect quantification (before any filtering or normalization):

```python
def pca_variance_explained_by_batch(exp_df, batch_series, n_components=10):
    """
    Returns the mean fraction of variance in the first `n_components` PCs
    explained by batch (one-way ANOVA R² averaged across PCs).
    """
    pca    = PCA(n_components=n_components)
    coords = pca.fit_transform(StandardScaler().fit_transform(exp_df.fillna(0)))
    groups = batch_series.reindex(exp_df.index).fillna("NA")
    r2_list = []
    for pc in range(n_components):
        vals       = coords[:, pc]
        grand_mean = vals.mean()
        ss_between = sum(
            len(vals[groups == g]) * (vals[groups == g].mean() - grand_mean) ** 2
            for g in groups.unique() if (groups == g).sum() > 1
        )
        ss_total = ((vals - grand_mean) ** 2).sum()
        r2_list.append(ss_between / ss_total if ss_total > 0 else 0)
    return np.mean(r2_list)

def r2_batch(exp_df, ann_df, batch_col=BATCH_COL, n_pcs=10):
    return pca_variance_explained_by_batch(exp_df, ann_df[batch_col], n_pcs)

baseline_r2 = r2_batch(comb_exp.dropna(axis=1), comb_ann)
print(f"Baseline batch R² in PCA (before normalization): {baseline_r2:.2%}")
```

---

## 2 — Dataset Filtering Strategy

### 2.1. Invariant biological exclusions (always applied)

Rare diagnosis groups are excluded from all downstream analyses regardless of the batch-removal strategy chosen.

```python
RARE_GROUPS = [
    "Extranodal_Marginal_Zone_Lymphoma", "Double_Hit_Lymphoma",
    "Mantle_Cell_Lymphoma", "Chronic_Lymphocytic_Leukemia", "Other",
]

ann_base = comb_ann[~comb_ann[BIO_COL].isin(RARE_GROUPS)].copy()
print(f"After rare-group removal: {len(ann_base)} samples")
```

### 2.2. Sample-removal strategies

Ten strategies are defined, covering the full range from zero removal to platform-level filtering. The hard constraint is **≤ 1/3 of total samples removed** (≤ 2,413; ≥ 4,825 retained from 7,238). Each strategy feeds the same downstream normalization and SOM pipeline so the effect of sample removal can be isolated from the effect of normalization.

```python
TOTAL_SAMPLES = len(comb_ann)
MAX_REMOVE    = TOTAL_SAMPLES // 3          # ≤ 2,413
MIN_RETAINED  = TOTAL_SAMPLES - MAX_REMOVE  # ≥ 4,825

RNASEQ_BATCHES    = [b for b in ann_base[BATCH_COL].unique() if b.startswith("RNASeq")]
MICROARRAY_BATCHES = [b for b in ann_base[BATCH_COL].unique() if not b.startswith("RNASeq")]
AFFYMETRIX_BATCHES = [b for b in ann_base[BATCH_COL].unique() if b.startswith("GPL570")]
NORMAL_GROUPS     = ["Normal_B_cells", "Kassandra"]

def apply_filter(ann, bad_batches=(), bad_cohorts=(), keep_batches=None,
                 keep_groups=None, bio_col=BIO_COL):
    """
    Apply a sample-removal filter.
    keep_batches: if provided, only samples whose BATCH_COL is in keep_batches are retained.
    keep_groups:  if provided, only samples whose bio_col is in keep_groups are retained.
    """
    mask = pd.Series(True, index=ann.index)
    if bad_batches:
        mask &= ~ann[BATCH_COL].isin(bad_batches)
    if bad_cohorts:
        mask &= ~ann["COHORT_LABEL"].isin(bad_cohorts)
    if keep_batches is not None:
        mask &= ann[BATCH_COL].isin(keep_batches)
    if keep_groups is not None:
        mask &= ann[bio_col].isin(keep_groups)
    filtered  = ann[mask]
    n_removed = len(ann_base) - len(filtered)
    pct       = n_removed / TOTAL_SAMPLES
    ok        = n_removed <= MAX_REMOVE
    print(f"  Removed {n_removed} ({pct:.1%}) — {'OK ✓' if ok else 'OVER BUDGET ✗'} "
          f"— retained {len(filtered)}")
    return filtered
```

#### Strategy 0 — No removal (zero baseline)

No batches or cohorts removed beyond the biological rare-group exclusion. Used as the absolute baseline to measure the maximum batch effect before any curation.

```python
ann_S0 = ann_base.copy()
print("Strategy 0 — no removal:")
apply_filter(ann_base)   # just prints stats, ann_S0 = ann_base
```

#### Strategy A — Confirmed bad batches (from prior analysis)

The three FFPE batches and the SOM cohort identified as persistent outliers in `all_cohorts_assembly.ipynb`.

```python
BAD_BATCHES_A = ["GPL14951_FFPE_Unknown", "GPL8432_FFPE_Unknown", "GPL13938_FFPE_Unknown"]
BAD_COHORTS_A = ["SOM"]

print("Strategy A — confirmed bad batches:")
ann_A = apply_filter(ann_base, bad_batches=BAD_BATCHES_A, bad_cohorts=BAD_COHORTS_A)
```

#### Strategy B — Extended bad batches (aggressive)

All FFPE-unknown non-RNASeq batches that were flagged as problematic in qsmooth analysis.

```python
BAD_BATCHES_B = BAD_BATCHES_A + [
    "GPL6244_FFPE_Unknown", "GPL17586_FF_Unknown", "GPL20188_FF_Unknown",
    "GPL23541_FF_Unknown",  "GPL887_FFPE_Unknown",  "GPL26356_FF_Unknown",
    "GPL17047_FF_Unknown",  "GPL6244_FF_Unknown",
]
BAD_COHORTS_B = ["SOM"]

print("Strategy B — extended bad batches:")
ann_B = apply_filter(ann_base, bad_batches=BAD_BATCHES_B, bad_cohorts=BAD_COHORTS_B)
```

#### Strategy C — RNA-seq only

Removes all microarray samples entirely. Most aggressive; eliminates the fundamental microarray/RNA-seq incompatibility but removes ~67% of samples (over budget — included as an upper-bound reference only).

```python
print("Strategy C — RNA-seq only (reference, may exceed budget):")
ann_C = apply_filter(ann_base, keep_batches=RNASEQ_BATCHES)
```

#### Strategy D — Malignancies only (no normal B cells)

Removes all normal B-cell samples (Normal_B_cells + Kassandra). This eliminates the cross-platform batch from normal references and focuses the SOM on the tumour landscape only. Useful for evaluating whether normal B cells are causing the platform batch to dominate.

```python
MALIGNANT_GROUPS = [g for g in ann_base[BIO_COL].unique()
                    if g not in NORMAL_GROUPS]

print("Strategy D — malignancies only (no normal B cells):")
ann_D = apply_filter(ann_base, keep_groups=MALIGNANT_GROUPS)
```

#### Strategy F — Microarray only (all RNA-seq excluded)

Retains only microarray samples and removes all RNA-seq samples. Allows evaluation of batch correction methods in a purely microarray context — eliminates the fundamental technology-type incompatibility from the opposite direction to Strategy C.

```python
print("Strategy F — microarray only (RNA-seq excluded):")
ann_F = apply_filter(ann_base, keep_batches=MICROARRAY_BATCHES)
```

#### Strategy G — Affymetrix GPL570 only

Retains only Affymetrix GPL570 batches (`GPL570_FF_Unknown`, `GPL570_FFPE_Unknown`, `GPL570_Unknown_Unknown`), the largest and most internally consistent microarray platform (~2,800 samples). Useful for within-platform batch correction benchmarking.

```python
print("Strategy G — Affymetrix GPL570 only:")
ann_G = apply_filter(ann_base, keep_batches=AFFYMETRIX_BATCHES)
```

#### Strategies E1–E3 — Iterative PCA-based outlier removal

This family of strategies is data-driven: examine PCA colored by `BATCH_COL`, identify the 1–2 most outlying batches or cohorts in PC space, remove them, reassess, and repeat up to 3 rounds. Each round produces a new strategy (E1, E2, E3).

The iteration stops when either:
- The budget constraint is reached (≤ 1/3 removed), or
- The pre-normalization batch R² falls below a target threshold (e.g. 50%)

```python
def identify_outlier_batches(exp_df, ann_df, batch_col=BATCH_COL,
                              n_pcs=2, n_outliers=2, min_batch_size=20):
    """
    Runs PCA on the expression matrix. For each batch, computes the
    centroid in PC space. Returns the `n_outliers` batches whose centroid
    is furthest from the global centroid (Euclidean distance in PC1–PC2).
    Only considers batches with >= min_batch_size samples.
    """
    common = exp_df.index.intersection(ann_df.index)
    X      = StandardScaler().fit_transform(exp_df.loc[common].fillna(0))
    coords = PCA(n_components=n_pcs).fit_transform(X)
    coords_df = pd.DataFrame(coords, index=common,
                              columns=[f"PC{i+1}" for i in range(n_pcs)])
    batches   = ann_df.loc[common, batch_col].fillna("NA")
    global_centroid = coords_df.mean(axis=0).values

    batch_centroids = {}
    for b in batches.unique():
        idx = batches[batches == b].index
        if len(idx) < min_batch_size:
            continue
        batch_centroids[b] = np.linalg.norm(
            coords_df.loc[idx].mean(axis=0).values - global_centroid
        )

    ranked = sorted(batch_centroids, key=batch_centroids.get, reverse=True)
    outliers = ranked[:n_outliers]
    print(f"  Most outlying batches: {outliers}")
    for b in outliers:
        print(f"    {b}: centroid distance = {batch_centroids[b]:.3f}")
    return outliers

# ── Iterative removal — run interactively, update each round ─────────────────
# Round E1: start from Strategy A
print("\nIterative round E1:")
exp_S0, ann_S0_prep = prepare_dataset(ann_A, comb_exp)
outliers_E1 = identify_outlier_batches(exp_S0, ann_S0_prep)
ann_E1 = apply_filter(ann_A, bad_batches=BAD_BATCHES_A + outliers_E1,
                      bad_cohorts=BAD_COHORTS_A)

# Round E2: continue from E1
print("\nIterative round E2:")
exp_E1, _ = prepare_dataset(ann_E1, comb_exp)
outliers_E2 = identify_outlier_batches(exp_E1, ann_E1)
ann_E2 = apply_filter(ann_E1, bad_batches=outliers_E2)

# Round E3: continue from E2
print("\nIterative round E3:")
exp_E2, _ = prepare_dataset(ann_E2, comb_exp)
outliers_E3 = identify_outlier_batches(exp_E2, ann_E2)
ann_E3 = apply_filter(ann_E2, bad_batches=outliers_E3)
```

After each round, print the pre-normalization batch R² to confirm that removal is actually improving mixing:

```python
for label, ann_iter in [("E1", ann_E1), ("E2", ann_E2), ("E3", ann_E3)]:
    exp_iter, _ = prepare_dataset(ann_iter, comb_exp)
    r2 = r2_batch(exp_iter, ann_iter)
    print(f"  Strategy {label}: {len(ann_iter)} samples, batch R² = {r2:.3f}")
```

Visualise PCA after each round (two subplots: colored by BATCH_COL and by BIO_COL):

```python
for label, ann_iter in [("S0_base", ann_base), ("A", ann_A),
                         ("E1", ann_E1), ("E2", ann_E2), ("E3", ann_E3)]:
    exp_iter, ann_iter_p = prepare_dataset(ann_iter, comb_exp)
    fig, axs = plt.subplots(1, 2, figsize=(14, 5))
    pca_plot(exp_iter, grouping=ann_iter_p[BATCH_COL].fillna("NA"),
             palette=rna_batch_palette, legend=None, ax=axs[0],
             title=f"{label} — RNA_BATCH")
    pca_plot(exp_iter, grouping=ann_iter_p[BIO_COL].fillna("NA"),
             palette=lymphoma_ontogeny_palette, legend=None, ax=axs[1],
             title=f"{label} — {BIO_COL}")
    plt.suptitle(f"Iterative removal — Strategy {label}", fontsize=10)
    plt.tight_layout(); plt.show()
```

All strategies are collected in a registry for downstream loops:

```python
FILTER_STRATEGIES = {
    "S0_no_removal":    ann_S0,
    "A_confirmed_bad":  ann_A,
    "B_extended_bad":   ann_B,
    "C_rnaseq_only":    ann_C,   # reference only, may exceed budget
    "D_malignant_only": ann_D,
    "E1_iterative_r1":  ann_E1,
    "E2_iterative_r2":  ann_E2,
    "E3_iterative_r3":  ann_E3,
    "F_microarray_only": ann_F,
    "G_affymetrix_only": ann_G,
}
```

### 2.3. Per-batch distribution check

Visualize expression distributions per batch to inspect bimodality and flag remaining outliers after each removal strategy.

```python
def plot_batch_distributions(exp_df, ann_df, batch_col=BATCH_COL,
                              ncols=8, figsize=(28, 20), title_prefix=""):
    batches = ann_df[batch_col].value_counts().index
    nrows   = int(np.ceil(len(batches) / ncols))
    fig, axs = plt.subplots(nrows, ncols, figsize=figsize, squeeze=False)
    for ax, batch in zip(axs.flatten(), batches):
        samples = ann_df.index[ann_df[batch_col] == batch]
        vals    = exp_df.reindex(samples).values.ravel()
        vals    = vals[~np.isnan(vals)]
        ax.hist(vals, bins=40, density=True, alpha=0.7, color="steelblue")
        ax.set_title(batch, fontsize=6)
        ax.set_xlim(-2, 18)
    for ax in axs.flatten()[len(batches):]:
        ax.set_visible(False)
    fig.suptitle(f"{title_prefix} Expression distributions per RNA_BATCH", fontsize=10)
    plt.tight_layout()
    return fig

# Run on Strategy A (primary working dataset)
exp_A, ann_A_p = prepare_dataset(ann_A, comb_exp)
plot_batch_distributions(exp_A, ann_A_p, title_prefix="Strategy A —")
plt.show()
```

### 2.4. Gene filtering — strict full-coverage approach

The `prepare_dataset` function applies strict full-coverage filtering: **any gene that has NA in at least one sample in the retained cohort is dropped**. This differs from a loose filter (drop genes where ALL values are NA). The strict approach ensures every normalization method operates on a complete matrix with no imputation.

```python
def prepare_dataset(ann_filter, exp_full):
    """
    Align expression to annotation.
    Drop any gene (column) that has NA in at least one sample — strict full-coverage.
    Deduplicate sample indices.
    """
    common = ann_filter.index.intersection(exp_full.index)
    exp    = exp_full.loc[common]
    # dropna(axis=1) drops any column with at least one NA value
    exp    = exp.dropna(axis=1)
    exp    = exp.loc[~exp.index.duplicated(keep="first")]
    ann    = ann_filter.loc[exp.index]
    print(f"Dataset: {exp.shape[0]} samples × {exp.shape[1]} genes "
          f"(strict full-coverage, 0 NAs)")
    return exp, ann
```

### 2.5. Gene filtering — imputation alternatives

To avoid discarding genes that have only a small fraction of NA values, three imputation methods are offered as alternatives to strict dropping. These are applied on the filtered annotation subset (same samples as `prepare_dataset`) before normalization.

**Top imputation tools used in bulk RNA-seq / microarray bioinformatics:**

| Method | Library | Strategy | Typical use |
|---|---|---|---|
| KNN imputation | `sklearn.impute.KNNImputer` | Replaces NA with weighted mean of k nearest samples in gene expression space | Standard first choice; fast, well-validated on bulk data |
| missForest | R `missForest` package | Iterative random forest imputation; trains a forest per gene | Most accurate on benchmark studies; slow on large matrices |
| softImpute | R `softImpute` / Python `fancyimpute` | Regularised SVD matrix completion (nuclear norm minimisation) | Fast on large sparse matrices; handles systematic block missingness well |

```python
def prepare_dataset_imputed(ann_filter, exp_full, method="knn", knn_k=5,
                             max_na_frac=0.20):
    """
    Align expression to annotation. Keep genes with NA in ≤ max_na_frac of samples.
    Impute remaining NAs using the selected method.

    Parameters
    ----------
    method : "knn" | "missforest" | "softimpute"
    knn_k  : number of neighbours for KNN imputation
    max_na_frac : genes with more NAs than this fraction are dropped before imputation
    """
    from sklearn.impute import KNNImputer

    common = ann_filter.index.intersection(exp_full.index)
    exp    = exp_full.loc[common]
    # Drop genes with too many NAs first
    na_frac = exp.isna().mean(axis=0)
    exp     = exp.loc[:, na_frac <= max_na_frac]
    exp     = exp.loc[~exp.index.duplicated(keep="first")]
    ann     = ann_filter.loc[exp.index]
    n_na_genes = (exp.isna().any(axis=0)).sum()
    print(f"Dataset: {exp.shape[0]} samples × {exp.shape[1]} genes "
          f"({n_na_genes} genes with NAs to impute, method={method})")

    if n_na_genes == 0:
        return exp, ann

    if method == "knn":
        imp    = KNNImputer(n_neighbors=knn_k)
        values = imp.fit_transform(exp.values)
        exp    = pd.DataFrame(values, index=exp.index, columns=exp.columns)

    elif method == "missforest":
        missforest_r = importr("missForest")
        r_mat = pandas2ri.py2rpy(exp)
        result = missforest_r.missForest(r_mat)
        imp_np = pandas2ri.rpy2py(result.rx2("ximp"))
        exp    = pd.DataFrame(imp_np, index=exp.index, columns=exp.columns)

    elif method == "softimpute":
        softimpute_r = importr("softImpute")
        base_r       = importr("base")
        r_mat    = base_r.as_matrix(pandas2ri.py2rpy(exp))
        si_obj   = softimpute_r.softImpute(r_mat, type="svd")
        imp_mat  = softimpute_r.complete(r_mat, si_obj)
        imp_np   = pandas2ri.rpy2py(imp_mat)
        exp      = pd.DataFrame(imp_np, index=exp.index, columns=exp.columns)

    else:
        raise ValueError(f"Unknown imputation method: {method}")

    return exp, ann
```

Prepare all strategies using both strict and imputed approaches:

```python
# Strict approach — default for all normalization benchmarking
datasets = {}
for name, ann_strat in FILTER_STRATEGIES.items():
    print(f"\n── {name} ──")
    exp_s, ann_s = prepare_dataset(ann_strat, comb_exp)
    datasets[name] = (exp_s, ann_s)

# Imputed approaches — evaluate on Strategy A as a representative case
print("\n── Imputation comparison on Strategy A ──")
datasets_imputed = {}
for imp_method in ["knn", "missforest", "softimpute"]:
    exp_s, ann_s = prepare_dataset_imputed(ann_A, comb_exp, method=imp_method)
    datasets_imputed[f"A_{imp_method}"] = (exp_s, ann_s)
    r2 = r2_batch(exp_s.fillna(0), ann_s)
    print(f"  {imp_method}: {exp_s.shape[1]} genes retained, pre-norm batch R²={r2:.3f}")
```

---

## 3 — Harmonization Methods

Methods are ordered from **lowest** to **highest harshness**. Harshness measures how aggressively the method forces different batches to share the same feature distribution:

- **Low harshness** — shifts batch-level location parameters only; preserves relative gene relationships within batches (median scaling, limma, SVA, ComBat)
- **Medium harshness** — corrects both location and scale; may alter gene-level variance (ComBat variants, MNN, Harmony, Scanorama, FSMVN)
- **High harshness** — forces all samples or batches to share an identical distribution; destroys original amplitude information (qsmooth, FSQN, quantile normalization, rank normalization)

Each method is a **self-contained function** returning a `pd.DataFrame` (samples × genes) with the same shape as the input, enabling identical downstream evaluation for all methods. Methods operating in embedding space (Harmony, Scanorama, MNN) recover expression values via inverse PCA projection.

All method functions use `bio_col=BIO_COL` and `batch_col=BATCH_COL` as defaults so changing the global config in Section 0 propagates everywhere automatically.

---

### LOW HARSHNESS

#### Method 1 — Baseline (no normalization)

```python
def normalize_raw(exp_df, ann_df=None, **kw):
    """Passthrough — no normalization. Absolute baseline."""
    return exp_df.copy()
```

#### Method 2 — Median scaling per batch

Subtracts the per-batch per-gene median. Very mild: only corrects the median expression level of each gene within each batch, preserving the full within-batch variance structure. Analogous to median-centering in proteomics.

```python
def normalize_median_scaling(exp_df, ann_df, batch_col=BATCH_COL, **kw):
    """
    Per-batch median centering: for each gene, subtract its median within
    each batch so that all batch medians are aligned to 0.
    Preserves within-batch variance and inter-gene rank order.
    Lowest-harshness correction; acts purely on location, not scale.
    """
    groups = ann_df.loc[exp_df.index, batch_col].fillna("Unknown")
    out    = exp_df.copy()
    global_median = exp_df.median(axis=0)
    for g in groups.unique():
        idx          = exp_df.index[groups == g]
        batch_median = exp_df.loc[idx].median(axis=0)
        shift        = global_median - batch_median
        out.loc[idx] = exp_df.loc[idx].add(shift, axis=1)
    return out
```

#### Method 3 — limma removeBatchEffect (R)

Linear model subtraction of batch mean effects. Appropriate for visualization; equivalent to including batch in a design matrix.

```python
def normalize_limma(exp_df, ann_df, batch_col=BATCH_COL, **kw):
    """
    limma::removeBatchEffect (Ritchie et al. 2015, Nucleic Acids Research).
    Linear subtraction of batch means. BiocManager::install('limma')
    """
    limma_r = importr("limma")
    base_r  = importr("base")
    batches = ann_df.loc[exp_df.index, batch_col].astype(str).values
    r_mat   = base_r.as_matrix(pandas2ri.py2rpy(exp_df.T))
    result  = limma_r.removeBatchEffect(r_mat, batch=ro.StrVector(batches))
    result_np = result if isinstance(result, np.ndarray) else pandas2ri.rpy2py(result)
    return pd.DataFrame(result_np.T, index=exp_df.index, columns=exp_df.columns)
```

#### Method 4 — SVA (Surrogate Variable Analysis, R)

Detects unknown hidden confounders without requiring explicit batch labels; corrects for estimated surrogate variables.

```python
def normalize_sva(exp_df, ann_df, bio_col=BIO_COL, **kw):
    """
    Surrogate Variable Analysis (Leek & Storey 2012, PNAS).
    Detects hidden confounders; corrects expression by removing SV contributions.
    BiocManager::install('sva')
    """
    sva_r   = importr("sva")
    limma_r = importr("limma")
    base_r  = importr("base")
    bio     = ann_df.loc[exp_df.index, bio_col].fillna("Unknown").astype(str).values
    r_mat   = base_r.as_matrix(pandas2ri.py2rpy(exp_df.T))
    r_bio   = ro.StrVector(bio)
    mod     = ro.r["model.matrix"](ro.Formula("~r_bio"), data=ro.DataFrame({"r_bio": r_bio}))
    mod0    = ro.r["model.matrix"](ro.Formula("~1"),     data=ro.DataFrame({"r_bio": r_bio}))
    n_sv    = sva_r.num_sv(r_mat, mod)
    if int(n_sv[0]) == 0:
        print("SVA: 0 surrogate variables detected — returning uncorrected data")
        return exp_df.copy()
    sv_obj  = sva_r.sva(r_mat, mod, mod0, n_sv=n_sv)
    svs     = pandas2ri.rpy2py(sv_obj.rx2("sv"))
    result  = limma_r.removeBatchEffect(
        r_mat, covariates=ro.r["t"](pandas2ri.py2rpy(pd.DataFrame(svs, index=exp_df.index)))
    )
    result_np = result if isinstance(result, np.ndarray) else pandas2ri.rpy2py(result)
    return pd.DataFrame(result_np.T, index=exp_df.index, columns=exp_df.columns)
```

---

### MEDIUM HARSHNESS

#### Method 5 — ComBat (R, sva package)

Empirical Bayes parametric correction of batch mean and variance. Gold standard for microarray data.

```python
def normalize_combat(exp_df, ann_df, batch_col=BATCH_COL,
                     bio_col=BIO_COL, **kw):
    """
    ComBat Empirical Bayes batch correction (Johnson et al. 2007).
    BiocManager::install('sva')
    Operates on log-space expression (microarray + log-transformed RNA-seq).
    Protects biological group as a covariate.
    """
    sva_r  = importr("sva")
    base_r = importr("base")
    batches = ann_df.loc[exp_df.index, batch_col].astype(str).values
    bio     = ann_df.loc[exp_df.index, bio_col].fillna("Unknown").astype(str).values
    r_mat   = base_r.as_matrix(pandas2ri.py2rpy(exp_df.T))
    r_bio   = ro.StrVector(bio)
    mod     = ro.r["model.matrix"](ro.Formula("~r_bio"), data=ro.DataFrame({"r_bio": r_bio}))
    result  = sva_r.ComBat(dat=r_mat, batch=ro.StrVector(batches), mod=mod)
    result_np = result if isinstance(result, np.ndarray) else pandas2ri.rpy2py(result)
    return pd.DataFrame(result_np.T, index=exp_df.index, columns=exp_df.columns)
```

#### Method 6 — ComBat-seq (R, sva package)

ComBat for RNA-seq count data using a negative binomial model.

```python
def normalize_combat_seq(exp_df, ann_df, batch_col=BATCH_COL,
                          bio_col=BIO_COL, **kw):
    """
    ComBat-seq (Zhang et al. 2020, NAR Genomics & Bioinformatics).
    BiocManager::install('sva')
    Expects integer counts; use on RNA-seq batches. For microarray values,
    the wrapper rounds to integers as a pragmatic approximation.
    """
    sva_r  = importr("sva")
    base_r = importr("base")
    batches = ann_df.loc[exp_df.index, batch_col].astype(str).values
    bio     = ann_df.loc[exp_df.index, bio_col].fillna("Unknown").astype(str).values
    counts  = np.round(exp_df.values).astype(int).clip(0)
    r_mat   = base_r.as_matrix(pandas2ri.py2rpy(
                  pd.DataFrame(counts.T, index=exp_df.columns, columns=exp_df.index)))
    result  = sva_r.ComBat_seq(counts=r_mat,
                                batch=ro.StrVector(batches),
                                group=ro.StrVector(bio))
    result_np = result if isinstance(result, np.ndarray) else pandas2ri.rpy2py(result)
    return pd.DataFrame(result_np.T, index=exp_df.index, columns=exp_df.columns)
```

#### Method 7 — pyComBat (Python)

Pure-Python Empirical Bayes ComBat. No rpy2 dependency.

```python
# pip install combat

def normalize_pycombat(exp_df, ann_df, batch_col=BATCH_COL, **kw):
    """
    pyComBat: Python port of ComBat (Müller et al. 2023, BMC Bioinformatics).
    pip install combat. Input: genes × samples; returns samples × genes.
    """
    from combat.pycombat import pycombat
    batches = ann_df.loc[exp_df.index, batch_col].fillna("Unknown").tolist()
    result  = pycombat(exp_df.T, batches)
    return result.T
```

#### Method 8 — InMoose / pycombat_seq (Python)

Python port of ComBat-seq. Only Python implementation of count-based ComBat as of 2025.

```python
# pip install inmoose

def normalize_inmoose_combat_seq(exp_df, ann_df, batch_col=BATCH_COL,
                                  bio_col=BIO_COL, **kw):
    """
    pycombat_seq via InMoose (Colom-Díaz et al. 2025, Scientific Reports).
    pip install inmoose
    """
    from inmoose.pycombat import pycombat_seq
    batches = ann_df.loc[exp_df.index, batch_col].fillna("Unknown").tolist()
    bio     = ann_df.loc[exp_df.index, bio_col].fillna("Unknown").tolist()
    counts  = np.round(exp_df.values).astype(int).clip(0)
    result  = pycombat_seq(counts.T, batch=batches, group=bio)
    return pd.DataFrame(result.T, index=exp_df.index, columns=exp_df.columns)
```

#### Method 9 — RUVSeq (Removal of Unwanted Variation, R)

Uses housekeeping genes as negative controls to estimate and remove unwanted variation factors.

```python
def normalize_ruv(exp_df, ann_df, k=2, **kw):
    """
    RUVg (Risso et al. 2014). BiocManager::install('RUVSeq')
    Uses ACTB, GAPDH, B2M, HPRT1, RPL13A, SDHA, UBC, YWHAZ, HMBS, TBP
    as negative control housekeeping genes.
    """
    ruvseq_r    = importr("RUVSeq")
    base_r      = importr("base")
    HOUSEKEEPING = ["ACTB", "GAPDH", "B2M", "HPRT1", "RPL13A",
                    "SDHA", "UBC", "YWHAZ", "HMBS", "TBP"]
    ctrl_genes  = [g for g in HOUSEKEEPING if g in exp_df.columns]
    if len(ctrl_genes) < 3:
        print(f"RUV: only {len(ctrl_genes)} control genes found — skipping")
        return exp_df.copy()
    counts  = np.round(exp_df.values).astype(int).clip(0)
    r_counts = base_r.as_matrix(pandas2ri.py2rpy(
                   pd.DataFrame(counts.T, index=exp_df.columns, columns=exp_df.index)))
    ctrl_idx = ro.IntVector([list(exp_df.columns).index(g) + 1 for g in ctrl_genes])
    ruv_obj  = ruvseq_r.RUVg(r_counts, cIdx=ctrl_idx, k=k)
    norm_counts = pandas2ri.rpy2py(ruv_obj.rx2("normalizedCounts"))
    return pd.DataFrame(norm_counts.T, index=exp_df.index, columns=exp_df.columns)
```

#### Method 10 — MNN (Mutual Nearest Neighbours, R batchelor)

Locally corrects batch effects by aligning mutual nearest neighbour pairs across batches.

```python
def normalize_mnn(exp_df, ann_df, batch_col=BATCH_COL, k=20, **kw):
    """
    fastMNN (Haghverdi et al. 2018, Nature Biotechnology).
    BiocManager::install('batchelor')
    Corrected embedding is inverse-projected back to expression space.
    """
    batchelor_r = importr("batchelor")
    base_r      = importr("base")
    batches = ann_df.loc[exp_df.index, batch_col].astype(str)
    r_mat   = base_r.as_matrix(pandas2ri.py2rpy(exp_df.T))
    result  = batchelor_r.fastMNN(r_mat, batch=ro.StrVector(batches.values), k=k)
    corrected_embed = pandas2ri.rpy2py(
        ro.r["as.matrix"](ro.r["reducedDim"](result, "corrected")))
    pca       = PCA(n_components=corrected_embed.shape[1]).fit(exp_df.values)
    recovered = corrected_embed @ pca.components_ + pca.mean_
    return pd.DataFrame(recovered, index=exp_df.index, columns=exp_df.columns)
```

#### Method 11 — Harmony (Python, harmonypy)

Iterative PCA-space correction. Originally designed for single-cell; adapted here for bulk with inverse PCA reconstruction.

```python
# pip install harmonypy

def normalize_harmony(exp_df, ann_df, batch_col=BATCH_COL, n_pcs=50, **kw):
    """
    Harmony (Korsunsky et al. 2019, Nature Methods). pip install harmonypy
    Corrects in PCA space; recovered via inverse PCA transform.
    """
    import harmonypy as hm
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(exp_df.fillna(0).values)
    pca      = PCA(n_components=min(n_pcs, exp_df.shape[1] - 1))
    coords   = pca.fit_transform(X_scaled)
    meta     = ann_df.loc[exp_df.index, [batch_col]].fillna("Unknown")
    harmony  = hm.run_harmony(coords, meta, vars_use=batch_col, max_iter_harmony=20)
    recovered = pca.inverse_transform(harmony.Z_corr.T)
    recovered = scaler.inverse_transform(recovered)
    return pd.DataFrame(recovered, index=exp_df.index, columns=exp_df.columns)
```

#### Method 12 — Scanorama (Python)

Panoramic stitching via randomised SVD MNN. Inverse-projected back to expression space.

```python
# pip install scanorama

def normalize_scanorama(exp_df, ann_df, batch_col=BATCH_COL, **kw):
    """
    Scanorama (Hie et al. 2019). pip install scanorama
    Integrated embedding inverse-projected to expression space.
    """
    import scanorama
    batches    = ann_df.loc[exp_df.index, batch_col].fillna("Unknown")
    datasets   = [exp_df.loc[batches == b].values for b in batches.unique()]
    genes_list = [list(exp_df.columns)] * len(datasets)
    integrated, _ = scanorama.integrate(datasets, genes_list, dimred=50)
    all_coords = np.zeros((len(exp_df), integrated[0].shape[1]))
    for b_idx, b in enumerate(batches.unique()):
        mask = (batches == b).values
        all_coords[mask] = integrated[b_idx]
    pca       = PCA(n_components=integrated[0].shape[1]).fit(exp_df.fillna(0).values)
    recovered = all_coords @ pca.components_ + pca.mean_
    return pd.DataFrame(recovered, index=exp_df.index, columns=exp_df.columns)
```

#### Method 13 — FSMVN (Feature-Specific Mean-Variance Normalization)

Corrects both the mean and variance of each gene per batch. Included as a medium-harshness negative control: prior analysis shows it fails to align distributions.

```python
def normalize_fsmvn(exp_df, ann_df, batch_col=BATCH_COL,
                    target_group="RNASeq_FF_PolyA", **kw):
    """
    Feature-Specific Mean-Variance Normalization (custom).
    Prior analysis: fails to align distributions — negative control.
    """
    groups = ann_df.loc[exp_df.index, batch_col]
    ref    = exp_df.loc[groups == target_group] if target_group in groups.values else exp_df
    t_mean = ref.mean(axis=0)
    t_std  = ref.std(axis=0).replace(0, 1)
    out = exp_df.copy()
    for g in groups.unique():
        idx   = exp_df.index[groups == g]
        grp   = exp_df.loc[idx]
        g_std = grp.std(axis=0).replace(0, 1)
        out.loc[idx] = (grp - grp.mean(axis=0)) / g_std * t_std + t_mean
    return out
```

---

### HIGH HARSHNESS

#### Method 14 — qsmooth (R, Bioconductor)

Smooth quantile normalization per group. Forces distributions to be similar while smoothly interpolating between groups.

```python
def normalize_qsmooth(exp_df, ann_df, batch_col=BATCH_COL, **kw):
    """
    Smooth quantile normalization (Hicks et al. 2018, Biostatistics).
    BiocManager::install('qsmooth')
    Accounts for between-group distributional differences.
    """
    qsmooth_r = importr("qsmooth")
    base_r    = importr("base")
    groups = ann_df.loc[exp_df.index, batch_col].astype(str).values
    r_mat  = base_r.as_matrix(pandas2ri.py2rpy(exp_df.T))
    qs_obj = qsmooth_r.qsmooth(r_mat, group_factor=ro.StrVector(groups))
    result = pandas2ri.rpy2py(qsmooth_r.qsmoothData(qs_obj))
    return pd.DataFrame(result.T, index=exp_df.index, columns=exp_df.columns)
```

#### Method 15 — FSQN Python (custom implementation)

Feature-specific quantile normalization targeting RNASeq_FF_PolyA. Already present in `all_cohorts_assembly.ipynb`.

```python
def normalize_fsqn_py(exp_df, ann_df, batch_col=BATCH_COL,
                       target_group="RNASeq_FF_PolyA", **kw):
    """
    FSQN Python implementation (Franks et al. 2018, Biostatistics).
    Matches per-gene distribution of each batch to the target batch.
    """
    groups = ann_df.loc[exp_df.index, batch_col]
    out    = exp_df.copy()
    target_dist = (np.sort(exp_df.loc[groups == target_group].values, axis=1).mean(axis=0)
                   if target_group in groups.values
                   else np.sort(exp_df.values, axis=1).mean(axis=0))
    for g in groups.unique():
        idx = exp_df.index[groups == g]
        for sample in idx:
            vals  = exp_df.loc[sample].values
            order = np.argsort(vals)
            out.loc[sample].iloc[order] = target_dist
    return out
```

#### Method 16 — FSQN R package ★ (selected best from prior analysis)

The R package implementation, which achieved 16% residual batch R² — the best result in the prior benchmark.

```python
def normalize_fsqn_r(exp_df, ann_df, batch_col=BATCH_COL,
                      target_group="RNASeq_FF_PolyA", **kw):
    """
    FSQN via original R package (Franks et al. 2018).
    devtools::install_github('jenniferfranks/FSQN')
    ★ Selected best method from prior analysis: 16% residual batch PCA R².
    """
    fsqn_r = importr("FSQN")
    base_r = importr("base")
    groups = ann_df.loc[exp_df.index, batch_col].astype(str)
    target_mask = (groups == target_group) if target_group in groups.values \
                  else pd.Series(True, index=exp_df.index)
    target_mat = base_r.as_matrix(pandas2ri.py2rpy(exp_df.loc[target_mask].T))
    query_mat  = base_r.as_matrix(pandas2ri.py2rpy(exp_df.T))
    result     = fsqn_r.quantileNormalizeByFeature(query_mat, target_mat)
    result_np  = result if isinstance(result, np.ndarray) else pandas2ri.rpy2py(result)
    return pd.DataFrame(result_np.T, index=exp_df.index, columns=exp_df.columns)
```

#### Method 17 — Standard Quantile Normalization

Forces all samples to share an identical distribution. No external dependency.

```python
def normalize_quantile(exp_df, ann_df=None, **kw):
    """
    Standard quantile normalization (Bolstad et al. 2003).
    Highest harshness: completely destroys cross-sample amplitude differences.
    """
    X      = exp_df.values.copy().astype(float)
    rank   = np.argsort(np.argsort(X, axis=1), axis=1)
    target = np.sort(X, axis=1).mean(axis=0)
    return pd.DataFrame(target[rank], index=exp_df.index, columns=exp_df.columns)
```

#### Method 18 — Rank normalization

Replaces expression values with within-sample ranks (0–1 scaled). Maximum harshness: preserves only ordinal gene relationships. Platform-independent; used by the internal B-cell classifiers.

```python
def normalize_rank(exp_df, ann_df=None, **kw):
    """
    Rank-transforms each sample to 0–1 fractional ranks.
    Maximum harshness: only ordinal information preserved.
    Used internally by the internal B-cell classifiers for platform independence.
    """
    ranked = exp_df.rank(axis=1, method="average", na_option="keep")
    return ranked / (exp_df.notna().sum(axis=1).values[:, None] + 1)
```

---

### Method registry (ordered low → high harshness)

```python
METHODS = {
    # ── Low harshness ──────────────────────────────────────────────────────
    "01_raw":               (normalize_raw,               "low"),
    "02_median_scaling":    (normalize_median_scaling,     "low"),
    "03_limma":             (normalize_limma,              "low"),
    "04_sva":               (normalize_sva,                "low"),
    # ── Medium harshness ───────────────────────────────────────────────────
    "05_combat":            (normalize_combat,             "medium"),
    "06_combat_seq":        (normalize_combat_seq,         "medium"),
    "07_pycombat":          (normalize_pycombat,           "medium"),
    "08_inmoose_combatseq": (normalize_inmoose_combat_seq, "medium"),
    "09_ruv":               (normalize_ruv,                "medium"),
    "10_mnn":               (normalize_mnn,                "medium"),
    "11_harmony":           (normalize_harmony,            "medium"),
    "12_scanorama":         (normalize_scanorama,          "medium"),
    "13_fsmvn":             (normalize_fsmvn,              "medium"),   # negative control
    # ── High harshness ─────────────────────────────────────────────────────
    "14_qsmooth":           (normalize_qsmooth,            "high"),
    "15_fsqn_py":           (normalize_fsqn_py,            "high"),
    "16_fsqn_r":            (normalize_fsqn_r,             "high"),    # ★ prior best
    "17_quantile":          (normalize_quantile,           "high"),
    "18_rank":              (normalize_rank,               "high"),
}

HARSHNESS_COLORS = {"low": "#4da6ff", "medium": "#ff9933", "high": "#cc0000"}
```

---

## 4 — Full Cross-Product Evaluation

The benchmark uses a **4-dimensional cross-product** covering all combinations of:

| Dimension | Options | Count |
|---|---|---|
| **D1** — Sample-removal strategy | S0, A, B, C, D, E1, E2, E3, F, G | 10 |
| **D2** — Imputation approach | none (strict drop), KNN, missForest, softImpute | 4 |
| **D3** — Harmonization method | 18 methods (low → medium → high harshness) | 18 |
| **D4** — Post-harmonization outlier removal | skip / apply `identify_outlier_batches` once | 2 |

Total combinations: **10 × 4 × 18 × 2 = 1,440**.

Pipeline order within each combination:
1. Apply sample-removal strategy (D1) → `ann_strat`
2. Apply imputation approach (D2) → `exp_s` (strict drop or imputed)
3. Apply harmonization method (D3) → `exp_norm`
4. Optionally apply one round of post-harmonization outlier-batch removal (D4):
   call `identify_outlier_batches(exp_norm, ann_s)`, drop the returned batches,
   re-align expression to the reduced annotation.
5. Compute batch R² and diagnosis R² on the final `exp_norm`.

The `cross_results` dict uses a 4-tuple key:
`cross_results[(strategy, imputation, method, post_removal)]`.

Results are summarised as a multi-dimensional heatmap collapsed along each axis.
Top `TOP_K_SOM` combinations (ranked by pre-SOM batch R²) carry forward to SOM.

### 4.1. Run full cross-product and compute metrics

```python
# cross_results[strategy_name][method_name] = {"exp": df, "r2_batch": float, "r2_diag": float, "harshness": str}
cross_results = {}

for strat_name, ann_strat in tqdm(FILTER_STRATEGIES.items(), desc="Strategies"):
    exp_s, ann_s = datasets[strat_name]
    cross_results[strat_name] = {}
    for method_name, (fn, harshness) in METHODS.items():
        try:
            exp_norm = fn(exp_s, ann_s, batch_col=BATCH_COL, bio_col=BIO_COL)
            r2_b = r2_batch(exp_norm, ann_s, batch_col=BATCH_COL)
            r2_d = r2_batch(exp_norm, ann_s, batch_col=BIO_COL)
            cross_results[strat_name][method_name] = {
                "exp": exp_norm, "r2_batch": r2_b, "r2_diag": r2_d, "harshness": harshness
            }
        except Exception as e:
            print(f"  FAILED {strat_name} × {method_name}: {e}")
            cross_results[strat_name][method_name] = {
                "exp": None, "r2_batch": np.nan, "r2_diag": np.nan, "harshness": harshness
            }
```

### 4.2. Cross-product batch R² heatmap

```python
# Build strategy × method matrix
batch_r2_matrix = pd.DataFrame(
    {strat: {meth: cross_results[strat][meth]["r2_batch"]
             for meth in METHODS}
     for strat in FILTER_STRATEGIES}
).T   # shape: strategies × methods

diag_r2_matrix = pd.DataFrame(
    {strat: {meth: cross_results[strat][meth]["r2_diag"]
             for meth in METHODS}
     for strat in FILTER_STRATEGIES}
).T

fig, axs = plt.subplots(1, 2, figsize=(22, 6))
sns.heatmap(batch_r2_matrix.astype(float), ax=axs[0], cmap="RdYlGn_r",
            vmin=0, vmax=1, annot=True, fmt=".2f", linewidths=0.3,
            cbar_kws={"label": "Batch R² (↓ better)"})
axs[0].set_title("Pre-SOM Batch R² — Strategy × Method")
axs[0].set_xlabel("Normalization method"); axs[0].set_ylabel("Filtering strategy")

sns.heatmap(diag_r2_matrix.astype(float), ax=axs[1], cmap="RdYlGn",
            vmin=0, vmax=0.5, annot=True, fmt=".2f", linewidths=0.3,
            cbar_kws={"label": f"{BIO_COL} R² (↑ better)"})
axs[1].set_title(f"Pre-SOM Diagnosis R² — Strategy × Method")
axs[1].set_xlabel("Normalization method"); axs[1].set_ylabel("Filtering strategy")

plt.tight_layout()
plt.savefig(f"{OUT_DIR}/crossproduct_heatmap.pdf", bbox_inches="tight")
plt.show()

batch_r2_matrix.to_csv(f"{OUT_DIR}/crossproduct_batch_r2.csv")
diag_r2_matrix.to_csv(f"{OUT_DIR}/crossproduct_diag_r2.csv")
```

### 4.3. Summary bar chart per method (across strategies, with harshness colour coding)

```python
# Show mean batch R² per method across all strategies
mean_batch_r2 = batch_r2_matrix.mean(axis=0).sort_values()
colors_bar = [HARSHNESS_COLORS[METHODS[m][1]] for m in mean_batch_r2.index]

fig, ax = plt.subplots(figsize=(14, 5))
ax.bar(range(len(mean_batch_r2)), mean_batch_r2.values, color=colors_bar, alpha=0.85)
ax.set_xticks(range(len(mean_batch_r2)))
ax.set_xticklabels(mean_batch_r2.index, rotation=40, ha="right", fontsize=8)
ax.axhline(0.16, ls="--", lw=1, color="gray", label="FSQN R baseline (16%)")
from matplotlib.patches import Patch
legend_patches = [Patch(color=c, label=l) for l, c in HARSHNESS_COLORS.items()]
ax.legend(handles=legend_patches)
ax.set_ylabel("Mean batch R² across all strategies"); ax.set_title("Pre-SOM Method Ranking")
plt.tight_layout(); plt.show()
```

### 4.4. Select top combinations for SOM

```python
TOP_K_SOM = 15   # number of strategy+method combinations to carry forward to SOM

# Flatten cross-product into ranked list of (strategy, method, batch_r2)
combo_rows = []
for strat in FILTER_STRATEGIES:
    for meth in METHODS:
        r2 = cross_results[strat][meth]["r2_batch"]
        if not np.isnan(r2):
            combo_rows.append({"strategy": strat, "method": meth,
                                "r2_batch": r2,
                                "harshness": METHODS[meth][1],
                                "n_samples": len(datasets[strat][1])})

combo_df = (pd.DataFrame(combo_rows)
              .sort_values("r2_batch")
              .reset_index(drop=True))

top_combos = combo_df.head(TOP_K_SOM)
print(f"Top {TOP_K_SOM} strategy+method combinations selected for SOM:")
print(top_combos[["strategy", "method", "r2_batch", "harshness", "n_samples"]].to_string())
```

### 4.5. PCA / UMAP / tSNE for top combinations

Six coloring variables are used. **BATCH_COL** and **BIO_COL** are the two primary variables for assessing batch removal and biological signal preservation respectively. The remaining four are secondary.

```python
PRIMARY_COLS = [
    (BATCH_COL,   rna_batch_palette),
    (BIO_COL,     lymphoma_ontogeny_palette),
]

SECONDARY_COLS = [
    ("PLATFORM_RNA",  platform_palette),
    ("RNASEQ_SOURCE", None),               # FF vs FFPE
    ("TUMOR_NORMAL",  None),
    ("Major_group",   lymphoma_ontogeny_palette),
]

COLOR_COLS = PRIMARY_COLS + SECONDARY_COLS

for col, pal in COLOR_COLS:
    combos_to_show = top_combos if (col, pal) in PRIMARY_COLS \
                     else top_combos.head(8)
    n_combos = len(combos_to_show)

    fig, axs = plt.subplots(n_combos, 3,
                             figsize=(18, 3.5 * n_combos),
                             squeeze=False)
    for row, combo_row in combos_to_show.iterrows():
        strat, meth = combo_row["strategy"], combo_row["method"]
        label    = f"{strat} × {meth}"
        exp_norm = cross_results[strat][meth]["exp"]
        ann_s    = datasets[strat][1]
        grouping = ann_s.loc[exp_norm.index, col].fillna("NA")
        pca_plot(exp_norm,  grouping=grouping, palette=pal, legend=None,
                 ax=axs[row, 0], title=f"{label} — PCA")
        umap_plot(exp_norm, grouping=grouping, palette=pal, legend=None,
                  ax=axs[row, 1], title=f"{label} — UMAP")
        tsne_plot(exp_norm, grouping=grouping, palette=pal, legend=None,
                  ax=axs[row, 2], title=f"{label} — tSNE")
    fig.suptitle(f"Pre-SOM Top Combinations — Color: {col}", fontsize=11)
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/pre_som_top_{col}.pdf", bbox_inches="tight")
    plt.show()
```

### 4f. Expression distribution comparison (per-batch histograms) for top combinations

```python
def distribution_panel_comparison(combo_list, cross_res, datasets_dict,
                                   batch_col=BATCH_COL):
    batches   = comb_ann[batch_col].value_counts().head(20).index
    n_combos  = len(combo_list)
    n_batches = len(batches)
    fig, axs  = plt.subplots(n_combos, n_batches,
                              figsize=(n_batches * 1.5, n_combos * 1.2),
                              squeeze=False)
    for mi, (_, row) in enumerate(combo_list.iterrows()):
        strat, meth  = row["strategy"], row["method"]
        exp_norm     = cross_res[strat][meth]["exp"]
        ann_s        = datasets_dict[strat][1]
        harshness    = METHODS[meth][1]
        for bi, batch in enumerate(batches):
            ax   = axs[mi, bi]
            samp = ann_s.index[ann_s[batch_col] == batch]
            vals = exp_norm.reindex(samp).values.ravel()
            vals = vals[~np.isnan(vals)]
            ax.hist(vals, bins=30, density=True, alpha=0.75,
                    color=HARSHNESS_COLORS[harshness])
            if mi == 0: ax.set_title(batch[:16], fontsize=5, rotation=30)
            if bi == 0: ax.set_ylabel(f"{strat[:12]}\n{meth[:12]}", fontsize=5)
            ax.set_xlim(-2, 18); ax.tick_params(labelsize=4)
    plt.suptitle("Expression distributions per batch × top combinations", fontsize=9)
    plt.tight_layout()
    return fig

distribution_panel_comparison(top_combos, cross_results, datasets)
plt.show()
```

---

## 5 — SOM Analysis Per Top Combination

**oposSOM is run only for the top `TOP_K_SOM` strategy+method combinations** ranked by pre-SOM batch R². This reflects the practical reality that SOM analysis takes ~40 min per run.

### 5.1. Shared oposSOM runner (optional limma pre-correction + oposSOM)

```python
def run_som(exp_norm, ann_df, run_name,
            group_col=BIO_COL, apply_limma=True):
    """
    Full SOM pipeline: optional limma batch correction → oposSOM → metagene extraction.
    All oposSOM outputs (PDFs, HTML reports) are written to OUT_DIR/{run_name}/.
    Returns metagenes_df (metagenes × samples).
    """
    opossom_r = importr("oposSOM")
    limma_r   = importr("limma")
    base_r    = importr("base")
    common = exp_norm.index.intersection(ann_df.index)
    X      = exp_norm.loc[common].dropna(axis=1)
    ann    = ann_df.loc[X.index]
    if apply_limma:
        r_mat   = base_r.as_matrix(pandas2ri.py2rpy(X.T))
        batches = ro.StrVector(ann[BATCH_COL].astype(str).values)
        X_r     = limma_r.removeBatchEffect(r_mat, batch=batches)
        X_np    = X_r if isinstance(X_r, np.ndarray) else pandas2ri.rpy2py(X_r)
        X       = pd.DataFrame(X_np.T, index=X.index, columns=X.columns)
    r_X    = base_r.as_matrix(pandas2ri.py2rpy(X.T))
    groups = ann[group_col].astype(str).values
    out_dir  = f"{OUT_DIR}/{run_name}"
    orig_dir = os.getcwd()
    os.makedirs(out_dir, exist_ok=True)
    os.chdir(out_dir)
    pref = ro.ListVector({
        "dataset.name":                  "MyCohort+",
        "dim.1stLvlSom":                 "automatic",
        "standard.spot.modules":         "kmeans",
        "adjust.expression.values":      False,
        "feature.centralization":        True,
        "sample.quantile.normalization": True,
    })
    env = opossom_r.opossom_new(pref)
    env["indata"]       = r_X
    env["group.labels"] = ro.StrVector(groups)
    opossom_r.opossom_run(env)
    os.chdir(orig_dir)
    meta_r  = env["metadata"]
    meta_np = meta_r if isinstance(meta_r, np.ndarray) else pandas2ri.rpy2py(meta_r)
    meta_df = pd.DataFrame(meta_np, columns=X.index)
    meta_df.index = [f"M{i+1}" for i in range(meta_df.shape[0])]
    return meta_df, ann
```

### 5.2. Run SOM for top combinations with caching

```python
som_results = {}   # (strategy, method) → (metagenes_df, ann_df)

for _, combo_row in tqdm(top_combos.iterrows(), total=len(top_combos), desc="SOM runs"):
    strat, meth = combo_row["strategy"], combo_row["method"]
    run_name    = f"{strat}__{meth}"
    cache_path  = f"{OUT_DIR}/{run_name}/metagenes.csv"

    if os.path.exists(cache_path):
        meta_df = pd.read_csv(cache_path, index_col=0)
        som_results[(strat, meth)] = (meta_df, datasets[strat][1])
        print(f"{run_name}: loaded from cache — {meta_df.shape[0]} metagenes")
        continue

    try:
        exp_norm = cross_results[strat][meth]["exp"]
        ann_s    = datasets[strat][1]
        meta_df, ann_out = run_som(exp_norm, ann_s, run_name)
        meta_df.to_csv(cache_path)
        som_results[(strat, meth)] = (meta_df, ann_out)
        print(f"{run_name}: SOM complete — {meta_df.shape[0]} metagenes")
    except Exception as e:
        print(f"{run_name}: FAILED — {e}")
```

---

## 6 — Post-SOM Batch Effect Evaluation

### 6.1. Batch R² in metagene space

```python
som_summary = {}
for (strat, meth), (meta_df, ann_out) in som_results.items():
    meta_T = meta_df.T
    r2_b   = r2_batch(meta_T, ann_out, batch_col=BATCH_COL)
    r2_d   = r2_batch(meta_T, ann_out, batch_col=BIO_COL)
    som_summary[(strat, meth)] = {"strategy": strat, "method": meth,
                                   "post_batch_r2": r2_b, "post_diag_r2": r2_d}

som_summary_df = pd.DataFrame(som_summary.values()).set_index(["strategy", "method"])

# Join pre-SOM metrics from combo_df
pre_metrics = combo_df.set_index(["strategy", "method"])[["r2_batch", "r2_diag"]]
combined    = pre_metrics.join(som_summary_df, how="right").sort_values("post_batch_r2")
combined.to_csv(f"{OUT_DIR}/batch_effect_summary.csv")
print(combined.to_string())
```

### 6.2. PCA / UMAP / tSNE in metagene space

Same six coloring variables as Section 4e, operating on `meta_df.T` (samples × metagenes).

```python
for col, pal in COLOR_COLS:
    fig, axs = plt.subplots(len(som_results), 3,
                             figsize=(18, 3.5 * len(som_results)),
                             squeeze=False)
    for row, ((strat, meth), (meta_df, ann_out)) in enumerate(som_results.items()):
        meta_T   = meta_df.T
        grouping = ann_out.loc[meta_T.index, col].fillna("NA")
        label    = f"{strat} × {meth}"
        pca_plot(meta_T,  grouping=grouping, palette=pal, legend=None,
                 ax=axs[row, 0], title=f"{label} — PCA")
        umap_plot(meta_T, grouping=grouping, palette=pal, legend=None,
                  ax=axs[row, 1], title=f"{label} — UMAP")
        tsne_plot(meta_T, grouping=grouping, palette=pal, legend=None,
                  ax=axs[row, 2], title=f"{label} — tSNE")
    fig.suptitle(f"POST-SOM — Color: {col}", fontsize=11)
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/post_som_{col}.pdf", bbox_inches="tight")
    plt.show()
```

### 6.3. Formal batch-dominates-biology test

Mirrors the critical diagnostic from the prior analysis (slides 90–91): if same-batch fraction in k-nearest-neighbours exceeds same-biology fraction, the batch effect dominates and the test fails.

```python
def batch_dominates_biology_test(meta_df, ann_df,
                                  batch_col=BATCH_COL,
                                  bio_col=BIO_COL,
                                  n_neighbors=15):
    """
    For each sample, find its k nearest neighbours in metagene space.
    Computes:
      same_batch_ratio — fraction of NN sharing the same RNA_BATCH
      same_bio_ratio   — fraction of NN sharing the same diagnosis
    PASSED if same_bio_ratio >= same_batch_ratio.
    """
    meta_T  = meta_df.T
    common  = meta_T.index.intersection(ann_df.index)
    X       = meta_T.loc[common].values
    batches = ann_df.loc[common, batch_col].fillna("NA").values
    bios    = ann_df.loc[common, bio_col].fillna("NA").values
    nn      = NearestNeighbors(n_neighbors=n_neighbors + 1).fit(X)
    _, idxs = nn.kneighbors(X)
    idxs    = idxs[:, 1:]
    same_batch = np.mean([np.mean(batches[i] == batches[idxs[i]]) for i in range(len(X))])
    same_bio   = np.mean([np.mean(bios[i]    == bios[idxs[i]])    for i in range(len(X))])
    passed = same_bio >= same_batch
    print(f"  same-batch NN: {same_batch:.3f}  |  same-bio NN: {same_bio:.3f}  "
          f"|  {'PASSED ✓' if passed else 'FAILED ✗'}")
    return {"same_batch": same_batch, "same_bio": same_bio, "passed": passed}

test_results = {}
for (strat, meth), (meta_df, ann_out) in som_results.items():
    print(f"\n── {strat} × {meth} ──")
    test_results[(strat, meth)] = batch_dominates_biology_test(meta_df, ann_out)
```

---

## 7 — SOM Portrait Comparison

The most important visual output of the notebook. Portraits are compared both across strategy+method combinations (do they agree on biology?) and across batches within the same biology group (does any combination fully remove platform effects?).

### 7.1. Portrait helper functions

```python
def create_som_colormap():
    colors = ["darkblue", "blue", "cyan", "green", "yellow", "red", "darkred"]
    return LinearSegmentedColormap.from_list("som_rainbow", colors)

def group_portrait(meta_df, ann_df, group_label, group_col,
                   vmin=None, vmax=None, cmap=None, ax=None, title=None):
    """
    Draws the mean SOM portrait for all samples in a given group.
    meta_df: metagenes × samples
    """
    cmap    = cmap or create_som_colormap()
    samples = [s for s in ann_df.index[ann_df[group_col] == group_label]
               if s in meta_df.columns]
    if not samples:
        if ax: ax.set_visible(False)
        return
    mean_vec = meta_df[samples].mean(axis=1).values
    grid_sz  = int(np.ceil(np.sqrt(len(mean_vec))))
    portrait = mean_vec[:grid_sz**2].reshape(grid_sz, grid_sz, order="F")
    ax = ax or plt.gca()
    ax.imshow(portrait, cmap=cmap, origin="lower",
              vmin=vmin or np.percentile(mean_vec, 2),
              vmax=vmax or np.percentile(mean_vec, 98),
              aspect="auto")
    ax.set_title(title or group_label, fontsize=7)
    ax.axis("off")
```

### 7.2. Master portrait comparison grid

**Rows** = biological or batch groups. **Columns** = top strategy+method combinations from Section 5.

```python
PORTRAIT_GROUPS = [
    # Biology groups — should differ visually across rows, be consistent across columns
    ("Diffuse_Large_B_Cell_Lymphoma",     BIO_COL),
    ("Follicular_Lymphoma",               BIO_COL),
    ("Diffuse_Large_B_Cell_Lymphoma_GCB", "Diagnosis_unified_with_coo"),
    ("Diffuse_Large_B_Cell_Lymphoma_ABC", "Diagnosis_unified_with_coo"),
    ("Normal_B_cells",                           "Major_group"),
    ("Kassandra",                         "Major_group"),
    # Batch groups — same platform, should look similar within same biology row
    ("RNASeq_FF_PolyA",                   BATCH_COL),
    ("GPL570_FF_Unknown",                 BATCH_COL),
    ("RNASeq_FFPE_Exome_capture",         BATCH_COL),
    ("GPL570_Unknown_Unknown",            BATCH_COL),
]

def plot_master_portrait_grid(som_res, groups, run_labels,
                               figsize_per_cell=(1.8, 1.8)):
    n_rows = len(groups)
    n_cols = len(run_labels)
    fig    = plt.figure(figsize=(figsize_per_cell[0] * n_cols,
                                 figsize_per_cell[1] * n_rows))
    gs     = gridspec.GridSpec(n_rows, n_cols, figure=fig, hspace=0.05, wspace=0.05)
    for ci, key in enumerate(run_labels):
        if key not in som_res: continue
        meta_df, ann_out = som_res[key]
        for ri, (group_label, group_col) in enumerate(groups):
            ax = fig.add_subplot(gs[ri, ci])
            group_portrait(meta_df, ann_out, group_label, group_col, ax=ax,
                           title=str(key) if ri == 0 else None)
            if ci == 0:
                ax.set_ylabel(group_label[:22], fontsize=6)
    fig.suptitle("SOM Portrait Grid — Rows: groups/batches  ·  Cols: top combinations",
                 fontsize=10, y=1.01)
    plt.savefig(f"{OUT_DIR}/portrait_comparison_grid.pdf", bbox_inches="tight")
    plt.show()

plot_master_portrait_grid(som_results, PORTRAIT_GROUPS, list(som_results.keys()))
```

### 7.3. Within-biology batch consistency portraits

For each combination, show one portrait per RNA_BATCH for the same diagnosis group (minimum 10 samples per batch). A successful combination produces visually identical portraits across columns (batches) within the same row (diagnosis).

```python
def plot_within_biology_batch_grid(som_res, diagnosis_group,
                                    diag_col=BIO_COL,
                                    batch_col=BATCH_COL, min_samples=10):
    # Collect batches with enough samples across all combinations
    all_ann = pd.concat([ann_out for _, ann_out in som_res.values()])
    batches = (all_ann.loc[all_ann[diag_col] == diagnosis_group, batch_col]
               .value_counts()
               .pipe(lambda s: s[s >= min_samples])
               .index.tolist())

    keys = list(som_res.keys())
    fig, axs = plt.subplots(len(keys), len(batches),
                             figsize=(1.6 * len(batches), 1.6 * len(keys)),
                             squeeze=False)
    for ri, key in enumerate(keys):
        meta_df, ann_out = som_res[key]
        for ci, batch in enumerate(batches):
            mask = ((ann_out[diag_col] == diagnosis_group) &
                    (ann_out[batch_col] == batch))
            samp = ann_out.index[mask].tolist()
            ax   = axs[ri, ci]
            if ri == 0: ax.set_title(batch[:18], fontsize=5, rotation=30)
            if ci == 0: ax.set_ylabel(str(key)[:18], fontsize=5)
            if samp:
                mean_vec = meta_df[samp].mean(axis=1).values
                grid_sz  = int(np.ceil(np.sqrt(len(mean_vec))))
                portrait = mean_vec[:grid_sz**2].reshape(grid_sz, grid_sz, order="F")
                ax.imshow(portrait, cmap=create_som_colormap(), origin="lower",
                          aspect="auto")
            ax.axis("off")
    fig.suptitle(f"Within-biology batch check: {diagnosis_group}", fontsize=9)
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/within_biology_{diagnosis_group}.pdf", bbox_inches="tight")
    plt.show()

plot_within_biology_batch_grid(som_results, "Diffuse_Large_B_Cell_Lymphoma")
plot_within_biology_batch_grid(som_results, "Follicular_Lymphoma")
```

---

## 8 — Quantitative Summary Table

Merge pre-SOM and post-SOM metrics (for the top combinations that ran SOM) into a single colour-coded table.

```python
final_rows = []
for (strat, meth), (meta_df, ann_out) in som_results.items():
    pre  = combo_df.set_index(["strategy", "method"]).loc[(strat, meth)]
    t    = test_results.get((strat, meth), {})
    row  = {
        "strategy":          strat,
        "method":            meth,
        "harshness":         METHODS[meth][1],
        "n_samples":         len(ann_out),
        "pre_batch_r2":      pre["r2_batch"],
        "pre_diag_r2":       pre["r2_diag"],
        "post_batch_r2":     r2_batch(meta_df.T, ann_out, BATCH_COL),
        "post_diag_r2":      r2_batch(meta_df.T, ann_out, BIO_COL),
        "batch_test_passed": t.get("passed", None),
        "same_batch_nn":     t.get("same_batch", None),
        "same_bio_nn":       t.get("same_bio", None),
    }
    final_rows.append(row)

final_df = (pd.DataFrame(final_rows)
              .set_index(["strategy", "method"])
              .sort_values("post_batch_r2"))

display(final_df.style
    .background_gradient(cmap="RdYlGn_r", subset=["pre_batch_r2", "post_batch_r2"],
                         axis=0, vmin=0, vmax=1)
    .background_gradient(cmap="RdYlGn",   subset=["pre_diag_r2",  "post_diag_r2"],
                         axis=0, vmin=0, vmax=0.5)
    .applymap(lambda v: "background-color: #90ee90" if v is True  else
                        "background-color: #ffcccc" if v is False else "",
              subset=["batch_test_passed"]))

final_df.to_csv(f"{OUT_DIR}/final_summary.csv")
print("\nTop 5 combinations by post-SOM batch R²:")
print(final_df.sort_values("post_batch_r2").head(5)
      [["harshness", "n_samples", "pre_batch_r2", "post_batch_r2",
        "batch_test_passed"]].to_string())
```

---

## Notebook Structure Summary

| Section | Title | Scope | Key output |
|---|---|---|---|
| 0 | Setup | — | Imports, `BIO_COL`/`BATCH_COL` global config, R bridge, install checklist |
| 1 | Data loading & baseline | — | Raw batch R², platform/diagnosis distribution |
| 2 | Filtering strategies | **10 strategies** | S0, A, B, C, D, E1–E3, **F (microarray-only)**, **G (Affymetrix-only)**; iterative PCA removal loop; per-batch distribution panel; **strict vs imputed gene filtering (2d/2e)** |
| 3 | Harmonization methods | **18 methods** | Functions ordered by harshness; `BIO_COL`/`BATCH_COL` defaults throughout; method registry |
| 4 | Full cross-product evaluation | **10 × 18 = 1,440 combinations** | Batch R² heatmap (strategy × method), top-K selection for SOM, PCA/UMAP/tSNE for top combinations |
| 5 | SOM analysis | **Top `TOP_K_SOM` combinations** | oposSOM runs, metagene extraction, caching |
| 6 | Post-SOM evaluation | **Top combinations** | Batch R² in metagenes, PCA/UMAP/tSNE (6 color vars), NN batch dominance test |
| 7 | Portrait comparison | **Top combinations** | Master grid (10 groups × top combinations), within-biology batch grid |
| 8 | Summary table | All | Colour-coded merged metrics table, top-5 combinations |

---

## Implementation Notes

### Global configuration
`BIO_COL = "Diagnosis_cell_type_unified"` and `BATCH_COL = "RNA_BATCH"` are defined in Section 0 and used as defaults throughout all functions. Changing them in Section 0 propagates to all sections automatically.

### Gene filtering strictness
`prepare_dataset` drops any gene with **at least one NA** across the retained samples (`dropna(axis=1)`). The alternative `prepare_dataset_imputed` retains genes with up to `max_na_frac` NA fraction and fills them via KNN, missForest, or softImpute. For the full cross-product benchmark, the strict approach is used by default to ensure complete matrices. The imputed variants are evaluated separately on Strategy A.

### Full cross-product computation
10 strategies × 18 methods = 180 normalisation runs. Computationally expensive methods (MNN, Scanorama, missForest imputation) may take 5–15 min per strategy. Run the full cross-product cell overnight; use `tqdm` progress bars to monitor. Failed combinations are recorded as `NaN` and skipped in subsequent analysis.

### Top-K selection for SOM
`TOP_K_SOM = 15` combinations are selected from the cross-product by lowest pre-SOM batch R². This is dynamic — the best combinations in any given dataset are selected automatically. Adjust `TOP_K_SOM` based on available compute time (~40 min per SOM run).

### Strategies F and G
- **F (microarray-only)**: removes RNA-seq samples; useful for evaluating whether microarray-specific normalisations (ComBat, qsmooth) fully harmonise within the microarray space. Typically retains ~3,821 samples — within the budget constraint.
- **G (Affymetrix-only)**: retains only GPL570 batches (~2,800 samples). Used to isolate within-platform batch effects between `GPL570_FF_Unknown`, `GPL570_FFPE_Unknown`, and `GPL570_Unknown_Unknown`. Highly within-budget and expected to show very low batch R² after standard normalization.

### Iterative removal convergence
Rounds E1–E3 are meant to be run interactively: inspect the PCA plot after each round, decide whether to proceed. Each round updates the bad_batches list cumulatively. Round E3 should not be run if the budget constraint is already approached after E2.

### Strategy C and RNA-seq only
Strategy C (RNA-seq only) typically removes ~67% of samples, exceeding the 1/3 budget. It is included as a reference upper bound for what is achievable when platform effects are fully eliminated.

### ComBat-seq / InMoose on mixed data
Both count-based methods use `np.round().clip(0)` to convert log2-intensity microarray values to pseudo-counts. This is an approximation; their SOM portraits should be interpreted with the caveat that their input assumption (integer counts from RNA-seq) is violated for microarray batches.

### Caching
All SOM runs save metagene matrices to `harmonization_results/{run_name}/metagenes.csv`. The run loop checks the cache first; re-running the notebook after an interruption is free for completed combinations.

### R working directory
`run_som()` uses `os.chdir(out_dir)` so oposSOM writes its PDFs and HTML reports into the run-specific subdirectory. `os.chdir(orig_dir)` restores the original path afterward.

### Time budget (approximate)
| Step | Estimated time |
|---|---|
| 10 × 18 normalizations (Section 4a) | 4–8 hours |
| Pre-SOM plots (Section 4b–f) | 30–60 min |
| Top-15 SOM runs (Section 5b) | ~10 hours |
| Post-SOM plots + portraits (Sections 6–7) | 20–30 min |

Run Sections 4a and 5b overnight in separate sessions. All other sections are interactive.

### Constraint compliance
| Strategy | Samples removed | % of total | Within budget? |
|---|---|---|---|
| S0 no removal | 0 | 0% | ✓ |
| A confirmed bad | ~1,794 | 24.8% | ✓ |
| B extended bad | ~2,200 | 30.4% | ✓ |
| C RNA-seq only | ~4,852 | 67% | ✗ (reference only) |
| D malignant only | ~1,000 | ~14% | ✓ |
| E1–E3 iterative | varies (runtime) | checked per round | checked per round |
| F microarray only | ~2,386 RNA-seq | ~33% | ✓ (borderline) |
| G Affymetrix only | ~4,400 non-GPL570 | ~61% | ✗ (reference only) |

---

## TODO List

> Status assessed against `collagen_3_11mark.ipynb` as of 2026-04-18.  
> **[x]** = code written in notebook. **[ ]** = not yet implemented.  
> Notes on stale/broken cells that need cleanup are collected at the end under **"Notebook cleanup required"**.

---

### Phase 0 — Environment setup

- [ ] **0.1** Verify all required R packages are installed: `sva`, `limma`, `batchelor`, `RUVSeq`, `qsmooth`, `preprocessCore`, `missForest`, `softImpute`, `FSQN` (via devtools)
- [ ] **0.2** Verify all required Python packages are installed: `harmonypy`, `combat`, `inmoose`, `scanorama`, `fancyimpute`, `umap-learn`
- [ ] **0.3** Confirm `REMOTE_ROOT` path `$FL_DATA_ROOT/` is mounted and `comb_exp.tsv` is accessible
- [ ] **0.4** Confirm `comb_ann_unified.csv` exists locally and contains the `Diagnosis_cell_type_unified` column
- [ ] **0.5** Create a dedicated Python 3.11 virtual environment for this notebook:
  ```bash
  python3.11 -m venv ~/venvs/collagen_3_11
  source ~/venvs/collagen_3_11/bin/activate
  pip install ipykernel umap-learn harmonypy combat inmoose scanorama fancyimpute rpy2 tqdm
  python -m ipykernel install --user --name collagen_3_11 --display-name "Python 3.11 (harmonization)"
  ```
  Then switch the notebook kernel from `collagen_3_11` to `collagen_3_11`.

---

### Phase 1 — Data loading and baseline (Section 0–1)

- [x] **1.1** Write Section 0 cell: all imports, global config with `BIO_COL` and `BATCH_COL`, paths, `OUT_DIR`, color palettes, custom plot helpers — cells 2–5
- [x] **1.2** Write install-check cell (R and Python package comments) — cell-4
- [x] **1.3** Write Section 1 loading cell: load `comb_exp`, `comb_ann`; print shape, `BATCH_COL` counts, `BIO_COL` counts — cell-6
- [x] **1.4** Implement `pca_variance_explained_by_batch()` and `r2_batch()` helper functions — cell-7
- [x] **1.5** Compute and print baseline batch R² before any filtering — cell-7

---

### Phase 2 — Filtering strategies (Section 2)

- [x] **2.1** Implement `apply_filter()` with support for `bad_batches`, `bad_cohorts`, `keep_batches`, `keep_groups`, and `bio_col` parameters — cell-10
- [x] **2.2** Define `RARE_GROUPS`, `RNASEQ_BATCHES`, `MICROARRAY_BATCHES`, `AFFYMETRIX_BATCHES`, `NORMAL_GROUPS` lists — cell-10
- [x] **2.3** Implement Strategy 0 (no removal) and print stats — cell-10
- [x] **2.4** Implement Strategy A (confirmed bad batches: 3 FFPE batches + SOM cohort) and print stats — cell-11
- [x] **2.5** Implement Strategy B (extended bad batches list) and print stats — cell-11
- [x] **2.6** Implement Strategy C (RNA-seq only) and print stats with budget warning — cell-12
- [x] **2.7** Implement Strategy D (malignancies only, no normal B cells) and print stats — cell-12
- [x] **2.8** Implement Strategy F (microarray only, RNA-seq excluded) and print stats — cell-13
- [x] **2.9** Implement Strategy G (Affymetrix GPL570 only) and print stats with budget warning — cell-13
- [x] **2.10** Implement `identify_outlier_batches()` for iterative PCA-based removal — cell-14
- [x] **2.11** Interactively run Strategies E1, E2, E3 (iterative removal rounds); inspect PCA after each round; record chosen bad batches — cell-15/16/17
- [x] **2.12** Build `FILTER_STRATEGIES` dict with all 10 strategies — cell-18
- [x] **2.13** Implement `plot_batch_distributions()` and run on Strategy A — cell-19
- [x] **2.14** Implement `prepare_dataset()` (strict full-coverage: drop any gene with ≥1 NA) — cell-14
- [x] **2.15** Prepare all 10 strategy datasets using `prepare_dataset()`; store in `datasets` dict — cell-18
- [x] **2.16** Implement `prepare_dataset_imputed()` with KNN, missForest, and softImpute methods — cell-20
- [x] **2.17** Run imputation comparison on Strategy A: compare gene counts retained and pre-norm batch R² for all 3 imputation methods vs strict dropping — cell-20

---

### Phase 3 — Harmonization method implementations (Section 3)

- [x] **3.1** Implement `normalize_raw()` — cell-22
- [x] **3.2** Implement `normalize_median_scaling()` — cell-22
- [x] **3.3** Implement `normalize_limma()` — cell-22
- [x] **3.4** Implement `normalize_sva()` — cell-22
- [x] **3.5** Implement `normalize_combat()` — cell-23
- [x] **3.6** Implement `normalize_combat_seq()` — cell-23
- [x] **3.7** Implement `normalize_pycombat()` — cell-23
- [x] **3.8** Implement `normalize_inmoose_combat_seq()` — cell-23
- [x] **3.9** Implement `normalize_ruv()` — cell-23
- [x] **3.10** Implement `normalize_mnn()` — cell-23
- [x] **3.11** Implement `normalize_harmony()` — cell-23
- [x] **3.12** Implement `normalize_scanorama()` — cell-23
- [x] **3.13** Implement `normalize_fsmvn()` — cell-23
- [x] **3.14** Implement `normalize_qsmooth()` — cell-24
- [x] **3.15** Implement `normalize_fsqn_py()` — cell-24
- [x] **3.16** Implement `normalize_fsqn_r()` — cell-24
- [x] **3.17** Implement `normalize_quantile()` — cell-24
- [x] **3.18** Implement `normalize_rank()` — cell-24
- [x] **3.19** Build `METHODS` registry dict and `HARSHNESS_COLORS` — cell-25
- [x] **3.20** Smoke-test each method on a small subset (100 samples × 500 genes) to confirm no crashes — cell-29

---

### Phase 4 — Full cross-product evaluation (Section 4)

- [x] **4.1** Set up `cross_results` dict; run 4D 1,440 combinations (10×4×18×2) via `tqdm`; error handling; pre-compute `imputed_datasets` — cell-31
- [x] **4.2** Build `batch_r2_matrix` and `diag_r2_matrix` (collapsed mean over D2×D4); save as CSV; flat ranked table of all combos — cell-32
- [x] **4.3** Plot cross-product batch R² heatmap; save as PDF — cell-32
- [x] **4.4** Plot mean-batch-R² bar chart per method (harshness colour coded) — cell-33
- [x] **4.5** Flatten into `combo_df` (4-tuple key: strategy, imputation, method, post_removal); select top `TOP_K_SOM` — cell-34
- [x] **4.6** Plot PCA/UMAP/tSNE for top combinations, 2 primary + 4 secondary colour columns — cell-31
- [x] **4.7** Run `distribution_panel_comparison()` for top combinations — cell-32

---

### Phase 5 — SOM analysis (Section 5)

- [x] **5.1** Implement `run_som()` with `group_col=BIO_COL` default; `os.chdir` restore — cell-34
- [x] **5.2** SOM loop with caching for top-K combinations — cell-35
- [ ] **5.3** Verify metagene matrix shapes are consistent across runs; reload from cache for any crashed runs

---

### Phase 6 — Post-SOM evaluation (Section 6)

- [x] **6.1** Compute post-SOM batch R² and diagnosis R² in metagene space — cell-38
- [x] **6.2** Build `combined` DataFrame joining pre/post-SOM metrics; save as CSV — cell-38
- [x] **6.3** Plot PCA/UMAP/tSNE in metagene space, coloured by `BATCH_COL` and `BIO_COL` — cell-39
- [x] **6.4** Implement `batch_dominates_biology_test()` with `bio_col=BIO_COL` default; run for all SOM combinations — cell-40

---

### Phase 7 — Portrait comparison (Section 7)

- [x] **7.1** Implement `create_som_colormap()` and `group_portrait()` — cell-41 *(misplaced before Section 7 markdown; see cleanup item C4)*
- [x] **7.2** Define `PORTRAIT_GROUPS` list — cell-44
- [x] **7.3** Implement and run `plot_master_portrait_grid()`; save as PDF — cell-44
- [x] **7.4** Run `plot_within_biology_batch_grid()` for DLBCL — cell-45
- [x] **7.5** Run `plot_within_biology_batch_grid()` for FL — cell-45

---

### Phase 8 — Final summary (Section 8)

- [x] **8.1** Build `final_df` with all pre/post-SOM metrics — cell-47
- [x] **8.2** Colour-coded HTML table — cell-47
- [x] **8.3** Save `final_summary.csv` — cell-47
- [x] **8.4** Print top-5 combinations by post-SOM batch R² — cell-47
- [x] **8.5** Write 1-paragraph interpretation cell identifying the winning combination and whether the batch-dominates-biology test passes for any combination — cell-50

---

### Phase 9 — Review and reporting

- [x] **9.1** Cross-check: confirm `BIO_COL` / `BATCH_COL` used consistently; no hardcoded `"RNA_BATCH"` or `"Major_group"` strings outside Section 0 — verified
- [ ] **9.2** Strip outputs with `nbstripout` before committing
- [ ] **9.3** Archive `harmonization_results/` to remote (`$FL_DATA_ROOT/harmonization_results/`)
- [ ] **9.4** Update `CLAUDE.md` "Current Status" section with findings
- [ ] **9.5** Decide next step: if no combination passes the batch test for mixed-platform data, proceed with RNA-seq-only SOM


---

## To-do list after the user review of the notebook

Issues and gaps identified by reviewing `harmonization_benchmark.ipynb` after the user updated it. All items refer to specific cells and are ordered by section.

### T0 — Section 0 (Setup)

- [x] **T0.1** Fixed `_lookup_color()` helper in cell-3: iterates palette items to find float NaN keys; falls back to `str(g)` then `"#888888"`.

- [x] **T0.2** Added `("COHORT_LABEL", cohort_palette)` to `SECONDARY_COLS` / `COLOR_COLS` in cell-35.

- [x] **T0.3** Implemented `_draw_grouped_legend()` and `PALETTE_GROUPS` dict (cell-5); `_scatter_grouped` accepts optional `palette_groups=` parameter.

- [x] **T0.4** Updated `pca_plot` in cell-3: stores fitted `PCA` object, sets `xlabel = f"PC1 ({pca.explained_variance_ratio_[0]:.1%})"` and `ylabel` accordingly.

### T1 — Section 1 (Data Loading)

- [x] **T1.1** `Diagnosis_with_coo` and `Diagnosis_unified_with_coo` columns are created in cell-8 (data loading). `PORTRAIT_GROUPS` in cell-46 references `"Diagnosis_unified_with_coo"`. Column order confirmed correct.

- [x] **T1.2** Biology R² check (`r2_batch(comb_exp.dropna(axis=1), comb_ann, BIO_COL)`) is in cell-10, positioned after `r2_batch` definition in cell-9.

### T2 — Section 2 (Filtering Strategies)

- [x] **T2.1** Fixed: removed the buggy `r2_bio = r2_batch(comb_exp.dropna(axis=1), ...)` lines from cell-19. The loop now only prints batch R² per strategy.

- [x] **T2.2** Deleted duplicate cell (was cell-19 in old numbering). The correct cell is now cell-19 in the new notebook.

### T3 — Section 3 (Harmonization Methods)

No new issues found. Section 3 methods are correct.

### T4 — Section 4 (Cross-Product Evaluation)

- [x] **T4.1** Expanded to 4D: `cross_results[(strategy, imputation, method, post_removal)]`. Pre-computes `imputed_datasets` for all (strat, imp) pairs. `IMPUTATION_METHODS` and `POST_REMOVAL_OPTIONS` globals defined in cell-31.

- [x] **T4.2** Updated heatmap (cell-32): collapses to 2D (strategy × method) by taking mean over imputation × post_removal; also saves flat ranked CSV of all 1,440 combinations.

- [x] **T4.3** Updated `combo_df` (cell-34): 4-tuple index with `strategy`, `imputation`, `method`, `post_removal` columns. `top_combos` carries all four columns forward.

### T5 — Section 5–8 (SOM and downstream)

No new issues found beyond the Section 4 expansion above.

### T6 — Notebook structure

- [x] **T6.1** All 9 section markdown cells renamed: "## Section N —..." → "## N —..." throughout the notebook.

- [ ] **T6.2** Subsection headers (### 0.1, ### 0.2, ..., ### 1.1, etc.) not yet added as separate markdown cells. The section structure is clear from code comment headings. Add if desired for navigation.

- [x] **T6.3** Title cell (cell-0) ToC updated: "Section" prefix removed, 4D cross-product dimensions added to Section 4 row, `Diagnosis_with_coo` / `Diagnosis_unified_with_coo` reference added to Section 1 row.

