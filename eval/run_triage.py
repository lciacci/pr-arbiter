"""
Iter3 runner: load iter2 merged findings, run mutual triage, classify by
confidence, write iter3 results.

Reuses iter2's reviewer + arbiter findings — no fresh review calls. Only the
triage step is new. Output adds per-finding confidence tags and reports both
high-confidence (blocking) and total recall slices.
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

from agents.triage import classify, triage  # noqa: E402
from eval.harness import load_agent_input, score_pr, summarize  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--source",
        default="results/iter2_20260513.json",
        help="Iter2 results JSON to load merged findings from.",
    )
    ap.add_argument("--prs", nargs="+", help="Subset of PR IDs.")
    ap.add_argument(
        "--out",
        default=None,
        help="Output JSON. Default: results/iter3_YYYYMMDD.json",
    )
    args = ap.parse_args()

    src = json.loads(Path(args.source).read_text())
    pr_records = src["per_pr"]
    if args.prs:
        wanted = set(args.prs)
        pr_records = [p for p in pr_records if p["pr_id"] in wanted]

    per_pr = []
    t0 = time.time()
    for p in pr_records:
        pid = p["pr_id"]
        ti = time.time()
        ai = load_agent_input(pid)
        merged = p["final_findings"]
        if merged:
            rv = triage(ai, merged, voice="reviewer")
            av = triage(ai, merged, voice="arbiter")
        else:
            rv, av = [], []
        classified = classify(merged, rv, av)

        high_conf = [f for f, c in classified if c == "high"]
        low_conf = [f for f, c in classified if c == "low"]
        dropped = [f for f, c in classified if c == "drop"]
        final = high_conf + low_conf  # dropped findings are filtered out

        # Score at three slices: high-conf only (blocking), final (high+low),
        # and merged (iter2 baseline — what we started with).
        score_blocking = score_pr(pid, high_conf)
        score_final = score_pr(pid, final)
        score_merged = score_pr(pid, merged)

        elapsed = time.time() - ti
        per_pr.append({
            "pr_id": pid,
            "elapsed_s": round(elapsed, 2),
            "merged_findings": merged,
            "reviewer_votes": rv,
            "arbiter_votes": av,
            "high_conf_findings": high_conf,
            "low_conf_findings": low_conf,
            "dropped_findings": dropped,
            "final_findings": final,
            "score_blocking": asdict(score_blocking),
            "score_final": asdict(score_final),
            "score_merged_baseline": asdict(score_merged),
        })
        print(
            f"  {pid}  expected={score_final.expected}  "
            f"merged={len(merged)} -> high={len(high_conf)} low={len(low_conf)} dropped={len(dropped)}  "
            f"final_match={score_final.matched} blocking_match={score_blocking.matched}  ({elapsed:.1f}s)",
            flush=True,
        )

    scores_final = [score_pr(p["pr_id"], p["final_findings"]) for p in per_pr]
    scores_blocking = [score_pr(p["pr_id"], p["high_conf_findings"]) for p in per_pr]
    scores_merged = [score_pr(p["pr_id"], p["merged_findings"]) for p in per_pr]

    summary = {
        "merged_baseline": summarize(scores_merged),
        "final_high_plus_low": summarize(scores_final),
        "blocking_high_only": summarize(scores_blocking),
    }

    out = {
        "run_date": date.today().isoformat(),
        "mode": "iter3 mutual-triage",
        "source_iter2": args.source,
        "total_elapsed_s": round(time.time() - t0, 2),
        "pr_count": len(per_pr),
        "summary": summary,
        "per_pr": per_pr,
    }

    out_path = Path(args.out) if args.out else ROOT / "results" / f"iter3_{date.today().strftime('%Y%m%d')}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {out_path}")
    for name, s in summary.items():
        o = s["overall"]
        print(f"  {name:24}  recall {o['recall']:.2%}  precision {o['precision']:.2%}  fp {o['false_positives']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
