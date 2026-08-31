"""
Generate supervisor_slides_260428.pptx from the plan in supervisor_slides_260428.md
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import copy

# ── Colour palette ────────────────────────────────────────────────────────────
C_DARK_BLUE  = RGBColor(0x1F, 0x3A, 0x5F)   # slide title bar
C_MID_BLUE   = RGBColor(0x2E, 0x6D, 0xA4)   # accents / header rows
C_LIGHT_BLUE = RGBColor(0xD6, 0xE8, 0xF5)   # alternate table rows
C_WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
C_BLACK      = RGBColor(0x1A, 0x1A, 0x1A)
C_GREY_TEXT  = RGBColor(0x44, 0x44, 0x44)
C_GREEN      = RGBColor(0x1E, 0x7A, 0x46)   # "ok" / best results
C_RED        = RGBColor(0xC0, 0x39, 0x2B)   # rejected / failed
C_ORANGE     = RGBColor(0xD3, 0x7C, 0x00)   # warning / partial
C_GOLD       = RGBColor(0xFF, 0xD7, 0x00)   # star
C_HARSHNESS_L  = RGBColor(0x27, 0xAE, 0x60)
C_HARSHNESS_M  = RGBColor(0xE6, 0x7E, 0x22)
C_HARSHNESS_H  = RGBColor(0xC0, 0x39, 0x2B)

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

prs = Presentation()
prs.slide_width  = SLIDE_W
prs.slide_height = SLIDE_H

BLANK_LAYOUT = prs.slide_layouts[6]   # completely blank

# ── Helper: add text box ──────────────────────────────────────────────────────
def txb(slide, text, x, y, w, h,
        size=18, bold=False, italic=False, color=C_BLACK,
        align=PP_ALIGN.LEFT, wrap=True, mono=False):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = wrap
    p  = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size  = Pt(size)
    run.font.bold  = bold
    run.font.italic = italic
    run.font.color.rgb = color
    if mono:
        run.font.name = "Courier New"
    return tb

def txb_multi(slide, paragraphs, x, y, w, h, default_size=16,
              default_color=C_BLACK, default_bold=False):
    """paragraphs: list of (text, size, bold, italic, color, indent_level, bullet)"""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    first = True
    for (text, size, bold, italic, color, indent, bullet) in paragraphs:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.level = indent
        if bullet and indent == 0:
            p.text = "• " + text
        elif bullet:
            p.text = "  " * indent + "– " + text
        else:
            p.text = text
        for run in p.runs:
            run.font.size  = Pt(size)
            run.font.bold  = bold
            run.font.italic = italic
            run.font.color.rgb = color
    return tb

# ── Helper: slide header band ─────────────────────────────────────────────────
def add_header(slide, title, subtitle=None, slide_num=None):
    # dark blue band at top
    band = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(0), Inches(0), SLIDE_W, Inches(1.1)
    )
    band.fill.solid()
    band.fill.fore_color.rgb = C_DARK_BLUE
    band.line.fill.background()

    # slide number badge
    if slide_num:
        badge = slide.shapes.add_shape(
            1, Inches(12.5), Inches(0.1), Inches(0.7), Inches(0.45)
        )
        badge.fill.solid()
        badge.fill.fore_color.rgb = C_MID_BLUE
        badge.line.fill.background()
        tf = badge.text_frame
        p  = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = str(slide_num)
        run.font.size  = Pt(12)
        run.font.bold  = True
        run.font.color.rgb = C_WHITE

    # title text
    tb = slide.shapes.add_textbox(Inches(0.25), Inches(0.05), Inches(12), Inches(0.65))
    tf = tb.text_frame
    tf.word_wrap = False
    p  = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = title
    run.font.size  = Pt(26)
    run.font.bold  = True
    run.font.color.rgb = C_WHITE

    if subtitle:
        tb2 = slide.shapes.add_textbox(Inches(0.25), Inches(0.65), Inches(12.8), Inches(0.4))
        tf2 = tb2.text_frame
        tf2.word_wrap = True
        p2  = tf2.paragraphs[0]
        run2 = p2.add_run()
        run2.text = subtitle
        run2.font.size   = Pt(14)
        run2.font.italic = True
        run2.font.color.rgb = RGBColor(0xCC, 0xDD, 0xEE)

# ── Helper: table ─────────────────────────────────────────────────────────────
def add_table(slide, rows, x, y, w, h,
              header_bg=C_MID_BLUE, header_fg=C_WHITE,
              alt_bg=C_LIGHT_BLUE, font_size=11,
              col_widths=None):
    """rows: list of lists of strings. First row = header."""
    nrows = len(rows)
    ncols = len(rows[0])
    tbl  = slide.shapes.add_table(nrows, ncols, x, y, w, h).table

    # column widths
    if col_widths:
        total = sum(col_widths)
        for i, cw in enumerate(col_widths):
            tbl.columns[i].width = int(w * cw / total)

    for ri, row in enumerate(rows):
        for ci, cell_text in enumerate(row):
            cell = tbl.cell(ri, ci)
            cell.text = str(cell_text)
            tf = cell.text_frame
            tf.word_wrap = True
            p  = tf.paragraphs[0]
            run = p.add_run()
            run.text = ""   # clear pptx default
            p.clear()
            p = tf.paragraphs[0]
            run = p.add_run()
            run.text = str(cell_text)
            run.font.size = Pt(font_size)

            if ri == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = header_bg
                run.font.color.rgb = header_fg
                run.font.bold = True
            elif ri % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = alt_bg
                run.font.color.rgb = C_BLACK
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = C_WHITE
                run.font.color.rgb = C_BLACK

    return tbl

# ── Helper: bullet block ──────────────────────────────────────────────────────
def bullet_block(slide, items, x, y, w, h, size=14, title=None, title_size=15):
    """items: list of (text, indent, color) or just strings."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    first = True

    if title:
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = title
        run.font.size  = Pt(title_size)
        run.font.bold  = True
        run.font.color.rgb = C_DARK_BLUE
        first = False

    for item in items:
        if isinstance(item, str):
            text, indent, color = item, 0, C_BLACK
        else:
            text, indent, color = item[0], item[1], item[2] if len(item) > 2 else C_BLACK

        p = tf.add_paragraph() if not first else tf.paragraphs[0]
        if title and first:
            p = tf.add_paragraph()
        first = False

        prefix = "• " if indent == 0 else ("  " * indent + "– ")
        run = p.add_run()
        run.text = prefix + text
        run.font.size  = Pt(size - indent)
        run.font.color.rgb = color

    return tb

# ── Helper: monospace box ─────────────────────────────────────────────────────
def code_box(slide, text, x, y, w, h, size=9):
    bg = slide.shapes.add_shape(1, x, y, w, h)
    bg.fill.solid()
    bg.fill.fore_color.rgb = RGBColor(0xF4, 0xF4, 0xF4)
    bg.line.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)

    tb = slide.shapes.add_textbox(
        x + Inches(0.05), y + Inches(0.05),
        w - Inches(0.1), h - Inches(0.1)
    )
    tf = tb.text_frame
    tf.word_wrap = False
    first = True
    for line in text.split("\n"):
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        run = p.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.name = "Courier New"
        run.font.color.rgb = C_BLACK

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — Title
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)

bg = sl.shapes.add_shape(1, Inches(0), Inches(0), SLIDE_W, SLIDE_H)
bg.fill.solid(); bg.fill.fore_color.rgb = C_DARK_BLUE; bg.line.fill.background()

accent = sl.shapes.add_shape(1, Inches(0), Inches(5.5), SLIDE_W, Inches(0.08))
accent.fill.solid(); accent.fill.fore_color.rgb = C_MID_BLUE; accent.line.fill.background()

txb(sl, "Cross-Platform Transcriptomic Harmonization\nof B-Cell Lymphomas",
    Inches(0.8), Inches(1.5), Inches(11.7), Inches(1.8),
    size=34, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)

txb(sl, "Benchmark Progress Report",
    Inches(0.8), Inches(3.3), Inches(11.7), Inches(0.5),
    size=22, italic=True, color=RGBColor(0xAA, 0xCC, 0xEE), align=PP_ALIGN.CENTER)

txb(sl,
    "25 batch-correction methods  ×  11 sample-removal strategies\n"
    "×  4 imputation approaches  ×  2 post-removal options\n"
    "= 2,000 output matrices evaluated",
    Inches(1.5), Inches(3.9), Inches(10.3), Inches(1.2),
    size=14, color=RGBColor(0xCC, 0xDD, 0xEE), align=PP_ALIGN.CENTER)

