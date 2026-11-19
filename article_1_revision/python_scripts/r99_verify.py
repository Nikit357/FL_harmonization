"""
r99_verify.py — final validation of the revised manuscript package (plan WP14).

Checks (each prints PASS / FAIL / SKIP / REVIEW; exit code 1 on any FAIL):

 1. frozen files      every MD5 of FROZEN_MD5.txt still matches (frozen code, baseline
                      docx, approved selection rule)
 2. reject-all        the Reject-All text of the tracked docx equals the baseline text
 3. citations         w:sdt count and contents (w:t + w:delText) unchanged; hyperlinks
 4. revision markup   no w:t inside w:del, no w:delText outside w:del
 5. revision ids      every w:ins / w:del / *Change id unique
 6. abstract          Accept-All abstract ≤ 200 words
 7. numbers           every entry of output/numbers.json present in the text (SKIP when
                      the file does not exist yet; FAIL only for entries marked
                      "in_text": true, REVIEW for the others)
 8. supp. figures     "Supplementary Figure n" cited with n ≤ 18 only, every legend
                      S1–S18 present, first citations in increasing order
 9. alt text          an "Alt text:" paragraph right after every main-figure legend
                      (supplementary legends: counted, REVIEW)
10. internal labels   plan §1.1 scan of the Accept-All docx text, response_letter_draft.md,
                      sheet names / column headers of the revised supplementary files in
                      Revised_manuscript/, and the text elements of every SVG in
                      figures_svg/: FAIL tokens fail, ambiguous tokens are listed (REVIEW)

Report: output/wp14/verify_report.md

Usage
-----
python r99_verify.py Revised_manuscript/<tracked>.docx
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

import revision_lib as rl

MANUSCRIPT_DIR = rl.REVISION_DIR / "Revised_manuscript"
BASELINE_DOCX = MANUSCRIPT_DIR / "FL_harmonization_article_NARGAB_baseline_260912.docx"
FROZEN_MD5_PATH = rl.REVISION_DIR / "FROZEN_MD5.txt"
NUMBERS_PATH = rl.OUTPUT_DIR / "numbers.json"
LETTER_DRAFT = rl.REVISION_DIR / "response_letter_draft.md"
SVG_DIR = rl.REVISION_DIR / "figures_svg"
REPORT_PATH = rl.OUTPUT_DIR / "wp14" / "verify_report.md"

N_SUPP_FIGURES = 18
ABSTRACT_WORD_LIMIT = 200
W = f"{{{rl.W_NS}}}"
REVISION_TAGS = ("ins", "del", "rPrChange", "pPrChange", "moveFrom", "moveTo")

# Plan §1.1: tokens that are never legitimate in a publication document …
FAIL_PATTERNS: dict[str, str] = {
    "work package": r"\bWP\d+\b",
    "covariate-free arm code": r"_nocov\b",
    "rule_front": r"\brule_front\b",
    "visual_best": r"\bvisual_best\b",
    "bridging_biology": r"\bbridging_biology\b",
    "single_dx": r"single_dx",
    "L11 design code": r"\bL11\b",
    "V1 validation code": r"\bV1\b",
    "post0 / post1": r"\bpost[01]\b",
    "four_score": r"four_score",
    "reviewer-comment code": r"\bR[12]\.\d",
    "script name": r"\b(?:r|nb)\d\d_\w+",
}
# … and tokens that can be fine in biology text (G0 / G1 phases, CD markers …).
REVIEW_PATTERNS: dict[str, str] = {
    "D-code": r"\bD\d\b",
    "G-code": r"\bG\d\b",
    "C-code": r"\bC\d+\b",
}
# Not scanned: the strategy codes S0, A–K (incl. E1–E3). They are publication notation since
# Daniil's decision of 2026-11-08 (gates_review §10.6 A; plan §1.1 exception).


class Report:
    """Collects check lines, prints them and writes the markdown report."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.n_fail = 0

    def add(self, check: str, status: str, detail: str = "") -> None:
        """Record one check result."""
        self.n_fail += status == "FAIL"
        line = f"[{status:6s}] {check}" + (f" — {detail}" if detail else "")
        print(line)
        self.lines.append(f"- **{status}** {check}" + (f": {detail}" if detail else ""))

    def detail(self, text: str) -> None:
        """Extra indented detail lines (report only)."""
        self.lines.append(f"    - {text}")


# ── docx helpers ──────────────────────────────────────────────────────────────


