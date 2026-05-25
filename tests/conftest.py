import os
import sys
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv
from playwright.sync_api import BrowserContext, Page

from ebay_automation.db.client import TestDatabase
from ebay_automation.db.models import Environment
from ebay_automation.services.auth import AuthService
from ebay_automation.services.cart import CartService
from ebay_automation.services.search import SearchService
from ebay_automation.services.variants import VariantService
from ebay_automation.utils.logger import get_logger
from ebay_automation.utils.screenshot import ScreenshotManager

load_dotenv()

_LOG = get_logger("conftest")
_ROOT = Path(__file__).resolve().parent.parent
_DB_PATH = _ROOT / "db"
_ALLURE_RESULTS = _ROOT / "allure-results"


# ---------- session-scoped config (browser-free) ----------


@pytest.fixture(scope="session")
def profile() -> str:
    return os.getenv("PROFILE", "dev")


@pytest.fixture(scope="session")
def db() -> TestDatabase:
    return TestDatabase(_DB_PATH)


@pytest.fixture(scope="session")
def env(db: TestDatabase, profile: str) -> Environment:
    return db.environments.get(profile)


@pytest.fixture(scope="session")
def base_url(env: Environment) -> str:
    return env.base_url


# ---------- playwright launch / context overrides ----------


# Chromium launch args that reduce automation fingerprinting against
# bot-aware sites (eBay's Akamai layer). These are well-known, non-
# deceptive measures — they remove signals that Chromium volunteers
# *only* when driven by automation tools, not signals that lie about
# what the browser is. Without these, PROFILE=ci is challenged by an
# Akamai interstitial ("Checking your browser…") and Locator.fill
# times out on the search box. See README §Assumptions.
_ANTI_DETECTION_ARGS = [
    "--disable-blink-features=AutomationControlled",
]
# A real Chrome user-agent. The default Playwright UA in headless
# mode includes "HeadlessChrome", which Akamai flags immediately.
_CHROME_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


@pytest.fixture(scope="session")
def browser_type_launch_args(
    browser_type_launch_args: dict[str, Any], env: Environment
) -> dict[str, Any]:
    existing_args = list(browser_type_launch_args.get("args", []))
    return {
        **browser_type_launch_args,
        "headless": env.headless,
        "slow_mo": env.slow_mo_ms,
        "args": existing_args + _ANTI_DETECTION_ARGS,
    }


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any], env: Environment) -> dict[str, Any]:
    # Tracing, video and screenshot capture are driven by pytest-playwright
    # CLI flags (see pyproject [tool.pytest.ini_options] addopts) — do not
    # reimplement context-level tracing.start here.
    return {
        **browser_context_args,
        "base_url": env.base_url,
        "locale": f"en-{env.region}",
        "viewport": {"width": 1440, "height": 900},
        "user_agent": _CHROME_UA,
    }


# ---------- allure environment.properties (session-scoped, autouse) ----------


@pytest.fixture(scope="session", autouse=True)
def _allure_environment(env: Environment, profile: str) -> None:
    """Write ``allure-results/environment.properties`` so the Allure
    report's Environment panel shows the run profile, base URL, region
    and component versions."""
    _ALLURE_RESULTS.mkdir(parents=True, exist_ok=True)
    py_ver = ".".join(str(p) for p in sys.version_info[:3])
    try:
        pw_ver = _pkg_version("playwright")
    except Exception:  # noqa: BLE001 — best-effort version probe
        pw_ver = "unknown"
    lines = [
        f"python.version={py_ver}",
        f"playwright.version={pw_ver}",
        f"profile={profile}",
        f"base_url={env.base_url}",
        f"region={env.region}",
        f"headless={env.headless}",
    ]
    (_ALLURE_RESULTS / "environment.properties").write_text("\n".join(lines) + "\n")


# ---------- per-test setup ----------
#
# Autouse fixtures are gated on ``request.fixturenames`` so that unit
# tests under ``tests/unit/`` — which never request ``page`` or
# ``context`` — do not pay the cost of launching a browser.


def _uses_browser(request: pytest.FixtureRequest) -> bool:
    names = request.fixturenames
    return "page" in names or "context" in names


@pytest.fixture(autouse=True)
def _set_region_cookies(request: pytest.FixtureRequest, env: Environment):
    if not _uses_browser(request):
        yield
        return
    context: BrowserContext = request.getfixturevalue("context")
    context.add_cookies(
        [
            {
                "name": "ebay_region",
                "value": env.region,
                "domain": ".ebay.com",
                "path": "/",
            },
            {
                "name": "ebay_currency",
                "value": env.currency,
                "domain": ".ebay.com",
                "path": "/",
            },
        ]
    )
    yield


@pytest.fixture
def screenshots(page: Page, request: pytest.FixtureRequest) -> ScreenshotManager:
    return ScreenshotManager(page, test_id=_safe_id(request.node.nodeid))


# ---------- services (constructor injection from fixtures) ----------


@pytest.fixture
def variant_service(page: Page) -> VariantService:
    return VariantService(page)


@pytest.fixture
def auth_service(page: Page, context: BrowserContext, env: Environment) -> AuthService:
    return AuthService(page, context, env)


@pytest.fixture
def search_service(page: Page, env: Environment) -> SearchService:
    return SearchService(page, env)


@pytest.fixture
def cart_service(
    page: Page,
    context: BrowserContext,
    variant_service: VariantService,
) -> CartService:
    return CartService(page, context, variant_service)


# ---------- data-driven scenarios ----------


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "scenario" in metafunc.fixturenames:
        db = TestDatabase(_DB_PATH)
        scenarios = db.scenarios.where(tag="regression")
        metafunc.parametrize("scenario", scenarios, ids=lambda s: s.id)


# ---------- hooks ----------


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


def _safe_id(node_id: str) -> str:
    return (
        node_id.replace("/", "_")
        .replace("::", "__")
        .replace(" ", "_")
        .replace("[", "_")
        .replace("]", "_")
    )
