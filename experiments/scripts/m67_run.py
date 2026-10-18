#!/usr/bin/env python3
"""M67 development runner: m64_run.py plus validation-based checkpoint selection.

Training is unchanged and byte-identical to m64_run.py. Snapshots are written at
episode boundaries through the policy's own save_checkpoint, which consumes no
randomness. After training:
  1. the last checkpoint is evaluated exactly as m64_run.py does, into eval_last/;
  2. every snapshot is scored greedily on VAL_EPISODES episodes of the validation
     stream VAL_OFFSET + seed, disjoint from every training and evaluation stream;
  3. the best snapshot (ties go to the later one) is evaluated into eval/.
The same procedure applies to every value-based arm. The single-agent DQN's
initialisation is seeded, as in m66c_seeded_single.py. The framework is not modified.

Variants (env M67_VARIANT), see docs/PAPER5_M67_development_protocol.md:
  V1  snapshots every 25 episodes from 100 to 300, 10 validation episodes each
"""
import json
import os
import shutil
import sys
from pathlib import Path

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m64_run  # noqa: E402
from m2_correctness_metrics import per_seed_metrics  # noqa: E402
from qoe_oran_framework.env import RANEnv  # noqa: E402
from qoe_oran_framework.marl.ctde_policy import GatCtdeMarlPolicy  # noqa: E402
from qoe_oran_framework.marl.independent_dqn_ablation import IndependentPerGnbDqnPolicy  # noqa: E402
from qoe_oran_framework.marl.marl_training import run_episodes_marl  # noqa: E402
from qoe_oran_framework.mc_runner import build_policy, run_mc  # noqa: E402
from qoe_oran_framework.omega_logger import OmegaLogger  # noqa: E402
from qoe_oran_framework.policies.dqn_admission import DQNAdmissionPolicy  # noqa: E402

VAL_OFFSET = 20000
VARIANTS = {"V1": {"snap_eps": list(range(100, 301, 25)), "val_episodes": 10}}
VARIANT = os.environ.get("M67_VARIANT", "V1")
CFG = VARIANTS[VARIANT]

STATE = {"dir": None, "count": 0, "policy": None}


def _wrap_on_episode_end(cls):
    orig = cls.on_episode_end

    def hooked(self, *args, **kw):
        out = orig(self, *args, **kw)
        if STATE["dir"] is not None:
            STATE["count"] += 1
            STATE["policy"] = self
            if STATE["count"] in CFG["snap_eps"]:
                self.save_checkpoint(f"{STATE['dir']}/ep{STATE['count']}.pt")
        return out
    cls.on_episode_end = hooked


for _c in (GatCtdeMarlPolicy, IndependentPerGnbDqnPolicy, DQNAdmissionPolicy):
    _wrap_on_episode_end(_c)

_orig_run_learned = m64_run.run_learned


def _score(path):
    return per_seed_metrics(path)[0]


def run_learned_selected(arm, cfg, factory, adj, seed, train_eps, out_dir):
    if arm.startswith("mappo"):
        raise SystemExit("M67 covers value-based arms only")
    seed_dir = f"{out_dir}/{arm}/seed{seed}"
    snap = f"{seed_dir}/snapshots"
    if arm == "single_agent_dqn":
        torch.manual_seed(seed)
    STATE.update(dir=None, count=0, policy=None)
    # m64_run.run_learned clears the seed directory first, so snapshots are enabled from inside the
    # first hook call: create the directory lazily once training has started.
    Path(snap).mkdir(parents=True, exist_ok=True)

    real_clear = m64_run.clear

    def clear_then_enable(o, a, s):
        real_clear(o, a, s)
        Path(snap).mkdir(parents=True, exist_ok=True)
        STATE["dir"] = snap
    m64_run.clear = clear_then_enable
    try:
        eval_path, train_s = _orig_run_learned(arm, cfg, factory, adj, seed, train_eps, out_dir)
    finally:
        m64_run.clear = real_clear
        STATE["dir"] = None
    shutil.move(f"{seed_dir}/eval", f"{seed_dir}/eval_last")
    last_path = eval_path.replace(f"{seed_dir}/eval/", f"{seed_dir}/eval_last/")

    val_seed = VAL_OFFSET + seed
    scores = {}
    for ep in CFG["snap_eps"]:
        ck = f"{snap}/ep{ep}.pt"
        if not os.path.exists(ck):
            continue
        vdir = f"{seed_dir}/val/ep{ep}"
        if arm == "single_agent_dqn":
            def pf(_s, ck=ck):
                p = build_policy("dqn", cfg)
                p.load_checkpoint(ck)
                return p
            run_mc(cfg, "dqn", factory, n_reps=1, episodes_per_rep=CFG["val_episodes"], base_seed=val_seed,
                   mode="offline_eval", training=False, results_dir=vdir, policy_factory=pf, reward_mode="sla")
            scores[ep] = _score(f"{vdir}/dqn/offline_eval/rep_0/omega_log.jsonl")
        else:
            pol = STATE["policy"]
            pol.load_checkpoint(ck)
            env = RANEnv(cfg, factory(val_seed), seed=val_seed, reward_mode="sla")
            Path(vdir).mkdir(parents=True, exist_ok=True)
            with OmegaLogger(f"{vdir}/omega_log.jsonl") as omega:
                run_episodes_marl(env, pol, arm, omega, CFG["val_episodes"], val_seed,
                                  f"{arm}_seed{seed}_val_ep{ep}", "offline_eval", False, cfg)
            env.close()
            scores[ep] = _score(f"{vdir}/omega_log.jsonl")
    best = max(scores, key=lambda e: (round(scores[e], 9), e))
    ck = f"{snap}/ep{best}.pt"
    if arm == "single_agent_dqn":
        def pf(_s):
            p = build_policy("dqn", cfg)
            p.load_checkpoint(ck)
            return p
        run_mc(cfg, "dqn", factory, n_reps=1, episodes_per_rep=50, base_seed=m64_run.EVAL_OFFSET + seed,
               mode="offline_eval", training=False, results_dir=f"{seed_dir}/eval", policy_factory=pf, reward_mode="sla")
        sel_path = f"{seed_dir}/eval/dqn/offline_eval/rep_0/omega_log.jsonl"
    else:
        pol = STATE["policy"]
        pol.load_checkpoint(ck)
        sel_path = m64_run.eval_marl(cfg, factory, pol, arm, seed, out_dir)
    json.dump({"variant": VARIANT, "val_scores": scores, "selected_episode": best,
               "last_eval": _score(last_path), "selected_eval": _score(sel_path)},
              open(f"{seed_dir}/selection.json", "w"), indent=1)
    print(f"[m67:{arm}] seed={seed} selected ep{best} val={scores[best]:.3f} last_eval={_score(last_path):.3f} "
          f"selected_eval={_score(sel_path):.3f}", flush=True)
    return sel_path, train_s


if __name__ == "__main__":
    m64_run.run_learned = run_learned_selected
    m64_run.main()
