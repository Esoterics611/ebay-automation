import re

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ebay_automation.components.base import BaseComponent

_PROBE_TIMEOUT_MS = 2000


class CookieBannerComponent(BaseComponent):
    """Detects and dismisses the consent banner. Idempotent: ``accept()`` is
    a no-op when no banner is present."""

    _SEL_ACCEPT_NAME = re.compile(r"^Accept(?:\s+all)?$", re.I)

    def __init__(self, page: Page, root: Locator | None = None) -> None:
        super().__init__(page, root)

    def _accept_button(self) -> Locator:
        return self.root.get_by_role("button", name=self._SEL_ACCEPT_NAME).first

    def is_visible(self) -> bool:
        try:
            self._accept_button().wait_for(state="visible", timeout=_PROBE_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            return False
        return True

    def accept(self) -> None:
        if self.is_visible():
            self._accept_button().click()
