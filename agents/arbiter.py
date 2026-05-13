"""
Arbiter agent: triages the reviewer's findings.

Single Anthropic API call per PR. Sees diff + before + after + reviewer findings.
Outputs a filtered, re-prioritized list. Must be willing to drop findings,
not just relabel them. Returns the rubric shape (rationale field is stripped
before returning so the eval harness sees the canonical shape).
"""

from __future__ import annotations

import json

from anthropic import Anthropic

# Same model as reviewer — keeps the ablation clean. If the arbiter shows
# signal but underperforms, swapping to Opus is a deliberate session 3 move.
MODEL = "claude-sonnet-4-6"

ARBITER_SYSTEM = """You are an arbiter triaging a code reviewer's findings on a pull request. The reviewer was instructed to be adversarial; your job is the opposite — precision over recall.

Your principles:
- Reviewer optimizes for catching everything. You optimize for what should actually block or land in the PR.
- You should be willing to drop findings. A finding survives only if you can confirm it from the diff and the surrounding code. If the reviewer's rationale doesn't hold up when you re-read the after-state, drop it.
- Some PRs have no real issues. Returning an empty list is the right answer on a clean refactor. Do not preserve findings just because the reviewer wrote them.
- Demote severity when the reviewer inflated it. A real issue at the wrong tier is still a finding worth keeping, but at the correct severity.
- Do not invent new findings. Your output must be a subset of (or re-prioritization of) the reviewer's findings — same file, same approximate location. If the reviewer missed something, that is a reviewer problem, not an arbiter problem.

For each finding you keep, write a short rationale describing why it survives arbitration. This is for offline debugging, not graded."""

ARBITER_TOOL = {
    "name": "report_triaged_findings",
    "description": "Report your triaged findings. Use an empty list to drop all findings.",
    "input_schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "file": {"type": "string"},
                        "line_range": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 2,
                            "maxItems": 2,
                        },
                        "category": {
                            "type": "string",
                            "enum": ["security", "correctness", "style"],
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"],
                        },
                        "description": {"type": "string"},
                        "rationale": {
                            "type": "string",
                            "description": "Why this finding survives arbitration. For debugging; stripped before scoring.",
                        },
                    },
                    "required": ["file", "line_range", "category", "severity", "description", "rationale"],
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


def arbitrate(agent_input: dict) -> list[dict]:
    """Arbitrate over the reviewer's findings.

    :param agent_input: must contain pr_id, before, after, diff, reviewer_findings.
    :returns: filtered/re-prioritized list of findings in rubric shape
        (rationale stripped).
    """
    user_msg = _format_user_message(agent_input)
    resp = _client().messages.create(
        model=MODEL,
        max_tokens=4096,
        system=ARBITER_SYSTEM,
        tools=[ARBITER_TOOL],
        tool_choice={"type": "tool", "name": "report_triaged_findings"},
        messages=[{"role": "user", "content": user_msg}],
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "report_triaged_findings":
            raw = block.input.get("findings", [])
            return _strip_rationale(_validate(raw))
    return []


def _format_user_message(agent_input: dict) -> str:
    return (
        "Triage the reviewer's findings on this pull request.\n\n"
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
        "# Reviewer's findings\n\n"
        "```json\n"
        f"{json.dumps(agent_input['reviewer_findings'], indent=2)}\n"
        "```\n\n"
        "Return your triaged findings via the report_triaged_findings tool. "
        "Drop, demote, or re-prioritize as you see fit. Empty list is valid."
    )


def _validate(findings: list) -> list[dict]:
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


def _strip_rationale(findings: list[dict]) -> list[dict]:
    """Return findings in canonical rubric shape, without the rationale field."""
    return [{k: v for k, v in f.items() if k != "rationale"} for f in findings]


if __name__ == "__main__":
    # Smoke run: take reviewer output for one PR, arbitrate, print.
    import sys
    from pathlib import Path

    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(), override=True)

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from agents.reviewer import review
    from eval.harness import load_agent_input

    pr_id = sys.argv[1] if len(sys.argv) > 1 else "pr_001"
    ai = load_agent_input(pr_id)
    rev = review(ai)
    triaged = arbitrate({**ai, "reviewer_findings": rev})
    print(json.dumps({"reviewer": rev, "arbiter": triaged}, indent=2))
