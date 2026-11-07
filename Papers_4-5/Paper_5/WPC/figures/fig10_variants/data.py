"""Every value plotted by the Fig. 10 variants, computed from stored per-seed results. Nothing is typed in.

Logs are read with the independent reader of experiments/scripts/m66_verify.py (seeds_of, prio), the same reader
the paper's verifier uses. Confidence intervals are 95% percentile bootstraps of the mean over seeds
(scipy.stats.bootstrap, 10,000 resamples, numpy default_rng(0)). Output: data.json next to this file, with N and the
source of every value. Run: python data.py   (the figure scripts call load(), which builds data.json if missing).
"""
import glob
import json
import os
import sys

import numpy as np
from scipy.stats import bootstrap

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data.json")
ROOT = "/home/kmanojp/oranslice_rig/experiments/results"
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/plots")

LEARNED = ("axiom2", "mappo_tuned", "single_agent_dqn", "independent_dqn")
LOADS = ("load_1.10", "load_1.15", "load_1.20")


def ci(vals):
    v = np.asarray(list(vals), float)
    if len(v) < 2 or np.all(v == v[0]):
        return [float(v.mean()), float(v.mean())]
    r = bootstrap((v,), np.mean, n_resamples=10000, confidence_level=0.95, method="percentile",
                  random_state=np.random.default_rng(0))
    return [float(r.confidence_interval.low), float(r.confidence_interval.high)]


def summ(per_seed, source):
    v = list(per_seed.values())
    return {"mean": float(np.mean(v)), "ci95": ci(v), "n": len(v), "per_seed": {str(k): float(x) for k, x in per_seed.items()},
            "source": source}


