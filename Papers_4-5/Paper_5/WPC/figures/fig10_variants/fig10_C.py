#!/usr/bin/env python3
"""Fig. 10, option C: annotated normalised heatmap. Every value comes from data.json (data.py).

Rows are the current figure's criteria without "Learns its rules" and without the score row; columns are the six
controllers. Each cell prints its raw value with units. Colour is the signed distance d to the row's target, divided
by the largest |d| in that row, so every row spans at most -1 to +1 and 0 is the target:
  size growth  d = -log10(params at 37 / params at 3)        target 0 (no growth)
  transfer     d = compliance after 7 to 37 - 90 (points)    target 90%
  compliance   d = compliance at 37 - 90 (points)            target 90%
  delay        d = log10(0.5 / delay)                        target 0.5 control periods
  past load    d = reward per step minus the tuned rule's, Env B, 19 gNBs, mean of 110, 115, 120% load; target 0
  steady load  d = the same at nominal load; target 0
Private training has no measured scale for five of six controllers and keeps words, uncoloured. Cells that were not
measured are white with hatching and "n/t"; "×" marks a controller that cannot run at another size.
Run: python fig10_C.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S  # noqa: E402
from data import load  # noqa: E402

S.setup()
import matplotlib as mpl  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

D = load()
CMAP = mpl.colormaps["cividis"]


def m(x):
    return f"{x}".replace("-", "−")


def r1(x):
    """one decimal, two when the value would otherwise print as zero"""
    return m(f"{x:+.2f}" if abs(x) < 0.05 and x != 0 else f"{x:+.1f}")


def rows():
    P, tr, sla, dl, past, st = D["params"], D["transfer37"], D["sla37"], D["delay37"], D["past19"], D["steady19"]
    R = []
    g = {}
    for a in S.ORDER:
        if a in P:
            v = P[a]["37"] / P[a]["3"]
            g[a] = (-np.log10(v), f"{P[a]['37']:,}\n×{v:.1f} from 3", "num")
        else:
            g[a] = (0.0, "no params", "num")
    R.append(("Parameter growth,\n3 to 37 gNBs", g))
    t = {}
    for a in S.ORDER:
        if a in tr:
            t[a] = (tr[a]["mean"] - 90, f"{tr[a]['mean']:.1f}%", "num")
        elif a in ("single_agent_dqn", "independent_dqn"):
            t[a] = (None, "×\nfixed input", "x")
        elif a == "rule_static":
            t[a] = (sla[a]["mean"] - 90, f"{sla[a]['mean']:.2f}%\nsize-free", "num")
        else:
            t[a] = (None, "n/t", "nt")
    R.append(("Compliance at 37,\ntrained at 7", t))
    R.append(("Compliance\nat 37 gNBs", {a: ((sla[a]["mean"] - 90, f"{sla[a]['mean']:.1f}%" if a in S.LEARNED else f"{sla[a]['mean']:.2f}%", "num")
                                            if a in sla else (None, "n/t", "nt")) for a in S.ORDER}))
    R.append(("URLLC delay\nat 37 gNBs", {a: ((np.log10(0.5 / dl[a]["mean"]), f"{dl[a]['mean']:.2f} cp", "num") if a in dl else (None, "n/t", "nt"))
                                          for a in S.ORDER}))
    pl = {a: (past[a]["mean"], r1(past[a]['mean']) + "\n/step", "num") for a in past}
    pl["rule_local"] = (0.0, "0\nreference", "num")
    R.append(("Past tuning load,\nvs tuned rule", pl))
    sl = {a: (st[a]["mean"], r1(st[a]['mean']) + "\n/step", "num") for a in st}
    sl["rule_local"] = (0.0, "0\nreference", "num")
    R.append(("Steady load,\nvs tuned rule", sl))
    pv = {"axiom2": "FedAvg,\nmeasured", "mappo_tuned": "pooled\n(design)", "single_agent_dqn": "pooled\n(design)",
          "independent_dqn": "local\n(design)", "rule_static": "no model", "rule_local": "no model"}
    R.append(("Private training", {a: (None, pv[a], "word") for a in S.ORDER}))
    return R


def main():
    Hmm = 92.0
    fig = plt.figure(figsize=(S.WIDTH_IN, Hmm / 25.4))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, S.WIDTH_MM); ax.set_ylim(Hmm, 0); ax.axis("off")
    x0, cw, y0, rh = 27.0, (S.WIDTH_MM - 27.0 - 1.0) / 6, 7.0, 9.4
    for i, a in enumerate(S.ORDER):
        ax.text(x0 + (i + 0.5) * cw, y0 - 2.6, S.NAME[a], ha="center", va="center", color=S.AX if a == "axiom2" else S.INK)
    R = rows()
    for j, (lab, cells) in enumerate(R):
        y = y0 + j * rh
        ax.text(1.0, y + rh / 2, lab, ha="left", va="center", linespacing=0.95)
        ds = [abs(c[0]) for c in cells.values() if c[0] is not None and c[2] == "num"]
        sc = max(ds) if ds and max(ds) > 0 else 1.0
        for i, a in enumerate(S.ORDER):
            d, txt, kind = cells[a]
            x = x0 + i * cw
            if kind == "num":
                z = d / sc
                col = CMAP(0.5 + 0.5 * z)
                ax.add_patch(Rectangle((x + 0.3, y + 0.3), cw - 0.6, rh - 0.6, fc=col, ec="none"))
                tc = "white" if np.dot(col[:3], [0.299, 0.587, 0.114]) < 0.5 else S.INK
            else:
                ax.add_patch(Rectangle((x + 0.3, y + 0.3), cw - 0.6, rh - 0.6, fc="white", ec=S.FAINT, lw=0.5,
                                       hatch="////" if kind == "nt" else None))
                tc = "#555555" if kind != "word" else S.INK
            ax.text(x + cw / 2, y + rh / 2, txt, ha="center", va="center", color=tc, linespacing=0.95)
    yb = y0 + len(R) * rh + 4.0
    ax.plot([x0 + 4 * cw, x0 + 4 * cw], [y0 - 5, y0 + len(R) * rh], color=S.INK, lw=0.5)
    cax = fig.add_axes([(x0 + 0.5 * cw) / S.WIDTH_MM, 1 - (yb + 2.2) / Hmm, 3 * cw / S.WIDTH_MM, 2.2 / Hmm])
    cb = mpl.colorbar.ColorbarBase(cax, cmap=CMAP, norm=mpl.colors.Normalize(-1, 1), orientation="horizontal")
    cb.set_ticks([-1, 0, 1]); cb.set_ticklabels(["\u22121, worse", "0, at target", "+1, better"])
    cb.outline.set_linewidth(0.5)
    cax.set_xlabel("Signed distance to the row's target, divided by the row's largest distance", labelpad=2)
    return S.save(fig, "fig10_C")


if __name__ == "__main__":
    main()
