---
name: article_review
description: Review a scientific article or method for applicability to the FL lymphoma multi-platform harmonization benchmark. Use this skill whenever the user shares an article URL or DOI and asks to assess a normalization/batch correction method, review a paper, add a markdown document to harmonization-tools-research/, or check whether a tool belongs in the benchmark. Also trigger when the user says "review this paper", "assess this method", "should we add X to the benchmark", or provides a PMC/DOI link alongside any question about harmonization methods.
---

# Article Review — FL Harmonization Benchmark

This skill produces correctly formatted assessment documents for the `harmonization-tools-research/` folder. Each document records whether a method is applicable to the FL multi-platform harmonization project and why, so future conversations can skip the research phase.

---

## Project Context (always relevant)

| Parameter | Value |
|---|---|
| Dataset | ~5,444 samples, 88 cohorts, 4 platforms |
| Platforms | Affymetrix GPL570, Illumina NGS (RNA-seq), Illumina microarray, Agilent microarray |
| Batch granularity | `RNA_BATCH` — 6+ sub-platform batches (e.g. GPL570_FF, GPL570_FFPE, RNASeq_FFPE_Exome_capture) |
| Metric | One-way ANOVA R² of `RNA_BATCH` on first 10 PCA axes — lower is better |
| Baseline | Raw data ~95% batch R² |
| Benchmark winner | FSQN R (`16_fsqn_r`) — ~16% batch R² |
| Reference batch | `RNASeq_FF_PolyA` (n=1,039) |
| Downstream pipeline | oposSOM SOM analysis → requires **genes × samples expression matrix** in log2 space |
| Benchmark registry | 25 methods `01_raw` … `25_angel` in `bench_shared.py`; `26_xpn` and `27_dwd` planned |

---

## Step 1 — Fetch the Article

Use `WebFetch` with two passes on the article URL:

**Pass 1 — broad extraction:**
```
Extract: (1) paper full citation (authors, title, journal, year, DOI),
(2) all normalization/batch-correction methods evaluated or introduced,
with a brief description of each, (3) datasets used, (4) main metrics and
findings, (5) top-performing methods and the paper's recommendations.
```

**Pass 2 — deep dive on unknown methods:**
For each method not already in the benchmark, fetch again asking:
```
For method <NAME>: exact algorithm step by step, input requirements
(does it need matched samples? reference batch? specific assay type?),
output format (expression matrix vs. embedding vs. other), code/package
availability (R/Python/MATLAB, CRAN/Bioconductor/GitHub), scale
limitations, and any cross-platform or multi-cohort validation.
```

If the main URL fails (Nature paywall, redirect), try the PMC mirror. bioRxiv preprints usually work directly.

---

## Step 2 — Audit the Existing Coverage

Run both checks before assessing any method:

```bash
# List existing review documents
ls /path/to/harmonization-tools-research/

# Benchmark registry (scan METHODS dict)
grep -n '"[0-9][0-9]_' bench_shared.py | head -40
```

Build a three-column classification for every method in the paper:

| Method | Status | Key |
|---|---|---|
| Method A | In benchmark | `17_quantile` |
| Method B | Already reviewed | `MatchMixeR_usage_perspectives.md` |
| Method C | **Needs assessment** | — |

Only methods in the third row require new documents.

---

## Step 3 — Applicability Filter (apply in order)

For each unreviewed method, check these blockers. The **first blocker that applies** determines the verdict — do not keep looking for additional problems once a fatal flaw is found.

### Fatal structural blockers (method cannot run on our data)
1. **Requires matched/paired samples** — method needs the same biological specimen measured on two platforms simultaneously. Our 88 cohorts are assembled retrospectively; no matched samples exist. → `NOT APPLICABLE` (cite MatchMixeR_usage_perspectives.md as precedent)

2. **Wrong output format** — method outputs a latent embedding (PCA coords, topic vectors, cluster assignments) instead of a genes × samples expression matrix in the original gene space. oposSOM requires a full expression matrix. → `NOT APPLICABLE`