def build():
    from m66_verify import S15, S30, S30_19, holm, paired, prio, seeds_of
    from paper5_fig_superiority import shift_row
    d = {"notes": {}, "sources": {}}

    # ---- parameters at execution (deterministic counts, no seeds)
    cx = json.load(open(f"{ROOT}/m64/complexity.json")); c37 = json.load(open(f"{ROOT}/m73/complexity_n37.json"))["37"]
    key = {"axiom2": "axiom2", "mappo_tuned": "mappo", "single_agent_dqn": "single_agent_dqn", "independent_dqn": "independent_dqn"}
    d["params"] = {a: {str(n): int(cx[str(n)][k]["params_execution"]) for n in (3, 7, 19)} | {"37": int(c37[k]["params_execution"])}
                   for a, k in key.items()}
    d["sources"]["params"] = "m64/complexity.json [n][arm].params_execution (3, 7, 19 gNBs); m73/complexity_n37.json ['37'][arm].params_execution"

    # ---- Env A, 37 gNBs: priority-slice compliance (mean of URLLC and eMBB SLA, %), per seed
    P = lambda r: 100 * prio(r)
    ax = {}
    for t, ss in (("hex", S30_19), ("ring", S15), ("fully_connected", S15)):
        ax.update({f"{t}:{s}": P(r) for s, r in seeds_of(f"m73/A_n37_{t}", "axiom2", ss).items()})
    sla = {"axiom2": summ(ax, "m73/A_n37_{hex 30 seeds, ring 15, fully_connected 15}/axiom2 eval logs, pooled as in the paper")}
    for a in ("mappo_tuned", "single_agent_dqn", "independent_dqn", "rule_static"):
        sla[a] = summ({s: P(r) for s, r in seeds_of("m73/A_n37_hex", a, S30_19).items()}, f"m73/A_n37_hex/{a} eval logs, 30 seeds")
    sla["axiom2_hex"] = summ({s: P(r) for s, r in seeds_of("m73/A_n37_hex", "axiom2", S30_19).items()}, "m73/A_n37_hex/axiom2, hex only")
    m97 = os.path.exists(f"{ROOT}/m97/A_n37_hex/rule_local_selection.json")
    if m97:
        sla["rule_local"] = summ({s: P(r) for s, r in seeds_of("m97/A_n37_hex", "rule_local", S30_19).items()},
                                 "m97/A_n37_hex/rule_local eval logs (M97, prereg 33522657), 30 seeds")
        d["tuned_rule_A37"] = json.load(open(f"{ROOT}/m97/A_n37_hex/rule_local_selection.json"))["selected"]
    d["sla37"] = sla

    # ---- Env A, 37 gNBs hex: mean URLLC backlog delay (backlog PRBs / served PRBs, in control periods), M77 recorder
    def kpi(cell, arm):
        rows = {}
        for f in glob.glob(f"{ROOT}/{cell}/{arm}_*.json"):
            rows.update({int(k): v for k, v in json.load(open(f)).items()})
        return {s: r["kpi"]["urllc"]["delay_steps"] for s, r in rows.items() if r["kpi"]["urllc"]["delay_steps"] is not None}
    dl = {a: summ(kpi("m77/A_n37_hex", a), f"m77/A_n37_hex/{a}_*.json kpi.urllc.delay_steps") for a in LEARNED + ("rule_static",)}
    if m97 and glob.glob(f"{ROOT}/m97/A_n37_hex_kpi/rule_local_cell_*.json"):
        dl["rule_local"] = summ(kpi("m97/A_n37_hex_kpi", "rule_local_cell"), "m97/A_n37_hex_kpi/rule_local_cell_*.json kpi.urllc.delay_steps (M97)")
    d["delay37"] = dl

    # ---- Env A: trained at 7 gNBs and evaluated at 7 (the transfer source), and the same checkpoints run at 37 (M92)
    c7, tr = {}, {}
    for a in LEARNED:
        c7[a] = summ({f"{t}:{s}": P(r) for t in ("hex", "ring", "fully_connected")
                      for s, r in seeds_of(f"m65_scaling/n7_{t}", a, S15).items()}, f"m65_scaling/n7_{{hex,ring,fully_connected}}/{a}, 15 seeds each")
    for a in ("axiom2", "mappo_tuned"):
        tr[a] = summ({f"{t}:{s}": P(r) for t in ("hex", "ring", "fully_connected")
                      for s, r in seeds_of(f"m92/A_{t}_n37", f"{a}_transfer", S15).items()}, f"m92/A_{{hex,ring,fully_connected}}_n37/{a}_transfer, 15 seeds each")
        tr[a]["by_layout"] = {t: float(np.mean([P(r) for r in seeds_of(f"m92/A_{t}_n37", f"{a}_transfer", S15).values()]))
                              for t in ("hex", "ring", "fully_connected")}
    d["compliance7"], d["transfer37"] = c7, tr
    d["notes"]["transfer"] = ("DQN-SA and DQN-I cannot run at another size: their input dimension is fixed by the number of gNBs. "
                              "Rules have no learned part; the static rule's threshold was chosen in Env A at 3 gNBs and its 37-gNB "
                              "compliance is sla37.rule_static. The tuned local rule was never carried across sizes in Env A.")

    # ---- Env B, 19 gNBs hex: reward per step relative to the tuned rule carried from 7 gNBs, nominal and 110-120% load
    def b19(arm, load):
        if arm == "rule_static":                 # not in M96; M76 ran it on the same seeds and loads
            return {s: shift_row("m76/b1_shift_n19", load, arm, s)["reward"] for s in S15}
        return {s: r["reward"] for s, r in seeds_of(f"m96/B_shift/n19_hex/{load}", arm, S15).items()}
    rule = {L: b19("rule_local_transfer", L) for L in ("nominal",) + LOADS}
    # the M76 rule rows, used for the static rule, must equal the M96 rule rows
    m76rule = {L: {s: shift_row("m76/b1_shift_n19", L, "rule_local_transfer", s)["reward"] for s in S15} for L in ("nominal",) + LOADS}
    d["notes"]["m76_m96_rule_identical"] = all(abs(m76rule[L][s] - rule[L][s]) < 1e-9 for L in rule for s in S15)
    past, steady = {}, {}
    for a in LEARNED + ("rule_static",):
        rows = {L: b19(a, L) for L in ("nominal",) + LOADS}
        past[a] = summ({s: float(np.mean([rows[L][s] - rule[L][s] for L in LOADS])) for s in S15},
                       ("m96" if a != "rule_static" else "m76") + "/…/n19 shift logs: mean over 110, 115, 120% load of (arm - tuned rule) reward per step")
        past[a]["by_load"] = {L: float(np.mean([rows[L][s] - rule[L][s] for s in S15])) for L in LOADS}
        steady[a] = summ({s: rows["nominal"][s] - rule["nominal"][s] for s in S15},
                         ("m96" if a != "rule_static" else "m76") + "/…/n19 nominal: (arm - tuned rule) reward per step")
    d["past19"], d["steady19"] = past, steady
    d["over_tuned_rule_m76"] = {L: paired({s: {"reward": shift_row("m76/b1_shift_n19", L, "axiom2", s)["reward"]} for s in S15},
                                          {s: {"reward": m76rule[L][s]} for s in S15}) for L in LOADS}
    d["sources"]["over_tuned_rule_m76"] = "m76/b1_shift_n19/{load}/{axiom2,rule_local_transfer}: the paper's +6.23, +7.55, +8.67"

    # M96 b, as in the current Fig. 10: tests won against the tuned rule over 3, 7, 19 gNBs x 110, 115, 120%, Holm per controller
    cells = {3: ("m96/B_shift/n3", list(range(905, 930)), "rule_local"), 7: ("m96/B_shift/n7_ring", S15, "rule_local"),
             19: ("m96/B_shift/n19_hex", S15, "rule_local_transfer")}
    wins = {}
    for a in LEARNED:
        t = {f"{n}|{L}": paired(seeds_of(f"{c}/{L}", a, ss), seeds_of(f"{c}/{L}", rl, ss)) for n, (c, ss, rl) in cells.items() for L in LOADS}
        h = holm({k: v["p"] for k, v in t.items()})
        wins[a] = {"wins": int(sum(v["diff"] > 0 and h[k] < 0.05 for k, v in t.items())), "tests": len(t)}
    d["past_wins_m96"] = wins

    # Env A steady load at 37 gNBs hex: reward per step, all controllers on the same 30 seeds
    rA = {a: summ({s: r["reward"] for s, r in seeds_of("m73/A_n37_hex", a, S30_19).items()}, f"m73/A_n37_hex/{a} reward")
          for a in LEARNED + ("rule_static",)}
    if m97:
        rA["rule_local"] = summ({s: r["reward"] for s, r in seeds_of("m97/A_n37_hex", "rule_local", S30_19).items()}, "m97/A_n37_hex/rule_local reward")
    d["rewardA37"] = rA

    # ---- federated training (Env A, 3 gNBs): centralised minus federated reward per step, 30 seeds (as the paper's +0.491)
    REP = list(range(1000, 1010)); S10 = list(range(900, 910))
    fd = {}
    for cen, fc, ss in (("m65_reviewer/base", "m65_m3", S10), ("m65_reviewer/replication", "m65_m3_replication", REP)):
        a_, b_ = seeds_of(cen, "axiom2", ss), seeds_of(fc, "fl_gat_ctde_sigma0.0", ss)
        fd.update({s: a_[s]["reward"] - b_[s]["reward"] for s in ss})
    a_ = seeds_of("m66_fresh/A_n3", "axiom2", list(range(3000, 3010))); b_ = {}
    for k in range(3000, 3010, 2):
        b_.update(seeds_of(f"m66b_fresh/m3_s{k}", "fl_gat_ctde_sigma0.0", [k, k + 1]))
    fd.update({s: a_[s]["reward"] - b_[s]["reward"] for s in range(3000, 3010)})
    from scipy.stats import wilcoxon
    d["fed_cost"] = summ(fd, "m65_reviewer/{base,replication} axiom2 minus m65_m3{,_replication} fl sigma0; m66_fresh/A_n3 minus m66b_fresh/m3_s*")
    d["fed_cost"]["p_wilcoxon"] = float(wilcoxon(np.array(list(fd.values()))).pvalue)
    d["notes"]["private_training"] = ("Only AXIOM was trained federated (measured). For the others the entry follows from the training "
                                      "design stated in the paper (Sec. 4, Table 3): MAPPO's critic reads every gNB's features, DQN-SA is one "
                                      "learner over the joint state, DQN-I trains each gNB on its own requests, and the rules learn no model.")

    # ---- Env B reward over MAPPO at 3 and 19 gNBs (ratio of means, paired bootstrap over seeds)
    om = {}
    for lab, cell, ss in (("3", "m64/n3_fully_connected", S30), ("19", "m75/D_envB_n19_hex", S15)):
        A_, M_ = seeds_of(cell, "axiom2", ss), seeds_of(cell, "mappo_tuned", ss)
        s_ = sorted(set(A_) & set(M_)); a = np.array([A_[s]["reward"] for s in s_]); m = np.array([M_[s]["reward"] for s in s_])
        r = bootstrap((a, m), lambda x, y: 100 * (x.mean() / y.mean() - 1), paired=True, vectorized=False, n_resamples=10000,
                      method="percentile", random_state=np.random.default_rng(0))
        om[lab] = {"pct": float(100 * (a.mean() / m.mean() - 1)), "ci95": [float(r.confidence_interval.low), float(r.confidence_interval.high)],
                   "n": len(s_), "source": f"{cell} axiom2 and mappo_tuned reward"}
    d["over_mappo_pct"] = om

    # ---- derived margins quoted on the current figure
    best = max(("mappo_tuned", "single_agent_dqn", "independent_dqn"), key=lambda a: sla[a]["mean"])
    d["lead37"] = {"points": sla["axiom2"]["mean"] - sla[best]["mean"], "over": best}
    d["delay_ratio"] = {a: dl[a]["mean"] / dl["axiom2"]["mean"] for a in ("mappo_tuned", "single_agent_dqn", "independent_dqn")}
    d["params_ratio_dqni"] = d["params"]["independent_dqn"]["37"] / d["params"]["axiom2"]["37"]
    d["m97_available"] = m97 and "rule_local" in dl
    json.dump(d, open(OUT, "w"), indent=1)
    return d


def load(refresh=False):
    if refresh or not os.path.exists(OUT):
        return build()
    return json.load(open(OUT))


if __name__ == "__main__":
    d = build()
    print({k: (round(v["mean"], 3), [round(x, 3) for x in v["ci95"]], v["n"]) for k, v in d["sla37"].items()})
    print({k: (round(v["mean"], 3), v["n"]) for k, v in d["delay37"].items()})
    print("past", {k: round(v["mean"], 3) for k, v in d["past19"].items()}, "steady", {k: round(v["mean"], 3) for k, v in d["steady19"].items()})
    print("m76==m96 rule:", d["notes"]["m76_m96_rule_identical"], "fed", round(d["fed_cost"]["mean"], 3), d["fed_cost"]["n"])
    print("lead", d["lead37"], "ratio", d["delay_ratio"], "params", d["params_ratio_dqni"], "om", d["over_mappo_pct"])
