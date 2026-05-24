import re
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page


class ScreenshotManager:
    def __init__(
        self,
        page: Page,
        test_id: str = "no-test",
        base_dir: Path | str = "reports/screenshots",
    ) -> None:
        self.page = page
        self.test_id = test_id
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._step_counter = 0

    def for_test(self, test_id: str) -> "ScreenshotManager":
        self.test_id = test_id
        self._step_counter = 0
        return self

    def capture(self, step: str, *, full_page: bool = True) -> Path:
        self._step_counter += 1
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = (
            f"{_safe(self.test_id)}__" f"{self._step_counter:02d}_{_safe(step)}__" f"{ts}.png"
        )
        path = self.base_dir / filename
        self.page.screenshot(path=str(path), full_page=full_page)
        return path


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name)[:80] or "_"
