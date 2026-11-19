#!/usr/bin/env python3
"""Apply the 2026-09-12 combined referee / rewrite / scientific-review pass to
`FL_harmonization_article_NAR_260802_3rd_iteration.docx` as Word tracked changes.

Accept All  -> the corrected manuscript.
Reject All  -> the original, byte for byte.

Three skills were applied together:
  * nar-review        — referee findings, severity-ranked (NAR_review_260912.md)
  * word-rewrite      — NAR format compliance (page size), [NAR EDITOR NOTE] items
  * scientific-review — P1/P2/P3/P4/P5/P7/P9 author-side principles

Citations are Mendeley `w:sdt` content controls (78 sdt / 64 MENDELEY_CITATION).
Every text edit therefore goes through `safe_tracked_replace`, which touches only
direct-child runs and leaves anything nested in `w:sdt` / `w:hyperlink` intact.
Never use `word_rewrite_trackchanges.tracked_replace` on this document.

Run from `figures_for_article/`:
    python3 edit_python_scripts/apply_nar_review_edits_260912.py
"""

from __future__ import annotations

import itertools
import re
import sys
from pathlib import Path

import docx
from docx.oxml.ns import qn
from docx.shared import Cm

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent                      # FL_harmonization/
sys.path.insert(0, str(ROOT / ".claude" / "skills"))

import word_rewrite_trackchanges as wrt        # noqa: E402
from word_rewrite_trackchanges import (        # noqa: E402
    delete_paragraph,
    insert_after,
    note_paragraph,
    set_revision_identity,
)
from nar_review_tools import safe_tracked_replace  # NOT tracked_replace  # noqa: E402

MSDIR = HERE.parent / "FL_manuscript_versions"
SRC = MSDIR / "FL_harmonization_article_NAR_260802_3rd_iteration.docx"
DST = MSDIR / "FL_harmonization_article_NAR_260912.docx"

set_revision_identity("Claude (NAR referee + scientific review 2026-09-12)",
                      "2026-09-12T00:00:00Z")

W_T = qn("w:t")
NOTE_MARKERS = ("[REVIEWER NOTE]", "[EDITOR NOTE]", "[NAR EDITOR NOTE]")


