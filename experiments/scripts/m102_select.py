#!/usr/bin/env python3
"""M102 selection (docs/PAPER5_M102_preregistration.md), written after that commit and before any pilot result was
read. In each family, the variant with the highest mean over the two pilot settings of the mean reward per gNB per
step on pilot seeds 2100 to 2103; exact ties go to the current configuration (gat, mlp).
Run from framework/: ../venv/bin/python ../experiments/scripts/m102_select.py --out ../experiments/results/m102/selection.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import seeds_of  # noqa: E402
from m102_variants import FAMILY  # noqa: E402

PILOT = list(range(2100, 2104))
SETTINGS = {"B_n7_ring": 7, "A_n37_hex": 37}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    table, sel = {}, {}
    for fam, variants in FAMILY.items():
        scores = {}
        for v in variants:
            per = {}
            for s, n in SETTINGS.items():
                rows = seeds_of(f"m102/{s}/{v}", "axiom2", PILOT)
                assert len(rows) == len(PILOT), (s, v, len(rows))
                per[s] = {"reward_per_gnb": float(np.mean([r["reward"] / n for r in rows.values()])),
                          "collapsed": int(sum(r["collapsed"] for r in rows.values()))}
            scores[v] = float(np.mean([per[s]["reward_per_gnb"] for s in SETTINGS]))
            table[v] = {"family": fam, "settings": per, "score": scores[v]}
        best = max(scores.values())
        winners = [v for v in variants if scores[v] == best]
        sel[fam] = variants[0] if variants[0] in winners else winners[0]
    out = {"selected": sel, "pilot": table, "rule": "max mean over settings of mean reward per gNB per step; ties to the current configuration"}
    json.dump(out, open(a.out, "w"), indent=1)
    for v, t in table.items():
        print(f"{t['family']:9s} {v:10s} score {t['score']:.4f}  " + "  ".join(f"{s} {d['reward_per_gnb']:.4f} (coll {d['collapsed']})" for s, d in t["settings"].items()))
    print("selected:", sel)


if __name__ == "__main__":
    main()
