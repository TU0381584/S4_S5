#!/usr/bin/env python3
"""M70 analysis against docs/PAPER5_M70_preregistration.md (R1-R4).

Uses the independent reader in m66_verify.py. Every criterion is reported as
HOLDS, FAILS or REPORT.

Usage: m70_analysis.py --out experiments/results/m70/analysis.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import S15, S30, S30_19, holm, mean, paired, prio, seeds_of  # noqa: E402

LAYOUTS = ("fully_connected", "ring", "hex")
ABL19 = list(range(900, 912)) + [1000, 1001, 1002]
R = lambda r: r["reward"]  # noqa: E731
C = []


def crit(label, ok, detail, kind=None):
    tag = kind or ("HOLDS" if ok else "FAILS")
    print(f"[{tag}] {label}: {detail}")
    C.append({"label": label, "holds": None if kind else bool(ok), "detail": detail})


def fmt(t):
    return f"diff {t['diff']:+.4f}, W/T/L {t['wins']}/{t['ties']}/{t['losses']}, p {t['p']:.3g}, p_holm {t.get('p_holm', float('nan')):.3g} (n={t['n']})"


def r1(out):
    res = {}
    for n, ss in ((7, S15), (19, S30_19)):
        for t in LAYOUTS:
            rows = seeds_of(f"m70/R1/A_n{n}_{t}", "rule_static", ss)
            p_ = 100 * mean(rows, prio) if rows else float("nan")
            res[f"{n}/{t}"] = {"n": len(rows), "prio": p_, "reward": mean(rows) if rows else None}
            crit(f"R1 rule priority SLA >= 99% at N={n} {t}", len(rows) == len(ss) and p_ >= 99, f"{p_:.2f}% on {len(rows)} seeds")
    out["R1"] = res


def r2(out):
    res = {}
    for n, ss in ((7, S15), (19, S30_19)):
        tests = {}
        for t in LAYOUTS:
            sd = f"m66c_fresh/C7_A_n19_ring" if (n == 19 and t == "ring") else f"m70/R2/A_n{n}_{t}"
            sg = seeds_of(sd, "single_agent_dqn", ss)
            ax = seeds_of(f"m65_scaling/n{n}_{t}", "axiom2", ss)
            for m, f in (("reward", R), ("prio", prio)):
                tests[f"{t}/{m}"] = paired(ax, sg, f)
            res[f"A{n}/{t}"] = {"seeded_single_prio": 100 * mean(sg, prio) if sg else None,
                                "seeded_single_collapsed": int(sum(r["collapsed"] for r in sg.values())), "n": len(sg)}
        h = holm({k: v["p"] for k, v in tests.items()})
        for k in tests:
            tests[k]["p_holm"] = h[k]
        res[f"A{n}_tests"] = tests
        ok = all(v["n"] == len(ss) and v["diff"] > 0 and v["p_holm"] < 0.05 for v in tests.values())
        crit(f"R2 Env A N={n}: AXIOM beats seeded single-agent DQN, all 6 at Holm p<0.05", ok,
             f"max p_holm {max(h.values()):.3g}, min diff {min(v['diff'] for v in tests.values()):+.4f}")
    for t in LAYOUTS:
        ax = seeds_of(f"m64/n7_{t}", "axiom2", S15)
        sg = seeds_of(f"m70/R2/B_n7_{t}", "single_agent_dqn", S15)
        tr, tp = paired(ax, sg), paired(ax, sg, prio)
        res[f"B7/{t}"] = {"reward": tr, "prio": tp}
        crit(f"R2 Env B N=7 {t}: AXIOM vs seeded single-agent DQN", None, f"reward {fmt(tr)}; prio {fmt(tp)}", "REPORT")
    out["R2"] = res


def r3(out):
    sel = json.load(open("/home/kmanojp/oranslice_rig/experiments/results/m70/R3_pilot/selection.json"))
    res = {"selection": {e: sel[e]["selected"] for e in sel}}
    cells = {"A3": ("m65_n3_view", "m70/R3_confirm/A_n3", S30), "A19": ("m65_scaling/n19_ring", "m70/R3_confirm/A_n19_ring", S30_19),
             "B3": ("m64/n3_fully_connected", "m70/R3_confirm/B_n3", S30), "B7": ("m64/n7_ring", "m70/R3_confirm/B_n7_ring", S15)}
    d = {k: (seeds_of(a, "axiom2", ss), seeds_of(b, "mappo", ss), seeds_of(a, "mappo_tuned", ss)) for k, (a, b, ss) in cells.items()}
    tests = {"A3/reward": paired(d["A3"][0], d["A3"][1]), "A19/reward": paired(d["A19"][0], d["A19"][1]),
             "A19/prio": paired(d["A19"][0], d["A19"][1], prio), "B3/reward": paired(d["B3"][0], d["B3"][1])}
    h = holm({k: v["p"] for k, v in tests.items()})
    for k in tests:
        tests[k]["p_holm"] = h[k]
    res["tests"] = tests
    for k, (ax, mb, mo) in d.items():
        res[f"{k}_summary"] = {"axiom": mean(ax) if ax else None, "mappo_best": mean(mb) if mb else None,
                               "mappo_reported": mean(mo) if mo else None, "n_best": len(mb),
                               "mappo_best_prio": 100 * mean(mb, prio) if mb else None,
                               "mappo_best_collapsed": int(sum(r["collapsed"] for r in mb.values()))}
    crit("R3 AXIOM beats the grid-selected MAPPO, all 4 at Holm p<0.05",
         all(v["diff"] > 0 and v["p_holm"] < 0.05 and v["n"] > 0 for v in tests.values()),
         "; ".join(f"{k} {fmt(v)}" for k, v in tests.items()))
    tb = paired(d["B7"][0], d["B7"][1])
    res["B7_test"] = tb
    crit("R3 Env B N=7 ring: AXIOM vs grid-selected MAPPO", None, fmt(tb), "REPORT")
    out["R3"] = res


def r4(out):
    res = {}
    cells = {"A3": ("m65_n3_view", S30), "B3": ("m64/n3_fully_connected", S30), "A19": ("m65_scaling/n19_ring", ABL19)}
    for v in ("sharedhead", "vdn"):
        tests, summ = {}, {}
        for k, (cell, ss) in cells.items():
            vd = {"A3": "A_n3", "B3": "B_n3", "A19": "A_n19_ring"}[k]
            ax, va = seeds_of(cell, "axiom2", ss), seeds_of(f"m70/R4_{v}/{vd}", "axiom2", ss)
            for m, f in (("reward", R), ("prio", prio)):
                tests[f"{k}/{m}"] = paired(ax, va, f)
            summ[k] = {"axiom": mean(ax), "variant": mean(va) if va else None, "variant_prio": 100 * mean(va, prio) if va else None,
                       "axiom_prio": 100 * mean(ax, prio), "variant_collapsed": int(sum(r["collapsed"] for r in va.values())), "n": len(va)}
        h = holm({k: t["p"] for k, t in tests.items()})
        for k in tests:
            tests[k]["p_holm"] = h[k]
        better = [k for k, t in tests.items() if t["diff"] > 0 and t["p_holm"] < 0.05]
        worse = [k for k, t in tests.items() if t["diff"] < 0 and t["p_holm"] < 0.05]
        res[v] = {"tests": tests, "summary": summ, "axiom_better": better, "axiom_worse": worse}
        name = {"sharedhead": "per-slice heads", "vdn": "per-request TD samples"}[v]
        crit(f"R4 {name} supported (AXIOM better in >=1 cell, worse in none)", bool(better) and not worse,
             f"better {better}, worse {worse}; " + "; ".join(f"{k} {fmt(t)}" for k, t in tests.items()))
    out["R4"] = res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = {}
    for f in (r1, r2, r3, r4):
        f(out)
    judged = [c for c in C if c["holds"] is not None]
    n_fail = sum(not c["holds"] for c in judged)
    print(f"== {len(judged) - n_fail}/{len(judged)} hold, {len(C) - len(judged)} reported only")
    out["criteria"], out["n_judged"], out["n_fail"] = C, len(judged), n_fail
    json.dump(out, open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
