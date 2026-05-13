#!/usr/bin/env python3
"""
Migration: introduce 'critical' severity tier.

Promotes 8 findings across 7 PRs from 'high' to 'critical'. Idempotent —
running twice is safe. Verifies each target finding currently has the
expected severity before promoting; aborts on mismatch so you don't
silently miss a finding that drifted.

Run from repo root:
    python migrations/001_add_critical_severity.py

Or with --dry-run to preview without writing:
    python migrations/001_add_critical_severity.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CORPUS = REPO_ROOT / "corpus"

# (pr_id, finding_id, expected current severity) — promote each to 'critical'.
PROMOTIONS = [
    ("pr_001", "F1", "high"),   # path traversal
    ("pr_001", "F2", "high"),   # hardcoded sk_live_ token
    ("pr_008", "F1", "high"),   # SQL injection
    ("pr_009", "F1", "high"),   # regex XSS sanitizer
    ("pr_010", "F1", "high"),   # timing-vuln token comparison
    ("pr_011", "F1", "high"),   # pickle on cache input
    ("pr_015", "F1", "high"),   # open email relay
    ("pr_019", "F1", "high"),   # reinvented send_from_directory
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    promoted = 0
    already_critical = 0
    errors = []

    for pr_id, finding_id, expected_current in PROMOTIONS:
        rubric_path = CORPUS / pr_id / "rubric.json"
        if not rubric_path.exists():
            errors.append(f"{pr_id}: rubric.json not found")
            continue

        rubric = json.loads(rubric_path.read_text())
        finding = next(
            (f for f in rubric["expected_findings"] if f["id"] == finding_id),
            None,
        )
        if finding is None:
            errors.append(f"{pr_id}: finding {finding_id} not found")
            continue

        current = finding["severity"]
        if current == "critical":
            already_critical += 1
            print(f"  {pr_id} {finding_id}: already critical, skipping")
            continue

        if current != expected_current:
            errors.append(
                f"{pr_id} {finding_id}: expected severity '{expected_current}', "
                f"found '{current}'. Aborting this finding."
            )
            continue

        finding["severity"] = "critical"
        promoted += 1
        print(f"  {pr_id} {finding_id}: {current} -> critical")

        if not args.dry_run:
            rubric_path.write_text(json.dumps(rubric, indent=2) + "\n")

    print()
    print(f"Promoted: {promoted}")
    print(f"Already critical (idempotent skip): {already_critical}")
    if errors:
        print(f"Errors: {len(errors)}")
        for e in errors:
            print(f"  - {e}")
        return 1
    if args.dry_run:
        print("(dry run — no files written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
