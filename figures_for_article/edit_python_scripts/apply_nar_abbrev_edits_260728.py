#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Rename PCR -> PCReg and define abbreviations at first use, as Word tracked changes.

Reads  FL_harmonization_article_NAR_260727_partially_edited.docx  (Daniil's partly-revised copy)
Writes FL_harmonization_article_NAR_260728.docx

Scope (Daniil's instruction of 2026-07-28, answering the [REVIEWER NOTE] on abbreviations):

1.  Every occurrence of the metric name "PCR" (principal component regression) becomes
    "PCReg", so it can no longer be read as polymerase chain reaction.
2.  Abbreviations flagged as undefined are expanded at their first occurrence:
    AUC, tSNE, UMAP, PC, PCA, GEO, PBMCs, AWS, cLISI, iLISI, TPM, DSC, and FSQN / QN
    inside Table 1.  KNN was already defined at first use and is left alone.

Design constraints (unchanged from apply_nar_review_edits_260727.py):

*   Every change is a real OOXML revision, so *Accept All* yields the corrected manuscript
    and *Reject All* restores the input file byte-for-byte in text.
*   Edits are as short as possible: only the words that change are wrapped in del/ins.
*   **References are never touched.**  Citations are 118 `<w:sdt>` elements, so
    `word_rewrite_trackchanges.tracked_replace` must NOT be used; `safe_tracked_replace`
    edits only runs that are direct children of the paragraph.
*   The input file already carries 327 revisions from the 2026-07-27 pass.  Three "PCR"
    occurrences sit *inside* those unaccepted insertions; they are corrected in place
    (Word behaves the same way when you retype inside your own insertion) and reported
    separately at the end.
*   Reviewer-note paragraphs are skipped: they quote the old wording on purpose.

Run:  source ~/venvs/collagen_3_11/bin/activate && python apply_nar_abbrev_edits_260728.py
"""
import re
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
from nar_review_tools import safe_tracked_replace  # noqa: E402

SRC = MANUSCRIPTS / "FL_harmonization_article_NAR_260727_partially_edited.docx"
DST = MANUSCRIPTS / "FL_harmonization_article_NAR_260728.docx"

AUTHOR = "Claude (NAR referee, abbreviations 2026-07-28)"
set_revision_identity(AUTHOR, "2026-07-28T00:00:00Z")

# author of the still-unaccepted insertions from the previous pass, safe to retype inside
PREV_AUTHOR = "Claude (NAR referee report 2026-07-27)"

W_P, W_R, W_T, W_INS = qn("w:p"), qn("w:r"), qn("w:t"), qn("w:ins")
PCR_RE = re.compile(r"(?<![A-Za-z0-9])PCR(?![A-Za-z0-9])")
NOTE_PREFIXES = ("[REVIEWER NOTE]", "[NAR EDITOR NOTE]", "[REVIEWER NOTE —")


# --------------------------------------------------------------------------- load + index
doc = docx.Document(str(SRC))
body = doc.element.body


def text_of(el):
    """Visible text: original runs plus insertions, deletions excluded (w:delText)."""
    return "".join(t.text or "" for t in el.findall(".//" + W_T))


def plain_text_of(p):
    """Text of runs that are direct children of the paragraph — what is safely editable."""
    return "".join(
        "".join(t.text or "" for t in r.findall(W_T)) for r in p if r.tag == W_R
    )


def is_note(p):
    return text_of(p).lstrip().startswith(NOTE_PREFIXES)


ALL_P = list(body.iter(W_P))                       # includes paragraphs inside tables
BODY_P = [el for el in body if el.tag == W_P]      # top-level only (safe note anchors)


def find_p(anchor, pool=None, first=False):
    """The paragraph whose visible text contains `anchor`; error unless exactly one match.

    With first=True the earliest match in document order is returned instead — used for
    the three identical Table 1 rows that differ only in the strategy letter.
    """
    hits = [p for p in (pool if pool is not None else ALL_P) if anchor in text_of(p)]
    if not hits or (len(hits) > 1 and not first):
        raise LookupError(f"{len(hits)} matches for anchor {anchor!r}")
    return hits[0]


# ====================================================== ABBREVIATIONS DEFINED AT FIRST USE
# (anchor, [(old, new), ...], first_match_only)
# `old` is kept to the shortest unambiguous stretch of plain prose so that the tracked
# change covers only the words that actually change, and never a superscript or a citation.
EDITS = [
    # --- Introduction: AUC ------------------------------------------------------------
    ("Batch-confounded AI models can undergo performance collapse", [
        ("an AUC decrease", "an area under the curve (AUC) decrease"),
    ], False),

    # --- Introduction: tSNE and UMAP -------------------------------------------------
    ("These methods were both the best performing ones by metrics", [
        ("in tSNE and UMAP space",
         "in t-distributed stochastic neighbor embedding (tSNE) and uniform manifold "
         "approximation and projection (UMAP) space"),
    ], False),

    # --- Table 1: PC, FSQN, QN -------------------------------------------------------
    ("Outlier batches by an initial FSQN manual screening removed", [
        ("initial FSQN manual",
         "initial feature-specific quantile normalization (FSQN) manual"),
    ], False),
    ("More outlier batches by an additional QN manual screening", [
        ("additional QN manual", "additional quantile normalization (QN) manual"),
    ], False),
    ("with the highest PC distance from the global centroid", [
        ("highest PC distance", "highest principal component (PC) distance"),
    ], True),   # three identical rows (strategies A, E1, E2) — define in the first

    # --- Methods, batch annotation: GEO and PBMCs ------------------------------------
    ("We devised a systematic batch naming convention", [
        ("is the GEO platform identifier",
         "is the Gene Expression Omnibus (GEO) platform identifier"),
        ("sorted cells, PBMCs",
         "sorted cells, peripheral blood mononuclear cells (PBMCs)"),
    ], False),

    # --- Table 3 (method list): spell out PCA in full, no acronym needed in the cell --
    ("overcorrection-probability constraint", [
        ("PCA-based batch correction",
         "principal component analysis-based batch correction"),
    ], False),

    # --- Methods, post-removal: PCA (first use of the acronym) -----------------------
    ("we calculated Euclidean distance of its centroid", [
        ("in the PCA space", "in the principal component analysis (PCA) space"),
    ], False),

    # --- Figure 7 legend: cLISI and iLISI (first occurrence = panel A) ---------------
    ("Figure 7. Local mixing-based metrics performance", [
        ("cLISI", "cell-type LISI (cLISI)"),
        ("iLISI", "integration LISI (iLISI)"),
    ], False),

    # --- Results, expression ranges: TPM --------------------------------------------
    # target "(TPM)" only: the 2 of log2 is a separate superscript run and must not be
    # pulled into the replacement.
    ("comparable with the standard RNA-seq log", [
        ("(TPM)", "(transcripts per million, TPM)"),
    ], False),

    # --- Results, composite score: DSC (and the PCR rename in the same clause) -------
    ("The two top methods after the clustermap best group", [
        ("of PCR-only or DSC-only rankings",
         "of rankings based on PCReg or the dispersion separability criterion (DSC) alone"),
    ], False),
]

# Text that lives inside an unaccepted insertion from the 2026-07-27 pass cannot carry its own
# del/ins pair, so it is retyped in place — exactly what Word does when you edit your own
# not-yet-accepted insertion. (anchor, [(old, new), ...])
IN_PLACE_EDITS = [
    # Methods, pipeline: AWS — the whole sentence was inserted on 2026-07-27
    ("Outputs of both steps were saved to Amazon Web Services", [
        ("Amazon Web Services S3", "Amazon Web Services (AWS) S3"),
    ]),
]

RESOLUTION_NOTE = (
    "Response to the abbreviation note above, applied 2026-07-28. "
    "PCR has been renamed PCReg throughout the text and in Table 4. Abbreviations are now "
    "expanded at first use: AUC and tSNE/UMAP (Introduction); PC, FSQN and QN (Table 1); "
    "PCA (post-removal subsection, with the Table 3 Harman entry spelled out in full); "
    "GEO and PBMCs (batch annotation subsection); AWS (pipeline subsection); cLISI and "
    "iLISI (Figure 7 legend); TPM (expression-range results); DSC (composite-score "
    "results). KNN was already defined at first use ('k-nearest-neighbor (KNN) "
    "imputation') and was left unchanged. TWO ITEMS STILL NEED YOUR ACTION: (1) Figure 6 "
    "and Extended Figures 2, 3, 6 and 8 still print 'PCR' / 'pcr' in axis labels and "
    "panel titles, and every principal-component-regression column of Supplementary File 3 "
    "is named 'pcr_*' — regenerate them as PCReg so the figures match the text; (2) delete "
    "this note and the one above once you are satisfied."
)


# =============================================================================== apply
report_ok, report_fail, report_inplace = [], [], []

# Resolve every anchor to an lxml element reference BEFORE mutating anything: once an edit
# has run, the original wording lives in w:delText, which text_of() no longer sees.
edit_targets = []
for anchor, reps, first in EDITS:
    try:
        edit_targets.append((find_p(anchor, first=first), anchor, reps))
    except LookupError as exc:
        report_fail.append(f"EDIT-ANCHOR  {exc}")

inplace_targets = []
for anchor, reps in IN_PLACE_EDITS:
    try:
        inplace_targets.append((find_p(anchor), anchor, reps))
    except LookupError as exc:
        report_fail.append(f"INPLACE-ANCHOR  {exc}")

try:
    note_anchor_p = find_p("ABBREVIATION — PLEASE RECONSIDER", pool=BODY_P)
except LookupError as exc:
    note_anchor_p = None
    report_fail.append(f"NOTE-ANCHOR  {exc}")

for p, anchor, reps in edit_targets:
    for old, status in safe_tracked_replace(p, reps):
        line = f"{status:9s} {old[:64]!r}   (in {anchor[:40]!r})"
        (report_ok if status == "ok" else report_fail).append(line)

for p, anchor, reps in inplace_targets:
    for old, new in reps:
        done = False
        for ins in p.findall(W_INS):
            if ins.get(qn("w:author")) != PREV_AUTHOR:
                continue
            for t in ins.iter(W_T):
                if t.text and old in t.text:
                    t.text = t.text.replace(old, new, 1)
                    report_inplace.append(f"{old!r} -> {new!r}")
                    done = True
                    break
            if done:
                break
        if not done:
            report_fail.append(f"INPLACE not-found {old!r} (in {anchor[:40]!r})")

# ------------------------------------------------------------------ PCR -> PCReg sweep
pcr_plain = pcr_ins = 0
for p in ALL_P:
    if is_note(p):
        continue

    # (a) plain, never-revised prose: one tracked del+ins per occurrence
    n = len(PCR_RE.findall(plain_text_of(p)))
    for _ in range(n):
        (old, status), = safe_tracked_replace(p, [("PCR", "PCReg")])
        if status == "ok":
            pcr_plain += 1
        else:
            report_fail.append(f"PCR {status:9s} in {text_of(p)[:60]!r}")

    # (b) occurrences inside the previous pass's own unaccepted insertions: retype in place
    for ins in p.findall(W_INS):
        joined = "".join(t.text or "" for t in ins.iter(W_T))
        if not PCR_RE.search(joined):
            continue
        if ins.get(qn("w:author")) != PREV_AUTHOR:
            report_fail.append(f"PCR in w:ins by {ins.get(qn('w:author'))!r} — left alone")
            continue
        hit = 0
        for t in ins.iter(W_T):
            if t.text and PCR_RE.search(t.text):
                hit += len(PCR_RE.findall(t.text))
                t.text = PCR_RE.sub("PCReg", t.text)
        if hit != len(PCR_RE.findall(joined)):
            report_fail.append(f"PCR split across runs inside w:ins: {joined[:60]!r}")
        pcr_ins += hit
        report_inplace.append(joined[:90])

# ------------------------------------------------------------------------ resolution note
if note_anchor_p is not None:
    insert_after(note_anchor_p, [note_paragraph(RESOLUTION_NOTE, label="[REVIEWER NOTE] ")])

doc.save(str(DST))

# =============================================================================== report
print(f"wrote {DST.name}")
print(f"abbreviation edits applied : {len(report_ok)}")
print(f"PCR -> PCReg, tracked      : {pcr_plain}")
print(f"PCR -> PCReg, retyped inside 2026-07-27 insertions : {pcr_ins}")
for line in report_inplace:
    print(f"    ...{line}")
if report_fail:
    print(f"\nPROBLEMS ({len(report_fail)}):")
    for line in report_fail:
        print(f"  {line}")
else:
    print("\nno failed anchors, no unsafe replacements")
