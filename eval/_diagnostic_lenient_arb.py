"""
One-off diagnostic: v1 (lenient) arbiter prompt over v2 reviewer findings.

The question: does ANY arbiter help a well-calibrated reviewer? If even the
lenient v1 prompt loses to reviewer-alone, the filter-only arbiter architecture
is dead and iter2 should rethink the arbiter's job.

This script is not part of the regular pipeline — it inlines the v1 system
prompt to avoid mutating agents/arbiter.py. Delete after iter2 decision.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(find_dotenv(), override=True)

from anthropic import Anthropic  # noqa: E402

from agents.arbiter import ARBITER_TOOL, _strip_rationale, _validate  # noqa: E402
from eval.harness import load_agent_input, score_pr, summarize  # noqa: E402

# Verbatim v1 arbiter system prompt (the original lenient version).
V1_ARBITER_SYSTEM = """You are an arbiter triaging a code reviewer's findings on a pull request. The reviewer was instructed to be adversarial; your job is the opposite — precision over recall.

Your principles:
- Reviewer optimizes for catching everything. You optimize for what should actually block or land in the PR.
- You should be willing to drop findings. A finding survives only if you can confirm it from the diff and the surrounding code. If the reviewer's rationale doesn't hold up when you re-read the after-state, drop it.
- Some PRs have no real issues. Returning an empty list is the right answer on a clean refactor. Do not preserve findings just because the reviewer wrote them.
- Demote severity when the reviewer inflated it. A real issue at the wrong tier is still a finding worth keeping, but at the correct severity.
- Do not invent new findings. Your output must be a subset of (or re-prioritization of) the reviewer's findings — same file, same approximate location. If the reviewer missed something, that is a reviewer problem, not an arbiter problem.

For each finding you keep, write a short rationale describing why it survives arbitration. This is for offline debugging, not graded."""

MODEL = "claude-sonnet-4-6"
_CLIENT = Anthropic()


def arbitrate_v1(agent_input: dict) -> list[dict]:
    user_msg = (
        "Triage the reviewer's findings on this pull request.\n\n"
        "# Diff\n\n```\n" + agent_input["diff"] + "\n```\n\n"
        "# Before (full file)\n\n```python\n" + agent_input["before"] + "\n```\n\n"
        "# After (full file)\n\n```python\n" + agent_input["after"] + "\n```\n\n"
        "# Reviewer's findings\n\n```json\n"
        + json.dumps(agent_input["reviewer_findings"], indent=2)
        + "\n```\n\n"
        "Return your triaged findings via the report_triaged_findings tool. "
        "Drop, demote, or re-prioritize as you see fit. Empty list is valid."
    )
    resp = _CLIENT.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=V1_ARBITER_SYSTEM,
        tools=[ARBITER_TOOL],
        tool_choice={"type": "tool", "name": "report_triaged_findings"},
        messages=[{"role": "user", "content": user_msg}],
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "report_triaged_findings":
            return _strip_rationale(_validate(block.input.get("findings", [])))
    return []


def main() -> int:
    cache = json.loads(Path("results/iter1_20260513.json").read_text())
    per_pr = []
    t0 = time.time()
    for p in cache["per_pr"]:
        pid = p["pr_id"]
        ti = time.time()
        ai = load_agent_input(pid)
        final = arbitrate_v1({**ai, "reviewer_findings": p["reviewer_findings"]})
        sc = score_pr(pid, final)
        elapsed = time.time() - ti
        per_pr.append({
            "pr_id": pid,
            "elapsed_s": round(elapsed, 2),
            "reviewer_findings": p["reviewer_findings"],
            "final_findings": final,
            "score": asdict(sc),
        })
        print(
            f"  {pid}  persona={sc.persona}  expected={sc.expected}  "
            f"matched={sc.matched}  fp={sc.false_positives}  ({elapsed:.1f}s)",
            flush=True,
        )

    scores = [score_pr(p["pr_id"], p["final_findings"]) for p in per_pr]
    summary = summarize(scores)
    out = {
        "run_date": "2026-05-13",
        "mode": "v2_reviewer + v1_lenient_arbiter (diagnostic)",
        "total_elapsed_s": round(time.time() - t0, 2),
        "pr_count": len(per_pr),
        "summary": summary,
        "per_pr": per_pr,
    }
    Path("results/iter1_v2rev_v1arb.json").write_text(json.dumps(out, indent=2))
    o = summary["overall"]
    print(f"\nOverall recall: {o['recall']:.2%}  precision: {o['precision']:.2%}  FP: {o['false_positives']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
