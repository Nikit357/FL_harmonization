"""Graphical Abstract assets for the ComboBatch article (NAR).

Generates artwork for three candidate graphical-abstract variants, composed in
Figma frames "Graphical Abstract v2-A/B/C" of the file `FL harmonization article`
(file key t8bFgusleBEwB9ht7rORCH).

  Variant A:  ga_benchmark_mosaic.svg    2,234 attempt tiles, score-ordered
              ga_platform_stack.svg      proportional platform bands
              ga_tsne_<subset>.png x4    verdict thumbnails, 900 px
  Variant B:  ga_strip_stage<n>.png x5   five real pipeline stages, 900 px each
  Variant C:  ga_decision_fan.svg        sample-weighted semicircular fan

All assets contain ARTWORK ONLY -- no text. Every label in the final figure is a
Figma text node in Arimo. This keeps the Figma acceptance audit authoritative: it
can see and verify every character that appears in the graphical abstract, which
would be impossible for type baked into an SVG.

Typography for any incidental in-asset type: Liberation Sans (Arial-metric
substitute; real Arial is installed in neither Figma nor this pod), 12 pt floor.
Designed for a 127 x 50.8 mm (5:2) final canvas at the convention 2 px = 1 pt.

Filters applied
---------------
- mosaic: figures_helpers.load_metrics_data() applies the v3 notebook pipeline
  (status == "ok", one canonical Shambhala representative, NA filter at 5% of
  5,444 samples). Verified 2026-07-31 to yield exactly 2,234 rows and 87 scoring
  metrics; both are asserted, not assumed.
- composite score: unweighted mean of the 87 polarity-normalized scoring columns,
  matching the definition used by the barplot_composite_score_by_* figures.
- t-SNE / strip: per-panel S3 expression matrix, PCA to 50 components then t-SNE;
  subsampled to TSNE_MAX_POINTS for tractability and because a 44 x 44 px
  thumbnail cannot resolve more.
- platform stack: Agilent is 64 / 7,174 = 0.89% of samples and would render about
  1 px tall. A minimum band fraction is enforced, which DELIBERATELY EXAGGERATES
  the smallest platform. The applied distortion is printed and must be disclosed
  in the caption and alt text.

Usage
-----
    source ~/venvs/collagen_3_11/bin/activate
    cd figures_for_article
    python graphical_abstract_assets.py --fast     # mosaic, stack, fan (no S3)
    python graphical_abstract_assets.py --slow     # embeddings (downloads ~2.9 GB)
    python graphical_abstract_assets.py            # everything
"""

from __future__ import annotations

import argparse
import gzip
import io
import os
import tempfile
from pathlib import Path

import boto3
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle, Wedge
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

import figures_helpers as fh

# ── Project plot conventions (figures_for_article/CLAUDE.md) ──────────────────
# sns.set_style() MUST come first: it resets font.family to the generic
# "sans-serif", silently undoing the Liberation Sans choice if set beforehand.
sns.set_style("ticks")
plt.rcParams["pdf.fonttype"] = "truetype"
plt.rcParams["svg.fonttype"] = "none"          # text stays editable in Figma
plt.rcParams["figure.dpi"] = 200
plt.rcParams["font.family"] = ["sans-serif"]
plt.rcParams["font.sans-serif"] = ["Liberation Sans", "Arimo", "DejaVu Sans"]

# NAR 6.9 floor. The directory convention GLOBAL_FONT_SIZE = 10 is ILLEGAL in a
# graphical abstract, so this script deliberately overrides it.
GA_FONT_PT = 12

OUT_DIR = Path("figures/ga")
CACHE_DIR = Path("figures/ga/_embedding_cache")
# Same environment contract as bench_shared.py; only the t-SNE/strip panels touch S3,
# so the mosaic and platform-stack assets still build without a bucket.
S3_BUCKET = os.environ.get("FL_S3_BUCKET", "")
_S3_PREFIX = os.environ.get("FL_S3_PREFIX", "FL_batch_correction")
S3_EXP_PREFIX = f"{_S3_PREFIX}/exp"
S3_ANN_PREFIX = f"{_S3_PREFIX}/prepared"

