# pr-arbiter Phase 2 iter2 — variance + finding-type schema

iter2 ran three arms × three seeds on the same 13-task corpus as iter1:

- **Arm A** — writer-alone (control, unchanged from iter1)
- **Arm B** — writer + reviewer + arbiter, unchanged from iter1 multi-agent
- **Arm C** — arm B + finding-type schema (`spec-violation` vs
  `spec-interpretation`) + writer prompt change

All Sonnet 4.6, default temperature, 3-iteration budget per task. Same
discipline as iter1 (sequential per arm). Pre-registration committed before
running ([results/phase2/iter2_preregistration.md](results/phase2/iter2_preregistration.md));
this writeup reports against that criterion verbatim.

## TL;DR

- **Arm C failed both pre-registered criteria.** Underspec regressed
  (median 0 vs arm A's 0.5). `task_007` converged in only 1/3 arm-C seeds.
- **The schema fix worked as designed.** Adversarial robustness
  property held: 45 attempted spec-violations downgraded by the
  validator, 0 contamination, 0 validated spec-violations on
  `task_013` across all 3 seeds (correct — spec is silent).
- **The writer prompt change broke the writer's recovery loop.** Telling
  the writer "don't change your interpretation just because the critic
  disagrees" suppressed the exploration that arm A relied on for
  underspec recovery. Writer locked in (e.g., `task_013` s1
  15→15→15) or oscillated worse (s2: 13→16→12).
- **iter1 single-seed signal was largely noise.** task_013 arm A 1/3
  conv (iter1's 17/17 was lucky); task_013 arm B 1/3 conv (iter1's
  regression not stable); task_007 arm B 1/3 conv (iter1 "win" not
  stable). The iter1 architectural narrative was overfit to one seed.
- **Mutual-triage analog (iter1 candidate #3) is no longer the obvious
  next experiment.** The bottleneck is writer behavior under ambiguity,
  not critic-induced overshoot.

## Per-seed aggregate (converged / 13)

| arm | seed 1 | seed 2 | seed 3 | total |
|-----|--------|--------|--------|-------|
| A writer-alone           | 11/13 | 11/13 | 10/13 | **32/39 (82%)** |
| B writer+rev+arb         | 11/13 | 12/13 | 11/13 | **34/39 (87%)** |
| C writer+rev+arb+typed   | 11/13 | 10/13 | 10/13 | **31/39 (79%)** |

Iter1's 11/13 vs 11/13 sits inside the per-seed range for all three arms.
Multi-agent (arm B) is marginally ahead of writer-alone under variance,
but the margin is 2 tasks across 39 runs — not load-bearing.

## Per-task stability across seeds

The interesting tasks are the three the architecture is supposed to
discriminate on. The 10 other tasks are stable_pass for all arms.

| task | difficulty | arm A | arm B | arm C |
|------|------------|-------|-------|-------|
| task_007 (JSON path)    | medium    | 0/3 stable-fail | 1/3 flippy | 1/3 flippy |
| task_012 (date parse)   | underspec | 1/3 flippy      | 2/3 flippy | 0/3 stable-fail |
| task_013 (whitespace)   | underspec | 1/3 flippy      | 1/3 flippy | 0/3 stable-fail |

**The iter1 multi-agent task_007 win is real but small.** Arm B beats
arm A on task_007 by 1 task out of 3 seeds. The iter1 narrative
(multi-agent unstuck the writer) is consistent with the 1/3 vs 0/3
split, but the effect size is one seed.

**The iter1 multi-agent task_013 loss does not survive variance.**
Both arm A and arm B converge task_013 in 1/3 seeds. The iter1
single-seed split (writer-alone 17/17 vs multi-agent 13/17) was the
two tails of the same flippy task.

**Arm C is strictly worse on the underspec tasks.** Both task_012 and
task_013 went stable_fail. The schema fix did not help; the writer
prompt change actively hurt.

## Pre-registered criterion: result

Criterion 1 — **underspec preserved or recovered**: FAILED.
- Arm A underspec pass-per-seed: `[0.5, 0.5, 0.0]`, median 0.5
- Arm C underspec pass-per-seed: `[0.0, 0.0, 0.0]`, median 0.0
- Arm C median is strictly below arm A's. Underspec regressed.

Criterion 2 — **task_007 converges in ≥ 2/3 arm-C seeds**: FAILED.
- Arm C task_007 per-seed: `[True, False, False]` — 1/3.

**Both criteria failed. Arm C does not succeed under the
pre-registration.** No goalposts were moved.

## Why arm C lost underspec — trajectory analysis

The schema fix on critics worked. Look at task_013 reviewer/arbiter
output across all 3 arm-C seeds × 3 iterations: **0 validated
spec-violations**, 35 spec-interpretation findings. The adversarial
robustness property fired exactly as designed — critics couldn't
quote the spec verbatim because the spec is silent, so they were
forced to label their feedback as judgment calls.

The writer prompt extension told the writer:

> If your current code has already chosen an interpretation, do not
> change it solely because the critic chose a different one. Only adopt
> the critic's interpretation if you do not yet have one or yours has
> produced test failures.

The writer obeyed. The failure modes per seed on task_013:

- **C seed 1**: 15 → 15 → 15. Writer locked in on iter1 (15/17) and
  didn't change interpretation across 3 iterations despite passes
  being below 17/17. The critic's spec-interpretation findings (all
  honest about being judgment calls) gave the writer no reason to
  adopt them. Self-exploration suppressed.
- **C seed 2**: 13 → 16 → 12. Writer changed interpretation once
  (improved to 16/17), then on iter3 reverted past the improvement
  back to a worse interpretation. Same oscillation arm A's iter1
  writer-alone showed, but worse landing.
- **C seed 3**: 16 → 13 → 16. Writer changed, regressed, restored.
  Ended at 16/17, never converged.

Compare arm A task_013 seed 1: **16 → 17, converged in 2 iters.**
Writer had no critic input, saw 16/17 (one failing), tried a different
interpretation, hit 17/17. Pure self-exploration under binary signal
was the recovery path the iter1 narrative attributed to multi-agent
absence.

The arm C writer prompt over-constrained that exploration. It told the
writer "stick with your interpretation if you've already picked one,"
but the writer has no signal for *which* interpretation is right — only
the binary pass count. Telling it to stay put when the count is below
17 is the wrong instruction for underspec.

This is symmetric to the iter1 finding restated:

| iter1 reading | iter2 finding |
|---|---|
| Critic-induced overshoot pushes writer wrong way on underspec | Schema fixes that. **AND** writer prompt-induced under-exploration ALSO pushes writer wrong way. |
| Independent critic = false certainty | Independent critic, properly tagged = correct labels. But: telling the writer to weight interpretation findings low = removing the writer's reason to explore at all. |

## Adversarial robustness sanity check (arm C)

| metric | count |
|---|---|
| Total findings (rev + arb, 3 seeds × 13 tasks × up to 3 iters) | 131 |
| Validated spec-violations (post-validation) | 6 |
| Attempted spec-violations downgraded by validator | 45 |
| Quotes verified present in spec | 6 |
| Quotes NOT in spec (downgrade trigger) | 30 |
| Contamination (validated SV with bad quote) | 0 |

Schema integrity is clean: 0 spec-violation findings survived
validation with a quote not in spec. The validator is doing its job.

**Per-task** (summed across 3 arm-C seeds):

| task | violations | interpretations | downgraded |
|---|---|---|---|
| task_007 (medium win)         | 5  | 28 | 22 |
| task_009 (hard, stable_pass)  | 0  | 9  | 6  |
| task_012 (underspec)          | 1  | 53 | 12 |
| task_013 (underspec)          | 0  | 35 | 5  |

- task_007 produced 5 validated spec-violations across 3 seeds.
  Pilot showed the arbiter quoting the spec's KeyError/IndexError
  clause and the empty-path clause verbatim. The schema is
  surfacing real correctness violations correctly.
- task_013 produced 0 validated spec-violations across 3 seeds, 3
  iterations each. This is the desired behavior: the spec is silent
  on whitespace-adjacent-to-newlines and the critics couldn't quote
  it because there's nothing to quote. Adversarial robustness
  property held.
- 88% of attempted spec-violations were downgraded (45 / 51 attempts).
  Models prefer to assert; the validator forces calibration.

The schema fix passed its own sanity check. The architectural part
that broke arm C was the writer prompt — not the critic side.

## Variance bound on iter1 tie

Independent of arm C: arm A and arm B together bound how much of the
iter1 11/13 vs 11/13 was real.

**task_013 (iter1's multi-agent loss):**

| arm | converged per seed | test passes per seed | regression rate vs arm A iter1 |
|-----|---|---|---|
| A | True, False, False | 17, 13, 12 | — |
| B | False, False, True | 16, 16, 17 | 2/3 |

Arm B's task_013 regression rate is 67% (2/3 seeds). Two seeds match
iter1's failure (multi-agent stuck < 17/17). One seed (B s3) actually
converges. Under variance, **the iter1 task_013 regression is partial
signal, not stable.** Calling it a "real shift in failure mix" in the
iter1 writeup was overconfident.

**task_007 (iter1's multi-agent win):**

| arm | converged per seed |
|-----|---|
| A | False, False, False |
| B | False, True, False |

Arm A is stable_fail (matches iter1). Arm B is 1/3 — same direction
as iter1 (multi-agent wins) but not stably. The iter1 claim "multi-agent
fixed task_007" is supported in 1/3 seeds. Effect size: 1 task.

**The iter1 architectural narrative was overfit to one seed.** Two
phases of the same model, two corpora, same "multi-agent independent
review beats single-agent on correctness, loses on ambiguity" — that
remains directionally true but the magnitude in any single run is
~1 task out of 13. Most of the iter1 difference between arms was
noise.

## What this means for the architecture

1. **Schema fix on critics: validated.** The adversarial-robustness
   property held. Critics can't lie about quotes. The validator is
   clean. This is a real artifact and should stay.
2. **Writer prompt change: harmful.** The "stick with your
   interpretation" guidance suppresses the writer's binary-signal
   exploration loop that does most of the underspec recovery work.
   Should be removed or reversed for any further iter.
3. **Multi-agent advantage is real but small under variance.** Arm B
   beats arm A by ~1 task on the corpus per seed. Probably enough to
   keep, but not large enough to claim "multi-agent unlocks
   correctness" with a single 11/13 vs 11/13 tie.
4. **Underspec is dominated by writer behavior, not critic behavior.**
   Both arm A and arm B converge task_013 in 1/3 seeds. The critic
   architecture matters less than how the writer explores under
   binary signal.

## What was NOT changed in iter2 (held from iter1)

- Corpus: 13 tasks, 197 tests, unchanged.
- Writer hidden from tests and failure traces. Binary pass count only.
- Sonnet 4.6 across all arms.
- Reviewer history vs arbiter latest-only split.
- 3-iteration budget.

## Cost

- Wall: 990s (A) + 1363s (B) + 1920s (C) = ~71 min total, sequential.
- API calls: rough estimate ~600 across 9 runs (writer + reviewer +
  arbiter on non-converged tasks; convergent tasks short-circuit).
- $ spend: in the $25-35 range at Sonnet 4.6 rates.

## Files / reproducibility

- `results/phase2/iter2_preregistration.md` — committed before runs
- `results/phase2/iter2/<arm>/seed<N>/<task>.json` — per-task per-seed
- `results/phase2/iter2/<arm>/seed<N>_summary.json` — per-arm-seed aggregate
- `results/phase2/iter2/aggregate.json` — machine-readable iter2 summary
- `results/phase2/iter2/logs/{armA,armB,armC}.log` — live console output
- `agents/writer_reviewer_typed.py`, `agents/writer_arbiter_typed.py` — typed schema
- `agents/writer.py` (modified) — `extra_system` kwarg + `ARM_C_TYPED_FINDINGS_GUIDANCE`
- `eval/aggregate_iter2.py` — produces `aggregate.json` and stdout summary

To re-run:

```bash
.venv/bin/python eval/phase2_harness.py A --seed 1 3   # arm A, seed 1
.venv/bin/python eval/phase2_harness.py B --seed 1 3
.venv/bin/python eval/phase2_harness.py C --seed 1 3
# (loop seeds 1..3 per arm; bash _run_iter2.sh A|B|C)
.venv/bin/python eval/aggregate_iter2.py
```

## Decision on next experiment

**Not mutual-triage analog (iter1 candidate #3).** The iter1 reason to
do mutual-triage was "fix critic-induced overshoot." iter2 showed
critic-induced overshoot is fixable on the critic side (the typed
schema works) but the writer's response to ambiguous feedback is the
larger problem. Mutual triage adds a layer to the critic pipeline that
iter2 evidence says is not the bottleneck.

Three more-promising directions, in order:

1. **Reverse the arm C writer prompt change and re-run.** Keep the
   typed schema (it's clean); drop the "stick with your interpretation"
   guidance; let the writer use its own pass-count-driven exploration
   the way arm A does. Predicted outcome: arm C matches arm B on
   correctness, doesn't regress underspec. Cheapest test of whether
   the schema alone is neutral or net-positive.

2. **Show the writer which iteration's pass count was best.** The arm
   A self-recovery loop on task_013 worked because the writer compared
   attempt 2's 12/17 to attempt 1's 16/17 and reverted. Make this
   comparison explicit in the prompt (literally: "your prior attempts
   ranked by pass count are: …"). May make the writer's binary
   exploration more reliable across seeds.

3. **Clarifying-question mode (deferred from iter1 candidate #4).**
   Both arms cap at 1/3 conv on task_013 and 1-2/3 on task_012. The
   ceiling is "writer must guess on truly ambiguous specs and has no
   way to ask." A bounded oracle ("you can ask one yes/no question
   per task") would close the underspec gap entirely — but it's a new
   architectural piece, not a tuning change. Defer until 1-2 are
   exhausted.

The pre-registered iter2 result is unambiguously a failure for arm C.
The schema fix is preserved; the writer prompt extension is rejected;
the next experiment is reversing the writer prompt to isolate the
schema's effect.
