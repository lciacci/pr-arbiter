# pr-arbiter — summary

A reviewer + arbiter multi-agent system for code review, built as a Phase 1
POC. Goal: measure whether agent-to-agent dynamics produce better triage
than self-critique, against a ground-truth corpus.

This document is a working summary of the work to date. Per-iteration notes
in `results/` carry the detail.

## Architecture journey

The system evolved across four iterations. Each iteration was an
architectural change, not a prompt tweak.

| iter | architecture                                       | what it tested                                       |
|------|----------------------------------------------------|------------------------------------------------------|
| 0    | reviewer (adversarial single-pass) + arbiter as triage filter | does filter-style arbitration improve reviewer output? |
| 1    | reviewer with severity anchoring + strict-default-drop arbiter | does aggressive arbitration help? does severity calibration matter? |
| 2    | reviewer unchanged + arbiter as independent second reviewer (can ADD findings) | does the second agent surface things the first misses? |
| 3    | iter2 + mutual triage (two voices vote KEEP/DROP/UNSURE on merged findings) | does adversarial assessment between existing voices produce a useful blocking/advisory split? |

A separate diagnostic between iter1 and iter2 (`results/diagnostic_notes.md`)
ruled out the filter-only arbiter at both prompt extremes.

Iter4 was not a prompt iteration — it was a corpus discovery, described
below.

## The corpus

20 PRs built from public Flask 3.0.0 source. Each PR has a controlled
before/after pair with a rubric of expected findings. 55 expected findings
total: 8 critical, 11 high, 18 medium, 18 low.

Four author personas (Marcus / Priya / Devon / Alex) produce bugs with
different signatures — Marcus's are subtle semantic bugs, Priya's are
almost-secure code, Devon's are obvious bugs, Alex's are architectural
mistakes. Personas are an authoring tool only; agents never see them.

3 PRs are "negative controls" — clean refactors meant to produce empty
reviews. 3 are "style-heavy with latent bug" to test triage. 14 are
straightforward planted-bug PRs.

The eval harness keeps a strict separation between agent input
(`load_agent_input`) and rubric loading (`load_rubric`) — agents cannot
accidentally see the answer key.

## Headline numbers

All scores on the same 20-PR corpus. Critical recall is reported separately
because missing a critical is qualitatively worse than missing a low.

| configuration                              | recall | precision | FP | critical recall | neg-ctrl |
|--------------------------------------------|-------:|----------:|---:|----------------:|---------:|
| v1 reviewer-alone (baseline)               |  50.9% |     48.3% | 30 |        6/8 (75%) |     1/3 |
| v1 reviewer + v1 arbiter (filter)          |  47.3% |     52.0% | 24 |        6/8 (75%) |     1/3 |
| **v2 reviewer-alone**                      |  52.7% |     60.4% | 19 |        6/8 (75%) |     1/3 |
| v2 reviewer + v2 strict arbiter            |  38.2% |     70.0% |  9 |        4/8 (50%) |     1/3 |
| iter2: v2 reviewer + indep arbiter (merge) |  61.8% |     49.3% | 35 |        7/8 (88%) |     2/3 |
| iter3 final (merged, mutual-triage kept)   |  56.4% |     51.7% | 29 |        7/8 (88%) |     1/3 |
| **iter3 blocking (high-conf only)**        |  43.6% | **58.5%** | **17** |    **7/8 (88%)** | **1/3** |

The two configurations worth defending operationally are **v2 reviewer-alone**
and **iter3 blocking-tier**. They occupy different operating points: the
single-agent path peaks at 6/8 critical recall with strong precision; the
multi-agent path catches one additional critical at comparable precision and
lower FP count, plus surfaces an advisory tier of 17 lower-confidence
findings.

## What the multi-agent setup adds

The architecture justification rests on `pr_009` F1 — a critical security
issue (regex-based HTML sanitization, an XSS-bypassable anti-pattern). The
single-agent reviewer missed this bug across every run and every prompt
variant tried. The iter2 independent arbiter caught it; the iter3 mutual
triage promoted it to high-confidence blocking. The architecture catches
specifically the kind of bug a single pass with the same model doesn't.

It also produces a two-tier output (blocking vs advisory) that maps to how
senior reviewers actually triage. The advisory tier carries real findings
the system isn't fully confident about — `pr_005`'s function defined after
`if __name__ == "__main__"` (unreachable), `pr_015`'s unauthenticated
`/send-email` endpoint, `pr_004`'s duplicate ETag helper. These are surfaced
without being blocking — the right disposition for "probably real but I
can't be sure from the code alone."

## Where the system loses

- **Two criticals remain uncaught.** `pr_015` F1 (missing JSON validation
  on `request.get_json()`) and `pr_017` F1 (config field set but not
  persisted) are missed across every configuration. These appear to be
  genuine reasoning ceilings: the bugs require holding "what happens when
  this returns None" or "is this state actually persisted" in mind, which
  the agents don't do reliably. Worth a focused experiment if pursued.

- **Asymmetric triage bias.** Mutual triage produces 10 reviewer-keep
  arbiter-drop disagreements and zero in the reverse direction. The arbiter
  voice does the triage work; the reviewer voice acts as a backstop. Real
  findings end up in advisory because of this. Symmetric-skeptic voices
  (e.g., security-skeptic vs correctness-skeptic) would rebalance but
  probably lose some real advisories — tested in spirit, not in code.

