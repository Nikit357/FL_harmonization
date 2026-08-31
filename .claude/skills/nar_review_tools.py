#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Measurement tools for the `NAR_review` skill — run these instead of reading files.

Every subcommand prints a compact report and keeps the raw bytes out of the agent's
context. Read `NAR_review.md` for the procedure these implement.

    source ~/venvs/collagen_3_11/bin/activate
    S=~/FL_harmonization/.claude/skills/nar_review_tools.py

    python $S extract   MS.docx  /tmp/.../manuscript.txt   # body dump, ONE read afterwards
    python $S docx      MS.docx                            # formatting / abstract / variants
    python $S fields    MS.docx                            # how citations are stored (critical)
    python $S figures   FIGDIR/                            # geometry, legibility, fonts, colour
    python $S figtext   FIGDIR/ --grep 04_sva 34_arsyn     # which figure contains which label
    python $S render    FIGDIR/ OUTDIR/ --only "Figure 3"  # PDF -> PNG for visual review
    python $S validate  MS.docx  MS_edited.docx            # tracked-change integrity

`safe_tracked_replace` is importable and is the citation-safe replacement for
`word_rewrite_trackchanges.tracked_replace` — see the docstring for why.

Dependencies: python-docx, lxml, pandas (all in ~/venvs/collagen_3_11); pymupdf for the
figure subcommands (`pip install pymupdf` if missing).
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import sys
import zipfile
from collections import Counter

import docx
from docx.oxml.ns import qn

# ----------------------------------------------------------------- OOXML shorthands
W_P, W_R, W_T, W_RPR = qn("w:p"), qn("w:r"), qn("w:t"), qn("w:rPr")
W_TBL, W_SECTPR, W_SDT = qn("w:tbl"), qn("w:sectPr"), qn("w:sdt")
W_INS, W_DEL, W_DELTEXT = qn("w:ins"), qn("w:del"), qn("w:delText")
W_LRPB = qn("w:lastRenderedPageBreak")
# A run holding only these can be safely rebuilt; w:lastRenderedPageBreak is a layout
# hint Word regenerates. Anything else (w:br, w:tab, w:drawing, footnote refs) is not.
W_SAFE_RUN_KIDS = (W_RPR, W_T, W_LRPB)

# NAR printed-figure limits (author guidelines Part 6.4), in centimetres.
NAR_MAX_W_CM, NAR_MAX_H_CM = 17.35, 23.35
MIN_LEGIBLE_PT = 5.0


def text_of(el) -> str:
    """All visible text under an element (w:t and w:delText)."""
    return "".join(t.text or "" for t in
                   el.findall(".//" + W_T) + el.findall(".//" + W_DELTEXT))


def accepted_text(el) -> str:
    """Text as it reads after Accept All: w:t not inside a w:del."""
    return "".join(t.text or "" for t in el.findall(".//" + W_T)
                   if not any(a.tag == W_DEL for a in t.iterancestors()))


def style_of(p) -> str:
    ppr = p.find(qn("w:pPr"))
    if ppr is None:
        return ""
    ps = ppr.find(qn("w:pStyle"))
    return ps.get(qn("w:val")) if ps is not None else ""


