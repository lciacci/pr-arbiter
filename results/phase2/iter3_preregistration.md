# Phase 2 iter3 — pre-registration

Date written: 2026-05-15
Author: claude (Sonnet 4.6 driver, Opus 4.7 orchestrator)
Branch: claude/phase2-iter3

Committed BEFORE any iter3 runs. Read against `PHASE_2_ITER3_SUMMARY.md`
to verify no goalpost movement.

## Context (one-paragraph)

Phase 2 iter2 ran arms A (writer-alone), B (multi-agent), and C (typed
schema + iter2 writer prompt that said "don't change your interpretation
just because the critic disagrees"). Arm C failed both pre-registered
criteria. Trajectory analysis showed arm C's writer locked in on early
interpretations (e.g., task_013 s1: 15→15→15) where arm A's writer
explored (16→17). The iter2 writer prompt suppressed the binary-signal
recovery loop. Two hypotheses fall out:

- **H1 — schema-neutrality.** The finding-type schema is at worst neutral
  and possibly net-positive. iter2's failure was caused by the writer
  prompt change, not the schema. Removing the prompt while keeping the
  schema should match arm B.
- **H2 — explicit attempt comparison.** Writer recovery from
  under-exploration improves when prior-attempt pass counts are
  rendered explicitly, ranked highest-first. Makes the binary-signal
  exploration loop legible to the writer rather than implicit.

## Design — 2×2 factorial, 3 seeds each

| | no prior-attempt prompt | + prior-attempt prompt |
|---|---|---|
| typed schema, NO iter2 writer prompt | **Arm D** (H1 control) | **Arm F** (H2 isolated) |
| typed schema + iter2 writer prompt | Arm C (reuse iter2) | **Arm E** (H1+H2 combined) |

Arm C numbers reused from iter2 — same task list, same model, same
seeds 1-3. Arms D, E, F are new. Total new runs: 9 × 3 seeds.

Sonnet 4.6 across the board. Default temperature. 3-iteration budget
per task. 13-task corpus unchanged.

## Prior-attempt prompt (H2 intervention, in arms E and F)

Inserted in the writer user-message before the writer iterates,
starting at iter2 (no prior attempts at iter1; block omitted then).

Block format:

```
# Your prior attempts on this task, ranked by pass count (highest first)

- Attempt N: P_N / TOTAL passing
- Attempt M: P_M / TOTAL passing
- ...

If your most recent attempt has a lower pass count than a prior attempt,
your last change made things worse. Consider reverting toward the
higher-scoring approach.
```

Ordering by pass count, not chronological — the ranking IS the signal.
Pass counts only — no code, no diffs, no reasoning. Including code
would reintroduce an oracle-leakage vector the binary-signal design
exists to prevent.

Implementation: `writer.py::write(..., include_pass_ranking: bool = False)`.

## Pre-registered success criteria

**H1 (schema-neutrality) succeeds iff BOTH hold:**

1. Arm D aggregate within ±1 task/seed of arm B aggregate, summed
   across 3 seeds. iter2 established the A vs B noise floor at
   ±~2 tasks total across 3 seeds, so ±1/seed = ±3 total is generous.
   Tightening to ±1/seed * 1 seed (= ±1 total) would over-claim
   precision the data doesn't support.
2. Arm D underspec median ≥ arm A underspec median (no regression
   vs writer-alone control). iter2 arm A underspec median = 0.5.

**H2 (attempt-comparison) succeeds iff BOTH hold:**

1. Arm F underspec median > arm A underspec median (STRICT inequality).
   If attempt-comparison only matches writer-alone, the prompt
   complexity is not worth carrying. iter2 arm A underspec median = 0.5.
2. Arm F task_007 converges in ≥ 2/3 seeds. Does not regress on the
   iter1 medium-correctness win.

**Interaction effect (descriptive only, not pass/fail):**

- If arm E ≈ arm F → iter2 writer prompt is no-op under attempt-comparison.
- If arm E < arm F → iter2 writer prompt is harmful even with attempt-comparison.
- If arm E > arm F → iter2 writer prompt is rescued by attempt-comparison
  (unlikely but possible; would imply prompt-induced inertia is broken
   by giving the writer explicit pass-rank context).

## Logging requirements

`results/phase2/iter3/<arm>/seed<N>/<task>.json` mirrors iter2 schema.
Additional fields for arms E and F:

- `pass_ranking_shown` per attempt: the rendered ranking block string
  (or null when no ranking was rendered, i.e., iter1 of any task).
- Writer reasoning already captured in `att.reasoning`; useful for
  trajectory analysis on whether the writer cited the ranking.

## Pre-registered analysis plan

1. **H1 numerical test.** Arm D per-seed converged-count compared to
   arm B per-seed converged-count. Report aggregate delta and per-task
   convergence stability.
2. **H2 numerical test.** Arm F per-seed underspec converged-count
   compared to arm A per-seed underspec converged-count. Report median
   per arm.
3. **Trajectory narrative on task_013.** Side-by-side comparison of
   seed 1 of each arm (A, B, C, D, E, F): iteration-by-iteration pass
   counts + writer reasoning. This is the load-bearing qualitative
   artifact.
4. **Adversarial-robustness sanity check (arms D, E, F).** Per arm:
   total findings, validated spec-violations, downgrades, contamination.
   Confirm the schema validator continues to perform as designed.

## What is NOT allowed to change after running

- Success criteria above. Conjunctive. No moving from "strict
  inequality" to "≥".
- Corpus: 13 tasks, same tests as iter1/iter2.
- Model: Sonnet 4.6.
- Default temperature.
- 3-iteration budget per task.
- Prompt wording. If H2 fails, that's data — not a reason to tune.

## What iter3 will NOT introduce

- Mutual-triage analog (iter1 candidate #3). iter2 ruled it out.
- Clarifying-question architecture. Deferred to Phase 3.
- Corpus expansion. Phase 2 is closing out, not opening.
- Failure-trace exposure to writer. Blind-writer locked.

## Expected cost and wall

~9 new corpus runs × ~10 min each ≈ 90 min wall sequential.
~$30 at Sonnet 4.6 rates.

## Deliverables (post-run)

- `results/phase2/iter3/<arm>/seed<N>/<task>.json` — all per-run data (arms D, E, F)
- `results/phase2/iter3/<arm>/seed<N>_summary.json` — per-arm-seed aggregates
- `results/phase2/iter3/aggregate.json` — machine-readable iter3 summary, includes arm C reused from iter2
- `PHASE_2_ITER3_SUMMARY.md` — writeup with H1, H2, interaction effect, task_013 trajectory narrative
