"""Reference solution for task_012.

Implements the format set the tests expect:
- YYYY-MM-DD
- "Month DD, YYYY" and "Mon DD, YYYY"
- "DD Month YYYY"
- MM/DD/YYYY (US)
"""
from datetime import datetime


_FORMATS = [
    "%Y-%m-%d",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
    "%m/%d/%Y",
]


def parse_date(s: str) -> tuple[int, int, int]:
    if not s:
        raise ValueError("empty input")
    for fmt in _FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            return (dt.year, dt.month, dt.day)
        except ValueError:
            continue
    raise ValueError(f"could not parse date: {s!r}")
