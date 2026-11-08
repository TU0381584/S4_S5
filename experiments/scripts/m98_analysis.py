#!/usr/bin/env python3
"""M98 analysis (docs/PAPER5_M98_preregistration.md, commit d800a0a6), written after that commit and before any M98
result was read. Reads every log with m66_verify's independent reader and judges each pre-registered criterion as
HOLDS or FAILS; nothing is dropped when it fails.

Usage: m98_analysis.py --out experiments/results/m98/analysis.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/plots")
from m66_verify import holm, paired, seeds_of  # noqa: E402

A_SEEDS, B_SEEDS, C_SEEDS = list(range(9500, 9540)), list(range(9600, 9630)), list(range(9700, 9720))
S15 = list(range(900, 912)) + [1000, 1001, 1002]
LOADS = ("load_1.10", "load_1.15", "load_1.20")
R = lambda r: r["reward"]


def ci(d, seed=0):
    d = np.asarray(d, float)
    m = d[np.random.default_rng(seed).integers(0, len(d), size=(10000, len(d)))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def comp(a, b):
    """a minus b on reward per step, paired by seed."""
    t = paired(a, b, R)
    common = sorted(set(a) & set(b))
    t["ci"] = ci([a[s]["reward"] - b[s]["reward"] for s in common])
    t["collapsed_a"] = int(sum(a[s]["collapsed"] for s in common)); t["collapsed_b"] = int(sum(b[s]["collapsed"] for s in common))
    return t


def keyed(rows, tag):
    return {f"{tag}:{s}": r for s, r in rows.items()}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    out, crit = {}, []

    # A: Env A, 3 gNBs, AXIOM against the seeded DQN-SA
    ax, sa = seeds_of("m98/A_n3", "axiom2", A_SEEDS), seeds_of("m98/A_n3", "single_agent_dqn", A_SEEDS)
    a1 = comp(ax, sa)
    ax0, sa0 = seeds_of("m66d_fresh/D1_A_n3", "axiom2", list(range(4000, 4040))), seeds_of("m66d_fresh/D1_A_n3", "single_agent_dqn", list(range(4000, 4040)))
    a2 = comp({**keyed(ax, "m98"), **keyed(ax0, "m66d")}, {**keyed(sa, "m98"), **keyed(sa0, "m66d")})
    out["A"] = {"A1_fresh40": a1, "A2_pooled80": a2}
    crit.append({"id": "A1", "criterion": "AXIOM beats DQN-SA, Env A 3 gNBs, 40 fresh seeds", "n": a1["n"],
                 "verdict": "HOLDS" if a1["diff"] > 0 and a1["p"] < 0.05 else "FAILS"})
    crit.append({"id": "A2", "criterion": "AXIOM beats DQN-SA, Env A 3 gNBs, 80 fresh seeds pooled", "n": a2["n"],
                 "verdict": "HOLDS" if a2["diff"] > 0 and a2["p"] < 0.05 else "FAILS"})

    # B: Env B, 3 gNBs, load shift on the fresh checkpoints
    B = {L: {arm: seeds_of(f"m98/B_shift/n3/{L}", arm, B_SEEDS) for arm in ("axiom2", "mappo_tuned", "single_agent_dqn", "independent_dqn", "rule_local")}
         for L in ("nominal",) + LOADS}
    b1 = {f"{b}|{L}": comp(B[L]["axiom2"], B[L][b]) for b in ("mappo_tuned", "single_agent_dqn", "independent_dqn") for L in LOADS}
    h1 = holm({k: v["p"] for k, v in b1.items()})
    for k in b1:
        b1[k]["p_holm"] = h1[k]
    b2 = {L: comp(B[L]["axiom2"], B[L]["rule_local"]) for L in LOADS}
    h2 = holm({k: v["p"] for k, v in b2.items()})
    for k in b2:
        b2[k]["p_holm"] = h2[k]
    b3 = comp(B["nominal"]["axiom2"], B["nominal"]["rule_local"])
    out["B"] = {"B1": b1, "B2": b2, "B3_nominal": b3,
                "tuned_rule": json.load(open("/home/kmanojp/oranslice_rig/experiments/results/m98/B_n3/rule_local_selection.json"))["selected"]}
    crit.append({"id": "B1", "criterion": "AXIOM out-earns MAPPO, DQN-SA and DQN-I at 110-120% load, 3 gNBs, all 9 at Holm p<0.05",
                 "n": min(v["n"] for v in b1.values()), "verdict": "HOLDS" if all(v["diff"] > 0 and v["p_holm"] < 0.05 for v in b1.values()) else "FAILS"})
    crit.append({"id": "B2", "criterion": "AXIOM out-earns the tuned rule at 110-120% load, 3 gNBs, all 3 at Holm p<0.05",
                 "n": min(v["n"] for v in b2.values()), "verdict": "HOLDS" if all(v["diff"] > 0 and v["p_holm"] < 0.05 for v in b2.values()) else "FAILS"})

    # C: Env B, 7 gNBs ring, the MLP variant against AXIOM
    cx, cm = seeds_of("m98/C_n7_ring", "axiom2", C_SEEDS), seeds_of("m98/C_n7_ring", "axiom2_mlp", C_SEEDS)
    c1 = comp(cm, cx)
    px = {**keyed(cx, "m98"), **keyed(seeds_of("m66_fresh/B_n7_ring", "axiom2", list(range(3000, 3010))), "m66"),
          **keyed(seeds_of("m67_confirm_envB/B_n7_ring", "axiom2", list(range(8100, 8110))), "m67")}
    pm = {**keyed(cm, "m98"), **keyed(seeds_of("m66_fresh/B_n7_ring", "axiom2_mlp", list(range(3000, 3010))), "m66"),
          **keyed(seeds_of("m67_confirm_envB/B_n7_ring", "axiom2_mlp", list(range(8100, 8110))), "m67")}
    c2 = comp(pm, px)
    out["C"] = {"C1_fresh20": c1, "C2_pooled40": c2}
    crit.append({"id": "C1", "criterion": "MLP variant ahead of AXIOM, Env B 7 ring, 20 fresh seeds", "n": c1["n"],
                 "verdict": "HOLDS" if c1["diff"] > 0 and c1["p"] < 0.05 else "FAILS"})
    crit.append({"id": "C2", "criterion": "MLP variant ahead of AXIOM, Env B 7 ring, 40 fresh seeds pooled", "n": c2["n"],
                 "verdict": "HOLDS" if c2["diff"] > 0 and c2["p"] < 0.05 else "FAILS"})

    # D: Env B, 19 gNBs, static rule against AXIOM past the tuning load, reported and fresh seeds pooled
    from paper5_fig_superiority import shift_row
    d1 = {}
    for L in LOADS:
        rep_ax = {f"rep:{s}": shift_row("m76/b1_shift_n19", L, "axiom2", s) for s in S15}       # full records, as read from the logs
        rep_st = {f"rep:{s}": shift_row("m76/b1_shift_n19", L, "rule_static", s) for s in S15}
        fr_ax = keyed(seeds_of(f"m96/C_fresh_shift/n19_hex/{L}", "axiom2", list(range(7000, 7015))), "fresh")
        fr_st = keyed(seeds_of(f"m96/C_fresh_shift/n19_hex/{L}", "rule_static", list(range(7000, 7015))), "fresh")
        d1[L] = comp({**rep_st, **fr_st}, {**rep_ax, **fr_ax})
    hd = holm({k: v["p"] for k, v in d1.items()})
    for k in d1:
        d1[k]["p_holm"] = hd[k]
    out["D"] = {"D1": d1}
    crit.append({"id": "D1", "criterion": "static rule ahead of AXIOM at 110-120% load, Env B 19 gNBs, 30 seeds pooled, all 3 at Holm p<0.05",
                 "n": min(v["n"] for v in d1.values()), "verdict": "HOLDS" if all(v["diff"] > 0 and v["p_holm"] < 0.05 for v in d1.values()) else "FAILS"})

    out["criteria"] = crit
    json.dump(out, open(a.out, "w"), indent=1, default=float)
    for c in crit:
        print(f"{c['id']:3s} {c['verdict']:6s} n={c['n']:3d}  {c['criterion']}")


if __name__ == "__main__":
    main()
