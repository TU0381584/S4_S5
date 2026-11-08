#!/usr/bin/env python3
"""AXIOM's advantage as the Env A cluster grows from 3 to 7 to 19 gNBs, and to 37 with --with-37.

(a) Priority-slice compliance, the mean of URLLC and eMBB SLA compliance, per learned policy and the static rule:
    one dot per run, the mean and its 95% bootstrap CI over all seeds and layouts.
(b) Share of trained policies that collapse into accepting every request, with Wilson 95% intervals.
(c) Reward per gNB per step, mean and 95% bootstrap CI over the same runs (moved here from the
    retired AXIOM-superiority figure, panel a, in the figure audit).

Data: three gNBs from the 30-seed Env A campaign (m65_n3_view, fully-connected);
seven gNBs from 15 seeds under each of three layouts (45 cells); nineteen gNBs
from 30 seeds under each of three layouts (90 cells); thirty-seven gNBs (M73)
from AXIOM on 30 hex seeds and 15 ring and 15 fully-connected seeds, and the
layout-independent baselines on the 30 hex seeds. The static rule is plotted in (a).
Drawn at 119 mm with figures/axiom_style.py. Every plotted number is
written to <out>_summary.json.

Usage: paper5_fig_scaling_trend.py --out Papers_4-5/Paper_5/WPC/figures/fig6_scaling_trend
"""
import argparse
import json
import sys

import numpy as np

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/plots")
from m62_analysis import boot_ci  # noqa: E402
from m66_verify import ROOT, S15, S30, S30_19, prio, seeds_of  # noqa: E402
sys.path.insert(0, "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures")
import axiom_style as S  # noqa: E402
S.setup()

ARMS = ["axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned"]
LABEL = {"axiom2": "AXIOM (proposed)", "single_agent_dqn": "DQN-SA",
         "independent_dqn": "DQN-I", "mappo_tuned": "MAPPO"}
COMPLEXITY_KEY = {"axiom2": "axiom2", "single_agent_dqn": "single_agent_dqn",
                  "independent_dqn": "independent_dqn", "mappo_tuned": "mappo"}
LAYOUTS = ("fully_connected", "ring", "hex")


def rule_cells(n):
    if n == 37:
        return list(seeds_of("m73/A_n37_hex", "rule_static", S30_19).values())
    if n == 3:
        return list(seeds_of("m65_n3_view", "heuristic", S30).values())
    seeds = S15 if n == 7 else S30_19
    return [r for t in LAYOUTS for r in seeds_of(f"m70/R1/A_n{n}_{t}", "rule_static", seeds).values()]


