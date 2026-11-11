#!/usr/bin/env python3
"""M105 analysis (docs/PAPER5_M105_preregistration.md), committed with the pre-registration, before any M105 run.
Selected-checkpoint evaluations are read from eval/ and last-checkpoint evaluations from eval_last/, both with
m66_verify's reader (gzip-aware). Also writes the job list: --jobs <path> writes it and exits.
Run from framework/: ../venv/bin/python ../experiments/scripts/m105_analysis.py --out ../experiments/results/m105/analysis.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import ROOT, holm, paired, prio, read  # noqa: E402

SEEDS = list(range(10000, 10010))
CELLS = {"A_n37_hex": "--env A --n 37 --topology hex", "A_n19_hex": "--env A --n 19 --topology hex",
         "B_n19_hex": "--n 19 --topology hex", "A_n7_hex": "--env A --n 7 --topology hex",
         "B_n7_ring": "--n 7 --topology ring"}           # longest first
ARMS = ("axiom2", "single_agent_dqn", "independent_dqn")
BASE = ("single_agent_dqn", "independent_dqn")
MEAS = {"reward": lambda r: r["reward"], "compliance": lambda r: 100 * prio(r)}
SUBS = ("omega_log.jsonl", "dqn/offline_eval/rep_0/omega_log.jsonl", "lb_only/offline_eval/rep_0/omega_log.jsonl")


def find(cell, arm, seed, which):
    base = f"{ROOT}/m105/{cell}/{arm}/seed{seed}/{which}"
    for sub in SUBS:
        for p in (f"{base}/{sub}", f"{base}/{sub}.gz"):
            if os.path.exists(p):
                return p
    return None


def rows(cell, arm, which):
    out = {}
    for s in SEEDS:
        p = find(cell, arm, s, which)
        if p:
            out[s] = read(p)
    return out


def ci(d, seed=0):
    d = np.asarray(d, float)
    m = d[np.random.default_rng(seed).integers(0, len(d), size=(10000, len(d)))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def family(which):
    t = {}
    for c in CELLS:
        A = rows(c, "axiom2", which)
        for b in BASE:
            B = rows(c, b, which)
            for m, f in MEAS.items():
                x = paired(A, B, f)
                d = [f(A[k]) - f(B[k]) for k in sorted(set(A) & set(B))]
                x["ci"], x["median"] = (ci(d), float(np.median(d))) if d else ([0.0, 0.0], 0.0)
                t[f"{c}|{b}|{m}"] = x
    h = holm({k: v["p"] for k, v in t.items()})
    for k, v in t.items():
        v["p_holm"] = h[k]
        v["verdict"] = ("AXIOM ahead" if v["diff"] > 0 else "baseline ahead") if h[k] < 0.05 else "within chance"
    return t


def jobs(path):
    env = "M63_BACKLOG_RESET=1 M64_AXIOM_V2=1 M102_VARIANT=gat"
    with open(path, "w") as f:
        for c, args in CELLS.items():
            for arm in ARMS:
                for s in SEEDS:
                    f.write(f"{c}_{arm}_{s}|{env}|../experiments/scripts/m104_run.py --arm {arm} {args} --seeds {s} "
                            f"--out-dir ../experiments/results/m105/{c}\n")
    print("wrote", path)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out"); ap.add_argument("--jobs"); a = ap.parse_args()
    if a.jobs:
        return jobs(a.jobs)
    L, S = family("eval_last"), family("eval")
    changes = {k: [L[k]["verdict"], S[k]["verdict"]] for k in L if L[k]["verdict"] != S[k]["verdict"]}
    erosion = {k: [L[k]["diff"], S[k]["diff"]] for k in L
               if L[k]["verdict"] == "AXIOM ahead" and S[k]["diff"] < 0.5 * L[k]["diff"]}
    gain = {}
    for c in CELLS:
        gain[c] = {}
        for arm in ARMS:
            Sr, Lr = rows(c, arm, "eval"), rows(c, arm, "eval_last")
            x = paired(Sr, Lr)
            x["collapsed_selected"] = int(sum(r["collapsed"] for r in Sr.values()))
            x["collapsed_last"] = int(sum(r["collapsed"] for r in Lr.values()))
            gain[c][arm] = x
    out = {"L_last": L, "S_selected": S, "verdict_changes": changes, "lead_erosion": erosion,
           "selected_minus_last": gain, "full_rerun_needed": bool(changes or erosion)}
    json.dump(out, open(a.out, "w"), indent=1, default=float)
    for name, t in (("L", L), ("S", S)):
        for k, v in t.items():
            print(f"{name} {k:42s} diff={v['diff']:+.3f} ci=[{v['ci'][0]:+.3f},{v['ci'][1]:+.3f}] holm={v['p_holm']:.3g} "
                  f"W/T/L={v['wins']}/{v['ties']}/{v['losses']} {v['verdict']}")
    for c, g in gain.items():
        print(c, {arm: (round(x["diff"], 3), f"{x['wins']}/{x['ties']}/{x['losses']}", x["collapsed_last"], x["collapsed_selected"])
                  for arm, x in g.items()})
    print("verdict changes:", changes)
    print("lead erosion:", erosion)
    print("full rerun needed:", out["full_rerun_needed"])


if __name__ == "__main__":
    main()
