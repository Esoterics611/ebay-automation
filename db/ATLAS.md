# db/

JSON store for structural configuration and static test data. Loaded by
`ebay_automation.db.client.TestDatabase` and validated against the
dataclasses in `ebay_automation.db.models`.

| File | Schema | Purpose |
|---|---|---|
| `environments.json` | `Environment` | Per-profile (`dev`, `ci`) browser + runtime config |
| `scenarios.json` | `Scenario` | Parameterised scenarios driving the regression / smoke suites |
| `expectations.json` | `Expectation` | Pass criteria per scenario id |
| `demo_scenarios.json` | `DemoScenario` | Curated showcase scenarios with narrative copy |

**Never put secrets here.** Secrets belong in `.env` (gitignored). Money
fields (`max_price`, `max_acceptable_total_pct`) are stored as **strings**
and parsed to `Decimal` on load — never floats.
