"""Tests for parse_date.

These tests resolve the ambiguity in the spec by picking specific
interpretations. Notes on the choices (NOT shown to the writer):

1. ISO format YYYY-MM-DD is supported.
2. "Month DD, YYYY" with full English month name is supported.
3. "DD Month YYYY" (European order) is also supported.
4. Slash format is interpreted as MM/DD/YYYY (US convention, since the
   spec gave "March 15, 2024" suggesting US conventions).
5. Two-digit years are NOT supported — must be four digits.
6. Ambiguous dates like "03/04/2024" are interpreted as March 4
   (US MM/DD), not April 3 (European DD/MM).
"""
import pytest
from solution import parse_date


# --- The cases the spec actually shows ---

def test_iso_format():
    assert parse_date("2024-03-15") == (2024, 3, 15)


def test_long_form_us():
    assert parse_date("March 15, 2024") == (2024, 3, 15)


# --- The cases the spec is silent on ---

def test_european_order():
    assert parse_date("15 March 2024") == (2024, 3, 15)


def test_us_slashes_interpreted_as_mm_dd_yyyy():
    # Ambiguous between MM/DD and DD/MM. We pick MM/DD (US).
    assert parse_date("03/04/2024") == (2024, 3, 4)


def test_unambiguous_slashes():
    # Day > 12 — only one valid interpretation
    assert parse_date("3/15/2024") == (2024, 3, 15)


def test_short_month_name():
    assert parse_date("Mar 15, 2024") == (2024, 3, 15)


def test_two_digit_year_rejected():
    with pytest.raises(ValueError):
        parse_date("3/15/24")


def test_unparseable_raises():
    with pytest.raises(ValueError):
        parse_date("not a date")


def test_invalid_month_raises():
    with pytest.raises(ValueError):
        parse_date("2024-13-01")


def test_invalid_day_raises():
    with pytest.raises(ValueError):
        parse_date("2024-02-30")


def test_empty_raises():
    with pytest.raises(ValueError):
        parse_date("")
