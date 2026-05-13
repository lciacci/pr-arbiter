"""
Arbiter agent (iter2): independent second-pass reviewer.

The iter0/iter1 design treated the arbiter as a triage filter over the
reviewer's findings. The diagnostic in results/diagnostic_notes.md showed that
filter-only arbitration cannot beat a well-calibrated reviewer: lenient drops
true positives faster than false positives, strict drops criticals. So iter2
changes the arbiter's job.

This arbiter does an INDEPENDENT review of the diff. It sees the reviewer's
findings as context (anti-redundancy framing) but is allowed — and explicitly
encouraged — to surface new findings the reviewer missed. The expected
contribution is correctness-critical bugs and architectural issues (reinvented
helpers, cross-function concerns) that the single-pass reviewer's pattern
matching tends to skip.

The runner (`eval/run_baseline.py`) unions arbiter and reviewer findings with
approximate-match dedup, keeping the higher-severity version of any duplicate.
"""

from __future__ import annotations

import json

from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"

ARBITER_SYSTEM = """You are a second-pass code reviewer. A first reviewer has already looked at this PR. Your job is to find what the first reviewer missed — not to triage or re-rank what they already found.

Your focus areas, in order:
1. Correctness-critical bugs. The first reviewer is good at security vuln patterns (path traversal, SQLi, credential leaks) but often misses correctness-critical bugs: missing None / empty / type checks on return values, off-by-one, race conditions, missing branches, silent error suppression that violates the function's contract, state changes that aren't persisted.
2. Architectural issues. Code that reinvents an existing helper in the same file, function-level coupling that should use existing abstractions, configuration that's set but never read or saved.
3. Things hiding behind style. Style-heavy PRs sometimes carry a real bug under the formatting noise — a parameter ordering swap, a sign flip, a condition negation. Read the diff for behavior changes, not just structure changes.

Anti-redundancy rules:
- The first reviewer's findings are shown to you as context. Do NOT re-report the same issues with different words. If you would have flagged the same bug at the same line, skip it — the runner merges your output with theirs.
- A finding "at the same line as a reviewer finding but in a different category or describing a different mechanism" counts as new. Report it.
- If you re-read the code and the reviewer's finding looks wrong, do NOT drop it from their list — your output is additive, not subtractive. Note your disagreement in the rationale of any of your own findings if relevant, but only your own findings appear in your output.

Calibration:
- A clean refactor with nothing the reviewer caught is fine — return an empty list rather than invent findings. The same severity anchors apply (critical = exploitable / RCE / state corruption / broken contract on happy path; high = real bug in production; medium = worth fixing; low = style nit). Default to the lower tier when in doubt.
- If you find no NEW issues beyond what the reviewer caught, return an empty list. That is the correct answer when the reviewer was thorough.

For each finding, write a short rationale that explains the bug from the code alone. This is for offline debugging."""

ARBITER_TOOL = {
    "name": "report_independent_findings",
    "description": "Report findings the first reviewer missed. Empty list is valid if the reviewer was thorough or the PR is clean.",
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
                            "description": "Why this is a real issue, in terms of the after-state code. For debugging; stripped before scoring.",
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
    """Run the independent second-pass reviewer.

    :param agent_input: must contain pr_id, before, after, diff, reviewer_findings.
    :returns: arbiter's own findings (rubric shape, rationale stripped). The
        runner is responsible for merging with reviewer findings.
    """
    user_msg = _format_user_message(agent_input)
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
            return _strip_rationale(_validate(block.input.get("findings", [])))
    return []


def _format_user_message(agent_input: dict) -> str:
    return (
        "Independent second-pass review of this pull request.\n\n"
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
        "# First reviewer's findings (context — do not re-report these)\n\n"
        "```json\n"
        f"{json.dumps(agent_input['reviewer_findings'], indent=2)}\n"
        "```\n\n"
        "Report any findings the first reviewer missed via report_independent_findings. "
        "Empty list is valid if the reviewer was thorough."
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
    return [{k: v for k, v in f.items() if k != "rationale"} for f in findings]


# ---------- merge helper ----------

_SEV_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def merge_findings(
    reviewer_findings: list[dict],
    arbiter_findings: list[dict],
    line_tolerance: int = 3,
) -> list[dict]:
    """Union reviewer + arbiter findings, deduping by approximate match.

    Approximate match: same file + category, line midpoint within ±line_tolerance.
    When a pair matches, keep the higher-severity version; on a tie, prefer the
    reviewer's finding (it ran first).
    """
    merged: list[dict] = list(reviewer_findings)
    for a in arbiter_findings:
        if not _is_dup(a, merged, line_tolerance):
            merged.append(a)
            continue
        # Replace dup with higher-severity version
        for i, m in enumerate(merged):
            if _findings_match(m, a, line_tolerance):
                if _SEV_RANK.get(a.get("severity"), 0) > _SEV_RANK.get(m.get("severity"), 0):
                    merged[i] = a
                break
    return merged


def _is_dup(f: dict, existing: list[dict], tol: int) -> bool:
    return any(_findings_match(f, m, tol) for m in existing)


def _findings_match(a: dict, b: dict, tol: int) -> bool:
    if a.get("file") != b.get("file"):
        return False
    if a.get("category") != b.get("category"):
        return False
    a_lines = a.get("line_range", [0, 0])
    b_lines = b.get("line_range", [0, 0])
    a_mid = (a_lines[0] + a_lines[1]) / 2
    b_mid = (b_lines[0] + b_lines[1]) / 2
    return abs(a_mid - b_mid) <= tol


if __name__ == "__main__":
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
    arb = arbitrate({**ai, "reviewer_findings": rev})
    merged = merge_findings(rev, arb)
    print(json.dumps({"reviewer": rev, "arbiter": arb, "merged": merged}, indent=2))
