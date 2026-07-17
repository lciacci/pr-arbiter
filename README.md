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
(writer + reviewer + arbiter on code-from-spec), directionally
replicates the Phase 1 effect but far more weakly once tested for
variance. The iter1 run (single seed) reported an 11/13 vs 11/13 tie
with a clean narrative swap — multi-agent fixing `task_007` and
breaking `task_013`. **iter2/iter3 re-ran both arms across 3 seeds
and that narrative didn't hold**: under variance, multi-agent beats
writer-alone by 2 tasks across 39 runs, and both `task_007` and
`task_013` flip outcome depending on seed with no stable winner.

| mode (Phase 2, 3-seed variance) | pass rate (39 runs) |
|----------------------------------|---------------------:|
| writer-alone (arm A)             | 32/39 (82.1%) |
| writer + reviewer + arbiter (arm B) | 34/39 (87.2%) |

**Same direction as Phase 1 — multi-agent still wins — but the
margin is roughly half what the single-seed iter1 report suggested.**
The load-bearing Phase 2 finding is bounding that effect size under
proper variance, not confirming the architecture works. See
[PHASE_2_FINAL.md](PHASE_2_FINAL.md) for the full analysis, including
a reusable typed-finding schema (0 contaminated findings across 551
checked) and why underspec convergence looks information-bounded
rather than architecture-bounded — the motivation for the (currently
paused) Phase 3 design.

