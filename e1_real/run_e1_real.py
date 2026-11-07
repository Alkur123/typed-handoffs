"""E1 against real, kernel-enforced isolation (AMENDMENTS.md A1). Written 7 Nov 2026.

Each principal = its own Docker container running as its own Linux UID. Shared stores are
real volumes with real permissions and mount flags. The sweep fills Kemmerer's Shared
Resource Matrix by execution. Storage attributes decide H1; the network probe is exploratory.

Usage: python run_e1_real.py            (default bridge network per configuration)
       python run_e1_real.py --control  (--network none; network probe should find nothing)
"""
import json
import pathlib
import random
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROBE = str(HERE).replace("\\", "/")
IMG = "python:3.12-alpine"
N = 4
EXPECTED = {"C1": "OPEN", "C2": "OPEN", "C3": "OPEN", "C4": "OPEN", "C5": "OPEN", "C6": "OPEN",
            "C7": "CLOSED", "C8": "CLOSED", "C9": "CLOSED", "C10": "CLOSED"}
STORAGE = {"content", "filename", "size", "mtime", "existence"}

# config -> (mount point, init shell, write mode, write name)
DIRCFG = {
    "C1": ("/cache", "chmod 1777 /v", "0644", "obj_{c}"),
    "C2": ("/tmp", "chmod 1777 /v", "0644", "obj_{c}"),
    "C3": ("/logs", "chmod 1777 /v", "0644", "log_{c}"),
    "C4": ("/pkg", "chmod 1777 /v", "0644", "obj_{c}"),
    "C5": ("/cache", "chmod 1777 /v", "0600", "obj_{c}"),
    "C7": ("/cache", "for i in 0 1 2 3; do mkdir -p /v/p$i; chown $((1001+i)) /v/p$i; chmod 700 /v/p$i; done", "0644", "obj_{c}"),
    "C8": ("/ref", "echo reference > /v/ref.txt; chmod 755 /v", "0644", "obj_{c}"),
    "C9": ("/cache", "chmod 1733 /v", "0600", "obj_{c}"),
}
PASTE = {"C6": "1", "C10": "0"}


def sh(args, check=False):
    r = subprocess.run(args, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"{' '.join(args)}\n{r.stderr}")
    return r


def canary(rng):
    return "CNRY" + "".join(rng.choice("ABCDEFGHJKMNPQRSTUVWXYZ23456789") for _ in range(8))


def run_config(cid, control, rng):
    net = "none" if control else f"swarm_{cid.lower()}"
    vol = f"swarm_{cid.lower()}_vol"
    names = [f"swarm_{cid.lower()}_p{i}" for i in range(N)]
    cans = {f"p{i}": canary(rng) for i in range(N)}
    who = {c: p for p, c in cans.items()}
    cleanup(cid)
    if not control:
        sh(["docker", "network", "create", net], check=True)
    extra = []
    if cid in DIRCFG:
        mnt, init, mode, wname = DIRCFG[cid]
        sh(["docker", "volume", "create", vol], check=True)
        sh(["docker", "run", "--rm", "-v", f"{vol}:/v", IMG, "sh", "-c", init], check=True)
    else:
        mnt, mode, wname = None, None, None
        sh(["docker", "run", "-d", "--name", f"swarm_{cid.lower()}_paste", "--network", net,
            "-e", f"LISTABLE={PASTE[cid]}", "-v", f"{PROBE}:/probe:ro", IMG,
            "python", "/probe/paste_server.py"], check=True)
    for i, n in enumerate(names):
        mount = []
        if cid in DIRCFG:
            if cid == "C7":
                mount = ["--mount", f"type=volume,src={vol},dst={mnt},volume-subpath=p{i}"]
            elif cid == "C8":
                mount = ["-v", f"{vol}:{mnt}:ro"]
            else:
                mount = ["-v", f"{vol}:{mnt}"]
        sh(["docker", "run", "-d", "--name", n, "--network", net, "--user", str(1001 + i),
            *mount, "-v", f"{PROBE}:/probe:ro", IMG, "sleep", "900"], check=True)

    # write phase
    writes = {}
    for i, n in enumerate(names):
        c = cans[f"p{i}"]
        if cid in DIRCFG:
            r = sh(["docker", "exec", n, "python", "/probe/probe_agent.py", "write", mnt, c, mode, wname])
        else:
            r = sh(["docker", "exec", n, "python", "/probe/probe_agent.py", "paste_put",
                    f"http://swarm_{cid.lower()}_paste:8080", c])
        writes[f"p{i}"] = r.stdout.strip() or r.stderr.strip()[-200:]

    # observe phase: storage attributes
    storage = []
    for j, n in enumerate(names):
        if cid in DIRCFG:
            r = sh(["docker", "exec", n, "python", "/probe/probe_agent.py", "observe", mnt, json.dumps(list(cans.values()))])
        else:
            r = sh(["docker", "exec", n, "python", "/probe/probe_agent.py", "paste_observe",
                    f"http://swarm_{cid.lower()}_paste:8080", json.dumps(list(cans.values()))])
        try:
            seen = json.loads(r.stdout or "{}")
        except json.JSONDecodeError:
            seen = {}
        for c, attrs in seen.items():
            s = who[c]
            if s != f"p{j}":
                for a in attrs:
                    storage.append({"sender": s, "receiver": f"p{j}", "attr": a})

    # exploratory network probe
    network = []
    if cid in DIRCFG:  # paste configs need the network by design; probe only directory configs
        for i, n in enumerate(names):
            sh(["docker", "exec", "-d", n, "python", "/probe/probe_agent.py", "listen", "9000", cans[f"p{i}"]])
        sh(["docker", "exec", names[0], "sleep", "1"])
        for j, n in enumerate(names):
            for i, m in enumerate(names):
                if i == j:
                    continue
                r = sh(["docker", "exec", n, "python", "/probe/probe_agent.py", "connect", m, "9000"])
                try:
                    got = json.loads(r.stdout or "{}").get("got")
                except json.JSONDecodeError:
                    got = None
                if got and got in who:
                    network.append({"sender": who[got], "receiver": f"p{j}"})
    cleanup(cid)
    attrs = sorted({x["attr"] for x in storage})
    verdict = "OPEN" if storage else "CLOSED"
    return {"config": cid, "control_network_none": control, "expected": EXPECTED[cid], "observed": verdict,
            "correct": verdict == EXPECTED[cid], "storage_attrs": attrs, "storage_channels": len(storage),
            "network_channels": len(network), "writes": writes}


def cleanup(cid):
    l = cid.lower()
    for i in range(N):
        sh(["docker", "rm", "-f", f"swarm_{l}_p{i}"])
    sh(["docker", "rm", "-f", f"swarm_{l}_paste"])
    sh(["docker", "volume", "rm", "-f", f"swarm_{l}_vol"])
    sh(["docker", "network", "rm", f"swarm_{l}"])


def main():
    control = "--control" in sys.argv
    rng = random.Random(20261107)
    sh(["docker", "pull", IMG], check=True)
    cfgs = [c for c in EXPECTED if not (control and c in PASTE)]
    res = [run_config(c, control, rng) for c in cfgs]
    for r in res:
        print(f"{r['config']:4} expected {r['expected']:6} observed {r['observed']:6} {'OK ' if r['correct'] else 'MISS'} "
              f"storage={r['storage_attrs']} net_channels={r['network_channels']}")
    n = sum(r["correct"] for r in res)
    print(f"H1 (real isolation{', network none' if control else ''}): {n}/{len(res)} correct")
    out = HERE / ("results_e1_real_control.json" if control else "results_e1_real.json")
    out.write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
