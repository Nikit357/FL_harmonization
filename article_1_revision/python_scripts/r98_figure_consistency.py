"""
r98_figure_consistency.py — deterministic consistency audit of the figure notebooks and SVGs.

Plan: `figure_review_corrections_plan_261108.md`, item 14a (Daniil 2026-11-08: "palettes,
notations, names and conventions universal across all figures"). Runs on JupyterHub, reads
only the repository (no S3), takes a few seconds.

What it checks
--------------
1. Palettes. Every dict literal named after an article palette (`strat_pal`, `method_pal`,
   `imp_pal`, `lymphoma_ontogeny_palette`, `rna_batch_palette`, `platform_palette`) in the
   code cells of nb01–nb08 is compared key by key with its canonical copy:
   `strat_pal`, `lymphoma_ontogeny_palette`, `rna_batch_palette` from nb01; `method_pal`,
   `imp_pal` from nb04 §0c; `platform_palette` from nb06. A key with another colour, or a
   palette built by code instead of copied (no literal), is a finding.
2. Figure text. The text of every publication SVG in `figures_svg/` (top level; `svg.fonttype
   = none` keeps the text as text) is scanned for: snake_case words, internal codes (`post0`,
   `post1`, `_nocov`, `L11`, `WP` + digit, `V1` as a word), the word "regret" (renamed
   "decrease", 2026-11-08), "Batch removal" as the name of a combined axis (D1: "Batch mixing
   (global + local mean)"), and the agreement with batch-free fold changes (removed
   2026-11-08). Only files listed in `figures_svg/PLACEMENT.md` are publication figures;
   review-only files are skipped.

What it does not check (the reviewer agent does): grey dots where a palette exists, axis
directions, scales, legend wording between figures.

Output: `output/wp14/figure_consistency.tsv` (check, figure / notebook, element, found,
expected); one row per finding. An empty table (header only) means no finding.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pandas as pd
from matplotlib.colors import to_rgb

REVISION_DIR = Path(__file__).resolve().parent
FIGURES_DIR = REVISION_DIR / "figures_svg"
OUT_PATH = REVISION_DIR / "output" / "wp14" / "figure_consistency.tsv"
NOTEBOOKS = sorted(REVISION_DIR.glob("nb0[1-8]_*.ipynb"))
CANONICAL_SOURCE = {
    "strat_pal": "nb01",
    "lymphoma_ontogeny_palette": "nb01",
    "rna_batch_palette": "nb01",
    "method_pal": "nb04",
    "imp_pal": "nb04",
    "platform_palette": "nb06",
}
# Notebooks whose figures are review material only (not in PLACEMENT.md as publication files):
# a deviating palette there is reported with this note, not hidden.
REVIEW_ONLY_NOTEBOOKS = {"nb07"}
TEXT_RULES: list[tuple[str, re.Pattern, str]] = [
    ("snake_case word", re.compile(r"\b[a-z0-9]+_[a-z0-9_]+\b"), "plain words (PUBLICATION_NAMES)"),
    ("internal code", re.compile(r"\bpost[01]\b|_nocov|\bL11\b|\bWP\d|\bV1\b"), "plain words"),
    ("regret", re.compile(r"(?i)\bregret"), "decrease (Daniil 2026-11-08)"),
    ("combined axis named 'Batch removal'", re.compile(r"(?<![Gg]lobal )\bBatch removal\b"),
     "Batch mixing (global + local mean) (D1)"),
    ("fold-change agreement", re.compile(r"(?i)batch-free fold change"), "removed 2026-11-08"),
]


KEY_ALIASES = {"RNA-seq": "RNASeq"}  # figure label of the nb06 key
COLOUR_TOLERANCE = 1.5 / 255  # hex vs 3–4-decimal RGB copies of the same colour


def same_colour(a: object, b: object) -> bool:
    """True when two colour specs (hex or RGB tuple) are the same colour up to rounding."""
    try:
        return max(abs(x - y) for x, y in zip(to_rgb(a), to_rgb(b))) <= COLOUR_TOLERANCE
    except ValueError:
        return str(a).lower() == str(b).lower()


def notebook_code(path: Path) -> list[str]:
    """Code cells of a notebook as source strings."""
    cells = json.loads(path.read_text())["cells"]
    return ["".join(cell["source"]) for cell in cells if cell["cell_type"] == "code"]


def palette_literals(path: Path) -> dict[str, dict | None]:
    """Palette name → dict literal (None when the palette is built by code)."""
    found: dict[str, dict | None] = {}
    for source in notebook_code(path):
        try:
            tree = ast.parse(source)
        except SyntaxError:  # notebook magics; such cells hold no palette
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in CANONICAL_SOURCE:
                    try:
                        found[target.id] = ast.literal_eval(node.value)
                    except ValueError:
                        found.setdefault(target.id, None)
    return found


def palette_findings() -> list[dict]:
    """Key-by-key comparison of every palette copy with its canonical notebook."""
    literals = {path.name[:4]: palette_literals(path) for path in NOTEBOOKS}
    rows = []
    for palette, source in CANONICAL_SOURCE.items():
        canonical = literals.get(source, {}).get(palette)
        assert canonical, f"{palette} has no literal in {source}"
        for notebook, palettes in literals.items():
            if palette not in palettes or notebook == source:
                continue
            note = " (review-only figures)" if notebook in REVIEW_ONLY_NOTEBOOKS else ""
            copy = palettes[palette]
            if copy is None:
                rows.append({"check": "palette built by code", "where": notebook, "element": palette,
                             "found": "not a literal copy" + note, "expected": f"copy of {source}"})
                continue
            for key, colour in copy.items():
                key = KEY_ALIASES.get(key, key)
                if key in canonical and not same_colour(canonical[key], colour):
                    rows.append({"check": "palette colour", "where": notebook, "element": f"{palette}[{key!r}]",
                                 "found": f"{colour}{note}", "expected": f"{canonical[key]} ({source})"})
                if key not in canonical:
                    rows.append({"check": "palette key unknown", "where": notebook, "element": f"{palette}[{key!r}]",
                                 "found": f"{colour}{note}", "expected": f"key of {source}"})
    return rows


def publication_svgs() -> list[Path]:
    """SVGs named in PLACEMENT.md as publication figures (review-only rows excluded)."""
    placement = (FIGURES_DIR / "PLACEMENT.md").read_text()
    stems = set(re.findall(r"^\| (\w+?)\.\{svg", placement, flags=re.M))
    stems |= {s for s in re.findall(r"^\| (fig[45])\{", placement, flags=re.M)}
    files = []
    for svg in sorted(FIGURES_DIR.glob("*.svg")):
        if svg.stem in stems or any(svg.stem.startswith(s) for s in stems if s in ("fig4", "fig5")):
            files.append(svg)
    return files


def svg_text(path: Path) -> list[str]:
    """Text strings of an SVG (svg.fonttype = none keeps them as <text> elements)."""
    content = path.read_text(errors="ignore")
    texts = re.findall(r"<text\b[^>]*>(.*?)</text>", content, flags=re.S)
    return [re.sub(r"<[^>]+>", "", t).strip() for t in texts if re.sub(r"<[^>]+>", "", t).strip()]


def text_findings() -> list[dict]:
    """Rule hits in the figure text of every publication SVG."""
    rows = []
    for svg in publication_svgs():
        for text in svg_text(svg):
            for check, pattern, expected in TEXT_RULES:
                for match in pattern.findall(text):
                    rows.append({"check": check, "where": svg.name, "element": text[:80],
                                 "found": match if isinstance(match, str) else match[0],
                                 "expected": expected})
    return rows


def main() -> None:
    findings = pd.DataFrame(palette_findings() + text_findings(),
                            columns=["check", "where", "element", "found", "expected"]).drop_duplicates()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    findings.to_csv(OUT_PATH, sep="\t", index=False)
    n_svgs = len(publication_svgs())
    print(f"{len(NOTEBOOKS)} notebooks, {n_svgs} publication SVGs → {len(findings)} findings")
    if len(findings):
        print(findings.groupby(["check", "where"]).size().to_string())
    print(f"wrote {OUT_PATH.relative_to(REVISION_DIR)}")


if __name__ == "__main__":
    main()
