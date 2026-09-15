"""Audit a finished bundle before it is uploaded, and after it lands on Zenodo.

Verification has to happen *inline*, one bundle at a time: the build host has ~10 GB
free and the deposit is ~45 GB, so there is never a moment when the whole payload
exists to be audited at the end. Every check below therefore runs against a single
closed ZIP, before that ZIP is uploaded and deleted.

The module is importable (``verify_bundle(...)`` is what the builder calls) and also
runs standalone over ``work/*.zip``.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import os
import random
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

import redact_lib as R
from zenodo_manifest import (
    EXPECTED_ANN_COLUMNS,
    EXPECTED_COUNTS,
    MAX_FILES,
    MAX_RECORD_GB,
    SHORT_POST0_PUBLIC_ROWS,
    s3_method,
)

# Every token that must not reach a public file.
#
# Only the *generic* tokens are written here. Two are internal-schema column names that
# this repository already documents by name in DATA_AVAILABILITY.md, so naming them
# costs nothing; the third catches the 17 non-default Shambhala calibration variants,
# which is also what keeps the internal group label out of the deposit.
#
# The site-specific tokens — an internal bucket or container-registry name, a cluster
# pod prefix, a work e-mail, and the R3 group label itself — are deliberately *not*
# written here. This file is public, and spelling those tokens out would defeat the
# removal they exist to enforce, exactly as `redact_lib.legacy_label()` already avoids
# doing for the group label. Supply them at build time:
#
#     export FL_LEGACY_LABEL=<the R3 group label>
#     export FL_FORBIDDEN_EXTRA=<comma-separated further tokens>
#
# `main()` warns when neither is set, because an unconfigured run still passes every
# check and is therefore the one failure mode that looks like success.
GENERIC_FORBIDDEN = (
    # `shambhala_` followed by an alphanumeric is a raw calibration-variant name
    # (`shambhala_NBKass_Q0std`). The one deposited configuration is renamed to
    # `20_shambhala`, where the next character is the `__` field separator — the
    # earlier `shambhala_(?!P0std)` spelling rejected every legitimate member.
    r"bags_class|avicennaid|shambhala_[A-Za-z0-9]"
)


def site_tokens() -> list[str]:
    """Site-specific forbidden tokens, from FL_FORBIDDEN_EXTRA and FL_LEGACY_LABEL.

    Returns
    -------
    list[str]
        Literal tokens, unescaped. Empty when neither variable is set, which leaves
        only the generic checks in force.
    """
    raw = os.environ.get("FL_FORBIDDEN_EXTRA", "")
    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    legacy = R.legacy_label()
    if legacy:
        tokens.append(legacy)
    return tokens


def build_forbidden() -> "re.Pattern[str]":
    """Compile the forbidden-token pattern for this site."""
    parts = [GENERIC_FORBIDDEN] + [re.escape(t) for t in site_tokens()]
    return re.compile("|".join(parts), re.IGNORECASE)


FORBIDDEN = build_forbidden()

ALLOWED_MAJOR_GROUPS = {
    "Diffuse_Large_B_Cell_Lymphoma",
    "Follicular_Lymphoma",
    "Normal_B_cells",
    "Kassandra",
}

MAX_ABS_ROUNDING_ERROR = 5e-5
MAX_CORRELATION_LOSS = 1e-8


class VerificationError(AssertionError):
    """Raised when a bundle fails any check; the caller must not upload it."""


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    """Hex SHA-256 of a file, read in 1 MB blocks."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def md5_file(path: Path, chunk: int = 1 << 20) -> str:
    """Hex MD5 of a file — the checksum Zenodo reports back for an uploaded file."""
    digest = hashlib.md5()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def _member_text(zf: zipfile.ZipFile, name: str) -> io.TextIOBase:
    """Open a gzipped member of a ZIP as a text stream."""
    return io.TextIOWrapper(
        gzip.GzipFile(fileobj=io.BytesIO(zf.read(name)), mode="rb"), newline=""
    )


def _strategy_of(member: str) -> str | None:
    """Strategy token of a member filename, or None if it does not carry one."""
    head = member.split("__")[0]
    return head if head in EXPECTED_COUNTS else None


def _post_rm_of(member: str) -> str | None:
    """post0/post1 token of a harmonized member, or None for a prepared one."""
    parts = member.split("__")
    return parts[3].split(".")[0] if len(parts) == 4 else None


