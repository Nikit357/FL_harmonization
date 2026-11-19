"""
r50_manuscript_tracked_edits.py — tracked edits of the manuscript (plan WP11).

Input : Revised_manuscript/FL_harmonization_article_NARGAB_baseline_260912.docx (read-only)
Output: Revised_manuscript/FL_harmonization_article_NARGAB_tracked_stage<X>_<YYMMDD>.docx

Every change is a genuine Word tracked change (author "Daniil Nikitin"): Accept All gives
the revised text, Reject All gives the baseline byte-for-byte in text. Edits go through
`safe_tracked_replace` (nar_review_tools.py), which only touches runs that are direct
children of a paragraph, so the Mendeley `w:sdt` citations stay untouched. All anchors
are resolved to element references BEFORE the first mutation; each anchor is a body
index of `inputs/baseline_dump.txt` checked against the expected opening words of that
paragraph, so a wrong paragraph stops the script instead of being edited.

STAGE A (this version; nothing here depends on a pod result or a gate answer)
-------------------------------------------------------------------------------
- m4 terminology sweep over every paragraph (body + table cells, never notes):
  "RNA-seq (NGS)" → "RNA-seq"; "NGS platform model" → "sequencing platform model";
  "NGS" → "RNA-seq"; "RNASeq only" → "RNA-seq only" (batch identifiers such as
  RNASeq_FF_PolyA and the quoted code 'RNASeq' are left alone); "Softimpute" →
  "softImpute"; "2 X 2" / "3 X 3" / "3 X 2" → "2 × 2" / "3 × 3" / "3 × 2".
- m1 method count: ¶[13] Abstract "33 harmonization algorithms" → "… (31 analysed)",
  paid for by "Most harmonization tools" → "Most tools" (the abstract is at 199 / 200
  words); ¶[82] "one of 33 harmonization methods (" → "one of 33 implemented
  harmonization methods (31 analysed; ". ¶[80] holds no method count; ¶[217] and ¶[224]
  already say "31 … analyzed" / "33 … implemented" — no edit needed there.
- m2 Table 1 (¶[42]): strategy D type "By biomaterial" → "By biology".
- m3 Figure 4 legend (¶[127]): panel F "KNN imputed S0 dataset" → "KNN-imputed C
  (RNA-seq only) dataset".
- Decision D3: tracked deletion of the composite-score paragraphs ¶[141], ¶[149], ¶[151]
  (its Leek 2010 citation is deleted as a tracked deletion inside the w:sdt; the sdt
  element itself and its text stay) and ¶[153].

STAGE_B_TODO (needs pod results, gate answers or numbers.json; plan §5 WP11 table)
-------------------------------------------------------------------------------
 1. ¶[13]  Abstract: replace the composite / clustermap sentence with the gradient and
           leave-cohort-out results (≤ 200 words).
 2. ¶[36], ¶[38] Methods: A, B, E1–E3 came from the first manual FSQN R run; pointer to
           the leave-strategies-out check; one "real-world" sentence.
 3. ¶[42]  Table 1: two new columns (Cramér's V; % samples in single-diagnosis batches).
 4. new after ¶[61] Methods: confounding diagnostics + gradient (formal λ definition).
 5. ¶[63], ¶[65] Methods: 87 metrics → reduced panel (after gate G1); the four scores.
 6. new after ¶[65] Methods: selection rule + leave-cohort-out design (after gate G2b).
 7. ¶[84]  Results: composition with V / AMI / single-diagnosis / bridging batches.
 8. ¶[87]  Figure 1 legend: panel E replaced; alt text ¶[88].
 9. ¶[102]–[112] Results: reduced panel, 1,993 complete approaches; drop S8 / S10 text.
10. ¶[114] Figure 3 legend (+ alt text ¶[115]).
11. ¶[118] Results: selection rule instead of composite; concordance; leave-strategies-out.
           + the visual check: why each vetoed approach was rejected (Daniil, G2b
           2026-11-04); draft D-1 in stage_b_text_drafts.md.
12. ¶[121] Table 3: new columns; "Reason to include" in terms of the rule.
13. ¶[143], ¶[145] Results: η² recomputed on the reduced panel.
14. ¶[147] Results: radar → four scores with the λ = 0 / λ = 1 anchors.
15. ¶[155] Figure 6 legend (+ alt text ¶[156]).
16. ¶[157]–[170] Results: prediction as a gate; label leakage; tempered biology wording.
17. new after ¶[170] Results: confounding gradient + leave-cohort-out results.
18. ¶[173]–[179] Results: decision tree readouts per leaf (decision D5 if the set changes).
19. ¶[185] Discussion: single "real-world benchmark" paragraph with numbers.
20. ¶[200], ¶[201] Discussion: composite limitation out; leave-cohort-out result in.
21. ¶[203]–[210] Discussion: retitle / shorten; S7 orthogonality numbers on the panel.
22. ¶[232]–[256] Supplementary data list: S1–S18 renumbering sweep (collision-safe, one
           left-to-right pass) + new legends + File 2 / 3 descriptions.
23. All Supplementary Figure citations in the body: the same renumbering sweep.

STAGE B (implemented 2026-11-07, gate G4 answered): the text lives in
`r50_stage_b_text.py` (data only, `{{key}}` placeholders filled from output/numbers.json —
a missing number stops the run). `run_stage_b()` applies, on the stage-A document:
tracked deletions, paragraph rewrites (old paragraph deleted, new one inserted after it),
in-paragraph replacements, new paragraphs / subsections, two Table 1 columns, the rebuilt
Table 3 (rows from output/wp4/selection_after_visual_check.tsv) and the Supplementary
Figure renumbering sweep (old → new map in r50_stage_b_text; replaced right to left at
exact offsets, so a new number never collides with a later old one). No text compares the
revision with the submitted version (Daniil, 2026-11-07).

Usage
-----
python r50_manuscript_tracked_edits.py              # stage A → ..._tracked_stageA_<YYMMDD>.docx
python r99_verify.py Revised_manuscript/<output>.docx
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

REVISION_DIR = Path(__file__).resolve().parent
SKILLS_DIR = REVISION_DIR.parent / ".claude" / "skills"
sys.path.insert(0, str(SKILLS_DIR))

import word_rewrite_trackchanges as wrt  # noqa: E402
from nar_review_tools import safe_tracked_replace  # noqa: E402

BASELINE_DOCX = (
    REVISION_DIR
    / "Revised_manuscript"
    / "FL_harmonization_article_NARGAB_baseline_260912.docx"
)
AUTHOR = "Daniil Nikitin"
NOTE_MARKERS = ("[REVIEWER NOTE]", "[EDITOR NOTE]", "[NAR EDITOR NOTE]")

# ── Edit records ──────────────────────────────────────────────────────────────


@dataclass
class ParagraphEdit:
    """Tracked replacements inside one top-level body paragraph."""

    body_index: int
    expect_prefix: str
    replacements: list[tuple[str, str]]
    reason: str
    element: object = field(default=None, repr=False)


@dataclass
class TableCellEdit:
    """Tracked replacements inside one table cell (row found by its first cell)."""

    body_index: int
    row_first_cell: str
    column: int
    replacements: list[tuple[str, str]]
    reason: str
    element: object = field(default=None, repr=False)


@dataclass
class ParagraphDeletion:
    """Tracked deletion of a whole top-level body paragraph."""

    body_index: int
    expect_prefix: str
    reason: str
    element: object = field(default=None, repr=False)


# Terminology sweep (minor comment m4). Order inside the alternation: the specific
# phrases first, so that "RNA-seq (NGS)" is not split into a bare "NGS" hit.
SWEEP_PATTERN = re.compile(
    r"RNA-seq \(NGS\)|NGS platform model|(?<![A-Za-z0-9_'])NGS(?![A-Za-z0-9_])"
    r"|RNASeq only|Softimpute|(?<!\d)(\d) X (\d)(?!\d)"
)


def sweep_replacement(match: re.Match) -> str:
    """Replacement text for one terminology-sweep hit."""
    text = match.group(0)
    fixed = {
        "RNA-seq (NGS)": "RNA-seq",
        "NGS platform model": "sequencing platform model",
        "NGS": "RNA-seq",
        "RNASeq only": "RNA-seq only",
        "Softimpute": "softImpute",
    }
    if text in fixed:
        return fixed[text]
    return f"{match.group(1)} × {match.group(2)}"


def stage_a_edits() -> list:
    """Stage A records (see the module docstring)."""
    return [
        ParagraphEdit(
            13,
            "Cross-platform harmonization of bulk transcriptomic",
            [
                ("Most harmonization tools are", "Most tools are"),
                (
                    "33 harmonization algorithms",
                    "33 harmonization algorithms (31 analysed)",
                ),
            ],
            "m1: 33 implemented, 31 analysed (abstract word count kept ≤ 200)",
        ),
        ParagraphEdit(
            82,
            "To benchmark publicly available harmonization tools",
            [
                (
                    "one of 33 harmonization methods (",
                    "one of 33 implemented harmonization methods (31 analysed; ",
                )
            ],
            "m1: 33 implemented, 31 analysed",
        ),
        TableCellEdit(
            42,
            "D malignant only",
            1,
            [("By biomaterial", "By biology")],
            "m2: strategy D is a diagnosis-based filter",
        ),
        ParagraphEdit(
            127,
            "Figure 4.",
            [("KNN imputed S0 dataset", "KNN-imputed C (RNA-seq only) dataset")],
            "m3: Figure 4F shows the RNA-seq-only strategy C",
        ),
        ParagraphDeletion(
            141, "To integrate the multi-dimensional metric signals", "D3 composite"
        ),
        ParagraphDeletion(
            149, "We then assessed the contribution of each metric type", "D3 composite"
        ),
        ParagraphDeletion(
            151, "The two top methods after the clustermap best group", "D3 composite"
        ),
        ParagraphDeletion(
            153, "It should be noted that the composite score", "D3 composite"
        ),
    ]


def stage_b_edits() -> list:
    """Stage B records — empty until the results exist (STAGE_B_TODO above)."""
    return []


# ── Helpers ───────────────────────────────────────────────────────────────────


def visible_text(element: object) -> str:
    """Accept-all text (w:t only) beneath an element."""
    return "".join(t.text or "" for t in element.iter(qn("w:t")))


def direct_run_text(paragraph: object) -> str:
    """Text of the runs that are direct children of a paragraph."""
    return "".join(
        "".join(t.text or "" for t in run.findall(qn("w:t")))
        for run in paragraph
        if run.tag == qn("w:r")
    )


def is_note(paragraph: object) -> bool:
    """True for an inserted reviewer / editor note paragraph."""
    return any(marker in visible_text(paragraph) for marker in NOTE_MARKERS)


def span_is_contiguous(paragraph: object, old: str) -> bool:
    """
    True when the first occurrence of `old` lies in runs that are adjacent siblings.

    Parameters
    ----------
    paragraph : w:p element.
    old : the text to be replaced.

    Returns
    -------
    False if a citation (w:sdt) or hyperlink sits between the runs that hold `old`:
    replacing across it would move the citation.
    """
    runs = [c for c in paragraph if c.tag == qn("w:r")]
    texts = ["".join(t.text or "" for t in r.findall(qn("w:t"))) for r in runs]
    joined = "".join(texts)
    start = joined.find(old)
    if start < 0:
        return True  # reported as not-found by safe_tracked_replace
    end, offset, covered = start + len(old), 0, []
    for run, text in zip(runs, texts):
        if offset < end and offset + len(text) > start:
            covered.append(run)
        offset += len(text)
    return only_markers_between(paragraph, covered)


# Elements that may sit between the runs of a replaced span: proofing and bookmark marks
# carry no text and no citation, so crossing them is safe (a w:sdt or hyperlink is not).
HARMLESS_TAGS = {
    qn(tag)
    for tag in (
        "w:proofErr",
        "w:bookmarkStart",
        "w:bookmarkEnd",
        "w:permStart",
        "w:permEnd",
    )
}


def only_markers_between(paragraph: object, covered: list) -> bool:
    """True when nothing but runs and harmless marks lies between the covered runs."""
    children = list(paragraph)
    positions = [children.index(r) for r in covered]
    between = children[positions[0] : positions[-1] + 1]
    return all(c.tag == qn("w:r") or c.tag in HARMLESS_TAGS for c in between)


def tracked_replace_checked(paragraph: object, replacements: list) -> list:
    """`safe_tracked_replace` one replacement at a time, refusing non-contiguous spans."""
    results = []
    for old, new in replacements:
        if not span_is_contiguous(paragraph, old):
            results.append((old, "unsafe-span"))
            continue
        results += safe_tracked_replace(paragraph, [(old, new)])
    return results


def delete_paragraph_with_citations(paragraph: object) -> None:
    """
    Tracked deletion of a paragraph, including the runs inside its citation w:sdt.

    `word_rewrite_trackchanges.delete_paragraph` wraps direct runs and hyperlinks only;
    a citation's runs inside w:sdt/w:sdtContent would survive Accept All. Here they are
    wrapped in w:del too (w:t → w:delText); the w:sdt element and its text are kept, so
    Reject All restores the citation unchanged.
    """
    wrt.delete_paragraph(paragraph)
    delete_inserted_runs(paragraph)
    for content in paragraph.iter(qn("w:sdtContent")):
        for run in list(content.iter(qn("w:r"))):
            if any(a.tag == qn("w:del") for a in run.iterancestors()):
                continue
            for text in run.findall(qn("w:t")):
                text.tag = qn("w:delText")
            wrapper = wrt._rev_attrs(OxmlElement("w:del"))
            run.addprevious(wrapper)
            wrapper.append(run)


def delete_inserted_runs(paragraph: object) -> None:
    """
    Tracked deletion of the runs of earlier insertions (stage A) in a paragraph.

    A run inside w:ins becomes w:ins/w:del/w:r with w:delText ("inserted, then deleted"):
    Accept All removes it, Reject All removes the insertion, so both views stay right.
    """
    for insertion in paragraph.findall(qn("w:ins")):
        for run in list(insertion.findall(qn("w:r"))):
            for text in run.findall(qn("w:t")):
                text.tag = qn("w:delText")
            wrapper = wrt._rev_attrs(OxmlElement("w:del"))
            run.addprevious(wrapper)
            wrapper.append(run)


def reserve_revision_ids(body: object) -> None:
    """Start the revision-id counter above every w:id already in the document."""
    existing = [
        int(value)
        for element in body.iter()
        if (value := element.get(qn("w:id"))) is not None and value.isdigit()
    ]
    wrt._rid[0] = max(existing + [0]) + 1000


def resolve(records: list, body_children: list) -> None:
    """Attach the element of every record; stop if an anchor does not match."""
    for record in records:
        element = body_children[record.body_index]
        if isinstance(record, TableCellEdit):
            rows = [
                row
                for row in element.findall(qn("w:tr"))
                if visible_text(row.findall(qn("w:tc"))[0]).strip()
                == record.row_first_cell
            ]
            if len(rows) != 1:
                raise SystemExit(f"table ¶[{record.body_index}]: row anchor not unique")
            cell = rows[0].findall(qn("w:tc"))[record.column]
            paragraphs = [
                p
                for p in cell.findall(qn("w:p"))
                if record.replacements[0][0] in visible_text(p)
            ]
            if len(paragraphs) != 1:
                raise SystemExit(f"table ¶[{record.body_index}]: cell anchor not found")
            record.element = paragraphs[0]
            continue
        text = visible_text(element).strip()
        if not text.startswith(record.expect_prefix):
            raise SystemExit(
                f"¶[{record.body_index}] starts with {text[:60]!r}, "
                f"expected {record.expect_prefix!r}"
            )
        record.element = element


def sweep_records(body: object, skip: set) -> list[tuple[object, list]]:
    """Terminology-sweep replacements for every paragraph not deleted and not a note."""
    planned = []
    for paragraph in body.iter(qn("w:p")):
        if paragraph in skip or is_note(paragraph):
            continue
        text = direct_run_text(paragraph)
        hits = [
            (m.group(0), sweep_replacement(m)) for m in SWEEP_PATTERN.finditer(text)
        ]
        if hits:
            planned.append((paragraph, hits))
    return planned


# ── Stage B ───────────────────────────────────────────────────────────────────

NUMBERS_PATH = REVISION_DIR / "output" / "numbers.json"
SELECTION_PATH = REVISION_DIR / "output" / "wp4" / "selection_after_visual_check.tsv"
PLACEHOLDER = re.compile(r"\{\{([^}:]+)(?::([^}]+))?\}\}")
SUPP_FIGURE_PATTERN = re.compile(r"Supplementary Figure (\d+)")
HEADING2_TEMPLATE_INDEX = 62  # "Harmonization quality metrics": a Heading2 to copy


def fill_numbers(text: str, numbers: dict) -> str:
    """
    Replace every {{key}} / {{key:fmt}} by its value from numbers.json.

    `fmt` is a Python format spec, or "q" for an FDR / p-value ("< 0.001" below 0.001).
    A key that is missing or not ready stops the run: numbers are never typed.
    """

    def substitute(match: re.Match) -> str:
        key, fmt = match.group(1), match.group(2)
        entry = numbers.get(key)
        if entry is None or entry.get("status") != "ready":
            raise SystemExit(f"number {key!r} is missing in numbers.json (run r45)")
        value = entry["value"]
        if fmt == "q":
            return "< 0.001" if value < 0.001 else f"{value:.2g}"
        return format(value, fmt) if fmt else entry["display"]

    return PLACEHOLDER.sub(substitute, text)


def first_run_rpr(paragraph: object):
    """Run properties of the first direct run (font of the paragraph), or None."""
    for run in paragraph.findall(qn("w:r")):
        rpr = run.find(qn("w:rPr"))
        if rpr is not None:
            return copy.deepcopy(rpr)
    return None


def inserted_paragraph(template: object, text: str, base_rpr=None) -> object:
    """A tracked-inserted paragraph with the paragraph style of `template`."""
    paragraph = OxmlElement("w:p")
    template_ppr = template.find(qn("w:pPr"))
    ppr = copy.deepcopy(template_ppr) if template_ppr is not None else OxmlElement("w:pPr")
    for old_rpr in ppr.findall(qn("w:rPr")):
        ppr.remove(old_rpr)
    mark = OxmlElement("w:rPr")
    mark.append(wrt._rev_attrs(OxmlElement("w:ins")))
    ppr.append(mark)
    paragraph.append(ppr)
    paragraph.append(wrt.wrap_ins(wrt.make_run(text, base=base_rpr)))
    return paragraph


def delete_runs_only(paragraph: object) -> None:
    """Tracked deletion of every run of a paragraph (citations included), keeping its mark."""
    delete_inserted_runs(paragraph)
    for child in list(paragraph):
        if child.tag == qn("w:r"):
            for text in child.findall(qn("w:t")):
                text.tag = qn("w:delText")
            wrapper = wrt._rev_attrs(OxmlElement("w:del"))
            child.addprevious(wrapper)
            wrapper.append(child)
    for container in list(paragraph.iter(qn("w:sdtContent"))) + list(
        paragraph.iter(qn("w:hyperlink"))
    ):
        for run in list(container.iter(qn("w:r"))):
            if any(a.tag == qn("w:del") for a in run.iterancestors()):
                continue
            for text in run.findall(qn("w:t")):
                text.tag = qn("w:delText")
            wrapper = wrt._rev_attrs(OxmlElement("w:del"))
            run.addprevious(wrapper)
            wrapper.append(run)


def tracked_replace_at(paragraph: object, start: int, old: str, new: str) -> str:
    """
    Tracked replacement of `old` at character offset `start` of the direct-run text.

    Same run handling as `safe_tracked_replace`, but at a given offset, so that repeated
    strings ("Supplementary Figure 2" twice) are replaced exactly where they were found.
    Returns "ok" or "unsafe" (span crosses a non-plain run).
    """
    runs = [c for c in paragraph if c.tag == qn("w:r")]
    texts = ["".join(t.text or "" for t in r.findall(qn("w:t"))) for r in runs]
    end, offsets, acc = start + len(old), [], 0
    for text in texts:
        offsets.append(acc)
        acc += len(text)
    assert "".join(texts)[start:end] == old
    covered = [
        i for i, t in enumerate(texts) if offsets[i] < end and offsets[i] + len(t) > start
    ]
    first, last = covered[0], covered[-1]
    if not only_markers_between(paragraph, [runs[i] for i in covered]):
        return "unsafe"
    base = runs[first].find(qn("w:rPr"))
    prefix = texts[first][: start - offsets[first]]
    suffix = texts[last][end - offsets[last]:]
    pieces = []
    if prefix:
        pieces.append(wrt.make_run(prefix, base=base))
    pieces.append(wrt.wrap_del(wrt.make_del_run(old, base=base)))
    pieces.append(wrt.wrap_ins(wrt.make_run(new, base=base)))
    if suffix:
        pieces.append(wrt.make_run(suffix, base=base))
    for piece in pieces:
        runs[first].addprevious(piece)
    for i in covered:
        paragraph.remove(runs[i])
    return "ok"


def supplementary_sweep(paragraphs: list, figure_map: dict) -> int:
    """Renumber "Supplementary Figure N" in the direct-run text, right to left."""
    n_hits = 0
    for paragraph in paragraphs:
        text = direct_run_text(paragraph)
        hits = list(SUPP_FIGURE_PATTERN.finditer(text))
        for match in reversed(hits):
            old_number = int(match.group(1))
            new_number = figure_map[old_number]
            if new_number is None:
                raise SystemExit(
                    f"removed Supplementary Figure {old_number} still cited: {text[:80]!r}"
                )
            if new_number == old_number:
                continue
            status = tracked_replace_at(
                paragraph,
                match.start(),
                match.group(0),
                f"Supplementary Figure {new_number}",
            )
            if status != "ok":
                raise SystemExit(f"unsafe renumbering span in {text[:80]!r}")
            n_hits += 1
    return n_hits


def append_tracked_column(table: object, header: str, values: list[str]) -> None:
    """Append one tracked-inserted column (w:cellIns + w:ins text) to a table."""
    grid = table.find(qn("w:tblGrid"))
    grid_col = OxmlElement("w:gridCol")
    grid_col.set(qn("w:w"), "1300")
    grid.append(grid_col)
    rows = table.findall(qn("w:tr"))
    texts = [header] + list(values)
    if len(texts) != len(rows):
        raise SystemExit(f"column length {len(texts)} != {len(rows)} rows")
    for row, text in zip(rows, texts):
        model = row.findall(qn("w:tc"))[-1]
        cell = OxmlElement("w:tc")
        cell_pr = OxmlElement("w:tcPr")
        width = OxmlElement("w:tcW")
        width.set(qn("w:w"), "1300")
        width.set(qn("w:type"), "dxa")
        cell_pr.append(width)
        cell_pr.append(wrt._rev_attrs(OxmlElement("w:cellIns")))
        cell.append(cell_pr)
        model_paragraph = model.find(qn("w:p"))
        paragraph = OxmlElement("w:p")
        if model_paragraph is not None and model_paragraph.find(qn("w:pPr")) is not None:
            paragraph.append(copy.deepcopy(model_paragraph.find(qn("w:pPr"))))
        base = first_run_rpr(model_paragraph) if model_paragraph is not None else None
        paragraph.append(wrt.wrap_ins(wrt.make_run(text, base=base)))
        cell.append(paragraph)
        row.append(cell)


def table1_columns(table: object, numbers: dict, text_module) -> None:
    """Cramér's V and % samples in single-diagnosis batches per strategy (Table 1)."""
    v_values, pct_values = [], []
    for row in table.findall(qn("w:tr"))[1:]:
        first_cell = visible_text(row.findall(qn("w:tc"))[0]).strip()
        strategy = text_module.TABLE1_ROW_STRATEGIES[first_cell.split()[0]]
        v_values.append(fill_numbers(f"{{{{table1_V__{strategy}:.2f}}}}", numbers))
        pct_values.append(
            fill_numbers(f"{{{{table1_pct_single_dx__{strategy}:.1f}}}}", numbers)
        )
    append_tracked_column(table, text_module.TABLE1_HEADERS[0], v_values)
    append_tracked_column(table, text_module.TABLE1_HEADERS[1], pct_values)


