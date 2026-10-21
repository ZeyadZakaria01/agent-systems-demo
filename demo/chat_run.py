"""The chat runs: record one on a memory system, replay it from a file (`python -m demo.chat_run`).

This file holds the bad-merge run (spec stories 52, 54; ticket 17) and the recording command line for both runs. The
"two weeks ago" run (ticket 18, `demo/chat_two_weeks.py`) records into the same recording format and is rendered by
the same replay. Replay reads JSON only: it starts no server, needs no Ollama and no GPU, and imports neither `httpx`
nor `demo.server`.

The bad-merge run, on upstream MemState through `/v1` and the system adapter:

1. The Website Redesign storyline is played (`demo/storyline.py`, all 29 events) on one topic, the *original*, with the
   deadline history March 15 -> April 20 and the "vendor delay" provenance. Then the user "re-explains" the project
   (the paper's Figure 1, "stored twice"): a second topic gets `Deadline = April 20` and nothing else.
2. MemState's merge keeps the lower topic id (F9) and the ids are random, so the order is arranged the way C2(a)
   arranges it (`demo/merge.py`, `create_retitled_pair`): two topics are created under distinct placeholder titles, the
   lower id is the re-explanation and the higher the original, then both are given the title "Website Redesign" by a
   labelled setup `PATCH title` (an editor edit; every value is written through `/v1` only). A `/v1 extend_topic` with
   no fields triggers the scan. The merge then drops the original and keeps the re-explanation.
3. 2-3 storyline questions go through MemState chat (`POST /api/llm/chat`, provider `ollama`, one request per question,
   no `intent_override`, no Groq, no judge). Each turn records the question, ground truth, answer, route, latency, what
   the state lost in the merge on the question's own field and on the topic, and an empty hand-grade slot.

What the merge loses is computed by comparing the original's stored topic before the merge with the survivor after it
(`lost_in_merge`): history entries (value, provenance, reason) of fields both topics held are gone; fields only the
original held are copied to the survivor by MemState's merge (`graph_store.py:1249`, [INFERENCE] from reading the code;
the recorded run shows what actually happened).
"""

from __future__ import annotations

import argparse
import re
import dataclasses
import json
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from demo.adapter import System
from demo.chat_recording import (EMPTY_GRADE, LEFT_UNSET, RECORDINGS_ROOT, is_variant, load_recording, new_recording,
                                 recording_files, render_recording, save_recording)
from demo.chat_two_weeks import CASE as TWO_WEEKS_CASE, FIRST_INTENT_OVERRIDE, record_two_weeks
from demo.merge import DEFAULT_INTERVAL_S, DEFAULT_TIMEOUT_S, MergeOutcome, Pair, await_merge, unique_title
from demo.paths import REPO_ROOT
from demo.reads import NO_VALUE, current_value
from demo.storyline import WEBSITE_REDESIGN, Storyline

if TYPE_CHECKING:
    from demo.evidence import RunDir

TITLE = "Website Redesign"
REEXPLAINED_FIELD = "Deadline"
REEXPLAINED_VALUE = "April 20"
REEXPLAINED_PROVENANCE = "chat-reexplanation"
IDENTITY_KEYS = ("value", "provenance", "why_changed")  # what identifies a history entry across the merge


class ScenarioError(RuntimeError):
    """The arrangement did not hold (no retitle path, no merge, the wrong topic survived): nothing is recorded."""


def trim(topic: dict | None) -> dict | None:
    """A stored topic as the recording keeps it: identity, current value and the full history of every field."""
    if topic is None:
        return None
    fields = {}
    for name, f in topic["fields"].items():
        now = current_value(f)
        fields[name] = {"current": None if now is NO_VALUE else now,
                        "history": [{k: e.get(k) for k in ("value", "provenance", "why_changed", "impact_expected",
                                                           "valid_from")} for e in f.get("history") or []]}
    return {"id": topic["id"], "title": topic["title"], "summary": topic.get("summary"),
            "topic_kind": topic.get("topic_kind"), "fields": fields}


def _identity(entry: dict) -> tuple:
    return tuple(entry.get(k) for k in IDENTITY_KEYS)


