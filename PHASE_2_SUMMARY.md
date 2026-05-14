# pr-arbiter Phase 2 — writer-loop summary

Phase 2 tests whether the multi-agent reviewer + arbiter pattern from
Phase 1 generalizes to a **writer-loop** architecture: a writer agent
produces code, the reviewer + arbiter critique, the writer revises,
iterate until tests pass or budget is hit.

Phase 1 measured *review*. Phase 2 measures *writing*.

## Setup

13 tasks, 197 deterministic tests across four difficulty tiers (easy /
medium / hard / underspec). Corpus is in `phase2_corpus/`; see
`phase2_corpus/README.md` for task selection rationale.

Two configurations evaluated on the same corpus:

- **writer-alone** (ablation). Writer + binary pass count signal only.
  No reviewer, no arbiter. Tests whether the loop itself works without
  external critique.
- **writer + reviewer + arbiter** (multi-agent). Reviewer sees the
  attempt history (catches regression / oscillation). Arbiter sees the
  latest attempt only (independent second pass, anti-anchoring property
  from Phase 1). Writer sees both critique streams + binary pass count.

### Design choices made before running

These were locked before the API spend so the run measures something
real rather than tuning toward a desired headline:

1. **Writer never sees the tests.** Spec only. No test names, no test
   inputs, no expected values. Forces spec-interpretation to carry the
   reasoning load.
2. **Writer never sees test failures.** Only a binary pass count
   (`5 / 17 passing`). Tracebacks and failed-input values would leak
   ground truth.
3. **Reviewer sees history. Arbiter sees latest only.** Mirrors the
   Phase 1 split: reviewer is the primary feedback, arbiter is the
   independent second-pass with no anchoring to prior critiques.
4. **Underspec tasks: writer guesses.** No oracle for asking
   clarifying questions. The two underspec tasks (`task_012`,
   `task_013`) deliberately have ambiguous specs; the test suite picks
   a specific interpretation the spec is silent on.
5. **Budget = 3 iterations.** Anything that converges in 1 is "writer
   one-shotted it" (no multi-agent value). Anything past 5 is probably
   stuck and just burns API calls.
6. **Sequential ablation.** Writer-alone first, full corpus, then
   multi-agent full corpus. Clean per-arm data.

All agents use Sonnet 4.6 — same model as Phase 1 — so the ablation
argument (same model, different architectures) is preserved.

## Iter 1 result — tie on aggregate, divergent on failure modes

| mode | pass rate | test recall | avg iter | wall |
|------|-----------|-------------|----------|------|
| writer-alone           | 11/13 (84.6%) | 193/197 (98.0%) | 1.46 | 413s |
| writer + rev + arb     | 11/13 (84.6%) | 192/197 (97.5%) | 1.46 | 615s |

Identical aggregate convergence. Multi-agent costs ~1.5× wall and ~3×
API calls. **The aggregate tie hides a real shift in failure mix.**

By difficulty:

| difficulty | n | writer-alone | multi-agent |
|------------|---|--------------|-------------|
| easy       | 4 | 4/4          | 4/4         |
| medium     | 4 | 3/4          | **4/4** (multi-agent fixed `task_007`) |
| hard       | 3 | 3/3          | 3/3         |
| underspec  | 2 | 1/2          | **0/2** (multi-agent broke `task_013`) |

The aggregate tie is real, but it's a **swap, not a wash.** Multi-agent
gained a medium-difficulty task and lost an underspec task. Same
direction as Phase 1: helps with correctness, hurts on ambiguity.

## Worked examples — where the signal lives

### `task_007` — multi-agent WIN

JSON path resolver (medium, HumanEval-shaped). Writer's first attempt
had multiple correctness bugs: bracket parsing, mutable sentinel
default, dot-handling on edge cases, swallowed exceptions that
violated the spec's "raise on missing key" rule.

Trajectory:

- **writer-alone:** 15/17 → 16/17 → 16/17. Stuck across 3 iterations.
  The binary signal told the writer it was wrong but didn't say where.
- **multi-agent:** iter1 timed out (infinite loop on some inputs).
  Reviewer + arbiter together produced 10 specific findings — bracket
  parser, sentinel default, dot-handling, swallowed exceptions, path
  starting/ending with `.`. iter2: 17/17.

This is the Phase 1 multi-agent value, restated for code generation:
**when the writer is wrong about correctness, specific natural-language
critique gives it the diagnostic information the binary signal can't.**
The reviewer wasn't telling the writer the answer; it was telling the
writer where to look.

### `task_013` — multi-agent LOSS

Whitespace normalizer (underspec). Spec is ambiguous on whether spaces
adjacent to newlines should be stripped or preserved. The test suite
picks one interpretation; the writer has to guess.

Trajectory:

- **writer-alone:** 16/17 → 12/17 → 17/17. Oscillated, recovered.
  Binary signal alone let the writer notice it had regressed and try a
  different approach.
- **multi-agent:** 11/17 → 16/17 → 13/17. Iter1 reviewer + arbiter
  flagged "spaces adjacent to newlines aren't stripped". Iter2 writer
  obeyed (16/17). Iter3 the arbiter doubled down asserting more
  whitespace assumptions; writer over-corrected and broke previously
  passing cases.

