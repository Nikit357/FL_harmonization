# Implementation Plan: Comprehensive Batch Effect Metrics Script

**Date:** 2026-04-29  
**Author:** Daniil Nikitin  
**Revised:** 2026-04-30  
**Purpose:** Design a new pipeline that computes a comprehensive set of batch effect and data quality metrics for every harmonized expression dataset stored in S3, writes results as per-harmonization JSON sidecars and a separate gene-set JSON, and uploads an aggregated result file.

---

## 1. Context and Motivation

The current `metrics.csv` on S3 contains only two metrics per dataset: `r2_batch` (PCA R² for RNA_BATCH) and `r2_diag` (PCA R² for Diagnosis). This is insufficient for a complete batch effect assessment. The literature (Büttner et al. 2019; Luecken et al. 2022; Korsunsky et al. 2019; Hoffman & Schadt 2016; Lüttgenau et al. 2021; Freytag et al. 2023 — SelectBCM) recommends a multi-metric approach because:

- PCA R² is a global, linear metric — it misses local batch structure and non-linear batch effects
- A method can score low on PCA R² by destroying biological signal (e.g., over-correction), which PCA R² alone does not detect
- Different metrics capture different aspects: global mixing (LISI, kBET), distributional alignment (KS test), gene-level decomposition (variancePartition), visual/neighborhood structure (UMAP/tSNE batch entropy)

**Scope:** 533 expression files (post0 variants) × comprehensive metric suite.

**Inputs:** All `FL_batch_correction/exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz` files  
**Annotation source:** `FL_batch_correction/prepared/{strat}__{imp}__ann.tsv.gz` (aligned by sample index)

**Output — three artefacts per harmonization attempt:**

1. **Metrics JSON sidecar:** `FL_batch_correction/metrics/{strat}__{imp}__{method}__post{0|1}_metrics.json`  
   Contains all computed metric values. Written incrementally — each metric group appended immediately after calculation so that a crash after group B does not lose group A results. A failed group stores `null` values plus an `"error"` string; other groups continue unaffected.

2. **Gene-set JSON sidecar:** `FL_batch_correction/genes/{strat}__{imp}__{method}__post{0|1}_genes.json`  
   Records the exact list of genes present in this harmonization output. Needed for downstream gene set analysis, particularly important for methods that reduce the gene space (e.g., `25_angel`).

3. **Aggregated output:** `FL_batch_correction/metrics_comprehensive.csv`  
   Produced by a dedicated aggregation script (`run_metrics_concat.py`) that reads all per-harmonization JSON files and concatenates them into a single table. Run separately from the job dispatcher so that a partial run can be aggregated at any time.

---

## 2. Metric Catalog 

**Batch annotation columns** (used where "batch columns" is referenced):  
`RNA_BATCH`, `PLATFORM_RNA`, `RNASEQ_SOURCE`, `COHORT_LABEL`

**Biology annotation columns** (used where "biology columns" is referenced):  
`Major_group`, `PLATFORM_RNA`, `Diagnosis_cell_type_unified`, `TUMOR_NORMAL`

**Full annotation column set** (used where "all columns" is referenced):  
`RNA_BATCH`, `Major_group`, `PLATFORM_RNA`, `RNASEQ_SOURCE`, `TUMOR_NORMAL`, `COHORT_LABEL`, `Diagnosis_cell_type_unified`

---

### 2.1 Group A — PCA-based Variance Decomposition

---

#### A1. PCA R² (ANOVA) — per batch/covariate column

**What it measures:** The fraction of variance in the first N principal components that is statistically attributable to a categorical grouping variable, using one-way ANOVA R².

**Formula:**
```
For each PC_i (i=1..N):
  R²_i = SS_between / SS_total
  where SS_between = Σ_g n_g × (ȳ_g − ȳ)²
        SS_total   = Σ_j (y_j − ȳ)²

Mean R² = (1/N) × Σ_i R²_i
```

**Why needed:** The primary quality metric for batch correction in this project. Already implemented as `pca_variance_explained_by_batch()` in `bench_shared.py`. Extended to cover all relevant covariates.

**Covariates computed:**
- `RNA_BATCH` — main platform/batch effect. Target: < 0.20. Raw baseline: ~0.95.
- `Major_group` — coarse biology (DLBCL/FL/Normal). Should remain high after normalization — if it drops, biological signal is being destroyed.
- `PLATFORM_RNA` — platform technology (RNASeq vs Microarray). Should decrease after correction.
- `RNASEQ_SOURCE` — FF vs FFPE effect. Expected to remain moderate (FFPE degrades RNA quality irreversibly).
- `TUMOR_NORMAL` — tumor vs. normal separation. Must be preserved — loss = over-correction.
- `COHORT_LABEL` — tracks degree of mixing between and within individual cohorts. High R² indicates residual cohort-level batch structure beyond platform effects.
- `Diagnosis_cell_type_unified` - detailed biology.

**Output columns:** `r2_RNA_BATCH`, `r2_Major_group`, `r2_PLATFORM_RNA`, `r2_RNASEQ_SOURCE`, `r2_TUMOR_NORMAL`, `r2_COHORT_LABEL`

**Parameters:** N = 10 PCs.

**Caveats:**
- ANOVA R² assumes homogeneous within-group variance (rarely met in genomics but useful as a relative measure).
- For `25_angel`, gene space is reduced — R² values are not directly comparable with other methods.
- A method can achieve low `r2_RNA_BATCH` by compressing all variance toward zero — this is why `r2_Major_group` and `r2_TUMOR_NORMAL` are needed as counterparts.
- Equal-weight mean R² across PCs treats PC1 and PC10 equally. See metric A3 (PCR) for the variance-weighted version.

**References:** Leek et al. 2010 (*Nat Rev Genet*); existing implementation in `bench_shared.py`.

---

#### A2. Per-PC R² Profile — per batch column

**What it measures:** Individual R² values for each of PC1–PC10, for each batch column. Reveals whether batch effect is concentrated in the first few PCs (large-scale platform shift) or distributed across many PCs (complex residual confounding).

**Applied to:** `RNA_BATCH`, `PLATFORM_RNA`, `RNASEQ_SOURCE`, `COHORT_LABEL`

**Why needed:** The mean R² can be misleading — a method with R²_PC1 = 0.9 and R²_PC2..10 ≈ 0 has mean R² ≈ 0.09 (looks excellent) but still has a dominant batch PC. Reporting per-PC R² reveals this pattern.

**Output columns:** `r2_pc1_RNA_BATCH` .. `r2_pc10_RNA_BATCH`,  `r2_pc1_PLATFORM_RNA` .. `r2_pc10_PLATFORM_RNA`,  `r2_pc1_RNASEQ_SOURCE` .. `r2_pc10_RNASEQ_SOURCE`,  `r2_pc1_COHORT_LABEL` .. `r2_pc10_COHORT_LABEL` (40 columns total)

