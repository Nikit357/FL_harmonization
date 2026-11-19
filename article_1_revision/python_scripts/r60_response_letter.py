"""
r60_response_letter.py — response letter docx from response_letter_draft.md (plan WP13).

Reads the draft (edited by Daniil and Arsen, gate G5), fills every {{key}} with the
`display` value of output/numbers.json (CLAUDE.md hard rule 5: no typed numbers), and
writes Revised_manuscript/NARGAB-2026-312_response_to_reviewers_<YYMMDD>.docx.

Final mode (default) refuses to build while the draft still holds a [PENDING: …] marker,
a [LINES] marker or a {{key}} that is missing or pending in numbers.json. `--draft`
builds anyway and highlights every unresolved place in yellow, for reading.

Supported Markdown: the leading HTML comment (dropped), #/##/### headings, paragraphs,
"- " and "1. " list items (one level, wrapped lines joined), **bold** and *italic*.

Usage
-----
python r60_response_letter.py --draft
python r60_response_letter.py            # after gate G5, when nothing is pending
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re

import revision_lib as rl

DRAFT_PATH = rl.REVISION_DIR / "response_letter_draft.md"
NUMBERS_PATH = rl.OUTPUT_DIR / "numbers.json"
OUT_DIR = rl.REVISION_DIR / "Revised_manuscript"
KEY_PATTERN = re.compile(r"\{\{([^}]+)\}\}")
UNRESOLVED_PATTERN = re.compile(r"\[PENDING:[^\]]*\]|\[LINES\]|⟦[^⟧]*⟧")
INLINE_PATTERN = re.compile(
    r"(\*\*[^*]+\*\*|\*[^*]+\*|\[PENDING:[^\]]*\]|\[LINES\]|⟦[^⟧]*⟧)"
)


def fill_numbers(text: str, numbers: dict) -> tuple[str, list[str]]:
    """Replace {{key}} by its display value; unresolved keys become ⟦key⟧."""
    problems: list[str] = []

    def replace(match: re.Match) -> str:
        key = match.group(1)
        entry = numbers.get(key)
        if entry is None or entry.get("status") != "ready":
            problems.append(key)
            return f"⟦{key}⟧"
        return str(entry["display"])

    return KEY_PATTERN.sub(replace, text), problems


def blocks(text: str) -> list[tuple[str, str]]:
    """(kind, text) blocks: h1/h2/h3, bullet, number, para. Wrapped lines are joined."""
    text = re.sub(r"^<!--.*?-->\s*", "", text, flags=re.S)
    out: list[tuple[str, str]] = []
    for chunk in re.split(r"\n\s*\n", text.strip()):
        lines = chunk.splitlines()
        if lines[0].startswith("#"):
            level = len(lines[0]) - len(lines[0].lstrip("#"))
            out.append((f"h{level}", lines[0].lstrip("#").strip()))
            continue
        current: tuple[str, list[str]] | None = None
        for line in lines:
            stripped = line.strip()
            item = re.match(r"^(-|\d+\.)\s+(.*)$", stripped)
            if item and not line.startswith("   "):
                if current:
                    out.append((current[0], " ".join(current[1])))
                kind = "bullet" if item.group(1) == "-" else "number"
                current = (kind, [item.group(2)])
            elif current:
                current[1].append(stripped)
            else:
                current = ("para", [stripped])
        if current:
            out.append((current[0], " ".join(current[1])))
    return out


def add_inline(paragraph: object, text: str) -> None:
    """Runs with bold / italic / yellow highlight for unresolved markers."""
    from docx.enum.text import WD_COLOR_INDEX

    for piece in INLINE_PATTERN.split(text):
        if not piece:
            continue
        if piece.startswith("**"):
            paragraph.add_run(piece[2:-2]).bold = True
        elif piece.startswith("*"):
            paragraph.add_run(piece[1:-1]).italic = True
        elif UNRESOLVED_PATTERN.fullmatch(piece):
            run = paragraph.add_run(piece)
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW
        else:
            paragraph.add_run(piece)


def build(parsed: list[tuple[str, str]], path) -> None:
    """Write the docx (Arial 11, headings in the document's heading styles)."""
    from docx import Document
    from docx.shared import Pt

    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(11)
    for kind, text in parsed:
        if kind.startswith("h"):
            document.add_heading(text, level=min(int(kind[1]) - 1, 3) or 0)
        elif kind == "bullet":
            add_inline(document.add_paragraph(style="List Bullet"), text)
        elif kind == "number":
            add_inline(document.add_paragraph(style="List Number"), text)
        else:
            add_inline(document.add_paragraph(), text)
    document.save(path)


def main() -> None:
    """Fill, check and write the letter."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--draft", action="store_true", help="build with highlights")
    args = parser.parse_args()
    numbers = json.loads(NUMBERS_PATH.read_text()) if NUMBERS_PATH.exists() else {}
    draft = re.sub(r"^<!--.*?-->\s*", "", DRAFT_PATH.read_text(), flags=re.S)
    text, missing_keys = fill_numbers(draft, numbers)
    unresolved = UNRESOLVED_PATTERN.findall(text)
    print(f"numbers not ready: {sorted(set(missing_keys))}")
    print(f"unresolved markers: {len(unresolved)}")
    if (missing_keys or unresolved) and not args.draft:
        raise SystemExit("not final: resolve the markers above or build with --draft")
    tag = dt.date.today().strftime("%y%m%d")
    suffix = "_DRAFT" if args.draft else ""
    path = OUT_DIR / f"NARGAB-2026-312_response_to_reviewers_{tag}{suffix}.docx"
    build(blocks(text), path)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
