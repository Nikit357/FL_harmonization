# FL Project Update Slides — 2026-05-14

## SLIDE 1 — Title
**Title:** Best harmonization approach: per aspera ad astra

## SLIDE 2 — Agenda
**Title:** Agenda for May 14th
**Content:**
- Recap the analysis
- Clustermap of all tested harmonization approaches, general trends
- Visual inspection of the best approaches on PCA/UMAP/tSNE
- Trends in global metrics
- Incomplete results in local metrics
- Shambhala harmonization discussion
- Action points

## SLIDE 3 — Analysis Overview
**Title:** Two-stage computational pipeline architecture
**Content:**
- **RAW DATA (S3):** `comb_exp.tsv` (~1.9 GB, ~7,174 samples × ~20,000 genes)
- **STAGE 1 — FILTER STRATEGIES:**
    - S0: No removal
    - A: Confirmed bad
    - B: Extended bad
    - C: RNASeq only
    - D: Malignant only
    - E1 / E2 / E3: Iterative PCA-based removal
    - F: Microarray only
    - G: Affymetrix only
- **STAGE 2 — Imputation:**
    - strict: dropna → 3,520 genes
    - knn: KNNImputer → ~12k genes (S0)
    - missforest: FAILED (>24h / 240 GB)
    - softimpute: softImpute → ~11k genes (S0)
- **STAGE 3 — Pre-processing:** `log_transform_by_cohort()` [log2(x+1) where max > 30]
- **STAGE 4 — NORMALIZATION (25 methods):**
    - Low: raw, median_scaling, limma, sva, tmm, vst
    - Med: combat, pycombat, ruv, mnn, harmony, scanorama, harmonizr, peer, inmoose, combat_seq, fsmvn
    - High: qsmooth, fsqn_py, fsqn_r, quantile, rank, tdm, shambhala, angel
- **STAGE 5 — Post-Normalization Batch Removal:** `post_rm=False` (post0) vs `post_rm=True` (post1, remove outliers)
- **STAGE 6 — Metrics Calculation**

## SLIDE 4 — Dataset Description
**Title:** 88 когорт для анализа. NGS + чипы, 7238 семплов
**Table: Sample Distribution by Group**
| Группа | #семплов |
| --- | --- |
| DLBCL | 4466 |
| FL | 1687 |
| High_Grade_B_Cell_Lymphoma | 34 |
| Double_Hit_Lymphoma | 17 |
| Burkitt_Lymphoma | 88 |
| Other (from Arsen) | 25 |
| В клетки из Normal_B_cells | 733 |
| В клетки из Кассандры | 142 |

**Table: Sample Distribution by RNA_BATCH**
| RNA_BATCH | Platform_classified | count |
| --- | --- | --- |
| RNASeq_FF_PolyA | Illumina NGS | 1063 |
| GPL570_Unknown_Unknown | Affymetrix Microarray | 1030 |
| GPL570_FF_Unknown | Affymetrix Microarray | 983 |
| RNASeq_FFPE_Exome_capture | Illumina NGS | 929 |
| GPL14951_FFPE_Unknown | Illumina Microarray | 810 |
| GPL570_FFPE_Unknown | Affymetrix Microarray | 800 |
| GPL96+97_FF_Unknown | Affymetrix Microarray | 305 |
| GPL13938_FFPE_Unknown | Illumina Microarray  | 167 |
| GPL96_FF_Unknown | Affymetrix Microarray | 133 |
| GPL6244_FF_Unknown | Affymetrix Microarray | 131 |
| GPL8432_FFPE_Unknown | Illumina Microarray | 130 |
| RNASeq_FF_rRNADepletion | Illumina NGS | 117 |
| GPL96_FFPE_Unknown | Affymetrix Microarray | 84 |
| RNASeq_FF_Unknown | Illumina NGS | 79 |
| GPL20188_FF_Unknown | Illumina NGS | 68 |
| GPL16686_FF_Unknown | Affymetrix Microarray | 48 |
| GPL13158_FF_Unknown | Affymetrix Microarray | 40 |
| GPL17586_FF_Unknown | Affymetrix Microarray | 40 |
| GPL1708_FF_Unknown | Agilent Microarray | 40 |
| GPL23541_FF_Unknown | Illumina NGS | 35 |
| RNASeq_FFPE_PolyA | Illumina NGS | 35 |
| RNASeq_FF_Total | Illumina NGS | 32 |
| GPL17077_FF_Unknown | Agilent Microarray | 24 |
| GPL887_FFPE_Unknown | Agilent Microarray | 24 |
| GPL26356_FF_Unknown | Illumina NGS | 15 |
| GPL17047_FF_Unknown | Affymetrix Microarray | 12 |
| GPL570_FF_Unknown | Illumina NGS | 11 |
| GPL6244_FFPE_Unknown | Affymetrix Microarray | 11 |
| GPL17077_FF_Unknown | Agilent Microarray | 9 |
| GPL10739_FF_Unknown | Affymetrix Microarray | 4 |
| RNASeq_FF_Exome_capture | Illumina NGS | 2 |

