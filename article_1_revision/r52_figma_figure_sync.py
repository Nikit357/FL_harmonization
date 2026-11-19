#!/usr/bin/env python
"""Align the manuscript text with the final Figma figures (page 5, 2026-11-18).

Reads Daniil's edited manuscript, which already holds his pending tracked changes, and
writes every edit as a tracked revision on top of them:

* text in a plain run   -> <w:del> / <w:ins> at paragraph level;
* text inside one of Daniil's pending insertions -> <w:ins><w:del>...</w:del></w:ins>
  ("inserted, then deleted", as Word writes it); the new text goes into a new <w:ins>
  placed after the deleted part (the old insertion is split around it);
* citations (w:sdt), hyperlinks and runs holding tabs / breaks are never touched: a
  replacement may not span them.

Accept All = text aligned with the Figma figures; Reject All = the input file.

    python3 r52_figma_figure_sync.py            # writes Revised_manuscript/..._261118_figma_sync.docx
"""
from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

import docx
from docx.oxml.ns import qn

SRC = Path("Revised_manuscript/FL_harmonization_article_NARGAB_261113_edited_Daniil.docx")
DST = Path("Revised_manuscript/FL_harmonization_article_NARGAB_261118_figma_sync.docx")
AUTHOR = "Claude (Figma figure sync)"
DATE = "2026-11-18T12:00:00Z"


def W(tag: str) -> str:
    return qn("w:" + tag)


SAFE_RUN_KIDS = {W("rPr"), W("t"), W("lastRenderedPageBreak")}
ZERO_WIDTH = {W("pPr"), W("proofErr"), W("bookmarkStart"), W("bookmarkEnd"),
              W("commentRangeStart"), W("commentRangeEnd")}
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


class Rev:
    next_id = 900000

    @classmethod
    def el(cls, kind: str):
        e = docx.oxml.OxmlElement("w:" + kind)
        e.set(W("id"), str(cls.next_id))
        e.set(W("author"), AUTHOR)
        e.set(W("date"), DATE)
        cls.next_id += 1
        return e


# --------------------------------------------------------------------------- runs
def run_text(r) -> str:
    return "".join(t.text or "" for t in r.findall(W("t")))


def clean_rpr(rpr):
    if rpr is None:
        return None
    rpr = copy.deepcopy(rpr)
    for tag in ("ins", "del", "rPrChange"):
        for x in rpr.findall(W(tag)):
            rpr.remove(x)
    return rpr


def new_run(text: str, rpr=None, bold=None, italic=None, color=None):
    r = docx.oxml.OxmlElement("w:r")
    rp = clean_rpr(rpr)
    if rp is None:
        rp = docx.oxml.OxmlElement("w:rPr")
    for tag, val in (("b", bold), ("i", italic)):
        if val is None:
            continue
        for x in rp.findall(W(tag)) + rp.findall(W(tag + "Cs")):
            rp.remove(x)
        if val:
            rp.append(docx.oxml.OxmlElement("w:" + tag))
    if color:
        for x in rp.findall(W("color")):
            rp.remove(x)
        c = docx.oxml.OxmlElement("w:color")
        c.set(W("val"), color)
        rp.append(c)
    if len(rp):
        r.append(rp)
    t = docx.oxml.OxmlElement("w:t")
    t.set(XML_SPACE, "preserve")
    t.text = text
    r.append(t)
    return r


def set_run_text(r, text: str):
    ts = r.findall(W("t"))
    for t in ts[1:]:
        r.remove(t)
    if ts:
        ts[0].text = text
        ts[0].set(XML_SPACE, "preserve")


def markup_runs(text: str, rpr, color=None, italic=None):
    """'**bold** plain' -> runs; bold toggled, everything else from rpr."""
    out = []
    for i, part in enumerate(re.split(r"\*\*", text)):
        if part:
            out.append(new_run(part, rpr, bold=(i % 2 == 1), italic=italic, color=color))
    return out


# ----------------------------------------------------------------------- segments
def segments(p):
    """[(run, container_or_None, start, end)], joined accepted text with barriers."""
    segs, buf = [], []
    pos = 0

    def add_run(r, cont):
        nonlocal pos
        if all(c.tag in SAFE_RUN_KIDS for c in r):
            t = run_text(r)
            segs.append((r, cont, pos, pos + len(t)))
            buf.append(t)
            pos += len(t)
        else:
            buf.append("\x00")
            pos += 1

    for c in p:
        if c.tag == W("r"):
            add_run(c, None)
        elif c.tag == W("ins"):
            for cc in c:
                if cc.tag == W("r"):
                    add_run(cc, c)
                elif cc.tag == W("del") or cc.tag in ZERO_WIDTH:
                    continue
                else:
                    buf.append("\x00")
                    pos += 1
        elif c.tag == W("del") or c.tag in ZERO_WIDTH:
            continue
        else:  # sdt, hyperlink, fldSimple, smartTag ...
            buf.append("\x00")
            pos += 1
    return segs, "".join(buf)


def split_at(p, k: int) -> None:
    """Make k a run boundary."""
    for r, cont, s, e in segments(p)[0]:
        if s < k < e:
            t = run_text(r)
            r2 = copy.deepcopy(r)
            set_run_text(r, t[: k - s])
            set_run_text(r2, t[k - s:])
            r.addnext(r2)
            return


