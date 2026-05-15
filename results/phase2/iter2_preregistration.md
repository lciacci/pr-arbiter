# Phase 2 iter2 — pre-registration

Date written: 2026-05-14
Author: claude (Sonnet 4.6 driver, Opus 4.7 orchestrator)

This document is committed BEFORE any iter2 runs are executed. It states
the three arms, the schema change for arm C, the pre-registered success
criterion, and the explicit no-goalpost-moving rule. Read this against
the final `PHASE_2_ITER2_SUMMARY.md` to verify the conclusion did not
drift from the intent.

## Context (one-paragraph)

Phase 2 iter1 produced 11/13 vs 11/13 between writer-alone and
writer + reviewer + arbiter. Multi-agent fixed `task_007` (medium
correctness, JSON path resolver) and broke `task_013` (underspec,
whitespace normalizer). On `task_013`, the arbiter asserted a confident
spec-interpretation guess as if it were a spec-violation; the writer
obeyed; the loop diverged. iter2 tests whether (a) a schema change that
forces critics to distinguish spec-violations from spec-interpretations
fixes the regression and (b) the iter1 single-seed signal is real vs
noise.

## Arms

Three arms, 13 tasks each, 3 seeds each → 9 corpus runs. Sonnet 4.6
across the board. Default temperature. Sequential per arm to keep
per-arm data clean (same discipline as iter1).

- **Arm A — writer-alone.** Unchanged from iter1. Re-run under variance
  to bound the noise floor on the baseline.
- **Arm B — writer + reviewer + arbiter, un-fixed.** Unchanged from
  iter1 multi-agent arm. Load-bearing control: tells us whether the
  task_013 regression was stable across seeds or single-seed noise.
- **Arm C — writer + reviewer + arbiter, finding-type tagged.** Same as
  arm B plus the schema change below.

## Schema change for arm C

Reviewer and arbiter findings each carry a required `finding_type`:

- `spec-violation` — the spec contains a clause this code violates.
  REQUIRES a `spec_quote` field containing verbatim spec text. If the
  critic cannot produce a quote, the finding is downgraded to
  `spec-interpretation` at validation time. The harness also checks the
  quote appears in the spec (whitespace-tolerant substring match) and
  downgrades on miss. This is the adversarial-robustness property:
  critics cannot label guesses as violations to bully the writer.
- `spec-interpretation` — the spec is silent or ambiguous; the critic is
  making a judgment call. No quote required. May include
  `proposed_interpretation`.

Severity and `finding_type` are orthogonal. A spec-interpretation can
be high-severity; a spec-violation can be low.

The writer system prompt is extended with explicit guidance:

> Findings tagged `spec-violation` cite specific spec clauses your code
> contradicts. Address these. Findings tagged `spec-interpretation` are
> the critic's judgment on points the spec is silent or ambiguous about.
> If your current code has already chosen an interpretation, do not
> change it solely because the critic chose a different one. Only adopt
> the critic's interpretation if you do not yet have one or yours has
> produced test failures.

(See `agents/writer.py::ARM_C_TYPED_FINDINGS_GUIDANCE` for the exact
text the writer sees.)

## Pre-registered success criterion for arm C

Arm C succeeds IFF **both** hold across the 3 arm-C seeds:

1. **Underspec preserved or recovered.** Median underspec pass rate
   across `task_012` and `task_013` is ≥ arm A's median across the
   same two tasks. Reported per seed and as median-of-medians. The
   fix must not regress underspec relative to writer-alone.

2. **Medium correctness gain preserved.** Median `task_007` outcome
   across the 3 arm-C seeds matches arm B's iter1 result — i.e.,
   `task_007` passes (converges to 17/17 within the 3-iteration budget)
   in at least 2 of 3 arm-C seeds. The fix must not break the win that
   motivated the multi-agent architecture in the first place.

**A result that improves underspec but loses `task_007` is not a
success.** It just shifts the swap. The criterion is conjunctive on
purpose.

## Variance bound on iter1 tie

Independent of arm C, arm A and arm B together bound the noise floor of
the iter1 11/13 vs 11/13 tie. Reported as:

- Per-task pass rate by arm across 3 seeds (3 = stable pass, 0 = stable
  fail, 1 or 2 = flippy).
- `task_013` arm-B regression rate: out of 3 arm-B seeds, how many
  regress vs writer-alone on `task_013`? If 2/3 or 3/3, the iter1
  finding was real signal and arm C is measuring against it. If 1/3 or
  0/3, the iter1 finding was noise and arm C's outcome is not
  interpretable as a "fix."

This is reported regardless of arm-C outcome.

## Sanity check on adversarial-robustness property

Reported for arm C:

- Count of reviewer + arbiter findings emitted with
  `finding_type=spec-violation` (post-validation, i.e., quote actually
  in spec).
- Count of findings the model attempted to emit as spec-violation but
  were downgraded (quote missing or quote not in spec).
- Per-finding breakdown for `task_012`, `task_013`, and `task_007` —
  the three tasks the analysis hinges on.

If the model emits spec-violation findings whose quotes are not in the
spec, the schema isn't doing its job and the arm-C result is
contaminated. Reported as a contamination rate per arm-C seed.

## What is NOT allowed to be changed after running

- The success criterion above. If arm C achieves criterion 1 but not 2,
  it is a failure, not a partial success. Same in reverse.
- The corpus. 13 tasks, same tests as iter1.
- The model (Sonnet 4.6) or default temperature across arms.
- The 3-iteration budget per task.

If the result is ambiguous (e.g., arm C achieves criterion 1 in 2/3
seeds and fails in 1/3), the summary reports it as ambiguous, not as
success.

## What iter2 will NOT change

- Mutual-triage analog (iter1 candidate #3) is NOT introduced in iter2.
  Held for iter3 if arm C fails.
- Writer still does not see tests or failure traces. Only the binary
  pass count.
- No clarifying-question architecture. `task_012` will remain a guess
  for the writer in all arms.

## Expected cost and wall

~9 corpus runs × ~$2-4 = $20-40 total. ~1 hour wall, sequential. Live
log per run in stdout; persisted artifacts in
`results/phase2/iter2/<arm>/seed<N>/<task>.json` and
`results/phase2/iter2/<arm>/seed<N>_summary.json`.

## Deliverables (post-run)

- `results/phase2/iter2/<arm>/seed<N>/<task>.json` — all per-run data
- `results/phase2/iter2/<arm>/seed<N>_summary.json` — per-arm-seed aggregates
- `PHASE_2_ITER2_SUMMARY.md` writeup with: variance bound on iter1 tie,
  arm C result against pre-registered criterion, sanity-check on
  spec_quote presence, and decision on whether to pursue mutual-triage
  analog (iter1 candidate #3) next.
