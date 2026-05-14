"""Tests for merge_intervals."""
import pytest
from solution import merge_intervals


def test_no_overlap():
    assert merge_intervals([(1, 2), (3, 4), (5, 6)]) == [(1, 2), (3, 4), (5, 6)]


def test_basic_overlap():
    assert merge_intervals([(1, 3), (2, 6), (8, 10), (15, 18)]) == [(1, 6), (8, 10), (15, 18)]


def test_touching_intervals_merge():
    # Closed intervals — (1,4) and (4,5) share point 4
    assert merge_intervals([(1, 4), (4, 5)]) == [(1, 5)]


def test_sorted_output_when_input_unsorted():
    assert merge_intervals([(5, 7), (1, 3)]) == [(1, 3), (5, 7)]


def test_one_interval_contains_others():
    assert merge_intervals([(1, 10), (2, 3), (4, 5)]) == [(1, 10)]


def test_single_point_interval():
    assert merge_intervals([(3, 3)]) == [(3, 3)]


def test_empty_input():
    assert merge_intervals([]) == []


def test_single_interval():
    assert merge_intervals([(1, 5)]) == [(1, 5)]


def test_all_overlap_into_one():
    assert merge_intervals([(1, 5), (2, 6), (3, 7), (4, 8)]) == [(1, 8)]


def test_invalid_interval_raises():
    with pytest.raises(ValueError):
        merge_intervals([(5, 3)])


def test_invalid_interval_in_middle_raises():
    with pytest.raises(ValueError):
        merge_intervals([(1, 2), (5, 3), (8, 10)])


def test_duplicate_intervals():
    assert merge_intervals([(1, 3), (1, 3), (1, 3)]) == [(1, 3)]


def test_output_uses_tuples():
    result = merge_intervals([(1, 3), (2, 4)])
    assert isinstance(result[0], tuple)


def test_adjacent_point_intervals_merge():
    # (3,3) and (3,3) overlap at the single point 3
    assert merge_intervals([(3, 3), (3, 3)]) == [(3, 3)]
