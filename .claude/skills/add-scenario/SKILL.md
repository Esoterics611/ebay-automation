---
name: add-scenario
description: Add a new parametrized test row to db/data.yaml under scenarios: or demos:. Use when the user asks to add a regression case, smoke case, or demo narrative. Codifies the naming, ILS rescaling, tag conventions, and the validation step so the new row is picked up by pytest_generate_tests without a code change.
---

# add-scenario

The data-driven testing pattern in this repo: scenarios live in
`db/data.yaml`, not in test code. `tests/conftest.py::pytest_generate_tests`
parametrizes `tests/test_data_driven.py::test_scenario` from every row
tagged `regression`; `scripts/simulate_usage.py` reads `demos:`. Adding
a test = adding a YAML row.

## When to invoke

- "Add a test for <query> under <price>" — almost always means a new
  scenario row, not a new `tests/test_*.py` file.
- "Add a demo for <category>" — `demos:` table, with a `narrative` field.
- The user names a query, a price ceiling, and an expected result count.

## Decide which table

| Table | Purpose | Required fields |
|---|---|---|
| `scenarios:` | Parametrized into the regression suite | `name`, `query`, `max_price`, `limit`, `min_results`, `allow_partial`, `tags` |
| `demos:` | Driven by `scripts/simulate_usage.py` only | same as above + `narrative` (multiline string) |

If unsure: ask. Most additions are `scenarios:`.

## Id and naming

- Id: lowercase kebab-case, prefixed with the tier:
  `smoke-<noun>` / `regression-<noun>` / `demo-<noun>`.
- `name`: human-readable, includes currency in the title
  (`"Bluetooth speakers under ILS 150"`).
- `query`: the literal string typed into eBay search.

## Money — ILS, quoted string

`max_price` MUST be a quoted string. The loader does
`Decimal(str(value))`; unquoted floats lose precision. Values are in
ILS (this suite's currency — see README). Convert from USD at the
current rate (~2.89 ILS/USD), then round up to a clean boundary so the
test isn't fragile to small currency moves:

| USD intent | ILS value | Rationale |
|---|---|---|
| $10 | `"30.00"` | smallish item |
| $20 | `"60.00"` | |
| $30 | `"90.00"` | |
| $50 | `"150.00"` | |
| $75 | `"225.00"` | |
| $100 | `"300.00"` | |

## Tags drive routing

- `[smoke]` — runs under `pytest -m smoke`. Keep these fast (small
  `limit`, `allow_partial: true`).
- `[regression]` — full E2E parametrization. `allow_partial: false`
  for strict scenarios; `true` for tolerant ones (and set `min_results`
  to the minimum acceptable count).
- A row can carry both: `[smoke, regression]`.

## Validation

After writing the row:

```bash
uv run python -c "
from ebay_automation.db.client import TestDatabase
db = TestDatabase('db')
s = db.scenarios.get('<new-id>')
print(s)
"
```

If the dataclass refuses the row (missing field, wrong type), the
loader raises `ValueError` with a structured message — fix the YAML
and re-run.

Then run the new test in isolation:

```bash
uv run pytest "tests/test_data_driven.py::test_scenario[<new-id>-chromium]" -v
```

A passing isolated run with the actual eBay markup is the only proof
the scenario's `max_price` and `limit` are realistic.

## Anti-patterns

- Hardcoding the query / price into a new `test_*.py` file. The whole
  point of `pytest_generate_tests` is that new cases are data, not code.
- Floats for `max_price`. Quoted strings only.
- USD values silently mixed into ILS thresholds. The README's currency
  notice is the contract; respect it.
- `allow_partial: true` AND `min_results == limit`. That defeats the
  partial-tolerance — pick one or the other.