The arbiter expressed false certainty about behaviour the spec didn't
specify, the writer trusted it, and the loop diverged. **Critic
confidence in the face of spec ambiguity pushes the writer in the
wrong direction.**

This is the iter1-arbiter overshoot from Phase 1 (severity inflation
dropping criticals), translated to a different surface: instead of
over-confidence about severity, over-confidence about
spec-interpretation.

## What this means

Two phases, two corpora, same architectural finding:

| | Phase 1 (review) | Phase 2 (writer-loop) |
|-|------------------|----------------------|
| Domain | PR review against planted bugs | Code generation from spec |
| Multi-agent win | `pr_009` XSS critical caught by independent arbiter (single agent missed it across every variant) | `task_007` correctness bugs caught (single-agent loop stuck) |
| Multi-agent loss | False positives on style-heavy PRs (fixed by mutual triage in iter4) | False direction on underspec (no equivalent fix yet) |
| Operating point | Multi-agent for criticals; single-agent at iter3 blocking tier for precision | Same trade-off, no two-tier output yet |

The architectural finding is robust:

1. **Independent multi-agent review beats single-agent on correctness
   bugs the latter can't catch alone.** Same model, different
   architecture — the additional pass surfaces something a single pass
   doesn't.
2. **Independent multi-agent review loses to single-agent on ambiguity
   where the critic introduces false certainty.** The independence
   property that helps catch bugs also produces confidently-wrong
   spec-interpretation.
3. **The tradeoff is real, not a Phase 1 artifact.** Two corpora, two
   surfaces, two architectures (review vs write), same pattern.

## What's not there yet

Phase 2 has **no mutual-triage analog.** Phase 1's iter3 fix for the
overshoot — two voices voting KEEP/DROP on each finding — doesn't map
cleanly. There's no merge-list to triage; feedback flows to the writer
as a continuous stream rather than a discrete list. The shape of the
fix would have to be different (e.g., a critic that explicitly tags
"high-confidence correctness bug" vs "spec-ambiguity guess"; or two
critic voices that have to agree before the writer is shown
spec-interpretation feedback).

Three candidate iter2 directions, in order of expected value:

1. **Underspec-aware reviewer prompt.** Instruct the reviewer/arbiter
   to surface spec ambiguity as a *question* rather than an
   *assertion*. Targets `task_013`-class failures specifically. Cheap
   to test; binary outcome.
2. **Variance run.** Re-run both arms 3× with different seeds. N=13
   tasks is small; an 11/13 vs 11/13 could flip with one re-roll.
   Bounds the tie before reading too much into it.
3. **Mutual-triage analog.** Two critic voices vote
   blocking/advisory/drop on each finding before it hits the writer.
   Phase 1's fix for over-rotation; whether it transfers to write is
   the load-bearing question.

Decision pending.

## Cost

13 tasks × ~3-5 API calls per task per mode. Writer-alone: ~60 calls
total. Multi-agent: ~150 calls. At Sonnet 4.6 rates, total spend for
Phase 2 iter 1 is on the order of a few dollars. Wall-clock: 7 minutes
writer-alone, 10 minutes multi-agent.

## Methodology choices that worked (Phase 2)

- **Same ablation discipline as Phase 1.** Writer-alone is the
  load-bearing control; without it the multi-agent number means
  nothing.
- **Hide tests from the writer.** Showing tests would have collapsed
  the task to "fit-the-tests" and removed the multi-agent surface area
  entirely.
- **Hide failure traces from the writer.** Binary pass count only.
  Forces the multi-agent feedback to carry the diagnostic signal;
  otherwise writer + traces would beat writer + reviewer + arbiter on
  cost.
- **Different review/arbiter modules from Phase 1.** New file names
  (`writer_reviewer.py`, `writer_arbiter.py`) so Phase 1 keeps
  working. No coupling.
- **Per-task JSON dump.** Reviewer/arbiter findings + writer reasoning
  per iteration. The qualitative narratives (`task_007` win,
  `task_013` loss) came from inspecting these, not from the aggregate.

## Reading guide

- `phase2_corpus/` — 13 tasks, 197 tests, manifest, README
- `agents/writer.py` — writer agent (new)
- `agents/writer_reviewer.py`, `agents/writer_arbiter.py` — Phase 2
  reviewer + arbiter (new, separate from Phase 1 to keep Phase 1
  intact)
- `eval/sandbox.py` — tmpdir + pytest subprocess + json-report parse
- `eval/writer_loop.py` — single-task loop driver
- `eval/phase2_harness.py` — corpus runner + summarize
- `results/phase2/writer-alone/` — per-task JSON for ablation arm
- `results/phase2/writer_reviewer_arbiter/` — per-task JSON for
  multi-agent arm
- `results/phase2/<mode>_summary.json` — corpus-level aggregates
- `SUMMARY.md` — Phase 1 writeup
- `docs/PHASE_2_HANDOFF.md` — original Phase 2 design doc
