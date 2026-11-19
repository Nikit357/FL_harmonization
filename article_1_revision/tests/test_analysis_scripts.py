"""
Toy checks of the post-pod analysis code (plan WP5, WP6 step 6.6, WP7 step 7.3):
`revision_lib.pareto_layers / rule_order / score_runs`, the line fit of r13, the
leave-cohort-out evaluation of r22 and the comparison of r05.

All inputs are synthetic: nothing here reads the real four scores, so nothing reveals a
pick of the selection rule (blindness, CLAUDE.md hard rule 2).

Run: python -m pytest tests/test_analysis_scripts.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import revision_lib as rl  # noqa: E402


def toy_points() -> pd.DataFrame:
    """Five points: a, b on the first front; c dominated by a; d by c; e has NaN."""
    return pd.DataFrame(
        {
            "batch_removal": [0.9, 0.5, 0.8, 0.7, np.nan],
            "biology_retention": [0.6, 0.9, 0.5, 0.4, 0.9],
            "local_batch_scaled": [0.2, 0.9, 0.5, 0.1, 0.3],
            "candidate": [True, True, True, True, True],
        },
        index=list("abcde"),
    )


def test_pareto_layers_depths():
    layers = rl.pareto_layers(toy_points(), ["batch_removal", "biology_retention"])
    assert layers["a"] == 1 and layers["b"] == 1
    assert layers["c"] == 2 and layers["d"] == 3
    assert np.isnan(layers["e"])


def test_rule_order_candidates_first_then_layer_then_tiebreak():
    points = toy_points()
    points.loc["a", "candidate"] = False
    order = rl.rule_order(points)
    # b is the only remaining front-1 candidate; a (non-candidate) comes after all
    # candidates; e (NaN axis) is last among candidates.
    assert order["b"] == 1
    assert order["c"] == 2 and order["d"] == 3 and order["e"] == 4
    assert order["a"] == 5


def test_rule_order_tiebreak_inside_front():
    order = rl.rule_order(toy_points())
    assert order["b"] < order["a"]  # same layer, higher local batch first


def toy_reference() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "headline_metric": ["gb", "gbio", "lb", "lbio"],
            "polarity": [1, -1, 1, 1],
            "low": [0.0, -1.0, 0.0, 0.0],
            "high": [1.0, 0.0, 0.5, 2.0],
        },
        index=list(rl.FOUR_SCORE_BARS),
    )


def test_score_runs_scaling_and_axes():
    metrics = pd.DataFrame(
        {
            "gb": [0.5],
            "gbio": [0.25],  # polarity −1 → −0.25 → (−0.25 + 1) / 1 = 0.75
            "lb": [0.25],
            "lbio": [1.0],
            rl.L_SCORE_COL: [0.8],
            rl.N_SCORE_COL: [0.6],
        }
    )
    scored = rl.score_runs(metrics, toy_reference())
    assert scored["global_batch_scaled"].iloc[0] == pytest.approx(0.5)
    assert scored["global_biology_scaled"].iloc[0] == pytest.approx(0.75)
    assert scored["local_batch_scaled"].iloc[0] == pytest.approx(0.5)
    assert scored["batch_removal"].iloc[0] == pytest.approx(0.5)
    assert scored["biology_retention"].iloc[0] == pytest.approx(0.625)
    assert scored["L"].iloc[0] == 0.8 and np.isnan(scored["N_perm_pvalue"].iloc[0])


def test_r13_fit_line_recovers_slope():
    import r13_gradient_stats as r13

    rng = np.random.default_rng(1)
    rows = [
        {
            "cramers_v_major_group": v,
            "replicate": r,
            "y": 0.9 - 0.3 * v + rng.normal(0, 0.01) + 0.02 * r,
        }
        for r in (1, 2, 3)
        for v in np.linspace(0, 1, 11)
    ]
    fit = r13.fit_line(pd.DataFrame(rows), "y")
    assert fit["slope"] == pytest.approx(-0.3, abs=0.03)
    assert (
        fit["slope_ci_low"] < -0.3 < fit["slope_ci_high"]
        or abs(fit["slope"] + 0.3) < 0.03
    )


def test_r13_fit_line_flat_series_is_not_fitted():
    import r13_gradient_stats as r13

    frame = pd.DataFrame(
        {"cramers_v_major_group": [0, 0.5, 1, 0.2], "replicate": 1, "y": 1.0}
    )
    assert r13.fit_line(frame, "y")["model"] == "not fitted"


def toy_v1_runs() -> pd.DataFrame:
    """One fold, three methods; 'good' best on train and second on test."""
    rows = []
    values = {
        ("train", "01_raw"): (0.2, 0.9),
        ("train", "good"): (0.9, 0.8),
        ("train", "bad"): (0.1, 0.1),
        ("test", "01_raw"): (0.3, 0.9),
        ("test", "good"): (0.8, 0.7),
        ("test", "bad"): (0.95, 0.95),
    }
    for (part, arm), (batch, bio) in values.items():
        rows.append(
            {
                "subset_id": f"v1_C_f1_{part}",
                "scenario": "C",
                "fold": 1,
                "part": part,
                "arm": arm,
                "status": "ok",
                "L": 0.9,
                "N": 0.7,
                "N_null_mean": 0.3,
                "N_null_std": 0.05,
                "N_perm_pvalue": 0.01,
                "global_batch_scaled": batch,
                "local_batch_scaled": batch,
                "global_biology_scaled": bio,
                "local_biology_scaled": bio,
                "global_biology": bio,
                "batch_removal": batch,
                "biology_retention": bio,
            }
        )
    return pd.DataFrame(rows)


def test_r22_chosen_method_rank_and_regret():
    import r22_v1_evaluate as r22

    runs = toy_v1_runs()
    parts = []
    for _, part in runs.groupby("subset_id"):
        gated = r22.gate_and_rank(part)
        gated["_front"] = rl.pareto_front(
            gated.where(gated["candidate"]), ["batch_removal", "biology_retention"]
        )
        parts.append(gated)
    ranked = pd.concat(parts, ignore_index=True)
    summary = pd.DataFrame(
        [
            {
                "scenario": "C",
                "fold": 1,
                "part": "test",
                "n_batches": 3,
                "n_DLBCL": 5,
                "n_FL": 5,
                "n_Normal_B": 0,
            }
        ]
    )
    results = r22.evaluate(ranked, summary)
    chosen = results[results["role"] == "chosen on the training part"].iloc[0]
    assert chosen["method"] == "good"
    assert chosen["rank_on_test"] == 2 and not chosen["top1_hit"] and chosen["top3_hit"]
    assert chosen["regret_batch_removal"] == pytest.approx(0.15)
    assert bool(chosen["test_evaluable"])
    random_row = results[results["role"] == "random method"].iloc[0]
    assert random_row["top1_hit"] == pytest.approx(1 / 3)


def test_r05_jaccard_and_compare_identity():
    import r05_robustness as r05

    assert r05.jaccard({1, 2}, {2, 3}) == pytest.approx(1 / 3)
    frame = pd.DataFrame(
        {
            "strat": ["J_ff_only"] * 4,
            "imp": "strict",
            "method": list("wxyz"),
            "post_rm": False,
            "rule_rank": [1, 2, 3, 4],
            "on_front": [True, True, False, False],
            "scenario": "FF only",
        }
    )
    row = r05.compare(frame, frame, "same")[0]
    assert row["kendall_tau_b"] == pytest.approx(1.0)
    assert row["top3_jaccard"] == 1.0 and row["front_jaccard"] == 1.0
