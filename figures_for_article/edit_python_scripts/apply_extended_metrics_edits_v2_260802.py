#!/usr/bin/env python
"""Full language + numerical pass on `Harmonization_metrics_extended.docx` (2026-08-02, v2).

This script supersedes `apply_extended_metrics_edits_260802.py`. It runs from the *original*
document, so it also re-applies that pass's figure renumbering; do not chain the two.

Scope, as requested
-------------------
1. **Every number recomputed** on the same 2,234-approach analysis set used for the main
   article, and replaced where the manuscript value did not reproduce.
2. **Language and grammar** raised to scientific-prose standard throughout.
3. **A new closing section**, "Summary of metric trends", appended as a tracked insertion.
4. **Figure renumbering** carried over from the first pass (document numbering was three
   behind the delivered `Extended Figure *.pdf` artwork).

Which metric table
------------------
Daniil named `metrics_comprehensive_260527.csv`. That snapshot cannot reproduce the article:
it predates strategies I, J and K (11 strategies only), and — decisively — it was computed on
a different set of prepared matrices. Merging it against the deposited `Supplementary File 3`
on (strat, imp, method, post_rm) gives 1,822 shared rows and **0 of 66 numeric columns
agreeing**; `n_samples` and `n_genes` themselves differ by up to 850 and 1,309. The same merge
against `metrics_comprehensive_260609.csv` gives **79 of 79 columns agreeing exactly**.

The recomputation therefore uses `metrics_comprehensive_260609.csv` through
`figures_helpers.load_metrics_data()` — the very function the article's figure notebook calls.
It reproduces the analysis set exactly: 2,234 rows, 31 methods, 14 strategies, 87 scoring
metrics, 15 clustermap best approaches. Where 260527 and 260609 overlap, 260609 is the later
and internally consistent snapshot, so no information from 260527 is lost.

Statistical conventions used for the replacement values
-------------------------------------------------------
* "median"/"MAD" are over individual approaches; MAD is the plain (unscaled) median absolute
  deviation, matching the manuscript's usage.
* Per-method and per-strategy summaries in the heat-map paragraphs are **means over runs**,
  matching the figures, which average across imputations and post-removal variants.
* "Best group" = the 15 clustermap-selected approaches (`top_ids`, post_rm = False).
* Percentage-point differences between imputations are stated as such, not as ratios.

Why `safe_tracked_replace` and not `tracked_replace`
---------------------------------------------------
`safe_tracked_replace` edits only runs that are direct children of the paragraph, and after
each call the replaced text moves into `w:del`, which the next search no longer sees. That
makes a left-to-right sweep of overlapping figure references collision-proof.

Output: Harmonization_metrics_extended_260802_v2.docx
"""
import os
import re
import sys

import docx

sys.path.insert(0, os.path.expanduser("~/FL_harmonization/.claude/skills"))
from nar_review_tools import safe_tracked_replace  # noqa: E402
from word_rewrite_trackchanges import (  # noqa: E402
    heading,
    ins_paragraph,
    set_revision_identity,
)

SRC = "Harmonization_metrics_extended.docx"
DST = "Harmonization_metrics_extended_260802_v2.docx"

set_revision_identity("Claude (metrics review 2026-08-02)", "2026-08-02T00:00:00Z")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


# ── figure renumbering ────────────────────────────────────────────────────────
REF = re.compile(r"(Supplementary |Extended )?(Figures?)\s+(\d+)")

SPECIALS = [
    ("Figures 6-8", "Extended Figures 1-3"),
    ("Extended Figure 5G, 5H, 5K, 5L", "Extended Figure 8G, 8H, 8K, 8L"),
    ("Extended Figure 4 and 5", "Extended Figure 7 and 8"),
    # A trailing panel reference that repeats the figure number without the word "Figure":
    # the generic sweep sees "Extended Figure 2D" but not the bare "2E" beside it.
    ("Extended Figure 2D, 2E", "Extended Figure 5D, 5E"),
]


def renumber(token_prefix, word, number):
    """Return the replacement figure number, or None if the reference is unchanged."""
    if token_prefix == "Supplementary ":
        return None  # points at the main article's supplementary figures
    if token_prefix == "Extended ":
        return number + 3
    if number in (6, 7, 8):
        return number - 5  # the section moved out of the main manuscript
    return None  # Figure 1-5 = main article figures, untouched


def _replacement_for(prefix, word, num):
    """The rewritten reference, or None when the reference is left alone."""
    new_num = renumber(prefix, word, num)
    if new_num is None:
        return None
    return f"Extended {word} {new_num}" if not prefix else f"{prefix}{word} {new_num}"


def figure_edits(text):
    """Ordered (search, replace) pairs for every figure reference in one paragraph.

    The bare reference is *not* a safe search key. "Figure 6" is a substring of
    "Supplementary Figure 6", which must stay untouched because it points at the main
    article, so a naive key rewrites the wrong reference and leaves a real one behind. Each
    key is therefore grown leftwards until it is the first match in the text that
    `safe_tracked_replace` will still be able to see — that is, in the text with the spans
    consumed by earlier pairs blanked out.
    """
    out = []
    shadow = text  # spans already claimed by an earlier pair, blanked
    for m in REF.finditer(text):
        prefix, word, num = m.group(1) or "", m.group(2), int(m.group(3))
        new_ref = _replacement_for(prefix, word, num)
        if new_ref is None:
            continue
        start, end = m.span()
        for pad in range(0, min(start, 40) + 1):
            key = text[start - pad:end]
            if shadow.find(key) == start - pad:
                break
        else:
            raise SystemExit(f"cannot disambiguate figure reference {m.group(0)!r}")
        out.append((key, text[start - pad:start] + new_ref))
        shadow = shadow[:start - pad] + "\0" * (end - start + pad) + shadow[end:]
    return out


def renum_text(text):
    """Renumber the figure references inside a replacement string.

    Every replacement below is written against the document's *original* numbering, so that
    it can be read side by side with the source. Running it through the same renumbering the
    sweep applies keeps the two consistent. It must be applied to the replacement text only:
    the search text has to match the document as it stands.

    This also has to happen before the sweep rather than during it. Replacement text lands
    inside `w:ins`, which `safe_tracked_replace` deliberately cannot see, so the sweep would
    never reach it.
    """
    for old, new in SPECIALS:
        text = text.replace(old, new)

    def sub(m):
        new_ref = _replacement_for(m.group(1) or "", m.group(2), int(m.group(3)))
        return m.group(0) if new_ref is None else new_ref

    return REF.sub(sub, text)


