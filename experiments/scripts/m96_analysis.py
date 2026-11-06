#!/usr/bin/env python3
"""M96 analysis (docs/PAPER5_M96_preregistration.md, commit 32de84d0). Reads every log with m66_verify's
independent reader and judges each pre-registered criterion as HOLDS or FAILS; nothing is dropped when it fails.

Usage: m96_analysis.py --out experiments/results/m96/analysis.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import holm, paired, prio, seeds_of  # noqa: E402

FRESH = list(range(8000, 8020))
S15 = list(range(900, 912)) + [1000, 1001, 1002]
rng = np.random.default_rng(0)


def ci(d):
    d = np.asarray(d, float)
    m = d[rng.integers(0, len(d), size=(10000, len(d)))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def comp(a, b, f):
    t = paired(a, b, f)
    t["ci"] = ci([f(a[s]) - f(b[s]) for s in sorted(set(a) & set(b))])
    return t


P = lambda r: 100 * prio(r)
R = lambda r: r["reward"]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    out, crit = {}, []

    def judge(name, ok, detail):
        crit.append({"criterion": name, "verdict": "HOLDS" if ok else "FAILS", "detail": detail})
        print(f"{'HOLDS' if ok else 'FAILS':6s} {name}: {detail}")

    # ---------------- M96a
    A = {}
    for n in (19, 37):
        A[n] = {"AXIOM from 7": seeds_of(f"m96/A_fresh/transfer_n{n}", "axiom2_transfer", FRESH),
                "MAPPO from 7": seeds_of(f"m96/A_fresh/transfer_n{n}", "mappo_tuned_transfer", FRESH),
                "AXIOM trained at N": seeds_of(f"m96/A_fresh/n{n}_hex", "axiom2", FRESH),
                "Static rule": seeds_of(f"m96/A_fresh/n{n}_hex", "rule_static", FRESH),
                "Accept all": seeds_of(f"m96/A_fresh/n{n}_hex", "rule_accept_all", FRESH)}
    out["A"] = {str(n): {k: {"n": len(v), "prio": float(np.mean([P(r) for r in v.values()])) if v else None,
                             "reward_per_gnb": float(np.mean([R(r) / n for r in v.values()])) if v else None,
                             "collapsed": int(sum(r["collapsed"] for r in v.values()))} for k, v in A[n].items()} for n in A}
    ra1 = {n: out["A"][str(n)]["AXIOM from 7"]["prio"] for n in (19, 37)}
    judge("R-A1 transferred AXIOM above 93% at 19 and 37 gNBs (fresh seeds)", all(v is not None and v > 93 for v in ra1.values()),
          {n: round(v, 2) for n, v in ra1.items()})
    fam = {}
    for n in (19, 37):
        fam[f"R-A2 vs accept-all at {n}"] = comp(A[n]["AXIOM from 7"], A[n]["Accept all"], P)
        fam[f"R-A3 vs MAPPO from 7 at {n}"] = comp(A[n]["AXIOM from 7"], A[n]["MAPPO from 7"], P)
    h = holm({k: v["p"] for k, v in fam.items()})
    for k, v in fam.items():
        v["p_holm"] = h[k]
        judge(k, v["diff"] > 0 and h[k] < 0.05, f"{v['diff']:+.2f} points [{v['ci'][0]:.2f}, {v['ci'][1]:.2f}], {v['wins']}/{v['ties']}/{v['losses']}, Holm p {h[k]:.2g}, n {v['n']}")
    out["A_family"] = fam
    out["A_descriptive"] = {}
    for n in (19, 37):
        for nm, f in (("prio", P), ("reward_per_gnb", lambda r, n=n: R(r) / n)):
            t = comp(A[n]["AXIOM from 7"], A[n]["AXIOM trained at N"], f)
            out["A_descriptive"][f"R-A4 transferred minus trained at {n}, {nm}"] = t
            print(f"REPORT R-A4 at {n} {nm}: {t['diff']:+.3f} [{t['ci'][0]:.3f}, {t['ci'][1]:.3f}] p {t['p']:.3g} n {t['n']}")

    # ---------------- M96b
    cells = {3: ("m96/B_shift/n3", list(range(905, 930)), "rule_local"), 7: ("m96/B_shift/n7_ring", S15, "rule_local"),
             19: ("m96/B_shift/n19_hex", S15, "rule_local_transfer")}
    loads = ("load_0.80", "nominal", "load_1.05", "load_1.10", "load_1.15", "load_1.20")
    base = ("mappo_tuned", "single_agent_dqn", "independent_dqn")
    out["B"] = {}
    for n, (c, ss, rule) in cells.items():
        res = {L: {arm: seeds_of(f"{c}/{L}", arm, ss) for arm in ("axiom2",) + base + (rule,)} for L in loads}
        tests, table = {}, {}
        for L in loads:
            table[L] = {arm: float(np.mean([R(r) for r in v.values()])) if v else None for arm, v in res[L].items()}
            for b in base:
                t = comp(res[L]["axiom2"], res[L][b], R)
                table[L][f"AXIOM minus {b}"] = t
                if L in ("load_1.10", "load_1.15", "load_1.20"):
                    tests[f"{L} {b}"] = t
            for b in base:
                table[L][f"{b} minus tuned rule"] = comp(res[L][b], res[L][rule], R)
            table[L]["AXIOM minus tuned rule"] = comp(res[L]["axiom2"], res[L][rule], R)
        hb = holm({k: v["p"] for k, v in tests.items()})
        ok = all(v["diff"] > 0 and hb[k] < 0.05 for k, v in tests.items()) and len(tests) == 9
        judge(f"R-B1 AXIOM out-earns every learned baseline at 110-120% load, {n} gNBs", ok,
              {k: (round(v["diff"], 3), round(hb[k], 4)) for k, v in tests.items()})
        out["B"][str(n)] = {"table": table, "holm": hb, "n_seeds": {L: {arm: len(v) for arm, v in res[L].items()} for L in loads}}

    # ---------------- M96c
    c = "m96/C_fresh_shift/n19_hex"; ss = list(range(7000, 7015))
    resc = {L: {arm: seeds_of(f"{c}/{L}", arm, ss) for arm in ("axiom2", "rule_local_transfer", "rule_static") + base}
            for L in ("nominal", "load_1.10", "load_1.15", "load_1.20")}
    tc = {L: comp(resc[L]["axiom2"], resc[L]["rule_local_transfer"], R) for L in ("load_1.10", "load_1.15", "load_1.20")}
    hc = holm({k: v["p"] for k, v in tc.items()})
    judge("R-C1 AXIOM beats the carried tuned rule at 110-120% load on fresh seeds 7000-7014",
          all(v["diff"] > 0 and hc[k] < 0.05 for k, v in tc.items()), {k: (round(v["diff"], 2), round(hc[k], 4), f"{v['wins']}/{v['ties']}/{v['losses']}") for k, v in tc.items()})
    nomc = comp(resc["nominal"]["axiom2"], resc["nominal"]["rule_local_transfer"], R)
    print(f"REPORT R-C nominal AXIOM minus carried rule {nomc['diff']:+.2f} p {nomc['p']:.3g} {nomc['wins']}/{nomc['ties']}/{nomc['losses']}")
    out["C"] = {"tests": tc, "holm": hc, "nominal": nomc,
                "baselines": {L: {b: comp(resc[L]["axiom2"], resc[L][b], R) for b in base} for L in resc},
                "means": {L: {arm: float(np.mean([R(r) for r in v.values()])) if v else None for arm, v in resc[L].items()} for L in resc}}
    out["criteria"] = crit
    json.dump(out, open(a.out, "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
