# tests/regression/

Full regression suite. Run nightly or on PRs targeting main.

**Criteria for regression tests:**
- Cover edge cases, negative paths, and cross-feature interactions.
- May rely on parameterisation for data-driven scenarios.
- Run with `-n auto` (pytest-xdist) to parallelise across workers.

Mark each test: `@pytest.mark.regression`
