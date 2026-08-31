#!/usr/bin/env python
"""Rebuild `supplementary_260802/Supplementary File 2.xlsx` with the two moved tables.

Main-manuscript Tables 3 (harmonization methods) and 4 (metric groups) are moved out of the
article and become two extra sheets of Supplementary File 2:

    Genes_per_sample   (unchanged)
    Metric_polarity    (unchanged)
    Table_S1_methods   <- former main Table 3
    Table_S2_metrics   <- former main Table 4

Numerical citations such as "(20)" are replaced by the **full bibliographic reference**,
read out of the manuscript's own reference list, so each sheet stands on its own.

Two structural facts about the source tables
--------------------------------------------
Both carry horizontally merged cells, so rows have different `w:tc` counts and
`python-docx`'s `row.cells` cannot be trusted (it silently repeats merged content):

* Table 3 — the header and 2 of the 39 data rows have 10 cells; the other 37 have 9, because
  the Version cell spans the Reference column. The old, largely empty `Reference` column is
  dropped here; the newer `Reference (citation)` column is the one that is resolved.
* Table 4 — the header and 1 of the 19 data rows have 6 cells; the other 18 have 5, because
  the `Source` cell spans `Full citation`. Where the row was split, the two are rejoined.

Cell text is read at *accept-all*: `w:ins` kept, `w:del` dropped, so the sheets carry the
corrected wording from the tracked-change passes.

Usage:
    source ~/venvs/collagen_3_11/bin/activate
    python build_supp_file2_260802.py
"""
from __future__ import annotations

import re
from pathlib import Path

import docx
import pandas as pd

HERE = Path(__file__).resolve().parent
SRC_DOCX = HERE.parent / "FL_manuscript_versions" / "FL_harmonization_article_NAR_260802.docx"
SUPP_DIR = HERE.parent / "supplementary_260802"
WORKBOOK = SUPP_DIR / "Supplementary File 2.xlsx"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

TABLE3_INDEX = 2  # harmonization methods
TABLE4_INDEX = 3  # metric groups

TABLE3_COLUMNS = [
    "Method name", "Method harshness", "Method full name", "Implementation done",
    "Implementation failure reason", "Version", "Parameters used",
    "Harshness justification", "Reference",
]
TABLE4_COLUMNS = [
    "Metric name", "Metric type", "Metric group", "Method definition", "Source",
]

# Citation markers that are not numeric and need no lookup.
NOT_A_CITATION = {"-", "", "—"}


def accepted_text(el) -> str:
    """Text of an element at accept-all: keep w:ins content, drop everything under w:del."""
    parts = []
    for t in el.iter(f"{W}t"):
        anc = t.getparent()
        while anc is not None:
            if anc.tag == f"{W}del":
                break
            anc = anc.getparent()
        else:
            parts.append(t.text or "")
    return " ".join("".join(parts).split())


def read_bibliography(body) -> dict[int, str]:
    """Parse the manuscript's reference list into {number: full entry}.

    The list lives in one structured-document tag as a single run of text, so entries are
    located by scanning for "1. ", "2. " ... in order rather than by splitting on a pattern
    — entry text itself contains "N. " sequences (initials, volume numbers).
    """
    biblio = max(
        (accepted_text(sdt) for sdt in body.iter(f"{W}sdt")),
        key=len,
        default="",
    )
    if len(biblio) < 5000:
        raise SystemExit("bibliography sdt not found")
    starts, pos = {}, 0
    n = 1
    while True:
        i = biblio.find(f"{n}. ", pos)
        if i < 0:
            break
        starts[n] = i
        pos = i + len(f"{n}. ")
        n += 1
    entries = {}
    ordered = sorted(starts.items(), key=lambda kv: kv[1])
    for idx, (num, start) in enumerate(ordered):
        end = ordered[idx + 1][1] if idx + 1 < len(ordered) else len(biblio)
        entries[num] = biblio[start + len(f"{num}. "):end].strip()
    return entries


def resolve_citation(value: str, refs: dict[int, str]) -> str:
    """Turn "(20)" into the full reference; pass anything else through unchanged.

    A cell that already carries a written-out reference (two of them do) is kept as it
    stands, and any trailing "[reference list entry N]" marker is expanded in place.
    """
    value = value.strip()
    if value in NOT_A_CITATION:
        return ""
    numeric = re.fullmatch(r"\(?(\d+)\)?", value)
    if numeric:
        num = int(numeric.group(1))
        if num not in refs:
            raise SystemExit(f"citation ({num}) is not in the reference list")
        return refs[num]
    # "... [reference list entry 57]" -> the full entry, so the sheet is self-contained.
    marker = re.search(r"\[reference list entry (\d+)\]", value)
    if marker:
        num = int(marker.group(1))
        if num not in refs:
            return value
        head = value[:marker.start()].strip()
        # Some cells attribute the metric to this study and only then name the source it
        # follows ("This study (custom implementation); ... formulation after Keyes,T.J. ...").
        # Keep that lead-in and swap only the abbreviated citation for the full entry.
        lead = re.match(r"(?P<lead>This study\b.*?\bafter\s)", head, re.S)
        return (lead.group("lead") + refs[num]) if lead else refs[num]
    return value


