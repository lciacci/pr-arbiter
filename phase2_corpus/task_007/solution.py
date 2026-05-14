"""Reference solution for task_007."""
import re

_SENTINEL = object()


def _parse_path(path: str) -> list[str]:
    """Tokenize 'a.b[0].c' into ['a', 'b', '0', 'c']."""
    if not path:
        return []
    # Replace [n] with .n, then split on dot. Whitespace preserved.
    transformed = re.sub(r"\[([^\]]*)\]", r".\1", path)
    # Now split on dots, but only top-level ones
    parts = transformed.split(".")
    # The leading dot from [n] at start could produce empty first part; drop only that case
    if parts and parts[0] == "" and path.startswith("["):
        parts = parts[1:]
    return parts


def get_path(obj, path: str, default=_SENTINEL):
    parts = _parse_path(path)
    current = obj
    for part in parts:
        try:
            if isinstance(current, list):
                # Must be a valid non-negative integer
                if part.lstrip("-").isdigit() is False or part.startswith("-"):
                    if default is _SENTINEL:
                        raise IndexError(f"invalid list index: {part!r}")
                    return default
                idx = int(part)
                current = current[idx]
            elif isinstance(current, dict):
                current = current[part]
            else:
                if default is _SENTINEL:
                    raise TypeError(
                        f"cannot traverse into {type(current).__name__} with key {part!r}"
                    )
                return default
        except (KeyError, IndexError, TypeError):
            if default is _SENTINEL:
                raise
            return default
    return current
