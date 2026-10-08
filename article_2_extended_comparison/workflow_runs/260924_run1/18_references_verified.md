# 18 — References verified (Phase 4, reference-verifier)

## Status

- **Done** (2026-09-25). Nothing in the manuscript, drafts, `.docx`, `references_260917.md` or `reference_support_260917.md` was edited; this file is the only output (plus `tools/cache/` entries written by `fetch_literature.py`).
- Duty 1: 24 proposals re-resolved independently — **20 CONFIRMED, 4 CONFIRMED WITH CORRECTION (P-02, P-05, P-08, P-23), 0 NOT CONFIRMED.** No identifier resolved to a different paper.
- Duty 1 side finding: **3 of 8 package versions in the Methods disagree with the venv** (scipy 1.12.0 vs installed 1.17.1; scikit-learn 1.3.2 vs 1.8.0; statsmodels 0.14.1 vs 0.14.6).
- Duty 1 gap: the 260925 Methods names tests with no proposal (ε², Fisher's exact, chi-square GOF, binomial, hypergeometric); Wilcoxon 1945 (P-05) is now required, not optional, for the new signed-rank sentence.
- Duty 2: base `.docx` has **46** Mendeley `w:sdt` / 46 MENDELEY_CITATION; `03_revision_edits.json` has **46** `⟦CIT:…⟧` tokens (base 46 = new 46), 0 token-sequence mismatches in 203 entries, base token order equals the docx `w:sdt` order 46/46, numeric `[38]`×2, `[50,51]`, `[52]` present. **No integrity drift.** Two placement questions for Daniil (P23 wording change next to the source-benchmark citation; mixed numeric/author-year forms for the same reference [38]).

---

## Duty 1 — independent re-resolution of the 24 proposals

Sources queried by this agent (2026-09-25), independently of `11_citations_to_insert.md`:
Crossref REST (`api.crossref.org/works/<DOI>`, plus an issue listing of JRSS B 1958 vol 20 no 2),
OpenAlex (`api.openalex.org/works/doi:<DOI>`) for end pages Crossref lacks, DataCite
(`api.datacite.org/dois/<DOI>`) and the Zenodo records API, the e-periodica issue table of
contents, PubMed eSummary / PMC full text via `tools/fetch_literature.py`, Open Library
(works + ISBN), JMLR paper pages, and each package's official citing page (SciPy: the raw
`CITATION.bib` in the scipy repository). Quoted passages were matched programmatically
(whitespace/quote-normalised substring search against the fetched text).

### Per-proposal verdicts

