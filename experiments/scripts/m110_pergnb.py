#!/usr/bin/env python3
"""M110: per-gNB SLA compliance of the stored Env A policies (no training).

docs/PAPER5_M110_preregistration.md fixes the plan. Every stored checkpoint behind the paper's Env A scaling
figure is loaded and evaluated again on its own held-out stream (50 episodes, stream 5000 + seed), at its own
cluster size and layout, with m75_run's recorder on (M75_PERGNB=1). The recorder applies the per-gNB SLA test of
the framework's reward.check_violations before it is ORed over gNBs and changes nothing else. Each re-evaluation
must equal the stored evaluation exactly (reward, blocks and cluster-level SLA flags); a run that does not is
flagged, kept, and left out of the per-gNB estimate. When it is exact, the new evaluation log is a duplicate of the
stored one and is deleted, and per_gnb_sla.json and the row are kept.

Nothing in framework/ or in the earlier runners is modified.

Usage (cwd = framework/):
  M75_PERGNB=1 m110_pergnb.py --n 19 --topology hex --arm axiom2 --seeds 900 901
  m110_pergnb.py --jobs      prints the job list (one line per cell and policy, seeds in chunks)
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m66_verify as V  # noqa: E402
from m66_verify import S15, S30, S30_19, pooled_paths, read  # noqa: E402

OUT = "/home/kmanojp/oranslice_rig/experiments/results/m110"
ARMS = ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")
LAYOUTS = ("fully_connected", "ring", "hex")


def cells(n, arm):
    """(stored cell, topology, seeds) exactly as experiments/plots/paper5_fig_scaling_trend.py pools them."""
    if n == 37:
        if arm != "axiom2":
            return [("m73/A_n37_hex", "hex", S30_19)]
        return [("m73/A_n37_hex", "hex", S30_19), ("m73/A_n37_ring", "ring", S15),
                ("m73/A_n37_fully_connected", "fully_connected", S15)]
    if n == 3:
        return [("m65_n3_view", "fully_connected", S30)]
    return [(f"m65_scaling/n{n}_{t}", t, S15 if n == 7 else S30_19) for t in LAYOUTS]


def stored(n, topology, arm):
    for cell, t, ss in cells(n, arm):
        if t == topology:
            return {s: os.path.realpath(p) for s, p in pooled_paths(cell, arm, ss)}
    raise SystemExit(f"no stored cell for N={n} {topology} {arm}")


def ckpt_of(eval_path):
    run = eval_path.split("/eval/")[0]
    for q in (f"{run}/train/checkpoint.pt", f"{run}/train/dqn/offline_train/rep_0/checkpoint.pt"):
        if os.path.exists(q):
            return q
    raise SystemExit(f"no checkpoint beside {eval_path}")


def jobs():
    chunk = {3: 10, 7: 10, 19: 5, 37: 3}
    for n in (37, 19, 7, 3):                      # longest first
        for arm in ARMS:
            for cell, t, ss in cells(n, arm):
                seeds = sorted(stored(n, t, arm))
                for i in range(0, len(seeds), chunk[n]):
                    print(f"{n} {t} {arm} {' '.join(str(s) for s in seeds[i:i + chunk[n]])}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", action="store_true")
    ap.add_argument("--n", type=int)
    ap.add_argument("--topology")
    ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--seeds", type=int, nargs="+")
    ap.add_argument("--out-root", default=OUT)
    a = ap.parse_args()
    if a.jobs:
        return jobs()
    if os.environ.get("M75_PERGNB") != "1":
        raise SystemExit("set M75_PERGNB=1")
    import torch
    import m64_run
    import m92_transfer as m92
    from qoe_oran_framework.marl.marl_env import node_feature_dim, request_context_dim
    from qoe_oran_framework.mc_runner import build_policy

    cfg, factory, adj = m92.build_target("A", a.n, a.topology)     # installs m75_run (recorder) and the backlog reset
    src = stored(a.n, a.topology, a.arm)
    out_dir = f"{a.out_root}/A_n{a.n}_{a.topology}"
    n, nd, cdim = len(cfg.gnb_ids), node_feature_dim(cfg), request_context_dim(cfg)
    for s in a.seeds:
        row_path = f"{out_dir}/{a.arm}/seed{s}/row.json"
        if os.path.exists(row_path):
            continue
        ck = ckpt_of(src[s])
        m64_run.clear(out_dir, a.arm, s)
        torch.manual_seed(s)
        t0 = time.time()
        if a.arm == "single_agent_dqn":
            def pf(_s, ck=ck):
                p = build_policy("dqn", cfg)
                p.load_checkpoint(ck)
                return p
            ev = f"{out_dir}/{a.arm}/seed{s}/eval"
            m64_run.run_mc(cfg, "dqn", factory, n_reps=1, episodes_per_rep=50, base_seed=m64_run.EVAL_OFFSET + s,
                           mode="offline_eval", training=False, results_dir=ev, policy_factory=pf, reward_mode="sla")
            path = f"{ev}/dqn/offline_eval/rep_0/omega_log.jsonl"
        else:
            if a.arm == "independent_dqn":
                policy = m64_run.IndependentPerGnbDqnPolicy(n, nd, cdim, 2, learning_rate=1e-3)
                policy.load_checkpoint(ck)
            else:
                policy, _ = m92.load_policy(a.arm, ck, cfg, adj)
            path = m64_run.eval_marl(cfg, factory, policy, a.arm, s, out_dir)
        pg_path = f"{out_dir}/{a.arm}/seed{s}/eval/per_gnb_sla.json"
        pg = json.load(open(pg_path))
        x, y = read(path), read(src[s])
        exact = bool(x["reward"] == y["reward"] and x["blocks"] == y["blocks"] and x["sla"] == y["sla"])
        row = {"n": a.n, "topology": a.topology, "arm": a.arm, "seed": s, "stored_eval": src[s], "checkpoint": ck,
               "exact": exact, "reward": x["reward"], "stored_reward": y["reward"], "cluster_sla": x["sla"],
               "per_gnb_mean": pg["mean_compliance"], "steps": pg["steps"], "eval_seconds": round(time.time() - t0, 1)}
        if exact:
            os.remove(path)                      # a duplicate of the stored evaluation log
        Path(os.path.dirname(row_path)).mkdir(parents=True, exist_ok=True)
        json.dump(row, open(row_path + ".tmp", "w"), indent=1)
        os.replace(row_path + ".tmp", row_path)
        print(f"[m110] N={a.n} {a.topology} {a.arm} seed={s} exact={exact} reward={x['reward']:.4f} "
              f"per-gNB urllc={pg['mean_compliance']['urllc']:.4f} embb={pg['mean_compliance']['embb']:.4f} "
              f"t={row['eval_seconds']}s", flush=True)


if __name__ == "__main__":
    main()
