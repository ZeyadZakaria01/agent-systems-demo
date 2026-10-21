"""The pre-commit hook refuses a commit whose author or committer is a test identity (`@example.com`): 85 commits
once went in as `t <t@example.com>` after a test wrote its identity into the real config."""

import os
import subprocess

import pytest

from demo.paths import REPO_ROOT

HOOK = REPO_ROOT / ".githooks" / "pre-commit"


@pytest.fixture
def staged_repo(tmp_path):
    path = tmp_path / "repo"
    path.mkdir()
    subprocess.run(["git", "-C", str(path), "init", "-q", "-b", "main"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "-c",
            "user.name=a",
            "-c",
            "user.email=a@b.c",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "first",
        ],
        check=True,
    )
    (path / "notes.txt").write_text("x\n")
    subprocess.run(["git", "-C", str(path), "add", "notes.txt"], check=True)
    return path


def run_hook(repo, author, committer="Zeyad Zakaria <zeyad.zakaria01@gmail.com>"):
    def split(ident):
        name, email = ident[:-1].split(" <")
        return name, email

    (an, ae), (cn, ce) = split(author), split(committer)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": an,
        "GIT_AUTHOR_EMAIL": ae,
        "GIT_COMMITTER_NAME": cn,
        "GIT_COMMITTER_EMAIL": ce,
    }
    return subprocess.run(["sh", str(HOOK)], cwd=repo, env=env, capture_output=True, text=True)


def test_a_real_identity_passes(staged_repo):
    assert run_hook(staged_repo, "Zeyad Zakaria <zeyad.zakaria01@gmail.com>").returncode == 0


@pytest.mark.parametrize(
    "author, committer",
    [
        ("t <t@example.com>", "Zeyad Zakaria <zeyad.zakaria01@gmail.com>"),
        ("Zeyad Zakaria <zeyad.zakaria01@gmail.com>", "t <t@example.com>"),
    ],
)
def test_a_test_identity_is_refused_naming_it(staged_repo, author, committer):
    result = run_hook(staged_repo, author, committer)
    assert result.returncode == 1
    assert "t@example.com" in result.stderr


FAKE_KEYS = [
    "gs" + "k_" + "A1b2C3d4" * 6,
    "AI" + "za" + "Sy" + "Q9w8E7r6" * 4,
    "AQ" + ".Ab8" + "X" * 40,
    "xa" + "i-" + "Z9y8X7w6" * 4,
]


@pytest.mark.parametrize("key", FAKE_KEYS)
def test_a_staged_api_key_is_refused_without_printing_it(staged_repo, key):
    (staged_repo / "config.env").write_text(f"API_KEY={key}\n")
    subprocess.run(["git", "-C", str(staged_repo), "add", "config.env"], check=True)
    result = run_hook(staged_repo, "Zeyad Zakaria <zeyad.zakaria01@gmail.com>")
    assert result.returncode == 1
    assert "config.env" in result.stderr and key not in result.stderr


def test_text_that_only_resembles_a_key_passes(staged_repo):
    (staged_repo / "notes.txt").write_text("the task-runner and sk-learn; gsk_ prefix; AIza is Google's\n")
    subprocess.run(["git", "-C", str(staged_repo), "add", "notes.txt"], check=True)
    assert run_hook(staged_repo, "Zeyad Zakaria <zeyad.zakaria01@gmail.com>").returncode == 0