def value_range(values, fmt: str = "{:.2f}") -> str:
    """'0.95' when all values round alike, else '0.94–0.96'."""
    low, high = fmt.format(min(values)), fmt.format(max(values))
    return low if low == high else f"{low}–{high}"


def table3_rows(text_module) -> list[list[str]]:
    """Header + one row per scenario × method of the recommended approaches."""
    import pandas as pd

    selection = pd.read_csv(SELECTION_PATH, sep="\t")
    selection = selection[selection["visual_check"] == "accepted"]
    imputation_names = {"strict": "no imputation", "knn": "KNN", "softimpute": "softImpute"}
    rows = [list(text_module.TABLE3_HEADER)]
    for scenario in text_module.TABLE3_SCENARIO_NAMES:
        members = selection[selection["scenario"] == scenario]
        method_order = members.groupby("method")["front_rank"].min().sort_values().index
        for method in method_order:
            group = members[members["method"] == method].sort_values("front_rank")
            approaches = "; ".join(
                f"{row.strat.split('_')[0]}, {imputation_names[row.imp]}"
                + (" + post-removal" if str(row.post_rm) == "True" else "")
                for row in group.itertuples()
            )
            task = "; DLBCL vs FL" if (group["gate_N_classes"] == 2).all() else ""
            prediction = (
                f"{value_range(group['N_gate'])} ({value_range(group['N_raw'])}){task}"
            )
            rows.append(
                [
                    text_module.TABLE3_SCENARIO_NAMES[scenario],
                    group["method_display"].iloc[0],
                    approaches,
                    value_range(group["L"]),
                    prediction,
                    text_module.TABLE3_VISUAL[(scenario, method)],
                ]
            )
    return rows


