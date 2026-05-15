"""
Arm-C arbiter for Phase 2 writer-loop iter2.

Same role as agents/writer_arbiter.py (second-pass reviewer; latest attempt
+ spec + reviewer findings; amnesic — no prior attempts) but with the
typed-finding schema. See agents/writer_reviewer_typed.py for the rationale.
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

## Finding types (REQUIRED)

Every finding must be tagged with `finding_type`:

- `spec-violation` — the spec contains a clause that the writer's code contradicts. You MUST provide a `spec_quote` field with the verbatim text from the spec that supports the finding. If you cannot quote the spec verbatim, the finding is not a spec-violation — it is a spec-interpretation. A spec-violation without a quote will be downgraded.
- `spec-interpretation` — the spec is silent or ambiguous on this point and you are making a judgment call. `spec_quote` is optional. You may include `proposed_interpretation`.

Severity and finding_type are orthogonal. A spec-interpretation can be high-severity; a spec-violation can be low. Default to the lower tier when uncertain.

This distinction matters: the writer treats spec-violation findings as bugs to address and spec-interpretation findings as advisory. The first reviewer also uses this schema; do not contradict their typing without reason. If you re-classify something they tagged as spec-violation, your spec_quote should differ from theirs (or you should be downgrading because they had no quote).

Calibration anchors — critical = violates concrete spec example or crashes on valid input; high = real bug under normal use; medium = probably-wrong interpretation; low = style. If you have no new findings, return an empty list — that's the correct answer when the first reviewer was thorough.

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
                        "finding_type": {
                            "type": "string",
                            "enum": ["spec-violation", "spec-interpretation"],
                        },
                        "spec_quote": {
                            "type": "string",
                            "description": "Verbatim spec text. REQUIRED for spec-violation; will be downgraded otherwise.",
                        },
                        "proposed_interpretation": {
                            "type": "string",
                            "description": "Optional, only meaningful for spec-interpretation.",
                        },
                        "description": {"type": "string"},
                        "rationale": {"type": "string"},
                    },
                    "required": [
                        "line_range",
                        "category",
                        "severity",
                        "finding_type",
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


def arbitrate(code: str, spec: str, reviewer_findings: list[dict]) -> list[dict]:
    """Independent second-pass with typed-finding schema. No history."""
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
            return _validate(block.input.get("findings", []), spec)
    import sys
    print(
        f"writer_arbiter_typed.arbitrate: no tool_use block "
        f"(stop_reason={getattr(resp, 'stop_reason', 'unknown')!r})",
        file=sys.stderr,
    )
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
        "Tag every finding with finding_type and provide spec_quote (verbatim) for spec-violation. "
        "Empty list is valid if the first reviewer was thorough."
    )


def _normalize_for_match(text: str) -> str:
    return " ".join(text.split())


def _validate(findings: list, spec: str) -> list[dict]:
    out: list[dict] = []
    norm_spec = _normalize_for_match(spec)
    for raw in findings:
        if not isinstance(raw, dict):
            continue
        f = dict(raw)  # Shallow-copy to avoid mutating SDK-returned dicts.
        lr = f.get("line_range")
        if not (isinstance(lr, list) and len(lr) == 2 and all(isinstance(x, int) for x in lr)):
            continue
        if not all(k in f for k in ("category", "severity", "description", "rationale", "finding_type")):
            continue
        orig_ft = f.get("finding_type")
        ft = orig_ft
        if ft not in ("spec-violation", "spec-interpretation"):
            ft = "spec-interpretation"
            f["downgraded_reason"] = f"unknown finding_type {orig_ft!r}"
        sq = (f.get("spec_quote") or "").strip()
        if ft == "spec-violation" and not sq:
            ft = "spec-interpretation"
            f["downgraded_reason"] = "spec-violation without spec_quote"
        if sq:
            norm_sq = _normalize_for_match(sq)
            in_spec = norm_sq in norm_spec
            f["spec_quote_found_in_spec"] = in_spec
            if ft == "spec-violation" and not in_spec:
                ft = "spec-interpretation"
                f["downgraded_reason"] = "spec-violation with spec_quote not found in spec"
        else:
            f["spec_quote_found_in_spec"] = None
        f["finding_type"] = ft
        out.append(f)
    return out


if __name__ == "__main__":
    import sys
    from pathlib import Path
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(), override=True)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from agents.writer_reviewer_typed import review

    task = sys.argv[1] if len(sys.argv) > 1 else "task_013"
    spec = (Path(__file__).parent.parent / "phase2_corpus" / task / "spec.md").read_text()
    code = (Path(__file__).parent.parent / "phase2_corpus" / task / "solution.py").read_text()
    rev = review(code, spec, history=None)
    arb = arbitrate(code, spec, rev)
    print(json.dumps({"reviewer": rev, "arbiter": arb}, indent=2))
