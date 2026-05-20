Implement E2E and data-driven tests. Read atlas/FLOWS.md before writing 
test orchestration; the test bodies should call services per the flow 
documented there.

Context: tests/conftest.py already exists with fixtures (db, page, 
auth_service, search_service, cart_service, variant_service). Use them. 
If a needed fixture is missing or under-specified, ADD it to conftest.py 
rather than working around it in a test.

=== tests/test_smoke.py ===

Two tests, both marked @pytest.mark.smoke:

- test_home_loads(page, db): 
  Navigate to db.environments.get(profile).base_url, accept cookies via 
  cookie_banner component, assert the header's search input is visible.

- test_search_returns_results(page, db): 
  Use HomePage component to load + search for "shoes". Assert that 
  search_results.get_visible_result_cards() returns at least 1 card.
  Use expect() for all waits. No assertion on count beyond > 0; eBay 
  inventory shifts.

=== tests/test_search_under_price.py ===

One test, marked @pytest.mark.regression:

- test_full_e2e_search_add_assert(auth_service, search_service, 
  cart_service):
  Allure step labels: SEARCH, ADD_TO_CART, ASSERT_TOTAL.
  
  1. auth_service.start_guest_session() — Allure step "SETUP_GUEST".
  2. Inside Allure step "SEARCH": 
     urls = search_service.search_items_by_name_under_price(
         "shoes", Decimal("220"), 5)
     Allure attach: search-results screenshot from ScreenshotManager.
     Assert len(urls) > 0.
  3. Inside Allure step "ADD_TO_CART":
     cart_service.add_items_to_cart(urls)
     Per-item screenshots are attached by the service itself (already 
     implemented in Prompt 4); no extra attachment work here.
  4. Inside Allure step "ASSERT_TOTAL":
     cart_service.assert_cart_total_not_exceeds(Decimal("220"), len(urls))
     Allure attach: cart screenshot from ScreenshotManager.
  
  Playwright trace attachment is handled by conftest on retry — do NOT 
  manually start/stop tracing in the test.

=== tests/test_data_driven.py ===

Parametrized from db.scenarios.where(tag="regression") via 
pytest_generate_tests hook.

In tests/conftest.py (or test_data_driven.py local conftest if cleaner):

  def pytest_generate_tests(metafunc):
      if "scenario" in metafunc.fixturenames:
          db = TestDatabase(Path("db"))
          scenarios = db.scenarios.where(tag="regression")
          metafunc.parametrize("scenario", scenarios, 
                               ids=lambda s: s.id)

Test body, marked @pytest.mark.regression:

- test_scenario(scenario, auth_service, search_service, cart_service):
  Same SEARCH → ADD → ASSERT flow as test_search_under_price.py, but 
  parameters come from scenario:
    urls = search_service.search_items_by_name_under_price(
        scenario.query, scenario.max_price, scenario.limit)
  
  Partial-result handling per scenario.allow_partial:
    - If allow_partial is False AND len(urls) < scenario.limit, fail 
      with a clear AssertionError including scenario.id, scenario.limit, 
      and len(urls).
    - If allow_partial is True, log a warning via the standard logger 
      and proceed with what was found, even if 0 (skip ADD_TO_CART and 
      ASSERT_TOTAL if 0 — there's nothing to add or assert).
  
  Minimum result check:
    - assert len(urls) >= scenario.min_results, with descriptive message.
  
  Then proceed with add and assert as usual when len(urls) > 0.

=== tests/unit/test_price_parser.py ===

Already exists from Prompt 4. Do not modify.

=== Verification ===

1. uv run pytest tests/unit -v → must remain green (22 passing).
2. uv run pytest -m smoke -v → must collect 2 tests; do not require 
   them to pass yet (network/site shape can vary; we'll verify in CI).
3. uv run pytest --collect-only -m regression → must show one E2E test 
   from test_search_under_price.py plus one parametrized test per 
   regression-tagged scenario from db/scenarios.json. Report the 
   collected count.

Do NOT run the full regression suite as part of verification — that 
hits live eBay and takes minutes. Collection-only check is sufficient.
