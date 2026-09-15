"""Build the 26 standalone tables that sit beside the ZIP bundles in the record.

Three groups:

* **metric tables** — copied from the private tree or from S3, filtered to the 33
  deposited methods and renamed so the single deposited Shambhala configuration is
  called ``20_shambhala``, exactly as the article's Supplementary File 3 already does;
* **registries** — the metric dictionary, the method registry and the strategy
  registry, so the record is self-describing without the manuscript;
* **source data** — the raw public expression matrix, the redacted annotation, the
  cohort table and the per-strategy sample/gene selection tables.

Nothing here is written to the local Mac: run it on the build host, where
``repo_root`` points at the checkout and everything else is streamed from S3.
"""

from __future__ import annotations

import csv
import gzip
import io
import shutil
import zlib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

import redact_lib as R
from zenodo_manifest import (
    EXPECTED_COUNTS,
    EXPECTED_METRIC_ROWS,
    EXPECTED_PUBLIC_ROWS,
    IMPUTATIONS,
    SHAMBHALA_PUB,
    SHAMBHALA_S3,
    STRATEGIES,
    public_method,
)

SUPP_DIR = Path("figures_for_article") / "supplementary_260824"
SUPP_XLSX = SUPP_DIR / "Supplementary File 2.xlsx"
COHORT_SHORT = SUPP_DIR / "Supplementary File 1 short.csv"
MASTER_ANN_KEY = "prepared/S0_no_removal__strict__ann.tsv.gz"
RAW_EXP_KEY = "exp/comb_exp.tsv"


@dataclass
class TableSpec:
    """One standalone table: where it comes from and how it is filtered.

    Attributes
    ----------
    out_name : str
        Filename in the deposit.
    local : str | None
        Path relative to the repository root; tried first.
    s3_key : str | None
        Key relative to the FL_batch_correction prefix; the fallback.
    mode : str
        "runid" filters on a run_id column, "cols" on strat/imp/method columns,
        "none" copies through untouched.
    gzip_out : bool
        Whether the deposited copy is gzipped.
    """

    out_name: str
    local: str | None
    s3_key: str | None
    mode: str = "none"
    gzip_out: bool = False


METRIC_TABLES: tuple[TableSpec, ...] = (
    TableSpec("metrics_comprehensive_260905.csv",
              "harmonization-metrics/metric_tables/metrics_comprehensive_260905.csv",
              "metrics_comprehensive.csv", mode="cols"),
    TableSpec("marker_gene_correlations_long_260905.csv.gz",
              "harmonization-metrics/metric_tables/marker_gene_correlations_long.csv",
              "marker_gene_correlations_long.csv", mode="runid", gzip_out=True),
    TableSpec("marker_cohort_correlations_long_260905.csv.gz",
              "harmonization-metrics/metric_tables/marker_cohort_correlations_long.csv",
              "marker_cohort_correlations_long.csv", mode="runid", gzip_out=True),
    TableSpec("prediction_folds_long_260905.csv.gz",
              "harmonization-metrics/metric_tables/prediction_folds_long.csv",
              "prediction_folds_long.csv", mode="runid", gzip_out=True),
    TableSpec("gene_qc_long_260828.csv.gz",
              None, "gene_qc_long.csv.gz", mode="runid", gzip_out=True),
    TableSpec("gene_gene_consensus_within_260828.csv.gz",
              "harmonization-metrics/metric_tables/"
              "gene_gene_consensus_within_260828.csv.gz", None, gzip_out=True),
    TableSpec("gene_gene_consensus_global_260828.csv.gz",
              "harmonization-metrics/metric_tables/"
              "gene_gene_consensus_global_260828.csv.gz", None, gzip_out=True),
    TableSpec("gene_gene_consensus_sd_260828.csv.gz",
              "harmonization-metrics/metric_tables/"
              "gene_gene_consensus_sd_260828.csv.gz", None, gzip_out=True),
    TableSpec("gene_gene_consensus_n_260828.csv.gz",
              "harmonization-metrics/metric_tables/"
              "gene_gene_consensus_n_260828.csv.gz", None, gzip_out=True),
    TableSpec("marker_gene_coverage_by_attempt_260828.csv",
              "harmonization-metrics/metric_tables/"
              "marker_gene_coverage_by_attempt_260828.csv", None),
    TableSpec("gene_level_stats_260905.csv",
              "harmonization-metrics/metric_tables/gene_level_stats_260905.csv", None),
    TableSpec("marker_gene_annotation.csv",
              "harmonization-metrics-calculation/marker_gene_annotation.csv", None),
)


# ── Method filtering and the 20_shambhala rename ─────────────────────────────


def is_deposited_method(method: str) -> bool:
    """True for the 32 non-Shambhala methods and the default Shambhala pair."""
    return not method.startswith("shambhala") or method == SHAMBHALA_S3


def rename_run_id(run_id: str) -> str:
    """Rewrite an S3 run identifier into its deposited form."""
    strat, imp, method, post = run_id.split("__")
    return f"{strat}__{imp}__{public_method(method)}__{post}"


