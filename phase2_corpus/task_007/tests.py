"""Tests for get_path."""
import pytest
from solution import get_path


# --- happy path ---

def test_simple_dict_access():
    assert get_path({"a": 1}, "a") == 1


def test_nested_dict():
    assert get_path({"a": {"b": {"c": 5}}}, "a.b.c") == 5


def test_list_index_bracket_notation():
    assert get_path({"xs": [10, 20, 30]}, "xs[1]") == 20


def test_list_index_dot_notation():
    assert get_path({"xs": [10, 20, 30]}, "xs.1") == 20


def test_mixed_dot_and_bracket():
    obj = {"users": [{"name": "Lo"}, {"name": "Cl"}]}
    assert get_path(obj, "users[0].name") == "Lo"
    assert get_path(obj, "users.1.name") == "Cl"


def test_empty_path_returns_obj():
    obj = {"a": 1}
    assert get_path(obj, "") == obj


def test_scalar_at_root():
    assert get_path(42, "") == 42


# --- default values ---

def test_missing_key_with_default():
    assert get_path({"a": 1}, "missing", default=None) is None


def test_out_of_bounds_list_with_default():
    assert get_path([1, 2, 3], "5", default="x") == "x"


def test_traverse_into_scalar_with_default():
    assert get_path({"a": 1}, "a.b", default="fallback") == "fallback"


# --- error cases ---

def test_missing_key_raises():
    with pytest.raises(KeyError):
        get_path({"a": 1}, "missing")


def test_out_of_bounds_list_raises():
    with pytest.raises(IndexError):
        get_path([1, 2], "5")


def test_traverse_into_scalar_raises():
    with pytest.raises(TypeError):
        get_path({"a": 1}, "a.b")


# --- type disambiguation ---

def test_numeric_key_in_dict_is_string_key():
    assert get_path({"0": "value"}, "0") == "value"


def test_numeric_key_in_list_is_index():
    assert get_path(["value"], "0") == "value"


# --- edge cases ---

def test_negative_index_is_treated_as_string_key():
    # On a list, "-1" is NOT last element — should fail (it's not a valid index)
    with pytest.raises((IndexError, ValueError, KeyError)):
        get_path([1, 2, 3], "-1")


def test_whitespace_in_key_is_significant():
    # "a " is a different key from "a"
    obj = {"a ": 1}
    assert get_path(obj, "a ") == 1
    with pytest.raises(KeyError):
        get_path(obj, "a")