# --------------------------------------------------------------------------- #
# Edits.  (anchor, [(old, new), ...])  -- `new=""` is a pure tracked deletion. #
# --------------------------------------------------------------------------- #
EDITS: list[tuple[str, list[tuple[str, str]]]] = [

    # ---- Title -------------------------------------------------------- P9 --
    ("Benchmarking of bulk transcriptomic harmonization tools", [
        ("feature specific quantile normalization", "feature-specific quantile normalization"),
    ]),

    # ---- Abstract (199/200 words: every edit below is net word-neutral) -----
    # 14 x 3 x 33 x 2 = 2,772, the cross-product actually run.  31 is the count
    # that SURVIVES the pct_samples_allNA < 5 filter, not the count evaluated.
    ("Cross-platform harmonization of bulk transcriptomic datasets", [
        ("3 imputation methods, 31 harmonization algorithms",
         "3 imputation methods, 33 harmonization algorithms"),
        ("utilize 31 harmonization and 3 imputation methods",
         "utilize 33 harmonization and 3 imputation methods"),
    ]),

    # ---- Introduction --------------------------------------------------- P4 --
    ("Batch-explained variance was ten times higher", [
        ("than the biology explained one", "than the biology-explained variance"),
    ]),
    ("The tool includes code for evaluating", [
        ("evaluating 31 harmonization and 3 imputation methods",
         "evaluating 33 harmonization and 3 imputation methods"),
    ]),
    # P1: promotional close with no testable content.
    ("Together, these results and computational tools", [
        ("Together, these results and computational tools help convert large-scale "
         "omics data into foundational AI models, biological insight and, ultimately, "
         "into clinically actionable cancer biomarkers.",
         "Together, the benchmark and the ComboBatch tool provide a basis for "
         "harmonizing retrospective multi-platform transcriptomic datasets for "
         "biomarker discovery."),
    ]),

    # ---- Materials and methods ------------------------------------------------
    ("For RNA-seq datasets gene expression profiling was done", [
        ("back potentiated using the formula", "back-transformed using the formula"),
    ]),
    ("We devised a systematic batch naming convention", [
        ("is labelled <Platform_name>", "is labeled <Platform_name>"),
    ]),
    ("Each implemented method was assigned a qualitative harshness score", [
        ("Among the methods tested, the two ones were the simplest ones: FSMVN and "
         "median scaling, transforming biology to the least extent.",
         "Among the methods tested, FSMVN and median scaling were the simplest, "
         "transforming biology to the least extent."),
    ]),
    # P5: Metric_polarity holds 344 rows (87 scoring + 257 non-scoring), and
    #     Table_S3_gene_panel holds 633 unique genes over 834 gene-signature rows.
    ("For harmonization quality assessment, we assembled a set of 87", [
        ("together with 247 additional metrics", "together with 257 additional metrics"),
        ("572 biomarker genes for correlation", "633 biomarker genes for correlation"),
    ]),

    # ---- Results ---------------------------------------------------------------
    ("For each of the 2,234 successful harmonization approaches", [
        ("we computed up to 229 harmonization metrics per approach",
         "we computed up to 344 harmonization metrics per approach"),
    ]),
    ("we manually assigned polarity values", [
        ("For 87 of the 229 computed metrics", "For 87 of the 344 computed metrics"),
        ("For the rest 142 additional metrics polarity was set as 0",
         "For the remaining 257 metrics polarity was set as 0"),
        ("Polarity assignments for all the 229 metrics",
         "Polarity assignments for all the 344 metrics"),
    ]),
    ("confirming that cluster identity was not an artefact", [
        ("was not an artefact of the primary", "was not an artifact of the primary"),
    ]),
    ("Notably, Softimpute also introduced spurious trimodal", [
        ("an imputation artefact consistent", "an imputation artifact consistent"),
    ]),
    # Major: reads as the paper's final verdict, but MNN is withdrawn two
    # sub-sections later on biomarker-preservation grounds.
    ("Based on the clustermap visual inspection combined with quantitative", [
        ("MNN and SVA emerged as the most versatile harmonization methods:",
         "By the clustermap metrics, MNN and SVA emerged as the most versatile "
         "harmonization methods:"),
    ]),
    ("To integrate the multi-dimensional metric signals", [
        ("Figc ure 6A", "Figure 6A"),
    ]),
    ("In order to independently assess harmonization quality", [
        ("sheets Table_S3_gene_panel", "sheet Table_S3_gene_panel"),
    ]),
    ("Biomarker gene correlation before and after harmonization", [
        ("is achieved with a cost of biology corruption",
         "is achieved at the cost of biology corruption"),
        ("Control the correlation over housekeeping genes showed no difference",
         "The control correlation over housekeeping genes showed no difference"),
    ]),
    # P2: a cross-reference that names no figure number at all.
    ("We then compared biomarker rank concordance", [
        ("Supplementary Figure D, K", "Supplementary Figure 18D, 18K"),
    ]),
    ("We separately investigated prediction quality by RNA batches", [
        ("Mann-Whitey two-sided raw p", "Mann-Whitney two-sided raw p"),
    ]),
    ("Taken together, the additional assessment of the clustermap best", [
        ("achieve high performance by complete biology corruption",
         "achieve high performance at the cost of complete biology corruption"),
    ]),
    ("For fresh-frozen only datasets", [
        ("but was excluded because of biomarkers correlation vanished",
         "but was excluded because the biomarker correlation vanished"),
    ]),
    ("For mixed RNA-seq and Illumina microarray datasets", [
        ("despite the latter achieved superior global and local batch correction at "
         "the cost of biomarkers rank correlation being lost",
         "despite the latter achieving superior global and local batch correction at "
         "the cost of biomarker rank correlation being lost"),
    ]),

    # ---- Discussion ------------------------------------------------------------
    # 33 were implemented; 34_arsyn and 38_harman carry no analysable run, so
    # every claim about what was *benchmarked/analysed* is over the 31 survivors.
    ("Current benchmarking datasets (TCGA, GTEx, SEQC, MAQC", [
        ("among 33 harmonization tools benchmarked",
         "among the 31 harmonization tools analyzed"),
    ]),
    ("The computational scale of ComboBatch", [
        ("the Zenodo links (add link!) described", "the Zenodo links described"),
    ]),
    ("We note important technical limitations of the current pipeline", [
        ("Two methods, 30_recombat and 37_fabatch, failed at the implementation stage "
         "for technical reasons that remain to be resolved.",
         "Two of the six methods that failed implementation, 30_recombat and "
         "37_fabatch, did so for technical reasons that remain to be resolved."),
    ]),
    ("We also acknowledge additional mathematical limitations", [
        ("six of the 33 implemented methods were not run on all 14 strategies",
         "six of the 31 analyzed methods were not run on all 14 strategies"),
    ]),
    # P1: superlative claim about the literature with no systematic search behind it.
    ("approach clustermap (Figure 3) with additional prediction quality", [
        ("represents, to our knowledge, the largest systematic harmonization "
         "evaluation matrix reported to date in bulk transcriptomics",
         "comprises 194,358 metric values"),
    ]),
    # P1 + internal contradiction: "bias-free" is refuted by the paper's own
    # caveat that the composite averages different metric subsets per strategy.
    ("The practical value of the clustermap-based selection approach", [
        ("provides a bias-free, data-driven ranking", "provides a data-driven ranking"),
    ]),
    # P1: a general principle asserted from a single dataset.
    ("Interestingly, rank normalization and standard quantile normalization", [
        ("This finding illustrates a general principle: algorithmic sophistication in "
         "method design (biology-conditioned normalization, mutual nearest-neighbor "
         "graph construction, surrogate variable modelling) consistently outperforms "
         "generic location-and-scale corrections",
         "In this dataset, methods that condition on biological structure or model "
         "latent factors outperformed generic location-and-scale corrections"),
    ]),
    ("Among the 33 methods benchmarked", [
        ("Among the 33 methods benchmarked, SVA, and FSQN R were the only algorithms",
         "Among the 31 methods analyzed, SVA and FSQN R were the only algorithms"),
    ]),

    # ---- Conclusions -----------------------------------------------------------
    ("In the present study we assembled a GC B cell lymphoma cross-platform cohort", [
        ("showed that among 33 harmonization tools, only SVA and FSQN R",
         "showed that among the 31 harmonization tools analyzed, only SVA and FSQN R"),
    ]),

    # ---- Author contributions --------------------------------------------------
    # Byline reads "Nikolay Borisov"; CRediT read "Nicolas Borisoff".
    ("Daniil Nikitin: Conceptualization, Data curation, Formal analysis", [
        ("Nicolas Borisoff: Conceptualization", "Nikolay Borisov: Conceptualization"),
        ("Nazar Harutyunyan: Data curation, Svetlana Paponova",
         "Nazar Harutyunyan: Data curation. Svetlana Paponova"),
    ]),

    # ---- Supplementary legends and file descriptions ---------------------------
    # NB: the Supplementary Figure 18 legend spans two body paragraphs; panel (I)
    # lives in the second one, so it must be anchored there, not on the caption head.
    ("(I) Scatter plot of cross-batch agreement of extended biomarker genes", [
        ("in the save versus the different biology groups",
         "in the same versus the different biology groups"),
    ]),
    # The "(С)" below is CYRILLIC ES (U+0421), not Latin C.
    ("Supplementary Figure 19. PCA and tSNE plots", [
        ("(С) FSQN R in S0", "(C) FSQN R in S0"),
        ("in FF only script compared to", "in FF only strict compared to"),
    ]),
    ("Supplementary File 2. Excel workbook", [
        ("Excel workbook with four sheets", "Excel workbook with five sheets"),
        ("the polarity coefficients of the 229 harmonization quality metrics",
         "the polarity coefficients of the 344 harmonization quality metrics"),
        ("computational groups and sources of the harmonization quality metric families.",
         "computational groups and sources of the harmonization quality metric families; "
         "and ‘Table_S3_gene_panel’ (Supplementary Table S3), the 633 biomarker "
         "genes across 63 signatures with their coverage, quality-control and per-gene "
         "correlation statistics."),
    ]),
]