def lost_in_merge(before: dict, after: dict) -> dict:
    """What a merge took from `before` (the dropped topic as stored) that `after` (the survivor) no longer holds.

    `lost_entries`: per field, the history entries (identified by value, provenance and reason) of `before` that are
    not in `after`'s history of that field. `lost_values`: per field, the values `before` held that `after` never
    held (a value whose entry is lost but is held again by another entry is not lost as a value). `fields_lost`:
    fields `before` held and `after` does not. `kept_fields`: fields present on both."""
    lost_entries: dict[str, list[dict]] = {}
    lost_values: dict[str, list] = {}
    fields_lost, kept = [], []
    for name, f in before["fields"].items():
        theirs = after["fields"].get(name)
        if theirs is None:
            fields_lost.append(name)
            continue
        kept.append(name)
        held = {_identity(e) for e in theirs["history"]}
        gone = [e for e in f["history"] if _identity(e) not in held]
        if gone:
            lost_entries[name] = gone
            values = [v for v in dict.fromkeys(e["value"] for e in gone) if v not in {e["value"] for e in theirs["history"]}]
            if values:
                lost_values[name] = values
    return {"lost_entries": lost_entries, "lost_values": lost_values, "fields_lost": fields_lost, "kept_fields": kept}


@dataclass
class BuiltState:
    """The state the run asks its questions over, and how the bad merge went."""

    events: int
    topic_ids: dict[str, str]  # storyline topic key -> id; `redesign` is the original
    original_id: str
    reexplanation_id: str
    outcome: MergeOutcome
    before_original: dict  # the original as stored just before the merge (trimmed)
    before_reexplanation: dict
    survivor: dict  # the survivor as stored after the merge (trimmed)
    loss: dict
    setup_labels: list[str] = field(default_factory=list)

    @property
    def arranged(self) -> bool:
        """The merge kept the re-explanation and dropped the original, as the run needs."""
        return self.outcome.survivor_id == self.reexplanation_id and self.outcome.dropped_id == self.original_id


def build_bad_merge_state(system: System, storyline: Storyline = WEBSITE_REDESIGN,
                          merge_timeout: float = DEFAULT_TIMEOUT_S) -> BuiltState:
    first = storyline.events[0]
    if first.placement != "new_topic" or not first.topic:
        raise ScenarioError("the storyline's first event must create the topic that gets duplicated")
    placeholder = unique_title(TITLE)
    pair_ids = [system.ingest({"placement": "new_topic", "title": f"{placeholder} {n}", "topic_kind": first.topic_kind,
                               "summary": first.summary, "fields": []})["topic_id"] for n in ("first", "second")]
    reexplanation_id, original_id = sorted(pair_ids)  # the merge keeps the lower id (F9)
    ids = {first.topic: original_id}
    # the original's first event writes into the placeholder: the topic exists already under its placeholder title
    written = dataclasses.replace(first, placement="extend_topic", title=None, summary=None, topic_kind=None)
    system.ingest(written.request(ids))
    played = 1
    for event in storyline.events[1:]:
        response = system.ingest(event.request(ids))
        if event.placement == "new_topic":
            ids[event.topic] = response["topic_id"]
        played += 1
    system.ingest({"placement": "extend_topic", "topic_id": reexplanation_id,
                   "fields": [{"name": REEXPLAINED_FIELD, "value": REEXPLAINED_VALUE,
                               "provenance": REEXPLAINED_PROVENANCE}]})
    before_original = trim(system.read_topic(original_id))
    before_reexplanation = trim(system.read_topic(reexplanation_id))
    labels = []
    for topic_id in (reexplanation_id, original_id):
        label = "give the duplicate pair one title (the editor never writes a value)"
        if system.setup_write("patch_topic", label=label, topic_id=topic_id, title=first.title) is None:
            raise ScenarioError("the system has no way to retitle a topic: the bad merge cannot be arranged")
        labels.append(label)
    system.ingest({"placement": "extend_topic", "topic_id": reexplanation_id, "fields": []})  # the merge trigger
    pair = Pair(first.title or "", REEXPLAINED_FIELD, reexplanation_id, original_id, REEXPLAINED_VALUE, REEXPLAINED_VALUE)
    outcome = await_merge(system, pair, merge_timeout, DEFAULT_INTERVAL_S)
    if not outcome.merged:
        raise ScenarioError(f"no merge seen within {merge_timeout:g} s of the trigger")
    survivor = trim(system.read_topic(outcome.survivor_id)) if outcome.survivor_id else None
    if survivor is None:
        raise ScenarioError("the merge left no survivor to read")
    built = BuiltState(events=played, topic_ids=ids, original_id=original_id, reexplanation_id=reexplanation_id,
                       outcome=outcome, before_original=before_original, before_reexplanation=before_reexplanation,
                       survivor=survivor, loss=lost_in_merge(before_original, survivor), setup_labels=labels)
    if not built.arranged:
        raise ScenarioError(f"the merge kept {outcome.survivor_id} and dropped {outcome.dropped_id}; the run needs it to "
                            f"keep the re-explanation {reexplanation_id} and drop the original {original_id}")
    return built


