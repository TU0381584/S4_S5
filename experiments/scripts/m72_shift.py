#!/usr/bin/env python3
"""M72 B: AXIOM against rules under Env B conditions that shift after training and tuning.

Stored AXIOM v2 checkpoints and rules tuned on nominal conditions are evaluated,
without retraining or retuning, on the usual evaluation streams under shifted
load or coupling. Optionally the rule is also re-tuned on shifted training
streams, as a reference for what re-tuning recovers. Pre-registered in
docs/PAPER5_M72_preregistration.md. The framework and the simulator are not
modified; the simulator's module constants are set before each environment is built.

Usage:
  m72_shift.py eval   --n 3 --topology fully_connected --cell m64/n3_fully_connected --shift load_1.10 --seeds ... --out DIR
  m72_shift.py retune --n 3 --topology fully_connected --shift load_1.10 --select-seeds ... --seeds ... --out DIR
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m64_run  # noqa: E402  (first: puts the framework on sys.path)
import coupled_dynamic_kpm_source as cd  # noqa: E402
import m62_reviewer_experiments as m62  # noqa: E402
import m6_run_experiment as m6  # noqa: E402
from m64_axiom2 import AxiomV2Policy  # noqa: E402
from m66_verify import prio, read  # noqa: E402
from qoe_oran_framework.config import load_saclb_config  # noqa: E402
from qoe_oran_framework.env import RANEnv  # noqa: E402
from qoe_oran_framework.marl.marl_env import node_feature_dim, request_context_dim  # noqa: E402
from qoe_oran_framework.marl.marl_training import run_episodes_marl  # noqa: E402
from qoe_oran_framework.omega_logger import OmegaLogger  # noqa: E402

RESULTS = "/home/kmanojp/oranslice_rig/experiments/results"
NOMINAL = {"LOAD_BASE": cd.LOAD_BASE, "COUPLING_ALPHA": cd.COUPLING_ALPHA, "LOAD_AMPLITUDE": cd.LOAD_AMPLITUDE}
SHIFTS = {"nominal": {}, "load_0.80": {"LOAD_BASE": 0.80}, "load_1.05": {"LOAD_BASE": 1.05}, "load_1.10": {"LOAD_BASE": 1.10},
          "load_1.15": {"LOAD_BASE": 1.15}, "load_1.20": {"LOAD_BASE": 1.20}, "coupling_0.30": {"COUPLING_ALPHA": 0.30},
          "amplitude_0.50": {"LOAD_AMPLITUDE": 0.50}}


def setup(n, topology, shift):
    for k, v in NOMINAL.items():
        setattr(cd, k, v)
    for k, v in SHIFTS[shift].items():
        setattr(cd, k, v)
    cfg = load_saclb_config(m64_run.CONFIGS[n])
    sd = {k: v.sd for k, v in cfg.slice_by_id.items()}
    factory = cd.make_coupled_factory(cfg, sd, topology=topology)
    return cfg, factory, cd.neighbour_lists(n, topology), m6.adjacency_for(topology, n)


def summarise(path):
    r = read(path)
    return {"reward": r["reward"], "urllc": r["sla"]["urllc"], "embb": r["sla"]["embb"], "prio": prio(r), "blocks": r["blocks"]}


def tuned_rule(cell):
    sel = json.load(open(f"{RESULTS}/{cell}/rule_local_selection.json"))["selected"]
    return {k: v for k, v in sel.items()}


def do_eval(a):
    cfg, factory, nbrs, adj = setup(a.n, a.topology, a.shift)
    n, nd, cdim = len(cfg.gnb_ids), node_feature_dim(cfg), request_context_dim(cfg)
    rule = tuned_rule(a.cell)
    out = {}
    for s in a.seeds:
        seed = m64_run.EVAL_OFFSET + s
        pol = AxiomV2Policy(n, nd, cdim, 2, adj)
        pol.load_checkpoint(f"{RESULTS}/{a.cell}/axiom2/seed{s}/train/checkpoint.pt")
        d = f"{a.out}/{a.shift}/axiom2/seed{s}"
        Path(d).mkdir(parents=True, exist_ok=True)
        env = RANEnv(cfg, factory(seed), seed=seed, reward_mode="sla")
        with OmegaLogger(f"{d}/omega_log.jsonl") as omega:
            run_episodes_marl(env, pol, "axiom2", omega, 50, seed, f"m72_{a.shift}_{s}", "offline_eval", False, cfg)
        env.close()
        out[s] = {"axiom2": summarise(f"{d}/omega_log.jsonl"),
                  "rule_local": summarise(m64_run.rule_eval(cfg, factory, rule, nbrs, seed, 50, f"{a.out}/{a.shift}/rule_local/seed{s}", "offline_eval")),
                  "rule_static": summarise(m64_run.rule_eval(cfg, factory, dict(tau_c=0.0), nbrs, seed, 50, f"{a.out}/{a.shift}/rule_static/seed{s}", "offline_eval"))}
        print(f"[m72 {a.shift}] seed {s} AXIOM {out[s]['axiom2']['reward']:.3f} tuned {out[s]['rule_local']['reward']:.3f} "
              f"static {out[s]['rule_static']['reward']:.3f}", flush=True)
    json.dump({"rule": rule, "results": out}, open(f"{a.out}/{a.shift}_eval_{min(a.seeds)}-{max(a.seeds)}.json", "w"), indent=1)


def do_retune(a):
    cfg, factory, nbrs, _ = setup(a.n, a.topology, a.shift)
    scores = []
    for i, r in enumerate(m64_run.RULE_GRID["local"]):
        vals = [read(m64_run.rule_eval(cfg, factory, r, nbrs, s, m64_run.RULE_SELECT_EPISODES,
                                       f"{a.out}/{a.shift}/retune_select/r{i}/seed{s}", "offline_select"))["reward"] for s in a.select_seeds]
        scores.append((sum(vals) / len(vals), r))
    best = max(scores, key=lambda x: x[0])[1]
    out = {}
    for s in a.seeds:
        seed = m64_run.EVAL_OFFSET + s
        out[s] = summarise(m64_run.rule_eval(cfg, factory, best, nbrs, seed, 50, f"{a.out}/{a.shift}/rule_retuned/seed{s}", "offline_eval"))
    print(f"[m72 retune {a.shift}] selected {best}", flush=True)
    json.dump({"selected": best, "grid": [(sc, r) for sc, r in scores], "results": out},
              open(f"{a.out}/{a.shift}_retune.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["eval", "retune"])
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--topology", default="fully_connected")
    ap.add_argument("--cell", default="m64/n3_fully_connected")
    ap.add_argument("--shift", required=True, choices=list(SHIFTS))
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--select-seeds", type=int, nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    m62.install_backlog_reset()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (do_eval if a.mode == "eval" else do_retune)(a)
