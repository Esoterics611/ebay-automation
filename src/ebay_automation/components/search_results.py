from decimal import Decimal
from urllib.parse import urlencode

from playwright.sync_api import Locator, Page

from ebay_automation.components.base import BaseComponent
from ebay_automation.components.filter_panel import FilterPanelComponent
from ebay_automation.components.result_card import ResultCardComponent


class SearchResultsPage(BaseComponent):
    """Search results page. URL pattern documented in atlas/PAGES.md."""

    URL_PATH = "/sch/i.html"
    # eBay's 2024 SRP rewrite renamed the result-card container and item
    # classes from .s-item to .s-card; the wrapping <ul> is now
    # .srp-river-results (no id).
    _SEL_CARDS_CSS = ".srp-river-results li.s-card"
    _SEL_NEXT_PAGE_NAME = "Next page"
    # The assignment brief asks to retrieve items "using XPath". Role/CSS
    # locators are this suite's default (atlas/SELECTORS.md) because they
    # survive cosmetic refactors; XPath is reserved for exactly this
    # spec-mandated case. `//` is the descendant axis; each predicate
    # `[contains(@class, '...')]` filters by class without binding to
    # element position (no `li[2]`-style ordinal traversal, which eBay
    # shuffles per visitor).
    _SEL_CARD_LINKS_XPATH = (
        "//*[contains(@class, 'srp-river-results')]"
        "//li[contains(@class, 's-card')]"
        "//a[contains(@class, 's-card__link')]"
    )

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

    def card_links_via_xpath(self) -> list[str]:
        """Return result-card item URLs collected via an explicit XPath
        expression, satisfying the brief's "retrieve using XPath" clause.

        Functionally equivalent to ``get_visible_result_cards`` (which the
        default flow uses), but expressed as XPath to demonstrate the
        positional-traversal locator family. The walrus `:=` keeps only
        cards that actually expose an ``href``.
        """
        links = self.page.locator(f"xpath={self._SEL_CARD_LINKS_XPATH}")
        return [href for i in range(links.count()) if (href := links.nth(i).get_attribute("href"))]

    def apply_price_filter(self, max_price: Decimal) -> None:
        self.filter_panel.apply_price_range(max_value=max_price)

    def has_next_page(self) -> bool:
        return self.page.get_by_role("link", name=self._SEL_NEXT_PAGE_NAME).is_visible()

    def go_to_next_page(self) -> None:
        self.page.get_by_role("link", name=self._SEL_NEXT_PAGE_NAME).click()
