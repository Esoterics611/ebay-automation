# tests/slow/

Long-running tests (> 30 s each). Run in a dedicated pipeline slot.

**Examples:** multi-step purchase flows, pagination exhaustion, large search
result sets, timed wait assertions.

Mark each test: `@pytest.mark.slow`
