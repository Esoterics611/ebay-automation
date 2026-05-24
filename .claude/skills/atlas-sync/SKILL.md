---
name: atlas-sync
description: Audit drift between atlas/SELECTORS.md and the actual _SEL_* constants in src/ebay_automation/components/, then patch whichever side is stale. Use after a qa-debug session that updated several selectors, or on demand when the docs feel out of date. The atlas docs are part of the AI-assisted onboarding surface — if they lie, the next agent session starts from a broken map.
---

# atlas-sync

`atlas/SELECTORS.md` is documentation for both humans and AI agents.
It encodes the selector strategy and a per-component table of preferred
locators. When code-level `_SEL_*` constants drift but the doc doesn't
follow, the next debugging session reads a lying map — worse than no
map.

## When to invoke

- A `qa-debug` session just patched two or more `_SEL_*` constants.
- A new component was added.
- The user asks "are the atlas docs up to date?"
- Quarterly hygiene (if the user decides to schedule it).

## Workflow

### 1. Inventory the code

```bash
grep -rn "_SEL_" src/ebay_automation/components/ \
  | grep -E "^[^:]+:[0-9]+:\s+_SEL_[A-Z_]+\s*[=:]" \
  | sort
```

Each hit is a `(file, line, constant, value)` tuple. Build a mental
table:

| Component | Constant | Current value |

### 2. Read the atlas table

`atlas/SELECTORS.md` carries an "Examples by component" table. Compare
each row against the code inventory.

### 3. Classify each mismatch

- **DOC STALE** — code is correct (recent fix); doc still references
  the old selector. Update the doc.
- **CODE STALE** — doc is correct (intended target); code never caught
  up. This is rarer but real; verify with a `qa-debug` probe before
  patching code.
- **DOC MISSING** — code has a constant that the table doesn't mention.
  Add a row.
- **CODE MISSING** — table mentions a locator that no component uses.
  Either the table is aspirational (delete the row) or a component was
  removed without doc cleanup (delete the row).

### 4. Update one side

Patch the side that's wrong, in one commit per logical mismatch. Do
NOT silently rewrite the doc to match incorrect code — that launders
a code bug into "intentional."

## Output format

Report to the user as a single table before patching:

```
Component         | Constant                  | Code value         | Doc value          | Verdict
HeaderComponent   | _SEL_SEARCH_SUBMIT_NAME   | "Search" exact     | "Search" exact     | OK
ResultCardComp.   | _SEL_PRICE_CSS            | .s-card__price     | .s-item__price     | DOC STALE
FilterPanelComp.  | _SEL_SORT_TRIGGER_NAME    | "Sort" exact       | regex ^Sort:       | DOC STALE
```

The user approves before any doc edits.

## Anti-patterns

- "Auto-syncing" — generating SELECTORS.md from the code on every push.
  The atlas is editorialized; auto-generation strips the *why* lines
  that make the doc useful.
- Adding every `_SEL_*` constant to the table. The table is for the
  selectors a *new contributor* needs to understand quickly — internal
  helpers (regex patterns reused inside a method) don't belong.
- Burying drift in the same commit as a fix. Doc sync is its own
  commit so reviewers can see the maintenance discipline.

## Optional: pre-commit hook

If atlas drift becomes recurring, add a simple grep-based check to
`scripts/` and wire it into `init_env.sh` or CI:

```bash
# scripts/check_atlas_sync.sh — fails CI if SELECTORS.md mentions a
# class name that no component imports.
for sel in $(grep -oE '\.s-[a-z_-]+' atlas/SELECTORS.md | sort -u); do
    grep -rq "$sel" src/ebay_automation/components/ || \
        echo "atlas references $sel but no component uses it"
done
```

Keep it advisory (`exit 0`) until the noise level is known.
