import re
from decimal import Decimal

# Matches a $-, ILS-, ₪-, or NIS-anchored amount. eBay shows ILS prices
# in three forms on different surfaces: "ILS 356.56" on the SRP, "₪
# 332.48" on the cart page (Unicode shekel sign U+20AA), and "NIS …"
# occasionally on legacy widgets. The $-form is retained for
# USD-localized runs and cart copy that still uses "$". See README
# §Currency and atlas/EDGE_CASES.md.
_PRICE_AMOUNT = re.compile(
    r"(?:\$|ILS|₪|NIS)\s*(-?\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
)


def parse_price(text: str) -> Decimal:
    """Parse a displayed price string into a ``Decimal``.

    Handles the formats listed in atlas/EDGE_CASES.md (currency parsing):

        "$25.00"                    → Decimal("25.00")
        "$25"                       → Decimal("25")
        "US $25.00"                 → Decimal("25.00")
        "$1,234.56"                 → Decimal("1234.56")
        "ILS 356.56"                → Decimal("356.56")
        "ILS 1,486.79"              → Decimal("1486.79")
        "₪332.48"                   → Decimal("332.48")  (cart page)
        "₪ 1,486.79"                → Decimal("1486.79")
        "Subtotal ₪332.48"          → Decimal("332.48")
        "ILS 25 to ILS 30"          → Decimal("25")     (lower bound)
        "$25.00 to $30.00"          → Decimal("25.00")  (lower bound)
        "Subtotal (3 items) $50.00" → Decimal("50.00")  (currency anchor
                                                         wins over the
                                                         count)

    The parser **requires** a ``$`` or ``ILS`` anchor — every locator
    that feeds this function (``ResultCard.price_text``,
    ``ItemPage.price``, ``CartPage.subtotal``) returns text containing
    one. Bare numerics like ``"3d 4h"`` or ``"Auction ended"`` raise
    ``ValueError`` rather than silently returning a misleading number.

    Never coerces through ``float``.
    """
    match = _PRICE_AMOUNT.search(text)
    if match is None:
        raise ValueError(f"no numeric value found in price text: {text!r}")
    return Decimal(match.group(1).replace(",", ""))
