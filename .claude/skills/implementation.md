# Skill: Implementation

## When to invoke

Use this skill whenever Daniil asks you to implement an approved plan for any change
to the harmonization pipeline, analysis notebooks, Docker/K8s infrastructure, or any
other component in this repository. Recognizable triggers:

- "Implement it"
- "Apply the plan"
- "Go ahead and do it"
- "Implement all tasks"

**Do not begin until Daniil has explicitly approved the plan.** If no plan document
exists, invoke the `implementation_plan_writing` skill first.

---

## Step 1 — Read every target file before editing anything

Before making the first edit, read all files that the plan says will change. Do this
in parallel (multiple Read calls in a single message) to save time and tokens.

For each file, identify:

- The **exact surrounding text** at every edit location (line numbers from the plan
  are approximate — trust context strings, not numbers).
- Whether the exact text in the plan's "before" snippet still matches the file. If it
  does not, locate the correct text and proceed with the correct match.
- Dependencies between edits within the same file (e.g., a new variable must be
  defined before it is referenced in a dict).

Do not start editing until you have confirmed the match locations for all files.

### What to read first

1. The **plan document** — re-read the TODO checklist to confirm the full scope.
2. The **core library** (e.g., `bench_shared.py`) — most other changes depend on the
   symbol names introduced here.
3. All **dispatcher scripts** that share the same list (e.g., `ALL_STRATEGIES`) — they
   must stay in sync.
4. **Documentation files** (`CLAUDE.md`, `project_overview.md`, `README.md`) — find
   the exact count literals and table rows that need updating.

---

## Step 2 — Edit in dependency order

Apply edits in the order listed in the plan's TODO checklist. Within a single file,
apply edits from top to bottom so line positions are consistent.

### Parallelism rules

- **Independent files:** submit all edits in a single message as multiple Edit calls.
  For example, updating `ALL_STRATEGIES` in `run_prep_parallel.py`,
  `run_norm_parallel.py`, and `run_cross_product_parallel.py` can be done in one
  message because none depends on the other.
- **Dependent edits within one file:** apply sequentially — do not send two edits to
  the same file in one message.

### Coding standards to follow during implementation

- Add comments where the WHY is non-obvious (a hidden constraint or
  surprising invariant). Narrate WHAT the code does in docstring of functions.
- No extraneous refactoring or cleanup beyond what the plan describes.
- Variable naming: match the style of the surrounding code (snake_case, descriptive).
- Line length: 88 characters (Black).
- Do not add error handling for conditions that cannot occur in the current codebase.

---

## Step 3 — Run the smoke test after editing the core library

After finishing all edits to `bench_shared.py` (or whichever file contains the core
logic), run the smoke test before continuing to documentation files:

Example:
```bash
source ~/venvs/collagen_3_11/bin/activate
python harmonization-scripts/test_mock.py
```

Exit code 0 = safe to continue. If the test fails with an error introduced by this
change, fix it before proceeding. Pre-existing failures (methods that raise
`NotImplementedError` or fail due to missing R packages) are expected and not caused
by the current change — confirm by checking the failure names against the plan.

Also verify the new symbol is importable:

```python
python -c "
import sys; sys.path.insert(0, 'harmonization-scripts')
from bench_shared import <NEW_SYMBOL>
print(<NEW_SYMBOL>)
"
```

---

## Step 4 — Mark each TODO item as completed in the plan document

As soon as an edit is confirmed successful, update the corresponding `- [ ]` item in
the plan's TODO checklist to `- [x]`. Do this incrementally — mark each group of
related items complete before moving to the next file, so the plan document always
reflects the current real state.

If a TODO item from the plan turns out not to be needed (e.g., the count was already
correct), mark it `- [x]` and add a short note in parentheses explaining why no edit
was needed.

Post-implementation checks that require the live K8s pod (e.g., deleting a pickle
cache, verifying live data counts) cannot be done locally. Mark these items with a
note: `(requires live pod)` and leave them unchecked.

---

## Step 5 — Do a final consistency check

After all edits are applied, verify that no stale count literals or references remain:

Example:
```bash
# Check that all three dispatcher ALL_STRATEGIES lists are identical
grep -A 20 "^ALL_STRATEGIES" harmonization-scripts/run_prep_parallel.py
grep -A 20 "^ALL_STRATEGIES" harmonization-scripts/run_norm_parallel.py
grep -A 20 "^ALL_STRATEGIES" harmonization-scripts/run_cross_product_parallel.py

# Check that all count literals in documentation match the new count
grep -n "dict of [0-9]\+ labeled\|Build all [0-9]\+ filter\|× [0-9]\+ filter\|→ [0-9]\+ labeled" \
    harmonization-scripts/CLAUDE.md \
    harmonization-scripts/bench_shared.py \
    project_overview.md
```

If any mismatch is found, fix it immediately.

---

## Anti-patterns to avoid

