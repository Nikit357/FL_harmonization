"""Composed Graphical Abstract candidates for the ComboBatch article (NAR).

Draws the three candidate graphical abstracts as COMPLETE, self-contained PDFs --
artwork and type together -- so they can be judged at final print size without a
Figma round trip. Written because the Figma MCP tool-call quota (Starter plan)
blocked composition on the canvas; see
`graphical_abstract_redesign_plan_260731.md`, section "BLOCKER".

  graphical_abstract_variantA_mosaic.pdf    2,234 attempts -> four verdicts
  graphical_abstract_variantB_strip.pdf     five real pipeline stages, edge to edge
  graphical_abstract_variantC_fan.pdf       sample-weighted semicircular fan

Canvas and typography
---------------------
Every page is exactly 5.000 x 2.000 in = 127.0 x 50.8 mm, aspect 2.5000, which is
the NAR 6.9 minimum size and required ratio. Because matplotlib measures type in
points and the page is 360 pt wide, `fontsize=12` really is 12 pt on paper -- so
the 12-16 pt rule from 6.9 is expressed directly, with no px conversion. This is
the one advantage the PDF route has over composing in Figma at 720 px.

Font is Liberation Sans, the metric-compatible Arial substitute (real Arial is
installed neither here nor in Figma). `pdf.fonttype = "truetype"` embeds it, per
6.6. The Figma variants use Arimo, the same Arial-metric lineage, so the two
routes are typographically interchangeable.

Text budget per variant is fixed by 6.9 ("text sparingly"): A = 8 items,
B = 7, C = 6. `_report_text_fit()` counts them and measures every string against
its zone, failing loudly on overflow rather than shipping clipped type.

Data provenance
---------------
All artwork comes from `graphical_abstract_assets.py`, which is imported rather
than duplicated -- the mosaic, platform stack and fan drawers, the biology
collapse, and the cached embeddings are shared. Nothing here downloads from S3:
embeddings are read from `figures/ga/_embedding_cache/`, and the composer raises
if a panel is missing rather than silently fetching ~700 MB.

Disclosures that must reach the caption
---------------------------------------
- Platform stack: Agilent is 0.89% of samples and is lifted to 3.50% so it stays
  visible. Deliberate exaggeration, printed at run time.
- Decision fan: "Mixed platforms" is 4.0% of samples (7.2 deg) and is widened to
  18 deg so it can carry a label. Same rationale, also printed.
- Mosaic: tiles are ordered by composite score, best first. The distribution is a
  narrow continuum (0.34-0.66) with NO elite cluster; the four outlined tiles are
  the recommended approaches, at global ranks 5, 45, 47 and 213. Do not caption
  this as "a few score well and most score poorly" -- that is not what it shows.

Usage
-----
    source ~/venvs/collagen_3_11/bin/activate
    cd figures_for_article
    python graphical_abstract_pdfs.py            # all three
    python graphical_abstract_pdfs.py --only A   # one variant
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

import graphical_abstract_assets as ga

# ── Page geometry ─────────────────────────────────────────────────────────────
# NAR 6.9: 5:2 landscape, minimum 127 x 50 mm. 5 x 2 in is 127.0 x 50.8 mm and
# exactly 2.5:1, so it satisfies both the ratio and the floor with no slack.
PAGE_W_IN, PAGE_H_IN = 5.0, 2.0
PAGE_W_PT, PAGE_H_PT = PAGE_W_IN * 72.0, PAGE_H_IN * 72.0   # 360 x 144 pt

# NAR 6.9 type range. Enforced by _report_text_fit, not merely intended.
FONT_MIN_PT, FONT_MAX_PT = 12.0, 16.0
FS_HEAD, FS_LEAD, FS_BODY = 16.0, 14.0, 12.0

OUT_DIR = Path(".")
INK = "#1A1A1A"

# Expected number of text items per variant (NAR 6.9 "text sparingly").
TEXT_BUDGET = {"A": 8, "B": 7, "C": 6}


def _pt(x: float, y: float) -> tuple[float, float]:
    """Convert a point position on the page to figure-fraction coordinates."""
    return x / PAGE_W_PT, y / PAGE_H_PT


def _axes_pt(fig: plt.Figure, x: float, y: float, w: float, h: float) -> plt.Axes:
    """Add an axes positioned in page points, measured from the bottom-left."""
    return fig.add_axes([x / PAGE_W_PT, y / PAGE_H_PT, w / PAGE_W_PT, h / PAGE_H_PT])


def _text_pt(
    fig: plt.Figure, x: float, y: float, s: str, size: float, **kwargs
) -> plt.Text:
    """Place text at a page-point position, recording its size for the audit."""
    handle = fig.text(*_pt(x, y), s, fontsize=size, color=INK, **kwargs)
    handle.set_gid(f"ga-text-{size:g}pt")
    return handle


def _new_page() -> plt.Figure:
    """Create a blank 127 x 50.8 mm page with an explicit white background.

    White is set explicitly on both figure and savefig: a transparent PDF
    background can render black in some print pipelines, which is exactly the
    defect the v1 Figma frame had (`fills` was an empty array).
    """
    fig = plt.figure(figsize=(PAGE_W_IN, PAGE_H_IN))
    fig.patch.set_facecolor("white")
    return fig


def _rule(fig: plt.Figure, y: float, x0: float = 10.0, x1: float = 350.0) -> None:
    """Draw the hairline that separates the headline band from the body."""
    fig.add_artist(Line2D(
        [x0 / PAGE_W_PT, x1 / PAGE_W_PT], [y / PAGE_H_PT, y / PAGE_H_PT],
        color=INK, linewidth=0.8,
    ))


def _report_text_fit(
    fig: plt.Figure, variant: str, zones: dict[str, float]
) -> list[str]:
    """Measure every text item and report font-size and overflow violations.

    Returns the list of problems found. Widths are measured from the rendered
    text, not estimated from character counts, because Liberation Sans is
    narrower than a naive 0.5 em estimate and estimating would either waste
    space or clip silently.

    `zones` maps a text's gid-independent label to the width in points it is
    allowed to occupy; a text whose label is absent is only size-checked.
    """
    fig.canvas.draw()
    dpi = fig.dpi
    problems: list[str] = []
    print(f"  text items: {len(fig.texts)} (budget {TEXT_BUDGET[variant]})")
    if len(fig.texts) != TEXT_BUDGET[variant]:
        problems.append(
            f"text count {len(fig.texts)} != budget {TEXT_BUDGET[variant]}"
        )

    for handle in fig.texts:
        bbox = handle.get_window_extent(renderer=fig.canvas.get_renderer())
        w_pt = bbox.width / dpi * 72.0
        h_pt = bbox.height / dpi * 72.0
        size = handle.get_fontsize()
        label = handle.get_text().replace("\n", " / ")[:34]
        budget = zones.get(handle.get_label())
        flag = ""
        if not (FONT_MIN_PT - 1e-9 <= size <= FONT_MAX_PT + 1e-9):
            problems.append(f"{label!r}: {size} pt outside {FONT_MIN_PT}-{FONT_MAX_PT}")
            flag = "  <-- FONT SIZE"
        if budget is not None and w_pt > budget + 0.5:
            problems.append(f"{label!r}: {w_pt:.1f} pt wide, zone is {budget:.1f} pt")
            flag += "  <-- OVERFLOW"
        print(
            f"    {size:>4.0f} pt  {w_pt:>6.1f} x {h_pt:>5.1f} pt  "
            f"{label:<36}{flag}"
        )
    return problems


def _save(fig: plt.Figure, name: str) -> None:
    """Write the composed page as PDF (deliverable) plus a 600 dpi PNG proof."""
    pdf_path = OUT_DIR / f"{name}.pdf"
    fig.savefig(pdf_path, facecolor="white", edgecolor="none")
    fig.savefig(OUT_DIR / f"{name}.png", facecolor="white", edgecolor="none", dpi=600)
    plt.close(fig)
    print(f"  wrote {pdf_path}  ({pdf_path.stat().st_size / 1024:.1f} kB)")


def _biology_panel(ax: plt.Axes, name: str, s: float = 0.9) -> dict[str, int]:
    """Draw one cached embedding coloured and shaped by diagnosis."""
    coords, ann = ga.load_cached_panel(name)
    labels = ga.biology_labels(ann, ann.index)
    ga.draw_biology_scatter(ax, coords, labels, s=s)
    return labels.value_counts().to_dict()


# ── Variant A — "2,234 attempts -> four verdicts" ─────────────────────────────

def build_variant_a() -> list[str]:
    """Compose Variant A: input stack, attempt mosaic, four extracted verdicts.

    Layout in page points (origin bottom-left, page 360 x 144):

        headline band   y 120-140
        rule            y 116
        zone 1 input    x  10- 84
        zone 2 mosaic   x  88-174
        zone 3 verdicts x 186-350

    Zones 2 and 3 sit further left than a visually even three-column split would
    put them. "Mixed platforms → MNN" measures 131 pt at 12 pt, and 12 pt is the
    legal floor, so the widest label dictates the widest column -- the alternative
    was shortening it to "Mixed", which loses the meaning.
    """
    print("[A] mosaic -> verdicts")
    fig = _new_page()

    _text_pt(fig, 10, 138, "NO UNIVERSAL HARMONIZER", FS_HEAD,
             ha="left", va="top", fontweight="bold", label="head")
    _rule(fig, 116)

    # ── Zone 1: the input dataset ────────────────────────────────────────────
    _text_pt(fig, 10, 108, "7,174\nsamples", FS_LEAD,
             ha="left", va="top", fontweight="bold", linespacing=1.15, label="z1a")
    stack_ax = _axes_pt(fig, 8, 30, 34, 50)
    ga.draw_platform_stack(stack_ax, lw=0.9)
    _text_pt(fig, 10, 26, "88 cohorts\n4 platforms", FS_BODY,
             ha="left", va="top", linespacing=1.15, label="z1b")

    # ── Zone 2: the whole benchmark as texture ───────────────────────────────
    scores = ga.load_composite_scores()
    verdict_ids = [
        f"{strat}__{imp}__{method}__post{post_rm}"
        for _, strat, imp, method, post_rm in ga.VERDICT_PANELS
    ]
    # Square: the 47 x 48 grid is near-square, so a non-square axes would leave
    # dead space rather than bigger tiles.
    mosaic_ax = _axes_pt(fig, 96, 34, 78, 78)
    ga.draw_benchmark_mosaic(
        mosaic_ax, scores, highlight_ids=verdict_ids,
        edge_lw=0.12, highlight_lw=0.7,
    )
    _text_pt(fig, 88, 28, "2,234 attempts\n× 87 metrics", FS_BODY,
             ha="left", va="top", linespacing=1.15, label="z2")

    # ── Zone 3: the four verdicts ────────────────────────────────────────────
    verdict_text = {
        "fresh_frozen": "Fresh frozen → MNN",
        "ffpe": "FFPE → SVA",
        "rnaseq": "RNA-seq → SVA",
        "mixed": "Mixed platforms → MNN",
    }
    row_pitch, row_top = 26.0, 112.0
    for i, (subset, *_rest) in enumerate(ga.VERDICT_PANELS):
        top = row_top - i * row_pitch
        thumb_ax = _axes_pt(fig, 186, top - 23, 22, 22)
        counts = _biology_panel(thumb_ax, f"ga_tsne_{subset}", s=0.6)
        _text_pt(fig, 213, top - 12, verdict_text[subset], FS_BODY,
                 ha="left", va="center", label=f"z3-{subset}")
        print(f"    {subset:<13} {counts}")

    problems = _report_text_fit(fig, "A", {
        "head": 340.0, "z1a": 74.0, "z1b": 74.0, "z2": 96.0,
        "z3-fresh_frozen": 137.0, "z3-ffpe": 137.0,
        "z3-rnaseq": 137.0, "z3-mixed": 137.0,
    })
    _save(fig, "graphical_abstract_variantA_mosaic")
    return problems


# ── Variant B — "the continuous strip" ────────────────────────────────────────

def build_variant_b() -> list[str]:
    """Compose Variant B: five real pipeline stages, edge to edge.

    The five panels are genuine S3 matrices at five real stages, never an
    interpolated morph between two -- a morph would be a visual fiction a referee
    could fairly call misleading.

    Panels are square (72 x 72 pt) and butt together with no gaps or borders, so
    5 x 72 = 360 pt fills the page width exactly and the eye reads one continuous
    transformation rather than five plots.
    """
    print("[B] continuous strip")
    fig = _new_page()

    _text_pt(fig, 10, 138, "BATCH OUT, BIOLOGY IN", FS_HEAD,
             ha="left", va="top", fontweight="bold", label="head")
    _text_pt(fig, 350, 136, "colour: batch → biology", FS_BODY,
             ha="right", va="top", label="key")
    # No headline rule here: the tinted band below is full-bleed and already
    # separates headline from body. A 10-350 pt rule above a 0-360 pt band just
    # looks like a mis-drawn band edge.

    stage_labels = {
        1: "Raw",
        2: "Batch\nremoved",
        3: "Imputed",
        4: "Harmonized\n(MNN)",
        5: "Post-\nremoval",
    }
    # A faint full-bleed band behind the panels. Needed because each embedding is
    # drawn on equal axes and its point cloud does not fill its square, so without
    # a shared ground the five panels read as five separate plots -- destroying the
    # "one continuous transformation" idea that is the whole variant.
    band_ax = _axes_pt(fig, 0, 42, PAGE_W_PT, 76)
    band_ax.set_facecolor("#F4F6F8")
    band_ax.set_xticks([])
    band_ax.set_yticks([])
    for spine in band_ax.spines.values():
        spine.set_visible(False)

    panel_w = PAGE_W_PT / len(ga.STRIP_STAGES)     # 72 pt
    for idx, label, *_rest in ga.STRIP_STAGES:
        name = ga.strip_stage_name(idx, label)
        coords, ann = ga.load_cached_panel(name)
        colors, scheme, bio = ga.strip_stage_colors(idx, ann, ann.index)

        x0 = (idx - 1) * panel_w
        ax = _axes_pt(fig, x0, 44, panel_w, 72)
        ax.patch.set_visible(False)     # let the shared band show through
        if bio is None:
            ga.draw_scatter(ax, coords, colors, s=0.9)
        else:
            # Biology stages get one marker per group, so the batch -> biology
            # message does not depend on hue alone (NAR 6.7).
            ga.draw_biology_scatter(ax, coords, bio, s=0.9)
        # Panels butt together: no spines, or five boxes appear inside the band.
        for spine in ax.spines.values():
            spine.set_visible(False)

        _text_pt(fig, x0 + panel_w / 2.0, 38, stage_labels[idx], FS_BODY,
                 ha="center", va="top", linespacing=1.15, label=f"stage{idx}")
        print(f"    stage {idx} {label:<14} {len(coords):>5} points, {scheme}")

    problems = _report_text_fit(fig, "B", {
        "head": 340.0, "key": 150.0,
        **{f"stage{i}": 70.0 for i in range(1, 6)},
    })
    _save(fig, "graphical_abstract_variantB_strip")
    return problems


# ── Variant C — "the decision fan" ────────────────────────────────────────────

def build_variant_c() -> list[str]:
    """Compose Variant C: a sample-weighted semicircular decision fan.

    Sector angular width is proportional to subset size, so the geometry itself
    carries dataset composition. Labels sit at each sector's mid-angle; the
    narrowest sector, "Mixed platforms", is labelled OUTSIDE the arc on the right
    because even after widening to MIN_SECTOR_DEG it cannot hold two lines of
    12 pt type. Placing it outside works precisely because that sector lies at
    the horizontal right end of the semicircle, where the page has free margin.
    """
    print("[C] decision fan")
    fig = _new_page()

    _text_pt(fig, 10, 138, "WHICH HARMONIZER? IT DEPENDS", FS_HEAD,
             ha="left", va="top", fontweight="bold", label="head")
    _rule(fig, 118)

    # The fan axes hold the unit semicircle: centre (0,0), outer radius 1. A
    # semicircle is 2:1, not 5:2, so the arc alone cannot fill this page -- the
    # four external labels are what occupy the corners a semicircle leaves empty.
    fan_cx, fan_cy, fan_r = 180.0, 6.0, 80.0
    fan_ax = _axes_pt(fig, fan_cx - fan_r, fan_cy, 2 * fan_r, fan_r)
    sectors = ga.draw_decision_fan(fan_ax, lw=0.9)

    _text_pt(fig, fan_cx, fan_cy + fan_r * ga.FAN_R_HOLE - 1, "7,174\nsamples",
             FS_LEAD, ha="center", va="top", fontweight="bold", linespacing=1.15,
             label="centre")

    # One combined "subset -> method" label per sector, placed radially OUTSIDE
    # the arc at that sector's mid-angle. Alignment follows the angle so labels
    # lean away from the fan: right-aligned on the left flank, left-aligned on the
    # right flank, centred above the top. "Mixed" is abbreviated because the full
    # "Mixed platforms" ends 0.3 pt short of the right margin -- too tight to ship.
    label_names = {"Mixed platforms": "Mixed"}
    label_r = fan_r * ga.FAN_R_LABEL
    for name, _count, method, _true_span, _span, mid_deg in sectors:
        text = f"{label_names.get(name, name)}\n→ {method}"
        cos_mid = float(np.cos(np.radians(mid_deg)))
        x = fan_cx + label_r * cos_mid
        y = fan_cy + label_r * float(np.sin(np.radians(mid_deg)))
        if cos_mid < -0.30:
            ha, va = "right", "center"
        elif cos_mid > 0.30:
            ha, va = "left", "center"
        else:
            # Above the top of the arc, the label sits on the radius rather than
            # centred on it, so pull it back in or it drifts away from its sector.
            ha, va = "center", "bottom"
            y = fan_cy + fan_r * 1.01
        _text_pt(fig, x, y, text, FS_BODY, ha=ha, va=va,
                 linespacing=1.15, label=f"sector-{name}")

    problems = _report_text_fit(fig, "C", {
        "head": 340.0, "centre": 62.0,
        "sector-Fresh frozen": 100.0, "sector-FFPE": 60.0,
        "sector-RNA-seq": 100.0, "sector-Mixed platforms": 85.0,
    })
    _save(fig, "graphical_abstract_variantC_fan")
    return problems


# ── Entry point ───────────────────────────────────────────────────────────────

BUILDERS = {"A": build_variant_a, "B": build_variant_b, "C": build_variant_c}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=sorted(BUILDERS), action="append",
                        help="build only these variants (repeatable)")
    args = parser.parse_args()
    wanted = args.only or sorted(BUILDERS)

    all_problems: dict[str, list[str]] = {}
    for key in wanted:
        problems = BUILDERS[key]()
        if problems:
            all_problems[key] = problems
        print()

    print(f"page: {PAGE_W_IN * 25.4:.1f} x {PAGE_H_IN * 25.4:.1f} mm, "
          f"aspect {PAGE_W_IN / PAGE_H_IN:.4f}")
    if all_problems:
        print("\nPROBLEMS FOUND -- do not submit until fixed:")
        for key, problems in all_problems.items():
            for problem in problems:
                print(f"  [{key}] {problem}")
        raise SystemExit(1)
    print("all variants pass the size, budget and overflow checks")


if __name__ == "__main__":
    main()
