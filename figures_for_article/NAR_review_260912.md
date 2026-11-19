# Referee report — *Nucleic Acids Research*
### Benchmarking of bulk transcriptomic harmonization tools in a multi-platform B-cell lymphoma cohort…

| | |
|---|---|
| **Manuscript reviewed** | `FL_manuscript_versions/FL_harmonization_article_NAR_260802_3rd_iteration.docx` (282 body children, ~15,050 words, 78 `w:sdt` citations, no pre-existing revisions) |
| **Supplementary reviewed** | `supplementary_260824/` — Files 1–3, Figures S1–S17 bundle, S18, S19 |
| **Figures reviewed** | `current_figures_tables_for_article_260802/` — Figures 1–6, Graphical Abstract |
| **Tracked-changes output** | `FL_manuscript_versions/FL_harmonization_article_NAR_260912.docx` |
| **Edit script** | `edit_python_scripts/apply_nar_review_edits_260912.py` |
| **Date** | 2026-09-12 |
| **Excluded from scope by the author** | Missing Zenodo DOIs; all reference/bibliography formatting (managed in Mendeley) |

---

## §0 Summary assessment

This is a substantial and unusually honest piece of benchmarking. Three things are genuinely
strong and worth stating plainly:

1. **The analysis set is now exactly reproducible from the deposited data.** Applying
   `pct_samples_allNA < 5` to Supplementary File 3 returns **exactly 2,234 of 2,407 rows** and
   drops **exactly** `34_arsyn` and `38_harman`, leaving 31 methods. This was the single largest
   reproducibility failure in the 2026-07-27 pass and it is fully resolved.
2. **The headline effect sizes reproduce to four decimal places**, confidence intervals included.
3. **The paper argues against its own best-scoring method.** MNN wins the clustermap and is then
   withdrawn because the biomarker correlation collapses. Benchmarks rarely do this, and the
   group L/M/N blind check is the right instrument for it.

My concerns fall into three groups, in descending seriousness.

**First, one quantitative claim runs backwards against the deposited data.** The method-harshness
comparison (Results, composite-score paragraph) states that harsher methods score higher; every
reconstruction I attempted returns the opposite ordering, and the maxima are reversed too. A
Discussion claim about algorithmic sophistication rests on it.

**Second, the metric bookkeeping does not reconcile anywhere.** The manuscript gives three
mutually incompatible totals for the number of metrics computed (229, 87 + 247 = 334, and 229
again in the Supplementary File 2 description), against 344 rows in the deposited workbook. The
biomarker panel size and the Supplementary File 2 sheet count are likewise stale.

**Third, the figures are not yet submittable.** Every figure overruns the NAR print box; after
the required scaling, a third of the text in Figures 1 and 2 falls below 5 pt; all use Type 3
fonts with nothing embedded; six of nine have no extractable text layer at all; and the deposited
supplementary bundle does not contain the 19 supplementary figures the text cites.

**Recommendation: major revision.** The science is sound and the corrections are tractable — most
are bookkeeping, and one is a sign error. Counts: **2 critical, 7 major, 31 minor**, of which
**44 text edits** are applied in the tracked-changes file and **10 reviewer notes** mark what only
the authors can resolve.

---

## §1 Critical

### C1 — The method-harshness comparison is stated in the wrong direction

The manuscript states medians of **0.479 (low) < 0.488 (medium) < 0.493 (high)** and that "the
high harshness methods had higher maximum values (0.69 compared to 0.66 for low harshness
methods)". Recomputing the composite score exactly as the manuscript defines it — polarity flip,
min–max per metric, mean over the 87 scoring metrics, on the 2,234 analysis rows:

| Tier | As reported (median) | As recomputed (median) | Reported max | Recomputed max |
|---|---|---|---|---|
| low | 0.479 | **0.520** | 0.66 | **0.716** |
| medium | 0.488 | **0.497** | — | 0.704 |
| high | 0.493 | **0.480** | 0.69 | **0.700** |

Both the ordering and the maxima are inverted. This is not a normalization artifact — I tested
five recipes (flip→min–max over 2,234 rows; flip→min–max over all 2,407; min–max→polarity;
rank-percentile; z-score) and three aggregations (all rows; post-removal = 0 only; complete-87
only), plus median-of-per-method-medians. **All eight give `high < medium < low`.** Excluding the
`01_raw` control widens the gap (low rises to 0.546).

