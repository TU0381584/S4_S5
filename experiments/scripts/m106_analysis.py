#!/usr/bin/env python3
"""M106 analysis (docs/PAPER5_M106_preregistration.md), committed with the pre-registration, before any M106 run.
--jobs <path> writes the job list and exits. Run from framework/:
  ../venv/bin/python ../experiments/scripts/m106_analysis.py --out ../experiments/results/m106/analysis.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import ROOT, holm, paired, prio, read  # noqa: E402

CELLS = {"B_n7_ring": ("--n 7 --topology ring", list(range(10010, 10030))),
         "A_n3": ("--env A --n 3", list(range(10010, 10040)))}            # longest first
ARMS = ("axiom2", "single_agent_dqn", "independent_dqn")
BASE = ("single_agent_dqn", "independent_dqn")
MEAS = {"reward": lambda r: r["reward"], "compliance": lambda r: 100 * prio(r)}
SUBS = ("omega_log.jsonl", "dqn/offline_eval/rep_0/omega_log.jsonl", "lb_only/offline_eval/rep_0/omega_log.jsonl")
POOL = {"A_n3": ("m67_dev/V1/A3_base", list(range(7000, 7020))), "B_n7_ring": ("m105/B_n7_ring", list(range(10000, 10010)))}


def rows(root, arm, seeds, which):
    out = {}
    for s in seeds:
        base = f"{ROOT}/{root}/{arm}/seed{s}/{which}"
        for sub in SUBS:
            p = next((q for q in (f"{base}/{sub}", f"{base}/{sub}.gz") if os.path.exists(q)), None)
            if p:
                out[s] = read(p)
                break
    return out


def ci(d, seed=0):
    d = np.asarray(d, float)
    m = d[np.random.default_rng(seed).integers(0, len(d), size=(10000, len(d)))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def test(A, B, f):
    x = paired(A, B, f)
    d = [f(A[k]) - f(B[k]) for k in sorted(set(A) & set(B))]
    x["ci"], x["median"] = (ci(d), float(np.median(d))) if d else ([0.0, 0.0], 0.0)
    return x


def family(which):
    t = {}
    for c, (_, seeds) in CELLS.items():
        A = rows(f"m106/{c}", "axiom2", seeds, which)
        for b in BASE:
            B = rows(f"m106/{c}", b, seeds, which)
            for m, f in MEAS.items():
                t[f"{c}|{b}|{m}"] = test(A, B, f)
    h = holm({k: v["p"] for k, v in t.items()})
    for k, v in t.items():
        v["p_holm"] = h[k]
        v["verdict"] = ("AXIOM ahead" if v["diff"] > 0 else "baseline ahead") if h[k] < 0.05 else "within chance"
    return t


def pooled():
    out = {}
    for c, (_, seeds) in CELLS.items():
        root, ps = POOL[c]
        A = {**{("new", s): r for s, r in rows(f"m106/{c}", "axiom2", seeds, "eval").items()},
             **{("old", s): r for s, r in rows(root, "axiom2", ps, "eval").items()}}
        for b in BASE:
            B = {**{("new", s): r for s, r in rows(f"m106/{c}", b, seeds, "eval").items()},
                 **{("old", s): r for s, r in rows(root, b, ps, "eval").items()}}
            for m, f in MEAS.items():
                out[f"{c}|{b}|{m}"] = test(A, B, f)
    return out


def jobs(path):
    env = "M63_BACKLOG_RESET=1 M64_AXIOM_V2=1 M102_VARIANT=gat"
    with open(path, "w") as fh:
        for c, (args, seeds) in CELLS.items():
            for arm in ARMS:
                for s in seeds:
                    fh.write(f"{c}_{arm}_{s}|{env}|../experiments/scripts/m104_run.py --arm {arm} {args} --seeds {s} "
                             f"--out-dir ../experiments/results/m106/{c}\n")
    print("wrote", path)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out"); ap.add_argument("--jobs"); a = ap.parse_args()
    if a.jobs:
        return jobs(a.jobs)
    S, L = family("eval"), family("eval_last")
    gain = {}
    for c, (_, seeds) in CELLS.items():
        gain[c] = {}
        for arm in ARMS:
            Sr, Lr = rows(f"m106/{c}", arm, seeds, "eval"), rows(f"m106/{c}", arm, seeds, "eval_last")
            x = paired(Sr, Lr)
            x["collapsed_selected"] = int(sum(r["collapsed"] for r in Sr.values()))
            x["collapsed_last"] = int(sum(r["collapsed"] for r in Lr.values()))
            gain[c][arm] = x
    q1 = S["A_n3|single_agent_dqn|reward"]["verdict"]
    q2 = [S[f"B_n7_ring|independent_dqn|{m}"]["verdict"] for m in MEAS]
    out = {"S_selected": S, "L_last": L, "pooled_selected_descriptive": pooled(), "selected_minus_last": gain,
           "Q1_axiom_ahead_of_dqn_sa_at_A3_under_selection": q1 == "AXIOM ahead",
           "Q2_axiom_ahead_of_dqn_i_at_B7_ring_under_selection": all(v == "AXIOM ahead" for v in q2)}
    json.dump(out, open(a.out, "w"), indent=1, default=float)
    for name, t in (("S", S), ("L", L), ("pooled S", out["pooled_selected_descriptive"])):
        for k, v in t.items():
            print(f"{name:8s} {k:38s} n={v['n']} diff={v['diff']:+.3f} ci=[{v['ci'][0]:+.3f},{v['ci'][1]:+.3f}] p={v['p']:.3g} "
                  f"holm={v.get('p_holm', float('nan')):.3g} W/T/L={v['wins']}/{v['ties']}/{v['losses']} {v.get('verdict', '')}")
    for c, g in gain.items():
        print(c, {arm: (round(x["diff"], 3), f"{x['wins']}/{x['ties']}/{x['losses']}", x["collapsed_last"], x["collapsed_selected"])
                  for arm, x in g.items()})
    print("Q1:", out["Q1_axiom_ahead_of_dqn_sa_at_A3_under_selection"], " Q2:", out["Q2_axiom_ahead_of_dqn_i_at_B7_ring_under_selection"])


if __name__ == "__main__":
    main()
