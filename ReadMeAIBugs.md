# AI-Generated Test Code: Static Review

A teammate used an AI assistant to draft the following Playwright test and asked
for review. The code runs, but is broken in ways that make it useless as a test
and dangerous as a template. Five issues below, ordered by impact.

## The Code Under Review

```python
from playwright.sync_api import sync_playwright
from selenium import webdriver
import time


def test_search_functionality():
    browser = sync_playwright().start().chromium.launch()
    page = browser.new_page()
    page.goto("https://example.com")

    time.sleep(2)

    search_box = page.locator("#search")
    search_box.fill("playwright testing")

    page.locator(".button").click()

    time.sleep(3)

    results = page.locator(".result-item")

    browser.close()
```

## Issue 1 — The test has no assertions

**Problem.** `results = page.locator(".result-item")` constructs a locator
object; it does not query the DOM, count anything, or verify anything. The
function exits without a single `assert` or `expect(...)`. As written, this
"test" passes whenever no exception is thrown — even if the search returned
zero results, redirected to an error page, or loaded the wrong site entirely.
A test that cannot fail meaningfully is not a test.

**Fix.** Replace the dangling locator with explicit verification.

```python
results = page.locator(".result-item")
expect(results.first).to_be_visible()
assert results.count() > 0, f"Expected results, got {results.count()}"
expect(page).to_have_url(re.compile(r".*search.*"))  # sanity-check destination
```

## Issue 2 — Brittle CSS locators (`#search`, `.button`)

**Problem.** `#search` is a fragile ID; if the page is re-built with a CSS
framework or React rename, it disappears silently. `.button` is worse — it is
almost certainly not unique on the page, so Playwright either throws a
strict-mode violation or clicks the wrong element. Neither locator survives a
DOM refactor, and neither communicates *intent*: a reviewer cannot tell from
the code which button is being clicked or what the search box is for.

**Fix.** Use semantic locators that target accessibility roles and visible
labels — these are stable across cosmetic refactors and self-documenting.

```python
search_box = page.get_by_role("searchbox", name="Search")
search_box.fill("playwright testing")
page.get_by_role("button", name="Search").click()
```

## Issue 3 — `time.sleep()` instead of Playwright's auto-waits

**Problem.** Two hardcoded sleeps (2 s and 3 s). This is the canonical
Playwright anti-pattern. `time.sleep()` is simultaneously *too slow* (always
burns the full duration even when the page is ready in 100 ms) and *too flaky*
(when a slow CI runner needs 4 s, the test fails despite the page eventually
loading correctly). Playwright already auto-waits on actions (`fill`, `click`)
and offers `expect()` for state assertions.

**Fix.** Remove `import time` entirely. Wait on observable state, not wall clock.

```python
page.goto("https://example.com", wait_until="domcontentloaded")
expect(search_box).to_be_visible()        # replaces the first sleep
# ... click ...
expect(page.locator(".result-item").first).to_be_visible()  # replaces the second
```

## Issue 4 — Stray Selenium import + Playwright resource leak

**Problem.** Two distinct mistakes that together reveal an AI hallucination:

1. `from selenium import webdriver` is imported but never used. Selenium and
   Playwright are different frameworks; mixing them in one file suggests the
   generator was stitching examples from training data without understanding
   either. The import will also fail in an environment without `selenium`
   installed, breaking the test before it runs.
2. `sync_playwright().start()` returns a `Playwright` runtime that owns a
   background process; the code calls `browser.close()` but never calls
   `.stop()` on the runtime, leaking the process. On a CI runner repeating
   this pattern, the runner exhausts handles and starts failing mysteriously.

**Fix.** Delete the Selenium import. Wrap the runtime in a context manager so
both browser *and* runtime are cleaned up, even on exception.

```python
from playwright.sync_api import sync_playwright, expect

def test_search_functionality():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()  # isolate cookies/storage per test
        page = context.new_page()
        # ... test body ...
        context.close()
        browser.close()
```

Better still in a real suite: use the `pytest-playwright` plugin's `page`
fixture, which handles the runtime, browser, context, trace, and video
lifecycle for you — that's the entire reason the plugin exists.

## Issue 5 — Not a real pytest test (mixed paradigms)

**Problem.** The function is named `test_search_functionality`, signalling
pytest, but the body manually launches Playwright instead of accepting the
`page` fixture from `pytest-playwright`. The result is a function that pytest
*will* discover and run, but which ignores all of pytest-playwright's
machinery: no automatic trace capture on failure, no video, no screenshot,
no per-test isolation, no parallelism via `pytest-xdist`. Debugging a failure
means rerunning manually with a debugger — exactly what the framework exists
to prevent.

**Fix.** Pick a paradigm and commit. For a pytest suite:

```python
import re
from playwright.sync_api import Page, expect

def test_search_functionality(page: Page):
    page.goto("https://example.com", wait_until="domcontentloaded")
    page.get_by_role("searchbox", name="Search").fill("playwright testing")
    page.get_by_role("button", name="Search").click()

    results = page.locator(".result-item")
    expect(results.first).to_be_visible()
    assert results.count() > 0
    expect(page).to_have_url(re.compile(r".*search.*"))
```

Configure trace, video, and screenshot capture once in `conftest.py` and they
apply to every test in the suite.

## Summary

| # | Issue | Why it matters |
|---|---|---|
| 1 | No assertions | Test cannot fail on real bugs |
| 2 | `#search` and `.button` locators | Brittle, ambiguous, opaque |
| 3 | `time.sleep()` | Slow and flaky |
| 4 | Selenium import + leaked Playwright runtime | Dead code + process leak |
| 5 | Manual Playwright in a pytest function | Ignores the framework you're paying for |

The deeper lesson: AI-generated test code often *looks* like a test because
it has the shape of one — imports, a `test_*` function, browser launch, page
actions. Reviewing it requires checking whether each line does the thing its
shape implies. In this snippet, the assertions are missing, the locators are
ornamental, the waits are wishful, and the framework is bypassed.
