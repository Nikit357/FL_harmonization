#!/usr/bin/env python3
"""Audit every number in the Article 2 manuscript against the tables it came from.

For each numeric token in the manuscript .md, search the Article 2 result tables
(`tables/A2_T*.csv`), the workflow evidence JSON and any sibling `.md` for the same value.
A number that appears nowhere is a BLOCKER: it was invented, mistyped, or carried over from
an older draft.

Usage:
    python3 tools/audit_numbers.py <manuscript.md> [--tables tables/] [--folder DIR]
                                   [--evidence FILE.json] [--quiet] [--json OUT.json]

Exit codes: 0 = every number sourced, 1 = at least one unsourced number.

The audit is generous about *form* and strict about *presence*: "0.928", "92.8%", "1,349"
and "1349" all match their evidence spellings, but a value that simply is not in the sources
fails no matter how plausible it looks.

Retargeted from the AACR proposal audit. One change matters. The AACR evidence was prose,
where a quoted number is written the way the proposal writes it; the Article 2 evidence is
CSV, where the same quantity is stored at full float precision. A manuscript that reports
median F1 0.745 is quoting 0.7453118..., and a literal search finds nothing. CSV sources are
therefore parsed into numeric values and indexed at every rounding from 0 to ROUND_MAX
decimal places, so a correctly rounded quotation matches and a wrong one still fails.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Numbers that carry no evidentiary weight — dates, small counts used as prose, and the
# metric-group / figure numbering the manuscript uses as labels.
STOPWORDS = {
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
    "2021", "2022", "2023", "2024", "2025", "2026", "2027",
    "0", "100",
}
# The comma-grouped alternative carries an optional decimal part. Without it "555,004.7"
# tokenized as "555,004" and "1,359.6" as "1,359", so a comma-grouped decimal was audited as a
# different number -- which fails honestly against the tables and, worse, can pass against an
# unrelated integer: 1,359.6 matched the fold count 1,359 in A2_T8 by coincidence.
NUM_RE = re.compile(
    r"(?<![\w.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d+)\s*(%|×|x|-fold)?", re.I)

# A number that is a label, not a measurement: "Figure 12", "Supplementary Figure 11",
# "Table 3", "§1.5", "Results §7". Auditing these against the tables is meaningless and
# every one of them would fail.
LABEL_BEFORE = re.compile(
    r"(?:figure|fig\.?|table|supplementary\s+figure|supplementary\s+file|extended\s+figure"
    r"|section|§|panel|phase|group|step)\s*$", re.I)

CONTEXT = 60
ROUND_MAX = 4


def variants(tok: str):
    """Spellings of the same value that should count as a match."""
    out = {tok}
    bare = tok.replace(",", "")
    out.add(bare)
    if bare.isdigit() and len(bare) > 3:                    # 1349 -> 1,349
        out.add(f"{int(bare):,}")
    if "." in bare:
        stripped = bare.rstrip("0").rstrip(".")
        out.add(stripped)
        try:                                                # 0.928 -> 92.8
            f = float(bare)
            if 0 < f < 1:
                pct = f"{f * 100:g}"
                out.add(pct)
                out.add(f"{f * 100:.1f}".rstrip("0").rstrip("."))
        except ValueError:
            pass
    else:                                                   # 96 -> 0.96
        try:
            i = int(bare)
            if 0 < i <= 100:
                out.add(f"0.{i:02d}".rstrip("0"))
                out.add(f"{i / 100:g}")
        except ValueError:
            pass
    return {v for v in out if v}


def occurs(value: str, blob: str) -> bool:
    """True if `value` appears in `blob` as a whole number.

    Substring matching is what makes a numeric audit useless: plain `"96" in blob`
    is satisfied by 96.84, 1996 and image96.png. Require that no digit or decimal
    point sits directly on either side.
    """
    return re.search(r"(?<![\d.])" + re.escape(value) + r"(?![\d.])", blob) is not None


def numeric_index(blob: str) -> set[str]:
    """Every value in a CSV blob, at every rounding a manuscript might quote it at.

    0.7453118 is indexed as 0.7453, 0.745, 0.75, 0.7 and 1, plus the percentage forms, so
    "median F1 0.745" resolves to the stored value and "0.746" does not.
    """
    idx: set[str] = set()
    for m in re.finditer(r"(?<![\w.])-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", blob):
        try:
            v = float(m.group(0))
        except ValueError:
            continue
        for n in range(ROUND_MAX + 1):
            s = f"{v:.{n}f}"
            idx.add(s)
            if "." in s:
                idx.add(s.rstrip("0").rstrip("."))
        if abs(v) >= 1000 and v == int(v):
            idx.add(f"{int(v):,}")
        if 0 < abs(v) < 1:                                   # 0.745 -> 74.5, 74.53
            for n in range(ROUND_MAX + 1):
                p = f"{v * 100:.{n}f}"
                idx.add(p)
                if "." in p:
                    idx.add(p.rstrip("0").rstrip("."))
    return idx


def load_sources(tables: Path | None, folder: Path, evidence: Path | None, manuscript: Path):
    """Return {name: ('text'|'numeric', blob_or_index)}."""
    sources: dict[str, tuple[str, object]] = {}
    if tables and tables.exists():
        for p in sorted(tables.glob("A2_T*.csv")):
            sources[p.name] = ("numeric", numeric_index(p.read_text(errors="ignore")))
    for p in sorted(folder.glob("*.md")):
        if p.resolve() == manuscript.resolve() or p.name == "CLAUDE.md":
            continue
        sources[p.name] = ("text", p.read_text(errors="ignore"))
    if evidence and evidence.exists():
        sources[evidence.name] = ("text", evidence.read_text(errors="ignore"))
    return sources


def matches(cands: set[str], kind: str, blob) -> bool:
    if kind == "numeric":
        return bool(cands & blob)
    return any(occurs(v, blob) for v in cands)


def audit(manuscript: Path, tables: Path | None, folder: Path, evidence: Path | None):
    text = manuscript.read_text()
    # Drop sections that are not manuscript claims: the reference list (whose years, volumes
    # and page numbers are not assertions), the provenance table, URLs, DOIs and PMIDs.
    body = re.split(r"\n#{1,6}\s*References", text)[0]
    body = re.split(r"\n#{1,6}\s*Provenance", body)[0]
    body = re.split(r"\n#{1,6}\s*Comments in document", body)[0]
    body = re.sub(r"\]\([^)]*\)", "]", body)          # markdown link targets
    body = re.sub(r"https?://\S+", " ", body)          # bare URLs
    body = re.sub(r"\b10\.\d{4,}/\S+", " ", body)     # DOIs
    body = re.sub(r"PMID:?\s*\d+", " ", body)         # PMIDs
    # Affiliation addresses, for the same reason as the reference list: a postal code is not a
    # measurement. Without this, "Waltham, MA, 02453, USA" is audited as an unsourced number and
    # no table can ever resolve it. Matches the superscript-marked affiliation lines that F1000
    # puts between the author list and the abstract.
    body = re.sub(r"(?m)^\^\d+\^[^\n]*$", " ", body)
    sources = load_sources(tables, folder, evidence, manuscript)

    seen, rows = set(), []
    for m in NUM_RE.finditer(body):
        tok = m.group(1)
        if tok in STOPWORDS or tok in seen:
            continue
        if LABEL_BEFORE.search(body[max(0, m.start() - 30): m.start()]):
            continue
        seen.add(tok)
        start = max(0, m.start() - CONTEXT)
        ctx = " ".join(body[start:m.end() + CONTEXT].split())
        cands = variants(tok)
        hits = [name for name, (kind, blob) in sources.items() if matches(cands, kind, blob)]
        rows.append({
            "number": tok,
            "context": ctx,
            "found_in": hits,
            "verdict": "SOURCED" if hits else "UNSOURCED",
        })
    return rows, sources


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manuscript")
    ap.add_argument("--tables", default=str(REPO / "tables"),
                    help="folder holding A2_T*.csv (default: tables/)")
    ap.add_argument("--folder", help="folder holding the .md sources (default: the manuscript's own folder)")
    ap.add_argument("--evidence", help="evidence JSON from the workflow run, e.g. 01_numbers.json")
    ap.add_argument("--extra", action="append", default=[],
                    help="additional source file(s). Repeatable. Use for meta-numbers "
                         "(word limits, journal caps) that are not study data.")
    ap.add_argument("--quiet", action="store_true", help="print only unsourced numbers")
    ap.add_argument("--json", dest="json_out", help="write the full result as JSON")
    args = ap.parse_args()

    manuscript = Path(args.manuscript)
    if not manuscript.exists():
        print(f"ERROR: no such file: {manuscript}", file=sys.stderr)
        return 2
    folder = Path(args.folder) if args.folder else manuscript.parent
    tables = Path(args.tables) if args.tables else None
    evidence = Path(args.evidence) if args.evidence else None

    rows, sources = audit(manuscript, tables, folder, evidence)
    for x in args.extra:
        xp = Path(x)
        if xp.exists():
            kind = "numeric" if xp.suffix == ".csv" else "text"
            blob = numeric_index(xp.read_text(errors="ignore")) if kind == "numeric" \
                else xp.read_text(errors="ignore")
            sources[xp.name] = (kind, blob)
            for r in rows:
                if r["verdict"] == "UNSOURCED" and matches(variants(r["number"]), kind, blob):
                    r["found_in"].append(xp.name); r["verdict"] = "SOURCED"
    bad = [r for r in rows if r["verdict"] == "UNSOURCED"]

    n_tab = sum(1 for k, (kind, _) in sources.items() if kind == "numeric")
    print(f"{manuscript.name}")
    print(f"  checked against {len(sources)} source(s): {n_tab} table(s) in {tables}/, "
          f"{len(sources) - n_tab} text file(s)")
    print(f"  {len(rows)} distinct numbers · {len(rows) - len(bad)} sourced · {len(bad)} UNSOURCED\n")

    show = bad if args.quiet else rows
    for r in show:
        mark = "✗" if r["verdict"] == "UNSOURCED" else "✓"
        where = ", ".join(s[:38] for s in r["found_in"][:2]) or "—"
        print(f"  {mark} {r['number']:>9}  {where}")
        print(f"              …{r['context']}…")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"manuscript": str(manuscript), "sources": sorted(sources), "rows": rows}, indent=2))
        print(f"\n  wrote {args.json_out}")

    if bad:
        print(f"\nFAIL: {len(bad)} number(s) not found in any evidence file.")
        return 1
    print("\nOK: every number traced to an evidence file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
