#!/usr/bin/env python3
"""M76 b1: the M72 load-shift test at nineteen gNBs in Env B, with per-gNB compliance.

The stored M75 AXIOM v2 checkpoints (m75/D_envB_n19_hex, trained under nominal Env B) and
the local rule tuned at seven gNBs (the rule carried over in M75 D), plus the static rule,
are evaluated without retraining or re-tuning on the usual evaluation streams under
shifted load, exactly as m72_shift.py does at three gNBs. Per-gNB SLA compliance is
recorded as in m75_run.py. Pre-registered in docs/PAPER5_M76_preregistration.md.

Usage (cwd = framework/): m76_shift.py --shift load_1.10 --seeds 900 901 --out DIR
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m75_run  # noqa: E402
import m72_shift as m72  # noqa: E402
import m64_run  # noqa: E402
import m62_reviewer_experiments as m62  # noqa: E402
from m64_axiom2 import AxiomV2Policy  # noqa: E402
from qoe_oran_framework.env import RANEnv  # noqa: E402
from qoe_oran_framework.marl.marl_env import node_feature_dim, request_context_dim  # noqa: E402
from qoe_oran_framework.marl.marl_training import run_episodes_marl  # noqa: E402
from qoe_oran_framework.omega_logger import OmegaLogger  # noqa: E402

RES = "/home/kmanojp/oranslice_rig/experiments/results"
CELL = "m75/D_envB_n19_hex"


def pergnb(path):
    m = json.load(open(path))["mean_compliance"]
    return 100 * 0.5 * (m["urllc"] + m["embb"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shift", required=True, choices=list(m72.SHIFTS))
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.environ["M75_PERGNB"] = "1"
    m75_run.install()
    m62.install_backlog_reset()
    cfg, factory, nbrs, adj = m72.setup(19, "hex", a.shift)
    n, nd, cdim = len(cfg.gnb_ids), node_feature_dim(cfg), request_context_dim(cfg)
    tuned = json.load(open(f"{RES}/m64/n7_hex/rule_local_selection.json"))["selected"]
    out = {}
    for s in a.seeds:
        seed = m64_run.EVAL_OFFSET + s
        d = f"{a.out}/{a.shift}/axiom2/seed{s}"
        Path(d).mkdir(parents=True, exist_ok=True)
        pol = AxiomV2Policy(n, nd, cdim, 2, adj)
        pol.load_checkpoint(f"{RES}/{CELL}/axiom2/seed{s}/train/checkpoint.pt")
        env = RANEnv(cfg, factory(seed), seed=seed, reward_mode="sla")
        m75_run.start()
        with OmegaLogger(f"{d}/omega_log.jsonl") as omega:
            run_episodes_marl(env, pol, "axiom2", omega, 50, seed, f"m76_{a.shift}_{s}", "offline_eval", False, cfg)
        env.close()
        m75_run.dump(f"{d}/per_gnb_sla.json")
        row = {"axiom2": dict(m72.summarise(f"{d}/omega_log.jsonl"), pergnb=pergnb(f"{d}/per_gnb_sla.json"))}
        for name, rule in (("rule_local_transfer", tuned), ("rule_static", dict(tau_c=0.0))):
            rd = f"{a.out}/{a.shift}/{name}/seed{s}"
            p = m64_run.rule_eval(cfg, factory, rule, nbrs, seed, 50, rd, "offline_eval")
            row[name] = dict(m72.summarise(p), pergnb=pergnb(f"{rd}/per_gnb_sla.json"))
        out[s] = row
        print(f"[m76 {a.shift}] seed {s} AXIOM {row['axiom2']['reward']:.3f} ({row['axiom2']['pergnb']:.1f}%) tuned "
              f"{row['rule_local_transfer']['reward']:.3f} ({row['rule_local_transfer']['pergnb']:.1f}%) static "
              f"{row['rule_static']['reward']:.3f}", flush=True)
    json.dump({"rule": tuned, "results": out}, open(f"{a.out}/{a.shift}_eval_{min(a.seeds)}-{max(a.seeds)}.json", "w"), indent=1)


if __name__ == "__main__":
    main()
