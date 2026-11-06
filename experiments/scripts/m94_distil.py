#!/usr/bin/env python3
"""M94: distil AXIOM's admission decisions into small decision trees and run them as a rule (Gate D).

Pre-registered in docs/PAPER5_M94_preregistration.md. Stored checkpoints only; no retraining; framework untouched.

Subcommands (cwd = framework/):
  probe     replay a stored AXIOM checkpoint for 50 episodes on the seed's training stream (seed) or its
            held-out stream (5000 + seed), exactly as m64_run.eval_marl runs an evaluation, and record for every
            actual request the gNB's features and AXIOM's decision. The held-out replay must reproduce the stored
            evaluation reward exactly.
  fit       per target: choose one tree depth in {1, 2, 3} by 5-fold cross-validated fidelity on training-stream
            decisions only (mean over seeds, ties to the shallower tree), fit one tree per slice and seed at that
            depth on all of that seed's training-stream decisions, and report held-out fidelity at every depth.
  eval      run the fitted trees as a rule arm (distilled_tree) through mc_runner's no-learning path, like the
            tuned rules, for 50 episodes on each seed's held-out stream.
  check     consistency checks of the feature paths (see main()).

Features of a request at gNB i for slice k: i's URLLC queue (queue_len_norm), i's congestion level (served PRBs
over the budget, the signal the tuned rules read), slice k's PRB-used ratio at i (slice PRBs over the budget),
and the mean congestion level of i's neighbours in the layout. Label: 1 if AXIOM rejects.
"""
import argparse
import glob
import json
import os
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/framework")

ROOT = "/home/kmanojp/oranslice_rig/experiments/results"
OUT = f"{ROOT}/m94"
S15 = list(range(900, 912)) + [1000, 1001, 1002]
S30 = list(range(900, 930))
TARGETS = {  # name: (checkpoint cell, n, topology, seeds, tuned-rule cell)
    "B7_ring_900": ("m79/ep900_n7_ring", 7, "ring", S15, "m64/n7_ring"),
    "B7_ring_300": ("m64/n7_ring", 7, "ring", S15, "m64/n7_ring"),
    "B3": ("m64/n3_fully_connected", 3, "fully_connected", S30, "m64/n3_fully_connected"),
}
SLICES = ("urllc", "embb", "mmtc")
FEATURES = ("urllc_queue", "congestion", "slice_prb_used", "neighbour_congestion")
DEPTHS = (1, 2, 3)


def setup(n, topology):
    import coupled_dynamic_kpm_source as cd
    import m62_reviewer_experiments as m62
    import m64_run
    from qoe_oran_framework.config import load_saclb_config
    m62.install_backlog_reset()
    cfg = load_saclb_config(m64_run.CONFIGS[n])
    sd = {k: v.sd for k, v in cfg.slice_by_id.items()}
    factory = cd.make_coupled_factory(cfg, sd, topology=topology)
    nbrs = cd.neighbour_lists(len(cfg.gnb_ids), topology)
    return cfg, factory, nbrs


def feats_from_nodes(nf, i, k, nbrs, slices):
    iu = slices.index("urllc")
    cong = lambda j: float(nf[j, 3 * iu + 1])
    nb = nbrs[i]
    return [float(nf[i, 3 * iu + 2]), cong(i), float(nf[i, 3 * slices.index(k)]),
            float(np.mean([cong(j) for j in nb])) if nb else 0.0]


