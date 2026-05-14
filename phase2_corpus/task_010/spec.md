# Task 010 — Simple filter expression evaluator

Difficulty: **hard**
Style: hand-authored

## Function to implement

```python
def evaluate(expr: str, record: dict) -> bool:
    ...
```

## Specification

Parse and evaluate a simple filter expression against a single record
(a flat dict). Returns True if the record matches.

### Grammar

```
expr     := or_expr
or_expr  := and_expr ("OR" and_expr)*
and_expr := not_expr ("AND" not_expr)*
not_expr := "NOT" not_expr | comparison
comparison := field op value
            | "(" or_expr ")"
op       := "==" | "!=" | ">" | "<" | ">=" | "<="
field    := identifier (letter/digit/underscore, must start with letter)
value    := number | quoted_string
number   := integer or float, optionally negative
quoted_string := single-quoted, e.g., 'foo'
```

Operator precedence (highest first): NOT > AND > OR.
Parentheses override precedence.

### Examples

- `evaluate("age >= 18", {"age": 21})` → `True`
- `evaluate("age >= 18 AND age < 65", {"age": 21})` → `True`
- `evaluate("name == 'Lorenzo' OR name == 'Lo'", {"name": "Lo"})` → `True`
- `evaluate("NOT (status == 'banned')", {"status": "active"})` → `True`
- `evaluate("(a == 1 OR b == 2) AND c == 3", {"a": 1, "b": 9, "c": 3})` → `True`

### Type rules

- Numeric comparison if both sides are numeric (int or float).
- String comparison if both sides are strings.
- Comparison between different types raises `TypeError`.
- A missing field (referenced in the expression but not in `record`)
  raises `KeyError`.

### Whitespace

- Whitespace between tokens is allowed and ignored.
- No whitespace inside identifiers or quoted strings (no need to handle
  escaped quotes — strings cannot contain `'`).

### Errors

- Syntax errors (unmatched parens, missing operator, etc.) raise
  `ValueError` with a message describing the problem.

## Out of scope

- Functions or method calls in expressions
- Double-quoted strings
- Escape sequences in strings
- Comparison operators on multiple fields (`a.b > c.d`) — fields are
  flat dict keys only
- Boolean literals (`true`/`false`)
- Null/None
- Array/list values in records
