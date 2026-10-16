#!/usr/bin/env python3
"""M64: run any arm on Env B (coupled, time-varying shared-budget simulator).

Arms
  axiom                 GAT encoder + per-slice Q-heads (LR 1e-4)
  axiom_mlp             same, encoder replaced by a per-node MLP (ignores the graph)
  axiom_lr3e-5 / axiom_lr3e-4 / axiom_wide   AXIOM hyperparameter sensitivity
  independent_dqn       one DQN per gNB (LR 1e-3)
  single_agent_dqn      one DQN over the flattened joint state (LR 1e-3)
  mappo                 MAPPO, shared actor + centralised critic (m64_mappo.py)
  rule_static           shed every mMTC request (the Env A oracle)
  rule_accept_all       accept every request
  rule_local            best local-threshold rule, chosen on training streams
  rule_neighbour        best neighbour-aware rule, chosen on training streams

Every learned arm trains for 300 episodes on the seed's training stream and
is evaluated for 50 episodes on the held-out stream 5000 + seed. Rule
thresholds are chosen on training streams only. Env B constants come from
coupled_dynamic_kpm_source.py and are fixed in docs/PAPER5_M64_preregistration.md.

Usage (cwd = framework/):
  m64_run.py --arm axiom --n 3 --topology fully_connected --seeds 900 901 --out-dir ../experiments/results/m64/n3_fully_connected
"""
import argparse
import itertools
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/framework")

import torch  # noqa: E402

import coupled_dynamic_kpm_source as cd  # noqa: E402
import m2_run_experiment as m2  # noqa: E402
import m62_reviewer_experiments as m62  # noqa: E402
import m6_run_experiment as m6  # noqa: E402
from m2_correctness_metrics import per_seed_metrics  # noqa: E402
from m64_heuristics import ThresholdHeuristic  # noqa: E402
from m64_mappo import MappoPolicy, train_mappo  # noqa: E402
from qoe_oran_framework.config import load_saclb_config  # noqa: E402
from qoe_oran_framework.env import RANEnv  # noqa: E402
from qoe_oran_framework.marl.ctde_policy import GatCtdeMarlPolicy, GatCtdeNetwork  # noqa: E402
from qoe_oran_framework.marl.independent_dqn_ablation import IndependentPerGnbDqnPolicy  # noqa: E402
from qoe_oran_framework.marl.marl_env import node_feature_dim, request_context_dim  # noqa: E402
from qoe_oran_framework.marl.marl_training import run_episodes_marl  # noqa: E402
from qoe_oran_framework.mc_runner import build_policy, run_mc  # noqa: E402
from qoe_oran_framework.omega_logger import OmegaLogger  # noqa: E402

CONFIGS = {3: "qoe_oran_framework/configs/saclb_offline_dqn.yaml",
           7: "qoe_oran_framework/configs/saclb_offline_dqn_n7.yaml",
           19: "qoe_oran_framework/configs/saclb_offline_dqn_n19.yaml"}
EVAL_OFFSET = 5000
RULE_SELECT_EPISODES = 10
RULE_GRID = {
    "local": [dict(tau_c=c, tau_q=q, tau_e=e) for c, q, e in
              itertools.product((None, 0.0, 0.9, 0.95, 1.01), (None, 0.05, 0.1, 0.2), (None, 0.05, 0.1, 0.2, 0.4))
              if not (c is None and q is None)],
    "neighbour": [dict(tau_c=c, tau_q=q, tau_e=e, tau_n=n) for c, q, e, n in
                  itertools.product((None, 0.95, 1.01), (None, 0.1, 0.2), (None, 0.05, 0.1, 0.2), (0.85, 0.9, 0.95))],
}


