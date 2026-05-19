# EDGE_CASES

Known irregularities on the eBay public site that test code must handle.

---

## Cookie banner

**Symptoms:** A consent banner appears on first visit; variants observed:
- Full-page modal with "Accept all" / "Reject all".
- Footer slide-up bar with the same buttons.
- No banner (consent already in browser storage, common in CI runs after
  the first scenario).

**Strategy:** Probe for an "Accept" / "Accept all" button with a short
(≤ 2 s) timeout. If not visible, proceed. Use `is_visible()` rather than
waiting — the banner missing is the happy path.

---

## Geo-redirects

**Symptoms:** Navigating `ebay.com` from a non-US IP redirects to
`ebay.de`, `ebay.co.uk`, etc., yielding different layouts and currencies.

**Strategy:** Set the region cookie *before* the first navigation (handled
in `tests/conftest.py::_set_region_cookies`). After the first page load,
assert `page.url` starts with `env.base_url`; if not, fail fast with a
clear diagnostic. Also set `Accept-Language: en-US` via the browser
context locale.

---

## Sponsored vs organic results

**Symptoms:** Sponsored listings interleave with organic ones in the
results grid; their position and price profile differ from organic items.

**Strategy:** Skip any card that contains the text "SPONSORED" (case
sensitive) or has the `data-listing-status="sponsored"` attribute. Treat
as separate from "Featured" cards, which are organic.

---

## Mixed Buy-It-Now and Auction listings

**Symptoms:** Result grid mixes fixed-price listings with live auctions.
Auctions show "Current bid" / "Time left" and have no Add-to-Cart button.

**Strategy:** When collecting URLs in the flow, skip cards whose price
block contains "bid" / "auction" / "time left" — only Buy-It-Now items
qualify. If unsure, opening the item page and probing for the Add-to-Cart
button is the authoritative check.

---

## Price ranges

**Symptoms:** Listings with variants display prices as a range:
"$10.00 to $25.00".

**Strategy:** Parse the lower bound as the "listed price" used for
filtering. Reject the listing if the upper bound exceeds `max_price` and
the test cannot guarantee the chosen variant lands under budget. When in
doubt, choose a variant on the item page and read the resolved price
before adding to cart.

---

## Variant detection

**Symptoms:** Some items have one or more variant pickers (size, color,
storage, …). Submitting Add-to-Cart without a selection produces an
inline error.

**Strategy:** Enumerate all visible variant comboboxes/listboxes. For
each, pick a random in-stock option (skip ones labeled "Out of stock" or
disabled). After all variants are chosen, wait for the price to refresh
(`expect(price_locator).not_to_have_text(""))` before clicking Add to
Cart. If no variants can be satisfied, log and skip the item.

---

## Currency parsing

**Symptoms:** Displayed prices include currency symbols, codes, thousands
separators, and occasionally explicit "US " prefixes:
- `$19.99`
- `US $1,234.56`
- `$10.00 to $25.00`

**Strategy:** Strip everything that is not a digit, dot, or hyphen, then
construct `Decimal` from the resulting string. Use `Decimal(str(value))`
form to avoid float intermediate values. Never multiply or compare price
strings via `float()`.

---

## Cart drawer vs page

**Symptoms:** After clicking Add to Cart on an item page, the site may:
- show a transient overlay/drawer with "Added to cart — View cart", or
- navigate to `/cart`, or
- show a modal sheet on narrower viewports.

**Strategy:** The cart service navigates to `/cart` directly after every
add, regardless of drawer state. This avoids relying on the drawer being
present and keeps the flow deterministic.

---

## Login interstitials (guest only)

**Symptoms:** Clicking "Check out" forces a sign-in flow. Some flows
(wishlists, watchlists, "save for later") also prompt.

**Strategy:** The suite is guest-only. Tests must stop at the cart
subtotal assertion — never click Check out. If a sign-in interstitial
appears mid-flow (unexpected), fail the test with the current URL in the
error message.
