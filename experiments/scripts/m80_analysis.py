#!/usr/bin/env python3
"""M80 analysis against docs/PAPER5_M80_preregistration.md (A, C, D, B).

Uses the independent reader in m66_verify.py. Every criterion is reported as
HOLDS or FAILS; a part whose runs are missing is reported as NOT RUN.

Usage: m80_analysis.py --out experiments/results/m80/analysis.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m62_analysis import boot_ci  # noqa: E402
from m66_verify import ROOT, S15, holm, paired, prio, seeds_of  # noqa: E402

BASE = ("single_agent_dqn", "independent_dqn", "mappo_tuned")
F15 = list(range(7000, 7015))
C = []


def crit(label, ok, detail, kind=None):
    tag = kind or ("HOLDS" if ok else "FAILS")
    print(f"[{tag}] {label}: {detail}")
    C.append({"label": label, "holds": None if kind else bool(ok), "detail": detail})


def fmt(t):
    return (f"diff {t['diff']:+.4f}, W/T/L {t['wins']}/{t['ties']}/{t['losses']}, p {t['p']:.3g}"
            + (f", p_holm {t['p_holm']:.3g}" if "p_holm" in t else "") + f" (n={t['n']})")


def holm_family(tests):
    h = holm({k: v["p"] for k, v in tests.items()})
    for k in tests:
        tests[k]["p_holm"] = h[k]
    return tests


def mmtc_only(r):
    return r["blocks"] > 0 and r["mmtc"] == r["blocks"]


def per_gnb(cell, arm, s):
    f = f"{ROOT}/{cell}/{arm}/seed{s}/eval/per_gnb_sla.json"
    if not os.path.exists(f):
        return None
    m = json.load(open(f))["mean_compliance"]
    return 100 * 0.5 * (m["urllc"] + m["embb"])


def describe(rows, n):
    v = list(rows.values())
    rw = [r["reward"] / n for r in v]
    pr = [100 * prio(r) for r in v]
    out = {"n": len(v), "reward_per_gnb": float(np.mean(rw)), "reward_per_gnb_ci": list(boot_ci(rw)),
           "prio_sla": float(np.mean(pr)), "prio_sla_ci": list(boot_ci(pr)),
           "mmtc_share_of_blocks": float(sum(r["mmtc"] for r in v) / max(1, sum(r["blocks"] for r in v))),
           "mmtc_only_seeds": int(sum(mmtc_only(r) for r in v)), "collapsed": int(sum(r["collapsed"] for r in v))}
    if all("pergnb" in r for r in v):
        pg = [r["pergnb"] for r in v]
        out.update(pergnb_prio=float(np.mean(pg)), pergnb_ci=list(boot_ci(pg)))
    return out


def show(name, d):
    extra = f" per-gNB {d['pergnb_prio']:5.1f}" if "pergnb_prio" in d else ""
    crit(name, None, f"n={d['n']} r/gNB {d['reward_per_gnb']:.3f} prio {d['prio_sla']:.1f}{extra} "
         f"mMTC share {d['mmtc_share_of_blocks']:.3f} mMTC-only {d['mmtc_only_seeds']} collapsed {d['collapsed']}", "REPORT")


def part_a(out):
    n, ring = 7, "m80/A_ep900_n7_ring"
    ax = seeds_of("m79/ep900_n7_ring", "axiom2", S15)
    b900 = {b: seeds_of(ring, b, S15) for b in BASE}
    b300 = {"single_agent_dqn": seeds_of("m80/A_ep300_n7_ring", "single_agent_dqn", S15),
            "independent_dqn": seeds_of("m64/n7_ring", "independent_dqn", S15),
            "mappo_tuned": seeds_of("m64/n7_ring", "mappo_tuned", S15)}
    if len(ax) < 15 or any(len(v) < 15 for v in b900.values()):
        crit("A not complete", False, {"axiom900": len(ax), **{b: len(v) for b, v in b900.items()}}, "NOT RUN")
        out["A"] = None
        return
    rp = lambda r: r["reward"] / n
    cp = lambda r: 100 * prio(r)
    t1 = holm_family({b: paired(ax, b900[b], cp) for b in BASE})
    t2 = holm_family({b: paired(ax, b900[b], rp) for b in BASE})
    crit("A1 AXIOM-900 keeps more compliance than each baseline at 900, Holm over 3",
         all(t["diff"] > 0 and t["p_holm"] < 0.05 for t in t1.values()), "; ".join(f"{k} {fmt(t)}" for k, t in t1.items()))
    crit("A2 AXIOM-900 earns more reward per gNB than each baseline at 900, Holm over 3",
         all(t["diff"] > 0 and t["p_holm"] < 0.05 for t in t2.values()), "; ".join(f"{k} {fmt(t)}" for k, t in t2.items()))
    summ = {"axiom2 900": describe(ax, n)}
    for b in BASE:
        summ[f"{b} 900"] = describe(b900[b], n)
        if b300[b]:
            summ[f"{b} 300"] = describe(b300[b], n)
            for nm, f in (("prio", cp), ("reward_per_gnb", rp)):
                crit(f"A reported: {b} 900 vs 300, {nm}", None, fmt(paired(b900[b], b300[b], f)), "REPORT")
    loc = seeds_of("m64/n7_ring", "rule_local", S15)
    for nm, f in (("prio", cp), ("reward_per_gnb", rp)):
        crit(f"A reported: AXIOM-900 vs stored local rule, {nm}", None, fmt(paired(ax, loc, f)), "REPORT")
    summ["rule_local (stored)"] = describe(loc, n)
    sa_old = seeds_of("m64/n7_ring", "single_agent_dqn", S15)
    crit("A reported: seeded DQN-SA 300 vs stored unseeded DQN-SA, prio", None,
         fmt(paired(b300["single_agent_dqn"], sa_old, cp)) if b300["single_agent_dqn"] else "missing", "REPORT")
    for k, d in summ.items():
        show(f"A {k}", d)
    out["A"] = {"A1": t1, "A2": t2, "summary": summ}


REPRO = [("m80/C_A_n7_ring", "m65_scaling/n7_ring", ("axiom2", "independent_dqn", "mappo_tuned")),
         ("m80/C_A_n19_hex", "m65_scaling/n19_hex", ("axiom2", "independent_dqn", "mappo_tuned")),
         ("m80/C_A_n37_hex", "m73/A_n37_hex", ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")),
         ("m80/C_B_n7_hex", "m64/n7_hex", ("axiom2", "independent_dqn", "mappo_tuned")),
         ("m80/C_B_n7_fully_connected", "m64/n7_fully_connected", ("axiom2", "independent_dqn", "mappo_tuned"))]


def part_c(out):
    rows, missing = [], []
    for fresh, stored, arms in REPRO:
        for a in arms:
            x, y = seeds_of(fresh, a, [900]).get(900), seeds_of(stored, a, [900]).get(900)
            if x is None or y is None:
                missing.append(f"{fresh}/{a}")
                continue
            d = max(abs(x["reward"] - y["reward"]), abs(x["blocks"] - y["blocks"]),
                    max(abs(x["sla"][k] - y["sla"][k]) for k in ("urllc", "embb", "mmtc")))
            rows.append({"run": f"{fresh}/{a}", "stored": f"{stored}/{a}", "rerun_reward": x["reward"],
                         "stored_reward": y["reward"], "max_abs_diff": d, "exact": d <= 1e-9})
            crit(f"C {fresh}/{a} reproduces {stored}", d <= 1e-9, f"rerun {x['reward']:.6f} stored {y['reward']:.6f} max diff {d:.3g}")
    if missing:
        crit("C runs not available", False, missing, "NOT RUN")
    crit("C every listed run reproduces exactly", not missing and all(r["exact"] for r in rows),
         f"{sum(r['exact'] for r in rows)} of {len(rows)} exact, {len(missing)} missing")
    out["C"] = {"rows": rows, "missing": missing}


def part_d(out):
    cell = "m80/D_envB_n19_hex_fresh"
    arms = ("axiom2",) + BASE + ("rule_static", "rule_accept_all", "rule_local_transfer")
    d = {a: seeds_of(cell, a, F15) for a in arms}
    if any(len(v) < 15 for v in d.values()):
        crit("D not complete", False, {a: len(v) for a, v in d.items()}, "NOT RUN")
        out["D"] = None
        return
    for a in arms:
        for s, r in d[a].items():
            r["pergnb"] = per_gnb(cell, a, s)
    assert all(r["pergnb"] is not None for v in d.values() for r in v.values()), "missing per-gNB sidecar"
    g = lambda r: r["pergnb"]
    t1 = holm_family({b: paired(d["axiom2"], d[b]) for b in BASE})
    t2 = holm_family({b: paired(d["axiom2"], d[b], g) for b in BASE})
    crit("D1 AXIOM earns more reward per step than each learned baseline, Holm over 3",
         all(t["diff"] > 0 and t["p_holm"] < 0.05 for t in t1.values()), "; ".join(f"{k} {fmt(t)}" for k, t in t1.items()))
    crit("D2 AXIOM keeps more per-gNB priority compliance than each learned baseline, Holm over 3",
         all(t["diff"] > 0 and t["p_holm"] < 0.05 for t in t2.values()), "; ".join(f"{k} {fmt(t)}" for k, t in t2.items()))
    t3 = paired(d["rule_static"], d["axiom2"])
    crit("D3 the static rule earns more reward per step than AXIOM on average", t3["diff"] > 0, fmt(t3))
    t4 = paired(d["rule_local_transfer"], d["axiom2"])
    crit("D4 the carried-over local rule beats AXIOM in at least 13 of 15 seeds", t4["wins"] >= 13, fmt(t4))
    summ = {a: describe(d[a], 19) for a in arms}
    for a, s in summ.items():
        show(f"D {a}", s)
    out["D"] = {"D1": t1, "D2": t2, "D3": t3, "D4": t4, "summary": summ}


def part_b(out):
    seeds = list(range(900, 908))
    new = seeds_of("m80/B_ep900_envB_n19_hex", "axiom2", seeds)
    old = seeds_of("m75/D_envB_n19_hex", "axiom2", seeds)
    st = seeds_of("m75/D_envB_n19_hex", "rule_static", seeds)
    if len(new) < 8:
        crit("B not complete", False, {"done": sorted(new)}, "NOT RUN")
        out["B"] = {"done": sorted(new)}
        if not new:
            return
    for cell, rows, arm in (("m80/B_ep900_envB_n19_hex", new, "axiom2"), ("m75/D_envB_n19_hex", old, "axiom2"),
                            ("m75/D_envB_n19_hex", st, "rule_static")):
        for s, r in rows.items():
            r["pergnb"] = per_gnb(cell, arm, s)
    common = sorted(new)
    oldc = {s: old[s] for s in common}
    stc = {s: st[s] for s in common}
    crit(f"B1 fewer mMTC-only seeds at 900 than at 300 episodes on seeds {common}",
         sum(mmtc_only(r) for r in new.values()) < sum(mmtc_only(r) for r in oldc.values()),
         f"{sum(mmtc_only(r) for r in new.values())} vs {sum(mmtc_only(r) for r in oldc.values())} of {len(common)}")
    g = lambda r: r["pergnb"]
    rep = {}
    for nm, ref in (("stored AXIOM 300", oldc), ("stored static rule", stc)):
        for m, f in (("reward", lambda r: r["reward"]), ("per-gNB prio", g)):
            t = paired(new, ref, f)
            rep[f"{nm} {m}"] = t
            crit(f"B reported: AXIOM 900 vs {nm}, {m}", None, fmt(t), "REPORT")
    out["B"] = {"done": common, "tests": rep, "summary": {"axiom2 900": describe(new, 19), "axiom2 300": describe(oldc, 19),
                                                          "rule_static": describe(stc, 19)}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = {}
    for f in (part_a, part_c, part_d, part_b):
        f(out)
    out["criteria"] = C
    json.dump(out, open(a.out, "w"), indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