# ===================================================================== 1. extract
def cmd_extract(args):
    """Dump the body with body-child indices, styles, italic markers and revision flags.

    Italic runs are wrapped in {{ ... }} so author placeholder text can be skipped on
    sight — Daniil marks unfinished passages in italics. Write once, then Read the
    text file in 2-3 chunks; never Read the .docx repeatedly.
    """
    doc = docx.Document(args.docx)
    body = doc.element.body

    def run_italic(r):
        rpr = r.find(W_RPR)
        if rpr is None:
            return False
        i = rpr.find(qn("w:i"))
        return i is not None and i.get(qn("w:val")) not in ("0", "false")

    def marked(p):
        parts, open_i = [], False
        for r in p.iter(W_R):
            ts = r.findall(W_T) + r.findall(W_DELTEXT)
            if not ts:
                if r.findall(".//" + qn("w:drawing")):
                    parts.append("<IMAGE>")
                continue
            txt = "".join(t.text or "" for t in ts)
            if not txt:
                continue
            ital = run_italic(r)
            if ital and not open_i:
                parts.append("{{"); open_i = True
            elif not ital and open_i:
                parts.append("}}"); open_i = False
            parts.append(txt)
        if open_i:
            parts.append("}}")
        return "".join(parts)

    lines, n_img = [], 0
    for idx, el in enumerate(body):
        if el.tag == W_P:
            flags = [f for f, t in (("INS", W_INS), ("DEL", W_DEL)) if el.findall(".//" + t)]
            fl = "{" + ",".join(flags) + "}" if flags else ""
            if el.findall(".//" + qn("w:drawing")):
                n_img += 1
            txt = marked(el)
            lines.append(f"[{idx}] <{style_of(el)}> {fl} {txt if txt.strip() else '(empty)'}")
        elif el.tag == W_TBL:
            rows = []
            for tr in el.findall(qn("w:tr")):
                rows.append(" | ".join(
                    " ".join("".join(t.text or "" for t in p.findall(".//" + W_T))
                             for p in tc.findall(qn("w:p"))).strip()
                    for tc in tr.findall(qn("w:tc"))))
            lines.append(f"[{idx}] <TABLE {len(rows)} rows>")
            lines.extend(f"      {r}" for r in rows)
        elif el.tag == W_SECTPR:
            lines.append(f"[{idx}] <SECTPR>")
        else:
            lines.append(f"[{idx}] <{el.tag.split('}')[-1]}>")

    with open(args.out, "w") as fh:
        fh.write("\n".join(lines))
    words = len("\n".join(lines).split())
    print(f"body children {len(body)} | paragraph images {n_img} | "
          f"w:ins {len(body.findall('.//' + W_INS))} w:del {len(body.findall('.//' + W_DEL))}")
    print(f"wrote {args.out}  (~{words} words, ~{int(words * 1.4)} tokens to Read)")


# ===================================================================== 2. docx checks
def cmd_docx(args):
    """Formatting vs the NAR template, abstract word count, spelling variants, placeholders."""
    doc = docx.Document(args.docx)
    body, sec = doc.element.body, doc.sections[0]

    print("== PAGE SETUP (NAR template: A4 21.0x29.7 cm, 1 in margins) ==")
    print(f"  page    {sec.page_width.cm:.2f} x {sec.page_height.cm:.2f} cm"
          f"{'  <-- US Letter, not A4' if abs(sec.page_width.cm - 21.0) > 0.3 else ''}")
    print(f"  margins T{sec.top_margin.cm:.2f} B{sec.bottom_margin.cm:.2f} "
          f"L{sec.left_margin.cm:.2f} R{sec.right_margin.cm:.2f} cm")
    sectPr = body.find(W_SECTPR)
    print(f"  line numbering (recommended for review): "
          f"{sectPr is not None and sectPr.find(qn('w:lnNumType')) is not None}")

    z = zipfile.ZipFile(args.docx)
    hf = [n for n in z.namelist() if "header" in n or "footer" in n]
    print(f"  header/footer parts: {hf or 'NONE -> no page numbers'}")

    st = doc.styles["Normal"]
    print(f"\n== NORMAL STYLE (template: 11 pt, 1.15 spacing, ~10 pt after) ==")
    print(f"  font={st.font.name} size={st.font.size.pt if st.font.size else None} "
          f"spacing={st.paragraph_format.line_spacing} "
          f"after={st.paragraph_format.space_after.pt if st.paragraph_format.space_after else None}")

    sizes = Counter()
    for r in body.iter(W_R):
        rpr = r.find(W_RPR)
        sz = rpr.find(qn("w:sz")) if rpr is not None else None
        txt = "".join(t.text or "" for t in r.findall(W_T))
        if txt.strip():
            sizes[int(sz.get(qn("w:val"))) / 2 if sz is not None else None] += len(txt)
    print(f"  explicit run sizes by chars: {sizes.most_common(6)}")

    paras = list(body.iter(W_P))
    for i, p in enumerate(paras):
        if accepted_text(p).strip().upper() == "ABSTRACT":
            for q in paras[i + 1:]:
                t = accepted_text(q).strip()
                if t:
                    n = len(t.split())
                    print(f"\n== ABSTRACT: {n} words (NAR limit 200)"
                          f"{f' -> OVER BY {n - 200}' if n > 200 else ''} ==")
                    break
            break

    full = "\n".join(accepted_text(p) for p in paras)
    print(f"\n== BODY ~{len(full.split())} words ==")

    print("\n== SPELLING VARIANTS (NAR accepts either, demands consistency) ==")
    for a, b in [("neighbor", "neighbour"), (r"\bcenter", r"\bcentre"), ("tumor", "tumour"),
                 (r"\bcolor", "colour"), ("artifact", "artefact"), (r"\blabeled", "labelled"),
                 ("analyze", "analyse"), (r"\btSNE", "t-SNE")]:
        na, nb = len(re.findall(a, full, re.I)), len(re.findall(b, full, re.I))
        if na and nb:
            print(f"  MIXED  {a} {na}  vs  {b} {nb}")
        elif na or nb:
            print(f"  ok     {a if na else b} {na or nb}")

    print("\n== UNRESOLVED PLACEHOLDERS / STRAY NOTES ==")
    for pat in [r"\(ref\)", r"XXXX", r"\bTBD\b", r"\[full official", r"check later",
                r"correct it", r"create a repo", r"add link", r"maybe move", r"…",
                r"\.\.\.", r"[Ѐ-ӿ]+"]:
        hits = re.findall(pat, full, re.I)
        if hits:
            print(f"  {pat!r}: {len(hits)}")
    for p in paras:
        t = accepted_text(p)
        if re.search(r"[Ѐ-ӿ]", t):
            print(f"  CYRILLIC: {t[:90]}")

    print("\n== FIGURE / TABLE CITATION COVERAGE ==")
    for lbl in ("Supplementary Figure", "Supplementary File", "Extended Figure", "Figure", "Table"):
        # bare "Figure"/"Table" must not match "Supplementary Figure"/"Extended Figure"
        pre = "" if " " in lbl else r"(?<!Supplementary )(?<!Extended )"
        nums = sorted({int(m) for m in re.findall(rf"{pre}{lbl}s?\s+(\d+)", full)})
        gaps = [n for n in range(1, max(nums) + 1) if n not in nums] if nums else []
        print(f"  {lbl:22s} cited: {nums}{f'  GAPS {gaps}' if gaps else ''}")


