# phase2_corpus

13 tasks for the Phase 2 writer-loop experiment. Each task is a small
programming problem with deterministic tests serving as ground truth.

## Layout

```
phase2_corpus/
  task_NNN/
    spec.md       # task description shown to the writer agent
    tests.py     # pytest suite — the ground truth
    solution.py  # reference solution, NOT shown to writer (eval harness must isolate)
  manifest.json   # task index with difficulty/style tags
```

## Task distribution

| Difficulty  | Count | Style breakdown                              |
|-------------|-------|----------------------------------------------|
| easy        | 4     | 2 hand-authored, 2 HumanEval-shaped          |
| medium      | 4     | 2 hand-authored, 2 HumanEval-shaped          |
| hard        | 3     | 3 hand-authored                              |
| underspec   | 2     | 2 hand-authored (deliberately ambiguous)     |

Total: 13 tasks, 197 tests.

## Style note: HumanEval-shaped vs hand-authored

**Hand-authored** tasks were designed from scratch. Unlikely to be in
Sonnet training data; the writer has to reason about the spec.

**HumanEval-shaped** tasks use patterns similar to public benchmarks
(query string parsing, list flattening, JSON path, interval merge) but
with modified specs — added edge cases, twisted requirements, or
behavior the canonical solution doesn't handle. The point is to keep
the test-writing economy without inheriting the memorization risk.

The 4 HumanEval-shaped tasks (001, 004, 007, 008) require a sanity
check before relying on them: confirm Sonnet 4.6 does NOT one-shot the
full test set. If it does, harden the spec or add edge cases.

## Underspec tasks

Tasks 012 (date parser) and 013 (whitespace normalizer) have
deliberately incomplete specs. The tests pick specific
interpretations the spec is silent on — e.g., US vs European date
order, whether blank lines collapse to one or are preserved.

These exist to test something the Phase 1 reviewer/arbiter couldn't:
surfacing ambiguity in requirements before the writer commits to a
wrong direction. A writer that just guesses will fail roughly half
the time. A writer that asks the right question can succeed.

Note for the harness: notes within `tests.py` headers document the
specific interpretation chosen. These notes are NOT to be shown to
the writer.

## Verifying the corpus

From the corpus root:

```bash
for d in task_*/; do
  cd "$d" && python3 -m pytest tests.py && cd ..
done
```

Every task should pass 100% against its reference solution. If any
task fails, the corpus is broken — fix before running the agents.

## What this corpus is NOT

- **Not a benchmark of code generation in general.** 13 tasks is too
  small for that. It's a probe for whether the Phase 1 multi-agent
  patterns generalize to a writer loop.
- **Not exhaustive.** Each task has 11-20 tests, enough to discriminate
  reasonable from broken, not enough to be a full spec.
- **Not the eval harness.** Building `run_tests(task_id, code_str)` and
  the writer-loop driver is Phase 2 agent work, not corpus work.
