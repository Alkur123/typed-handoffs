"""Report figures, computed from the saved episode files (no number typed by hand). Written 7 Nov 2026.
  python report/figs.py      -> report/fig*.png
Palette: validated light categorical slots 1-2 (#2a78d6 blue, #eb6834 orange) + neutral greys.
"""
import glob
import json
import math
import pathlib
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
R = ROOT / "results" / "gpt-6.1-sol"
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": "white", "axes.facecolor": "white", "savefig.dpi": 220})


def wilson(k, n, z=1.96):
    if n == 0:
        return 0, 0
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - h), min(1, c + h)


def load(pattern):
    return [json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(str(R / pattern)))]


# ---------------- Figure 1: the four store modes (schematic) ----------------
def fig1():
    # (title, rule, what happens to the legitimate reading '44', what happens to a laundered 'U344RXNS 44')
    LAU = "K7QX2MPA 44"   # illustrative code, not one from the runs
    modes = [("Detect only", "every read allowed\nand logged", ("44", True), (LAU, True)),
             ("Block all (naive)", "every cross-agent read of\nan agent-written file refused", ("44", False), (LAU, False)),
             ("Object-scoped", "declared handoff file\nreadable, any content", ("44", True), (LAU, True)),
             ("Content-typed (ours)", "declared file readable;\nwrite must match ^\\d{2}$", ("44", True), (LAU, False))]
    fig, axes = plt.subplots(1, 4, figsize=(7.4, 2.55))
    for ax, (name, rule, legit, laund) in zip(axes, modes):
        ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
        hi = name.startswith("Content")
        ax.text(5, 9.9, name, ha="center", va="top", fontsize=8.6, weight="bold", color=BLUE if hi else INK)
        for x, lab in ((0.1, "holder"), (7.0, "stuck")):
            ax.add_patch(FancyBboxPatch((x, 6.0), 2.9, 1.7, boxstyle="round,pad=0.05,rounding_size=0.35",
                                        fc="white", ec=INK2, lw=0.9))
            ax.text(x + 1.45, 6.85, lab, ha="center", va="center", fontsize=7.4, color=INK)
        ax.add_patch(FancyBboxPatch((3.6, 6.0), 2.8, 1.7, boxstyle="round,pad=0.05,rounding_size=0.35",
                                    fc="#eef4fc" if hi else "#f3f2ee", ec=BLUE if hi else MUTED, lw=1.6 if hi else 0.9))
        ax.text(5.0, 6.85, "store", ha="center", va="center", fontsize=7.4, color=INK)
        ax.add_patch(FancyArrowPatch((3.05, 6.85), (3.55, 6.85), arrowstyle="-|>", mutation_scale=9, color=INK2, lw=1))
        ax.add_patch(FancyArrowPatch((6.45, 6.85), (6.95, 6.85), arrowstyle="-|>", mutation_scale=9, color=INK2, lw=1))
        ax.text(5, 5.15, rule, ha="center", va="top", fontsize=6.6, color=INK2, linespacing=1.25)
        for y, (txt, ok) in ((2.55, legit), (1.0, laund)):
            ax.text(0.4, y, f"'{txt}'", ha="left", va="center", fontsize=6.9, family="DejaVu Sans Mono", color=INK)
            ax.text(9.6, y, "delivered" if ok else "refused", ha="right", va="center", fontsize=6.9,
                    weight="bold", color=(ORANGE if (ok and " " in txt) else (BLUE if ok else INK2)))
    fig.text(0.01, 0.03, "Example writes by a holder:  '44' = the legitimate reading;  'K7QX2MPA 44' = reading plus the restricted code (laundering).",
             fontsize=6.4, color=INK2)
    fig.tight_layout(pad=0.3, rect=(0, 0.06, 1, 1))
    fig.savefig(HERE / "fig1_modes.png", bbox_inches="tight"); plt.close(fig)


