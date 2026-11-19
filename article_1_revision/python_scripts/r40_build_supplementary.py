"""
r40_build_supplementary.py — revised Supplementary Files 1–3 (plan WP10).

Builds new files from read-only copies of the submitted ones (inputs/), never by editing
the submitted package. Every new sheet name, column header and categorical value is in
plain words (plan §1.1, `revision_lib.PUBLICATION_NAMES`); the 87 published metric
columns keep their published identifiers.

The script is re-run as results arrive. Each part is filled from what exists and lists
what is still missing (printed and written to `output/wp10/build_status.tsv`):

| Part | Needs | Available |
|---|---|---|
| File 1: samples in single- / multi-diagnosis batches per cohort | wp1 + S0 annotation | now |
| File 2: Metric_polarity panel columns | wp2 + wp3 | now (provisional until gate G1) |
| File 2: Table_S1 01_raw "no-op control"; Table_S2 two new rows | — | now |
| File 3 "Main benchmark": 87 metrics + four scores | wp3 | now |
| File 3: gate results, "Selected by the rule", method failed (returned input), visual check + final selection (G2b) | wp4 (r04, after gates G2 / G2b) | later |
| File 3: "Diagnosis separation on multi-diagnosis batches" | wp8 (metrics pod) | later |
| File 3 "Confounding gradient" sheet | wp6 gradient_scores (r13) | later |
| File 3 "Leave-cohort-out validation" sheet | wp7 v1_scores (r22) | later |

BLINDNESS: the script reads rule picks only from `output/wp4/selection_by_rule.tsv`
(written by r04 after the rule is frozen); it never computes a front itself.

Deviation from the plan (noted for gate G4): Supplementary File 1 has one row per cohort
(88 rows), not per sample, so the two new columns are sample counts per cohort ("Samples
in single-diagnosis batches", "Samples in multi-diagnosis batches") instead of yes / no.

Outputs (output/wp10/)
----------------------
Supplementary File 1.csv
Supplementary File 2.xlsx
Supplementary File 3.xlsx   (or Supplementary File 3.zip of three csv.gz if > 25 MB)
build_status.tsv            part → filled / missing (what it waits for)

Usage
-----
python r40_build_supplementary.py
"""

from __future__ import annotations

import zipfile

import pandas as pd

import r04_apply_rule as rule
import revision_lib as rl

OUT_DIR = rl.OUTPUT_DIR / "wp10"
PN = rl.PUBLICATION_NAMES
MAX_XLSX_MB = 25.0

WP1_BRIDGING = rl.OUTPUT_DIR / "wp1/bridging_batches.tsv"
PANEL_PATH = rl.OUTPUT_DIR / "wp2/reduced_panel.tsv"
CLUSTERS_PATH = rl.OUTPUT_DIR / "wp2/cluster_membership.tsv"
HEADLINES_PATH = rl.OUTPUT_DIR / "wp3/bar_headlines.tsv"
FOUR_SCORES_PATH = rl.OUTPUT_DIR / "wp3/four_scores.parquet"
GATES_PATH = rl.OUTPUT_DIR / "wp4/gates.tsv"
SELECTION_PATH = rl.OUTPUT_DIR / "wp4/selection_by_rule.tsv"
VISUAL_CHECK_PATH = rl.OUTPUT_DIR / "wp4/visual_check.tsv"
FINAL_SELECTION_PATH = rl.OUTPUT_DIR / "wp4/selection_after_visual_check.tsv"
BRIDGING_PATH = rl.OUTPUT_DIR / "wp8/bridging_biology.parquet"
GRADIENT_PATH = rl.OUTPUT_DIR / "wp6/gradient_scores.parquet"
V1_PATH = rl.OUTPUT_DIR / "wp7/v1_scores.parquet"

BAR_NAMES: dict[str, str] = {bar: PN[bar] for bar in rl.FOUR_SCORE_BARS}
SCOPE_ROLE_NAMES: dict[str, str] = {
    "batch removal": "batch mixing",  # D1, 2026-11-08
    "biology retention": "diagnosis retention",
    "neither": "neither",
}
SCENARIO_NAMES: dict[str, str] = {
    "C": rl.STRATEGY_DISPLAY_NAMES["C_rnaseq_only"],
    "K": rl.STRATEGY_DISPLAY_NAMES["K_ffpe_only"],
    "J": rl.STRATEGY_DISPLAY_NAMES["J_ff_only"],
    "S0": rl.STRATEGY_DISPLAY_NAMES["S0_no_removal"],
}

status_rows: list[dict] = []


