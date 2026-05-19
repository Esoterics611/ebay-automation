import random
import re

from playwright.sync_api import Page

from ebay_automation.components.item import ItemPage
from ebay_automation.services.base import BaseService


class VariantService(BaseService):
    """Resolves required variant pickers on the item detail page."""

    _PLACEHOLDER_PATTERN = re.compile(
        r"^\s*(?:-+|select|choose|please select|--)", re.I
    )
    _OUT_OF_STOCK_PATTERN = re.compile(
        r"(?:out of stock|sold out|unavailable)", re.I
    )

    def __init__(self, page: Page) -> None:
        super().__init__(page)

    def pick_random_variants(self, item: ItemPage) -> None:
        """For each required variant select on the item page, pick a
        random in-stock option. Skips:
          * placeholder labels (``Select…``, ``Choose…``, ``--``),
          * options whose text or ``disabled`` attribute mark them as
            out of stock.

        Logs and continues when a combobox has no in-stock option — the
        caller (cart service) decides whether the item is still usable.
        """
        for combo in item.required_variant_selects():
            in_stock = combo.locator("option:not([disabled])")
            labels = [label.strip() for label in in_stock.all_text_contents()]
            valid = [
                label
                for label in labels
                if label
                and not self._PLACEHOLDER_PATTERN.match(label)
                and not self._OUT_OF_STOCK_PATTERN.search(label)
            ]
            if not valid:
                self.log.warning(
                    "variant: no in-stock option for combobox; skipping"
                )
                continue
            choice = random.choice(valid)
            combo.select_option(label=choice)
            self.log.info("variant: picked %r", choice)