# ===================================================================== 3. citation fields
def cmd_fields(args):
    """How are citations stored?  RUN THIS BEFORE ANY EDIT.

    Mendeley may use w:fldChar/w:instrText fields OR w:sdt structured-document tags.
    `tracked_replace` flattens a paragraph and destroys BOTH. This lists every paragraph
    that must be edited with `safe_tracked_replace` instead.
    """
    doc = docx.Document(args.docx)
    body = doc.element.body
    print(f"w:fldChar {len(body.findall('.//' + qn('w:fldChar')))} | "
          f"w:instrText {len(body.findall('.//' + qn('w:instrText')))} | "
          f"w:sdt {len(body.findall('.//' + W_SDT))} | "
          f"w:hyperlink {len(body.findall('.//' + qn('w:hyperlink')))}")
    risky = 0
    for i, el in enumerate(body):
        if el.tag != W_P:
            continue
        marks = [m for m, t in (("SDT", W_SDT), ("FLD", qn("w:fldChar")),
                                ("LINK", qn("w:hyperlink"))) if el.findall(".//" + t)]
        if marks:
            risky += 1
            print(f"  [{i}] {'+'.join(marks):12s} {accepted_text(el)[:78]}")
    print(f"\n{risky} paragraphs hold citation fields or links -> "
          f"tracked_replace() would destroy them; use safe_tracked_replace().")
    for s in [el for el in body if el.tag == W_SDT]:
        bib = text_of(s)
        nums = sorted({int(n) for n in re.findall(r"(\d{1,3})\.\s[A-Z][a-z]", bib)})
        if len(nums) > 5:
            print(f"\nStandalone bibliography sdt: {len(bib)} chars, "
                  f"entries {min(nums)}-{max(nums)} ({len(nums)} found)")


# ===================================================================== 4. figures
def _pdf_pages(path):
    import pymupdf
    return pymupdf.open(path)


