#!/usr/bin/env python
"""Gate: the mechanical half of Daniil's review principles (plan §4), per sentence.

    python tools/check_principles.py manuscript/FL_metric_classes_F1000_260925.md
    python tools/check_principles.py MS.md --only density,tables
    python tools/check_principles.py MS.md --docx OUT.docx    # also the .docx citations

| check | rule | blocks |
|---|---|---|
| decimals | D5 / HARD_RULE 13: a decimal with more than three decimals outside a p-value | yes |
| spelling | D7: British spellings from a fixed list | yes |
| citations | C1 / HARD_RULE 14: 46 Mendeley tokens and the four numeric brackets | yes |
| antithesis | D4: antithesis, aphorism and self-reference patterns | report |
| scatter | A3: a sentence reading a scatter relationship with no ρ in it | report |
| panels | B2: panels a legend declares that the body never cites | yes |
| order | B1: supplementary figures not cited in numeric order | yes after Phase 5 |
| density | r.15: more than three numeric values or more than one test in a sentence | yes |
| tables | r.19: more than five main tables, or a main table over 15 rows | yes |
| markers | r.16: a surviving [STAT: …] marker or an open stat request | yes |

The citation invariants are read from `03_revision_edits.json`, where the Mendeley fields
still carry their `⟦CIT:…⟧` tokens; the Markdown renders them as plain author–year text
and cannot tell a field from typed text. `--docx` additionally runs the scientific-review
skill's `citations` subcommand on a built .docx. The skill's copy on this machine has no
`stats` or `panels` subcommand, so A3 and B2 are implemented here.

`order` is reported, not blocking, while `[FIG:<name>]` tokens remain: numbering is
assigned in Phase 5. Exit code 1 if any blocking check fails.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The renumbered edit list (Phase 5) supersedes the assembler's once it exists.
EDITS = next(f for f in (ROOT / "workflow_runs/260924_run1/03_revision_edits_final.json",
                         ROOT / "workflow_runs/260924_run1/03_revision_edits.json")
             if f.exists())
RUN = ROOT / "workflow_runs/260924_run1"
SKILL_TOOL = Path.home() / ".claude/skills/scientific-review/scientific_review_tools.py"

BRITISH = ["colour", "neighbour", "behaviour", "tumour", "centre", r"analys(?:e|ed|ing)\b",
           "favour",
           "modelled", "labelled", "normalis", "harmonis", "organis", "characteris",
           "minimis", "maximis", "summaris", "optimis", "utilis", "recognis", "grey"]
ANTITHESIS = [r"\brather than\b", r", not [a-z]+[.,;]", r"\bit is not\b.*, it is\b",
              r"\bnot because\b.*\bbut because\b", r"\bthis (?:article|paper|study) "
              r"(?:shows|makes|argues)", r"\bthe rest of this\b", r"\bis the cost of\b",
              r"\bcorrect under its own\b", r"\bdetermines the recommendation\b"]
SCATTER = re.compile(r"\b(?:tracked|followed .{0,40}\balong|increased together|"
                     r"decreased with|along an? (?:arc|sigmoid|monotone|diagonal)|"
                     r"nearly unrelated|(?:positive|negative) (?:relationship|association)|"
                     r"(?:strong|weak) (?:positive |negative )?(?:relationship|association))"
                     r"\b", re.I)
LEGEND_START = re.compile(r"^\*\*(?:\[FIG:(\w+)\]|(Supplementary Figure|Figure) (\d+))")
FIGREF = re.compile(r"(\[FIG:(\w+)\]|(?<!\w)(Supplementary Figure|Figure)s? (\d+))"
                    r"((?:[ ]?[A-L](?![a-z])(?:\s*(?:,|and|to|–|-)\s*\d*[A-L](?![a-z]))*)?)")
NUM = re.compile(r"(?<![\w.])[-−]?\d[\d,]*(?:\.\d+)?(?![\w])")
TEST = re.compile(r"\bp\s*[=<≤]")


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(\[])", text) if s.strip()]


def countable(sent: str) -> str:
    """The sentence with every number that is a label, not a value, removed."""
    s = re.sub(r"×\s*10[⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+", "", sent)  # the exponent of a p-value
    s = re.sub(r"\b\d+\.\d+\.\d+\b|\bPython 3\.\d+", "", s)  # software versions
    s = re.sub(r"\([^()]*\b(?:et al\.|and \w+) (?:19|20)\d\d[^()]*\)", "", s)
    s = FIGREF.sub("", s)
    s = re.sub(r"\b(?:Table|Supplementary File|Section|PC|LOBO|Group|R)\s?\d+\b", "", s)
    s = re.sub(r"\b\d+_[A-Za-z]\w*", "", s)  # method names such as 10_mnn
    s = re.sub(r"\b[A-Z]\d\b|\b(?:19|20)\d\d\b", "", s)  # E1, years
    return s


def body_and_legends(md: str) -> tuple[list[str], list[str]]:
    body, legends = [], []
    for para in re.split(r"\n\s*\n", md):
        p = para.strip()
        if not p or p.startswith(("#", ">", "---")):
            continue
        (legends if LEGEND_START.match(p) else body).append(p)
    return body, legends


def _letters(spec: str) -> set[str]:
    out = set()
    for a, b in re.findall(r"([A-L])\s*(?:to|–|-)\s*\d*([A-L])", spec):
        out |= {chr(c) for c in range(ord(a), ord(b) + 1)}
    out |= set(re.findall(r"(?<![A-Za-z])([A-L])(?![a-z])", spec))
    return out


def _key(m: re.Match) -> str:
    return f"[FIG:{m.group(2)}]" if m.group(2) else f"{m.group(3)} {m.group(4)}"


def check_panels(body: list[str], legends: list[str]) -> list[str]:
    declared: dict[str, set] = {}
    for leg in legends:
        m = LEGEND_START.match(leg)
        key = f"[FIG:{m.group(1)}]" if m.group(1) else f"{m.group(2)} {m.group(3)}"
        spans = re.findall(r"\(([A-L](?:\s*(?:,|and|to|–|-)\s*[A-L])*)\)", leg)
        declared[key] = set().union(*[_letters(s) for s in spans]) if spans else set()
    cited: dict[str, set] = {}
    for para in body:
        for m in FIGREF.finditer(para):
            cited.setdefault(_key(m), set()).update(_letters(m.group(5) or ""))
    out = []
    for key, letters in declared.items():
        miss = sorted(letters - cited.get(key, set()))
        if letters and key not in cited:
            out.append(f"{key}: never cited in the body")
        elif miss and not (letters == {"A"} and key in cited):  # single-panel figure
            out.append(f"{key}: panels declared, never cited: {', '.join(miss)}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("md", type=Path)
    ap.add_argument("--only", default="")
    ap.add_argument("--docx", type=Path)
    ap.add_argument("--json", dest="json_out", type=Path)
    args = ap.parse_args(argv)
    only = set(filter(None, args.only.split(",")))
    run = lambda name: not only or name in only
    md = args.md.read_text()
    md_noc = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    body, legends = body_and_legends(md_noc)
    prose = [p for p in body if not p.startswith("|")]
    found: dict[str, list[str]] = {}
    blocking = {"decimals", "spelling", "citations", "panels", "density", "tables",
                "markers"}

    if run("decimals"):
        hits = []
        for p in prose + legends:
            for s in sentences(p):
                s = re.sub(r"https?://\S+|doi\.org/\S+", "", s)
                for m in re.finditer(r"(?<![\w.])\d+\.\d{4,}(?!\s*×)", s):
                    before = s[max(0, m.start() - 14):m.start()]
                    # p-values (two significant figures) and stated filter thresholds
                    # such as "exceeded 0.9999" are exempt from the three-digit rule.
                    if not re.search(r"\bp\b[^.]{0,8}$|\b(?:exceed\w*|above|below|"
                                     r"under|over|than)\s*$", before):
                        hits.append(f"{m.group(0)} :: {s[:100]}")
        found["decimals"] = hits
    if run("spelling"):
        found["spelling"] = [f"{w} :: {s[:100]}" for p in prose + legends
                             for s in sentences(p) for w in BRITISH
                             if re.search(rf"\b{w}", s, re.I)]
    if run("citations"):
        hits = []
        recs = json.loads(EDITS.read_text())
        new = "\n".join(r["new"] for r in recs if r["new"])
        n_cit = new.count("⟦CIT:")
        if n_cit != 46:
            hits.append(f"{n_cit} Mendeley tokens, the invariant is 46")
        for r in recs:
            if r["action"] == "edit" and re.findall(r"⟦CIT:.*?⟧", r["base"]) != \
                    re.findall(r"⟦CIT:.*?⟧", r["new"] or ""):
                hits.append(f"{r['id']}: citation tokens changed")
        for c, want in (("[38]", 2), ("[50,51]", 1), ("[52]", 1)):
            if new.count(c) != want:
                hits.append(f"{c}: {new.count(c)} occurrences, expected {want}")
        if args.docx:
            out = subprocess.run([sys.executable, str(SKILL_TOOL), "citations",
                                  str(args.docx)], capture_output=True, text=True).stdout
            m = re.search(r"MENDELEY_CITATION tags\s*:\s*(\d+)", out)
            if not m or int(m.group(1)) != 46:
                hits.append(f"{args.docx.name}: MENDELEY_CITATION count "
                            f"{m.group(1) if m else '?'}, expected 46")
        found["citations"] = hits
    if run("antithesis"):
        found["antithesis"] = [f"{pat} :: {s[:110]}" for p in prose for s in sentences(p)
                               for pat in ANTITHESIS if re.search(pat, s, re.I)]
    if run("scatter"):
        found["scatter"] = [s[:120] for p in prose for s in sentences(p)
                            if SCATTER.search(s) and "Figure" in s + p and "ρ" not in s
                            and "ρ" not in p]
    if run("panels"):
        found["panels"] = check_panels(prose, legends)
    if run("order"):
        seen = []
        for p in prose:
            for m in re.finditer(r"Supplementary Figures? (\d+)", p):
                if int(m.group(1)) not in seen:
                    seen.append(int(m.group(1)))
        found["order"] = ([] if seen == sorted(seen) else
                          [f"first-citation order {seen}"])
        if "[FIG:" in md_noc:
            blocking.discard("order")
    if run("density"):
        hits = []
        for p in prose:
            for s in sentences(p):
                k, t = len(NUM.findall(countable(s))), len(TEST.findall(s))
                if k > 3 or t > 1:
                    dest = ("Supplementary File 1, sheet Paired_tests" if t > 1 else
                            "a main table or a Supplementary File sheet")
                    hits.append(f"[{k} values, {t} tests] -> {dest} :: {s[:120]}")
        found["density"] = hits
    if run("tables"):
        hits = []
        caps = [m.group(1) for m in re.finditer(r"^\*\*Table (\d+)\.", md_noc, re.M)]
        if len(set(caps)) > 5:
            hits.append(f"{len(set(caps))} main tables {sorted(set(caps))}, budget 5")
        for block in re.split(r"\n\s*\n", md_noc):
            rows = [ln for ln in block.splitlines() if ln.startswith("|")]
            if len(rows) - 2 > 15:
                hits.append(f"a main table with {len(rows) - 2} rows (limit 15)")
        found["tables"] = hits
    if run("markers"):
        hits = [f"[STAT: {m}]" for m in re.findall(r"\[STAT:\s*([^\]]+)\]", md_noc)]
        for f in sorted(RUN.glob("10_stat_requests_*.json")):
            hits += [f"{f.name}: {r.get('id')} open" for r in json.loads(f.read_text())
                     if r.get("status") == "open"]
        found["markers"] = hits

    failed = False
    for name, hits in found.items():
        block = name in blocking
        mark = "✗" if hits and block else ("!" if hits else "✓")
        print(f"{mark} {name:11s} {len(hits):4d}  ({'blocks' if block else 'report'})")
        for h in hits[:8]:
            print(f"      {h}")
        if len(hits) > 8:
            print(f"      … {len(hits) - 8} more")
        failed |= bool(hits) and block
    if args.json_out:
        args.json_out.write_text(json.dumps(found, indent=1, ensure_ascii=False))
    print("FAIL" if failed else "OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
