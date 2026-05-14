# Phase 2 handoff — corpus authoring + session resumption guide

This document is what you need to come back to in order to start Phase 2.
It is intentionally self-contained so you can either resume the current
session or start a fresh one and recover full context.

## Where we left off (Phase 1)

Phase 1 of `pr-arbiter` is complete. Three agents (reviewer + independent
arbiter + mutual triage), four iterations, blocking-tier output catches
7/8 criticals at 58.5% precision. See:
- `SUMMARY.md` — full project writeup
- `docs/index.html` — visual one-pager
- `results/pr_009_worked_example.md` — concrete demo of the multi-agent
  win
- `README.md` — repo overview + how to run

All committed and pushed to `main` at github.com/lciacci/pr-arbiter.

## Phase 2 — what we agreed on

Phase 2 tests whether the multi-agent patterns from Phase 1 generalize to
a **writer-loop** architecture: a writer agent produces code; the
reviewer + arbiter critique; the writer revises; iterate until tests pass
or budget hit.

The kickoff doc had two options (writer-loop OR spec → arch → impl); we
picked the writer-loop because:
- Test-based eval = automatic ground truth (no rubric authoring)
- Iteration loop is the interesting multi-agent dynamic
- Spec → arch → impl needs fuzzier ground truth (multiple valid
  architectures), harder to score

This maps to the Phase 1 kickoff's bailout option ("mutation testing where
eval is automatic") — applied to writing instead of bug-finding.

## Phase 2 corpus — what you need to build

10-15 tasks. Each task has three artifacts:

```
phase2_corpus/
  task_001/
    spec.md           # short task description, human-written
    tests.py          # pytest test suite, the ground truth
    starter.py        # optional, for iterate-on-existing-code tasks
    notes.md          # optional, author notes (NOT for agent context)
  task_002/
    ...
  manifest.json       # corpus summary, same shape as phase 1
```

### Task selection — what makes a good Phase 2 task

A good task is one where:
- **Tests can be deterministic.** No randomness, no time-dependence, no
  external services. Pure functions or clearly-bounded I/O.
- **Tests cover obvious cases AND edge cases.** 5-10 test cases per task.
  At least 2 should be edge cases the writer might miss on first attempt
  (empty input, None, very large input, malformed input). These are where
  the reviewer + arbiter loop should add value.
- **The task is solvable in ~50-200 lines.** Big enough to have multiple
  parts (so iteration matters), small enough that the writer can produce
  a full attempt per loop iteration.
- **The task isn't tutorial-trivial.** "Add two numbers" is too easy.
  "Implement a redis-compatible LRU cache with TTL" is right size.

### Task difficulty mix (target distribution)

| difficulty | count | example                                                    |
|------------|-------|------------------------------------------------------------|
| easy       | 3-4   | URL parser, query string builder, simple data transformer |
| medium     | 4-6   | LRU cache, rate limiter, JSON path resolver                |
| hard       | 3-4   | Bounded-time event scheduler, retry-with-backoff, simple DSL parser |
| underspec  | 2-3   | Deliberately ambiguous spec — tests reveal the spec       |

The "underspec" category tests something the Phase 1 reviewer/arbiter
couldn't: surfacing ambiguity in requirements before the writer commits
to a wrong direction.

### Sourcing tasks — three options

1. **HumanEval / MBPP subset.** Public benchmarks for code-generation
   eval. Permissive licensing. Pick 10-15 tasks at varying difficulty.
   Pros: zero authoring effort, comparable to other published work.
   Cons: well-known, possibly memorized by Sonnet; tests may not match
   the patterns we want.
2. **Hand-author from scratch.** Custom tasks targeting the kinds of
   bugs Phase 1 surfaced (regex sanitization, race conditions, off-by-one,
   reinvented stdlib). Pros: targeted, novel. Cons: slow (~30 min/task).
3. **Pick public OSS tickets.** Find good-first-issue-level tickets from
   archived OSS projects, distill into self-contained tasks with tests.
   Pros: realistic, decent difficulty. Cons: licensing + authoring overhead.

**Recommendation:** option 1 for the first 8-10 tasks (fast bootstrap),
option 2 for the 3-5 "interesting" tasks (the ones that test the
multi-agent value-add). Skip option 3 unless option 1 doesn't expose the
interesting failure modes.

### Anti-patterns to avoid (per Phase 1 ground rules)

- **Don't write tests so loose that any solution passes.** Tests are the
  eval. If they don't discriminate, you can't measure.
- **Don't write tasks that the writer already knows the answer to.**
  HumanEval has this risk; sanity-check that Sonnet doesn't one-shot the
  full task. If it does, modify the spec or add edge cases the canonical
  solution doesn't handle.
- **Don't add planted bugs to starter.py to test reviewer.** Phase 1
  already tested that. Phase 2 tests writer convergence. Different
  experiment.
- **Don't tune the corpus to the writer.** If the writer fails 100% on
  task_007, that's data, not a corpus bug. Same rule as Phase 1.

## Phase 2 architecture — what to build after the corpus

This is rough scope, not a commitment. Adjust after corpus exists.

### Agents

1. **writer**: produces code for the task. Sees: spec + tests (or some of
   the tests) + previous attempt + reviewer/arbiter feedback. Returns:
   complete code attempt.
2. **reviewer**: reuse Phase 1's `agents/reviewer.py` with minor prompt
   adjustments (review write-attempt code instead of PR diff).
3. **arbiter**: reuse Phase 1's `agents/arbiter.py` independent-second-pass
   pattern.
