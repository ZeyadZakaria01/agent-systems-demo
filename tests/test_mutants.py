"""Mutation tests (ticket 29, ADR 0007): the checks are run against deliberately broken reference GEMs, each built by
overriding one behaviour of `ReferenceGem`. Every check that has a row on the scorecard (or a time probe) is shown to
fail a wrong system by at least one mutant: the targeted rows must give the verdict the spec's table names, the case the
table names must be the one that broke, and every other row keeps its unmutated verdict and its unmutated held/broke
cases (controls included), except the rows the break itself causes (listed per mutant, with the reason). The C5 ramp
is the small one (`tests/reference_runs.py`); the 2,000-topic figures are pinned in the reference GEM tests."""

from dataclasses import dataclass, field
from functools import partial

import pytest

from demo.adapter import Rejected
from demo.checks.c2b_atomicity import CASE as C2B_CASE
from demo.reference_gem import DEFAULT_POLICIES, HISTORY_CAP, ReferenceGem
from demo.verdict import ABSENT, FAIL, PASS, Verdict
from tests.reference_runs import run_checks, unmutated

NOT_PASS = None  # an expected verdict that is only "not pass"
CONTROLS = "<every control case of the row>"


# ---------------------------------------------------------------- the mutants (one overridden behaviour each)


class OldestIsCurrent(ReferenceGem):
    def _valid_entry(self, f, asked, recorded=None):
        live = self._live(f, recorded)
        return min(live, key=lambda e: e.order, default=None), None


class MergeKeepsEarlier(ReferenceGem):
    def _merge(self, keep_id, drop_id):
        super()._merge(keep_id, drop_id)
        for f in self._topics[keep_id].fields.values():
            by_write = sorted(f.entries, key=lambda e: e.seq)
            stamps = sorted((e.valid_from for e in by_write), reverse=True)
            for e, stamp in zip(by_write, stamps):  # the earliest write now carries the latest timestamp
                e.valid_from = stamp


class CommitsFirstField(ReferenceGem):
    def _transact(self, request, at):
        try:
            return super()._transact(request, at)
        except Rejected:
            writes = request.get("fields") or []
            if len(writes) > 1:
                super()._transact({**request, "fields": writes[:1]}, at)  # the first field is committed, then the error
            raise


class IgnoresRuntimePolicies(ReferenceGem):
    def _apply_policies(self, proposal, now):
        shipped = {p["name"] for p in DEFAULT_POLICIES}
        stored = self._policies
        self._policies = [p for p in stored if p["name"] in shipped]
        try:
            super()._apply_policies(proposal, now)
        finally:
            self._policies = stored


class FlagsAssociations(ReferenceGem):
    def _neighbours(self, topic_id, kind, extra):
        if kind != "extension":
            return super()._neighbours(topic_id, kind, extra)
        return sorted(
            {*super()._neighbours(topic_id, "extension", extra), *super()._neighbours(topic_id, "association", extra)}
        )


class DeletesOverflow(ReferenceGem):
    def _cap(self, f):
        while len(f.entries) > HISTORY_CAP:
            f.entries.remove(min(f.entries, key=lambda e: e.seq))


class NoDecay(ReferenceGem):
    def _effective(self, topic, at):
        return topic.salience


class NeverArchives(ReferenceGem):
    def _forget(self, at):
        pass


class ReadsDoNotRaiseSalience(ReferenceGem):
    def _bump(self, topic, at):
        self._touch(topic, at, 0.0)


class StoresNoSource(ReferenceGem):
    def _propose(self, request, at):
        proposal = super()._propose(request, at)
        proposal.sources.clear()
        return proposal


class LastWrittenWins(ReferenceGem):
    def _valid_entry(self, f, asked, recorded=None):  # the valid time is ignored: the latest write is current
        return max(self._live(f, recorded), key=lambda e: e.seq, default=None), None


class IgnoresInvalidAt(ReferenceGem):
    def _propose(self, request, at):
        writes = [{k: v for k, v in w.items() if k != "invalid_at"} for w in request.get("fields") or []]
        return super()._propose({**request, "fields": writes} if writes else request, at)


class BelievedOnFromCurrent(ReferenceGem):
    def _live(self, f, recorded):
        return super()._live(f, None)


@dataclass(frozen=True)
class Mutant:
    factory: type[ReferenceGem]
    targets: dict[str, str | None]  # row -> the verdict it must give (`NOT_PASS`: any verdict but pass)
    caused: frozenset[str] = frozenset()  # other rows the break itself changes
    phase: int = 1
    broken: dict[str, tuple[str, ...]] = field(default_factory=dict)  # row -> ids of cases that must be broken


