"""Start and stop one MemState server through `scripts/run_memstate.sh`.

One server at a time, port 8765 (fixed by the script). The run that calls this holds the machine-wide lock
(`demo/server_lock.py`); a busy port at start means a server outside the lock, and the error says so. Every start gets a fresh absolute DB path;
`MemState/memstate.kuzu` is never passed or opened.
"""

from __future__ import annotations

import os
import re
import signal
import socket
import subprocess
import time
from dataclasses import dataclass, replace
from pathlib import Path

import httpx

from demo.paths import REPO_ROOT, RUN_SCRIPT

HOST, PORT = "127.0.0.1", 8765
BASE_URL = f"http://{HOST}:{PORT}"


class ServerError(RuntimeError):
    pass


def port_free(port: int = PORT) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, port)) != 0


def _wait_port_free(timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if port_free():
            return True
        time.sleep(0.2)
    return port_free()


def _git_head(source_dir: str) -> str | None:
    r = subprocess.run(["git", "-C", source_dir, "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() or None if r.returncode == 0 else None


def parse_startup(log_text: str) -> ServerInfo:
    """The run script prints `MemState engine module: <m>`, `MemState source folder: <dir>`, `MemState DB: <path>`."""

    def grab(prefix: str) -> str | None:
        m = re.search(rf"^({re.escape(prefix)}.*)$", log_text, re.MULTILINE)
        return m.group(1).strip() if m else None

    engine_line = grab("MemState engine module:")
    source_line = grab("MemState source folder:")
    db_line = grab("MemState DB:")
    source_dir = source_line.split(":", 1)[1].strip() if source_line else None
    return ServerInfo(
        engine_line=engine_line, source_dir=source_dir, db_path=db_line.split(":", 1)[1].strip() if db_line else None
    )


@dataclass(frozen=True)
class ServerInfo:
    """What the launcher learns about a server it started: the run script's startup output plus the source commit."""

    commit: str | None = None
    engine_line: str | None = None
    source_dir: str | None = None
    db_path: str | None = None


@dataclass
class ServerHandle:
    proc: subprocess.Popen
    info: ServerInfo
    log_path: Path

    def stop(self) -> dict:
        """SIGTERM the process group, escalate to SIGKILL, then verify port 8765 is free. Safe to call twice."""
        result = {"log": str(self.log_path)}
        try:
            pgid = os.getpgid(self.proc.pid)
        except ProcessLookupError:
            pgid = None
        if pgid is not None:
            for sig, wait in ((signal.SIGTERM, 20), (signal.SIGKILL, 10)):
                try:
                    os.killpg(pgid, sig)
                except ProcessLookupError:
                    break
                try:
                    self.proc.wait(timeout=wait)
                    break
                except subprocess.TimeoutExpired:
                    continue
        self.proc.wait(timeout=10)
        result["port_free_after_stop"] = _wait_port_free(15)
        return result


def start(db_path: Path, patched: bool, log_path: Path, timeout: float = 240) -> ServerHandle:
    if not db_path.is_absolute():
        raise ServerError(f"DB path must be absolute: {db_path}")
    if db_path.exists():
        raise ServerError(f"DB path is not fresh: {db_path}")
    if not port_free():
        raise ServerError(f"port {PORT} is busy: a server is running outside the machine-wide lock; stop it")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["bash", str(RUN_SCRIPT), *(["--patched"] if patched else []), str(db_path)]
    with open(log_path, "wb") as log:
        proc = subprocess.Popen(
            cmd, cwd=REPO_ROOT, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True
        )
    handle = ServerHandle(proc=proc, info=ServerInfo(), log_path=log_path)
    try:
        deadline = time.monotonic() + timeout
        while True:
            if proc.poll() is not None:
                raise ServerError(f"run script exited {proc.returncode}; log tail:\n{log_path.read_text()[-2000:]}")
            try:
                if httpx.get(f"{BASE_URL}/health", timeout=2).status_code == 200:
                    graph = httpx.get(f"{BASE_URL}/health/graph", timeout=10)
                    if graph.status_code == 200:
                        break
            except httpx.HTTPError:
                pass
            if time.monotonic() > deadline:
                raise ServerError(f"/health not ready after {timeout}s; log tail:\n{log_path.read_text()[-2000:]}")
            time.sleep(0.25)
        info = parse_startup(log_path.read_text())
        handle.info = replace(
            info,
            commit=_git_head(info.source_dir) if info.source_dir else None,
            db_path=graph.json().get("path") or info.db_path,
        )
        return handle
    except BaseException:
        handle.stop()
        raise