3. **Wrong problem domain** — method solves a different biological problem (cross-species, single-cell deconvolution, spatial transcriptomics) whose core assumptions are violated in our single-species bulk setting. → `NOT APPLICABLE`

4. **No code available** — no R package, Python package, or runnable implementation exists. Reimplementation from paper is feasible only if the algorithm is simple and the method has compelling unique advantages. → `NOT APPLICABLE` in most cases

5. **Platform scope mismatch** — method is validated on RNA-seq only (e.g. ComBat-seq, VST, TMM) or microarray only, and has no cross-platform extension. → `NOT APPLICABLE` unless only applied to the relevant subset

### Secondary concerns (downgrade priority, may still be benchmarkable)
6. **Wrong correction granularity** — method corrects at the platform level (4 groups) rather than `RNA_BATCH` level (6+ groups). Platform-level correction leaves within-platform batch effects uncorrected, which dominate our metric. → Lower priority; likely to underperform FSQN

7. **Scale mismatch** — method was validated on <500 samples or <10 cohorts and has no evidence of scaling to 88 cohorts. Large-scale performance is uncertain. → Note in document; do not automatically reject

8. **Functionally redundant** — method is a monotone transformation or minor variant of a method already in the benchmark. → Note the nearest equivalent; mark as low priority for addition

9. **Paper context too narrow** — study used matched samples or 2-dataset titration protocols that don't generalize to our retrospective 88-cohort structure. → Reduces confidence; note in document

---

## Step 4 — Choose Document Type

| Situation | Document type | Filename pattern |
|---|---|---|
| Single method, nuanced assessment needed (multiple blockers, indirect value, or possible future use) | Usage perspectives | `<Tool>_usage_perspectives.md` |
| Single method, clear immediate blocker, nothing interesting to add | Not-useful note | `<Tool>_not_useful.md` |
| Paper covers ≥3 methods, mix of covered + new | Multi-method review | `<Author>_<Year>_methods_review_<YYMMDD>.md` |
| Method is accepted for benchmark addition, needs implementation plan | Implementation plan | `<tool>_implementation.md` (may go in parent dir) |

**Rule of thumb:** if the verdict requires more than two sentences to explain, use `_usage_perspectives.md`. If it's "requires matched samples, done", use `_not_useful.md`.

---

## Step 5 — Write the Document

### Header block (all document types)

```markdown
# <Tool> — Usage Perspectives for Multi-Platform Bulk RNA Harmonization

**Full name:** <full method name>
**Paper:** <Authors>. "<Title>." *<Journal>* <Volume>(<Issue>): <pages> (<Year>). <DOI>
**PMC/GitHub:** <link>
**Code:** <package name and availability, or "Not publicly released">

**Context:** Evaluation of <Tool> as a harmonization candidate for ~5,444 samples across
88 cohorts from mixed platforms (Affymetrix GPL570, Illumina NGS, Illumina microarray,
Agilent microarray). Reference batch: RNASeq_FF_PolyA (n=1,039). Current benchmark winner:
FSQN (R) at ~16% PCA variance explained by batch (down from ~95% raw).
```

### `_usage_perspectives.md` sections (in order)

1. **What `<Tool>` Actually Does — Core Concept** — one paragraph on the method's purpose, the problem it solves, and the key insight that distinguishes it from simpler approaches
2. **Algorithm — Step by Step** — numbered steps; use code blocks for formulas; include a table for I/O spec
3. **Experimental Validation** — datasets, sample sizes, methods compared, key quantitative results
4. **Assessment for This Project** — 2–4 subsections, each covering one blocker or compatibility issue; start with the most fundamental mismatch
5. **Comparison with Current Benchmark Methods** — table with ≥4 rows, comparing the new method vs. FSQN and 2–3 closest existing methods on: problem domain, input requirements, code availability, multi-platform validation, batch R² (if known)
6. **Indirect Value** (optional) — if the method introduces a metric, diagnostic concept, or dataset annotation strategy that is useful even without integrating the method itself, describe it here
7. **Verdict** — bold `**<Tool> is not applicable…**` or `**<Tool> warrants benchmark integration…**`; 2–3 sentences max; list secondary blockers as bullet points if multiple

