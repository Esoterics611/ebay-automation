from playwright.sync_api import BrowserContext, Page

from ebay_automation.components.cookie_banner import CookieBannerComponent
from ebay_automation.components.home import HomePage
from ebay_automation.db.models import Environment
from ebay_automation.services.base import BaseService


class AuthService(BaseService):
    """Guest-only session management.

    eBay's real sign-in flow is intentionally **not** automated:

    * The live login page gates automated browsers behind FunCaptcha /
      hCaptcha — solving these reliably in CI is a moving target and
      adds external dependencies.
    * eBay rate-limits login attempts per IP; a flaky CI run would burn
      that budget for the team.
    * Storing real credentials in the suite would create a secrets-
      handling burden out of proportion with what we actually need to
      test — every flow in scope (search, item detail, add-to-cart,
      cart subtotal) is fully reachable by guests.

    ``start_guest_session`` is therefore the only entry point: it
    pre-loads the region/currency cookies, lands on the home page, and
    dismisses the consent banner before any test code runs.
    """

    def __init__(
        self,
        page: Page,
        context: BrowserContext,
        env: Environment,
    ) -> None:
        super().__init__(page)
        self.context = context
        self.env = env
        self._home = HomePage(page)
        self._cookie_banner = CookieBannerComponent(page)

    def start_guest_session(self) -> None:
        self.context.add_cookies(
            [
                {
                    "name": "ebay_region",
                    "value": self.env.region,
                    "domain": ".ebay.com",
                    "path": "/",
                },
                {
                    "name": "ebay_currency",
                    "value": self.env.currency,
                    "domain": ".ebay.com",
                    "path": "/",
                },
            ]
        )
        self.log.info(
            "guest session: region=%s currency=%s",
            self.env.region,
            self.env.currency,
        )
        self._home.load()
        self._cookie_banner.accept()
