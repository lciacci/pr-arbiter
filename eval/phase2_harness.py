"""
Phase 2 corpus runner. Runs every task in phase2_corpus/manifest.json
through writer_loop.run_task in the chosen mode, persists per-run JSON,
and prints a summary.

Usage:
    python eval/phase2_harness.py writer-alone               # ablation
    python eval/phase2_harness.py writer+reviewer+arbiter    # multi-agent

Results land in results/phase2/<mode>/<task_id>.json plus a summary
results/phase2/<mode>_summary.json.
"""

from __future__ import annotations

import dataclasses
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import find_dotenv, load_dotenv

from eval.writer_loop import TaskRun, run_task

CORPUS_DIR = ROOT / "phase2_corpus"
RESULTS_DIR = ROOT / "results" / "phase2"


def load_manifest() -> dict:
    return json.loads((CORPUS_DIR / "manifest.json").read_text())


def serialize_run(run: TaskRun) -> dict:
    """Convert TaskRun to a JSON-safe dict. Strip raw stdout/stderr from
    test_results to keep payload sane — they're useful for live debugging
    but bloat the persisted artifact."""
    history_out = []
    for att in run.history:
        history_out.append(
            {
                "code": att.code,
                "reasoning": att.reasoning,
                "test_signal": att.test_signal,
                "reviewer_feedback": att.reviewer_feedback,
                "arbiter_feedback": att.arbiter_feedback,
            }
        )
    tr_out = []
    for r in run.test_results:
        tr_out.append(
            {
                "passed": r.passed,
                "failed": r.failed,
                "errors": r.errors,
                "total": r.total,
                "all_passed": r.all_passed,
                "crashed": r.crashed,
                "timed_out": r.timed_out,
                # failure_summaries kept — useful for offline analysis;
                # NEVER fed back to the writer at runtime.
                "failure_summaries": r.failure_summaries,
            }
        )
    return {
        "task_id": run.task_id,
        "mode": run.mode,
        "converged": run.converged,
        "iterations": run.iterations,
        "final_passed": run.final_passed,
        "final_total": run.final_total,
        "final_crashed": run.final_crashed,
        "error": run.error,
        "history": history_out,
        "test_results": tr_out,
    }


def summarize(runs: list[TaskRun], manifest: dict) -> dict:
    by_difficulty: dict[str, dict] = {}
    diff_of = {t["id"]: t["difficulty"] for t in manifest["tasks"]}

    total = len(runs)
    converged = sum(1 for r in runs if r.converged)
    crashed = sum(1 for r in runs if r.final_crashed)
    total_iters = sum(r.iterations for r in runs)
    total_tests = sum(r.final_total for r in runs)
    total_passed = sum(r.final_passed for r in runs)

    for r in runs:
        d = diff_of.get(r.task_id, "unknown")
        b = by_difficulty.setdefault(d, {"n": 0, "converged": 0, "iter_sum": 0, "passed": 0, "total": 0})
        b["n"] += 1
        b["converged"] += 1 if r.converged else 0
        b["iter_sum"] += r.iterations
        b["passed"] += r.final_passed
        b["total"] += r.final_total

    for d, row in by_difficulty.items():
        row["pass_rate"] = row["converged"] / row["n"] if row["n"] else 0.0
        row["avg_iters"] = row["iter_sum"] / row["n"] if row["n"] else 0.0
        row["test_recall"] = row["passed"] / row["total"] if row["total"] else 0.0

    return {
        "overall": {
            "tasks": total,
            "converged": converged,
            "pass_rate": converged / total if total else 0.0,
            "crashed": crashed,
            "avg_iterations": total_iters / total if total else 0.0,
            "test_recall": total_passed / total_tests if total_tests else 0.0,
            "total_tests": total_tests,
            "total_passed": total_passed,
        },
        "by_difficulty": by_difficulty,
        "per_task": [
            {
                "task_id": r.task_id,
                "converged": r.converged,
                "iterations": r.iterations,
                "passed": r.final_passed,
                "total": r.final_total,
                "crashed": r.final_crashed,
            }
            for r in runs
        ],
    }


def main(mode: str, budget: int = 3, task_filter: list[str] | None = None) -> None:
    load_dotenv(find_dotenv(), override=True)

    reviewer_fn = None
    arbiter_fn = None
    if mode == "writer+reviewer+arbiter":
        from agents.writer_arbiter import arbitrate
        from agents.writer_reviewer import review
        reviewer_fn = review
        arbiter_fn = arbitrate
    elif mode != "writer-alone":
        raise ValueError(f"unknown mode: {mode}")

    manifest = load_manifest()
    tasks = [t["id"] for t in manifest["tasks"]]
    if task_filter:
        tasks = [t for t in tasks if t in task_filter]

    out_dir = RESULTS_DIR / mode.replace("+", "_")
    out_dir.mkdir(parents=True, exist_ok=True)

    runs: list[TaskRun] = []
    t0 = time.time()
    for i, task_id in enumerate(tasks, start=1):
        print(f"[{i}/{len(tasks)}] {task_id} ...", flush=True)
        ti = time.time()
        try:
            run = run_task(
                task_id,
                mode=mode,
                budget=budget,
                reviewer_fn=reviewer_fn,
                arbiter_fn=arbiter_fn,
            )
        except Exception as e:
            # Surface but don't abort; per-task isolation.
            print(f"    EXCEPTION: {type(e).__name__}: {e}", flush=True)
            run = TaskRun(
                task_id=task_id,
                mode=mode,
                converged=False,
                iterations=0,
                final_passed=0,
                final_total=0,
                final_crashed=True,
                error=f"{type(e).__name__}: {e}",
            )
        runs.append(run)
        elapsed = time.time() - ti
        (out_dir / f"{task_id}.json").write_text(json.dumps(serialize_run(run), indent=2))
        status = "OK" if run.converged else ("CRASH" if run.final_crashed else "FAIL")
        print(
            f"    {status}  iters={run.iterations}  {run.final_passed}/{run.final_total}  ({elapsed:.1f}s)",
            flush=True,
        )

    summary = summarize(runs, manifest)
    summary["mode"] = mode
    summary["budget"] = budget
    summary["wall_seconds"] = time.time() - t0
    (RESULTS_DIR / f"{mode.replace('+', '_')}_summary.json").write_text(json.dumps(summary, indent=2))

    print("\n=== SUMMARY ===")
    print(f"  mode: {mode}")
    print(f"  pass rate: {summary['overall']['converged']}/{summary['overall']['tasks']} "
          f"({summary['overall']['pass_rate']*100:.1f}%)")
    print(f"  test recall: {summary['overall']['total_passed']}/{summary['overall']['total_tests']} "
          f"({summary['overall']['test_recall']*100:.1f}%)")
    print(f"  avg iterations: {summary['overall']['avg_iterations']:.2f}")
    print(f"  crashes: {summary['overall']['crashed']}")
    print(f"  wall time: {summary['wall_seconds']:.1f}s")
    print(f"\n  by difficulty:")
    for d, row in summary["by_difficulty"].items():
        print(f"    {d:10s}  {row['converged']}/{row['n']} pass  "
              f"(test {row['test_recall']*100:.1f}%, avg {row['avg_iters']:.1f} iter)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python eval/phase2_harness.py <mode> [budget] [task_id ...]")
        print("modes: writer-alone | writer+reviewer+arbiter")
        sys.exit(1)
    mode = sys.argv[1]
    budget = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 3
    filter_tasks = [a for a in sys.argv[3:] if not a.isdigit()]
    main(mode, budget=budget, task_filter=filter_tasks or None)
