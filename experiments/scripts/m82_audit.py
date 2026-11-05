#!/usr/bin/env python3
"""M82 pre-submission audit: every number in the two documents that no earlier check pinned to its text.

Called from m66_verify.main() as m82_audit.run(C). Each check recomputes its value from the stored results, the
configuration files, or the code that produced the results, and requires the exact printed text to be present.
Run on its own (python m82_audit.py --tex ... --supp ...) it prints each check without touching the main verifier.
"""
import inspect
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/kmanojp/oranslice_rig/framework")
import m66_verify as V  # noqa: E402  helpers only: seeds_of, prio, mean, paired, holm, read, find_eval

ROOT = V.ROOT
FW = "/home/kmanojp/oranslice_rig/framework/qoe_oran_framework"
SC = "/home/kmanojp/oranslice_rig/experiments/scripts"
S15, S30, S30_19, S10, REP = V.S15, V.S30, V.S30_19, V.S10, V.REP   # the verifier's own seed lists
LAY = ("fully_connected", "ring", "hex")
ARMS = ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")


def pct(x):
    return round(100 * x, 1)


def V_shift(n_dir, sh, arm, ss=tuple(range(905, 930))):
    out = {}
    for s_ in ss:
        base = f"{ROOT}/m72/B_shift/{n_dir}/{sh}/{arm}/seed{s_}"
        p = f"{base}/omega_log.jsonl" if arm == "axiom2" else f"{base}/lb_only/offline_eval/rep_0/omega_log.jsonl"
        for c_ in (p, p + ".gz"):          # some logs are stored compressed
            if os.path.exists(c_):
                out[s_] = V.read(c_)
                break
    return out


def _jsonable(d):
    """Detail values go into the verifier's JSON report, whose keys must be strings."""
    if isinstance(d, dict):
        return {(k if isinstance(k, (str, int, float, bool)) or k is None else "|".join(map(str, k)) if isinstance(k, tuple) else str(k)): _jsonable(v) for k, v in d.items()}
    if isinstance(d, (list, tuple)):
        return [_jsonable(x) for x in d]
    return d


