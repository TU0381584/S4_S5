#!/usr/bin/env python3
"""M110 analysis, fixed in docs/PAPER5_M110_preregistration.md before any campaign run. Run from framework/:
  ../venv/bin/python ../experiments/scripts/m110_analysis.py --out ../experiments/results/m110/analysis.json
Per-gNB priority-slice compliance of a run is the mean over gNBs of the share of evaluation steps on which that gNB
meets the SLA, averaged over URLLC and eMBB. The cluster-level value is the paper's (m66_verify.prio on the stored log).
"""
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m66_verify as V
from m62_analysis import boot_ci
from m110_pergnb import ARMS, OUT, cells, stored
from scipy.stats import wilcoxon


def holm(ps):
    o = np.argsort(ps); adj = [0.0] * len(ps); run = 0.0
    for k, i in enumerate(o):
        run = max(run, min(1.0, (len(ps) - k) * ps[i])); adj[i] = run
    return adj


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    res, inexact, missing = {}, [], []
    for n in (3, 7, 19, 37):
        res[n] = {}
        for arm in ARMS:
            runs = {}
            for cell, t, ss in cells(n, arm):
                for s, p in stored(n, t, arm).items():
                    f = f"{OUT}/A_n{n}_{t}/{arm}/seed{s}/row.json"
                    if not os.path.exists(f):
                        missing.append(f); continue
                    r = json.load(open(f))
                    if not r["exact"]:
                        inexact.append(f); continue
                    pg = r["per_gnb_mean"]
                    runs[(t, s)] = {"pergnb": 100 * (pg["urllc"] + pg["embb"]) / 2, "cluster": 100 * V.prio(V.read(p))}
            res[n][arm] = runs
    out = {"missing": missing, "inexact": inexact, "summary": {}, "tests": {}}
    for n in res:
        out["summary"][n] = {}
        for arm, runs in res[n].items():
            pg = [r["pergnb"] for r in runs.values()]; cl = [r["cluster"] for r in runs.values()]
            out["summary"][n][arm] = {"n": len(pg), "pergnb_mean": float(np.mean(pg)), "pergnb_ci": list(boot_ci(pg)),
                                      "cluster_mean": float(np.mean(cl)), "cluster_ci": list(boot_ci(cl))}
            print(f"N={n:2d} {arm:18s} n={len(pg):3d} per-gNB {np.mean(pg):6.2f}  cluster {np.mean(cl):6.2f}")
        base = [b for b in ARMS if b != "axiom2"]; rows = []
        for b in base:
            keys = sorted(set(res[n]["axiom2"]) & set(res[n][b]))
            d = np.array([res[n]["axiom2"][k]["pergnb"] - res[n][b][k]["pergnb"] for k in keys])
            nz = d[np.abs(d) > 1e-9]
            p = float(wilcoxon(nz).pvalue) if len(nz) else 1.0
            rows.append({"baseline": b, "n": len(keys), "diff": float(d.mean()), "ci": list(boot_ci(d)), "p": p})
        for r, hp in zip(rows, holm([r["p"] for r in rows])):
            r["holm_p"] = hp
            print(f"   AXIOM - {r['baseline']:18s} n={r['n']:3d} diff {r['diff']:+6.2f} [{r['ci'][0]:+.2f}, {r['ci'][1]:+.2f}] Holm p {hp:.4g}")
        out["tests"][n] = rows
    best = {n: min(out["tests"][n], key=lambda r: r["diff"]) for n in (19, 37)}
    out["decision"] = {str(n): {"closest_baseline": r["baseline"], "diff": r["diff"], "holm_p": r["holm_p"],
                                "lead_holds": bool(r["diff"] >= 5 and r["holm_p"] < 0.05)} for n, r in best.items()}
    print("decision:", json.dumps(out["decision"])); print("missing", len(missing), "inexact", len(inexact))
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
