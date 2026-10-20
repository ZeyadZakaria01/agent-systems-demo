"""The systems the runner can measure. To add one (or fill a patch step in), register a `SystemSpec`.

A spec's `open(tag_id, run)` is a context manager yielding a ready `System` on a fresh database and cleaning up on
exit, also after an error; the runner calls it once per check for `ctx.system` and once per `ctx.fresh_system(tag)`
(`tag_id` is the check id, plus `--<tag>` for fresh systems, and names the DB folder). `setup(run)` / `teardown(run)`
bracket ALL of the system's checks in a run: `teardown` always runs once `setup` was attempted, including when
`setup` or a check failed (ticket 03: `setup` checks out a patch step, `teardown` returns to `bitemporal`); a
failing `setup` gives every check of that system an error verdict. A system id is what checks list in `systems=`
and what a scorecard `Column` lists in `systems=`. The patch steps `step1`, `step2`, `step3` (`demo/steps.py`) feed the
patch column and the change table: `setup` checks the step's commit out in the shared `MemState-patched/`, the
checks run on a `--patched` server (LadybugDB, `.lbug`), `teardown` returns to `bitemporal`. `default_systems()` is
what a run measures without `--systems`: only the steps that exist.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, ContextManager, Iterator

from demo import server
from demo.baseline import Baseline
from demo.client import MemStateSystem, System
from demo.evidence import RunDir, slug
from demo.steps import PatchRepo, StepError


@dataclass(frozen=True)
class SystemSpec:
    id: str
    label: str
    open: Callable[[str, RunDir], ContextManager[System]]
    setup: Callable[[RunDir], None] | None = None
    teardown: Callable[[RunDir], None] | None = None


@contextmanager
def open_memstate(spec_id: str, label: str, patched: bool, db_name: str, tag_id: str, run: RunDir) -> Iterator[System]:
    """Fresh absolute DB, server via `scripts/run_memstate.sh`, wait for /health, stop in `finally` (process group
    killed, port 8765 verified free). The caller holds the machine-wide lock."""
    name = f"{spec_id}-{slug(tag_id)}"
    db_path = run.runtime_dir / name / db_name
    handle = server.start(db_path, patched=patched, log_path=run.logs / f"{name}.log")
    system = MemStateSystem(label, server.BASE_URL, server=handle.info)
    try:
        yield system
    finally:
        system.close()
        stop = handle.stop()
        run.events.append({"system": spec_id, "check": tag_id, "db_path": handle.info.db_path,
                           "commit": handle.info.commit, "engine_line": handle.info.engine_line,
                           "source_dir": handle.info.source_dir, **stop})
        if not stop["port_free_after_stop"]:
            raise server.ServerError(f"port {server.PORT} still busy after stopping {name}")


@contextmanager
def open_baseline(tag_id: str, run: RunDir) -> Iterator[System]:
    yield Baseline()


def step_label(n: int, commit: str) -> str:
    return f"bitemporal patch step {n} ({commit[:7]}, LadybugDB)"


def step_spec(n: int, repo: PatchRepo | None = None,
              open_fn: Callable[[str, RunDir], ContextManager[System]] | None = None) -> SystemSpec:
    """Patch step `n`: its commit checked out detached in `repo` while its checks run, a `--patched` server on a
    fresh `.lbug` per check, labelled with the step and commit. `open_fn` replaces the server (tests)."""
    repo = repo or PatchRepo()
    spec_id = f"step{n}"

    moved = False  # did THIS run's setup move the worktree? only then does teardown put it back

    def setup(run: RunDir) -> None:
        nonlocal moved
        moved = False
        before = repo.position()
        try:
            commit = repo.checkout_step(n)
        finally:
            moved = repo.position() != before
        run.events.append({"system": spec_id, "step": n, "checkout": commit})

    def teardown(run: RunDir) -> None:
        if moved:
            repo.return_to_branch()

    @contextmanager
    def open_step(tag_id: str, run: RunDir) -> Iterator[System]:
        commit = repo.step_commit(n)
        with open_memstate(spec_id, step_label(n, commit), True, "memstate.lbug", tag_id, run) as system:
            served = system.server.commit
            if served != commit:
                raise StepError(f"{spec_id}: the server runs commit {served}, expected step {n} = {commit}")
            yield system

    return SystemSpec(spec_id, f"bitemporal patch step {n}", open_fn or open_step,
                      setup=setup, teardown=teardown)


def default_systems(repo: PatchRepo | None = None) -> list[str]:
    """What a run measures without `--systems`: upstream, the patch steps that exist in `repo`, the baseline."""
    existing = len((repo or PatchRepo()).steps())
    return [i for i in SYSTEMS if not (i.startswith("step") and int(i[4:]) > existing)]


def _upstream(tag_id: str, run: RunDir) -> ContextManager[System]:
    return open_memstate("upstream", "upstream", False, "memstate.kuzu", tag_id, run)


SYSTEMS: dict[str, SystemSpec] = {s.id: s for s in (
    SystemSpec("upstream", "upstream (Kuzu)", _upstream),
    step_spec(1), step_spec(2), step_spec(3),
    SystemSpec("baseline", "baseline", open_baseline),
)}
