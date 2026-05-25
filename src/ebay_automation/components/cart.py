import re
from decimal import Decimal
from pathlib import Path

from playwright.sync_api import Page

from ebay_automation.components.base import BaseComponent
from ebay_automation.utils.price_parser import parse_price


class CartPage(BaseComponent):
    """Shopping cart page. Lives on the ``cart.ebay.com`` subdomain — the
    legacy ``www.ebay.com/cart`` path 302s to ``pages.ebay.com/cart``
    which then 404s in some regions (notably IL during the 2024+
    shipping pause). The cart subdomain works for guests in all
    regions tested."""

    URL_PATH = "https://cart.ebay.com/"
    _SEL_SUBTOTAL_TEXT = re.compile(r"^Subtotal", re.I)
    _SEL_LINE_ITEM_CSS = "[data-testid='cart-item'], li.cart-item, [data-listitemid]"
    # Safety net: if eBay ever routes us to its error page again
    # (regional block, deprecated route, etc.), this URL substring is
    # the most reliable signal because the error page is otherwise
    # styled like a normal eBay page.
    _ERROR_URL_MARKER = "/n/error"

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def navigate(self) -> None:
        self.page.goto(self.URL_PATH)

    def open(self) -> None:
        self.navigate()

    def is_unavailable(self) -> bool:
        """True when /cart did not actually load a cart — e.g. eBay
        redirected to an error page because guest cart is disabled in
        this region. See README §Assumptions."""
        return self._ERROR_URL_MARKER in self.page.url

    def subtotal(self) -> Decimal:
        text = self.page.get_by_text(self._SEL_SUBTOTAL_TEXT).first.inner_text()
        return parse_price(text)

    def items_count(self) -> int:
        return self.locator(self._SEL_LINE_ITEM_CSS).count()

    def screenshot_cart(self) -> Path:
        return self.screenshot("cart")
