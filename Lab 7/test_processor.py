"""Hypothesis fuzz tests for processor.py (Lab 7).

Contract being tested for every function:
  * valid input            -> documented return value
  * non-str input          -> TypeError
  * malformed str input    -> ValueError
  * any OTHER exception type (IndexError, KeyError, AttributeError,
    OverflowError, ...) is a bug: it means input validation was skipped.
"""
import math
import string

import pytest
from hypothesis import given, strategies as st

from processor import (
    calculate_seat_tier_price,
    decode_promo_voucher,
    parse_attendee_badge,
)

# ------------------------------------------------- contract limits (the spec)
MAX_ROW = 1000   # seat rows are 0..1000
MAX_AGE = 150    # attendee ages are 0..150
ADULT_AGE = 18   # age < 18 -> Child
BASE = {"VIP": 150.0, "PREMIUM": 90.0, "GENERAL": 45.0}

# ---------------------------------------------------------------- strategies
# Inputs the handout asks for: arbitrary text or None.
text_or_none = st.text() | st.none()

# Non-string values of assorted types (must be rejected with TypeError).
non_strings = st.one_of(
    st.none(), st.integers(), st.floats(), st.booleans(), st.binary(),
    st.lists(st.integers()), st.dictionaries(st.text(), st.integers()),
    st.tuples(st.text()),
)

# Whitespace that str.strip() removes; used to pad otherwise-valid input.
padding = st.text(alphabet=" \t\r\n", max_size=4)
word = st.text(alphabet=string.ascii_letters + string.digits, min_size=1, max_size=20)
non_digit_text = st.text().filter(lambda s: not (s.strip().isascii() and s.strip().isdigit()))
name_chars = st.text(
    st.characters(blacklist_characters=",",
                  blacklist_categories=("Cs", "Cc", "Zs", "Zl", "Zp")),
    min_size=1, max_size=30)


# ------------------------------------------------------ decode_promo_voucher
@given(text_or_none)
def test_decode_promo_voucher_no_crash(s):
    """Any str/None either yields a str or raises only the documented errors."""
    try:
        result = decode_promo_voucher(s)
    except (ValueError, TypeError):
        return  # deterministic, documented rejection
    assert isinstance(result, str)


@given(non_strings)
def test_decode_promo_voucher_rejects_non_strings(value):
    with pytest.raises(TypeError):
        decode_promo_voucher(value)


@given(padding, word, st.integers(0, 100), padding)
def test_decode_promo_voucher_valid_roundtrip(pad, prefix, pct, pad2):
    """Valid vouchers (surrounding whitespace allowed) decode exactly."""
    out = decode_promo_voucher(f"{pad}{prefix}-{pct}{pad2}")
    assert out == f"Valid {prefix.upper()}: {pct}% OFF"


@given(st.text(alphabet=string.ascii_letters + "-", max_size=20)
       .filter(lambda s: s.strip().count("-") != 1))
def test_decode_promo_voucher_wrong_separator_count(s):
    """Zero or several '-' separators is malformed -> ValueError, not unpack error."""
    with pytest.raises(ValueError):
        decode_promo_voucher(s)


@given(word, st.one_of(st.integers(101, 10**30), st.integers(max_value=-1)))
def test_decode_promo_voucher_percentage_out_of_range(prefix, pct):
    """A discount must be 0-100%; negative (extra '-') or >100 is rejected."""
    with pytest.raises(ValueError):
        decode_promo_voucher(f"{prefix}-{pct}")


@given(word, non_digit_text.filter(lambda s: "-" not in s))
def test_decode_promo_voucher_non_numeric_percentage(prefix, pct):
    """Letters, '+5', '1_0', unicode digits, floats and empty are not valid percentages."""
    with pytest.raises(ValueError):
        decode_promo_voucher(f"{prefix}-{pct}")


@given(padding, st.integers(0, 100))
def test_decode_promo_voucher_empty_prefix(pad, pct):
    with pytest.raises(ValueError):
        decode_promo_voucher(f"{pad}-{pct}")


@given(st.sampled_from([0, 100]))
def test_decode_promo_voucher_boundaries(pct):
    assert decode_promo_voucher(f"X-{pct}") == f"Valid X: {pct}% OFF"


# -------------------------------------------------- calculate_seat_tier_price
@given(text_or_none)
def test_calculate_seat_tier_price_safe(s):
    """Any str/None yields a finite non-negative float or a documented error."""
    try:
        price = calculate_seat_tier_price(s)
    except (ValueError, TypeError):
        return
    assert isinstance(price, float) and math.isfinite(price) and price >= 0


@given(non_strings)
def test_calculate_seat_tier_price_rejects_non_strings(value):
    with pytest.raises(TypeError):
        calculate_seat_tier_price(value)


@given(padding, st.sampled_from(sorted(BASE)), st.booleans(), padding,
       st.integers(0, MAX_ROW), padding)
