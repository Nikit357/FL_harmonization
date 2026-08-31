#!/usr/bin/env python
"""Second-iteration edits to `FL_harmonization_article_NAR_260802.docx`.

What this pass does
-------------------
1. **Moves Tables 3 and 4 out of the article** into Supplementary File 2 as the sheets
   `Table_S1_methods` and `Table_S2_metrics` (built by `build_supp_file2_260802.py`, which
   also swaps each numeric citation for the full bibliographic reference). Both tables and
   their captions are removed here as tracked deletions.
2. **Renumbers what is left.** Tables 1 and 2 keep their numbers; the former Table 5 becomes
   **Table 3**, so the article again runs 1, 2, 3 in order of first citation. Every in-text
   reference is repointed: former Table 3 -> Supplementary Table S1, former Table 4 ->
   Supplementary Table S2.
3. **Reverts a defect introduced by the previous pass.** The 2026-08-02 figure sweep searched
   for the bare string "Figure 9" and therefore also rewrote it inside "Supplementary
   Figure 9", producing three wrong references to "Supplementary Figure 6". Those three are
   restored; the genuine main-article Figure 9 -> Figure 6 edits in the same paragraphs are
   left alone. See `revert_supplementary_figure_nine`.
4. **Final language pass**: grammar, punctuation, number formatting and two meaning errors.

Editing a document that already carries tracked changes
-------------------------------------------------------
The input is the previous pass's output, so much of the target text sits inside an
unaccepted `w:ins`. `safe_tracked_replace` deliberately cannot see those runs — they are not
direct children of the paragraph — so it reports `not-found` for them. The work is therefore
split three ways:

* `safe_tracked_replace` for plain direct-child runs (a real del/ins pair);
* `retype_in_own_ins` for text inside **our own** earlier `w:ins`, retyped in place after
  checking `w:author`. That is what Word does when you edit your own not-yet-accepted
  insertion, and reject-all still restores the original because the whole insertion
  disappears. Never retype inside another author's revision;
* `drop_own_insertion` for whole paragraphs we inserted last pass and now withdraw — removing
  the element is exactly equivalent to rejecting our own insertion.

Output: FL_harmonization_article_NAR_260802_2nd_iteration.docx
"""
from __future__ import annotations

import os
import sys

import docx
from docx.oxml.ns import qn

sys.path.insert(0, os.path.expanduser("~/FL_harmonization/.claude/skills"))
from nar_review_tools import safe_tracked_replace  # noqa: E402
import word_rewrite_trackchanges as wrt  # noqa: E402
from word_rewrite_trackchanges import (  # noqa: E402
    delete_paragraph,
    nid,
    set_revision_identity,
)


def reserve_revision_ids(body, module=wrt):
    """Start this pass's revision ids above every id already in the document.

    The input already carries the previous pass's revisions, and `nid()` restarts from a
    fixed base each run, so without this every new `w:ins`/`w:del` collides with an existing
    id and Word's revision pane breaks.
    """
    used = [
        int(el.get(qn("w:id")))
        for tag in ("ins", "del")
        for el in body.iter(f"{W}{tag}")
        if (el.get(qn("w:id")) or "").isdigit()
    ]
    module._rid[0] = max(used or [0]) + 1000

SRC = "FL_manuscript_versions/FL_harmonization_article_NAR_260802.docx"
DST = "FL_manuscript_versions/FL_harmonization_article_NAR_260802_2nd_iteration.docx"

PRIOR_AUTHOR = "Claude (NAR referee report 2026-08-02)"
AUTHOR = "Claude (NAR review, 2nd iteration 2026-08-02)"
DATE = "2026-08-02T12:00:00Z"

set_revision_identity(AUTHOR, DATE)

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

TABLE3_INDEX = 2  # harmonization methods -> Supplementary Table S1
TABLE4_INDEX = 3  # metric groups        -> Supplementary Table S2


# ── text views ────────────────────────────────────────────────────────────────

def accepted(el) -> str:
    """Text as Word shows it with all changes accepted: keep w:ins, drop w:del."""
    parts = []
    for t in el.iter(f"{W}t"):
        anc = t.getparent()
        while anc is not None:
            if anc.tag == f"{W}del":
                break
            anc = anc.getparent()
        else:
            parts.append(t.text or "")
    return "".join(parts)


