"""The machine-wide one-server lock (`SERVER_LOCK`), held for the whole of every run that starts a server.

A run started under `flock server.lock <command>` inherits the locked descriptor and uses it instead of waiting on
itself. While held, `GEM_SERVER_LOCK_HELD` names the lock, so the scripts a run starts (`scripts/run_memstate.sh`,
`scripts/run_ollama.sh`, through `scripts/server_lock.sh`) do not lock again. The scripts started by hand hold it too.
"""

from __future__ import annotations

import fcntl
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from demo.paths import SERVER_LOCK

HELD_ENV = "GEM_SERVER_LOCK_HELD"


def _inherited(lock: Path) -> bool:
    """An open descriptor on the lock came with the process: `flock FILE <command>` passes its locked one on."""
    fds = Path("/proc/self/fd")
    for fd in fds.iterdir():
        try:
            if Path(os.readlink(fd)) == lock:
                return True
        except OSError:
            continue
    return False


@contextmanager
def _announced(lock: Path) -> Iterator[None]:
    previous = os.environ.get(HELD_ENV)
    os.environ[HELD_ENV] = str(lock)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(HELD_ENV, None)
        else:
            os.environ[HELD_ENV] = previous


@contextmanager
def server_lock(lock: Path | str = SERVER_LOCK) -> Iterator[None]:
    lock = Path(lock).resolve()
    if os.environ.get(HELD_ENV) == str(lock) or _inherited(lock):
        with _announced(lock):
            yield
        return
    lock.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f"waiting for {lock} (another run holds the machine-wide server lock)", file=sys.stderr)
            fcntl.flock(fd, fcntl.LOCK_EX)
        with _announced(lock):
            yield
    finally:
        os.close(fd)
