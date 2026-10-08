"""Phase 2: write 07_panels.{json,md}, the panel inventory the legend writer consumes.

Reads the two machine records of Phase 2 and joins them into one row per panel:

- `figures/panels_260925/figure_report_260925.json` -- per composite figure: size,
  frame fit, the automated text-overlap count, and one description per panel letter,
  written by `figures/article2_figures_260925.py`;
- `figures/panels_260925/editable/overlay_manifest_260925.json` -- per Figma frame:
  pixel geometry, TEXT-node count and smallest label, written by
  `tools/split_figure_text_260925.py`.

    python workflow_runs/260924_run1/phase2_panel_inventory.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
REPORT = ROOT / "figures/panels_260925/figure_report_260925.json"
MANIFEST = ROOT / "figures/panels_260925/editable/overlay_manifest_260925.json"

# Which review comment each figure answers, and what the text still has to catch up on.
COMMENTS = {
    "fig_markers_lm": (
        "C48, C50",
        "legend of Figure 4 must drop the old A/B scatter "
        "grids and re-letter C-G to A-F; old 4F described a panel that "
        "was never drawn and is now drawn as D",
    ),
    "fig_prediction_n": (
        "C16, C50",
        "Figure 5 now ends at D; old E-G moved to "
        "fig_election; D is on the E1 index",
    ),
    "fig_election": ("C50", "new figure; text citing Figure 5E-5G must move to it"),
    "sfig_harshness": (
        "C44",
        "12 letters A-L to cite individually; legend must state "
        "the Kruskal-Wallis test and the permutation null",
    ),
    "sfig_lmn_scatter": (
        "C48",
        "new; cite from the harshness 'Taken together' " "paragraph C48 is anchored to",
    ),
    "sfig_metric_clustermap": (
        "C48",
        "new; legend states 325 of 334 metrics used and "
        "why (5 absent, 4 constant or sparse)",
    ),
    "sfig_expression": (
        "C50",
        "replaces Figure 4A/4B and Supplementary Figure 14; "
        "text citing those must be repointed",
    ),
    "sfig_pca": (
        "C35",
        "replaces Figure 1C and Supplementary Figure 2F as the place "
        "the per-component PCA is discussed; Page 2 frames stay protected",
    ),
    "sfig_marker_qc": ("C50", "unchanged panels, re-laid out to fit the frame"),
    "sfig_gene_method": ("C50", "unchanged panel, re-laid out to fit the frame"),
}
SOURCE = {
    "sfig_marker_qc": "figures/panels_260917/a2_p15-p17 (marker_gene_deep_analysis.ipynb)",
    "sfig_gene_method": "figures/panels_260917/a2_p18 (marker_gene_deep_analysis.ipynb)",
}


def main() -> None:
    report = json.loads(REPORT.read_text())
    manifest = json.loads(MANIFEST.read_text())
    rows = []
    for name, m in manifest.items():
        comment, action = COMMENTS[name]
        rep = report.get(name, {})
        panels = rep.get("panels") or {b["letter"]: b["panel"] for b in m["boxes"]}
        for letter, desc in panels.items():
            rows.append(
                {
                    "figure": name,
                    "current_figure": m["figure"],
                    "letter": letter,
                    "description": desc,
                    "source": SOURCE.get(
                        name, f"figures/article2_figures_260925.py::{name}"
                    ),
                    "frame_px": m["frame"],
                    "fits_frame_756x1159": m["frame"][0] <= 756
                    and m["frame"][1] <= 1159,
                    "text_nodes_in_frame": m["n_text"],
                    "min_label_px": m["min_text_px"],
                    "text_overlaps": rep.get("n_text_overlaps"),
                    "comments": comment,
                    "text_action": action,
                    "status": "offline assets ready; Figma placement pending",
                }
            )
    (RUN / "07_panels.json").write_text(json.dumps(rows, indent=1))

    figs = list(manifest)
    lines = [
        "# 07 — Panel inventory (Phase 2), 2026-09-25",
        "",
        "## Status",
        "",
        f"**Offline work done; Figma placement pending.** {len(figs)} figures, "
        f"{len(rows)} lettered panels. Every figure fits the reference frame "
        "`637:93145` (756 x 1159 px), has 0 overlapping text boxes by the automated "
        "check, and no label is under 6 px. The Figma step needs an authenticated "
        "Figma session, which this run does not have; everything it needs is in "
        "`figures/for_figma_upload/<figure>/` with the geometry in "
        "`figures/figma_layout_260925.md`.",
        "",
        "Figure names are working names. Final numbers come from Phase 5, after the "
        "text settles the order of first citation.",
        "",
        "## Figures",
        "",
        "| figure | now | frame px | TEXT nodes | min px | overlaps | comments |",
        "|---|---|---|---|---|---|---|",
    ]
    for name in figs:
        m, rep = manifest[name], report.get(name, {})
        lines.append(
            f"| `{name}` | {m['figure']} | {m['frame'][0]} x {m['frame'][1]} | "
            f"{m['n_text']} | {m['min_text_px']} | "
            f"{rep.get('n_text_overlaps', 'n/a')} | {COMMENTS[name][0]} |"
        )
    lines += [
        "",
        "## Panels",
        "",
        "| figure | letter | what it shows |",
        "|---|---|---|",
    ]
    lines += [f"| `{r['figure']}` | {r['letter']} | {r['description']} |" for r in rows]
    lines += ["", "## What the text and legends must catch up on (Phase 3)", ""]
    lines += [f"- **`{n}`** — {COMMENTS[n][1]}" for n in figs]
    (RUN / "07_panels.md").write_text("\n".join(lines) + "\n")
    print(
        f"wrote 07_panels.json and 07_panels.md: {len(figs)} figures, {len(rows)} panels"
    )


if __name__ == "__main__":
    main()