# -- the turns

QUESTIONS = ("Q02", "Q06", "Q11")  # deadline (looks right), then two fields only the original topic held
CASE = "bad-merge"
CASE_TITLE = "Bad merge on upstream: the re-explained Website Redesign is merged over the original"


def _setup_writes(system: System) -> list[dict]:
    return [{"action": e["op"], "label": e["request"]["label"],
             **{k: v for k, v in e["request"].items() if k not in ("action", "label")}} for e in system.log.of_kind("setup")]


def contains_every_word(truth: object, answer: str) -> bool:
    """Does the answer contain every alphanumeric word of the ground truth (case ignored, whole words only)? A hint
    printed beside the hand-grade slot, not a grade: "completed" is not "complete", and a wrong answer can repeat the
    right words."""
    words = lambda text: re.findall(r"[a-z0-9]+", str(text).casefold())  # noqa: E731
    return set(words(truth)) <= set(words(answer))


def state_violation(built: BuiltState, question) -> dict:
    """What the merge cost the question's own field, read from the survivor and the loss (never from the answer)."""
    name = question.field
    lost = built.loss["lost_entries"].get(name, [])
    slot = built.survivor["fields"].get(name)
    return {"present": bool(lost), "condition": "C4" if lost else None, "field": name, "lost_entries": lost,
            "lost_values": built.loss["lost_values"].get(name, []),
            "current_after": None if slot is None else slot["current"]}


def ask(system: System, built: BuiltState, question) -> dict:
    """One storyline question as one chat request; the turn keeps everything the replay prints."""
    request = {"messages": [{"role": "user", "content": question.text}], "provider": "ollama"}
    before = trim(system.read_topic(built.reexplanation_id))
    response = system.chat(request)
    after = trim(system.read_topic(built.reexplanation_id))
    entry = next(e for e in reversed(system.log.entries) if e["kind"] == "chat")
    answer = response.get("reply") or ""
    return {"question": question.id, "ability": question.ability, "text": question.text,
            "ground_truth": question.truth, "topic_key": question.topic, "field": question.field,
            "request": request, "answer": answer,
            "answer_contains_ground_truth": contains_every_word(question.truth, answer),
            "route": {"intent": response.get("intent"), "intent_source": response.get("intent_source"),
                      "tool_calls": [t.get("tool") for t in response.get("tool_log") or []]},
            "latency_ms": entry["latency_ms"], "model": response.get("model"), "provider": response.get("provider"),
            "tool_log": response.get("tool_log") or [],
            "state_violation": state_violation(built, question),
            "topic_changed_by_turn": before != after,
            "hand_grade": dict(EMPTY_GRADE)}


