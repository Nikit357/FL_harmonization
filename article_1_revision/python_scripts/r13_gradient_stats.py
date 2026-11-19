"""
r13_gradient_stats.py — statistics of the confounding gradient (plan WP6 step 6.6).

Runs on JupyterHub after the pods: needs `output/wp6/gradient_metrics.parquet`, written by
`python r12_revision_metrics.py --experiment gradient --concat`.

What it does
------------
1. Scores every run (`revision_lib.score_runs`): L (marker correlation), N (cross-batch
   prediction), the four bars in their native units and min-max scaled on the main
   benchmark range, and the two combined axes (12 scores). The agreement with batch-free
   fold changes (gt_*, written by r12) is not analysed (Daniil 2026-11-08).
2. For every arm (method) × score, over the 33 capped designs (11 λ levels × 3
   replicates), fits the linear mixed model  score ~ V + (1 | replicate), where V is the
   measured bias-corrected Cramér's V (batch × major group) of the design. If the mixed
   model cannot be fitted (singular random effect, < 3 replicates, too few points) an
   ordinary least squares line is fitted instead; the `model` column says which.
3. Reports the slope with its 95 % CI, the fitted value at V = 0 and V = 1, the value
   predicted at the real-data V (on the same 5 batches, and for all 7,174 samples), and
   the fixed "meaningful" criterion of the plan: |mean(λ = 1) − mean(λ = 0)| >
   2 × SD of the replicates at λ = 0. A null result is reported as a null. Arms that
   cannot run at λ = 1 (covariate arms) use their last λ with a value (0.9) as the end
   point (column `end_lambda`; Daniil 2026-11-08). `mean_at_lambda1` holds the end-point
   mean.
3b. Monotonic trend test (Daniil, gate G4 review 2026-11-07): Spearman ρ between the score
   and V over the 33 capped runs of the arm (3 replicates per λ, treated as independent
   points; constant scores → not tested), its two-sided p-value, and the
   Benjamini–Hochberg FDR over every tested arm × score row of the table (12 scores ×
   tested arms)
   (`spearman_fdr`). `significant_fdr` = FDR < 0.05; `changes_with_confounding` =
   significant_fdr AND meaningful (both the statistical and the effect-size criterion).
4. Anchors for the four scores (plan WP3): median value at λ = 0 (positive control),
   λ = 1 (negative control) and on the unharmonized arm, over the capped designs.
5. The uncapped sensitivity curve (11 designs, replicate 1) is fitted with OLS and set
   next to the capped slope; the 11-single-diagnosis-batch control is listed as its own
   point (different batches: it confounds design with platform, so it is not on the line).
5b. Rule ranks along the gradient (Daniil, gate G4 review 2026-11-07): inside every
   gradient design the arms are gated (r04.apply_gates, the design's 01_raw run gives
   N_raw) and ranked in the rule order (revision_lib.rule_order, 1 = best), exactly as
   r22 ranks the leave-cohort-out runs. Runs that failed or returned their input are not
   ranked; n_ranked says how many arms were ranked in the design.
6. Failures and fallbacks (expected at λ = 1 for the covariate arms, plan caveat C3):
   one row per run that did not give a score, with the λ level and the status.

Outputs (output/wp6/)
---------------------
gradient_scores.parquet        every run with its scores (input of nb04 and Supp File 3)
gradient_slopes.tsv            arm × score: model, slope, CI, values at V = 0 / 1 / real,
                               delta, replicate SD at λ = 0, meaningful flag, Spearman ρ /
                               p / BH-FDR, significant_fdr, changes_with_confounding
gradient_anchors.tsv           score × arm: medians at λ = 0, λ = 1, real-data position
gradient_cap_sensitivity.tsv   arm × score: capped vs uncapped slope
gradient_single_dx_control.tsv arm × score on the 11 single-diagnosis batches
gradient_failures.tsv          runs without scores (status, λ, arm)
gradient_ranks.tsv             design × arm: λ, replicate, cap, V, gates, rule rank, n_ranked
real_data_v.json               the real-data V used to place the data on the curves

Usage
-----
python r13_gradient_stats.py
"""

from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from statsmodels.stats.multitest import multipletests

import r04_apply_rule as rule
import revision_lib as rl

OUT_DIR = rl.OUTPUT_DIR / "wp6"
METRICS_PATH = OUT_DIR / "gradient_metrics.parquet"
WP1_PATH = rl.OUTPUT_DIR / "wp1/confounding_by_strategy.tsv"

