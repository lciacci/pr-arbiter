"""
Eval harness for pr-arbiter.

Design invariant: agent input and rubric loading are separate functions.
Nothing that loads the rubric is reachable from anything that constructs
agent input. This prevents accidental leakage of expected findings, persona
info, or arbiter notes into the agents.

Layout:
- load_agent_input(pr_id) -> dict with before/after/diff/lang. Used by runners.
- load_rubric(pr_id) -> dict with expected_findings, etc. Used only by score().
- run_eval(agent_callable) -> per-PR scores aggregated.

The agent_callable receives only what load_agent_input returns. It must
return a list of findings in the same shape as expected_findings (minus
the 'id' field, which we don't expect agents to reproduce).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from agents import lang_fence

CORPUS_DIR = Path(__file__).parent.parent / "corpus"


# ---------- AGENT-FACING ----------

def load_agent_input(pr_id: str) -> dict:
    """Load the diff and source files for an agent.

    This function MUST NOT read rubric.json. Anything that needs the rubric
    must go through load_rubric() instead. Keeping these paths separate is
    the only thing preventing accidental contamination of agent context with
    expected findings.
    """
    pr_dir = CORPUS_DIR / pr_id
    # Any single-extension before.*/after.* pair; corpus is .py today but the
    # loader no longer hardcodes it. before.* and after.* must share an ext.
    after = next(p for p in sorted(pr_dir.glob("after.*")) if p.suffix != ".patch")
    before = pr_dir / f"before{after.suffix}"
    return {
        "pr_id": pr_id,
        "before": before.read_text(),
        "after": after.read_text(),
        "diff": (pr_dir / "diff.patch").read_text(),
        "lang": lang_fence(after.name),
    }


# ---------- SCORING-FACING ----------

def load_rubric(pr_id: str) -> dict:
    """Load the rubric for scoring. NEVER call this from agent code paths."""
    return json.loads((CORPUS_DIR / pr_id / "rubric.json").read_text())


def list_pr_ids() -> list[str]:
    """Return all PR IDs from the manifest."""
    manifest = json.loads((CORPUS_DIR / "manifest.json").read_text())
    return [pr["id"] for pr in manifest["prs"]]


# ---------- SCORING ----------

@dataclass
class PRScore:
    pr_id: str
    persona: str
    category: str
    expected: int
    matched: int  # findings the agent caught (approximate match)
    missed: list[str] = field(default_factory=list)  # finding ids missed
    false_positives: int = 0  # agent findings with no expected match
    notes: list[str] = field(default_factory=list)
    # Per-severity tallies — populated by score_pr. Critical is tracked
    # separately because missing a critical is qualitatively worse than
    # missing a high.
    expected_by_severity: dict[str, int] = field(default_factory=dict)
    matched_by_severity: dict[str, int] = field(default_factory=dict)


def _approximate_match(agent_finding: dict, expected: dict, line_tolerance: int = 3) -> bool:
    """Approximate match: same file, line within ±3, same category.

    Deliberately loose. We don't require exact line numbers because rubric
    line numbers are best-effort and not worth manual verification across
    20 PRs. Category match is the primary signal; line proximity is a tiebreaker.
    """
    if agent_finding.get("file") != expected.get("file"):
        return False
    if agent_finding.get("category") != expected.get("category"):
        return False
    a_lines = agent_finding.get("line_range", [0, 0])
    e_lines = expected.get("line_range", [0, 0])
    a_mid = (a_lines[0] + a_lines[1]) / 2
    e_mid = (e_lines[0] + e_lines[1]) / 2
    return abs(a_mid - e_mid) <= line_tolerance


def score_pr(pr_id: str, agent_findings: list[dict]) -> PRScore:
    """Score one PR's agent output against its rubric."""
    rubric = load_rubric(pr_id)
    expected = rubric["expected_findings"]
    score = PRScore(
        pr_id=pr_id,
        persona=rubric["persona"],
        category=rubric["category"],
        expected=len(expected),
        matched=0,
    )

    # Pre-tally expected severities so negative controls show up cleanly too
    for e in expected:
        sev = e.get("severity", "unknown")
        score.expected_by_severity[sev] = score.expected_by_severity.get(sev, 0) + 1

    used_agent_findings: set[int] = set()
    for e in expected:
        match_idx = None
        for i, a in enumerate(agent_findings):
            if i in used_agent_findings:
                continue
            if _approximate_match(a, e):
                match_idx = i
                break
        if match_idx is not None:
            score.matched += 1
            used_agent_findings.add(match_idx)
            sev = e.get("severity", "unknown")
            score.matched_by_severity[sev] = score.matched_by_severity.get(sev, 0) + 1
        else:
            score.missed.append(e["id"])

    score.false_positives = len(agent_findings) - len(used_agent_findings)
    return score


