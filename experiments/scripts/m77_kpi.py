#!/usr/bin/env python3
"""M77: throughput and backlog-delay measurements for stored checkpoints and rules.

The evaluation logs record decisions, rewards and SLA flags but not the PRBs
served or the queue backlog. This script re-runs the usual evaluation (stream
5000 + seed, 50 episodes) of a stored checkpoint or a rule with a recorder on
the simulator's per-step output. For every step, gNB and slice it sums the
PRBs served and the backlog over that slice's UE samples, and reads the
offered demand from the source. Re-evaluation is deterministic, and every run
is checked against the stored evaluation log (reward, blocks, SLA) before its
measurements are used. Plan: docs/PAPER5_M77_plan.md. The framework is not modified.

Usage (cwd = framework/):
  m77_kpi.py --env A --n 3 --topology fully_connected --cell m65_n3_view --arm axiom2 --seeds 900 901 --out DIR
  m77_kpi.py ... --arm rule_static|rule_accept_all|rule_local_transfer|rule_local_cell
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m73_run  # noqa: E402  (registers N=37; puts the framework on sys.path via m64_run)
import m64_run  # noqa: E402
import coupled_dynamic_kpm_source as cd  # noqa: E402
import m62_reviewer_experiments as m62  # noqa: E402
import m6_run_experiment as m6  # noqa: E402
from m64_axiom2 import AxiomV2Policy  # noqa: E402
from m64_mappo import MappoPolicy  # noqa: E402
from m66_verify import find_eval, read  # noqa: E402
from qoe_oran_framework.config import load_saclb_config  # noqa: E402
from qoe_oran_framework.marl.independent_dqn_ablation import IndependentPerGnbDqnPolicy  # noqa: E402
from qoe_oran_framework.marl.marl_env import node_feature_dim, request_context_dim  # noqa: E402
from qoe_oran_framework.mc_runner import build_policy  # noqa: E402

RES = "/home/kmanojp/oranslice_rig/experiments/results"
SLICES = ("urllc", "embb", "mmtc")
REC = {"rows": []}


def recording(factory, sd_to_slice):
    def wf(seed):
        src = factory(seed)
        orig = src.poll

        def poll():
            samples = orig()
            served, backlog = {}, {}
            for u in samples:
                key = (u.gnb_id, sd_to_slice[u.nssai_sd])
                served[key] = served.get(key, 0.0) + u.avg_prbs_dl
                backlog[key] = backlog.get(key, 0.0) + u.dl_mac_buffer_occupation
            REC["rows"].append({k: (served[k], backlog[k], float(src._offered[k])) for k in served})
            return samples
        src.poll = poll
        return src
    return wf


def kpis(rows):
    out = {}
    for sl in SLICES:
        sv = np.array([v[0] for r in rows for k, v in r.items() if k[1] == sl])
        bl = np.array([v[1] for r in rows for k, v in r.items() if k[1] == sl])
        of = np.array([v[2] for r in rows for k, v in r.items() if k[1] == sl])
        ratio = bl[sv > 1e-9] / sv[sv > 1e-9]
        out[sl] = {"served_prb": float(sv.mean()), "offered_prb": float(of.mean()), "served_over_offered": float(sv.sum() / of.sum()),
                   "backlog_prb": float(bl.mean()), "delay_steps": float(bl.mean() / sv.mean()) if sv.mean() > 0 else None,
                   "delay_steps_p95": float(np.percentile(ratio, 95)) if len(ratio) else None, "n": int(len(sv))}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", choices=["A", "B"], required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--topology", default="fully_connected")
    ap.add_argument("--cell", required=True, help="stored cell under experiments/results")
    ap.add_argument("--arm", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    m73_run.install()
    m62.install_backlog_reset()
    cfg = load_saclb_config(m64_run.CONFIGS[a.n])
    sd = {k: v.sd for k, v in cfg.slice_by_id.items()}
    sd_to_slice = {v: k for k, v in sd.items()}
    if a.env == "A":
        from shared_budget_kpm_source import make_shared_budget_factory
        base = make_shared_budget_factory(cfg, sd)
    else:
        base = cd.make_coupled_factory(cfg, sd, topology=a.topology)
    factory = recording(base, sd_to_slice)
    nbrs = cd.neighbour_lists(a.n, a.topology)
    adj = m6.adjacency_for(a.topology, a.n)
    n, nd, cdim = len(cfg.gnb_ids), node_feature_dim(cfg), request_context_dim(cfg)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    res = {}
    for s in a.seeds:
        REC["rows"] = []
        d = f"{a.out}/{a.arm}/seed{s}"
        seed = m64_run.EVAL_OFFSET + s
        if a.arm.startswith("rule_"):
            if a.arm == "rule_static":
                rule = dict(tau_c=0.0)
            elif a.arm == "rule_accept_all":
                rule = dict()
            elif a.arm == "rule_local_transfer":
                rule = json.load(open(f"{RES}/m64/n7_hex/rule_local_selection.json"))["selected"]
            else:                                   # rule_local_cell: the rule tuned in this cell
                rule = json.load(open(f"{RES}/{a.cell}/rule_local_selection.json"))["selected"]
            log = m64_run.rule_eval(cfg, factory, rule, nbrs, seed, 50, f"{d}/eval", "offline_eval")
        elif a.arm == "single_agent_dqn":
            ckpt = f"{RES}/{a.cell}/single_agent_dqn/seed{s}/train/dqn/offline_train/rep_0/checkpoint.pt"

            def pf(_s, ckpt=ckpt):
                p = build_policy("dqn", cfg)
                p.load_checkpoint(ckpt)
                return p
            m64_run.run_mc(cfg, "dqn", factory, n_reps=1, episodes_per_rep=50, base_seed=seed, mode="offline_eval", training=False,
                           results_dir=f"{d}/eval", policy_factory=pf, reward_mode="sla")
            log = f"{d}/eval/dqn/offline_eval/rep_0/omega_log.jsonl"
        else:
            pol = {"axiom2": lambda: AxiomV2Policy(n, nd, cdim, 2, adj), "independent_dqn": lambda: IndependentPerGnbDqnPolicy(n, nd, cdim, 2),
                   "mappo_tuned": lambda: MappoPolicy(n, nd, cdim)}[a.arm]()
            pol.load_checkpoint(f"{RES}/{a.cell}/{a.arm}/seed{s}/train/checkpoint.pt")
            log = m64_run.eval_marl(cfg, factory, pol, a.arm, s, a.out)
        new = read(log)
        stored_arm = {"rule_static": "rule_static", "rule_accept_all": "rule_accept_all", "rule_local_transfer": "rule_local_transfer",
                      "rule_local_cell": "rule_local"}.get(a.arm, a.arm)
        sp = find_eval(a.cell, stored_arm, s) or (find_eval(a.cell, "heuristic", s) if a.arm == "rule_static" else None)
        old = read(f"{RES}/{sp}" if sp and not sp.startswith("/") else sp) if sp else None
        same = None if old is None else (new["reward"] == old["reward"] and new["blocks"] == old["blocks"] and new["sla"] == old["sla"])
        res[s] = {"reproduces_stored": same, "reward": new["reward"], "kpi": kpis(REC["rows"])}
        print(f"[m77 {a.env}{a.n} {a.arm}] seed {s} reproduces={same} urllc delay {res[s]['kpi']['urllc']['delay_steps']:.3f} "
              f"embb served/offered {res[s]['kpi']['embb']['served_over_offered']:.3f}", flush=True)
    json.dump(res, open(f"{a.out}/{a.arm}_{min(a.seeds)}-{max(a.seeds)}.json", "w"), indent=1)


if __name__ == "__main__":
    main()
