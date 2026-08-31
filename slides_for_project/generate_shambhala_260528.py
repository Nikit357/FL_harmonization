"""
Generate supervisor_slides_shambhala_260528.pptx
Based on content in supervisor_slides_shambhala_260528.md
Replicates style from supervisor_slides_260428.pptx
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from lxml import etree
import copy

# ── Color palette ────────────────────────────────────────────────────────────
C_NAVY = RGBColor(0x1F, 0x3A, 0x5F)   # header fill
C_BLUE = RGBColor(0x2E, 0x6D, 0xA4)   # badge fill, table header, section accent
C_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
C_TEXT = RGBColor(0x1A, 0x1A, 0x1A)   # default body text
C_RED = RGBColor(0xC0, 0x39, 0x2B)    # DLBCL / warning
C_GREEN = RGBColor(0x1E, 0x7A, 0x46)  # positive result
C_ORANGE = RGBColor(0xD3, 0x7C, 0x00) # insight box text
C_LIGHT_BLUE = RGBColor(0xAA, 0xCC, 0xEE)  # subtitle
C_SUBTITLE2 = RGBColor(0xCC, 0xDD, 0xEE)
C_AUTHOR = RGBColor(0x99, 0xBB, 0xDD)

BG_INSIGHT = RGBColor(0xFF, 0xF0, 0xD0)  # insight box fill
BG_GREEN = RGBColor(0xE8, 0xF4, 0xE8)    # green box fill
BG_BLUE = RGBColor(0xF0, 0xF6, 0xFF)     # card fill
BG_CODE = RGBColor(0xF4, 0xF4, 0xF4)     # code block fill
BG_WHITE = RGBColor(0xFF, 0xFF, 0xFF)

# ── Slide dimensions ─────────────────────────────────────────────────────────
SW = 12188952   # slide width  (EMU) ~ 13.33"
SH = 6858000    # slide height (EMU) ~  7.50"
HDR_H = 1005840     # header bar height
MARGIN = 365760     # left margin
MARGIN_R = 228600   # right margin
CONTENT_TOP = 1097280   # content area top
CONTENT_H = SH - CONTENT_TOP - MARGIN  # ~5,394,960 EMU
CONTENT_W = SW - MARGIN - MARGIN_R     # ~11,594,592 EMU

# Badge right edge constants
BADGE_W = 640080
BADGE_H = 411480
BADGE_L = SW - BADGE_W
BADGE_T = 91440


# ── Helpers ──────────────────────────────────────────────────────────────────

def _set_fill(shape, color: RGBColor):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color


def _add_header(slide, title_text: str, slide_num: int):
    """Add the dark-navy header bar + white title text + slide-number badge."""
    # Header rectangle
    hdr = slide.shapes.add_shape(
        1, 0, 0, SW, HDR_H
    )
    hdr.line.fill.background()
    _set_fill(hdr, C_NAVY)

    # Slide number badge
    badge = slide.shapes.add_shape(1, BADGE_L, BADGE_T, BADGE_W, BADGE_H)
    badge.line.fill.background()
    _set_fill(badge, C_BLUE)
    tf = badge.text_frame
    tf.word_wrap = False
    para = tf.paragraphs[0]
    para.alignment = PP_ALIGN.CENTER
    run = para.add_run()
    run.text = str(slide_num)
    run.font.size = Pt(12)
    run.font.bold = True
    run.font.color.rgb = C_WHITE

    # Title text box
    title_box = slide.shapes.add_textbox(MARGIN_R, 45720, SW - MARGIN_R * 2, 640080)
    tf = title_box.text_frame
    tf.word_wrap = True
    para = tf.paragraphs[0]
    para.alignment = PP_ALIGN.LEFT
    run = para.add_run()
    run.text = title_text
    run.font.size = Pt(26)
    run.font.bold = True
    run.font.color.rgb = C_WHITE


def _add_textbox(slide, left, top, width, height, text, size=14, bold=False,
                 color=None, wrap=True, align=PP_ALIGN.LEFT, italic=False):
    """Add a simple single-run text box."""
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = wrap
    para = tf.paragraphs[0]
    para.alignment = align
    run = para.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color or C_TEXT
    return tb


def _add_bullets(slide, left, top, width, height, items, base_size=13,
                 color=None):
    """
    items: list of (level, text, bold, color_override)
    level 0 = bullet, level 1 = sub-bullet
    """
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True

    first = True
    for level, text, bold, col in items:
        if first:
            para = tf.paragraphs[0]
            first = False
        else:
            para = tf.add_paragraph()
        indent = "  " * level
        bullet = "• " if level == 0 else "  – "
        para.alignment = PP_ALIGN.LEFT
        run = para.add_run()
        run.text = indent + bullet + text
        sz = base_size if level == 0 else base_size - 1
        run.font.size = Pt(sz)
        run.font.bold = bold
        run.font.color.rgb = col or color or C_TEXT
    return tb


def _add_code_block(slide, left, top, width, height, code_text, font_size=8.5):
    """Add a monospace code block with light-gray background."""
    # Background rectangle
    bg = slide.shapes.add_shape(1, left, top, width, height)
    bg.line.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
    bg.line.width = Pt(0.5)
    _set_fill(bg, BG_CODE)

    # Text box on top
    pad = 91440  # ~0.1"
    tb = slide.shapes.add_textbox(
        left + pad, top + pad, width - pad * 2, height - pad * 2
    )
    tf = tb.text_frame
    tf.word_wrap = False

    first = True
    for line in code_text.split("\n"):
        if first:
            para = tf.paragraphs[0]
            first = False
        else:
            para = tf.add_paragraph()
        run = para.add_run()
        run.text = line
        run.font.name = "Courier New"
        run.font.size = Pt(font_size)
        run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
    return tb


def _add_table(slide, left, top, width, height, headers, rows,
               col_widths=None, font_size=10, header_color=None):
    """
    Add a styled table.
    headers: list of str
    rows: list of list of str
    col_widths: list of fractions summing to 1.0 (or None for equal)
    """
    n_rows = len(rows) + 1  # +1 for header
    n_cols = len(headers)

    tbl_shape = slide.shapes.add_table(n_rows, n_cols, left, top, width, height)
    tbl = tbl_shape.table

    # Set column widths
    if col_widths:
        for i, frac in enumerate(col_widths):
            tbl.columns[i].width = int(width * frac)

    hdr_fill = header_color or C_BLUE

    # Header row
    for j, hdr in enumerate(headers):
        cell = tbl.cell(0, j)
        cell.fill.solid()
        cell.fill.fore_color.rgb = hdr_fill
        tf = cell.text_frame
        para = tf.paragraphs[0]
        run = para.add_run()
        run.text = hdr
        run.font.size = Pt(font_size)
        run.font.bold = True
        run.font.color.rgb = C_WHITE

    # Data rows
    for i, row in enumerate(rows):
        bg = BG_WHITE if i % 2 == 0 else RGBColor(0xF7, 0xF9, 0xFF)
        for j, cell_text in enumerate(row):
            cell = tbl.cell(i + 1, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg
            tf = cell.text_frame
            para = tf.paragraphs[0]
            run = para.add_run()
            run.text = cell_text
            run.font.size = Pt(font_size)
            run.font.color.rgb = C_TEXT

    return tbl_shape


def _add_insight_box(slide, left, top, width, height, text, font_size=11,
                     bg=None, text_color=None):
    """Add a highlighted insight/note box."""
    box = slide.shapes.add_shape(1, left, top, width, height)
    box.line.fill.background()
    _set_fill(box, bg or BG_INSIGHT)
    tb = slide.shapes.add_textbox(
        left + 91440, top + 45720, width - 182880, height - 91440
    )
    tf = tb.text_frame
    tf.word_wrap = True
    para = tf.paragraphs[0]
    run = para.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = True
    run.font.color.rgb = text_color or C_ORANGE


# ── Slide builders ────────────────────────────────────────────────────────────

def make_title_slide(prs):
    slide_layout = prs.slide_layouts[6]  # Blank
    slide = prs.slides.add_slide(slide_layout)

    # Background
    bg = slide.shapes.add_shape(1, 0, 0, SW, SH)
    bg.line.fill.background()
    _set_fill(bg, C_NAVY)

    # Accent bar at bottom
    bar = slide.shapes.add_shape(1, 0, SH - 73152, SW, 73152)
    bar.line.fill.background()
    _set_fill(bar, C_BLUE)

    # Main title
    title_tb = slide.shapes.add_textbox(731520, 1371600, 10698480, 1645920)
    tf = title_tb.text_frame
    tf.word_wrap = True
    para = tf.paragraphs[0]
    run = para.add_run()
    run.text = "Supervisor Update:\nShambhala Harmonization"
    run.font.size = Pt(34)
    run.font.bold = True
    run.font.color.rgb = C_WHITE

    # Subtitle
    sub_tb = slide.shapes.add_textbox(731520, 3017520, 10698480, 457200)
    tf = sub_tb.text_frame
    tf.word_wrap = True
    para = tf.paragraphs[0]
    run = para.add_run()
    run.text = "Containerization · Parallelization · Speed-up · Full Benchmark Run (1,296 harmonizations)"
    run.font.size = Pt(18)
    run.font.color.rgb = C_LIGHT_BLUE

    # Description
    desc_tb = slide.shapes.add_textbox(1371600, 3566160, 9418320, 1097280)
    tf = desc_tb.text_frame
    tf.word_wrap = True
    para = tf.paragraphs[0]
    run = para.add_run()
    run.text = (
        "Pure-Python rewrite (no R / rpy2)  ·  30-worker parallelization  ·  "
        "A_E speed-up: 8.6× lab / ~10× real-world  ·  Metrics pipeline ~45% complete"
    )
    run.font.size = Pt(14)
    run.font.color.rgb = C_SUBTITLE2

    # Author line
    auth_tb = slide.shapes.add_textbox(731520, 5303520, 10698480, 365760)
    tf = auth_tb.text_frame
    tf.word_wrap = True
    para = tf.paragraphs[0]
    run = para.add_run()
    run.text = "Daniil Nikitin  ·  BostonGene  ·  2026-05-28"
    run.font.size = Pt(13)
    run.font.color.rgb = C_AUTHOR


def make_slide2_overview(prs):
    """Slide 1 — Two Weeks of Work"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, "Overview: Two Weeks of Work", 1)

    items = [
        (0, "Shambhala containerization — pure-Python rewrite, no R, no rpy2", True, C_BLUE),
        (0, "Parallelization & speed-up research — 9 combinations tested; A_E approved and deployed", True, C_BLUE),
        (0, "Full benchmark run — 1,296 harmonizations completed; metrics calculation ~45% done", True, C_BLUE),
    ]
    _add_textbox(slide, MARGIN, CONTENT_TOP, CONTENT_W, 400000,
                 "Three workstreams completed:", 14, bold=True, color=C_NAVY)
    _add_bullets(slide, MARGIN, CONTENT_TOP + 400000, CONTENT_W, 1200000,
                 items, base_size=14)

    _add_textbox(slide, MARGIN, CONTENT_TOP + 1700000, CONTENT_W, 300000,
                 "Timeline:", 14, bold=True, color=C_NAVY)

    timeline = [
        (0, "May 13 — containerized pipeline passes all 30 tests", False, C_TEXT),
        (0, "May 17 — first Shambhala runs start on K8s pod", False, C_TEXT),
        (0, "May 22 — A_E speed-up deployed; throughput jumps ~10×", False, C_GREEN),
        (0, "May 24–26 — metrics calculation running", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP + 2050000, CONTENT_W, 1200000,
                 timeline, base_size=13)

    headers = ["Metric", "Status"]
    rows = [
        ["Expression files harmonized", "1,296 / 1,296  (100% ✓)"],
        ["Metrics calculated", "579 / 1,296  (~45%)"],
        ["Speed-up gain (A_E)", "~8.6× lab  /  ~10× real-world"],
        ["Test suite", "69 tests pass"],
    ]
    _add_table(slide, MARGIN, CONTENT_TOP + 3400000,
               CONTENT_W, 1400000, headers, rows,
               col_widths=[0.45, 0.55], font_size=12)


def make_slide3_original_pipeline(prs):
    """Slide 2 — Original Pipeline"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, "Original Pipeline: Why It Had to Change", 2)

    code = (
        "R wrapper (Shambhala2.R)\n"
        "  → writes P_prim.txt to disk     — merged [Input + P] matrix for QN\n"
        "  → writes args.txt to disk       — 3 integers: NH, NP, k\n"
        "  → spawns Octave subprocess      — Octave reads P_prim.txt and args.txt\n"
        "  → Octave writes Cu_bis.txt      — CuBlock-normalized output matrix\n"
        "  → R reads Cu_bis.txt            — applies Q-rescaling"
    )
    _add_code_block(slide, MARGIN, CONTENT_TOP, CONTENT_W, 900000, code, font_size=9.5)

    _add_textbox(slide, MARGIN, CONTENT_TOP + 950000, CONTENT_W, 280000,
                 "Why each intermediate file exists:", 12, bold=True, color=C_NAVY)

    rationale = [
        (0, "P_prim.txt — merged [Input + P] matrix; QN operates on the combined set so all samples share the same rank map", False, C_TEXT),
        (0, "args.txt — Octave cannot receive Python/R variables directly; integers (NH, NP, k) passed as plain text", False, C_TEXT),
        (0, "Cu_bis.txt — Octave cannot return data to R; CuBlock output written to disk for R to read back", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP + 1250000, CONTENT_W, 1100000,
                 rationale, base_size=12)

    _add_textbox(slide, MARGIN, CONTENT_TOP + 2450000, CONTENT_W, 280000,
                 "Problems:", 12, bold=True, color=C_RED)
    problems = [
        (0, "Requires a full R installation", False, C_TEXT),
        (0, "File collisions when running multiple jobs in parallel from the same directory", False, C_TEXT),
        (0, "rpy2 version conflicts on newer Python", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP + 2750000, CONTENT_W, 800000,
                 problems, base_size=12)

    _add_insight_box(slide, MARGIN, CONTENT_TOP + 3650000, CONTENT_W, 380000,
                     "Solution: eliminate all three files — route data through process stdin/stdout streams instead.")


def make_slide4_new_pipeline(prs):
    """Slide 3 — New Pipeline"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, "New Pipeline: Python + Octave via Stdin/Stdout", 3)

    code = (
        "Python (run_shambhala.py)\n"
        "  → gene intersection + NA handling (drop / KNN)\n"
        "  → format [batch + P] as TSV → pipe to Octave stdin\n"
        "  → Octave (Shambhala2_piped.m) reads /dev/stdin\n"
        "  → Octave writes normalized matrix to stdout\n"
        "  → Python parses stdout → Q-rescaling in NumPy/pandas"
    )
    _add_code_block(slide, MARGIN, CONTENT_TOP, CONTENT_W, 870000, code, font_size=9.5)

    _add_textbox(slide, MARGIN, CONTENT_TOP + 950000, CONTENT_W, 300000,
                 "Only 3 targeted changes to Shambhala2_piped.m:", 13, bold=True, color=C_NAVY)

    changes = [
        (0, "Remove args.txt reading — NH, NP, k injected via Octave --eval before script start", False, C_TEXT),
        (0, 'readExpressionData("P_prim.txt")  →  readExpressionData(\'/dev/stdin\')', False, C_TEXT),
        (0, "fopen / fprintf-to-file / fclose  →  fprintf(1, ...)  (stdout = file descriptor 1)", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP + 1270000, CONTENT_W, 900000,
                 changes, base_size=12)

    _add_insight_box(
        slide, MARGIN, CONTENT_TOP + 2300000, CONTENT_W, 380000,
        "CuBlock.m is UNTOUCHED — the core algorithm is verbatim from the original. "
        "All changes are in the I/O layer only.",
        bg=BG_GREEN, text_color=C_GREEN
    )

    extra = [
        (0, "ProcessPoolExecutor (not threads) — each worker is an independent system process with its own Octave subprocess → stdin/stdout pipes can never interfere with each other", False, C_TEXT),
        (0, "All previous unit tests pass with the new piped implementation (30 tests)", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP + 2850000, CONTENT_W, 900000,
                 extra, base_size=12)


def make_slide5_module_map(prs):
    """Slide 4 — Module Map"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, "Module Map: Shambhala_containerized/", 4)

    code = (
        "Shambhala_containerized/\n"
        "├── run_shambhala.py           ← CLI entry point; orchestrates all steps\n"
        "├── shambhala/\n"
        "│   ├── octave_bridge.py       ← sends TSV to Octave stdin; reads result from stdout\n"
        "│   ├── parallel.py            ← splits samples into worker batches; assembles results\n"
        "│   ├── progress_display.py    ← live progress bars in terminal; plain log in K8s\n"
        "│   ├── q_rescale.py           ← Q reference stats; gene-level mean/std alignment\n"
        "│   ├── na_handling.py         ← missing gene handling (drop or KNN-impute)\n"
        "│   └── io_utils.py            ← reads/writes local files and S3 (.csv/.tsv/.tsv.gz)\n"
        "├── octave/\n"
        "│   ├── Shambhala2_piped.m     ← 3 targeted edits (stdin/stdout)\n"
        "│   ├── CuBlock.m              ← VERBATIM — zero changes\n"
        "│   └── *.m (3 files)          ← verbatim copies (QN, kmeans, readExpressionData)\n"
        "├── harmonization_scripts/     ← cross-product benchmark (18 P/Q × 3 imp = 54 jobs)\n"
        "└── tests/ (30 passing tests)"
    )
    _add_code_block(slide, MARGIN, CONTENT_TOP, CONTENT_W, 2700000, code, font_size=9)

    notes = [
        (0, "progress_display.py: TTY mode = live ANSI progress bars; K8s mode = plain timestamped log lines (no interactive terminal in pod)", False, C_TEXT),
        (0, "ProcessPoolExecutor (not threads): each worker is a separate OS process with its own Octave subprocess — stdin/stdout pipes are fully isolated", False, C_TEXT),
        (0, "Tests: 30 unit tests (containerization) + 39 additional tests (speed-up fixtures) = 69 total", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP + 2800000, CONTENT_W, 1300000,
                 notes, base_size=11)


def make_slide6_parallelization(prs):
    """Slide 5 — Initial Parallelization"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, "Initial Parallelization: Shambhala-Workers", 5)

    problem_items = [
        (0, "Before parallelization: Shambhala processes one sample at a time (sequential loop inside Octave)", False, C_TEXT),
        (0, "Running full 5,444-sample FL dataset in a single Octave process: ~9 hours for P0std × Q0std", False, C_RED),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP, CONTENT_W, 600000, problem_items, base_size=12)

    _add_textbox(slide, MARGIN, CONTENT_TOP + 680000, CONTENT_W, 280000,
                 "Solution: --n-shambhala-workers splits samples into N batches:", 12, bold=True, color=C_NAVY)
    solution_items = [
        (0, "Input divided into N equal batches", False, C_TEXT),
        (0, "Each batch sent to a separate Octave subprocess (independent process, own stdin/stdout pipe)", False, C_TEXT),
        (0, "All batches run in parallel using ProcessPoolExecutor", False, C_TEXT),
        (0, "Results assembled; Q-rescaling applied once on the merged output", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP + 980000, CONTENT_W, 850000,
                 solution_items, base_size=12)

    headers = ["Configuration", "Time for P0std × Q0std, full dataset (strict)"]
    rows = [
        ["1 worker (sequential Octave)", "~9 hours"],
        ["30 workers (parallel batches, K8s pod 32 vCPU)", "~1–2 hours"],
    ]
    _add_table(slide, MARGIN, CONTENT_TOP + 1950000,
               CONTENT_W, 700000, headers, rows,
               col_widths=[0.55, 0.45], font_size=12)

    remaining = [
        (0, "Remaining problem: large P variants (ANTE, GTExAffy, NBGPL570, NP=250) still took 6–8 h even with 30 workers", False, C_RED),
        (0, "KNN and softimpute imputation (more genes after imputation) grew 4–5× further", False, C_RED),
        (0, "Single large-P run under knn/softimpute: 2–3 days — full 54-job benchmark projected to take weeks", False, C_RED),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP + 2800000, CONTENT_W, 900000,
                 remaining, base_size=11)

    _add_insight_box(slide, MARGIN, CONTENT_TOP + 3850000, CONTENT_W, 350000,
                     "Root cause: QN and CuBlock both slow down when P is larger (NP=250 vs NP=39). "
                     "Goal: cache computations identical across all N worker batches within one job.")


def make_slide7_pq_datasets(prs):
    """Slide 6 — P/Q Reference Datasets"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, "P/Q Reference Datasets: What Was Tested", 6)

    _add_textbox(slide, MARGIN, CONTENT_TOP, CONTENT_W, 280000,
                 "FL input (S0, strict): 7,174 samples × 3,447 genes.  "
                 "Shambhala needs P (QN calibration anchor) and Q (final rescaling target).",
                 11, color=C_TEXT)

    _add_textbox(slide, MARGIN, CONTENT_TOP + 310000, CONTENT_W // 2, 250000,
                 "P datasets (9 variants)", 12, bold=True, color=C_NAVY)

    p_headers = ["Name", "Samples", "Notes"]
    p_rows = [
        ["P0std", "39", "Original Borisov 2021 / Zenodo; diverse tissues; standard benchmark reference"],
        ["NBKass", "141", "Normal B cells, Kassandra; B-cell specific"],
        ["NBRNAseq", "317", "Normal B cells, RNA-seq; platform match"],
        ["NBGPL570", "250", "Normal B cells, GPL570 Affy; largest NP → slowest"],
        ["ANTE", "202", "Affymetrix reference; large gene panel (36k genes)"],
        ["NBlegacy", "733", "Normal B cells, Normal_B_cells; BostonGene-curated"],
        ["NBext", "878", "Normal B cells, extended; broadest B-cell coverage"],
        ["Oncobox", "779", "Cancer reference; oncology-biased anchor (exploratory)"],
        ["GTExAffy", "651", "GTEx Affymetrix; tissue-diverse; strict run failed (gene ID mismatch)"],
    ]
    _add_table(slide, MARGIN, CONTENT_TOP + 580000,
               CONTENT_W, 2700000, p_headers, p_rows,
               col_widths=[0.15, 0.1, 0.75], font_size=9.5)

    _add_textbox(slide, MARGIN, CONTENT_TOP + 3380000, CONTENT_W // 2, 250000,
                 "Q datasets (2 variants)", 12, bold=True, color=C_NAVY)

    q_headers = ["Name", "Samples", "Genes", "Notes"]
    q_rows = [
        ["Q0std", "100", "11,887", "Original paper reference (GTEx RNA-seq); ~31–69% gene loss with strict FL input"],
        ["QNBKass", "141", "11,768", "Normal B cells, Kassandra; PERFECT gene overlap → 3,447 genes retained, zero gene loss"],
    ]
    _add_table(slide, MARGIN, CONTENT_TOP + 3640000,
               CONTENT_W, 680000, q_headers, q_rows,
               col_widths=[0.12, 0.1, 0.1, 0.68], font_size=10)

    _add_insight_box(
        slide, MARGIN, CONTENT_TOP + 4450000, CONTENT_W, 380000,
        "Key: Q0std causes 31–69% gene loss (different gene set from FL panel). "
        "QNBKass shares the exact gene set → zero gene loss when paired with any P dataset.",
    )


def make_slide8_speedup_motivation(prs):
    """Slide 7 — Speed-Up Motivation"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, "Speed-Up Motivation: Why Another Layer Was Needed", 7)

    _add_textbox(slide, MARGIN, CONTENT_TOP, CONTENT_W, 280000,
                 "Even with 30 parallel Octave workers, per-run times were prohibitive:",
                 13, color=C_TEXT)

    headers = ["Scenario", "Imputation", "Estimated time / Shambhala run"]
    rows = [
        ["P0std (NP=39)", "strict", "~1 h"],
        ["Large P (ANTE, GTExAffy, NBext, NBGPL570)", "strict", "6–8 h"],
        ["Large P", "knn or softimpute", "2–3 days"],
    ]
    _add_table(slide, MARGIN, CONTENT_TOP + 350000,
               CONTENT_W, 850000, headers, rows,
               col_widths=[0.40, 0.25, 0.35], font_size=12)

    motivation = [
        (0, "KNN and softimpute produce more surviving genes (fewer dropped due to NAs) → larger input matrix → more QN and CuBlock work per sample", False, C_TEXT),
        (0, "Total benchmark cost without speed-up: 54 jobs × average ~12 h = ~27 days of compute on a single pod", False, C_RED),
        (0, "Goal: reduce per-run time by caching computations that are identical across all N worker batches within one job", False, C_GREEN),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP + 1300000, CONTENT_W, 1200000,
                 motivation, base_size=12)

    _add_textbox(slide, MARGIN, CONTENT_TOP + 2650000, CONTENT_W, 280000,
                 "Two bottlenecks identified:", 12, bold=True, color=C_NAVY)
    bottlenecks = [
        (0, "Bottleneck 1 — Quantile Normalization on P: each of 30 workers re-sorts the same P matrix (NP=250 for NBGPL570) independently", False, C_TEXT),
        (0, "Bottleneck 2 — k-means in CuBlock: 30 stochastic k-means runs per sample × N_samples per worker, with P-matrix-dependent complexity", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP + 2950000, CONTENT_W, 800000,
                 bottlenecks, base_size=12)

    _add_insight_box(
        slide, MARGIN, CONTENT_TOP + 3900000, CONTENT_W, 350000,
        "Strategy: pre-compute QN reference and k-means clusters once before launching workers, "
        "then inject the cached results into every Octave subprocess.",
        bg=BG_GREEN, text_color=C_GREEN
    )


def make_slide9_speedup_approaches(prs):
    """Slide 8 — Speed-Up Approaches"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, "Speed-Up Approaches: 9 Combinations Tested", 8)

    _add_textbox(slide, MARGIN, CONTENT_TOP, CONTENT_W, 260000,
                 "All approaches pre-compute or approximate something Octave otherwise recomputes per sample. "
                 "Trade-off: speed vs. fidelity to the original algorithm.",
                 11, color=C_TEXT)

    headers = ["Combo", "What it does", "Speedup", "Distortion"]
    rows = [
        ["baseline", "Exact Octave; no caching", "1.0×", "0.00%"],
        ["A — Python QN ref.", "Pre-compute QN sort order from P once; inject into every worker", "~1.0×", "0.98%"],
        ["C_40 — P subsampling", "Replace P with 40 centroids if NP>40; no effect at NP=39", "~1.0× at NP=39", "0.00%"],
        ["C_20 — P subsampling", "Same as C_40 but more aggressive (20 centroids)", "~1.6×", "2.45%"],
        ["E — pre-run k-means", "Run k-means on P genes once in Python; pass labels to Octave (skips 30 random inits)", "~10.6×", "1.26%"],
        ["A_D — QN + synthetic P", "Replace P matrix with 1 synthetic centroid; eliminates large-P overhead", "~5.3×", "14.67%"],
        ["★ A_E — QN + k-means", "Pre-compute BOTH: QN reference (A) + k-means labels (E)", "~8.6×", "1.39%"],
        ["A_D_E — all flags", "A + D + E combined", "~16.8×", "9.00%"],
        ["G — Python CuBlock", "Replace entire Octave CuBlock with pure Python", "—", "XFAIL"],
    ]
    _add_table(slide, MARGIN, CONTENT_TOP + 310000,
               CONTENT_W, 3100000, headers, rows,
               col_widths=[0.22, 0.46, 0.16, 0.16], font_size=10)

    fail_note = (
        "G fails (deadlock): Python PCG64 and Octave Mersenne Twister produce different k-means clusters from same seed → 226% distortion. "
        "Additionally, returning a large NumPy array from subprocess via ProcessPoolExecutor shared queue causes a permanent QueueFeederThread hang."
    )
    _add_insight_box(slide, MARGIN, CONTENT_TOP + 3520000, CONTENT_W, 460000,
                     fail_note, font_size=10, bg=RGBColor(0xFF, 0xEE, 0xEE),
                     text_color=C_RED)

    _add_insight_box(
        slide, MARGIN, CONTENT_TOP + 4100000, CONTENT_W, 350000,
        "★ A_E selected: 8.6× speedup with only 1.39% mean relative distortion. "
        "No structural algorithm change — only caches two pre-computable results.",
        bg=BG_GREEN, text_color=C_GREEN
    )


def make_slide10_ae_approach(prs):
    """Slide 9 — A_E Approved Approach"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, "A_E Approved Approach: How Each Flag Works", 9)

    _add_textbox(slide, MARGIN, CONTENT_TOP, CONTENT_W, 260000,
                 "A_E = --precompute-qn-reference  +  --precompute-cublock-clusters",
                 13, bold=True, color=C_BLUE)

    # Flag A section
    _add_textbox(slide, MARGIN, CONTENT_TOP + 310000, CONTENT_W, 260000,
                 "Flag A — pre-compute QN reference in Python", 13, bold=True, color=C_NAVY)
    a_items = [
        (0, "What: sort each gene in P by expression value; record rank-to-value mapping. Inject pre-computed lookup table into every Octave subprocess (no re-sorting of P)", False, C_TEXT),
        (0, "Why it helps: QN on large P matrix (NP=250 for NBGPL570) is the single biggest bottleneck. Without caching, each of 30 workers recomputes the same sort on the same P data", False, C_TEXT),
        (0, "Risk: Python qnorm library and Octave's QN agree to within 0.98% on continuous data (Bolstad 2003 method). For integer/tie-heavy data implementations may diverge slightly — stays below 1% in FL dataset", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN + 200000, CONTENT_TOP + 600000, CONTENT_W - 200000, 1200000,
                 a_items, base_size=11)

    # Flag E section
    _add_textbox(slide, MARGIN, CONTENT_TOP + 1900000, CONTENT_W, 260000,
                 "Flag E — pre-compute k-means clusters", 13, bold=True, color=C_NAVY)
    e_items = [
        (0, "What: run k-means on P gene matrix once in Python with a fixed random seed; produce k=5 cluster labels. Pass labels to Octave via --eval — Octave skips its own k-means initialization", False, C_TEXT),
        (0, "Why it helps: CuBlock's inner loop runs k-means 30 times per sample (averaging over random initializations). Pre-computing removes all 30 × N_samples random k-means calls", False, C_TEXT),
        (0, "Why 1.39% distortion is acceptable: CuBlock already averages 30 stochastic runs to smooth out randomness. The single Python k-means pass uses a slightly different PRNG than Octave — deviation (1.39%) is comparable to natural run-to-run variability of the baseline itself", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN + 200000, CONTENT_TOP + 2200000, CONTENT_W - 200000, 1200000,
                 e_items, base_size=11)

    _add_insight_box(
        slide, MARGIN, CONTENT_TOP + 3550000, CONTENT_W, 380000,
        "Both flags cache only external inputs (P matrix computations). "
        "The per-sample harmonization logic inside Octave/CuBlock is fully preserved.",
        bg=BG_GREEN, text_color=C_GREEN
    )


def make_slide11_ae_performance(prs):
    """Slide 10 — A_E Performance Summary"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, "A_E Performance Summary", 10)

    _add_textbox(slide, MARGIN, CONTENT_TOP, CONTENT_W // 2, 260000,
                 "Lab test (10-sample fixture, 8,174 genes, P0std NP=39):",
                 12, bold=True, color=C_NAVY)
    lab_headers = ["", "Baseline", "A_E"]
    lab_rows = [
        ["Wall time", "~48 s", "~5.6 s"],
        ["Speedup", "1.0×", "8.6×"],
        ["Mean relative distortion", "0.00%", "1.39%"],
    ]
    _add_table(slide, MARGIN, CONTENT_TOP + 310000,
               CONTENT_W // 2 - 100000, 850000,
               lab_headers, lab_rows,
               col_widths=[0.45, 0.27, 0.28], font_size=12)

    _add_textbox(slide, MARGIN + CONTENT_W // 2 + 100000, CONTENT_TOP, CONTENT_W // 2 - 100000, 260000,
                 "Real-world K8s pod (S0, ~5,444 samples):",
                 12, bold=True, color=C_NAVY)
    rw_headers = ["Variant", "Timestamp", "Interval"]
    rw_rows = [
        ["ANTE × Q0std (knn)", "2026-05-22 16:01", "—"],
        ["NBGPL570 × Q0std (knn)", "2026-05-22 16:42", "41 min"],
        ["NBKass × Q0std (knn)", "2026-05-22 17:22", "40 min"],
        ["NBRNAseq × Q0std (knn)", "2026-05-22 18:03", "41 min"],
    ]
    _add_table(slide, MARGIN + CONTENT_W // 2 + 100000, CONTENT_TOP + 310000,
               CONTENT_W // 2 - 100000, 1000000,
               rw_headers, rw_rows,
               col_widths=[0.42, 0.35, 0.23], font_size=10)

    _add_insight_box(
        slide, MARGIN, CONTENT_TOP + 1450000, CONTENT_W, 280000,
        "~40 minutes per run for ALL P/Q variants including the largest (NBGPL570, NP=250).",
        bg=BG_GREEN, text_color=C_GREEN
    )

    _add_textbox(slide, MARGIN, CONTENT_TOP + 1870000, CONTENT_W, 280000,
                 "Before vs. after A_E deployment:", 12, bold=True, color=C_NAVY)
    ba_headers = ["Metric", "Before A_E", "After A_E", "Gain"]
    ba_rows = [
        ["Files per day", "~53", "~517", "~10×"],
        ["Large-P run time (estimated)", "~4–6 h", "~40 min", "~6–9×"],
    ]
    _add_table(slide, MARGIN, CONTENT_TOP + 2170000,
               CONTENT_W, 700000, ba_headers, ba_rows,
               col_widths=[0.40, 0.20, 0.20, 0.20], font_size=12)

    distortion_note = [
        (0, "Distortion metric: mean relative difference across all genes", False, C_TEXT),
        (0, "Values reach ~100,000 in Q-rescaled scale; max absolute difference dominated by outlier genes → not a useful metric", False, C_TEXT),
        (0, "Mean relative difference of 1.39% is within natural run-to-run variability of the stochastic baseline", False, C_GREEN),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP + 3050000, CONTENT_W, 900000,
                 distortion_note, base_size=11)


def make_slide12_metrics(prs):
    """Slide 11 — Metrics Implemented"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, "Metrics Implemented: What Is Measured", 11)

    _add_textbox(slide, MARGIN, CONTENT_TOP, CONTENT_W, 260000,
                 "11 metric groups computed per harmonized expression file. Three new/extended groups this period:",
                 12, color=C_TEXT)

    # Group J
    _add_textbox(slide, MARGIN, CONTENT_TOP + 310000, CONTENT_W, 250000,
                 "Group J — PC variance distribution  (new)", 12, bold=True, color=C_BLUE)
    j_items = [
        (0, "pct_var_pc1 through pct_var_pc10 and pct_var_cum_top10: % variance explained per PC", False, C_TEXT),
        (0, "Purpose: track batch effect removal. Before FSQN: PC1 ≈ 95%. After good normalization: PC1 drops to single-digit %", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN + 150000, CONTENT_TOP + 580000, CONTENT_W - 150000, 500000,
                 j_items, base_size=11)

    # Group K
    _add_textbox(slide, MARGIN, CONTENT_TOP + 1150000, CONTENT_W, 250000,
                 "Group K — NA retention statistics  (new)", 12, bold=True, color=C_BLUE)
    k_items = [
        (0, "pct_genes_noNA, pct_samples_noNA, n_na_cells, pct_na_cells", False, C_TEXT),
        (0, "Purpose: detect methods that silently drop genes or samples (e.g. strict imputation removes all genes with any NA)", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN + 150000, CONTENT_TOP + 1420000, CONTENT_W - 150000, 500000,
                 k_items, base_size=11)

    # Group I
    _add_textbox(slide, MARGIN, CONTENT_TOP + 2000000, CONTENT_W, 250000,
                 "Group I — WaterMelon score  (extended)", 12, bold=True, color=C_BLUE)
    i_items = [
        (0, "wm_mean_batch: entropy-based clustering quality — LOW = same-batch samples NOT clustered together = good batch removal", False, C_TEXT),
        (0, "wm_mean_bio: HIGH = same-diagnosis samples DO cluster together = biology preserved", False, C_TEXT),
        (0, "wm_ratio_bio_batch: single composite score to rank methods (Zolotovskaya et al. 2020)", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN + 150000, CONTENT_TOP + 2270000, CONTENT_W - 150000, 750000,
                 i_items, base_size=11)

    _add_textbox(slide, MARGIN, CONTENT_TOP + 3130000, CONTENT_W, 250000,
                 "Previously implemented (groups A–H):", 12, bold=True, color=C_NAVY)
    prev_items = [
        (0, "PCA R², kBET, iLISI, cLISI, ASW (batch + biology), UMAP/tSNE centroid dispersion", False, C_TEXT),
        (0, "Pairwise KS tests, variancePartition mixed-model decomposition, kNN graph connectivity, intra/inter-group distance ratios", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN + 150000, CONTENT_TOP + 3400000, CONTENT_W - 150000, 500000,
                 prev_items, base_size=11)


def make_slide13_progress_exp(prs):
    """Slide 12 — Benchmark Progress: Expression Files"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, "Benchmark Progress: Expression Files", 12)

    _add_textbox(slide, MARGIN, CONTENT_TOP, CONTENT_W, 260000,
                 "S3 bucket: $FL_S3_BUCKET/FL_batch_correction/exp/   |   Log date: 2026-05-26",
                 11, color=C_TEXT, italic=True)

    _add_textbox(slide, MARGIN, CONTENT_TOP + 310000, CONTENT_W, 260000,
                 "Shambhala harmonizations:", 13, bold=True, color=C_NAVY)

    # Progress bar (text representation)
    progress_code = "████████████████████████████████████████████████████████████████  100%\n1,297 / 1,296 expected\n18 P/Q variants × 3 imputations × 12 strategies × 2 post_rm variants\n(One extra file is an exploratory speed-up test.)"
    _add_code_block(slide, MARGIN, CONTENT_TOP + 600000, CONTENT_W, 700000,
                    progress_code, font_size=11)

    _add_insight_box(slide, MARGIN, CONTENT_TOP + 1430000, CONTENT_W, 280000,
                     "All 1,296 Shambhala harmonizations complete.",
                     bg=BG_GREEN, text_color=C_GREEN)

    _add_textbox(slide, MARGIN, CONTENT_TOP + 1840000, CONTENT_W, 260000,
                 "All-methods expression files on S3 (Shambhala + all other 39 methods):",
                 13, bold=True, color=C_NAVY)

    all_code = "████████████████████████████████████████████████████████░░░░░░░░  75%\n3,282 total  (Shambhala: 1,297  |  Other methods: 1,985)"
    _add_code_block(slide, MARGIN, CONTENT_TOP + 2130000, CONTENT_W, 550000,
                    all_code, font_size=11)

    strat_items = [
        (0, "12 strategies covered: S0 (all samples), A–I batch exclusion variants, C RNA-seq only, D malignant only, F–H platform subsets, I rare-batch removal", False, C_TEXT),
        (0, "39 normalization methods × 11 strategies × 4 imputation × 2 post_rm = 3,432 S3 outputs (target)", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP + 2800000, CONTENT_W, 700000,
                 strat_items, base_size=11)


def make_slide14_progress_metrics(prs):
    """Slide 13 — Benchmark Progress: Metrics Files"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, "Benchmark Progress: Metrics Files", 13)

    _add_textbox(slide, MARGIN, CONTENT_TOP, CONTENT_W, 260000,
                 "S3 bucket: $FL_S3_BUCKET/FL_batch_correction/metrics/   |   Log date: 2026-05-26",
                 11, color=C_TEXT, italic=True)

    _add_textbox(slide, MARGIN, CONTENT_TOP + 310000, CONTENT_W, 260000,
                 "Shambhala metrics calculated:", 13, bold=True, color=C_NAVY)

    shambhala_code = "████████████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  45%\n579 / 1,296 expected\nStarted 2026-05-24 on fl-metrics pod"
    _add_code_block(slide, MARGIN, CONTENT_TOP + 600000, CONTENT_W, 600000,
                    shambhala_code, font_size=11)

    _add_textbox(slide, MARGIN, CONTENT_TOP + 1330000, CONTENT_W, 260000,
                 "All-methods metrics on S3:", 13, bold=True, color=C_NAVY)

    all_code = "████████████████████████████████████████████████████░░░░░░░░░░░░  66%\n2,401 total  (Shambhala: 579  |  Other methods: 1,822)"
    _add_code_block(slide, MARGIN, CONTENT_TOP + 1620000, CONTENT_W, 520000,
                    all_code, font_size=11)

    detail_items = [
        (0, "Metrics date range for Shambhala: 2026-05-24 15:40 → 2026-05-26 13:05", False, C_TEXT),
        (0, "Completed Shambhala metrics strategies: A, B, C, D, E1, E2, E3, S0 ✓", False, C_GREEN),
        (0, "In progress: F, G, H, I", False, C_ORANGE),
        (0, "Expected completion: ~2026-05-28 (2 more days from log date)", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP + 2300000, CONTENT_W, 900000,
                 detail_items, base_size=12)

    _add_insight_box(
        slide, MARGIN, CONTENT_TOP + 3330000, CONTENT_W, 460000,
        "Once metrics complete: aggregate into shambhala_metrics.csv  →  "
        "load into harmonization_metrics_analysis.ipynb  →  "
        "rank all 18 P/Q variants by batch metrics and select best for downstream SOM analysis.",
    )


def make_slide15_summary(prs):
    """Slide 14 — Summary"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, "Summary", 14)

    _add_textbox(slide, MARGIN, CONTENT_TOP, CONTENT_W, 260000,
                 "Built and deployed:", 13, bold=True, color=C_GREEN)
    built = [
        (0, "Pure-Python Shambhala pipeline — no R, no rpy2, no intermediate files", False, C_TEXT),
        (0, "30-worker parallelization (shambhala-workers): 9 h → 1–2 h for P0std", False, C_TEXT),
        (0, "A_E speed-up approved: 8.6× lab / ~10× real-world throughput gain", False, C_TEXT),
        (0, "1,296 Shambhala expression harmonizations — 100% complete", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP + 320000, CONTENT_W, 900000,
                 built, base_size=12)

    _add_textbox(slide, MARGIN, CONTENT_TOP + 1330000, CONTENT_W, 260000,
                 "Running now:", 13, bold=True, color=C_ORANGE)
    running = [
        (0, "Metrics: 579/1,296 Shambhala files done (~45%); projected completion ~2026-05-28", False, C_TEXT),
        (0, "Once complete → aggregate into shambhala_metrics.csv → load into harmonization_metrics_analysis.ipynb", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP + 1650000, CONTENT_W, 600000,
                 running, base_size=12)

    _add_textbox(slide, MARGIN, CONTENT_TOP + 2400000, CONTENT_W, 260000,
                 "Open questions:", 13, bold=True, color=C_NAVY)
    questions = [
        (0, "Which P/Q combination performs best by batch metrics? (answer pending metrics completion)", False, C_TEXT),
        (0, "Should Shambhala runs be restricted to RNA-seq only (same decision as for SOM pipeline)?", False, C_TEXT),
        (0, "Is the normal B cell Q reference (QNBKass) biologically more appropriate for FL cohorts than GTEx (Q0std)?", False, C_TEXT),
        (0, "Are B-cell-specific P/Q references (NBlegacy, NBext, >700 samples) at risk of over-calibrating toward normal B-cell baseline and compressing tumor subtype signal?", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP + 2720000, CONTENT_W, 1200000,
                 questions, base_size=12)


def make_slide16_next_steps(prs):
    """Slide 15 — Planned Work"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, "Planned Work — Next Steps", 15)

    steps = [
        (0, "1. Presentation on Shambhala and its adaptation — document normalization runs before/after speed-up; present quantitative throughput improvement and parallelization approach.  (This presentation.)", False, C_BLUE),
        (0, "2. Comparison of test dataset before and after speed-up — show output expression values do not change materially (1.39% mean relative diff); explain what was accelerated.", False, C_TEXT),
        (0, "3. Verify completeness of harmonizations; estimate per-run time per Shambhala variant via AWS S3 file listing timestamps.  (Done — Slides 10 and 12–13.)", False, C_GREEN),
        (0, "4. Select best Shambhala attempt from those available by Wednesday evening — once metrics complete, rank all 18 P/Q variants and pick top performer for downstream SOM analysis.", False, C_TEXT),
        (0, "5. Continue trend analysis — extend harmonization_metrics_analysis.ipynb with Shambhala results; compare with the 39-method benchmark.", False, C_TEXT),
        (0, "6. Propose a decision tree — document normalization choice logic (platform, imputation, post-removal) as a practical decision tree for the manuscript.", False, C_TEXT),
        (0, "7. Start writing the article — begin drafting the harmonization benchmark methods and results section.", False, C_TEXT),
    ]
    _add_bullets(slide, MARGIN, CONTENT_TOP, CONTENT_W, 4800000,
                 steps, base_size=12)

    _add_textbox(slide, MARGIN, CONTENT_TOP + 4950000, CONTENT_W, 260000,
                 "Generated: 2026-05-28  |  Pipeline: shambhala_adoption/Shambhala_containerized/  |  Pod: fl-shambhala",
                 9, color=RGBColor(0x88, 0x88, 0x88), italic=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Start from a blank presentation (same dimensions as template)
    prs = Presentation()
    prs.slide_width = Emu(SW)
    prs.slide_height = Emu(SH)

    make_title_slide(prs)
    make_slide2_overview(prs)
    make_slide3_original_pipeline(prs)
    make_slide4_new_pipeline(prs)
    make_slide5_module_map(prs)
    make_slide6_parallelization(prs)
    make_slide7_pq_datasets(prs)
    make_slide8_speedup_motivation(prs)
    make_slide9_speedup_approaches(prs)
    make_slide10_ae_approach(prs)
    make_slide11_ae_performance(prs)
    make_slide12_metrics(prs)
    make_slide13_progress_exp(prs)
    make_slide14_progress_metrics(prs)
    make_slide15_summary(prs)
    make_slide16_next_steps(prs)

    out = os.path.expanduser("~/FL_harmonization/slides_for_project/supervisor_slides_shambhala_260528.pptx")
    prs.save(out)
    print(f"Saved {len(prs.slides)} slides → {out}")


if __name__ == "__main__":
    main()