class WideGatPolicy(GatCtdeMarlPolicy):
    """AXIOM with a wider encoder (hidden and output 32, Q-head hidden 64), for sensitivity."""

    def __init__(self, n, nd, cd_, ad, adj, **kw):
        super().__init__(n, nd, cd_, ad, adj, **kw)
        self.online = GatCtdeNetwork(n, nd, cd_, ad, gat_hidden_dim=32, gat_out_dim=32, q_hidden_dim=64).to(self.device)
        self.target = GatCtdeNetwork(n, nd, cd_, ad, gat_hidden_dim=32, gat_out_dim=32, q_hidden_dim=64).to(self.device)
        self.target.load_state_dict(self.online.state_dict())
        self.target.eval()
        self.optimizer = torch.optim.Adam(self.online.parameters(), lr=kw.get("learning_rate", 1e-4))


def clear(out_dir, arm, seed):
    m2._clear_seed_dir(out_dir, arm, seed)


def eval_marl(cfg, factory, policy, arm, seed, out_dir):
    eval_env = RANEnv(cfg, factory(EVAL_OFFSET + seed), seed=EVAL_OFFSET + seed, reward_mode="sla")
    d = f"{out_dir}/{arm}/seed{seed}/eval"
    Path(d).mkdir(parents=True, exist_ok=True)
    with OmegaLogger(f"{d}/omega_log.jsonl") as omega:
        run_episodes_marl(eval_env, policy, arm, omega, 50, EVAL_OFFSET + seed,
                          f"{arm}_seed{seed}_eval", "offline_eval", False, cfg)
    eval_env.close()
    return f"{d}/omega_log.jsonl"


def run_learned(arm, cfg, factory, adj, seed, train_eps, out_dir):
    n, nd, cd_ = len(cfg.gnb_ids), node_feature_dim(cfg), request_context_dim(cfg)
    clear(out_dir, arm, seed)
    train_dir = f"{out_dir}/{arm}/seed{seed}/train"
    Path(train_dir).mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if arm == "single_agent_dqn":
        run_mc(cfg, "dqn", factory, n_reps=1, episodes_per_rep=train_eps, base_seed=seed,
               mode="offline_train", training=True, results_dir=train_dir, reward_mode="sla")
        ckpt = f"{train_dir}/dqn/offline_train/rep_0/checkpoint.pt"
        train_s = time.time() - t0

        def pf(_s):
            p = build_policy("dqn", cfg)
            p.load_checkpoint(ckpt)
            return p
        run_mc(cfg, "dqn", factory, n_reps=1, episodes_per_rep=50, base_seed=EVAL_OFFSET + seed,
               mode="offline_eval", training=False, results_dir=f"{out_dir}/{arm}/seed{seed}/eval",
               policy_factory=pf, reward_mode="sla")
        return f"{out_dir}/{arm}/seed{seed}/eval/dqn/offline_eval/rep_0/omega_log.jsonl", train_s
    torch.manual_seed(seed)
    if arm == "mappo":
        policy = MappoPolicy(n, nd, cd_)
        env = RANEnv(cfg, factory(seed), seed=seed, reward_mode="sla")
        train_mappo(env, policy, cfg, train_eps, curve_path=f"{train_dir}/curve.json")
        env.close()
    else:
        if arm == "independent_dqn":
            policy = IndependentPerGnbDqnPolicy(n, nd, cd_, 2, learning_rate=1e-3)
        elif arm == "axiom_mlp":
            policy = m62.MlpCtdeMarlPolicy(n, nd, cd_, 2, adj, learning_rate=1e-4)
        elif arm == "axiom_wide":
            policy = WideGatPolicy(n, nd, cd_, 2, adj, learning_rate=1e-4)
        elif arm.startswith("axiom"):
            lr = {"axiom": 1e-4, "axiom_lr3e-5": 3e-5, "axiom_lr3e-4": 3e-4}[arm]
            policy = GatCtdeMarlPolicy(n, nd, cd_, 2, adj, learning_rate=lr)
        else:
            raise ValueError(arm)
        env = RANEnv(cfg, factory(seed), seed=seed, reward_mode="sla")
        with OmegaLogger(f"{train_dir}/omega_log.jsonl") as omega:
            run_episodes_marl(env, policy, arm, omega, train_eps, seed, f"{arm}_seed{seed}_train",
                              "offline_train", True, cfg)
        env.close()
    train_s = time.time() - t0
    policy.save_checkpoint(f"{train_dir}/checkpoint.pt")
    return eval_marl(cfg, factory, policy, arm, seed, out_dir), train_s


