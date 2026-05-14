"""Reference solution for task_013."""
import re


def normalize_whitespace(s: str) -> str:
    if not s:
        return ""
    # Normalize CRLF and lone CR to LF
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # Split into lines, strip each, collapse internal whitespace runs
    lines = []
    for line in s.split("\n"):
        # Collapse internal runs of space/tab to single space, then strip
        stripped = re.sub(r"[ \t]+", " ", line).strip(" \t")
        lines.append(stripped)
    # Drop leading and trailing empty lines, collapse runs of empties to one
    # (which effectively becomes a single \n between content lines)
    result = []
    prev_empty = True  # treat start as if preceded by an empty line, so leading empties get dropped
    for line in lines:
        if line == "":
            if not prev_empty:
                # Mark that we've seen an empty line; do not emit it directly —
                # it will manifest as a newline separator only if a non-empty
                # line follows.
                prev_empty = True
        else:
            if result and prev_empty:
                result.append("")  # placeholder for the collapsed empty run
            result.append(line)
            prev_empty = False
    # Now join with \n; the empty-string entries become the blank-line separator
    out = "\n".join(result)
    # Per the rules, blank lines collapse to a single \n separator, so
    # any "\n\n" sequences should become "\n". The construction above
    # actually inserts at most one "" between non-empty lines, so joining
    # gives "a\n\nb" — but the spec wants "a\nb" (single newline).
    out = re.sub(r"\n+", "\n", out)
    return out
