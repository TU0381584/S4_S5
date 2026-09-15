#!/usr/bin/env python3
"""M47-PF2-1c -- GATE analysis, PRIMARY DRAW ONLY (preliminary/unreplicated,
see docs/PAPER5_M47_PF21c_plan_and_deviation.md addendum: the replication
draw was stopped by explicit user decision at 5/30 runs, not completed, so
no independent-draw confirmation exists for this campaign -- unlike every
prior gated milestone in this project's WPC line). Reuses bootstrap_ci from
m2_correctness_metrics.py (not reimplemented). Paired by slot_seed (the
natural pairing unit -- every arm in a slot shares the same eval_seed /
arrival-process realization).

Usage: python3 experiments/scripts/m47_pf21c_analysis.py
"""
import csv
import sys
from pathlib import Path

import numpy as np
from scipy import stats as sstats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from m2_correctness_metrics import bootstrap_ci  # noqa: E402

RIG = Path(__file__).resolve().parent.parent.parent
MANIFEST = RIG / "experiments/results/m47_pf21c/manifest.csv"
ARMS = ["dqn_qoe", "dqn_sla", "static_cap", "static_floor", "lb_only"]

PAIRS = [
    ("static_cap", "dqn_sla"),
    ("dqn_sla", "dqn_qoe"),
    ("static_cap", "dqn_qoe"),
    ("static_cap", "static_floor"),
    ("static_cap", "lb_only"),
    ("dqn_sla", "lb_only"),
]


def load():
    rows = list(csv.DictReader(MANIFEST.open()))
    primary = [r for r in rows if r["draw"] == "primary"]
    repl = [r for r in rows if r["draw"] == "replication"]
    by_slot_arm = {}
    for r in primary:
        by_slot_arm[(int(r["slot_seed"]), r["arm"])] = r
    slots = sorted(set(int(r["slot_seed"]) for r in primary))
    return primary, repl, by_slot_arm, slots


def paired_series(by_slot_arm, slots, arm_a, arm_b, metric):
    a, b = [], []
    for s in slots:
        ra, rb = by_slot_arm.get((s, arm_a)), by_slot_arm.get((s, arm_b))
        if ra is None or rb is None or not ra[metric] or not rb[metric]:
            continue
        a.append(float(ra[metric]))
        b.append(float(rb[metric]))
    return np.array(a), np.array(b)


def report_pair(by_slot_arm, slots, arm_a, arm_b, metric):
    a, b = paired_series(by_slot_arm, slots, arm_a, arm_b, metric)
    n = len(a)
    diff = a - b
    mean_diff = float(diff.mean())
    ci_lo, ci_hi = bootstrap_ci(diff.tolist(), seed=0)
    if np.allclose(diff, 0):
        t_p, w_p = 1.0, 1.0
    else:
        t_p = sstats.ttest_rel(a, b).pvalue
        try:
            w_p = sstats.wilcoxon(diff).pvalue
        except ValueError:
            w_p = float("nan")
    print(f"  {arm_a:>13s} - {arm_b:<13s} n={n}  mean_diff={mean_diff:+.4f}  "
          f"boot95%CI=[{ci_lo:+.4f},{ci_hi:+.4f}]  paired_t_p={t_p:.4f}  wilcoxon_p={w_p:.4f}")
    return dict(arm_a=arm_a, arm_b=arm_b, metric=metric, n=n, mean_diff=mean_diff,
                ci_lo=ci_lo, ci_hi=ci_hi, t_p=t_p, w_p=w_p)


def main():
    primary, repl, by_slot_arm, slots = load()
    print(f"[m47-pf21c-analysis] PRIMARY draw: {len(primary)} rows, slots={slots}")
    print(f"[m47-pf21c-analysis] partial REPLICATION draw (not used for inference, "
          f"informal spot-check only): {len(repl)}/30 rows collected before stop\n")

    print("=== per-arm PWC / PWC_eq summary (primary draw, n=6/arm) ===")
    for arm in ARMS:
        pwcs = [float(by_slot_arm[(s, arm)]["pwc"]) for s in slots if (s, arm) in by_slot_arm]
        pwc_eqs = [float(by_slot_arm[(s, arm)]["pwc_eq"]) for s in slots if (s, arm) in by_slot_arm]
        classes = [by_slot_arm[(s, arm)]["shed_classification"] for s in slots if (s, arm) in by_slot_arm]
        ci = bootstrap_ci(pwcs, seed=0)
        ci_eq = bootstrap_ci(pwc_eqs, seed=0)
        from collections import Counter
        print(f"  {arm:14s} n={len(pwcs)}  PWC mean={np.mean(pwcs):.4f} 95%CI=[{ci[0]:.4f},{ci[1]:.4f}]  "
              f"PWC_eq mean={np.mean(pwc_eqs):.4f} 95%CI=[{ci_eq[0]:.4f},{ci_eq[1]:.4f}]  classes={dict(Counter(classes))}")

    print("\n=== paired comparisons on PWC (priority-weighted, w_urllc=5.0) ===")
    results_pwc = [report_pair(by_slot_arm, slots, a, b, "pwc") for a, b in PAIRS]

    print("\n=== paired comparisons on PWC_eq (equal-weight) -- ranking agree or flip? ===")
    results_eq = [report_pair(by_slot_arm, slots, a, b, "pwc_eq") for a, b in PAIRS]

    print("\n=== partial replication spot-check (5/30 rows, NOT a powered independent test) ===")
    for r in repl:
        key = (int(r["slot_seed"]), r["arm"])
        pr = by_slot_arm.get(key)
        match = "MATCH" if pr and pr["shed_classification"] == r["shed_classification"] else "MISMATCH"
        print(f"  slot={r['slot_seed']:>4s} arm={r['arm']:14s} primary={pr['shed_classification'] if pr else '?':22s} "
              f"replication={r['shed_classification']:22s} [{match}]")

    return dict(pwc=results_pwc, pwc_eq=results_eq)


if __name__ == "__main__":
    main()