def rebuild_table3(table: object, rows: list[list[str]]) -> None:
    """Old cell content → tracked deletion; new content → tracked insertion; extra rows
    are copies of the last row marked as inserted (w:trPr/w:ins)."""
    old_rows = table.findall(qn("w:tr"))
    spare_row = copy.deepcopy(old_rows[-1])
    if len(rows) < len(old_rows):
        raise SystemExit("Table 3 has fewer new rows than old rows")
    for row, cells in zip(old_rows, rows):
        tcs = row.findall(qn("w:tc"))
        if len(tcs) != len(cells):
            raise SystemExit(f"Table 3: {len(tcs)} cells, {len(cells)} values")
        for tc, text in zip(tcs, cells):
            paragraphs = tc.findall(qn("w:p"))
            base = first_run_rpr(paragraphs[0])
            for paragraph in paragraphs:
                delete_runs_only(paragraph)
            paragraphs[0].append(wrt.wrap_ins(wrt.make_run(text, base=base)))
    for cells in rows[len(old_rows):]:
        row = copy.deepcopy(spare_row)
        tr_pr = row.find(qn("w:trPr"))
        if tr_pr is None:
            tr_pr = OxmlElement("w:trPr")
            row.insert(0, tr_pr)
        tr_pr.append(wrt._rev_attrs(OxmlElement("w:ins")))
        for tc, text in zip(row.findall(qn("w:tc")), cells):
            paragraphs = tc.findall(qn("w:p"))
            base = first_run_rpr(paragraphs[0])
            for paragraph in paragraphs:
                for child in list(paragraph):
                    if child.tag != qn("w:pPr"):
                        paragraph.remove(child)
            for extra in paragraphs[1:]:
                tc.remove(extra)
            paragraphs[0].append(wrt.wrap_ins(wrt.make_run(text, base=base)))
        table.append(row)


