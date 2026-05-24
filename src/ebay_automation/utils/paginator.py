from typing import Callable, Protocol, TypeVar

from ebay_automation.db.models import Environment
from ebay_automation.utils.logger import get_logger

T = TypeVar("T")

_LOG = get_logger("paginator")


class _Pageable(Protocol):
    def has_next_page(self) -> bool: ...
    def go_to_next_page(self) -> None: ...


def collect_until(
    component: _Pageable,
    collect_fn: Callable[[_Pageable], list[T]],
    target_count: int,
    max_pages: int | None = None,
    *,
    env: Environment | None = None,
) -> list[T]:
    """Paginate-and-accumulate from any component that exposes
    ``has_next_page()`` and ``go_to_next_page()`` (e.g. ``SearchResultsPage``).

    On each page, ``collect_fn(component)`` is called and the returned list
    is appended to the accumulator. Pagination stops when any of:
      * the accumulator has reached ``target_count``,
      * ``component.has_next_page()`` returns False,
      * ``max_pages`` pages have been walked.

    May return fewer than ``target_count`` items — that's expected when
    the result set is smaller than requested (callers decide via their
    own ``allow_partial`` flag what to do with a short return).

    ``max_pages`` falls back to ``env.max_pages_to_paginate`` when not
    supplied. One of the two must be provided.
    """
    if max_pages is None:
        if env is None:
            raise ValueError(
                "collect_until requires either max_pages or env " "(to read max_pages_to_paginate)"
            )
        max_pages = env.max_pages_to_paginate

    collected: list[T] = []
    for page_index in range(1, max_pages + 1):
        batch = collect_fn(component)
        collected.extend(batch)
        _LOG.info(
            "paginator: page=%d collected_this_page=%d total=%d target=%d",
            page_index,
            len(batch),
            len(collected),
            target_count,
        )
        if len(collected) >= target_count:
            return collected[:target_count]
        if not component.has_next_page():
            _LOG.info("paginator: no next page after page %d", page_index)
            break
        component.go_to_next_page()

    return collected
