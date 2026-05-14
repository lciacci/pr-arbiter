"""Tests for parse_query_string."""
import pytest
from solution import parse_query_string


def test_single_pair():
    assert parse_query_string("a=1") == {"a": ["1"]}


def test_multiple_pairs():
    assert parse_query_string("a=1&b=2") == {"a": ["1"], "b": ["2"]}


def test_repeated_key_collects_into_list():
    assert parse_query_string("a=1&a=2&a=3") == {"a": ["1", "2", "3"]}


def test_repeated_key_preserves_order():
    # Order of appearance must be preserved
    result = parse_query_string("k=c&k=a&k=b")
    assert result["k"] == ["c", "a", "b"]


def test_empty_value():
    assert parse_query_string("a=") == {"a": [""]}


def test_key_without_equals():
    assert parse_query_string("flag") == {"flag": [""]}


def test_empty_input():
    assert parse_query_string("") == {}


def test_percent_decoding_in_value():
    assert parse_query_string("name=Lorenzo%20Ciacci") == {"name": ["Lorenzo Ciacci"]}


def test_percent_decoding_in_key():
    assert parse_query_string("my%20key=val") == {"my key": ["val"]}


def test_plus_decoded_to_space():
    assert parse_query_string("q=hello+world") == {"q": ["hello world"]}


def test_stray_ampersands_ignored():
    assert parse_query_string("&a=1&&b=2&") == {"a": ["1"], "b": ["2"]}


def test_value_contains_equals_sign():
    # An `=` inside a value should not split the pair again — split on FIRST `=` only
    assert parse_query_string("expr=1=2") == {"expr": ["1=2"]}


def test_mixed_encoded_and_repeated():
    result = parse_query_string("tag=python&tag=web%20dev&tag=async+io")
    assert result == {"tag": ["python", "web dev", "async io"]}
