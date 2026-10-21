"""The findings file stays citable: each finding has one number, in order, and every commit it or the report cites
resolves in this repo or in the MemState submodule (patch-step commits live only in the submodule's local objects)."""

import re
import subprocess

import pytest

from demo.paths import REPO_ROOT, SHARED_ROOT

FINDINGS = REPO_ROOT / "docs" / "findings.md"
REPORT = REPO_ROOT / "docs" / "report" / "gem-limitations-and-directions.md"
CITED_HASH = re.compile(r"`([0-9a-f]{7,40})`")
# Commits of other projects, cited from code read there; they cannot resolve here.
EXTERNAL_COMMITS = {"6e3e3cb": "Graphiti (getzep/graphiti), read for the Zep comparison"}


def finding_numbers(text: str) -> list[int | None]:
    """The number of each `## ` finding heading in file order; None for a heading with no `F<n>.` number."""
    numbers = []
    for heading in re.findall(r"^## (.*)$", text, flags=re.MULTILINE):
        match = re.match(r"F(\d+)\. ", heading)
        numbers.append(int(match.group(1)) if match else None)
    return numbers


def test_finding_numbers_reads_numbered_and_unnumbered_headings():
    assert finding_numbers("# Findings\n## F1. a\ntext\n## F2. b\n## Notes\n") == [1, 2, None]


def test_every_finding_is_numbered_once_in_order():
    numbers = finding_numbers(FINDINGS.read_text())
    assert numbers == list(range(1, len(numbers) + 1)), \
        "each `## ` heading in docs/findings.md is `F<n>. ` with n = 1, 2, 3, … in file order"


def _resolves(repo, commit: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{commit}^{{commit}}"],
                          capture_output=True).returncode == 0


@pytest.mark.parametrize("doc", [FINDINGS, REPORT], ids=["findings", "report"])
def test_every_cited_commit_resolves(doc):
    submodule = SHARED_ROOT / "MemState"
    if not _resolves(submodule, "945d7c4"):
        pytest.skip("MemState submodule not initialised")
    cited = sorted(set(CITED_HASH.findall(doc.read_text())) - EXTERNAL_COMMITS.keys())
    missing = [c for c in cited if not _resolves(REPO_ROOT, c) and not _resolves(submodule, c)]
    assert not missing, f"{doc.name} cites commits that resolve nowhere: {missing}"