def cells(n, arm):
    if n == 37:
        if arm != "axiom2":
            return list(seeds_of("m73/A_n37_hex", arm, S30_19).values())
        return [r for t, ss in (("hex", S30_19), ("ring", S15), ("fully_connected", S15))
                for r in seeds_of(f"m73/A_n37_{t}", arm, ss).values()]
    if n == 3:
        return list(seeds_of("m65_n3_view", arm, S30).values())
    seeds = S15 if n == 7 else S30_19
    return [r for t in LAYOUTS for r in seeds_of(f"m65_scaling/n{n}_{t}", arm, seeds).values()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--with-37", action="store_true")
    a = ap.parse_args()
    comp = json.load(open(f"{ROOT}/m64/complexity.json"))
    sizes = [3, 7, 19]
    if a.with_37:
        comp.update(json.load(open(f"{ROOT}/m73/complexity_n37.json")))
        sizes.append(37)
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
            rg = [r["reward"] / n for r in rows]
            summ[arm][n]["reward_per_gnb_mean"] = float(np.mean(rg)); summ[arm][n]["reward_per_gnb_ci"] = list(boot_ci(rg))
    summ["rule"] = {}
    for n in sizes:
        rows = rule_cells(n)
        v = [100 * prio(r) for r in rows]
        summ["rule"][n] = {"n_cells": len(rows), "prio_mean": float(np.mean(v)), "prio_ci": list(boot_ci(v)),
                           "collapsed": int(sum(r["collapsed"] for r in rows))}
    big = sizes[-1]
    gap19 = summ["axiom2"][19]["prio_mean"] - max(summ[b][19]["prio_mean"] for b in ARMS[1:])
    gap = summ["axiom2"][big]["prio_mean"] - max(summ[b][big]["prio_mean"] for b in ARMS[1:])
    for arm in ARMS:   # Wilson 95% interval of the collapsed share, for panel b
        for n in sizes:
            k_, n_ = summ[arm][n]["collapsed"], summ[arm][n]["n_cells"]
            summ[arm][n]["collapsed_wilson"] = [100 * x for x in S.wilson(k_, n_)]
    fig = S.figure("full", 104)
    fw, fh = (lambda mm: mm / 119.0), (lambda mm: mm / 104.0)
    axa = fig.add_axes([fw(15), fh(58), fw(101), fh(37)])
    axb = fig.add_axes([fw(15), fh(10), fw(42), fh(30)])
    axc = fig.add_axes([fw(74), fh(10), fw(42), fh(30)])
    order = ["axiom2", "mappo_tuned", "single_agent_dqn", "independent_dqn"]
    dx = {"axiom2": -0.24, "mappo_tuned": -0.08, "single_agent_dqn": 0.08, "independent_dqn": 0.24, "rule": 0.38}
    xs = {n: i for i, n in enumerate(sizes)}
    rng = np.random.default_rng(0)
    # a, compliance: seeds, mean, CI, and the static rule
    for arm in order + ["rule"]:
        pol = "rule_static" if arm == "rule" else arm
        col = S.POLICY[pol]["color"]
        for n in sizes:
            rows = rule_cells(n) if arm == "rule" else cells(n, arm)
            v = [100 * prio(r) for r in rows]
            x = xs[n] + dx[arm]
            axa.scatter(x + rng.uniform(-0.035, 0.035, len(v)), v, s=1.2, c=[S.lighten(col, 0.6)], lw=0, zorder=2)
            m, (lo, hi) = summ[arm][n]["prio_mean"], summ[arm][n]["prio_ci"]
            axa.plot([x, x], [lo, hi], color=col, lw=0.9, zorder=3)
            axa.plot([x], [m], zorder=4, **S.marker_kw(pol, 3.6))
    i37 = xs[big]
    axa.text(i37 + dx["axiom2"] - 0.07, summ["axiom2"][big]["prio_mean"], f"{summ['axiom2'][big]['prio_mean']:.1f}%", ha="right", va="center",
             color=S.POLICY["axiom2"]["color"])
    yb = max(summ[b][big]["prio_mean"] for b in ARMS[1:])
    xg = i37 + 0.52
    axa.annotate("", xy=(xg, summ["axiom2"][big]["prio_mean"]), xytext=(xg, yb), arrowprops=dict(arrowstyle="<->", color=S.POLICY["axiom2"]["color"], lw=0.8))
    axa.text(xg + 0.05, (summ["axiom2"][big]["prio_mean"] + yb) / 2, f"+{gap:.1f} pp", va="center", ha="left", color=S.POLICY["axiom2"]["color"])
    axa.set_xlim(-0.5, len(sizes) - 0.5 + 0.55); axa.set_ylim(0, 104)
    axa.set_xticks(range(len(sizes))); axa.set_xticklabels([str(n) for n in sizes]); axa.set_xlabel("gNBs")
    axa.set_ylabel("Priority-slice\ncompliance (%)")
    # b, collapsed share with Wilson CIs
    for arm in order:
        col = S.POLICY[arm]["color"]
        for n in sizes:
            x = xs[n] + dx[arm]; k_, n_ = summ[arm][n]["collapsed"], summ[arm][n]["n_cells"]
            lo, hi = summ[arm][n]["collapsed_wilson"]
            axb.plot([x, x], [lo, hi], color=col, lw=0.9, zorder=3)
            axb.plot([x], [100 * k_ / n_], zorder=4, **S.marker_kw(arm, 3.6))
    axb.set_xlim(-0.5, len(sizes) - 0.5); axb.set_ylim(-3, 103)
    axb.set_xticks(range(len(sizes))); axb.set_xticklabels([str(n) for n in sizes]); axb.set_xlabel("gNBs")
    axb.set_ylabel("Collapsed runs (%)")
    # c, reward per gNB per step
    for arm in order:
        col = S.POLICY[arm]["color"]
        for n in sizes:
            x = xs[n] + dx[arm]
            m, (lo, hi) = summ[arm][n]["reward_per_gnb_mean"], summ[arm][n]["reward_per_gnb_ci"]
            axc.plot([x, x], [lo, hi], color=col, lw=0.9, zorder=3)
            axc.plot([x], [m], zorder=4, **S.marker_kw(arm, 3.6))
    axc.set_xlim(-0.5, len(sizes) - 0.5)
    axc.set_xticks(range(len(sizes))); axc.set_xticklabels([str(n) for n in sizes]); axc.set_xlabel("gNBs")
    axc.set_ylabel("Reward per gNB\nper step")
    for ax_, t_ in ((axa, "a"), (axb, "b"), (axc, "c")):
        ax_.text(-0.13 if ax_ is not axa else -0.07, 1.02, t_, transform=ax_.transAxes, fontweight="bold", va="bottom", ha="left")
    from matplotlib.lines import Line2D
    hs = [Line2D([], [], label=S.POLICY[a_]["label"], **S.marker_kw(a_, 3.6)) for a_ in order + ["rule_static"]]
    fig.legend(handles=hs, loc="upper center", ncol=5, bbox_to_anchor=(0.55, 1.0), handletextpad=0.2, columnspacing=1.0)
    facts = S.save(fig, a.out)
    print(facts)
    json.dump({"gap19_points": gap19, f"gap{big}_points": gap, "arms": summ}, open(a.out + "_summary.json", "w"), indent=1)
    print("rule", {n: (round(summ["rule"][n]["prio_mean"], 2), summ["rule"][n]["collapsed"], summ["rule"][n]["n_cells"]) for n in sizes})
    for arm in ARMS:
        print(arm, {n: (round(summ[arm][n]["prio_mean"], 1), summ[arm][n]["collapsed"], summ[arm][n]["n_cells"], summ[arm][n]["params"]) for n in sizes})
    print("gap at 19:", round(gap19, 1), f"gap at {big}:", round(gap, 1))


if __name__ == "__main__":
    main()
