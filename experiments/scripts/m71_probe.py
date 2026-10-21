#!/usr/bin/env python3
"""M71 exploratory probes for the third review's Tier 3 questions (not confirmatory).

hindsight  M7: how much headroom does Env B leave above the tuned rule? Every rule
           of the local family is evaluated directly on each seed's evaluation
           stream, and the best one per seed is taken in hindsight. This is an
           upper reference for the rule family, not a true optimum.
shift      M1: does AXIOM degrade more gracefully than the tuned rule when Env B's
           conditions change after training and tuning? Stored AXIOM v2 checkpoints
           and the rules tuned on nominal conditions are evaluated, without
           retraining or retuning, under shifted load and coupling.

Probe outputs are exploratory: any later confirmatory test must use other seeds.

Usage:
  m71_probe.py hindsight --seeds 2000 2001 --out <dir>
  m71_probe.py shift --seeds 900 901 --out <dir>
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
from m64_heuristics import ThresholdHeuristic  # noqa: E402,F401
from m66_verify import prio, read  # noqa: E402
from qoe_oran_framework.config import load_saclb_config  # noqa: E402
from qoe_oran_framework.env import RANEnv  # noqa: E402
from qoe_oran_framework.marl.marl_env import node_feature_dim, request_context_dim  # noqa: E402
from qoe_oran_framework.marl.marl_training import run_episodes_marl  # noqa: E402
from qoe_oran_framework.omega_logger import OmegaLogger  # noqa: E402

SHIFTS = {"nominal": {}, "load_0.80": {"LOAD_BASE": 0.80}, "load_1.10": {"LOAD_BASE": 1.10},
          "coupling_0.30": {"COUPLING_ALPHA": 0.30}, "amplitude_0.50": {"LOAD_AMPLITUDE": 0.50}}
NOMINAL = {"LOAD_BASE": cd.LOAD_BASE, "COUPLING_ALPHA": cd.COUPLING_ALPHA, "LOAD_AMPLITUDE": cd.LOAD_AMPLITUDE}
TUNED_LOCAL = dict(tau_c=0.0, tau_q=None, tau_e=0.2)       # selected on training streams (m64 rule_local_selection.json)


def setup(shift):
    for k, v in NOMINAL.items():
        setattr(cd, k, v)
    for k, v in SHIFTS[shift].items():
        setattr(cd, k, v)
    cfg = load_saclb_config(m64_run.CONFIGS[3])
    sd = {k: v.sd for k, v in cfg.slice_by_id.items()}
    factory = cd.make_coupled_factory(cfg, sd, topology="fully_connected")
    return cfg, factory, cd.neighbour_lists(3, "fully_connected"), m6.adjacency_for("fully_connected", 3)


def summarise(path):
    r = read(path)
    return {"reward": r["reward"], "urllc": r["sla"]["urllc"], "embb": r["sla"]["embb"], "prio": prio(r), "blocks": r["blocks"]}


def rule_run(cfg, factory, nbrs, rule, seed, d):
    return summarise(m64_run.rule_eval(cfg, factory, rule, nbrs, m64_run.EVAL_OFFSET + seed, 50, d, "offline_eval"))


def hindsight(a):
    out = {}
    for s in a.seeds:
        cfg, factory, nbrs, _ = setup("nominal")
        res = []
        for i, rule in enumerate(m64_run.RULE_GRID["local"]):
            r = rule_run(cfg, factory, nbrs, rule, s, f"{a.out}/hindsight/seed{s}/r{i}")
            res.append({"rule": rule, **r})
        tuned = rule_run(cfg, factory, nbrs, TUNED_LOCAL, s, f"{a.out}/hindsight/seed{s}/tuned")
        best = max(res, key=lambda x: x["reward"])
        out[s] = {"tuned": tuned, "best_in_hindsight": best, "max_embb_any_rule": max(x["embb"] for x in res),
                  "n_rules": len(res)}
        print(f"[hindsight] seed {s} tuned {tuned['reward']:.3f} (eMBB {tuned['embb']:.3f}) | best {best['reward']:.3f} "
              f"{best['rule']} (eMBB {best['embb']:.3f}) | max eMBB over grid {out[s]['max_embb_any_rule']:.3f}", flush=True)
    json.dump(out, open(f"{a.out}/hindsight_{min(a.seeds)}-{max(a.seeds)}.json", "w"), indent=1, default=str)


def shift(a):
    out = {}
    for sh in SHIFTS:
        cfg, factory, nbrs, adj = setup(sh)
        n, nd, cdim = len(cfg.gnb_ids), node_feature_dim(cfg), request_context_dim(cfg)
        out[sh] = {}
        for s in a.seeds:
            pol = AxiomV2Policy(n, nd, cdim, 2, adj)
            pol.load_checkpoint(f"{m64_run.__file__.rsplit('/scripts', 1)[0]}/results/m64/n3_fully_connected/axiom2/seed{s}/train/checkpoint.pt")
            seed = m64_run.EVAL_OFFSET + s
            d = f"{a.out}/shift/{sh}/axiom2/seed{s}"
            Path(d).mkdir(parents=True, exist_ok=True)
            env = RANEnv(cfg, factory(seed), seed=seed, reward_mode="sla")
            with OmegaLogger(f"{d}/omega_log.jsonl") as omega:
                run_episodes_marl(env, pol, "axiom2", omega, 50, seed, f"probe_{sh}_{s}", "offline_eval", False, cfg)
            env.close()
            out[sh][s] = {"axiom2": summarise(f"{d}/omega_log.jsonl"),
                          "rule_local": rule_run(cfg, factory, nbrs, TUNED_LOCAL, s, f"{a.out}/shift/{sh}/rule_local/seed{s}"),
                          "rule_static": rule_run(cfg, factory, nbrs, dict(tau_c=0.0), s, f"{a.out}/shift/{sh}/rule_static/seed{s}")}
            o = out[sh][s]
            print(f"[shift {sh}] seed {s} AXIOM {o['axiom2']['reward']:.3f} | tuned rule {o['rule_local']['reward']:.3f} | "
                  f"static {o['rule_static']['reward']:.3f}", flush=True)
    json.dump(out, open(f"{a.out}/shift_{min(a.seeds)}-{max(a.seeds)}.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["hindsight", "shift"])
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    m62.install_backlog_reset()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    {"hindsight": hindsight, "shift": shift}[a.mode](a)
