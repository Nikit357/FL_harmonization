# Implementation plan — Graphical Abstract redesign (2026-07-31)

## Overview

The graphical abstract in the Figma file `FL harmonization article`
(frame `757:65863`) is a three-panel montage: dataset inventory → ComboBatch pipeline
→ a 2×3 grid of before/after t-SNE thumbnails. It is competently assembled but it
**fails four hard NAR requirements** and, as a piece of communication, it says
"here is our pipeline" — the single most common thing a graphical abstract can say.

This plan does two things. First, it fixes the compliance failures, which are not
cosmetic: **every one of the 24 text items is less than half the minimum legal font
size**, the aspect ratio is wrong, the artwork reuses a main figure, and twelve
embedded raster images have unverified provenance. Second, it specifies **three
complete design variants** that trade the pipeline-diagram cliché for the paper's
actual, unusual punchline — *there is no universal harmonizer*.

**All three variants will be built in Figma, side by side, so that Daniil selects from
finished artwork rather than from descriptions.** A recommendation is still recorded
(Variant A), together with the specific risks of B and C, but the decision is deferred
until all three exist on the canvas.

The constraint that shapes every variant: the 12–16 pt font rule, applied to a
127 mm-wide canvas, allows roughly **one ninth** of the text currently present.
Compliance is not achievable by nudging sizes — each variant is built around **six to
eight short labels**.

**Nothing in this plan has been implemented.** The only change made to the Figma file
so far is the snowflake icon `903:2` added earlier today (logged in
`figma_review_260731.md`).

---

## Background / reference data

### NAR requirements for the Graphical Abstract

From `NAR_author_guidelines.md` §6.9, plus the figure-wide rules in §6.2–6.7.

