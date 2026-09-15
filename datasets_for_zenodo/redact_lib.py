"""Every transform applied to a deposited file, in one auditable place.

Two rules from the release plans govern this module:

R2  No expression and no annotation from a proprietary cohort may be published,
    including sample names. Redaction is row-wise for expression, and row-wise *plus*
    column-wise for annotation — a row filter is not a redaction, because a surviving
    row can still name a proprietary sample in one of its cells.
R3  An internal, unpublished label is removed from *every* annotation column. It is a
    label rename only; no sample changes group, so no published count moves. Sweeping
    all columns rather than the two originally named ones is deliberate: the first
    build found the label in a third column the schema audit had not looked at, and
    the forbidden-token grep treats an occurrence anywhere as a leak. The label itself
    is not written here — this module is destined for the public mirror, and naming it
    would defeat the removal. Supply it with --legacy-label / FL_LEGACY_LABEL when
    building, and rely on ``verify_bundle.py`` to fail loudly if it was forgotten.
"""

from __future__ import annotations

import contextlib
import csv
import gzip
import os
import re
from pathlib import Path
from typing import IO

import pandas as pd

from zenodo_manifest import (
    EXPECTED_ANN_COLUMNS,
    EXPECTED_PROP_COHORTS,
    EXPECTED_PROP_IDS,
    EXPECTED_PUBLIC_ROWS,
)

S3_PREFIX = os.environ.get("FL_S3_PREFIX", "FL_batch_correction")


def s3_bucket() -> str:
    """The bucket holding the harmonization outputs, from ``FL_S3_BUCKET``.

    Deliberately has no default. The bucket name is site-specific and this file
    is public; the mirror's convention is an explicit export (see the repository
    README, ``export FL_S3_BUCKET=your-bucket``). Resolved lazily rather than at
    import time so that ``test_transforms.py``, which touches no S3, runs on a
    laptop with no AWS configuration at all.

    Raises
    ------
    RuntimeError
        When the variable is unset or empty.
    """
    bucket = os.environ.get("FL_S3_BUCKET")
    if not bucket:
        raise RuntimeError(
            "FL_S3_BUCKET is not set - export the bucket holding "
            f"{S3_PREFIX}/ before building the deposit"
        )
    return bucket


SOT_DIR = Path("figures_for_article") / "supplementary_260824"
SHORT_NAME = "Supplementary File 1 short.csv"
FULL_NAME = "Supplementary File 1.csv"

# Dropped outright: a third-party work e-mail, 4,468 cells and one distinct value.
# It identifies a colleague and carries no analytical information.
ANN_DROP = ("AUTHOR",)

# Renamed to say what the column holds rather than which internal system produced it.
# The values are untouched: `bcell_type_call` holds ordinary cell-type names, and
# `treatment_regimen_detail` is the deposit's only source of regimen detail (1,271
# values, disjoint from TREATMENT_REGIMEN).
ANN_RENAME = {
    "bags_class": "bcell_type_call",
    "avicennaid": "treatment_regimen_detail",
}

LEGACY_LABEL_REPLACEMENT = "Normal_B_cells"
SAMPLE_LABEL_COL = "PUBLIC_SAMPLE_LABEL"


def legacy_label(explicit: str | None = None) -> str | None:
    """The internal group label to rename, from --legacy-label or FL_LEGACY_LABEL."""
    return explicit or os.environ.get("FL_LEGACY_LABEL") or None


# ── Proprietary identifiers ──────────────────────────────────────────────────


def derive_prop_ids(root: str | Path = "..") -> set[str]:
    """Re-derive the proprietary sample identifiers from the supplementary tables.

    Never typed and never cached into git: the cohort classification lives in
    `Supplementary File 1 short.csv` and the sample-to-cohort mapping in
    `Supplementary File 1.csv`, so the set is reproducible by anyone holding the
    unredacted tree.

    Parameters
    ----------
    root : str | Path
        Repository root holding `figures_for_article/supplementary_260824/`.

    Returns
    -------
    set[str]
        The 1,996 proprietary sample identifiers.
    """
    root = Path(root)
    short = root / SOT_DIR / SHORT_NAME
    full = root / SOT_DIR / FULL_NAME
    with open(short, newline="") as fh:
        prop_cohorts = {
            r["COHORT_LABEL"].strip()
            for r in csv.DictReader(fh)
            if r["Cohort type"].strip() == "Proprietary"
        }
    with open(full, newline="") as fh:
        rows = list(csv.DictReader(fh))
    key = list(rows[0].keys())[0]
    ids = {r[key] for r in rows if r["COHORT_LABEL"] in prop_cohorts}
    if len(prop_cohorts) != EXPECTED_PROP_COHORTS or len(ids) != EXPECTED_PROP_IDS:
        raise ValueError(
            f"expected {EXPECTED_PROP_COHORTS} cohorts / {EXPECTED_PROP_IDS} ids, "
            f"got {len(prop_cohorts)} / {len(ids)}"
        )
    return ids