# ---------- RUNNER ----------

AgentFn = Callable[[dict], list[dict]]


def run_eval(reviewer: AgentFn, arbiter: AgentFn | None = None, pr_ids: list[str] | None = None) -> list[PRScore]:
    """Run an eval pass over the corpus.

    :param reviewer: callable taking load_agent_input output, returning findings.
    :param arbiter: optional callable taking (agent_input, reviewer_output)
        and returning triaged findings. If None, the reviewer output is scored
        directly (useful for ablation: is the arbiter adding value?).
    :param pr_ids: subset to run; defaults to all.
    """
    pr_ids = pr_ids or list_pr_ids()
    scores: list[PRScore] = []
    for pr_id in pr_ids:
        agent_input = load_agent_input(pr_id)
        reviewer_out = reviewer(agent_input)
        if arbiter is not None:
            final = arbiter({**agent_input, "reviewer_findings": reviewer_out})
        else:
            final = reviewer_out
        scores.append(score_pr(pr_id, final))
    return scores


def summarize(scores: list[PRScore]) -> dict:
    """Aggregate scores. Reports overall recall AND per-severity recall.

    Critical recall is reported separately rather than weighted into a
    single score — missing a critical is qualitatively different from
    missing a low, and a single weighted number hides that.
    """
    total_expected = sum(s.expected for s in scores)
    total_matched = sum(s.matched for s in scores)
    total_fp = sum(s.false_positives for s in scores)
    total_agent = total_matched + total_fp

    by_persona: dict[str, dict] = {}
    for s in scores:
        p = by_persona.setdefault(s.persona, {"expected": 0, "matched": 0, "fp": 0})
        p["expected"] += s.expected
        p["matched"] += s.matched
        p["fp"] += s.false_positives

    # Per-severity recall. Missing severities (e.g., a corpus with no
    # criticals yet) appear with expected=0 and recall=None.
    by_severity: dict[str, dict] = {}
    for s in scores:
        for sev, n in s.expected_by_severity.items():
            row = by_severity.setdefault(sev, {"expected": 0, "matched": 0})
            row["expected"] += n
        for sev, n in s.matched_by_severity.items():
            row = by_severity.setdefault(sev, {"expected": 0, "matched": 0})
            row["matched"] += n
    for sev, row in by_severity.items():
        row["recall"] = row["matched"] / row["expected"] if row["expected"] else None

    # Negative-control failure rate: PRs with expected=0 where the agent
    # produced any findings. Inverse of precision on the noise dimension.
    nc_scores = [s for s in scores if s.expected == 0]
    nc_failures = sum(1 for s in nc_scores if s.false_positives > 0)

    return {
        "overall": {
            "recall": total_matched / total_expected if total_expected else 0.0,
            "precision": total_matched / total_agent if total_agent else 0.0,
            "expected": total_expected,
            "matched": total_matched,
            "false_positives": total_fp,
        },
        "by_severity": by_severity,
        "by_persona": by_persona,
        "negative_controls": {
            "total": len(nc_scores),
            "failures": nc_failures,
            "failure_rate": nc_failures / len(nc_scores) if nc_scores else 0.0,
        },
    }


if __name__ == "__main__":
    # Smoke test: load every PR's agent input and rubric independently.
    ids = list_pr_ids()
    print(f"Found {len(ids)} PRs in corpus.")
    for pr_id in ids:
        ai = load_agent_input(pr_id)
        rb = load_rubric(pr_id)
        print(f"  {pr_id}  persona={rb['persona']}  expected={len(rb['expected_findings'])}  diff_lines={len(ai['diff'].splitlines())}")
