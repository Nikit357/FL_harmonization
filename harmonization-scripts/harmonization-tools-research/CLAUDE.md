# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This folder is a **research scratchpad** for the FL harmonization benchmark. It contains one document per tool or method evaluated for possible inclusion in (or exclusion from) the 25-method cross-product benchmark defined in `../bench_shared.py`. There is no executable code here.

---

## Document types

| Pattern | Filename convention | When to write |
|---|---|---|
| **Usage perspectives** | `<Tool>_usage_perspectives.md` | Tool is plausibly applicable; document algorithm, assumptions, known failure modes, and a verdict |
| **Applicability assessment** | `<Tool>_not_useful.md` | Tool was evaluated and ruled out; document the blockers concisely |
| **Implementation plan** | `<tool>_implementation.md` | Tool is accepted; document the exact code changes needed across `bench_shared.py`, `Dockerfile`, `install_r_packages.R`, `test_mock.py`, and `k8s/pod-ssh.yaml` |
| **Multi-method paper review** | `<Author>_<Year>_methods_review_<YYMMDD>.md` | A single paper covers many methods; one file assesses all of them at once with an include/exclude table |

Implementation plans that cover multiple tools at once (e.g., XPN + DWD) may live in the **parent directory** (`../new_methods_implementation_<date>.md`) rather than here.

---

## Benchmark context (for writing new documents)

- **Dataset:** ~5,444 samples, 88 cohorts, 4 platforms (Affymetrix GPL570, Illumina NGS, Illumina microarray, Agilent microarray)
- **Metric:** one-way ANOVA R² of `RNA_BATCH` on first 10 PCA axes — lower is better; raw baseline ≈ 0.95, current best (HarmonizR E3×softimpute) ≈ 0.099; FSQN R (selected for SOM pipeline) ≈ 0.16
- **Reference batch:** `RNASeq_FF_PolyA` (n=1,039; used as normalization target by FSQN, TDM, Shambhala2)
- **Current methods:** 39 entries in `METHODS` dict in `../bench_shared.py` (`01_raw` … `39_procrustes`)
- **Grid:** 11 filter strategies × 4 imputation options × 39 methods = 1,716 jobs → 3,432 S3 outputs (before SKIPs for RNA-seq-only and permanently-unavailable methods)

### Applicability blockers — check in order, stop at first hit

| # | Blocker | Verdict |
|---|---|---|
| 1 | Requires matched/paired samples (same specimen on two platforms) | NOT APPLICABLE — see `MatchMixeR_usage_perspectives.md` |
| 2 | Output is a latent embedding, not a genes × samples matrix | NOT APPLICABLE — see `MoDAmix_not_useful.md`, `HARP_usage_perspectives.md` |
| 3 | Wrong biological domain (cross-species, single-cell, spatial) | NOT APPLICABLE — see `CSN_usage_perspectives.md` |
| 4 | No runnable code (no R/Python package, no maintained repo) | NOT APPLICABLE in most cases |
| 5 | Platform scope mismatch (RNA-seq only or microarray only, no cross-platform extension) | NOT APPLICABLE unless applied to the relevant subset only |
| 6 | Corrects at platform level (4 groups) not RNA_BATCH level (6+ groups) | Lower priority — likely underperforms FSQN |
| 7 | Validated on < 500 samples / < 10 cohorts only | Note uncertainty; do not auto-reject |
| 8 | Monotone variant of a method already in the benchmark | Note nearest equivalent; mark low priority |

---

## Coverage at a glance

| Document | Method(s) | Verdict |
|---|---|---|
| `MatchMixeR_usage_perspectives.md` | MatchMixeR | NOT APPLICABLE — requires matched samples |
| `TDM_usage_perspectives.md` | TDM | In benchmark as `19_tdm` |
| `Angel_usage_perspectives.md` | Angel | In benchmark as `25_angel` |
| `HARP_usage_perspectives.md` | HARP | NOT APPLICABLE — embedding output |
| `MoDAmix_not_useful.md` | MoDAmix | NOT APPLICABLE — embedding output |
| `COCONUT_usage_perspectives.md` | COCONUT | NOT APPLICABLE — requires matched samples |
| `RNABC_usage_perspectives.md` | RNABC | NOT APPLICABLE |
| `CSN_usage_perspectives.md` | CSN | NOT APPLICABLE — cross-species domain |
| `scBatch_usage_perspectives.md` | scBatch | NOT APPLICABLE — scRNA-seq method |
| `shambhala2_implementation.md` | Shambhala2 | In benchmark as `20_shambhala` |
| `imputation_and_batch_effect_research.md` | Imputation strategies | Reference notes; informs KNN/MissForest/SoftImpute choices |
| `Borisov_2022_methods_review_260506.md` | 19 methods from Borisov & Buzdin 2022 | None added — all covered or not applicable |
| `Foltz_2023_methods_review_260506.md` | 8 methods from Foltz et al. 2023 | None added — QN/TDM already in benchmark; rest not applicable |
| `Yu_2024_methods_review_260506.md` | 13 methods from Yu et al. 2024 (Genome Biology); incl. scGen, scVI, DESC, AutoClass, deepMNN, M-ComBat, reComBat, RUV-III-PRPS | DL methods NOT APPLICABLE (scRNA-seq); M-ComBat low priority; RUV-III-PRPS medium priority |

Before writing a new document, check this table and `Borisov_2022_methods_review_260506.md` + `Foltz_2023_methods_review_260506.md` + `Yu_2024_methods_review_260506.md` summary tables to confirm the method has not already been assessed.

---

## Article review skill

Use `/article_review` (defined in `skills/article_review/SKILL.md`) whenever the user provides a paper URL or DOI and asks to assess a normalization/batch correction method. The skill encodes the full two-pass fetch strategy, applicability filter, document-type decision rules, and output templates — invoke it rather than re-deriving the procedure from scratch.

---

## Adding a new document

1. Name the file after the tool using the conventions above.
2. Open with a header block: tool name, paper citation, GitHub URL, and one-sentence context sentence referencing the dataset scale and current best method.
3. For usage-perspectives and implementation-plan documents, include a **Verdict** or **Status summary** section at the end that makes the decision explicit.
4. Cross-reference the method key (e.g., `19_tdm`, `25_angel`) when the tool maps to an existing or proposed benchmark entry.
5. After writing, add a row to the **Coverage at a glance** table above.
