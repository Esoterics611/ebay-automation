from decimal import Decimal
from urllib.parse import urlencode

from playwright.sync_api import Locator, Page

from ebay_automation.components.base import BaseComponent
from ebay_automation.components.filter_panel import FilterPanelComponent
from ebay_automation.components.result_card import ResultCardComponent


class SearchResultsPage(BaseComponent):
    """Search results page. URL pattern documented in atlas/PAGES.md."""

    URL_PATH = "/sch/i.html"
    _SEL_CARDS_CSS = "ul.srp-results > li.s-item"
    _SEL_NEXT_PAGE_NAME = "Next page"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.filter_panel = FilterPanelComponent(page)

    def navigate(self, query: str) -> None:
        qs = urlencode({"_nkw": query})
        self.page.goto(f"{self.URL_PATH}?{qs}")

    @property
    def cards(self) -> Locator:
        return self.page.locator(self._SEL_CARDS_CSS)

    def get_visible_result_cards(self) -> list[ResultCardComponent]:
        cards = self.cards
        # List comprehension is a structural child-factory, not business
        # logic — each card is wrapped as its own typed sub-component.
        return [ResultCardComponent(self.page, cards.nth(i)) for i in range(cards.count())]

    def apply_price_filter(self, max_price: Decimal) -> None:
        self.filter_panel.apply_price_range(max_value=max_price)

    def has_next_page(self) -> bool:
        return self.page.get_by_role("link", name=self._SEL_NEXT_PAGE_NAME).is_visible()

    def go_to_next_page(self) -> None:
        self.page.get_by_role("link", name=self._SEL_NEXT_PAGE_NAME).click()