txb(sl, "Daniil Nikitin  ·  BostonGene  ·  2026-04-28",
    Inches(0.8), Inches(5.8), Inches(11.7), Inches(0.4),
    size=13, color=RGBColor(0x99, 0xBB, 0xDD), align=PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — Project Context
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Research objective and why harmonization matters", slide_num="2")

bullet_block(sl, [
    ("Central question: can SOM gene-expression patterns resolve FL subtypes, align them to normal GC B-cell states (LZ ↔ DZ), and predict clinical outcomes across mixed platforms?", 0, C_DARK_BLUE),
    ("Data span: Affymetrix microarray · Illumina NGS · Illumina microarray · Agilent microarray — four fundamentally incompatible measurement technologies", 0),
    ("Problem magnitude: ~95% of PCA variance is explained by RNA_BATCH (platform) in raw data — biology is entirely hidden", 0, C_RED),
    ("Goal: reduce batch R² below 20% while preserving biological signal (diagnosis, cell type)", 0, C_GREEN),
    ("Metric: one-way ANOVA R² of RNA_BATCH on first 10 PCA components (lower = better)", 0),
], Inches(0.4), Inches(1.2), Inches(12.5), Inches(5.8), size=16)

# highlight box
box = sl.shapes.add_shape(1, Inches(0.4), Inches(5.6), Inches(12.5), Inches(0.75))
box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0xFF, 0xF0, 0xD0)
box.line.color.rgb = C_ORANGE
txb(sl, "Before normalization: ~95% of PCA variance explained by platform.  Target: R² < 0.20",
    Inches(0.55), Inches(5.65), Inches(12.2), Inches(0.65),
    size=15, bold=True, color=C_ORANGE, align=PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — Dataset Overview
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Multi-platform cohort: 5,444 samples · 88 cohorts", slide_num="3")

# left table
txb(sl, "Dataset composition", Inches(0.4), Inches(1.2), Inches(5.5), Inches(0.35),
    size=13, bold=True, color=C_DARK_BLUE)
add_table(sl, [
    ["Attribute", "Value"],
    ["Total samples (initial)", "7,174"],
    ["After bad-batch / rare-group exclusion", "5,444"],
    ["Genes (full coverage, no NA)", "3,520"],
    ["Cohorts", "88"],
    ["Platforms", "4"],
], Inches(0.4), Inches(1.55), Inches(5.5), Inches(2.1), font_size=12,
   col_widths=[3, 1.2])

# right table
txb(sl, "Major RNA batches", Inches(6.2), Inches(1.2), Inches(6.7), Inches(0.35),
    size=13, bold=True, color=C_DARK_BLUE)
add_table(sl, [
    ["RNA_BATCH", "N", "Platform"],
    ["RNASeq_FF_PolyA  ★ reference", "1,039", "Illumina NGS"],
    ["GPL570_Unknown_Unknown", "1,030", "Affymetrix"],
    ["GPL570_FF_Unknown", "994", "Affymetrix"],
    ["RNASeq_FFPE_Exome_capture", "939", "Illumina NGS"],
    ["GPL14951_FFPE_Unknown", "810", "Illumina microarray"],
    ["GPL570_FFPE_Unknown", "800", "Affymetrix"],
], Inches(6.2), Inches(1.55), Inches(6.7), Inches(2.4), font_size=11,
   col_widths=[3.5, 0.8, 2.4])

# diagnosis boxes
txb(sl, "Diagnosis groups", Inches(0.4), Inches(3.75), Inches(12.5), Inches(0.35),
    size=13, bold=True, color=C_DARK_BLUE)

dx_data = [
    ("DLBCL", "~3,000", C_RED),
    ("FL", "~2,000", C_MID_BLUE),
    ("Normal B cells\n(Normal_B_cells + Kassandra)", "~1,000", C_GREEN),
    ("Rare subtypes\n(MCL, DHL, MZL, CLL, Other)", "excluded", C_GREY_TEXT),
]
for i, (label, n, col) in enumerate(dx_data):
    bx = sl.shapes.add_shape(1,
        Inches(0.4 + i * 3.1), Inches(4.15),
        Inches(2.9), Inches(1.3))
    bx.fill.solid(); bx.fill.fore_color.rgb = RGBColor(0xF0, 0xF6, 0xFF)
    bx.line.color.rgb = col
    txb(sl, label, Inches(0.5 + i * 3.1), Inches(4.2), Inches(2.7), Inches(0.55),
        size=13, bold=True, color=col)
    txb(sl, n, Inches(0.5 + i * 3.1), Inches(4.7), Inches(2.7), Inches(0.5),
        size=18, bold=True, color=col, align=PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — Design Philosophy
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Benchmark design: exhaustive cross-product of all methodological choices", slide_num="4")

bullet_block(sl, [
    ("A partial factorial design cannot identify the best combination — methods interact in non-obvious ways", 0),
    ("Full cross-product is the only way to:", 0),
    ("Compare methods under identical data conditions (same samples, same genes)", 1),
    ("Identify which method is most robust across imputation choices", 1),
    ("Quantify the marginal effect of each dimension independently", 1),
], Inches(0.4), Inches(1.2), Inches(12.5), Inches(2.0), size=15)

add_table(sl, [
    ["Dimension", "Options", "Description"],
    ["Sample-removal strategy", "11", "Which batches / cohorts to exclude before normalization"],
    ["Imputation approach", "4", "How to handle missing genes across platforms"],
    ["Normalization method", "25", "Batch-correction algorithm"],
    ["Post-normalization outlier removal", "2", "With / without removing residual outlier batches"],
], Inches(0.4), Inches(3.3), Inches(12.5), Inches(2.1), font_size=13,
   col_widths=[3.5, 0.7, 8.3])

box = sl.shapes.add_shape(1, Inches(0.4), Inches(5.55), Inches(12.5), Inches(0.7))
box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0xE8, 0xF4, 0xE8)
box.line.color.rgb = C_GREEN
txb(sl, "10 × 4 × 25 = 1,000 normalization runs  →  2,000 output matrices on S3  "
        "(each job stored as post0 + post1 variant)",
    Inches(0.6), Inches(5.6), Inches(12.1), Inches(0.6),
    size=15, bold=True, color=C_GREEN, align=PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — 10 Sample-Removal Strategies
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Dimension 1 — Sample-removal strategies", slide_num="5")

add_table(sl, [
    ["Key", "Description", "Samples", "Rationale"],
    ["S0_no_removal",     "All samples (rare-group exclusion only)",             "~6,000", "Baseline; maximum data"],
    ["A_confirmed_bad",   "Exclude 3 confirmed FFPE microarray batches + SOM cohort", "5,444",  "Removes known bad-quality batches"],
    ["B_extended_bad",    "Exclude 11 batches + SOM cohort (superset of A)",     "~4,700", "More aggressive known-bad removal"],
    ["C_rnaseq_only",     "RNA-seq batches only",                                "2,386",  "Removes cross-platform challenge entirely"],
    ["D_malignant_only",  "Tumor samples only (no normal B cells)",              "4,444",  "Tests normalization without normal/tumor mixing"],
    ["E1_iterative_r1",   "A + 1 data-driven PCA-outlier batch removed",         "5,350",  "Iterative PCA-based outlier detection round 1"],
    ["E2_iterative_r2",   "E1 + 1 more PCA-outlier batch removed",              "~5,300", "Round 2"],
    ["E3_iterative_r3",   "E2 + 1 more PCA-outlier batch removed",              "5,256",  "Round 3"],
    ["F_microarray_only", "Microarray batches only",                             "4,825",  "Intra-platform normalization test"],
    ["G_affymetrix_only", "GPL570 batches only",                                 "2,824",  "Single-technology normalization test"],
    ["I_rare_batches_removed", "Batches ≥ 50 samples only (removes 15 small batches)", "~5,100", "Avoids distortion from under-represented batches"],
], Inches(0.3), Inches(1.2), Inches(12.7), Inches(5.9), font_size=11,
   col_widths=[2.2, 4.8, 1.2, 4.5])

txb(sl, "Note: E1–E3 use identify_outlier_batches() iteratively on PCA-corrected data — most expensive preparation step",
    Inches(0.3), Inches(7.15), Inches(12.7), Inches(0.3),
    size=10, italic=True, color=C_GREY_TEXT)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — 4 Imputation Approaches
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Dimension 2 — Handling missing genes (imputation)", slide_num="6")

txb(sl, "~13,000 genes pass the 5,000-sample presence threshold; only 3,520 have full coverage (no NA across all platforms).",
    Inches(0.4), Inches(1.15), Inches(12.5), Inches(0.4), size=13, italic=True, color=C_GREY_TEXT)

add_table(sl, [
    ["Key", "Method", "Genes (S0)", "Missing-data assumption", "Key limitation"],
    ["strict",      "Drop all genes with any NA",                          "3,520",  "Complete case",      "Smallest gene space; zero NaN guarantee"],
    ["knn",         "sklearn KNNImputer k=5 (Troyanskaya 2001)",           "~12,000","MAR within neighborhood","Residual NaN for BEAM genes"],
    ["missforest",  "R missForest (Stekhoven 2012) — Random Forest",        "FAILED", "MAR across all samples","Ran >24h on 16 CPUs / 240 GB RAM; pod killed, no restart"],
    ["softimpute",  "R softImpute (Hastie 2015) — matrix completion",       "~11,000","Low-rank MAR",       "Residual NaN when no low-rank signal; same BEAM limitation"],
], Inches(0.3), Inches(1.6), Inches(12.7), Inches(2.3), font_size=11,
   col_widths=[1.3, 3.3, 1.3, 2.4, 4.4])

# BEAM box
txb(sl, "Key decision: dropna(axis=1) for residual NaN (BEAM genes)", Inches(0.4), Inches(4.05), Inches(12.5), Inches(0.35),
    size=14, bold=True, color=C_DARK_BLUE)

bullet_block(sl, [
    ("After KNN/softImpute, remaining NaN are BEAMs (Batch-Effect Associated Missing values, Goh 2023) — absent from entire batches → MNAR", 0),
    ("Global median imputation of BEAMs: creates artificial homogenization · inflates intra-sample variance (Hui 2023: +21.3% RMSE) · biases ComBat/SVA EB priors", 0, C_RED),
    ("Decision: dropna(axis=1) for all 24 methods  |  Exception: HarmonizR handles BEAMs internally by design", 0, C_GREEN),
    ("Rubin 1976 (MNAR theory)  ·  Goh 2025 (Briefings in Bioinformatics): 'none of the MVI methods evaluated are suitable for handling BEAMs effectively'", 0, C_GREY_TEXT),
], Inches(0.4), Inches(4.4), Inches(12.5), Inches(2.8), size=13)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 7A — Normalization Methods Part 1
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Dimension 3 — Batch-correction methods evaluated (1/2: methods 01–13)", slide_num="7A")

add_table(sl, [
    ["#", "Key", "Algorithm family", "Lang", "Tier", "Reference / Notes"],
    ["01", "01_raw",              "Passthrough (baseline)",          "—",   "L", "Absolute baseline"],
    ["02", "02_median_scaling",   "Per-batch median shift",          "Py",  "L", "Simple interpretable baseline"],
    ["03", "03_limma",            "Linear model (additive)",         "R",   "L", "limma removeBatchEffect; classic microarray method"],
    ["04", "04_sva",              "Surrogate variable analysis",     "R",   "L", "Leek & Storey 2012; falls back if 0 SVs detected"],
    ["05", "05_combat",           "Empirical Bayes (ComBat)",        "R",   "M", "Johnson 2007; additive + multiplicative; biology covariate"],
    ["06", "06_combat_seq",       "ComBat-seq (NB counts)",          "R",   "M", "Zhang 2020; count data; rounds to integers"],
    ["07", "07_pycombat",         "ComBat Python port",              "Py",  "M", "combat package"],
    ["08", "08_inmoose_combatseq","ComBat-seq Python port",          "Py",  "M", "inmoose.pycombat"],
    ["09", "09_ruv",              "Factor analysis (RUVg)",          "R",   "M", "Risso 2014; 10 housekeeping negative-control genes"],
    ["10", "10_mnn",              "Mutual nearest neighbours",       "R",   "M", "Haghverdi 2018 fastMNN; embedding inverse-projected"],
    ["11", "11_harmony",          "PCA-space clustering",            "Py",  "M", "Korsunsky 2019 Harmony; inverse-projected to gene space"],
    ["12", "12_scanorama",        "Panoramic alignment",             "Py",  "M", "Hie 2019 Scanorama; gene intersection"],
    ["13", "13_fsmvn",            "Feature mean-variance norm.",     "Py",  "M", "Negative control for distributional methods"],
], Inches(0.3), Inches(1.2), Inches(12.7), Inches(5.8), font_size=10,
   col_widths=[0.35, 1.9, 2.5, 0.5, 0.5, 7.0])

txb(sl, "Tier: L = Low (minimal correction)   M = Medium (parametric / subspace)   H = High (distributional)",
    Inches(0.3), Inches(7.15), Inches(12.7), Inches(0.3), size=10, italic=True, color=C_GREY_TEXT)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 7B — Normalization Methods Part 2
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Dimension 3 — Batch-correction methods evaluated (2/2: methods 14–25)", slide_num="7B")

add_table(sl, [
    ["#", "Key", "Algorithm family", "Lang", "Tier", "Reference / Notes"],
    ["14", "14_qsmooth",     "Smooth quantile norm.",          "R",      "H", "Hicks 2018 qsmooth; group-aware quantile normalization"],
    ["15", "15_fsqn_py",     "FSQN Python re-impl.",           "Py",     "H", "Per-gene quantile matching to reference batch"],
    ["16", "16_fsqn_r",      "FSQN R package",                 "R",      "H", "★ Best known result — Franks 2018"],
    ["17", "17_quantile",    "Standard quantile norm.",        "Py",     "H", "Bolstad 2003; forces one global distribution"],
    ["18", "18_rank",        "Fractional rank",                "Py",     "H", "Platform-independent; monotone transform"],
    ["19", "19_tdm",         "Training distribution match",    "R",      "H", "Thompson 2016 TDM"],
    ["20", "20_shambhala",   "CuBlock + quantile norm.",       "R+Oct",  "H", "Borisov 2022 Shambhala2 — currently failing (package not installed)"],
    ["21", "21_harmonizr",   "BEAM-aware ComBat/limma",        "R",      "M", "Voss 2022 HarmonizR; dissection-based; handles NA natively"],
    ["22", "22_tmm",         "TMM (edgeR)",                    "R",      "L", "Robinson 2010; RNA-seq only — skipped on mixed strategies"],
    ["23", "23_vst",         "DESeq2 VST",                     "R",      "L", "Love 2014; RNA-seq only — skipped on mixed strategies"],
    ["24", "24_peer_k10",    "PEER hidden factors",            "—",      "M", "Unavailable for R 4.5 — always skipped"],
    ["25", "25_angel",       "Rank + platform-variance filter","Py",     "H", "Reduced gene space — R² not directly comparable with others"],
], Inches(0.3), Inches(1.2), Inches(12.7), Inches(5.5), font_size=10,
   col_widths=[0.35, 1.9, 2.5, 0.6, 0.5, 6.85])

txb(sl, "Tier: L = Low   M = Medium   H = High (distributional — most aggressive)",
    Inches(0.3), Inches(6.85), Inches(12.7), Inches(0.3), size=10, italic=True, color=C_GREY_TEXT)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 8 — Known Results
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Partial results — strategy A_confirmed_bad × strict imputation", slide_num="8")

# left: results table
txb(sl, "Pre-benchmark exploration (harmonization_benchmark.ipynb):",
    Inches(0.3), Inches(1.2), Inches(7.2), Inches(0.35), size=12, bold=True, color=C_DARK_BLUE)
add_table(sl, [
    ["Method", "R² batch (post0)", "R² diag", "Notes"],
    ["01_raw", "~0.95", "—", "Baseline; platform dominates"],
    ["03_limma", "~0.45", "—", "Partial; additive correction only"],
    ["05_combat", "~0.35", "—", "EB + biology covariate"],
    ["07_pycombat", "~0.35", "—", "Comparable to ComBat"],
    ["11_harmony", ">0.95", "—", "REJECTED — worsened batch"],
    ["14_qsmooth", "~0.48", "—", "Fails 12/88 cohorts"],
    ["15_fsqn_py", "~0.20–0.25", "—", "Good"],
    ["16_fsqn_r", "~0.16", "~0.09", "★ CURRENT BEST"],
    ["17_quantile", "~0.20", "—", "5 outlier batches remain"],
    ["21_harmonizr*", "~0.10", "~0.14", "*E3×softimpute — metrics.csv"],
], Inches(0.3), Inches(1.6), Inches(7.5), Inches(4.5), font_size=10,
   col_widths=[2.0, 1.5, 1.0, 3.0])

# right: metric explanations + metrics.csv example
txb(sl, "How to read the columns:", Inches(8.0), Inches(1.2), Inches(5.0), Inches(0.35),
    size=12, bold=True, color=C_DARK_BLUE)
bullet_block(sl, [
    ("R² batch (post0): fraction of PCA variance (first 10 PCs) explained by RNA_BATCH — without post-normalization outlier removal.  Lower = better. Target < 0.20", 0),
    ("R² diag (post0): same formula for Diagnosis_cell_type_unified. Measures biology preserved. Higher = better", 0),
], Inches(8.0), Inches(1.6), Inches(5.1), Inches(1.6), size=12)

txb(sl, "Verified example from metrics.csv\n(E3 × softimpute × HarmonizR):",
    Inches(8.0), Inches(3.3), Inches(5.1), Inches(0.5), size=12, bold=True, color=C_DARK_BLUE)

add_table(sl, [
    ["strat", "imp", "method", "post_rm", "r2_batch", "r2_diag", "n_samples", "n_genes"],
    ["E3_iterative_r3", "softimpute", "21_harmonizr", "False", "0.099", "0.141", "5,256", "15,226"],
], Inches(7.9), Inches(3.8), Inches(5.2), Inches(0.7), font_size=8,
   col_widths=[2.5, 1.3, 1.8, 1.1, 1.1, 1.0, 1.2, 1.1])

bullet_block(sl, [
    ("FSQN R: only method reaching R² < 0.20 on full mixed-platform data with strategy A", 0, C_GREEN),
    ("HarmonizR: R² = 0.099 with E3 × softimpute — best result in metrics.csv", 0, C_GREEN),
    ("Harmony: R² > 0.95 — anti-optimal; worsened batch effect", 0, C_RED),
    ("Full 10×25 heatmap pending all 1,000 jobs", 0, C_GREY_TEXT),
], Inches(7.9), Inches(4.7), Inches(5.2), Inches(2.0), size=12)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 9 — Post-Normalization Outlier Removal
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Dimension 4 — Post-normalization batch outlier removal", slide_num="9")

bullet_block(sl, [
    ("After normalization: identify batches whose PCA centroid is >2σ from global mean → remove those samples → recompute matrix", 0),
    ("post_rm=False  →  __post0  — normalized output as-is", 1),
    ("post_rm=True   →  __post1  — normalized output with outlier batches removed", 1),
    ("Purpose: 'second-chance' dimension — tests whether residual outlier batches can be remediated without re-normalizing", 0),
], Inches(0.4), Inches(1.2), Inches(12.5), Inches(1.7), size=14)

txb(sl, "Concrete examples from logs/norm_log_e3_260428.txt (E3_iterative_r3 × strict):",
    Inches(0.4), Inches(3.0), Inches(12.5), Inches(0.35), size=13, bold=True, color=C_DARK_BLUE)

add_table(sl, [
    ["Method", "post0 R²", "post1 R²", "Batch removed", "Effect"],
    ["19_tdm",                  "0.548", "0.518", "GPL1708_FF_Unknown", "−0.030 — meaningful improvement"],
    ["09_ruv",                  "0.383", "0.380", "GPL1708_FF_Unknown", "−0.003 — negligible"],
    ["06_combat_seq",           "0.336", "0.337", "GPL1708_FF_Unknown", "+0.001 — no improvement"],
    ["21_harmonizr (strict)",   "0.101", "0.101", "GPL1708_FF_Unknown", "0 — already optimal"],
    ["21_harmonizr (softimpute)","0.099","0.099", "— none detected",    "0 — already fully integrated"],
], Inches(0.4), Inches(3.4), Inches(12.5), Inches(2.4), font_size=12,
   col_widths=[2.5, 1.0, 1.0, 2.8, 5.2])

box = sl.shapes.add_shape(1, Inches(0.4), Inches(5.95), Inches(12.5), Inches(0.75))
box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0xFF, 0xF0, 0xD0)
box.line.color.rgb = C_ORANGE
txb(sl, "GPL1708_FF_Unknown (Illumina microarray) is consistently the residual outlier across most methods on E3.\n"
        "For well-performing methods (HarmonizR), post_rm has no effect — the batch is already integrated.",
    Inches(0.55), Inches(5.98), Inches(12.1), Inches(0.68), size=12, color=C_BLACK)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — Pipeline Diagram
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Two-stage computational pipeline architecture", slide_num="10")

pipeline_text = """\
RAW DATA (S3)
  comb_exp.tsv (~1.9 GB · ~7,174 samples × ~50,000 genes)
  comb_ann_unified.csv (~7 MB)
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1 — PREPARATION  (run_prep_parallel.py)                      │
│  44 jobs: 11 strategies × 4 imputation approaches  |  4 workers     │
│                                                                     │
│  Filter strategies          Imputation                              │
│  S0_no_removal              strict:     dropna → 3,520 genes        │
│  A_confirmed_bad  ◄──PCA    knn:        KNNImputer → ~12k genes (S0)│
│  B_extended_bad             missforest: FAILED  (>24h / 240 GB)     │
│  C_rnaseq_only              softimpute: softImpute → ~11k genes (S0)│
│  D_malignant_only           [residual NaN → dropna(axis=1)]         │
│  E1 / E2 / E3  ◄──PCA                                              │
│  F_microarray_only          log_transform_by_cohort()               │
│  G_affymetrix_only          [log2(x+1) where max > 30]              │
│  I_rare_batches_removed                                              │
│                                    │                                │
│  UPLOAD → S3: prepared/{strat}__{imp}__exp.tsv.gz + __ann.tsv.gz   │
└─────────────────────────────────────────────────────────────────────┘
                    │   40 prepared pairs on S3
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 2 — NORMALIZATION  (run_norm_parallel.py)                    │
│  1,000 jobs: 40 pairs × 25 methods  |  4 workers                    │
│                                                                     │
│  Download prepared (strat, imp) pair  → apply one of 25 methods     │
│  Low:  raw · median_scaling · limma · sva · tmm* · vst*             │
│  Med:  combat · pycombat · ruv · mnn · harmony · scanorama          │
│        harmonizr · peer** · inmoose · combat_seq · fsmvn            │
│  High: qsmooth · fsqn_py · fsqn_r · quantile · rank · tdm           │
│        shambhala · angel                                            │
│                                                                     │
│  post_rm=False → post0  |  post_rm=True → remove outlier → post1   │
│  compute r2_batch, r2_diag, n_samples, n_genes                      │
│  UPLOAD post0 + post1 TSV.GZ to S3  |  WRITE JSON metrics sidecar  │
└─────────────────────────────────────────────────────────────────────┘
          │
          ▼  metrics.csv  →  harmonization_benchmark.ipynb
               heatmaps · ranking tables · top-K analysis"""

code_box(sl, pipeline_text, Inches(0.3), Inches(1.2), Inches(12.7), Inches(6.1), size=8)

txb(sl, "* RNA-seq only (TMM/VST): skipped on mixed strategies    ** PEER: unavailable for R 4.5",
    Inches(0.3), Inches(7.35), Inches(12.7), Inches(0.2), size=9, italic=True, color=C_GREY_TEXT)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 11 — FSQN R
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Selected method: Feature-Specific Quantile Normalization (FSQN R package)", slide_num="11")

txb(sl, "Reference: Franks, Cai & Whitfield, Biostatistics 2018  — doi.org/10.1093/biostatistics/kxx028",
    Inches(0.4), Inches(1.2), Inches(12.5), Inches(0.35), size=12, italic=True, color=C_GREY_TEXT)

txb(sl, "Algorithm (per gene independently):", Inches(0.4), Inches(1.65), Inches(6.2), Inches(0.35),
    size=13, bold=True, color=C_DARK_BLUE)
bullet_block(sl, [
    ("Compute empirical quantile distribution in the reference batch (RNASeq_FF_PolyA, n=1,039)", 0),
    ("For each non-reference batch: map each sample's value to the corresponding quantile in the reference distribution", 0),
    ("Apply the quantile mapping function — aligns distribution shape within each gene, not across genes", 0),
], Inches(0.4), Inches(2.0), Inches(6.2), Inches(1.5), size=13)

txb(sl, "Why better than standard QN:", Inches(0.4), Inches(3.6), Inches(6.2), Inches(0.35),
    size=13, bold=True, color=C_DARK_BLUE)
txb(sl, "Standard QN forces all genes to the same global distribution — ignores that different genes "
        "have different biological variance. FSQN aligns per-gene distributions only, preserving relative expression differences.",
    Inches(0.4), Inches(3.95), Inches(6.2), Inches(1.1), size=13, color=C_BLACK)

txb(sl, "Configuration:", Inches(0.4), Inches(5.15), Inches(6.2), Inches(0.35),
    size=13, bold=True, color=C_DARK_BLUE)
bullet_block(sl, [
    ("Reference batch: RNASeq_FF_PolyA (1,039 samples — highest quality, largest RNA-seq batch)", 0),
    ("Via rpy2 file-based interface: expression → tempfile → R reads/writes → Python reads result", 0),
    ("Pre-computed output: $FL_DATA_ROOT/fsqn_normalized_exp_R.tsv", 0),
], Inches(0.4), Inches(5.5), Inches(6.2), Inches(1.7), size=12)

# right column
bx = sl.shapes.add_shape(1, Inches(6.8), Inches(1.2), Inches(6.2), Inches(4.1))
bx.fill.solid(); bx.fill.fore_color.rgb = RGBColor(0xF0, 0xF6, 0xFF)
bx.line.color.rgb = C_MID_BLUE

txb(sl, "Current limitation", Inches(7.0), Inches(1.3), Inches(5.8), Inches(0.35),
    size=14, bold=True, color=C_RED)
txb(sl, "Even after FSQN, the formal SOM-space batch test fails:\n\n"
        "Different cell types from the same platform cluster together more tightly than "
        "the same cell type across platforms.\n\n"
        "FSQN corrects well in gene-expression PCA space — but platform-specific gene-set "
        "activation patterns remain in SOM metagene space.\n\n"
        "→ Restricting SOM analysis to RNA-seq-only samples is the current recommendation.",
    Inches(7.0), Inches(1.7), Inches(5.8), Inches(3.4), size=13, color=C_BLACK)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 12 — FSQN vs Other Methods
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Comparison of top normalization approaches", slide_num="12")

txb(sl, "Values from pre-benchmark exploration (harmonization_benchmark.ipynb). Formal benchmark metrics pending full run. "
        "R² values omitted where unverified — will be populated from metrics.csv after all 1,000 jobs complete.",
    Inches(0.3), Inches(1.2), Inches(12.7), Inches(0.45), size=11, italic=True, color=C_GREY_TEXT)

add_table(sl, [
    ["Method", "Batch R²", "Biology (R² diag)", "Key limitation", "Verdict"],
    ["Raw (no normalization)",  "—", "Reference", "—", "Baseline only"],
    ["limma removeBatchEffect", "—", "Partial",   "Additive only; multiplicative effects remain", "Partial"],
    ["ComBat (Johnson 2007)",   "—", "Good",      "Requires complete matrix; fails with BEAMs in large gene space", "Not selected"],
    ["SVA (Leek 2012)",         "—", "Good",      "0 SVs detected on full data; falls through to uncorrected", "Not selected"],
    ["qsmooth (Hicks 2018)",    "—", "Partial",   "Fails on 12/88 cohorts; partial improvement only", "Partial"],
    ["Standard QN (Bolstad 2003)", "—", "Good",   "Forces one global distribution; 5 outlier batches remain", "Good — not selected"],
    ["FSQN Python re-impl.",    "—", "Good",      "Slightly weaker than R package", "Alternative"],
    ["FSQN R (Franks 2018)",    "—", "Best",      "Requires reference batch; gene space restricted to intersection", "★ SELECTED"],
    ["Harmony (Korsunsky 2019)", "—", "Worsened", "Embedding-based; back-projection to gene space loses structure", "REJECTED"],
    ["HarmonizR (Voss 2022)*",  "0.099", "0.141", "E3×softimpute only; slow (~14 min/run)", "Promising"],
    ["TMM / VST",               "—", "—",         "RNA-seq only; inapplicable to mixed-platform data", "Inapplicable"],
], Inches(0.3), Inches(1.7), Inches(12.7), Inches(5.5), font_size=10,
   col_widths=[2.5, 0.9, 1.4, 4.6, 3.3])

txb(sl, "* HarmonizR E3×softimpute result from metrics.csv (2026-04-28 run)",
    Inches(0.3), Inches(7.3), Inches(12.7), Inches(0.2), size=10, italic=True, color=C_GREY_TEXT)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 13 — Batch Effect Metric
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "How we measure batch effect: PCA R² (one-way ANOVA)", slide_num="13")