# Sample counts per platform, from CLAUDE.md Dataset section. Total 7,211 vs the
# 7,174 headline: the headline is the authoritative unfiltered count (7,238 seen
# elsewhere is incorrect and must not be used), so bands are drawn from these
# four values normalized to their own sum, not to 7,174.
PLATFORM_COUNTS: dict[str, int] = {
    "Affymetrix": 3821,
    "Illumina NGS": 2386,
    "Illumina microarray": 940,
    "Agilent": 64,
}

# Okabe-Ito, colour-blind safe (NAR 6.7). Not the notebook's platform_palette,
# which lives in a notebook cell and is not importable.
PLATFORM_COLORS: dict[str, str] = {
    "Affymetrix": "#0072B2",
    "Illumina NGS": "#009E73",
    "Illumina microarray": "#E69F00",
    "Agilent": "#CC79A7",
}

# Temperature-split palette (root CLAUDE.md): normal = cold/blue, cancer = warm/red.
BIOLOGY_COLORS: dict[str, str] = {
    "DLBCL": "#B2182B",
    "FL": "#EF8A62",
    "Normal": "#2166AC",
    "Other": "#BBBBBB",
}

# One marker shape per biological group, so the grouping does not rely on colour
# alone (NAR 6.7). Order fixes the draw order, hence which group ends up on top.
BIOLOGY_MARKERS: dict[str, str] = {
    "Other": ".",
    "Normal": "s",
    "FL": "^",
    "DLBCL": "o",
}

# Minimum share of the stack any single platform may occupy, so Agilent stays
# visible at final print size. Exaggerates the smallest band on purpose.
MIN_BAND_FRACTION = 0.035

# Minimum angular width of a decision-fan sector, in degrees. "Mixed platforms"
# is 288 / 7,174 = 4.0% of samples, a 7.2 deg sliver that cannot carry a label.
# Same remedy as MIN_BAND_FRACTION: lift it, then disclose the distortion.
MIN_SECTOR_DEG = 18.0

# Decision-fan radii as fractions of the outer radius. The hole is large because
# it has to clear a two-line 14 pt "7,174 samples" label. Sector labels sit
# OUTSIDE the arc (FAN_R_LABEL > 1), not inside the bands: horizontal type only
# fits a curved band near the top of the semicircle, and the sectors at the
# horizontal left and right ends pushed their labels clean off the artwork.
FAN_R_HOLE = 0.50
FAN_R_SPLIT = 0.72
FAN_R_LABEL = 1.075

TSNE_MAX_POINTS = 2500
TSNE_RANDOM_STATE = 0

# Variant A: (subset label, strategy, imputation, method, post_rm) per the
# decision tree approved 2026-06-04.
VERDICT_PANELS: list[tuple[str, str, str, str, int]] = [
    ("fresh_frozen", "J_ff_only", "strict", "10_mnn", 1),
    ("ffpe", "K_ffpe_only", "softimpute", "04_sva", 0),
    ("rnaseq", "C_rnaseq_only", "softimpute", "04_sva", 0),
    ("mixed", "A_confirmed_bad", "knn", "10_mnn", 1),
]

# Variant B: five genuine pipeline stages. Not an interpolated morph -- each
# panel is a real S3 matrix at a real stage, so the progression is honest.
STRIP_STAGES: list[tuple[int, str, str, str, str, int]] = [
    (1, "raw", "S0_no_removal", "strict", "01_raw", 0),
    (2, "batch_removed", "A_confirmed_bad", "strict", "01_raw", 0),
    (3, "imputed", "A_confirmed_bad", "knn", "01_raw", 0),
    (4, "harmonized", "A_confirmed_bad", "knn", "10_mnn", 0),
    (5, "post_removal", "A_confirmed_bad", "knn", "10_mnn", 1),
]

# Variant C: fan sectors, angular width proportional to subset sample count.
# Counts are the platform/biomaterial subset sizes the decision tree splits on.
FAN_SECTORS: list[tuple[str, int, str]] = [
    ("Fresh frozen", 3200, "MNN"),
    ("FFPE", 1300, "SVA"),
    ("RNA-seq", 2386, "SVA"),
    ("Mixed platforms", 288, "MNN"),
]


# ── Shared helpers ────────────────────────────────────────────────────────────

def _s3() -> "boto3.client":
    return boto3.client("s3")


