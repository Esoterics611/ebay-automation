from playwright.sync_api import Page

from ebay_automation.components.base import BaseComponent
from ebay_automation.components.cookie_banner import CookieBannerComponent
from ebay_automation.components.header import HeaderComponent


class HomePage(BaseComponent):
    """eBay home page. Search is performed via the embedded header
    sub-component (``self.header``)."""

    URL_PATH = "/"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.header = HeaderComponent(page)
        self.cookie_banner = CookieBannerComponent(page)

    def navigate(self) -> None:
        self.page.goto(self.URL_PATH)

    def load(self) -> None:
        self.navigate()
