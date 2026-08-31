#!/usr/bin/env python
"""Tracked-change edits for `FL_harmonization_article_NAR_260802_manually_edited.docx`.

Third pass (2026-08-02). It carries out the seven inline "Daniil to Claude" instructions
plus the corrections from NAR_review_260802.md.

  #1  Table 3: per-method parameter column, taken from `bench_shared.py`.
  #2  Table 3: per-method harshness justification column, plus explicit criteria in Methods
      and the full bibliographic reference for every method.
  #3  Table 4: new column with the full NAR-format citation for every metric source.
  #4  Methods: random seed and the UMAP / t-SNE parameters, from `compute_batch_metrics.py`.
  #5  The "Harmonization metrics behavior by approaches" section moved to the Extended
      Metrics document: its stub heading is deleted, Figure 9 becomes Figure 6, and the two
      surviving cross-references to the old Figures 6-8 are removed.
  #6  Supplementary tables repackaged from four files to three: former Supplementary File 4
      (polarity) is now sheet `Metric_polarity` of Supplementary File 2.
  #7  Data Availability: one sentence placing the Extended Metrics comparison and its 13
      Extended Figures outside the article and supplementary material.

Plus the review's own corrections — the model-specification error (limma and RUV were run
without a biological covariate), the "1,354 of 2,407" denominator, the Figure 6B response
variable, and the minor language layer.

Safety
------
This manuscript stores all 95 in-text citations as 121 `w:sdt` structured-document tags and
zero `w:fldChar` fields. `word_rewrite_trackchanges.tracked_replace()` rebuilds a paragraph
import os
from its concatenated text and would destroy every one of them, so all prose edits go
through `safe_tracked_replace`, which touches only runs that are direct children of the
paragraph. Table 4's Source column is a merged cell holding a Mendeley citation; it is left
untouched and a new column is appended to its right instead.

Output: FL_harmonization_article_NAR_260802.docx
"""
import re
import sys

import docx
from docx.oxml.ns import qn

sys.path.insert(0, os.path.expanduser("~/FL_harmonization/.claude/skills"))
from nar_review_tools import safe_tracked_replace  # noqa: E402
from word_rewrite_trackchanges import (  # noqa: E402
    delete_paragraph, insert_after, make_run, nid, note_paragraph, set_revision_identity,
    wrap_ins,
)

SRC = "FL_manuscript_versions/FL_harmonization_article_NAR_260802_manually_edited.docx"
DST = "FL_manuscript_versions/FL_harmonization_article_NAR_260802.docx"
AUTHOR, DATE = "Claude (NAR referee report 2026-08-02)", "2026-08-02T00:00:00Z"
set_revision_identity(AUTHOR, DATE)

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


