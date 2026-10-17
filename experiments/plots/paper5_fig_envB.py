#!/usr/bin/env python3
"""Env B (M64) results figure.
(a) Mean reward per step at N=3, every arm, per-seed points behind the mean and 95% CI.
(b) URLLC and eMBB SLA compliance at N=3, every arm.
(c) Mean URLLC/eMBB compliance at N=7 by layout for the learned arms (attention test: AXIOM vs MLP).
Writes a JSON of every plotted number next to the figure.

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
from paper5_common import M2_ARM_STYLE, RULE_STYLE  # noqa: E402

N3_ARMS = ["rule_accept_all", "rule_static", "rule_local", "rule_neighbour",
           "single_agent_dqn", "independent_dqn", "mappo_tuned", "axiom2_mlp", "axiom2"]
N7_ARMS = ["single_agent_dqn", "independent_dqn", "mappo_tuned", "axiom2_mlp", "axiom2"]
SHORT = {"rule_accept_all": "Accept\nall", "rule_static": "Shed\nmMTC", "rule_local": "Tuned\nlocal",
         "rule_neighbour": "Tuned\nneigh.", "single_agent_dqn": "Single\nDQN", "independent_dqn": "Indep.\nDQN",
         "mappo_tuned": "MAPPO", "axiom2_mlp": "AXIOM\nMLP", "axiom2": "AXIOM"}


def style(arm):
    return RULE_STYLE.get(arm) or M2_ARM_STYLE[arm]


def load(cell, arms, seeds):
    return {a: [seed_metrics(p) for s in seeds if (p := eval_log(cell, a, s))] for a in arms}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    S30 = list(range(900, 930)); S15 = list(range(900, 912)) + [1000, 1001, 1002]
    d3 = load(f"{a.root}/n3_fully_connected", N3_ARMS, S30)
    d7 = {t: load(f"{a.root}/n7_{t}", N7_ARMS, S15) for t in ("fully_connected", "ring", "hex")}
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(10.6, 2.9), gridspec_kw={"width_ratios": [1.25, 1.25, 1]})
    rng = np.random.RandomState(0)
    summ = {"n3": {}, "n7": {}}
    for i, arm in enumerate(N3_ARMS):
        rows = d3[arm]
        if not rows:
            continue
        st = style(arm)
        r = [x["reward"] for x in rows]
        lo, hi = boot_ci(r)
        ax1.scatter(i + rng.uniform(-0.12, 0.12, len(r)), r, s=6, color=st["color"], alpha=0.35, lw=0)
        ax1.errorbar(i, np.mean(r), yerr=[[np.mean(r) - lo], [hi - np.mean(r)]], fmt=st["marker"],
                     color=st["color"], ms=6, capsize=3, lw=1.2)
        u = np.mean([x["sla"]["urllc"] for x in rows]); e = np.mean([x["sla"]["embb"] for x in rows])
        ax2.bar(i - 0.2, u, 0.4, color=st["color"], alpha=0.95)
        ax2.bar(i + 0.2, e, 0.4, color=st["color"], alpha=0.45, hatch="///", edgecolor="white", lw=0)
        summ["n3"][arm] = {"n": len(rows), "reward": float(np.mean(r)), "ci": [lo, hi], "urllc": float(u), "embb": float(e),
                           "collapsed": int(sum(x["collapsed"] for x in rows))}
    for ax in (ax1, ax2):
        ax.set_xticks(range(len(N3_ARMS)))
        ax.set_xticklabels([SHORT[x] for x in N3_ARMS], fontsize=6.3)
        ax.axvline(3.5, color="#999", lw=0.6, ls=":")
        ax.grid(True, axis="y", lw=0.4, alpha=0.4)
        ax.spines[["top", "right"]].set_visible(False)
    ax1.set_ylabel("Mean reward per step")
    ax1.set_title("(a) Reward, 3 gNBs", loc="left", fontsize=9)
    ax2.set_ylabel("SLA compliance")
    ax2.set_ylim(0, 1.05)
    ax2.set_title("(b) URLLC solid, eMBB hatched, 3 gNBs", loc="left", fontsize=9)
    topo = ["fully_connected", "ring", "hex"]
    w = 0.8 / len(N7_ARMS)
    for j, arm in enumerate(N7_ARMS):
        st = style(arm)
        for k, t in enumerate(topo):
            rows = d7[t][arm]
            if not rows:
                continue
            v = [0.5 * (x["sla"]["urllc"] + x["sla"]["embb"]) for x in rows]
            lo, hi = boot_ci(v) if len(v) > 1 else (v[0], v[0])
            x0 = k - 0.4 + w * (j + 0.5)
            ax3.errorbar(x0, np.mean(v), yerr=[[np.mean(v) - lo], [hi - np.mean(v)]], fmt=st["marker"],
                         color=st["color"], ms=5, capsize=2, lw=1.1, label=st["label"].replace(" (proposed)", "") if k == 0 else None)
            summ["n7"].setdefault(t, {})[arm] = {"n": len(rows), "prio": float(np.mean(v)), "ci": [lo, hi],
                                                 "reward": float(np.mean([x["reward"] for x in rows]))}
    ax3.set_xticks(range(3))
    ax3.set_xticklabels(["Fully-\nconnected", "Ring", "Hex"], fontsize=7)
    ax3.set_ylabel("URLLC and eMBB SLA, 7 gNBs")
    ax3.set_title("(c) 7 gNBs by layout", loc="left", fontsize=9)
    ax3.grid(True, axis="y", lw=0.4, alpha=0.4)
    ax3.spines[["top", "right"]].set_visible(False)
    ax3.legend(fontsize=5.8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3)
    fig.tight_layout()
    fig.savefig(a.out + ".pdf", bbox_inches="tight")
    fig.savefig(a.out + ".png", dpi=200, bbox_inches="tight")
    json.dump(summ, open(a.out + "_summary.json", "w"), indent=1)
    print(json.dumps(summ, indent=1)[:3000])


if __name__ == "__main__":
    main()
