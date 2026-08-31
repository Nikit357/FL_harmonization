#!/usr/bin/env python
"""Add a 'Linear' (+ justification) column to Table_S1_methods in Supplementary File 2.xlsx.

Classification is grounded in the actual `normalize_*` implementation in
`harmonization-scripts/bench_shared.py` for the 33 methods marked "Yes" in
`Implementation done`, and in the method's published definition (the algorithm this
pipeline intends to call, per bench_shared.py's docstring/citation) for the 6 methods
marked "No". The rule applied throughout: classify by the functional form of the
*final applied correction* to the expression matrix (is a sample's corrected value an
affine function of its raw value, for a fixed batch/gene?), not by whether parameter
*estimation* used an iterative or non-linear procedure (e.g. ComBat's empirical-Bayes
shrinkage and SVA's surrogate-variable estimation are both non-linear estimation
steps feeding into a final linear/affine correction, so both count as Linear here).

Usage:
    source ~/venvs/collagen_3_11/bin/activate
    python figure_drawing_scripts/add_linearity_column_260825.py
"""

import os
import copy
import openpyxl

PATH = os.path.expanduser("~/FL_harmonization/figures_for_article/supplementary_260824/Supplementary File 2.xlsx")

# method_name -> (Linear / Non-linear / N/A, justification)
LINEARITY = {
    "01_raw": ("Linear", "Identity map — no transform is applied."),
    "02_median_scaling": (
        "Linear",
        "Adds a fixed per-gene shift (global median − batch median) to every sample in "
        "the batch — an affine, location-only correction.",
    ),
    "03_limma": (
        "Linear",
        "`removeBatchEffect` fits and subtracts a linear-model batch term; the "
        "correction is an affine function of the raw value for fixed batch/gene.",
    ),
    "04_sva": (
        "Linear",
        "Surrogate variables are estimated by an iterative procedure, but the applied "
        "correction is `limma::removeBatchEffect` regressing them out — an affine "
        "adjustment, as in 03_limma.",
    ),
    "05_combat": (
        "Linear",
        "Empirical-Bayes location-and-scale adjustment: x' = (x − batch mean)/batch sd × "
        "pooled sd + pooled mean, with EB-shrunk parameters. The shrinkage is a non-linear "
        "estimation step, but the applied transform is affine per gene/batch.",
    ),
    "06_combat_seq": (
        "Non-linear",
        "Fits a negative-binomial GLM per gene and remaps counts by quantile-matching "
        "between the fitted batch and reference NB distributions — not an affine map.",
    ),
    "07_pycombat": ("Linear", "Same empirical-Bayes location-scale model as 05_combat, ported to Python."),
    "08_inmoose_combatseq": (
        "Non-linear",
        "Same NB-GLM quantile-matching algorithm as 06_combat_seq (InMoose is a Python "
        "port of ComBat-seq).",
    ),
    "09_ruv": (
        "Linear",
        "RUVg subtracts a low-rank factor reconstruction (W·α, estimated from control "
        "genes) from the data — an affine correction once the factors are estimated.",
    ),
    "10_mnn": (
        "Non-linear",
        "fastMNN computes per-cell correction vectors from mutual-nearest-neighbour pairs "
        "with Gaussian-kernel smoothing in PCA space; the correction a sample receives is "
        "a non-linear function of every other sample's local neighbourhood, not a fixed "
        "affine coefficient (the final PCA→gene-space step is linear, but the correction "
        "computed in PCA space is not).",
    ),
    "11_harmony": (
        "Non-linear",
        "Iterative soft k-means clustering in PCA space followed by a cluster-weighted "
        "correction; the correction depends non-linearly on each cell's soft cluster "
        "assignment, which is itself the output of a non-linear optimization.",
    ),
    "12_scanorama": (
        "Non-linear",
        "Panoramic stitching via randomized-SVD mutual-nearest-neighbour matching between "
        "batch pairs in PCA space — the same MNN family as 10_mnn.",
    ),
    "13_fsmvn": (
        "Linear",
        "Per-gene, per-batch Z-score — (x − batch mean)/batch sd — rescaled to a "
        "reference batch's mean/sd: an affine transform, and the pipeline's explicit "
        "'negative control' baseline for simple standardization.",
    ),
    "14_qsmooth": ("Non-linear", "Quantile normalization smoothly blended with the raw distribution — rank-based, not affine."),
    "15_fsqn_py": ("Non-linear", "Feature-specific quantile normalization: each sample's values are reordered onto a target rank-sorted distribution."),
    "16_fsqn_r": ("Non-linear", "Same feature-specific quantile-normalization algorithm as 15_fsqn_py, via the original R package."),
    "17_quantile": ("Non-linear", "Classic quantile normalization forces every sample onto the same rank-sorted reference distribution."),
    "18_rank": ("Non-linear", "Per-sample rank transform — explicitly non-linear by construction."),
    "19_tdm": ("Non-linear", "Training Distribution Matching maps each sample's empirical distribution onto the reference batch's, a non-linear (non-affine) distributional mapping."),
    "20_shambhala": ("Non-linear", "CuBlock (a non-linear cross-platform mapping) followed by quantile normalization."),
    "21_harmonizr": ("Linear", "NA-aware blockwise wrapper that dispatches to ComBat (default) or limma internally — same affine family as 05/03."),
    "22_tmm": (
        "Linear",
        "edgeR's trimmed-mean-of-M-values computes one multiplicative scaling factor per "
        "sample (applied identically to every gene) — a linear (purely multiplicative) "
        "rescaling, though the factor is per-sample rather than per-gene.",
    ),
    "23_vst": ("Non-linear", "DESeq2's variance-stabilizing transformation is explicitly a non-linear function of the fitted mean-dispersion relationship."),
    "24_peer_k10": ("Linear", "PEER removes latent factors via linear regression, the same family as SVA/RUV — not implemented in this pipeline (package unobtainable for R 4.5)."),
    "25_angel": ("Non-linear", "Rank-percentile transform per sample, then platform-variance gene filtering — rank-based, not affine."),
    "26_xpn": ("Non-linear", "Per-gene piecewise-linear interpolation onto the reference batch's quantiles; each gene gets its own data-dependent curve, so the overall map is a non-linear (piecewise) quantile-matching transform, not a single affine map."),
    "27_dwd": (
        "Linear",
        "Finds a DWD separating hyperplane direction w between batch and reference, then "
        "adds a fixed multiple of w to every sample in the batch (`X_batch + shift * w`) "
        "— an affine translation.",
    ),
    "28_npn": ("Non-linear", "Per-batch rank-to-Gaussian transform, Φ⁻¹(rank/(n+1)) — a probit-of-rank map, non-linear by construction."),
    "29_combat_ref": ("Linear", "Same empirical-Bayes location-scale ComBat model as 05_combat, anchored to a reference batch instead of the global mean."),
    "30_recombat": ("Linear", "Ridge-regularized ComBat: regularization changes how the location/scale coefficients are estimated, not the affine form of the applied correction — not implemented in this pipeline (package never provisioned on the pod)."),
    "31_ruv3prps": ("Linear", "RUV-III subtracts an estimated low-rank unwanted-variation factor via linear algebra on pseudo-replicate-augmented data — same affine family as 09_ruv."),
    "32_deepmnn": ("Non-linear", "Deep-neural-network-augmented MNN correction — not implemented in this pipeline (scRNA-seq-only interface, incompatible with bulk data)."),
    "33_amdbnorm": ("Non-linear", "Corrects each batch using a degree-9 polynomial fit to the reference batch's distribution — explicitly non-linear."),
    "34_arsyn": ("Linear", "ANOVA-ASCA decomposes expression into biology + batch + residual and subtracts the batch PCA component — a linear-model decomposition and linear subtraction."),
    "35_dasc": ("N/A", "A batch-detection/classification tool (semi-NMF cluster assignment), not a corrected-expression-matrix method — linearity does not apply. Not implemented in this pipeline (architecturally incompatible interface)."),
    "36_explobatch": ("Linear", "Probabilistic PCA with covariates (PPCCA) is a linear latent-variable model; the batch component it estimates is subtracted linearly."),
    "37_fabatch": ("Linear", "bapred::fabatch() combines ComBat-style location/scale adjustment with a linear factor-model correction — not implemented in this pipeline (bapred/cmake never provisioned on the pod)."),
    "38_harman": ("Linear", "PCA-based correction that shifts samples along principal-component directions under an overcorrection-probability bound — a linear (PCA-space) correction."),
    "39_procrustes": ("Linear", "Applies pre-fitted per-gene linear coefficients (slope + intercept) to convert exome-capture batches to polyA-equivalent expression — explicitly linear by construction and by name."),
}

wb = openpyxl.load_workbook(PATH)
ws = wb["Table_S1_methods"]

header_font = copy.copy(ws["A1"].font)
data_font = copy.copy(ws["A2"].font)
data_align = copy.copy(ws["A2"].alignment)

ws.cell(row=1, column=10, value="Linear").font = header_font
ws.cell(row=1, column=11, value="Linearity justification").font = header_font

unresolved = []
for r in range(2, ws.max_row + 1):
    name = ws.cell(row=r, column=1).value
    if name not in LINEARITY:
        unresolved.append(name)
        continue
    linear, note = LINEARITY[name]
    c10 = ws.cell(row=r, column=10, value=linear)
    c10.font = data_font
    c10.alignment = data_align
    c11 = ws.cell(row=r, column=11, value=note)
    c11.font = data_font
    c11.alignment = data_align

if unresolved:
    print("UNRESOLVED method names:", unresolved)
else:
    print(f"Classified all {ws.max_row - 1} methods")

ws.column_dimensions["J"].width = 12.71
ws.column_dimensions["K"].width = 60.71

wb.save(PATH)
print("Saved:", PATH)
