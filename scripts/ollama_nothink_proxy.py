#!/usr/bin/env python3
"""Forward Ollama API calls, defaulting `think` to false on /api/chat and /api/generate.

MemState's Ollama client sends no `think` field (llm/ollama_chat.py, llm/intent_router.py), and
qwen3.5 thinks by default; Ollama's Modelfile has no `think` parameter and qwen3.5 ignores
`/no_think`. Pointing MEMSTATE_OLLAMA_BASE_URL at this proxy turns thinking off without
modifying MemState. Requests that set `think` explicitly are passed through unchanged.

Usage: ollama_nothink_proxy.py [LISTEN_PORT] [UPSTREAM_URL]   (defaults: 11435, http://127.0.0.1:11434)
"""
import json
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 11435
UPSTREAM = (sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:11434").rstrip("/")
THINK_PATHS = ("/api/chat", "/api/generate")


class Proxy(BaseHTTPRequestHandler):
    def _forward(self) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)) or None
        if body and self.command == "POST" and self.path in THINK_PATHS:
            payload = json.loads(body)
            payload.setdefault("think", False)
            body = json.dumps(payload).encode()
        req = urllib.request.Request(UPSTREAM + self.path, data=body, method=self.command)
        req.add_header("Content-Type", self.headers.get("Content-Type", "application/json"))
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                status, ctype, data = resp.status, resp.headers.get("Content-Type"), resp.read()
        except urllib.error.HTTPError as err:
            status, ctype, data = err.code, err.headers.get("Content-Type"), err.read()
        self.send_response(status)
        self.send_header("Content-Type", ctype or "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = do_DELETE = _forward

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("nothink-proxy %s\n" % (fmt % args))


if __name__ == "__main__":
    print(f"nothink-proxy 127.0.0.1:{PORT} -> {UPSTREAM}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Proxy).serve_forever()
