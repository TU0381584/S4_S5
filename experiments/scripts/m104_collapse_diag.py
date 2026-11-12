#!/usr/bin/env python3
"""Reproduces items 1-3 of docs/PAPER5_M104_diagnosis.md (exploratory, not pre-registered).

Rebuilt on 2026-11-12. The original scratch scripts (collapse_diag.py, collapse_probe.py) were never committed and
were lost when the scratch directory was cleared, so this file replaces them and its output is the record.
  item 1: mMTC blocks per training episode, last 50 episodes, for every 37-gNB AXIOM and MLP run.
  item 2: step-by-step mMTC admissions in the final training episode of runs 8002, 8010, 919 and healthy 8000.
  item 3: stored checkpoints of 8002, 8010, 8000 re-evaluated for 5 episodes without learning: greedy on the
          evaluation stream, with epsilon 0.05 on the evaluation stream, and greedy on the training stream.
Run from framework/ with M63_BACKLOG_RESET=1 M64_AXIOM_V2=1:
  ../venv/bin/python ../experiments/scripts/m104_collapse_diag.py --out ../experiments/results/m104_collapse_diag.json
"""
import argparse
import gzip
import json
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m64_run  # noqa: E402
import m73_run  # noqa: E402
from m66_verify import find_eval, read  # noqa: E402

R = "/home/kmanojp/oranslice_rig/experiments/results"
AX = [("m96/A_fresh/n37_hex", "axiom2", s) for s in range(8000, 8020)] + \
     [("m101/A_n37_hex", "axiom2", s) for s in range(9960, 9980)] + \
     [("m73/A_n37_hex", "axiom2", s) for s in list(range(900, 927)) + [1000, 1001, 1002]]
ML = [("m100/A_n37_hex", "axiom2_mlp", s) for s in range(8000, 8020)] + [("m101/A_n37_hex", "axiom2_mlp", s) for s in range(9960, 9980)]


def train_log(cell, arm, s):
    p = f"{R}/{cell}/{arm}/seed{s}/train/omega_log.jsonl"
    f = gzip.open(p + ".gz", "rt") if os.path.exists(p + ".gz") else open(p)
    return [json.loads(l) for l in f]


def item1():
    out = {"axiom": {}, "mlp": {}}
    for grp, runs in (("axiom", AX), ("mlp", ML)):
        for c, a, s in runs:
            recs = train_log(c, a, s)
            mm = {r["episode"]: r["evidence"]["episode_block_by_slice"].get("mmtc", 0) for r in recs if r["evidence"].get("rollup")}
            last = max(mm)
            coll = read(find_eval(c, a, s))["collapsed"]
            out[grp][f"{c}:{s}"] = {"collapsed_eval": coll, "mmtc_last50": float(np.mean([mm[e] for e in mm if e > last - 50]))}
    ax = out["axiom"]
    summ = {"axiom_runs": len(ax), "axiom_collapsed": sum(v["collapsed_eval"] for v in ax.values()),
            "axiom_healthy_mean": float(np.mean([v["mmtc_last50"] for v in ax.values() if not v["collapsed_eval"]])),
            "axiom_collapsed_mean": float(np.mean([v["mmtc_last50"] for v in ax.values() if v["collapsed_eval"]])),
            "mlp_runs": len(out["mlp"]), "mlp_collapsed": sum(v["collapsed_eval"] for v in out["mlp"].values()),
            "mlp_mean": float(np.mean([v["mmtc_last50"] for v in out["mlp"].values()])),
            "collapsed_runs": {k: round(v["mmtc_last50"], 1) for k, v in ax.items() if v["collapsed_eval"]}}
    return summ, out


def item2():
    out = {}
    for c, s in (("m96/A_fresh/n37_hex", 8002), ("m96/A_fresh/n37_hex", 8010), ("m73/A_n37_hex", 919), ("m96/A_fresh/n37_hex", 8000)):
        recs = train_log(c, "axiom2", s)
        last = max(r["episode"] for r in recs)
        out[f"{c}:{s}"] = [r["evidence"]["accepted_counts"]["mmtc"] for r in recs
                           if r["episode"] == last and not r["evidence"].get("rollup")]
    return out


def item3():
    m73_run.install()
    m64_run.m62.install_backlog_reset()
    cfg = m64_run.load_saclb_config(m64_run.CONFIGS[37])
    sd = {k: v.sd for k, v in cfg.slice_by_id.items()}
    from shared_budget_kpm_source import make_shared_budget_factory
    factory = make_shared_budget_factory(cfg, sd)
    adj = m64_run.m6.adjacency_for("hex", 37)
    n, nd, cd_ = len(cfg.gnb_ids), m64_run.node_feature_dim(cfg), m64_run.request_context_dim(cfg)
    out = {}
    for s in (8002, 8010, 8000):
        ck = f"{R}/m96/A_fresh/n37_hex/axiom2/seed{s}/train/checkpoint.pt"
        for mode, stream, eps in (("greedy_eval_stream", m64_run.EVAL_OFFSET + s, None),
                                  ("eps0.05_eval_stream", m64_run.EVAL_OFFSET + s, 0.05),
                                  ("greedy_training_stream", s, None)):
            pol = m64_run.AxiomV2Policy(n, nd, cd_, 2, adj)
            pol.load_checkpoint(ck)
            if eps is not None:
                pol.epsilon = eps
                orig = pol.select_actions
                pol.select_actions = lambda nf, req, training=False, orig=orig: orig(nf, req, training=True)
            np.random.seed(stream)
            env = m64_run.RANEnv(cfg, factory(stream), seed=stream, reward_mode="sla")
            with tempfile.TemporaryDirectory() as d:
                with m64_run.OmegaLogger(f"{d}/o.jsonl") as om:
                    m64_run.run_episodes_marl(env, pol, "axiom2", om, 5, stream, f"probe_{s}", "offline_eval", False, cfg)
                env.close()
                blocks = {}
                for line in open(f"{d}/o.jsonl"):
                    e = json.loads(line).get("evidence", {})
                    if e.get("rollup"):
                        for k, v in e["episode_block_by_slice"].items():
                            blocks[k] = blocks.get(k, 0) + v
            out[f"{s}:{mode}"] = blocks
            print(s, mode, blocks, flush=True)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    s1, full1 = item1()
    print("item 1:", json.dumps(s1))
    s2 = item2()
    for k, v in s2.items():
        print("item 2:", k, v)
    s3 = item3()
    json.dump({"item1": s1, "item1_runs": full1, "item2": s2, "item3": s3}, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
