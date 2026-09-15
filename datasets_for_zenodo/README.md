# `datasets_for_zenodo/` — building the Zenodo expression record

This directory holds the code that builds and uploads the Zenodo companion record to
this repository: the public-cohort raw matrix, the 42 imputed input matrices, 911
harmonized matrices, and the full metric tables for all 2,407 harmonization attempts.

**It contains no data.** Every matrix is streamed out of object storage, transformed in
memory, written straight into a ZIP and uploaded, so the deposit never exists as a whole
on any disk. What is committed here is the transform, the audit, and the two planning
documents that record why the deposit is shaped the way it is.

The deposit's own DOI is `10.5281/zenodo.22737294`.

## Relationship to the rest of the repository

`make_public_supplementary.py` at the repository root redacts the *supplementary tables*
that ship inside this repository. This directory does the same job for the *expression
layer* that ships on Zenodo, under the same two rules (`redact_lib.py` names them R2 and
R3), and `DATA_AVAILABILITY.md` is the statement both of them implement.

`comb_ann_public.csv` is **not** duplicated here — the deposited annotation is rebuilt
from object storage by `build_tables.py`, and the repository's own copy lives at the
root. The two are the same 5,178 × 192 table with one deliberate difference, recorded as
caveat 14 of the deposit plan.

## Files

| File | What it does |
|---|---|
| `zenodo_manifest.py` | Declarative layout: which runs land in which ZIP, the budget guards, the expected sample counts. Pure data and pure functions — the builder and the auditor both import it so they cannot drift apart |
| `redact_lib.py` | Every transform applied to a deposited file, in one auditable place: the proprietary row filter, the annotation column whitelist, the group-label rename, and the 4-decimal rounding |
| `verify_bundle.py` | Audits one closed ZIP before it is uploaded — row counts, forbidden tokens, annotation schema, and a sampled comparison against the untouched original |
| `build_tables.py` | The 26 standalone tables that sit beside the ZIPs: metric tables, registries, and the source data |
| `build_and_upload.py` | The pipeline: build one bundle while the previous ones upload, verify before every PUT, resume from what the draft already holds |
| `test_transforms.py` | Smoke test of the transforms on a synthetic fixture. No object storage, no credentials, no real data — runs anywhere |
| `zenodo_progress.py` | Reads the live draft and prints what has landed against the manifest's totals |
| `probe_upload_concurrency.py` | One-off measurement of whether Zenodo's throughput limit is per-connection or global |
| `zenodo_metadata.json` | The record's Zenodo metadata |
| `readme_templates/` | The README, caveats and licence that are deposited *in* the record |
| `zenodo_deposit_plan_260913.md` | The deposit plan: what is deposited, what is withheld, the verification protocol, and 18 caveats found while building it |
| `upload_throughput_plan_260914.md` | Why the upload was slow and what was changed about it |

## Running it

```bash
export FL_S3_BUCKET=your-bucket          # required; no default
export FL_S3_PREFIX=FL_batch_correction  # optional, this is the default
export ZENODO_TOKEN=$(tr -d '\n\r ' < ~/.zenodo_token)

python test_transforms.py                # needs none of the above
python build_and_upload.py --dry-run     # bundle layout and budget, no I/O to Zenodo
python verify_bundle.py work/*.zip       # audit finished bundles standalone
```

Run it from this directory; `--repo-root` defaults to `..`, where the two
`Supplementary File 1` tables that define the proprietary sample set live.

### Site-specific tokens are supplied, not hardcoded

`verify_bundle.py` refuses a bundle containing a forbidden token. Two kinds of token are
treated differently, and the distinction is deliberate:

- **generic tokens** — two internal-schema column names that `DATA_AVAILABILITY.md`
  already documents by name, and any non-default Shambhala calibration variant — are
  written literally in `GENERIC_FORBIDDEN`;
- **site-specific tokens** — an internal bucket or container-registry name, a cluster pod
  prefix, a work e-mail, and the internal group label that rule R3 renames — are **not**
  written anywhere in this directory, because it is public and naming them would defeat
  the removal they enforce. `redact_lib.legacy_label()` already worked this way for the
  group label; `verify_bundle.site_tokens()` extends it to the rest.

```bash
export FL_LEGACY_LABEL=<the internal group label>      # also drives the R3 rename
export FL_FORBIDDEN_EXTRA=<comma-separated further tokens>
```

Set both before a real build. With neither set the build still succeeds and every check
still passes — which is the one failure mode that looks like success, so
`verify_bundle.py` prints a warning when it finds no site tokens, and
`build_and_upload.py` warns when `FL_LEGACY_LABEL` is missing.

## What the deposit withholds

Fifteen of the 88 cohorts (1,996 samples) are proprietary or under controlled access.
Redaction is row-wise for expression and row-wise *plus* column-wise for annotation: a
row filter alone is not a redaction, because a surviving row can still name a withheld
sample in one of its cells. All 88 cohorts remain **named**, with their sample counts, in
the deposited `cohorts.csv`. `DATA_AVAILABILITY.md` in the repository root is the full
statement; `readme_templates/_common_caveats.md` is the version that ships in the record.
