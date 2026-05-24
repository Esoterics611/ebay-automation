from decimal import Decimal

import allure
import pytest

from ebay_automation.services.auth import AuthService
from ebay_automation.services.cart import CartService
from ebay_automation.services.search import SearchService
from ebay_automation.utils.screenshot import ScreenshotManager


@pytest.mark.regression
def test_full_e2e_search_add_assert(
    auth_service: AuthService,
    search_service: SearchService,
    cart_service: CartService,
    screenshots: ScreenshotManager,
) -> None:
    with allure.step("SETUP_GUEST"):
        auth_service.start_guest_session()

    with allure.step("SEARCH"):
        urls = search_service.search_items_by_name_under_price("shoes", Decimal("640"), 5)
        path = screenshots.capture("search-results")
        allure.attach.file(
            str(path),
            name="search-results",
            attachment_type=allure.attachment_type.PNG,
        )
        assert len(urls) > 0

    with allure.step("ADD_TO_CART"):
        cart_service.add_items_to_cart(urls)

    with allure.step("ASSERT_TOTAL"):
        cart_service.assert_cart_total_not_exceeds(Decimal("640"), len(urls))
        path = screenshots.capture("cart")
        allure.attach.file(
            str(path),
            name="cart",
            attachment_type=allure.attachment_type.PNG,
        )
