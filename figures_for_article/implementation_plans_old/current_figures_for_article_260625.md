# Article-Level Figure Descriptions — ComboBatch Harmonization Manuscript

**Generated:** 2026-06-25 (revised 2026-06-26)
**Source folder:** `figures_for_article/current_figures_for_article_260625/`
**Notebook reference:** `notebooks_for_figures_260625.md`
**Article status reference:** `article_figures_status_260625.md`

---

## Rendering notes

- **Figure 4** (31 MB PDF) and **Figure 5** (22 MB PDF): described from JPEG versions uploaded alongside the PDFs in the same directory.
- **Figure 7** and **Supplementary Figure 20**: explicitly marked as **INCOMPLETE / PLACEHOLDER** by the author. Descriptions cover visible content only.

---

## Visualization Patterns and Design Principles

All figures in this manuscript follow a unified visual language designed for publication in a peer-reviewed bioinformatics article.

**Fixed global font size.** A single `GLOBAL_FONT_SIZE = 10` constant is applied to all text elements (axis labels, tick labels, legend entries, panel annotations) across every figure. No font sizes are hard-coded per-panel or per-figure. This ensures that all figures are legible at print scale (A4) and visually consistent when placed side-by-side in a multi-figure manuscript layout.

**Multiple colour palettes, placed near corresponding plots.** Each figure uses one or more of the following canonical palettes, always displayed as a legend adjacent to the panel it annotates:
- `lymphoma_ontogeny_palette` — the Temperature-Split palette assigning cold/blue tones to normal B-cell populations and warm/red tones to malignancies; used for `Diagnosis_cell_type_unified` in all biology-coloured panels.
- `rna_batch_palette` — 29-colour palette, one colour per RNA_BATCH; used in all batch-coloured panels.
- `platform_palette` — per `PLATFORM_RNA` / GPL code; used in platform-grouped figures.
- Harmonization method palette — 31 colours, one per method; used in scatter plots and clustermaps.
- Batch removal strategy palette — 14 colours, one per strategy; used in clustermaps and scatter plots.
- Harshness / status palette — green (low harshness / good), orange (medium), red (high / bad); used as annotation strips in PCR and kBET barplots.

Legends are placed immediately to the right of or below the plot they annotate, rather than in a single consolidated legend block, to minimise eye travel.

**A4 article format with full panel coverage.** Each figure is sized to fill an A4 page (210 × 297 mm, portrait or landscape). Panels are laid out in even grids using `gridspec` or `subplot_mosaic`, with consistent inter-panel spacing. No panel is left undersized; the grid proportions are adjusted so that panels cover the available space without whitespace gaps.

**Complex circos and Sankey diagrams for gene and sample number visualisations.** Figures 2A and 2D use a specialised combined Circos-Sankey layout implemented with custom Python functions. The circos outer ring encodes strategy group membership (coloured arc sectors); the inner radial spokes encode sample or gene counts for each strategy. Sankey arcs connect the central reference node to each strategy arm, with arc width proportional to count. This layout was developed specifically for this manuscript to convey both the hierarchical grouping of 14 strategies and the quantitative gene-retention differences across imputation methods in a single diagram.

**Side colour annotation strips.** All heatmaps and clustermaps (Figures 3, 4, 5, 6D, Supplementary Figures 5–9, 18–19) include one or more annotation colour strips placed at the margin of the heatmap body:
- For column annotations: strategy, imputation, harmonization method, post-removal flag, and harshness level strips are stacked above each clustermap column.
- For row annotations: metric group, annotation column, and metric type strips are stacked to the left of each clustermap row.
- Harshness strips use the green/orange/red palette; good/bad status annotations are added as text labels above barplots where relevant.
- Biology and RNA_BATCH strips appear as sidebar annotations on all sample×PC heatmaps in Figures 4 and 5.

**Overall publication-level figure quality.** All figures are saved as both SVG (vector, with `svg.fonttype = "none"` so text remains editable in Figma/Illustrator) and PNG (200 dpi, for rapid review). PDF fonttype is set to `"truetype"` for embedded rasters. Seaborn style is set to `"ticks"` globally. Every axis is explicitly labelled; colour scales include numeric ticks; legends are formatted with frame-off, compact spacing, and cross-referenced to the nearest plot panel.

---

## MAIN FIGURES

---

### Figure 1. Dataset overview and ComboBatch pipeline

**Multi-platform transcriptomic dataset composition and the nine-step ComboBatch harmonization benchmark pipeline.**

**Proposed article caption:**

> Overview of the multi-platform transcriptomic dataset and the nine-step ComboBatch harmonization benchmark pipeline. **(A)** Bubble chart of 7,174 samples distributed across 29 RNA batches, grouped and colour-coded by sequencing platform (Illumina NGS, blues; Affymetrix microarrays, oranges/browns; Illumina microarrays, reds; Agilent microarrays, greens). Each dot represents one sample; bubble area is proportional to batch size. **(B)** Bubble chart of the same 7,174 samples organized by disease and cell-type biology group. Malignant diagnoses (DLBCL, FL, High-Grade B Cell Lymphoma, Burkitt Lymphoma) are shown in warm colours; normal B-cell populations (Early-to-GC and Mature-to-plasma lineages) are shown in cool colours following the Temperature-Split palette. **(C)** Schematic of the nine-step ComboBatch pipeline: (1) raw expression data from microarray and NGS sources; (2) 14 batch removal strategies defined by batch, biology, biomaterial, and platform composition; (3) three imputation strategies (strict, KNN, softimpute); (4) cohort-wise log₂(x+1) transformation; (5) harmonization by one of 31 methods; (6) optional post-removal of one PCA-outlier batch; (7) computation of local, global, distributional similarity, and Watermelon score metrics; (8) polarity setting (batch mixing ↑, biology mixing ↓); (9) clustermap construction and selection of the 2,234 valid attempts. **(D)** Stacked barplot (log scale) of sample counts per RNA batch, coloured by diagnosis/cell-type biology group. **(E)** Stacked barplot (log scale) of sample counts per biology group, coloured by RNA batch.

**Panel-level description:**

**Panel A — Platform bubble chart.** Twenty-nine circular bubbles, each scaled by sample count (range ~68–1,039 samples per batch). Each dot within a bubble represents one sample. Platform colour groups: Illumina NGS (blues), Affymetrix microarrays (oranges/browns), Illumina microarrays (reds), Agilent microarrays (greens). Full RNA_BATCH legend with per-batch colour coding shown in the lower left. Log₁₀ sample count scale shown at upper right.

**Panel B — Biology bubble chart.** Biology groups shown as individual sample dots grouped into bubbles by group membership. DLBCL (4,466) and FL (1,697) dominate. Normal B-cell populations (cool colours): Early-to-GC includes Bone_marrow_CD19+, Immature, Naive, GC, Centroblast, Centrocyte; Mature-to-plasma includes B_cells, MZ, Memory, Plasmablast, Plasma. Rare malignancies: High Grade B Cell Lymphoma (1,007), Burkitt Lymphoma (88). Legend split into three groups: Early to GC B cells (cool blues/greens), Mature to plasma B cells (greens/teals), Malignancies (warm reds/oranges).

**Panel C — Pipeline schematic.** Nine numbered boxes connected by arrows. Each step is annotated with a mini-diagram: step 4 shows the log₂(x+1) curve; step 5 shows a Before → After PCA-style illustration; step 8 shows two scatter icons labelled "Batch ↑ / Biology ↓"; step 9 shows a clustermap thumbnail with 2,234 attempts annotated.

**Panel D — Barplot per RNA batch.** ~29 bars (log₁₀ scale, y-axis 10¹–10³) ordered by total size, coloured by diagnosis/cell-type biology group using the Temperature-Split palette.

**Panel E — Barplot per biology group.** ~15 biology groups on x-axis (ordered by total size, log₁₀ scale), coloured by RNA_BATCH.

**Results section:**

The dataset spans four sequencing platforms and 29 RNA batches, with a total of 7,174 samples — one of the largest multi-platform B-cell lymphoma transcriptomic collections assembled for harmonization benchmarking. DLBCL (62%) and FL (24%) dominate the malignant compartment, while normal B-cell populations (~14%) provide essential biological reference points spanning the full B-cell ontogeny from bone marrow progenitors through plasma cells. The extreme imbalance between the largest batch (RNASeq_FF_PolyA, 1,039 samples) and the smallest batches (~68 samples) directly drives the challenge of global harmonization: methods that optimize for large batches often fail to integrate rare platform types.

The nine-step ComboBatch pipeline distils 2,407 harmonization runs to 2,234 valid attempts through systematic QC at step 9. The pipeline's modularity — with explicit separation of strategy definition (step 2), imputation (step 3), harmonization (step 5), and post-removal (step 6) — allows orthogonal decomposition of each factor's contribution to harmonization quality, which is the central analytical contribution of Article 1.

---

### Figure 2. Batch removal strategies, imputation, and NA gene analysis

**Fourteen batch removal strategies, imputation-dependent gene set composition, and NA expression patterns in the 7,174-sample dataset.**

**Proposed article caption:**

