#!/usr/bin/env python
"""Tracked-change edits for `Harmonization_metrics_extended.docx` (2026-08-02 pass).

The document is destined for GitHub/Zenodo rather than for the journal, so this pass is
restricted to what Daniil asked for: figure renumbering to match the delivered files,
language and grammar, and numerical precision.

Three groups of edits
---------------------
1. **Figure renumbering.** The delivered artwork uses one continuous `Extended Figure`
   sequence, but the document's own numbering is three behind it:

       document "Figure 6 / 7 / 8"        ->  Extended Figure 1 / 2 / 3
       document "Extended Figure 1 .. 10" ->  Extended Figure 4 .. 13

   Verified by matching every delivered `Extended Figure *.pdf` text layer against the
   document's own legends (see NAR_review_260802.md §5).

2. **Numbers.** Every quoted statistic was recomputed on the 2,234-approach analysis set
   (`Supplementary File 3.csv.gz` for polarity-adjusted PCReg, `metrics_comprehensive_260609.csv`
   for un-normalized LISI and expression statistics). Only the ones that did not reproduce
   are changed here; the full audit, including the many that reproduced exactly, is in
   NAR_review_260802.md §3.2.

3. **Language.** Typographical and register fixes.

Why `safe_tracked_replace` and not `tracked_replace`
---------------------------------------------------
This document holds no `w:sdt` citations, so `tracked_replace` would technically be safe.
`safe_tracked_replace` is used anyway for one property that matters here: it edits only
runs that are direct children of the paragraph, and after each call the replaced text moves
into `w:del`, which the next search no longer sees. That makes a left-to-right sweep of
overlapping figure references collision-proof — "Extended Figure 5" can be rewritten to
"Extended Figure 8" in a paragraph that later contains a genuine "Extended Figure 8"
without the second edit landing on the first edit's output.

Output: Harmonization_metrics_extended_260802.docx
"""
import os
import re
import sys

import docx

sys.path.insert(0, os.path.expanduser("~/FL_harmonization/.claude/skills"))
from nar_review_tools import safe_tracked_replace  # noqa: E402
from word_rewrite_trackchanges import set_revision_identity  # noqa: E402

SRC = "Harmonization_metrics_extended.docx"
DST = "Harmonization_metrics_extended_260802.docx"

set_revision_identity("Claude (metrics review 2026-08-02)", "2026-08-02T00:00:00Z")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


# ── figure renumbering ────────────────────────────────────────────────────────
# Matches an optional "Supplementary "/"Extended " qualifier, "Figure"/"Figures",
# then the leading number only. Panel letters that follow ("6A", "5H") are left in
# place because only the numeral is rewritten, and a bare "Supplementary Figure N"
# is recognised so it can be skipped.
REF = re.compile(r"(Supplementary |Extended )?(Figures?)\s+(\d+)")

