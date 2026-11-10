#!/usr/bin/env python3
"""M104 analysis (docs/PAPER5_M104_preregistration.md), written after that commit and before any M104 result was read.
Selected-checkpoint evaluations are read from eval/ with m66_verify's reader; last-checkpoint evaluations from
eval_last/ with the same reader function. Run from framework/:
  ../venv/bin/python ../experiments/scripts/m104_analysis.py --out ../experiments/results/m104/analysis.json
"""
import argparse
import json
import os
import sys

import numpy as np
from scipy.stats import binomtest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import ROOT, holm, paired, prio, read, seeds_of  # noqa: E402
sys.path.insert(0, "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures")
from axiom_style import wilson  # noqa: E402

SEEDS = list(range(9940, 9960))
SETTINGS = ("A_n37_hex", "B_n7_ring")
R = lambda r: r["reward"]
P = lambda r: 100 * prio(r)


def ci(d, seed=0):
    d = np.asarray(d, float)
    m = d[np.random.default_rng(seed).integers(0, len(d), size=(10000, len(d)))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def last_rows(cell, arm, seeds):
    out = {}
    for s in seeds:
        p = f"{ROOT}/{cell}/{arm}/seed{s}/eval_last/omega_log.jsonl"
        if os.path.exists(p) or os.path.exists(p + ".gz"):
            out[s] = read(p)
    return out


def family(get):
    t = {}
    for st in SETTINGS:
        A, M = get(f"m104/{st}/gat"), get(f"m104/{st}/mlp")
        for m, f in (("reward", R), ("compliance", P)):
            x = paired(A, M, f)
            d = [f(A[k]) - f(M[k]) for k in sorted(set(A) & set(M))]
            x["ci"], x["median"] = ci(d), float(np.median(d))
            t[f"{st}|{m}"] = x
    h = holm({k: v["p"] for k, v in t.items()})
    for k, v in t.items():
        v["p_holm"] = h[k]
        v["verdict"] = ("attention ahead" if v["diff"] > 0 else "MLP ahead") if h[k] < 0.05 else "within chance"
    return t


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    sel = lambda cell: seeds_of(cell, "axiom2", SEEDS)
    last = lambda cell: last_rows(cell, "axiom2", SEEDS)
    g1, g2 = family(sel), family(last)
    g3 = {}
    for st in SETTINGS:
        g3[st] = {}
        for v in ("gat", "mlp"):
            S_, L_ = sel(f"m104/{st}/{v}"), last(f"m104/{st}/{v}")
            ks, kl = sum(r["collapsed"] for r in S_.values()), sum(r["collapsed"] for r in L_.values())
            only_last = sum(1 for s in S_ if s in L_ and L_[s]["collapsed"] and not S_[s]["collapsed"])
            only_sel = sum(1 for s in S_ if s in L_ and S_[s]["collapsed"] and not L_[s]["collapsed"])
            g3[st][v] = {"n": len(S_), "collapsed_selected": int(ks), "collapsed_last": int(kl),
                         "wilson_selected_pct": [100 * x for x in wilson(int(ks), len(S_))],
                         "wilson_last_pct": [100 * x for x in wilson(int(kl), len(L_))],
                         "discordant_last_only": only_last, "discordant_selected_only": only_sel,
                         "mcnemar_exact_p": float(binomtest(min(only_last, only_sel), only_last + only_sel, 0.5).pvalue) if only_last + only_sel else 1.0}
    artefact = {}
    for k, v in g2.items():
        if v["verdict"] == "MLP ahead":
            artefact[k] = g1[k]["verdict"] in ("within chance", "attention ahead")
    beats = any(v["verdict"] == "attention ahead" for k, v in g1.items() if k.endswith("|reward")) and \
        not any(v["verdict"] == "MLP ahead" for v in g1.values())
    out = {"G1_selected": g1, "G2_last": g2, "G3_collapse": g3,
           "checkpointing_artefact_where_mlp_led_with_last": artefact, "attention_beats_mlp_under_selection": bool(beats)}
    json.dump(out, open(a.out, "w"), indent=1, default=float)
    for name, t in (("G1 selected", g1), ("G2 last", g2)):
        for k, v in t.items():
            print(f"{name:11s} {k:22s} diff={v['diff']:+.3f} ci=[{v['ci'][0]:+.3f},{v['ci'][1]:+.3f}] p={v['p']:.3g} holm={v['p_holm']:.3g} "
                  f"W/T/L={v['wins']}/{v['ties']}/{v['losses']} {v['verdict']}")
    print("G3", json.dumps(g3))
    print("artefact:", artefact, "attention beats MLP under selection:", out["attention_beats_mlp_under_selection"])


if __name__ == "__main__":
    main()
