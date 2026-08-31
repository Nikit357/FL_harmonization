# Figma review — Graphical Abstract (2026-07-31)

> **Superseded by `graphical_abstract_redesign_plan_260731.md`.** That plan supersedes the
> recommendations here: rather than repairing the v1 frame, three redesigned candidate
> variants are being built. This document remains the record of what v1 contained and why
> it needed replacing. Read the plan for current actions; read this for the audit trail.

Review of the graphical abstract in the shared Figma file, carried out via the Figma
MCP plugin (read-only inspection: `get_metadata`, `get_screenshot`, and one read-only
`use_figma` ancestry probe). No changes were written to the file.

## Source

| Item | Value |
|---|---|
| File | `FL harmonization article` |
| File key | `t8bFgusleBEwB9ht7rORCH` |
| URL | https://www.figma.com/design/t8bFgusleBEwB9ht7rORCH/FL-harmonization-article |
| Editor type | Design (`/design/` path) |
| Reviewed node | `757:65863` — frame "Graphical Abstract", 755 × 290 px at (−4113, 95) |
| Heading text node | `753:53579` — "Graphical abstract", 181 × 24 px at (−4109, 21) |
| Figma account | Daniil Nikitin, plan `team::1303927689220376868` (starter tier, Full seat) |

Note: the node originally opened from the URL (`753:53579`) is only the text label
above the artwork, not the artwork itself. The composition lives in the sibling
frame `757:65863` directly below it.

## File structure

- **One page only:** `0:1` "Page 1", holding **729 direct children**. The entire
  article figure inventory sits on a single flat canvas.
- **No design system:** no components, no component sets, no variable collections,
  no auto-layout. Everything is positioned by absolute `x`/`y`.
- **Provenance:** most children are imported matplotlib SVGs — recognisable from the
  generated group names (`patch_*`, `text_*`, `line2d_*`, `axes_*`, `p<hash>` clip
  paths). This means large parts of the file are *derived* artefacts whose true
  source is the plotting notebooks.

Practical consequence: any future edits should follow the existing absolute-position
convention rather than retrofitting auto-layout onto neighbouring work.

## Current composition of `757:65863`

Three panels, left to right:

1. **INPUT** (group `754:54383` "Group 4951") — "INPUT: Germinal centre lymphoma
   dataset 7174 samples", with four labelled data-type icons: RNA-seq, Microarrays,
   Fresh Frozen, FFPE.
2. **ComboBatch pipeline** (group `754:65314` "Group 4973") — seven stacked steps:
   Batch removal → Imputation → Log-transform → Harmonization → Post-removal →
   Quality metrics → Clustermap, each with a small illustrative thumbnail.
3. **Best harmonization** (group `754:65848` "Group 4974" plus surrounding axes
   frames) — a t-SNE grid: "tSNE Before" on top (two facets), "tSNE After" below in
   three columns (Full dataset MNN · RNA-seq SVA · FFPE SVA) × two rows.

Overall assessment: the figure is already close to submission quality — clear
left-to-right narrative, legible labels, consistent panel framing. The findings
below are refinements, not a rebuild.

## Findings

### 1. Before/after panels order their facets inconsistently — highest priority

- **"tSNE Before"** runs **Biology → Batch** left-to-right
  (text nodes `754:65426` "Biology" at x≈509, `754:65428` "Batch" at x≈602).
- **"tSNE After"** runs **Batch (top) → Biology (bottom)**
  (text nodes `757:65859` "Batch" at y≈210, `757:65861` "Biology" at y≈290).

The reader must re-map which facet is which halfway through the panel — precisely
where the figure is asking them to compare before against after. This is the one
finding that affects comprehension rather than polish.

**Fix:** swap the "After" rows so Biology sits above Batch, matching the reading
order established by the "Before" panel. This is a layout change in Figma *if* the
two rows are separate imported images; if both rows come from one matplotlib
figure, change the subplot order in the generating notebook instead (see
"Where edits belong" below).

### 2. Duplicated node subtrees inflate the export payload

Several matplotlib imports are stacked exactly on top of themselves at identical
coordinates — invisible on screen, but doubling the vector content that has to be
written on PDF/SVG export.

Confirmed duplicate pairs inside `757:65863`:

| Original | Duplicate | Name | Position |
|---|---|---|---|
| `754:63951` | `754:65035` | "Clip path group" | 299.9999, 259.0400 |
| `754:63952` | `754:65036` | `pacd6c8aa9c` | 299.9999, 259.0400 |
| `754:63956` | `754:65040` | `patch_74` | 299.9999, 259.0400 |
| `754:63961`–`754:64011` | `754:65045`–`754:65095` | `line2d_9`–`line2d_19` | identical |
| `754:57458`–`754:57640` | `754:58542`–`754:58724` | `pe8acbcd925` / `p65105baf57` / `Group` | identical |

The same pattern appears at page level, outside the reviewed frame:

| Original | Duplicate | Name | Position |
|---|---|---|---|
| `753:40468` | `754:55765` | `text_10` | −4586, 388 |
| `753:40466` | `754:55763` | `text_9` | −4591, 366 |
| `753:40459` | `754:55756` | `text_5` | −4592, 262 |
| `753:40476` | `754:55773` | `text_15` | −4592, 557 |
| `753:40461` | `754:55758` | `text_6` | −4599, 278 |
| `753:40478` | `754:55775` | `text_16` | −4599, 570 |
| `753:40470` | `754:55767` | `text_11` | −4604, 429 |

