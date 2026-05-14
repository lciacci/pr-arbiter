# Task 008 — Merge overlapping intervals

Difficulty: **medium**
Style: HumanEval-shaped (modified: added touch-vs-overlap distinction)

## Function to implement

```python
def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    ...
```

## Specification

Given a list of `(start, end)` integer intervals, merge any that overlap
and return the resulting list of non-overlapping intervals, sorted by
start.

### Rules

- An interval `(a, b)` means the closed range `[a, b]`. Both endpoints
  are inclusive.
- Two intervals overlap if they share any point. Because intervals are
  closed, `(1, 3)` and `(3, 5)` overlap (they share the point 3) and
  must be merged to `(1, 5)`.
- After merging, return intervals **sorted by start**.
- Input intervals may be given in any order and may overlap arbitrarily.
- An input interval must satisfy `start <= end`. If any interval has
  `start > end`, raise `ValueError`.
- An interval where `start == end` is a single point and is valid.
  `[(3, 3)]` returns `[(3, 3)]`.
- Empty input returns an empty list.
- The output uses tuples, not lists.

### Examples

- `merge_intervals([(1, 3), (2, 6), (8, 10), (15, 18)])` → `[(1, 6), (8, 10), (15, 18)]`
- `merge_intervals([(1, 4), (4, 5)])` → `[(1, 5)]`  (touching counts as overlapping)
- `merge_intervals([(5, 7), (1, 3)])` → `[(1, 3), (5, 7)]`  (sorted by start)
- `merge_intervals([(1, 10), (2, 3), (4, 5)])` → `[(1, 10)]`  (one contains others)
- `merge_intervals([(3, 3)])` → `[(3, 3)]`
- `merge_intervals([])` → `[]`

## Out of scope

- Floating-point endpoints (integers only)
- Open intervals
- Negative-infinity / positive-infinity bounds
