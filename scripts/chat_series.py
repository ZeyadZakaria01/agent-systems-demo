#!/usr/bin/env python3
"""Record a series of chat takes on a rate-limited provider, spending quota only on takes that can finish.

    .venv/bin/python scripts/chat_series.py bad-merge --takes 10 --provider groq --model openai/gpt-oss-20b \
        --out demo/chat-series/gpt-oss-20b/bad-merge

One take at a time with `demo.chat_run record`. Resumes: takes already in `--out` count. Before each take on Groq, one
1-token request reads the free-tier quota left today (`x-ratelimit-remaining-requests`); the requests the last take
used (the drop between two readings, minus the reading itself) estimate the next take, which starts only if it fits
with a 20% margin. The series stops at the first failed take and never retries it (a failed take saves nothing, and
MemState retries a rate-limited call 3 times at most, `scripts/run_memstate.sh`). The key is read from `MemState/.env`
and never printed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MARGIN = 1.2


def take_fits(remaining_requests: int | None, per_take: int | None) -> bool:
    """Start a take only when the quota left can finish it; before the first take the cost is unknown: allow one."""
    if remaining_requests is None or per_take is None:
        return True
    return remaining_requests >= per_take * MARGIN


def groq_key() -> str:
    for line in (REPO / "MemState" / ".env").read_text().splitlines():
        m = re.match(r"\s*GROQ_API_KEY\s*=\s*(.*)$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    raise SystemExit("no GROQ_API_KEY in MemState/.env")


def groq_quota(model: str) -> dict:
    """One 1-token request; returns the rate-limit headers. A 401 or 429 here stops the series before any take."""
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": "ok"}], "max_tokens": 1}).encode()
    req = urllib.request.Request(GROQ_URL, data=body, method="POST",
                                 headers={"Authorization": f"Bearer {groq_key()}", "Content-Type": "application/json",
                                          "User-Agent": "gem-conformance-suite/1.0"})  # Cloudflare blocks urllib's default (1010)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            h = resp.headers
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Groq refused the quota check: HTTP {e.code} {e.read()[:200]!r}")
    def num(name):
        v = h.get(name)
        return int(v) if v and v.isdigit() else None
    return {"requests_left_today": num("x-ratelimit-remaining-requests"), "requests_per_day": num("x-ratelimit-limit-requests"),
            "tokens_left_minute": num("x-ratelimit-remaining-tokens"), "tokens_per_minute": num("x-ratelimit-limit-tokens")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("case", choices=["bad-merge", "two-weeks"])
    ap.add_argument("--takes", type=int, required=True, help="total takes wanted in --out (existing ones count)")
    ap.add_argument("--provider", choices=["ollama", "groq"], default="groq")
    ap.add_argument("--model", required=True, help="Groq model id, e.g. openai/gpt-oss-20b (or the Ollama model)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "GEM_CHAT_PROVIDER": args.provider,
           ("MEMSTATE_GROQ_MODEL" if args.provider == "groq" else "MEMSTATE_OLLAMA_MODEL"): args.model}
    per_take = None
    before = groq_quota(args.model) if args.provider == "groq" else None
    if before:
        print(f"[series] quota: {before}", flush=True)
    while (done := len(list(args.out.glob(f"{args.case}-*.json")))) < args.takes:
        left = before["requests_left_today"] if before else None
        if not take_fits(left, per_take):
            print(f"[series] stop: {left} requests left today, a take needs about {per_take}; resume tomorrow", flush=True)
            return 3
        print(f"[series] {args.case} take {done + 1}/{args.takes}", flush=True)
        rc = subprocess.run([sys.executable, "-m", "demo.chat_run", "record", args.case, "--recordings", str(args.out)],
                            cwd=REPO, env=env).returncode
        if rc:
            print(f"[series] stop: take {done + 1} failed (exit {rc}); nothing saved, not retried", flush=True)
            return rc
        if args.provider == "groq":
            after = groq_quota(args.model)
            if before["requests_left_today"] is not None and after["requests_left_today"] is not None:
                per_take = max(1, before["requests_left_today"] - after["requests_left_today"] - 1)
            print(f"[series] take used about {per_take} requests; quota now {after}", flush=True)
            before = after
    print(f"[series] done: {args.takes} takes in {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
