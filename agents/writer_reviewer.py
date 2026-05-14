"""
Reviewer agent for Phase 2 writer-loop.

Reviews a writer's code attempt against the spec. Sees the prior attempt
history (so it can catch regression patterns and oscillation). Does NOT
see the tests or the failure traces — same epistemic boundary as the
writer.

Distinct from agents/reviewer.py (Phase 1 PR reviewer) because the input
shape and the failure modes are different. Kept separate to avoid coupling
Phase 1 + Phase 2 prompts.
"""

from __future__ import annotations

from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"


REVIEWER_SYSTEM = """You are a senior code reviewer. A writer agent is attempting to implement a Python module from a written specification. You see the writer's latest attempt, the spec, and the history of prior attempts + your prior feedback (if any).

Your job: find correctness bugs in the latest attempt and surface ambiguities in the spec that the writer is resolving incorrectly. You do NOT see the test suite, and you do NOT see test failures. The writer only sees the pass count.

Read the spec carefully. Every concrete example in the spec is a real case the tests cover. If the writer's code would give a different answer than the spec's example states, that is a critical bug.

Pay attention to:
- Mismatches between the writer's code and the spec's stated behavior, especially on edge cases (empty input, None, malformed input, boundary conditions, repeated operations).
- Silent bugs: caught-and-ignored exceptions, default fallbacks that mask errors, incorrect return types.
- Reinvented stdlib (the writer wrote 30 lines that one call to a stdlib function would handle correctly — those 30 lines probably have bugs).
- Off-by-one, sign flips, condition inversions, parameter order swaps.
- Spec ambiguity: the spec is silent on some case AND the writer is making an assumption the tests may not share. Call this out so the writer can reconsider.

Cross-iteration patterns (use the history):
- Regression: the writer fixed something but broke a case the prior attempt got right. Pass count moved backwards.
- Oscillation: the writer is toggling between two wrong approaches. Tell them to commit to one and debug.
- Misread feedback: the writer addressed prior feedback the wrong way. Be explicit about what to do differently.

Calibration:
- critical = the code violates a concrete example in the spec or crashes on valid input from the spec
- high = real bug under normal use; will fail tests for the stated behavior
- medium = an interpretation choice that is probably wrong, or missing input validation the spec implies
- low = style; rarely worth a finding in this setting

Default to the lower tier when uncertain.

Write each rationale so the writer can act on it. Reference line numbers in the attempt. Do not paste test inputs or expected values — you don't see them, and inventing them confuses the writer."""


REPORT_TOOL = {
    "name": "report_findings",
    "description": "Report findings about the writer's latest attempt. Empty list is valid if the attempt looks correct or if you would only have style nits.",
    "input_schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "line_range": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 2,
                            "maxItems": 2,
                            "description": "[start_line, end_line] inclusive, in the writer's latest code attempt. Use [0, 0] if the issue is whole-file.",
                        },
                        "category": {
                            "type": "string",
                            "enum": ["correctness", "spec-ambiguity", "regression", "style"],
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"],
                        },
                        "description": {"type": "string"},
                        "rationale": {
                            "type": "string",
                            "description": "Why this is a real issue. Read by the writer next iteration.",
                        },
                    },
                    "required": ["line_range", "category", "severity", "description", "rationale"],
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


def review(code: str, spec: str, history: list = None) -> list[dict]:
    """Run the writer-reviewer.

    :param code: latest writer attempt source.
    :param spec: task spec.md contents.
    :param history: list of Attempt records (writer.py) — prior attempts +
        prior feedback. Reviewer sees this so it can catch regression /
        oscillation patterns. Pass empty list or None on iter 1.
    """
    user_msg = _format_user_message(code, spec, history or [])
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


def _format_user_message(code: str, spec: str, history: list) -> str:
    parts = [
        "# Task specification\n\n",
        spec,
        "\n\n# Latest attempt (the one you are reviewing)\n\n```python\n",
        code,
        "\n```\n\n",
    ]
    if history:
        parts.append("# Prior attempts and prior feedback (history)\n\n")
        parts.append(
            "These are the writer's earlier attempts on this task and the feedback that was given. "
            "Use this to spot regressions (writer fixed X, broke Y) and oscillation patterns. "
            "The writer also sees this.\n\n"
        )
        for i, att in enumerate(history, start=1):
            parts.append(f"## Attempt {i}\n\n")
            parts.append("```python\n")
            parts.append(att.code)
            parts.append("\n```\n\n")
            parts.append(f"Test signal: {att.test_signal}\n\n")
            if att.reviewer_feedback:
                parts.append(f"Reviewer feedback given:\n")
                for f in att.reviewer_feedback:
                    parts.append(f"  - [{f.get('severity','?')}/{f.get('category','?')}] {f.get('description','')}\n")
                parts.append("\n")
    parts.append(
        "Report findings on the latest attempt via report_findings. "
        "Empty list is correct if the code looks right or you would only have style nits."
    )
    return "".join(parts)


def _validate(findings: list) -> list[dict]:
    out: list[dict] = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        lr = f.get("line_range")
        if not (isinstance(lr, list) and len(lr) == 2 and all(isinstance(x, int) for x in lr)):
            continue
        if not all(k in f for k in ("category", "severity", "description", "rationale")):
            continue
        out.append(f)
    return out


if __name__ == "__main__":
    import sys
    from pathlib import Path
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(), override=True)
    task = sys.argv[1] if len(sys.argv) > 1 else "task_001"
    spec = (Path(__file__).parent.parent / "phase2_corpus" / task / "spec.md").read_text()
    code = (Path(__file__).parent.parent / "phase2_corpus" / task / "solution.py").read_text()
    import json
    print(json.dumps(review(code, spec, history=None), indent=2))
