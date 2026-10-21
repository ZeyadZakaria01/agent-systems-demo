"""Test setup: the baseline's MiniLM model comes from the shared fastembed cache (no network)."""

import os

from demo.paths import SHARED_ROOT

os.environ.setdefault("FASTEMBED_CACHE_PATH", str(SHARED_ROOT / ".cache" / "fastembed"))

import pytest

# A git hook runs with the committing repository's locators in the environment (`GIT_INDEX_FILE`, ...). The tests that
# build throwaway repositories would then stage and commit into the real one, so each test starts without them.
_GIT_LOCATORS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_NAMESPACE",
)


@pytest.fixture(autouse=True)
def _no_git_hook_environment(monkeypatch):
    for name in _GIT_LOCATORS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(scope="session", autouse=True)
def _real_repository_untouched():
    """A leak once set `core.bare` and a test identity in the real config and moved HEAD to a fixture branch."""
    from demo.paths import REPO_ROOT
    from tests.repo_guard import repo_fingerprint

    before = repo_fingerprint(REPO_ROOT)
    yield
    after = repo_fingerprint(REPO_ROOT)
    changed = [part for part in before if before[part] != after[part]]
    assert not changed, f"the suite changed the real repository's {', '.join(changed)} ({REPO_ROOT})"