def note(part: str, filled: bool, waits_for: str = "") -> None:
    """Record whether a part of the package could be filled."""
    status_rows.append(
        {
            "part": part,
            "status": "filled" if filled else "missing",
            "waits_for": waits_for,
        }
    )


def yes_no(flag: object) -> str:
    """Yes / No / Not evaluable for a boolean-or-NaN flag."""
    if pd.isna(flag):
        return "Not evaluable"
    return "Yes" if bool(flag) else "No"


# ── File 1 ─────────────────────────────────────────────────────────────────────


def build_file_1() -> pd.DataFrame:
    """Cohort table + samples in single- / multi-diagnosis batches."""
    cohorts = pd.read_csv(rl.INPUTS_DIR / "Supplementary File 1.csv")
    ann = rl.load_s0_annotation()
    single = set(rl.single_diagnosis_batches(ann))
    in_single = ann[rl.BATCH_COL].isin(single)
    cohort = ann[rl.COHORT_COL]
    counts = pd.DataFrame(
        {
            "Samples in single-diagnosis batches": in_single.groupby(cohort).sum(),
            "Samples in multi-diagnosis batches": (~in_single).groupby(cohort).sum(),
        }
    )
    merged = cohorts.merge(
        counts, left_on="COHORT_LABEL", right_index=True, how="left", validate="1:1"
    )
    missing = merged["Samples in single-diagnosis batches"].isna().sum()
    note("File 1 batch columns", missing == 0, f"{missing} cohorts without samples")
    return merged


# ── File 2 ─────────────────────────────────────────────────────────────────────


def panel_columns(polarity: pd.DataFrame) -> pd.DataFrame:
    """Metric_polarity sheet + the five reduced-panel columns."""
    panel = pd.read_csv(PANEL_PATH, sep="\t").set_index("metric")
    clusters = pd.read_csv(CLUSTERS_PATH, sep="\t").set_index("metric")
    headlines = set(pd.read_csv(HEADLINES_PATH, sep="\t")["headline_metric"])
    out = polarity.copy()
    metric = out["Metric"]
    out[PN["in_reduced_panel"]] = metric.isin(panel.index).map(
        {True: "Yes", False: "No"}
    )
    out[PN["cluster_id"]] = metric.map(clusters["cluster_id"]).astype("Int64")
    out[PN["representative_of"]] = (
        metric.map(panel["representative_of"]).fillna("").str.replace(";", ", ")
    )
    out[PN["axis"]] = metric.map(
        panel["axis_scope"] + " / " + panel["axis_role"].map(SCOPE_ROLE_NAMES)
    ).fillna("")
    bar = metric.map(panel["four_score_bar"]).map(BAR_NAMES).fillna("")
    out[PN["four_score_bar"]] = [
        f"{name} (headline metric)" if name and m in headlines else name
        for name, m in zip(bar, metric)
    ]
    return out


# The fold-change agreement row was removed (Daniil 2026-11-08): the metric is not
# analysed or shown in the revision.
NEW_METRIC_ROWS: list[dict] = [
    {
        "Metric name": "The four scores",
        "Metric type": "Summary",
        "Metric group": "Selection rule",
        "Method definition": (
            "Four readouts replace the composite score; no total is computed. "
            f"{PN['L']}: mean per-gene Spearman correlation of 56 marker genes before vs "
            f"after harmonization. {PN['N']}: macro-F1 of a 3-class diagnosis classifier "
            "trained with one batch left out, compared with its permutation null. "
            f"{PN['global_batch']} / {PN['global_biology']} and {PN['local_batch']} / "
            f"{PN['local_biology']}: one headline metric each, the medoid of its group in "
            "the reduced metric panel (column 'Score bar' of sheet Metric_polarity)."
        ),
        "Source": "This revision",
    },
]


def build_file_2() -> dict[str, pd.DataFrame]:
    """All sheets of Supplementary File 2 with the revision changes."""
    sheets = pd.read_excel(rl.SUPP_FILE_2_PATH, sheet_name=None)
    sheets["Metric_polarity"] = panel_columns(sheets["Metric_polarity"])
    note("File 2 Metric_polarity panel columns (provisional until gate G1)", True)
    methods = sheets["Table_S1_methods"].copy()
    methods.loc[methods["Method name"] == "01_raw", "Method harshness"] = (
        "no-op control"
    )
    sheets["Table_S1_methods"] = methods
    sheets["Table_S2_metrics"] = pd.concat(
        [sheets["Table_S2_metrics"], pd.DataFrame(NEW_METRIC_ROWS)], ignore_index=True
    )
    note("File 2 Table_S1 / Table_S2 edits", True)
    return sheets


