#!/usr/bin/env python3
"""Extract every cell of a generated notebook that the generator did not write.

Plan §4.2e step 1. Regenerating a notebook overwrites it. Any cell a human added, and
any generator cell a human edited in place, is destroyed silently by that overwrite, so
both are collected here before anything is regenerated.

Method: the generator is copied to a scratch directory and run there, so it writes its
reference notebook next to the copy instead of over the real one (OUTPUT is derived from
`__file__`). Every real cell is then matched against that reference:

    GENERATOR  identical after normalization  -> the generator owns it
    NEAR       >= NEAR_RATIO similarity       -> a generator cell edited by hand
    DIVERGED   below that                     -> written by hand

NEAR is the category that matters most and the one a diff of cell counts misses. Such a
cell still looks like the generator's, so nobody notices when regeneration reverts it.

Normalization folds the six-digit date tags together, so a notebook built at one
--date-tag compares cleanly against a generator run at another.

Usage:
    python3 tools/extract_hand_written_cells.py \
        --generator ../harmonization-metrics/create_correlation_prediction_notebook.py \
        --notebook  ../harmonization-metrics/correlation_prediction_metrics_analysis.ipynb \
        --tag main --gen-args "--date-tag 260905" \
        --out-notebook ../harmonization-metrics/hand_written_cells_260917.ipynb \
        --out-report   ../harmonization-metrics/diverged_cells_260917.md
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import nbformat as nbf

NEAR_RATIO = 0.90
CYRILLIC = re.compile(r"[\u0410-\u044f\u0401\u0451]")

# A cell whose whole body is a bare name or attribute — `df_lmn`, `analysis`,
# `len(gl.gene.unique())` — is an inspection someone typed while reading the output. It
# carries no logic to port and nothing to lose.
SCRATCH_MAX_LINES = 2
PORT_MARKERS = ("save_figure", "save_panel", "to_csv", "ExcelWriter", "to_excel",
                "def ", "savefig")


def normalize(src: str) -> str:
    src = re.sub(r"\b26\d{4}\b", "DATE", src)
    src = re.sub(r"[ \t]+$", "", src, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", src).strip()


def read_cells(path: Path):
    nb = json.loads(path.read_text())
    return [(c["cell_type"],
             "".join(c["source"]) if isinstance(c["source"], list) else c["source"])
            for c in nb["cells"]]


def reference_cells(generator: Path, gen_args: str, notebook_name: str):
    """Run the generator in a scratch copy so it cannot overwrite the real notebook."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        shutil.copy(generator, tmp / generator.name)
        cmd = [sys.executable, str(tmp / generator.name)] + (gen_args.split() if gen_args else [])
        r = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"generator failed:\n{r.stdout}\n{r.stderr}")
        ref = tmp / notebook_name
        if not ref.exists():
            found = list(tmp.glob("*.ipynb"))
            raise SystemExit(f"generator wrote {[p.name for p in found]}, not {notebook_name}")
        return read_cells(ref)


def classify(real, ref):
    refn = [normalize(s) for _, s in ref]
    refset = set(refn)
    rows = []
    for i, (ct, src) in enumerate(real):
        n = normalize(src)
        if not n:
            kind, ratio = "EMPTY", 1.0
        elif n in refset:
            kind, ratio = "GENERATOR", 1.0
        else:
            ratio = max((difflib.SequenceMatcher(None, n, r).ratio() for r in refn), default=0.0)
            kind = "NEAR" if ratio >= NEAR_RATIO else "DIVERGED"
        rows.append({"index": i, "cell_type": ct, "kind": kind,
                     "ratio": round(ratio, 3), "source": src,
                     "russian": bool(CYRILLIC.search(src))})
    return rows