**How to interpret:** Ideal: all 10 values near 0. Acceptable: PC1 slightly elevated if PCs 2–10 are clean.

---

#### A3. PCR — Principal Component Regression (variance-weighted R²)

**Reference:** Luecken MD et al. *Nature Methods* 19(1):41–50. 2022. DOI: 10.1038/s41592-021-01336-8. Also: CellMixS — Lüttgenau S et al. *Life Science Alliance* 4(6):e202001004. 2021.

**What it measures:** Fraction of total PCA variance attributable to batch labels, where each PC is weighted by its proportion of explained variance.

**Formula:**
```
For each PC_l (l=1..L), let var_l = variance explained by PC_l:
  r²_l = Pearson R² of regressing PC_l on batch dummy variables

PCR = 1 − Σ_l (var_l × r²_l) / Σ_l var_l   → [0, 1], higher = better (less batch in PCA)
```

**Applied to all columns:** `RNA_BATCH`, `Major_group`, `PLATFORM_RNA`, `RNASEQ_SOURCE`, `TUMOR_NORMAL`, `COHORT_LABEL`, `Diagnosis_cell_type_unified`

**Why preferred over simple mean R²:** If PC1 explains 40% of variance and PC2 explains 2%, the simple mean treats them equally. PCR gives PC1 20× more weight, correctly reflecting that a batch effect concentrated in PC1 is far more serious than one in PC2.

**Output columns:** `pcr_RNA_BATCH`, `pcr_Major_group`, `pcr_PLATFORM_RNA`, `pcr_RNASEQ_SOURCE`, `pcr_TUMOR_NORMAL`, `pcr_COHORT_LABEL`, `pcr_Diagnosis_cell_type_unified`  
(Reported as scib convention: higher = better = 1 − variance-weighted R²)

**Implementation:** Top-100 PCs; per-PC ANOVA SS ratio weighted by eigenvalue/sum(eigenvalues).

---

#### A4. DSC — Dispersion Separability Criterion

**Reference:** PCA-Plus paper. *PLOS ONE* (2024). DOI: 10.1371/journal.pone.0295473.

**What it measures:** Ratio of between-group scatter to within-group scatter in the first two PCA dimensions.

**Formula:**
```
DSC = Db / Dw
  where Db = trace(between-group scatter matrix)
        Dw = trace(within-group scatter matrix)
  Both computed in the 2D PCA space.

between-group scatter: Sb = Σ_b n_b (μ_b − μ)(μ_b − μ)ᵀ
within-group scatter:  Sw = Σ_b Σ_{i in b} (x_i − μ_b)(x_i − μ_b)ᵀ
```

**Applied to batch columns:** `RNA_BATCH`, `PLATFORM_RNA`, `RNASEQ_SOURCE`, `COHORT_LABEL`

**How to interpret:**
- **DSC < 0.3**: No meaningful batch separation in PCA — good integration
- **DSC 0.3–0.6**: Moderate batch effect
- **DSC > 0.6**: Strong batch clustering — problematic
- Accompanied by a permutation p-value (permute batch labels 999 times → empirical null).

**Output columns:** `dsc_RNA_BATCH`, `dsc_pvalue_RNA_BATCH`, `dsc_PLATFORM_RNA`, `dsc_pvalue_PLATFORM_RNA`, `dsc_RNASEQ_SOURCE`, `dsc_pvalue_RNASEQ_SOURCE`, `dsc_COHORT_LABEL`, `dsc_pvalue_COHORT_LABEL`

---

### 2.2 Group B — Neighbor-based Integration Metrics

---

#### B1. kBET Acceptance Rate

**Reference:** Büttner M et al. *Nature Methods* 16(1):43–49. 2019. DOI: 10.1038/s41592-018-0254-1.

**What it measures:** Whether the local (k-nearest-neighbor) composition of batch labels around each sample matches the global batch label distribution.

**Applied to batch columns:** `RNA_BATCH`, `PLATFORM_RNA`, `RNASEQ_SOURCE`, `COHORT_LABEL`

**Algorithm:**
1. Compute PCA embedding (first N PCs).
2. Randomly sample 10% of all samples as test points.
3. Set neighborhood size: k = min(25, n/4).
4. For each test point `i`, find k nearest neighbors. Count per-batch: `O_b` = observed, `E_b` = global fraction × k.
5. Compute χ²_i = Σ_b (O_b − E_b)² / E_b with (n_batches − 1) degrees of freedom.
6. Acceptance rate = 1 − (fraction of test points with p ≤ 0.05).

**How to interpret:**
- **Acceptance rate near 1.0:** excellent batch mixing
- **Acceptance rate near 0.0:** severe batch effect
- Target: acceptance rate > 0.70

**Output columns:** `kbet_acceptance_rate_RNA_BATCH`, `kbet_acceptance_rate_PLATFORM_RNA`, `kbet_acceptance_rate_RNASEQ_SOURCE`, `kbet_acceptance_rate_COHORT_LABEL`

**Implementation:** Python-only using `sklearn.neighbors.NearestNeighbors` + `scipy.stats.chi2`. k = min(25, n/4).

---

#### B2. iLISI — Integration Local Inverse Simpson's Index

**Reference:** Korsunsky I et al. *Nature Methods* 16(12):1289–1296. 2019. DOI: 10.1038/s41592-019-0619-0.

**What it measures:** For each sample, how diverse are the batch labels in its local neighborhood (effective number of equally-present batches).

**Applied to batch columns:** `RNA_BATCH`, `PLATFORM_RNA`, `RNASEQ_SOURCE`, `COHORT_LABEL`

**Formula:**
```
For sample i with neighborhood of k samples:
  p_b = fraction of k neighbors belonging to batch b
  LISI_i = 1 / Σ_b p_b²

iLISI = mean(LISI_i) over all samples
iLISI_normalized = (iLISI − 1) / (n_batches − 1)   → [0, 1]
```

**How to interpret:**
- **iLISI = n_batches:** perfect integration
- **iLISI = 1.0:** no mixing → maximum batch effect
- Target: iLISI_normalized ≥ 0.5

**Output columns:** `ilisi_mean_RNA_BATCH`, `ilisi_norm_RNA_BATCH`, `ilisi_mean_PLATFORM_RNA`, `ilisi_norm_PLATFORM_RNA`, `ilisi_mean_RNASEQ_SOURCE`, `ilisi_norm_RNASEQ_SOURCE`, `ilisi_mean_COHORT_LABEL`, `ilisi_norm_COHORT_LABEL`

---

#### B3. cLISI — Cell-type (Biology) Local Inverse Simpson's Index

**Reference:** Same as iLISI (Korsunsky et al. 2019).

