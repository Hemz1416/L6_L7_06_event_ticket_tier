"""Event-ticket input processing.

Contract shared by every public function:
  * non-str input        -> TypeError
  * malformed str input  -> ValueError (with a descriptive message)
  * valid input          -> documented return value
"""

MAX_PERCENT = 100
MAX_ROW = 1000
MAX_AGE = 150
ADULT_AGE = 18

TIER_RATES = {
    "VIP": 150.0,
    "PREMIUM": 90.0,
    "GENERAL": 45.0,
}
ROW_PRICE_STEP = 2.0


def _require_str(value, label):
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a str, got {type(value).__name__}")
    return value


def _parse_bounded_int(text, label, low, high):
    """Parse plain ASCII digits (no sign, spaces, '_' or non-ASCII digits)
    and check low <= value <= high. Length is checked first so absurdly long
    digit strings are rejected without a big-int conversion."""
    text = text.strip()
    if not (text.isascii() and text.isdigit()):
        raise ValueError(f"{label} must be a whole number, got {text!r}")
    if len(text.lstrip("0")) > len(str(high)):
        raise ValueError(f"{label} must be between {low} and {high}")
    value = int(text)
    if not low <= value <= high:
        raise ValueError(f"{label} must be between {low} and {high}, got {value}")
    return value


def decode_promo_voucher(voucher_code):
    """'PREFIX-PCT' -> 'Valid PREFIX: PCT% OFF' (PCT is 0-100)."""
    code = _require_str(voucher_code, "voucher_code").strip()
    parts = code.split('-')
    if len(parts) != 2:
        raise ValueError(f"voucher must look like PREFIX-PERCENT, got {code!r}")
    prefix, pct_str = parts[0].strip(), parts[1]
    if not prefix:
        raise ValueError("voucher prefix must not be empty")
    percentage = _parse_bounded_int(pct_str, "voucher percentage", 0, MAX_PERCENT)
    return f"Valid {prefix.upper()}: {percentage}% OFF"


def calculate_seat_tier_price(tier_spec):
    """'TIER@ROW' -> base rate of the tier + 2.0 per row (ROW is 0-1000)."""
    spec = _require_str(tier_spec, "tier_spec")
    parts = spec.split('@')
    if len(parts) != 2:
        raise ValueError(f"tier spec must look like TIER@ROW, got {spec!r}")
    tier = parts[0].strip().upper()
    if tier not in TIER_RATES:
        raise ValueError(f"unknown tier {tier!r}; expected one of {sorted(TIER_RATES)}")
    row = _parse_bounded_int(parts[1], "seat row", 0, MAX_ROW)
    return TIER_RATES[tier] + (row * ROW_PRICE_STEP)


def parse_attendee_badge(badge_csv):
    """'Name,Age,Seat' -> 'Name [Child|Adult] - Seat X' (Age is 0-150)."""
    csv = _require_str(badge_csv, "badge_csv")
    tokens = csv.split(',')
    if len(tokens) != 3:
        raise ValueError(f"badge must have exactly 3 fields (Name,Age,Seat), got {len(tokens)}")
    name = tokens[0].strip()
    seat = tokens[2].strip()
    if not name:
        raise ValueError("badge name must not be empty")
    if not seat:
        raise ValueError("badge seat must not be empty")
    age = _parse_bounded_int(tokens[1], "attendee age", 0, MAX_AGE)
    category = "Child" if age < ADULT_AGE else "Adult"
    return f"{name} [{category}] - Seat {seat}"


def _show(label, func, raw):
    """Print func(raw); report rejected input instead of crashing."""
    try:
        print(label, func(raw))
    except (ValueError, TypeError) as exc:
        print(f"Invalid input: {exc}")


def main():
    print("==== Running decode_promo_voucher ====")
    _show("Voucher:", decode_promo_voucher, input("Enter voucher (e.g. EARLY-20): "))

    print("\n==== Running calculate_seat_tier_price ====")
    _show("Seat Price: $", calculate_seat_tier_price, input("Enter tier spec (e.g. VIP@4): "))

    print("\n==== Running parse_attendee_badge ====")
    _show("Badge:", parse_attendee_badge, input("Enter badge CSV (Name,Age,Seat): "))

if __name__ == "__main__":
    main()
