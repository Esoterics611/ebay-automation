Write the final documentation. The README is the single comprehensive 
doc that a Ness reviewer reads first. CLAUDE.md stays as the AI-session 
conventions doc. No separate ARCHITECTURE.md.

=== README.md structure ===

# eBay Automation Suite

[![regression](https://github.com/<USERNAME_PLACEHOLDER>/<REPO_PLACEHOLDER>/actions/workflows/regression.yml/badge.svg)](https://github.com/<USERNAME_PLACEHOLDER>/<REPO_PLACEHOLDER>/actions/workflows/regression.yml)

(Leave the USERNAME and REPO placeholders for the user to fill in after 
push — they'll edit one line in the README.)

## 1. Quick Start

One code block:
  git clone <repo-url>
  cd ebay-automation
  ./scripts/init_env.sh
  PROFILE=ci uv run pytest -m regression -n 4 --alluredir=allure-results
  uv run allure serve allure-results

## 2. Architecture

Layers diagram (ASCII):

  +-------------------------------------------------------+
  |  tests/  (pytest, parametrized from db/scenarios.json)|
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

### Why services on top of components

One short paragraph: the 4 spec functions orchestrate across multiple 
pages and own business logic (pagination, price parsing, variant random 
selection, money math). Putting that on a single component breaks SRP; 
putting it in tests creates duplication. Services let each layer keep 
one responsibility.

### Why JSON DB instead of .env

One short paragraph: test scenarios, environment profiles, and demo 
narratives are structured, queryable, and shared across regression 
tests, the data-driven runner, and the simulation script. JSON is the 
right shape. .env stays for secrets (mostly empty here — eBay is public, 
guest only).

### Locator strategy

One short paragraph: role-based locators preferred (get_by_role, 
get_by_label, get_by_test_id). CSS as fallback. XPath only where the 
spec explicitly demands. Cookie banner and geo redirect handled once 
in fixtures, not per-test.

### Extension points

One short paragraph: to add a new flow, document it in atlas/FLOWS.md, 
add the service method (or extend an existing service), add a test or 
a scenario to db/scenarios.json. Components rarely need to change.

## 3. Project Layout

Annotated tree showing top-level structure. Reference only the 
directories and key files; don't enumerate every component.

## 4. Configuration

Two-paragraph section:
- JSON DB in db/ holds environments, scenarios, demos. Loaded via 
  TestDatabase accessor.
- .env (gitignored) for secrets. Profile selected via PROFILE env var 
  (default "dev"). Switches headless mode, trace settings, region.

## 5. Running Tests

Code blocks for: smoke, regression, regression in parallel, single 
test, with trace, with allure report generation.

## 6. Reports

Where allure-results/ and allure-report/ live. The CI workflow uploads 
both as artifacts on every run — link to the latest workflow run in 
the GitHub Actions tab.

Include an embedded screenshot of an Allure report:
  ![Allure report](docs/allure-screenshot.png)
(Note in this same section: "Add docs/allure-screenshot.png after first 
green CI run — generate via `allure serve allure-results` locally and 
screenshot the dashboard.")

## 7. Demo Mode

  uv run python scripts/simulate_usage.py

One paragraph explaining what it does and why it exists (proves 
framework is library-quality; sales/demo runs same components as tests).

## 8. CI

Link to .github/workflows/regression.yml. State: runs on push to main, 
PR to main, and workflow_dispatch. Uploads allure-results, 
allure-report, and reports/ as artifacts on every run, including 
failures (continue-on-error on the test step).

## 9. Assumptions and Limitations

Bullet list:
- Guest authentication only. eBay login is captcha-walled; the assignment 
  explicitly allows Login Stub/Guest. AuthService accepts cookies and 
  pins region.
- USD / US region pinned via cookie at context level. Cross-currency 
  scenarios out of scope.
- eBay structure is volatile. Selectors prefer roles; CSS used only 
  where roles are unavailable; XPath only where the spec demands.
- max_pages_to_paginate cap (default 5) bounds the search-with-price 
  loop to avoid runaway pagination.
- Variant selection is random from available; not exhaustive.
- Auction-only items skipped with warning, not failure (cart-add fails 
  for auctions).

## 10. AI-Assisted Development

Two paragraphs:
- The repo was built using Claude Code with an atlas-driven approach. 
  atlas/ describes the system under test. CLAUDE.md encodes conventions 
  and anti-patterns. ai/prompts/ holds the actual prompts used to 
  generate each layer, in build order.
- Every prompt is a design-by-contract specification: file paths, class 
  names, method signatures, and behavior — implementation left to the 
  tool. The senior judgment lives in the design, not in the typing. 
  ReadMeAIBugs.md applies the same lens to AI-generated code that didn't 
  go through that discipline.

## 11. Bug Review

Link: See ReadMeAIBugs.md.

=== ai/prompts/ ===

Copy the 8 prompts as run, one per file, named:
  01_scaffold.md
  02_atlas_db_infra.md
  03_components.md
  04_services_utilities.md
  05_tests.md
  06_reporting_ci.md
  07_scripts.md
  08_documentation.md

Optional but recommended: add 00_cleanup.md with the scope-reduction 
prompt that was run mid-stream, with a short header noting "Run after 
01-04 to remove over-engineered artifacts; documented for full 
transparency."

Each prompt file should be the prompt exactly as it was sent to Claude 
Code, no editorial.

=== CLAUDE.md ===

Already exists. Do not modify. CLAUDE.md is the AI-session conventions 
doc; README.md is the human-reader doc. They serve different audiences.

=== ReadMeAIBugs.md ===

Already exists from earlier in the session. Do not modify here. The 
user will hand-edit it to adjust voice if needed.

=== Verification ===

1. Render check: 
   - Confirm README.md has no broken markdown (uneven heading levels, 
     missing code fences, dangling links).
   - Confirm every internal link target exists: atlas/, db/, 
     scripts/init_env.sh, scripts/simulate_usage.py, 
     scripts/init_fresh_system.py, ReadMeAIBugs.md, CLAUDE.md, 
     .github/workflows/regression.yml, ai/prompts/.
   - Confirm no references to: ARCHITECTURE.md, ai/conventions.md, 
     populate_scenarios.py, run_regression.sh, retry.py, 
     expectations.json.
2. Print line counts:
   wc -l README.md
3. List ai/prompts/ contents:
   ls -la ai/prompts/
4. Report any placeholder text the user still needs to fill in 
   (USERNAME/REPO in the badge, screenshot path).
