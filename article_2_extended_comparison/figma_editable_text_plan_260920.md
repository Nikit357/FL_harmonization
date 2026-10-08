# Making every label in the Article 2 Figma frames editable — implementation plan, 2026-09-20

**Scope:** the seven frames created on Page 2 of Figma file `t8bFgusleBEwB9ht7rORCH` on
2026-09-20 — `Figure 4`, `Figure 5`, `Figure 6 - Recipe`, and `Supplementary Figure 11`–`14`.
**Status:** IMPLEMENTED 2026-09-20. 1,966 editable `TEXT` nodes across the 21 panels;
0 geometry and 0 name differences against the before-snapshot.

---

## Overview

Daniil cannot edit the text in the new frames because **there is no text in them to edit**. Every
one of the 21 panels is a single `RECTANGLE` whose fill is a 300 dpi PNG: axis ticks, legends,
method names and annotations are pixels, not `TEXT` nodes. This was decision 34 of
`f1000_article2_plan_260917.md` §11 — raster fills were chosen over importing 21 SVGs to avoid a
node explosion — and it directly contradicts that same plan's §5.4 hard constraint, *"Every
character on the canvas is a Figma TEXT node, never type baked into an imported SVG."* Figure 6
is the only frame that honours the constraint, because its twelve assets are text-free by design
and every label on it was created as a `TEXT` node.

The fix keeps the good half of decision 34 and repairs the bad half: **artwork stays raster, text
stops being raster.** For each panel the source matplotlib SVG is split in Python into two
derivatives — a *text-free artwork* SVG that is re-rendered to a 300 dpi PNG, and a *text-only*
overlay SVG pre-scaled to the panel's exact placed pixel box. Figma imports the overlay, which its
own SVG reader turns into real `TEXT` nodes at exactly the right coordinates, and each panel becomes
a small `FRAME` holding one locked artwork rectangle plus a `labels` group of editable text. Node
cost is the 1,966 text elements that actually exist, not the 93,824 drawable elements a full vector
import would create.

The key design decision — **pre-scale the overlay in Python rather than rescale it in Figma** — is
what makes the registration exact: the x and y scale factors of the current layout differ by up to
0.7 % (see the table below), and `rescale()` is uniform, so doing the arithmetic offline is the only
way to land every tick on its tick mark.

---

## Background — what was measured, not assumed

### B1. The current state of the seven frames (read from Figma, 2026-09-20)

| Frame | node id | size | children |
|---|---|---|---|
| `Figure 4 - Biomarker expression and correlation (L, M)` | `1255:2` | 750 × 6229 | 7 `RECTANGLE` (IMAGE fill) + 7 `TEXT` panel letters |
| `Figure 5 - Prediction and election (N)` | `1255:3` | 750 × 2585 | 7 `RECTANGLE` (IMAGE fill) + 7 `TEXT` panel letters |
| `Figure 6 - Recipe` | `1255:4` | 750 × 1120 | 12 vector `FRAME` + 21 `TEXT` — **already correct, not in scope** |
| `Supplementary Figure 11 - Marker panel QC` | `1255:5` | 750 × 1261 | 3 `RECTANGLE` (IMAGE fill) + 3 `TEXT` |
| `Supplementary Figure 12 - Harshness by L, M, N` | `1255:6` | 750 × 356 | 1 `RECTANGLE` (IMAGE fill) + 1 `TEXT` |
| `Supplementary Figure 13 - Gene by method clustering` | `1255:7` | 750 × 1315 | 1 `RECTANGLE` (IMAGE fill) + 1 `TEXT` |
| `Supplementary Figure 14 - Remaining expression scatters` | `1255:8` | 750 × 3768 | 2 `RECTANGLE` (IMAGE fill) + 2 `TEXT` |

The seven frame-title `TEXT` nodes (`1257:2251`–`1257:2257`) and the 21 panel-letter `TEXT` nodes
are already editable. **Only the 21 panel rectangles are in scope.**

### B2. Four Figma probes, run on the live file and rolled back

Every scratch node created by these probes was removed in the same script.

1. **`createNodeFromSvg` does produce editable `TEXT` nodes** from a matplotlib `<text>` element,
   including one carrying `transform="translate(...) rotate(-90)"`. Import is therefore a legitimate
   text route, not only a vector route.
