#!/usr/bin/env python3
"""M100 analysis (docs/PAPER5_M100_preregistration.md), written after that commit and before any M100 result was read.
Run from framework/: ../venv/bin/python ../experiments/scripts/m100_analysis.py --out ../experiments/results/m100/analysis.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import holm, paired, prio, seeds_of  # noqa: E402
sys.path.insert(0, "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures")
from axiom_style import wilson  # noqa: E402

SEEDS = list(range(8000, 8020))
R = lambda r: r["reward"]
P = lambda r: 100 * prio(r)


def ci(d, seed=0):
    d = np.asarray(d, float)
    m = d[np.random.default_rng(seed).integers(0, len(d), size=(10000, len(d)))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def comp(a, b, f):
    t = paired(a, b, f)
    common = sorted(set(a) & set(b))
    d = [f(a[s]) - f(b[s]) for s in common]
    t["ci"] = ci(d); t["median"] = float(np.median(d))
    return t


def fam(a, b):
    t = {"compliance": comp(a, b, P), "reward": comp(a, b, R)}
    h = holm({k: v["p"] for k, v in t.items()})
    for k in t:
        t[k]["p_holm"] = h[k]
    return t


def arm_summary(rows):
    k = int(sum(r["collapsed"] for r in rows.values()))
    return {"n": len(rows), "collapsed": k, "wilson_pct": [100 * x for x in wilson(k, len(rows))],
            "prio_mean": float(np.mean([P(r) for r in rows.values()])), "reward_mean": float(np.mean([R(r) for r in rows.values()]))}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    ax = seeds_of("m96/A_fresh/n37_hex", "axiom2", SEEDS)
    mlp = seeds_of("m100/A_n37_hex", "axiom2_mlp", SEEDS)
    sh = seeds_of("m100/A_sharedhead_n37_hex", "axiom2", SEEDS)
    e1, e2 = fam(ax, sh), fam(mlp, ax)
    for k, v in e2.items():
        v["verdict"] = ("MLP ahead" if v["diff"] > 0 else "AXIOM ahead") if v["p_holm"] < 0.05 else "within chance"
    out = {"E1_axiom_minus_sharedhead": e1, "E2_mlp_minus_axiom": e2,
           "arms": {"axiom2": arm_summary(ax), "axiom2_mlp": arm_summary(mlp), "sharedhead": arm_summary(sh)}}
    out["criteria"] = [
        {"id": "E1", "criterion": "AXIOM ahead of the shared-head variant on compliance and reward, Env A 37 gNBs hex, 20 seeds, Holm",
         "n": min(v["n"] for v in e1.values()), "verdict": "HOLDS" if all(v["diff"] > 0 and v["p_holm"] < 0.05 for v in e1.values()) else "FAILS"},
        {"id": "E2", "criterion": "MLP variant against AXIOM, Env A 37 gNBs hex, 20 seeds, Holm (reported per test)",
         "n": min(v["n"] for v in e2.values()), "verdict": "; ".join(f"{k} {v['verdict']}" for k, v in e2.items())}]
    json.dump(out, open(a.out, "w"), indent=1, default=float)
    for c in out["criteria"]:
        print(f"{c['id']} n={c['n']} {c['verdict']} | {c['criterion']}")


if __name__ == "__main__":
    main()
