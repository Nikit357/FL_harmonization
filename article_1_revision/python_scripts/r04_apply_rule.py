"""
r04_apply_rule.py — blind application of the written selection rule (plan WP4 4.2–4.3).

Answers Reviewer 2, comment 1 (primary criterion and precedence) and Reviewer 1,
comment 2 (selection bias: leave-strategies-out check).

BLINDNESS PROTOCOL: the rule file (adjudication_rule_261029.md, or the _v2 file passed
with --rule) must be frozen first — its MD5 must be listed in FROZEN_MD5.txt (gate G2).
The script refuses to run otherwise, so that no pick is seen before the rule is fixed.

Steps (see the rule file for the definitions)
---------------------------------------------
1. Gate L: L ≥ 0.7 (approaches without L are "not evaluable").
1b. Method failure: an approach identical to its 01_raw row (rl.flag_identical_to_raw,
   r03 column identical_to_raw) is "method failed (returned the input)", not a candidate.
2. Gate N: N ≥ N_raw − 0.05 (01_raw, same strategy / imputation / post-removal) and
   permutation p < 0.05 (fallback: N > null mean + 1.645 · null SD). N is the 3-class
   F1; for strategy D (almost no Normal B) the 2-class DLBCL-vs-FL F1 (gate G2).
3. Pareto front on (batch_removal, biology_retention) inside each scenario pool;
   front ordered by the scaled Local-batch bar.
4. Visual check: the decisions of gate G2b are read from output/wp4/visual_check.tsv
   (accepted / vetoed / no veto given, with the reason; vetoes.tsv = its vetoed rows).
   The version-1 front never sees a veto (blindness: it is always reported). A second
   front is computed without the vetoed approaches; a candidate that enters it after the
   vetoes has not been looked at yet ("not reviewed") and goes to the next nb07 round.
   Gate G2b round 2 (Daniil, 2026-11-07): the visual check is CLOSED after round 2
   (VISUAL_CHECK_CLOSED). The front is not refilled again: only the accepted members are
   the selection; members that enter after the round-2 vetoes are written to
   not_added_check_closed.tsv (reported, never recommended). The frozen rule allows this:
   step 4 lets a front member be vetoed and does not require refilling the front.
   The multi-platform members get their tree leaf from leaf_assignment.tsv (rule step 4c).

Outputs (output/wp4/)
---------------------
gates.tsv                      every approach with its gate values and pass flags
selection_by_rule.tsv          version-1 front members per scenario, in rule order
                               (no veto applied)
selection_after_visual_check.tsv  front recomputed without the vetoed approaches, with
                               the column visual_check (accepted / no veto given / not
                               reviewed); the approaches the article recommends. With
                               the check closed: accepted members only, plus the column
                               tree_leaf_name (leaf of the decision tree)
not_added_check_closed.tsv     members that entered the front after the last round of
                               vetoes and were not shown (check closed)
rule_vs_visual_concordance.tsv the 15 approaches of the submitted Table 3 vs the front
                               (version 1; _after_visual_check.tsv: vs the second front)
leave_strategies_out.tsv       step 4.3: front without strategies A, B, E1–E3 (FSQN R, SVA,
                               MNN, plus every other method on either front)
selection_review.xlsx / .md    --review: gate G2b package (one sheet per scenario,
                               Table 3 preview, Figure 6F leaf preview, vetoes)

Usage
-----
python r04_apply_rule.py [--rule adjudication_rule_261029.md] [--review]
"""

from __future__ import annotations

import argparse
import hashlib

import numpy as np
import pandas as pd

import revision_lib as rl

OUT_DIR = rl.OUTPUT_DIR / "wp4"
FOUR_SCORES_PATH = rl.OUTPUT_DIR / "wp3/four_scores.parquet"
FROZEN_MD5_PATH = rl.REVISION_DIR / "FROZEN_MD5.txt"
DEFAULT_RULE = rl.REVISION_DIR / "adjudication_rule_261029.md"

GATE_L_THRESHOLD = 0.7
# Gate G2b round 2 (Daniil, 2026-11-07): no third round; the front is not refilled again.
VISUAL_CHECK_CLOSED = True
LEAF_ASSIGNMENT_PATH = OUT_DIR / "leaf_assignment.tsv"
GATE_N_MARGIN = 0.05
GATE_N_PVALUE = 0.05
NULL_Z_95 = 1.645

