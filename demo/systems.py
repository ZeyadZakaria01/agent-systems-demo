"""The systems the runner can measure. To add one (or fill a patch step in), register a `SystemSpec`.

A spec's `open(tag_id, run)` is a context manager yielding a ready `System` on a fresh database and cleaning up on
exit, also after an error; the runner calls it once per check for `ctx.system` and once per `ctx.fresh_system(tag)`
(`tag_id` is the check id, plus `--<tag>` for fresh systems, and names the DB folder). `setup(run)` / `teardown(run)`
bracket ALL of the system's checks in a run: `teardown` always runs once `setup` was attempted, including when
`setup` or a check failed (a patch step's `setup` checks the step out, its `teardown` returns to `bitemporal`); a
failing `setup` gives every check of that system an error verdict. A system id is what checks list in `systems=`
and what a scorecard `Column` names as its `system`. The patch steps `step1`, `step2`, `step3` (`demo/steps.py`) each have their own column and feed the
change table: `setup` checks the step's commit out in the shared `MemState-patched/`, the
checks run on a `--patched` server (LadybugDB, `.lbug`), `teardown` returns to `bitemporal`. A run without `--systems`
measures every system; a patch step fails its setup unless `bitemporal` holds exactly three commits.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
from typing import Callable, ContextManager, Iterator

from demo import server
from demo.baseline import Baseline
from demo.adapter import System
from demo.memstate_system import MemStateSystem
from demo.reference_gem import PHASES, ReferenceGem, reference_gem_id
from demo.evidence import RunDir, slug
from demo.steps import PatchRepo, StepError
from demo.upstream_tests import TestCounts, run_patched, run_upstream


@dataclass(frozen=True)
class SystemSpec:
    id: str
    label: str
    open: Callable[[str, RunDir], ContextManager[System]]
    setup: Callable[[RunDir], None] | None = None
    teardown: Callable[[RunDir], None] | None = None
    step: int | None = None  # the patch step this system is (steps.py); None for every other system
    # Counts MemState's upstream tests on this system's source (demo/upstream_tests.py); runs after the system's checks,
    # while a step is still checked out. None for systems that are not MemState.
    unit_tests: Callable[[], TestCounts] | None = None


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


def step_spec(n: int, repo: PatchRepo | None = None,
              open_fn: Callable[[str, RunDir], ContextManager[System]] | None = None,
              unit_tests: Callable[[], TestCounts] | None = None) -> SystemSpec:
    """Patch step `n`: its commit checked out detached in `repo` while its checks run, a `--patched` server on a
    fresh `.lbug` per check, labelled with the step and commit. `open_fn` replaces the server (tests; then the upstream
    tests are not run unless `unit_tests` is given)."""
    repo = repo or PatchRepo()
    spec_id = f"step{n}"
    name = f"bitemporal patch step {n}"

    # Does teardown owe the worktree a return to the branch? Yes once setup completed the checkout (also when HEAD
    # was already at the step), or when a failing setup left HEAD somewhere else than it found it. A setup that
    # refused (dirty tree, operation in progress) leaves the worktree as it was, and so does the teardown.
    checked_out = False

    def setup(run: RunDir) -> None:
        nonlocal checked_out
        checked_out = False
        before = repo.position()
        try:
            commit = repo.checkout_step(n)
        except BaseException:
            checked_out = repo.position() != before
            raise
        checked_out = True
        run.events.append({"system": spec_id, "step": n, "checkout": commit})

    def teardown(run: RunDir) -> None:
        if checked_out:
            repo.return_to_branch()

    @contextmanager
    def open_step(tag_id: str, run: RunDir) -> Iterator[System]:
        commit = repo.step_commit(n)
        with open_memstate(spec_id, f"{name} ({commit[:7]}, LadybugDB)", True, "memstate.lbug", tag_id, run) as system:
            served = system.server.commit
            if served != commit:
                raise StepError(f"{spec_id}: the server runs commit {served}, expected step {n} = {commit}")
            yield system

    return SystemSpec(spec_id, name, open_fn or open_step, setup=setup, teardown=teardown, step=n,
                      unit_tests=unit_tests or (run_patched if open_fn is None else None))


def reference_gem_spec(phase: int) -> SystemSpec:
    """The in-process reference GEM, phase 1 or 2 (`demo/reference_gem.py`): a fresh instance per open, nothing to
    start or clean up. It runs every check, the time probes and the storyline; its C5-2 ramps run once and are not timed
    (`describe()["latency_comparable"]` is False) and it has no chat run."""
    label = f"reference GEM (phase {phase})"

    @contextmanager
    def open_gem(tag_id: str, run: RunDir) -> Iterator[System]:
        yield ReferenceGem(label, phase=phase)

    return SystemSpec(reference_gem_id(phase), label, open_gem)


def _upstream(tag_id: str, run: RunDir) -> ContextManager[System]:
    return open_memstate("upstream", "upstream", False, "memstate.kuzu", tag_id, run)


SYSTEMS: dict[str, SystemSpec] = {s.id: s for s in (
    SystemSpec("upstream", "upstream (Kuzu)", _upstream, unit_tests=run_upstream),
    step_spec(1), step_spec(2), step_spec(3),
    *map(reference_gem_spec, PHASES),
    SystemSpec("baseline", "baseline", open_baseline),
)}
STEP_IDS = tuple(i for i, s in SYSTEMS.items() if s.step is not None)  # registry order = the order of the chain