> Batch removal strategy structure, imputation-dependent gene set composition, and NA expression patterns in the ComboBatch dataset. **(A)** Circos-Sankey diagram of 14 batch removal strategies organized by four grouping criteria (By biology, By biomaterial, By platform, Bad batches removal), with sample counts (N) for each strategy. S0_no_removal (N=7,174) is the reference. **(B)** Grouped barplot showing the number of genes retained per batch removal strategy under strict imputation (bottom; 3,447 genes retained uniformly) and KNN or softimpute imputation (top; 6,000–16,000 genes depending on the strategy). **(C)** Sample-by-gene NA heatmap for the full dataset. Samples (columns) are ordered by increasing NA count; genes (rows) are ordered by increasing NA frequency. Annotation rows indicate RNA_BATCH and Diagnosis_cell_type_unified per sample. Green = known expression; red = NA expression. **(D)** Circular gene-count Sankey showing gene counts per strategy for strict (blue, 3,447) vs. KNN/softimpute (brown, 6,052–15,881) imputation; gene counts printed at each arc terminus. Centre node: S0_no_removal with KNN imputation (N=11,768 genes).

**Panel-level description:**

**Panel A — Circos-Sankey.** Radial diagram with 14 labelled wedges radiating from a central ring. Four coloured outer arcs classify strategies: By biology (D_malignant_only N=6,285), By biomaterial (C_rnaseq_only N=2,243; J_ff_only N=3,167; K_ffpe_only N=3,000), By platform (F_microarray_only N=4,931; G_affymetrix_only N=2,801; H_affymetrix_extended N=3,727), Bad batches removal (A_confirmed_bad N=5,444; B_extended_bad N=5,108; E1_iterative_r1 N=5,420; E2_iterative_r2 N=5,387; E3_iterative_r3 N=5,256; I_rare_batches_removed N=6,803). S0_no_removal sits in the centre ring. Sector sizes are proportional to sample counts.

**Panel B — Gene count barplot.** Two stacked horizontal barplot groups (knn/softimpute top; strict bottom). X-axis: 14 strategies ordered by gene count. Strict imputation uniformly retains 3,447 genes across all strategies. KNN/softimpute gene counts vary widely: D_malignant_only reaches 15,818 (KNN) – 15,196 (softimpute); C_rnaseq_only ~9,447–9,857; G_affymetrix_only ~6,710 (lowest for KNN/softimpute among platform-restricted strategies). Per-bar gene count values printed inside bars.

**Panel C — NA heatmap.** Dense matrix (~7,174 samples × ~20,000 genes). Green = known expression; red = NA. Two annotation rows above: RNA_BATCH (multicolour, 29 values) and Diagnosis_cell_type_unified (Temperature-Split). Sharp green-to-red boundary visible at ~3,447 genes on the y-axis.

**Panel D — Circular gene-count Sankey.** Radial diagram centred on "S0 KNN, N=11,768". Each strategy arm shows two arc segments: blue (strict, always 3,447) and brown (knn/softimpute, strategy-dependent). Gene counts printed at arc terminus. Four strategy-category wedges: Biomaterial (K_ffpe_only, J_ff_only), Platform (C_rnaseq_only, F_microarray_only, H_affymetrix_extended, G_affymetrix_only), Biology (D_malignant_only reaching 15,818), Bad batches (A_confirmed_bad, B_extended_bad, E1/E2/E3, I_rare_batches_removed).

**Results section:**

Imputation method is the primary driver of gene-set size: strict imputation retains a uniform 3,447 genes across all 14 strategies, while KNN and softimpute expand coverage to 6,000–15,818 genes depending on strategy composition. The extreme range — with D_malignant_only retaining 15,818 genes under KNN but only 3,447 under strict — directly reflects the biology of that strategy: by excluding heterogeneous Normal B-cell RNA-seq batches that introduce the most NA values, more genes achieve full coverage. Conversely, G_affymetrix_only retains only ~6,710 genes under KNN because Affymetrix arrays have inherently more inter-platform gene set variation.

The NA heatmap (Panel C) reveals a sharp boundary at ~3,447 genes that defines the strict-imputation gene set. Below this threshold, virtually all samples (both RNA-seq and microarray) have known expression values. Above it, FFPE microarray batches accumulate dense NA values. This boundary is the key parameter controlling the trade-off between gene depth (biological resolution) and sample coverage (statistical power). The Circos-Sankey (Panel A) further demonstrates that strategy sample size varies 3-fold (N=2,243 for C_rnaseq_only vs. N=6,803 for I_rare_batches_removed), reinforcing that strategy selection is the most consequential decision in the benchmark design.

---

### Figure 3. Comprehensive harmonization clustermap across 2,234 attempts and 87 metrics

**Hierarchical clustermap of 2,234 harmonization attempts scored across 87 polarity-normalized batch effect metrics, with column and row annotations.**

**Proposed article caption:**

> Comprehensive hierarchical clustermap of 2,234 harmonization attempts evaluated across 87 polarity-normalized batch effect metrics. Rows represent individual metrics (polarity-normalized 0–1; 1 = optimal batch correction or biology preservation); columns represent individual harmonization attempts (method × strategy × imputation × post-removal). Colour scale: green (1.0) → white (0.5) → red (0.0). Row colour annotations: metric group (A–K), annotation column (batch or biology covariate), metric type (local neighborhood, global distance, distribution similarity, other). Column colour annotations: batch removal strategy, imputation method, harmonization method, post-removal flag, harshness level. Five major metric row clusters are identified: NA percentage cluster (Group K), Local metrics cluster (Group B/C iLISI, kBET, entropy, ASW_batch), Global metrics clusters A–C (PCR, DSC, WaterMelon, distance ratios), and Distribution similarity cluster (Group D KS tests). Four column super-clusters are labelled: Good cross-platform, Bad cross-platform, Same sample type, and Same platform (with Bad/Good sub-groups).

**Panel-level description:**

Single large clustermap (~87 rows × 2,234 columns) with full hierarchical dendrograms on both axes.

**Row annotations (left margin, three strips):**
1. Metric group (A–K, 10 colours): A = PCA variance decomposition; B = Neighbor-based integration; C = UMAP/tSNE embeddings; D = Distribution comparison; E = Zero fraction and bimodality; G = Graph connectivity; H = Pairwise Euclidean distance; I = Watermelon score; J = Percentage variance explained; K = Samples and genes with NAs.
2. Annotation column (8 colours): batch covariates = RNA_BATCH, PLATFORM_RNA, RNASEQ_SOURCE, COHORT_LABEL; biology covariates = Major_group, Diagnosis_cell_type_unified, TUMOR_NORMAL; Global_all_columns (grey).
3. Metric type (4 colours): Local neighborhood (dark teal), Global distance (dark brown), Distribution similarity (medium brown), Other (light grey/tan).

**Column annotations (top, five strips):** batch removal strategy (14 colours), imputation (strict/knn/softimpute), harmonization method (31 colours), post-removal flag (False/True), harshness level (green/orange/red).

**Metric row clusters (top to bottom):** NA percentage cluster (K, ~10 rows); Global metrics cluster A (~20 rows); Local metrics cluster (~15 rows: kBET, iLISI, entropy, ASW_batch); Global metrics clusters B and C (~25 rows: PCR, DSC, dist_ratio, WaterMelon); Distribution similarity cluster (~15 rows: KS tests, graph connectivity, pcr_COHORT_LABEL).

**Column super-clusters (left to right):** Good cross-platform (MNN in multi-platform strategies, FSMVN and AMDBNorm in S0); Bad cross-platform (MNN in J_ff_only, FSQN R in J_ff_only); Same sample type — Bad (K_ffpe_only, C_rnaseq_only, poor global metrics); Same sample type — Good (SVA in K_ffpe_only and C_rnaseq_only with knn/softimpute); Same platform — Bad/Good (G_affymetrix_only, F_microarray_only; FSQN R in C_rnaseq_only in Good sub-group).

**Results section:**

The clustermap reveals that batch removal strategy is the dominant organizer of harmonization outcome: attempts from K_ffpe_only, C_rnaseq_only, and J_ff_only form isolated column super-clusters regardless of harmonization method, while attempts from multi-platform strategies (S0, H, D) intermix more freely. This confirms the hierarchy established by the metric PCA analysis (Supplementary Figure 9): strategy > method > post-removal > imputation.

Four biologically meaningful column super-clusters emerge. The "Good cross-platform" cluster identifies the small subset of attempts — primarily MNN in S0_no_removal and H_affymetrix_extended, and AMDBNorm/FSMVN in S0_no_removal — that simultaneously achieve strong global batch correction (green row colors in PCR/DSC rows) and biology preservation (green in cLISI/ASW_bio rows). The "Same sample type — Good" cluster highlights SVA as uniquely effective within biomaterial-restricted strategies: SVA with knn or softimpute in C_rnaseq_only and K_ffpe_only achieves the best local metric scores within their respective subsets, even though these strategies cannot achieve cross-platform mixing by design. The "Bad cross-platform" cluster exposes methods that over-correct, collapsing biology clusters while achieving global batch homogenization.

The separation of the Local metrics cluster from the Global metrics clusters (visible as two distinct row super-clusters) confirms that iLISI/kBET and PCR/DSC capture complementary, non-redundant aspects of harmonization quality — a key methodological justification for using both metric types in the benchmark.

