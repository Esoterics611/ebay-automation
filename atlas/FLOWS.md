# FLOWS

End-to-end flow this suite drives, expressed at the service level.

---

## Primary flow: search → filter → collect → add to cart → assert subtotal

Inputs (from `db/scenarios.json` via `TestDatabase`):
- `query: str`
- `max_price: Decimal`
- `limit: int`           — target number of items to add to cart
- `allow_partial: bool`  — if true, proceed with fewer items when supply
                           runs out before `limit`
- `max_pages_to_paginate: int` (from `db/environments.json`)

### Steps

1. **Open home.** Navigate to `env.base_url`. Dismiss cookie banner if it
   appears (see EDGE_CASES). Verify URL didn't geo-redirect; if it did,
   the region cookie didn't take — fail fast.

2. **Search.** Type `query` into the search combobox and submit. Wait for
   the results heading (`expect(results_heading).to_be_visible()`).

3. **Apply price filter.** Set `_udhi=<max_price>` either via:
   - URL param (preferred — deterministic, survives reload), or
   - filter panel UI (fallback when URL filter is overridden).
   Wait for the results grid to re-render.

4. **Collect URLs.** Walk the result cards:
   - Skip sponsored listings.
   - Skip auction-only listings (no "Buy It Now").
   - Parse the listed price as `Decimal`; skip if `> max_price`.
   - Capture the item URL.
   - Stop when collected count == `limit`.

5. **Paginate.** If page yielded fewer than `limit` qualifying URLs:
   - Click "Next" and repeat step 4.
   - Bound by `max_pages_to_paginate`.
   - If still short after the bound:
     - `allow_partial=true`  → proceed with what we have.
     - `allow_partial=false` → fail with diagnostic showing pages walked.

6. **Per item, add to cart.** For each captured URL:
   - Navigate to item page.
   - If variant pickers are present, pick a random valid option from each
     (see VariantsService). Skip items whose required variants are all
     out-of-stock — log and continue.
   - Click "Add to cart".
   - Dismiss any "Added to cart" drawer/modal.

7. **Open cart.** Navigate to `/cart` directly (don't rely on drawer state).

8. **Read subtotal.** Locate the subtotal element, parse the displayed
   amount as `Decimal` (see currency parsing in EDGE_CASES).

9. **Assert.** Let `count` = number of items actually added.
   - Required: `subtotal <= max_price * count`.
   - With expectations: `subtotal <= max_price * count * (max_acceptable_total_pct / 100)`.
   - Also assert `count >= expectation.min_results`.

### Non-goals

- No checkout — flow stops at cart subtotal.
- No login — guest-only.
- No shipping/tax assertions — subtotal is the line-item total only.
