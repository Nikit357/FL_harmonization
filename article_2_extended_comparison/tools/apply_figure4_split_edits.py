#!/usr/bin/env python3
"""Apply the Figure 4 / Supplementary Figure 14 split to the manuscript .docx.

Daniil's decision of 2026-09-20: Figure 4 keeps only two of its four expression-scatter
grids, at full width, and the other two move to a new Supplementary Figure 14. Four full
grids stacked would make the Figma frame about 9,500 px tall, and a 2x2 arrangement
would put the per-facet gene and cohort labels at roughly 4 pt.

That relettering is already in `manuscript/FL_metric_classes_F1000_260917.md`. This
script puts the same changes into the Word file, which has been the main state since
Phase 5, as tracked changes: Accept All gives the split, Reject All restores the
delivered text exactly.

Every target string sits inside one uninterrupted run, so `safe_tracked_replace` from
the nar-review tools handles all of them. The one exception is the new Supplementary
Figure 14 entry, which needs a bold label beside plain prose and is therefore built as
elements and inserted with `wrap_ins`.

    source ~/venvs/collagen_3_11/bin/activate
    cd article_2_extended_comparison
    python tools/apply_figure4_split_edits.py
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2] / ".claude" / "skills"
sys.path.insert(0, str(SKILLS))

import docx  # noqa: E402
from nar_review_tools import safe_tracked_replace  # noqa: E402
import word_rewrite_trackchanges as wt  # noqa: E402

AUTHOR = "Claude (Article 2)"
DATE = "2026-09-20T00:00:00Z"

# Body references: two panels left Figure 4 for the new supplementary figure, and
# everything after them moved up two letters.
REPLACEMENTS = [
    ("12_scanorama returns a cloud with no relation to the input (Figure 4C)",
     "12_scanorama returns a cloud with no relation to the input "
     "(Supplementary Figure 14A)"),
    ("while keeping the within-cohort spread (Figure 4D)",
     "while keeping the within-cohort spread (Supplementary Figure 14B)"),
    ("in the reverse order (Figure 4H)", "in the reverse order (Figure 4F)"),
    ("for 10_mnn and 12_scanorama (Figure 4E, 4F)",
     "for 10_mnn and 12_scanorama (Figure 4C, 4D)"),
    ("which we call agreement-specific (Figure 4G)",
     "which we call agreement-specific (Figure 4E)"),
    # The Figure 4 legend: the four-grid opening becomes a two-grid opening that points
    # at the new supplementary figure, and the remaining panels are relettered.
    ("(A to D) Harmonized against raw expression for the marker panel, one point per "
     "sample, faceted by gene and cohort, with the identity line and a per-facet "
     "Spearman correlation, for one representative of each group: (A) the unharmonized "
     "baseline 01_raw, (B) 13_fsmvn, selected by the published clustermap, (C) "
     "12_scanorama, elected by class M, and (D) 29_combat_ref, elected by class N. (E) "
     "Class M margin",
     "(A and B) Harmonized against raw expression for the marker panel, one point per "
     "sample, faceted by gene and cohort, with the identity line and a per-facet "
     "Spearman correlation: (A) the unharmonized baseline 01_raw and (B) 13_fsmvn, "
     "selected by the published clustermap. The two further representatives, "
     "12_scanorama elected by class M and 29_combat_ref elected by class N, are drawn "
     "on the same axes in Supplementary Figure 14. (C) Class M margin"),
    ("with the 0.75 gate drawn. (F) Methods ranked by median margin",
     "with the 0.75 gate drawn. (D) Methods ranked by median margin"),
    ("isolated group. (G) Change in different-biology agreement",
     "isolated group. (E) Change in different-biology agreement"),
    ("lower right quadrant. (H) Median marker correlation",
     "lower right quadrant. (F) Median marker correlation"),
    ("by imputation and by method. (I) Same-biology agreement",
     "by imputation and by method. (G) Same-biology agreement"),
]

# The paragraph the new entry is appended to, identified by its closing sentence.
SUPP_ANCHOR = "Gene by method clustering of the per-gene marker correlations."
SUPP_LABEL = "Supplementary Figure 14."
SUPP_TEXT = (" Harmonized against raw marker expression for the two remaining "
             "best-approach representatives, 12_scanorama and 29_combat_ref, on the "
             "axes of Figure 4A and 4B.")


def append_supp_entry(paragraph) -> None:
    """Add the bold-labelled Supplementary File 14 sentence as a tracked insertion."""
    runs = [c for c in paragraph if c.tag == wt.qn("w:r")]
    base = runs[-1].find(wt.qn("w:rPr")) if runs else None
    paragraph.append(wt.wrap_ins(
        wt.make_run(" ", base=base),
        wt.make_run(SUPP_LABEL, bold=True, base=base),
        wt.make_run(SUPP_TEXT, base=base),
    ))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--docx",
                    default="manuscript/FL_metric_classes_F1000_260917.docx")
    args = ap.parse_args()

    src = Path(args.docx)
    backup = src.with_name(src.stem + "_pre_fig4split" + src.suffix)

    wt.set_revision_identity(AUTHOR, DATE)
    document = docx.Document(str(src))

    done = {}
    supp_done = False
    for paragraph in document.paragraphs:
        text = paragraph.text
        pending = [(o, n) for o, n in REPLACEMENTS if o in text and o not in done]
        if pending:
            for old, status in safe_tracked_replace(paragraph._p, pending):
                done[old] = status
        if not supp_done and SUPP_ANCHOR in text and SUPP_LABEL not in text:
            append_supp_entry(paragraph._p)
            supp_done = True

    missing = [o for o, _ in REPLACEMENTS if done.get(o) != "ok"]
    if missing or not supp_done:
        for old in missing:
            print(f"  FAILED ({done.get(old, 'not-found')}): {old[:70]}",
                  file=sys.stderr)
        if not supp_done:
            print("  FAILED: the Supplementary Figure 13 paragraph was not found",
                  file=sys.stderr)
        print("nothing written", file=sys.stderr)
        return 1

    if not backup.exists():
        shutil.copy2(src, backup)
        print(f"  backup: {backup.name}")
    document.save(str(src))
    print(f"  {len(REPLACEMENTS)} tracked replacements and 1 tracked insertion "
          f"written to {src.name} as {AUTHOR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
