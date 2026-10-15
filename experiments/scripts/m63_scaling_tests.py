#!/usr/bin/env python3
"""Paired per-layout scaling tests: AXIOM (gat_ctde) against each baseline,
on cluster reward and on priority-slice SLA (mean of URLLC and eMBB
compliance), Wilcoxon with Holm correction over the 12 tests at each size.
Also reports collapse counts and the pooled N=19 priority-slice SLA.

Usage: m63_scaling_tests.py --root experiments/results/m63_scaling --out <json>
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).resolve().parent))
from m62_analysis import boot_ci, eval_log, holm, seed_metrics  # noqa: E402

ARMS = ["gat_ctde", "single_agent_dqn", "independent_dqn"]
TOPOS = ["fully_connected", "ring", "hex"]
SEEDS = list(range(900, 912)) + [1000, 1001, 1002]


def prio(r):
    return 0.5 * (r["sla"]["urllc"] + r["sla"]["embb"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = {}
    for n in (7, 19):
        data = {(t, arm): {s: seed_metrics(p) for s in SEEDS if (p := eval_log(f"{a.root}/n{n}_{t}", arm, s))}
                for t in TOPOS for arm in ARMS}
        pv, rows = {}, {}
        for t in TOPOS:
            g = data[(t, "gat_ctde")]
            for b in ARMS[1:]:
                c = sorted(set(g) & set(data[(t, b)]))
                if len(c) < 5:
                    continue
                for metric, f in (("sla", prio), ("rew", lambda r: r["reward"])):
                    d = np.array([f(g[s]) - f(data[(t, b)][s]) for s in c])
                    key = f"{t}|{b}|{metric}"
                    pv[key] = float(wilcoxon(d).pvalue) if np.any(d != 0) else 1.0
                    rows[key] = {"n": len(c), "axiom": float(np.mean([f(g[s]) for s in c])),
                                 "base": float(np.mean([f(data[(t, b)][s]) for s in c])),
                                 "diff": float(d.mean()), "ci": boot_ci(d),
                                 "wtl": [int((d > 0).sum()), int((d == 0).sum()), int((d < 0).sum())]}
        h = holm(pv)
        for k in rows:
            rows[k]["p"], rows[k]["p_holm"] = pv[k], h[k]
            r = rows[k]
            print(f"N={n} {k:36s} axiom={r['axiom']:.3f} base={r['base']:.3f} diff={r['diff']:+.3f} "
                  f"[{r['ci'][0]:+.3f},{r['ci'][1]:+.3f}] W/T/L={r['wtl']} p_holm={r['p_holm']:.3g}")
        coll = {arm: [sum(r["collapsed"] for t in TOPOS for r in data[(t, arm)].values()),
                      sum(len(data[(t, arm)]) for t in TOPOS)] for arm in ARMS}
        slices = {arm: {k: float(np.mean([r["sla"][k] for t in TOPOS for r in data[(t, arm)].values()]))
                        for k in ("urllc", "embb")} for arm in ARMS}
        pooled = {arm: (lambda v: {"mean": float(np.mean(v)), "ci": boot_ci(v)})(
            [prio(r) for t in TOPOS for r in data[(t, arm)].values()]) for arm in ARMS}
        collapsed_seeds = {f"{t}|{arm}": [s for s, r in data[(t, arm)].items() if r["collapsed"]]
                           for t in TOPOS for arm in ARMS}
        print(f"N={n} collapse {coll}\nN={n} slices {slices}\nN={n} pooled prio {pooled}")
        out[n] = {"tests": rows, "collapse": coll, "slices": slices, "pooled_priority_sla": pooled,
                  "collapsed_seeds": collapsed_seeds}
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