| Anti-pattern | Why it fails |
|---|---|
| Editing without reading first | The plan's line numbers are approximate; the exact surrounding text must be confirmed before editing |
| Sending two edits to the same file in one message | The second edit's `old_string` may not match after the first edit is applied |
| Marking TODO items done before the edit is confirmed | Gives a false picture of progress if an edit fails |
| Adding comments that describe WHAT the code does | Violates code standards; well-named identifiers are sufficient |
| Editing beyond the plan's scope | Introduces unreviewed changes; scope creep that bypasses the Human-in-the-Loop protocol |
| Skipping the smoke test | An import error in the core library will break all workers silently |
| Forgetting to update all three dispatcher `ALL_STRATEGIES` lists | They are independent copies that must stay in sync; one missed update causes the strategy to be silently skipped by that dispatcher |
| Leaving count literals stale in documentation | `CLAUDE.md`, `project_overview.md`, and docstrings go stale and confuse future planning |

---

## Example — Adding `I_rare_batches_removed` strategy (2026-05-16)

This example shows the full implementation flow for the plan at
`harmonization-scripts/rare_batch_removal_strategy_plan_260516.md`.

### Step 1: Read all target files in parallel

Eight files were read in two batches:

**Batch 1** (core logic + dispatchers):
- `bench_shared.py` lines 78–100 (constant location) and lines 440–530 (function body)
- `run_prep_parallel.py` lines 70–130 (docstring + ALL_STRATEGIES)
- `run_norm_parallel.py` lines 68–145 (docstring + ALL_STRATEGIES)

**Batch 2** (remaining dispatchers + docs):
- `run_cross_product_parallel.py` lines 100–130 (ALL_STRATEGIES) and 525–540 (argparse)
- `project_overview.md` lines 150–170 (strategy table) and 205–215 (count comment)
- `harmonization-scripts/CLAUDE.md` lines 120–130 (function signature comment)
- `make_slides.py` lines 255–270, 358–400, 573–600 (three locations)

Grep was used to confirm exact line numbers for count literals:
```bash
grep -n "sample-removal strategies\|Sample-removal strategy\|10 strat\|40 jobs" make_slides.py
grep -n "build_filter_strategies\|dict of [0-9]" harmonization-scripts/CLAUDE.md
```

### Step 2: Edits in dependency order

**Phase 1 — `bench_shared.py` (4 sequential edits, top to bottom):**
1. Insert `MIN_BATCH_SIZE: int = 50` after `BAD_COHORTS_B`.
2. Update `build_filter_strategies()` docstring: "10" → "11".
3. Update Returns section: added "(11 entries)".
4. Insert `ann_I` computation after `ann_G = _f(...)`.
5. Add `"I_rare_batches_removed": ann_I` to strategies dict.

**Phase 2 — Three dispatcher scripts (parallel, one message):**
All three files updated in a single message:
- Docstring count updated in `run_prep_parallel.py` and `run_norm_parallel.py`
- argparse help updated in `run_cross_product_parallel.py`

Then another parallel message to append `"I_rare_batches_removed"` to all three
`ALL_STRATEGIES` lists simultaneously.

**Phase 3 — Documentation files (parallel):**
`project_overview.md` and `harmonization-scripts/CLAUDE.md` updated in one message.

**Phase 4 — `make_slides.py` (5 sequential edits, top to bottom):**
Slide text count, table count cell, strategy table row, pipeline overview job count,
pipeline filter strategy list — each applied after the previous was confirmed.

**Phase 5 — New file:**
`harmonization-scripts/README.md` created with `Write` tool.

### Step 3: Smoke test

```bash
python harmonization-scripts/test_mock.py  # exit code 0
```

Also verified import directly:
```python
python -c "
import sys; sys.path.insert(0, 'harmonization-scripts')
from bench_shared import MIN_BATCH_SIZE
print(MIN_BATCH_SIZE)  # → 50
"
```

Output: `MIN_BATCH_SIZE = 50`, `Import OK`.

The smoke test reported 6 failures (27_dwd, 28_npn, 31_ruv3prps, 33_amdbnorm,
34_arsyn, 38_harman) — all pre-existing R-package failures, confirmed against the
Known startup failures table in `CLAUDE.md`. Not caused by this change.

### Step 4: TODO items marked complete

All 22 implementation items marked `[x]` in the plan document. Two post-implementation
checks left unchecked with `(requires live pod)` notes:
- Delete `/tmp/bench_filter_strategies.pkl` on the K8s pod.
- Verify `len(strats['I_rare_batches_removed'])` in the expected range ~5,000–5,300.

### Step 5: Consistency check

```bash
grep -n "dict of [0-9]\+ labeled" harmonization-scripts/CLAUDE.md
# → dict of 12 labeled annotation DataFrames ✓

grep -A 14 "^ALL_STRATEGIES" harmonization-scripts/run_prep_parallel.py \
                              harmonization-scripts/run_norm_parallel.py \
                              harmonization-scripts/run_cross_product_parallel.py
# → all three lists end with "I_rare_batches_removed" ✓
```

---

## Order of implementation (general template)

1. **Core library** (`bench_shared.py`) — constants, new function bodies, new dict entries
2. **Dispatcher scripts** — `ALL_STRATEGIES` and docstrings (parallel across files)
3. **Documentation** — `CLAUDE.md`, `project_overview.md` (parallel)
4. **Presentation** — `make_slides.py` (lowest priority; sequential within file)
5. **New files** — `README.md` or other new files (last)
6. **Smoke test** — after step 1; confirm exit code 0
7. **Consistency grep** — after all edits; confirm no stale count literals remain
8. **Mark plan complete** — update TODO checklist throughout
