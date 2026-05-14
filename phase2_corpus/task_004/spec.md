# Task 004 — Flatten nested lists with depth limit

Difficulty: **easy**
Style: HumanEval-shaped (modified: added depth parameter)

## Function to implement

```python
def flatten(items: list, depth: int = -1) -> list:
    ...
```

## Specification

Flatten a nested list of arbitrary depth, optionally limited to a
maximum flattening depth.

- `items` is a list. Elements may be lists themselves, or any other
  value (strings, ints, dicts, None, etc.).
- `depth` controls how many levels to flatten:
  - `depth=-1` (default): fully flatten — recurse until no inner lists remain.
  - `depth=0`: return the input unchanged (a shallow copy).
  - `depth=1`: flatten one level only.
  - `depth=k`: flatten up to k levels deep.
- **Only `list` is flattened.** Tuples, strings, sets, generators, and
  dicts are treated as atomic values and never expanded — even though
  strings and tuples are iterable. `flatten(["ab"])` returns `["ab"]`,
  not `["a", "b"]`.
- The input list is not mutated.
- An empty list returns an empty list.

### Examples

- `flatten([1, [2, 3], [4, [5, 6]]])` → `[1, 2, 3, 4, 5, 6]`
- `flatten([1, [2, [3, [4]]]], depth=1)` → `[1, 2, [3, [4]]]`
- `flatten([1, [2, [3, [4]]]], depth=2)` → `[1, 2, 3, [4]]`
- `flatten([1, [2, 3]], depth=0)` → `[1, [2, 3]]`
- `flatten([])` → `[]`
- `flatten(["a", ["b", "c"]])` → `["a", "b", "c"]`  (strings are atomic)
- `flatten([(1, 2), [3]])` → `[(1, 2), 3]`  (tuples are atomic)

## Out of scope

- Flattening non-list iterables (generators, tuples, sets)
- Negative depths other than -1 (no need to handle -2, -3, etc.)
