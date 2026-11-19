"""
r00_baseline_ledger.py — the "never up" reference of the revision (plan WP0 step 0.5).

Reads the frozen baseline copy
    Revised_manuscript/FL_harmonization_article_NARGAB_baseline_260912.docx
and writes
    output/ledger_baseline.tsv         words / estimated lines per section
    output/ledger_baseline_totals.json totals + numbers of figures, tables, supp items

Lines are estimated as ceil(characters / 90) per paragraph (revision_lib.CHARS_PER_LINE);
r90_ledger.py uses the same estimator on the accept-all text of the revised docx, so the
comparison is like for like even though Word's real line breaks are not known here.

Usage
-----
python r00_baseline_ledger.py
"""

from __future__ import annotations

import json

import revision_lib as rl

BASELINE_DOCX = (
    rl.REVISION_DIR
    / "Revised_manuscript/FL_harmonization_article_NARGAB_baseline_260912.docx"
)


def main() -> None:
    """Compute and save the baseline ledger."""
    per_section, totals = rl.docx_ledger(BASELINE_DOCX)
    rl.OUTPUT_DIR.mkdir(exist_ok=True)
    per_section.to_csv(rl.OUTPUT_DIR / "ledger_baseline.tsv", sep="\t", index=False)
    with open(rl.OUTPUT_DIR / "ledger_baseline_totals.json", "w") as handle:
        json.dump(totals, handle, indent=1)
    print(json.dumps(totals, indent=1))


if __name__ == "__main__":
    main()
