#!/usr/bin/env python3
"""M103 analysis (docs/PAPER5_M102_preregistration.md), written after that commit and before any M102 or M103 result
was read. Reads the two variants selected by m102_select.py and compares them on fresh seeds 9980 to 9999.
Also writes the M103 job list: --jobs <path> writes it and exits.
Run from framework/: ../venv/bin/python ../experiments/scripts/m103_analysis.py --out ../experiments/results/m103/analysis.json
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

SEL = "/home/kmanojp/oranslice_rig/experiments/results/m102/selection.json"
SEEDS = list(range(9980, 10000))
SETTINGS = {"B_n7_ring": (7, "--n 7 --topology ring"), "B_n7_hex": (7, "--n 7 --topology hex"),
            "A_n37_hex": (37, "--env A --n 37 --topology hex")}
R = lambda r: r["reward"]
P = lambda r: 100 * prio(r)


def ci(d, seed=0):
    d = np.asarray(d, float)
    m = d[np.random.default_rng(seed).integers(0, len(d), size=(10000, len(d)))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def jobs(path):
    sel = json.load(open(SEL))["selected"]
    env = "M63_BACKLOG_RESET=1 M64_AXIOM_V2=1"
    with open(path, "w") as f:
        for s, (n, args) in sorted(SETTINGS.items(), key=lambda kv: -kv[1][0]):   # longest first
            for v in (sel["attention"], sel["mlp"]):
                for seed in SEEDS:
                    f.write(f"{s}_{v}_{seed}|{env} M102_VARIANT={v}|../experiments/scripts/m102_run.py --arm axiom2 {args} "
                            f"--seeds {seed} --out-dir ../experiments/results/m103/{s}/{v}\n")
    print("selected", sel, "->", path)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out"); ap.add_argument("--jobs"); a = ap.parse_args()
    if a.jobs:
        return jobs(a.jobs)
    sel = json.load(open(SEL))["selected"]
    att, mlp = sel["attention"], sel["mlp"]
    tests, arms = {}, {}
    for s, (n, _) in SETTINGS.items():
        A = seeds_of(f"m103/{s}/{att}", "axiom2", SEEDS)
        M = seeds_of(f"m103/{s}/{mlp}", "axiom2", SEEDS)
        for m, f in (("reward", R), ("compliance", P)):
            t = paired(A, M, f)
            d = [f(A[k]) - f(M[k]) for k in sorted(set(A) & set(M))]
            t["ci"], t["median"] = ci(d), float(np.median(d))
            tests[f"{s}|{m}"] = t
        arms[s] = {v: {"n": len(rows), "collapsed": int(sum(r["collapsed"] for r in rows.values())),
                       "wilson_pct": [100 * x for x in wilson(int(sum(r["collapsed"] for r in rows.values())), len(rows))],
                       "reward_mean": float(np.mean([R(r) for r in rows.values()])), "prio_mean": float(np.mean([P(r) for r in rows.values()]))}
                   for v, rows in ((att, A), (mlp, M))}
    h = holm({k: v["p"] for k, v in tests.items()})
    for k, v in tests.items():
        v["p_holm"] = h[k]
        v["verdict"] = ("attention ahead" if v["diff"] > 0 else "MLP ahead") if h[k] < 0.05 else "within chance"
    ahead_reward = any(v["verdict"] == "attention ahead" for k, v in tests.items() if k.endswith("|reward"))
    behind = any(v["verdict"] == "MLP ahead" for v in tests.values())
    out = {"selected": sel, "tests": tests, "arms": arms,
           "attention_beats_mlp": bool(ahead_reward and not behind),
           "reading": "attention beats the MLP only if ahead on reward in at least one setting and behind on neither measure in any setting"}
    json.dump(out, open(a.out, "w"), indent=1, default=float)
    for k, v in tests.items():
        print(f"{k:25s} diff={v['diff']:+.3f} ci=[{v['ci'][0]:+.3f},{v['ci'][1]:+.3f}] p={v['p']:.3g} holm={v['p_holm']:.3g} "
              f"W/T/L={v['wins']}/{v['ties']}/{v['losses']} {v['verdict']}")
    print("attention beats the MLP:", out["attention_beats_mlp"])


if __name__ == "__main__":
    main()
