"""The machine-wide one-server lock is held by the runs and scripts that start servers, so forgetting the `flock`
wrapper cannot put two servers on the laptop. An inherited lock (`flock server.lock <command>`) is used, not waited on;
a child script started under a holder sees `GEM_SERVER_LOCK_HELD` and does not lock again."""

import os
import subprocess
import sys
import time

from demo.paths import REPO_ROOT
from demo.server_lock import HELD_ENV, server_lock

SCRIPT = REPO_ROOT / "scripts" / "server_lock.sh"


def free(path) -> bool:
    return subprocess.run(["flock", "-n", str(path), "true"]).returncode == 0


def test_a_free_lock_is_held_for_the_block_and_announced_to_children(tmp_path):
    lock = tmp_path / "server.lock"
    with server_lock(lock):
        assert not free(lock)
        child_env = subprocess.run(["sh", "-c", f"echo ${HELD_ENV}"], capture_output=True, text=True).stdout.strip()
        assert child_env == str(lock)
    assert free(lock)
    assert HELD_ENV not in os.environ


def test_a_busy_lock_is_waited_for(tmp_path, capsys):
    lock = tmp_path / "server.lock"
    other = subprocess.Popen(["flock", str(lock), "sleep", "1"])
    time.sleep(0.2)
    started = time.monotonic()
    with server_lock(lock):
        waited = time.monotonic() - started
    other.wait()
    assert waited > 0.5
    assert "waiting for" in capsys.readouterr().err


def test_a_lock_inherited_from_flock_is_used_not_waited_on_and_announced_to_children(tmp_path):
    lock = tmp_path / "server.lock"
    code = (
        f"import os, subprocess\nfrom demo.server_lock import server_lock\nwith server_lock({str(lock)!r}):\n"
        f"    print(subprocess.run(['sh', '-c', 'echo ${HELD_ENV}'], capture_output=True, text=True).stdout.strip())"
    )
    result = subprocess.run(
        ["flock", str(lock), sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        env={**os.environ, HELD_ENV: ""},
    )
    assert result.stdout.strip() == str(lock)


def test_only_runs_that_start_a_server_need_the_lock():
    from demo.run import needs_server_lock

    assert not needs_server_lock(["baseline", "reference-gem-p1", "reference-gem-p2"], chat=False)
    assert needs_server_lock(["baseline", "upstream"], chat=False)
    assert needs_server_lock(["step2"], chat=False)
    assert needs_server_lock(["baseline"], chat=True)


def shell(lock, body, held_env=None, wrap=()):
    """Run `body` after `hold_server_lock` in bash; `held_env` is what a parent announced (none by default)."""
    env = {k: v for k, v in os.environ.items() if k != HELD_ENV}
    env["GEM_SERVER_LOCK"] = str(lock)
    if held_env is not None:
        env[HELD_ENV] = held_env
    return subprocess.run(
        [*wrap, "bash", "-c", f"source {SCRIPT}; hold_server_lock; {body}"],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_the_script_lock_holds_a_free_lock_for_the_rest_of_the_script(tmp_path):
    lock = tmp_path / "server.lock"
    result = shell(lock, f"flock -n {lock} true && echo free || echo held")
    assert result.stdout.strip() == "held"


def test_the_script_lock_refuses_a_busy_lock_naming_it(tmp_path):
    lock = tmp_path / "server.lock"
    with server_lock(lock):
        result = shell(lock, "echo started")
    assert result.returncode == 1
    assert "started" not in result.stdout
    assert str(lock) in result.stderr


def test_the_script_lock_trusts_a_holding_parent(tmp_path):
    lock = tmp_path / "server.lock"
    with server_lock(lock):
        assert shell(lock, "echo started", held_env=str(lock)).stdout.strip() == "started"


def test_the_script_lock_uses_a_lock_inherited_from_flock(tmp_path):
    lock = tmp_path / "server.lock"
    assert shell(lock, "echo started", wrap=("flock", str(lock))).stdout.strip() == "started"
