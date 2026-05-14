# pr-arbiter

A reviewer + arbiter multi-agent system for code review. Phase 1 of a
multi-agent software development POC.

**Headline result:** the multi-agent system (reviewer + independent arbiter
+ mutual triage) catches a critical security bug (regex-based HTML
sanitization on pr_009) that the best single-agent reviewer misses across
every prompt variant tried. Same comparable precision, fewer false
positives, two-tier output (blocking + advisory) that matches how senior
reviewers actually work.

| configuration                              | recall | precision | FP | critical recall | neg-ctrl |
|--------------------------------------------|-------:|----------:|---:|----------------:|---------:|
| best single-agent (v2 reviewer-alone)      |  52.7% |     60.4% | 19 |   6/8 (75%)     |   1/3    |
| **multi-agent blocking-tier (iter3)**      |  43.6% | **58.5%** | **17** | **7/8 (88%)** | **1/3**  |

See [SUMMARY.md](SUMMARY.md) for the full project writeup, or
[docs/index.html](docs/index.html) for a one-page visual overview.

## Quick links

- [SUMMARY.md](SUMMARY.md) — project writeup, all iterations, methodology.
- [docs/index.html](docs/index.html) — visual one-pager (open in a browser).
- [results/pr_009_worked_example.md](results/pr_009_worked_example.md) —
  step-by-step on the critical catch.
- [results/iter3_notes.md](results/iter3_notes.md) — most recent iteration.
- [results/iter4_corpus_discovery.md](results/iter4_corpus_discovery.md) —
  the agent caught a real bug the rubric mislabeled.

## What this is

Three agents, in order:
1. **Reviewer** — adversarial single-pass review of the diff. Tuned to
   surface issues, not to triage them.
2. **Arbiter** — independent second-pass review. Sees the reviewer's
   findings as anti-redundancy context; surfaces what the reviewer missed,
   especially correctness-critical and architectural issues.
3. **Triage** — two voices (reviewer-style, arbiter-style) independently
   vote KEEP / DROP / UNSURE on the merged finding list. Aggregation:
   both KEEP → blocking, both DROP → drop, mixed → advisory.

Input: a PR diff (before/after pair).
Output: a two-tier triaged review (blocking findings + advisory findings).

This is a stepping-stone POC. Phase 2 will close the writer loop or pivot
to spec → architecture → implementation using the patterns learned here.

## Why agents, not just a prompt

A single-pass review with a good prompt catches roughly 6/8 criticals on
this corpus, capped by what one model + one prompt can see. The interesting
question is whether multi-agent dynamics produce real second-opinion
signal — and on this corpus, yes: the architecture catches one additional
critical at comparable precision.

The four-iteration journey across this exact question (and the diagnostic
that ruled out a wrong architectural assumption between iter1 and iter2)
is documented in `results/*_notes.md`.

## Repo layout

```
agents/             # reviewer.py, arbiter.py, triage.py
corpus/             # 20 PRs with rubrics + Flask 3.0.0 source
eval/
  harness.py        # load_agent_input, load_rubric, score_pr, summarize
  run_baseline.py   # reviewer-only or reviewer+arbiter pipeline
  run_triage.py     # iter3 mutual-triage runner
  show_results.py   # dashboard of all iterations side-by-side
docs/
  index.html        # visual one-page summary
  PERSONAS.md       # corpus authoring reference (NEVER read by agents)
results/            # eval outputs + per-iteration notes
```

## Running it

Requires Python 3.9+ and an `ANTHROPIC_API_KEY` set in `.env` at repo root.

```bash
# Set up (once)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Run reviewer-alone over all 20 PRs (~3 min)
.venv/bin/python eval/run_baseline.py

# Run reviewer + independent arbiter (~5 min)
.venv/bin/python eval/run_baseline.py --with-arbiter

# Run iter3 mutual triage over a prior iter2 output (~3 min)
.venv/bin/python eval/run_triage.py --source results/iter2_20260513.json

# View all configurations side-by-side
.venv/bin/python eval/show_results.py
```

## Eval design

- **Recall**: of the 55 expected findings, how many did the system catch?
- **Critical recall**: of the 8 critical findings specifically, how many
  caught? Reported separately because missing a critical is qualitatively
  worse than missing a low. No weighted-average score.
- **Precision**: of the system's findings, how many matched something in a
  rubric?
- **Negative control failure rate**: how often did the system flag
  something on a PR with `expected_findings: []`?
- **Per-persona breakdown**: slice results by persona to identify
  systematic blind spots.

Matching is approximate (file + category match, line within ±3). Exact
line matching isn't worth the manual effort to maintain.

## Corpus

20 PRs built from public Flask 3.0.0 source. Each PR is a controlled
before/after pair with rubric-defined expected findings.

| Persona | Count | Bug type signature                                      |
|---------|-------|---------------------------------------------------------|
| Marcus  | 5     | Clean code, subtle semantics (races, contract bugs)     |
| Priya   | 5     | Almost-secure code (validation theater, wrong crypto)   |
| Devon   | 6     | Obvious bugs (nulls, off-by-one, secrets in logs)       |
| Alex    | 4     | Architectural mistakes, style-heavy refactors           |

55 expected findings total: 8 critical, 11 high, 18 medium, 18 low.

Personas are authoring tools. **Agents never see persona info.** See
`docs/PERSONAS.md`.

## Status

Phase 1 architecture and methodology are complete (4 iterations + corpus
discovery). Five candidate Phase 1 polish moves are listed in
`results/iter3_notes.md`; none are architectural.

Phase 2 (writer-loop or spec → arch → impl) is the next research target.
Will require a new corpus, but test-based eval makes that lighter than the
Phase 1 rubric authoring.

## Ground rules (preserved from kickoff)

1. **Eval-first.** Iterate against the corpus every change. Don't tune
   prompts without re-running the eval.
2. **Run the ablation.** Always score reviewer-only alongside
   reviewer+arbiter. If the arbiter isn't adding signal, the architecture
   is wrong.
3. **Don't expand the corpus to fit the agent.** If the agent is failing
   on Priya-flavored bugs, fix the agent. Don't make the bugs more
   obvious. (We extended this in iter4 — when the agent catches a bug the
   rubric mislabeled, document the discovery; do not silently rewrite the
   corpus.)
4. **Bailout.** If iteration becomes vibes-only (eval not discriminating
   between prompt variants), bailout is mutation testing where eval is
   automatic.
