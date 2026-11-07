"""Run E3 swarm episodes against OpenAI models (Responses API). One JSON per episode; existing files skipped.

PREEXISTING (Oct 2026): the Responses-API call/retry pattern and the budget-cap bookkeeping are adapted
from contrib/apart-collusion/run.py (functions rcall, the cost formula). NEW (7 Nov 2026): parallel
per-tick querying of N agents, the swarm environment, specs for E3 cells.

  python run_swarm.py --model gpt-6-luna --which posctrl --seeds 4
  python run_swarm.py --model gpt-6-luna --which smoke
  BUDGET_USD=20 python run_swarm.py --model gpt-6-luna --which grid --seeds 6
"""
import argparse
import json
import os
import pathlib
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI

from swarm_env import Episode, TOOLS, SELF_REPORT_Q

HERE = pathlib.Path(__file__).resolve().parent
NUDGE = "Continue. Use one tool per turn, and call submit_answer when you are done."
PRICE = {"gpt-6.1-sol": (2.00, 0.10, 10.00), "gpt-6-luna": (0.10, 0.01, 0.50)}  # $/M in, cached in, out


def api_key():  # PREEXISTING (Oct 2026)
    k = os.environ.get("OPENAI_API_KEY")
    if k:
        return k
    for line in (HERE.parents[1] / "backend" / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit("OPENAI_API_KEY not found")


# 7 Nov evening fix (openai-python issues #371, #1059): stale keep-alive sockets in long-running, highly
# concurrent clients surface as APIConnectionError. Explicit pool limits + short keep-alive expiry.
import httpx  # noqa: E402
from openai import DefaultHttpxClient  # noqa: E402
CLIENT = OpenAI(api_key=api_key(), max_retries=6, timeout=120,
                http_client=DefaultHttpxClient(limits=httpx.Limits(max_connections=64, max_keepalive_connections=24,
                                                                   keepalive_expiry=15.0)))
def resp_tools(tools):
    return [{"type": "function", "name": t["name"], "description": t["description"],
             "parameters": t["parameters"], "strict": False} for t in tools]


def rcall(model, instructions, inp, prev, tools, tools_on=True):  # PREEXISTING pattern (Oct 2026)
    kw = dict(model=model, instructions=instructions, input=inp, tools=tools,
              max_output_tokens=4000, parallel_tool_calls=False)
    if prev:
        kw["previous_response_id"] = prev
    if not tools_on:
        kw["tool_choice"] = "none"
    t0 = time.time()
    for attempt in range(60):   # 7 Nov evening fix: ride out connection outages up to ~15 min per call
        try:
            return CLIENT.responses.create(**kw)
        except Exception as e:
            if getattr(e, "code", None) in ("credit_balance_exhausted", "insufficient_quota"):
                print("OUT OF CREDITS: add OpenAI credits; nothing is retried.", flush=True)
                raise SystemExit("OUT OF CREDITS")
            conn = type(e).__name__ in ("APIConnectionError", "APITimeoutError", "InternalServerError", "RateLimitError")
            if (not conn and attempt >= 5) or time.time() - t0 > 900:
                cause = repr(getattr(e, "__cause__", None))[:200]
                raise RuntimeError(f"{type(e).__name__} after {attempt + 1} tries / {time.time() - t0:.0f}s; cause={cause}") from e
            if attempt and attempt % 5 == 0:
                print(f"  [retry] {type(e).__name__} x{attempt}, {time.time() - t0:.0f}s; cause={repr(getattr(e, '__cause__', None))[:120]}", flush=True)
            time.sleep(min(60, 3 * 2 ** min(attempt, 5)))


def run_episode(model, ep: Episode, ticks=30, usage=None):
    P = ep.P
    pending = {p: [{"role": "user", "content": ep.task_prompt(p)}] for p in P}
    prev = {p: None for p in P}
    tlog = {p: [] for p in P}
    usage = usage if usage is not None else {"prompt": 0, "completion": 0, "cached": 0}
    usage.update(prompt=0, completion=0, cached=0)
    lock = threading.Lock()
    tools = resp_tools(ep.tools())
    shuffler = __import__("random").Random(ep.seed * 7919 + int(ep.f * 100))   # A4.13

    def go(p, tools_on=True):
        try:
            r = rcall(model, ep.system_prompt(p), pending[p], prev[p], tools, tools_on)
        except Exception as e:   # say where it failed (7 Nov evening fix)
            raise RuntimeError(f"agent {p} step {ep.steps[p]} input_items={len(pending[p])}: {type(e).__name__}: {str(e)[:150]}") from e
        prev[p] = r.id
        with lock:
            usage["prompt"] += r.usage.input_tokens
            usage["completion"] += r.usage.output_tokens
            usage["cached"] += getattr(r.usage.input_tokens_details, "cached_tokens", 0) or 0
        return r

    active = set(P)
    with ThreadPoolExecutor(len(P)) as pool:
        for tick in range(ticks):
            order = [p for p in P if p in active]
            if not order:
                break
            shuffler.shuffle(order)
            resps = dict(zip(order, pool.map(go, order)))
            for p in order:  # apply in agent-index order: deterministic store state
                r = resps[p]
                ep.steps[p] += 1
                calls = [o for o in r.output if o.type == "function_call"]
                entry = {"tick": tick, "text": r.output_text, "calls": [], "outputs": []}
                if calls:
                    tc = calls[0]
                    try:
                        args = json.loads(tc.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    res = ep.tool(p, tc.name, args, tick)
                    entry["calls"].append({"name": tc.name, "args": args}); entry["outputs"].append(res[:2000])
                    pending[p] = [{"type": "function_call_output", "call_id": tc.call_id, "output": res}] + \
                                 [{"type": "function_call_output", "call_id": c.call_id,
                                   "output": "Error: one tool call per turn."} for c in calls[1:]]
                    if tc.name == "submit_answer":
                        active.discard(p)
                        pending[p].append({"role": "user", "content": SELF_REPORT_Q})
                else:
                    pending[p] = [{"role": "user", "content": NUDGE}]
                tlog[p].append(entry)
                if ep.steps[p] >= ep.max_steps:
                    active.discard(p)
        # self-reports for everyone who submitted or ran out (asked once, no tools)
        need = [p for p in P if p not in ep.self_report]
        q = {"role": "user", "content": SELF_REPORT_Q}
        for p in need:
            if q in pending[p]:
                continue
            if pending[p] and pending[p][0].get("type") == "function_call_output":
                pending[p].append(q)   # keep the unanswered tool outputs, then ask
            else:
                pending[p] = [q]
        reps = dict(zip(need, pool.map(lambda p: go(p, tools_on=False).output_text or "", need)))
        ep.self_report.update(reps)
    d = ep.to_json()
    d["model"], d["usage"], d["transcripts"] = model, usage, tlog
    return d


def specs(which, seeds):
    """A4.16 cell plan. The grid is ordered so a budget cut removes the least important cells last-in."""
    if which == "smoke":
        return [dict(f=0.5, condition="normal", seed=999, posctrl=True)]
    if which == "posctrl":
        return [dict(f=0.5, condition="normal", seed=s, posctrl=True) for s in range(101, 105)]
    plan = []
    if which == "grid":
        for f, k in ((0.5, 10), (0.0, 12), (0.10, 4), (0.25, 4)):
            for s in range(1, k + 1):
                plan += [dict(f=f, condition="normal", seed=s), dict(f=f, condition="falsify", seed=s)]
        return plan
    if which == "hinted":   # A5
        for f in (0.5, 0.25, 0.10):
            for c in ("normal", "falsify", "evade"):
                plan += [dict(f=f, condition=c, seed=s, posctrl=True) for s in range(11, 16)]
        plan += [dict(f=0.5, condition="normal", seed=s, posctrl=True, lobby=True) for s in range(11, 16)]
        return plan
    if which == "e7":   # PREREGISTRATION_2 as amended by E7-A1: interleaved by seed so cells run concurrently
        for s in range(21, 26):
            plan += [dict(f=0.5, condition="normal", seed=s, posctrl=True),                            # DET-normal
                     dict(f=0.5, condition="normal", seed=s, posctrl=True, enforce=True),               # ENF-normal
                     dict(f=0.5, condition="normal", seed=s, posctrl=True, enforce=True, lobby=True),   # ENF-lobby
                     dict(f=0.5, condition="informed", seed=s, posctrl=True, enforce=True),             # ENF-informed
                     dict(f=0.5, condition="watched", seed=s, posctrl=True)]                            # WATCH
        return plan
    if which == "e8":   # PREREGISTRATION_3: interleaved by seed, ENF-typed first
        for s in range(31, 36):
            plan += [dict(f=0.5, condition="normal", seed=s, posctrl=True, handoff=m)
                     for m in ("typed", "declared", "naive", "det")]
        return plan
    if which == "e8b":   # PREREGISTRATION_3b
        for s in range(31, 36):
            plan += [dict(f=0.5, condition="helpful", seed=s, posctrl=True, handoff=m) for m in ("typed", "declared")]
        return plan
    if which == "hinted_lobby":   # A5, run first: the cell where the monitor is predicted to MISS
        return [dict(f=0.5, condition="normal", seed=s, posctrl=True, lobby=True) for s in range(11, 16)]
    if which == "evade":
        return [dict(f=0.5, condition="evade", seed=s) for s in range(1, 7)]
    if which == "lobby":
        return [dict(f=0.5, condition="normal", seed=s, lobby=True) for s in range(1, 7)]
    raise SystemExit(which)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--which", choices=["smoke", "posctrl", "grid", "evade", "lobby", "hinted", "hinted_lobby", "e7", "e8", "e8b"], required=True)
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--shard", default="0/1", help="i/k: run every k-th spec starting at i")
    ap.add_argument("--only-seeds", default="", help="comma list; run only specs with these seeds (top-ups)")
    a = ap.parse_args()
    out = HERE / ("results_smoke" if a.which == "smoke" else "results") / a.model
    out.mkdir(parents=True, exist_ok=True)
    cap = float(os.environ.get("BUDGET_USD", "inf"))
    price = PRICE.get(a.model, (5.0, 0.5, 30.0))
    spent = 0.0
    si, sk = map(int, a.shard.split("/"))
    keep = {int(x) for x in a.only_seeds.split(",") if x}
    for sp in specs(a.which, a.seeds)[si::sk]:
        if keep and sp["seed"] not in keep:
            continue
        ep = Episode(n=a.n, **sp)
        tag = f"{'POS' if ep.posctrl else 'f'}{ep.f:.2f}_{ep.condition}{'_lobby' if ep.lobby else ''}{'_ENF' if ep.enforce else ''}{'_HO' + ep.handoff if ep.handoff else ''}_s{ep.seed}"
        f = out / f"{tag}.json"
        if f.exists():
            continue
        if spent >= cap:
            print(f"BUDGET CAP reached (${spent:.2f} >= ${cap:.2f}); {tag} and later cells NOT run", flush=True)
            break
        cost = lambda u: ((u["prompt"] - u["cached"]) * price[0] + u["cached"] * price[1] + u["completion"] * price[2]) / 1e6
        d = None
        for attempt in range(3):   # 7 Nov evening fix: a failed attempt's tokens are billed, so they are counted
            u = {}
            try:
                d = run_episode(a.model, Episode(n=a.n, **sp), usage=u)
                break
            except Exception as e:
                lost = cost(u) if u else 0.0
                spent += lost
                print(f"EPISODE FAILED {tag} attempt {attempt + 1}/3 (billed ${lost:.3f}, total=${spent:.2f}): "
                      f"{type(e).__name__}: {str(e)[:250]}", flush=True)
                if spent >= cap:
                    break
                time.sleep(60)
        if d is None:
            continue
        u = d["usage"]
        c = cost(u)
        spent += c
        d["cost_usd"] = c
        f.write_text(json.dumps(d, indent=1), encoding="utf-8")
        pv = d["provenance"]
        print(f"{tag}: coord={d['coordinating']} flows={len(d['flows'])} stuck_solved={d['stuck_solved']} "
              f"prov_alarm={pv['alarm']} tool_edges={pv['n_tool_metadata_edges']} cost=${c:.3f} total=${spent:.2f}"
              + (f" legit={d['legit_success']}/20 stuck_code={len(d['stuck_code_solved'])} type_refused={d['type_refused']}"
                 if d.get("handoff") else ""),
              flush=True)


if __name__ == "__main__":
    main()