txb(sl, "Formula:", Inches(0.4), Inches(1.2), Inches(6.0), Inches(0.35),
    size=13, bold=True, color=C_DARK_BLUE)
code_box(sl,
    "R²_PC  =  SS_between_batches  /  SS_total\n\n"
    "  where SS = Sum of Squares\n"
    "    SS_between  =  variance in that PC attributable to batch membership\n"
    "    SS_total    =  total variance in that PC across all samples\n\n"
    "mean R²  =  (1/10) × Σ R²_PC    (averaged over first 10 PCA components)",
    Inches(0.4), Inches(1.6), Inches(5.8), Inches(1.9), size=12)

bullet_block(sl, [
    ("R² = 1.0: all variance in that PC explained by batch — pure technical noise", 0, C_RED),
    ("R² = 0.0: batch has no predictive power — ideal (biology-preserving)", 0, C_GREEN),
    ("Baseline (raw data): R² ≈ 0.95  — source: harmonization_benchmark.ipynb", 0),
    ("Current best (HarmonizR, E3×softimpute): R² = 0.099  — source: metrics.csv", 0, C_GREEN),
], Inches(0.4), Inches(3.6), Inches(6.2), Inches(2.0), size=13)

# right column
txb(sl, "Complementary metric — R² diagnosis:", Inches(6.8), Inches(1.2), Inches(6.1), Inches(0.35),
    size=13, bold=True, color=C_DARK_BLUE)
