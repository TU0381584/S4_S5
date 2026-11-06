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

mpl.rcParams.update({"font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
                     "axes.linewidth": 0.7, "pdf.fonttype": 42, "ps.fonttype": 42})
SUMMARY = "/home/kmanojp/oranslice_rig/experiments/results/m93/m93_summary.json"
OUT = "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures/fig_rliable"
TABLE = "/home/kmanojp/oranslice_rig/experiments/results/m93/table_rliable.tex"
STYLE = {"AXIOM": ("#0072B2", "-", 1.6), "DQN-SA": ("#009E73", "-", 1.1), "DQN-I": ("#D55E00", "-", 1.1),
         "MAPPO": ("#000000", "-", 1.1), "Static rule": ("#555555", "--", 1.1), "Tuned rule": ("#CC79A7", "--", 1.1)}
ORDER = ("Env A, 3 gNBs", "Env A, 7 gNBs", "Env A, 19 gNBs", "Env A, 37 gNBs", "Env B, 3 gNBs", "Env B, 7 gNBs", "Env B, 19 gNBs")
TAG = {"A": dict(fc="#e2e8f0", ec="#5a6b82", tc="#26344a"), "B": dict(fc="#f4ead6", ec="#9c7a45", tc="#4f3a15")}
MINUS = "−"


def figure(d):
    fig, axs = plt.subplots(2, 4, figsize=(SUPP_WIDTH_IN, 4.1), sharey=True)
    for i, name in enumerate(ORDER):
        ax = axs.flat[i]
        S = d["settings"][name]
        tau = np.array(S["profile_tau"])
        for k, p in S["policies"].items():
            c, ls, lw = STYLE[k]
            ci = np.array(p["profile_ci"])
            ax.fill_between(tau, ci[0], ci[1], color=c, alpha=0.12, lw=0)
            ax.plot(tau, p["profile"], color=c, ls=ls, lw=lw, zorder=3 if k == "AXIOM" else 2)
        env, size = name.split(", ")
        e = env[-1]
        ax.text(0.10, 1.05, f"Env {e}", transform=ax.transAxes, va="bottom", fontsize=8, color=TAG[e]["tc"],
                bbox=dict(boxstyle="round,pad=0.25", fc=TAG[e]["fc"], ec=TAG[e]["ec"], lw=0.6))
        ax.text(0.44, 1.05, size, transform=ax.transAxes, va="bottom", fontsize=8)
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 1.02)
        ax.set_xticks([0, 50, 100])
        ax.grid(alpha=0.25, lw=0.5)
        if i % 4 == 0:
            ax.set_ylabel("Fraction of runs above τ")
        if i >= 3:
            ax.set_xlabel("Priority-slice SLA τ, %")
        ax.text(-0.02, 1.05, "abcdefg"[i], transform=ax.transAxes, fontsize=9, va="bottom")
    leg = axs.flat[7]
    leg.axis("off")
    handles = [Line2D([], [], color=c, ls=ls, lw=lw, label=k) for k, (c, ls, lw) in STYLE.items()]
    leg.legend(handles=handles, loc="center", frameon=False, fontsize=8, handlelength=2.2)
    fig.tight_layout(w_pad=0.6, h_pad=1.4)
    fig.savefig(OUT + ".pdf", bbox_inches="tight", pad_inches=0.03)
    fig.savefig(OUT + ".png", dpi=200, bbox_inches="tight", pad_inches=0.03)


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