# ═════════════════════════════════════════════════════ Table 3 — new columns ══
# Parameters as actually passed in bench_shared.py. BIO_COL = Diagnosis_cell_type_unified,
# BATCH_COL = RNA_BATCH, the reference batch is RNASeq_FF_PolyA throughout.
METHOD_PARAMS = {
    "01_raw": "None (pass-through baseline)",
    "02_median_scaling": "Per-batch median shifted to the global median; batch = RNA_BATCH",
    "03_limma": "removeBatchEffect(batch = RNA_BATCH); no design matrix and no biological "
                "covariate supplied",
    "04_sva": "mod = model.matrix(~Diagnosis_cell_type_unified), mod0 = model.matrix(~1), "
              "n.sv = num.sv(dat, mod); surrogate variables then removed with "
              "removeBatchEffect(covariates = SVs)",
    "05_combat": "ComBat(batch = RNA_BATCH, mod = model.matrix(~Diagnosis_cell_type_unified)); "
                 "parametric empirical Bayes",
    "06_combat_seq": "ComBat_seq(batch = RNA_BATCH, group = Diagnosis_cell_type_unified)",
    "07_pycombat": "pycombat(batch = RNA_BATCH); the implementation takes no covariate argument",
    "08_inmoose_combatseq": "pycombat_seq(batch = RNA_BATCH, covar_mod = dummy-coded "
                            "Diagnosis_cell_type_unified)",
    "09_ruv": "RUVg(cIdx = 10 housekeeping genes ACTB, GAPDH, B2M, HPRT1, RPL13A, SDHA, UBC, "
              "YWHAZ, HMBS, TBP; k = 2); no biological covariate",
    "10_mnn": "fastMNN(batch = RNA_BATCH, k = 20); corrected embedding back-projected to "
              "expression space",
    "11_harmony": "batch = RNA_BATCH, n_pcs = 50; default clustering parameters",
    "12_scanorama": "batch = RNA_BATCH; default parameters",
    "13_fsmvn": "Reference batch RNASeq_FF_PolyA; per-gene mean and variance matched to the "
                "reference batch",
    "14_qsmooth": "qsmooth(group = RNA_BATCH); default smoothing",
    "15_fsqn_py": "Reference batch RNASeq_FF_PolyA",
    "16_fsqn_r": "Reference batch RNASeq_FF_PolyA; every non-reference batch normalised "
                 "independently, reference samples unchanged",
    "17_quantile": "Per-sample rank-to-mean-quantile mapping over all genes",
    "18_rank": "Per-sample average ranks rescaled to the interval (0, 1)",
    "19_tdm": "Training (reference) batch RNASeq_FF_PolyA",
    "20_shambhala": "Calibration (P) and definitive (Q) references both RNASeq_FF_PolyA; k = 5",
    "21_harmonizr": "algorithm = ComBat, batch = RNA_BATCH; default block splitting",
    "22_tmm": "calcNormFactors(method = 'TMM'); RNA-seq-only strategies",
    "23_vst": "DESeq2 vst, design = ~1; RNA-seq-only strategies",
    "24_peer_k10": "n_factors = 10 (not run)",
    "25_angel": "Platform-variance gene-filter threshold = 0.20; per-sample rank percentiles",
    "26_xpn": "Reference batch RNASeq_FF_PolyA; n_quantiles = 50 piecewise-linear breakpoints",
    "27_dwd": "Reference batch RNASeq_FF_PolyA; min_batch_size = 5; DWDLargeR genDWD solver",
    "28_npn": "Per-batch rank-to-N(0,1) transform; no reference batch",
    "29_combat_ref": "ComBat(batch = RNA_BATCH, mod = model.matrix(~Diagnosis_cell_type_unified), "
                     "ref.batch = RNASeq_FF_PolyA)",
    "30_recombat": "Not run",
    "31_ruv3prps": "RUVIII(k = 5); pseudo-replicates built from Diagnosis_cell_type_unified x "
                   "RNA_BATCH cells with min_cell_size = 2",
    "32_deepmnn": "Not run",
    "33_amdbnorm": "Reference batch RNASeq_FF_PolyA; degree-9 polynomial fit of each batch to "
                   "the reference distribution",
    "34_arsyn": "ARSyN(Batch = RNA_BATCH, Condition = Diagnosis_cell_type_unified); default "
                "number of factors",
    "35_dasc": "Not run",
    "36_explobatch": "method = 'ppcca', scale = 'unit', SDselect = 0, maxdim = 9",
    "37_fabatch": "Not run",
    "38_harman": "harman(expt = Diagnosis_cell_type_unified, batch = RNA_BATCH, limit = 0.1)",
    "39_procrustes": "Not run",
}

# Why each method sits in its harshness tier, against the criteria now stated in Methods.
METHOD_HARSHNESS_WHY = {
    "01_raw": "No transformation at all",
    "02_median_scaling": "Additive per-batch shift; gene ranks within a sample unchanged",
    "03_limma": "Linear model residuals; additive, rank-preserving within a sample",
    "04_sva": "Linear removal of a small number of estimated latent factors; distribution shape "
              "preserved",
    "05_combat": "Location-and-scale adjustment with empirical-Bayes shrinkage; per-gene "
                 "variance rescaled",
    "06_combat_seq": "Negative-binomial quantile mapping of counts; per-gene distribution "
                     "re-fitted",
    "07_pycombat": "Same location-and-scale model as ComBat",
    "08_inmoose_combatseq": "Same count-level model as ComBat-seq",
    "09_ruv": "Removal of k factors estimated on control genes; linear but data-adaptive",
    "10_mnn": "Local, neighbour-dependent offsets; global distribution largely preserved",
    "11_harmony": "Iterative soft-clustered linear correction in PC space",
    "12_scanorama": "Panorama-stitched local correction in a reduced space",
    "13_fsmvn": "Per-gene mean and variance forced to a reference batch; shape preserved",
    "14_qsmooth": "Per-gene quantile function replaced by a smoothed reference",
    "15_fsqn_py": "Per-gene quantiles replaced by the reference batch quantiles",
    "16_fsqn_r": "Per-gene quantiles replaced by the reference batch quantiles",
    "17_quantile": "Every sample forced onto one common quantile function",
    "18_rank": "Expression values discarded and replaced by ranks",
    "19_tdm": "Distribution matched to a training reference across the whole matrix",
    "20_shambhala": "Quantile normalization on top of a CuBlock re-projection; both shape and "
                    "dimensionality altered",
    "21_harmonizr": "ComBat applied blockwise after matrix dissection; distribution locally "
                    "re-fitted",
    "22_tmm": "Single scaling factor per sample",
    "23_vst": "Monotone variance-stabilizing transform; ranks preserved",
    "24_peer_k10": "Linear removal of k latent factors (not run)",
    "25_angel": "Values replaced by rank percentiles after gene filtering",
    "26_xpn": "Piecewise-linear quantile matching per gene",
    "27_dwd": "Projection along a single discriminant direction; linear",
    "28_npn": "Values replaced by a rank-derived Gaussian score",
    "29_combat_ref": "ComBat location-and-scale anchored to a reference batch",
    "30_recombat": "Ridge-regularized ComBat (not run)",
    "31_ruv3prps": "Removal of k factors using pseudo-replicates; linear",
    "32_deepmnn": "Neural-network-augmented local correction (not run)",
    "33_amdbnorm": "Whole distribution re-fitted by a degree-9 polynomial",
    "34_arsyn": "ANOVA-ASCA residual removal; linear",
    "35_dasc": "Semi-NMF batch detection (not run)",
    "36_explobatch": "PPCCA re-projection; dimensionality altered",
    "37_fabatch": "Location-and-scale plus latent-factor adjustment (not run)",
    "38_harman": "PC-space shift bounded by an overcorrection probability; linear",
    "39_procrustes": "Per-gene linear rescaling with fixed coefficients (not run)",
}