MULTI_PLATFORM = (
    "S0_no_removal",
    "A_confirmed_bad",
    "B_extended_bad",
    "D_malignant_only",
    "E1_iterative_r1",
    "E2_iterative_r2",
    "E3_iterative_r3",
    "I_rare_batches_removed",
)
# Scenario pools of the rule file (section "Scenario → candidate strategies").
SCENARIOS: dict[str, tuple[str, ...]] = {
    "FF only": ("J_ff_only",),
    "FFPE only": ("K_ffpe_only",),
    "RNA-seq only": ("C_rnaseq_only",),
    "Multi-platform (RNA-seq + microarrays)": MULTI_PLATFORM,
}
INFORMATION_ONLY_SCENARIOS: dict[str, tuple[str, ...]] = {
    "Microarrays only (not a tree leaf)": (
        "F_microarray_only",
        "G_affymetrix_only",
        "H_affymetrix_extended",
    ),
    # Gate G2b (Daniil, 2026-11-03): which imputations and methods are best when no batch
    # may be removed before harmonization. Both post-removal settings, on equal terms.
    # Asked after the freeze; reported as information, not as a rule pick.
    "No batch removal (S0 only)": ("S0_no_removal",),
}
FSQN_DERIVED_STRATEGIES = (
    "A_confirmed_bad",
    "B_extended_bad",
    "E1_iterative_r1",
    "E2_iterative_r2",
    "E3_iterative_r3",
)

# The 15 visually selected approaches of the submitted Table 3 (strategy, imputation,
# method); the table does not state post-removal, so concordance ignores it.
VISUAL_BEST: tuple[tuple[str, str, str], ...] = (
    ("D_malignant_only", "strict", "10_mnn"),
    ("H_affymetrix_extended", "strict", "10_mnn"),
    ("S0_no_removal", "strict", "10_mnn"),
    ("S0_no_removal", "strict", "13_fsmvn"),
    ("S0_no_removal", "strict", "33_amdbnorm"),
    ("J_ff_only", "strict", "10_mnn"),
    ("J_ff_only", "strict", "16_fsqn_r"),
    ("K_ffpe_only", "knn", "04_sva"),
    ("K_ffpe_only", "softimpute", "04_sva"),
    ("K_ffpe_only", "strict", "04_sva"),
    ("C_rnaseq_only", "knn", "04_sva"),
    ("C_rnaseq_only", "softimpute", "04_sva"),
    ("C_rnaseq_only", "knn", "16_fsqn_r"),
    ("C_rnaseq_only", "softimpute", "16_fsqn_r"),
    ("C_rnaseq_only", "strict", "16_fsqn_r"),
)


def assert_rule_frozen(rule_path) -> str:
    """Refuse to run unless the rule file's MD5 is listed in FROZEN_MD5.txt."""
    digest = hashlib.md5(rule_path.read_bytes()).hexdigest()
    frozen = FROZEN_MD5_PATH.read_text()
    if digest not in frozen:
        raise SystemExit(
            f"{rule_path.name} (md5 {digest}) is not in FROZEN_MD5.txt. Gate G2: Daniil "
            "approves the rule, then append its md5 line, then run this script."
        )
    return digest


def _n_columns(two_class: pd.Series, frame: pd.DataFrame, suffix: str) -> pd.Series:
    """N (3-class) or N2 (DLBCL vs FL) value of each row, per the strategy's gate N."""
    three = frame[f"N{suffix}"]
    two = (
        frame[f"N2{suffix}"]
        if f"N2{suffix}" in frame
        else pd.Series(np.nan, frame.index)
    )
    return two.where(two_class, three)