def check_member(zf: zipfile.ZipFile, member: str, prop_ids: set[str]) -> dict:
    """Run the per-member checks and return its observed shape.

    Checks applied to every member: no proprietary identifier in the index column;
    the row count matches the strategy's public sample count, or the smaller count
    recorded in SHORT_POST0_PUBLIC_ROWS for a method that drops batches; no token in
    the member name, the header, or any index value. Annotation members are read in
    full and additionally checked for their column count, the surviving-cell leak in
    `PUBLIC_SAMPLE_LABEL`, the allowed `Major_group` vocabulary, and the absence of
    the three dropped/renamed column names.

    Only the header and the index column of an expression member are scanned for
    tokens: those are the only places a human-authored string can appear — the body
    is numeric.

    Returns
    -------
    dict
        {"member", "rows", "cols"} for the manifest cross-check.

    Raises
    ------
    VerificationError
        On the first failure, naming the member and the check.
    """
    if FORBIDDEN.search(member):
        raise VerificationError(f"{member}: forbidden token in member name")

    is_annotation = "__ann" in member
    with _member_text(zf, member) as fh:
        reader = csv.reader(fh, delimiter="\t")
        header = next(reader)
        if FORBIDDEN.search("\t".join(header)):
            raise VerificationError(f"{member}: forbidden token in header")
        rows = 0
        leaked = 0
        for row in reader:
            rows += 1
            sample = row[0]
            if sample in prop_ids:
                leaked += 1
            if FORBIDDEN.search(sample):
                raise VerificationError(f"{member}: forbidden token in index value")
    if leaked:
        raise VerificationError(f"{member}: {leaked} proprietary sample IDs present")

    strat = _strategy_of(member)
    if strat:
        method = member.split("__")[2] if len(member.split("__")) == 4 else ""
        expected_rows = SHORT_POST0_PUBLIC_ROWS.get(
            (strat, method), EXPECTED_COUNTS[strat][1]
        )
        if _post_rm_of(member) == "post1":
            # Post-normalization outlier removal drops samples, and how many is a
            # property of the run rather than of the strategy — C_rnaseq_only's
            # 01_raw keeps 325 of its 878 public samples. Bound it, do not pin it;
            # the exact count per member is recorded in manifest.csv.
            if not 0 < rows <= expected_rows:
                raise VerificationError(
                    f"{member}: {rows} rows, expected 1..{expected_rows} after "
                    f"post-normalization outlier removal"
                )
        elif rows != expected_rows:
            raise VerificationError(
                f"{member}: {rows} rows, expected {expected_rows}"
            )

    if is_annotation:
        with _member_text(zf, member) as fh:
            frame = pd.read_csv(fh, sep="\t", index_col=0, dtype=str,
                                keep_default_na=False, low_memory=False)
        if frame.shape[1] != EXPECTED_ANN_COLUMNS:
            raise VerificationError(
                f"{member}: {frame.shape[1]} columns, expected "
                f"{EXPECTED_ANN_COLUMNS}"
            )
        for dropped in ("AUTHOR", "bags_class", "avicennaid"):
            if dropped in frame.columns:
                raise VerificationError(f"{member}: column {dropped} survived")
        if "PUBLIC_SAMPLE_LABEL" in frame.columns:
            hits = int(frame["PUBLIC_SAMPLE_LABEL"].isin(prop_ids).sum())
            if hits:
                raise VerificationError(
                    f"{member}: {hits} proprietary names in PUBLIC_SAMPLE_LABEL"
                )
        if "Major_group" in frame.columns:
            seen = {v for v in frame["Major_group"].unique() if v}
            unexpected = seen - ALLOWED_MAJOR_GROUPS
            if unexpected:
                raise VerificationError(
                    f"{member}: unexpected Major_group values {sorted(unexpected)}"
                )
        # Every row, not a head() sample: the leak this check exists to catch was a
        # label in 710 of 5,178 rows of one column, which a 50-row sample can miss.
        # An annotation member is 3.6 MB, so scanning all of it costs nothing.
        blob = "\t".join(frame.columns) + "\t".join(
            frame.select_dtypes(include="object").astype(str).values.ravel()
        )
        if FORBIDDEN.search(blob):
            raise VerificationError(f"{member}: forbidden token in annotation content")

    return {"member": member, "rows": rows, "cols": len(header) - 1}