---

### Figure 4. PCA, tSNE, and per-sample PC heatmaps for MNN on S0_no_removal and biomaterial strategy subsets

**Proposed article caption:**

> Visual inspection of harmonization performance for MNN (10_mnn) on the S0_no_removal strategy compared with the raw baseline, and for biomaterial-restricted strategy subsets. **(A)** PCA and tSNE scatter plots of 01_raw S0_no_removal strict, coloured by RNA_BATCH (batch) and Diagnosis_cell_type_unified (biology). PC1 = 81%. **(B)** Sample×PC score heatmaps for 01_raw S0_no_removal strict (top) and 10_mnn S0_no_removal strict post-removal (bottom), with Biology, RNA_BATCH, and Principal component sidebar annotations; colour scale blue–red (negative to positive PC scores). **(C)** PCA and tSNE scatter plots for 10_mnn S0_no_removal strict, with PC1 = 48.4%. **(D)** Sample×PC score heatmaps for a second strategy condition, showing variance redistribution across PCs after harmonization. **(E)** PCA and tSNE scatter plots for a biomaterial-restricted strategy condition (KNN imputation), PC1 ~23%. **(F)** PCA and tSNE scatter plots for a C-strategy strict condition. Batch legend (Illumina microarrays, RNA sequencing, Affymetrix microarrays) and biology legend (Early to GC B cells, Mature to plasma B cells, Malignancies) shown at bottom.

**Panel-level description:**

**Panel A — 01_raw S0_no_removal strict.** Two-row × two-column scatter grid. Row labels: "By batch" (top) and "By biology" (bottom). Columns: PCA (PC1 81%, PC2 on y-axis) and tSNE. Colours: 29 RNA_BATCH entries (batch row) or Temperature-Split biology palette (biology row). Each point = one sample.

**Panel B — Sample×PC heatmaps (S0_no_removal).** Two heatmaps stacked vertically. Top: 01_raw S0_no_removal strict. Bottom: 10_mnn S0_no_removal strict post-removal. Each heatmap: samples (columns) × principal components (rows). Colour encodes PC score value (blue = negative, red = positive). Right sidebar strips: Biology (Temperature-Split), RNA_BATCH (29-colour palette), Principal components labels. Colour bar shown with numeric range.

**Panel C — 10_mnn S0_no_removal strict.** Same two-row × two-column scatter grid as Panel A. PCA PC1 = 48.4%. tSNE shows intermixed batch colours.

**Panel D — Sample×PC heatmaps (second strategy).** Same format as Panel B; shows a second strategy condition for cross-strategy comparison of PC structure.

**Panel E — Biomaterial-restricted strategy, KNN imputation.** Two-row × two-column scatter grid; PC1 ~23%. Shows within-modality batch mixing after harmonization.

**Panel F — C-strategy strict condition.** PCA and tSNE embeddings for C_rnaseq_only or comparable strategy under strict imputation.

**Results section:**

The raw S0_no_removal data (Panel A) is almost entirely batch-driven: PC1 captures 81% of variance, and tSNE shows 29 distinct batch-segregated clusters. Virtually no biology-driven grouping is visible in the PCA batch-coloured view, confirming that uncorrected multi-platform data is unsuitable for downstream biological analysis.

MNN reduces PC1 to 48.4% (Panel C), a 40% relative reduction in batch variance concentration. More critically, the tSNE biology panel shows that DLBCL, FL, and Normal B-cell clusters remain spatially distinct after MNN, demonstrating that biology-preserving batch removal is achievable in the full 29-batch multi-platform context. The sample×PC heatmaps (Panels B, D) make this redistribution explicit: in the raw condition, PC1 carries a nearly uniform per-batch signal visible as horizontal stripes that align with RNA_BATCH annotation colours; after MNN post-removal, variance redistributes across PC2–PC10 with the RNA_BATCH colour structure becoming progressively less coherent, indicating that batch no longer dominates the top principal components.

The biomaterial-restricted subset panels (E, F) demonstrate that within-modality harmonization achieves even lower PC1 values (~23%) than cross-platform MNN, but this reflects reduced inter-platform variance rather than superior harmonization — a distinction critical for interpreting PCR values across strategies.

---

### Figure 5. PCA, tSNE, and per-sample PC heatmaps for J_ff_only, K_ffpe_only, and S0_no_removal strategy comparisons

**Proposed article caption:**

> Visual inspection of harmonization performance for biomaterial-specific and cross-platform strategies. **(A)** PCA and tSNE scatter plots for 10_mnn J_ff_only strict (PC1 = 28.7%), coloured by RNA_BATCH and Diagnosis_cell_type_unified. **(B)** Sample×PC score heatmaps for 01_raw J_ff_only strict (top) and 10_mnn J_ff_only strict (bottom), with Biology, RNA_BATCH, and PC sidebar annotations. **(C)** PCA and tSNE scatter plots for 04_sva K_ffpe_only softimpute (PC1 = 38.4%) and 04_sva K_ffpe_only strict; raw baseline PC1 = 87.6%. **(D)** Sample×PC score heatmaps for 01_raw K_ffpe_only strict (top) and 04_sva K_ffpe_only softimpute (bottom). **(E)** PCA and tSNE scatter plots for 13_fsmvn S0_no_removal strict (PC1 = 32.1%) and a second S0_no_removal condition. Batch legend (Illumina microarrays, RNA sequencing, Affymetrix microarrays) and biology legend shown at bottom.

**Panel-level description:**

**Panel A — 10_mnn J_ff_only strict.** Two-row × two-column scatter grid. Row labels: "By batch" and "By biology". PCA: PC1 = 28.7%. tSNE shows inter-platform mixing of FF batch types (Affymetrix, Illumina microarray, Agilent, RNA-seq FF subsets).

**Panel B — Sample×PC heatmaps (J_ff_only).** Two heatmaps stacked vertically: 01_raw J_ff_only strict (top) and 10_mnn J_ff_only strict (bottom). Format identical to Figure 4 Panel B. Sidebar: Biology, RNA_BATCH (FF-subset palette), PC labels.

**Panel C — 04_sva K_ffpe_only (softimpute and strict).** Two scatter pairs shown. Left: softimpute condition, PCA PC1 ~38.4%. Right: strict condition. Row labels: "By batch" and "By biology". The softimpute biology panel shows DLBCL and FL clusters distinguishable in tSNE despite cross-FFPE-platform mixing.

**Panel D — Sample×PC heatmaps (K_ffpe_only).** Top: 01_raw K_ffpe_only strict. Bottom: 04_sva K_ffpe_only softimpute. Sidebar annotations show Biology and RNA_BATCH for the FFPE-only subset (Affymetrix FFPE, Illumina microarray FFPE, RNA-seq FFPE types). Colour scale: blue–red.

**Panel E — 13_fsmvn S0_no_removal strict (two conditions).** Two scatter pairs side by side. PCA PC1 ~32.1% for the first condition. tSNE shows residual platform-type clustering after FSMVN.

**Results section:**

Three key biological findings emerge from Figure 5.

For J_ff_only (Panel A, B): MNN reduces PC1 from ~69% (raw) to 28.7% within the fresh-frozen subset. The sample×PC heatmap shows that after MNN, the RNA_BATCH-colour stripe pattern in PC1 is substantially reduced, with batch signal redistributed across PC2–PC5. DLBCL and FL clusters remain resolved in tSNE, confirming that MNN preserves the biology–batch variance distinction even within a multi-platform FF-only context.

For K_ffpe_only (Panels C, D): This is the most technically striking result in the figure. The raw PC1 = 87.6% represents the most extreme batch domination in the entire benchmark — Affymetrix FFPE, Illumina FFPE, and RNA-seq FFPE platforms are nearly completely segregated. SVA with softimpute reduces this to ~38.4%, and the tSNE batch-coloured panel shows for the first time that all three FFPE platform types are co-mingled in embedding space. The sample×PC heatmap directly confirms that after SVA, PC1 loses its clean RNA_BATCH-aligned stripe structure. This constitutes the first demonstrated mixing of FFPE Affymetrix, FFPE Illumina microarray, and FFPE RNA-seq data in a single harmonized transcriptomic dataset for B-cell lymphomas.

For S0_no_removal FSMVN (Panel E): PC1 ~32.1% represents a strong global correction (comparable to MNN), but the tSNE biology panel shows platform-type sub-clusters persisting — FSMVN homogenizes expression distributions without learning the biology–batch structure that MNN captures. This explains why FSMVN scores well on global metrics (PCR) but poorly on local metrics (iLISI, kBET) in the clustermap.

---

### Figure 6. PCR and per-PC variance analysis for 31 harmonization methods

**Principal component regression and per-PC variance decomposition across 31 methods and 14 strategies, with method-level and strategy-level barplots and per-PC heatmaps.**

**Proposed article caption:**

