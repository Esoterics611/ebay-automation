import json
from dataclasses import fields, is_dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Generic, TypeVar

from ebay_automation.db.models import DemoScenario, Environment, Expectation, Scenario

T = TypeVar("T")

_DECIMAL_FIELDS: frozenset[str] = frozenset({"max_price", "max_acceptable_total_pct"})


class Accessor(Generic[T]):
    def __init__(self, items: dict[str, T]) -> None:
        self._items = items

    def get(self, id: str) -> T:
        if id not in self._items:
            raise KeyError(
                f"id '{id}' not found. Available: {sorted(self._items)}"
            )
        return self._items[id]

    def all(self) -> list[T]:
        return list(self._items.values())

    def where(self, **filters: Any) -> list[T]:
        def matches(item: T) -> bool:
            for key, value in filters.items():
                attr = getattr(item, key, None)
                if attr is None and hasattr(item, key + "s"):
                    attr = getattr(item, key + "s")
                if isinstance(attr, list):
                    if value not in attr:
                        return False
                elif attr != value:
                    return False
            return True

        return [item for item in self._items.values() if matches(item)]


class TestDatabase:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        if not self.db_path.is_dir():
            raise FileNotFoundError(f"db path is not a directory: {self.db_path}")
        self._cache: dict[str, dict[str, Any]] = {}
        self._environments = self._build(Environment, "environments.json")
        self._scenarios = self._build(Scenario, "scenarios.json")
        self._expectations = self._build(Expectation, "expectations.json")
        self._demos = self._build(DemoScenario, "demo_scenarios.json")

    @property
    def environments(self) -> Accessor[Environment]:
        return self._environments

    @property
    def scenarios(self) -> Accessor[Scenario]:
        return self._scenarios

    @property
    def expectations(self) -> Accessor[Expectation]:
        return self._expectations

    @property
    def demos(self) -> Accessor[DemoScenario]:
        return self._demos

    def _read(self, name: str) -> dict[str, Any]:
        if name not in self._cache:
            self._cache[name] = json.loads((self.db_path / name).read_text())
        return self._cache[name]

    def _build(self, model: type, name: str) -> Accessor:
        raw = self._read(name)
        items = {id_: _load_model(model, id_, payload) for id_, payload in raw.items()}
        return Accessor(items)


def _load_model(model: type, id_: str, payload: dict[str, Any]) -> Any:
    if not is_dataclass(model):
        raise TypeError(f"{model.__name__} is not a dataclass")
    kwargs: dict[str, Any] = {"id": id_}
    for f in fields(model):
        if f.name == "id":
            continue
        if f.name in payload:
            value = payload[f.name]
            if f.name in _DECIMAL_FIELDS:
                value = Decimal(str(value))
            kwargs[f.name] = value
    try:
        return model(**kwargs)
    except TypeError as exc:
        raise ValueError(
            f"Invalid {model.__name__} for id '{id_}': {exc}. Payload: {payload}"
        ) from exc
