"""A4.17 metadata sweep against real Docker isolation. Written 7 Nov 2026 (evening).

Directory configurations only (C1-C5, C7-C9). Senders write ONE AT A TIME; before and after each write,
every other principal takes a side-effect-free metadata snapshot of its mount (probe_agent.py meta):
directory mtime/ctime/nlink/size, statvfs free blocks/inodes, and stat()/errno on the sender's guessed
object name. A field that changes across the sender's write is an attributed channel sender -> receiver.
A null round (no write between snapshots) measures noise first. Expected verdicts are NOT changed
(AMENDMENTS A4.17): a CLOSED configuration in which any attribute moves is reported as OPEN.

Usage: python run_e1_meta.py
"""
import json
import random

from run_e1_real import DIRCFG, EXPECTED, IMG, N, PROBE, HERE, canary, cleanup, sh


def setup(cid, cans):
    vol, net = f"swarm_{cid.lower()}_vol", "none"
    names = [f"swarm_{cid.lower()}_p{i}" for i in range(N)]
    cleanup(cid)
    mnt, init, mode, wname = DIRCFG[cid]
    sh(["docker", "volume", "create", vol], check=True)
    sh(["docker", "run", "--rm", "-v", f"{vol}:/v", IMG, "sh", "-c", init], check=True)
    for i, n in enumerate(names):
        if cid == "C7":
            mount = ["--mount", f"type=volume,src={vol},dst={mnt},volume-subpath=p{i}"]
        elif cid == "C8":
            mount = ["-v", f"{vol}:{mnt}:ro"]
        else:
            mount = ["-v", f"{vol}:{mnt}"]
        sh(["docker", "run", "-d", "--name", n, "--network", net, "--user", str(1001 + i),
            *mount, "-v", f"{PROBE}:/probe:ro", IMG, "sleep", "900"], check=True)
    return names, mnt, mode, wname


def snap(n, mnt, cans, wname):
    r = sh(["docker", "exec", n, "python", "/probe/probe_agent.py", "meta", mnt, json.dumps(cans), wname])
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"err": r.stderr[-200:]}


def diff(a, b, c):
    ch = []
    if a.get("dir") != b.get("dir"):
        ch.append("dir_metadata")
    if a.get("vfs") != b.get("vfs"):
        ch.append("statvfs")
    if c and a.get("guess", {}).get(c) != b.get("guess", {}).get(c):
        ch.append("guessed_stat:" + str(b.get("guess", {}).get(c, {}).get("stat")))
    return ch


def run(cid, rng):
    cans = [canary(rng) for _ in range(N)]
    names, mnt, mode, wname = setup(cid, cans)
    # null round: no write between snapshots
    noise = []
    for j, n in enumerate(names):
        a = snap(n, mnt, cans, wname); b = snap(n, mnt, cans, wname)
        if diff(a, b, None):
            noise.append({"receiver": f"p{j}", "fields": diff(a, b, None)})
    chans = []
    for i, s in enumerate(names):
        before = {j: snap(n, mnt, cans, wname) for j, n in enumerate(names) if j != i}
        w = sh(["docker", "exec", s, "python", "/probe/probe_agent.py", "write", mnt, cans[i], mode, wname])
        for j, n in enumerate(names):
            if j == i:
                continue
            ch = diff(before[j], snap(n, mnt, cans, wname), cans[i])
            for a in ch:
                chans.append({"sender": f"p{i}", "receiver": f"p{j}", "attr": a, "write": w.stdout.strip()[:80]})
    cleanup(cid)
    attrs = sorted({c["attr"] for c in chans})
    return {"config": cid, "expected_storage_verdict": EXPECTED[cid], "meta_verdict": "OPEN" if chans else "CLOSED",
            "attrs": attrs, "pairs": len({(c["sender"], c["receiver"]) for c in chans}), "of_pairs": N * (N - 1),
            "null_round_noise": noise, "channels": chans}


def main():
    rng = random.Random(20261117)
    sh(["docker", "pull", IMG], check=True)
    res = [run(c, rng) for c in DIRCFG]
    for r in res:
        flag = "" if r["meta_verdict"] == r["expected_storage_verdict"] else "   <-- differs from storage verdict"
        print(f"{r['config']:4} storage-expected {r['expected_storage_verdict']:6} meta {r['meta_verdict']:6} "
              f"pairs {r['pairs']}/{r['of_pairs']} attrs={r['attrs']} noise={len(r['null_round_noise'])}{flag}")
    (HERE / "results_e1_meta.json").write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