# --------------------------------------------------------------------------- #
# Reviewer notes (red italic, inserted after a top-level body paragraph).      #
# --------------------------------------------------------------------------- #
NOTES: list[tuple[str, str]] = [

    ("To integrate the multi-dimensional metric signals",
     "CRITICAL (R1). The harshness comparison in this paragraph runs OPPOSITE to "
     "Supplementary File 3. Recomputing the composite score as described here (polarity "
     "flip, min-max per metric, mean over the 87 scoring metrics) on the 2,234 analysis "
     "rows gives medians low 0.520 / medium 0.497 / high 0.480 and maxima low 0.716 / "
     "high 0.700 - i.e. LOW harshness scores highest and has the higher maximum, whereas "
     "the text states the reverse on both counts. The ordering high < medium < low was "
     "reproduced under five normalization recipes (flip-then-min-max over 2,234 and over "
     "2,407 rows, min-max-then-polarity, rank-percentile, z-score) and under three "
     "aggregations (all rows, post-removal = 0 only, complete-87 only); excluding the "
     "01_raw control widens the gap (low 0.546). Your exact composite could not be "
     "reproduced from the deposited file - your three medians span 0.014 whereas every "
     "recipe tried spans 0.03-0.04 - so please re-derive from the notebook. If the "
     "recomputation stands, this paragraph and the Discussion sentence on algorithmic "
     "sophistication must both be reversed."),

    ("To integrate the multi-dimensional metric signals",
     "MAJOR (R2). 01_raw - the unharmonized control - is classified as a 'low harshness' "
     "harmonization method in Table_S1_methods and contributes 84 of the 344 low-harshness "
     "rows to this comparison, with a composite of 0.445 against an overall median of "
     "0.489. Pooling the no-op control into a harmonization tier biases the low tier "
     "downward. Please state whether 01_raw was excluded from Figure 6A; if it was not, "
     "exclude it and re-quote."),

    ("For each of the 2,234 successful harmonization approaches",
     "MAJOR (R3). Metric counts did not reconcile anywhere in the manuscript and have been "
     "made consistent with the deposited workbook, but please confirm the wording. "
     "Supplementary File 2 sheet 'Metric_polarity' now holds 344 rows: 87 scoring (51 with "
     "polarity +1, 36 with -1) and 257 non-scoring. The manuscript previously said 229 "
     "here and in two other places, 87 + 247 = 334 in Methods, and 229 in the Supplementary "
     "File 2 description - three mutually incompatible totals. Note that the 344 rows "
     "include the 111 group L/M/N rows, 10 metadata rows and 18 unharmonized-baseline "
     "delta rows added after this text was written, and the last two families are computed "
     "in the analysis layer rather than per approach. If 'computed per approach' is meant "
     "strictly, the correct number may be lower than 344 - please give the figure your "
     "pipeline actually emits. Supplementary File 3 itself carries 87 scoring metrics plus "
     "pct_samples_allNA (93 columns, 2,407 rows), which matches the Supplementary File 3 "
     "description and contradicted the '229 metrics (Supplementary File 3)' claim here."),

    ("Based on the clustermap visual inspection combined with quantitative",
     "MAJOR (R4). Composite scores quoted for this group could not be reproduced. You "
     "report the clustermap-best approaches at '0.559 and higher (median 0.603, MAD "
     "0.023)'; recomputation gives min 0.572, median 0.639, MAD 0.034 over all 30 rows and "
     "min 0.572, median 0.637 with post-removal = 0. All 15 Table 3 approach names resolve "
     "in Supplementary File 3, so the mismatch is in the score construction, not the "
     "approach set. Related: the text calls 22_tmm and 23_vst the two best methods after "
     "this group at 0.589 and 0.583; recomputation gives 23_vst = 0.584 (matches) but "
     "22_tmm = 0.625, and places 16_fsqn_r (0.603) and 33_amdbnorm (0.590) between them. "
     "Please re-derive all four numbers."),

    ("Using the 87 polarity-defined metrics and 2,234 qualifying harmonization approaches",
     "VERIFIED. The following all reproduce exactly from Supplementary File 3 and need no "
     "change: the analysis-set filter (pct_samples_allNA < 5 gives exactly 2,234 of 2,407 "
     "rows and drops exactly 34_arsyn and 38_harman, leaving 31 methods); the four R2 "
     "effect sizes and their confidence intervals (method 0.3629 [31.5, 41.1], strategy "
     "0.2564 [0.208, 0.305], imputation 0.0155 [0.009, 0.022], post-removal 0.0020 [0.001, "
     "0.003]); the 1,354 of 2,234 approaches (60.6%) with all 87 metrics defined; the "
     "biology counts 4,466 / 1,697 / 889 / 88 / 34 summing to 7,174; and the design-balance "
     "statement that six methods were not run on all 14 strategies (22_tmm, 23_vst, 27_dwd, "
     "29_combat_ref, 33_amdbnorm, 36_explobatch)."),

    ("The metric cross-correlation structure",
     "MINOR (R5). The citation here is attached to a median Spearman correlation and MAD "
     "that are your own computed results, which reads as though the values were taken from "
     "the cited work. Move the citation to the end of the sentence, or drop it."),

    ("We assembled a comprehensive set of publicly available cohorts",
     "MAJOR (R6) - FIGURE AND SUBMISSION COMPLIANCE, not fixable from this document. "
     "Measured on current_figures_tables_for_article_260802 and supplementary_260824: "
     "(a) every figure exceeds the NAR maximum print box of 17.35 x 23.35 cm and needs "
     "scaling to 0.57-0.65, and after that scaling 37.5% of the text in Figure 1 and 35.8% "
     "in Figure 2 falls below 5 pt (medians 5.7 and 6.1 pt); (b) all nine figures checked "
     "use Type 3 fonts with zero embedded font files, and six of them - Figures 3, 4, 5, "
     "the Graphical Abstract and Supplementary Figures 18 and 19 - return no extractable "
     "text at all, so screen readers cannot reach the labels and the supplied alt text is "
     "the only accessible description; (c) all are RGB, none CMYK; (d) Supplementary "
     "Figures 18 and 19 sit in a different folder from Figures 1-17, use an 'S'-prefixed "
     "filename convention the others do not, and are absent from the combined "
     "'Supplementary Figures S1-S17.pdf' bundle, so the deposited bundle does not contain "
     "the 19 supplementary figures the text cites; (e) 13 'Extended Figure' PDFs remain in "
     "the 260802 folder and are cited nowhere in this manuscript - confirm they are not "
     "part of the submission."),

    ("This work was supported by",
     "MANDATORY BEFORE SUBMISSION. Three placeholders remain in this statement: the full "
     "official funder name, the grant number (currently 'XXXX'), and the open-access charge "
     "funder and grant number. NAR will not process the submission with these unresolved. "
     "The Zenodo DOIs in the Data Availability statement are known to be pending and were "
     "left alone at your instruction; the instruction text '(add link!)' that sat beside "
     "them in the Discussion has been removed so it cannot reach the journal."),

    ("The data supporting this article are available in the article",
     "MAJOR (R7). GitHub is currently the primary archive for the code, the pipeline and "
     "the intermediate matrices. NAR requires a persistent identifier; the sentence two "
     "paragraphs down asserts Zenodo archival but carries no DOI. Per your instruction the "
     "missing Zenodo links were not treated as a defect, but the two statements should be "
     "merged once the DOIs exist so that the article does not simultaneously claim GitHub "
     "as the deposit and Zenodo as the archive. MIAME / MINSEQE compliance is also not "
     "stated anywhere in the manuscript."),

    ("We thank Alisa Sadekova for normal B cells dataset provision",
     "LEFT TO THE AUTHOR (R8). Two judgement calls, deliberately not edited. (1) The "
     "sentence thanking your family is unusual for NAR and most referees would ask for its "
     "removal; it is your call. (2) The final sentence duplicates the AI usage section in "
     "Materials and methods - consider deleting it here and keeping the fuller Methods "
     "statement, which already names the models and the plan-then-act protocol."),
]


