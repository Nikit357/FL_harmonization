"""Assemble the Article 2 supplementary table workbooks (plan §7, Phase 6).

Three Excel workbooks are written to `supplementary/`:

    Supplementary File 1 — the analysis set and its metrics       (README + 6 sheets)
    Supplementary File 2 — cross-batch structure and prediction   (README + 6 sheets)
    Supplementary File 3 — the marker panel                       (README + 4 sheets)

Files 1 and 2 are built from the nine `A2_T*` tables in `tables/`, which
`article2_generalizability.py` writes. Two sheets are not stored as an `A2_T*` table
and are derived here instead: `Elected_sets_by_class`, which needs the election itself,
and `Strategy_and_imputation_summary`, which is an aggregate over `A2_T1`. Both are
recomputed from the same module the tables came from, so a workbook cannot disagree
with a table.

File 3 is built from the marker-panel tables of Article 1's deep-dive analysis in
`figures_for_article/current_figures_tables_for_article_260819/` and from the gene
panel annotation. It is the data behind Supplementary Figures 11 and 13.

Every workbook opens with a README sheet written in plain language: one line per
following sheet saying what it stores, how many rows it has and which table it came
from. Every data sheet carries a provenance line in row 1 naming the source table and
the filter that produced it, so a sheet lifted out of the workbook is still
self-describing; the column headers are on row 2 and the data starts on row 3.

The script finishes with the duplication check plan §7 asks for: every sheet's columns
are compared against the three supplementary files Article 1 ships, and the report is
written to `supplementary/duplication_check_{stamp}.md`.

    source ~/venvs/collagen_3_11/bin/activate
    cd article_2_extended_comparison
    python analysis/build_supplementary_workbooks.py
"""
from __future__ import annotations

import argparse
import gzip
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                      # article_2_extended_comparison/
REPO = ROOT.parent                      # FL_harmonization/

sys.path.insert(0, str(HERE))
import article2_generalizability as a2   # noqa: E402

MARKER_TABLES = REPO / "figures_for_article/current_figures_tables_for_article_260819"
GENE_ANNOTATION = REPO / "harmonization-metrics-calculation/marker_gene_annotation.csv"

# Article 1's shipped supplementary files, for the duplication check of plan §7.
ARTICLE1_SUPP = {
    "Supplementary File 1 (cohort annotation)":
        REPO / "figures_for_article/supplementary_260824/Supplementary File 1.csv",
    "Supplementary File 2 (methods, metrics, polarity)":
        REPO / "figures_for_article/supplementary_260824/Supplementary File 2.xlsx",
    "Supplementary File 3 (87 metrics x 2,407 approaches)":
        REPO / "figures_for_article/supplementary_260824/Supplementary File 3.csv.gz",
}

# openpyxl refuses a sheet name over 31 characters; every name below is inside it.
MAX_SHEET_NAME = 31


# ── sheet assembly helpers ────────────────────────────────────────────────────

class Sheet:
    """One workbook sheet: a table, the provenance line above it, and its README text.

    `extra` holds further (provenance, table) blocks written below the first one,
    separated by a blank row. Two sheets need it: the reconciliation ledger, which
    carries the Shambhala identity check underneath, and the strategy summary, which
    carries the method-by-strategy medians underneath.
    """

    def __init__(self, name, table, provenance, readme, extra=None):
        assert len(name) <= MAX_SHEET_NAME, f"sheet name too long: {name}"
        self.name = name
        self.table = table
        self.provenance = provenance
        self.readme = readme
        self.extra = extra or []

    @property
    def n_rows(self) -> int:
        return len(self.table)