**Fix:** delete one member of each pair. Verify visually before and after — the
render should be pixel-identical. Deletion is safe only after confirming both nodes
are genuinely coincident and neither is referenced elsewhere.

### 3. Sample-count discrepancy against project documentation — RESOLVED

**Resolved 2026-07-31 by Daniil: 7,174 is correct. 7,238 is an incorrect unfiltered
sample count and must not be used anywhere.** The figure's number is therefore right as
printed. The root `CLAUDE.md` Dataset section still carries the wrong 7,238 and remains
the source from which this error resurfaces; correcting it is tracked as an optional item
in the redesign plan. Note that `comb_ann_unified.csv` has 7,238 rows, which is the likely
origin of the confusion — it is a row count, not the sample count.

Original finding, retained for the record:

The figure states **7174 samples**. Project documentation disagrees with itself:

- `CLAUDE.md` → *Current Status → Completed*: "88 cohorts, ~7,174 samples" — agrees.
- `CLAUDE.md` → *Dataset* section: "~7,238 samples / 88 cohorts / 4 platforms" — disagrees.

One of these is stale. The graphical abstract is among the most-read elements of a
paper, so the number needs to be settled and made consistent across figure,
abstract, Methods, and `CLAUDE.md` before submission. Note also that 7,174/7,238 is
the *pre-exclusion* count; the analysed matrix is 5,444 samples × 3,520 genes after
bad-batch exclusion. If the figure's number is meant to describe the input to
ComboBatch, the pre-exclusion count is correct — but the caption should say which.

### 4. Spelling convention — layer name and rendered text disagree

Corrected 2026-07-31 after inspecting the panel at higher resolution:

- The **rendered text** reads "Germinal **center**" (American spelling).
- The **layer is named** "INPUT: Germinal **centre** lymphoma dataset 7174 samples"
  (British spelling), node `753:53649`.

Only the rendered text reaches the reader, so the figure currently uses American
spelling. NAR is published by Oxford University Press, which prefers British forms,
but either variant is acceptable provided the manuscript is internally consistent.

**Action:** decide one variant, and check it against the manuscript body
(`FL_harmonization_article_NAR_260728.docx`). The layer name is cosmetic and can be
left alone, but renaming it to match avoids this same confusion next time.

## Where edits belong

The t-SNE grids, clustermap, and pipeline thumbnails are matplotlib output imported
as SVG. Changes to *how data is presented* (panel order, palettes, axis labels,
point sizes) should be made in the generating notebooks and re-exported, so the
figure stays reproducible from the metrics tables. Figma is the right place only for
composition, schematic elements, and text labels that do not originate in a plot.

This matters directly for finding 1: if the "After" rows are two separately imported
images, reordering in Figma is fine; if they are one matplotlib figure, reorder the
subplots in the notebook.

## Suggested order of work

1. Settle the sample count (finding 3) — blocks nothing else but affects text too.
2. Fix the before/after facet ordering (finding 1) — the only comprehension issue.
3. Remove duplicated subtrees (finding 2) — mechanical, do last, verify by screenshot.
4. Settle the spelling variant and check it against the manuscript (finding 4).

## Changes applied to the Figma file

### 2026-07-31 — snowflake icon added for Fresh Frozen

| Item | Value |
|---|---|
| New node | `903:2` — "Snowflake (Fresh Frozen)" |
| Type | `VECTOR` (true vector, exports cleanly to PDF/SVG) |
| Parent | `757:65863` "Graphical Abstract" (frame, per request) |
| Position | x = 45, y = 173 (frame-relative) |
| Size | 12.6 × 11.84 px |
| Stroke | `#1F77B4` (matplotlib tab10 blue), weight 1, round caps and joins |
| Fill | none — transparent background |
| Geometry | six-fold symmetric: 6 spokes, each with two outward branch pairs at 45°, 30 path segments |

Placement rationale: the Fresh Frozen row is tight — the petri-dish/vial icons occupy
x 15–57, the "Fresh Frozen" label starts at x 63, and the panel border ends at x 157.
The only free space adjacent to the row is the band above the icons (y 169–184), so
the snowflake sits at the icon cluster's top-right, directly above the vial cap. It
reads as "frozen vial" without colliding with the label. Its blue happens to match
the existing vial-cap colour closely.

Note: the node is a child of the frame, not of the INPUT group `754:54383`. It will
therefore not move if that group is repositioned. Re-parenting it into the group is a
one-line change if panel-local grouping is preferred.

## Reproducing this review

```
# Read-only inspection via the Figma MCP plugin
get_metadata   fileKey=t8bFgusleBEwB9ht7rORCH                  # lists pages
get_metadata   fileKey=t8bFgusleBEwB9ht7rORCH nodeId=757:65863 # frame subtree XML
get_screenshot fileKey=t8bFgusleBEwB9ht7rORCH nodeId=757:65863 maxDimension=1512
```

Screenshot URLs returned by `get_screenshot` are short-lived and were not archived;
re-run the call above to regenerate. Figma MCP authentication from the JupyterHub
pod requires the paste-back OAuth flow (the `localhost` callback cannot reach the
pod) — the callback URL from the browser address bar is passed to
`complete_authentication`.
