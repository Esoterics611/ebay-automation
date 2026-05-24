---
name: fixture-recorder
description: Convert a flaky live-site test into a deterministic fixture-replay test using Playwright's page.route() interception. Records real responses from a clean run to tests/fixtures/<test>/, then replays them on subsequent runs so the test no longer depends on eBay's geo-localization, Akamai mitigation, currency, or DOM drift. Use only after flake-triage classifies a failure as ENVIRONMENT or repeated TRANSIENT — fixture replay is the right answer when the live target is the problem, not the wrong answer when the code is.
---

# fixture-recorder

The most reliable cure for a hostile live target. eBay's Akamai layer,
geo-redirects, ILS/USD localization, and SRP rewrites are all things
this repo cannot control. Fixture replay removes the live dependency
from any test that doesn't need it.

## When to invoke

- `flake-triage` classified a failure as **ENVIRONMENT** (bot wall,
  geo, captcha) AND the user wants the test to keep running in CI.
- A test has flaked > 3 times with no code change.
- The user explicitly asks for "fixtures" / "mock server" / "offline
  testing."

## When NOT to invoke

- The test is a **smoke** test designed to catch live-site regressions.
  Smokes need the real network — that's their purpose.
- Selector drift (`qa-debug`'s territory). Replaying a stale recording
  freezes the drift in place; the test stops catching real changes.
- Single intermittent failure of an otherwise-stable test. Re-run first.

## File layout

```
tests/
├── fixtures/
│   └── <scenario-id>/
│       ├── responses.jsonl       # one JSON object per recorded response
│       └── README.md              # date recorded, scenario, eBay region
```

Each recording is scoped to a scenario id (or `test_<name>` for non-
parametrized tests). The README captures *when* and *under what
conditions* it was recorded — recordings rot, and the next maintainer
needs to know how old "current" is.

## Workflow

### 1. Add a record/replay fixture to conftest.py

Add this once per repo (gate on an env var so live runs are unaffected):

```python
import json, os
from pathlib import Path

@pytest.fixture
def network(page, request):
    mode = os.getenv("NETWORK", "live")  # live | record | replay
    if mode == "live":
        yield
        return

    fx_dir = Path("tests/fixtures") / _safe_id(request.node.nodeid)
    fx_file = fx_dir / "responses.jsonl"

    if mode == "record":
        fx_dir.mkdir(parents=True, exist_ok=True)
        records = []
        def on_response(resp):
            try:
                records.append({"url": resp.url, "status": resp.status,
                                "headers": dict(resp.headers),
                                "body": resp.body().decode("utf-8", "replace")})
            except Exception:
                pass
        page.on("response", on_response)
        yield
        fx_file.write_text("\n".join(json.dumps(r) for r in records))

    elif mode == "replay":
        recs = [json.loads(l) for l in fx_file.read_text().splitlines()]
        by_url = {r["url"]: r for r in recs}
        def handler(route):
            r = by_url.get(route.request.url)
            if r:
                route.fulfill(status=r["status"], headers=r["headers"], body=r["body"])
            else:
                route.abort()
        page.route("**/*", handler)
        yield
```

### 2. Record a clean run

```bash
NETWORK=record uv run pytest tests/test_data_driven.py::test_scenario[regression-vintage-postcards-chromium]
```

Confirm the recording landed in `tests/fixtures/<id>/responses.jsonl`.
Write the README with date, region, and any notable observations.

### 3. Replay

```bash
NETWORK=replay uv run pytest tests/test_data_driven.py::test_scenario[regression-vintage-postcards-chromium]
```

The test should now pass without any network access. Verify by
disabling network on the box (`unshare -n` on Linux) and re-running.

### 4. CI policy

Add to CI matrix:

| Job | NETWORK= | Tests included | Cadence |
|---|---|---|---|
| smoke-live | live | `@smoke` | every commit |
| regression-replay | replay | `@regression` | every commit |
| regression-live | live | `@regression` | nightly + dispatch |

Replay catches *our* regressions; live catches *eBay's* regressions.
Both matter.

## Maintenance

A fixture is **frozen drift**. After a `qa-debug` selector update:

1. Re-record the affected scenario:
   `NETWORK=record uv run pytest <test>`
2. Diff the new recording against the old one to verify only the
   expected fields changed.
3. Commit the fixture as a separate commit from the code change.

## Anti-patterns

- Recording from a flaky run. If the recording captures the failure
  mode, replay perpetuates it. Always record from a known-good run.
- Replaying smoke tests. Smokes exist precisely to catch the live
  changes replay would hide.
- Hand-editing `responses.jsonl`. The file is generated; if it's
  wrong, re-record.
- Committing very large recordings (>1 MB per scenario). Trim noisy
  third-party calls (analytics, tracking pixels) in the recorder
  before write.
