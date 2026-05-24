import re
from decimal import Decimal

from playwright.sync_api import Locator, Page

from ebay_automation.components.base import BaseComponent
from ebay_automation.utils.price_parser import parse_price


class ItemPage(BaseComponent):
    """Single-item detail page (``/itm/<id>``)."""

    URL_PATH = "/itm/"
    _SEL_TITLE_LEVEL = 1
    # Price has no semantic role; the data-testid is the most stable
    # anchor eBay exposes today, with a class fallback.
    _SEL_PRICE_CSS = '[data-testid="x-price-primary"], .x-price-primary'
    _SEL_VARIANT_NAME = re.compile(r"select", re.I)
    _SEL_ADD_TO_CART_NAME = "Add to cart"
    _SEL_BUY_IT_NOW_NAME = "Buy It Now"

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def navigate(self, item_id: str) -> None:
        self.page.goto(f"{self.URL_PATH}{item_id}")

    def title(self) -> str:
        return self.page.get_by_role("heading", level=self._SEL_TITLE_LEVEL).inner_text().strip()

    def price(self) -> Decimal:
        text = self.locator(self._SEL_PRICE_CSS).first.inner_text().strip()
        return parse_price(text)

    def required_variant_selects(self) -> list[Locator]:
        """All variant comboboxes on the page (size, color, …). The list
        is a structural wrapping of children — caller decides which to
        act on."""
        selects = self.page.get_by_role("combobox", name=self._SEL_VARIANT_NAME)
        return [selects.nth(i) for i in range(selects.count())]

    def add_to_cart(self) -> None:
        self.page.get_by_role("button", name=self._SEL_ADD_TO_CART_NAME).click()

    def is_buy_it_now(self) -> bool:
        if self.page.get_by_role("button", name=self._SEL_ADD_TO_CART_NAME).is_visible():
            return True
        return self.page.get_by_role("button", name=self._SEL_BUY_IT_NOW_NAME).is_visible()
