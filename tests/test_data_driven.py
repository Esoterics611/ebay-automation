import allure
import pytest

from ebay_automation.db.models import Scenario
from ebay_automation.services.auth import AuthService
from ebay_automation.services.cart import CartService
from ebay_automation.services.search import SearchService
from ebay_automation.utils.logger import get_logger
from ebay_automation.utils.screenshot import ScreenshotManager

_LOG = get_logger("test_data_driven")


@pytest.mark.regression
def test_scenario(
    scenario: Scenario,
    auth_service: AuthService,
    search_service: SearchService,
    cart_service: CartService,
    screenshots: ScreenshotManager,
) -> None:
    with allure.step(f"SETUP_GUEST [{scenario.id}]"):
        auth_service.start_guest_session()

    with allure.step(f"SEARCH [{scenario.id}]"):
        urls = search_service.search_items_by_name_under_price(
            scenario.query, scenario.max_price, scenario.limit
        )
        path = screenshots.capture("search-results")
        allure.attach.file(
            str(path),
            name="search-results",
            attachment_type=allure.attachment_type.PNG,
        )

    if len(urls) < scenario.limit:
        if not scenario.allow_partial:
            raise AssertionError(
                f"scenario {scenario.id}: expected {scenario.limit} urls "
                f"(allow_partial=False), got {len(urls)}"
            )
        _LOG.warning(
            "scenario %s: collected %d/%d urls; proceeding (allow_partial=True)",
            scenario.id,
            len(urls),
            scenario.limit,
        )

    assert len(urls) >= scenario.min_results, (
        f"scenario {scenario.id}: min_results={scenario.min_results}, " f"got len(urls)={len(urls)}"
    )

    if not urls:
        return

    with allure.step(f"ADD_TO_CART [{scenario.id}]"):
        cart_service.add_items_to_cart(urls)

    with allure.step(f"ASSERT_TOTAL [{scenario.id}]"):
        cart_service.assert_cart_total_not_exceeds(scenario.max_price, len(urls))
        path = screenshots.capture("cart")
        allure.attach.file(
            str(path),
            name="cart",
            attachment_type=allure.attachment_type.PNG,
        )
