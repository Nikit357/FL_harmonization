#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Reusable Word (.docx) track-changes helpers for the `word_rewrite` skill.

python-docx has no native track-changes support, so these helpers write the OOXML
revision markup (<w:ins>/<w:del>) directly. Import into a rewrite script:

    import sys; sys.path.insert(0, "<dir-of-this-file>")
    from word_rewrite_trackchanges import *
    set_revision_identity("Claude (NAR reformat)", "2026-07-17T00:00:00Z")

All builders return lxml elements; use insert_after / insert_before / delete_paragraph /
tracked_replace to place them. Accept-All in Word yields the edited doc; Reject-All restores
the original. See .claude/skills/word_rewrite.md for the full procedure.
"""
import copy
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# ---------------------------------------------------------------- revision identity
_AUTHOR = ["Claude (reformat)"]
_DATE = ["2026-01-01T00:00:00Z"]
_rid = [1000]

def set_revision_identity(author, date):
    """Set the author name and ISO date shown for every revision in Word."""
    _AUTHOR[0] = author
    _DATE[0] = date

def nid():
    _rid[0] += 1
    return str(_rid[0])

def _rev_attrs(el):
    el.set(qn("w:id"), nid())
    el.set(qn("w:author"), _AUTHOR[0])
    el.set(qn("w:date"), _DATE[0])
    return el

# ---------------------------------------------------------------- generic helpers
def text_of(el):
    """Concatenated visible text (all <w:t>/<w:delText>) beneath an element."""
    return "".join(t.text or "" for t in
                   el.findall(".//" + qn("w:t")) + el.findall(".//" + qn("w:delText")))

def is_p(el):
    return el.tag == qn("w:p")

def style_of(p):
    ppr = p.find(qn("w:pPr"))
    if ppr is None:
        return ""
    ps = ppr.find(qn("w:pStyle"))
    return ps.get(qn("w:val")) if ps is not None else ""

# ---------------------------------------------------------------- run builders
def _make_rpr(bold=False, italic=False, color=None, base=None):
    rpr = copy.deepcopy(base) if base is not None else OxmlElement("w:rPr")
    def drop(tag):
        for e in rpr.findall(qn(tag)):
            rpr.remove(e)
    if bold:
        drop("w:b"); rpr.append(OxmlElement("w:b"))
    if italic:
        drop("w:i"); rpr.append(OxmlElement("w:i"))
    if color:
        drop("w:color")
        c = OxmlElement("w:color"); c.set(qn("w:val"), color); rpr.append(c)
    return rpr

def make_run(text, bold=False, italic=False, color=None, base=None):
    r = OxmlElement("w:r")
    rpr = _make_rpr(bold, italic, color, base)
    if len(rpr):
        r.append(rpr)
    t = OxmlElement("w:t"); t.set(qn("xml:space"), "preserve"); t.text = text
    r.append(t)
    return r

def make_del_run(text, base=None):
    r = OxmlElement("w:r")
    rpr = _make_rpr(base=base)
    if len(rpr):
        r.append(rpr)
    t = OxmlElement("w:delText"); t.set(qn("xml:space"), "preserve"); t.text = text
    r.append(t)
    return r

def wrap_ins(*runs):
    ins = _rev_attrs(OxmlElement("w:ins"))
    for r in runs:
        ins.append(r)
    return ins

def wrap_del(*runs):
    d = _rev_attrs(OxmlElement("w:del"))
    for r in runs:
        d.append(r)
    return d

# ---------------------------------------------------------------- paragraph builders
def _ppr(style=None, mark="ins"):
    ppr = OxmlElement("w:pPr")
    if style:
        ps = OxmlElement("w:pStyle"); ps.set(qn("w:val"), style); ppr.append(ps)
    rpr = OxmlElement("w:rPr")
    if mark == "ins":
        rpr.append(_rev_attrs(OxmlElement("w:ins")))
    elif mark == "del":
        rpr.append(_rev_attrs(OxmlElement("w:del")))
    ppr.append(rpr)
    return ppr

def ins_paragraph(text, style=None, bold=False, italic=False, color=None):
    """A fully tracked-inserted paragraph containing a single run."""
    p = OxmlElement("w:p")
    p.append(_ppr(style, "ins"))
    p.append(wrap_ins(make_run(text, bold=bold, italic=italic, color=color)))
    return p

def ins_paragraph_runs(runs, style=None):
    """A fully tracked-inserted paragraph built from custom runs (see make_run)."""
    p = OxmlElement("w:p")
    p.append(_ppr(style, "ins"))
    p.append(wrap_ins(*runs))
    return p

def note_paragraph(text, label="[EDITOR NOTE] ", color="C00000"):
    """Red italic tracked-inserted editor note paragraph."""
    runs = [make_run(label, bold=True, italic=True, color=color),
            make_run(text, italic=True, color=color)]
    return ins_paragraph_runs(runs)

def heading(text, level=1, style_fmt="Heading%d"):
    """Tracked-inserted heading paragraph using the source's heading style id."""
    return ins_paragraph(text, style=style_fmt % level)