| # | Requirement | Source | Current state (v1) | Verdict |
|---|---|---|---|---|
| 1 | Aspect ratio **5:2 landscape**, min **127 × 50 mm** | §6.9 | 755 × 290 px → **2.6034:1** | ✗ **FAIL** |
| 2 | Must be **original** — not a copy of any main or supplementary figure | §6.9 | Middle panel is the Fig 1C pipeline scheme (`pipeline_scheme.svg`) | ✗ **FAIL** |
| 3 | Font **sans-serif (Arial), 12–16 pt** | §6.9 | Inter, 10–15 px → **4.77–7.15 pt** | ✗ **FAIL** |
| 4 | Text used **sparingly** (mainly labels) | §6.9 | 24 separate text items | ✗ **FAIL** |
| 5 | Reads top-to-bottom or left-to-right; **one main point** | §6.9 | Reads left-to-right ✓, but presents pipeline + 8 embeddings | ~ Partial |
| 6 | Colour used; no trademarks or logos | §6.9 | Colour ✓, no logos ✓ | ✓ Pass |
| 7 | **One** sans-serif font family across all figures | §6.6 | Figma = Inter; matplotlib figures = DejaVu Sans | ✗ Inconsistent |
| 8 | Colour-blind-safe; **do not rely on colour alone** | §6.7 | t-SNE facets distinguished by colour only | ✗ **FAIL** |
| 9 | **CMYK**, not RGB, for print fidelity | §6.5 | RGB | ~ Revision-stage |
| 10 | ≥300 dpi colour / **600 dpi combination** at final size | §6.3 | 12 embedded rasters, native resolution unverified | ~ Unverified |
| 11 | Third-party images need reproduction permission | §6.10 | 12 rasters incl. `image 998337380`, `images 2` | ⚠ **RISK** |
| 12 | **Alt text** required, in manuscript under the legend | §6.7 | Not written | ✗ Missing (Daniil's action — see Handover) |

### The font-size arithmetic — the constraint that drives everything

Measured directly from the file (`use_figma` audit, 2026-07-31):

```
frame width            = 755 px
final printed width    = 127 mm = 5 in = 360 pt
scale                  = 360 / 755 = 0.4768 pt per px
```

| Requirement | Font size in a 755 px canvas |
|---|---|
| 12 pt minimum | **25.2 px** |
| 16 pt maximum | **33.6 px** |
| **Actual, currently** | **10–15 px** |

So the largest type in the figure prints at **7.15 pt** where 12 pt is the floor, and
the smallest (`754:58166`, the word "After") prints at **4.77 pt**. Every text node
fails. Correcting this means type must be **2.2× to 3.4× larger**, which cuts the
usable text budget by roughly an order of magnitude — hence a redesign.

Full audit of all 24 text nodes:

| Node | Text | px | printed pt |
|---|---|---|---|
| `754:54388` | ComboBatch pipeline *(italic)* | 15 | 7.15 |
| `754:65318` | Best harmonization *(italic)* | 15 | 7.15 |
| `753:53649` | INPUT: / Germinal center lymphoma dataset / 7174 samples | 15 | 7.15 |
| `753:54316` · `753:54318` · `753:54320` · `753:54322` | RNA-seq · Microarrays · Fresh Frozen · FFPE | 15 | 7.15 |
| `754:54391` … `754:60939` (7 nodes) | Batch removal … Clustermap | 15 | 7.15 |
| `754:65424` · `757:65851` | tSNE Before · tSNE After | 15 | 7.15 |
| `754:65426` · `754:65428` · `757:65859` · `757:65861` | Biology · Batch (×2 pairs) | 13 | 6.20 |
| `757:65853` · `757:65855` · `757:65857` | Full dataset, MNN · RNA-seq, SVA · FFPE, SVA | 13 | 6.20 |
| `754:58166` | After | 10 | **4.77** |

### Font availability — a genuine constraint discovered while planning

NAR §6.6 asks for Arial or Helvetica. **Neither is installed**, in either environment:

| Environment | Arial | Helvetica | Available Arial-metric substitute |
|---|---|---|---|
| Figma (1,938 families installed) | ✗ | ✗ | **Arimo** (Regular / Bold / Italic / Bold Italic) |
| matplotlib on the pod (22 families) | ✗ | ✗ | **Liberation Sans** |

Arimo and Liberation Sans are the same metric-compatible Arial substitute lineage —
identical advance widths and near-identical glyphs. Using **Arimo in Figma** and
**Liberation Sans in matplotlib** therefore gives one visually consistent, Arial-metric
typographic system across both halves of the figure, satisfying §6.6's *"one sans-serif
font for all figures, do not mix"* in substance.

Caveat to accept knowingly: the embedded font name in the exported PDF will read
"Arimo", not "Arial". This is standard and normally passes production. If OUP objects
at proof stage, the fallback is to outline the text on export — but §6.6 asks for
embedded fonts, so outline only if asked.

### The twelve embedded raster images

| Node | Name | Size (px) | Role |
|---|---|---|---|
| `754:65359` · `754:65414` | `image18d896c7da` · `imageb5a79c2ac6` | 80 × 71 | "Before" t-SNE ×2 |
| `754:65601` · `754:65688` · `754:65469` · `754:65526` · `754:65757` · `754:65838` | `image09497c4aae` etc. | 85.9 × 71.4 | "After" t-SNE ×6 |
| `753:54311` | `image 998337380` | 47 × 26 | RNA-seq icon |
| `753:54312` | `images 2` | 47 × 24 | Microarray icon |
| `754:63955` · `754:65039` | `image998337370c` (**same hash — the duplicate pair**) | 82.4 × 25.2 | Clustermap thumbnail |

Two distinct problems:

1. **Provenance.** Names of the form `image 998337380`, `images 2`, `image 998337383`
   are characteristic of downloaded stock artwork, not of exported plots. Under §6.10
   any third-party image needs documented reproduction permission before submission.
2. **Resolution.** All eight t-SNE panels are raster at ~86 px wide, which at final
   size is 41 pt ≈ 14.4 mm. §6.3 requires 600 dpi for combination line+halftone art;
   14.4 mm at 600 dpi needs ~340 px of real image data. Unless the embedded originals
   are much larger than their display size, these are **under-resolved**.

**Both problems disappear for the new variants**, because none of the three reuses any
v1 raster: every embedding is regenerated from source, and every icon is drawn as an
original `VectorNode`. The §6.10 question therefore only matters if v1 itself is ever
submitted — it does not block this work.

### Dataset and benchmark numbers

From `CLAUDE.md`. Counts marked ⚠ must be re-verified against the data at
implementation time (see caveats).

| Quantity | Value |
|---|---|
| **Samples (pre-exclusion, unfiltered)** | **7,174 — definitive** |
| Samples (post bad-batch exclusion) | 5,444 × 3,520 genes |
| Cohorts · platforms | 88 · 4 |
| Affymetrix · Illumina NGS · Illumina microarray · Agilent | 3,821 · 2,386 · 940 · 64 |
| Harmonization attempts benchmarked | ⚠ 2,234 valid (of 2,407 runs) |
| Scoring metrics | ⚠ 87 (of ~230 computed) |
| Methods · strategies · imputations · post-removal | 31 · 14 · 3 · 2 |
| Methods preserving FL/DLBCL/normal GC B-cell biology | **only MNN, FSQN R, SVA** |

The figure that appears in the graphical abstract is **7,174**. The value 7,238 that
appears in the root `CLAUDE.md` Dataset section is **incorrect** and must not be used.

Approved decision tree (2026-06-04), the source of the "verdicts":

| Data subset | Recommended method |
|---|---|
| Fresh frozen only | MNN or FSQN R (no post-removal) |
| FFPE only | **SVA** + softimpute/KNN |
| RNA-seq only | **SVA** + softimpute/KNN |
| RNA-seq + Illumina microarrays | FSQN R, or AMDBNorm/FSMVN + post-removal |
| RNA-seq + various microarrays | **MNN** + post-removal |

---

## The design problem, stated plainly

A graphical abstract has one job: make a browsing reader stop. The current figure
shows a labelled pipeline, which is what most methods papers show, so it reads as
generic even though the work behind it is not.

The paper's genuinely distinctive finding is a **negative** one: across 2,234
harmonization attempts scored on 87 metrics, **no method wins everywhere** — only
three of 31 preserve the FL/DLBCL/normal biology at all, and which of them to use
depends on the biomaterial and platform mix. Negative, "it depends" results are rare
in graphical abstracts. Leading with it is both more honest and more memorable than
another pipeline diagram.

The canvas budget, at 12–16 pt: **six to eight** short text items, one dominant visual
idea, three zones at most.

---

## Shared specification (applies to all three variants)

### Canvas and the px↔pt convention

Build each variant in Figma at **720 × 288 px**, under the fixed convention
**2 px = 1 pt**:

```
720 px / 2 = 360 pt = 127.0 mm   ← exactly the §6.9 minimum width
288 px / 2 = 144 pt =  50.8 mm   ← 720/288 = 2.500 exactly ✓ 5:2
```

This makes the font rule trivial to obey and to check: **no text below 24 px, none
above 32 px, ever.** Designing at the *minimum* permitted size is deliberate — it is
the strict reading of §6.9 and guarantees legibility at whatever size NAR displays it.

| Role | Figma px | Printed pt |
|---|---|---|
| Headline | 32 | 16 (max) |
| Method names, primary numbers | 28 | 14 |
| Secondary labels | 24 | 12 (min) |
| **Anything smaller** | — | **not permitted** |

Strokes: 2 px = 1 pt for primary rules and leader lines; 1 px = 0.5 pt absolute
minimum. Consistent weights across variants, per §6.6.

### All text lives in Figma, never in the assets

Generated SVG/PNG assets contain **artwork only — no text**. Every label is a Figma
text node in Arimo. Two reasons: the acceptance-gate audit (below) can then see and
verify every character in the figure, and font control stays in one place. This is a
change from a naive approach of baking axis labels into matplotlib output.

### Frame placement

The three variants sit as three separate frames stacked vertically with 60 px gaps, in
clear canvas space, named:

```
Graphical Abstract v2-A  (mosaic → verdicts)
Graphical Abstract v2-B  (continuous strip)
Graphical Abstract v2-C  (decision fan)
```

`figma.currentPage` has 729 children; scan for free space and place the block to the
right of the rightmost existing node, per figma-use Rule 13. Each frame gets an
explicit **white** fill — v1's `fills` is `[]` (transparent), which can render black in
some PDF/TIFF pipelines.

Auto-layout is **not** used: the file's convention is absolute positioning throughout,
and the zones are independently positioned artwork, not a flow.

---

## Variant A — "2,234 attempts → four verdicts" ★ recommended

```
┌──────────────────────────────────────────────────────────────────────┐
│  NO UNIVERSAL HARMONIZER                                    32px/16pt│
├───────────────┬──────────────────────┬───────────────────────────────┤
│ 7,174 samples │  ▓▒░▓▓▒░▒▓░▒▓▒░▓▒░   │  ▪ t-SNE   Fresh frozen → MNN │
│  28px/14pt    │  ░▓▒▓░▒▒▓░▓▒░▓▓▒░▓   │  ▪ t-SNE   FFPE        → SVA  │
│ ┌───────────┐ │  ▒░▓▒▓░▓▒░▒▓▒░▓░▒▓   │  ▪ t-SNE   RNA-seq     → SVA  │
│ │ ▇▇▇▇▇▇▇▇▇ │ │  ▓▒░▒▓▓░▒▓░▓▒▒░▓▒░   │  ▪ t-SNE   Mixed       → MNN  │
│ │ ▇▇▇▇▇▇    │ │  ░▒▓░▓▒░▓▒▓░▒▓░▒▓▒   │            28px/14pt          │
│ │ ▇▇        │ │  ▒▓░▓▒░▒▓░▓▒░▓▒▓░▓   │                               │
│ │ ▏         │ │                      │                               │
│ └───────────┘ │ 2,234 harmonizations │                               │
│ 88 cohorts    │   × 87 metrics       │                               │
│  · 4 platforms│      24px/12pt       │                               │
└───────────────┴──────────────────────┴───────────────────────────────┘
```

The signature element is the **middle mosaic: one small tile per harmonization
attempt, all 2,234 of them, coloured by composite score.** The benchmark's entire
search space becomes a visual texture — you can see at a glance that most of it is
mediocre and only a few tiles are good. Four leader lines pull the winners out to the
right, each with a real t-SNE thumbnail and its verdict.

**Why it is distinctive:** graphical abstracts almost never show the *whole* search
space. Showing 2,234 real results as texture, then extracting four answers, is a shape
not seen in this literature, and it is only available to a paper that actually ran that
many attempts. It converts the paper's main cost into its main visual asset.

| Property | Value |
|---|---|
| One main point | The benchmark yields *subset-specific* winners, not a champion |
| Reading order | left → right (input → evidence → verdict) ✓ §6.9 |
| Text items | **8** |
| Originality | The mosaic exists in no current figure ✓ §6.9 |
| Colour-blind safety | Verdicts carry text labels; mosaic is one sequential ramp, message survives greyscale ✓ §6.7 |
| Risk | Tile ordering must be defensible (caveat 1); platform stack is unlabelled (caveat 3) |

### Zone layout (frame-relative px)

| Zone | x | width | Contents |
|---|---|---|---|
| Headline | 24 | 672 | y 20–52, 32 px Arimo Bold |
| 1 — Input | 24 | 176 | Platform stack asset + 3 labels |
| 2 — Evidence | 224 | 248 | Mosaic asset + 1 label |
| 3 — Verdicts | 496 | 200 | 4 rows: thumbnail + verdict text |
| Gutters | — | 24 | Between zones |

Mosaic grid: 47 columns × 48 rows = 2,256 cells for 2,234 attempts (22 trailing cells
left empty). Tile 4.16 px → mosaic 196 × 200 px, leaving 24 px for its label.

Verdict rows: 4 rows × 52 px pitch; 44 × 44 px t-SNE thumbnail + 8 px gap + text.
At final size each thumbnail is 22 pt ≈ 7.8 mm, so a 600 dpi export needs ≥185 px of
real pixels — generate at 900 px and downsample.

### Text inventory — exactly 8 items

| # | Text | px / pt |
|---|---|---|
| 1 | NO UNIVERSAL HARMONIZER | 32 / 16 |
| 2 | 7,174 samples | 28 / 14 |
| 3 | 88 cohorts · 4 platforms | 24 / 12 |
| 4 | 2,234 harmonizations × 87 metrics | 24 / 12 |
| 5–8 | Fresh frozen → MNN · FFPE → SVA · RNA-seq → SVA · Mixed platforms → MNN | 28 / 14 |

---

## Variant B — "The continuous strip"

```
┌──────────────────────────────────────────────────────────────────────┐
│  BATCH OUT, BIOLOGY IN                    colour: batch → biology    │
├──────────┬──────────┬──────────┬──────────┬──────────────────────────┤
│ ∴∵∴ ∵∴   │  ∵∴∵∴    │   ∴∵∴    │  ●●● ○○  │  ●●●●   ○○○○             │
│ ∵ ∴∵ ∴∵  │ ∴ ∵∴ ∵   │ ∵∴ ∵∴∵   │ ●● ○○○   │ ●●●●●  ○○○○○             │
│  ∴∵∴∵∴   │  ∵∴∵ ∴   │  ∴∵∴∵    │  ●○○ ●   │  ●●●    ○○○○             │
│          │          │          │          │      (one 720 px strip)  │
├──────────┼──────────┼──────────┼──────────┼──────────────────────────┤
│   Raw    │  Batch   │ Imputed  │Harmonized│      Post-removal        │
│          │ removed  │          │  (MNN)   │        24px/12pt         │
└──────────┴──────────┴──────────┴──────────┴──────────────────────────┘
```

One full-bleed band, 720 px wide, made of **five real embeddings at five real pipeline
stages**, placed edge to edge with no internal borders so the eye reads a single
continuous transformation from batch-dominated noise to biology-resolved clusters.
Point colour shifts across the strip from batch-coded to diagnosis-coded.

**Deliberate design decision:** the strip uses five *genuine* embeddings, not an
interpolation between two. An interpolated morph would be a visual fiction that a
referee could fairly call misleading; five real pipeline stages are honest and happen
to progress smoothly anyway.

| Property | Value |
|---|---|
| One main point | The pipeline converts batch structure into biological structure |
| Reading order | left → right ✓ §6.9 |
| Text items | **7** |
| Originality | New renders at new stages; must be checked against Supp 7s / Supp 9 (caveat 6) |
| Colour-blind safety | ⚠ **Weakest of the three** — the whole message is carried by point colour. Mitigation: stage labels below, plus distinct marker shapes for the two colour schemes. |
| Risk | Closest to the standard before/after form, so lowest novelty (see below) |

**Honest assessment of the novelty risk:** the before/after embedding pair is the most
common graphical abstract in the batch-correction literature. Rendering it as one
continuous strip is a real improvement but a variation on a familiar theme, not a new
idea. If the brief is "unique among millions", B is the weakest of the three. It is
also the most immediately legible of the three, which is a genuine counter-argument.

### Layout (frame-relative px)

| Element | Position | Notes |
|---|---|---|
| Headline | x 24, y 20–52 | 32 px Arimo Bold |
| Colour-key label | right-aligned, y 24–48 | 24 px |
| Strip | x 0–720, y 72–248 | Full bleed, 176 px tall |
| Stage panels | 5 × 144 px wide | No borders, no gaps |
| Stage labels | y 256–280, centred per panel | 24 px, ≤12 characters each |

Asset: one PNG at **3000 × 733 px** (600 dpi at 127 mm), or five PNGs at 600 × 733 if
per-panel placement proves easier to align.

### Text inventory — 7 items

| # | Text | px / pt |
|---|---|---|
| 1 | BATCH OUT, BIOLOGY IN | 32 / 16 |
| 2 | colour: batch → biology | 24 / 12 |
| 3–7 | Raw · Batch removed · Imputed · Harmonized (MNN) · Post-removal | 24 / 12 |

---

## Variant C — "The decision fan"

```
┌──────────────────────────────────────────────────────────────────────┐
│  WHICH HARMONIZER? IT DEPENDS                               32px/16pt│
│                                                                      │
│              ╱▔▔▔╲   ╱▔▔▔╲   ╱▔▔▔╲   ╱▔▔▔╲                          │
│         ╱▔▔╲ │MNN│   │SVA│   │SVA│   │MNN│ ╱▔▔╲    ← outer: method   │
│        ╱ Fresh ╲ │ FFPE │ │RNA-seq│ │ Mixed ╲                        │
│       ╱  frozen  ╲──────╲─╲───────╱─╱ platforms╲   ← inner: subset   │
│      ╱─────────────── 7,174 samples ─────────────╲   28px/14pt       │
└──────────────────────────────────────────────────────────────────────┘
```

A semicircular fan rising from the bottom centre. **Sector angular width is
proportional to the number of samples in that data subset**, so the geometry itself
carries the dataset composition. The inner ring names the subset, the outer ring names
the winning method. The eye reads outward: *what data do I have → which method wins*.

A semicircle fits a 5:2 box almost perfectly, which is why this shape suits the format
better than a full circle would.

| Property | Value |
|---|---|
| One main point | Method choice is conditional on the data subset |
| Reading order | centre → outward, with a left-to-right sector sweep ~ §6.9 (weaker than A or B) |
| Text items | **6** — the leanest of the three |
| Originality | ⚠ **Overlaps Figure 11**, the existing decision tree (see below) |
| Colour-blind safety | Sectors labelled directly with text ✓ §6.7 |
| Risk | The §6.9 originality question is real, not hypothetical |

**Honest assessment of the originality risk:** `fig11_decision_tree_harmonization_selection.svg`
already presents this decision as a tree. A radial restatement of the same content
could attract an editorial query under §6.9's "not a copy of any main figure". The
counter-argument is that a proportional sample-weighted fan carries information the
tree does not (subset sizes) and is visually unmistakable from it. **If C is selected,
expect to justify this, or to adjust Figure 11.**

### Layout (frame-relative px)

| Element | Position | Notes |
|---|---|---|
| Headline | x 24, y 20–48 | 32 px Arimo Bold |
| Fan centre | (360, 265) | Semicircle opening upward |
| Inner ring | r 60–120 | Subset names |
| Outer ring | r 120–205 | Method names; arc top at y ≈ 60 |
| Centre label | (360, 238) | 28 px, "7,174 samples" |
| Sectors | 4 | Angular width ∝ subset sample count |

Asset: `ga_decision_fan.svg` — matplotlib `Wedge` patches only, **no text**. All six
labels are Figma text nodes.

### Text inventory — 6 items

| # | Text | px / pt |
|---|---|---|
| 1 | WHICH HARMONIZER? IT DEPENDS | 32 / 16 |
| 2 | 7,174 samples | 28 / 14 |
| 3–6 | Fresh frozen → MNN · FFPE → SVA · RNA-seq → SVA · Mixed → MNN | 24 / 12 |

---

## Variant comparison

| | A — Mosaic | B — Strip | C — Fan |
|---|---|---|---|
| Novelty | **Highest** | Lowest | High |
| Immediate legibility | Medium | **Highest** | Medium |
| Text items | 8 | 7 | **6** |
| §6.9 originality risk | None | Low | ⚠ Fig 11 overlap |
| §6.7 colour-blind safety | Good | ⚠ Weakest | **Best** |
| Asset generation effort | Highest (mosaic + 4 t-SNE) | Medium (1 strip) | Lowest (1 SVG) |
| Recommendation | ★ **Recommended** | Fallback if A reads as too abstract | Only if Fig 11 overlap is accepted |

---

## Files to change

### 1. NEW — `figures_for_article/graphical_abstract_assets.py`

A standalone, cacheable asset generator producing the assets for **all three
variants**, following the project's modularization rule (root `CLAUDE.md`
"Architectural principles"). Modelled on the existing `pipeline_scheme_figure.py` and
`fig10_metric_star_visualization.py`, which are the precedent for standalone figure
scripts in this directory.