# ── S3 access ────────────────────────────────────────────────────────────────


def s3_client():
    """A boto3 S3 client, created lazily so the module imports without boto3."""
    import boto3

    return boto3.client("s3")


def open_s3_stream(key: str, client=None) -> IO[bytes]:
    """Open an S3 object as a binary stream, never writing it to disk.

    Parameters
    ----------
    key : str
        Key relative to the FL_batch_correction prefix, e.g.
        "prepared/S0_no_removal__strict__ann.tsv.gz".
    client : optional
        An existing boto3 S3 client; one is created if omitted.

    Returns
    -------
    IO[bytes]
        The object body. Sequential reads only — it is not seekable.
    """
    client = client or s3_client()
    full_key = key if key.startswith(S3_PREFIX) else f"{S3_PREFIX}/{key}"
    return client.get_object(Bucket=s3_bucket(), Key=full_key)["Body"]


def _open_any(source: str | Path | IO[bytes], client=None) -> IO[bytes]:
    """Open a local path or an S3 key as a binary stream."""
    if hasattr(source, "read"):
        return source                                    # already a stream
    path = Path(source)
    if path.exists():
        return path.open("rb")
    return open_s3_stream(str(source), client=client)


# ── The annotation column whitelist ──────────────────────────────────────────


def _is_empty(series: pd.Series) -> bool:
    """True when a column holds no content for any row.

    Note the shape of this predicate. The obvious one-liner
    ``not df[c].astype(str).str.strip().any()`` drops ZERO columns, because
    ``astype(str)`` renders NaN as the non-empty string "nan", which is truthy.
    Drop the NaNs first, then test for content.
    """
    values = series.dropna().astype(str).str.strip()
    return not (values != "").any()


def annotation_whitelist(
    source: str | Path | IO[bytes],
    prop_ids: set[str],
    sep: str = "\t",
    client=None,
) -> list[str]:
    """Compute the fixed column whitelist shared by every deposited annotation.

    Derived once from the master annotation restricted to all 5,178 public rows:
    485 annotation columns beside the sample-ID index, 293 of them empty for every
    public sample, minus `AUTHOR` leaves 191 — a deposited file of 192 columns once
    the index is written back, which is the figure the public mirror quotes.
    Computing the whitelist per strategy instead would yield a different schema per
    file (172 columns for A_confirmed_bad's 4,071 rows) and make two deposited
    annotations impossible to concatenate.

    Parameters
    ----------
    source : str | Path | IO[bytes]
        Local path, S3 key, or open stream of the master annotation — in practice
        `prepared/S0_no_removal__strict__ann.tsv.gz`.
    prop_ids : set[str]
        The proprietary sample identifiers.
    sep : str
        Field separator of the source table.
    client : optional
        boto3 S3 client to reuse.

    Returns
    -------
    list[str]
        The 191 surviving column names, in their original order.
    """
    with gzip.GzipFile(fileobj=_open_any(source, client), mode="rb") as raw:
        df = pd.read_csv(raw, sep=sep, index_col=0, dtype=str,
                         keep_default_na=False, low_memory=False)
    public = df.loc[~df.index.isin(prop_ids)]
    if len(public) != EXPECTED_PUBLIC_ROWS:
        raise ValueError(
            f"master annotation has {len(public)} public rows, "
            f"expected {EXPECTED_PUBLIC_ROWS}"
        )
    keep = [c for c in public.columns if not _is_empty(public[c])]
    keep = [c for c in keep if c not in ANN_DROP]
    if len(keep) != EXPECTED_ANN_COLUMNS:
        raise ValueError(
            f"whitelist has {len(keep)} columns, expected {EXPECTED_ANN_COLUMNS}"
        )
    return keep


# ── The two transforms ───────────────────────────────────────────────────────


