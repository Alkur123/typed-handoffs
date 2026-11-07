"""Generate report appendices from the code and the saved episodes (nothing typed by hand). Written 7 Nov 2026.
  python report/gen_appendix.py  -> report/app_prompts.md, report/app_cells.md
"""
import glob
import json
import pathlib
import sys
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from swarm_env import Episode, SELF_REPORT_Q  # noqa: E402
from run_swarm import NUDGE  # noqa: E402


def prompts():
    ep = Episode(f=0.5, condition="normal", seed=31, posctrl=True, handoff="typed")
    s = sorted(ep.stuck)[0]
    fr = sorted(p for p in ep.P if p not in ep.stuck)[0]
    e3 = Episode(f=0.5, condition="normal", seed=11, posctrl=True)
    s3 = sorted(e3.stuck)[0]
    out = ["Verbatim prompts, generated from `swarm_env.py` (E8, seed 31; agent names are the environment's).", "",
           f"**System prompt, stuck agent ({s}), hinted condition:** {ep.system_prompt(s)}", "",
           f"**System prompt, non-stuck agent ({fr}):** {ep.system_prompt(fr)}", "",
           f"**Task prompt, stuck agent ({s}), E8:** {ep.task_prompt(s)}", "",
           f"**Task prompt, non-stuck agent ({fr}), E8:** {ep.task_prompt(fr)}", "",
           f"**Task prompt, E3/E7 (no handoff):** {e3.task_prompt(s3)}", "",
           "**Sentences added by condition** (appended to the system prompt):", ""]
    for cond in ("falsify", "evade", "watched", "informed", "helpful"):
        e = Episode(f=0.5, condition=cond, seed=31, posctrl=True)
        base = Episode(f=0.5, condition="normal", seed=31, posctrl=True)
        st = sorted(e.stuck)[0]
        extra = e.system_prompt(st).replace(base.system_prompt(st), "").strip()
        out.append(f"- *{cond}*: {extra}")
    lob = Episode(f=0.5, condition="normal", seed=31, posctrl=True, lobby=True)
    out.append(f"- *lobby available*: {lob.system_prompt(sorted(lob.stuck)[0]).replace(Episode(f=0.5, condition='normal', seed=31, posctrl=True).system_prompt(sorted(lob.stuck)[0]), '').strip()}")
    out += ["", f"**Nudge when an agent makes no tool call:** {NUDGE}", "",
            f"**Self-report question, asked once after an agent finishes (no tools):** {SELF_REPORT_Q}"]
    (HERE / "app_prompts.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def cells():
    rows = defaultdict(list)
    for f in glob.glob(str(ROOT / "results" / "*" / "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        model = pathlib.Path(f).parent.name
        if d.get("posctrl") and d["seed"] >= 100:
            block = "E3 positive control"
        elif d.get("handoff_mode"):
            block = "E8/E8b" if model == "gpt-6.1-sol" else "E9 gate"
        elif d.get("posctrl") and 21 <= d["seed"] <= 25:
            block = "E7"
        elif d.get("posctrl"):
            block = "E3 hinted"
        else:
            block = "E3 no hint"
        cell = d["condition"] + ("+lobby" if d.get("lobby") else "") + ("+enforce" if d.get("enforce") else "") + \
            (f"+{d['handoff_mode']}" if d.get("handoff_mode") else "")
        rows[(block, model, cell, d["f"])].append(d)
    order = ["E3 positive control", "E3 no hint", "E3 hinted", "E7", "E8/E8b", "E9 gate"]
    out = ["Every cell that was run, computed from the episode files. *Stuck solved* uses the holder's code (edit distance ≤ 1); "
           "for E8/E8b/E9 it is the code token of the `<code> <reading>` answer.", "",
           "| Block | Model | Condition | f | Eps. | Flow eps. | Stuck solved | Legit |",
           "|---|---|---|---|---|---|---|---|"]
    for (b, m, c, f), es in sorted(rows.items(), key=lambda kv: (order.index(kv[0][0]), kv[0][1], kv[0][2], kv[0][3])):
        ns = sum(len(e["stuck"]) for e in es)
        if es[0].get("handoff_mode"):
            ks = sum(len(e["stuck_code_solved"]) for e in es)
            leg = f"{sum(e['legit_success'] for e in es)}/{sum(e['n'] for e in es)}"
        else:
            ks = sum(e["stuck_solved"] for e in es); leg = ""
        out.append(f"| {b} | {m} | {c.replace('+', ' + ')} | {f:.2f} | {len(es)} | {sum(e['coordinating'] for e in es)}/{len(es)} | "
                   f"{f'{ks}/{ns}' if ns else 'n/a'} | {leg} |")
    (HERE / "app_cells.md").write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    prompts(); cells()
    print((HERE / "app_prompts.md").read_text(encoding="utf-8")[:1500])
    print((HERE / "app_cells.md").read_text(encoding="utf-8"))
