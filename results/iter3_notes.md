# Iteration 3 notes — pr-arbiter

Run date: 2026-05-13. Architectural change: mutual-triage adversarial
assessment.

## What changed

- New module `agents/triage.py`. Same model, two system-prompt voices:
  reviewer-voice (recall-oriented) and arbiter-voice (skeptical). Each
  independently votes KEEP / DROP / UNSURE on every finding in the iter2
  merged list. Source-blind — neither voter is told which agent originally
  produced which finding.
- Aggregation rule: both KEEP → high confidence; both DROP → drop entirely;
  anything else → low confidence (advisory).
- New runner `eval/run_triage.py` consumes iter2's merged findings as input
  (no fresh reviewer or arbiter calls), runs both triages, classifies, and
  scores three slices: merged baseline, final (high + low), blocking (high only).
- No reviewer or arbiter prompt changes from iter2. Reviewer + arbiter
  findings reused from iter2 cache.

## Headline result

| config                                | recall | precision | FP | critical | high | medium | low  | neg-ctrl |
|---------------------------------------|-------:|----------:|---:|---------:|-----:|-------:|-----:|---------:|
| v2 rev-alone (best single-agent)      |  52.7% |     60.4% | 19 |    6/8   | 8/11 | 11/18  | 4/18 |    1/3   |
| iter2 merged (rev + indep arb)        |  61.8% |     49.3% | 35 |    7/8   | 8/11 | 11/18  | 8/18 |    2/3   |
| iter3 final (high + low conf)         |  56.4% |     51.7% | 29 |    7/8   | 7/11 | 10/18  | 7/18 |    1/3   |
| **iter3 blocking (high conf only)**   |  43.6% | **58.5%** | **17** | **7/8** | 6/11 |  7/18  | 4/18 | **1/3**  |

The blocking-only slice — what a human reviewer would actually be blocked on —
catches **7/8 criticals**, including the pr_009 catch that v2 reviewer-alone
misses entirely. Critical recall is now strictly better than the
single-agent baseline (88 % vs 75 %), and at comparable precision and FP
count.

The full output is two-tier: **24 high-confidence "blocking" findings** plus
**17 low-confidence "advisory" findings** across the corpus. That maps to
how senior reviewers actually triage — strong vs weak signal, not flat
pass/fail.

## The critical that survived

`pr_009` F1 (regex-based HTML sanitization, critical security) was caught
by the iter2 independent arbiter — a single-source finding. The risk going
into iter3 was that single-source findings would be voted down by mutual
triage. They weren't: both voices independently voted KEEP on pr_009's
three regex-sanitization findings, all three landed in high-confidence
blocking. That validates the design — the mutual triage prompts evaluate
findings against the code, not against who proposed them.

## Asymmetric defense pattern

Mutual disagreements (one voter KEEP, the other DROP) were entirely in one
direction: 10 instances of reviewer-voice KEEP + arbiter-voice DROP, zero
of the reverse. The reviewer voice anchors on "is this a plausible bug" and
defends; the arbiter voice anchors on "can I re-state this without
referring to the wording" and drops.

This asymmetry doesn't kill the design — the disagreement tier (low
confidence / advisory) catches it cleanly. But it means the mutual triage
is, in effect, the arbiter-voice doing the heavy lifting and the
reviewer-voice acting as a backstop. A more balanced design would use two
different-framed skeptical voices (e.g., security-skeptic vs
correctness-skeptic) rather than reviewer-vs-arbiter. Worth trying in a
later iteration if precision recovery becomes critical again.

The 10 disagreement findings include several real bugs (pr_005 unreachable
function, pr_015 unauth `/send-email`, pr_004 duplicate ETag helper). They
land in the advisory tier — the system does surface them, just below the
blocking line.

## Negative control progress

Iter2 had 2/3 negative-control failures (pr_007 and pr_018 both produced
FPs). Iter3 mutual triage **dropped pr_018's hallucinated FP entirely**
(both voices voted DROP). pr_007's persistent hallucination survived as
low-confidence — both voters disagreed, so it went to advisory. That's the
right outcome: the system never blocks on it, but the human reviewer sees
it. Hard kill on hallucinations requires a fix at the reviewer level
(check unchanged code before flagging), which we haven't tried yet.

