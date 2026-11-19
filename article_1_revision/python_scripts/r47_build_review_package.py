"""r47 — final review package of the NARGAB-2026-312 revision (Daniil 2026-11-09).

Collects every article material into Revised_manuscript/review_package_<tag>/:

  1_manuscript/           tracked docx (newest r50 stage B) + clean copy (all changes accepted)
  2_response_letter/      newest response-letter docx built by r60 (draft while [LINES] remain)
  3_main_tables/          Tables 1–3 cut from the clean manuscript: one docx + one xlsx (a sheet
                          per table)
  4_main_figures/         review PDF of the revised main-figure panels (r46)
  5_supplementary_figures/ Supplementary Figures S1-S18 review PDF (r46)
  6_supplementary_files/  Supplementary Files 1–3 (r40)
  README.md               inventory: file, size, what it is, source script

The clean copy is built here (accept-all on the XML): deleted runs / rows / paragraphs are
dropped, inserted ones unwrapped, formatting-change records removed; a paragraph whose mark was
deleted is merged into the next one. It is checked against the accept-all text that r90 / r99 read
(revision_lib.docx_paragraphs(view="accept")).

Run: python r47_build_review_package.py [--tag YYMMDD] (after r46 with the same tag)."""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import shutil
import zipfile
from pathlib import Path

import docx
import pandas as pd
from lxml import etree

import revision_lib as rl

REV = rl.REVISION_DIR
MANUSCRIPT_DIR = REV / "Revised_manuscript"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"
DROP_WITH_CONTENT = ("del", "moveFrom")
UNWRAP = ("ins", "moveTo")
DROP_MARKERS = ("rPrChange", "pPrChange", "sectPrChange", "tblPrChange", "trPrChange", "tcPrChange",
                "tblGridChange", "numberingChange", "moveFromRangeStart", "moveFromRangeEnd",
                "moveToRangeStart", "moveToRangeEnd")
TABLE_TITLE_PREFIX = "Table "


def newest(pattern: str) -> Path:
    """Newest file in Revised_manuscript/ matching the pattern (date tag in the name)."""
    hits = sorted(MANUSCRIPT_DIR.glob(pattern))
    assert hits, pattern
    return hits[-1]


def paragraph_mark_deleted(p: etree._Element) -> bool:
    return p.find(f"{W}pPr/{W}rPr/{W}del") is not None


def accept_all_xml(root: etree._Element) -> None:
    """Accept every tracked change of one XML part in place."""
    for tr in root.iter(f"{W}tr"):
        if tr.find(f"{W}trPr/{W}del") is not None:
            tr.getparent().remove(tr)
    paragraphs = list(root.iter(f"{W}p"))
    deleted_marks = {id(p) for p in paragraphs if paragraph_mark_deleted(p)}
    for tag in DROP_WITH_CONTENT:
        for el in list(root.iter(f"{W}{tag}")):
            parent = el.getparent()
            if parent is not None and parent.tag != f"{W}rPr":  # rPr/del = deleted mark, handled below
                parent.remove(el)
    for tag in UNWRAP:
        for el in list(root.iter(f"{W}{tag}")):
            parent = el.getparent()
            if parent is None or parent.tag in (f"{W}rPr", f"{W}trPr"):
                if parent is not None:
                    parent.remove(el)
                continue
            index = parent.index(el)
            for child in list(el):
                parent.insert(index, child)
                index += 1
            parent.remove(el)
    for tag in DROP_MARKERS:
        for el in list(root.iter(f"{W}{tag}")):
            el.getparent().remove(el)
    # paragraphs whose mark was deleted: content joins the next paragraph
    for p in [p for p in paragraphs if id(p) in deleted_marks]:
        mark = p.find(f"{W}pPr/{W}rPr/{W}del")
        if mark is not None:
            mark.getparent().remove(mark)
        content = [c for c in p if c.tag != f"{W}pPr"]
        following = p.getnext()
        if content and following is not None and following.tag == f"{W}p":
            ppr = following.find(f"{W}pPr")
            index = 0 if ppr is None else following.index(ppr) + 1
            for child in content:
                following.insert(index, child)
                index += 1
        p.getparent().remove(p)


def accept_all_docx(source: Path, target: Path) -> None:
    """Copy a docx with every tracked change accepted (document, headers, footers, notes)."""
    with zipfile.ZipFile(source) as zin, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.startswith("word/") and item.filename.endswith(".xml") and b"w:" in data:
                root = etree.fromstring(data)
                accept_all_xml(root)
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            zout.writestr(item, data)


def check_clean_text(tracked: Path, clean: Path) -> None:
    """The clean copy must read exactly like the accept-all view used by r90 / r99."""
    def joined(path, view):
        return "\n".join(p["text"] for p in rl.docx_paragraphs(path, view=view) if p["text"].strip())
    expected, got = joined(tracked, "accept"), joined(clean, "accept")
    assert expected == got, "clean copy differs from the accept-all view"
    tracked_left = sum(1 for _ in etree.fromstring(zipfile.ZipFile(clean).read("word/document.xml")).iter(f"{W}ins", f"{W}del"))
    assert tracked_left == 0, f"{tracked_left} tracked marks left in the clean copy"


def text_of(el: etree._Element) -> str:
    return "".join(t.text or "" for t in el.iter(f"{W}t"))


