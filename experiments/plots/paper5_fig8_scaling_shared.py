"""Scaling figure for the shared-budget rerun (replaces paper5_fig8_m6_topology.py).

Reads experiments/results/m62_scaling/n{7,19}_{topology}/{arm}/seed{N}/eval
logs (primary seeds 900-911 plus replication seeds 1000-1002, pooled), and
draws (a) collapse rate per arm at N=7 and N=19, pooled over topologies,
with collapsed/total cell counts, and (b) priority-slice SLA compliance
(mean of URLLC and eMBB) per topology at N=19, per-seed points behind the
mean with a 95% bootstrap CI. Also writes a JSON summary of every number
plotted, so the manuscript text can quote the figure exactly.
"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/plots")
from m62_analysis import boot_ci, eval_log, seed_metrics  # noqa: E402
from paper5_common import M2_ARM_STYLE  # noqa: E402

ARMS = ["single_agent_dqn", "gat_ctde", "independent_dqn"]
TOPOLOGIES = ["fully_connected", "ring", "hex"]
TOPO_LABEL = {"fully_connected": "Fully-\nconnected", "ring": "Ring", "hex": "Hex"}
SEEDS = list(range(900, 912)) + [1000, 1001, 1002]


def collect(root: str, n: int, arms=None, seeds=None) -> dict:
    out = {}
    for topo in TOPOLOGIES:
        for arm in (arms or ARMS):
            rows = {}
            for s in (seeds or SEEDS):
                p = eval_log(f"{root}/n{n}_{topo}", arm, s)
                if p:
                    rows[s] = seed_metrics(p)
            out[(topo, arm)] = rows
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="experiments/results/m62_scaling")
    ap.add_argument("--out", default="Papers_4-5/Paper_5/WPC/figures/fig6_m6_topology")
    ap.add_argument("--arms", nargs="+", default=ARMS)
    ap.add_argument("--seeds7", type=int, nargs="+", default=SEEDS)
    ap.add_argument("--seeds19", type=int, nargs="+", default=SEEDS)
    a = ap.parse_args()
    ARMS[:] = a.arms
    data = {7: collect(a.root, 7, a.arms, a.seeds7), 19: collect(a.root, 19, a.arms, a.seeds19)}

    summary = {}
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.16, 2.9))
    x = np.arange(len(ARMS)); w = 0.36
    for j, (n, col) in enumerate([(7, "#c3c2b7"), (19, "#5b5a52")]):
        rates, labels = [], []
        for arm in ARMS:
            cells = [r for t in TOPOLOGIES for r in data[n][(t, arm)].values()]
            c = sum(r["collapsed"] for r in cells)
            rates.append(c / len(cells) if cells else np.nan)
            labels.append(f"{c}/{len(cells)}" if cells else "")
            summary.setdefault(f"n{n}", {})[arm] = {
                "cells": len(cells), "collapsed": c,
                "precision_mean": float(np.mean([r["precision"] for r in cells if r["precision"] is not None]))
                if any(r["precision"] is not None for r in cells) else None,
                "reward_mean": float(np.mean([r["reward"] for r in cells])) if cells else None,
                "sla": {k: float(np.mean([r["sla"][k] for r in cells])) for k in ("urllc", "embb", "mmtc")} if cells else {},
            }
        bars = ax1.bar(x + (j - 0.5) * w, rates, w, color=col, label=f"N = {n}")
        for b, lab in zip(bars, labels):
            ax1.text(b.get_x() + b.get_width() / 2, (b.get_height() if np.isfinite(b.get_height()) else 0) + 0.02,
                     lab, ha="center", va="bottom", fontsize=6.5)
    ax1.set_xticks(x)
    ax1.set_xticklabels([M2_ARM_STYLE[a_]["label"].replace(" (proposed)", "") for a_ in ARMS], fontsize=7)
    ax1.set_ylim(0, 1.15)
    ax1.set_ylabel("Collapse rate\n(fraction of cells, 0 blocks)")
    ax1.set_title("(a)", loc="left")
    ax1.legend(loc="upper right", frameon=False, fontsize=7)

    xc = np.arange(len(TOPOLOGIES))
    width = 0.6 / max(1, len(ARMS) - 1)
    offs = {arm: -0.3 + i * width for i, arm in enumerate(ARMS)}
    rng = np.random.RandomState(0)
    for arm in ARMS:
        st = M2_ARM_STYLE[arm]
        for xi, topo in zip(xc, TOPOLOGIES):
            vals = [0.5 * (r["sla"]["urllc"] + r["sla"]["embb"]) for r in data[19][(topo, arm)].values()]
            if not vals:
                continue
            ax2.scatter(xi + offs[arm] + rng.uniform(-0.05, 0.05, len(vals)), vals, s=9, color=st["color"],
                        alpha=0.35, linewidth=0)
            lo, hi = boot_ci(vals) if len(vals) > 1 else (vals[0], vals[0])
            m = float(np.mean(vals))
            ax2.errorbar(xi + offs[arm], m, yerr=[[m - lo], [hi - m]], fmt=st["marker"], color=st["color"],
                         markersize=6, capsize=3, linewidth=1.2,
                         label=st["label"].replace(" (proposed)", "") if topo == TOPOLOGIES[0] else None)
            summary.setdefault("n19_priority_sla_by_topology", {}).setdefault(arm, {})[topo] = {
                "mean": m, "ci": [lo, hi], "n": len(vals)}
    ax2.set_xticks(xc)
    ax2.set_xticklabels([TOPO_LABEL[t] for t in TOPOLOGIES])
    ax2.set_ylim(-0.03, 1.05)
    ax2.set_ylabel("URLLC and eMBB SLA\ncompliance, N = 19")
    ax2.set_title("(b)", loc="left")
    ax2.legend(loc="lower left", bbox_to_anchor=(0.01, 0.02), frameon=False, fontsize=6.2, ncol=3, columnspacing=0.6, handlelength=1.0, handletextpad=0.3)
    fig.tight_layout()

    out = Path(a.out)
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(out.with_suffix(".png"), dpi=200, bbox_inches="tight")
    json.dump(summary, open(f"{a.root}/scaling_summary.json", "w"), indent=2)
    print(json.dumps(summary["n7"], indent=1)[:1500])
    print(json.dumps(summary["n19"], indent=1)[:1500])


if __name__ == "__main__":
    main()
