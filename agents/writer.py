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


def write(spec: str, history: list[Attempt] | None = None, task_id: str = "") -> WriterOutput:
    """Run the writer agent. Returns full module source + reasoning.

    :param spec: task spec.md contents.
    :param history: prior attempts in order. Latest is most recent.
    :param task_id: for logging only; not shown to the agent.
    """
    user_msg = _format_user_message(spec, history or [])
    resp = _client().messages.create(
        model=MODEL,
        max_tokens=8192,
        system=WRITER_SYSTEM,
        tools=[SUBMIT_TOOL],
        tool_choice={"type": "tool", "name": "submit_solution"},
        messages=[{"role": "user", "content": user_msg}],
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "submit_solution":
            code = block.input.get("code", "")
            reasoning = block.input.get("reasoning", "")
            return WriterOutput(code=code, reasoning=reasoning)
    return WriterOutput(code="", reasoning="agent did not call submit_solution")


def _format_user_message(spec: str, history: list[Attempt]) -> str:
    parts = [
        "Implement the following specification.\n\n# Specification\n\n",
        spec,
        "\n\n",
    ]
    if history:
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


def _render_feedback(items: list[dict]) -> str:
    """Render feedback as terse bullets. Keeps writer context lean."""
    out_lines = []
    for f in items:
        sev = f.get("severity", "?")
        cat = f.get("category", "?")
        desc = f.get("description", "").strip()
        rat = f.get("rationale", "").strip()
        out_lines.append(f"- [{sev}/{cat}] {desc}")
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
