"""Online Resource 1: performance profiles of priority-slice SLA compliance, and the rliable summary table.

Reads experiments/results/m93/m93_summary.json, written by experiments/scripts/m93_rliable.py (rliable 1.2.0).
Each panel shows, for one reported setting, the fraction of runs whose priority-slice SLA compliance exceeds tau,
with its stratified bootstrap 95% band. The table rows are written to experiments/results/m93/table_rliable.tex.
"""
import json
import sys

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/plots")
from paper5_common import SUPP_WIDTH_IN  # noqa: E402

sys.path.insert(0, "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures")
import axiom_style as S  # noqa: E402
S.setup()
SUMMARY = "/home/kmanojp/oranslice_rig/experiments/results/m93/m93_summary.json"
OUT = "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures/fig_rliable"
TABLE = "/home/kmanojp/oranslice_rig/experiments/results/m93/table_rliable.tex"
# figure-audit tokens: AXIOM blue, learned baselines grey told apart by line style, rules vermillion
# pre-audit colours restored (2026-11-09); line styles keep the rules apart without colour
STYLE = {"AXIOM": ("#0072B2", "-", 1.6), "DQN-SA": ("#009E73", "-", 1.1), "DQN-I": ("#D55E00", "-", 1.1),
         "MAPPO": ("#000000", "-", 1.1), "Static rule": ("#555555", (0, (4, 1.5)), 1.1), "Tuned rule": ("#CC79A7", (0, (4, 1.5)), 1.1)}
ORDER = ("Env A, 3 gNBs", "Env A, 7 gNBs", "Env A, 19 gNBs", "Env A, 37 gNBs", "Env B, 3 gNBs", "Env B, 7 gNBs", "Env B, 19 gNBs")
TAG = {"A": dict(fc="#e2e8f0", ec="#5a6b82", tc="#26344a"), "B": dict(fc="#f4ead6", ec="#9c7a45", tc="#4f3a15")}
MINUS = "−"


def figure(d):
    """Figure audit: a 4 x 2 grid, Env A down the left column and Env B down the right, the legend in the last cell.
    Tokens of figures/axiom_style.py; CI bands are opaque tints with their edges drawn, since EPS has no transparency."""
    fig = S.figure("full", 150)
    fw, fh = (lambda mm: mm / 119.0), (lambda mm: mm / 150.0)
    slots = {"Env A, 3 gNBs": (0, 0), "Env A, 7 gNBs": (0, 1), "Env A, 19 gNBs": (0, 2), "Env A, 37 gNBs": (0, 3),
             "Env B, 3 gNBs": (1, 0), "Env B, 7 gNBs": (1, 1), "Env B, 19 gNBs": (1, 2)}
    for i, name in enumerate(ORDER):
        col, row = slots[name]
        ax = fig.add_axes([fw(14 + col * 56), fh(150 - 31 - row * 34.5), fw(46), fh(24)])
        St = d["settings"][name]
        tau = np.array(St["profile_tau"])
        for k, p in St["policies"].items():
            c, ls, lw = STYLE[k]
            ci = np.array(p["profile_ci"])
            ax.fill_between(tau, ci[0], ci[1], color=S.lighten(c, 0.88), lw=0, zorder=0)   # opaque tint, EPS-safe
            for e_ in ci:   # band edges stay visible where bands overlap
                ax.plot(tau, e_, color=S.lighten(c, 0.45), lw=0.4, ls=ls, zorder=1)
            ax.plot(tau, p["profile"], color=c, ls=ls, lw=lw, zorder=3 if k == "AXIOM" else 2)
        ax.set_xlim(0, 100); ax.set_ylim(0, 1.02); ax.set_xticks([0, 50, 100]); ax.set_yticks([0, 0.5, 1])
        env_, size_ = name.split(", ")
        tg_ = S.ENV_TAG[env_[-1]]
        ax.text(0.0, 1.05, env_, transform=ax.transAxes, va="bottom", color=tg_["tc"],
                bbox=dict(boxstyle="round,pad=0.25", fc=tg_["fc"], ec=tg_["ec"], lw=0.6))
        ax.text(0.30, 1.05, size_, transform=ax.transAxes, va="bottom")
        ax.text(-0.2, 1.08, "abcdefg"[i], transform=ax.transAxes, fontweight="bold", va="bottom")
        if col == 0:
            ax.set_ylabel("Fraction of runs\nabove \u03c4")
        if row == 3 or (col == 1 and row == 2):
            ax.set_xlabel("Priority-slice compliance \u03c4 (%)")
    leg = fig.add_axes([fw(70), fh(150 - 31 - 3 * 34.5), fw(46), fh(24)]); leg.axis("off")
    handles = [Line2D([], [], color=c, ls=ls, lw=lw, label=k) for k, (c, ls, lw) in STYLE.items()]
    leg.legend(handles=handles, loc="center", frameon=False, handlelength=2.6)
    print(S.save(fig, OUT))


def fmt(x, nd):
    s = f"{x:.{nd}f}"
    return s.replace("-", "$-$")


def table(d):
    lines = []
    for name in ORDER:
        S = d["settings"][name]
        lines.append(f"\\multicolumn{{6}}{{@{{}}l}}{{{name}}} \\\\")
        for k, p in S["policies"].items():
            r = f"{fmt(p['iqm_reward'], 3)} [{fmt(p['iqm_reward_ci'][0], 2)}, {fmt(p['iqm_reward_ci'][1], 2)}]"
            s = f"{fmt(p['iqm_prio'], 1)} [{fmt(p['iqm_prio_ci'][0], 1)}, {fmt(p['iqm_prio_ci'][1], 1)}]"
            if k == "AXIOM":
                pr = ps = "--"
            else:
                pr = f"{p['poi_reward']:.2f} [{p['poi_reward_ci'][0]:.2f}, {p['poi_reward_ci'][1]:.2f}]"
                ps = f"{p['poi_prio']:.2f} [{p['poi_prio_ci'][0]:.2f}, {p['poi_prio_ci'][1]:.2f}]"
            lines.append(f"\\quad {k} & {p['runs']} & {r} & {s} & {pr} & {ps} \\\\")
        if name != ORDER[-1]:
            lines.append("\\midrule")
    open(TABLE, "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    d = json.load(open(SUMMARY))
    figure(d)
    table(d)
    print("wrote", OUT + ".pdf", "and", TABLE)