See [SUMMARY.md](SUMMARY.md) and [PHASE_2_FINAL.md](PHASE_2_FINAL.md)
for the full writeups, or [docs/promo/index.html](docs/promo/index.html)
(live at [houseofyeti.com/pr-arbiter](https://houseofyeti.com/pr-arbiter))
for an interactive overview of both phases.

## Cohesion

pr-arbiter is the **pattern** layer in the Conclave / Tessera / pr-arbiter
cohesion contract — the multi-role union-recall review workflow (Conclave =
substrate, Tessera = policy). Its lane, the anti-conflation guards
(union-recall ≠ select-best; ROLE diversity ≠ MODEL diversity; the numbers are
thin), and its seam contributions live in **[docs/INTEGRATION.md](docs/INTEGRATION.md)**.
Canonical contract: `../tessera/docs/contracts/three-project-cohesion.md`
(Tessera-hosted; if it and the stub disagree, canonical wins). Full integration
(→ Tessera's `/arbiter` on Conclave's fleet) is ADR-gated — nothing to wire today.

## Quick links

- [docs/promo/index.html](docs/promo/index.html) — interactive promo page: architecture tabs, iteration journey, worked examples. Live at [houseofyeti.com/pr-arbiter](https://houseofyeti.com/pr-arbiter).
- [docs/index.html](docs/index.html) — earlier static one-pager (Phase 1 + Phase 2 iter1 numbers only, not updated with the iter2/iter3 variance result above). Kept for reference, not deployed.

**Phase 2 (most recent):**
- [PHASE_2_FINAL.md](PHASE_2_FINAL.md) — canonical Phase 2 writeup: 3-iteration, 3-seed variance result, typed-finding schema, and the Phase 3 motivation.
- [PHASE_2_SUMMARY.md](PHASE_2_SUMMARY.md), [PHASE_2_ITER2_SUMMARY.md](PHASE_2_ITER2_SUMMARY.md), [PHASE_2_ITER3_SUMMARY.md](PHASE_2_ITER3_SUMMARY.md) — per-iteration writeups, preserved for reproducibility (iter1's single-seed narrative is superseded by PHASE_2_FINAL.md; read alongside it).
- [results/phase2/iter1_notes.md](results/phase2/iter1_notes.md) — iter 1 deep dive, full trajectories for `task_007` and `task_013` (the effects later shown to be single-seed, not stable).
- [phase2_corpus/README.md](phase2_corpus/README.md) — corpus structure and task selection rationale.
- [docs/PHASE_2_HANDOFF.md](docs/PHASE_2_HANDOFF.md) — original Phase 2 design doc.

**Phase 3 (design complete, paused):** a coherence-dimension review
architecture (real PRs + maintainer comments, not planted bugs) is
designed and ratified but not implemented — it's blocked on an 8-15
hour senior-annotator pilot. See
[docs/PHASE_3_RESUMPTION.md](docs/PHASE_3_RESUMPTION.md) for exact
status and next action, [docs/PHASE_3_DESIGN.md](docs/PHASE_3_DESIGN.md)
for the design, and [results/phase3/corpus_pilot.md](results/phase3/corpus_pilot.md)
for the corpus-viability probe.

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

Reviewer and arbiter are language-agnostic: the prompt derives its
code-fence label from the file extension (`agents.lang_fence`), so
non-Python diffs review fine even though the corpus itself is Python.
`eval/review_pr.py` is a small dogfooding script that runs this
pipeline outside the corpus, against this repo's own PR diffs.

This is a stepping-stone POC. Phase 2 closed the writer loop; Phase 3
(design complete, currently paused — see Quick links above) is the
next step toward spec → architecture → implementation.

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
  __init__.py              # lang_fence: extension -> code-fence label (multi-language support)
  reviewer.py               # Phase 1 PR reviewer
  arbiter.py                # Phase 1 independent arbiter
  triage.py                 # Phase 1 mutual-triage voices
  writer.py                 # Phase 2 writer agent
  writer_reviewer.py        # Phase 2 reviewer (code-attempt vs spec)
  writer_arbiter.py         # Phase 2 arbiter (latest-attempt independent pass)
  writer_reviewer_typed.py  # Phase 2 iter2+: typed finding schema (spec-violation vs spec-interpretation)
  writer_arbiter_typed.py   # Phase 2 iter2+: typed-schema arbiter
corpus/                  # 20 PRs with rubrics + Flask 3.0.0 source (Phase 1)
phase2_corpus/           # 13 tasks with deterministic tests (Phase 2)
eval/
  harness.py             # Phase 1: load_agent_input, load_rubric, score_pr
  run_baseline.py        # Phase 1: reviewer-only or reviewer+arbiter pipeline
  run_triage.py          # Phase 1: iter3 mutual-triage runner
  show_results.py        # Phase 1: side-by-side dashboard
  review_pr.py           # dogfood: run reviewer+arbiter on this repo's own PR diff
  sandbox.py             # Phase 2: tmpdir + pytest subprocess + pass-count parse
  writer_loop.py         # Phase 2: per-task loop driver
  phase2_harness.py      # Phase 2: corpus runner + summarize
  aggregate_iter2.py, aggregate_iter3.py  # Phase 2 iter2/iter3: 3-seed variance aggregators
migrations/              # one-off corpus rubric migrations (e.g. severity-tier promotion)
docs/
  index.html             # earlier static one-pager (Phase 1 + Phase 2 iter1 only; not deployed)
  promo/index.html       # interactive promo page — deployed at houseofyeti.com/pr-arbiter
  PERSONAS.md            # Phase 1 corpus authoring reference (NEVER read by agents)
  PHASE_2_HANDOFF.md, PHASE_2_ITER2_HANDOFF.md  # Phase 2 design docs
  PHASE_3_DESIGN.md, PHASE_3_DESIGN_REVIEW.md, PHASE_3_RESUMPTION.md  # Phase 3 design + status
  IMPROVEMENTS.md        # backlog notes (SQL-review false-positive/noise-floor fixes)
results/
  baseline_notes.md ... iter4_corpus_discovery.md  # Phase 1 iterations
  pr_009_worked_example.md                          # Phase 1 critical catch
  phase2/
    writer-alone/, writer_reviewer_arbiter/          # Phase 2 iter1 per-task JSON
    iter2/, iter3/                                    # Phase 2 iter2/iter3: 3-seed × arm JSON + aggregates
    *_summary.json                                    # Phase 2 iter1 aggregates
    iter1_notes.md                                    # Phase 2 iter 1 deep dive
  phase3/
    corpus_pilot.md                                   # Phase 3 corpus-viability probe (no code)
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

The corpus is synthetic: every PR is a deliberately planted-bug
before/after pair, not a real Flask history. That includes planted
fake secrets — e.g. `corpus/pr_001` hardcodes a fabricated
`sk_live_...`-style token as a "hardcoded credential" test case. It is
not a real key and does not correspond to any live account; it exists
so the reviewer/arbiter can be scored on whether they catch it.

## Status

**Phase 1 (PR review):** complete. 4 iterations + corpus discovery.
Five candidate polish moves listed in `results/iter3_notes.md`; none
are architectural.

**Phase 2 (writer-loop):** complete. 3 iterations across 2 months —
iter1 (single-seed baseline), iter2 (3-seed variance + typed-finding
schema), iter3 (2×2 factorial on writer-prompt/ranking variants).
Canonical result in `PHASE_2_FINAL.md`: the Phase 1 architectural
effect replicates directionally but at roughly half the magnitude
the single-seed iter1 run suggested, and the specific iter1 narrative
(`task_007` win / `task_013` loss) didn't hold up under variance.
Motivates Phase 3.

**Phase 3 (coherence-dimension review):** design complete and
ratified, implementation paused. Blocked on an 8-15 hour
senior-annotator pilot (see `docs/PHASE_3_RESUMPTION.md` for exact
status and next action). No corpus has been built and no code has
been written for this phase yet.

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
