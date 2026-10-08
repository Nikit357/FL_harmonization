#!/usr/bin/env python3
"""Build extended-document v3: the v2 edit pass, renumbered to Article 2's figures.

Article 2 promotes the extended document's Extended Figures 1 to 3 to main Figures 1 to
3 and demotes Extended Figures 4 to 13 to Supplementary Figures 1 to 10, and the Figma
frames are renamed to match. v3 carries that numbering.

**Why this rebuilds from the original instead of editing v2.** All 123 "Extended Figure"
references in v2 sit inside v2's own unaccepted `w:ins` insertions -- they *are* that
pass's 112 figure-reference rewrites. Renumbering them would mean nesting a second
author's revision inside a pending insertion, which `safe_tracked_replace` cannot do.
So v3 is built the way `../CLAUDE.md` says never to chain edit passes: from the
untouched original, with one clean layer of tracked changes. Reject All on v3 restores
`Harmonization_metrics_extended.docx` exactly. v2 is left on disk untouched; the audit
cites it by name.

**What is reused and what is replaced.** Every anchored number and language edit of the
v2 pass is reused verbatim by importing them from that script. Only the figure map is
replaced, and composing the two maps is what makes it simple:

    original "Figure 6, 7, 8"        -> "Figure 1, 2, 3"          (the document's own,
                                                                   promoted to main)
    original "Extended Figure 1..10" -> "Supplementary Figure 1..10"   (unchanged number)
    original "Figure 1..5"           -> qualified, see below
    original "Supplementary Figure N"-> qualified, see below

**The collision, and Daniil's ruling of 2026-09-20.** The document also cites the source
benchmark's own figures: "Figure 3" seven times, "Figure 4" once, and Supplementary
Figures 6, 7 and 17. Renaming the document's own Extended Figure 3 to "Figure 3" would
put two meanings on one label, so every borrowed reference gains "of the source
benchmark". The reference regex swallows a trailing panel letter before the qualifier is
appended, so "Figure 4A" becomes "Figure 4A of the source benchmark" and not
"Figure 4 of the source benchmarkA".

    source ~/venvs/collagen_3_11/bin/activate
    cd article_2_extended_comparison
    python tools/apply_extended_doc_v3_260920.py
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                       # article_2_extended_comparison/
REPO = ROOT.parent                       # FL_harmonization/
V2_SCRIPT = (REPO / "figures_for_article/edit_python_scripts"
                    "/apply_extended_metrics_edits_v2_260802.py")

AUTHOR = "Claude (Article 2)"
DATE = "2026-09-20T00:00:00Z"
QUALIFIER = " of the source benchmark"

SRC = "Harmonization_metrics_extended.docx"
DST = "Harmonization_metrics_extended_260920_v3.docx"

# The reference regex, extended with the panel letter so a qualified reference keeps it.
# The negative lookahead on a lower-case letter stops "Figure 3 and" being read as panel
# "a", which would swallow a real word.
REF = re.compile(r"(Supplementary |Extended )?(Figures?)\s+(\d+)([A-Z](?![a-z]))?")

# Spans the generic sweep cannot get right on its own, searched in the ORIGINAL text.
# The last three only change the prefix, because the composed map leaves their numbers
# alone; they are kept explicit so the sweep is never asked to guess at a comma list.
SPECIALS = [
    ("Figures 6-8", "Figures 1-3"),
    ("Extended Figure 5G, 5H, 5K, 5L", "Supplementary Figure 5G, 5H, 5K, 5L"),
    ("Extended Figure 4 and 5", "Supplementary Figure 4 and 5"),
    ("Extended Figure 2D, 2E", "Supplementary Figure 2D, 2E"),
]


def load_v2_module():
    """Import the v2 edit script so its 328 anchored edits are reused, not retyped."""
    sys.path.insert(0, str(REPO / ".claude" / "skills"))
    spec = importlib.util.spec_from_file_location("extended_v2", V2_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replacement_for(prefix, word, num, panel):
    """The rewritten reference under Article 2's numbering. Never returns None.

    Every reference in this document changes: the document's own figures are renumbered
    and the borrowed ones are qualified, so there is no untouched case left.
    """
    panel = panel or ""
    if prefix == "Extended ":
        return f"Supplementary {word} {num}{panel}"
    if prefix == "Supplementary ":
        return f"Supplementary {word} {num}{panel}{QUALIFIER}"
    if num in (6, 7, 8):
        return f"{word} {num - 5}{panel}"
    return f"{word} {num}{panel}{QUALIFIER}"


def figure_edits(text):
    """Ordered (search, replace) pairs for every figure reference in one paragraph.

    Each key is grown leftwards until it is the first match in the text that
    `safe_tracked_replace` can still see, which is the discipline of
    `figures_for_article/CLAUDE.md`: a bare reference is not a safe key, because
    "Figure 6" is a substring of "Supplementary Figure 6".
    """
    out = []
    shadow = text
    for m in REF.finditer(text):
        prefix, word, num, panel = m.group(1) or "", m.group(2), int(m.group(3)), m.group(4)
        new_ref = replacement_for(prefix, word, num, panel)
        start, end = m.span()
        for pad in range(0, min(start, 40) + 1):
            key = text[start - pad:end]
            if shadow.find(key) == start - pad:
                break
        else:
            raise SystemExit(f"cannot disambiguate figure reference {m.group(0)!r}")
        out.append((key, text[start - pad:start] + new_ref))
        shadow = shadow[:start - pad] + "\0" * (end - start + pad) + shadow[end:]
    return out


def renum_text(text):
    """Renumber the figure references inside a replacement string.

    The v2 pass writes every replacement against the document's original numbering so it
    can be read beside the source; the same map has to be applied to that text before it
    is inserted, because it lands inside `w:ins` where the sweep cannot reach it.
    """
    for old, new in SPECIALS:
        text = text.replace(old, new)
    return REF.sub(
        lambda m: replacement_for(m.group(1) or "", m.group(2),
                                  int(m.group(3)), m.group(4)), text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--dst", default=DST)
    args = ap.parse_args()

    versions = ROOT / "manuscript_versions"
    if (versions / args.dst).exists():
        print(f"{args.dst} already exists; move it aside to rebuild", file=sys.stderr)
        return 1

    module = load_v2_module()
    module.SRC, module.DST = args.src, args.dst
    module.REF = REF
    module.SPECIALS = SPECIALS
    module.figure_edits = figure_edits
    module.renum_text = renum_text
    module.set_revision_identity(AUTHOR, DATE)

    # The v2 script resolves SRC and DST against the working directory.
    os.chdir(versions)
    module.main()
    print(f"  wrote manuscript_versions/{args.dst} as {AUTHOR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
