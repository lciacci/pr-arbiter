# pr-arbiter Phase 2 iter2 — implementation brief

## Context

Phase 2 iter1 produced an aggregate tie (11/13 vs 11/13) between writer-alone
and writer + reviewer + arbiter on a 13-task code-generation corpus. The tie
hid a swap: multi-agent gained `task_007` (medium correctness, JSON path
resolver) and lost `task_013` (underspec, whitespace normalizer). On
task_013, the arbiter asserted a confident spec-interpretation guess about
whitespace-adjacent-to-newlines behavior; writer obeyed; loop diverged.

See `PHASE_2_SUMMARY.md` for full iter1 writeup. This brief is iter2.

## Goal

Test whether the multi-agent regression on underspec tasks is (a) fixable
via a schema change that distinguishes spec-violations from
spec-interpretations, and (b) real signal vs single-seed noise.

## Three-arm variance run

Run all three arms on the existing 13-task corpus, 3 seeds each, 9 runs
total. Sonnet 4.6 across the board, same as iter1.

**Arm A — writer-alone (control).** Unchanged from iter1. Re-running under
variance to bound noise floor on the baseline.

**Arm B — writer + reviewer + arbiter, un-fixed (load-bearing control).**
Unchanged from iter1 multi-agent arm. This is the load-bearing control: it
tells us whether task_013's regression was stable across seeds or noise. If
arm B regresses on task_013 2/3 or 3/3 runs, the fix in arm C is measuring
against real signal. If arm B regresses 1/3 or 0/3, the iter1 finding was
noise and the fix is unfalsifiable.

**Arm C — writer + reviewer + arbiter, finding-type tagged.** Same as arm B
plus the schema change below.

## Schema change for arm C

Modify the reviewer and arbiter tool schemas to require a `finding_type`
field on every finding, with two values:

- `spec-violation` — the spec contains a clause that this code violates.
  Requires a `spec_quote` field containing the verbatim text from the spec
  that supports the finding. If the critic cannot produce a quote, the
  finding is `spec-interpretation` by definition. This is the adversarial
  robustness property — prevents the critic from labeling guesses as
  violations to get the writer to act on them.

- `spec-interpretation` — the spec is silent or ambiguous on this point and
  the critic is making a judgment call. No quote required. May include a
  `proposed_interpretation` field.

Update both `agents/writer_reviewer.py` and `agents/writer_arbiter.py`. Keep
the existing severity field — finding-type and severity are orthogonal
(a spec-interpretation can still be high-severity if the critic thinks
the guess matters; a spec-violation can be low-severity for cosmetic
issues).

## Writer prompt change for arm C

Update the writer prompt to treat the two finding types differently. Exact
wording matters here; vague "down-weight" instructions will be ignored by
the model. Use language closer to:

> Findings tagged `spec-violation` cite specific spec clauses your code
> contradicts. Address these.
>
> Findings tagged `spec-interpretation` are the critic's judgment on
> points the spec is silent or ambiguous about. If your current code has
> already chosen an interpretation, do not change it solely because the
> critic chose a different one. Only adopt the critic's interpretation if
> you do not yet have one or yours has produced test failures.

The goal is to prevent the task_013 iter3 failure mode where the writer
over-corrected because the critic asserted, not because the critic was
right.

## Pre-registered success criterion

Write this in `results/phase2/iter2_preregistration.md` before running:

Arm C succeeds if **both** of the following hold across the 3 seeds:

1. **Underspec preserved or recovered.** Median underspec pass rate
   (across tasks 012 and 013) is ≥ arm A's median. The fix must not
   regress underspec relative to writer-alone.

2. **Medium correctness gain preserved.** Median task_007 outcome
   matches arm B's iter1 result (passes within budget). The fix must
   not break the win that motivated the multi-agent architecture in
   the first place.

A result that improves underspec but loses task_007 is not a success —
it just shifts the swap.

## What to log per run

Per-task JSON for every (arm, seed, task) combination, mirroring iter1
structure under `results/phase2/iter2/<arm>/<seed>/`. Include:

- All reviewer + arbiter findings with finding_type and spec_quote where
  applicable (arm C only for the new fields)
- Writer reasoning per iteration
- Iteration count, final pass count, wall time
- For arm C: count of findings by type, count of spec-violation findings
  where the spec_quote was actually present in the spec (sanity check on
  the adversarial robustness property)

The last bullet is important. If arm C critics produce spec-violation
findings with quotes that aren't in the spec, the schema isn't doing what
it's supposed to and the result is contaminated.

## Order of operations

1. Implement schema change in reviewer + arbiter. Run on 1-2 tasks
   manually to verify the new fields appear and spec_quote is actually
   pulled from the spec.
2. Update writer prompt. Verify on task_013 iter1 trajectory specifically
   — does the new prompt change writer behavior on the existing
   reviewer/arbiter findings?
3. Write pre-registration doc. Commit before running the corpus.
4. Run arm A × 3 seeds, then arm B × 3 seeds, then arm C × 3 seeds.
   Sequential to keep per-arm data clean (same discipline as iter1).
5. Aggregate. Report against pre-registered criterion. Do not move the
   goalposts.

## What NOT to do in this iter

- Don't change the corpus. 13 tasks, same tests. Comparability with iter1
  matters.
- Don't add the mutual-triage analog (iter1 candidate #3). If arm C fixes
  task_013, triage is overkill. If arm C fails, triage becomes the next
  experiment with a real failure to design against.
- Don't show the writer test traces. The adversarial-reviewer thesis
  depends on the writer reasoning from spec, not from oracle leakage.
  This is locked.
- Don't change models or temperatures across arms.

## Estimated cost

~9 corpus runs × ~$2-4 per run = $20-40 total. ~1 hour wall.

## Deliverables

- `results/phase2/iter2_preregistration.md` (written before running)
- `results/phase2/iter2/<arm>/<seed>/<task>.json` (all per-run data)
- `results/phase2/iter2/<arm>_summary.json` (per-arm aggregates)
- `PHASE_2_ITER2_SUMMARY.md` writeup with: variance bound on iter1 tie,
  arm C result against pre-registered criterion, sanity-check on
  spec_quote presence, and decision on whether to pursue mutual-triage
  analog (iter1 candidate #3) next.
