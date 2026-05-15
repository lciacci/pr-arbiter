# New-session context — pr-arbiter

Paste-this-first context for starting a fresh Claude session on this
project. Read this file, then the three pointers it names. That is
the full bootstrap.

## What pr-arbiter is

A research project measuring whether **independent multi-agent code
review** (a reviewer agent + an independent arbiter agent, with an
anti-anchoring property) outperforms single-agent review. Run as a
sequence of pre-registered experiments. All agents are Sonnet 4.6.

## Phase status

- **Phase 1 — complete.** PR review against planted bugs. Multi-agent
  caught a critical XSS bug (`pr_009`) single-agent missed across
  every variant. Writeup: `SUMMARY.md`.
- **Phase 2 — complete.** Tested whether the property generalizes to
  code generation (writer-loop). Result: weak transfer — multi-agent
  beats writer-alone by ~2 tasks across 39 runs under 3-seed
  variance. The iter1 single-seed narrative was overfit; variance
  work corrected it. Reusable artifact: the typed-finding schema
  with validator-checked `spec_quote`. Writeup: `PHASE_2_FINAL.md`.
- **Phase 3 — designed, ratified, PAUSED.** Coherence-dimension PR
  review at scale: does multi-agent catch abstraction / convention /
  layer / duplication issues single-agent misses on real PRs?
  Paused pending a senior-annotator pilot.

## Where to start reading (the three pointers)

1. `docs/PHASE_3_RESUMPTION.md` — the paused-state capture. What's
   paused, the exact next action, committed vs open decisions, what
   NOT to do on resume. **Read this first when resuming Phase 3.**
2. `docs/PHASE_3_DESIGN.md` — the Phase 3 design (six design
   questions with recommendations + ratification checklist).
3. `docs/PHASE_3_DESIGN_REVIEW.md` — Q1/Q2 resolutions and the
   senior-pilot protocol.

For Phase 1 / Phase 2 background only if needed: `SUMMARY.md`,
`PHASE_2_FINAL.md`.

## Current state in one paragraph

Phase 3 design is complete and ratified. Implementation has not
started and must not start until a senior-annotator 5-PR pilot runs
(8-15 hours of senior-rater time; the project lead is the rater and
is time-constrained). The pilot produces a recall number that fires
a pre-registered decision rule selecting the corpus path. Provisional
repo is pydantic. Phases 1 and 2 are merged to main and done.

## The exact next action

Run the senior-annotator 5-PR pilot per the protocol in
`docs/PHASE_3_DESIGN_REVIEW.md`. It is a human task — an LLM cannot
produce the ground-truth annotations (the LLM reviewer is the thing
under test; LLM-generated ground truth makes the experiment
circular). Until the pilot's recall number comes in, the corpus path
is undecided and nothing downstream can proceed.

## Working conventions on this project

- Every change ships as its own PR; merge commits (not squash);
  delete the branch after merge.
- The repo lives at `/Users/lciacci/Claude/pr-arbiter`; agent work
  happens in a git worktree. The `.venv` and `.env` are in the main
  repo root — symlink them into a fresh worktree if needed.
- Pre-registration before every experiment run. Strict,
  conjunctive success criteria. No goalpost movement post-run.
- 3-seed variance minimum — Phase 2 proved single-seed conclusions
  overfit.
- Dogfooding: `eval/review_pr.py` runs the Phase 1 reviewer+arbiter
  on the project's own PRs. It filters to `.py` files; docs-only
  PRs produce no review.
- Caveman mode is active in the current session config (terse
  responses); not a project property.

## What NOT to do

- Do not start Phase 3 implementation before the senior pilot.
- Do not let an LLM produce senior-rater annotations.
- Do not re-litigate Phase 3 Q1 (coherence reframe) or Q2 (corpus
  decision rule) — both resolved and committed.
- Do not implement against
  `docs/PHASE_3_DESIGN_CLARIFYING_QUESTIONS_ARCHIVED.md` — superseded.