# ---------------------------------------------------------------- delete existing paragraph
def delete_paragraph(p):
    """Convert an existing paragraph into a tracked deletion, in place.

    Wraps run children in <w:del>, converts <w:t>->  <w:delText>, marks the paragraph
    mark deleted. Runs containing images (<w:drawing>) are wrapped intact.
    """
    ppr = p.find(qn("w:pPr"))
    if ppr is None:
        ppr = OxmlElement("w:pPr"); p.insert(0, ppr)
    rpr = ppr.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr"); ppr.append(rpr)
    if rpr.find(qn("w:del")) is None:
        rpr.append(_rev_attrs(OxmlElement("w:del")))
    for child in list(p):
        if child.tag == qn("w:r"):
            for t in child.findall(qn("w:t")):
                t.tag = qn("w:delText")
            d = _rev_attrs(OxmlElement("w:del"))
            p.replace(child, d); d.append(child)
        elif child.tag == qn("w:hyperlink"):
            for t in child.findall(".//" + qn("w:t")):
                t.tag = qn("w:delText")
            for r in child.findall(qn("w:r")):
                d = _rev_attrs(OxmlElement("w:del"))
                child.replace(r, d); d.append(r)

# ---------------------------------------------------------------- tracked replace in paragraph
def tracked_replace(p, replacements):
    """Rebuild paragraph applying (old, new) substring replacements as tracked del/ins.

    new="" means pure deletion. Robust to text split across multiple/nested runs;
    preserves the first run's rPr as base formatting for the rebuilt runs.
    """
    full = text_of(p)
    base = None
    r0 = p.find(".//" + qn("w:r"))
    if r0 is not None:
        rp = r0.find(qn("w:rPr"))
        if rp is not None:
            base = rp
    segs = [("keep", full)]
    for old, new in replacements:
        nsegs = []
        for kind, txt in segs:
            if kind != "keep" or old not in txt:
                nsegs.append((kind, txt)); continue
            before, after = txt.split(old, 1)
            if before:
                nsegs.append(("keep", before))
            nsegs.append(("del", old))
            if new:
                nsegs.append(("ins", new))
            if after:
                nsegs.append(("keep", after))
        segs = nsegs
    ppr = p.find(qn("w:pPr"))
    for child in list(p):
        if child is not ppr:
            p.remove(child)
    for kind, txt in segs:
        if not txt:
            continue
        if kind == "keep":
            p.append(make_run(txt, base=base))
        elif kind == "del":
            p.append(wrap_del(make_del_run(txt, base=base)))
        elif kind == "ins":
            p.append(wrap_ins(make_run(txt, base=base)))

# ---------------------------------------------------------------- placement helpers
def insert_after(ref, new_els):
    cur = ref
    for el in new_els:
        cur.addnext(el); cur = el

def insert_before(ref, new_els):
    for el in new_els:
        ref.addprevious(el)

# ---------------------------------------------------------------- lookup helpers
def find_p(body, pred):
    for el in body:
        if is_p(el) and pred(text_of(el)):
            return el
    return None

def find_all_p(body, pred):
    return [el for el in body if is_p(el) and pred(text_of(el))]

def image_paragraphs(body):
    return [el for el in body if is_p(el) and el.findall(".//" + qn("w:drawing"))]

# ---------------------------------------------------------------- section reorder
def reorder_sections(body, seg_key, target_order, heading_style="Heading1"):
    """Reorder top-level sections. seg_key(text)->key or None; target_order is a list of
    keys in desired order. Segments start at each top-level heading; unkeyed leading content
    becomes a 'PREHEAD' segment. <w:sectPr> stays last. Returns the final key order.
    """
    sectPr = body.find(qn("w:sectPr"))
    children = [el for el in body if el is not sectPr]
    segments, cur = [], None
    for el in children:
        if is_p(el) and style_of(el) == heading_style:
            cur = {"key": seg_key(text_of(el)), "els": [el]}
            segments.append(cur)
        elif cur is None:
            cur = {"key": "PREHEAD", "els": [el]}
            segments.append(cur)
        else:
            cur["els"].append(el)
    order_index = {k: i for i, k in enumerate(["PREHEAD"] + list(target_order))}
    ordered = [s for _, s in sorted(enumerate(segments),
               key=lambda p: (order_index.get(p[1]["key"], 10**6), p[0]))]
    for el in children:
        body.remove(el)
    for seg in ordered:
        for el in seg["els"]:
            sectPr.addprevious(el) if sectPr is not None else body.append(el)
    return [s["key"] for s in ordered]

def add_line_numbering(body):
    """Add continuous line numbering (useful for review copies)."""
    sectPr = body.find(qn("w:sectPr"))
    if sectPr is None:
        return
    for e in sectPr.findall(qn("w:lnNumType")):
        sectPr.remove(e)
    ln = OxmlElement("w:lnNumType")
    ln.set(qn("w:countBy"), "1"); ln.set(qn("w:restart"), "continuous")
    cols = sectPr.find(qn("w:cols"))
    cols.addprevious(ln) if cols is not None else sectPr.append(ln)
