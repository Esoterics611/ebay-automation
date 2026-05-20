"""Headed demo of the eBay automation services outside pytest.

Loads every demo scenario from db/demo_scenarios.json and runs the same
search → add-to-cart → subtotal-assert flow the regression suite uses,
proving the components/services are reusable without pytest fixtures."""
import subprocess
from pathlib import Path

import allure
from playwright.sync_api import sync_playwright

from ebay_automation.db.client import TestDatabase
from ebay_automation.services.cart import CartService
from ebay_automation.services.search import SearchService
from ebay_automation.services.variants import VariantService

_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    db = TestDatabase(_ROOT / "db")
    env = db.environments.get("dev")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=env.headless, slow_mo=env.slow_mo_ms)
        context = browser.new_context(
            base_url=env.base_url, locale=f"en-{env.region}",
            viewport={"width": 1440, "height": 900},
        )
        context.add_cookies([
            {"name": "ebay_region", "value": env.region, "domain": ".ebay.com", "path": "/"},
            {"name": "ebay_currency", "value": env.currency, "domain": ".ebay.com", "path": "/"},
        ])
        page = context.new_page()
        variants = VariantService(page)
        search = SearchService(page, env)
        cart = CartService(page, context, variants)
        for demo in db.demos.all():
            print(f"\n=== {demo.id}: {demo.narrative}")
            with allure.step(demo.id):
                urls = search.search_items_by_name_under_price(
                    demo.query, demo.max_price, demo.limit
                )
                if not urls:
                    print(f"  no urls; skipping {demo.id}")
                    continue
                cart.add_items_to_cart(urls)
                cart.assert_cart_total_not_exceeds(demo.max_price, len(urls))
        context.close()
        browser.close()
    subprocess.run(
        ["allure", "generate", "allure-results", "--clean", "-o", "allure-report"],
        check=False,
    )
    print(f"\nDemo report: file://{_ROOT / 'allure-report' / 'index.html'}")
    print("Or: uv run allure serve allure-results")


if __name__ == "__main__":
    main()
