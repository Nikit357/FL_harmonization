#!/usr/bin/env python
"""Figma-ready text overlays for the revision-round figures (plan Phase 2), 2026-09-25.

The 2026-09-20 script `split_panel_text_260920.py` is kept unchanged (plan §5): it is
wired to the 21 panels of that date, their Figma node ids and the 260920 layout. This
driver imports its text extraction and overlay writer and applies them to

* the eight composite figures of `figures/article2_figures_260925.py`, each drawn at
  the reference frame's size, so one figure = one Figma frame and the overlay scale is
  exactly 2 px per pt; and
* Supplementary Figures 11 and 13, which are NOT redrawn (their gene-level panels are
  unchanged) but re-laid out from the 260920 panels at 1/1.5 of their old size so each
  frame fits the reference frame (C50).

For every item it writes `<name>_text.svg` (Inter TEXT, typography as presentation
attributes) next to a text-free 300 dpi artwork PNG resized to the box's exact aspect,
copies both plus the full PDF into `figures/for_figma_upload/<name>/`, and writes the
geometry to `figures/figma_layout_260925.md` and `overlay_manifest_260925.json`.

    python tools/split_figure_text_260925.py
"""

from __future__ import annotations

import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import split_panel_text_260920 as sp  # noqa: E402

PANELS = ROOT / "figures" / "panels_260925"
EDIT = PANELS / "editable"
OLD_PANELS = ROOT / "figures" / "panels_260917"
OLD_EDIT = OLD_PANELS / "editable_260920"
UPLOAD = ROOT / "figures" / "for_figma_upload"
LAYOUT_MD = ROOT / "figures" / "figma_layout_260925.md"
FRAME_W, FRAME_H = 756, 1159  # reference frame 637:93145
PAD, GAP, LETTER_ROW = 30, 24, 34  # the 260920 layout conventions

# Working name -> the figure it currently is. Final numbers are Phase 5's.
COMPOSITES = {
    "fig_markers_lm": "Figure 4 (classes L, M)",
    "fig_prediction_n": "Figure 5 (class N)",
    "fig_election": "new figure: election structure (old Figure 5E-G)",
    "sfig_harshness": "Supplementary Figure 12 (harshness), rebuilt",
    "sfig_lmn_scatter": "new supplementary: L/M/N scatterplots",
    "sfig_metric_clustermap": "new supplementary: metric cross-correlation clustermap",
    "sfig_expression": "new supplementary: expression, linear vs non-linear "
    "(replaces Figure 4A/B and Supplementary Figure 14)",
    "sfig_pca": "new supplementary: per-component PCA (Figure 1C + Supp. Figure 2F)",
}

# Existing panels, re-laid out: rows of (letter, panel), placed left to right, at a
# shrink factor. C50 asks for 1.5-2x smaller; Supplementary Figure 11 is shrunk by 1.2
# only, because at 1/1.5 its gene labels fall to 4.9 px, under the 6 px legibility
# floor of the 260920 pipeline. 1/1.2 already fits the reference frame.
RELAID = {
    "sfig_marker_qc": (
        "Supplementary Figure 11 (marker panel QC), re-laid out",
        [
            [("A", "a2_p15_panel_coverage"), ("B", "a2_p16_qc_gate")],
            [("C", "a2_p17_rho_by_signature")],
        ],
        1 / 1.2,
    ),
    "sfig_gene_method": (
        "Supplementary Figure 13 (gene by method), re-laid out",
        [[("A", "a2_p18_gene_method_clustermap")]],
        1 / 1.5,
    ),
}


def _fit_png(src: Path, dst: Path, w: int, h: int) -> tuple[int, int]:
    """Copy a 300 dpi artwork, resized to the box's exact aspect (Figma FILL crops)."""
    im = Image.open(src).convert("RGBA")
    target = (im.size[0], round(im.size[0] * h / w))
    im.resize(target, Image.LANCZOS).save(dst)
    return target