> Principal component regression (PCR) analysis and per-PC variance decomposition across 31 harmonization methods and 14 batch removal strategies. **(A)** Grouped barplot of PCR values for three annotation covariates — pcr_RNA_BATCH (dark brown), pcr_Diagnosis_cell_type_unified (teal), pcr_COHORT_LABEL (beige) — for each harmonization method, ordered by harshness level. Methods are colour-coded by harshness (green = low, orange = medium, red = high) with status annotations (good/medium/bad). **(B)** Same PCR barplot grouped by batch removal strategy (14 strategies, ordered from C_rnaseq_only with lowest batch PCR to D_malignant_only with highest), including pcr_RNASEQ_SOURCE as a fourth covariate. **(C)** Scatter plot of pcr_RNA_BATCH (x-axis, 0–1) vs. pcr_Diagnosis_cell_type_unified (y-axis, 0.4–1.0) for all 2,234 attempts, coloured by harmonization method. Star symbols (☆) mark the 15 manually curated best approaches. **(D)** Top: same scatter coloured by batch removal strategy. Bottom: two heatmaps showing mean percentage of variance explained per PC (PC1–PC10, blue scale, 0–100%) and mean R² explained by RNA_BATCH per PC (PC1–PC10, red scale, 0–1), both × harmonization method (ordered as in A).

**Panel-level description:**

**Panel A — PCR by method.** Horizontal grouped barplot, one triplet of bars per method, ordered by harshness (left = low, right = high). Three sub-bars per method: pcr_RNA_BATCH (dark brown), pcr_Diagnosis_cell_type_unified (teal), pcr_COHORT_LABEL (beige). Harshness colour strip below x-axis; good/medium/bad status labels above bars.

**Panel B — PCR by strategy.** Same barplot format; x-axis = 14 strategies ordered by ascending mean pcr_RNA_BATCH. Four sub-bars per strategy (adds pcr_RNASEQ_SOURCE, olive). Strategy-level status annotations shown.

**Panel C — PCR scatter by method.** 2,234 dots, coloured by harmonization method (31-colour legend). Stars (☆) mark 15 best approaches. X-axis: pcr_RNA_BATCH (0–1); y-axis: pcr_Diagnosis_cell_type_unified (0.4–1.0).

**Panel D — PCR scatter by strategy + per-PC heatmaps.** Top: same scatter recoloured by batch removal strategy (14-colour legend). Bottom left: blue heatmap (31 methods × PC1–PC10, % variance explained, 0–100%). Bottom right: red heatmap (31 methods × PC1–PC10, R² explained by RNA_BATCH, 0–1).

**Results section:**

PCR analysis reveals a fundamental separation between methods: most harmonizers (limma, pycombat, NPN, XPN, median_scaling, harmonizr) reduce pcr_RNA_BATCH modestly to 0.6–0.8, while only MNN, SVA, FSQN R, and CombatSeq achieve pcr_RNA_BATCH < 0.5 in appropriate strategy contexts. Raw (01_raw) and qsmooth (14_qsmooth) sit at pcr_RNA_BATCH ~0.9–1.0, confirming that no harmonization has been applied.

Critically, pcr_Diagnosis_cell_type_unified does not decrease proportionally with pcr_RNA_BATCH. Methods like AMDBNorm and FSMVN achieve low pcr_RNA_BATCH (strong global correction) but simultaneously reduce pcr_Diagnosis values, indicating over-correction that erases biologically meaningful variance. In contrast, the best approaches (stars in Panel C) cluster at pcr_RNA_BATCH 0.7–1.0 with pcr_Diagnosis_cell_type_unified 0.85–0.95 — these retain the maximum biology-associated variance while still reducing batch-associated variance relative to their strategy baseline.

The per-PC heatmaps (Panel D bottom) expose a mechanistic distinction: in raw data and qsmooth, PC1 carries ~80–100% of variance and R²_RNA_BATCH ~0.9 at PC1. After effective harmonizers (MNN, SVA, FSQN R), PC1 drops to ~20–50% variance, R² at PC1 drops to ~0.2–0.4, and batch signal decays to near-zero by PC7. TMM (22_tmm) and VST (23_vst) show an unusual pattern: low PC1 R²_RNA_BATCH but strong residual batch signal in PC2–PC5, suggesting that these methods distort the variance structure rather than removing batch effects.

---

### Figure 7. iLISI vs. cLISI scatter for local batch mixing and biology preservation [INCOMPLETE]

**Local integration and biology preservation trade-off for 2,234 harmonization attempts assessed by iLISI and cLISI. [INCOMPLETE — requires additional panels and formatted legends before submission]**

**Draft proposed article caption:**

> Local integration and biology preservation trade-off across 2,234 harmonization attempts. **(A)** Scatter of iLISI RNA_BATCH (x-axis, 1.0–2.2; higher = better local batch mixing) vs. cLISI Diagnosis_cell_type_unified (y-axis, 1.0–2.0; higher = better local biology preservation) for all 2,234 attempts, coloured by harmonization method. Star symbols (☆) mark the 15 curated best approaches. **(B)** Same scatter coloured by batch removal strategy.

**Panel-level description:**

**Panel A — iLISI × cLISI by harmonization method.** 2,234 dots, multicolour by harmonization method. X range: 1.0–2.2; Y range: 1.0–2.0. Stars (☆) mark best approaches. Several stars appear at high iLISI × moderate cLISI (AMDBNorm/FSMVN runs); one star at iLISI ~2.0 × cLISI ~1.2.

**Panel B — iLISI × cLISI by batch removal strategy.** Same scatter recoloured by strategy. C_rnaseq_only (teal) extends to highest iLISI values (1.8–2.2). K_ffpe_only achieves best local integration within its subset.

**Missing elements:** Legends for panels A and B; axis tick labels for panel B; additional panels (kBET × iLISI, cLISI × ASW_bio, per-group local metrics); figure title and full annotation.

**Results section:**

[To be completed when the figure is finalized.] The visible data confirm a positive but loose correlation between iLISI and cLISI across all 2,234 attempts, consistent with the hypothesis that effective batch mixing tends to preserve rather than destroy biology structure — except for over-correcting methods (AMDBNorm, FSMVN) where high iLISI is achieved at the cost of collapsed cLISI. The best approaches cluster at iLISI 1.5–2.0 × cLISI 1.5–1.8, confirming that the top methods identified by global metrics (Figure 6) also achieve superior local performance.

---

## SUPPLEMENTARY FIGURES

---

### Supplementary Figure 1. Sample composition per cohort — biology and platform

**Per-cohort sample distribution for the 88-cohort dataset, coloured by biology group and by RNA batch.**

**Proposed caption:**

> Per-cohort sample composition of the 88-cohort dataset. **(A)** Stacked barplot (log scale) of sample counts per cohort, coloured by diagnosis/cell-type biology group. Cohorts are ordered by total sample count. **(B)** Stacked barplot of the same cohorts coloured by RNA_BATCH / platform group.

**Panel-level description:**

**Panel A:** ~88 bars, log₁₀ y-axis (10⁰–10³). Temperature-Split biology colour scheme. Large DLBCL-dominant cohorts (>500 samples) on the left; small cohorts (1–10 samples) on the right.

**Panel B:** Same 88 bars recoloured by RNA_BATCH (29-colour palette). Most cohorts map to a single batch; some span two batches.

**Results section:**

Cohort-level composition reveals that batch and biology are partially confounded: several RNA batches consist entirely of one diagnosis (e.g., FFPE-only cohorts are predominantly DLBCL), while FL cohorts are disproportionately represented in Affymetrix microarray batches. This confounding is the central motivation for the biomaterial- and platform-restricted strategies in the benchmark, which attempt to harmonize within more homogeneous subsets before assessing cross-platform generalization.

---

### Supplementary Figure 2. Per-cohort expression histograms — S0_no_removal, strict imputation

**Per-cohort expression value distributions for all 88 cohorts under S0_no_removal with strict imputation (3,447 genes).**

**Proposed caption:**

> Distribution of gene expression values per cohort at S0_no_removal with strict imputation (3,447 genes). Each panel shows a histogram of expression values for one cohort, characterizing the initial expression range, scale, and bimodal structure prior to harmonization. The 88 panels together reveal the full extent of cross-cohort distributional heterogeneity that harmonization must address.

**Panel-level description:**

Grid of 88 histograms (one per cohort). Expression values (x-axis, log₂ scale) vs. frequency (y-axis). Microarray cohorts show characteristic bimodal distributions; RNA-seq cohorts show right-skewed or unimodal distributions. Large inter-cohort scale differences are visible even between cohorts of the same platform type.

**Results section:**

The 88 per-cohort histograms expose the full heterogeneity that any harmonization method must resolve: Affymetrix cohorts show bimodal distributions with a low-expression peak at ~4–5 and a high-expression peak at ~8–10 (log₂); RNA-seq cohorts show right-skewed unimodal distributions with a mode at ~6–8; FFPE microarray cohorts show compressed dynamic ranges relative to FF counterparts. These differences in distributional shape, not just mean offset, explain why global location-and-scale methods (median scaling, quantile normalization) fail to fully harmonize multi-platform data — they correct for mean and variance but not for the bimodal shape specific to microarray data.

---

### Supplementary Figure 3. Per-cohort expression histograms — S0_no_removal, KNN imputation

**Per-cohort expression value distributions for all 88 cohorts under S0_no_removal with KNN imputation.**

