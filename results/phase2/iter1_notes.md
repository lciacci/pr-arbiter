# Phase 2 iter 1 — writer-loop, baseline comparison

Date: 2026-05-14
Model: Sonnet 4.6 (all agents)
Corpus: phase2_corpus, 13 tasks, 197 deterministic tests

## What iter 1 tested

Whether the Phase 1 multi-agent pattern (reviewer + independent arbiter)
helps a writer agent converge on correct code given:

- spec only (no tests, no failure traces)
- binary pass count signal (`5 / 17 passing`)
- 3-iteration budget per task
- reviewer with full attempt history; arbiter with latest attempt only

Both arms run sequentially over the same 13 tasks. Per-task JSON dumps
in `results/phase2/writer-alone/` and
`results/phase2/writer_reviewer_arbiter/`.

## Aggregate

| mode | pass rate | test recall | avg iter | wall |
|------|-----------|-------------|----------|------|
| writer-alone           | 11/13 (84.6%) | 193/197 (98.0%) | 1.46 | 413s |
| writer + rev + arb     | 11/13 (84.6%) | 192/197 (97.5%) | 1.46 | 615s |

Same convergence rate. Multi-agent costs ~1.5× wall, ~3× API calls. The
aggregate tie is real but conceals a failure-mix shift documented below.

## By difficulty

| difficulty | n | writer-alone | multi-agent |
|------------|---|--------------|-------------|
| easy       | 4 | 4/4          | 4/4         |
| medium     | 4 | 3/4          | **4/4** (`task_007` fixed) |
| hard       | 3 | 3/3          | 3/3         |
| underspec  | 2 | 1/2          | **0/2** (`task_013` broken) |

## Per-task

| task | difficulty | writer-alone | multi-agent | delta |
|------|------------|--------------|-------------|-------|
| task_001 | easy      | 1-shot 13/13 | 1-shot 13/13 | — |
| task_002 | easy      | 1-shot 15/15 | 1-shot 15/15 | — |
| task_003 | easy      | 1-shot 14/14 | 1-shot 14/14 | — |
| task_004 | easy      | 1-shot 14/14 | 1-shot 14/14 | — |
| task_005 | medium    | 1-shot 17/17 | 1-shot 17/17 | — |
| task_006 | medium    | 1-shot 15/15 | 2-iter 15/15 | extra iter, same outcome |
| task_007 | medium    | 3-iter 16/17 (stuck) | 2-iter 17/17 | **multi-agent WIN** |
| task_008 | medium    | 1-shot 14/14 | 1-shot 14/14 | — |
| task_009 | hard      | 1-shot 16/16 | 1-shot 16/16 | — |
| task_010 | hard      | 1-shot 20/20 | 1-shot 20/20 | — |
| task_011 | hard      | 1-shot 14/14 | 1-shot 14/14 | — |
| task_012 | underspec | 3-iter 8/11  | 3-iter 10/11 | multi-agent partial improvement, neither converged |
| task_013 | underspec | 3-iter 17/17 (recovered) | 3-iter 13/17 (regressed) | **multi-agent LOSS** |

## task_007 — multi-agent WIN (full trajectory)

JSON path resolver. HumanEval-shaped, medium difficulty.

### Writer-alone

- iter1: 15/17. Reasoning quotes "I parse the path character by character, handling dot notation, bracket notation, and mixed notation."
- iter2: 16/17. Reasoning: "Looking at the prior attempt that got 15/17 tests, I need to figure out what the 2 failing cases might be." Writer guesses at edge cases, makes minor change.
- iter3: 16/17. Reasoning: "The logic is mostly the same between attempt 1 and 2... I need to figure out what the remaining failing test might be." Writer still guessing, doesn't move the needle.

**Diagnosis:** binary signal (`16/17`) tells writer it's wrong but not where. Writer keeps making locally plausible edits with no diagnostic information. 3 iterations burned, still stuck at 16/17.

### Multi-agent

- iter1: **timeout**. Writer produced code with an infinite loop on some inputs (caught by 30s sandbox timeout). Reviewer + arbiter ran against the code anyway and produced 10 findings combined.

Reviewer findings (high-severity sample):
- "Trailing empty component when path ends with a dot is not flushed correctly"
- "Negative index handling raises TypeError but the spec says treat as literal key"
- "Outer try/except catches KeyError, IndexError, TypeError unconditionally and may mask bugs"

Arbiter findings (critical):
- "Function signature uses `default=_SENTINEL` where spec shows `default=...` (Ellipsis). Tests doing signature introspection will fail."
- "`path.index(']', i+1)` raises uncaught ValueError on malformed paths like `'a[0'`"
- "Outer except wraps for-loop; chained exception context creates spurious `During handling of the above exception...`"

- iter2: **17/17**. Reasoning quotes: "Key changes from attempt 1: Signature fix — changed `default=_SENTINEL` to `default=...` (Ellipsis) to match the spec signature exactly. Removed the outer try/except wrapper."

**Diagnosis:** specific natural-language critique gave writer the diagnostic information binary signal couldn't. Direct analog of Phase 1 `pr_009` — multi-agent caught what single-agent couldn't see across 3 iterations.