def find_p(body, needle, nth=0):
    hits = [el for el in body.iter(f"{W}p") if needle in accepted(el)]
    if not hits:
        raise SystemExit(f"anchor matched no paragraph: {needle!r}")
    if nth >= len(hits):
        raise SystemExit(f"anchor matched {len(hits)} paragraphs, wanted #{nth}: {needle!r}")
    return hits[nth]


# ── editing our own unaccepted insertions ─────────────────────────────────────

def retype_in_own_ins(p, replacements, author=PRIOR_AUTHOR):
    """Replace text inside `w:ins` elements written by `author`, in place.

    Word represents an edit to your own not-yet-accepted insertion as a straight retype of
    the inserted text, with no nested revision — which is what this does. Reject-all still
    restores the original wording because the whole insertion disappears.

    Returns one (old, status) pair per replacement, mirroring `safe_tracked_replace`.
    """
    out = []
    for old, new in replacements:
        done = False
        for ins in p.findall(f"{W}ins"):
            if ins.get(qn("w:author")) != author:
                continue
            runs = ins.findall(f"{W}r")
            texts = [t for r in runs for t in r.findall(f"{W}t")]
            whole = "".join(t.text or "" for t in texts)
            if old not in whole:
                continue
            replaced = whole.replace(old, new, 1)
            # Collapse the insertion onto its first w:t; the run properties of that run are
            # kept, so formatting of the insertion is preserved.
            texts[0].text = replaced
            texts[0].set(qn("xml:space"), "preserve")
            for t in texts[1:]:
                t.text = ""
            out.append((old, "ok"))
            done = True
            break
        if not done:
            out.append((old, "not-found"))
    return out


def drop_own_insertion(p, author=PRIOR_AUTHOR):
    """Withdraw a paragraph that we inserted in an earlier, unaccepted pass.

    Equivalent to rejecting our own insertion: the paragraph never existed in the original,
    so removing the element leaves reject-all unchanged.
    """
    children = [c for c in p if c.tag not in (f"{W}pPr",)]
    if not children or any(c.tag != f"{W}ins" for c in children):
        raise SystemExit(f"paragraph is not a pure insertion: {accepted(p)[:60]!r}")
    if any(c.get(qn("w:author")) != author for c in children):
        raise SystemExit(f"paragraph was inserted by another author: {accepted(p)[:60]!r}")
    p.getparent().remove(p)


# ── tracked deletion of a whole table ─────────────────────────────────────────

def delete_table(tbl, author=PRIOR_AUTHOR):
    """Mark an entire table as a tracked deletion.

    Each `w:tr` gets `w:trPr/w:del`, which is how Word records a deleted row, and every
    surviving run is wrapped in `w:del` with `w:t` converted to `w:delText`. Columns that we
    inserted in the previous, still-unaccepted pass are withdrawn outright instead of being
    marked deleted — an insert-then-delete of our own text carries no information, and
    reject-all is identical either way.
    """
    n_rows = n_runs = n_withdrawn = 0
    for tr in tbl.findall(f"{W}tr"):
        tr_pr = tr.find(f"{W}trPr")
        if tr_pr is None:
            tr_pr = tr.makeelement(f"{W}trPr", {})
            tr.insert(0, tr_pr)
        d = tr_pr.makeelement(f"{W}del", {})
        d.set(qn("w:id"), str(nid()))
        d.set(qn("w:author"), AUTHOR)
        d.set(qn("w:date"), DATE)
        tr_pr.append(d)
        n_rows += 1

        for ins in list(tr.iter(f"{W}ins")):
            if ins.get(qn("w:author")) == author:
                ins.getparent().remove(ins)
                n_withdrawn += 1

        for p in tr.iter(f"{W}p"):
            for r in list(p.findall(f"{W}r")):
                texts = r.findall(f"{W}t")
                if not texts:
                    continue
                idx = list(p).index(r)
                wrapper = p.makeelement(f"{W}del", {})
                wrapper.set(qn("w:id"), str(nid()))
                wrapper.set(qn("w:author"), AUTHOR)
                wrapper.set(qn("w:date"), DATE)
                p.remove(r)
                for t in texts:
                    dt = r.makeelement(f"{W}delText", {})
                    dt.text = t.text
                    dt.set(qn("xml:space"), "preserve")
                    r.replace(t, dt)
                wrapper.append(r)
                p.insert(idx, wrapper)
                n_runs += 1
    return n_rows, n_runs, n_withdrawn


