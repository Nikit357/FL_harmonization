#!/usr/bin/env python3
"""
Strip all cell outputs from both harmonization-metrics notebooks and reorganize
harmonization_metrics_visual_inspection.ipynb by strategy group.

Run from the harmonization-metrics/ directory:
    python strip_and_reorganize.py

What it does:
  1. Removes all outputs and resets execution_count on every code cell in both notebooks.
  2. Reorders cells 19-282 in harmonization_metrics_visual_inspection.ipynb into 11
     strategy groups (J, K, A/B, C, D, F, G, H, I, cross-strategy, generic), each
     preceded by a new ##-level markdown header. Inserts a Table of Contents cell at
     position 19. Cells 0-18 (setup) are kept in place.
"""

import json
from pathlib import Path

ANALYSIS_NB = "harmonization_metrics_analysis_v2.ipynb"
VISUAL_NB = "harmonization_metrics_visual_inspection.ipynb"

# ── Strategy group assignment ─────────────────────────────────────────────────
# Maps each original cell index (0-based in the full notebook) to a group key.
# Cells 0-18 are setup and stay in place (not in this dict).
GROUP_MAP: dict[int, str] = {}


def _assign(start: int, end_inclusive: int, group: str) -> None:
    for i in range(start, end_inclusive + 1):
        GROUP_MAP[i] = group


# J — J_ff_only (Fresh-Frozen only)
_assign(19, 24, "J")
# K — K_ffpe_only (FFPE only)
_assign(25, 36, "K")
# D — D_malignant_only: 25_angel + 05_combat + 26_xpn (first)
_assign(37, 58, "D")
# G — G_affymetrix_only: first section
_assign(59, 63, "G")
# H — H_affymetrix_extended
_assign(64, 68, "H")
# cross — cross-strategy method comparisons: 33_amdbnorm, 23_vst, 16_fsqn_r top-5
_assign(69, 85, "cross")
# F — F_microarray_only: best by PCR
_assign(86, 90, "F")
# D — D_malignant_only: 13_fsmvn through Shambhala (malignant) + empty placeholder
_assign(91, 141, "D")
# C — C_rnaseq_only: Shambhala (bad)
_assign(142, 149, "C")
# AB — A_confirmed_bad / B_extended_bad: MNN top-5
_assign(150, 155, "AB")
# C — C_rnaseq_only: FSQN py + kBET
_assign(156, 161, "C")
# D — D_malignant_only: Harmony
_assign(162, 166, "D")
# I — I_rare_batches_removed: 08_inmoose_combatseq
_assign(167, 171, "I")
# C — C_rnaseq_only: more kBET, Harmony kBET, TMM
_assign(172, 186, "C")
# D — D_malignant_only: Arsyn/Harman
_assign(187, 194, "D")
# C — C_rnaseq_only: 04_sva, per-batch violins, 11_harmony, 18_rank
_assign(195, 213, "C")
# G — G_affymetrix_only: mnn10 (mostly empty placeholder)
_assign(214, 218, "G")
# C — C_rnaseq_only: mnn10 average
_assign(219, 223, "C")
# AB — A/B: worst examples + angel normalization
_assign(224, 233, "AB")
# F — F_microarray_only: Scanorama
_assign(234, 238, "F")
# cross — cross-strategy: rank normalization
_assign(239, 243, "cross")
# G — G_affymetrix_only: mnn10 (awful)
_assign(244, 248, "G")
# F — F_microarray_only: qsmooth
_assign(249, 253, "F")
# G — G_affymetrix_only: 16_fsqn_r FAILED
_assign(254, 262, "G")
# generic — metric-sorted and miscellaneous
_assign(263, 282, "generic")

# Order in which groups appear in the reorganized notebook
GROUP_ORDER = ["J", "K", "AB", "C", "D", "F", "G", "H", "I", "cross", "generic"]

# Header title and one-line description for each group
GROUP_HEADERS: dict[str, tuple[str, str]] = {
    "J": (
        "Strategy: J — `J_ff_only` (Fresh-Frozen only)",
        "",
    ),
    "K": (
        "Strategy: K — `K_ffpe_only` (FFPE only)",
        "",
    ),
    "AB": (
        "Strategy: A/B — `A_confirmed_bad` / `B_extended_bad`",
        "General batch removal — confirmed and extended bad batches removed.",
    ),
    "C": (
        "Strategy: C — `C_rnaseq_only` (RNA-seq only)",
        "All imputation variants; fresh-frozen + FFPE RNA-seq fully mixed.",
    ),
    "D": (
        "Strategy: D — `D_malignant_only`",
        "Malignant samples only — excludes normal B-cell references.",
    ),
    "F": (
        "Strategy: F — `F_microarray_only`",
        "Microarray-only (Illumina + Agilent + Affymetrix mixed).",
    ),
    "G": (
        "Strategy: G — `G_affymetrix_only`",
        "Affymetrix GPL570 platform only.",
    ),
    "H": (
        "Strategy: H — `H_affymetrix_extended`",
        "Affymetrix + extended microarray platforms.",
    ),
    "I": (
        "Strategy: I — `I_rare_batches_removed`",
        "Batches with fewer than 50 samples removed before harmonization.",
    ),
    "cross": (
        "Cross-strategy: Method-level comparisons (all strategies)",
        "Each section filters by method across all strategies to compare behaviour.",
    ),
    "generic": (
        "Generic: Metric-sorted and miscellaneous explorations",
        "",
    ),
}

