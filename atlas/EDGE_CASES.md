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
arrive as `ILS NNN.NN` on the SRP and `₪NNN.NN` on the cart page.
Multiple forms must parse:
- `$19.99`, `US $1,234.56`, `$10.00 to $25.00`
- `ILS 25`, `ILS 356.56`, `ILS 1,486.79`, `ILS 25 to ILS 30`
- `+ILS 75.00 delivery` (shipping line in SRP card body)
- `₪332.48`, `₪ 1,486.79`, `Subtotal ₪332.48` (cart-page subtotal)
- `NIS 50` (legacy widget format, occasionally)

**Strategy:** Anchor on a currency token (`$`, `ILS`, `₪`, or `NIS`),
then capture the numeric. `Decimal(str(...))` only — never `float`.
The price parser returns the lower bound for ranges, which is what the
filtering rules use. Bare numerics (`Subtotal (3 items)`) are rejected
on purpose: the anchor disambiguates the count from the price.

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

## Cart subdomain (`cart.ebay.com`)

**Symptoms:** Navigating `https://www.ebay.com/cart` returns HTTP 302
to `https://pages.ebay.com/cart` which then 404s on `/n/error` in some
regions (this is the deprecated legacy route). The error page is
styled like a normal eBay page (header, search, footer) so a naive
"did the page load?" check passes — the distinguishing signal is the
URL substring `/n/error`.

**Cause:** eBay moved the cart to its own subdomain
`https://cart.ebay.com/`. The legacy `/cart` path on the main domain
is a deprecated route that is regionally inconsistent.

**Strategy:** `CartPage.URL_PATH` is the absolute URL
`https://cart.ebay.com/`. As a safety net, `CartPage.is_unavailable()`
checks for the `/n/error` URL substring after navigation. If eBay
ever routes us there again (region block, deprecated path), the cart
service raises a domain-specific `CartUnavailableError`; tests convert
that to `pytest.skip` with the landing URL in the reason rather than
fail opaquely. In normal use against `cart.ebay.com`, this never
fires.

**Subtotal text format:** The cart page displays the subtotal as
`₪ 332.48` (Unicode shekel sign U+20AA) — not `ILS 332.48`. The
price parser accepts both, plus `$`-prefixed amounts. See the
"Currency parsing" section.

## Login interstitials (guest only)

**Symptoms:** Clicking "Check out" forces a sign-in flow. Some flows
(wishlists, watchlists, "save for later") also prompt.

**Strategy:** The suite is guest-only. Tests must stop at the cart
subtotal assertion — never click Check out. If a sign-in interstitial
appears mid-flow (unexpected), fail the test with the current URL in the
error message.