V_COLUMN = "cramers_v_major_group"
SCORES: tuple[str, ...] = (
    "L",
    "N",
    *rl.FOUR_SCORE_BARS,
    *(f"{bar}_scaled" for bar in rl.FOUR_SCORE_BARS),
    "batch_removal",
    "biology_retention",
)
# Agreement with batch-free fold changes (gt_*) is computed by r12 but not analysed:
# Daniil 2026-11-08 keeps the metric space at the 22-metric panel + L / N, and the
# metric must also leave the BH family, or the q-values would depend on it.
MEANINGFUL_SD_FACTOR = 2.0  # plan WP6 step 6.6, fixed before the results
FDR_THRESHOLD = 0.05  # gate G4 review (Daniil, 2026-11-07)


def real_data_v() -> dict:
    """
    Real-data position on the V axis.

    `five_batches`: bias-corrected V (batch × 3-class major group) of all S0 samples of
    the 5 gradient batches with a DLBCL / FL / Normal B label; `all_samples`: the S0
    batch × diagnosis V of the confounding diagnostics (r01).
    """
    ann = rl.load_s0_annotation()
    five = ann[ann[rl.BATCH_COL].isin(rl.GRADIENT_ASSIGNED_DIAGNOSIS)]
    group = rl.major_group(five, n_classes=3)
    keep = group.notna()
    result = {
        "five_batches": rl.cramers_v(five.loc[keep, rl.BATCH_COL], group[keep]),
        "five_batches_n": int(keep.sum()),
    }
    if WP1_PATH.exists():
        wp1 = pd.read_csv(WP1_PATH, sep="\t").set_index("strategy")
        result["all_samples"] = float(wp1.loc["S0_no_removal", "V_batch_x_diagnosis"])
    return result


def fit_line(points: pd.DataFrame, score: str) -> dict:
    """
    score ~ V + (1 | replicate); OLS fallback. Returns slope, CI, intercept, model.

    Parameters
    ----------
    points : rows of one arm with columns V_COLUMN, "replicate" and `score`.
    score : column to model.
    """
    import statsmodels.formula.api as smf

    data = points[[V_COLUMN, "replicate", score]].dropna()
    data = data.rename(columns={V_COLUMN: "V", score: "y"})
    empty = {"model": "not fitted", "n_points": len(data)}
    if len(data) < 4 or data["V"].nunique() < 3 or data["y"].std() == 0:
        return empty
    fitted, model = None, "mixed"
    if data["replicate"].nunique() >= 3:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                fitted = smf.mixedlm("y ~ V", data, groups=data["replicate"]).fit(
                    reml=True
                )
                if not fitted.converged or not np.isfinite(fitted.bse["V"]):
                    fitted = None
            except (ValueError, np.linalg.LinAlgError):
                fitted = None
    if fitted is None:
        fitted, model = smf.ols("y ~ V", data).fit(), "ols"
    low, high = fitted.conf_int().loc["V"]
    return {
        "model": model,
        "n_points": len(data),
        "slope": float(fitted.params["V"]),
        "slope_ci_low": float(low),
        "slope_ci_high": float(high),
        "intercept": float(fitted.params["Intercept"]),
    }


def arm_statistics(capped: pd.DataFrame, real_v: dict) -> pd.DataFrame:
    """Slope table: one row per arm × score over the capped designs."""
    rows = []
    for arm, points in capped.groupby("arm"):
        for score in SCORES:
            if score not in points or points[score].notna().sum() == 0:
                continue
            fit = fit_line(points, score)
            at_zero = points.loc[points["lambda"] == 0.0, score].dropna()
            # End point = the highest λ with a value: λ = 1, or λ = 0.9 for the arms
            # that cannot run at λ = 1 (ComBat / M-ComBat with the diagnosis covariate;
            # Daniil 2026-11-08, gates_review §10.6 Q2 option a).
            with_value = points.loc[points[score].notna(), "lambda"]
            end_lambda = float(with_value.max()) if len(with_value) else np.nan
            at_one = points.loc[np.isclose(points["lambda"], end_lambda), score].dropna()
            sd_zero = float(at_zero.std()) if len(at_zero) > 1 else np.nan
            delta = (
                float(at_one.mean() - at_zero.mean())
                if len(at_zero) and len(at_one)
                else np.nan
            )
            row = {
                "arm": arm,
                "method_display": rl.method_display_name(arm),
                "score": score,
                **fit,
                "mean_at_lambda0": float(at_zero.mean()) if len(at_zero) else np.nan,
                "end_lambda": end_lambda,
                "mean_at_lambda1": float(at_one.mean()) if len(at_one) else np.nan,
                "delta_lambda1_minus_lambda0": delta,
                "replicate_sd_at_lambda0": sd_zero,
                "meaningful": bool(
                    np.isfinite(delta)
                    and np.isfinite(sd_zero)
                    and abs(delta) > MEANINGFUL_SD_FACTOR * sd_zero
                ),
            }
            if "slope" in fit:
                for label, v in (("V0", 0.0), ("V1", 1.0), *real_v_items(real_v)):
                    row[f"fitted_at_{label}"] = fit["intercept"] + fit["slope"] * v
            row.update(spearman_trend(points, score))
            rows.append(row)
    return add_fdr(pd.DataFrame(rows))


