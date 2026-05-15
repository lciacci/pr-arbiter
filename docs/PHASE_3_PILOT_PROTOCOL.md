# Senior-annotator pilot protocol

## What this is

The pilot the Phase 3 design doc gates on. Produces two outputs:

1. The recall number that fires the Q2 corpus-path decision rule
   (≥60% / 30-60% / <30%).
2. The matcher calibration set — hand-labeled (finding, comment)
   pairs used to validate the LLM matcher before it runs on
   experimental data.

Senior rater: project lead (Lorenzo Ciacci). The blinding concern
is real but mitigable; see "Blinding protocol" below.

## Why project lead can be the senior rater

The methodological worry is that a non-blinded rater can elevate
multi-agent findings post-hoc when rating experimental output.
That worry applies to the residual-rating step in the main Phase 3
experiment, not to the pilot. The pilot rates PRs cold for
coherence issues, with no experimental output to be biased toward.

The blinding mitigation for the later experimental phase:
annotations from the pilot are frozen and committed before any
experimental run. Project lead does not see arm output during
pilot annotation. When the experimental phase runs, the senior
rating of residual findings (findings not matching maintainer
comments) is done blind to arm-of-origin. Both conditions are
procedurally enforceable.

## Pre-pilot setup (1-2 hours)

1. Select 5 PRs from pydantic. Criteria:
   - Merged within the last 18 months.
   - Has at least 3 maintainer review comments (filters for PRs
     that got real review).
   - Touches non-trivial code (more than a one-line bugfix; more
     than a docstring change).
   - Mix of sizes: 1 small (<100 lines diff), 3 medium (100-500),
     1 large (>500).
   - Avoid PRs project lead has personally reviewed or commented
     on if any exist.

2. Snapshot each PR's state at the time of review:
   - PR diff
   - Touched files at the PR's base commit
   - Maintainer review comments (text + author + file/line if
     line-anchored)
   - Final merged state (for reference, not used in annotation)

3. Commit the snapshot to `phase3_corpus/pilot/<pr_id>/`. One
   directory per PR. Include a `comments.json` with the
   maintainer comments in structured form.

## Annotation phase (6-10 hours, the bulk of the pilot)

For each of the 5 PRs, project lead does an independent coherence
review WITHOUT looking at the maintainer comments first. The
annotation is "what coherence issues would I flag if I were
reviewing this PR cold." Annotations cover only the three
in-scope dimensions from the design doc: convention alignment,
layer appropriateness, duplication.

Per-PR procedure:

1. Read PR diff and touched files. Spend 30-60 minutes per PR.
   Use the full repo at the PR's base commit for context (this is
   the equivalent of what option (c) retrieval gives reviewers in
   the experiment).

2. Write findings to
   `phase3_corpus/pilot/<pr_id>/senior_findings.json`. One entry
   per finding:

   ```json
   {
     "dimension": "convention-alignment | layer-appropriateness | duplication",
     "claim": "1-2 sentence description of the issue",
     "evidence_pointer": "path/to/file.py:LINE_RANGE",
     "severity": "blocking | advisory | nit",
     "rationale": "why this is the issue, 2-3 sentences"
   }
   ```

   No upper bound on findings per PR. If a PR has no coherence
   issues, log an empty list with a note explaining why.

3. After writing findings, open `comments.json` for that PR. For
   each maintainer comment, classify as:

   - `coherence` — comment is about one of the three in-scope
     dimensions.
   - `correctness` — comment is about a bug, behavior, or
     functional issue.
   - `style` — formatting, naming-only without convention claim,
     docstring wording.
   - `other` — discussion, questions, agreement, etc.

   Only `coherence` comments matter for the recall calculation.

4. For each `coherence` maintainer comment, mark whether it
   corresponds to one of project lead's senior findings. Pair
   them in a `comment_to_finding_map.json`:

   ```json
   {
     "comment_id_or_hash": "finding_id_or_null"
   }
   ```

   `null` means the maintainer flagged a coherence issue project
   lead missed. This is fine — the pilot is measuring recall in
   both directions.

## Recall calculation (15 minutes)

For each PR, compute:

- `maintainer_coherence_comments` = count of comments classified
  as `coherence`
- `senior_findings_in_maintainer_comments` = count of senior
  findings that pair to a maintainer `coherence` comment
- `recall_for_pr` = senior_findings_in_maintainer_comments /
  total_senior_findings (NOT divided by maintainer comment count)

Aggregate across PRs:

- `pilot_recall` = sum of senior findings matched to comments,
  divided by total senior findings across all 5 PRs.

This is the number that fires the Q2 decision rule. Specifically:
recall is "fraction of senior-flagged coherence issues that
maintainers also commented on." If high, maintainer comments are
a good ground truth (option d works as-is). If low, maintainer
comments miss many real coherence issues and the corpus path
needs more annotation (option d expanded, or fall back to c).

Commit `phase3_corpus/pilot/recall.json` with the aggregate and
per-PR breakdown.

## Matcher calibration set output

The pilot also produces (finding, comment) pairs that seed the
matcher calibration. Specifically:

- Positive pairs: each (senior_finding, maintainer_comment) pair
  where project lead marked them as corresponding.
- Negative pairs: each (senior_finding, maintainer_comment) pair
  where they don't correspond (sampled randomly from the
  non-matching cross-product).

Target: 30-50 positive pairs, 30-50 negative pairs across the 5
PRs. If pilot doesn't produce enough, the matcher calibration set
is undersized and the design doc's matcher-calibration step needs
either more pilot PRs or supplementary hand-labeling.

Commit to `phase3_corpus/pilot/matcher_calibration.json`.

## Blinding protocol for later experimental phase

This section exists because project lead is both pilot annotator
and senior rater. The procedural protections:

1. Pilot annotations are committed to git and signed off with a
   timestamp BEFORE any experimental arm runs. Project lead
   cannot retroactively modify pilot findings to align with
   experimental output.

2. During the experimental phase, residual findings (those not
   matched to maintainer comments via the matcher) are rated by
   project lead WITHOUT arm-of-origin labels. The rating tool
   shuffles findings from both arms and presents them blind.

3. Project lead does not see arm-of-origin until rating is
   complete and committed.

4. Inter-temporal blinding: there should be at least 2 weeks
   between pilot annotation and experimental rating, to reduce
   the chance project lead remembers specific PR contents and
   identifies arms by recognition.

These protections are weaker than independent senior raters but
stronger than no blinding. Document explicitly in the Phase 3
writeup that project lead was both pilot annotator and senior
rater, with these mitigations.

## What this protocol does NOT do

- Does NOT pilot the matcher itself. Matcher calibration happens
  later using the pairs this protocol produces.
- Does NOT run any experimental arms. The pilot precedes any
  arm-level experiment by design.
- Does NOT involve any LLM in the senior-rater role. The whole
  point of the pilot is to produce human ground truth.

## Time estimate

- Pre-pilot setup: 1-2 hours
- Annotation: 6-10 hours (1-2 hours per PR including write-up)
- Recall + matcher set: 15-30 minutes
- Total: 8-12 hours, ideally over 2-4 sessions

Can be done in chunks. The annotation phase parallelizes across
PRs — one PR at a time, can pause between them.

## Resumption signal

When this pilot is complete and `recall.json` is committed, the
Q2 decision rule fires and the implementation brief can be
written. Resume the implementation phase by reading
`docs/PHASE_3_RESUMPTION.md` and following its next-action
pointer.