def record_bad_merge(system: System, *, run_id: str, recorded_at: str, command: str = "",
                     ollama_base_url: str | None = None, storyline: Storyline = WEBSITE_REDESIGN,
                     question_ids: tuple[str, ...] = QUESTIONS, merge_timeout: float = DEFAULT_TIMEOUT_S,
                     snapshot: str | None = None, extra: dict | None = None) -> dict:
    """Build the state, ask the questions, return the recording (a plain dict; `save_recording` writes it)."""
    asked = {q.id: q for q in storyline.questions}
    unknown = [q for q in question_ids if q not in asked]
    if unknown:
        raise ScenarioError(f"unknown storyline question(s) {unknown}")
    first = storyline.events[0]
    for q in (asked[i] for i in question_ids):
        if q.topic != first.topic:
            raise ScenarioError(f"{q.id} asks about {q.topic!r}, not the duplicated topic {first.topic!r}")
    built = build_bad_merge_state(system, storyline, merge_timeout)
    turns = [ask(system, built, asked[i]) for i in question_ids]
    return new_recording(
        system.describe(), case=CASE, title=CASE_TITLE, run_id=run_id, recorded_at=recorded_at, command=command,
        snapshot=snapshot, ollama_base_url=ollama_base_url, left_unset=list(LEFT_UNSET), turns=turns, extra=extra,
        state={
            "title": first.title, "events_played": built.events, "topic_ids": built.topic_ids,
            "original_id": built.original_id, "reexplanation_id": built.reexplanation_id,
            "reexplained": {"field": REEXPLAINED_FIELD, "value": REEXPLAINED_VALUE,
                            "provenance": REEXPLAINED_PROVENANCE},
            "merge": {"survivor_id": built.outcome.survivor_id, "dropped_id": built.outcome.dropped_id,
                      "dropped_state": built.outcome.dropped_state.value if built.outcome.dropped_state else None,
                      "window_s": built.outcome.window_s, "arranged": built.arranged},
            "setup_writes": _setup_writes(system),
            "before_merge": {"original": built.before_original, "reexplanation": built.before_reexplanation},
            "after_merge": {"survivor": built.survivor},
            "loss": built.loss})


# -- command line: replay (JSON only) and record (needs the machine: MemState, Ollama, the GPU)

OLLAMA_PORT, PROXY_PORT = 11434, 11435
PROXY_URL = f"http://127.0.0.1:{PROXY_PORT}"
DEFAULT_MODEL = "qwen3.5:2b"


def replay(paths: list[Path], out=None, err=None) -> int:
    """Print the recordings at `paths` (files, or folders holding them). Reads JSON only."""
    out, err = out or sys.stdout, err or sys.stderr
    files: list[Path] = []
    for p in paths:
        files += [p] if p.is_file() else recording_files(p)
    if not files:
        print(f"no recording found in {', '.join(map(str, paths))}", file=err)
        return 1
    for i, path in enumerate(files):
        print(("\n" if i else "") + render_recording(load_recording(path), level=1), file=out)
    return 0


def _port_open(port: int) -> bool:
    import socket
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


class OllamaError(RuntimeError):
    pass


def _listener_pid(port: int) -> int | None:
    out = subprocess.run(["ss", "-H", "-ltnp", f"sport = :{port}"], capture_output=True, text=True).stdout
    found = re.search(r"pid=(\d+)", out)
    return int(found.group(1)) if found else None


def stop_ollama() -> None:
    """SIGTERM whatever listens on Ollama's port and on the proxy's, and wait until both are closed."""
    import os
    import signal
    import time

    for port in (OLLAMA_PORT, PROXY_PORT):
        pid = _listener_pid(port)
        if pid is not None:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    deadline = time.monotonic() + 30
    while (_port_open(OLLAMA_PORT) or _port_open(PROXY_PORT)) and time.monotonic() < deadline:
        time.sleep(0.3)
    if _port_open(OLLAMA_PORT) or _port_open(PROXY_PORT):
        raise OllamaError("Ollama or its proxy is still up 30 s after SIGTERM (or no pid could be found for it)")