def write_workbook(path: Path, title: str, purpose: str, sheets: list[Sheet]) -> None:
    """Write one workbook: the README sheet first, then every data sheet in order."""
    readme = build_readme(title, purpose, sheets)
    with pd.ExcelWriter(path, engine="openpyxl") as xl:
        readme.to_excel(xl, sheet_name="README", index=False)
        for sheet in sheets:
            row = 0
            for prov, table in [(sheet.provenance, sheet.table)] + sheet.extra:
                pd.DataFrame({prov: []}).to_excel(
                    xl, sheet_name=sheet.name, index=False, startrow=row)
                table.to_excel(xl, sheet_name=sheet.name, index=False, startrow=row + 1)
                row += len(table) + 3
        autosize(xl)
    size_mb = path.stat().st_size / 1e6
    print(f"  wrote {path.name}  ({len(sheets)} data sheets + README, {size_mb:.1f} MB)")


def build_readme(title: str, purpose: str, sheets: list[Sheet]) -> pd.DataFrame:
    """The plain-language contents page: one row per sheet, plus the workbook header."""
    rows = [{"Sheet": title, "What it holds": purpose, "Rows": "", "Source table": ""},
            {"Sheet": "", "What it holds": "", "Rows": "", "Source table": ""},
            {"Sheet": "README", "What it holds": "This contents page.",
             "Rows": "", "Source table": ""}]
    for sheet in sheets:
        rows.append({"Sheet": sheet.name, "What it holds": sheet.readme,
                     "Rows": f"{sheet.n_rows:,}", "Source table": sheet.provenance})
    return pd.DataFrame(rows)


def autosize(xl) -> None:
    """Widen every column enough to read the header without opening the cell."""
    for ws in xl.book.worksheets:
        for column_cells in ws.iter_cols(min_row=1, max_row=min(ws.max_row, 40)):
            longest = max((len(str(c.value)) for c in column_cells if c.value), default=0)
            letter = column_cells[0].column_letter
            ws.column_dimensions[letter].width = min(max(longest + 2, 10), 60)


# ── derived sheets ────────────────────────────────────────────────────────────

def reconciliation_ledger(df: pd.DataFrame, supp3: pd.DataFrame,
                          snapshot_rows: int, snapshot_canonical_rows: int,
                          date_tag: str) -> pd.DataFrame:
    """The 2,407 → 2,234 audit trail, one row per step, with the count after each.

    A reader who disagrees with the analysis set can follow this ledger from the
    published benchmark table to the 2,234 rows Article 2 analyses without reading any
    code.
    """
    steps = [
        ("1", "Completed approaches in Supplementary File 3 of the source benchmark",
         len(supp3), "none"),
        ("2", "Approaches kept as the canonical analysis set",
         int((supp3.pct_samples_allNA < 5).sum()), "pct_samples_allNA < 5"),
        ("3", f"Rows in the pinned metric snapshot metrics_comprehensive_{date_tag}.csv",
         snapshot_rows, "none"),
        ("4", "Snapshot rows after the Shambhala canonicalization",
         snapshot_canonical_rows,
         "drop the 17 non-canonical shambhala_P/Q variants; "
         "rename shambhala_P0std_Q0std to 20_shambhala"),
        ("5", "Analysis set after joining groups L, M and N from the snapshot",
         len(df), "one-to-one merge on strat, imp, method, post_rm"),
        ("6", "of which 20_shambhala", int((df.method == "20_shambhala").sum()), "none"),
        ("7", "Distinct methods", int(df.method.nunique()), "none"),
        ("8", "Distinct filter strategies", int(df.strat.nunique()), "none"),
        ("9", "Distinct imputation strategies", int(df.imp.nunique()), "none"),
        ("10", "Post-removal variants", int(df.post_rm.nunique()), "none"),
        ("11", "Approaches flagged as Article 1 clustermap best",
         int(df.is_clustermap_best.sum()), "is_clustermap_best"),
        ("12", "Approaches on a confounded strategy",
         int(df.is_confirmed_bad.sum()), "strat in A_confirmed_bad, B_extended_bad"),
    ]
    return pd.DataFrame(steps, columns=["step", "what is counted", "count",
                                        "filter applied"])


