#!/usr/bin/env python3
"""M101 analysis (docs/PAPER5_M101_preregistration.md), written after that commit and before any M101 result was read.
Run from framework/: ../venv/bin/python ../experiments/scripts/m101_analysis.py --out ../experiments/results/m101/analysis.json"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import seeds_of  # noqa: E402
from m100_analysis import P, R, arm_summary, fam  # noqa: E402   (same tests, CIs and Holm as M100)

F_SEEDS, M100_SEEDS = list(range(9960, 9980)), list(range(8000, 8020))


def keyed(rows, tag):
    return {f"{tag}:{s}": r for s, r in rows.items()}


def verdicts(t):
    for v in t.values():
        v["verdict"] = ("MLP ahead" if v["diff"] > 0 else "AXIOM ahead") if v["p_holm"] < 0.05 else "within chance"
    return t


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    ax, ml = seeds_of("m101/A_n37_hex", "axiom2", F_SEEDS), seeds_of("m101/A_n37_hex", "axiom2_mlp", F_SEEDS)
    ax0, ml0 = seeds_of("m96/A_fresh/n37_hex", "axiom2", M100_SEEDS), seeds_of("m100/A_n37_hex", "axiom2_mlp", M100_SEEDS)
    f1 = verdicts(fam(ml, ax))
    pa, pm = {**keyed(ax, "m101"), **keyed(ax0, "m100")}, {**keyed(ml, "m101"), **keyed(ml0, "m100")}
    f2 = verdicts(fam(pm, pa))
    out = {"F1_fresh20_mlp_minus_axiom": f1, "F2_pooled40_mlp_minus_axiom": f2,
           "arms_fresh20": {"axiom2": arm_summary(ax), "axiom2_mlp": arm_summary(ml)},
           "arms_pooled40": {"axiom2": arm_summary(pa), "axiom2_mlp": arm_summary(pm)}}
    out["criteria"] = [{"id": k, "n": min(v["n"] for v in t.values()), "verdict": "; ".join(f"{m} {v['verdict']}" for m, v in t.items())}
                       for k, t in (("F1", f1), ("F2", f2))]
    json.dump(out, open(a.out, "w"), indent=1, default=float)
    for c in out["criteria"]:
        print(c["id"], "n =", c["n"], c["verdict"])


if __name__ == "__main__":
    main()
