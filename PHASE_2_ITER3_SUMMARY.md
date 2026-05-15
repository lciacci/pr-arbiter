# pr-arbiter Phase 2 iter3 — schema-neutrality + attempt-comparison

iter3 ran a 2×2 factorial on top of the typed-finding schema. Two new
prompts: the iter2 writer prompt (rejected in iter2) and an explicit
pass-count ranking block (new in iter3). Arms D, E, F are new; arm C is
reused from iter2.

| | no ranking | + ranking |
|---|---|---|
| no iter2 writer prompt | **D** | **F** |
| iter2 writer prompt | C (reuse) | **E** |

Pre-registration committed before runs ([results/phase2/iter3_preregistration.md](results/phase2/iter3_preregistration.md));
this writeup reports against that criterion verbatim.

## TL;DR

- **H1 (schema-neutrality): PASSES.** Arm D matches arm B aggregate
  exactly (34/39 each) and arm A on underspec median (0.5 each). The
  iter2 schema change is at worst neutral, possibly net-positive.
- **H2 (attempt-comparison): FAILS the strict pre-registration.** Arm F
  ties arm A on underspec median (0.5 each, not strict >) and regresses
  on task_007 (0/3 conv). But task_013 went **3/3 stable_pass** under
  arm F — the strongest single-task effect across all 6 arms.
- **Interaction: arm E ≈ arm D > arm F.** Combining ranking with the
  iter2 writer prompt (E) does better than ranking alone (F). Ranking
  alone over-encourages reversion on tasks where the writer is stuck
  near a local optimum (task_012 0/3 in F). The iter2 prompt anchors
  the writer to its own interpretation, which counterbalances.
- **Three architectures hit the same ceiling (34/39): B, D, E.** Under
  variance, the multi-agent advantage is ~2 tasks across 39 runs and
  stable across reasonable prompt variations. The architectural choice
  is bounded.

## Per-seed aggregate (converged / 13)

| arm | s1 | s2 | s3 | total | underspec median |
|-----|----|----|----|-------|------------------|
| A writer-alone                 | 11 | 11 | 10 | 32/39 | 0.500 |
| B writer+rev+arb               | 11 | 12 | 11 | 34/39 | 0.500 |
| C +typed+iter2-prompt          | 11 | 10 | 10 | 31/39 | 0.000 |
| **D typed only**               | 11 | 11 | 12 | **34/39** | **0.500** |
| **E typed+iter2-prompt+ranking** | 12 | 11 | 11 | **34/39** | **0.500** |
| **F typed+ranking only**       | 10 | 11 | 11 | 32/39 | 0.500 |

## Per-task convergence (across 3 seeds)

The 10 stable_pass tasks are omitted (all 6 arms 3/3 on them).

| task | difficulty | A | B | C | D | E | F |
|------|------------|---|---|---|---|---|---|
| task_007 (JSON path)    | medium    | 0/3 | 1/3 | 1/3 | **2/3** | 1/3 | 0/3 |
| task_012 (date parse)   | underspec | 1/3 | 2/3 | 0/3 | **2/3** | **2/3** | 0/3 |
| task_013 (whitespace)   | underspec | 1/3 | 1/3 | 0/3 | 0/3 | 1/3 | **3/3** |

Three different best-arms across three failure modes:

- task_007 best: arm D (2/3). Schema-alone helps the writer recover
  from correctness bugs; ranking doesn't (F=0/3 because the writer
  reverts toward 16/17 instead of trying further fixes).
- task_012 best: tied at arm B, D, E (2/3). Spec ambiguity on date
  order has a guess-luck ceiling.
- task_013 best: arm F (3/3 stable_pass). Ranking lets the writer
  systematically explore variants when the binary signal shows
  regression. Arm A managed this implicitly 1/3 seeds; arm F gets it
  3/3.

## Pre-registered criterion: result

**H1 (schema-neutrality): PASSES.**

- Crit 1 — arm D within ±1 task/seed of arm B:
  D per seed = [11, 11, 12], B per seed = [11, 12, 11], delta = [0, -1, +1].
  All within ±1. **PASS.**
- Crit 2 — arm D underspec median ≥ arm A median:
  A = 0.500, D = 0.500. ≥ holds. **PASS.**

**H2 (attempt-comparison): FAILS.**

- Crit 1 — arm F underspec median STRICTLY > arm A median:
  A = 0.500, F = 0.500. Strict inequality fails. **FAIL.**
- Crit 2 — arm F task_007 converges in ≥ 2/3 seeds:
  F = [False, False, False] = 0/3. **FAIL.**

