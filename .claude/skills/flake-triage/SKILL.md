---
name: flake-triage
description: Classify a failing pytest run into one of five buckets — drift, transient, environment (Akamai/captcha/geo), test-assumption-wrong, or network — and route to the right next action. Use BEFORE jumping to qa-debug, when a previously-green test fails or the failure mode is not obviously a selector problem. Prevents wasted effort patching selectors when the real issue is a guest-cart redirect, a bot wall, or a USD-vs-ILS assumption.
---

# flake-triage

Pair-skill to `qa-debug`. `qa-debug` assumes drift — this one decides
*whether* drift is even the diagnosis. Tests against a live retail site
fail for many reasons; patching the wrong one wastes a session and
sometimes makes the suite worse (e.g. relaxing an assertion to hide an
environment problem).

## When to invoke

- A test that passed in the previous run fails in the current one, with
  no code changes on our side.
- The failure mode does not look like a `Locator` exception — empty
  result sets, unexpected page content, 403/404 responses, captcha
  screenshots, "Access Denied" pages.
- Multiple tests fail in a *correlated* way (e.g. all four regression
  tests fail at the same step) — that pattern is rarely drift.

## The five buckets

Walk the decision tree top-down. Stop at the first match.

### 1. ENVIRONMENT (geo / bot wall / captcha / rate limit)

**Signals:**
- Failure screenshot or page content shows "Access Denied", "Pardon Our
  Interruption", a captcha, or a geo-redirect (`ebay.co.uk`, `ebay.de`
  instead of `ebay.com`).
- HTTP response was 403 / 429 / 503 (visible in trace.zip network log).
- Multiple unrelated tests fail at the *first* navigation.
- `/cart`, `/myb/`, or `/signin` returns 404 — eBay disables guest
  access to some flows region-by-region.

**Next action:** **Do not patch code.** Surface to the user with the
evidence. Suggested mitigations (user decides):
- Re-run from a different IP / VPN.
- Switch profile (`PROFILE=ci` runs headless with different fingerprint).
- Switch to fixture-based replay (see the `fixture-recorder` skill).
- Wait out a rate limit (often 5-30 min).

### 2. TEST ASSUMPTION WRONG (currency / region / locale)

**Signals:**
- Cards qualify in isolation but not in the test (e.g. `parse_price`
  rejects all values).
- Asserted budget is in USD but eBay served ILS prices, or vice versa.
- Subtotals look right but in the wrong currency.

**Next action:** Patch `db/data.yaml` thresholds, the test's `Decimal`
budget, or `parse_price`'s anchor set — *not* a `_SEL_*` constant.
This is data/config, not UI drift.

### 3. NETWORK (timeout, DNS, connection reset)

**Signals:**
- `playwright._impl._errors.TimeoutError` on a `goto()` call.
- `ERR_CONNECTION_RESET`, `ECONNREFUSED` in the trace.
- The test takes the full timeout, not the page-load time.

**Next action:** Re-run once. If it still fails, surface to user; do
not increase timeouts in code. Pinned timeouts are intentional — they
detect real slowness.

### 4. TRANSIENT (passed before, fails now, no clear cause)

**Signals:**
- Same test passed in the previous run.
- No environment red flags.
- No obvious DOM drift in the failure screenshot.
- Failure does not reproduce on a single-test re-run.

**Next action:** Re-run the failing test alone:
`uv run pytest <path>::<test_name> -v`. If it passes, log it as a
known flake (don't auto-quarantine; that hides real intermittent
failures). If it fails again, escalate to bucket 5 (DRIFT).

### 5. DRIFT (selector / DOM mismatch)

**Signals:**
- `Locator.click: Timeout` / `Locator.fill: Timeout` / strict-mode
  violation.
- Failure screenshot shows the expected page, but the targeted element
  is in a different place, has a different role, or has a renamed class.
- All buckets 1-4 ruled out.

**Next action:** Invoke the `qa-debug` skill. It is built for exactly
this.

## Output format

After triage, report to the user in this shape — no more than five
lines:

```
Bucket: <ENVIRONMENT|TEST-ASSUMPTION|NETWORK|TRANSIENT|DRIFT>
Evidence: <one-line citation — screenshot path, log line, response code>
Next: <one sentence — re-run / patch data.yaml / invoke qa-debug / escalate>
```

Then act on "Next" (or hand off, if the action requires user
authorization — re-running is fine, switching VPNs is not).

## Anti-patterns

- Calling everything DRIFT and going straight to `qa-debug`. The
  bucket-1 (environment) case is the most expensive to misdiagnose —
  you can spend hours patching selectors that were never wrong.
- Relaxing assertions to "fix" flakes. The whole point of an assertion
  is that it fails when reality changes; silencing it converts the test
  into ceremony.
- Quarantining tests on first flake. A test that flakes 1% of runs is
  worth keeping for the 1% — that's a real bug surfacing.
