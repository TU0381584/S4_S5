#!/usr/bin/env python3
"""Parameters used at execution per learned arm at N=37, counted exactly as
m64_complexity.py counts them at N = 3, 7 and 19 (same modules, same
exclusions). With --timing, greedy inference time per control step is also
measured exactly as m64_complexity.py measures it (one CPU thread, one pending
request per gNB per slice, 20 warm-up and 300 timed steps); run it on an idle
machine.

Usage (cwd = framework/): m73_complexity.py --out ../experiments/results/m73/complexity_n37.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m73_run  # noqa: E402  (registers the N=37 config and hex layout)
import m6_run_experiment as m6  # noqa: E402
from m64_axiom2 import AxiomV2Policy, MlpAxiomV2Policy  # noqa: E402
from m64_complexity import count  # noqa: E402
from m64_mappo import MappoPolicy  # noqa: E402
from qoe_oran_framework.config import load_saclb_config  # noqa: E402
from qoe_oran_framework.marl.independent_dqn_ablation import IndependentPerGnbDqnPolicy  # noqa: E402
from qoe_oran_framework.marl.marl_env import node_feature_dim, request_context_dim  # noqa: E402
from qoe_oran_framework.mc_runner import build_policy  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--timing", action="store_true")
    ap.add_argument("--reps", type=int, default=300)
    a = ap.parse_args()
    m73_run.install()
    n = 37
    cfg = load_saclb_config(m73_run.N37_CONFIG)
    nd, cd = node_feature_dim(cfg), request_context_dim(cfg)
    adj = m6.adjacency_for("ring", n)
    ax, mlp = AxiomV2Policy(n, nd, cd, 2, adj), MlpAxiomV2Policy(n, nd, cd, 2, adj)
    ind, mp, sa = IndependentPerGnbDqnPolicy(n, nd, cd, 2), MappoPolicy(n, nd, cd), build_policy("dqn", cfg)
    res = {"axiom2": count([ax.online.encoder, ax.online.q_head]), "axiom2_mlp": count([mlp.online.encoder, mlp.online.q_head]),
           "independent_dqn": count([g.q_network for g in ind.agents]), "mappo": count([mp.actor]),
           "mappo_total": count([mp.actor, mp.critic]), "single_agent_dqn": count([sa.q_network])}
    out = {"37": {k: {"params_execution": int(v)} for k, v in res.items()}}
    if a.timing:
        import time
        import numpy as np
        import torch
        torch.set_num_threads(1)
        rng = np.random.RandomState(0)
        reqs = [(i, np.eye(cd, dtype=np.float32)[k % cd]) for i in range(n) for k in range(3)]
        nf = rng.rand(n, nd).astype(np.float32)
        for name, pol in (("axiom2", ax), ("axiom2_mlp", mlp), ("independent_dqn", ind), ("mappo", mp)):
            for _ in range(20):
                pol.select_actions(nf, reqs, training=False)
            t0 = time.perf_counter()
            for _ in range(a.reps):
                pol.select_actions(nf, reqs, training=False)
            out["37"][name]["ms_per_step"] = round(1000 * (time.perf_counter() - t0) / a.reps, 3)
            out["37"][name]["requests_per_step"] = len(reqs)
        # single-agent DQN: one select_action per pending request on its flattened request state,
        # the same per-step workload; measured at every size because m64/complexity.json has no
        # single-agent latency
        from qoe_oran_framework.env import request_state_dim
        out["single_agent_ms_per_step"] = {}
        for nn_ in (3, 7, 19, 37):
            cfg_ = load_saclb_config(m73_run.N37_CONFIG if nn_ == 37 else m73_run.m64_run.CONFIGS[nn_])
            pol = build_policy("dqn", cfg_)
            states = rng.rand(3 * nn_, request_state_dim(cfg_)).astype(np.float32)
            for _ in range(20):
                for st in states:
                    pol.select_action(st, training=False)
            t0 = time.perf_counter()
            for _ in range(a.reps):
                for st in states:
                    pol.select_action(st, training=False)
            out["single_agent_ms_per_step"][str(nn_)] = round(1000 * (time.perf_counter() - t0) / a.reps, 3)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
