"""Reference solution for task_010: recursive descent parser + evaluator."""
import re
from typing import Any


# --- Lexer ---

_TOKEN_RE = re.compile(
    r"""
    \s*(?:
        (?P<paren>[()])
      | (?P<op>==|!=|>=|<=|>|<)
      | (?P<number>-?\d+(?:\.\d+)?)
      | (?P<string>'[^']*')
      | (?P<word>[A-Za-z_][A-Za-z0-9_]*)
      | (?P<error>\S)
    )
    """,
    re.VERBOSE,
)


def _tokenize(expr: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    for m in _TOKEN_RE.finditer(expr):
        kind = m.lastgroup
        value = m.group(kind)
        if kind == "error":
            raise ValueError(f"unexpected character: {value!r}")
        tokens.append((kind, value))
    return tokens


# --- Parser ---

class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self):
        tok = self.peek()
        self.pos += 1
        return tok

    def parse(self):
        if not self.tokens:
            raise ValueError("empty expression")
        result = self.parse_or()
        if self.pos != len(self.tokens):
            raise ValueError(f"unexpected token at end: {self.tokens[self.pos]}")
        return result

    def parse_or(self):
        left = self.parse_and()
        while self.peek() and self.peek() == ("word", "OR"):
            self.consume()
            right = self.parse_and()
            left = ("or", left, right)
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.peek() and self.peek() == ("word", "AND"):
            self.consume()
            right = self.parse_not()
            left = ("and", left, right)
        return left

    def parse_not(self):
        if self.peek() == ("word", "NOT"):
            self.consume()
            return ("not", self.parse_not())
        return self.parse_comparison()

    def parse_comparison(self):
        tok = self.peek()
        if tok and tok[0] == "paren" and tok[1] == "(":
            self.consume()
            inner = self.parse_or()
            close = self.consume()
            if close != ("paren", ")"):
                raise ValueError("expected ')'")
            return inner
        # field op value
        field = self.consume()
        if field is None or field[0] != "word":
            raise ValueError(f"expected field name, got {field}")
        op = self.consume()
        if op is None or op[0] != "op":
            raise ValueError(f"expected operator, got {op}")
        value = self.consume()
        if value is None or value[0] not in ("number", "string"):
            raise ValueError(f"expected value, got {value}")
        return ("cmp", field[1], op[1], value)


# --- Evaluator ---

def _coerce_value(token: tuple[str, str]) -> Any:
    kind, raw = token
    if kind == "number":
        return float(raw) if "." in raw else int(raw)
    if kind == "string":
        return raw[1:-1]
    raise ValueError(f"not a literal: {token}")


def _eval(node, record):
    op = node[0]
    if op == "or":
        return _eval(node[1], record) or _eval(node[2], record)
    if op == "and":
        return _eval(node[1], record) and _eval(node[2], record)
    if op == "not":
        return not _eval(node[1], record)
    if op == "cmp":
        _, field, comp, value_tok = node
        if field not in record:
            raise KeyError(field)
        left = record[field]
        right = _coerce_value(value_tok)
        # Type checking
        left_numeric = isinstance(left, (int, float)) and not isinstance(left, bool)
        right_numeric = isinstance(right, (int, float)) and not isinstance(right, bool)
        if left_numeric != right_numeric:
            raise TypeError(f"cannot compare {type(left).__name__} and {type(right).__name__}")
        if isinstance(left, str) != isinstance(right, str):
            raise TypeError(f"cannot compare {type(left).__name__} and {type(right).__name__}")
        return {
            "==": left == right,
            "!=": left != right,
            ">":  left >  right,
            "<":  left <  right,
            ">=": left >= right,
            "<=": left <= right,
        }[comp]
    raise ValueError(f"unknown node: {node}")


def evaluate(expr: str, record: dict) -> bool:
    if not expr or not expr.strip():
        raise ValueError("empty expression")
    tokens = _tokenize(expr)
    if not tokens:
        raise ValueError("empty expression")
    ast = _Parser(tokens).parse()
    return _eval(ast, record)
