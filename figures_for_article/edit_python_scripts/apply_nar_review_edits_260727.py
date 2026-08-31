#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Apply the NAR_review_260727.md edits to the manuscript as Word tracked changes.

Reads  FL_harmonization_article_NAR.docx
Writes FL_harmonization_article_NAR_260727.docx

Design constraints (see NAR_review_260727.md):

*   Every change is a genuine OOXML revision (<w:ins>/<w:del>), so *Accept All* gives the
    corrected manuscript and *Reject All* restores Daniil's exact original.
*   Edits are made in the smallest possible pieces: only the words that change are wrapped
    in del/ins, the rest of the sentence stays untouched.
*   **References are never touched.** The Mendeley citations in this document are stored as
    118 `<w:sdt>` structured-document-tag elements, and the bibliography is a further sdt.
    `word_rewrite_trackchanges.tracked_replace` rebuilds a paragraph from its concatenated
    text, which would destroy those fields, so it is NOT used here. `safe_tracked_replace`
    below edits only runs that are *direct children* of the paragraph; anything nested in a
    w:sdt or w:hyperlink is left byte-for-byte intact.
*   Where the correct wording depends on data only the authors have, no guess is made: a red
    italic [REVIEWER NOTE] paragraph is inserted instead (or in addition).

Run:  source ~/venvs/collagen_3_11/bin/activate && python apply_nar_review_edits_260727.py
"""
import sys
from pathlib import Path

import docx
from docx.oxml.ns import qn

HERE = Path(__file__).resolve().parent
MANUSCRIPTS = HERE.parent / "FL_manuscript_versions"
sys.path.insert(0, str(Path.home() / ".claude" / "skills"))
sys.path.insert(0, str(HERE.parent.parent / ".claude" / "skills"))
from word_rewrite_trackchanges import (  # noqa: E402
    insert_after,
    note_paragraph,
    set_revision_identity,
)
# The citation-safe replacement for word_rewrite_trackchanges.tracked_replace; see
# .claude/skills/nar-review/SKILL.md Step 2 for why tracked_replace must not be used here.
from nar_review_tools import safe_tracked_replace  # noqa: E402

SRC = MANUSCRIPTS / "FL_harmonization_article_NAR.docx"
DST = MANUSCRIPTS / "FL_harmonization_article_NAR_260727.docx"

set_revision_identity("Claude (NAR referee report 2026-07-27)", "2026-07-27T00:00:00Z")

W_P = qn("w:p")
W_T = qn("w:t")


# --------------------------------------------------------------------------- load + index
doc = docx.Document(str(SRC))
body = doc.element.body


def text_of(el):
    return "".join(t.text or "" for t in el.findall(".//" + qn("w:t")))


ALL_P = list(body.iter(qn("w:p")))          # includes paragraphs inside tables
BODY_P = [el for el in body if el.tag == qn("w:p")]   # top-level only (safe note anchors)


def find_p(anchor, pool=None):
    """The single paragraph whose text contains `anchor`; error if 0 or >1 matches."""
    hits = [p for p in (pool if pool is not None else ALL_P) if anchor in text_of(p)]
    if len(hits) != 1:
        raise LookupError(f"{len(hits)} matches for anchor {anchor!r}")
    return hits[0]


# =============================================================================== EDITS
# Each entry: (anchor used to locate the paragraph, [(old, new), ...])
# `old` is always chosen to sit inside one uninterrupted stretch of prose, never spanning
# a citation field.
EDITS = [
    # ---------------------------------------------------------------- ABSTRACT
    ("Cross-platform harmonization of bulk transcriptomic datasets remains", [
        # net -1 word: the abstract is at 199/200 words
        ("available in GitHub repository and can be used", "available on GitHub and can be used"),
    ]),

    # ---------------------------------------------------------------- INTRODUCTION
    ("bulk transcriptomic profiling remains the industry standard", [
        ("Regardless of the recent single cell RNA-seq, bulk transcriptomic profiling remains "
         "the industry standard for biomarkers detection",
         "Despite the rise of single-cell RNA sequencing, bulk transcriptomic profiling remains "
         "the standard approach for biomarker detection"),
        ("approximately 65000 bulk profiled patients", "approximately 65,000 bulk-profiled patients"),
        ("compared to the 4000 single cell profiled ones",
         "compared with approximately 4,000 single-cell-profiled patients"),
    ]),
    ("Most harmonization tools have been developed and benchmarked", [
        ("diffuse large B cell lymphoma (DLBCL)", "diffuse large B-cell lymphoma (DLBCL)"),
        ("technical batch effects can significantly exceed",
         "technical batch effects can substantially exceed"),
    ]),
    ("To benchmark the available harmonization tools under", [
        ("under the real world subtle biological and large-scale batch differences, we assembled "
         "a dataset of 7174 DLBCL, FL and B cells.",
         "under conditions of subtle biological and large-scale technical variation, we assembled "
         "a dataset of 7,174 DLBCL, FL and normal B-cell samples."),
        ("(sorted cells etc)", "(e.g. sorted cells)"),
    ]),
    ("We built a novel computational pipeline ComboBatch", [
        ("We built a novel computational pipeline ComboBatch, that included",
         "We built a computational pipeline, ComboBatch, that comprised"),
        ("encompassing totally 2,234 successfully completed",
         "encompassing 2,234 successfully completed"),
    ]),
    ("We demonstrated that Mutual Nearest Neighbours", [
        ("Mutual Nearest Neighbours (MNN)", "Mutual Nearest Neighbors (MNN)"),
    ]),
    ("Finally, the ComboBatch tool is available in GitHub repository", [
        ("tool is available in GitHub repository", "tool is available in a public GitHub repository"),
    ]),
    ("These results and computational tools further advance", [
        ("These results and computational tools further advance our abilities to transform the "
         "vast amounts of omics data into biological insights, foundation AI models and "
         "successful treatment options for cancer patients.",
         "Together, these results and computational tools help convert large-scale omics data "
         "into biological insight and, ultimately, into clinically actionable cancer biomarkers."),
    ]),

    # ---------------------------------------------------------------- METHODS
    ("MATERIALS AND METHODS", [
        ("MATERIALS AND METHODS", "MATERIAL AND METHODS"),
    ]),
    ("We assembled the largest possible set of publicly available cohorts", [
        ("the largest possible set of publicly available cohorts",
         "a comprehensive set of publicly available cohorts"),
    ]),
    ("For RNA-seq datasets gene expression profiling was done", [
        ("using the Genome reference GRCh38.d1.vd1 and Kallisto according to",
         "using the GRCh38.d1.vd1 reference and kallisto as described in"),
        ("the python implementation of Biomart package version 0.9.2",
         "the Python biomart package version 0.9.2"),
    ]),
    ("The full cross-product of prior batch removal", [
        ("on a Kubernetes pod with 32-48 CPU cores and 240 GB RAM managed by Karpenter",
         "on Kubernetes pods with 32–48 CPU cores and 240 GB RAM, provisioned by the Karpenter "
         "node autoscaler"),
    ]),
    ("The capital letters in the beginning of strategy names", [
        ("The capital letters in the beginning of strategy names are used as their synonyms in "
         "this paper.",
         "The capital letters at the beginning of the strategy names are used as strategy labels "
         "throughout this paper."),
    ]),
    ("Multi-platform batch correction introduced extensive missing", [
        ("Multi-platform batch correction introduced extensive missing expression values",
         "Combining data from multiple platforms introduced extensive missing expression values"),
        ("strict NA exclusion, KNN, Softimpute, and missForest",
         "strict NA exclusion, k-nearest-neighbour (KNN) imputation, Softimpute, and missForest"),
        ("MissForest was excluded from the benchmark", "missForest was excluded from the benchmark"),
    ]),
    ("Through systematic literature search, we reviewed 75", [
        ("Through systematic literature search, we reviewed 75",
         "Through a systematic literature search, we reviewed 75"),
    ]),
    ("Rejection reasons for harmonization methods that have not been taken", [
        ("that have not been taken into the implementation phase",
         "that were not taken forward to the implementation phase"),
    ]),
    ("After the rejection, we identified 39 harmonization methods", [
        ("We successfully implemented 31 of these methods",
         "We successfully implemented 33 of these methods"),
        ("Seven methods failed implementation", "Six methods failed implementation"),
        ("the ComboBatch pipeline combinatory space", "the ComboBatch pipeline combinatorial space"),
        ("released it as a separate Github repository", "released it as a separate GitHub repository"),
    ]),
    ("Each implemented method was assigned a qualitative harshness score", [
        ("owing to increasing algorithmic complexity",
         "consistent with their increasing algorithmic complexity"),
    ]),
    ("As an optional step after harmonization, we implemented a post-removal", [
        ("based on the assumption that harmonization can fail in certain cohorts and therefore "
         "they should be removed",
         "on the premise that harmonization may fail for individual cohorts, which can then be "
         "excluded"),
    ]),
    ("We built the harmonization pipeline based on python scripts", [
        ("executed by individual job script", "executed by an individual job script"),
        ("A monolithic implementation allowed to run additional combinations of all the two steps "
         "if necessary.",
         "The modular implementation allowed additional combinations of the two steps to be run "
         "if necessary."),
        ("Both steps outputs were saved on AWS s3 storage as expression.tsv.gz files accompanied "
         "with annotation files.",
         "Outputs of both steps were saved to Amazon Web Services S3 storage as gzipped "
         "expression tables accompanied by annotation files."),
    ]),
    ("For harmonization quality assessment, we assembled a set of 87", [
        ("The metrics have been collected from the available public literature",
         "The metrics were collected from the published literature"),
    ]),
    ("The 87 scoring metrics spanned four major groups", [
        ("(i) global intersection metrics, quantifying", "(i) global distance metrics, quantifying"),
        ("(ii) local mixing metrics, assessing", "(ii) local neighborhood metrics, assessing"),
        ("(iv) other metrics, including gene and sample level NA rate",
         "(iv) other metrics, including gene- and sample-level NA rate"),
    ]),
    ("Basic plotting was done using the general Python packages", [
        ("matplotlib (v 3.10.8)", "matplotlib (v3.10.8)"),
        ("assembled into final figures in Figma design", "assembled into final figures in Figma"),
    ]),
    ("Claude code with models Sonnet 4.8 and 5.0", [
        ("Claude code with models Sonnet 4.8 and 5.0",
         "Claude Code with the Claude Sonnet 4.8 and Sonnet 5 models"),
        ("the AI agent first wrote a research and implementation plan according, then the authors "
         "reviewed and commented it, then the AI agent acknowledged the comments and after a 2-5 "
         "review cycles it implemented the requested feature",
         "the AI agent first wrote a research and implementation plan, the authors then reviewed "
         "and commented on it, and after two to five review cycles the agent implemented the "
         "requested feature"),
    ]),
    ("Iterative code refinement for complicated visuals", [
        ("was done using Gemini AI", "was done using Google Gemini"),
    ]),

    # ---------------------------------------------------------------- RESULTS
    ("We assembled a multi-platform dataset of 7,174 bulk transcriptomic profiles", [
        ("With a focus on germinal centre (GC) B-cell malignancies",
         "With a focus on GC B-cell malignancies"),
    ]),
    ("To benchmark publicly available harmonization tools in an unbiased manner", [
        ("that had less then 5% samples with all NA gene expressions out of totally 2407 approaches",
         "that had fewer than 5% of samples with entirely missing gene expression values, out of "
         "2,407 attempted approaches"),
    ]),
    ("The dataset was markedly imbalanced with respect to both batch", [
        ("Among the five largest RNA batches by sample count, the fifth largest",
         "Among the six largest RNA batches by sample count, the fifth"),
        ("and sixth largest (GPL570_FFPE) contained DLBCL exclusively",
         "and sixth (GPL570_FFPE) contained DLBCL exclusively"),
    ]),
    ("We visualized gene set overlaps across imputation", [
        ("have broadly overlapped transcriptome coverage", "have broadly overlapping transcriptome coverage"),
    ]),
    ("For each combination of batch removal strategy and imputation method, we applied 31", [
        ("terminated by a 3-hour CPU timeout on Karpenter",
         "terminated by a 3-hour CPU-time limit imposed by the job scheduler"),
    ]),
    ("Using the 87 polarity-defined metrics and 2,234 qualifying harmonization approaches", [
        ("A third cluster showed no dominant correlation direction with the other two, it "
         "consisted of global, other and distributional metrics.",
         "A third cluster showed no dominant correlation direction with the other two and "
         "consisted of global, other and distributional metrics."),
    ]),
    ("Metrics in the 'NA percentage' cluster showed uniformly high performance", [
        ("and 87.2 – 100% for the rest strategies", "and 87.2–100% for the remaining strategies"),
        ("the good sub-cluster of 'same biomaterial and the entire 'same platform' cluster",
         "the good sub-cluster of the ‘same sample type’ cluster and the entire ‘same platform’ "
         "cluster"),
    ]),
    ("We calculated Spearman cross-correlations between all harmonization approaches", [
        ("confirming cluster identity was not an artefact",
         "confirming that cluster identity was not an artefact"),
        ("whereas the rest correlations had median of 0.730",
         "whereas the remaining correlations had a median of 0.730"),
    ]),
    ("Cluster map of 2234 harmonization approaches", [
        ("Cluster map of 2234 harmonization approaches (columns) in a space of 87 quality metrics "
         "(rows)",
         "Clustermap of 2,234 harmonization approaches (rows) in a space of 87 quality metrics "
         "(columns)"),
        ("The best approaches by clustermap are outlined below it via arrows and a rectangle for "
         "the MNN group.",
         "The best approaches identified from the clustermap are indicated beneath it by arrows, "
         "with a rectangle marking the MNN group."),
    ]),
    ("Without harmonization, the FL dataset exhibited a pronounced batch effect", [
        ("with percentage of variance explained by first PC 81.1%",
         "with 81.1% of the variance explained by the first PC"),
        ("produced further improvement in the concurrence of biological clustering",
         "produced a further improvement in the concordance of biological clustering"),
    ]),
    ("The second-best approach for the RNA-seq-only strategy (C) was FSQN R", [
        ("there were 3 batch-derived subclusters in the DLBCL cluster and two ones in the FL one",
         "there were three batch-derived subclusters in the DLBCL cluster and two in the FL cluster"),
    ]),
    ("We next visualized and assessed the remaining top-performing approaches", [
        ("PCA revealed incomplete batch mix but biologically relevant batches ordering",
         "PCA revealed incomplete batch mixing but a biologically meaningful ordering of samples"),
        ("tSNE confirmed this supremacy of biology over batch, but there was high degree of same "
         "batch connectivity: most NGS and Affymetrics platforms formed isolated clusters",
         "tSNE confirmed this dominance of biology over batch, but same-batch connectivity "
         "remained high: most NGS and Affymetrix batches formed isolated clusters"),
        ("because it resulted in the less pronounced biological clustering supremacy on both PCA, "
         "UMAP and tSNE",
         "because biological structure dominated less clearly in PCA, UMAP and tSNE"),
    ]),
    ("For the FFPE only batch removal strategy, the top approach", [
        ("resulted in a larger success: DLBCL samples of NGS, Affymetrix and Illumina microarrays "
         "mixed perfectly on both PCA and tSNE",
         "was more successful: DLBCL samples from NGS, Affymetrix and Illumina microarray batches "
         "were fully intermixed in both PCA and tSNE"),
        ("First 10 PCs clustering (Figure 5D) resulted two high level branches",
         "Clustering on the first 10 PCs (Figure 5D) produced two high-level branches"),
    ]),
    ("Finally, FSMVN and AMDBNorm methods showed promising results", [
        ("FSMVN in S0 lead to co-clustering", "FSMVN in S0 led to co-clustering"),
        ("AMDBNorm mixed the RNASeq_FF_ PolyA", "AMDBNorm mixed the RNASeq_FF_PolyA"),
        ("FF and FFPE only strategies lead to moderate success",
         "FF and FFPE only strategies led to moderate success"),
    ]),
    ("For the global PCA-based metrics we selected Principal Component Regression", [
        ("Zero PCR for an annotation column indicated that this column explained 0% of PCA "
         "variation, whereas PCR 1 showed that a column completely explained PCA variation.",
         "PCR is reported here in polarity-adjusted form, so that a value of 0 indicates that the "
         "annotation column explains all of the PCA variation and a value of 1 indicates that it "
         "explains none of it."),
        ("obtaining weak negative correlation", "obtaining a weak negative correlation"),
    ]),
    ("05_combat and 29_combat_ref harmonization showed better separation", [
        ("but they were rejected by clustermap",
         "but they were not selected in the clustermap-based assessment"),
    ]),
    ("It should be noted that S0 01_raw dataset", [
        ("This could be interpreted as 77.4% of total PCA variance is explained by batch "
         "confounding, and this baseline level is expected to be lowered by successful "
         "harmonization approaches.",
         "This corresponds to 77.4% of the total PCA variance being explained by batch — a "
         "baseline that successful harmonization is expected to reduce, thereby raising the "
         "polarity-adjusted PCR value."),
    ]),
    ("PCA variance explained by batch", [
        ("were below 1% for all PCs", "values were below 1% for all PCs"),
        ("with except for 33_amdbnorm applied", "with the exception of 33_amdbnorm applied"),
        ("14 methods out of 31 showed RNA_BATCH R2 for the first PC lower than the next PCs ones",
         "14 methods out of 31 showed a lower RNA_BATCH R2 for the first PC than for the "
         "subsequent PCs"),
        ("for 4 ones (with except for 20_shambhala)", "four (with the exception of 20_shambhala)"),
        ("Such pattern could indicate", "Such a pattern could indicate"),
        ("which manifest itself in poor local mixing performance",
         "which manifests itself as poor local mixing performance"),
    ]),
    ("We then investigated performance of the local mixing (local neighborhood) metrics", [
        ("scattered along the entire local metrics cluster in Supplementary Figure 6",
         "scattered along the entire local metrics cluster in Supplementary Figure 7"),
        ("which implies a fundamental trade-off: better local mixing of different batches leads "
         "also to the lower integrity of biology-derived local clusters",
         "which implies a trade-off: better local mixing of batches is accompanied by lower "
         "integrity of biology-defined local neighborhoods"),
    ]),
    ("As an additional local mixing metric, we visualized tSNE entropy", [
        ("As in the case of LISI, 10_mnn was the best approach",
         "As in the case of LISI, 10_mnn was the best method"),
    ]),
    ("We then compared percentage of samples and genes without NA", [
        ("the same 10 harmonizations methods returned no NA at all",
         "the same harmonization methods returned no NA at all"),
    ]),
    ("The harmonization methods drastically differ by expression range", [
        ("The harmonization methods drastically differ by expression range of their outputs",
         "The harmonization methods differed markedly in the expression range of their outputs"),
        ("whereas methods returning exotic transcriptomic profiles",
         "whereas methods returning atypical expression profiles"),
        ("06_combat_seq) failed.", "06_combat_seq) performed poorly."),
    ]),
    ("To integrate the multi-dimensional metric signals, we computed a composite", [
        ("across all the 87 scoring metrics, weighted by their polarity (Figure 9)",
         "across all the 87 scoring metrics, weighted by their polarity (Figure 9A)"),
        ("but have the comparable medians", "but had comparable medians"),
    ]),
    ("To quantify the relative contribution of each experimental factor", [
        ("we performed a variance decomposition analysis using R² effect sizes across the full "
         "87-metric composite scoring space",
         "we computed the mean η² effect size of each factor across the 87 scoring metrics"),
    ]),
    ("This ordering has direct practical implications for experimental planning", [
        ("one third of the good harmonization is the method itself, and one quarter more is the "
         "batch pre-selection",
         "approximately one third of the variation in harmonization quality is attributable to "
         "the method and a further quarter to the batch pre-selection"),
        ("this analysis refutes the common assumption", "this analysis argues against the assumption"),
    ]),
    ("We then visualized the clustermap best approaches along the six axes", [
        ("By batch removal strategies we had the C one with the highest batch mixing by kBET",
         "Among batch removal strategies, C showed the highest batch mixing by kBET"),
    ]),
    ("We then assessed an impact of metric types into the composite score", [
        ("We then assessed an impact of metric types into the composite score.",
         "We then assessed the contribution of each metric type to the composite score."),
        ("the local ones conferred 0.11 into the clustermap best group and 0.034 into the worst "
         "27_dwd one",
         "the local ones contributed 0.11 to the clustermap best group and 0.034 to the worst, "
         "27_dwd"),
    ]),
    ("The two top methods after the clustermap best group", [
        ("– apparently because they were applied to C strategy only.",
         "; both were applied only to strategy C, which limits their comparability with methods "
         "run across all 14 strategies."),
        ("and then raising to 0.106 in 10_mnn", "and then rising to 0.106 in 10_mnn"),
    ]),
    ("Composite performance score, clustermap best approaches behavior", [
        ("the composite score by harmonozation method harshness level",
         "the composite score by harmonization method harshness level"),
        # minimal panel-letter swap; see the note inserted after this legend
        ("(D) Stacked bar chart of cumulative normalized score", "(E) Stacked bar chart of cumulative normalized score"),
        ("(E) Enlarged radar plot showing the same best approaches", "(D) Enlarged radar plot showing the same best approaches"),
    ]),
    ("Based on the comprehensive benchmarking analysis, we formulated a data-driven", [
        ("five primary scenarios derived from the final decision analysis",
         "five primary scenarios derived from the benchmark results"),
        ("because the cohorts of these batches already co-clustered in PCA and tSNE spaces "
         "(Figure 4A), therefore the extensive and tricky harmonization was not needed",
         "because such datasets already co-clustered in PCA and tSNE space (Figure 4A), so "
         "extensive harmonization was not required"),
    ]),
    ("For fresh-frozen only datasets — comprising Affymetrix", [
        ("that may correspond to the previously unknown molecular subtypes",
         "that may correspond to as-yet-uncharacterized molecular subtypes"),
    ]),
    ("For mixed RNA-seq and Illumina microarray datasets", [
        ("the superiority of imputation-augmented approaches over strict gene-set restriction "
         "combined with SVA harmonization",
         "the superiority of imputation-augmented approaches over strict gene-set restriction "
         "when combined with SVA harmonization"),
    ]),
    ("Notably, post-removal — the exclusion of one PCA-outlier batch", [
        ("We recommend post-removal for all strategies as an optional step after visual "
         "inspection (Figure 9F), where a strong outlier batch was systematically identified "
         "across multiple imputation conditions.",
         "We recommend post-removal as an optional step for all strategies, applied after visual "
         "inspection (Figure 9F) when a strong outlier batch is consistently identified across "
         "multiple imputation conditions."),
    ]),

    # ---------------------------------------------------------------- DISCUSSION
    ("We aimed to find the best harmonization approach for the multiplatform", [
        ("outnumbers single cell profiled patients by approximately an order of magnitude",
         "outnumbers single-cell-profiled patients by more than an order of magnitude"),
        ("clinical assays like BostonGene Tumor Portrait", "clinical assays such as BostonGene Tumor Portrait"),
        ("the primary FF/FFPE batch effect is unreliable to scRNA",
         "the dominant FF/FFPE batch effect is largely irrelevant to scRNA-seq"),
    ]),
    ("The dataset assembled for this study was markedly imbalanced", [
        ("renders the current FL-containing dataset inherently more challenging harmonization "
         "target",
         "renders the present FL-containing dataset an inherently more challenging harmonization "
         "target"),
    ]),
    ("Moreover, the follicular lymphoma transcriptome represents one of the most", [
        ("across 29 RNA batches and four sequencing platforms",
         "across 29 RNA batches and four transcriptomic platforms"),
    ]),
    ("The current state of the art benchmarking datasets", [
        ("The current state of the art benchmarking datasets", "Current benchmarking datasets"),
        ("possess massively distinct biological groups", "comprise biologically highly distinct groups"),
        ("while preserving thousands differentially expressed genes",
         "while preserving thousands of differentially expressed genes"),
        ("only SVA and MNN allow to preserve the subtle FL/DLBCL/normal GC B cells differences",
         "only SVA and MNN preserved the subtle differences between FL, DLBCL and normal GC "
         "B cells"),
    ]),
    ("The FL-specific biological discovery — two transcriptional subgroups", [
        ("the established GCB/ memory cell like", "the established GCB-like and memory-cell-like"),
    ]),
    ("The ComboBatch pipeline is conceptually distinct from previous", [
        ("approximately 5–-fold smaller in transcriptional effect size",
         "approximately five-fold smaller in transcriptional effect size"),
        ("spanning local neighborhood, global, distributional, and structural aspects of "
         "harmonization quality",
         "spanning local neighborhood, global distance, distributional similarity and other "
         "aspects of harmonization quality"),
    ]),
    ("The computational scale of ComboBatch", [
        ("on 32 vCPU / 240 GiB RAM infrastructure", "on 32–48 vCPU / 240 GiB RAM infrastructure"),
    ]),
    ("We note important technical limitations of the current pipeline", [
        ("and we have 2 batches and 15 cohorts below 10 samples",
         "and the present dataset contains 2 batches and 15 cohorts with fewer than 10 samples"),
        ("have been failed in implementation due to technical reasons that should be solved",
         "failed at the implementation stage for technical reasons that remain to be resolved"),
    ]),
    ("The 87-metric ", [
        ("2,234- approach clustermap", "2,234-approach clustermap"),
    ]),
    ("The practical value of the clustermap-based selection approach", [
        ("such as the Angel harmonizer's low gene retention failure",
         "such as the HarmonizR gene-retention failure"),
        ("(manifesting as a distinct column in the NA-percentage metric cluster in Figure 3)",
         "(manifesting as a distinct band in the NA-percentage metric cluster in Figure 3)"),
    ]),
    ("The metric cross-correlation structure (Supplementary Figure 7) further reveals", [
        ("validating this two-axis evaluation framework", "validating the two-axis evaluation framework"),
        ("can simultaneously fail spectacularly on kBET and iLISI",
         "can simultaneously perform poorly on kBET and iLISI"),
    ]),
    ("AI-driven brute force and human-based approaches", [
        ("AI-driven brute force and human-based approaches: AI enhancement leads to ~2 times more "
         "actionable approaches",
         "Complementary roles of AI-assisted and expert-driven method discovery"),
    ]),
    ("The ComboBatch benchmark was designed as an exhaustive computational search", [
        ("This brute-force approach proved critical", "This exhaustive approach proved critical"),
    ]),
    ("Interestingly, rank normalization and standard quantile normalization", [
        ("but conditions on a biology-matched reference distribution, preserving expression shape "
         "while eliminating scale differences",
         "but matches each feature to a gene-wise reference distribution derived from a reference "
         "platform, preserving expression shape while eliminating scale differences"),
    ]),

    # ---------------------------------------------------------------- CONCLUSIONS / BACK MATTER
    ("In the present study we assembled a GC B cell lymphoma cross-platform cohort", [
        ("SVA and MNN only were able to recurrently resolve subtle differences between "
         "transcritpional programs",
         "only SVA and MNN reproducibly resolved subtle differences between the transcriptional "
         "programs"),
    ]),
    ("We thank Alisa Sadekova for normal B cells dataset provision", [
        ("A special gratitude is dedicated to Daniil Nikitin’s sons, Ivan and Alexandr, who have "
         "been intensively playing, crying and fighting around Daniil while he was writing the "
         "article, asking each day ‘when you daddy will complete it?’. Daniil’s wife Irina "
         "Nikitina was asking the same question but with the same support and more patience, a "
         "special thanks to her.",
         "D.N. thanks his family — his sons Ivan and Alexandr and his wife Irina Nikitina — for "
         "their patience and support during the preparation of this manuscript."),
    ]),
    ("Daniil Nikitin, Maria Savchenko, Mark Meerson and Alexandr Bagaev are BostonGene", [
        ("where Daniil Nikitin is currently applying as PhD student and this article is planned "
         "as a part of articles series for his PhD thesis.",
         "where Daniil Nikitin is a PhD candidate; this article is planned as part of a series of "
         "articles constituting his PhD thesis."),
    ]),
    ("Clustermap of the 87 scoring metrics Sperman cross-correlations", [
        ("Sperman cross-correlations", "Spearman cross-correlations"),
    ]),
    ("3 X 2 rectangular grid of PCA plots of 10_mnn harmonized strict", [
        ("color palettes in the lefr side of the figure", "color palettes on the left side of the figure"),
    ]),
    ("Values of the 87 scoring metrics for the 2409 harmonization approaches", [
        ("for the 2409 harmonization approaches analyzed in this study",
         "for the 2,407 harmonization approaches computed in this study"),
    ]),
    ("The transcriptomic data analyzed in this study derive from publicly available", [
        ("are listed in Supplementary Table 1", "are listed in Supplementary File 1"),
    ]),

    # ---------------------------------------------------------------- TABLE CELLS
    ("DASC is a batch returns semi-NMF cluster assignments", [
        ("DASC is a batch returns semi-NMF cluster assignments",
         "DASC returns semi-NMF cluster assignments"),
    ]),
    ("Same as the previous metric but measures within-batch cohort effects", [
        ("Its specifically isolates residual cohort effects", "It specifically isolates residual cohort effects"),
    ]),
    ("Anderson-Darling test on per-batch 30 nearest neighbor", [
        ("per-batch 30 nearest neighbor’s distance distributions",
         "per-batch 30-nearest-neighbour distance distributions"),
    ]),
]

# =============================================================================== NOTES
# (anchor of a TOP-LEVEL paragraph, note text) — inserted immediately after that paragraph.
NOTES = [
    ("Cross-platform harmonization of bulk transcriptomic datasets remains",
     "Abstract is 199/200 words, so it has almost no headroom; the edit above is net −1 word. "
     "Render “R2” as R² (superscript). The Abstract states method (0.36) > strategy (0.26), but "
     "the clustermap analysis in Results/Discussion concludes the opposite ordering — reconcile "
     "the two, or state here that the two analyses weight the factors differently."),

    ("bulk transcriptomic profiling remains the industry standard",
     "65,000 / 4,000 is a ~16-fold ratio, but the Discussion describes it as “approximately an "
     "order of magnitude”. Please give one consistent figure (the Discussion sentence has been "
     "changed to “more than an order of magnitude”)."),

    ("For RNA-seq datasets gene expression profiling was done",
     "CRITICAL FOR REPRODUCIBILITY — please supply: (a) the kallisto version; (b) the "
     "transcriptome annotation used to build the index (e.g. GENCODE release), since kallisto "
     "indexes a transcriptome and not the genome; (c) which Python BioMart package was used "
     "(`biomart` or `pybiomart`) and the Ensembl/BioMart release, since probe→HGNC mapping "
     "changes between releases."),

    ("The full cross-product of prior batch removal",
     "Hardware is described three different ways in this manuscript: “32-48 CPU cores / 240 GB” "
     "here, “an 8-core, 64 GB RAM server” in the missForest exclusion, and “32 vCPU / 240 GiB” in "
     "the Discussion. Please reconcile, and state which analyses ran on which machine — the "
     "missForest exclusion currently rests on a timeout measured on the smallest configuration, "
     "which weakens that justification."),

    ("We ran KNN imputation using the KNNImputer",
     "VERSION CONFLICT: scikit-learn is given as v1.8.0 here and as v1.3.2 in both the metrics "
     "and the figure-preparation subsections. Please correct to the version actually used."),

    ("Through systematic literature search, we reviewed 75",
     "“Systematic” requires a documented protocol. Please add the databases searched, the query "
     "strings, the date range, and the inclusion/exclusion criteria — a PRISMA-style flow diagram "
     "in the supplement would support the 75 → 39 → 33 funnel well. Table 2 also still contains "
     "an unresolved “(ref)” placeholder in the row “Reported earlier to actively harm signal”."),

    ("After the rejection, we identified 39 harmonization methods",
     "CRITICAL — METHOD COUNT: Table 3 marks 33 methods “Implementation done = Yes” and 6 “No”, "
     "and Supplementary File 3 contains 33 distinct methods; the text said 31 implemented and 7 "
     "failed (31+7=38≠39). I have changed the numbers to 33 and 6, but this creates a second "
     "problem you must resolve: 34_arsyn and 38_harman are implemented (78 runs each in "
     "Supplementary File 3) yet appear in NONE of Figures 3, 6, 7, 8 or 9, all of which show "
     "exactly 31 methods. Either include them in the analyses or state explicitly that they were "
     "excluded and why, and make every “31 methods” statement in the paper consistent with that "
     "decision."),

    ("After the rejection, we identified 39 harmonization methods",
     "CRITICAL — MODEL SPECIFICATION: “default parameters” does not determine the behaviour of "
     "SVA, limma removeBatchEffect, ComBat, ComBat-seq, M-ComBat or RUV, all of which require the "
     "user to declare which covariates are protected. This is the single most consequential "
     "choice in the study: an SVA run with no biological covariate in `mod` can remove exactly "
     "the FL/DLBCL signal being measured. Please state the design/model matrices (mod, mod0, "
     "batch vector, k) for every supervised method."),

    ("Each implemented method was assigned a qualitative harshness score",
     "Figure 9A tests a hypothesis about harshness, so the harshness assignment must be "
     "auditable: please state who assigned the scores, against what written criteria, and whether "
     "the assignment was made before the results were seen. A supplementary table listing the "
     "score and its justification per method would settle this."),

    ("As an optional step after harmonization, we implemented a post-removal",
     "The post-removal rule is incomplete and inconsistently scoped. (a) The removal criterion "
     "itself is never stated — only the distance metric. Please give the rule (e.g. “the single "
     "cohort with the largest centroid distance”, or a threshold in MAD units). (b) This "
     "paragraph removes COHORTS (“for each of the 88 cohorts”), whereas Results and Discussion "
     "both describe removing “one PCA-outlier BATCH”. There are 88 cohorts and 29 batches; please "
     "state which unit was actually removed."),

    ("We built the harmonization pipeline based on python scripts",
     "I changed “A monolithic implementation” to “The modular implementation” because the "
     "preceding two sentences describe a dispatcher/worker/library architecture, which is the "
     "opposite of monolithic. Please confirm this was the intended meaning."),

    ("For harmonization quality assessment, we assembled a set of 87",
     "CRITICAL — METRIC COUNT: this paragraph says 87 scoring + 143 additional = 230 metrics, and "
     "Results repeats “up to 230”. Supplementary File 4 as deposited lists 165 metrics: 51 with "
     "polarity +1, 36 with −1 (= the 87 scoring metrics, which match Supplementary File 3's 87 "
     "metric columns exactly) and 78 with polarity 0. 87 + 78 = 165. Please correct 230/143, or "
     "deposit the missing 65 metric definitions. Also document the third polarity level (0), "
     "which the Results text does not mention."),

    ("Table 4. Metric groups for harmonization quality control",
     "TABLE 4 IS INCOMPLETE AND PARTLY INCONSISTENT WITH THE DATA. (a) It lists metric groups A, "
     "B, C, D, E, G, H, I, J but omits group K (“Samples and genes with NAs”), which appears in "
     "Figure 3's own legend; no group F is defined anywhere. (b) The “Source” column is filled in "
     "for only one of the 18 rows. (c) CRITICAL: the PCR and PCA R² definitions here are written "
     "in the conventional direction (higher = column explains more variance), but the values "
     "deposited in Supplementary File 3 run in the opposite direction for PCR (unharmonized S0 = "
     "0.23; best methods = 1.00) while per-PC R² is non-inverted. Please state, per metric, "
     "whether the reported value is raw or polarity-adjusted. (d) ASW and CMS are typed “Global”, "
     "while kBET and LISI in the same group B are “Local”; CMS is a local mixing metric by "
     "construction. (e) Sarle's bimodality coefficient is a statistic, not a test."),

    ("Harmonization quality metrics were computed and statistically analyzed",
     "Please add here: the random seed and the UMAP/t-SNE parameters (n_neighbors, min_dist, "
     "perplexity). Fourteen of the 87 scoring metrics are computed in embedding space, the "
     "embeddings are stochastic, and several conclusions rest on differences of 0.01–0.05 in "
     "those metrics. Please also report the run-to-run variability of the embedding metrics on at "
     "least a subsample, so readers can judge whether those differences exceed the noise."),

    ("Iterative code refinement for complicated visuals",
     "Please give the Gemini model name and version, to match the level of detail given for "
     "Claude Code."),

    ("We assembled a multi-platform dataset of 7,174 bulk transcriptomic profiles",
     "The counts in this sentence do not sum to the dataset: 4,466 DLBCL + 1,697 FL + 875 normal "
     "B cells + 88 Burkitt + 34 high-grade = 7,160, not 7,174. The missing 14 are the plasmablast "
     "samples, which are present in Supplementary File 1 and mentioned two paragraphs below. "
     "(I verified that the 10 normal-B categories in Supplementary File 1 sum to exactly 875, and "
     "that 875 + 14 = 889 = the samples removed by strategy D, consistent with Table 1's 6,285.) "
     "Please add the plasmablasts."),

    ("To benchmark publicly available harmonization tools in an unbiased manner",
     "CRITICAL — APPROACH COUNT AND REPRODUCIBILITY. (a) Four different totals appear in the "
     "manuscript: 2,234 (Abstract, Results, Figure 3, Discussion), 2,407 (here and below), 2,604 "
     "(Discussion) and 2,409 (Supplementary File 3 legend). Supplementary File 3 has 2,407 data "
     "rows, all with status = ok. Please fix all four and state the denominator each refers to. "
     "(b) The “<5% samples with all-NA expression” filter cannot be reproduced from the deposited "
     "file: pct_samples_noNA ≥ 95 gives 2,038 rows, pct_na_cells < 5 gives 2,186, and requiring "
     "all 87 metrics to be defined gives 1,354 — none of them 2,234. Please add the subset flag "
     "as a column in Supplementary File 3 so that every number in the paper can be recomputed."),

    ("The initial step of ComboBatch was prior batch removal",
     "Two points on this paragraph. (a) The gene-count ranges are hard to follow in prose and the "
     "value 6,797 bounds the strict range from above (strategy C) and the imputed range from "
     "below (strategy J) — please tabulate gene counts per strategy × imputation instead. (b) The "
     "modality sentence reads as if there were only 16 microarray and 72 RNA-seq cohorts; please "
     "rephrase to make clear that 16 of 88 cohorts were unimodal and 72 of 88 bimodal."),

    ("For each combination of batch removal strategy and imputation method, we applied 31",
     "The strategies with undefined annotation-dependent metrics are listed as “C, G, J, and K” "
     "here but as “(J, K) … or (H, C)” two paragraphs below. Supplementary File 3 supports the "
     "first list: mean non-NA metric counts are K 66.6, G 67.0, C 71.8, J 74.8, S0 81.4 and "
     "85.9–86.8 for every other strategy, including H at 86.7. Please correct the second list."),

    ("Using the 87 polarity-defined metrics and 2,234 qualifying harmonization approaches",
     "CRITICAL — THE COMPOSITE SCORE IS NOT COMPARABLE ACROSS STRATEGIES. Because annotation "
     "columns become invariant in single-platform/single-biomaterial subsets, the number of "
     "DEFINED metrics varies from 66.6 (K) to 86.8 (I) per approach, and only 1,354 of 2,407 "
     "approaches have all 87 metrics. A mean over 67 metrics is not on the same scale as a mean "
     "over 87, yet the two are ranked against each other and used as the response variable in "
     "Figure 9. This biases the comparison in favour of strategies C and K — exactly the "
     "strategies the paper recommends. Please either restrict the composite to the metric subset "
     "defined for all strategies, or compute it within strategy and compare ranks, and report how "
     "sensitive the conclusions are to that choice."),

    ("We calculated Spearman cross-correlations between all harmonization approaches",
     "Please report an effect size alongside p-values of this magnitude. With n = 2,234 the "
     "p-value carries almost no information, and the approaches are not independent observations "
     "— they are repeated analyses of 42 overlapping strategy × imputation subsets, so every "
     "Mann–Whitney test and correlation in the paper is pseudo-replicated. Consider testing at "
     "the level of the 42 independent subsets, and state the dependence as a limitation."),

    ("Cluster map of 2234 harmonization approaches",
     "FIGURE 3 — four problems. (1) The legend had the axes reversed: in the figure the approach "
     "dendrogram is on the left and the metric names label the vertical strips, so approaches are "
     "ROWS and metrics are COLUMNS (corrected above — please verify). (2) The figure is drawn at "
     "39.6 × 26.8 cm; at NAR's maximum 17.35 cm width the scale factor is 0.44 and 100% of the "
     "text falls below 5 pt (median 4.4 pt) — it must be re-laid out for a 17.35 cm canvas, not "
     "scaled down. (3) The whole panel is rotated 90°, so every label reads sideways. (4) The "
     "metric-score scale is red–green, the worst choice for the commonest colour-vision "
     "deficiency, on a figure where colour IS the data; NAR/OUP require a colour-blind-safe "
     "palette. Please also confirm that the method colour legend intentionally omits 34_arsyn and "
     "38_harman, and note that the group-K swatch in the legend has no counterpart in Table 4."),

    ("Without harmonization, the FL dataset exhibited a pronounced batch effect",
     "PC1 variance for the raw S0 dataset is given as 81.1% here and as 73.5% in the Figure 6C "
     "paragraph, and a third quantity — “77.4% of PCA variance attributable to RNA_BATCH” — is "
     "derived from 1 − PCR and is not the same thing as either. Please give one number per "
     "quantity, label each precisely (total variance on PC1 vs batch-explained variance on PC1 vs "
     "weighted PCR), and state which imputation and post-removal condition each refers to."),

    ("Based on the clustermap visual inspection combined with quantitative composite scoring",
     "Table 5 has no group for the “RNA-seq + Illumina microarrays” scenario, yet the decision "
     "tree (Figure 9F) and the Discussion recommend FSQN R as best for it with AMDBNorm/FSMVN as "
     "alternates, while Table 5 lists FSMVN and AMDBNorm only, both under S0. Please make Table "
     "5, Figure 9F and the Discussion agree. Note also that Table 5 defines eight best-approach "
     "groups while Figure 8F is described as showing “the 15 clustermap-selected best "
     "approaches” — please reconcile the 8 and the 15."),

    ("For the global PCA-based metrics we selected Principal Component Regression",
     "CRITICAL — THE PCR DEFINITION WAS INVERTED. As written, the definition (0 = explains "
     "nothing, 1 = explains everything) is the opposite of how PCR is used everywhere else in "
     "this section and of the values in Supplementary File 3: unharmonized S0 has pcr_RNA_BATCH "
     "0.227–0.313 and the best methods (33_amdbnorm, 13_fsmvn, 03_limma) have exactly 1.000. I "
     "have rewritten the definition to the polarity-adjusted direction, which makes the rest of "
     "the section coherent — but please confirm the exact transformation you applied (1 − "
     "weighted R²?), state it in Methods and Table 4, and note explicitly that PCR is reported "
     "inverted while the per-PC R² values in Figure 6C are not. Also: r = −0.159 explains ~2.5% "
     "of the variance and cannot on its own support the global/local trade-off claim — please "
     "report a confidence interval and lean on the LISI correlation for that argument. I could "
     "not reproduce either coefficient from Supplementary File 3 (I obtain r = −0.109, p = 8.7 × "
     "10⁻⁸ here and r = 0.352, p = 6 × 10⁻⁷¹ for the LISI pair), presumably because the paper "
     "uses the 2,234-row subset — see the note on the approach count."),

    ("It should be noted that S0 01_raw dataset",
     "The unharmonized S0 dataset has six rows in Supplementary File 3 (three imputations × two "
     "post-removal conditions) with pcr_RNA_BATCH from 0.227 to 0.313. Please state which one the "
     "quoted 0.226 refers to, or give the median across the six."),

    ("To deeply investigate the PC-level variation, we calculated percentage of variance",
     "33_amdbnorm and 13_fsmvn both have pcr_RNA_BATCH of exactly 1.0000 in every run — a global "
     "metric pinned at its theoretical optimum, combined with the poor local mixing you report. "
     "That pattern is at least as consistent with the method having destroyed the expression "
     "structure as with successful correction (13_fsmvn also produces a minimum expression value "
     "of −40.6). Since both methods are recommended in Table 5 and Figure 9F, please investigate "
     "and report what these outputs actually look like. Note also that 33_amdbnorm completed only "
     "14 of 84 possible runs."),

    ("We then investigated performance of the local mixing (local neighborhood) metrics",
     "The by-METHOD LISI values quoted here (10_mnn median 1.72, all approaches 1.16, 14_qsmooth "
     "1.07) are on a 1–2.3 scale, whereas the iLISI column deposited in Supplementary File 3 "
     "(ilisi_norm_RNA_BATCH) ranges 0–0.234 with a 10_mnn median of 0.046. The by-STRATEGY values "
     "in the same paragraph do reproduce exactly against clisi_mean_Diagnosis_cell_type_unified "
     "(J 1.620, C 1.391, H 1.412, D 1.095, K 1.073). Please state which iLISI variant is plotted "
     "in Figure 7A/B, deposit it, and note that the two axes of that panel are on different "
     "normalisations (clisi_mean_* vs ilisi_norm_*). Please also define cLISI and iLISI at first "
     "use — currently only “LISI” is defined, in Table 4."),

    ("As an additional local mixing metric, we visualized tSNE entropy",
     "“peak values of 0.26 and 1.01” — please say which value belongs to the low-dispersion and "
     "which to the high-dispersion area."),

    ("As a final part of the harmonization quality metrics comparison among the approaches",
     "The KS-test metric is defined two different ways: Table 4 says the test compares "
     "distributions “between all pairs of batches” for each of 1,000 randomly selected genes, "
     "while this paragraph says “between all sample pairs within batches”. Please give one "
     "definition. Please also state whether the 1,000-gene subset was drawn once and held fixed "
     "across all approaches — if it was redrawn per approach, the metric is not comparable "
     "between approaches — and give the seed."),

    ("We then compared percentage of samples and genes without NA",
     "The counts in this paragraph do not add up: the first sentence says 19 of 31 methods "
     "returned no NA at sample level, then “the same 10 harmonization methods returned no NA at "
     "all” at gene level, and 10 + 11 + 1 = 22 ≠ 31. Please recount both sentences. Also, "
     "Supplementary File 3 gives 99.72–100% (not 87.2–100%) as the per-strategy medians of "
     "pct_genes_noNA for 21_harmonizr on the eight non-zero strategies — if 87.2% is a minimum "
     "over individual runs, say so."),

    ("To quantify the relative contribution of each experimental factor",
     "CRITICAL — THIS IS NOT A VARIANCE DECOMPOSITION. The text said “variance decomposition "
     "using R² effect sizes”; the Figure 9B axis says “Mean η² effect size across 87 scoring "
     "metrics”. Those are three different quantities. Four separate marginal one-way effect sizes "
     "do not partition variance, they ignore interactions, and they ignore the fact that the "
     "design is badly unbalanced (runs per method in Supplementary File 3: 22_tmm 6, 23_vst 6, "
     "33_amdbnorm 14, 27_dwd 34, 29_combat_ref 34, 36_explobatch 60, 04_sva 80, 05_combat 80, "
     "19_tdm 80, 08_inmoose 82, 06_combat_seq 83, all others 84). Recomputing on the composite "
     "score over all 2,407 rows I obtain method 0.429, strategy 0.174, imputation 0.002, "
     "post-removal 0.000 (additive four-factor R² = 0.593) — the ORDERING reproduces but the "
     "strategy term differs by ~50% from the reported 0.256, which matters because "
     "“method > strategy” is an Abstract-level claim that the clustermap analysis contradicts. "
     "Please specify the model and estimator, report confidence intervals, use one notation "
     "throughout, and re-derive the figure on a coverage-balanced subset."),

    ("We then visualized the clustermap best approaches along the six axes",
     "Figure 9C and 9D have no colour legend, so a reader cannot map a line to a method (C) or to "
     "a strategy (D) — please add both. The two panels also label the same six axes differently "
     "(“Global batch” vs “Global batch mixing”, “Local biology” vs “Local biology separation”). "
     "Please also state which normalised scale the values quoted in this paragraph (0.65–1.0, "
     "0.07–0.7) are on. Finally, kBET is one of the six axes but has a median of 0.000 and a 75th "
     "percentile of 0.0041 across 2,395 approaches — a metric that is zero for more than half the "
     "design cannot carry a sixth of the summary figure; either drop it or justify keeping it."),

    ("The two top methods after the clustermap best group",
     "CRITICAL — UNBALANCED COVERAGE DRIVES THIS RANKING. 22_tmm and 23_vst rank 1st and 2nd on 6 "
     "runs each, all in strategy C, which the sentence now acknowledges; but they are still left "
     "at the top of Figure 9E and of the narrative ranking. 33_amdbnorm (3rd–5th here, in Table 5 "
     "and in the decision tree) has 14 of 84 runs. Please report coverage per method, and either "
     "exclude methods with incomplete coverage from the ranking or report them separately. In my "
     "reconstruction on all 2,407 rows the order after tmm/vst is 28_npn, 33_amdbnorm, 26_xpn, "
     "13_fsmvn, then 10_mnn — i.e. two methods that outrank MNN are not mentioned. Please "
     "re-derive the ranking on a balanced subset."),

    ("Composite performance score, clustermap best approaches behavior",
     "FIGURE 9 LEGEND — panels D and E were swapped relative to the figure (the figure is C = "
     "radar by method, D = enlarged radar by strategy, E = stacked bar chart; the main text cites "
     "them correctly). I have swapped the two panel letters only; please now reorder the two "
     "sentences so the legend reads C, D, E, F in sequence. Also: panel E's metric-type names "
     "(“Local neighborhood / Global distance / Distribution similarity / Other”) do not match the "
     "four names used in Methods — I have changed Methods to match the figures, so please check "
     "you are happy with that direction. Panel B's axis says η² while the text said R²."),

    ("For fresh-frozen only datasets — comprising Affymetrix",
     "The 56% relative PC1 reduction quoted here (87.6% raw → 38.4% post-harmonization) does not "
     "appear in any figure, table or supplementary file. Please add the supporting data. The "
     "claim that SVA “uniquely” reveals two FL transcriptional subgroups also needs support: as "
     "written it is indistinguishable from an imputation artefact of the same low-rank machinery "
     "that you report introducing spurious trimodal distributions in 14 cohorts. At minimum, show "
     "that the subgroups reproduce across both imputation methods and across random seeds, give "
     "the subgroup-defining genes, and confirm they are not enriched for high-missingness genes."),

    ("The current state of the art benchmarking datasets",
     "The paper gives three different counts of how many methods preserved the biology: “SVA and "
     "MNN” here and in the Conclusions, “MNN, SVA, and FSQN R” in the comparison subsection, and "
     "five methods in Table 5 / Figure 9F. Please state one explicit criterion for “resolved the "
     "biology” and use one consistent count throughout."),

    ("The ComboBatch pipeline is conceptually distinct from previous",
     "Two points. (a) “approximately five-fold smaller in transcriptional effect size” is "
     "unsourced, and the Discussion later gives “2–5-fold” and “5–10-fold” for closely related "
     "quantities — please give one estimate, state how it was computed, and cite it. (b) “2,604 "
     "theoretical configurations (2,234 successfully completed)” omits the 2,407 attempted runs "
     "reported in Results, and 2,604 assumes 31 methods; with the 33 implemented methods the "
     "cross-product is 2,772. Please give a single reconciled chain of numbers."),

    ("We note important technical limitations of the current pipeline",
     "This limitations paragraph is welcome. Please consider adding, as the referee report notes: "
     "(a) that the composite score averages different metric subsets for different strategies; "
     "(b) that six of the 33 implemented methods were not run on all 14 strategies; (c) that the "
     "embedding-space metrics are computed on stochastic embeddings without replication; and (d) "
     "that no permutation-based negative control or predictive positive control was performed. On "
     "(d): a label-permutation control (permute the biology labels and confirm the "
     "biology-preservation metrics collapse) plus a cross-cohort FL-vs-DLBCL classification check "
     "before and after harmonization would be the single most valuable addition to this study — "
     "they would convert “the embeddings look right” into a measured result."),

    ("The practical value of the clustermap-based selection approach",
     "The gene-retention failure is attributed to 21_harmonizr in Results (0% pct_genes_noNA for "
     "strategies A, B, C, E1–E3, J and S0 — which Supplementary File 3 confirms exactly) but to "
     "“the Angel harmonizer” here. I have changed it to HarmonizR; please confirm which method "
     "you meant."),

    ("The metric cross-correlation structure (Supplementary Figure 7) further reveals",
     "Please give the actual value behind “Spearman r ≈ 0 between clusters” (median and "
     "confidence interval), since this empirical orthogonality is described as the key statistical "
     "justification for the two-axis framework."),

    ("The ComboBatch benchmark was designed as an exhaustive computational search",
     "The section heading previously claimed “AI enhancement leads to ~2 times more actionable "
     "approaches”; I have replaced it, because nothing in this section measures that. The "
     "remaining claim that the mixed discovery process “identified a combination that "
     "outperformed any single-strategy search” also has no supporting comparison — please either "
     "provide one or soften it to an observation."),

    ("We thank Alisa Sadekova for normal B cells dataset provision",
     "The personal paragraph about the author's family was well outside the register of a research "
     "journal (and contained grammatical errors), so I have replaced it with a short formal "
     "acknowledgement. Please confirm the shortened wording, or delete the sentence entirely — "
     "either is acceptable to NAR."),

    ("Daniil Nikitin: Conceptualization, Data curation, Formal analysis",
     "The Author Contributions list covers seven authors, but the byline lists nine names, several "
     "marked “?”, including one that appears to be a database rather than a person. The "
     "two lists must match exactly, every author needs an affiliation superscript, and the "
     "submitting author needs an ORCID iD (mandatory)."),

    ("Supplementary Data are available at NAR online",
     "SUPPLEMENTARY MATERIAL DOES NOT MEET NAR'S LIMITS. NAR allows one combined PDF, or "
     "otherwise at most 10 files of ≤2 MB each. The submission folder currently holds 32 files: "
     "17 Supplementary Figures, 10 “Extended Figure” PDFs, 4 Supplementary Files and "
     "Harmonization_metrics_extended.docx; four exceed 2 MB (Supplementary Figure 9 at 8.4 MB, "
     "Supplementary Figures 2–4 at ~4.4 MB each). Please combine the figures into a single PDF and "
     "the tables into one spreadsheet workbook. Three further points: (a) the 10 “Extended Figure” "
     "files are cited nowhere in the manuscript and NAR has no “Extended Figure” category — fold "
     "them into the Supplementary Figure sequence and cite each, or drop them; (b) none of the "
     "Supplementary Figure legends carries an “Alt text:” line, which the main figures correctly "
     "do; (c) “Supplementary File 4” has no file extension — it is a CSV and should be named as "
     "one."),

    ("Number of genes with defined gene expression by sample in the initial dataset",
     "Supplementary File 2 as deposited contains 7,238 rows, but the dataset described throughout "
     "the manuscript has 7,174 samples (Supplementary File 1 has exactly 7,174 rows). Either this "
     "is a pre-filtering version — in which case say so and document the 64 excluded samples — or "
     "it is the wrong file."),

    ("Polarity coefficients by harmonization quality metrics used in this study",
     "Supplementary File 4 contains 165 metrics with a three-level polarity code (+1: 51, −1: 36, "
     "0: 78). Please update this legend to describe the 0 level and the 165 total, and reconcile "
     "with the “230 metrics / 143 additional” figures given in Methods and Results."),

    ("The data supporting this article are available in the article",
     "DATA AVAILABILITY IS NOT YET NAR-COMPLIANT. (a) NAR explicitly does not accept GitHub as a "
     "primary archive because it issues no permanent DOI; the statement currently points to GitHub "
     "for the pipeline, the ComboBatch tool, the extended metrics document and the containerised "
     "Shambhala, and asserts a Zenodo DOI without giving one. Please mint the Zenodo DOIs and cite "
     "them. (b) MIAME/MINSEQE compliance is not stated and is required for reused microarray and "
     "sequencing data. (c) The deposited code must be accompanied by installation instructions, a "
     "manual, a worked usage example and sample input/output. (d) On your own open question about "
     "depositing ~2,000 datasets of ~1 GB: a defensible and finite answer is to deposit the "
     "87-metric table, the polarity table, the per-strategy gene lists and the harmonized matrices "
     "for the eight best approaches only, together with the pipeline and a container image "
     "sufficient to regenerate the rest — and to state that in the manuscript."),

    ("Funding for computational resources was provided by BostonGene internal grant",
     "There are two competing funding statements here, the second of which is the unfilled "
     "template, and the first ends with a bare “Funding for open access charge:” followed by "
     "nothing. Please merge them into one NAR-formatted statement: full official funder names (not "
     "acronyms), grant numbers in square brackets, agencies separated by semicolons, attribution "
     "as “to A.B.”, and ending with the mandatory “Funding for open access charge: …” line."),
]

# =============================================================================== APPLY
report_ok, report_fail = [], []

# Resolve every anchor to an lxml element reference BEFORE mutating anything. Text edits
# move the original wording into <w:delText>, which text_of() no longer sees, so a note
# anchor looked up afterwards would fail. Element references stay valid across all edits.
edit_targets, note_targets = [], []
for anchor, reps in EDITS:
    try:
        edit_targets.append((find_p(anchor), reps))
    except LookupError as exc:
        report_fail.append(f"EDIT-ANCHOR  {exc}")
for anchor, text in NOTES:
    try:
        note_targets.append((find_p(anchor, pool=BODY_P), text))
    except LookupError as exc:
        report_fail.append(f"NOTE-ANCHOR  {exc}")
try:
    first_methods_p = find_p("We assembled the largest possible set of publicly available cohorts",
                             pool=BODY_P)
except LookupError as exc:
    raise SystemExit(f"cannot anchor the document-level notes: {exc}")

for p, reps in edit_targets:
    for old, status in safe_tracked_replace(p, reps):
        (report_ok if status == "ok" else report_fail).append(f"{status:9s} {old[:70]!r}")

# group consecutive notes on the same paragraph so they stay in order
from itertools import groupby
for p, group in groupby(note_targets, key=lambda t: t[0]):
    insert_after(p, [note_paragraph(t[1], label="[REVIEWER NOTE] ") for t in group])

# ------------------------------------------------------------------ document-level notes
insert_after(first_methods_p, [note_paragraph(t, label="[REVIEWER NOTE] ") for t in [
    "DOCUMENT FORMATTING (NAR Part 1): the manuscript is not in the NAR November-2025 template. "
    "Measured: page 21.59 × 27.94 cm (US Letter, should be A4 210 × 297 mm); Normal style is Times "
    "New Roman with no explicit size, line spacing 1.0 and no paragraph spacing (template is 11 pt, "
    "1.15 spacing, ~10 pt after); there is no header or footer part in the file at all, so there "
    "are no page numbers; and continuous line numbers, which NAR recommends for the review copy, "
    "are absent. Please move the text into the template and add page and line numbers.",
    "LANGUAGE VARIANT: the manuscript mixes British and American spelling — neighbor 19 / "
    "neighbour 4, centre 6 / center 4, colour 2 / color 51, artefact 1 / artifact 1, labelled 1, "
    "tSNE 53 / t-SNE 3. The title uses “centre” while the Abstract uses “tumor”. NAR accepts either "
    "variant but requires internal consistency; this is a single global decision that you should "
    "make and apply once (I have not auto-changed it). Please also standardise on “t-SNE”, which "
    "your own alt-text already uses.",
    "ABBREVIATION — PLEASE RECONSIDER “PCR”: throughout this manuscript PCR denotes principal "
    "component regression, but in a molecular-biology journal PCR means polymerase chain reaction. "
    "This is a genuine comprehension hazard rather than a stylistic point. Consider “PCReg” or "
    "“PC regression”. It occurs roughly 30 times, so I have left the choice to you. Also not "
    "defined at first use: PCA, UMAP, KNN, DSC, cLISI, iLISI, TPM, AUC, PBMC, GEO, AWS/S3; and "
    "FSQN and QN are used in Table 1's strategy descriptions before Table 3 defines them.",
    "FIGURE FILES (NAR Part 6) — measured from the submitted PDFs. (1) All 37 figures exceed NAR's "
    "maximum print size (17.35 × 23.35 cm) and require scaling by 0.44–0.67; after scaling, 100% of "
    "the text is below 5 pt in Figure 3 and Supplementary Figures 2–4, 81% in Supplementary "
    "Figure 7 (median 3.0 pt), 49% in Extended Figure 2, 27% in Figure 2 and 22% in Figure 6. Even "
    "the best figures sit at 5.2–6.7 pt. Please re-lay out for a 17.35 cm canvas rather than "
    "scaling down. (2) Every figure PDF uses Type 3 fonts with no embedded font file, so fonts "
    "cannot be verified, text extraction is corrupted (Figure 1's “log₂(x+1)” extracts as "
    "“log‡(x+1)”) and screen readers cannot read the figures — re-export with "
    "matplotlib.rcParams[\"pdf.fonttype\"] = 42 and with fonts embedded from Figma. (3) All figures "
    "are RGB; NAR asks for CMYK. (4) Figure 3 is also supplied as JPG, which NAR advises against, "
    "at ~288 dpi (below the 300 dpi minimum); Figures 4 and 5 are supplied as both PDF and PNG and "
    "the two versions have different aspect ratios, so at least one of each pair is stale. (5) The "
    "Graphical Abstract is 267 × 103 mm (ratio 2.59; NAR specifies 5:2 = 2.50), its smallest text "
    "is 9.3 pt against a 12 pt floor, and its t-SNE panels appear to be reused from Figures 4/5 — "
    "NAR requires the Graphical Abstract not to reproduce any main or supplementary figure. Please "
    "also confirm the provenance of its icons (a BioRender licence and acknowledgement would be "
    "required if they came from there).",
]])

# ------------------------------------------------------------------ save
doc.save(str(DST))

n_notes = len([p for p in doc.element.body.iter(qn("w:p"))
               if "[REVIEWER NOTE]" in "".join(t.text or "" for t in p.findall(".//" + qn("w:t")))])
print(f"applied edits : {len(report_ok)}")
print(f"notes inserted: {n_notes}")
if report_fail:
    print(f"\nPROBLEMS ({len(report_fail)}):")
    for line in report_fail:
        print("  ", line)
else:
    print("\nno failed anchors or unsafe replacements")
print(f"\nwrote {DST}")
