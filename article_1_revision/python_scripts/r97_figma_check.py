"""r97 — Figma check of the publication figure files (Daniil 2026-11-09, daniil_review_261109.md).

Figma imports an SVG with 1 pt = 4/3 px; Daniil's figure frame (Figma node 1607-116664) is
756 × 1159 px for the 180 × 275 mm page. For every publication SVG in figures_svg/ this script
reports, in Figma px:
  - the font sizes of all texts (rule: 10 px; S5 may keep its small row labels),
  - the size of the whole file (plot + legends) and of the plot area alone (the figure notebooks
    log it in output/wp14/figma_fit/<notebook>.tsv: axes, tick labels and titles without
    legends and colour bars, which Daniil moves by hand),
  - whether the plot area fits its slot (+2 px tolerance) and the frame.
Output: output/wp14/figma_check.tsv. Exit code 1 if any rule fails.
Run: python r97_figma_check.py (from article_1_revision/)."""
import re
import sys
from pathlib import Path

import pandas as pd

REV = Path(__file__).resolve().parent
FIG = REV / "figures_svg"
FIT_DIR = REV / "output" / "wp14" / "figma_fit"
OUT = REV / "output" / "wp14" / "figma_check.tsv"
PX_PER_PT = 4 / 3
FRAME_PX = (756, 1159)
FONT_PX = 10.0
TOLERANCE_PX = 2.0
# panels allowed to keep smaller text (Daniil 2026-11-09: large clustermap with 87 metric names)
SMALL_FONT_ALLOWED = {"figS5_metric_correlation_clusters"}
# publication panels (review-only files such as figS2_..._all_cohorts are not checked)
PUBLICATION_PREFIXES = ("fig1E", "fig2A", "fig3_", "fig4", "fig5", "fig6", "figS2_merged_distributions.",
                        "figS4", "figS5", "figS6", "figS14", "figS16", "figS17", "figS18")


def svg_size_px(text: str) -> tuple[float, float]:
    """Width and height of the SVG in Figma px (matplotlib writes pt)."""
    width = float(re.search(r'<svg[^>]* width="([\d.]+)pt"', text).group(1))
    height = float(re.search(r'<svg[^>]* height="([\d.]+)pt"', text).group(1))
    return width * PX_PER_PT, height * PX_PER_PT


def font_sizes_px(text: str) -> list[float]:
    """Every font size of a <text> element, in Figma px (matplotlib's "px" is pt)."""
    sizes = re.findall(r"font-size: ([\d.]+)px", text) + re.findall(r"font: (?:\w+ )*([\d.]+)px", text)
    return [round(float(s) * PX_PER_PT, 2) for s in sizes]


def load_fit_log() -> pd.DataFrame:
    """Plot-area sizes logged by the notebooks (one file per notebook)."""
    frames = [pd.read_csv(p, sep="\t") for p in sorted(FIT_DIR.glob("*.tsv"))]
    return pd.concat(frames).drop_duplicates("stem", keep="last").set_index("stem") if frames else pd.DataFrame()


def check_one(svg: Path, fit: pd.DataFrame) -> dict:
    """One row of the check table."""
    text = svg.read_text()
    width, height = svg_size_px(text)
    sizes = font_sizes_px(text)
    stem = svg.stem
    off_size = sorted({s for s in sizes if abs(s - FONT_PX) > 0.05})
    row = {"stem": stem, "file_w_px": round(width, 1), "file_h_px": round(height, 1),
           "font_sizes_px": ", ".join(f"{s:g}" for s in sorted(set(sizes))),
           "font_ok": not off_size or stem in SMALL_FONT_ALLOWED}
    if stem in fit.index:
        r = fit.loc[stem]
        row.update(plot_w_px=r.plot_w_px, plot_h_px=r.plot_h_px, slot_w_px=r.slot_w_px, slot_h_px=r.slot_h_px)
        slot_w = r.slot_w_px if pd.notna(r.slot_w_px) else FRAME_PX[0]
        slot_h = r.slot_h_px if pd.notna(r.slot_h_px) else FRAME_PX[1]
        row["fits_slot"] = bool(r.plot_w_px <= slot_w + TOLERANCE_PX and r.plot_h_px <= slot_h + TOLERANCE_PX)
    else:
        row.update(plot_w_px=None, plot_h_px=None, slot_w_px=None, slot_h_px=None, fits_slot=False)
    return row


def main() -> int:
    fit = load_fit_log()
    svgs = sorted(p for p in FIG.glob("*.svg") if p.name.startswith(PUBLICATION_PREFIXES))
    table = pd.DataFrame([check_one(p, fit) for p in svgs])
    table.to_csv(OUT, sep="\t", index=False)
    failed = table[~(table["font_ok"] & table["fits_slot"])]
    print(f"{len(table)} publication SVGs; {len(failed)} fail → {OUT.relative_to(REV)}")
    if len(failed):
        print(failed[["stem", "font_sizes_px", "plot_w_px", "plot_h_px", "slot_w_px", "slot_h_px"]].to_string(index=False))
    return 1 if len(failed) else 0


if __name__ == "__main__":
    sys.exit(main())
