"""Order checkout.

The rules live in `src/shop/specs/checkout.md` - read it first.
Do not change the constants: the tests rely on them.
"""

from shop.money import percent_of

PROMO_CODES = {"WELCOME10": 10, "SUMMER15": 15, "VIP35": 35}
SUPPORTED_CITIES = ("msk", "spb")
MAX_DISCOUNT_PERCENT = 30
VAT_PERCENT = 20
SHIPPING_KOPEKS = 49_000
FREE_DELIVERY_FROM_KOPEKS = 500_000
TIER_DISCOUNTS = ((10, 5), (25, 10), (50, 15))
REQUIRED_LINE_KEYS = ("sku", "qty", "unit_price_kopecks")


def _parse_int(text: str) -> int | None:
    """Return `text` as an integer, or None when it is not a whole number."""
    stripped = text.strip()
    digits = stripped[1:] if stripped[:1] in ("+", "-") else stripped
    # Exceptions are not used in this project, so the text is checked before int().
    if not (digits.isascii() and digits.isdigit()):
        return None
    return int(stripped)


def _line_problem(line: dict[str, str], number: int) -> str | None:
    """Return why order line `number` is invalid, or None if it is fine."""
    for key in REQUIRED_LINE_KEYS:
        if key not in line:
            return f"line {number}: key '{key}' is missing"
    if not line["sku"]:
        return f"line {number}: sku must not be empty"
    qty = _parse_int(line["qty"])
    if qty is None:
        return f"line {number}: qty must be a whole number"
    if qty <= 0:
        return f"line {number}: qty must be greater than zero"
    price = _parse_int(line["unit_price_kopecks"])
    if price is None:
        return f"line {number}: unit_price_kopecks must be a whole number"
    if price < 0:
        return f"line {number}: unit_price_kopecks must not be negative"
    return None


def validate_order(
    lines: list[dict[str, str]],
    promo_code: str = "",
    shipping_city: str = "",
) -> str | None:
    """Return a human readable reason why the order is invalid, or None if it is fine."""
    if not lines:
        return "the order has no lines"
    seen: list[str] = []
    for number, line in enumerate(lines, start=1):
        problem = _line_problem(line, number)
        if problem is not None:
            return problem
        if line["sku"] in seen:
            return f"line {number}: sku '{line['sku']}' is repeated"
        seen.append(line["sku"])
    if promo_code and promo_code not in PROMO_CODES:
        return f"unknown promo code '{promo_code}'"
    if shipping_city and shipping_city not in SUPPORTED_CITIES:
        return f"delivery to '{shipping_city}' is not supported"
    return None


def _tier_percent(units: int) -> int:
    """Return the discount of the highest tier that `units` reaches."""
    percent = 0
    for threshold, tier_percent in TIER_DISCOUNTS:
        if units >= threshold:
            percent = max(percent, tier_percent)
    return percent


def calculate_order_total(
    lines: list[dict[str, str]],
    promo_code: str = "",
    shipping_city: str = "",
) -> int | None:
    """Return the order total in kopecks, or None if the order is invalid."""
    if validate_order(lines, promo_code, shipping_city) is not None:
        return None
    subtotal = sum(int(line["qty"]) * int(line["unit_price_kopecks"]) for line in lines)
    units = sum(int(line["qty"]) for line in lines)
    # The tier and the promo code do not add up: the bigger one wins, then the cap.
    percent = max(_tier_percent(units), PROMO_CODES.get(promo_code, 0))
    percent = min(percent, MAX_DISCOUNT_PERCENT)
    discounted = subtotal - percent_of(subtotal, percent)
    shipping = 0
    if shipping_city and discounted < FREE_DELIVERY_FROM_KOPEKS:
        shipping = SHIPPING_KOPEKS
    base = discounted + shipping
    return base + percent_of(base, VAT_PERCENT)