def rule_eval(cfg, factory, rule, nbrs, seed, episodes, results_dir, mode):
    run_mc(cfg, "lb_only", factory, n_reps=1, episodes_per_rep=episodes, base_seed=seed, mode=mode,
           training=False, results_dir=results_dir,
           policy_factory=lambda _s: ThresholdHeuristic(cfg.gnb_ids, nbrs, **rule), reward_mode="sla")
    return f"{results_dir}/lb_only/{mode}/rep_0/omega_log.jsonl"


def run_rules(arm, cfg, factory, nbrs, seeds, out_dir):
    if arm == "rule_static":
        rule = dict(tau_c=0.0)
    elif arm == "rule_accept_all":
        rule = dict()
    else:
        fam = arm.split("_", 1)[1]
        scores = []
        for r in RULE_GRID[fam]:
            vals = []
            for s in seeds:
                d = f"{out_dir}/{arm}_select/r{RULE_GRID[fam].index(r)}/seed{s}"
                Path(d).mkdir(parents=True, exist_ok=True)
                vals.append(per_seed_metrics(rule_eval(cfg, factory, r, nbrs, s, RULE_SELECT_EPISODES, d, "offline_select"))[0])
            scores.append((sum(vals) / len(vals), r))
        best = max(scores, key=lambda x: x[0])
        rule = best[1]
        json.dump({"selected": rule, "train_score": best[0],
                   "grid": [(sc, r) for sc, r in scores]}, open(f"{out_dir}/{arm}_selection.json", "w"), indent=1)
        print(f"[m64:{arm}] selected {rule} (train-stream reward {best[0]:.3f})", flush=True)
    out = {}
    for s in seeds:
        clear(out_dir, arm, s)
        p = rule_eval(cfg, factory, rule, nbrs, EVAL_OFFSET + s, 50, f"{out_dir}/{arm}/seed{s}/eval", "offline_eval")
        out[s] = per_seed_metrics(p)[0]
    return rule, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--topology", default="fully_connected")
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--train-episodes", type=int, default=300)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    m62.install_backlog_reset()                 # also calls Env B's on_episode_reset
    cfg = load_saclb_config(CONFIGS[a.n])
    sd = {k: v.sd for k, v in cfg.slice_by_id.items()}
    factory = cd.make_coupled_factory(cfg, sd, topology=a.topology)
    nbrs = cd.neighbour_lists(len(cfg.gnb_ids), a.topology)
    adj = m6.adjacency_for(a.topology, len(cfg.gnb_ids))
    print(f"[m64] arm={a.arm} N={a.n} topology={a.topology} alpha={cd.COUPLING_ALPHA} amp={cd.LOAD_AMPLITUDE} "
          f"base={cd.LOAD_BASE} seeds={a.seeds}", flush=True)
    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    if a.arm.startswith("rule_"):
        rule, out = run_rules(a.arm, cfg, factory, nbrs, a.seeds, a.out_dir)
        res = {"rule": rule, "reward": out}
    else:
        res = {}
        for s in a.seeds:
            path, train_s = run_learned(a.arm, cfg, factory, adj, s, a.train_episodes, a.out_dir)
            r, mb, tb = per_seed_metrics(path)
            res[s] = {"reward": r, "mmtc_blocks": mb, "blocks": tb, "train_seconds": round(train_s, 1)}
            print(f"[m64:{a.arm}] seed={s} reward={r:.3f} blocks={tb} mmtc={mb} train={train_s:.0f}s", flush=True)
    json.dump(res, open(f"{a.out_dir}/{a.arm}_{min(a.seeds)}-{max(a.seeds)}.json", "w"), indent=1)


if __name__ == "__main__":
    main()