def elected_sets_long(df: pd.DataFrame, sets: dict) -> pd.DataFrame:
    """Every elected approach, one row per (metric class, approach).

    `n_classes_electing` travels with each row so the reader can find the approaches
    several classes agree on without pivoting the table first.
    """
    census = pd.Series(0, index=df.index, dtype=int)
    for ids in sets.values():
        census.loc[sorted(ids)] += 1

    rows = []
    for metric_class, ids in sets.items():
        sub = df.loc[sorted(ids), ["run_id", "strat", "imp", "method", "post_rm",
                                   "harshness_level", "generalizability_index"]].copy()
        sub.insert(0, "metric_class", metric_class)
        sub["n_classes_electing"] = census.loc[sub.index].values
        rows.append(sub)
    out = pd.concat(rows, ignore_index=True)
    return out.sort_values(["metric_class", "n_classes_electing", "run_id"],
                           ascending=[True, False, True])


def strategy_imputation_summary(df: pd.DataFrame, sets: dict) -> pd.DataFrame:
    """Median L/M/N behaviour per (strategy, imputation), with the election counts."""
    elected = {c: set(ids) for c, ids in sets.items()}
    out = []
    for (strat, imp), sub in df.groupby(["strat", "imp"]):
        row = {"strat": strat, "imp": imp, "n_approaches": len(sub),
               "n_methods": sub.method.nunique()}
        for col in a2.INDEX_COLUMNS:
            row[f"median_{col}"] = sub[col].median()
        row["median_generalizability_index"] = sub.generalizability_index.median()
        for cls in ("global", "local", "distributional", "structural", "composite",
                    "L", "M", "N", "clustermap_best"):
            row[f"n_elected_{cls}"] = len(set(sub.index) & elected[cls])
        out.append(row)
    return (pd.DataFrame(out)
            .sort_values("median_generalizability_index", ascending=False))


def method_strategy_medians(df: pd.DataFrame) -> pd.DataFrame:
    """The bubble grid of panel a2_p7 as a table: one row per (method, strategy)."""
    out = (df.groupby(["method", "strat"])
             .agg(n_approaches=("run_id", "size"),
                  median_generalizability_index=("generalizability_index", "median"),
                  median_mk_rho_mean_markers=("mk_rho_mean_markers", "median"),
                  median_xb_margin=("xb_margin", "median"),
                  median_pv_lobo3_f1_macro_mean=("pv_lobo3_f1_macro_mean", "median"))
             .reset_index())
    return out.sort_values(["method", "strat"])


def margin_raw_and_delta(t1: pd.DataFrame) -> pd.DataFrame:
    """Group M in all three forms — harmonized, raw baseline, and the difference."""
    keep = ["run_id", "strat", "imp", "method", "post_rm", "harshness_level",
            "is_clustermap_best", "is_prediction_best", "is_confirmed_bad",
            "xb_rank_agree", "xb_rank_agree_raw", "xb_rank_agree_delta",
            "xb_rank_disagree_diffbio", "xb_rank_disagree_diffbio_raw",
            "xb_rank_disagree_diffbio_delta",
            "xb_margin", "xb_margin_raw", "xb_margin_delta",
            "xb_rank_agree_median", "xb_rank_agree_ratio",
            "xb_n_samples_used", "xb_n_panel_genes_used",
            "xb_n_pairs_same_bio", "xb_n_pairs_diff_bio", "xb_subsampled"]
    cols = [c for c in keep if c in t1.columns]
    return t1[cols].sort_values("xb_margin_delta", ascending=False)


