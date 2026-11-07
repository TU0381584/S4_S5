#!/usr/bin/env python3
"""Fig. 10, option B: trade-off scatter. Every value comes from data.json (data.py).

a, parameters at execution (log) against priority-slice compliance at 37 gNBs (Env A). Learned controllers trained at
37 gNBs as points with 95% bootstrap CIs; rules as horizontal reference lines. For AXIOM and MAPPO an arrow runs from
the 7-gNB checkpoint's compliance at 7 gNBs to the same checkpoint's compliance at 37 gNBs (measured, M92). DQN-SA and
DQN-I are marked at their 7-gNB size with a cross, since their input size is fixed.
b, URLLC backlog delay (log) against compliance at 37 gNBs on the hex layout, paired per seed; ellipses are one
standard deviation of the per-seed points, covariance taken in log10 delay and compliance.
Run: python fig10_B.py
"""
import os
import sys

import numpy as np
import matplotlib as mpl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S  # noqa: E402
from data import load  # noqa: E402

S.setup()
import matplotlib.pyplot as plt  # noqa: E402

D = load()
LBL = {"axiom2": (0.8, 0.0, "right"), "mappo_tuned": (1.25, -4.5, "left"), "single_agent_dqn": (1.25, -4.5, "left"),
       "independent_dqn": (0.8, 0.0, "right")}
XOFF = {"axiom2": 1.55, "mappo_tuned": 0.62}       # arrows drawn beside the 37-gNB point so the two never overlap


def panel_a(ax):
    P, sla, c7, tr = D["params"], D["sla37"], D["compliance7"], D["transfer37"]
    ax.axhline(90, color=S.INK, lw=0.6, ls=(0, (3, 2)), zorder=1)
    for a, ls in (("rule_static", "-"), ("rule_local", (0, (4, 1.5)))):
        if a in sla:
            ax.axhline(sla[a]["mean"], color=S.RULE, lw=0.9, ls=ls, zorder=1)
    for a in S.LEARNED:
        m, (lo, hi) = sla[a]["mean"], sla[a]["ci95"]
        x = P[a]["37"]
        ax.errorbar([x], [m], yerr=[[m - lo], [hi - m]], color=S.COLOR[a], elinewidth=0.9, capsize=1.6, capthick=0.6, zorder=3,
                    **S.marker_kw(a, ms=4.6))
        f, dy, ha = LBL[a]
        ax.text(x * f, m + dy, S.NAME[a], ha=ha, va="center", color=S.AX if a == "axiom2" else S.INK)
    for a in ("axiom2", "mappo_tuned"):
        x7 = P[a]["7"] * XOFF[a]
        y0, y1 = c7[a]["mean"], tr[a]["mean"]
        ax.plot([x7], [y0], marker=S.MARKER[a], ms=3.6, mec=S.COLOR[a], mfc="white", mew=0.8, ls="none", zorder=4)
        ax.annotate("", xy=(x7, y1), xytext=(x7, y0), arrowprops=dict(arrowstyle="-|>", color=S.COLOR[a], lw=0.8,
                    mutation_scale=6, shrinkA=2.2, shrinkB=0), zorder=4)
    for a in ("single_agent_dqn", "independent_dqn"):
        x7, y0 = P[a]["7"], c7[a]["mean"]
        ax.plot([x7], [y0], marker=S.MARKER[a], ms=3.6, mec=S.COLOR[a], mfc="white", mew=0.8, ls="none", zorder=4)
        ax.plot([x7], [y0 - 6], marker="x", ms=4.0, mec=S.INK, mew=0.9, ls="none", zorder=4)
    ax.set_xscale("log"); ax.set_xlim(2e3, 2e6); ax.set_ylim(0, 108)
    ax.set_xticks([1e4, 1e5, 1e6]); ax.set_xticklabels(["10k", "100k", "1M"])
    ax.xaxis.set_minor_formatter(mpl.ticker.NullFormatter())
    ax.set_xlabel("Parameters at execution (count, log scale)")
    ax.set_ylabel("Compliance at 37 gNBs (%)")
    txt = f"Rules: static {sla['rule_static']['mean']:.2f}%, " + (f"tuned {sla['rule_local']['mean']:.2f}%" if "rule_local" in sla else "tuned n/t")
    ax.text(1.9e6, 104.5, txt, ha="right", va="center", color=S.RULE)


