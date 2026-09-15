"""Smoke test for the deposit transforms, on a synthetic fixture.

Runs anywhere — no S3, no credentials, and no real expression data, so it can be
executed on a laptop without pulling any of the deposit payload onto it.

    python test_transforms.py      # exit code 0 = all PASS
"""

from __future__ import annotations

import gzip
import io
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

import redact_lib as R
import verify_bundle as V

PROP_IDS = {"S003-PROPRIETARY", "S007-PROPRIETARY"}
LEGACY = "LEGACY_GROUP"          # stands in for the real internal label


def _fixture_expression(n_rows: int = 10, n_genes: int = 6) -> bytes:
    """A gzipped samples x genes TSV with two proprietary rows and one NaN."""
    rng = np.random.default_rng(0)
    index = [f"S{i:03d}-PUB" for i in range(n_rows)]
    index[3], index[7] = "S003-PROPRIETARY", "S007-PROPRIETARY"
    frame = pd.DataFrame(
        rng.uniform(0, 15, size=(n_rows, n_genes)),
        index=index,
        columns=[f"GENE{i}" for i in range(n_genes)],
    )
    frame.iloc[0, 0] = np.nan
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(frame.to_csv(sep="\t").encode())
    return buf.getvalue()


def _fixture_annotation() -> bytes:
    """A gzipped annotation with an empty column, a leak, and the legacy label."""
    frame = pd.DataFrame(
        {
            "Major_group": [LEGACY, "Follicular_Lymphoma", "Follicular_Lymphoma",
                            "Kassandra"],
            "Diagnosis_with_coo": [f"{LEGACY}_Centrocyte", "FL_1", "FL_2", "K_1"],
            # The label on the *surviving* row S001-PUB is what exercises the
            # column-wise blanking: that row passes the proprietary row filter, yet
            # one of its cells still names a proprietary sample. An identifier from a
            # real withheld cohort must never stand in for it — rule R2 covers sample
            # names in source files too, not only in deposited tables.
            "PUBLIC_SAMPLE_LABEL": ["", "S007-PROPRIETARY", "S007-PROPRIETARY", ""],
            "AUTHOR": ["someone@example.com"] * 4,
            "bags_class": ["Centrocyte", "", "", ""],
            "avicennaid": ["r-chop", "chop", "", ""],
            "ALWAYS_EMPTY": [None, "", "  ", None],
            "KEEP_ME": ["a", "b", "c", "d"],
        },
        index=["S000-PUB", "S001-PUB", "S003-PROPRIETARY", "S002-PUB"],
    )
    frame.index.name = None
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(frame.to_csv(sep="\t").encode())
    return buf.getvalue()


def test_redact_and_round() -> None:
    raw = _fixture_expression()
    out = io.StringIO()
    kept, dropped = R.redact_and_round(io.BytesIO(raw), out, PROP_IDS,
                                       decimals=4, chunk_rows=3)
    assert (kept, dropped) == (8, 2), (kept, dropped)

    text = out.getvalue()
    assert text.count("PROPRIETARY") == 0, "proprietary row survived"
    assert text.startswith("\tGENE0"), "header must open with an empty index cell"
    assert text.count("GENE0\t") == 0 or text.count("\tGENE0") == 1, "header repeated"

    frame = pd.read_csv(io.StringIO(text), sep="\t", index_col=0)
    original = pd.read_csv(gzip.GzipFile(fileobj=io.BytesIO(raw)), sep="\t",
                           index_col=0)
    original = original.loc[~original.index.isin(PROP_IDS)]
    delta = (frame - original).abs().max().max()
    assert delta <= 5e-5, f"rounding error {delta}"
    assert pd.isna(frame.iloc[0, 0]), "NaN must survive as an empty cell"
    print("PASS  redact_and_round: 8 kept / 2 dropped, max |delta| "
          f"{delta:.2e}, NaN preserved")


