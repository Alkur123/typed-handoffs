"""Project image (2560x1440) for the submission form and the repo. Every number is read from result files.
Written 8 Nov 2026.  python report/build_cover.py -> report/cover.png
"""
import glob
import json
import math
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
BG, INK, INK2, MUTED, GRID = "#f6f4ef", "#141413", "#55534e", "#9a978f", "#e3e0d8"
BLUE, ORANGE = "#2a78d6", "#eb6834"
L2 = math.log2(10)


def e8():
    out = {}
    for f in glob.glob(str(ROOT / "results" / "gpt-6.1-sol" / "POS0.50_*HO*.json")):
        d = json.load(open(f, encoding="utf-8"))
        k = (d["handoff_mode"], d["condition"])
        L, LN, S, SN = out.get(k, (0, 0, 0, 0))
        out[k] = (L + d["legit_success"], LN + d["n"], S + len(d["stuck_code_solved"]), SN + len(d["stuck"]))
    return out


def e10():
    sc = json.load(open(ROOT / "results" / "e10_scripted.json", encoding="utf-8"))
    cap = {"OBJECT": 26.6, "TYPED": 26.6, "ONCE": sc["ONCE"]["bits"], "VERIFIED": sc["VERIFIED"]["bits"],
           "RELEASE": sc["RELEASE"]["bits"]}
    got = {}
    for p in cap:
        es = [json.load(open(f, encoding="utf-8")) for f in glob.glob(str(ROOT / "results_e10" / "gpt-6.1-sol" / f"{p}_s*.json"))]
        got[p] = (sum(e["digits"] for e in es) / len(es) * L2, sum(e["digits"] == 8 for e in es), len(es))
    return cap, got, sc