def spearman_trend(points: pd.DataFrame, score: str) -> dict:
    """Spearman ρ (score vs V) and its two-sided p over the runs of one arm.

    Parameters
    ----------
    points
        Capped runs of one arm (columns V_COLUMN and score).
    score
        Score column.

    Returns
    -------
    dict with spearman_rho, spearman_p, spearman_n (NaN when the score is constant or
    fewer than 4 runs have it).
    """
    pair = points[[V_COLUMN, score]].dropna()
    if len(pair) < 4 or pair[score].nunique() < 2:
        return {"spearman_rho": np.nan, "spearman_p": np.nan, "spearman_n": len(pair)}
    rho, p_value = spearmanr(pair[V_COLUMN], pair[score])
    return {"spearman_rho": float(rho), "spearman_p": float(p_value), "spearman_n": len(pair)}


def add_fdr(slopes: pd.DataFrame) -> pd.DataFrame:
    """Benjamini–Hochberg FDR over every tested row; significance and combined flag."""
    tested = slopes["spearman_p"].notna()
    slopes["spearman_fdr"] = np.nan
    if tested.any():
        slopes.loc[tested, "spearman_fdr"] = multipletests(
            slopes.loc[tested, "spearman_p"], method="fdr_bh"
        )[1]
    slopes["significant_fdr"] = slopes["spearman_fdr"] < FDR_THRESHOLD
    slopes["changes_with_confounding"] = slopes["significant_fdr"] & slopes["meaningful"]
    return slopes


def gradient_ranks(usable: pd.DataFrame) -> pd.DataFrame:
    """Gate and rank the arms inside every gradient design (rule order, 1 = best).

    Parameters
    ----------
    usable
        Scored gradient runs with status ok (capped and uncapped designs).

    Returns
    -------
    One row per design × arm with the gate flags, rule_rank and n_ranked.
    """
    frames = []
    for _, design in usable.groupby("subset_id"):
        frame = design.assign(
            strat=design["subset_id"],
            imp="softimpute",
            method=design["arm"],
            post_rm=False,
            in_analysis_set=True,
        )
        gated = rule.apply_gates(frame)
        gated["rule_rank"] = rl.rule_order(gated)
        gated["n_ranked"] = len(gated)
        frames.append(gated)
    ranks = pd.concat(frames, ignore_index=True)
    columns = [
        "subset_id", "arm", "method_display", "lambda", "replicate", "cap", V_COLUMN,
        "gate_L_pass", "gate_N_pass", "candidate", "batch_removal", "biology_retention",
        "local_batch_scaled", "rule_rank", "n_ranked",
    ]
    return ranks[[c for c in columns if c in ranks]]


def real_v_items(real_v: dict) -> list[tuple[str, float]]:
    """(label, V) pairs of the real-data positions that exist."""
    return [
        (f"real_{key}", float(real_v[key]))
        for key in ("five_batches", "all_samples")
        if key in real_v
    ]


def anchors(capped: pd.DataFrame) -> pd.DataFrame:
    """Medians at λ = 0 and λ = 1 per score × arm, and the unharmonized-arm medians."""
    rows = []
    for score in SCORES:
        if score not in capped:
            continue
        for arm, points in capped.groupby("arm"):
            rows.append(
                {
                    "score": score,
                    "arm": arm,
                    "method_display": rl.method_display_name(arm),
                    "median_lambda0": points.loc[
                        points["lambda"] == 0.0, score
                    ].median(),
                    "median_lambda1": points.loc[
                        points["lambda"] == 1.0, score
                    ].median(),
                    "median_all_levels": points[score].median(),
                }
            )
    return pd.DataFrame(rows)


