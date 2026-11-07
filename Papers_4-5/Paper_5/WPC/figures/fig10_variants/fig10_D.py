#!/usr/bin/env python3
"""Fig. 10, option D: radar chart, for comparison only. Every value comes from data.json (data.py).

Six axes, each min-max normalised across the controllers that have a value on it (0 = lowest, 1 = highest):
  compliance at 37 gNBs (%), 1/URLLC delay (1/control periods), log10(1/parameters at 37 gNBs), compliance at 37 after
  training at 7 (%), reward per step minus the tuned rule's past the tuning load (Env B, 19 gNBs, mean of 110-120%),
  and the same at nominal load. Missing values break the outline: rules have no learned parameters, DQN-SA and DQN-I
  cannot run at another size, and the tuned rule was not carried across sizes in Env A.
Writes fig10_D (default order) and fig10_D_alt (permuted order) to show how the shape depends on axis order.
Run: python fig10_D.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S  # noqa: E402
from data import load  # noqa: E402

S.setup()
import matplotlib.pyplot as plt  # noqa: E402

D = load()
LS = {"axiom2": "-", "mappo_tuned": "-", "single_agent_dqn": (0, (4, 1.5)), "independent_dqn": (0, (1, 1.2)),
      "rule_static": "-", "rule_local": (0, (4, 1.5))}


def raw():
    sla, dl, P, tr, past, st = D["sla37"], D["delay37"], D["params"], D["transfer37"], D["past19"], D["steady19"]
    ax = {}
    ax["comp"] = {a: sla[a]["mean"] for a in S.ORDER if a in sla}
    ax["delay"] = {a: 1 / dl[a]["mean"] for a in S.ORDER if a in dl}
    ax["params"] = {a: np.log10(1 / P[a]["37"]) for a in S.LEARNED}
    ax["transfer"] = {a: tr[a]["mean"] for a in tr} | {"rule_static": sla["rule_static"]["mean"]}
    ax["past"] = {a: past[a]["mean"] for a in past} | {"rule_local": 0.0}
    ax["steady"] = {a: st[a]["mean"] for a in st} | {"rule_local": 0.0}
    return ax


LABEL = {"comp": "Compliance,\n37 gNBs", "delay": "1 / URLLC\ndelay", "params": "log(1 / params)",
         "transfer": "Compliance at 37,\ntrained at 7", "past": "Reward past\ntuning load", "steady": "Reward at\nsteady load"}


def draw(order, stem):
    R = raw()
    N = {k: {a: (v - min(d.values())) / (max(d.values()) - min(d.values())) for a, v in d.items()} for k, d in R.items()}
    th = np.linspace(0, 2 * np.pi, len(order), endpoint=False)
    fig = plt.figure(figsize=(S.WIDTH_IN, 84 / 25.4))
    ax = fig.add_axes([0.06, 0.10, 0.52, 0.80], polar=True)
    ax.set_theta_offset(np.pi / 2); ax.set_theta_direction(-1)
    ax.set_ylim(0, 1); ax.set_yticks([0.5, 1.0]); ax.set_yticklabels(["0.5", "1"]); ax.set_rlabel_position(0)
    ax.set_xticks(th); ax.set_xticklabels([LABEL[k] for k in order])
    ax.tick_params(axis="x", pad=6)
    ax.grid(color=S.FAINT, lw=0.5); ax.spines["polar"].set_linewidth(0.5)
    hs = []
    for a in S.ORDER[::-1]:
        vals = [N[k].get(a) for k in order]
        lw = 1.8 if a == "axiom2" else 0.7
        for i in range(len(order)):
            j = (i + 1) % len(order)
            if vals[i] is not None and vals[j] is not None:
                t2 = th[j] if j else 2 * np.pi
                ax.plot([th[i], t2], [vals[i], vals[j]], color=S.COLOR[a], lw=lw, ls=LS[a], zorder=5 if a == "axiom2" else 3)
        pts = [(t, v) for t, v in zip(th, vals) if v is not None]
        h, = ax.plot([p[0] for p in pts], [p[1] for p in pts], zorder=6, **S.marker_kw(a, ms=3.4 if a != "axiom2" else 4.2))
        h.set_linestyle(LS[a]); h.set_linewidth(lw); h.set_color(S.COLOR[a])
        h.set_data([p[0] for p in pts], [p[1] for p in pts]); h.set_linestyle("none")
        hs.append((a, ax.plot([], [], color=S.COLOR[a], lw=lw, ls=LS[a], **{k: v for k, v in S.marker_kw(a, ms=3.6).items() if k != "ls"})[0]))
    hs = [h for a in S.ORDER for b, h in hs if a == b]
    fig.legend(hs, [S.NAME[a] for a in S.ORDER], loc="center left", bbox_to_anchor=(0.66, 0.62), frameon=False, handlelength=2.6)
    fig.text(0.66, 0.24, "Each axis min-max scaled\nover the controllers with a\nvalue; a gap means no value", ha="left", va="center",
             color="#444444", linespacing=1.0)
    return S.save(fig, stem)


def main():
    a = draw(["comp", "delay", "params", "transfer", "past", "steady"], "fig10_D")
    b = draw(["comp", "transfer", "steady", "delay", "past", "params"], "fig10_D_alt")
    return a, b


if __name__ == "__main__":
    main()
