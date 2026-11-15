#!/usr/bin/env python3
"""Gate 3 re-analysis from stored logs only (no training, no re-evaluation). Run from framework/:
  ../venv/bin/python ../experiments/scripts/gate3_reanalysis.py curves|admission
curves     training reward per gNB per step in each training episode, per seed, for the four learned policies
           (Env A at 3, 19 hex and 37 hex gNBs, Env B at 3 and 7 ring gNBs), from the training logs
admission  per-slice acceptance ratio accepted / (accepted + blocked) on the held-out evaluation streams,
           for every policy of Tables 3 and 4
Samples are the paper's own (stored plus M107 seeds), resolved through m66_verify.pooled_paths.
"""
import gzip, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m66_verify as V
from m66_verify import pooled_paths, S15, S30

OUT = "/home/kmanojp/oranslice_rig/experiments/results/gate3"
S30_19 = V.S30_19 if hasattr(V, "S30_19") else None
LEARN = ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")


def op(p):
    return gzip.open(p, "rt") if p.endswith(".gz") else open(p)


def gz(p):
    return p if os.path.exists(p) else (p + ".gz" if os.path.exists(p + ".gz") else None)


def train_curve(eval_path):
    """Mean reward per step of each training episode, from the training log beside an evaluation log."""
    run = eval_path.split("/eval/")[0]
    c = os.path.join(run, "train", "curve.json")                      # MAPPO stores its curve directly
    if os.path.exists(c):
        return [float(x) for x in json.load(open(c))["episode_mean_reward"]]
    p = gz(os.path.join(run, "train", "omega_log.jsonl")) or gz(os.path.join(run, "train", "dqn", "offline_train", "rep_0", "omega_log.jsonl"))
    if p is None:
        return None
    ep = {}
    for line in op(p):
        r = json.loads(line); ev = r.get("evidence", r)
        if isinstance(ev, dict) and not ev.get("rollup") and "reward" in ev:
            ep.setdefault(r["episode"], []).append(ev["reward"])
    return [float(np.mean(ep[k])) for k in sorted(ep)]


def admission(eval_path):
    acc, blk, pend = {}, {}, 0
    for line in op(eval_path):
        r = json.loads(line); ev = r.get("evidence", r)
        if not isinstance(ev, dict):
            continue
        if ev.get("rollup"):
            for k, v in ev.get("episode_block_by_slice", {}).items():
                blk[k] = blk.get(k, 0) + v
        elif "accepted_counts" in ev:
            pend += ev["n_pending"]
            for k, v in ev["accepted_counts"].items():
                acc[k] = acc.get(k, 0) + v
    tot = sum(acc.values()) + sum(blk.values())
    return {"accepted": acc, "blocked": blk, "pending": pend, "balanced": tot == pend}


def curves():
    cells = {"A3": (3, lambda a: ("m65_reviewer/base" if a in ("axiom2", "mappo_tuned") else "m63_reviewer/base", S30)),
             "A19hex": (19, lambda a: ("m65_scaling/n19_hex", V.S30_19)),
             "A37hex": (37, lambda a: ("m73/A_n37_hex", V.S30_19)),
             "B3": (3, lambda a: ("m64/n3_fully_connected", S30)),
             "B7ring": (7, lambda a: ("m64/n7_ring", S15))}
    out = {}
    for name, (n, f) in cells.items():
        out[name] = {"n_gnb": n, "arms": {}}
        for a in LEARN:
            cell, seeds = f(a)
            runs, missing = {}, []
            for s, p in pooled_paths(cell, a, seeds):
                c = train_curve(p)
                if c is None:
                    missing.append(s)
                else:
                    runs[s] = [x / n for x in c]
            out[name]["arms"][a] = {"runs": runs, "missing": missing}
            L = sorted({len(v) for v in runs.values()})
            print(name, a, "seeds", len(runs), "missing", len(missing), "episodes", L, flush=True)
    json.dump(out, open(f"{OUT}/curves.json", "w"))


def admission_all():
    sets = {"A3": [("m65_reviewer/base", a) for a in ("axiom2", "mappo_tuned")] + [("m63_reviewer/base", a) for a in ("heuristic", "single_agent_dqn", "independent_dqn")],
            "B3": [("m64/n3_fully_connected", a) for a in ("rule_accept_all", "rule_static", "rule_local", "rule_neighbour", "axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")]}
    out = {}
    for name, lst in sets.items():
        out[name] = {}
        for cell, a in lst:
            per = {}
            for s, p in pooled_paths(cell, a, S30):
                per[s] = admission(p)
            ok = all(v["balanced"] for v in per.values())
            ratio = {k: float(np.mean([v["accepted"].get(k, 0) / max(1, v["accepted"].get(k, 0) + v["blocked"].get(k, 0)) for v in per.values()]))
                     for k in ("urllc", "embb", "mmtc")}
            out[name][a] = {"n": len(per), "balanced": ok, "acceptance": ratio, "per_seed": per}
            print(name, a, len(per), "balanced" if ok else "NOT BALANCED", {k: round(100 * v, 1) for k, v in ratio.items()}, flush=True)
    json.dump(out, open(f"{OUT}/admission.json", "w"))


if __name__ == "__main__":
    {"curves": curves, "admission": admission_all}[sys.argv[1]]()