txb(sl, "Same formula applied to Diagnosis_cell_type_unified.\n"
        "Measures biological signal preserved after normalization.\n"
        "We want: batch R² LOW  and  diagnosis R² HIGH.",
    Inches(6.8), Inches(1.6), Inches(6.1), Inches(1.1), size=13)

# summary bar chart placeholder
bx = sl.shapes.add_shape(1, Inches(6.8), Inches(2.9), Inches(6.1), Inches(3.6))
bx.fill.solid(); bx.fill.fore_color.rgb = RGBColor(0xF8, 0xF8, 0xF8)
bx.line.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)

txb(sl, "Batch R² range across completed methods (E3 × strict, from metrics.csv):",
    Inches(7.0), Inches(3.0), Inches(5.8), Inches(0.4), size=11, bold=True, color=C_DARK_BLUE)

methods_vals = [
    ("01_raw", 0.520, C_RED),
    ("06_combat_seq", 0.336, C_ORANGE),
    ("09_ruv", 0.383, C_ORANGE),
    ("19_tdm", 0.548, C_RED),
    ("21_harmonizr", 0.101, C_GREEN),
]
bar_max = 0.6
bar_area_w = Inches(5.0)
bar_area_x = Inches(7.3)
bar_h = Inches(0.35)
bar_y0 = Inches(3.55)
for i, (name, val, col) in enumerate(methods_vals):
    bar_w = int(bar_area_w * val / bar_max)
    bar = sl.shapes.add_shape(1,
        bar_area_x, bar_y0 + i * Inches(0.47),
        bar_w, bar_h)
    bar.fill.solid(); bar.fill.fore_color.rgb = col; bar.line.fill.background()
    txb(sl, f"{name}  {val:.3f}",
        bar_area_x, bar_y0 + i * Inches(0.47) + Inches(0.05),
        Inches(5.5), Inches(0.3),
        size=10, color=C_WHITE if val > 0.15 else C_BLACK)

