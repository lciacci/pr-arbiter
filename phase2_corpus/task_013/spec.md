# Task 013 — Normalize whitespace

Difficulty: **underspec**
Style: hand-authored

## Function to implement

```python
def normalize_whitespace(s: str) -> str:
    """Clean up whitespace in a string."""
    ...
```

## Specification

Take a string with messy whitespace and return a cleaner version.

## Examples

- `normalize_whitespace("  hello   world  ")` → `"hello world"`
- `normalize_whitespace("line one\n\n\nline two")` → `"line one\nline two"`
