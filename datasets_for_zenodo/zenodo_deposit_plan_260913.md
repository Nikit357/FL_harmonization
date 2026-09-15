# Public data deposit — preparation and upload plan

**Date:** 2026-09-13 (revised the same day after Daniil's review)
**Working directory:** `<private repo>/datasets_for_zenodo/`
**Build and upload host:** **JupyterHub** (`$FL_REPO_ROOT`), ~10 GB free disk. **Nothing is copied to the authoring laptop.**
**Private source repo:** `<private repo>` (the unredacted tree)
**Public mirror:** `<this repository>` (already sanitized, commit `79b6e09` + the 2026-09-11 transfer)
**Governing precedents:**
`<archived benchmark repo>/public_release_sanitization_plan_260830.md` (rules R1–R4),
`<private repo>/public_release_transfer_plan_260910.md` (§Class 3a redaction recipe),
`<public mirror>/make_public_supplementary.py` (the auditable redactor),
`<public mirror>/DATA_AVAILABILITY.md` (the statement this deposit amends)

> **THIS DOCUMENT STAYS IN THE PRIVATE REPOSITORY.** Like its two predecessors it names the S3
> bucket, the proprietary cohorts and exactly which rows are withheld. Do not copy it into
> `FL_harmonization` and do not let a bulk `rsync` pick it up.

---

## Overview

`DATA_AVAILABILITY.md` in the public mirror currently says, in as many words: *"Expression
matrices are **not** in this repository for any cohort, open or withheld."* That is the one
remaining hole in the ComboBatch release — a reader can reproduce every ranking from the metric
tables but cannot see a single harmonized matrix. This plan closes it with **one Zenodo record,
filled to ≈45 GB**, carrying the public-cohort raw matrix, all 42 imputed input matrices, and
**911 harmonized matrices** — including the *complete* method × strategy × post-removal grid at
the `strict` imputation.

Five design decisions drive everything below.

1. **One record, filled to capacity.** Zenodo gives 50 GB free per record but caps a record at
   **100 files**. 995 matrices cannot be 995 top-level files, so the payload is organised as
   **27 ZIP bundles + 26 standalone tables = 53 top-level files**, which is exactly what Zenodo's
   own guidance recommends ("package 20+ files into a ZIP"). One record means one DOI, one
   README, one citation.
2. **Subset, never recompute.** Every deposited matrix is the *exact* matrix the article's
   metrics were computed on, with the 1,996 proprietary rows deleted. It is *not* a
   re-harmonization of the 5,178 open samples. Re-running the pipeline on open samples only
   would be a different experiment (batch correction is a function of the whole matrix), and its
   numbers would not match a single figure in the manuscript. The README says this first.
3. **Round to 4 decimal places.** The S3 files store full float64 `repr` — 17 significant digits
   of a log2 expression value, i.e. ~13 digits of pure noise. Rounding to 4 dp bounds the error
   at 5·10⁻⁵ (measured) and shrinks the gzip payload **2.97×** (measured). Without it the same
   selection would be 134 GB.
4. **One Shambhala, named `20_shambhala`.** Only the default `P0std × Q0std` calibration pair is
   deposited, renamed to `20_shambhala` — which is **already** the convention in the article's
   own `Supplementary File 3.csv.gz` (verified: 2,407 rows, 33 methods, zero `shambhala_*`
   tokens). The other 17 P/Q variants are dropped from the matrices *and* from every metric
   table. This also disposes of rule R3's label problem: the internal group label survives
   only inside those variants' run identifiers, so with them gone it no longer exists
   anywhere in the deposit.
5. **Stream; never stage the whole deposit.** The build runs on JupyterHub with ~10 GB free. Each
   matrix is streamed S3 → transform → straight into the open ZIP; each finished bundle is
   uploaded to Zenodo and deleted before the next begins. Peak disk stays under **4 GB**.

---

## 1. Background — measured reference data

All numbers below were measured on 2026-09-13, not quoted from documentation.

### 1a. What is on S3

```
s3://$FL_S3_BUCKET/FL_batch_correction/
  exp/        3,836 harmonized matrices   1,167.3 GB   (464 GB of that is Shambhala)
  prepared/      42 exp + 42 ann matrices    15.6 GB
  exp/comb_exp.tsv       the raw matrix       1.92 GB   (uncompressed TSV, 21,890 genes)
  exp/comb_ann_unified.csv                     6.9 MB
  metric tables at the prefix root                        ~280 MB
```

Restricted to the 33 deposited methods (32 non-Shambhala + `20_shambhala`), the harmonized layer
is **2,407 matrices / 179.9 GB on S3**, which is exactly the run set of `Supplementary File 3`.

Per-imputation size, and why `strict` is so much smaller:

| Imputation | Files (33 methods) | S3 size | After redact + round | Genes at `A_confirmed_bad` |
|---|---:|---:|---:|---:|
| `strict` (no imputation, full-coverage genes only) | 810 | — | **27.9 GB** | 3,520 |
| `softimpute` | 793 | — | 74.8 GB | 15,195 |
| `knn` | 804 | — | 77.3 GB | 15,195 |

The complete `strict` grid — every method × every strategy × both post-removal settings — fits
in 27.9 GB. That is the backbone of this deposit.

### 1b. The proprietary sample set — re-derived, not typed

Unchanged from the 260830 plan and re-verified today: **15 proprietary cohorts, 1,996 of 7,174
sample IDs.** Source of truth is `Supplementary File 1 short.csv`'s `Cohort type` column joined
to `Supplementary File 1.csv`'s index:

```python
import csv
short = "figures_for_article/supplementary_260824/Supplementary File 1 short.csv"
full  = "figures_for_article/supplementary_260824/Supplementary File 1.csv"
prop_cohorts = {r["COHORT_LABEL"].strip() for r in csv.DictReader(open(short))
                if r["Cohort type"].strip() == "Proprietary"}          # 15
rows = list(csv.DictReader(open(full)))
key  = list(rows[0].keys())[0]
PROP_IDS = {r[key] for r in rows if r["COHORT_LABEL"] in prop_cohorts}  # 1,996
```

### 1c. Public sample counts per removal strategy — **read this table before anything else**

Measured by downloading the 14 `prepared/{strat}__strict__ann.tsv.gz` files and applying
`PROP_IDS`. The withheld fraction is **not** uniform across strategies:

| Strategy | Total | Public | Withheld | % public |
|---|---:|---:|---:|---:|
| `S0_no_removal` | 7,174 | 5,178 | 1,996 | 72.2% |
| `A_confirmed_bad` | 5,444 | 4,071 | 1,373 | 74.8% |
| `B_extended_bad` | 5,108 | 3,735 | 1,373 | 73.1% |
| **`C_rnaseq_only`** | **2,243** | **878** | **1,365** | **39.1%** ⚠ |
| `D_malignant_only` | 6,285 | 4,478 | 1,807 | 71.2% |
| `E1_iterative_r1` | 5,420 | 4,047 | 1,373 | 74.7% |
| `E2_iterative_r2` | 5,387 | 4,014 | 1,373 | 74.5% |
| `E3_iterative_r3` | 5,256 | 3,883 | 1,373 | 73.9% |
| `F_microarray_only` | 4,931 | 4,300 | 631 | 87.2% |
| `G_affymetrix_only` | 2,801 | 2,178 | 623 | 77.8% |
| `H_affymetrix_extended` | 3,727 | 3,096 | 631 | 83.1% |
| `I_rare_batches_removed` | 6,803 | 4,847 | 1,956 | 71.2% |
| `J_ff_only` | 3,167 | 2,203 | 964 | 69.6% |
| `K_ffpe_only` | 3,000 | 2,591 | 409 | 86.4% |

⚠ **`C_rnaseq_only` loses 61% of its samples.** The RNA-seq arm is dominated by proprietary
cohorts (`PUB_DLBCL_NCICCR` 567, `PUB_FL_TOBIN` 224, `Kassandra` 140, `PUB_DLBCL_DLC1` 133 …).
Those matrices are still worth depositing — they are the article's real inputs minus rows — but
the README must warn that any *reanalysis* of that strategy on the open subset is working with
878 samples, not 2,243. The same warning applies in weaker form to `J_ff_only` (69.6%).

### 1d. Rounding: measured error and measured compression

Measured on a 53-sample × 6,797-gene block of `C_rnaseq_only__strict__01_raw__post0`:

| Format | Text | gzip -6 | Shrink vs. original |
|---|---:|---:|---:|
| original (float64 `repr`, ~18 chars/value) | 6.37 MB | 2.993 MB | 1.00× |
| `%.5f` | 2.93 MB | 1.236 MB | 2.42× |
| **`%.4f`** | **2.57 MB** | **1.008 MB** | **2.97×** |
| `%.3f` | 2.21 MB | 0.814 MB | 3.68× |

Maximum absolute rounding error at 4 dp: **4.99999·10⁻⁵**. Expression values are log2(x+1) in
the 0–20 range, so this is ~3·10⁻⁶ relative — four orders of magnitude below the run-to-run
variability the Shambhala speed-up work already accepted (1.39% mean relative distortion).

**All size estimates below use the conservative 2.97× factor and the per-strategy public
fractions from §1c.** Real output will be **smaller** — gzip's window sees far more repetition in
a full 4,000-row file than in a 53-row block — so the projected 45.2 GB is expected to land
nearer 41 GB. The builder enforces a hard 46 GB budget regardless (§4.4).

### 1e. Method availability

32 non-Shambhala methods have at least one output on S3 (8 of the 39 registry entries never
produced valid output — see `harmonization-scripts/methods_table_for_manuscript.md`); with
`20_shambhala` that is **33 deposited methods**. Coverage is uneven and the builder resolves it
against a live S3 listing rather than assuming — a method with no output at a given
(strategy, imputation) is recorded in `manifest.csv` as missing, with the reason from the
methods registry. Known gaps: `22_tmm` / `23_vst` are RNA-seq-only by design (6 runs each),
`33_amdbnorm` 14, `27_dwd` and `29_combat_ref` 34, `36_explobatch` 60.

### 1f. Shambhala: which one, and under what name

`20_shambhala` = `shambhala_P0std_Q0std`, the default Borisov 2021 calibration pair
(P0std, 39 samples; Q0std, 100 GTEx RNA-seq samples). 84 matrices on S3 — the complete
14 × 3 × 2 grid. The single stray `shambhala_P0std_Q0std_speed_up` object is **not** deposited.

This rename is not new: `figures_for_article/supplementary_260824/Supplementary File 3.csv.gz`
already ships **2,407 rows × 93 columns with 33 methods and zero `shambhala_*` tokens**, with
`20_shambhala` carrying 84 rows. The deposit simply applies the same mapping to the richer
329-column `metrics_comprehensive_260905.csv` and to the long-format tables.

Consequence for rule R3: the internal group label lives only in the run identifiers of the
two calibration variants named after it. Dropping the 17 non-default variants removes all
168 of them. No `sed` rename
is needed, and none may be applied — a rename would resurrect rows that are being dropped.

### 1g. The curated Best-15

From `harmonization-metrics/create_v3_notebook.py:20-34` (`_top_ids`, `post_rm=False` only);
5 methods × 6 strategies. All 15 exist on S3 (verified):

| Method | Imputation | Strategy |
|---|---|---|
| `10_mnn` | strict | `S0_no_removal`, `H_affymetrix_extended`, `D_malignant_only`, `J_ff_only` |
| `16_fsqn_r` | strict | `C_rnaseq_only`, `J_ff_only` |
| `16_fsqn_r` | knn, softimpute | `C_rnaseq_only` |
| `04_sva` | knn, softimpute | `C_rnaseq_only` |
| `04_sva` | knn, strict, softimpute | `K_ffpe_only` |
| `13_fsmvn` | strict | `S0_no_removal` |
| `33_amdbnorm` | strict | `S0_no_removal` |

Nine of the fifteen are `strict` and therefore already inside the complete strict grid; the
remaining six land in `best15_clustermap_approaches.zip`, and `manifest.csv` marks **all
fifteen** with `is_best15 = true` wherever they appear so the set is discoverable from one
column.

### 1h. The annotation schema — 293 columns are empty, and five leak

This was the plan's own blind spot on the first pass. `comb_ann_public.csv` was known to need a
column-wise redaction; the **42 prepared annotation twins carry the identical 486-column schema
and the identical leaks**, and the first draft would have deposited them raw.

Measured on `prepared/S0_no_removal__strict__ann.tsv.gz` restricted to the 5,178 public rows:

| | Columns |
|---|---:|
| Full internal schema — sample-ID index + 485 annotation columns | 486 |
| Empty across all 5,178 public rows — dropped | 293 |
| Survive the trim | 192 |
| `AUTHOR` (a colleague's work e-mail, 4,468 cells, 1 distinct value) — dropped outright | −1 |
| **Deposited annotation columns** | **191** |
| **Deposited file, counting the sample-ID column** | **192** |

Both numbers describe the same table, and both already appear in the release: the
mirror's `comb_ann_public.csv` reads as 5,178 × 192 with a plain `read_csv` and
5,178 × 191 with `index_col=0`. The code asserts on 191 (`EXPECTED_ANN_COLUMNS`) and
the prose quotes 192, matching `DATA_AVAILABILITY.md`. **Verified live 2026-09-13:**
the whitelist this pipeline derives and the mirror's independently produced schema are
the same 191 names, with exactly one exception — see §6 caveat 14.

The trim itself removes `dbgap_id`, `MPINR`, `BG ID`, `Alias (Patient ID)`, every `CHRONOS_*`
column, and — for free — the two product-name headers `subtype (bags)` and `bags-based`
(verified individually). Five items survive the trim and need explicit handling:

| Item | Extent | Action | Rule |
|---|---:|---|---|
| `PUBLIC_SAMPLE_LABEL` holds 76 `MPI-###` labels — proprietary `SOM`-cohort sample names — on `PUB_FL_HORN` rows | 76 cells | blank the cell | **R2** |
| `AUTHOR` | 4,468 cells | drop the column | third-party PII |
| `Major_group`, `Diagnosis_with_coo` and `Diagnosis_cell_type_general` carrying the internal group label (supplied as `FL_LEGACY_LABEL`; not named here, since this plan is mirrored publicly) | 709 + 710 + 710 cells | rename to `Normal_B_cells` | **R3** |
| `bags_class` — the internal classifier's output column | 1 header, 55 cells | rename to `bcell_type_call`; values are ordinary cell-type names and stay | **R3** |
| `avicennaid` — internal-sounding header over public regimen data (`r-chop` 593, `rb-chop` 398, `chop` 179 …), disjoint from `TREATMENT_REGIMEN` | 1 header, 1,271 cells | rename to `treatment_regimen_detail`; **keep the values** — this is the deposit's only source of regimen detail | judgement |

**A single fixed 191-column whitelist is applied to every deposited annotation table** — the
master table and all 42 prepared twins — computed once from the 5,178-row master rule, not
per-strategy. Computing it per strategy would give a different schema per file (314 empty
columns for `A_confirmed_bad`'s 4,071 rows, so 172 columns) and make the deposit hostile to
anyone trying to `concat` two of them. The fixed whitelist reproduces the mirror's
`comb_ann_public.csv` schema exactly, so the deposit and the GitHub repository agree column for
column.

---

## 2. Platform survey — Zenodo and the alternatives

### 2a. Zenodo, as it actually stands (checked 2026-09-13)

| Constraint | Value |
|---|---|
| Default quota **per record** | 50 GB |
| **Files per record** | **100 — the binding constraint for this deposit** |
| Records per user | unlimited, as long as each is ≤ 50 GB |
| Extra allowance | up to **150 GB** the user can distribute across their own drafts, self-service, via the draft's *Manage storage* slider |
| One-off increase | up to **200 GB** per record, by support request, still < 100 files |
| Per-file max | 50 GB (bucket-based Files API); the legacy files API caps at 100 MB — it is unusable here |
| DOI | minted per record, plus a concept DOI that always resolves to the newest version |
| Versioning | new versions keep the concept DOI and get their own version DOI |
| Cost | free |
| API | `POST /api/deposit/depositions`, bucket `PUT`, `prereserve_doi: true`, publish action; Bearer token, scopes `deposit:write` + `deposit:actions`; sandbox at `sandbox.zenodo.org` (test DOI prefix `10.5072`) |

**The file count, not the byte count, is what shapes this deposit.** 995 matrices must be
bundled. 53 top-level files leaves comfortable headroom.

**Headroom if more is ever wanted.** The self-service 150 GB allowance can be pushed onto this
one record from the draft's *Manage storage* control, taking it to 200 GB without a support
ticket. That would fit the entire post0 corpus at all three imputations plus every `strict`
post1 matrix — 1,609 matrices, ~106 GB — inside the same 100-file ZIP layout. Not proposed here
(it triples the upload time for a 3× less interesting marginal gain), but it is one slider away
if a reviewer asks.

### 2b. The alternatives

| Platform | Size limits | Cost | DOI | Pros for *this* deposit | Cons for *this* deposit |
|---|---|---|---|---|---|
| **Zenodo** ★ | 50 GB/record free (unlimited records), +150 GB self-service, 200 GB on request; ≤100 files | free | yes, + concept DOI | CERN-operated, no fee, GitHub-native for the code mirror, versioning, embargo option, communities, plain REST API; 45 GB fits the *free* tier untouched | the 100-file cap forces ZIP bundling; no domain curation |
| **Figshare** (free tier) | 20 GB total per user, 20 GB/file | free tier; Figshare+ from 100 GB is **paid** | yes | Nice previews, good metadata | 20 GB free is less than half this deposit; would need paid Figshare+ |
| **Dryad** | 10 GB/file, up to 300 GB/publication | **paid** (per-submission fee) | yes | Strong curation, ties to journals | **Requires CC0.** We are redistributing processed derivatives of other people's GEO/ArrayExpress studies — asserting a CC0 waiver over them is the wrong claim. Also charges a fee, also restrictive about human-subject data |
| **OSF** | 5 GB/file, 50 GB per public project | free | yes | Nice project structure | **OSF is disabling the Projects generalist-repository workflow after 2026-11-16** — disqualifying for a 2026-autumn deposit |
| **Mendeley Data** | 10 GB/dataset | free | yes | Elsevier-linked, simple | 10 GB/dataset means 5 records for one deposit — the opposite of the one-record requirement |
| **EBI BioStudies** | very large submissions accepted, FTP/Aspera | free | accession, DOI on request | Domain-appropriate (EMBL-EBI), permanent, no ZIP bundling needed | Curated and slower; modelled on *primary* study data, and these matrices derive from 73 other studies |
| **GEO / ArrayExpress** | n/a | free | accession | The canonical home for expression data | **Will not accept this.** Both archive *primary* experiments from the group that generated them |
| **Synapse (Sage)** | effectively unlimited | free | yes | Would allow the 1,996 proprietary samples under governed access later | Requires a governance setup and certified-user flow; heavyweight for a 100%-open deposit |
| **Hugging Face Datasets** | very generous (LFS), free | free | DOI supported | Cheap, fast, no file-count cap, great for ML reuse | Not an archival repository of record; no preservation guarantee; reviewers and NAR will want a recognised repository DOI |

### 2c. Recommendation

**Zenodo — one record, ~45 GB, 53 files, CC BY 4.0** (matching the mirror's existing
`LICENSE-DATA`), with `related_identifiers` pointing at the article and at the
`FL_harmonization` GitHub repository.

Optionally, mirror the deposit to **Hugging Face** later as a convenience copy for ML reuse —
no file-count cap there, so the matrices could sit unbundled. Costs nothing, the DOI of record
stays on Zenodo. Not part of this plan.

---

## 3. Deposit design — one record, 53 files, ≈45 GB

**Title:** *ComboBatch: harmonized transcriptomic matrices and benchmark metrics for 73 public
germinal-centre B-cell lymphoma cohorts*

Sizes are conservative projections (§1d factor 2.97 + §1c per-strategy fractions); actual sizes
are written to `manifest.csv` and `SIZES.md` as the build proceeds.

### 3a. Standalone tables — 26 files, ≈0.40 GB

| File | Content | Size |
|---|---|---:|
| `README.md` | the record's front matter; §4.6 | small |
| `LICENSE-CC-BY-4.0.txt` | data licence | small |
| `manifest.csv` | **the index of the whole record**: one row per deposited matrix — bundle, member path, strategy, imputation, method, post_rm, n_samples, n_genes, sha256, `is_best15`, `is_decision_tree` | ~0.5 MB |
| `SHA256SUMS.txt` | SHA-256 of **all 59** other top-level files — the 34 bundles and the 25 tables (itself excluded, as usual). Bundle digests are read back from `manifest.csv`'s `sha256_bundle`, because a streamed bundle is deleted as soon as its PUT returns and cannot be re-hashed at the end of the run — see §6 caveat 27 | small |
| `metrics_comprehensive_260905.csv` | **2,407 runs × 329 columns** (33 methods; groups A–N incl. the blind check) | ~12 MB |
| `marker_gene_correlations_long_260905.csv.gz` | Group L per-gene detail, filtered to the 2,407 run IDs | ~10 MB |
| `marker_cohort_correlations_long_260905.csv.gz` | Group L per-cohort detail, same filter | ~1.5 MB |
| `prediction_folds_long_260905.csv.gz` | Group N per-fold detail, same filter | ~1 MB |
| `gene_qc_long_260828.csv.gz` | per-attempt per-gene expression QC | 123 MB |
| `gene_gene_consensus_{within,global,sd,n}_260828.csv.gz` | Fisher-z consensus gene × gene matrices (4 files) | 9.1 MB |
| `marker_gene_coverage_by_attempt_260828.csv` | per-gene coverage audit | 0.25 MB |
| `gene_level_stats_260905.csv` | per-gene ρ / QC statistics | 0.31 MB |
| `marker_gene_annotation.csv` | the 633-gene / 63-signature panel + the 56-gene narrow set | 0.13 MB |
| `metric_dictionary.csv` | **new** — metric column → group letter A–N, polarity, one-line definition | small |
| `methods_registry.csv` | **new** — 33 deposited methods: full name, harshness, package, version, reference, coverage | small |
| `strategies_registry.csv` | **new** — 14 strategies: definition, total N, public N, % public (§1c) | small |
| `comb_exp_public.tsv.gz` | **raw, unharmonized**: 5,178 × 21,890, log2, NA preserved, 4 dp. Restricted to the annotation's own sample set — the S3 source is wider than the cohort; see §6 caveat 16 | 0.27 GB |
| `comb_ann_public.csv` | 5,178 × 192, redacted per §1h | 5.3 MB |
| `cohorts.csv` | **all 88** cohorts incl. the 15 withheld, with accessions and provenance | 22 KB |
| `sample_selection_by_strategy.csv` | 5,178 rows × 14 boolean columns | ~1 MB |
| `strategy_sample_counts.csv` | the §1c table, machine-readable | small |
| `gene_selection_by_pair.csv.gz` | long `(strat, imp, gene)` over the 42 prepared pairs | ~2 MB |

### 3b. Imputed input matrices — 3 bundles, 84 matrices, ≈3.87 GB

| Bundle | Members | Size |
|---|---:|---:|
| `prepared_inputs__strict.zip` | 14 exp + 14 ann | 0.59 GB |
| `prepared_inputs__softimpute.zip` | 14 exp + 14 ann | 1.65 GB |
| `prepared_inputs__knn.zip` | 14 exp + 14 ann | 1.63 GB |

These are the inputs every harmonization method was given. Each annotation twin carries the
191-column redacted schema of §1h — **not** the 486-column internal schema.

### 3c. Harmonized matrices — 24 bundles, 911 matrices, ≈40.9 GB

**Tier 1 — the complete `strict` grid** (33 methods × 14 strategies × post0 + post1 = 810
matrices), one bundle per strategy. This is the full two-way cross-product at the
imputation-free setting, not a slice:

| Bundle | Members | Size | | Bundle | Members | Size |
|---|---:|---:|---|---|---:|---:|
| `grid_strict__S0_no_removal.zip` | 62 | 2.23 GB | | `grid_strict__F_microarray_only.zip` | 56 | 1.60 GB |
| `grid_strict__A_confirmed_bad.zip` | 62 | 1.84 GB | | `grid_strict__G_affymetrix_only.zip` | 56 | 1.41 GB |
| `grid_strict__B_extended_bad.zip` | 56 | 2.39 GB | | `grid_strict__H_affymetrix_extended.zip` | 60 | 2.27 GB |
| `grid_strict__C_rnaseq_only.zip` | 60 | 0.63 GB | | `grid_strict__I_rare_batches_removed_part{1,2}.zip` | 44 + 12 | 2.93 + 0.56 GB |
| `grid_strict__D_malignant_only.zip` | 56 | 1.71 GB | | `grid_strict__J_ff_only.zip` | 58 | 1.49 GB |
| `grid_strict__E1_iterative_r1.zip` | 56 | 2.38 GB | | `grid_strict__K_ffpe_only.zip` | 60 | 1.85 GB |
| `grid_strict__E2_iterative_r2.zip` | 56 | 2.34 GB | | **Tier 1 total** | **810** | **27.87 GB** |
| `grid_strict__E3_iterative_r3.zip` | 56 | 2.24 GB | | | | |

`I_rare_batches_removed` is the one strategy over the 3 GB bundle cap (§4.4) and is
split automatically, so Tier 1 is 15 files. Counts and sizes in this table are the
resolved values from `--dry-run` against the live listing, not projections of a
projection.

**Tier 2 — `softimpute` and `knn` marginal slices** (101 further matrices):

| Bundle | Members | Size |
|---|---:|---:|
| `sweep_methods__A_confirmed_bad__softimpute__post0_part1.zip` | 21 | 2.84 GB |
| `sweep_methods__A_confirmed_bad__softimpute__post0_part2.zip` | 7 | 0.73 GB |
| `sweep_methods__A_confirmed_bad__knn__post0_part1.zip` | 21 | 2.85 GB |
| `sweep_methods__A_confirmed_bad__knn__post0_part2.zip` | 9 | 1.05 GB |
| `sweep_strategies__10_mnn__softimpute__post0.zip` | 13 | 1.66 GB |
| `sweep_strategies__16_fsqn_r__softimpute__post0.zip` | 13 | 1.40 GB |
| `sweep_strategies__04_sva__softimpute__post0.zip` | 12 | 1.52 GB |
| `best15_clustermap_approaches.zip` | 3 | 0.19 GB |
| `decision_tree_recommended.zip` | 2 | 0.29 GB |
| **Tier 2 total** | **101** | **12.53 GB** |

Deduplication runs in bundle order, and the sweeps are resolved before the two curated
archives, so a Best-15 or decision-tree run that also belongs to a complete sweep stays
in the sweep and the curated archive holds only what appears nowhere else — 3 and 2
members respectively. Keeping the sweeps whole is the right trade: a strategy sweep
missing three of its fourteen strategies would not be a sweep. The curated sets stay
discoverable because `manifest.csv` carries `is_best15` and `is_decision_tree` on
**every** row, wherever the matrix physically sits.

Decision-tree targets (2026-06-04 tree), deduplicated against Tiers 1–2 by the builder:

```
J_ff_only         × softimpute × 10_mnn      × post0   (FF only → MNN)
J_ff_only         × softimpute × 16_fsqn_r   × post0   (FF only → FSQN R)
K_ffpe_only       × softimpute × 04_sva      × post0   (FFPE only → SVA; the platform-mixing result)
K_ffpe_only       × knn        × 04_sva      × post0
C_rnaseq_only     × softimpute × 04_sva      × post0   (RNA-seq only → SVA; ⚠ 878 public samples)
C_rnaseq_only     × knn        × 04_sva      × post0
F_microarray_only × softimpute × 16_fsqn_r   × post0   (RNA-seq + Illumina arrays → FSQN R)
F_microarray_only × softimpute × 33_amdbnorm × post1   (… or AMDBNorm + post-removal)
S0_no_removal     × softimpute × 10_mnn      × post1   (RNA-seq + various arrays → MNN + post-removal)
A_confirmed_bad   × softimpute × 10_mnn      × post1
```

### 3d. Totals

| | Files | Matrices | Size |
|---|---:|---:|---:|
| Standalone tables | 26 | — | 0.41 GB |
| Imputed inputs (3 bundles) | 3 | 84 | 4.16 GB |
| Harmonized (31 bundles) | 31 | 911 | 43.60 GB |
| **Record total, as deposited 2026-09-14** | **60** | **995** | **48.17 GB** |
| Zenodo free limit | 100 | — | 50 GB |

The 53-file / 44.66 GB figures this table carried until 2026-09-14 were the `--dry-run`
projection for 27 bundles. Two things moved them. The Option C re-split
(`upload_throughput_plan_260914.md` §2) cut four bundles that could not survive a PUT into
11 sub-parts, taking the record from 27 to 34 bundles and 53 to 60 files without changing
the 995 matrices. And gzip came out 8% larger than projected across the board — every
bundle overshot its `est_gb` by 12-20% — which is what carries the total past the 46 GB
budget of §4.4 to 48.17 GB. Still inside Zenodo's 50 GB, but the budget guard is now the
binding constraint and would refuse this record if re-run from empty.

Those figures are the output of `python build_and_upload.py --dry-run` resolved against
the live S3 listing on 2026-09-13, not hand arithmetic. The same run reports **124
requested combinations with no S3 output** — all of them the known coverage gaps of
§1e (`22_tmm` and `23_vst` RNA-seq-only by design, plus `27_dwd`, `29_combat_ref` and
`33_amdbnorm` partial) — and they are listed rather than silently skipped.

**911 harmonized matrices** are deposited out of the 2,407 in the deposited method set (37.8%) —
including 100% of the `strict` grid. Shambhala is represented by `20_shambhala` only; the other
17 P/Q variants (1,428 attempts) appear nowhere in the record, matrices or metrics.

---

## 4. Files to create

Everything new lives in `datasets_for_zenodo/`, is developed here, and is **run on JupyterHub**.
No existing pipeline file is modified.

```
datasets_for_zenodo/
├── zenodo_deposit_plan_260913.md      ← this document (private only)
├── zenodo_manifest.py                 ← declarative: bundles, keys, expected counts
├── redact_lib.py                      ← PROP_IDS, the 191-column whitelist, the transforms
├── build_tables.py                    ← the 26 standalone tables: metrics, registries, source
├── build_and_upload.py                ← the streaming pipeline: S3 → transform → zip → Zenodo
├── verify_bundle.py                   ← per-bundle auditor, importable and standalone
├── test_transforms.py                 ← synthetic-fixture smoke test; no S3, no real data
├── zenodo_metadata.json               ← record metadata; FILL_ME placeholders block upload
├── readme_templates/
│   ├── record_readme.md
│   ├── _common_caveats.md
│   └── LICENSE-CC-BY-4.0.txt
├── prop_ids.txt                       ← generated, gitignored
└── work/                              ← generated, gitignored; one bundle at a time
    └── tables/                        ← the standalone tables, uploaded last
```

### 4.1 `zenodo_manifest.py` — the single source of truth

Pure data, no I/O, so the builder and the verifier read the same structure.

```python
"""Declarative manifest of the Zenodo deposit: which S3 keys land in which bundle."""

from __future__ import annotations
from dataclasses import dataclass, field

SHAMBHALA_S3 = "shambhala_P0std_Q0std"   # the only variant deposited
SHAMBHALA_PUB = "20_shambhala"           # its public name, per Supplementary File 3
SWEEP_METHODS = ("10_mnn", "16_fsqn_r", "04_sva")
ANCHOR_STRAT = "A_confirmed_bad"
IMPUTATIONS = ("strict", "softimpute", "knn")
STRATEGIES = (
    "S0_no_removal", "A_confirmed_bad", "B_extended_bad", "C_rnaseq_only",
    "D_malignant_only", "E1_iterative_r1", "E2_iterative_r2", "E3_iterative_r3",
    "F_microarray_only", "G_affymetrix_only", "H_affymetrix_extended",
    "I_rare_batches_removed", "J_ff_only", "K_ffpe_only",
)

MAX_BUNDLE_GB = 3.0        # bundle cap; keeps peak JupyterHub disk under 4 GB
MAX_RECORD_GB = 46.0       # hard budget; bundles past it are dropped, not truncated
MAX_FILES = 100            # Zenodo's per-record cap
MIN_FREE_GB = 3.0          # abort before starting a bundle if free space is below this

# Samples per strategy, measured 2026-09-13 (§1c). The builder asserts against these;
# a mismatch means the S3 prepared layer moved and this plan is stale.
EXPECTED_COUNTS: dict[str, tuple[int, int]] = {      # strat -> (total, public)
    "S0_no_removal": (7174, 5178),     "A_confirmed_bad": (5444, 4071),
    "B_extended_bad": (5108, 3735),    "C_rnaseq_only": (2243, 878),
    "D_malignant_only": (6285, 4478),  "E1_iterative_r1": (5420, 4047),
    "E2_iterative_r2": (5387, 4014),   "E3_iterative_r3": (5256, 3883),
    "F_microarray_only": (4931, 4300), "G_affymetrix_only": (2801, 2178),
    "H_affymetrix_extended": (3727, 3096), "I_rare_batches_removed": (6803, 4847),
    "J_ff_only": (3167, 2203),         "K_ffpe_only": (3000, 2591),
}

# harmonization-metrics/create_v3_notebook.py:20-34, post_rm=False only
BEST15 = (
    ("10_mnn", "strict", "S0_no_removal"), ("10_mnn", "strict", "H_affymetrix_extended"),
    ("10_mnn", "strict", "D_malignant_only"), ("04_sva", "knn", "C_rnaseq_only"),
    ("04_sva", "softimpute", "C_rnaseq_only"), ("16_fsqn_r", "knn", "C_rnaseq_only"),
    ("16_fsqn_r", "softimpute", "C_rnaseq_only"), ("16_fsqn_r", "strict", "C_rnaseq_only"),
    ("10_mnn", "strict", "J_ff_only"), ("16_fsqn_r", "strict", "J_ff_only"),
    ("04_sva", "knn", "K_ffpe_only"), ("04_sva", "strict", "K_ffpe_only"),
    ("04_sva", "softimpute", "K_ffpe_only"), ("13_fsmvn", "strict", "S0_no_removal"),
    ("33_amdbnorm", "strict", "S0_no_removal"),
)

DECISION_TREE_PICKS = (...)   # the 10 tuples of §3c

@dataclass
class Bundle:
    name: str                                          # the .zip filename on Zenodo
    keys: list[tuple[str, str, str, str]] = field(default_factory=list)
    kind: str = "harmonized"                           # harmonized | prepared
    priority: int = 0                                  # lower drops first under MAX_RECORD_GB
```

`build_bundles()` materialises the 27 bundles by intersecting the wanted slices with a **live
`list-objects-v2` listing**, never a hardcoded list, applies `MAX_BUNDLE_GB` splitting, and
deduplicates Tier 2 against Tier 1 so no matrix is deposited twice.

### 4.2 `redact_lib.py` — every transform, in one auditable place

```python
ANN_DROP = ("AUTHOR",)
ANN_RENAME = {"bags_class": "bcell_type_call",
              "avicennaid": "treatment_regimen_detail"}
LEGACY_LABEL_REPLACEMENT = "Normal_B_cells"
```

Four functions:

- **`derive_prop_ids(root) -> set[str]`** — the six lines of §1b, asserting 15 cohorts / 1,996
  IDs. Never cached into git.
- **`annotation_whitelist(master_ann, prop_ids) -> list[str]`** — computes the 191-column
  whitelist **once** from the 5,178 public rows of `prepared/S0_no_removal__strict__ann.tsv.gz`
  (drop all-empty, then drop `ANN_DROP`), writes it to `work/ann_columns.txt`, and asserts
  `len == 191`. Note the predicate shape, which the 260910 plan already learned the hard way:

  ```python
  def _is_empty(s: pd.Series) -> bool:
      # astype(str) renders NaN as the truthy string "nan", so the obvious
      # one-liner drops ZERO columns. Drop the NaNs first, then test for content.
      v = s.dropna().astype(str).str.strip()
      return not (v != "").any()
  ```

- **`redact_annotation(src, dst, prop_ids, whitelist)`** — row filter → column whitelist →
  blank proprietary `PUBLIC_SAMPLE_LABEL` cells → `Major_group` / `Diagnosis_with_coo` label
  rename → `ANN_RENAME`. Read with `dtype=str, keep_default_na=False` so nothing is retyped and
  the literal string `"NA"` is not turned into a blank.
- **`redact_and_round(src_stream, dst_fileobj, prop_ids, decimals=4, chunk_rows=256)`** — the
  expression transform, streaming:

  ```python
  def redact_and_round(src_stream, dst_fileobj, prop_ids: set[str],
                       decimals: int = 4, chunk_rows: int = 256) -> tuple[int, int]:
      """Drop proprietary rows and round values, streaming a samples x genes TSV.

      Parameters
      ----------
      src_stream : IO[bytes]
          An open S3 `get_object()["Body"]` (or any binary stream) holding a gzip TSV,
          samples x genes, first column = sample ID under an empty header cell.
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

      Returns
      -------
      tuple[int, int]
          (rows kept, rows dropped).
      """
      kept = dropped = 0
      first = True
      for chunk in pd.read_csv(src_stream, sep="\t", index_col=0,
                               chunksize=chunk_rows, compression="gzip"):
          mask = ~chunk.index.isin(prop_ids)
          dropped += int((~mask).sum())
          kept += int(mask.sum())
          sub = chunk.loc[mask]
          if sub.empty and not first:
              continue
          sub.to_csv(dst_fileobj, sep="\t", header=first,
                     float_format=f"%.{decimals}f", na_rep="")
          first = False
      return kept, dropped
  ```

  `header=first` writes the header exactly once, and pandas emits an empty first header cell for
  an unnamed index — reproducing the S3 file's own header shape. `na_rep=""` matters only for
  `comb_exp_public.tsv.gz`; the prepared and harmonized layers have no NaNs.

### 4.3 `build_and_upload.py` — the streaming pipeline

There is **no way to move bytes from S3 to Zenodo without them passing through compute.** Zenodo
has no server-side "ingest from URL", and every matrix must be transformed anyway. What the
pipeline does instead is guarantee that **no more than one bundle exists on disk at any moment,
and nothing is ever written to the Mac**:

```
for each bundle (in priority order):
    check free disk >= MIN_FREE_GB + projected bundle size   ── else abort with a clear message
    open work/<bundle>.zip, mode="w", compression=ZIP_STORED  (members are already gzip)
    submit every member to a ProcessPoolExecutor(--workers), at most workers+2 ahead:
        body = s3.get_object(...)["Body"]                     ── streamed, never a local copy
        redact_and_round(body, gzip.open(work/parts/<member>, "wt"), PROP_IDS)
    parent consumes the futures IN TASK ORDER:
        zf.write(part, member_name); part.unlink()            ── stored, so this is a byte copy
        append row to manifest.csv and to work/manifest_rows.jsonl
    close zip; verify_bundle(...) §4.5; sha256 it
    PUT work/<bundle>.zip to the Zenodo bucket
    GET the file entry back; assert Zenodo's MD5 == locally computed MD5
    delete work/<bundle>.zip
```

**Why a pool and not a loop.** Measured on this node: one process transforms 59 MB of
deposit per minute at 98% of one core, so the record takes ~12.5 h serially — the `%.4f`
formatting is pure Python work that no amount of streaming avoids. Members are independent,
so they parallelise cleanly; the parent still appends them in task order, which keeps the
member order, the `manifest.csv` row order and the verifier's `expected` list identical to
the serial path. A part file is deleted the moment it is in the archive. Each worker builds
its own boto3 client, because one does not survive a fork.

`manifest_rows.jsonl` exists because `manifest.csv` is written once at the end of a run while
`--resume` builds only the bundles that are missing. Without the sidecar, a resumed run would
publish a record index that omitted every bundle an earlier run had uploaded.

`ZIP_STORED` (no deflate) is deliberate: the members are already gzip, so re-compressing costs
CPU and gains nothing, and stored members let a reader stream one matrix out of a bundle without
decompressing the whole archive.

CLI:

```
python build_and_upload.py --token-env ZENODO_TOKEN [--sandbox] \
    [--bundles grid_strict__*,prepared_inputs__*] \
    [--decimals 4] [--min-free-gb 3] [--max-record-gb 46] \
    [--dry-run] [--resume] [--no-upload]
```

- `--dry-run` resolves every S3 key, prints the bundle table and the projected size, writes
  nothing. **Run this first.**
- `--resume` reads the deposition's existing file list and skips bundles already uploaded with a
  matching MD5 — the pipeline is interruptible, which matters over a multi-hour upload.
- `--no-upload` builds and verifies one bundle at a time and deletes it without uploading; used
  to rehearse the transform without a token.

**Experimental variant, to be tested in sandbox only.** `requests` will stream a `PUT` from a
generator, which sends `Transfer-Encoding: chunked` and would let a bundle be piped straight from
the ZIP writer to Zenodo with *zero* bytes on disk. Invenio's bucket endpoint is not documented
to accept chunked uploads, and a chunked PUT cannot be resumed. Try it against
`sandbox.zenodo.org` with one small bundle; if it works it is a nice-to-have, and if it does not
the disk-backed path above is unaffected.

### 4.4 Budget and disk guards

| Guard | Value | Behaviour on breach |
|---|---|---|
| `MAX_BUNDLE_GB` | 3.0 | bundle is split into `_partN` at manifest-build time |
| `MAX_FILES` | 100 | build aborts before uploading anything |
| `MAX_RECORD_GB` | 46.0 | lowest-priority bundles are **dropped whole** and recorded in `manifest.csv` as `deposited=false`; a bundle is never truncated |
| `MIN_FREE_GB` | 3.0 | build stops cleanly before starting a bundle that would not fit |
| `--workers` | `min(6, cpu-2)` | look-ahead capped at `workers + 2` parts, so `work/parts/` adds well under 1 GB beside the growing ZIP |

Priority order, lowest first (i.e. first to be dropped): `sweep_methods__…knn`,
`sweep_methods__…softimpute`, `sweep_strategies__…`, `prepared_inputs__knn`,
`prepared_inputs__softimpute`, then everything else. The complete `strict` grid, the standalone
tables, `best15` and `decision_tree` are never dropped.

Peak JupyterHub disk: the largest bundle (2.85 GB after the 3 GB cap) plus streaming buffers,
so **< 3.5 GB against ~10 GB free**. No S3 source file is ever written to disk; the largest one
is 872 MB and it is consumed as a stream.

### 4.5 `verify_bundle.py` — verification that happens *before* each upload

The first draft of this plan verified the whole deposit after building it. That is impossible
with a 10 GB disk, so verification moves inline. Every check runs against the in-memory
transformed matrix or the finished bundle, before the bundle is uploaded and deleted:

Per member:
1. The first column contains **zero** IDs from `PROP_IDS`.
2. Row count equals `EXPECTED_COUNTS[strat][1]` for `post0` and prepared members.
   For `post1` it is only bounded by it — see §6 caveat 17.
3. For annotation members: exactly 191 annotation columns; `PUBLIC_SAMPLE_LABEL` has zero proprietary
   hits; `Major_group` values are within the allowed set; `AUTHOR`, `bags_class` and
   `avicennaid` are absent as column names.
4. No forbidden token anywhere in the member — `bags_class`, `avicennaid` and
   `shambhala_[A-Za-z0-9]` inline, plus the site tokens supplied through
   `FL_FORBIDDEN_EXTRA` and `FL_LEGACY_LABEL` (the internal bucket and registry
   names, the pod prefix, the work e-mail, the R3 group label).
   For annotation members the scan covers every row, not a sample — see §6 caveats 15
   and 18.
5. Rounding fidelity, on a 1-in-25 sample of members: re-read the S3 original for a
   200 × 500 block and assert `max|Δ| ≤ 5e-5` and Pearson r = 1.0 to 12 dp.

Per bundle:
6. Member count and names match `manifest.csv`; the ZIP opens and every member's CRC validates.
7. Zenodo's reported MD5 equals the locally computed MD5 **before** the local copy is deleted.

Any failure aborts the run with a non-zero exit and leaves the bundle on disk for inspection.
Because the record is a draft until explicitly published, a failure mid-run is recoverable:
delete the offending file from the draft and `--resume`.

### 4.6 `readme_templates/_common_caveats.md`

Included verbatim in the record README. Draft text:

> **What is withheld, and why the counts differ from the article.**
> The analysis behind this article used 7,174 samples from 88 cohorts. This record contains
> 5,178 samples from 73 cohorts. Fifteen cohorts are proprietary or under controlled access, and
> for those neither expression values nor per-sample annotation — including the sample
> identifiers — may be redistributed. All 88 cohorts are still *named*, with the sample count
> each contributed, in `cohorts.csv`. This is a redaction of the deposited files, not a
> discrepancy in the science: every statistic, figure and metric in the article was computed on
> the full 7,174 samples.
>
> **These matrices are subsets, not re-runs.** Each deposited matrix is the exact matrix the
> article's metrics were computed on, with the proprietary rows deleted. It is *not* the result
> of re-harmonizing the 5,178 open samples. Because batch correction is a function of the whole
> matrix, re-running the pipeline on the open subset is a different experiment, not a
> replication, and its metrics will not match the published tables.
>
> **Withheld fractions are not uniform.** `C_rnaseq_only` retains 878 of 2,243 samples (39%) and
> `J_ff_only` 2,203 of 3,167 (70%); `F_microarray_only` and `K_ffpe_only` retain 87% and 86%.
> See `strategy_sample_counts.csv`.
>
> **Annotation schema.** The deposited annotation has 192 columns — a sample identifier
> and 191 annotation fields. The internal schema has 486,
> of which 293 are empty for every public sample and one identifies a colleague; all 294 are
> removed. Two columns are renamed to say what they contain rather than which internal system
> produced them (`bcell_type_call`, `treatment_regimen_detail`); their values are unchanged.
>
> **Shambhala.** One Shambhala configuration is included, the default `P0std × Q0std`
> calibration pair, named `20_shambhala` — the same name used in the article's Supplementary
> File 3. Seventeen further P/Q variants were run during the benchmark and are not deposited:
> they are excluded from the article, and their matrices are available from the authors on
> request.
>
> **Numeric precision.** Values are log2-scale and rounded to 4 decimal places (maximum absolute
> error 5·10⁻⁵). The unrounded values differ only in float64 noise.
>
> **Orientation and conventions.** Matrices are **samples × genes** (rows = samples). Gene
> symbols are HGNC. Values are log2(x+1)-transformed per cohort. The first column holds the
> sample identifier under an empty header cell. ZIP members are stored, not deflated, so a
> single matrix can be streamed out without expanding the archive.
>
> **Where to start.** `manifest.csv` indexes every one of the 995 matrices — which bundle it is
> in, its shape, its checksum, and whether it is one of the 15 clustermap-derived best
> approaches (`is_best15`) or a decision-tree recommendation (`is_decision_tree`).
>
> **Attribution.** These matrices are derived from 73 publicly deposited studies. Please cite
> the original studies as well as this deposit; accessions are in `cohorts.csv`.

---

## 5. Files that do NOT change

| File / area | Why it is untouched |
|---|---|
| `harmonization-scripts/bench_shared.py` and every worker/dispatcher | The deposit reads S3; it does not re-run the benchmark. No constant, strategy or method registry changes. |
| `harmonization-metrics-calculation/*` | Same. Metric tables are copied and filtered, not recomputed. |
| Any notebook | The deposit is a build artefact, not an analysis. |
| `comb_ann_unified.csv` and `comb_ann_public.csv` (this tree) | Both unredacted. The deposit's annotation is produced by `redact_lib.redact_annotation()` from the S3 prepared master, so no pre-redacted file needs to be trusted. |
| `make_public_supplementary.py` in the mirror | Already does its job for the repository's tables; `redact_lib.py` reimplements the same recipe so the deposit does not depend on a cross-repository import. The two must agree — §7 check 4d compares their outputs column for column. |
| The S3 bucket | Read-only throughout. Nothing is written back. |
| The local Mac | Nothing is downloaded to it. The build runs on JupyterHub. |

**Documents that DO need a follow-up edit once the DOI exists** (deferred until after
publication, listed here so they are not forgotten — they appear in the TODO):

- `<public mirror>/DATA_AVAILABILITY.md` — the sentence *"Expression matrices are
  **not** in this repository for any cohort"* becomes misleading the moment the record is
  published. Rewrite to keep the repository-vs-deposit distinction and point at the DOI.
- `<public mirror>/README.md` — add a Data section with the concept DOI.
- `figures_for_article/FL_manuscript_versions/` — the Data Availability statement.
- `CITATION.cff` in the mirror — add the dataset DOI as a `reference`.

---

## 6. Side effects and caveats

1. **Publishing is irreversible.** A published Zenodo record's files are immutable; a mistake
   costs a new version, and the old version stays visible forever. The sandbox rehearsal must
   succeed and every bundle must pass §4.5 before `--publish`.
2. **The annotation twins were the plan's own blind spot.** The 42 prepared annotation files
   carry the same 486-column internal schema as `comb_ann_public.csv`, with the same five
   surviving leaks (§1h). Depositing them raw would have published `AUTHOR`, `bags_class`,
   `avicennaid`, the 76 `MPI-###` proprietary labels and the internal group label, 42 times
   over. Every deposited annotation now goes through one function and one 191-column whitelist,
   and §7 check 4d compares the result against the mirror's independently produced copy.
3. **Row filtering is not redaction.** The 260830 plan learned this twice, and §1h is the third
   instance. Any deposited table whose *cells* can hold a sample identifier needs a column-wise
   pass, not just a row filter — and the verifier greps every member for all 1,996 IDs anyway.
4. **`20_shambhala` must be applied consistently or the joins break.** The rename and the
   17-variant drop apply to `metrics_comprehensive`, all three long tables, `gene_qc_long`,
   and the matrix filenames. If one table keeps non-default `shambhala_*` rows while another drops
   them, the `run_id` join goes orphan. §7 check 4c asserts that the method vocabulary of every
   deposited table is exactly the 33 names in `methods_registry.csv` — and that
   `metrics_comprehensive` has 2,407 rows, matching `Supplementary File 3` run for run.
5. **`C_rnaseq_only` is 39% public.** Anyone reusing that strategy's matrices on the open subset
   is working with a third of the RNA-seq arm. Called out in the README, in
   `strategy_sample_counts.csv`, and in `manifest.csv` per row.
6. **Per-cohort statistics for withheld cohorts are still deposited.**
   `marker_cohort_correlations_long.csv` carries a `cohort` column with rows for all 88 cohorts,
   including the 15 proprietary ones — aggregate ρ values computed from samples that are not
   themselves published. Rule R1 permits naming a proprietary cohort, and the public GitHub
   mirror already publishes this table, so the deposit follows that precedent. **Flagged for
   Daniil**: if that precedent is to be revisited, it must be revisited in the mirror and the
   deposit together, not in one of them.
7. **No bytes touch the local Mac.** The build runs on JupyterHub, streams from S3, and holds at
   most one bundle on disk. If JupyterHub free space drops below `MIN_FREE_GB` the run stops
   cleanly at a bundle boundary and `--resume` picks it up.
8. **There is no S3 → Zenodo direct transfer.** Zenodo has no server-side ingest-from-URL, and
   every matrix needs transforming regardless, so the bytes must pass through the build host.
   The chunked-PUT variant in §4.3 is the only way to avoid a disk-backed bundle, and it is
   unproven against Invenio and unresumable — test it in sandbox, do not depend on it.
9. **Wall-clock.** **Measured 2026-09-13, and the original estimate was wrong.** One process
   sustains **59 MB of deposit per minute** at 98% of one core — the `%.4f` formatting of
   ~15 billion values, exactly as predicted, but three times slower than assumed. Serially
   that is **~12.5 h**, not 2.5–3 h. `write_bundle()` therefore transforms members on a
   `ProcessPoolExecutor` (`--workers`, default `min(6, cpu-2)`; this node has 8 vCPU) and the
   parent appends each finished part to the ZIP in order, with look-ahead capped at
   `workers + 2` so `work/parts/` stays small. Run it detached — a plain `nohup … &` launched
   from a tool call **was reaped** when its shell exited; use `setsid`.
10. **`pandas.read_csv(chunksize=...)` dtype drift.** Chunks are typed independently. For the
    expression matrices every body column is float and this is safe; for the annotation files
    pass `dtype=str, keep_default_na=False` so a chunk boundary cannot silently retype a column
    or turn the string `"NA"` into a NaN that writes back as empty.
11. **Licence scope.** CC BY 4.0 covers Daniil's derived matrices and tables. It does not and
    cannot re-license the 73 source studies. The README's attribution paragraph and
    `cohorts.csv` carry that; do not deposit under CC0 (which is why Dryad is rejected in §2b).
12. **The 100-file cap is the fragile constraint, not the 50 GB.** At 60 files (53 before
    the Option C re-split) there is headroom, but any change that unbundles a slice or adds
    per-matrix files will hit it fast.
    The builder aborts at 100 rather than producing an unuploadable record.
13. **The five Shambhala calibration matrices** that `DATA_AVAILABILITY.md` records as withheld
    (derived from proprietary cohorts) stay withheld; `calibration_datasets/` is out of scope.
    Note that `P0_standard.csv` and `Q0_standard.csv` — the two that define `20_shambhala` — are
    **not** among the withheld five and could be added to the record later if a reader asks how
    the deposited Shambhala run was calibrated.
14. **The public mirror still ships a column named after the internal classifier.**
    Comparing the whitelist this pipeline derives against
    `<public mirror>/comb_ann_public.csv` on 2026-09-13 found the two schemas
    identical at 191 names with exactly one difference: the deposit renames `bags_class`
    → `bcell_type_call`, the mirror does not. §Class 3a edit 5 of the 260910 transfer plan
    specified that rename and it did not land — and that plan predicted precisely why it
    would be missed, since `bags_class` does not match the label verification grep.
    **The deposit is correct; the mirror needs the same one-line fix**, plus a widened
    grep. Flagged for Daniil as a separate repository edit, outside this deposit's scope.
15. **The legacy group label was in a third column, and §1h did not look for it.**
    The first build of `comb_ann_public.csv` still carried the internal label in 710 cells of
    `Diagnosis_cell_type_general`; §1h had audited only `Major_group` and
    `Diagnosis_with_coo`. Worse, the verifier would probably not have caught it either:
    its annotation content scan looked at `head(50)` rows, and the leak was 710 rows out
    of 5,178 in a single column. Both were fixed — the scan now covers every row of
    every annotation member, which costs nothing on a 3.6 MB file, and
    `redact_annotation()` sweeps **every** column with a token-bounded
    pattern instead of two named columns. Two consequences worth recording: the public
    cohort `PUB_DLBCL_BAGS` — the published BAGS classifier, not the internal product —
    is deliberately left alone and does not match the label grep; and the old
    prefix rule silently ate the separator (`<label>_Centrocyte` →
    `Normal_B_cellsCentrocyte`), which the token rule fixes.
16. **The raw matrix is wider than the cohort, and holds one sample twice.**
    `exp/comb_exp.tsv` predates the cohort's QC: filtering it by proprietary rows alone
    gives 5,242 rows, not the 5,178 §3a specifies — 63 public samples the final
    7,174-sample cohort later dropped, plus `SRX2422726` written twice.
    `redact_and_round()` grew a `keep_ids` argument and `build_source_tables()` passes
    the deposited annotation's own sample set, so `comb_exp_public.tsv.gz` joins to
    `comb_ann_public.csv` row for row. The count is now asserted, as the annotation's
    already was.
17. **`post1` members have fewer rows than the strategy, by design.**
    §4.5 check 2 pinned every member's row count to `EXPECTED_COUNTS[strat][1]`, which is a
    `post0` figure. Post-normalization outlier removal drops samples, sometimes most of them:
    `C_rnaseq_only__strict__01_raw__post1` holds 325 of that strategy's 878 public samples,
    and the S3 original agrees (1,304 of 2,243 total). The first rehearsal build failed on
    this. The check now pins `post0` and prepared members and merely bounds `post1` at
    `0 < rows <= post0`; the exact per-member count is in `manifest.csv`. Worth saying in the
    README: a `post1` matrix is not a row-aligned twin of its `post0` sibling.
18. **The Shambhala guard rejected every legitimate member.** `shambhala_(?!P0std)`
    was written to catch raw calibration-variant names, but the deposited public name
    is `20_shambhala` followed by the `__` field separator, so `shambhala_` matched
    with `_post0` after it and the standalone verifier refused the bundle. The guard is
    now `shambhala_[A-Za-z0-9]`: a variant name always has an alphanumeric after the
    underscore (`shambhala_NBKass_Q0std`), a deposited name never does. Note the
    negative lookahead was also the wrong shape on its own terms — it would have
    *allowed* `shambhala_P0std_Q0std`, the one raw name the rename exists to remove.

19. **Two methods deposit mostly-empty matrices, and nothing said so.** `34_arsyn` and
    `38_harman` return ~87% NaN in all 84 of their runs each — the S3 sources genuinely
    are that way; these are two of the known R-package startup failures. The article's
    analysis set already filtered them out, but `status` reads `ok`, and 168 such
    matrices are in the deposit. Daniil's call (2026-09-13): **keep them, and flag
    them** — dropping them would leave the metric tables pointing at 168 matrices that
    are not in the record. `manifest.csv` grew a `pct_na_cells` column, joined from the
    deposited metrics table rather than recomputed so the record quotes one number, and
    the README names both methods.
20. **Not every method returns log2, and not every method returns the full gene set.**
    The README claimed `log2(x+1)` for all matrices. True of the inputs, false of
    several outputs: `18_rank` and `25_angel` return ranks in [0,1], `23_vst` a
    variance-stabilised scale, `28_npn` a z-like scale, `19_tdm` a target range ~1–92,
    and `20_shambhala` is **linear** (~15–110,000). Seven mean-centring methods return
    negatives. `20_shambhala` and `25_angel` also return reduced gene spaces (2,293 and
    3,582 genes where the strategy has 6,797). The README now says so and points at
    `manifest.csv`'s `n_genes`.
21. **zenodo.org went down mid-launch, 2026-09-13.** The first production run died on
    `POST /deposit/depositions` with a 504; probing showed 504 on the public API and on
    the site's own home page, while sandbox.zenodo.org answered normally — a Zenodo
    outage, not the token and not this code. Nothing had been uploaded. The real hazard
    it exposed: `_request` retries 5xx, and a gateway timeout on a POST can still have
    created the deposition, so one outage could have left several duplicate drafts each
    holding part of a 45 GB record. `create_draft` is now preceded by `find_draft()`,
    which reuses an existing unpublished deposition with the same title. Retries also
    went from 5 to 8 with the backoff capped at 60 s, and every request carries a
    `(30, 1800)` timeout — a multi-GB PUT holds the socket while Zenodo checksums it,
    and an untimed hung socket would stall the run forever. Sitting out a long outage is
    not the retry loop's job; `--resume` is.
22. **Shambhala returns the samples in a different order, and the rounding check assumed
    it did not.** The second production run uploaded ten bundles and then died inside
    `check_rounding()` with `ValueError: zero-size array to reduction operation maximum`
    on `grid_strict__G_affymetrix_only`. The check compared the deposited head — 200 rows
    — against only the first 600 rows of the S3 original, which is correct exactly when
    redaction preserves row order. It does for every other method; `20_shambhala` emits
    the proprietary `MPI-*` samples first, so the deposited head sat far below row 600
    and the two blocks shared no row at all. G was the first bundle whose one-in-25
    sampler happened to draw a Shambhala member — the earlier ten passed by luck, not by
    correctness. The check now reads the original in full but keeps only the deposited
    block's columns (the header is read off the same stream, then `usecols`), so the
    block is matched by **label** rather than by position; it is also faster than the old
    positional read, 2.5–3.3 s per member. An explicit `VerificationError` replaced the
    numpy crash for the case where the overlap really is empty. Re-verified on the
    already-built G bundle: 56 members, all checks green, `max|Δ| = 5·10⁻⁵` on both
    sampled members.
23. **Two reference-based harmonizers return fewer samples than the strategy they were
    run on, and the row-count check pinned the strategy figure.** Run 3 uploaded
    `grid_strict__G_affymetrix_only` and then failed on
    `H_affymetrix_extended__strict__19_tdm__post0`: 2,978 rows where the check demanded
    3,096. The deposit was faithful — the S3 original itself holds 3,609 of the
    strategy's 3,727 rows, of which 631 are proprietary, so 2,978 public rows is exactly
    right. Caveat 17 had already relaxed the pin for `post1`; this is the same wrong
    premise surviving in the `post0` branch. The scope was measured over all 1,204 post0
    attempts in `metrics_comprehensive_260905.csv`: **exactly four fall short, every one
    in `H_affymetrix_extended`, every one by the same 118 samples** — one `19_tdm` and
    the three imputations of `20_shambhala`. The 118 are identical between the two
    methods and are all public: three singleton Affymetrix batches, `GPL20188` (68),
    `GPL23541` (35) and `GPL26356` (15), all FF with an unknown source, spread over
    `GSE68878`, `GSE99635`, `GSE69033` and `GSE149089`. Both methods are reference-based
    and discard a batch they cannot map onto the reference. Fixed with
    `SHORT_POST0_PUBLIC_ROWS` in `zenodo_manifest.py`, a keyed exception rather than a
    blanket bound, so an accidental over-filter in any of the other 1,200 post0 members
    still fails. Two deposited members are affected — `19_tdm` and `20_shambhala`,
    `post0`, in the H bundle — and the record README says so. Re-verified on the
    already-built H bundle: 60 members, 2.54 GB, all checks green.
24. **`_request` retried status codes but not dropped connections.** Run 4 uploaded
    `grid_strict__G_affymetrix_only`, rebuilt and verified H, and then died on the H PUT
    with `ssl.SSLEOFError: EOF occurred in violation of protocol`. Caveat 21 had raised
    the retry count to 8 and capped the backoff, but the loop only ever inspected
    `response.status_code` — a transport failure raises before there is a response, so
    it escaped the loop entirely and killed the run. A multi-GB PUT holds the socket for
    minutes while Zenodo checksums the body, which is exactly when the far side drops
    it, so this is a normal event over a 45 GB deposit rather than an outage. The loop
    now catches `requests.exceptions.RequestException` around the request call on the
    same backoff schedule, and re-raises on the final attempt. Only the call is guarded,
    not `raise_for_status()`, so a 4xx still fails immediately instead of being retried
    eight times. The retry is safe because `body_factory` already hands out a fresh file
    handle per attempt and a bucket PUT replaces whatever is at the key; the existing
    post-upload MD5 comparison catches a partial body. The failed PUT left nothing on
    the draft — it stayed at 11 files / 18.49 GB.
25. **The legacy-label rename left a dangling separator, and only step 4d saw it.**
    Daniil supplied the mirror's `comb_ann_public.csv` on 2026-09-14, which finally made
    §7 step 4d runnable. Shapes and sample sets matched exactly, and the only column
    difference was the expected `bags_class` / `bcell_type_call` pair of caveat 14 —
    but a cell-by-cell comparison of the 191 shared columns found **710 disagreements in
    `Diagnosis_with_coo`**: the deposit said `Normal_B_cells_`, the mirror said
    `Normal_B_cells`. The source value on S3 is literally `<label>_` in 734 of the 7,174
    rows — the column is diagnosis + cell-of-origin, and normal B cells have no cell of
    origin, so the separator is there with nothing after it. Caveat 15's token-bounded
    rule is right about the token and says nothing about the orphaned separator, so the
    rename produced a trailing underscore that the mirror's independently written script
    does not. `redact_annotation()` now strips exactly `^<replacement>_$` and nothing
    else. Nothing uploaded was affected: none of the twelve bundles built by then
    contains an `__ann` member, and the standalone tables upload last. The three
    `prepared_inputs__*` bundles do carry annotations, so the run was restarted before
    reaching them — an editing process does not pick up a changed module. After
    regenerating, the deposit and the mirror differ in **23 cells of one column,
    `ldh`**, where the mirror writes `156.0` and the deposit writes `156`; the two are
    numerically identical, and the deposit's rendering is the cleaner one.
    A second trap surfaced while regenerating: `work/ann_columns.txt` must be read with
    `splitlines()`, never `split()` — three whitelisted column names contain a space, and
    whitespace-splitting silently turns 191 columns into 194 tokens and a short file.
26. **The size estimator runs ~8.7% low, and the record will exceed the plan's budget.**
    Measured against the first eleven uploaded bundles, `GZIP_SHRINK = 2.97` under-calls
    every grid bundle: 17.01 GB estimated against 18.49 GB actual. Extrapolated, the
    record lands at **≈48.5 GB**, past the 46 GB budget of §4.4 and inside Zenodo's 50 GB
    free quota by only ~1.5 GB. `apply_budget()` works from estimates and therefore never
    trips. Daniil's call, 2026-09-14: **keep all 27 bundles and accept ≈48.5 GB** rather
    than drop the lowest-priority knn method sweeps. `zenodo_progress.py` reports the
    live figure against the quota so the margin stays visible.
27. **`SHA256SUMS.txt` covered only the standalone tables, not the 34 bundles.** The
    checksum file is written by iterating `work/tables/`, and a bundle never appears
    there: it is streamed S3 -> transform -> ZIP and `unlink`ed by `upload_one()` the
    moment its PUT returns, which is the whole point of the ~10 GB disk design. So the
    copy run 12 deposited listed 25 files and left **47.8 of 48.17 GB uncovered**, while
    the README's contents table promised "checksums of every top-level file". Nothing was
    unverifiable in fact — `manifest.csv` carries a `sha256_bundle` per bundle (34
    distinct 64-char digests), and every PUT was MD5-checked against Zenodo's own
    checksum by `upload_one()` — but the record's advertised checksum file did not match
    its advertised scope. Fixed 2026-09-15 by seeding the digest map from `manifest_rows`
    before hashing `table_dir`, which is also what makes the file correct on a **resumed**
    run, whose bundles were built by an earlier process and are long gone from disk. The
    deposited replacement has 59 entries (34 bundles + 25 tables). Verified end-to-end
    before re-upload: `best15_clustermap_approaches.zip` was re-downloaded from the draft
    and its SHA-256 recomputed from the deposited bytes, matching `manifest.csv` exactly,
    which is what licenses reusing the build-time digests for the other 33 bundles instead
    of re-downloading 48 GB. The 25 table digests were recomputed from the local copies
    after confirming all 25 MD5s still match the draft.
---

## 7. Verification commands

Run on **JupyterHub**, from `datasets_for_zenodo/`, with the project venv active.

```bash
source ~/venvs/collagen_3_11/bin/activate

# 0. Re-derive the proprietary ID list (never type it, never cache it into git)
python - <<'PY'
import csv, pathlib
root = pathlib.Path("..")
short = root/"figures_for_article/supplementary_260824/Supplementary File 1 short.csv"
full  = root/"figures_for_article/supplementary_260824/Supplementary File 1.csv"
prop_cohorts = {r["COHORT_LABEL"].strip() for r in csv.DictReader(open(short))
                if r["Cohort type"].strip() == "Proprietary"}
rows = list(csv.DictReader(open(full))); key = list(rows[0].keys())[0]
ids = sorted({r[key] for r in rows if r["COHORT_LABEL"] in prop_cohorts})
assert len(prop_cohorts) == 15 and len(ids) == 1996, (len(prop_cohorts), len(ids))
pathlib.Path("prop_ids.txt").write_text("\n".join(ids) + "\n")
print("OK 15 cohorts / 1996 ids")
PY

# 1. Derive and freeze the annotation whitelist.
#    Expect 485 annotation columns -> 293 empty -> 192 -> minus AUTHOR -> 191.
python -c "
import redact_lib as R
ids = R.derive_prop_ids('..')
cols = R.annotation_whitelist('prepared/S0_no_removal__strict__ann.tsv.gz', ids)
print(len(cols), 'columns'); assert len(cols) == 191
assert 'AUTHOR' not in cols   # bags_class / avicennaid are renamed, not dropped
"

# 2. Dry run: resolve every S3 key, print the bundle table and the projected size.
#    Expect 53 files, 27 bundles, 995 matrices, ~45.2 GB projected, and an explicit
#    list of (strategy, imputation, method) combinations that have no S3 output.
python build_and_upload.py --dry-run

# 3. Transform-only rehearsal of one bundle, no token needed, nothing uploaded
python build_and_upload.py --bundles grid_strict__C_rnaseq_only --no-upload

# 4. Spot checks, on a bundle still in work/ (use --no-upload to keep one there)

# 4a. Zero proprietary sample IDs in any member (Aho-Corasick; a 1,996-way regex
#     alternation takes >15 min, grep -F takes seconds)
python - <<'PY'
import zipfile, gzip, io, pathlib
prop = set(open("prop_ids.txt").read().split())
for z in pathlib.Path("work").glob("*.zip"):
    with zipfile.ZipFile(z) as zf:
        for n in zf.namelist():
            with gzip.open(io.BytesIO(zf.read(n)), "rt") as fh:
                next(fh)
                hits = sum(1 for line in fh if line.split("\t", 1)[0] in prop)
            if hits: print("LEAK", z.name, n, hits)
print("leak scan done")
PY

# 4b. Row counts per strategy match §1c
python verify_bundle.py work/*.zip --check row-counts

# 4c. Method vocabulary is exactly the 33 deposited names, and the metrics table
#     agrees with Supplementary File 3 run for run — expect 2407 and an empty diff
python - <<'PY'
import csv, gzip
dep = {r["method"] for r in csv.DictReader(open("work/metrics_comprehensive_260905.csv"))}
with gzip.open("../figures_for_article/supplementary_260824/Supplementary File 3.csv.gz","rt") as f:
    supp = {r["method"] for r in csv.DictReader(f)}
print("deposited methods:", len(dep), "| supp:", len(supp))
print("symmetric difference:", dep ^ supp, "(expect set())")
print("rows:", sum(1 for _ in csv.DictReader(open("work/metrics_comprehensive_260905.csv"))),
      "(expect 2407)")
PY

# 4d. The deposited annotation matches the mirror's independently produced copy.
#     Two different scripts, same 191 columns and same 5,178 rows.
python - <<'PY'
import pandas as pd
a = pd.read_csv("work/comb_ann_public.csv", low_memory=False)
b = pd.read_csv(f"{MIRROR}/comb_ann_public.csv", low_memory=False)  # public mirror checkout
print("deposit:", a.shape, "| mirror:", b.shape, "(expect 5178 x 192 both)")
print("column diff:", set(a.columns) ^ set(b.columns),
      "(expect {bags_class, bcell_type_call} — see caveat 14)")
prop = set(open("prop_ids.txt").read().split())
print("PUBLIC_SAMPLE_LABEL proprietary hits:", int(a["PUBLIC_SAMPLE_LABEL"].isin(prop).sum()),
      "(expect 0)")
print("Major_group:", sorted(a["Major_group"].dropna().unique()))
PY

# 4e. No internal identifiers, no removed product name, no non-default Shambhala
python - <<'PY'
import zipfile, gzip, io, pathlib, re
import os
# Generic tokens inline; site tokens from the environment, never spelled out in a
# file that is mirrored publicly — the same contract as verify_bundle.build_forbidden().
extra = [t.strip() for t in os.environ.get("FL_FORBIDDEN_EXTRA", "").split(",") if t.strip()]
extra += [t for t in [os.environ.get("FL_LEGACY_LABEL")] if t]
pat = re.compile("|".join([r"bags_class|avicennaid|shambhala_[A-Za-z0-9]"]
                          + [re.escape(t) for t in extra]).encode(), re.I)
for z in sorted(pathlib.Path("work").glob("*.zip")):
    with zipfile.ZipFile(z) as zf:
        for n in zf.namelist():
            if pat.search(n.encode()): print("NAME HIT", z.name, n)
            head = gzip.decompress(zf.read(n))[:200_000]
            if pat.search(head): print("CONTENT HIT", z.name, n)
print("token scan done")
PY

# 4f. Rounding fidelity against freshly streamed S3 originals
python verify_bundle.py work/*.zip --check rounding --sample-rate 25 --seed 0

# 4g. Zenodo limits and disk headroom
python build_and_upload.py --dry-run | tail -20   # asserts <=100 files and <=46 GB
df -h "$HOME" | tail -1

# 5. Sandbox rehearsal, end to end, on the two smallest bundles
export ZENODO_SANDBOX_TOKEN=...
python build_and_upload.py --sandbox --token-env ZENODO_SANDBOX_TOKEN \
    --bundles best15_clustermap_approaches,decision_tree_recommended

# 6. Production build + upload, resumable, under nohup
export ZENODO_TOKEN=...
nohup python build_and_upload.py --token-env ZENODO_TOKEN --resume \
    > zenodo_build.log 2>&1 &
tail -f zenodo_build.log
```

---

## TODO

**Implementation status, 2026-09-13.** Every script exists and every check that can run
without the build host has been run: the module imports, the synthetic-fixture transform
tests, the live `--dry-run` against S3, the live 191-column whitelist derivation, and the
live metrics filter (3,835 → 2,407 rows, 33 methods, `20_shambhala` = 84). What remains is
the build itself, which by design only happens on JupyterHub — nothing of the deposit
payload is staged on the laptop.

### Phase 0 — decisions (blocking)
- [x] Platform: **Zenodo** — confirmed
- [x] **One record**, ~40–45 GB, ZIP-bundled — confirmed
- [x] **Best-15** clustermap approaches included — confirmed; all 15 exist on S3 (§1g)
- [x] Shambhala: **default P0std × Q0std only, named `20_shambhala`** — confirmed; verified
      live that the filter reproduces Supplementary File 3's run set exactly (§1f)
- [x] Build and upload from **JupyterHub**, one file at a time, never via the Mac — confirmed
- [x] Daniil confirms **4-decimal rounding** (error ≤ 5·10⁻⁵; implemented as the default,
      overridable with `--decimals`) — confirmed 2026-09-13
- [x] Daniil confirms **CC BY 4.0** for the data (drafted in `readme_templates/` and
      `zenodo_metadata.json`) — confirmed 2026-09-13
- [x] Daniil rules on §6 caveat 6 — per-cohort ρ rows for the 15 withheld cohorts:
      **keep**, matching the mirror's existing precedent (2026-09-13)
- [x] Daniil fills the `FILL_ME` fields in `zenodo_metadata.json` (2026-09-13):
      affiliation = Institute of Molecular Biology, NAS Armenia; ORCID 0000-0003-1029-1174
      (read off his own earlier Zenodo records); `isDerivedFrom`
      https://github.com/Nikit357/FL_harmonization. The `isSupplementTo` entry is
      **removed** — no article DOI exists yet; add it in the web form before publishing
- [x] Decide publish-now vs. embargo: **neither — the record stays an unpublished
      draft.** Everything is uploaded and the DOI reserved; Daniil presses Publish
      himself once the article is ready (2026-09-13)

### Phase 1 — scaffolding *(complete)*
- [x] `datasets_for_zenodo/.gitignore` — ignores `work/`, `prop_ids.txt`, `*.log`
- [x] `zenodo_manifest.py` — constants, `EXPECTED_COUNTS`, `BEST15`, `DECISION_TREE_PICKS`,
      `Bundle` dataclass, `build_bundles()` with live S3 resolution, 3 GB splitting,
      Tier-2-against-Tier-1 deduplication, priority ordering, `apply_budget()`
- [x] `readme_templates/_common_caveats.md` — the §4.6 text
- [x] `readme_templates/record_readme.md` — title, contents table, naming, how-to-read,
      with an `<!-- INCLUDE: -->` marker expanded at build time by `render_readme()`
- [x] `readme_templates/LICENSE-CC-BY-4.0.txt` — with the scope note that the licence does
      not extend to the 73 source studies
- [x] `zenodo_metadata.json` — record metadata with `FILL_ME` placeholders that block upload

### Phase 2 — `redact_lib.py` *(complete)*
- [x] `derive_prop_ids()` — asserts 15 cohorts / 1,996 ids; **verified live: 1,996**
- [x] `annotation_whitelist()` — master rule, asserts 191, writes `work/ann_columns.txt`;
      **verified live: 191 columns, `AUTHOR` dropped**
- [x] `redact_annotation()` — row filter, whitelist, `PUBLIC_SAMPLE_LABEL` blanking,
      the legacy-label rename **across every column** (widened 2026-09-13, §6 caveat 15),
      `bags_class` / `avicennaid` rename.
      The legacy label is *not* hardcoded — pass `--legacy-label` or `FL_LEGACY_LABEL`,
      matching the mirror's `make_public_supplementary.py` precedent
- [x] `redact_and_round()` — streaming, with a `gzipped` flag for the one plain-TSV input
      and a `keep_ids` filter for the raw matrix, whose sample set is wider than the
      cohort's (§6 caveat 16)
- [x] `test_transforms.py` — five tests on a synthetic fixture, including the `_is_empty`
      NaN trap and two planted leaks that the verifier must reject. **All pass**

### Phase 3 — `build_and_upload.py` *(complete)*
- [x] S3 streaming reader (`get_object()["Body"]`, no local source copy)
- [x] Incremental `ZIP_STORED` bundle writer, member written straight into the archive
- [x] Disk guard (`MIN_FREE_GB`), record budget (`MAX_RECORD_GB`), file cap (`MAX_FILES`)
- [x] `manifest.csv` row per matrix incl. `is_best15`, `is_decision_tree`, `deposited`
- [x] Zenodo client: create draft, `prereserve_doi`, bucket `PUT`, MD5 confirm, delete local
- [x] `--resume` against the draft's existing file list; `--dry-run`; `--no-upload`
- [x] Experimental chunked-PUT path behind `--chunked-upload`, refused outside `--sandbox`
- [x] **Parallel member transform** added 2026-09-13 after the serial rate was measured at
      59 MB/min (§6 caveat 9): `ProcessPoolExecutor`, `--workers`, bounded look-ahead,
      parent assembles the ZIP in task order
- [x] **`manifest_rows.jsonl` sidecar** — `--resume` previously produced a `manifest.csv`
      containing only the bundles built in the final run
- [x] **`--dry-run` verified live**: 27 bundles + 26 tables = 53 files, 995 matrices,
      44.66 GB projected, 124 absent combinations listed (all known §1e gaps)

### Phase 4 — standalone tables *(code complete in `build_tables.py`; runs on the build host)*
- [x] Filter + rename logic **verified live in memory**: 3,835 → 2,407 rows, 33 methods,
      `20_shambhala` = 84 rows, identical to Supplementary File 3
- [x] Registries sourced from `Supplementary File 2.xlsx` — `Metric_polarity` (345 × 6) →
      `metric_dictionary.csv`, `Table_S2_metrics` (28 × 5) → `metric_group_definitions.csv`,
      `Table_S1_methods` (40 × 11) → `methods_registry.csv`. These are the manuscript's own
      curated tables; re-deriving them from source code would create a second, divergent
      description of the same thing, so the plan's "from `methods_table_for_manuscript.md`"
      was superseded
- [x] `strategies_registry.csv` / `strategy_sample_counts.csv` from `EXPECTED_COUNTS`
- [x] Registries written live 2026-09-13; `methods_registry.csv` keeps all 39 benchmark
      methods with an `n_outputs_deposited_set` column, so the 6 that produced nothing
      read as 0 rather than vanishing
- [x] Run `build_metric_tables()` — writes the 12 metric tables. **Done 2026-09-13 on
      JupyterHub**: 2,407 rows in `metrics_comprehensive`, and all four long tables carry
      exactly the 33 deposited method names with no stray Shambhala variant
- [x] Run `build_source_tables()` — `comb_exp_public.tsv.gz`, `comb_ann_public.csv`,
      `cohorts.csv`, `sample_selection_by_strategy.csv`, `gene_selection_by_pair.csv.gz`.
      **Done 2026-09-13**, after the two redaction fixes of §6 caveats 15 and 16

### Phase 5 — bundles *(requires build host)*
- [x] **Rehearsal, 2026-09-13**: `grid_strict__C_rnaseq_only` built twice, once serially and
      once through the new worker pool. All 60 members, same order, identical decompressed
      SHA-256 — the pool is content-equivalent to the loop it replaces. 3.0 min incl.
      verification, against ~10 min serial
- [ ] `prepared_inputs__{strict,softimpute,knn}.zip` — 84 matrices with redacted annotations
- [ ] Tier 1 — the complete `strict` grid, 810 matrices, 15 bundles
- [ ] Tier 2 — method sweeps, strategy sweeps, `best15`, `decision_tree`, 101 matrices
- [x] No matrix appears in two bundles — enforced by `build_bundles()`'s `seen` set and
      confirmed by the dry run's member counts (810 + 101 + 84 = 995)

### Phase 6 — verification
- [x] `verify_bundle.py` — the seven checks of §4.5, non-zero exit on any failure,
      importable by the builder and runnable standalone over `work/*.zip`
- [x] §7 steps 0, 1 and 2 run green (prop IDs, whitelist, dry run)
- [x] §7 step 3 (transform-only rehearsal) and steps 4a, 4b, 4e, 4f, 4g — run 2026-09-13 on
      `grid_strict__C_rnaseq_only`. Three of the checks were themselves wrong and are fixed:
      the `post1` row count (caveat 17), the Shambhala member-name guard (caveat 18) and the
      `r == 1.0` rounding assertion, which 4-dp rounding cannot satisfy — `1 - r <= 1e-8` now,
      with `max|Δ| <= 5e-5` unchanged as the bound that matters
- [ ] §7 step 4d — compare the deposited annotation against the mirror's independently
      produced `comb_ann_public.csv`. **Cannot run here**: the mirror lives on the Mac and is
      not checked out on JupyterHub. Run it there, or copy the mirror's file over
- [x] Open two matrices out of two different bundles and sanity-check shape, dtype, range
- [x] **Row-count pin corrected for batch-dropping methods** 2026-09-14 (caveat 23) —
      `SHORT_POST0_PUBLIC_ROWS` keys the two affected members; scope measured over all
      1,204 post0 attempts, and the record README now states the 118-sample shortfall
- [x] **Rounding check made order-independent** 2026-09-14 (caveat 22) — `check_rounding()`
      matches the block by label instead of by position, so a harmonizer that reorders
      samples (`20_shambhala`) no longer produces an empty intersection. Re-verified live
      on `grid_strict__G_affymetrix_only`: 56 members OK, 1.56 GB

### Phase 7 — upload *(requires build host and a Zenodo token)*
- [x] Sandbox rehearsal — **superseded** (2026-09-13). No sandbox.zenodo.org account
      exists; Daniil chose to rehearse against the production *draft* instead, which is
      equally reversible since a draft's files can be replaced and the draft deleted.
      A transform-only rehearsal (`--no-upload`) ran first on `grid_strict__C_rnaseq_only`
- [x] Create the production draft, reserve the DOI, fill the metadata and
      `related_identifiers` — **done 2026-09-13**: draft `22737294`, reserved DOI
      `10.5281/zenodo.22737294`, state `unsubmitted`
- [ ] `nohup` the production run with `--resume`; watch `zenodo_build.log`.
      **In progress.** Run 2 (2026-09-13) uploaded 10 bundles / 16.93 GB and then died on
      caveat 22. Run 3 started 2026-09-14 with the fix, `--resume --skip-tables`; it skips
      those 10 and rebuilds from `grid_strict__G_affymetrix_only`.
      The token lives in `~/.zenodo_token` (chmod 600, outside git) and `FL_LEGACY_LABEL`
      must be exported alongside it — see the project memory note
- [x] **Before the final run, delete `manifest.csv` and `SHA256SUMS.txt` from the draft.**
      Not needed in the end: neither file ever reached the draft during runs 1-11, so run 12
      wrote both fresh from the full `manifest_rows.jsonl` and uploaded them last, exactly as
      intended. Verified: `manifest.csv` holds 995 rows over 34 bundles, all `deposited=True`,
      no placeholder rows and no stale pre-re-split `_part1` names.
      Every run writes them fresh at the end from `manifest_rows.jsonl`, but `--resume`
      skips any file already on the draft — so a copy uploaded by a partial run (runs 8+
      build a subset of the bundles) would be frozen in place and would index only the
      bundles that existed at the time. They are the two files that must be written last
- [x] Confirm the file count, ≤50 GB, every MD5 matched — **60 files (34 bundles + 26
      tables), 48.17 GB**, no missing bundles and no orphans against `build_bundles()`.
      Every PUT was MD5-checked against Zenodo's reported checksum by `upload_one()`,
      which raises on mismatch; none did.
- [x] **`SHA256SUMS.txt` completed and re-uploaded 2026-09-15.** The copy run 12 wrote
      listed only the 25 files in `work/tables/` — every one of the 34 bundles was absent,
      leaving 47.8 of 48.17 GB uncovered while the README promised "checksums of every
      top-level file". Cause and fix in §6 caveat 27. The replacement carries **59 entries
      (34 bundles + 25 tables)**, MD5-confirmed by Zenodo on upload; the draft is still
      60 files / 48.17 GB and only that one file changed
- [ ] Publish (or set the embargo date, per Phase 0)

### Phase 8 — propagate the DOI *(deferred until it exists)*
- [ ] `<public mirror>/DATA_AVAILABILITY.md` — rewrite the "expression matrices are
      not in this repository" section around the DOI
- [ ] `<public mirror>/README.md` — Data section with the concept DOI
- [ ] `<public mirror>/CITATION.cff` — dataset DOI under `references`
- [ ] Manuscript Data Availability statement — DOI + the withheld-cohort paragraph
- [ ] Transfer the six new scripts to the mirror per the 260910 plan's transfer classes; keep
      **this plan document private**

### Phase 9 — repository fix found during implementation *(separate from the deposit)*
- [ ] Rename `bags_class` → `bcell_type_call` in the mirror's `comb_ann_public.csv` and
      re-run `make_public_supplementary.py`; widen its verification grep so a column named
      after the product cannot pass again (§6 caveat 14)
