#!/usr/bin/env python3
"""M99 analysis (docs/PAPER5_M99_preregistration.md), written after that commit and before any M99 result was read.
Reads every log with m66_verify's independent reader and judges each pre-registered criterion; nothing is dropped
when it fails. Run from framework/: ../venv/bin/python ../experiments/scripts/m99_analysis.py --out ../experiments/results/m99/analysis.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import holm, paired, prio, seeds_of  # noqa: E402
sys.path.insert(0, "/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures")
from axiom_style import wilson  # noqa: E402

A_SEEDS, B_SEEDS, C_SEEDS = list(range(9800, 9820)), list(range(9900, 9940)), list(range(9840, 9860))
R = lambda r: r["reward"]
P = lambda r: 100 * prio(r)
LOADS = ("load_1.10", "load_1.15", "load_1.20")


def ci(d, seed=0):
    d = np.asarray(d, float)
    m = d[np.random.default_rng(seed).integers(0, len(d), size=(10000, len(d)))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def comp(a, b, f=R):
    """a minus b, paired by seed, with the bootstrap CI and median of the paired differences and collapsed runs."""
    t = paired(a, b, f)
    common = sorted(set(a) & set(b))
    d = [f(a[s]) - f(b[s]) for s in common]
    t["ci"] = ci(d); t["median"] = float(np.median(d))
    t["collapsed_a"] = int(sum(a[s]["collapsed"] for s in common)); t["collapsed_b"] = int(sum(b[s]["collapsed"] for s in common))
    return t


def keyed(rows, tag):
    return {f"{tag}:{s}": r for s, r in rows.items()}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    out, crit = {}, []

    # A: per-slice heads at 19 gNBs, ring, Env A
    ax, sh = seeds_of("m99/A_n19_ring", "axiom2", A_SEEDS), seeds_of("m99/A_sharedhead_n19_ring", "axiom2", A_SEEDS)
    a1 = {"prio": comp(ax, sh, P), "reward": comp(ax, sh, R)}
    h = holm({k: v["p"] for k, v in a1.items()})
    for k in a1:
        a1[k]["p_holm"] = h[k]
    coll = {nm: {"collapsed": int(sum(r["collapsed"] for r in rows.values())), "n": len(rows),
                 "wilson_pct": [100 * x for x in wilson(int(sum(r["collapsed"] for r in rows.values())), len(rows))],
                 "prio_mean": float(np.mean([P(r) for r in rows.values()]))} for nm, rows in (("axiom2", ax), ("sharedhead", sh))}
    out["A"] = {"A1": a1, "collapse": coll}
    crit.append({"id": "A1", "criterion": "AXIOM ahead of the shared-head variant on compliance and reward, Env A 19 gNBs ring, 20 fresh seeds, Holm",
                 "n": min(v["n"] for v in a1.values()), "verdict": "HOLDS" if all(v["diff"] > 0 and v["p_holm"] < 0.05 for v in a1.values()) else "FAILS"})

    # B: AXIOM against the seeded DQN-SA, Env A, 3 gNBs
    bx, bs = seeds_of("m99/B_A_n3", "axiom2", B_SEEDS), seeds_of("m99/B_A_n3", "single_agent_dqn", B_SEEDS)
    b1 = comp(bx, bs)
    px = {**keyed(bx, "m99"), **keyed(seeds_of("m98/A_n3", "axiom2", list(range(9500, 9540))), "m98"),
          **keyed(seeds_of("m66d_fresh/D1_A_n3", "axiom2", list(range(4000, 4040))), "m66d")}
    ps = {**keyed(bs, "m99"), **keyed(seeds_of("m98/A_n3", "single_agent_dqn", list(range(9500, 9540))), "m98"),
          **keyed(seeds_of("m66d_fresh/D1_A_n3", "single_agent_dqn", list(range(4000, 4040))), "m66d")}
    b2 = comp(px, ps)
    out["B"] = {"B1_fresh40": b1, "B2_pooled120": b2}
    crit.append({"id": "B1", "criterion": "AXIOM beats DQN-SA, Env A 3 gNBs, 40 fresh seeds", "n": b1["n"],
                 "verdict": "HOLDS" if b1["diff"] > 0 and b1["p"] < 0.05 else "FAILS"})
    crit.append({"id": "B2", "criterion": "AXIOM beats DQN-SA, Env A 3 gNBs, 120 fresh seeds pooled, p<0.05 and CI of the mean above zero",
                 "n": b2["n"], "verdict": "HOLDS" if b2["diff"] > 0 and b2["p"] < 0.05 and b2["ci"][0] > 0 else "FAILS"})

    # C: MLP variant against AXIOM, Env B, 7 gNBs, hex
    cx, cm = seeds_of("m99/C_n7_hex", "axiom2", C_SEEDS), seeds_of("m99/C_n7_hex", "axiom2_mlp", C_SEEDS)
    c1 = comp(cm, cx)
    c2 = comp({**keyed(cm, "m99"), **keyed(seeds_of("m67_confirm_envB/B_n7_hex", "axiom2_mlp", list(range(8100, 8110))), "m67")},
              {**keyed(cx, "m99"), **keyed(seeds_of("m67_confirm_envB/B_n7_hex", "axiom2", list(range(8100, 8110))), "m67")})
    out["C"] = {"C1_fresh20": c1, "C2_pooled30": c2}
    crit.append({"id": "C1", "criterion": "MLP variant ahead of AXIOM, Env B 7 hex, 20 fresh seeds", "n": c1["n"],
                 "verdict": "HOLDS" if c1["diff"] > 0 and c1["p"] < 0.05 else "FAILS"})
    crit.append({"id": "C2", "criterion": "MLP variant ahead of AXIOM, Env B 7 hex, 30 fresh seeds pooled", "n": c2["n"],
                 "verdict": "HOLDS" if c2["diff"] > 0 and c2["p"] < 0.05 else "FAILS"})

    # D: pooled load shift at 3 gNBs, Env B, M96 (905-929) and M98 (9600-9629)
    d1 = {}
    for b in ("mappo_tuned", "single_agent_dqn", "independent_dqn"):
        for L in LOADS:
            A_ = {**keyed(seeds_of(f"m96/B_shift/n3/{L}", "axiom2", list(range(905, 930))), "m96"),
                  **keyed(seeds_of(f"m98/B_shift/n3/{L}", "axiom2", list(range(9600, 9630))), "m98")}
            B_ = {**keyed(seeds_of(f"m96/B_shift/n3/{L}", b, list(range(905, 930))), "m96"),
                  **keyed(seeds_of(f"m98/B_shift/n3/{L}", b, list(range(9600, 9630))), "m98")}
            d1[f"{b}|{L}"] = comp(A_, B_)
    hd = holm({k: v["p"] for k, v in d1.items()})
    for k in d1:
        d1[k]["p_holm"] = hd[k]
        d1[k]["verdict"] = ("AXIOM ahead" if d1[k]["diff"] > 0 else "AXIOM behind") if hd[k] < 0.05 else "within chance"
    out["D"] = {"D1": d1}
    crit.append({"id": "D1", "criterion": "AXIOM against MAPPO, DQN-SA, DQN-I past the tuning load, Env B 3 gNBs, 55 seeds pooled, 9 tests, Holm (reported per test)",
                 "n": min(v["n"] for v in d1.values()), "verdict": "; ".join(f"{k} {v['verdict']}" for k, v in d1.items())})

    out["criteria"] = crit
    json.dump(out, open(a.out, "w"), indent=1, default=float)
    for c in crit:
        print(f"{c['id']:3s} n={c['n']:3d}  {c['verdict']}  | {c['criterion']}")


if __name__ == "__main__":
    main()