# ── revert the previous pass's "Supplementary Figure 9" defect ────────────────

def revert_supplementary_figure_nine(body, author=PRIOR_AUTHOR):
    """Undo the three "Supplementary Figure 9" -> "Supplementary Figure 6" rewrites.

    The previous pass renumbered the main article's Figure 9 to Figure 6 with a bare search
    for "Figure 9", which also matched inside "Supplementary Figure 9". Only those matches
    are reverted here: a `w:del`("Figure 9") + `w:ins`("Figure 6") pair whose preceding text
    ends with "Supplementary ". The genuine main-article rewrites, which have no such prefix,
    are left in place.
    """
    reverted = 0
    for p in body.iter(f"{W}p"):
        children = list(p)
        for i, el in enumerate(children):
            if el.tag != f"{W}del" or el.get(qn("w:author")) != author:
                continue
            del_text = "".join(t.text or "" for t in el.iter(f"{W}delText"))
            if del_text != "Figure 9":
                continue
            nxt = children[i + 1] if i + 1 < len(children) else None
            if nxt is None or nxt.tag != f"{W}ins":
                continue
            if "".join(t.text or "" for t in nxt.iter(f"{W}t")) != "Figure 6":
                continue
            before = "".join(
                t.text or ""
                for c in children[:i] for t in c.iter(f"{W}t")
            )
            if not before.endswith("Supplementary "):
                continue  # a genuine main-article Figure 9 ->6 rewrite; leave it
            # Withdraw the insertion and unwrap the deletion back into a plain run.
            p.remove(nxt)
            run = el.find(f"{W}r")
            for dt in run.findall(f"{W}delText"):
                t = run.makeelement(f"{W}t", {})
                t.text = dt.text
                t.set(qn("xml:space"), "preserve")
                run.replace(dt, t)
            idx = list(p).index(el)
            p.remove(el)
            p.insert(idx, run)
            reverted += 1
            break
    return reverted