**Content:**
- Affymetrix Microarray: 3821
- Illumina NGS: 2386
- Illumina Microarray: 940
- Agilent Microarray: 64

## SLIDES 5-7 — Harmonization Results & Clustermaps
**Title:** Selection of the best approaches - large clustermap of all metrics
**Content:**
- **Worst approaches:** Preserve local batch-effect.
- **So-so:** RNASeq only cluster.
- **Best!:** MNN approaches.
- **Promising:** 
    1. MNN (best group).
    2. SVA in RNASeq only.
    3. Rank in RNASeq only.
    4. Affymetrix extended, FSQN R.
    5. Angel (Better normalization, but with trade-offs).
- **Metric Clusters:**
    - **Cluster 1:** Almost always bad, local neighborhood metrics (kBET, cLISI, iLISI, entropy).
    - **Cluster 2:** Mostly bad, local neighborhood, global and KS metrics.
    - **Cluster 3:** Mostly good, global metrics (Distance ratio, KS distribution test, centroids, CMS, silhouette width).
    - **Cluster 4:** Almost always good, global metrics (Dispersion separability, PCR, centroids, silhouette width).

## SLIDE 8 — Trends of the Best Approaches (MNN)
**Title:** Trends of the best approaches: MNN is the best harmonization approach regardless of imputation and batch removal
**Content:**
- 60% of tested approaches are "bad" (30-40% of metrics < 0.5).
- RNASeq only selection clusters as "so-so".
- 16/19 MNN instances (excluding RNASeq only) cluster separately with > 75% metrics > 0.5.
- For MNN: KNN and strict imputation outperform softimpute.
- **Absolutely the best MNN approaches (Strict):**
    - B extended bad
    - A confirmed bad
    - E1, E2, E3 iterative
- **Best MNN approaches (KNN-imputed, for more genes):**
    - B extended bad
    - A confirmed bad
    - E1, E2, E2 iterative

## SLIDE 9 — Additional Promising Cases
**Title:** Trends of the best approaches: 3 more promising cases
**Content:**
- SVA in RNASeq only
- Rank in RNASeq only
- Affymetrix extended, FSQN R
- *Note:* Genes and GO processes accumulation to be studied in these approaches, including FL ones.

## SLIDE 10 — Metrics Behavior Trends
**Title:** Trends by metrics behavior: all the tools handle local intermixing worse than global distances.
**Content:**
- **Local Metrics (Cluster 1):** Measure local neighborhood/batch-effect (entropy, cLISI/iLISI, kBET). Generally bad across most methods, only 1/3 good for the best methods.
- **Graph Connectivity:** Best for RNASeq only cluster; moderate for MNN cluster.
- **KS Similarity (Gene-level distributions):** Best for RNASeq only cluster; mild to moderate elsewhere.
- **Fraction of Bimodal Distributions:** Generally low, except for Angel and Rank normalization.
- **Global Metrics (Clusters 3 & 4):** Distance ratio, centroids, silhouette width, dispersion separability. Usually well-handled by all approaches.
- **RNASeq only cluster performance:** Worse than others regarding FF/FFPE tSNE/UMAP centroids separation.

