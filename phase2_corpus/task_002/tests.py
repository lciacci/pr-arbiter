"""Tests for Roman numeral converter."""
import pytest
from solution import to_roman, from_roman


# --- to_roman ---

def test_to_roman_one():
    assert to_roman(1) == "I"


def test_to_roman_four_uses_subtractive():
    assert to_roman(4) == "IV"


def test_to_roman_nine_uses_subtractive():
    assert to_roman(9) == "IX"


def test_to_roman_forty():
    assert to_roman(40) == "XL"


def test_to_roman_complex():
    assert to_roman(1994) == "MCMXCIV"
    assert to_roman(3999) == "MMMCMXCIX"
    assert to_roman(58) == "LVIII"


def test_to_roman_rejects_zero():
    with pytest.raises(ValueError):
        to_roman(0)


def test_to_roman_rejects_negative():
    with pytest.raises(ValueError):
        to_roman(-1)


def test_to_roman_rejects_too_large():
    with pytest.raises(ValueError):
        to_roman(4000)


# --- from_roman ---

def test_from_roman_one():
    assert from_roman("I") == 1


def test_from_roman_four():
    assert from_roman("IV") == 4


def test_from_roman_complex():
    assert from_roman("MCMXCIV") == 1994
    assert from_roman("MMMCMXCIX") == 3999


def test_from_roman_rejects_empty():
    with pytest.raises(ValueError):
        from_roman("")


def test_from_roman_rejects_invalid_chars():
    with pytest.raises(ValueError):
        from_roman("ABC")


def test_from_roman_rejects_non_canonical():
    # IIII is not canonical (canonical is IV)
    with pytest.raises(ValueError):
        from_roman("IIII")


# --- round-trip ---

def test_round_trip_all_valid():
    # Spot-check across the range
    for n in [1, 4, 9, 14, 40, 99, 100, 444, 999, 1000, 1984, 3999]:
        assert from_roman(to_roman(n)) == n, f"failed at n={n}"
