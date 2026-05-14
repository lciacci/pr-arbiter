"""
Dashboard: show all eval configurations side-by-side from saved results JSONs.

Reads the canonical result files in results/ and prints a comparison table
to stdout. Useful for a quick "where do we stand?" check or for sanity-
checking after a new iteration.

Usage:
    python eval/show_results.py
    python eval/show_results.py --corrected   # apply iter4 corpus correction
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.harness import score_pr, summarize  # noqa: E402
import eval.harness as harness  # noqa: E402

CORRECTED_PR_007 = {
    "pr_id": "pr_007",
    "category": "style_with_latent_bug",
    "persona": "Marcus",
    "summary": "_parse_env_bool docstring/impl mismatch + inverted vs get_debug_flag.",
    "source": "pallets/flask v3.0.0 src/flask/helpers.py",
    "expected_findings": [
        {
            "id": "F1",
            "category": "correctness",
            "severity": "medium",
            "file": "after.py",
            "line_range": [35, 47],
            "description": "_parse_env_bool docstring/implementation mismatch and inverted semantics vs sibling get_debug_flag.",
        }
    ],
    "should_not_flag": [],
    "notes_for_arbiter": "Borderline; runtime behavior of single existing caller preserved.",
}

RUNS = [
    ("v1 reviewer-alone",        "results/baseline_20260513.json",          "final_findings"),
    ("v1 reviewer + filter arb", "results/baseline_20260513_arbiter.json",  "final_findings"),
    ("v2 reviewer-alone",        "results/iter1_20260513.json",             "final_findings"),
    ("v2 + strict arbiter",      "results/iter1_20260513_arbiter.json",     "final_findings"),
    ("v2 + indep arbiter (iter2)", "results/iter2_20260513.json",           "final_findings"),
    ("iter3 final (high+low)",   "results/iter3_20260513.json",             "final_findings"),
    ("iter3 blocking (high)",    "results/iter3_20260513.json",             "high_conf_findings"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--corrected",
        action="store_true",
        help="Apply the iter4 pr_007 corpus correction (in-memory only).",
    )
    args = ap.parse_args()

    if args.corrected:
        _orig = harness.load_rubric

        def patched(pr_id):
            return CORRECTED_PR_007 if pr_id == "pr_007" else _orig(pr_id)

        harness.load_rubric = patched

    print(f"{'configuration':<28} {'recall':>8} {'prec':>8} {'FP':>4} {'crit':>6} {'high':>6} {'med':>6} {'low':>6} {'NC':>5}")
    print("-" * 80)
    for name, path, key in RUNS:
        p = Path(path)
        if not p.exists():
            print(f"{name:<28}  (missing: {path})")
            continue
        data = json.loads(p.read_text())
        scores = [score_pr(rec["pr_id"], rec.get(key) or rec.get("final_findings", [])) for rec in data["per_pr"]]
        s = summarize(scores)
        o = s["overall"]
        bs = s["by_severity"]
        nc = s["negative_controls"]
        def sr(sev: str) -> str:
            row = bs.get(sev, {})
            return f"{row.get('matched', 0)}/{row.get('expected', 0)}"
        nc_str = f"{nc['failures']}/{nc['total']}"
        print(f"{name:<28} {o['recall']:>7.1%} {o['precision']:>7.1%} {o['false_positives']:>4} {sr('critical'):>6} {sr('high'):>6} {sr('medium'):>6} {sr('low'):>6} {nc_str:>5}")
    print()
    tag = "WITH iter4 pr_007 correction" if args.corrected else "as-measured (rubric unchanged)"
    print(f"Scoring: {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
