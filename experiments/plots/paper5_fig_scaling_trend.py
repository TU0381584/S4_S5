#!/usr/bin/env python3
"""AXIOM's advantage as the Env A cluster grows from 3 to 7 to 19 gNBs.

(a) Priority-slice compliance, the mean of URLLC and eMBB SLA compliance, per
    learned policy, mean and 95% bootstrap CI over all seeds and layouts.
(b) Share of trained policies that collapse into accepting every request.
(c) Parameters used at execution, from the measured complexity table.

Data: three gNBs from the 30-seed Env A campaign (m65_n3_view, fully-connected);
seven gNBs from 15 seeds under each of three layouts (45 cells); nineteen gNBs
from 30 seeds under each of three layouts (90 cells). Every plotted number is
written to <out>_summary.json.

Usage: paper5_fig_scaling_trend.py --out Papers_4-5/Paper_5/WPC/figures/fig6_scaling_trend
"""
import argparse
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/plots")
from m62_analysis import boot_ci  # noqa: E402
from m66_verify import ROOT, S15, S30, S30_19, prio, seeds_of  # noqa: E402
from paper5_common import M2_ARM_STYLE  # noqa: E402

ARMS = ["axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned"]
LABEL = {"axiom2": "AXIOM (proposed)", "single_agent_dqn": "Single-agent DQN",
         "independent_dqn": "Independent DQN", "mappo_tuned": "MAPPO"}
COMPLEXITY_KEY = {"axiom2": "axiom2", "single_agent_dqn": "single_agent_dqn",
                  "independent_dqn": "independent_dqn", "mappo_tuned": "mappo"}
LAYOUTS = ("fully_connected", "ring", "hex")


def cells(n, arm):
    if n == 3:
        return list(seeds_of("m65_n3_view", arm, S30).values())
    seeds = S15 if n == 7 else S30_19
    return [r for t in LAYOUTS for r in seeds_of(f"m65_scaling/n{n}_{t}", arm, seeds).values()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    comp = json.load(open(f"{ROOT}/m64/complexity.json"))
    sizes = [3, 7, 19]
    summ = {}
    for arm in ARMS:
        summ[arm] = {}
        for n in sizes:
            rows = cells(n, arm)
            v = [100 * prio(r) for r in rows]
            lo, hi = boot_ci(v)
            summ[arm][n] = {"n_cells": len(rows), "prio_mean": float(np.mean(v)), "prio_ci": [lo, hi],
                            "collapsed": int(sum(r["collapsed"] for r in rows)),
                            "params": comp[str(n)][COMPLEXITY_KEY[arm]]["params_execution"]}
    fig, axs = plt.subplots(1, 3, figsize=(10.4, 3.25), gridspec_kw={"width_ratios": [1.35, 1, 1]})
    xs = np.arange(len(sizes))
    for arm in ARMS:
        st = M2_ARM_STYLE[arm]
        emph = arm == "axiom2"
        kw = dict(color=st["color"], marker=st["marker"], lw=2.8 if emph else 1.3, ms=8 if emph else 5,
                  alpha=1.0 if emph else 0.75, zorder=5 if emph else 3, label=LABEL[arm])
        m = [summ[arm][n]["prio_mean"] for n in sizes]
        lo = [summ[arm][n]["prio_ci"][0] for n in sizes]
        hi = [summ[arm][n]["prio_ci"][1] for n in sizes]
        axs[0].plot(xs, m, **kw)
        axs[0].fill_between(xs, lo, hi, color=st["color"], alpha=0.18 if emph else 0.08, lw=0)
        axs[1].plot(xs, [100 * summ[arm][n]["collapsed"] / summ[arm][n]["n_cells"] for n in sizes], **kw)
        axs[2].plot(xs, [summ[arm][n]["params"] for n in sizes], **kw)
    for i, n in enumerate(sizes):
        v = summ["axiom2"][n]["prio_mean"]
        axs[0].annotate(f"{v:.1f}%", (i, v), textcoords="offset points", xytext=(0, 8), ha="center",
                        fontsize=8, color=M2_ARM_STYLE["axiom2"]["color"], fontweight="bold")
    gap19 = summ["axiom2"][19]["prio_mean"] - max(summ[b][19]["prio_mean"] for b in ARMS[1:])
    axs[0].annotate("", xy=(2.18, summ["axiom2"][19]["prio_mean"]),
                    xytext=(2.18, max(summ[b][19]["prio_mean"] for b in ARMS[1:])),
                    arrowprops=dict(arrowstyle="<->", color="#1f5fae", lw=1.3))
    axs[0].text(2.24, (summ["axiom2"][19]["prio_mean"] + max(summ[b][19]["prio_mean"] for b in ARMS[1:])) / 2,
                f"+{gap19:.0f}\npoints", fontsize=8, color="#1f5fae", va="center", fontweight="bold")
    axs[0].set_ylabel("Priority-slice SLA compliance, %")
    axs[0].set_ylim(40, 104)
    axs[0].set_title("(a) Compliance as the cluster grows", loc="left", fontsize=9.5)
    axs[1].set_ylabel("Collapsed policies, % of cells")
    axs[1].set_title("(b) Collapse into accept-all", loc="left", fontsize=9.5)
    axs[2].set_ylabel("Parameters at execution")
    axs[2].set_yscale("log")
    axs[2].set_title("(c) Model size", loc="left", fontsize=9.5)
    for ax in axs:
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{n} gNBs" for n in sizes])
        ax.set_xlim(-0.3, 2.55)
        ax.grid(True, axis="y", lw=0.4, alpha=0.4)
        ax.spines[["top", "right"]].set_visible(False)
    axs[0].legend(fontsize=7.5, frameon=False, loc="lower left")
    fig.tight_layout()
    fig.savefig(a.out + ".pdf", bbox_inches="tight")
    fig.savefig(a.out + ".png", dpi=200, bbox_inches="tight")
    json.dump({"gap19_points": gap19, "arms": summ}, open(a.out + "_summary.json", "w"), indent=1)
    for arm in ARMS:
        print(arm, {n: (round(summ[arm][n]["prio_mean"], 1), summ[arm][n]["collapsed"], summ[arm][n]["n_cells"], summ[arm][n]["params"]) for n in sizes})
    print("gap at 19:", round(gap19, 1))


if __name__ == "__main__":
    main()