# ── File 3 ─────────────────────────────────────────────────────────────────────


def score_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """The six score columns in plain words (native units)."""
    return pd.DataFrame(
        {
            PN["L"]: frame["L"],
            PN["N"]: frame["N"],
            **{BAR_NAMES[bar]: frame[bar] for bar in rl.FOUR_SCORE_BARS},
        },
        index=frame.index,
    )


def main_benchmark_sheet() -> pd.DataFrame:
    """2,407 approaches: published columns + four scores + gates + selection flags."""
    table = rl.load_supp_file_3(analysis_set_only=False).drop(columns="in_analysis_set")
    scores = pd.read_parquet(FOUR_SCORES_PATH)
    assert (table[rl.APPROACH_KEYS].values == scores[rl.APPROACH_KEYS].values).all()
    sheet = pd.concat([table, score_columns(scores)], axis=1)
    note("File 3 Main benchmark: 87 metrics + four scores", True)

    visual = set(rule.VISUAL_BEST)
    sheet[PN["visual_best"]] = [
        "Yes" if (s, i, m) in visual else "No"
        for s, i, m in table[["strat", "imp", "method"]].to_numpy()
    ]
    keys = rl.APPROACH_KEYS
    if GATES_PATH.exists():
        gates = pd.read_csv(GATES_PATH, sep="\t")
        gates["post_rm"] = gates["post_rm"].astype(bool)
        merged = table[keys].merge(gates, on=keys, how="left")
        sheet[PN["gate_L"]] = [
            yes_no(p) if e else "Not evaluable"
            for p, e in zip(
                merged["gate_L_pass"], merged["gate_L_evaluable"].fillna(False)
            )
        ]
        sheet[PN["gate_N"]] = [
            yes_no(p) if e else "Not evaluable"
            for p, e in zip(
                merged["gate_N_pass"], merged["gate_N_evaluable"].fillna(False)
            )
        ]
        note("File 3 gate results", True)
    else:
        note("File 3 gate results", False, "r04 (after gate G2)")
    if SELECTION_PATH.exists():
        selection = pd.read_csv(SELECTION_PATH, sep="\t")
        selection = selection[selection["tree_leaf"]]
        selection["post_rm"] = selection["post_rm"].astype(bool)
        picked = set(map(tuple, selection[keys].to_numpy()))
        sheet[PN["rule_front"]] = [
            "Yes" if tuple(k) in picked else "No" for k in table[keys].to_numpy()
        ]
        note("File 3 Selected by the rule", True)
    else:
        note("File 3 Selected by the rule", False, "r04 + gate G2b")
    sheet[PN["method_returned_input"]] = [
        yes_no(flag) for flag in scores["identical_to_raw"].fillna(False)
    ]
    if VISUAL_CHECK_PATH.exists() and FINAL_SELECTION_PATH.exists():
        # gate G2b (closed 2026-11-07): Daniil's decision on every front member he saw
        decisions = rule.read_decisions(VISUAL_CHECK_PATH)
        decided = {
            tuple(k): d.capitalize()
            for k, d in zip(decisions[keys].to_numpy(), decisions["decision"])
        }
        sheet[PN["visual_check"]] = [
            decided.get(tuple(k), "Not shown") for k in table[keys].to_numpy()
        ]
        final = rule.read_decisions(FINAL_SELECTION_PATH)
        recommended = set(map(tuple, final[keys].to_numpy()))
        sheet[PN["final_selection"]] = [
            "Yes" if tuple(k) in recommended else "No" for k in table[keys].to_numpy()
        ]
        note("File 3 visual check and final selection", True)
    else:
        note("File 3 visual check and final selection", False, "r04 after gate G2b")
    if BRIDGING_PATH.exists():
        bridging = pd.read_parquet(BRIDGING_PATH)
        bridging["post_rm"] = bridging["post_rm"].astype(bool)
        reference = rl.bar_scaling_reference()
        values = []
        merged = table[keys].merge(bridging, on=keys, how="left")
        for bar in ("global_biology", "local_biology"):
            row = reference.loc[bar]
            raw = pd.to_numeric(merged.get(row["headline_metric"]), errors="coerce")
            values.append(
                (raw * row["polarity"] - row["low"]) / (row["high"] - row["low"])
            )
        sheet[PN["bridging_biology"]] = pd.concat(values, axis=1).mean(
            axis=1, skipna=False
        )
        note("File 3 bridging-batch diagnosis separation", True)
    else:
        note(
            "File 3 bridging-batch diagnosis separation",
            False,
            "r30 on the metrics pod",
        )
    return sheet