txb(sl, "Angel (25_angel) uses a reduced gene space — R² is not directly comparable with other methods.",
    Inches(0.4), Inches(5.7), Inches(12.5), Inches(0.35), size=11, italic=True, color=C_GREY_TEXT)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 14 — Current Progress
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Benchmark run status — as of 2026-04-28", slide_num="14")

# stage 1 box
bx = sl.shapes.add_shape(1, Inches(0.3), Inches(1.2), Inches(6.1), Inches(2.6))
bx.fill.solid(); bx.fill.fore_color.rgb = RGBColor(0xF0, 0xF6, 0xFF)
bx.line.color.rgb = C_MID_BLUE
txb(sl, "Stage 1 — Preparation (40 pairs total)", Inches(0.5), Inches(1.3), Inches(5.8), Inches(0.35),
    size=13, bold=True, color=C_MID_BLUE)
bullet_block(sl, [
    ("~31 prepared pairs on S3 (62 files: exp + ann per pair)", 0),
    ("~9 missing pairs: all involve missforest imputation", 0),
    ("missforest FAILURE: ran >24 hours on 16 CPUs / 240 GB RAM; Kubernetes pod was killed with no automated restart → removed from active benchmark", 0, C_RED),
    ("3 active imputations (strict, knn, softimpute): all fully prepared", 0, C_GREEN),
], Inches(0.5), Inches(1.65), Inches(5.8), Inches(2.0), size=12)

