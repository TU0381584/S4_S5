#!/usr/bin/env python3
"""M64 Env B analysis, exactly as pre-registered (docs/PAPER5_M64_preregistration.md).

  H1  N=3: AXIOM v2 reward > rule_static and > rule_accept_all (one-sided Wilcoxon, Holm over 2)
  H2  per size: AXIOM v2 vs independent_dqn, single_agent_dqn, mappo_tuned, rule_local,
      rule_neighbour on reward and on priority-slice SLA (two-sided Wilcoxon, Holm over the 10 tests;
      at N=7 the family pools the three layouts, 30 tests)
  H3  N=7 ring and hex: AXIOM v2 vs axiom2_mlp on reward (two-sided Wilcoxon, Holm over 2)
Also writes a per-arm summary (reward with CI, precision, collapse count, per-slice SLA).

Usage: m64_analysis.py --root experiments/results/m64 --out experiments/results/m64/m64_analysis.json
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).resolve().parent))
from m62_analysis import boot_ci, eval_log, holm, seed_metrics  # noqa: E402

LEARNED = ["axiom2", "axiom2_mlp", "independent_dqn", "single_agent_dqn", "mappo_tuned", "axiom",
           "axiom2_lr3e-4", "axiom2_lr3e-3", "axiom2_wide"]
RULES = ["rule_static", "rule_accept_all", "rule_local", "rule_neighbour"]
H2_ARMS = ["independent_dqn", "single_agent_dqn", "mappo_tuned", "rule_local", "rule_neighbour"]


def prio(r):
    return 0.5 * (r["sla"]["urllc"] + r["sla"]["embb"])


def load(cell, seeds):
    return {arm: {s: seed_metrics(p) for s in seeds if (p := eval_log(cell, arm, s))} for arm in LEARNED + RULES}


def summary(data):
    out = {}
    for arm, rows in data.items():
        if not rows:
            continue
        r = [v["reward"] for v in rows.values()]
        prec = [v["precision"] for v in rows.values() if v["precision"] is not None]
        out[arm] = {"n": len(rows), "reward": float(np.mean(r)), "reward_ci": boot_ci(r),
                    "precision": float(np.mean(prec)) if prec else None,
                    "collapsed": int(sum(v["collapsed"] for v in rows.values())),
                    "sla": {k: float(np.mean([v["sla"][k] for v in rows.values()])) for k in ("urllc", "embb", "mmtc")},
                    "prio_sla": float(np.mean([prio(v) for v in rows.values()]))}
    return out


def paired(a_rows, b_rows, f, alternative="two-sided"):
    c = sorted(set(a_rows) & set(b_rows))
    d = np.array([f(a_rows[s]) - f(b_rows[s]) for s in c])
    p = float(wilcoxon(d, alternative=alternative).pvalue) if len(d) and np.any(d != 0) else 1.0
    return {"n": len(c), "diff": float(d.mean()) if len(d) else None, "ci": boot_ci(d) if len(d) > 1 else None,
            "wtl": [int((d > 0).sum()), int((d == 0).sum()), int((d < 0).sum())], "p": p}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    S30, REP, S15 = list(range(900, 930)), list(range(1000, 1010)), list(range(900, 912)) + [1000, 1001, 1002]
    res = {"cells": {}}
    cells = {"n3": (f"{a.root}/n3_fully_connected", S30), "n3_rep": (f"{a.root}/n3_replication", REP)}
    for t in ("fully_connected", "ring", "hex"):
        cells[f"n7_{t}"] = (f"{a.root}/n7_{t}", S15)
    data = {k: load(*v) for k, v in cells.items()}
    for k, d in data.items():
        res["cells"][k] = summary(d)
    rew = lambda r: r["reward"]
    # H1
    h1 = {b: paired(data["n3"]["axiom2"], data["n3"][b], rew, "greater") for b in ("rule_static", "rule_accept_all")}
    adj = holm({b: v["p"] for b, v in h1.items()})
    for b in h1:
        h1[b]["p_holm"] = adj[b]
    res["H1"] = h1
    # H2 at N=3 (primary and replication separately) and N=7 (three layouts pooled into one family)
    for key, cellkeys in (("H2_n3", ["n3"]), ("H2_n3_rep", ["n3_rep"]), ("H2_n7", ["n7_fully_connected", "n7_ring", "n7_hex"])):
        fam = {}
        for ck in cellkeys:
            for b in H2_ARMS:
                for mname, f in (("reward", rew), ("prio_sla", prio)):
                    if data[ck].get(b):
                        fam[f"{ck}|{b}|{mname}"] = paired(data[ck]["axiom2"], data[ck][b], f)
        adj = holm({k: v["p"] for k, v in fam.items()})
        for k in fam:
            fam[k]["p_holm"] = adj[k]
        res[key] = fam
    # H3
    h3 = {t: paired(data[f"n7_{t}"]["axiom2"], data[f"n7_{t}"]["axiom2_mlp"], rew) for t in ("ring", "hex")}
    adj = holm({t: v["p"] for t, v in h3.items()})
    for t in h3:
        h3[t]["p_holm"] = adj[t]
    h3["fully_connected_secondary"] = paired(data["n7_fully_connected"]["axiom2"], data["n7_fully_connected"]["axiom2_mlp"], rew)
    h3["n3_secondary"] = paired(data["n3"]["axiom2"], data["n3"]["axiom2_mlp"], rew)
    res["H3"] = h3
    # exploratory: original AXIOM and v2 sensitivity against v2, N=3 seeds 900-909
    res["exploratory_n3"] = {b: paired(data["n3"]["axiom2"], data["n3"][b], rew)
                             for b in ("axiom", "axiom2_lr3e-4", "axiom2_lr3e-3", "axiom2_wide") if data["n3"].get(b)}
    json.dump(res, open(a.out, "w"), indent=1, default=float)
    for k in ("H1", "H3"):
        print(k, json.dumps(res[k], default=float))
    for k in ("H2_n3", "H2_n3_rep", "H2_n7"):
        for kk, v in res[k].items():
            print(f"{k} {kk:46s} diff={v['diff']:+.3f} W/T/L={v['wtl']} p_holm={v['p_holm']:.3g}")
    for ck, sm in res["cells"].items():
        for arm, s in sm.items():
            print(f"{ck:20s} {arm:18s} n={s['n']:2d} reward={s['reward']:7.3f} prio={s['prio_sla']:.3f} "
                  f"urllc={s['sla']['urllc']:.3f} embb={s['sla']['embb']:.3f} mmtc={s['sla']['mmtc']:.3f} coll={s['collapsed']}")


if __name__ == "__main__":
    main()