def gradient_sheet() -> pd.DataFrame | None:
    """540 gradient runs in plain words."""
    if not GRADIENT_PATH.exists():
        note("File 3 Confounding gradient sheet", False, "pods + r13")
        return None
    runs = pd.read_parquet(GRADIENT_PATH)
    design = [
        PN["L11_single_dx"] if kind == "single_dx_control" else "Gradient"
        for kind in runs["kind"]
    ]
    sheet = pd.DataFrame(
        {
            "Design": design,
            PN["lambda"]: runs["lambda"],
            PN["replicate"]: runs["replicate"],
            PN["cap"]: runs["cap"].astype(str).map({"150": "Yes"}).fillna("No"),
            # r13 merges the design table into the metrics: the design's own count
            # (n_samples_y) exists also for failed runs.
            "Samples": runs.get("n_samples_y", runs.get("n_samples")),
            PN["cramers_v"]: runs["cramers_v_major_group"],
            "Method": runs["arm"].map(rl.method_display_name),
            "Run status": runs["status"].map({"ok": "Completed"}).fillna("Failed"),
        }
    )
    sheet = pd.concat([sheet, score_columns(runs)], axis=1)
    note("File 3 Confounding gradient sheet", True)
    return sheet


def v1_sheet() -> pd.DataFrame | None:
    """1,240 leave-cohort-out runs in plain words."""
    if not V1_PATH.exists():
        note("File 3 Leave-cohort-out sheet", False, "pods + r22 (after gate G2b)")
        return None
    runs = pd.read_parquet(V1_PATH)
    chosen = (
        runs[runs["part"] == "train"]
        .sort_values("rule_rank")
        .groupby(["scenario", "fold"])["method"]
        .first()
    )
    sheet = pd.DataFrame(
        {
            "Scenario": runs["scenario"].map(SCENARIO_NAMES),
            "Fold": runs["fold"],
            "Part": runs["part"].map({"train": PN["train"], "test": PN["test"]}),
            "Method": runs["method"].map(rl.method_display_name),
        }
    )
    sheet = pd.concat([sheet, score_columns(runs)], axis=1)
    sheet[PN["gate_L"]] = runs["gate_L_pass"].map(yes_no)
    sheet[PN["gate_N"]] = runs["gate_N_pass"].map(yes_no)
    sheet["Rank in the order of the selection rule"] = runs["rule_rank"]
    sheet[PN["chosen_on_train"]] = [
        "Yes" if chosen.get((s, f)) == m else "No"
        for s, f, m in zip(runs["scenario"], runs["fold"], runs["method"])
    ]
    note("File 3 Leave-cohort-out sheet", True)
    return sheet


def write_file_3(sheets: dict[str, pd.DataFrame]) -> None:
    """xlsx with up to three sheets; a zip of csv.gz files when the xlsx is too big."""
    path = OUT_DIR / "Supplementary File 3.xlsx"
    with pd.ExcelWriter(path) as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)
    size_mb = path.stat().st_size / 1e6
    print(f"Supplementary File 3.xlsx: {size_mb:.1f} MB")
    if size_mb > MAX_XLSX_MB:
        archive = OUT_DIR / "Supplementary File 3.zip"
        with zipfile.ZipFile(archive, "w") as zipped:
            for name, frame in sheets.items():
                data = frame.to_csv(index=False).encode()
                import gzip

                zipped.writestr(f"{name}.csv.gz", gzip.compress(data))
        path.unlink()
        print(f"too large for xlsx → {archive}")


def main() -> None:
    """Build every part that can be built now."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    build_file_1().to_csv(OUT_DIR / "Supplementary File 1.csv", index=False)
    with pd.ExcelWriter(OUT_DIR / "Supplementary File 2.xlsx") as writer:
        for name, frame in build_file_2().items():
            frame.to_excel(writer, sheet_name=name, index=False)
    sheets = {PN["main_benchmark"]: main_benchmark_sheet()}
    for name, builder in (
        (PN["confounding_gradient"], gradient_sheet),
        (PN["leave_cohort_out"], v1_sheet),
    ):
        frame = builder()
        if frame is not None:
            sheets[name] = frame
    write_file_3(sheets)
    status = pd.DataFrame(status_rows)
    status.to_csv(OUT_DIR / "build_status.tsv", sep="\t", index=False)
    print(status.to_string(index=False))


if __name__ == "__main__":
    main()