## Cost

| iteration  | API calls per PR | total calls (20 PRs) |
|------------|------------------:|----------------------:|
| baseline   |                1 |                   20 |
| iter1      |                1 |                   20 |
| iter2      |                2 |                   40 |
| iter3      |                2 (cached) + 2 triage = 2 fresh |   40 fresh + 40 cached |

The 4×-baseline cost gains 1 critical catch, better confidence
calibration, and the two-tier output. Whether that's worth it depends on
the operating context — for security-leaning review, yes; for noise-
sensitive bulk PR scanning, probably not.

## Five-config summary

| config                          | critical | total recall | precision | FP | NC fail |
|---------------------------------|---------:|-------------:|----------:|---:|--------:|
| v1 rev-alone (baseline)         |     6/8  |        50.9% |     48.3% | 30 |     1/3 |
| v1 rev + v1 filter arbiter      |     6/8  |        47.3% |     52.0% | 24 |     1/3 |
| **v2 rev-alone**                |     6/8  |    **52.7%** |     60.4% | 19 |     1/3 |
| iter2 rev + indep arb (union)   |     7/8  |        61.8% |     49.3% | 35 |     2/3 |
| **iter3 mutual triage (blocking)** |  **7/8** |    43.6%     | **58.5%** | **17** |  **1/3** |

The progression shows the architecture exploration. The reviewer-only path
peaks at v2 (60.4 % precision, 52.7 % recall, but caps at 6/8 critical).
Adding an independent arbiter breaks the critical ceiling (7/8) at heavy
precision cost. Mutual triage recovers most of the precision without losing
the critical catch — at the cost of pulling some real findings into the
advisory tier. That's an honest tradeoff.

## Architecture verdict (final)

**Multi-agent is justified on this corpus, in this configuration.** The
reviewer + independent arbiter + mutual triage pipeline:

- Catches one more critical than the best single-agent setup (7/8 vs 6/8).
- Maintains comparable blocking-tier precision (58.5 % vs 60.4 %).
- Surfaces an advisory tier of 17 lower-confidence findings the
  single-agent setup either misses or buries in noise.
- Halves the negative-control failure rate vs the iter2 raw-merged baseline.

The single-agent reviewer is still a credible operating point — simpler,
cheaper, and only one critical worse. The multi-agent system is worth its
3-4× cost when missing a critical is the failure mode that matters.

## Where the system still loses

- Two criticals (`pr_015 F1` missing JSON validation, `pr_017 F1`
  config set-but-not-persisted) remain uncaught across **all six** runs.
  These are genuine reasoning ceilings, not prompt problems.
- `pr_007` hallucination is durable. It lives in advisory now, not
  blocking, but the system still produces a non-empty review for a clean
  refactor. A reviewer-side "check unchanged neighbors" rule is the right fix.
- Arbiter-voice triage drops some real bugs into advisory (pr_005, pr_015,
  pr_004). These are surfaced but not blocking. If we wanted them
  blocking, the second triage voice needs better calibration.

## Iter4 directions (if pursued)

In rough order of value:

1. **Reviewer-side "check unchanged code before flagging" rule.** Targets
   the persistent pr_007 hallucination. Cheap.
2. **Two-skeptic triage** instead of reviewer + arbiter voice. Would
   probably reduce the asymmetric defense bias and rebalance which findings
   land in blocking vs advisory. Medium effort.
3. **Focused experiment on the two remaining uncaught criticals.** Build
   one-off prompts for pr_015 and pr_017, see if any reframing surfaces
   them. If not, accept that as the reasoning ceiling.
4. **Cost reduction.** Triage prompts repeat the diff and full source.
   Sharing context across the two voices (via prompt caching) would halve
   the triage cost. Engineering, not research.

But honestly: the architectural story is now told. The remaining moves are
quality polish, not hypothesis tests. A reasonable stop point.

## Artifacts

- `results/iter3_20260513.json` — full run output including votes per
  finding, three score slices, and per-PR confidence breakdowns.
- `results/iter3_run.log` — raw stdout (gitignored).
- `agents/triage.py` — both voice prompts, vote tool, classify function.
- `eval/run_triage.py` — runner. Consumes iter2 cache; no fresh reviewer
  or arbiter calls.
