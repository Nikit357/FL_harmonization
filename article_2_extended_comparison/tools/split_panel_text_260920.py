#!/usr/bin/env python
"""Split each Article 2 panel SVG into text-free artwork and a text-only overlay.

The seven Article 2 frames on Page 2 of Figma file ``t8bFgusleBEwB9ht7rORCH``
were assembled on 2026-09-20 with every panel as a single rectangle carrying a
300 dpi PNG fill, so no label, tick or annotation could be edited. This script
is the offline half of the repair described in
``figma_editable_text_plan_260920.md``: for every panel it writes

* ``<panel>_artwork.svg``       -- the same drawing with every ``<text>`` removed
* ``<panel>_artwork_300dpi.png``-- that artwork rendered for the Figma image fill
* ``<panel>_text.svg``          -- only the text, pre-scaled to the panel's placed
                                   pixel box, with all typography as presentation
                                   attributes
* ``overlay_manifest.json``     -- geometry, counts and checksums for the Figma step

Two measured facts drive the design. Figma's SVG reader ignores ``font-size``
inside a ``style=`` attribute, which is the only place matplotlib ever writes it,
so the overlay must use presentation attributes or every label imports at 10 px.
And the placed boxes have x and y scale factors that differ by up to 0.7 %, so the
overlay is scaled here with independent ``sx``/``sy`` rather than with Figma's
uniform ``rescale()``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
SVG = "{%s}" % SVG_NS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PANEL_DIR = ROOT / "figures" / "panels_260917"
LAYOUT_MD = ROOT / "figures" / "figma_layout_260920.md"
DEFAULT_OUT = PANEL_DIR / "editable_260920"

OVERLAY_FONT = "Inter"
DEFAULT_FILL = "#262626"
LEGIBILITY_FLOOR_PX = 6.0

# Figma node ids, read from the live file on 2026-09-20. The frame id is the
# figure frame; the rect id is the panel rectangle whose image fill is replaced
# and which then becomes the locked ``artwork`` child of the new panel frame.
FIGMA_NODES: dict[str, tuple[str, str]] = {
    "a2_p14_expression_scatter_01_raw": ("1255:2", "1256:2"),
    "a2_p14_expression_scatter_13_fsmvn": ("1255:2", "1256:3"),
    "a2_p1_rho_vs_margin": ("1255:2", "1256:4"),
    "a2_p2_margin_ranking": ("1255:2", "1256:5"),
    "a2_p3_agreement_specific": ("1255:2", "1256:6"),
    "a2_p7_strategy_imputation_method": ("1255:2", "1256:7"),
    "a2_p12_raw_to_harmonized": ("1255:2", "1256:8"),
    "a2_p4_lobo_ranking": ("1255:3", "1256:9"),
    "a2_p5_per_batch": ("1255:3", "1256:10"),
    "a2_p6_singleclass_audit": ("1255:3", "1256:11"),
    "a2_p8_generalizability_index": ("1255:3", "1256:12"),
    "a2_p9_cross_election_circos": ("1255:3", "1256:13"),
    "a2_p10_venn_supervenn": ("1255:3", "1256:14"),
    "a2_p13_election_sankey": ("1255:3", "1256:15"),
    "a2_p15_panel_coverage": ("1255:5", "1256:16"),
    "a2_p16_qc_gate": ("1255:5", "1256:17"),
    "a2_p17_rho_by_signature": ("1255:5", "1256:18"),
    "a2_p11_harshness_lmn": ("1255:6", "1256:19"),
    "a2_p18_gene_method_clustermap": ("1255:7", "1256:20"),
    "a2_p14_expression_scatter_12_scanorama": ("1255:8", "1256:21"),
    "a2_p14_expression_scatter_29_combat_ref": ("1255:8", "1256:22"),
}


# --------------------------------------------------------------------------- #
# Placement table
# --------------------------------------------------------------------------- #
@dataclass
class Placement:
    """Where one panel sits inside its Figma frame."""

    frame: str
    letter: str
    x: int
    y: int
    w: int
    h: int


_FRAME_RE = re.compile(r"^## `([^`]+)`")
_ROW_RE = re.compile(
    r"^\|\s*([A-Z])\s*\|\s*`([^`]+)`\s*\|\s*(-?\d+)\s*\|\s*(-?\d+)\s*"
    r"\|\s*(\d+)\s*\|\s*(\d+)\s*\|"
)


def parse_layout(path: Path = LAYOUT_MD) -> dict[str, Placement]:
    """Parse the per-frame panel tables of the Figma layout document.

    Parameters
    ----------
    path : Path
        ``figures/figma_layout_260920.md``.

    Returns
    -------
    dict[str, Placement]
        Panel stem -> placement. The layout document is the single source of
        truth for panel geometry; nothing here is hardcoded.
    """
    placements: dict[str, Placement] = {}
    frame = ""
    for line in path.read_text().splitlines():
        m = _FRAME_RE.match(line)
        if m:
            frame = m.group(1)
            continue
        m = _ROW_RE.match(line)
        if m:
            letter, panel, x, y, w, h = m.groups()
            placements[panel] = Placement(
                frame, letter, int(x), int(y), int(w), int(h)
            )
    missing = sorted(set(FIGMA_NODES) - set(placements))
    if missing:
        raise SystemExit(
            f"{path.name} has no row for: {', '.join(missing)} — a panel with no "
            "row would silently end up with no overlay"
        )
    return placements


# --------------------------------------------------------------------------- #
# SVG text extraction
# --------------------------------------------------------------------------- #
@dataclass
class TextItem:
    """One rendered string lifted out of a panel SVG."""

    text: str
    x: float
    y: float
    size: float
    anchor: str
    rotation: float
    fill: str
    italic: bool = False
    mixed_italic: bool = False
    is_tick: bool = False
    ancestor_ids: tuple[str, ...] = field(default_factory=tuple)


_IDENT = np.eye(3)
_NUM = r"[-+]?[\d.]+(?:[eE][-+]?\d+)?"
_XFORM_RE = re.compile(r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)")


def _parse_transform(value: str | None) -> np.ndarray:
    """Turn an SVG ``transform`` attribute into a 3x3 affine matrix."""
    if not value:
        return _IDENT
    m = _IDENT
    for op, args in _XFORM_RE.findall(value):
        nums = [float(v) for v in re.findall(_NUM, args)]
        if op == "matrix":
            a, b, c, d, e, f = nums
            t = np.array([[a, c, e], [b, d, f], [0, 0, 1]])
        elif op == "translate":
            tx = nums[0]
            ty = nums[1] if len(nums) > 1 else 0.0
            t = np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1]])
        elif op == "scale":
            sx = nums[0]
            sy = nums[1] if len(nums) > 1 else sx
            t = np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]])
        elif op == "rotate":
            a = math.radians(nums[0])
            ca, sa = math.cos(a), math.sin(a)
            t = np.array([[ca, -sa, 0], [sa, ca, 0], [0, 0, 1]])
            if len(nums) == 3:
                cx, cy = nums[1], nums[2]
                to = np.array([[1, 0, cx], [0, 1, cy], [0, 0, 1]])
                back = np.array([[1, 0, -cx], [0, 1, -cy], [0, 0, 1]])
                t = to @ t @ back
        else:  # skewX / skewY
            raise ValueError(f"unsupported transform {op!r}: text would be sheared")
        m = m @ t
    return m


def _parse_style(value: str | None) -> dict[str, str]:
    """Parse a ``style="k: v; ..."`` attribute into a dict."""
    if not value:
        return {}
    out = {}
    for part in value.split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def _decompose(m: np.ndarray) -> tuple[float, float, float, float]:
    """Return (tx, ty, rotation_deg, uniform_scale) of an affine matrix.

    Raises if the matrix carries shear or a non-uniform scale — matplotlib never
    emits either on a text element, so encountering one means the walk has gone
    wrong rather than that the case needs handling.
    """
    a, c, e = m[0]
    b, d, f = m[1]
    sx = math.hypot(a, b)
    sy = math.hypot(c, d)
    if sx == 0 or sy == 0:
        raise ValueError("degenerate text transform")
    shear = (a * c + b * d) / (sx * sy)
    if abs(shear) > 1e-6 or abs(sx - sy) > 1e-6 * max(sx, sy):
        raise ValueError(f"sheared or non-uniform text transform: {m.tolist()}")
    return e, f, math.degrees(math.atan2(b, a)), sx


def iter_text(svg_path: Path) -> list[TextItem]:
    """Walk an SVG, compose ancestor transforms, and return one TextItem per
    rendered string.

    Parameters
    ----------
    svg_path : Path
        A matplotlib SVG exported with ``svg.fonttype = "none"``.

    Returns
    -------
    list[TextItem]
        One item per ``<text>`` element, with mathtext ``<tspan>`` runs merged
        into a single string. A mathtext annotation is emitted by matplotlib as
        one ``<text>`` per glyph-run with no ``x``/``y`` of its own, positioned by
        an ancestor ``<g transform="translate(...)">``; merging is what keeps a
        ``rho = 0.83`` label one editable box instead of eleven.
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()
    items: list[TextItem] = []

    def walk(node: ET.Element, ctm: np.ndarray, ids: tuple[str, ...]) -> None:
        node_id = node.get("id")
        if node_id:
            ids = ids + (node_id,)
        if node.tag == SVG + "text":
            # _text_item applies the element's own transform itself, so it is
            # handed the ancestor matrix only. Composing it here as well would
            # double-apply it — invisible on the rotate(-0 ...) no-op matplotlib
            # puts on every horizontal label, and a 180 degree flip plus a
            # displacement on every translate(...) rotate(-90) axis title.
            item = _text_item(node, ctm, ids)
            if item is not None:
                items.append(item)
            return
        here = ctm @ _parse_transform(node.get("transform"))
        for child in node:
            walk(child, here, ids)

    walk(root, _IDENT, ())
    return items


