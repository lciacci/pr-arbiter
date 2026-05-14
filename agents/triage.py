"""
Triage agent (iter3): mutual-triage adversarial assessment.

Two existing agent voices (reviewer-style, arbiter-style) independently vote
on each finding in the merged list. Source-blind — the agents don't know
which finding came from whom. Aggregation rule:

    both keep   -> high confidence  (blocking-tier candidate)
    both drop   -> drop entirely
    anything else -> low confidence  (advisory)

This tests whether the existing two POVs disagree informatively. If high-conf
findings are much more likely to match the rubric than low-conf, the
confidence tier carries signal and the architecture is justified.
"""

from __future__ import annotations

import json
from typing import Literal

from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"

# Reviewer-voice triage system prompt — recall-oriented framing. Tends to
# keep a finding if a bug claim is plausible.
REVIEWER_VOICE_SYSTEM = """You are a senior code reviewer. A set of findings has been compiled on a pull request. For each finding, decide whether it represents a real issue in the after-state code.

Vote KEEP if you can re-state the bug from the code without relying on the finding's wording.
Vote DROP if re-reading the code shows the finding is wrong, the reviewer misread something, or the issue does not apply to the after-state behavior.
Vote UNSURE if you can construct an argument both ways and can't reach a confident call from the code alone.

You see only the findings — not who proposed them. Treat every finding the same. Be willing to drop your own first instinct if the code doesn't support it. Be willing to keep findings that you wouldn't have flagged yourself if they describe a real bug.

For each vote include a one-sentence rationale grounded in the code."""

# Arbiter-voice triage system prompt — skeptical second-pass framing.
# Tends to drop a finding if the bug can't be reproduced on close reading.
ARBITER_VOICE_SYSTEM = """You are a skeptical second-pass reviewer. A set of findings has been compiled on a pull request. For each finding, decide whether it represents a real issue you would block the PR on, after carefully re-reading the after-state code.

Vote KEEP if the bug claim is concrete and you can reproduce the issue from the code without referring back to the finding's wording.
Vote DROP if the finding is speculative, restates a different finding using different words, applies to unchanged code, or describes a "what if" that the function's contract does not actually allow.
Vote UNSURE if the issue is real but small, or if the bug claim is plausible but you can't verify it cleanly from the diff alone.

You see only the findings — not who proposed them. Apply equal scrutiny to every finding. A clean refactor with all findings being hallucinations is a legitimate outcome — return DROP on all of them if that's what the code shows.

For each vote include a one-sentence rationale grounded in the code."""

TRIAGE_TOOL = {
    "name": "report_votes",
    "description": "Cast a KEEP / DROP / UNSURE vote on every finding, in order.",
    "input_schema": {
        "type": "object",
        "properties": {
            "votes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {
                            "type": "integer",
                            "description": "Index of the finding being voted on (0-based, matches input order).",
                        },
                        "vote": {
                            "type": "string",
                            "enum": ["keep", "drop", "unsure"],
                        },
                        "rationale": {"type": "string"},
                    },
                    "required": ["index", "vote", "rationale"],
                },
            }
        },
        "required": ["votes"],
    },
}


Voice = Literal["reviewer", "arbiter"]


_CLIENT: Anthropic | None = None


def _client() -> Anthropic:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = Anthropic()
    return _CLIENT


def triage(agent_input: dict, findings: list[dict], voice: Voice) -> list[dict]:
    """Vote on every finding. Returns list of vote dicts in input order.

    :param agent_input: must contain before, after, diff.
    :param findings: merged-list findings to vote on.
    :param voice: 'reviewer' (recall-oriented) or 'arbiter' (skeptical).
    :returns: list of {index, vote, rationale} in input order. Missing
        indices are filled with UNSURE votes.
    """
    if not findings:
        return []

    system = REVIEWER_VOICE_SYSTEM if voice == "reviewer" else ARBITER_VOICE_SYSTEM
    user_msg = _format_user_message(agent_input, findings)
    resp = _client().messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system,
        tools=[TRIAGE_TOOL],
        tool_choice={"type": "tool", "name": "report_votes"},
        messages=[{"role": "user", "content": user_msg}],
    )
    raw_votes: list[dict] = []
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "report_votes":
            raw_votes = block.input.get("votes", [])
            break

    # Re-index: ensure one vote per finding in correct order. Missing or
    # malformed votes default to UNSURE (which classifies as low confidence,
    # not drop — safer fallback).
    by_index = {v["index"]: v for v in raw_votes if isinstance(v, dict) and "index" in v}
    out: list[dict] = []
    for i, _ in enumerate(findings):
        v = by_index.get(i)
        if not v or v.get("vote") not in ("keep", "drop", "unsure"):
            out.append({"index": i, "vote": "unsure", "rationale": "missing or malformed vote"})
        else:
            out.append({"index": i, "vote": v["vote"], "rationale": v.get("rationale", "")})
    return out


def _format_user_message(agent_input: dict, findings: list[dict]) -> str:
    numbered = "\n".join(
        f"[{i}] {f['file']} L{f['line_range']} {f['category']}/{f['severity']}: {f['description']}"
        for i, f in enumerate(findings)
    )
    return (
        "Vote on each of the following findings against this pull request.\n\n"
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
        "# Findings to vote on\n\n"
        f"{numbered}\n\n"
        "Use the report_votes tool. Cast one vote per finding, in order. "
        "KEEP, DROP, or UNSURE; one-sentence rationale each."
    )


# ---------- aggregation ----------

Confidence = Literal["high", "low", "drop"]


def classify(
    findings: list[dict],
    reviewer_votes: list[dict],
    arbiter_votes: list[dict],
) -> list[tuple[dict, Confidence]]:
    """Apply the aggregation rule per finding.

        both keep    -> high
        both drop    -> drop
        anything else -> low
    """
    out: list[tuple[dict, Confidence]] = []
    for i, f in enumerate(findings):
        rv = reviewer_votes[i]["vote"] if i < len(reviewer_votes) else "unsure"
        av = arbiter_votes[i]["vote"] if i < len(arbiter_votes) else "unsure"
        if rv == "keep" and av == "keep":
            out.append((f, "high"))
        elif rv == "drop" and av == "drop":
            out.append((f, "drop"))
        else:
            out.append((f, "low"))
    return out


if __name__ == "__main__":
    # Smoke: load iter2 result for pr_001 and triage the merged findings.
    import sys
    from pathlib import Path
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(), override=True)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from eval.harness import load_agent_input

    pr_id = sys.argv[1] if len(sys.argv) > 1 else "pr_001"
    iter2 = json.loads(Path("results/iter2_20260513.json").read_text())
    p = next(p for p in iter2["per_pr"] if p["pr_id"] == pr_id)
    ai = load_agent_input(pr_id)
    findings = p["final_findings"]
    rv = triage(ai, findings, voice="reviewer")
    av = triage(ai, findings, voice="arbiter")
    classified = classify(findings, rv, av)
    for (f, c), r, a in zip(classified, rv, av):
        print(f"  [{c:5}] rv={r['vote']:6} av={a['vote']:6}  {f['category']}/{f['severity']:8} L{f['line_range']}: {f['description'][:70]}")
