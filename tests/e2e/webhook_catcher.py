"""Tiny HTTP receiver for outbound integration tests (standard library only).

Every POST is recorded and answered with 200 {"_id": "catcher-<n>"}; GET /received returns the
recorded requests as JSON. Point SLACK_WEBHOOK_URL, WEBHOOK_URL, THEHIVE_URL ... at it, e.g.:
    docker run -d --name catcher --network esm-siem_default -v "$PWD/tests/e2e:/t" \
      python:3.12-slim python /t/webhook_catcher.py
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RECEIVED: list[dict] = []


class Handler(BaseHTTPRequestHandler):
    def _reply(self, status: int, body: object) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode(errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = raw
        RECEIVED.append({"path": self.path, "authorization": self.headers.get("Authorization"),
                         "body": body})
        self._reply(200, {"_id": f"catcher-{len(RECEIVED)}"})

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/received"):
            self._reply(200, RECEIVED)
        else:
            self._reply(404, {"error": "not found"})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.command} {self.path}", flush=True)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
