import pytest
from playwright.sync_api import Page, expect

from ebay_automation.components.cookie_banner import CookieBannerComponent
from ebay_automation.components.header import HeaderComponent
from ebay_automation.components.home import HomePage
from ebay_automation.components.search_results import SearchResultsPage
from ebay_automation.db.client import TestDatabase


@pytest.mark.smoke
def test_home_loads(page: Page, db: TestDatabase, profile: str) -> None:
    env = db.environments.get(profile)
    page.goto(env.base_url)
    CookieBannerComponent(page).accept()
    header = HeaderComponent(page)
    expect(header.search_input).to_be_visible()


@pytest.mark.smoke
def test_search_returns_results(page: Page, db: TestDatabase) -> None:
    home = HomePage(page)
    home.load()
    home.cookie_banner.accept()
    home.header.search("shoes")
    results = SearchResultsPage(page)
    expect(results.cards.first).to_be_visible()
    assert len(results.get_visible_result_cards()) > 0