def document_root(path: Path) -> etree._Element:
    """Parsed word/document.xml."""
    with zipfile.ZipFile(path) as archive:
        return etree.fromstring(archive.read("word/document.xml"))


def reject_all_text(root: etree._Element) -> str:
    """Concatenated Reject-All text (no paragraph separators)."""
    pieces = []
    for node in root.iter(f"{W}t", f"{W}delText"):
        inside_ins = any(a.tag == f"{W}ins" for a in node.iterancestors())
        if not inside_ins:
            pieces.append(node.text or "")
    return "".join(pieces)


def sdt_texts(root: etree._Element) -> list[str]:
    """Text (w:t + w:delText) of every w:sdt."""
    return [
        "".join(n.text or "" for n in sdt.iter(f"{W}t", f"{W}delText"))
        for sdt in root.iter(f"{W}sdt")
    ]


# ── checks ────────────────────────────────────────────────────────────────────


def check_frozen(report: Report) -> None:
    """1. MD5 of every frozen file."""
    bad = []
    lines = [l for l in FROZEN_MD5_PATH.read_text().splitlines() if l.strip()]
    for line in lines:
        digest, name = line.split(maxsplit=1)
        path = (rl.REVISION_DIR / name.strip().lstrip("*")).resolve()
        if not path.exists():
            bad.append(f"{name} missing")
        elif hashlib.md5(path.read_bytes()).hexdigest() != digest:
            bad.append(f"{name} changed")
    report.add(
        "frozen files",
        "FAIL" if bad else "PASS",
        f"{len(lines) - len(bad)} / {len(lines)} match",
    )
    for item in bad:
        report.detail(item)


def check_docx_integrity(report: Report, tracked: Path) -> None:
    """2–6. Reject-all, citations, revision markup, ids, abstract."""
    base_root, root = document_root(BASELINE_DOCX), document_root(tracked)
    base_text, rejected = reject_all_text(base_root), reject_all_text(root)
    if base_text == rejected:
        report.add("reject-all text == baseline", "PASS")
    else:
        i = next(
            (k for k, (a, b) in enumerate(zip(base_text, rejected)) if a != b),
            min(len(base_text), len(rejected)),
        )
        report.add(
            "reject-all text == baseline",
            "FAIL",
            f"first difference at char {i}: {rejected[max(0, i - 40):i + 40]!r}",
        )

    base_sdt, sdt = sdt_texts(base_root), sdt_texts(root)
    links = [len(list(r.iter(f"{W}hyperlink"))) for r in (base_root, root)]
    same = base_sdt == sdt and links[0] == links[1]
    report.add(
        "citations (w:sdt) unchanged",
        "PASS" if same else "FAIL",
        f"sdt {len(sdt)} (baseline {len(base_sdt)}), hyperlinks {links[1]} "
        f"(baseline {links[0]})",
    )

    t_in_del = sum(len(list(d.iter(f"{W}t"))) for d in root.iter(f"{W}del"))
    stray = sum(
        1
        for n in root.iter(f"{W}delText")
        if not any(a.tag == f"{W}del" for a in n.iterancestors())
    )
    report.add(
        "revision markup",
        "FAIL" if t_in_del or stray else "PASS",
        f"w:t inside w:del {t_in_del}; w:delText outside w:del {stray}",
    )

    ids = [
        node.get(f"{W}id")
        for tag in REVISION_TAGS
        for node in root.iter(f"{W}{tag}")
        if node.get(f"{W}id") is not None
    ]
    duplicates = len(ids) - len(set(ids))
    report.add(
        "unique revision ids",
        "FAIL" if duplicates else "PASS",
        f"{len(ids)} revisions, {duplicates} duplicate ids",
    )

    paragraphs = rl.docx_paragraphs(tracked, view="accept")
    texts = [p["text"].strip() for p in paragraphs]
    if "ABSTRACT" in [t.upper() for t in texts]:
        start = [t.upper() for t in texts].index("ABSTRACT")
        abstract = next(t for t in texts[start + 1 :] if t)
        n_words = len(abstract.split())
        report.add(
            "abstract length",
            "FAIL" if n_words > ABSTRACT_WORD_LIMIT else "PASS",
            f"{n_words} words (limit {ABSTRACT_WORD_LIMIT})",
        )
    else:
        report.add("abstract length", "FAIL", "no ABSTRACT heading found")


def number_variants(value: object) -> list[str]:
    """Spellings of a number as it may appear in the text (1234 → '1,234', '1234')."""
    if isinstance(value, bool):
        return [str(value)]
    if isinstance(value, int):
        return [f"{value:,}", str(value)]
    if isinstance(value, float):
        return [str(value), f"{value:,}"]
    return [str(value)]