def probe(job):
    target, seed, stream = job
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    import torch
    torch.set_num_threads(1)
    import m6_run_experiment as m6
    import m64_run
    from m2_correctness_metrics import per_seed_metrics
    from m64_axiom2 import AxiomV2Policy
    from qoe_oran_framework.env import RANEnv
    from qoe_oran_framework.marl.marl_env import node_feature_dim, request_context_dim
    from qoe_oran_framework.marl.marl_training import run_episodes_marl
    from qoe_oran_framework.omega_logger import OmegaLogger
    cell, n, topo, _, _ = TARGETS[target]
    cfg, factory, nbrs = setup(n, topo)
    slices = [s.slice_id for s in cfg.slices]
    policy = AxiomV2Policy(n, node_feature_dim(cfg), request_context_dim(cfg), 2, m6.adjacency_for(topo, n))
    policy.load_checkpoint(f"{ROOT}/{cell}/axiom2/seed{seed}/train/checkpoint.pt")
    X, y, sl, cong_spread = [], [], [], 0.0
    orig = policy.select_actions

    def select_actions(node_features, requests, training=False):
        nonlocal cong_spread
        acts = orig(node_features, requests, training=training)
        nf = np.asarray(node_features)
        cong_spread = max(cong_spread, float(np.max(np.ptp(nf[:, 1::3], axis=1))))
        for (i, ctx), a in zip(requests, acts):
            k = slices[int(np.argmax(ctx))]
            X.append(feats_from_nodes(nf, i, k, nbrs, slices))
            y.append(1 - int(a))           # action 1 = accept, so label 1 = reject
            sl.append(SLICES.index(k))
        return acts
    policy.select_actions = select_actions
    s_run = seed if stream == "train" else m64_run.EVAL_OFFSET + seed
    env = RANEnv(cfg, factory(s_run), seed=s_run, reward_mode="sla")
    log = f"{OUT}/probe/{target}/{stream}_seed{seed}.jsonl"
    Path(os.path.dirname(log)).mkdir(parents=True, exist_ok=True)
    if os.path.exists(log):
        os.remove(log)                              # the omega logger appends
    with OmegaLogger(log) as omega:
        run_episodes_marl(env, policy, "axiom2", omega, 50, s_run, f"axiom2_seed{seed}_{stream}", "offline_eval", False, cfg)
    env.close()
    from m66_verify import find_eval, read
    mine = read(log)
    reward = mine["reward"]
    os.remove(log)
    np.savez_compressed(f"{OUT}/probe/{target}/{stream}_seed{seed}.npz", X=np.array(X), y=np.array(y), slice=np.array(sl))
    exact = None
    if stream == "heldout":
        st = read(find_eval(cell, "axiom2", seed))
        exact = (st["reward"] == mine["reward"] and st["blocks"] == mine["blocks"] and st["sla"] == mine["sla"])
    return target, seed, stream, reward, exact, len(y), cong_spread


def load_probe(target, stream, seed):
    d = np.load(f"{OUT}/probe/{target}/{stream}_seed{seed}.npz")
    return d["X"], d["y"], d["slice"]


def fit_trees(X, y, s, depth):
    from sklearn.tree import DecisionTreeClassifier
    trees = {}
    for k in range(3):
        m = s == k
        if not m.any():
            trees[k] = ("const", 0)
        elif len(np.unique(y[m])) == 1:
            trees[k] = ("const", int(y[m][0]))
        else:
            trees[k] = ("tree", DecisionTreeClassifier(max_depth=depth, class_weight="balanced", random_state=0).fit(X[m], y[m]))
    return trees


def predict(trees, X, s):
    out = np.zeros(len(s), dtype=int)
    for k, (kind, t) in trees.items():
        m = s == k
        if m.any():
            out[m] = t if kind == "const" else t.predict(X[m])
    return out


def cv_fidelity(X, y, s, depth):
    from sklearn.model_selection import KFold
    agree, total = 0, 0
    for tr, te in KFold(5, shuffle=True, random_state=0).split(X):
        t = fit_trees(X[tr], y[tr], s[tr], depth)
        agree += int((predict(t, X[te], s[te]) == y[te]).sum())
        total += len(te)
    return agree / total