def test_is_empty_nan_trap() -> None:
    # The obvious predicate would keep this column, because astype(str) renders
    # NaN as the truthy string "nan".
    column = pd.Series([None, "", "  ", None])
    assert R._is_empty(column), "all-empty column not detected"
    assert not R._is_empty(pd.Series([None, "x"])), "column with content dropped"
    naive = bool(column.astype(str).str.strip().any())
    assert naive, "the naive predicate is supposed to be wrong here"
    print("PASS  _is_empty: NaN trap avoided (naive predicate would keep it)")


def test_redact_annotation() -> None:
    raw = _fixture_annotation()
    full = pd.read_csv(gzip.GzipFile(fileobj=io.BytesIO(raw)), sep="\t",
                       index_col=0, dtype=str, keep_default_na=False)
    public = full.loc[~full.index.isin(PROP_IDS)]
    whitelist = [c for c in public.columns
                 if not R._is_empty(public[c]) and c not in R.ANN_DROP]
    assert "ALWAYS_EMPTY" not in whitelist and "AUTHOR" not in whitelist

    out = io.StringIO()
    kept, dropped = R.redact_annotation(io.BytesIO(raw), out, PROP_IDS, whitelist,
                                        legacy=LEGACY, sep="\t")
    assert (kept, dropped) == (3, 1), (kept, dropped)

    frame = pd.read_csv(io.StringIO(out.getvalue()), sep="\t", index_col=0,
                        dtype=str, keep_default_na=False)
    assert "AUTHOR" not in frame.columns
    assert "bcell_type_call" in frame.columns and "bags_class" not in frame.columns
    assert ("treatment_regimen_detail" in frame.columns
            and "avicennaid" not in frame.columns)
    assert frame.loc["S001-PUB", "treatment_regimen_detail"] == "chop"
    assert LEGACY not in out.getvalue(), "legacy label survived the rename"
    assert frame.loc["S000-PUB", "Major_group"] == "Normal_B_cells"
    # The separator survives: every other value in this column is `<diagnosis>_<coo>`,
    # so the renamed one has to keep its underscore to stay joinable with the rest.
    assert frame.loc["S000-PUB", "Diagnosis_with_coo"] == "Normal_B_cells_Centrocyte"
    assert not frame["PUBLIC_SAMPLE_LABEL"].isin(PROP_IDS).any()
    print("PASS  redact_annotation: 3 kept / 1 dropped, AUTHOR + empty column gone, "
          "renames applied, label leak blanked")


def test_verifier_catches_a_leak() -> None:
    """A planted proprietary row must make verify_bundle refuse the bundle."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fixture.zip"
        member = "A_confirmed_bad__strict__01_raw__post0.public.tsv.gz"
        body = gzip.compress(
            b"\tGENE0\nS000-PUB\t1.0000\nS003-PROPRIETARY\t2.0000\n"
        )
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as zf:
            zf.writestr(member, body)
        try:
            V.verify_bundle(path, PROP_IDS, [member], checks="tokens")
        except V.VerificationError as exc:
            assert "proprietary sample IDs" in str(exc), exc
            print("PASS  verify_bundle: planted leak rejected "
                  f"({str(exc).split(':')[-1].strip()})")
            return
        raise AssertionError("verify_bundle accepted a bundle containing a leak")


def test_verifier_catches_a_forbidden_token() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fixture.zip"
        member = "C_rnaseq_only__strict__shambhala_NBKass_Q0std__post0.public.tsv.gz"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as zf:
            zf.writestr(member, gzip.compress(b"\tGENE0\nS000-PUB\t1.0000\n"))
        try:
            V.verify_bundle(path, PROP_IDS, [member], checks="tokens")
        except V.VerificationError as exc:
            assert "member name" in str(exc), exc
            print("PASS  verify_bundle: non-default Shambhala member name rejected")
            return
        raise AssertionError("verify_bundle accepted a forbidden member name")


def main() -> int:
    for test in (test_redact_and_round, test_is_empty_nan_trap,
                 test_redact_annotation, test_verifier_catches_a_leak,
                 test_verifier_catches_a_forbidden_token):
        test()
    print("\nAll transform tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
