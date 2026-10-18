#!/usr/bin/env python3
"""M67 amendment 1 confirmatory analysis: Env B N=7, seeds 8100-8109.

Decisive if AXIOM v2 MLP beats the seeded single-agent DQN and the independent
DQN on reward under every layout, all 6 comparisons at Holm-adjusted p < 0.05.
The same comparisons for AXIOM v2 with GAT are reported, not predicted.

Usage: m67_confirm_analysis.py --out experiments/results/m67_confirm_envB/analysis.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import holm, mean, paired, prio, seeds_of  # noqa: E402

SEEDS = list(range(8100, 8110))
LAYOUTS = ("fully_connected", "ring", "hex")
BASE = ("single_agent_dqn", "independent_dqn")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = {}
    for ref in ("axiom2_mlp", "axiom2"):
        tests, summ = {}, {}
        for t in LAYOUTS:
            d = {k: seeds_of(f"m67_confirm_envB/B_n7_{t}", k, SEEDS) for k in (ref,) + BASE}
            summ[t] = {k: {"n": len(v), "reward": mean(v), "prio": mean(v, prio)} for k, v in d.items()}
            for b in BASE:
                tests[f"{t}/{b}"] = paired(d[ref], d[b])
        h = holm({k: v["p"] for k, v in tests.items()})
        for k in tests:
            tests[k]["p_holm"] = h[k]
        complete = all(v["n"] == 10 for v in tests.values())
        decisive = complete and all(v["diff"] > 0 and v["p_holm"] < 0.05 for v in tests.values())
        out[ref] = {"summary": summ, "tests": tests, "complete": complete, "all_six_hold": decisive}
        tag = "PREDICTION" if ref == "axiom2_mlp" else "REPORTED"
        print(f"== {tag} {ref}: all six at Holm p<0.05 = {decisive} (complete={complete})")
        for k, v in tests.items():
            print(f"   {k:34s} diff {v['diff']:+.3f}  W/T/L {v['wins']}/{v['ties']}/{v['losses']}  p {v['p']:.3g}  p_holm {v['p_holm']:.3g}")
        for t in LAYOUTS:
            print(f"   {t:16s} " + "  ".join(f"{k} {summ[t][k]['reward']:.3f}/{100 * summ[t][k]['prio']:.1f}%" for k in summ[t]))
    gm = {t: paired(seeds_of(f"m67_confirm_envB/B_n7_{t}", "axiom2_mlp", SEEDS),
                    seeds_of(f"m67_confirm_envB/B_n7_{t}", "axiom2", SEEDS)) for t in LAYOUTS}
    out["mlp_minus_gat"] = gm
    print("   MLP minus GAT: " + "  ".join(f"{t} {v['diff']:+.3f} (p {v['p']:.2g})" for t, v in gm.items()))
    json.dump(out, open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