def run(C):
    C.supp_only = C.tex[len(C.main):]
    _note = C.note
    C.note = lambda label, ok, detail: _note(label, ok, _jsonable(detail))
    seeds_of, prio, mean, paired = V.seeds_of, V.prio, V.mean, V.paired

    # ---------------- parameter table and simulator constants against the code that produced the results
    import yaml
    import torch
    cfg = yaml.safe_load(open(f"{FW}/configs/saclb_offline_dqn.yaml"))
    sl = {x["slice_id"]: x for x in cfg["slices"]}
    C.note("M82 Table 2 slice rows match the configuration", [(sl[k]["min_ratio_floor"], sl[k]["max_ratio_cap"]) for k in ("urllc", "embb", "mmtc")] == [(5, 33), (10, 66), (5, 11)]
           and [sl[k]["priority_weight"] for k in ("urllc", "embb", "mmtc")] == [12.0, 3.5, 0.3]
           and [sl[k]["violation_penalty"] for k in ("urllc", "embb", "mmtc")] == [10.0, 5.0, 2.5]
           and [sl[k]["latency_budget_ms"] for k in ("urllc", "embb", "mmtc")] == [15, 45, 65]
           and [sl[k]["loss_budget_pct"] for k in ("urllc", "embb", "mmtc")] == [0.8, 2.0, 3.5]
           and all(sl[k]["accept_reward"] == 1.0 for k in sl)
           and "Floor and cap, PRB ratio & 5 to 33, 10 to 66, 5 to 11 & Priority weight $\\omega_k$ & 12.0, 3.5, 0.3" in C.main
           and "Violation penalty $\\lambda_k$ & 10.0, 5.0, 2.5 & Per-accept reward $R_k$ & 1.0 for every slice" in C.main
           and "Latency budget & 15, 45, 65 ms & Loss budget & 0.8\\%, 2.0\\%, 3.5\\%" in C.main, None)
    C.note("M82 Table 2 reward, episode, arrival and gate rows match the configuration",
           cfg["reward"]["congestion_coeff"] == 1.5 and cfg["reward"]["lb_coeff"] == 1.0
           and cfg["episode"]["steps_per_episode"] == 60 and cfg["episode"]["step_seconds"] == 5.0
           and cfg["arrivals"]["synthetic_arrivals_per_step"] == 3 and cfg["arrivals"]["max_pending_per_step"] == 12
           and cfg["arrivals"]["ceiling_step_ratio"] == 5 and cfg["B"] == 100
           and "Congestion $\\kappa$, balance $\\beta$ & 1.5, 1.0 & Episode & 60 steps of 5 s, queues emptied at start" in C.main
           and "Requests per step & $N$, uniform slice and gNB, at most $4N$ pending & Demand noise, gate step & $0.005B$ per step, 5 PRB-ratio points per decision" in C.main, None)
    sbt = open(f"{SC}/shared_budget_kpm_source.py").read()
    cds = open(f"{SC}/coupled_dynamic_kpm_source.py").read()
    C.note("M82 simulator constants in the text match the simulator code",
           re.search(r"^LOAD_FACTOR = 1\.05\b", sbt, re.M) and re.search(r"^OFFERED_VOLATILITY = 0\.005\b", sbt, re.M)
           and re.search(r"^LOAD_MULTIPLIER_RANGE = \(0\.9, 1\.0\)", sbt, re.M) and "1.0 if i == 0 else" in sbt
           and sbt.count("drift = 0.1 * (mean - self._offered[key])") == 1 and cds.count("drift = 0.1 * (mean - self._offered[key])") == 1
           and re.search(r"^LOAD_BASE = 0\.95\b", cds, re.M) and re.search(r"^LOAD_AMPLITUDE = 0\.30\b", cds, re.M)
           and re.search(r"^LOAD_PERIOD = 60\.0\b", cds, re.M) and re.search(r"^COUPLING_ALPHA = 0\.15\b", cds, re.M)
           and [sl[k]["nominal_ratio"] for k in ("urllc", "embb", "mmtc")] == [30, 60, 10]
           and "Each gNB has a budget of $B{=}100$ PRBs in both simulators. The nominal shares are 30, 60, and 10 PRBs for URLLC, eMBB, and mMTC. Each slice's mean offered demand is 105\\% of its share, scaled by a fixed per-gNB multiplier $m_i$ between 0.9 and 1.0." in C.main
           and "$0.95\\,(1+0.3\\sin(2\\pi(s+\\psi_i)/60))$" in C.main and "$B_i(t)=B\\,(1-0.15\\,\\bar u_{\\mathcal{N}(i)}(t-1))$" in C.main
           and "offered PRBs drift 10\\% per step towards" in C.main
           and "whose load the simulator fixes at the nominal level while it draws every other gNB's from 90\\% to 100\\% of it" in C.main, None)
    from decimal import Decimal, ROUND_HALF_UP
    hu = lambda x: int(Decimal(str(round(100 * x, 6))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))   # 94.5 -> 95, 123.5 -> 124
    C.note("M82 Env A and Env B demand ranges follow from the constants", (hu(0.9 * 1.05), hu(1.0 * 1.05)) == (95, 105)
           and (hu(0.9 * 0.95 * 0.7), hu(1.0 * 0.95 * 1.3)) == (60, 124)
           and "about 95\\% to 105\\% of its budget" in C.main and "between about 60\\% and 124\\% of the budget" in C.main, None)

    # the learners as the training script builds them
    import m64_mappo as mp
    import m64_run
    from m64_axiom2 import AxiomV2Policy
    from qoe_oran_framework.config import load_saclb_config
    from qoe_oran_framework.marl.marl_env import node_feature_dim, request_context_dim
    from qoe_oran_framework.marl import marl_training as mt
    c3 = load_saclb_config(f"{FW}/configs/saclb_offline_dqn.yaml")
    n3, nd, cd_ = len(c3.gnb_ids), node_feature_dim(c3), request_context_dim(c3)
    pol = AxiomV2Policy(n3, nd, cd_, 2, np.ones((n3, n3)) - np.eye(n3))
    gl = [m for m in pol.online.modules() if hasattr(m, "W")]
    qh = [m for n_, m in pol.online.named_modules() if n_.startswith("q_head.heads.") and isinstance(m, torch.nn.Linear)]
    mix = sum(p.numel() for n_, p in pol.online.named_parameters() if n_.startswith("mixer."))
    sig = inspect.signature(mt.run_episodes_marl).parameters
    ctd = open(f"{FW}/marl/ctde_policy.py").read()
    C.note("M82 AXIOM as trained matches Table 2 and the 7,782 execution parameters",
           [tuple(m.W.shape) for m in gl] == [(4, nd, 16), (4, 64, 16)] and len(qh) == 6 and all(m.out_features in (32, 2) for m in qh)
           and qh[0].out_features == 32 and pol.optimizer.param_groups[0]["lr"] == 1e-3 and pol.gamma == 0.95
           and (pol.epsilon, pol.epsilon_end, pol._per_episode_epsilon_decay, pol._target_sync_every_episodes) == (1.0, 0.05, 0.985, 10)
           and sum(p.numel() for p in pol.online.parameters()) - mix == 7782
           and "F.smooth_l1_loss(chosen_all, target_all)" in ctd and "clip_grad_norm_(self.online.parameters(), max_norm=1.0)" in ctd
           and (sig["batch_size"].default, sig["replay_capacity"].default, sig["warmup_transitions"].default) == (16, 10000, 32)
           and "Adam, learning rate $10^{-3}$, $\\epsilon$ from 1.0 to 0.05 at $\\times0.985$ per episode, replay 10,000, minibatch 16, warm-up 32, target sync every 10 episodes" in C.main
           and "Two-layer, four-head GAT, hidden and output 16, raw-feature skip, per-slice Q-heads of hidden 32, Huber loss, gradient clip 1.0" in C.main,
           {"gat_W": [tuple(m.W.shape) for m in gl], "params_exec": sum(p.numel() for p in pol.online.parameters()) - mix})
    dqn = open("/home/kmanojp/oranslice_rig/framework/drl_slicing/oranslice_drl/drl_policy.py").read()
    run_src = inspect.getsource(m64_run.run_learned)
    C.note("M82 DQN and MAPPO settings in Table 2 match the code",
           "hidden_dim: int = 128" in dqn and "self.loss_fn = nn.MSELoss()" in dqn
           and (mp.CLIP, mp.ENTROPY, mp.GAE_LAMBDA, mp.LR_CRITIC) == (0.2, 0.01, 0.95, 1e-3)
           and "mp.LR_ACTOR, mp.EPOCHS, mp.MINIBATCH = 1e-3, 10, 64" in run_src
           and "IndependentPerGnbDqnPolicy(n, nd, cd_, 2, learning_rate=1e-3)" in run_src
           and "DQN baselines & Two hidden layers of 128, squared-error loss & MAPPO & Learning rate $10^{-3}$, 10 epochs, minibatch 64, clip 0.2, entropy 0.01, advantage $\\lambda=0.95$" in C.main, None)
    gat = open(f"{FW}/marl/gat_encoder.py").read()
    C.note("M82 OR1 LeakyReLU slope 0.2 is the encoder's", "leaky_relu_slope: float = 0.2" in gat
           and "has slope $0.2$ for negative inputs" in C.tex, None)

    # ---------------- campaign design: seeds and episodes per seed, read off the stored runs
    def n_eval_eps(cell, arm, seed):
        p = V.find_eval(cell, arm, seed)
        return V.read(p)["episodes"] if p else None
    import gzip
    tr_eps = {json.loads(l)["episode"] for l in gzip.open(f"{ROOT}/m64/n3_fully_connected/axiom2/seed900/train/omega_log.jsonl.gz", "rt") if '"episode"' in l}
    cur = json.load(open(f"{ROOT}/m64/n3_fully_connected/mappo_tuned/seed900/train/curve.json"))
    have = lambda cell, arm, ss: len(seeds_of(cell, arm, ss))
    C.note("M82 300 training and 50 evaluation episodes per seed", len(cur["episode_mean_reward"]) == 300 and len(tr_eps) == 300
           and n_eval_eps("m64/n3_fully_connected", "axiom2", 900) == 50 and n_eval_eps("m65_scaling/n19_ring", "axiom2", 900) == 50
           and "Every campaign uses 300 training and 50 evaluation episodes per seed" in C.main, None)
    C.note("M82 seed sets of the campaigns", have("m64/n3_fully_connected", "axiom2", range(900, 930)) == 30 and have("m65_reviewer/replication", "axiom2", REP) == 10
           and all(have(f"m65_scaling/n7_{t}", "axiom2", S15) == 15 for t in LAY)
           and all(have(f"m65_scaling/n19_{t}", "axiom2", S30_19) == 30 for t in LAY)
           and have("m73/A_n37_hex", "axiom2", S30_19) == 30 and all(have(f"m73/A_n37_{t}", "axiom2", S15) == 15 for t in ("ring", "fully_connected"))
           and "The three-gNB campaigns use 30 seeds, 900 to 929, with a disjoint replication sample, 1000 to 1009. The scaling campaigns use 15 seeds per layout at seven gNBs, 30 at nineteen, and at thirty-seven 30 on the hex layout and 15 on each other layout." in C.main, None)
    an = open(f"{SC}/m2_correctness_metrics.py").read()
    vf = open(f"{SC}/m66_verify.py").read()
    C.note("M82 bootstrap CIs use 10,000 resamples", "def bootstrap_ci(values, n_boot=10000, alpha=0.05, seed=0):" in an
           and "size=(10000, len(v))" in vf
           and "95\\% bootstrap percentile intervals over 10{,}000 resamples" in C.main, None)


    # ---------------- main-text results that no earlier check pinned to their text
    import glob
    A = {a: seeds_of("m65_reviewer/base", a, S30) for a in ("axiom2", "mappo_tuned")}
    A.update({a: seeds_of("m63_reviewer/base", a, S30) for a in ("heuristic", "single_agent_dqn", "independent_dqn")})
    ra = {a: mean(A[a]) for a in A}
    C.note("M82 Table 4 Env A reward row", f"Env A reward, 3 gNBs & {ra['axiom2']:.2f}, {100 * ra['axiom2'] / ra['heuristic']:.1f}\\% of static rule & {ra['single_agent_dqn']:.2f} & {ra['independent_dqn']:.2f} & {ra['mappo_tuned']:.2f} \\\\" in C.main,
           {k: round(v, 3) for k, v in ra.items()})
    cx = json.load(open(f"{ROOT}/m64/complexity.json")); cx37 = json.load(open(f"{ROOT}/m73/complexity_n37.json"))["37"]
    allc = {n_: cx[n_] for n_ in ("3", "7", "19")}; allc["37"] = cx37
    C.note("M82 Table 4 parameter row", all(allc[n_]["axiom2"]["params_execution"] == 7782 and allc[n_]["mappo"]["params_execution"] == 5122 for n_ in allc)
           and "Parameters at execution & 7,782 at any size & 21,250 to 64,770 & 55,302 to 682,058 & 5,122 \\\\" in C.main, None)
    n7 = {t: {a: seeds_of(f"m64/n7_{t}", a, S15) for a in ARMS} for t in LAY}
    n7p = {a: 100 * float(np.mean([mean(n7[t][a], prio) for t in LAY])) for a in ARMS}
    C.note("M82 Table 4 Env B 7-gNB priority SLA row", "Env B priority SLA, 7 gNBs & " + " & ".join(f"{n7p[a]:.1f}\\%" for a in ARMS) + " \\\\" in C.main,
           {k: round(v, 2) for k, v in n7p.items()})
    def pooled(n_):
        if n_ == 37:
            rows = {a: [r for t, ss in (("hex", S30_19), ("ring", S15), ("fully_connected", S15)) for r in seeds_of(f"m73/A_n37_{t}", a, ss if a == "axiom2" or t == "hex" else []).values()] for a in ARMS}
        else:
            ss = S15 if n_ == 7 else S30_19
            rows = {a: [r for t in LAY for r in seeds_of(f"m65_scaling/n{n_}_{t}", a, ss).values()] for a in ARMS}
        return {a: 100 * float(np.mean([prio(r) for r in v])) for a, v in rows.items()}
    pl = {n_: pooled(n_) for n_ in (7, 19, 37)}
    C.note("M82 abstract and contributions: AXIOM above 93% and every learned baseline below 84% at 7, 19 and 37 gNBs",
           min(pl[n_]["axiom2"] for n_ in pl) > 93 and max(pl[n_][a] for n_ in pl for a in ARMS[1:]) < 84
           and "At 7, 19, and 37 gNBs, AXIOM keeps Ultra-Reliable Low-Latency Communication (URLLC) and Enhanced Mobile Broadband (eMBB) service-level compliance above 93\\%, while every learned baseline stays below 84\\%" in C.main
           and "AXIOM keeps priority-slice compliance above 93\\% at 7, 19, and 37 gNBs, while both DQN baselines and MAPPO stay below 84\\%" in C.main,
           {n_: {a: round(v, 1) for a, v in pl[n_].items()} for n_ in pl})
    f74 = {a: seeds_of("m74/A_n37_hex", a, list(range(6100, 6120))) for a in ARMS}
    fp = {a: 100 * mean(f74[a], prio) for a in ARMS}
    C.note("M82 fresh 37-gNB sentence: AXIOM 95.1% against 34.1% to 58.5%", f"{fp['axiom2']:.1f}" == "95.1" and f"{min(fp[a] for a in ARMS[1:]):.1f}" == "34.1"
           and f"{max(fp[a] for a in ARMS[1:]):.1f}" == "58.5" and all(len(f74[a]) == 20 for a in ARMS)
           and "There AXIOM keeps 95.1\\% priority-slice compliance against 34.1\\% to 58.5\\% for the baselines" in C.main, {k: round(v, 2) for k, v in fp.items()})
    gs = json.load(open("/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures/fig13_gnb_map_summary.json"))["arms"]
    C.note("M82 no baseline closes the 37-gNB mMTC gate below 0.51", round(min(gs[a]["mean_openness"]["mmtc"] for a in ARMS[1:]), 2) == 0.51
           and "No baseline closes the mMTC gate below 0.51" in C.main, {a: gs[a]["mean_openness"] for a in gs})
    h3 = {t: paired(seeds_of(f"m64/n7_{t}", "axiom2_mlp", S15), seeds_of(f"m64/n7_{t}", "axiom2", S15)) for t in ("ring", "hex")}
    C.note("M82 MLP variant wins 10 of 15 seeds on each Env B 7-gNB layout", all(h3[t]["wins"] == 10 for t in h3)
           and "and wins 10 of 15 seeds in each" in C.main, {t: (h3[t]["wins"], round(h3[t]["diff"], 3)) for t in h3})
    sens = {c_: paired(seeds_of(f"m65_reviewer/{c_}", "axiom2", S10), seeds_of(f"m63_reviewer/{c_}", "heuristic", S10)) for c_ in ("load102", "load107", "weights")}
    C.note("M82 AXIOM within 0.13 of the oracle under changed load and weights", max(abs(v["diff"]) for v in sens.values()) <= 0.13
           and "AXIOM stays within 0.13 of the static rule's reward under changed load and slice weights" in C.main
           and "AXIOM stays within 0.13 of the static rule's reward" in C.supp_only, {k: round(v["diff"], 3) for k, v in sens.items()})
    B = {a: seeds_of("m64/n3_fully_connected", a, S30) for a in ARMS + ("rule_static", "rule_accept_all", "rule_local")}
    h1 = V.holm({b: paired(B["axiom2"], B[b])["p"] for b in ("rule_static", "rule_accept_all")})
    pr = V.holm({b: paired(B["axiom2"], B[b], prio)["p"] for b in ARMS[1:]})
    loc = paired(B["rule_local"], B["axiom2"])
    sel = json.load(open(f"{ROOT}/m64/n3_fully_connected/rule_local_selection.json"))["selected"]
    C.note("M82 Env B three-gNB sentences: Holm p<0.0001, tuned rule's 0.2 threshold, 0.420 at p<0.0001",
           max(h1.values()) < 1e-4 and max(pr.values()) < 1e-4 and all(paired(B["axiom2"], B[b], prio)["diff"] > 0 for b in ARMS[1:])
           and sel["tau_e"] == 0.2 and f"{loc['diff']:.3f}" == "0.420" and loc["p"] < 1e-4
           and "Both gaps hold at Holm-adjusted $p<0.0001$" in C.main and "and keeps more priority-slice compliance than each, at Holm-adjusted $p<0.0001$" in C.main
           and "sheds eMBB whenever the URLLC queue passes 0.2" in C.main and "earning 0.420 more than AXIOM at $p<0.0001$" in C.main,
           {"h1": h1, "prio": pr, "loc": loc, "sel": sel})
    w7 = {(t, r_): paired(seeds_of(f"m64/n7_{t}", r_, S15), seeds_of(f"m64/n7_{t}", "axiom2", S15))["wins"] for t in LAY for r_ in ("rule_local", "rule_neighbour")}
    C.note("M82 tuned rules beat AXIOM in all 15 seeds at seven gNBs under every layout", all(v == 15 for v in w7.values())
           and "At seven gNBs the tuned rules beat AXIOM in all 15 seeds under every layout" in C.main, w7)
    def med_train(cell, arm):
        v = [r["train_seconds"] for f_ in glob.glob(f"{ROOT}/{cell}/{arm}_*.json") for r in json.load(open(f_)).values() if isinstance(r, dict) and "train_seconds" in r]
        return round(float(np.median(v)))
    def prim_train(cell, arm):
        fs = [f_ for f_ in glob.glob(f"{ROOT}/{cell}/{arm}_*.json") if re.fullmatch(rf"{arm}_\d+-\d+\.json", os.path.basename(f_))]
        return round(float(np.median([r["train_seconds"] for f_ in fs for r in json.load(open(f_)).values() if isinstance(r, dict) and "train_seconds" in r])))
    rows = {}
    for a, lab in (("axiom2", "AXIOM"), ("single_agent_dqn", "DQN-SA"), ("independent_dqn", "DQN-I"), ("mappo_tuned", "MAPPO")):
        k = "mappo" if a == "mappo_tuned" else a
        par = [allc[n_][k]["params_execution"] for n_ in ("3", "7", "19", "37")]
        sa_ms = json.load(open(f"{ROOT}/m73/complexity_n37.json"))["single_agent_ms_per_step"]   # DQN-SA's latency, measured separately
        lat = " / ".join(f"{(sa_ms[n_] if a == 'single_agent_dqn' else allc[n_][k]['ms_per_step']):.2f}" for n_ in ("3", "7", "19", "37"))
        tr = (prim_train("m64/n3_fully_connected", a), med_train("m65_scaling/n19_ring", a), med_train("m73/A_n37_ring" if a == "axiom2" else "m73/A_n37_hex", a))
        p_ = (f"{par[0]:,} at every size" if len(set(par)) == 1 else " / ".join(f"{x:,}" for x in par))
        rows[a] = f"{lab} & {p_} & {lat} & {tr[0]} / {tr[1]} / {tr[2]} \\\\"
    C.note("M82 complexity table rows recomputed from the measurements", all(r in C.main for r in rows.values()), rows)
    C.note("M82 federation pooled over 30 seeds, ten of them fresh", len(seeds_of("m65_m3", "fl_gat_ctde_sigma0.0", S10)) == 10
           and len(seeds_of("m65_m3_replication", "fl_gat_ctde_sigma0.0", REP)) == 10
           and "Pooled over all 30 federated seeds, ten of them fresh" in C.main, None)


    # ---------------- main-text sentences whose numbers earlier checks computed but did not tie to the text
    for n_, ss, txt in ((7, S15, "At seven gNBs, under every layout, AXIOM keeps {s0} to {s1} percentage points more priority-slice compliance than each baseline and earns {r0} to {r1} more reward per step. All 18 comparisons hold after Holm correction, at adjusted $p\\leq{h}$."),
                        (19, S30_19, "Under every layout AXIOM keeps {s0} to {s1} percentage points more compliance than every baseline and earns {r0} to {r1} more reward per step, winning {w0} to {w1} of 30 seeds. All 18 comparisons hold after Holm correction, at adjusted $p\\leq{h}$.")):
        D = {t: {a: seeds_of(f"m65_scaling/n{n_}_{t}", a, ss) for a in ARMS} for t in LAY}
        tests = {(t, b, m): paired(D[t]["axiom2"], D[t][b], f_) for t in LAY for b in ARMS[1:] for m, f_ in (("s", prio), ("r", lambda r: r["reward"]))}
        hh = V.holm({k: v["p"] for k, v in tests.items()})
        sd = [100 * v["diff"] for k, v in tests.items() if k[2] == "s"]; rd = [v["diff"] for k, v in tests.items() if k[2] == "r"]
        ws = [v["wins"] for k, v in tests.items() if k[2] == "s"]
        rf = "{:.2f}" if n_ == 7 else "{:.1f}"
        h = "0.011" if n_ == 7 else "0.0001"
        t_ = txt.format(s0=f"{min(sd):.1f}", s1=f"{max(sd):.1f}", r0=rf.format(min(rd)), r1=rf.format(max(rd)), w0=min(ws), w1=max(ws), h=h)
        C.note(f"M82 {n_}-gNB scaling sentence recomputed", t_ in C.main and max(hh.values()) <= float(h) and all(v["diff"] > 0 for v in tests.values()), t_)
    r37 = {t: {a: seeds_of(f"m73/A_n37_{t}", a, S30_19 if t == "hex" else S15) for a in ARMS} for t in LAY}
    for t in ("ring", "fully_connected"):       # the baselines never read the layout and ran once, on the hex seeds
        for b in ARMS[1:]:
            r37[t][b] = {s_: v for s_, v in r37["hex"][b].items() if s_ in S15}
    t37 = {(t, b, m): paired(r37[t]["axiom2"], r37[t][b], f_) for t in LAY for b in ARMS[1:] for m, f_ in (("s", prio), ("r", lambda r: r["reward"]))}
    h37 = V.holm({k: v["p"] for k, v in t37.items()})
    C.note("M82 37-gNB comparisons hold after Holm correction at p<0.01", max(h37.values()) < 0.01 and all(v["diff"] > 0 for v in t37.values())
           and "Here all 18 comparisons hold after Holm correction within their pre-registered families, at adjusted $p<0.01$" in C.main
           and "A pre-registered replication on 20 fresh seeds confirms the result" in C.main, round(max(h37.values()), 5))
    n7r = {(t, b, m): paired(n7[t]["axiom2"], n7[t][b], f_) for t in LAY for b in ("independent_dqn", "single_agent_dqn", "mappo_tuned", "rule_local", "rule_neighbour")
           for m, f_ in (("reward", lambda r: r["reward"]), ("prio", prio))
           for _ in [n7[t].setdefault(b, seeds_of(f"m64/n7_{t}", b, S15))]}
    h7 = V.holm({k: v["p"] for k, v in n7r.items()})
    C.note("M82 Env B 7-gNB ring: AXIOM below DQN-SA in compliance at Holm p=0.011", round(h7[("ring", "single_agent_dqn", "prio")], 3) == 0.011
           and n7r[("ring", "single_agent_dqn", "prio")]["diff"] < 0
           and "On the ring layout AXIOM keeps less compliance than DQN-SA, at Holm-adjusted $p=0.011$" in C.main, h7[("ring", "single_agent_dqn", "prio")])
    sel70 = json.load(open(f"{ROOT}/m70/R3_pilot/selection.json"))
    C.note("M82 the MAPPO tuning grid has 24 configurations in each environment", len(sel70["A"]["grid"]) == 24 and len(sel70["B"]["grid"]) == 24
           and "A 24-configuration MAPPO grid" in C.main and "A grid of 24 MAPPO configurations" in C.tex, None)
    m74a = json.load(open(f"{ROOT}/m74/analysis.json")); m80a = json.load(open(f"{ROOT}/m80/analysis.json"))
    d80 = [c_ for c_ in m80a["criteria"] if re.match(r"D\d ", c_["label"])]
    C.note("M82 fifth and sixth fresh-seed runs: 3 of 3 and 4 of 4 checks held", (m74a["n_judged"], m74a["n_fail"]) == (3, 0)
           and len(d80) == 4 and all(c_["holds"] for c_ in d80)
           and "A fifth fresh-seed run held all three of its checks at thirty-seven gNBs on 20 seeds. A sixth held all four in Env B at nineteen gNBs on 15 seeds" in C.main, None)
    mb = json.load(open(f"{ROOT}/m66b_analysis.json")); mc = json.load(open(f"{ROOT}/m66c_analysis.json"))
    bounds = [c_["label"] for c_ in mb["criteria"] + mc["criteria"] if "<= 80%" in c_["label"]]
    sizes = {"m66_fresh/A_n3": 20, "m66_fresh/A_n19_ring": 15, "m66_fresh/B_n7_ring": 10, "m66b_fresh/A_n7_ring": 10, "m66d_fresh/D1_A_n3": 40}
    seen = {c_: len(seeds_of(c_, "axiom2", range(3000, 4040))) for c_ in sizes}
    C.note("M82 fresh-seed runs used 10 to 40 seeds per setting and an 80% baseline bound", seen == sizes and len(bounds) > 0
           and "retrained every policy on fresh seeds, 10 to 40 per setting" in C.main and "above the 80\\% bound we had set" in C.main, (seen, bounds[:2]))
    rt = {sh: paired(V_shift("n3", sh, "axiom2"), V_shift("n3", sh, "rule_retuned")) for sh in ("load_1.10", "load_1.15", "load_1.20")}
    C.note("M82 a re-tuned rule ties AXIOM up to 115% load and beats it at 120%", all(rt[k]["p"] >= 0.05 for k in ("load_1.10", "load_1.15"))
           and rt["load_1.20"]["diff"] < 0 and rt["load_1.20"]["p"] < 0.05
           and "A re-tuned rule ties AXIOM up to 115\\% load and beats it at 120\\%" in C.main
           and f"Against it AXIOM trails by {-rt['load_1.10']['diff']:.2f} and {-rt['load_1.15']['diff']:.2f} per step at 110\\% and 115\\% load, which is not significant, and by {-rt['load_1.20']['diff']:.2f} at 120\\% load" in C.tex,
           {k: (round(v["diff"], 3), round(v["p"], 4)) for k, v in rt.items()})


    # ---------------- Online Resource 1: design and process statements against the code, configs and records
    DOCS = "/home/kmanojp/oranslice_rig/docs"
    rep = open(f"{DOCS}/PAPER5_M66_verification_report.md").read()
    v1 = rep[rep.index("## V1 reproducibility"):rep.index("### Single-agent DQN root cause")]
    rows_v1 = [l for l in v1.splitlines() if l.startswith("| ") and not l.startswith("| Cell") and "extra check" not in l]
    n_set = sum(2 if "rule_static, rule_local" in l else 1 for l in rows_v1)
    C.note("M82 OR1 eleven rerun settings and the oracle on 30 seeds", n_set == 11 and any("rule_static vs stored oracle" in l and "900-929" in l for l in v1.splitlines())
           and "We reran eleven reported settings on their original seeds in fresh processes" in C.tex and "as did the Env A static rule, which sheds every mMTC request, on all 30 seeds" in C.tex, n_set)
    m62 = open(f"{SC}/m62_reviewer_experiments.py").read(); runsrc = open(f"{SC}/m64_run.py").read()
    flp = open(f"{FW}/marl/fl_ctde_policy.py").read(); m3r = open(f"{SC}/m3_run_experiment.py").read()
    C.note("M82 OR1 sensitivity, federated and wide-encoder settings match the code",
           'sb.LOAD_FACTOR = 1.02 if condition == "load102" else 1.07' in m62 and 'slices["embb"].priority_weight = 2.5' in m62 and "0.6" in m62[m62.index('if condition == "weights"'):m62.index('if condition == "weights"') + 400]
           and "gat_hidden_dim=32, gat_out_dim=32, q_hidden_dim=64" in runsrc
           and "local_steps_per_round: int = 50" in flp and "dp_clip_norm: float = 1.0" in flp and "dp_clip_norm=1.0, local_steps_per_round=50" in m3r
           and all(len(seeds_of(f"m65_reviewer/{c_}", "axiom2", S10)) == 10 for c_ in ("load102", "load107", "weights"))
           and "on 10 seeds at 102\\% and 107\\% of the nominal load. It also changes the slice weights, lowering eMBB from 3.5 to 2.5 and raising mMTC from 0.3 to 0.6" in C.tex
           and "at learning rates of $3{\\times}10^{-4}$ and $3{\\times}10^{-3}$ and with an encoder twice as wide" in C.tex
           and "The federated campaign runs in Env A on seeds 900 to 909, with noise multipliers $\\sigma \\in \\{0, 0.5, 1, 2, 4\\}$ and a replication on seeds 1000 to 1009" in C.tex
           and "Each round runs 50 local steps of federated averaging (FedAvg) with a gradient-clip norm of $1.0$" in C.tex, None)
    scr = open(f"{SC}/m63_validation_screen.py").read()
    C.note("M82 OR1 validation screen: five greedy episodes, 90% of blocks on mMTC", 'ap.add_argument("--episodes", type=int, default=5)' in scr and "MIN_MMTC_SHARE = 0.9" in scr
           and "Each plays five greedy episodes on its own training stream and fails if it blocks no request or if fewer than 90\\% of its blocks target mMTC" in C.tex, None)
    m64p = open(f"{DOCS}/PAPER5_M64_preregistration.md").read(); m63p = open(f"{DOCS}/PAPER5_M63_preregistration.md").read()
    m72p = open(f"{DOCS}/PAPER5_M72_preregistration.md").read(); m2d = open(f"{DOCS}/PAPER5_M2_gat_ctde.md").read()
    C.note("M82 OR1 process records: pilot seeds, M63 timing, probe seeds, earlier mixer's diverging loss",
           "pilot seeds 2000 to 2009" in m64p and "using rules only" in m64p and "after the M63 rerun was launched (14:28) and before any M63 result was read" in m63p
           and "900-904 were used by the probe" in m72p and "mean loss ~76 in the first" in m2d and "~409 in the last 20%" in m2d
           and "all chosen on pilot seeds 2000 to 2009" in C.tex and "The M63 plan was committed one minute after that rerun was launched" in C.tex
           and "its mean training loss diverged from about 76 to about 409" in C.tex, None)
    dis = open(f"{SC}/m4_run_experiment.py").read()
    C.note("M82 OR1 disruption windows and spike multipliers", "DROPOUT_CHURN_DURATION_FRAC = {1: 0.10, 2: 0.30, 3: 0.60}" in dis and "SPIKE_MULTIPLIER = {1: 2.0, 2: 4.0, 3: 8.0}" in dis
           and "Dropout and churn windows last 10\\%, 30\\%, or 60\\% of the episode. Spikes multiply arrivals by 2, 4, or 8." in C.tex, None)
    c37 = yaml.safe_load(open("/home/kmanojp/oranslice_rig/experiments/configs/saclb_offline_dqn_n37.yaml"))
    C.note("M82 OR1 thirty-seven-gNB arrivals", c37["arrivals"]["synthetic_arrivals_per_step"] == 37 and c37["arrivals"]["max_pending_per_step"] == 148
           and "with 37 arrivals per step and at most 148 pending requests" in C.tex, None)
    m76p = open(f"{DOCS}/PAPER5_M76_preregistration.md").read()
    sel_grid = json.load(open(f"{ROOT}/m64/n3_fully_connected/rule_local_selection.json"))["grid"]
    C.note("M82 OR1 uneven load range and the 95 local rules", "U[0.75, 1.25] per seed" in m76p and "M76_HETERO" in open(f"{SC}/m76_run.py").read()
           and len(sel_grid) == 95 and "drawn between 75\\% and 125\\% per seed" in C.tex and "among all 95 local rules" in C.tex, len(sel_grid))


    # ---------------- Online Resource 1: result sentences and table cells not yet tied to their text
    rng = np.random.default_rng(12345)
    def ci(vals):
        v = np.asarray(vals); bm = v[rng.integers(0, len(v), size=(10000, len(v)))].mean(axis=1)
        return np.percentile(bm, 2.5), np.percentile(bm, 97.5)
    def ci_ok(vals, lo, hi, tol=0.05):
        a_, b_ = ci(vals); return abs(a_ - lo) <= tol and abs(b_ - hi) <= tol
    fa = {k: seeds_of("m66_fresh/A_n3", k, list(range(3000, 3020))) for k in ("axiom2", "single_agent_dqn")}
    d1 = {k: seeds_of("m66d_fresh/D1_A_n3", k, list(range(4000, 4040))) for k in ("axiom2", "single_agent_dqn")}
    g20, g40 = paired(fa["axiom2"], fa["single_agent_dqn"]), paired(d1["axiom2"], d1["single_agent_dqn"])
    C.note("M82 OR1 small DQN-SA margins on 20 and 40 new seeds", f"{g20['diff']:.3f}" == "-0.021" and f"{g40['diff']:.3f}" == "0.159" and (g20["n"], g40["n"]) == (20, 40)
           and "at margins of $-0.021$ and $0.159$ reward per step on 20 and 40 new seeds" in C.tex and "seeds from 3000 onwards" in C.tex, (g20, g40))
    crit = mb["criteria"] + mc["criteria"]
    hi_b = [float(re.search(r"([\d.]+)%", c_["detail"]).group(1)) for c_ in crit if "<= 80%" in c_["label"] and re.search(r"([\d.]+)%", c_["detail"])]
    C.note("M82 OR1 baselines up to 83.3% at seven gNBs, above the 80% bound", f"{max(hi_b):.1f}" == "83.3"
           and "kept up to 83.3\\% priority-slice compliance, above the 80\\% bound we had set" in C.tex, hi_b)
    m19a, m19m = seeds_of("m65_scaling/n19_ring", "axiom2", range(900, 912)), seeds_of("m65_scaling_mlp/n19_ring", "axiom2_mlp", range(900, 912))
    t19 = paired(m19a, m19m)
    b3 = paired(seeds_of("m64/n3_fully_connected", "axiom2_mlp", S30), seeds_of("m64/n3_fully_connected", "axiom2", S30))
    f7 = paired(seeds_of("m66_fresh/B_n7_ring", "axiom2_mlp", list(range(3000, 3010))), seeds_of("m66_fresh/B_n7_ring", "axiom2", list(range(3000, 3010))))
    C.note("M82 OR1 MLP variant: 0.31 at 19 gNBs with 7 of 12 tied, 0.116 in 17 of 30, fresh 1.38 in 9 of 10 at p=0.006",
           f"{t19['diff']:.2f}" == "0.31" and t19["ties"] == 7 and t19["n"] == 12 and f"{b3['diff']:.3f}" == "0.116" and b3["wins"] == 17 and f"{b3['p']:.2f}" == "0.45"
           and f"{f7['diff']:.2f}" == "1.38" and f7["wins"] == 9 and f"{f7['p']:.3f}" == "0.006"
           and "0.31 more at nineteen gNBs on the ring layout, with 7 of 12 seeds tied" in C.tex and "0.116 per step at three gNBs in 17 of 30 seeds at $p=0.45$" in C.tex
           and "it led by 1.38 reward per step, in 9 of 10 seeds at $p=0.006$" in C.tex, (t19, b3, f7))
    brep = {a: seeds_of("m64/n3_replication", a, REP) for a in ARMS}
    wr = [paired(brep["axiom2"], brep[b])["wins"] for b in ARMS[1:]]
    C.note("M82 OR1 Env B replication: AXIOM wins 7 or 8 of 10 against each", sorted(set(wr)) in ([7, 8], [7], [8])
           and "with AXIOM winning 7 or 8 of 10 seeds against each" in C.tex, wr)
    lr4 = {k: seeds_of("m63_reviewer/base", k, S30) for k in ("single_agent_dqn_lr1e4", "independent_dqn_lr1e4")}
    rs, ri = [x["reward"] for x in lr4["single_agent_dqn_lr1e4"].values()], [x["reward"] for x in lr4["independent_dqn_lr1e4"].values()]
    C.note("M82 OR1 DQN baselines at learning rate 1e-4", f"{np.mean(rs):.3f}" == "11.477" and f"{np.mean(ri):.3f}" == "11.119"
           and ci_ok(rs, 10.61, 12.09) and ci_ok(ri, 10.73, 11.50)
           and "falling to 11.477 [10.61, 12.09] and 11.119 [10.73, 11.50] reward per step in Env A at three gNBs" in C.tex, (np.mean(rs), ci(rs), np.mean(ri), ci(ri)))
    C.note("M82 OR1 roughly 360 per-round updates", round(17969 / 50) == 359 and "Each client takes 17{,}969 noisy steps over its training run" in C.tex
           and "the roughly 360 per-round model updates" in C.tex, 17969 / 50)
    m4s = json.load(open(f"{ROOT}/m65_m4/m4_summary.json"))["cells"]
    sp = {a: float(np.mean([m4s[f"{a}|spike|{v}"]["precision_mean"] for v in (1, 2, 3)])) for a in ("gat_ctde", "single_agent_dqn", "independent_dqn")}
    C.note("M82 OR1 spike precision 0.98, 1.00, about 0.95", (f"{sp['gat_ctde']:.2f}", f"{sp['single_agent_dqn']:.2f}") == ("0.98", "1.00") and abs(sp["independent_dqn"] - 0.95) < 0.01
           and "with block precision at 0.98, against 1.00 for DQN-SA and about 0.95 for DQN-I" in C.tex, sp)
    def slices(n_, a):
        if n_ == 37:
            rows = [r for t, ss in (("hex", S30_19), ("ring", S15), ("fully_connected", S15)) for r in seeds_of(f"m73/A_n37_{t}", a, ss).values()]
        else:
            rows = [r for t in LAY for r in seeds_of(f"m65_scaling/n{n_}_{t}", a, S15 if n_ == 7 else S30_19).values()]
        return tuple(f"{100 * np.mean([r['sla'][k] for r in rows]):.1f}" for k in ("urllc", "embb"))
    s7 = {a: slices(7, a) for a in ARMS}; s19, s37 = slices(19, "axiom2"), slices(37, "axiom2")
    t_ = (f"At seven gNBs AXIOM keeps URLLC and eMBB at {s7['axiom2'][0]}\\% and {s7['axiom2'][1]}\\%, against {s7['single_agent_dqn'][0]}\\% and {s7['single_agent_dqn'][1]}\\% for DQN-SA, "
          f"{s7['independent_dqn'][0]}\\% and {s7['independent_dqn'][1]}\\% for DQN-I, and {s7['mappo_tuned'][0]}\\% and {s7['mappo_tuned'][1]}\\% for MAPPO. "
          f"At nineteen gNBs it keeps them at {s19[0]}\\% and {s19[1]}\\%, and at thirty-seven at {s37[0]}\\% and {s37[1]}\\%.")
    C.note("M82 OR1 per-slice compliance at 7, 19 and 37 gNBs", t_ in C.tex, t_)
    for cell, ss, n_lab in (("m73/A_n37_hex", S30_19, "30"), ("m74/A_n37_hex", list(range(6100, 6120)), "20")):
        st = seeds_of(cell, "rule_static", ss)
        row = (f"Static rule & {n_lab} & {100 * mean(st, lambda r: r['sla']['urllc']):.1f}\\% & {100 * mean(st, lambda r: r['sla']['embb']):.1f}\\% & "
               f"{100 * mean(st, prio):.2f}\\% & {mean(st):.2f} & {sum(r['collapsed'] for r in st.values())} \\\\")
        C.note(f"M82 OR1 Table S2 static-rule row, {cell}", row in C.tex, row)
    nc = [100 * float(np.mean([prio(r) for r in seeds_of(f"m73/A_n37_{t}", "axiom2", ss).values() if not r["collapsed"]]))
          for t, ss in (("hex", S30_19), ("ring", S15), ("fully_connected", S15))]
    h1d = lambda x: str(Decimal(str(round(x, 9))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))   # 96.85 -> 96.9
    C.note("M82 OR1 AXIOM's non-collapsed 37-gNB runs keep 96.9% to 98.1% under each layout", (h1d(min(nc)), h1d(max(nc))) == ("96.9", "98.1")
           and "while its other runs keep 96.9\\% to 98.1\\% on average under each layout" in C.tex, nc)
    f37 = {(b, m): paired(f74["axiom2"], f74[b], fn) for b in ARMS[1:] for m, fn in (("r", lambda r: r["reward"]), ("p", prio))}
    h_f37 = V.holm({k: v["p"] for k, v in f37.items()})
    C.note("M82 OR1 fresh 37 gNBs: 18 to 19 of 20 wins, Holm p<0.001", (min(v["wins"] for v in f37.values()), max(v["wins"] for v in f37.values())) == (18, 19)
           and max(h_f37.values()) < 0.001 and "It wins 18 to 19 of 20 seeds in every comparison, all at Holm-adjusted $p<0.001$" in C.tex, {k: v["wins"] for k, v in f37.items()})
    g75 = json.load(open(f"{ROOT}/m75/C_selection.json"))
    grid_keys = set(k for v in g75.values() if isinstance(v, dict) for k in v.get("grid", {}))
    lrs = sorted({float(k.split(",")[0]) for k in grid_keys}); bss = sorted({int(k.split(",")[1]) for k in grid_keys})
    C.note("M82 OR1 tuned DQN grid: learning rates 1e-4 to 1e-3, minibatches 16 and 64", min(lrs) == 1e-4 and max(lrs) == 1e-3 and bss == [16, 64]
           and "over learning rates from $10^{-4}$ to $10^{-3}$ and minibatches of 16 and 64" in C.tex, (lrs, bss))
    def shp(sh):
        t = paired(V_shift("n3", sh, "axiom2"), V_shift("n3", sh, "rule_local")); return t
    fmt_p = lambda p: f"{p:.2g}" if p >= 1e-3 else f"{p:.2g}".replace("e-0", "e-0")
    ptxt = {"load_0.80": "80\\% load", "nominal": "nominal", "load_1.05": "105\\% load", "load_1.10": "110\\% load", "load_1.15": "115\\% load",
            "load_1.20": "120\\% load", "coupling_0.30": "coupling 0.30", "amplitude_0.50": "load swing 0.50"}
    bad = []
    for sh, lab in ptxt.items():
        t = shp(sh)
        if not t["n"]:
            bad.append((sh, "no data")); continue
        line = [l for l in C.tex.splitlines() if l.startswith(lab + " & ")]
        if not line or f"& {t['wins']}/{t['losses']} & " not in line[0] or not np.isclose(float(line[0].split("&")[-1].strip(" \\\\")), t["p"], rtol=0.06):
            bad.append((sh, t["wins"], t["losses"], t["p"], line[:1]))
    C.note("M82 OR1 Table S5 wins, losses and Wilcoxon p", not bad, bad)


    # ---------------- Online Resource 1: the last sentences, reuse of M63 results, and the old simulator
    reuse = {}
    for n_, ss in ((7, S15), (19, S30_19)):
        for a in ("single_agent_dqn", "independent_dqn"):
            for t in LAY:
                new, old = seeds_of(f"m65_scaling/n{n_}_{t}", a, ss), seeds_of(f"m63_scaling/n{n_}_{t}", a, ss)
                reuse[(n_, a, t)] = (sum(abs(new[s_]["reward"] - old[s_]["reward"]) < 1e-9 for s_ in new if s_ in old), len(new))
    C.note("M82 OR1 the main campaign reuses M63 baselines at seven gNBs and for 15 of the 30 seeds at nineteen",
           all(v == (15, 15) for k, v in reuse.items() if k[0] == 7) and all(v == (15, 30) for k, v in reuse.items() if k[0] == 19)
           and "seven gNBs, and 15 of the 30 seeds at nineteen gNBs" in C.tex, reuse)
    n7r_ = {t: {a: seeds_of(f"m64/n7_{t}", a, S15) for a in ("axiom2", "rule_local", "rule_neighbour", "rule_static")} for t in LAY}
    rl = [mean(n7r_[t][a]) for t in LAY for a in ("rule_local", "rule_neighbour")]; ax = [mean(n7r_[t]["axiom2"]) for t in LAY]
    st = float(np.mean([mean(n7r_[t]["rule_static"]) for t in LAY]))
    C.note("M82 OR1 seven gNBs: tuned rules 26.5 to 27.3, AXIOM 23.4 to 23.6, static rule 23.6",
           (f"{min(rl):.1f}", f"{max(rl):.1f}", f"{min(ax):.1f}", f"{max(ax):.1f}", f"{st:.1f}") == ("26.5", "27.3", "23.4", "23.6", "23.6")
           and "the tuned rules earn 26.5 to 27.3 per step and beat AXIOM in all 15 seeds under every layout, while AXIOM earns 23.4 to 23.6, no more than the static rule's 23.6" in C.tex,
           (rl, ax, st))
    ring = n7r_["ring"]["axiom2"]
    mo = sum(1 for r in ring.values() if r["blocks"] and r["mmtc"] == r["blocks"])
    C.note("M82 OR1 Table S7 AXIOM 300-episode row", f"AXIOM, 300 episodes, as reported & {mean(ring) / 7:.2f} & {100 * mean(ring, prio):.1f}\\% & {mo} \\\\" in C.tex,
           (mean(ring) / 7, 100 * mean(ring, prio), mo))
    b1 = [c_ for c_ in m80a["criteria"] if c_["label"].startswith("B1 ")]
    C.note("M82 OR1 nineteen gNBs: seven of eight seeds still shed only mMTC after 900 episodes", len(b1) == 1 and b1[0]["detail"].startswith("7 vs 8")
           and "After 900 episodes seven of eight seeds still shed only mMTC, against all eight after 300" in C.tex, b1[0]["detail"] if b1 else None)
    sel7 = json.load(open(f"{ROOT}/m64/n7_ring/rule_local_selection.json"))["selected"]
    C.note("M82 OR1 the tuned rule's step at 0.2 at seven gNBs", sel7["tau_e"] == 0.2 and "a softer form of the tuned rule's step at 0.2" in C.tex, sel7)
    C.note("M82 OR1 fifteen fresh seeds 7000 to 7014 at nineteen gNBs", len(seeds_of("m80/D_envB_n19_hex_fresh", "axiom2", range(7000, 7015))) == 15
           and "On 15 fresh seeds, 7000 to 7014, in Env B at nineteen gNBs" in C.tex, None)
    g73 = json.load(open(f"{ROOT}/m70/R3_pilot/selection.json"))["A"]["selected"]
    C.note("M82 OR1 the grid-selected MAPPO at 37 gNBs trains for 900 episodes", "900" in str(g73)
           and "We also ran MAPPO with the configuration that the main paper's grid selected for Env A, trained for 900 episodes" in C.tex, g73)
    old = json.load(open(f"{ROOT}/m78_oldsim/summary.json")) if os.path.exists(f"{ROOT}/m78_oldsim/summary.json") else None
    aa = (old or {}).get("accept_all", {})
    C.note("M82 OR1 old simulator: accept-all kept URLLC and eMBB at 100% on the 30 held-out seeds", len(aa) == 30
           and all(v["sla"]["urllc"] == 1.0 and v["sla"]["embb"] == 1.0 for v in aa.values())
           and "kept URLLC and eMBB at 100\\% SLA compliance" in C.tex and "Over the same 30 held-out seeds" in C.tex, old)
    m77s = open(f"{SC}/m77_kpi.py").read() if os.path.exists(f"{SC}/m77_kpi.py") else ""
    C.note("M82 OR1 delay definition: mean backlog over mean served PRBs, 95th percentile over steps and gNBs",
           '"delay_steps": float(bl.mean() / sv.mean())' in m77s and '"delay_steps_p95": float(np.percentile(ratio, 95))' in m77s
           and "the mean backlog over the mean served PRBs in 5 s control periods, with the 95th percentile over steps and gNBs" in C.tex, None)


    # ---------------- Online Resource 1, Section S9: the reproducibility figure against this machine and its packages
    import platform, scipy, matplotlib
    cpu = [l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")]
    osr = open("/etc/os-release").read()
    spec = open("/home/kmanojp/oranslice_rig/PAPER5_SYSTEM_SPECS.md").read()
    C.note("M82 OR1 Fig. S7 hardware and software match this machine and its packages",
           cpu and "i5-1135G7" in cpu[0] and len(cpu) == 8 and 'VERSION_ID="24.04"' in osr and not torch.cuda.is_available()
           and platform.python_version() == "3.12.3" and torch.__version__.split("+")[0] == "2.13.0" and np.__version__ == "2.5.1"
           and scipy.__version__ == "1.18.0" and matplotlib.__version__ == "3.11.0" and yaml.__version__ == "6.0.3"
           and "7.4 GiB total" in spec and "OAI 2024.w28" in spec and "17 containers" in spec and "v1.5.2" in spec
           and "One laptop, Intel Core i5-1135G7, 4 cores and 8 threads" in C.tex and "8 GB of memory, 7.4 GiB usable" in C.tex
           and "Python 3.12.3, PyTorch 2.13.0 on the CPU" in C.tex and "NumPy 2.5.1, SciPy 1.18.0, Matplotlib 3.11.0, PyYAML 6.0.3" in C.tex
           and "OAI gNB, ORANSlice fork on OAI 2024.w28, rfsim radio" in C.tex and "protobuf-c 1.5.2" in C.tex,
           (cpu[:1], platform.python_version(), torch.__version__, np.__version__, scipy.__version__, matplotlib.__version__, yaml.__version__))
    for f_ in ("m64_run.py", "m73_run.py", "m72_shift.py", "m77_kpi.py", "m65_rebuild_all.sh", "m66_verify.py", "m66_ci_recompute.py"):
        assert os.path.exists(f"{SC}/{f_}"), f_

    LG = "/home/kmanojp/oranslice_rig/experiments/logs/m64/full"
    runcmd, chain = open(f"{LG}/run_cmd.sh").read(), open(f"{LG}/chain.sh").read()
    rrs, lea = open(f"{SC}/restart_ran_stack.sh").read(), open(f"{SC}/run_live_eval_arm.py").read()
    ex = lambda p: os.path.exists(p)
    C.note("M82 OR1 Fig. S7 step details match the launch records, scripts and specification",
           "export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 M63_BACKLOG_RESET=1 M64_AXIOM_V2=1" in runcmd
           and "cd /home/kmanojp/oranslice_rig/framework" in runcmd and "xargs -0 -P 5" in chain
           and "5000 + seed, 50 episodes" in open(f"{SC}/m77_kpi.py").read() and "23 GiB" in spec
           and (prim_train("m64/n3_fully_connected", "mappo_tuned"), med_train("m73/A_n37_hex", "independent_dqn")) == (73, 2088)
           and "ORANSlice.gnb.sa.band78.fr1.106PRB.usrpx310.conf --sa --rfsim" in rrs and "ip netns exec ue2ns ./nr-uesoftmodem" in rrs
           and "docker_open5gs/5g-sa-deploy-slicing.yaml" in spec and "listen port 6600, gNB-side port 6655" in spec and "iperf3" in spec and "Drive iperf3 UDP traffic on every slice" in C.tex
           and "health-checking the rig before every batch" in lea and "full stack restart if unhealthy" in lea
           and 'ap.add_argument("mode", choices=["eval", "retune"])' in open(f"{SC}/m72_shift.py").read()
           and all(ex(f"{SC}/{x}") for x in ("m62_shared_env.py", "m3_run_experiment.py", "m4_run_experiment.py", "m70_run.py", "m75_run.py", "m76_run.py",
                                             "m63_validation_screen.py", "m81_decision_probe.py", "m64_analysis.py", "m62_analysis.py", "m66_v1v2.py", "m82_audit.py"))
           and ex("/home/kmanojp/oranslice_rig/experiments/plots/paper5_cvd_check.py")
           and "Every job runs from \\texttt{framework/} on one thread" in C.tex and "the main campaigns ran five jobs at a time" in C.tex
           and "evaluated for 50 episodes on the held-out stream 5000 plus the seed" in C.tex and "8 GB of memory, 7.4 GiB usable, with 23 GiB of swap" in C.tex
           and "The median training time per seed runs from 73 s to 2{,}088 s" in C.tex
           and "the replication 1000 to 1009, the pilots 2000 to 2009, and the fresh seeds 3000 onwards" in C.tex
           and "with noise multipliers 0, 0.5, 1, 2, and 4" in C.tex and "on ports 6600 and 6655" in C.tex, None)
    C.note("M82 OR1 Fig. S7 names scripts that exist and do what it says", os.path.exists("/home/kmanojp/oranslice_rig/experiments/plots/paper5_regen_wpc_figures.sh")
           and os.path.exists("/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/make_submission.py")
           and all(x in inspect.getsource(m64_run.main) for x in ('"--env"', '"--n"', '"--topology"', '"--arm"', '"--seeds"', '"--train-episodes", type=int, default=300'))
           and "N37_CONFIG" in open(f"{SC}/m73_run.py").read(), None)


class _Dry:
    """Prints each check, for running this audit on its own."""
    def __init__(self, tex, main):
        self.tex, self.main, self.texr, self.rows = tex, main, tex, []

    def claim(self, label, snippet, value, fmt, tol=None):
        quoted = fmt.format(value) if value is not None else None
        ok = snippet in self.tex and quoted is not None and quoted in snippet
        self.rows.append(ok); print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  value={quoted} in_text={snippet in self.tex}"))

    def note(self, label, ok, detail):
        self.rows.append(bool(ok)); print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  detail={detail}"))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--tex", required=True); ap.add_argument("--supp", required=True); a = ap.parse_args()
    m = open(a.tex).read(); C_ = _Dry(m + "\n" + open(a.supp).read(), m)
    run(C_)
    print(f"{sum(C_.rows)} of {len(C_.rows)} M82 checks pass")
