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
    _SEL_BUY_IT_NOW_NAME = "Buy It Now"
    # The current SRP renders the sort trigger with an accessible name of
    # just "Sort"; "Sort: Best Match" is its *value*, not its name.
    _SEL_SORT_TRIGGER_NAME = "Sort"
    _SEL_SORT_LOWEST_OPTION_NAME = re.compile(r"Price\s*\+\s*Shipping:\s*lowest first", re.I)

    def __init__(self, page: Page, root: Locator | None = None) -> None:
        # The filter rail lives at the page level — there is no stable
        # container id to scope to (the old #srp-river-main was removed
        # in eBay's 2024 SRP rewrite). Default to the page body via
        # BaseComponent so role/label queries resolve globally.
        super().__init__(page, root)

    def apply_price_range(
        self,
        min_value: Decimal | None = None,
        max_value: Decimal | None = None,
    ) -> None:
        if min_value is not None:
            self.root.get_by_label(self._SEL_MIN_PRICE_LABEL).fill(str(min_value))
        if max_value is not None:
            max_input = self.root.get_by_label(self._SEL_MAX_PRICE_LABEL)
            max_input.fill(str(max_value))
            # eBay's "Submit price range" button stays disabled after a
            # programmatic .fill() — the framework only enables it on a
            # real keydown sequence. Press Enter to submit the range form
            # directly; clicking the button is unreachable from automation.
            max_input.press("Enter")
            self._wait_for_results_reload()
            return
        self.root.get_by_role("button", name=self._SEL_APPLY_PRICE_NAME).click()
        self._wait_for_results_reload()

    def apply_buy_it_now(self) -> None:
        # exact=True avoids the count-suffixed sibling chip
        # ("Buy It Now (11,821,659) Items") in the buying-format section.
        self.root.get_by_role("link", name=self._SEL_BUY_IT_NOW_NAME, exact=True).first.click()
        self._wait_for_results_reload()

    def sort_by_price_plus_shipping_lowest(self) -> None:
        self.root.get_by_role("button", name=self._SEL_SORT_TRIGGER_NAME, exact=True).click()
        # The opened menu portals to the page root, outside the filter
        # panel's locator scope. Options are anchor links (role=link),
        # not menuitems — confirmed against current SRP markup.
        self.page.get_by_role("link", name=self._SEL_SORT_LOWEST_OPTION_NAME).first.click()
        self._wait_for_results_reload()

    def _wait_for_results_reload(self) -> None:
        """Every filter action triggers a full SRP navigation. Without an
        explicit wait, callers that immediately read ``cards.count()``
        race the navigation and see 0 on a mid-load DOM snapshot
        (Playwright sync ``.count()`` does not auto-wait). DOM-ready is
        sufficient — the cards container is in the initial HTML."""
        self.page.wait_for_load_state("domcontentloaded")
