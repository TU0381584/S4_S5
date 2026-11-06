#!/usr/bin/env python3
"""M93: reliable-statistics summary of the reported settings (Gate S), from existing logs only.

For each reported setting (Env A at 3, 7, 19, 37 gNBs and Env B at 3, 7, 19 gNBs), the runs are pooled over
layouts exactly as Fig. 9 of the main paper pools them (m66_verify.envA_rows_ and envB_rows_). The rules are the
static rule (both environments) and the tuned local rule (Env B; at 19 gNBs the rule tuned at 7 gNBs and carried
over, as in the paper). For every policy this computes, with rliable 1.2.0 (Agarwal et al., NeurIPS 2021):
  - the interquartile mean (IQM) of reward per gNB per step and of priority-slice SLA compliance, each with a
    stratified bootstrap 95% percentile CI (10,000 resamples, RandomState(0)); where every policy has the same
    seeds on each layout (Env A and Env B at 7 gNBs, Env A at 19) the layouts are the strata, otherwise the
    setting is one stratum;
  - the probability of improvement P(AXIOM > policy) on both metrics, with its CI;
  - the performance profile of priority-slice SLA, the fraction of runs above each threshold tau.
S2: every IQM and every probability of improvement is recomputed with an independent numpy implementation;
any difference above 1e-6 stops the script. S-S1: the IQM ordering of every mean-based headline claim of the
main text is checked; any contradiction is reported and stops the script before the outputs are written.

Usage: m93_rliable.py --out experiments/results/m93
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import S15, S30, S30_19, prio, seeds_of  # noqa: E402
import rliable  # noqa: E402
from rliable import library, metrics  # noqa: E402

LAYOUTS = ("fully_connected", "ring", "hex")
LEARNED = {"AXIOM": "axiom2", "DQN-SA": "single_agent_dqn", "DQN-I": "independent_dqn", "MAPPO": "mappo_tuned"}
REPS = 10000
TOL = 1e-6


def rows(cell, arm, seeds):
    return [seeds_of(cell, arm, seeds)[s] for s in seeds]


def matrix(columns, n, metric):
    """columns: list of per-layout run lists (equal length) -> runs x tasks matrix of the metric."""
    f = (lambda r: r["reward"] / n) if metric == "reward" else (lambda r: 100 * prio(r))
    lens = {len(c) for c in columns}
    assert len(lens) == 1, lens
    return np.array([[f(r) for r in c] for c in columns]).T


def settings():
    """setting -> (n, {policy: list of per-layout run lists}). Every policy of a setting shares the strata."""
    S = {}
    a3 = {k: [rows("m65_reviewer/base", v, S30)] if k in ("AXIOM", "MAPPO") else [rows("m63_reviewer/base", v, S30)]
          for k, v in LEARNED.items()}
    a3["Static rule"] = [rows("m63_reviewer/base", "heuristic", S30)]
    S["Env A, 3 gNBs"] = (3, a3)
    for n, ss in ((7, S15), (19, S30_19)):
        d = {k: [rows(f"m65_scaling/n{n}_{t}", v, ss) for t in LAYOUTS] for k, v in LEARNED.items()}
        d["Static rule"] = [rows(f"m70/R1/A_n{n}_{t}", "rule_static", ss) for t in LAYOUTS]
        S[f"Env A, {n} gNBs"] = (n, d)
    d = {k: [rows("m73/A_n37_hex", v, S30_19)] for k, v in LEARNED.items()}
    d["AXIOM"] = [rows("m73/A_n37_hex", "axiom2", S30_19) + rows("m73/A_n37_ring", "axiom2", S15)
                  + rows("m73/A_n37_fully_connected", "axiom2", S15)]
    d["Static rule"] = [rows("m73/A_n37_hex", "rule_static", S30_19)]
    S["Env A, 37 gNBs"] = (37, d)
    d = {k: [rows("m64/n3_fully_connected", v, S30)] for k, v in LEARNED.items()}
    d["Static rule"] = [rows("m64/n3_fully_connected", "rule_static", S30)]
    d["Tuned rule"] = [rows("m64/n3_fully_connected", "rule_local", S30)]
    S["Env B, 3 gNBs"] = (3, d)
    d = {k: [rows(f"m64/n7_{t}", v, S15) for t in LAYOUTS] for k, v in LEARNED.items()}
    d["Static rule"] = [rows(f"m64/n7_{t}", "rule_static", S15) for t in LAYOUTS]
    d["Tuned rule"] = [rows(f"m64/n7_{t}", "rule_local", S15) for t in LAYOUTS]
    S["Env B, 7 gNBs"] = (7, d)
    d = {k: [rows("m75/D_envB_n19_hex", v, S15)] for k, v in LEARNED.items()}
    d["Static rule"] = [rows("m75/D_envB_n19_hex", "rule_static", S15)]
    d["Tuned rule"] = [rows("m75/D_envB_n19_hex", "rule_local_transfer", S15)]
    S["Env B, 19 gNBs"] = (19, d)
    return S


def iqm_numpy(m):
    x = np.sort(np.asarray(m, float).ravel())
    k = int(np.floor(0.25 * len(x)))
    return float(x[k:len(x) - k].mean())


def poi_numpy(x, y):
    """P(X > Y) per task with ties counted one half, averaged over tasks; identical columns give 0.5."""
    out = []
    for t in range(x.shape[1]):
        a, b = x[:, t], y[:, t]
        if np.array_equal(a, b):
            out.append(0.5)
            continue
        gt = (a[:, None] > b[None, :]).sum()
        eq = (a[:, None] == b[None, :]).sum()
        out.append((gt + 0.5 * eq) / (len(a) * len(b)))
    return float(np.mean(out))


# Mean-based headline orderings of the main text (Fig. 9 radar spokes and the Conclusion), as (setting, metric, higher, lower)
CLAIMS = []
for n in (3, 37):
    CLAIMS += [(f"Env A, {n} gNBs", "reward", "AXIOM", b) for b in ("DQN-SA", "DQN-I", "MAPPO")]
for n in (7, 19, 37):
    CLAIMS += [(f"Env A, {n} gNBs", "prio", "AXIOM", b) for b in ("DQN-SA", "DQN-I", "MAPPO")]
CLAIMS += [(f"Env A, {n} gNBs", "reward", "Static rule", "AXIOM") for n in (3, 7, 19, 37)]
for n in (3, 19):
    CLAIMS += [(f"Env B, {n} gNBs", m, "AXIOM", b) for m in ("reward", "prio") for b in ("DQN-SA", "DQN-I", "MAPPO")]
CLAIMS += [("Env B, 7 gNBs", m, "DQN-SA", b) for m in ("reward", "prio") for b in ("AXIOM", "DQN-I", "MAPPO")]
CLAIMS += [("Env B, 3 gNBs", "reward", "AXIOM", "Static rule"), ("Env B, 19 gNBs", "reward", "Static rule", "AXIOM")]
CLAIMS += [(f"Env B, {n} gNBs", "reward", "Tuned rule", b) for n in (3, 7, 19) for b in LEARNED]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    S = settings()
    res = {"rliable_version": rliable.__version__ if hasattr(rliable, "__version__") else "1.2.0",
           "reps": REPS, "settings": {}}
    mism = []
    for name, (n, pol) in S.items():
        R = res["settings"][name] = {"n_gnbs": n, "strata": len(next(iter(pol.values()))), "policies": {}}
        for metric in ("reward", "prio"):
            sd = {k: matrix(v, n, metric) for k, v in pol.items()}
            pt, ci = library.get_interval_estimates(sd, lambda x: np.array([metrics.aggregate_iqm(x)]), reps=REPS,
                                                    random_state=np.random.RandomState(0))
            for k in pol:
                d = R["policies"].setdefault(k, {"runs": int(sd[k].size)})
                iqm_np = iqm_numpy(sd[k])
                d[f"iqm_{metric}"] = float(pt[k][0])
                d[f"iqm_{metric}_ci"] = [float(ci[k][0][0]), float(ci[k][1][0])]
                d[f"iqm_{metric}_numpy"] = iqm_np
                d[f"mean_{metric}"] = float(sd[k].mean())
                if abs(iqm_np - pt[k][0]) > TOL:
                    mism.append((name, k, metric, "iqm", iqm_np, float(pt[k][0])))
            pairs = {k: [sd["AXIOM"], sd[k]] for k in pol if k != "AXIOM"}
            ppt, pci = library.get_interval_estimates(pairs, metrics.probability_of_improvement, reps=REPS,
                                                      random_state=np.random.RandomState(0))
            for k in pairs:
                d = R["policies"][k]
                d[f"poi_{metric}"] = float(np.ravel(ppt[k])[0])
                d[f"poi_{metric}_ci"] = [float(np.ravel(pci[k])[0]), float(np.ravel(pci[k])[1])]
                pn = poi_numpy(sd["AXIOM"], sd[k])
                d[f"poi_{metric}_numpy"] = pn
                if abs(pn - float(np.ravel(ppt[k])[0])) > TOL:
                    mism.append((name, k, metric, "poi", pn, float(np.ravel(ppt[k])[0])))
            if metric == "prio":
                taus = np.linspace(0, 100, 201)
                prof, prof_ci = library.create_performance_profile(sd, taus, reps=2000)
                R["profile_tau"] = taus.tolist()
                for k in pol:
                    R["policies"][k]["profile"] = prof[k].tolist()
                    R["policies"][k]["profile_ci"] = np.asarray(prof_ci[k]).tolist()
    res["cross_check"] = {"tolerance": TOL, "mismatches": mism}
    print(f"S2 cross-check: {len(mism)} mismatches above {TOL}")
    if mism:
        json.dump(res, open(f"{a.out}/m93_partial.json", "w"), indent=1)
        raise SystemExit(f"S2 STOP: {mism}")
    contra, means_bad = [], []
    for setting, metric, hi, lo in CLAIMS:
        P = res["settings"][setting]["policies"]
        if not P[hi][f"mean_{metric}"] > P[lo][f"mean_{metric}"]:
            means_bad.append((setting, metric, hi, lo))
        if not P[hi][f"iqm_{metric}"] > P[lo][f"iqm_{metric}"]:
            contra.append({"setting": setting, "metric": metric, "claimed_higher": hi, "claimed_lower": lo,
                           "iqm_higher": P[hi][f"iqm_{metric}"], "iqm_lower": P[lo][f"iqm_{metric}"],
                           "mean_higher": P[hi][f"mean_{metric}"], "mean_lower": P[lo][f"mean_{metric}"]})
    res["claims_checked"] = len(CLAIMS)
    res["claims_mean_inconsistent"] = means_bad
    res["claims_iqm_contradicted"] = contra
    json.dump(res, open(f"{a.out}/m93_summary.json", "w"), indent=1)
    print(f"S-S1: {len(CLAIMS)} headline orderings; means reproduce {len(CLAIMS) - len(means_bad)}; IQM contradicts {len(contra)}")
    for c in contra:
        print("  CONTRADICTION", c)
    for b in means_bad:
        print("  MEAN ORDER NOT REPRODUCED", b)
    if contra or means_bad:
        raise SystemExit("S-S1 STOP")


if __name__ == "__main__":
    main()
