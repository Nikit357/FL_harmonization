# Research Report: B-Cell Lymphomas Dissertation Project

## Overview

This is an active bioinformatics dissertation project focused on the transcriptomic characterization of germinal center (GC) B-cell lymphomas — primarily Diffuse Large B-Cell Lymphoma (DLBCL) and Follicular Lymphoma (FL). The overarching goal is to identify transcriptomic subtypes of FL using Self-Organizing Maps (SOM), characterize differentiation trajectories from normal B-cell ontogeny, and develop survival/therapy-response prediction tools based on SOM-derived signatures.

**Working directory:** `~/B_cell_lymphomas`  
**PI/researcher:** Daniil Nikitin (BostonGene)  
**Status as of April 2026:** Active research, target for publishable results is autumn 2026

---

## Research Hypotheses and Directions

Three candidate directions were evaluated (slides 8–10):

1. **Fundamental** — Mapping differentiation trajectories of GC lymphomas
2. **Applied** — Predicting survival and therapy response using SOM-derived signatures
3. **Methodological** — Developing ML-based subtyping pipelines grounded in SOM

The chosen focus is the **fundamental + applied** track: using SOM gene expression patterns to resolve FL transcriptomic subtypes, align them with normal GC B-cell states (Light Zone / Dark Zone axis, proliferating and differentiating cells), and link to clinical outcomes (OS, PFS, POD24).

Key biological hypothesis (from prior Shevkoplyas thesis): SOM expression maps form characteristic patterns for B-lymphoma subtypes, with continuous transitions between subtypes along a LZ (inflammation/anergy) ↔ DZ (proliferation) axis (Loeffler-Wirth et al. 2022). The thesis aims to establish whether these patterns can be used to define biologically meaningful and clinically relevant subtypes for FL.

---

## Dataset Assembly

### Scale
- **88 cohorts**, ~7,238 RNA expression samples (after assembly in `all_cohorts_assembly.ipynb`)
- **Post-filtering:** 5,444 samples and 3,520 genes after exclusion of bad batches/cohorts

### Sources
1. **Internal cohort database** — 46 cohorts downloaded with its Python client, expanding annotation. Major cohorts include:
   - DLBCL: CARTFARAMAND, GOYA, GSE117556, GSE10846, and 10+ others
   - FL: DAVE, GSE62241, HUET, PARSA, GUO, and 10+ others
   - Tracking: CRON3 (chronology)
2. **Sorted normal B cells** — 28 publicly available sorted B-cell datasets (GEO + ArrayExpress), stored in `/normal_B_cells/`. Includes GSE12195, GSE12453, GSE36907, GSE68878, GSE85289, E-MTAB-3974, and others. These provide reference distributions for all five normal B-cell types.
3. **Kassandra** — Deconvolution-derived B cells (RNA-seq only)
4. **Arsen GPL570 data** — Microarray data from internal `DLBCL_selected_samples.Rdata`, mapped from Affymetrix HG-U133-Plus-2 probe IDs to HGNC symbols via Ensembl BioMart API (`GPL570_mapping.py`). This cohort was **excluded** due to a persistent batch effect for one of the normalization approaches (see below).
5. **MDA FL Stratification** — Patient-level FL cohort with clinical annotations (MDA_Strati_FL_annotation.csv), including FLIPI, FLIPI-2, PRIMA-PI, treatment regimen, response, PFS, OS, POD24, transformation status.

### Platform Distribution (RNA_BATCH)
| Batch | N |
|---|---|
| RNASeq_FF_PolyA | 1,039 |
| GPL570_Unknown_Unknown | 1,030 |
| GPL570_FF_Unknown | 994 |
| RNASeq_FFPE_Exome_capture | 939 |
| GPL14951_FFPE_Unknown | 810 |
| GPL570_FFPE_Unknown | 800 |
| GPL96+97_FF_Unknown | 305 |
| GPL96_FF_Unknown | 133 |
| RNASeq_FF_rRNADepletion | 117 |
| … | … |

Platforms overall: Affymetrix Microarray (3,821), Illumina NGS (2,386), Illumina Microarray (940), Agilent Microarray (64).