# Reference numbers refer to the manuscript's own Mendeley bibliography; the two methods that
# have no entry there are given in full so they can be added.
METHOD_REFS = {
    "01_raw": "-", "02_median_scaling": "(20)", "03_limma": "(21)", "04_sva": "(22)",
    "05_combat": "(23)", "06_combat_seq": "(24)", "07_pycombat": "(25)",
    "08_inmoose_combatseq": "(26)", "09_ruv": "(27)", "10_mnn": "(28)", "11_harmony": "(29)",
    "12_scanorama": "(30)", "13_fsmvn": "(31)", "14_qsmooth": "(32)", "15_fsqn_py": "(33)",
    "16_fsqn_r": "(33)", "17_quantile": "(34)", "18_rank": "(35)", "19_tdm": "(36)",
    "20_shambhala": "(37)", "21_harmonizr": "(38)", "22_tmm": "(39)", "23_vst": "(40)",
    "24_peer_k10": "(41)", "25_angel": "(42)", "26_xpn": "(43)", "27_dwd": "(44)",
    "28_npn": "Liu,H., Lafferty,J. and Wasserman,L. (2009) The nonparanormal: semiparametric "
              "estimation of high dimensional undirected graphs. J. Mach. Learn. Res., 10, "
              "2295-2328. [not yet in the reference list]",
    "29_combat_ref": "(46)", "30_recombat": "(47)", "31_ruv3prps": "(48)", "32_deepmnn": "(49)",
    "33_amdbnorm": "(50)", "34_arsyn": "(51)", "35_dasc": "(52)", "36_explobatch": "(53)",
    "37_fabatch": "(54)", "38_harman": "(55)",
    "39_procrustes": "Kotlov,N. et al. (2024) Procrustes is a machine-learning approach that "
                     "removes cross-platform batch effects from clinical RNA sequencing data. "
                     "Commun. Biol., 7, 289. [not yet in the reference list]",
}

