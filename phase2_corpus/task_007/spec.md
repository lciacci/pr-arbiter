# Task 007 — JSON path resolver

Difficulty: **medium**
Style: HumanEval-shaped (modified: added edge cases and error semantics)

## Function to implement

```python
def get_path(obj, path: str, default=...):
    ...
```

## Specification

Read a value out of a nested JSON-like Python structure using a
dot-and-bracket path expression.

- `obj` is a dict, list, or scalar (str/int/float/bool/None).
- `path` is a string like `"users.0.name"` or `"users[0].name"`.
- The path may mix dot notation and bracket notation: `"a.b[2].c"` is valid.
- Dict keys are referenced by name. List indices are referenced by integer.
- Negative list indices are NOT supported. `"a.-1"` should be treated as
  the literal key `"-1"` (not as a list-from-end index).
- Whitespace inside path components is significant: `"a .b"` is asking
  for the key `"a "` followed by `"b"`. Don't trim.

### Behavior

- Returns the resolved value on success.
- On any failure (missing key, missing index, type mismatch like indexing
  a string with a dict key), returns `default` if provided, else raises
  `KeyError` (for dicts) or `IndexError` (for lists) or `TypeError` (for
  scalar traversal).
- An empty path returns `obj` itself.
- A path component that LOOKS like an integer (e.g., `"0"`) is treated as
  a list index when the current object is a list, and as a string key when
  the current object is a dict. So `get_path({"0": "x"}, "0")` returns
  `"x"`, while `get_path(["x"], "0")` also returns `"x"`.

### Examples

- `get_path({"a": {"b": 1}}, "a.b")` → `1`
- `get_path({"users": [{"name": "Lo"}]}, "users[0].name")` → `"Lo"`
- `get_path({"users": [{"name": "Lo"}]}, "users.0.name")` → `"Lo"`
- `get_path({"a": 1}, "a.b", default=None)` → `None`
- `get_path({"a": 1}, "missing")` → raises `KeyError`
- `get_path([1, 2, 3], "5", default="x")` → `"x"`
- `get_path({"a": 1}, "")` → `{"a": 1}`

## Out of scope

- Wildcards (`a.*.b`)
- Filter expressions (`a[?b==1]`)
- Negative indexing
- Escaped brackets/dots inside path components