**What it measures:** Same computation as iLISI but using biological labels. High cLISI means neighborhoods contain mixed diagnoses → biology NOT preserved.

**Applied to biology columns:** `Major_group`, `PLATFORM_RNA`, `Diagnosis_cell_type_unified`, `TUMOR_NORMAL`

**How to interpret:**
- **cLISI near 1.0:** neighborhoods biologically pure — biology preserved (ideal)
- **cLISI near n_groups:** neighborhoods are random w.r.t. biology — biology destroyed

**Output columns:** `clisi_mean_Major_group`, `clisi_mean_PLATFORM_RNA`, `clisi_mean_Diagnosis_cell_type_unified`, `clisi_mean_TUMOR_NORMAL`

---

#### B4. ASW_batch — Average Silhouette Width for Batch Labels

**Reference:** Rousseeuw PJ. *Journal of Computational and Applied Mathematics* 20:53–65. 1987. Applied to batch assessment in Luecken et al. 2022.

**What it measures:** How much more similar each sample is to its own batch vs. the nearest other batch. Computed on PCA coordinates (first 50 components).

**Applied to batch columns:** `RNA_BATCH`, `PLATFORM_RNA`, `RNASEQ_SOURCE`, `COHORT_LABEL`

**Formula:**
```
For sample i in batch B_i:
  a_i = mean distance from i to all other samples in B_i
  b_i = min over other batches B_j≠B_i of mean distance from i to B_j
  s_i = (b_i − a_i) / max(a_i, b_i)

ASW_batch = mean(s_i) over all samples
ASW_batch_norm = 1 − |ASW_batch|   (scib convention; higher = better)
```

**How to interpret:**
- **ASW_batch near −1:** well-mixed (samples closer to other batches)
- **ASW_batch near +1:** severe batch clustering
- Target: ASW_batch < 0.10

**Output columns:** `asw_batch_RNA_BATCH`, `asw_batch_norm_RNA_BATCH`, `asw_batch_PLATFORM_RNA`, `asw_batch_norm_PLATFORM_RNA`, `asw_batch_RNASEQ_SOURCE`, `asw_batch_norm_RNASEQ_SOURCE`, `asw_batch_COHORT_LABEL`, `asw_batch_norm_COHORT_LABEL`

**Implementation:** `sklearn.metrics.silhouette_score(pca_coords, batch_labels)`. PCA-based distances throughout (50 dimensions). Subsample to max 2,000 samples if n > 2,000 for computational feasibility.

---

#### B5. ASW_biology — Average Silhouette Width for Biology Labels

**Reference:** Same as ASW_batch.

**What it measures:** Silhouette score using biological labels on PCA coordinates. High values = biologically similar samples cluster together = biology preserved.

**Applied to biology columns:** `Major_group`, `PLATFORM_RNA`, `Diagnosis_cell_type_unified`, `TUMOR_NORMAL`

**How to interpret:**
- **ASW_bio near +1:** biological groups well-separated — biology preserved
- **ASW_bio near 0 or −1:** biological structure lost
- Normalization: `ASW_bio_norm = (ASW_bio + 1) / 2` → [0, 1], higher = better

**Output columns:** `asw_bio_Major_group`, `asw_bio_norm_Major_group`, `asw_bio_PLATFORM_RNA`, `asw_bio_norm_PLATFORM_RNA`, `asw_bio_Diagnosis_cell_type_unified`, `asw_bio_norm_Diagnosis_cell_type_unified`, `asw_bio_TUMOR_NORMAL`, `asw_bio_norm_TUMOR_NORMAL`

---

#### B6. CMS — Cell-specific Mixing Score

**Reference:** Lüttgenau S et al. *Life Science Alliance* 4(6):e202001004. 2021. DOI: 10.26508/lsa.202001004.

**What it measures:** Anderson-Darling test on per-batch kNN distance distributions. Tests whether distances from a sample to each batch are drawn from the same distribution.

**Applied to batch columns:** `RNA_BATCH`, `PLATFORM_RNA`, `RNASEQ_SOURCE`, `COHORT_LABEL`

**Algorithm:**
1. For sample i in PCA space, retrieve k nearest neighbors (k ≈ 20–50 for bulk).
2. Split distances by batch membership.
3. Apply Anderson-Darling k-sample test.
4. CMS_i = p-value of the AD test ∈ [0, 1] (higher = better mixing).

**Output columns:** `cms_mean_RNA_BATCH`, `cms_fraction_mixed_RNA_BATCH`, `cms_mean_PLATFORM_RNA`, `cms_fraction_mixed_PLATFORM_RNA`, `cms_mean_RNASEQ_SOURCE`, `cms_fraction_mixed_RNASEQ_SOURCE`, `cms_mean_COHORT_LABEL`, `cms_fraction_mixed_COHORT_LABEL`

Where `cms_fraction_mixed_{col}` = fraction of samples with CMS > 0.05.

**Implementation:** `scipy.stats.anderson_ksamp`. Requires `scipy ≥ 1.9`.

---

### 2.3 Group C — UMAP/tSNE Embedding Metrics

---

#### C1. Batch Centroid Dispersion in UMAP

**What it measures:** After computing a UMAP 2D embedding, for each batch compute its centroid (mean x, y). The centroid dispersion is the standard deviation of centroid positions divided by the overall standard deviation of all sample positions.

**Applied to batch columns:** `RNA_BATCH`, `PLATFORM_RNA`, `RNASEQ_SOURCE`, `COHORT_LABEL`

**Formula:**
```
For each batch b: centroid_b = mean of UMAP coordinates of samples in b
Centroid dispersion = std(centroid_x) / std(all_x),  mean of x and y dimensions
```

**How to interpret:** Ratio near 0 = batch centroids overlap (good); near 1 or higher = batches form separated islands.

**Implementation:** `umap-learn` Python package. Configuration: n_neighbors=30, min_dist=0.3, n_components=2, metric='euclidean' on PCA(n=50) coordinates, random_state=42.

**Output columns:** `umap_centroid_disp_RNA_BATCH`, `umap_centroid_disp_PLATFORM_RNA`, `umap_centroid_disp_RNASEQ_SOURCE`, `umap_centroid_disp_COHORT_LABEL`

---

#### C2. Local Neighborhood Batch Entropy in UMAP and tSNE

**What it measures:** For each sample, Shannon entropy of the batch label distribution in its k-nearest-neighbor neighborhood in the embedding space. Averaged over all samples.

**Applied to batch columns:** `RNA_BATCH`, `PLATFORM_RNA`, `RNASEQ_SOURCE`, `COHORT_LABEL`  
Applied in both UMAP and tSNE embedding spaces.

**Formula:**
```
For sample i with k-NN in embedding space:
  p_b = fraction of k neighbors in batch b
  H_i = −Σ_b p_b × log(p_b)   (convention: 0×log0 = 0)

Normalized entropy = mean(H_i) / log(n_batches)   → [0, 1]
```

