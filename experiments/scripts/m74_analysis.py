#!/usr/bin/env python3
"""M74 analysis against docs/PAPER5_M74_preregistration.md (F1-F3 and reported rows).

Usage: m74_analysis.py --out experiments/results/m74/analysis.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m62_analysis import boot_ci  # noqa: E402
from m66_verify import S30_19, holm, mean, paired, prio, seeds_of  # noqa: E402

BASE = ("single_agent_dqn", "independent_dqn", "mappo_tuned")
SEEDS = list(range(6100, 6120))
CELL = "m74/A_n37_hex"
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = {k: seeds_of(CELL, k, SEEDS) for k in ("axiom2",) + BASE + ("rule_static",)}
    ax = d["axiom2"]
    tests = {}
    for b in BASE:
        tests[f"{b}/prio"] = paired(ax, d[b], pp)
        tests[f"{b}/reward"] = paired(ax, d[b])
    h = holm({k: v["p"] for k, v in tests.items()})
    for k in tests:
        tests[k]["p_holm"] = h[k]
    crit("F1 AXIOM beats every baseline on priority SLA and reward, Holm over 6, p<0.05",
         all(t["n"] == 20 and t["diff"] > 0 and t["p_holm"] < 0.05 for t in tests.values()),
         "; ".join(f"{k} {fmt(t)}" for k, t in tests.items()))
    v = [pp(r) for r in ax.values()]
    lo, hi = boot_ci(v)
    crit("F2 AXIOM mean priority-slice compliance at least 90%", len(v) == 20 and np.mean(v) >= 90,
         f"{np.mean(v):.2f}% [{lo:.2f}, {hi:.2f}] over {len(v)} seeds")
    coll = sum(r["collapsed"] for r in ax.values())
    crit("F3 AXIOM collapses in at most 2 of 20 seeds", len(ax) == 20 and coll <= 2,
         f"{coll} of {len(ax)} ({sorted(s for s, r in ax.items() if r['collapsed'])})")
    summ = {}
    for k, dd in d.items():
        if not dd:
            continue
        w = [pp(r) for r in dd.values()]
        summ[k] = {"n": len(dd), "prio": float(np.mean(w)), "prio_ci": list(boot_ci(w)) if len(w) > 1 else None,
                   "reward": mean(dd), "collapsed": int(sum(r["collapsed"] for r in dd.values())),
                   "urllc": 100 * mean(dd, lambda r: r["sla"]["urllc"]), "embb": 100 * mean(dd, lambda r: r["sla"]["embb"])}
        crit(f"Reported: {k}", None, f"priority SLA {summ[k]['prio']:.2f}% (URLLC {summ[k]['urllc']:.1f}, eMBB {summ[k]['embb']:.1f}), "
             f"reward {summ[k]['reward']:.3f}, collapsed {summ[k]['collapsed']} of {summ[k]['n']}", "REPORT")
    best = max(summ[b]["prio"] for b in BASE)
    crit("Reported: AXIOM lead over the best baseline", None, f"{summ['axiom2']['prio'] - best:+.2f} points (35.0 in M73)", "REPORT")
    m73 = seeds_of("m73/A_n37_hex", "axiom2", S30_19)
    pool = list(m73.values()) + list(ax.values())
    pv = [pp(r) for r in pool]
    summ["pooled_axiom_hex_50"] = {"n": len(pool), "prio": float(np.mean(pv)), "prio_ci": list(boot_ci(pv)),
                                   "collapsed": int(sum(r["collapsed"] for r in pool))}
    crit("Reported: AXIOM pooled over M73 hex and M74 seeds", None,
         f"{np.mean(pv):.2f}% over {len(pool)} seeds, collapsed {summ['pooled_axiom_hex_50']['collapsed']}", "REPORT")
    judged = [c for c in C if c["holds"] is not None]
    n_fail = sum(not c["holds"] for c in judged)
    print(f"== {len(judged) - n_fail}/{len(judged)} hold, {len(C) - len(judged)} reported only")
    json.dump({"tests": tests, "summary": summ, "criteria": C, "n_judged": len(judged), "n_fail": n_fail},
              open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
