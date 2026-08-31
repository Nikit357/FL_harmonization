# Nucleic Acids Research (NAR) — Author Guidelines Reference

**Purpose of this document.** This is a consolidated, detailed reference of the *Nucleic Acids
Research* (NAR) author guidelines, compiled from the official NAR author-guidelines page, the
NAR data-deposition page, Oxford University Press (OUP) figure/accessibility guidance, and the
official **NAR manuscript Word template ("nar-word-template November 2025.docx")**. It is written
so that any later agent can rewrite a manuscript draft into full NAR compliance without needing to
re-read the source pages.

**Sources**
- NAR author guidelines: https://academic.oup.com/nar/pages/author-guidelines
- NAR data deposition and standardization: https://academic.oup.com/nar/pages/data_deposition_and_standardization
- OUP figure/artwork + accessibility (alt text) standard text (identical across OUP journals)
- NAR Word template `nar-word-template November 2025.docx` (November 2025 edition), analysed directly

**How to use this for rewriting.** Follow the section order in Part 2, apply the formatting rules
in Part 1, and run the checklist in Part 12 before declaring a draft NAR-ready. Anything the
template marks in red is an *instruction* to the author and must be deleted from the final
manuscript.

> **Relevance to this project (FL harmonization / ComboBatch).** This manuscript uses public
> microarray + RNA-seq cohorts. That triggers the **GEO / ArrayExpress / SRA + MIAME/MINSEQE**
> deposition rules, the **software → Zenodo/Figshare permanent DOI** rule (GitHub alone is *not*
> sufficient), and **HGNC gene nomenclature**. See Part 8.

---

## PART 1 — Document formatting (from the NAR Word template)

The November 2025 template is the canonical formatting source. Its measured settings:

| Property | Value |
|---|---|
| Page size | A4 (210 × 297 mm; 8.27 × 11.69 in) |
| Margins | 1 inch (2.54 cm) on all four sides |
| Body text style | "Normal", **11 pt** |
| Body line spacing | 1.15 |
| Body paragraph spacing | ~10 pt after each paragraph |
| Title | Cambria, 26 pt |
| Theme fonts | Calibri / Calibri Light (headings render in a bold sans-serif) |

**General formatting rules**
- Keep the manuscript in the supplied template; do not re-style it. Text you add should inherit the
  "Normal" style.
- **Delete all red instruction text** from the template before submission (the template explicitly
  says so at the top).
- Use a single, consistent body font throughout. The template body is 11 pt.
- Number pages and, for the submitted (review) version, **line numbers are recommended** to help
  reviewers (add continuous line numbering).
- Write for a broad readership: the title and abstract must be intelligible to a non-specialist.
  **No jargon or non-standard abbreviations in the title.** Define every abbreviation at first use
  in the body.

**Heading hierarchy in the template (match this exactly).**
1. **Top-level section headings** — ALL CAPS, bold, on their own line. These are the fixed
   manuscript sections (see Part 2): `ABSTRACT`, `INTRODUCTION`, `MATERIAL AND METHODS`, `RESULTS`,
   `DISCUSSION`, `ACKNOWLEDGEMENTS`, `AUTHOR CONTRIBUTIONS`, `SUPPLEMENTARY DATA`,
   `CONFLICT OF INTEREST`, `FUNDING`, `DATA AVAILABILITY`, `REFERENCES`, etc.
2. **"A Heading"** — first-level subheading *within* a section: bold, on its own line.
3. **"B Heading"** — second-level subheading: bold/italic and **run-in** (the heading begins the
   paragraph on the same line as the following text).

**Equations.** Use Word's *Insert equation* and *Insert symbol* functions — **do not insert
equations as images**. Times New Roman and Arial Unicode MS give the widest symbol coverage. Number
equations on the right margin, e.g. `(1)`.

---

## PART 2 — Required manuscript structure and section order

Assemble the manuscript in this order (matching the template):