**How to interpret:** Normalized entropy near 1.0 = excellent local mixing; near 0.0 = extreme batch clustering. Target: > 0.5.

**Output columns (UMAP):** `umap_entropy_mean_RNA_BATCH`, `umap_entropy_norm_RNA_BATCH` (and same for `PLATFORM_RNA`, `RNASEQ_SOURCE`, `COHORT_LABEL`)

**Output columns (tSNE):** `tsne_entropy_mean_RNA_BATCH`, `tsne_entropy_norm_RNA_BATCH` (and same for `PLATFORM_RNA`, `RNASEQ_SOURCE`, `COHORT_LABEL`)

---

#### C3. Batch Centroid Dispersion in tSNE

**Same formulation as C1 but applied to tSNE 2D embedding.**

**Why tSNE separately from UMAP:** tSNE emphasizes local neighborhood structure differently. A normalization method may pass the UMAP test but fail on tSNE because it corrects global structure but leaves local batch clusters.

**Implementation:** `sklearn.manifold.TSNE(n_components=2, perplexity=30, random_state=42, method='barnes_hut')` on PCA(n=50) coordinates. Always run on the full dataset — no subsampling.

**Applied to batch columns:** `RNA_BATCH`, `PLATFORM_RNA`, `RNASEQ_SOURCE`, `COHORT_LABEL`

**Output columns:** `tsne_centroid_disp_RNA_BATCH`, `tsne_centroid_disp_PLATFORM_RNA`, `tsne_centroid_disp_RNASEQ_SOURCE`, `tsne_centroid_disp_COHORT_LABEL`

---

### 2.4 Group D — Distribution Comparison Metrics

---

#### D1. KS Test Mean D-statistic (gene-level)

**Reference:** Kolmogorov 1933. Applied to transcriptomics: Leek et al. 2010 batch effect review.

**What it measures:** For each gene, KS two-sample test comparing expression distributions between all pairs of batches/groups. The D statistic = maximum absolute difference between empirical CDFs.

**Applied to:** `RNA_BATCH`, `PLATFORM_RNA`, `COHORT_LABEL`

**Formula:**
```
For gene g and batch pair (B_i, B_j), i < j:
  D_g,ij = sup_x |F_{B_i}(x) − F_{B_j}(x)|

Aggregate:
  mean_KS_D_{col} = mean over all genes and all batch pairs
  frac_sig_KS_{col} = fraction of (gene, pair) combinations where p < 0.05 after BH correction
```

**How to interpret:**
- mean_KS_D near 0 → gene distributions well-aligned across groups
- frac_sig_KS near 0 → few genes differ significantly between groups

**Output columns:** `ks_mean_D_RNA_BATCH`, `ks_frac_sig_RNA_BATCH`, `ks_mean_D_PLATFORM_RNA`, `ks_frac_sig_PLATFORM_RNA`, `ks_mean_D_COHORT_LABEL`, `ks_frac_sig_COHORT_LABEL`

**Computational strategy:** All-pairwise batch comparisons; use a random sample of 1,000 genes for speed; BH correction via `statsmodels.stats.multitest.multipletests`. A per-group timeout of 1 hour is enforced: if D1 computation has not completed within 3,600 seconds, it is killed and the group's output keys are written as `null` with `"error_D": "timeout"`. All other metric groups continue unaffected.

---

#### D2. KS Test — Within-RNA_BATCH Cohort-Level D-statistic

**Same as D1 but measures within-RNA_BATCH cohort effects.** Where D1's `COHORT_LABEL` component compares each cohort against all other cohorts globally, D2 specifically isolates residual cohort effects within the same technology batch by comparing each cohort only against the pooled samples from its own `RNA_BATCH`. This detects lab-specific effects that platform-level normalization cannot remove (e.g., two different Affymetrix cohorts from different labs within `GPL570_FF_Unknown`).

**Output columns:** `ks_cohort_within_batch_mean_D`, `ks_cohort_within_batch_frac_sig`

---

#### D3. Per-gene Batch Mean CV (Coefficient of Variation of Batch Means)

**What it measures:** For each gene, CV of the per-batch mean expression values. Averaged across all genes.

**Formula:**
```
For gene g and grouping column col:
  μ_b = mean expression of gene g in group b
  CV_g = std(μ_1, ..., μ_B) / |mean(μ_1, ..., μ_B)|

mean_CV_{col} = mean(CV_g) over all genes
```

**Applied to:** `RNA_BATCH`, `COHORT_LABEL`, `PLATFORM_RNA`

**How to interpret:** near 0 → batch means well-aligned; > 0.5 → substantial batch-specific mean shifts remain.

**Output columns:** `per_gene_batch_mean_cv_RNA_BATCH`, `per_gene_batch_mean_cv_COHORT_LABEL`, `per_gene_batch_mean_cv_PLATFORM_RNA`

---

### 2.5 Group E — Data Quality and Descriptive Statistics

---

#### E1. Basic Dataset Dimensions

**Metrics:** `n_samples`, `n_genes`

---

#### E2. Batch and Cohort Structure

**Metrics:**
- `n_batches` — number of unique RNA_BATCH values
- `n_cohorts` — number of unique COHORT_LABEL values
- `n_diagnosis_groups` — number of unique Diagnosis_cell_type_unified values
- `n_samples_per_batch_min`, `n_samples_per_batch_max`, `n_samples_per_batch_median`, `n_samples_per_batch_sd` — distribution of batch sizes (SD added to capture spread)

**Why needed:** Essential context for interpreting all other metrics. The SD of batch sizes flags heavily imbalanced designs (e.g., one batch of 2,000 and twenty batches of 10) that can skew neighbor-based metrics.

---

#### E3. Zero Expression Fraction and Low-Expression Fraction

**Metrics:**
- `zero_fraction_global` — fraction of (sample, gene) pairs with exactly 0 expression
- `zero_fraction_by_batch_max` — maximum zero fraction across all batches
- `zero_fraction_by_batch_min` — minimum zero fraction
- `fraction_genes_below_1` — fraction of (sample, gene) pairs with expression value < 1 (including zeros); flags genes that are essentially silent regardless of normalization
- `below_1_fraction_by_batch_max` — maximum below-1 fraction across all batches
- `below_1_fraction_by_batch_min` — minimum below-1 fraction across all batches

**Why needed:**
- High zero fraction in some batches but not others indicates normalization artifacts.
- Microarray data should have very few zeros; high microarray zero fraction = data quality issue.
- `fraction_genes_below_1` additionally captures near-zero values that do not become exactly zero after transformation — relevant when comparing RNA-seq (sparse) vs. microarray (dense) post-normalization profiles.
- `below_1_fraction_by_batch_max/min` expose batch-specific near-zero patterns that global `fraction_genes_below_1` would average away.