# ═════════════════════════════════════════════════════ Table 4 — new column ═══
# Full NAR-format citations, copied verbatim from the manuscript's own bibliography so that
# the table and the reference list cannot drift apart.
METRIC_CITATIONS = {
    "PCA R2":
        "Luecken,M.D., Buettner,M., Chaichoompu,K., Danese,A., Interlandi,M., Mueller,M.F., "
        "Strobl,D.C., Zappia,L., Dugas,M., Colome-Tatche,M., et al. (2021) Benchmarking "
        "atlas-level data integration in single-cell genomics. Nat. Methods, 19, 41-50.",
    "Percentage variance":
        "Zhang,N., Casasent,T.D., Casasent,A.K., Kumar,S.V., Wakefield,C., Broom,B.M., "
        "Weinstein,J.N. and Akbani,R. (2024) PCA-Plus: enhanced principal component analysis "
        "with illustrative applications to batch effects and their quantitation. "
        "[reference list entry 58]",
    "Principal component regression (PCReg)":
        "Luecken,M.D., et al. (2021) Benchmarking atlas-level data integration in single-cell "
        "genomics. Nat. Methods, 19, 41-50. [reference list entry 57]",
    "Dispersion separability criterion (DSC)":
        "Zhang,N., et al. (2024) PCA-Plus: enhanced principal component analysis with "
        "illustrative applications to batch effects and their quantitation. "
        "[reference list entry 58]",
    "kBET acceptance rate":
        "Buettner,M., Miao,Z., Wolf,F.A., Teichmann,S.A. and Theis,F.J. (2019) A test metric "
        "for assessing single-cell RNA-seq batch correction. Nat. Methods, 16, 43-49. "
        "[reference list entry 59]",
    "Local inverse Simpson's index (LISI)":
        "Korsunsky,I., Millard,N., Fan,J., Slowikowski,K., Zhang,F., Wei,K., Baglaenko,Y., "
        "Brenner,M., Loh,P. and Raychaudhuri,S. (2019) Fast, sensitive and accurate integration "
        "of single-cell data with Harmony. Nat. Methods, 16, 1289-1296. "
        "[reference list entry 29]",
    "Average silhouette width (ASW)":
        "Rousseeuw,P.J. (1987) Silhouettes: a graphical aid to the interpretation and validation "
        "of cluster analysis. J. Comput. Appl. Math., 20, 53-65. [reference list entry 60]",
    "Cell-specific mixing score (CMS)":
        "Luetge,A., Zyprych-Walczak,J., Kunzmann,U.B., Crowell,H.L., Calini,D., Malhotra,D., "
        "Soneson,C. and Robinson,M.D. (2021) CellMixS: quantifying and visualizing batch effects "
        "in single-cell RNA-seq data. Life Sci. Alliance, 4, e202001004. "
        "[reference list entry 61]",
    "Centroid dispersion in UMAP and tSNE":
        "This study (custom implementation); embedding-based batch-effect assessment after "
        "Tung,P.Y., et al. (2017) Batch effects and the effective design of single-cell gene "
        "expression studies. Sci. Rep., 7, 39921. [reference list entry 63]",
    "Local neighborhood entropy in UMAP and tSNE":
        "This study (custom implementation); neighbourhood-entropy formulation after "
        "Keyes,T.J., Domizi,P., Lo,Y.C., Nolan,G.P. and Davis,K.L. (2020) A cancer biologist's "
        "primer on machine learning applications in high-dimensional cytometry. Cytometry A, 97, "
        "782-799. [reference list entry 62]",
    "KS test mean gene-level D-statistic":
        "This study (custom implementation); two-sample Kolmogorov-Smirnov statistic.",
    "Within-batch cohort-level D-statistic":
        "This study (custom implementation); two-sample Kolmogorov-Smirnov statistic.",
    "Per-gene batch mean CV":
        "Tung,P.Y., Blischak,J.D., Hsiao,C.J., Knowles,D.A., Burnett,J.E., Pritchard,J.K. and "
        "Gilad,Y. (2017) Batch effects and the effective design of single-cell gene expression "
        "studies. Sci. Rep., 7, 39921. [reference list entry 63]",
    "Zero expression fraction":
        "Zyla,J., Papiez,A., Zhao,J., Qu,R., Li,X., Kluger,Y., Polanska,J., Hatzis,C., "
        "Pusztai,L. and Marczyk,M. (2023) Evaluation of zero counts to better understand the "
        "discrepancies between bulk and single-cell RNA-seq platforms. Comput. Struct. "
        "Biotechnol. J., 21, 4663-4674. [reference list entry 64]",
    "Fraction cohorts bimodal":
        "Knapp,T.R. (2007) Bimodality revisited. J. Mod. Appl. Stat. Methods, 6, 8-20. "
        "[reference list entry 65]",
    "Graph connectivity":
        "Luecken,M.D., et al. (2021) Benchmarking atlas-level data integration in single-cell "
        "genomics. Nat. Methods, 19, 41-50. [reference list entry 57]",
    "Average pairwise Euclidean distance":
        "Liu,Y. and Yang,C. (2024) Computational methods for alignment and integration of "
        "spatially resolved transcriptomics data. Comput. Struct. Biotechnol. J., 23, 1094-1105. "
        "[reference list entry 66]",
    "Watermelon score":
        "Zolotovskaia,M.A., Sorokin,M.I., Petrov,I.V., Poddubskaya,E.V., Moiseev,A.A., "
        "Sekacheva,M.I., Borisov,N.M., Tkachev,V.S., Garazha,A.V., Kaprin,A.D., et al. (2020) "
        "Disparity between inter-patient molecular heterogeneity and repertoires of target drugs "
        "and biomarkers of oncological diseases. [reference list entry 67]",
    "Genes and samples with NA":
        "This study (custom implementation).",
}