def cmd_figures(args):
    """Geometry, legibility at the journal's max print size, fonts, colour space."""
    files = sorted(glob.glob(os.path.join(args.figdir, "*.pdf")))
    print(f"NAR max print box {NAR_MAX_W_CM} x {NAR_MAX_H_CM} cm; "
          f"flagging text below {MIN_LEGIBLE_PT} pt after scaling\n")
    hdr = (f"{'figure':32s} {'MB':>6s} {'p':>2s} {'w x h cm':>13s} {'scl':>5s} "
           f"{'med pt':>7s} {'<5pt':>6s} {'fonts':<22s} colour")
    print(hdr)
    print("-" * len(hdr))
    for f in files:
        doc = _pdf_pages(f)
        page = doc[0]
        w = page.rect.width * 2.54 / 72
        h = page.rect.height * 2.54 / 72
        scale = min(NAR_MAX_W_CM / w, NAR_MAX_H_CM / h, 1.0)
        sizes, fonts = [], set()
        for blk in page.get_text("dict")["blocks"]:
            for ln in blk.get("lines", []):
                for sp in ln["spans"]:
                    if sp["text"].strip():
                        sizes.append(sp["size"])
                        fonts.add(re.sub(r"\(\d+ \d+ R\)", "", sp["font"]).strip())
        med = sorted(sizes)[len(sizes) // 2] * scale if sizes else 0
        pct = f"{100 * sum(1 for s in sizes if s * scale < MIN_LEGIBLE_PT) / len(sizes):.0f}%" \
            if sizes else "n/a"
        raw = open(f, "rb").read()
        cs = ",".join(sorted({m for m in ("DeviceRGB", "DeviceCMYK", "DeviceGray")
                              if m.encode() in raw}))
        emb = len(re.findall(rb"/FontFile[23]?", raw))
        print(f"{os.path.basename(f):32s} {len(raw)/1e6:6.2f} {len(doc):2d} "
              f"{w:5.1f} x {h:5.1f} {scale:5.2f} {med:7.1f} {pct:>6s} "
              f"{','.join(sorted(fonts))[:22]:<22s} {cs} emb={emb}")
        doc.close()

    print("\nRasters and duplicates:")
    for f in sorted(glob.glob(os.path.join(args.figdir, "*"))):
        ext = f.rsplit(".", 1)[-1].lower()
        if ext in ("png", "jpg", "jpeg", "tif", "tiff"):
            from PIL import Image
            im = Image.open(f)
            print(f"  {os.path.basename(f):32s} {im.size} {im.mode} "
                  f"ratio {im.size[0]/im.size[1]:.2f}"
                  f"{'  <-- JPG, NAR advises against' if ext in ('jpg', 'jpeg') else ''}")
        elif os.path.isdir(f):
            print(f"  {os.path.basename(f):32s} DIR")
        elif "." not in os.path.basename(f):
            print(f"  {os.path.basename(f):32s} NO EXTENSION "
                  f"({os.path.getsize(f)} bytes) -- rename for submission")
    over = [os.path.basename(f) for f in glob.glob(os.path.join(args.figdir, "*"))
            if os.path.isfile(f) and os.path.getsize(f) > 2e6]
    n = len([f for f in glob.glob(os.path.join(args.figdir, "*")) if os.path.isfile(f)])
    print(f"\nSupplementary limits (NAR: one PDF, else <=10 files of <=2 MB):")
    print(f"  {n} files in folder; {len(over)} exceed 2 MB: {over}")


def cmd_figtext(args):
    """Which figure contains which label — catches items silently dropped from analyses."""
    texts = {}
    for f in sorted(glob.glob(os.path.join(args.figdir, "*.pdf"))):
        doc = _pdf_pages(f)
        texts[os.path.basename(f)] = "".join(p.get_text() for p in doc)
        doc.close()
    union = "".join(texts.values())
    missing = [t for t in args.grep if t not in union]
    print(f"terms absent from EVERY figure: {missing}")
    for name, body in texts.items():
        present = [t for t in args.grep if t in body]
        if present or args.verbose:
            print(f"  {name:32s} {len(present)}/{len(args.grep)} "
                  f"missing={[t for t in args.grep if t not in body]}")


def cmd_render(args):
    """Render figure PDFs to PNG so only a handful need to enter context as images."""
    os.makedirs(args.outdir, exist_ok=True)
    pats = args.only or ["*"]
    for pat in pats:
        for f in sorted(glob.glob(os.path.join(args.figdir, f"{pat}*.pdf" if pat != "*" else "*.pdf"))):
            doc = _pdf_pages(f)
            for i, page in enumerate(doc):
                out = os.path.join(args.outdir,
                                   f"{os.path.basename(f)[:-4].replace(' ', '_')}_p{i}.png")
                pix = page.get_pixmap(dpi=args.dpi)
                pix.save(out)
                print(f"  {out} {pix.width}x{pix.height}")
            doc.close()


# ===================================================================== 5. tracked edits
def _direct_runs(p):
    """Runs that are direct children of p — never inside w:sdt / w:hyperlink."""
    return [c for c in p if c.tag == W_R]


def _run_is_plain(r):
    return all(c.tag in W_SAFE_RUN_KIDS for c in r)


def safe_tracked_replace(p, replacements):
    """Citation-safe tracked del+ins for substrings inside a paragraph.

    Use this INSTEAD of word_rewrite_trackchanges.tracked_replace whenever the document
    holds Mendeley/EndNote citations: tracked_replace rebuilds the paragraph from its
    concatenated text and re-emits plain runs, which silently deletes every w:sdt or
    field in that paragraph. This function edits only direct-child runs, so anything
    nested in w:sdt or w:hyperlink survives byte-for-byte.

    `old` must lie inside one uninterrupted stretch of prose — it may span several runs
    but must not span a citation. `new=""` gives a pure tracked deletion.

    Returns [(old, 'ok' | 'not-found' | 'unsafe'), ...].
    Requires word_rewrite_trackchanges on sys.path (make_run/make_del_run/wrap_ins/wrap_del).
    """
    from word_rewrite_trackchanges import make_del_run, make_run, wrap_del, wrap_ins

    results = []
    for old, new in replacements:
        runs = _direct_runs(p)
        texts = ["".join(t.text or "" for t in r.findall(W_T)) for r in runs]
        joined = "".join(texts)
        start = joined.find(old)
        if start < 0:
            results.append((old, "not-found"))
            continue
        end = start + len(old)
        offsets, acc = [], 0
        for t in texts:
            offsets.append(acc)
            acc += len(t)
        first = last = None
        for i, t in enumerate(texts):
            if offsets[i] < end and offsets[i] + len(t) > start:
                first = i if first is None else first
                last = i
        if not all(_run_is_plain(runs[i]) for i in range(first, last + 1)):
            results.append((old, "unsafe"))
            continue
        base = runs[first].find(W_RPR)
        prefix = texts[first][: start - offsets[first]]
        suffix = texts[last][end - offsets[last]:]
        new_els = []
        if prefix:
            new_els.append(make_run(prefix, base=base))
        new_els.append(wrap_del(make_del_run(old, base=base)))
        if new:
            new_els.append(wrap_ins(make_run(new, base=base)))
        if suffix:
            new_els.append(make_run(suffix, base=base))
        anchor = runs[first]
        for el in new_els:
            anchor.addprevious(el)
        for r in runs[first:last + 1]:
            p.remove(r)
        results.append((old, "ok"))
    return results


# ===================================================================== 6. validate
def cmd_validate(args):
    """Tracked-change integrity: reject-all must restore the original byte-for-byte."""
    d0, d1 = docx.Document(args.src), docx.Document(args.dst)
    b0, b1 = d0.element.body, d1.element.body
    fails = []

    z = zipfile.ZipFile(args.dst)
    for part in ("word/document.xml", "word/styles.xml", "word/settings.xml"):
        r = subprocess.run([sys.executable, "-c",
                            "import sys,lxml.etree as e; e.fromstring(sys.stdin.buffer.read())"],
                           input=z.read(part), capture_output=True)
        print(f"1. {part} parses: {r.returncode == 0}")
        if r.returncode:
            fails.append(f"{part} malformed")

    bad_t = sum(len(el.findall(".//" + W_T)) for el in b1.iter(W_DEL))
    bad_dt = len([t for t in b1.iter(W_DELTEXT)
                  if not any(a.tag == W_DEL for a in t.iterancestors())])
    revs = list(b1.iter(W_INS)) + list(b1.iter(W_DEL))
    miss = [r for r in revs if not all(r.get(qn(a)) for a in ("w:id", "w:author", "w:date"))]
    ids = [r.get(qn("w:id")) for r in revs]
    print(f"2. revisions {len(revs)} | w:t in w:del {bad_t} | stray delText {bad_dt} | "
          f"missing attrs {len(miss)} | dup ids {len(ids) - len(set(ids))}")
    for nm, v in (("w:t in w:del", bad_t), ("stray delText", bad_dt),
                  ("missing rev attrs", len(miss)), ("dup ids", len(ids) - len(set(ids)))):
        if v:
            fails.append(f"{nm}={v}")

    def reject_all(body):
        out = []
        for t in body.iter():
            if t.tag == W_T and not any(a.tag == W_INS for a in t.iterancestors()):
                out.append(t.text or "")
            elif t.tag == W_DELTEXT:
                out.append(t.text or "")
        return "".join(out)

    r0, r1 = reject_all(b0), reject_all(b1)
    same = r0 == r1
    print(f"3. reject-all restores the original: {same}")
    if not same:
        i = next((k for k in range(min(len(r0), len(r1))) if r0[k] != r1[k]),
                 min(len(r0), len(r1)))
        print(f"   first divergence @{i}\n   orig: ...{r0[i-80:i+80]!r}\n   rej : ...{r1[i-80:i+80]!r}")
        fails.append("reject-all differs from original")

    def sdt_texts(b):
        return [text_of(s) for s in b.findall(".//" + W_SDT)]

    n0, n1 = len(b0.findall(".//" + W_SDT)), len(b1.findall(".//" + W_SDT))
    l0, l1 = (len(b.findall(".//" + qn("w:hyperlink"))) for b in (b0, b1))
    ident = sdt_texts(b0) == sdt_texts(b1)
    print(f"4. citation fields: sdt {n1} (was {n0}), hyperlinks {l1} (was {l0}), "
          f"contents identical: {ident}")
    if n0 != n1 or l0 != l1 or not ident:
        fails.append("citation fields altered")

    paras = list(b1.iter(W_P))
    for i, p in enumerate(paras):
        if accepted_text(p).strip().upper() == "ABSTRACT":
            for q in paras[i + 1:]:
                t = accepted_text(q).strip()
                if t:
                    n = len(t.split())
                    print(f"5. abstract after Accept All: {n} words (limit 200)")
                    if n > 200:
                        fails.append(f"abstract {n} > 200 words")
                    break
            break

    acc = accepted_text(b1)
    notes = acc.count("[REVIEWER NOTE]") + acc.count("[EDITOR NOTE]")
    print(f"6. inserted note paragraphs: {notes}")
    for s in args.absent or []:
        if s in acc:
            print(f"   STILL PRESENT after accept: {s!r} "
                  f"(check it is not merely quoted inside a reviewer note)")
    print("\n" + ("ALL CHECKS PASSED" if not fails else "FAILURES:\n  " + "\n  ".join(fails)))
    return 1 if fails else 0


# ===================================================================== CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("extract", help="body dump with indices/italics/revisions")
    p.add_argument("docx"); p.add_argument("out"); p.set_defaults(fn=cmd_extract)

    p = sub.add_parser("docx", help="formatting, abstract, variants, placeholders")
    p.add_argument("docx"); p.set_defaults(fn=cmd_docx)

    p = sub.add_parser("fields", help="how citations are stored (run before editing)")
    p.add_argument("docx"); p.set_defaults(fn=cmd_fields)

    p = sub.add_parser("figures", help="geometry, legibility, fonts, colour space")
    p.add_argument("figdir"); p.set_defaults(fn=cmd_figures)

    p = sub.add_parser("figtext", help="which figure contains which label")
    p.add_argument("figdir"); p.add_argument("--grep", nargs="+", required=True)
    p.add_argument("--verbose", action="store_true"); p.set_defaults(fn=cmd_figtext)

    p = sub.add_parser("render", help="PDF -> PNG for visual review")
    p.add_argument("figdir"); p.add_argument("outdir")
    p.add_argument("--only", nargs="*"); p.add_argument("--dpi", type=int, default=90)
    p.set_defaults(fn=cmd_render)

    p = sub.add_parser("validate", help="tracked-change integrity")
    p.add_argument("src"); p.add_argument("dst")
    p.add_argument("--absent", nargs="*", help="strings that must be gone after Accept All")
    p.set_defaults(fn=cmd_validate)

    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
