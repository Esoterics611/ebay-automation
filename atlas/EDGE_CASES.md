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
separators, and explicit "US " prefixes. eBay localizes the SRP price
text to the visitor's IP — the assessment runs from Israel, so prices
arrive as `ILS NNN.NN` rather than `$NN.NN`. Both forms must parse:
- `$19.99`, `US $1,234.56`, `$10.00 to $25.00`
- `ILS 25`, `ILS 356.56`, `ILS 1,486.79`, `ILS 25 to ILS 30`
- `+ILS 75.00 delivery` (shipping line in card body)

**Strategy:** Anchor on a currency token (`$` or `ILS`), then capture the
numeric. `Decimal(str(...))` only — never `float`. The price parser
returns the lower bound for ranges, which is what the filtering rules
use. Bare numerics (`Subtotal (3 items)`) are rejected on purpose: the
anchor disambiguates the count from the price.

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

## `/cart` page disabled (cart data still works)

**Symptoms:** Navigating `https://www.ebay.com/cart` returns HTTP 404
with a redirect to `/n/error`. The error page is styled like a normal
eBay page (header, search, footer) so a naive "did the page load?"
check passes — the distinguishing signal is the URL substring
`/n/error`. **However**, the cart *data* is intact: clicking "Add to
cart" on an item page still updates the header mini-cart dropdown,
which correctly lists items and shows a total. Only the standalone
`/cart` URL is blocked.

**Cause:** Observed for guests in IL during the 2024+ eBay shipping
pause to Israel (homepage banner: *"Shipping temporarily paused"*).
The shape — full-page cart blocked while the dropdown works — is
unusual and suggests a routing-level guard rather than a cart-storage
disable.

**Strategy:** `CartPage.is_unavailable()` checks for the URL marker
after `/cart` navigation. `CartService.assert_cart_total_not_exceeds`
raises a domain-specific `CartUnavailableError`; tests convert that
to `pytest.skip` with the landing URL in the reason. The
search/filter/add-to-cart flow remains green; only the subtotal
assertion (which reads from `/cart`) is skipped. Reading the subtotal
from the mini-cart dropdown is a possible follow-up but out of scope
for this assessment.

## Login interstitials (guest only)

**Symptoms:** Clicking "Check out" forces a sign-in flow. Some flows
(wishlists, watchlists, "save for later") also prompt.

**Strategy:** The suite is guest-only. Tests must stop at the cart
subtotal assertion — never click Check out. If a sign-in interstitial
appears mid-flow (unexpected), fail the test with the current URL in the
error message.
