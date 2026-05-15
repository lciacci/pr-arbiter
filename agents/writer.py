"""
Writer agent: produces a Python module that satisfies the task spec.

Phase 2 design (see docs/PHASE_2_HANDOFF.md):
- Writer sees: spec.md, no tests, no test names. History block holds prior
  attempts + reviewer/arbiter feedback + binary pass count signal.
- Writer does NOT see tracebacks, failed inputs, or expected outputs.
- Output is a single Python file shipped to a sandbox.

Tool-use schema forces structured output (full module source as one
string). No JSON parsing of free-form text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"


WRITER_SYSTEM = """You are a senior Python engineer. You implement a single module that satisfies a written specification. A separate test suite is the ground truth; you do not see it. You see only the spec, your prior attempts, and feedback from independent reviewers.

Rules:
- Produce ONE Python module. No extra files. No external state. Stdlib only unless the spec says otherwise.
- Match the function or class signature in the spec exactly. Wrong names mean the tests cannot import your code.
- Read the spec carefully. Every concrete example in the spec is a real case the tests cover — including edge cases (empty input, None, malformed input, boundary conditions).
- The spec may be incomplete or ambiguous. When silent, pick the interpretation a careful Python engineer would default to. Document your interpretation in a docstring or short comment so the reviewers can see your reasoning.
- On retry: read the prior attempts and feedback. Address every reviewer concern. Do NOT regress on cases the prior attempt got right (the pass count tells you whether your fix broke prior coverage).
- Never write code that depends on the test file's contents, environment variables, or external services.
- Return the COMPLETE module via the submit_solution tool. No fragments, no diffs — the full file. Each attempt overwrites the prior one in the sandbox."""


# Arm C extension used in Phase 2 iter2: tells the writer how to weight
# reviewer/arbiter findings tagged with finding_type. Appended to
# WRITER_SYSTEM via the extra_system kwarg on write().
ARM_C_TYPED_FINDINGS_GUIDANCE = """## Reviewer findings: handling finding_type

Reviewer and second-pass-reviewer findings in this run are tagged with a `finding_type` field. Two values are possible:

- `spec-violation` — the finding cites a specific spec clause that your code contradicts. The reviewer includes a `Spec quote` line copying the spec text verbatim. Address these. They are bugs.
- `spec-interpretation` — the spec is silent or ambiguous on this point and the reviewer is making a judgment call about what the spec probably means. If your current code has already chosen an interpretation, do not change it solely because the reviewer chose a different one. Only adopt the reviewer's interpretation if you do not yet have one, or yours has produced test failures (pass count dropped), or you on reflection agree the spec implies the reviewer's interpretation more naturally than yours.

