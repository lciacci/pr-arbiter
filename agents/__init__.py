"""Shared agent helpers."""

from __future__ import annotations

# Map file extension -> markdown fence label. Drives only syntax-highlight
# hinting in the prompt; the agents' system prompts are language-agnostic, so
# an unknown extension (empty label) still reviews fine.
_EXT_FENCE = {
    "py": "python", "js": "javascript", "jsx": "javascript",
    "ts": "typescript", "tsx": "typescript", "java": "java",
    "go": "go", "rs": "rust", "rb": "ruby", "php": "php",
    "c": "c", "h": "c", "cpp": "cpp", "cc": "cpp", "hpp": "cpp",
    "cs": "csharp", "kt": "kotlin", "swift": "swift", "scala": "scala",
    "sh": "bash", "sql": "sql", "html": "html", "css": "css",
    "yaml": "yaml", "yml": "yaml", "json": "json",
}


def lang_fence(path: str) -> str:
    """Fence label for a file path. '' (plain fence) if extension unknown."""
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return _EXT_FENCE.get(ext, "")
