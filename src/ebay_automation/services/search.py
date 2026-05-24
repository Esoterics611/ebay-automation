from decimal import Decimal

from playwright.sync_api import Page

from ebay_automation.components.home import HomePage
from ebay_automation.components.result_card import ResultCardComponent
from ebay_automation.components.search_results import SearchResultsPage
from ebay_automation.db.models import Environment
from ebay_automation.services.base import BaseService
from ebay_automation.utils.paginator import collect_until
from ebay_automation.utils.price_parser import parse_price


class SearchService(BaseService):
    """Composes the search-and-collect flow documented in atlas/FLOWS.md."""

    def __init__(self, page: Page, env: Environment) -> None:
        super().__init__(page)
        self.env = env
        self._home = HomePage(page)
        self._results = SearchResultsPage(page)

    def search_items_by_name_under_price(
        self,
        query: str,
        max_price: Decimal,
        limit: int = 5,
    ) -> list[str]:
        """Drive the full search flow and return up to ``limit`` item URLs
        whose listed price is ``<= max_price``.

        Steps (per spec):
          1. Load home, search via header.
          2. Apply ``max_price`` filter on results.
          3. Apply "Buy It Now" filter (cart-compatible listings only).
          4. Sort by "Price + Shipping: lowest first".
          5. Paginate, skipping sponsored listings.
          6. Return the URLs (may be fewer than ``limit`` — callers
             handle ``allow_partial`` themselves).
        """
        self.log.info(
            "search start: query=%r max_price=%s limit=%d",
            query,
            max_price,
            limit,
        )

        self._home.load()
        self._home.header.search(query)
        self._results.apply_price_filter(max_price)
        self._results.filter_panel.apply_buy_it_now()
        self._results.filter_panel.sort_by_price_plus_shipping_lowest()

        urls = collect_until(
            component=self._results,
            collect_fn=lambda _: self._collect_card_urls(self._results, max_price),
            target_count=limit,
            env=self.env,
        )
        self.log.info("search done: collected=%d target=%d", len(urls), limit)
        return urls

    def _collect_card_urls(
        self,
        results: SearchResultsPage,
        max_price: Decimal,
    ) -> list[str]:
        """Page-level URL collector — composed by the paginator. Lives
        here (service layer) because the filtering rules (sponsored,
        non-BIN, price > max) are business decisions, not UI mechanics."""
        urls: list[str] = []
        for card in results.get_visible_result_cards():
            url = self._qualify_card(card, max_price)
            if url is not None:
                urls.append(url)
        return urls

    def _qualify_card(
        self,
        card: ResultCardComponent,
        max_price: Decimal,
    ) -> str | None:
        if card.is_sponsored():
            return None
        if card.item_type() != "buy_it_now":
            return None
        try:
            price = parse_price(card.price_text())
        except ValueError:
            self.log.debug("card price unparseable; skipping")
            return None
        if price > max_price:
            return None
        return card.url() or None
