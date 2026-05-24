# eBay Automation Suite

[![regression](https://github.com/vanguard-dao/ebay-automation/actions/workflows/regression.yml/badge.svg)](https://github.com/vanguard-dao/ebay-automation/actions/workflows/regression.yml)

> **Currency note for reviewers.** eBay localizes search-results prices to
> the visitor's IP. Because this assessment is delivered from Israel,
> scenario thresholds and the e2e test budget are denominated in **ILS**
> (at ~2.89 ILS / USD). The price parser accepts both `$` and `ILS`
> anchors, so a US-based reviewer running from a US IP can rescale
> `db/data.yaml` thresholds back to USD without code changes — see
> §"Assumptions and Limitations".

End-to-end automation suite for ebay.com built with Python 3.11, Playwright,
pytest, and Allure. Implements the four spec functions — guest auth,
search-with-price-cap, add-to-cart, cart-total assertion — inside a strict
page-object architecture with a services layer on top.

## 1. Quick Start

```bash
git clone <repo-url>
cd ebay-automation
./scripts/init_env.sh
PROFILE=ci uv run pytest -m regression -n 4 --alluredir=allure-results
uv run allure serve allure-results
```

`./scripts/init_env.sh` is idempotent. On a fresh box it installs uv, syncs
Python deps, and provisions chromium + its system libs (one-time sudo). On
subsequent runs it detects the libs are already present and skips the sudo
step — safe for re-runs and cron.

## 2. Architecture

```
+-------------------------------------------------------+
|  tests/  (pytest, parametrized from db/data.yaml)     |
+-------------------------------------------------------+
                        |
                        v
+-------------------------------------------------------+
|  services/  (the 4 spec functions, business logic)    |
|    auth | search | cart | variants                    |
+-------------------------------------------------------+
                        |
                        v
+-------------------------------------------------------+
|  components/  (POM: pages + sub-components)           |
|    home, search_results, item, cart                   |
|    header, cookie_banner, filter_panel, result_card   |
+-------------------------------------------------------+
                        |
                        v
+-------------------------------------------------------+
|  Playwright sync API                                  |
+-------------------------------------------------------+

Side branch:
  scripts/simulate_usage.py  ──> services/ ──> components/
  (same services used by tests; framework is library-quality)
```

### Why services on top of components

The four spec functions orchestrate across multiple pages and own business
logic — pagination bounds, price parsing, random variant selection, money
math (`Decimal`-only). Placing that on any one component breaks
single-responsibility (a "cart page" that also knows how to walk search
results is not a cart page anymore). Placing it in tests creates duplication
across the smoke, regression, and data-driven suites. A services layer keeps
each tier with one job: components know markup, services know flow, tests
know assertions.

### Why YAML DB instead of .env

Test scenarios, environment profiles, and demo narratives are structured,
queryable, and shared across the regression suite, the data-driven runner,
and `scripts/simulate_usage.py`. A single [`db/data.yaml`](db/data.yaml)
holds all three tables under top-level keys (`environments`, `scenarios`,
`demos`) — typed loaders (`db/models.py`) and accessor classes
(`db.scenarios.where(tag=...)`) make the data first-class. `.env` is
reserved for secrets, which on a public, guest-only site like eBay is
mostly empty here. Money values (`max_price`) are quoted strings so they
parse via `Decimal(str(...))` without ever touching `float`.

### Locator strategy

Role-based locators are first choice (`get_by_role`, `get_by_label`,
`get_by_text`). CSS is fallback when the site exposes no semantic role
(e.g. eBay's price node carries only a `data-testid`). XPath is reserved
for the single case the brief explicitly requires it: the assignment asks
to "retrieve the items using XPath," so `SearchResultsPage.card_links_via_xpath()`
implements that retrieval path with an explicit, commented XPath expression,
while the default search flow stays role/CSS-based for resilience.
Cookie-banner dismissal and
region/currency cookie pinning happen once in `tests/conftest.py` fixtures,
not per-test. See [`atlas/SELECTORS.md`](atlas/SELECTORS.md) for the full
priority order and per-component locator table.

### Extension points

To add a new flow: document it in [`atlas/FLOWS.md`](atlas/FLOWS.md), add a
method on an existing service (or a new service if the flow spans a new
domain), then either add a test under `tests/` or a scenario row in
[`db/data.yaml`](db/data.yaml) under the `scenarios:` table — the data-driven runner picks it
up automatically. Components rarely need to change because they cover the
markup surface eBay actually exposes (4 pages, ~5 sub-components).

## 3. Project Layout

```
ebay-automation/
├── README.md                          # this file
├── CLAUDE.md                          # AI-session conventions
├── ReadMeAIBugs.md                    # static review of AI-generated code
├── pyproject.toml                     # deps, pytest config, ruff/black
├── atlas/                             # spec documentation
│   ├── PAGES.md                       #   URL patterns, roles, dynamic behaviors
│   ├── FLOWS.md                       #   E2E flow specification
│   ├── SELECTORS.md                   #   selector priority + per-component table
│   └── EDGE_CASES.md                  #   cookie banners, geo, variants, currency
├── db/                                # YAML store (config + scenario data)
│   └── data.yaml                      #   environments, scenarios, demos under top-level keys
├── src/ebay_automation/
│   ├── db/                            # TestDatabase + dataclass models
│   ├── utils/                         # logger, ScreenshotManager, price_parser, paginator
│   ├── components/                    # POM layer (BaseComponent + 9 regions)
│   └── services/                      # business logic (auth, search, cart, variants)
├── tests/
│   ├── conftest.py                    # fixtures: db, services, region cookies, Allure env
│   ├── test_smoke.py                  # @smoke   — fast critical-path
│   ├── test_search_under_price.py     # @regression — full E2E
│   ├── test_data_driven.py            # @regression — parametrized from db/data.yaml (scenarios)
│   └── unit/test_price_parser.py      # pure-Python parser tests (22 cases)
├── scripts/
│   ├── init_env.sh                    # idempotent local bootstrap
│   ├── simulate_usage.py              # headed demo of services outside pytest
│   └── init_fresh_system.py           # connectivity probe; pattern for owned systems
├── ai/prompts/                        # the 8 build prompts in order
└── .github/workflows/regression.yml   # CI: chromium-headless on ubuntu-latest
```

## 4. Configuration

**YAML DB.** Structural test data lives in [`db/data.yaml`](db/data.yaml)
and is loaded via `TestDatabase`. Three top-level keys: `environments`
maps a profile id (`dev`, `ci`) to browser/runtime knobs (headless,
slow-mo, trace policy, region, currency, pagination cap); `scenarios`
defines parameterised regression rows (query, max_price, limit,
min_results, allow_partial, tags); `demos` carries the same shape plus a
`narrative` field for the demo runner.

**Environment selection.** Profile is chosen via the `PROFILE` env var
(default `dev`). `dev` is headed with slow-mo for watchability; `ci` is
headless with tighter pagination and `retain-on-failure` traces.
[`.env`](.env.example) is gitignored and reserved for secrets; eBay is
public and guest-only, so it's mostly empty here.

## 5. Running Tests

```bash
# Smoke (network-dependent, ~30s):
uv run pytest -m smoke

# Full regression (live eBay, several minutes):
uv run pytest -m regression

# Regression, 4 parallel workers:
PROFILE=ci uv run pytest -m regression -n 4

# Single test:
uv run pytest tests/test_search_under_price.py::test_full_e2e_search_add_assert

# With trace recorded on failure (default in addopts; can override):
uv run pytest -m regression --tracing=on

# Allure report:
uv run pytest -m regression --alluredir=allure-results
uvx allure generate allure-results -o allure-report --clean
uvx allure open allure-report
```

Unit tests (pure Python, no browser) run instantly:

```bash
uv run pytest tests/unit -v   # 22 cases against price_parser
```

## 6. Reports

`allure-results/` (raw JSON + the autogenerated `environment.properties`)
and `allure-report/` (rendered HTML) are produced by every run.
[`.github/workflows/regression.yml`](.github/workflows/regression.yml)
uploads both, plus the Playwright `test-results/` folder (traces, videos,
failure screenshots), as artifacts on every workflow run — including
failed ones (`continue-on-error: true` on the test step). The latest run's
artifacts are downloadable from the **Actions** tab in GitHub.

The Allure dashboard — suites, timeline, the Environment panel populated by
`conftest.py`, and per-step screenshots — is downloadable from the
**Actions** tab after any CI run, or viewable locally via
`uv run allure serve allure-results`.

## 7. Demo Mode

```bash
uv run python scripts/simulate_usage.py
```

Drives every demo scenario from [`db/data.yaml`](db/data.yaml) (`demos:` table)
through the same `search → add-to-cart → assert-subtotal` flow as the
regression suite, but headed (`PROFILE=dev`) and outside pytest. Its
purpose is to prove the framework is library-quality: a sales demo or
internal tool can reuse the exact services regression covers, with no
fixture rig and no parallel implementation to maintain.

## 8. CI

The single workflow [`.github/workflows/regression.yml`](.github/workflows/regression.yml)
runs on `push` to `main`, `pull_request` targeting `main`, and
`workflow_dispatch`. It boots Python 3.11, installs `uv`, syncs deps,
installs chromium with system libs, executes `pytest -m regression -n 4`
with `PROFILE=ci`, generates an Allure HTML report, and uploads four
artifact bundles (`allure-results`, `allure-report`, `reports`,
`test-results`) regardless of test outcome.

## 9. Assumptions and Limitations

- **Guest auth only.** eBay's real login flow is gated by FunCaptcha /
  hCaptcha; reliably automating it in CI is a moving target with a
  credentials-storage burden out of proportion with this flow's needs.
  The assignment explicitly allows a guest/stub approach. `AuthService`
  pre-loads region + currency cookies and lands on the home page.
- **ILS / Israel region by default.** Locale and currency are pinned via
  cookie at the browser-context level (`db/data.yaml` `environments:`).
  eBay localizes price text to the visitor's IP, so the parser handles
  both `$`- and `ILS`-anchored amounts. To run against USD, change the
  profile's `region`/`currency` and rescale `scenarios:` `max_price`
  values — no code changes required.
- **eBay markup is volatile.** Selectors prefer accessibility roles; CSS
  is used only where eBay exposes no semantic anchor (price block,
  result card); no XPath is required for the implemented flow.
- **Pagination bounded.** `max_pages_to_paginate` in
  `db/data.yaml` under `environments:` (default 5 / 3 for ci) caps the
  search-with-price loop so a query that doesn't yield `limit` items
  doesn't walk indefinitely.
- **Variant selection is random.** When an item has variant pickers, the
  service chooses a random in-stock option per combobox. Exhaustive
  variant traversal is out of scope.
- **Auctions are skipped, not failed.** A live auction listing has no
  Add-to-Cart button; the cart service logs a warning and continues with
  the remaining URLs. The data-driven test honors `allow_partial` from
  the scenario row to decide whether a short result set is fatal.

## 10. AI-Assisted Development

This repository was built using Claude Code with an atlas-driven approach.
[`atlas/`](atlas/) describes the *system under test* (pages, flows,
selectors, edge cases) so the AI doesn't have to infer eBay's structure
from scratch each turn. [`CLAUDE.md`](CLAUDE.md) encodes per-session
conventions and anti-patterns (no `time.sleep`, no selectors in tests,
`Decimal`-only money, layer boundaries). [`ai/prompts/`](ai/prompts/)
holds the eight build prompts used to generate each layer, in order —
`01_scaffold.md` through `08_documentation.md`, with an extra
`00_cleanup.md` capturing the mid-stream scope reduction.

Every prompt is a design-by-contract specification: file paths, class
names, method signatures, behavior, and verification commands —
implementation is delegated to the tool. The senior judgment lives in
the design, not in the typing. [`ReadMeAIBugs.md`](ReadMeAIBugs.md)
applies the same lens to AI-generated test code that *didn't* go through
that discipline — a static review of five concrete failure modes.

## 11. Bug Review

See [`ReadMeAIBugs.md`](ReadMeAIBugs.md).
