---
name: qa-debug
description: Triage and fix failing Playwright E2E tests against a live UI by capturing the actual page state (HTML + accessibility tree + screenshot), visually inspecting the screenshot, and re-anchoring the failing component's _SEL_* constant. Use when pytest fails with Locator.click / Locator.fill timeouts, strict-mode violations, "element not found" assertions, or empty result collections that suggest DOM drift on a live target.
---

# qa-debug

A workflow for AI-assisted maintenance of selectors against a moving target
(public retail sites, third-party UIs, anything not under our control).
The premise: don't guess selectors — capture the page once, look at it with
your own (multimodal) eyes, then patch the one constant that drifted.

## When to invoke

- A pytest run fails with one of:
  - `Locator.click: Timeout` / `Locator.fill: Timeout`
  - `Error: strict mode violation: ... resolved to N elements`
  - `expect(locator).to_be_visible() failed`
  - empty collection (e.g. `assert len(urls) > 0` when the page has cards)
- A previously green test starts failing without a code change on our side.
- An assessment / interview demo run needs to be brought back to green.

## What this skill does NOT do

- Does not patch business logic in services. Drift = UI-layer; if the
  failure is in `_qualify_card`, `parse_price`, or pagination math, this
  skill is the wrong tool.
- Does not chase test-environment flakes (geo redirects, currency
  localization, captcha walls). Surface those to the user; do not "fix"
  them by relaxing assertions.

## Workflow

### 1. Triage the failure

Read the pytest output. Identify exactly:
- **The failing call**: which component method, which `_SEL_*` constant.
- **The error class**: timeout (selector missing), strict mode (ambiguous),
  or assertion (post-selector logic).

If strict-mode: the fix is usually `exact=True` or a narrower regex.
Skip the snapshot — go straight to the patch.

If timeout / empty: the selector is wrong. Continue.

### 2. Inspect the artifacts that already exist (before probing live)

A failing pytest run in this project already drops a rich set of
artifacts on disk. Look at these *first* — most drift can be diagnosed
without launching another browser session.

| Path | What's there | When to use |
|---|---|---|
| `test-results/<test-id>/test-failed-N.png` | Full-page screenshot at the moment of failure (pytest-playwright, `--screenshot=only-on-failure`) | First thing to look at. `Read` it to see what the page actually looked like when the assertion blew up. |
| `test-results/<test-id>/trace.zip` | Playwright trace — every action, before/after DOM snapshot, network log, console messages | The richest artifact. Open with `npx playwright show-trace test-results/<test-id>/trace.zip` (or extract and read individual frames). Use when the screenshot alone doesn't reveal the cause. |
| `test-results/<test-id>/video-N.webm` | Video recording of the run (`--video=retain-on-failure`) | When you need to see the sequence (e.g. a transient modal that closes too fast for a screenshot). |
| `reports/screenshots/*.png` | Per-step screenshots captured by `screenshots.capture(...)` calls in tests/services. Filenames are `<test-id>__<NN>_<step>__<timestamp>.png` so they sort chronologically. | Scrub through to find the last *successful* step before failure — that's where to focus. |
| `allure-results/*-attachment.png` | Allure-attached screenshots from `allure.step("...")` blocks | Same content as `reports/screenshots/` but indexed by Allure step name in the report. |

**Recommended order:**
1. `Read` the `test-failed-N.png` for the failing test.
2. List `reports/screenshots/<test-id>__*.png` in chronological order; `Read` the last 2-3 in sequence to see how the page progressed.
3. If the failure cause is now obvious (wrong page, unexpected modal,
   greyed-out control, empty state), **skip straight to step 4 (patch)** —
   no live probe needed.
4. If the artifacts don't tell the story (e.g. screenshot shows a
   plausible page but a specific selector still didn't match), go to
   Step 3 (live capture).

### 3. Capture live page state (only if step 2 was inconclusive)

Create a single throwaway file `tests/_z_probe.py` that piggybacks on
this project's `conftest.py` (the `page` fixture is what gets through
Akamai — bare Playwright will not):

```python
"""Throwaway — capture page state at the failure point. Delete after."""
from pathlib import Path
from playwright.sync_api import Page

OUT = Path("/tmp/qa_debug")

def test_capture(page: Page) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # Reproduce the steps the failing test took, up to (but not past)
    # the failing call. Copy the test verbatim if unsure.
    page.goto("https://www.ebay.com/")
    # ... reproduce up to the failing line ...

    OUT.joinpath("url.txt").write_text(page.url)
    OUT.joinpath("page.html").write_text(page.content())
    OUT.joinpath("aria.yaml").write_text(page.locator("body").aria_snapshot())
    page.screenshot(path=str(OUT / "viewport.png"))
    page.screenshot(path=str(OUT / "full.png"), full_page=True)
```

Run: `uv run pytest tests/_z_probe.py -s`.

### 3. Look at the page — with your eyes AND the DOM

This is the step that's easy to skip and worth the most. Use all three:

| Artifact | What it's good for |
|---|---|
| `viewport.png` / `full.png` | **Visual state** — is the element actually rendered? greyed out? behind a cookie banner? off-screen? Is there an unexpected modal? Read the image with the `Read` tool to inspect it directly. |
| `aria.yaml` | **Roles + accessible names** — the fastest way to find a `get_by_role` target. Much smaller than HTML (~150 KB vs ~1.5 MB on eBay SRP). `grep -i "<expected name>"` to find candidates. |
| `page.html` | **Class names, data attributes, parent containers** — the fallback when role/name can't disambiguate. Search for the old selector substring to see what replaced it. |

