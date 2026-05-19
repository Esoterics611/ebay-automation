from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class Environment:
    id: str
    base_url: str
    region: str
    currency: str
    headless: bool
    slow_mo_ms: int
    trace: str
    video: str
    screenshot_on_failure: bool
    max_pages_to_paginate: int


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    query: str
    max_price: Decimal
    limit: int
    allow_partial: bool
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Expectation:
    id: str
    min_results: int
    all_under_budget: bool
    max_acceptable_total_pct: Decimal


@dataclass(frozen=True)
class DemoScenario:
    id: str
    name: str
    query: str
    max_price: Decimal
    limit: int
    narrative: str