def cap_sensitivity(capped: pd.DataFrame, uncapped: pd.DataFrame) -> pd.DataFrame:
    """Capped (replicate 1 only, for a like-for-like comparison) vs uncapped OLS slopes."""
    rows = []
    for arm in sorted(set(capped["arm"]) | set(uncapped["arm"])):
        for score in SCORES:
            fits = {}
            for label, frame in (
                ("capped_r1", capped[capped["replicate"] == 1]),
                ("uncapped", uncapped),
            ):
                points = frame[frame["arm"] == arm].assign(replicate=1)
                fit = fit_line(points, score) if score in points else {}
                fits[f"slope_{label}"] = fit.get("slope", np.nan)
            rows.append({"arm": arm, "score": score, **fits})
    table = pd.DataFrame(rows)
    table["slope_difference"] = table["slope_uncapped"] - table["slope_capped_r1"]
    return table.dropna(subset=["slope_capped_r1", "slope_uncapped"], how="all")


def main() -> None:
    """Score the gradient runs and write the statistics tables."""
    if not METRICS_PATH.exists():
        raise SystemExit(
            f"{METRICS_PATH} is missing: run `python r12_revision_metrics.py "
            "--experiment gradient --concat` after the pod runs (RUNBOOK.md)."
        )
    metrics = pd.read_parquet(METRICS_PATH)
    scored = rl.score_runs(metrics, rl.bar_scaling_reference())
    scored["method_display"] = scored["arm"].map(rl.method_display_name)
    scored.to_parquet(OUT_DIR / "gradient_scores.parquet", index=False)

    # Gate G3 (d) / G2 choice 5 (Daniil, 2026-11-03): a run whose method returned its
    # input (e.g. SVA's "returning uncorrected data" fallback) is a method failure; the
    # slope of that arm rests on the remaining λ levels.
    scored["identical_to_raw"] = rl.flag_identical_to_raw(
        scored.assign(method=scored["arm"]), group_keys=("subset_id",)
    )
    scored.loc[
        scored["identical_to_raw"] & (scored["status"] == "ok"), "status"
    ] = "method_returned_input"
    scored.to_parquet(OUT_DIR / "gradient_scores.parquet", index=False)
    ok = scored["status"] == "ok"
    failures = scored.loc[
        ~ok | scored[["L", "N", "global_batch"]].isna().any(axis=1),
        ["subset_id", "arm", "status", "kind", "lambda", "replicate", "cap"],
    ]
    failures.to_csv(OUT_DIR / "gradient_failures.tsv", sep="\t", index=False)

    usable = scored[ok & (scored["kind"] == "gradient")]
    capped = usable[usable["cap"].astype(str) == "150"]
    uncapped = usable[usable["cap"].astype(str) != "150"]
    real_v = real_data_v()
    (OUT_DIR / "real_data_v.json").write_text(json.dumps(real_v, indent=1))

    gradient_ranks(usable).to_csv(OUT_DIR / "gradient_ranks.tsv", sep="\t", index=False)
    slopes = arm_statistics(capped, real_v)
    slopes.to_csv(OUT_DIR / "gradient_slopes.tsv", sep="\t", index=False)
    anchors(capped).to_csv(OUT_DIR / "gradient_anchors.tsv", sep="\t", index=False)
    cap_sensitivity(capped, uncapped).to_csv(
        OUT_DIR / "gradient_cap_sensitivity.tsv", sep="\t", index=False
    )
    single = scored[ok & (scored["kind"] == "single_dx_control")]
    columns = ["arm", "method_display", V_COLUMN, *[s for s in SCORES if s in single]]
    single[columns].to_csv(
        OUT_DIR / "gradient_single_dx_control.tsv", sep="\t", index=False
    )

    print(f"runs: {len(scored)}; ok {int(ok.sum())}; failures listed {len(failures)}")
    print(f"real-data V: {real_v}")
    headline = slopes[slopes["score"].isin(["L", "N", "batch_removal"])]
    print(
        headline[
            ["method_display", "score", "slope", "meaningful", "spearman_rho", "spearman_fdr"]
        ]
        .round(3)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
