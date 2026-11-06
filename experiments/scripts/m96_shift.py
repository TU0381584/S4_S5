#!/usr/bin/env python3
"""M96 b and c: stored Env B checkpoints of every learned policy, and the rules, under shifted load.

Pre-registered in docs/PAPER5_M96_preregistration.md. Generalises m72_shift.py (AXIOM and the tuned rule only)
to the learned baselines, with neither policies retrained nor rules re-tuned. The simulator's module constants are
set before the environment is built, exactly as m72_shift.setup does, and each evaluation is the usual 50 episodes
on the held-out stream 5000 + seed. Nothing in the framework is modified.

  --validate   run under nominal conditions and compare each policy's log with its stored evaluation (must be exact)

Usage (cwd = framework/):
  m96_shift.py --cell m64/n7_ring --n 7 --topology ring --shift load_1.10 --arms axiom2 mappo_tuned single_agent_dqn \
      independent_dqn rule_local --seeds 900 901 --out ../experiments/results/m96/B_shift/n7_ring
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m72_shift as m72  # noqa: E402  (imports m64_run, which puts the framework on sys.path)
import m64_run  # noqa: E402
import m62_reviewer_experiments as m62  # noqa: E402
from m64_axiom2 import AxiomV2Policy  # noqa: E402
from m64_mappo import MappoPolicy  # noqa: E402
from m66_verify import find_eval, read  # noqa: E402
from qoe_oran_framework.marl.independent_dqn_ablation import IndependentPerGnbDqnPolicy  # noqa: E402
from qoe_oran_framework.marl.marl_env import node_feature_dim, request_context_dim  # noqa: E402
from qoe_oran_framework.mc_runner import build_policy, run_mc  # noqa: E402

RES = "/home/kmanojp/oranslice_rig/experiments/results"


def rule_for(cell, arm):
    if arm == "rule_static":
        return dict(tau_c=0.0)
    if arm == "rule_local_transfer":       # the local rule tuned at seven gNBs, carried over as in M75 D and M76 b1
        return json.load(open(f"{RES}/m64/n7_hex/rule_local_selection.json"))["selected"]
    return json.load(open(f"{RES}/{cell}/rule_local_selection.json"))["selected"]


def eval_arm(arm, cell, cfg, factory, nbrs, adj, s, out):
    n, nd, cdim = len(cfg.gnb_ids), node_feature_dim(cfg), request_context_dim(cfg)
    seed = m64_run.EVAL_OFFSET + s
    d = f"{out}/{arm}/seed{s}"
    shutil.rmtree(d, ignore_errors=True)             # the omega logger appends, so never reuse a directory
    ck = f"{RES}/{cell}/{arm}/seed{s}/train"
    if arm.startswith("rule_"):
        return m64_run.rule_eval(cfg, factory, rule_for(cell, arm), nbrs, seed, 50, f"{d}/eval", "offline_eval")
    if arm == "single_agent_dqn":
        def pf(_s):
            p = build_policy("dqn", cfg)
            p.load_checkpoint(f"{ck}/dqn/offline_train/rep_0/checkpoint.pt")
            return p
        run_mc(cfg, "dqn", factory, n_reps=1, episodes_per_rep=50, base_seed=seed, mode="offline_eval", training=False,
               results_dir=f"{d}/eval", policy_factory=pf, reward_mode="sla")
        return f"{d}/eval/dqn/offline_eval/rep_0/omega_log.jsonl"
    if arm == "axiom2":
        pol = AxiomV2Policy(n, nd, cdim, 2, adj)
    elif arm == "independent_dqn":
        pol = IndependentPerGnbDqnPolicy(n, nd, cdim, 2, learning_rate=1e-3)
    elif arm == "mappo_tuned":
        pol = MappoPolicy(n, nd, cdim)
    else:
        raise ValueError(arm)
    pol.load_checkpoint(f"{ck}/checkpoint.pt")
    return m64_run.eval_marl(cfg, factory, pol, arm, s, out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--topology", required=True)
    ap.add_argument("--shift", required=True, choices=list(m72.SHIFTS))
    ap.add_argument("--arms", nargs="+", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--validate", action="store_true")
    a = ap.parse_args()
    m62.install_backlog_reset()
    cfg, factory, nbrs, adj = m72.setup(a.n, a.topology, "nominal" if a.validate else a.shift)
    out_dir = f"{a.out}/{'nominal_check' if a.validate else a.shift}"
    res = {}
    for s in a.seeds:
        for arm in a.arms:
            p = eval_arm(arm, a.cell, cfg, factory, nbrs, adj, s, out_dir)
            r = m72.summarise(p)
            row = {**r}
            if a.validate:
                st = read(find_eval(a.cell, arm, s))
                mine = read(p)
                row["exact"] = st["reward"] == mine["reward"] and st["blocks"] == mine["blocks"] and st["sla"] == mine["sla"]
            res.setdefault(str(s), {})[arm] = row
            print(f"[m96 {a.cell} {a.shift if not a.validate else 'validate'}] seed {s} {arm} reward {r['reward']:.3f}"
                  + (f" exact={row['exact']}" if a.validate else ""), flush=True)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    tag = "validate" if a.validate else a.shift
    json.dump(res, open(f"{a.out}/{tag}_{'_'.join(a.arms)}_{min(a.seeds)}-{max(a.seeds)}.json", "w"), indent=1)


if __name__ == "__main__":
    main()