def composite(name: str) -> dict:
    svg = PANELS / f"{name}.svg"
    w_pt, h_pt = sp._svg_size_pt(ET.parse(svg).getroot())
    w, h = round(w_pt * 2), round(h_pt * 2)
    assert w <= FRAME_W and h <= FRAME_H, f"{name}: {w} x {h} exceeds the frame"
    items = sp.iter_text(svg)
    txt = EDIT / f"{name}_text.svg"
    n = sp.write_overlay_svg(items, txt, w / w_pt, h / h_pt, w, h)
    art = EDIT / f"{name}_artwork_300dpi.png"
    size = _fit_png(art, art, w, h)
    out = UPLOAD / name
    out.mkdir(parents=True, exist_ok=True)
    for f in (txt, art, PANELS / f"{name}.pdf", PANELS / f"{name}.png"):
        shutil.copy2(f, out / f.name)
    small = min((it.size * w / w_pt for it in items), default=0)
    return {
        "kind": "composite",
        "figure": COMPOSITES[name],
        "frame": [w, h],
        "boxes": [{"letter": "all", "panel": name, "x": 0, "y": 0, "w": w, "h": h}],
        "n_text": n,
        "min_text_px": round(small, 2),
        "artwork_px": list(size),
    }


def relaid(name: str) -> dict:
    """Place existing 260920 panels at `shrink` of their 260920 boxes, in rows."""
    label, rows, shrink = RELAID[name]
    old = sp.parse_layout()
    boxes, y = [], PAD
    for row in rows:
        x, row_h = PAD, 0
        for letter, panel in row:
            p = old[panel]
            bw, bh = round(p.w * shrink), round(p.h * shrink)
            boxes.append(
                {
                    "letter": letter,
                    "panel": panel,
                    "x": x,
                    "y": y + LETTER_ROW,
                    "w": bw,
                    "h": bh,
                }
            )
            x += bw + GAP
            row_h = max(row_h, bh)
        y += LETTER_ROW + row_h + GAP
    w, h = FRAME_W - 6, y - GAP + PAD  # 750 wide, as the 260920 frames
    assert h <= FRAME_H, f"{name}: {h} px exceeds the frame"
    out = UPLOAD / name
    out.mkdir(parents=True, exist_ok=True)
    preview = Image.new("RGB", (w * 2, h * 2), "white")
    draw = ImageDraw.Draw(preview)
    from matplotlib import font_manager

    font = ImageFont.truetype(
        font_manager.findfont(
            font_manager.FontProperties(family="DejaVu Sans", weight="bold")
        ),
        40,
    )
    n_total, small = 0, []
    for b in boxes:
        svg = OLD_PANELS / f"{b['panel']}.svg"
        w_pt, h_pt = sp._svg_size_pt(ET.parse(svg).getroot())
        items = sp.iter_text(svg)
        # The 260917 panels predate the American-spelling rule (principle D7); their
        # artwork is text-free, so the label is corrected here, in the overlay only.
        for it in items:
            it.text = it.text.replace("centre", "center").replace("colour", "color")
        txt = EDIT / f"{b['panel']}_text_260925.svg"
        n_total += sp.write_overlay_svg(
            items, txt, b["w"] / w_pt, b["h"] / h_pt, b["w"], b["h"]
        )
        small += [it.size * b["w"] / w_pt for it in items]
        art = EDIT / f"{b['panel']}_artwork_300dpi_260925.png"
        _fit_png(OLD_EDIT / f"{b['panel']}_artwork_300dpi.png", art, b["w"], b["h"])
        for f in (txt, art):
            shutil.copy2(f, out / f.name)
        full = Image.open(OLD_PANELS / f"{b['panel']}.png").convert("RGB")
        preview.paste(
            full.resize((b["w"] * 2, b["h"] * 2), Image.LANCZOS),
            (b["x"] * 2, b["y"] * 2),
        )
        draw.text(
            (b["x"] * 2 - 40, (b["y"] - LETTER_ROW) * 2),
            b["letter"],
            fill="black",
            font=font,
        )
    preview.save(PANELS / f"{name}_preview.png")
    shutil.copy2(PANELS / f"{name}_preview.png", out / f"{name}_preview.png")
    return {
        "kind": "relaid",
        "figure": label,
        "frame": [w, h],
        "boxes": boxes,
        "shrink": round(shrink, 4),
        "n_text": n_total,
        "min_text_px": round(min(small), 2),
    }


