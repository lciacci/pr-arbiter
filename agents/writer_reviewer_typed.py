"""
Arm-C reviewer for Phase 2 writer-loop iter2.

Same role as agents/writer_reviewer.py (sees latest attempt + spec + history,
not tests, not failure traces) but with an extended tool schema requiring
`finding_type` on every finding:

- `spec-violation` — the spec contains a clause this code violates. Requires
  a verbatim `spec_quote`. If the critic cannot produce a quote that is
  actually in the spec, the finding is downgraded to `spec-interpretation`
  at validation time. Adversarial-robustness property: prevents critics
  from labeling guesses as violations to bully the writer.
- `spec-interpretation` — the spec is silent or ambiguous on this point and
  the critic is making a judgment call. `spec_quote` not required; an
  optional `proposed_interpretation` field may suggest what the critic
  thinks the spec implies.

Distinct module from agents/writer_reviewer.py so arm B (un-fixed control)
keeps the original schema and arm C uses this one. Both share the same
underlying writer.write() and writer_loop driver — the only difference is
the reviewer/arbiter outputs and the writer system-prompt extension that
tells the writer how to weight the two finding types.
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

## Finding types (REQUIRED)

Every finding must be tagged with `finding_type`:

- `spec-violation` — the spec contains a clause that the writer's code contradicts. You MUST provide a `spec_quote` field with the verbatim text from the spec that supports the finding. If you cannot quote the spec verbatim, the finding is not a spec-violation — it is a spec-interpretation, and you must tag it that way. Do not paraphrase; copy the spec text exactly. A spec-violation without a quote will be downgraded.
- `spec-interpretation` — the spec is silent or ambiguous on this point and you are making a judgment call about what the spec probably means. `spec_quote` is optional (and usually not applicable). You may include `proposed_interpretation` describing what you think the spec implies. The writer will weight these findings less than spec-violations and may keep their own interpretation if they already have one.

This distinction is the most important part of your output. The writer treats `spec-violation` findings as bugs to fix and `spec-interpretation` findings as advisory. Mislabeling a guess as a violation pushes the writer in the wrong direction on underspecified tasks.

## Calibration (severity, orthogonal to finding_type)

- critical = the code violates a concrete example in the spec or crashes on valid input from the spec
- high = real bug under normal use; will fail tests for the stated behavior
- medium = an interpretation choice that is probably wrong, or missing input validation the spec implies
- low = style; rarely worth a finding in this setting

Severity and finding_type are orthogonal: a spec-interpretation can be high-severity (you really think it matters), and a spec-violation can be low-severity (cosmetic). Default to the lower tier when uncertain.

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
                        "finding_type": {
                            "type": "string",
                            "enum": ["spec-violation", "spec-interpretation"],
                            "description": "spec-violation REQUIRES a verbatim spec_quote. spec-interpretation does not. See system prompt.",
                        },
                        "spec_quote": {
                            "type": "string",
                            "description": "Verbatim text from the spec, copied character-for-character. REQUIRED when finding_type=spec-violation. Leave empty or omit for spec-interpretation. A spec-violation finding with no quote, or a quote that is not actually in the spec, will be downgraded to spec-interpretation.",
                        },
                        "proposed_interpretation": {
                            "type": "string",
                            "description": "Optional. For spec-interpretation findings: a short statement of what you think the spec implies. The writer may or may not adopt it.",
                        },
                        "description": {"type": "string"},
                        "rationale": {
                            "type": "string",
                            "description": "Why this is a real issue. Read by the writer next iteration.",
                        },
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


def review(code: str, spec: str, history: list = None) -> list[dict]:
    """Run the typed writer-reviewer.

    Output findings have the v1 fields plus:
      - finding_type: "spec-violation" | "spec-interpretation"
      - spec_quote: present iff spec-violation (validated; missing/empty → downgrade)
      - proposed_interpretation: optional, only meaningful for spec-interpretation
      - spec_quote_found_in_spec: bool | None — sanity check, computed at validation
      - downgraded_reason: optional str — set if finding was downgraded
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
            return _validate(block.input.get("findings", []), spec)
    # No tool_use block found. Surface stop_reason so callers can distinguish
    # "model produced no findings" from "response truncated / refused".
    import sys
    print(
        f"writer_reviewer_typed.review: no tool_use block "
        f"(stop_reason={getattr(resp, 'stop_reason', 'unknown')!r})",
        file=sys.stderr,
    )
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
                    ft = f.get("finding_type", "?")
                    parts.append(
                        f"  - [{f.get('severity','?')}/{f.get('category','?')}/{ft}] {f.get('description','')}\n"
                    )
                parts.append("\n")
    parts.append(
        "Report findings on the latest attempt via report_findings. "
        "Tag every finding with finding_type. Provide spec_quote (verbatim) for any spec-violation."
    )
    return "".join(parts)


def _normalize_for_match(text: str) -> str:
    return " ".join(text.split())


def _validate(findings: list, spec: str) -> list[dict]:
    out: list[dict] = []
    norm_spec = _normalize_for_match(spec)
    for raw in findings:
        if not isinstance(raw, dict):
            continue
        # Shallow-copy so we don't mutate the SDK-returned dict in place.
        f = dict(raw)
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
        # Sanity check: spec_quote actually present in spec (whitespace-tolerant).
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
    task = sys.argv[1] if len(sys.argv) > 1 else "task_013"
    spec = (Path(__file__).parent.parent / "phase2_corpus" / task / "spec.md").read_text()
    code = (Path(__file__).parent.parent / "phase2_corpus" / task / "solution.py").read_text()
    import json
    print(json.dumps(review(code, spec, history=None), indent=2))