# Table of Contents entries — (display label, notes)
TOC_ENTRIES = [
    ("Strategy J — J_ff_only", ""),
    ("Strategy K — K_ffpe_only", ""),
    ("Strategy A/B — A_confirmed_bad / B_extended_bad", ""),
    ("Strategy C — C_rnaseq_only", "best: SVA+softimpute/knn ★"),
    ("Strategy D — D_malignant_only", ""),
    ("Strategy F — F_microarray_only", ""),
    ("Strategy G — G_affymetrix_only", ""),
    ("Strategy H — H_affymetrix_extended", ""),
    ("Strategy I — I_rare_batches_removed", ""),
    ("Cross-strategy: method-level comparisons", "33_amdbnorm, 23_vst, 16_fsqn_r"),
    ("Generic: metric-sorted explorations", "sort by kBET, tSNE, harsh methods"),
]


# ── Cell constructors ─────────────────────────────────────────────────────────

def _new_markdown(cell_id: str, source_lines: list[str]) -> dict:
    return {
        "cell_type": "markdown",
        "id": cell_id,
        "metadata": {},
        "source": source_lines,
    }


def make_toc_cell() -> dict:
    lines = ["## Table of Contents — Visual Inspection Sections\n", "\n"]
    for i, (label, notes) in enumerate(TOC_ENTRIES, start=1):
        note_str = f"  — {notes}" if notes else ""
        lines.append(f"{i}. **{label}**{note_str}\n")
    return _new_markdown("toc-visual-inspection", lines)


def make_group_header(group: str) -> dict:
    title, desc = GROUP_HEADERS[group]
    lines = [f"## {title}\n"]
    if desc:
        lines += ["\n", f"{desc}\n"]
    return _new_markdown(f"group-header-{group.lower()}", lines)


# ── Core operations ───────────────────────────────────────────────────────────

def strip_outputs(nb: dict) -> None:
    """Remove outputs and reset execution_count on every code cell in-place."""
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            cell["outputs"] = []
            cell["execution_count"] = None


def reorganize_visual(nb: dict) -> None:
    """Reorder cells 19-282 into strategy groups in-place."""
    cells = nb["cells"]

    setup_cells = cells[:19]

    # Validate that group_map covers exactly cells 19-282
    expected = set(range(19, 283))
    assigned = set(GROUP_MAP.keys())
    if expected != assigned:
        missing = expected - assigned
        extra = assigned - expected
        if missing:
            print(f"  WARNING: cells not assigned to any group: {sorted(missing)}")
        if extra:
            print(f"  WARNING: group_map has out-of-range indices: {sorted(extra)}")

    # Collect cells per group in original order
    grouped: dict[str, list] = {g: [] for g in GROUP_ORDER}
    for original_idx, cell in enumerate(cells):
        if original_idx < 19:
            continue
        g = GROUP_MAP.get(original_idx)
        if g is not None:
            grouped[g].append(cell)
        else:
            print(f"  WARNING: cell {original_idx} not in GROUP_MAP — placed in generic")
            grouped["generic"].append(cell)

    # Build new cell list
    new_cells = list(setup_cells)
    new_cells.append(make_toc_cell())
    for g in GROUP_ORDER:
        new_cells.append(make_group_header(g))
        new_cells.extend(grouped[g])

    nb["cells"] = new_cells


# ── Main ──────────────────────────────────────────────────────────────────────

def process_notebook(path: str, reorganize: bool = False) -> None:
    size_before = Path(path).stat().st_size
    with open(path, encoding="utf-8") as f:
        nb = json.load(f)
    cells_before = len(nb["cells"])

    strip_outputs(nb)
    if reorganize:
        reorganize_visual(nb)

    cells_after = len(nb["cells"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")

    size_after = Path(path).stat().st_size
    print(f"\n{path}:")
    print(f"  Size:  {size_before / 1e6:.1f} MB → {size_after / 1e6:.1f} MB")
    print(f"  Cells: {cells_before} → {cells_after} (Δ {cells_after - cells_before:+d} new header/ToC cells)")


def main() -> None:
    print("Stripping outputs and reorganizing notebooks...")
    process_notebook(ANALYSIS_NB, reorganize=False)
    process_notebook(VISUAL_NB, reorganize=True)
    print("\nDone. Verify with:")
    print("  python -c \"import json; nb=json.load(open('harmonization_metrics_visual_inspection.ipynb')); "
          "print('Cells:', len(nb['cells'])); "
          "[print(f'  [{i:3d}]', '##' if '##' in ''.join(c['source'])[:5] else '  ', ''.join(c['source'])[:80]) "
          "for i, c in enumerate(nb['cells']) if c['cell_type']=='markdown' and '##' in ''.join(c['source'])[:5]]\"")


if __name__ == "__main__":
    main()
