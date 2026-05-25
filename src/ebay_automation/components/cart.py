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
    # eBay's Akamai layer occasionally gates /cart behind an hCaptcha
    # ("Please verify yourself to continue"). The cart page never
    # renders, so subtotal selectors time out generically — detect the
    # gate explicitly so tests can skip with a clear reason instead.
    _CAPTCHA_TEXT = re.compile(r"verify yourself", re.I)

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def navigate(self) -> None:
        self.page.goto(self.URL_PATH)

    def open(self) -> None:
        self.navigate()

    def is_unavailable(self) -> bool:
        """True when /cart did not actually load a cart — e.g. eBay
        redirected to an error page because guest cart is disabled in
        this region, or the Akamai layer served an hCaptcha gate.
        See README §Assumptions."""
        if self._ERROR_URL_MARKER in self.page.url:
            return True
        return self.page.get_by_text(self._CAPTCHA_TEXT).count() > 0

    def subtotal(self) -> Decimal:
        # eBay's Order summary places "Subtotal" and the price in sibling
        # elements; get_by_text("Subtotal") resolves to the label-only
        # leaf whose inner_text drops the digits. Climb the nearest
        # ancestors until we find one whose text contains a digit — the
        # row that wraps both label and price.
        label = self.page.get_by_text(self._SEL_SUBTOTAL_TEXT).first
        current = label
        for _ in range(4):
            current = current.locator("xpath=..")
            text = current.inner_text()
            if re.search(r"\d", text):
                return parse_price(text)
        raise ValueError(
            "subtotal price not found within 4 ancestors of the "
            f"'Subtotal' label; label text: {label.inner_text()!r}"
        )

    def items_count(self) -> int:
        return self.locator(self._SEL_LINE_ITEM_CSS).count()

    def screenshot_cart(self) -> Path:
        return self.screenshot("cart")
