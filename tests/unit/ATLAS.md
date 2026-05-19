# tests/unit/

Pure-Python unit tests with **no browser dependency**. They must run
without launching Playwright — the autouse fixtures in
``tests/conftest.py`` are gated on ``request.fixturenames`` so unit tests
that don't request ``page`` or ``context`` skip browser setup entirely.

Use these for parsers, dataclass loaders, and other framework-internal
helpers where a full browser would be overkill.
