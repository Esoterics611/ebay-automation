Three scripts. Two real, one a documented skeleton.

=== scripts/init_env.sh ===

#!/usr/bin/env bash
set -euo pipefail

- Check Python 3.11+ present; if not, print a clear error and exit 1.
- If uv not on PATH, install via curl from astral.sh installer. Add 
  ~/.local/bin to PATH for the current shell.
- Run: uv sync
- Run: uv run playwright install --with-deps chromium
- If .env does not exist, copy .env.example to .env (use cp -n).
- Run: uv run pytest tests/unit -v
  (smoke tests are network-dependent; unit tests are safe locally and 
  prove the install is sane)
- Print final usage block to stdout:
    "Environment ready."
    "Run regression:   PROFILE=ci uv run pytest -m regression -n 4 --alluredir=allure-results"
    "Run simulation:   uv run python scripts/simulate_usage.py"
    "View Allure:      uv run allure serve allure-results"

Make the script idempotent — re-running it on an already-initialized 
repo must succeed without errors.

=== scripts/simulate_usage.py ===

Target: under 60 lines. No CLI flags. Single purpose: prove components 
and services are reusable outside pytest.

Imports services directly from ebay_automation.services.* and the 
TestDatabase from ebay_automation.db.client. Launches Playwright with 
sync_playwright() context manager, profile = "dev" (headed, watchable).

Flow:
1. Load db.demos.all() via TestDatabase.
2. For each demo scenario:
   a. Print the demo's narrative to stdout.
   b. Use allure_commons or allure_pytest's step API to wrap the work 
      in an Allure step named after demo.id.
   c. Call search_service.search_items_by_name_under_price(
        demo.query, demo.max_price, demo.limit).
   d. If any URLs found, call cart_service.add_items_to_cart and 
      assert_cart_total_not_exceeds(demo.max_price, len(urls)).
   e. If 0 URLs, log and skip (parallels the data-driven test's 
      partial-result handling).
3. At end, generate Allure HTML:
   import subprocess
   subprocess.run(["allure", "generate", "allure-results", "--clean", 
                   "-o", "allure-report"], check=False)
   Print: "Demo report: file://<absolute path>/allure-report/index.html"
   Print: "Or: uv run allure serve allure-results"

Important: services were designed to take page + env via constructor 
injection. In this script (no pytest fixtures), construct them 
explicitly:
  with sync_playwright() as p:
      env = TestDatabase("db").environments.get("dev")
      browser = p.chromium.launch(headless=env.headless)
      context = browser.new_context()
      # set region cookie at context level same way conftest does it
      page = context.new_page()
      search_service = SearchService(page, env)
      cart_service = CartService(page, env)
      # ... loop demos
      context.close()
      browser.close()

=== scripts/init_fresh_system.py ===

Target: 15-20 lines including the docstring. The docstring IS the 
deliverable.

#!/usr/bin/env python3
"""Init script for a system we owned.

For a system under our control, this script would seed catalog, users,
and categories using the same services and components used in regression
— same code path, same coverage, no separate "fixture rig" to maintain.

For eBay (public, read-only, guest-only) the seed functions are 
unimplemented; this script only verifies connectivity to the target 
environment. The pattern is here; the seed work happens when we own 
the SUT.
"""

import argparse
import urllib.request
from ebay_automation.db.client import TestDatabase

def verify_connectivity(env) -> bool:
    req = urllib.request.Request(env.base_url, method="HEAD")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return 200 <= resp.status < 400

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default="dev", 
                        help="environment id from db/environments.json")
    args = parser.parse_args()
    env = TestDatabase("db").environments.get(args.env)
    print(f"verifying {env.base_url}...")
    ok = verify_connectivity(env)
    print("OK" if ok else "FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())

=== Verification ===

1. chmod +x scripts/init_env.sh scripts/init_fresh_system.py
2. ./scripts/init_env.sh — must complete successfully (idempotent).
3. uv run python scripts/init_fresh_system.py — must print "OK" (eBay 
   is reachable from this machine; if not, the script's failure mode 
   is the correct behavior).
4. uv run python scripts/simulate_usage.py — do NOT run as part of 
   verification (hits live eBay, takes minutes). Just verify Python 
   syntax with:
   uv run python -c "import ast; ast.parse(open('scripts/simulate_usage.py').read())"
5. Report line counts: 
   wc -l scripts/init_env.sh scripts/simulate_usage.py scripts/init_fresh_system.py
   simulate_usage.py target < 60, init_fresh_system.py target < 25.
