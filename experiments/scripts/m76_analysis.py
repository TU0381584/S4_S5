#!/usr/bin/env python3
"""M76 analysis against docs/PAPER5_M76_preregistration.md (b1, b2, c, d, e).

Usage: m76_analysis.py --out experiments/results/m76/analysis.json [--parts b1,b2,c,d,e]
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
from scipy.stats import wilcoxon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m62_analysis import boot_ci  # noqa: E402
from m66_verify import ROOT, S15, S30, S30_19, holm, mean, paired, prio, seeds_of  # noqa: E402

BASE = ("single_agent_dqn", "independent_dqn", "mappo_tuned")
C = []


def crit(label, ok, detail, kind=None):
    tag = kind or ("HOLDS" if ok else "FAILS")
    print(f"[{tag}] {label}: {detail}")
    C.append({"label": label, "holds": None if kind else bool(ok), "detail": detail})


def fmt(t):
    return (f"diff {t['diff']:+.4f}, W/T/L {t['wins']}/{t['ties']}/{t['losses']}, p {t['p']:.3g}"
            + (f", p_holm {t['p_holm']:.3g}" if "p_holm" in t else "") + f" (n={t['n']})")


def pv(a, b):
    """paired test on two {seed: value} dicts"""
    common = sorted(set(a) & set(b))
    d = np.array([a[s] - b[s] for s in common])
    p = float(wilcoxon(d).pvalue) if np.any(d != 0) else 1.0
    return {"n": len(d), "diff": float(d.mean()) if len(d) else float("nan"), "wins": int((d > 0).sum()),
            "ties": int((d == 0).sum()), "losses": int((d < 0).sum()), "p": p}


def pergnb(cell, arm, s):
    f = f"{ROOT}/{cell}/{arm}/seed{s}/eval/per_gnb_sla.json"
    m = json.load(open(f))["mean_compliance"]
    return 100 * 0.5 * (m["urllc"] + m["embb"])


def pp(r):
    return 100 * prio(r)


def cell_summary(cell, arms, seeds, with_pergnb=True):
    out = {}
    for a in arms:
        d = seeds_of(cell, a, seeds)
        row = {"n": len(d), "reward": mean(d) if d else None, "prio": 100 * mean(d, prio) if d else None,
               "collapsed": int(sum(r["collapsed"] for r in d.values()))}
        if with_pergnb and d:
            g = [pergnb(cell, a, s) for s in d]
            row["pergnb"] = float(np.mean(g))
        out[a] = row
    return out


def part_b1(out):
    res = {}
    for f in glob.glob(f"{ROOT}/m76/b1_shift_n19/*_eval_*.json"):
        sh = os.path.basename(f).split("_eval_")[0]
        for s, v in json.load(open(f))["results"].items():
            res.setdefault(sh, {})[int(s)] = v
    stored = {a: seeds_of("m75/D_envB_n19_hex", a, S15) for a in ("axiom2", "rule_local_transfer", "rule_static")}
    nom_ok = len(res.get("nominal", {})) == 15 and all(abs(res["nominal"][s][a]["reward"] - stored[a][s]["reward"]) < 1e-9 for s in S15 for a in stored)
    crit("b1 sanity: nominal reproduces the stored M75 results exactly", None, f"{nom_ok} on {len(res.get('nominal', {}))} seeds", "CHECK")
    tests = {}
    for sh in ("nominal", "load_1.10", "load_1.15", "load_1.20"):
        r = res[sh]
        for m in ("reward", "pergnb"):
            tests[f"{sh}/tuned/{m}"] = pv({s: r[s]["axiom2"][m] for s in r}, {s: r[s]["rule_local_transfer"][m] for s in r})
            tests[f"{sh}/static/{m}"] = pv({s: r[s]["axiom2"][m] for s in r}, {s: r[s]["rule_static"][m] for s in r})
        tests[f"{sh}/means"] = {a: {m: float(np.mean([r[s][a][m] for s in r])) for m in ("reward", "pergnb")} for a in ("axiom2", "rule_local_transfer", "rule_static")}
    prim = ("load_1.10", "load_1.15", "load_1.20")
    h = holm({k: tests[f"{k}/tuned/reward"]["p"] for k in prim})
    for k in prim:
        tests[f"{k}/tuned/reward"]["p_holm"] = h[k]
    crit("B1 AXIOM beats the carried-over tuned rule on reward at 1.10, 1.15, 1.20 x load (19 gNBs), Holm over 3",
         all(tests[f"{k}/tuned/reward"]["n"] == 15 and tests[f"{k}/tuned/reward"]["diff"] > 0 and h[k] < 0.05 for k in prim),
         "; ".join(f"{k} {fmt(tests[f'{k}/tuned/reward'])}" for k in prim))
    for sh in ("nominal",) + prim:
        crit(f"b1 reported {sh}", None, f"means {json.dumps({a: {m: round(v, 3) for m, v in x.items()} for a, x in tests[f'{sh}/means'].items()})}; "
             f"vs tuned per-gNB {fmt(tests[f'{sh}/tuned/pergnb'])}; vs static reward {fmt(tests[f'{sh}/static/reward'])}", "REPORT")
    out["b1"] = tests


def part_b2(out):
    cell = "m76/b2_hetero_n7_ring"
    arms = ("axiom2",) + BASE + ("rule_static", "rule_accept_all", "rule_local_transfer", "rule_local")
    d = {a: seeds_of(cell, a, S15) for a in arms}
    t = paired(d["axiom2"], d["rule_local_transfer"])
    crit("B2 AXIOM beats the nominally tuned rule on reward under heterogeneous load (7 gNBs ring)", t["n"] == 15 and t["diff"] > 0 and t["p"] < 0.05, fmt(t))
    g = {a: {s: pergnb(cell, a, s) for s in d[a]} for a in arms}
    rep = {"vs_retuned_reward": paired(d["axiom2"], d["rule_local"]), "vs_retuned_pergnb": pv(g["axiom2"], g["rule_local"]),
           "vs_transfer_pergnb": pv(g["axiom2"], g["rule_local_transfer"]), "vs_static_reward": paired(d["axiom2"], d["rule_static"])}
    for b in BASE:
        rep[f"vs_{b}_reward"] = paired(d["axiom2"], d[b])
        rep[f"vs_{b}_pergnb"] = pv(g["axiom2"], g[b])
    sel = json.load(open(f"{ROOT}/{cell}/rule_local_selection.json"))["selected"]
    summ = cell_summary(cell, arms, S15)
    for k, v in rep.items():
        crit(f"b2 reported AXIOM {k}", None, fmt(v), "REPORT")
    crit("b2 reported summary", None, f"re-tuned rule {sel}; " + "; ".join(f"{a} reward {v['reward']:.3f} per-gNB {v['pergnb']:.1f}% collapsed {v['collapsed']}" for a, v in summ.items()), "REPORT")
    out["b2"] = {"B2": t, "reported": rep, "summary": summ, "retuned_rule": sel}


def part_c(out):
    cell = "m76/c_pergnb_n19_hex"
    arms = ("axiom2",) + BASE + ("rule_static", "rule_accept_all", "rule_local_transfer")
    d = {a: seeds_of(cell, a, S15) for a in arms}
    g = {a: {s: pergnb(cell, a, s) for s in d[a]} for a in arms}
    old = {s: pergnb("m75/D_envB_n19_hex", "axiom2", s) for s in S15}
    c1, c2 = pv(g["axiom2"], old), pv(g["axiom2"], g["rule_static"])
    crit("C1 AXIOM with the per-gNB penalty keeps higher per-gNB priority compliance than AXIOM with the original reward", c1["n"] == 15 and c1["diff"] > 0 and c1["p"] < 0.05, fmt(c1))
    crit("C2 AXIOM with the per-gNB penalty beats the static rule on per-gNB priority compliance", c2["n"] == 15 and c2["diff"] > 0 and c2["p"] < 0.05, fmt(c2))
    rep = {"vs_transfer_pergnb": pv(g["axiom2"], g["rule_local_transfer"]), "vs_static_reward": paired(d["axiom2"], d["rule_static"]),
           "vs_transfer_reward": paired(d["axiom2"], d["rule_local_transfer"])}
    for b in BASE:
        rep[f"vs_{b}_pergnb"] = pv(g["axiom2"], g[b])
        rep[f"vs_{b}_reward"] = paired(d["axiom2"], d[b])
    old_b = {b: float(np.mean([pergnb("m75/D_envB_n19_hex", b, s) for s in S15])) for b in BASE + ("rule_static", "rule_accept_all", "rule_local_transfer")}
    summ = cell_summary(cell, arms, S15)
    for k, v in rep.items():
        crit(f"c reported AXIOM {k}", None, fmt(v), "REPORT")
    crit("c reported summary (per-gNB under original reward in brackets)", None,
         f"AXIOM {summ['axiom2']['pergnb']:.1f}% (orig {np.mean(list(old.values())):.1f}%); " +
         "; ".join(f"{a} reward {v['reward']:.3f} per-gNB {v['pergnb']:.1f}% (orig {old_b.get(a, float('nan')):.1f}%) collapsed {v['collapsed']}" for a, v in summ.items() if a != "axiom2"), "REPORT")
    out["c"] = {"C1": c1, "C2": c2, "reported": rep, "summary": summ, "axiom_orig_pergnb": float(np.mean(list(old.values())))}


def part_d(out):
    cells = {"A3": ("m76/d_vdn/A_n3", "m65_n3_view", S30), "B3": ("m76/d_vdn/B_n3", "m64/n3_fully_connected", S30),
             "A19": ("m76/d_vdn/A_n19_hex", "m65_scaling/n19_hex", S30_19)}
    tests, summ = {}, {}
    for k, (vc, ac, ss) in cells.items():
        v, a = seeds_of(vc, "vdn", ss), seeds_of(ac, "axiom2", ss)
        tests[f"{k}/reward"] = paired(a, v)
        if k == "A19":
            tests[f"{k}/prio"] = paired(a, v, pp)
        ind = seeds_of(ac, "independent_dqn", ss)
        summ[k] = {"n": len(v), "vdn_reward": mean(v), "vdn_prio": 100 * mean(v, prio), "vdn_collapsed": int(sum(r["collapsed"] for r in v.values())),
                   "axiom_reward": mean(a), "axiom_prio": 100 * mean(a, prio), "independent_reward": mean(ind) if ind else None,
                   "independent_prio": 100 * mean(ind, prio) if ind else None, "vs_independent_reward": paired(v, ind) if ind else None}
    h = holm({k: v["p"] for k, v in tests.items()})
    for k in tests:
        tests[k]["p_holm"] = h[k]
    crit("D1 AXIOM beats VDN on reward in all three cells and on priority compliance at 19 gNBs, Holm over 4",
         all(t["diff"] > 0 and t["p_holm"] < 0.05 for t in tests.values()), "; ".join(f"{k} {fmt(t)}" for k, t in tests.items()))
    for k, v in summ.items():
        crit(f"d reported {k}", None, f"VDN reward {v['vdn_reward']:.3f}, priority {v['vdn_prio']:.1f}%, collapsed {v['vdn_collapsed']} of {v['n']}; "
             f"AXIOM {v['axiom_reward']:.3f} / {v['axiom_prio']:.1f}%; independent DQN {v['independent_reward']:.3f} / {v['independent_prio']:.1f}%; "
             f"VDN minus independent {fmt(v['vs_independent_reward'])}", "REPORT")
    out["d"] = {"tests": tests, "summary": summ}


def part_e(out):
    tests, summ = {}, {}
    for L in ("1.10", "1.20"):
        cell = f"m76/e_load{L}_n19_hex"
        ax = seeds_of(cell, "axiom2", S15)
        for b in BASE:
            tests[f"{L}/{b}/prio"] = paired(ax, seeds_of(cell, b, S15), pp)
            tests[f"{L}/{b}/reward"] = paired(ax, seeds_of(cell, b, S15))
        summ[L] = cell_summary(cell, ("axiom2",) + BASE + ("rule_static", "rule_accept_all"), S15, with_pergnb=False)
    prim = [k for k in tests if k.endswith("/prio")]
    h = holm({k: tests[k]["p"] for k in prim})
    for k in prim:
        tests[k]["p_holm"] = h[k]
    crit("E1 AXIOM beats each learned baseline on priority compliance at 1.10 and 1.20 x load (Env A, 19 gNBs), Holm over 6",
         all(tests[k]["n"] == 15 and tests[k]["diff"] > 0 and h[k] < 0.05 for k in prim), "; ".join(f"{k} {fmt(tests[k])}" for k in prim))
    for L, v in summ.items():
        crit(f"e reported load {L}", None, "; ".join(f"{a} reward {x['reward']:.3f} priority {x['prio']:.1f}% collapsed {x['collapsed']}" for a, x in v.items()), "REPORT")
    out["e"] = {"tests": tests, "summary": summ}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--parts", default="b1,b2,c,d,e")
    a = ap.parse_args()
    out = {}
    fns = {"b1": part_b1, "b2": part_b2, "c": part_c, "d": part_d, "e": part_e}
    for k in a.parts.split(","):
        fns[k](out)
    judged = [c for c in C if c["holds"] is not None]
    n_fail = sum(not c["holds"] for c in judged)
    print(f"== {len(judged) - n_fail}/{len(judged)} hold, {len(C) - len(judged)} reported only")
    out["criteria"], out["n_judged"], out["n_fail"] = C, len(judged), n_fail
    json.dump(out, open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