@contextmanager
def ollama_running():
    """Ollama and the think-off proxy (`scripts/run_ollama.sh --bg`, ADR 0003) for the length of the block; yields
    whether this call started them. Both are stopped on exit, errors included, also when they were already running:
    the caller holds the machine-wide lock, so a running one is a leftover or the user's own, and the run owns the
    machine until it ends (README, "Chat runs and replay"; ticket 19: Ollama and the proxy are stopped at the end).
    One running without the other is a leftover too: it is stopped and both are started fresh."""
    import time
    import urllib.request

    up = (_port_open(OLLAMA_PORT), _port_open(PROXY_PORT))
    started = not all(up)
    try:
        if started:
            if any(up):
                stop_ollama()
            subprocess.run(["bash", str(REPO_ROOT / "scripts" / "run_ollama.sh"), "--bg"], cwd=REPO_ROOT, check=True)
            deadline = time.monotonic() + 120
            while True:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{OLLAMA_PORT}/api/tags", timeout=2):
                        if _port_open(PROXY_PORT):
                            break
                except OSError:
                    pass
                if time.monotonic() > deadline:
                    raise OllamaError("Ollama did not answer within 120 s")
                time.sleep(0.5)
        yield started
    finally:
        stop_ollama()


def warm_up(model: str) -> float:
    """Load the model through the proxy (Ollama only, no MemState), so turn 1's latency is not the model load.
    Returns the seconds it took; the run states the model was warm."""
    import time
    import urllib.request
    t0 = time.perf_counter()
    req = urllib.request.Request(f"{PROXY_URL}/api/generate", method="POST",
                                 data=json.dumps({"model": model, "prompt": "Reply with OK.", "stream": False}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300):
        pass
    return round(time.perf_counter() - t0, 2)


TWO_WEEKS_VARIANTS = {"--no-router-decides": {"first_intent_override": FIRST_INTENT_OVERRIDE},
                      "--seed-profile": {"seed": True}}
CASES = (CASE, TWO_WEEKS_CASE)  # the order the run of record records them in
CASE_SYSTEM = {CASE: ("upstream", "chat-bad-merge"), TWO_WEEKS_CASE: ("step3", "chat-two-weeks")}


@dataclass
class Recorded:
    saved: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)  # one per case that could not be recorded


def _link(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _record_case(case: str, run: "RunDir", recordings: Path, link_root: Path, flags: tuple[str, ...],
                 environment: dict, command: str, ollama_url: str) -> Path:
    """One chat run on a fresh DB: its server started and stopped here (a step checked out for the run and returned
    after it). The snapshot goes to `<run dir>/snapshots/...` and the recording cites it as `<link_root>/<run id>/...`:
    `link_root` is where the run folder will be (the results root, or `demo/record/` for the run of record), so the
    link resolves from the repository root. A variant take is saved under `attempts/`, never as the scored case."""
    from datetime import date, datetime, timezone
    from demo import evidence
    from demo.adapter import utc_now
    from demo.systems import SYSTEMS

    system_id, tag = CASE_SYSTEM[case]
    spec = SYSTEMS[system_id]
    snapshot = evidence.snapshot_path(system_id, tag)
    try:
        if spec.setup is not None:
            spec.setup(run)
        started_at = utc_now()
        with spec.open(tag, run) as system:
            common = dict(run_id=run.id, recorded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                          command=command, ollama_base_url=ollama_url, snapshot=_link(link_root / run.id / snapshot),
                          extra={"environment": environment})
            recording = (record_bad_merge(system, **common) if case == CASE
                         else record_two_weeks(system, run_day=date.today(), **common,
                                               **{k: v for f in flags for k, v in TWO_WEEKS_VARIANTS[f].items()}))
            captured = evidence.capture(system_id, tag, system, None, started_at, utc_now())
    finally:
        if spec.teardown is not None:
            spec.teardown(run)
    path = run.dir / snapshot
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(captured, indent=2, default=str))
    return save_recording(recording, recordings / "attempts" if is_variant(recording) else recordings)


