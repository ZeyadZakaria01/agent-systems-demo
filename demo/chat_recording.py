"""Chat recordings: save, load, render (replay) and the chat-case section of the scorecard.

A recording is one JSON file per chat run under `demo/recordings/` (tracked: it is evidence of record, n = 1 per
case). Nothing here starts a server, calls Ollama or imports `httpx`: replay reads the file and prints it, so
interview day does not depend on the laptop's GPU.

Shape (schema 1): `case` ("bad-merge", "two-weeks"), `title`, `run_id`, `recorded_at`, `command`, `system`
(label, URL, DB path, commit, engine), `llm` (provider, model, base URL, the settings the run left unset), `state`
(how the state was built; for the bad merge what the merge lost, for the two-weeks run the dates), `turns` (one per
question: `question`, `ability`, `text`, `ground_truth`, `answer`, `answer_contains_ground_truth` (a hint, not a
grade: every word of the ground truth in the answer, or the rule named in `hint_rule`), `route`, `latency_ms`,
`model`, `provider`, `tool_log`, `model_grade` once `python -m demo.model_grade` has graded the turn (`demo/model_grade.py`), and
`reviewer_grade` once the blind reviewer's grade is applied (`demo/review_grade.py`)). A case adds its own
per-turn evidence under its own key, which the renderer prints only when a turn carries it: `state_violation` and
`topic_changed_by_turn` (bad merge); `reference_time`, `graded_on`, `written`, `topics_created` and
`stored_start_date` (two weeks).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from demo.paths import REPO_ROOT

SCHEMA = 1
RECORDINGS_ROOT = REPO_ROOT / "demo" / "recordings"
LEFT_UNSET = ("no `intent_override`", "no `model` in the request (the server's `MEMSTATE_OLLAMA_MODEL`)", "no Groq",
              "no judge")  # what every chat run leaves to MemState's defaults


PROVIDERS = ("ollama", "groq")


def chat_provider() -> str:
    """The LLM provider chat turns ask for (`GEM_CHAT_PROVIDER`, set by `--provider`): ollama (local) or groq."""
    import os
    provider = os.environ.get("GEM_CHAT_PROVIDER") or "ollama"
    if provider not in PROVIDERS:
        raise ValueError(f"GEM_CHAT_PROVIDER={provider!r}: use one of {PROVIDERS}")
    return provider


def new_recording(described: dict, *, case: str, title: str, run_id: str, recorded_at: str, command: str,
                  snapshot: str | None, ollama_base_url: str | None, left_unset: list[str], state: dict,
                  turns: list[dict], extra: dict | None = None) -> dict:
    """The recording both chat runs write: the envelope (case, run, system as `describe()` states it, the LLM) around
    the case's own `state` and `turns`. `extra` is merged last (the run's environment)."""
    return {
        "schema": SCHEMA, "case": case, "title": title, "run_id": run_id, "recorded_at": recorded_at,
        "command": command, "snapshot": snapshot,
        "system": {"label": described.get("system"), "url": described.get("url"), "db_path": described.get("db_path"),
                   "commit": described.get("commit"), "engine": described.get("engine"),
                   "source_dir": described.get("source_dir")},
        "llm": {"provider": next((t["provider"] for t in turns if t.get("provider")), chat_provider()), "model": next((t["model"] for t in turns if t["model"]), None),
                "base_url": ollama_base_url or "(not stated)", "left_unset": list(left_unset)},
        "state": state, "turns": turns, **(extra or {})}


def is_variant(recording: dict) -> bool:
    """A take that deviates from the case as the spec states it (W1's route forced, or a profile topic seeded): kept as
    evidence, never the scored case."""
    state = recording.get("state") or {}
    return bool(state.get("first_intent_override") or state.get("seed"))


def save_recording(recording: dict, root: Path = RECORDINGS_ROOT) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{recording['case']}-{recording['run_id']}.json"
    path.write_text(json.dumps(recording, indent=2, ensure_ascii=False) + "\n")
    return path


def load_recording(path: Path) -> dict:
    recording = json.loads(Path(path).read_text())
    if not isinstance(recording, dict) or recording.get("schema") != SCHEMA:
        raise ValueError(f"{path}: not a chat recording (schema {SCHEMA} expected, "
                         f"found {recording.get('schema') if isinstance(recording, dict) else type(recording).__name__})")
    return recording


def recording_files(root: Path = RECORDINGS_ROOT) -> list[Path]:
    return sorted(root.glob("*.json")) if root.is_dir() else []


def latest_per_case(root: Path = RECORDINGS_ROOT) -> list[dict]:
    """The newest recording of every case in `root` (by `recorded_at`), ordered by case name; each carries its
    file name as `file`. Files that are not recordings are skipped, and so are variant takes (`is_variant`): the
    scored case is the newest take run as the spec states it."""
    newest: dict[str, dict] = {}
    for path in recording_files(root):
        try:
            rec = load_recording(path)
        except (ValueError, json.JSONDecodeError):
            continue
        if is_variant(rec):
            continue
        rec = {**rec, "file": path.name}
        if rec["case"] not in newest or rec["recorded_at"] > newest[rec["case"]]["recorded_at"]:
            newest[rec["case"]] = rec
    return [newest[c] for c in sorted(newest)]


def results_payload(recordings: list[dict]) -> list[dict]:
    """The recordings as `results.json` carries them: whole, minus each turn's tool log (the file keeps it)."""
    return [{**{k: v for k, v in rec.items() if k != "turns"},
             "turns": [{k: v for k, v in t.items() if k != "tool_log"} for t in rec["turns"]]} for rec in recordings]


# -- rendering


def _shown(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value


def _entry(e: dict) -> str:
    why = f", reason: {e['why_changed']}" if e.get("why_changed") else ""
    return f"{_shown(e['value'])} ({e.get('provenance')}{why})"


def violation_text(turn: dict, loss: dict | None) -> str:
    v = turn["state_violation"]
    if v["present"]:
        values = f"; values gone from the history: {', '.join(map(_shown, v['lost_values']))}" if v["lost_values"] else ""
        return (f"{v['condition']} violated on {v['field']}: history entries lost {'; '.join(_entry(e) for e in v['lost_entries'])}"
                f"{values}; current value now {_shown(v['current_after'])}")
    elsewhere = ""
    if loss and loss.get("lost_entries"):
        elsewhere = f"; the merge did lose history elsewhere ({', '.join(loss['lost_entries'])})"
    return f"none on {v['field']} (current value {_shown(v['current_after'])}, no entry lost){elsewhere}"


def _written(e: dict) -> str:
    dated = f", valid_from {e['valid_from']}" if e.get("valid_from") else ""
    return f"{e['title'] or e['topic_id']} / {e['field']} = {_shown(e['value'])} ({e.get('provenance')}{dated})"


def start_date_text(start: dict) -> str:
    found = "; ".join(f"{c['date']} (in the {c['source'].replace('_', ' ')}: {_shown(c['from'])})" for c in start["candidates"])
    verdict = "yes" if start["within_tolerance"] else "no"
    return (f"dates read from the stored entries: {found or 'none'}; one within {start['tolerance_days']} day of "
            f"{start['truth']}: {verdict} (a date match, not a grade)")


def render_turn(turn: dict, loss: dict | None) -> list[str]:
    """One turn. A case adds its own per-turn evidence under its own key (`state_violation` for the bad merge,
    `written` and `stored_start_date` for the two-weeks run); a key a turn does not carry is not printed."""
    route = turn["route"]
    tools = ", ".join(route["tool_calls"]) if route["tool_calls"] else "none"
    lines = [f"- **{turn['question']}** [{turn['ability']}] {turn['text']}"]
    if "reference_time" in turn:
        lines.append(f"  - reference time sent: {turn['reference_time']}")
    lines += [f"  - ground truth: {_shown(turn['ground_truth'])}",
              f"  - answer: {' '.join(str(turn['answer']).split()) or '(empty)'}"]
    if "answer_contains_ground_truth" in turn:
        contains = "yes" if turn["answer_contains_ground_truth"] else "no"
        rule = turn.get("hint_rule") or "answer contains every word of the ground truth"
        lines.append(f"  - {rule}: {contains} (a match, not a grade)")
    lines += [f"  - route: {route['intent']} ({route['intent_source']}); tool calls: {tools}",
              f"  - latency: {turn['latency_ms']:,.0f} ms; model {turn['model']} ({turn['provider']})"]
    if "written" in turn:
        wrote = "; ".join(_written(e) for e in turn["written"])
        made = [t["title"] or t["topic_id"] for t in turn.get("topics_created") or []]
        lines.append(f"  - entries the turn wrote: {wrote or 'none'}" + (f"; topics it created: {', '.join(made)}" if made else ""))
    if "stored_start_date" in turn:
        lines.append(f"  - stored start date: {start_date_text(turn['stored_start_date'])}")
    if "state_violation" in turn:
        lines.append(f"  - state violation: {violation_text(turn, loss)}")
    if "topic_changed_by_turn" in turn:
        lines.append(f"  - state changed by the turn itself: {'yes' if turn['topic_changed_by_turn'] else 'no'}")
    if turn.get("graded_on"):
        lines.append(f"  - graded on: {turn['graded_on']}")
    if "model_grade" in turn:
        model = turn["model_grade"]
        lines.append(f"  - model grade ({model['grader']}): {model['grade']}; note: {model['note'] or '(empty)'}")
    if turn.get("reviewer_grade"):
        review = turn["reviewer_grade"]
        lines.append(f"  - reviewer grade ({review['grader']}): {review['grade']}; note: {review['note'] or '(empty)'}")
    return lines


def render_state(rec: dict) -> list[str]:
    state, merge, loss = rec["state"], rec["state"]["merge"], rec["state"]["loss"]
    window = f" {merge['window_s']:.2f} s after the trigger" if merge.get("window_s") is not None else ""
    lines = [f"{state['events_played']} storyline events and the re-explained {state['title']} (`{state['reexplanation_id']}`, "
             f"{state['reexplained']['field']} = {_shown(state['reexplained']['value'])}) were written through `/v1`; "
             f"the merge{window} kept `{merge['survivor_id']}` and {merge['dropped_state']} `{merge['dropped_id']}` "
             f"(the original; {'as arranged' if merge['arranged'] else 'NOT as arranged'})."]
    gone = "; ".join(f"{name}: {', '.join(_entry(e) for e in entries)}" for name, entries in loss["lost_entries"].items())
    lines.append(f"The merge lost: {gone or 'no history entry'}. Fields only the original held and still on the survivor: "
                 f"{', '.join(f for f in loss['kept_fields'] if f not in loss['lost_entries']) or 'none'}"
                 f"{'; fields lost outright: ' + ', '.join(loss['fields_lost']) if loss['fields_lost'] else ''}.")
    return lines


def render_two_weeks_state(rec: dict) -> list[str]:
    d = rec["state"]["dates"]
    shifted = (f"the story (Oct 6, Oct 20) is shifted by {d['shift_days']:+d} day(s) so that its last day is the run day"
               if d["shift_days"] else "the story's own dates (Oct 6, Oct 20) fall on the run day")
    forced = rec["state"].get("first_intent_override")
    route = (f" The first request forces the route (`intent_override: {forced}`), a variant of the case; the router decides "
             "the second." if forced else " Both routes are the router's.")
    seed = rec["state"].get("seed")
    first = seed["request"]["fields"][0] if seed else None
    start = (f"one profile topic seeded through `/v1` ({seed['request']['title']}: {first['name']} = {first['value']}, "
             f"from {first['valid_from'][:10]})" if seed else "nothing written through `/v1` and no topic seeded")
    return [f"A fresh database: {start}. Two separate chat requests follow: reference time {d['first_reference_time']} "
            f"(\"two weeks ago\" means {d['start_date']}), then reference time {d['second_reference_time']} (the run day, "
            f"{d['run_day']}; {shifted}).{route}"]


def render_recording(rec: dict, level: int = 2) -> str:
    """One recording as Markdown (replay prints it, the scorecard embeds it one level deeper)."""
    system, llm = rec["system"], rec["llm"]
    h = "#" * level
    lines = [f"{h} {rec['title']}", "",
             f"Recorded {rec['recorded_at']} (run `{rec['run_id']}`, n = 1, graded by Sonnet and a blind reviewer). System: {system['label']}, "
             f"commit {(system.get('commit') or 'n/a')[:7]}, {system.get('engine') or 'engine n/a'}, DB `{system.get('db_path')}`. "
             f"LLM: {llm['provider']} `{llm['model']}` at {llm['base_url']}; "
             f"{'; '.join(llm['left_unset'])}.", ""]
    if rec["case"] == "bad-merge":
        lines += render_state(rec) + [""]
    elif rec["case"] == "two-weeks":
        lines += render_two_weeks_state(rec) + [""]
    lines += [f"{h}# Turns", ""]
    for turn in rec["turns"]:
        lines += render_turn(turn, rec["state"].get("loss"))
    return "\n".join(lines)


def render_chat_cases(recordings: list[dict], level: int = 3) -> str:
    """The scorecard's chat-case section, or "" when no recording exists (the output then stays unchanged)."""
    if not recordings:
        return ""
    body = "\n\n".join(render_recording({**rec, "title": f"{rec['title']} (`{rec['file']}`)"}, level + 1)
                       for rec in recordings)
    return (f"{'#' * level} Chat cases (recorded, n = 1 each, graded by Sonnet and a blind reviewer; no verdict)\n\n"
            "Each case is one recorded Ollama chat run on MemState, replayed from `demo/recordings/` without a server "
            "(`python -m demo.chat_run replay`). Each turn carries Sonnet's grade and, once applied, the blind reviewer's (`demo/model_grade.py`, `demo/review_grade.py`). A recording is one "
            "sample of a 2B model: the other takes of a case are in `demo/recordings/attempts/`, and `docs/journal.md` says "
            "how many were made.\n\n" + body)