# ── numerical corrections ─────────────────────────────────────────────────────
# Each entry: (anchor substring identifying one paragraph, [(old, new), ...]).
# Values that already reproduced exactly are deliberately left untouched; the comment
# above each block records what was checked.
NUMBER_EDITS = [
    # Spearman r = -0.1592, p = 3.73e-14 both reproduce. The CI upper bound is a typo
    # (bootstrap, 2,000 resamples, seed 42: -0.203 to -0.114). Best-vs-rest medians and MADs
    # reproduce to three decimals; the biology comparison p = 0.686 was not stated.
    ("weak negative correlation (Spearman r = -0.159",
     [("95% CI -0.21, -11", "95% CI -0.20 to -0.11"),
      ("(median 0.871 and MAD 0.122 by batch, median 0.820 and MAD 0.063 by biology), albeit "
       "only the batch difference between the best and the rest approaches was significant "
       "(two-sided Mann-Whitney p = 0.0063)",
       "(median 0.871 and MAD 0.122 by batch against a median of 0.626 for the remaining "
       "approaches; median 0.820 and MAD 0.063 by biology against 0.802). Only the batch "
       "difference between the best approaches and the rest was significant (two-sided "
       "Mann-Whitney U test, p = 6.3 * 10-3 for batch and p = 0.69 for biology)")]),

    # PCReg Diagnosis_cell_type_unified for 05_combat + 29_combat_ref over strategies
    # A, B, I, J and E1-E3: 0.357-0.823, median 0.568, against 0.778 for all other methods
    # on the same strategies. The quoted upper bound of 0.465 is not in the data.
    ("05_combat and 29_combat_ref harmonization showed better separation",
     [("(Figure 6A, PCReg 0.357 – 0.465)",
       "(Figure 6A; median PCReg Diagnosis_cell_type_unified 0.568 over these strategies "
       "against 0.778 for the remaining methods, full range 0.357-0.823)")]),

    # 33_amdbnorm is exactly 1.0000 in all 14 runs; 13_fsmvn has a median of 1.0000 but a
    # minimum of 0.9967, so it is not pinned.
    ("33_amdbnorm and 13_fsmvn both have",
     [("33_amdbnorm and 13_fsmvn both have pcr_RNA_BATCH of exactly 1.0000 in every run — a "
       "global metric pinned at its theoretical optimum, but they were again not selected",
       "33_amdbnorm returns a PCReg RNA_BATCH of exactly 1.0000 in all 14 of its runs, and "
       "13_fsmvn reaches a median of 1.0000 (range 0.9967-1.0000) — a global metric pinned at "
       "its theoretical optimum — yet neither was selected")]),

    # n_diagnosis_groups: four in every malignant-only run and in 163 of 164 FFPE-only runs.
    ("Notably, the malignant only and FFPE only strategies did not have normal B cells",
     [("so their number of unique classes by Diagnosis_cell_type_unified was only 4",
       "so their number of unique classes by Diagnosis_cell_type_unified was only four (four "
       "in every malignant-only run and in 163 of the 164 FFPE-only runs)")]),

    # Maximum mean R2 over all ten PCs for the five top-PCReg methods is 0.0024, at
    # 07_pycombat PC2, not 0.0013 at 28_npn PC1. Methods whose PC1 R2 is lower than the
    # maximum over PC2-PC10: 19 of 31. Mean PC2 variance for 01_raw is 9.73%.
    ("PCA variance explained by batch (R2 by RNA_BATCH) showed a more complicated pattern",
     [("(0.0013 at maximum for 28_npn PC1)", "(0.0024 at maximum, for 07_pycombat PC2)"),
      ("14 methods out of 31 showed a lower RNA_BATCH R2 for the first PC than for the "
       "subsequent PCs",
       "19 of the 31 methods showed a lower RNA_BATCH R2 for the first PC than for the "
       "subsequent PCs"),
      ("resulted in 64.8 and 65.9% R2 RNA_BATCH and 73.5 and 9.8% of total variance",
       "resulted in 64.8 and 65.9% R2 RNA_BATCH and 73.5 and 9.7% of total variance")]),

    # Mean PCReg RNA_BATCH > mean PCReg Diagnosis_cell_type_unified for 12 of 31 methods.
    # Five methods average 0.999 or above, but only 33_amdbnorm attains exactly 1.0000.
    ("10 out of 31 harmonization methods showed better PCA overlap",
     [("10 out of 31 harmonization methods showed better PCA overlap of batches than biology",
       "12 of the 31 harmonization methods showed better PCA overlap of batches than biology"),
      ("showed maximum possible PCReg values of 1, indicating complete overlap of batches in "
       "PCA space",
       "showed mean PCReg values of 0.999 or above, with 33_amdbnorm at exactly 1.0000, "
       "indicating essentially complete overlap of batches in PCA space")]),

    # Imputation: over the eleven lowest-PCReg methods the means are strict 0.370, KNN 0.390,
    # softimpute 0.438; softimpute exceeds KNN by 1.7-9.7 pp (mean 4.8 pp).
    ("As a next step of global metrics analysis, we compared PCReg RNA_BATCH by imputations",
     [("KNN and strict approach were indistinguishable, whereas Softimpute had 7-10% better "
       "performance for the 11 lowest PCReg methods",
       "Strict imputation was marginally poorer than KNN (mean PCReg RNA_BATCH 0.370 against "
       "0.390 over the affected methods), whereas softimpute exceeded KNN by 1.7-9.7 "
       "percentage points (mean 4.8) for the 11 lowest-PCReg methods"),
      ("(the worst method by PCReg RNA_BATCH.", "(the worst method by PCReg RNA_BATCH)."),
      ("In the C strategy, all methods lead to PCReg RNA_BATCH above 0.62. G had lower limit "
       "of 0.55, and H had this limit at the level of 0.4.",
       "In the C strategy every method reached a mean PCReg RNA_BATCH of at least 0.76; the "
       "corresponding floors were 0.72 for G and 0.46 for H."),
      ("0.77 in G, 0.6 in H, compared to 0.84 averaged",
       "0.76 in G and 0.58 in H, against 0.83 averaged over all strategies"),
      ("In the K strategy it had 0.11 PCReg RNA_BATCH, indicating that FSQN is not applicable "
       "for FFPE datasets.",
       "In the K strategy it fell to 0.08, and in the microarray-only strategy F to 0.30, "
       "indicating that FSQN is not applicable to FFPE datasets."),
      ("The only visible difference was 22_tmm and 25_angel inverse order: the former had "
       "higher PCReg RNA_BATCH with post-removal (0.83), the latter had better performance "
       "without post-removal (0.77).",
       "Post-removal raised the mean PCReg RNA_BATCH for 30 of the 31 methods, but the median "
       "shift was only 0.030. The largest gains were for 22_tmm (0.70 to 0.88) and 23_vst "
       "(0.70 to 0.83), and 12_scanorama was the only method for which post-removal lowered "
       "the metric (0.49 to 0.48).")]),

    # Strategy-level PC heat map: mean PC1 variance 30.4% (C) and 37.9% (best group); the
    # maximum is 66.0% (G). Mean PC1 R2 RNA_BATCH 0.288 (C) and 0.229 (best). Ten of the
    # fourteen strategies have a lower PC1 than PC2 R2.
    ("For all the batch removal strategies we also investigated batch-explained variance",
     [("lowest average percentage of variance explained by the first PC (20 and 22%, "
       "respectively)",
       "the lowest average percentage of variance explained by the first PC (30.4 and 37.9%, "
       "respectively)"),
      ("G strategy showed highest average percentage at the level of 50%",
       "The G strategy showed the highest average percentage, 66.0%"),
      ("started with 0.27 and 0.22, respectively", "started at 0.29 and 0.23, respectively"),
      ("8 out of 14 batch removal strategies had lower R2 RNA_BATCH for first PCs than the "
       "one for the second PC",
       "10 of the 14 batch removal strategies had a lower R2 RNA_BATCH for the first PC than "
       "for the second")]),

    # All 15 best approaches sit below the overall median DSC RNA_BATCH of 0.962; the four
    # MNN approaches (0.781-0.957) lie at the boundary, two orders of magnitude above the
    # FSQN R ones (0.0013-0.0098).
    ("Dispersion separability criterion (DSC) was selected",
     [("Interestingly, only 2 out of 15 clustermap best approaches were found in the lower "
       "half of the DSC RNA_BATCH log scale.",
       "All 15 clustermap best approaches fell below the overall median DSC RNA_BATCH of "
       "0.962, but the four MNN approaches (0.781-0.957) lay at the very boundary, two orders "
       "of magnitude above the FSQN R ones (0.0013-0.0098).")]),

    # 11_harmony tSNE centroid dispersion in J and K, and G post-removal PCReg medians.
    ("Among the non-linear global metrics, we visualized and studied tSNE centroid dispersion",
     [("showing an improved tSNE centroid dispersion: 0.55-0.75 compared to the expected 1.1 "
       "for K and 0.65 compared to the expected 1.0 for J",
       "showing an improved tSNE centroid dispersion: 0.55-0.78 against a K-wide median of "
       "0.87, and 0.62-0.68 against a J-wide median of 0.81"),
      ("we found no systematic shift except for the G strategy points that had 0.7-0.9 PCReg "
       "RNA_BATCH before post-removal and 0.9-1 PCReg after it",
       "we found no systematic shift except for the G strategy, whose median PCReg RNA_BATCH "
       "rose from 0.78 before post-removal to 0.88 after it"),
      ("ASW depended on PCReg in a noisier manner, with the K strategy showing the worst "
       "performance",
       "ASW depended on PCReg in a noisier manner, with the G and K strategies showing the "
       "worst performance (mean ASW RNA_BATCH 0.165 and 0.078 against -0.066 to -0.019 for "
       "the remaining strategies)"),
      ("located in the zone of -0.05 – 0.3 ASW but with the same high PCReg as the clustermap "
       "best approaches (PCReg 0.68 - 1)",
       "located in the zone of 0.02-0.34 ASW but with the same high PCReg as the clustermap "
       "best approaches (PCReg 0.65-1.00)"),
      ("02_median_scaling and 11_harmony were the top performing harmonization methods by ASW",
       "02_median_scaling and 33_amdbnorm were the top-performing harmonization methods by "
       "ASW (mean ASW RNA_BATCH -0.286 and -0.276)")]),

    # kBET distribution over the analysis set, and the composition of the high-kBET cloud in
    # the C strategy.
    ("There was a weak positive relationship between LISI and kBET acceptance rate",
     [("Among all 2,234 attempts, the vast majority achieved near-zero kBET acceptance rates",
       "Among all 2,234 attempts, 82.0% fell below a kBET acceptance rate of 0.01 and 97.0% "
       "below 0.10"),
      ("the C strategy was the highest one by kBET with a compact group of methods located "
       "between 0.6 and 1 kBET. But they had LISI below 1.4 and were not selected by the "
       "integrative clustermap.",
       "the C strategy was the highest by kBET, with a compact group of 41 approaches drawn "
       "from 18 methods between 0.654 and 0.867. Their LISI values were nonetheless confined "
       "to 1.24-1.38, and none of these approaches was selected by the integrative "
       "clustermap.")]),

    # Missing-value metrics, as per-method means over the analysis set. 18 methods return no
    # missing value at all; 9 more lose 0.003-1.4% of samples; 4 lose 30.2-38.1%. For genes,
    # the same 18 return none, 10 lose 0.004-2.41%, 15_fsqn_py and 17_quantile lose 13.0 and
    # 16.2%, and 21_harmonizr loses every gene in 8 of the 14 strategies.
    ("All samples had all genes with defined expression values",
     [("for 19 out of 31 harmonization methods, regardless of the batch removal strategy "
       "used, 8 more methods had a minor percentage of 0.44 - 2.3% samples with at least one "
       "NA and 4 methods (20_shambhala, 26_xpn, 15_fsqn_py, 17_quantile) had 26-67% samples "
       "with at least one NA",
       "for 18 of the 31 harmonization methods, regardless of the batch removal strategy "
       "used; 9 further methods lost a minor share of 0.003-1.4% of samples to at least one "
       "missing value, and 4 methods (26_xpn, 20_shambhala, 15_fsqn_py and 17_quantile) lost "
       "30.2-38.1%"),
      ("the same 19 harmonization methods returned no NA at all, 11 more methods had "
       "0.05-33.6% genes with at least one sample with NA and the last one method "
       "21_harmonizr had all genes with NAs in 8 out of 14 batch removal strategies",
       "the same 18 harmonization methods returned no missing value at all, 10 further "
       "methods had 0.004-2.41% of genes carrying a missing value in at least one sample, "
       "15_fsqn_py and 17_quantile had 13.0 and 16.2%, and 21_harmonizr lost every gene in 8 "
       "of the 14 batch removal strategies")]),

    # The two quoted "maxima" for the ComBat-seq implementations are in fact their mean
    # standard deviations; the mean maxima are 1.46*10^11 and 2.76*10^8. The 99th percentiles
    # are also swapped between the two methods. 19, not 20, methods have a negative minimum.
    ("08_inmoose_combatseq and 06_combat_seq had outliers",
     [("08_inmoose_combatseq and 06_combat_seq had outliers with expression value above 1 "
       "million (5.08*108, 1.69 million, respectively), whereas their 99th percentiles were "
       "only 18.5 and 17.9, respectively.",
       "08_inmoose_combatseq and 06_combat_seq produced extreme outliers, with mean maximum "
       "expression of 1.46*1011 and 2.76*108 respectively, whereas their 99th percentiles "
       "were only 17.9 and 18.5."),
      ("Generally, 20 out of 31 harmonization methods had minimum gene expression value below "
       "zero (the lowest one -40.6 for 13_fsmvn)",
       "In total, 19 of the 31 harmonization methods had a mean minimum gene expression value "
       "below zero (the lowest being -40.6 for 13_fsmvn)")]),

    # Eight methods exceed 01_raw (mean 0.0266) on kBET RNA_BATCH; 22 fall below.
    # kBET PLATFORM_RNA is undefined for 22_tmm and 23_vst (single-platform strategy).
    ("Looking at kBET acceptance rate by different columns",
     [("we revealed that only three harmonization methods (22_tmm, 23_vst, 10_mnn) showed "
       "kBET acceptance rate RNA_BATCH better than in 01_raw and could be considered as "
       "‘good’, and 14 methods were poorer by this metric than 01_raw and can be therefore "
       "deemed ‘bad’",
       "we found that eight harmonization methods exceeded the kBET acceptance rate "
       "RNA_BATCH of 01_raw (mean 0.027) — 22_tmm (0.331), 23_vst (0.230), 10_mnn (0.044), "
       "04_sva and 36_explobatch (0.036 each), 13_fsmvn (0.035), 20_shambhala (0.029) and "
       "19_tdm (0.028) — although only 22_tmm and 23_vst did so by a wide margin, and the "
       "remaining 22 methods fell below 01_raw and can therefore be deemed ‘bad’"),
      ("kBET by PLATFORM_RNA was above 0.1 for all methods except 36_explobatch, indicating "
       "that good local mixing by platforms is abolished by the FF/FFPE distinction in 28 out "
       "of 31 methods in total",
       "kBET by PLATFORM_RNA was above 0.1 for 27 of the 29 methods for which it is defined "
       "(it is undefined for 22_tmm and 23_vst, which were run only on the single-platform C "
       "strategy); only 05_combat (0.100) and 36_explobatch (0.075) fell below, indicating "
       "that good local mixing by platform is abolished by the FF/FFPE distinction in almost "
       "every method"),
      ("the strategies C, H, J and G were considered as ‘good’ by the same criterion compared "
       "with the S0 strategy",
       "the strategies C, H, J and G were considered ‘good’ by the same criterion relative to "
       "S0 (mean kBET RNA_BATCH 0.205, 0.015, 0.012 and 0.011 against 0.0034 for S0)"),
      ("The strategies B, D and I had poor performance",
       "The strategies B, D and I had the poorest performance (0.0020, 0.0016 and 0.0004)")]),

    # Methods with at least five approaches above kBET 0.1, and the kBET behavior of
    # approaches whose PCReg is at the optimum.
    ("Finally, we compared PCReg and kBET acceptance rate by RNA_BATCH",
     [("where only 04_sva and 10_mnn methods had kBET above 0.1 for enough approaches (5 and "
       "more, Extended Figure 6E)",
       "where only 04_sva and 10_mnn had kBET above 0.1 for five or more approaches (10 and 9 "
       "respectively; the next method, 11_harmony, reached four; Extended Figure 6E)"),
      ("Interestingly, approaches that had PCReg 1.0 (07_pycombat, 03_limma, 13_fsmvn, "
       "14_qsmooth, 16_fsqn_r, 06_combat_seq) demonstrated kBET below 0.1.",
       "Interestingly, of the 198 approaches with a PCReg RNA_BATCH above 0.9999 — produced "
       "by 03_limma, 07_pycombat, 13_fsmvn, 21_harmonizr, 28_npn and 33_amdbnorm — 98.5% "
       "demonstrated kBET below 0.1.")]),

    # KS fraction significant: 01_raw (0.948) is the second-highest of the 31 methods, so 29
    # methods lie below it. Ten methods fall below 0.7; the best group averages 0.560.
    ("For distributional similarity we selected the metric KS fraction significant",
     [("15 out of 31 harmonization methods showed KS fraction significant for RNA_BATCH lower "
       "than this metric for 01_raw and were considered ‘good’ by this metric, as in the case "
       "for the clustermap best approaches",
       "29 of the 31 harmonization methods showed a KS fraction significant for RNA_BATCH "
       "lower than that of 01_raw (0.948, the second-highest value after 27_dwd at 0.965) and "
       "were considered ‘good’ by this metric, as were the clustermap best approaches (0.560)"),
      ("Interestingly, KS fraction significant was above 0.7 for all methods except 22_tmm "
       "and 23_vst, since they were applied to RNA-seq only cohorts with lower between-cohort "
       "differences. This fact indicates that even for the best harmonization by RNA_BATCH "
       "there are still 70-80% cohorts that have significant differences in gene expression "
       "profiles between them.",
       "The metric fell below 0.7 for only ten methods, ranging from 28_npn (0.173) and "
       "26_xpn (0.217) to 03_limma (0.691), and remained above 0.7 for the other 21. Even the "
       "clustermap best approaches left 56.0% of cohort pairs with significant differences in "
       "gene expression profile, so convergence of distributions is never complete.")]),

    # Graph connectivity of the best approaches, and the D/K means.
    ("We then investigated the behavior of graph connectivity",
     [("above 0.8 for PLATFORM_RNA and above 0.65 for Diagnosis_cell_type_unified",
       "0.832-1.000 for PLATFORM_RNA and 0.688-1.000 for Diagnosis_cell_type_unified"),
      ("they formed two compact clouds below the main peak, having 0.53 – 0.65 graph "
       "connectivity by Diagnosis_cell_type_unified",
       "they formed two compact clouds below the main peak, with mean graph connectivity by "
       "Diagnosis_cell_type_unified of 0.646 for D and 0.727 for K against 0.799-0.854 for "
       "the remaining strategies")]),

    # Distance ratio: best approaches 0.845-1.032 (median 0.914) against 0.757 overall.
    # 27_dwd, not 11_harmony, is the poorest method.
    ("As an additional metric of global distance separation",
     [("the clustermap best approaches located at the right side of the plot having dist "
       "ratio RNA_BATCH above 0.8 and no shift by dist ratio Diagnosis_cell_type_unified",
       "the clustermap best approaches lay at the right of the plot, with a distance ratio "
       "RNA_BATCH of 0.845-1.032 (median 0.914 against 0.757 for the full set) and no shift "
       "in distance ratio by Diagnosis_cell_type_unified"),
      ("14_qsmooth, 11_harmony and 19_tdm had the poorest performance by RNA_BATCH distance "
       "ratio.",
       "27_dwd (mean 0.508) and 14_qsmooth (0.531) had the poorest performance by RNA_BATCH "
       "distance ratio, both below no harmonization at all (01_raw, 0.566)."),
      ("with S0 and K having higher distance ratio by biology (less biology preservation, "
       "ratio 0.8 – 1.1) and J having it lower (0.5 – 0.8), which could be explained by lower "
       "biological group size in the J (FF only) strategy",
       "with D, S0 and K having the highest mean distance ratio by biology (0.931, 0.921 and "
       "0.912, that is, the least biology preservation) and G and J the lowest (0.756 and "
       "0.760), which for J (FF only) could be explained by its smaller biological groups")]),

    # Watermelon score by batch columns: C is second-lowest after J; G is the highest.
    ("The next step of other metrics comparison was the Watermelon (WM) score analysis",
     [("The C strategy had lowest WM by batch (0.12-0.25), and G strategy had again the "
       "highest batch WM (0.4-0.5).",
       "The C strategy had among the lowest mean Watermelon scores by batch columns (0.335, "
       "fifth to ninety-fifth percentile 0.213-0.392), second only to J (0.320), whereas G "
       "again had the highest (0.434, 0.372-0.471).")]),

    # Harshness panel B: low harshness gives the lowest PCReg by biology in 7 strategies.
    ("In the case of PCReg RNA_BATCH",
     [("in 8 strategies low harshness showed the lowest metric (best performance)",
       "in 7 strategies low harshness showed the lowest metric (best performance)")]),

    # Harshness panel F: the worst level is medium in 10 strategies and low in 4.
    ("As a final part of the methods harshness comparison",
     [("and 5 strategies had the worst performance in low harshness methods, and in 9 cases "
       "the worst behavior was observed for medium harshness methods",
       "4 strategies had the worst performance for low harshness methods, and in the "
       "remaining 10 the worst behavior was observed for medium harshness methods")]),

    # Composite score: best group 0.602, C 0.578. Metric-type contributions to the best
    # group: global distance 0.360, local neighborhood 0.109. Local contribution by
    # strategy: C 0.095, J 0.064, remaining eleven 0.047-0.052, G lowest at 0.037.
    ("The group of clustermap best approaches was indeed the best by composite score",
     [("having it at the level of 0.6 (Extended Figure 9A), whereas the next strategy C had "
       "the composite score 0.57",
       "reaching 0.602 (Extended Figure 9A), whereas the next-best strategy, C, reached 0.578"),
      ("Global distance metrics were the most numerous and therefore contributed 0.35 of the "
       "total score of the best group",
       "Global distance metrics were the most numerous (47 of the 87 scoring metrics) and "
       "therefore contributed 0.360 of the total score of the best group"),
      ("the local neighborhood contributed only 0.12 total score in the best group but they "
       "heavily differentiated the strategies: C had it 0.9, the next one J had it 0.6 and "
       "the rest 11 strategies showed it at the level of 0.4-0.5 without significant "
       "differences, with the worst one G having the local score 0.3",
       "the local neighborhood metrics contributed only 0.109 to the total score of the best "
       "group, yet they separated the strategies most sharply: C reached 0.095 and J 0.064, "
       "the remaining eleven strategies clustered between 0.047 and 0.052 without appreciable "
       "differences, and G was lowest at 0.037")]),

    # Local contributions of the third to fifth methods.
    ("The pattern of metric type impact by harmonization methods was more complicated",
     [("with gradual decrease of local composite impact from 0.1 to 0.7 (in 28_npn) and then "
       "raising to 0.11 in 10_mnn, accompanied with the decrease of global and distributional "
       "performance",
       "the local contribution falling from 0.083 in 33_amdbnorm to 0.072 in 28_npn and then "
       "rising to 0.106 in 10_mnn, whose gain in local mixing was offset by lower global "
       "(0.343 against 0.356-0.358) and distributional (0.065 against 0.078-0.084) "
       "contributions")]),

    # Metric-group spreads, expressed as max-min of the group contribution across strategies
    # and across methods.
    ("Comparison of the metrics computational groups revealed",
     [("did not confer difference by batch removal strategies (Extended Figure 9C) and "
       "introduced a minor impact of 0.02 total score between the first 15 and the rest "
       "methods (Extended Figure 9D)",
       "varied little across batch removal strategies (a spread of 0.017 between the highest "
       "and lowest strategy, Extended Figure 9C) and introduced a minor spread of 0.030 "
       "across harmonization methods (Extended Figure 9D)"),
      ("and they differentiated significantly the C strategy against the rest ones (by 0.04 "
       "total score) and the top 12 methods (except 25_angel) versus the rest ones (by 0.03 "
       "total score)",
       "and they separated the C strategy from the rest most strongly (spreads of 0.043 and "
       "0.039 across strategies) and likewise separated the leading methods from the rest "
       "(spreads of 0.049 and 0.054 across methods)"),
      ("and the rest three groups (graph connectivity, distributional similarity, pairwise "
       "Euclidean distance) added 0.04 of the total score between the top 1/3 and the bottom "
       "1/3 of the harmonization methods and batch removal strategies",
       "and the remaining three groups contributed intermediate spreads across methods: 0.036 "
       "for distributional similarity, 0.022 for graph connectivity and 0.019 for pairwise "
       "Euclidean distance")]),

    # Biology columns account for 18 of the 87 scoring metrics.
    ("Finally, we investigated the impact of metrics calculated by different annotation "
     "columns",
     [("and in total they comprised a quarter of the metrics equally weighted average",
       "and in total they comprised 18 of the 87 scoring metrics, about a fifth of the "
       "equally weighted average")]),

    # Local metrics: 22 of 87 columns, 8.1-18.1% of the composite. Batch columns: 57 of 87
    # columns, 60.7-67.4% of the composite.
    ("Taken together, the metrics of local type were the most important",
     [("despite they comprised only 10-15% of the total score. Batch related metrics "
       "comprised ¾ of it and the biology ones did not differ between the good and the bad "
       "harmonization methods or batch removal strategy.",
       "even though, at 22 of the 87 scoring metrics, they accounted for only 8.1-18.1% of "
       "the composite. Batch-related metrics supplied 57 of the 87 metrics and 60.7-67.4% of "
       "the composite, while the biology metrics barely separated the good from the bad "
       "harmonization methods or batch removal strategies (a spread of 0.053 across "
       "strategies against 0.122 for the batch metrics).")]),

    # Composite tail: 150 of 2,234 approaches (6.7%) exceed 0.6, and 9 of the 15 best
    # approaches are among them.
    ("We sorted and visualized all the approaches by their composite score",
     [("with 10/15 clustermap best approaches residing it it",
       "containing 150 of the 2,234 approaches (6.7%), 9 of the 15 clustermap best approaches "
       "among them"),
      ("a tiny minority of harmonization approaches (1-5%) are promising",
       "a small minority of harmonization approaches (under 7%) are promising")]),
]


