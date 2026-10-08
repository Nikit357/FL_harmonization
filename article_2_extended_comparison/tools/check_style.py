#!/usr/bin/env python3
"""Enforce the Article 2 register on the F1000Research manuscript .md.

Retargeted from the AACR proposal gate (`an earlier internal proposal workflow (not public)`)
for the six F1000 sections of the implementation plan §3.1. The antithesis and
banned-phrase detectors are kept verbatim from the AACR version — they encode what Daniil
actually corrected by hand — and the §6.2 banned list is added on top of them.

Two things changed in the retarget beyond the section table:

  * Sections are markdown headings (`## Introduction`), not the numbered form lines of the
    AACR template, so SECTION_MARKER matches headings.
  * The meta-language check runs on the body only. An F1000 article carries a mandatory AI
    usage statement in the back matter, where "the manuscript" is the correct word; in the
    Results it is a tell.

Usage:
    python3 tools/check_style.py <manuscript.md> [--journal f1000] [--max-words 20000]
                                 [--rules style_rules.json] [--json OUT.json] [--quiet]

Exit codes: 0 = clean, 1 = at least one violation.

Calibration rule, inherited: an exemplar Daniil accepted must pass with zero violations. If
it does not, the thresholds are wrong, not the exemplar.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_RULES = REPO / "workflow_runs" / "260917_phase1" / "style_rules.json"

# The six sections of plan §3.1, in order. `pattern` matches the heading text; `lo`/`hi` are
# the word budgets.
#
# The targets are §3.1's: 300 / 900 / 1,400 / 5,500 / 600 / 700, total ~9,400. They are
# widened to [0.8x, 1.35x] as in the AACR gate, so a different argument is not forced to pad
# or truncate to hit a number. The abstract is the exception: 300 is F1000's own hard cap
# (§1.10), so its upper bound is not widened.
SECTIONS = [
    ("abstract",     r"^abstract",                                   150,  300),
    ("introduction", r"^introduction",                               720, 1215),
    ("methods",      r"^(?:materials\s+and\s+)?methods",            1120, 1890),
    ("results",      r"^results(?:\s+and\s+discussion)?",           4400, 7425),
    ("conclusions",  r"^conclusions?",                               480,  810),
    ("back_matter",  r"^(?:data\s+availability|data\s+and\s+software)", 560, 945),
]

# Revision round 1 re-baseline (plan decision 10, 2026-09-25): Daniil's review added 31 panel
# discussions, a test beside every comparison, four main tables, full panel-by-panel legends
# for 17 supplementary figures and three workbooks (C30, C38, C41, C73, C74, C21, C25, C31).
# The plan chose to re-baseline the budgets instead of letting them fail. Results, the
# conclusions and the back matter (which carries the supplementary legends) are widened to
# the revised text plus about 5% headroom; the abstract keeps F1000's hard 300-word cap.
SECTIONS_REVISION_260925 = [
    ("abstract",     r"^abstract",                                   150,  300),
    ("introduction", r"^introduction",                               720, 1215),
    ("methods",      r"^(?:materials\s+and\s+)?methods",            1120, 1890),
    ("results",      r"^results(?:\s+and\s+discussion)?",           4400, 13500),
    ("conclusions",  r"^conclusions?",                               480,  900),
    ("back_matter",  r"^(?:data\s+availability|data\s+and\s+software)", 560, 4000),
]
MAX_WORDS_REVISION_260925 = 21000

# Back matter is many separate H2 sections in F1000's own order. `back_matter` above anchors
# on the first of them; everything from there to EOF is charged to that one budget.
BACK_MATTER_START = "back_matter"

# A section starts on a markdown heading line: "## Introduction", "# Abstract".
SECTION_MARKER = re.compile(r"^\s*#{1,6}\s+")

TO_CONFIRM = re.compile(r"\[TO CONFIRM:.*?\]", re.S | re.I)

# Kept verbatim from the AACR gate, plus the two constructions Daniil named in §6.2: the
# bare "X, not Y" antithesis and "it is not X, it is Y".
ANTITHESIS = [
    (r"not\s+(?:a|an|the)\s+\w+[,;]\s+but", "not-a-X-but-Y antithesis"),
    (r"\brather than\b", '"rather than"'),
    (r"\bwhat separates\b", '"what separates"'),
    (r"\bis not a\b", '"is not a"'),
    (r"\bit\s+is\s+not\s+[^.;]{1,60},\s+it\s+is\b", '"it is not X, it is Y"'),
    (r",\s+not\s+[a-z][a-z-]*\s*[.;]", 'bare "X, not Y" antithesis'),
]

META = ["the manuscript", "this review", "provenance", "headroom", "verbatim"]

# §6.2, the list Daniil extended. Literal needles; the adjectives are handled separately
# because they are allowed when a measurement sits next to them.
BANNED_PHRASES_62 = [
    "delve into", "underscores", "leverage", "seamless", "pivotal", "landscape",
    "testament to", "crucial", "stands as", "in the realm of",
    "it is important to note", "plays a vital role", "navigating the complexities",
]

# §6.2 "proofless adjectives": deleted unless the adjacent clause states the measurement
# that justifies them. Mechanically: a digit must appear within PROOF_WINDOW characters.
PROOFLESS_ADJECTIVES = [
    "comprehensive", "novel", "robust", "extensive", "substantial", "powerful",
    "state-of-the-art",
]
PROOF_WINDOW = 80

# §6.2 hedge stacks ("may potentially help to").
HEDGE_STACK = re.compile(
    r"\b(?:may|might|could|can)\s+(?:potentially|possibly|perhaps|conceivably)\b", re.I)

# Daniil uses "robustness" as a technical term with a measured quantity attached. The
# Phase 1 banned list flags it outright; that entry is wrong for this register and is
# skipped here — the PROOFLESS_ADJECTIVES check covers the unmeasured use.
# See style_rules_ADDENDUM_house_guide.md in the AACR run.
BANNED_SKIP = "robustness / robust / resilience"

# The rulebook entry "Furthermore, / Moreover, / Additionally, chained across consecutive
# sentences" forbids the chain, not the word: its own rationale is "Two of them in a row
# signal that the paragraph is a list with no argument". Grepping the entry literally would
# fail the file that defines the standard, so the chain is detected by proximity instead.
CONNECTOR_ENTRY = "Furthermore, / Moreover, / Additionally,"
CONNECTORS = re.compile(r"\b(?:furthermore|moreover|additionally)\b", re.I)
CONNECTOR_CHAIN_CHARS = 400

# The exemplar carries 3 semicolons in 797 counted words = 3.8 per 1,000.
SEMICOLON_PER_1K = 4.0

# F1000 §1.10.
MAX_KEYWORDS = 8
ABSTRACT_HEADS = ("Background", "Methods", "Results", "Conclusions")


def strip_markdown(text: str) -> str:
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)      # links -> label
    text = re.sub(r"[*_~`]+", "", text)                        # emphasis, strike, code
    text = re.sub(r"^\s*[-+*]\s+", "", text, flags=re.M)       # bullet markers
    return text


def count_words(text: str) -> int:
    """Words of authored prose: markdown syntax and [TO CONFIRM] spans do not count."""
    text = TO_CONFIRM.sub(" ", text)
    return sum(1 for tok in strip_markdown(text).split() if re.search(r"[A-Za-z0-9]", tok))


def split_document(md: str):
    """Return (header_text, {section_key: body_text}, [missing_keys]).

    Heading lines are excluded from both bodies and header. `back_matter` runs from its
    anchor heading to the end of the file, so the nine F1000 back-matter sections share one
    budget instead of needing nine of their own.
    """
    lines = md.splitlines()
    body = [ln for ln in lines if ln.strip() != "---"]

    hits = []
    for i, ln in enumerate(body):
        if not SECTION_MARKER.match(ln):
            continue
        plain = strip_markdown(SECTION_MARKER.sub("", ln)).strip().lower()
        for key, pat, _, _ in SECTIONS:
            if re.search(pat, plain):
                hits.append((i, key))
                break

    seen, ordered = set(), []
    for i, key in hits:
        if key not in seen:
            seen.add(key)
            ordered.append((i, key))

    header = "\n".join(body[: ordered[0][0]]) if ordered else "\n".join(body)
    bodies = {}
    for n, (i, key) in enumerate(ordered):
        end = len(body) if key == BACK_MATTER_START else (
            ordered[n + 1][0] if n + 1 < len(ordered) else len(body))
        bodies[key] = "\n".join(body[i + 1: end])
    missing = [k for k, _, _, _ in SECTIONS if k not in bodies]
    return header, bodies, missing


def banned_needles(rules_path: Path):
    """Turn the rulebook's banned entries into literal strings that can be grepped.

    Entries are written for a human ("unprecedented (as in '...')",
    "robustness / robust / resilience (as a property of...)"), so the parenthetical
    gloss is dropped and slash-separated alternatives become separate needles.
    """
    if not rules_path.exists():
        # Silent degradation is the failure mode that matters here: with no rulebook the
        # gate still prints "OK: clean" while checking none of the 48 banned entries.
        print(f"WARNING: rulebook not found at {rules_path}; "
              f"the 48 banned-phrase entries were NOT checked", file=sys.stderr)
        return []
    data = json.loads(rules_path.read_text())
    out = []
    for entry in data.get("banned", []):
        phrase = entry.get("phrase", "")
        if phrase.startswith(BANNED_SKIP) or phrase.startswith(CONNECTOR_ENTRY):
            continue
        head = phrase.split(" (")[0].strip().rstrip(".")
        for alt in head.split(" / "):
            alt = alt.strip().lower()
            if len(alt) >= 4:
                out.append((alt, phrase))
    return out


def check(path: Path, max_words: int, rules_path: Path):
    md = path.read_text()
    header, bodies, missing = split_document(md)
    counted = header + "\n" + "\n".join(bodies.values())
    prose = strip_markdown(TO_CONFIRM.sub(" ", counted))
    low = prose.lower()

    # The meta-language check exempts the back matter: the AI usage statement F1000 requires
    # is about how the manuscript was made, so those words are correct there.
    body_only = strip_markdown(TO_CONFIRM.sub(" ", header + "\n" + "\n".join(
        v for k, v in bodies.items() if k != BACK_MATTER_START))).lower()

    total = count_words(counted)
    per_section = {k: count_words(bodies.get(k, "")) for k, _, _, _ in SECTIONS}
    violations = []

    for key in missing:
        violations.append(("sections", f"section '{key}' not found"))
    for key, _, lo, hi in SECTIONS:
        if key in missing:
            continue
        n = per_section[key]
        if n == 0:
            violations.append(("sections", f"section '{key}' is empty"))
        elif not lo <= n <= hi:
            violations.append(("length", f"section '{key}': {n} words, budget {lo}-{hi}"))

    if total > max_words:
        violations.append(("length", f"total {total} words exceeds {max_words}"))

    abstract = bodies.get("abstract", "")
    if abstract:
        absent = [h for h in ABSTRACT_HEADS if not re.search(rf"\b{h}\b", abstract, re.I)]
        if absent:
            violations.append(("f1000", "abstract is not structured; missing "
                                        + ", ".join(absent)))

    kw = re.search(r"^\s*(?:#{1,6}\s*)?\**keywords\**\s*[:—-]\s*(.+)$", md, re.I | re.M)
    if not kw:
        violations.append(("f1000", "no Keywords line; F1000 requires keywords"))
    else:
        n_kw = len([k for k in re.split(r"[;,]", kw.group(1)) if k.strip()])
        if n_kw > MAX_KEYWORDS:
            violations.append(("f1000", f"{n_kw} keywords; F1000 allows {MAX_KEYWORDS}"))

    em = prose.count("—")
    if em:
        violations.append(("em-dash", f"{em} em-dash(es); the budget is zero"))

    semis = prose.count(";")
    density = semis / total * 1000 if total else 0
    if density > SEMICOLON_PER_1K:
        violations.append(("semicolon",
                           f"{semis} semicolons = {density:.1f} per 1,000 words, "
                           f"limit {SEMICOLON_PER_1K}"))

    for pat, name in ANTITHESIS:
        for m in re.finditer(pat, low):
            violations.append(("antithesis", f"{name}: …{prose[max(0, m.start()-40):m.end()+40].strip()}…"))

    for word in META:
        if word in body_only:
            violations.append(("meta", f'"{word}" — the body does not discuss how it was made'))

    for needle in BANNED_PHRASES_62:
        for m in re.finditer(re.escape(needle), low):
            violations.append(("banned-6.2",
                               f'"{needle}": …{prose[max(0, m.start()-40):m.end()+40].strip()}…'))

    for adj in PROOFLESS_ADJECTIVES:
        for m in re.finditer(rf"\b{re.escape(adj)}\b", low):
            window = prose[max(0, m.start() - PROOF_WINDOW): m.end() + PROOF_WINDOW]
            if not re.search(r"\d", window):
                violations.append(("proofless",
                                   f'"{adj}" with no measurement within {PROOF_WINDOW} chars: '
                                   f"…{prose[max(0, m.start()-40):m.end()+40].strip()}…"))

    for m in HEDGE_STACK.finditer(prose):
        violations.append(("hedge", f"stacked hedge: …{prose[max(0, m.start()-30):m.end()+30].strip()}…"))

    # The rulebook and the §6.2 list overlap. Where both cover a phrase, the §6.2 check
    # already reported every occurrence with its context, so the rulebook's presence-only
    # hit would only inflate the count.
    covered = set(BANNED_PHRASES_62) | set(PROOFLESS_ADJECTIVES) | {"rather than"}
    for needle, phrase in banned_needles(rules_path):
        if needle in covered:
            continue
        if needle in low:
            violations.append(("banned", f'"{needle}"  (rulebook: {phrase[:70]}…)'))

    spans = [m.start() for m in CONNECTORS.finditer(prose)]
    chains = sum(1 for a, b in zip(spans, spans[1:]) if b - a < CONNECTOR_CHAIN_CHARS)
    if chains:
        violations.append(("banned", f"{chains} additive-connective chain(s): two of "
                                     f"Furthermore/Moreover/Additionally within "
                                     f"{CONNECTOR_CHAIN_CHARS} characters"))

    return {
        "file": str(path),
        "total_words": total,
        "max_words": max_words,
        "per_section": per_section,
        "em_dashes": em,
        "semicolons": semis,
        "semicolon_density_per_1k": round(density, 2),
        "violations": [{"check": c, "detail": d} for c, d in violations],
        "verdict": "CLEAN" if not violations else "VIOLATIONS",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manuscript")
    ap.add_argument("--journal", default="f1000", choices=["f1000"],
                    help="section table and hard limits to apply (only f1000 is defined)")
    ap.add_argument("--max-words", type=int, default=20000,
                    help="F1000's body limit (§1.10); the section budgets catch drift below it")
    ap.add_argument("--rules", default=str(DEFAULT_RULES))
    ap.add_argument("--budgets", default="plan_260917", choices=["plan_260917",
                                                                 "revision_260925"],
                    help="section budgets: the original plan's, or the revision-round "
                         "re-baseline (plan decision 10)")
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--quiet", action="store_true", help="print only violations")
    args = ap.parse_args()

    path = Path(args.manuscript)
    if not path.exists():
        print(f"ERROR: no such file: {path}", file=sys.stderr)
        return 2

    if args.budgets == "revision_260925":
        global SECTIONS
        SECTIONS = SECTIONS_REVISION_260925
        args.max_words = max(args.max_words, MAX_WORDS_REVISION_260925)
    r = check(path, args.max_words, Path(args.rules))

    print(path.name)
    if not args.quiet:
        print(f"  {r['total_words']} words (limit {r['max_words']}) · "
              f"{r['em_dashes']} em-dash · {r['semicolons']} semicolons "
              f"({r['semicolon_density_per_1k']}/1k)")
        for key, _, lo, hi in SECTIONS:
            n = r["per_section"][key]
            mark = "✓" if lo <= n <= hi else "✗"
            print(f"  {mark} {key:14s} {n:>5} w   budget {lo}-{hi}")

    if r["violations"]:
        print(f"\n  {len(r['violations'])} violation(s):")
        for v in r["violations"]:
            print(f"  ✗ [{v['check']}] {v['detail']}")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(r, indent=2))
        print(f"\n  wrote {args.json_out}")

    if r["violations"]:
        print(f"\nFAIL: {len(r['violations'])} violation(s).")
        return 1
    print("\nOK: clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
