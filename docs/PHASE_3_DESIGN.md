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

**Mandatory pre-experiment validation: the retrieval ablation.**
Before any full Phase 3 run, run a no-retrieval-vs-retrieval ablation
on a ~5-PR subset, single-agent only. The ablation must confirm that
retrieval improves single-agent recall by a margin that is (a)
positive and (b) similar in size to its effect on multi-agent on the
same subset. This is a gating check, not an optional extra:

- If retrieval helps both arms by a similar margin, retrieval is a
  legitimate held-constant input and the architectural comparison is
  clean.
- If retrieval helps one arm substantially more than the other, the
  retrieval component is interacting with the architecture and the
  full-experiment attribution ("arbiter adds discrimination") is
  contaminated. The design must be revised before proceeding —
  e.g. by simplifying to option (b) (touched files only) or by
  characterizing the interaction explicitly.

The ablation result is logged and reported in PHASE_3_SUMMARY.md
regardless of outcome. Skipping it, or running the full experiment
before it passes, invalidates the architectural claim.

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
and line range that supports the claim ("convention X in
`auth/handler.py:42`"). The validator is the load-bearing
adversarial-robustness mechanism — it must bound how much the critic
can assert without evidence. Three validator strictness levels:

- **(a1) Existence only.** The cited path exists at the PR's base
  commit and the line range is within the file's length. Cheap,
  deterministic, no model call. But weak: the critic can point at
  any real file and the validator passes. A coherence-violation
  with a real-but-irrelevant pointer survives.
- **(a2) Verbatim substring.** (a1) plus: the cited code contains a
  token or symbol the finding's description mentions verbatim
  (direct analog of Phase 2's spec_quote substring match). Cheap,
  deterministic, strongly adversarially robust. But likely too
  strict for coherence — many real coherence claims are about
  *patterns* ("this layer never imports from `db/` directly"),
  not specific tokens. A correct finding whose description
  paraphrases the pattern would fail (a2) and be wrongly downgraded.
- **(a3) Path-exists + LLM-judged description match.** (a1) plus: a
  separate LLM-judge call confirms the cited code semantically
  supports the finding's description (the code at the pointer is
  genuinely an instance of the convention/pattern/duplicate the
  finding claims). Not deterministic; costs a model call per
  pointer; but matches the actual shape of coherence evidence,
  which is semantic rather than lexical.

**Recommendation for review: (a3).** (a1) is too weak to bound the
critic — it's the no-validator case in disguise. (a2) imports
Phase 2's exact mechanism but Phase 2's mechanism worked because
spec violations *are* lexical (a spec clause is literal text);
coherence evidence is not. (a3) is the right shape for the domain.
Its cost is one LLM-judge call per coherence-violation finding, and
its non-determinism is itself a calibration target — see the
matcher-calibration section, which covers the same judge-reliability
problem.

The (a3) judge is structurally identical to the finding-to-comment
matcher in design question 5. Both are LLM-judged semantic
equivalence calls. They should share a calibration protocol; do not
treat them as two unrelated components.

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

**Prose-quality confound — and why arm-label blinding does not
fix it.** Blinding hides *which arm* produced a finding, but it
does not hide *stylistic tells* that correlate with arm. The
multi-agent pipeline runs an extra arbiter pass; its findings may
be systematically longer, more hedged, more thoroughly justified,
or simply better-written than single-agent findings — and a senior
rater, even fully blinded to arm labels, will rate a well-argued
finding "valid" more readily than a terse one making the identical
substantive point. That biases the residual rating toward whichever
arm writes better prose, which is not the architectural property
under test. Two mitigations, pick one at design review:

- **(a) Canonicalize findings before rating.** Strip each finding
  to a normalized form before it reaches the rater: a fixed-length
  description, the `finding_type`, the `evidence_pointer`, the
  dimension. A separate LLM-rewrite pass rewrites every finding —
  both arms — into one house style, removing length and
  rhetoric as signals. Risk: the rewrite pass can itself drop or
  distort substance; it must be validated (does the rewritten
  finding still make the same claim? — another LLM-judge call,
  another calibration target).
- **(b) Paired rating.** When single-agent and multi-agent both
  produce a finding about the same underlying issue (matched via
  the same matcher used for maintainer comments), the rater sees
  the pair together and rates them relative to each other, not on
  an absolute scale. This neutralizes prose quality because both
  members of the pair are rated in the same context. Risk: only
  works for findings that *both* arms produced; the
  architecturally-interesting case (multi-agent found it,
  single-agent did not) has no pair, so paired rating must fall
  back to (a)-style canonicalization for the unpaired residual.

Recommendation for review: **(a) canonicalization as the default,
because the unpaired residual — multi-agent-only findings — is
exactly the population the Phase 3 result hinges on, and (b)
cannot cover it.** Use (b) additionally on the paired subset as a
cross-check: if canonicalized absolute ratings and paired relative
ratings disagree on the paired subset, the canonicalization is
leaking prose signal and must be fixed before the residual ratings
are trusted.

### 6. Variance and sample size

Phase 2's lesson: small-n single-seed produces overfit conclusions.

**Sample size.** Phase 1 was small (single-digit PRs). Phase 3 for
variance reasons needs ≥ 30 PRs to discriminate effect sizes near
Phase 1's. Target ~40 PRs from a single repo (see below).

**Seeds per arm.** Phase 2's 3 seeds was load-bearing. Phase 3 should
match. Two arms × 3 seeds × 40 PRs = 240 reviewer-runs total per
experiment.

**Repo scope — committed: single repo for initial Phase 3.** Single
repo controls convention variance; multi-repo tests generalization
but introduces repo-as-confound (some repos are more amenable to
coherence review than others; a 2-repo split with 1 favorable repo
would produce a misleading aggregate). The initial Phase 3 question
is *does the coherence effect exist at all* — a structural
existence claim. That question is answered cleanest on a single
repo where conventions are uniform and can be fully characterized
as part of corpus annotation. Cross-repo generalization is a
genuine follow-up question but it is **Phase 3.1, not Phase 3**:
running it before the existence claim is settled spends corpus
budget hedging a question that only matters if the effect exists.

Repo-selection criteria for the single repo (settle at design
review): active maintainership with substantive review culture
(so maintainer comments are dense enough to be useful ground
truth); a codebase large enough that cross-file coherence is a
real concern (cross-file synthesis is the discrimination axis —
see design question 2); a license permitting corpus
redistribution; and a domain the senior annotator can rate
competently. A mid-size, well-reviewed library is the archetype;
a sprawling application monorepo or a trivial single-file utility
are both poor fits.

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

## Matcher calibration — load-bearing methodology

Phase 3 depends on LLM-judged semantic-equivalence calls in at least
three places:

1. **Finding ↔ maintainer-comment matching** (design question 5).
   Decides whether a reviewer finding "counts as" surfacing a
   maintainer comment. Drives the F1 primary metric directly.
2. **`evidence_pointer` validation** (design question 4, option a3).
   Decides whether the code at a cited pointer genuinely supports a
   coherence-violation claim. Drives the schema's
   adversarial-robustness property.
3. **Finding ↔ finding pairing** (design question 5, prose mitigation
   b). Decides whether single-agent and multi-agent produced "the
   same" finding for paired rating.

All three are the same operation: an LLM judging whether two
natural-language artifacts make the same claim. **This judge is not
a neutral utility — it is a measurement instrument, and an
uncalibrated instrument invalidates every number downstream of it.**
A matcher that is too lenient inflates recall (spurious matches make
both arms look like they found everything); too strict deflates it
(real matches missed, residual set bloated, senior-rating cost
balloons). Either way the architectural comparison is corrupted, and
because the corruption is systematic it will not show up as seed
variance — both arms are scored by the same bad instrument, so the
*delta* between arms can be silently wrong without any noise signal
to flag it. This is the Phase 2 lesson (an unvalidated component
produces confidently-wrong aggregates) applied to the matcher.

Treat matcher calibration as a pre-experiment deliverable with the
same status as the corpus itself:

**Calibration set.** Before any Phase 3 run, hand-label a calibration
set of ~150-200 candidate pairs spanning all three matcher uses:
finding/comment pairs, pointer/description pairs, finding/finding
pairs. Each pair is labeled match / no-match / debatable by a human
(the senior annotator, or a second annotator — see below). The set
must include hard negatives: pairs that are topically similar but
make different claims ("this should be extracted" vs "this is
duplicated" — related, not the same), and hard positives: pairs that
make the same claim in very different words.

**Calibration metric.** Run the LLM matcher against the calibration
set and report precision, recall, and Cohen's κ against the human
labels. Pre-register a threshold: e.g. κ ≥ 0.7 against human labels,
with neither precision nor recall below 0.8. The matcher prompt and
model are tuned against the calibration set *only* — never against
experiment data — and frozen before runs. If the threshold cannot
be met, the matcher design is wrong and the experiment does not
proceed; this is a hard gate, like the retrieval ablation.

**Inter-annotator agreement on the calibration set itself.** The
human labels are themselves a judgment. Have two annotators
independently label a ~40-pair subset and report their κ. If the
humans cannot agree (κ < 0.6), "same claim" is not crisply defined
and the matcher *cannot* be calibrated against an incoherent target
— the operational definition of a match must be tightened (a written
rubric: what makes two coherence claims "the same") before either
the humans or the LLM are scored.

**Match-decision logging.** Every matcher call in the live
experiment logs its inputs, its verdict, and its confidence/rationale.
A post-hoc audit samples ~30 live match decisions per arm and checks
them against a human — a drift check confirming the frozen matcher
behaves on experiment data the way it did on the calibration set.
Reported in PHASE_3_SUMMARY.md.

**Shared instrument, shared calibration.** The three matcher uses
share an underlying judge; they should share the calibration
protocol and, where the prompt allows, the implementation. They do
*not* share a threshold — pointer-validation can tolerate a
different precision/recall balance than finding/comment matching —
but each threshold is pre-registered and justified against the
calibration set, not picked during the run.

## Pre-registration constraints to lock in before runs

These must be settled before any Phase 3 run:

- **Primary metric chosen and operationalized.** Likely F1 on
  coherence findings vs maintainer comments, with senior-reviewer
  rating filling in for the residual set.
- **Coherence dimensions enumerated.** 3-4 specific dimensions, with
  the rubric for each.
- **Schema adaptation specified.** `evidence_pointer` validator
  per option a3 (path existence + line-range bounds + LLM-judged
  description match), with the judge threshold pre-registered
  against the calibration set. `finding_type` enum locked. Render
  rules for each type.
- **Matcher calibrated and frozen.** Calibration set hand-labeled;
  matcher precision/recall/κ meets the pre-registered threshold;
  inter-annotator κ on the calibration set itself meets its
  threshold; matcher prompt + model frozen. Hard gate — see the
  matcher-calibration section.
- **Retrieval ablation passed.** No-retrieval-vs-retrieval ablation
  on a ~5-PR subset confirms retrieval helps both arms by a similar
  margin. Hard gate — see design question 3.
- **Variance protocol locked.** Seeds, sample size, noise-floor
  estimation procedure. Pre-register the single-agent-only baseline
  run before multi-agent runs (matches Phase 2's sequential
  discipline).
- **Failure-mode hypotheses pre-registered.** What "multi-agent
  helps" and "multi-agent doesn't help" look like in data, with
  effect-size thresholds.
- **Senior-reviewer protocol.** Rubric, blinding procedure,
  prose-quality mitigation (canonicalization), inter-rater
  calibration if more than one rater.
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
  set size; senior-reviewer hours required) and prose-quality
  mitigation chosen.
- Sample size and variance protocol (6) committed.
- Matcher-calibration protocol accepted and the calibration-set
  authorship costed.
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

## Deferred: mutual-triage variant

Phase 1's iter3 + iter4 introduced a mutual-triage step — two critic
voices voting KEEP/DROP on each finding before it ships — to fix the
arbiter over-rotation failure mode for correctness findings. A natural
question is whether mutual triage transfers to coherence review.

**This is explicitly deferred, not an open question for review.** It
is deferred to Phase 3.1 — a follow-up conditional on Phase 3's base
result — for two reasons:

1. **It is downstream of the existence question.** Mutual triage is a
   *fix* for a *failure mode* (over-rotation). Phase 3 has not yet
   established that multi-agent coherence review has that failure
   mode, or any architectural effect at all. Designing a fix before
   the base effect is measured repeats the iter1 mistake of building
   on a single observation. If Phase 3 finds multi-agent helps on
   coherence AND exhibits over-rotation, mutual triage becomes a
   well-motivated Phase 3.1 experiment with a real failure to design
   against.
2. **It doubles the experiment.** Mutual triage is a third arm.
   Three arms × 3 seeds × 40 PRs is 360 reviewer-runs plus the triage
   passes — a ~50% cost increase to hedge a question that only
   matters if the two-arm result comes back positive. Spend the
   corpus budget on the existence claim first.

Phase 3 ships two arms (single-agent, reviewer + arbiter). Mutual
triage is named here so the deferral is on the record, not so it is
on the Phase 3 critical path.

## Open questions for the reviewer of this doc

The reviewer of this design (the human, not the agent) should settle.
The doc has made recommendations on all six numbered design questions;
these two are the genuinely unresolved calls where the doc does not
take a position:

- **Reframe scope.** Is coherence-dimension review at scale the
  right Phase 3, or is there a third option better than both
  clarifying-questions and coherence? The strongest alternative is
  adversarial multi-agent — one critic plays defense, one plays
  offense, on real PRs — which tests a different architectural
  property (productive disagreement) rather than coherence as a
  dimension. The doc recommends coherence but does not foreclose
  this.
- **Corpus path.** Is option (d) — real PRs + maintainer comments +
  spot senior annotations — the right primary path, or is the
  maintainer-comment-recall ceiling too low to discriminate the
  arms? If a pilot on ~5 PRs shows maintainer comments cover too
  few of the issues a senior annotator flags, fall back to (c)
  gold-standard annotation at smaller N. This is the highest-risk
  single decision in the design; recommend resolving it with a
  5-PR pilot annotation before committing the full corpus budget.

(Resolved in-doc, no longer open: code-generation carryover — clean
break from the writer-loop, no carryover; repo scope — single repo
for initial Phase 3, see design question 6; `evidence_pointer`
strictness — option a3, path + LLM-judged description match, see
design question 4; mutual-triage variant — deferred to Phase 3.1,
see above.)

## Suggested timeline (no commitment)

Design review → finalize 6 design choices → corpus authorship
(highest cost; bounded above by senior-reviewer availability for
the spot-annotation subset) → infrastructure (reviewer/arbiter
modules with `evidence_pointer` validator; RAG component; matcher
for maintainer-comments-vs-findings; senior-rating tool) → matcher
calibration + retrieval ablation (both hard gates) →
pre-registration → runs → writeup. Realistic 6-10 weeks elapsed
for one researcher; corpus authorship, senior-annotation, and
matcher calibration are the long poles.

## Deliverables when Phase 3 implementation completes

- `docs/PHASE_3_HANDOFF.md` — implementation brief (this doc's
  successor, written after design review).
- `phase3_corpus/` — PR snapshots + maintainer comments +
  spot-annotation subset + per-repo convention summaries.
- `agents/reviewer_coherence.py`, `agents/arbiter_coherence.py` —
  reviewer + arbiter with `evidence_pointer` validator (a3).
- `agents/retrieval.py` — RAG component, fixed across arms.
- `eval/match_findings.py` — LLM-judged matcher (shared by
  finding/comment matching, `evidence_pointer` a3 validation, and
  finding/finding pairing).
- `results/phase3/matcher_calibration.md` — calibration set,
  precision/recall/κ, inter-annotator κ, frozen matcher config.
- `results/phase3/retrieval_ablation.md` — ablation result (hard gate).
- `eval/senior_rating_tool.py` — blinded rating interface with
  finding canonicalization.
- `results/phase3/phase3_preregistration.md` — pre-registration.
- `results/phase3/<arm>/seed<N>/<pr_id>.json` — per-run data.
- `PHASE_3_SUMMARY.md` — writeup, headline finding first regardless
  of direction.
