#!/usr/bin/env python3
"""M64 calibration probe for Env B, heuristics only, on PILOT seeds (2000+).

For given coupling alpha and load amplitude, evaluates the rule families
(accept_all, static, local, neighbour) on pilot-seed training streams and
reports the best rule per family by mean reward, with per-slice SLA. Used
only to choose Env B's two constants before pre-registration; no reported
seed is touched.

Usage (cwd = framework/):
  m64_calibrate.py --n 3 --topology fully_connected --alpha 0.08 --amp 0.15 --seeds 2000 2001 2002
"""
import argparse
import itertools
import json
import os
import statistics as st
import sys
import tempfile

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/framework")
import coupled_dynamic_kpm_source as cd  # noqa: E402
import m62_reviewer_experiments as m62  # noqa: E402
from m2_correctness_metrics import per_seed_metrics  # noqa: E402
from m64_heuristics import ThresholdHeuristic  # noqa: E402
from qoe_oran_framework.config import load_saclb_config  # noqa: E402
from qoe_oran_framework.mc_runner import run_mc  # noqa: E402

CONFIGS = {3: "qoe_oran_framework/configs/saclb_offline_dqn.yaml",
           7: "qoe_oran_framework/configs/saclb_offline_dqn_n7.yaml",
           19: "qoe_oran_framework/configs/saclb_offline_dqn_n19.yaml"}
COARSE = {
    "accept_all": [dict()],
    "static": [dict(tau_c=0.0)],
    "local": [dict(tau_c=c) for c in (0.85, 0.9, 0.95, 0.98)] + [dict(tau_q=q) for q in (0.05, 0.1, 0.2)]
             + [dict(tau_c=c, tau_q=q) for c, q in itertools.product((0.9, 0.95), (0.1, 0.2))],
    "local_embb": [dict(tau_c=c, tau_q=q, tau_e=e) for c, q, e in itertools.product((0.95, 1.01), (0.1, 0.2), (0.05, 0.1, 0.2, 0.4))],
    "neighbour_embb": [dict(tau_c=c, tau_q=q, tau_e=e, tau_n=n) for c, q, e, n in itertools.product((0.95, 1.01), (0.1, 0.2), (0.05, 0.1, 0.2), (0.85, 0.9, 0.95))],
    "neighbour": [dict(tau_c=c, tau_q=q, tau_n=n) for c, q, n in itertools.product((0.95, 1.01), (0.1, None), (0.85, 0.9, 0.95))],
}


def slice_comp(path):
    acc = {}
    for l in open(path):
        ev = json.loads(l).get("evidence", {})
        if isinstance(ev, dict) and ev.get("rollup"):
            for k, v in ev["episode_sla_compliance_by_slice"].items():
                acc.setdefault(k, []).append(v)
    return {k: st.mean(v) for k, v in acc.items()}


def evaluate(cfg, factory, rule, seeds, episodes, nbrs):
    rows = []
    for s in seeds:
        with tempfile.TemporaryDirectory() as td:
            run_mc(cfg, "lb_only", factory, n_reps=1, episodes_per_rep=episodes, base_seed=s,
                   mode="offline_select", training=False, results_dir=td,
                   policy_factory=lambda _s: ThresholdHeuristic(cfg.gnb_ids, nbrs, **rule), reward_mode="sla")
            p = f"{td}/lb_only/offline_select/rep_0/omega_log.jsonl"
            r, mb, tb = per_seed_metrics(p)
            rows.append((r, slice_comp(p)))
    return st.mean(x[0] for x in rows), {k: st.mean(x[1][k] for x in rows) for k in rows[0][1]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--topology", default="fully_connected")
    ap.add_argument("--alpha", type=float, required=True)
    ap.add_argument("--amp", type=float, required=True)
    ap.add_argument("--base", type=float, default=1.0)
    ap.add_argument("--seeds", type=int, nargs="+", default=[2000, 2001, 2002])
    ap.add_argument("--episodes", type=int, default=10)
    ap.add_argument("--lam-mmtc", type=float, default=None, help="mMTC violation penalty (config default 2.5)")
    a = ap.parse_args()
    cd.COUPLING_ALPHA, cd.LOAD_AMPLITUDE, cd.LOAD_BASE = a.alpha, a.amp, a.base
    m62.install_backlog_reset()
    cfg = load_saclb_config(CONFIGS[a.n])
    if a.lam_mmtc is not None:
        cfg.slice_by_id["mmtc"].violation_penalty = a.lam_mmtc
    sd = {k: v.sd for k, v in cfg.slice_by_id.items()}
    factory = cd.make_coupled_factory(cfg, sd, topology=a.topology)
    nbrs = cd.neighbour_lists(len(cfg.gnb_ids), a.topology)
    best = {}
    for fam, rules in COARSE.items():
        res = [(evaluate(cfg, factory, r, a.seeds, a.episodes, nbrs), r) for r in rules]
        (rew, sla), rule = max(res, key=lambda x: x[0][0])
        best[fam] = (rew, sla, rule)
        print(f"N={a.n} {a.topology} alpha={a.alpha} amp={a.amp} base={a.base} lam={a.lam_mmtc} {fam:10s} best={rew:8.3f} "
              f"urllc={sla['urllc']:.3f} embb={sla['embb']:.3f} mmtc={sla['mmtc']:.3f} rule={rule}", flush=True)
    s, l = best["static"][0], max(best["local"][0], best["local_embb"][0])
    nb = max(best["neighbour"][0], best["neighbour_embb"][0])
    triv = max(best["static"][0], best["accept_all"][0])
    print(f"ADAPT N={a.n} alpha={a.alpha} amp={a.amp} base={a.base} lam={a.lam_mmtc}: best_trivial={triv:.2f} "
          f"local={best['local'][0]:.2f} local_embb={best['local_embb'][0]:.2f} nb={nb:.2f} "
          f"nb_embb={best['neighbour_embb'][0]:.2f} adaptive_gain={100 * (l - triv) / abs(triv):+.1f}% "
          f"neighbour_gain={100 * (nb - l) / abs(l):+.1f}%", flush=True)
    fam = max(("local", "local_embb", "neighbour", "neighbour_embb"), key=lambda f: best[f][0])
    sla = best[fam][1]
    print(f"BESTSLA N={a.n} alpha={a.alpha} amp={a.amp} base={a.base} lam={a.lam_mmtc}: {fam} urllc={sla['urllc']:.3f} "
          f"embb={sla['embb']:.3f} mmtc={sla['mmtc']:.3f} | static urllc={best['static'][1]['urllc']:.3f} embb={best['static'][1]['embb']:.3f} "
          f"| accept urllc={best['accept_all'][1]['urllc']:.3f} embb={best['accept_all'][1]['embb']:.3f}", flush=True)
    print(f"SUMMARY N={a.n} {a.topology} alpha={a.alpha} amp={a.amp} base={a.base} lam={a.lam_mmtc}: static={s:.2f} local={l:.2f} nb={nb:.2f} "
          f"local-static={l - s:+.3f} ({100 * (l - s) / abs(s):+.1f}%) neighbour-local={nb - l:+.3f} "
          f"({100 * (nb - l) / abs(l):+.1f}%) accept_all={best['accept_all'][0]:.3f}", flush=True)


if __name__ == "__main__":
    main()
