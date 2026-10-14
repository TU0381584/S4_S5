#!/usr/bin/env python3
"""M62: reviewer-driven experiments for the WPC manuscript.

Answers three peer-review concerns with the SAME environment, seeds,
episode budget, and evaluation protocol as the M2 centralised campaign
(experiments/scripts/m2_run_experiment.py, reused unchanged where possible):

  heuristic             -- a static priority rule that encodes the reward's
                           own intended behaviour: accept URLLC and eMBB,
                           reject mMTC once the gNB's congestion level reaches
                           a threshold tau. No learning. tau is chosen on the
                           TRAINING-seed environments only, then evaluated on
                           the held-out eval seeds (5000 + seed), so the
                           reported number is not tuned on its own test data.
  independent_dqn_lr1e4 -- M2's independent-DQN ablation at AXIOM's learning
                           rate (1e-4) instead of its default 1e-3.
  single_agent_dqn_lr1e4-- M2's single-agent DQN at AXIOM's learning rate.
  axiom_mlp             -- AXIOM with its GAT encoder replaced by a per-node
                           MLP of the same width (with the same final
                           LayerNorm) that ignores the adjacency entirely, so
                           no information flows between gNBs. Everything else
                           (shared parameters, per-slice Q-heads, per-request
                           Huber TD, learning rate 1e-4, epsilon schedule) is
                           identical. Isolates the graph message passing.

Sensitivity conditions (--condition), applied by editing the loaded config
in memory only (the YAML on disk is never modified):
  base         -- unchanged (shared env: mean offered demand 1.05 x nominal shares)
  load102      -- shared env with offered demand 1.02 x nominal shares (lighter)
  load107      -- shared env with offered demand 1.07 x nominal shares (heavier)
  weights      -- priority weights perturbed but kept on their intended side
                  of the ~1.5 marginal congestion cost: embb 3.5 -> 2.5,
                  mmtc 0.3 -> 0.6 (urllc unchanged at 12.0)

Usage (cwd must be framework/, like m2_run_experiment.py):
    cd framework && ../venv/bin/python3 ../experiments/scripts/m62_reviewer_experiments.py \
        --arm axiom_mlp --seeds 900 901 --train-episodes 300 --eval-episodes 50 \
        --out-dir ../experiments/results/m62_reviewer/base
"""
import argparse
import json
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
import m2_run_experiment as m2  # noqa: E402
from m2_correctness_metrics import per_seed_metrics  # noqa: E402
from qoe_oran_framework.config import load_saclb_config  # noqa: E402
from qoe_oran_framework.env import RANEnv  # noqa: E402
from qoe_oran_framework.mc_runner import build_policy, run_mc  # noqa: E402
from qoe_oran_framework.omega_logger import OmegaLogger  # noqa: E402
from qoe_oran_framework.marl.ctde_policy import GatCtdeMarlPolicy  # noqa: E402
from qoe_oran_framework.marl.independent_dqn_ablation import IndependentPerGnbDqnPolicy  # noqa: E402
from qoe_oran_framework.marl.marl_env import node_feature_dim, request_context_dim  # noqa: E402
from qoe_oran_framework.marl.marl_training import run_episodes_marl  # noqa: E402
from qoe_oran_framework.marl.topology import build_adjacency  # noqa: E402
from shared_budget_kpm_source import make_shared_budget_factory  # noqa: E402

HEURISTIC_TAUS = [0.0, 0.5, 0.8, 0.9, 0.97]
TAU_SELECTION_EPISODES = 20


# ---------------------------------------------------------------- conditions
def apply_condition(cfg, condition: str) -> None:
    slices = cfg.slice_by_id
    if condition == "base":
        return
    if condition in ("load102", "load107"):
        import shared_budget_kpm_source as sb  # read at factory-call time
        sb.LOAD_FACTOR = 1.02 if condition == "load102" else 1.07
        return
    if condition == "weights":
        slices["embb"].priority_weight = 2.5
        slices["mmtc"].priority_weight = 0.6
        return
    raise ValueError(f"unknown condition {condition!r}")


# ---------------------------------------------------------------- heuristic
class PriorityHeuristic:
    """Accept URLLC and eMBB; reject mMTC iff the gNB's congestion level is at
    or above tau. Plugs into mc_runner's no-learning path via decide()."""

    def __init__(self, tau: float):
        self.tau = tau

    def decide(self, pending, cluster_state):
        actions = []
        for request in pending:
            if request.slice_id != "mmtc":
                actions.append(1)
                continue
            agg = cluster_state.per_gnb.get(request.gnb_id, {}).get(request.slice_id)
            congestion = agg.congestion_level if agg is not None else 0.0
            actions.append(0 if congestion >= self.tau else 1)
        return actions


