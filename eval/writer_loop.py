"""
Writer-loop driver. Runs the iterative writer ± reviewer ± arbiter loop
for a single task. Designed so the multi-agent mode and the writer-alone
ablation share one driver — the only difference is whether reviewer and
arbiter are called.

Single-task entry point. The corpus runner (eval/phase2_harness.py)
calls this once per task.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

# Make agents/ importable when running this file directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.writer import Attempt, render_pass_ranking, write
from eval.sandbox import TestResult, run_tests

CORPUS_DIR = Path(__file__).parent.parent / "phase2_corpus"


@dataclass
class TaskRun:
    """Outcome of running one task through the loop."""

    task_id: str
    mode: str  # "writer-alone" or "writer+reviewer+arbiter"
    converged: bool
    iterations: int  # how many writer calls were made
    final_passed: int
    final_total: int
    final_crashed: bool
    history: list[Attempt] = field(default_factory=list)
    test_results: list[TestResult] = field(default_factory=list)  # one per attempt, parallel to history
    error: str | None = None


def run_task(
    task_id: str,
    *,
    mode: str = "writer-alone",
    budget: int = 3,
    reviewer_fn=None,
    arbiter_fn=None,
    writer_extra_system: str = "",
    include_pass_ranking: bool = False,
) -> TaskRun:
    """Run the writer loop on a single task.

    :param task_id: directory under phase2_corpus/.
    :param mode: "writer-alone" or "writer+reviewer+arbiter". Reviewer and
        arbiter functions must be supplied for the multi-agent mode.
    :param budget: max writer calls.
    :param reviewer_fn: callable(code: str, spec: str, history: list[Attempt]) -> list[dict].
        History is included so reviewer can spot regressions. Optional.
    :param arbiter_fn: callable(code: str, spec: str, reviewer_findings: list[dict]) -> list[dict].
        NO history — arbiter is the independent second pass. Optional.
    :param writer_extra_system: appended to the writer's system prompt.
        Arm C uses this to add finding-type handling guidance.
    :param include_pass_ranking: arms E and F (iter3 H2). Renders a
        prior-attempt pass-count ranking in the writer prompt at iter ≥ 2.
    """
    spec = (CORPUS_DIR / task_id / "spec.md").read_text()
    history: list[Attempt] = []
    results: list[TestResult] = []

    for it in range(1, budget + 1):
        # Render the ranking block once, here. Pass the same string into
        # write() and into the Attempt log so the two cannot diverge.
        ranking_for_this_call = (
            render_pass_ranking(history)
            if (include_pass_ranking and history)
            else None
        )
        try:
            out = write(
                spec,
                history=history,
                task_id=task_id,
                extra_system=writer_extra_system,
                pass_ranking_block=ranking_for_this_call,
            )
        except Exception as e:
            return TaskRun(
                task_id=task_id,
                mode=mode,
                converged=False,
                iterations=it,
                final_passed=0,
                final_total=0,
                final_crashed=True,
                history=history,
                test_results=results,
                error=f"writer call failed: {type(e).__name__}: {e}",
            )
        if not out.code:
            return TaskRun(
                task_id=task_id,
                mode=mode,
                converged=False,
                iterations=it,
                final_passed=0,
                final_total=0,
                final_crashed=True,
                history=history,
                test_results=results,
                error=f"writer returned empty code: {out.reasoning}",
            )

        result = run_tests(task_id, out.code)
        results.append(result)
        signal = _format_signal(result)

        # Build attempt record. Feedback fields populated below if we're in
        # multi-agent mode and we're going to iterate. pass_ranking_shown
        # captures the ranking block that was shown to the writer *this*
        # iteration (None if not applicable).
        attempt = Attempt(
            code=out.code,
            reasoning=out.reasoning,
            test_signal=signal,
            pass_ranking_shown=ranking_for_this_call,
        )

        if result.all_passed:
            history.append(attempt)
            return TaskRun(
                task_id=task_id,
                mode=mode,
                converged=True,
                iterations=it,
                final_passed=result.passed,
                final_total=result.total,
                final_crashed=False,
                history=history,
                test_results=results,
            )

        # Last iteration: no point gathering feedback we won't use.
        if it == budget:
            history.append(attempt)
            break

        # Gather feedback for the next iteration.
        if mode == "writer+reviewer+arbiter":
            if reviewer_fn is None or arbiter_fn is None:
                raise ValueError("multi-agent mode requires reviewer_fn and arbiter_fn")
            rev = reviewer_fn(out.code, spec, history)  # reviewer SEES history
            arb = arbiter_fn(out.code, spec, rev)        # arbiter sees latest only
            attempt.reviewer_feedback = rev
            attempt.arbiter_feedback = arb
        history.append(attempt)

    final = results[-1]
    return TaskRun(
        task_id=task_id,
        mode=mode,
        converged=False,
        iterations=len(results),
        final_passed=final.passed,
        final_total=final.total,
        final_crashed=final.crashed,
        history=history,
        test_results=results,
    )


def _format_signal(r: TestResult) -> str:
    if r.crashed:
        return "collection error (your code failed to import or has a syntax error). 0 tests ran."
    if r.timed_out:
        return "execution timed out. Likely infinite loop or excessive blocking."
    if r.total == 0:
        return "no tests collected"
    return f"{r.passed} / {r.total} tests passing"


if __name__ == "__main__":
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(), override=True)

    task = sys.argv[1] if len(sys.argv) > 1 else "task_001"
    mode = sys.argv[2] if len(sys.argv) > 2 else "writer-alone"
    budget = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    reviewer_fn = None
    arbiter_fn = None
    if mode == "writer+reviewer+arbiter":
        from agents.writer_arbiter import arbitrate
        from agents.writer_reviewer import review
        reviewer_fn = review
        arbiter_fn = arbitrate

    run = run_task(task, mode=mode, budget=budget, reviewer_fn=reviewer_fn, arbiter_fn=arbiter_fn)
    print(f"\n=== {run.task_id} [{run.mode}] ===")
    print(f"  converged: {run.converged}")
    print(f"  iterations: {run.iterations}")
    print(f"  final: {run.final_passed}/{run.final_total}")
    if run.error:
        print(f"  error: {run.error}")
    for i, r in enumerate(run.test_results, start=1):
        print(f"  iter{i}: passed={r.passed}/{r.total} crashed={r.crashed}")
        if i <= len(run.history):
            att = run.history[i - 1]
            if att.reviewer_feedback or att.arbiter_feedback:
                print(f"    feedback: reviewer={len(att.reviewer_feedback)} arbiter={len(att.arbiter_feedback)}")
