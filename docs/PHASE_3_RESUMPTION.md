# Phase 3 — resumption point

Written 2026-05-15 at the Phase 3 checkpoint. This document is for
the future-you who comes back to pr-arbiter after the pause. Read it
first.

## Status: paused

Phase 3 design is complete and ratified. Implementation has not
started and should not start yet. Phase 3 is paused on a single hard
dependency: a **senior-annotator pilot** that requires senior-reviewer
time the project lead does not have right now.

The project lead is the available senior rater. There is no external
annotator — that path was evaluated and rejected. So the pilot waits
until the lead has the 8-15 hours it needs (see "time to complete"
below).

Everything that could be closed without the pilot has been closed.
The project is at a clean resumption point.

## Exact next action when resuming

Run the senior-annotator 5-PR pilot. The protocol is specified in
`docs/PHASE_3_DESIGN_REVIEW.md` under "The senior-annotator 5-PR
pilot — protocol". The project lead may also commit a standalone
`docs/PHASE_3_PILOT_PROTOCOL.md` expanding that sketch; if it exists,
follow it — it supersedes the inline protocol. If it does not exist,
the inline protocol in `PHASE_3_DESIGN_REVIEW.md` is sufficient to
run the pilot.

In one line: a senior reviewer independently annotates every
coherence issue on 5 reviewed pydantic PRs (#13070, #13133, #13129 +
2 more with ≥3 review comments), then the maintainer's actual review
comments are matched against those annotations to produce a recall
number.

That recall number fires the Q2 decision rule. Until it fires, the
corpus path is not decided and implementation cannot start.

## Decision points already committed

- **Q1 — reframe scope.** Phase 3 is coherence-dimension review.
  Adversarial multi-agent is a candidate Phase 4, not Phase 3.
  Resolved in `PHASE_3_DESIGN_REVIEW.md`.
- **Q2 — corpus path.** A pre-registered decision rule keyed on the
  senior-pilot recall number:
  - recall ≥ 60% → corpus option (d) as designed
  - recall 30–60% → option (d) with an enlarged senior-annotation
    subset (~20-25 PRs instead of ~10)
  - recall < 30% → fall back to option (c), gold-standard senior
    annotation at smaller N (~20 PRs fully annotated)
  Resolved in `PHASE_3_DESIGN_REVIEW.md`. The rule itself is locked;
  only the input number is pending.
- **Provisional repo:** pydantic. Largest cross-file coherence
  surface of the probed candidates; MIT license; Python domain.
- **Six design recommendations** (corpus, dimensions, reviewer
  input, schema adaptation, ground truth, variance) — all six
  accepted, ratification checklist appended to
  `docs/PHASE_3_DESIGN.md` under "Design recommendations:
  ratification". Each acceptance carries a dependency note; none was
  redirected.

## Decision points still open

- **The senior-pilot recall number.** The single missing input. It
  fires the Q2 decision rule and selects the corpus path. Nothing
  downstream can be decided without it.
- **The repo lock.** pydantic is provisional. The senior pilot runs
  on pydantic PRs; if nothing surfaces in the pilot to disqualify
  it, pydantic locks at that point. No open concern — just not yet
  formally locked.
- **`docs/PHASE_3_PILOT_PROTOCOL.md`.** The project lead intends to
  commit a standalone expanded pilot protocol. Until then the inline
  protocol in `PHASE_3_DESIGN_REVIEW.md` stands. Not a blocker.

No items from the PR #7 review were pushed back — the design-review
response was accepted as written. No smaller open items are
outstanding.

## Estimated time to complete the pilot when resumed

8-15 hours of senior-rater time:

- Annotation: 5 PRs × ~1-2 hours each for a thorough independent
  coherence annotation = 5-10 hours.
- Matching + recall computation: ~1-2 hours.
- Writing up the recall number and the qualitative note (are the
  issues maintainers miss systematically different) and seeding the
  matcher calibration set from the pilot annotations: ~2-3 hours.

This is senior-rater time specifically — it cannot be parallelized
to a junior or to an LLM (see "what NOT to do" below).

## What NOT to do when resuming

- **Do not skip the pilot to save time.** The corpus path is the
  load-bearing decision of Phase 3. The pilot is one measurement
  away from settling it. Skipping it means guessing the corpus
  path, and a wrong guess wastes the ~40-PR corpus authorship
  budget — far more than the 8-15 hours the pilot costs.
- **Do not have an LLM produce the senior-rater annotations.** The
  agent under test is an LLM reviewer. If an LLM generates the
  ground-truth annotations, the experiment measures the agent
  against itself and the Phase 3 result is circular and worthless.
  The annotations must come from a human senior reviewer.
- **Do not start the implementation brief (`PHASE_3_HANDOFF.md`)
  before the pilot.** The brief depends on the corpus path, the
  corpus path depends on the Q2 decision rule, the decision rule
  depends on the pilot recall number. Writing the brief first means
  rewriting it once the number comes in.
- **Do not re-litigate Q1 or Q2.** Both are resolved and committed.
  Resumption is execution, not redesign.

## Map of Phase 3 artifacts

- `docs/PHASE_3_DESIGN.md` — the design (coherence-dimension review),
  with the ratification checklist appended.
- `docs/PHASE_3_DESIGN_REVIEW.md` — Q1/Q2 resolutions + the
  senior-pilot protocol.
- `docs/PHASE_3_DESIGN_CLARIFYING_QUESTIONS_ARCHIVED.md` — superseded
  prior design; do not implement against it.
- `results/phase3/corpus_pilot.md` — the GitHub-data corpus probe
  (density low, content coherence-flavored, option d viable on
  content grounds).
- `docs/PHASE_3_RESUMPTION.md` — this document.

Phase 1 and Phase 2 are complete and merged; see `SUMMARY.md` and
`PHASE_2_FINAL.md`.
