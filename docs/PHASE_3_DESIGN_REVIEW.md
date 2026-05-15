# Phase 3 design review — response to the two open questions

Status: **agent recommendation, pending human ratification.**

`docs/PHASE_3_DESIGN.md` ends with two open questions explicitly
addressed to the human reviewer. This document gives a reasoned
position on both, so the human review is a ratify-or-redirect
decision rather than an open-ended one. It does not replace human
sign-off — scope decisions that commit weeks of corpus authorship
should be confirmed, not delegated.

Once ratified, the resolved decisions here fold into
`docs/PHASE_3_DESIGN.md` (or its successor `PHASE_3_HANDOFF.md`) and
this document is archived.

## Q1 — Reframe scope: coherence vs adversarial multi-agent

**Recommendation: coherence-dimension review. Confirmed, not
redirected.**

The design doc named one alternative worth considering: adversarial
multi-agent — one critic plays defense, one plays offense, on real
PRs. The reasoning for staying with coherence:

1. **Coherence is a dimension; adversarial is a mechanism.** Phase 1
   and Phase 2 both measured the multi-agent property on *testable*
   dimensions (correctness bugs fire or don't; functions pass tests
   or don't). Coherence is the dimension neither phase could touch —
   the judgment calls with no unit test to ground them. Adversarial
   multi-agent is a different *agent topology*, but it still has to
   be measured against *some* ground truth, and that ground truth is
   either correctness (Phase 1 territory, already done) or coherence
   (which is the reframe anyway). Adversarial framing without a new
   dimension just re-runs Phase 1's question with a different
   topology.

2. **Coherence puts a genuine structural claim at risk.** The
   unanswered question after Phase 1 + Phase 2 is: does the
   multi-agent advantage extend to non-testable judgment? That is a
   real claim that can fail. "Does an adversarial topology beat a
   reviewer+arbiter topology" is a tuning question, not a structural
   one.

3. **Mechanism variations come after the dimension question.** This
   is the same logic the design doc applied to deferring mutual
   triage: a mechanism variation is only worth running once the base
   dimensional effect is established. If Phase 3 shows coherence is a
   place multi-agent helps, adversarial multi-agent becomes a
   well-motivated **Phase 4** — testing whether a different topology
   amplifies the coherence effect. If Phase 3 shows multi-agent does
   not help on coherence, adversarial multi-agent is unlikely to
   rescue it and Phase 4 would pivot elsewhere.

**Decision: Phase 3 is coherence-dimension review. Adversarial
multi-agent is logged as a candidate Phase 4, contingent on a
positive Phase 3 coherence result.**

## Q2 — Corpus path: option (d) viable, or fall back to (c)?

**Recommendation: convert the open question into a pre-registered
decision rule keyed on one measurement. Provisionally commit to
option (d); the senior-annotator pilot supplies the number that
confirms or overrides it.**

The corpus pilot (`results/phase3/corpus_pilot.md`) already settled
the parts that GitHub data alone can settle:

- Content viability: **confirmed.** Real maintainer comments on
  mature Python repos are substantively coherence-flavored and map
  onto the design doc's dimensions.
- Density: **low but workable.** ~10% of merged PRs are reviewed
  inline; a ~40-PR reviewed corpus means scanning ~350-400 merged
  PRs. Mechanically feasible.
- Selection bias: **a corpus property to pre-register**, not a
  blocker — the arms share the corpus so the inter-arm delta stays
  valid.

The one number the pilot could not produce — because it needs a
senior annotator, not GitHub data — is the **maintainer-comment-recall
ceiling**: of all the coherence issues a senior reviewer flags on a
reviewed PR, what fraction did the maintainer actually comment on?

Rather than leave the corpus path "open," pre-register this decision
rule now, so the senior pilot is a measurement that plugs into a
committed rule:

| senior-pilot recall | corpus decision |
|---------------------|-----------------|
| **≥ 60%** | Proceed with option (d) as designed. Maintainer comments are a dense enough ground truth; the F1 primary metric is well-founded. |
| **30–60%** | Proceed with option (d), but enlarge the senior-annotation subset from ~10 PRs to ~20-25. The senior annotations patch the maintainer-comment ceiling on the residual; F1 is computed against the *union* of maintainer comments and senior annotations on the annotated subset, against maintainer comments alone on the rest. Cost: more senior-hours. |
| **< 30%** | Fall back to option (c): gold-standard senior annotation on a smaller corpus (~20 PRs fully annotated). Maintainer comments become a secondary signal, not the primary ground truth. The experiment shrinks but stays valid. |

This rule is itself a pre-registration commitment — it goes into
`results/phase3/phase3_preregistration.md` and is not revised after
the senior-pilot number comes in.

**Provisional repo: pydantic.** The pilot probed httpx and pydantic;
pydantic has the larger cross-file coherence surface (design question
2 identified cross-file synthesis as the discrimination axis), a
slightly higher review density, an MIT license, and a domain a
Python-competent senior annotator can rate. Lock at design review,
contingent on nothing surfacing in the senior pilot.

## The senior-annotator 5-PR pilot — protocol

This is the remaining hard human dependency. It cannot be run by an
agent: the agent is the thing under test, so it cannot also be the
ground-truth annotator. Protocol, so whoever runs it has no
ambiguity:

1. **PRs.** Draw 5 reviewed PRs from pydantic's reviewed ~10%. The
   corpus pilot surfaced #13070, #13133, #13129 as confirmed
   coherence-comment-bearing; pick 2 more with ≥ 3 review comments
   from the same era. Avoid PRs the agent reviewer has already seen
   in any pilot run.

2. **Annotation task.** The senior annotator reads each PR (diff +
   touched files + repo access) and independently writes down every
   coherence issue they would flag in a real review — before looking
   at the maintainer's actual comments. Each annotation: dimension
   (convention / layer / duplication — the design doc's three),
   severity, one-line description, evidence pointer.

3. **Measurement.** For each PR, match the maintainer's actual review
   comments against the senior annotations. Recall = fraction of
   senior-annotated coherence issues that the maintainer also
   commented on. Report per-PR and pooled.

4. **Output.** A pooled recall number → plug into the Q2 decision
   table. Plus a qualitative note: are the issues maintainers *miss*
   systematically different (e.g. maintainers catch convention
   deviations but miss duplication)? That shifts which dimensions
   Phase 3 can measure.

5. **Calibration byproduct.** The senior annotations from this pilot
   double as the seed of the matcher calibration set (the design
   doc's matcher-calibration section needs hand-labeled pairs) — the
   senior-issue ↔ maintainer-comment matches and non-matches are
   exactly the finding↔comment pairs the matcher must be calibrated
   on. Run the pilot so its output feeds both decisions.

## What is now decided vs still open

**Decided (pending human ratification of this doc):**
- Phase 3 = coherence-dimension review. (Q1)
- Adversarial multi-agent → candidate Phase 4. (Q1)
- Corpus path = pre-registered decision rule on senior-pilot recall. (Q2)
- Provisional repo = pydantic. (Q2)

**Still open — genuine human dependencies, no agent can close them:**
- The senior-annotator 5-PR pilot. Needs a senior reviewer. Produces
  the recall number that resolves Q2's decision rule.
- Ratification of this document.
- The six in-doc design-question recommendations (corpus option d,
  3 dimensions, RAG-held-constant, evidence_pointer a3, F1+residual,
  single-repo) — all recommended in `PHASE_3_DESIGN.md`, all still
  want a human yes.

## Next action

Human runs (or assigns) the senior-annotator 5-PR pilot using the
protocol above. Its recall number resolves Q2; its annotations seed
the matcher calibration set. Until then, Phase 3 implementation
cannot start — and should not, because the corpus path is the
load-bearing decision and it is one measurement away from settled.