# ═══════════════════════════════════════════════════════ prose edits ══════════
# (anchor substring that uniquely identifies the paragraph, [(old, new), ...])

MODEL_SPEC = (
    "For SVA, limma removeBatchEffect, ComBat, ComBat-seq, M-ComBat and RUV we selected the "
    "annotation column ‘Diagnosis_cell_type_unified’ as the biology covariate to protect its "
    "variance in the gene expression space."
)
MODEL_SPEC_NEW = (
    "For SVA, ComBat, ComBat-seq, M-ComBat, InMoose ComBat-seq, ARSyN and Harman we supplied "
    "the annotation column ‘Diagnosis_cell_type_unified’ as the biology covariate in the model "
    "matrix, to protect its variance in the gene expression space. limma removeBatchEffect was "
    "run with the batch vector only and no design matrix, and RUV was run on ten housekeeping "
    "control genes with k = 2 and no biological covariate; neither implementation therefore "
    "protected the biology term. The parameters actually passed to every method are listed in "
    "Table 3."
)

HARSHNESS_OLD = (
    "Each implemented method was manually assigned a qualitative harshness score (low, medium, "
    "or high) reflecting the degree of data transformation imposed: low-harshness methods apply "
    "linear transformations (e.g., median scaling); high-harshness methods alter data "
    "distributions or dimensionality (e.g., quantile normalization, rank transformation); "
    "medium-harshness methods transform data to an intermediate degree."
)
HARSHNESS_NEW = (
    "Each implemented method was assigned a qualitative harshness score (low, medium or high) "
    "by the first author, from the published description of the algorithm and its source code, "
    "before any benchmark result was seen. The criteria were applied in the following order. "
    "Low: the method applies an additive or otherwise monotone transformation that leaves the "
    "rank order of genes within a sample unchanged (median scaling, limma, TMM, variance "
    "stabilization, SVA). Medium: the method estimates a model or a small number of latent "
    "factors from the data and subtracts their contribution, or applies local neighbour-"
    "dependent offsets, so that the shape of the per-sample expression distribution is largely "
    "preserved (ComBat and its variants, RUV, MNN, Harmony, Scanorama, DWD, Harman). High: the "
    "method rewrites the per-gene or per-sample quantile function, replaces expression values "
    "by ranks, or changes the dimensionality of the data (quantile normalization, FSQN, rank "
    "normalization, TDM, NPN, AMDBNorm, exploBATCH, Shambhala-2). The tier assigned to each "
    "method and the reason for it are given in Table 3."
)

SEEDS_NEW = (
    " All stochastic steps used a fixed random seed of 42. Principal component analysis was "
    "computed on standardized expression values; UMAP embeddings used n_neighbors = 30, "
    "min_dist = 0.3, two components and the Euclidean metric; t-SNE embeddings used "
    "perplexity = min(30, n_samples / 4), two components and the Barnes-Hut approximation, both "
    "computed on the principal component coordinates. The 1,000 genes sampled for the "
    "Kolmogorov-Smirnov metrics were drawn once with the same seed and reused for every "
    "approach."
)

