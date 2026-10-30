#!/usr/bin/env python3
"""Env B (M64) results figure: mean reward per step at N=3 for the learned
policies, per-seed points behind the mean and 95% CI. The rules are reported
in the text and in Table tab:envb, not plotted. Writes a JSON of every
plotted number next to the figure.

Usage: paper5_fig_envB.py --root experiments/results/m64 --out Papers_4-5/Paper_5/WPC/figures/fig11_envB
"""
import argparse
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
from m62_analysis import boot_ci, eval_log, seed_metrics  # noqa: E402
from paper5_common import M2_ARM_STYLE, MAIN_WIDTH_IN, RULE_STYLE  # noqa: E402,F401

N3_ARMS = ["single_agent_dqn", "independent_dqn", "mappo_tuned", "axiom2"]
SHORT = {"single_agent_dqn": "DQN-SA", "independent_dqn": "DQN-I",
         "mappo_tuned": "MAPPO", "axiom2": "AXIOM\n(proposed)"}


def style(arm):
    return RULE_STYLE.get(arm) or M2_ARM_STYLE[arm]


def load(cell, arms, seeds):
    return {a: [seed_metrics(p) for s in seeds if (p := eval_log(cell, a, s))] for a in arms}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    S30 = list(range(900, 930))
    d3 = load(f"{a.root}/n3_fully_connected", N3_ARMS, S30)
    fig, ax = plt.subplots(figsize=(0.72 * MAIN_WIDTH_IN, 2.1))
    rng = np.random.RandomState(0)
    summ = {"n3": {}}
    for i, arm in enumerate(N3_ARMS):
        rows = d3[arm]
        st = style(arm)
        r = [x["reward"] for x in rows]
        lo, hi = boot_ci(r)
        m = float(np.mean(r))
        emph = arm == "axiom2"
        if emph:
            ax.axvspan(i - 0.42, i + 0.42, color=st["color"], alpha=0.08, lw=0)
        ax.scatter(i + rng.uniform(-0.16, 0.16, len(r)), r, s=6, color=st["color"], alpha=0.35, lw=0)
        ax.errorbar(i, m, yerr=[[m - lo], [hi - m]], fmt=st["marker"], color=st["color"],
                    ms=6.5 if emph else 5, capsize=3, lw=1.3 if emph else 1.0, mec="white" if emph else st["color"], zorder=5)
        ax.text(i + 0.24, m, f"{m:.2f}", fontsize=8.5, va="center", ha="left", color=st["color"],
                fontweight="normal")
        summ["n3"][arm] = {"n": len(rows), "reward": m, "ci": [lo, hi],
                           "urllc": float(np.mean([x["sla"]["urllc"] for x in rows])),
                           "embb": float(np.mean([x["sla"]["embb"] for x in rows])),
                           "collapsed": int(sum(x["collapsed"] for x in rows))}
    ax.set_xticks(range(len(N3_ARMS)))
    ax.set_xticklabels([SHORT[x] for x in N3_ARMS], fontsize=8.5)
    ax.set_xlim(-0.55, len(N3_ARMS) - 0.35)
    ax.set_ylabel("Reward per step, 3 gNBs", fontsize=8.5)
    ax.tick_params(axis="y", labelsize=8.5)
    ax.grid(True, axis="y", lw=0.4, alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(a.out + ".pdf", bbox_inches="tight")
    fig.savefig(a.out + ".png", dpi=200, bbox_inches="tight")
    json.dump(summ, open(a.out + "_summary.json", "w"), indent=1)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
