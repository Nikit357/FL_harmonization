# Angel — Usage Perspectives for Multi-Platform Bulk RNA Harmonization

**Full name (paper title):** "A simple, scalable approach to building a cross-platform transcriptome atlas"  
**Authors:** Angel PW, Rajab N, Deng Y, Pacheco CM, Chen T, Lê Cao K-A, Choi J, Wells CA  
**Reference:** *PLOS Computational Biology* 16(9), e1008219 (2020). https://doi.org/10.1371/journal.pcbi.1008219  
**Code:** https://bitbucket.org/stemformatics/s4m_pyramid/src/master/scripts/atlas.py (Python)  
**Web atlas:** https://www.stemformatics.org/atlas/blood

**Context:** Evaluation of Angel as a harmonization candidate for ~5,444 samples across 88 cohorts from mixed platforms (Affymetrix GPL570, Illumina NGS, Illumina microarray, Agilent microarray). Reference batch: RNASeq_FF_PolyA (n=1,039). Current benchmark winner: FSQN (R) at ~16% PCA variance explained by batch (down from ~95% raw).

---

## What Angel Actually Does — Core Concept

Angel is an **atlas construction framework**, not a traditional batch correction method. Its philosophy is the inverse of ComBat, FSQN, and limma: rather than transforming expression values to remove batch effects, it **removes the genes that carry platform signal** and maps the remaining genes onto a PCA reference space. Batch effects are not corrected — they are sidestepped by gene selection.

The method has three conceptual components:

1. **Rank-percentile transformation** — maps each sample's expression values to [0,1], making the representation platform-agnostic at the per-sample level
2. **Platform variance filtering** — discards genes where platform membership explains ≥20% of total variance
3. **PCA + projection** — builds a low-dimensional reference space from the filtered, rank-transformed data; new samples project in without re-normalization

The authors explicitly avoid ComBat, limma, and RUV-III, which they argue "enforce strong transformations to data structure that meaningful biological signal is removed."

---

## Algorithm — Complete Step by Step

### Step 1: Rank-percentile transformation

For each sample independently, rank all genes by expression value. Assign the highest-expressed gene rank 1.0, the lowest rank 0.0, with ties averaged. The result is a genes × samples matrix with values in [0,1].

This is applied identically to microarray intensities and RNA-seq RPKM values, making the two data types directly comparable in rank space without any platform-specific scaling.

### Step 2: Platform variance partitioning (gene filtering)

For each gene g, fit the univariate linear model:

```
y_g = X_platform · β_platform + ε
```

Compute the platform variance fraction:

```
platform_fraction_g = Var(X_platform · β_platform) / Var(y_g)
```

Retain only genes where `platform_fraction_g < threshold` (default threshold = 0.20). In the blood atlas application this reduced 13,661 common genes to ~3,700 (≈27% retained).

**Effect of threshold:**
| Threshold | Genes retained |
|---|---|
| 0.05 | ~500 |
| 0.20 (default) | ~3,700 |
| 0.50 | ~10,000 |

Roughly 25% of genes in the paper's dataset had >50% variance explained by platform and were excluded at any reasonable threshold.

### Step 3: PCA

Run PCA on the rank-transformed, platform-variance-filtered matrix. Components are ordered by variance explained. Gene loadings are stored for projection.

### Step 4: Clustering (optional)

Apply K-Means or Agglomerative hierarchical clustering to the PCA coordinates. Optimal cluster count k is determined by Jaccard-H-index stability analysis across bootstrap resamples. In the blood atlas: k=6 whole blood, k=5 myeloid, k=4 lymphocyte.

### Step 5: Projection of new data

New samples are rank-transformed (same [0,1] normalization), restricted to the atlas gene list, and multiplied by the stored PCA loadings:

```
new_coords = loadings · new_sample_ranks
```

No re-fitting is required. New samples do not alter the atlas.

### Step 6: Recursive refinement (optional)

