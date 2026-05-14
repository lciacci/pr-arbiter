# Task 001 — Query string parser

Difficulty: **easy**
Style: HumanEval-shaped (modified)

## Function to implement

```python
def parse_query_string(qs: str) -> dict[str, list[str]]:
    ...
```

## Specification

Parse a URL query string into a dict mapping each key to a list of its
values.

- Input is the portion of a URL after `?`, without the `?` itself.
  Example: `"a=1&b=2&a=3"`.
- Keys and values are separated by `=`. Pairs are separated by `&`.
- A key may appear multiple times; all its values must be collected
  into the list in order of appearance.
- Values may be empty: `"a="` produces `{"a": [""]}`.
- Keys with no `=` at all are treated as having an empty-string value:
  `"flag"` produces `{"flag": [""]}`.
- An empty input string produces an empty dict.
- Percent-encoded characters in keys and values must be decoded.
  `"name=Lorenzo%20Ciacci"` produces `{"name": ["Lorenzo Ciacci"]}`.
- `+` in values must be decoded to a space (standard form-urlencoded
  behavior). `"q=hello+world"` produces `{"q": ["hello world"]}`.
- Stray `&` characters (leading, trailing, or consecutive) are ignored.
  `"&a=1&&b=2&"` produces `{"a": ["1"], "b": ["2"]}`.

## Out of scope

- You do not need to handle the leading `?`. Caller strips it.
- You do not need to validate that keys are non-empty. Assume keys are
  non-empty when a `=` is present.
- No need to use `urllib.parse` (it's allowed, but the test cases will
  cover the cases above whether you use it or not).