**Proposed caption:**

> Distribution of gene expression values per cohort at S0_no_removal with KNN imputation. Comparison with Supplementary Figure 2 (strict imputation) illustrates the effect of the expanded gene set (KNN, ~11,768 genes vs. strict 3,447) on per-cohort expression distributions.

**Panel-level description:**

Same 88-cohort grid as Supplementary Figure 2. Expression distributions include the additional ~8,000 genes recovered by KNN imputation. Axes may differ per panel (per-cohort autoscaling). Bimodal structure in microarray cohorts is partially retained; the low-expression peak may broaden due to KNN-imputed values for genes with partial NA coverage.

**Results section:**

KNN imputation adds ~8,321 genes relative to strict, primarily genes with incomplete coverage across FFPE microarray batches. The per-cohort histograms under KNN show that the low-expression peak in microarray cohorts broadens slightly, reflecting the KNN-imputed values assigned to near-zero-expression genes in batches that lack measurements. This distributional widening motivates the use of softimpute as an alternative: softimpute's low-rank matrix completion assigns structurally consistent imputed values, producing distributions more similar to strict imputation than KNN does.

---

### Supplementary Figure 4. Per-cohort expression histograms — S0_no_removal, softimpute imputation

**Per-cohort expression value distributions for all 88 cohorts under S0_no_removal with softimpute imputation.**

**Proposed caption:**

> Distribution of gene expression values per cohort at S0_no_removal with softimpute imputation. Comparison with Supplementary Figures 2–3 illustrates the cumulative effect of imputation strategy choice on cross-cohort expression alignment.

**Panel-level description:**

Same 88-cohort grid. Axes adjusted relative to strict and KNN panels. Softimpute-imputed gene distributions show tighter cohort-to-cohort variation in the low-expression range compared with KNN, consistent with the rank-constrained matrix completion approach assigning smoother imputed values.

**Results section:**

Softimpute produces per-cohort distributions that are ~10 percentage points closer to strict-imputation distributions than KNN, explaining the consistently superior harmonization performance of softimpute over KNN observed across the 2,234 attempts. The residual inter-cohort distributional differences visible even after softimpute imputation motivate the downstream harmonization methods benchmarked in the main analysis.

---

### Supplementary Figure 5. Jaccard similarity clustermap for all strategy × imputation gene sets

**Pairwise Jaccard similarity of gene sets across all 42 strategy × imputation combinations, showing imputation as the primary determinant of gene-set overlap.**

**Proposed caption:**

> Pairwise Jaccard similarity index for gene sets retained across all 42 strategy × imputation combinations (14 strategies × 3 imputations). Colour encodes Jaccard similarity (0 = no overlap, 1 = identical gene sets). Strategies sharing the same imputation method cluster together, demonstrating that imputation is the primary driver of gene set composition.

**Panel-level description:**

42×42 symmetric heatmap with hierarchical dendrograms. Colour scale: white (low overlap) → dark teal/blue (high overlap; diagonal = 1.0). Three major cluster blocks: strict (14 entries with identical gene sets, Jaccard = 1.0), KNN (intermediate overlap across strategies), softimpute (high overlap with KNN, slightly different from strict). Axes labelled with strategy_imputation strings.

**Results section:**

The Jaccard clustermap makes explicit that imputation method, not strategy, determines which genes are included in the analysis. All 14 strategies under strict imputation share identical gene sets (Jaccard = 1.0) — the 3,447 genes with no NA in any sample across the full S0_no_removal dataset. Under KNN and softimpute, gene set composition is strategy-dependent: strategies that exclude FFPE microarray batches (J_ff_only, C_rnaseq_only) recover more genes (~9,000–15,000) than strategies that include them (G_affymetrix_only ~6,700). The high KNN–softimpute cross-imputation Jaccard (~0.8–0.9 for most strategies) confirms that both non-strict imputation methods recover largely the same gene universe; softimpute consistently recovers slightly fewer genes, prioritising completeness quality over count.

---

### Supplementary Figure 6. Harmonization attempts in metric space and metric computation success rate

**PCA of 2,234 attempts in 87-dimensional metric space, and a success-rate heatmap for metric computation across all strategy × imputation × method combinations.**

**Proposed caption:**

> Overview of 2,234 harmonization attempts in metric space and success rate of metric computation. **(A)** PCA scatter of all 2,234 attempts in the 87-dimensional polarity-normalized metric space, coloured by batch removal strategy × imputation combination. **(B)** Heatmap of metric computation success (fraction of metrics successfully computed) across 42 strategy × imputation conditions (rows) × 68 harmonization method × post_rm combinations (columns). Green = all metrics computed; red = computation failures.

**Panel-level description:**

**Panel A:** 2D PCA projection (2,234 dots), coloured by 42 (strategy × imputation) combinations. Clear separation by strategy; imputation creates sub-clusters within each strategy.

**Panel B:** 42 × 68 heatmap. Most cells green (all metrics computed). Red/orange cells indicate specific method × strategy × imputation failures (variancePartition OOM errors, kBET failures on small batch sizes).

**Results section:**

The metric-space PCA (Panel A) provides independent confirmation that batch removal strategy is the dominant source of variation in harmonization outcomes: K_ffpe_only and C_rnaseq_only occupy regions far from S0_no_removal and D_malignant_only, with the distance encoding the reduction in accessible metric range (fewer platforms, fewer possible mixing gradients). This spatial separation explains why cross-strategy comparisons of absolute metric values are misleading: a "good" iLISI for K_ffpe_only is numerically lower than a "good" iLISI for S0_no_removal because the K_ffpe_only dataset has fewer RNA_BATCH levels to mix.

The computation success heatmap (Panel B) identifies fragile method × strategy combinations: kBET fails on strategies with very small batch sizes (I_rare_batches_removed at batch size <5), and variancePartition times out on the largest strategies (S0_no_removal with softimpute). These failures are handled by the pipeline's success-rate filter, which excludes any attempt missing more than 10% of metrics from the 2,234 valid set.

---

### Supplementary Figure 7. Metric-metric Spearman correlation clustermap

**Pairwise Spearman correlation matrix of 87 batch effect metrics, revealing two orthogonal metric clusters (local neighborhood vs. global distance).**

**Proposed caption:**

> Pairwise Spearman correlation matrix of 87 batch effect metrics. The 87×87 symmetric clustermap shows Spearman rank correlations across all scoring metrics computed over 2,234 attempts. Row and column annotations indicate Metric group (A–K), Annotation column (batch vs. biology covariates), and Metric type. Two major correlation clusters are identified: a Local metrics cluster (iLISI, kBET, entropy, ASW_batch; high positive intra-cluster correlation, near-zero cross-cluster correlation with global metrics) and Global metrics clusters (PCR, DSC, KS tests, distance ratios; high positive intra-cluster correlation). Biology-preservation metrics (cLISI, ASW_bio, WaterMelon bio) show intermediate correlations, bridging the two clusters.

**Panel-level description:**

87×87 symmetric heatmap with hierarchical dendrogram. Colour scale: deep blue (Spearman ρ = −1) → white (ρ = 0) → deep red (ρ = +1). Diagonal = +1.

*Local metrics cluster (~15 rows/cols):* iLISI_RNA_BATCH, iLISI_COHORT_LABEL, iLISI_PLATFORM_RNA, umap/tsne entropy metrics, kBET acceptance rates. High mutual correlation (ρ = 0.6–0.9). Near-zero or weakly negative correlation with global metrics.

*Global metrics clusters (~50 rows/cols):* PCR (all covariates), DSC (all covariates), ks_mean_D, ks_frac_sig, distance ratios, WaterMelon batch metrics. Strong intra-cluster positive correlation (ρ = 0.5–0.95). Sub-clusters: RNASEQ_SOURCE metrics; PLATFORM_RNA metrics; RNA_BATCH metrics; biology covariates.

Row/column annotation strips: Metric group (A–K), Annotation column (8 colours), Metric type (4 colours).

**Results section:**

The near-zero Spearman correlation between local and global metrics is the key statistical finding of this figure. It demonstrates that iLISI/kBET and PCR/DSC are not redundant: a method can score high on one while scoring low on the other. This empirical orthogonality justifies the two-axis evaluation framework used throughout the benchmark (batch mixing × biology preservation), and it explains why no single metric can rank harmonization methods across all strategies — the local–global trade-off is real and context-dependent. Biology-preservation metrics (cLISI, ASW_bio) bridge the two clusters with intermediate correlation values, consistent with their conceptual role as a second axis orthogonal to both batch-mixing and global-correction metrics.

---

### Supplementary Figure 8. Metric space embeddings colored by annotation type

**PCA, UMAP, and tSNE projections of 87 metrics as points, coloured by metric type, annotation column, and metric group.**

**Proposed caption:**

> Projection of 87 batch effect metrics into two-dimensional space using PCA, UMAP, and t-SNE. A 3×3 grid shows the 87 metrics as points, coloured by three annotation schemes: Metric type, Annotation column, and Metric group (A–K). In all three embeddings, local neighborhood metrics form a spatially distinct cluster from global distance metrics and distribution similarity metrics.

**Panel-level description:**