2. **It ignores `font-size` written inside a `style=` attribute** — a 7.5 px label imported at
   Figma's default 10 px. matplotlib writes all typography into `style=`, so a raw panel SVG imports
   with every label the wrong size.
3. **It honours `font-size` written as a presentation attribute** — the same label as
   `font-size="7.5"` imported at 7.5. The overlay builder must therefore convert `style=` to
   presentation attributes; this is the single most important detail of the whole plan.
4. **Only `Inter` is available.** `Arial`, `Helvetica`, `DejaVu Sans` and `Liberation Sans` all
   return `no` from `listAvailableFontsAsync()`. Panel text will be Inter, which is also the house
   style of §1.8 of the main plan. Inter's AUTO line box measured 1.20 × font size.

### B3. Panel inventory — placed geometry, scale factors and element counts

`draw` counts `<use> + <path> + <rect> + <polygon> + <circle> + <line>`; it is the number of nodes
a full vector import would create. `sx = placed_w / svg_w`, `sy = placed_h / svg_h`.

| Frame | ltr | panel | text | draw | svg (pt) | placed (px) | sx | sy | sy/sx |
|---|---|---|---|---:|---|---|---:|---:|---:|
| Fig 4 | A | `a2_p14_expression_scatter_01_raw` | 281 | 8 830 | 380.0 × 988.1 | 690 × 1794 | 1.8158 | 1.8156 | 0.9999 |
| Fig 4 | B | `a2_p14_expression_scatter_13_fsmvn` | 282 | 23 357 | 373.2 × 988.1 | 690 × 1826 | 1.8489 | 1.8479 | 0.9995 |
| Fig 4 | C | `a2_p1_rho_vs_margin` | 19 | 2 264 | 206.1 × 179.1 | 417 × 363 | 2.0231 | 2.0263 | 1.0016 |
| Fig 4 | D | `a2_p2_margin_ranking` | 66 | 135 | 373.3 × 243.0 | 690 × 451 | 1.8485 | 1.8563 | 1.0042 |
| Fig 4 | E | `a2_p3_agreement_specific` | 23 | 4 460 | 196.0 × 184.7 | 395 × 375 | 2.0156 | 2.0303 | 1.0073 |
| Fig 4 | F | `a2_p7_strategy_imputation_method` | 53 | 443 | 367.0 × 300.3 | 690 × 564 | 1.8800 | 1.8780 | 0.9989 |
| Fig 4 | G | `a2_p12_raw_to_harmonized` | 31 | 114 | 238.8 × 206.2 | 478 × 414 | 2.0017 | 2.0075 | 1.0029 |
| Fig 5 | A | `a2_p4_lobo_ranking` | 68 | 134 | 373.3 × 243.1 | 690 × 451 | 1.8485 | 1.8550 | 1.0035 |
| Fig 5 | B | `a2_p5_per_batch` | 33 | 2 104 | 387.7 × 195.1 | 690 × 349 | 1.7797 | 1.7884 | 1.0049 |
| Fig 5 | C | `a2_p6_singleclass_audit` | 23 | 2 207 | 200.3 × 179.1 | 403 × 363 | 2.0118 | 2.0263 | 1.0073 |
| Fig 5 | D | `a2_p8_generalizability_index` | 52 | 298 | 373.3 × 257.3 | 690 × 475 | 1.8482 | 1.8461 | 0.9988 |
| Fig 5 | E | `a2_p9_cross_election_circos` | 10 | 40 | 158.9 × 158.5 | 318 × 317 | 2.0008 | 1.9994 | 0.9993 |
| Fig 5 | F | `a2_p10_venn_supervenn` | 26 | 49 | 308.3 × 177.7 | 426 × 246 | 1.3818 | 1.3846 | 1.0021 |
| Fig 5 | G | `a2_p13_election_sankey` | 12 | 18 | 179.0 × 147.5 | 247 × 204 | 1.3798 | 1.3833 | 1.0026 |
| Supp 11 | A | `a2_p15_panel_coverage` | 31 | 623 | 259.4 × 293.8 | 384 × 436 | 1.4801 | 1.4840 | 1.0026 |
| Supp 11 | B | `a2_p16_qc_gate` | 185 | 190 | 194.1 × 240.6 | 288 × 357 | 1.4841 | 1.4840 | 0.9999 |
| Supp 11 | C | `a2_p17_rho_by_signature` | 72 | 392 | 346.4 × 338.6 | 690 × 673 | 1.9921 | 1.9876 | 0.9978 |
| Supp 12 | A | `a2_p11_harshness_lmn` | 89 | 226 | 375.9 × 141.8 | 690 × 262 | 1.8355 | 1.8483 | 1.0070 |
| Supp 13 | A | `a2_p18_gene_method_clustermap` | 49 | 7 610 | 397.1 × 702.2 | 690 × 1221 | 1.7375 | 1.7389 | 1.0008 |
| Supp 14 | A | `a2_p14_expression_scatter_12_scanorama` | 280 | 23 355 | 374.7 × 988.1 | 690 × 1819 | 1.8414 | 1.8409 | 0.9997 |
| Supp 14 | B | `a2_p14_expression_scatter_29_combat_ref` | 281 | 16 975 | 379.3 × 988.1 | 690 × 1797 | 1.8193 | 1.8186 | 0.9996 |
| | | **total** | **1 966** | **93 824** | | | | | |

