from playwright.sync_api import Page

from ebay_automation.utils.logger import get_logger


class BaseService:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.log = get_logger(self.__class__.__name__)
