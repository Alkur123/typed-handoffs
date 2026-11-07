"""E1: a model-free isolation certificate (PREREGISTRATION.md section 3).

The sweep fills Kemmerer's Shared Resource Matrix (ACM TOCS 1983) by execution
instead of by analyst judgement: for every shared store and every attribute, each
principal tries to modify it with its own canary, and every other principal tries
every reference primitive. An (attribute, sender, receiver) cell is an OPEN storage
channel when the receiver can observe something the sender alone controls.
Timing channels are out of scope by design (H5).
"""
from __future__ import annotations

import itertools
import json
import secrets
import sys

import configs
from store import AccessDenied, ProvLog, Store, Policy

PRINCIPALS = ["p0", "p1", "p2", "p3"]


def make_world(cid: str, principals=PRINCIPALS):
    log = ProvLog()
    tick = {"t": 0}

    def clock():
        tick["t"] += 1
        return tick["t"]

    stores = {name: Store(name, pol, log, clock) for name, pol in configs.build(cid, principals).items()}
    return log, stores


def probe(cid: str, principals=PRINCIPALS, seed: int | None = None) -> dict:
    """Run the sweep on one configuration. Returns the matrix and the open channels."""
    rng = secrets.SystemRandom() if seed is None else __import__("random").Random(seed)
    log, stores = make_world(cid, principals)
    canary = {p: "CNRY" + "".join(rng.choice("ABCDEFGHJKMNPQRSTUVWXYZ23456789") for _ in range(8))
              for p in principals}
    open_channels = []
    matrix = {}
    for sname, st in stores.items():
        # Each sender writes an object whose NAME, CONTENT and SIZE all carry its canary.
        # Size carries the canary's first byte as a length, so it is sender-controlled.
        written = {}
        for s in principals:
            body = canary[s] + "x" * (ord(canary[s][4]) % 17)
            try:
                written[s] = st.write(s, f"obj_{canary[s]}", body)
            except AccessDenied:
                pass
        for s, r in itertools.permutations(principals, 2):
            if s not in written:
                continue
            seen = set()
            # filename / existence / size / mtime via list
            try:
                for e in st.list(r):
                    if canary[s] in e["name"]:
                        seen.update({"filename", "existence"})
                        if "size" in e:
                            seen.update({"size", "mtime"})
            except AccessDenied:
                pass
            # content via read, by the name the sender used
            try:
                if canary[s] in st.read(r, f"obj_{canary[s]}"):
                    seen.add("content")
            except AccessDenied:
                pass
            # size / mtime / existence via stat
            try:
                st.stat(r, f"obj_{canary[s]}")
                seen.update({"size", "mtime", "existence"})
            except AccessDenied:
                pass
            for a in sorted(seen):
                open_channels.append({"store": sname, "attr": a, "sender": s, "receiver": r})
            matrix[f"{sname}|{s}->{r}"] = sorted(seen)
    verdict = "OPEN" if open_channels else "CLOSED"
    return {"config": cid, "verdict": verdict, "open_channels": open_channels,
            "matrix": matrix, "log_records": len(log.records), "log_chain_ok": log.verify()}


def main(repeats: int = 3) -> int:
    results, ok = [], True
    for cid in configs.EXPECTED:
        verdicts = {probe(cid)["verdict"] for _ in range(repeats)}
        det = len(verdicts) == 1
        v = verdicts.pop() if det else "NONDETERMINISTIC"
        hit = v == configs.EXPECTED[cid]
        ok &= hit and det
        attrs = sorted({c["attr"] for c in probe(cid, seed=1)["open_channels"]})
        results.append({"config": cid, "description": configs.DESCRIPTION[cid], "expected": configs.EXPECTED[cid],
                        "observed": v, "deterministic": det, "correct": hit, "open_attributes": attrs})
    for r in results:
        print(f"{r['config']:4} expected {r['expected']:6} observed {r['observed']:6} "
              f"{'OK ' if r['correct'] else 'MISS'} attrs={r['open_attributes']}  {r['description']}")
    n = sum(r["correct"] for r in results)
    print(f"H1: {n}/{len(results)} correct, deterministic over {repeats} repeats: {all(r['deterministic'] for r in results)}")
    json.dump(results, open("results_e1.json", "w"), indent=2)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
