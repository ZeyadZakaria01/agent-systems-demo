"""The git hooks. pre-commit refuses a commit whose author or committer is a test identity (`@example.com`; 85 commits
once went in as `t <t@example.com>` after a test wrote its identity into the real config) or that adds an API key;
commit-msg strips AI attribution and refuses a subject that is not a Conventional Commit (198 unsquashed commits,
merge commits and free-form subjects once landed on main)."""

import os
import subprocess

import pytest

from demo.paths import REPO_ROOT

HOOK = REPO_ROOT / ".githooks" / "pre-commit"
COMMIT_MSG = REPO_ROOT / ".githooks" / "commit-msg"


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


def run_commit_msg(tmp_path, message: str):
    path = tmp_path / "COMMIT_EDITMSG"
    path.write_text(message)
    result = subprocess.run(["sh", str(COMMIT_MSG), str(path)], capture_output=True, text=True)
    return result, path.read_text()


@pytest.mark.parametrize(
    "subject",
    [
        "feat(checks): add the C2(a) merge check",
        "fix: repair the lock path",
        "refactor!: move run data to runs/",
        "fixup! feat(checks): add the C2(a) merge check",
    ],
)
def test_a_conventional_subject_passes(tmp_path, subject):
    assert run_commit_msg(tmp_path, f"{subject}\n\nbody\n")[0].returncode == 0


@pytest.mark.parametrize(
    "subject",
    [
        "Merge ticket 02: patch-step-1",
        "Resolve ticket 10",
        "Add C4: history survival",
        "feat:missing space",
        "feat(checks): " + "x" * 60,
    ],
)
def test_a_merge_free_form_or_long_subject_is_refused(tmp_path, subject):
    result, _ = run_commit_msg(tmp_path, f"{subject}\n")
    assert result.returncode == 1 and "commit-msg:" in result.stderr


def test_ai_attribution_is_stripped_and_a_human_co_author_kept(tmp_path):
    message = (
        "docs: add the journal\n\nbody\n\n"
        "Co-authored-by: Claude <noreply@anthropic.com>\n"
        "Co-authored-by: Essam Mansour <essam@example.org>\n"
    )
    result, kept = run_commit_msg(tmp_path, message)
    assert result.returncode == 0
    assert "anthropic" not in kept and "Co-authored-by: Essam Mansour" in kept