---

#### E4. Expression Range, Percentile Statistics, and Bimodality

**Metrics (global):**
- `exp_min`, `exp_max`, `exp_median`, `exp_std`
- `exp_p01`, `exp_p05`, `exp_p25`, `exp_p75`, `exp_p95`, `exp_p99`
- `per_batch_median_cv` — CV of per-batch median expression

**Bimodality metrics (by COHORT_LABEL):**

For each cohort, fit the marginal expression distribution (across all genes × samples in that cohort) and test for bimodality using the **bimodality coefficient (BC)**:
```
BC = (skewness² + 1) / (kurtosis_excess + 3 × (n−1)² / ((n−2)(n−3)))
Threshold: BC > 5/9 ≈ 0.555 → bimodal
```

Additionally, fit a 2-component Gaussian Mixture Model per cohort. A cohort is classified as **zero-inflated bimodal** if:
- BC > 0.555 (bimodal), AND
- The lower GMM component mean < 1.0 in log2 space (one mode anchored near zero)

This pattern indicates cohorts where many genes are essentially not measured (FFPE degradation, sparse sequencing depth), leaving a prominent near-zero mode alongside a real expression mode.

**Metrics:**
- `n_cohorts_bimodal` — number of cohorts with BC > 0.555
- `fraction_cohorts_bimodal` — fraction of cohorts with bimodal distribution
- `n_cohorts_zero_inflated_bimodal` — number of cohorts with bimodal distribution and lower mode near zero (< 1.0)
- `fraction_cohorts_zero_inflated_bimodal` — fraction of such cohorts

**Implementation:** `scipy.stats.skew`, `scipy.stats.kurtosis`, and `sklearn.mixture.GaussianMixture(n_components=2)` per cohort. No additional package dependencies.

---

### 2.6 Group F — Gene-level Variance Decomposition (variancePartition)

---

#### F1. variancePartition Decomposition

**Reference:** Hoffman GE, Schadt EE. *BMC Bioinformatics* 17:483. 2016. DOI: 10.1186/s12859-016-1323-z.

**What it measures:** For each gene, partition total expression variance into fractions attributable to each specified variable using a mixed linear model.

**Applied to all columns:** `RNA_BATCH`, `Major_group`, `PLATFORM_RNA`, `RNASEQ_SOURCE`, `TUMOR_NORMAL`, `COHORT_LABEL`, `Diagnosis_cell_type_unified`

`COHORT_LABEL` treated as a random effect `(1|COHORT_LABEL)` (88 levels — too many for fixed effect). All others as fixed effects.

**Reported metrics per dataset:**
- `vp_median_RNA_BATCH`, `vp_p25_RNA_BATCH`, `vp_p75_RNA_BATCH` — batch fraction distribution
- `vp_median_Major_group`, `vp_median_PLATFORM_RNA`, `vp_median_RNASEQ_SOURCE`, `vp_median_TUMOR_NORMAL`, `vp_median_COHORT_LABEL`, `vp_median_Diagnosis_cell_type_unified`
- `vp_median_residual` — unexplained variance

**Why preferred over PCA R²:** Operates at gene level; simultaneously quantifies biology and technical noise at per-gene resolution; batch effect concentrated in a subset of genes is visible as high p75 even with low median.

**Computational note:** Run on a random sample of 2,000 genes. R-based via rpy2 file interface. Controlled by `--skip-slow` flag.

**Implementation:** R via rpy2 using the file-based interface (`fitExtractVarPartModel` with `BiocParallel` parallel workers).

---

### 2.7 Group G — Silhouette and Graph Connectivity

---

#### G1. Graph Connectivity

**Reference:** Luecken MD et al. *Nature Methods* 19(1):41–50. 2022. DOI: 10.1038/s41592-021-01336-8.

**What it measures:** For each biology group, checks whether all samples in that group are connected in the kNN graph regardless of batch. Captures whether biology groups are globally connected in kNN topology.

**Applied to biology columns:** `Major_group`, `PLATFORM_RNA`, `Diagnosis_cell_type_unified`, `TUMOR_NORMAL`

**Formula:**
```
For each biology group d:
  Build kNN graph restricted to samples of group d
  Count connected components C_d
  GC_d = 1 / C_d

Overall GC_{col} = mean(GC_d) over all groups of that column
```

**How to interpret:** GC = 1.0 → every group is fully connected across batches; GC < 0.5 → biological groups fragmented by batch effect.

**Output columns:** `graph_connectivity_Major_group`, `graph_connectivity_PLATFORM_RNA`, `graph_connectivity_Diagnosis_cell_type_unified`, `graph_connectivity_TUMOR_NORMAL`

**Implementation:** `sklearn.neighbors.kneighbors_graph`, `scipy.sparse.csgraph.connected_components`.

---

### 2.8 Group H — Average Pairwise Euclidean Distance

**What it measures:** In the full harmonized expression space (all genes), the average intra-group and inter-group pairwise Euclidean distances for each annotation column. Provides a direct, embedding-free view of how much samples from the same group resemble each other vs. samples from different groups.

**Applied to all annotation columns:** `RNA_BATCH`, `Major_group`, `PLATFORM_RNA`, `RNASEQ_SOURCE`, `TUMOR_NORMAL`, `COHORT_LABEL`, `Diagnosis_cell_type_unified`

**Formula:**
```
For annotation column col and groups g₁, g₂, ...:

  avg_intra_{col} = mean Euclidean distance between all pairs (i, j)
                    where label_col(i) = label_col(j)

  avg_inter_{col} = mean Euclidean distance between all pairs (i, j)
                    where label_col(i) ≠ label_col(j)

  dist_ratio_{col} = avg_intra_{col} / avg_inter_{col}
                     (lower = better mixing; higher = stronger grouping)
```

**How to interpret:**
- For **batch columns**: dist_ratio near 1 → samples from the same batch are no more similar to each other than to other batches (ideal batch removal). dist_ratio < 1 → within-batch distances are smaller → residual batch clustering.
- For **biology columns**: dist_ratio < 1 → biologically similar samples cluster tightly (good biology preservation). dist_ratio > 1 → biological structure is lost.

**Computational note:** Full pairwise computation is O(n²) and expensive for large datasets. Use subsampling to max 2,000 samples (random, no stratification) when n > 2,000. Distances computed on the full gene expression space (not PCA), as this metric is intended to complement PCA-based metrics.

**Output columns:** `avg_intra_dist_{col}`, `avg_inter_dist_{col}`, `dist_ratio_{col}` for each of the 7 annotation columns (21 columns total).

---

## 3. Summary of Output Metrics per Dataset

