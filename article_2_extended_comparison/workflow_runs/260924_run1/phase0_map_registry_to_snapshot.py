"""Phase 0 of the Article 2 revision: map Article 1's metric registry onto the snapshot.

Plan: ``f1000_article2_revision_plan_260924.md`` §B5 and Phase 0 TODO item
"Map the 334 registry names onto the snapshot columns; report how many are recoverable".

Inputs (read-only)
------------------
- ``figures_for_article/supplementary_260824/Supplementary File 2.xlsx``, sheet
  ``Metric_polarity`` — Article 1's metric registry, 344 rows.
- ``harmonization-metrics/metric_tables/metrics_comprehensive_260905.csv`` — the pinned
  metric snapshot, 3,835 rows × 329 columns.
- ``figures_for_article/supplementary_260824/Supplementary File 3.csv.gz`` — used only to
  confirm that the ``PCReg_*`` → ``pcr_*`` rename points at the same quantity.

Filters applied
---------------
- The 10 registry rows whose ``Metric group`` is ``Metadata`` are excluded, leaving 334.
- No snapshot rows are filtered: recoverability is a property of columns, not of rows.
  The analysis-set restriction to 2,234 approaches happens downstream in Phase 1.

Outputs
-------
- ``09_registry_to_snapshot_map.csv`` — one row per non-metadata registry metric, with
  the snapshot column it maps to, the mapping route and whether it is recoverable.
- A printed summary, copied into ``09_metric_census.md``.
"""

from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = (
    REPO_ROOT / "figures_for_article/supplementary_260824/Supplementary File 2.xlsx"
)
SNAPSHOT_PATH = (
    REPO_ROOT / "harmonization-metrics/metric_tables/metrics_comprehensive_260905.csv"
)
SUPP_FILE_3_PATH = (
    REPO_ROOT / "figures_for_article/supplementary_260824/Supplementary File 3.csv.gz"
)
OUTPUT_MAP_PATH = Path(__file__).with_name("09_registry_to_snapshot_map.csv")

KEY_COLUMNS = ["strat", "imp", "method", "post_rm"]
BOOLEAN_FLAGS = {"wm_subsampled", "mk_is_self_reference", "xb_subsampled"}
# Registry name -> (snapshot numerator column, snapshot denominator column).
PERCENT_DERIVED = {
    "pct_samples_allNA": ("n_samples_allNA", "n_samples"),
    "pct_genes_allNA": ("n_genes_allNA", "n_genes"),
}
BASELINE_SUFFIXES = ("_raw", "_delta")


def classify_metric(registry_name: str, snapshot_columns: set[str]) -> tuple[str, str]:
    """Decide how one registry metric is recovered from the snapshot.

    Parameters
    ----------
    registry_name
        The metric name as Supplementary File 2 spells it.
    snapshot_columns
        Every column name of the pinned snapshot.

    Returns
    -------
    tuple[str, str]
        ``(route, snapshot_source)``. ``route`` is one of ``direct``,
        ``boolean_flag``, ``rename``, ``derived_percent``, ``derived_baseline`` or
        ``absent``; ``snapshot_source`` names the column(s) the value comes from.
    """
    if registry_name in BOOLEAN_FLAGS:
        return "boolean_flag", registry_name
    if registry_name in snapshot_columns:
        return "direct", registry_name
    if registry_name.startswith("PCReg_"):
        renamed = "pcr_" + registry_name.removeprefix("PCReg_")
        if renamed in snapshot_columns:
            return "rename", renamed
    if registry_name in PERCENT_DERIVED:
        numerator, denominator = PERCENT_DERIVED[registry_name]
        return "derived_percent", f"100 * {numerator} / {denominator}"
    for suffix in BASELINE_SUFFIXES:
        base_metric = registry_name.removesuffix(suffix)
        if registry_name.endswith(suffix) and base_metric in snapshot_columns:
            # figures_helpers.attach_raw_baseline(): the 01_raw, post_rm=False row of
            # the same (strat, imp) pair supplies the baseline.
            return "derived_baseline", f"{base_metric} vs 01_raw baseline"
    return "absent", ""


def pcreg_rename_agreement(snapshot: pd.DataFrame) -> pd.Series:
    """Spearman rho between each snapshot ``pcr_*`` column and Supp. File 3 ``PCReg_*``.

    Supplementary File 3 stores polarity-normalized values, so the check is a rank
    correlation on the shared (strat, imp, method, post_rm) keys, not equality.
    """
    supp_file_3 = pd.read_csv(SUPP_FILE_3_PATH)
    pcreg_columns = [c for c in supp_file_3.columns if c.startswith("PCReg_")]
    snapshot_keyed = snapshot.assign(post_rm=snapshot["post_rm"].astype(str))
    supp_keyed = supp_file_3.assign(post_rm=supp_file_3["post_rm"].astype(str))
    joined = snapshot_keyed.merge(supp_keyed, on=KEY_COLUMNS, suffixes=("", "_f3"))
    return pd.Series(
        {
            column: spearmanr(
                joined["pcr_" + column.removeprefix("PCReg_")],
                joined[column],
                nan_policy="omit",
            )[0]
            for column in pcreg_columns
        },
        name=f"spearman_rho_n{len(joined)}",
    )


def main() -> None:
    registry = pd.read_excel(REGISTRY_PATH, sheet_name="Metric_polarity")
    non_metadata_registry = registry[registry["Metric group"] != "Metadata"].copy()
    snapshot = pd.read_csv(SNAPSHOT_PATH, low_memory=False)
    snapshot_columns = set(snapshot.columns)
    numeric_columns = set(snapshot.select_dtypes("number").columns)

    routes = non_metadata_registry["Metric"].map(
        lambda name: classify_metric(name, snapshot_columns)
    )
    non_metadata_registry["route"] = routes.str[0]
    non_metadata_registry["snapshot_source"] = routes.str[1]
    non_metadata_registry["direct_is_numeric"] = non_metadata_registry["Metric"].isin(
        numeric_columns
    )
    non_metadata_registry["recoverable"] = non_metadata_registry["route"] != "absent"
    non_metadata_registry[
        [
            "Metric",
            "Polarity",
            "Metric group",
            "Metric type",
            "route",
            "snapshot_source",
            "direct_is_numeric",
            "recoverable",
        ]
    ].to_csv(OUTPUT_MAP_PATH, index=False)

    print("registry rows          :", len(registry))
    print("non-metadata metrics   :", len(non_metadata_registry))
    print(non_metadata_registry["route"].value_counts().to_string())
    print("recoverable            :", int(non_metadata_registry["recoverable"].sum()))
    print(
        "absent                 :",
        non_metadata_registry.loc[~non_metadata_registry["recoverable"], "Metric"]
        .sort_values()
        .tolist(),
    )
    print(
        "boolean flag counts    :",
        {
            flag: snapshot[flag].value_counts(dropna=False).to_dict()
            for flag in sorted(BOOLEAN_FLAGS)
        },
    )
    print(
        "PCReg rename check:\n" + pcreg_rename_agreement(snapshot).round(4).to_string()
    )
    print("wrote", OUTPUT_MAP_PATH)


if __name__ == "__main__":
    main()
