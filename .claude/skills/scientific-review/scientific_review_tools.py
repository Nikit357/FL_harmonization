#!/usr/bin/env python
"""scientific_review_tools.py — measurement CLI for the `scientific-review` skill.

Everything the skill asks you to check is measured by one of these subcommands, so raw
document bytes never have to enter the conversation. Nothing here writes to a .docx;
tracked-change editing goes through nar_review_tools.safe_tracked_replace.

    V=~/venvs/collagen_3_11/bin/python
    T=~/.claude/skills/scientific-review/scientific_review_tools.py

    $V $T extract MS.docx out.txt              # accept-all view (the object under review)
    $V $T extract MS.docx out0.txt --mode orig # reject-all view (must equal the original)
    $V $T diff a.txt b.txt                     # sentence-level: what argument changed
    $V $T diff a.txt b.txt --words             # word-level: spelling, citations, clauses
    $V $T numbering ms.txt                     # P3 sequential-numbering audit
    $V $T prose ms.txt                         # P1/P4/P6/P7/P9 language audit
    $V $T numbers ms.txt                       # P2/P5 untraceable-number audit
    $V $T citations MS.docx                    # Mendeley content-control inventory
    $V $T anchors MS.docx --anchor "..."       # is this edit anchor citation-safe?
    $V $T audit ms.txt                         # prose + numbering + numbers in one report

Requires: lxml (in ~/venvs/collagen_3_11).
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
import zipfile
from collections import Counter, OrderedDict

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


# --------------------------------------------------------------------------- extract

def _para_text(p, mode="final"):
    """Text of one <w:p>.

    mode='final' -> as if every tracked change were accepted (deletions dropped).
    mode='orig'  -> as if every tracked change were rejected (insertions dropped).
    """
    parts = []
    for node in p.iter():
        tag = node.tag
        if tag not in (W + "t", W + "delText", W + "tab", W + "br"):
            continue
        if tag == W + "tab":
            parts.append("\t")
            continue
        if tag == W + "br":
            parts.append(" ")
            continue
        # find the nearest revision ancestor below the paragraph
        rev = None
        anc = node.getparent()
        while anc is not None and anc.tag != W + "p":
            if anc.tag in (W + "del", W + "ins"):
                rev = anc.tag
                break
            anc = anc.getparent()
        if mode == "final":
            if rev == W + "del":
                continue
        else:
            if rev == W + "ins":
                continue
        parts.append(node.text or "")
    return "".join(parts)


def load_paragraphs(docx_path, mode="final"):
    from lxml import etree
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read("word/document.xml")
    root = etree.fromstring(xml)
    body = root.find(W + "body")
    out = []
    for p in body.iter(W + "p"):
        t = _para_text(p, mode).strip()
        if t:
            out.append(t)
    return out


def cmd_extract(args):
    paras = load_paragraphs(args.docx, args.mode)
    with open(args.out, "w") as f:
        f.write("\n".join(paras) + "\n")
    words = sum(len(p.split()) for p in paras)
    print(f"{args.docx}  mode={args.mode}")
    print(f"  {len(paras)} non-empty paragraphs, {words:,} words -> {args.out}")


# --------------------------------------------------------------------------- diff

_SENT = re.compile(r"(?<=[.:;])\s+(?=[A-Z0-9(])")


def _sentences(path):
    out = []
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        out.extend(s.strip() for s in _SENT.split(line) if s.strip())
    return out


def _words(path):
    return re.findall(r"\S+", open(path).read())


def cmd_diff(args):
    if args.words:
        a, b = _words(args.a), _words(args.b)
        ctx = 8
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        n = 0
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            n += 1
            if (i2 - i1) > args.max_block or (j2 - j1) > args.max_block:
                print(f"\n@@@ {tag.upper()} [large block {i2-i1} -> {j2-j1} words, skipped]")
                continue
            print(f"\n@@@ {tag.upper()}")
            print("  ctx< ..." + " ".join(a[max(0, i1 - ctx):i1]))
            print("  -    " + " ".join(a[i1:i2]))
            print("  +    " + " ".join(b[j1:j2]))
            print("  >ctx " + " ".join(a[i2:i2 + ctx]) + "...")
        print(f"\n{n} word-level edit sites")
    else:
        a, b = _sentences(args.a), _sentences(args.b)
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        n = 0
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            n += 1
            print(f"\n@@@ {tag.upper()}  a[{i1}:{i2}]  b[{j1}:{j2}]")
            for s in a[i1:i2]:
                print("  - " + s)
            for s in b[j1:j2]:
                print("  + " + s)
        print(f"\n{n} sentence-level edit sites")


# --------------------------------------------------------------------------- numbering (P3)

TOKEN = re.compile(
    r"\b("
    r"Supplementary Figure S?\d+[A-Z]?|Supplementary Table S?\d+|Supplementary File S?\d+|"
    r"Figure S\d+[A-Z]?|Fig\. S\d+[A-Z]?|Figure \d+[A-Z]?|Fig\. \d+[A-Z]?|"
    r"File S\d+|Table S\d+|Table \d+"
    r")\b"
)

# "Figures S11, S12 and S13A" / "Figures 4 and 5" / "Files S1-S3" elide the head noun on every
# item after the first. Expand them before scanning, or every elided item is invisible to the
# audit — which is exactly how an uncited supplementary figure hides.
_PLURAL_HEAD = re.compile(
    r"\b(Figures|Figs\.|Files|Tables)\s+(S?\d+[A-Z]?(?:\s*(?:,|and|&|-|–|to)\s*S?\d+[A-Z]?)+)",
    re.I,
)
_SINGULAR = {"figures": "Figure", "figs.": "Figure", "files": "File", "tables": "Table"}


def expand_elided(text):
    """Rewrite 'Figures S11, S12 and S13A' as three full tokens so TOKEN sees all of them.

    A range ('Figures 4-6') is expanded to its endpoints only; the audit cares about which
    objects are cited, and an endpoint pair is enough to place the range in the sequence.
    """
    def repl(m):
        head = _SINGULAR[m.group(1).lower()]
        items = re.findall(r"S?\d+[A-Z]?", m.group(2))
        # a File/Table series is written 'File S1'; a bare number keeps its own form
        return " and ".join(f"{head} {it}" for it in items)
    return _PLURAL_HEAD.sub(repl, text)
SERIES = re.compile(
    r"^(Supplementary Figure S?|Supplementary Table S?|Supplementary File S?|"
    r"Figure S|Fig\. S|Figure |Fig\. |File S|Table S|Table )(\d+)"
)
# a legend line starts with the object it describes and a full stop
LEGEND = re.compile(r"^(Supplementary )?(Figure|Fig\.|Table|File) ?S?\d+\s*[.:]")


def _series_of(tok):
    m = SERIES.match(tok)
    if not m:
        return None, None
    prefix = m.group(1).strip()
    # normalise the aliases onto one series name
    key = {
        "Supplementary Figure S": "Figure S", "Supplementary Figure": "Figure S",
        "Fig. S": "Figure S", "Figure S": "Figure S",
        "Fig.": "Figure", "Figure": "Figure",
        "Supplementary Table S": "Table S", "Supplementary Table": "Table S",
        "Table S": "Table S", "Table": "Table",
        "Supplementary File S": "File S", "Supplementary File": "File S",
        "File S": "File S",
    }.get(prefix, prefix)
    return key, int(m.group(2))


def cmd_numbering(args):
    lines = [l.rstrip("\n") for l in open(args.txt)]
    body, legends = [], []
    for l in lines:
        (legends if LEGEND.match(l.strip()) else body).append(l)
    scan = body if not args.include_legends else lines
    print(f"scanned {len(scan)} lines "
          f"({len(legends)} legend lines {'included' if args.include_legends else 'excluded'})")

    first = OrderedDict()
    for l in scan:
        for tok in TOKEN.findall(expand_elided(l)):
            key, num = _series_of(tok)
            if key is None:
                continue
            first.setdefault((key, num), tok)

    by_series = OrderedDict()
    for (key, num) in first:
        by_series.setdefault(key, []).append(num)

    ok = True
    for key, nums in by_series.items():
        order = " ".join(f"{key}{n}" for n in nums)
        ascending = nums == sorted(nums)
        gaps = [n for n in range(1, max(nums) + 1) if n not in nums] if nums else []
        status = "OK" if ascending and not gaps else "VIOLATION"
        if status != "OK":
            ok = False
        print(f"\n[{status}] {key} — order of first citation:")
        print(f"    {order}")
        if not ascending:
            print(f"    expected ascending: {' '.join(f'{key}{n}' for n in sorted(nums))}")
        if gaps:
            print(f"    numbers never cited in the body: {gaps}")

    # legend inventory vs body citations
    if legends and not args.include_legends:
        legend_nums = {}                       # (key, num) -> its own legend header
        legend_cites = {}                      # (key, num) -> the legend that cites it
        for l in legends:
            s = l.strip()
            key, num = _series_of(s)
            if key:
                legend_nums[(key, num)] = f"{key}{num}"
            # tokens AFTER the leading header are genuine citations made from inside a legend
            body_of_legend = TOKEN.sub("", expand_elided(s), count=1)
            for tok in TOKEN.findall(body_of_legend):
                k2, n2 = _series_of(tok)
                if k2 is not None:
                    legend_cites.setdefault((k2, n2), f"{key}{num}")

        cited = set(first.keys())
        missing_legend = sorted(cited - set(legend_nums))
        never_in_body = sorted(set(legend_nums) - cited)
        legend_only = [(k, n) for (k, n) in never_in_body if (k, n) in legend_cites]
        truly_orphan = [(k, n) for (k, n) in never_in_body if (k, n) not in legend_cites]

        if missing_legend:
            ok = False
            print(f"\n[VIOLATION] cited in the body but no legend found: "
                  f"{[f'{k}{n}' for k, n in missing_legend]}")
        if legend_only:
            print("\n[REVIEW] cited only from another object's legend, never from body prose:")
            for k, n in legend_only:
                print(f"    {k}{n} — cited from the legend of {legend_cites[(k, n)]}")
            print("    Not automatically a violation: its position in the sequence is the position")
            print("    of the object whose legend cites it. Confirm that ordering by hand.")
        if truly_orphan:
            ok = False
            print(f"\n[VIOLATION] legend exists but the object is cited nowhere: "
                  f"{[f'{k}{n}' for k, n in truly_orphan]}")

    print("\nP3 verdict:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# --------------------------------------------------------------------------- prose (P1/P4/P6/P7/P9)

RULES = [
    # (principle, label, regex, fix) or (principle, label, regex, fix, re_flags)
    # flags default to re.I; pass 0 for a case-sensitive rule.
    ("P1", "self-assessment of the work",
     r"rather than (assumed|guessed|a visual|impressionistic)|is what (makes|justifies|allows)|"
     r"\brobustness\b|\breliab(le|ility)\b|verified rather than|measured rather than|"
     r"cannot be (silent|missed)|serves as a (solid|strong|reliable|robust)",
     "replace with the measurement that would justify it, or delete"),
    ("P1", "intensifier / editorial nudge",
     r"\b(notably|strikingly|remarkably|importantly|interestingly|clearly shows|"
     r"demonstrates convincingly|convincing(ly)?|it is worth noting|it should be noted|"
     r"we emphasi[sz]e|dramatic(ally)?|substantial(ly)?|highly significant)\b",
     "delete; the number carries the emphasis"),
    ("P1", "editorial verdict about the paper",
     r"\bthe .{0,30}claim is now\b|\bwe no longer claim\b|\bis no longer claimed\b|"
     r"\brests on one .{0,20}rather than\b",
     "restate as a count or a set membership"),
    ("P6", "revision history leaking into the paper",
     r"\bno longer\b|\bnot retained\b|previous(ly)? threshold|at the tightened|"
     r"in the (earlier|previous) (version|draft|analysis)|do(es)? not survive|"
     r"\bwe now\b|\bis now\b|at the previous|the tightened threshold",
     "delete, or restate as a property of the data under a NAMED alternative threshold"),
    ("P7", "process scaffolding",
     r"\[EDITOR NOTE\]|\[REVIEWER NOTE\]|\[TODO\]|\[ZENODO DOI\]|\(ref\)|\bTBD\b|\bFIXME\b|"
     r"\bXXXX?\b|<placeholder>|check later|create a repo",
     "resolve the instruction and delete the note; expected count 0 at submission"),
    ("P4", "casual register",
     r"\b(sit|sits|sitting) (relative to|next to|near)\b|\bjust outside\b|\bjust below\b|"
     r"\bagain reflecting\b|\bat all\b|\ba lot of\b|\bquite\b|\bfairly\b|\bpretty\b|"
     r"\bdeal with\b|\bcome(s)? out\b",
     "replace with the technical verb"),
    ("P4", "demonstrative reaching back",
     r"\bthe latter\b|\bthe former\b|\bthis section\b|\bthe choice\b(?! of)|"
     r"\bthese values\b|\bthe above\b|\b(see )?below\b",
     "name the referent; a demonstrative may not reach back more than one clause"),
    ("P5", "rounded or approximate quantity",
     r"\b(roughly|approximately|about|around|some|nearly|almost) \d|~\s?\d|"
     r"\d+\s?[-–]\s?\d+\s?%|\bmore than \d+|\bover \d+\b|\bup to \d+\b",
     "recompute and state the exact value, or label the bound explicitly"),
    ("P9", "Unicode superscript / subscript",
     r"(?:[⁰-₟²³¹]+)",
     "flatten to plain text (10-91), or typesetting and grep both break"),
    ("P9", "capital P-value", r"\bP-value|\bP\s*[=<>]", "lower-case p throughout", 0),
]

# a narrower, high-precision British list — the broad P9 rule is advisory only
BRITISH = re.compile(
    r"\b(neighbour\w*|characteris\w+|signalling|randomis\w+|localis\w+|normalis\w+|"
    r"visualis\w+|analys(e|ed|ing)\b|colour\w*|centre\w*|behaviour\w*|labelled|modelling|"
    r"utilis\w+|summaris\w+|minimis\w+|maximis\w+|organis\w+|recognis\w+|emphasis(e|ed|ing)\b)\b",
    re.I,
)


def _iter_lines(path, skip_notes=True):
    for i, line in enumerate(open(path), 1):
        s = line.strip()
        if not s:
            continue
        if skip_notes and re.search(r"\[(EDITOR|REVIEWER) NOTE\]", s):
            # notes quote old wording on purpose; they poison every other sweep
            yield i, s, True
            continue
        yield i, s, False


def cmd_prose(args):
    hits = Counter()
    total = 0
    print(f"=== prose audit: {args.txt}\n")
    for rule in RULES:
        principle, label, pattern, fix = rule[:4]
        flags = rule[4] if len(rule) > 4 else re.I
        rx = re.compile(pattern, flags)
        found = []
        for i, s, is_note in _iter_lines(args.txt):
            if is_note and principle != "P7":
                continue
            for m in rx.finditer(s):
                lo = max(0, m.start() - 60)
                found.append((i, m.group(0), s[lo:m.end() + 60]))
        if not found:
            continue
        hits[principle] += len(found)
        total += len(found)
        print(f"[{principle}] {label} — {len(found)} hit(s)")
        print(f"       fix: {fix}")
        for i, tok, ctx in found[:args.max_hits]:
            print(f"   L{i:<5} «{tok}»  …{ctx}…")
        if len(found) > args.max_hits:
            print(f"   … {len(found) - args.max_hits} more")
        print()

    brit = []
    for i, s, is_note in _iter_lines(args.txt):
        if is_note:
            continue
        for m in BRITISH.finditer(s):
            brit.append((i, m.group(0)))
    if brit:
        c = Counter(t.lower() for _, t in brit)
        print(f"[P9] British spellings (high-precision list) — {len(brit)} hit(s)")
        print("       " + ", ".join(f"{k} x{v}" for k, v in c.most_common()))
        print()
        hits["P9"] += len(brit)
        total += len(brit)

    print("--- summary by principle ---")
    for p in ("P1", "P4", "P5", "P6", "P7", "P9"):
        print(f"  {p}: {hits.get(p, 0)}")
    print(f"  total: {total}")
    return 0 if total == 0 else 1


# --------------------------------------------------------------------------- numbers (P2/P5)

# a quantitative claim: an FDR/p-value, an odds ratio, a percentage, an exponent, a count
CLAIM = re.compile(
    r"(FDR\s*[=<>]|(?<![A-Za-z])p\s*[=<>]|\braw p\b|\bOR\b|odds ratio|"
    r"\d+(?:\.\d+)?\s?%|10-\d+|×\s?10|\bR\s*=|\brho\s*=|\bn\s*=)",
    re.I,
)
POINTER = re.compile(
    r"\((?:[^)]*\b(?:Figure|Fig\.|File|Table|Supplementary)\b[^)]*)\)|"
    r"\b(?:Figure|Fig\.|File S|Table)\s?S?\d+",
)
ORPHAN_CITATION = re.compile(r"^(?:\(\s?[0-9][0-9,–—\- ]*\)\s?)+$")

# Canonical section headings. A number in Results or Discussion MUST carry a pointer;
# a parameter value in Methods need not, and an Abstract carries its evidence downstream.
SECTIONS = [
    ("abstract", r"^Abstract$"),
    ("introduction", r"^Introduction$"),
    ("methods", r"^(Materials and methods|Methods|Material and Methods)$"),
    ("results", r"^Results$"),
    ("discussion", r"^Discussion$"),
    ("backmatter", r"^(Supplementary material|Acknowledg|Data availability|Funding|"
                   r"Conflicts? of interest|Author contributions|Ethical statement|"
                   r"Literature cited|References|Bibliography)"),
]
STRICT = {"results", "discussion"}


def _section_of(line, current):
    for name, pat in SECTIONS:
        if re.match(pat, line.strip()):
            return name
    return current


def cmd_numbers(args):
    by_section = {}
    orphans, n_claims = [], 0
    section = "front"
    for i, s, is_note in _iter_lines(args.txt):
        section = _section_of(s, section)
        if is_note:
            continue
        if ORPHAN_CITATION.match(s):
            orphans.append((i, s[:80]))
            continue
        if LEGEND.match(s):
            continue  # a legend IS the pointer
        # a table cell: a short fragment with no sentence punctuation. Word stores every
        # cell as its own <w:p>, so an inlined table would otherwise flood the report.
        if len(s.split()) < 7 and not re.search(r"[.;:]\s|[.;:]$", s):
            continue
        for sent in _SENT.split(s):
            sent = sent.strip()
            if not sent or not CLAIM.search(sent):
                continue
            n_claims += 1
            if not POINTER.search(sent):
                by_section.setdefault(section, []).append((i, sent))

    print(f"=== number traceability audit: {args.txt}\n")
    print(f"{n_claims} quantitative claims found in body prose\n")

    print(f"[P7] orphan citation-only paragraphs — {len(orphans)} (expected 0)")
    for i, s in orphans[:args.max_hits]:
        print(f"   L{i:<5} {s}")
    if len(orphans) > args.max_hits:
        print(f"   … {len(orphans) - args.max_hits} more")

    strict_hits = sum(len(v) for k, v in by_section.items() if k in STRICT)
    print(f"\n[P2] quantitative claims with NO Figure/Table/File pointer, by section:")
    for name in ("front", "abstract", "introduction", "methods", "results",
                 "discussion", "backmatter"):
        v = by_section.get(name)
        if not v:
            continue
        mark = "MUST FIX" if name in STRICT else "review"
        print(f"    {name:<13} {len(v):>4}   ({mark})")

    for name in ("results", "discussion"):
        v = by_section.get(name, [])
        if not v:
            continue
        print(f"\n  --- {name}: every one of these needs a pointer or must go ---")
        for i, sent in v[:args.max_hits]:
            print(f"   L{i:<5} {sent[:200]}")
        if len(v) > args.max_hits:
            print(f"   … {len(v) - args.max_hits} more")

    print("\nMethods/Abstract hits are reviewed, not auto-failed: a parameter value or a")
    print("headline number legitimately carries its evidence downstream. Results and")
    print("Discussion hits are failures.")
    print("Then, for each pointer that DOES exist, open the object and confirm the number is in it —")
    print("that check is not automatable and is where wrong pointers are actually found.")
    return 0 if strict_hits == 0 and not orphans else 1


# --------------------------------------------------------------------------- citations

def _doc_xml(docx_path):
    with zipfile.ZipFile(docx_path) as z:
        return z.read("word/document.xml").decode("utf8"), z.namelist()


def cmd_citations(args):
    xml, names = _doc_xml(args.docx)
    sdt = xml.count("<w:sdt>")
    mendeley = xml.count("MENDELEY_CITATION")
    biblio = xml.count("MENDELEY_BIBLIOGRAPHY")
    fld = xml.count("<w:fldChar") + xml.count("<w:instrText")
    hyper = xml.count("<w:hyperlink")
    ins = xml.count("<w:ins ")
    dele = xml.count("<w:del ")
    webext = [n for n in names if "webextension" in n]
    print(f"=== citation inventory: {args.docx}")
    print(f"  <w:sdt> content controls   : {sdt}")
    print(f"  MENDELEY_CITATION tags     : {mendeley}")
    print(f"  MENDELEY_BIBLIOGRAPHY tags : {biblio}")
    print(f"  legacy field codes         : {fld}")
    print(f"  <w:hyperlink>              : {hyper}")
    print(f"  <w:ins> / <w:del>          : {ins} / {dele}")
    print(f"  webextension parts         : {webext or 'none'}")
    print()
    if mendeley:
        print("  STORAGE = Mendeley content controls (<w:sdt>).")
        if fld:
            print(f"  ({fld} legacy field codes also present — usually a TOC or page ref, not a")
            print("   citation; confirm before touching any paragraph that contains one.)")
        print("  => NEVER rebuild a paragraph from its concatenated text.")
        print("  => Use nar_review_tools.safe_tracked_replace (direct-child runs only).")
        print("  => Do not edit, renumber or reorder citations — Daniil refreshes them in Mendeley.")
    elif fld:
        print("  STORAGE = legacy field codes. Still use safe_tracked_replace.")
    else:
        print("  No managed citations detected — confirm with Daniil before editing near references.")
    print(f"\n  RECORD THESE NUMBERS. After every edit script, re-run and require sdt={sdt}, "
          f"MENDELEY_CITATION={mendeley}.")


def cmd_anchors(args):
    """Check whether a proposed edit anchor is citation-safe in this document."""
    from lxml import etree
    with zipfile.ZipFile(args.docx) as z:
        root = etree.fromstring(z.read("word/document.xml"))
    body = root.find(W + "body")
    anchors = args.anchor
    for a in anchors:
        matches = []
        for p in body.iter(W + "p"):
            visible = _para_text(p, "final")
            if a in visible:
                # is the anchor confined to direct-child runs of the paragraph?
                direct = "".join(
                    (t.text or "")
                    for r in p.findall(W + "r")
                    for t in r.findall(W + "t")
                )
                safe = a in direct
                has_sdt = p.find(".//" + W + "sdt") is not None
                matches.append((safe, has_sdt, visible[:110]))
        if not matches:
            print(f"[NOT FOUND] {a!r}")
            print("            the text is probably split by a superscript or an existing <w:ins>;")
            print("            shorten the anchor or target the surrounding words.\n")
            continue
        if len(matches) > 1:
            print(f"[AMBIGUOUS] {a!r} matches {len(matches)} paragraphs — lengthen it.\n")
            continue
        safe, has_sdt, preview = matches[0]
        tag = "SAFE" if safe else "UNSAFE"
        print(f"[{tag}] {a!r}")
        print(f"        paragraph contains a citation control: {has_sdt}")
        print(f"        …{preview}…")
        if not safe:
            print("        the anchor crosses a citation or another nested element;")
            print("        pick a shorter anchor inside one uninterrupted stretch of prose.")
        print()


# --------------------------------------------------------------------------- audit

def cmd_audit(args):
    rc = 0
    for fn in (cmd_prose, cmd_numbers):
        print("\n" + "=" * 78)
        rc |= fn(args)
    print("\n" + "=" * 78)
    rc |= cmd_numbering(args)
    print("\n" + "=" * 78)
    print("audit verdict:", "PASS" if rc == 0 else "ISSUES FOUND — see above")
    return rc


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("extract", help="docx -> one line per paragraph")
    p.add_argument("docx"); p.add_argument("out")
    p.add_argument("--mode", choices=["final", "orig"], default="final")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("diff", help="sentence- or word-level diff of two extracts")
    p.add_argument("a"); p.add_argument("b")
    p.add_argument("--words", action="store_true")
    p.add_argument("--max-block", type=int, default=400)
    p.set_defaults(func=cmd_diff)

    p = sub.add_parser("numbering", help="P3 sequential-numbering audit")
    p.add_argument("txt")
    p.add_argument("--include-legends", action="store_true")
    p.set_defaults(func=cmd_numbering)

    p = sub.add_parser("prose", help="P1/P4/P5/P6/P7/P9 language audit")
    p.add_argument("txt"); p.add_argument("--max-hits", type=int, default=12)
    p.set_defaults(func=cmd_prose)

    p = sub.add_parser("numbers", help="P2/P5 untraceable-number audit")
    p.add_argument("txt"); p.add_argument("--max-hits", type=int, default=25)
    p.set_defaults(func=cmd_numbers)

    p = sub.add_parser("citations", help="Mendeley content-control inventory")
    p.add_argument("docx")
    p.set_defaults(func=cmd_citations)

    p = sub.add_parser("anchors", help="is a proposed edit anchor citation-safe?")
    p.add_argument("docx"); p.add_argument("--anchor", nargs="+", required=True)
    p.set_defaults(func=cmd_anchors)

    p = sub.add_parser("audit", help="prose + numbers + numbering in one report")
    p.add_argument("txt")
    p.add_argument("--max-hits", type=int, default=12)
    p.add_argument("--include-legends", action="store_true")
    p.set_defaults(func=cmd_audit)

    args = ap.parse_args()
    sys.exit(args.func(args) or 0)


if __name__ == "__main__":
    main()
