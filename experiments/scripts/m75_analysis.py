#!/usr/bin/env python3
"""M75 analysis against docs/PAPER5_M75_preregistration.md (B, C, D, E).

Usage: m75_analysis.py --out experiments/results/m75/analysis.json
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


def learned_rows(n, arm):
    if n == 37:
        if arm == "axiom2":
            return [r for t, ss in (("hex", S30_19), ("ring", S15), ("fully_connected", S15)) for r in seeds_of(f"m73/A_n37_{t}", arm, ss).values()]
        return list(seeds_of("m73/A_n37_hex", arm, S30_19).values())
    ss = S15 if n == 7 else S30_19
    return [r for t in ("fully_connected", "ring", "hex") for r in seeds_of(f"m65_scaling/n{n}_{t}", arm, ss).values()]


def part_b(out):
    res = {}
    for n, ss in ((7, S15), (19, S30_19), (37, S30_19)):
        aa = seeds_of(f"m75/B_acceptall/n{n}", "rule_accept_all", ss)
        a_p = float(np.mean([pp(r) for r in aa.values()]))
        res[n] = {"n": len(aa), "accept_all_prio": a_p, "accept_all_reward": mean(aa), "arms": {}}
        for arm in ("axiom2",) + BASE:
            rows = learned_rows(n, arm)
            nc = [pp(r) for r in rows if not r["collapsed"]]
            res[n]["arms"][arm] = {"prio": float(np.mean([pp(r) for r in rows])), "prio_noncollapsed": float(np.mean(nc)) if nc else None,
                                   "n": len(rows), "collapsed": int(sum(r["collapsed"] for r in rows))}
        below = [a for a, v in res[n]["arms"].items() if v["prio"] < a_p]
        crit(f"B reported: accept-all at {n} gNBs", None,
             f"priority SLA {a_p:.2f}%, reward {res[n]['accept_all_reward']:.3f} ({len(aa)} seeds); arms below it on mean: {below}; "
             + "; ".join(f"{a} {v['prio']:.1f}% (non-collapsed {v['prio_noncollapsed']:.1f}%)" if v["prio_noncollapsed"] is not None else f"{a} {v['prio']:.1f}%"
                         for a, v in res[n]["arms"].items()), "REPORT")
    out["B"] = res


def part_c(out):
    sel = json.load(open(f"{ROOT}/m75/C_selection.json"))
    tests, rows = {}, {}
    for n in (19, 37):
        ax = seeds_of("m65_scaling/n19_hex" if n == 19 else "m73/A_n37_hex", "axiom2", S30_19)
        for arm in ("single_agent_dqn", "independent_dqn"):
            s = sel[f"{arm}|{n}"]
            cell = ("m65_scaling/n19_hex" if n == 19 else "m73/A_n37_hex") if s["is_current"] else f"m75/C_confirm/n{n}"
            bl = seeds_of(cell, arm, S30_19)
            rows[f"{arm}|{n}"] = {"selected": s["selected"], "is_current": s["is_current"], "cell": cell, "n": len(bl),
                                  "prio": float(np.mean([pp(r) for r in bl.values()])), "reward": mean(bl),
                                  "collapsed": int(sum(r["collapsed"] for r in bl.values()))}
            tests[f"{n}/{arm}/prio"] = paired(ax, bl, pp)
            tests[f"{n}/{arm}/reward"] = paired(ax, bl)
    h = holm({k: v["p"] for k, v in tests.items()})
    for k in tests:
        tests[k]["p_holm"] = h[k]
    crit("C1 AXIOM beats each tuned DQN baseline on priority SLA and reward at 19 and 37 gNBs, Holm over 8, p<0.05",
         all(t["n"] == 30 and t["diff"] > 0 and t["p_holm"] < 0.05 for t in tests.values()), "; ".join(f"{k} {fmt(t)}" for k, t in tests.items()))
    for k, v in rows.items():
        crit(f"C reported: tuned {k}", None, f"selected lr,batch {v['selected']} (current: {v['is_current']}), priority SLA {v['prio']:.2f}%, "
             f"reward {v['reward']:.3f}, collapsed {v['collapsed']} of {v['n']}; grid {json.dumps({g: round(x['reward'], 3) for g, x in sel[k]['grid'].items()})}", "REPORT")
    out["C"] = {"tests": tests, "rows": rows}


def per_gnb(cell, arm, s):
    f = f"{ROOT}/{cell}/{arm}/seed{s}/eval/per_gnb_sla.json"
    if not os.path.exists(f):
        return None
    m = json.load(open(f))["mean_compliance"]
    return 100 * 0.5 * (m["urllc"] + m["embb"])


def part_d(out):
    cell = "m75/D_envB_n19_hex"
    arms = ("axiom2",) + BASE + ("rule_static", "rule_accept_all", "rule_local_transfer")
    d = {a: seeds_of(cell, a, S15) for a in arms}
    for a in arms:
        for s, r in d[a].items():
            r["pergnb"] = per_gnb(cell, a, s)
    assert all(r["pergnb"] is not None for v in d.values() for r in v.values()), "missing per-gNB sidecar"
    g = lambda r: r["pergnb"]
    t1 = {}
    for b in BASE:
        t1[f"{b}/reward"] = paired(d["axiom2"], d[b])
        t1[f"{b}/pergnb"] = paired(d["axiom2"], d[b], g)
    h1 = holm({k: v["p"] for k, v in t1.items()})
    for k in t1:
        t1[k]["p_holm"] = h1[k]
    crit("D1 AXIOM beats every learned baseline on reward and per-gNB priority SLA (Env B, 19 gNBs), Holm over 6, p<0.05",
         all(t["n"] == 15 and t["diff"] > 0 and t["p_holm"] < 0.05 for t in t1.values()), "; ".join(f"{k} {fmt(t)}" for k, t in t1.items()))
    t2 = {r: paired(d["axiom2"], d[r]) for r in ("rule_static", "rule_accept_all")}
    h2 = holm({k: v["p"] for k, v in t2.items()})
    for k in t2:
        t2[k]["p_holm"] = h2[k]
    crit("D2 AXIOM beats rule_static and rule_accept_all on reward, Holm over 2, p<0.05",
         all(t["n"] == 15 and t["diff"] > 0 and t["p_holm"] < 0.05 for t in t2.values()), "; ".join(f"{k} {fmt(t)}" for k, t in t2.items()))
    t3 = {"reward": paired(d["axiom2"], d["rule_local_transfer"]), "pergnb": paired(d["axiom2"], d["rule_local_transfer"], g)}
    crit("D reported: AXIOM vs the transferred tuned rule", None, "; ".join(f"{k} {fmt(t)}" for k, t in t3.items()), "REPORT")
    summ = {}
    for a in arms:
        v = d[a]
        pg = [g(r) for r in v.values()]
        summ[a] = {"n": len(v), "reward": mean(v), "pergnb_prio": float(np.mean(pg)), "pergnb_ci": list(boot_ci(pg)),
                   "cluster_prio": 100 * mean(v, prio), "collapsed": int(sum(r["collapsed"] for r in v.values()))}
        crit(f"D reported: {a}", None, f"reward {summ[a]['reward']:.3f}, per-gNB priority SLA {summ[a]['pergnb_prio']:.2f}%, "
             f"cluster-level priority SLA {summ[a]['cluster_prio']:.2f}%, collapsed {summ[a]['collapsed']} of {summ[a]['n']}", "REPORT")
    out["D"] = {"D1": t1, "D2": t2, "vs_transfer": t3, "summary": summ}


def part_e(out):
    res = {}
    for f in ("hex_axiom2", "ring_axiom2", "fully_connected_axiom2", "hex_single_agent_dqn", "hex_independent_dqn", "hex_mappo_tuned"):
        p = f"{ROOT}/m75/E_screen/{f}.json"
        if os.path.exists(p):
            rows = json.load(open(p))
            res[f] = {"n": len(rows), "fails": sum(r["fails"] for r in rows),
                      "collapsed_and_failed": sum(r["fails"] and r["eval_collapsed"] for r in rows),
                      "collapsed": sum(r["eval_collapsed"] for r in rows)}
    crit("E reported: validation screen at 37 gNBs", None, json.dumps(res), "REPORT")
    out["E"] = res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--parts", default="BCDE")
    a = ap.parse_args()
    out = {}
    for k, f in (("B", part_b), ("C", part_c), ("D", part_d), ("E", part_e)):
        if k in a.parts:
            f(out)
    judged = [c for c in C if c["holds"] is not None]
    n_fail = sum(not c["holds"] for c in judged)
    print(f"== {len(judged) - n_fail}/{len(judged)} hold, {len(C) - len(judged)} reported only")
    out["criteria"], out["n_judged"], out["n_fail"] = C, len(judged), n_fail
    json.dump(out, open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