# stage 2 box
bx2 = sl.shapes.add_shape(1, Inches(6.7), Inches(1.2), Inches(6.3), Inches(2.6))
bx2.fill.solid(); bx2.fill.fore_color.rgb = RGBColor(0xF0, 0xF6, 0xFF)
bx2.line.color.rgb = C_MID_BLUE
txb(sl, "Stage 2 — Normalization (1,000 jobs → 2,000 files)", Inches(6.9), Inches(1.3), Inches(6.0), Inches(0.35),
    size=13, bold=True, color=C_MID_BLUE)
bullet_block(sl, [
    ("Output files on S3: 1,116 (as of 2026-04-28 evening)", 0),
    ("Completed job combos: 558 (each → post0 + post1)", 0),
    ("Skipped (TMM/VST on mixed, PEER): included in total", 0, C_GREY_TEXT),
    ("Failed jobs in failed_jobs_norm.txt: 31 entries (to be retried)", 0, C_ORANGE),
], Inches(6.9), Inches(1.65), Inches(6.0), Inches(2.0), size=12)

# timeline table
txb(sl, "Timeline of outputs (source: current_normalized_files_260428.txt):",
    Inches(0.3), Inches(3.95), Inches(12.7), Inches(0.35), size=13, bold=True, color=C_DARK_BLUE)
add_table(sl, [
    ["Date", "Outputs produced", "Phase"],
    ["2026-04-19", "309", "Initial run (early strategies/methods)"],
    ["2026-04-20", "38",  "Continued initial run"],
    ["2026-04-26", "179", "After refactoring + pod relaunch"],
    ["2026-04-27", "408", "Large batch — E3 strategies"],
    ["2026-04-28", "133", "E3 × softimpute completion (logs/norm_log_e3_260428.txt)"],
], Inches(0.3), Inches(4.3), Inches(12.7), Inches(1.9), font_size=12,
   col_widths=[1.8, 1.8, 9.1])

# milestone
box = sl.shapes.add_shape(1, Inches(0.3), Inches(6.3), Inches(12.7), Inches(0.75))
box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0xE8, 0xF8, 0xE8); box.line.color.rgb = C_GREEN
txb(sl, "🏆  Recent milestone: E3 × softimpute × HarmonizR — R² batch = 0.099 — new lowest score across all completed runs\n"
        "Source: metrics.csv row: E3_iterative_r3, softimpute, 21_harmonizr, post_rm=False → r2_batch=0.09861, r2_diag=0.14055, 5256 samples, 15226 genes",
    Inches(0.5), Inches(6.35), Inches(12.3), Inches(0.65), size=12, bold=True, color=C_GREEN)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 15A — Technical Challenges Part 1
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Technical problems solved during benchmark development (1/2)", slide_num="15A")

for i, (title, prob, sol) in enumerate([
    (
        "1. rpy2 fork-safety issues",
        "Running multiple R sessions via rpy2 in a multiprocessing pool caused memory corruption and crashes.",
        "Each normalization job runs as an isolated subprocess (fresh Python + R session). ThreadPoolExecutor launches subprocesses — threads manage processes, processes own R sessions."
    ),
    (
        "2. Two-stage pipeline design",
        "Each of 1,000 workers re-downloading the 1.9 GB expression matrix and re-running imputation was prohibitively slow and redundant.",
        "Separated Stage 1 (preparation, 40 jobs) from Stage 2 (normalization, 1,000 jobs). Stage 2 workers download only the ~600 MB pre-prepared file for their (strategy, imputation) pair."
    ),
    (
        "3. Residual NaN handling (BEAM genes)",
        "KNN and softImpute leave residual NaN for genes absent from entire batches. Early code used fillna(median) — statistically incorrect (Hui 2023: inflates noise irreversibly).",
        "Literature-backed decision: dropna(axis=1) for all 24 methods; HarmonizR handles BEAMs internally. Documented in research notes with citations."
    ),
]):
    y_off = Inches(1.2 + i * 1.95)
    bx = sl.shapes.add_shape(1, Inches(0.3), y_off, Inches(12.7), Inches(1.8))
    bx.fill.solid()
    bx.fill.fore_color.rgb = RGBColor(0xF8, 0xF8, 0xFF)
    bx.line.color.rgb = C_MID_BLUE
    txb(sl, title, Inches(0.5), y_off + Inches(0.05), Inches(12.3), Inches(0.35),
        size=14, bold=True, color=C_DARK_BLUE)
    txb(sl, f"Problem: {prob}", Inches(0.5), y_off + Inches(0.4), Inches(12.3), Inches(0.45),
        size=12, color=C_RED)
    txb(sl, f"Solution: {sol}", Inches(0.5), y_off + Inches(0.9), Inches(12.3), Inches(0.75),
        size=12, color=C_GREEN)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 15B — Technical Challenges Part 2
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Technical problems solved during benchmark development (2/2)", slide_num="15B")

challenges_b = [
    (
        "4. Memory management on K8s pod (16 CPU / 240 GB RAM)",
        "OOM crashes when running high-memory methods (HarmonizR, missForest) with large softimpute gene spaces (~15,000 genes × 5,256 samples). missForest failed to complete in >24 hours.",
        "Three-level memory guard in dispatcher + worker-level checks + gc.collect() + R GC calls. missForest removed from benchmark. HarmonizR requires ~14 min and ~40 GB peak RAM."
    ),
    (
        "5. Shambhala2 R package environment issue",
        "library(Shambhala2) throws 'there is no package called Shambhala2' in the pod — even though installation was attempted. Source: logs/norm_log_e3_260428.txt",
        "All shambhala jobs fail and are logged in failed_jobs_norm.txt. Root cause to be investigated — likely GitHub package installation failure during pod init script."
    ),
    (
        "6. Kubernetes deployment",
        "Building a reproducible pod environment with R 4.5 + Bioconductor 3.22 + 12 R packages + Python packages takes 30–40 minutes and must work reliably across pod restarts.",
        "Dockerfile + k8s/pod-ssh.yaml embed requirements.txt and install_r_packages.R inline. VSCode Remote-SSH via port-forward; scripts synced by rsync from Mac."
    ),
]
for i, (title, prob, sol) in enumerate(challenges_b):
    y_off = Inches(1.2 + i * 1.95)
    bx = sl.shapes.add_shape(1, Inches(0.3), y_off, Inches(12.7), Inches(1.8))
    bx.fill.solid()
    bx.fill.fore_color.rgb = RGBColor(0xF8, 0xF8, 0xFF)
    bx.line.color.rgb = C_MID_BLUE
    txb(sl, title, Inches(0.5), y_off + Inches(0.05), Inches(12.3), Inches(0.35),
        size=14, bold=True, color=C_DARK_BLUE)
    txb(sl, f"Problem: {prob}", Inches(0.5), y_off + Inches(0.4), Inches(12.3), Inches(0.45),
        size=12, color=C_RED)
    txb(sl, f"Solution/Status: {sol}", Inches(0.5), y_off + Inches(0.9), Inches(12.3), Inches(0.75),
        size=12, color=C_GREEN)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 16 — Batch Effect Testing Done
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Batch effect testing — completed assessments", slide_num="16")