def ellipse(ax, x, y, color, ls="-"):
    lx = np.log10(np.asarray(x)); y = np.asarray(y)
    if len(lx) < 3 or np.allclose(np.cov(lx, y), 0):
        return
    C = np.cov(lx, y)
    w, V = np.linalg.eigh(C)
    t = np.linspace(0, 2 * np.pi, 200)
    pts = V @ (np.sqrt(np.maximum(w, 0))[:, None] * np.vstack([np.cos(t), np.sin(t)]))
    ax.plot(10 ** (lx.mean() + pts[0]), y.mean() + pts[1], color=color, lw=0.6, ls=ls, zorder=2)


def panel_b(ax):
    sla, dl = D["sla37"], D["delay37"]
    for a in S.ORDER:
        sk = "axiom2_hex" if a == "axiom2" else a
        if sk not in sla or a not in dl:
            continue
        common = sorted(set(sla[sk]["per_seed"]) & set(dl[a]["per_seed"]))
        x = [dl[a]["per_seed"][s] for s in common]; y = [sla[sk]["per_seed"][s] for s in common]
        ax.scatter(x, y, s=1.4, c=S.COLOR[a], alpha=0.35, lw=0, zorder=2)
        ellipse(ax, x, y, S.COLOR[a], ls="-" if a in S.LEARNED else (0, (3, 1.5)))
        ax.plot([np.mean(x)], [np.mean(y)], zorder=4, **S.marker_kw(a, ms=4.2))
    ax.axhline(90, color=S.INK, lw=0.6, ls=(0, (3, 2)), zorder=1)
    ax.axvline(0.5, color=S.INK, lw=0.6, ls=(0, (3, 2)), zorder=1)
    ax.set_xscale("log"); ax.set_ylim(0, 108); ax.set_xlim(5e-3, 80)
    ax.set_xticks([0.01, 0.1, 1, 10]); ax.set_xticklabels(["0.01", "0.1", "1", "10"])
    ax.xaxis.set_minor_formatter(mpl.ticker.NullFormatter())
    ax.set_xlabel("URLLC delay (control\nperiods, log scale)")
    ax.set_ylabel("Compliance at 37 gNBs, hex (%)")


def main():
    Hmm = 84.0
    fig = plt.figure(figsize=(S.WIDTH_IN, Hmm / 25.4))
    fw = lambda mm: mm / S.WIDTH_MM; fh = lambda mm: mm / Hmm
    axa = fig.add_axes([fw(11), fh(27), fw(68), fh(54)])
    axb = fig.add_axes([fw(95), fh(27), fw(34), fh(54)])
    panel_a(axa); panel_b(axb)
    fig.text(fw(0.8), fh(81.5), "a", fontweight="bold", va="center")
    fig.text(fw(85), fh(81.5), "b", fontweight="bold", va="center")
    from matplotlib.lines import Line2D
    hs = [Line2D([], [], label=S.NAME[a], **S.marker_kw(a, ms=4.2)) for a in S.LEARNED]
    hs += [Line2D([], [], color=S.RULE, lw=0.9, ls="-", label="Static rule", **{k: v for k, v in S.marker_kw("rule_static", ms=4.2).items() if k != "ls"}),
           Line2D([], [], color=S.RULE, lw=0.9, ls=(0, (4, 1.5)), label="Tuned rule", **{k: v for k, v in S.marker_kw("rule_local", ms=4.2).items() if k != "ls"})]
    hs += [Line2D([], [], marker="o", ms=3.6, mec=S.INK, mfc="white", mew=0.8, ls="none", label="Trained and run at 7 gNBs"),
           Line2D([], [], marker=r"$\downarrow$", ms=6, color=S.INK, ls="none", label="Same checkpoint at 37"),
           Line2D([], [], marker="x", ms=4, mec=S.INK, mew=0.9, ls="none", label="Fixed input, cannot run at 37")]
    fig.legend(handles=hs[:6], loc="lower left", ncol=6, frameon=False, bbox_to_anchor=(fw(1), fh(5.5)), handletextpad=0.3,
               columnspacing=1.0, handlelength=1.8)
    fig.legend(handles=hs[6:], loc="lower left", ncol=3, frameon=False, bbox_to_anchor=(fw(1), fh(0.5)), handletextpad=0.3,
               columnspacing=1.0)
    return S.save(fig, "fig10_B")


if __name__ == "__main__":
    main()