Repeat steps 1–4 on biological subsets (e.g., myeloid-only samples) to reveal finer resolution within the coarse clusters.

---

## Input Data Requirements

- Expression matrices: microarray intensities or RNA-seq RPKM, any number of platforms
- Only genes measurable across all platforms are used (intersection)
- No matched samples required
- No reference batch designation required
- Preprocessing: standard within-platform normalization (e.g., RMA for Affymetrix) before input

---

## Output

- Rank-percentile expression matrix restricted to platform-low-variance genes (genes × samples, values [0,1])
- PCA coordinates per sample (visualization/clustering)
- Cluster assignments
- Gene loading vectors (for projection)
- Interactive web atlas (for the blood implementation)

**Critically: the primary output used for biological interpretation is PCA coordinates, not a corrected expression matrix.** The rank-transformed filtered matrix exists as an intermediate but the authors use it only as input to PCA.

---

## Validation

**Blood cell atlas:** 850 samples, 38 independent datasets, 5 platforms, covering the full blood cell differentiation hierarchy (progenitors, myeloid, lymphoid). Sources: GEO, ArrayExpress, Human Cell Atlas.

**External projection validation:**
- Haemosphere bulk RNA-seq cohort: projects to expected positions ✓
- van Galen et al. scRNA-seq (pseudo-aggregated): myeloid/lymphoid arms resolve correctly ✓
- Single-cell individual projections: "did not work very well" — the rank distribution of individual cells differs too strongly from bulk

**Stability analysis (bootstrap, 500 iterations):**
- Whole blood (k=6): H-index ≈ 0.90
- Myeloid subset (k=5): H-index ≈ 0.90
- Lymphocyte subset (k=4): H-index ≈ 0.75–0.79

**Gene set stability:**
- 93% median overlap across 500 bootstrap iterations
- 97% median overlap in leave-one-out analysis

**No quantitative comparison with batch correction methods is reported** — supplementary t-SNE comparisons with limma+voom and ComBat are visual only, with no numerical metrics.

---

## Stated Limitations

1. **Rank transformation loses expression magnitude.** The scale of difference between two expression values is discarded; only relative ordering is preserved. This removes information about fold-change magnitude.

2. **Gene filtering may exclude biologically relevant markers.** A cell-type marker gene that is also platform-biased will be removed, reducing the discriminatory power for that cell type.

3. **PCA captures only linear structure.** Non-linear biological manifolds (e.g., differentiation trajectories) are not well represented.

4. **Single-cell projection fails.** Individual scRNA-seq cells have fundamentally different rank distributions (sparse, zero-inflated) and cannot be projected directly. Pseudo-aggregation into pseudo-bulk is required.

5. **Requires large diverse datasets.** The variance partitioning in Step 2 becomes unstable with few samples or few platforms represented. Recursive refinement degrades with <255 samples per biological arm.

6. **Biological confounding not modelled.** If a diagnosis group is concentrated on one platform, the variance attributed to "platform" will be partially biological variance, and the filtering will remove biologically informative genes.

---

## Assessment for This Project

### The fundamental distinction: gene selection vs. expression correction

Angel's approach is mechanistically different from every other method in the benchmark. FSQN, ComBat, limma, TDM, and Shambhala2 all transform expression values to remove batch effects while keeping the full gene set. Angel instead **discards the genes that carry batch signal** and transforms the survivors to rank space.

This has a critical implication for the benchmark metric (PCA R² of RNA_BATCH): Angel would trivially produce a low R² not by correcting platform effects but by removing the genes that drive them. The resulting metric is not comparable to other methods — it measures a smaller, preselected gene space. Adding Angel as `26_angel` to the METHODS registry would produce a misleading entry in the metrics table.

### Relationship to existing method 18_rank

