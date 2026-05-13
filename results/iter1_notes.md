# Iteration 1 notes — pr-arbiter session 2 (cont'd)

Run date: 2026-05-13. Two prompt changes from baseline, evaluated against the same 20-PR corpus.

## Changes from baseline

**Reviewer (v2):**
- Added explicit "pay equal attention to correctness bugs" framing with concrete examples (None checks, off-by-one, reinvented stdlib, silent error suppression, missing branches).
- Anchored severity tiers with concrete examples instead of abstract definitions.
- Added "when in doubt between two tiers, pick the lower one."

**Arbiter (v2):**
- Flipped default action from "be willing to drop" to "default action: DROP".
- Added "first ask: does this PR have any real issue at all?" framing.
- Added duplicate-finding detection (the PII-in-logs split-finding case from baseline).
- Kept no-new-findings rule.

## Results — all four configurations

| config          | recall | precision | FP | critical | high  | medium | low   | neg-ctrl |
|-----------------|-------:|----------:|---:|---------:|------:|-------:|------:|---------:|
| v1 rev-alone    | 50.9%  | 48.3%     | 30 |    6/8   |  7/11 |  10/18 |  5/18 |     1/3  |
| v1 rev+arb      | 47.3%  | 52.0%     | 24 |    6/8   |  7/11 |   9/18 |  4/18 |     1/3  |
| **v2 rev-alone**| **52.7%** | **60.4%** | **19** |    6/8   |  8/11 |  11/18 |  4/18 |     1/3  |
| v2 rev+arb      | 38.2%  | 70.0%     |  9 |    4/8   |  6/11 |   7/18 |  4/18 |     1/3  |

## Headline

**v2 reviewer-alone is the best configuration across the board.** Recall up, precision up 12 points, FP down by a third. The arbiter on top of v2 reviewer makes things worse on every metric except precision, and the precision gain comes at the cost of dropping two critical findings.

The multi-agent architecture, as currently structured (single-pass reviewer → triage arbiter with no-new-findings rule), does not improve over a well-calibrated reviewer alone. That is the load-bearing finding from this iteration.

## What the reviewer v2 changes accomplished

- Severity anchoring fixed the over-flagging problem. False positives went from 30 to 19 without losing matched findings. The model had been inflating low/medium issues to medium/high; with concrete tier examples it calibrates.
- Correctness-critical bias closed one of the two baseline blind spots. pr_019 (reinvented `send_from_directory`) is now caught by the reviewer — the "reinvented stdlib or local helpers" line in the prompt did exactly what it was designed to do. pr_015 (missing JSON validation) is still missed; the prompt did not generalize to that case.
- Alex persona recall jumped from 30% to 50% on the reviewer-alone path. The correctness-critical framing surfaces the architectural issues that single-file-diff review usually misses.

## What the arbiter v2 changes broke

The arbiter dropped **two criticals** (path traversal on pr_001, reinvented send_from_directory on pr_019) and two highs (race condition on pr_004, open email relay on pr_015). All of these are exactly the kind of finding the system exists to surface.

The earlier debate about numeric drop-rate anchors was the right one to have, but the fix went the wrong direction. The v1 prompt anchored on "be willing to drop"; the v2 prompt anchored on "default action: DROP". The first under-shoots, the second over-shoots. Both are anchored prompts; neither is calibrated to actual base rates. The arbiter would need to see drop-rate feedback (or be evaluated on per-PR drop decisions) to find the middle ground — a static prompt can't do this.

## What persists across all four configurations

- **pr_007 negative control still fails.** Marcus's clean-refactor PR produces 1 FP from the reviewer in every run; the arbiter never catches it. This is a stubborn pattern-match failure — the reviewer sees `_legacy_normalize_path` next to a new `_normalize_path` and concludes one of them must be a bug. The arbiter can't undo this without re-reading the diff itself, and even the v2 arbiter (default drop) keeps the finding. Worth a specific intervention.
- **Critical recall ceiling is 6/8 on the reviewer.** Two criticals (pr_015 missing JSON validation, pr_017 set-then-use config without persistence) remain uncaught regardless of prompt. These look like the boundary of single-pass single-file reasoning — the bug requires holding "if this returns None, downstream code crashes" or "this state change isn't persisted" in mind while reading.

## Per-persona (v2 reviewer-alone)

| Persona | Recall | FP | vs baseline |
|---------|-------:|---:|-------------|
| Marcus  |    50% |  7 | 62% → 50% (regression — investigate)  |
| Priya   |    53% |  4 | 53% → 53% (flat; FP from 9 to 4)      |
| Devon   |    55% |  4 | 55% → 55% (flat; FP from 6 to 4)      |
| Alex    |    50% |  4 | 30% → 50% (big win)                   |

Marcus regression is unexpected. The severity-anchoring change apparently dropped some Marcus findings the looser baseline was catching. Worth inspecting before iter2.

## Open question for next iteration

The arbiter has been tested at two prompt extremes (lenient, aggressive). Both lose to reviewer-alone when the reviewer is well-calibrated. Three paths forward, in increasing radicalness:

1. **Find the arbiter sweet spot.** A prompt halfway between v1 and v2 might preserve criticals while still dropping FPs. Probably 2-3 more iterations to converge. Diminishing returns; even the best arbiter case from iter1 would gain ~5pp precision against a 60% baseline.

2. **Change the arbiter's job.** Instead of drop/keep over reviewer findings, have the arbiter independently review the diff and emit findings + reviewer-comparison. The "no new findings" rule was deliberately conservative; relaxing it lets the arbiter compensate for reviewer misses (like the persistent pr_015 missing-JSON-validation case). Risk: arbiter becomes a second reviewer, doubling cost without doubling signal.

3. **Different architecture.** Reviewer→reviewer self-critique loop (no second model). Or reviewer→arbiter where arbiter only triages confidence levels, not keep/drop decisions, and the output is "blocking findings" vs "advisory findings" rather than a flat list. The eval would need to change to score blocking vs advisory separately.

My read: option 2 is the most interesting because it tests whether the second agent can ADD signal, not just filter. Option 3 is more ambitious but requires eval changes. Option 1 is the conservative move and the cheapest to run.

The kickoff doc's bailout — switch to mutation testing where eval is automatic — should be on the table if iter2 doesn't show a clear arbiter win. The risk of iter1 → iter2 → iter3 being vibes-only iteration is real now that the headline finding has flipped against the architecture.

## Artifacts

- `results/iter1_20260513.json` — v2 reviewer-alone over all 20 PRs.
- `results/iter1_20260513_arbiter.json` — v2 reviewer findings (cached) fed through v2 arbiter.
- `results/iter1_run.log`, `results/iter1_arbiter_run.log` — raw stdout (gitignored).
- Prompts: `agents/reviewer.py` and `agents/arbiter.py` reflect the v2 system prompts as of this commit.
