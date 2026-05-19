import re
from decimal import Decimal
from pathlib import Path

from playwright.sync_api import Page

from ebay_automation.components.base import BaseComponent
from ebay_automation.utils.price_parser import parse_price


class CartPage(BaseComponent):
    """Shopping cart page (``/cart``)."""

    URL_PATH = "/cart"
    _SEL_SUBTOTAL_TEXT = re.compile(r"^Subtotal", re.I)
    _SEL_LINE_ITEM_CSS = (
        "[data-testid='cart-item'], li.cart-item, [data-listitemid]"
    )

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def navigate(self) -> None:
        self.page.goto(self.URL_PATH)

    def open(self) -> None:
        self.navigate()

    def subtotal(self) -> Decimal:
        text = self.page.get_by_text(self._SEL_SUBTOTAL_TEXT).first.inner_text()
        return parse_price(text)

    def items_count(self) -> int:
        return self.locator(self._SEL_LINE_ITEM_CSS).count()

    def screenshot_cart(self) -> Path:
        return self.screenshot("cart")
