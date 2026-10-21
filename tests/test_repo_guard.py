"""The suite-wide guard (`tests/conftest.py`) compares the real repository's config and HEAD before and after the
run; here its fingerprint is shown to see the two changes that once leaked from a test into the real repo."""

import subprocess

from tests.repo_guard import repo_fingerprint


def git(path, *args):
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


def make_repo(tmp_path):
    path = tmp_path / "repo"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    git(path, "-c", "user.name=a", "-c", "user.email=a@b.c", "commit", "-q", "--allow-empty", "-m", "first")
    return path


def test_the_fingerprint_is_stable_when_nothing_changes(tmp_path):
    repo = make_repo(tmp_path)
    assert repo_fingerprint(repo) == repo_fingerprint(repo)


def test_a_config_write_changes_the_fingerprint(tmp_path):
    repo = make_repo(tmp_path)
    before = repo_fingerprint(repo)
    git(repo, "config", "user.email", "t@example.com")
    assert repo_fingerprint(repo) != before


def test_moving_head_changes_the_fingerprint(tmp_path):
    repo = make_repo(tmp_path)
    before = repo_fingerprint(repo)
    git(repo, "checkout", "-q", "-b", "bitemporal")
    assert repo_fingerprint(repo) != before