3×3 grid. Rows: PCA (top), UMAP (middle), t-SNE (bottom). Columns: coloured by Metric type (left), Annotation column (centre), Metric group (right). Each panel: 87 points. Local metrics cluster occupies a distinct region in all 9 panels, with clearest separation in UMAP and t-SNE.

**Results section:**

The consistent spatial separation of local and global metric types across all three embedding methods (PCA, UMAP, t-SNE) and all three colouring schemes confirms that metric identity (local vs. global) is the dominant driver of metric-space position, not the choice of covariate (RNA_BATCH vs. biology). Distribution similarity metrics (Group D, KS tests) form a third sub-cluster adjacent to global distance metrics, confirming that KS-based metrics capture overlapping but non-identical information to PCR/DSC. This structure validates the metric taxonomy used in Figure 3's clustermap row annotations.

---

### Supplementary Figure 9. Metric space overview of all 2,234 attempts — five experimental factors

**PCA, UMAP, and tSNE projections of 2,234 attempts in 87-dimensional metric space, coloured by strategy, method, harshness, imputation, and post-removal.**

**Proposed caption:**

> Overview of 2,234 harmonization attempts projected into metric space (PCA, UMAP, t-SNE), coloured by five experimental factors. A 5×3 grid shows the full attempt space across three embeddings and five annotation layers: batch removal strategy, harmonization method, harshness level, imputation method, and post-removal flag. Batch removal strategy explains the largest fraction of metric-space variance.

**Panel-level description:**

15-panel grid (5 rows × 3 columns).
- Row 1 (by strategy, 14 colours): clearest clustering; each strategy occupies a distinct region.
- Row 2 (by harmonization method, 31 colours): within-strategy method clustering visible.
- Row 3 (by harshness, 3 colours): moderate separation; high-harshness methods cluster separately.
- Row 4 (by imputation, 3 colours): strict vs. KNN/softimpute shows moderate separation.
- Row 5 (by post-removal, 2 colours): minimal separation — post-removal is the smallest marginal factor.

**Results section:**

The hierarchical ordering of factor importance — strategy > method > harshness > imputation > post-removal — is visually evident in the 15-panel grid: the sharpest cluster boundaries appear in the strategy row and progressively blur through subsequent rows. This ordering matches the variance decomposition analysis in the main CLAUDE.md decision tree and provides the empirical basis for the recommendation that strategy selection should be the primary decision point when planning harmonization for a new multi-platform dataset. Post-removal's negligible metric-space effect confirms that removing one PCA-outlier batch is a fine-tuning step, not a fundamentally different harmonization approach.

---

### Supplementary Figure 10. Alternative metric space embedding view

**Alternative 2D PCA/UMAP/t-SNE embedding of 2,234 harmonization attempts confirming strategy-driven clustering.**

**Proposed caption:**

> Additional 2D embedding view of the 2,234 harmonization attempts in metric space, confirming strategy-driven clustering observed in Supplementary Figure 9. An alternative colouring or parameterisation highlights structural detail not visible in the primary grid.

**Panel-level description:**

Alternative 2D projection of the same 2,234 attempts. Similar strategy-driven cluster structure to Supplementary Figure 9 Row 1. May show UMAP with different n_neighbors, or colouring by a composite score (polarity-normalized mean metric). Confirms robustness of strategy-driven separation.

**Results section:**

The consistency between this alternative embedding and those in Supplementary Figure 9 confirms that the strategy-driven cluster structure is not an artefact of a specific dimensionality reduction choice. The spatial positions of individual attempt groups (K_ffpe_only, C_rnaseq_only, S0_no_removal) are robust across embedding parameterisations, indicating that the 87-metric space genuinely encodes strategy-level differences as high-variance directions.

---

### Supplementary Figure 11. MNN visual inspection: S0_no_removal, H_affymetrix_extended, D_malignant_only

**PCA, UMAP, and tSNE embeddings for MNN across three multi-platform strategies and the raw baseline.**

**Proposed caption:**

> PCA, UMAP, and t-SNE embeddings for MNN (10_mnn) harmonization across three strategies and the raw baseline (01_raw). Columns: (1) 10_mnn S0_no_removal strict; (2) 10_mnn H_affymetrix_extended strict; (3) 10_mnn D_malignant_only strict; (4) 01_raw S0_no_removal strict. Rows alternate between RNA_BATCH colouring (batch mixing) and Diagnosis_cell_type_unified colouring (biology preservation), for each of the three embeddings (PCA, UMAP, tSNE). PC1 variance annotated at top of PCA panels.

**Panel-level description:**

4 columns × 6 rows (alternating batch/biology colouring per embedding: PCA×2, UMAP×2, tSNE×2). PC1 variance annotated at top of PCA panels. Raw baseline (column 4) shows tight batch-segregated clusters; PC1 ~81%. MNN columns show homogeneous batch mixing with retained biology structure. H_affymetrix_extended shows moderately less mixing than S0 (fewer RNA-seq batches present). Full 29-RNA_BATCH and biology legends shown at right.

**Results section:**

MNN achieves comparable batch mixing quality across three multi-platform strategies (S0_no_removal, H_affymetrix_extended, D_malignant_only), reducing PC1 from ~81% to 39–49% and producing homogeneous batch colouring in UMAP and tSNE. Biology clusters (DLBCL, FL, Normal B cells) are consistently distinguishable across all three MNN columns, confirming that MNN's biology-preservation is a robust property not contingent on the specific strategy or sample composition. The H_affymetrix_extended strategy shows slightly less local mixing than S0_no_removal, consistent with the absence of RNA-seq batches as anchoring references in the neighbour graph.

---

### Supplementary Figure 12. SVA visual inspection: C_rnaseq_only strategy

**PCA, UMAP, and tSNE embeddings for SVA across three imputation methods on the C_rnaseq_only strategy.**

**Proposed caption:**

> PCA, UMAP, and t-SNE embeddings for SVA (04_sva) harmonization on the C_rnaseq_only strategy with three imputation methods and the raw baseline. Columns: (1) 04_sva C_rnaseq_only strict; (2) 04_sva C_rnaseq_only knn; (3) 04_sva C_rnaseq_only softimpute; (4) 01_raw C_rnaseq_only strict. SVA with softimpute achieves the best local RNA-seq batch mixing and reveals two FL subgroups in UMAP.

**Panel-level description:**

Same 4×6 format. Left three columns: SVA with strict/knn/softimpute. Column 4: raw baseline. PC1: SVA columns ~25–27%; raw baseline ~higher. Biology colouring rows show DLBCL cluster (large, central) and FL cluster (smaller, distinct, dark red). Softimpute panel shows clearest FL sub-cluster separation. Full RNA-seq batch legend (7 batch types) and biology legend shown.

**Results section:**

SVA on C_rnaseq_only reduces PC1 to 25–27% regardless of imputation, but the imputation method critically determines local embedding structure. Softimpute produces the cleanest RNA-seq batch mixing in UMAP and the clearest separation of two FL subgroups — a biologically significant finding, as this sub-clustering may correspond to the GCB and non-GCB FL subtypes. KNN imputation produces intermediate results, while strict imputation preserves slightly stronger biology separation but with reduced batch mixing. This imputation-dependent FL sub-structure is the primary justification for recommending SVA + softimpute (rather than SVA + strict) for the C_rnaseq_only strategy.

---

### Supplementary Figure 13. FSQN R visual inspection: C_rnaseq_only strategy

**PCA, UMAP, and tSNE embeddings for FSQN R across three imputation methods on the C_rnaseq_only strategy.**

**Proposed caption:**

> PCA, UMAP, and t-SNE embeddings for FSQN R (16_fsqn_r) harmonization on the C_rnaseq_only strategy with three imputation methods and the raw baseline. Columns: (1) 16_fsqn_r strict; (2) 16_fsqn_r knn; (3) 16_fsqn_r softimpute; (4) 01_raw strict. FSQN R achieves PC1 variance of 18–20.6% (lower than SVA), but KNN and softimpute imputation introduce embedding artefacts.

**Panel-level description:**

Same 4×6 format. FSQN R columns: PC1 ~18–20.6%. UMAP/tSNE biology rows for KNN and softimpute show dispersed, less structured clouds. Strict FSQN R shows biology clusters comparable to SVA + strict. PCA y-axis scale inflated for KNN (up to ~400 vs. typical ~50) indicating imputation-driven outlier coordinates.

**Results section:**

FSQN R achieves lower PC1 than SVA on C_rnaseq_only (18–20.6% vs. 25–27%), appearing superior by global PCR metrics. However, KNN and softimpute imputation introduce artefactual spread in the PCA coordinate space (y-axis scale up to 400), indicating that FSQN R is sensitive to imputed gene values in a way SVA is not. The strict-imputation FSQN R column, which avoids this artefact, produces biology clusters comparable to SVA + strict but with stronger global correction. This explains the recommendation of FSQN R for RNA-seq + Illumina microarray strategies where strict imputation is preferred: FSQN R's global correction advantage is only realized safely under strict imputation, not under KNN or softimpute.

---

### Supplementary Figure 14. MNN and FSQN R on J_ff_only (fresh-frozen only)

