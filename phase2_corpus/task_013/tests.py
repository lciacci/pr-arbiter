"""Tests for normalize_whitespace.

Choices the spec is silent on (NOT shown to writer):

1. Multiple spaces/tabs within a line collapse to a SINGLE space.
2. Leading/trailing whitespace per LINE is stripped.
3. Multiple consecutive newlines collapse to a SINGLE newline (no
   preservation of blank paragraphs).
4. Tabs are treated as whitespace (collapsed with spaces), not converted
   to 4 or 8 spaces.
5. Trailing newline at end of the entire string is removed.
6. The result of a string that is ENTIRELY whitespace is the empty string.
7. Unicode whitespace (non-breaking space, etc.) is NOT specially handled —
   only ASCII space, tab, newline, and \\r are normalized. \\xa0
   (non-breaking space) is preserved as-is.
8. \\r\\n and \\r are normalized to \\n.
"""
import pytest
from solution import normalize_whitespace


# --- The two cases shown in the spec ---

def test_spec_example_inline_spaces():
    assert normalize_whitespace("  hello   world  ") == "hello world"


def test_spec_example_blank_lines():
    assert normalize_whitespace("line one\n\n\nline two") == "line one\nline two"


# --- Within-line behavior ---

def test_tabs_collapse_with_spaces():
    assert normalize_whitespace("a\t\tb") == "a b"


def test_mixed_tabs_and_spaces():
    assert normalize_whitespace("a \t  \tb") == "a b"


def test_single_space_unchanged():
    assert normalize_whitespace("a b") == "a b"


# --- Per-line trim ---

def test_leading_whitespace_per_line_stripped():
    assert normalize_whitespace("  line one\n  line two") == "line one\nline two"


def test_trailing_whitespace_per_line_stripped():
    assert normalize_whitespace("line one  \nline two  ") == "line one\nline two"


# --- Newline collapse ---

def test_two_newlines_collapse():
    assert normalize_whitespace("a\n\nb") == "a\nb"


def test_many_newlines_collapse():
    assert normalize_whitespace("a\n\n\n\n\nb") == "a\nb"


def test_newlines_with_whitespace_between_collapse():
    # "a\n   \nb" — the middle "line" is whitespace-only, so it
    # becomes an empty line, which then collapses.
    assert normalize_whitespace("a\n   \nb") == "a\nb"


# --- CRLF handling ---

def test_crlf_normalized():
    assert normalize_whitespace("a\r\nb") == "a\nb"


def test_lone_cr_normalized():
    assert normalize_whitespace("a\rb") == "a\nb"


# --- Edge cases ---

def test_empty_string():
    assert normalize_whitespace("") == ""


def test_only_whitespace():
    assert normalize_whitespace("   \t\n\n  ") == ""


def test_trailing_newline_removed():
    assert normalize_whitespace("hello\n") == "hello"


def test_no_leading_newline_added():
    assert normalize_whitespace("\nhello") == "hello"


# --- Unicode is left alone ---

def test_nbsp_preserved():
    # \xa0 is a non-breaking space; not in our normalization set.
    assert normalize_whitespace("a\xa0b") == "a\xa0b"