def check_rounding(zf: zipfile.ZipFile, member: str, client=None,
                   n_rows: int = 200, n_cols: int = 500) -> float:
    """Compare a deposited block against the untouched S3 original.

    Streams the original, takes the same block by label, and returns the maximum
    absolute difference. Raises if it exceeds the bound implied by 4-decimal
    rounding, or if the two blocks do not correlate perfectly.
    """
    strat, imp, method, rest = member.split("__")
    post = rest.split(".")[0]
    key = f"exp/{strat}__{imp}__{s3_method(method)}__{post}.tsv.gz"

    with _member_text(zf, member) as fh:
        deposited = pd.read_csv(fh, sep="\t", index_col=0, nrows=n_rows)

    # Every row of the original has to be parsed, not just the first few hundred:
    # some harmonizers (Shambhala) return the samples in a different order, so the
    # public rows of the deposited head can sit anywhere in the original. Only the
    # columns of the deposited block are kept, which holds the parse at a few tens
    # of MB even for the widest matrix.
    body = R.open_s3_stream(key, client=client)
    with gzip.GzipFile(fileobj=body, mode="rb") as raw:
        header = raw.readline().decode().rstrip("\r\n").split("\t")
        wanted = set(deposited.columns[:n_cols])
        usecols = [header[0]] + [c for c in header[1:] if c in wanted]
        original = pd.read_csv(raw, sep="\t", header=None, names=header,
                               index_col=0, usecols=usecols)

    shared_rows = [i for i in deposited.index if i in original.index][:n_rows]
    shared_cols = [c for c in deposited.columns if c in original.columns][:n_cols]
    if not shared_rows or not shared_cols:
        raise VerificationError(
            f"{member}: no overlapping block with S3 original {key} "
            f"({len(shared_rows)} shared rows, {len(shared_cols)} shared columns)"
        )
    a = deposited.loc[shared_rows, shared_cols].to_numpy(dtype=float)
    b = original.loc[shared_rows, shared_cols].to_numpy(dtype=float)
    delta = float(abs(a - b).max())
    if delta > MAX_ABS_ROUNDING_ERROR:
        raise VerificationError(f"{member}: max rounding error {delta:.3g}")
    corr = float(pd.Series(a.ravel()).corr(pd.Series(b.ravel())))
    # 12 dp was unreachable by construction: rounding to 4 decimals adds ~1.4e-5 of RMS
    # noise, which costs a real block ~7e-11 of correlation. `max|delta|` above is the
    # bound that actually matters; this is a second, weaker witness that no column was
    # transposed or shifted, so it only needs to be far tighter than any such error.
    if 1.0 - corr > MAX_CORRELATION_LOSS:
        raise VerificationError(f"{member}: Pearson r {corr!r}, 1-r exceeds "
                                f"{MAX_CORRELATION_LOSS:g}")
    return delta


def verify_bundle(path: Path, prop_ids: set[str], expected_members: list[str] | None,
                  checks: str = "all", sample_rate: int = 25, seed: int = 0,
                  client=None) -> list[dict]:
    """Run every check over one closed bundle.

    Parameters
    ----------
    path : Path
        The ZIP to audit.
    prop_ids : set[str]
        The proprietary sample identifiers.
    expected_members : list[str] | None
        Member names the manifest says should be present; skipped when None.
    checks : str
        "all", "row-counts", "tokens" or "rounding".
    sample_rate : int
        One in this many expression members gets the rounding check.
    seed : int
        Seed for the rounding-check sample, so a run is reproducible.

    Returns
    -------
    list[dict]
        Per-member observations for the manifest cross-check.

    Raises
    ------
    VerificationError
        On the first failing check.
    """
    with zipfile.ZipFile(path) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise VerificationError(f"{path.name}: CRC failure in {bad}")
        members = zf.namelist()
        if expected_members is not None and sorted(members) != sorted(expected_members):
            missing = sorted(set(expected_members) - set(members))
            extra = sorted(set(members) - set(expected_members))
            raise VerificationError(
                f"{path.name}: member mismatch; missing={missing} extra={extra}"
            )

        observed = []
        if checks in ("all", "row-counts", "tokens"):
            for member in members:
                observed.append(check_member(zf, member, prop_ids))

        if checks in ("all", "rounding"):
            expression = [m for m in members if "__ann" not in m and "__exp" not in m]
            rng = random.Random(seed)
            sampled = [m for m in expression if rng.randrange(sample_rate) == 0]
            for member in sampled:
                check_rounding(zf, member, client=client)
    return observed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundles", nargs="+", type=Path)
    parser.add_argument("--check", default="all",
                        choices=["all", "row-counts", "tokens", "rounding"])
    parser.add_argument("--sample-rate", type=int, default=25)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--repo-root", default="..")
    args = parser.parse_args()

    if not site_tokens():
        print("WARNING: neither FL_FORBIDDEN_EXTRA nor FL_LEGACY_LABEL is set; "
              "only the generic token checks will run", file=sys.stderr)
    prop_ids = R.derive_prop_ids(args.repo_root)
    total_gb = 0.0
    for path in args.bundles:
        observed = verify_bundle(path, prop_ids, None, checks=args.check,
                                 sample_rate=args.sample_rate, seed=args.seed)
        size_gb = path.stat().st_size / 1e9
        total_gb += size_gb
        print(f"OK  {path.name:58s} {len(observed):3d} members {size_gb:6.2f} GB")
    print(f"\n{len(args.bundles)} bundles, {total_gb:.2f} GB")
    if len(args.bundles) > MAX_FILES:
        print(f"WARNING: {len(args.bundles)} files exceeds the {MAX_FILES} cap")
    if total_gb > MAX_RECORD_GB:
        print(f"WARNING: {total_gb:.2f} GB exceeds the {MAX_RECORD_GB} GB budget")
    return 0


if __name__ == "__main__":
    sys.exit(main())
