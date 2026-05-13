# Diagnostic: lenient arbiter over v2 reviewer

Run date: 2026-05-13. Cheap pre-iter2 check.

## Question

Iter1 showed v2 reviewer-alone beats v2 reviewer + v2-strict-arbiter. But that
could mean either (a) the v2 arbiter prompt is too aggressive, or (b) no
filter-only arbiter can help a well-calibrated reviewer. The iter1 v2 arbiter
dropped two criticals, which suggests (a) — but doesn't rule out (b).

This diagnostic re-runs the **lenient v1 arbiter prompt** against the cached
**v2 reviewer findings**. That's the missing cell from iter1.

## Result

| config                       | recall | precision | FP | critical | high | medium | low  | neg-ctrl |
|------------------------------|-------:|----------:|---:|---------:|-----:|-------:|-----:|---------:|
| v2 rev-alone                 |  52.7% |     60.4% | 19 |    6/8   | 8/11 | 11/18  | 4/18 |    1/3   |
| **v2 rev + v1 lenient arb**  | **40.0%** | **56.4%** | **17** |    6/8   | 6/11 |  7/18  | 3/18 |    1/3   |
| v2 rev + v2 strict arb       |  38.2% |     70.0% |  9 |    4/8   | 6/11 |  7/18  | 4/18 |    1/3   |

## Reading

The lenient arbiter is **strictly worse than reviewer-alone on every metric
except FP count**. It preserves criticals (6/8, same as reviewer) but drops
true positives faster than it drops false positives — recall craters −12.7 pp
while precision actually moves the wrong direction by 4 points.

This isn't a prompt-tuning problem. The lenient and strict arbiters bound the
behavior space of filter-only arbitration:

- Strict (drop by default) gains precision but sacrifices criticals. Unsafe.
- Lenient (keep if defensible) preserves criticals but trades 1 TP for ~0.5
  FP. Worse than just running the reviewer.

The arbiter is genuinely seeing the same code as the reviewer. When it
disagrees enough to drop a finding, it's almost as likely to be wrong (drop a
TP) as the reviewer was when it included the finding. The "second opinion"
isn't independent enough to add signal because both agents are reading the same
diff with the same model under similar prompt pressure.

## Implication for the architecture

The kickoff doc framed the load-bearing question as: "is reviewer + arbiter
better than reviewer alone?" The answer on this corpus, with this architecture
(filter-only arbiter, no-new-findings rule), is **no**, across both prompt
extremes.

That doesn't kill multi-agent for code review. It kills the *filter* role for
the second agent. Options that remain on the table:

1. **Independent reviewer + arbiter that can ADD findings** — relax the
   no-new-findings rule. Arbiter independently reviews the diff (perhaps with a
   different framing — "what's the worst bug here?" instead of generic
   review). Then a merge step combines the two finding lists. Tests whether
   the second agent surfaces things the first missed.

2. **Reviewer self-critique loop** — single agent, two passes. First pass
   produces findings; second pass critiques the first pass's findings. No
   second model call. Cheaper, less context overhead. Worth comparing to (1).

3. **Mutation testing pivot** — kickoff bailout. Drop prompted eval, use
   programmatically-generated mutations as ground truth. Eliminates the
   rubric-authoring bottleneck but requires writing a mutation framework.

My recommendation: iter2 = option 1, with a hard scope: change only the
arbiter (independent review, allow new findings), keep the v2 reviewer
prompt frozen, run against the same 20-PR corpus, compare. If option 1 also
fails to beat reviewer-alone, iter3 is the mutation pivot.

## What persists

- pr_007 negative control still produces a FP across **all five** configurations
  now tested. The reviewer's "this looks like a placeholder, surely it's a bug"
  instinct is durable, and no filter-only arbiter undoes it. The fix has to
  come from the reviewer side, not the arbiter side.
- Critical ceiling is still 6/8 across all configurations. pr_015 (missing JSON
  validation) and pr_017 (config set-but-not-persisted) remain uncaught by any
  reviewer prompt tried so far.

## Artifacts

- `results/iter1_v2rev_v1arb.json` — diagnostic output.
- `eval/_diagnostic_lenient_arb.py` — one-off script. Delete after iter2.