def table_rows(tbl) -> list[list[str]]:
    return [
        [accepted_text(tc) for tc in tr.findall(f"{W}tc")]
        for tr in tbl.findall(f"{W}tr")
    ]


def build_table3(rows, refs) -> pd.DataFrame:
    """Normalise the ragged method table and resolve its citations."""
    out = []
    for row in rows[1:]:
        if len(row) == 10:
            # name, harshness, full name, done, failure, version, OLD reference,
            # parameters, justification, citation
            name, harsh, full, done, fail, version, _old, params, just, cite = row
        elif len(row) == 9:
            name, harsh, full, done, fail, version, params, just, cite = row
        else:
            raise SystemExit(f"unexpected row width {len(row)} in Table 3: {row[0]!r}")
        out.append([
            name, harsh, full, done, fail or "-", version or "-",
            params, just, resolve_citation(cite, refs) or "-",
        ])
    df = pd.DataFrame(out, columns=TABLE3_COLUMNS)
    if len(df) != 39:
        raise SystemExit(f"expected 39 methods, got {len(df)}")
    return df


def build_table4(rows, refs) -> pd.DataFrame:
    """Normalise the ragged metric table; rejoin the split Source/Full citation column."""
    out = []
    for row in rows[1:]:
        if len(row) == 6:
            name, mtype, group, definition, source, full = row
            source = resolve_citation(full or source, refs)
        elif len(row) == 5:
            name, mtype, group, definition, source = row
            source = resolve_citation(source, refs)
        else:
            raise SystemExit(f"unexpected row width {len(row)} in Table 4: {row[0]!r}")
        out.append([name, mtype, group, definition, source])
    df = pd.DataFrame(out, columns=TABLE4_COLUMNS)
    if len(df) != 19:
        raise SystemExit(f"expected 19 metric rows, got {len(df)}")
    return df


def autosize(writer, sheet_name, df, wide_cols=()):
    """Give the sheet usable column widths and wrap the long prose columns."""
    ws = writer.sheets[sheet_name]
    wrap = writer.book.add_format({"text_wrap": True, "valign": "top"})
    header = writer.book.add_format({"bold": True, "valign": "top", "text_wrap": True})
    for col_idx, col in enumerate(df.columns):
        ws.write(0, col_idx, col, header)
        if col in wide_cols:
            ws.set_column(col_idx, col_idx, 60, wrap)
        else:
            longest = max([len(str(col))] + [len(str(v)) for v in df[col]])
            ws.set_column(col_idx, col_idx, min(max(longest + 2, 10), 32), wrap)
    ws.freeze_panes(1, 1)


def main():
    doc = docx.Document(SRC_DOCX)
    body = doc.element.body
    tables = [ch for ch in body if ch.tag == f"{W}tbl"]
    refs = read_bibliography(body)
    print(f"reference list: {len(refs)} entries")

    t3 = build_table3(table_rows(tables[TABLE3_INDEX]), refs)
    t4 = build_table4(table_rows(tables[TABLE4_INDEX]), refs)
    resolved = int((t3["Reference"].str.len() > 40).sum())
    print(f"Table S1 (methods): {t3.shape}; full references for "
          f"{resolved} of {len(t3)} methods (01_raw has none by design)")
    print(f"Table S2 (metrics): {t4.shape}")

    # The workbook is rewritten in place, so a re-run must not treat the sheets this script
    # adds as pre-existing data sheets to be copied forward.
    generated = {"Table_S1_methods", "Table_S2_metrics"}
    existing = {
        name: df for name, df in pd.read_excel(WORKBOOK, sheet_name=None).items()
        if name not in generated
    }
    print(f"data sheets carried forward: {list(existing)}")

    with pd.ExcelWriter(WORKBOOK, engine="xlsxwriter") as writer:
        for name, df in existing.items():
            df.to_excel(writer, sheet_name=name, index=False)
            autosize(writer, name, df)
        t3.to_excel(writer, sheet_name="Table_S1_methods", index=False)
        autosize(writer, "Table_S1_methods", t3,
                 wide_cols=("Method full name", "Implementation failure reason",
                            "Parameters used", "Harshness justification", "Reference"))
        t4.to_excel(writer, sheet_name="Table_S2_metrics", index=False)
        autosize(writer, "Table_S2_metrics", t4,
                 wide_cols=("Method definition", "Source"))

    size = WORKBOOK.stat().st_size / 1e6
    print(f"wrote {WORKBOOK} ({size:.2f} MB) with sheets "
          f"{list(existing) + ['Table_S1_methods', 'Table_S2_metrics']}")


if __name__ == "__main__":
    main()
