"""
Toy checks of revision_lib (plan §8): design maths of λ, Cramér's V, panel clustering,
ground-truth log fold-change concordance, Pareto front, four-score axes, plain-word names
and the docx ledger. Pure Python: runs on JupyterHub and inside both pods.

Tests that need the cached S0 annotation (cache/S0_no_removal__softimpute__ann.tsv.gz) or
the baseline docx are skipped when the file is absent (e.g. inside the pods, where only
the scripts are copied).

Run: python -m pytest tests/test_revision_lib.py -q
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import revision_lib as rl  # noqa: E402

S0_ANN = rl.CACHE_DIR / "S0_no_removal__softimpute__ann.tsv.gz"
BASELINE_DOCX = (
    rl.REVISION_DIR
    / "Revised_manuscript"
    / "FL_harmonization_article_NARGAB_baseline_260912.docx"
)
# Plan §1.1: tokens that must never reach a publication document.
FORBIDDEN = re.compile(
    r"WP\d+|_nocov|rule_front|visual_best|bridging_biology|single_dx|"
    r"L11|\bV1\b|post0|post1|four_score|R1\.\d|R2\.\d|\br\d\d_|nb\d\d_"
)


# ── λ design maths (plan §3.3) ────────────────────────────────────────────────


def test_batch_sizes_match_plan_table():
    counts = {
        "GPL570_FF_Unknown": ({"DLBCL": 282, "FL": 462, "Normal B": 250}, 150, 250),
        "GPL570_Unknown_Unknown": ({"DLBCL": 642, "FL": 266, "Normal B": 25}, 75, 75),
        "GPL96+97_FF_Unknown": ({"DLBCL": 78, "FL": 191, "Normal B": 36}, 108, 108),
        "GPL96_FF_Unknown": ({"DLBCL": 53, "FL": 72, "Normal B": 8}, 24, 24),
        "RNASeq_FF_PolyA": ({"DLBCL": 898, "FL": 16, "Normal B": 125}, 48, 48),
    }
    for batch, (cells, capped, uncapped) in counts.items():
        assigned = rl.GRADIENT_ASSIGNED_DIAGNOSIS[batch]
        assert rl.gradient_batch_size(cells, assigned, 150) == capped
        assert rl.gradient_batch_size(cells, assigned, None) == uncapped


@pytest.mark.parametrize("lam", rl.GRADIENT_LAMBDAS)
@pytest.mark.parametrize("n_b", [24, 48, 75, 108, 150, 250])
def test_cell_targets_sum_and_bounds(lam, n_b):
    targets = rl.gradient_cell_targets(n_b, "FL", lam)
    assert sum(targets.values()) == n_b
    if lam > 0:  # at λ = 0 a remainder sample goes by tie order, not to a(b)
        assert targets["FL"] >= max(targets["DLBCL"], targets["Normal B"])
    if lam == 0:
        assert max(targets.values()) - min(targets.values()) <= 1
    if lam == 1:
        assert targets == {"DLBCL": 0, "FL": n_b, "Normal B": 0}


def test_largest_remainder_is_exact():
    assert rl.largest_remainder_round({"a": 1.5, "b": 1.5, "c": 1.0}, 4) == {
        "a": 2,
        "b": 1,
        "c": 1,
    }


@pytest.mark.skipif(not S0_ANN.exists(), reason="cached S0 annotation not present")
def test_designs_feasible_equal_sizes_and_v_rising():
    ann = pd.read_csv(S0_ANN, sep="\t", index_col=0, low_memory=False)
    expected_v = [
        0,
        0.014,
        0.169,
        0.287,
        0.388,
        0.490,
        0.592,
        0.690,
        0.799,
        0.896,
        0.998,
    ]
    for cap, n_total in ((150, 405), (None, 505)):
        v_values = []
        for lam in rl.GRADIENT_LAMBDAS:
            design = rl.build_gradient_design(ann, lam, 1, cap)
            assert len(design) == n_total and design.index.is_unique
            v_values.append(
                rl.design_confounding(ann, design.index)["cramers_v_major_group"]
            )
        assert np.all(np.diff(v_values) > 0)
        if cap == 150:
            assert np.allclose(v_values, expected_v, atol=0.002)


# ── statistics ────────────────────────────────────────────────────────────────


def test_cramers_v_extremes():
    batches = np.repeat(["b1", "b2", "b3"], 100)
    assert rl.cramers_v(batches, np.tile(["x", "y", "z", "w"], 75)) == pytest.approx(
        0, abs=0.02
    )
    assert rl.cramers_v(batches, batches) > 0.99
    assert np.isnan(rl.cramers_v(batches, ["x"] * 300))


def test_clusters_merge_correlated_metrics():
    rng = np.random.default_rng(0)
    base = rng.normal(size=500)
    table = pd.DataFrame(
        {
            "a": base,
            "b": base + rng.normal(0, 0.05, 500),
            "c": -base + rng.normal(0, 0.05, 500),
            "d": rng.normal(size=500),
        }
    )
    clusters = rl.complete_linkage_clusters(rl.abs_spearman(table), 0.2)
    assert clusters["a"] == clusters["b"] == clusters["c"] != clusters["d"]


def test_pareto_front():
    points = pd.DataFrame({"x": [1, 2, 3, 1, np.nan], "y": [3, 2, 1, 1, 5]})
    assert rl.pareto_front(points, ["x", "y"]).tolist() == [
        True,
        True,
        True,
        False,
        False,
    ]


def test_four_score_axes():
    assert rl.four_score_bar("Distributional", "batch removal") == "global_batch"
    assert rl.four_score_bar("Local", "biology retention") == "local_biology"
    assert rl.four_score_bar("Coverage", "neither") is None
    assert rl.metric_axis("kbet_acceptance_rate_RNA_BATCH", "B", "Local") == (
        "Local",
        "batch removal",
    )


def test_gt_logfc_recovers_signal_and_detects_shrinkage():
    rng = np.random.default_rng(1)
    n_genes, per_cell = 300, 20
    true_fc = rng.normal(0, 1, n_genes)
    rows, labels, batches = [], [], []
    for batch_index, shift in enumerate(rng.normal(0, 3, (3, n_genes))):
        for group in (
            "Diffuse_Large_B_Cell_Lymphoma",
            "Follicular_Lymphoma",
            "Normal_B_cells",
        ):
            effect = true_fc if group.startswith("Diffuse") else 0
            rows.append(shift + effect + rng.normal(0, 0.3, (per_cell, n_genes)))
            labels += [group] * per_cell
            batches += [f"b{batch_index}"] * per_cell
    index = [f"s{i}" for i in range(len(labels))]
    exp_df = pd.DataFrame(
        np.vstack(rows), index=index, columns=[f"g{i}" for i in range(n_genes)]
    )
    ann = pd.DataFrame({"Major_group": labels, rl.BATCH_COL: batches}, index=index)
    reference = rl.gt_logfc_reference(exp_df, ann)
    assert np.corrcoef(reference["DLBCL_vs_FL"], true_fc)[0, 1] > 0.99
    centred = exp_df - exp_df.groupby(ann[rl.BATCH_COL]).transform("mean")
    good = rl.gt_logfc_concordance(centred, ann, reference)
    assert (
        good["gt_rho_DLBCL_vs_FL"] > 0.95
        and abs(good["gt_slope_DLBCL_vs_FL"] - 1) < 0.1
    )
    shrunk = rl.gt_logfc_concordance(centred * 0.5, ann, reference)
    assert shrunk["gt_slope_DLBCL_vs_FL"] == pytest.approx(0.5, abs=0.1)


# ── names (plan §1.1) ─────────────────────────────────────────────────────────


def test_publication_names_cover_every_new_column():
    needed = {
        "L",
        "N",
        "gate_L",
        "gate_N",
        "local_batch",
        "local_biology",
        "global_batch",
        "global_biology",
        "rule_front",
        "visual_best",
        "bridging_biology",
        "single_dx_batch",
        "bridging_batch",
        "in_reduced_panel",
        "cluster_id",
        "representative_of",
        "axis",
        "four_score_bar",
        "main_benchmark",
        "confounding_gradient",
        "leave_cohort_out",
        "lambda",
        "L11_single_dx",
        "04_sva_nocov",
        "05_combat_nocov",
        "V1",
        "LOBO",
        "gt_logfc",
    }
    assert needed <= set(rl.PUBLICATION_NAMES)
    assert set(rl.ANALYSED_METHODS) | set(rl.GRADIENT_ARMS) <= set(
        rl.METHOD_DISPLAY_NAMES
    )


def test_publication_names_hold_no_internal_label():
    values = (
        list(rl.PUBLICATION_NAMES.values())
        + list(rl.METHOD_DISPLAY_NAMES.values())
        + list(rl.STRATEGY_DISPLAY_NAMES.values())
    )
    offenders = [v for v in values if FORBIDDEN.search(v)]
    assert not offenders, offenders


def test_combined_axes_not_named_removal():
    """D1 (2026-11-08): the two combined axes never read as a sample-removal strategy."""
    for key in ("batch_removal", "biology_retention", "batch_removal_short"):
        assert "removal" not in rl.PUBLICATION_NAMES[key].lower()
    assert "global + local" in rl.PUBLICATION_NAMES["batch_removal"]


def test_no_publication_name_says_regret():
    """The leave-cohort-out loss is called "decrease" in publications (2026-11-08)."""
    values = list(rl.PUBLICATION_NAMES.values())
    assert not [v for v in values if "regret" in v.lower()]


# ── ledger ────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(not BASELINE_DOCX.exists(), reason="baseline docx not present")
def test_baseline_ledger_counts():
    _, totals = rl.docx_ledger(BASELINE_DOCX)
    assert (
        totals["main_figures"],
        totals["main_tables"],
        totals["supplementary_figures"],
        totals["supplementary_files"],
    ) == (6, 3, 19, 3)


# ── ComboBatch-image pod (plan revision_pod_combobatch_image_plan_261101) ─────


def test_harmonizer_routes_shambhala_to_published_implementation() -> None:
    """20_shambhala must use Shambhala2_fast (the published code), not the R entry."""
    assert rl.harmonizer("20_shambhala") is rl.shambhala_fast
    assert "20_shambhala" in rl.ANALYSED_METHODS


def test_env_check_compare_matrices() -> None:
    """r18's comparison: identical, slightly drifted and unrelated matrices."""
    import r18_env_check as r18

    rng = np.random.default_rng(1)
    base = pd.DataFrame(
        rng.normal(size=(20, 30)),
        index=[f"s{i}" for i in range(20)],
        columns=[f"g{j}" for j in range(30)],
    )
    assert r18.compare_matrices(base, base.copy())["verdict"] == "identical"
    drifted = base + rng.normal(scale=1e-4, size=base.shape)
    assert r18.compare_matrices(drifted, base)["verdict"] == "equivalent"
    other = pd.DataFrame(rng.normal(size=base.shape), base.index, base.columns)
    assert r18.compare_matrices(other, base)["verdict"] == "DIFFERENT"
    fewer_genes = base.iloc[:, :25]
    assert r18.compare_matrices(fewer_genes, base)["verdict"] == "DIFFERENT"
    loose = r18.compare_matrices(fewer_genes, base, require_same_shape=False)
    assert loose["verdict"] == "identical"