### What multi-agent provided

The critical finding was the signature mismatch. The spec writes
`default=...` (literal Ellipsis as sentinel); writer used a custom
`_SENTINEL = object()`. Behaviorally equivalent on the happy path, but
fails any test that introspects the signature default. Binary signal
("you're wrong somewhere") gave the writer no chance of guessing this —
arbiter pointing at the exact line did.

## task_013 — multi-agent LOSS (full trajectory)

Whitespace normalizer. Underspec, deliberately ambiguous on whether
spaces adjacent to newlines should be stripped or preserved.

### Writer-alone

- iter1: 16/17. Reasoning: "Split on `\n`, clean each line (strip + collapse horizontal whitespace), filter out empty lines, rejoin."
- iter2: 12/17. Reasoning: "The prior attempt was collapsing ALL empty lines... The failing test likely involves a single blank line that should be preserved as one blank line." Writer changes approach: preserve single blank lines, collapse runs of 2+.
- iter3: **17/17**. Reasoning: "Attempt 1 got 16/17 and attempt 2 regressed to 12/17. I should go back to attempt 1's core logic (remove all empty lines)... attempt 1 was close (16/17) while attempt 2's change made things worse." Writer reverts + adds `\r\n` normalization.

**Diagnosis:** writer's binary-signal recovery loop worked. iter2 regression was diagnosed by the writer itself ("attempt 2's change made things worse"), and iter3 recovered. The pass count drop from 16→12 was enough signal to backtrack.

### Multi-agent

- iter1: 11/17. Writer's reasoning matches `writer-alone` iter1 (similar starting point).
  - Reviewer: "Handling of mixed whitespace adjacent to newlines is unspecified", "Tabs and other horizontal whitespace mixed with newlines may not be handled as expected"
  - Arbiter: "Carriage returns and `\r\n` line endings are not handled", "**[high] After collapsing non-newline whitespace, spaces immediately adjacent to newlines are not removed, leaving stray spaces at line boundaries.**"
- iter2: 16/17. Writer's reasoning: "Based on reviewer feedback, I made three key fixes: 1. Normalize carriage returns to `\n`. 2. Strip spaces/tabs immediately adjacent to newlines. 3. Collapse multiple newlines."
  - Arbiter: doubles down: "Stripping spaces/tabs around newlines means that 'hello   \n   world' is reduced to 'hello\nworld', discarding the surrounding spaces entirely. The spec example 'hello   world' → 'hello world' suggests spaces should become a single space, but once a newline is in play, what should happen is unspecified."
  - Arbiter (medium): "After `re.sub(r'[^\S\n]+', ' ', s)`, a leading/trailing `\n` adjacent to spaces could leave a stray space next to the newline."
- iter3: **13/17**. Writer's reasoning: "The reviewers on attempt 2 pointed out that stripping spaces adjacent to newlines is an extra unspecified behavior that may be causing the one remaining failure. Going back to something closer to attempt 1 but adding the `\r/\r\n` normalization fix from attempt 2."

**Diagnosis:** the arbiter expressed confident assertions about behavior
the spec did not specify. iter1 arbiter said "spaces adjacent to
newlines are not removed" (asserting they should be). Writer obeyed in
iter2 (16/17). Arbiter then walked back in iter3 critique ("once a
newline is in play, what should happen is unspecified") and writer
over-corrected, ending at 13/17.

The asymmetry between writer-alone and multi-agent here is striking:

- Writer-alone iter1 → 16/17 → 12/17 → **17/17** (self-diagnosed iter2 as regression, reverted)
- Multi-agent iter1 → 11/17 → 16/17 → **13/17** (followed arbiter into wrong region, then over-corrected)

The arbiter had asymmetric confidence: confident enough to push the
writer in iter1, but uncertain enough to undermine the writer's
iter2 fix. Writer ended up worse than no feedback.

### What multi-agent did wrong

The reviewer/arbiter prompts say "surface ambiguity" but their tool
schema only emits findings with severity tags
(critical/high/medium/low). There is no way to emit "this is a
guess." Result: every spec-interpretation hint is delivered with the
same authority as a correctness bug. The writer treats a `high`
arbiter finding the same whether it's "your code crashes on valid
input" (correctness) or "I think the spec implies X" (guess about
ambiguity).

This maps to the Phase 1 iter1 arbiter overshoot: the arbiter had no
way to express low confidence, so it expressed all findings with the
same weight, and inflated severity collapsed criticals. Same shape,
different surface.

## task_012 — underspec, neither converged

Date string parser. Spec is silent on US vs European date order. Test
suite picks US (`03/04/2024` → March 4). Writer guesses on this in
both arms.

- Writer-alone: 8/11, 8/11, 8/11. Stuck.
- Multi-agent: 10/11, 10/11, 10/11. Stuck at a slightly better point.

Both runs picked European order. Neither got to 11/11. Multi-agent had
~1 better test pass per run (different writer initialization caught a
formatting edge case), but neither could discover the US-order
interpretation from the binary signal alone. Reviewer + arbiter
correctly noted "date order is ambiguous in the spec" but had no way
to break the tie.

