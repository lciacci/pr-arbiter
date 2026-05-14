# Task 012 — Parse a date string

Difficulty: **underspec**
Style: hand-authored

## Function to implement

```python
def parse_date(s: str) -> tuple[int, int, int]:
    """Parse a date string and return (year, month, day)."""
    ...
```

## Specification

Parse a human-readable date string into a `(year, month, day)` tuple.

The function should be robust to common formats users might type.
Return values as integers. Raise `ValueError` for input that cannot
be parsed as a date.

## Examples

- `parse_date("2024-03-15")` → `(2024, 3, 15)`
- `parse_date("March 15, 2024")` → `(2024, 3, 15)`