def do_fit(target):
    from sklearn.tree import export_text
    _, _, _, seeds, _ = TARGETS[target]
    res = {"cv": {}, "heldout": {}, "per_seed": {}}
    data = {s: (load_probe(target, "train", s), load_probe(target, "heldout", s)) for s in seeds}
    for d in DEPTHS:
        cv, ho = [], []
        for s, ((X, y, sl), (Xh, yh, slh)) in data.items():
            cv.append(cv_fidelity(X, y, sl, d))
            ho.append(float((predict(fit_trees(X, y, sl, d), Xh, slh) == yh).mean()))
        res["cv"][d], res["heldout"][d] = float(np.mean(cv)), float(np.mean(ho))
    best = max(DEPTHS, key=lambda d: (round(res["cv"][d], 12), -d))
    res["selected_depth"] = best
    Path(f"{OUT}/trees/{target}").mkdir(parents=True, exist_ok=True)
    for s, ((X, y, sl), (Xh, yh, slh)) in data.items():
        t = fit_trees(X, y, sl, best)
        pickle.dump(t, open(f"{OUT}/trees/{target}/seed{s}.pkl", "wb"))
        ps = {"heldout_fidelity": float((predict(t, Xh, slh) == yh).mean()),
              "train_requests": int(len(y)), "heldout_requests": int(len(yh)),
              "reject_share_train": {SLICES[k]: float(y[sl == k].mean()) if (sl == k).any() else None for k in range(3)}}
        for k, (kind, tr) in t.items():
            if kind == "const":
                ps[f"tree_{SLICES[k]}"] = f"constant: {'reject' if tr else 'accept'}"
            else:
                ps[f"tree_{SLICES[k]}"] = export_text(tr, feature_names=list(FEATURES), decimals=4)
                tt = tr.tree_
                ps[f"splits_{SLICES[k]}"] = [(FEATURES[tt.feature[j]], float(tt.threshold[j])) for j in range(tt.node_count) if tt.feature[j] >= 0]
        res["per_seed"][str(s)] = ps
    json.dump(res, open(f"{OUT}/trees/{target}/fit.json", "w"), indent=1)
    print(f"[m94 fit] {target}: cv {res['cv']}, held-out {res['heldout']}, selected depth {best}")


class TreeRule:
    """Runs fitted per-slice trees through mc_runner's no-learning path, like ThresholdHeuristic."""

    def __init__(self, gnb_ids, neighbours, trees):
        self.gnb_ids, self.index, self.nbrs, self.trees = list(gnb_ids), {g: i for i, g in enumerate(gnb_ids)}, neighbours, trees

    def _cong(self, cluster_state, g):
        per = cluster_state.per_gnb.get(g, {})
        a = next(iter(per.values()), None)
        return a.congestion_level if a is not None else 0.0

    def features(self, r, cluster_state):
        per = cluster_state.per_gnb.get(r.gnb_id, {})
        i = self.index[r.gnb_id]
        nb = self.nbrs[i]
        return [per["urllc"].queue_len_norm if "urllc" in per else 0.0, self._cong(cluster_state, r.gnb_id),
                per[r.slice_id].prb_used_ratio if r.slice_id in per else 0.0,
                float(np.mean([self._cong(cluster_state, self.gnb_ids[j]) for j in nb])) if nb else 0.0]

    def decide(self, pending, cluster_state):
        out = []
        for r in pending:
            kind, t = self.trees[SLICES.index(r.slice_id)]
            rej = t if kind == "const" else int(t.predict(np.array([self.features(r, cluster_state)]))[0])
            out.append(0 if rej else 1)
        return out


def run_rule(target, seed, rule_factory, out_dir):
    import m64_run
    from m2_correctness_metrics import per_seed_metrics
    from qoe_oran_framework.mc_runner import run_mc
    cell, n, topo, _, _ = TARGETS[target]
    cfg, factory, nbrs = setup(n, topo)
    d = f"{out_dir}/seed{seed}/eval"
    import shutil
    shutil.rmtree(d, ignore_errors=True)          # the omega logger appends, so never reuse a seed's directory
    run_mc(cfg, "lb_only", factory, n_reps=1, episodes_per_rep=50, base_seed=m64_run.EVAL_OFFSET + seed, mode="offline_eval",
           training=False, results_dir=d, policy_factory=lambda _s: rule_factory(cfg, nbrs), reward_mode="sla")
    return per_seed_metrics(f"{d}/lb_only/offline_eval/rep_0/omega_log.jsonl")[0]


