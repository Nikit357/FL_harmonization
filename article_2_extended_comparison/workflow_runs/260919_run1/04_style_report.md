# 04 — Style-editor report (Article 2, run 260919_run1)

## Status

- **Complete:** mechanical gates (overlap, style, banned-phrase grep) run and recorded; manual LLM-register pass over the whole manuscript; 12 prose edits applied to `manuscript/FL_metric_classes_F1000_260917.md`; the `.docx` brought into agreement in the same pass as plain edits (0 `w:ins`, 0 `w:del`).
- **In progress:** nothing.
- **Not started:** Phase 6 and anything downstream of it (stop point set by Daniil). Figma assembly untouched (rule 8).

## Gates

| Gate | Exit | Result |
|---|---|---|
| `check_overlap.py` (8-gram, 2 sources) | 0 | 8-grams vs FL_harmonization_article_NAR_260912.docx and Harmonization_metrics_extended_260802_v2.docx; 40 allow-listed hits ignored; no verbatim overlap. Re-run after the edits: still 0. |
| `check_style.py --journal f1000` | 0 | f1000 profile. After edits: 10,266 words (limit 20,000), 0 em-dash, 33 semicolons (3.21/1k). All six section budgets inside range. |
| banned-phrase grep | 1 (no match) | grep -nEi "rather than|, not [a-z]+\.|it is not .*, it is" over manuscript/*.md printed nothing, before and after the edits. |

Word count 10302 → 10266 (-36). Section budgets after the edits: abstract 300, introduction 729, methods 1359, results 6389, conclusions 685, back matter 712 — all inside range.

## Manual pass — 12 edits, all applied

### 1. empty intensifier
*Location:* Methods / Metric classes and the election procedure

- **Before:** so the classes can be compared against the choice that was actually published.
- **After:** so the classes can be compared against the published choice.

### 2. bare antithesis ("X and not Y")
*Location:* Methods / The biology-facing metric classes L, M and N

- **Before:** A single-class fold is a test and not a defect: a classifier trained on every batch but one can still mislabel a DLBCL-only batch, and dropping such folds would remove that failure from the record.
- **After:** A single-class fold is a test in its own right: a classifier trained on every batch but one can still mislabel a DLBCL-only batch, and dropping such folds would remove that failure from the record.

### 3. epigram for a plain condition
*Location:* Methods / The biology-facing metric classes L, M and N

- **Before:** We treated a mean marker correlation above 0.75 as necessary and insufficient. Passing it carries no information on its own,
- **After:** We treated a mean marker correlation above 0.75 as a necessary condition. Passing it carries no information on its own,

### 4. tricolon padding / sentence fragment
*Location:* Results / Metric classes capture non-overlapping components

- **Before:** Three families, three orderings, one set of approaches. The rest of this article takes that observation and makes it quantitative.
- **After:** The three families ordered the same set of approaches differently. The rest of this article makes that observation quantitative.

### 5. heading grammar after removing the banned contrast form
*Location:* Results / section heading

- **Before:** ### Batch-associated variance is redistributed across principal components instead of eliminated
- **After:** ### Batch-associated variance is redistributed across principal components instead of being eliminated

### 6. arch phrasing ("what it should")
*Location:* Results / Preservation of biomarker expression

- **Before:** When class L is allowed to elect on its own it therefore chooses what it should: doing nothing.
- **After:** When class L elects on its own it therefore chooses unharmonized output.

### 7. proofless superlative ("clearest statement")
*Location:* Results / Preservation of biomarker expression

- **Before:** That 01_raw passes the joint gate in 80 of its 84 approaches is the clearest statement of what this gate does and does not test: passing it does not require having harmonized anything.
- **After:** 01_raw passes the joint gate in 80 of its 84 approaches, so passing the gate does not require having harmonized anything.

### 8. rhetorical filler ("because it is the point")
*Location:* Results / Preservation of biomarker expression

- **Before:** They win on classes L and M while failing a basic check on the scale of their own output. We report that contradiction because it is the point: a class elects what it measures.
- **After:** They win on classes L and M while failing a basic check on the scale of their own output. We report that contradiction because the scale of the output lies outside what classes L and M measure: a class elects what it measures.

### 9. empty intensifier ("actually") and rhetorical framing
*Location:* Results / Cross-batch prediction elects a third set

- **Before:** Class N asks the question a user of a harmonized matrix actually asks: can a classifier fitted on the batches that are present label the samples of a batch it has never seen.
- **After:** Class N asks whether a classifier fitted on the batches that are present can label the samples of a batch it has never seen.

### 10. hedge ("effectively")
*Location:* Results / The sets elected by the individual metric classes

- **Before:** Four of the nine groups are therefore effectively single-method verdicts,
- **After:** Four of the nine groups are therefore single-method verdicts,

### 11. proofless adjective ("concrete")
*Location:* Results / The sets elected by the individual metric classes

- **Before:** This is the concrete cost of choosing a criterion before running a benchmark.
- **After:** This is the cost of choosing a criterion before running a benchmark.

### 12. negation-first framing and intensifier without a number
*Location:* Results / The sets elected by the individual metric classes

- **Before:** Each recommendation is correct under its own criterion and fails under the next one. The disagreement is not noise between similar answers: the elected sets barely intersect, so the choice of metric class determines the recommendation more than the data do.
- **After:** Each recommendation is correct under its own criterion and fails under the next one. The choice of metric class therefore determines the recommendation more than the data do.

## Sent back to the writer (number, citation or claim — outside the style editor's limit)

**1. Software availability**

- *Defect:* Unresolved placeholder in the deposited text: "archived at [TO CONFIRM: new FL_harmonization release DOI]". The other three archive DOIs in the same paragraph are concrete.
- *Why not fixed here:* A DOI is a citation. Inventing or guessing one is prohibited; the placeholder must be filled by the writer once the release is minted.

**2. References (last line of the manuscript)**

- *Defect:* The manuscript states that the supporting passage quoted from each cited article is kept in `manuscript/reference_support_260917.md`. That file does not exist; the manuscript folder holds only the manuscript .md/.docx, figure_legends_260917.md and references_260917.md.
- *Why not fixed here:* This is a factual claim about a deliverable, not prose. Either the file has to be produced or the sentence has to be changed by the writer.

**3. Competing interests**

- *Defect:* "[the earlier competing-interests sentence, superseded]" The affiliation block gives affiliation 2 to ten authors: Nikitin, Savchenko, Bobe, Meerson, Nesmelov, Harutyunyan, Paponova, Kravets, Zaitsev and Bagaev.
- *Why not fixed here:* A competing-interest declaration is a claim about people, and the count is a number. The writer or Daniil has to decide which list is right.

**4. Data availability**

- *Defect:* The Zenodo record 10.5281/ZENODO.22737294 is quoted as deposited. Project memory records that draft 22737294 was fully uploaded on 2026-09-14 but NOT published, so the DOI may not yet resolve.
- *Why not fixed here:* A DOI and its resolvability are citation facts. The writer has to confirm publication state before submission.

## Artifacts written

- `<repo>/article_2_extended_comparison/workflow_runs/260919_run1/04_style_report.json`
- `<repo>/article_2_extended_comparison/workflow_runs/260919_run1/04_style_report.md`
- `<repo>/article_2_extended_comparison/manuscript/FL_metric_classes_F1000_260917.md`
- `<repo>/article_2_extended_comparison/manuscript/FL_metric_classes_F1000_260917.docx`

## .docx state

`<w:ins >` = 0, `<w:del >` = 0. Plain edits applied run-level with python-docx; no suggestion-mode markup (rule 12). Verified after saving.