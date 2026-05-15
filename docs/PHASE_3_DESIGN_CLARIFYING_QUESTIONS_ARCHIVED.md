# Phase 3 design — clarifying-question architecture (ARCHIVED)

> **SUPERSEDED 2026-05-15.** This design framed Phase 3 as a
> clarifying-question architecture closing the underspec gap measured
> in Phase 2. On review it was rejected on three grounds:
>
> 1. The "underspec gap" is a Phase 2 corpus artifact — Phase 2's
>    narrow definition of underspec ("test-discriminating binary
>    ambiguity") doesn't map to ambiguity in real PR review.
> 2. Clarifying-question architecture is established in the
>    literature; running it on a constructed underspec corpus would
>    measure how much it helps on that corpus, not produce a
>    structural finding.
> 3. The pr-arbiter project's original target was PR review (Phase 1).
>    Phase 2 was a useful detour to test generalization to code
>    generation, but the result (weak transfer, ~2 tasks across 39
>    runs) doesn't justify continuing in the writer-loop direction.
>
> Superseded by `docs/PHASE_3_DESIGN.md` (coherence-dimension review
> at scale on real PRs).
>
> Preserved here for historical reference. Do not implement against
> this document.

Status: **design draft**, not implementation brief. Open to revision
before any runs.

This doc is intentionally standalone. It does not assume Phase 2
context beyond the one-paragraph motivation; it does not commit to a
specific oracle or corpus until the design is reviewed.

## Research question

**Can a code-generation agent recognize when it should ask a clarifying
question rather than guess on spec ambiguity, and does a bounded oracle
("you can ask N yes/no questions") close the underspec convergence gap
that Phase 2 established is dominated by writer behavior?**

This is a different research question than Phase 2 asked. Phase 2 was
*does multi-agent critique add value over single-agent on code
generation?* — answered: directionally yes, with bounded effect size
(~2 tasks across 39 runs). Phase 3 is *can the agent distinguish
guessable from un-guessable situations, and act on the distinction by
acquiring information instead of guessing?*

The shift is from **routing existing information** (Phase 2: same
spec, same tests, different critic configurations) to **acquiring new
information** (Phase 3: spec + bounded oracle access).

## Why this is the right Phase 3

Phase 2 established three constraints that point at clarifying
questions as the only un-tested intervention:

1. **Critic architecture is well-calibrated under the typed schema.**
   0 contamination across 551 findings in iter3. The critic side has
   no remaining design pressure that hasn't been tested.
2. **Underspec convergence does not exceed 0.5 median in any tested
   arm.** Six prompt configurations, two underspec tasks, no
   architecture closes the gap.
3. **Writer behavior dominates underspec outcomes.** iter3 H2 showed
   the writer's reasoning about its own trajectory is the load-bearing
   variable, but the intervention that helps on one underspec failure
   mode (task_013) hurts on another (task_012).

Clarifying-question architecture is the **only intervention that adds
information** rather than reshuffling existing signal. The 0.5 median
ceiling exists because the writer must guess on truly ambiguous specs
with no path to resolve the ambiguity. A bounded oracle breaks that
ceiling — or fails to, in which case the underspec gap has a different
explanation than information availability.

## Six open design questions

These are the load-bearing decisions. The doc lays out options and
tradeoffs without picking — picking happens in design review.

### 1. Oracle design

The oracle is the entity the writer asks. Four options:

**(a) Human-in-loop.** Highest fidelity (real spec author can give
nuanced answers); lowest scalability (one human per task per run, no
batching, expensive to redo for variance).

**(b) Pre-authored "spec author" responses.** The corpus author writes
a Q&A bank per task ahead of time: every plausible question and its
answer. Scalable (one-time cost), reproducible across seeds. Risk: the
author anticipates the writer's questions and the writer's job becomes
"phrase your question to match a Q&A entry." Overfits to what the
author imagined.

**(c) Second LLM playing spec-author with access to the test suite.**
The oracle is an LLM (different model or same model with different
prompt) that has been given the spec, the test suite, and instructions
to answer yes/no questions consistent with both. Most adversarially
interesting: the oracle can answer any question the writer phrases.
Risk: test-suite access means the oracle could leak ground truth if
not carefully bounded (e.g. by enforcing yes/no answers only and
preventing the oracle from quoting tests).

**(d) Structured ambiguity tags in the spec itself.** The corpus
author marks ambiguous clauses in the spec (e.g.
`<ambig id="date-order">US or European date order?</ambig>`). The
writer can resolve a tag by querying it, and the spec author specifies
the answer per tag. Cheapest, but trivializes the question-asking
*decision* — the writer just queries every tag. Loses the "recognize
ambiguity" property.

**Tradeoff axis:** fidelity ↔ scalability ↔ trivialization-risk. (a)
maxes fidelity, loses scalability. (b)/(c) balance both with different
oracle-leakage profiles. (d) maxes scalability, loses the recognition
property.

**Recommendation to consider in review:** (c) with hard constraints on
the oracle prompt (yes/no answers only; cannot quote tests; cannot
reveal specific input/output pairs). This is the interesting
adversarial design and the only one that scales while preserving the
recognize-then-ask property.

### 2. Question budget

Three options: 0, 1, unbounded.

- **0 questions** is the Phase 2 baseline (already measured).
- **1 yes/no question per task** is the strongest design constraint:
  forces the writer to pick the *most* ambiguous point. If 1 question
  is enough to close the underspec gap, the gap is genuinely about
  one binary choice per task.
- **N questions (N small, e.g. 3)** lets the writer explore. Risk of
  degenerating to "ask everything."
- **Unbounded** probably degenerates to "writer asks for the tests"
  or near-equivalent. Not interesting.

The interesting comparison is **0 vs 1**. If 1 question doesn't move
the underspec rate substantially over 0, the underspec problem has a
different shape than "writer can't ask." If 1 question moves it
substantially (e.g. 0.5 → 0.8 median), the binary-resolution
hypothesis holds and the architecture is validated. N > 1 is a
follow-up if 1 is insufficient but moves in the right direction.

**Recommendation to consider in review:** primary comparison is
**0-question (Phase 2 baseline) vs 1-question**. Add **3-question** as
a secondary comparison only if 1-question is insufficient.

### 3. Corpus

**Phase 2's 2-of-13 underspec slice was the bottleneck.** Phase 3
should have ≥ 20 underspec tasks. Two options:

**(a) Extend phase2_corpus/ with new underspec tasks.** Keep the same
manifest format, add tasks 014-040. Total corpus ~30-40 tasks with
majority underspec. Preserves comparability with Phase 2.

**(b) Build a new phase3_corpus/.** Same task structure (spec.md,
tests.py, solution.py) but designed from scratch for clarifying-question
discrimination. Each task spec has a specific ambiguity the test suite
resolves one way. The Q&A bank or oracle prompt is the new artifact.

Either way the corpus construction is the dominant cost of Phase 3.
Estimate **2-4 hours per underspec task** for hand-authoring spec +
tests + reference solution + (if not using oracle (c)) Q&A bank or
ambiguity tags. 20 tasks = 40-80 hours.

**Recommendation to consider in review:** (a) with target N = 20
underspec tasks (Phase 2's 2 + 18 new). Preserves comparability and
keeps the manifest format. Half the new tasks should have a single
binary ambiguity (testing 1-question sufficiency); half should have
multiple ambiguities (testing multi-question and recognition-of-which).

### 4. What counts as a "good" question

The writer's question-asking decision should be evaluable independent
of whether the writer converges. Two reasons:

- A writer that asks a useless question and then guesses correctly
  isn't validating the architecture.
- A writer that asks a good question and then ignores the answer is a
  different failure mode than asking a bad question.

Candidate question-quality measures:

- **Reduces ambiguity space.** The spec has N plausible interpretations
  pre-question; the answer rules out ≥ 1. Operationalize as: the
  pre-authored Q&A bank has a finite set of "useful" questions; the
  writer's question matches one of them (LLM-judged similarity).
- **Targets a test-discriminating ambiguity.** The question's resolution
  affects which interpretation passes the tests. Operationalize: the
  Q&A bank tags which questions are test-relevant; non-tagged questions
  are scored 0 regardless of how well-formed they are.
- **Yes/no answerable.** Open-ended questions are out of bounds by
  design (oracle answers yes/no only). Operationalize: the oracle
  refuses non-binary questions and the writer must reformulate.

**Pre-registration constraint:** question quality must be scored on
the question alone, not on the downstream outcome. The same question
should get the same quality score regardless of whether the writer
converges. Otherwise the metric measures "lucky question" not "good
question."

### 5. Architectural placement

Two options:

**(a) Writer asks.** The writer decides when to ask, what to ask, and
incorporates the answer into its next attempt. Natural design;
matches the Phase 2 writer-loop structure.

**(b) Reviewer/arbiter asks on the writer's behalf.** The typed
schema already has critics flagging `spec-interpretation` findings.
The reviewer could be extended to *promote* a spec-interpretation
finding into a question to the oracle. The writer never directly
queries.

Phase 2 evidence is ambiguous on which is right:

- The typed schema validated that critics correctly identify
  spec-interpretations (0 contamination). This is evidence (b) might
  work: the critic-asks-clarification path reuses a calibrated
  component.
- But: arm F's task_013 win showed the *writer* can act on critic
  findings effectively when given the right context. (b) would still
  need the writer to incorporate the answer. So (b) ≠ less writer
  work.

**Recommendation to consider in review:** (a) for the primary
experiment (simpler design, clearer attribution of question-asking to
the writer's reasoning). (b) as a follow-up if (a) succeeds.

### 6. Comparison arms

Phase 3's writer-alone baseline cannot be the literal Phase 2 arm A:

- If iter3 H2 validates that pass-count ranking helps (it didn't pass
  pre-reg but had a strong concentrated effect), the Phase 3 baseline
  should include ranking. Otherwise Phase 3 is testing
  clarifying-questions against a strawman writer.

Proposed Phase 3 comparison arms:

- **G** — best Phase 2 writer config (typed schema + ranking, no
  iter2 prompt, i.e. arm F) + 0 questions. The Phase 3 baseline.
- **H** — G + 1 yes/no question per task.
- **I** — G + 3 yes/no questions per task (if H succeeds).
- (J — reviewer-asks variant, if H succeeds.)

Pre-register arm G's underspec rate on the Phase 3 corpus before
running H. Otherwise G's number is contaminated by the corpus changes
relative to Phase 2.

## Pre-registration constraints to bake in

These are the lock-in points that must be settled before Phase 3 runs:

- **Primary metric: underspec convergence rate.** Defined as: fraction
  of underspec tasks converged in ≤ 3 iters, across all seeds.
- **Non-underspec convergence must not regress vs Phase 2 best arm**
  on the comparable subset of corpus (the 11 non-underspec Phase 2
  tasks, if (a) corpus extension). Question-asking on non-underspec
  tasks is a failure mode (the writer asks when it shouldn't).
- **Question-asking rate, pre-registered as a range.** E.g. "between
  60% and 95% of underspec tasks should ask a question; outside that
  range is suspect (either the writer doesn't recognize ambiguity or
  it asks indiscriminately)." Optimizing this post-hoc is forbidden.
- **Oracle response policy locked.** The Q&A bank / oracle prompt is
  finalized before runs. No retroactive "the oracle would have
  answered X." All oracle interactions logged.
- **Strict success criterion for "Phase 3 succeeds."** Pre-register:
  arm H underspec convergence rate ≥ arm G + 0.2 (i.e. closes at
  least 40% of the [0, 1] gap from Phase 2's 0.5 median). Smaller
  improvements are suggestive but not confirmation.

## Success criteria for the design (what makes this doc ready to implement)

This doc is ready to implement against when:

- One oracle option (1) is selected with explicit rationale.
- Question budget (2) is locked at 0 vs 1 (and optionally 3).
- Corpus plan (3) has committed task counts and authorship cost
  estimate.
- Question-quality metric (4) is operationalized into a single rubric.
- Architectural placement (5) is chosen for the primary experiment.
- Comparison arms (6) are listed with Phase 2 carryover settings.
- Pre-registration constraints are locked into a draft
  `results/phase3/phase3_preregistration.md` template ready to fill
  in.

## What this design doc is NOT

- **Not an implementation brief.** Code design comes after design
  review.
- **Not committing to a specific oracle.** Recommendations are listed
  for review; the design review picks one with rationale.
- **Not estimating implementation cost in detail.** The corpus
  expansion dominates and needs scoping separately once the corpus
  plan (3) is selected.
- **Not promising a timeline.** Design first; iteration after.

## Open questions for review

The reviewer's job on this doc is to settle the six design questions
and identify any seventh that I missed. Specific questions for
review:

- Is oracle option (c) (LLM-as-spec-author with test access) too risky
  on oracle-leakage even with hard prompt constraints? If yes,
  fallback to (b) pre-authored Q&A with what mitigation against
  author-overfit?
- Is the underspec-only corpus expansion (option a) the right scope,
  or does Phase 3 need both underspec and a fresh non-underspec
  control to test the "writer asks when it shouldn't" failure mode?
- Should the 0 vs 1 question budget comparison include a *forced ask*
  arm where the writer must always ask exactly one question? This
  decouples the "recognize ambiguity" decision from the "use the
  answer" decision.
- Phase 2 arm F's task_013 3/3 result might mean ranking is enough
  for some underspec tasks; Phase 3 should report whether the
  improvement from clarifying-questions stacks with ranking or
  cannibalizes it.

## Suggested timeline (no commitment)

Design review → finalize 6 design choices → corpus extension (highest
cost, ~40-80 hours) → infrastructure (oracle, question budget,
logging) → pre-registration → runs → writeup. Realistic 4-6 weeks of
elapsed time for one researcher; corpus authorship is the long pole.

## Related work that would inform implementation

(Not surveyed here; would inform implementation but not the design
decisions above.) Self-asking / clarifying-question literature in the
instruction-following and agent-research lines. Specifically: research
on when models should defer to humans vs proceed, and on
disambiguation-via-question vs disambiguation-via-multi-shot.

## Deliverables when Phase 3 implementation completes

- `docs/PHASE_3_HANDOFF.md` — implementation brief (this doc's
  successor)
- `phase3_corpus/` (or extended `phase2_corpus/`) — task set
- `agents/oracle.py` — oracle implementation per chosen option
- `agents/writer.py` extension — question-asking pathway
- `results/phase3/phase3_preregistration.md` — pre-registration
- `results/phase3/<arm>/seed<N>/<task>.json` — per-run data
- `PHASE_3_SUMMARY.md` — writeup
