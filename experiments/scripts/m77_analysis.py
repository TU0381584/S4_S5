#!/usr/bin/env python3
"""M77 analysis: aggregate throughput and backlog-delay measurements (docs/PAPER5_M77_plan.md).

Only runs that reproduce their stored evaluation log enter the means; runs with no
stored log to compare against (accept-all in some cells) are kept and flagged.

Usage: m77_analysis.py --out experiments/results/m77/analysis.json
"""
import argparse
import glob
import json
import os

import numpy as np

ROOT = "/home/kmanojp/oranslice_rig/experiments/results/m77"
SLICES = ("urllc", "embb", "mmtc")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = {}
    for cell in ("A_n3", "A_n37_hex", "B_n3", "B_n19_hex"):
        out[cell] = {}
        runs = {}
        for f in glob.glob(f"{ROOT}/{cell}/*_*.json"):
            arm = os.path.basename(f).rsplit("_", 1)[0]
            for s, r in json.load(open(f)).items():
                runs.setdefault(arm, {})[int(s)] = r
        for arm, rr in sorted(runs.items()):
            bad = [s for s, r in rr.items() if r["reproduces_stored"] is False]
            unchecked = [s for s, r in rr.items() if r["reproduces_stored"] is None]
            use = {s: r for s, r in rr.items() if r["reproduces_stored"] is not False}
            row = {"n": len(use), "not_reproduced": bad, "unchecked": len(unchecked)}
            for sl in SLICES:
                k = [r["kpi"][sl] for r in use.values()]
                row[sl] = {"served_over_offered": float(np.mean([x["served_over_offered"] for x in k])),
                           "served_prb": float(np.mean([x["served_prb"] for x in k])),
                           "delay_steps": float(np.mean([x["delay_steps"] for x in k if x["delay_steps"] is not None])),
                           "delay_steps_p95": float(np.mean([x["delay_steps_p95"] for x in k if x["delay_steps_p95"] is not None]))}
            out[cell][arm] = row
            print(f"{cell:10s} {arm:20s} n={row['n']:2d} bad={bad} unchecked={len(unchecked):2d} | "
                  + " | ".join(f"{sl} thr {row[sl]['served_over_offered']:.3f} delay {row[sl]['delay_steps']:.3f} p95 {row[sl]['delay_steps_p95']:.3f}" for sl in SLICES))
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
