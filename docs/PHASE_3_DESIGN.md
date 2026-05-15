# Phase 3 design — coherence-dimension review at scale

Status: **design draft**, not implementation brief. Open to revision
before any runs.

A prior Phase 3 design framed the work as a clarifying-question
architecture closing Phase 2's underspec gap. That framing was
rejected because the gap is a Phase 2 corpus artifact (its definition
of "underspec" doesn't map to PR review) and because
clarifying-question architecture is established in the literature.
See `docs/PHASE_3_DESIGN_CLARIFYING_QUESTIONS_ARCHIVED.md` for the
superseded design and the full reasoning. This doc is a fresh start.

## Research question

Phase 1 established that independent multi-agent review catches
correctness bugs single-agent misses — the `pr_009` XSS finding (see
[SUMMARY.md](../SUMMARY.md)) was caught by the arbiter across every
variant that produced it, and missed by single-agent across every
variant that didn't. Phase 2 showed that the same architectural property
extends weakly to code generation (~2 tasks across 39 runs under
variance; see [PHASE_2_FINAL.md](../PHASE_2_FINAL.md)).

Both results were on dimensions where the right answer is testable:
the XSS bug either fires or doesn't; the function either passes the
test suite or doesn't. **Real code review is dominated by a different
class of judgment** — the dimensions that don't have a unit test or a
crash trace to ground them. Senior reviewers comment on abstraction,
on whether the change belongs where it is, on convention alignment,
on test quality, on whether the diff is "doing too much." These
judgments are the ones that distinguish a good review from one that
just catches bugs.

**Phase 3 asks whether the multi-agent architectural property
extends to coherence-dimension review.** Specifically:

- Does multi-agent review surface coherence issues (abstraction,
  consistency, layer-appropriateness, convention alignment, test
  quality) that single-agent review misses?
- If yes, is the effect size comparable to, larger than, or smaller
  than the Phase 1 correctness-dimension effect?
- Do the Phase 2 failure modes (over-confidence on ambiguous calls,
  schema-fix neutralizing critic-induced noise) reappear here, or
  are they writer-loop-specific?

This is a structural research question about where the multi-agent
advantage lives. The hypothesis space includes **"multi-agent
doesn't help on coherence"** as a real, publishable outcome —
designing the experiment so that's discoverable is a primary
constraint.

## Why this reframe

Three reasons the project should turn back to PR review at scale:

1. **Project target.** pr-arbiter is named for PR review. Phase 1
   was the foundational claim; Phase 2 was a generalization probe.
   Phase 3 returning to PR review tests whether Phase 1's result
   was a planted-bug artifact or a property of the architecture.

2. **Dimension under-explored.** Phase 1's planted-bug corpus had
   no real way to measure coherence. Phase 2's HumanEval-shaped
   tasks had no surrounding codebase to be coherent with.
   Coherence is the dimension senior reviewers actually spend most
   of their attention on and the one neither phase could touch.

3. **Schema reuse pressure-test.** Phase 2's typed-finding schema
   (validator-checked `spec_quote`) is the most reusable artifact
   from the project so far. Whether it adapts cleanly to coherence
   findings (which don't have spec clauses to quote, but do have
   code locations to point at) is itself a contribution
   independent of the architectural claim.

## Six open design questions

These are the load-bearing decisions, in resolution order. The doc
lays out options and tradeoffs; final picks happen at design review.

### 1. Corpus

The corpus is the dominant design decision. Phase 1's planted-bug
approach won't work — you can't plant coherence issues the way you
plant XSS bugs. Phase 2's HumanEval-shaped approach won't work —
those tasks have no surrounding codebase to be coherent with.

**(a) Real PRs from open-source repos with maintainer labels.**
Mine PRs that have review comments tagged with coherence concerns
("this should live elsewhere," "we use X pattern for this
everywhere else," "consider extracting"). Ground truth is the
maintainer's review comments. Scalable; ecologically valid;
**known ceiling problem** — maintainer comments aren't a complete
coverage of issues. Many real coherence issues never get
commented because the reviewer was time-constrained, deferred, or
the maintainer didn't notice. This bounds (a)'s discrimination
power from above.

**(b) Real PRs with synthetic coherence violations introduced.**
Take clean merged PRs, introduce coherence issues programmatically
(rename a variable to violate convention, move logic to the wrong
layer, duplicate a utility that exists elsewhere in the codebase).
Phase 1's planted-bug methodology but for coherence. Reproducible
ground truth; **ecologically suspect** because real coherence
issues don't look like "I broke this on purpose" — they're the
product of a developer doing their best and not seeing a better
option.

**(c) Curated PR corpus with senior-reviewer annotations.** Have a
senior reviewer go through ~30-50 real PRs and annotate every
coherence issue they would flag, with severity and dimension.
Ground truth is the annotation. Highest fidelity; most expensive
(~1-2 hours per PR for a thorough annotation = 30-100 senior-hours
for one corpus); small sample.

**(d) Hybrid: real PRs + maintainer comments + spot annotations.**
Use (a) as the primary signal, supplement with (c)-style
annotations on a subset (~10 PRs) to estimate the
maintainer-comment-recall ceiling. Senior annotations also provide
the "finding not in any maintainer comment but rated valid"
category that's where the multi-agent property is most likely to
show up.

Tradeoff axis: ecological validity ↔ ground-truth completeness ↔
authorship cost. (a) is cheap and realistic but ceiling-bounded.
(b) is cheap and clean but artificial. (c) is gold-standard and
expensive. (d) gets you (a)'s scale with (c)'s discrimination on
the subset where it matters.

**Recommendation for review: (d).** Annotate ~10 PRs at the (c)
fidelity to bound the maintainer-comment ceiling and identify the
"multi-agent caught something maintainers missed" category.
Primary metric runs on the full (a) corpus of ~30-50 PRs.

**Logistics: how does the reviewer see the codebase context?**
This is a real design question, not a footnote. Real reviewers
have access to the repo. Phase 3 reviewers need at minimum the
touched files in full (not just the diff), and probably more.
See design question 3.

### 2. Coherence dimensions

"Coherence" is a bucket. The doc must enumerate which specific
dimensions are in scope. Candidate list:

- **Abstraction appropriateness** — is the change at the right
  level of abstraction, or paying complexity for a one-off case?
- **Convention alignment** — does the change follow patterns
  established elsewhere in the codebase?
- **Layer appropriateness** — is the logic in the right module,
  file, or layer, or leaking concerns across?
- **Test quality** — does the test test behavior or implementation?
  Coverage at the right granularity?
- **Duplication** — does this change duplicate something that
  exists elsewhere, or could the new code share an existing utility?
- **Naming and clarity** — are the names accurate, conventional,
  unambiguous?

Not all six are equally good candidates for Phase 3:

- **Dimensions that don't need cross-file synthesis** are unlikely
  to discriminate multi-agent vs single-agent. Naming, for example,
  can mostly be judged from the diff. Abstraction-within-a-function
  is local.
- **Dimensions that require synthesizing across the codebase** are
  where the architectural property might pay off. Layer
  appropriateness, convention alignment, and duplication all
  require the reviewer to compare the change against patterns
  elsewhere.

**Recommendation for review: convention alignment + layer
appropriateness + duplication.** These three require cross-file
synthesis, which is where a second independent reviewer might
catch what a first reviewer missed. Test quality is interesting
but the ground-truth comparison is harder (when is a test "the
right test"?). Abstraction and naming are weaker discriminators.

Drop to 3 dimensions for the initial Phase 3; expand to 4 if data
suggests the discrimination story is real and worth more
investment.

### 3. Reviewer/arbiter input

Phase 1 reviewers saw the PR diff. Phase 3 reviewers need more.

**(a) Diff only.** Same as Phase 1. Forces the reviewer to reason
from the change alone. Loses most coherence signal — a reviewer
can't flag "this duplicates X" without seeing X.

**(b) Diff + touched files in full.** Standard human reviewer
context. Captures local coherence (within touched files), misses
cross-file patterns (conventions established elsewhere).

**(c) Diff + touched files + RAG over the rest of the repo.** The
reviewer can pull in similar code, convention examples, related
utilities via retrieval. Most realistic; **introduces a confound** —
is the architecture winning, or is the retrieval doing the work?
If multi-agent's retrieval happens to surface something
single-agent's didn't, the attribution is ambiguous.

**(d) Diff + touched files + curated "codebase context" doc per
PR.** A human-authored summary of "things a reviewer would need to
know" — relevant conventions, similar code locations, layer
boundaries. Most experimentally controlled; **least scalable**
(authorship overhead per PR); introduces author bias (the context
doc primes the reviewer toward the issues the author thought to
include).

Tradeoff: realism ↔ experimental cleanliness.

The retrieval option (c) creates a real attribution problem. If
single-agent gets retrieval too, the two arms differ only in
whether arbiter runs — the retrieval is held constant. That's the
clean design. Both arms use the same retrieval, and the
architectural question is what the second independent pass adds on
top.

**Recommendation for review: (c) with retrieval held constant
across arms.** Both single-agent and multi-agent get the same RAG
component. Retrieval is a fixed input, not a varied condition.
Phase 3's architectural question is whether the arbiter adds
discrimination over the reviewer with the same context — this
matches Phase 1's setup conceptually (same input to both passes;
arbiter is the additional pass).

Alternative for review consideration: run a tiny "retrieval
ablation" (no retrieval vs retrieval) on a 5-PR subset to confirm
retrieval helps both arms equally. If retrieval helps one arm
more, attribution gets harder and the design needs revisiting.

### 4. Schema adaptation

Phase 2's typed-finding schema requires `spec_quote` on
`spec-violation` findings, validated as substring match against the
spec. Coherence findings don't have a spec clause to quote — they
have **a code location elsewhere in the repo** that supports the
claim ("convention X in `auth/handler.py:42`"; "duplicate of
`utils/format.py:18`").

Two changes to the schema, both substantive enough to deserve
design-doc treatment:

**(a) `evidence_pointer` field replacing `spec_quote`.** A
coherence-violation finding requires citing a specific file path
and line range that supports the claim. Validator rule: the path
must exist in the repo at the PR's base commit AND the line range
must be in range of the file's length. Optional stronger validator:
the cited code must contain a token/symbol the reviewer's
description mentions (verbatim substring, like Phase 2's spec_quote
match). The stronger validator is more adversarially robust but
may be too strict for real coherence claims that involve patterns
rather than specific tokens.

Open sub-question for review: is the verbatim-substring validator
viable for coherence pointers, or does it need to be looser
(e.g., the cited file is in the same module/directory as the
described pattern)?

**(b) `finding_type` enum extended.** Phase 2 had `spec-violation`
(quotable) vs `spec-interpretation` (judgment call). Phase 3
candidate:

- `coherence-violation` — there's a specific code location that
  supports the claim. `evidence_pointer` required.
- `coherence-judgment` — the reviewer is making an experienced
  taste call without a specific pointer ("this feels like it
  belongs in the service layer"). No pointer required.
- `correctness-finding` — preserves Phase 1's bug-catching as a
  separate category. Phase 3 isn't primarily about correctness but
  if the reviewer happens to spot a real bug, it should be reported
  in its own category.

The Phase 2 lesson — `coherence-judgment` findings should be
weighted lower than `coherence-violation` by downstream consumers,
because the validator can't bound the critic's confidence on them
— transfers directly. Whether to render judgment-type findings to
the human reviewer at all, or only the pointer-validated ones, is
a design choice. Phase 2 chose to show both with type tagging;
Phase 3 should do the same to preserve comparability.

### 5. Ground-truth comparison

How is a finding scored?

**(a) Recall against maintainer comments.** Reviewer findings
matched to maintainer comments via LLM-judged similarity. Score
is fraction of maintainer comments surfaced. Captures "did the
reviewer find what humans found." Bounded above by the
maintainer-comment-recall ceiling discussed in design question 1.

**(b) Precision against maintainer comments.** Same matching,
score is fraction of reviewer findings matching a maintainer
comment. Captures "is the reviewer producing real signal." Penalizes
findings that humans didn't comment on, including real issues
humans missed.

**(c) Senior-reviewer rating.** A senior reviewer rates each
finding (valid / invalid / debatable). Highest fidelity; expensive;
requires senior-hours per evaluation run. Doesn't scale to 50 PRs
× 3 seeds × 2 arms = 300 ratings per experiment.

**(d) F1 against maintainer comments PLUS senior-reviewer rating
on findings not matching any comment.** F1 captures the "found
what humans found" measure cheaply across all findings; senior
ratings only fire on the residual set (findings not matched to a
comment), which is where the architectural property could
plausibly differentiate arms.

**The interesting Phase 3 result would be reviewer findings that
maintainers MISSED but a senior reviewer rates as valid.** That's
the multi-agent architectural property worth measuring — surfacing
coherence issues humans didn't catch but should have. Only (d) can
find this. (a) and (b) bound the measurement from above and below;
(c) is the ideal but doesn't scale.

**Recommendation for review: (d).** Senior-reviewer rating fires
only on the residual; the maintainer-comment F1 covers the rest.
Cost is bounded by residual-set size (~10-30 ratings per arm-seed
combination if findings-not-matched are a small minority).

**Mandatory blinding constraint:** the senior reviewer must not
know which arm produced a finding when rating it. Otherwise the
rating can retroactively elevate multi-agent findings into "valid
coherence issues maintainers missed." Phase 3 result is only
meaningful if blinding is enforced procedurally (random shuffle of
findings across arms before sending to rater; arm-of-origin not
in the rater interface).

### 6. Variance and sample size

Phase 2's lesson: small-n single-seed produces overfit conclusions.

**Sample size.** Phase 1 was small (single-digit PRs). Phase 3 for
variance reasons needs ≥30 PRs to discriminate effect sizes near
Phase 1's. ~50 PRs gives more headroom on cross-repo generalization
if that's in scope.

**Seeds per arm.** Phase 2's 3 seeds was load-bearing. Phase 3 should
match. Two arms × 3 seeds × 50 PRs = 300 reviewer-runs total per
experiment.

**Single repo vs multiple repos.** Single repo controls for
convention variance but tests generalization weakly. Multiple repos
test generalization but introduce repo-as-confound (some repos may
be more amenable to coherence review than others).

Recommendation for review: **3-5 repos with ~10 PRs each.** Enough
to test generalization, few enough that per-repo conventions can be
characterized as part of the corpus annotation. Pre-register
per-repo expected effect-size variance; if multi-agent helps in
one repo and not others, that's a finding to report, not noise to
average over.

**Effect-size pre-registration.** Phase 2 established its noise
floor empirically (±2 tasks across 39 runs between arms A and B).
Phase 3 should do the same: run the single-agent baseline first on
the full corpus, then bound noise on coherence-recall via the seed
variance. The architectural claim (multi-agent helps on coherence)
needs to clear that noise floor by a pre-registered margin.

**Failure-mode pre-registration.** What does "multi-agent doesn't
help on coherence" look like in the data? Possibilities to
pre-register:

- Multi-agent finds the same maintainer-comment matches as
  single-agent within noise (recall flat).
- Multi-agent's extra findings (not in maintainer comments) are
  rated invalid by the senior reviewer (precision drops; no real
  discrimination).
- Multi-agent helps on one or two dimensions but not the others
  (specify which dimensions in advance).

Each of these has a different downstream implication; pre-registering
them prevents the iter1-style post-hoc narrative that Phase 2
caught.

## Pre-registration constraints to lock in before runs

These must be settled before any Phase 3 run:

- **Primary metric chosen and operationalized.** Likely F1 on
  coherence findings vs maintainer comments, with senior-reviewer
  rating filling in for the residual set.
- **Coherence dimensions enumerated.** 3-4 specific dimensions, with
  the rubric for each.
- **Schema adaptation specified.** `evidence_pointer` validator
  rules (path existence, line-range bounds, optional substring
  match). `finding_type` enum locked. Render rules for each type.
- **Variance protocol locked.** Seeds, sample size, noise-floor
  estimation procedure. Pre-register the single-agent-only baseline
  run before multi-agent runs (matches Phase 2's sequential
  discipline).
- **Failure-mode hypotheses pre-registered.** What "multi-agent
  helps" and "multi-agent doesn't help" look like in data, with
  effect-size thresholds.
- **Senior-reviewer protocol.** Rubric, blinding procedure,
  inter-rater calibration if more than one rater.
- **Honest framing.** A "multi-agent doesn't help on coherence"
  outcome must be publishable. The doc and the pre-registration
  must not be structured to produce a positive result either way.

## Success criteria for this design doc

The doc is ready to implement against when design review settles:

- Corpus option (1) selected with rationale and a path to acquire
  it (which repos, what scale, who does the annotations).
- Coherence dimensions (2) enumerated and prioritized (3-4 picked).
- Reviewer input strategy (3) chosen, with confound implications
  acknowledged.
- Schema adaptation (4) specified concretely (`evidence_pointer`
  validator rules; `finding_type` enum committed).
- Ground-truth comparison (5) selected with cost estimate (residual
  set size; senior-reviewer hours required).
- Sample size and variance protocol (6) committed.
- Pre-registration template draft exists at
  `results/phase3/phase3_preregistration.md` (template, not filled
  in — fill happens once corpus is in place).

## What this design doc is NOT

- Not an implementation brief. The implementation brief comes after
  design review and corpus scoping.
- Not committed to a corpus, schema, or metric until design review.
- Not a fork of the archived clarifying-question doc. Different
  research question, different methodology.
- Not promising effect sizes. "Multi-agent doesn't help on
  coherence" is in the hypothesis space and the design must let
  that outcome be discovered.

## Honest framing requirement

The previous Phase 3 design erred toward measurement of a known
architecture. This reframe is supposed to put a real structural claim
at risk — that the Phase 1 multi-agent advantage extends to
coherence.

Three constraints flow from this:

1. **Pre-register what "doesn't help" looks like.** Not "any positive
   effect counts." A pre-registered effect-size threshold tied to
   the empirically-bounded noise floor.
2. **Blind the senior reviewer.** The rater cannot know which arm
   produced a finding when rating it. Otherwise the rating measures
   "rater knew the architecture and was inclined to agree."
3. **Report unflattering results in the TL;DR.** Phase 2's iter1
   writeup buried the variance-fragility of its single-seed claims
   in paragraph 8. Phase 3 must report the headline finding in the
   TL;DR regardless of direction. If multi-agent doesn't help on
   coherence, that's the headline.

## Open questions for the reviewer of this doc

The reviewer of this design (the human, not the agent) should settle:

- **Reframe scope.** Is coherence-dimension review at scale the
  right Phase 3, or is there a third option that's better than
  both clarifying-questions and coherence? (E.g., adversarial
  multi-agent — one critic plays defense, one plays offense, on
  real PRs.)
- **Corpus path.** Is option (d) — real PRs + maintainer comments
  + spot senior annotations — the right primary path, or is the
  maintainer-comment-recall ceiling too low to discriminate? If
  too low, fall back to (c) gold-standard at smaller N.
- **Code-generation carryover.** Should Phase 3 include any
  code-generation tasks at all, or is the reframe a clean break
  from Phase 2's writer-loop? Default in this doc is **clean
  break**; revisit if there's an argument for carryover.
- **Repo scope.** 3-5 repos × ~10 PRs each, or single repo × ~50
  PRs? Single repo controls more; multi-repo tests generalization
  the project's headline ultimately needs.
- **Schema strictness.** Verbatim substring match for
  `evidence_pointer`, or looser "same directory" rule? Strict
  match is more adversarially robust (Phase 2's lesson); looser
  match is more realistic for coherence findings that involve
  patterns rather than specific tokens.
- **Architecture variants.** Should Phase 3 include a "mutual
  triage" variant (the Phase 1 iter3 + iter4 fix)? Phase 1 showed
  it helped on the over-rotation failure mode for correctness
  findings. Whether it transfers to coherence is its own question
  and adds an arm to the experiment.

## Suggested timeline (no commitment)

Design review → finalize 6 design choices → corpus authorship
(highest cost; bounded above by senior-reviewer availability for
the spot-annotation subset) → infrastructure (reviewer/arbiter
modules with `evidence_pointer` validator; RAG component; matcher
for maintainer-comments-vs-findings; senior-rating tool) →
pre-registration → runs → writeup. Realistic 6-10 weeks elapsed
for one researcher; corpus authorship and senior-annotation are the
long poles.

## Deliverables when Phase 3 implementation completes

- `docs/PHASE_3_HANDOFF.md` — implementation brief (this doc's
  successor, written after design review).
- `phase3_corpus/` — PR snapshots + maintainer comments +
  spot-annotation subset + per-repo convention summaries.
- `agents/reviewer_coherence.py`, `agents/arbiter_coherence.py` —
  reviewer + arbiter with `evidence_pointer` validator.
- `agents/retrieval.py` — RAG component, fixed across arms.
- `eval/match_findings.py` — finding-to-maintainer-comment matcher.
- `eval/senior_rating_tool.py` — blinded rating interface.
- `results/phase3/phase3_preregistration.md` — pre-registration.
- `results/phase3/<arm>/seed<N>/<pr_id>.json` — per-run data.
- `PHASE_3_SUMMARY.md` — writeup, headline finding first regardless
  of direction.