Header must document every data filter applied, per the Transparency principle.

```python
"""Graphical Abstract assets for the ComboBatch article (NAR).

Generates artwork for three candidate graphical-abstract variants, composed in
Figma frames "Graphical Abstract v2-A/B/C":

  Variant A:  ga_benchmark_mosaic.svg    2,234 attempt tiles
              ga_platform_stack.svg      proportional platform bands
              ga_tsne_<subset>.png x4    verdict thumbnails, 900 px
  Variant B:  ga_morph_strip.png         5 real pipeline stages, 3000 px
  Variant C:  ga_decision_fan.svg        sample-weighted semicircular fan

All assets contain ARTWORK ONLY -- no text. Every label is a Figma text node in
Arimo, so the Figma acceptance audit can verify all type in the figure.

Typography for any incidental in-asset type: Liberation Sans (Arial-metric),
12 pt floor. Designed for a 127 x 50.8 mm (5:2) final canvas.

Filters applied
---------------
- mosaic: metrics_comprehensive.csv, rows where <valid-attempt predicate>;
  expect 2,234 rows -- asserted, not assumed.
- t-SNE / strip: <subset and stage predicates>, from S3 harmonized matrices.
- fan: sector angles from platform sample counts (3,821 / 2,386 / 940 / 64).
"""
```