def split_container_after(x):
    """x lies in a w:ins of another author: move the siblings after x into a copy."""
    e = x.getparent()
    tail = list(x.itersiblings())
    if not tail:
        return e
    e2 = copy.deepcopy(e)
    for ch in list(e2):
        e2.remove(ch)
    e2.set(W("id"), str(Rev.next_id))
    Rev.next_id += 1
    for ch in tail:
        e2.append(ch)
    e.addnext(e2)
    return e


def delete_run(r):
    for t in r.findall(W("t")):
        t.tag = W("delText")
        t.set(XML_SPACE, "preserve")
    d = Rev.el("del")
    r.addprevious(d)
    d.append(r)
    return d


def place_after(x, p, el):
    if x.getparent() is p:
        x.addnext(el)
    else:
        split_container_after(x).addnext(el)


def place_before(x, p, el):
    if x.getparent() is p:
        x.addprevious(el)
        return
    prev = x.getprevious()
    if prev is None:
        x.getparent().addprevious(el)
    else:
        split_container_after(prev).addnext(el)


def word_trim(old: str, new: str):
    """Common prefix / suffix cut at word boundaries -> (pre, suf)."""
    pre = 0
    while pre < min(len(old), len(new)) and old[pre] == new[pre]:
        pre += 1
    while pre > 0 and not (old[pre - 1] in " (" or pre == len(old) or pre == len(new)):
        pre -= 1
    suf = 0
    while (suf < min(len(old), len(new)) - pre
           and old[len(old) - 1 - suf] == new[len(new) - 1 - suf]):
        suf += 1
    while suf > 0 and not old[len(old) - suf] in " ,.;:)":
        suf -= 1
    return pre, suf


def replace_span(p, s: int, e: int, ins_runs) -> None:
    """Track-delete accepted text [s, e) and insert ins_runs (list of w:r) there."""
    split_at(p, s)
    split_at(p, e)
    segs, joined = segments(p)
    if "\x00" in joined[s:e]:
        raise ValueError("span crosses a citation / field / special run: "
                         + repr(joined[s:e][:80]))
    inside = [sg for sg in segs if sg[2] >= s and sg[3] <= e and sg[3] > sg[2]]
    ins_el = None
    if ins_runs:
        ins_el = Rev.el("ins")
        for r in ins_runs:
            ins_el.append(r)
    if inside:
        last = None
        for r, cont, _, _ in inside:
            last = delete_run(r)
        if ins_el is not None:
            place_after(last, p, ins_el)
        return
    if ins_el is None:
        return
    after = [sg for sg in segs if sg[2] >= s and sg[3] > sg[2]]
    before = [sg for sg in segs if sg[3] <= s and sg[3] > sg[2]]
    if before and before[-1][3] == s:
        place_after(before[-1][0], p, ins_el)
    elif after:
        place_before(after[0][0], p, ins_el)
    else:
        p.append(ins_el)


def base_rpr(p, at: int):
    for r, _, s, e in segments(p)[0]:
        if s <= at < e or (at == e and e > s):
            return r.find(W("rPr"))
    segs = segments(p)[0]
    return segs[0][0].find(W("rPr")) if segs else None


LOG: list[str] = []


def tr(p, pairs, tag=""):
    """Tracked replacements of accepted-text substrings (first occurrence each)."""
    for old, new in pairs:
        segs, joined = segments(p)
        i = joined.find(old)
        if i < 0:
            LOG.append(f"NOT FOUND [{tag}]: {old[:70]!r}")
            continue
        pre, suf = word_trim(old, new)
        s, e = i + pre, i + len(old) - suf
        mid_new = new[pre: len(new) - suf]
        rpr = base_rpr(p, s if s < e else max(s - 1, 0))
        runs = markup_runs(mid_new, rpr) if mid_new else []
        replace_span(p, s, e, runs)
        LOG.append(f"ok [{tag}]: {old[pre:len(old)-suf][:50]!r} -> {mid_new[:50]!r}")


def rewrite_after(p, keep_prefix: str, new_markup: str, tag=""):
    """Keep the accepted text up to and including keep_prefix; rewrite the rest."""
    segs, joined = segments(p)
    i = joined.find(keep_prefix)
    if i != 0:
        LOG.append(f"PREFIX NOT AT START [{tag}]: {joined[:60]!r}")
        return
    s = len(keep_prefix)
    rpr = None
    for r, _, a, b in segs:
        if a >= s and b > a:
            rpr = r.find(W("rPr"))
            break
    replace_span(p, s, len(joined), markup_runs(new_markup, rpr))
    LOG.append(f"rewrite [{tag}]")


def delete_paragraph(p, tag=""):
    segs, joined = segments(p)
    if "\x00" in joined:
        raise ValueError(f"paragraph {tag} holds fields")
    for r, _, a, b in segs:
        if b > a:
            delete_run(r)
    ppr = p.find(W("pPr"))
    if ppr is None:
        ppr = docx.oxml.OxmlElement("w:pPr")
        p.insert(0, ppr)
    rpr = ppr.find(W("rPr"))
    if rpr is None:
        rpr = docx.oxml.OxmlElement("w:rPr")
        ppr.append(rpr)
    rpr.append(Rev.el("del"))
    LOG.append(f"deleted paragraph [{tag}]")


