"""
r90_ledger.py — "nothing grew" check of the revised manuscript (plan WP14, rule 4).

Computes the ledger of the accept-all text of a revised docx with
`revision_lib.docx_ledger` (the same estimator as r00: words, lines estimated as
ceil(characters / 90) per paragraph, numbers of main figures / tables and of
supplementary figures / files) and compares every total with the baseline reference
`output/ledger_baseline_totals.json`.

Exit code 1 if ANY total is larger than in the baseline (Daniil's hard constraint:
lines, figures and tables may go down, never up); 0 otherwise.

Output: output/wp14/ledger_<docx stem>.tsv (one row per total: baseline, revised, delta,
status) and output/wp14/ledger_<docx stem>_sections.tsv (per section, revised).

Usage
-----
python r90_ledger.py                       # newest Revised_manuscript/*tracked*.docx
python r90_ledger.py Revised_manuscript/<file>.docx
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

import revision_lib as rl

MANUSCRIPT_DIR = rl.REVISION_DIR / "Revised_manuscript"
BASELINE_DOCX = MANUSCRIPT_DIR / "FL_harmonization_article_NARGAB_baseline_260912.docx"
BASELINE_TOTALS = rl.OUTPUT_DIR / "ledger_baseline_totals.json"
OUT_DIR = rl.OUTPUT_DIR / "wp14"


def default_docx() -> Path:
    """Newest tracked docx of Revised_manuscript/, else the baseline itself."""
    tracked = sorted(
        MANUSCRIPT_DIR.glob("*tracked*.docx"), key=lambda p: p.stat().st_mtime
    )
    return tracked[-1] if tracked else BASELINE_DOCX


def compare_totals(baseline: dict, revised: dict) -> pd.DataFrame:
    """
    One row per total with the delta and a PASS / FAIL status.

    Parameters
    ----------
    baseline, revised : totals dicts of `rl.docx_ledger`.

    Returns
    -------
    DataFrame total, baseline, revised, delta, status (FAIL when revised > baseline).
    """
    rows = [
        {
            "total": key,
            "baseline": baseline[key],
            "revised": revised.get(key),
            "delta": revised.get(key, 0) - baseline[key],
        }
        for key in baseline
    ]
    table = pd.DataFrame(rows)
    table["status"] = ["FAIL" if d > 0 else "PASS" for d in table["delta"]]
    return table


def main() -> None:
    """Ledger of one docx against the baseline; exit 1 if anything grew."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("docx", nargs="?", default=None)
    args = parser.parse_args()
    path = Path(args.docx) if args.docx else default_docx()

    baseline = json.loads(BASELINE_TOTALS.read_text())
    per_section, totals = rl.docx_ledger(path)
    table = compare_totals(baseline, totals)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT_DIR / f"ledger_{path.stem}.tsv", sep="\t", index=False)
    per_section.to_csv(
        OUT_DIR / f"ledger_{path.stem}_sections.tsv", sep="\t", index=False
    )
    print(f"ledger of {path.name}")
    print(table.to_string(index=False))
    grew = table[table["status"] == "FAIL"]
    if len(grew):
        print(f"FAIL: {len(grew)} totals grew: {', '.join(grew['total'])}")
        sys.exit(1)
    print("PASS: nothing grew")


if __name__ == "__main__":
    main()