4. **triage** (optional iter): reuse Phase 1's mutual triage if the merged
   feedback list gets noisy.

### Loop

```
attempt = writer(spec, tests_visible, history=None)
while not tests_pass(attempt) and iterations < budget:
    feedback = reviewer(attempt) + arbiter(attempt, reviewer_findings)
    attempt = writer(spec, tests_visible, history=[...prev attempts, feedback])
    iterations += 1
```

Key design questions you'll need to make decisions on:
- **Which tests does the writer see?** All? A subset? None (writer
  works from spec only, tests are oracle)? Different answers test
  different things.
- **Does the writer see the test failures, or just reviewer/arbiter
  feedback?** Showing failures = easier task, less interesting.
  Hiding failures = pure multi-agent dynamics test.
- **Budget?** 3 iterations is a reasonable default. Anything that
  converges in 1 is "writer one-shotted it" (no multi-agent value).
  Anything past 5 is probably stuck.

### Eval metrics (Phase 2)

Different from Phase 1. Suggested:
- **Pass rate**: of N tasks, how many converged to passing tests?
- **Iterations to converge**: mean / median across passing tasks.
- **Regression rate**: when reviewer/arbiter feedback is wrong, does
  the writer regress on previously-passing tests?
- **No-feedback ablation**: same writer, no reviewer/arbiter loop.
  Does the multi-agent setup beat writer-alone?

The ablation is critical, same as Phase 1. If writer-alone matches
writer+reviewer+arbiter, the multi-agent pattern doesn't generalize.

### Cost estimate (rough)

Per task per attempt: ~4-5 API calls (writer + reviewer + arbiter + maybe
triage). 3 iterations average = ~15 calls per task. 15 tasks = ~225 calls.
At Sonnet 4.6 rates: ~$3-5 per full corpus run. Cheap.

## How to resume

You have two options.

### Option A: resume current session

If this session is still open or recoverable, just say "resume Phase 2"
and we pick up where we left off. The session has:
- Full Phase 1 architecture in context
- Knowledge of every iteration's tradeoff
- Pre-loaded familiarity with the codebase

Trade-off: this session has accumulated a lot of context. Phase 2 work
may compete for token budget with Phase 1 retrospection.

### Option B: fresh session, point at this repo

Start a new Claude Code session in the same repo. Open with:

> Phase 2 of pr-arbiter. Read `docs/PHASE_2_HANDOFF.md` first, then
> `SUMMARY.md`. Phase 2 corpus is in `phase2_corpus/` (which I've
> populated with N tasks). Start by reading the manifest and one task to
> calibrate, then propose the writer agent design.

The handoff doc + SUMMARY together carry forward what matters.
Recommended if it's been more than a few days or if you want a clean
context budget.

## Pre-Phase-2 checklist

Before kicking off the writer agent work, confirm:

- [ ] `phase2_corpus/` directory exists with at least 8 tasks
- [ ] Each task has `spec.md` + `tests.py` (+ optional `starter.py`)
- [ ] `phase2_corpus/manifest.json` lists every task with difficulty tag
- [ ] You've spot-checked that Sonnet doesn't one-shot the task (run the
  task description through `agents/reviewer.py` style call, see if it
  produces working code first try — if yes, harden the task)
- [ ] An eval harness sketch exists (mirror of `eval/harness.py` for
  Phase 2 — at minimum, `run_tests(task_id, code_str) -> {passed, failed,
  errors}`)
- [ ] `.env` still has `ANTHROPIC_API_KEY` (Phase 1 path; reuse)

Once that's in place, the agent work is mostly small adaptations of the
Phase 1 agents.

## Open questions to think through (before or during Phase 2)

These weren't decided in Phase 1 and will need answers in Phase 2:

1. **Should the writer see prior attempts, or only the latest +
   feedback?** Memory vs. amnesia per iteration.
2. **Should reviewer/arbiter see prior attempts?** Probably yes — pattern
   of "the writer keeps making this mistake" is signal.
3. **What's the budget for catastrophic divergence?** If iteration 3
   regresses on a test that iteration 1 passed, do we revert or push on?
4. **Two-tier output (Phase 1) vs. flat feedback (Phase 2)?** Mutual
   triage worked well as blocking/advisory — does that map to writer
   prompts ("address these, consider these")?
5. **Per-task or global eval?** Phase 1 corpus-level metrics worked.
   Phase 2 has the option of per-task narratives ("converged in 2 vs
   stuck at 4"), which may be more demoable.

Bring these up early — they shape the writer prompt + the eval design.

## What not to do (lessons from Phase 1)

- Don't iterate on prompts without re-running the eval.
- Don't add agents to fix problems that are corpus problems.
- Don't ship without ablation. Writer-alone vs writer+reviewer+arbiter
  is the load-bearing comparison.
- Don't change the corpus to make agents look better.
- If iter1 or iter2 of Phase 2 shows no signal, consider the bailout
  (single-agent writer is fine; this whole exercise was about measuring).

## Reading guide before Phase 2 starts

Order, roughly 30 min total:

1. `SUMMARY.md` (5 min) — what we built and learned
2. `results/pr_009_worked_example.md` (3 min) — the headline win
3. `docs/index.html` open in browser (2 min) — visual reinforcement
4. `results/iter3_notes.md` (5 min) — most relevant architecture details
5. `agents/reviewer.py` + `agents/arbiter.py` + `agents/triage.py`
   (10 min) — code patterns to mirror in Phase 2
6. This document, second pass (5 min) — Phase 2 plan crystallizes

After that, you're calibrated.