I could **not** reproduce your exact values — your three medians span 0.014, every recipe I tried
spans 0.03–0.04 — so I have **not** edited the numbers. Please re-derive from the notebook. If the
recomputation stands, this paragraph must be reversed, and so must the Discussion sentence
asserting that "algorithmic sophistication … consistently outperforms generic location-and-scale
corrections" (that sentence has been narrowed to a claim about this dataset in the tracked file,
which is defensible either way).

### C2 — Metric counts do not reconcile in any direction

| Quantity | Location | As written | As deposited |
|---|---|---|---|
| Metrics computed per approach | Results | 229 | Metric_polarity has **344** rows |
| Scoring + additional | Methods | 87 + **247** = 334 | 87 + **257** = 344 |
| Non-scoring metrics | Results | **142** | **257** |
| Polarity assignments | Results | "all the 229" | 344 |
| Supplementary File 2 description | Supp. data | "229 … metrics" | 344 |
| Metrics in Supplementary File 3 | Results | "229 … (Supplementary File 3)" | **87** scoring + `pct_samples_allNA` (93 cols) |

The scoring count itself is right: Metric_polarity contains **51 metrics at +1 and 36 at −1 = 87**,
and all 87 are present in Supplementary File 3. Everything else drifted. All six have been made
consistent at 344 / 257 in the tracked file, with a note: the 344 rows include 111 group L/M/N
rows, 10 metadata rows and 18 unharmonized-baseline delta rows added *after* this text was
written, and the last two families are computed in the analysis layer rather than per approach —
so if "computed per approach" is meant strictly, the true figure may be below 344. Please supply
the number your pipeline actually emits.

---

## §2 Major

**M1 — Composite scores for the best-approach group do not reproduce.** Reported "0.559 and
higher (median 0.603, MAD 0.023)"; recomputed min 0.572, median 0.639, MAD 0.034 (all 30 rows) or
median 0.637 (post-removal = 0). All 15 Table 3 approach names resolve in Supplementary File 3, so
the mismatch is in the score construction. Related: 23_vst reproduces (0.584 vs 0.583) but 22_tmm
does not (0.625 vs 0.589), and 16_fsqn_r (0.603) and 33_amdbnorm (0.590) rank *between* the two
methods the text calls the top pair. Not edited — noted.

**M2 — The unharmonized control is pooled into a harmonization tier.** `01_raw` is classified
"low harshness" in Table_S1_methods and contributes 84 rows to the low tier with a composite of
0.445 against an overall median of 0.489. State whether it was excluded from Figure 6A.

**M3 — 33 vs 31 used interchangeably for the analysed set.** 33 were implemented; 31 survive the
NA filter. Claims about what was *benchmarked or analysed* — Discussion ×3, Conclusions ×1,
limitations ×1 — said 33. Corrected to 31 where the claim is about analysis; left at 33 where it
means "implemented". The Abstract said the cross-product covered 31 algorithms, which contradicts
its own 2,772 = 14 × 3 × **33** × 2; corrected to 33 (word-neutral, abstract stays at 199).

**M4 — The Results name MNN a top method; the paper later withdraws it.** "MNN and SVA emerged as
the most versatile harmonization methods" reads as the final verdict, two sub-sections before MNN
is excluded for biomarker corruption. Qualified to "By the clustermap metrics, …".

**M5 — Two unsupported claims about the literature.** "the largest systematic harmonization
evaluation matrix reported to date in bulk transcriptomics" (no systematic search is reported) and
"provides a bias-free, data-driven ranking" (refuted by your own caveat that the composite
averages different metric subsets per strategy). Replaced with the factual "comprises 194,358
metric values" and "provides a data-driven ranking".

**M6 — A section heading asserts an untested result.** "AI-assisted methods evaluation made the
same impact as the expert-driven method discovery" — the section compares one method found each
way. Not edited (retitling is your call); flagged.

**M7 — Figure and packaging compliance.** See §4. Not fixable from the `.docx`.

---

## §3 Minor — applied as tracked changes