PROSE_EDITS = [
    # ── #4 and the model-specification correction ──────────────────────────────
    ("After the rejection, we identified 39 harmonization methods potentially applicable",
     [("We used all the methods with default parameters, in order to avoid further inflation of "
       "the ComboBatch pipeline combinatorial space.",
       "Except where Table 3 states otherwise, we used the methods with their default "
       "parameters, to avoid further inflation of the ComboBatch pipeline combinatorial space."),
      (MODEL_SPEC, MODEL_SPEC_NEW)]),

    ("Each implemented method was manually assigned a qualitative harshness score",
     [(HARSHNESS_OLD, HARSHNESS_NEW)]),

    ("Harmonization quality metrics were computed and statistically analyzed using the scipy",
     [("The code for harmonization metrics calculation can be found via the link",
       SEEDS_NEW.strip() + " The code for harmonization metrics calculation can be found via "
       "the link")]),

    # ── #5 the moved section ───────────────────────────────────────────────────
    ("the second poorest one and the worst by global and local metrics as revealed previously",
     [(" and the worst by global and local metrics as revealed previously in Figures 6 and 7",
       " and the worst by global and local metrics")]),

    # ── review corrections ─────────────────────────────────────────────────────
    ("It should be noted that the composite score is comparable only between the methods",
     [("only 1,354 of 2,407 approaches have all the 87 scoring metrics",
       "only 1,354 of the 2,234 approaches (60.6%) have all the 87 scoring metrics")]),

    ("To quantify the relative contribution of each experimental factor to overall harmonization",
     [("we computed the mean R² effect size of each factor across the 87 scoring metrics in the "
       "2234 successful approaches",
       "we computed the R² effect size of each factor separately for each of the 87 scoring "
       "metrics across the 2,234 successful approaches and averaged it over the metrics"),
      ("Harmonization method emerged as the dominant factor, explaining 36.3% of variance in "
       "composite harmonization quality",
       "Harmonization method emerged as the dominant factor, explaining on average 36.3% of the "
       "variance of a single quality metric")]),

    # ── #6 supplementary table nomenclature ────────────────────────────────────
    ("For 87 of the 229 computed metrics, we manually assigned polarity values",
     [("Polarity assignments for all the 229 metrics are listed in Supplementary File 4.",
       "Polarity assignments for all the 229 metrics are listed in Supplementary File 2, sheet "
       "‘Metric_polarity’; the metric names there match the column names of Supplementary "
       "File 3 exactly.")]),

    ("Supplementary File 2. Number of genes with defined gene expression by sample",
     [("Supplementary File 2. Number of genes with defined gene expression by sample in the "
       "initial dataset prior to imputation.",
       "Supplementary File 2. Excel workbook with two sheets: ‘Genes_per_sample’, the number of "
       "genes with defined gene expression for each of the 7,174 samples in the initial dataset "
       "prior to imputation; and ‘Metric_polarity’, the polarity coefficients of the 229 "
       "harmonization quality metrics used in this study.")]),

    ("Supplementary File 4. Polarity coefficients by the 229 harmonization quality metrics",
     [("Supplementary File 4. Polarity coefficients by the 229 harmonization quality metrics "
       "used in this study.", "")]),

    ("Supplementary File 3. Values of the 87 scoring metrics",
     [("Values of the 87 scoring metrics for the 2,407 harmonization approaches computed in "
       "this study.",
       "Values of the 87 scoring metrics for the 2,407 harmonization approaches computed in "
       "this study; the 2,234 approaches used in the analysis are those with "
       "pct_samples_allNA < 5.")]),

    # ── minor language and numbers ─────────────────────────────────────────────
    ("we identified eight best-performing harmonization approach groups",
     [("(15 indiviual approaches, Table 5)", "(15 individual approaches, Table 5)")]),

    ("We also acknowledge additional mathematical limitations of the ComboBatch pipeline",
     [("First, lbeit the composite score", "First, albeit the composite score"),
      ("Second, fix of the 33 implemented methods", "Second, six of the 33 implemented methods")]),

    ("Methods that dominated earlier harmonization benchmarks designed on TCGA or GTEx data",
     [("batch effects are typically 2–5 smaller in variance explained",
       "batch effects are typically 2–5-fold smaller in variance explained")]),

    ("missForest was excluded from the benchmark after exceeding 48 hours",
     [("on a 32-48-core, 240 GiB RAM server", "on a 32–48-core, 240 GiB RAM server")]),

    ("These methods were both the best performing ones by metrics",
     [("t-distributed stochastic neighbor embedding (tSNE) and uniform manifold approximation "
       "and projection (UMAP) space",
       "t-distributed stochastic neighbor embedding (tSNE) and uniform manifold approximation "
       "and projection (UMAP) space")]),
]

# Table-cell edits: (table index, row index, column index, [(old, new), ...])
CELL_EDITS = [
    (3, 19, 3, [("Sparsity metrics: umber and percentage", "Sparsity metrics: number and "
                                                           "percentage")]),
    (1, 3, 0, [("Output is not a corrected expression matrix - its embedding, probability, "
                "categorical, or score.",
                "Output is not a corrected expression matrix — it is an embedding, a "
                "probability, a category, or a score.")]),
    (1, 4, 2, [("RUV-2, BMC, Z-scaling,", "RUV-2, BMC, Z-scaling")]),
]

# Data Availability sentence for instruction #7.
EXTENDED_SENTENCE = (
    "The extended comparison of harmonization quality metrics, together with its 13 Extended "
    "Figures, is deposited with the pipeline code rather than as supplementary material of this "
    "article, and is therefore linked from the article but is not part of the main or "
    "supplementary files."
)


# ═════════════════════════════════════════════════════════ helpers ════════════
def visible(el):
    """Text as Word displays it: original plus insertions, deletions excluded."""
    return "".join(t.text or "" for t in el.findall(f".//{W}t"))