def apply_gates(scores: pd.DataFrame) -> pd.DataFrame:
    """
    Gate L, the method-failure check and gate N for every approach of the analysis set.

    Gate N uses the two-class (DLBCL vs FL) prediction for rl.TWO_CLASS_N_STRATEGIES
    and the three-class one elsewhere (rule step 2; gate G2, 2026-11-03). An approach
    flagged `identical_to_raw` (the method returned its input) is a method failure and
    never a candidate; `01_raw` itself stays a candidate.
    """
    gated = scores[scores["in_analysis_set"]].copy()
    two_class = gated["strat"].isin(rl.TWO_CLASS_N_STRATEGIES)
    gated["gate_N_classes"] = np.where(two_class, 2, 3)
    gated["N_gate"] = _n_columns(two_class, gated, "")
    gated["N_gate_null_mean"] = _n_columns(two_class, gated, "_null_mean")
    gated["N_gate_null_std"] = _n_columns(two_class, gated, "_null_std")
    gated["N_gate_pvalue"] = _n_columns(two_class, gated, "_perm_pvalue")
    raw = gated[gated["method"] == "01_raw"].set_index(["strat", "imp", "post_rm"])[
        "N_gate"
    ]
    gated["N_raw"] = [
        raw.get((s, i, p), np.nan)
        for s, i, p in zip(gated["strat"], gated["imp"], gated["post_rm"])
    ]
    if "identical_to_raw" not in gated:
        gated["identical_to_raw"] = False
    gated["method_failed"] = gated["identical_to_raw"].fillna(False).astype(bool) & (
        gated["method"] != "01_raw"
    )
    gated["gate_L_evaluable"] = gated["L"].notna()
    gated["gate_L_pass"] = gated["L"] >= GATE_L_THRESHOLD
    null_threshold = gated["N_gate_null_mean"] + NULL_Z_95 * gated["N_gate_null_std"]
    above_null = np.where(
        gated["N_gate_pvalue"].notna(),
        gated["N_gate_pvalue"] < GATE_N_PVALUE,
        gated["N_gate"] > null_threshold,
    )
    gated["gate_N_evaluable"] = gated["N_gate"].notna() & gated["N_raw"].notna()
    gated["gate_N_noninferior"] = gated["N_gate"] >= gated["N_raw"] - GATE_N_MARGIN
    gated["gate_N_above_null"] = above_null & gated["N_gate"].notna()
    gated["gate_N_pass"] = gated["gate_N_noninferior"] & gated["gate_N_above_null"]
    gated["candidate"] = (
        gated["gate_L_pass"] & gated["gate_N_pass"] & ~gated["method_failed"]
    )
    return gated


def scenario_front(
    gated: pd.DataFrame, strategies: tuple[str, ...], vetoed: set[tuple]
) -> pd.DataFrame:
    """Pareto front of the candidates of one scenario pool, in rule order."""
    pool = gated[gated["strat"].isin(strategies) & gated["candidate"]].copy()
    pool = pool[[tuple(k) not in vetoed for k in pool[rl.APPROACH_KEYS].to_numpy()]]
    if pool.empty:
        return pool.assign(on_front=pd.Series(dtype=bool))
    pool["on_front"] = rl.pareto_front(pool, ["batch_removal", "biology_retention"])
    front = pool[pool["on_front"]].sort_values("local_batch_scaled", ascending=False)
    front["front_rank"] = np.arange(1, len(front) + 1)
    return front


def all_fronts(
    gated: pd.DataFrame, exclude: tuple[str, ...], vetoed: set[tuple]
) -> pd.DataFrame:
    """Fronts of every scenario (rule pools + information-only pools)."""
    frames = []
    for name, pool in {**SCENARIOS, **INFORMATION_ONLY_SCENARIOS}.items():
        kept = tuple(s for s in pool if s not in exclude)
        front = scenario_front(gated, kept, vetoed)
        frames.append(
            front.assign(
                scenario=name,
                tree_leaf=name in SCENARIOS,
                n_candidates=int(gated["strat"].isin(kept).sum()),
            )
        )
    return pd.concat(frames, ignore_index=True)


def concordance(front: pd.DataFrame) -> pd.DataFrame:
    """kept / lost / new of the 15 visual picks vs the rule front (post-removal ignored)."""
    front_keys = set(map(tuple, front[["strat", "imp", "method"]].to_numpy()))
    visual = set(VISUAL_BEST)
    rows = [
        {
            "strat": s,
            "imp": i,
            "method": m,
            "status": "kept" if (s, i, m) in front_keys else "lost",
        }
        for s, i, m in VISUAL_BEST
    ]
    rows += [
        {"strat": s, "imp": i, "method": m, "status": "new"}
        for s, i, m in sorted(front_keys - visual)
    ]
    return pd.DataFrame(rows)


