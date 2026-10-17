#!/usr/bin/env python3
"""M66b fresh-seed analysis against addendum 1 of docs/PAPER5_M66_verification_plan.md.

Uses the independent reader in m66_verify.py. Every criterion is reported as
HOLDS or FAILS.

Usage: m66b_analysis.py --out experiments/results/m66b_analysis.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import holm, mean, paired, prio, seeds_of  # noqa: E402

SEEDS = list(range(3000, 3010))
BASE = ("independent_dqn", "single_agent_dqn", "mappo_tuned")
ARMS = ("axiom2",) + BASE


def crit(C, label, ok, detail):
    print(f"[{'HOLDS' if ok else 'FAILS'}] {label}: {detail}")
    C.append({"label": label, "holds": bool(ok), "detail": detail})


def boot_ci(x, n=10000):
    x = np.asarray(x, float)
    rng = np.random.RandomState(0)
    m = x[rng.randint(0, len(x), (n, len(x)))].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def summ(rows):
    return {"n": len(rows), "reward": mean(rows), "prio": mean(rows, prio),
            "urllc": mean(rows, lambda r: r["sla"]["urllc"]), "embb": mean(rows, lambda r: r["sla"]["embb"]),
            "collapsed": int(sum(r["collapsed"] for r in rows.values()))}


def scaling(C, out, cells, label, hi_base):
    d = {c: {a: seeds_of(f"m66b_fresh/{c}", a, SEEDS) for a in ARMS} for c in cells}
    out[label] = {"summary": {c: {a: summ(d[c][a]) for a in ARMS} for c in cells}, "tests": {}}
    pooled = {a: float(np.mean([prio(r) for c in cells for r in d[c][a].values()])) for a in ARMS}
    out[label]["pooled_prio"] = pooled
    crit(C, f"{label} AXIOM pooled priority SLA >= 90%", pooled["axiom2"] >= 0.90,
         f"{100 * pooled['axiom2']:.1f}% on {sum(len(d[c]['axiom2']) for c in cells)} cells")
    for a in BASE:
        crit(C, f"{label} {a} pooled priority SLA <= {100 * hi_base:.0f}%", pooled[a] <= hi_base, f"{100 * pooled[a]:.1f}%")
    tests = {}
    for c in cells:
        for a in BASE:
            for m, f in (("reward", lambda r: r["reward"]), ("prio", prio)):
                tests[(c, a, m)] = paired(d[c]["axiom2"], d[c][a], f)
    h = holm({k: v["p"] for k, v in tests.items()})
    for k, t in tests.items():
        t["p_holm"] = h[k]
        out[label]["tests"]["/".join(k)] = t
    ok = all(t["diff"] > 0 and t["p_holm"] < 0.05 for t in tests.values())
    worst = max(tests.values(), key=lambda t: t["p_holm"])
    crit(C, f"{label} AXIOM beats every baseline on reward and priority SLA, all {len(tests)} at Holm p<0.05", ok,
         f"max p_holm {worst['p_holm']:.3g}, min diff {min(t['diff'] for t in tests.values()):+.4f}")
    for c in cells:
        for a in ARMS:
            s = out[label]["summary"][c][a]
            print(f"   {c:20s} {a:18s} n={s['n']} reward {s['reward']:.3f} prio {100 * s['prio']:.1f}% "
                  f"urllc {100 * s['urllc']:.1f}% embb {100 * s['embb']:.1f}% collapsed {s['collapsed']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    C, out = [], {}
    scaling(C, out, ("A_n7_ring", "A_n7_fully_connected"), "Env A N=7", 0.80)
    scaling(C, out, ("A_n19_hex",), "Env A N=19 hex", 0.75)

    fed = {}
    for b in range(3000, 3010, 2):
        fed.update(seeds_of(f"m66b_fresh/m3_s{b}", "fl_gat_ctde_sigma0.0", [b, b + 1]))
    cen = seeds_of("m66_fresh/A_n3", "axiom2", SEEDS)
    t = paired(cen, fed)
    common = sorted(set(cen) & set(fed))
    d = [cen[s]["reward"] - fed[s]["reward"] for s in common]
    t["ci"] = boot_ci(d) if d else None
    out["federated"] = {"centralised": mean(cen), "federated": mean(fed) if fed else None, "test": t}
    crit(C, "Env A N=3 federated sigma 0 shows no significant reward difference from centralised", len(common) == 10 and t["p"] >= 0.05,
         f"n={len(common)} centralised {mean(cen):.3f} federated {mean(fed) if fed else float('nan'):.3f} "
         f"diff {t['diff']:+.3f} CI [{t['ci'][0]:.2f}, {t['ci'][1]:.2f}] p {t['p']:.3g} W/T/L {t['wins']}/{t['ties']}/{t['losses']}")

    n_fail = sum(not c["holds"] for c in C)
    print(f"== {len(C) - n_fail}/{len(C)} hold")
    out["criteria"], out["n_fail"] = C, n_fail
    json.dump(out, open(a.out, "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
