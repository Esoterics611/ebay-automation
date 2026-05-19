# tests/smoke/

Fast, critical-path tests. Run before every deploy.

**Criteria for smoke tests:**
- Cover the single most important happy path per feature area.
- Complete in < 60 s total on a single worker.
- No dependency on test-data setup beyond what `conftest.py` provides.

Mark each test: `@pytest.mark.smoke`