def leave_strategies_out(gated: pd.DataFrame, vetoed: set[tuple]) -> pd.DataFrame:
    """Step 4.3: front membership with / without A, B, E1–E3 (FSQN R, SVA, MNN + others)."""
    rows = []
    for name, pool in SCENARIOS.items():
        without = tuple(s for s in pool if s not in FSQN_DERIVED_STRATEGIES)
        # the three methods of the tree, then every other method on either front (G2b)
        on_any_front = set()
        for strategies in (pool, without):
            on_any_front |= set(scenario_front(gated, strategies, vetoed)["method"])
        methods = ["16_fsqn_r", "04_sva", "10_mnn"] + sorted(
            on_any_front - {"16_fsqn_r", "04_sva", "10_mnn"}
        )
        if not without:
            rows.append({"scenario": name, "status": "not evaluable"})
            continue
        for label, strategies in (("with", pool), ("without", without)):
            front = scenario_front(gated, strategies, vetoed)
            for method in methods:
                hits = front[front["method"] == method]
                rows.append(
                    {
                        "scenario": name,
                        "pool": label,
                        "method": method,
                        "method_display": rl.method_display_name(method),
                        "n_candidates": int(gated["strat"].isin(strategies).sum()),
                        "n_front": len(front),
                        "on_front": not hits.empty,
                        "best_front_rank": (
                            int(hits["front_rank"].min()) if len(hits) else None
                        ),
                    }
                )
    return pd.DataFrame(rows)


def write_review(
    gated: pd.DataFrame,
    fronts: pd.DataFrame,
    concord: pd.DataFrame,
    lso: pd.DataFrame,
    vetoes: pd.DataFrame,
    final: pd.DataFrame,
) -> None:
    """Gate G2b package: selection_review.xlsx + selection_review.md."""
    columns = [
        "front_rank",
        *rl.APPROACH_KEYS,
        "method_display",
        "L",
        "N",
        "gate_N_classes",
        "N_gate",
        "N_raw",
        "global_batch",
        "local_batch",
        "global_biology",
        "local_biology",
        "batch_removal",
        "biology_retention",
    ]
    path = OUT_DIR / "selection_review.xlsx"
    with pd.ExcelWriter(path) as writer:
        for name, front in fronts.groupby("scenario", sort=False):
            front[columns].to_excel(writer, sheet_name=name[:31], index=False)
        concord.to_excel(writer, sheet_name="Table 3 vs rule", index=False)
        preview = (
            fronts[fronts["tree_leaf"]]
            .sort_values(["scenario", "front_rank"])
            .groupby("scenario")
            .head(3)[
                ["scenario", "front_rank", "method_display", "strat", "imp", "post_rm"]
            ]
        )
        preview.to_excel(writer, sheet_name="Figure 6F preview", index=False)
        lso.to_excel(writer, sheet_name="Leave-strategies-out", index=False)
        vetoes.to_excel(writer, sheet_name="Vetoes", index=False)
        final[["scenario", "visual_check", *columns]].to_excel(
            writer, sheet_name="After visual check", index=False
        )
        gated.groupby("strat")[
            ["method_failed", "gate_L_pass", "gate_N_pass", "candidate"]
        ].sum().to_excel(writer, sheet_name="Gate pass counts")
        gated[gated["method_failed"]][[*rl.APPROACH_KEYS, "method_display"]].to_excel(
            writer, sheet_name="Method failed", index=False
        )
    lines = [
        "# Selection review (gate G2b)",
        "",
        "Generated by `r04_apply_rule.py --review`.",
        "",
    ]
    for name, front in fronts.groupby("scenario", sort=False):
        lines.append(f"## {name} — {len(front)} on the front")
        lines += [
            f"{int(r.front_rank)}. {r.method_display} · {r.strat} · {r.imp} · "
            f"post_rm={r.post_rm}"
            for r in front.itertuples()
        ]
        lines.append("")
    lines.append("# After the visual check (vetoes removed, front recomputed)")
    lines.append("")
    for name, front in final.groupby("scenario", sort=False):
        lines.append(f"## {name} — {len(front)} on the front")
        lines += [
            f"{int(r.front_rank)}. [{r.visual_check}] {r.method_display} · {r.strat} · "
            f"{r.imp} · post_rm={r.post_rm}"
            for r in front.itertuples()
        ]
        lines.append("")
    lines.append("## Concordance with the submitted Table 3")
    lines.append(concord["status"].value_counts().to_string())
    (OUT_DIR / "selection_review.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {path}")


def visual_check_status(fronts: pd.DataFrame, visual_check: pd.DataFrame) -> pd.Series:
    """G2b decision of every front member; members never shown to Daniil → not reviewed."""
    decided = {
        tuple(k): d
        for k, d in zip(
            visual_check[rl.APPROACH_KEYS].to_numpy(), visual_check["decision"]
        )
    }
    return pd.Series(
        [
            decided.get(tuple(k), "not reviewed")
            for k in fronts[rl.APPROACH_KEYS].to_numpy()
        ],
        index=fronts.index,
    )


