"""
Run a baseline eval pass and write the results JSON.

Usage:
    python eval/run_baseline.py                    # reviewer-alone, all PRs
    python eval/run_baseline.py --with-arbiter     # reviewer + arbiter
    python eval/run_baseline.py --prs pr_001 pr_002

Output:
    results/baseline_YYYYMMDD[_arbiter].json — per-PR findings + summary.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import date
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv(find_dotenv(), override=True)

from agents.reviewer import review  # noqa: E402
from eval.harness import list_pr_ids, load_agent_input, run_eval, score_pr, summarize  # noqa: E402


def _load_arbiter():
    """Lazy-import arbiter so this script runs before arbiter.py exists.

    Returns (arbitrate_fn, merge_fn) — the merge function is iter2; older
    arbiter modules without merge_findings return (arbitrate_fn, None) and the
    runner falls back to using the arbiter output as the final list.
    """
    try:
        from agents.arbiter import arbitrate
    except ImportError:
        return None, None
    try:
        from agents.arbiter import merge_findings
    except ImportError:
        merge_findings = None
    return arbitrate, merge_findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-arbiter", action="store_true", help="Run reviewer+arbiter pipeline.")
    ap.add_argument("--prs", nargs="+", help="Subset of PR IDs to run.")
    ap.add_argument("--out", help="Output JSON path. Default: results/baseline_YYYYMMDD[_arbiter].json")
    ap.add_argument(
        "--reviewer-from",
        help="Path to a prior baseline JSON. Skips reviewer calls; uses its "
             "reviewer_findings as input to the arbiter. Required for clean "
             "ablation against an earlier baseline.",
    )
    args = ap.parse_args()

    pr_ids = args.prs or list_pr_ids()
    arbiter_fn = None
    merge_fn = None
    if args.with_arbiter:
        arbiter_fn, merge_fn = _load_arbiter()
        if arbiter_fn is None:
            print("ERROR: --with-arbiter requested but agents/arbiter.py not found.", file=sys.stderr)
            return 1

    reviewer_cache: dict[str, list[dict]] = {}
    if args.reviewer_from:
        prior = json.loads(Path(args.reviewer_from).read_text())
        for p in prior["per_pr"]:
            reviewer_cache[p["pr_id"]] = p["reviewer_findings"]
        print(f"Loaded reviewer findings for {len(reviewer_cache)} PRs from {args.reviewer_from}")

    # We run manually rather than via run_eval() so we can capture raw findings
    # per PR (not just the score). The score JSON is the primary artifact, but
    # raw findings let us inspect mistakes without re-running the agents.
    per_pr = []
    t0 = time.time()
    for pr_id in pr_ids:
        ti = time.time()
        agent_input = load_agent_input(pr_id)
        if pr_id in reviewer_cache:
            reviewer_out = reviewer_cache[pr_id]
        else:
            reviewer_out = review(agent_input)
        arbiter_out: list[dict] = []
        if arbiter_fn is not None:
            arbiter_out = arbiter_fn({**agent_input, "reviewer_findings": reviewer_out})
            if merge_fn is not None:
                # iter2 path: arbiter returns its own findings; runner unions
                # with reviewer findings using approximate-match dedup.
                final = merge_fn(reviewer_out, arbiter_out)
            else:
                # iter0/iter1 path: arbiter's output IS the final list (filter).
                final = arbiter_out
        else:
            final = reviewer_out
        score = score_pr(pr_id, final)
        elapsed = time.time() - ti
        per_pr.append({
            "pr_id": pr_id,
            "elapsed_s": round(elapsed, 2),
            "reviewer_findings": reviewer_out,
            "arbiter_findings": arbiter_out,
            "final_findings": final,
            "score": asdict(score),
        })
        print(
            f"  {pr_id}  persona={score.persona}  expected={score.expected}  "
            f"matched={score.matched}  fp={score.false_positives}  ({elapsed:.1f}s)",
            flush=True,
        )

    scores = [score_pr(p["pr_id"], p["final_findings"]) for p in per_pr]
    summary = summarize(scores)
    total_s = time.time() - t0

    out = {
        "run_date": date.today().isoformat(),
        "mode": "reviewer+arbiter" if arbiter_fn is not None else "reviewer-alone",
        "total_elapsed_s": round(total_s, 2),
        "pr_count": len(pr_ids),
        "summary": summary,
        "per_pr": per_pr,
    }

    if args.out:
        out_path = Path(args.out)
    else:
        tag = "_arbiter" if arbiter_fn is not None else ""
        out_path = ROOT / "results" / f"baseline_{date.today().strftime('%Y%m%d')}{tag}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {out_path}")
    print(f"Overall recall: {summary['overall']['recall']:.2%}  "
          f"precision: {summary['overall']['precision']:.2%}  "
          f"FP: {summary['overall']['false_positives']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