The following columns will be computed for each expression file. Per-column variants are shown using `{batch_col}` (= RNA_BATCH, PLATFORM_RNA, RNASEQ_SOURCE, COHORT_LABEL) and `{bio_col}` (= Major_group, PLATFORM_RNA, Diagnosis_cell_type_unified, TUMOR_NORMAL) and `{all_col}` (= all 7 annotation columns).

| Column(s) | Group | Description |
|---|---|---|
| `strat`, `imp`, `method`, `post_rm`, `harshness` | metadata | Job identifiers and tier |
| `n_samples`, `n_genes` | E1 | Dataset dimensions |
| `n_batches`, `n_cohorts`, `n_diagnosis_groups` | E2 | Unique group counts |
| `n_samples_per_batch_min`, `_max`, `_median`, `_sd` | E2 | Batch size statistics |
| `zero_fraction_global`, `zero_fraction_by_batch_max`, `zero_fraction_by_batch_min` | E3 | Zero-expression fractions |
| `fraction_genes_below_1`, `below_1_fraction_by_batch_max`, `below_1_fraction_by_batch_min` | E3 | Fraction of (sample, gene) pairs with expression < 1, plus per-batch extremes |
| `exp_min`, `exp_max`, `exp_median`, `exp_std` | E4 | Global expression statistics |
| `exp_p01`, `exp_p05`, `exp_p25`, `exp_p75`, `exp_p95`, `exp_p99` | E4 | Global expression percentiles |
| `per_batch_median_cv` | E4 | CV of per-batch median expression |
| `n_cohorts_bimodal`, `fraction_cohorts_bimodal` | E4 | Bimodal cohort count and fraction |
| `n_cohorts_zero_inflated_bimodal`, `fraction_cohorts_zero_inflated_bimodal` | E4 | Zero-inflated bimodal cohort count and fraction |
| `r2_RNA_BATCH`, `r2_Major_group`, `r2_PLATFORM_RNA`, `r2_RNASEQ_SOURCE`, `r2_TUMOR_NORMAL`, `r2_COHORT_LABEL` | A1 | PCA R² per covariate (mean over 10 PCs) |
| `r2_pc{1..10}_RNA_BATCH`, `r2_pc{1..10}_PLATFORM_RNA`, `r2_pc{1..10}_RNASEQ_SOURCE`, `r2_pc{1..10}_COHORT_LABEL` | A2 | Per-PC R² profiles for 4 batch columns (40 columns) |
| `pcr_{all_col}` (7 columns) | A3 | PCR: 1 − variance-weighted R² per covariate (higher = better) |
| `dsc_{batch_col}`, `dsc_pvalue_{batch_col}` (4×2 = 8 columns) | A4 | DSC ratio and permutation p-value per batch column |
| `kbet_acceptance_rate_{batch_col}` (4 columns) | B1 | kBET acceptance rate per batch column |
| `ilisi_mean_{batch_col}`, `ilisi_norm_{batch_col}` (4×2 = 8 columns) | B2 | iLISI mean and normalized per batch column |
| `clisi_mean_{bio_col}` (4 columns) | B3 | cLISI mean per biology column |
| `asw_batch_{batch_col}`, `asw_batch_norm_{batch_col}` (4×2 = 8 columns) | B4 | ASW for batch per batch column |
| `asw_bio_{bio_col}`, `asw_bio_norm_{bio_col}` (4×2 = 8 columns) | B5 | ASW for biology per biology column |
| `cms_mean_{batch_col}`, `cms_fraction_mixed_{batch_col}` (4×2 = 8 columns) | B6 | CMS mean and fraction well-mixed per batch column |
| `umap_centroid_disp_{batch_col}` (4 columns) | C1 | UMAP centroid dispersion per batch column |
| `umap_entropy_mean_{batch_col}`, `umap_entropy_norm_{batch_col}` (4×2 = 8 columns) | C2 | UMAP local batch entropy per batch column |
| `tsne_centroid_disp_{batch_col}` (4 columns) | C3 | tSNE centroid dispersion per batch column |
| `tsne_entropy_mean_{batch_col}`, `tsne_entropy_norm_{batch_col}` (4×2 = 8 columns) | C2 | tSNE local batch entropy per batch column |
| `ks_mean_D_RNA_BATCH`, `ks_frac_sig_RNA_BATCH`, `ks_mean_D_PLATFORM_RNA`, `ks_frac_sig_PLATFORM_RNA`, `ks_mean_D_COHORT_LABEL`, `ks_frac_sig_COHORT_LABEL` | D1 | KS D-statistic and fraction significant (all-pairwise) per batch column |
| `ks_cohort_within_batch_mean_D`, `ks_cohort_within_batch_frac_sig` | D2 | KS for within-RNA_BATCH cohort effects |
| `per_gene_batch_mean_cv_RNA_BATCH`, `per_gene_batch_mean_cv_COHORT_LABEL`, `per_gene_batch_mean_cv_PLATFORM_RNA` | D3 | CV of per-batch gene means per grouping column |
| `vp_median_RNA_BATCH`, `vp_p25_RNA_BATCH`, `vp_p75_RNA_BATCH` | F1 | variancePartition batch fraction (with IQR) |
| `vp_median_Major_group`, `vp_median_PLATFORM_RNA`, `vp_median_RNASEQ_SOURCE`, `vp_median_TUMOR_NORMAL`, `vp_median_COHORT_LABEL`, `vp_median_Diagnosis_cell_type_unified`, `vp_median_residual` | F1 | variancePartition per covariate |
| `graph_connectivity_{bio_col}` (4 columns) | G1 | kNN graph connectivity per biology column |
| `avg_intra_dist_{all_col}`, `avg_inter_dist_{all_col}`, `dist_ratio_{all_col}` (7×3 = 21 columns) | H | Average pairwise Euclidean distance per annotation column |
| `status`, `compute_time_s` | metadata | Job status and wall-clock time |

**Approximate total: ~205 metric columns per dataset.**

---

## 4. Architecture

### Design principles

1. **Per-harmonization JSON files.** Do not store all harmonization attempt metrics in a single file. Each job writes `FL_batch_correction/metrics/{strat}__{imp}__{method}__post{0|1}_metrics.json`. This prevents overwriting and allows crashed jobs to be retried without affecting already-computed results.

2. **Gene sets stored separately.** Each job also writes `FL_batch_correction/genes/{strat}__{imp}__{method}__post{0|1}_genes.json` containing the list of genes in the harmonized expression output. This file is needed for downstream gene set analysis and is particularly important for methods that reduce the gene space.

3. **Incremental JSON writing within each job.** Each metric group (E, A, B, C, D, F, G, H) is computed independently. Results are appended to the local JSON file immediately after each group completes. If a group fails, its keys are written as `null` with an `"error_{group}"` field containing the exception message; computation continues for all remaining groups. This ensures a partial result is always better than no result. All exceptions are logged to stdout with full tracebacks so that debugging from pod logs does not require a separate log file.

