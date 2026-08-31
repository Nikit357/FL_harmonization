"""
test_mock_gene_structure.py — Smoke tests for gene_panel_structure.py.

Synthetic data only: no S3 access, no expression download, runs in seconds. Mirrors
the style of ../test_mock_metrics.py — plain asserts, a printed pass/fail line per
check, and a non-zero exit code if anything fails.

    python test_mock_gene_structure.py
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from gene_panel_structure import (  # noqa: E402
    FISHER_CLIP,
    MIN_COHORT_N,
    fisher_z,
    gene_expression_qc,
    gene_gene_correlation,
    gene_gene_correlation_within_cohort,
    inverse_fisher_z,
    pack_upper_triangle,
    unpack_upper_triangle,
)

RNG = np.random.default_rng(260827)

_n_pass = 0
_n_fail = 0


def check(name: str, fn) -> None:
    """Run one assertion block and report it without aborting the whole run."""
    global _n_pass, _n_fail
    try:
        fn()
    except Exception:
        _n_fail += 1
        print(f"FAIL  {name}")
        print(traceback.format_exc())
    else:
        _n_pass += 1
        print(f"ok    {name}")


# ── Fixtures ──────────────────────────────────────────────────────────────────


def make_dataset(
    n_per_cohort: int = 40, n_cohorts: int = 4, cohort_offset: float = 5.0
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Synthetic matrix with a known structure.

    Genes:
      G_A, G_B    perfectly co-expressed, globally and within every cohort
      G_BATCHY    independent noise plus the cohort offset — correlated with G_A
                  globally, uncorrelated with it inside any cohort
      G_SHIFT     flat within a cohort but offset between cohorts (pure batch effect)
      G_NOISE     independent noise, no cohort offset
      G_ZERO      all zeros
      G_LOW       always below the low-expression threshold
    The cohort offset is what makes the global and within-cohort correlation flavours
    disagree, which is the property the two-flavour design exists to capture.
    """
    frames = []
    labels = []
    for c in range(n_cohorts):
        base = RNG.normal(8.0, 1.0, n_per_cohort)
        offset = c * cohort_offset
        g_a = base + offset
        frames.append(
            pd.DataFrame(
                {
                    "G_A": g_a,
                    "G_B": 2.0 * g_a + 1.0,
                    "G_BATCHY": RNG.normal(6.0, 1.0, n_per_cohort) + offset,
                    "G_SHIFT": np.full(n_per_cohort, 3.0 + offset)
                    + RNG.normal(0, 1e-6, n_per_cohort),
                    "G_NOISE": RNG.normal(6.0, 1.0, n_per_cohort),
                    "G_ZERO": np.zeros(n_per_cohort),
                    "G_LOW": RNG.uniform(0.0, 0.5, n_per_cohort),
                }
            )
        )
        labels.extend([f"COHORT_{c}"] * n_per_cohort)

    exp_df = pd.concat(frames, ignore_index=True)
    exp_df.index = [f"S{i:04d}" for i in range(len(exp_df))]
    ann_df = pd.DataFrame({"COHORT_LABEL": labels}, index=exp_df.index)
    return exp_df, ann_df


GENES = ["G_A", "G_B", "G_BATCHY", "G_SHIFT", "G_NOISE", "G_ZERO", "G_LOW"]


# ── 1. Correlation of perfectly co-expressed genes ────────────────────────────


def test_perfect_correlation() -> None:
    exp_df, _ = make_dataset()
    mat, order = gene_gene_correlation(exp_df, ["G_A", "G_B"])
    assert order == ["G_A", "G_B"], order
    assert mat.shape == (2, 2)
    assert np.isclose(mat[0, 1], 1.0, atol=1e-9), mat[0, 1]
    assert np.isclose(mat[0, 0], 1.0)


# ── 2. Global and within-cohort flavours must differ ──────────────────────────


def test_within_vs_global() -> None:
    exp_df, ann_df = make_dataset()
    pair = ["G_A", "G_BATCHY"]

    global_mat, _ = gene_gene_correlation(exp_df, pair)
    within_mat, counts, order = gene_gene_correlation_within_cohort(
        exp_df, ann_df, pair
    )
    assert order == pair

    # The shared cohort offset creates a strong global correlation between two genes
    # that are independent inside every cohort.
    assert abs(global_mat[0, 1]) > 0.5, global_mat[0, 1]
    assert abs(within_mat[0, 1]) < 0.3, within_mat[0, 1]
    assert counts[0, 1] == 4, counts[0, 1]