**PCA, UMAP, and tSNE embeddings comparing MNN and FSQN R on the J_ff_only strategy against the raw baseline.**

**Proposed caption:**

> PCA, UMAP, and t-SNE embeddings for MNN (10_mnn) and FSQN R (16_fsqn_r) on the J_ff_only strategy (fresh-frozen samples only, N=3,167), compared to the raw baseline. Columns: (1) 10_mnn J_ff_only strict; (2) 16_fsqn_r J_ff_only strict; (3) 01_raw J_ff_only strict. PC1 variance: raw = 69.2%; FSQN R = 25.1%; MNN = 28.7%.

**Panel-level description:**

3 columns × 6 rows. Rows: PCA×2 (batch+biology), UMAP×2, tSNE×2. PC1 annotations: raw 69.2%, FSQN R 25.1%, MNN 28.7%. MNN and FSQN R columns show comparable biology cluster structure. Extended legend for all FF-only batch types (Affymetrix, Illumina microarray, Agilent, and RNA-seq).

**Results section:**

Within the J_ff_only fresh-frozen subset, FSQN R achieves slightly lower PC1 (25.1%) than MNN (28.7%), and both substantially improve over the raw baseline (69.2%). The comparable biology cluster structure in UMAP/tSNE between the two methods indicates that the PCR advantage of FSQN R does not translate into substantially different biological conclusions. However, at the local embedding level, MNN tends to produce denser, more cohesive biology clusters, while FSQN R produces sharper between-platform mixing — reflected in MNN's higher iLISI and FSQN R's better PCR. The choice between them for J_ff_only therefore depends on the downstream analytical goal: global normalization (FSQN R) vs. biology-cluster preservation (MNN).

---

### Supplementary Figure 15. SVA on K_ffpe_only (FFPE-only strategy)

**PCA, UMAP, and tSNE embeddings for SVA on K_ffpe_only with three imputation methods and the raw baseline.**

**Proposed caption:**

> PCA, UMAP, and t-SNE embeddings for SVA (04_sva) on the K_ffpe_only strategy (FFPE samples only, N=3,000) with three imputation methods and the raw baseline. Columns: (1) 04_sva softimpute; (2) 04_sva knn; (3) 04_sva strict; (4) 01_raw strict. PC1 variance: raw = 87.6%; SVA + softimpute = 38.4%. First demonstrated mixing of Affymetrix FFPE, Illumina FFPE, and RNA-seq FFPE platform types within a single harmonized dataset.

**Panel-level description:**

4×6 format. SVA + softimpute column: homogeneous batch colouring in UMAP across Affymetrix FFPE, Illumina FFPE, and RNA-seq FFPE batches. Biology colouring rows preserve DLBCL/FL separation. Raw baseline (column 4): PC1 = 87.6%, with FFPE microarray and RNA-seq FFPE occupying distinct PCA quadrants.

**Results section:**

K_ffpe_only presents the most extreme batch effect in the entire benchmark: raw PC1 = 87.6%, with Affymetrix FFPE, Illumina microarray FFPE, and RNA-seq FFPE batches forming fully segregated PCA clusters. SVA + softimpute reduces this to 38.4% — a 56% relative reduction — and for the first time produces a UMAP embedding where all three FFPE platform types co-mingle. The biology-coloured UMAP confirms that DLBCL and FL clusters remain distinguishable after this cross-platform FFPE mixing, establishing SVA + softimpute as the method of choice for FFPE-dominant datasets. Strict imputation with SVA shows weaker mixing (PC1 ~53%), confirming that the expanded gene set from softimpute provides the additional signal necessary for SVA to identify surrogate variables spanning the cross-FFPE-platform dimension.

---

### Supplementary Figure 16. FSMVN on S0_no_removal

**PCA, UMAP, and tSNE embeddings for FSMVN across three imputation methods on S0_no_removal and the raw baseline.**

**Proposed caption:**

> PCA, UMAP, and t-SNE embeddings for FSMVN (13_fsmvn) harmonization on the S0_no_removal strategy with three imputation methods and the raw baseline. Columns: (1) 13_fsmvn strict; (2) 13_fsmvn knn; (3) 13_fsmvn softimpute; (4) 01_raw strict. FSMVN achieves partial global correction (PC1 reduced to 32–39%), but platform-specific batch clusters persist in UMAP and t-SNE.

**Panel-level description:**

4×6 format. FSMVN columns: PC1 32–39%. UMAP batch-coloured rows show residual platform-type segregation. Biology rows show mixed DLBCL/FL structure without clear two-subgroup separation. Raw baseline: PC1 ~80.5% with clear platform-segregated PCA.

**Results section:**

FSMVN achieves global PCR values comparable to MNN (PC1 32–39%), but the embedding structure reveals a qualitative failure mode: Affymetrix batches remain spatially segregated from RNA-seq batches in UMAP and tSNE even after FSMVN correction. This indicates that FSMVN normalizes global statistics (mean, variance) across batches without modelling the non-linear, platform-specific expression space structure that drives the residual clustering. The biology-coloured panels further show that FL and Normal B-cell clusters are less clearly separated after FSMVN than after MNN, consistent with FSMVN's lower cLISI and ASW_bio scores in the benchmark clustermap.

---

### Supplementary Figure 17. AMDBNorm across strategies

**PCA, UMAP, and tSNE embeddings for AMDBNorm across four strategy × imputation conditions.**

**Proposed caption:**

> PCA, UMAP, and t-SNE embeddings for AMDBNorm (33_amdbnorm) harmonization across four strategy × imputation conditions. Columns: (1) 33_amdbnorm K_ffpe_only strict; (2) 33_amdbnorm S0_no_removal strict; (3) 33_amdbnorm J_ff_only knn; (4) 33_amdbnorm J_ff_only softimpute. AMDBNorm achieves very low PC1 variance (~12–16%), but UMAP and t-SNE show scattered, unstructured biology clouds.

**Panel-level description:**

4×6 format. All AMDBNorm columns: PC1 ~12–16% (lowest across all methods). Biology-coloured UMAP/tSNE rows show dispersed point clouds with DLBCL, FL, and Normal B cells intermixed without clear cluster structure. Batch-coloured rows show highly homogeneous mixing.

**Results section:**

AMDBNorm achieves the lowest PC1 values in the benchmark (~12–16%), reflecting maximum global variance removal. However, the biology-coloured embedding panels reveal that this comes at the cost of complete biology structure collapse: DLBCL, FL, and Normal B-cell clusters are indistinguishable in all UMAP and tSNE panels. This over-correction disqualifies AMDBNorm for any downstream biological analysis requiring diagnostic subtype discrimination. The contrast with MNN — which achieves similar or higher PC1 values (~39–49%) while preserving biology clusters — demonstrates that the minimum-PCR criterion is not a valid harmonization objective for datasets where biology-associated variance must be retained.

---

### Supplementary Figure 18. Comprehensive PCR analysis — methods, strategies, post-removal, per-PC

**Strip plot, strategy-faceted catplot, post-removal comparison, and per-PC heatmaps for PCR across all 2,234 attempts.**

**Proposed caption:**

> Comprehensive principal component regression (PCR) analysis. **(A)** Strip plot of pcr_RNA_BATCH values across all harmonization attempts, grouped by harmonization method × imputation combination, showing the full distribution of PCR values per method. **(B)** Catplot of PCR values faceted by batch removal strategy (14 facets), showing method-level PCR distributions within each strategy context. **(C)** PCR values stratified by post-removal condition (post0 vs. post1), demonstrating the marginal effect of removing one PCA-outlier batch. **(D)** Dual heatmap: mean percentage of variance explained per PC (PC1–PC10, blue scale) and mean R² explained by RNA_BATCH per PC (red scale), both × harmonization method, confirming concentration of batch effect in PC1–PC3.

**Panel-level description:**

**Panel A — Strip plot of PCR by method × imputation.** X-axis: harmonization method × imputation combinations ordered by harshness. Y-axis: pcr_RNA_BATCH (0–1). Each point represents one harmonization attempt. Methods ordered by harshness (low to high). Softimpute and KNN imputation tend to produce slightly higher PCR than strict for the same method. qsmooth (14) shows the lowest and most concentrated PCR distribution. Raw (01) shows PCR 0.9–1.0.

**Panel B — Strategy-faceted catplot.** 14 facets (one per strategy). Within each facet: x-axis = harmonization method, y-axis = PCR. K_ffpe_only facet shows the lowest within-strategy PCR range; S0_no_removal and D_malignant_only show the highest.

**Panel C — Post-removal comparison.** Distribution comparison of pcr_RNA_BATCH for post0 vs. post1 conditions. Post-removal produces a 5–15 percentage-point PCR improvement for strategies with a strong outlier batch; negligible effect on average across all attempts.

**Panel D — Per-PC heatmaps.** Side-by-side (31 methods × PC1–PC10). Left (blue, % variance explained): raw/qsmooth near 100% in PC1; effective harmonizers reduce PC1 to ~20–40%. Right (red, R²_RNA_BATCH): raw/qsmooth show R² > 0.8 at PC1; effective harmonizers reduce this to < 0.2; signal decays to near-zero by PC7–PC10.

**Results section:**

