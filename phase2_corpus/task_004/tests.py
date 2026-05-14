"""Tests for flatten."""
import pytest
from solution import flatten


def test_empty_list():
    assert flatten([]) == []


def test_already_flat():
    assert flatten([1, 2, 3]) == [1, 2, 3]


def test_one_level_nested():
    assert flatten([1, [2, 3], 4]) == [1, 2, 3, 4]


def test_deeply_nested_full_flatten():
    assert flatten([1, [2, [3, [4, [5]]]]]) == [1, 2, 3, 4, 5]


def test_depth_zero_returns_shallow_copy():
    src = [1, [2, 3]]
    result = flatten(src, depth=0)
    assert result == [1, [2, 3]]
    assert result is not src  # must be a copy


def test_depth_one():
    assert flatten([1, [2, [3, [4]]]], depth=1) == [1, 2, [3, [4]]]


def test_depth_two():
    assert flatten([1, [2, [3, [4]]]], depth=2) == [1, 2, 3, [4]]


def test_strings_are_atomic():
    assert flatten(["a", ["b", "c"]]) == ["a", "b", "c"]


def test_string_inside_not_split_into_chars():
    # The critical case: "ab" must stay "ab", not become ["a", "b"]
    assert flatten(["ab", "cd"]) == ["ab", "cd"]


def test_tuples_are_atomic():
    assert flatten([(1, 2), [3, 4]]) == [(1, 2), 3, 4]


def test_dicts_are_atomic():
    assert flatten([{"a": 1}, [{"b": 2}]]) == [{"a": 1}, {"b": 2}]


def test_none_values_preserved():
    assert flatten([None, [None, 1]]) == [None, None, 1]


def test_input_not_mutated():
    src = [1, [2, [3]]]
    _ = flatten(src)
    assert src == [1, [2, [3]]]


def test_mixed_types():
    assert flatten([1, "two", [3.0, [True, None]]]) == [1, "two", 3.0, True, None]
