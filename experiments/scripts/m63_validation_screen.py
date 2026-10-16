#!/usr/bin/env python3
"""M63: greedy validation-rollout screen for trained checkpoints, any learned arm.

Pre-registered in docs/PAPER5_M63_preregistration.md. Each checkpoint runs
EPISODES greedy episodes on its seed's OWN training stream (env seed =
training seed, never the 5000+seed eval stream). It FAILS the screen if
it blocks nothing, or if fewer than 90% of its blocks target mMTC. Eval
logs are read only afterwards, to score the screen.

Usage (cwd = framework/):
    ../venv/bin/python3 ../experiments/scripts/m63_validation_screen.py \
        --cell ../experiments/results/m63_scaling/n19_ring --arm gat_ctde --n 19 --topology ring \
        --seeds 900 901 --backlog-reset --out screen.json
"""
import argparse
import collections
import glob
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
from qoe_oran_framework.mc_runner import build_policy, run_mc  # noqa: E402
from qoe_oran_framework.marl.ctde_policy import GatCtdeMarlPolicy  # noqa: E402
from qoe_oran_framework.marl.independent_dqn_ablation import IndependentPerGnbDqnPolicy  # noqa: E402
from qoe_oran_framework.marl.marl_env import node_feature_dim, request_context_dim  # noqa: E402
from qoe_oran_framework.marl.marl_training import run_episodes_marl  # noqa: E402
from qoe_oran_framework.omega_logger import OmegaLogger  # noqa: E402

CONFIGS = {3: "qoe_oran_framework/configs/saclb_offline_dqn.yaml",
           7: "qoe_oran_framework/configs/saclb_offline_dqn_n7.yaml",
           19: "qoe_oran_framework/configs/saclb_offline_dqn_n19.yaml"}
MIN_MMTC_SHARE = 0.9   # pre-registered, do not change


def _blocks(path):
    blk = collections.Counter()
    for line in open(path):
        ev = json.loads(line).get("evidence", {})
        if ev.get("rollup"):
            blk.update(ev.get("episode_block_by_slice", {}))
    return blk


ENV = "A"   # set by --env; B uses the M64 coupled time-varying simulator


def validate(cfg, arm, topology, cell, seed, episodes, mlp):
    sd = {sid: spec.sd for sid, spec in cfg.slice_by_id.items()}
    if ENV == "B":
        import coupled_dynamic_kpm_source as cdk
        factory = cdk.make_coupled_factory(cfg, sd, topology=topology)
    else:
        factory = shared_factory(cfg, sd)
    with tempfile.TemporaryDirectory() as td:
        if arm.startswith("single_agent_dqn"):
            ckpt = f"{cell}/{arm}/seed{seed}/train/dqn/offline_train/rep_0/checkpoint.pt"

            def pf(_s):
                p = build_policy("dqn", cfg)
                p.load_checkpoint(ckpt)
                return p
            run_mc(cfg, "dqn", factory, n_reps=1, episodes_per_rep=episodes, base_seed=seed,
                   mode="offline_val", training=False, results_dir=td, policy_factory=pf, reward_mode="sla")
            path = glob.glob(f"{td}/**/omega_log.jsonl", recursive=True)[0]
        else:
            ckpt = f"{cell}/{arm}/seed{seed}/train/checkpoint.pt"
            n = len(cfg.gnb_ids)
            nd, cd = node_feature_dim(cfg), request_context_dim(cfg)
            if arm.startswith("independent_dqn"):
                policy = IndependentPerGnbDqnPolicy(n, nd, cd, m6.ACTION_DIM)
            elif arm.startswith("mappo"):
                from m64_mappo import MappoPolicy
                policy = MappoPolicy(n, nd, cd)
            elif arm.startswith("axiom2") or (ENV == "B" and arm == "gat_ctde"):
                from m64_axiom2 import AxiomV2Policy, MlpAxiomV2Policy
                adj2 = m6.adjacency_for(topology, n)
                policy = (MlpAxiomV2Policy if (arm == "axiom2_mlp" or mlp) else AxiomV2Policy)(n, nd, cd, m6.ACTION_DIM, adj2)
                if arm == "axiom2_wide":
                    raise SystemExit("screen not defined for sensitivity variants")
            else:
                adj = m6.adjacency_for(topology, n)
                if mlp or arm == "axiom_mlp":
                    from m62_reviewer_experiments import MlpCtdeMarlPolicy
                    policy = MlpCtdeMarlPolicy(n, nd, cd, m6.ACTION_DIM, adj)
                else:
                    policy = GatCtdeMarlPolicy(n, nd, cd, m6.ACTION_DIM, adj)
            policy.load_checkpoint(ckpt)
            env = RANEnv(cfg, factory(seed), seed=seed, reward_mode="sla")
            path = os.path.join(td, "v.jsonl")
            with OmegaLogger(path) as omega:
                run_episodes_marl(env, policy, arm, omega, episodes, seed, "val", "offline_val", False, cfg)
            env.close()
        blk = _blocks(path)
    total = sum(blk.values())
    share = blk["mmtc"] / total if total else None
    return {"val_blocks": total, "val_mmtc_share": share,
            "fails": total == 0 or share < MIN_MMTC_SHARE}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", required=True, help="directory holding <arm>/seed*/")
    ap.add_argument("--arm", required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--topology", default="fully_connected")
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--episodes", type=int, default=5)
    ap.add_argument("--mlp", action="store_true", help="checkpoints use the per-node MLP encoder")
    ap.add_argument("--backlog-reset", action="store_true")
    ap.add_argument("--env", default="A", choices=["A", "B"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    global ENV
    ENV = a.env
    if a.backlog_reset:
        from m62_reviewer_experiments import install_backlog_reset
        install_backlog_reset()
    cfg = load_saclb_config(CONFIGS[a.n])
    rows = []
    for s in a.seeds:
        ev_path = eval_log(a.cell, a.arm, s)
        if not ev_path:
            continue
        v = validate(cfg, a.arm, a.topology, a.cell, s, a.episodes, a.mlp)
        ev = seed_metrics(ev_path)
        row = {"cell": a.cell, "arm": a.arm, "n": a.n, "topology": a.topology, "seed": s, **v,
               "eval_collapsed": ev["collapsed"], "eval_reward": ev["reward"],
               "eval_priority_sla": 0.5 * (ev["sla"]["urllc"] + ev["sla"]["embb"])}
        rows.append(row)
        print(json.dumps(row), flush=True)
    json.dump(rows, open(a.out, "w"), indent=1)
    bad = lambda r: r["eval_collapsed"] or r["eval_priority_sla"] < 0.5
    f = [r for r in rows if r["fails"]]
    print(f"cells={len(rows)} fail={len(f)} fail_and_bad={sum(bad(r) for r in f)} "
          f"pass_but_bad={sum(bad(r) for r in rows if not r['fails'])}")


if __name__ == "__main__":
    main()
