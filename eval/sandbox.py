"""
Sandbox runner for Phase 2: write writer's code to a tmpdir, run pytest
against the task's tests.py, parse pass/fail counts.

The writer never sees test names, inputs, expected values, or tracebacks.
The harness gets the full pytest output for debugging; only a binary
pass-count signal is fed back into the writer loop.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

CORPUS_DIR = Path(__file__).parent.parent / "phase2_corpus"


@dataclass
class TestResult:
    passed: int
    failed: int
    errors: int
    total: int
    all_passed: bool
    raw_stdout: str = ""  # for harness logs / debugging only — NEVER fed to writer
    raw_stderr: str = ""
    failure_summaries: list[dict] = field(default_factory=list)  # for reviewer/arbiter context if we choose to share
    timed_out: bool = False
    crashed: bool = False


def run_tests(task_id: str, code: str, timeout_s: int = 30) -> TestResult:
    """Run a task's tests against a candidate solution.

    :param task_id: directory under phase2_corpus/, e.g. "task_001".
    :param code: full contents of the candidate solution.py.
    :param timeout_s: wall-clock cap. Some tasks (rate limiter) sleep briefly.
    :returns: TestResult with pass/fail counts and raw output.
    """
    task_dir = CORPUS_DIR / task_id
    if not task_dir.is_dir():
        raise FileNotFoundError(f"unknown task: {task_id}")

    with tempfile.TemporaryDirectory(prefix=f"pr-arbiter-{task_id}-") as tmp:
        tmp_path = Path(tmp)
        shutil.copy(task_dir / "tests.py", tmp_path / "tests.py")
        (tmp_path / "solution.py").write_text(code)
        report_path = tmp_path / "report.json"

        try:
            proc = subprocess.run(
                [
                    _python(),
                    "-m",
                    "pytest",
                    "tests.py",
                    "--json-report",
                    f"--json-report-file={report_path}",
                    "-q",
                    "--no-header",
                    "--tb=short",
                ],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired as e:
            return TestResult(
                passed=0,
                failed=0,
                errors=0,
                total=0,
                all_passed=False,
                raw_stdout=(e.stdout or "") if isinstance(e.stdout, str) else "",
                raw_stderr=f"TIMEOUT after {timeout_s}s",
                timed_out=True,
            )

        if not report_path.exists():
            # pytest crashed before collection (e.g., import error in solution)
            return TestResult(
                passed=0,
                failed=0,
                errors=0,
                total=0,
                all_passed=False,
                raw_stdout=proc.stdout,
                raw_stderr=proc.stderr,
                crashed=True,
            )

        report = json.loads(report_path.read_text())
        summary = report.get("summary", {})
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        errors = summary.get("error", 0)
        total = summary.get("total", 0)

        failure_summaries: list[dict] = []
        for t in report.get("tests", []):
            if t.get("outcome") in ("failed", "error"):
                failure_summaries.append(
                    {
                        "nodeid": t.get("nodeid"),
                        "outcome": t.get("outcome"),
                        "longrepr": (t.get("call") or {}).get("longrepr"),
                    }
                )

        # Collection failure: pytest couldn't import tests.py because solution
        # is missing the expected symbol or has a syntax error. exitcode 2 from
        # pytest = collection or usage error; total stays 0. Surface as crashed
        # so the writer-loop knows nothing ran, not "0/0 trivially clean".
        collection_failed = False
        if total == 0 and proc.returncode != 0:
            collection_failed = True
            for c in report.get("collectors", []):
                if c.get("outcome") == "failed":
                    failure_summaries.append(
                        {
                            "nodeid": c.get("nodeid"),
                            "outcome": "collection-error",
                            "longrepr": c.get("longrepr"),
                        }
                    )

        return TestResult(
            passed=passed,
            failed=failed,
            errors=errors,
            total=total,
            all_passed=(total > 0 and failed == 0 and errors == 0),
            raw_stdout=proc.stdout,
            raw_stderr=proc.stderr,
            failure_summaries=failure_summaries,
            crashed=collection_failed,
        )


def _python() -> str:
    """Path to the venv python so pytest + plugins resolve correctly."""
    venv_py = Path(__file__).parent.parent / ".venv" / "bin" / "python"
    return str(venv_py) if venv_py.exists() else "python3"


if __name__ == "__main__":
    import sys

    task = sys.argv[1] if len(sys.argv) > 1 else "task_001"
    code = (CORPUS_DIR / task / "solution.py").read_text()
    result = run_tests(task, code)
    print(f"{task}: passed={result.passed}/{result.total} failed={result.failed} errors={result.errors} all_passed={result.all_passed}")
    if not result.all_passed:
        print("STDOUT:", result.raw_stdout[-500:])
        print("STDERR:", result.raw_stderr[-500:])
