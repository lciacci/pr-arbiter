"""Reference solution for task_004."""


def flatten(items: list, depth: int = -1) -> list:
    if depth == 0:
        return list(items)
    out = []
    for item in items:
        if isinstance(item, list):
            if depth == -1:
                out.extend(flatten(item, depth=-1))
            else:
                out.extend(flatten(item, depth=depth - 1))
        else:
            out.append(item)
    return out
