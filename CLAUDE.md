# ebay-automation — Claude Code Guide

## Stack

| Tool | Purpose |
|---|---|
| Python 3.11+ | Runtime |
| uv | Package & venv manager |
| Playwright (sync) | Browser automation |
| pytest | Test runner |
| pytest-playwright | Playwright fixtures for pytest |
| pytest-xdist | Parallel test execution (`-n auto`) |
| allure-pytest | Rich HTML reporting |
| ruff | Linter |
| black | Formatter |

---

## Directory layout

```
ebay-automation/
├── pyproject.toml
├── pytest.ini
├── .env.example
├── atlas/                       # architecture & spec documentation
│   ├── PAGES.md                 # URL patterns, roles, dynamic behaviors
│   ├── FLOWS.md                 # E2E flow specification
│   ├── SELECTORS.md             # selector strategy & priority
│   └── EDGE_CASES.md            # cookie banners, geo, variants, currency …
├── db/                          # YAML store (config + scenario data)
│   └── data.yaml                # environments, scenarios, demos under top-level keys
├── src/
│   └── ebay_automation/
│       ├── db/                  # TestDatabase + dataclass models
│       ├── utils/               # logger, ScreenshotManager
│       ├── components/          # Page-Object layer (BaseComponent + regions)
│       └── services/            # Business-logic layer (auth, search, cart, variants)
└── tests/
    ├── conftest.py              # session fixtures: db, env, services, tracing
    ├── smoke/
    ├── regression/
    └── slow/
```

---

## Architecture rules

### Layer flow

```
tests  →  services  →  components  →  playwright
```

- **Tests** call service methods and assert on return values / page state.
- **Services** own all business logic; they compose component calls into
  meaningful actions (e.g. `SearchService.find_listings_under_budget`).
- **Components** wrap a single UI region. They know selectors and expose
  intent-revealing methods. They never contain business logic.
- **Playwright** (`page.*`) is called **only** inside components.

### Hard rules

| Rule | Reason |
|---|---|
| No selectors in test files | Couples tests to markup; breaks en masse on redesign |
| No `time.sleep()` anywhere | Race conditions; use `expect(locator).to_…()` or `page.wait_for_*` |
| `Decimal` for all money values | Float rounding errors corrupt price comparisons |
| No hardcoded URLs in tests | All base URLs come from `db/data.yaml` (`environments` table) via `PROFILE` |
| Secrets in `.env` only | Structural config in `db/data.yaml`; credentials never in the YAML |

### Component conventions

- One class per UI region.
- Constructor signature: `__init__(self, page: Page, root: Locator | None = None)`.
- Extend `BaseComponent` (`src/ebay_automation/components/base.py`).
- Selector strings live as class-level constants prefixed `_SEL_`.
- Use the scoped `self.locator(...)` factory rather than raw
  `self.page.locator(...)` whenever the component has a non-default root.

### Service conventions

- One service class per domain area (search, cart, variants, auth).
- Services receive the `page` object at construction; never import a
  service from another service.
- Return domain values or dataclasses, not `Locator` instances.

### Naming

| Thing | Convention | Example |
|---|---|---|
| Test file | `test_<what>.py` | `test_search_results.py` |
| Test function | `test_<scenario>` | `test_search_under_budget_caps_subtotal` |
| Component class | `<Region>Component` | `SearchBarComponent` |
| Service class | `<Domain>Service` | `SearchService` |
| Selector constant | `_SEL_<ELEMENT>` | `_SEL_SEARCH_INPUT_NAME` |

---

## Anti-patterns to refuse

- `time.sleep(n)` — always reject; suggest `expect()` or `wait_for_*`.
- Raw `page.locator(…)` calls inside test functions.
- Magic strings for prices — wrap in `Decimal(str(value))`.
- Importing a component directly inside another component.
- `assert "text" in page.content()` — use locator assertions.
- Ignoring the `PROFILE` env var and hardcoding environment URLs.
- `float(price)` — always `Decimal`.

---

## How to run

```bash
# Install deps (first time)
uv sync

# Install Playwright browsers (first time)
uv run playwright install chromium

# Smoke suite (dev profile, headed)
uv run pytest -m smoke

# Full regression, 4 workers, CI profile, headless
PROFILE=ci uv run pytest -m regression -n 4

# Generate & open Allure report
uvx allure generate allure-results -o allure-report --clean
uvx allure open allure-report

# Lint + format check
uv run ruff check .
uv run black --check .
```

Switch environments by setting `PROFILE` in `.env` or inline:

```bash
PROFILE=ci uv run pytest -m smoke
```

Profiles are defined in `db/data.yaml` under `environments:` (currently `dev` and `ci`).
