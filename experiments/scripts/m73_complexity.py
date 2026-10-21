#!/usr/bin/env python3
"""Parameters used at execution per learned arm at N=37, counted exactly as
m64_complexity.py counts them at N = 3, 7 and 19 (same modules, same
exclusions). Inference latency is not measured here.

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
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