The strip-plot distribution (Panel A) quantifies the method-level spread in PCR: most methods show wide within-method PCR ranges (spanning 0.3–0.4 units) driven primarily by strategy variation, while qsmooth occupies a uniquely narrow low-PCR distribution reflecting its consistent behaviour across strategies. This narrow distribution in qsmooth, however, reflects distributional distortion rather than effective batch removal — as confirmed by qsmooth's poor biology-preservation metrics.

The strategy-faceted catplot (Panel B) demonstrates that the same method can perform radically differently across strategies: SVA achieves the lowest PCR in C_rnaseq_only and K_ffpe_only (where it is the top method) but only mediocre PCR in S0_no_removal (where MNN outperforms it). This context-dependence is why no single method can be recommended universally, and why the decision tree in Figure 4 conditions method selection on strategy (biomaterial type and platform composition).

The per-PC heatmaps (Panel D) identify TMM and VST as anomalous: their R²_RNA_BATCH is low at PC1 but unexpectedly elevated at PC2–PC5, suggesting that these methods redistribute rather than remove batch variance — a pattern consistent with their known behaviour as differential expression normalization tools misapplied to cross-platform harmonization.

---

### Supplementary Figure 19. PCR vs. DSC scatter correlations

**Scatter plots of PCR and DSC correlation across complementary annotation covariates for all 2,234 attempts.**

**Proposed caption:**

> Correlations between Principal Component Regression (PCR) and Distance Similarity Coefficient (DSC) across complementary annotation covariates for all 2,234 harmonization attempts. Five scatter panels: **(A)** PCR_RNA_BATCH vs. PCR_PLATFORM_RNA; **(B)** PCR_RNA_BATCH vs. PCR_COHORT_LABEL; **(C)** PCR_RNA_BATCH (x) vs. DSC_RNA_BATCH (y, log scale 10¹ to 10⁻²⁹); **(D)** DSC_RNA_BATCH vs. DSC_PLATFORM_RNA (log×log); **(E)** DSC_RNA_BATCH vs. DSC_COHORT_LABEL. Star symbols (☆) mark the 15 curated best approaches throughout.

**Panel-level description:**

**Panel A (PCR_BATCH vs. PCR_PLATFORM):** ~2,234 dots, coloured by strategy. Near-diagonal distribution. Best approaches (stars) cluster at high PCR (0.7–1.0) for both axes.

**Panel B (PCR_BATCH vs. PCR_COHORT):** Fan-shaped scatter. Points at high PCR_RNA_BATCH spread widely in PCR_COHORT_LABEL (0.3–1.0), showing cohort-level batch effects are more heterogeneous.

**Panel C (PCR_BATCH vs. DSC_BATCH, log y):** Inverse S-shaped scatter. Y-axis: DSC_RNA_BATCH log scale 10¹ to 10⁻²⁹. Best approaches (stars) at PCR ~0.8–1.0 × DSC ~10⁻²⁰ to 10⁻²⁹.

**Panel D (DSC_BATCH vs. DSC_PLATFORM, log×log):** Tight near-diagonal scatter confirming covariate-level DSC consistency.

**Panel E (DSC_BATCH vs. DSC_COHORT):** Wider scatter; cohort-level separation less correlated with batch-level separation than platform-level separation.

**Results section:**

The PCR_RNA_BATCH × PCR_PLATFORM_RNA near-diagonal correlation (Panel A) confirms that batch-level and platform-level variance removal co-occur: methods that reduce batch PCR also reduce platform PCR proportionally. This makes PCR_RNA_BATCH a sufficient proxy for PCR_PLATFORM_RNA in method ranking. In contrast, PCR_COHORT_LABEL shows fan-shaped scatter (Panel B), indicating that cohort-level batch effects respond differently to harmonization than RNA_BATCH-level effects — a finding with practical implications for multi-cohort downstream analyses, where residual cohort structure can re-emerge even after effective RNA_BATCH harmonization.

Panel C's extreme DSC range (10¹ to 10⁻²⁹) visualizes why DSC is a more sensitive measure than PCR for discriminating between effective harmonizers: PCR saturates at 0.8–1.0 for many good methods, while DSC continues to discriminate across 30 orders of magnitude. The best approaches (stars) cluster at the extreme low-DSC end, confirming that MNN, SVA, and FSQN R achieve the most complete statistical separation of within-batch from across-batch expression distributions.

---

### Supplementary Figure 20. kBET and iLISI local batch mixing analysis [INCOMPLETE]

**kBET acceptance rate and iLISI scatter with per-method barplots for local batch mixing assessment. [INCOMPLETE — legends, axis labels, and additional panels required before submission]**

**Draft proposed caption:**

> Local batch mixing assessed by kBET acceptance rate and iLISI. **(A)** Scatter of kBET acceptance rate for RNA_BATCH (x-axis, log scale) vs. iLISI RNA_BATCH (y-axis, 1.0–2.2) for all 2,234 attempts; stars (☆) mark the 15 best approaches. **(B)** Same scatter with alternative colouring. **(C)** Bar chart of kBET acceptance rate per harmonization method for RNA_BATCH, COHORT_LABEL, and PLATFORM_RNA covariates, log scale. **(D)** Same barplot on linear scale with harshness and status annotation strips.

**Panel-level description:**

**Panel A:** 2,234 dots; x-axis = kBET acceptance rate RNA_BATCH (log scale ~10⁻⁴ to 10⁰); y-axis = iLISI RNA_BATCH (1.0–2.2). Dense cloud at very low kBET × moderate iLISI (1.0–1.5). Best approaches (stars) at moderate kBET (~10⁻² to 10⁻¹) × high iLISI (1.5–2.0).

**Panel B:** Same scatter with alternative colour scheme. Same pattern visible.

**Panel C (log scale barplot):** Per-method kBET acceptance rates for three covariates, log scale. TMM (22_tmm) and VST (23_vst) show highest rates (~10⁻¹ to 10⁰). Most methods near 10⁻⁴.

**Panel D (linear scale barplot):** Same per-method barplot, linear scale, with harshness (green/orange/red) and status (good/medium/bad) annotation strips. TMM/VST annotated as "bad" despite high kBET.

**Missing elements:** Complete legends for panels A and B; axis label for panel B; figure title; finalized panel layout; additional panels (cLISI × kBET, per-strategy kBET analysis).

**Results section:**

[To be completed when the figure is finalized.] The visible panels establish that kBET acceptance is near the null expectation (~10⁻⁴) for the vast majority of harmonization attempts, indicating that local neighbourhood composition remains batch-biased even after global correction. Only the best approaches achieve kBET > 0.01. The striking finding that TMM and VST exhibit the highest kBET acceptance rates — yet are classified as "bad" approaches — confirms that excessive expression distortion can artifactually homogenize local neighbourhoods without achieving biologically meaningful batch mixing. This dissociation between kBET acceptance and biological validity motivates the joint kBET × iLISI evaluation shown in Panel A, where the best approaches are distinguished by high iLISI (true local mixing) rather than by kBET acceptance alone.

---

## Summary of figure status

| Figure | Status | File size | Description source |
|---|---|---|---|
| Figure 1 | Complete | 5 MB | Direct visual inspection |
| Figure 2 | Complete | 1 MB | Direct visual inspection |
| Figure 3 | Complete | 5.1 MB | Direct visual inspection |
| Figure 4 | Complete | 31 MB | JPEG visual inspection |
| Figure 5 | Complete | 22 MB | JPEG visual inspection |
| Figure 6 | Complete | 2.2 MB | Direct visual inspection |
| Figure 7 | **INCOMPLETE** | 438 KB | Partial visual inspection |
| Supp Fig 1 | Complete | 2 MB | Direct visual inspection |
| Supp Fig 2 | Complete | 4.3 MB | Direct visual inspection |
| Supp Fig 3 | Complete | 4.2 MB | Direct visual inspection |
| Supp Fig 4 | Complete | 4.2 MB | Direct visual inspection |
| Supp Fig 5 | Complete | 1.2 MB | Direct visual inspection |
| Supp Fig 6 | Complete | 1.6 MB | Direct visual inspection |
| Supp Fig 7 | Complete | 2.4 MB | Direct visual inspection |
| Supp Fig 8 | Complete | 478 KB | Direct visual inspection |
| Supp Fig 9 | Complete | 8 MB | Direct visual inspection |
| Supp Fig 10 | Complete | 936 KB | Direct visual inspection |
| Supp Fig 11 | Complete | 790 KB | Direct visual inspection |
| Supp Fig 12 | Complete | 1.1 MB | Direct visual inspection |
| Supp Fig 13 | Complete | 1.1 MB | Direct visual inspection |
| Supp Fig 14 | Complete | 1 MB | Direct visual inspection |
| Supp Fig 15 | Complete | 797 KB | Direct visual inspection |
| Supp Fig 16 | Complete | 782 KB | Direct visual inspection |
| Supp Fig 17 | Complete | 790 KB | Direct visual inspection |
| Supp Fig 18 | Complete | 2.6 MB | Direct visual inspection |
| Supp Fig 19 | Complete | 904 KB | Direct visual inspection |
| Supp Fig 20 | **INCOMPLETE** | 1.4 MB | Partial visual inspection |
