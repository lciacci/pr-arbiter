# pr-arbiter

A reviewer + arbiter multi-agent system for code review. Phase 1 of a multi-agent software development POC.

## What this is

Two agents:
- **Reviewer** hunts for security issues, correctness bugs, missing tests, and style violations in PR diffs. Tuned to be adversarial without going unhinged.
- **Arbiter** triages the reviewer's findings into blocking issues, non-blocking suggestions, and nitpicks to drop. Does not just split the difference.

Input: a PR diff (before/after pair).
Output: a triaged code review.

This is a stepping-stone POC. Phase 2 will close the writer loop or pivot to spec → architecture → implementation using the patterns learned here.

## Why agents, not just a prompt

A single-pass review with a good prompt covers most of what the reviewer does. The interesting question is whether the arbiter adds signal — i.e., whether agent-to-agent dynamics produce better triage than self-critique. The eval harness supports running with and without the arbiter so this can be measured rather than assumed.

## Repo layout

```
corpus/             # 20 PRs with known ground truth (see corpus/manifest.json)
  pr_NNN/
    before.py       # original source
    after.py        # source with planted change(s)
    diff.patch      # unified diff (what the agents see)
    rubric.json     # expected findings, things-not-to-flag, persona metadata
  _source/          # clean Flask source files used to construct PRs
  manifest.json     # corpus summary
agents/             # reviewer.py, arbiter.py — to be implemented
eval/
  harness.py        # loads input, runs agents, scores against rubrics
results/            # eval outputs land here (gitignored except .gitkeep)
docs/
  PERSONAS.md       # authoring reference; NOT for agent context
```

## Corpus

20 PRs built from public Flask 3.0.0 source. Each PR is a controlled before/after pair with rubric-defined expected findings.

| Persona | Count | Bug type signature                                      |
|---------|-------|---------------------------------------------------------|
| Marcus  | 5     | Clean code, subtle semantics (races, contract bugs)     |
| Priya   | 5     | Almost-secure code (validation theater, wrong crypto)   |
| Devon   | 6     | Obvious bugs (nulls, off-by-one, secrets in logs)       |
| Alex    | 4     | Architectural mistakes, style-heavy refactors           |

Breakdown by category:
- 14 planted-bug PRs (real issues to find)
- 3 negative controls (clean refactors — should produce empty reviews)
- 3 style-heavy PRs with latent bugs (tests arbiter triage)

55 expected findings total. Severity 4-level: critical / high / medium / low.

Critical (8): exploitable security vuln, credential exposure, RCE path, or correctness bug that corrupts state.
High (11): real bug that will surface in production. Block the PR.
Medium (18): real issue worth fixing before merge.
Low (18): style, nits, non-blocking suggestions.

Personas are authoring tools. **Agents never see persona info.** See `docs/PERSONAS.md`.

## Eval design

- **Recall**: of the 55 expected findings, how many did the system catch?
- **Critical recall**: of the 8 critical findings specifically, how many caught? Reported separately because missing a critical is qualitatively worse than missing a low. No weighted-average score.
- **Precision**: of the system's findings, how many matched something in a rubric?
- **Negative control failure rate**: how often did the system flag something on a PR with `expected_findings: []`?
- **Per-persona breakdown**: slice results by persona to identify systematic blind spots.

Matching is approximate (file + category match, line within ±3). Exact line matching isn't worth the manual effort to maintain.

## Status

- [x] Project scaffolding
- [x] Corpus: 20 PRs with rubrics
- [x] Eval harness skeleton
- [x] Reviewer agent v0 + v1 (severity anchoring + correctness-critical bias)
- [x] Arbiter agent v0 + v1 (default-drop framing; overshot, see `results/iter1_notes.md`)
- [x] Baseline eval run (see `results/baseline_notes.md`)
- [x] Iter1 eval run (see `results/iter1_notes.md`) — headline: reviewer-alone wins
- [x] Iter2: independent-arbiter architecture (see `results/iter2_notes.md`) — headline: catches a critical the reviewer missed, at precision cost
- [x] Iter3: mutual-triage adversarial assessment (see `results/iter3_notes.md`) — headline: blocking-tier 7/8 critical recall at 58.5% precision; architecture vindicated
- [x] Iter4: corpus discovery — pr_007's "persistent hallucination" is a real mislabel (see `results/iter4_corpus_discovery.md`); pending corpus correction approval

## Running the eval

```bash
# Smoke test — confirms corpus loads cleanly
python eval/harness.py
```

Once `agents/reviewer.py` and `agents/arbiter.py` are implemented, point the harness at them:

```python
from eval.harness import run_eval, summarize
from agents.reviewer import review
from agents.arbiter import arbitrate

scores = run_eval(review, arbitrate)
print(summarize(scores))
```

## Ground rules

1. **Eval-first.** Iterate against the corpus every change. Don't tune prompts without re-running the eval.
2. **Run the ablation.** Always score reviewer-only alongside reviewer+arbiter. If the arbiter isn't adding signal, the architecture is wrong.
3. **Don't expand the corpus to fit the agent.** If the agent is failing on Priya-flavored bugs, fix the agent. Don't make the bugs more obvious.
4. **Bailout.** If iteration on this becomes vibes-only (eval not discriminating well between prompt variants), the bailout is to switch to mutation testing where eval is automatic.