# Where each frame was placed in Figma (file t8bFgusleBEwB9ht7rORCH, Page 3 `1013:3`),
# recorded here so the layout document keeps it on every rerun. The election frame's
# labels were replaced on 2026-09-25 after the PCReg fix (15_pcreg_fix.md).
FIGMA_PLACED = {
    "fig_markers_lm": "1321:3",
    "fig_prediction_n": "1321:7",
    "fig_election": "1321:11",
    "sfig_harshness": "1321:15",
    "sfig_lmn_scatter": "1321:19",
    "sfig_metric_clustermap": "1321:23",
    "sfig_expression": "1321:27",
    "sfig_pca": "1321:31",
    "sfig_marker_qc": "1321:35",
    "sfig_gene_method": "1321:46",
}
FIGMA_NOTE = (
    "## Placed in Figma, 2026-09-25\n\n"
    "File `t8bFgusleBEwB9ht7rORCH`, **Page 3** (`1013:3`, empty before), frames in one row "
    "at y = 0, 150 px apart, a title TEXT node above each. Each panel is a `FRAME` holding a "
    "locked `artwork` rectangle (text-free 300 dpi image fill) and a `labels` frame of Inter "
    "TEXT nodes imported from `<panel>_text.svg`. Checked at placement: overlay within 1 px "
    "of its box, TEXT count equal to the SVG, every label Inter, every artwork an IMAGE "
    "fill. Page 2: 58 top-level nodes before and after, 0 geometry or child-count "
    "differences (`figma_snapshots/page2_{before,after}_revision_260925.json`).\n\n"
    "| frame | Figma node |\n|---|---|\n"
)


def write_layout(manifest: dict) -> None:
    lines = [
        "# Figma layout for the revision-round figures — computed 2026-09-25",
        "",
        "Every frame must fit the reference frame `637:93145`, **756 x 1159 px** "
        "(C50). 2 px = 1 pt. Each composite is one artwork + one `labels` overlay "
        "filling the frame; the re-laid figures place the 260920 panels at 1/1.5 "
        "of their old boxes. Final figure numbers are assigned in Phase 5, so the "
        "frames below are named by working name. Written by "
        "`tools/split_figure_text_260925.py`.",
        "",
    ]
    for name, m in manifest.items():
        lines += [
            f"## `{name}` — {m['figure']}",
            "",
            f"Frame **{m['frame'][0]} x {m['frame'][1]}**, {m['n_text']} TEXT "
            f"nodes, smallest label {m['min_text_px']} px.",
            "",
            "| letter | panel | x | y | w | h |",
            "|---|---|---|---|---|---|",
        ]
        lines += [
            f"| {b['letter']} | `{b['panel']}` | {b['x']} | {b['y']} | {b['w']} | "
            f"{b['h']} |"
            for b in m["boxes"]
        ]
        lines.append("")
    lines.append(
        FIGMA_NOTE + "\n".join(f"| `{k}` | `{v}` |" for k, v in FIGMA_PLACED.items())
    )
    LAYOUT_MD.write_text("\n".join(lines) + "\n")


def main() -> int:
    EDIT.mkdir(parents=True, exist_ok=True)
    manifest = {n: composite(n) for n in COMPOSITES}
    manifest |= {n: relaid(n) for n in RELAID}
    for n, m in manifest.items():
        print(
            f"{n:24s} {m['frame'][0]:4d} x {m['frame'][1]:4d} px  {m['n_text']:4d} "
            f"text  min {m['min_text_px']:.1f} px"
        )
    (EDIT / "overlay_manifest_260925.json").write_text(json.dumps(manifest, indent=1))
    write_layout(manifest)
    print(f"wrote {LAYOUT_MD.relative_to(ROOT)} and {UPLOAD.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