4. **Shared pre-computed embeddings.** Within a single job, PCA (n=50), UMAP (2D on PCA), and tSNE (2D on PCA) are computed once after data loading and reused by all metric groups that require them. This avoids redundant computation across groups A, B, C, G, H.

5. **Job-level independence.** One job = one expression file. Jobs do not share state. The dispatcher launches them in parallel; each has its own process, downloads its own files, and writes its own JSON sidecar.

6. **Skip-if-exists.** Before downloading expression data, check whether the S3 metrics JSON sidecar already exists → write `{"status": "cached"}` and exit.

7. **Separate aggregation script.** `run_metrics_concat.py` reads all per-harmonization JSON files from S3 and concatenates them into `metrics_comprehensive.csv`. Run independently from the dispatcher — allows aggregation after partial runs.

### New files

All new scripts live in a dedicated `harmonization-metrics/` directory, separate from `harmonization-scripts/`, to keep concerns cleanly separated.

```
harmonization-metrics/
├── run_metrics_job.py          ← Worker: one expression file → JSON metrics + JSON genes
├── run_metrics_parallel.py     ← Dispatcher: all expression files → launches jobs
├── run_metrics_concat.py       ← Aggregation: all JSON sidecars → metrics_comprehensive.csv
├── compute_batch_metrics.py    ← Library: all metric computation functions
├── test_mock_metrics.py        ← Mock tests for the metrics library
├── requirements.txt            ← Metrics-only Python dependencies (no normalization packages)
├── README.md                   ← Step-by-step guide: pod setup, rsync, running, aggregation
└── k8s/
    └── pod-metrics.yaml        ← K8s pod for metrics calculation (analogous to pod-ssh.yaml)
```

`compute_batch_metrics.py` is a dedicated library, not merged into `bench_shared.py`, to keep concerns separated. It has different dependencies (`umap-learn`, `statsmodels`, bimodality logic) and is not needed for normalization runs.

### Data flow

```
S3: exp/{strat}__{imp}__{method}__post{0|1}.tsv.gz
S3: prepared/{strat}__{imp}__ann.tsv.gz
              ↓ download + align by index intersection
    exp_df (samples × genes), ann_df (samples × metadata)
              ↓
    [1] Write gene list → FL_batch_correction/genes/{key}_genes.json
              ↓
    [2] Compute shared embeddings: PCA(50), UMAP(2D), tSNE(2D)
              ↓
    [3] For each metric group independently (E → H):
          compute group metrics → append to local metrics dict
          write partial JSON to /tmp/{key}_metrics.json (incremental)
          on failure: log full traceback to stdout, write null values + error message, continue
              ↓
    [4] Upload /tmp/{key}_metrics.json
          → FL_batch_correction/metrics/{key}_metrics.json

Aggregation (run_metrics_concat.py):
    List all FL_batch_correction/metrics/*_metrics.json
    → download each → pd.DataFrame → upload metrics_comprehensive.csv
```

### Annotation alignment strategy

1. Download prepared annotation for `(strat, imp)` from `prepared/{strat}__{imp}__ann.tsv.gz`
2. Intersect: `ann_df = ann_df.loc[ann_df.index.intersection(exp_df.index)]`
3. Assert `len(ann_df) == len(exp_df)` before proceeding

---

## 5. Implementation Steps

### Step 1: Create `compute_batch_metrics.py` — metric library ✓ COMPLETED

1.1 Define `compute_pca(exp_df, n_components=50) → np.ndarray` — PCA coordinate matrix; wraps StandardScaler + PCA; handles NaN with `fillna(0)`.

1.2 Define `compute_umap(pca_coords) → np.ndarray` — 2D UMAP on PCA coordinates.

1.3 Define `compute_tsne(pca_coords) → np.ndarray` — 2D tSNE with Barnes-Hut on the full dataset (no subsampling).

1.4 Implement `compute_group_e(exp_df, ann_df) → dict` — all Group E metrics (distribution stats, zero fractions, below-1 fractions, bimodality).

1.5 Implement `compute_group_a(pca_coords, ann_df) → dict` — R² profile per covariate (A1), per-PC R² (A2), PCR (A3), DSC (A4).

1.6 Implement `compute_group_b(pca_coords, ann_df) → dict` — kBET (B1), iLISI (B2), cLISI (B3), ASW_batch (B4), ASW_bio (B5), CMS (B6). All on PCA coordinates.

1.7 Implement `compute_group_c(umap_coords, tsne_coords, ann_df) → dict` — centroid dispersions and entropy in UMAP (C1, C2) and tSNE (C2, C3).

1.8 Implement `compute_group_d(exp_df, ann_df, n_genes_max=1000, timeout_s=3600) → dict` — KS tests all-pairwise with timeout (D1, D2), batch mean CV for three grouping columns (D3).

1.9 Implement `compute_group_f(exp_df, ann_df, n_genes=2000) → dict` — variancePartition via R/rpy2 file interface. Optional; controlled by `skip_slow` flag.

1.10 Implement `compute_group_g(pca_coords, ann_df) → dict` — graph connectivity per biology column.

1.11 Implement `compute_group_h(exp_df, ann_df, subsample=2000) → dict` — average pairwise Euclidean distances per annotation column.

1.12 Implement `compute_all_metrics(exp_df, ann_df, skip_slow=False) → dict` — orchestrator. Computes shared embeddings once, then calls each group function independently in try/except blocks. On exception: logs full traceback to stdout, writes null values + error message to the output dict, continues to the next group. Writes the output dict incrementally to a temporary file after each group.

### Step 2: Create `run_metrics_job.py` — worker script ✓ COMPLETED

2.1 Parse CLI: `--key`, `--strat`, `--imp`, `--method`, `--post-rm`, `--out-json`, `--out-genes-json`, `--memory-limit-gb`, `--skip-if-exists`, `--skip-slow`.

2.2 Fast-path skip: check if S3 metrics sidecar already exists → write `{"status": "cached"}` and exit.

2.3 Memory check (same pattern as `run_norm_job.py`).

2.4 Download expression and annotation. Align by index intersection.

2.5 Write gene list to `--out-genes-json` and upload to `FL_batch_correction/genes/{key}_genes.json`.

2.6 Call `compute_all_metrics(exp_df, ann_df, skip_slow=args.skip_slow)` — incremental JSON writing happens inside.

2.7 Add metadata columns: `strat`, `imp`, `method`, `post_rm`, `harshness`, `status`, `compute_time_s`.

2.8 Upload metrics JSON to `FL_batch_correction/metrics/{strat}__{imp}__{method}__post{0|1}_metrics.json`.

2.9 On top-level exception: log full traceback to stdout, write `{"status": "failed", "error": str(e)}`, exit 1.

