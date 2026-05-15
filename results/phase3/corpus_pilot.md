# Phase 3 corpus pilot — maintainer-comment viability probe

Date: 2026-05-15
Purpose: de-risk the highest-risk decision in `docs/PHASE_3_DESIGN.md`
— the corpus path. The design doc flagged corpus option (d) (real PRs
+ maintainer comments + spot senior annotations) as carrying a
"maintainer-comment-recall ceiling" risk and recommended a ~5-PR pilot
before committing the full corpus budget. This is that pilot, run one
step earlier than planned: before picking the repo, to check whether
the maintainer-comment supply is even dense enough to build a corpus
from.

**This is exploratory. No corpus was built. No senior annotation was
done.** The pilot probes GitHub PR data only.

## What the pilot can and cannot answer

Can answer (from PR data alone):
- Do mature Python repos produce maintainer review comments at a
  density sufficient to assemble a ~40-PR corpus?
- When a PR is reviewed, are the comments substantively
  coherence-flavored, or nits / CI noise / correctness-only?
- What are the mechanical mining blockers?

Cannot answer (needs a senior annotator — deferred to the real 5-PR
pilot in the design doc's plan):
- The actual maintainer-comment-recall ceiling: of all coherence
  issues a senior reviewer would flag on a PR, what fraction did the
  maintainer actually comment on? This is THE number that decides
  whether option (d) discriminates the arms. The pilot below bounds
  the *supply* of comments; it does not bound their *completeness*.

## Repos probed

| repo | lang | license | size | stars |
|------|------|---------|------|-------|
| encode/httpx | Python | BSD-3-Clause | ~8.5 MB | 15.3k |
| pydantic/pydantic | Python | MIT | ~404 MB | 27.8k |

Both fit the design doc's repo-selection archetype (active
maintainership, permissive license, Python so a senior annotator on
this project is competent to rate). pydantic is larger — more
cross-file coherence surface, which design question 2 identified as
the discrimination axis.

## Finding 1 — inline review-comment density is LOW

Inline review comments (`pulls/{n}/comments`) per merged PR:

| repo | merged PRs scanned | PRs with ≥1 inline comment | total inline comments |
|------|--------------------|-----------------------------|------------------------|
| httpx | 62 | 6 (~10%) | ~16 |
| pydantic | 55 | 6 (~11%) | ~16 |

~90% of merged PRs on both repos have **zero** inline review
comments. This is the dominant pilot finding. Mature Python OSS with
strong maintainers trends toward approve-and-merge: review happens,
but it does not leave a dense inline-comment trail.

Implication for corpus construction: to assemble a ~40-PR corpus of
*reviewed* PRs, you scan ~350-400 merged PRs. That is mechanically
feasible (both repos have thousands of merged PRs) but it means the
corpus is drawn from the ~10% most-commented PRs — a selection-biased
minority. See Finding 3.

## Finding 2 — when a PR IS reviewed, comments are coherence-flavored

Content quality is the good news. Three pydantic PRs read in full:

**PR #13070** (`encode/httpx`-style cleanup PR). Maintainer review
produced ~6 distinct coherence observations:
- "`from typing import TypeAlias` can be moved to the top-level
  import" — convention alignment.
- "this can be inlined into the call on line 212" — abstraction.
- review body: "a TODO ... could switch to a `match` statement" —
  idiom/convention.
- review body: "`test_new_union_origin` is probably not needed any
  more" — test quality.
- review body: "`SafeGetItemProxy` can probably be made a
  `slots=True` dataclass" — convention/idiom.

**PR #13133.** Naming accuracy ("Is our `_eval_type` really a
'backport'? ... rather than bringing new features to older
versions" → author renames to "vendored"); comment clarity
(`suggestion` blocks rewording an inline comment).