Functions, one purpose each, per the Coding Standards:

| Function | Variant | Output |
|---|---|---|
| `load_composite_scores()` | A | asserts row count == 2,234 |
| `make_benchmark_mosaic(scores, out_path)` | A | `ga_benchmark_mosaic.svg` |
| `make_platform_stack(counts, out_path)` | A | `ga_platform_stack.svg` |
| `make_verdict_tsne(subset, method, out_path)` | A | `ga_tsne_<subset>.png` ×4 |
| `make_morph_strip(stages, out_path)` | B | `ga_morph_strip.png` |
| `make_decision_fan(counts, out_path)` | C | `ga_decision_fan.svg` |
| `main()` | all | 7 assets into `figures/ga/` |

Mandatory rcParams block (project convention, `figures_for_article/CLAUDE.md`):

```python
plt.rcParams["pdf.fonttype"] = "truetype"
plt.rcParams["svg.fonttype"] = "none"     # text stays editable in Figma
plt.rcParams["figure.dpi"] = 200
plt.rcParams["font.family"] = "Liberation Sans"   # NEW: Arial-metric, NAR 6.6
sns.set_style("ticks")
GA_FONT_PT = 12    # NAR 6.9 floor; do not lower
```

Note the deliberate departure: `figures_for_article/CLAUDE.md` fixes
`GLOBAL_FONT_SIZE = 10` "for Figma alignment". **10 pt is illegal in a graphical
abstract.** This script must override it to 12 pt, and that exception needs recording
in the subsystem CLAUDE.md (change 6 below) so it does not read as a mistake later.

### 2. NEW — `figures_for_article/figures/ga/` output directory

Seven files across the three variants. Kept separate from `figures/` so the GA assets
are not confused with numbered article figures — they must remain demonstrably *not*
copies of them (§6.9).

### 3. Figma — archive the current frame

Before any edit, duplicate `757:65863` and rename the copy
`Graphical Abstract v1 (archive 260731)`, parked clear of the working area. The
current version is the fallback if all three variants are rejected, and `use_figma`
writes are not undoable from the API side.

### 4. Figma — three variant frames

Create `Graphical Abstract v2-A`, `v2-B`, `v2-C`, each **720 × 288** with explicit
white fill, stacked vertically with 60 px gaps in free canvas space.

### 5. Figma — typography

Load fonts **before** creating or mutating any text, per the canonical recipe:

```js
await figma.loadFontAsync({ family: "Arimo", style: "Regular" });
await figma.loadFontAsync({ family: "Arimo", style: "Bold" });
```

Verified available: Arimo Regular / Bold / Italic / Bold Italic. Do **not** guess
"Semi Bold" — Arimo does not have it (that is an Inter style, and the classic
figma-use footgun).

### 6. Figma — import assets via `upload_assets`

The assets cannot be inlined into `use_figma`: the `code` parameter caps at
**50,000 characters**, and a 2,234-rect SVG plus the scatter plots exceed that by a
wide margin. `figma.createImageAsync` is also explicitly unsupported by this MCP
server.