# ── edits on plain, direct-child runs ─────────────────────────────────────────
PLAIN_EDITS = [
    # -- Table 3 -> Supplementary Table S1 ------------------------------------
    ("we identified 39 harmonization methods potentially applicable",
     [("current GC lymphoma dataset (Table 3)",
       "current GC lymphoma dataset (Supplementary Table S1 in Supplementary File 2)")]),
    ("Six methods failed implementation",
     [("documented with reasons in Table 3",
       "documented with reasons in Supplementary Table S1")]),
    ("Starting from the full multi-platform dataset",
     [("one of 33 harmonization methods (Table 3)",
       "one of 33 harmonization methods (Supplementary Table S1)")]),

    # -- Table 4 -> Supplementary Table S2 ------------------------------------
    ("we assembled a set of 87 polarity-defined scoring metrics",
     [("not included in the composite scoring (Table 4)",
       "not included in the composite scoring (Supplementary Table S2 in Supplementary "
       "File 2)"),
      ("batch correction (Table 4), and their source code",
       "batch correction (Supplementary Table S2), and their source code")]),
    ("For each of the 2,234 successful harmonization approaches, we computed",
     [("(Supplementary File 3; Table 4 in Methods)",
       "(Supplementary File 3; Supplementary Table S2)")]),

    # -- former Table 5 becomes Table 3 ---------------------------------------
    ("Table 5. 15 best harmonization approaches",
     [("Table 5. 15 best harmonization approaches",
       "Table 3. The 15 best harmonization approaches")]),

    # -- number formatting, spelling and grammar ------------------------------
    ("We then assessed the contribution of each metric type",
     [("again for the successful 2234 approaches",
       "again for the 2,234 successful approaches")]),
    ("The two top methods after the clustermap best group",
     [("The third method was 33_amdbnorm, run only for 14 of 84 runs, which also impacted "
       "its compatibility with the regular ones.",
       "The third method was 33_amdbnorm, which completed only 14 of its 84 possible runs, "
       "again limiting its comparability with the rest."),
      ("and then rising to 0.106 in 10_mnn, accompanied with the decrease of global and "
       "distributional performance",
       "and then rising to 0.106 in 10_mnn, accompanied by a decrease in global and "
       "distributional performance")]),
    ("We did not include the trivial combination of single platform",
     [("(such as FFPE only RNA-seq only, FF only Affymetrix only, etc)",
       "(such as FFPE-only RNA-seq, or FF-only Affymetrix)")]),
    ("A common finding across the RNA-seq only and FFPE only scenarios",
     [("when combined with SVA harmonization (Figures 4, 5)",
       "when combined with SVA harmonization (Figures 4 and 5)")]),
    ("Current benchmarking datasets (TCGA, GTEx, SEQC, MAQC etc)",
     [("such as homogenous RNA-seq protocols", "such as homogeneous RNA-seq protocols"),
      ("But the vast majority of clinically actionable biomarker research",
       "However, the vast majority of clinically actionable biomarker research"),
      ]),
    ("We note important technical limitations of the current pipeline",
     [("rapidly expanding including the recent diffusion model-based ones",
       "expanding rapidly, including recent diffusion-model-based methods")]),
    ("The ComboBatch benchmark was designed as an exhaustive computational search",
     [("of the three top-performing methods (MNN, SVA, FSQN R), the best ones MNN and SVA "
       "were identified",
       "of the three top-performing methods (MNN, SVA and FSQN R), the two best — MNN and "
       "SVA — were identified")]),
    ("Among the 33 methods benchmarked, MNN, SVA, and FSQN R",
     [("with AMDBNorm and FSMVN having more limited application scale",
       "with AMDBNorm and FSMVN having a narrower scope of application")]),
    # "locally separate batches" states the opposite of the finding: these methods failed to
    # MIX batches locally, which is why they are criticised in this sentence.
    ("Methods that dominated earlier harmonization benchmarks",
     [("but failed to preserve local biology structure and locally separate batches",
       "but failed both to preserve local biology structure and to mix batches locally")]),
    ("In the present study we assembled a GC B cell lymphoma cross-platform cohort",
     [("cross-platform cohort of 7174 bulk transcriptomic profiles",
       "cross-platform cohort of 7,174 bulk transcriptomic profiles")]),
    ("We aimed to find the best harmonization approach for the multiplatform",
     [("bulk transcriptomic dataset of 7174 samples",
       "bulk transcriptomic dataset of 7,174 samples")]),
    ("Figure 6. Composite performance score",
     [("and post-removal.  (C) Radar plot", "and post-removal. (C) Radar plot")]),

    # -- supplementary figure legends: thousands separator --------------------
    ("Clustermap of the 87 scoring metrics Spearman cross-correlations",
     [("in the space of the successful 2234 harmonization approaches",
       "in the space of the 2,234 successful harmonization approaches")]),
    ("3 X 3 square grid of scatterplots showing distribution of the 87 scoring metrics",
     [("calculated based on the 2234 harmonization approaches space",
       "calculated on the space of the 2,234 harmonization approaches")]),
    ("Clustermap showing Spearman cross-correlations of the successful",
     [("of the successful 2234 harmonization approaches",
       "of the 2,234 successful harmonization approaches")]),
    ("3 X 5 rectangular grid of scatterplots showing distribution of the 2234",
     [("distribution of the 2234 successful approaches",
       "distribution of the 2,234 successful approaches")]),
]

# ── edits inside our own earlier (unaccepted) insertions ──────────────────────
IN_INS_EDITS = [
    ("The parameters actually passed to every method",
     [("Except where Table 3 states otherwise",
       "Except where Supplementary Table S1 states otherwise"),
      ("The parameters actually passed to every method are listed in Table 3.",
       "The parameters actually passed to every method are listed in Supplementary "
       "Table S1.")]),
    ("The tier assigned to each method and the reason for it",
     [("The tier assigned to each method and the reason for it are given in Table 3.",
       "The tier assigned to each method and the reason for it are given in Supplementary "
       "Table S1."),
      ("or applies local neighbour-dependent offsets",
       "or applies local neighbor-dependent offsets")]),
    ("15 individual approaches",
     [("(15 individual approaches, Table 5)", "(15 individual approaches, Table 3)")]),
    ("We also acknowledge additional mathematical limitations",
     # The insertion ends mid-sentence, so the search string must stop at its boundary.
     [("First, albeit the composite score", "First, although the composite score")]),
    ("t-SNE embeddings used perplexity",
     [("UMAP embeddings used n_neighbors", "UMAP embeddings used n_neighbors"),
      ("t-SNE embeddings used perplexity", "tSNE embeddings used perplexity")]),
    # Supplementary File 2 now carries the two moved tables as well.
    ("Excel workbook with two sheets",
     [("Supplementary File 2. Excel workbook with two sheets: ‘Genes_per_sample’, the number "
       "of genes with defined gene expression for each of the 7,174 samples in the initial "
       "dataset prior to imputation; and ‘Metric_polarity’, the polarity coefficients of the "
       "229 harmonization quality metrics used in this study.",
       "Supplementary File 2. Excel workbook with four sheets: ‘Genes_per_sample’, the "
       "number of genes with defined gene expression for each of the 7,174 samples in the "
       "initial dataset prior to imputation; ‘Metric_polarity’, the polarity coefficients of "
       "the 229 harmonization quality metrics used in this study; ‘Table_S1_methods’ "
       "(Supplementary Table S1), the 39 harmonization methods reviewed for implementation, "
       "with the parameters used, the harshness tier and its justification, and the full "
       "bibliographic reference for each method; and ‘Table_S2_metrics’ (Supplementary "
       "Table S2), the definitions, types, computational groups and sources of the "
       "harmonization quality metric families.")]),
]

