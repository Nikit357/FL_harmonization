"""
fig10_metric_star_visualization.py

Standalone script: ray-star (radar) plot showing how the Best 15 harmonization
approaches compare to the overall benchmark on each metric group.

Each ray = one metric group (A–K or as defined in col_meta).
Ray length ∝ mean superiority of Best 15 over all attempts:
    superiority_group = mean_normed_Best15 - mean_normed_all

Saves: figures/fig10_metric_star_best15.svg and .png
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import sys

# ── Environment setup ──────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.resolve()))
import figures_helpers as fh

matplotlib.rcParams["pdf.fonttype"] = "truetype"
matplotlib.rcParams["svg.fonttype"] = "none"
matplotlib.rcParams["figure.dpi"] = 200

FIGURES_DIR = Path("figures")
FIGURES_DIR.mkdir(exist_ok=True)

GLOBAL_FONT_SIZE = 10
BEST_COLOR = "#E63946"

METRICS_CSV_PATH = (
    Path(__file__).parent.parent.parent
    / "harmonization-metrics"
    / "metric_tables"
    / "metrics_comprehensive_260609.csv"
)

# ── Best 15 run identifiers ────────────────────────────────────────────────────
TOP_IDS = [
    ("10_mnn",      "strict",     "S0_no_removal"),
    ("10_mnn",      "strict",     "H_affymetrix_extended"),
    ("10_mnn",      "strict",     "D_malignant_only"),
    ("04_sva",      "knn",        "C_rnaseq_only"),
    ("04_sva",      "softimpute", "C_rnaseq_only"),
    ("16_fsqn_r",   "knn",        "C_rnaseq_only"),
    ("16_fsqn_r",   "softimpute", "C_rnaseq_only"),
    ("16_fsqn_r",   "strict",     "C_rnaseq_only"),
    ("10_mnn",      "strict",     "J_ff_only"),
    ("16_fsqn_r",   "strict",     "J_ff_only"),
    ("04_sva",      "knn",        "K_ffpe_only"),
    ("04_sva",      "strict",     "K_ffpe_only"),
    ("04_sva",      "softimpute", "K_ffpe_only"),
    ("13_fsmvn",    "strict",     "S0_no_removal"),
    ("33_amdbnorm", "strict",     "S0_no_removal"),
]

BEST_LABEL = "Best"


def _radar_frame(ax: plt.Axes, num_vars: int, color: str = "gray") -> None:
    """Draw concentric polygon grid lines for the radar plot."""
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]  # close polygon
    for level in [0.25, 0.5, 0.75, 1.0]:
        vals = [level] * num_vars + [level]
        ax.plot(angles, vals, color=color, linewidth=0.5, linestyle="--", alpha=0.6)
    ax.set_xticks([])
    ax.set_yticks([])


def build_superiority_by_group(
    df_ok: pd.DataFrame,
    df_normed: pd.DataFrame,
    scoring_cols: list,
    col_meta: pd.DataFrame,
    df_best: pd.DataFrame,
) -> pd.Series:
    """
    Compute per-group mean superiority of Best 15 over all attempts.

    Parameters
    ----------
    df_ok : DataFrame of all validated runs
    df_normed : polarity-normalized [0,1] scores aligned to df_ok
    scoring_cols : columns with nonzero polarity (85 metrics)
    col_meta : DataFrame with 'col' and 'group' columns
    df_best : DataFrame of Best 15 rows (subset of df_ok)

    Returns
    -------
    pd.Series : group → superiority (mean_best15 - mean_all), clipped ≥ 0
    """
    group_sup: dict = {}
    for grp, grp_cols in col_meta.groupby("group").apply(lambda x: x.index.tolist()).items():
        valid_cols = [c for c in grp_cols if c in scoring_cols]
        if not valid_cols:
            continue
        mean_all = df_normed[valid_cols].mean().mean()
        mean_best = df_normed.loc[df_best.index, valid_cols].mean().mean()
        group_sup[grp] = float(np.clip(mean_best - mean_all, 0, None))
    return pd.Series(group_sup).sort_index()


def draw_radar_star(
    ax: plt.Axes,
    superiority: pd.Series,
    title: str = "Best 15 superiority by metric group",
) -> None:
    """
    Draw a radar/star plot on ax.

    Parameters
    ----------
    superiority : per-group mean superiority values (already clipped ≥ 0)
    """
    groups = superiority.index.tolist()
    values = superiority.values.tolist()
    num_vars = len(groups)

    if num_vars < 3:
        ax.text(0.5, 0.5, "Too few metric groups for radar",
                ha="center", va="center", transform=ax.transAxes)
        return

    # Normalize rays to [0, 1] for display
    _max_val = max(values) if max(values) > 0 else 1.0
    values_norm = [v / _max_val for v in values]

    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    values_plot = values_norm + values_norm[:1]
    angles_plot = angles + angles[:1]

    ax = plt.subplot(ax.get_subplotspec(), projection="polar")
    _radar_frame(ax, num_vars, color="#999999")

    # Fill the star polygon
    ax.fill(angles_plot, values_plot, color=BEST_COLOR, alpha=0.35)
    ax.plot(angles_plot, values_plot, color=BEST_COLOR, linewidth=2.0)
    ax.scatter(angles, values_norm, s=55, color=BEST_COLOR, zorder=5)

    # Labels with actual superiority values
    ax.set_xticks(angles)
    ax.set_xticklabels(
        [f"{g}\n+{v:.3f}" for g, v in zip(groups, values)],
        fontsize=GLOBAL_FONT_SIZE - 1,
    )
    ax.set_yticks([0.25, 0.50, 0.75, 1.0])
    ax.set_yticklabels(
        [f"{v * _max_val:.3f}" for v in [0.25, 0.50, 0.75, 1.0]],
        fontsize=GLOBAL_FONT_SIZE - 2, color="#555555",
    )
    ax.set_ylim(0, 1.05)
    ax.set_title(title, fontsize=GLOBAL_FONT_SIZE, pad=16)


def main() -> None:
    print(f"Loading metrics from {METRICS_CSV_PATH} …")
    df_ok, df_normed, scoring_cols, col_meta = fh.load_metrics_data(METRICS_CSV_PATH)
    df_best, _, _ = fh.build_best_vs_rest(df_ok, TOP_IDS, BEST_LABEL, BEST_COLOR)

    print(f"  df_ok: {df_ok.shape} | df_best: {df_best.shape}")
    print(f"  scoring_cols: {len(scoring_cols)} | groups: {col_meta['group'].unique().tolist()}")

    superiority = build_superiority_by_group(df_ok, df_normed, scoring_cols, col_meta, df_best)
    print(f"  Superiority per group:\n{superiority.to_string()}")

    # ── Figure layout ──────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(10, 8))
    gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.4)
    ax_radar = fig.add_subplot(gs[0, 0])  # will be replaced by polar projection inside
    ax_bar = fig.add_subplot(gs[0, 1])    # horizontal bar for exact values

    # Radar star (polar)
    draw_radar_star(ax_radar, superiority, title="Best 15 superiority by metric group")

    # Horizontal bar (reference, exact values)
    _sup_sorted = superiority.sort_values(ascending=True)
    _colors_bar = [BEST_COLOR if v > 0.01 else "#CCCCCC" for v in _sup_sorted.values]
    ax_bar.barh(_sup_sorted.index, _sup_sorted.values, color=_colors_bar, height=0.7)
    for i, (grp, val) in enumerate(_sup_sorted.items()):
        ax_bar.text(val + 0.001, i, f"+{val:.4f}", va="center",
                    fontsize=GLOBAL_FONT_SIZE - 1)
    ax_bar.set_xlabel(
        "Mean superiority (Best 15 − all attempts, normalized 0–1)",
        fontsize=GLOBAL_FONT_SIZE,
    )
    ax_bar.set_title(
        "Superiority by metric group\n(clipped at 0 — groups where Best 15 outperform overall)",
        fontsize=GLOBAL_FONT_SIZE,
    )
    ax_bar.tick_params(labelsize=GLOBAL_FONT_SIZE - 1)
    import seaborn as sns
    sns.despine(ax=ax_bar)

    fig.suptitle("Fig 10 Supplement: Best 15 Metric Group Superiority Star",
                 fontsize=GLOBAL_FONT_SIZE + 1)
    plt.tight_layout()

    _svg_path = FIGURES_DIR / "fig10_metric_star_best15.svg"
    _png_path = FIGURES_DIR / "fig10_metric_star_best15.png"
    fig.savefig(_svg_path, bbox_inches="tight")
    fig.savefig(_png_path, bbox_inches="tight", dpi=200)
    plt.close()
    print(f"Saved:\n  {_svg_path}\n  {_png_path}")


if __name__ == "__main__":
    main()