def test_within_cohort_perfect_pair() -> None:
    exp_df, ann_df = make_dataset()
    mat, counts, _ = gene_gene_correlation_within_cohort(exp_df, ann_df, ["G_A", "G_B"])
    assert np.isclose(mat[0, 1], 1.0, atol=1e-6), mat[0, 1]
    assert counts[0, 1] == 4


# ── 3. Small cohorts are excluded at MIN_COHORT_N ─────────────────────────────


def test_min_cohort_n_exclusion() -> None:
    assert MIN_COHORT_N == 20, MIN_COHORT_N
    exp_df, ann_df = make_dataset(n_per_cohort=40, n_cohorts=2)

    # Shrink one cohort below the threshold; it must stop contributing.
    small = ann_df["COHORT_LABEL"] == "COHORT_1"
    drop_idx = ann_df.index[small][MIN_COHORT_N - 1 :]
    exp_small = exp_df.drop(index=drop_idx)
    ann_small = ann_df.drop(index=drop_idx)

    _, counts_full, _ = gene_gene_correlation_within_cohort(
        exp_df, ann_df, ["G_A", "G_B"]
    )
    _, counts_small, _ = gene_gene_correlation_within_cohort(
        exp_small, ann_small, ["G_A", "G_B"]
    )
    assert counts_full[0, 1] == 2, counts_full[0, 1]
    assert counts_small[0, 1] == 1, counts_small[0, 1]


# ── 4. A gene constant inside a cohort drops out of that cohort only ──────────


def test_constant_gene_partial_contribution() -> None:
    exp_df, ann_df = make_dataset()
    # G_SHIFT is (numerically) constant within each cohort, so no pair involving it
    # can be estimated anywhere, while G_A/G_B keep their full count.
    _, counts, order = gene_gene_correlation_within_cohort(exp_df, ann_df, GENES)
    i_a, i_b = order.index("G_A"), order.index("G_B")
    i_zero = order.index("G_ZERO")
    assert counts[i_a, i_b] == 4, counts[i_a, i_b]
    assert counts[i_a, i_zero] == 0, counts[i_a, i_zero]


# ── 5. Upper-triangle packing round trip ──────────────────────────────────────


