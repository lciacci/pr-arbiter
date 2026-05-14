"""Tests for evaluate."""
import pytest
from solution import evaluate


# --- simple comparisons ---

def test_eq():
    assert evaluate("age == 18", {"age": 18}) is True
    assert evaluate("age == 18", {"age": 19}) is False


def test_ne():
    assert evaluate("age != 18", {"age": 19}) is True
    assert evaluate("age != 18", {"age": 18}) is False


def test_gt_lt():
    assert evaluate("age > 10", {"age": 11}) is True
    assert evaluate("age < 10", {"age": 5}) is True


def test_gte_lte():
    assert evaluate("age >= 18", {"age": 18}) is True
    assert evaluate("age <= 18", {"age": 18}) is True


def test_string_comparison():
    assert evaluate("name == 'Lorenzo'", {"name": "Lorenzo"}) is True
    assert evaluate("name != 'Lo'", {"name": "Lorenzo"}) is True


def test_float_value():
    assert evaluate("ratio > 0.5", {"ratio": 0.75}) is True


def test_negative_value():
    assert evaluate("temp < 0", {"temp": -5}) is True


# --- logical operators ---

def test_and():
    assert evaluate("age >= 18 AND age < 65", {"age": 21}) is True
    assert evaluate("age >= 18 AND age < 65", {"age": 70}) is False


def test_or():
    assert evaluate("name == 'Lorenzo' OR name == 'Lo'", {"name": "Lo"}) is True
    assert evaluate("name == 'Lorenzo' OR name == 'Lo'", {"name": "X"}) is False


def test_not():
    assert evaluate("NOT (status == 'banned')", {"status": "active"}) is True
    assert evaluate("NOT (status == 'banned')", {"status": "banned"}) is False


def test_precedence_and_over_or():
    # a == 1 OR b == 2 AND c == 3   →   a == 1 OR (b == 2 AND c == 3)
    # With a=0, b=2, c=3 → False OR (True AND True) → True
    assert evaluate("a == 1 OR b == 2 AND c == 3", {"a": 0, "b": 2, "c": 3}) is True
    # With a=0, b=2, c=99 → False OR (True AND False) → False
    assert evaluate("a == 1 OR b == 2 AND c == 3", {"a": 0, "b": 2, "c": 99}) is False


def test_parens_override_precedence():
    # (a == 1 OR b == 2) AND c == 3
    # With a=0, b=2, c=99 → True AND False → False
    assert evaluate("(a == 1 OR b == 2) AND c == 3", {"a": 0, "b": 2, "c": 99}) is False
    # With a=1, b=9, c=3 → True AND True → True
    assert evaluate("(a == 1 OR b == 2) AND c == 3", {"a": 1, "b": 9, "c": 3}) is True


def test_double_not():
    assert evaluate("NOT NOT a == 1", {"a": 1}) is True


# --- error handling ---

def test_missing_field_raises_keyerror():
    with pytest.raises(KeyError):
        evaluate("age > 10", {"name": "x"})


def test_type_mismatch_raises_typeerror():
    with pytest.raises(TypeError):
        evaluate("age == 'eighteen'", {"age": 18})


def test_unmatched_paren_raises_valueerror():
    with pytest.raises(ValueError):
        evaluate("(a == 1", {"a": 1})


def test_garbage_input_raises_valueerror():
    with pytest.raises(ValueError):
        evaluate("&&& ??? !!!", {"a": 1})


def test_empty_expression_raises_valueerror():
    with pytest.raises(ValueError):
        evaluate("", {"a": 1})


# --- whitespace ---

def test_extra_whitespace_ok():
    assert evaluate("  age   >=   18  ", {"age": 21}) is True


def test_no_extra_whitespace_around_parens():
    assert evaluate("(a==1)AND(b==2)", {"a": 1, "b": 2}) is True
