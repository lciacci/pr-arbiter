# Task 002 — Roman numeral converter

Difficulty: **easy**
Style: hand-authored

## Functions to implement

```python
def to_roman(n: int) -> str: ...
def from_roman(s: str) -> int: ...
```

## Specification

Convert between integers and Roman numerals, using standard subtractive
notation (e.g., `IV` for 4, `IX` for 9, `XL` for 40).

### `to_roman(n)`
- Input is an integer `1 <= n <= 3999`.
- Output uses uppercase characters from `M D C L X V I`.
- Use subtractive notation for 4, 9, 40, 90, 400, 900.
- For `n` outside the valid range, raise `ValueError`.

### `from_roman(s)`
- Input is a non-empty uppercase Roman numeral string.
- Output is the integer it represents.
- The input is guaranteed to be in *canonical* form (i.e., the form
  produced by `to_roman`). You do not need to accept `IIII` for 4.
- For empty input, input containing non-Roman characters, or input
  that is not canonical, raise `ValueError`.

### Round-trip property

For every valid `n`, `from_roman(to_roman(n)) == n`.

## Out of scope

- Lowercase input
- Non-canonical forms (`IIII`, `VV`, etc.)
- Zero or negative numbers
