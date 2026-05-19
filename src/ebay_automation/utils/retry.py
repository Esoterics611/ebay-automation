import functools
from typing import Callable, TypeVar, overload

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ebay_automation.utils.logger import get_logger

T = TypeVar("T")

_LOG = get_logger("retry")


@overload
def retry_on_stale(fn: Callable[..., T]) -> Callable[..., T]: ...
@overload
def retry_on_stale(*, max_attempts: int = 3) -> Callable[[Callable[..., T]], Callable[..., T]]: ...


def retry_on_stale(fn: Callable[..., T] | None = None, *, max_attempts: int = 3):
    """Retry a Playwright-driven function when the DOM re-renders under
    it. Catches ``playwright.sync_api.Error`` (stale / detached locators,
    transient page-load races) and retries up to ``max_attempts`` times.
    ``TimeoutError`` is not retried — it indicates a genuine wait
    failure, not a stale element.

    Usable in either form::

        @retry_on_stale
        def foo(...): ...

        @retry_on_stale(max_attempts=5)
        def bar(...): ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exc: PlaywrightError | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except PlaywrightTimeoutError:
                    raise
                except PlaywrightError as exc:
                    last_exc = exc
                    _LOG.warning(
                        "retry_on_stale: attempt %d/%d failed for %s: %s",
                        attempt,
                        max_attempts,
                        func.__qualname__,
                        exc,
                    )
            assert last_exc is not None
            raise last_exc

        return wrapper

    if fn is None:
        return decorator
    return decorator(fn)
