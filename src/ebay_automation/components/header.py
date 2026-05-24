import re

from playwright.sync_api import Locator, Page

from ebay_automation.components.base import BaseComponent


class HeaderComponent(BaseComponent):
    """Global navigation bar: search entry, cart icon, region indicator."""

    _SEL_SEARCH_INPUT_NAME = "Search for anything"
    _SEL_SEARCH_SUBMIT_NAME = "Search"
    _SEL_CART_NAME = re.compile(r"^Cart")
    # eBay marks the country indicator with the gh-flag class in the
    # global header; fall back to a data-testid where the new header
    # variant exposes one.
    _SEL_REGION_CSS = ".gh-flag, [data-testid='region-indicator']"

    def __init__(self, page: Page, root: Locator | None = None) -> None:
        super().__init__(page, root if root is not None else page.get_by_role("banner"))

    @property
    def search_input(self) -> Locator:
        return self.root.get_by_role("combobox", name=self._SEL_SEARCH_INPUT_NAME)

    def search(self, query: str) -> None:
        self.search_input.fill(query)
        # exact=True so "Search" does not also match the "Clear search"
        # button that appears once the input has text.
        self.root.get_by_role(
            "button", name=self._SEL_SEARCH_SUBMIT_NAME, exact=True
        ).click()

    def open_cart(self) -> None:
        self.root.get_by_role("link", name=self._SEL_CART_NAME).first.click()

    def region_text(self) -> str:
        indicator = self.locator(self._SEL_REGION_CSS).first
        if indicator.count() == 0:
            return ""
        return indicator.inner_text().strip()