Severity is orthogonal to finding_type. A high-severity spec-interpretation is the reviewer saying "I really think the spec means X" — still a judgment call, still not a violation. Weight it accordingly."""


SUBMIT_TOOL = {
    "name": "submit_solution",
    "description": "Submit the complete Python module that satisfies the spec.",
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Full contents of solution.py. Must be valid Python. Must define every symbol the spec names.",
            },
            "reasoning": {
                "type": "string",
                "description": "One paragraph: how you interpreted the spec, what assumptions you made on ambiguity, what you changed since the prior attempt (if any). Read by reviewers, not by tests.",
            },
        },
        "required": ["code", "reasoning"],
    },
}


@dataclass
class Attempt:
    """One iteration of writer output + the feedback it generated."""

    code: str
    reasoning: str
    test_signal: str  # e.g., "5/13 passing" or "collection error: ImportError"
    reviewer_feedback: list[dict] = field(default_factory=list)
    arbiter_feedback: list[dict] = field(default_factory=list)
    # iter3 H2 logging: the ranked pass-count block shown to the writer at
    # the iteration *following* this attempt. None if the ranking was not
    # rendered (arms without include_pass_ranking, or no prior attempts).
    pass_ranking_shown: str | None = None


@dataclass
class WriterOutput:
    code: str
    reasoning: str


_CLIENT: Anthropic | None = None


def _client() -> Anthropic:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = Anthropic()
    return _CLIENT


def write(
    spec: str,
    history: list[Attempt] | None = None,
    task_id: str = "",
    extra_system: str = "",
    pass_ranking_block: str | None = None,
) -> WriterOutput:
    """Run the writer agent. Returns full module source + reasoning.

    :param spec: task spec.md contents.
    :param history: prior attempts in order. Latest is most recent.
    :param task_id: for logging only; not shown to the agent.
    :param extra_system: appended to the writer system prompt. Used by arm C
        in Phase 2 iter2 to add finding-type handling guidance without
        touching the default prompt.
    :param pass_ranking_block: pre-rendered pass-ranking block (or None).
        Caller (writer_loop) renders once and passes the same string both
        here and to the per-attempt log, ensuring the writer and the log
        cannot diverge. None means no ranking block is inserted.
    """
    user_msg = _format_user_message(spec, history or [], pass_ranking_block)
    system = WRITER_SYSTEM + (("\n\n" + extra_system) if extra_system else "")
    resp = _client().messages.create(
        model=MODEL,
        max_tokens=8192,
        system=system,
        tools=[SUBMIT_TOOL],
        tool_choice={"type": "tool", "name": "submit_solution"},
        messages=[{"role": "user", "content": user_msg}],
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "submit_solution":
            code = block.input.get("code", "")
            reasoning = block.input.get("reasoning", "")
            return WriterOutput(code=code, reasoning=reasoning)
    # No tool_use block — agent refused, hit max_tokens before tool call, or
    # returned only text. Surface this rather than masking it as an empty
    # solution; the loop driver decides whether to treat it as a failed
    # attempt or abort the task.
    stop_reason = getattr(resp, "stop_reason", "unknown")
    text_preview = ""
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            text_preview = (getattr(block, "text", "") or "")[:200]
            break
    return WriterOutput(
        code="",
        reasoning=f"agent did not call submit_solution (stop_reason={stop_reason}, text={text_preview!r})",
    )


def _format_user_message(
    spec: str,
    history: list[Attempt],
    pass_ranking_block: str | None = None,
) -> str:
    parts = [
        "Implement the following specification.\n\n# Specification\n\n",
        spec,
        "\n\n",
    ]
    if history:
        if pass_ranking_block:
            parts.append(pass_ranking_block)
        parts.append("# Prior attempts\n\n")
        parts.append(
            "Below are your prior attempts and the feedback two independent reviewers gave on each. "
            "The pass count is the only ground-truth signal you receive — you do not see which tests failed or with what input. "
            "Use the reviewer feedback to diagnose what's wrong with your implementation. "
            "Do not regress on cases the prior attempt passed.\n\n"
        )
        for i, att in enumerate(history, start=1):
            parts.append(f"## Attempt {i}\n\n")
            parts.append("### Code\n\n```python\n")
            parts.append(att.code)
            parts.append("\n```\n\n")
            parts.append(f"### Test signal\n\n{att.test_signal}\n\n")
            if att.reviewer_feedback:
                parts.append("### Reviewer feedback\n\n")
                parts.append(_render_feedback(att.reviewer_feedback))
                parts.append("\n")
            if att.arbiter_feedback:
                parts.append("### Independent second-pass feedback\n\n")
                parts.append(_render_feedback(att.arbiter_feedback))
                parts.append("\n")
            if not att.reviewer_feedback and not att.arbiter_feedback:
                parts.append("### Feedback\n\n(none — writer-alone ablation)\n\n")
        parts.append(
            "\nProduce the next attempt. Address the feedback. Preserve correctness on cases the prior attempt passed.\n"
        )
    else:
        parts.append("Produce the implementation. Submit via the submit_solution tool.\n")
    return "".join(parts)


_PASS_COUNT_RE = re.compile(r"(\d+)\s*/\s*(\d+)")


def _parse_pass_count(test_signal: str) -> tuple[int, int] | None:
    """Extract (passed, total) from a test_signal string like '5 / 17 tests
    passing'. Returns None for non-numeric signals (crashes, timeouts,
    collection errors)."""
    m = _PASS_COUNT_RE.search(test_signal)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def render_pass_ranking(history: list[Attempt]) -> str:
    """Render prior attempts as a ranked pass-count list.

    Iter3 H2 intervention: makes the writer's binary-signal exploration
    explicit. Pass counts only — no code, no diffs, no reasoning. Sorted
    by pass count descending (the ranking IS the signal); ties broken by
    attempt index ascending (older attempt cited first within a tie).

    Attempts with no numeric pass count (crashes / timeouts) sort to the
    bottom under a separate marker so the writer can see them too.
    Returns empty string if history has no attempts.
    """
    if not history:
        return ""
    numeric: list[tuple[int, int, int]] = []  # (passed, idx, total)
    non_numeric: list[tuple[int, str]] = []  # (idx, signal)
    for idx, att in enumerate(history, start=1):
        parsed = _parse_pass_count(att.test_signal)
        if parsed is None:
            non_numeric.append((idx, att.test_signal))
        else:
            passed, total = parsed
            numeric.append((passed, idx, total))
    numeric.sort(key=lambda x: (-x[0], x[1]))
    lines = ["# Your prior attempts on this task, ranked by pass count (highest first)\n"]
    for passed, idx, total in numeric:
        lines.append(f"- Attempt {idx}: {passed} / {total} passing")
    for idx, sig in non_numeric:
        lines.append(f"- Attempt {idx}: {sig} (no numeric pass count)")
    lines.append("")
    lines.append(
        "If your most recent attempt has a lower pass count than a prior "
        "attempt, your last change made things worse. Consider reverting "
        "toward the higher-scoring approach.\n"
    )
    return "\n".join(lines) + "\n"


def _render_feedback(items: list[dict]) -> str:
    """Render feedback as terse bullets. Keeps writer context lean.

    When a finding has the iter2 typed-schema fields (finding_type,
    spec_quote, proposed_interpretation) they are rendered inline so the
    writer can weight findings differently. v1 findings without these
    fields render unchanged.
    """
    out_lines = []
    for f in items:
        sev = f.get("severity", "?")
        cat = f.get("category", "?")
        ft = f.get("finding_type")
        desc = f.get("description", "").strip()
        rat = f.get("rationale", "").strip()
        tag = f"{sev}/{cat}" + (f"/{ft}" if ft else "")
        out_lines.append(f"- [{tag}] {desc}")
        sq = (f.get("spec_quote") or "").strip()
        # Only show the spec quote when the critic actually has a validated
        # spec-violation. Models occasionally attach a stray spec_quote to
        # spec-interpretation findings; showing it would mislead the writer
        # into treating the guess as a cited violation.
        if sq and ft == "spec-violation":
            out_lines.append(f"  Spec quote: {sq!r}")
        pi = (f.get("proposed_interpretation") or "").strip()
        if pi:
            out_lines.append(f"  Proposed interpretation: {pi}")
        if rat:
            out_lines.append(f"  Why: {rat}")
    return "\n".join(out_lines) + "\n"


if __name__ == "__main__":
    import sys
    from pathlib import Path

    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(), override=True)

    task = sys.argv[1] if len(sys.argv) > 1 else "task_001"
    spec_path = Path(__file__).parent.parent / "phase2_corpus" / task / "spec.md"
    out = write(spec_path.read_text(), history=None, task_id=task)
    print("=== REASONING ===\n", out.reasoning)
    print("\n=== CODE ===\n", out.code)