def _heuristic_eval(cfg, kpm_factory, tau, seed, episodes, results_dir, mode):
    run_mc(cfg, "lb_only", kpm_factory, n_reps=1, episodes_per_rep=episodes, base_seed=seed,
           mode=mode, training=False, results_dir=results_dir,
           policy_factory=lambda _s: PriorityHeuristic(tau), reward_mode="sla")
    return f"{results_dir}/lb_only/{mode}/rep_0/omega_log.jsonl"


def run_heuristic(cfg, sd_for_slice, seeds, eval_episodes, out_dir):
    kpm_factory = m2.make_kpm_source_factory(cfg, sd_for_slice)
    # 1) choose tau on the TRAINING-seed environments only
    selection = {}
    for tau in HEURISTIC_TAUS:
        rewards = []
        for seed in seeds:
            d = f"{out_dir}/heuristic_tau_select/tau{tau}/seed{seed}"
            Path(d).mkdir(parents=True, exist_ok=True)
            path = _heuristic_eval(cfg, kpm_factory, tau, seed, TAU_SELECTION_EPISODES, d, "offline_select")
            rewards.append(per_seed_metrics(path)[0])
        selection[tau] = sum(rewards) / len(rewards)
        print(f"[m62:heuristic] tau={tau}: mean train-env reward/step={selection[tau]:.3f}")
    best_tau = max(selection, key=selection.get)
    print(f"[m62:heuristic] selected tau={best_tau} on training seeds")
    # 2) evaluate the selected rule on the held-out eval seeds
    results = {}
    for seed in seeds:
        d = f"{out_dir}/heuristic/seed{seed}/eval"
        Path(d).mkdir(parents=True, exist_ok=True)
        path = _heuristic_eval(cfg, kpm_factory, best_tau, m2.EVAL_SEED_OFFSET + seed, eval_episodes, d, "offline_eval")
        mrps, mmtc_b, total_b = per_seed_metrics(path)
        results[seed] = {"mean_reward_per_step": mrps, "mmtc_blocks": mmtc_b, "total_blocks": total_b,
                         "eval_omega": path}
    return {"selected_tau": best_tau, "tau_selection_train_reward": selection, "per_seed": results}


# ---------------------------------------------------------------- MLP ablation
class PerNodeMlpEncoder(nn.Module):
    """Same output width and final LayerNorm as AXIOM's GAT encoder, but each
    node is encoded from its own features only; the adjacency is ignored, so
    nothing passes between gNBs."""

    def __init__(self, in_dim: int, hidden_dim: int = 16, out_dim: int = 16):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(in_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.ELU(),
                                 nn.Linear(hidden_dim, out_dim), nn.LayerNorm(out_dim))

    def forward(self, node_features, adjacency):  # adjacency deliberately unused
        return self.net(node_features)


class MlpCtdeMarlPolicy(GatCtdeMarlPolicy):
    def __init__(self, n_agents, node_feat_dim, context_dim, action_dim, adjacency, **kw):
        super().__init__(n_agents, node_feat_dim, context_dim, action_dim, adjacency, **kw)
        self.online.encoder = PerNodeMlpEncoder(node_feat_dim).to(self.device)
        self.target.encoder = PerNodeMlpEncoder(node_feat_dim).to(self.device)
        self.target.load_state_dict(self.online.state_dict())
        lr = kw.get("learning_rate", 1e-4)
        self.optimizer = torch.optim.Adam(self.online.parameters(), lr=lr)


# ---------------------------------------------------------------- learned arms
def _train_eval_marl(cfg, kpm_factory, policy, tag, seed, train_episodes, eval_episodes, out_dir):
    m2._clear_seed_dir(out_dir, tag, seed)
    env = RANEnv(cfg, kpm_factory(seed), seed=seed, reward_mode="sla")
    train_dir = f"{out_dir}/{tag}/seed{seed}/train"
    Path(train_dir).mkdir(parents=True, exist_ok=True)
    with OmegaLogger(f"{train_dir}/omega_log.jsonl") as omega:
        run_episodes_marl(env, policy, tag, omega, train_episodes, seed,
                          f"{tag}_seed{seed}_train", "offline_train", True, cfg)
    env.close()
    policy.save_checkpoint(f"{train_dir}/checkpoint.pt")
    eval_seed = m2.EVAL_SEED_OFFSET + seed
    eval_env = RANEnv(cfg, kpm_factory(eval_seed), seed=eval_seed, reward_mode="sla")
    eval_dir = f"{out_dir}/{tag}/seed{seed}/eval"
    Path(eval_dir).mkdir(parents=True, exist_ok=True)
    with OmegaLogger(f"{eval_dir}/omega_log.jsonl") as omega:
        run_episodes_marl(eval_env, policy, tag, omega, eval_episodes, eval_seed,
                          f"{tag}_seed{seed}_eval", "offline_eval", False, cfg)
    eval_env.close()
    return f"{eval_dir}/omega_log.jsonl"