Implication: pure-guess on truly ambiguous specs has a ceiling neither
arm can break. Option 1 of the iter 2 candidates (clarifying-question
mode) is the only architecture that could plausibly close this.

## Cost

API calls (approximate):

| mode | writer | reviewer | arbiter | total |
|------|--------|----------|---------|-------|
| writer-alone           | ~19  | 0  | 0  | 19  |
| writer + rev + arb     | ~19  | ~13 | ~13 | ~45 |

(Convergent-on-iter-1 tasks skip reviewer/arbiter calls entirely.)

Wall: 7 min writer-alone, 10 min multi-agent.

## Methodology calls that proved load-bearing

1. **Sequential ablation.** Running writer-alone full corpus before
   multi-agent gave clean per-arm data. With interleaved per-task runs,
   stochastic variance would have made `task_007` win look like
   "lucky writer roll" rather than "feedback helped."
2. **Hide tests entirely.** The arbiter's `task_007` critical finding
   ("signature uses `_SENTINEL` not `Ellipsis`") would have been
   invisible to a reviewer that saw the test file — they would have
   seen the test expectation directly and not had to read the spec
   signature. Hiding tests forced the reviewer to use the spec the
   same way the writer does.
3. **Different reviewer/arbiter modules from Phase 1.** Building
   `agents/writer_reviewer.py` and `agents/writer_arbiter.py`
   instead of modifying Phase 1's `agents/reviewer.py` kept Phase 1
   intact and let the prompts diverge cleanly (PR review and code
   generation need different system prompts).
4. **Per-task JSON dump.** The qualitative narratives (`task_007`
   win, `task_013` loss) came from inspecting the per-task dumps,
   not the aggregate. Without the dumps the failure-mix shift would
   have been invisible — both arms would have looked identical at
   11/13.

## What did NOT prove load-bearing

- **Reviewer history vs latest-only.** No `task_007`/`task_013`
  trajectory required the reviewer to recall a prior attempt. The
  reviewer-sees-history split was set up to catch regression /
  oscillation patterns, but the runs didn't exhibit the
  cross-iteration patterns that would have shown the difference.
  Worth revisiting in iter 2 if more iterations per task surface
  oscillation cases (or remove the split as YAGNI).

## What iter 2 should test

In order of expected value:

1. **Confidence tagging in reviewer/arbiter tool schema.** Add a
   `confidence` field (e.g., `correctness` vs `spec-guess`) so the
   writer can weight feedback. Directly targets the `task_013`-class
   failure: arbiter's spec-guess was delivered with same authority as
   a correctness bug. Cheap; binary outcome ("does task_013 stop
   regressing under multi-agent?").
2. **Variance run.** Re-run both arms 3× with different seeds. N=13
   is small; an 11/13 vs 11/13 could flip with one re-roll. Bounds
   the tie before reading too much into it.
3. **Mutual-triage analog.** Two critic voices vote agree/disagree
   on each finding before writer sees it. Phase 1 fix for
   over-rotation; whether it transfers to the write surface is open.
4. **Clarifying-question mode (deferred).** Allow writer to emit one
   question to a fixed oracle on underspec tasks. Would close
   `task_012`-class failures but adds a new architectural piece;
   defer until 1–3 are exhausted.

The candidate to test first is (1). It's a one-prompt change with a
specific predicted outcome.

## Open questions still unanswered

From `docs/PHASE_2_HANDOFF.md`:

| question | answer found in iter 1? |
|----------|-------------------------|
| Writer sees prior attempts or latest+feedback? | locked at "writer sees full history"; held up — writer cited prior attempts to diagnose regressions |
| Reviewer/arbiter see prior attempts? | locked at "reviewer yes, arbiter no"; no clear evidence either way in iter 1 trajectories |
| Catastrophic divergence budget? | not exercised — no run got worse than iter 1 baseline by more than 3-4 tests |
| Two-tier output (Phase 1) vs flat feedback (Phase 2)? | flat held in iter 1; the `task_013` loss is the case for two-tier (confidence tagging in iter 2) |
| Per-task or global eval? | per-task narratives carried the signal; global aggregate hid the failure-mix shift |

## Files / reproducibility

- `phase2_corpus/manifest.json` — corpus index
- `agents/writer.py`, `agents/writer_reviewer.py`, `agents/writer_arbiter.py`
- `eval/sandbox.py`, `eval/writer_loop.py`, `eval/phase2_harness.py`
- `results/phase2/writer-alone/` — per-task JSON, ablation arm
- `results/phase2/writer_reviewer_arbiter/` — per-task JSON, multi-agent arm
- `results/phase2/writer-alone_summary.json` — aggregate, ablation arm
- `results/phase2/writer_reviewer_arbiter_summary.json` — aggregate, multi-agent arm

To re-run iter 1:

```bash
.venv/bin/python eval/phase2_harness.py writer-alone 3
.venv/bin/python eval/phase2_harness.py writer+reviewer+arbiter 3
```
