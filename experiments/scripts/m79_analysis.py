#!/usr/bin/env python3
"""M79 analysis against docs/PAPER5_M79_preregistration.md (R, H1, H2, H3).

Usage: m79_analysis.py --out experiments/results/m79/analysis.json
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m62_analysis import boot_ci  # noqa: E402
from m66_verify import ROOT, S15, holm, paired, prio, seeds_of  # noqa: E402

N = 7
STORED = "m64/n7_ring"
C = []


def crit(label, ok, detail, kind=None):
    tag = kind or ("HOLDS" if ok else "FAILS")
    print(f"[{tag}] {label}: {detail}")
    C.append({"label": label, "holds": None if kind else bool(ok), "detail": detail})


def fmt(t):
    return (f"diff {t['diff']:+.4f}, W/T/L {t['wins']}/{t['ties']}/{t['losses']}, p {t['p']:.3g}"
            + (f", p_holm {t['p_holm']:.3g}" if "p_holm" in t else "") + f" (n={t['n']})")


def mmtc_only(r):
    return r["blocks"] > 0 and r["mmtc"] == r["blocks"]


def describe(rows):
    v = list(rows.values())
    rw = [r["reward"] / N for r in v]
    pr = [100 * prio(r) for r in v]
    return {"n": len(v), "reward_per_gnb": float(np.mean(rw)), "reward_per_gnb_ci": list(boot_ci(rw)),
            "prio_sla": float(np.mean(pr)), "prio_sla_ci": list(boot_ci(pr)),
            "urllc": float(np.mean([100 * r["sla"]["urllc"] for r in v])),
            "embb": float(np.mean([100 * r["sla"]["embb"] for r in v])),
            "mmtc_share_of_blocks": float(sum(r["mmtc"] for r in v) / max(1, sum(r["blocks"] for r in v))),
            "non_mmtc_blocks_per_seed": float(np.mean([r["blocks"] - r["mmtc"] for r in v])),
            "mmtc_only_seeds": int(sum(mmtc_only(r) for r in v)), "collapsed": int(sum(r["collapsed"] for r in v))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    arms = {
        "stored AXIOM": (STORED, "axiom2"),
        "stored DQN-SA": (STORED, "single_agent_dqn"),
        "stored AXIOM-MLP": (STORED, "axiom2_mlp"),
        "stored static rule": (STORED, "rule_static"),
        "stored local rule": (STORED, "rule_local"),
        "H1 AXIOM per-gNB penalty": ("m79/pergnb_n7_ring", "axiom2"),
        "H1 DQN-SA per-gNB penalty": ("m79/pergnb_n7_ring", "single_agent_dqn"),
        "H2 AXIOM LR 3e-3": ("m79/lr3e-3_n7_ring", "axiom2_lr3e-3"),
        "H3 AXIOM 900 episodes": ("m79/ep900_n7_ring", "axiom2"),
    }
    rows = {k: seeds_of(c, arm, S15) for k, (c, arm) in arms.items()}
    table = {k: describe(v) for k, v in rows.items() if v}
    for k, d in table.items():
        print(f"{k:28s} n={d['n']:2d} r/gNB {d['reward_per_gnb']:.3f} prio {d['prio_sla']:5.1f} "
              f"U {d['urllc']:5.1f} E {d['embb']:5.1f} mMTC share {d['mmtc_share_of_blocks']:.3f} "
              f"mMTC-only {d['mmtc_only_seeds']:2d} collapsed {d['collapsed']}")

    # R. Reproduction against the stored per-seed evaluation reward
    stored = {}
    for f in glob.glob(f"{ROOT}/{STORED}/axiom2_[0-9]*.json"):
        stored.update({int(s): v["reward"] for s, v in json.load(open(f)).items()})
    rep = {}
    for f in glob.glob(f"{ROOT}/m79/repro_n7_ring/axiom2_[0-9]*.json"):
        rep.update({int(s): v["reward"] for s, v in json.load(open(f)).items()})
    gaps = {s: abs(rep[s] - stored[s]) for s in rep}
    crit("R. AXIOM seeds 900-902 reproduce the stored evaluation reward within 1e-9",
         len(gaps) == 3 and max(gaps.values()) <= 1e-9, gaps)

    # a, b per hypothesis
    base = rows["stored AXIOM"]
    tests = {}
    for h, k in (("H1", "H1 AXIOM per-gNB penalty"), ("H2", "H2 AXIOM LR 3e-3"), ("H3", "H3 AXIOM 900 episodes")):
        d = table.get(k)
        if not d or d["n"] < 15:
            crit(f"{h} incomplete", False, {"n": d["n"] if d else 0}, kind="MISSING")
            continue
        crit(f"{h}a. {k} mMTC-only in at most 5 of 15 seeds", d["mmtc_only_seeds"] <= 5, d["mmtc_only_seeds"])
        tests[h] = paired(rows[k], base, f=lambda r: 100 * prio(r))
    adj = holm({h: t["p"] for h, t in tests.items()})
    for h, t in tests.items():
        t["p_holm"] = adj[h]
        crit(f"{h}b. compliance above stored AXIOM, Holm over {len(tests)}", t["diff"] > 0 and t["p_holm"] < 0.05, fmt(t))

    # reported comparisons
    rep_tests = {}
    pairs = [("H1 AXIOM per-gNB penalty", "H1 DQN-SA per-gNB penalty")] + \
            [(k, "stored DQN-SA") for k in ("H1 AXIOM per-gNB penalty", "H2 AXIOM LR 3e-3", "H3 AXIOM 900 episodes")] + \
            [(k, "stored AXIOM") for k in ("H1 AXIOM per-gNB penalty", "H2 AXIOM LR 3e-3", "H3 AXIOM 900 episodes")]
    for x, y in pairs:
        if rows.get(x) and rows.get(y):
            for name, f in (("prio", lambda r: 100 * prio(r)), ("reward_per_gnb", lambda r: r["reward"] / N)):
                if name == "reward_per_gnb" and ("per-gNB" in x) != ("per-gNB" in y):
                    continue    # the per-gNB penalty changes the reward itself, so only compliance compares
                t = paired(rows[x], rows[y], f=f)
                rep_tests[f"{x} vs {y}, {name}"] = t
                crit(f"{x} vs {y}, {name}", None, fmt(t), kind="REPORTED")
    json.dump({"table": table, "criteria": C, "tests": tests, "reported": rep_tests}, open(a.out, "w"), indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
