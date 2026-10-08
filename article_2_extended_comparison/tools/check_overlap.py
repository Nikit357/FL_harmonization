#!/usr/bin/env python3
"""Verbatim-overlap gate: no 8-gram of Article 2 may appear in Article 1 or the source document.

Plan §2.1 rule 3 and §8.5. Every n-gram of the draft is checked against the reference
documents; any hit is a defect and exits non-zero. The offending span is printed with the
name of every source it was found in and the surrounding sentence from the first of them, so
the writer can see what was reused and reword it.

Usage:
    python3 tools/check_overlap.py manuscript/*.md
    python3 tools/check_overlap.py DRAFT.md --against A.docx --against B.docx --ngram 8
                                   [--allow tools/overlap_allow.txt] [--json OUT.json]

Exit codes: 0 = no unallowed overlap, 1 = at least one hit, 2 = a source could not be read.

With no --against, the two documents of §2.1 are used: Article 1's NAR manuscript and the
extended source document.

Tracked changes: a .docx is read in its accept-all form. Inserted text lives in `w:t` like
any other run and is included; deleted text lives in `w:delText` and is skipped, because it
is not in the document a reader receives.

The allow-list exists for text F1000 requires to be identical to Article 1's: the grant
wording of §1.10 is quoted verbatim on Daniil's instruction, and flagging it every run would
train the reader to ignore the gate.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

REPO = Path(__file__).resolve().parent.parent
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

DEFAULT_AGAINST = [
    REPO.parent / "figures_for_article" / "FL_manuscript_versions"
    / "FL_harmonization_article_NAR_260912.docx",
    REPO / "manuscript_versions" / "Harmonization_metrics_extended_260802_v2.docx",
]
DEFAULT_ALLOW = REPO / "tools" / "overlap_allow.txt"


def docx_text(path: Path) -> str:
    """Paragraph text of a .docx with all tracked changes accepted."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    paras = []
    for p in root.iter(f"{W}p"):
        paras.append("".join(t.text or "" for t in p.iter(f"{W}t")))
    return "\n".join(paras)


def read_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        return docx_text(path)
    return path.read_text(errors="ignore")


def normalize(text: str) -> list[str]:
    """Word tokens, case- and punctuation-insensitive.

    Markdown syntax, citation markers and numbers are dropped before tokenizing: an 8-gram
    that differs only in a figure number is the same borrowed sentence, and one that differs
    only in `**bold**` is the same sentence too.
    """
    text = re.sub(r"```.*?```", " ", text, flags=re.S)          # fenced code
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)        # links -> label
    text = re.sub(r"https?://\S+", " ", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return text.split()


def ngrams(tokens: list[str], n: int):
    for i in range(len(tokens) - n + 1):
        yield i, " ".join(tokens[i:i + n])


def load_allow(path: Path, n: int) -> set[str]:
    """Allowed n-grams, taken over blocks of consecutive lines.

    A block is a run of non-comment, non-blank lines, joined before tokenizing. Taking
    n-grams line by line would leave the window that straddles two lines unallowed, and the
    grant statement is two sentences on two lines: the gate would flag "...lymphoma research
    this work was funded by..." on every run even though both sentences are exempt.
    """
    if not path.exists():
        return set()
    out: set[str] = set()
    block: list[str] = []

    def flush():
        if block:
            out.update(g for _, g in ngrams(normalize(" ".join(block)), n))
            block.clear()

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            flush()
            continue
        block.append(line)
    flush()
    return out


def merge_spans(hits: list[tuple[int, str, list[str]]], n: int):
    """Collapse the run of overlapping n-gram hits that one borrowed sentence produces."""
    merged = []
    for i, gram, srcs in hits:
        if merged and i <= merged[-1]["end"]:
            merged[-1]["end"] = i + n
            merged[-1]["sources"] = sorted(set(merged[-1]["sources"]) | set(srcs))
        else:
            merged.append({"start": i, "end": i + n, "sources": sorted(srcs)})
    return merged


def check(draft: Path, against: list[Path], n: int, allow: set[str]):
    tokens = normalize(draft.read_text())
    sources = {}
    for p in against:
        toks = normalize(read_text(p))
        sources[p.name] = (set(g for _, g in ngrams(toks, n)), toks)

    hits, allowed = [], 0
    for i, gram in ngrams(tokens, n):
        where = [name for name, (grams, _) in sources.items() if gram in grams]
        if not where:
            continue
        if gram in allow:
            allowed += 1
            continue
        hits.append((i, gram, where))

    spans = merge_spans(hits, n)
    for s in spans:
        s["span"] = " ".join(tokens[s["start"]:s["end"]])
    return {
        "draft": str(draft),
        "ngram": n,
        "draft_tokens": len(tokens),
        "sources": sorted(sources),
        "allowed_hits": allowed,
        "spans": spans,
        "verdict": "CLEAN" if not spans else "OVERLAP",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("drafts", nargs="+")
    ap.add_argument("--against", action="append", default=[],
                    help="reference document (.docx or .md). Repeatable. "
                         "Default: Article 1 and the extended source document.")
    ap.add_argument("--ngram", type=int, default=8)
    ap.add_argument("--allow", default=str(DEFAULT_ALLOW),
                    help="file of phrases that are allowed to be identical (grant wording)")
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    against = [Path(a) for a in args.against] or list(DEFAULT_AGAINST)
    missing = [str(p) for p in against if not p.exists()]
    if missing:
        print("ERROR: reference document not found:\n  " + "\n  ".join(missing), file=sys.stderr)
        return 2

    allow = load_allow(Path(args.allow), args.ngram)
    results, failed = [], 0
    for d in args.drafts:
        path = Path(d)
        if not path.exists():
            print(f"ERROR: no such file: {path}", file=sys.stderr)
            return 2
        r = check(path, against, args.ngram, allow)
        results.append(r)

        print(f"{path.name}  ({r['draft_tokens']} tokens, {args.ngram}-grams vs "
              f"{len(r['sources'])} source(s))")
        if r["allowed_hits"] and not args.quiet:
            print(f"  {r['allowed_hits']} allow-listed n-gram hit(s) ignored")
        if not r["spans"]:
            print("  ✓ no verbatim overlap\n")
            continue
        failed += 1
        print(f"  ✗ {len(r['spans'])} overlapping span(s):")
        for s in r["spans"]:
            print(f"    [{', '.join(s['sources'])}] …{s['span']}…")
        print()

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(results, indent=2))
        print(f"wrote {args.json_out}")

    if failed:
        print(f"FAIL: verbatim overlap in {failed} file(s).")
        return 1
    print("OK: no verbatim overlap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
