# db/

Single-file YAML store for structural configuration and static test data.
Loaded by `ebay_automation.db.client.TestDatabase` and validated against
the dataclasses in `ebay_automation.db.models`.

| File | Top-level keys | Purpose |
|---|---|---|
| `data.yaml` | `environments` | Per-profile (`dev`, `ci`) browser + runtime config — schema: `Environment` |
| | `scenarios` | Parameterised scenarios driving the regression / smoke suites; each carries its own `min_results` and `tags` — schema: `Scenario` |
| | `demos` | Curated showcase scenarios with narrative copy — schema: `DemoScenario` |

**Never put secrets here.** Secrets belong in `.env` (gitignored). Money
fields (`max_price`) are stored as **quoted strings** and parsed via
`Decimal(str(value))` on load — never floats.