**PR #13129.** Abstraction-appropriateness ("This is a bit weird,
because even though the metadata is attached to the root type ...");
duplication ("This is not necessary anymore as later in the code
this gets set from the metadata we now populate").

Every coherence dimension the design doc named — convention
alignment, layer/abstraction appropriateness, duplication, naming,
test quality — appears unprompted in real pydantic review comments.
The dimension framing in design question 2 is ecologically grounded.

## Finding 3 — the ceiling risk is SELECTION, not per-PR quality

The design doc framed the risk as "maintainer comments aren't a
complete coverage of issues." The pilot refines this: the limiting
factor is not how thoroughly a reviewed PR is commented (Finding 2
shows reviewed PRs are richly commented). It is that **only ~10% of
merged PRs are reviewed inline at all**, and that minority is
plausibly not representative:

- PRs that attract review comments may be the riskier / more
  contentious / junior-contributor changes.
- Maintainer self-merges (the silent ~90%) may be systematically
  *more* coherent already — which is why they drew no comment.

A corpus built from the reviewed 10% would over-represent
low-coherence PRs. That is not fatal — the experiment asks whether
multi-agent catches coherence issues, and PRs with coherence issues
are the useful ones — but it must be stated as a corpus property,
not discovered later. The arms are compared on the same corpus, so
selection bias does not invalidate the *delta* between arms; it does
limit how far the result generalizes ("multi-agent helps on
coherence-issue-bearing PRs" is a narrower claim than "on PRs").

## Finding 4 — mechanical mining notes

- **Two comment sources, both load-bearing.** Inline review comments
  (`pulls/{n}/comments`) and review-summary bodies
  (`pulls/{n}/reviews[].body`) both carry coherence signal. PR
  #13070's review body had 3 coherence observations that appear in
  no inline comment. A miner that reads only inline comments loses
  signal. Conversation comments (`issues/{n}/comments`) are mostly
  author replies and CI/bot noise — lower yield, still worth
  scanning.
- **`suggestion` blocks** (GitHub's ```suggestion fenced blocks)
  appear in review comments and are concrete coherence fixes — easy
  to parse, high-precision ground truth.
- **Author replies interleave.** Comment threads mix maintainer
  comments and author responses (e.g. Viicos replying to
  davidhewitt). The miner must filter to comments authored by a
  maintainer (not the PR author) — author identity is in the API
  payload, the maintainer set is known per repo.
- **Force-push history loss.** Inline comments anchored to lines that
  later force-pushes rewrote can become "outdated" — the API still
  returns them but the line anchor is stale. The miner must snapshot
  the PR's head commit at comment time, not assume the final diff.

## Recommendation

**Corpus option (d) is viable on content grounds.** Finding 2 is a
clear positive: real maintainer comments on mature Python repos are
substantively coherence-flavored and map onto the design doc's
dimensions. Finding 1's low density is a cost (scan ~10× the corpus
size) and Finding 3's selection bias is a corpus property to
pre-register, but neither is disqualifying.

**Do not pick the repo yet.** The pilot probed httpx and pydantic;
pydantic has more cross-file coherence surface and a slightly higher
review density. But the real 5-PR pilot from the design doc's plan —
the one that needs a senior annotator — must run before the repo is
locked. That pilot answers Finding 1's open question: of the
coherence issues a senior annotator flags on a reviewed PR, what
fraction did the maintainer comment on? If that recall is, say, >60%,
option (d) discriminates fine. If it is <30%, the maintainer comments
are too sparse a ground truth and the corpus must fall back to design
question 1 option (c) — gold-standard senior annotation at smaller N.

**Suggested next step:** pick 5 pydantic PRs from the reviewed ~10%
(e.g. #13070, #13133, #13129, #13070-era PRs with ≥3 comments), have
a senior annotator independently flag every coherence issue they see
on each PR, then measure overlap with the maintainer comments. That
is the design doc's recommended 5-PR pilot, now with a concrete repo
and PR shortlist to draw from.

## Data

Repos and PR numbers probed are listed inline above. No PR snapshots
were persisted — this pilot read the GitHub API live and did not
build corpus artifacts. The real corpus pilot will persist PR
snapshots under `phase3_corpus/` once the repo is locked.
