#!/usr/bin/env python3
"""M81: what AXIOM learned about shedding eMBB in Env B at seven gNBs (ring), 300 against 900 training episodes.

For every stored AXIOM checkpoint (M64 at 300 episodes, M79 at 900, seeds 900-911 and 1000-1002) the
held-out evaluation is replayed exactly as m64_run.py ran it. At every step, for every gNB, the probe records
that gNB's own URLLC queue (queue_len_norm) and congestion level, and whether AXIOM's eMBB head would
reject an eMBB request there (Q_reject > Q_accept). The replay must reproduce each seed's stored evaluation
reward; the summary records both so the verifier can check it. Nothing in the framework is modified.

Usage (cwd = framework/): m81_decision_probe.py --out ../experiments/results/m81
"""
import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/framework")

SEEDS = list(range(900, 912)) + [1000, 1001, 1002]
CKPT = {"300": "m64/n7_ring", "900": "m79/ep900_n7_ring"}
ROOT = "/home/kmanojp/oranslice_rig/experiments/results"


def probe(job):
    budget, seed, out_dir = job
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    import torch
    torch.set_num_threads(1)
    import coupled_dynamic_kpm_source as cd
    import m62_reviewer_experiments as m62
    import m6_run_experiment as m6
    import m64_run
    from m2_correctness_metrics import per_seed_metrics
    from m64_axiom2 import AxiomV2Policy
    from qoe_oran_framework.config import load_saclb_config
    from qoe_oran_framework.env import RANEnv
    from qoe_oran_framework.marl.marl_env import node_feature_dim, request_context_dim
    from qoe_oran_framework.marl.marl_training import run_episodes_marl
    from qoe_oran_framework.omega_logger import OmegaLogger

    m62.install_backlog_reset()
    cfg = load_saclb_config(m64_run.CONFIGS[7])
    sd = {k: v.sd for k, v in cfg.slice_by_id.items()}
    factory = cd.make_coupled_factory(cfg, sd, topology="ring")
    adj = m6.adjacency_for("ring", 7)
    n, nd, cdim = len(cfg.gnb_ids), node_feature_dim(cfg), request_context_dim(cfg)
    policy = AxiomV2Policy(n, nd, cdim, 2, adj)
    policy.load_checkpoint(f"{ROOT}/{CKPT[budget]}/axiom2/seed{seed}/train/checkpoint.pt")
    slices = [s.slice_id for s in cfg.slices]
    iu, ie = slices.index("urllc"), slices.index("embb")
    ctx = torch.zeros(n, cdim)
    ctx[:, ie] = 1.0
    rec = []
    orig = policy.select_actions

    def select_actions(node_features, requests, training=False):
        with torch.no_grad():
            nf = torch.tensor(node_features, dtype=torch.float32).unsqueeze(0)
            emb = policy.online.embed(nf, policy.adjacency).squeeze(0)
            q = policy.online.agent_q_values(emb, ctx)
        shed = (q[:, 0] > q[:, 1]).numpy()
        for i in range(n):
            rec.append((float(node_features[i, 3 * iu + 2]), float(node_features[i, 3 * iu + 1]), bool(shed[i])))
        return orig(node_features, requests, training=training)
    policy.select_actions = select_actions

    s_eval = m64_run.EVAL_OFFSET + seed
    env = RANEnv(cfg, factory(s_eval), seed=s_eval, reward_mode="sla")
    log = f"{out_dir}/logs/{budget}_seed{seed}.jsonl"
    Path(os.path.dirname(log)).mkdir(parents=True, exist_ok=True)
    with OmegaLogger(log) as omega:
        run_episodes_marl(env, policy, "axiom2", omega, 50, s_eval, f"axiom2_seed{seed}_eval", "offline_eval", False, cfg)
    env.close()
    reward = per_seed_metrics(log)[0]
    a = np.array(rec, dtype=np.float64)
    np.savez_compressed(f"{out_dir}/{budget}_seed{seed}.npz", urllc_queue=a[:, 0], congestion=a[:, 1], shed_embb=a[:, 2].astype(bool))
    os.remove(log)
    return budget, seed, reward, len(rec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    jobs = [(b, s, a.out) for b in CKPT for s in SEEDS]
    res = {}
    # one fresh process per job: the M62 environment patches must be installed exactly once per process
    with ProcessPoolExecutor(a.workers, max_tasks_per_child=1) as ex:
        for b, s, r, k in ex.map(probe, jobs):
            res.setdefault(b, {})[str(s)] = {"replayed_reward": r, "states": k}
            print(f"[m81] {b} episodes seed {s}: reward {r:.6f}, {k} gNB-steps", flush=True)
    json.dump(res, open(f"{a.out}/replay.json", "w"), indent=1)


if __name__ == "__main__":
    main()
