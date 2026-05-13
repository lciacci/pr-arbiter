"""
Reviewer agent: adversarial first-pass code review.

Single Anthropic API call per PR. Tool-use schema for structured output.
Input: dict from load_agent_input() (pr_id, before, after, diff).
Output: list of finding dicts. Includes a rationale field beyond the
rubric shape for the arbiter to consume; the harness ignores extra fields.

The reviewer never sees the rubric, persona, or expected findings.
"""

from __future__ import annotations

from anthropic import Anthropic

# Sonnet 4.6 is the current Sonnet. Kickoff doc referenced 4.5; we're using
# 4.6 because that's the canonical Sonnet ID in the current model lineup.
# The ablation argument (same model for both agents) is unaffected.
MODEL = "claude-sonnet-4-6"

REVIEWER_SYSTEM = """You are a senior code reviewer reviewing a pull request. Your job is to find real issues — security vulnerabilities, correctness bugs, and style problems — in the diff.

Rules:
- Focus on changed code (the diff). Unchanged code is context, not your target.
- Anchor every finding to a specific file and line range in the after-state.
- Be adversarial but precise. Do not fabricate issues. Do not flag stylistic preferences as bugs.
- If the diff is clean and you find no real issues, report zero findings. A short review is fine.

Pay equal attention to correctness bugs and security bugs. Specifically watch for:
- Missing None / empty / type checks on call return values (e.g., does request.get_json() handle non-JSON bodies?).
- Off-by-one and boundary errors.
- Reinvented stdlib or local helpers — if the new code does what an existing function in the same file already does, that is a correctness issue, not a style nit.
- Silent error suppression that violates the declared return type.
- Missing branches: what happens when the input is empty, None, or unexpected?

Categories: security | correctness | style

Severities — anchor against these examples, do not inflate:
- critical: exploitable vuln (path traversal, SQLi, RCE), credential exposure in source or logs, or a correctness bug that corrupts state / loses data / breaks the function's contract on the happy path.
- high: real bug that will surface under normal use (e.g., crashes on common input, returns wrong type, races on shared state).
- medium: real issue worth fixing before merge (e.g., poor error handling that produces a 500 instead of a 400, missing input validation that isn't directly exploitable, PII in logs).
- low: style, nit, non-blocking suggestion (local import inside a function, naming, formatting, dead code).

When in doubt between two tiers, pick the lower one. Severity inflation is a quality problem.

For each finding include a brief rationale explaining why this is a real issue. The rationale is read by an arbiter, not scored — write for the arbiter, not for diplomacy."""

REPORT_TOOL = {
    "name": "report_findings",
    "description": "Report findings from the code review. Use an empty list if no real issues were found.",
    "input_schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "file": {
                            "type": "string",
                            "description": "File path within the PR, e.g. 'after.py'.",
                        },
                        "line_range": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 2,
                            "maxItems": 2,
                            "description": "[start_line, end_line] inclusive, in the after-state file.",
                        },
                        "category": {
                            "type": "string",
                            "enum": ["security", "correctness", "style"],
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"],
                        },
                        "description": {
                            "type": "string",
                            "description": "What the issue is. One sentence.",
                        },
                        "rationale": {
                            "type": "string",
                            "description": "Why this is a real issue. One or two sentences for the arbiter.",
                        },
                    },
                    "required": [
                        "file",
                        "line_range",
                        "category",
                        "severity",
                        "description",
                        "rationale",
                    ],
                },
            }
        },
        "required": ["findings"],
    },
}


_CLIENT: Anthropic | None = None


def _client() -> Anthropic:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = Anthropic()
    return _CLIENT


def review(agent_input: dict) -> list[dict]:
    """Run the reviewer agent against a single PR.

    :param agent_input: output of load_agent_input(): pr_id, before, after, diff.
    :returns: list of finding dicts. May include a 'rationale' field beyond the
        rubric shape; the scoring harness ignores extra fields.
    """
    user_msg = _format_user_message(agent_input)
    resp = _client().messages.create(
        model=MODEL,
        max_tokens=4096,
        system=REVIEWER_SYSTEM,
        tools=[REPORT_TOOL],
        tool_choice={"type": "tool", "name": "report_findings"},
        messages=[{"role": "user", "content": user_msg}],
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "report_findings":
            return _validate(block.input.get("findings", []))
    return []


def _format_user_message(agent_input: dict) -> str:
    return (
        "Review this pull request.\n\n"
        "# Diff\n\n"
        "```\n"
        f"{agent_input['diff']}\n"
        "```\n\n"
        "# Before (full file)\n\n"
        "```python\n"
        f"{agent_input['before']}\n"
        "```\n\n"
        "# After (full file)\n\n"
        "```python\n"
        f"{agent_input['after']}\n"
        "```\n\n"
        "Report findings using the report_findings tool. An empty list is the correct answer if the diff has no real issues."
    )


def _validate(findings: list) -> list[dict]:
    """Drop malformed entries. The tool schema is strict but defense-in-depth."""
    out: list[dict] = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        lr = f.get("line_range")
        if not (isinstance(lr, list) and len(lr) == 2 and all(isinstance(x, int) for x in lr)):
            continue
        if not all(k in f for k in ("file", "category", "severity", "description")):
            continue
        out.append(f)
    return out


if __name__ == "__main__":
    # Smoke run: review pr_001 and print the result.
    import json
    import sys
    from pathlib import Path

    from dotenv import find_dotenv, load_dotenv

    # override=True because some shells export ANTHROPIC_API_KEY="" which
    # would otherwise block the .env value from loading.
    load_dotenv(find_dotenv(), override=True)

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from eval.harness import load_agent_input

    pr_id = sys.argv[1] if len(sys.argv) > 1 else "pr_001"
    findings = review(load_agent_input(pr_id))
    print(json.dumps(findings, indent=2))