### `<Author>_<Year>_methods_review_<YYMMDD>.md` structure

1. **Paper Overview** — citation, experimental design, key limitation relative to our benchmark
2. **Methods Already in Benchmark** — table mapping paper methods to our keys; no further analysis
3. **Methods Not in Benchmark — Individual Assessments** — one `###` subsection per unreviewed method, each with: algorithm summary, assessment for our project, verdict
4. **Paper Scope and Value for This Project** — what the paper confirms or informs about existing benchmark entries, even without adding new methods
5. **Summary Table** — all methods × (in benchmark? / applicable? / verdict)
6. **Overall Conclusion** — 3–5 sentences; restate benchmark winner and whether anything changes

---

## Step 6 — Quality Checks Before Saving

Before writing the file, verify:

- [ ] Citation is complete: authors, title, journal, year, DOI, PMC link if available
- [ ] Algorithm description is self-contained — a reader unfamiliar with the paper should understand the mechanism
- [ ] Blockers are project-specific, not generic (e.g. "no matched samples in our dataset" not just "requires matched samples")
- [ ] Comparison table includes FSQN (`16_fsqn_r`) as the benchmark reference row
- [ ] Verdict is explicit: "NOT APPLICABLE" or "warrants consideration" — no hedging
- [ ] File is saved to `harmonization-tools-research/` (not a subdirectory)
- [ ] Filename matches the conventions in the CLAUDE.md for this folder

---

## Common Patterns and Precedents

Keep these on hand to avoid re-researching solved questions:

| Pattern | Precedent document |
|---|---|
| Requires matched samples → not applicable | `MatchMixeR_usage_perspectives.md` |
| Cross-species design → wrong domain | `CSN_usage_perspectives.md` |
| Embedding output → not applicable | `MoDAmix_not_useful.md`, `HARP_usage_perspectives.md` |
| No code → not applicable | `CSN_usage_perspectives.md` (secondary blocker) |
| Rank method → redundant with `18_rank` | `Angel_usage_perspectives.md`, `Foltz_2023_methods_review_260506.md` |
| scRNA-seq method on bulk data | `scBatch_usage_perspectives.md` |
| Deep learning / neural network method (VAE, autoencoder, GAN) on bulk data | `Yu_2024_methods_review_260506.md` (scGen, scVI, DESC, AutoClass, deepMNN — all NOT APPLICABLE) |
| Borisov 2022 suite (Shambhala, XPN, DWD, UPC, etc.) | `Borisov_2022_methods_review_260506.md` |
| Foltz 2023 suite (QN, TDM, NPN, CrossNorm, etc.) | `Foltz_2023_methods_review_260506.md` |
| Yu 2024 suite (all DL methods + M-ComBat, reComBat, RUV-III-PRPS) | `Yu_2024_methods_review_260506.md` |

If a method appears conceptually similar to one of these precedents, cite the precedent in the new document rather than re-deriving the reasoning from scratch.

---

## Notes on Fetching Specific Sources

- **PMC links** (`pmc.ncbi.nlm.nih.gov/articles/PMC…`): reliable, full text including methods
- **Nature/Springer** (`nature.com/articles/…`): may return 303 redirect; try the PMC mirror instead or append `/fulltext`
- **bioRxiv** (`biorxiv.org/content/…`): use `mcp__claude_ai_bioRxiv__get_preprint` tool if available; otherwise WebFetch works for most preprints
- **GitHub repositories**: read README + main source files directly with `WebFetch` on the raw URL, or `gh` CLI if accessible
- If a URL redirects, the WebFetch result will say "Request failed with status code 303" — switch to the PMC alternative immediately rather than retrying the same URL