Both criteria failed. No goalpost movement: the strict-inequality clause
in H2 crit 1 was load-bearing and the result obeyed it. Task_013 going
3/3 is striking but it doesn't satisfy a criterion designed to require
underspec recovery as a property, not on one specific task.

**Interaction effect (descriptive, not pass/fail):**

- Arm E aggregate = 34/39; arm F aggregate = 32/39.
- Delta = +2 in favor of E (both prompts) over F (ranking alone).
- Per-task: E beats F on task_007 (1 vs 0) and task_012 (2 vs 0); F
  beats E on task_013 (3 vs 1). E ties D on aggregate.
- Interpretation: ranking alone is too aggressive — it pushes the
  writer to revert whenever the current attempt isn't the best-so-far,
  even when the right move is to keep exploring a different
  interpretation. The iter2 writer prompt acts as a brake on naive
  reversion. The combination is closer to optimal than either alone.

## task_013 trajectory analysis across all 6 arms (seed 1)

This is the qualitative anchor. Same task, same seed, six prompt
configurations; trajectories diverge.

**Arm A (writer-alone): 16 → 17. Converged in 2 iters.**

Attempt 2 reasoning: "The prior attempt passed 16/17 tests. Without
seeing which test failed, I need to think about what edge case might be
missing." Writer noticed it was at 16/17 and tried CR/CRLF handling.
Got it. Implicit binary-signal exploration worked.

**Arm B (multi-agent untyped): 15 → 15 → 16. Stuck.**

Reviewer + arbiter flagged whitespace-adjacent-to-newlines (iter2's
identified failure mode). Writer obeyed in iter2 (still 15/17), then
iter3 reverted partly (16/17). Never recovered to 17. Same single-seed
narrative as iter1.

**Arm C (typed + iter2 writer prompt): 15 → 15 → 15. Locked in.**

Attempt 3 reasoning verbatim: "The code is essentially the same as
attempt 2, which got 15/17 tests passing. The reviewers confirmed the
logic is correct for all the cases they analyzed. Since the code is
unchanged from attempt 2 and both reviewers in attempt 2 said the
approach is correct…" The iter2 prompt told the writer not to change
interpretation just because the critic disagrees. The writer obeyed
maximally — submitted the same code in iter3.

**Arm D (typed only, no extra prompts): 16 → 15 → 15. Regressed.**

Attempt 3 reasoning: "Attempt 1 got 16/17, Attempt 2 got 15/17 — so
attempt 2 regressed." Writer noticed the regression but stayed near
attempt 2 instead of reverting to attempt 1's approach. Without
explicit ranking, the writer's spontaneous comparison was fragile.

**Arm E (typed + iter2 prompt + ranking): 16 → 15 → 13. Regressed twice.**

Attempt 3 reasoning: "Attempt 1 scored 16/17 and attempt 2 scored
15/17. The key difference between attempts 1 and 2 was switching from
`[ \t]+` to `[^\S\n]+` for matching non-newline whitespace. Attempt 2
scored lower (15), so that change may have introduced a regression."
Writer SAW the regression (ranking forced the comparison) but the iter2
prompt told it to hold interpretation. Conflicting signals → writer
made a different change in iter3 (going further) and got 13/17. Worst
trajectory.

**Arm F (typed + ranking only): 15 → 17. Converged in 2 iters.**

Attempt 2 reasoning: "Based on the reviewer feedback, the main issues
were: 1. Whitespace-only lines… were not being collapsed together with
adjacent newlines — they should be treated as blank lines." Writer
adopted the reviewer's spec-interpretation finding cleanly because the
iter2 prompt wasn't there to suppress it. Ranking made the writer
notice "attempt 1 = 15/17, can I do better." Adopted critic suggestion,
hit 17/17.

**The pattern:** explicit ranking lets the writer reason about its
trajectory ("attempt N got X, attempt M got Y"). But when combined with
the iter2 "don't change your interpretation" prompt (arm E), the
ranking surfaces the regression but the prompt blocks the obvious fix.
When alone (arm F), the writer can act on the comparison. When the
ranking is implicit (arm A), it works some seeds and not others
(1/3 conv across seeds — same as iter1 narrative).

## Adversarial-robustness sanity check (arms D, E, F)

Typed schema continues to perform as designed. Per arm (3 seeds × 13
tasks × up to 3 iters), computed by `aggregate_iter3.py`:

