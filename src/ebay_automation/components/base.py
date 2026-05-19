from pathlib import Path

from playwright.sync_api import Locator, Page

from ebay_automation.utils.logger import get_logger
from ebay_automation.utils.screenshot import ScreenshotManager


class BaseComponent:
    def __init__(self, page: Page, root: Locator | None = None) -> None:
        self.page = page
        self.root: Locator = root if root is not None else page.locator("body")
        self.log = get_logger(self.__class__.__name__)
        self.screenshots = ScreenshotManager(page)

    def locator(self, selector: str) -> Locator:
        """Scoped locator factory — resolves within ``self.root``."""
        return self.root.locator(selector)

    def screenshot(self, step: str) -> Path:
        return self.screenshots.capture(step)