# ── language corrections ──────────────────────────────────────────────────────
# Grammar, register and terminology, brought to scientific-prose standard.
LANGUAGE_EDITS = [
    ("On the clustermaps in Figure 3 and Supplementary Figure 7 we observed a trade-off",
     [("To deeply investigate the root cause of this trend, we analyzed harmonization metrics "
       "by group, harmonization method and batch removal strategy.",
       "To establish the origin of this trend, we analyzed the harmonization metrics by "
       "metric group, harmonization method and batch removal strategy."),
      ("we treated metrics for clustermap best approaches (Figure 3) as a separate group",
       "we treated the metrics of the clustermap-selected best approaches (Figure 3) as a "
       "separate group")]),

    ("For the global PCA-based metrics we selected Principal Component Regression",
     [("as the most unbiased one", "as the least biased of them"),
      ("We visualized its distribution for the main batch column RNA_BATCH in comparison with "
       "the same metric for the biology column Diagnosis_cell_type_unified.",
       "We compared its distribution for the principal batch column, RNA_BATCH, with that for "
       "the biology column Diagnosis_cell_type_unified."),
      ("The clustermap-selected best approaches located in the upper-right quadrant of the "
       "plot, displaying high overlapping of both batches and biology",
       "The clustermap-selected best approaches occupied the upper-right quadrant of the "
       "plot, showing extensive overlap of both batches and biological groups")]),

    ("05_combat and 29_combat_ref harmonization showed better separation",
     [("It should also be noted that 33_amdbnorm completed only 14 of 84 possible runs being "
       "terminated by 3 hours timeout",
       "It should also be noted that 33_amdbnorm completed only 14 of its 84 possible runs, "
       "the remainder being terminated by the three-hour timeout"),
      ("whereas RNA-seq only had highest average ability to correct batch variation",
       "whereas the RNA-seq-only strategy had the greatest average ability to correct batch "
       "variation"),
      ("FF only had relatively lower batch and biology groups overlapping in the PCA space",
       "The FF-only strategy showed comparatively less overlap of both batch and biology "
       "groups in PCA space"),
      ("Interestingly, harmonization methods formed diagonal lines moving from the left-top "
       "to right-bottom corners of the plot, with those close to the PCReg RNA_BATCH = 1 "
       "vertical line being vertical too",
       "Harmonization methods formed diagonal bands running from the upper left to the lower "
       "right of the plot; those close to the PCReg RNA_BATCH = 1 boundary became vertical")]),

    ("It should be noted that S0 01_raw dataset",
     [("i.e. the full dataset of 7174 samples without harmonization",
       "that is, the full dataset of 7,174 samples and 3,447 genes without harmonization")]),

    ("To deeply investigate the PC-level variation",
     [("To deeply investigate the PC-level variation, we calculated percentage of variance "
       "explained by each of the first 10 PCs, as well as R2 explained by RNA_BATCH for each "
       "of them.",
       "To resolve the variation at the level of individual components, we calculated the "
       "percentage of variance explained by each of the first ten PCs together with the R2 "
       "explained by RNA_BATCH for each of them."),
      ("Additional 8 methods", "A further eight methods"),
      ("and the sameslow decay over PCs", "and the same slow decay over PCs"),
      ("The rest 18 methods resulted in a large proportion of variance explained by first PC",
       "The remaining 18 methods concentrated a large proportion of the variance in the first "
       "PC")]),

    ("PCA variance explained by batch (R2 by RNA_BATCH) showed a more complicated pattern",
     [("implying that the batches almost completely overlapped each other on the PCA space",
       "implying that the batches almost completely overlapped in PCA space"),
      ("Yet local mixing for these approaches was of poor quality",
       "Local mixing for these approaches was nonetheless poor"),
      ("For the 5 methods that demonstrated smooth decay of percentage variance explained by "
       "PCs, four (with the exception of 20_shambhala) maximum RNA_BATCH R2 was for the "
       "non-first PC.",
       "Of the five methods that showed a smooth decay in the percentage of variance "
       "explained, four (all but 20_shambhala) had their maximum RNA_BATCH R2 at a component "
       "other than the first."),
      ("Such a pattern could indicate that these methods do not abolish batch-level variance "
       "but rather hide it in lower rank PCs",
       "This pattern suggests that these methods do not abolish batch-level variance but "
       "displace it into lower-ranked PCs")]),

    ("We then investigated performance of the local mixing (local neighborhood) metrics",
     [("We then investigated performance of the local mixing (local neighborhood) metrics",
       "We next examined the performance of the local mixing (local neighborhood) metrics"),
      ("as it was scattered along the entire local metrics cluster in Supplementary Figure 7 "
       "and visualized it for the same biology and batch column",
       "because it was distributed across the whole local-metric cluster in Supplementary "
       "Figure 7, and visualized it for the same biology and batch columns"),
      ("The clustermap best approaches located in the right half of the scatterplots, "
       "demonstrating higher than average batch local mixing but visually no trend by local "
       "preservation of biological groups",
       "The clustermap best approaches occupied the right half of the scatterplots, showing "
       "higher than average local batch mixing but no visible trend in the local preservation "
       "of biological groups"),
      ("as was previously showed on Figure 3", "as shown earlier in Figure 3"),
      ("Batch removal strategies formed isolated curved structures located in layers in order "
       "resembling the PCReg by biology order in Figure 6B",
       "Batch removal strategies formed separate curved bands, layered in an order resembling "
       "that of PCReg by biology in Figure 6B"),
      ("We also observed positive correlation of biology mixing with the batch one",
       "We also observed a positive correlation between biology and batch mixing")]),

    ("As an additional local mixing metric, we visualized tSNE entropy",
     [("the one that by definition closely correlates with different batches mixing at tSNE "
       "plot",
       "which by construction tracks the mixing of batches in the tSNE embedding"),
      # The duplicated "10_mnn was the best approach" clause is already a tracked deletion
      # by the author, so the visible text needs no further edit here.
      ("Among the batch removal strategies, FF only and RNA-seq only were the best ones "
       "(median 0.062 and 0.089, respectively), whereas the FFPE only and Affymetrix only "
       "were the worst approaches (median 0.011 and 0.015, respectively).",
       "Among the batch removal strategies, RNA-seq only and FF only were the best (median "
       "0.089 and 0.063, respectively), whereas FFPE only and Affymetrix only were the worst "
       "(median 0.011 and 0.015, respectively)."),
      ("Harmonization methods and batch removal strategies clearly separated into the low and "
       "high dispersion areas (peak values of 0.26 and 1.01, respectively), with the "
       "clustermap best approaches tending to locate at the border between these areas.",
       "Harmonization methods separated cleanly into low- and high-dispersion regions (method "
       "means ranging from 0.24 for 13_fsmvn to 1.00 for 27_dwd), and the clustermap best "
       "approaches tended to lie at the boundary between them."),
      ("Such a non-trivial pattern could indicate that tSNE centroids are poor harmonization "
       "quality measures as tSNE does not preserve global distance",
       "This pattern suggests that tSNE centroids are poor measures of harmonization quality, "
       "because tSNE does not preserve global distances")]),

    ("As a final part of the harmonization quality metrics comparison among the approaches",
     [("we visualized the selected metrics that fall outside the main global/local axis",
       "we examined the metrics that fall outside the main global/local axis"),
      ("To systematically test whether harmonization leads to convergence in gene expression "
       "distribution, we plotted mean D statistic of Kolmogorov-Smirnov test between randomly "
       "selected 1000 genes within batches versus mean between-batches (by RNA_BATCH) D "
       "statistics by the same 1000 genes",
       "To test systematically whether harmonization drives convergence of gene expression "
       "distributions, we plotted the mean Kolmogorov-Smirnov D statistic computed within "
       "batches over 1,000 randomly selected genes against the mean between-batch (RNA_BATCH) "
       "D statistic for the same 1,000 genes")]),

    ("The clustermap best approaches were in the lower half of the plot",
     [("showing high similarity of gene expression distributions for these best approaches "
       "within each batch group",
       "indicating closely similar gene expression distributions within each batch group"),
      ("Interestingly, different harmonization methods showed vertical lines of data points, "
       "implying that harmonization tools differ by their ability to transform different "
       "batch distributions to the same shape.",
       "Individual harmonization methods formed vertical bands of data points, implying that "
       "the tools differ in their ability to transform batch distributions to a common shape."),
      ("horizontal layers were formed with fixed within-batch mean D statistic",
       "horizontal layers formed at a fixed within-batch mean D statistic")]),

    ("We then compared percentage of samples and genes without NA",
     [("We then compared percentage of samples and genes without NA",
       "We then compared the percentage of samples and genes without missing values")]),

    ("The harmonization methods differed markedly in the expression range of their outputs",
     [("18_rank and 25_angel collapsed entire distribution to range between 0 and 1",
       "18_rank and 25_angel collapsed the entire distribution to the interval between 0 "
       "and 1"),
      ("All the rest methods were comparable with the standard RNA-seq log2 (transcripts per "
       "million, TPM) value range",
       "All remaining methods were comparable with the standard RNA-seq log2 (transcripts per "
       "million, TPM) range"),
      ("Compared to all harmonization approaches, the best ones showed higher uniformity in "
       "the expression profiles",
       "Relative to the full set of approaches, the best ones showed greater uniformity of "
       "expression profile"),
      ("MNN started with positive ones (1.61 to 2.44), and median expression was in the "
       "interval of 2.89 to 6.70, maximum one being in the interval 12.6 to 28.6.",
       "MNN started from positive values (1.61 to 2.44); across the fifteen best approaches "
       "the median expression lay between 2.63 and 6.70 and the maximum between 12.6 "
       "and 28.6."),
      ("This higher uniformity of best approaches is close to the typical log2(TPM) "
       "normalization distribution",
       "This greater uniformity brings the best approaches close to a typical log2(TPM) "
       "distribution")]),

    ("Among global metrics, we firstly analyzed Principal Component Regression",
     [("Among global metrics, we firstly analyzed Principal Component Regression",
       "Among the global metrics we first analyzed principal component regression"),
      ("that could indicate that harmonization method impacts more the PCA resolution of "
       "batches compared to biology compared to prior batch removal strategies",
       "which suggests that the harmonization method affects the PCA-level resolution of "
       "batches more than the prior batch removal strategy does")]),

    ("As a next step of global metrics analysis, we compared PCReg RNA_BATCH by imputations",
     [("Multiplatform strategies (S0, A, B, D, E1-E3, I) and FF only (J) had the methods "
       "performance as in the total plots by imputations",
       "The multiplatform strategies (S0, A, B, D, E1-E3, I) and FF only (J) reproduced the "
       "overall ordering of methods seen in the imputation plots"),
      ("Moreover, the 16_fsqn_r method had poorer performance than on average",
       "The 16_fsqn_r method also performed worse than its own average"),
      ("For additional check we visualized PCReg RNA_BATCH by harmonization methods and "
       "compared the values by post-removal",
       "As a further check we compared PCReg RNA_BATCH by harmonization method with and "
       "without post-removal")]),

    ("We defined PCReg metric in such a way that 1 is the best possible overlapping",
     [("We defined PCReg metric in such a way that 1 is the best possible overlapping in PCA "
       "space by a given column: the variance is not explained by this column at all.",
       "We defined the PCReg metric so that 1 denotes the best possible overlap in PCA space "
       "for a given column, that is, none of the variance is explained by that column."),
      ("Keeping in mind the fact that variance in unevenly distributed along the PCs",
       "Because the variance is unevenly distributed across the PCs"),
      ("As expected, we observed a strong negative relationship",
       "As expected, we observed a strong negative relationship between the two")]),

    ("For all the batch removal strategies we also investigated batch-explained variance",
     [("looking at percentage variance explained and R2 RNA_BATCH for each PC",
       "examining the percentage of variance explained and the R2 for RNA_BATCH at each PC"),
      ("presumably because the already quantile-normalized SOM cohort comprised the highest "
       "percentage of samples in this strategy compared to the rest ones",
       "presumably because the already quantile-normalized SOM cohort makes up a larger share "
       "of the samples in this strategy than in any other")]),

    ("As the last step of global metrics analysis, we compared PCReg by various columns",
     [("PLATFORM_RNA was a larger scale column compared to RNA_BATCH",
       "PLATFORM_RNA is a coarser annotation than RNA_BATCH"),
      ("with strategies the FFPE only and FF only strategies being closest to the 1:1 "
       "diagonal line",
       "with the FFPE-only and FF-only strategies lying closest to the 1:1 diagonal"),
      ("This can be explained by the fast that selecting FFPE only or FF only batches reduced "
       "the batch and platform classes to the 1:1 ratio",
       "This follows from the fact that selecting FFPE-only or FF-only batches reduces the "
       "batch and platform classes to a 1:1 correspondence"),
      ("Multi-batch PLATFROM_RNA column in the rest strategies explained less variance in PCA "
       "space compared to RNA_BATCH, hence these strategies are above the main 1:1 diagonal.",
       "In the remaining strategies the multi-batch PLATFORM_RNA column explained less "
       "variance in PCA space than RNA_BATCH, so these strategies lie above the 1:1 diagonal."),
      ("we observed the inversed pattern", "we observed the inverse pattern"),
      ("The clustermap best approaches were consentingly found in the best 1/3 part of the "
       "plots.",
       "The clustermap best approaches were consistently found in the best third of the "
       "plots.")]),

    ("Dispersion separability criterion (DSC) was selected",
     [("but it showed monotonous sigmoidal dependency on PCReg for the RNA_BATCH column",
       "but it showed a monotonic, sigmoidal dependence on PCReg for the RNA_BATCH column"),
      ("DCS by PLATFORM_RNA over RNA_BATCH dependency was again monotonous and linear in a "
       "log-scale (Extended Figure 3D) without any non-trivial effects as in the PCReg case",
       "The dependence of DSC by PLATFORM_RNA on DSC by RNA_BATCH was again monotonic and "
       "linear on a logarithmic scale (Extended Figure 3D), without the non-trivial "
       "structure seen for PCReg"),
      ("In a contrast, DSC COHORT_LABEL showed two clouds of points not explained by batch "
       "removal strategies (Extended Figure 3E), that could be presumable explained by "
       "harmonization methods.",
       "In contrast, DSC by COHORT_LABEL formed two clouds of points that were not explained "
       "by the batch removal strategy (Extended Figure 3E) and are more plausibly attributed "
       "to the harmonization method."),
      ("Such outliers can be explained by the fact that DSC is calculated as ratio of between "
       "group scatter to within group scatter, and ratio is vulnerable to outliers even under "
       "log-transformation.",
       "Such behavior follows from the definition of DSC as the ratio of between-group to "
       "within-group scatter, a quantity that remains sensitive to outliers even after "
       "log transformation.")]),

    ("Among the non-linear global metrics, we visualized and studied tSNE centroid dispersion",
     [("As expected, tSNE centroid dispersion negatively correlated with PCReg following a "
       "non-linear arc-like pattern.",
       "As expected, tSNE centroid dispersion correlated negatively with PCReg, following a "
       "non-linear, arc-shaped pattern."),
      ("Interestingly, a subgroup of 11_harmony approaches in J and K strategies deviated "
       "below the general trend",
       "A subgroup of 11_harmony approaches in the J and K strategies fell below the general "
       "trend"),
      ("This fact can be again attributed to the fact that the SOM cohort comprised "
       "approximately 800 out of 2801 samples processed with the GPL570 cohort in this "
       "strategy.",
       "This can again be attributed to the SOM cohort, which contributes roughly 800 of the "
       "2,801 GPL570 samples in this strategy."),
      ("This also means that post-removal of only one cohort does not significantly improve "
       "the harmonization performance for the majority of cases.",
       "It also means that removing a single cohort after harmonization does not appreciably "
       "improve performance in most cases.")]),

    ("Local neighborhood quality was assessed by kBET acceptance rate",
     [("We expected that the best approaches should mix batch labels in the local "
       "neighborhood of each sample while preserving local integrity of biological groups.",
       "We expected the best approaches to mix batch labels within the local neighborhood of "
       "each sample while preserving the local integrity of the biological groups.")]),

    ("LISI metrics (Local inverse Simpson's index) revealed 10_mnn",
     [("LISI metrics (Local inverse Simpson's index) revealed 10_mnn the top performing "
       "harmonization method by RNA_BATCH labels mixing",
       "The LISI metrics (local inverse Simpson's index) identified 10_mnn as the "
       "top-performing harmonization method for mixing RNA_BATCH labels"),
      ("The best approaches performed so well by LISI because they were selected in the "
       "relatively high local mixing clusters of the main clustermap, and visually confirmed "
       "by tSNE/UMAP plots to have good batch mixing while preserving the biology groups.",
       "The best approaches performed well by LISI because they were drawn from the "
       "high-local-mixing clusters of the main clustermap and were confirmed visually on "
       "tSNE and UMAP plots to mix batches while preserving the biological groups."),
      ("Among 31 methods in total, only 6 ones", "Of the 31 methods, only six")]),

    ("LISI metrics stratification by batch removal strategy revealed a supremacy",
     [("revealed a supremacy of the clustermap best approaches",
       "again placed the clustermap best approaches first"),
      ("J and S0 strategies followed it by LISI RNA_BATCH, but their biology local mixing "
       "(LISI Diagnosis_cell_type_unified) was higher than the batch ones.",
       "The J and S0 strategies followed on LISI RNA_BATCH, but their local biology mixing "
       "(LISI Diagnosis_cell_type_unified) exceeded their batch mixing."),
      ("We found that the best approaches occupied local peaks by batch but did not so with "
       "local valleys the biology, which reflects the subtle biological differences and the "
       "sharper technical ones in the current FL dataset.",
       "The best approaches occupied local peaks for batch but did not occupy the "
       "corresponding local minima for biology, which reflects the subtlety of the biological "
       "differences relative to the technical ones in this FL dataset.")]),

    ("There was a weak positive relationship between LISI and kBET acceptance rate",
     [("confirming that local neighborhood composition remained batch-biased after most "
       "harmonization methods even when global PCReg values were substantially reduced",
       "confirming that the composition of the local neighborhood remained batch-biased "
       "after most harmonization methods, even where the global PCReg had improved "
       "substantially"),
      ("Interestingly, other harmonization methods were also unevenly distributed along the "
       "kBET-LISI axis: 02_median_scaling had disproportionally high LISI and 25_angel was "
       "shifted towards the kBET direction, probably pointing at different modes of local "
       "batches mixing by harmonization method.",
       "Other harmonization methods were also unevenly distributed along the kBET-LISI axis: "
       "02_median_scaling had disproportionately high LISI, whereas 25_angel was shifted "
       "towards kBET, which points to distinct modes of local batch mixing between methods."),
      ("suggests that both modes really improve the batch correction performance",
       "suggests that both modes genuinely improve batch correction")]),

    ("Looking at kBET acceptance rate by different columns",
     [("whereas 22_tmm and 23_vst performed better because they were applied to the C "
       "strategy only, where all methods perform better because of RNA-seq platforms higher "
       "comparability",
       "whereas 22_tmm and 23_vst performed better only because they were applied to the C "
       "strategy alone, in which all methods benefit from the greater comparability of "
       "RNA-seq platforms"),
      ("indicating that minor batch removal or selecting malingnant only samples does not "
       "improve local mixing by batches",
       "indicating that removing a few batches, or selecting malignant samples only, does not "
       "improve local mixing of batches")]),

    ("We then investigated behavior of other local mixing metrics",
     [("We then investigated behavior of other local mixing metrics that highly impacted "
       "harmonization quality: tSNE and UMAP entropy.",
       "We then examined two further local mixing metrics that strongly influenced "
       "harmonization quality: tSNE and UMAP entropy."),
      ("By batch removal strategies we saw less differences",
       "Fewer differences were apparent between batch removal strategies")]),

    ("Generally, for local metrics we observed less harmonization methods",
     [("Generally, for local metrics we observed less harmonization methods performing at a "
       "‘good’ level (Extended Figure 4A) compared to the global ones (Extended Figure 1A), "
       "reflecting the fact that local mixing by batches is more challenging than their "
       "global overlapping at the PCA space.",
       "Overall, fewer harmonization methods reached a ‘good’ level on the local metrics "
       "(Extended Figure 4A) than on the global ones (Extended Figure 1A), reflecting the "
       "fact that mixing batches locally is harder than overlapping them globally in PCA "
       "space.")]),

    ("tSNE centroid dispersion is a natural complementary pair to tSNE entropy",
     [("tSNE centroid dispersion is a natural complementary pair to tSNE entropy: it "
       "quantifies separation of groups in the same embedding space as their local mixing by "
       "entropy.",
       "tSNE centroid dispersion is the natural complement to tSNE entropy: it quantifies the "
       "separation of groups in the same embedding in which entropy quantifies their local "
       "mixing."),
      ("whereas the rest harmonization methods separated into two dense clouds with "
       "approximately round shape",
       "whereas the remaining harmonization methods separated into two dense, approximately "
       "round clouds"),
      ("At a higher level, this pattern indicates that a given harmonization method can lead "
       "to good or bad batches overlapping in tSNE embeddings, but the precise composition of "
       "batches will govern how well they mix locally. Only MNN mixes batches well for most "
       "of the batch removal strategies. In other words, harmonization method cannot impact "
       "local mixing of batches except for these three methods.",
       "This indicates that a given harmonization method can produce either good or poor "
       "batch overlap in a tSNE embedding, but that the composition of the batches themselves "
       "governs how well they mix locally. Only MNN mixed batches well across most batch "
       "removal strategies; for the other methods, the choice of harmonization had little "
       "influence on local batch mixing.")]),

    ("As an additional check, we compared tSNE and UMAP centroid dispersion",
     [("we saw strong positive relationship and the same separation of harmonization methods "
       "in two clouds",
       "we found a strong positive relationship and the same separation of harmonization "
       "methods into two clouds"),
      ("indicating that local mixing was of higher priority compared to the global separation "
       "even in the case of non-linear embeddings",
       "indicating that local mixing took priority over global separation even for non-linear "
       "embeddings")]),

    ("We then compared LISI and kBET against PCReg as the main global metric",
     [("LISI by RNA_BATCH showed weakly positive relationship with PCReg",
       "LISI by RNA_BATCH showed a weakly positive relationship with PCReg"),
      ("Batch removal strategies demonstrated a layered structure (Extended Figure 6B) "
       "resembling the pattern of tSNE centroid dispersion and tSNE entropy albeit noisier",
       "Batch removal strategies showed a layered structure (Extended Figure 6B) resembling, "
       "though noisier than, the pattern seen for tSNE centroid dispersion and tSNE entropy")]),

    ("The analogous comparison of LISI and PCReg by the main biology column",
     [("revealed more noise but general weak negative relationship",
       "was noisier but revealed a weak negative relationship overall"),
      ("indicating that biology preservation was secondary criterion compared to the batch "
       "mixing",
       "indicating that biology preservation was secondary to batch mixing"),
      ("While the distribution of harmonization methods by LISI and PCReg by "
       "Diagnosis_cell_type_unified was apparently random",
       "Whereas the distribution of harmonization methods by LISI and PCReg for "
       "Diagnosis_cell_type_unified appeared random"),
      ("probably connected with different effective number of biological groups in each "
       "strategy",
       "probably reflecting the differing effective number of biological groups in each "
       "strategy"),
      ("This finding implies that local metrics could be highly impacted by the effective "
       "number of classes, whereas the global ones like PCReg are more robust to such changes "
       "in the dataset.",
       "This implies that local metrics are strongly affected by the effective number of "
       "classes, whereas global metrics such as PCReg are more robust to such changes in the "
       "dataset.")]),

    ("Finally, we compared PCReg and kBET acceptance rate by RNA_BATCH",
     [("The comparison revealed a weakly positive dependency",
       "The comparison revealed a weakly positive dependence"),
      ("Among batch removal strategies, C showed the highest kBET unlike in the case of LISI "
       "by biology",
       "Among the batch removal strategies, C showed the highest kBET, unlike the case of "
       "LISI by biology"),
      ("but neither of them was selected as the clustermap best approaches",
       "yet none of them was selected among the clustermap best approaches"),
      ("Only the entire set of metrics reveal’s the truly best approaches via clustermap.",
       "Only the complete set of metrics, viewed together in the clustermap, reveals the "
       "truly best approaches.")]),

    ("As the next section of harmonization quality metrics analysis",
     [("As the next section of harmonization quality metrics analysis, we visualized and "
       "compared distributional similarity, graph connectivity, Watermelon score, distance "
       "ratio and expression properties",
       "In the next part of the analysis we compared distributional similarity, graph "
       "connectivity, Watermelon score, distance ratio and expression properties"),
      ("quantifying fraction of pairs by a certain column that have significant differences "
       "by gene expression distribution according to Kolmogorov-Smirnov test",
       "which quantifies the fraction of pairs within a given column whose gene expression "
       "distributions differ significantly by the Kolmogorov-Smirnov test"),
      ("so they all had medium quality, and all the rest ones were considered as ‘bad’",
       "so all three were of medium quality, and the remaining strategies were considered "
       "‘bad’")]),

    ("We then investigated the behavior of graph connectivity",
     [("We then investigated the behavior of graph connectivity as an orthogonal measure of "
       "local mixing.",
       "We then examined graph connectivity as an orthogonal measure of local mixing."),
      ("revealed no dependency, but the clustermap derived best approaches had connectivity "
       "by both columns relatively high",
       "revealed no dependence, although the clustermap-derived best approaches had "
       "relatively high connectivity for both columns"),
      ("Harmonization methods were non-randomly distributed too",
       "Harmonization methods were also distributed non-randomly"),
      ("having lower biology preservation and simultaneously more interrupted platform-level "
       "distribution",
       "showing both lower biology preservation and a more fragmented platform-level "
       "distribution"),
      ("only D and K ones significantly deviated from the rest strategies",
       "only D and K deviated appreciably from the remaining strategies"),
      ("Notably, they each have only 4 biological groups and their connectivity should be "
       "higher all else being equal, but the fact that they were composed mainly from "
       "heterogeneous FFPE batches (and malignant FF ones in D which further increases "
       "heterogeneity) could explain lower connectivity by biology.",
       "Each of them contains only four biological groups, so all else being equal their "
       "connectivity should be higher; that it is not is most plausibly explained by their "
       "composition from heterogeneous FFPE batches, with additional malignant FF batches "
       "in D.")]),

    ("As an additional metric of global distance separation",
     [("we calculated ratio of within group Euclidean distance to the between group one",
       "we calculated the ratio of the within-group to the between-group Euclidean distance"),
      ("emphasizing higher priority of batch overlapping than biological differences "
       "preservation in these best approaches",
       "underlining that these approaches prioritize batch overlap over the preservation of "
       "biological differences"),
      ("Surprizingly, 07_pycombat, 03_limma and minority of 02_median_scaling were located "
       "even further to the right in the plot",
       "Surprisingly, 07_pycombat, 03_limma and a minority of 02_median_scaling approaches "
       "lay even further to the right"),
      ("This fact could be interpreted as a manifestation of the same principle: neither "
       "metric alone can be used to select the best harmonization approaches, but the "
       "clustermap of all of them can.",
       "This is a further illustration of the same principle: no single metric can be used to "
       "select the best harmonization approaches, whereas a clustermap of all of them can."),
      ("Batch removal strategies had more random distribution along the distance ratio axes",
       "Batch removal strategies were distributed more randomly along the distance ratio "
       "axes")]),

    ("The next step of other metrics comparison was the Watermelon (WM) score analysis",
     [("The next step of other metrics comparison was the Watermelon (WM) score analysis, "
       "which measures how well a given harmonization approach separates classes on a "
       "clustermap in a space of gene expression.",
       "We next analyzed the Watermelon (WM) score, which measures how well a harmonization "
       "approach separates classes on a clustermap in gene expression space."),
      ("whereas there was not any directed change by the WM Diagnosis_cell_type_unified "
       "metric",
       "whereas no directional change was apparent for WM by Diagnosis_cell_type_unified"),
      ("We then calculated and averaged WM score by all batch columns and all biology columns "
       "and build a standard scatteplot",
       "We then averaged the WM score over all batch columns and all biology columns and "
       "plotted the two against each other"),
      ("Even further compared to the previous WM score metrics, the clustermap best "
       "approaches did not form any compact or shifted group in the plot.",
       "Even more clearly than for the individual WM metrics, the clustermap best approaches "
       "formed no compact or displaced group in this plot."),
      ("Batch removal strategies had even higher degree of separation into compact groups",
       "Batch removal strategies separated into compact groups still more clearly"),
      ("which is particularly interesting since their number of biology classes is the same",
       "which is notable given that their number of biological classes is the same")]),

    ("The last of the ‘other’ metrics in our analysis was gene expression quantiles",
     [("Compared to the analysis by harmonization method (described in the main article), "
       "average gene expression properties by batch removal strategy were indistinguishable "
       "except the G strategy with the highest maximum gene expression and its standard "
       "deviation.",
       "In contrast to the analysis by harmonization method reported in the main article, the "
       "average gene expression properties were indistinguishable between batch removal "
       "strategies, except for G, which had the highest maximum gene expression and the "
       "largest standard deviation.")]),

    ("Taken together, the distributional similarity and distance ratio metrics",
     [("Potentially WM score measures another mode of harmonization quality that is not "
       "captured by the clustermap.",
       "The WM score may therefore capture a mode of harmonization quality that the "
       "clustermap does not."),
      ("The future best harmonization pipelines should take WM score as an independent group "
       "of metrics equally important as the PCA-based global and tSNE/UMAP based local ones.",
       "Future harmonization pipelines should treat the WM score as an independent metric "
       "group, on an equal footing with the PCA-based global and the tSNE/UMAP-based local "
       "metrics.")]),

    ("As an additional study of harmonization methods, we compared major metric types",
     [("We started with the widely accepted premise that in order to obtain perfect batch "
       "mixing and biology separation, one should apply as sophisticated methods that "
       "extensively reshape the gene expression distribution as possible. We aimed to test "
       "whether it’s true in the case of our FL multiplatform dataset.",
       "We began from the widely held premise that perfect batch mixing and biology "
       "separation require the most elaborate methods available, those that reshape the gene "
       "expression distribution most extensively. We set out to test whether this holds for "
       "our multiplatform FL dataset.")]),

    ("In the case of PCReg RNA_BATCH",
     [("In an opposite way, for PCReg Diagnosis_cell_type_unified",
       "Conversely, for PCReg Diagnosis_cell_type_unified")]),

    ("Local metrics showed the similar pattern of low harshness methods",
     [("Local metrics showed the similar pattern of low harshness methods having the best "
       "pefromance.",
       "The local metrics showed a similar pattern, with low-harshness methods performing "
       "best."),
      ("By LISI RNA_BATCH the behavior was even more favorable towards low harshness",
       "For LISI RNA_BATCH the pattern favored low harshness still more strongly"),
      ("By LISI Diagnosis_cell_type_unified, unfortunately, low harshness methods performed "
       "the worst (highest LISI by biology) in 12 strategies",
       "For LISI Diagnosis_cell_type_unified, by contrast, low-harshness methods performed "
       "worst (highest LISI by biology) in 12 strategies"),
      ("here in the case of LISI we observed the local mixing trade-off as in the main "
       "article: stronger local mixing by batch inevitably causes less local preservation "
       "(higher local mixing) of biology",
       "for LISI we observed the local mixing trade-off described in the main article: "
       "stronger local mixing of batches is accompanied by weaker local preservation of "
       "biology")]),

    ("Taken together, the harshness comparisons confer an intricate picture",
     [("Taken together, the harshness comparisons confer an intricate picture",
       "Taken together, the harshness comparisons give a nuanced picture"),
      ("In other words, it is better for harmonization to take less harsh interventions into "
       "data (like rank or quantile normalization), and harsh data transformations lead only "
       "to apparent success (similar expression distributions), not a real one.",
       "In other words, milder interventions in the data are preferable, and the harshest "
       "transformations yield only an apparent success — matched expression distributions — "
       "rather than a real one.")]),

    ("As the last part of the harmonization metrics extended analysis",
     [("we build the composite performance score as average of all the 87 polarity-multiplied "
       "scoring metrics and visualized it",
       "we built a composite performance score as the mean of all 87 polarity-adjusted "
       "scoring metrics and visualized it")]),

    ("The group of clustermap best approaches was indeed the best by composite score",
     [("but they were homogeneous among the batch removal strategies",
       "but they were homogeneous across the batch removal strategies"),
      ("The distributional similarity and other groups conferred no visible differences at "
       "the level of batch removal strategies.",
       "The distributional similarity and remaining metric groups produced no visible "
       "differences between batch removal strategies.")]),

    ("The pattern of metric type impact by harmonization methods was more complicated",
     [("The two top methods after the clustermap best group (it was again the best by the "
       "composite score) were 22_tmm and 23_vst – apparently because they were applied to C "
       "strategy only.",
       "The two leading methods after the clustermap best group, which was again first "
       "overall, were 22_tmm and 23_vst — apparently because they were applied to the C "
       "strategy alone.")]),

    ("Comparison of the metrics computational groups revealed",
     [("Neighbor based integration and tSNE/UMAP embeddings were the two major groups for "
       "local metrics",
       "Neighbor-based integration and tSNE/UMAP embedding were the two principal groups of "
       "local metrics"),
      ("Watermelon score and samples/genes with NA conferred no differences",
       "The Watermelon score and the missing-value metrics produced no differences")]),

    ("Finally, we investigated the impact of metrics calculated by different annotation "
     "columns",
     [("Biology columns (Major_group, Diagnosis_cell_type_unified, TUMOR_NORMAL) added no "
       "significant difference into the composite score",
       "The biology columns (Major_group, Diagnosis_cell_type_unified, TUMOR_NORMAL) "
       "contributed no appreciable difference to the composite score"),
      ("Among the batch columns COHORT_LABEL and RNA_BATCH brought the most variability "
       "between the top and the bottom strategies and harmonization methods.",
       "Among the batch columns, COHORT_LABEL and RNA_BATCH introduced the most variability "
       "between the leading and trailing strategies and harmonization methods.")]),

    # ── final prose polish ────────────────────────────────────────────────────
    ("Figure 6. Global PCA-based metrics performance",
     [("(A) Scatterplot of  PCReg", "(A) Scatterplot of PCReg")]),

    ("It should be noted that S0 01_raw dataset",
     [("It should be noted that S0 01_raw dataset",
       "It should be noted that the S0 01_raw dataset")]),

    ("To deeply investigate the PC-level variation",
     [("showed that 5 methods", "showed that five methods"),
      ("11.3-15.3% for the second PC etc.", "11.3-15.3% for the second, and so on.")]),

    ("PCA variance explained by batch (R2 by RNA_BATCH) showed a more complicated pattern",
     [("For the top 5 methods by average PCReg RNA_BATCH",
       "For the five leading methods by average PCReg RNA_BATCH"),
      ("14_qsmooth method as the worst one by PCA-based performance showed average 53.7",
       "14_qsmooth, the worst method by PCA-based performance, showed averages of 53.7")]),

    ("We then investigated performance of the local mixing (local neighborhood) metrics",
     [("and FF only had the highest local biology mixing, followed by RNA-seq only and "
       "Affymetrix extended (median 1.62, 1.39 and 1.41, respectively)",
       "and FF only had the highest local biology mixing, followed by Affymetrix extended and "
       "RNA-seq only (median 1.62, 1.41 and 1.39, respectively)")]),

    ("Among global metrics, we firstly analyzed Principal Component Regression",
     [("and were considered as of ‘good’ quality", "and were considered to be of ‘good’ "
                                                   "quality"),
      ("5 of the methods (33_amdbnorm", "Five of the methods (33_amdbnorm")]),

    ("Extended Figure 3. Additional global metrics analysis.",
     [("(E) The same scatterplot of tSNE centroid disp RNA_BATCH",
       "(G) The same scatterplot of tSNE centroid disp RNA_BATCH"),
      ("(E) The same scatterplot of ASW RNA_BATCH",
       "(J) The same scatterplot of ASW RNA_BATCH")]),

    ("At a general scale, global metrics behaved to the high degree",
     [("At a general scale, global metrics behaved to the high degree like the PCReg metrics "
       "family. R2 by first principal component, dispersion separability criterion, tSNE "
       "centroid dispersion, average silhouette width – they monotonously correlated with "
       "PCReg, either linearly or non-linearly. Outliers that arose in the perpendicular "
       "direction of the main dependency and that performed better than average – were not "
       "validated by the clustermap best methods and, therefore, had a poorer performance by "
       "other metrics, especially the local ones.",
       "Taken as a whole, the global metrics behaved much like the PCReg family. The R2 of "
       "the first principal component, the dispersion separability criterion, tSNE centroid "
       "dispersion and average silhouette width all correlated monotonically with PCReg, "
       "either linearly or non-linearly. Outliers that departed from the main dependence in "
       "the perpendicular direction, and that appeared better than average, were not "
       "corroborated by the clustermap best methods and therefore performed worse on the "
       "other metrics, particularly the local ones.")]),

    ("LISI metrics (Local inverse Simpson's index) revealed 10_mnn",
     [("4 more methods (13_fsmvn", "Four further methods (13_fsmvn"),
      ("were considered as ‘good’ since their LISI by biology",
       "were considered ‘good’ because their LISI by biology")]),

    ("tSNE centroid dispersion is a natural complementary pair to tSNE entropy",
     [("10_mnn with minority of 04_sva, 11_harmony, 12_scanorama and 16_fsqn_r approaches "
       "formed a diagonally shaped cloud",
       "10_mnn, together with a minority of the 04_sva, 11_harmony, 12_scanorama and "
       "16_fsqn_r approaches, formed a diagonal cloud")]),

    ("The analogous comparison of LISI and PCReg by the main biology column",
     [("Indeed, the D and K strategies contained a few malignant only groups",
       "Indeed, the D and K strategies contained only four malignant groups"),
      ("Simultaneously the J strategy contained all the diverse normal B cell types and less "
       "cancers than other strategies, and it had highest LISI.",
       "The J strategy, by contrast, contained the full range of normal B cell types and "
       "fewer malignancies than the others, and had the highest LISI.")]),

    ("Finally, we compared PCReg and kBET acceptance rate by RNA_BATCH",
     [("This example highlights the general trend: absolute maximum by any metric (even the "
       "local mixing one) does not guarantee an approach to be the best by clustermap and "
       "confirmed by visual inspection.",
       "This illustrates the general trend: attaining the maximum of any single metric, even "
       "a local mixing one, does not make an approach the best by clustermap or confirm it "
       "under visual inspection.")]),

    ("The next step of other metrics comparison was the Watermelon (WM) score analysis",
     [("S0 and I strategies had relative decrease in WM by Diagnosis_cell_type_unified",
       "The S0 and I strategies showed a relative decrease in WM by "
       "Diagnosis_cell_type_unified"),
      ("As previously, we had a compact group of 10_mnn approaches",
       "As before, there was a compact group of 10_mnn approaches")]),

    ("We sorted and visualized all the approaches by their composite score",
     [("The resulting curve had an upper tail of outliers by high composite score (above 0.6)",
       "The resulting curve had an upper tail of high-scoring outliers (composite score above "
       "0.6)"),
      ("Such a pattern confirms the general strategy dataset harmonization with high "
       "technical and subtle biological differences",
       "This pattern supports the general strategy for harmonizing datasets with pronounced "
       "technical and subtle biological differences"),
      ("To find these approaches, one should build a clustermap of quality metrics or do "
       "another integrative analysis of them, then visually confirming the findings on the "
       "dimensional reduction plots.",
       "To identify them, one should build a clustermap of the quality metrics, or perform "
       "another integrative analysis of them, and then confirm the result visually on "
       "dimensionality reduction plots."),
      ("There is no royal way in the field of the cross-platform transcriptomic harmonization.",
       "There is no shortcut in cross-platform transcriptomic harmonization.")]),
]


