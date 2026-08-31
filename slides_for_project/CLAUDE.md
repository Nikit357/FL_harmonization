# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Directory purpose

Slide decks for supervisor meetings on the FL harmonization dissertation project. Each presentation cycle produces artefacts:

| File pattern | Role |
|---|---|
| `FL_project_update_slides_<YYMMDD>.md` | Slide-by-slide content plan (primary source of truth) |
| `FL_project_update_slides_<YYMMDD>.pptx` | PPTX auto-generated from the `.md` plan via python-pptx |
| `FL_project_update_slides_<YYMMDD>_manually_edited.pptx` | Human-polished version actually shown to supervisor |

Older decks used the prefix `supervisor_slides_<YYMMDD>` — both naming styles exist in the directory; new decks use `FL_project_update_slides_`.

## Environment

Always activate before running any Python script:
```bash
source ~/venvs/collagen_3_11/bin/activate
```

There is no standing generation script — one must be written per deck. The `supervisor_slides_260428.pptx` output is a concrete reference example (generated April 2026).

## Slide plan format

### Two formats exist

**Detailed format** (April 2026, `supervisor_slides_260428.md`) — one `##` section per slide, each with explicit `**Title:**` and `**Content:**` labels, tables, and code blocks:
```markdown
## SLIDE N — Short name

**Title:** Exact slide title
**Content:**
- bullet
- bullet

**Table:**
| Col | Col |
|---|---|
```
Appendix slides use `### A1`, `### A2`, etc. after the last numbered slide.

**Compact format** (May 2026, `FL_project_update_slides_260514.md`) — slide ranges are allowed, content is less structured:
```markdown
## SLIDES 5-7 — Section heading
**Title:** Exact title for first slide in range
**Content:**
- key finding
- key finding
```
Slide titles may appear in Russian when presenting to a Russian-speaking supervisor.

Use the compact format for new decks unless the supervisor requests more detail.

## Generating a PPTX

python-pptx is the standard library. Key imports:
```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
```

Mapping rules from `.md` to PPTX:
- Each `## SLIDE N` section → one slide using the **Title and Content** layout (index 1)
- `**Title:**` value → title placeholder text
- Bullet lists → `text_frame.add_paragraph()` with `level=0` (sub-bullets: `level=1`)
- Markdown tables → `slide.shapes.add_table(rows, cols, left, top, width, height)`
- Code blocks → `add_textbox` with monospace font (Courier New)
- `## SLIDES N-M` ranges → repeat the same title across M−N+1 slides with a placeholder note on slides 2+

Always save with `prs.save("FL_project_update_slides_<YYMMDD>.pptx")`.

## Presentation context

- **Audience:** Scientific supervisor with deep bioinformatics background
- **Language:** Slides may mix English and Russian; no strict rule
- **Length:** ~20–90 slides; allow multi-slide sections for visual inspection results
- **Focus:** Harmonization benchmark progress (current: 39 methods × 11 strategies × 4 imputation × 2 post-removal = 3,432 S3 outputs)
- **Primary metric:** PCA ANOVA R² of `RNA_BATCH` on first 10 PCs (lower = better; raw baseline ≈ 0.95, target < 0.20)
- **Current benchmark winner:** MNN (mutual nearest neighbors) across most metric clusters; best global R²: HarmonizR E3×softimpute ≈ 0.099

For full project context (dataset, methods, infrastructure) see `../CLAUDE.md`.

## Slide content guidelines

**Standard slide types that recur across decks:**

| Slide type | Key info to include |
|---|---|
| Title | Presentation title, date, author, affiliation |
| Agenda | Bulleted list of sections |
| Analysis overview / pipeline diagram | The 6-stage pipeline (filter → impute → log-transform → normalize → post-rm → metrics) |
| Dataset description | 88 cohorts, ~7,238 samples, diagnosis × RNA_BATCH breakdown table |
| Clustermap interpretation | Metric clusters 1–4; best/worst approach groups |
| Visual inspection (PCA/UMAP/tSNE) | One approach per 3–4 slides; annotate batch and biology coloring |
| Metrics deep dive | PCR, local neighborhood (kBET/iLISI/cLISI), global distance metrics |
| Shambhala section | Current status, action points |
| Conclusions / action points | Numbered list; split by topic (Shambhala, quick fixes, analysis, documentation) |

**Figures referenced in slides** are stored in `../harmonization-metrics/figures/` (SVG + PNG). When embedding in PPTX, prefer PNG at 200 DPI.