### Gene Filtering
- Initial filtering: genes with >5,000 non-NA values across all samples
- After bad batch/cohort exclusion: 3,520 genes with no NA in any sample (full coverage)
- The reduction from ~5,000 to ~3,520 genes occurs when the three bad batches + SOM cohort are removed

### Combined Annotation Fields (comb_ann_unified.csv)
Key columns include: `Diagnosis_cell_type_unified`, `RNA_BATCH`, `PLATFORM_RNA`, `RNASEQ_SOURCE` (FF/FFPE), `OS`, `OS_FLAG`, `PFS`, `PFS_FLAG`, `RESPONSE`, `COHORT_LABEL`, `Major_group`, `TUMOR_NORMAL`, `AGE`, `GENDER`, plus clinical fields from MDA cohort (FLIPI, FLIPI-2, PRIMA-PI, STAGE, LDH, B2M, etc.)

---

## The Batch Effect Problem

### Magnitude
Before any normalization, **~95% of the variance in PCA is explained by batch effects** (RNA_BATCH column). This is the dominant signal — biological differences between DLBCL, FL, and normal B cells are completely masked.

### Nature of Batch Effects
- All batches except GPL570_FF_Unknown, GPL570_Unknown_Unknown, and GPL96_FF_Unknown cluster at a single point in PCA before normalization; after normalization they spread out
- RNASeq samples are much more compact (less within-platform variance)
- FFPE samples are compact because fewer platforms use FFPE
- FF vs FFPE separation is visible even after normalization
- Key problematic batches: GPL14951_FFPE_Unknown, GPL8432_FFPE_Unknown, GPL13938_FFPE_Unknown (Agilent/Illumina arrays, FFPE, unknown tissue)
- The "SOM" cohort (from Arsen's GPL570 data) batches strongly within the GPL570_Unknown_Unknown group

### Normal_B_cells vs Kassandra batch effect
After normalization, a residual batch effect remains between normal B-cell sources:
- **Normal_B_cells** = primarily microarray datasets (chips), contains all GC B-cell types
- **Kassandra** = RNA-seq deconvolution only
- Different cell types from the same batch cluster together more tightly than the same cell type across batches — a classic batch-dominates-biology signature (slide 90)
- The same pattern holds for tumor samples: different diagnoses from the same batch are more similar to each other than the same diagnosis from different batches (slide 91)

### UMAP Stability
UMAP is resistant to normalization — the number of clusters and their relative positions do not change before vs. after normalization. PCA is more sensitive to batch correction. This means UMAP topology reflects biology more robustly even in raw data.

---

## Normalization Methods Tested

### 1. qsmooth (Smooth Quantile Normalization)
- Applied per-group by RNA_BATCH
- **Result**: Reduced batch effect from 95% to 48% explained variance in PCA
- **Failure**: Could not normalize 12 out of 88 cohorts (they did not transition to a bimodal expression distribution)
- 8 cohorts improved; the rest were already fine before
- Bad batches had to be excluded prior to qsmooth: `['GPL8432_FFPE_Unknown', 'GPL6244_FFPE_Unknown', 'GPL17586_FF_Unknown', 'GPL20188_FF_Unknown', 'GPL23541_FF_Unknown', 'GPL887_FFPE_Unknown', 'GPL26356_FF_Unknown', 'GPL17047_FF_Unknown', 'GPL6244_FFPE_Unknown', 'GPL13938_FFPE_Unknown']`
- UMAP was unaffected by qsmooth (clusters preserved)

### 2. Quantile Normalization (QN, standard)
- Brings all cohorts to exactly the same distribution
- Allows inclusion of 12 cohorts that qsmooth failed on (since it doesn't depend on group structure)
- **Residual problem**: 5 batches remain as PCA outliers after QN alone
- Removing 3 bad batches + SOM cohort before QN causes GPL570_Unknown_Unknown to split into two groups → must also remove the outlier sub-group
- Final after QN cleanup: 5,444 samples, 3,520 genes
- "Overall internal variance within RNASeq is comparable to variance between cohorts — batch effect beyond this point is hard to remove further" (slide 48)

### 3. Feature-Specific Mean-Variance Normalization (FSMVN)
- Does **not** bring cohorts to similar or bimodal distributions
- Rejected

### 4. Harmony (Python implementation)
- Batch correction in PCA space
- **Result**: Batch effect **increased** — worse than no correction
- Rejected

### 5. limma `removeBatchEffect` (directly on expression)
- Applied on RNA_BATCH column
- **Result**: Did not improve batch separation sufficiently
- Rejected as standalone approach, but retained as a secondary step within the SOM pipeline (see SOM pipeline section)

### 6. ComBat (Empirical Bayes via neuroCombat / Bioconductor::sva)
- Tested on both RNA_BATCH and PLATFORM_RNA columns
- Distribution: peak always at zero, but tails can extend into negative and positive values (outliers clipped)
- Tested but not chosen as primary normalization

### 7. FSQN — Feature-Specific Quantile Normalization (**selected**)

#### Concept
FSQN (Franks et al., Biostatistics 2018; PMC11265146) transforms each feature's (gene's) distribution within each group to match a target reference distribution. This is "quantile normalization per gene per batch" — unlike standard QN which forces all genes to one global distribution, FSQN preserves relative gene-level differences across platforms.

#### Two implementations compared:
- **Python (custom)** — `fsqn_normalize()` in `SOM.py` and `all_cohorts_assembly.ipynb`:
  - Sorts each sample's values, maps target quantiles onto them
  - Target = global mean distribution (or specific group)
  - Effectively equivalent to standard quantile normalization per sample due to incorrect implementation
 
- **R package (original)** — called via `rpy2` in `SOM_FSQN_R.py` and `all_cohorts_assembly.ipynb`:
  - Uses the official `FSQN` R package
  - Normalized to **RNASeq_FF_PolyA** as the reference (highest-quality fresh-frozen polyA RNA-seq)
  - Reduces batch effect from **95% to 16%** in PCA
  - This last implementation by R package was selected for the downstream SOM step.

#### Why RNASeq_FF_PolyA as reference?
- Highest biological coverage and data quality
- Fresh-frozen samples preserve RNA integrity
- PolyA selection captures full transcriptome without rRNA contamination
- 1,039 samples — the largest single batch, providing a stable reference distribution

#### FSQN R result (slides 60–84):
- All cohorts converge to a similar bimodal expression distribution
- PCA by RNA_BATCH: microarray batches still mixing
- PCA by diagnosis: better mixing of DLBCL, FL, normal B cells
- UMAP by diagnosis: biologically coherent clusters visible
- tSNE by cell type: Normal_B_cells and Kassandra still separated (residual batch from platform)

- **Final dataset: 7174 samples, 3,447 genes**


**Winners: QC and FSQN from R, target = RNASeq_FF_PolyA**

---

## Self-Organizing Maps (SOM) Pipeline

### Biological Motivation
SOM (oposSOM, Loeffler-Wirth et al.) maps all gene expression values onto a 2D grid (default 50×50 = 2,500 nodes). Each node (metagene) represents the centroid expression of ~genes with maximal within-cohort correlation to each other. This provides:
- A compressed, interpretable representation of transcriptional programs
- "Portrait" visualizations: heatmaps where color intensity (blue→green→yellow→red) shows the activity of each metagene in each sample
- Biologically interpretable spots: groups of active metagenes correspond to co-regulated gene programs
- Good survival prediction (Loeffler-Wirth et al. 2019)
- Visualization of continuous transitions between lymphoma subtypes (Loeffler-Wirth et al. 2022)

### Two SOM Scripts

#### SOM.py — FSQN Python → limma → oposSOM
1. Load `comb_exp.tsv` and `comb_ann.tsv` from `$FL_DATA_ROOT/`
2. Filter bad batches: GPL14951_FFPE_Unknown, GPL8432_FFPE_Unknown, GPL13938_FFPE_Unknown
3. Filter rare diagnoses: Extranodal MZL, Double-Hit Lymphoma, MCL, CLL, Other
4. Merge the sorted B-cell references and Kassandra into a single "Normal_B_cells" group
5. Drop NaN-containing genes and duplicated sample indices
6. Apply `fsqn_normalize()` (Python implementation, target = global mean)
7. Apply `batch_correct_for_som()` using `limma::removeBatchEffect` on RNA_BATCH via rpy2
8. Run `run_opossom_analysis()` grouped by `Major_group`
9. Extract metagene matrix, gene-to-metagene BMU map, GSZ scores
10. Cluster metagenes: `AgglomerativeClustering(n_clusters=15, metric='euclidean', linkage='ward')`
11. Retrieve HALLMARK + KEGG gene set enrichment scores
12. Output: `metagenes_matrix.csv`, `gene_to_metagene_map.csv`, `pathway_scores.csv`

#### SOM_FSQN_R.py — FSQN R → oposSOM
1. Load pre-normalized data: `fsqn_normalized_exp_R.tsv` and `ann_normalized_fsqn_R.tsv`
2. Skip Python FSQN (data already normalized by R FSQN)
3. Apply `batch_correct_for_som()` with limma (same as above)
4. Run `run_opossom_analysis()` grouped by `Diagnosis_cell_type_unified`
5. Same downstream steps as SOM.py

**Key difference**: SOM_FSQN_R.py uses pre-computed R-package FSQN data (the better normalization) and groups by the more granular `Diagnosis_cell_type_unified` rather than `Major_group`.

### oposSOM Configuration
```python
pref = {
    'dataset.name': 'MyCohort',
    'dim.1stLvlSom': 'automatic',       # auto-size the SOM grid
    'standard.spot.modules': 'kmeans',   # k-means for spot detection
    'adjust.expression.values': False,   # already batch-corrected
    'feature.centralization': True,
    'sample.quantile.normalization': True
}
```

### Batch Effect in SOM Metagene Space

The SOM pipeline was run under two normalization conditions and the residual batch effect in the metagene space was evaluated:

#### After QN → SOM (slides 96–117):
- PCA in metagenes by RNA_BATCH: batch mixing is better than in raw expression space
- UMAP in metagenes by RNA_BATCH: batches split into sub-clusters AND merge between different batches — partial success
- tSNE in metagenes by RNA_BATCH: better mixing
- PCA by diagnosis: ABC/GC separation appears, Kassandra and specific normal B-cell subtypes are identifiable
- UMAP by diagnosis: coherent structure visible
- **However**: QN → SOM does **not** remove batch effect completely (slide 115: "QN → SOM не удаляют батч эффект")
- Normal B-cell batch effect persists: different cells from same platform cluster together more than same cell type across platforms (slide 116)
- Same for tumors: different diagnoses from same batch > same diagnosis across batches (slide 117)

#### After FSQN R → SOM (slides 65–84):
- PCA by diagnosis: **best mixing achieved** ("Наилучшее перемешивание!" — slide 66)
- UMAP by diagnosis: biologically coherent separation
- tSNE by diagnosis: coherent
- PCA/UMAP/tSNE by RNA_BATCH: residual batch effect visible but reduced
- PCA by FF/FFPE: mixing present
- PCA by tumor/normal: tumor and normal are broadly separable
- Normal_B_cells vs Kassandra still show separation (slide 89)
- Batch effect test (slide 90–91): **FAILED** — same-platform cells still cluster more than same-type cells across platforms. Same conclusion for lymphomas.

### Critical Conclusion on SOM Batch Effect
**Slides 90–92 contain the key conclusion:**
> "Different cell types from the same batch are more similar to each other than the same cell type in different batches"

This holds for both normal B cells and tumor samples. The implication is severe: **the SOM batch effect test was failed**, and the recommendation on slide 92 is:
> **"ОСТАВИТЬ ТОЛЬКО РНК СЕК!!!"** (USE ONLY RNA-SEQ!)

This is a fundamental finding: no normalization fully harmonizes microarray and RNA-seq data for SOM-based analysis. The recommended path forward is to restrict the dataset to RNA-seq only, which eliminates the major platform-driven batch effect.

### SOM Portrait Visualization
The oposSOM portraits visualize each sample's metagene activity as a heatmap (50×50 grid, rainbow colormap blue→red):
- DLBCL samples: activation patterns differ between GCB-DLBCL and ABC-DLBCL
- ABC vs GCB DLBCL: distinct SOM pattern separation (slide 87)
- FL samples: own pattern (slides 86)
- Normal B cells (Kassandra, Normal_B_cells): distinct from all lymphomas (slide 88)
- Normal_B_cells vs Kassandra: their patterns differ — batch effect manifests in portrait differences (slide 89)

### SOM Output Files
Two sets of oposSOM results were generated and stored:
- `MyCohort - Results/` — from initial run (quantile normalization, fewer samples)
- `MyCohort+ - Results FSQN R/` — from FSQN R normalization run; includes:
  - `Data Distribution.pdf`, `t-SNE.pdf`, `Entropy Profiles.pdf`, `Supporting Maps.pdf`, `Topology Profiles.pdf`
- `MyCohort+ - Results Quantile norm/` — from quantile normalization run; includes:
  - All of the above plus `Correlation Maps.pdf`, `Correlation Network.pdf`, `Hierarchical Clustering.pdf`, `Sample SOM.pdf`, `Component Analysis.pdf`, `Neighbor Joining.pdf`, `Correlation Backbone.pdf`, `Correlation Spanning Tree.pdf`
  - `CSV Sheets/Gene localization.csv` (gene-to-SOM-node mapping)
  - `CSV Sheets/Sample GSZ scores.csv` (gene set Z-scores per sample)
  - `Summary Sheets - Groups/PAT-groups assignment.pdf`
  - `Summary Sheets - Modules/Overexpression Spots/Report.pdf`

---

## B-Cell Normal Reference: Internal Classifier

### Purpose
The internal B-cell classifier provides scores for five normal B-cell differentiation states for each sample. These scores are used to:
- Map lymphoma samples to their cell-of-origin
- Reconstruct differentiation trajectories
- Provide biologically grounded features for clustering

### Five B-Cell Types
1. **Naive** (CD45RA+, IgD+) — resting, pre-activation
2. **Centroblast** (GC dark zone, proliferating)
3. **Centrocyte** (GC light zone, selection)
4. **Memory** (CD27+, post-GC)
5. **Plasma** (antibody-secreting cells)

### Training Data
- 28 sorted B-cell public datasets from GEO/ArrayExpress (28+ TSV files in `/normal_B_cells/`)
- Multiple tissue sources: LN, Tonsil, Peripheral Blood, Spleen, BM, Intestine
- Multiple platforms: GPL570, GPL96, RNASeq, etc.

### Workflow (bcell_typing_2022_clean.ipynb, bcell_typing_one_vs_all_clean.ipynb)
1. Start from ~350 public BAGS genes per cell type
2. Apply **iterative feature selection with holdout cohorts**:
   - 8 GSE datasets held out for validation
   - SHAP feature importance + expression rank filtering
   - Genes retained if stable across ≥(n_holdouts − threshold) iterations
   - Final: ~30–50 genes per cell type
3. Evaluate feature set size by clustering metrics: AIC, Silhouette, Calinski-Harabasz, Davies-Bouldin
4. Train `LogisticRegression(penalty='l2')` with `GridSearchCV(C=[10^-10, ..., 10^-2])`
5. Input: **rank-transformed** gene expression (platform-independent)
6. Evaluate on 8 holdout cohorts: ROC-AUC, F1, confusion matrix
7. Save: pickle files with model, feature genes, train/test data

### Application
```python
scores = calc_bcell_type_one_vs_all(expression_matrix)
# Returns: DataFrame [samples × 5 cell types] with probability scores
# Optionally: median-scaled scores per sample
```
The rank-transformation makes the classifier **platform-independent** — works on both microarray and RNA-seq data without additional normalization.

---

## Signature Scoring and Pathway Analysis

### DLBCL Signatures (ssGSEA)
Loaded from `dlbcl_signatures.gmt`. 27 signatures including:
`T_cells, T_cell_traffic, B_cells, Th2_signature, Matrix_remodeling, Follicular_dendritic_cells, Protumor_cytokines, Lymphatic_endothelium, Matrix, Fibroblastic_reticular_cells, Proliferation_rate, Granulocyte_traffic, Treg, Follicular_B_helper_T_cells, Macrophages, Th1_signature, NK_cells, B_cells_traffic, CAF, M1_signature, MHCII, Eosinophil_signature, Antitumor_cytokines, Checkpoint_inhibition, MHCI, Neutrophil_signature, Angiogenesis`

Applied via ssGSEA; scores are median-scaled by cohort to remove inter-cohort baseline differences. Used for PCA visualization and clinical outcome correlation.

### PROGENy Pathway Scoring
Oncogenic pathway activity scores computed for all samples; included in the integrated analysis.

### Gene Set Z-scores (oposSOM GSZ)
The oposSOM pipeline internally computes GSZ (Gene Set Z-score) for HALLMARK and KEGG genesets across all SOM nodes. Extracted via `retrieve_and_score_genesets(env, keywords=['HALLMARK', 'KEGG'])`.

---

## Literature Overview (from Slides)

### Key References
- **Loeffler-Wirth et al. 2019** — SOM expression maps form characteristic patterns for B-lymphoma subtypes and predict OS well
- **Loeffler-Wirth et al. 2022** — SOM shows continuous transitions between lymphoma subtypes along LZ (inflammation) ↔ DZ (proliferation) axis
- **Nilushi et al. 2015** — B-cell lymphoma biology context
- **Franks et al. 2018** (FSQN) — Feature-specific quantile normalization for cross-platform integration (https://academic.oup.com/biostatistics/article/19/2/185/3949169)
- **Qsmooth reference** — https://pmc.ncbi.nlm.nih.gov/articles/PMC11265146/
- **FL transcriptomic subtypes (2025)** — C1/C2/C3 molecular subtypes (https://www.nature.com/articles/s41375-025-02603-9)
- **FL PFS prediction (2019)** — ~20 gene signature predicting PFS; validated on independent dataset (https://pubmed.ncbi.nlm.nih.gov/29475724/)
- **SOM projection method** — Projecting new cohorts onto reference SOM space (https://www.mdpi.com/2673-7426/2/1/4)
- **Internal B-cell typing / Mark Meyerson** — DZ-like FL subtype has worst prognosis; GC and Memory-like FL subtypes have different outcomes

### FL Transcriptomic Subtypes (Literature Summary, slides 135–144)
- Two major subtypes: **GC-like** and **Memory-like (MEM-like)**
- Different top marker genes identified for each subtype
- Subtype prediction by mutations achieves ~80% accuracy
- An IHC test system based on 4 markers was developed from the classifier (slide 140)
- Forest plots show survival differences between subtypes (slide 141)
- Cartographic mapping of signatures onto single-cell B-cell and FL datasets validates biological relevance (slide 137)

---

## Key Technical Tools and Infrastructure

### Data Storage
- **Cohort database** — an internal cohort database (not public); see `DATA_AVAILABILITY.md`
- **S3** — AWS S3 storage, accessed via `boto3`; large files streamed from `s3://` paths
- **Zarr** — `local_copy.zarr` stores normalized expression + annotation in hierarchical chunked format
- **AnnData** — `.h5ad` format for compatibility with Scanpy/scVI; created in `anndata_creation_demo.ipynb`

### Software Stack
- **Python**: pandas, numpy, scipy, scikit-learn, matplotlib, seaborn, lightgbm, rpy2, boto3, supervenn, SHAP
- **R** (via rpy2): oposSOM, limma, FSQN, sva/neuroCombat
- **Internal analysis library** (not public): supplied annotation, clustering, GSEA, pathway-scoring, plotting, ssGSEA, survival and palette helpers. The public notebooks redefine every helper they used on top of public packages.
- **Version control**: git with `nbstripout` filter to strip notebook outputs before commits

### GPL570 Probe Mapping (`GPL570_mapping.py`)
Connects to Ensembl BioMart to map Affymetrix HG-U133-Plus-2 probe IDs → HGNC symbols + Entrez IDs. Batches 100 probes per query. Output: `GPL570_mapping_probes.csv`.

### Cell Line Resources (`/cell_lines/`)
- **CCLE_expression.csv** (409 MB) — Cancer Cell Line Encyclopedia expression
- **GDSC1.tsv / GDSC2.tsv** — Genomics of Drug Sensitivity in Cancer screening data
- **LL-100_ann.tsv** — Lymphoma cell line annotations
- **LL_100_B_expr.tsv** — Lymphoma cell line expression (B-cell specific)

---

## Project People (Slide 145)

- **Masha Savchenko** — Advice on harmonization choice, training/testing strategy, interpretation
- **Tolya Bobe** — Generating embeddings (AnnData passed to him for downstream embedding analysis)
- **Helpdesk support**
- **Mark Meyerson** — Occasional scientific advice
- **Arsen** — Provided GPL570 DLBCL dataset (subsequently excluded due to batch effect)
- **Alexei Shevkoplyas** — Prior thesis establishing the SOM-based clustering framework for GC lymphomas

---

## Current Status and Next Steps (April 2026)

### What Was Accomplished
1. Assembly of 88 cohorts (~7,200 samples) from the internal cohort database + public sources
2. Systematic evaluation of 6 normalization approaches
3. Selection of **FSQN (R implementation, target = RNASeq_FF_PolyA)** as the best harmonization
4. Identification and exclusion of 3 bad batches + 1 bad cohort (SOM/Arsen)
5. oposSOM analysis run under both QN and FSQN conditions; SOM portraits generated
6. Critical finding: **batch effect test failed** — batch effect persists in metagene space for mixed microarray + RNA-seq data
7. AnnData object finalized and passed to Tolya for embedding generation
8. Literature review of FL transcriptomic subtypes (C1/C2/C3 subtypes, 2025 paper)

### Open Issues
- Residual batch effect in SOM metagenes (microarray vs RNA-seq)
- Normal_B_cells vs Kassandra still separate (platform-level batch)
- Normal B-cell types: GC B cells only in Normal_B_cells, not in Kassandra

### April 2026 Analysis Plan (slide 95)
1. **Test best harmonization approaches specifically for SOM** (not just for PCA/UMAP)
2. Build PCA/UMAP in best SOM metagenes, evaluate batch effect quantitatively
3. **Project other cohorts onto reference SOM** (per the MDPI 2022 method): use RNA-seq B cells, or FL, or best DLBCL batch as reference → project all others
4. Analyze heatmap intensity per metagene cluster
5. Identify signatures/pathways enriched in each SOM cluster
6. Reproduce internal B-cell typing signatures on the assembled dataset

### Immediate Recommendation (from slide 92)
**Restrict analysis to RNA-seq only** to eliminate the fundamental microarray/RNA-seq batch incompatibility. This reduces the dataset but allows cleaner SOM analysis without residual platform bias.

### Future Ideas (slides 16, 93)
- Use GeneCorpus-30M single-cell datasets for pre-training (https://huggingface.co/datasets/ctheodoris/Genecorpus-30M)
- Median-scale within dataset first, then rank-transform
- Map C1/C2/C3 FL subtypes from 2025 paper onto the assembled dataset
- Large comparative study of all available signatures on the big combined dataset
- Compare SOM performance vs PCA64/25 vs internal B-cell typing signatures vs embeddings for OS/PFS prediction

---

## Summary of Key Findings

| Finding | Detail |
|---|---|
| Batch effect magnitude | 95% of PCA variance before normalization |
| Best normalization | FSQN (R package, target = RNASeq_FF_PolyA), reduces to 16% |
| Failed normalizations | FSMVN, Harmony (Python), limma alone |
| Partial normalizations | qsmooth (→48%, fails 12/88 cohorts), ComBat, QN (→ 5 outlier batches remain) |
| Excluded batches | GPL14951_FFPE_Unknown, GPL8432_FFPE_Unknown, GPL13938_FFPE_Unknown |
| Excluded cohort | SOM (Arsen's GPL570 data) |
| Final dataset | 5,444 samples, 3,520 genes |
| SOM best result | FSQN R → SOM: "best mixing" in PCA by diagnosis |
| SOM batch test | FAILED — platform dominates cell type in both normals and tumors |
| Key recommendation | Use only RNA-seq samples for SOM analysis |
| UMAP stability | Resistant to normalization; topology reflects biology regardless of batch correction |
| B-cell types | 5 types classified (Naive, Centroblast, Centrocyte, Memory, Plasma) via rank-based logistic regression |
| Target publication | Autumn 2026 |