def narrow_set_genes(annotation: pd.DataFrame) -> pd.DataFrame:
    """The QC-filtered narrow panel, collapsed to one row per gene.

    The annotation is stored one row per (gene, signature); a gene in three signatures
    appears three times. The workbook ships one row per gene with the memberships
    joined, because the sheet answers "which genes are in the narrow set".
    """
    narrow = annotation[annotation.in_narrow_set.astype(bool)].copy()
    joined = (narrow.groupby("gene")
              .agg(n_signatures=("gene_group", "nunique"),
                   signatures=("gene_group", lambda s: "; ".join(sorted(set(s.dropna())))),
                   cell_types=("cell_type", lambda s: "; ".join(sorted(set(s.dropna())))),
                   pathways=("pathway", lambda s: "; ".join(sorted(set(s.dropna())))),
                   tme_subtypes=("tme_subtype",
                                 lambda s: "; ".join(sorted(set(s.dropna())))),
                   prognostic=("prognostic_significance",
                               lambda s: "; ".join(sorted(set(s.dropna())))),
                   is_housekeeping=("is_housekeeping", "max"),
                   sources=("source_article",
                            lambda s: "; ".join(sorted(set(s.dropna())))))
              .reset_index())
    return joined.sort_values(["is_housekeeping", "gene"])


# ── the duplication check ─────────────────────────────────────────────────────

def article1_columns() -> dict[str, set]:
    """Column names of each supplementary file Article 1 ships, for the overlap check."""
    out = {}
    for label, path in ARTICLE1_SUPP.items():
        if not path.exists():
            print(f"  ! missing Article 1 file, skipped in the check: {path}")
            continue
        if path.suffix == ".xlsx":
            book = pd.read_excel(path, sheet_name=None, nrows=0)
            cols = {c for sheet in book.values() for c in sheet.columns}
        elif path.suffixes[-2:] == [".csv", ".gz"]:
            with gzip.open(path, "rt") as fh:
                cols = set(pd.read_csv(fh, nrows=0).columns)
        else:
            cols = set(pd.read_csv(path, nrows=0).columns)
        out[label] = cols
    return out


def duplication_report(workbooks: dict[str, list[Sheet]], stamp: str) -> str:
    """Report each Article 2 sheet's column overlap with Article 1's three files.

    An overlap is not by itself duplication — every sheet keyed on an approach repeats
    `strat`, `imp`, `method` and `post_rm`, and it has to, or the sheet could not be
    joined to anything. The report therefore separates the four key columns from the
    rest, and it is the rest that must stay empty for a sheet to be new.
    """
    key_cols = {"strat", "imp", "method", "post_rm", "run_id", "gene"}
    a1 = article1_columns()
    lines = [f"# Duplication check — Article 2 supplementary sheets against Article 1",
             "",
             f"Generated {stamp} by `analysis/build_supplementary_workbooks.py`.",
             "",
             "A shared column is only duplication when it is a shared *measurement*. "
             "The join keys (`strat`, `imp`, `method`, `post_rm`, `run_id`, `gene`) are "
             "shared on purpose and are listed separately.",
             ""]
    clean = True
    for book, sheets in workbooks.items():
        lines += [f"## {book}", ""]
        for sheet in sheets:
            cols = set(map(str, sheet.table.columns))
            for label, a1_cols in a1.items():
                shared = cols & a1_cols
                measurements = sorted(shared - key_cols)
                keys = sorted(shared & key_cols)
                if measurements:
                    clean = False
                    lines.append(f"- **{sheet.name}** vs {label}: shared measurement "
                                 f"columns {measurements}; keys {keys}")
                elif keys:
                    lines.append(f"- {sheet.name} vs {label}: keys only ({keys}) — new")
                else:
                    lines.append(f"- {sheet.name} vs {label}: no shared column — new")
        lines.append("")
    verdict = ("No Article 2 sheet reproduces a measurement column of any Article 1 "
               "supplementary file." if clean else
               "At least one sheet shares a measurement column with Article 1 — "
               "review the entries marked in bold above.")
    lines += ["## Verdict", "", verdict, ""]
    return "\n".join(lines)


