#!/usr/bin/env python3
"""Trivial-policy check on the shared-budget simulator: accept every request
(tau=2.0, never sheds) against shedding every mMTC request (tau=0.0), on the
held-out eval streams (5000 + seed). --backlog-reset applies the M63
per-episode queue reset. Usage (cwd = framework/):
    m63_acceptall_probe.py --out <dir> --seeds 900 ... [--backlog-reset]"""
import argparse, json, statistics as st, sys
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
import m62_reviewer_experiments as m62
import m2_run_experiment as m2
from m2_correctness_metrics import per_seed_metrics
from qoe_oran_framework.config import load_saclb_config
from shared_budget_kpm_source import make_shared_budget_factory

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--seeds", type=int, nargs="+", required=True)
ap.add_argument("--backlog-reset", action="store_true")
a = ap.parse_args()
m2.make_kpm_source_factory = make_shared_budget_factory
if a.backlog_reset:
    m62.install_backlog_reset()
cfg = load_saclb_config(m2.CONFIG_PATH)
sd = {k: v.sd for k, v in cfg.slice_by_id.items()}
kf = m2.make_kpm_source_factory(cfg, sd)

def slice_comp(path):
    acc = {}
    for l in open(path):
        ev = json.loads(l).get("evidence", {})
        if isinstance(ev, dict) and ev.get("rollup"):
            for k, v in ev["episode_sla_compliance_by_slice"].items():
                acc.setdefault(k, []).append(v)
    return {k: st.mean(v) for k, v in acc.items()}

res = {}
for tau in (2.0, 0.0):
    rows = []
    for s in a.seeds:
        p = m62._heuristic_eval(cfg, kf, tau, m2.EVAL_SEED_OFFSET + s, 50, f"{a.out}/tau{tau}/seed{s}", "offline_eval")
        r, mb, tb = per_seed_metrics(p)
        rows.append({"seed": s, "reward": r, "mmtc_blocks": mb, "blocks": tb, "sla": slice_comp(p)})
    comp = {k: st.mean([x["sla"][k] for x in rows]) for k in rows[0]["sla"]}
    res[str(tau)] = {"reward": st.mean([x["reward"] for x in rows]), "sla": comp, "per_seed": rows}
    print(f"tau={tau}: reward/step={res[str(tau)]['reward']:.3f} sla={ {k: round(v, 3) for k, v in comp.items()} }", flush=True)
json.dump(res, open(f"{a.out}/probe.json", "w"), indent=1)