def find_p(body, needle, skip_notes=True):
    hits = []
    for p in body.iter(f"{W}p"):
        txt = visible(p)
        if needle not in txt:
            continue
        if skip_notes and ("[REVIEWER NOTE]" in txt or "[NAR EDITOR NOTE]" in txt):
            continue
        hits.append(p)
    if len(hits) != 1:
        raise SystemExit(f"anchor matched {len(hits)} paragraphs: {needle[:70]!r}")
    return hits[0]


def append_tracked_column(tbl, header, values):
    """Append one column to a table as a tracked insertion.

    Adds a `w:gridCol` and one `w:tc` per row. Each new cell is marked `w:cellIns` and its
    text is wrapped in `w:ins`, so Accept All keeps the column and Reject All empties it and
    drops the cell. Rows whose last cell is horizontally merged (as in Table 4, where the
    definition spans the Source column) still receive exactly one trailing cell.
    """
    grid = tbl.find(qn("w:tblGrid"))
    gc = grid.makeelement(qn("w:gridCol"), {})
    gc.set(qn("w:w"), "2400")
    grid.append(gc)

    rows = tbl.findall(qn("w:tr"))
    texts = [header] + list(values)
    if len(texts) != len(rows):
        raise SystemExit(f"column length {len(texts)} != {len(rows)} rows")

    for tr, text in zip(rows, texts):
        model = tr.findall(qn("w:tc"))[-1]
        tc = tr.makeelement(qn("w:tc"), {})
        tc_pr = tc.makeelement(qn("w:tcPr"), {})
        tc_w = tc_pr.makeelement(qn("w:tcW"), {})
        tc_w.set(qn("w:w"), "2400")
        tc_w.set(qn("w:type"), "dxa")
        tc_pr.append(tc_w)
        cell_ins = tc_pr.makeelement(qn("w:cellIns"), {})
        cell_ins.set(qn("w:id"), str(nid()))
        cell_ins.set(qn("w:author"), AUTHOR)
        cell_ins.set(qn("w:date"), DATE)
        tc_pr.append(cell_ins)
        tc.append(tc_pr)

        p = tc.makeelement(qn("w:p"), {})
        # Copy the model cell's paragraph properties so the new column matches the table style.
        model_p = model.find(qn("w:p"))
        if model_p is not None:
            model_ppr = model_p.find(qn("w:pPr"))
            if model_ppr is not None:
                import copy
                p.append(copy.deepcopy(model_ppr))
        p.append(wrap_ins(make_run(text)))
        tc.append(p)
        tr.append(tc)