def _open_source(spec: TableSpec, repo_root: Path, client) -> io.TextIOBase:
    """Open a table from the repository if present, otherwise from S3."""
    if spec.local:
        path = repo_root / spec.local
        if path.exists():
            if path.suffix == ".gz":
                return gzip.open(path, "rt", newline="")
            return path.open("rt", newline="")
    if not spec.s3_key:
        raise FileNotFoundError(f"{spec.out_name}: no local copy and no S3 fallback")
    body = R.open_s3_stream(spec.s3_key, client=client)
    if spec.s3_key.endswith(".gz"):
        return io.TextIOWrapper(gzip.GzipFile(fileobj=body, mode="rb"), newline="")
    return io.TextIOWrapper(body, newline="")


def _open_dest(path: Path, gzip_out: bool) -> io.TextIOBase:
    if gzip_out:
        return gzip.open(path, "wt", compresslevel=6, newline="")
    return path.open("wt", newline="")


def build_metric_tables(out_dir: Path, repo_root: Path, client=None) -> list[dict]:
    """Copy, filter and rename every metric table into the deposit directory.

    Filtering is line-wise rather than DataFrame-wise so that `gene_qc_long`
    (123 MB gzipped, tens of millions of rows) never has to fit in memory.

    Returns
    -------
    list[dict]
        One record per table: name, rows in, rows out, bytes.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    report: list[dict] = []
    for spec in METRIC_TABLES:
        dest = out_dir / spec.out_name
        rows_in = rows_out = 0
        with _open_source(spec, repo_root, client) as src, \
                _open_dest(dest, spec.gzip_out) as dst:
            if spec.mode == "none":
                shutil.copyfileobj(src, dst)
            else:
                reader = csv.reader(src)
                header = next(reader)
                writer = csv.writer(dst, lineterminator="\n")
                writer.writerow(header)
                if spec.mode == "runid":
                    col = header.index("run_id")
                    for row in reader:
                        rows_in += 1
                        method = row[col].split("__")[2]
                        if not is_deposited_method(method):
                            continue
                        row[col] = rename_run_id(row[col])
                        writer.writerow(row)
                        rows_out += 1
                else:                                   # mode == "cols"
                    m_col = header.index("method")
                    r_col = header.index("run_id") if "run_id" in header else None
                    for row in reader:
                        rows_in += 1
                        if not is_deposited_method(row[m_col]):
                            continue
                        row[m_col] = public_method(row[m_col])
                        if r_col is not None:
                            row[r_col] = rename_run_id(row[r_col])
                        writer.writerow(row)
                        rows_out += 1
        report.append({"file": spec.out_name, "rows_in": rows_in,
                       "rows_out": rows_out, "bytes": dest.stat().st_size})
        if spec.out_name.startswith("metrics_comprehensive"):
            if rows_out != EXPECTED_METRIC_ROWS:
                raise ValueError(
                    f"metrics_comprehensive has {rows_out} rows after filtering, "
                    f"expected {EXPECTED_METRIC_ROWS} — the same run set as "
                    f"Supplementary File 3"
                )
    return report


# ── Registries ───────────────────────────────────────────────────────────────


def build_registries(out_dir: Path, repo_root: Path,
                     coverage: dict[str, int] | None = None) -> None:
    """Write metric_dictionary.csv, methods_registry.csv, strategies_registry.csv.

    The first two are lifted from `Supplementary File 2.xlsx`, which already holds
    the manuscript-grade curated versions (`Metric_polarity` 345 x 6,
    `Table_S2_metrics` 28 x 5, `Table_S1_methods` 40 x 11) — re-deriving them from
    the source code would produce a second, divergent description of the same thing.

    Parameters
    ----------
    coverage : dict[str, int] | None
        Public method name -> number of S3 outputs, appended to the method registry
        so a reader can see that e.g. `22_tmm` ran on 6 combinations by design.
    """
    xlsx = repo_root / SUPP_XLSX

    polarity = pd.read_excel(xlsx, sheet_name="Metric_polarity")
    groups = pd.read_excel(xlsx, sheet_name="Table_S2_metrics")
    polarity.to_csv(out_dir / "metric_dictionary.csv", index=False)
    groups.to_csv(out_dir / "metric_group_definitions.csv", index=False)

    methods = pd.read_excel(xlsx, sheet_name="Table_S1_methods")
    name_col = methods.columns[0]
    methods[name_col] = methods[name_col].replace({SHAMBHALA_S3: SHAMBHALA_PUB})
    methods = methods[methods[name_col].astype(str).str.match(r"^\d{2}_")]
    if coverage:
        methods["n_outputs_deposited_set"] = methods[name_col].map(coverage).fillna(0)
        methods["n_outputs_deposited_set"] = (
            methods["n_outputs_deposited_set"].astype(int)
        )
    methods.to_csv(out_dir / "methods_registry.csv", index=False)

    rows = []
    for strat in STRATEGIES:
        total, public = EXPECTED_COUNTS[strat]
        rows.append({
            "strategy": strat,
            "n_samples_total": total,
            "n_samples_public": public,
            "n_samples_withheld": total - public,
            "pct_public": round(100 * public / total, 1),
        })
    pd.DataFrame(rows).to_csv(out_dir / "strategies_registry.csv", index=False)
    pd.DataFrame(rows).to_csv(out_dir / "strategy_sample_counts.csv", index=False)


# ── Source data ──────────────────────────────────────────────────────────────


def gz_header_from_s3(key: str, client=None, probe_bytes: int = 4_000_000) -> list[str]:
    """Read only the header line of a gzipped S3 TSV, without downloading it.

    A ranged GET plus a partial inflate is enough: the header of even the widest
    matrix (21,890 genes) lands well inside the first few megabytes.
    """
    client = client or R.s3_client()
    full_key = f"{R.S3_PREFIX}/{key}"
    body = client.get_object(
        Bucket=R.s3_bucket(), Key=full_key, Range=f"bytes=0-{probe_bytes}"
    )["Body"].read()
    text = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(body).decode(
        "utf8", "replace"
    )
    return text.split("\n", 1)[0].split("\t")


def build_source_tables(out_dir: Path, repo_root: Path, prop_ids: set[str],
                        whitelist: list[str], legacy: str | None = None,
                        client=None, decimals: int = 4) -> dict:
    """Write the raw public matrix, the annotation, and the selection tables.

    Returns
    -------
    dict
        Row and column counts for the verification log.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    client = client or R.s3_client()
    report: dict = {}

    shutil.copyfile(repo_root / COHORT_SHORT, out_dir / "cohorts.csv")

    dest = out_dir / "comb_ann_public.csv"
    with dest.open("wt", newline="") as fh:
        kept, dropped = R.redact_annotation(
            MASTER_ANN_KEY, fh, prop_ids, whitelist,
            legacy=legacy, sep="\t", out_sep=",", client=client,
        )
    report["comb_ann_public"] = {"rows": kept, "dropped": dropped,
                                 "cols": len(whitelist)}
    if kept != EXPECTED_PUBLIC_ROWS:
        raise ValueError(f"comb_ann_public has {kept} rows, "
                         f"expected {EXPECTED_PUBLIC_ROWS}")

    # The raw matrix predates the cohort's QC: it holds 63 public samples the final
    # 7,174-sample cohort dropped and one sample twice. Restricting it to the
    # annotation's own sample set is what makes the two files joinable.
    cohort_ids = set(
        pd.read_csv(out_dir / "comb_ann_public.csv", usecols=[0], dtype=str)
        .iloc[:, 0]
    )

    dest = out_dir / "comb_exp_public.tsv.gz"
    body = R.open_s3_stream(RAW_EXP_KEY, client=client)
    with gzip.open(dest, "wt", compresslevel=6, newline="") as fh:
        kept, dropped = R.redact_and_round(
            body, fh, prop_ids, decimals=decimals, gzipped=False,
            keep_ids=cohort_ids,
        )
    report["comb_exp_public"] = {"rows": kept, "dropped": dropped,
                                 "bytes": dest.stat().st_size}
    if kept != EXPECTED_PUBLIC_ROWS:
        raise ValueError(f"comb_exp_public has {kept} rows, "
                         f"expected {EXPECTED_PUBLIC_ROWS}")

    selection: dict[str, set[str]] = {}
    for strat in STRATEGIES:
        key = f"prepared/{strat}__strict__ann.tsv.gz"
        with gzip.GzipFile(
            fileobj=R.open_s3_stream(key, client=client), mode="rb"
        ) as raw:
            reader = csv.reader(io.TextIOWrapper(raw, newline=""), delimiter="\t")
            next(reader)
            selection[strat] = {r[0] for r in reader if r[0] not in prop_ids}
        if len(selection[strat]) != EXPECTED_COUNTS[strat][1]:
            raise ValueError(
                f"{strat}: {len(selection[strat])} public samples, "
                f"expected {EXPECTED_COUNTS[strat][1]}"
            )
    all_samples = sorted(selection["S0_no_removal"])
    frame = pd.DataFrame(
        {strat: [s in selection[strat] for s in all_samples] for strat in STRATEGIES},
        index=pd.Index(all_samples, name="sample"),
    )
    frame.to_csv(out_dir / "sample_selection_by_strategy.csv")
    report["sample_selection"] = {"rows": len(frame), "cols": frame.shape[1]}

    rows = []
    for strat in STRATEGIES:
        for imp in IMPUTATIONS:
            genes = gz_header_from_s3(
                f"prepared/{strat}__{imp}__exp.tsv.gz", client=client
            )[1:]
            rows.extend({"strat": strat, "imp": imp, "gene": g} for g in genes)
    with gzip.open(out_dir / "gene_selection_by_pair.csv.gz", "wt",
                   compresslevel=6, newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["strat", "imp", "gene"],
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    report["gene_selection"] = {"rows": len(rows)}

    return report
