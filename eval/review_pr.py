"""
Dogfood: run Phase 1 reviewer + arbiter against the Phase 2 PR diff.

For each new or modified Python file in this branch vs main, assemble
the (before, after, diff) tuple the Phase 1 agents expect and feed it
through reviewer + arbiter. Persist findings as markdown.

Intentional limitations:
- Per-file reviews. The Phase 1 agents were trained on corpus PRs which
  are single-file. Multi-file context is not given to either agent.
- Skips markdown, JSON, HTML. The agents review code.
- Uses Phase 1 agents/reviewer.py + agents/arbiter.py unchanged. The
  prompts are tuned for "review a code change" — fine for new files
  (before is empty) as well as modified files.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import find_dotenv, load_dotenv

from agents.arbiter import arbitrate, merge_findings
from agents.reviewer import review

REVIEWABLE_EXTS = {".py"}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout


def changed_files(base: str = "main") -> list[tuple[str, str]]:
    """Return [(status, path)] for files changed in HEAD vs base.

    status is A (added), M (modified), D (deleted), etc.
    """
    out = git("diff", "--name-status", f"{base}..HEAD")
    rows = []
    for line in out.splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        rows.append((parts[0], parts[1]))
    return rows


def file_content_at(ref: str, path: str) -> str:
    """Return file contents at a git ref, or empty string if missing."""
    try:
        return git("show", f"{ref}:{path}")
    except subprocess.CalledProcessError:
        return ""


def file_diff(base: str, path: str) -> str:
    return git("diff", f"{base}..HEAD", "--", path)


def assemble_agent_input(status: str, path: str, base: str = "main") -> dict:
    before = "" if status == "A" else file_content_at(base, path)
    after = file_content_at("HEAD", path)
    diff = file_diff(base, path)
    return {
        "pr_id": path,
        "before": before,
        "after": after,
        "diff": diff,
    }


def main() -> None:
    load_dotenv(find_dotenv(), override=True)

    base = sys.argv[1] if len(sys.argv) > 1 else "main"
    out_path = ROOT / "results" / "phase2" / "pr_review.md"

    files = changed_files(base)
    reviewable = [
        (s, p)
        for s, p in files
        if s != "D" and Path(p).suffix in REVIEWABLE_EXTS
    ]

    print(f"PR base: {base}")
    print(f"Total changed: {len(files)}  reviewable .py: {len(reviewable)}")
    print()

    per_file: list[dict] = []
    for i, (status, path) in enumerate(reviewable, start=1):
        print(f"[{i}/{len(reviewable)}] {status} {path} ...", flush=True)
        agent_input = assemble_agent_input(status, path, base=base)

        rev = review(agent_input)
        arb = arbitrate({**agent_input, "reviewer_findings": rev})
        merged = merge_findings(rev, arb)

        per_file.append(
            {
                "status": status,
                "path": path,
                "reviewer": rev,
                "arbiter": arb,
                "merged": merged,
            }
        )
        print(f"    rev={len(rev)}  arb={len(arb)}  merged={len(merged)}", flush=True)

    render_markdown(per_file, out_path, base=base)
    print(f"\nWrote {out_path.relative_to(ROOT)}")


def render_markdown(per_file: list[dict], out_path: Path, base: str = "main") -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    total_findings = sum(len(f["merged"]) for f in per_file)
    by_sev: dict[str, int] = {}
    for f in per_file:
        for finding in f["merged"]:
            sev = finding.get("severity", "?")
            by_sev[sev] = by_sev.get(sev, 0) + 1

    lines = [
        f"# Phase 2 PR — agent review",
        "",
        f"Phase 1 reviewer + arbiter run against the Phase 2 PR (`HEAD` vs `{base}`).",
        f"Per-file reviews. Findings merged across reviewer + arbiter with",
        f"approximate-match dedup.",
        "",
        f"## Summary",
        "",
        f"- Files reviewed: **{len(per_file)}** Python files",
        f"- Total merged findings: **{total_findings}**",
    ]
    for sev in ("critical", "high", "medium", "low"):
        if sev in by_sev:
            lines.append(f"- {sev}: {by_sev[sev]}")
    lines.append("")

    for f in per_file:
        lines.append(f"## `{f['path']}` ({f['status']})")
        lines.append("")
        if not f["merged"]:
            lines.append("_No findings._")
            lines.append("")
            continue
        sorted_findings = sorted(
            f["merged"], key=lambda x: (sev_rank.get(x.get("severity", ""), 9), x.get("line_range", [0])[0])
        )
        for finding in sorted_findings:
            lr = finding.get("line_range", [0, 0])
            sev = finding.get("severity", "?")
            cat = finding.get("category", "?")
            desc = finding.get("description", "")
            rat = finding.get("rationale", "")
            lines.append(f"### [{sev}/{cat}] lines {lr[0]}–{lr[1]}")
            lines.append("")
            lines.append(desc)
            if rat:
                lines.append("")
                lines.append(f"_Rationale:_ {rat}")
            lines.append("")
        lines.append("---")
        lines.append("")

    out_path.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
