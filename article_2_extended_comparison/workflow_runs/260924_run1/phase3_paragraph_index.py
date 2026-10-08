"""Phase 3 input: number every paragraph of Daniil's edited .docx, citations as tokens.

Writes `00_paragraph_index.{md,json}`. Paragraph ids are `P<n>`, n counting the
non-empty `w:p` elements of the body in document order (table cells included and
flagged), so a writer's revision maps back onto exactly one Word paragraph for the
Phase 5 tracked-changes build. Text inside a `w:del` is dropped (it is not visible in
the accepted text); a Mendeley content control is written as `⟦CIT:<its text>⟧`, the
token a writer must carry through verbatim and in the same order (HARD_RULE 14); the
Word comments anchored in the paragraph are listed by id (C2 ... C74).

    python workflow_runs/260924_run1/phase3_paragraph_index.py
"""
import json
import zipfile
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "manuscript/FL_metric_classes_F1000_260917_edited_Daniil.docx"
RUN = Path(__file__).resolve().parent
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def is_mendeley(sdt) -> bool:
    pr = sdt.find(W + "sdtPr")
    return pr is not None and b"MENDELEY" in etree.tostring(pr)


def para_text(p) -> str:
    """Visible text of one paragraph, Mendeley content controls as CIT tokens."""
    out = []

    def walk(node):
        for ch in node:
            if ch.tag == W + "del":
                continue
            if ch.tag == W + "sdt" and is_mendeley(ch):
                txt = "".join(t.text or "" for t in ch.iter(W + "t"))
                out.append(f"⟦CIT:{txt}⟧")
                continue
            if ch.tag == W + "t":
                out.append(ch.text or "")
            elif ch.tag == W + "tab":
                out.append("\t")
            else:
                walk(ch)

    walk(p)
    return "".join(out)


def main() -> None:
    root = etree.fromstring(zipfile.ZipFile(BASE).read("word/document.xml"))
    body = root.find(W + "body")
    rows = []
    for p in body.iter(W + "p"):
        text = para_text(p)
        if not text.strip():
            continue
        style = p.find(f"{W}pPr/{W}pStyle")
        comments = sorted({int(c.get(W + "id")) for c in p.iter(W + "commentRangeStart")})
        in_table = any(a.tag == W + "tbl" for a in p.iterancestors())
        rows.append({"id": f"P{len(rows)}", "style": style.get(W + "val") if style is
                     not None else "", "in_table": in_table,
                     "comments": [f"C{c}" for c in comments],
                     "n_citations": text.count("⟦CIT:"), "text": text})
    (RUN / "00_paragraph_index.json").write_text(json.dumps(rows, indent=1,
                                                             ensure_ascii=False))
    lines = ["# 00 — Paragraph index of the base .docx (Phase 3 input), 2026-09-25", "",
             f"Source `{BASE.relative_to(ROOT)}`. {len(rows)} non-empty paragraphs. "
             "`⟦CIT:…⟧` is a Mendeley content control: carry it verbatim, same order, never "
             "add, move between paragraphs or delete one. Plain `[38]`, `[50,51]`, `[52]` "
             "are the four numeric citations, also verbatim.", ""]
    for r in rows:
        tag = " ".join(filter(None, [r["style"], "table" if r["in_table"] else "",
                                     " ".join(r["comments"])]))
        lines += [f"### {r['id']}  `{tag}`", "", r["text"], ""]
    (RUN / "00_paragraph_index.md").write_text("\n".join(lines))
    n_cit = sum(r["n_citations"] for r in rows)
    print(f"{len(rows)} paragraphs, {n_cit} CIT tokens, "
          f"{sum(len(r['comments']) for r in rows)} comment anchors")


if __name__ == "__main__":
    main()
