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
├── conftest.py              # session fixtures: browser, base_url, env_config
├── pytest.ini
├── pyproject.toml
├── .env.example
├── db/
│   └── environments.json   # base_url, timeouts per PROFILE
├── tests/
│   ├── smoke/
│   ├── regression/
│   └── slow/
├── components/             # Page-Object layer (Playwright interactions only)
│   ├── base.py
│   ├── header/
│   ├── search/
│   └── listing/
├── services/               # Business-logic layer (orchestrates components)
└── utils/
    └── config.py           # loads db/environments.json via PROFILE env var
```

---

## Architecture rules

### Layer flow

```
tests  →  services  →  components  →  playwright
```

- **Tests** call service methods and assert on return values / page state.
- **Services** own all business logic; they compose component calls into
  meaningful actions (e.g. `SearchService.find_cheapest_listing`).
- **Components** wrap a single UI region. They know selectors and expose
  intent-revealing methods. They never contain business logic.
- **Playwright** (`page.*`) is called **only** inside components.

### Hard rules

| Rule | Reason |
|---|---|
| No selectors in test files | Couples tests to markup; breaks en masse on redesign |
| No `time.sleep()` anywhere | Race conditions; use `expect(locator).to_be_visible()` or `page.wait_for_*` |
| `Decimal` for all money values | Float rounding errors corrupt price comparisons |
| No hardcoded URLs in tests | All base URLs come from `db/environments.json` via `PROFILE` |
| Secrets in `.env` only | Structural config in `db/environments.json`; credentials never in JSON |

### Component conventions

- One class per UI region, file name matches class name in snake_case.
- Constructor signature: `__init__(self, page: Page) -> None`.
- Extend `BaseComponent` (components/base.py).
- Selector strings live as class-level constants prefixed `_SEL_`.

### Service conventions

- One service class per domain area (search, cart, account, …).
- Services receive the `page` object at construction; never import components
  from other services.
- Return domain objects or primitives, not `Locator` instances.

### Naming

| Thing | Convention | Example |
|---|---|---|
| Test file | `test_<what>.py` | `test_search_results.py` |
| Test function | `test_<scenario>` | `test_search_by_keyword_returns_results` |
| Component class | `<Region>Component` | `SearchBarComponent` |
| Service class | `<Domain>Service` | `SearchService` |
| Selector constant | `_SEL_<ELEMENT>` | `_SEL_SEARCH_INPUT` |

---

## Anti-patterns to refuse

- `time.sleep(n)` — always reject; suggest `expect()` or `wait_for_*`.
- Raw `page.locator(…)` calls inside test functions.
- Magic strings for prices — wrap in `Decimal(str(value))`.
- Importing a component directly inside another component.
- `assert "text" in page.content()` — use locator assertions.
- Ignoring the `PROFILE` env var and hardcoding environment URLs.

---

## How to run

```bash
# Install deps (first time)
uv sync

# Install Playwright browsers (first time)
uv run playwright install chromium

# Smoke suite
uv run pytest -m smoke

# Full regression, 4 workers, with Allure
uv run pytest -m regression -n 4

# Generate & open Allure report
uvx allure generate allure-results -o allure-report --clean
uvx allure open allure-report

# Lint + format check
uv run ruff check .
uv run black --check .
```

Switch environments by setting `PROFILE` in `.env` or inline:

```bash
PROFILE=staging uv run pytest -m smoke
```
