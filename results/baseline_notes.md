# Baseline notes — pr-arbiter session 2

Run date: 2026-05-13. Model: `claude-sonnet-4-6` for both reviewer and arbiter.
Tool-use schema for structured output. Arbiter sees diff + before + after + reviewer findings.

## Headline

|                   | reviewer-alone | reviewer + arbiter | Δ           |
|-------------------|---------------:|-------------------:|-------------|
| Recall            |         50.91% |             47.27% | −3.6 pp     |
| Precision         |         48.28% |             52.00% | +3.7 pp     |
| False positives   |             30 |                 24 | −6          |
| Critical recall   |         75% (6/8) |             75% (6/8) | 0           |
| High recall       |         64% (7/11) |             64% (7/11) | 0           |
| Neg-ctrl failures |            1/3 |                1/3 | 0           |

The arbiter is doing something — it drops findings, all of them at medium/low
severity — but the net effect is a near-1:1 trade of recall for precision. The
multi-agent setup is not yet justified on these numbers. That's a real finding,
not a failure of the run.

## What worked

- **Tool-use for structured output is the right call.** Zero parse failures
  across 40 calls (20 reviewer + 20 arbiter). The earlier debate over JSON-mode
  vs tool-use was settled correctly. Adding fields later (e.g., the rationale
  field used by the arbiter) was a schema edit, not a prompt rewrite.
- **Critical recall is good.** 6/8 caught on first pass with a generic
  adversarial-reviewer prompt and no eval-aware tuning. Both misses were
  correctness-critical bugs (pr_015 missing JSON validation; pr_019 reinventing
  `send_from_directory`), not security-critical.
- **Arbiter preserved every critical and high finding it saw.** No regression
  on the severity tiers that matter. The drops are all in medium/low.
- **Negative controls mostly work.** pr_002 and pr_018 both produced empty
  reviews from the reviewer, no arbitration needed.

## What didn't

- **Arbiter is too lenient.** Total reviewer findings across 20 PRs ≈ 58. The
  arbiter dropped 8 (6 FP + 2 TP). That's a ~14% drop rate — well below the
  20–40% calibration target floated in design. The bias is exactly what was
  predicted: helpfulness training pushes the model to keep findings unless it
  has strong reason to drop. The system prompt's "be willing to drop" framing
  was not aggressive enough.
- **The arbiter did not fix systemic reviewer weaknesses.** Specifically:
  - pr_007 (Marcus negative control) still has 1 FP from the reviewer — the
    arbiter let it through.
  - Alex persona stays at 30% recall (3/10), with 9 FPs unchanged from the
    reviewer-alone run.
- **Reviewer's severity calibration is consistently inflated.** F3 and F4 on
  pr_001, for example: rubric says medium, reviewer says high. Not visible in
  recall but degrades the perceived signal of "block the PR." Worth fixing
  even though it doesn't move the headline number.
- **Reviewer is weaker on correctness-critical than security-critical.** Both
  missed criticals are logic bugs, not vuln patterns. The model pattern-matches
  on classic CVE shapes well; reasoning about whether `request.get_json()` can
  return `None` and whether downstream code handles it is harder.
- **The eval matcher splits some reviewer findings.** On pr_001 the reviewer
  produced separate findings for "AUDIT_TOKEN in logs" and "user email in
  logs" — the rubric folds these into one F3. The approximate matcher counts
  one as TP, the other as FP. Not strictly a model problem; worth a note for
  matcher v2 or rubric authoring.

## Per-persona recall (reviewer-alone)

| Persona | Recall | FP | Note                                        |
|---------|-------:|---:|---------------------------------------------|
| Marcus  |    62% |  6 | Subtle semantics — solid given the prompt.  |
| Priya   |    53% |  9 | Almost-secure code — vuln-pattern bias hurts. |
| Devon   |    55% |  6 | Obvious bugs — weaker than expected. Investigate. |
| Alex    |    30% |  9 | Architectural — clear blind spot.            |

Alex is the biggest gap. The bugs in those PRs are about cross-file structure,
function-level coupling, and "this should call the existing helper" — things a
single-file diff review doesn't see. The agent has full file context but is not
using it to reason about alternatives that already exist in the file.

## Next iteration — concrete moves

In rough order of expected impact:

1. **Rewrite the arbiter system prompt to push drop rate up.** Replace the
   abstract "be willing to drop" framing with: "By default, assume the
   reviewer is over-flagging. Drop a finding unless you can re-state from the
   after-state code exactly why it's a bug." This shifts the prior from
   "keep unless I have a reason to drop" to "drop unless I have a reason to
   keep." Track drop rate per PR; if it overshoots and recall craters, back
   off. The earlier concern about anchoring on a numeric drop rate is still
   right — don't put a percentage in the prompt — but flip the default action.

2. **Add an "is the diff clean?" first question to the arbiter.** Explicit
   reasoning step before listing kept findings. The negative-control miss on
   pr_007 looks like the arbiter pattern-matched the reviewer's finding shape
   and assumed something must be wrong. A "first, decide if this PR has any
   real issue at all" framing should help.

3. **Reviewer prompt: bias toward correctness-critical detection.** Add to
   the system: "Logic bugs (None handling, off-by-one, missing branches,
   reinvented stdlib) are as important as security vulns. Spend equal attention."
   This is targeted at the two missed criticals.

4. **Reviewer severity calibration.** Add concrete severity examples to the
   system prompt. The current text describes severities abstractly; the model
   inflates because it has nothing to anchor against.

5. **Alex blind spot is a separate experiment.** Probably needs a "look for
   existing functions in this file that already do what the new code is doing"
   instruction. Defer until 1–4 are tried.

## What I'd not change

- **Don't expand the corpus.** The Alex blind spot is the agent's problem,
  not the corpus's. The rubric items are real engineering critiques.
- **Don't switch the arbiter to Opus yet.** The arbiter is too lenient on
  Sonnet — that's a prompt problem, not a capability problem. Throwing
  Opus at it before fixing the prompt confounds the experiment.
- **Don't run the eval on a subset to "see if it works."** The full 20 PRs
  took ~3.5 min wall time and a few dollars. Iterate against the full
  corpus.

## Open questions for session 3

- After the prompt rewrite, does the arbiter actually drop more? If recall
  still craters at higher drop rates, the architecture is wrong (re-ranking
  doesn't add signal — we need an arbiter that can SEE different things than
  the reviewer).
- Is the eval's approximate-match function too coarse? File+category+line±3
  is generous; tighter matching might surface real precision issues currently
  hidden.
- The current pipeline is single-shot reviewer → single-shot arbiter. If
  iteration plateaus, consider letting the reviewer self-critique once before
  arbitration. That's an architectural change, not a prompt change.

## Artifacts

- `results/baseline_20260513.json` — reviewer-alone run, per-PR findings + scores.
- `results/baseline_20260513_arbiter.json` — same reviewer findings (cached, not
  re-run) fed through the arbiter, with arbiter outputs and scores.
- `results/baseline_run.log` and `results/arbiter_run.log` — raw stdout from
  both runs.
