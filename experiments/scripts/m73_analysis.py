#!/usr/bin/env python3
"""M73 analysis against docs/PAPER5_M73_preregistration.md (P1-P4 and reported rows).

Usage: m73_analysis.py --out experiments/results/m73/analysis.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m62_analysis import boot_ci  # noqa: E402
from m66_verify import ROOT, S15, S30_19, holm, mean, paired, prio, seeds_of  # noqa: E402

BASE = ("single_agent_dqn", "independent_dqn", "mappo_tuned")
LAYOUT_SEEDS = {"hex": S30_19, "ring": S15, "fully_connected": S15}
C = []


def crit(label, ok, detail, kind=None):
    tag = kind or ("HOLDS" if ok else "FAILS")
    print(f"[{tag}] {label}: {detail}")
    C.append({"label": label, "holds": None if kind else bool(ok), "detail": detail})


def fmt(t):
    return (f"diff {t['diff']:+.4f}, W/T/L {t['wins']}/{t['ties']}/{t['losses']}, p {t['p']:.3g}"
            + (f", p_holm {t['p_holm']:.3g}" if "p_holm" in t else "") + f" (n={t['n']})")


def pp(r):
    return 100 * prio(r)


def tests_for(layouts):
    tests = {}
    for t in layouts:
        ss = LAYOUT_SEEDS[t]
        ax = seeds_of(f"m73/A_n37_{t}", "axiom2", ss)
        for b in BASE:
            bl = seeds_of("m73/A_n37_hex", b, ss)          # layout-independent baselines, run once in the hex cell
            tests[f"{t}/{b}/prio"] = paired(ax, bl, pp)
            tests[f"{t}/{b}/reward"] = paired(ax, bl)
    h = holm({k: v["p"] for k, v in tests.items()})
    for k in tests:
        tests[k]["p_holm"] = h[k]
    return tests


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = {}
    p1 = tests_for(["hex"])
    ok1 = all(t["n"] == 30 and t["diff"] > 0 and t["p_holm"] < 0.05 for t in p1.values())
    crit("P1 hex: AXIOM beats every baseline on priority SLA and reward, Holm over 6, p<0.05", ok1,
         "; ".join(f"{k} {fmt(t)}" for k, t in p1.items()))
    p2 = tests_for(["ring", "fully_connected"])
    ok2 = all(t["n"] == 15 and t["diff"] > 0 and t["p_holm"] < 0.05 for t in p2.values())
    crit("P2 ring and fully-connected: the same 6 comparisons per layout, Holm over 12, p<0.05", ok2,
         "; ".join(f"{k} {fmt(t)}" for k, t in p2.items()))
    pooled = {t: seeds_of(f"m73/A_n37_{t}", "axiom2", ss) for t, ss in LAYOUT_SEEDS.items()}
    rows = [r for d in pooled.values() for r in d.values()]
    v = [pp(r) for r in rows]
    lo, hi = boot_ci(v)
    crit("P3 AXIOM pooled priority-slice compliance at least 90%", len(rows) == 60 and np.mean(v) >= 90,
         f"{np.mean(v):.2f}% [{lo:.2f}, {hi:.2f}] over {len(rows)} runs")
    coll = sum(r["collapsed"] for r in rows)
    crit("P4 AXIOM collapses in at most 10% of runs", len(rows) == 60 and coll <= 6, f"{coll} of {len(rows)}")
    summ = {"axiom2": {"n": len(rows), "prio": float(np.mean(v)), "prio_ci": [lo, hi], "collapsed": coll,
                       "reward_by_layout": {t: mean(d) for t, d in pooled.items()},
                       "prio_by_layout": {t: 100 * mean(d, prio) for t, d in pooled.items()},
                       "urllc": 100 * float(np.mean([r["sla"]["urllc"] for r in rows])),
                       "embb": 100 * float(np.mean([r["sla"]["embb"] for r in rows]))}}
    for b in BASE + ("rule_static",):
        d = seeds_of("m73/A_n37_hex", b, S30_19)
        if not d:
            continue
        w = [pp(r) for r in d.values()]
        summ[b] = {"n": len(d), "prio": float(np.mean(w)), "prio_ci": list(boot_ci(w)) if len(w) > 1 else None,
                   "reward": mean(d), "collapsed": int(sum(r["collapsed"] for r in d.values())),
                   "urllc": 100 * float(np.mean([r["sla"]["urllc"] for r in d.values()])),
                   "embb": 100 * float(np.mean([r["sla"]["embb"] for r in d.values()]))}
    best = max(summ[b]["prio"] for b in BASE if b in summ)
    crit("Reported: AXIOM lead over the best baseline on pooled priority SLA at 37 gNBs", None,
         f"{summ['axiom2']['prio'] - best:+.2f} points (32.0 at 19 gNBs)", "REPORT")
    for b in BASE + ("rule_static",):
        if b in summ:
            s = summ[b]
            crit(f"Reported: {b} at 37 gNBs", None,
                 f"priority SLA {s['prio']:.2f}% (URLLC {s['urllc']:.1f}, eMBB {s['embb']:.1f}), reward {s['reward']:.3f}, "
                 f"collapsed {s['collapsed']} of {s['n']}", "REPORT")
    crit("Reported: AXIOM by layout", None,
         "; ".join(f"{t} reward {summ['axiom2']['reward_by_layout'][t]:.3f}, priority SLA {summ['axiom2']['prio_by_layout'][t]:.2f}%"
                   for t in LAYOUT_SEEDS), "REPORT")
    g = seeds_of("m73/A_n37_hex_mappo_grid", "mappo", S15)
    if g:
        ax = seeds_of("m73/A_n37_hex", "axiom2", S15)
        t1, t2 = paired(ax, g, pp), paired(ax, g)
        summ["mappo_grid"] = {"n": len(g), "prio": 100 * mean(g, prio), "reward": mean(g),
                              "collapsed": int(sum(r["collapsed"] for r in g.values()))}
        crit("Reported: AXIOM vs grid-selected MAPPO (900 episodes), hex 15 seeds", None,
             f"MAPPO priority SLA {summ['mappo_grid']['prio']:.2f}%, reward {summ['mappo_grid']['reward']:.3f}; "
             f"AXIOM minus MAPPO priority {fmt(t1)}; reward {fmt(t2)}", "REPORT")
        out["mappo_grid_tests"] = {"prio": t1, "reward": t2}
    out.update({"P1": p1, "P2": p2, "summary": summ})
    train = {}
    for t, ss in LAYOUT_SEEDS.items():
        for f in os.listdir(f"{ROOT}/m73/A_n37_{t}") if os.path.isdir(f"{ROOT}/m73/A_n37_{t}") else []:
            if f.endswith(".json") and "_" in f and f[0].isalpha() and not f.startswith(("rule", "analysis", "complexity")):
                arm = f.rsplit("_", 1)[0]
                for s, r in json.load(open(f"{ROOT}/m73/A_n37_{t}/{f}")).items():
                    if isinstance(r, dict) and "train_seconds" in r:
                        train.setdefault(f"{t}/{arm}", []).append(r["train_seconds"])
    out["train_seconds_median"] = {k: float(np.median(v)) for k, v in train.items()}
    crit("Reported: median training seconds per seed", None, json.dumps(out["train_seconds_median"]), "REPORT")
    judged = [c for c in C if c["holds"] is not None]
    n_fail = sum(not c["holds"] for c in judged)
    print(f"== {len(judged) - n_fail}/{len(judged)} hold, {len(C) - len(judged)} reported only")
    out["criteria"], out["n_judged"], out["n_fail"] = C, len(judged), n_fail
    json.dump(out, open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