- **The persistent pr_007 issue turned out to be a corpus mislabel.**
  Across all six configurations, the reviewer produced one "false positive"
  on pr_007 — a negative-control PR. Investigating after iter3 revealed
  the reviewer was correctly identifying a real bug introduced by the
  refactor: `_parse_env_bool` has a docstring/implementation mismatch and
  sets up future callers for silent inversion bugs. The rubric author
  checked "does this preserve runtime behavior?" (yes) but missed "does
  this introduce a foot-gun for future maintainers?" (yes). See
  `results/iter4_corpus_discovery.md` for the full analysis. We have chosen
  not to relabel the rubric — the cost of the mislabel is honest and the
  discovery is itself a load-bearing artifact of the eval-first discipline.

### Footnote: scores under a corrected pr_007 rubric

For reference, here is the same table re-scored against a corrected rubric
that credits the `_parse_env_bool` finding (medium correctness, line range
[35, 47]) and recategorizes pr_007 from `negative_control` to
`style_with_latent_bug`. The corpus file itself is unchanged; this is an
in-memory rescore.

| configuration                              | recall | precision | FP | critical | neg-ctrl |
|--------------------------------------------|-------:|----------:|---:|---------:|---------:|
| v1 reviewer-alone                          |  51.8% |     50.0% | 29 |     6/8  |    0/2   |
| v1 reviewer + v1 arbiter (filter)          |  48.2% |     54.0% | 23 |     6/8  |    0/2   |
| **v2 reviewer-alone**                      |  51.8% |     60.4% | 19 |     6/8  |  **0/2** |
| v2 reviewer + v2 strict arbiter            |  37.5% |     70.0% |  9 |     4/8  |    0/2   |
| iter2: v2 reviewer + indep arbiter         |  62.5% |     50.7% | 34 |     7/8  |    1/2   |
| iter3 final (merged kept)                  |  57.1% |     53.3% | 28 |     7/8  |    0/2   |
| **iter3 blocking (high-conf only)**        |  42.9% | **58.5%** | **17** | **7/8** | **0/2**  |

Two things move materially. First, every configuration except iter2-merged
drops to 0/2 negative-control failures — the durable pr_007 reviewer flag
that previously dragged the metric is now a true positive. Second, recall
moves up across most configurations as pr_007's `_parse_env_bool` finding
joins the rubric.

Critical recall is unchanged (pr_007's issue is medium-severity), so the
load-bearing 7/8 critical figure for the multi-agent system holds either
way. The corrected view is a cleaner read of the system's actual quality;
the reported view is what the eval-as-written measures. Both are honest;
they answer different questions.

The line-range chosen for the corrected expected finding ([35, 47], full
function body) matters at the edges. With [42, 47] (return statement
focus) iter3's high-confidence finding would also match, raising blocking
recall slightly. Neither choice is uniquely correct; the rubric author
would decide.

## Methodology choices that worked

- **Eval-first, no prompt iteration without rerunning.** Every prompt
  change measured. Iter1 reviewer changes turned out to be a clear win
  (+12 pp precision, +2 pp recall); iter1 arbiter changes overshot (dropped
  criticals). Without the eval, the wrong move would have looked plausible.

- **Architectural changes, not prompt nudges.** The architecture-vs-
  architecture comparisons (iter1 vs iter2 vs iter3) carried more signal
  than the prompt-vs-prompt sweep. Once iter2 showed independent arbitration
  catches a critical, iter3 was about how to *use* the second agent's
  output, not how to tune either agent.

- **Capturing per-stage findings, not just final scores.** The runner
  records reviewer_findings, arbiter_findings, and final_findings
  separately. Inspecting reviewer/arbiter divergence is what revealed both
  the multi-agent value and the corpus mislabel.

- **Critical recall reported separately.** A single weighted score would
  have hidden the iter1 arbiter dropping criticals to gain medium-tier
  precision — exactly the failure mode that matters most.

## Cost

API calls per PR by configuration: 1 (reviewer-alone), 2 (reviewer +
arbiter), 4 (reviewer + arbiter + 2 triage voices). On 20 PRs, total
spend across all iterations is on the order of several dollars. The full
iter3 pipeline runs in roughly 5 minutes wall-clock.

## Where this could go next

In priority order, if iter5 were pursued:

1. **Reviewer-side "check unchanged code before flagging" rule.** Targets
   the kind of false positive where the reviewer assumes the unchanged
   code must contain something to flag because a refactor occurred. Cheap.
2. **Focused experiments on the two uncaught criticals.** One-off prompts
   targeted at `pr_015` and `pr_017`. If no reframing surfaces them, accept
   that as the agent reasoning ceiling.
3. **Symmetric-skeptic triage voices.** Replace reviewer/arbiter voices
   with two skeptics framed differently (security vs correctness, say). Test
   whether the asymmetric defense bias is feature or bug.
4. **Prompt caching for cost reduction.** Engineering, not research.

A reasonable alternative is to stop here and treat the architectural finding
as the Phase 1 deliverable. The next interesting question (Phase 2 territory)
is whether this pattern generalizes to spec → architecture → implementation
workflows where the corpus isn't pre-authored.

## Reading guide

- `README.md` — repo overview, status checklist.
- `results/baseline_notes.md` — first reviewer + arbiter baseline.
- `results/iter1_notes.md` — severity-anchored reviewer + default-drop arbiter.
- `results/diagnostic_notes.md` — proves filter-only arbitration cannot
  win over a calibrated reviewer.
- `results/iter2_notes.md` — independent-arbiter architecture; catches the
  pr_009 critical.
- `results/iter3_notes.md` — mutual-triage adversarial assessment; the
  blocking/advisory split.
- `results/iter4_corpus_discovery.md` — pr_007 mislabel investigation.
- `corpus/manifest.json`, `docs/PERSONAS.md` — corpus structure and authoring
  reference.
- `agents/reviewer.py`, `agents/arbiter.py`, `agents/triage.py` — agent code.
- `eval/harness.py`, `eval/run_baseline.py`, `eval/run_triage.py` — eval
  pipeline.