def main_tables(clean: Path, out_docx: Path, out_xlsx: Path) -> list[str]:
    """Tables 1–3 with their title paragraphs (and notes right below) → docx + xlsx."""
    document = docx.Document(str(clean))
    body = document.element.body
    children = list(body.iterchildren())
    keep: list[etree._Element] = []
    titles: list[str] = []
    for i, el in enumerate(children):
        if el.tag != f"{W}tbl":
            continue
        title = next(children[j] for j in range(i - 1, -1, -1)
                     if children[j].tag == f"{W}p" and text_of(children[j]).startswith(TABLE_TITLE_PREFIX))
        titles.append(text_of(title))
        keep += [title, el, etree.Element(f"{W}p")]  # empty paragraph between tables
    sect = body.find(f"{W}sectPr")
    for el in list(body):
        if el is not sect:
            body.remove(el)
    for el in keep:
        body.insert(body.index(sect) if sect is not None else len(body), copy.deepcopy(el))
    # the figures stay in the manuscript: drop image relationships no kept element uses (24 MB → KB)
    used = set(body.xpath(".//@r:embed | .//@r:id"))
    for rel_id, rel in list(document.part.rels.items()):
        if rel.reltype.endswith("/image") and rel_id not in used:
            document.part.drop_rel(rel_id)
    document.save(str(out_docx))
    with pd.ExcelWriter(out_xlsx) as writer:
        for n, table in enumerate(document.tables, start=1):
            rows = [[cell.text for cell in row.cells] for row in table.rows]
            header = [c if rows[0].count(c) == 1 else f"{c} ({k + 1})" for k, c in enumerate(rows[0])]
            frame = pd.DataFrame(rows[1:], columns=header)
            frame.to_excel(writer, sheet_name=f"Table {n}", index=False)
    return titles


def main() -> None:
    parser = argparse.ArgumentParser(description="final review package")
    parser.add_argument("--tag", default=dt.date.today().strftime("%y%m%d"))
    tag = parser.parse_args().tag
    package = MANUSCRIPT_DIR / f"review_package_{tag}"
    parts = {name: package / name for name in ("1_manuscript", "2_response_letter", "3_main_tables",
                                                "4_main_figures", "5_supplementary_figures",
                                                "6_supplementary_files")}
    for folder in parts.values():
        folder.mkdir(parents=True, exist_ok=True)
    inventory = []

    def add(src: Path, folder: str, name: str | None, what: str, made_by: str) -> Path:
        target = parts[folder] / (name or src.name)
        if src != target:
            shutil.copy2(src, target)
        inventory.append((f"{folder}/{target.name}", round(target.stat().st_size / 1e6, 2), what, made_by))
        return target

    tracked = newest("FL_harmonization_article_NARGAB_tracked_stageB_*.docx")
    add(tracked, "1_manuscript", None, "manuscript with tracked changes (Reject All = submitted text)", "r50 --stage B")
    clean = parts["1_manuscript"] / tracked.name.replace("_tracked_stageB_", "_clean_")
    accept_all_docx(tracked, clean)
    check_clean_text(tracked, clean)
    add(clean, "1_manuscript", None, "same manuscript, every change accepted", "r47")

    letter = newest("NARGAB-2026-312_response_to_reviewers_*.docx")
    add(letter, "2_response_letter", None,
        "response to the reviewers" + (" (DRAFT: [LINES] markers wait for Word line numbers)" if "DRAFT" in letter.name else ""),
        "r60" + (" --draft" if "DRAFT" in letter.name else ""))

    tables_docx = parts["3_main_tables"] / f"Main Tables 1-3 {tag}.docx"
    tables_xlsx = parts["3_main_tables"] / f"Main Tables 1-3 {tag}.xlsx"
    titles = main_tables(clean, tables_docx, tables_xlsx)
    add(tables_docx, "3_main_tables", None, "; ".join(t.split(".")[0] for t in titles) + " with titles (clean text)", "r47")
    add(tables_xlsx, "3_main_tables", None, "same tables, one sheet each", "r47")

    # r46 writes its PDFs and figure_sources.tsv at the package root: move them into place
    for p in package.glob("*.pdf"):
        p.replace(parts["4_main_figures" if p.name.startswith("Revised") else "5_supplementary_figures"] / p.name)
    if (package / "figure_sources.tsv").exists():
        (package / "figure_sources.tsv").replace(parts["4_main_figures"] / "figure_sources.tsv")
    add(parts["4_main_figures"] / f"Revised main-figure panels (review draft) {tag}.pdf", "4_main_figures", None,
        "revised main-figure panels (1E, 2A, 3, 4, 5, 6B–F), one panel per page", "r46")
    add(parts["5_supplementary_figures"] / f"Supplementary Figures S1-S18 (review draft) {tag}.pdf", "5_supplementary_figures", None,
        "Supplementary Figures S1–S18, new numbering, alt-text line per figure", "r46")
    for n, what in [(1, "per-cohort sample table (88 cohorts)"), (2, "metric definitions, polarity, panel"),
                    (3, "metrics of every approach; gradient and leave-cohort-out sheets")]:
        src = next((rl.OUTPUT_DIR / "wp10").glob(f"Supplementary File {n}.*"))
        add(src, "6_supplementary_files", None, what, "r40")

    lines = [f"# Review package {tag} — NARGAB-2026-312 revision (all article materials)", "",
             "Read `../../gates_review_261102.md` §13 first (what changed since 261108, open decisions).", "",
             "| File | MB | What it is | Made by |", "|---|---|---|---|"]
    lines += [f"| `{f}` | {mb} | {what} | {by} |" for f, mb, what, by in inventory]
    lines += ["", f"Rebuild: `python r46_review_figure_pdfs.py --tag {tag} && python r47_build_review_package.py --tag {tag}`",
              "(from `article_1_revision/`). Figure files for Figma: `../../figures_svg/` (10 px text, frame-fitted;",
              "check `python r97_figma_check.py`)."]
    (package / "README.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