Route: the **`upload_assets` tool** (available on the plugin server; its schema is not
loaded yet — load it and confirm it accepts local file paths before relying on this
step). Upload the seven files, then place them with `use_figma` using the returned
handles.

Fallback if `upload_assets` cannot take local paths: draw the Variant A mosaic
procedurally inside Figma by passing only quantized scores as a compact string
(2,234 × 2 chars ≈ 4.5 kB, comfortably within the limit) and creating tiles in
**8 batched calls of ~280 rects**, respecting the incremental-workflow guidance. The
Variant C fan can likewise be drawn as ~4 `Wedge`-equivalent vectors natively. The
t-SNE thumbnails and the Variant B strip have no such fallback and must be uploaded.

### 7. Figma — assemble each variant incrementally

Per figma-use §6, one zone per call, `placeholder = true` while building and cleared
when done, returning all created node IDs each time, with a `get_screenshot` check
between zones. Build A fully, then B, then C — not interleaved, so a failure in one
does not leave three half-built frames.

### 8. Figma — original vector icons where a variant needs them

Any icon required (Variant A's platform stack may want none) is drawn as an original
`VectorNode` in-script, as done for the snowflake `903:2`. No v1 raster is reused in
any variant.

### 9. `figures_for_article/CLAUDE.md`

- Add a `Fig GA` row to the "Implemented figures" table pointing at
  `graphical_abstract_assets.py` and `figures/ga/`.
- Add `graphical_abstract_redesign_plan_260731.md` to the "Implementation plan files"
  table.
- Record the **`GLOBAL_FONT_SIZE = 10` exception**: the GA uses 12 pt minimum because
  §6.9 forbids anything smaller. Without this note the next person will "fix" it back.
- Note the Arimo (Figma) / Liberation Sans (matplotlib) typographic pairing and why.
- Note the **all-text-in-Figma, no-text-in-assets** rule and its reason.

### 10. `figures_for_article/figma_review_260731.md`

- Append a "Superseded by" line pointing at this plan, so the review and the plan are
  not read as competing sets of recommendations.
- Update finding 3: the sample count is **resolved** — 7,174 is correct, 7,238 is not.

---

## Handover to Daniil (not actioned by this plan)

The manuscript is **not touched** — Daniil is reviewing it directly. Two items are
therefore delivered here as text to insert rather than as edits.

### Alt text (required by §6.7, currently missing)

Place directly under the graphical abstract's legend in the manuscript, prefixed with
the literal label `Alt text:`. Draft for **Variant A**:

> `Alt text: Graphical abstract in three parts. Left: the input dataset, 7,174
> germinal-centre lymphoma samples from 88 cohorts across four platforms, shown as
> proportional bands. Centre: a mosaic of 2,234 small tiles, one per harmonization
> attempt, shaded by composite score across 87 metrics; most tiles score poorly and
> only a few score well. Right: four verdicts extracted from the benchmark — fresh
> frozen tissue is best harmonized by MNN, FFPE and RNA-seq-only subsets by SVA, and
> mixed platforms by MNN — each with a t-SNE thumbnail showing batches mixed and
> biology preserved. Take-home point: no single harmonization method is best for all
> data subsets.`

Alt text for B and C will be drafted once a variant is selected.

### BioRender acknowledgement (§6.10)

Needed **only if** a BioRender-derived icon survives into the selected variant. Since
all three variants use original vectors only, the expected answer is that **no
acknowledgement is required** — worth confirming before submission.

---

## Files that do NOT need to change

| File | Why not |
|---|---|
| `FL_harmonization_article_NAR_260728.docx` and all manuscript files | **Excluded by instruction** — Daniil is reviewing the manuscript himself. See Handover above. |
| `pipeline_scheme_figure.py`, `figures/pipeline_scheme.svg` | Stays as main Figure 1C. The GA simply must stop reusing it (§6.9) — the figure itself is fine. |
| `fig11_decision_tree_harmonization_selection.svg` | Stays as Figure 11. Only revisit if Variant C is selected (see its originality risk). |
| `Finally_assembled_figures_for_article.ipynb`, `Introductory_figures_for_article.ipynb` | The GA gets its own standalone script; no notebook cell is involved. |
| `harmonization-scripts/*`, `harmonization-metrics/*` | Read-only consumers of `metrics_comprehensive.csv`. No pipeline change. |
| `.claude/skills/nar_review_tools.py` | Used as-is for verification (`figures` subcommand). |
| Figma frame `757:65863` | **Not edited** — archived as v1 and left intact. |
| Snowflake `903:2` | Belongs to the v1 frame. The variants may not use it; keep it in the archive rather than deleting. |

---

## Side effects and caveats

1. **Mosaic tile ordering must be defensible (Variant A).** 2,234 tiles in an arbitrary
   order is decoration; ordered meaningfully it is data. Recommend sorting by composite
   score descending, filled left-to-right, top-to-bottom, so the visual gradient *is*
   the score distribution. State the ordering in the caption. Do **not** order by
   method or strategy without saying so — a reader will infer structure that is not
   there.
2. **22 empty tiles (Variant A).** 47 × 48 = 2,256 cells for 2,234 attempts. Leave the
   trailing 22 blank (not white-filled) rather than distorting the grid; mention in the
   caption if anyone might count.
3. **Agilent is 64 / 7,174 = 0.9%.** A strictly proportional band is ~1 px tall and
   effectively invisible in Variant A's stack, and its fan sector in Variant C is
   ~1.6° wide. Either enforce a minimum size and mark it with an asterisk, or label
   counts directly. Do not silently exaggerate it. Note also that Variant A's stack
   carries **no per-platform labels** (text budget), so the platform breakdown lives in
   the alt text and caption only.
4. **Building three variants roughly triples the work** of building one: 7 assets
   instead of 3, three Figma frames, three acceptance audits. This is the accepted
   cost of choosing from finished artwork rather than from descriptions. Two of the
   three will be discarded — archive rather than delete them, in case a reviewer later
   asks for an alternative.
5. **All benchmark counts must be re-verified against the data, not copied from
   `CLAUDE.md`.** `CLAUDE.md` says 2,234 attempts / 87 metrics, while the
   `project_june2026_status` memory records 3,835 metrics. `load_composite_scores()`
   must `assert` the row count and fail loudly on mismatch. The sample count 7,174 is
   settled and needs no further checking.
6. **Originality of the regenerated embeddings.** Regenerating at GA size is not by
   itself enough if the same panels appear in a main figure. Confirm against
   `supp9_embeddings_best_stars.svg` and `supp7s_umap_entropy.svg`, and choose subsets,
   stages, or styling that make the GA panels demonstrably distinct. This applies to
   Variant A's four thumbnails and to all five of Variant B's stages.
7. **CMYK is a revision-stage task** (§6.5). matplotlib cannot emit CMYK directly;
   convert the final export with Ghostscript or ImageMagick. §6.1 permits
   screen-resolution RGB at initial submission, so this must not block submission —
   but it must not be forgotten either.
8. **`use_figma` writes are not revertible via the API.** Hence the archive step 3
   before anything else. Failed scripts are atomic (no partial nodes), but *successful*
   unwanted ones are only undoable by hand in the Figma UI.
9. **Frame `757:65863` currently has 1,443 descendant nodes.** Duplicating it is
   cheap, but do not attempt to "clean up" the duplicate-node pairs from
   `figma_review_260731.md` finding 2 in the same session as this redesign — separate,
   independently verifiable changes.
10. **Text volume is a one-way door.** Dropping from 24 labels to 6–8 loses the
    step-by-step pipeline narrative. That narrative still exists in Figure 1C, which is
    where a reader who wants it will look. Variant B retains the most of it (five stage
    labels); Variant C retains the least.
11. **The root `CLAUDE.md` Dataset section still says ~7,238 samples**, which is the
    incorrect figure. It is the source from which this error will keep resurfacing.
    Correcting it is listed as an optional documentation item below — flagged rather
    than assumed, since it is outside this plan's original scope.

---

## Verification commands

```bash
source ~/venvs/collagen_3_11/bin/activate
cd ~/FL_harmonization/figures_for_article

# 1. Generate all seven assets; asserts the 2,234-row count internally
python graphical_abstract_assets.py

# 2. Confirm all seven assets exist and are non-trivial
ls -la figures/ga/

# 3. Project figure auditor: size, legibility at print size, fonts, colour space
python ~/FL_harmonization/.claude/skills/nar_review_tools.py \
    figures figures/ga/

# 4. Confirm no silent DejaVu fallback in any emitted SVG
python -c "
import re, pathlib
for p in sorted(pathlib.Path('figures/ga').glob('*.svg')):
    fams = set(re.findall(r'font-family:\s*([^;\"]+)', p.read_text()))
    print(p.name, fams)
    assert not any('DejaVu' in f for f in fams), f'{p.name}: font fell back to DejaVu'
"
```

Figma-side acceptance gate — run per variant frame; every value must pass:

```js
// via use_figma, once per variant frame id
const f = await figma.getNodeByIdAsync("<variant frame id>");
const PT = 360 / f.width;
const t = f.findAllWithCriteria({types:["TEXT"]}).map(n => ({
  chars: n.characters.slice(0,40),
  px: n.fontSize,
  pt: Number((n.fontSize * PT).toFixed(2)),
  fam: n.fontName.family,
}));
return {
  aspect: Number((f.width/f.height).toFixed(4)),   // must be exactly 2.5
  hasWhiteBg: JSON.stringify(f.fills),             // must not be []
  textCount: t.length,                             // A<=8, B<=7, C<=6
  violations: t.filter(x => x.pt < 12 || x.pt > 16 || x.fam !== "Arimo"),  // must be []
  texts: t,
};
```

Acceptance gate per variant: `aspect === 2.5`, `violations` empty, `textCount` within
that variant's budget, `hasWhiteBg !== "[]"`.

Final step: export all three at 127 mm and view them at actual size, side by side,
before selecting.

---

## Implementation status — 2026-07-31

Implementation began the same day the plan was approved. **Blocked partway** by an
external limit, documented below. Three findings from implementation change the plan's
own claims and are recorded here rather than buried in a commit message.

### Finding 1 — there is no elite cluster; the drafted alt text was wrong

The composite score distribution over all 2,234 attempts is **smooth and unimodal**:

| min | 5% | 25% | median | 75% | 95% | max |
|---|---|---|---|---|---|---|
| 0.3397 | 0.3942 | 0.4541 | 0.4857 | 0.5495 | 0.6058 | 0.6615 |

IQR/range = 0.296. Only **0.0355** separates rank 1 from rank 50, and 0.0698 separates
rank 50 from rank 500. There is no small set of standout winners.

Consequence: the alt text drafted in the Handover section — "most tiles score poorly and
only a few score well" — **would have been misleading and must not be used**. The honest
reading is a narrow continuum with no standout winner, which supports the
"NO UNIVERSAL HARMONIZER" headline more directly than the original framing did. The
Handover alt text is superseded by the corrected wording below.

### Finding 2 — the recommended approaches are not the top-ranked ones

| Verdict panel | run_id | Composite rank |
|---|---|---|
| Fresh frozen → MNN | `J_ff_only__strict__10_mnn__post1` | **5** / 2,234 |
| RNA-seq → SVA | `C_rnaseq_only__softimpute__04_sva__post0` | **45** / 2,234 |
| FFPE → SVA | `K_ffpe_only__softimpute__04_sva__post0` | **47** / 2,234 |
| Mixed platforms → MNN | `A_confirmed_bad__knn__10_mnn__post1` | **213** / 2,234 |

This is expected but must be stated in the caption: composite score aggregates 87
*global* metrics, whereas the decision tree is driven by *local* biology preservation.
A reader who assumes the recommendations are the composite winners will be confused by
rank 213. The four tiles are outlined in the mosaic so the relationship is visible
rather than hidden.

### Finding 3 — a biology-labelling bug, caught and fixed

The first implementation collapsed diagnoses with substring matching, testing for
`"_b_"` to find normal B cells. The literal value is `Diffuse_Large_B_Cell_Lymphoma`,
so **all 4,466 DLBCL samples were silently coloured as normal B cells**. Caught by
checking the rendered panels against the known composition (~3,000 DLBCL) rather than by
reading the code.

Fixed by matching exact diagnosis names plus the `TUMOR_NORMAL` flag. `Major_group` was
evaluated and rejected: it mixes disease names with cohort sources (`Normal_B_cells`,
`Kassandra`) for the normal samples. Verified group counts after the fix:

| Panel | DLBCL | FL | Normal | Other |
|---|---|---|---|---|
| Fresh frozen | 557 | 832 | 739 | — |
| FFPE | 1,970 | 490 | — | 40 |
| RNA-seq | 1,540 | 352 | 303 | 48 |
| Mixed | 1,280 | 739 | 452 | 29 |

FFPE having zero normal samples is correct, not a defect.

Two further implementation corrections worth recording:

- **`imshow` cannot be used for the mosaic.** It embeds a raster at the grid's native
  47 × 48 px, which is ~34 dpi at the final ~35 mm width. Replaced with 2,234 explicit
  `Rectangle` patches; the SVG now contains 2,239 vector paths and zero embedded images.
- **Tiles need thin white edges.** Without them the mosaic renders as a smooth gradient
  swatch and the "one tile per attempt" reading is lost entirely.

### BLOCKER — Figma MCP tool-call limit (Starter plan)

Further Figma writes are blocked:

> You've reached the Figma MCP tool call limit on the Starter plan.

The account is `Daniil Nikitin's team` (`team::1303927689220376868`), **starter tier**.
The limit applies to Figma MCP *tool* calls, so `use_figma`, `get_screenshot` and
`upload_assets` are all affected — including the audit and screenshot steps needed to
verify what was built.

Note that POSTing bytes to an already-issued upload URL is plain HTTP and does **not**
consume quota; three uploads were completed that way after the limit hit. Upload URLs
expire after 10 minutes, so this only helps for URLs already in hand.

Resolution options, for Daniil to choose:
1. Wait for the quota window to reset, then resume (no cost, unknown delay).
2. Upgrade the Figma plan.
3. Finish the remaining placement by hand in the Figma UI — all assets are generated and
   sitting in `figures/ga/`, and the target rectangles are named `asset:*` inside each
   frame, so manual placement is a drag-and-drop job.

### RESOLUTION — composed as PDFs instead of in Figma (2026-07-31, later)

Daniil chose a fourth option not in the list above: **draw the three variants as complete
PDFs locally**, bypassing Figma entirely. All three are delivered:

| File | Variant | Size |
|---|---|---|
| `graphical_abstract_variantA_mosaic.pdf` | A — mosaic → verdicts | 183 kB |
| `graphical_abstract_variantB_strip.pdf` | B — continuous strip | 197 kB |
| `graphical_abstract_variantC_fan.pdf` | C — decision fan | 19 kB |

Each also has a 600 dpi PNG proof alongside it for on-screen review.

New script `graphical_abstract_pdfs.py` composes them; the artwork drawers were extracted
from `graphical_abstract_assets.py` into shared `draw_*(ax, ...)` functions, so both routes
render identical artwork and nothing is duplicated. Nothing re-downloads from S3 — all
five embeddings come from the `.npz` cache.

**The PDF route is better than the Figma route, not merely a fallback.** On a 360 pt-wide
page matplotlib's `fontsize=12` *is* 12 pt on paper, so §6.9's type rule is expressed
directly instead of through the `0.4768 pt per px` conversion Figma required. Verified on
all three files:

| Check | Requirement | Measured |
|---|---|---|
| Page size | ≥ 127 × 50 mm (§6.9) | **127.0 × 50.8 mm** |
| Aspect | exactly 5:2 (§6.9) | **2.5000** |
| Minimum type | 12 pt (§6.9) | **12.0 pt, 0% below** |
| Maximum type | 16 pt (§6.9) | **16.0 pt** |
| Font | one sans-serif, embedded (§6.6) | **LiberationSans + Bold, embedded, no DejaVu fallback** |
| Resolution | 300/600 dpi at final size (§6.3) | **all-vector — 0 embedded raster images** |
| Text items | used sparingly (§6.9) | **A = 8, B = 7, C = 6, as budgeted** |
| Background | — | **explicit white**, not transparent |

`_report_text_fit()` measures the rendered extent of every string against its zone and
exits non-zero on overflow, so a clipped label cannot ship silently. It caught one real
overflow: "Mixed platforms → MNN" is 131 pt at 12 pt against a 117 pt column. Fixed by
shifting zones 2 and 3 left — 12 pt is the legal floor, so the widest label has to dictate
the widest column. Shortening the label was rejected as losing meaning.

### Three defects fixed that the Figma route had not yet exposed

1. **Variant C's labels did not fit their sectors.** Horizontal text only fits a curved
   band near the top of the arc; at the horizontal left and right ends the labels ran
   clean off the artwork onto white space. Fixed by moving **all four** labels outside the
   arc, aligned by angle. This also solves a problem the plan got wrong: a semicircle is
   2:1, not 5:2, so it *cannot* fill this page — the plan's claim that "a semicircle fits a
   5:2 box almost perfectly" is false, and about 160 pt of width was left empty. The
   external labels are what now occupy those corners.
2. **Variant C's rings were mis-proportioned.** The label straddled the white split line
   between the two bands, and "7,174 samples" overflowed the centre hole. Radii retuned to
   `FAN_R_HOLE = 0.50`, `FAN_R_SPLIT = 0.72`.
3. **Variant B did not read as continuous.** Each embedding is drawn on equal axes and its
   point cloud does not fill its square, so the five panels read as five separate plots —
   destroying the one idea the variant exists for. Fixed with a faint full-bleed band
   (`#F4F6F8`) behind all five panels, giving them a shared ground. B's headline rule was
   also dropped: a 10–350 pt rule above a 0–360 pt band looks like a mis-drawn band edge.

The §6.7 marker-shape gap is also now closed: `draw_biology_scatter()` gives each
diagnosis group its own marker (DLBCL circle, FL triangle, Normal square), so neither
Variant A's thumbnails nor Variant B's biology stages depend on hue alone.

### One remaining disclosure, new to Variant C

The fan needed the same treatment as the platform stack. "Mixed platforms" is 288 / 7,174
= 4.0% of samples, a **7.2°** sliver no label can sit in. `MIN_SECTOR_DEG = 18.0` widens
it and shrinks the other three proportionally; the applied distortion is printed at run
time. **Both exaggerations must be disclosed in the caption** if C is selected:

| Element | True | Drawn |
|---|---|---|
| Agilent band (A) | 0.89% | 3.50% |
| Mixed platforms sector (C) | 7.2° | 18.0° |

The label is abbreviated to "Mixed" because the full "Mixed platforms" ends 0.3 pt short
of the right margin — too tight to ship.

### Figma node inventory as built

| Node | What it is |
|---|---|
| `757:65863` | Original v1 frame — **untouched** |
| `910:2` | `Graphical Abstract v1 (archive 260731)`, full 1,443-node clone, parked at (10579, −2900) |
| `910:1446` | `v2-A (mosaic to verdicts)` at (10579, −2458), 720 × 288, aspect 2.5, white |
| `910:1448` | `v2-B (continuous strip)` at (10579, −2110) — frame + headline only |
| `910:1450` | `v2-C (decision fan)` at (10579, −1762) — frame + headline only |

Variant A contents (8 text nodes, exactly the budget):

| Node | Content | Size | State |
|---|---|---|---|
| `910:1447` | "NO UNIVERSAL HARMONIZER" | 32 px / 16 pt Bold | ✓ |
| `911:2` | "7,174 / samples" | 28 px / 14 pt Bold | ✓ |
| `911:3` | "88 cohorts / 4 platforms" | 24 px / 12 pt | ✓ |
| `911:6` | "2,234 attempts / 87 metrics" | 24 px / 12 pt | ✓ |
| `911:8` `911:10` `911:12` `911:14` | four verdict labels | 24 px / 12 pt | ✓ |
| `911:5` | mosaic asset | 170 × 170 | ✓ **placed** |
| `911:4` | platform stack asset | 48 × 84 | ✓ **placed** |
| `911:7` | t-SNE fresh frozen | 44 × 44 | ✓ **placed** |
| `911:9` | t-SNE FFPE | 44 × 44 | ✓ **placed** |
| `911:11` | t-SNE RNA-seq | 44 × 44 | ✗ grey placeholder — blocked |
| `911:13` | t-SNE mixed | 44 × 44 | ✗ grey placeholder — blocked |

All measured text widths fit their zone budgets; Arimo proved narrower than estimated
("Fresh frozen → MNN" measures 135 px against a 156 px budget).

### Corrected alt text for Variant A

Supersedes the Handover draft. Reflects findings 1 and 2.

> `Alt text: Graphical abstract in three parts. Left: the input dataset, 7,174
> germinal-centre lymphoma samples from 88 cohorts across four platforms, shown as
> proportional bands. Centre: a mosaic of 2,234 tiles, one per harmonization attempt,
> shaded by composite score across 87 metrics; scores form a narrow continuous range
> with no standout winner, and four outlined tiles mark the recommended approaches.
> Right: four verdicts — fresh frozen tissue is best harmonized by MNN, FFPE and
> RNA-seq-only subsets by SVA, and mixed platforms by MNN — each with a t-SNE thumbnail
> coloured by diagnosis. Take-home point: no single harmonization method is best for all
> data subsets.`

---

## TODO

**Decisions taken during implementation (proceeded under stated assumptions):**

- [x] Headline wordings — implemented as proposed; all three are editable text nodes, retype freely
- [x] Caveat 10 trade accepted (24 labels → 8 in Variant A)
- [x] Arimo / Liberation Sans confirmed and used — real Arial is installed in neither environment
- [ ] Optional: authorise correcting the root `CLAUDE.md` ~7,238 → 7,174 (caveat 11) *(not done — outside the annotated scope)*

**Asset generation — shared:**

- [x] Create `figures_for_article/graphical_abstract_assets.py` with the documented header
- [x] Set `font.family = "Liberation Sans"` and `GA_FONT_PT = 12` in the rcParams block
- [x] Create the `figures/ga/` output directory
- [x] Add embedding coordinate caching to `figures/ga/_embedding_cache/` *(not in the original plan; added because a colour fix would otherwise re-download 2.9 GB)*

**Asset generation — Variant A:**

- [x] Implement `load_composite_scores()` with a hard `assert` on the 2,234-row count *(verified: 2,234 rows, 87 metrics, 31 methods, 14 strategies)*
- [x] Implement `make_benchmark_mosaic()` — 47 × 48 grid, score-descending, `Blues` ramp; **`imshow` replaced with 2,234 Rectangle patches** (see Finding 3 notes)
- [x] Add thin white tile edges — without them the mosaic reads as a gradient swatch
- [x] Outline the four verdict tiles so their global rank is visible (ranks 5, 45, 47, 213)
- [x] Implement `make_platform_stack()` — Agilent lifted 0.89% → 3.50%, printed as EXAGGERATED
- [x] Implement `make_verdict_tsne()` ×4 at 900 px, axes off, no text
- [x] Fix the biology-labelling bug (substring `_b_` matched DLBCL); use exact names + `TUMOR_NORMAL`

**Asset generation — Variant B:**

- [x] Implement the five real pipeline stages, 900 px each, no text *(delivered as 5 separate PNGs rather than one 3000 px strip — placement is per-panel in Figma, and 5 files let a single stage be regenerated alone)*
- [x] Choose and document the five pipeline stages and the batch→biology colour transition
- [x] Add distinct marker shapes for the two colour schemes (§6.7 mitigation) — done in the PDF route via `draw_biology_scatter()`: DLBCL circle, FL triangle, Normal square

**Asset generation — Variant C:**

- [x] Implement `make_decision_fan()` — semicircular wedges, angles ∝ subset sample counts, no text
- [x] The "Mixed platforms" sector is only **7.2°** wide — resolved with `MIN_SECTOR_DEG = 18.0`, the same lift-and-disclose pattern as the platform stack. Distortion printed at run time; **must be disclosed in the caption**

**Asset verification:**

- [x] Run the script; **12** files in `figures/ga/` (3 fast + 4 verdict + 5 strip), not 7 as planned
- [x] Run `nar_review_tools.py figures figures/ga/` — no font or size findings
- [x] Verify no DejaVu fallback in any emitted SVG *(assets carry no text at all, by design)*
- [x] Confirm the mosaic SVG is true vector — 2,239 paths, zero embedded images
- [ ] Confirm regenerated embeddings are demonstrably distinct from Supp 9 / Supp 7s (caveat 6) — **not done**

**Figma assembly:**

- [x] Load the `upload_assets` schema — takes a `count`/`nodeId` and returns upload URLs; bytes are POSTed over plain HTTP, which does not consume MCP quota
- [x] Duplicate `757:65863` → `910:2` `Graphical Abstract v1 (archive 260731)`, parked at (10579, −2900)
- [x] Scan `figma.currentPage.children` for free space *(730 children; rightmost edge 10279)*
- [x] `loadFontAsync` Arimo Regular **and** Bold before any text
- [x] Create all three frames, 720 × 288, aspect exactly 2.5, explicit white fill
- [x] Build `v2-A` text: 8 nodes, all measured against zone budgets, all fitting
- [x] Place 4 of 6 Variant A assets (mosaic, platform stack, 2 of 4 t-SNE thumbnails)
- [~] Place the remaining 2 Variant A thumbnails (`911:11` RNA-seq, `911:13` mixed) — **superseded**, delivered in the PDF instead
- [~] Build `v2-B` body: 5 strip panels + 5 stage labels + colour-key label — **superseded**, delivered in the PDF
- [~] Build `v2-C` body: fan asset + 6 labels — **superseded**, delivered in the PDF
- [x] Run the acceptance gate on each variant — done locally instead of in Figma: `_report_text_fit()` plus the geometry/font/raster checks tabulated above
- [x] Export all three at 127 mm and compare at actual size — the PDFs *are* 127 mm

**PDF composition (`graphical_abstract_pdfs.py`):**

- [x] Extract shared `draw_*(ax, ...)` artwork functions into `graphical_abstract_assets.py`
- [x] Compose all three variants at exactly 127.0 × 50.8 mm, aspect 2.5000
- [x] Enforce the 12–16 pt range and the per-variant text budget programmatically
- [x] Measure every string's rendered width against its zone; fail on overflow
- [x] Verify Liberation Sans + Bold are embedded and nothing fell back to DejaVu
- [x] Verify all three PDFs are fully vector (0 embedded raster images)
- [x] Set an explicit white background so no print pipeline renders it black
- [x] Fix Variant C label placement (all four moved outside the arc)
- [x] Fix Variant C ring radii so the centre label clears the hole
- [x] Give Variant B a shared background band so the five panels read as one strip

**Selection and follow-up:**

- [ ] Daniil selects one variant from the three finished frames
- [ ] Archive (do not delete) the two unselected frames
- [ ] Draft alt text for the selected variant if it is B or C
- [ ] Hand the alt text to Daniil for insertion into the manuscript *(Variant A alt text is drafted and corrected above)*

**Documentation:**

- [x] `figures_for_article/CLAUDE.md` — add the Fig GA row
- [x] `figures_for_article/CLAUDE.md` — add this plan to the plan-files table
- [x] `figures_for_article/CLAUDE.md` — record the `GLOBAL_FONT_SIZE = 10` → 12 pt GA exception
- [x] `figures_for_article/CLAUDE.md` — record the Arimo / Liberation Sans pairing
- [x] `figures_for_article/CLAUDE.md` — record the all-text-in-Figma rule
- [x] `figma_review_260731.md` — add the "Superseded by" pointer
- [x] `figma_review_260731.md` — mark finding 3 resolved (7,174 correct, 7,238 incorrect)
- [ ] Defer CMYK conversion to the revision stage; add it to the revision checklist *(requires the final export, which is blocked)*