## SLIDES 11-14 — Factor Comparisons
**Title:** Comparison by strategies, methods, and imputation
**Content:**
- **Strategies (Slide 11):** RNASeq only is best; Malignant only is worst. Others are comparable.
- **Methods (Slide 12):** MNN is the best overall. Median scaling, limma, pycombat, and fsmvn show better local mixing and PC R² but worse distance ratio by RNA batch.
- **Imputation (Slide 13):** No significant differences. KNN/Softimpute are safe to use for more genes.
- **Ordering (Slide 14):** No significant trend by columns for metrics calculation.

## SLIDES 15-20 — Visual Inspection: MNN Group
**Title:** Visual inspection of the best approaches - MNN
**Content:**
- PCA/UMAP/tSNE by batch and biology: **Bad**.
- Same diagnoses from different batches cluster differently.
- Always two DLBCL batch outliers (consider removal).
- Potential improvement after removing `GPL570_FFPE_Unknown`.

## SLIDES 21-24 — Visual Inspection: RNASeq only + SVA
**Title:** Promising 2. RNASeq only and SVA normalization
**Content:**
- Best among RNASeq only attempts.
- **Best approach for visual correction** of batch effect (PCA/UMAP/tSNE) tested to date.
- No batch effect; FF and FFPE are mixed.
- Biology is separated; two FL groups identified (potential biological signal).
- *Constraint:* Impossible without imputation.

## SLIDES 25-28 — Visual Inspection: RNASeq only + Rank
**Title:** Promising 3. RNASeq only and rank normalization
**Content:**
- Batch effect still present between FF and FFPE in DLBCL.

## SLIDES 29-32 — Visual Inspection: FSQN R + Affymetrix Extended
**Title:** Promising 4. FSQN R, Affymetrix extended (3609 samples)
**Content:**
- Biology separates, but batch effect is preserved.

## SLIDES 33-35 — Metrics Insights & Trade-offs
**Title:** Comparisons by metrics groups: trends and insights
**Content:**
- **Trade-off:** Methods resolving global distances well often poorly handle local mixing (Slide 34).
- **Hierarchy of Importance (Slide 35):**
    1. Batch removal strategy
    2. Harmonization method
    3. Post-removal
    4. Imputation
- Recommendation: "Mine" good clusters for rare "diamonds".

## SLIDES 37-46 — PCA and PCR Metrics Deep Dive
**Title:** Global PCA-related metrics
**Content:**
- **PCR (Slide 39):** `dwd`, `qsmooth` are best for global metrics. `fsqn` lowers PCR for most factors except RNASeq source (FF/FFPE).
- **Strategies (Slide 40):** Microarrays are best.
- **No Impact:** Post-removal and imputation have no impact on global RNA_BATCH handling (Slide 41).
- **Trade-off (Slide 42):** Better methods disproportionately amplify individual PCs with low variance %.
- **Strategy Comparison (Slide 43):** RNASeq and Affymetrix perform worst due to FF/FFPE differences; Malignant only and No removal are best.
- **PC Variance (Slide 45):** Non-promising methods behave best on PC variance.

## SLIDES 47-50 — Local Neighborhood Metrics Deep Dive
**Title:** Local neighbourhood metrics
**Content:**
- MNN is a known good group.
- Slide 48 identifies 3 more potential good groups to be tested.

## SLIDES 51-54 — RNASeq only + Harmony
**Title:** RNASeq only and Harmony normalization with post-removal
**Content:**
- Another "best" among RNASeq only attempts.
- Still shows batch effect between FF and FFPE in DLBCL; similar to raw.

