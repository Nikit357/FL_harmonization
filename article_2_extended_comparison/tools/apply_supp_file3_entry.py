#!/usr/bin/env python3
"""Insert the Supplementary File 3 entry into the manuscript .docx as a tracked change.

Phase 6 built a third supplementary workbook (the marker gene panel, behind
Supplementary Figures 11 and 13), so the "Supplementary material" section has to name
it. Phase 5 made the Word file the main state, so the sentence goes in as a Word
tracked insertion: Accept All gives the new sentence, Reject All restores the file
exactly as delivered.

The edit is a raw `word/document.xml` splice rather than a python-docx edit because
python-docx has no tracked-change API, and the target paragraph is plain pandoc output
with no Mendeley `w:sdt` field to damage.

    source ~/venvs/collagen_3_11/bin/activate
    cd article_2_extended_comparison
    python tools/apply_supp_file3_entry.py
"""
from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

AUTHOR = "Claude (Article 2)"
DATE = "2026-09-20T00:00:00Z"
REVISION_ID = 9001

# The run that currently follows the Supplementary File 2 sentence. The insertion goes
# immediately before it, so the new sentence lands between the File 2 entry and the
# closing pointer to the legend file.
ANCHOR = ('<w:r><w:t xml:space="preserve">Full legends with alt text are provided in'
          '</w:t></w:r>')

SENTENCE = ("The marker gene panel behind Supplementary Figures 11 and 13: five sheets "
            "covering the coverage gate sweep, the quality gate grid, the per-gene "
            "correlation summary with signature membership, and the genes of the "
            "narrow panel.")

INSERTION = (
    f'<w:ins w:id="{REVISION_ID}" w:author="{AUTHOR}" w:date="{DATE}">'
    '<w:r><w:rPr><w:bCs/><w:b/></w:rPr>'
    '<w:t xml:space="preserve">Supplementary File 3.</w:t></w:r>'
    '<w:r><w:t xml:space="preserve"> </w:t></w:r>'
    f'<w:r><w:t xml:space="preserve">{SENTENCE}</w:t></w:r>'
    '<w:r><w:t xml:space="preserve"> </w:t></w:r>'
    '</w:ins>'
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--docx",
                    default="manuscript/FL_metric_classes_F1000_260917.docx")
    ap.add_argument("--backup", default=None,
                    help="where to copy the untouched file (default: alongside, "
                         "suffixed _pre_suppfile3)")
    args = ap.parse_args()

    src = Path(args.docx)
    backup = Path(args.backup) if args.backup else src.with_name(
        src.stem + "_pre_suppfile3" + src.suffix)

    with zipfile.ZipFile(src) as z:
        parts = {name: z.read(name) for name in z.namelist()}
    doc = parts["word/document.xml"].decode("utf-8")

    if "Supplementary File 3." in doc:
        print("already applied; nothing to do")
        return 0
    if doc.count(ANCHOR) != 1:
        print(f"anchor matched {doc.count(ANCHOR)} times, expected exactly 1 -- "
              "the paragraph has changed; inspect before editing", file=sys.stderr)
        return 1

    if not backup.exists():
        shutil.copy2(src, backup)
        print(f"  backup: {backup.name}")

    parts["word/document.xml"] = doc.replace(ANCHOR, INSERTION + ANCHOR).encode("utf-8")
    with zipfile.ZipFile(src, "w", zipfile.ZIP_DEFLATED) as z:
        for name, blob in parts.items():
            z.writestr(name, blob)

    print(f"  inserted one tracked change into {src.name} as {AUTHOR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