# References that carry the figure number more than once and therefore need the
# whole expression rewritten in one go. Applied before the generic sweep.
SPECIALS = [
    ("Figures 6-8", "Extended Figures 1-3"),
    ("Extended Figure 5G, 5H, 5K, 5L", "Extended Figure 8G, 8H, 8K, 8L"),
    ("Extended Figure 4 and 5", "Extended Figure 7 and 8"),
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


def figure_edits(text):
    """Ordered (old, new) pairs for every figure reference in one paragraph."""
    out = []
    for m in REF.finditer(text):
        prefix, word, num = m.group(1) or "", m.group(2), int(m.group(3))
        new_num = renumber(prefix, word, num)
        if new_num is None:
            continue
        old = m.group(0)
        new = f"Extended {word} {new_num}" if not prefix else f"{prefix}{word} {new_num}"
        out.append((old, new))
    return out


# ── numerical corrections ─────────────────────────────────────────────────────
# (anchor substring that identifies the paragraph, [(old, new), ...])
NUMBER_EDITS = [
    # 95% CI upper bound: bootstrap gives -0.115, the document prints "-11".
    ("weak negative correlation (Spearman r = -0.159",
     [("95% CI -0.21, -11", "95% CI -0.21, -0.12")]),

    # 13_fsmvn is not pinned at the optimum: it ranges 0.9967-1.0000 (median 1.0000).
    # Only 33_amdbnorm is exactly 1.0000 in all 14 of its runs.
    ("33_amdbnorm and 13_fsmvn both have",
     [("33_amdbnorm and 13_fsmvn both have pcr_RNA_BATCH of exactly 1.0000 in every run — a "
       "global metric pinned at its theoretical optimum, but they were again not selected",
       "33_amdbnorm has PCReg RNA_BATCH of exactly 1.0000 in all 14 of its runs and 13_fsmvn "
       "reaches 0.9967-1.0000 (median 1.0000) — a global metric pinned at its theoretical "
       "optimum, but they were again not selected")]),

    # LISI MAD over all approaches recomputes to 0.109, not 0.103.
    ("median for all approaches 1.16 and MAD 0.103",
     [("median for all approaches 1.16 and MAD 0.103",
       "median for all approaches 1.17 and MAD 0.109")]),

    # Mann-Whitney best vs rest on iLISI RNA_BATCH.
    ("two-sided Mann-Whitney p = 2.0*10-7 for batch",
     [("p = 2.0*10-7 for batch", "p = 8.5*10-9 for batch")]),

    # Spearman iLISI ~ cLISI recomputes to 0.523 on the 2,150 approaches for which the
    # un-normalized LISI values exist (20_shambhala is absent from the metric snapshot).
    ("positive correlation of biology mixing with the batch one",
     [("Spearman r = 0.527, p = 7*10-160 for the entire dataset",
       "Spearman r = 0.523, p = 1.8*10-151 for the entire dataset, n = 2,150 approaches for "
       "which un-normalized LISI values were available"),
      ("Spearman r varied from 0.374 to 0.815 with median 0.617",
       "Spearman r varied from 0.355 to 0.820 with median 0.650")]),

    # Per-method mean percentages of samples / genes carrying at least one NA.
    ("All samples had all genes with defined expression values for 19 out of 31",
     [("for 19 out of 31 harmonization methods, regardless of the batch removal strategy used, "
       "8 more methods had a minor percentage of 0.44 - 2.3% samples with at least one NA and "
       "4 methods (20_shambhala, 26_xpn, 15_fsqn_py, 17_quantile) had 26-67% samples with at "
       "least one NA",
       "for 18 of the 30 harmonization methods for which the metric snapshot holds expression "
       "statistics, regardless of the batch removal strategy used; 9 more methods had a minor "
       "percentage of 0.003 - 1.4% samples with at least one NA, and 3 methods (26_xpn, "
       "15_fsqn_py, 17_quantile) had 30.2 - 38.1% samples with at least one NA"),
      ("the same 19 harmonization methods returned no NA at all, 11 more methods had "
       "0.05-33.6% genes",
       "the same 18 harmonization methods returned no NA at all, 9 more methods had "
       "0.003-2.4% genes, two methods (15_fsqn_py and 17_quantile) had 13.0 and 16.2% genes")]),

    # The two 99th percentiles are attached to the wrong methods, and the maxima are the
    # per-method means over the analysis set.
    ("08_inmoose_combatseq and 06_combat_seq had outliers",
     [("with expression value above 1 million (5.08*108, 1.69 million, respectively), whereas "
       "their 99th percentiles were only 18.5 and 17.9, respectively",
       "with mean maximum expression of 1.46*1011 and 2.76*108 respectively, whereas their "
       "99th percentiles were only 17.9 and 18.5"),
      ("Generally, 20 out of 31 harmonization methods had minimum gene expression value below "
       "zero (the lowest one -40.6 for 13_fsmvn)",
       "Generally, 19 of the 30 harmonization methods with available expression statistics had "
       "a mean minimum gene expression value below zero (the lowest one -40.6 for 13_fsmvn)")]),

    # 0.1 -> 0.7 is an increase, not the described decrease; the intended value is 0.07.
    ("with gradual decrease of local composite impact from 0.1 to 0.7",
     [("from 0.1 to 0.7 (in 28_npn) and then raising to 0.11",
       "from 0.10 to 0.07 (in 28_npn) and then rising to 0.11")]),

    # 20_shambhala is missing from the metric snapshot, so its expression range is unverified.
    ("20_shambhala had generally high expression outputs",
     [("20_shambhala had generally high expression outputs, with 555004.7 maximum expression "
       "and 1359.6 median.",
       "20_shambhala had generally high expression outputs, with 555004.7 maximum expression "
       "and 1359.6 median (these two values could not be re-derived from the deposited metric "
       "table, in which 20_shambhala is absent).")]),
]


# ── language corrections ──────────────────────────────────────────────────────
LANGUAGE_EDITS = [
    ("Additional 8 methods (33_amdbnorm", [("and the sameslow decay", "and the same slow decay")]),
    ("The rest 18 methods resulted", [("The rest 18 methods", "The remaining 18 methods")]),
    ("For COHORT_LABEL", [("we observed the inversed pattern", "we observed the inverse pattern")]),
    ("The clustermap best approaches were consentingly found",
     [("were consentingly found", "were consistently found")]),
    ("This can be explained by the fast that selecting",
     [("explained by the fast that", "explained by the fact that")]),
    ("Multi-batch PLATFROM_RNA column", [("PLATFROM_RNA", "PLATFORM_RNA")]),
    ("DCS by PLATFORM_RNA", [("DCS by PLATFORM_RNA", "DSC by PLATFORM_RNA")]),
    ("that could be presumable explained by harmonization methods",
     [("presumable explained", "presumably explained")]),
    ("LISI metrics stratification by batch removal strategy revealed a supremacy",
     [("revealed a supremacy of the clustermap best approaches",
       "revealed the highest values for the clustermap best approaches")]),
    ("indicating that minor batch removal or selecting malingnant only samples",
     [("selecting malingnant only samples", "selecting malignant-only samples")]),
    ("Only the entire set of metrics reveal", [("metrics reveal’s the truly best",
                                                "metrics reveals the truly best")]),
    ("Local metrics showed the similar pattern of low harshness methods having the best",
     [("having the best pefromance", "having the best performance"),
      ("showed the similar pattern", "showed a similar pattern")]),
    ("We aimed to test whether it’s true", [("whether it’s true", "whether this is true")]),
    ("There is no royal way in the field",
     [("There is no royal way in the field of the cross-platform transcriptomic harmonization.",
       "There is no shortcut in cross-platform transcriptomic harmonization.")]),
    ("we build the composite performance score",
     [("we build the composite performance score", "we built the composite performance score")]),
    ("build a standard scatteplot", [("build a standard scatteplot",
                                      "built a standard scatterplot")]),
    ("Taken together, the metrics of local type were the most important",
     [("despite they comprised only", "even though they comprised only")]),
    ("with 10/15 clustermap best approaches residing it it",
     [("residing it it", "residing in it")]),
    ("harmonization tools differ by their ability",
     [("harmonization tools differ by their ability", "harmonization tools differ in their "
                                                      "ability")]),
]


def visible(p):
    """Text as Word displays it: original plus insertions, deletions excluded."""
    return "".join(t.text or "" for t in p.findall(f".//{W}t"))


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
                print(f"  [{status}] {tag}: {old[:80]!r}")

    # 1 ── numbers and language, located by text anchor.
    #      Resolve every anchor to an element reference before mutating anything: once an
    #      edit lands, the original wording lives in w:delText and a text search misses it.
    resolved = []
    for anchor, pairs in NUMBER_EDITS + LANGUAGE_EDITS:
        resolved.append((find_p(body, anchor), pairs, anchor))
    for p, pairs, anchor in resolved:
        apply(p, pairs, anchor[:40])

    # 2 ── figure renumbering, paragraph by paragraph, left to right.
    n_refs = 0
    for p in paragraphs:
        text = visible(p)
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

    print(f"\nfigure references rewritten: {n_refs}")
    print(f"ok {report['ok']} | not-found {report['not-found']} | unsafe {report['unsafe']}")
    doc.save(DST)
    print(f"wrote {DST}")


if __name__ == "__main__":
    main()