| metric | arm D | arm E | arm F |
|---|---|---|---|
| Total findings | 120 | 116 | 184 |
| Validated spec-violations | 19 | 19 | 33 |
| Spec-interpretations | 101 | 97 | 151 |
| Downgrades (SV-attempt → interp) | 32 | 36 | 48 |
| Quotes verified in spec | 20 | 19 | 34 |
| Quotes NOT in spec (downgrade trigger) | 23 | 26 | 25 |
| Contamination (validated SV with bad quote) | **0** | **0** | **0** |

Validator integrity holds across all iter3 arms. 0 contamination
across 420 total findings. Arm F generates ~50% more findings than D/E
because its writer iterates more often (it rarely 1-shots and ranking
encourages multi-iteration trajectories); per-finding behavior is
identical across arms.

The schema fix from iter2 is therefore preserved as a clean
reusable artifact independent of the rest of iter3's design choices.

## What iter3 demonstrates about the architecture

1. **The schema fix from iter2 was a clean win.** Arm D = arm B
   aggregate, identical convergence, but with a calibrated critic. The
   "spec_quote required + validator-checked" schema is a reusable
   methodological artifact for any multi-agent critique system.

2. **There is no single best prompt configuration on this corpus.**
   B, D, E all hit 34/39 with different failure mixes. The "right"
   prompt depends on which task class you care about; no architectural
   choice dominates across the matrix.

3. **The writer's binary-signal exploration is genuinely fragile.** Arm
   A's 1/3 conv on task_013 was lucky; arm D regresses 0/3 on task_013
   even without the iter2 prompt. The implicit comparison the iter2
   summary attributed to "arm A's self-recovery loop" is unreliable
   across seeds.

4. **Explicit attempt-ranking helps the writer in one specific failure
   mode and hurts in others.** F's 3/3 on task_013 is the strongest
   single effect Phase 2 produced. F's 0/3 on task_007 + task_012 is
   the strongest concurrent regression. The intervention is not a free
   improvement — it changes how the writer reasons about exploration in
   ways that help on tasks where the right move is "revert" and hurt
   where the right move is "keep trying."

5. **Underspec convergence has a ceiling that prompt engineering does
   not break.** Across all 6 arms, no underspec median exceeds 0.5.
   task_012 (date ambiguity) caps at 2/3 in the best arms; task_013
   (whitespace ambiguity) caps at 3/3 in F but accomplishes that by
   sacrificing other failure modes. Closing the underspec gap
   uniformly requires information the writer doesn't currently have —
   which motivates Phase 3.

## Cost

- Wall: ~25 min D + ~42 min F + ~25 min E ≈ 92 min total, sequential.
- API spend: ~$30 at Sonnet 4.6 rates.
- Reuse of arm C from iter2 saved ~32 min and ~$10.

## Files / reproducibility

- `results/phase2/iter3_preregistration.md` — committed before runs
- `results/phase2/iter3/<arm>/seed<N>/<task>.json` — all per-run data
- `results/phase2/iter3/<arm>/seed<N>_summary.json` — per-arm-seed aggregates
- `results/phase2/iter3/aggregate.json` — machine-readable iter3 summary
- `results/phase2/iter3/logs/{armD,armE,armF}.log` — live console output
- `agents/writer.py` — `render_pass_ranking()` + Attempt.pass_ranking_shown
- `eval/phase2_harness.py` — arms D/E/F + iter3 output root
- `eval/aggregate_iter3.py` — produces aggregate.json + stdout summary

Re-run:
```bash
.venv/bin/python eval/phase2_harness.py D --seed 1 3
.venv/bin/python eval/phase2_harness.py E --seed 1 3
.venv/bin/python eval/phase2_harness.py F --seed 1 3
# loop seeds 1..3 per arm; bash _run_iter3.sh D|E|F
.venv/bin/python eval/aggregate_iter3.py
```

## Decision

iter3 is the last iter of Phase 2. The pre-registered criteria are
decided (H1 passes, H2 fails, interaction descriptive). No goalposts
were moved.

Phase 2 closes with:

- A validated reusable artifact: the typed-finding schema with
  validator-checked spec_quote.
- A bounded effect-size claim: multi-agent independent review beats
  single-agent on this corpus by ~2 tasks across 39 runs.
- A negative result: explicit attempt-ranking helps in one failure
  mode and regresses in others. Not a general fix.
- A motivation for Phase 3: underspec convergence is information-
  bounded, not architecture-bounded. The clarifying-question design
  doc is the next deliverable.

See [PHASE_2_FINAL.md](PHASE_2_FINAL.md) for the consolidated Phase 2
writeup and [docs/PHASE_3_DESIGN.md](docs/PHASE_3_DESIGN.md) for the
next-phase research design.