def test_pack_unpack_round_trip() -> None:
    n = 12
    base = RNG.normal(size=(n, n))
    sym = np.clip((base + base.T) / 2.0, -1.0, 1.0)
    np.fill_diagonal(sym, 1.0)

    packed = pack_upper_triangle(sym)
    assert packed.dtype == np.float16
    assert packed.shape == (n * (n - 1) // 2,)

    restored = unpack_upper_triangle(packed, n)
    assert restored.shape == (n, n)
    assert np.allclose(restored, restored.T)
    assert np.allclose(np.diag(restored), 1.0)
    assert np.max(np.abs(restored - sym)) < 1e-3, np.max(np.abs(restored - sym))


# ── 6. Fisher transform ───────────────────────────────────────────────────────


def test_fisher_round_trip() -> None:
    r = np.array([-0.9, -0.5, 0.0, 0.25, 0.75])
    assert np.allclose(inverse_fisher_z(fisher_z(r)), r, atol=1e-8)


def test_fisher_clips_unit_correlation() -> None:
    z = fisher_z(np.array([1.0, -1.0]))
    assert np.all(np.isfinite(z)), z
    assert np.isclose(z[0], np.arctanh(FISHER_CLIP))
    assert np.isclose(inverse_fisher_z(z)[0], 1.0, atol=1e-5)


# ── 7. Expression QC ──────────────────────────────────────────────────────────


def test_qc_all_zero_gene() -> None:
    exp_df, ann_df = make_dataset()
    qc = gene_expression_qc(exp_df, ann_df, GENES).set_index("gene")

    assert np.isclose(qc.loc["G_ZERO", "zero_frac"], 1.0)
    assert np.isclose(qc.loc["G_ZERO", "frac_lt_1"], 1.0)
    assert np.isclose(qc.loc["G_ZERO", "detection_frac"], 0.0)
    # mean is exactly 0, so CV must be NaN rather than a division error.
    assert np.isnan(qc.loc["G_ZERO", "cv"]), qc.loc["G_ZERO", "cv"]


def test_qc_low_expression_gene() -> None:
    exp_df, ann_df = make_dataset()
    qc = gene_expression_qc(exp_df, ann_df, GENES).set_index("gene")
    assert np.isclose(qc.loc["G_LOW", "frac_lt_1"], 1.0)
    assert np.isclose(qc.loc["G_A", "frac_lt_1"], 0.0)
    assert qc.loc["G_A", "detection_frac"] == 1.0


def test_qc_icc() -> None:
    exp_df, ann_df = make_dataset()
    qc = gene_expression_qc(exp_df, ann_df, GENES).set_index("gene")

    # G_SHIFT is constant within a cohort and different between cohorts: ICC ~ 1.
    assert qc.loc["G_SHIFT", "icc_cohort"] > 0.99, qc.loc["G_SHIFT", "icc_cohort"]
    # G_NOISE has no cohort structure at all: ICC ~ 0.
    assert abs(qc.loc["G_NOISE", "icc_cohort"]) < 0.2, qc.loc["G_NOISE", "icc_cohort"]
    assert (
        qc.loc["G_SHIFT", "var_between_cohort"] > qc.loc["G_SHIFT", "var_within_cohort"]
    )
    assert (
        qc.loc["G_NOISE", "var_between_cohort"] < qc.loc["G_NOISE", "var_within_cohort"]
    )


def test_qc_genorm_ranks_stable_gene_lower() -> None:
    # A deliberately unstable gene (large within-cohort spread) must score a higher
    # geNorm M than a stable one measured against the same reference genes.
    n = 60
    exp_df = pd.DataFrame(
        {
            "REF1": RNG.normal(8.0, 0.05, n),
            "REF2": RNG.normal(7.0, 0.05, n),
            "REF3": RNG.normal(9.0, 0.05, n),
            "STABLE": RNG.normal(8.5, 0.05, n),
            "UNSTABLE": RNG.normal(8.5, 3.0, n),
        }
    )
    exp_df.index = [f"S{i}" for i in range(n)]
    ann_df = pd.DataFrame(
        {"COHORT_LABEL": ["C0"] * 30 + ["C1"] * 30}, index=exp_df.index
    )

    qc = gene_expression_qc(exp_df, ann_df, list(exp_df.columns)).set_index("gene")
    assert qc.loc["UNSTABLE", "genorm_m"] > qc.loc["STABLE", "genorm_m"], (
        qc.loc["UNSTABLE", "genorm_m"],
        qc.loc["STABLE", "genorm_m"],
    )


def test_qc_columns_and_missing_genes() -> None:
    exp_df, ann_df = make_dataset()
    qc = gene_expression_qc(exp_df, ann_df, GENES + ["NOT_PRESENT"])
    assert "NOT_PRESENT" not in set(qc["gene"])
    assert len(qc) == len(GENES)
    assert qc["n_samples"].iloc[0] == len(exp_df)
    assert qc["n_cohorts_used"].iloc[0] == 4


# ── 8. Degenerate inputs ──────────────────────────────────────────────────────


def test_single_gene_panel() -> None:
    exp_df, ann_df = make_dataset()
    mat, order = gene_gene_correlation(exp_df, ["G_A"])
    assert order == ["G_A"] and mat.shape == (1, 1)

    mat_w, counts, order_w = gene_gene_correlation_within_cohort(
        exp_df, ann_df, ["G_A"]
    )
    assert order_w == ["G_A"] and mat_w.shape == (1, 1) and counts.shape == (1, 1)


def test_no_cohort_column() -> None:
    exp_df, _ = make_dataset()
    ann_df = pd.DataFrame(index=exp_df.index)
    mat, counts, _ = gene_gene_correlation_within_cohort(exp_df, ann_df, ["G_A", "G_B"])
    # Everything collapses into one pseudo-cohort, which is large enough to be used.
    assert counts[0, 1] == 1, counts[0, 1]
    assert np.isclose(mat[0, 1], 1.0, atol=1e-6)


def main() -> None:
    print("=" * 72)
    print("gene_panel_structure.py — smoke tests")
    print("=" * 72)

    check("perfect correlation", test_perfect_correlation)
    check("within-cohort differs from global", test_within_vs_global)
    check("within-cohort perfect pair", test_within_cohort_perfect_pair)
    check("MIN_COHORT_N exclusion", test_min_cohort_n_exclusion)
    check("constant gene drops its pairs", test_constant_gene_partial_contribution)
    check("pack/unpack round trip", test_pack_unpack_round_trip)
    check("fisher round trip", test_fisher_round_trip)
    check("fisher clips |r| = 1", test_fisher_clips_unit_correlation)
    check("QC: all-zero gene", test_qc_all_zero_gene)
    check("QC: low-expression gene", test_qc_low_expression_gene)
    check("QC: ICC separates batch-driven genes", test_qc_icc)
    check("QC: geNorm M ranks instability", test_qc_genorm_ranks_stable_gene_lower)
    check("QC: columns and missing genes", test_qc_columns_and_missing_genes)
    check("degenerate: single-gene panel", test_single_gene_panel)
    check("degenerate: no cohort column", test_no_cohort_column)

    print("=" * 72)
    print(f"{_n_pass} passed, {_n_fail} failed")
    sys.exit(1 if _n_fail else 0)


if __name__ == "__main__":
    main()
