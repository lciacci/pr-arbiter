"""Reference solution for task_002."""

_ROMAN_PAIRS = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]


def to_roman(n: int) -> str:
    if not isinstance(n, int) or n < 1 or n > 3999:
        raise ValueError(f"out of range: {n}")
    out = []
    for value, sym in _ROMAN_PAIRS:
        while n >= value:
            out.append(sym)
            n -= value
    return "".join(out)


def from_roman(s: str) -> int:
    if not s:
        raise ValueError("empty input")
    valid_chars = set("MDCLXVI")
    if not all(c in valid_chars for c in s):
        raise ValueError(f"invalid characters in {s!r}")
    # Parse left to right
    values = {"M": 1000, "D": 500, "C": 100, "L": 50, "X": 10, "V": 5, "I": 1}
    total = 0
    i = 0
    while i < len(s):
        if i + 1 < len(s) and values[s[i]] < values[s[i + 1]]:
            total += values[s[i + 1]] - values[s[i]]
            i += 2
        else:
            total += values[s[i]]
            i += 1
    # Verify canonical form via round-trip
    if to_roman(total) != s:
        raise ValueError(f"non-canonical roman numeral: {s}")
    return total