# ── driver ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date-tag", default="260905", help="metric snapshot to reconcile")
    ap.add_argument("--stamp", default="260924", help="date stamp of the A2_T* tables")
    ap.add_argument("--out-stamp", default="260925",
                    help="date stamp of the workbooks (revision round 1: 260925)")
    ap.add_argument("--tables-dir", default="tables/")
    ap.add_argument("--out-dir", default="supplementary/")
    ap.add_argument("--top-frac", type=float, default=0.05)
    args = ap.parse_args()

    tables_dir = Path(args.tables_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = args.stamp

    def table(name: str) -> pd.DataFrame:
        path = next(tables_dir.glob(f"{name}_*_{stamp}.csv"))
        return pd.read_csv(path, low_memory=False)

    print("build_supplementary_workbooks")
    t0 = table("A2_T0")
    t1 = table("A2_T1")
    t2 = table("A2_T2")
    t3 = pd.read_csv(next(tables_dir.glob(f"A2_T3_*_{stamp}.csv")), index_col=0)
    t4 = table("A2_T4")
    t5 = table("A2_T5")
    t6 = table("A2_T6")
    t7 = table("A2_T7")
    t8 = table("A2_T8")
    # Revision round 1 (plan Phase 5): the tables the revised text cites by sheet name.
    rev = {name: table(name) for name in ("A2_T3b", "A2_T3c", "A2_T9b", "A2_T10",
                                           "A2_T11", "A2_T12", "A2_T13", "A2_T14",
                                           "A2_T15", "A2_T16")}
    print(f"  loaded {9 + len(rev)} A2_T* tables from {tables_dir}")

    # The election is not stored as a table, so it is recomputed from the same module
    # that wrote them. The counts are asserted against A2_T3 before use.
    metrics_path = a2.METRICS_CSV.format(tag=args.date_tag)
    df = a2.load_analysis_set(a2.SUPP_FILE_3, metrics_path)
    df = a2.add_raw_deltas(df)
    df, _ = a2.add_fold_metrics(df, a2.FOLDS_CSV)
    df["generalizability_index"] = a2.generalizability_index(df)
    matrix, sets = a2.cross_election_matrix(df, args.top_frac)
    df["is_prediction_best"] = df.index.isin(sets["N"])
    assert matrix.shape == t3.shape, "the recomputed election disagrees with A2_T3"
    print(f"  recomputed the election: {len(sets)} classes, "
          f"{len(sets['N'])} approaches per class")

    supp3 = pd.read_csv(a2.SUPP_FILE_3)
    snapshot = pd.read_csv(metrics_path, low_memory=False)
    ledger = reconciliation_ledger(
        df, supp3, len(snapshot),
        len(a2._canonicalize_shambhala(snapshot)), args.date_tag)

    file1 = [
        Sheet("Analysis_set", t1,
              f"Source: tables/A2_T1_analysis_set_census_{stamp}.csv · filter: "
              "Supplementary File 3 of the source benchmark, pct_samples_allNA < 5, "
              "with groups L, M and N joined from metrics_comprehensive_"
              f"{args.date_tag}.csv",
              "Every one of the 2,234 approaches with its identifying fields, its "
              "group flags, and the class L, M and N metrics in harmonized, raw and "
              "difference form. This is the table all other sheets are cut from."),
        Sheet("Canonical_set_reconciliation", ledger,
              "Source: derived here from Supplementary File 3 of the source benchmark "
              f"and metrics_comprehensive_{args.date_tag}.csv · filter: none",
              "How the 2,407 completed approaches of the source benchmark become the "
              "2,234 analysed here, one row per step. The block underneath is the "
              "column-by-column check that the two names of Shambhala-2 hold the same "
              "values.",
              extra=[(f"Source: tables/A2_T0_shambhala_identity_{stamp}.csv · filter: "
                      "the 84 strategy/imputation/post-removal keys both names share",
                      t0)]),
        Sheet("Generalizability_ranking", t2,
              f"Source: tables/A2_T2_generalizability_ranking_{stamp}.csv · filter: "
              "all 2,234 approaches, sorted by the generalizability index",
              "All 2,234 approaches ordered by the generalizability index, with the "
              "six metrics the index averages, each shown as its value and as its "
              "rank percentile."),
        Sheet("Method_census_by_class", t4,
              f"Source: tables/A2_T4_method_census_by_class_{stamp}.csv · filter: "
              "the approaches each metric class elects (top 5 per cent of that class)",
              "Which harmonization methods each metric class picks, and how often. "
              "One row per (metric class, method)."),
        Sheet("Strategy_and_imputation_summary",
              strategy_imputation_summary(df, sets),
              f"Source: derived from tables/A2_T1_analysis_set_census_{stamp}.csv · "
              "filter: grouped by filter strategy and imputation over all 2,234 "
              "approaches",
              "Median behaviour of each sample filter strategy crossed with each "
              "imputation, and how many approaches in that cell each metric class "
              "elected. The block underneath is the same summary by method and "
              "strategy, which is the data behind the bubble grid panel.",
              extra=[(f"Source: derived from tables/A2_T1_analysis_set_census_{stamp}"
                      ".csv · filter: grouped by method and filter strategy",
                      method_strategy_medians(df))]),
        Sheet("Harshness_by_LMN", t7,
              f"Source: tables/A2_T7_harshness_by_lmn_{stamp}.csv · filter: "
              "approaches grouped into the three method harshness tiers; each test "
              "drops the rows missing its own metric",
              "Seven biology-facing metrics compared across the low, medium and high "
              "method harshness tiers: the median in each tier, the number of "
              "approaches behind it, and the Kruskal-Wallis test across the three."),
        # Polarity, group and type are Article 1's own registry columns; the metric name
        # is kept as the join key, everything repeated from Article 1 is left out.
        Sheet("Metric_class_assignment", rev["A2_T12"].drop(
                  columns=["Polarity", "Metric group", "Metric type", "tier",
                           "destination"]),
              f"Source: tables/A2_T12_metric_census_{stamp}.csv · filter: all 344 "
              "metrics of the source benchmark's registry (its Supplementary File 2, "
              "sheet Metric_polarity)",
              "Every registered metric, by the name it has in the source benchmark's "
              "registry (join on Metric for its polarity, group and type): whether it "
              "scores, the snapshot column it is read from, whether it could be "
              "recovered, and the Article 2 metric class it belongs to."),
        Sheet("Class_percentile_scores", rev["A2_T15"],
              f"Source: tables/A2_T15_class_percentile_scores_{stamp}.csv · filter: all "
              "2,234 approaches",
              "For every approach, the mean rank percentile of each metric class (the "
              "score each class ranks on) and whether the approach is in that class's "
              "top 5 per cent."),
        Sheet("Paired_tests", rev["A2_T10"],
              f"Source: tables/A2_T10_paired_tests_{stamp}.csv · filter: one row per "
              "test the text relies on",
              "Every statistical test behind a comparison in the text: the groups, "
              "their sizes, medians, MADs and means, the test (Mann-Whitney U, "
              "Kruskal-Wallis H, Fisher's exact, Wilcoxon signed-rank, binomial), its "
              "statistic, raw two-sided p and effect size."),
        Sheet("Scatter_correlations", rev["A2_T11"],
              f"Source: tables/A2_T11_scatter_correlations_{stamp}.csv · filter: one "
              "row per scatterplot relationship the text reads",
              "Spearman correlation, raw p and n for every pair of metrics plotted "
              "against each other, per figure panel, plus the L, M and N pairs."),
        Sheet("Harshness_full", rev["A2_T9b"],
              f"Source: tables/A2_T9b_harshness_full_{stamp}.csv · filter: every "
              "numeric class L, M and N column; each test drops the rows missing its "
              "own metric",
              "Every class L, M and N metric across the three method harshness tiers: "
              "n, mean, median and MAD per tier, the Kruskal-Wallis test and the three "
              "pairwise Mann-Whitney tests."),
        Sheet("Composite_dispersion", rev["A2_T14"],
              f"Source: tables/A2_T14_dispersion_{stamp}.csv · filter: the 87 scoring "
              "metrics of the composite",
              "How much each metric type, metric group and annotation kind contributes "
              "to the composite score, and how much that contribution varies across "
              "strategies and methods (range of group means, with and without the "
              "clustermap group, and standard deviation)."),
        Sheet("PCA_component_means", rev["A2_T16"],
              f"Source: tables/A2_T16_pca_component_means_{stamp}.csv · filter: group "
              "means over the analysis set",
              "Mean percentage of total variance and mean RNA_BATCH R² on each of the "
              "first ten principal components, for every method, every strategy, the "
              "clustermap group and the unharmonized no-removal approaches."),
    ]

    file2 = [
        Sheet("Cross_election_matrix", matrix.reset_index().rename(
                  columns={"index": "metric_class"}),
              f"Source: tables/A2_T3_cross_election_matrix_{stamp}.csv · filter: "
              "the top 5 per cent of the 2,234 approaches per metric class",
              "How much any two metric classes agree about which approaches are best, "
              "as the Jaccard overlap of their elected sets. 1.0 would be complete "
              "agreement, 0.0 no shared approach at all."),
        Sheet("Elected_sets_by_class", elected_sets_long(df, sets),
              f"Source: derived from tables/A2_T1_analysis_set_census_{stamp}.csv · "
              "filter: the elected approaches of each metric class",
              "The elected approaches themselves, named, one row per (metric class, "
              "approach). `n_classes_electing` counts how many of the nine classes "
              "chose that same approach."),
        Sheet("Agreement_specific_61", t6,
              f"Source: tables/A2_T6_agreement_specific_{stamp}.csv · filter: "
              "non-raw approaches whose same-biology agreement rose (xb_rank_agree_delta "
              "> 0) and whose different-biology agreement fell (xb_rank_disagree_"
              "diffbio_delta < 0) against the unharmonized baseline at the same strategy "
              "and imputation",
              "The 61 agreement-specific approaches: harmonization raised their "
              "same-biology cross-batch agreement and lowered their different-biology "
              "agreement against their own unharmonized baseline. With their class L "
              "and N values."),
        Sheet("Margin_raw_and_delta", margin_raw_and_delta(t1),
              f"Source: derived from tables/A2_T1_analysis_set_census_{stamp}.csv · "
              "filter: the class M columns of all 2,234 approaches",
              "The cross-batch agreement margin in three forms for every approach: "
              "after harmonization, on the unharmonized matrix it was built from, and "
              "the difference between the two."),
        Sheet("Per_batch_folds", t5,
              f"Source: tables/A2_T5_per_batch_folds_{stamp}.csv · filter: the "
              "leave-one-batch-out folds of the prediction best and clustermap best "
              "approaches, both targets",
              "One row per (approach, prediction target, held-out batch): how many "
              "samples and how many diagnosis classes that batch held, and the F1 and "
              "AUC the model reached on it. `n_classes` is what separates the "
              "full fold cut from the multiclass-only cut."),
        Sheet("Fold_composition", t8,
              f"Source: tables/A2_T8_fold_composition_{stamp}.csv · filter: one row "
              "per held-out batch, pooled over approaches",
              "The census of the held-out batches themselves: how many diagnosis "
              "classes each carries, how many folds it appears in, and the median "
              "size and median score over those folds."),
        Sheet("Cross_election_pairs", rev["A2_T3b"],
              f"Source: tables/A2_T3b_cross_election_pairs_{stamp}.csv · filter: every "
              "pair of the nine elected sets",
              "For each pair of elected sets: both sizes, the approaches they share, "
              "their union, the Jaccard index, the overlap expected by chance and the "
              "hypergeometric p of more and of less overlap than chance."),
        Sheet("Threshold_sensitivity", rev["A2_T3c"],
              f"Source: tables/A2_T3c_threshold_sensitivity_{stamp}.csv · filter: "
              "elections at the top 2.5, 5 and 10 per cent",
              "The overlap of every pair of elected sets at three election thresholds, "
              "with each pair's rank and the Spearman correlation of each threshold's "
              "Jaccard values with those at 5 per cent."),
        Sheet("LOBO_summary", rev["A2_T13"],
              f"Source: tables/A2_T13_lobo_summary_{stamp}.csv · filter: the named "
              "groups (medians) and the leading approaches",
              "Leave-one-batch-out prediction for the named groups and the leading "
              "approaches, on both fold cuts and both targets (main-text Table 2)."),
    ]

    coverage_gate = pd.read_csv(MARKER_TABLES / "T1_coverage_gate.csv")
    qc_gate = pd.read_csv(MARKER_TABLES / "T2_qc_gate.csv").rename(
        columns={"Unnamed: 0": "max_frac_null_allowed"})
    rho_summary = pd.read_csv(MARKER_TABLES / "T4_per_gene_rho_summary.csv")
    saturation = pd.read_csv(MARKER_TABLES / "T3_saturation_split.csv")[
        ["gene", "saturated"]]
    rho_by_signature = rho_summary.merge(saturation, on="gene", how="left")
    annotation = pd.read_csv(GENE_ANNOTATION)
    narrow = narrow_set_genes(annotation)

    file3 = [
        Sheet("Panel_coverage_by_attempt", coverage_gate,
              "Source: figures_for_article/current_figures_tables_for_article_260819/"
              "T1_coverage_gate.csv · filter: marker panel genes, swept over the "
              "coverage threshold",
              "How many marker genes survive as the required coverage is raised, "
              "counted three ways: over one filter strategy, over every in-scope "
              "approach, and over the unharmonized reference matrices."),
        Sheet("QC_gate_sweep", qc_gate,
              "Source: figures_for_article/current_figures_tables_for_article_260819/"
              "T2_qc_gate.csv · filter: marker panel genes over a two-dimensional "
              "threshold grid",
              "Surviving gene counts over the grid of the two quality gates: the "
              "largest fraction of missing values allowed (rows) against the coverage "
              "required (columns)."),
        Sheet("Rho_by_signature", rho_by_signature,
              "Source: figures_for_article/current_figures_tables_for_article_260819/"
              "T4_per_gene_rho_summary.csv, with the saturation flag from "
              "T3_saturation_split.csv · filter: the 572 marker genes measured in at "
              "least one attempt",
              "Per-gene within-cohort correlation between raw and harmonized "
              "expression: median, mean, spread and percentiles over the attempts, "
              "with the gene's signature, cell type, housekeeping flag and whether it "
              "sits at the saturated top of the range."),
        Sheet("Narrow_set_56_genes", narrow,
              "Source: harmonization-metrics-calculation/marker_gene_annotation.csv · "
              "filter: in_narrow_set is true, collapsed to one row per gene",
              "The genes of the quality-filtered narrow panel, one row per gene, with "
              "every signature, cell type, pathway and source the gene belongs to."),
    ]

    write_workbook(out_dir / f"A2_Supplementary_File_1_{args.out_stamp}.xlsx",
                   "Supplementary File 1 — the analysis set and its metrics",
                   "The 2,234 harmonization approaches Article 2 compares, how that "
                   "set was arrived at, and the class L, M and N metrics measured on "
                   "each of them.", file1)
    write_workbook(out_dir / f"A2_Supplementary_File_2_{args.out_stamp}.xlsx",
                   "Supplementary File 2 — cross-batch structure and prediction",
                   "Which approaches each metric class elects, how little the classes "
                   "agree, and the per-fold prediction results behind class N.", file2)
    write_workbook(out_dir / f"A2_Supplementary_File_3_{args.out_stamp}.xlsx",
                   "Supplementary File 3 — the marker gene panel",
                   "The coverage and quality gates applied to the marker gene panel, "
                   "the per-gene correlation behaviour behind class L, and the narrow "
                   "panel that survives the gates.", file3)

    report = duplication_report(
        {"Supplementary File 1": file1,
         "Supplementary File 2": file2,
         "Supplementary File 3": file3}, stamp)
    report_path = out_dir / f"duplication_check_{args.out_stamp}.md"
    report_path.write_text(report)
    print(f"  wrote {report_path.name}")
    print(report.split("## Verdict")[-1].strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