def _save_vector_asset(fig: plt.Figure, name: str) -> None:
    """Write an artwork-only asset as SVG plus a PNG proof.

    Uses transparent backgrounds so the Figma frame's white fill shows through
    and the asset can be placed over any zone without a visible bounding box.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / f"{name}.svg", bbox_inches="tight", pad_inches=0,
                transparent=True)
    # dpi=600, not the project default 200: the PNG is what actually gets placed
    # in Figma for the tile mosaic, and it must clear 600 dpi at a final printed
    # width of ~35 mm (NAR 6.3). The SVG remains the editable master.
    fig.savefig(OUT_DIR / f"{name}.png", bbox_inches="tight", pad_inches=0,
                dpi=600, transparent=True)
    plt.close(fig)


def _save_raster_asset(fig: plt.Figure, name: str, px: int) -> None:
    """Write a raster asset whose longest edge is `px` pixels.

    Embeddings are point clouds, so they are delivered as raster. `px` is chosen
    so that the panel exceeds 600 dpi at its final printed size (NAR 6.3).
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    size_in = fig.get_size_inches()
    fig.savefig(OUT_DIR / f"{name}.png", bbox_inches="tight", pad_inches=0,
                dpi=px / max(size_in), transparent=True)
    plt.close(fig)


def _load_composite_scores() -> pd.Series:
    """Return the composite score per harmonization attempt, best first.

    Composite score is the unweighted mean of the polarity-normalized scoring
    columns, so 1 = best on every metric. Asserts the two counts the plan and
    the figure captions depend on.

    Returns
    -------
    pd.Series
        Index = run_id, values in [0, 1], sorted descending.
    """
    df_ok, df_normed, scoring_cols, _ = fh.load_metrics_data()
    assert len(df_ok) == 2234, f"expected 2,234 attempts, got {len(df_ok)}"
    assert len(scoring_cols) == 87, f"expected 87 scoring metrics, got {len(scoring_cols)}"
    return df_normed[scoring_cols].mean(axis=1).sort_values(ascending=False)


def _download_matrix(strat: str, imp: str, method: str, post_rm: int) -> pd.DataFrame:
    """Stream one harmonized expression matrix from S3 into a DataFrame.

    Downloads to a temporary file and deletes it immediately after parsing, so
    peak disk stays at one matrix (the largest is ~711 MB gzipped) rather than
    the ~2.9 GB the full asset set would otherwise need.

    Returns
    -------
    pd.DataFrame
        samples x genes, per the project convention.
    """
    key = f"{S3_EXP_PREFIX}/{strat}__{imp}__{method}__post{post_rm}.tsv.gz"
    with tempfile.NamedTemporaryFile(suffix=".tsv.gz", delete=True) as tmp:
        _s3().download_fileobj(S3_BUCKET, key, tmp)
        tmp.flush()
        tmp.seek(0)
        exp = pd.read_csv(tmp.name, sep="\t", index_col=0, compression="gzip")
    return exp


def _download_annotation(strat: str, imp: str) -> pd.DataFrame:
    """Load the prepared annotation table for a (strategy, imputation) pair."""
    key = f"{S3_ANN_PREFIX}/{strat}__{imp}__ann.tsv.gz"
    buf = io.BytesIO()
    _s3().download_fileobj(S3_BUCKET, key, buf)
    buf.seek(0)
    with gzip.open(buf, "rt") as handle:
        return pd.read_csv(handle, sep="\t", index_col=0, low_memory=False)


def _embed(exp: pd.DataFrame) -> np.ndarray:
    """PCA to 50 components, then t-SNE to 2D.

    Subsamples to TSNE_MAX_POINTS first: a 44 x 44 px thumbnail cannot resolve
    more points than that, and t-SNE cost grows steeply with n.

    Returns
    -------
    np.ndarray
        Shape (n_kept, 2). Row order matches the subsampled index returned by
        the caller's own reindexing, so callers must use `exp.index` slicing
        consistently -- see `_subsample`.
    """
    values = np.nan_to_num(exp.to_numpy(dtype=np.float32))
    n_comp = min(50, values.shape[0] - 1, values.shape[1])
    pcs = PCA(n_components=n_comp, random_state=TSNE_RANDOM_STATE).fit_transform(values)
    return TSNE(
        n_components=2,
        init="pca",
        perplexity=30,
        random_state=TSNE_RANDOM_STATE,
    ).fit_transform(pcs)