# Paragraphs removed outright: two reviewer notes whose requests are now fully carried out,
# and the two RESOLVED notes we added in reply to them.
NOTES_TO_DROP_PLAIN = [
    "does not determine the behaviour of SVA",          # model-specification note
    "tests a hypothesis about harshness",               # harshness-auditability note
]
NOTES_TO_DROP_OWN_INS = [
    "Table 3 now carries a ‘Parameters used’ column",
    "The harshness criteria are now stated explicitly",
]

# Captions of the two tables being moved out.
CAPTIONS_TO_DELETE = [
    "Table 3. Harmonization methods utilized in this study",
    "Table 4. Metric groups for harmonization quality control",
]


def main():
    doc = docx.Document(SRC)
    body = doc.element.body
    reserve_revision_ids(body)
    report = {"ok": 0, "not-found": 0, "unsafe": 0}

    def apply(p, pairs, tag, fn=safe_tracked_replace):
        for old, status in fn(p, pairs):
            report[status] = report.get(status, 0) + 1
            if status != "ok":
                print(f"  [{status}] {tag}: {old[:90]!r}")

    # 1 ── revert the previous pass's Supplementary Figure 9 defect, before anything else
    #      moves text around.
    n_reverted = revert_supplementary_figure_nine(body)
    print(f"reverted 'Supplementary Figure 6' -> 'Supplementary Figure 9': {n_reverted}")

    # 2 ── text edits. Resolve every anchor to an element before mutating anything: after an
    #      edit lands the original wording lives in w:delText, which a text search misses.
    plain = [(find_p(body, a), pairs, a) for a, pairs in PLAIN_EDITS]
    in_ins = [(find_p(body, a), pairs, a) for a, pairs in IN_INS_EDITS]
    for p, pairs, anchor in plain:
        apply(p, pairs, anchor[:45])
    for p, pairs, anchor in in_ins:
        apply(p, pairs, anchor[:45], fn=retype_in_own_ins)

    # 3 ── remove the two tables, their captions and the four spent reviewer notes.
    tables = [ch for ch in body if ch.tag == f"{W}tbl"]
    for idx, label in ((TABLE3_INDEX, "Table 3"), (TABLE4_INDEX, "Table 4")):
        rows, runs, withdrawn = delete_table(tables[idx])
        print(f"deleted {label}: {rows} rows, {runs} runs marked deleted, "
              f"{withdrawn} own insertions withdrawn")

    for needle in CAPTIONS_TO_DELETE + NOTES_TO_DROP_PLAIN:
        delete_paragraph(find_p(body, needle))
    for needle in NOTES_TO_DROP_OWN_INS:
        drop_own_insertion(find_p(body, needle))
    print(f"deleted {len(CAPTIONS_TO_DELETE)} captions, "
          f"{len(NOTES_TO_DROP_PLAIN)} reviewer notes, "
          f"{len(NOTES_TO_DROP_OWN_INS)} own resolved notes")

    print(f"\nok {report['ok']} | not-found {report['not-found']} | unsafe {report['unsafe']}")
    doc.save(DST)
    print(f"wrote {DST}")


if __name__ == "__main__":
    main()