### B4. Text styling present in the 21 SVGs

- **Two fills only:** `#262626` (1 678 elements) and `#ffffff` (139, the in-cell labels of the
  bubble and heat panels).
- **Eight sizes:** 4.5, 5, 5.5, 7.5, 9, 10, 12 px and a handful of others; after scaling these land
  between ~7 and ~22 Figma px.
- **Three anchors:** `start` (the matplotlib default when the attribute is absent), `middle`, `end`.
- **Rotation** appears as both `transform="rotate(-0 x y)"` (the no-op on every horizontal label)
  and `transform="translate(x y) rotate(-90)"` on axis titles and column labels.
- **1 450 `<tspan>` elements** — these are **mathtext**, not multi-line text. A single `ρ = 0.83`
  annotation is emitted as one `<text>` with no `x`/`y` of its own, positioned by an ancestor
  `<g transform="translate(...)">`, holding one `<tspan>` **per glyph** in `DejaVu Sans`, the first
  of which carries `font-style: oblique` for the ρ. Merging those tspans back into one string is a
  required step; a naïve per-tspan conversion would create 1 450 one-character text boxes.
- Consequence: the extractor must be a real XML walk with ancestor-transform composition. A regex
  over `<text ...>` would miss every mathtext annotation and every `translate`-positioned label.

### B5. Rendering tools present on this Mac

`Homebrew 6.0.20` with `/opt/homebrew/lib/libcairo.2.dylib`, `pdftoppm` (poppler), `qlmanage`,
`matplotlib` and `Pillow` in `~/venvs/collagen_3_11`. **`cairosvg` is not installed but will install
cleanly** against the Homebrew cairo. No `rsvg-convert`, no `inkscape`, no ImageMagick.
The existing panel PNGs on disk are 200 dpi (2.777 px/pt); the fills currently in Figma are 300 dpi
(4.167 px/pt), so the replacement artwork renders at `scale = 300/72`.

---

## Design decision and the alternatives rejected

**Chosen — artwork raster, text as a pre-scaled overlay SVG imported by Figma.**
Cost: 1 966 new `TEXT` nodes, 21 new image fills, 21 new panel frames. Registration is exact because
Figma itself places the text from coordinates computed offline at full precision.

| Alternative | Why not |
|---|---|
| **Import each panel SVG whole as vector** (the route decision 34 rejected) | 93 824 drawable nodes, 23 357 in a single panel. Figma would import them onto Page 1 for manual reparenting, the file would become unusable, and probe 2 shows every label would arrive at the wrong size anyway. Viable only for the seven lightest panels, which is not worth a second code path. |
| **Create the `TEXT` nodes from a JSON dump with arithmetic done in the `use_figma` script** | Needs a hand-derived baseline model (SVG `y` is a baseline, Figma `y` is a box top), an anchor model, and an Inter-vs-Arial advance-width model. Probe 1 shows Figma's own SVG reader already solves all three correctly. Do not reimplement it. |
| **`rescale()` the imported overlay inside Figma** | `rescale` is uniform; `sy/sx` reaches 1.0073 on three panels, which is a 2 px drift at the bottom of `a2_p11` and 2.7 px on `a2_p3`. Pre-scaling in Python applies `sx` and `sy` independently and drifts by nothing. |
| **Re-flow the layout so every box has an exact aspect ratio** | Would change the geometry of frames Daniil has already begun reviewing, for a 0.7 % gain the overlay already delivers. |
| **Regenerate the panels from the notebook with text suppressed** | Requires a full analysis re-run for an artwork-only change, and the text would still have to be recreated. |
| **Leave ticks baked and lift only titles and legends** | Daniil asked for "labels, ticks etc". Offered below as an option, not the default. |