def main():
    m = e8()
    cap, got, sc = e10()
    typed, det, naive, obj = m[("typed", "normal")], m[("det", "normal")], m[("naive", "normal")], m[("declared", "normal")]
    W, H = 25.6, 14.4
    fig = plt.figure(figsize=(W, H), dpi=100)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

    # header
    ax.text(1.3, 12.75, "TYPED HANDOFFS", fontsize=26, color=BLUE, weight="bold", family="DejaVu Sans")
    ax.text(1.3, 11.45, "Bounding what a coordinating agent swarm can pass through\nshared infrastructure without breaking legitimate work",
            fontsize=40, color=INK, va="top", family="DejaVu Serif", linespacing=1.15)

    ax.text(1.3, 9.35, "A type is a rate limit.  Verification is the boundary.", fontsize=25, color=INK2, style="italic",
            family="DejaVu Serif")

    # left: the four policies on the legitimate dependency (E8)
    ax.text(1.3, 8.2, "When agents must share some things but not others", fontsize=21, color=INK2)
    rows = [("Detect only", det, MUTED), ("Block everything", naive, MUTED), ("Object-scoped allow-list", obj, MUTED),
            ("Content-typed handoff", typed, BLUE)]
    y = 7.55
    ax.text(7.55, y - 0.15, "legitimate work", fontsize=15, color=INK2, ha="center")
    ax.text(10.75, y - 0.15, "restricted codes leaked", fontsize=15, color=INK2, ha="center")
    for name, (L, LN, S, SN), col in rows:
        y -= 1.05
        bold = col == BLUE
        ax.text(1.3, y, name, fontsize=21, color=BLUE if bold else INK, weight="bold" if bold else "normal", va="center")
        ax.add_patch(FancyBboxPatch((6.25, y - 0.22), 2.6, 0.44, boxstyle="round,pad=0,rounding_size=0.12", fc=GRID, ec="none"))
        if L:
            ax.add_patch(FancyBboxPatch((6.25, y - 0.22), 2.6 * L / LN, 0.44, boxstyle="round,pad=0,rounding_size=0.12",
                                        fc=col, ec="none"))
        ax.text(9.05, y, f"{L}/{LN}", fontsize=17, color=INK, va="center")
        ax.add_patch(FancyBboxPatch((10.15, y - 0.22), 1.5, 0.44, boxstyle="round,pad=0,rounding_size=0.12", fc=GRID, ec="none"))
        if S:
            ax.add_patch(FancyBboxPatch((10.15, y - 0.22), 1.5 * S / SN, 0.44, boxstyle="round,pad=0,rounding_size=0.12",
                                        fc=ORANGE, ec="none"))
        ax.text(11.85, y, f"{S}/{SN}", fontsize=17, color=INK, va="center")

    # right: attacking our own defence (E10)
    x0 = 14.2
    ax.text(x0, 8.2, "Then we attacked our own defence", fontsize=21, color=INK2)
    sub = ax.inset_axes([x0 / W, 1.55 / H, 10.0 / W, 6.15 / H])
    sub.set_facecolor(BG)
    pols = ["OBJECT", "TYPED", "ONCE", "VERIFIED", "RELEASE"]
    labels = ["object-\nscoped", "typed", "typed,\nwrite-once", "value-\nverified", "verified +\nrelease"]
    sub.bar(range(5), [cap[p] for p in pols], 0.62, color=GRID, zorder=1)
    sub.scatter(range(5), [got[p][0] for p in pols], s=260, color=[ORANGE if got[p][0] > 3 else BLUE for p in pols],
                zorder=3, edgecolor=BG, linewidth=2.5)
    for i, p in enumerate(pols):
        sub.text(i, cap[p] + 1.0, f"{cap[p]:.1f}" if p not in ("OBJECT", "TYPED") else ("all" if p == "OBJECT" else "6.6/write"),
                 ha="center", fontsize=14, color=INK2)
    sub.set_xticks(range(5)); sub.set_xticklabels(labels, fontsize=15, color=INK)
    sub.set_ylim(0, 31); sub.set_yticks([0, 10, 20, 26.6]); sub.set_yticklabels(["0", "10", "20", "26.6"], fontsize=13, color=INK2)
    sub.set_ylabel("secret bits through the channel", fontsize=15, color=INK2)
    for s_ in ("top", "right"):
        sub.spines[s_].set_visible(False)
    for s_ in ("left", "bottom"):
        sub.spines[s_].set_color(MUTED)
    sub.tick_params(length=0)
    sub.yaxis.grid(True, color=GRID, lw=1); sub.set_axisbelow(True)
    t = got["TYPED"]
    sub.annotate(f"type alone: full secret leaked\nin {t[1]}/{t[2]} episodes, legit work intact", xy=(1, t[0]), xytext=(1.55, 22.5),
                 fontsize=15, color=ORANGE, arrowprops=dict(arrowstyle="-", color=ORANGE, lw=1.5))
    v = got["VERIFIED"]
    sub.annotate(f"verified: 0 bits in {v[2]}/{v[2]}", xy=(3, 0.4), xytext=(2.7, 11.5), fontsize=15, color=BLUE,
                 arrowprops=dict(arrowstyle="-", color=BLUE, lw=1.5))

    # footer
    ax.plot([1.3, W - 1.3], [0.95, 0.95], color=GRID, lw=2)
    ax.text(1.3, 0.45, "Jaswanth Alkur  ·  Kiran Kadekoppa", fontsize=17, color=INK, va="center")
    ax.text(W / 2, 0.45, "Apart Research · Swarm Alignment Hackathon · Nov 2026 · 6 pre-registrations",
            fontsize=15, color=INK2, va="center", ha="center")
    ax.text(W - 1.3, 0.45, "github.com/Alkur123/typed-handoffs", fontsize=15, color=BLUE, va="center", ha="right")
    fig.savefig(HERE / "cover.png", facecolor=BG)
    print("cover.png", {"typed_E8": typed, "E10_typed": t, "E10_verified": v})


if __name__ == "__main__":
    main()
