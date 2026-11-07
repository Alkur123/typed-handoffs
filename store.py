"""Shared stores whose provenance log is kept by the store, not the agent.

Written 7 Nov 2026 for the Apart Swarm Alignment Hackathon (new code).
Every operation is stamped with the caller's principal, which the environment
assigns and agents cannot read or set. The log is append-only and hash-chained
(each record carries the SHA-256 of the previous record). W3C PROV mapping:
write -> wasGeneratedBy, read/list/stat -> used, principal -> wasAttributedTo.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

ATTRIBUTES = ("content", "filename", "size", "mtime", "existence")


class AccessDenied(Exception):
    pass


@dataclass
class Obj:
    content: str
    writer: str
    mtime: int
    size: int


@dataclass
class Policy:
    """Who may do what on a store. Principals are strings like 'p0'."""
    writers: set | None = None          # None = everyone may write
    readers: set | None = None          # None = everyone may read content
    listers: set | None = None          # None = everyone may list names
    own_only: bool = False              # list/read/stat restricted to the object's writer
    namespaced: bool = False            # each principal sees only its own subtree
    sizes_visible: bool = True          # list() also returns sizes and mtimes
    keyed: bool = False                 # paste-tool semantics: read needs the key
    keys_listable: bool = True          # for keyed stores: may others enumerate keys?
    sanctioned: bool = False            # an officially allowed channel (edges are not covert)

    def may(self, op: str, p: str, obj: Obj | None = None) -> bool:
        if op == "write":
            return self.writers is None or p in self.writers
        if op == "list":
            return self.listers is None or p in self.listers
        if op in ("read", "stat"):
            if self.readers is not None and p not in self.readers:
                return False
            if self.own_only and obj is not None and obj.writer != p:
                return False
            return True
        raise ValueError(op)


class ProvLog:
    def __init__(self):
        self.records: list[dict] = []
        self._prev = "0" * 64

    def add(self, **rec) -> dict:
        rec = dict(rec, i=len(self.records), prev=self._prev)
        h = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()
        rec["h"] = h
        self._prev = h
        self.records.append(rec)
        return rec

    def verify(self) -> bool:
        prev = "0" * 64
        for r in self.records:
            body = {k: v for k, v in r.items() if k != "h"}
            if body["prev"] != prev:
                return False
            if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != r["h"]:
                return False
            prev = r["h"]
        return True


class Store:
    def __init__(self, name: str, policy: Policy, log: ProvLog, clock):
        self.name, self.policy, self.log, self.clock = name, policy, log, clock
        self.objs: dict[str, Obj] = {}

    # Namespacing turns 'x' into 'p3/x' for p3; others never see it.
    def _key(self, p: str, name: str) -> str:
        return f"{p}/{name}" if self.policy.namespaced else name

    def _visible(self, p: str, key: str, obj: Obj) -> bool:
        if self.policy.namespaced and not key.startswith(p + "/"):
            return False
        if self.policy.own_only and obj.writer != p:
            return False
        if self.policy.keyed and not self.policy.keys_listable and obj.writer != p:
            return False
        return True

    def write(self, p: str, name: str, content: str) -> str:
        if not self.policy.may("write", p):
            raise AccessDenied(f"{p} cannot write {self.name}")
        key = self._key(p, name)
        self.objs[key] = Obj(content, p, self.clock(), len(content))
        self.log.add(t=self.clock(), principal=p, op="write", store=self.name, obj=key,
                     attr="content", writer=p)
        return key

    def read(self, p: str, name: str) -> str:
        key = name if (self.policy.namespaced and "/" in name) else self._key(p, name)
        obj = self.objs.get(key)
        if obj is None or not self.policy.may("read", p, obj) or \
                (self.policy.namespaced and not key.startswith(p + "/")):
            self.log.add(t=self.clock(), principal=p, op="read_denied", store=self.name, obj=key,
                         attr="content", writer=None)
            raise AccessDenied(f"{p} cannot read {self.name}:{name}")
        self.log.add(t=self.clock(), principal=p, op="read", store=self.name, obj=key,
                     attr="content", writer=obj.writer)
        return obj.content

    def list(self, p: str) -> list[dict]:
        if not self.policy.may("list", p):
            raise AccessDenied(f"{p} cannot list {self.name}")
        out = []
        for key, obj in sorted(self.objs.items()):
            if not self._visible(p, key, obj):
                continue
            entry = {"name": key.split("/", 1)[1] if self.policy.namespaced else key}
            attrs = ["filename", "existence"]
            if self.policy.sizes_visible:
                entry.update(size=obj.size, mtime=obj.mtime)
                attrs += ["size", "mtime"]
            out.append(entry)
            for a in attrs:
                self.log.add(t=self.clock(), principal=p, op="list", store=self.name, obj=key,
                             attr=a, writer=obj.writer)
        return out

    def stat(self, p: str, name: str) -> dict:
        key = self._key(p, name)
        obj = self.objs.get(key)
        if obj is None or not self.policy.may("stat", p, obj) or not self._visible(p, key, obj):
            raise AccessDenied(f"{p} cannot stat {self.name}:{name}")
        for a in ("size", "mtime", "existence"):
            self.log.add(t=self.clock(), principal=p, op="stat", store=self.name, obj=key,
                         attr=a, writer=obj.writer)
        return {"size": obj.size, "mtime": obj.mtime}


def edges(log: ProvLog, stores: dict[str, Store]) -> list[dict]:
    """Cross-principal read-after-write edges, from the store-side log only.

    An edge A->B exists when B reads, lists or stats an object (or an attribute of it)
    whose recorded writer is A != B. Nothing the agents say is consulted.
    """
    out = []
    for r in log.records:
        if r["op"] in ("read", "list", "stat") and r.get("writer") and r["writer"] != r["principal"]:
            st = stores.get(r["store"])
            out.append({"src": r["writer"], "dst": r["principal"], "store": r["store"],
                        "attr": r["attr"], "op": r["op"], "t": r["t"],
                        "sanctioned": bool(st and st.policy.sanctioned)})
    return out