1. **Title**
2. **Authors** (byline) and **affiliations**
3. **Corresponding-author line(s)** with email
4. **Graphical Abstract** (mandatory at initial submission — see Part 6)
5. **Abstract** (Part 3)
6. **Introduction**
7. **Material and Methods**
8. **Results**
9. **Discussion** (Results and Discussion may be combined if appropriate to the article type)
10. **Acknowledgements**
11. **Author Contributions** (CRediT — Part 9)
12. **Supplementary Data** statement (if any — Part 7)
13. **Conflict of Interest** statement (Part 10)
14. **Funding** (Part 10)
15. **Data Availability** statement (mandatory — Part 8)
16. **Appendix** (only if a large consortium's members are listed here)
17. **References** (Part 5)
18. **Tables and Figures** with captions (Part 6)

During review, **embed figures and tables with their captions at the relevant points in the text**
to make reviewing easier; high-resolution figure files are uploaded separately at the revision
stage (see Part 6).

---

## PART 3 — Title, authors, affiliations, abstract

### Title
- Must be clearly intelligible to a non-specialist.
- **No jargon and no non-standard abbreviations.**

### Authors and affiliations
- Format: `Name Surname1, Name Surname2 and Name Surname3,*` with superscript numerals keyed to
  affiliation lines.
- Affiliation line format: `Department, Institution, Town, State, Postcode, Country`.
- Authors who moved since the work was done may list a current affiliation marked
  `Present address:` under Affiliations.
- **ORCID iD is required for the submitting author** (register free at https://orcid.org). Provide
  ORCIDs for all authors where possible.

### Corresponding authors
- **Maximum 3** corresponding authors.
- All designated with an asterisk `*`; may appear anywhere in the author list.
- The 2nd and 3rd are introduced with "Correspondence may also be addressed to…".
- Corresponding-author line format: `* To whom correspondence should be addressed. Email: …`

### Equal / joint contribution
- Joint first and/or last authorship is allowed. Mark joint authors with a dagger `†` and add a
  footnote: `† Name1, Name2 and Name3 contributed equally to this work`.

### Groups / consortia
- May appear in the byline (PubMed tags members as "collaborators").
- Few members → list in the byline on the title page. Many members → list in Acknowledgements or an
  Appendix. If a consortium authored the paper, one member is the corresponding author, listed
  "on behalf of" the group. Unambiguous acronyms are acceptable.

### Abstract
- **Single paragraph, ≤ 200 words.**
- **No references, no figure/scheme citations, no URLs** — *except* Database and Web Server issue
  articles, where URLs **must** be included.

---

## PART 4 — Main text sections

- **Introduction** — motivation and background; references cited by sequential number.
- **Material and Methods** — enough detail for reproduction; document every data filter/exclusion
  (e.g. "removed N samples for low counts"). Include ethics approvals and any AI-tool usage
  disclosure here (or in Acknowledgements). State compliance with reporting standards (MIAME,
  MIQE, ARRIVE, etc.) where relevant.
- **Results** — reference each figure/table; embed them (with captions) at first mention during
  review.
- **Discussion** — interpretation, limitations, conclusions.
- Abbreviations must be defined at first use. Use SI units.

---

## PART 5 — References and citations (strict NAR style)

**In-text citation**
- Cite by **sequential number only, in order of appearance**, e.g. `… as shown previously (1)` and
  `… reported earlier (2,3)`.
- List numerically in the References section.
- Every reference in the list must be cited in the text, and vice versa — check carefully.

**What must NOT go in the reference list** (cite in text only):
personal communications, unpublished results, manuscripts submitted or in preparation, statistical
packages, computer programs, and websites.

**Formatting rules for the reference list**
- Journal names abbreviated in **Chemical Abstracts** style.
- If there are **four or more authors, list the first three followed by `et al.`**
- **Full article titles must be provided.**
- Include DOIs for online articles and preprints.

**Exact NAR reference formats (copy these patterns):**

- **Journal article**
  `Schmitt E, Panvert M, Blanquet S and Mechulam Y. Transition state stabilisation by the 'high' motif of class I aminoacyl-tRNA synthetases: the case of Escherichia coli methionyl-tRNA synthetase. Nucleic Acids Res. 1995; 23: 4793–4798.`

- **Book**
  `Maniatis T, Fritsch EF and Sambrook J. Molecular Cloning: A Laboratory Manual. Cold Spring Harbor, NY: Cold Spring Harbor Laboratory Press, 1982.`

- **Book chapter**
  `Huynh TV, Young RA and Davies RW. Constructing and screening cDNA libraries in lambdagt10 and lambdagt11. In: Glover DM (ed.), DNA Cloning – A Practical Approach. Oxford: IRL Press, 1988, Vol. I, 49–78.`

- **Online journal article** (with DOI)
  `Capaldi S, Getts RC and Jayasena SD. Signal amplification through nucleotide extension and excision on a dendritic DNA platform. Nucleic Acids Res. 2000; 28: e21. https://doi.org/10.1093/nar/28.7.e21.`

- **Preprint**
  `Fan X, Yang Y and Wang Z. Pervasive translation of circular RNAs driven by short IRES-like elements. biorXiv, https://doi.org/10.1101/473207, 18 November 2018, preprint: not peer-reviewed.`

**Style notes distilled from the examples**
- Author names: `Surname Initials` (no periods between initials), authors separated by commas, `and`
  before the last author.
- Article title in sentence case, ending with a period.
- Abbreviated journal, year `;`, volume `:`, page range with an en dash `–`.
- **Data and software that are available online should be cited as full references** in the list
  (NAR follows the Force11 Data Citation and Software Citation principles).

---

## PART 6 — Figures, images, and the Graphical Abstract

### 6.1 When to submit what
- **Initial submission:** embed figures + captions in the text; screen-resolution is fine for review.
- **Revision stage:** high-resolution figure files are **required**, uploaded as separate
  individual files, *and* embedded (with captions) in the text.
- **Figures cannot be corrected at proof stage** — get them right before acceptance.

### 6.2 File formats
- **Preferred: TIFF (.tif)** and **EPS (.eps)**. Vector formats (EPS, AI, editable PDF) are best for
  line art and plots; keep them as vectors where possible.
- Also accepted: PNG, PostScript (.ps), PSD, AI, GIF, PowerPoint, Word, Excel.
- **Avoid JPG** — JPEG re-compresses and degrades every time the file is opened.
  *(For this project's matplotlib/seaborn figures: export SVG/PDF as the editable master per the
  project convention, then supply TIFF/EPS or high-res PNG at revision.)*

### 6.3 Resolution (dpi) — required minimums at final print size
| Figure type | Minimum resolution |
|---|---|
| Line art / black-and-white line figures | **600–1200 dpi** (1200 dpi optimal) |
| Line figures with some grey/coloured lines | 600 dpi |
| Halftones / photographs / colour figures | **300 dpi** |
| Combination (line + halftone) | 600 dpi |

Resolution must hold **at the figure's final published size**, not at oversized dimensions.

### 6.4 Sizing (column widths)
- Figures are published at either single- or double-column width. Design to fit:
  - **Minimum width ≈ 8.3 cm** (single column).
  - **Maximum width ≈ 17.35 cm**; maximum height ≈ 23.35 cm (must fit within the print page).
  - Pixel guide for raster art: up to ~1081 (w) × 1280 (h) at the target dpi.
- Size text and lines so they remain legible when the figure is reduced to column width.

### 6.5 Colour
- Supply colour figures in **CMYK, not RGB**, for print fidelity (RGB colours can shift on
  conversion). Keep a consistent colour profile across all figures.
- Use colour purposefully and consistently. *(Project note: keep the Temperature-Split palette —
  Normal cells cold/blue, cancer warm/red — but verify it survives CMYK conversion and remains
  colour-blind-safe; see 6.7.)*

### 6.6 Fonts and lines in figures
- Use **one sans-serif font for all figures** — Arial or Helvetica preferred (Times, Courier, Symbol
  also acceptable). Do not mix fonts across figures.
- **Embed all fonts** in vector files so text is preserved in production.
- Keep lettering large enough to read at final size; use consistent line weights.

### 6.7 Accessibility and **alt text** (required — asked about specifically)
NAR/OUP require every figure to be accessible:
- **Provide alt text for every figure.** Place each alt-text description **in the main manuscript
  file, directly under the relevant figure's legend, preceded by the literal label `Alt text:`**.
- Purpose: alt text lets screen-reader users understand the content and context of the figure. Keep
  it **concise and informative** — describe what the figure shows and its take-home point, not every
  data value.
- Alt text is delivered only via e-readers/screen readers; it **does not appear in the typeset
  article**, so it is separate from (and complementary to) the visible caption.
- Design figures for accessibility: sufficient **contrast**, colour-blind-safe palettes, and do not
  rely on colour alone to convey meaning (add labels, patterns, or direct annotation). Follow the
  C4DISC accessibility guidelines.

*Example alt-text pattern for a project figure:*
`Alt text: Grouped bar chart comparing batch-mixing scores across 31 harmonization methods; MNN, FSQN R and SVA score highest, while most other methods cluster near the no-correction baseline.`

### 6.8 Captions and numbering
- Number figures sequentially (`Figure 1`, `Figure 2`, …) in order of first mention.
- Every figure and table must be cited in the text.
- Caption format in the template: `Figure 1: <caption text>.`

### 6.9 Graphical Abstract (mandatory for all article types at initial submission)
- **Aspect ratio 5:2, landscape**, minimum **127 × 50 mm (5 × 2 in)**.
- Must be **original** — not a copy of any main or supplementary figure.
- Use colour; use text **sparingly** (mainly labels); font: sans-serif (Arial), **12–16 pt**.
- Should read **top-to-bottom or left-to-right** and illustrate one main point or method.
- **No trademarked/copyrighted images or logos** (e.g. the text "UniProt" is fine, the UniProt logo
  is not).

### 6.10 Third-party and tool-generated graphics
- **BioRender:** supply an article-and-journal-specific licence and add the required BioRender
  acknowledgement in the figure caption (or in Acknowledgements for a graphical abstract).
- Obtain **reproduction permission** for any third-party figure/image before submission (at latest
  before acceptance); include the required credit line under open-access licences.
- **Maps** must be accurate and note how they were generated/sourced.

---

## PART 7 — Tables

- Supply tables in an **editable format (Word)** — **never as an image**.
- **Avoid heavy formatting**: no colour/shading (not reproduced in the web version); do not use
  tabs/spaces to fake column alignment (use real table cells).
- Put **units in the column or row headers**, not in the body cells.
- Explain any symbols (e.g. asterisks, superscripts) in a **table footnote**.
- Number tables sequentially; **every table must be cited in the text**.

---

## PART 8 — Data availability and deposition (mandatory)

### 8.1 The Data Availability Statement (DAS) is required
- A DAS is **mandatory** for every NAR article, placed under a `DATA AVAILABILITY` heading near the
  end (before References).
- It must **describe how to access the data** via links or unique identifiers (accession numbers,
  DOIs).
- Underlying data must be **public at acceptance** (reviewer-access tokens/private links allowed
  during review), unless a legal/privacy/ethical restriction applies — in which case state the
  restriction and the access mechanism.
- **Insufficient on its own:** "data are available from the corresponding author on reasonable
  request."
- The template's standard supplementary line is separate: see Part 7 of the template
  (`Supplementary Data are available at NAR online.`).

### 8.2 Repository preference order (FAIR)
1. **Subject-specific public repository** (preferred) → provide accession numbers.
2. **General-purpose repository issuing a permanent DOI** — Zenodo, Figshare, Dryad, Code Ocean,
   Harvard Dataverse, OSF → provide the DOI.
3. **Institutional repository** with a stable link (author guarantees permanence).
4. **Supplementary files** with the article (last resort).
- **Not acceptable as a primary archive** (no permanent DOI): GitHub, DropBox, Google Drive.

### 8.3 Data-type-specific deposition (the ones relevant to this project in **bold**)
| Data type | Required repository | Standard/notes |
|---|---|---|
| **Genome-wide expression / sequencing** | **GEO, SRA/BioProject, or ArrayExpress/BioStudies** | Must be viewable on UCSC or IGV browser; provide accession + reviewer token/session URL |
| **Microarray data** | **GEO or ArrayExpress/BioStudies** | **Follow MIAME** (Minimum Information About a Microarray Experiment) |
| **High-throughput sequencing (Illumina/PacBio/nanopore)** | **SRA (via BioProject), ArrayExpress/BioStudies, or GEO** | ENA not recommended (no private referee access); assembled seqs → GenBank/EMBL/DDBJ |
| Novel nucleic acid sequences | GenBank / EMBL / DDBJ | Give sequence names + accession numbers |
| Novel protein sequences | UniProt (SPIN tool) | — |
| Molecular structures | wwPDB (RCSB/PDBe/PDBj); EMDB/EMPIAR (cryo-EM); CCDC (small molecules); NDB (nucleic acids) | Supply validation report + coordinates for review |
| Mass-spec proteomics | ProteomeXchange / PRIDE | — |
| qPCR | — | **Follow MIQE** guidelines |
| Human identifiable data | EGA or dbGaP (controlled access) | Provide study/dataset IDs |
| **Software / source code** | **Zenodo or Figshare (permanent DOI)** — GitHub/GitLab for review, but **GitHub alone is NOT sufficient** | Include install instructions, manual, usage example, sample I/O |

### 8.4 Software / code requirements (relevant — ComboBatch pipeline)
- Deposit the analysis source code in a **permanent-DOI repository (Zenodo or Figshare)**, or as
  supplementary material. A GitHub/GitLab link alone does **not** satisfy the policy.
- Provide documentation: installation instructions, a manual, a clear usage example/test case, and
  sample input/output.
- Software cited in the paper should appear as a **full citation in the reference list**.
- (You can connect a GitHub release to Zenodo/Figshare to auto-mint a DOI.)

### 8.5 Example Data Availability Statements (fill the square brackets)
- **Public repository, subject-specific:**
  `The data underlying this article are available in [repository name] and can be accessed with [accession number(s)] at [URL/DOI].`
- **Generic repository with DOI:**
  `The data underlying this article are available in [Zenodo/Figshare] at https://doi.org/[DOI].`
- **Derived / third-party data:**
  `The data underlying this article were derived from sources in the public domain: [source names and accession numbers/URLs].`
- **Code:**
  `The source code used for [analysis] is available in [Zenodo/Figshare] at https://doi.org/[DOI].`
- **Restricted data:**
  `The data underlying this article cannot be shared publicly due to [reason]. The data will be shared on reasonable request to the corresponding author [and subject to approval by …].`

### 8.6 Submission checklist
At submission you must complete NAR's online **Data Availability, Standardization, and
Reproducibility Checklist**, which is attached for reviewers.

---

## PART 9 — Author contributions (CRediT)

- An **Author Contributions statement is mandatory** (at submission, no later than revision).
- Use the **CRediT taxonomy** (Conceptualization, Data curation, Formal analysis, Funding
  acquisition, Investigation, Methodology, Project administration, Resources, Software, Supervision,
  Validation, Visualization, Writing—original draft, Writing—review & editing).
- Format (from template):
  `John Smith: Conceptualization, Formal analysis, Methodology, Validation, Writing—original draft. Peter Jones: Conceptualization, Visualization, Writing—review & editing. …`
- Non-author contributors go in **Acknowledgements** with their contribution described.
- **AI/NLP tools do not qualify as authors.** Disclose any AI-tool use in the cover letter and in
  Methods or Acknowledgements.

---

## PART 10 — Funding, conflicts, acknowledgements, ethics

### Funding (specific formatting rules)
- Give the **full official funder name** ("National Institutes of Health", not "NIH"); match the
  Crossref Funder Registry spelling exactly.
- Grant numbers in brackets: `[grant number xxxx]`; multiple: `[grant numbers xxxx, yyyy]`.
- Separate agencies with a semicolon (and "and" before the last).
- Attribute to individuals with `to [author initials]`.
- **End with the open-access charge line:** `Funding for open access charge: [agency/number].`
- Example:
  `This work was supported by the National Institutes of Health [AA123456 to A.B., BB123456 to C.D.]; and the Alcohol & Education Research Council [abcde123456]. Funding for open access charge: National Institutes of Health.`

### Conflict of Interest
- Mandatory statement disclosing any financial or other interests that could bias the work
  (funding sources, personal relationships, direct academic competition). If none:
  `Conflict of interest statement. None declared.`

### Acknowledgements
- Thank non-author contributors and describe their contribution. Include required BioRender
  acknowledgement here for graphical abstracts.

### Ethics (include in Methods where applicable)
- **Human subjects:** follow the Declaration of Helsinki; state ethics-committee approval with the
  body name and permit/reference number; obtain and state written informed consent; anonymise
  patient data (no names/ID numbers; blanking eyes is not adequate de-identification).
- **Animals:** state institutional animal-care approval, permit numbers, and compliance with
  national/international guidelines; consult ARRIVE guidelines.
- **Geopolitical neutrality:** maps must state how they were generated/sourced.

---

## PART 11 — Supplementary data

- Should **enhance but not be required to understand** the main article; online only; **not
  copyedited/typeset**.
- Submit in a **separate file** from the main article. **Cite every supplementary item in the main
  text.**
- **Preferably a single PDF** containing all text, figures, tables, and legends. If that is not
  possible: **max 10 files**, **each ≤ 2 MB**.
- Non-PDF formats: text → .docx/.html/.rtf; spreadsheets → .xlsx/.csv (combine tables into one Excel
  workbook, one table per labelled worksheet); figures per the figure guidelines; movies → .mp4.
- Filenames must be self-explanatory (e.g. `Supplementary Figure 1`). Style must match the
  manuscript. Must work in any browser.
- Host only on OUP or a preferred partner (e.g. Dryad) — **not** on personal sites, Google Docs, or
  YouTube.
- **Required statement** at the end of the manuscript when supplementary data exist:
  `Supplementary Data are available at NAR online.`
- **Videos** (main article): .mp4, highest resolution, with a still image for the print PDF; must be
  cited in the text; no third-party-hosted (e.g. YouTube) videos.

---

## PART 12 — Rewriting checklist (run before declaring a draft NAR-ready)

**Structure & formatting**
- [ ] Sections present and in template order (Part 2); top-level headings ALL-CAPS bold.
- [ ] All red template instruction text deleted.
- [ ] Body 11 pt, 1.15 spacing, 1-inch margins, A4; line numbers added for review.
- [ ] Equations inserted via Word equation editor (not images).

**Front matter**
- [ ] Title jargon-free, no non-standard abbreviations.
- [ ] ≤ 3 corresponding authors (asterisks); equal contributors marked with `†` + footnote.
- [ ] Submitting author ORCID present.
- [ ] Graphical Abstract: 5:2 landscape, ≥127×50 mm, original, sans-serif 12–16 pt, no logos.

**Abstract**
- [ ] Single paragraph ≤ 200 words; no references, figure citations, or URLs (URLs only for
      Database/Web Server issues).

**References**
- [ ] Numbered by order of appearance; every reference cited and vice versa.
- [ ] ≥4 authors → first three + `et al.`; full article titles; Chemical Abstracts journal
      abbreviations; DOIs on online items.
- [ ] Software/data cited as full references; websites/software/personal comms *not* in the list.

**Figures**
- [ ] TIFF/EPS (or high-res PNG), not JPG; line art 600–1200 dpi, halftone/colour 300 dpi at final
      size.
- [ ] Width fits 8.3–17.35 cm; CMYK; single embedded sans-serif font.
- [ ] **`Alt text:` line under every figure legend**; colour-blind-safe, high contrast, not
      colour-dependent.
- [ ] Every figure numbered and cited; BioRender licence + acknowledgement if used; permissions
      cleared for third-party material.

**Tables**
- [ ] Editable Word tables (not images); units in headers; symbols explained in footnotes; no
      colour/shading or tab-alignment; all cited in text.

**Back matter**
- [ ] Author Contributions (CRediT) present; AI-tool use disclosed if any.
- [ ] Funding formatted per rules, ending with open-access charge line.
- [ ] Conflict of Interest statement present.
- [ ] **Data Availability statement** present with repository + accession/DOI; MIAME/MINSEQE for
      array/seq data; **code in Zenodo/Figshare with DOI** (not GitHub alone).
- [ ] Supplementary data: separate file(s), ≤10 files ≤2 MB each (or one PDF), all cited;
      `Supplementary Data are available at NAR online.` added.
- [ ] Ethics statements (human/animal) in Methods if applicable.

---

## PART 13 — Key links

| Link | Description |
|---|---|
| https://academic.oup.com/nar/pages/author-guidelines | Main NAR author guidelines |
| https://academic.oup.com/nar/pages/data_deposition_and_standardization | Data deposition & standardization (repositories, MIAME/MIQE) |
| https://academic.oup.com/nar/pages/methods-guidelines | Methods article guidelines |
| https://academic.oup.com/nar/pages/Ms_Prep_Database | Database issue guidelines |
| https://academic.oup.com/nar/pages/Submission_Webserver | Web Server issue guidelines |
| http://mc.manuscriptcentral.com/nar | Submission site (ScholarOne) |
| https://credit.niso.org/ | CRediT contributor-roles taxonomy |
| https://orcid.org/ | ORCID registration |
| https://c4disc.pubpub.org/pub/v4up8c2n/release/1 | C4DISC accessibility guidelines (alt text, contrast) |
| https://help.biorender.com/en/articles/3619405-citing-biorender | BioRender citation/acknowledgement |
| https://zenodo.org / https://figshare.com | Permanent-DOI repositories for code/data |
| https://www.ncbi.nlm.nih.gov/geo/ | GEO (array/expression deposition) |
| https://www.ebi.ac.uk/biostudies/arrayexpress | ArrayExpress/BioStudies |
| https://www.ncbi.nlm.nih.gov/sra | SRA (raw sequencing) |
| https://www.wma.net/policies-post/wma-declaration-of-helsinki-ethical-principles-for-medical-research-involving-human-subjects/ | Declaration of Helsinki |
| https://arriveguidelines.org/ | ARRIVE animal-research guidelines |

---

*Compiled 2026-07-17 from the NAR author-guidelines pages, the NAR data-deposition page, OUP
figure/accessibility standard text, and the `nar-word-template November 2025.docx` template.
Where NAR-specific numbers were not published, OUP's cross-journal standard figures were used (noted
in Part 6); confirm against the live pages before final submission.*