sections = [
    ("1. Primary benchmark metric (PCA R² batch)  ✅",
     ["Computed for all completed E3-strategy jobs; stored in harmonization-scripts/metrics.csv (local partial copy; full on S3)",
      "136 rows: E3 × {strict, knn, softimpute} × all applicable methods",
      "Provides a single scalar per output matrix; enables cross-method ranking"],
     C_GREEN),
    ("2. Visual QC (PCA / UMAP / tSNE)  — to be done",
     ["Planned for top-10 normalization outputs in harmonization_benchmark.ipynb",
      "Colored by RNA_BATCH, Diagnosis, platform, FF/FFPE, tumor/normal"],
     C_ORANGE),
    ("3. SOM metagene space batch test  — previously shown to supervisor",
     ["Ran oposSOM on FSQN R and QN outputs (results already presented)",
      "Result: batch test fails in metagene space — cell types from same platform cluster more tightly than same cell type across platforms",
      "FSQN corrects well in gene-expression PCA space — but platform-specific gene-set activation remains in SOM metagene space"],
     C_GREY_TEXT),
    ("4. Strategy-level comparison  — to be done",
     ["Strategies C (RNA-seq only), G (Affymetrix only), F (microarray only) establish within-platform baselines",
      "Comparison against S0/A/B will quantify the benefit of cross-platform normalization"],
     C_ORANGE),
]
y = Inches(1.2)
for title, bullets, col in sections:
    bx = sl.shapes.add_shape(1, Inches(0.3), y, Inches(12.7), Inches(0.35 + len(bullets) * 0.38))
    bx.fill.solid()
    bx.fill.fore_color.rgb = RGBColor(0xF8, 0xF8, 0xFF)
    bx.line.color.rgb = col
    txb(sl, title, Inches(0.5), y + Inches(0.04), Inches(12.3), Inches(0.32),
        size=13, bold=True, color=col)
    for j, bullet in enumerate(bullets):
        txb(sl, "• " + bullet,
            Inches(0.7), y + Inches(0.36 + j * 0.38), Inches(12.1), Inches(0.38),
            size=12, color=C_BLACK)
    y += Inches(0.35 + len(bullets) * 0.38 + 0.1)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 17A — Batch Tests To Do Part 1
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Remaining batch effect assessment approaches (1/2)", slide_num="17A")

items_17a = [
    ("1. PCA R² heatmap across full cross-product",
     ["Pending: all 1,000 jobs complete",
      "Will produce 10 strategies × 25 methods heatmap for each of 3 active imputations × 2 post variants = 6 heatmaps total",
      "Key question: is FSQN R consistently best, or does it interact with strategy / imputation choice?"]),
    ("2. Visual inspection of PCA / UMAP / tSNE plots for top-10 approaches",
     ["To be done manually in harmonization_benchmark.ipynb after loading top-10 expression matrices",
      "Colored by RNA_BATCH, Diagnosis, platform, FF/FFPE, tumor/normal",
      "Will include comparison against 10 representative bad-normalization cases to visualize the contrast"]),
    ("3. Distribution plots by cohort after normalization",
     ["Visual inspection of per-cohort expression distributions before/after normalization",
      "Box plots or violin plots colored by RNA_BATCH for top-10 methods",
      "Will reveal residual cohort-level shifts not captured by PCA R²"]),
    ("4. kBET (Büttner 2019) — k-nearest neighbor batch effect test",
     ["Formal statistical test: are k nearest neighbors of each sample enriched for same-batch samples?",
      "More sensitive than PCA R²; operates at individual sample level",
      "Status: not yet implemented — planned addition to bench_shared.py"]),
]
y = Inches(1.2)
for title, bullets in items_17a:
    h = Inches(0.38 + len(bullets) * 0.38)
    bx = sl.shapes.add_shape(1, Inches(0.3), y, Inches(12.7), h)
    bx.fill.solid(); bx.fill.fore_color.rgb = RGBColor(0xF8, 0xF8, 0xFF); bx.line.color.rgb = C_MID_BLUE
    txb(sl, title, Inches(0.5), y + Inches(0.04), Inches(12.3), Inches(0.32),
        size=13, bold=True, color=C_DARK_BLUE)
    for j, b in enumerate(bullets):
        txb(sl, "• " + b, Inches(0.7), y + Inches(0.36 + j * 0.38), Inches(12.1), Inches(0.38),
            size=12, color=C_BLACK)
    y += h + Inches(0.1)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 17B — Batch Tests To Do Part 2
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Remaining batch effect assessment approaches (2/2)", slide_num="17B")

items_17b = [
    ("5. LISI (Korsunsky 2019) — Local Inverse Simpson's Index",
     ["iLISI (integration LISI) — higher = better batch mixing",
      "cLISI (cell-type LISI) — higher = better biology preservation",
      "Status: not yet implemented — planned as supplementary metric"]),
    ("6. SOM-space batch test (quantitative)",
     ["Qualitative SOM portrait comparison (shown previously to supervisor) showed platform clustering",
      "Needed: quantify R² of RNA_BATCH on SOM metagene matrix (not raw genes)",
      "Status: planned — requires running oposSOM on top-5 normalization outputs"]),
    ("7. Silhouette score (batch vs. biology)",
     ["Batch silhouette with RNA_BATCH labels — want low / negative",
      "Biology silhouette with Diagnosis labels — want high",
      "Composite ratio: biology silhouette / batch silhouette",
      "Status: planned — straightforward addition to bench_shared.py"]),
    ("8. Variance partition (Hoffman & Bhatt 2021)",
     ["Quantifies simultaneous contribution of batch, diagnosis, platform, FF/FFPE to gene-level variance",
      "More informative than single-covariate PCA R² — shows covariate interactions",
      "Status: planned for top-3 normalization methods comparison"]),
]
y = Inches(1.2)
for title, bullets in items_17b:
    h = Inches(0.38 + len(bullets) * 0.38)
    bx = sl.shapes.add_shape(1, Inches(0.3), y, Inches(12.7), h)
    bx.fill.solid(); bx.fill.fore_color.rgb = RGBColor(0xF8, 0xF8, 0xFF); bx.line.color.rgb = C_MID_BLUE
    txb(sl, title, Inches(0.5), y + Inches(0.04), Inches(12.3), Inches(0.32),
        size=13, bold=True, color=C_DARK_BLUE)
    for j, b in enumerate(bullets):
        txb(sl, "• " + b, Inches(0.7), y + Inches(0.36 + j * 0.38), Inches(12.1), Inches(0.38),
            size=12, color=C_BLACK)
    y += h + Inches(0.1)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 18 — Next Steps
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "What comes next after the benchmark", slide_num="18")

txb(sl, "Immediate — when all 1,000 jobs complete", Inches(0.4), Inches(1.2), Inches(12.5), Inches(0.35),
    size=14, bold=True, color=C_DARK_BLUE)
add_table(sl, [
    ["#", "Action"],
    ["1", "Load full metrics.csv → generate R² heatmaps (10 strats × 25 methods, per imputation × post_rm variant)"],
    ["2", "Identify top-10 combinations by R² batch across the full grid"],
    ["3", "Load top-10 matrices: PCA/UMAP visual QC + per-cohort distribution plots + compare against 10 representative bad-normalization cases"],
    ["4", "Run oposSOM on top-5 normalization outputs to assess SOM-space batch effect"],
    ["5", "Retry 31 failed jobs (--retry-failed)"],
], Inches(0.4), Inches(1.6), Inches(12.5), Inches(2.05), font_size=12,
   col_widths=[0.4, 12.1])

txb(sl, "Short term (2–4 weeks)", Inches(0.4), Inches(3.75), Inches(12.5), Inches(0.35),
    size=14, bold=True, color=C_DARK_BLUE)
add_table(sl, [
    ["#", "Action"],
    ["1", "Proceed with top-method downstream analysis in parallel with remaining benchmark jobs"],
    ["2", "Implement kBET and LISI metrics in bench_shared.py"],
    ["3", "Run variancePartition on top-3 outputs"],
    ["4", "SOM projection of external FL cohorts onto reference (MDPI 2022 method)"],
    ["5", "Analyze metagene cluster enrichment for FL biological programs (Centroblast vs. Centrocyte axis)"],
], Inches(0.4), Inches(4.15), Inches(12.5), Inches(2.05), font_size=12,
   col_widths=[0.4, 12.1])

txb(sl, "Dissertation-level", Inches(0.4), Inches(6.3), Inches(12.5), Inches(0.35),
    size=14, bold=True, color=C_DARK_BLUE)