A good triage pass takes 5 minutes:
1. Open the screenshot in `Read` → confirm the element is *actually
   visible*. If not, the issue is upstream (modal, navigation, geo).
2. `grep` the aria snapshot for the expected accessible name.
3. If found, check the role — `link`, `button`, `menuitem`, etc. Roles
   change in framework rewrites (e.g. `menuitem` → `link`).
4. If not found in aria, grep the HTML for the old class name to find
   the new one in the same DOM neighborhood.

### 4. Patch the failing call

Edit the component file. Keep the constant; change its value. Add an
inline comment with the **why** (one line — the framework rewrite,
the role change, the anti-scraping obfuscation, whatever applied):

```python
# Old:
_SEL_PRICE_CSS = ".s-item__price"
# New:
# eBay 2024 SRP rewrite: .s-item* class family was renamed to .s-card*.
_SEL_PRICE_CSS = ".s-card__price"
```

The constant name should not change — call sites stay untouched.

### 5. Verify the fix

```bash
uv run mypy src/                                 # must stay clean
uv run pytest tests/<the-failing-test>.py -v     # re-run JUST the one
```

If green: continue. If a NEW failure appears downstream, repeat from
Step 2 (look at the new artifacts first) — drift often comes in
clusters (a framework rewrite touches many selectors at once), but
each cluster is best diagnosed off its own fresh failure artifacts.

### 6. Clean up + hand off

```bash
rm tests/_z_probe.py
rm -rf /tmp/qa_debug
```

Do NOT run `git commit`. Hand the work back to the user with:
- the list of files changed
- a suggested commit message (in a fenced block, one per logical unit)
- a one-paragraph summary of the drift cause and the fix

Suggested message shape:
```
fix(selectors): <component> — <old> → <new>

<one-line explanation of the drift cause>
```

One suggested commit per drifted constant when the causes differ. One
bundled commit when it's a single framework rewrite touching many
constants. The user decides whether to bundle or split.

## Anti-patterns

- Relaxing the assertion to make the test pass without finding the right
  selector. The whole point of an E2E test is the assertion.
- Adding `time.sleep()` to "give the page time" — always use
  `expect(locator).to_be_visible()` or `wait_for_*`.
- Falling back to CSS / XPath when a role-based selector would survive.
  See `atlas/SELECTORS.md` priority order.
- Committing the `_z_probe.py` or the `/tmp/qa_debug/` artifacts.
- Patching multiple components in one commit without saying why — drift
  history is the most useful thing in `git log` for this codebase.

## Capture discipline (so the next failure debugs itself)

The richer the on-disk artifact set when a test fails, the less live
probing the next session needs. After fixing a failure, if Step 2
revealed a gap in the visual trail (e.g. you couldn't tell whether
add-to-cart succeeded on item #2 because there was no screenshot between
items), patch the gap by adding a `screenshots.capture(<step>)` call in
the service or test at that transition point. The convention:

- **Services** capture at every external-state transition: after a
  navigation, after a click that mutates server state, before reading a
  value that's about to be asserted. Filename labels should be
  imperative and short (`searched`, `price-filtered`, `added-cart`,
  `cart-opened`, `subtotal-read`).
- **Tests** capture at `allure.step` boundaries (already covered) and
  immediately *before* an assertion — so the failure screenshot shows
  the *input* to the assertion, not the page after the AssertionError
  is raised.
- **Components** do not capture. Components are below the layer that
  knows what a "step" is; capturing inside them would over-screenshot.

A captured step costs ~100 ms. Budget accordingly: a 5-step service
flow with capture is ~500 ms slower per run. That's worth it for the
zero-debug-cost next failure.

Example — the cart service today captures at "added-to-cart" per item
but not at "cart-opened" or "subtotal-read". A failure in
`assert_cart_total_not_exceeds` therefore has only the failed-test
screenshot to work from, with no record of what the cart *looked like*
when the subtotal was read. Two lines plug that gap:

```python
def assert_cart_total_not_exceeds(self, budget_per_item, items_count):
    self._cart.open()
    screenshot_path = self._cart.screenshot_cart()           # before
    subtotal = self._cart.subtotal()
    # add: capture the page state that produced this subtotal value
    self._cart.screenshot("subtotal-read")
    ...
```

When in doubt: **capture more, not less.** Allure groups screenshots by
step name so they don't clutter the report, and disk is cheaper than a
second live debugging session.

## Optional: auto-capture on failure

If selector drift is recurring, add this to `tests/conftest.py` so every
failing test drops the artifacts automatically — no manual probe step:

```python
@pytest.hookimpl(hookwrapper=True, trylast=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed and "page" in item.fixturenames:
        page = item.funcargs["page"]
        out = Path("debug") / _safe_id(item.nodeid)
        out.mkdir(parents=True, exist_ok=True)
        try:
            out.joinpath("page.html").write_text(page.content())
            out.joinpath("aria.yaml").write_text(page.locator("body").aria_snapshot())
            page.screenshot(path=str(out / "full.png"), full_page=True)
        except Exception:
            pass  # best-effort; never block the failure report
```

(Already covered for traces/video/screenshot by `pytest-playwright`'s
`--tracing=retain-on-failure` etc. in `pyproject.toml`; this extends
that to HTML + aria.)
