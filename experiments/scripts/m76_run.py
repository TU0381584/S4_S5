#!/usr/bin/env python3
"""M76 runner: m75_run.py plus the fifth review's variants (docs/PAPER5_M76_preregistration.md).

Neither the framework nor m64_run.py is modified. Selected by environment variables:

  M76_REWARD=pergnb     the SLA violation penalty is charged once per violating gNB
                        (sum over gNBs and slices of lambda_k * 1[v_k at gNB g]) instead of
                        once per slice for the whole cluster. Every other reward term is
                        unchanged. Training and evaluation both use it, for every arm.
  M76_HETERO=lo,hi      Env B: each gNB's load multiplier is drawn from U[lo, hi] per seed
                        (all gNBs; the original draws U[0.9, 1.0] and fixes gNB 0 at 1.0).
  M76_LOAD=<float>      Env A: mean offered demand = <float> x each slice's nominal share
                        (the original is 1.05).
  arm vdn               value-decomposition network (Sunehag et al., AAMAS 2018) over the
                        independent DQN's per-gNB networks: identical networks, optimiser,
                        exploration and target schedule, but trained on one joint target per
                        step, sum_i Q_i(s_i, a_i) regressed on r + gamma * sum_i max Q_i^-(s'_i).

M75_PERGNB=1 (per-gNB SLA recording during evaluation) works as in m75_run.py.

Usage (cwd = framework/): same arguments as m64_run.py.
"""
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m75_run  # noqa: E402  (also registers N=37 and seeds the single-agent DQN)
import m64_run  # noqa: E402
import coupled_dynamic_kpm_source as cd  # noqa: E402
import shared_budget_kpm_source as sb  # noqa: E402
from qoe_oran_framework import env as fenv  # noqa: E402
from qoe_oran_framework.env import RANEnv  # noqa: E402
from qoe_oran_framework.marl.independent_dqn_ablation import IndependentPerGnbDqnPolicy  # noqa: E402
from qoe_oran_framework.marl.marl_env import node_feature_dim, request_context_dim  # noqa: E402
from qoe_oran_framework.marl.marl_training import run_episodes_marl  # noqa: E402
from qoe_oran_framework.omega_logger import OmegaLogger  # noqa: E402


class VdnPolicy(IndependentPerGnbDqnPolicy):
    def train_step(self, batch):
        B = len(batch["rewards"])
        per = {i: {"b": [], "s": [], "s2": [], "a": []} for i in range(self.n_agents)}
        for b in range(B):
            nf, nnf = batch["node_features"][b], batch["next_node_features"][b]
            for k, ai in enumerate(batch["agent_request_agent_idx"][b]):
                ctx = batch["agent_request_context"][b][k]
                per[ai]["b"].append(b)
                per[ai]["s"].append(np.concatenate([nf[ai], ctx]).astype(np.float32))
                per[ai]["s2"].append(np.concatenate([nnf[ai], ctx]).astype(np.float32))
                per[ai]["a"].append(int(batch["agent_request_action"][b][k]))
        q_tot = torch.zeros(B)
        nxt = torch.zeros(B)
        used = []
        for ai, d in per.items():
            if not d["b"]:
                continue
            ag = self.agents[ai]
            idx = torch.as_tensor(d["b"], dtype=torch.long)
            s = torch.as_tensor(np.stack(d["s"]))
            s2 = torch.as_tensor(np.stack(d["s2"]))
            a = torch.as_tensor(d["a"], dtype=torch.long)
            q = ag.q_network(s)[:, 0, :].gather(1, a.unsqueeze(1)).squeeze(1)
            q_tot = q_tot.index_add(0, idx, q)
            with torch.no_grad():
                nxt = nxt.index_add(0, idx, ag.target_network(s2)[:, 0, :].max(dim=1)[0])
            used.append(ag)
        if not used:
            return {}
        r = torch.as_tensor(np.asarray(batch["rewards"], dtype=np.float32))
        done = torch.as_tensor(np.asarray(batch["dones"], dtype=np.float32))
        y = r + used[0].gamma * (1.0 - done) * nxt
        loss = nn.functional.mse_loss(q_tot, y)
        for ag in used:
            ag.optimizer.zero_grad()
        loss.backward()
        for ag in used:
            nn.utils.clip_grad_norm_(ag.q_network.parameters(), max_norm=1.0)
            ag.optimizer.step()
            ag.train_step_count += 1
            if ag.train_step_count % 100 == 0:          # as DQNPolicy.train_step does
                ag.target_network.load_state_dict(ag.q_network.state_dict())
        return {"loss": float(loss.item())}


def run_vdn(cfg, factory, adj, seed, train_eps, out_dir):
    n, nd, cd_ = len(cfg.gnb_ids), node_feature_dim(cfg), request_context_dim(cfg)
    m64_run.clear(out_dir, "vdn", seed)
    train_dir = f"{out_dir}/vdn/seed{seed}/train"
    Path(train_dir).mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    torch.manual_seed(seed)
    policy = VdnPolicy(n, nd, cd_, 2, learning_rate=1e-3)
    env = RANEnv(cfg, factory(seed), seed=seed, reward_mode="sla")
    with OmegaLogger(f"{train_dir}/omega_log.jsonl") as omega:
        run_episodes_marl(env, policy, "vdn", omega, train_eps, seed, f"vdn_seed{seed}_train", "offline_train", True, cfg)
    env.close()
    train_s = time.time() - t0
    policy.save_checkpoint(f"{train_dir}/checkpoint.pt")
    return m64_run.eval_marl(cfg, factory, policy, "vdn", seed, out_dir), train_s


def install():
    m75_run.install()
    rw_mode, het, load = os.environ.get("M76_REWARD"), os.environ.get("M76_HETERO"), os.environ.get("M76_LOAD")
    if rw_mode == "pergnb":
        orig = fenv.compute_step_reward

        def compute_step_reward(cluster_state, slice_specs, accepted_counts, weights, include_lb_term):
            reward, info = orig(cluster_state, slice_specs, accepted_counts, weights, include_lb_term)
            term = 0.0
            for slice_states in cluster_state.per_gnb.values():
                for sl, agg in slice_states.items():
                    if sl in slice_specs and (agg.queue_len_norm > 1.0 or agg.loss_proxy > slice_specs[sl].loss_budget_pct):
                        term += slice_specs[sl].violation_penalty
            reward = reward + info["violation_term"] - term
            info = dict(info, violation_term=term, cluster_violation_term=info["violation_term"])
            return reward, info
        fenv.compute_step_reward = compute_step_reward
        print("[m76] per-gNB SLA violation penalty", flush=True)
    if het:
        lo, hi = (float(x) for x in het.split(","))

        def mult(gnb_ids, seed):
            rng = np.random.RandomState(seed + 7919)
            return {g: float(rng.uniform(lo, hi)) for g in gnb_ids}
        cd.shared_budget_load_multiplier = mult
        print(f"[m76] heterogeneous per-gNB load multipliers U[{lo}, {hi}]", flush=True)
    if load:
        sb.LOAD_FACTOR = float(load)
        print(f"[m76] Env A load factor {sb.LOAD_FACTOR}", flush=True)
    orig_learned = m64_run.run_learned

    def run_learned(arm, cfg, factory, adj, seed, train_eps, out_dir):
        if arm == "vdn":
            return run_vdn(cfg, factory, adj, seed, train_eps, out_dir)
        return orig_learned(arm, cfg, factory, adj, seed, train_eps, out_dir)
    m64_run.run_learned = run_learned


if __name__ == "__main__":
    install()
    m64_run.main()
