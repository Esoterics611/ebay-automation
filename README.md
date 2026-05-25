# eBay Automation Suite

[![regression](https://github.com/vanguard-dao/ebay-automation/actions/workflows/regression.yml/badge.svg)](https://github.com/vanguard-dao/ebay-automation/actions/workflows/regression.yml)

End-to-end Playwright + pytest suite for ebay.com. Implements the four
spec functions — guest auth, search-with-price-cap, add-to-cart,
cart-total assertion — in a strict page-object + services architecture.

> **Reviewer note.** Tests run from Israel and prices arrive in **ILS**
> (~2.89 ILS / USD). `db/data.yaml` thresholds are ILS values; the
> parser handles `$`, `ILS`, `₪`, and `NIS`. To rescale to USD, edit
> the YAML — no code change.
> See §"Assumptions and Limitations" for the full environment matrix.

---

## 1. Quick Start

```bash
git clone <repo-url>
cd ebay-automation
./scripts/init_env.sh
PROFILE=ci uv run pytest -m regression -n 4 --alluredir=allure-results
allure serve --host 0.0.0.0 -p 8080 allure-results
# open http://localhost:8080
```

`init_env.sh` is idempotent. It installs `uv`, syncs Python deps,
provisions Chromium, and pulls a portable Adoptium JRE + Allure CLI
into `~/.local/`. No system Java needed. On WSL2, `--host 0.0.0.0`
is required so the Windows browser can reach the Allure server.

## 2. Architecture

```
┌───────────────────────────────────────────────────────┐
│  tests/     pytest, parametrized from db/data.yaml    │
├───────────────────────────────────────────────────────┤
│  services/  4 spec functions; business logic          │
│             auth | search | cart | variants           │
├───────────────────────────────────────────────────────┤
│  components/  POM: pages + sub-components             │
│               home, search_results, item, cart        │
│               header, cookie_banner, filter_panel,    │
│               result_card                             │
├───────────────────────────────────────────────────────┤
│  Playwright sync API                                  │
└───────────────────────────────────────────────────────┘

Side branch:
  scripts/simulate_usage.py → services/ → components/
  (same services as tests; framework is library-quality)
```

**Layer rules.** Components own selectors and a single UI region.
Services compose components into the spec flows and own business
logic (pagination, price parsing, variant choice, money math).
Tests call services and assert on return values. Components never
contain business logic; tests never contain selectors.

**Money is `Decimal` end-to-end.** `db/data.yaml` quotes prices as
strings so they enter Python via `Decimal(str(...))` without
floating-point intermediate. The parser accepts the four currency
anchors above.

**Locators prefer roles.** `get_by_role`, `get_by_label`,
`get_by_text` first. CSS where eBay exposes no semantic anchor.
XPath only where the brief explicitly required it
(`SearchResultsPage.card_links_via_xpath()`). Full priority order
in [`atlas/SELECTORS.md`](atlas/SELECTORS.md).

**Data-driven.** Add a row to `db/data.yaml` `scenarios:` and the
regression runner picks it up via `pytest_generate_tests`. No new
test file needed.

## 3. Project Layout

```
ebay-automation/
├── README.md                        # this file
├── CLAUDE.md                        # AI-session conventions
├── ReadMeAIBugs.md                  # static review of AI-generated code
├── pyproject.toml                   # deps, pytest config, ruff/black
├── atlas/                           # spec docs
│   ├── PAGES.md                     #   URLs, roles, dynamic behaviors
│   ├── FLOWS.md                     #   E2E flow specification
│   ├── SELECTORS.md                 #   locator priority + per-component table
│   └── EDGE_CASES.md                #   cookie banners, geo, variants, currency
├── db/
│   └── data.yaml                    # environments, scenarios, demos
├── src/ebay_automation/
│   ├── db/                          # TestDatabase + dataclasses
│   ├── utils/                       # logger, screenshots, parser, paginator
│   ├── components/                  # POM layer (BaseComponent + 9 regions)
│   └── services/                    # auth, search, cart, variants
├── tests/
│   ├── conftest.py                  # fixtures + region cookies + Allure env
│   ├── test_smoke.py                # @smoke
│   ├── test_search_under_price.py   # @regression — full E2E
│   ├── test_data_driven.py          # @regression — parametrized from YAML
│   └── unit/test_price_parser.py    # 32 parser cases, no browser
├── scripts/
│   ├── init_env.sh                  # bootstrap (uv, chromium, JRE, allure)
│   ├── simulate_usage.py            # headed demo runner
│   └── init_fresh_system.py         # connectivity probe
├── .claude/skills/                  # AI-assisted maintenance playbooks
└── .github/workflows/regression.yml # CI + GitHub Pages deploy
```

## 4. Configuration

`db/data.yaml` holds three tables under top-level keys:

- `environments` — profile → browser knobs (headless, slow_mo, region,
  currency, pagination cap)
- `scenarios` — parametrized regression rows (query, max_price, limit,
  min_results, allow_partial, tags)
- `demos` — same shape + `narrative`, used by `simulate_usage.py`

Profile is chosen with `PROFILE=`. Default `dev` is headed with
slow-mo (watchable). `ci` is headless with tighter pagination.
`.env` is reserved for secrets; eBay is guest-only here, so it's
mostly empty.

## 5. Running Tests

```bash
# Smoke (~30 s, live eBay)
uv run pytest -m smoke

# Full regression (live eBay, several minutes)
uv run pytest -m regression

# Headless, 4 workers (CI profile)
PROFILE=ci uv run pytest -m regression -n 4

# One test
uv run pytest tests/test_search_under_price.py::test_full_e2e_search_add_assert

# Unit tests (no browser, instant)
uv run pytest tests/unit -v   # 32 parser cases

# Allure report
allure generate allure-results -o allure-report --clean
allure open --host 0.0.0.0 -p 8080 allure-report
```

## 6. Reports

Every run produces `allure-results/` (raw JSON + environment.properties)
and `allure-report/` (rendered HTML). The CI workflow uploads both as
artifacts and **deploys the HTML to GitHub Pages** on every push to
main — the latest run is at the Pages URL on the repo's About panel.

Per-step screenshots, Playwright traces, videos, and failure
screenshots are attached automatically on test failure via the
`addopts` in `pyproject.toml`. The Environment panel of the Allure
report shows profile, region, base URL, Python version, and
Playwright version (from `conftest.py::_allure_environment`).

## 7. Demo Mode

```bash
uv run python scripts/simulate_usage.py
```

Drives every `demos:` row in `db/data.yaml` through
`search → add-to-cart → assert-subtotal`, headed and outside pytest.
Proves the services layer is library-quality: a sales demo or
internal tool can reuse the exact services regression covers.

## 8. CI

`.github/workflows/regression.yml` runs on push to main, PRs, and
manual dispatch. It installs deps, runs `pytest -m regression -n 4`
under `PROFILE=ci`, generates the Allure HTML report, uploads four
artifact bundles (`allure-results`, `allure-report`, `reports`,
`test-results`), and — on push to main — publishes `allure-report/`
to GitHub Pages.

## 9. Assumptions and Limitations

- **Guest auth only.** eBay's real login is gated by FunCaptcha /
  hCaptcha; the assignment allows guest mode. `AuthService` pre-loads
  region + currency cookies and lands on the home page.

- **ILS / Israel region by default.** Locale and currency are pinned
  in `db/data.yaml` `environments:` and via browser-context cookies.
  Parser handles `$`, `ILS`, `₪`, `NIS`. Switch to USD by editing the
  profile and rescaling scenario thresholds — no code change.

- **Headless (`PROFILE=ci`) can hit Akamai.** eBay's edge challenges
  some headless fingerprints with a "Checking your browser…"
  interstitial; `Locator.fill` then times out on the search box. The
  suite ships two non-deceptive reductions in `tests/conftest.py`:
  `--disable-blink-features=AutomationControlled` and an explicit
  Chrome user-agent. Sufficient on most CI runners and clean
  residential IPs. The headed `dev` profile is the reliable local
  path. Long-term fix: fixture replay
  (see `.claude/skills/fixture-recorder/SKILL.md`).

- **Cart lives at `cart.ebay.com`.** The legacy `www.ebay.com/cart`
  path is deprecated and 302s to a route that 404s in some regions.
  `CartPage.URL_PATH` points at the subdomain, which works for
  guests in all regions tested. The cart-page subtotal uses the `₪`
  Unicode shekel sign, so the parser anchors include it. As a
  defensive safety net, `CartPage.is_unavailable()` detects the
  `/n/error` redirect and `CartService` raises `CartUnavailableError`
  — tests `pytest.skip` with the URL in the reason instead of failing
  opaquely. In normal operation the safety net never fires.

- **eBay markup is volatile.** Selectors prefer accessibility roles;
  CSS only where eBay exposes no role; no XPath in the default flow.

- **Pagination bounded.** `max_pages_to_paginate` (default 5 / 3 for
  ci) caps the search loop. A query that doesn't yield `limit` items
  won't walk indefinitely.

- **Variant selection is random.** When an item has variant pickers,
  the service picks a random in-stock option. Exhaustive variant
  traversal is out of scope.

- **Auctions are skipped, not failed.** Auctions have no Add-to-Cart
  button; the cart service logs and continues. The data-driven test
  honors `allow_partial` to decide whether a short result is fatal.

## 10. AI-Assisted Development

Built with Claude Code using an atlas-driven approach. The `atlas/`
docs describe the system under test (pages, flows, selectors, edge
cases) so the AI doesn't re-derive eBay's structure every session.
`CLAUDE.md` encodes the per-session conventions (no `time.sleep`, no
selectors in tests, `Decimal` only, layer boundaries). `ai/prompts/`
holds the eight build prompts that produced each layer, in order.

`.claude/skills/` codifies the maintenance loop as five focused
playbooks:

| Skill | When it fires |
|---|---|
| **qa-debug** | A `Locator` timeout / strict-mode failure → triage existing artifacts, then patch the `_SEL_*` constant |
| **flake-triage** | Classifies a failure as DRIFT / ENVIRONMENT / NETWORK / TRANSIENT / TEST-ASSUMPTION before any code is touched |
| **add-scenario** | New regression case → YAML row, ILS rescale, validation |
| **atlas-sync** | After several selector patches, audit doc vs code |
| **fixture-recorder** | Convert a flake-prone live test to offline replay via `page.route` |

The skills are the playbook; the architecture is the artifact.
`ReadMeAIBugs.md` is a static review of AI-generated test code that
did **not** go through this discipline — a control case showing
five concrete failure modes.

## 11. Bug Review

See [`ReadMeAIBugs.md`](ReadMeAIBugs.md).