bullet_block(sl, [
    ("Write technical article on harmonization and imputation comparison as a first deliverable", 0),
    ("Compare SOM signatures vs. PCA64 vs. internal B-cell typing vs. embeddings for OS/PFS prediction", 0),
    ("Validate FL biological subtypes against published literature", 0),
], Inches(0.4), Inches(6.65), Inches(12.5), Inches(0.85), size=13)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 19 — Infrastructure Summary
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Computational infrastructure", slide_num="19")

add_table(sl, [
    ["Component", "Details"],
    ["K8s pod",          "fl-batch-correction · ubuntu:24.04 · 16 vCPU / 240 GiB RAM"],
    ["Python",           "3.11 · venv collagen_3_11"],
    ["R",                "4.5.3 · Bioconductor 3.22"],
    ["Key R packages",   "limma, sva, batchelor, RUVSeq, qsmooth, FSQN, TDM, HarmonizR, missForest, softImpute, edgeR, DESeq2"],
    ["Key Python pkgs",  "rpy2, boto3, pandas, numpy, scikit-learn, harmonypy, scanorama, combat, inmoose, psutil"],
    ["Storage",          "AWS S3 — $FL_S3_BUCKET/FL_batch_correction/"],
    ["Persistent vol.",  "100 GiB PVC fl-workspace for logs and workspace"],
    ["Job dispatch",     "ThreadPoolExecutor · 4 workers per stage"],
    ["Memory guard",     "Three-level: dispatcher → worker startup → worker post-load (exit code 2 on OOM)"],
    ["Docker image",     "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/fl-batch-correction:latest"],
    ["Smoke test",       "test_mock.py — 25 methods × 4 imputation approaches on synthetic 80×200 data"],
], Inches(0.3), Inches(1.2), Inches(12.7), Inches(5.1), font_size=12,
   col_widths=[2.3, 10.4])

box = sl.shapes.add_shape(1, Inches(0.3), Inches(6.4), Inches(12.7), Inches(0.6))
box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0xF0, 0xF6, 0xFF); box.line.color.rgb = C_MID_BLUE
txb(sl, "Total compute estimate: ~1,000 jobs × avg 10–30 min/job = ~200–500 CPU-hours for a complete benchmark run",
    Inches(0.5), Inches(6.45), Inches(12.3), Inches(0.5), size=13, bold=True, color=C_MID_BLUE,
    align=PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 20 — Summary and Open Questions
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Summary and questions for supervisor", slide_num="20")

# left: completed + key results
txb(sl, "Completed in the last 2 weeks", Inches(0.3), Inches(1.2), Inches(6.2), Inches(0.35),
    size=13, bold=True, color=C_GREEN)
completed = [
    "Two-stage K8s pipeline operational (preparation + normalization separated)",
    "25 normalization methods × 4 imputation strategies fully implemented and tested",
    "558 out of 1,000 normalization jobs completed; 1,116 output matrices on S3",
    "E3×softimpute×HarmonizR: R² batch = 0.099 — new best result (metrics.csv)",
    "Literature-backed decision for dropna vs fillna(median) for residual BEAM NaN",
    "Dockerfile + K8s pod with R 4.5 + Bioconductor 3.22 fully reproducible",
]
for i, item in enumerate(completed):
    txb(sl, "✅  " + item, Inches(0.3), Inches(1.6 + i * 0.42), Inches(6.2), Inches(0.4),
        size=11.5, color=C_BLACK)

txb(sl, "Key results so far", Inches(0.3), Inches(4.4), Inches(6.2), Inches(0.35),
    size=13, bold=True, color=C_DARK_BLUE)
bullet_block(sl, [
    ("FSQN R: best on A×strict (pre-benchmark exploration; formal metrics pending)", 0, C_MID_BLUE),
    ("HarmonizR: R² = 0.099 with E3×softimpute (metrics.csv) — competitive", 0, C_GREEN),
    ("Harmony: R² > 0.95 — anti-optimal (worsens batch)", 0, C_RED),
    ("SOM metagene space fails batch test even after FSQN — RNA-seq or microarray-only tracks needed", 0, C_ORANGE),
], Inches(0.3), Inches(4.75), Inches(6.2), Inches(2.1), size=12)

# right: open questions
bx = sl.shapes.add_shape(1, Inches(6.7), Inches(1.2), Inches(6.4), Inches(6.1))
bx.fill.solid(); bx.fill.fore_color.rgb = RGBColor(0xFF, 0xF8, 0xEC)
bx.line.color.rgb = C_ORANGE

txb(sl, "Open questions for discussion", Inches(6.9), Inches(1.3), Inches(6.0), Inches(0.35),
    size=14, bold=True, color=C_ORANGE)

questions = [
    ("1. SOM analysis scope",
     "RNA-seq only, or is a separate microarray-only SOM track also worth pursuing alongside the mixed-platform approach?"),
    ("2. Imputation order",
     "Should imputation be performed after log-transformation by cohort?\n"
     "Current order: impute → log-transform. Imputing on already log-transformed data is more honest: imputed values will be in log scale. Imputing on raw then log-transforming may artificially correct log offsets for imputed values."),
    ("3. Within-batch imputation",
     "Should imputation be limited to within-batch rather than across all samples?\n"
     "Within-batch imputation would impute far fewer genes but produce less artificial noise — consistent with the dropna reasoning for BEAMs."),
]
for i, (q_title, q_text) in enumerate(questions):
    y_q = Inches(1.75 + i * 1.85)
    txb(sl, q_title, Inches(6.9), y_q, Inches(6.0), Inches(0.32),
        size=13, bold=True, color=C_DARK_BLUE)
    txb(sl, q_text, Inches(6.9), y_q + Inches(0.35), Inches(6.0), Inches(1.4),
        size=12, color=C_BLACK)

# ═══════════════════════════════════════════════════════════════════════════════
# APPENDIX A1 — Literature Anchors
# ═══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(BLANK_LAYOUT)
add_header(sl, "Appendix A1 — Literature anchors for method selection", slide_num="A1")

add_table(sl, [
    ["Reference", "Relevance"],
    ["Loeffler-Wirth 2019 (Nat Commun)", "oposSOM predicts OS in B-lymphomas"],
    ["Loeffler-Wirth 2022 (Cells)", "Continuous LZ↔DZ transitions between lymphoma subtypes via SOM"],
    ["Franks et al. 2018 (Biostatistics)", "FSQN algorithm — doi.org/10.1093/biostatistics/kxx028"],
    ["Voss et al. 2022 (Nat Commun)", "HarmonizR BEAM-aware harmonization — doi.org/10.1038/s41467-022-31214-6"],
    ["Goh et al. 2023 / 2025 (Briefings in Bioinformatics)", "BEAM missing data framework — doi.org/10.1093/bib/bbad055 / bbae583"],
    ["Hui et al. 2023 (Sci Rep)", "Batch-sensitized imputation: M1 vs M2 vs M3 — doi.org/10.1038/s41598-023-35823-7"],
    ["Hie et al. 2019 (Nature Biotech)", "Scanorama gene intersection philosophy — doi.org/10.1038/s41587-019-0113-3"],
    ["Büttner et al. 2019 (Nature Methods)", "kBET batch effect test — doi.org/10.1038/s41592-018-0254-1"],
    ["Korsunsky et al. 2019 (Nature Methods)", "Harmony + LISI metrics — doi.org/10.1038/s41592-019-0619-0"],
    ["Troyanskaya et al. 2001 (Bioinformatics)", "KNN imputation — doi.org/10.1093/bioinformatics/17.6.520"],
    ["Stekhoven & Bühlmann 2012 (Bioinformatics)", "missForest imputation — doi.org/10.1093/bioinformatics/btr597"],
    ["Hastie et al. 2015 (JMLR)", "softImpute matrix completion"],
    ["Rubin 1976 (Biometrika)", "MNAR missing data theory — doi.org/10.1093/biomet/63.3.581"],
], Inches(0.3), Inches(1.2), Inches(12.7), Inches(5.9), font_size=11,
   col_widths=[4.5, 8.2])

# ═══════════════════════════════════════════════════════════════════════════════
# Save
# ═══════════════════════════════════════════════════════════════════════════════
out = os.path.expanduser("~/FL_harmonization/harmonization-scripts/supervisor_slides_260428.pptx")
prs.save(out)
print(f"Saved: {out}")
print(f"Slides: {len(prs.slides)}")