# ---------------- Figure 2: the headline (E8 + E8b) ----------------
def fig2():
    cells = [("det", "Detect\nonly"), ("naive", "Block\nall"), ("declared", "Object-\nscoped"), ("typed", "Content-\ntyped")]
    data = {}
    for cond in ("normal", "helpful"):
        for m, _ in cells:
            es = [e for e in load("POS0.50_*HO*.json") if e["handoff_mode"] == m and e["condition"] == cond]
            if not es:
                continue
            L = sum(e["legit_success"] for e in es); LN = sum(e["n"] for e in es)
            S = sum(len(e["stuck_code_solved"]) for e in es); SN = sum(len(e["stuck"]) for e in es)
            data[(m, cond)] = (L, LN, S, SN, len(es))
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.7), sharey=True)
    w = 0.36
    for ax, idx, title in ((axes[0], 0, "Legitimate handoffs completed (of 100 agents)"), (axes[1], 2, "Stuck agents that got the code (of 50)")):
        for j, (cond, col, lab) in enumerate((("normal", BLUE, "default holders"), ("helpful", ORANGE, "holders told “help your collaborator”"))):
            for i, (m, _) in enumerate(cells):
                if (m, cond) not in data:
                    continue
                k, n = data[(m, cond)][idx], data[(m, cond)][idx + 1]
                x = i + (j - 0.5) * w if (m, "helpful") in data else i
                lo, hi = wilson(k, n)
                ax.bar(x, 100 * k / n, w * 0.92, color=col, label=lab if i == 2 else None, zorder=2)
                ax.errorbar(x, 100 * k / n, yerr=[[max(0, 100 * (k / n - lo))], [max(0, 100 * (hi - k / n))]], color=INK2, lw=0.8,
                            capsize=2, zorder=3)
                ax.text(x, 100 * hi + 2.5, f"{k}", ha="center", fontsize=7, color=INK, zorder=4)
        ax.set_xticks(range(len(cells))); ax.set_xticklabels([c[1] for c in cells], fontsize=7.5)
        ax.set_title(title, fontsize=9, color=INK, loc="left")
        ax.set_ylim(0, 116); ax.set_yticks([0, 20, 40, 60, 80, 100]); ax.yaxis.grid(True, color=GRID, lw=0.6, zorder=0); ax.set_axisbelow(True)
    axes[0].set_ylabel("% (Wilson 95% CI)")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=7, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(pad=0.4, rect=(0, 0.07, 1, 1))
    fig.savefig(HERE / "fig2_headline.png", bbox_inches="tight"); plt.close(fig)
    return data


# ---------------- Figure 3: latency ----------------
def fig3():
    txt = (ROOT / "results" / "latency.txt").read_text(encoding="utf-8")
    blocks = txt.split("== ")[1:]
    series = []
    for b, (lab, col) in zip(blocks, (("hinted grid", BLUE), ("E7 detect cells", ORANGE))):
        reg = b.split("[EXPLORATORY")[0]
        lab = f"{lab} ({re.search(r'solved stuck agents: (\d+)', reg).group(1)} agents)"
        pts = [(int(L), int(p)) for L, p in re.findall(r"L=\s*(\d+) steps would prevent \d+/\d+ = (\d+)%", reg)]
        series.append((lab, col, pts))
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    for lab, col, pts in series:
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=col, lw=2, marker="o", ms=4, label=lab, zorder=3)
    ax.set_xlabel("steps between the receiver's first cross-agent\nread and the gate starting to refuse")
    ax.set_ylabel("% of transfers still prevented")
    ax.set_xticks([0, 1, 2, 5, 10]); ax.set_ylim(0, 105)
    ax.yaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout(pad=0.4)
    fig.savefig(HERE / "fig3_latency.png", bbox_inches="tight"); plt.close(fig)
    return series


