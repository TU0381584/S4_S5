#!/usr/bin/env python3
"""M75 runner: m64_run.py (through m73_run.py) plus the fourth review's runs.

docs/PAPER5_M75_preregistration.md fixes the plan. Neither the framework nor
m64_run.py is modified; everything below is selected by environment variables.

  M75_LR=<float>        learning rate of the DQN baselines (single-agent and independent)
  M75_BATCH=<int>       their training minibatch size
  M75_PERGNB=1          during evaluation, record whether each gNB meets each slice's SLA
                        at every step, with exactly the per-gNB test that the framework's
                        reward.check_violations applies before it ORs the result over gNBs,
                        and write per_gnb_sla.json next to the evaluation log. The training
                        reward and every logged quantity are unchanged.

Extra arm: rule_local_transfer applies, without re-tuning, the local rule selected on
training streams in Env B at seven gNBs (m64/n7_hex/rule_local_selection.json), the same
rule that was selected at three gNBs.

Usage (cwd = framework/): same arguments as m64_run.py.
"""
import functools
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m73_run  # noqa: E402  (registers N=37 and seeds the single-agent DQN)
import m64_run  # noqa: E402
from qoe_oran_framework import reward as rw  # noqa: E402
from qoe_oran_framework.mc_runner import build_policy  # noqa: E402

RESULTS = "/home/kmanojp/oranslice_rig/experiments/results"
SLICES = ("urllc", "embb", "mmtc")
ACC = {"on": False, "steps": 0, "ok": None, "n": 0}


def per_gnb_check(cluster_state, slice_specs):
    if ACC["on"]:
        gnbs = sorted(cluster_state.per_gnb)
        if ACC["ok"] is None:
            ACC["ok"] = {s: [0] * len(gnbs) for s in SLICES}
            ACC["gnbs"] = gnbs
        for gi, g in enumerate(gnbs):
            for sl, agg in cluster_state.per_gnb[g].items():
                if sl not in slice_specs or sl not in ACC["ok"]:
                    continue
                spec = slice_specs[sl]
                if not (agg.queue_len_norm > 1.0 or agg.loss_proxy > spec.loss_budget_pct):
                    ACC["ok"][sl][gi] += 1
        ACC["steps"] += 1
    return _orig_check(cluster_state, slice_specs)


_orig_check = rw.check_violations


def start():
    ACC.update(on=True, steps=0, ok=None)


def dump(path):
    ACC["on"] = False
    if not ACC["steps"]:
        return
    per = {s: [c / ACC["steps"] for c in v] for s, v in ACC["ok"].items()}
    out = {"steps": ACC["steps"], "gnbs": ACC["gnbs"], "per_gnb_compliance": per,
           "mean_compliance": {s: sum(v) / len(v) for s, v in per.items()}}
    Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)
    json.dump(out, open(path, "w"), indent=1)


def install():
    m73_run.install()
    lr, batch = os.environ.get("M75_LR"), os.environ.get("M75_BATCH")
    orig_run_mc, orig_marl, orig_eval_marl = m64_run.run_mc, m64_run.run_episodes_marl, m64_run.eval_marl
    pergnb = os.environ.get("M75_PERGNB") == "1"
    if pergnb:
        rw.check_violations = per_gnb_check

    def run_mc(cfg, algorithm, factory, *a, **kw):
        mode, training = kw.get("mode"), kw.get("training")
        if training and algorithm == "dqn":
            if batch:
                kw["batch_size"] = int(batch)
            if lr and kw.get("policy_factory") is None:
                kw["policy_factory"] = lambda _s: build_policy("dqn", cfg, learning_rate=float(lr))
        on = pergnb and mode == "offline_eval"
        if on:
            start()
        out = orig_run_mc(cfg, algorithm, factory, *a, **kw)
        if on:
            dump(os.path.join(kw["results_dir"], "per_gnb_sla.json"))
        return out
    m64_run.run_mc = run_mc

    ind_cls = m64_run.IndependentPerGnbDqnPolicy
    if batch:
        @functools.wraps(orig_marl)
        def run_episodes_marl(*a, **kw):
            if len(a) > 8 and a[8] and isinstance(a[1], ind_cls):     # training the independent DQN only
                kw.setdefault("batch_size", int(batch))
            return orig_marl(*a, **kw)
        m64_run.run_episodes_marl = run_episodes_marl
    if lr:
        def make_ind(*a, **kw):                             # m64_run passes learning_rate explicitly, so force it
            kw["learning_rate"] = float(lr)
            return ind_cls(*a, **kw)
        m64_run.IndependentPerGnbDqnPolicy = make_ind

    def eval_marl(cfg, factory, policy, arm, seed, out_dir):
        if pergnb:
            start()
        p = orig_eval_marl(cfg, factory, policy, arm, seed, out_dir)
        if pergnb:
            dump(f"{out_dir}/{arm}/seed{seed}/eval/per_gnb_sla.json")
        return p
    m64_run.eval_marl = eval_marl

    orig_rules = m64_run.run_rules

    def run_rules(arm, cfg, factory, nbrs, seeds, out_dir):
        if arm != "rule_local_transfer":
            return orig_rules(arm, cfg, factory, nbrs, seeds, out_dir)
        rule = json.load(open(f"{RESULTS}/m64/n7_hex/rule_local_selection.json"))["selected"]
        out = {}
        for s in seeds:
            m64_run.clear(out_dir, arm, s)
            p = m64_run.rule_eval(cfg, factory, rule, nbrs, m64_run.EVAL_OFFSET + s, 50, f"{out_dir}/{arm}/seed{s}/eval", "offline_eval")
            out[s] = m64_run.per_seed_metrics(p)[0]
        return rule, out
    m64_run.run_rules = run_rules
    if lr or batch:
        print(f"[m75] DQN baselines: learning rate {lr or 'default'}, minibatch {batch or 'default'}", flush=True)
    if pergnb:
        print("[m75] per-gNB SLA recording on during evaluation", flush=True)


if __name__ == "__main__":
    install()
    m64_run.main()