| # | Location | Issue |
|---|---|---|
| 1 | Title | "feature specific" → "feature-specific" |
| 2 | Results, composite score | **"Figc ure 6A"** → "Figure 6A" |
| 3 | Results, rank concordance | **"Supplementary Figure D, K"** — no figure number at all → "Supplementary Figure 18D, 18K" |
| 4 | Results, permutation control | "Mann-Whitey" → "Mann-Whitney" |
| 5 | Author contributions | **"Nicolas Borisoff"** → "Nikolay Borisov" (byline name) |
| 6 | Author contributions | "Nazar Harutyunyan: Data curation**,** Svetlana Paponova" → full stop |
| 7 | Supp. Fig. 19 legend | **Cyrillic "С" (U+0421)** in panel label "(С)" → Latin "C" |
| 8 | Supp. Fig. 19 legend | "FF only **script**" → "FF only strict" |
| 9 | Supp. Fig. 18 legend | "in the **save** versus" → "in the same versus" |
| 10 | Supp. File 2 description | "four sheets" → "five sheets"; `Table_S3_gene_panel` added (633 genes, 63 signatures) |
| 11 | Methods, metrics | "572 biomarker genes" → **633** (Table_S3_gene_panel: 633 unique genes over 834 gene–signature rows) |
| 12 | Results, blind check | "sheets Table_S3_gene_panel" → "sheet" |
| 13 | Methods, profiling | "back potentiated" → "back-transformed" |
| 14 | Methods, harshness | "the two ones were the simplest ones" → "FSMVN and median scaling were the simplest" |
| 15 | Intro | "than the biology explained one" → "than the biology-explained variance" |
| 16–17 | Results ×2 | "artefact" → "artifact" (document is US throughout) |
| 18 | Methods | "labelled" → "labeled" |
| 19 | Discussion | "modelling" → "modeling" (folded into the M5 rewrite) |
| 20 | Results, blind check | "Control the correlation over housekeeping genes showed" → "The control correlation … showed" |
| 21 | Results, blind check | "with a cost of" → "at the cost of" |
| 22 | Results, summary | "achieve high performance by complete biology corruption" → "at the cost of" |
| 23 | Decision tree | "because of biomarkers correlation vanished" → "because the biomarker correlation vanished" |
| 24 | Decision tree | "despite the latter achieved" → "despite the latter achieving" |
| 25 | Discussion, limitations | "Two methods … failed at the implementation stage" → "Two of the six methods that failed implementation …" (six are reported in Methods) |
| 26 | Discussion | Comma splice "SVA, and FSQN R" |
| 27 | Intro | P1 promotional close ("foundational AI models … clinically actionable") replaced with a testable statement |
| 28 | Abstract | `[NAR EDITOR NOTE] NAR limit: 200.` **deleted** (P7 — must not ship) |
| 29 | Discussion | Instruction text `(add link!)` **deleted** from the Zenodo sentence |
| 30 | Page setup | **US Letter → A4** (21.0 × 29.7 cm) |
| 31 | Discussion | Citation attached to your own computed median ρ — flagged, not edited |

**False positive, for the record:** the automated check reports "analyze 4 vs analyse 3". There is
no British/American conflict — the tool is matching *analysis* (26 occurrences). No edit needed.

---

## §4 Figures, supplementary material and NAR compliance

Measured with PyMuPDF against the NAR maximum print box (17.35 × 23.35 cm):

| File | Size (cm) | Required scale | Median pt after scaling | % text < 5 pt | Fonts / embedded | Colour |
|---|---|---|---|---|---|---|
| Figure 1 | 28.3 × 41.1 | 0.57 | 5.7 | **37.5 %** | 7 / **0** | RGB |
| Figure 2 | 27.2 × 41.1 | 0.57 | 6.1 | **35.8 %** | 2 / **0** | RGB |
| Figure 3 | 26.8 × 39.6 | 0.59 | *no text layer* | — | 6 / **0** | RGB |
| Figure 4 | 26.6 × 40.6 | 0.58 | *no text layer* | — | 2 / **0** | RGB |
| Figure 5 | 26.6 × 36.9 | 0.63 | *no text layer* | — | 3 / **0** | RGB |
| Figure 6 | 27.0 × 37.4 | 0.63 | 6.3 | 0 % | 3 / **0** | RGB |
| Graphical Abstract | 26.7 × 10.3 | 0.65 | *no text layer* | — | 1 / **0** | RGB |
| Supp. Fig. S18 | 26.5 × 37.7 | 0.62 | *no text layer* | — | 4 / **0** | vector |
| Supp. Fig. S19 | 26.6 × 40.8 | 0.57 | *no text layer* | — | 2 / **0** | RGB |

- **Every figure overruns the print box.** Figures 1 and 2 then push a third of their text below
  the 5 pt legibility floor.
- **Type 3 fonts, zero embedded, in all nine.** Six return no extractable text, so screen readers
  cannot reach any label and the supplied alt text is the *only* accessible description. This also
  means figure labels cannot be verified programmatically against the text.
