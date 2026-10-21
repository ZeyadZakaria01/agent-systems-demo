"""The systems one check works with.

`ctx.system` is the check's default system: opened on first use, closed (and its evidence captured) when the check
ends. `ctx.fresh_system(tag)` is a context manager opening ANOTHER fresh system (a fresh database, and for MemState a
fresh server) for the length of its `with` block; each gets its own snapshot, so a row can be assembled from several
(one fresh DB per time-probe story, one per ramp repeat).

One system at a time (one server at a time, port 8765): opening a system while another is open raises `SystemBusy`.
That includes the default system, which stays open until the check ends, so a check that uses `fresh_system` should
not touch `ctx.system`. Tags are unique within a check.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext

from demo.systems.adapter import System, utc_now

OpenSystem = Callable[
    [str | None], AbstractContextManager[System]
]  # tag (None = the default system) -> a system, cleaned on exit
Capture = Callable[[System, str | None, str, str], dict]  # (system, tag, started_at, finished_at) -> evidence


class SystemBusy(RuntimeError):
    pass


class Session:
    def __init__(self, open_system: OpenSystem, capture: Capture | None = None) -> None:
        self._open = open_system
        self._capture = capture
        self._active: tuple[str | None, AbstractContextManager[System], System, str] | None = None
        self._tags: set[str | None] = set()
        self.captured: list[dict] = []  # evidence of every system closed so far, in opening order

    @classmethod
    def around(cls, system: System) -> Session:
        """A session whose default system is `system` (tests and one-off runs); `fresh_system` is not available."""
        return cls(lambda tag: nullcontext(system) if tag is None else _no_fresh())

    @classmethod
    def in_process(cls, factory: Callable[[], System]) -> Session:
        """A session opening a new `factory()` system for every open (in-process systems need no cleanup)."""
        return cls(lambda tag: nullcontext(factory()))

    @property
    def system(self) -> System:
        if self._active is None or self._active[0] is not None:
            if self._active is not None:
                raise SystemBusy(f"system {self._active[0]!r} is still open; leave its fresh_system block first")
            if None in self._tags:
                raise SystemBusy("the default system was already closed; open a fresh_system instead")
            self._enter(None)
        assert self._active is not None
        return self._active[2]

    @contextmanager
    def fresh_system(self, tag: str) -> Iterator[System]:
        if not tag:
            raise ValueError("fresh_system needs a non-empty tag")
        system = self._enter(tag)
        try:
            yield system
        finally:
            self._leave()

    def close(self) -> None:
        """End of the check: capture and clean up the default system if it is still open."""
        if self._active is not None:
            self._leave()

    def _enter(self, tag: str | None) -> System:
        if self._active is not None:
            held = self._active[0]
            raise SystemBusy(
                f"system {held if held is not None else 'default (ctx.system)'!r} is still open: only one "
                f"system at a time; close it before opening {tag!r}"
            )
        if tag in self._tags:
            raise ValueError(f"system tag {tag!r} already used in this check")
        cm = self._open(tag)
        started = utc_now()
        system = cm.__enter__()
        self._tags.add(tag)
        self._active = (tag, cm, system, started)
        return system

    def _leave(self) -> None:
        assert self._active is not None
        tag, cm, system, started = self._active
        self._active = None
        try:
            if self._capture is not None:
                self.captured.append(self._capture(system, tag, started, utc_now()))
        finally:
            cm.__exit__(None, None, None)


def _no_fresh() -> AbstractContextManager[System]:
    raise RuntimeError("this session wraps one system; use Session.in_process(factory) for fresh_system")
