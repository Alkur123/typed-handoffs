"""A4.17 statvfs signal-vs-noise test (7 Nov 2026, evening). For C7, C8 (negative control: read-only) and C9:
5 null rounds give the receiver's max |delta ffree| with no sender action; then each sender creates 200 files
and every receiver's delta ffree is compared with that noise ceiling. Channel = delta <= -150 and |delta| > 3 x noise."""
import json
import random

from run_e1_meta import setup
from run_e1_real import HERE, IMG, N, canary, cleanup, sh

K = 200


def vfs(n, mnt):
    return json.loads(sh(["docker", "exec", n, "python", "/probe/probe_agent.py", "vfs", mnt]).stdout)["ffree"]


def run(cid, rng):
    cans = [canary(rng) for _ in range(N)]
    names, mnt, _, _ = setup(cid, cans)
    noise = 0
    for _ in range(5):
        for n in names:
            a = vfs(n, mnt); b = vfs(n, mnt); noise = max(noise, abs(b - a))
    rows = []
    for i, s in enumerate(names):
        before = {j: vfs(n, mnt) for j, n in enumerate(names) if j != i}
        made = json.loads(sh(["docker", "exec", s, "python", "/probe/probe_agent.py", "bulk", mnt, str(K), f"p{i}"]).stdout)["created"]
        for j, n in enumerate(names):
            if j != i:
                dlt = vfs(n, mnt) - before[j]
                rows.append({"sender": f"p{i}", "receiver": f"p{j}", "created": made, "delta_ffree": dlt,
                             "channel": dlt <= -0.75 * K and abs(dlt) > 3 * max(noise, 1)})
    cleanup(cid)
    return {"config": cid, "noise_max_abs_delta": noise, "pairs_open": sum(r["channel"] for r in rows),
            "of_pairs": len(rows), "rows": rows}


if __name__ == "__main__":
    rng = random.Random(20261118)
    res = [run(c, rng) for c in ("C7", "C8", "C9")]
    for r in res:
        ds = sorted(x["delta_ffree"] for x in r["rows"])
        print(f"{r['config']}: noise max |d|={r['noise_max_abs_delta']}  created/sender={r['rows'][0]['created']}  "
              f"delta range [{ds[0]}, {ds[-1]}]  statvfs channel pairs {r['pairs_open']}/{r['of_pairs']}")
    (HERE / "results_e1_vfs.json").write_text(json.dumps(res, indent=2))
