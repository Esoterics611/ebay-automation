from decimal import Decimal

from playwright.sync_api import BrowserContext, Page

from ebay_automation.components.cart import CartPage
from ebay_automation.components.item import ItemPage
from ebay_automation.services.base import BaseService
from ebay_automation.services.variants import VariantService


class CartUnavailableError(RuntimeError):
    """Raised when the ``/cart`` page does not load (HTTP 404 / redirect
    to ``/n/error``) — observed for guests in IL during the eBay
    shipping-pause. Note: the cart *data* still exists (the header
    mini-cart dropdown shows added items); only the full-page cart at
    ``/cart`` is blocked. The subtotal assertion reads from
    ``/cart``, so it cannot run in this state. Tests convert this to
    ``pytest.skip``; the add-to-cart flow is exercised in full. See
    README §Assumptions."""


class CartService(BaseService):
    """Per-URL add-to-cart driver and cart-subtotal assertion."""

    def __init__(
        self,
        page: Page,
        context: BrowserContext,
        variant_service: VariantService,
    ) -> None:
        super().__init__(page)
        self.context = context
        self.variant_service = variant_service
        self._cart = CartPage(page)

    def add_items_to_cart(self, urls: list[str]) -> None:
        """Open each URL in a new tab; if variants are required, defer to
        the variant service; click Add to Cart; capture a screenshot;
        close the tab. Auction-only listings are logged and skipped — the
        caller decides what to do with a partial result."""
        for url in urls:
            tab = self.context.new_page()
            try:
                tab.goto(url)
                item = ItemPage(tab)
                if not item.is_buy_it_now():
                    self.log.warning("cart: skipping auction-only listing: %s", url)
                    continue
                if item.required_variant_selects():
                    self.variant_service.pick_random_variants(item)
                item.add_to_cart()
                screenshot_path = item.screenshot("added-to-cart")
                self.log.info("cart: added %s (screenshot=%s)", url, screenshot_path)
            finally:
                tab.close()

    def assert_cart_total_not_exceeds(
        self,
        budget_per_item: Decimal,
        items_count: int,
    ) -> None:
        """Open the cart, capture state, parse the subtotal as Decimal,
        and assert it is ``<= budget_per_item * items_count``. Raises
        ``CartUnavailableError`` if the cart navigation lands on
        eBay's ``/n/error`` route (safety net for regional blocks or
        deprecated URL routing), or ``AssertionError`` with a
        structured message when the subtotal exceeds budget."""
        self._cart.open()
        if self._cart.is_unavailable():
            raise CartUnavailableError(
                f"/cart page returned 404 (landed on {self.page.url!r}); "
                f"items remain in the header mini-cart dropdown — only "
                f"the full-page cart is blocked, observed for IL guests "
                f"during the shipping pause. See README §Assumptions."
            )
        screenshot_path = self._cart.screenshot_cart()
        subtotal = self._cart.subtotal()
        # Second screenshot at the moment the subtotal was parsed. Lets a
        # later failure investigation read the exact page state that
        # produced the asserted Decimal — without it, a flake in
        # subtotal parsing has only the post-assertion screenshot to
        # work from, which can show a different drawer/modal state.
        self._cart.screenshot("subtotal-read")
        budget = budget_per_item * items_count
        self.log.info(
            "cart: subtotal=%s budget=%s (%s × %d) screenshot=%s",
            subtotal,
            budget,
            budget_per_item,
            items_count,
            screenshot_path,
        )
        if subtotal > budget:
            raise AssertionError(
                "cart subtotal exceeds budget\n"
                f"  budget_per_item : {budget_per_item}\n"
                f"  items_count     : {items_count}\n"
                f"  expected_max    : {budget_per_item} × {items_count} = {budget}\n"
                f"  actual_subtotal : {subtotal}\n"
                f"  over_by         : {subtotal - budget}"
            )
