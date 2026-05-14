"""Tests for normalize_path."""
import pytest
from solution import normalize_path


def test_simple_absolute():
    assert normalize_path("/a/b/c") == "/a/b/c"


def test_dotdot_in_absolute():
    assert normalize_path("/a/b/../c") == "/a/c"


def test_dot_removed():
    assert normalize_path("/a/./b") == "/a/b"


def test_collapse_consecutive_separators():
    assert normalize_path("/a//b///c") == "/a/b/c"


def test_dotdot_at_root_stays_at_root():
    assert normalize_path("/..") == "/"


def test_dotdot_past_root_stays_at_root():
    assert normalize_path("/../a") == "/a"


def test_leading_dotdot_preserved_in_relative():
    assert normalize_path("../a") == "../a"


def test_relative_dotdot_escapes_above():
    assert normalize_path("a/../../b") == "../b"


def test_empty_input():
    assert normalize_path("") == "."


def test_root_stays_root():
    assert normalize_path("/") == "/"


def test_trailing_slash_removed():
    assert normalize_path("/a/b/") == "/a/b"


def test_only_dots():
    assert normalize_path("./.") == "."


def test_relative_path_simplifies():
    assert normalize_path("a/./b/../c") == "a/c"


def test_complex_mixed():
    assert normalize_path("/foo/bar/../baz/./qux//") == "/foo/baz/qux"
