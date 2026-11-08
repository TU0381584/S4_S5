#!/usr/bin/env python3
"""Main Fig. 7: Env B reward per step at three gNBs, 30 seeds, the four learned policies and the two tuned rules.

Per-seed points (solid tints, so the EPS needs no transparency) behind the mean and its 95% CI. CIs are the paper's
order-independent bootstrap (m62_analysis.boot_ci), the same intervals Table 5 prints. Learned policies are filled
markers, rules hollow (figures/axiom_style.py, after Fig. 8); a dashed line marks the tuned local rule's mean.
Drawn at 84 mm. Every plotted number is written to <out>_summary.json.

Usage: paper5_fig_envB.py --root experiments/results/m64 --out Papers_4-5/Paper_5/WPC/figures/fig11_envB
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures")
from m62_analysis import boot_ci, eval_log, seed_metrics  # noqa: E402
import axiom_style as S  # noqa: E402

S.setup()
ARMS = ["axiom2", "mappo_tuned", "single_agent_dqn", "independent_dqn", "rule_local", "rule_neighbour"]
LABEL = {"axiom2": "AXIOM", "mappo_tuned": "MAPPO", "single_agent_dqn": "DQN-SA", "independent_dqn": "DQN-I",
         "rule_local": "Tuned local rule", "rule_neighbour": "Tuned neighbour rule"}
X = {a: x for a, x in zip(ARMS, (0, 1, 2, 3, 4.5, 5.5))}


def load(cell, arms, seeds):
    return {a: [seed_metrics(p) for s in seeds if (p := eval_log(cell, a, s))] for a in arms}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d3 = load(f"{a.root}/n3_fully_connected", ARMS, list(range(900, 930)))
    fig = S.figure("col", 52)
    ax = fig.add_axes([0.33, 0.19, 0.64, 0.78])
    rng = np.random.default_rng(0)
    summ = {"n3": {}}
    lab_x = []
    for arm in ARMS:
        rows = d3[arm]
        r = np.array([x["reward"] for x in rows])
        lo, hi = boot_ci(list(r)); m = float(r.mean())
        col = S.POLICY[arm]["color"]
        y = X[arm]
        ax.scatter(r, y + rng.uniform(-0.2, 0.2, len(r)), s=3, c=[S.lighten(col, 0.6)], lw=0, zorder=2)
        ax.plot([lo, hi], [y, y], color=col, lw=1.0, zorder=3)
        ax.plot([m], [y], zorder=4, **S.marker_kw(arm, 4.6))
        lab_x.append((y, m, col))
        summ["n3"][arm] = {"n": len(rows), "reward": m, "ci": [lo, hi],
                           "urllc": float(np.mean([x_["sla"]["urllc"] for x_ in rows])),
                           "embb": float(np.mean([x_["sla"]["embb"] for x_ in rows])),
                           "collapsed": int(sum(x_["collapsed"] for x_ in rows))}
    # pre-audit look restored: AXIOM's row highlighted and the Env B badge (2026-11-09)
    ax.axhspan(X["axiom2"] - 0.45, X["axiom2"] + 0.45, color=S.lighten(S.POLICY["axiom2"]["color"], 0.92), lw=0, zorder=0)
    S.env_badge(fig, 0.012, 0.975, "B", va="top")
    ref = summ["n3"]["rule_local"]["reward"]
    ax.axvline(ref, color=S.POLICY["rule_local"]["color"], lw=0.6, ls=(0, (3, 2)), zorder=1)
    ax.axhline(3.75, color=S.FAINT, lw=0.5, zorder=0)
    ax.set_yticks([X[a_] for a_ in ARMS]); ax.set_yticklabels([LABEL[a_].replace("\n", " ") for a_ in ARMS])
    for t, a_ in zip(ax.get_yticklabels(), ARMS):
        t.set_color(S.POLICY["axiom2"]["color"] if a_ == "axiom2" else S.INK)
    ax.set_ylim(5.95, -0.6)
    allr = [x_["reward"] for v_ in d3.values() for x_ in v_]
    x_hi = np.ceil(max(allr)) + 1.2
    ax.set_xlim(np.floor(min(allr)) - 0.2, x_hi)
    for y, m, col in lab_x:   # means in a column at the right, clear of the dots
        ax.text(x_hi - 0.05, y, f"{m:.2f}", va="center", ha="right", color=col)
    x_lo = np.floor(min(allr)) - 0.2
    ax.set_xticks([t_ for t_ in ax.get_xticks() if x_lo <= t_ <= np.ceil(max(allr))]); ax.set_xlim(x_lo, x_hi)
    ax.set_xlabel("Env B reward per step, three gNBs")
    ax.tick_params(axis="y", length=0); ax.spines["left"].set_visible(False)
    facts = S.save(fig, a.out)
    json.dump(summ, open(a.out + "_summary.json", "w"), indent=1)
    print(facts, {k: round(v["reward"], 3) for k, v in summ["n3"].items()})


if __name__ == "__main__":
    main()