def check_numbers(report: Report, accept_text: str) -> None:
    """7. Every number of numbers.json appears in the text."""
    if not NUMBERS_PATH.exists():
        report.add(
            "numbers.json in text", "SKIP", "output/numbers.json not written yet"
        )
        return
    numbers = json.loads(NUMBERS_PATH.read_text())
    missing_required, missing_other = [], []
    for key, entry in numbers.items():
        value = (
            entry.get("text", entry.get("value")) if isinstance(entry, dict) else entry
        )
        required = isinstance(entry, dict) and entry.get("in_text", False)
        if not any(v in accept_text for v in number_variants(value)):
            (missing_required if required else missing_other).append(f"{key} = {value}")
    status = "FAIL" if missing_required else ("REVIEW" if missing_other else "PASS")
    report.add(
        "numbers.json in text",
        status,
        f"{len(numbers)} entries; {len(missing_required)} required missing, "
        f"{len(missing_other)} other not found",
    )
    for item in missing_required + missing_other:
        report.detail(item)


SUPP_CITATION = re.compile(
    r"Supplementary Figures?\s+S?(\d+[A-Z]?(?:\s*(?:,|and|–|-|to)\s*S?\d+[A-Z]?)*)"
)


def cited_numbers(fragment: str) -> list[int]:
    """Figure numbers of one citation fragment ('2–4' → 2, 3, 4; '5 and 7' → 5, 7)."""
    numbers: list[int] = []
    for part in re.split(r"\s*(?:,|and)\s*", fragment):
        bounds = [int(x) for x in re.findall(r"\d+", part)]
        if len(bounds) == 2 and re.search(r"–|-|to", part):
            numbers += list(range(bounds[0], bounds[1] + 1))
        else:
            numbers += bounds
    return numbers


def check_supplementary_figures(report: Report, texts: list[str]) -> None:
    """8. Supplementary Figure numbering: ≤ 18, legends present, citation order."""
    legends = {
        int(m.group(1))
        for t in texts
        if (m := re.match(r"^Supplementary Figure S?(\d+)\b", t.strip()))
    }
    first_seen: list[int] = []
    for text in texts:
        if re.match(r"^Supplementary Figure S?\d+\b", text.strip()):
            continue  # legends of the supplementary data list are not citations
        for match in SUPP_CITATION.finditer(text):
            for n in cited_numbers(match.group(1)):
                if n not in first_seen:
                    first_seen.append(n)
    too_high = sorted(n for n in set(first_seen) | legends if n > N_SUPP_FIGURES)
    missing = sorted(set(range(1, N_SUPP_FIGURES + 1)) - legends)
    out_of_order = [(a, b) for a, b in zip(first_seen, first_seen[1:]) if b < a]
    problems = []
    if too_high:
        problems.append(f"numbers above {N_SUPP_FIGURES}: {too_high}")
    if missing:
        problems.append(f"legends missing: {missing}")
    if out_of_order:
        problems.append(f"first citations out of order: {out_of_order[:8]}")
    report.add(
        "supplementary figure numbering",
        "FAIL" if problems else "PASS",
        "; ".join(problems) or f"S1–S{N_SUPP_FIGURES} in citation order",
    )
    report.detail(f"first-citation order: {first_seen}")


def check_alt_text(report: Report, texts: list[str]) -> None:
    """9. 'Alt text:' after every main-figure legend; supplementary legends counted."""
    nonempty = [t.strip() for t in texts if t.strip()]
    main_missing, supp_without = [], 0
    for i, text in enumerate(nonempty):
        is_main = re.match(r"^Figure (\d+)\.", text)
        is_supp = re.match(r"^Supplementary Figure S?(\d+)\.", text)
        following = nonempty[i + 1] if i + 1 < len(nonempty) else ""
        has_alt = following.lower().startswith("alt text")
        if is_main and not has_alt:
            main_missing.append(is_main.group(1))
        if is_supp and not has_alt:
            supp_without += 1
    report.add(
        "alt text under main-figure legends",
        "FAIL" if main_missing else "PASS",
        f"missing for Figure(s) {main_missing}" if main_missing else "all present",
    )
    if supp_without:
        # Daniil 2026-11-08 (gates_review §9.4 B3, option b): the alt text of the
        # supplementary figures is in the supplementary PDF (r46), not under the legends.
        report.add(
            "alt text under supplementary legends",
            "PASS",
            f"{supp_without} supplementary legends without an 'Alt text:' paragraph; "
            "alt text is in the supplementary PDF (decision B3)",
        )