## SLIDES 55-58 — RNASeq only + MNN (Comparison)
**Title:** RNASeq only and MNN normalization - average attempt
**Content:**
- Batch effect present in 2/3 cases; DLBCL groups by cohorts.

## SLIDES 59-62 — Worst Examples (S0 + Softimpute)
**Title:** Worst group of S0
**Content:**
- Performance similar to having no normalization at all.

## SLIDES 63-66 — Angel Normalization
**Title:** Angel good examples
**Content:**
- PCA: No batch effect, but low PC percentages indicate hidden variance.
- UMAP/tSNE: Batch effect persists because of hidden variance.

## SLIDES 67-85 — Other Failed/Suboptimal Attempts
**Title:** Suboptimal joint normalization and microarray harmonizations
**Content:**
- **Scanorama for Microarrays (Slides 69-72):** Huge batch effect; cohorts scattered.
- **qsmooth for Microarrays (Slides 73-76):** Huge batch effect; cohorts smeared and scattered.
- **Rank Normalization (Slides 78-81):** Huge batch effect in all cohorts.
- **MNN for Affymetrix (Slides 82-85):** Best by metrics, but **awful visually** (huge batch effect).

## SLIDES 86-93 — Shambhala Harmonization
**Title:** Shambhala - could be promising
**Content:**
- **Principles:** Independent normalization, quantile + cubic scaling.
- Aims to improve both local and global metrics.
- Currently behaves slightly worse than MNN, but has room for improvement.

## SLIDE 95 — Conclusions for Visual Inspection
**Title:** Conclusions for visual inspection
**Content:**
- **Universal Challenge:** Almost impossible to remove PCA/tSNE batch effect between Microarrays and RNASeq.
- **RNASeq Best:** All cohorts harmonized well by SVA after KNN imputation.
- **kBET role:** Acceptance rate for `COHORT_LABEL` and `RNA_BATCH` seemingly determines UMAP/tSNE separability.
- **Shambhala:** Slightly worse than MNN, but improvement possible.

---

## NEXT STEPS AND ACTION POINTS

### Action Points for Shambhala (Slide 94)
1.  **Datasets:** Calibrate using datasets P/Q from Zenodo (https://zenodo.org/record/6415067).
2.  **B-Cell Context:** Treat normal B cells (bone marrow, blood, germinal center) separately as P0 or Q0.
3.  **Hyperparameters:** Do not adjust `k` (number of probe clusters) for now.
4.  **Experimentation:** Try different normalizing for different batches.
5.  **Execution:** Containerize Shambhala and run it alongside other approaches.
6.  **Code Improvement:** Download real libraries from Octave to replace AI-generated functions.

### Quick Fixes (Slide 96)
1.  **Filtering:** Filter harmonization attempts by the number and fraction of samples remaining after dropping NAs.
2.  **Visualization:** Add a "harshness level" palette (yellow, green, red) for normalization methods.
3.  **Variance Analysis:** Calculate % variance explained for each attempt in the top 10 PCs and compare PCR/R2.
4.  **Metric Visualization:** Visualize the best groups identified by iLICI and kBET (from Slide 48).

### Additional Analysis (Slide 96)
1.  **Strategy Update:** Add a strategy to remove minor batches (< 50 samples).
2.  **Batch Splitting:** (Optional) Split large batches.
3.  **Gene Retention:** Compare retained genes (all vs. FL-specific).
4.  **Method Selection:** Finalize the selection of the best approach.

### Documentation & Publication (Slide 96)
1.  **Manuscript:** Write the draft.
2.  **Decision Tree:** Add a decision tree with best practices for harmonization in the article.
    - *Key Insight:* No single best method for all batches.
    - *Constraint:* Do not mix FF and FFPE. Select either FF (RNASeq + Microarrays) or FFPE.
3.  **Post-Article:**
    - Add processed CEL files.
    - Add more NGS data from BG.