def _subsample(exp: pd.DataFrame) -> pd.DataFrame:
    """Deterministically subsample rows to at most TSNE_MAX_POINTS."""
    if len(exp) <= TSNE_MAX_POINTS:
        return exp
    rng = np.random.default_rng(TSNE_RANDOM_STATE)
    keep = rng.choice(len(exp), size=TSNE_MAX_POINTS, replace=False)
    return exp.iloc[np.sort(keep)]


def _biology_labels(ann: pd.DataFrame, index: pd.Index) -> pd.Series:
    """Collapse annotation into DLBCL / FL / Normal / Other.

    Uses EXACT diagnosis names plus the TUMOR_NORMAL flag, never substring
    matching. Substring rules are actively dangerous here: the literal value is
    "Diffuse_Large_B_Cell_Lymphoma", so a test for "_b_" (intended to catch
    normal B cells) silently reclassifies all 4,466 DLBCL samples as normal.

    Major_group is deliberately not used: it mixes disease names with cohort
    sources (Normal_B_cells, Kassandra) for the normal samples, so it is not a clean
    biological grouping.

    Precedence: explicit disease diagnosis, then the TUMOR_NORMAL flag, then
    Other. Rare tumour subtypes (Burkitt, high-grade, double-hit, marginal zone,
    mantle cell, CLL) fall into Other by design.
    """
    sub = ann.reindex(index)
    diag = sub["Diagnosis_cell_type_unified"].astype(str)
    tumor_normal = (
        sub["TUMOR_NORMAL"].astype(str)
        if "TUMOR_NORMAL" in sub.columns
        else pd.Series("Tumor", index=index)
    )

    labels = pd.Series("Other", index=index, dtype=object)
    labels[tumor_normal.eq("Normal")] = "Normal"
    labels[diag.eq("Follicular_Lymphoma")] = "FL"
    labels[diag.eq("Diffuse_Large_B_Cell_Lymphoma")] = "DLBCL"
    return labels


