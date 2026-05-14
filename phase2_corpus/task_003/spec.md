# Task 003 — Path normalizer

Difficulty: **easy**
Style: hand-authored

## Function to implement

```python
def normalize_path(path: str) -> str:
    ...
```

## Specification

Normalize a Unix-style POSIX path string by resolving `.` and `..`
components and collapsing redundant separators. **Do not use
`os.path.normpath`, `pathlib`, or `posixpath`** — write the resolution
logic directly.

### Rules

- The path uses `/` as separator.
- A leading `/` makes the path absolute. The normalized result of an
  absolute path always starts with `/`.
- A relative path (no leading `/`) stays relative in the result.
- `.` components are removed.
- `..` components remove the preceding component, **except**:
  - In an absolute path, `..` at the root stays at the root.
    `/..` normalizes to `/`. `/../a` normalizes to `/a`.
  - In a relative path, leading `..` components are preserved.
    `../a` normalizes to `../a`. `a/../../b` normalizes to `../b`.
- Multiple consecutive separators collapse: `a//b` → `a/b`.
- Trailing `/` is removed in the result (except for the root `/` itself).
- Empty input returns `"."` (current directory).
- The input is a string, never None.

### Examples

- `normalize_path("/a/b/c")` → `/a/b/c`
- `normalize_path("/a/b/../c")` → `/a/c`
- `normalize_path("/a/./b")` → `/a/b`
- `normalize_path("/a//b///c")` → `/a/b/c`
- `normalize_path("/..")` → `/`
- `normalize_path("../a")` → `../a`
- `normalize_path("a/../../b")` → `../b`
- `normalize_path("")` → `.`
- `normalize_path("/")` → `/`

## Out of scope

- Windows-style paths (backslash separators)
- Symlink resolution (purely lexical)
- Existence checking on filesystem
