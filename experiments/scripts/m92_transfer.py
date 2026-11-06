#!/usr/bin/env python3
"""M92: zero-shot cluster-size transfer of stored checkpoints (no training).

A checkpoint trained at one cluster size is evaluated, unchanged, at another. The target cluster's
config, simulator, layout and adjacency are built exactly as m64_run.py (and m73_run.py at 37 gNBs)
builds them, and the evaluation is m64_run.eval_marl: 50 episodes on the held-out stream 5000 + seed.

Loading. AXIOM and its MLP variant execute through the shared encoder and the per-slice Q-heads,
whose shapes do not depend on the number of gNBs. The saved network also holds a QMIX mixer whose
input is the flattened joint state (N x 9), used only by the training loss. The loader therefore
copies every parameter except mixer.*, and refuses any other missing or unexpected key. MAPPO
executes through its actor alone (own node features plus the request's slice), so only the actor is
loaded; its critic sees the joint state and is used only in training. Nothing in framework/ or in
m64_run.py is modified. With M75_PERGNB=1, m75_run's recorder also writes per_gnb_sla.json next to each
evaluation log (the per-gNB SLA test the framework applies before it ORs over gNBs; logs are unchanged).

--validate evaluates at the checkpoint's own size and compares with that seed's stored evaluation,
which must match exactly (this checks the loader and the harness, and is not a result).

Usage (cwd = framework/):
  m92_transfer.py --env A --arm axiom2 --src ../experiments/results/m65_scaling/n7_hex --n 19 \
      --topology hex --seeds 900 901 --out-dir ../experiments/results/m92/A_hex_7to19
  m92_transfer.py --validate --env A --arm axiom2 --src ../experiments/results/m65_scaling/n7_hex --n 7 \
      --topology hex --seeds 900 --out-dir /tmp/m92_validate
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m73_run  # noqa: E402  (imports m64_run, which puts the framework on sys.path)
import m75_run  # noqa: E402
import m64_run  # noqa: E402
import torch  # noqa: E402

import coupled_dynamic_kpm_source as cd  # noqa: E402
import m6_run_experiment as m6  # noqa: E402
import m62_reviewer_experiments as m62  # noqa: E402
from m2_correctness_metrics import per_seed_metrics  # noqa: E402
from m64_axiom2 import AxiomV2Policy, MlpAxiomV2Policy  # noqa: E402
from m64_mappo import MappoPolicy  # noqa: E402
from m66_verify import read  # noqa: E402
from qoe_oran_framework.config import load_saclb_config  # noqa: E402
from qoe_oran_framework.marl.marl_env import node_feature_dim, request_context_dim  # noqa: E402

EXEC_PARAMS_AXIOM = 7782


def build_target(env, n, topology):
    m75_run.install()                          # m73_run.install (37-cell hex walk and config) plus, if M75_PERGNB=1,
                                               # the per-gNB SLA recorder around m64_run.eval_marl
    m62.install_backlog_reset()
    cfg = load_saclb_config(m64_run.CONFIGS[n])
    sd = {k: v.sd for k, v in cfg.slice_by_id.items()}
    if env == "A":
        from shared_budget_kpm_source import make_shared_budget_factory
        factory = make_shared_budget_factory(cfg, sd)
    else:
        factory = cd.make_coupled_factory(cfg, sd, topology=topology)
    adj = m6.adjacency_for(topology, len(cfg.gnb_ids))
    return cfg, factory, adj


def load_policy(arm, ckpt_path, cfg, adj):
    n, nd, cdim = len(cfg.gnb_ids), node_feature_dim(cfg), request_context_dim(cfg)
    ck = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    if arm == "mappo_tuned":
        p = MappoPolicy(n, nd, cdim)
        p.actor.load_state_dict(ck["actor"])     # strict: every actor parameter, nothing else
        return p, sum(v.numel() for v in p.actor.state_dict().values())
    p = {"axiom2": AxiomV2Policy, "axiom2_mlp": MlpAxiomV2Policy}[arm](n, nd, cdim, 2, adj)
    for which in ("online", "target"):
        sd = {k: v for k, v in ck[which].items() if not k.startswith("mixer.")}
        missing, unexpected = getattr(p, which).load_state_dict(sd, strict=False)
        bad = [k for k in missing if not k.startswith("mixer.")] + list(unexpected)
        if bad:
            raise SystemExit(f"checkpoint keys do not match outside the mixer: {bad}")
    p.epsilon = ck["epsilon"]
    p.train_step_count = ck["train_step_count"]
    exec_params = sum(v.numel() for k, v in p.online.state_dict().items() if not k.startswith("mixer."))
    if arm == "axiom2" and exec_params != EXEC_PARAMS_AXIOM:
        raise SystemExit(f"AXIOM execution parameters {exec_params} != {EXEC_PARAMS_AXIOM}")
    return p, exec_params


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", required=True, choices=["A", "B"])
    ap.add_argument("--arm", required=True, choices=["axiom2", "axiom2_mlp", "mappo_tuned"])
    ap.add_argument("--src", required=True, help="stored cell holding <arm>/seed<s>/train/checkpoint.pt")
    ap.add_argument("--n", type=int, required=True, help="target number of gNBs")
    ap.add_argument("--topology", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--validate", action="store_true")
    a = ap.parse_args()
    cfg, factory, adj = build_target(a.env, a.n, a.topology)
    tag = a.arm if a.validate else f"{a.arm}_transfer"
    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    res = {}
    for s in a.seeds:
        torch.manual_seed(s)
        policy, exec_params = load_policy(a.arm, f"{a.src}/{a.arm}/seed{s}/train/checkpoint.pt", cfg, adj)
        t0 = time.time()
        path = m64_run.eval_marl(cfg, factory, policy, tag, s, a.out_dir)
        r, mb, tb = per_seed_metrics(path)
        row = {"reward": r, "mmtc_blocks": mb, "blocks": tb, "exec_params": exec_params,
               "eval_seconds": round(time.time() - t0, 1), "source": a.src}
        if a.validate:
            stored = m64_run.Path(f"{a.src}/{a.arm}/seed{s}/eval/omega_log.jsonl")
            sp = str(stored) if stored.exists() else str(stored) + ".gz"
            x, y = read(path), read(sp)
            row["stored_reward"] = y["reward"]
            row["exact"] = (x["reward"] == y["reward"] and x["blocks"] == y["blocks"] and x["sla"] == y["sla"])
            pg_new, pg_old = Path(path).parent / "per_gnb_sla.json", Path(f"{a.src}/{a.arm}/seed{s}/eval/per_gnb_sla.json")
            if pg_new.exists() and pg_old.exists():
                row["per_gnb_exact"] = json.load(open(pg_new)) == json.load(open(pg_old))
        res[s] = row
        print(f"[m92:{tag}] env={a.env} N={a.n} {a.topology} seed={s} reward={r:.4f} blocks={tb} "
              f"params={exec_params} eval={row['eval_seconds']}s" + (f" exact={row['exact']} per_gnb_exact={row.get('per_gnb_exact')}" if a.validate else ""), flush=True)
    json.dump(res, open(f"{a.out_dir}/{tag}_{min(a.seeds)}-{max(a.seeds)}.json", "w"), indent=1)


if __name__ == "__main__":
    main()
