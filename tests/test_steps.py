"""Patch steps: resolving, checking out and returning, on a throwaway git repo (real git, no MemState)."""

import json
import os
import subprocess
from datetime import date
from pathlib import Path

import pytest

from demo.checks import discover
from demo.run import run_recorded
from demo.steps import PatchRepo, StepError
from demo.systems import SYSTEMS, step_spec


def git(path, *args):
    return subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A base commit and a branch `bitemporal` with three commits on top (the whole patch)."""
    path = tmp_path / "patched"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.email", "t@example.com")
    git(path, "config", "user.name", "t")
    (path / "f.txt").write_text("upstream\n")
    git(path, "add", ".")
    git(path, "commit", "-q", "-m", "upstream")
    base = git(path, "rev-parse", "HEAD")
    git(path, "checkout", "-q", "-b", "bitemporal")
    for n in (1, 2, 3):
        (path / "f.txt").write_text(f"step {n}\n")
        git(path, "commit", "-q", "-am", f"step {n}")
    return PatchRepo(path=path, base=base, branch="bitemporal")


def test_steps_are_the_commits_above_upstream_oldest_first(repo):
    steps = repo.steps()
    assert len(steps) == 3
    assert git(repo.path, "log", "--format=%s", "--reverse", f"{repo.base}..bitemporal").split("\n") == \
        ["step 1", "step 2", "step 3"]
    assert [repo.step_commit(n) for n in (1, 2, 3)] == steps


def test_checkout_step_detaches_at_that_commit_and_returning_restores_the_branch(repo):
    commit = repo.checkout_step(1)
    assert git(repo.path, "rev-parse", "HEAD") == commit
    assert git(repo.path, "branch", "--show-current") == ""  # detached
    assert (repo.path / "f.txt").read_text() == "step 1\n"
    repo.return_to_branch()
    assert git(repo.path, "branch", "--show-current") == "bitemporal"
    assert (repo.path / "f.txt").read_text() == "step 3\n"


@pytest.mark.parametrize("extra", [-1, 1])
def test_a_branch_without_exactly_three_commits_is_refused_naming_the_count(repo, extra):
    if extra < 0:
        git(repo.path, "reset", "-q", "--hard", "HEAD~1")
    else:
        (repo.path / "f.txt").write_text("step 4\n")
        git(repo.path, "commit", "-q", "-am", "step 4")
    with pytest.raises(StepError, match=rf"bitemporal has {3 + extra} commit\(s\) on top of .*exactly 3"):
        repo.checkout_step(1)
    assert git(repo.path, "branch", "--show-current") == "bitemporal"  # nothing was touched


def test_a_dirty_worktree_is_refused_and_left_alone(repo):
    (repo.path / "f.txt").write_text("my uncommitted work\n")
    with pytest.raises(StepError, match="uncommitted changes"):
        repo.checkout_step(1)
    assert git(repo.path, "branch", "--show-current") == "bitemporal"
    assert (repo.path / "f.txt").read_text() == "my uncommitted work\n"


def test_untracked_files_do_not_count_as_dirty(repo):
    (repo.path / "scratch.txt").write_text("x")
    repo.checkout_step(1)


def test_a_run_without_systems_measures_every_registered_system():
    assert list(SYSTEMS) == ["upstream", "step1", "step2", "step3", "baseline"]


@pytest.mark.parametrize("operation", ["MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG", "rebase-merge"])
def test_an_operation_in_progress_is_refused(repo, operation):
    marker = git(repo.path, "rev-parse", "--path-format=absolute", "--git-path", operation)
    if operation == "rebase-merge":
        os.makedirs(marker)
    else:
        Path(marker).write_text(repo.head() + "\n")
    with pytest.raises(StepError, match=f"operation in progress \\({operation}\\)"):
        repo.checkout_step(1)
    assert git(repo.path, "branch", "--show-current") == "bitemporal"


def test_the_runner_checks_the_step_out_for_its_checks_and_returns_to_the_branch_even_when_they_fail(repo, tmp_path):
    seen = []

    class Boom(Exception):
        pass

    def opened(tag_id, run):
        seen.append((git(repo.path, "branch", "--show-current"), repo.head()))
        raise Boom("server did not start")

    spec = step_spec(1, repo, open_fn=opened)
    c1 = next(c for c in discover() if c.id == "C1")
    run = run_recorded(["step1"], [c1], tmp_path, "cmd", run_day=date(2026, 10, 20),
                       registry={"step1": spec}, runtime_root=tmp_path / "rt", log=lambda *_: None)
    assert seen == [("", repo.step_commit(1))]  # detached, at step 1, while its check ran
    (v,) = run.verdicts
    assert v.verdict == "error" and "server did not start" in v.error
    assert git(repo.path, "branch", "--show-current") == "bitemporal"


def test_an_incomplete_patch_gives_error_verdicts_naming_the_commit_count_and_touches_nothing(repo, tmp_path):
    git(repo.path, "reset", "-q", "--hard", "HEAD~1")
    spec = step_spec(2, repo, open_fn=lambda *_: pytest.fail("must not open"))
    c1 = next(c for c in discover() if c.id == "C1")
    run = run_recorded(["step2"], [c1], tmp_path, "cmd", run_day=date(2026, 10, 20),
                       registry={"step2": spec}, runtime_root=tmp_path / "rt", log=lambda *_: None)
    (v,) = run.verdicts
    assert v.verdict == "error" and "bitemporal has 2 commit(s)" in v.error and "exactly 3" in v.error
    assert git(repo.path, "branch", "--show-current") == "bitemporal"


def test_a_dirty_worktree_gives_error_verdicts_not_a_clobbered_checkout(repo, tmp_path):
    (repo.path / "f.txt").write_text("mine\n")
    spec = step_spec(1, repo, open_fn=lambda *_: pytest.fail("must not open"))
    c1 = next(c for c in discover() if c.id == "C1")
    run = run_recorded(["step1"], [c1], tmp_path, "cmd", run_day=date(2026, 10, 20),
                       registry={"step1": spec}, runtime_root=tmp_path / "rt", log=lambda *_: None)
    assert run.verdicts[0].verdict == "error" and "uncommitted changes" in run.verdicts[0].error
    assert (repo.path / "f.txt").read_text() == "mine\n"


def run_step1(repo, tmp_path, opened=None):
    spec = step_spec(1, repo, open_fn=opened or (lambda *_: pytest.fail("must not open")))
    c1 = next(c for c in discover() if c.id == "C1")
    return run_recorded(["step1"], [c1], tmp_path, "cmd", run_day=date(2026, 10, 20), registry={"step1": spec},
                        runtime_root=tmp_path / "rt", log=lambda *_: None)


def test_a_refused_setup_leaves_a_detached_worktree_with_a_tracked_edit_exactly_where_it_was(repo, tmp_path):
    # a developer amending step 1 (HEAD detached at it, an edit to a tracked file): the run refuses and does not
    # carry the edit over to `bitemporal` in teardown
    git(repo.path, "checkout", "-q", "--detach", repo.step_commit(1))
    (repo.path / "f.txt").write_text("amending step 1\n")
    head = repo.head()
    run = run_step1(repo, tmp_path)
    assert run.verdicts[0].verdict == "error" and "uncommitted changes" in run.verdicts[0].error
    assert repo.head() == head and git(repo.path, "branch", "--show-current") == ""
    assert (repo.path / "f.txt").read_text() == "amending step 1\n"
    assert not any("teardown_error" in e for e in run_events(run))


def test_a_refused_setup_for_an_operation_in_progress_does_not_move_the_worktree(repo, tmp_path):
    Path(git(repo.path, "rev-parse", "--path-format=absolute", "--git-path", "MERGE_HEAD")).write_text(repo.head() + "\n")
    run = run_step1(repo, tmp_path)
    assert "operation in progress" in run.verdicts[0].error
    assert git(repo.path, "branch", "--show-current") == "bitemporal"


def test_a_clean_worktree_already_detached_at_the_step_is_still_returned_to_the_branch(repo, tmp_path):
    # what a crashed earlier run leaves behind: the checkout is already where the step wants it, so setup moves
    # nothing, yet the run must still end on `bitemporal`
    git(repo.path, "checkout", "-q", "--detach", repo.step_commit(1))
    run = run_step1(repo, tmp_path, opened=_server_down)
    assert run.verdicts[0].verdict == "error" and "server did not start" in run.verdicts[0].error
    assert git(repo.path, "branch", "--show-current") == "bitemporal"


def _server_down(tag_id, run):
    raise RuntimeError("server did not start")


def run_events(run):
    return json.loads((run.dir / "results.json").read_text())["servers"]
