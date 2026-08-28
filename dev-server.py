#!/usr/bin/env python3
"""Local dev server for Dajia Talks.

Serves the app and mocks the two Firebase Realtime Database REST endpoints the
rooms feature uses (GET/PUT /rooms/<id>.json), storing rooms in memory. The app
auto-targets this mock when opened on localhost, so the full create/join/answer
flow works with no real database.

    python3 dev-server.py   ->  http://localhost:8123
"""
import http.server
import json
import os
import re
import socketserver
import urllib.parse

os.chdir(os.path.dirname(os.path.abspath(__file__)))

STORE = {}
CH_STORE = {}
ROOM = re.compile(r"/rooms/([A-Za-z0-9]+)\.json")


class Handler(http.server.SimpleHTTPRequestHandler):
    def _room_id(self):
        m = ROOM.fullmatch(self.path.split("?")[0])
        return m.group(1) if m else None

    def _send_json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        rid = self._room_id()
        if rid is None:
            return super().do_GET()
        self._send_json(STORE.get(rid))  # missing room -> null, like RTDB

    def do_PUT(self):
        rid = self._room_id()
        if rid is None:
            self.send_response(404)
            self.end_headers()
            return
        n = int(self.headers.get("Content-Length", 0))
        STORE[rid] = json.loads(self.rfile.read(n) or b"null")
        self._send_json({})

    def do_POST(self):
        # Mock of the ClickHouse HTTP interface used by the "clickhouse" adapter.
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if parsed.path != "/" or "query" not in qs:
            self.send_response(404)
            self.end_headers()
            return
        query = qs["query"][0].lstrip()
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n)
        if query.upper().startswith("SELECT"):
            rid = qs.get("param_id", [None])[0]
            data = CH_STORE.get(rid)
            out = (json.dumps({"data": data}) + "\n") if data is not None else ""
            payload = out.encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif query.upper().startswith("INSERT"):
            row = json.loads(body)
            CH_STORE[row["id"]] = row["data"]
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *args):
        pass


socketserver.ThreadingTCPServer.allow_reuse_address = True
with socketserver.ThreadingTCPServer(("127.0.0.1", 8123), Handler) as srv:
    print("dev server on http://localhost:8123")
    srv.serve_forever()
