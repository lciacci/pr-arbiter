# Iteration 2 notes — pr-arbiter

Run date: 2026-05-13. Architectural change: arbiter is now an independent
second-pass reviewer that can ADD findings, not a triage filter.

## What changed

- Arbiter prompt rewritten. Sees the reviewer's findings as context, instructed
  to focus on what the reviewer missed (correctness-criticals, architectural
  issues, behavior changes hiding under style refactors), explicitly told NOT
  to re-report the reviewer's findings.
- New tool `report_independent_findings` (was `report_triaged_findings`).
- New module function `merge_findings(reviewer, arbiter)` — union with
  approximate-match dedup (same file + category + line midpoint within ±3).
  When duplicates exist, keeps the higher-severity version.
- `eval/run_baseline.py` now captures all three lists per PR
  (reviewer_findings, arbiter_findings, final_findings) so we can inspect
  what the arbiter added independently of what survives the merge.
- Reviewer prompt unchanged from v2.

## Headline result

| config                          | recall | precision | FP | critical | high | medium | low  | neg-ctrl |
|---------------------------------|-------:|----------:|---:|---------:|-----:|-------:|-----:|---------:|
| v2 rev-alone                    |  52.7% |     60.4% | 19 |    6/8   | 8/11 | 11/18  | 4/18 |    1/3   |
| **iter2 rev + indep arb (merge)** | **61.8%** |     49.3% | 35 |  **7/8** | 8/11 | 11/18  | 8/18 |    2/3   |
| (reference: iter1 v2 strict arb)|  38.2% |     70.0% |  9 |    4/8   | 6/11 |  7/18  | 4/18 |    1/3   |
| (reference: v1 lenient over v2) |  40.0% |     56.4% | 17 |    6/8   | 6/11 |  7/18  | 3/18 |    1/3   |

The independent-arbiter architecture **catches things the reviewer alone
misses, including a critical security bug**. Recall +9.1 pp over v2 reviewer
alone, critical recall +1 (6/8 → 7/8). The architecture hypothesis — that a
second agent can add signal a first cannot — is supported on this corpus.

The cost is 16 added false positives, dropping precision from 60.4 % to
49.3 %. Negative control failures went from 1/3 to 2/3 — the arbiter
introduced a new FP on a previously clean PR (pr_018) and added a second FP
on the persistent pr_007 hallucination.

## The headline catch

`pr_009` F1 (Priya, critical security): the new code uses regex-based HTML
sanitization. The reviewer missed it across both baseline and iter1 runs —
it was in `v2_missed` every time. The independent arbiter flagged it with
the correct severity (critical) and category (security). This is exactly the
pattern that justifies a second pass: the bug requires recognizing that
"strip tags with regex" is an anti-pattern, which is more semantic than
syntactic, and a different framing surfaces it where the same prompt twice
would not.

## Other newly caught (all low-severity)

| PR     | Finding                                          | Sev | Notes                                       |
|--------|---------------------------------------------------|-----|---------------------------------------------|
| pr_001 | Local `import logging` inside the function       | low | Rubric F5. Arbiter caught what reviewer suppressed under "pick lower tier". |
| pr_011 | Return type `dict`, but `pickle.loads` can return any type | low | Arbiter as type-system reader. |
| pr_014 | `request.get_data()` consumes the stream         | low | Subtle middleware concern. |
| pr_016 | `success: False` field redundant with `error` present | low | API design nit, low value. |

The 4 lows account for most of the recall gain, but they're nits — the
critical catch on pr_009 is the load-bearing result.

## Where the FPs came from

The arbiter generated 16 new findings that didn't match anything in the
rubric. Two patterns explain most of them:

1. **Restating the reviewer with a different mechanism.** On pr_001 the
   reviewer flagged "bare except returns None and breaks contract"; the
   arbiter flagged "function typed Response but has implicit None return."
   Same bug, different framing, line midpoints 7 apart (outside ±3 merge
   tolerance), both counted. The merge tolerance is too tight, but loosening
   it risks dropping legitimately distinct findings nearby.

2. **Over-eager pattern matching on plausible-looking code.** On pr_018
   (clean refactor), the arbiter saw `default if not val else ...` logic
   and flagged a "what if val is empty string" issue. The behavior is
   actually correct under the function's contract, but the arbiter has no
   way to distinguish "this is intentional" from "this is a bug" without
   the original spec. Same pattern on pr_007.

Pattern 1 is fixable (merge dedup tuning). Pattern 2 is the architecture's
weakness — independent review without spec increases false-positive risk on
clean code.

## Architecture verdict

The hypothesis "multi-agent code review beats single-agent" now has evidence
on both sides:

- **For:** independent arbiter caught a critical security bug the reviewer
  missed across multiple runs. Recall went up meaningfully. The architecture
  is doing the thing it's supposed to do.
- **Against:** precision dropped 11 pp and negative control failures
  doubled. For a practical merge gate, the FP rate (~1.75 per PR) is too
  high to trust.

The right framing isn't "does multi-agent beat single-agent" but "what's
the precision–recall operating point we want?" Iter2 trades 11 pp precision
for 9 pp recall plus one extra critical caught. Whether that's a win
depends on the use case. For a security-leaning review where missing a
critical is qualitatively worse than a false positive, iter2 is the answer.
For a noise-sensitive merge gate, v2 reviewer-alone is.

## Iter3 directions (in priority order)

1. **Precision-recovery pass over the merged list.** Add a final small step
   that triages merged findings against the same skepticism bar as the
   strict v2 arbiter — but applied to BOTH agents' findings, not just the
   reviewer's. The strict prompt dropped criticals when applied to reviewer
   output alone; with two agents' findings in front of it, the criticals
   are double-supported and harder to drop. This is the cheapest move.
2. **Tighter arbiter calibration on clean PRs.** Add explicit framing:
   "the first reviewer's empty output is a strong prior. If you cannot point
   to a behavior change in the diff that creates a bug, return empty."
   Targets the pr_018 false positive specifically.
3. **Confidence scores from the arbiter.** Add a `confidence` field (low /
   medium / high) and only merge high-confidence arbiter findings. Tests
   whether the arbiter knows when it's guessing.
4. **Merge tolerance tuning.** ±3 line midpoint is too tight; some
   reviewer/arbiter pairs describe the same bug 5-7 lines apart. Bump to
   ±5 and check whether legitimately distinct findings get folded.

Iter3 = option 1, with option 2 layered in if cheap. Skip 3 and 4 unless 1
and 2 don't recover precision.

If iter3 fails to recover precision while preserving the critical catch,
the bailout becomes mutation testing — but the architectural finding from
iter2 is already strong enough to write up.

## Persistent issues (now four runs deep)

- `pr_007` Marcus negative control: 1 FP from reviewer in every run, plus
  1 from arbiter in iter2. The reviewer's "this looks like a placeholder"
  pattern match is durable. Fix has to come from the reviewer side, probably
  via a "before flagging, check if the unchanged code does the same thing"
  rule.
- Two criticals remain uncaught across all five configurations: pr_015 F1
  (missing JSON validation) and pr_017 F1 (config set-but-not-persisted).
  These look like genuine reasoning ceilings rather than prompt problems.
  Worth a focused experiment if iter3 doesn't surface them.

## Artifacts

- `results/iter2_20260513.json` — full iter2 results.
- `results/iter2_run.log` — raw stdout (gitignored).
- `agents/arbiter.py` — independent-reviewer prompt + tool + merge function.
- `eval/run_baseline.py` — captures arbiter_findings separately from final.