def redact_annotation(
    source: str | Path | IO[bytes],
    dst_fileobj: IO[str],
    prop_ids: set[str],
    whitelist: list[str],
    legacy: str | None = None,
    sep: str = "\t",
    out_sep: str | None = None,
    client=None,
) -> tuple[int, int]:
    """Redact one annotation table row-wise and column-wise.

    Applies, in order: the proprietary row filter; the fixed column whitelist; the
    blanking of proprietary sample names that survive the row filter in a *cell*
    (76 of them, on PUB_FL_HORN rows); the R3 group-label rename; and the two
    column renames of :data:`ANN_RENAME`.

    Parameters
    ----------
    source : str | Path | IO[bytes]
        Local path, S3 key, or open binary stream of a gzip table.
    dst_fileobj : IO[str]
        Open text destination — in practice a member handle inside the bundle ZIP.
    prop_ids : set[str]
        The proprietary sample identifiers.
    whitelist : list[str]
        Column names from :func:`annotation_whitelist`.
    legacy : str | None
        The internal group label to rename; skipped when None.
    sep, out_sep : str
        Input and output field separators; ``out_sep`` defaults to ``sep``.
    client : optional
        boto3 S3 client to reuse.

    Returns
    -------
    tuple[int, int]
        (rows kept, rows dropped).
    """
    with gzip.GzipFile(fileobj=_open_any(source, client), mode="rb") as raw:
        df = pd.read_csv(raw, sep=sep, index_col=0, dtype=str,
                         keep_default_na=False, low_memory=False)
    total = len(df)
    df = df.loc[~df.index.isin(prop_ids)]
    df = df[[c for c in whitelist if c in df.columns]]

    if SAMPLE_LABEL_COL in df.columns:
        df.loc[df[SAMPLE_LABEL_COL].isin(prop_ids), SAMPLE_LABEL_COL] = ""

    if legacy:
        # Token-bounded so a cohort label that merely ends in the same word — a real,
        # published GEO cohort does — is left alone, while the bare label and any
        # `<label>_suffix` value are renamed in whichever column they turn up in.
        token = re.compile(
            rf"(?<![A-Za-z0-9]){re.escape(legacy)}(?![A-Za-z0-9])"
        )
        # A cell holding the label and nothing else still carries the separator that
        # would have joined it to a second field: `Diagnosis_with_coo` is
        # diagnosis + cell-of-origin, and normal B cells have no cell of origin, so
        # 734 rows read `<label>_`. Renaming the token alone leaves a dangling
        # `Normal_B_cells_`, which is what the mirror's independently written script
        # does not produce. Strip exactly that, and only that.
        dangling = re.compile(rf"^{re.escape(LEGACY_LABEL_REPLACEMENT)}_$")
        for column in df.columns:
            df[column] = df[column].str.replace(
                token, LEGACY_LABEL_REPLACEMENT, regex=True
            ).str.replace(dangling, LEGACY_LABEL_REPLACEMENT, regex=True)

    df = df.rename(columns=ANN_RENAME)
    df.to_csv(dst_fileobj, sep=out_sep or sep)
    return len(df), total - len(df)


def redact_and_round(
    src_stream: IO[bytes],
    dst_fileobj: IO[str],
    prop_ids: set[str],
    decimals: int = 4,
    chunk_rows: int = 256,
    gzipped: bool = True,
    keep_ids: set[str] | None = None,
) -> tuple[int, int]:
    """Drop proprietary rows and round values, streaming a samples x genes TSV.

    Parameters
    ----------
    src_stream : IO[bytes]
        An open S3 ``get_object()["Body"]`` (or any binary stream) holding a gzip
        TSV, samples x genes, first column = sample ID under an empty header cell.
    dst_fileobj : IO[str]
        An open text-mode gzip writer — in practice a member handle inside the
        bundle ZIP, so the transformed matrix is never a separate file on disk.
    prop_ids : set[str]
        The 1,996 proprietary sample identifiers.
    decimals : int
        Decimal places for `float_format`; 4 bounds the absolute error at 5e-5.
    chunk_rows : int
        Rows per pandas chunk. 256 x 21,890 float64 is ~45 MB, so peak RSS stays
        flat regardless of matrix size.
    gzipped : bool
        False for the one plain-TSV input in the deposit, `exp/comb_exp.tsv`.
    keep_ids : set[str] | None
        When given, rows are additionally restricted to these identifiers and a
        repeated identifier is written only once. Used for the raw matrix, whose
        sample set is wider than the final cohort's; None for the prepared and
        harmonized layers, which are already exactly the cohort.

    Returns
    -------
    tuple[int, int]
        (rows kept, rows dropped).
    """
    kept = dropped = 0
    first = True
    seen: set[str] = set()
    raw_cm = (gzip.GzipFile(fileobj=src_stream, mode="rb") if gzipped
              else contextlib.nullcontext(src_stream))
    with raw_cm as raw:
        for chunk in pd.read_csv(raw, sep="\t", index_col=0, chunksize=chunk_rows):
            mask = ~chunk.index.isin(prop_ids)
            if keep_ids is not None:
                # The raw pre-QC matrix carries samples that the final cohort later
                # dropped, and one sample twice. Restricting to the annotation's own
                # sample set, first occurrence wins, keeps the deposited matrix
                # joinable to the deposited annotation row for row.
                mask &= chunk.index.isin(keep_ids) & ~chunk.index.isin(seen)
                seen.update(chunk.index[mask])
            dropped += int((~mask).sum())
            kept += int(mask.sum())
            sub = chunk.loc[mask]
            if sub.empty and not first:
                continue
            # header=first writes it exactly once; pandas emits an empty first
            # header cell for an unnamed index, reproducing the S3 header shape.
            sub.to_csv(dst_fileobj, sep="\t", header=first,
                       float_format=f"%.{decimals}f", na_rep="")
            first = False
    return kept, dropped