# ---------------- Figure 4: detection is easy, prevention displaces (E7) ----------------
def fig4():
    e7 = [e for e in load("POS0.50_*_s2[1-5].json")]
    def cell(e):
        if e.get("enforce") and e.get("lobby"): return "Block +\nopen lobby"
        if e["condition"] == "informed": return "Block,\nagents told"
        if e.get("enforce"): return "Block"
        if e["condition"] == "watched": return "No block,\n“you are watched”"
        return "No block"
    order = ["No block", "No block,\n“you are watched”", "Block", "Block,\nagents told", "Block +\nopen lobby"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6), gridspec_kw={"width_ratios": [1.35, 1]})
    ax = axes[0]
    for i, c in enumerate(order):
        es = [e for e in e7 if cell(e) == c]
        k = sum(e["stuck_solved"] for e in es); n = sum(len(e["stuck"]) for e in es)
        ax.bar(i, 100 * k / n, 0.62, color=ORANGE if "lobby" in c else (MUTED if c.startswith("No") else BLUE), zorder=2)
        ax.text(i, 100 * k / n + 3, f"{k}/{n}", ha="center", fontsize=7, color=INK)
    ax.set_xticks(range(len(order))); ax.set_xticklabels(order, fontsize=6.8)
    ax.set_ylim(0, 112); ax.set_ylabel("stuck agents solved\nvia another agent (%)")
    ax.set_title("A. Blocking stops the store channel; the swarm moves", fontsize=8.5, loc="left", color=INK)
    ax.yaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
    # B: detectors on flow episodes, pooled over hinted + E7 detect cells
    det = [e for e in load("POS*_s1[1-5].json") + e7 if e["coordinating"] and not e.get("enforce") and not e.get("lobby")]
    lob = [e for e in load("POS*lobby*.json") if e["coordinating"]]
    mons = [("provenance", "store provenance"), ("join", "string join (free)"), ("t_full_0", "LLM transcript reader")]
    ax = axes[1]
    for j, (pool, lab, col) in enumerate(((det, "store channel", BLUE), (lob, "lobby channel", ORANGE))):
        for i, (m, ml) in enumerate(mons):
            got = [(e["provenance"]["alarm"] if m == "provenance" else e.get("monitors", {}).get(m, {}).get("alarm"))
                   for e in pool]
            got = [g for g in got if g is not None]
            v = 100 * sum(got) / len(got) if got else 0
            ax.barh(i + (j - 0.5) * 0.36, v, 0.33, color=col, label=lab if i == 0 else None, zorder=2)
            ax.text(v + 2, i + (j - 0.5) * 0.36, f"{sum(got)}/{len(got)}", va="center", fontsize=6.5, color=INK)
    ax.set_yticks(range(len(mons))); ax.set_yticklabels([m[1] for m in mons], fontsize=7.2); ax.invert_yaxis()
    ax.set_xlim(0, 125); ax.set_xlabel("coordinating episodes flagged (%)")
    ax.set_title("B. Detection is easy", fontsize=8.5, loc="left", color=INK)
    ax.legend(frameon=False, fontsize=6.8, loc="upper center", bbox_to_anchor=(0.45, -0.22), ncol=2)
    fig.tight_layout(pad=0.5)
    fig.savefig(HERE / "fig4_detect_vs_prevent.png", bbox_inches="tight"); plt.close(fig)


# ---------------- Figure 5 (appendix): isolation matrix ----------------
def fig5():
    e1 = json.load(open(ROOT / "e1_real" / "results_e1_real.json"))
    vfs = {r["config"]: r for r in json.load(open(ROOT / "e1_real" / "results_e1_vfs.json"))}
    meta = {r["config"]: r for r in json.load(open(ROOT / "e1_real" / "results_e1_meta.json"))}
    cfgs = [r["config"] for r in e1]
    cols = ["file content /\nnames (H1)", "network\n(default bridge)", "shared inode\ncount", "dir metadata /\nguessed stat"]
    M = []
    for r in e1:
        c = r["config"]
        v = [1 if r["observed"] == "OPEN" else 0, 1 if r["network_channels"] else 0 if c in ("C1", "C2", "C3", "C4", "C5", "C7", "C8", "C9") else None]
        v.append((1 if vfs[c]["pairs_open"] else 0) if c in vfs else None)   # only the clean 200-inode test is used
        if c in meta:
            v.append(1 if any(a.startswith(("dir_", "guessed")) for a in meta[c]["attrs"]) else 0)
        else:
            v.append(None)
        M.append(v)
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    for i, row in enumerate(M):
        for j, v in enumerate(row):
            fc = "#f3f2ee" if v is None else (ORANGE if v else "#dbe8f8")
            ax.add_patch(plt.Rectangle((j, i), 0.94, 0.9, fc=fc, ec="white"))
            ax.text(j + 0.47, i + 0.45, "not tested" if v is None else ("OPEN" if v else "closed"), ha="center", va="center",
                    fontsize=6.5, color="white" if v else INK2)
    ax.set_xlim(0, len(cols)); ax.set_ylim(len(cfgs), 0)
    ax.set_xticks([j + 0.47 for j in range(len(cols))]); ax.set_xticklabels(cols, fontsize=6.5)
    ax.set_yticks([i + 0.45 for i in range(len(cfgs))]); ax.set_yticklabels(cfgs, fontsize=7)
    ax.tick_params(length=0); [s.set_visible(False) for s in ax.spines.values()]
    ax.xaxis.tick_top()
    fig.tight_layout(pad=0.3)
    fig.savefig(HERE / "fig5_isolation.png", bbox_inches="tight"); plt.close(fig)
    return cfgs, M


if __name__ == "__main__":
    fig1()
    d = fig2(); print("fig2 data:", d)
    s = fig3(); print("fig3 data:", s)
    fig4()
    print("fig5:", fig5())
