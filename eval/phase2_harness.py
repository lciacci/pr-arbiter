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
                "pass_ranking_shown": att.pass_ranking_shown,
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


# Arm mapping. iter1 arms: A, B. iter2 arm: C (typed schema + iter2 writer
# prompt). iter3 arms (2×2 factorial on top of typed schema): D, E, F.
#
#                 no prior-attempt prompt   + prior-attempt prompt
# no iter2 writer prompt   D                          F
# iter2 writer prompt      C (reuse iter2)            E
#
# All arm-C/D/E/F use the typed reviewer+arbiter (validator-checked
# spec_quote). The mode string passed into TaskRun stays compatible with
# iter1 so writer_loop doesn't need an arm concept.
def _arm_config(arm: str) -> dict:
    if arm == "A" or arm == "writer-alone":
        return {
            "mode": "writer-alone",
            "reviewer_fn": None,
            "arbiter_fn": None,
            "writer_extra_system": "",
            "include_pass_ranking": False,
            "label": "A_writer_alone",
        }
    if arm == "B" or arm == "writer+reviewer+arbiter":
        from agents.writer_arbiter import arbitrate
        from agents.writer_reviewer import review
        return {
            "mode": "writer+reviewer+arbiter",
            "reviewer_fn": review,
            "arbiter_fn": arbitrate,
            "writer_extra_system": "",
            "include_pass_ranking": False,
            "label": "B_writer_reviewer_arbiter",
        }
    if arm == "C" or arm == "writer+reviewer+arbiter+typed":
        from agents.writer import ARM_C_TYPED_FINDINGS_GUIDANCE
        from agents.writer_arbiter_typed import arbitrate
        from agents.writer_reviewer_typed import review
        return {
            "mode": "writer+reviewer+arbiter",
            "reviewer_fn": review,
            "arbiter_fn": arbitrate,
            "writer_extra_system": ARM_C_TYPED_FINDINGS_GUIDANCE,
            "include_pass_ranking": False,
            "label": "C_writer_reviewer_arbiter_typed",
        }
    if arm == "D":
        # H1 control: typed schema only. No iter2 writer prompt, no ranking.
        from agents.writer_arbiter_typed import arbitrate
        from agents.writer_reviewer_typed import review
        return {
            "mode": "writer+reviewer+arbiter",
            "reviewer_fn": review,
            "arbiter_fn": arbitrate,
            "writer_extra_system": "",
            "include_pass_ranking": False,
            "label": "D_typed_no_writer_prompt",
        }
    if arm == "E":
        # H1+H2 combined: typed schema + iter2 writer prompt + ranking.
        from agents.writer import ARM_C_TYPED_FINDINGS_GUIDANCE
        from agents.writer_arbiter_typed import arbitrate
        from agents.writer_reviewer_typed import review
        return {
            "mode": "writer+reviewer+arbiter",
            "reviewer_fn": review,
            "arbiter_fn": arbitrate,
            "writer_extra_system": ARM_C_TYPED_FINDINGS_GUIDANCE,
            "include_pass_ranking": True,
            "label": "E_typed_iter2prompt_plus_ranking",
        }
    if arm == "F":
        # H2 isolated: typed schema + ranking, no iter2 writer prompt.
        from agents.writer_arbiter_typed import arbitrate
        from agents.writer_reviewer_typed import review
        return {
            "mode": "writer+reviewer+arbiter",
            "reviewer_fn": review,
            "arbiter_fn": arbitrate,
            "writer_extra_system": "",
            "include_pass_ranking": True,
            "label": "F_typed_ranking_only",
        }
    raise ValueError(f"unknown arm: {arm!r}")


def main(
    arm: str,
    seed: int = 1,
    budget: int = 3,
    task_filter: list[str] | None = None,
    out_root: Path | None = None,
) -> None:
    """Run one arm × one seed of the iter2 variance experiment.

    Note on `seed`: the Anthropic API does not expose a sampling seed
    parameter, and this harness does not seed any local RNG (there is no
    local stochastic component to seed). `seed` is purely a run-label
    used to partition output directories so that three independent
    sample-of-the-distribution runs do not overwrite each other. Default
    temperature on the API means each call to `messages.create` draws a
    fresh sample from the model's output distribution regardless of the
    seed label.
    """
    load_dotenv(find_dotenv(), override=True)

    cfg = _arm_config(arm)
    mode = cfg["mode"]
    reviewer_fn = cfg["reviewer_fn"]
    arbiter_fn = cfg["arbiter_fn"]
    writer_extra_system = cfg["writer_extra_system"]
    include_pass_ranking = cfg.get("include_pass_ranking", False)
    arm_label = cfg["label"]

    manifest = load_manifest()
    tasks = [t["id"] for t in manifest["tasks"]]
    if task_filter:
        tasks = [t for t in tasks if t in task_filter]

    # Default output root: per-arm, matches the iter where each arm's
    # canonical results live. iter2 arms (A/B/C) → results/phase2/iter2/;
    # iter3 arms (D/E/F) → results/phase2/iter3/. Override with `out_root`
    # if you want to land elsewhere. arm_label starts with the canonical
    # arm letter so a prefix check is robust to legacy aliases.
    if out_root is None:
        canonical_letter = arm_label[0]
        out_root = (RESULTS_DIR / "iter2") if canonical_letter in ("A", "B", "C") else (RESULTS_DIR / "iter3")
    out_dir = out_root / arm_label / f"seed{seed}"
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
                writer_extra_system=writer_extra_system,
                include_pass_ranking=include_pass_ranking,
            )
        except Exception as e:
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
    summary["arm"] = arm_label
    summary["mode"] = mode
    summary["seed"] = seed
    summary["budget"] = budget
    summary["wall_seconds"] = time.time() - t0
    (out_dir.parent / f"seed{seed}_summary.json").write_text(json.dumps(summary, indent=2))

    print("\n=== SUMMARY ===")
    print(f"  arm: {arm_label}  seed: {seed}")
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
        print("usage: python eval/phase2_harness.py <arm> [--seed N] [budget] [task_id ...]")
        print("arms: A | B | C  (or legacy: writer-alone | writer+reviewer+arbiter | writer+reviewer+arbiter+typed)")
        sys.exit(1)
    args = sys.argv[1:]
    arm = args.pop(0)
    seed = 1
    if "--seed" in args:
        i = args.index("--seed")
        if i + 1 >= len(args):
            print("error: --seed requires an integer value", file=sys.stderr)
            sys.exit(2)
        try:
            seed = int(args[i + 1])
        except ValueError:
            print(f"error: --seed value must be an integer, got {args[i + 1]!r}",
                  file=sys.stderr)
            sys.exit(2)
        del args[i : i + 2]
    budget = 3
    remaining = []
    for a in args:
        if a.isdigit() and budget == 3:
            budget = int(a)
        else:
            remaining.append(a)
    filter_tasks = remaining or None
    main(arm, seed=seed, budget=budget, task_filter=filter_tasks)
