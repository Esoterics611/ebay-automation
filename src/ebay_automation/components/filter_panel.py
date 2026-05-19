import re
from decimal import Decimal

from playwright.sync_api import Locator, Page

from ebay_automation.components.base import BaseComponent


class FilterPanelComponent(BaseComponent):
    """Sidebar filter panel on the search-results page."""

    # eBay surfaces the min/max inputs with these accessible labels.
    _SEL_MIN_PRICE_LABEL = re.compile(r"Minimum Value", re.I)
    _SEL_MAX_PRICE_LABEL = re.compile(r"Maximum Value", re.I)
    _SEL_APPLY_PRICE_NAME = re.compile(r"Submit price range", re.I)
    _SEL_BUY_IT_NOW_NAME = re.compile(r"^Buy It Now$", re.I)
    _SEL_SORT_TRIGGER_NAME = re.compile(r"^Sort:", re.I)
    _SEL_SORT_LOWEST_OPTION_NAME = re.compile(
        r"Price\s*\+\s*Shipping:\s*lowest first", re.I
    )

    def __init__(self, page: Page, root: Locator | None = None) -> None:
        # When the caller doesn't scope us explicitly, fall back to the
        # main results region — the filter chips and price box live there.
        if root is None:
            root = page.locator("#srp-river-main, main").first
        super().__init__(page, root)

    def apply_price_range(
        self,
        min_value: Decimal | None = None,
        max_value: Decimal | None = None,
    ) -> None:
        if min_value is not None:
            self.root.get_by_label(self._SEL_MIN_PRICE_LABEL).fill(str(min_value))
        if max_value is not None:
            self.root.get_by_label(self._SEL_MAX_PRICE_LABEL).fill(str(max_value))
        self.root.get_by_role("button", name=self._SEL_APPLY_PRICE_NAME).click()

    def apply_buy_it_now(self) -> None:
        self.root.get_by_role("link", name=self._SEL_BUY_IT_NOW_NAME).click()

    def sort_by_price_plus_shipping_lowest(self) -> None:
        self.root.get_by_role("button", name=self._SEL_SORT_TRIGGER_NAME).click()
        # The opened menu portals to the page root, outside the filter
        # panel's locator scope — query it from page.
        self.page.get_by_role(
            "menuitem", name=self._SEL_SORT_LOWEST_OPTION_NAME
        ).click()
