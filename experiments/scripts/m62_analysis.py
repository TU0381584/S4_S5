#!/usr/bin/env python3
"""M62 analysis: per-arm metrics from eval omega logs, paired tests against
AXIOM with Holm correction, and per-slice SLA compliance.

Metrics per seed (from the eval omega log only):
  reward       mean reward per step (m2_correctness_metrics.per_seed_metrics)
  precision    mMTC-targeted blocks / total blocks (undefined when 0 blocks)
  collapsed    True when the policy never blocks in evaluation
  sla[k]       mean per-episode SLA compliance of slice k

Usage:
    venv/bin/python3 experiments/scripts/m62_analysis.py --root experiments/results/m62_reviewer/base \
        --arms axiom independent_dqn single_agent_dqn heuristic --out experiments/results/m62_reviewer/base_summary.json
"""
import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
from m2_correctness_metrics import per_seed_metrics  # noqa: E402

RNG = np.random.RandomState(0)


def eval_log(root: str, arm: str, seed: int):
    pats = [f"{root}/{arm}/seed{seed}/eval/omega_log.jsonl",
            f"{root}/{arm}/seed{seed}/eval/dqn/offline_eval/rep_0/omega_log.jsonl",
            f"{root}/{arm}/seed{seed}/eval/lb_only/offline_eval/rep_0/omega_log.jsonl"]
    for p in pats:
        if Path(p).exists():
            return p
    return None


def slice_compliance(path: str) -> dict:
    acc = {}
    for line in open(path):
        rec = json.loads(line)
        ev = rec.get("evidence", rec)
        if isinstance(ev, dict) and ev.get("rollup"):
            for k, v in ev["episode_sla_compliance_by_slice"].items():
                acc.setdefault(k, []).append(v)
    return {k: float(np.mean(v)) for k, v in acc.items()}


def seed_metrics(path: str) -> dict:
    reward, mmtc_b, total_b = per_seed_metrics(path)
    return {"reward": float(reward), "mmtc_blocks": int(mmtc_b), "total_blocks": int(total_b),
            "precision": (mmtc_b / total_b) if total_b > 0 else None, "collapsed": total_b == 0,
            "sla": slice_compliance(path)}


def boot_ci(x, n=10000):
    x = np.asarray(x, float)
    means = x[RNG.randint(0, len(x), (n, len(x)))].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def holm(pvals: dict) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def summarise(root: str, arms, seeds, ref: str = "axiom") -> dict:
    per = {}
    for arm in arms:
        rows = {}
        for s in seeds:
            p = eval_log(root, arm, s)
            if p:
                rows[s] = seed_metrics(p)
        per[arm] = rows
    summary = {}
    for arm, rows in per.items():
        if not rows:
            continue
        r = [v["reward"] for v in rows.values()]
        prec = [v["precision"] for v in rows.values() if v["precision"] is not None]
        slices = sorted({k for v in rows.values() for k in v["sla"]})
        summary[arm] = {
            "n": len(rows), "reward_mean": float(np.mean(r)), "reward_ci": boot_ci(r),
            "precision_mean": float(np.mean(prec)) if prec else None,
            "precision_ci": boot_ci(prec) if len(prec) > 1 else None,
            "n_blocking": len(prec), "collapsed": sum(v["collapsed"] for v in rows.values()),
            "sla": {k: float(np.mean([v["sla"].get(k, np.nan) for v in rows.values()])) for k in slices},
            "per_seed": {str(k): v for k, v in rows.items()},
        }
    tests = {}
    if ref in per:
        for arm in per:
            if arm == ref:
                continue
            common = sorted(set(per[ref]) & set(per[arm]))
            if len(common) < 5:
                continue
            d = np.array([per[ref][s]["reward"] - per[arm][s]["reward"] for s in common])
            p = float(wilcoxon(d).pvalue) if np.any(d != 0) else 1.0
            base = np.mean([per[arm][s]["reward"] for s in common])
            tests[arm] = {"n": len(common), "diff_mean": float(d.mean()), "diff_ci": boot_ci(d),
                          "rel_gain_pct": float(100 * d.mean() / abs(base)) if base else None,
                          "wins": int((d > 0).sum()), "ties": int((d == 0).sum()), "losses": int((d < 0).sum()),
                          "p": p}
        adj = holm({k: v["p"] for k, v in tests.items()})
        for k in tests:
            tests[k]["p_holm"] = adj[k]
    return {"root": root, "summary": summary, "paired_vs_" + ref: tests}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--arms", nargs="+", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", default=list(range(900, 930)))
    ap.add_argument("--ref", default="axiom")
    ap.add_argument("--out")
    a = ap.parse_args()
    res = summarise(a.root, a.arms, a.seeds, a.ref)
    for arm, s in res["summary"].items():
        prec = f"{s['precision_mean']:.3f}" if s["precision_mean"] is not None else "n/a"
        print(f"{arm:24s} n={s['n']:2d} reward={s['reward_mean']:7.3f} "
              f"[{s['reward_ci'][0]:.3f},{s['reward_ci'][1]:.3f}] precision={prec} "
              f"collapsed={s['collapsed']:2d} sla={ {k: round(v, 3) for k, v in s['sla'].items()} }")
    for arm, t in res["paired_vs_" + a.ref].items():
        print(f"  {a.ref} - {arm:22s} diff={t['diff_mean']:+.3f} [{t['diff_ci'][0]:+.3f},{t['diff_ci'][1]:+.3f}] "
              f"rel={t['rel_gain_pct']:+.1f}% W/T/L={t['wins']}/{t['ties']}/{t['losses']} "
              f"p={t['p']:.2g} p_holm={t['p_holm']:.2g}")
    if a.out:
        json.dump(res, open(a.out, "w"), indent=2)


if __name__ == "__main__":
    main()