def main():
    doc = docx.Document(SRC)
    body = doc.element.body
    tables = doc.tables

    report = {"ok": 0, "not-found": 0, "unsafe": 0}

    def apply(p, pairs, tag):
        for old, status in safe_tracked_replace(p, pairs):
            report[status] += 1
            if status != "ok":
                print(f"  [{status}] {tag}: {old[:90]!r}")

    # 1 ── prose edits. Resolve every anchor to an element reference BEFORE mutating
    #      anything: after an edit the original wording lives in w:delText, which a
    #      .//w:t search no longer sees, so a later anchor lookup would fail.
    resolved = [(find_p(body, a), pairs, a) for a, pairs in PROSE_EDITS]
    for p, pairs, anchor in resolved:
        apply(p, pairs, anchor[:45])

    # 2 ── table-cell edits
    for ti, ri, ci, pairs in CELL_EDITS:
        cell = tables[ti].rows[ri].cells[ci]
        for para in cell._tc.findall(qn("w:p")):
            if any(o in visible(para) for o, _ in pairs):
                apply(para, pairs, f"T{ti}r{ri}c{ci}")
                break
        else:
            print(f"  [not-found] cell T{ti}r{ri}c{ci}")
            report["not-found"] += 1

    # 3 ── Figure 9 -> Figure 6 throughout (the metrics section moved out, so the old
    #      Figures 6-8 no longer exist and Figure 9 is now the sixth main figure).
    n_fig = 0
    for p in body.iter(f"{W}p"):
        txt = visible(p)
        if "Figure 9" not in txt:
            continue
        # Reviewer notes quote the old wording on purpose; leave them alone so their
        # anchors still resolve and so the note keeps naming the figure the author saw.
        if "[REVIEWER NOTE]" in txt or "[NAR EDITOR NOTE]" in txt:
            continue
        pairs = [("Figure 9", "Figure 6")] * len(re.findall(r"Figure 9", txt))
        apply(p, pairs, "fig9->6")
        n_fig += len(pairs)

    # 4 ── new table columns (instructions #1, #2, #3)
    t3 = tables[2]._tbl
    order = [tables[2].rows[i].cells[0].text.strip() for i in range(1, len(tables[2].rows))]
    append_tracked_column(t3, "Parameters used",
                          [METHOD_PARAMS.get(m, "") for m in order])
    append_tracked_column(t3, "Harshness justification",
                          [METHOD_HARSHNESS_WHY.get(m, "") for m in order])
    print(f"  Table 3: two columns added for {len(order)} methods; "
          f"unmatched: {[m for m in order if m not in METHOD_PARAMS]}")

    t4 = tables[3]._tbl
    metrics = [tables[3].rows[i].cells[0].text.strip() for i in range(1, len(tables[3].rows))]
    append_tracked_column(t4, "Full citation",
                          [METRIC_CITATIONS.get(m, "") for m in metrics])
    print(f"  Table 4: citation column added for {len(metrics)} metrics; "
          f"unmatched: {[m for m in metrics if m not in METRIC_CITATIONS]}")

    # 5 ── Table 3's own "Reference" column cannot be filled in place: in 34 of the 39 rows
    #      the Version cell is horizontally merged across it, so those rows have no Reference
    #      cell to write into. A separate citation column is appended instead.
    append_tracked_column(t3, "Reference (citation)",
                          [METHOD_REFS.get(m, "") for m in order])
    print(f"  Table 3: citation column added for {len(order)} methods")

    # 5b ── delete the stub left behind by the moved metrics section (instruction #5):
    #       its now-empty Heading 2 and the instruction paragraph itself.
    for anchor in ("Harmonization metrics behavior by approaches",
                   "I moved this entire section to the Extended Metrics comparison document"):
        delete_paragraph(find_p(body, anchor, skip_notes=False))
    print("  moved-section stub: 2 paragraphs deleted")

    # 6 ── Data Availability sentence (instruction #7)
    da = find_p(body, "Extended comparison of harmonization quality metrics by batch removal")
    insert_after(da, [
        docx.oxml.parse_xml(
            '<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
        )
    ])
    new_p = da.getnext()
    new_p.append(wrap_ins(make_run(EXTENDED_SENTENCE)))

    # 7 ── mark the four resolved reviewer notes and record what is left for the author.
    NOTES = [
        ("“default parameters” does not determine the behaviour",
         "RESOLVED 2026-08-02. Table 3 now carries a ‘Parameters used’ column giving the exact "
         "call made for every method, taken from bench_shared.py, and the Methods text has been "
         "corrected: limma removeBatchEffect and RUV were run WITHOUT a biological covariate. "
         "This reviewer note can be deleted."),
        ("Figure 9A tests a hypothesis about harshness",
         "RESOLVED 2026-08-02. The harshness criteria are now stated explicitly in Methods, with "
         "the assigner and the fact that the assignment preceded the results; Table 3 carries a "
         "‘Harshness justification’ column and a filled Reference column. This reviewer note can "
         "be deleted."),
        ("Please add here: the random seed and the UMAP/t-SNE parameters",
         "RESOLVED 2026-08-02. Seed 42 and the UMAP / t-SNE parameters are now stated in this "
         "paragraph, taken from compute_batch_metrics.py. Run-to-run replication of the 14 "
         "embedding-space metrics is still absent and remains a recommendation. This reviewer "
         "note can be deleted."),
        ("SUPPLEMENTARY MATERIAL DOES NOT MEET NAR'S LIMITS",
         "PARTLY RESOLVED 2026-08-02. supplementary_260802/ holds ten files: Supplementary "
         "Files 1 and 3 unchanged, a new Supplementary File 2 workbook combining the former "
         "Files 2 and 4, and seven titled and bookmarked PDF bundles covering Supplementary "
         "Figures 1-17 with their numbering unchanged. Former Supplementary File 2 was "
         "deduplicated and restricted to the 7,174 annotated samples (it held 7,238 rows), and "
         "the polarity sheet was renamed pcr_* to PCReg_* so that all 87 scoring metrics resolve "
         "against Supplementary File 3. The bundles are 1.31-3.89 MB: 19.2 MB of vector artwork "
         "cannot fit seven files of 1.5 MB, so a single combined 17-page PDF has also been "
         "produced and is the recommended submission route. Alt text for the supplementary "
         "figures and the graphical abstract is still missing."),
    ]
    resolved_notes = [(find_p(body, a, skip_notes=False), t) for a, t in NOTES]
    for p, text in resolved_notes:
        insert_after(p, [note_paragraph(text, label="[REVIEWER NOTE] ")])

    print(f"\nfigure references renumbered: {n_fig}")
    print(f"ok {report['ok']} | not-found {report['not-found']} | unsafe {report['unsafe']}")
    doc.save(DST)
    print(f"wrote {DST}")


if __name__ == "__main__":
    main()