# --------------------------------------------------------------------------- #
# Paragraph deletions (whole tracked deletion).                                #
# --------------------------------------------------------------------------- #
DELETE_ANCHORS = [
    "[NAR EDITOR NOTE] NAR limit: 200.",   # P7: editor note must not ship
]


# --------------------------------------------------------------------------- #
def visible(p) -> str:
    """Visible text = original + insertions, deletions excluded."""
    return "".join(t.text or "" for t in p.findall(".//" + W_T))


def is_note(p) -> bool:
    v = visible(p)
    return any(m in v for m in NOTE_MARKERS)


def body_paragraphs(body):
    """Every w:p in document order, table cells inlined at their true position."""
    out = []
    for el in body:
        if el.tag == qn("w:p"):
            out.append(el)
        elif el.tag == qn("w:tbl"):
            out.extend(el.findall(".//" + qn("w:p")))
    return out


def find_p(body, anchor, skip_notes=True):
    """Resolve an anchor to exactly one paragraph element, else raise.

    `skip_notes=False` is needed for the one paragraph we delete, which is
    itself an editor note.
    """
    hits = [p for p in body_paragraphs(body)
            if anchor in visible(p) and (not skip_notes or not is_note(p))]
    if len(hits) != 1:
        raise AssertionError(
            f"anchor matched {len(hits)} paragraphs (need exactly 1): {anchor!r}")
    return hits[0]


