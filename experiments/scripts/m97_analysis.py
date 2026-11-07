#!/usr/bin/env python3
"""M97 analysis (docs/PAPER5_M97_preregistration.md, commit 33522657). The tuned local rule in Env A at 37 gNBs, hex
layout: its held-out priority-slice compliance and URLLC backlog delay, the figure's thresholds (90%, 0.5 control
periods), the selected thresholds, and a descriptive paired comparison with the static rule and AXIOM on the same seeds.
No hypothesis is tested. Reads every log with m66_verify's independent reader.

Usage: m97_analysis.py --out experiments/results/m97/analysis.json
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import S30_19, paired, prio, seeds_of  # noqa: E402

ROOT = "/home/kmanojp/oranslice_rig/experiments/results"
P = lambda r: 100 * prio(r)
R = lambda r: r["reward"]


def kpi(cell, arm):
    rows = {}
    for f in glob.glob(f"{ROOT}/{cell}/{arm}_*.json"):
        rows.update({int(k): v for k, v in json.load(open(f)).items()})
    return rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    sel = json.load(open(f"{ROOT}/m97/A_n37_hex/rule_local_selection.json"))
    grid = sorted(sel["grid"], key=lambda x: -x[0])
    rl = seeds_of("m97/A_n37_hex", "rule_local", S30_19)
    st = seeds_of("m73/A_n37_hex", "rule_static", S30_19)
    ax = seeds_of("m73/A_n37_hex", "axiom2", S30_19)
    k = kpi("m97/A_n37_hex_kpi", "rule_local_cell")
    dl = [v["kpi"]["urllc"]["delay_steps"] for v in k.values() if v["kpi"]["urllc"]["delay_steps"] is not None]
    out = {
        "selected": sel["selected"], "train_score": sel["train_score"], "grid_size": len(sel["grid"]),
        "runner_up": grid[1] if len(grid) > 1 else None,
        "n_eval": len(rl), "n_kpi": len(k), "kpi_all_reproduce_stored": all(v["reproduces_stored"] is True for v in k.values()),
        "prio_mean": float(np.mean([P(r) for r in rl.values()])), "urllc_mean": float(np.mean([100 * r["sla"]["urllc"] for r in rl.values()])),
        "embb_mean": float(np.mean([100 * r["sla"]["embb"] for r in rl.values()])), "reward_mean": float(np.mean([R(r) for r in rl.values()])),
        "urllc_delay_mean": float(np.mean(dl)), "n_delay": len(dl),
        "meets_sla90": bool(np.mean([P(r) for r in rl.values()]) >= 90.0), "meets_delay05": bool(np.mean(dl) < 0.5),
        "vs_static": {"prio": paired(rl, st, P), "reward": paired(rl, st, R)},
        "vs_axiom": {"prio": paired(rl, ax, P), "reward": paired(rl, ax, R)},
        "static_prio_mean": float(np.mean([P(r) for r in st.values()])), "axiom_hex_prio_mean": float(np.mean([P(r) for r in ax.values()])),
    }
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
