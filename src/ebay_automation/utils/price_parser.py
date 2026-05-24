import re
from decimal import Decimal

# Matches either a $-anchored amount or an ILS-anchored amount. The
# tests in this suite run against eBay's ILS-localized SRP (see README
# §"Currency"); the $-form is retained so the parser stays useful on
# USD-localized runs and on cart copy that still says "$".
_PRICE_AMOUNT = re.compile(
    r"(?:\$|ILS)\s*(-?\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
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