# ── new closing section ───────────────────────────────────────────────────────
SUMMARY_HEADING = "Summary of metric trends"

SUMMARY_PARAGRAPHS = [
    "The analyzes above rest on the same 2,234 successful approaches used in the main "
    "article: 31 harmonization methods applied across 14 batch removal strategies, three "
    "imputation schemes and two post-removal settings, scored on 87 polarity-adjusted "
    "metrics. Five trends run through them consistently, and are set out here in the order "
    "of the evidence presented above.",

    "First, global and local metrics measure different things, and agreement between them is "
    "the exception rather than the rule. Principal component regression, the dispersion "
    "separability criterion, tSNE centroid dispersion, average silhouette width and the R2 "
    "of the leading principal components all varied monotonically with one another, whether "
    "linearly or through a saturating curve, so that any one of them stands in for the "
    "global family. Local mixing did not follow. Five methods (33_amdbnorm, 13_fsmvn, "
    "03_limma, 07_pycombat and 28_npn) reached a mean PCReg RNA_BATCH of 0.999 or above, "
    "with a batch-explained variance below 0.25% at every one of the first ten principal "
    "components, and yet 98.5% of the 198 approaches they generated had a kBET acceptance "
    "rate below 0.1. A global metric at its theoretical optimum is therefore not evidence of "
    "successful harmonization; it is equally consistent with a transformation that has "
    "destroyed the structure it was meant to align.",

    "Second, batch-explained variance is frequently displaced rather than removed. Nineteen "
    "of the 31 methods, and 10 of the 14 batch removal strategies, showed a lower RNA_BATCH "
    "R2 at the first principal component than at some later component. The five methods with "
    "the slowest decay of explained variance (25_angel, 20_shambhala, 15_fsqn_py, "
    "17_quantile and 18_rank) illustrate this most clearly: four of them placed their maximum "
    "batch R2 at a component other than the first. Reporting only the leading component, or "
    "only a metric aggregated over the leading component, will systematically overstate how "
    "much batch structure has been eliminated.",

    "Third, the trade-off between mixing batches and preserving biology is real but modest, "
    "and it is dominated by the composition of the dataset. Across all approaches the "
    "un-normalized iLISI for RNA_BATCH and cLISI for Diagnosis_cell_type_unified correlated "
    "positively (Spearman r = 0.527, p = 7 * 10-160), and the correlation was significant "
    "within every batch removal strategy except G (r from 0.374 to 0.815, median 0.617). "
    "Polarity-adjusted PCReg showed the same tension far more weakly (Spearman r = -0.159, "
    "p = 3.7 * 10-14). The strategies themselves separated much more strongly than the "
    "methods did: the strategies with the fewest biological classes, malignant only and FFPE "
    "only, had both the lowest cLISI (median 1.10 and 1.07) and the highest PCReg by biology "
    "(median 0.939 and 0.925). Local metrics are sensitive to the effective number of "
    "classes in a way that global metrics are not, and comparisons of local metrics across "
    "strategies with different class structures are not directly interpretable.",

    "Fourth, elaborate transformations do not outperform simple ones. Grouping the methods by "
    "harshness, the low-harshness tier gave the highest PCReg RNA_BATCH in 11 of the 14 "
    "strategies and the highest LISI RNA_BATCH in 10 of 14, while the high-harshness tier was "
    "the worst on tSNE entropy in 12 of 14. High harshness prevailed on exactly one axis, "
    "distributional convergence: it gave the lowest KS fraction significant in 13 of the 14 "
    "strategies. Harsh transformations therefore succeed at making expression distributions "
    "look alike without making the underlying samples more comparable, which is precisely the "
    "failure mode that a distribution-based metric alone cannot detect. Consistent with this, "
    "the methods that produced the most atypical expression ranges — 08_inmoose_combatseq and "
    "06_combat_seq, with mean maxima of 1.46 * 1011 and 2.76 * 108, and 20_shambhala, with a "
    "median of 1,359.6 — ranked poorly overall, whereas the 15 best approaches stayed close "
    "to a conventional log2(TPM) profile (median 2.63 to 6.70, maximum 12.6 to 28.6).",

    "Fifth, the composite score is decided by the small local component. Local neighborhood "
    "metrics made up 22 of the 87 scoring columns and contributed only 8.1 to 18.1% of the "
    "composite, yet they accounted for its largest between-group spread: 0.043 across "
    "strategies for neighbor-based integration and 0.049 across methods, against 0.017 and "
    "0.030 for the PCA-based variance decomposition group. Batch-annotated columns supplied "
    "57 of the 87 metrics and 60.7 to 67.4% of the composite, while the 18 biology columns "
    "separated good from bad approaches only weakly (a spread of 0.053 across strategies "
    "against 0.122 for the batch columns). The clustermap best approaches were first overall "
    "(0.602) ahead of the RNA-seq-only strategy (0.578), and 9 of the 15 fell in the "
    "high-scoring tail above 0.6 that contains just 150 of the 2,234 approaches (6.7%).",

    "The practical conclusion is that no single metric, and no single metric family, "
    "identifies a usable harmonization approach. Global metrics are necessary but easily "
    "saturated; local metrics are discriminating but confounded by class composition; "
    "distributional metrics reward exactly the transformations that should be treated with "
    "most suspicion. Only the joint reading of all metric groups, followed by visual "
    "confirmation on dimensionality reduction plots, separates the approaches that work from "
    "those that merely score well.",
]