def new_paragraph(ref_p, markup: str, color=None, italic=None):
    p = docx.oxml.OxmlElement("w:p")
    ppr = copy.deepcopy(ref_p.find(W("pPr")))
    if ppr is None:
        ppr = docx.oxml.OxmlElement("w:pPr")
    rpr = ppr.find(W("rPr"))
    if rpr is None:
        rpr = docx.oxml.OxmlElement("w:rPr")
        ppr.append(rpr)
    for tag in ("ins", "del", "rPrChange"):
        for x in rpr.findall(W(tag)):
            rpr.remove(x)
    for x in ppr.findall(W("pPrChange")):
        ppr.remove(x)
    rpr.append(Rev.el("ins"))
    p.append(ppr)
    segs = segments(ref_p)[0]
    run_rpr = segs[0][0].find(W("rPr")) if segs else None
    ins = Rev.el("ins")
    for r in markup_runs(markup, run_rpr, color=color, italic=italic):
        ins.append(r)
    p.append(ins)
    return p


def note(ref_p, text: str):
    return new_paragraph(ref_p, "**[EDITOR NOTE]** " + text, color="C00000", italic=True)


# =========================================================================== edits
def main() -> int:
    d = docx.Document(str(SRC))
    body = d.element.body
    K = list(body)  # body-child indices as in the extraction (fixed before any edit)

    def P(i):
        el = K[i]
        assert el.tag == W("p"), i
        return el

    # -------------------------------------------------------------- abstract / intro
    tr(P(14), [("Feature Specific Quantile Normalization, FSMVN and ComBat variants for "
                "RNA-seq combined with microarrays, and Angel for fresh-frozen data",
                "Feature Specific Quantile Normalization, FSMVN and ComBat for malignant "
                "samples, M-ComBat after rare-batch removal, and Angel for fresh-frozen, "
                "microarray-only and whole-cohort data")], "abstract")
    tr(P(23), [("five-scenario decision tree", "seven-leaf decision tree")], "intro")

    # -------------------------------------------------------------------- methods
    tr(P(47), [("strict NA exclusion,", "strict NA exclusion (labelled 'strict' or 'no "
                "imputation' in the figures),")], "imputation")
    tr(P(73), [
        ("before and after harmonization had to reach 0.7;",
         "before and after harmonization (marker correlation, labelled 'biomarker "
         "correlation preservation' in the figures) had to reach 0.7;"),
        ("the leave-one-batch-out macro-F1 of diagnosis prediction could not fall",
         "the leave-one-batch-out macro-F1 of diagnosis prediction (cross-batch "
         "prediction) could not fall"),
        ("(removing more batch signal removes diagnosis signal; Figure 6, gradient panel)",
         "(removing more batch signal removes diagnosis signal; Figure 6A)"),
    ], "selection rule")
    tr(P(77), [("Ward linkage method", "Ward linkage method")], "noop")  # anchor check
    segs, joined = segments(P(77))
    end_rpr = segs[-1][0].find(W("rPr")) if segs else None
    replace_span(P(77), len(joined), len(joined), markup_runs(
        " The analysis notebooks drew every panel at its final size as an SVG file; in "
        "Figma the panels were then split, rearranged and relettered, and their legends, "
        "colours, labels and font sizes were edited by hand, so that one notebook panel "
        "can correspond to several figure panels. The Figma figures are the final ones, "
        "and every panel is described in its legend.", end_rpr))
    LOG.append("ok [figures preparation]: appended Figma sentence")

    # -------------------------------------------------------------------- results
    tr(P(92), [
        ("(Supplementary Figure 1):", "(Supplementary Figure 2):"),
        ("(Supplementary Figure 1A)", "(Supplementary Figure 2A)"),
        ("(Supplementary Figure 1B)", "(Supplementary Figure 2B)"),
        ("information 0.26; Figure 1E)", "information 0.26; Supplementary Figure 1)"),
        ("Burkitt lymphoma, and normal B cells (Figure 1D)",
         "Burkitt lymphoma, and normal B cells (Supplementary Figure 1)"),
    ], "cohort composition")

    rewrite_after(P(95), "Figure 1. Dataset composition and computational pipeline.",
        " **(A)** Dataset composition by batch: each bubble is one RNA batch (sample "
        "number in brackets) and each point one sample; batch colours are grouped by "
        "platform (Illumina, Agilent and Affymetrix microarrays, RNA sequencing). "
        "**(B)** Dataset composition by biology group: bubbles are diagnoses and B-cell "
        "populations, coloured in three groups (early to germinal-centre B cells, mature "
        "to plasma B cells, malignancies). The batch and biology colours of (A) and (B) "
        "are used in every figure. **(C)** The nine steps of the ComboBatch pipeline: raw "
        "expression data; 14 batch-removal strategies by batch, biology, biomaterial and "
        "platform; imputation (strict, KNN or softImpute); log2(x + 1) transformation per "
        "cohort; harmonization by 33 methods (31 analysed); post-removal (all batches "
        "kept, or the batch farthest from the PCA centroid removed); computation of the "
        "quality metrics; polarity setting, so that more batch mixing and less mixing of "
        "biology groups score better; and the clustermap of the 2,234 approaches with the "
        "selection of the best ones. Confounding between batch and diagnosis is shown in "
        "Supplementary Figure 1.", "Figure 1 legend")
    rewrite_after(P(96), "Alt text:",
        " Overview of the dataset and pipeline: bubble plots of sample composition by "
        "batch and by biology group, and a schematic of the nine-step ComboBatch "
        "pipeline.", "Figure 1 alt")

    tr(P(98), [("Supplementary Figure 1C", "Supplementary Figure 2C")], "strategies")
    for _ in range(6):
        tr(P(100), [("Supplementary Figure 2", "Supplementary Figure 3")], "distributions")
    tr(P(104), [("(Supplementary Figure 3)", "(Supplementary Figure 4)")], "jaccard")

    tr(P(111), [
        ("(Supplementary Figure 5)", "(Supplementary Figure 6)"),
        ("availability was nearly equal across strategies (Supplementary Figure 4)",
         "availability was nearly equal across strategies (Supplementary Figure 5B; the "
         "number of metrics computed for every approach is shown in Supplementary "
         "Figure 5A)"),
    ], "metric panel")

    tr(P(116), [
        ("resolved 5 metric clusters (global metrics, two clusters of local metrics, "
         "missing values, and bimodality with zero fraction) and 4 approach clusters. "
         "Cross-platform approaches with good local batch mixing formed one cluster (651 "
         "approaches) and approaches of a single platform or sample type another (404); "
         "two cross-platform clusters with poor batch mixing held 800 and 379 approaches. "
         "Of the 22 recommended approaches (below), 14 lay in the first cluster, 3 in the "
         "single-platform cluster and 5 in a poor-mixing cluster whose bimodality and "
         "missing-value metrics were best.",
         "resolved five metric clusters (mostly global metrics, mixed metrics, local "
         "metrics, missing values, and bimodality with zero fraction) and four approach "
         "clusters, each named in Figure 3 after its most frequent strategies and its "
         "metric values. Two clusters had good local batch mixing: one of 651 approaches, "
         "336 of them from microarray-only (F, G, H), malignant-only (D) and FFPE-only "
         "(K) strategies, and one of 404 approaches that held 149 of the 168 RNA-seq-only "
         "(C) approaches. Two cross-platform clusters had poor batch mixing: one of 800 "
         "approaches and one of 379 approaches with the highest share of bimodal cohorts. "
         "Of the 22 recommended approaches (below), 14 lay in the first cluster, 3 in the "
         "RNA-seq-only cluster and 5 in the bimodal cross-platform cluster, whose "
         "bimodality and missing-value metrics were best."),
        ("(Supplementary Figure 6)", "(Supplementary Figure 7)"),
    ], "clustermap")

    rewrite_after(P(125), "Figure 3.",
        "** Clustermap of 2,234 harmonization approaches (columns) on the 22 metrics of "
        "the reduced panel (rows).** Values are polarity adjusted and min–max scaled "
        "(1 = best); black cells are undefined metrics. Shaded bands name the four "
        "approach clusters (microarrays, malignant and FFPE only with good batch mixing; "
        "RNA-seq only with good batch mixing; cross-platform with poor batch mixing; "
        "cross-platform and bimodal) and the five metric clusters (bimodality and zero "
        "fraction, mixed metrics, local metrics, missing values, mostly global metrics). "
        "Column annotation: batch-removal strategy, harmonization method, imputation, "
        "post-removal, harshness level (low, medium or high; Supplementary Table S1) and "
        "a mark for each of the 22 recommended approaches. Row annotation: metric group "
        "(A–K; Supplementary Table S2), score bar (the score a metric belongs to, if any) "
        "and annotation column (batch, diagnosis or none). Dendrograms: Ward linkage on "
        "Euclidean distance.", "Figure 3 legend")

    tr(P(131), [("Figures 4 and 5 show the recommended approach of each scenario next to "
                 "the unharmonized data of the same strategy and imputation.",
                 "Figure 4A shows the unharmonized data of all samples; Figures 4B–D and "
                 "5 show six of the recommended approaches, one each for FF only, FFPE "
                 "only and RNA-seq only and three for RNA-seq combined with "
                 "microarrays.")], "figures 4-5 intro")
    tr(P(132), [("(Table 3, Figure 6F)", "(Table 3, Figure 6C)")], "visual check")
    tr(P(139), [("(first component 69 % → 8 % of the variance)",
                 "(first component 8 % of the variance, against 69 % in the unharmonized "
                 "data of the same strategy and imputation)")], "Angel J")

    rewrite_after(P(145), "Figure 4.",
        "** Unharmonized data and the recommended approaches for a single sample type.** "
        "**(A)** All 7,174 samples without batch removal, imputation or harmonization "
        "(S0): PCA (first two components, share of variance on the axes) and tSNE, "
        "coloured by batch and by diagnosis. **(B–D)** The recommended approach of one "
        "scenario, PCA (left) and tSNE (right), coloured by batch (top row) and diagnosis "
        "(bottom row): **(B)** Angel in J (FF only, softImpute; 3,167 samples); **(C)** "
        "SVA in K (FFPE only, softImpute; 3,000 samples); **(D)** SVA in C (RNA-seq only, "
        "KNN; 2,243 samples). Batch colours are grouped by platform and diagnosis colours "
        "by biology group, as in Figure 1A, B. Marker correlation and cross-batch "
        "prediction of each approach and of the unharmonized data are given in Table 3. "
        "Embeddings use the genes without missing values in each matrix (345 genes for "
        "Angel).", "Figure 4 legend")

    tr(P(150), [("lowered the share of the first component from 80 % to 22 %",
                 "left 22 % of the variance on the first component (80 % in the "
                 "unharmonized data of the same strategy)")], "FSQN R D")

    segs, joined = segments(P(157))
    replace_span(P(157), 0, len(joined), markup_runs(
        "PCA, UMAP and tSNE plots of every front member inspected at the visual check, "
        "and of further approaches (MNN, SVA and FSQN R with each imputation, FSMVN and "
        "AMDBNorm), are deposited with the exploratory plots in the project repository "
        "(Data Availability). MNN mixed batches but failed the marker correlation "
        "threshold (Supplementary Figure 8A), and SVA without imputation left the "
        "fresh-frozen and FFPE batches of C apart.", segs[0][0].find(W("rPr"))))
    LOG.append("rewrite [further embeddings]")
    K[157].addnext(note(P(157),
        "Supplementary Figures 7–13 and 15 of the previous version (embedding grids and "
        "cell-of-origin plots) were removed in Figma. Please confirm that these plots and "
        "the visual-check embeddings are in the GitHub / Zenodo record named in Data "
        "Availability, or delete the first sentence of this paragraph."))

    rewrite_after(P(160), "Figure 5.",
        "** Recommended approaches for RNA-seq combined with microarrays.** PCA (left, "
        "share of variance on the axes) and tSNE (right) of the harmonized data, coloured "
        "by batch (top row) and diagnosis (bottom row): **(A)** FSQN R in D (malignant "
        "samples only, KNN; 6,285 samples); **(B)** ComBat in D (malignant samples only, "
        "no imputation; 6,285 samples); **(C)** M-ComBat in I (rare batches removed, KNN; "
        "reference batch RNA-seq fresh-frozen poly-A; 6,803 samples). Colours as in "
        "Figure 4. Marker correlation and cross-batch prediction (DLBCL versus FL in D) of "
        "each approach and of the unharmonized data are given in Table 3.",
        "Figure 5 legend")
    rewrite_after(P(162), "Alt text:",
        " Grids of PCA and tSNE plots coloured by batch and by diagnosis for FSQN R and "
        "ComBat on malignant samples and for M-ComBat after removal of rare batches, all "
        "on RNA-seq combined with microarrays.", "Figure 5 alt")

    segs, joined = segments(P(172))
    replace_span(P(172), 0, len(joined), markup_runs(
        "Figure 6C shows the marker correlation, the cross-batch prediction and the four "
        "scores of the 22 recommended approaches, grouped by the leaves of the decision "
        "tree, with the medians of the confounding gradient at λ = 0 (balanced batches) "
        "and λ = 1 (one diagnosis per batch) and the marker correlation threshold (0.7) "
        "as reference lines, so that each value can be read against what harmonizers "
        "reach with and without confounding. The prediction column gives the value the "
        "rule used (DLBCL versus FL for strategy D, three classes otherwise) next to that "
        "of the unharmonized data of the same strategy and imputation (open circles).",
        segs[0][0].find(W("rPr"))))
    LOG.append("rewrite [Figure 6C text]")

    rewrite_after(P(181), "Figure 6.",
        "** Confounding gradient, factor effects, scores of the recommended approaches "
        "and decision tree.** **(A)** Batch mixing (left) and diagnosis retention (right), "
        "each the mean of the min–max-scaled global and local scores, of the six "
        "recommended methods against the measured Cramér's V between batch and diagnosis "
        "of the gradient designs: lines, mean of three replicate draws; bands, mean ± SD; "
        "vertical lines, the real data on the five gradient batches (V = 0.40, dashed) and "
        "on all 7,174 samples (V = 0.36, dotted). **(B)** Mean one-way η² of the four "
        "experimental factors over the reduced panel (22 metrics) and over all 87 metrics. "
        "**(C)** Marker correlation (biomarker correlation preservation), cross-batch "
        "prediction and the four scores of the 22 recommended approaches (rows: method, "
        "strategy, imputation and post-removal), grouped by decision-tree leaf and "
        "coloured by method; dashed and dotted lines, gradient medians at λ = 0 (balanced "
        "batches) and λ = 1 (one diagnosis per batch); dotted black line, marker "
        "correlation threshold 0.7; open circles, cross-batch prediction of the "
        "unharmonized data of the same strategy and imputation (DLBCL versus FL for "
        "strategy D). **(D)** Decision tree: (1) biomaterial and platform type of the "
        "dataset (seven leaves), (2) recommended method with alternatives, (3) "
        "recommended imputation and (4) quality control by visual inspection (batches "
        "should mix, biology groups should not), followed by optional post-removal of one "
        "outlier batch.", "Figure 6 legend")
    rewrite_after(P(183), "Alt text:",
        " Line plots of batch mixing and diagnosis retention against the confounding "
        "level, a bar plot of factor effect sizes, dot plots of the scores of the 22 "
        "recommended approaches with reference lines, and the harmonization decision tree "
        "with seven leaves.", "Figure 6 alt")

    tr(P(187), [
        ("(Supplementary Figure 14A)", "(Supplementary Figure 8A)"),
        ("(Supplementary Figure 14B)", "(Supplementary Figure 8B)"),
        ("(Supplementary Figure 14C)", "(Supplementary Figure 9A; diagnosis retention "
         "and separation in Supplementary Figure 9B, C)"),
        ("(Supplementary Figure 14)", "(Supplementary Figures 8 and 9)"),
        ("DLBCL cell-of-origin subtypes before and after harmonization are shown in "
         "Supplementary Figure 15. ", ""),
        ("(Supplementary Figure 16)", "(Supplementary Figure 10)"),
    ], "thresholds")
    tr(P(188), [
        ("(Figure 6, Supplementary Figure 17)",
         "(Figure 6A, Supplementary Figures 11 and 12A, B)"),
        ("Supplementary Figure 17A shows where the recommended methods sit among all 14 "
         "methods; Supplementary Figure 17F compares the recommended methods with each "
         "other on a scale where their differences are visible.",
         "Supplementary Figure 11A–F shows all 14 methods on the six scores, and Figure "
         "6A the recommended methods only, on a scale where their differences are "
         "visible."),
        ("Of 78 method × score trends, 43 changed with confounding by both criteria.",
         "Of 78 method × score trends on the six scores, 43 changed with confounding by "
         "both criteria; on the four scores of Supplementary Figure 11G–J, 37 of 52 "
         "did."),
        ("(median rank 1 at λ = 0.5–0.9; Supplementary Figure 17)",
         "(median rank 1 at λ = 0.5–0.9; Supplementary Figure 12A, B)"),
        ("The rank of a covariate method under strong confounding therefore reflects the "
         "covariate, not batch mixing.",
         "The rank of a covariate method under strong confounding therefore reflects the "
         "covariate, not batch mixing. Across the 14 batch-removal strategies, the "
         "confounding of a strategy did not predict its best diagnosis scores (Spearman "
         "ρ = −0.20, p = 0.50, for global diagnosis retention; ρ = 0.07, p = 0.82, for "
         "local diagnosis separation; Supplementary Figure 11K, L)."),
    ], "gradient")
    tr(P(189), [
        ("(Supplementary Figure 18)", "(Supplementary Figure 12C–J)"),
        ("Its rank on the test part was better", "Its rank on the test part "
         "(Supplementary Figure 12C–F) was better"),
        ("in 4 folds the chosen ComBat or limma could not run on the test cohorts, where "
         "each batch held one diagnosis.",
         "in three K folds and one C fold the chosen ComBat or limma could not run on the "
         "test cohorts, where each batch held one diagnosis (skull-and-crossbones in "
         "Supplementary Figure 12C, D)."),
        ("(Mann–Whitney false discovery rate 0.38",
         "(Supplementary Figure 12G–J; Mann–Whitney false discovery rate 0.38"),
    ], "leave-cohort-out")

    segs, joined = segments(P(205))
    replace_span(P(205), 0, len(joined), markup_runs(
        "The recommended approaches form a decision tree with four levels (Figure 6D): "
        "(1) the biomaterial, platform and sample composition of the dataset, (2) the "
        "recommended method, (3) the recommended imputation and (4) quality control by "
        "visual inspection, followed by optional post-removal. Level 1 has seven leaves: "
        "fresh-frozen only (RNA-seq and microarrays); FFPE only (RNA-seq and "
        "microarrays); RNA-seq only (any biomaterial); malignant samples only (any "
        "platform and biomaterial); rare batches removed (batches of fewer than 50 "
        "samples); microarrays only (any biomaterial); and any biomaterial and platform "
        "without sample removal. The multi-platform pool of the selection rule gave two "
        "leaves, because its accepted approaches came from two strategies, D and I. A "
        "single platform with a single biomaterial is not a leaf, because no benchmark "
        "strategy isolated such a dataset.", segs[0][0].find(W("rPr"))))
    LOG.append("rewrite [tree levels]")

    segs, joined = segments(P(211))
    replace_span(P(211), 0, len(joined), markup_runs(
        "For malignant samples on any platform and biomaterial (D), FSQN R with KNN "
        "imputation ranked first, with FSMVN (KNN) and ComBat (no imputation) as "
        "alternatives (4 approaches); the recommendation did not depend on the strategies "
        "derived from the first FSQN R harmonization. After removal of rare batches (I), "
        "M-ComBat is recommended without imputation or with KNN (3 approaches). For "
        "microarrays only (H), Angel with softImpute and post-removal was accepted, and "
        "without any sample removal (S0) Angel with any imputation (5 approaches); in S0 "
        "its batches of the same diagnosis overlapped on PCA but stayed apart on tSNE. On "
        "each leaf, the user checks the marker correlation (≥ 0.70), the cross-batch "
        "prediction (not more than 0.05 below the unharmonized data) and the PCA, UMAP "
        "and tSNE plots, on which batches should mix and biology groups should stay "
        "apart.", segs[0][0].find(W("rPr"))))
    LOG.append("rewrite [tree leaves]")
    tr(P(213), [("(Figure 6F)", "(Figure 6D)")], "post-removal")

    # ----------------------------------------------------------------- discussion
    tr(P(219), [("(Figure 1D, 1E)", "(Supplementary Figure 1)")], "discussion confounding")
    tr(P(249), [("(Supplementary Figure 14A)", "(Supplementary Figure 8A)"),
                ("(Supplementary Figure 17)", "(Supplementary Figure 12A, B)")],
       "discussion panel")
    tr(P(256), [("RNA-seq-only and multi-platform scenarios",
                 "RNA-seq-only and malignant-only multi-platform scenarios")],
       "discussion SVA FSQN")
    tr(P(264), [("FSQN R (with FSMVN, ComBat and M-ComBat as alternatives) for RNA-seq "
                 "combined with microarrays, and Angel for fresh-frozen data",
                 "FSQN R (with FSMVN and ComBat as alternatives) for malignant samples on "
                 "any platform, M-ComBat after removal of rare batches, and Angel for "
                 "fresh-frozen, microarray-only and whole-cohort data")], "conclusions")

    # -------------------------------------------------------------------- Table 3
    tr(P(135), [("grouped by scenario and method.",
                 "grouped by decision-tree leaf (Figure 6D) and method.")], "Table 3 title")
    tbl = K[136]
    rows = tbl.findall(W("tr"))
    leaf_by_method = {"FSQN R": "Malignant only", "ComBat": "Malignant only",
                      "FSMVN": "Malignant only", "M-ComBat": "Rare batches removed"}
    for tr_el in rows[1:]:
        cells = tr_el.findall(W("tc"))
        cp = cells[0].find(W("p"))
        method = "".join(t.text or "" for t in cells[1].iter(W("t"))
                         if not any(a.tag == W("del") for a in t.iterancestors()))
        txt = segments(cp)[1]
        if txt == "RNA-seq + microarrays" and method in leaf_by_method:
            tr(cp, [(txt, leaf_by_method[method])], "Table 3 leaf")
        elif "(information only)" in txt:
            tr(cp, [(" (information only)", "")], "Table 3 leaf")

    # ------------------------------------------------------ supplementary legends
    ref_leg = P(272)
    s1 = new_paragraph(ref_leg,
        "**Supplementary Figure 1.** Confounding between batch and diagnosis. Number of "
        "samples per RNA batch (rows) and diagnosis or B-cell population (columns) on a "
        "log colour scale (1 to 1,000 samples); empty cells, no samples. The 18 "
        "multi-diagnosis batches (top) share diagnoses and connect all batches; the 11 "
        "single-diagnosis batches (bottom, grey italic labels) hold 28.8 % of the "
        "samples. Bar plot on the right: number of diagnoses per batch. Row and column "
        "colour bars follow the batch and biology colours of Figure 1A, B. Bias-corrected "
        "Cramér's V between batch and diagnosis is 0.36, the adjusted mutual information "
        "0.26 (Table 1).")
    K[272].addprevious(s1)
    tr(P(272), [("Supplementary Figure 1", "Supplementary Figure 2")], "S2 label")

    rewrite_after(P(274), "Supplementary Figure 2.",
        " Gene expression distributions, log2(x + 1), of 30 representative cohorts of the "
        "S0 strategy (rows, with the sample number) without imputation, with KNN and with "
        "softImpute imputation (columns). Each density pools all samples of a cohort and "
        "is coloured by platform (RNA-seq, or the GEO platform of the microarray grouped "
        "by manufacturer); numbers at the right, modes counted in the smoothed density.",
        "S3 legend")
    tr(P(274), [("Supplementary Figure 2.", "Supplementary Figure 3.")], "S3 label")

    rewrite_after(P(277), "Supplementary Figure 3.",
        " Clustermap of the Jaccard index between the gene sets of all 42 combinations of "
        "batch-removal strategy and imputation (strict, KNN, softImpute), annotated by "
        "strategy and imputation.", "S4 legend")
    tr(P(277), [("Supplementary Figure 3.", "Supplementary Figure 4.")], "S4 label")

    rewrite_after(P(279), "Supplementary Figure 4.",
        " Metric availability. **(A)** Number of harmonization metrics computed for each "
        "approach: rows, strategy and imputation; columns, harmonization method and "
        "post-removal (False, all batches kept; True, one batch removed), annotated by "
        "method and harshness level. **(B)** Share of approaches with every metric "
        "defined, per strategy and imputation (no imputation = strict NA exclusion): the "
        "reduced panel of 22 metrics (left) against all 87 scoring metrics (right); cell "
        "text, approaches with every metric defined / all approaches.", "S5 legend")
    tr(P(279), [("Supplementary Figure 4.", "Supplementary Figure 5.")], "S5 label")
    tr(P(281), [("Supplementary Figure 5.", "Supplementary Figure 6.")], "S6 label")
    tr(P(285), [("Supplementary Figure 6.", "Supplementary Figure 7.")], "S7 label")
    for i in range(287, 294):
        delete_paragraph(P(i), f"old S{i - 280}")

    rewrite_after(P(295), "Supplementary Figure 14.",
        " The thresholds of the selection rule. **(A)** Marker correlation (biomarker "
        "correlation preservation: mean per-gene Spearman ρ of 56 marker genes before and "
        "after harmonization) of the 2,234 approaches by method; dashed line, 0.7. **(B)** "
        "Cross-batch prediction F1 minus that of the unharmonized data, by method; dashed "
        "line, −0.05; dot colour, above the permutation null (p < 0.05) or not. Boxes, "
        "quartiles and median; box colour, method.", "S8 legend")
    tr(P(295), [("Supplementary Figure 14.", "Supplementary Figure 8.")], "S8 label")
    s9 = new_paragraph(ref_leg,
        "**Supplementary Figure 9.** Label leakage through the diagnosis covariate. SVA "
        "and ComBat with and without the diagnosis covariate along the confounding "
        "gradient: **(A)** cross-batch diagnosis prediction (macro-F1), **(B)** global "
        "diagnosis retention and **(C)** local diagnosis separation against the measured "
        "Cramér's V between batch and diagnosis; points, mean of three replicate draws; "
        "error bars, SD.")
    K[295].addnext(s9)
    delete_paragraph(P(297), "old S15")

    rewrite_after(P(298), "Supplementary Figure 16.",
        " Robustness of the selection. Agreement between the reference ranking and seven "
        "variants of the panel and the scores (x axis): panels built at |ρ| ≥ 0.9, at "
        "|ρ| ≥ 0.7 and from all 87 metrics; score bars as the mean of their panel metrics "
        "or as the mean over metric groups; local scores from the runner-up metrics; and "
        "diagnosis separation computed on multi-diagnosis batches only. **(A)** Kendall "
        "τ-b of the approach ranking; **(B)** Jaccard index of the first three "
        "approaches; **(C)** Jaccard index of the Pareto front. Bars, mean over the six "
        "scenario pools of the selection rule; error bars, SD; dots, pools. **(D)** Share "
        "of the eight rankings (reference and seven variants) in which each of the 22 "
        "recommended approaches is on the Pareto front, grouped by pool and coloured by "
        "method.", "S10 legend")
    tr(P(298), [("Supplementary Figure 16.", "Supplementary Figure 10.")], "S10 label")

    rewrite_after(P(299), "Supplementary Figure 17.",
        " Confounding gradient, all 14 methods. **(A–F)** Marker correlation (biomarker "
        "correlation preservation, A), cross-batch diagnosis prediction (macro-F1, B), "
        "global batch removal (C), local batch mixing (D), global diagnosis retention (E) "
        "and local diagnosis separation (F; C–F min–max scaled) against the measured "
        "Cramér's V: lines, mean of three replicate draws; bands, ± SD; dotted lines, "
        "designs without the size cap (replicate 1); crosses at V = 1, the 11 real "
        "single-diagnosis batches; vertical lines, the real data on the five gradient "
        "batches (V = 0.40, dashed) and on all 7,174 samples (V = 0.36, dotted). "
        "**(G–J)** Slope on V, with 95 % confidence interval, of marker correlation (G), "
        "cross-batch prediction (H), batch mixing (I) and diagnosis retention (J; global "
        "+ local means); filled, Spearman FDR < 0.05 and a change from λ = 0 to λ = 1 "
        "(λ = 0.9 for ComBat and M-ComBat with the diagnosis covariate, which cannot run "
        "at λ = 1) larger than twice the replicate SD; open, not both criteria. **(K, L)** "
        "Cramér's V of the 14 batch-removal strategies against the best global diagnosis "
        "retention (K) and the best local diagnosis separation (L) of their approaches; "
        "Spearman ρ and p above the panels; colours as in Figure 2A.", "S11 legend")
    tr(P(299), [("Supplementary Figure 17.", "Supplementary Figure 11.")], "S11 label")

    rewrite_after(P(300), "Supplementary Figure 18.",
        " Ranks along the confounding gradient and leave-cohort-out validation. **(A, B)** "
        "Rank under the selection rule (1 = best) against the measured Cramér's V "
        "(medians of three replicate draws) for the methods of the final selection with "
        "no harmonization as reference (A) and for all 14 methods of the gradient (B); "
        "dashed line, the real data on the five gradient batches (V = 0.40). **(C–F)** "
        "Rank on the test cohorts (1 = best) of the method chosen on the training "
        "cohorts, per fold: RNA-seq only (strategy C) in panel C, FFPE only (K) in D, FF "
        "only (J) in E and no removal (S0) in F; coloured bars, the chosen method; grey bars, a random method "
        "(mean ± SD of the rank, uniform on 1 to n); dashed line, top-3 rank limit; "
        "skull-and-crossbones, the chosen method failed on the test part; 'test part not "
        "evaluable', a test part with one batch or one diagnosis. **(G–J)** Decrease "
        "against the best approach on the test part (0 = best) for batch mixing (G) and "
        "diagnosis retention (H; global + local means), marker correlation (I) and "
        "cross-batch prediction (J): bars, mean ± SD of the chosen method per fold (dots) "
        "and of every test run of the same folds (random method); brackets, two-sided "
        "Mann–Whitney test with Benjamini–Hochberg FDR over the four scores (ns, not "
        "significant). The Monte Carlo test of the ranks and the exact Poisson-binomial "
        "test of the top-1 and top-3 hits are reported in the Results.", "S12 legend")
    tr(P(300), [("Supplementary Figure 18.", "Supplementary Figure 12.")], "S12 label")

    # ---------------------------------------------------------- mapping note
    K[270].addnext(note(K[270],
        "Figure numbering follows the final Figma page 5 (2026-11-18). The notebook "
        "panels were split and edited in Figma, so one old panel can map to several new "
        "ones. Main figures: 1A–C = old 1A–C; old 1D (bar plot by batch and biology) "
        "removed; old 1E → Supplementary Figure 1. Figures 2 and 3 as before (Figure 3 "
        "clusters renamed). Figures 4–5 show the harmonized data only (unharmonized "
        "halves and the platform row removed). 6A = old gradient panel; 6B = old 6B; "
        "6C = old 6C/D; 6D = old 6F (tree with seven leaves). Supplementary: S1 = old "
        "Figure 1E; S2 = old S1; S3 = old S2; S4 = old S3; S5A new (metrics per "
        "approach), S5B = old S4; S6 = old S5; S7 = old S6; old S7–S13 (embedding grids) "
        "removed; S8 = old S14A, B; S9A–C = old S14C split; old S15 (cell-of-origin "
        "plots) removed; S10A–C = old S16a split, S10D = old S16b; S11A–F = old S17a "
        "split, S11G–J = old S17b (four scores), S11K–L = old S17c split; old S17d and "
        "S17f removed; S12A–B = old S17e; S12C–F = old S18a without the test statistics "
        "in the panel titles; S12G–J = old S18b. 6 main + 12 supplementary figures "
        "(19 before). Delete this note before submission."))

    d.save(str(DST))
    bad = [x for x in LOG if not x.startswith(("ok", "rewrite", "deleted"))]
    print("\n".join(LOG))
    print(f"\n{len(LOG)} operations, {len(bad)} problems -> {DST}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