def _text_item(
    node: ET.Element, ctm: np.ndarray, ids: tuple[str, ...]
) -> TextItem | None:
    """Build one TextItem from a ``<text>`` element and its composed transform."""
    own = _parse_style(node.get("style"))
    spans = node.findall(SVG + "tspan")

    if spans:
        first = _parse_style(spans[0].get("style"))
        style = {**own, **first}
        lx = float(spans[0].get("x", node.get("x", 0.0)))
        ly = float(spans[0].get("y", node.get("y", 0.0)))
        text = "".join(s.text or "" for s in spans)
        obl = [
            _parse_style(s.get("style")).get("font-style") in {"oblique", "italic"}
            for s in spans
            if (s.text or "").strip()
        ]
        # A mathtext label is usually upright prose with one italic symbol in it
        # (the rho of "mean marker rho"). Italicising the merged string because a
        # single glyph was oblique would be worse than leaving it upright, so the
        # item is italic only when every glyph is.
        italic = bool(obl) and all(obl)
        mixed_italic = any(obl) and not italic
        # Per-glyph tspan positions are absolute in the text's own frame, so the
        # merged string must start at the first glyph and grow rightwards.
        anchor = "start"
    else:
        style = own
        lx = float(node.get("x", 0.0))
        ly = float(node.get("y", 0.0))
        text = "".join(node.itertext())
        italic = style.get("font-style") in {"oblique", "italic"}
        mixed_italic = False
        anchor = style.get("text-anchor", "start")

    if not text.strip():
        return None

    size = style.get("font-size")
    if size is None:
        raise ValueError(f"<text> without font-size in {ids}: {text!r}")

    m = ctm @ _parse_transform(node.get("transform"))
    px, py = (m @ np.array([lx, ly, 1.0]))[:2]
    _, _, rot, scale = _decompose(m)

    return TextItem(
        text=text,
        x=float(px),
        y=float(py),
        size=float(size.removesuffix("px")) * scale,
        anchor=anchor,
        rotation=rot,
        fill=style.get("fill", DEFAULT_FILL),
        italic=italic,
        mixed_italic=mixed_italic,
        is_tick=any(i.startswith(("xtick_", "ytick_")) for i in ids),
        ancestor_ids=ids,
    )