def record_chats(run: "RunDir", recordings: Path, link_root: Path, command: str, cases: tuple[str, ...] = CASES,
                 flags: tuple[str, ...] = (), log=print) -> Recorded:
    """Record `cases` in `run`, with Ollama and the proxy up for the whole block and stopped after it. A case that fails
    is reported in `errors` and the next one still runs. Used by `record_cli` (one case, a run folder of its own) and
    by `python -m demo.run --chat` (both cases, in the suite's run folder); both hold the machine-wide lock around it."""
    import os

    base = os.environ.get("MEMSTATE_OLLAMA_BASE_URL")
    if base and base.rstrip("/") != PROXY_URL:
        raise OllamaError(f"MEMSTATE_OLLAMA_BASE_URL={base} bypasses the think-off proxy (ADR 0003); unset it")
    model = os.environ.get("MEMSTATE_OLLAMA_MODEL") or DEFAULT_MODEL
    ollama_url = f"{PROXY_URL} (think-off proxy, ADR 0003) -> Ollama :{OLLAMA_PORT}"
    result = Recorded()
    with ollama_running() as started:
        warm = warm_up(model)
        environment = {"model_warmed_up_s": warm, "ollama_started_by_run": started, "ollama_model_setting": model}
        for case in cases:
            log(f"[chat] {case}: recording")
            try:
                result.saved.append(_record_case(case, run, recordings, link_root, flags, environment,
                                                 command, ollama_url))
            except Exception as e:
                result.errors.append(f"{case}: {type(e).__name__}: {e}")
                log(f"[chat] {case}: failed: {e}")
    return result


def record_cli(recordings: Path, case: str = CASE, flags: tuple[str, ...] = ()) -> int:
    """Record one chat run on its own: a fresh DB, a server started and stopped here, Ollama likewise. `bad-merge` runs
    on upstream; `two-weeks` on patch step 3 (its commit checked out in `MemState-patched` for the run, then back on
    `bitemporal`). It holds the machine-wide lock for the whole recording (`demo/server_lock.py`). The run of record
    records both in its own run folder instead: `python -m demo.run --record --chat`."""
    from demo import evidence
    from demo.paths import RESULTS_ROOT, SHARED_ROOT
    from demo.server_lock import server_lock

    run = evidence.new_run_dir(RESULTS_ROOT, SHARED_ROOT / ".runtime" / "gem-suite")
    command = f"cd {REPO_ROOT} && {sys.executable} -m demo.chat_run record {case}" + "".join(f" {f}" for f in flags)
    try:
        with server_lock():
            result = record_chats(run, recordings, RESULTS_ROOT, command, (case,), flags)
    except OllamaError as e:
        print(e, file=sys.stderr)
        return 2
    for error in result.errors:
        print(f"error: {error}", file=sys.stderr)
    for saved in result.saved:
        print(f"recorded {saved} (servers stopped; snapshot under {run.dir / 'snapshots'})")
    return 1 if result.errors else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m demo.chat_run", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    rec = sub.add_parser("record", help="record a chat run (starts MemState and Ollama; run under the lock)")
    rec.add_argument("case", choices=[CASE, TWO_WEEKS_CASE])
    rec.add_argument("--recordings", type=Path, default=RECORDINGS_ROOT, help="where the recording is written (a variant take goes to its attempts/ folder)")
    rec.add_argument("--router-decides", action=argparse.BooleanOptionalAction, default=True,
                     help="two-weeks only, default on: W1 carries no `intent_override`; --no-router-decides forces the "
                          "ingest route for W1 (a variant: the router sends the statement to `query`, F31; a variant take is saved "
                          "under attempts/ and is never the scored case)")
    rec.add_argument("--seed-profile", action="store_true",
                     help="two-weeks only: write one profile topic (Me: job = analyst at Acme) through /v1 first (a variant: "
                          "saved under attempts/, never the scored case)")
    rep = sub.add_parser("replay", help="print recordings: no server, no Ollama, no GPU")
    rep.add_argument("paths", nargs="*", type=Path, help=f"files or folders (default {RECORDINGS_ROOT})")
    args = ap.parse_args(argv)
    if args.mode == "replay":
        return replay(args.paths or [RECORDINGS_ROOT])
    flags = tuple(f for f in TWO_WEEKS_VARIANTS if (not args.router_decides if f == "--no-router-decides" else args.seed_profile))
    if flags and args.case != TWO_WEEKS_CASE:
        ap.error(f"{', '.join(flags)} apply to the two-weeks case only")
    return record_cli(args.recordings, args.case, flags)


if __name__ == "__main__":
    raise SystemExit(main())
