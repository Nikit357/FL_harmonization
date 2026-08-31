# Skill: Implementation Plan Writing

## When to invoke

Use this skill whenever Daniil asks you to write an implementation plan for any change
to the harmonization pipeline, analysis notebooks, Docker/K8s infrastructure, or any
other component in this repository. Recognizable triggers:

- "Write an implementation plan for …"
- "Plan how to add / change / refactor …"
- "Describe all necessary steps to …"
- "What files need to change if I want to …"

**Do not implement any code changes until Daniil explicitly approves the plan.**

---

## Step 1 — Study the repository before writing anything

Before drafting the plan, perform a thorough dependency investigation. Follow this
priority order to save tokens:

### 1a. Read documentation first

Read these files before touching any Python scripts:

1. **Root `CLAUDE.md`** (`~/CLAUDE.md`) — project-wide conventions.
2. **Project `CLAUDE.md`** (`FL_harmonization/CLAUDE.md`) — dataset, key files,
   current status, code standards.
3. **Subsystem `CLAUDE.md`** (e.g., `harmonization-scripts/CLAUDE.md`,
   `harmonization-metrics/CLAUDE.md`, `k8s/CLAUDE.md`) — covers the specific area of the
   change. Read before any script in that subdirectory.
4. **`project_overview.md`** — authoritative reference for function signatures, S3 key
   patterns, filter strategies, method registry. Check here for exact names and counts
   before grepping scripts.
5. **Other markdown files** — `README.md` files in subdirectories, any `*_plan_*.md`
   files left from previous planning sessions.

### 1b. Then search scripts for specifics

After reading the documentation, use targeted searches (grep, `find`) to locate:

- The exact function or constant to be changed and its line number.
- All other files that import, reference, or enumerate the same symbol (e.g.,
  `ALL_STRATEGIES`, `METHODS`, `build_filter_strategies`).
- Docstrings and argparse help strings that describe the thing being changed — these
  are often forgotten and become stale.
- Any hardcoded count literals that will need updating (e.g., "dict of 11 labeled …",
  "all 10 strategies", `"(default: all 10)"`).

Search broadly — check all `.py` files and all `.md` files in the relevant subdirectory
and adjacent directories. Do not assume a symbol is used only in the file where it is
defined.

---

## Step 2 — Draft the plan document

Write the plan as a standalone Markdown file in the relevant subdirectory with the
naming convention:

```
<short_topic>_plan_YYMMDD.md
```

Example: `rare_batch_removal_strategy_plan_260516.md`

### Required sections

#### Overview
One paragraph. Explain *what* the change is, *why* it is needed (the scientific or
engineering motivation), and the key design decision (e.g., dynamic vs. hardcoded,
threshold-based vs. explicit list).

#### Background / reference data
If the change is driven by specific data (batch names, sample counts, thresholds),
list that data here in a table. Include all values provided by Daniil.

#### Files to change
One numbered section per file. For each file:

- State the file path relative to the project root.
- List every location (by approximate line number and context string) that must change.
- Show the **before** snippet and the **after** snippet for every edit.
- Explain *why* this file needs to change (import, enumeration, docstring, docs, etc.).

Group locations within a file with sub-headings (e.g., `1a`, `1b`, `1c`).

#### Files that do NOT need to change
Explicitly list scripts/files that might seem relevant but require no edits, and state
why. This prevents Daniil from second-guessing the scope.

#### Side effects and caveats
Warn about:

- Cache invalidation (e.g., `/tmp/bench_filter_strategies.pkl` must be deleted).
- S3 key changes and new output counts.
- Changes to cross-product job counts (e.g., "adds 4 prepared pairs and 156 normalized
  outputs").
- Backward-compatibility risks if existing downstream code references the old count.

#### Verification commands
Provide copy-paste commands to verify the change after implementation:

```bash
source ~/venvs/collagen_3_11/bin/activate
python harmonization-scripts/test_mock.py          # import/smoke check
```

And any Python one-liners to confirm the new symbol or key is present.

#### TODO checklist
End every plan with a detailed, ordered checklist of every atomic edit. Each item
must be checkable independently. Format as a GitHub-flavored Markdown task list:

```markdown
## TODO

- [ ] `bench_shared.py` — add constant near line 83
- [ ] `bench_shared.py` — add strategy computation after the last simple strategy definition
- [ ] `bench_shared.py` — add new key to `strategies` dict
- [ ] `bench_shared.py` — update docstring strategy count
- [ ] `run_prep_parallel.py` — append new strategy key to `ALL_STRATEGIES`
- [ ] `run_prep_parallel.py` — update `--strats` help text count and valid-values list
- [ ] `run_norm_parallel.py` — same two changes as `run_prep_parallel.py`
- [ ] `run_cross_product_parallel.py` — append to `ALL_STRATEGIES`; update argparse help
- [ ] `project_overview.md` — update strategy table count and add new row
- [ ] `CLAUDE.md` (harmonization-scripts) — update `build_filter_strategies` comment count
- [ ] `make_slides.py` — update count cells and strategy table row (lowest priority)
- [ ] Delete `/tmp/bench_filter_strategies.pkl` on pod before running new strategy
- [ ] Run `test_mock.py` to verify no import errors
- [ ] Manually verify new key is present in `build_filter_strategies()` output
```

---

## Step 3 — Present the plan for approval

After writing the plan file, summarize it to Daniil in the chat:

1. State the file name and path where the plan was saved.
2. Give a brief (5–10 line) summary: what changes, how many files, key design decision,
   any important caveats (cache invalidation, S3 impact, etc.).
3. End with: **"Please review and approve before I implement."**

Do not begin any code edits until Daniil replies with explicit approval.

---

## Anti-patterns to avoid

| Anti-pattern | Why it fails |
|---|---|
| Reading only the directly changed file | Misses `ALL_STRATEGIES` duplicated across 3 dispatcher scripts |
| Skipping docstrings and argparse help | Leaves stale user-visible text that contradicts the code |
| Forgetting count literals in markdown | `project_overview.md` and `CLAUDE.md` go stale and confuse future planning |
| Hardcoding a list when a threshold is cleaner | Threshold-based logic is self-documenting and survives dataset changes |
| Implementing immediately without approval | Violates the Human-in-the-Loop protocol in the project `CLAUDE.md` |
| Omitting documentation files from the TODO list | Documentation drift is a real risk in this project; always include `.md` file edits in the checklist |

---

## Example invocation

```
User: I want a new batch removal strategy that removes RNA_BATCH entries with fewer
      than 50 samples. Write an implementation plan.

Claude:
  1. Read root CLAUDE.md, project CLAUDE.md, harmonization-scripts/CLAUDE.md,
     project_overview.md.
  2. Grep for ALL_STRATEGIES, build_filter_strategies, strategy count literals
     in all .py and .md files.
  3. Write <topic>_plan_YYMMDD.md with all sections above.
  4. Present summary and wait for Daniil's approval.
