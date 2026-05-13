# Kickoff prompt — pr-arbiter session 2: agent implementation

Copy everything below the line into a fresh Claude chat.

---

**Project kickoff: pr-arbiter Phase 1 — agents v0**

Continuing implementation of a reviewer \+ arbiter multi-agent code review system. Prior session built the corpus and eval harness. This session: implement the two agents, run a baseline eval, decide where to iterate.

**Repo state (already in place at `pr-arbiter/`):**

- `corpus/` — 20 Flask 3.0.0 PRs with `before.py`, `after.py`, `diff.patch`, `rubric.json` per PR. Manifest at `corpus/manifest.json`. Persona distribution: Marcus 5, Priya 5, Devon 6, Alex 4\. Mix: 14 planted-bug, 3 negative-control, 3 style-with-latent-bug. 55 expected findings total across 4 severity tiers (critical 8 / high 11 / medium 18 / low 18). Critical recall reported separately, not weighted into a single score.  
- `eval/harness.py` — `load_agent_input(pr_id)` (returns before/after/diff only) and `load_rubric(pr_id)` (used only by scoring). `run_eval(reviewer, arbiter)` and `summarize(scores)` work. Smoke test passes.  
- `docs/PERSONAS.md` — authoring reference. **Agents never see this.** Rubric notes also contain persona color; that's fine because scoring path is isolated from agent path, but tighten if needed.  
- `agents/` — empty. This session fills it.  
- `results/` — for eval outputs.

**Hard constraints (don't violate without discussion):**

1. **Agents see diff \+ before \+ after. Nothing else.** No rubric, no persona, no PR id beyond what's needed for logging.  
2. **Run reviewer-alone before reviewer+arbiter.** This is the ablation. If the arbiter doesn't improve scores, the multi-agent architecture isn't justified — that's a real finding, not a failure.  
3. **Eval before tuning.** No prompt iteration without re-running the harness. Track scores in `results/` as JSON, one file per run.  
4. **Don't change the corpus to help the agent.** If recall is bad on Priya, fix the prompt. The corpus is ground truth.

**This session's deliverables:**

1. `agents/reviewer.py` — single Anthropic API call per PR. Input: dict from `load_agent_input()`. Output: list of findings matching the rubric finding shape (`file`, `line_range`, `category`, `severity`, `description`). Structured JSON output, parsed and validated before return.  
2. `agents/arbiter.py` — takes `{**agent_input, "reviewer_findings": [...]}`, returns a filtered/re-prioritized list in the same shape. Must be willing to drop findings, not just relabel them.  
3. Baseline eval run: reviewer-alone scores, then reviewer+arbiter scores. Write both to `results/baseline_YYYYMMDD.json`.  
4. A short `results/baseline_notes.md` — 1 page, plain prose — describing what worked, what didn't, and the next prompt iteration to try.

**Context budget — read this before starting:**

Reviewer \+ arbiter \+ 20 PRs of structured output \+ eval iteration is a lot for one session. The natural break is *after the reviewer-alone baseline runs and is logged to `results/`*. If context is getting tight at that point, stop. Write up what you have in `results/baseline_notes.md`, draft a session 3 kickoff prompt for the arbiter work, and call it done.

Signs context is getting tight: tool calls starting to feel slow, having to re-read files you already saw, or the assistant suggesting it "should summarize" without being asked. Don't try to muscle through — a clean reviewer baseline with notes is a better deliverable than a half-finished arbiter.

**Design questions to answer with me, not for me:**

1. Model choice for reviewer vs arbiter. Same model both? Different? Sonnet 4.5 for both is the simple default; consider whether Opus is justified for the arbiter (which is doing the harder judgment).  
2. Structured output mechanism. JSON mode via prompt, or tool-use schema? Tool-use is more reliable for structured output but adds a layer.  
3. How verbose should the reviewer be? Findings as terse one-liners or with rationale? Affects arbiter input quality.  
4. Should the arbiter see the diff, or only the reviewer's output? Arguments both ways — seeing the diff prevents the arbiter from being purely a re-ranker, but adds context length and cost.

**Communication preferences:** tight, direct, first-person. Push back when I'm wrong. Don't pad. No bullet lists when prose works. Treat me as senior — I'll ask if I need explanation.

**Context about me (only relevant pieces):** engineering leader rolling out Claude Code internally; this POC exists to build real multi-agent fluency for that rollout. Python and TypeScript both fine. Mac user.

**What I want from this session:**

Move from "corpus \+ harness ready" to "baseline eval results in hand, next iteration identified." Don't try to make the agents great on the first pass. The goal is to learn from the eval, not to win it.

Start by confirming you understand the scope, then propose answers to the four design questions above before writing code.  
