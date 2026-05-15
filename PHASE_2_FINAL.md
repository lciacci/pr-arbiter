# pr-arbiter Phase 2 — final writeup

Phase 2 tested whether the multi-agent independent-review pattern from
Phase 1 (reviewer + arbiter, anti-anchoring) generalizes from PR review
to code generation in a **writer-loop** architecture. Three iterations
across two months. This document is the canonical Phase 2 artifact;
iter-level writeups remain in place for reproducibility but the
load-bearing claims live here.

## TL;DR

- **The Phase 1 multi-agent effect did not replicate cleanly under
  Phase 2 variance.** Under 3-seed variance on a 13-task corpus, the
  multi-agent reviewer + arbiter beats writer-alone by **2 tasks across
  39 runs** (34/39 vs 32/39). Direction matches Phase 1; magnitude is
  ~2× smaller than the iter1 single-seed report.
- **The iter1 architectural narrative ("multi-agent fixes task_007 but
  regresses task_013") was overfit to one seed.** Under variance both
  task_007 and task_013 are flippy with no stable winner across arms.
- **The finding-type schema with validator-checked spec_quote is a
  clean reusable artifact.** 0 contamination across 551 findings in
  iter3; ~80% of attempted spec-violations are downgraded by the
  validator. Independent of the broader architectural claim, this
  prompt+validator pattern is reusable for any multi-agent critique
  system.
- **Underspec convergence is information-bounded, not
  architecture-bounded.** Across 6 distinct prompt configurations no
  arm reaches > 0.5 underspec median. The ceiling is "writer must
  guess on truly ambiguous specs with no oracle to ask." Motivates
  Phase 3.
- **Three architectures tied at 34/39 with different failure mixes.**
  Multi-agent (B), typed schema only (D), and typed + iter2 prompt +
  ranking (E) all hit the same effective ceiling. The architectural
  choice is bounded by the corpus and the model.

## Headline result — variance-bound replication

Phase 2 was designed to test whether multi-agent independent review
generalizes from PR review to code generation. The iter1 result
(11/13 vs 11/13 aggregate tie, with a "swap" in failure modes) was
publishable as written. The iter2 + iter3 variance work showed it was
not.

| arm | s1 | s2 | s3 | total |
|-----|----|----|----|-------|
| A writer-alone           | 11 | 11 | 10 | **32/39** |
| B writer + reviewer + arbiter | 11 | 12 | 11 | **34/39** |
| C +typed schema + iter2 prompt | 11 | 10 | 10 | 31/39 |
| D typed schema only      | 11 | 11 | 12 | **34/39** |
| E +typed + iter2 prompt + ranking | 12 | 11 | 11 | **34/39** |
| F +typed + ranking only  | 10 | 11 | 11 | 32/39 |

Multi-agent advantage (B vs A): +2 tasks across 39 runs, +6%. The
iter1 report claimed an 11/13 vs 11/13 aggregate tie with multi-agent
gaining task_007 and losing task_013 — both effects were 1-of-3-seed
signals on flippy tasks under variance.

**The architectural claim from Phase 1 ("independent multi-agent review
beats single-agent on correctness bugs the latter can't catch alone")
remains directionally supported on code generation but with a
substantially weaker effect size than the Phase 1 PR-review corpus
suggested.**

This is the load-bearing finding. Phase 2's contribution is bounding
the Phase 1 + Phase 2 effect size under proper variance, not confirming
the architecture works.

## Secondary findings

### 1. Schema validation as a methodological artifact

The iter2 typed-finding schema requires every reviewer/arbiter finding
to be tagged `spec-violation` (needs verbatim `spec_quote`) or
`spec-interpretation` (no quote required). A downstream validator
substring-matches each quote against the spec and downgrades any
spec-violation that can't be supported by a real quote.

| metric | iter2 arm C | iter3 arm D | iter3 arm E | iter3 arm F |
|---|---|---|---|---|
| Total findings | 131 | 120 | 116 | 184 |
| Validated spec-violations | 6 | 19 | 19 | 33 |
| Downgrades (SV-attempt → interp) | 45 | 32 | 36 | 48 |
| Contamination (validated SV w/ bad quote) | **0** | **0** | **0** | **0** |

Validator integrity is clean across all 4 typed-schema arms (~80%
downgrade rate, 0 contamination across 551 findings). The mechanism
works as designed: critics cannot label guesses as violations because
the validator catches the lack of a verifiable quote. Adversarial
robustness property holds.

**This pattern is reusable independent of the broader Phase 2 result.**
Any multi-agent critique system where the critic might assert beyond
what the spec supports can adopt this schema. See
[agents/writer_reviewer_typed.py](agents/writer_reviewer_typed.py) and
[agents/writer_arbiter_typed.py](agents/writer_arbiter_typed.py) for
the reference implementation.

### 2. Writer behavior under binary signal dominates critic behavior on underspec

iter1's failure on task_013 was attributed to arbiter overshoot. iter2
variance showed both writer-alone and multi-agent converge task_013 in
1/3 seeds. iter3's H2 experiment isolated the writer side: arm F
(typed schema + explicit pass-ranking, no critic prompt change)
achieved **3/3 stable_pass on task_013**, the strongest single-task
effect across all 6 arms.

But arm F's underspec median ties arm A's (0.5 each) — the gain on
task_013 was cancelled by a 0/3 regression on task_012. **The writer's
exploration strategy dominates the underspec outcome, but the
intervention that helps on one underspec failure mode hurts on
another.**

This is the most important methodological finding of Phase 2: critic
architecture changes (the focus of Phase 1 and most of iter1) move the
underspec needle by 0-1 tasks/seed. Writer prompt changes move it by
0-3 tasks/seed on individual tasks but with offsetting regressions on
others. The architecture matters less than the writer's reasoning
about its own trajectory.

### 3. Negative result on the iter2 writer prompt

The iter2 writer prompt ("don't change your interpretation just
because the critic disagrees") failed both pre-registered criteria in
iter2 and on its own. iter3 confirmed via arm D (typed schema only, no
iter2 prompt) that the schema alone matches arm B's aggregate. The
iter2 prompt was the cause of arm C's regression, not the schema.

When combined with explicit pass-count ranking (arm E), the iter2
prompt produces a different effect: it acts as a brake on the ranking's
"revert to best score" instinct, which prevents the task_012 regression
arm F suffered. Net: E ≈ D > F on aggregate. The iter2 prompt is not a
free improvement but it has a small role in tempering the ranking when
both are present.

## Trajectory analysis on task_013 (seed 1, all 6 arms)

The qualitative anchor of Phase 2. Same task, same seed, six prompt
configurations. Reproduced from iter3 summary because it's the most
informative single artifact Phase 2 produced.

| arm | trajectory | outcome | mechanism |
|-----|------------|---------|-----------|
| A | 16 → 17        | conv 2-iter   | implicit "I got 16/17, try CRLF" — works some seeds |
| B | 15 → 15 → 16   | stuck         | critic surfaced ambiguity; writer half-adopted |
| C | 15 → 15 → 15   | locked in     | iter2 prompt: writer submitted identical code in iter3 |
| D | 16 → 15 → 15   | regressed     | writer saw regression but didn't revert without ranking |
| E | 16 → 15 → 13   | regressed     | saw ranking, was blocked from acting by iter2 prompt |
| F | 15 → 17        | conv 2-iter   | ranking + critic suggestion → clean adoption |

The pattern across arms:

- Implicit comparison (arm A) is unreliable across seeds. 1/3 conv.
- Iter2 prompt alone (arm C) actively prevents exploration.
- Schema alone (arm D) gives the writer better critic input but doesn't
  fix the comparison fragility.
- Schema + iter2 prompt + ranking (arm E) has the writer explicitly
  noting the regression but the iter2 prompt suppresses the response.
- Schema + ranking, no iter2 prompt (arm F) lets the writer act on the
  comparison. 3/3 conv across seeds.

The arm F trajectory is what iter1 attributed to arm A's writer-loop —
but as a stable property, not a lucky seed.

## Methodology — what worked across Phase 2

These are the load-bearing practices, in order of importance:

1. **Pre-registration with strict success criteria.** iter2 and iter3
   each had pre-reg docs committed before runs. Strict-inequality
   clauses (H2 crit 1) and conjunctive criteria prevented post-hoc
   goalpost movement. iter2 arm C was clean negative; iter3 H2 was a
   clean negative despite a striking single-task effect that would
   have tempted a narrative re-frame.
2. **3-seed variance discipline.** iter2 introduced this and it
   immediately invalidated multiple iter1 single-seed claims. The
   variance work itself was the most important methodological
   contribution of iter2.
3. **Adversarial validator on the typed schema.** Forcing critics to
   produce verifiable spec_quotes turned model assertion into a
   testable property. 0 contamination across 551 findings.
4. **Blind writer (no tests, no failure traces).** The pass count is
   the only signal. Without this, the writer would fit tests and the
   underspec questions would be trivially closed via test leakage.
5. **Trajectory analysis as the qualitative anchor.** Per-seed,
   per-iteration pass counts + writer reasoning surfaced the H2
   hypothesis from iter2 data and validated the H2 mechanism on a
   single seed before the iter3 full run. The aggregate alone would
   have missed the writer-behavior signal.
6. **Per-arm separate modules instead of branching one module.** v1
   reviewer/arbiter remained unchanged across arms B (control) so the
   typed-schema arms (C/D/E/F) could not contaminate the control.

## Limitations

- **n = 13 corpus.** Small enough that 1-task differences swing arm
  rankings. iter3 added 9 runs × 3 seeds for 117 new datapoints but the
  *task* axis is what bounds inference, not the seed axis.
- **2 of 13 tasks underspec.** Underspec is the most interesting axis
  for Phase 3 but Phase 2's corpus underweights it. Phase 3 needs a
  majority-underspec corpus to discriminate clarifying-question
  designs.
- **Sonnet 4.6 only.** All claims are model-conditional.
- **3-iteration budget.** Some arm F task_013 trajectories converged
  in iter2/iter3; a longer budget might let writer-alone (arm A)
  match arm F's recovery rate. Untested.
- **HumanEval-shaped tasks may pattern-match training data.** task_007
  is HumanEval-shaped; arm D's 2/3 conv on it could partly reflect
  task familiarity rather than architectural improvement.

## What was rejected across Phase 2

- **Mutual-triage analog (iter1 candidate #3).** iter2 evidence ruled
  out as the bottleneck (critic side is well-calibrated under the typed
  schema). Not pursued.
- **Iter2 writer prompt ("don't change interpretation just because
  critic disagrees").** Failed pre-reg in iter2; iter3 arm D confirmed
  the schema alone is fine without it. Removed from canonical writer
  prompt.
- **Explicit pass-count ranking (iter3 H2) as a free improvement.**
  Strong on task_013, regresses on task_007 and task_012. Not adopted
  as a default; logged as an option for future trades.

## What was preserved

- **Typed-finding schema** with `spec-violation` / `spec-interpretation`
  tagging and validator-checked `spec_quote`. Default in writer_reviewer_typed
  and writer_arbiter_typed.
- **Phase 2 corpus and harness.** 13 tasks, 197 deterministic tests,
  blind writer, 3-iter budget. Phase 3 will build alongside, not
  replace.
- **Per-task JSON dump format** with pass_ranking_shown and
  reviewer/arbiter feedback. Trajectory analysis is the highest-value
  qualitative artifact.
- **Pre-registration + 3-seed variance discipline.** Carries forward
  to Phase 3.

## Motivation for Phase 3

Phase 2 established that on this corpus, with this model, with these
prompt variations:

- The critic side is well-calibrated under the typed schema (0
  contamination, 80% downgrade rate on SV attempts).
- The writer's exploration strategy is the dominant variable on
  underspec.
- No prompt configuration tested reaches > 0.5 underspec median.

The remaining intervention that adds *information* (not just routes
existing information differently) is a clarifying-question architecture
where the writer can ask a bounded oracle about spec ambiguities. Phase
3 asks: can the agent recognize when it should ask vs guess, and does
even one yes/no question close the underspec gap?

Full Phase 3 design: [docs/PHASE_3_DESIGN.md](docs/PHASE_3_DESIGN.md).

## Cost summary

| iter | wall | API |
|------|------|-----|
| iter1 (Phase 2 baseline) | ~17 min | ~$5 |
| iter2 (3-arm × 3-seed variance) | ~71 min | ~$25 |
| iter3 (3-arm × 3-seed, arm C reused) | ~92 min | ~$30 |
| **Total Phase 2** | **~3 hours** | **~$60** |

## Files / reproducibility

Canonical artifacts:

- [PHASE_2_FINAL.md](PHASE_2_FINAL.md) — this document
- [docs/PHASE_3_DESIGN.md](docs/PHASE_3_DESIGN.md) — next-phase design

Per-iteration writeups (preserved for reproducibility):

- [PHASE_2_SUMMARY.md](PHASE_2_SUMMARY.md) — iter1 narrative (note:
  iter2 invalidated some single-seed claims; read alongside iter2)
- [PHASE_2_ITER2_SUMMARY.md](PHASE_2_ITER2_SUMMARY.md) — iter2 variance
  + typed schema introduction
- [PHASE_2_ITER3_SUMMARY.md](PHASE_2_ITER3_SUMMARY.md) — iter3 2×2 +
  trajectory narrative

Pre-registration commitments (committed before each iter ran):

- [results/phase2/iter2_preregistration.md](results/phase2/iter2_preregistration.md)
- [results/phase2/iter3_preregistration.md](results/phase2/iter3_preregistration.md)

Code:

- [agents/writer.py](agents/writer.py) — writer agent + Attempt
  dataclass + `render_pass_ranking()`
- [agents/writer_reviewer.py](agents/writer_reviewer.py),
  [agents/writer_arbiter.py](agents/writer_arbiter.py) — Phase 1
  schema critics (arms A, B)
- [agents/writer_reviewer_typed.py](agents/writer_reviewer_typed.py),
  [agents/writer_arbiter_typed.py](agents/writer_arbiter_typed.py) —
  typed schema with spec_quote validator (arms C, D, E, F)
- [eval/writer_loop.py](eval/writer_loop.py) — single-task driver
- [eval/phase2_harness.py](eval/phase2_harness.py) — corpus runner +
  arm selector
- [eval/aggregate_iter2.py](eval/aggregate_iter2.py),
  [eval/aggregate_iter3.py](eval/aggregate_iter3.py) — aggregators

Data:

- `results/phase2/iter2/` — A, B, C × 3 seeds per-task JSONs
- `results/phase2/iter3/` — D, E, F × 3 seeds per-task JSONs + iter3
  aggregate.json
- `phase2_corpus/` — 13 tasks, manifest, README