def recommend(row) -> str:
    """One line per cell: port into the generator, keep only here, or drop."""
    src, body = row["source"], [l for l in row["source"].splitlines() if l.strip()]
    if row["kind"] == "NEAR":
        return ("port — a generator cell edited by hand; regeneration reverts the edit "
                f"silently (similarity {row['ratio']})")
    if row["russian"]:
        return "keep — Daniil's working note, not code the generator should emit"
    if row["cell_type"] == "markdown":
        return "port — section prose the regenerated notebook should carry"
    if len(body) <= SCRATCH_MAX_LINES and not any(m in src for m in PORT_MARKERS) \
            and "=" not in src:
        return "drop — bare inspection of a variable, no logic to lose"
    if any(m in src for m in PORT_MARKERS):
        return "port — writes a figure or a table that the article depends on"
    return "keep — exploratory analysis; port only if Article 2 quotes it"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--generator", action="append", required=True)
    ap.add_argument("--notebook", action="append", required=True)
    ap.add_argument("--tag", action="append", required=True)
    ap.add_argument("--gen-args", action="append", default=[])
    ap.add_argument("--out-notebook", required=True)
    ap.add_argument("--out-report", required=True)
    args = ap.parse_args()

    n = len(args.notebook)
    gen_args = (args.gen_args + [""] * n)[:n]

    out = nbf.v4.new_notebook()
    out.cells.append(nbf.v4.new_markdown_cell(
        "# Hand-written cells, preserved before regeneration\n\n"
        "Every cell below is one the generator did not write, collected by "
        "`article_2_extended_comparison/tools/extract_hand_written_cells.py` "
        "(plan §4.2e step 1). Cells keep their original source and their original order "
        "within each notebook.\n\n"
        "`DIVERGED` was written by hand. `NEAR` is a generator cell that was edited by "
        "hand — regenerating reverts that edit without saying so, which is the failure "
        "this notebook exists to prevent.\n\n"
        "The companion report is `diverged_cells_260917.md`."))

    report = ["# Diverged cells — port / keep / drop",
              "",
              "Produced by `article_2_extended_comparison/tools/extract_hand_written_cells.py`.",
              "",
              "`DIVERGED` = written by hand. `NEAR` = a generator cell edited by hand, "
              "which regeneration reverts silently. `GENERATOR` = the generator owns it, "
              "nothing to lose. Similarity is against the generator's own output at the "
              "same date tag.",
              "",
              "**Nothing is regenerated until Daniil has signed off on the "
              "recommendations below.**",
              ""]
    totals = {}

    for notebook, generator, tag, ga in zip(args.notebook, args.generator, args.tag, gen_args):
        nb_path, gen_path = Path(notebook), Path(generator)
        real = read_cells(nb_path)
        ref = reference_cells(gen_path, ga, nb_path.name)
        rows = classify(real, ref)
        keep = [r for r in rows if r["kind"] in ("DIVERGED", "NEAR")]
        counts = {k: sum(1 for r in rows if r["kind"] == k)
                  for k in ("GENERATOR", "NEAR", "DIVERGED", "EMPTY")}
        totals[tag] = (len(rows), counts, len(ref))

        out.cells.append(nbf.v4.new_markdown_cell(
            f"---\n\n## {nb_path.name}\n\n"
            f"{len(rows)} cells against {len(ref)} generated: "
            f"{counts['GENERATOR']} generator, {counts['NEAR']} edited generator cells, "
            f"{counts['DIVERGED']} hand-written, {counts['EMPTY']} empty. "
            f"The {len(keep)} cells that are not purely the generator's follow."))
        for r in keep:
            head = (f"<!-- {nb_path.name} cell {r['index']} · {r['kind']} "
                    f"(similarity {r['ratio']}) -->\n")
            if r["cell_type"] == "markdown":
                out.cells.append(nbf.v4.new_markdown_cell(head + r["source"]))
            else:
                out.cells.append(nbf.v4.new_code_cell(
                    f"# --- {nb_path.name} cell {r['index']} · {r['kind']} "
                    f"(similarity {r['ratio']}) ---\n" + r["source"]))

        report += [f"## {nb_path.name}", "",
                   f"{len(rows)} cells against {len(ref)} generated by "
                   f"`{gen_path.name} {ga}`.", "",
                   f"| kind | n |", "|---|---|"]
        report += [f"| {k} | {v} |" for k, v in counts.items()]
        report += ["", "| cell | type | kind | sim. | RU | first lines | recommendation |",
                   "|---|---|---|---|---|---|---|"]
        for r in keep:
            lines = [l.strip() for l in r["source"].splitlines() if l.strip()][:2]
            preview = " ⏎ ".join(lines)[:110].replace("|", "\\|")
            report.append(f"| {r['index']} | {r['cell_type'][:2]} | {r['kind']} | "
                          f"{r['ratio']} | {'yes' if r['russian'] else ''} | "
                          f"`{preview}` | {recommend(r).replace('|', '/')} |")
        report.append("")

    Path(args.out_notebook).write_text(nbf.writes(out))
    Path(args.out_report).write_text("\n".join(report))

    print(f"wrote {args.out_notebook} ({len(out.cells)} cells)")
    print(f"wrote {args.out_report}")
    for tag, (n_real, c, n_ref) in totals.items():
        print(f"  {tag}: {n_real} cells vs {n_ref} generated — "
              + ", ".join(f"{k} {v}" for k, v in c.items()))


if __name__ == "__main__":
    sys.exit(main())