def test_flag_identical_to_raw_marks_only_unchanged_approaches():
    """Gate G2 choice 5: identity to the 01_raw row of the same key, raw never flagged."""
    import pandas as pd

    import revision_lib as rl

    base = {m: 0.5 for m in rl.IDENTITY_METRICS}
    rows = [
        {"strat": "S", "imp": "i", "post_rm": False, "method": "01_raw", **base},
        {"strat": "S", "imp": "i", "post_rm": False, "method": "36_explobatch", **base},
        {
            "strat": "S",
            "imp": "i",
            "post_rm": False,
            "method": "10_mnn",
            **{**base, rl.IDENTITY_METRICS[0]: 0.4},
        },
        {"strat": "T", "imp": "i", "post_rm": False, "method": "04_sva", **base},
    ]
    flags = rl.flag_identical_to_raw(pd.DataFrame(rows))
    assert flags.tolist() == [False, True, False, False]


def test_strategy_labels_carry_their_code():
    # Daniil 2026-11-08: figures and tables show "code · name"; S0 is "No removal"
    assert set(rl.STRATEGY_CODES) == set(rl.STRATEGY_DISPLAY_NAMES)
    for strat, label in rl.STRATEGY_DISPLAY_NAMES.items():
        assert label.startswith(rl.STRATEGY_CODES[strat] + " · ")
    assert rl.STRATEGY_DISPLAY_NAMES["S0_no_removal"] == "S0 · No removal"