### Step 3: Create `run_metrics_parallel.py` — dispatcher script ✓ COMPLETED

3.1 Parse file list from S3 prefix `FL_batch_correction/exp/` or `--file-list` path.

3.2 Build job grid: for each `{strat}__{imp}__{method}__post{0|1}.tsv.gz`, create a job record.

3.3 Optional filter: `--post-rm-filter post0` to run only `post_rm=False` variant.

3.4 Parallelism: `ThreadPoolExecutor(n_workers)` — each thread calls `subprocess.run(["python", "run_metrics_job.py", ...])`. Same pattern as `run_norm_parallel.py`.

3.5 Memory guard: level-1 dispatcher RAM check.

3.6 Progress tracking: log `[HH:MM:SS] DONE {key} (Ns) → {status}` per completed job.

3.7 CLI:
```
--n-workers N          (default: 4)
--skip-if-exists       skip jobs whose S3 JSON sidecar exists
--retry-failed         retry jobs in failed_jobs_metrics.txt
--post-rm-filter {post0, post1, both}  (default: both)
--skip-slow            skip variancePartition (Group F)
--memory-limit-gb N    (default: 6.0)
--timeout-s N          (default: 600; slow mode: 3600)
--file-list PATH       path to file list (default: auto-list from S3)
```

### Step 4: Create `run_metrics_concat.py` — aggregation script ✓ COMPLETED

4.1 List all `FL_batch_correction/metrics/*_metrics.json` objects on S3.

4.2 Download each JSON, parse, append to list of dicts.

4.3 Build `pd.DataFrame`, resolve column ordering (metadata first, then groups E → H).

4.4 Upload as `FL_batch_correction/metrics_comprehensive.csv`.

4.5 Print summary: N total files, N successful, N failed, N cached.

### Step 5: Create `test_mock_metrics.py` — separate mock test file ✓ COMPLETED

Add a dedicated smoke test that:
- Creates a synthetic 80-sample × 200-gene matrix with 3 batches, 2 cohorts, and 2 diagnosis groups
- Calls `compute_all_metrics(exp_df, ann_df, skip_slow=True)`
- Asserts that all expected keys exist in the output dict
- Asserts that a perfectly random batch assignment gives `r2_RNA_BATCH < 0.1`
- Asserts that a strongly batch-structured matrix (genes drawn from different distributions per batch) gives `r2_RNA_BATCH > 0.5`
- Tests that a single metric group failure does not prevent other groups from producing results

Keep this as a standalone file (`test_mock_metrics.py`) separate from the normalization smoke test (`test_mock.py`).

### Step 6: Create `harmonization-metrics/` directory and K8s pod specification ✓ COMPLETED

Create the `harmonization-metrics/` directory containing all scripts listed in Section 4 plus:

**`harmonization-metrics/requirements.txt`** — metrics-only Python dependencies; deliberately excludes normalization-specific packages (harmonypy, scanorama, combat, inmoose) that are not needed here and take significant time to install:
```
boto3
pandas
numpy
scikit-learn
scipy
umap-learn>=0.5
statsmodels>=0.14
rpy2
psutil
```

**`harmonization-metrics/README.md`** — step-by-step running guide (modelled after `harmonization-scripts/k8s/README.md`), covering: pod creation, waiting for environment ready, SSH/port-forward setup, rsync from local Mac, mock test, single-job test, full dispatcher run, aggregation, and result download. The rsync command in README copies only the `harmonization-metrics/` directory to the pod (not the entire repo):
```bash
rsync -avz --progress -e "ssh -p 2222 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
    ~/fl_subset/harmonization-metrics/ \
    root@localhost:/app/harmonization-metrics/
```

**`harmonization-metrics/k8s/pod-metrics.yaml`** — new pod spec analogous to `k8s/pod-ssh.yaml`. Key differences from `pod-ssh.yaml`:

- Pod name: `fl-metrics`
- ConfigMap names: `fl-metrics-deps`
- Inline `requirements.txt` in ConfigMap uses the metrics-only dependency list above
- R install script adds `BiocManager::install(c('variancePartition', 'BiocParallel'), ask=FALSE)`
- Same SSH setup, same PVC mount, same AWS credentials, same resource requests
- Startup prints `[startup] Metrics environment ready.` when safe to run

### Step 7: End-to-end test, production run, and aggregation ✓ COMPLETED (documented in README.md)

Steps 7 onwards (local package verification, end-to-end test run, full K8s production run, and result aggregation) are documented in `harmonization-metrics/README.md` as the operational running guide. Follow that document when executing the pipeline.

---

## 6. Computational Complexity and Runtime Estimates

| Metric group | Time per file | Notes |
|---|---|---|
| Group E (data quality + bimodality) | < 10 s | GMM per cohort adds ~2–5 s |
| Group A (PCA R²) | ~20–40 s | PCA(50) + ANOVA × 7 covariates + per-PC profiles |
| Group H (Euclidean distances) | ~10–30 s | Subsample to 2,000; full gene space |
| Group B (kBET, LISI, ASW, GC) | ~60–120 s | kNN × 4 batch cols + 4 bio cols |
| Group D (KS tests) | ~30–120 s | 1,000 genes × all-pairwise; 1-hour hard timeout |
| Group G (graph connectivity) | ~20–40 s | kNN graph × 4 bio cols |
| Group C (UMAP) | ~60–120 s | UMAP on PCA(50) for n=5,000 |
| Group C (tSNE) | ~120–600 s | Barnes-Hut on full dataset (no subsampling) |
| Group F (variancePartition) | ~600–1800 s | R-based; parallel across 2,000 genes |

**Fast mode** (skip_slow=True): 
~5–10 min per file → 533 files × 4 workers ≈ ~4–6 hours total

**Full mode** (all metrics):
~15–30 min per file → ~25–40 hours total; run only on top-K files

---

## 7. Dependencies

### Python (harmonization-metrics/requirements.txt)
| Package | Use | Notes |
|---|---|---|
| `boto3` | S3 I/O | |
| `pandas`, `numpy` | Data structures | |
| `scikit-learn` | PCA, kNN, silhouette, GMM, tSNE | |
| `scipy` | chi2 test, KS test, AD test, skewness/kurtosis | |
| `umap-learn>=0.5` | UMAP embedding | **NEW** |
| `statsmodels>=0.14` | BH correction for KS tests | **NEW** |
| `rpy2` | variancePartition via R (Group F) | |
| `psutil` | Memory guards | |

### R (installed in pod via install script)
| Package | Use | Notes |
|---|---|---|
| `variancePartition` | Variance decomposition (Group F) | **NEW** |
| `BiocParallel` | Parallel execution in variancePartition | **NEW** |

---

*End of implementation plan. No implementation should begin until this plan is reviewed and approved.*
