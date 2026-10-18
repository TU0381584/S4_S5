#!/usr/bin/env python3
"""M67 development-round analysis against the target in docs/PAPER5_M67_development_protocol.md.

For each arm it reads both the selected-checkpoint evaluation (eval/) and the
last-checkpoint evaluation (eval_last/) of the same training runs.

Usage: m67_dev_analysis.py --root m67_dev/V1 [--ref-root m67_dev/V1] --out experiments/results/m67_dev/V1/analysis.json
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import ROOT, paired, prio, read, seeds_of  # noqa: E402

DEV = list(range(7000, 7020))


def last_of(cell, arm, seeds):
    out = {}
    for s in seeds:
        c = glob.glob(f"{ROOT}/{cell}/{arm}/seed{s}/eval_last/**/omega_log.jsonl*", recursive=True)
        if c:
            out[s] = read(c[0])
    return out


def line(t):
    return f"diff {t['diff']:+.3f}, p {t['p']:.3g}, W/T/L {t['wins']}/{t['ties']}/{t['losses']} (n={t['n']})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--axiom-arm", default="axiom2")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res, ok = {}, {}
    for c, alpha in (("A3_base", 0.01), ("A3_load102", 0.05)):
        cell = f"{a.root}/{c}"
        ax = seeds_of(cell, a.axiom_arm, DEV)
        base = {k: seeds_of(cell, k, DEV) for k in ("single_agent_dqn", "independent_dqn")}
        orc = seeds_of(cell, "rule_static", DEV)
        r = {"n": len(ax), "axiom": float(np.mean([v["reward"] for v in ax.values()])) if ax else None,
             "oracle": float(np.mean([v["reward"] for v in orc.values()])) if orc else None,
             "axiom_oracle_ties": sum(abs(ax[s]["reward"] - orc[s]["reward"]) < 1e-9 for s in ax if s in orc)}
        for k, v in base.items():
            t = paired(ax, v)
            r[k] = t
            r[k + "_ties_oracle"] = sum(abs(v[s]["reward"] - orc[s]["reward"]) < 1e-9 for s in v if s in orc)
            r[k + "_last"] = paired(last_of(cell, a.axiom_arm, DEV), last_of(cell, k, DEV))
        r["axiom_selected_vs_last"] = paired(ax, last_of(cell, a.axiom_arm, DEV))
        maxloss = 2 if c == "A3_base" else 20
        ok[c] = all(r[k]["n"] == 20 and r[k]["diff"] > 0 and r[k]["p"] < alpha and r[k]["losses"] <= maxloss
                    for k in ("single_agent_dqn", "independent_dqn"))
        res[c] = r
        print(f"== {c}: AXIOM {r['axiom']:.3f} oracle {r['oracle']:.3f} AXIOM ties oracle {r['axiom_oracle_ties']}/{r['n']}")
        for k in ("single_agent_dqn", "independent_dqn"):
            print(f"   vs {k:17s} selected: {line(r[k])}; last: {line(r[k + '_last'])}; {k} ties oracle {r[k + '_ties_oracle']}")
        print(f"   AXIOM selected minus last: {line(r['axiom_selected_vs_last'])}   target met: {ok[c]}")
    for g, cell, S in (("G_B3", f"{a.root}/G_B3", DEV[:10]), ("G_A7_ring", f"{a.root}/G_A7_ring", DEV[:10])):
        ax, ref = seeds_of(cell, a.axiom_arm, S), last_of(cell, "axiom2", S)
        if not ax:
            continue
        t = paired(ax, ref)
        res[g] = t
        ok[g] = not (t["diff"] < 0 and t["p"] < 0.05) and t["n"] == 10
        print(f"== guard {g}: variant minus current AXIOM v2 (last checkpoint, same runs): {line(t)}  ok: {ok[g]}")
    res["target_met"] = ok
    print("TARGET MET" if all(ok.values()) and len(ok) == 4 else "target not met", ok)
    json.dump(res, open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
