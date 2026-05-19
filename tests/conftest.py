import os
from dataclasses import dataclass
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


@dataclass
class Services:
    auth: AuthService
    search: SearchService
    cart: CartService
    variants: VariantService


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

@pytest.fixture(scope="session")
def browser_type_launch_args(
    browser_type_launch_args: dict[str, Any], env: Environment
) -> dict[str, Any]:
    return {
        **browser_type_launch_args,
        "headless": env.headless,
        "slow_mo": env.slow_mo_ms,
    }


@pytest.fixture(scope="session")
def browser_context_args(
    browser_context_args: dict[str, Any], env: Environment
) -> dict[str, Any]:
    args: dict[str, Any] = {
        **browser_context_args,
        "locale": f"en-{env.region}",
        "viewport": {"width": 1440, "height": 900},
    }
    if env.video != "off":
        args["record_video_dir"] = str(_ROOT / "reports" / "videos")
    return args


# ---------- per-test setup ----------
#
# These autouse fixtures are gated on ``request.fixturenames`` so that
# unit tests under ``tests/unit/`` — which never request ``page`` or
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


@pytest.fixture(autouse=True)
def _tracing(request: pytest.FixtureRequest, env: Environment):
    if not _uses_browser(request) or env.trace == "off":
        yield
        return
    context: BrowserContext = request.getfixturevalue("context")
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    try:
        yield
    finally:
        failed = bool(
            getattr(request.node, "rep_call", None)
            and request.node.rep_call.failed
        )
        keep = env.trace == "on" or (env.trace == "retain-on-failure" and failed)
        if keep:
            out = _ROOT / "reports" / "traces" / f"{_safe_id(request.node.nodeid)}.zip"
            out.parent.mkdir(parents=True, exist_ok=True)
            context.tracing.stop(path=str(out))
        else:
            context.tracing.stop()


@pytest.fixture
def screenshots(page: Page, request: pytest.FixtureRequest) -> ScreenshotManager:
    return ScreenshotManager(page, test_id=_safe_id(request.node.nodeid))


@pytest.fixture(autouse=True)
def _screenshot_on_failure(request: pytest.FixtureRequest, env: Environment):
    if "page" not in request.fixturenames:
        yield
        return
    yield
    failed = bool(
        getattr(request.node, "rep_call", None)
        and request.node.rep_call.failed
    )
    if failed and env.screenshot_on_failure:
        try:
            request.getfixturevalue("screenshots").capture("failure")
        except Exception as exc:  # noqa: BLE001 — best-effort capture
            _LOG.warning("failed to capture failure screenshot: %s", exc)


# ---------- services (constructor injection from fixtures) ----------

@pytest.fixture
def services(page: Page, context: BrowserContext, env: Environment) -> Services:
    variant_service = VariantService(page)
    return Services(
        auth=AuthService(page, context, env),
        search=SearchService(page, env),
        variants=variant_service,
        cart=CartService(page, context, variant_service),
    )


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
