#!/usr/bin/env python3
"""M92 analysis: zero-shot cluster-size transfer (docs/PAPER5_M92_preregistration.md, commit 2b1dae5).

Reads every evaluation log with the independent reader of m66_verify.py and judges each
pre-registered criterion as HOLDS or FAILS. Nothing is dropped when it fails.

Usage: m92_analysis.py --out experiments/results/m92/analysis.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import ROOT, S15, holm, paired, prio, seeds_of  # noqa: E402

SEEDS = S15
RULES_A = {19: ("m70/R1/A_n19_hex", "m75/B_acceptall/n19"), 37: ("m73/A_n37_hex", "m75/B_acceptall/n37")}
TRAINED_A = {("hex", 19): "m65_scaling/n19_hex", ("hex", 37): "m73/A_n37_hex",
             ("ring", 19): "m65_scaling/n19_ring", ("ring", 37): "m73/A_n37_ring",
             ("fully_connected", 19): "m65_scaling/n19_fully_connected", ("fully_connected", 37): "m73/A_n37_fully_connected"}  # Amendment 1
B_REF = "m75/D_envB_n19_hex"
rng = np.random.default_rng(0)


def per_gnb(cell, arm, s):
    p = f"{ROOT}/{cell}/{arm}/seed{s}/eval/per_gnb_sla.json"
    if not os.path.exists(p):
        return None
    m = json.load(open(p))["mean_compliance"]
    return 100 * 0.5 * (m["urllc"] + m["embb"])


def arm_rows(cell, arm, n, env):
    """seed -> dict(prio, prio_cluster, reward_per_gnb, collapsed)."""
    out = {}
    for s, r in seeds_of(cell, arm, SEEDS).items():
        row = {"prio_cluster": 100 * prio(r), "reward_per_gnb": r["reward"] / n, "collapsed": bool(r["collapsed"])}
        row["prio_per_gnb"] = per_gnb(cell, arm, s)
        row["prio"] = row["prio_per_gnb"] if env == "B" else row["prio_cluster"]
        out[s] = row
    return out


def boot_ci(d):
    d = np.asarray(d, float)
    idx = rng.integers(0, len(d), size=(10000, len(d)))
    m = d[idx].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def compare(a, b, key):
    t = paired(a, b, lambda r: r[key])
    common = sorted(set(a) & set(b))
    t["ci"] = boot_ci([a[s][key] - b[s][key] for s in common])
    return t


def summary(rows, key):
    v = [r[key] for r in rows.values() if r[key] is not None]
    return {"n": len(rows), "mean": float(np.mean(v)), "ci": boot_ci(v), "collapsed": int(sum(r["collapsed"] for r in rows.values()))}


def cell_A(topo, n):
    c = f"m92/A_{topo}_n{n}"
    st, aa = RULES_A[n]
    arms = {"AXIOM-7to%d" % n: arm_rows(c, "axiom2_transfer", n, "A"),
            "MAPPO-7to%d" % n: arm_rows(c, "mappo_tuned_transfer", n, "A"),
            "AXIOM trained at %d" % n: arm_rows(TRAINED_A[(topo, n)], "axiom2", n, "A"),
            "static rule": arm_rows(st, "rule_static", n, "A"),
            "accept-all": arm_rows(aa, "rule_accept_all", n, "A")}
    return arms


def cell_B():
    c = "m92/B_hex_n19"
    return {"AXIOM-7to19": arm_rows(c, "axiom2_transfer", 19, "B"),
            "MLP-7to19": arm_rows(c, "axiom2_mlp_transfer", 19, "B"),
            "MAPPO-7to19": arm_rows(c, "mappo_tuned_transfer", 19, "B"),
            "AXIOM trained at 19": arm_rows(B_REF, "axiom2", 19, "B"),
            "static rule": arm_rows(B_REF, "rule_static", 19, "B"),
            "accept-all": arm_rows(B_REF, "rule_accept_all", 19, "B")}


def family(tests):
    h = holm({k: v["p"] for k, v in tests.items()})
    for k, v in tests.items():
        v["p_holm"] = h[k]
    return tests


def judge_T1(t):
    return "HOLDS" if t["diff"] > 0 and t["p_holm"] < 0.05 else "FAILS"


def judge_T2(t):
    holds = t["diff"] >= 0 and not (t["diff"] < 0 and t["p_holm"] < 0.05)
    return "HOLDS" if holds else "FAILS"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = {"cells": {}, "families": {}, "criteria": [], "flags": [], "descriptive": {}}

    def crit(name, verdict, detail):
        out["criteria"].append({"criterion": name, "verdict": verdict, "detail": detail})
        print(f"{verdict:6s} {name}: {detail}")

    for topo, label in (("hex", "primary, Env A hex"), ("ring", "secondary, Env A ring"),
                        ("fully_connected", "secondary, Env A fully-connected (Amendment 1)")):
        fam = {}
        for n in (19, 37):
            arms = cell_A(topo, n)
            out["cells"][f"A_{topo}_n{n}"] = {k: {key: summary(v, key) for key in ("prio", "reward_per_gnb")} for k, v in arms.items()}
            ax, mp = arms[f"AXIOM-7to{n}"], arms[f"MAPPO-7to{n}"]
            fam[f"H-T1 {n}"] = compare(ax, arms["accept-all"], "prio")
            fam[f"H-T2 {n}"] = compare(ax, mp, "prio")
            d = out["descriptive"].setdefault(f"A_{topo}_n{n}", {})
            for key in ("prio", "reward_per_gnb"):
                d[f"H-T3 AXIOM-7to{n} minus AXIOM trained at {n}, {key}"] = compare(ax, arms[f"AXIOM trained at {n}"], key)
                d[f"AXIOM-7to{n} minus static rule, {key}"] = compare(ax, arms["static rule"], key)
                d[f"MAPPO-7to{n} minus static rule, {key}"] = compare(mp, arms["static rule"], key)
                d[f"MAPPO-7to{n} minus accept-all, {key}"] = compare(mp, arms["accept-all"], key)
                d[f"AXIOM-7to{n} minus accept-all, {key}"] = compare(ax, arms["accept-all"], key)
                d[f"AXIOM-7to{n} minus MAPPO-7to{n}, {key}"] = compare(ax, mp, key)
            if n == 37:
                below = summary(ax, "prio")["mean"] < summary(arms["accept-all"], "prio")["mean"]
                if below:
                    out["flags"].append(f"TRANSFER-LIMITATION ({topo})")
                crit(f"T-S1 check ({label})", "FLAG" if below else "clear",
                     f"AXIOM-7to37 mean priority SLA {summary(ax, 'prio')['mean']:.2f}% against accept-all {summary(arms['accept-all'], 'prio')['mean']:.2f}%")
        family(fam)
        out["families"][label] = fam
        for k, t in fam.items():
            v = judge_T1(t) if k.startswith("H-T1") else judge_T2(t)
            extra = "" if k.startswith("H-T1") else (", AXIOM significantly ahead" if t["diff"] > 0 and t["p_holm"] < 0.05 else ", AXIOM not significantly ahead")
            crit(f"{k} ({label})", v, f"diff {t['diff']:+.2f} points, CI [{t['ci'][0]:.2f}, {t['ci'][1]:.2f}], "
                 f"{t['wins']}/{t['ties']}/{t['losses']} W/T/L, p {t['p']:.2g}, Holm p {t['p_holm']:.2g}{extra}")

    arms = cell_B()
    out["cells"]["B_hex_n19"] = {k: {key: summary(v, key) for key in ("prio", "prio_cluster", "reward_per_gnb")} for k, v in arms.items()}
    ax, ml, mp = arms["AXIOM-7to19"], arms["MLP-7to19"], arms["MAPPO-7to19"]
    fam = family({"H-T1 19": compare(ax, arms["accept-all"], "prio"), "H-T2 19": compare(ax, mp, "prio")})
    out["families"]["secondary, Env B hex"] = fam
    crit("H-T1 19 (secondary, Env B hex)", judge_T1(fam["H-T1 19"]),
         f"diff {fam['H-T1 19']['diff']:+.2f} points per-gNB, Holm p {fam['H-T1 19']['p_holm']:.2g}")
    t2 = fam["H-T2 19"]
    crit("H-T2 19 (secondary, Env B hex)", judge_T2(t2),
         f"diff {t2['diff']:+.2f} points per-gNB, Holm p {t2['p_holm']:.2g}" + (", AXIOM significantly ahead" if t2["diff"] > 0 and t2["p_holm"] < 0.05 else ""))
    t4 = compare(ax, ml, "prio")
    t4r = compare(ax, ml, "reward_per_gnb")
    out["families"]["H-T4, Env B hex"] = {"prio_per_gnb": t4, "reward_per_gnb": t4r}
    if t4["p"] < 0.05 and t4["diff"] < 0:
        out["flags"].append("T-S2: MLP-7to19 beats GAT-7to19")
    if t4["p"] < 0.05 and t4["diff"] > 0:
        out["flags"].append("ATTENTION-TRANSFER (T-S3)")
    crit("H-T4 GAT-7to19 minus MLP-7to19 (Env B hex, reported either way)", "REPORT",
         f"per-gNB priority SLA {t4['diff']:+.2f} points, CI [{t4['ci'][0]:.2f}, {t4['ci'][1]:.2f}], p {t4['p']:.2g}; "
         f"reward per gNB {t4r['diff']:+.3f}, p {t4r['p']:.2g}")
    d = out["descriptive"].setdefault("B_hex_n19", {})
    for key in ("prio", "prio_cluster", "reward_per_gnb"):
        d[f"H-T3 AXIOM-7to19 minus AXIOM trained at 19, {key}"] = compare(ax, arms["AXIOM trained at 19"], key)
        for o in ("static rule", "accept-all"):
            d[f"AXIOM-7to19 minus {o}, {key}"] = compare(ax, arms[o], key)
            d[f"MAPPO-7to19 minus {o}, {key}"] = compare(mp, arms[o], key)
            d[f"MLP-7to19 minus {o}, {key}"] = compare(ml, arms[o], key)
    for cell, ds in out["descriptive"].items():
        for k, t in ds.items():
            if k.startswith("H-T3"):
                crit(f"{k} ({cell}, descriptive)", "REPORT", f"{t['diff']:+.3f}, CI [{t['ci'][0]:.3f}, {t['ci'][1]:.3f}], n {t['n']}")
    print("flags:", out["flags"] or "none")
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
