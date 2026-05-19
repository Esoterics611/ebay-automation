import re
from decimal import Decimal

_DOLLAR_AMOUNT = re.compile(r"\$\s*(-?\d{1,3}(?:,\d{3})*(?:\.\d+)?)")
_BARE_AMOUNT = re.compile(r"-?\d{1,3}(?:,\d{3})*(?:\.\d+)?")


def parse_price(text: str) -> Decimal:
    """Parse a displayed price string into a Decimal.

    Handles the formats listed in atlas/EDGE_CASES.md (currency parsing):
        "$19.99"            → Decimal("19.99")
        "US $1,234.56"      → Decimal("1234.56")
        "$10.00 to $25.00"  → Decimal("10.00")   (lower bound per spec)
        "Subtotal (3 items) $50.00" → Decimal("50.00")  ($ anchor wins
                                                         over the count)

    Strategy: prefer the first ``$``-prefixed amount (which excludes item
    counts and other bare integers). Fall back to the first bare number
    only when no ``$`` is present. Never coerces through ``float``.
    """
    match = _DOLLAR_AMOUNT.search(text)
    if match is not None:
        raw = match.group(1)
    else:
        bare = _BARE_AMOUNT.search(text)
        if bare is None:
            raise ValueError(f"no numeric value found in price text: {text!r}")
        raw = bare.group(0)
    return Decimal(raw.replace(",", ""))
