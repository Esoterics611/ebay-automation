# PAGES

Reference for the four eBay pages this suite drives.

---

## Home — `https://www.ebay.com/`

**URL pattern:** `/` (no query string in normal flow).

**Purpose:** Entry point — surfaces the global search bar and top-level
categories. We never log in here; all flows start from guest state.

**Key roles:**
| Role | Accessible name |
|---|---|
| `combobox` | "Search for anything" (the main search input) |
| `button` | "Search" (submit) |
| `link` | "Sign in" / "My eBay" / cart icon |

**Dynamic behaviors:**
- Cookie/consent banner appears on first visit per origin (see EDGE_CASES).
- Personalised "Recently viewed" / "Picked for you" tiles render only when
  visitor cookies exist — DOM order can shift between cold and warm visits.
- Promo hero banners rotate on a timer; do not anchor to their text.
- Some regions show an interstitial "Are you in the right country?" prompt.

---

## Search results — `https://www.ebay.com/sch/i.html?_nkw=<query>`

**URL pattern:** `/sch/i.html` with query params:
- `_nkw` — search keywords
- `_udlo` — minimum price filter
- `_udhi` — maximum price filter (we drive this from `scenario.max_price`)
- `_pgn` — pagination page number (1-indexed)

**Purpose:** List items matching the keyword, with facet filters and
pagination. Most of the cart flow originates here.

**Key roles:**
| Role | Accessible name / locator |
|---|---|
| `heading` | "X results for <query>" |
| `listitem` | Each result card (under `ul.srp-results > li.s-item`) |
| `link` | Title link inside each card (role=link, name = item title) |
| `button` | Filter chips (e.g. "Buy It Now", "Condition") |
| `link` | Pagination ("Next", numbered pages) |

**Dynamic behaviors:**
- Sponsored listings interleave with organic results — flagged by
  `SPONSORED` text or `[data-listing-status]` (see EDGE_CASES).
- Mixed Buy-It-Now and Auction listings; only Buy-It-Now can be added to
  cart in our flow.
- Lazy-loading on scroll; pagination link `Next` is the canonical way to
  advance pages.
- The filter panel may be a sidebar (desktop) or a collapsed sheet (narrow
  viewport) — we always set viewport ≥ 1280 to keep the sidebar visible.

---

## Item — `https://www.ebay.com/itm/<id>`

**URL pattern:** `/itm/<id>` where `<id>` is the numeric listing ID.

**Purpose:** Single product detail, including variant pickers, price, and
the Add-to-Cart / Buy-It-Now CTAs.

**Key roles:**
| Role | Accessible name / locator |
|---|---|
| `heading` | Item title (`h1`) |
| `text` | Price block (formatted with currency) |
| `combobox` / `listbox` | Variant selectors (e.g. "Size", "Color") |
| `button` | "Add to cart" |
| `button` | "Buy It Now" |
| `text` | Shipping cost, seller, condition |

**Dynamic behaviors:**
- Selecting a variant re-renders price and availability via XHR — wait for
  the new price node, not a fixed delay.
- Add-to-cart can show a drawer overlay ("Added to cart — View cart") or
  navigate to `/cart` depending on A/B bucket (see EDGE_CASES).
- Geo-redirects: visiting from non-US IP may bounce to `ebay.<tld>`; we
  hard-set region via cookie before navigation.
- Some items show "Price unavailable" until a variant is chosen — variants
  are then mandatory.

---

## Cart — `https://www.ebay.com/cart`

**URL pattern:** `/cart`

**Purpose:** Review items pending checkout and read the subtotal we assert
against.

**Key roles:**
| Role | Accessible name / locator |
|---|---|
| `heading` | "Shopping cart" |
| `listitem` | Each cart line |
| `text` | "Subtotal (N items)" with formatted amount |
| `button` | "Remove", "Save for later" |

**Dynamic behaviors:**
- May render as a full page (direct `/cart` nav) or a drawer overlay
  (triggered from item page) — components abstract both.
- Guest access is supported; do not let any flow click "Check out", which
  forces a login interstitial.
- Subtotal updates reactively when items are removed; read it once cart
  state is stable (use `expect(subtotal_locator).to_have_text(...)`).
- Currency badge can shift if an item is priced in a different currency
  than the session; we keep all scenarios USD-only for now.