| id | registry result (this agent) | passage check | verdict |
|---|---|---|---|
| P-01 Kruskal & Wallis 1952 | Crossref: "Use of Ranks in One-Criterion Variance Analysis", Kruskal WH, JASA 47(260):583-621, Dec 1952 | no abstract; bibliographic only | CONFIRMED |
| P-02 Spearman 1904 | Crossref: title, Spearman C, Am J Psychol 15(1), first page 72; Crossref and OpenAlex both carry **no end page** | bibliographic only | CONFIRMED WITH CORRECTION (minor): the end page 101 is not in any registry record queried; Mendeley/JSTOR should supply it — do not treat "72-101" as registry-verified |
| P-03 Hampel 1974 | Crossref: "The Influence Curve and its Role in Robust Estimation", Hampel FR, JASA 69(346):383-393, Jun 1974 | no abstract, no open text; MAD content not verifiable here | CONFIRMED (bibliography) — the record is correct; its suitability as *the* MAD reference remains an unread-text judgement, as the first agent said. Note: the current Methods sentence (line 69, `_260925.md`) does **not** say "unscaled"; the first agent's advice to add that word has not been acted on |
| P-04 Mann & Whitney 1947 | Crossref: title as proposed, Mann HB, Ann Math Stat 18(1):50-60, Mar 1947 | bibliographic only | CONFIRMED. The sentence now exists (line 69: "Two groups were compared by the two-sided Mann-Whitney U test") |
| P-05 Wilcoxon 1945 | Crossref: "Individual Comparisons by Ranking Methods", Wilcoxon F, Biometrics Bulletin 1(6), first page 80; **no end page** in Crossref or OpenAlex | bibliographic only | CONFIRMED WITH CORRECTION: (a) end page 83 not registry-verified; (b) **status change** — the current Methods now also names "the two-sided Wilcoxon signed-rank test" for matched pairs. Wilcoxon 1945 is the original paper of the signed-rank test as well as the rank-sum test, so it is no longer optional: it is the primary citation for the signed-rank sentence |
| P-06 Pearson 1901 | Crossref: "LIII. On lines and planes of closest fit to systems of points in space", Pearson K, Phil Mag 2(11):559-572, Nov 1901 | bibliographic only | CONFIRMED |
| P-07 Hotelling 1933 | Crossref: title as proposed, Hotelling H, J Educ Psychol 24(6):417-441, Sep 1933 | bibliographic only | CONFIRMED |
| P-08 Cox 1958 | Crossref: "The Regression Analysis of Binary Sequences", Cox DR, JRSS B 20(2):**215-232**, Jul 1958. Abstract quote found verbatim (Crossref "Summary") | abstract | CONFIRMED WITH CORRECTION: the first agent's claim that "215-242 is wrong" is overstated. The issue listing shows a separate item, "Discussion on Dr. Cox's Paper", pp. 232-242 (doi:10.1111/j.2517-6161.1958.tb00293.x). 215-242 is the paper-with-discussion range (as JSTOR and many reference lists print it); 215-232 is the paper alone. Either is defensible; 215-232 matches the DOI proposed |
| P-09 Jaccard 1901 | DataCite: title as proposed, Jaccard, Paul, 1901, publisher Imprimerie Corbaz; pid `bsv-002:1901:37::790` (vol 37). e-periodica TOC: item in **Heft 142**, starts p. 547, next item starts p. 581. OpenAlex: vol 37, pp. 547-579 | bibliographic only | CONFIRMED (vol 37, issue 142, pp. 547-579 now registry-supported, which the first agent had not established) |
| P-10 Jaccard 1912 | Crossref: "The distribution of the flora in the alpine zone", Jaccard P, New Phytologist 11(2):37-50, Feb 1912 | bibliographic only | CONFIRMED |
| P-11 Ojala & Garriga 2010 | JMLR page: title, authors, 11(62):1833-1863, 2010 | abstract passage found verbatim on JMLR page | CONFIRMED |
| P-12 Pitman 1937 / Fisher 1935 | Crossref: "Significance Tests Which May be Applied to Samples from Any Populations", Pitman EJG, 4(1):119-130, 1937 (Crossref container JRSS B; historically *Supplement to the JRSS*). Open Library OL1153859W: Fisher, *The Design of Experiments*, Oliver and Boyd, Edinburgh, 1935 edition exists | bibliographic only | CONFIRMED (as an optional alternative; the first agent's PARTIAL support judgement stands) |
| P-13 Hanley & McNeil 1982 | PubMed 7063747: title, Hanley JA, McNeil BJ, Radiology 1982; Crossref 143(1):29-36; doi matches; no PMC | both abstract sentences found verbatim | CONFIRMED. Hand & Till 2001 (Mach Learn 45(2):171-186) also resolves as stated |
| P-14 van Rijsbergen 1979 + Sokolova & Lapalme 2009 | Open Library ISBN 0408709294: *Information retrieval*, 2d ed., Butterworths, 1979. Crossref: Sokolova M, Inf Process Manag 45(4):427-437, Jul 2009 | book passage found verbatim on the author-hosted Chapter 7 page; Sokolova text not read | CONFIRMED |
| P-15 pandas 2.3.3 | DataCite + Zenodo API: doi:10.5281/zenodo.17229934 = "pandas-dev/pandas: Pandas", **version v2.3.3**, issued 2025-09-30. Crossref McKinney 2010, Proc. 9th Python in Science Conf., pp. 56-61. Citing page asks for "the published software and the following paper" and to use the version-specific Zenodo record | citing-page sentence found verbatim | CONFIRMED. Note: the concept DOI 10.5281/zenodo.3509134 now resolves to v3.0.6 (2026-09-17) — use the version DOI, not the concept DOI. The citing page's own BibTeX says "Volume 445" for McKinney; that is a proceedings artefact, pages 56-61 are correct |
| P-16 numpy | PubMed 32939066 / Crossref: Harris CR, Nature 585(7825):357-362, 2020; PMC7759461 | citing-page sentence and article sentence found verbatim | CONFIRMED (bibliography); **installed version matches** (1.26.4) |
| P-17 scipy | PubMed 32015543 / Crossref: Virtanen P, Nat Methods 17(3):261-272, 2020; PMC7056644; `CITATION.bib` entry `2020SciPy-NMeth` matches | article sentence found verbatim | CONFIRMED (bibliography). **Version disagreement — see below: installed scipy is 1.17.1, Methods says 1.12.0** |
| P-18 scikit-learn | JMLR page: Pedregosa F et al., 12(85):2825-2830, 2011; citing page sentence verbatim | abstract passage verbatim | CONFIRMED (bibliography). **Version disagreement: installed 1.8.0, Methods says 1.3.2** |
| P-19 statsmodels | Crossref: Seabold S, "Statsmodels: Econometric and Statistical Modeling with Python", Proc. SciPy 2010, pp. 92-96; citing sentence verbatim on docs index | bibliographic + official page | CONFIRMED (bibliography). **Version disagreement: installed 0.14.6, Methods says 0.14.1** |
| P-20 matplotlib | Crossref: Hunter JD, CiSE 9(3):90-95, 2007; citing sentence verbatim; the citing page lists a v3.10.8 version-specific Zenodo DOI | bibliographic + official page | CONFIRMED; installed 3.10.8 matches |
| P-21 seaborn | Crossref: Waskom M, JOSS 6(60):3021, 2021-04-06; citing sentence verbatim | bibliographic + official page | CONFIRMED; installed 0.13.2 matches |
| P-22 Python 3.11 | no bibliographic record exists; URL only | — | CONFIRMED (URL only). Installed interpreter 3.11.15 matches "Python 3.11" |
| P-23 Luecken et al. | PubMed 34949812 / Crossref: Luecken MD, Nat Methods **19(1):41-50**, issue Jan 2022, **online 2021-12-23**; PMC8748196 | 3 of 4 passages found verbatim; the kBET "algorithm" passage is verbatim except that a reference superscript ("composition¹¹") was dropped | CONFIRMED WITH CORRECTION: (a) year — issue 2022, online 2021; the manuscript's "(Luecken et al. 2021)" conflicts with `references_260917.md` [6] (2022) — Daniil should make the in-text year follow Mendeley's entry; (b) the first agent says the paper rescales LISI "precisely so that scores can be compared between tasks with different numbers of labels". The paper states only that LISI "range from 1 to B" and that "we rescaled them to the range 0 to 1"; the comparability motive is the first agent's inference, not a stated sentence. Support for the C37 sentence as it now reads: see next subsection |
| P-24 Korsunsky et al. 2019 | PubMed 31740819 / Crossref: Korsunsky I, Nat Methods 16(12):1289-1296, issue Dec 2019, online 2019-11-18; PMC6884693 | 6 of 7 passage fragments verbatim; "…LISI values become difficult to interpret." is verbatim only up to a dropped "(Supplementary Note 2)" before the full stop | CONFIRMED (PARTIAL support, as the first agent said) |

**Counts:** CONFIRMED 20 (P-01, 03, 04, 06, 07, 09, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24; P-17/18/19 carry the version caveat below, P-22 is URL only); CONFIRMED WITH CORRECTION 4 (P-02, P-05, P-08, P-23); NOT CONFIRMED 0. Every identifier resolved to the paper the proposal names; no title, first-author, journal or volume mismatch was found.

### Package versions: Methods sentence vs the installed venv

`~/venvs/collagen_3_11` (`python -c "import …; print(…__version__)"`):

| package | Methods (line 69, `_260925.md`) | installed | install date (dist-info) | agrees? |
|---|---|---|---|---|
| Python | 3.11 | 3.11.15 | — | yes |
| pandas | 2.3.3 | 2.3.3 | 2026-04-19 | yes |
| numpy | 1.26.4 | 1.26.4 | 2026-05-01 | yes |
| **scipy** | **1.12.0** | **1.17.1** | 2026-04-19 | **NO** |
| **scikit-learn** | **1.3.2** | **1.8.0** | 2026-04-19 | **NO** |
| **statsmodels** | **0.14.1** | **0.14.6** | 2026-04-19 | **NO** |
| matplotlib | 3.10.8 | 3.10.8 | — | yes |
| seaborn | 0.13.2 | 0.13.2 | — | yes |

The three disagreeing packages were installed in April 2026, before any Article 2 analysis
(September), so every local Article 2 script (`analysis/*.py`, the figure scripts) ran on
scipy 1.17.1, scikit-learn 1.8.0 and statsmodels 0.14.6. "SciPy 1.12.0" matches the pin in the
root `CLAUDE.md` rather than the environment. One caveat this agent cannot resolve: the
class L/M/N metrics (including the LOBO logistic regression) were computed on the metrics
pod, whose environment is not visible from here (`harmonization-scripts/requirements.txt` only
pins `scikit-learn>=1.3,<1.6`). **Question for Daniil:** should the Methods list the local
analysis versions (scipy 1.17.1, scikit-learn 1.8.0, statsmodels 0.14.6), and state the pod's
versions separately for the class N computation?

### C37 — the target sentence as it now reads

`grep` finds it at **line 125** of `manuscript/FL_metric_classes_F1000_260925.md` (it was line 131
in `_260924.md`), unchanged in wording: "According to their design, local values depended on
how many classes the strategy leaves in the data, which limits comparison across strategies."
The next sentences now add Mann-Whitney p-values and restate graph connectivity as means
(0.727 FFPE-only, 0.646 malignant-only).

- **P-23 (Luecken):** supports the dependence for LISI (verbatim: "LISI scores range from 1 to N,
  where N is the total number of batches in the dataset" — stated for batches; the same holds for
  cLISI with labels) and shows that the authors normalise by B. It does not literally say that raw
  values "limit comparison across strategies"; that is a fair inference from a range that depends on
  N. For kBET it shows dependence on the expected (global) label composition. It supports nothing
  about graph connectivity depending on class count — and the manuscript itself says fewer groups
  are *expected to increase* connectivity, a claim neither P-23 nor P-24 states. **Verdict: supports
  the sentence for LISI/kBET; recommended as proposed.**
- **P-24 (Korsunsky):** supports that the LISI ceiling depends on the number and proportions of
  labels (1.8 vs 1.5). Best as a co-citation with P-23, as proposed.
- The sentence says "local values" in general; if Daniil wants the citation to cover the whole
  sentence, narrowing it to "LISI and kBET values" would match what the two papers state.

### Gaps: tests named in the current Methods that no proposal covers

The Methods paragraph grew after `11_citations_to_insert.md` was written (it quoted the 260924
version). The 260925 paragraph also names: ε² as the Kruskal-Wallis effect size, the Wilcoxon
signed-rank test (covered by P-05, see above), Fisher's exact test, the chi-square
goodness-of-fit test, the binomial and binomial sign tests, and the hypergeometric overlap test.
None has a proposal. If C20 is read as "cite every statistical method", Daniil may want
references for ε² (e.g. Tomczak & Tomczak 2014, or Kelley 1935) and Fisher's exact test — this
agent did not resolve or verify any of these; they are listed as a gap only.

---

## Duty 2 — citation integrity of the revision (report only)

### Counts

| check | expected | found |
|---|---|---|
| `<w:sdt>` content controls in `FL_metric_classes_F1000_260917_edited_Daniil.docx` (`scientific_review_tools.py citations`) | 46 | **46** (MENDELEY_CITATION 46, bibliography 0, legacy fields 0) |
| `⟦CIT:…⟧` tokens in `03_revision_edits.json`, `base` fields | 46 | **46** |
| same, `new` fields | 46 | **46** (35 distinct token strings) |
| entries whose `new` token sequence differs from `base` | 0 | **0** of 203 (79 edit, 55 keep, 44 delete, 25 insert) |
| base token sequence vs the docx `w:sdt` text, in document order | identical | **46/46 identical** |
| numeric `[38]` | 2 | 2 in base, 2 in new (P146; P160 deleted → P159+8 inserted, same sentence content) |
| numeric `[50,51]` | 1 | 1 (P76, sentence unchanged) |
| numeric `[52]` | 1 | 1 (P82, sentence unchanged) |

No deleted or inserted paragraph carries a Mendeley token; all 46 sit in 13 paragraphs
(4 `keep`, 9 `edit`).

### Placement review — every edited paragraph that carries a citation

Sentence-level comparison of `base` and `new` around each token (extraction script output
was checked by hand):

| paragraph | change next to the citation | judgement |
|---|---|---|
| P13 (Introduction) | "An early **2021** empirical comparison" → "**2011**" before (Rudy and Valafar 2011); "k-nearest-neighbour batch-effect test" → "k-nearest-neighbor (KNN) batch-effect test" before (Büttner et al. 2018) | Same claim; the year fix makes the text agree with its own citation. OK |
| P14 | spelling (germinal-centre → germinal-center), one trailing space removed | OK |
| P16, P50, P63 | sentence carrying the citation unchanged | OK |
| P20 | spelling, double space removed | OK |
| P24 | "(Supplementary File X)" → sheet name; "treated the 15 approaches selected by the published clustermap (Nikitin et al.)" completed with "as one more set" | Same claim. OK |
| P25 | trailing space | OK |
| **P23** (Methods, metric classes) | Base: "We assigned each of the **87** polarity-adjusted scoring metrics of the source benchmark (Nikitin et al. 2026 Sep 17) to one of four classes: global, covering PCReg, DSC, **per-component R2 and the variance explained by each PC**; local … average silhouette width and graph connectivity; distributional … **per-gene batch quantities**; structural … **intra- and inter-group distances** …". New: "We assigned the scoring metrics of the source benchmark (Nikitin et al.) to four classes **by their column prefix**: global, covering **the 11 metrics of PCReg and DSC**; local … **the cell-specific mixing score** and graph connectivity; distributional … **the per-gene coefficient of variation of batch means**; structural … **embedding entropy and centroid dispersion** …" | The citation still sits on "scoring metrics of the source benchmark", which it supports. But the class membership described next to it changed in substance (per-component R² and PC variance no longer listed under global; cms added to local; the count 87 removed). **Question for Daniil:** does the source benchmark's metric registry list the cell-specific mixing score and define the class contents exactly as the new sentence says, so that the (Nikitin et al.) citation still covers the whole sentence? The cms, unlike kBET and LISI, has no citation of its own anywhere in the manuscript |
| P76 `[50,51]`, P82 `[52]`, P146 `[38]` | unchanged | OK (no drift). Not in scope to re-judge, but noted: [50] (glioblastoma miRNA in EVs) and [51] (plasma exosome proteins) support the "extracellular-vesicle and plasma-derived inputs" clause only loosely |
| P160 → P159+8 `[38]` | Supplementary File 1 legend rewritten per sheet; "the reconciliation from the 2,407 completed approaches of the source benchmark [38] to 2,234, with the Shambhala identity check" kept and extended with the 84-key / 78-of-79 detail | Same claim next to [38]. OK |

### Other integrity observations (questions, not fixes)

1. **Mixed citation forms for one reference.** `references_260917.md` [38] is the Nikitin et al.
   source benchmark, which the Mendeley fields cite as "(Nikitin et al. 2026 Sep 17)". The two
   plain-text "[38]" occurrences (P146 and the Supplementary File 1 legend) are numeric, as are
   [50,51] and [52]. When Mendeley renders the bibliography, will these four plain-text numbers stay
   consistent with its numbering? They are not Mendeley fields, so a Mendeley refresh will not
   renumber them.
2. **"Luecken et al. 2021" vs reference [6] "2022".** Issue date 2022-01, online 2021-12-23
   (Crossref). The in-text Mendeley field prints 2021; the frozen reference list says 2022. Mendeley
   should decide; the two should agree.
3. **C37 insertion** (P-23 + P-24) will add Mendeley fields; after Daniil inserts them the expected
   `w:sdt` count rises from 46 by the number of new fields.
