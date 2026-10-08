#!/usr/bin/env python
"""Extract Daniil's review of the Article 2 manuscript from his edited .docx.

Two outputs, both Markdown, both written into ``manuscript/``:

* ``daniil_comments_260924.md`` -- every Word comment, with the text it is
  anchored to, the section it sits in, and the tracked change (if any) that
  shares its anchor.
* ``daniil_diff_260924.md``     -- a paragraph-level diff of the agentic draft
  against Daniil's edited copy.

Daniil edited the .docx directly, so most of his changes are **not** tracked
revisions: the document carries 37 comments but only 10 ``w:ins`` and 8
``w:del``. The diff, not the revision marks, is what records what he did.
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MS = ROOT / "manuscript"
ORIG = MS / "FL_metric_classes_F1000_260917.docx"
EDIT = MS / "FL_metric_classes_F1000_260917_edited_Daniil.docx"

# Word lays out roughly this many body paragraphs per page in this template;
# calibrated against the edited copy, whose comments stop around page 16 of 31.
PARAS_PER_PAGE = 13.0


@dataclass
class Para:
    """One body paragraph, with the marks that matter for the review."""

    index: int
    style: str
    text: str
    is_heading: bool
    section: str = ""
    inserted: str = ""
    deleted: str = ""
    comment_ids: list[str] = field(default_factory=list)


def _runs(el: ET.Element, inside_del: bool = False) -> tuple[str, str, str]:
    """Return (visible_text, inserted_text, deleted_text) for one element."""
    vis, ins, dele = [], [], []
    for child in el:
        tag = child.tag
        if tag == W + "r":
            for t in child:
                if t.tag == W + "t":
                    s = t.text or ""
                    if inside_del:
                        dele.append(s)
                    else:
                        vis.append(s)
                elif t.tag == W + "delText":
                    dele.append(t.text or "")
                elif t.tag == W + "tab":
                    (dele if inside_del else vis).append("\t")
        elif tag == W + "ins":
            v, i, d = _runs(child, inside_del)
            vis.append(v)
            ins.append(v + i)
            dele.append(d)
        elif tag == W + "del":
            _, i, d = _runs(child, True)
            dele.append(d + i)
        elif tag in (W + "hyperlink", W + "smartTag", W + "sdtContent", W + "sdt"):
            v, i, d = _runs(child, inside_del)
            vis.append(v)
            ins.append(i)
            dele.append(d)
    return "".join(vis), "".join(ins), "".join(dele)


def read_paragraphs(path: Path) -> list[Para]:
    """Read every body paragraph of a .docx, including table cells, in order."""
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(W + "body")
    out: list[Para] = []
    section = ""

    def walk(el: ET.Element) -> None:
        nonlocal section
        for child in el:
            if child.tag == W + "p":
                pr = child.find(W + "pPr")
                style = ""
                if pr is not None:
                    st = pr.find(W + "pStyle")
                    if st is not None:
                        style = st.get(W + "val", "")
                vis, ins, dele = _runs(child)
                cids = [
                    c.get(W + "id")
                    for c in child.iter(W + "commentRangeStart")
                    if c.get(W + "id")
                ]
                cids += [
                    r.get(W + "id")
                    for r in child.iter(W + "commentReference")
                    if r.get(W + "id")
                ]
                is_head = style.lower().startswith("heading") or style == "Title"
                text = vis.strip()
                if is_head and text:
                    section = text
                if text or ins or dele or cids:
                    out.append(
                        Para(
                            index=len(out),
                            style=style,
                            text=text,
                            is_heading=is_head,
                            section=section,
                            inserted=ins.strip(),
                            deleted=dele.strip(),
                            comment_ids=sorted(set(cids), key=int),
                        )
                    )
            elif child.tag in (W + "tbl", W + "tr", W + "tc", W + "sdt",
                               W + "sdtContent"):
                walk(child)

    walk(body)
    return out


def read_comments(path: Path) -> dict[str, dict]:
    """Read ``word/comments.xml`` into {id: {author, date, text}}."""
    z = zipfile.ZipFile(path)
    if "word/comments.xml" not in z.namelist():
        return {}
    root = ET.fromstring(z.read("word/comments.xml"))
    out = {}
    for c in root.iter(W + "comment"):
        vis, ins, _ = _runs(c) if False else ("", "", "")
        parts = []
        for p in c.iter(W + "p"):
            v, i, d = _runs(p)
            parts.append(v.strip())
        out[c.get(W + "id")] = {
            "author": c.get(W + "author", ""),
            "date": (c.get(W + "date", "") or "")[:10],
            "initials": c.get(W + "initials", ""),
            "text": "\n".join(x for x in parts if x).strip(),
        }
    return out


def read_anchors(path: Path) -> dict[str, str]:
    """Return {comment id: the exact text the comment is attached to}.

    Word marks a comment span with ``commentRangeStart``/``commentRangeEnd``
    sentinels that sit *between* runs and may cross paragraphs, so the span has
    to be collected by walking the body in document order with a set of open
    ids. Taking the whole enclosing paragraph instead would make the four
    Abstract comments -- which ask four different things about four different
    clauses -- indistinguishable.
    """
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(W + "body")
    open_ids: set[str] = set()
    buf: dict[str, list[str]] = {}

    def walk(el: ET.Element) -> None:
        for child in el:
            tag = child.tag
            if tag == W + "commentRangeStart":
                cid = child.get(W + "id")
                if cid:
                    open_ids.add(cid)
                    buf.setdefault(cid, [])
            elif tag == W + "commentRangeEnd":
                open_ids.discard(child.get(W + "id"))
            elif tag in (W + "t", W + "delText"):
                if open_ids:
                    s = child.text or ""
                    for cid in open_ids:
                        buf[cid].append(s)
            else:
                walk(child)
            if tag == W + "p" and open_ids:
                for cid in open_ids:
                    buf[cid].append(" ")

    walk(body)
    return {k: re.sub(r"\s+", " ", "".join(v)).strip() for k, v in buf.items()}


def anchored_text(
    paras: list[Para], cid: str, anchors: dict[str, str]
) -> tuple[str, str, int]:
    """Return (anchored text, section, paragraph index) for one comment id."""
    hits = [p for p in paras if cid in p.comment_ids]
    para = hits[0] if hits else None
    span = anchors.get(cid, "")
    if not span and para is not None:
        span = para.text
    return span, (para.section if para else ""), (para.index if para else -1)


def page_of(index: int) -> int:
    """Approximate printed page of a paragraph index."""
    return int(index / PARAS_PER_PAGE) + 1


def write_comments_md(
    dst: Path, paras: list[Para], comments: dict[str, dict], anchors: dict[str, str]
) -> int:
    """Write the comment inventory."""
    rows = []
    for cid, c in sorted(comments.items(), key=lambda kv: int(kv[0])):
        text, section, idx = anchored_text(paras, cid, anchors)
        rows.append((cid, c, text, section, idx))
    rows.sort(key=lambda r: (r[4] if r[4] >= 0 else 10**6))

    L = [
        "# Daniil's comments on the Article 2 manuscript — extracted 2026-09-24",
        "",
        f"Source: `manuscript/{EDIT.name}`. "
        f"**{len(comments)} comments**, all by "
        + ", ".join(sorted({c['author'] for c in comments.values()}))
        + ".",
        "",
        "Comments are listed in document order. *Anchor* is the exact span the comment",
        "is attached to, collected between Word's commentRangeStart/End sentinels, so",
        "comments sharing a paragraph stay distinguishable. It is quoted from Daniil's",
        "edited copy, so it already reflects any manual rewriting of that sentence.",
        "The page is approximate",
        f"(~{PARAS_PER_PAGE:.0f} body paragraphs per page).",
        "",
    ]
    cur = None
    for cid, c, text, section, idx in rows:
        if section != cur:
            cur = section
            L += ["", f"## {section or '(front matter)'}", ""]
        L += [
            f"### C{cid} — p. ~{page_of(idx) if idx >= 0 else '?'} "
            f"({c['author']}, {c['date']})",
            "",
            "**Anchor:**",
            "",
            "> " + (
            text[:700] + ("…" if len(text) > 700 else "")
            if text
            else "*(whole paragraph)*"
        ),
            "",
            "**Comment:**",
            "",
            "> " + c["text"].replace("\n", "\n> "),
            "",
        ]
    dst.write_text("\n".join(L) + "\n", encoding="utf-8")
    return len(rows)


def write_diff_md(dst: Path, a: list[Para], b: list[Para]) -> dict:
    """Write a paragraph-level diff of the agentic draft against Daniil's copy."""
    at = [p.text for p in a]
    bt = [p.text for p in b]
    sm = difflib.SequenceMatcher(None, at, bt, autojunk=False)
    stats = {"equal": 0, "replace": 0, "delete": 0, "insert": 0}
    blocks = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        stats[tag] += max(i2 - i1, j2 - j1)
        if tag == "equal":
            continue
        blocks.append((tag, i1, i2, j1, j2))

    L = [
        "# Agentic draft vs. Daniil's edited copy — paragraph diff, 2026-09-24",
        "",
        f"`{ORIG.name}` (A) against `{EDIT.name}` (B), "
        "compared paragraph by paragraph.",
        "",
        f"A has **{len(a)}** paragraphs, B has **{len(b)}**. "
        f"**{stats['equal']}** are unchanged; "
        f"**{stats['replace']}** rewritten, **{stats['delete']}** removed, "
        f"**{stats['insert']}** added.",
        "",
        "Daniil edited the .docx directly, so almost none of this is a Word tracked",
        "revision — the diff below is the authoritative record of what he changed.",
        "",
        "Legend: **−** the agentic text, **+** Daniil's replacement.",
        "",
    ]
    cur = None
    for tag, i1, i2, j1, j2 in blocks:
        sec = (b[j1].section if j1 < len(b) else "") or (
            a[i1].section if i1 < len(a) else ""
        )
        if sec != cur:
            cur = sec
            L += ["", f"## {sec or '(front matter)'}", ""]
        L += [f"### {tag} — A[{i1}:{i2}] → B[{j1}:{j2}] (p. ~{page_of(j1)})", ""]
        for p in a[i1:i2]:
            if p.text:
                L.append(f"− {p.text}")
                L.append("")
        for p in b[j1:j2]:
            if p.text:
                cm = f"  `[C{','.join(p.comment_ids)}]`" if p.comment_ids else ""
                L.append(f"+ {p.text}{cm}")
                L.append("")
    dst.write_text("\n".join(L) + "\n", encoding="utf-8")
    return stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--orig", type=Path, default=ORIG)
    ap.add_argument("--edited", type=Path, default=EDIT)
    ap.add_argument("--out-dir", type=Path, default=MS)
    args = ap.parse_args(argv)

    a = read_paragraphs(args.orig)
    b = read_paragraphs(args.edited)
    comments = read_comments(args.edited)

    anchors = read_anchors(args.edited)
    n = write_comments_md(
        args.out_dir / "daniil_comments_260924.md", b, comments, anchors
    )
    stats = write_diff_md(args.out_dir / "daniil_diff_260924.md", a, b)

    last = max(
        (p.index for p in b if p.comment_ids or p.inserted or p.deleted), default=-1
    )
    print(f"paragraphs: A={len(a)} B={len(b)}")
    print(f"comments written: {n}")
    print(f"diff blocks: replace={stats['replace']} "
          f"delete={stats['delete']} insert={stats['insert']} equal={stats['equal']}")
    print(f"last marked paragraph: B[{last}] ~ page {page_of(last)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
