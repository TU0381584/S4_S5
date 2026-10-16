#!/usr/bin/env python3
"""Model complexity per learned arm: trainable parameters and per-step
inference latency (one greedy decision for every pending request of a
step, CPU, single thread), at N = 3, 7, and 19. Training wall-clock is
read separately from the campaign result JSONs (train_seconds).

Usage (cwd = framework/): m64_complexity.py --out ../experiments/results/m64/complexity.json
"""
import argparse
import json
import sys
import time

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/framework")

import numpy as np  # noqa: E402
import torch  # noqa: E402

torch.set_num_threads(1)

import m6_run_experiment as m6  # noqa: E402
from m64_axiom2 import AxiomV2Policy, MlpAxiomV2Policy  # noqa: E402
from m64_mappo import MappoPolicy  # noqa: E402
from qoe_oran_framework.config import load_saclb_config  # noqa: E402
from qoe_oran_framework.marl.independent_dqn_ablation import IndependentPerGnbDqnPolicy  # noqa: E402
from qoe_oran_framework.marl.marl_env import node_feature_dim, request_context_dim  # noqa: E402
from qoe_oran_framework.mc_runner import build_policy  # noqa: E402

CONFIGS = {3: "qoe_oran_framework/configs/saclb_offline_dqn.yaml",
           7: "qoe_oran_framework/configs/saclb_offline_dqn_n7.yaml",
           19: "qoe_oran_framework/configs/saclb_offline_dqn_n19.yaml"}


def count(mods):
    return sum(p.numel() for m in mods for p in m.parameters() if p.requires_grad)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--reps", type=int, default=300)
    a = ap.parse_args()
    out = {}
    rng = np.random.RandomState(0)
    for n in (3, 7, 19):
        cfg = load_saclb_config(CONFIGS[n])
        nd, cd = node_feature_dim(cfg), request_context_dim(cfg)
        adj = m6.adjacency_for("fully_connected" if n == 3 else "ring", n)
        # one step's pending requests: one per gNB per slice, the synthetic arrival rate's order of magnitude
        reqs = [(i, np.eye(cd, dtype=np.float32)[k % cd]) for i in range(n) for k in range(3)]
        nf = rng.rand(n, nd).astype(np.float32)
        arms = {
            "axiom2": AxiomV2Policy(n, nd, cd, 2, adj),
            "axiom2_mlp": MlpAxiomV2Policy(n, nd, cd, 2, adj),
            "independent_dqn": IndependentPerGnbDqnPolicy(n, nd, cd, 2),
            "mappo": MappoPolicy(n, nd, cd),
        }
        res = {}
        for name, pol in arms.items():
            if name == "mappo":
                params = count([pol.actor, pol.critic])
                exec_params = count([pol.actor])            # the critic is used only in training
            elif name == "independent_dqn":
                params = count([ag.q_network for ag in pol.agents])   # online networks, one per gNB
                exec_params = params
            else:
                params = count([pol.online.encoder, pol.online.q_head])  # the unused QMIX mixer is excluded
                exec_params = params
            for _ in range(20):
                pol.select_actions(nf, reqs, training=False)
            t0 = time.perf_counter()
            for _ in range(a.reps):
                pol.select_actions(nf, reqs, training=False)
            ms = 1000 * (time.perf_counter() - t0) / a.reps
            res[name] = {"params_total": int(params), "params_execution": int(exec_params),
                         "ms_per_step": round(ms, 3), "requests_per_step": len(reqs)}
        sa = build_policy("dqn", cfg)
        res["single_agent_dqn"] = {"params_total": int(count([sa.q_network])), "params_execution": int(count([sa.q_network]))}
        out[n] = res
        print(n, json.dumps(res))
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
