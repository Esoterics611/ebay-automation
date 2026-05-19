import re

from playwright.sync_api import Locator, Page

from ebay_automation.components.base import BaseComponent


class ResultCardComponent(BaseComponent):
    """A single result card on the search-results page. Scoped to a card
    root locator (`ul.srp-results > li.s-item`)."""

    _SEL_TITLE_ROLE = "link"
    _SEL_PRICE_CSS = ".s-item__price"
    _SEL_SPONSORED_TEXT = re.compile(r"SPONSORED", re.I)
    _SEL_SPONSORED_ATTR = "[data-listing-status='sponsored']"
    _SEL_AUCTION_INDICATORS = re.compile(
        r"(?:Current bid|Time left|\bbid\b)", re.I
    )

    def __init__(self, page: Page, root: Locator) -> None:
        # Result cards are never page-scoped; root is mandatory.
        super().__init__(page, root)

    def title(self) -> str:
        return self.root.get_by_role(self._SEL_TITLE_ROLE).first.inner_text().strip()

    def price_text(self) -> str:
        return self.locator(self._SEL_PRICE_CSS).first.inner_text().strip()

    def url(self) -> str:
        href = self.root.get_by_role(self._SEL_TITLE_ROLE).first.get_attribute("href")
        return href or ""

    def is_sponsored(self) -> bool:
        if self.root.get_by_text(self._SEL_SPONSORED_TEXT).count() > 0:
            return True
        return self.locator(self._SEL_SPONSORED_ATTR).count() > 0

    def item_type(self) -> str:
        """Returns one of: ``"auction"``, ``"buy_it_now"``.

        Auctions are identified by "Current bid" / "Time left" / "bid"
        copy on the card. Anything else is treated as a fixed-price /
        Buy-It-Now listing — the only kind addable to cart.
        """
        if self.root.get_by_text(self._SEL_AUCTION_INDICATORS).count() > 0:
            return "auction"
        return "buy_it_now"