---

## Files to create

### 1. `tools/split_panel_text_260920.py` — new, the offline half of the pipeline

One script, three outputs per panel, driven by a placement table it reads rather than guesses.

**1a. The placement table.** Read `figures/figma_layout_260920.md` rather than hardcoding: parse the
per-frame markdown tables into `{panel: (frame, letter, x, y, w, h)}`. If a row is missing for a
panel present in `PANELS`, raise — silent omission is how a panel would end up with no overlay.

**1b. `iter_text(svg_path)` — the XML walk.**

```python
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
        into a single string. Fields: text, x, y, size, anchor, rotation, fill,
        italic, source_line.
    """
```

Rules the walk must implement, each of them forced by something measured in B4:

- Maintain a transform stack. Support `translate(a[,b])`, `rotate(a[,cx,cy])`, `scale`, `matrix`.
  Compose as 2×3 affine matrices; `numpy` is already a dependency.
- A `<text>` with its own `x`/`y` uses those; one without inherits its position from the composed
  ancestor transform (the mathtext case).
- Merge child `<tspan>` text in document order into one string. Take position, size and fill from
  the **first** tspan. If any tspan carries `font-style: oblique`, set `italic=True` and record the
  item in the conversion report — Inter Italic will be applied if available, otherwise Regular and
  the item is listed for Daniil.
- Parse `style="key: value; ..."` into a dict; `text-anchor` defaults to `start`, `fill` to
  `#262626`, `font-size` is required and the walk raises if it is absent.
- Decompose the composed matrix into (translation, rotation, uniform scale). matplotlib emits no
  skew and no non-uniform scale in text transforms; assert that and raise if it ever appears.

**1c. `write_artwork_svg(src, dst)`** — parse, remove every `<text>` element (and any now-empty
`<g>` wrapper), serialise. Nothing else changes, so the artwork is byte-for-byte the same drawing
minus its type.

**1d. `write_overlay_svg(items, dst, sx, sy, w, h)`** — emit

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" version="1.1">
  <text x="..." y="..." font-size="..." font-family="Inter" text-anchor="..."
        fill="#262626" transform="rotate(-90 ... ...)">…</text>