def check_prefix(element: object, index: int, prefix: str) -> None:
    """Stop if the anchor paragraph does not start with the expected words."""
    text = visible_text(element).strip()
    if not text.startswith(prefix):
        raise SystemExit(f"¶[{index}] starts with {text[:60]!r}, expected {prefix!r}")


def run_stage_b(document: object) -> int:
    """Apply every stage-B edit (r50_stage_b_text) to the stage-A document."""
    import r50_stage_b_text as text_module

    numbers = json.loads(NUMBERS_PATH.read_text())
    body = document.element.body
    children = list(body)  # every anchor resolved before any mutation
    heading_template = children[HEADING2_TEMPLATE_INDEX]
    check_prefix(heading_template, HEADING2_TEMPLATE_INDEX, "Harmonization quality metrics")
    rewrites = {**text_module.REWRITES, **text_module.SUPP_LEGEND_REWRITES}
    deletions = {
        **text_module.DELETIONS,
        **text_module.SUPP_LEGEND_DELETIONS,
        **text_module.SUPP_LEGEND_ORPHANS,
    }
    for index, (prefix, _) in {**rewrites, **text_module.REPLACEMENTS}.items():
        check_prefix(children[index], index, prefix)
    for index, prefix in deletions.items():
        check_prefix(children[index], index, prefix)
    s15_legend = children[252]
    check_prefix(s15_legend, 252, "Supplementary Figure 19.")
    table1, table3 = children[42], children[121]
    assert table1.tag == qn("w:tbl") and table3.tag == qn("w:tbl")
    removed = set(deletions) | set(rewrites)
    sweep_targets = [
        element
        for index, element in enumerate(children)
        if element.tag == qn("w:p") and index not in removed and not is_note(element)
    ]
    # Fill every placeholder first, so that a missing number stops before any edit.
    filled_rewrites = {
        i: [fill_numbers(t, numbers) for t in texts] for i, (_, texts) in rewrites.items()
    }
    filled_replacements = {
        i: [(old, fill_numbers(new, numbers)) for old, new in pairs]
        for i, (_, pairs) in text_module.REPLACEMENTS.items()
    }
    filled_inserts = {
        i: [(style, fill_numbers(t, numbers)) for style, t in items]
        for i, items in text_module.INSERT_AFTER.items()
    }
    new_legends = [fill_numbers(t, numbers) for t in text_module.SUPP_NEW_LEGENDS_AFTER_S15]

    n_edits, last_element = 0, {}
    for index in sorted(deletions):
        delete_paragraph_with_citations(children[index])
        n_edits += 1
    for index, texts in sorted(filled_rewrites.items()):
        old = children[index]
        base = first_run_rpr(old)
        style_template = heading_template if wrt.style_of(old).lower().startswith(
            "heading"
        ) else old
        delete_paragraph_with_citations(old)
        anchor = old
        for text in texts:
            new = inserted_paragraph(style_template, text, base)
            anchor.addnext(new)
            anchor = new
        last_element[index] = anchor
        n_edits += 1
    problems = []
    for index, pairs in sorted(filled_replacements.items()):
        for old, status in tracked_replace_checked(children[index], pairs):
            n_edits += status == "ok"
            if status != "ok":
                problems.append((index, old[:60], status))
    for index, items in sorted(filled_inserts.items()):
        anchor = last_element.get(index, children[index])
        body_template = children[index]
        base = first_run_rpr(body_template)
        if base is None:
            base = first_run_rpr(children[index - 2])
        for style, text in items:
            template = heading_template if style == "Heading2" else body_template
            new = inserted_paragraph(template, text, None if style else base)
            anchor.addnext(new)
            anchor = new
            n_edits += 1
    anchor, base = s15_legend, first_run_rpr(s15_legend)
    for text in new_legends:
        new = inserted_paragraph(s15_legend, text, base)
        anchor.addnext(new)
        anchor = new
        n_edits += 1
    if problems:
        for problem in problems:
            print("PROBLEM", problem)
        raise SystemExit(f"{len(problems)} stage-B replacements not applied; nothing saved")
    table1_columns(table1, numbers, text_module)
    rebuild_table3(table3, table3_rows(text_module))
    n_sweep = supplementary_sweep(sweep_targets, text_module.SUPPLEMENTARY_FIGURE_MAP)
    print(f"stage B: {n_edits} paragraph edits, Table 1 + Table 3, {n_sweep} renumbered")
    return n_edits + n_sweep


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    """Apply the stage's edits and save a new docx."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--stage", choices=["A", "B"], default="A")
    parser.add_argument("--input", default=None, help="default: baseline (stage A)")
    parser.add_argument("--date", default=dt.date.today().strftime("%y%m%d"))
    args = parser.parse_args()

    source = Path(args.input) if args.input else BASELINE_DOCX
    output = (
        REVISION_DIR
        / "Revised_manuscript"
        / f"FL_harmonization_article_NARGAB_tracked_stage{args.stage}_{args.date}.docx"
    )
    iso_date = dt.datetime.strptime(args.date, "%y%m%d").strftime("%Y-%m-%dT00:00:00Z")
    wrt.set_revision_identity(AUTHOR, iso_date)

    if args.stage == "B" and args.input is None:
        stage_a = sorted((REVISION_DIR / "Revised_manuscript").glob("*_tracked_stageA_*.docx"))
        source = stage_a[-1]
    document = docx.Document(str(source))
    body = document.element.body
    reserve_revision_ids(body)
    if args.stage == "B":
        n_edits = run_stage_b(document)
        output.parent.mkdir(parents=True, exist_ok=True)
        document.save(str(output))
        print(f"{n_edits} tracked edits on {source.name} → {output}")
        return
    records = stage_a_edits() if args.stage == "A" else stage_b_edits()
    resolve(records, list(body))  # every anchor resolved before any mutation
    deleted = {r.element for r in records if isinstance(r, ParagraphDeletion)}
    sweep = sweep_records(body, deleted) if args.stage == "A" else []

    problems, n_ok = [], 0
    for record in records:
        if isinstance(record, ParagraphDeletion):
            delete_paragraph_with_citations(record.element)
            n_ok += 1
            print(f"deleted ¶[{record.body_index}] ({record.reason})")
            continue
        for old, status in tracked_replace_checked(record.element, record.replacements):
            print(f"¶[{record.body_index}] {status:12s} {old!r}")
            n_ok += status == "ok"
            if status != "ok":
                problems.append((record.body_index, old, status))
    for paragraph, hits in sweep:
        for old, status in tracked_replace_checked(paragraph, hits):
            n_ok += status == "ok"
            if status != "ok":
                problems.append(("sweep", old, status))
    print(
        f"terminology sweep: {sum(len(h) for _, h in sweep)} hits in {len(sweep)} paragraphs"
    )

    if problems:
        for problem in problems:
            print("PROBLEM", problem)
        raise SystemExit(f"{len(problems)} edits not applied; nothing saved")
    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output))
    print(f"{n_ok} tracked edits → {output}")


if __name__ == "__main__":
    main()
