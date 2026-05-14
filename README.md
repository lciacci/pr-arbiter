# pr-arbiter

Multi-agent dynamics for code review (Phase 1) and code generation
(Phase 2). A POC measuring whether reviewer + independent arbiter
architecture beats a single-agent baseline on two different surfaces.

**Phase 1 headline:** the multi-agent system (reviewer + independent
arbiter + mutual triage) catches a critical security bug (regex-based
HTML sanitization on `pr_009`) that the best single-agent reviewer
misses across every prompt variant tried. Comparable precision, fewer
false positives, two-tier output (blocking + advisory).

| configuration                              | recall | precision | FP | critical recall | neg-ctrl |
|--------------------------------------------|-------:|----------:|---:|----------------:|---------:|
| best single-agent (v2 reviewer-alone)      |  52.7% |     60.4% | 19 |   6/8 (75%)     |   1/3    |
| **multi-agent blocking-tier (iter3)**      |  43.6% | **58.5%** | **17** | **7/8 (88%)** | **1/3**  |

**Phase 2 headline:** the same architecture, ported to a writer-loop
(writer + reviewer + arbiter on code-from-spec), ties on aggregate
(11/13 each) but swaps a medium-difficulty win for an underspec loss.
Multi-agent fixes a stuck correctness bug on `task_007`; multi-agent
arbiter pushes the writer in the wrong direction on `task_013`.
**Same tradeoff as Phase 1: helps with correctness, hurts on
ambiguity.** Architectural finding holds across both surfaces.

| mode (Phase 2)              | pass rate | test recall | avg iter | wall |
|-----------------------------|----------:|------------:|---------:|-----:|
| writer-alone (ablation)     | 11/13 (84.6%) | 193/197 (98.0%) | 1.46 | 413s |
| writer + reviewer + arbiter | 11/13 (84.6%) | 192/197 (97.5%) | 1.46 | 615s |

See [SUMMARY.md](SUMMARY.md) and [PHASE_2_SUMMARY.md](PHASE_2_SUMMARY.md)
for the full writeups, or [docs/index.html](docs/index.html) for a
one-page visual overview of both phases.

## Quick links

- [docs/index.html](docs/index.html) — visual one-pager covering both phases (open in a browser).

**Phase 2 (most recent):**
- [PHASE_2_SUMMARY.md](PHASE_2_SUMMARY.md) — Phase 2 writeup, design choices, results, worked examples.
- [results/phase2/iter1_notes.md](results/phase2/iter1_notes.md) — iter 1 deep dive, full trajectories for `task_007` (win) and `task_013` (loss).
- [docs/PHASE_2_ITER2_HANDOFF.md](docs/PHASE_2_ITER2_HANDOFF.md) — iter 2 implementation brief (three-arm variance + finding-type schema). Drop into a fresh session to kick off.
- [phase2_corpus/README.md](phase2_corpus/README.md) — corpus structure and task selection rationale.
- [docs/PHASE_2_HANDOFF.md](docs/PHASE_2_HANDOFF.md) — original Phase 2 design doc.

**Phase 1:**
- [SUMMARY.md](SUMMARY.md) — project writeup, all iterations, methodology.
- [results/pr_009_worked_example.md](results/pr_009_worked_example.md) — step-by-step on the critical catch.
- [results/iter3_notes.md](results/iter3_notes.md) — most recent iteration.
- [results/iter4_corpus_discovery.md](results/iter4_corpus_discovery.md) — the agent caught a real bug the rubric mislabeled.

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
agents/
  reviewer.py            # Phase 1 PR reviewer
  arbiter.py             # Phase 1 independent arbiter
  triage.py              # Phase 1 mutual-triage voices
  writer.py              # Phase 2 writer agent
  writer_reviewer.py     # Phase 2 reviewer (code-attempt vs spec)
  writer_arbiter.py      # Phase 2 arbiter (latest-attempt independent pass)
corpus/                  # 20 PRs with rubrics + Flask 3.0.0 source (Phase 1)
phase2_corpus/           # 13 tasks with deterministic tests (Phase 2)
eval/
  harness.py             # Phase 1: load_agent_input, load_rubric, score_pr
  run_baseline.py        # Phase 1: reviewer-only or reviewer+arbiter pipeline
  run_triage.py          # Phase 1: iter3 mutual-triage runner
  show_results.py        # Phase 1: side-by-side dashboard
  sandbox.py             # Phase 2: tmpdir + pytest subprocess + pass-count parse
  writer_loop.py         # Phase 2: per-task loop driver
  phase2_harness.py      # Phase 2: corpus runner + summarize
docs/
  index.html             # visual one-page summary (both phases)
  PERSONAS.md            # Phase 1 corpus authoring reference (NEVER read by agents)
  PHASE_2_HANDOFF.md     # Phase 2 design doc
results/
  baseline_notes.md ... iter4_corpus_discovery.md  # Phase 1 iterations
  pr_009_worked_example.md                          # Phase 1 critical catch
  phase2/
    writer-alone/                                   # Phase 2 per-task JSON (ablation)
    writer_reviewer_arbiter/                        # Phase 2 per-task JSON (multi-agent)
    *_summary.json                                  # Phase 2 aggregates
    iter1_notes.md                                  # Phase 2 iter 1 deep dive
```

## Running it

Requires Python 3.13+ (for PEP 604 `X | None` syntax in Phase 2
solutions) and an `ANTHROPIC_API_KEY` set in `.env` at repo root.

```bash
# Set up (once)
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt pytest pytest-json-report
```

### Phase 1 (PR review)

```bash
# Run reviewer-alone over all 20 PRs (~3 min)
.venv/bin/python eval/run_baseline.py

# Run reviewer + independent arbiter (~5 min)
.venv/bin/python eval/run_baseline.py --with-arbiter

# Run iter3 mutual triage over a prior iter2 output (~3 min)
.venv/bin/python eval/run_triage.py --source results/iter2_20260513.json

# View all Phase 1 configurations side-by-side
.venv/bin/python eval/show_results.py
```

### Phase 2 (writer-loop)

```bash
# Ablation arm: writer + binary pass-count signal only (~7 min)
.venv/bin/python eval/phase2_harness.py writer-alone 3

# Multi-agent arm: writer + reviewer + arbiter (~10 min)
.venv/bin/python eval/phase2_harness.py writer+reviewer+arbiter 3

# Single-task quick test
.venv/bin/python eval/writer_loop.py task_007 writer+reviewer+arbiter 3
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

**Phase 1 (PR review):** complete. 4 iterations + corpus discovery.
Five candidate polish moves listed in `results/iter3_notes.md`; none
are architectural.

**Phase 2 (writer-loop):** iter 1 complete. Corpus (13 tasks, 197
tests), sandbox, writer + reviewer + arbiter agents, ablation arm
all built and run. Headline finding: Phase 1 architectural tradeoff
generalizes to code generation. Three candidate iter 2 directions
listed in `results/phase2/iter1_notes.md` (confidence tagging in
reviewer tool schema, variance run, mutual-triage analog).

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