def svg_text(path: Path) -> str:
    """Text content of every <text> / <tspan> element of an SVG."""
    try:
        root = etree.parse(str(path)).getroot()
    except etree.XMLSyntaxError:
        return ""
    return "\n".join(
        "".join(node.itertext())
        for node in root.iter()
        if isinstance(node.tag, str) and node.tag.split("}")[-1] == "text"
    )


def supplementary_headers(path: Path) -> str:
    """Sheet names and column headers of a revised supplementary file."""
    import pandas as pd

    if path.suffix == ".xlsx":
        sheets = pd.read_excel(path, sheet_name=None, nrows=0)
        return "\n".join(
            [name for name in sheets] + [str(c) for f in sheets.values() for c in f]
        )
    if path.suffix in {".csv", ".gz", ".tsv"}:
        separator = "\t" if ".tsv" in path.name else ","
        return "\n".join(map(str, pd.read_csv(path, sep=separator, nrows=0).columns))
    return ""


def label_scan_sources(accept_text: str) -> dict[str, str]:
    """Every publication text to scan, by source name."""
    sources = {"manuscript (accept-all)": accept_text}
    if LETTER_DRAFT.exists():
        # The leading HTML comment is the editors' note (dropped by r60) and every
        # {{key}} becomes a number, so neither reaches the letter.
        letter = re.sub(r"^<!--.*?-->\s*", "", LETTER_DRAFT.read_text(), flags=re.S)
        sources[LETTER_DRAFT.name] = re.sub(r"\{\{[^}]+\}\}", "0", letter)
    for path in sorted(MANUSCRIPT_DIR.glob("*response_to_reviewers*.docx")):
        sources[path.name] = "\n".join(
            p["text"] for p in rl.docx_paragraphs(path, view="accept")
        )
    supplementary = [
        *MANUSCRIPT_DIR.glob("Supplementary File*"),
        *(rl.OUTPUT_DIR / "wp10").glob("Supplementary File*"),
    ]
    for path in sorted(supplementary):
        sources[str(path.relative_to(rl.REVISION_DIR))] = supplementary_headers(path)
    for path in sorted(SVG_DIR.rglob("*.svg")):
        sources[str(path.relative_to(rl.REVISION_DIR))] = svg_text(path)
    return sources


def check_internal_labels(report: Report, accept_text: str) -> None:
    """10. Plan §1.1 scan: FAIL tokens and ambiguous REVIEW tokens."""
    sources = label_scan_sources(accept_text)
    fails, reviews = [], []
    for source, text in sources.items():
        for name, pattern in FAIL_PATTERNS.items():
            for match in re.finditer(pattern, text):
                context = text[max(0, match.start() - 40) : match.end() + 40]
                fails.append(f"{source} · {name} · …{context.strip()!r}…")
        for name, pattern in REVIEW_PATTERNS.items():
            hits = re.findall(pattern, text)
            if hits:
                reviews.append(f"{source} · {name}: {len(hits)} × {sorted(set(hits))}")
    report.add(
        "internal labels (fail list)",
        "FAIL" if fails else "PASS",
        f"{len(fails)} hits in {len(sources)} sources",
    )
    for item in fails:
        report.detail(item)
    report.add(
        "internal labels (review list)",
        "REVIEW" if reviews else "PASS",
        f"{len(reviews)} source × token groups for Daniil to mark fine / to fix",
    )
    for item in reviews:
        report.detail(item)


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    """Run every check on one tracked docx."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("docx", help="tracked manuscript (.docx)")
    args = parser.parse_args()
    tracked = Path(args.docx)

    report = Report()
    print(f"verifying {tracked.name}")
    check_frozen(report)
    check_docx_integrity(report, tracked)
    texts = [p["text"] for p in rl.docx_paragraphs(tracked, view="accept")]
    accept_text = "\n".join(texts)
    check_numbers(report, accept_text)
    check_supplementary_figures(report, texts)
    check_alt_text(report, texts)
    check_internal_labels(report, accept_text)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    header = [
        f"# Verification report — {tracked.name}",
        "",
        "Generated by `r99_verify.py`. FAIL blocks submission; REVIEW is for Daniil.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(header + report.lines) + "\n")
    print(f"report → {REPORT_PATH}; {report.n_fail} FAIL")
    sys.exit(1 if report.n_fail else 0)


if __name__ == "__main__":
    main()
