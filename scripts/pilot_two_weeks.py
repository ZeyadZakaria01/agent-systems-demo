#!/usr/bin/env python3
"""Pilot for the "two weeks ago" chat case: where does a take break, the router or the model?

Records N takes per (model, route setting) with `demo.chat.run record two-weeks` into a scratch folder (never
`runs/recordings/`), then prints one row per take and a per-setting summary: W1's route, whether W1 wrote a field, the
stored start date's match (within ±1 day of the truth, from the value or `valid_from`), and whether W2 says four weeks.
The matches are the recorder's hints, not grades. Each take starts and stops MemState (step 3) and Ollama under the
machine-wide lock.

    .venv/bin/python scripts/pilot_two_weeks.py --models qwen3.5:2b,qwen3.5:4b --takes 3 --out /tmp/pilot
    .venv/bin/python scripts/pilot_two_weeks.py --summarise /tmp/pilot      # re-print without recording
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SETTINGS = {"router": (), "ingest": ("--no-router-decides",)}  # router decides W1's route / W1 forced to ingest


def record(model: str, setting: str, takes: int, out: Path) -> None:
    folder = out / model.replace(":", "_") / setting
    for n in range(1, takes + 1):
        print(f"[pilot] {model} {setting} take {n}/{takes}", flush=True)
        rc = subprocess.run(
            [
                sys.executable,
                "-m",
                "demo.chat.run",
                "record",
                "two-weeks",
                "--recordings",
                str(folder),
                *SETTINGS[setting],
            ],
            cwd=REPO,
            env={**os.environ, "MEMSTATE_OLLAMA_MODEL": model},
        ).returncode
        if rc:
            print(f"[pilot] take failed (exit {rc})", flush=True)


def row(rec: dict) -> dict:
    w1, w2 = rec["turns"]
    written = w1.get("written") or []
    return {
        "route": w1["route"]["intent"],
        "wrote": bool(written),
        "start": bool(w1["stored_start_date"]["within_tolerance"]),
        "valid_from": [e.get("valid_from") for e in written],
        "values": [e.get("value") for e in written],
        "four_weeks": bool(w2.get("answer_contains_ground_truth")),
        "w2": " ".join(str(w2["answer"]).split())[:160],
    }


def summarise(out: Path) -> None:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for path in sorted(out.rglob("two-weeks-*.json")):
        model, setting = path.relative_to(out).parts[:2]
        groups[(model, setting)].append(row(json.loads(path.read_text())))
    print(
        "| model | W1 route | takes | routed ingest/both | W1 wrote | start date within ±1 day | W2 says four weeks |"
    )
    print("|---|---|---|---|---|---|---|")
    for (model, setting), rows in sorted(groups.items()):
        n = len(rows)
        print(
            f"| {model} | {setting} | {n} | {sum(r['route'] != 'query' for r in rows)}/{n} | "
            f"{sum(r['wrote'] for r in rows)}/{n} | {sum(r['start'] for r in rows)}/{n} | "
            f"{sum(r['four_weeks'] for r in rows)}/{n} |"
        )
    for (model, setting), rows in sorted(groups.items()):
        for i, r in enumerate(rows, 1):
            print(
                f"- {model} {setting} #{i}: route={r['route']} values={r['values']} valid_from={r['valid_from']} "
                f"W2: {r['w2']}"
            )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--models", default="qwen3.5:2b")
    ap.add_argument("--settings", default="router,ingest", help=f"comma-separated: {', '.join(SETTINGS)}")
    ap.add_argument("--takes", type=int, default=3)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--summarise", type=Path, help="print the table for an existing pilot folder and exit")
    args = ap.parse_args()
    if args.summarise:
        summarise(args.summarise)
        return 0
    if not args.out or str(args.out.resolve()).startswith(str(REPO / "runs" / "recordings")):
        ap.error("--out is a scratch folder outside runs/recordings/")
    for model in args.models.split(","):
        for setting in args.settings.split(","):
            record(model, setting, args.takes, args.out)
    summarise(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