def visible(p):
    """Text as Word displays it: original plus insertions, deletions excluded."""
    return "".join(t.text or "" for t in p.findall(f".//{W}t"))


def direct_text(p):
    """Text of runs that are direct children of the paragraph.

    This is exactly what `safe_tracked_replace` can act on. Driving the figure sweep from it
    rather than from `visible()` keeps the sweep from generating pairs for text that has
    already been rewritten into `w:ins`, where a search would either miss it or, worse, land
    on an unrelated live occurrence of the same string elsewhere in the paragraph.
    """
    return "".join(
        t.text or ""
        for r in p.findall(f"{W}r")
        for t in r.findall(f"{W}t")
    )


def find_p(body, needle, skip=()):
    hits = [
        el for el in body.iter(f"{W}p")
        if needle in visible(el) and not any(s in visible(el) for s in skip)
    ]
    if len(hits) != 1:
        raise SystemExit(f"anchor matched {len(hits)} paragraphs: {needle!r}")
    return hits[0]


def main():
    doc = docx.Document(SRC)
    body = doc.element.body
    paragraphs = list(body.iter(f"{W}p"))

    report = {"ok": 0, "not-found": 0, "unsafe": 0}

    def apply(p, pairs, tag):
        for old, status in safe_tracked_replace(p, pairs):
            report[status] += 1
            if status != "ok":
                print(f"  [{status}] {tag}: {old[:90]!r}")

    # 1 ── numbers and language, located by text anchor.
    #      Resolve every anchor to an element reference before mutating anything: once an
    #      edit lands, the original wording lives in w:delText and a text search misses it.
    resolved = []
    for anchor, pairs in NUMBER_EDITS + LANGUAGE_EDITS:
        renumbered = [(old, renum_text(new)) for old, new in pairs]
        resolved.append((find_p(body, anchor), renumbered, anchor))
    for p, pairs, anchor in resolved:
        apply(p, pairs, anchor[:45])

    # 2 ── figure renumbering, paragraph by paragraph, left to right.
    n_refs = 0
    for p in paragraphs:
        text = direct_text(p)
        if "Figure" not in text:
            continue
        pairs = [(o, n) for o, n in SPECIALS if o in text]
        remaining = text
        for o, _ in pairs:
            remaining = remaining.replace(o, " ")
        pairs += figure_edits(remaining)
        if not pairs:
            continue
        n_refs += len(pairs)
        apply(p, pairs, "figref")

    # 3 ── append the summary section as a tracked insertion.
    #      `sectPr` must stay last in the body, so insert before it when it is present.
    sect_pr = body.find(f"{W}sectPr")
    new_els = [heading(SUMMARY_HEADING, level=2)]
    new_els += [ins_paragraph(t) for t in SUMMARY_PARAGRAPHS]
    for el in new_els:
        if sect_pr is not None:
            sect_pr.addprevious(el)
        else:
            body.append(el)

    print(f"\nfigure references rewritten: {n_refs}")
    print(f"summary section: 1 heading + {len(SUMMARY_PARAGRAPHS)} paragraphs inserted")
    print(f"ok {report['ok']} | not-found {report['not-found']} | unsafe {report['unsafe']}")
    doc.save(DST)
    print(f"wrote {DST}")


if __name__ == "__main__":
    main()