def test_calculate_seat_tier_price_valid(pad, tier, upper, pad2, row, pad3):
    """price == base rate + 2.0 * row; tier name is case-insensitive."""
    t = tier if upper else tier.lower()
    price = calculate_seat_tier_price(f"{pad}{t}{pad2}@{row}{pad3}")
    assert price == BASE[tier] + 2.0 * row


@given(st.text(max_size=12).filter(lambda s: s.strip().upper() not in BASE),
       st.integers(0, MAX_ROW))
def test_calculate_seat_tier_price_unknown_tier(tier, row):
    """Unknown tiers must raise ValueError, not a raw KeyError."""
    with pytest.raises(ValueError):
        calculate_seat_tier_price(f"{tier.replace('@', '')}@{row}")


@given(st.sampled_from(sorted(BASE)),
       st.one_of(st.integers(max_value=-1), st.integers(MAX_ROW + 1, 10**400)))
def test_calculate_seat_tier_price_row_out_of_range(tier, row):
    """Negative rows would discount the price; huge rows overflow float() -> reject."""
    with pytest.raises(ValueError):
        calculate_seat_tier_price(f"{tier}@{row}")


@given(st.sampled_from(sorted(BASE)), non_digit_text.filter(lambda s: "@" not in s))
def test_calculate_seat_tier_price_non_numeric_row(tier, row):
    with pytest.raises(ValueError):
        calculate_seat_tier_price(f"{tier}@{row}")


@given(st.text(alphabet=string.digits, max_size=10), st.sampled_from([0, 2, 3]))
def test_calculate_seat_tier_price_wrong_at_count(body, extra_at):
    """Missing '@' (IndexError originally) or extra '@' (silently ignored) -> ValueError."""
    s = "VIP" if extra_at == 0 else "@".join(["VIP"] + ["1"] * extra_at) + body
    with pytest.raises(ValueError):
        calculate_seat_tier_price(s)


@given(st.sampled_from(sorted(BASE)), st.sampled_from([0, MAX_ROW]))
def test_calculate_seat_tier_price_boundaries(tier, row):
    assert calculate_seat_tier_price(f"{tier}@{row}") == BASE[tier] + 2.0 * row


# ------------------------------------------------------ parse_attendee_badge
@given(text_or_none)
def test_parse_attendee_badge_safe(s):
    """Any str/None yields a str or raises only the documented errors."""
    try:
        result = parse_attendee_badge(s)
    except (ValueError, TypeError):
        return
    assert isinstance(result, str)


@given(non_strings)
def test_parse_attendee_badge_rejects_non_strings(value):
    with pytest.raises(TypeError):
        parse_attendee_badge(value)


@given(name_chars, st.integers(0, MAX_AGE), name_chars)
def test_parse_attendee_badge_valid(name, age, seat):
    """Valid badge -> '<name> [Child|Adult] - Seat <seat>'; fields are stripped."""
    category = "Child" if age < ADULT_AGE else "Adult"
    assert parse_attendee_badge(f" {name} , {age} , {seat} ") == \
        f"{name} [{category}] - Seat {seat}"


@given(name_chars, name_chars, st.sampled_from([ADULT_AGE - 1, ADULT_AGE]))
def test_parse_attendee_badge_age_boundary(name, seat, age):
    expected = "Child" if age == ADULT_AGE - 1 else "Adult"
    assert f"[{expected}]" in parse_attendee_badge(f"{name},{age},{seat}")


@given(st.lists(st.text(alphabet=string.ascii_letters + string.digits + " ", max_size=8),
                max_size=6).filter(lambda parts: len(parts) != 3))
def test_parse_attendee_badge_wrong_field_count(parts):
    """Fewer than 3 fields (IndexError originally) or extra fields -> ValueError."""
    with pytest.raises(ValueError):
        parse_attendee_badge(",".join(parts))


@given(name_chars, name_chars,
       st.one_of(st.integers(max_value=-1), st.integers(MAX_AGE + 1, 10**30)))
def test_parse_attendee_badge_age_out_of_range(name, seat, age):
    with pytest.raises(ValueError):
        parse_attendee_badge(f"{name},{age},{seat}")


@given(name_chars, name_chars, non_digit_text.filter(lambda s: "," not in s))
def test_parse_attendee_badge_non_numeric_age(name, seat, age):
    with pytest.raises(ValueError):
        parse_attendee_badge(f"{name},{age},{seat}")


@given(st.sampled_from(["", " ", "\t"]), name_chars, st.integers(0, MAX_AGE))
def test_parse_attendee_badge_blank_name_or_seat(blank, other, age):
    """Whitespace-only name or seat is not a usable badge."""
    with pytest.raises(ValueError):
        parse_attendee_badge(f"{blank},{age},{other}")
    with pytest.raises(ValueError):
        parse_attendee_badge(f"{other},{age},{blank}")
