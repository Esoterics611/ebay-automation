import re
from decimal import Decimal

_DOLLAR_AMOUNT = re.compile(r"\$\s*(-?\d{1,3}(?:,\d{3})*(?:\.\d+)?)")


def parse_price(text: str) -> Decimal:
    """Parse a displayed price string into a ``Decimal``.

    Handles the formats listed in atlas/EDGE_CASES.md (currency parsing):

        "$25.00"                    → Decimal("25.00")
        "$25"                       → Decimal("25")
        "US $25.00"                 → Decimal("25.00")
        "$1,234.56"                 → Decimal("1234.56")
        "US $1,234.56"              → Decimal("1234.56")
        "$25.00 to $30.00"          → Decimal("25.00")   (lower bound)
        "Subtotal (3 items) $50.00" → Decimal("50.00")   ($ anchor wins
                                                          over the count)

    The parser **requires** a ``$``-anchored amount — every locator that
    feeds this function (``ResultCard.price_text``, ``ItemPage.price``,
    ``CartPage.subtotal``) returns text containing ``$``. Bare numerics
    like ``"3d 4h"`` or ``"Auction ended"`` raise ``ValueError`` rather
    than silently returning a misleading number.

    Never coerces through ``float``.
    """
    match = _DOLLAR_AMOUNT.search(text)
    if match is None:
        raise ValueError(f"no numeric value found in price text: {text!r}")
    return Decimal(match.group(1).replace(",", ""))