def close_visual_check(final: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split the recomputed front into the selection (accepted) and the not-added rest.

    Parameters
    ----------
    final
        Front without the vetoed approaches, with the column visual_check.

    Returns
    -------
    (selection, not_added): accepted members (re-numbered selection_rank inside each
    scenario, front_rank kept) and the members never shown (check closed).
    """
    undecided = final["visual_check"].isin(["no veto given"])
    assert not undecided.any(), "every shown member needs accepted / vetoed before closing"
    selection = final[final["visual_check"] == "accepted"].copy()
    selection["selection_rank"] = selection.groupby("scenario").cumcount() + 1
    not_added = final[final["visual_check"] == "not reviewed"].copy()
    not_added["visual_check"] = "not added (check closed)"
    return selection, not_added


def add_tree_leaf_names(selection: pd.DataFrame) -> pd.DataFrame:
    """Leaf of the decision tree: the scenario name, or leaf_assignment.tsv (multi-platform)."""
    leaf_names = selection["scenario"].where(selection["tree_leaf"], "")
    if LEAF_ASSIGNMENT_PATH.exists():
        leaves = read_decisions(LEAF_ASSIGNMENT_PATH)
        lookup = {
            tuple(k): leaf
            for k, leaf in zip(leaves[rl.APPROACH_KEYS].to_numpy(), leaves["tree_leaf_name"])
        }
        assigned = [lookup.get(tuple(k)) for k in selection[rl.APPROACH_KEYS].to_numpy()]
        leaf_names = pd.Series(
            [a if a is not None else n for a, n in zip(assigned, leaf_names)],
            index=selection.index,
        )
    return selection.assign(tree_leaf_name=leaf_names)


def read_decisions(path) -> pd.DataFrame:
    """visual_check.tsv / vetoes.tsv with a boolean post_rm (empty frame when absent)."""
    if not path.exists():
        return pd.DataFrame(columns=[*rl.APPROACH_KEYS, "decision", "reason"])
    table = pd.read_csv(path, sep="\t")
    table["post_rm"] = table["post_rm"].astype(str).str.lower().isin(["true", "1"])
    return table


def main() -> None:
    """Apply the frozen rule."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--rule", default=str(DEFAULT_RULE))
    parser.add_argument("--review", action="store_true")
    args = parser.parse_args()
    from pathlib import Path

    digest = assert_rule_frozen(Path(args.rule))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    visual_check = read_decisions(OUT_DIR / "visual_check.tsv")
    vetoes = read_decisions(OUT_DIR / "vetoes.tsv")
    vetoed = set(map(tuple, vetoes[rl.APPROACH_KEYS].to_numpy()))

    gated = apply_gates(pd.read_parquet(FOUR_SCORES_PATH))
    gated.to_csv(OUT_DIR / "gates.tsv", sep="\t", index=False)
    # version 1: blind, never touched by a veto
    fronts = all_fronts(gated, exclude=(), vetoed=set()).assign(rule_md5=digest)
    fronts.to_csv(OUT_DIR / "selection_by_rule.tsv", sep="\t", index=False)
    concord = concordance(fronts[fronts["tree_leaf"]])
    concord.to_csv(OUT_DIR / "rule_vs_visual_concordance.tsv", sep="\t", index=False)
    # after the visual check: vetoed approaches leave, the next ones may enter
    final = all_fronts(gated, exclude=(), vetoed=vetoed).assign(rule_md5=digest)
    final["visual_check"] = visual_check_status(final, visual_check)
    if VISUAL_CHECK_CLOSED:
        final, not_added = close_visual_check(final)
        final = add_tree_leaf_names(final)
        not_added.to_csv(OUT_DIR / "not_added_check_closed.tsv", sep="\t", index=False)
        print(f"check closed: {len(final)} selected, {len(not_added)} not added")
    final.to_csv(OUT_DIR / "selection_after_visual_check.tsv", sep="\t", index=False)
    concord_final = concordance(final[final["tree_leaf"]])
    concord_final.to_csv(
        OUT_DIR / "rule_vs_visual_concordance_after_visual_check.tsv",
        sep="\t",
        index=False,
    )
    lso = leave_strategies_out(gated, vetoed)
    lso.to_csv(OUT_DIR / "leave_strategies_out.tsv", sep="\t", index=False)
    print("version 1:\n" + fronts.groupby("scenario").size().to_string())
    print(
        "after the visual check:\n"
        + final.groupby(["scenario", "visual_check"]).size().to_string()
    )
    if args.review:
        write_review(gated, fronts, concord, lso, vetoes, final)


if __name__ == "__main__":
    main()