def _cache_panel(
    name: str,
    coords: np.ndarray,
    ann: pd.DataFrame,
    index: pd.Index,
) -> None:
    """Cache embedding coordinates and the annotation columns needed to colour them.

    The embedding is the expensive part (a ~700 MB download plus PCA and t-SNE);
    the colouring is nearly free. Caching lets a palette or label-mapping fix be
    re-rendered with `--recolor` instead of re-downloading ~2.9 GB.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    sub = ann.reindex(index)
    np.savez_compressed(
        CACHE_DIR / f"{name}.npz",
        coords=coords,
        diagnosis=sub["Diagnosis_cell_type_unified"].astype(str).to_numpy(),
        tumor_normal=(
            sub["TUMOR_NORMAL"].astype(str).to_numpy()
            if "TUMOR_NORMAL" in sub.columns
            else np.array(["Tumor"] * len(sub))
        ),
        rna_batch=(
            sub["RNA_BATCH"].astype(str).to_numpy()
            if "RNA_BATCH" in sub.columns
            else np.array(["unknown"] * len(sub))
        ),
        sample_ids=np.asarray(index, dtype=str),
    )


def _load_panel_cache(name: str) -> tuple[np.ndarray, pd.DataFrame] | None:
    """Return (coords, annotation-like frame) from cache, or None if absent."""
    path = CACHE_DIR / f"{name}.npz"
    if not path.exists():
        return None
    # allow_pickle=True is required because the cached label columns are numpy
    # object arrays. Safe here: these files are written by _cache_panel in this
    # same module, never received from elsewhere.
    data = np.load(path, allow_pickle=True)
    index = pd.Index(data["sample_ids"])
    ann = pd.DataFrame(
        {
            "Diagnosis_cell_type_unified": data["diagnosis"],
            "TUMOR_NORMAL": data["tumor_normal"],
            "RNA_BATCH": data["rna_batch"],
        },
        index=index,
    )
    return data["coords"], ann


def draw_scatter(
    ax: plt.Axes,
    coords: np.ndarray,
    colors: list[str],
    s: float = 1.6,
    equal_aspect: bool = True,
) -> None:
    """Draw one axis-free embedding into an existing axes.

    Shared by the standalone PNG assets and by the composed PDF variants, so a
    point cloud looks identical wherever it appears.
    """
    ax.scatter(coords[:, 0], coords[:, 1], s=s, c=colors, linewidths=0, alpha=0.85)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(0.6)
        spine.set_edgecolor("#333333")
    if equal_aspect:
        ax.set_aspect("equal")


def draw_biology_scatter(
    ax: plt.Axes,
    coords: np.ndarray,
    labels: pd.Series,
    s: float = 1.6,
    equal_aspect: bool = True,
) -> None:
    """Draw a diagnosis-coloured embedding using one marker shape per group.

    NAR 6.7 forbids relying on colour alone. Colour still carries the grouping
    (temperature-split palette), but each group also gets its own marker, so the
    panel survives greyscale printing and the common colour-vision deficiencies.
    """
    for group, marker in BIOLOGY_MARKERS.items():
        mask = (labels == group).to_numpy()
        if not mask.any():
            continue
        ax.scatter(
            coords[mask, 0], coords[mask, 1],
            s=s, c=BIOLOGY_COLORS[group], marker=marker,
            linewidths=0, alpha=0.85,
        )
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(0.6)
        spine.set_edgecolor("#333333")
    if equal_aspect:
        ax.set_aspect("equal")


def _scatter_panel(
    coords: np.ndarray,
    colors: list[str],
    out_name: str,
    px: int = 900,
) -> None:
    """Render one square, axis-free embedding panel."""
    fig, ax = plt.subplots(figsize=(3, 3))
    draw_scatter(ax, coords, colors)
    fig.tight_layout(pad=0.05)
    _save_raster_asset(fig, out_name, px=px)


# ── Variant A ─────────────────────────────────────────────────────────────────

def draw_benchmark_mosaic(
    ax: plt.Axes,
    scores: pd.Series,
    highlight_ids: list[str] | None = None,
    n_cols: int = 47,
    n_rows: int = 48,
    edge_lw: float = 0.25,
    highlight_lw: float = 1.1,
    verbose: bool = True,
) -> None:
    """Draw the attempt mosaic into an existing axes. See make_benchmark_mosaic."""
    n_cells = n_cols * n_rows
    assert n_cells >= len(scores), f"grid {n_cols}x{n_rows} too small for {len(scores)}"

    cmap = plt.get_cmap("Blues")
    norm = plt.Normalize(vmin=float(scores.min()), vmax=float(scores.max()))
    values = scores.to_numpy()

    highlight_ids = highlight_ids or []
    positions = {run_id: i for i, run_id in enumerate(scores.index)}

    rects, colors = [], []
    for i, value in enumerate(values):
        row, col = divmod(i, n_cols)
        rects.append(Rectangle((col, n_rows - 1 - row), 1.0, 1.0))
        colors.append(cmap(norm(value)))

    ax.add_collection(PatchCollection(
        rects, facecolors=colors, edgecolors="white", linewidths=edge_lw,
    ))

    for run_id in highlight_ids:
        if run_id not in positions:
            print(f"  mosaic: WARNING highlight id absent from scores: {run_id}")
            continue
        row, col = divmod(positions[run_id], n_cols)
        ax.add_patch(Rectangle(
            (col, n_rows - 1 - row), 1.0, 1.0,
            facecolor="none", edgecolor="#1A1A1A", linewidth=highlight_lw, zorder=5,
        ))
        if verbose:
            print(f"  mosaic: highlighted rank {positions[run_id] + 1:>5}  {run_id}")

    ax.set_xlim(0, n_cols)
    ax.set_ylim(0, n_rows)
    ax.set_aspect("equal")
    ax.axis("off")
    if verbose:
        print(
            f"  mosaic: {len(scores)} tiles in {n_cols}x{n_rows} grid "
            f"({n_cells - len(scores)} cells empty), "
            f"score range {scores.min():.4f}-{scores.max():.4f}"
        )


def make_benchmark_mosaic(
    scores: pd.Series,
    highlight_ids: list[str] | None = None,
    n_cols: int = 47,
    n_rows: int = 48,
) -> None:
    """Draw one tile per harmonization attempt, ordered best to worst.

    Tiles are filled left to right, top to bottom in descending composite score,
    so the visual gradient IS the score distribution. Any other ordering (by
    method, by strategy) would imply structure a reader could misread, and would
    have to be stated in the caption.

    Tiles carry thin white edges. Without them the mosaic renders as a smooth
    gradient, because the composite distribution is continuous (0.34-0.66, with
    only 0.036 between rank 1 and rank 50) -- there is NO elite cluster. The
    edges are what make 2,234 discrete attempts legible as discrete. The figure
    must NOT be captioned as "a few attempts score well and most score poorly";
    the honest reading is a narrow continuum with no standout winner, which is
    itself the paper's point.

    `highlight_ids` are outlined in dark ink, marking where the recommended
    approaches sit in the global ranking. They are deliberately not at the top:
    composite score aggregates 87 global metrics, while the decision tree is
    driven by local biology preservation.

    47 x 48 = 2,256 cells hold 2,234 attempts; the 22 trailing cells are left
    empty rather than distorting the grid.

    Drawn as explicit Rectangle patches, NOT imshow. imshow embeds a raster of
    the grid's native size (47x48 px), which at the final printed width of
    ~35 mm is about 34 dpi -- far below the 300/600 dpi NAR 6.3 requires. Real
    vector rectangles are resolution-independent instead.
    """
    fig, ax = plt.subplots(figsize=(4.7, 4.8))
    draw_benchmark_mosaic(ax, scores, highlight_ids, n_cols, n_rows)
    fig.tight_layout(pad=0.02)
    _save_vector_asset(fig, "ga_benchmark_mosaic")


def platform_stack_fractions() -> tuple[dict[str, float], dict[str, float]]:
    """Return (true, drawn) platform fractions after the visibility floor.

    Lifts any band below MIN_BAND_FRACTION, then shrinks the others
    proportionally so the column still sums to 1.

    Returns
    -------
    tuple[dict, dict]
        True fractions and the drawn (partly exaggerated) fractions.
    """
    total = sum(PLATFORM_COUNTS.values())
    true_fracs = {k: v / total for k, v in PLATFORM_COUNTS.items()}

    lifted = {k: max(v, MIN_BAND_FRACTION) for k, v in true_fracs.items()}
    excess = sum(lifted.values()) - 1.0
    donors = {k: v for k, v in lifted.items() if v > MIN_BAND_FRACTION}
    donor_total = sum(donors.values())
    drawn = {
        k: (v - excess * v / donor_total if k in donors else v)
        for k, v in lifted.items()
    }
    return true_fracs, drawn


def report_platform_distortion(
    true_fracs: dict[str, float], drawn: dict[str, float]
) -> None:
    """Print the exaggeration applied to each band, for caption disclosure."""
    for name in PLATFORM_COUNTS:
        print(
            f"  stack: {name:<20} true {true_fracs[name]*100:5.2f}%  "
            f"drawn {drawn[name]*100:5.2f}%"
            + ("   <-- EXAGGERATED, disclose in caption"
               if drawn[name] > true_fracs[name] + 1e-9 else "")
        )


def draw_platform_stack(ax: plt.Axes, lw: float = 1.2) -> dict[str, float]:
    """Draw the four platform bands into an existing axes; return drawn fractions."""
    _, fracs = platform_stack_fractions()
    bottom = 0.0
    for name, frac in fracs.items():
        ax.bar(
            0, frac, bottom=bottom, width=0.8,
            color=PLATFORM_COLORS[name], edgecolor="white", linewidth=lw,
        )
        bottom += frac
    ax.set_xlim(-0.5, 0.5)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fracs


def make_platform_stack() -> None:
    """Draw the four platform bands, heights proportional to sample counts.

    Enforces MIN_BAND_FRACTION so Agilent (0.89% of samples) stays visible at
    final print size. This exaggerates the smallest band; the applied distortion
    is printed so it can be disclosed in the caption and alt text.
    """
    fig, ax = plt.subplots(figsize=(1.6, 2.0))
    fracs = draw_platform_stack(ax)
    fig.tight_layout(pad=0.02)
    _save_vector_asset(fig, "ga_platform_stack")
    true_fracs, _ = platform_stack_fractions()
    report_platform_distortion(true_fracs, fracs)


def load_cached_panel(name: str) -> tuple[np.ndarray, pd.DataFrame]:
    """Return (coords, annotation) for an already-cached panel.

    Raises rather than silently re-downloading: the composer must never trigger
    a ~700 MB S3 fetch as a side effect of drawing a PDF. Run
    `python graphical_abstract_assets.py --slow` to populate the cache.
    """
    cached = _load_panel_cache(name)
    if cached is None:
        raise FileNotFoundError(
            f"no cached embedding for {name!r} at {CACHE_DIR / (name + '.npz')}; "
            "run `python graphical_abstract_assets.py --slow` first"
        )
    return cached


def biology_labels(ann: pd.DataFrame, index: pd.Index) -> pd.Series:
    """Public wrapper for the DLBCL / FL / Normal / Other collapse."""
    return _biology_labels(ann, index)


def load_composite_scores() -> pd.Series:
    """Public wrapper for the composite score series (best first)."""
    return _load_composite_scores()


def _coords_and_annotation(
    name: str, strat: str, imp: str, method: str, post_rm: int
) -> tuple[np.ndarray, pd.DataFrame, pd.Index]:
    """Return (coords, annotation, index) for one panel, using the cache if present."""
    cached = _load_panel_cache(name)
    if cached is not None:
        coords, ann = cached
        print(f"  {name}: using cached embedding ({len(ann)} points)")
        return coords, ann, ann.index

    print(f"  {name}: downloading {strat}__{imp}__{method}__post{post_rm}")
    exp = _subsample(_download_matrix(strat, imp, method, post_rm))
    ann = _download_annotation(strat, imp)
    coords = _embed(exp)
    _cache_panel(name, coords, ann, exp.index)
    return coords, ann.reindex(exp.index), exp.index


def make_verdict_tsnes() -> None:
    """Render the four Variant A verdict thumbnails, coloured by biology."""
    for label, strat, imp, method, post_rm in VERDICT_PANELS:
        name = f"ga_tsne_{label}"
        coords, ann, index = _coords_and_annotation(name, strat, imp, method, post_rm)
        bio = _biology_labels(ann, index)
        _scatter_panel(coords, [BIOLOGY_COLORS[b] for b in bio], name, px=900)
        print(f"  {name}: groups {bio.value_counts().to_dict()}")


# ── Variant B ─────────────────────────────────────────────────────────────────

def strip_stage_name(idx: int, label: str) -> str:
    """Canonical cache/asset basename for one Variant B stage."""
    return f"ga_strip_stage{idx}_{label}"


def strip_stage_colors(
    idx: int, ann: pd.DataFrame, index: pd.Index
) -> tuple[list, str, pd.Series | None]:
    """Colour one Variant B stage by batch or by biology.

    Stages 1-3 are coloured by RNA_BATCH (the batch structure being removed),
    stages 4-5 by collapsed diagnosis (the biology being revealed). Stage 3 is
    the transition and stays batch-coloured, so the handover happens exactly
    where harmonization does.

    Returns
    -------
    tuple
        (per-point colours, human-readable scheme description, biology labels or
        None). Biology labels are returned so the caller can draw the panel with
        one marker shape per group (NAR 6.7).
    """
    if idx <= 3:
        codes = pd.Categorical(ann["RNA_BATCH"].astype(str)).codes
        batch_cmap = plt.get_cmap("tab20")
        return (
            [batch_cmap(c % 20) for c in codes],
            f"batch ({len(set(codes))} batches)",
            None,
        )
    bio = _biology_labels(ann, index)
    return (
        [BIOLOGY_COLORS[b] for b in bio],
        f"biology {bio.value_counts().to_dict()}",
        bio,
    )


def make_strip_stages() -> None:
    """Render the five Variant B pipeline stages.

    Colour shifts across the strip: stages 1-3 are coloured by RNA_BATCH (the
    batch structure being removed), stages 4-5 by collapsed diagnosis (the
    biology being revealed).
    """
    for idx, label, strat, imp, method, post_rm in STRIP_STAGES:
        name = strip_stage_name(idx, label)
        coords, ann, index = _coords_and_annotation(name, strat, imp, method, post_rm)
        colors, scheme, _ = strip_stage_colors(idx, ann, index)
        _scatter_panel(coords, colors, name, px=900)
        print(f"  {name}: {len(coords)} points, coloured by {scheme}")


# ── Variant C ─────────────────────────────────────────────────────────────────

def fan_sector_angles() -> list[tuple[str, int, str, float, float, float]]:
    """Return per-sector geometry for the decision fan.

    Angular width is proportional to the subset's sample count, except that any
    sector narrower than MIN_SECTOR_DEG is lifted to that floor and the others
    are shrunk proportionally. Without the floor "Mixed platforms" is a 7.2 deg
    sliver that no label can sit in.

    Returns
    -------
    list of tuple
        (name, count, method, true_span_deg, drawn_span_deg, mid_angle_deg),
        sweeping from 180 deg (left) down to 0 deg (right).
    """
    total = sum(count for _, count, _ in FAN_SECTORS)
    true_spans = [180.0 * count / total for _, count, _ in FAN_SECTORS]

    lifted = [max(s, MIN_SECTOR_DEG) for s in true_spans]
    excess = sum(lifted) - 180.0
    donor_total = sum(s for s in lifted if s > MIN_SECTOR_DEG)
    drawn = [
        (s - excess * s / donor_total if s > MIN_SECTOR_DEG else s) for s in lifted
    ]

    out, start = [], 180.0
    for (name, count, method), true_span, span in zip(FAN_SECTORS, true_spans, drawn):
        out.append((name, count, method, true_span, span, start - span / 2.0))
        start -= span
    return out


def draw_decision_fan(
    ax: plt.Axes, lw: float = 1.5, verbose: bool = True
) -> list[tuple[str, int, str, float, float, float]]:
    """Draw the two-ring semicircular fan into an existing axes.

    Axes data coordinates are the unit semicircle: centre (0, 0), outer radius
    1.0, so callers can place labels with the returned mid-angles.

    Radii are set by FAN_R_HOLE / FAN_R_SPLIT rather than the obvious 0.30/0.60
    for two reasons found while composing the page: the hole must clear the
    two-line "7,174 samples" label at 14 pt, and the sector label has to sit
    wholly inside the outer band -- straddling the white split line makes the
    type look misaligned with the artwork.
    """
    sector_colors = list(PLATFORM_COLORS.values())
    sectors = fan_sector_angles()
    start = 180.0
    for i, (name, count, method, true_span, span, _) in enumerate(sectors):
        color = sector_colors[i % len(sector_colors)]
        # inner band: the data subset, saturated
        ax.add_patch(Wedge(
            (0, 0), FAN_R_SPLIT, start - span, start, width=FAN_R_SPLIT - FAN_R_HOLE,
            facecolor=color, edgecolor="white", linewidth=lw,
        ))
        # outer band: the winning method, same hue lightened; carries the label
        ax.add_patch(Wedge(
            (0, 0), 1.00, start - span, start, width=1.00 - FAN_R_SPLIT,
            facecolor=color, alpha=0.45, edgecolor="white", linewidth=lw,
        ))
        start -= span
        if verbose:
            print(
                f"  fan: {name:<18} {count:>5} samples -> true {true_span:5.1f} deg,"
                f" drawn {span:5.1f} deg  ({method})"
                + ("   <-- WIDENED, disclose in caption"
                   if span > true_span + 1e-9 else "")
            )

    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.set_aspect("equal")
    ax.axis("off")
    return sectors


def make_decision_fan() -> None:
    """Draw the semicircular decision fan, sector angles from subset sizes.

    Two concentric rings: inner = data subset, outer = winning method. Sector
    angular width is proportional to that subset's sample count, so the geometry
    carries dataset composition. All labels are added by the composer, not here.
    """
    fig, ax = plt.subplots(figsize=(5.0, 2.5))
    draw_decision_fan(ax)
    fig.tight_layout(pad=0.02)
    _save_vector_asset(fig, "ga_decision_fan")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fast", action="store_true",
                        help="only the assets that need no S3 download")
    parser.add_argument("--slow", action="store_true",
                        help="only the embedding assets (downloads ~2.9 GB)")
    args = parser.parse_args()
    do_fast = args.fast or not args.slow
    do_slow = args.slow or not args.fast

    if do_fast:
        print("[fast] composite scores")
        scores = _load_composite_scores()
        print("[fast] Variant A mosaic")
        verdict_ids = [
            f"{strat}__{imp}__{method}__post{post_rm}"
            for _, strat, imp, method, post_rm in VERDICT_PANELS
        ]
        make_benchmark_mosaic(scores, highlight_ids=verdict_ids)
        print("[fast] Variant A platform stack")
        make_platform_stack()
        print("[fast] Variant C decision fan")
        make_decision_fan()

    if do_slow:
        print("[slow] Variant A verdict thumbnails")
        make_verdict_tsnes()
        print("[slow] Variant B strip stages")
        make_strip_stages()

    print(f"\ndone -> {OUT_DIR.resolve()}")
    for path in sorted(OUT_DIR.glob("*")):
        print(f"  {path.name:<40} {path.stat().st_size/1024:8.1f} kB")


if __name__ == "__main__":
    main()
