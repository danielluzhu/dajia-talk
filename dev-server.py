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
CHAT_STORE = {}
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
        if query.upper().startswith("SELECT") and "dajia.chat" in query:
            key = (qs.get("param_r", [""])[0], qs.get("param_d", [""])[0])
            rows = CHAT_STORE.get(key, [])
            payload = "".join(json.dumps(r) + "\n" for r in rows).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif query.upper().startswith("INSERT") and "dajia.chat" in query:
            row = json.loads(body)
            import time
            CHAT_STORE.setdefault((row["room"], row["day"]), []).append(
                {"id": row["id"], "member": row["member"], "text": row["text"], "at": int(time.time() * 1000)})
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif query.upper().startswith("SELECT") and "dajia.world" in query:
            # canned world digest so the "Beyond your table" card is testable locally
            q = int(qs.get("param_q", ["0"])[0])
            if q % 2 == 0:
                digest = {"type": "poll", "n": 100, "votes": [28, 41, 17, 14][:4],
                          "line": "The world leans 'Pan-fried' — 41 of 100."}
            else:
                digest = {"type": "free", "n": 100,
                          "s": {"warm": 44, "funny": 26, "wistful": 19, "thoughtful": 11},
                          "themes": [["kitchen", 21], ["grandmother", 17], ["rain", 12], ["summer", 9], ["music", 7]],
                          "words": {"summer": 14, "kitchen": 21, "warm": 9},
                          "quotes": [{"name": "Amara", "text": "Woodsmoke and cardamom, my aunt's kitchen every single winter.", "s": "warm"},
                                     {"name": "Kenji", "text": "Chlorine. Swim practice at 6am, and somehow I miss it.", "s": "funny"}],
                          "line": "Mostly warm answers out there — 'kitchen' and 'grandmother' came up again and again."}
            payload = (json.dumps({"digest": json.dumps(digest)}) + "\n").encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif query.upper().startswith("SELECT"):
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
