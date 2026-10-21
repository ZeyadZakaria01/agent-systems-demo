"""MemState's upstream tests (39 of them), run at upstream and at each patch step, unedited.

The claim "the 39 tests pass unedited at every commit" needs a run behind it, so the recorded runner runs them: against
`MemState/` (upstream, which must stay byte-for-byte as it is, so the run writes no bytecode and no pytest cache and
the junit report goes to a temporary directory) and, in `MemState-patched/` with the step checked out, the same files by
name (the patch adds developer tests beside them; they are not counted). A system with any failing test, or whose
total is not 39, is flagged. Counts are carried in `results.json` under `upstream_tests` and in the scorecard.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from demo.paths import SHARED_ROOT

EXPECTED_TOTAL = 39
UPSTREAM_DIR = SHARED_ROOT / "MemState"
PATCHED_DIR = SHARED_ROOT / "MemState-patched"


@dataclass(frozen=True)
class TestCounts:
    __test__ = False  # not a pytest class
    passed: int
    failed: int  # failures and errors
    total: int
    command: str
    source_dir: str

    @property
    def flagged(self) -> bool:
        return self.failed > 0 or self.passed != self.total or self.total != EXPECTED_TOTAL

    def to_dict(self) -> dict:
        return {"passed": self.passed, "failed": self.failed, "total": self.total, "flagged": self.flagged,
                "expected_total": EXPECTED_TOTAL, "command": self.command, "source_dir": self.source_dir}


def upstream_test_files(upstream_dir: Path = UPSTREAM_DIR) -> list[str]:
    return sorted(p.name for p in (upstream_dir / "tests").glob("test_*.py"))


def count_tests(source_dir: Path, files: list[str] | None = None, patched: bool = False) -> TestCounts:
    """Run pytest in `source_dir` (on `files` under its `tests/`, default the whole folder) and count the outcomes.
    `patched` puts `source_dir/src` ahead of the editable install, which points at `MemState/src`."""
    with tempfile.TemporaryDirectory(prefix="gem-upstream-tests-") as tmp:
        report = Path(tmp) / "junit.xml"
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", MEMSTATE_KUZU_PATH=str(Path(tmp) / "t.kuzu"))
        if patched:
            env["PYTHONPATH"] = str(source_dir / "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        targets = [f"tests/{f}" for f in files] if files else ["tests"]
        argv = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={report}", *targets]
        proc = subprocess.run(argv, cwd=source_dir, env=env, capture_output=True, text=True)
        if not report.exists():
            raise RuntimeError(f"pytest in {source_dir} wrote no report (exit {proc.returncode}): "
                               f"{(proc.stderr or proc.stdout).strip()[-500:]}")
        suite = ET.parse(report).getroot()
        suite = suite if suite.tag == "testsuite" else suite.find("testsuite")
        total = int(suite.get("tests", 0))
        failed = int(suite.get("failures", 0)) + int(suite.get("errors", 0))
        skipped = int(suite.get("skipped", 0))
        command = f"cd {source_dir} && " + ("PYTHONPATH=$PWD/src " if patched else "") + "python -m pytest -q " + " ".join(targets)
        return TestCounts(passed=total - failed - skipped, failed=failed, total=total, command=command,
                          source_dir=str(source_dir))


def run_upstream(upstream_dir: Path = UPSTREAM_DIR) -> TestCounts:
    return count_tests(upstream_dir)


def run_patched(patched_dir: Path = PATCHED_DIR, upstream_dir: Path = UPSTREAM_DIR) -> TestCounts:
    """The step must be checked out already; runs upstream's 39 files by name from the patched copy."""
    return count_tests(patched_dir, upstream_test_files(upstream_dir), patched=True)


def render_upstream_tests(counts: dict[str, dict], labels: dict[str, str]) -> str:
    """`counts` maps system id to a `to_dict()` (or `{"error": ...}`); empty when no system was counted."""
    if not counts:
        return ""
    lines = [f"### MemState's {EXPECTED_TOTAL} upstream tests", "",
             "Upstream's own tests, run unedited at upstream and at each patch step (`demo/upstream_tests.py`). A step on "
             "which any of them fails is flagged.", "",
             "| System | Passed | Failed | Total | |", "|---|---|---|---|---|"]
    for system, c in counts.items():
        label = labels.get(system, system)
        if "error" in c:
            lines.append(f"| {label} | - | - | - | **FLAG: not run** ({c['error']}) |")
        else:
            lines.append(f"| {label} | {c['passed']} | {c['failed']} | {c['total']} | "
                         + ("**FLAG: not all pass**" if c["flagged"] else "all pass") + " |")
    return "\n".join(lines)
