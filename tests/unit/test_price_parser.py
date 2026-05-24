from decimal import Decimal

import pytest

from ebay_automation.utils.price_parser import parse_price


@pytest.mark.parametrize(
    "text, expected",
    [
        # Plain dollar amount
        ("$25.00", Decimal("25.00")),
        ("$0.99", Decimal("0.99")),
        # Without decimals
        ("$25", Decimal("25")),
        # US-prefixed currency
        ("US $25.00", Decimal("25.00")),
        ("US $19.99", Decimal("19.99")),
        # Comma thousands separators
        ("$1,234.56", Decimal("1234.56")),
        ("US $1,234.56", Decimal("1234.56")),
        ("$10,000.00", Decimal("10000.00")),
        # Price range — lower bound per spec
        ("$25.00 to $30.00", Decimal("25.00")),
        ("$10.00 to $25.00", Decimal("10.00")),
        # Cart subtotal — '3 items' must NOT be picked up as the price
        ("Subtotal (3 items) $50.00", Decimal("50.00")),
        ("Subtotal (12 items) US $1,234.50", Decimal("1234.50")),
        # Whitespace tolerance around the $ sign
        ("$ 42.50", Decimal("42.50")),
        # ILS-anchored amounts — eBay localizes SRP price text to the
        # visitor's IP. ILS is the assessment locale (see README §Currency).
        ("ILS 356.56", Decimal("356.56")),
        ("ILS 25", Decimal("25")),
        ("ILS 1,486.79", Decimal("1486.79")),
        ("ILS 25 to ILS 30", Decimal("25")),
        ("+ILS 75.00 delivery", Decimal("75.00")),
    ],
)
def test_parse_price_valid(text: str, expected: Decimal) -> None:
    result = parse_price(text)
    assert result == expected
    assert isinstance(result, Decimal), "parse_price must always return Decimal, never float"


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "no price here",
        "free shipping",
        "Auction ended",
        "Time left: 3d 4h",
    ],
)
def test_parse_price_unparseable_raises(text: str) -> None:
    with pytest.raises(ValueError, match="no numeric value"):
        parse_price(text)


def test_parse_price_returns_decimal_not_float() -> None:
    """Float coercion would corrupt prices like 0.1 + 0.2; ensure the
    parser never drops into float at any stage."""
    result = parse_price("$0.10")
    # Decimal(str) of the parsed digits is exact; Decimal(0.10) (from
    # float) is not. This asserts we took the str path.
    assert result == Decimal("0.10")
    assert result != Decimal(0.10)  # noqa: E721 — that's the point


def test_parse_price_dollar_anchor_beats_bare_integers() -> None:
    """``Subtotal (3 items) $50.00`` would parse as 3 if the regex took
    the first number. The $-anchored pattern must win."""
    assert parse_price("Subtotal (3 items) $50.00") == Decimal("50.00")
    assert parse_price("Subtotal (99 items) $1.00") == Decimal("1.00")


def test_parse_price_requires_dollar_anchor() -> None:
    """Bare numerics without ``$`` are rejected — the parser refuses
    to guess on ambiguous strings like ``"Time left: 3d 4h"`` even
    though they contain digits."""
    with pytest.raises(ValueError, match="no numeric value"):
        parse_price("Price: 12.50")
    with pytest.raises(ValueError, match="no numeric value"):
        parse_price("Quantity: 5")