The rank-percentile transformation in Angel is **essentially identical** to `normalize_rank` (`18_rank`) already in the benchmark. Both convert each sample's gene expression to fractional ranks in [0,1]. The only difference is that Angel applies rank transformation after gene filtering, whereas `18_rank` applies it to the full gene set.

The unique contribution of Angel relative to what the benchmark already contains is the **platform variance gene filter** (Step 2). This is a preprocessing/feature selection step, not a normalization method in the classical sense.

### Multi-platform validation is strong — but for atlas construction, not downstream matrices

Angel is validated on 850 samples across 5 platforms with no matched data required and no reference batch — the most permissive design of all methods reviewed. This is the right setting for our dataset. However, the output it is designed to produce is a **PCA atlas for visualization and cell typing**, not a harmonized expression matrix for oposSOM input or S3 storage.

oposSOM requires a genes × samples expression matrix in the original feature space. Providing rank-transformed, gene-filtered values to oposSOM is technically possible, but:
- The gene space would be reduced (3,700 instead of 3,520 common genes — slightly different set)
- Rank [0,1] values as SOM input conflict with the expectation of log2 expression values in most SOM portrait interpretations
- The `18_rank` method already benchmarks the rank transformation approach, and its batch R² result directly answers the question of how well rank normalization works for this dataset

### The gene filtering idea has independent merit

The Step 2 variance partitioning approach — identifying genes with high platform variance fractions — is worth applying as a **diagnostic tool** separate from the Atlas pipeline:

- Running the variance filter on the FL dataset would identify which of the 3,520 common genes are most platform-confounded
- These genes could be flagged in SOM portrait analysis as potentially platform-driven signals
- This is distinct from using Angel as a normalization method and does not require changing the benchmark design

---

## Comparison with Current Benchmark Methods

| Aspect | Angel | FSQN (best) | 18_rank | ComBat |
|---|---|---|---|---|
| Core mechanism | Rank transform + gene filter + PCA | Per-gene quantile replacement | Fractional rank per sample | Empirical Bayes shift |
| Output format | PCA coordinates (primary); rank matrix (intermediate) | Genes × samples matrix | Genes × samples matrix | Genes × samples matrix |
| Gene space | Reduced (~3,700 of 13,661; threshold-dependent) | Full gene set | Full gene set | Full gene set |
| Matched data required | No | No | No | No |
| Reference batch required | No | Yes (RNASeq_FF_PolyA) | No | No |
| Multi-platform validated | Yes (5 platforms, 850 samples) | Yes | Implicit | Partial |
| Batch R² comparability | **Not comparable** (gene set changed) | Direct | Direct | Direct |
| Rank transformation | [0,1] per sample | No | Fractional rank per sample | No |
| Biological signal preserved | High (by design — only low-platform-variance genes) | High | Moderate | Moderate |
| Suitable as oposSOM input | No (PCA coordinates; rank values suboptimal) | Yes | Yes | Yes |

---

## Verdict

**Angel is not suitable as a benchmark normalization method** for the cross-product evaluation.

The primary reason is structural: its batch reduction mechanism is gene selection, not expression transformation. A comparison of PCA R² values between Angel and FSQN/ComBat/rank would be apples-to-oranges — Angel achieves low platform variance by discarding platform-confounded genes, not by correcting their values.

A secondary reason is output format: the biologically meaningful output of Angel is PCA coordinates for atlas visualization, not a corrected expression matrix for SOM input.

**What Angel offers that is genuinely useful:**

The variance partitioning step (Step 2) is a powerful *diagnostic* for this dataset. Applied to the 3,520 common genes across 88 cohorts, it would identify which genes are most platform-biased and which are platform-stable — directly informing which SOM metagene signals can be trusted across platforms. This analysis could be run as a standalone gene annotation step without any benchmark changes.

**FSQN (R) remains the benchmark winner.** The rank-percentile transformation in Angel is already represented by `18_rank` in the benchmark. The gene filtering concept is worth applying as a diagnostic but does not belong in the normalization cross-product.
