import json
from dataclasses import fields, is_dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from ebay_automation.db.models import DemoScenario, Environment, Scenario

_DECIMAL_FIELDS = frozenset({"max_price"})


def _load_model(model: type, id_: str, payload: dict[str, Any]):
    if not is_dataclass(model):
        raise TypeError(f"{model.__name__} is not a dataclass")
    kwargs: dict[str, Any] = {"id": id_}
    for f in fields(model):
        if f.name == "id" or f.name not in payload:
            continue
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


def _load_all(model: type, path: Path) -> dict:
    raw = json.loads(path.read_text())
    return {id_: _load_model(model, id_, payload) for id_, payload in raw.items()}


class EnvironmentAccessor:
    def __init__(self, items: dict[str, Environment]) -> None:
        self._items = items
    def get(self, id: str) -> Environment:
        if id not in self._items:
            raise KeyError(f"environment '{id}' not found. Available: {sorted(self._items)}")
        return self._items[id]
    def all(self) -> list[Environment]:
        return list(self._items.values())


class ScenarioAccessor:
    def __init__(self, items: dict[str, Scenario]) -> None:
        self._items = items
    def get(self, id: str) -> Scenario:
        if id not in self._items:
            raise KeyError(f"scenario '{id}' not found. Available: {sorted(self._items)}")
        return self._items[id]
    def all(self) -> list[Scenario]:
        return list(self._items.values())
    def where(self, tag: str) -> list[Scenario]:
        return [s for s in self._items.values() if tag in s.tags]


class DemoScenarioAccessor:
    def __init__(self, items: dict[str, DemoScenario]) -> None:
        self._items = items
    def get(self, id: str) -> DemoScenario:
        if id not in self._items:
            raise KeyError(f"demo '{id}' not found. Available: {sorted(self._items)}")
        return self._items[id]
    def all(self) -> list[DemoScenario]:
        return list(self._items.values())
    def where(self, tag: str) -> list[DemoScenario]:
        return [d for d in self._items.values() if tag in getattr(d, "tags", [])]


class TestDatabase:
    __test__ = False  # not a pytest test class despite the "Test" prefix

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        if not self.db_path.is_dir():
            raise FileNotFoundError(f"db path is not a directory: {self.db_path}")
        env_path = self.db_path / "environments.json"
        sce_path = self.db_path / "scenarios.json"
        dem_path = self.db_path / "demo_scenarios.json"
        self._environments = EnvironmentAccessor(_load_all(Environment, env_path))
        self._scenarios = ScenarioAccessor(_load_all(Scenario, sce_path))
        self._demos = DemoScenarioAccessor(_load_all(DemoScenario, dem_path))

    @property
    def environments(self) -> EnvironmentAccessor:
        return self._environments

    @property
    def scenarios(self) -> ScenarioAccessor:
        return self._scenarios

    @property
    def demos(self) -> DemoScenarioAccessor:
        return self._demos
