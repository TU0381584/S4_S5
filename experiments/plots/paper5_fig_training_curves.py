#!/usr/bin/env python3
"""Training curves: mean step reward per training episode, mean over seeds
with a 95% bootstrap band, one panel per campaign cell.

Reads each seed's training log (omega_log.jsonl or .gz; the single-agent
DQN's sits under dqn/offline_train/rep_0) or, for MAPPO, train/curve.json.
A centred moving average of SMOOTH episodes is applied after averaging.

Usage:
  paper5_fig_training_curves.py --cell experiments/results/m64/n3_fully_connected "(a) Env B, 3 gNBs" \
      --cell experiments/results/m64/n7_ring "(b) Env B, 7 gNBs, ring" --seeds 900 ... --out <fig path>
"""
import argparse
import glob
import gzip
import json
import os
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paper5_common import M2_ARM_STYLE, SUPP_WIDTH_IN, panel  # noqa: E402

ARMS = [("axiom2", "AXIOM", "#2a78d6", "-"), ("single_agent_dqn", "DQN-SA", "#1baf7a", "--"),
        ("independent_dqn", "DQN-I", "#eb6834", "-."), ("mappo_tuned", "MAPPO", "#7a4fd0", ":")]
SMOOTH = 10


def seed_curve(cell, arm, seed):
    base = f"{cell}/{arm}/seed{seed}/train"
    cj = f"{base}/curve.json"
    if os.path.exists(cj):
        return np.array(json.load(open(cj))["episode_mean_reward"])
    cands = glob.glob(f"{base}/omega_log.jsonl*") + glob.glob(f"{base}/dqn/offline_train/rep_0/omega_log.jsonl*")
    if not cands:
        return None
    path = cands[0]
    op = gzip.open if path.endswith(".gz") else open
    ep = defaultdict(list)
    for line in op(path, "rt"):
        r = json.loads(line)
        ev = r.get("evidence", {})
        if isinstance(ev, dict) and "reward" in ev and not ev.get("rollup"):
            ep[r["episode"]].append(ev["reward"])
    return np.array([np.mean(ep[e]) for e in sorted(ep)]) if ep else None


def smooth(x, k):
    if k <= 1:
        return x
    pad = np.pad(x, (k // 2, k - 1 - k // 2), mode="edge")
    return np.convolve(pad, np.ones(k) / k, mode="valid")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", nargs=2, action="append", metavar=("DIR", "TITLE"), required=True)
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    fig, axes = plt.subplots(1, len(a.cell), figsize=(SUPP_WIDTH_IN, 2.35), squeeze=False)
    summary = {}
    rng = np.random.RandomState(0)
    for ax, (cell, title) in zip(axes[0], a.cell):
        for arm, label, col, ls in ARMS:
            curves = [c for s in a.seeds if (c := seed_curve(cell, arm, s)) is not None]
            if not curves:
                continue
            L = min(len(c) for c in curves)
            M = np.stack([c[:L] for c in curves])
            mean = M.mean(0)
            boots = np.stack([M[rng.randint(0, len(M), len(M))].mean(0) for _ in range(500)])
            lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
            x = np.arange(1, L + 1)
            ax.plot(x, smooth(mean, SMOOTH), color=col, ls=ls, lw=1.1, label=label)
            ax.fill_between(x, smooth(lo, SMOOTH), smooth(hi, SMOOTH), color=col, alpha=0.15, lw=0)
            summary.setdefault(cell, {})[arm] = {"n": len(M), "last20_mean": float(mean[-20:].mean()),
                                                 "first20_mean": float(mean[:20].mean())}
        panel(ax, title.split(")")[0].strip("( "))
        ax.set_xlabel("Training episode")
        ax.grid(True, lw=0.4, alpha=0.4)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0][0].set_ylabel("Mean reward per step")
    h_, l_ = axes[0][0].get_legend_handles_labels()
    fig.legend(h_, l_, loc="lower center", ncol=len(l_), fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(a.out + ".pdf", bbox_inches="tight")
    fig.savefig(a.out + ".png", dpi=200, bbox_inches="tight")
    json.dump(summary, open(a.out + "_summary.json", "w"), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
