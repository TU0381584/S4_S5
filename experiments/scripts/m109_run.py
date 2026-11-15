#!/usr/bin/env python3
"""M109 runner (docs/PAPER5_M109_preregistration.md). m64_run.py (m73_run at 37 gNBs) with one variant swapped in.
The framework, m64_run.py and every earlier runner are not edited: classes are swapped at run time, as M70 and M100 do.

  --variant none         the paper's own arms, unchanged (AXIOM reference, MLP encoder as --arm axiom2_mlp, MAPPO)
  --variant parity       --arm single_agent_dqn or independent_dqn with Huber loss and LayerNorm (m109_arms.py)
  --variant paramshared  --arm axiom2 runs ParamSharedQ, one shared MLP Q-network on own-row features
  --variant sharedhead   --arm axiom2 runs M70's SharedHeadAxiom
  --variant qmix         --arm axiom2 runs QmixShared
  --budget 300,900       value-based arms: also evaluate the snapshots saved after 300 and 900 episodes into eval300/
                         and eval900/ (use with --train-episodes 1500; MAPPO has no snapshot hook and is run separately)
DQN-SA's network initialisation is seeded in every M109 run, as m73_run.py does at 37 gNBs.
Usage (cwd framework/): m109_run.py --variant V [--budget 300,900] <m64_run.py arguments>
"""
import json
import os
import sys
from pathlib import Path

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m64_run  # noqa: E402
import m109_arms as A  # noqa: E402


def pop(flag, default=None):
    if flag in sys.argv:
        i = sys.argv.index(flag); v = sys.argv[i + 1]; del sys.argv[i:i + 2]
        return v
    return default


def install_variant(v):
    if v == "parity":
        import qoe_oran_framework.mc_runner as mc
        from qoe_oran_framework.mc_runner import request_state_dim
        orig = mc.build_policy

        def build_policy(algorithm, cfg, **overrides):
            if algorithm == "dqn":
                return A.make_parity_single(request_state_dim(cfg), **overrides)
            return orig(algorithm, cfg, **overrides)
        mc.build_policy = build_policy            # used by run_mc when training
        m64_run.build_policy = build_policy       # used by m64_run when evaluating
        m64_run.IndependentPerGnbDqnPolicy = A.ParityIndependentDqn
    elif v == "paramshared":
        m64_run.AxiomV2Policy = A.ParamSharedQ
    elif v == "sharedhead":
        import m70_run
        m64_run.AxiomV2Policy = m70_run.SharedHeadAxiom
    elif v == "qmix":
        m64_run.AxiomV2Policy = A.QmixShared
    elif v != "none":
        raise SystemExit(f"unknown variant {v!r}")


def install_seed_and_budget(budget):
    orig = m64_run.run_learned
    if budget:
        import m67_run                              # hooks snapshot saving into the value-based policy classes
        m67_run.CFG["snap_eps"] = list(budget)

    def run_learned(arm, cfg, factory, adj, seed, train_eps, out_dir):
        if arm == "single_agent_dqn":
            torch.manual_seed(seed)
        if not budget or arm.startswith("mappo"):
            return orig(arm, cfg, factory, adj, seed, train_eps, out_dir)
        seed_dir = f"{out_dir}/{arm}/seed{seed}"; snap = f"{seed_dir}/snapshots"
        m67_run.STATE.update(dir=None, count=0, policy=None)
        real_clear = m64_run.clear

        def clear_then_enable(o, a, s):
            real_clear(o, a, s)
            Path(snap).mkdir(parents=True, exist_ok=True)
            m67_run.STATE["dir"] = snap
        m64_run.clear = clear_then_enable
        try:
            eval_path, train_s = orig(arm, cfg, factory, adj, seed, train_eps, out_dir)
        finally:
            m64_run.clear = real_clear
            m67_run.STATE["dir"] = None
        for bud in budget:
            _eval_snapshot(arm, cfg, factory, seed, seed_dir, snap, bud)
        return eval_path, train_s

    def _eval_snapshot(arm, cfg, factory, seed, seed_dir, snap, budget):
        ck = f"{snap}/ep{budget}.pt"
        assert os.path.exists(ck), ck
        d = f"{seed_dir}/eval{budget}"
        if arm == "single_agent_dqn":
            def pf(_s):
                p = m64_run.build_policy("dqn", cfg)
                p.load_checkpoint(ck)
                return p
            m64_run.run_mc(cfg, "dqn", factory, n_reps=1, episodes_per_rep=50, base_seed=m64_run.EVAL_OFFSET + seed,
                           mode="offline_eval", training=False, results_dir=d, policy_factory=pf, reward_mode="sla")
            p900 = f"{d}/dqn/offline_eval/rep_0/omega_log.jsonl"
        else:
            pol = m67_run.STATE["policy"]
            pol.load_checkpoint(ck)
            env = m64_run.RANEnv(cfg, factory(m64_run.EVAL_OFFSET + seed), seed=m64_run.EVAL_OFFSET + seed, reward_mode="sla")
            Path(d).mkdir(parents=True, exist_ok=True)
            with m64_run.OmegaLogger(f"{d}/omega_log.jsonl") as omega:
                m64_run.run_episodes_marl(env, pol, arm, omega, 50, m64_run.EVAL_OFFSET + seed,
                                          f"{arm}_seed{seed}_eval{budget}", "offline_eval", False, cfg)
            env.close()
            p900 = f"{d}/omega_log.jsonl"
        r = m64_run.per_seed_metrics(p900)
        json.dump({"seed": seed, "episodes": budget, "reward": r[0], "mmtc_blocks": r[1], "blocks": r[2]},
                  open(f"{seed_dir}/eval{budget}.json", "w"))
        print(f"[m109:{arm}] seed={seed} eval at {budget} episodes reward={r[0]:.3f}", flush=True)
    m64_run.run_learned = run_learned


if __name__ == "__main__":
    variant = pop("--variant", "none")
    budget = [int(x) for x in pop("--budget", "").split(",") if x]
    if "--n" in sys.argv and sys.argv[sys.argv.index("--n") + 1] == "37":
        import m73_run
        m73_run.install()
    install_variant(variant)
    install_seed_and_budget(budget)
    print(f"[m109] variant={variant} budget={budget or 'none'}", flush=True)
    m64_run.main()
