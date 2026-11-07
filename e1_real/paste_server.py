"""A tiny paste service (C6 / C10). LISTABLE=1 exposes /keys. Written 7 Nov 2026."""
import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer

STORE = {}
LISTABLE = os.environ.get("LISTABLE") == "1"


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        if self.path == "/put":
            body = self.rfile.read(int(self.headers["Content-Length"])).decode()
            k = secrets.token_hex(16)
            STORE[k] = body
            self._send(200, k)

    def do_GET(self):
        if self.path == "/keys":
            self._send(200, json.dumps(list(STORE)) if LISTABLE else "[]")
        elif self.path.startswith("/get?k="):
            k = self.path.split("=", 1)[1]
            self._send(200 if k in STORE else 404, STORE.get(k, ""))
        else:
            self._send(404, "")

    def _send(self, code, body):
        self.send_response(code); self.end_headers(); self.wfile.write(body.encode())


HTTPServer(("0.0.0.0", 8080), H).serve_forever()