# --------------------------------------------------------------------------- #
# Derivative writers
# --------------------------------------------------------------------------- #
def _svg_size_pt(root: ET.Element) -> tuple[float, float]:
    """Read the root width/height in points."""
    w = float(root.get("width", "0").removesuffix("pt"))
    h = float(root.get("height", "0").removesuffix("pt"))
    return w, h


def write_artwork_svg(src: Path, dst: Path) -> tuple[float, float]:
    """Copy an SVG with every ``<text>`` element removed.

    Returns the root width and height in points. Groups emptied by the removal
    are dropped too, so the artwork carries no residue of its type.
    """
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", XLINK_NS)
    tree = ET.parse(src)
    root = tree.getroot()

    def prune(node: ET.Element) -> None:
        for child in list(node):
            if child.tag == SVG + "text":
                node.remove(child)
            else:
                prune(child)
                if (
                    child.tag == SVG + "g"
                    and len(child) == 0
                    and not (child.text or "").strip()
                ):
                    node.remove(child)

    prune(root)
    dst.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))
    return _svg_size_pt(root)


def write_overlay_svg(
    items: list[TextItem], dst: Path, sx: float, sy: float, w: int, h: int
) -> int:
    """Write the text-only overlay, pre-scaled to the placed pixel box.

    Every typographic property is a presentation attribute, never a ``style=``
    declaration: Figma's SVG reader silently drops ``style``-borne ``font-size``
    and imports the label at its own 10 px default.

    Returns the number of ``<text>`` elements written.
    """
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<svg xmlns="{SVG_NS}" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" version="1.1">',
    ]
    for it in items:
        x, y = it.x * sx, it.y * sy
        attrs = [
            f'x="{x:.4f}"',
            f'y="{y:.4f}"',
            f'font-size="{it.size * sx:.4f}"',
            f'font-family="{OVERLAY_FONT}"',
            f'fill="{it.fill}"',
        ]
        if it.anchor != "start":
            attrs.append(f'text-anchor="{it.anchor}"')
        if it.italic:
            attrs.append('font-style="italic"')
        if abs(it.rotation) > 1e-9:
            attrs.append(f'transform="rotate({it.rotation:.4f} {x:.4f} {y:.4f})"')
        body = (
            it.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        lines.append(f'  <text {" ".join(attrs)}>{body}</text>')
    lines.append("</svg>")
    dst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(items)


def render_png(
    artwork_svg: Path,
    dst: Path,
    dpi: int,
    w_pt: float,
    placed_w: int,
    placed_h: int,
    supersample: int = 2,
) -> tuple[int, int]:
    """Render a text-free artwork SVG to PNG at ``dpi``.

    cairosvg converts absolute units at 96 dpi, so the scale that yields a true
    ``dpi`` raster is ``dpi / 96``, not ``dpi / 72``.

    The render is done at ``supersample`` times the target and downsampled.
    cairosvg antialiases every path independently, which leaves a pale seam at
    each shared edge; on a heatmap of thousands of adjacent cells -- the gene by
    method clustermap is 7,560 paths -- those seams read as visible grid lines
    that the matplotlib raster does not have. Downsampling averages them away.

    The result is then resized to the exact aspect ratio of the placed box. The
    boxes were rounded to whole pixels when the frames were laid out, so their
    aspect differs from the drawing's by up to 0.7 %; left alone, Figma's FILL
    scale mode would crop that difference away and slide the artwork out from
    under the text overlay, which is stretched by sx and sy independently.
    """
    import cairosvg
    from PIL import Image

    expected = round(w_pt * dpi / 72.0)
    cairosvg.svg2png(
        url=str(artwork_svg), write_to=str(dst), scale=dpi * supersample / 96.0
    )
    scale = expected / placed_w
    target = (expected, round(placed_h * scale))
    Image.open(dst).convert("RGBA").resize(target, Image.LANCZOS).save(dst)
    size = Image.open(dst).size
    if size != target:
        raise SystemExit(f"{dst.name}: got {size}, expected {target}")
    # Compare in pixels, not in ratio: the target height is a rounded integer, so
    # a panel whose exact height lands on .5 is off by half a pixel by construction.
    if abs(size[1] - placed_h * scale) > 1.0:
        raise SystemExit(f"{dst.name}: aspect {size} does not match the placed box")
    return size


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def process(
    panel: str,
    place: Placement,
    out_dir: Path,
    dpi: int,
    renderer: str,
    labels_only: bool,
    supersample: int = 2,
) -> dict:
    """Produce the three derivatives of one panel and return its manifest entry."""
    src = PANEL_DIR / f"{panel}.svg"
    art_svg = out_dir / f"{panel}_artwork.svg"
    art_png = out_dir / f"{panel}_artwork_{dpi}dpi.png"
    txt_svg = out_dir / f"{panel}_text.svg"

    n_elements = src.read_text(errors="ignore").count("<text")
    items = iter_text(src)
    if labels_only:
        items = [it for it in items if not it.is_tick]

    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", XLINK_NS)
    if labels_only:
        w_pt, h_pt = _strip_selected_text(src, art_svg, keep_ticks=True)
    else:
        w_pt, h_pt = write_artwork_svg(src, art_svg)

    sx = place.w / w_pt
    sy = place.h / h_pt
    n_items = write_overlay_svg(items, txt_svg, sx, sy, place.w, place.h)

    png_size = (None, None)
    if renderer == "cairosvg":
        png_size = render_png(
            art_svg, art_png, dpi, w_pt, place.w, place.h, supersample
        )

    frame_id, rect_id = FIGMA_NODES[panel]
    return {
        "frame": place.frame,
        "frame_id": frame_id,
        "rect_id": rect_id,
        "letter": place.letter,
        "placed": [place.x, place.y, place.w, place.h],
        "svg_pt": [round(w_pt, 4), round(h_pt, 4)],
        "sx": round(sx, 6),
        "sy": round(sy, 6),
        "n_text_elements": n_elements,
        "n_text_items": n_items,
        "n_italic": sum(it.italic for it in items),
        "n_mixed_italic": sum(it.mixed_italic for it in items),
        "n_tick": sum(it.is_tick for it in items),
        "min_scaled_size": round(min((it.size * sx for it in items), default=0.0), 2),
        "png_size": list(png_size),
        "sha256": {
            "artwork_svg": _sha256(art_svg),
            "text_svg": _sha256(txt_svg),
            "artwork_png": _sha256(art_png) if art_png.exists() else None,
        },
        "_items": items,
    }


def _strip_selected_text(src: Path, dst: Path, keep_ticks: bool) -> tuple[float, float]:
    """Artwork writer for ``--labels-only``: keep tick text baked, drop the rest."""
    tree = ET.parse(src)
    root = tree.getroot()

    def prune(node: ET.Element, ids: tuple[str, ...]) -> None:
        node_id = node.get("id")
        here = ids + (node_id,) if node_id else ids
        for child in list(node):
            if child.tag == SVG + "text":
                tick = any(i.startswith(("xtick_", "ytick_")) for i in here)
                if not (keep_ticks and tick):
                    node.remove(child)
            else:
                prune(child, here)
                if (
                    child.tag == SVG + "g"
                    and len(child) == 0
                    and not (child.text or "").strip()
                ):
                    node.remove(child)

    prune(root, ())
    dst.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))
    return _svg_size_pt(root)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--panels",
        default="all",
        help="comma-separated panel stems, or 'all' (default: all 21)",
    )
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument(
        "--renderer",
        choices=["cairosvg", "none"],
        default="cairosvg",
        help="'none' skips the PNG render and writes the two SVGs only",
    )
    ap.add_argument(
        "--labels-only",
        action="store_true",
        help="leave tick labels baked into the artwork and lift only the rest",
    )
    ap.add_argument(
        "--supersample",
        type=int,
        default=2,
        help="render the artwork at this multiple of --dpi and downsample, to "
        "remove cairosvg's per-path antialiasing seams (default: 2)",
    )
    ap.add_argument("--report", action="store_true", help="print the conversion audit")
    args = ap.parse_args(argv)

    placements = parse_layout()
    panels = (
        list(FIGMA_NODES)
        if args.panels == "all"
        else [p.strip() for p in args.panels.split(",")]
    )
    unknown = [p for p in panels if p not in FIGMA_NODES]
    if unknown:
        raise SystemExit(f"unknown panel(s): {', '.join(unknown)}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict] = {}
    for panel in panels:
        entry = process(
            panel,
            placements[panel],
            args.out_dir,
            args.dpi,
            args.renderer,
            args.labels_only,
            args.supersample,
        )
        items = entry.pop("_items")
        manifest[panel] = entry
        if args.report:
            _report(panel, entry, items)
        else:
            print(
                f"{panel:45s} {entry['n_text_elements']:4d} -> "
                f"{entry['n_text_items']:4d} text  sx={entry['sx']:.4f}"
            )

    out = {
        "generated": "2026-09-20",
        "source": str(PANEL_DIR.relative_to(ROOT)),
        "font": OVERLAY_FONT,
        "dpi": args.dpi,
        "supersample": args.supersample,
        "labels_only": args.labels_only,
        "panels": manifest,
    }
    (args.out_dir / "overlay_manifest.json").write_text(json.dumps(out, indent=1))
    total = sum(m["n_text_items"] for m in manifest.values())
    print(f"\n{len(manifest)} panels, {total} text items -> {args.out_dir}")
    return 0


def _report(panel: str, entry: dict, items: list[TextItem]) -> None:
    """Print the per-panel conversion audit."""
    sizes = Counter(round(it.size * entry["sx"], 1) for it in items)
    anchors = Counter(it.anchor for it in items)
    small = [it for it in items if it.size * entry["sx"] < LEGIBILITY_FLOOR_PX]
    print(f"\n=== {panel}  [{entry['frame']} {entry['letter']}]")
    print(
        f"  <text> in {entry['n_text_elements']:4d} -> items out "
        f"{entry['n_text_items']:4d}   (mathtext merge accounts for the difference)"
    )
    print(
        f"  sx={entry['sx']:.4f} sy={entry['sy']:.4f}  italic={entry['n_italic']}"
        f"  mixed-italic={entry['n_mixed_italic']}  ticks={entry['n_tick']}"
    )
    print(f"  sizes px: {dict(sorted(sizes.items()))}")
    print(f"  anchors : {dict(anchors)}")
    if small:
        print(f"  BELOW {LEGIBILITY_FLOOR_PX} px: {len(small)} items, e.g. "
              f"{[i.text[:18] for i in small[:3]]}")
    if entry["n_italic"]:
        ital = [it.text[:28] for it in items if it.italic][:4]
        print(f"  fully italic items: {ital}")
    if entry["n_mixed_italic"]:
        mix = [it.text[:28] for it in items if it.mixed_italic][:4]
        print(f"  mixed-italic mathtext, upright ({entry['n_mixed_italic']}): {mix}")


if __name__ == "__main__":
    sys.exit(main())
