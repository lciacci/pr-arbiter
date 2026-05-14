"""Reference solution for task_003."""


def normalize_path(path: str) -> str:
    if not path:
        return "."
    is_absolute = path.startswith("/")
    parts = [p for p in path.split("/") if p]  # drops empty from consecutive `/`
    stack: list[str] = []
    for p in parts:
        if p == ".":
            continue
        if p == "..":
            if stack and stack[-1] != "..":
                stack.pop()
            elif not is_absolute:
                stack.append("..")
            # else: absolute path, dotdot at root — ignore
        else:
            stack.append(p)
    if is_absolute:
        return "/" + "/".join(stack)
    return "/".join(stack) if stack else "."
