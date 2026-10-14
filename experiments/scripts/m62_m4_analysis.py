#!/usr/bin/env python3
"""Paired statistics for an M62 disruption campaign.

For every (arm, kind, severity) cell, the per-seed cost is the arm's own
undisrupted volume-normalised reward minus its disrupted one, so a positive
cost means the disruption hurt. Reports mean cost, 95% bootstrap CI, the
number of seeds hurt, a Wilcoxon signed-rank test against zero, and Holm
correction across all dropout and churn cells. Spike cells also report
block precision, since spike changes request volume.

Usage:
    m62_m4_analysis.py --m4-dir experiments/results/m62_m4 \
        --m2-dir experiments/results/m62_m2_view --m3-dir experiments/results/m62_m3 \
        --out experiments/results/m62_m4/m4_summary.json
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).resolve().parent))
from m4_correctness_metrics import baseline_eval_path, disrupted_eval_path, per_seed_metrics_normalized  # noqa: E402
from m62_analysis import boot_ci, holm  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m4-dir", required=True)
    ap.add_argument("--m2-dir", required=True)
    ap.add_argument("--m3-dir", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    cells = json.load(open(f"{a.m4_dir}/campaign_results.json"))["results"]
    groups = {}
    for c in cells.values():
        groups.setdefault((c["arm"], c["kind"], c["severity"]), []).append(c["seed"])
    rows, pvals = {}, {}
    for (arm, kind, sev), seeds in sorted(groups.items()):
        cost, prec, lvl, base = [], [], {}, []
        for s in sorted(seeds):
            bp = baseline_eval_path(arm, s, a.m2_dir, a.m3_dir)
            dp = disrupted_eval_path(a.m4_dir, arm, f"{kind}_sev{sev}", s)
            if not (os.path.exists(bp) and os.path.exists(dp)):
                continue
            rb, _, _ = per_seed_metrics_normalized(bp)
            rd, mb, tb = per_seed_metrics_normalized(dp)
            cost.append(rb - rd)
            lvl[s] = rd
            base.append(rb)
            if tb > 0:
                prec.append(mb / tb)
        if not cost:
            continue
        c = np.array(cost)
        p = float(wilcoxon(c).pvalue) if np.any(c != 0) else 1.0
        key = f"{arm}|{kind}|{sev}"
        rows[key] = {"n": len(c), "cost_mean": float(c.mean()), "cost_ci": boot_ci(c),
                     "hurt": int((c > 0).sum()), "p": p,
                     "baseline_mean": float(np.mean(base)), "disrupted_mean": float(np.mean(list(lvl.values()))),
                     "disrupted_per_seed": {str(k): v for k, v in lvl.items()},
                     "precision_mean": float(np.mean(prec)) if prec else None, "n_blocking": len(prec)}
        if kind in ("dropout", "churn"):
            pvals[key] = p
    adj = holm(pvals)
    for k, r in rows.items():
        r["p_holm"] = adj.get(k)
        ph = f"{r['p_holm']:.3g}" if r["p_holm"] is not None else "-"
        pr = f"{r['precision_mean']:.3f}" if r["precision_mean"] is not None else "n/a"
        print(f"{k:40s} n={r['n']:2d} cost={r['cost_mean']:+.3f} [{r['cost_ci'][0]:+.3f},{r['cost_ci'][1]:+.3f}] "
              f"hurt={r['hurt']:2d} p={r['p']:.3g} p_holm={ph} prec={pr} ({r['n_blocking']})")
    # Paired AXIOM-minus-baseline gap in the disrupted level, same seed and disruption.
    gaps, gp = {}, {}
    for k, r in rows.items():
        arm, kind, sev = k.split("|")
        ref = rows.get(f"gat_ctde|{kind}|{sev}")
        if arm == "gat_ctde" or ref is None:
            continue
        common = sorted(set(ref["disrupted_per_seed"]) & set(r["disrupted_per_seed"]))
        if len(common) < 5:
            continue
        d = np.array([ref["disrupted_per_seed"][s] - r["disrupted_per_seed"][s] for s in common])
        gaps[k] = {"n": len(d), "gap_mean": float(d.mean()), "gap_ci": boot_ci(d), "wins": int((d > 0).sum())}
        gp[k] = float(wilcoxon(d).pvalue) if np.any(d != 0) else 1.0
    gadj = holm(gp)
    print("AXIOM minus baseline, disrupted normalised reward")
    for k, g in gaps.items():
        g["p"], g["p_holm"] = gp[k], gadj[k]
        r = rows[k]
        print(f"  {k:38s} base={r['baseline_mean']:.3f} disrupted={r['disrupted_mean']:.3f} gap={g['gap_mean']:+.3f} "
              f"[{g['gap_ci'][0]:+.3f},{g['gap_ci'][1]:+.3f}] wins={g['wins']}/{g['n']} p_holm={g['p_holm']:.3g}")
    for k in [k for k in rows if k.startswith("gat_ctde|")]:
        print(f"  {k:38s} base={rows[k]['baseline_mean']:.3f} disrupted={rows[k]['disrupted_mean']:.3f}")
    if a.out:
        json.dump({"cells": rows, "axiom_gap": gaps}, open(a.out, "w"), indent=2)


if __name__ == "__main__":
    main()
