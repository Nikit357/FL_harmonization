"""
r51_reference_audit.py — checklist of malformed bibliography entries (plan WP12;
Reviewer 1, minor comment 5).

The bibliography is ONE Mendeley content control (w:sdt) at the end of the docx; a
tracked edit inside it would be overwritten at the next refresh. This script therefore
only LISTS the problems; Daniil fixes them in Mendeley Desktop and refreshes the
bibliography, then runs the script again — it must report 0 items.

Checks per entry, on the author part (text before the year):
- all-caps tokens of ≥ 5 letters (e.g. "FABIANPEDREGOSA"; gene / consortium acronyms of
  ≤ 4 letters are not flagged);
- a URL or an e-mail address;
- the same author listed twice;
and on the whole entry: no year (1900–2099); no journal / source between the title and
the volume (heuristic: fewer than 3 sentence parts).

Usage
-----
python r51_reference_audit.py [docx]   # default: the baseline copy
Output: output/wp12/reference_audit.tsv (+ printed checklist). Exit code 1 if any item.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

import revision_lib as rl

DEFAULT_DOCX = (
    rl.REVISION_DIR
    / "Revised_manuscript"
    / "FL_harmonization_article_NARGAB_baseline_260912.docx"
)
YEAR = re.compile(r"\b(19|20)\d\d\b")


def bibliography_entries(docx_path: Path) -> list[str]:
    """Non-empty paragraphs after the last REFERENCES heading."""
    paragraphs = rl.docx_paragraphs(docx_path)
    start = max(
        i for i, p in enumerate(paragraphs) if p["text"].strip().upper() == "REFERENCES"
    )
    return [p["text"].strip() for p in paragraphs[start + 1 :] if p["text"].strip()]


def entry_problems(entry: str) -> list[str]:
    """Problems of one bibliography entry (empty list = fine)."""
    authors = entry.split(". ")[0]
    # publication year: before the Mendeley "[accessed …]" stamp, never inside it
    year = YEAR.search(entry.split("[accessed")[0])
    problems = []
    if re.match(r"^[a-z]", authors):
        problems.append(f"malformed author field: '{authors[:40]}'")
    if caps := re.findall(r"\b[A-Z]{5,}\b", authors):
        problems.append(f"all-caps author token(s): {', '.join(caps)}")
    if re.search(r"https?://|www\.|\S+@\S+", authors):
        problems.append("URL or e-mail address in the author field")
    names = [n.strip() for n in authors.rstrip(". ").split(",") if n.strip()]
    duplicated = sorted({n for n in names if names.count(n) > 1})
    if duplicated:
        problems.append(f"author listed twice: {', '.join(duplicated)}")
    if not year:
        problems.append("no year")
    elif len([part for part in entry[year.end() :].split(". ") if part.strip()]) < 3:
        problems.append("journal / source possibly missing")
    return problems


def main() -> None:
    """Print and save the checklist."""
    docx_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DOCX
    rows = [
        {"entry_number": i, "problem": problem, "entry_start": entry[:160]}
        for i, entry in enumerate(bibliography_entries(docx_path), start=1)
        for problem in entry_problems(entry)
    ]
    out = rl.OUTPUT_DIR / "wp12/reference_audit.tsv"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=["entry_number", "problem", "entry_start"]).to_csv(
        out, sep="\t", index=False
    )
    for row in rows:
        print(
            f"[{row['entry_number']:>3}] {row['problem']}\n      {row['entry_start']}"
        )
    print(f"{len(rows)} item(s) → {out}")
    sys.exit(1 if rows else 0)


if __name__ == "__main__":
    main()