def evaluate(job):
    target, seed = job
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    trees = pickle.load(open(f"{OUT}/trees/{target}/seed{seed}.pkl", "rb"))
    r = run_rule(target, seed, lambda cfg, nbrs: TreeRule(cfg.gnb_ids, nbrs, trees), f"{OUT}/{target}/distilled_tree")
    return target, seed, r


def check_job(job):
    """Feature-path check: the tuned local rule, re-expressed on this script's features, must reproduce the stored
    rule_local evaluation exactly when run through TreeRule's decide path."""
    target, seed = job
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    from m66_verify import find_eval, read
    _, _, _, _, rcell = TARGETS[target]
    sel = json.load(open(f"{ROOT}/{rcell}/rule_local_selection.json"))["selected"]
    assert sel.get("tau_q") is None and sel.get("tau_n") is None and sel["tau_c"] == 0.0, sel

    class Stub:  # depth-free stand-ins with the tuned rule's decisions on TreeRule's features
        def __init__(self, f):
            self.f = f

        def predict(self, X):
            return np.array([self.f(x) for x in X])
    trees = {0: ("const", 0), 1: ("tree", Stub(lambda x: int(x[0] >= sel["tau_e"]))), 2: ("tree", Stub(lambda x: int(x[1] >= sel["tau_c"])))}
    out = f"/tmp/claude-1000/-home-kmanojp-oranslice-rig/729c8c65-e20f-49fc-a7be-ab16a1b45414/scratchpad/m94_check/{target}"
    run_rule(target, seed, lambda cfg, nbrs: TreeRule(cfg.gnb_ids, nbrs, trees), out)
    mine = read(f"{out}/seed{seed}/eval/lb_only/offline_eval/rep_0/omega_log.jsonl")
    st = read(find_eval(rcell, "rule_local", seed))
    return target, seed, mine["reward"], st["reward"] == mine["reward"] and st["blocks"] == mine["blocks"] and st["sla"] == mine["sla"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["probe", "fit", "eval", "check"])
    ap.add_argument("--targets", nargs="+", default=list(TARGETS))
    ap.add_argument("--seeds", type=int, nargs="+")
    ap.add_argument("--streams", nargs="+", default=["train", "heldout"])
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args()
    sd = lambda t: a.seeds or TARGETS[t][3]
    if a.cmd == "fit":
        for t in a.targets:
            do_fit(t)
        return
    if a.cmd == "probe":
        jobs = [(t, s, st) for t in a.targets for s in sd(t) for st in a.streams]
        fn = probe
    elif a.cmd == "eval":
        jobs = [(t, s) for t in a.targets for s in sd(t)]
        fn = evaluate
    else:
        jobs = [(t, s) for t in a.targets for s in sd(t)]
        fn = check_job
    rows = []
    with ProcessPoolExecutor(a.workers, max_tasks_per_child=1) as ex:   # one process per job: M62 patches install once
        for r in ex.map(fn, jobs):
            rows.append(r)
            print(f"[m94 {a.cmd}]", *r, flush=True)
    Path(OUT).mkdir(parents=True, exist_ok=True)
    tag = "_".join(a.targets) if a.cmd != "check" else "check"
    json.dump([list(map(lambda v: v if not isinstance(v, np.generic) else v.item(), r)) for r in rows],
              open(f"{OUT}/{a.cmd}_{tag}{'_' + '_'.join(map(str, a.seeds)) if a.seeds else ''}.json", "w"), indent=1)


if __name__ == "__main__":
    main()