- **All RGB, none CMYK.**
- **Supplementary Figures 18 and 19 are not in the deposited bundle.** They sit in a different
  folder from Figures 1–17, use an `S`-prefixed filename convention the others do not, and are
  absent from `Supplementary Figures S1-S17.pdf`. The text cites 19 supplementary figures; the
  bundle contains 17.
- **13 uncited "Extended Figure" PDFs** remain in the 260802 folder. NAR has no such category;
  confirm they are not part of the submission.
- **Page size** was US Letter; corrected to A4 in the output file.
- **Funding statement** still carries three placeholders (`[full official funder name]`,
  `XXXX`, `[funder name/grant number]`). NAR will not process the submission with these.

---

## §5 Statistics and methodology — verdict

**What is sound, specifically.** The four-factor η² decomposition is correctly framed as a mean of
87 per-metric effect sizes rather than a decomposition of the composite, and it reproduces exactly
(method 0.3629 [31.5, 41.1]; strategy 0.2564 [0.208, 0.305]; imputation 0.0155 [0.009, 0.022];
post-removal 0.0020 [0.001, 0.003]). Seeds are fixed and stated (42), embedding hyperparameters
are given, and the 1,000 KS genes are drawn once and reused. The paper states plainly that the
composite score is *not* comparable across strategies and was not a decision criterion, and backs
it with the 1,354/2,234 (60.6 %) complete-metric count — which also reproduces exactly. The
blind-check design (groups L/M/N, best-vs-rest, 100-fold label permutation) is a real control and
it is reported honestly even though it does **not** favour the recommended approaches (LOBO F1
median 0.629 for the best approaches vs 0.717 for the rest).

**What must be fixed.**

1. The harshness direction (C1) — a sign error in the paper's own data, or an unrecoverable
   difference in score construction.
2. The composite-score values for the best-approach group and for 22_tmm (M1).
3. `01_raw` pooled into the low-harshness tier (M2).
4. The metric-count bookkeeping (C2).
5. Design imbalance is acknowledged but under-weighted: 22_tmm has **6 runs**, 33_amdbnorm 14, and
   six methods are absent from at least one strategy, yet all appear in method-level rankings.
   Recomputed from Supplementary File 3, the six are `22_tmm`, `23_vst`, `27_dwd`, `29_combat_ref`,
   `33_amdbnorm`, `36_explobatch` — worth naming in the limitations, as the text already names the
   count.

**On the central biological claim.** That SVA + Softimpute reveals two FL transcriptional
subgroups invisible under every other configuration is the paper's most interesting result and is
appropriately hedged — you state it requires survival analysis and enrichment beyond this study's
scope. That is the right register. I would only add that the claim currently rests on visual
inspection of embeddings; a cluster-stability statistic would make it much harder to dispute.

---

## §6 Recommendation

**Major revision.** The four changes that would most alter my assessment, ranked:

1. Resolve the harshness direction (C1) and re-quote the composite scores (M1) — or show me the
   construction under which the published numbers hold.
2. Regenerate the figures within the NAR print box with embedded Type 1/TrueType fonts and a live
   text layer, and deposit all 19 supplementary figures in one bundle.
3. Settle the metric bookkeeping (C2) to a single number you can defend.
4. State whether `01_raw` was in or out of Figure 6A.

---

## Appendix — verification method

All recomputation used `supplementary_260824/Supplementary File 3.csv.gz` (2,407 × 93) and
`Supplementary File 2.xlsx`, with polarity taken from the `Metric_polarity` sheet and harshness
from `Table_S1_methods`. Composite score = per-metric polarity flip → min–max over the analysis
set → row mean. η² = between-group SS / total SS per scoring metric, averaged over the 87, with a
t-interval on the mean. Biology counts from `Supplementary File 1.csv`
(`Diagnosis_cell_type_unified`; "normal B cells" = the 11 non-malignant categories, summing to
889). Figure geometry, font and colour-space measurements with PyMuPDF 1.26.5.

Tracked-change integrity was verified, not assumed: XML parses; 111 revisions with no `w:t` inside
`w:del`, no stray `w:delText`, no missing attributes, no duplicate ids; **reject-all restores the
original text exactly**; `w:sdt` 78 → 78 and hyperlinks 11 → 11 with contents identical; abstract
199 words after Accept All.

Word and LibreOffice are unavailable in this environment — open the file in Word to eyeball the
revision display before accepting anything.