MUTANTS = {
    # the spec's table, one mutant per condition
    "C1": Mutant(
        OldestIsCurrent,
        {"C1": FAIL, "C2(d)": NOT_PASS},  # C2(d) reads a current value too: its mutant
        caused=frozenset({"C2(a)", "C4", "T1", "T2", "T3", "T6"}),
    ),  # every other row that reads a current value
    "C2(a)": Mutant(MergeKeepsEarlier, {"C2(a)": NOT_PASS}),
    "C2(b)": Mutant(
        CommitsFirstField,
        {"C2(b)": FAIL},
        caused=frozenset({"C2(c)"}),  # C2(c) also relies on atomic rejection
        broken={"C2(b)": (C2B_CASE,)},
    ),
    "C2(c)": Mutant(IgnoresRuntimePolicies, {"C2(c)": FAIL}),
    "C3": Mutant(FlagsAssociations, {"C3": NOT_PASS}, broken={"C3": (CONTROLS,)}),
    "C4": Mutant(DeletesOverflow, {"C4": NOT_PASS}, broken={"C4": ("cap",)}),
    "C5": Mutant(
        NoDecay,
        {"C5-2": FAIL},
        caused=frozenset({"C6-2"}),  # C6 clause 2 needs decay to separate target from control
        broken={"C5-2": ("archived topics counted at each ramp step",)},
    ),
    "C6": Mutant(
        ReadsDoNotRaiseSalience,
        {"C6-1": FAIL, "C6-2": NOT_PASS},  # clause 2 is a reinforcement case too
        broken={"C6-1": ("each retrieval raises the salience of the topics it returns",)},
    ),
    "C4′": Mutant(StoresNoSource, {"C4′": FAIL}),
    "T4": Mutant(IgnoresInvalidAt, {"T4": FAIL}, phase=2),
    "T5": Mutant(BelievedOnFromCurrent, {"T5": FAIL}, phase=2),
    # the rows the table does not name: the checks that, with these, make every row's check fail some wrong system
    "forgetting": Mutant(
        NeverArchives,
        {"C5-1": NOT_PASS, "C5-2": FAIL},  # the mechanism, as well as the trajectory
        caused=frozenset({"C4", "C6-2"}),
    ),  # both read n/a or not-scored: forgetting was not shown to run
    "valid time": Mutant(
        LastWrittenWins, {"T1": FAIL, "T2": FAIL, "T3": FAIL, "T6": FAIL}, caused=frozenset({"C4"})
    ),  # its dated-merge case reads a current value
}


@pytest.fixture(scope="module")
def mutated():
    cache: dict[str, dict[str, Verdict]] = {}

    def run(name: str) -> dict[str, Verdict]:
        if name not in cache:
            mutant = MUTANTS[name]
            cache[name] = run_checks(partial(mutant.factory, phase=mutant.phase), small_ramps=True)
        return cache[name]

    return run


def test_the_unmutated_reference_gem_passes_every_checked_row():
    for phase in (1, 2):
        bad = {
            r: v.verdict
            for r, v in unmutated(phase).items()
            if v.verdict != PASS
            and r != "Over-flagging"  # a measurement has no verdict
            and not (phase == 1 and r in ("T4", "T5"))
        }
        assert not bad, (phase, bad)
    assert unmutated(1)["T4"].verdict == ABSENT and unmutated(1)["T5"].verdict == ABSENT


@pytest.mark.parametrize("name", MUTANTS)
def test_the_targeted_rows_give_the_verdict_the_table_names(name, mutated):
    for row, expected in MUTANTS[name].targets.items():
        v = mutated(name)[row]
        assert v.verdict != PASS, (name, row, [(c.name, c.held) for c in v.cases])
        if expected is not NOT_PASS:
            assert v.verdict == expected, (name, row, v.verdict, [(c.name, c.held) for c in v.cases])


@pytest.mark.parametrize("name", [n for n, m in MUTANTS.items() if m.broken])
def test_the_case_the_table_names_is_the_one_that_broke(name, mutated):
    for row, ids in MUTANTS[name].broken.items():
        cases = mutated(name)[row].cases
        for case_id in ids:
            wanted = [c for c in cases if c.control] if case_id == CONTROLS else [c for c in cases if c.id == case_id]
            assert wanted and all(c.held is False for c in wanted), (
                name,
                row,
                case_id,
                [(c.id, c.held) for c in cases],
            )


def _held(v: Verdict) -> list[tuple[str, bool | None]]:
    return [(c.id, c.held) for c in v.cases]


@pytest.mark.parametrize("name", MUTANTS)
def test_untargeted_rows_keep_their_unmutated_verdict_and_cases_controls_included(name, mutated):
    mutant = MUTANTS[name]
    base = unmutated(mutant.phase, small_ramps=True)
    allowed = {*mutant.targets, *mutant.caused}
    changed = {
        r: (base[r].verdict, v.verdict, _held(base[r]), _held(v))
        for r, v in mutated(name).items()
        if r not in allowed and (v.verdict, _held(v)) != (base[r].verdict, _held(base[r]))
    }
    assert not changed, (name, changed)
