"""Runs INSIDE one principal's container (stdlib only). Written 7 Nov 2026.

write   : leave this principal's canary in a shared location (name, content and size carry it)
observe : report which canaries this principal can see, and through which attribute
listen  : serve this principal's canary over TCP (exploratory network probe)
connect : try to read a canary from another container over TCP
"""
import json
import os
import socket
import sys
import urllib.request


def cmd_write(d, canary, mode, name):
    os.umask(0o077 if mode == "0600" else 0o022)
    path = os.path.join(d, name.replace("{c}", canary))
    body = canary + "x" * (ord(canary[4]) % 17)
    try:
        with open(path, "w") as f:
            f.write(body)
        print(json.dumps({"ok": True, "path": path}))
    except OSError as e:
        print(json.dumps({"ok": False, "err": type(e).__name__}))


def cmd_observe(d, canaries):
    seen = {}
    def mark(c, a):
        seen.setdefault(c, set()).add(a)
    try:
        names = os.listdir(d)
    except OSError:
        names = []
    for n in names:
        for c in canaries:
            if c in n:
                mark(c, "filename"); mark(c, "existence")
                try:
                    st = os.stat(os.path.join(d, n))
                    mark(c, "size"); mark(c, "mtime")
                except OSError:
                    pass
                try:
                    with open(os.path.join(d, n)) as f:
                        if c in f.read():
                            mark(c, "content")
                except OSError:
                    pass
    # also try guessed names directly (a receiver that cannot list can still guess)
    for c in canaries:
        for n in (f"obj_{c}", f"log_{c}"):
            p = os.path.join(d, n)
            try:
                with open(p) as f:
                    if c in f.read():
                        mark(c, "content")
            except OSError:
                pass
    print(json.dumps({c: sorted(a) for c, a in seen.items()}))


def cmd_paste_put(url, canary):
    req = urllib.request.Request(url + "/put", data=canary.encode(), method="POST")
    print(json.dumps({"key": urllib.request.urlopen(req, timeout=5).read().decode()}))


def cmd_paste_observe(url, canaries):
    seen = {}
    try:
        keys = json.loads(urllib.request.urlopen(url + "/keys", timeout=5).read())
    except Exception:
        keys = []
    for k in keys:
        try:
            body = urllib.request.urlopen(url + "/get?k=" + k, timeout=5).read().decode()
        except Exception:
            continue
        for c in canaries:
            if c in body:
                seen.setdefault(c, set()).update({"content", "existence"})
    print(json.dumps({c: sorted(a) for c, a in seen.items()}))


def cmd_listen(port, canary):
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port)); s.listen(8)
    while True:
        c, _ = s.accept(); c.sendall(canary.encode()); c.close()


def cmd_connect(host, port):
    try:
        s = socket.create_connection((host, port), timeout=3)
        print(json.dumps({"got": s.recv(64).decode()}))
    except OSError as e:
        print(json.dumps({"got": None, "err": type(e).__name__}))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"write": lambda: cmd_write(a[1], a[2], a[3], a[4]),
     "observe": lambda: cmd_observe(a[1], json.loads(a[2])),
     "paste_put": lambda: cmd_paste_put(a[1], a[2]),
     "paste_observe": lambda: cmd_paste_observe(a[1], json.loads(a[2])),
     "listen": lambda: cmd_listen(int(a[1]), a[2]),
     "connect": lambda: cmd_connect(a[1], int(a[2]))}[a[0]]()
