"""
Independent second-pass reviewer for Phase 2 writer-loop.

Sees: latest writer attempt + spec + reviewer's findings.
Does NOT see: prior attempts, prior feedback, tests, failure traces.

The amnesia is deliberate. Phase 1 showed independent arbitration only
works when the arbiter isn't anchored to prior critiques. In Phase 2,
that translates to: each iteration is a fresh read of the latest code,
no recall of what was said before.

Arbiter is additive: only emits findings the reviewer missed.
"""

from __future__ import annotations

import json

from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"


ARBITER_SYSTEM = """You are a second-pass code reviewer. A writer agent has produced a Python module against a written spec. A first reviewer has already commented on the latest attempt. Your job is to find what the first reviewer missed — not to re-rank or re-state what they already said.

What you see:
- The task spec.
- The writer's latest code attempt.
- The first reviewer's findings on that attempt.

What you do NOT see:
- The test suite.
- Failure traces.
- Prior attempts or prior feedback. You are reading the latest attempt fresh — this is intentional. Do not ask for history.

Focus areas, in order:
1. Correctness bugs the first reviewer missed. Especially: missing None / empty / type checks, off-by-one, race conditions, sign flips, condition inversions, parameter order swaps. The first reviewer pattern-matches obvious issues; you catch the subtle behavior bugs.
2. Spec violations the first reviewer missed. The spec gives concrete examples. If the code produces a different answer than the spec states, that is a critical finding.
3. Reinvented stdlib. If the writer wrote 30 lines that one stdlib call would handle, those 30 lines probably have bugs the first reviewer skimmed past.

Anti-redundancy:
- If you would flag the same bug at the same place as the first reviewer, skip it. Your output is additive — duplicates get merged out.
- A finding at the same location but describing a different mechanism counts as new. Report it.
- If you re-read the code and the first reviewer's finding looks wrong, do NOT remove it. Your output is additive, not subtractive. Note disagreement in your own rationale if relevant.

Calibration: same anchors — critical = violates concrete spec example or crashes on valid input; high = real bug under normal use; medium = probably-wrong interpretation; low = style. Default to the lower tier when uncertain. If you have no new findings, return an empty list — that's the correct answer when the first reviewer was thorough.

Write rationales tight. The writer reads them next iteration. Reference line numbers."""


ARBITER_TOOL = {
    "name": "report_independent_findings",
    "description": "Report findings the first reviewer missed. Empty list is valid.",
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
                        "rationale": {"type": "string"},
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


def arbitrate(code: str, spec: str, reviewer_findings: list[dict]) -> list[dict]:
    """Run the independent second-pass reviewer.

    No history parameter — the arbiter is deliberately amnesic. Each call
    is a fresh read of the latest code + the first reviewer's findings.
    """
    user_msg = _format_user_message(code, spec, reviewer_findings)
    resp = _client().messages.create(
        model=MODEL,
        max_tokens=4096,
        system=ARBITER_SYSTEM,
        tools=[ARBITER_TOOL],
        tool_choice={"type": "tool", "name": "report_independent_findings"},
        messages=[{"role": "user", "content": user_msg}],
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "report_independent_findings":
            return _validate(block.input.get("findings", []))
    return []


def _format_user_message(code: str, spec: str, reviewer_findings: list[dict]) -> str:
    return (
        "# Task specification\n\n"
        f"{spec}\n\n"
        "# Latest attempt\n\n```python\n"
        f"{code}\n"
        "```\n\n"
        "# First reviewer's findings (context — do not re-report these)\n\n"
        "```json\n"
        f"{json.dumps(reviewer_findings, indent=2)}\n"
        "```\n\n"
        "Report any findings the first reviewer missed via report_independent_findings. "
        "Empty list is valid if the first reviewer was thorough."
    )


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
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from agents.writer_reviewer import review

    task = sys.argv[1] if len(sys.argv) > 1 else "task_012"
    spec = (Path(__file__).parent.parent / "phase2_corpus" / task / "spec.md").read_text()
    code = (Path(__file__).parent.parent / "phase2_corpus" / task / "solution.py").read_text()
    rev = review(code, spec, history=None)
    arb = arbitrate(code, spec, rev)
    print(json.dumps({"reviewer": rev, "arbiter": arb}, indent=2))
