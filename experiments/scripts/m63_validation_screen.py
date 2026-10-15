#!/usr/bin/env python3
"""M63: greedy validation-rollout collapse screen for trained AXIOM checkpoints.

For each checkpoint, run a few greedy episodes on the seed's OWN training
stream (env seed = training seed, never the 5000+seed eval stream) and
record how many requests it blocks and what share target mMTC. A policy
that blocks nothing in validation is flagged as collapsed. Eval logs are
read only afterwards, to score the screen.

Usage (cwd = framework/):
    ../venv/bin/python3 ../experiments/scripts/m63_validation_screen.py \
        --root ../experiments/results/m62_scaling --n 7 19 --out screen.json [--backlog-reset]
"""
import argparse
import collections
import json
import os
import sys
import tempfile

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/framework")

import m6_run_experiment as m6  # noqa: E402
from m62_shared_env import shared_factory  # noqa: E402
from m62_analysis import eval_log, seed_metrics  # noqa: E402
from qoe_oran_framework.config import load_saclb_config  # noqa: E402
from qoe_oran_framework.env import RANEnv  # noqa: E402
from qoe_oran_framework.marl.ctde_policy import GatCtdeMarlPolicy  # noqa: E402
from qoe_oran_framework.marl.marl_env import node_feature_dim, request_context_dim  # noqa: E402
from qoe_oran_framework.marl.marl_training import run_episodes_marl  # noqa: E402
from qoe_oran_framework.omega_logger import OmegaLogger  # noqa: E402

CONFIGS = {3: "qoe_oran_framework/configs/saclb_offline_dqn.yaml",
           7: "qoe_oran_framework/configs/saclb_offline_dqn_n7.yaml",
           19: "qoe_oran_framework/configs/saclb_offline_dqn_n19.yaml"}


def validate(cfg, topology, ckpt, seed, episodes):
    n = len(cfg.gnb_ids)
    adj = m6.adjacency_for(topology, n)
    policy = GatCtdeMarlPolicy(n, node_feature_dim(cfg), request_context_dim(cfg), m6.ACTION_DIM, adj)
    policy.load_checkpoint(ckpt)
    sd = {sid: spec.sd for sid, spec in cfg.slice_by_id.items()}
    env = RANEnv(cfg, shared_factory(cfg, sd)(seed), seed=seed, reward_mode="sla")
    blk = collections.Counter()
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "v.jsonl")
        with OmegaLogger(path) as omega:
            run_episodes_marl(env, policy, "gat_ctde", omega, episodes, seed, "val", "offline_val", False, cfg)
        for line in open(path):
            ev = json.loads(line).get("evidence", {})
            if ev.get("rollup"):
                blk.update(ev.get("episode_block_by_slice", {}))
    env.close()
    total = sum(blk.values())
    return {"blocks": total, "mmtc_share": blk["mmtc"] / total if total else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--n", type=int, nargs="+", default=[7, 19])
    ap.add_argument("--topologies", nargs="+", default=["fully_connected", "ring", "hex"])
    ap.add_argument("--layout", default="n{n}_{topo}", help="subdirectory pattern under --root")
    ap.add_argument("--seeds", type=int, nargs="+", default=list(range(900, 912)) + [1000, 1001, 1002])
    ap.add_argument("--episodes", type=int, default=5)
    ap.add_argument("--backlog-reset", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.backlog_reset:
        from m62_reviewer_experiments import install_backlog_reset
        install_backlog_reset()
    rows = []
    for n in a.n:
        cfg = load_saclb_config(CONFIGS[n])
        for topo in a.topologies:
            cell = os.path.join(a.root, a.layout.format(n=n, topo=topo))
            for s in a.seeds:
                ckpt = f"{cell}/gat_ctde/seed{s}/train/checkpoint.pt"
                if not os.path.exists(ckpt):
                    continue
                v = validate(cfg, topo, ckpt, s, a.episodes)
                ev = seed_metrics(eval_log(cell, "gat_ctde", s))
                row = {"n": n, "topology": topo, "seed": s, "val_blocks": v["blocks"],
                       "val_mmtc_share": v["mmtc_share"], "eval_collapsed": ev["collapsed"],
                       "eval_priority_sla": 0.5 * (ev["sla"]["urllc"] + ev["sla"]["embb"])}
                rows.append(row)
                print(json.dumps(row), flush=True)
    json.dump(rows, open(a.out, "w"), indent=1)
    flagged = [r for r in rows if r["val_blocks"] == 0]
    tp = sum(r["eval_collapsed"] for r in flagged)
    print(f"cells={len(rows)} eval_collapsed={sum(r['eval_collapsed'] for r in rows)} "
          f"flagged={len(flagged)} true_pos={tp} false_pos={len(flagged) - tp} "
          f"missed={sum(r['eval_collapsed'] for r in rows) - tp}")


if __name__ == "__main__":
    main()