def top_level_p(body, anchor):
    """Anchor restricted to direct body children (notes must not land in a cell)."""
    hits = [el for el in body
            if el.tag == qn("w:p") and anchor in visible(el) and not is_note(el)]
    if len(hits) != 1:
        raise AssertionError(
            f"top-level anchor matched {len(hits)} paragraphs: {anchor!r}")
    return hits[0]


def reserve_revision_ids(doc):
    """Restart the id counter above any id already in the file (none here, but
    this keeps the script safe to re-run on its own output)."""
    ids = [int(v) for v in
           re.findall(r'w:id="(\d+)"',
                      doc.element.body.xml)] or [0]
    wrt._rid[0] = max(max(ids) + 1, 1000)


def set_a4(doc):
    """word-rewrite: the template is A4; the manuscript was US Letter."""
    changed = []
    for section in doc.sections:
        before = (round(section.page_width.cm, 2), round(section.page_height.cm, 2))
        if abs(section.page_width.cm - 21.0) > 0.2:
            section.page_width = Cm(21.0)
            section.page_height = Cm(29.7)
            changed.append((before, (21.0, 29.7)))
    return changed


def main() -> int:
    doc = docx.Document(str(SRC))
    body = doc.element.body
    reserve_revision_ids(doc)

    # --- 1. resolve EVERY anchor before mutating anything -------------------
    edit_targets = [(find_p(body, a), a, reps) for a, reps in EDITS]
    del_targets = [(find_p(body, a, skip_notes=False), a) for a in DELETE_ANCHORS]

    # --- 2. apply text edits ------------------------------------------------
    failures = []
    applied = 0
    for p, anchor, reps in edit_targets:
        for old, status in safe_tracked_replace(p, reps):
            if status == "ok":
                applied += 1
            else:
                failures.append((anchor, old, status))
            print(f"  [{status:9s}] {old[:68]}")

    # --- 3. British -> US spelling sweep (document dominant style is US) ----
    brit = [(r"(?<![A-Za-z])modelling(?![A-Za-z])", "modeling"),
            (r"(?<![A-Za-z])maximising(?![A-Za-z])", "maximizing"),
            (r"(?<![A-Za-z])artefact(?![A-Za-z])", "artifact"),
            (r"(?<![A-Za-z])artefacts(?![A-Za-z])", "artifacts"),
            (r"(?<![A-Za-z])labelled(?![A-Za-z])", "labeled")]
    sweep = 0
    for p in body_paragraphs(body):
        if is_note(p):
            continue
        for pat, repl in brit:
            while True:
                direct = "".join(
                    "".join(t.text or "" for t in r.findall(W_T))
                    for r in p.findall(qn("w:r")))
                m = re.search(pat, direct)
                if not m:
                    break
                res = safe_tracked_replace(p, [(m.group(0), repl)])
                if res[0][1] != "ok":
                    failures.append(("<spelling sweep>", m.group(0), res[0][1]))
                    break
                sweep += 1
                print(f"  [spelling ] {m.group(0)} -> {repl}")

    # --- 4. tracked paragraph deletions ------------------------------------
    for p, anchor in del_targets:
        delete_paragraph(p)
        print(f"  [deleted  ] {anchor[:68]}")

    # --- 5. notes last, grouped so multiple notes keep their order ---------
    n_notes = 0
    for anchor, group in itertools.groupby(NOTES, key=lambda x: x[0]):
        ref = top_level_p(body, anchor)
        els = [note_paragraph("[REVIEWER NOTE] " + txt, label="")
               for _, txt in group]
        insert_after(ref, els)
        n_notes += len(els)

    # --- 6. NAR page setup --------------------------------------------------
    page = set_a4(doc)

    doc.save(str(DST))

    print("\n" + "=" * 66)
    print(f"  text replacements applied : {applied}")
    print(f"  spelling sweep            : {sweep}")
    print(f"  paragraphs deleted        : {len(del_targets)}")
    print(f"  reviewer notes inserted   : {n_notes}")
    print(f"  page size changed         : {page or 'no change'}")
    print(f"  failures                  : {len(failures)}")
    for f in failures:
        print("    FAILED", f)
    print(f"  wrote {DST}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