</svg>
```

with **every typographic property as a presentation attribute** (probe 3), `x *= sx`, `y *= sy`,
`font-size *= sx`, rotation carried through unchanged, and the text content XML-escaped. No
`style=` attribute anywhere in the output. The viewBox equals the panel's placed pixel box, so the
import lands at 1:1 and needs no scaling in Figma at all.

**1e. `render_png(artwork_svg, dst, dpi=300)`** — `cairosvg.svg2png(..., scale=300/72)`. Assert the
output size equals `round(svg_pt * 300/72)` within one pixel. `--renderer` flag with a
`figma` fallback described in the caveats.

**1f. `main()`** — argparse: `--panels` (default all 21), `--out-dir`
(default `figures/panels_260917/editable_260920/`), `--dpi 300`, `--renderer cairosvg`,
`--report`. Writes `<panel>_artwork.svg`, `<panel>_artwork_300dpi.png`, `<panel>_text.svg` and a
machine-readable `overlay_manifest.json` carrying, per panel, the Figma frame id, the panel
rectangle id, the placed box, `sx`, `sy`, the text count and the sha256 of each output. The Figma
step reads this manifest and never recomputes geometry.

**1g. `--report`** prints a conversion audit: per panel, the number of `<text>` elements in, the
number of items out (these differ exactly by the mathtext merge), the number of italic items, the
size and anchor histograms, and any item whose scaled font size falls below 6 px, which is the
project's legibility floor.

### 2. `tools/figma_editable_text_260920.md` — new, the Figma half

A short runbook holding the four `use_figma` scripts of §"Figma procedure" verbatim, so the
operation is reproducible and reviewable. The 2026-09-20 assembly left no script on disk, which is
why nobody could tell from the repository how the frames were built; this plan does not repeat that.

### 3. `figures/panels_260917/editable_260920/` — new directory

63 generated files plus `overlay_manifest.json`. The originals in `figures/panels_260917/` are
never overwritten — same discipline as §4.2a of the main plan, where Article 2 panels were given
their own folder so an Article 1 panel could not be clobbered.

---

## Figma procedure

File `t8bFgusleBEwB9ht7rORCH`, **Page 2** (`1013:2`). Every script begins with
`await figma.setCurrentPageAsync(figma.root.children.find(p => p.name === 'Page 2'))`.
The three mechanical rules of `CLAUDE.md` still hold: never `get_metadata` on the page root, never
on a whole figure frame, and address nodes by id.

**Step F0 — snapshot.** Write `figures/figma_snapshots/page2_before_editable_260920.json` in the
same shape as the two existing snapshots (`id`, `name`, `type`, `x`, `y`, `w`, `h`, `kids`), plus a
per-frame child listing for the seven Article 2 frames. This is the rollback reference and the
input to the acceptance diff.

**Step F1 — upload the 21 artwork PNGs.** `upload_assets` with `count` ≤ 21 and `nodeIds` set to
the 21 existing panel rectangle ids, `scaleMode: "FILL"`. This replaces each image fill in place
with the text-free render and changes no geometry. Verify visually that the artwork is now blank
where the labels were.

**Step F2 — convert each panel rectangle into a panel frame.** Per panel, in batches of ≤ 6 panels
per call:

1. Create a `FRAME` at the rectangle's exact `x`, `y`, `width`, `height`, named
   `{letter} {panel}` — the rectangle's current name.
2. `clipsContent = true`, `fills = []`, and insert it into the parent frame at the rectangle's
   index so z-order is preserved.
3. Reparent the rectangle into the new frame at `(0, 0)`, rename it `artwork`, and set
   `locked = true` so a stray click selects the label above it rather than the image.
4. Return the created frame ids.

No auto-layout: these are absolutely-positioned artwork boxes on a poster canvas, which is the one
case Rule 12a of the figma-use skill exempts.

**Step F3 — import one overlay per panel.** Per panel:

1. `figma.createNodeFromSvg(<contents of {panel}_text.svg>)` — the SVG string is passed inline in
   the script, not uploaded, so the nodes land on Page 2 and never on Page 1. The four expression
   scatters carry ~280 text elements each; those get a call of their own.
2. The returned node is a `FRAME` of exactly the panel box. Rename it `labels`, set `fills = []`
   and `clipsContent = false`, and `appendChild` it into the panel frame at `(0, 0)`.
3. Walk its `TEXT` descendants and assert three things, raising on the first failure:
   `characters` is non-empty, `fontSize` matches the manifest to within 0.01 px, and
   `fontName.family === 'Inter'`. `loadFontAsync({family:'Inter', style:'Regular'})` — and
   `'Italic'` if the panel has italic items — before any mutation.
4. Return `{panelId, frameId, labelsId, nText}`.

**Step F4 — verify and finish.** `await frame.screenshot()` on each of the six frames and compare by
eye against `figures/panels_260917/<panel>.png`. Then run the acceptance script of the verification
section. Leave `placeholder` false everywhere.

**Batching.** 1 966 text nodes arrive as 21 import calls, one per panel, because
`createNodeFromSvg` is a single logical operation regardless of how many nodes it yields. Total
budget: 1 snapshot + 1 upload + 4 frame-conversion + 21 import + 6 screenshot ≈ 33 `use_figma`
calls.

---

## Files to change

### 4. `figures/figma_layout_260920.md`

Add a section **"Editable text pass, 2026-09-20"** recording that each panel is now a `FRAME`
containing a locked `artwork` rectangle and a `labels` group, that the artwork PNG is text-free, and
that the overlay is pre-scaled by `(sx, sy)` so the layout table's boxes are unchanged. Add the `sx`
and `sy` columns of table B3 to each per-frame table, since they are now load-bearing numbers rather
than derived ones.

### 5. `CLAUDE.md` (this directory), the "Figma — assembled 2026-09-20" section

Two edits.

**5a.** Replace

> Panels are 300 dpi PNG fills re-rendered from the panel PDFs; `Figure 6 - Recipe` is the exception
> and is fully vector, with every character a TEXT node.

with a statement of the new structure: each panel is a frame holding a locked text-free 300 dpi
artwork rectangle and a `labels` group of Figma `TEXT` nodes imported from a pre-scaled overlay SVG;
`Figure 6 - Recipe` is fully vector; every character in every Article 2 frame is a `TEXT` node.

**5b.** Add to the three mechanical facts a fourth: **matplotlib SVG imports at the wrong font size
unless the typography is rewritten from `style=` into presentation attributes** — the trap probe 2
found — and that only `Inter` is available in this file.

### 6. `f1000_article2_plan_260917.md` §11

Append decisions 37–39 in the existing voice:

- **37.** Decision 34 is superseded. Raster fills gave no editable text and broke §5.4. Panels are
  now text-free raster artwork plus an imported text overlay: 1 966 `TEXT` nodes instead of the
  93 824 vector nodes a full import would have cost, and §5.4 holds for the first time.
- **38.** The overlay is pre-scaled in Python, not rescaled in Figma, because `sy/sx` reaches 1.0073
  and `rescale()` is uniform.
- **39.** The pipeline is on disk as `tools/split_panel_text_260920.py` and
  `tools/figma_editable_text_260920.md`. The 2026-09-20 assembly left no script, so its steps could
  not be re-read or re-run; this pass is reproducible.

### 7. `README.md` (this directory)

The `figures/` row of the sub-directory table gains `panels_260917/editable_260920/` with a
one-line description.

---

## Files that do NOT need to change

| File | Why |
|---|---|
| `analysis/article2_generalizability.py`, `build_numbers_json.py` | No number changes. This is an artwork operation; the analysis set, the election and the nine `A2_T*` tables are untouched. |
| `figures/panels_260917/*.pdf/.svg/.png` (the originals) | Read-only inputs. Derivatives go to a new sub-directory so the published panels stay reproducible. |
| `manuscript/*.md`, `*.docx`, `figure_legends_260917.md` | No figure is renumbered, split or merged. Panel letters A–G are unchanged. |
| `tools/audit_numbers.py`, `check_style.py`, `check_overlap.py` | Gates over the manuscript text; nothing they read changes. Re-run them anyway (verification below) to prove it. |
| `figures/recipe_assets_260917/`, `Figure 6 - Recipe` (`1255:4`) | Already fully vector with 21 `TEXT` nodes. Out of scope. |
| The 13 Extended Figure frames on Page 2 | Protected by §5.4 of the main plan. Renaming remains the only edit ever permitted to them, and this pass makes none. |
| `manuscript_versions/*.docx` | Unrelated document line. |

---

## Side effects and caveats

1. **The 21 panel rectangles change type.** A `RECTANGLE` becomes a `FRAME` containing a
   `RECTANGLE`, so the node ids `1256:2`–`1256:22` survive as the inner `artwork` nodes but are no
   longer direct children of the figure frames. Any note Daniil has made that points at one of those
   ids still resolves; anything that assumed "panel = rectangle" does not. The acceptance diff must
   therefore compare on **outer box geometry**, not on node type.
2. **Text will not be pixel-identical to the current artwork.** Arial is unavailable in this Figma
   file (probe 4), so labels render in Inter. Advance widths differ by a few per cent: a long
   left-anchored method name may end 1–3 px further right than the old raster did, and a centred
   tick stays centred. This is a real visual change and is the price of editability. If Daniil
   prefers exact glyph fidelity, the only route is to keep the text baked, which is what he has
   asked to undo.
3. **Mathtext annotations lose per-glyph italics unless Inter Italic is present.** The ρ in
   `ρ = 0.83` is `font-style: oblique` on its own tspan. After merging, the whole string takes one
   style. The `--report` output lists every affected item — measured at 36 in
   `a2_p14_expression_scatter_01_raw` — so Daniil can italicise by hand if he wants.
4. **`cairosvg` is a new dependency** in `~/venvs/collagen_3_11`. It links against the Homebrew
   cairo already present. **Fallback if it will not install:** import the text-free artwork SVG into
   Figma with `createNodeFromSvg`, `exportAsync({format:'PNG', constraint:{type:'SCALE', value:
   4.167}})`, set the bytes as the fill with `figma.createImage`, delete the vector tree. This works
   for the 14 light panels and will choke on the four expression scatters and the clustermap, so it
   is a fallback, not a plan.
5. **Figure 4 is 6 229 px tall and gains 755 text nodes.** It is already flagged in §11 "Open for
   Daniil" as very tall. This pass does not change that; it makes the labels editable at that size.
6. **Do not re-run `upload_assets` without `nodeIds`.** Without targets it creates new frames on the
   current page, which is how the recipe assets landed on Page 1 in the first place.
7. **Rollback** is `page2_before_editable_260920.json` plus the original PNGs: delete the 21 `labels`
   groups, unwrap the 21 panel frames, and re-upload the original artwork PNGs to the same node ids.
   Nothing outside the seven Article 2 frames is touched, so rollback cannot reach the Extended
   Figures.
8. **Option Daniil may prefer:** a `--labels-only` flag that keeps tick labels baked into the artwork
   and lifts only titles, legends, annotations and category names. It cuts 1 966 text nodes to
   roughly 600, mostly by leaving the four expression-scatter tick grids alone. Default is **off** —
   he asked for ticks too.

---

## Verification commands

```bash
source ~/venvs/collagen_3_11/bin/activate
cd <repo>/article_2_extended_comparison

pip install cairosvg                                   # caveat 4

# 1. Offline pass over all 21 panels, with the conversion audit.
python tools/split_panel_text_260920.py --report

# 2. No text survives in any artwork SVG, and the overlays hold every string.
python - <<'PY'
import json, pathlib, re
d = pathlib.Path("figures/panels_260917/editable_260920")
man = json.loads((d / "overlay_manifest.json").read_text())
bad = []
for p, m in man["panels"].items():
    art = (d / f"{p}_artwork.svg").read_text()
    txt = (d / f"{p}_text.svg").read_text()
    if "<text" in art:
        bad.append(f"{p}: artwork still has text")
    if "style=" in txt:
        bad.append(f"{p}: overlay still uses style= (Figma would drop the font size)")
    n = txt.count("<text")
    if n != m["n_text_items"]:
        bad.append(f"{p}: overlay has {n} text nodes, manifest says {m['n_text_items']}")
print("\n".join(bad) or f"OK - {len(man['panels'])} panels, "
      f"{sum(m['n_text_items'] for m in man['panels'].values())} text items")
PY

# 3. Every artwork PNG is 300 dpi and matches its placed aspect ratio.
python - <<'PY'
import json, pathlib
from PIL import Image
d = pathlib.Path("figures/panels_260917/editable_260920")
man = json.loads((d / "overlay_manifest.json").read_text())
for p, m in man["panels"].items():
    w, h = Image.open(d / f"{p}_artwork_300dpi.png").size
    exp_w = round(m["svg_pt"][0] * 300 / 72)
    assert abs(w - exp_w) <= 1, (p, w, exp_w)
print("OK -", len(man["panels"]), "PNGs at 300 dpi")
PY

# 4. The manuscript gates are unaffected (they must still pass unchanged).
python tools/audit_numbers.py
python tools/check_style.py --journal f1000
python tools/check_overlap.py
```

**5. Figma acceptance**, run after step F4 as a read-only `use_figma` script:

```js
const p2 = figma.root.children.find(p => p.name === 'Page 2');
await figma.setCurrentPageAsync(p2);
const names = [/^Figure 4/, /^Figure 5/, /^Supplementary Figure 1[1-4]/];
const frames = p2.children.filter(n => names.some(r => r.test(n.name)));
const out = frames.map(f => {
  const panels = f.children.filter(c => c.type === 'FRAME');
  return {
    frame: f.name, x: f.x, y: f.y, w: f.width, h: f.height,
    nPanels: panels.length,
    panels: panels.map(p => ({
      name: p.name, x: p.x, y: p.y, w: p.width, h: p.height,
      artworkLocked: p.children.some(c => c.name === 'artwork' && c.locked),
      nText: p.query('TEXT').length,
      nonInter: p.query('TEXT').toArray()
        .filter(t => t.fontName !== figma.mixed && t.fontName.family !== 'Inter').length,
      empty: p.query('TEXT').toArray().filter(t => !t.characters.trim()).length
    }))
  };
});
return out;
```

Acceptance is met when, for all six frames: frame `x`/`y`/`w`/`h` equal the values in table B1;
every panel box equals its row in `figma_layout_260920.md`; `artworkLocked` is true everywhere;
`nText` per panel equals the manifest; `nonInter` and `empty` are 0 everywhere; and the six
screenshots show no label sitting off its axis and no doubled text.

---

## TODO

### Offline pipeline
- [x] `pip install cairosvg` into `~/venvs/collagen_3_11`; confirm it links against
      `/opt/homebrew/lib/libcairo.2.dylib` (pip's resolver fails on IPv6 here; the three
      pure-python wheels were fetched with `curl -4` and installed `--no-index`. cairo 1.18.4 linked)
- [x] `tools/split_panel_text_260920.py` — parse `figures/figma_layout_260920.md` into the placement
      table; raise on any panel missing a row
- [x] `tools/split_panel_text_260920.py` — `iter_text()`: transform stack, ancestor-positioned
      `<text>`, mathtext `<tspan>` merge, `style=` parsing, anchor/fill defaults, raise on skew
- [x] `tools/split_panel_text_260920.py` — `write_artwork_svg()`: strip `<text>`, drop emptied `<g>`
- [x] `tools/split_panel_text_260920.py` — `write_overlay_svg()`: presentation attributes only,
      `font-family="Inter"`, `x *= sx`, `y *= sy`, `font-size *= sx`, rotation preserved, XML-escaped
- [x] `tools/split_panel_text_260920.py` — `render_png()` at `scale = 300/72`, size assertion
- [x] `tools/split_panel_text_260920.py` — `overlay_manifest.json` with frame id, rect id, box,
      `sx`, `sy`, text count, sha256 per output
- [x] `tools/split_panel_text_260920.py` — `--report`, `--panels`, `--out-dir`, `--dpi`,
      `--renderer`, `--labels-only`
- [x] Run over all 21 panels; read `--report` and check nothing falls under the 6 px legibility floor
- [x] Run verification commands 1–3

### Figma
- [x] F0 — write `figures/figma_snapshots/page2_before_editable_260920.json`
- [x] F1 — `upload_assets` the 21 artwork PNGs onto the 21 existing rectangle ids; confirm the
      artwork is blank where the labels were (`nodeIds` stored the images but attached none — the
      fills were set explicitly from the returned `imageHash` in a second call)
- [x] F2 — convert the 21 rectangles into panel frames with a locked `artwork` child, preserving
      index and z-order (≤ 6 panels per call)
- [x] F3 — import the 21 overlays, reparent as `labels`, assert font family, size and non-empty
      characters. Uploaded as `image/svg+xml` rather than inlined via `createNodeFromSvg`: the four
      expression-scatter overlays are ~34 KB each against a 50,000-char `code` limit
- [x] F4 — `screenshot()` all six frames; compare against `figures/panels_260917/<panel>.png`
- [x] Run Figma acceptance script 5; write `page2_after_editable_260920.json` and diff the two
      snapshots — only the seven Article 2 frames may differ
- [x] Confirm the 13 Extended Figure frames and `Figure 6 - Recipe` are byte-identical in the diff

### Documentation
- [x] `tools/figma_editable_text_260920.md` — the four `use_figma` scripts, verbatim and runnable
- [x] `figures/figma_layout_260920.md` — "Editable text pass" section; `sx`/`sy` columns
- [x] `CLAUDE.md` — rewrite the raster-fill sentence (5a); add the presentation-attribute and
      Inter-only facts (5b)
- [x] `f1000_article2_plan_260917.md` §11 — decisions 37, 38, 39 and 40 (reproducibility)
- [x] `README.md` — `editable_260920/` row
- [x] Re-run `audit_numbers.py` (needs `--evidence workflow_runs/260919_run1/01_numbers.json`),
      `check_style.py --journal f1000`, `check_overlap.py` and the antithesis grep; all exit 0