def run_learned(arm, cfg, sd_for_slice, seeds, train_episodes, eval_episodes, out_dir):
    n_agents = len(cfg.gnb_ids)
    node_dim, ctx_dim = node_feature_dim(cfg), request_context_dim(cfg)
    adj = build_adjacency(n_agents)
    kpm_factory = m2.make_kpm_source_factory(cfg, sd_for_slice)
    results = {}
    for seed in seeds:
        t0 = time.time()
        if arm == "single_agent_dqn_lr1e4" or arm == "single_agent_dqn":
            m2._clear_seed_dir(out_dir, arm, seed)
            lr = 1e-4 if arm.endswith("lr1e4") else 1e-3
            train_dir = f"{out_dir}/{arm}/seed{seed}/train"
            run_mc(cfg, "dqn", kpm_factory, n_reps=1, episodes_per_rep=train_episodes, base_seed=seed,
                   mode="offline_train", training=True, results_dir=train_dir, reward_mode="sla",
                   policy_factory=lambda _s, lr=lr: build_policy("dqn", cfg, learning_rate=lr))
            ckpt = f"{train_dir}/dqn/offline_train/rep_0/checkpoint.pt"

            def eval_factory(_s, ckpt=ckpt, lr=lr):
                p = build_policy("dqn", cfg, learning_rate=lr)
                p.load_checkpoint(ckpt)
                return p
            eval_dir = f"{out_dir}/{arm}/seed{seed}/eval"
            run_mc(cfg, "dqn", kpm_factory, n_reps=1, episodes_per_rep=eval_episodes,
                   base_seed=m2.EVAL_SEED_OFFSET + seed, mode="offline_eval", training=False,
                   results_dir=eval_dir, policy_factory=eval_factory, reward_mode="sla")
            path = f"{eval_dir}/dqn/offline_eval/rep_0/omega_log.jsonl"
        else:
            torch.manual_seed(seed)  # before construction, as in m2_run_experiment.py
            if arm in ("independent_dqn_lr1e4", "independent_dqn"):
                lr = 1e-4 if arm.endswith("lr1e4") else 1e-3
                policy = IndependentPerGnbDqnPolicy(n_agents, node_dim, ctx_dim, m2.ACTION_DIM, learning_rate=lr)
            elif arm == "axiom_mlp":
                policy = MlpCtdeMarlPolicy(n_agents, node_dim, ctx_dim, m2.ACTION_DIM, adj, learning_rate=1e-4)
            elif arm == "axiom":
                policy = GatCtdeMarlPolicy(n_agents, node_dim, ctx_dim, m2.ACTION_DIM, adj)
            else:
                raise ValueError(arm)
            path = _train_eval_marl(cfg, kpm_factory, policy, arm, seed, train_episodes, eval_episodes, out_dir)
        mrps, mmtc_b, total_b = per_seed_metrics(path)
        results[seed] = {"mean_reward_per_step": mrps, "mmtc_blocks": mmtc_b, "total_blocks": total_b,
                         "eval_omega": path, "elapsed_s": round(time.time() - t0, 1)}
        print(f"[m62:{arm}] seed={seed}: reward/step={mrps:.3f} blocks={total_b} mmtc_blocks={mmtc_b} "
              f"({time.time()-t0:.0f}s)", flush=True)
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", required=True,
                    choices=["heuristic", "independent_dqn_lr1e4", "single_agent_dqn_lr1e4", "axiom_mlp",
                             "axiom", "independent_dqn", "single_agent_dqn"])
    ap.add_argument("--condition", default="base", choices=["base", "load102", "load107", "weights"])
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--train-episodes", type=int, default=300)
    ap.add_argument("--eval-episodes", type=int, default=50)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--env", default="shared", choices=["original", "shared"],
                    help="shared = shared-budget simulator fix (shared_budget_kpm_source.py)")
    args = ap.parse_args()
    if args.env == "shared":
        # every runner in this script and in m2_run_experiment looks the factory up on m2 at call time
        m2.make_kpm_source_factory = make_shared_budget_factory

    cfg = load_saclb_config(m2.CONFIG_PATH)
    apply_condition(cfg, args.condition)
    sd_for_slice = {sid: spec.sd for sid, spec in cfg.slice_by_id.items()}
    caps = {sid: s.max_ratio_cap for sid, s in cfg.slice_by_id.items()}
    weights = {sid: s.priority_weight for sid, s in cfg.slice_by_id.items()}
    print(f"[m62] env={args.env} arm={args.arm} condition={args.condition} caps={caps} weights={weights}", flush=True)

    if args.arm == "heuristic":
        out = run_heuristic(cfg, sd_for_slice, args.seeds, args.eval_episodes, args.out_dir)
    else:
        out = run_learned(args.arm, cfg, sd_for_slice, args.seeds, args.train_episodes,
                          args.eval_episodes, args.out_dir)
    out_path = Path(args.out_dir) / f"{args.arm}_{min(args.seeds)}-{max(args.seeds)}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    json.dump({"arm": args.arm, "env": args.env, "condition": args.condition, "caps": caps, "weights": weights,
               "results": out}, open(out_path, "w"), indent=2)
    print(f"[m62] wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
