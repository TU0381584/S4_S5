#!/usr/bin/env python3
"""M94 analysis: distilled AXIOM trees (docs/PAPER5_M94_preregistration.md, commit 43e6204).

Reads every evaluation log with m66_verify's independent reader and judges each pre-registered criterion.
Usage: m94_analysis.py --out experiments/results/m94/analysis.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import holm, paired, prio, seeds_of  # noqa: E402
from m94_distil import TARGETS  # noqa: E402

rng = np.random.default_rng(0)


def ci(d):
    d = np.asarray(d, float)
    m = d[rng.integers(0, len(d), size=(10000, len(d)))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def comp(a, b, f):
    t = paired(a, b, f)
    t["ci"] = ci([f(a[s]) - f(b[s]) for s in sorted(set(a) & set(b))])
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = {"targets": {}, "flags": []}
    R, P = (lambda r: r["reward"]), (lambda r: 100 * prio(r))
    for t, (cell, n, topo, seeds, rcell) in TARGETS.items():
        fit = json.load(open(f"/home/kmanojp/oranslice_rig/experiments/results/m94/trees/{t}/fit.json"))
        dt = seeds_of(f"m94/{t}", "distilled_tree", seeds)
        ax = seeds_of(cell, "axiom2", seeds)
        tr = seeds_of(rcell, "rule_local", seeds)
        fam = {"vs AXIOM, reward": comp(dt, ax, R), "vs tuned rule, reward": comp(dt, tr, R),
               "vs AXIOM, priority SLA": comp(dt, ax, P), "vs tuned rule, priority SLA": comp(dt, tr, P)}
        h = holm({k: v["p"] for k, v in fam.items()})
        for k in fam:
            fam[k]["p_holm"] = h[k]
        d = fit["selected_depth"]
        fid = [fit["per_seed"][str(s)]["heldout_fidelity"] for s in seeds]
        emb = [fit["per_seed"][str(s)].get("splits_embb", []) for s in seeds]
        uq = [th for sp in emb for f_, th in sp[:1] if f_ == "urllc_queue"]           # root split of each eMBB tree
        uq_any = [s for s, sp in zip(seeds, emb) if any(f_ == "urllc_queue" for f_, _ in sp)]
        T = out["targets"][t] = {
            "n_seeds": len(seeds), "selected_depth": d, "cv_fidelity": fit["cv"], "heldout_fidelity_by_depth": fit["heldout"],
            "heldout_fidelity_selected": {"mean": float(np.mean(fid)), "min": float(np.min(fid)), "max": float(np.max(fid))},
            "means": {k: {"reward": float(np.mean([R(r) for r in v.values()])), "prio": float(np.mean([P(r) for r in v.values()])),
                          "n": len(v), "collapsed": int(sum(r["collapsed"] for r in v.values()))}
                      for k, v in (("distilled_tree", dt), ("AXIOM", ax), ("tuned rule", tr))},
            "tests": fam,
            "embb_trees": {"seeds_splitting_on_urllc_queue": len(uq_any), "root_urllc_thresholds": uq,
                           "median_root_urllc_threshold": float(np.median(uq)) if uq else None, "tuned_rule_threshold": 0.2,
                           "constant_embb_trees": sum(1 for s in seeds if fit["per_seed"][str(s)]["tree_embb"].startswith("constant"))},
            "example_trees": {k: fit["per_seed"][str(seeds[0])][f"tree_{k}"] for k in ("urllc", "embb", "mmtc")},
        }
        print(f"== {t}: depth {d}, held-out fidelity {T['heldout_fidelity_selected']['mean']:.3f} "
              f"[{T['heldout_fidelity_selected']['min']:.3f}, {T['heldout_fidelity_selected']['max']:.3f}]")
        if T["heldout_fidelity_selected"]["mean"] < 0.80:
            out["flags"].append(f"NOT-DISTILLABLE {t}")
        for k, v in T["means"].items():
            print(f"   {k:15s} n={v['n']} reward {v['reward']:.3f}  priority SLA {v['prio']:.2f}%  collapsed {v['collapsed']}")
        for k, v in fam.items():
            print(f"   distilled {k:28s} {v['diff']:+.3f} [{v['ci'][0]:.3f}, {v['ci'][1]:.3f}] {v['wins']}/{v['ties']}/{v['losses']} "
                  f"p {v['p']:.2g} Holm {v['p_holm']:.2g}")
        e = T["embb_trees"]
        print(f"   eMBB trees: {e['seeds_splitting_on_urllc_queue']}/{len(seeds)} split on the URLLC queue, {e['constant_embb_trees']} constant; "
              f"root URLLC-queue thresholds median {e['median_root_urllc_threshold']} over {len(uq)} roots, against 0.2")
        if fam["vs AXIOM, reward"]["diff"] > 0 and fam["vs AXIOM, reward"]["p_holm"] < 0.05:
            out["flags"].append(f"D-S2 {t}: distilled tree beats AXIOM on reward")
    print("flags:", out["flags"] or "none")
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
