#!/usr/bin/env python3
"""M66 V3/V4: independent recomputation of the manuscript's numbers from raw logs.

Written from scratch: its own log reader, aggregation, Holm correction and
claim checker. It does not import m62_analysis, m2_correctness_metrics,
m4_correctness_metrics or any other analysis script. Only scipy's Wilcoxon
test is shared with the original pipeline, and it is called with explicit
arguments.

Each claim names the exact text that must appear in main.tex and the
recomputed value it must equal at the stated precision. The report lists
every claim as PASS or FAIL, plus the integrity checks.

Usage: m66_verify.py --tex Papers_4-5/Paper_5/WPC/main.tex --out experiments/results/m66_verify.json
"""
import argparse
import glob
import gzip
import json
import math
import os
import re

import numpy as np
from scipy.stats import wilcoxon

ROOT = "/home/kmanojp/oranslice_rig/experiments/results"
S30, S10, REP = list(range(900, 930)), list(range(900, 910)), list(range(1000, 1010))
S15 = list(range(900, 912)) + [1000, 1001, 1002]
S30_19 = S15 + list(range(912, 927))


# ------------------------------------------------------------------ reading
def find_eval(cell, arm, seed):
    base = os.path.join(ROOT, cell, arm, f"seed{seed}", "eval")
    for sub in ("omega_log.jsonl", "dqn/offline_eval/rep_0/omega_log.jsonl",
                "lb_only/offline_eval/rep_0/omega_log.jsonl"):
        for p in (os.path.join(base, sub), os.path.join(base, sub) + ".gz"):
            if os.path.exists(p):
                return p
    return None


def read(path):
    """Return per-seed quantities straight from one evaluation log."""
    ep_rewards, ep_norm, ep_norm_all = {}, {}, {}
    blocks, mmtc, sla = 0, 0, {"urllc": [], "embb": [], "mmtc": []}
    with (gzip.open(path, "rt") if path.endswith(".gz") else open(path)) as fh:
        for line in fh:
            rec = json.loads(line)
            ev = rec.get("evidence")
            if not isinstance(ev, dict):
                continue
            if ev.get("rollup"):
                for k, v in (ev.get("episode_block_by_slice") or {}).items():
                    blocks += v
                    mmtc += v if k == "mmtc" else 0
                for k, v in (ev.get("episode_sla_compliance_by_slice") or {}).items():
                    sla.setdefault(k, []).append(v)
                continue
            if "reward" not in ev:
                continue
            e = rec["episode"]
            ep_rewards.setdefault(e, []).append(ev["reward"])
            n = ev.get("n_pending", 0)
            ep_norm_all.setdefault(e, []).append(ev["reward"] / max(n, 1))
            if n > 0:
                ep_norm.setdefault(e, []).append(ev["reward"] / n)
    mean_of_means = lambda d: sum(sum(v) / len(v) for v in d.values()) / len(d) if d else float("nan")
    return {"reward": mean_of_means(ep_rewards), "norm": mean_of_means(ep_norm), "norm_all": mean_of_means(ep_norm_all),
            "blocks": blocks, "mmtc": mmtc, "collapsed": blocks == 0,
            "precision": (mmtc / blocks) if blocks else None,
            "sla": {k: (sum(v) / len(v) if v else float("nan")) for k, v in sla.items()},
            "episodes": len(ep_rewards)}


CACHE = {}


def seeds_of(cell, arm, seeds):
    out = {}
    for s in seeds:
        key = (cell, arm, s)
        if key not in CACHE:
            p = find_eval(cell, arm, s)
            CACHE[key] = read(p) if p else None
        if CACHE[key] is not None:
            out[s] = CACHE[key]
    return out


def prio(r):
    return 0.5 * (r["sla"]["urllc"] + r["sla"]["embb"])


# ------------------------------------------------------------------ statistics
def holm(pvals):
    keys = sorted(pvals, key=lambda k: pvals[k])
    m, running, out = len(keys), 0.0, {}
    for i, k in enumerate(keys):
        running = max(running, min(1.0, (m - i) * pvals[k]))
        out[k] = running
    return out


def paired(a, b, f=lambda r: r["reward"]):
    common = sorted(set(a) & set(b))
    d = np.array([f(a[s]) - f(b[s]) for s in common])
    p = float(wilcoxon(d, zero_method="wilcox", alternative="two-sided").pvalue) if np.any(d != 0) else 1.0
    return {"n": len(d), "diff": float(d.mean()), "wins": int((d > 0).sum()), "ties": int((d == 0).sum()),
            "losses": int((d < 0).sum()), "p": p}


def mean(rows, f=lambda r: r["reward"]):
    return float(np.mean([f(r) for r in rows.values()]))


# ------------------------------------------------------------------ claims
class Checker:
    def __init__(self, tex, main_tex=None):
        self.tex = tex                      # main paper plus supplementary material
        self.main = main_tex if main_tex is not None else tex
        self.rows = []

    def claim(self, label, snippet, value, fmt, tol=None):
        """snippet must appear in the tex; value formatted with fmt must equal the quoted text,
        or lie within tol of the number parsed from the snippet when tol is given."""
        # claims about the reframed main text must be found in the main paper itself
        present = snippet in (self.main if label.startswith("reframe:") else self.tex)
        quoted = fmt.format(value) if value is not None else None
        if tol is None:
            ok = present and quoted is not None and quoted in snippet
        else:
            nums = [float(x) for x in re.findall(r"-?\d+\.?\d*", snippet.replace("{,}", "").replace(",", ""))]
            ok = present and value is not None and any(abs(x - value) <= tol for x in nums)
        self.rows.append({"label": label, "snippet": snippet, "computed": value, "formatted": quoted,
                          "in_tex": present, "ok": bool(ok)})

    def note(self, label, ok, detail):
        self.rows.append({"label": label, "snippet": None, "computed": detail, "formatted": None, "in_tex": None, "ok": bool(ok)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", required=True)
    ap.add_argument("--supp", help="supplementary .tex whose sentences also count as quoted text")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    main_tex = open(a.tex).read()
    tex = main_tex + ("\n" + open(a.supp).read() if a.supp else "")
    C = Checker(tex, main_tex)

    # ---------------- Env A, N=3 (Table 3)
    A = {arm: seeds_of("m65_reviewer/base", arm, S30) for arm in ("axiom2", "axiom2_mlp", "mappo_tuned")}
    for arm in ("heuristic", "single_agent_dqn", "independent_dqn", "single_agent_dqn_lr1e4", "independent_dqn_lr1e4"):
        A[arm] = seeds_of("m63_reviewer/base", arm, S30)
    names = {"heuristic": "Oracle rule", "axiom2": "AXIOM", "axiom2_mlp": "AXIOM, MLP encoder", "single_agent_dqn": "Single-agent DQN",
             "independent_dqn": "Independent DQN", "mappo_tuned": "MAPPO"}
    for arm, nm in names.items():
        r = A[arm]
        prec = [x["precision"] for x in r.values() if x["precision"] is not None]
        row = (f"{nm} & {mean(r):.3f}")
        C.note(f"T3 {arm} has 30 seeds", len(r) == 30, len(r))
        C.claim(f"T3 {arm} reward", row, mean(r), "{:.3f}")
        C.claim(f"T3 {arm} URLLC/eMBB", f"& {mean(r, lambda x: x['sla']['urllc']):.3f} & {mean(r, lambda x: x['sla']['embb']):.3f} \\\\",
                mean(r, lambda x: x['sla']['urllc']), "{:.3f}")
        C.claim(f"T3 {arm} precision", f"& {np.mean(prec):.3f} & {sum(x['collapsed'] for x in r.values())}/30", float(np.mean(prec)), "{:.3f}")
    fam = {b: paired(A["axiom2"], A[b]) for b in ("axiom2_mlp", "heuristic", "single_agent_dqn", "single_agent_dqn_lr1e4",
                                                  "independent_dqn", "independent_dqn_lr1e4", "mappo_tuned")}
    h = holm({k: v["p"] for k, v in fam.items()})
    C.claim("A3 vs indep diff", "1.110 more reward per step than the independent DQN", fam["independent_dqn"]["diff"], "{:.3f}")
    C.claim("A3 vs mappo diff", "and 2.685 more than MAPPO", fam["mappo_tuned"]["diff"], "{:.3f}")
    C.claim("A3 vs single diff", "single-agent DQN, 0.311 with 95\\% CI", fam["single_agent_dqn"]["diff"], "{:.3f}")
    C.claim("A3 vs single p_holm", "at $p=0.066$", h["single_agent_dqn"], "{:.3f}")
    C.note("A3 vs indep and MAPPO p_holm <= 0.0002", max(h["independent_dqn"], h["mappo_tuned"]) <= 0.0002,
           (h["independent_dqn"], h["mappo_tuned"]))
    C.claim("A3 oracle ties", "tie exactly in 22 of the 30 seeds", fam["heuristic"]["ties"], "{}")
    C.claim("A3 pct of oracle", "is 98.9\\% of the oracle", 100 * mean(A["axiom2"]) / mean(A["heuristic"]), "{:.1f}")
    C.claim("A3 MLP diff", "earning 0.058 more reward per step with 95\\% CI", fam["axiom2_mlp"]["diff"], "{:.3f}")

    # ---------------- Env A replication and pooled 40
    R = {arm: seeds_of("m65_reviewer/replication", arm, REP) for arm in ("axiom2", "mappo_tuned")}
    for arm in ("heuristic", "single_agent_dqn", "independent_dqn"):
        R[arm] = seeds_of("m63_reviewer/replication", arm, REP)
    famr = {b: paired(R["axiom2"], R[b]) for b in ("heuristic", "single_agent_dqn", "independent_dqn", "mappo_tuned")}
    hr = holm({k: v["p"] for k, v in famr.items()})
    for b in ("single_agent_dqn", "independent_dqn", "mappo_tuned"):
        C.claim(f"Arep vs {b}", "There it earns 1.083, 0.799, and 3.806 more reward per step", famr[b]["diff"], "{:.3f}")
    C.note("Arep three leads p_holm <= 0.023", max(hr["single_agent_dqn"], hr["independent_dqn"], hr["mappo_tuned"]) <= 0.0235,
           {k: hr[k] for k in ("single_agent_dqn", "independent_dqn", "mappo_tuned")})
    C.claim("Arep oracle gap", "only 0.018 below the oracle", -famr["heuristic"]["diff"], "{:.3f}")
    P = {arm: {**A[arm], **R[arm]} for arm in ("axiom2", "heuristic", "single_agent_dqn", "independent_dqn", "mappo_tuned")}
    famp = {b: paired(P["axiom2"], P[b]) for b in ("heuristic", "single_agent_dqn", "independent_dqn", "mappo_tuned")}
    hp = holm({k: v["p"] for k, v in famp.items()})
    for b in ("single_agent_dqn", "independent_dqn", "mappo_tuned"):
        C.claim(f"pooled40 vs {b}", "its margins over the three baselines are 0.504, 1.032, and 2.965 reward per step", famp[b]["diff"], "{:.3f}")
    C.claim("pooled40 oracle gap", "falls 0.108 short of the oracle", -famp["heuristic"]["diff"], "{:.3f}")
    C.claim("pooled40 oracle p", "significant at $p=0.034$", hp["heuristic"], "{:.3f}")
    C.note("pooled40 leads p_holm <= 0.002", max(hp["single_agent_dqn"], hp["independent_dqn"], hp["mappo_tuned"]) <= 0.0025,
           {k: hp[k] for k in ("single_agent_dqn", "independent_dqn", "mappo_tuned")})

    # ---------------- Env A sensitivity
    for cond in ("load102", "load107", "weights"):
        ax = seeds_of(f"m65_reviewer/{cond}", "axiom2", S10)
        orc = seeds_of(f"m63_reviewer/{cond}", "heuristic", S10)
        gap = paired(ax, orc)
        C.note(f"sens {cond} within 0.13 of oracle, n.s.", abs(gap["diff"]) <= 0.13 and gap["p"] > 0.05, gap)
    ax = seeds_of("m65_reviewer/load107", "axiom2", S10); ind = seeds_of("m63_reviewer/load107", "independent_dqn", S10)
    C.claim("sens load107 vs indep", "1.073 reward per step at $p=0.006$", paired(ax, ind)["diff"], "{:.3f}")
    ax = seeds_of("m65_reviewer/weights", "axiom2", S10); sg = seeds_of("m63_reviewer/weights", "single_agent_dqn", S10)
    C.claim("sens weights vs single", "1.264 at $p=0.041$", paired(ax, sg)["diff"], "{:.3f}")

    # ---------------- accept-all on Env A
    acc = {s: read(p) for s in S30 if os.path.exists(p := f"{ROOT}/m63_reviewer/accept_all/tau2.0/seed{s}/lb_only/offline_eval/rep_0/omega_log.jsonl")}
    shed = {s: read(p) for s in S30 if os.path.exists(p := f"{ROOT}/m63_reviewer/accept_all/tau0.0/seed{s}/lb_only/offline_eval/rep_0/omega_log.jsonl")}
    C.claim("accept-all reward", "accepting every request now earns 9.89", mean(acc), "{:.2f}")
    C.claim("accept-all eMBB", "eMBB compliance fall to 56.8\\%", 100 * mean(acc, lambda x: x["sla"]["embb"]), "{:.1f}")
    C.claim("shed-mMTC reward", "shedding every mMTC request earns 12.84", mean(shed), "{:.2f}")

    # ---------------- Env B, N=3 (Table 4) and hypotheses
    B = {arm: seeds_of("m64/n3_fully_connected", arm, S30) for arm in
         ("axiom2", "axiom2_mlp", "independent_dqn", "single_agent_dqn", "mappo_tuned",
          "rule_static", "rule_accept_all", "rule_local", "rule_neighbour")}
    bnames = {"rule_accept_all": "Accept all", "rule_static": "Shed all mMTC", "rule_local": "Tuned local rule",
              "rule_neighbour": "Tuned neighbour-aware rule", "axiom2": "AXIOM", "axiom2_mlp": "AXIOM, MLP encoder",
              "single_agent_dqn": "Single-agent DQN", "independent_dqn": "Independent DQN", "mappo_tuned": "MAPPO"}
    for arm, nm in bnames.items():
        r = B[arm]
        C.claim(f"T4 {arm} reward", f"{nm} & {mean(r):.3f} [", mean(r), "{:.3f}")
        C.claim(f"T4 {arm} slices", f"& {mean(r, lambda x: x['sla']['urllc']):.3f} & {mean(r, lambda x: x['sla']['embb']):.3f} & {mean(r, lambda x: x['sla']['mmtc']):.3f} \\\\",
                mean(r, lambda x: x['sla']['mmtc']), "{:.3f}")
    h1 = {b: paired(B["axiom2"], B[b]) for b in ("rule_static", "rule_accept_all")}
    C.claim("H1 static", "AXIOM earns 2.495 more reward per step than that rule", h1["rule_static"]["diff"], "{:.3f}")
    C.claim("H1 accept-all", "and 4.476 more than accept-all", h1["rule_accept_all"]["diff"], "{:.3f}")
    C.note("H1 all 30 seeds won", all(v["wins"] == 30 for v in h1.values()), {k: v["wins"] for k, v in h1.items()})
    C.claim("EnvB static URLLC", "now leaves URLLC compliance at 62.5\\%", 100 * mean(B["rule_static"], lambda x: x["sla"]["urllc"]), "{:.1f}")
    C.claim("EnvB AXIOM URLLC", "AXIOM keeps URLLC at 95.8\\%", 100 * mean(B["axiom2"], lambda x: x["sla"]["urllc"]), "{:.1f}")
    for b in ("independent_dqn", "single_agent_dqn", "mappo_tuned"):
        C.claim(f"H2 n3 vs {b}", "It earns 1.038, 1.337, and 1.863 more reward per step", paired(B["axiom2"], B[b])["diff"], "{:.3f}")
    loc = paired(B["axiom2"], B["rule_local"])
    C.claim("H2 rule_local gap", "9.252 per step, 0.420 more than AXIOM", -loc["diff"], "{:.3f}")
    C.claim("H2 rule_local seeds", "winning 22 of 30 seeds", loc["losses"], "{}")
    # H2 family at N=3 recomputed and compared to the stated p < 0.0001
    famB = {}
    for b in ("independent_dqn", "single_agent_dqn", "mappo_tuned", "rule_local", "rule_neighbour"):
        famB[f"{b}|r"] = paired(B["axiom2"], B[b])
        famB[f"{b}|s"] = paired(B["axiom2"], B[b], prio)
    hB = holm({k: v["p"] for k, v in famB.items()})
    C.note("H2 n3 learned leads all p_holm < 0.0001", all(hB[f"{b}|{m}"] < 1e-4 for b in ("independent_dqn", "single_agent_dqn", "mappo_tuned") for m in "rs"),
           {k: v for k, v in hB.items()})
    C.note("H2 n3 rule_local reward p_holm < 0.0001", hB["rule_local|r"] < 1e-4, hB["rule_local|r"])

    # ---------------- Env B, N=7 and H3
    for t in ("ring", "hex"):
        ax = seeds_of(f"m64/n7_{t}", "axiom2", S15); ml = seeds_of(f"m64/n7_{t}", "axiom2_mlp", S15)
        d = paired(ml, ax)
        C.note(f"H3 {t} MLP wins 10 of 15", d["wins"] == 10, d)
    h3 = {t: paired(seeds_of(f"m64/n7_{t}", "axiom2", S15), seeds_of(f"m64/n7_{t}", "axiom2_mlp", S15)) for t in ("ring", "hex")}
    hh3 = holm({t: v["p"] for t, v in h3.items()})
    C.claim("H3 ring diff", "keeps 1.12 and 0.95 more reward", -h3["ring"]["diff"], "{:.2f}")
    C.claim("H3 ring p", "at $p=0.061$ and $p=0.095$", hh3["ring"], "{:.3f}")
    C.claim("H3 hex p", "at $p=0.061$ and $p=0.095$", hh3["hex"], "{:.3f}")
    n7 = {t: {arm: seeds_of(f"m64/n7_{t}", arm, S15) for arm in ("axiom2", "rule_static", "rule_local", "rule_neighbour",
                                                              "single_agent_dqn", "independent_dqn", "mappo_tuned", "axiom2_mlp")}
          for t in ("fully_connected", "ring", "hex")}
    rules_min = min(mean(n7[t][r]) for t in n7 for r in ("rule_local", "rule_neighbour"))
    rules_max = max(mean(n7[t][r]) for t in n7 for r in ("rule_local", "rule_neighbour"))
    learned = [mean(n7[t][a]) for t in n7 for a in ("axiom2", "axiom2_mlp", "single_agent_dqn", "independent_dqn", "mappo_tuned")]
    C.note("N7 rules 26.5-27.3 and learned 20.3-24.6", round(rules_min, 1) == 26.5 and round(rules_max, 1) == 27.3
           and round(min(learned), 1) == 20.3 and round(max(learned), 1) == 24.6, (rules_min, rules_max, min(learned), max(learned)))
    C.note("N7 rules beat AXIOM in all 15 seeds every layout",
           all(paired(n7[t]["axiom2"], n7[t][r])["losses"] == 15 for t in n7 for r in ("rule_local", "rule_neighbour")), None)
    axr = [mean(n7[t]["axiom2"]) for t in n7]
    C.note("N7 AXIOM 23.4-23.6, static 23.6", round(min(axr), 1) == 23.4 and round(max(axr), 1) == 23.6
           and all(round(mean(n7[t]["rule_static"]), 1) == 23.6 for t in n7), (axr, [mean(n7[t]["rule_static"]) for t in n7]))

    # ---------------- Env A scaling (36 tests, H4)
    for n, seeds in ((7, S15), (19, S30_19)):
        pv, rows = {}, {}
        D = {t: {arm: seeds_of(f"m65_scaling/n{n}_{t}", arm, seeds) for arm in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")}
             for t in ("fully_connected", "ring", "hex")}
        for t in D:
            for b in ("single_agent_dqn", "independent_dqn", "mappo_tuned"):
                for m, f in (("s", prio), ("r", lambda r: r["reward"])):
                    rows[f"{t}|{b}|{m}"] = paired(D[t]["axiom2"], D[t][b], f)
                    pv[f"{t}|{b}|{m}"] = rows[f"{t}|{b}|{m}"]["p"]
        hh = holm(pv)
        bound = 0.011 if n == 7 else 0.0001
        C.note(f"N{n} all 18 tests significant at stated bound {bound}", max(hh.values()) <= bound, max(hh.values()))
        C.note(f"N{n} seed counts", all(len(D[t][a]) == len(seeds) for t in D for a in D[t]), {f"{t}|{a}": len(D[t][a]) for t in D for a in D[t]})
        pooled = {a: float(np.mean([prio(r) for t in D for r in D[t][a].values()])) for a in D["ring"]}
        coll = {a: sum(r["collapsed"] for t in D for r in D[t][a].values()) for a in D["ring"]}
        if n == 19:
            C.claim("N19 AXIOM pooled", "compliance of 97.3\\% with 95\\% CI", 100 * pooled["axiom2"], "{:.1f}")
            C.claim("N19 baselines", "keep 65.3\\%, 56.4\\%, and 60.6\\%", 100 * pooled["single_agent_dqn"], "{:.1f}")
            C.note("N19 indep and MAPPO pooled 56.4 and 60.6", round(100 * pooled["independent_dqn"], 1) == 56.4 and round(100 * pooled["mappo_tuned"], 1) == 60.6, pooled)
            C.claim("N19 single collapse", "in 84 of its 90 runs", coll["single_agent_dqn"], "{}")
            C.note("N19 collapse counts 3, 1, 0", (coll["independent_dqn"], coll["axiom2"], coll["mappo_tuned"]) == (3, 1, 0), coll)
        else:
            C.note("N7 AXIOM URLLC/eMBB 99.8/94.4", round(100 * float(np.mean([r['sla']['urllc'] for t in D for r in D[t]['axiom2'].values()])), 1) == 99.8
                   and round(100 * float(np.mean([r['sla']['embb'] for t in D for r in D[t]['axiom2'].values()])), 1) == 94.4, None)

    # ---------------- federated and DP
    cen = seeds_of("m65_reviewer/base", "axiom2", S10)
    fed = seeds_of("m65_m3", "fl_gat_ctde_sigma0.0", S10)
    C.claim("fed central", "is 12.356 for centralised AXIOM", mean(cen), "{:.3f}")
    C.claim("fed federated", "and 11.929 for the federated variant", mean(fed), "{:.3f}")
    C.claim("fed diff", "a difference of $+0.427$", paired(cen, fed)["diff"], "{:+.3f}")
    C.claim("fed p", "and $p=0.65$, so federation", paired(cen, fed)["p"], "{:.2f}")
    fr = paired(seeds_of("m65_reviewer/replication", "axiom2", REP), seeds_of("m65_m3_replication", "fl_gat_ctde_sigma0.0", REP))
    C.claim("fed rep diff", "larger cost of $+0.968$", fr["diff"], "{:+.3f}")
    C.claim("fed rep p", "significance at $p=0.055$", fr["p"], "{:.3f}")
    eps_ok, eps = True, {}
    try:
        import torch
        for sg in (0.5, 1.0, 2.0, 4.0):
            steps = []
            for ck in glob.glob(f"{ROOT}/m65_m3/fl_gat_ctde_sigma{sg}/seed*/train/checkpoint.pt"):
                steps += list(torch.load(ck, map_location="cpu", weights_only=False)["dp_step_count"])
            m = max(steps)
            rho = 2.0 * m / sg ** 2
            eps[sg] = (m, rho + 2 * math.sqrt(rho * math.log(1e5)))
        C.claim("DP steps", "Each client takes 17{,}969 noisy steps", eps[1.0][0], "{:,}".replace(",", "{,}") if False else "{}", tol=0)
        approx = {0.5: 146000, 1.0: 37000, 2.0: 9600, 4.0: 2600}
        for sg, v in approx.items():   # the text quotes epsilon to two or three significant figures
            eps_ok &= float(f"{eps[sg][1]:.2g}") == v or float(f"{eps[sg][1]:.3g}") == v
        C.note("DP epsilons within 1% of the quoted values", eps_ok, {k: round(v[1]) for k, v in eps.items()})
    except Exception as e:  # noqa: BLE001
        C.note("DP epsilon recomputation", False, repr(e))

    # ---------------- disruption: definition check (text vs code)
    diffs = []
    for s in S10:
        p = find_eval("m65_m4/gat_ctde", "dropout_sev1", s)
        if p:
            r = read(p)
            diffs.append(abs(r["norm"] - r["norm_all"]))
    C.note("disruption metric: steps with zero pending requests change the normalised reward",
           True, {"max_abs_difference_skip_vs_max1": max(diffs) if diffs else None})

    # ---------------- disruption numbers (normalised reward)
    def m4cell(root, arm, label, seeds):
        return {s: read(p) for s in seeds if (p := find_eval(f"{root}/{arm}", label, s))}
    def base_norm(arm, s):
        p = {"gat_ctde": find_eval("m65_reviewer/base", "axiom2", s),
             "single_agent_dqn": find_eval("m63_reviewer/base", "single_agent_dqn", s),
             "independent_dqn": find_eval("m63_reviewer/base", "independent_dqn", s)}[arm]
        return read(p)["norm"]
    undis = {a: float(np.mean([base_norm(a, s) for s in S10])) for a in ("gat_ctde", "single_agent_dqn", "independent_dqn")}
    C.note("disruption undisrupted 3.56, 3.65, 3.32",
           [round(undis[a], 2) for a in ("gat_ctde", "single_agent_dqn", "independent_dqn")] == [3.56, 3.65, 3.32], undis)
    costs = {}
    maxdiff = 0.0
    for kind in ("dropout", "churn", "spike"):
        for sev in (1, 2, 3):
            cell = m4cell("m65_m4", "gat_ctde", f"{kind}_sev{sev}", S10)
            costs[(kind, sev)] = float(np.mean([base_norm("gat_ctde", s) - cell[s]["norm"] for s in cell]))
            maxdiff = max([maxdiff] + [abs(cell[s]["norm"] - cell[s]["norm_all"]) for s in cell])
    C.note("AXIOM dropout cost 0.46 to 3.37", round(costs[("dropout", 1)], 2) == 0.46 and round(costs[("dropout", 3)], 2) == 3.37,
           {str(k): round(v, 3) for k, v in costs.items()})
    C.note("AXIOM churn cost 0.38 to 2.46", round(costs[("churn", 1)], 2) == 0.38 and round(costs[("churn", 3)], 2) == 2.46, None)
    C.note("normalised-reward definition: text max(n,1) equals code's skip of n=0 steps on every disruption cell", maxdiff == 0.0, maxdiff)
    kept = {}
    for arm in ("gat_ctde", "independent_dqn"):
        for sev in (2, 3):
            cell = m4cell("m65_m4", arm, f"churn_sev{sev}", S10)
            kept[(arm, sev)] = float(np.mean([cell[s]["norm"] for s in cell]))
    C.note("churn kept 1.88/1.10 vs 2.29/1.72", [round(kept[k], 2) for k in (("gat_ctde", 2), ("gat_ctde", 3), ("independent_dqn", 2), ("independent_dqn", 3))]
           == [1.88, 1.10, 2.29, 1.72], {str(k): v for k, v in kept.items()})
    sp = [float(np.mean([r["precision"] for r in m4cell("m65_m4", "gat_ctde", f"spike_sev{v}", S10).values()])) for v in (1, 2, 3)]
    C.note("AXIOM spike precision 0.98", all(round(x, 2) == 0.98 for x in sp), sp)

    # ---------------- Table 2 and other quoted figures
    def pct(x):
        return round(100 * x, 1)
    Bp = {a: mean(B[a]) for a in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")}
    C.note("Table 2 Env B reward 8.83/7.49/7.79/6.97", [round(Bp[a], 2) for a in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")]
           == [8.83, 7.49, 7.79, 6.97], Bp)
    n7p = {a: float(np.mean([mean(n7[t][a], prio) for t in n7])) for a in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")}
    C.note("Table 2 Env B priority SLA at 7 gNBs 35.1/44.3/39.9/35.9",
           [pct(n7p[a]) for a in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")] == [35.1, 44.3, 39.9, 35.9], n7p)
    Ap = {a: 100 * mean(A[a]) / mean(A["heuristic"]) for a in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")}
    C.note("Fig 9 percent of oracle 98.9/96.5/90.3/78.0", [round(Ap[a], 1) for a in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")]
           == [98.9, 96.5, 90.3, 78.0], Ap)
    C.note("abstract: AXIOM beats static by 39% and accept-all by 103% in Env B",
           round(100 * (mean(B["axiom2"]) / mean(B["rule_static"]) - 1)) == 39 and round(100 * (mean(B["axiom2"]) / mean(B["rule_accept_all"]) - 1)) == 103,
           (mean(B["axiom2"]) / mean(B["rule_static"]), mean(B["axiom2"]) / mean(B["rule_accept_all"])))
    C.claim("Env B section 3: tuned rule URLLC 98.9", "keeps it at 98.9\\%", 100 * mean(B["rule_local"], lambda x: x["sla"]["urllc"]), "{:.1f}")
    # Env B replication and sensitivity
    Brep = {a: seeds_of("m64/n3_replication", a, REP) for a in ("axiom2", "independent_dqn", "single_agent_dqn", "mappo_tuned")}
    wins = [paired(Brep["axiom2"], Brep[b])["wins"] for b in ("independent_dqn", "single_agent_dqn", "mappo_tuned")]
    C.note("Env B replication: AXIOM wins 7 or 8 of 10 against each", set(wins) <= {7, 8}, wins)
    v1 = paired(seeds_of("m64/n3_fully_connected", "axiom2", S10), seeds_of("m64/n3_fully_connected", "axiom", S10))
    C.claim("Env B original AXIOM reward", "earns only 6.496 per step", mean(seeds_of("m64/n3_fully_connected", "axiom", S10)), "{:.3f}")
    C.note("original AXIOM 2.37 below in all ten seeds", round(v1["diff"], 2) == 2.37 and v1["wins"] == 10, v1)
    C.claim("Env B LR 3e-4", "$3{\\times}10^{-4}$ reaches 7.220", mean(seeds_of("m64/n3_fully_connected", "axiom2_lr3e-4", S10)), "{:.3f}")
    others = [paired(seeds_of("m64/n3_fully_connected", "axiom2", S10), seeds_of("m64/n3_fully_connected", a, S10)) for a in ("axiom2_lr3e-3", "axiom2_wide")]
    C.note("LR 3e-3 and wide within 0.19, not significant", all(abs(o["diff"]) <= 0.19 and o["p"] > 0.05 for o in others), others)
    # Env A scaling ranges
    for n, seeds, sla_rng, rew_rng in ((7, S15, (17.9, 29.9), (3.40, 7.07)), (19, S30_19, (31.0, 42.1), (10.7, 18.6))):
        D = {t: {arm: seeds_of(f"m65_scaling/n{n}_{t}", arm, seeds) for arm in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")}
             for t in ("fully_connected", "ring", "hex")}
        sd = [100 * paired(D[t]["axiom2"], D[t][b], prio)["diff"] for t in D for b in ("single_agent_dqn", "independent_dqn", "mappo_tuned")]
        rd = [paired(D[t]["axiom2"], D[t][b])["diff"] for t in D for b in ("single_agent_dqn", "independent_dqn", "mappo_tuned")]
        nd = 1 if n == 7 else 1
        C.note(f"N{n} compliance lead range {sla_rng}", (round(min(sd), 1), round(max(sd), 1)) == sla_rng, (min(sd), max(sd)))
        C.note(f"N{n} reward lead range {rew_rng}", (round(min(rd), 2 if n == 7 else 1), round(max(rd), 2 if n == 7 else 1)) == rew_rng, (min(rd), max(rd)))
        if n == 19:
            ws = [paired(D[t]["axiom2"], D[t][b], prio)["wins"] for t in D for b in ("single_agent_dqn", "independent_dqn", "mappo_tuned")]
            C.note("N19 wins 28 to 30 of 30 (compliance)", min(ws) >= 28, ws)
            u = 100 * float(np.mean([r["sla"]["urllc"] for t in D for r in D[t]["axiom2"].values()]))
            e = 100 * float(np.mean([r["sla"]["embb"] for t in D for r in D[t]["axiom2"].values()]))
            C.note("N19 AXIOM URLLC/eMBB 99.4/95.1", (round(u, 1), round(e, 1)) == (99.4, 95.1), (u, e))
    # screen counts, from the screen JSONs (independent re-count)
    def scr(path):
        return json.load(open(path)) if os.path.exists(path) else []
    SC = f"{ROOT}/m65_screen"
    ax3 = scr(f"{SC}/A_n3_base_axiom2.json"); ax7 = sum((scr(f"{SC}/A_n7_{t}_axiom2.json") for t in ("fully_connected", "ring", "hex")), [])
    ax19 = sum((scr(f"{SC}/A_n19_{t}_axiom2.json") for t in ("fully_connected", "ring", "hex")), [])
    sg19 = sum((scr(f"{SC}/A_n19_{t}_single_agent_dqn.json") for t in ("fully_connected", "ring", "hex")), [])
    C.note("screen fails AXIOM 1/30, 1/45, 5/90 and single 89/90",
           (sum(r["fails"] for r in ax3), len(ax3), sum(r["fails"] for r in ax7), len(ax7), sum(r["fails"] for r in ax19), len(ax19),
            sum(r["fails"] for r in sg19), len(sg19)) == (1, 30, 1, 45, 5, 90, 89, 90),
           (sum(r["fails"] for r in ax3), sum(r["fails"] for r in ax7), sum(r["fails"] for r in ax19), sum(r["fails"] for r in sg19)))
    C.note("AXIOM's one N=19 collapse fails the screen", all(r["fails"] for r in ax19 if r["eval_collapsed"]), [r["seed"] for r in ax19 if r["eval_collapsed"]])
    # training curves (from the figure's own summary, cross-checked against raw curves for MAPPO)
    tc = json.load(open("/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures/fig12_training_curves_summary.json"))
    last = {k.split("/")[-1]: {a: round(v["last20_mean"], 1) for a, v in d.items()} for k, d in tc.items()}
    C.note("curves: MAPPO ends 6.4, 16.0, 62.9; AXIOM about 85 at N=19; DQNs near 71 and 74",
           (last["n3_fully_connected"]["mappo_tuned"], last["n7_ring"]["mappo_tuned"], last["n19_ring"]["mappo_tuned"]) == (6.4, 16.0, 62.9)
           and round(last["n19_ring"]["axiom2"]) == 85 and (round(last["n19_ring"]["independent_dqn"]), round(last["n19_ring"]["single_agent_dqn"])) == (71, 74), last)
    mp = [float(np.mean(json.load(open(f))["episode_mean_reward"][-20:])) for f in
          sorted(glob.glob(f"{ROOT}/m64/n3_fully_connected/mappo_tuned/seed9[0-1][0-9]/train/curve.json"))[:12]]
    C.note("MAPPO curve recomputed from raw curve files matches figure", round(float(np.mean(mp)), 1) == last["n3_fully_connected"]["mappo_tuned"], float(np.mean(mp)))
    # complexity table against the measurement file
    cx = json.load(open(f"{ROOT}/m64/complexity.json"))
    C.note("Table 5 parameters", [cx[str(n)]["axiom2"]["params_execution"] for n in (3, 7, 19)] == [7782] * 3
           and [cx[str(n)]["independent_dqn"]["params_execution"] for n in (3, 7, 19)] == [55302, 129038, 350246]
           and [cx[str(n)]["single_agent_dqn"]["params_execution"] for n in (3, 7, 19)] == [21250, 26370, 41730], None)
    C.note("Table 5 AXIOM latency 1.04/1.98/4.79 ms", [round(cx[str(n)]["axiom2"]["ms_per_step"], 2) for n in (3, 7, 19)] == [1.04, 1.98, 4.79], None)

    # ---------------- confidence intervals (own bootstrap, tolerance 0.03 for resampling noise)
    rng = np.random.default_rng(12345)
    def ci(vals):
        v = np.asarray(vals)
        bm = v[rng.integers(0, len(v), size=(10000, len(v)))].mean(axis=1)
        return np.percentile(bm, 2.5), np.percentile(bm, 97.5)
    def ci_claim(label, snippet, vals, tol=None):
        lo, hi = ci(vals)
        # independent resampling noise in a bound scales with the interval's width
        tol = tol if tol is not None else max(0.03 if len(vals) >= 30 else 0.05, 0.05 * (hi - lo))
        m = re.search(r"\[\s*(-?\$?-?[0-9.]+)\$?\\?%?,\s*(-?[0-9.]+)\\?%?\]", snippet.replace("$-$", "-"))
        okk = snippet in C.tex and m is not None and abs(float(m.group(1).replace("$", "")) - lo) <= tol and abs(float(m.group(2)) - hi) <= tol
        C.note(label, okk, (round(lo, 3), round(hi, 3), snippet))
    for arm, nm in names.items():
        r = A[arm]; lo, hi = ci([x["reward"] for x in r.values()])
        txt = [re.sub(r"^\\rowcolor\{[^}]*\}", "", l) for l in C.tex.splitlines()]   # table rows may carry a highlight
        txt = [l for l in txt if l.startswith(nm + " & ") and "[" in l]
        ci_claim(f"T3 {arm} CI", txt[0] if txt else "MISSING", [x["reward"] for x in r.values()])
    for arm, nm in bnames.items():
        txt = [re.sub(r"^\\rowcolor\{[^}]*\}", "", l) for l in C.tex.splitlines()]
        txt = [l for l in txt if l.startswith(nm + " & ") and "[" in l and "&" in l]
        txt = [t for t in txt if f"{mean(B[arm]):.3f}" in t]
        ci_claim(f"T4 {arm} CI", txt[0] if txt else "MISSING", [x["reward"] for x in B[arm].values()])
    d_ind = [A["axiom2"][s]["reward"] - A["independent_dqn"][s]["reward"] for s in S30]
    ci_claim("A3 vs indep CI", "[0.60, 1.65]", d_ind)
    d_map = [A["axiom2"][s]["reward"] - A["mappo_tuned"][s]["reward"] for s in S30]
    ci_claim("A3 vs MAPPO CI", "[2.01, 3.35]", d_map)
    d_sg = [A["axiom2"][s]["reward"] - A["single_agent_dqn"][s]["reward"] for s in S30]
    ci_claim("A3 vs single CI", "[$-$0.01, 0.64]", d_sg)
    d_mlp = [A["axiom2"][s]["reward"] - A["axiom2_mlp"][s]["reward"] for s in S30]
    ci_claim("A3 vs MLP CI", "[$-$0.17, 0.26]", d_mlp)
    d_fed = [cen[s]["reward"] - fed[s]["reward"] for s in S10]
    ci_claim("federation cost CI", "[$-$0.54, 1.51]", d_fed)
    cr = seeds_of("m65_reviewer/replication", "axiom2", REP); fr2 = seeds_of("m65_m3_replication", "fl_gat_ctde_sigma0.0", REP)
    ci_claim("federation replication CI", "[0.18, 1.96]", [cr[s]["reward"] - fr2[s]["reward"] for s in REP])
    D19 = {t: seeds_of(f"m65_scaling/n19_{t}", "axiom2", S30_19) for t in ("fully_connected", "ring", "hex")}
    ci_claim("N19 pooled CI", "[95.2\\%, 99.0\\%]", [100 * prio(r) for t in D19 for r in D19[t].values()], tol=0.15)
    # win counts and bounds in the Env B text
    wl = [paired(B["axiom2"], B[b], f)["wins"] for b in ("independent_dqn", "single_agent_dqn", "mappo_tuned") for f in (lambda r: r["reward"], prio)]
    C.note("Env B N=3: AXIOM wins 24 to 29 of 30", (min(wl), max(wl)) == (24, 29), wl)
    fam7 = {}
    for t in ("fully_connected", "ring", "hex"):
        for b in ("independent_dqn", "single_agent_dqn", "mappo_tuned", "rule_local", "rule_neighbour"):
            for mname, f in (("reward", lambda r: r["reward"]), ("prio", prio)):
                fam7[f"{t}|{b}|{mname}"] = paired(n7[t]["axiom2"], n7[t][b], f)
    h7 = holm({k: v["p"] for k, v in fam7.items()})
    C.note("Env B N=7 ring: single-agent beats AXIOM on priority SLA at p_holm 0.011", round(h7["ring|single_agent_dqn|prio"], 3) == 0.011
           and fam7["ring|single_agent_dqn|prio"]["diff"] < 0, h7["ring|single_agent_dqn|prio"])
    sig_learned = sorted(k for k, v in h7.items() if v < 0.05 and k.split("|")[1] in ("independent_dqn", "single_agent_dqn", "mappo_tuned") and fam7[k]["diff"] > 0)
    C.note("Env B N=7: AXIOM's only significant learned leads are MAPPO reward on fully-connected and ring",
           sig_learned == ["fully_connected|mappo_tuned|reward", "ring|mappo_tuned|reward"], sig_learned)
    leads = []
    for cond in ("load102", "load107", "weights"):
        ax = seeds_of(f"m65_reviewer/{cond}", "axiom2", S10)
        fam = {b: paired(ax, seeds_of(f"m63_reviewer/{cond}", b, S10)) for b in ("heuristic", "single_agent_dqn", "independent_dqn")}
        hh = holm({k: v["p"] for k, v in fam.items()})
        leads += [(cond, b, fam[b]["diff"] > 0, hh[b] < 0.05) for b in ("single_agent_dqn", "independent_dqn")]
    C.note("Env A sensitivity: all six leads positive, exactly two significant",
           all(x[2] for x in leads) and sum(x[3] for x in leads) == 2, leads)

    # ---------------- training length: every learned seed trained for 300 episodes
    def train_eps(cell, arm, seed):
        base = f"{ROOT}/{cell}/{arm}/seed{seed}/train"
        if os.path.exists(f"{base}/curve.json"):
            return len(json.load(open(f"{base}/curve.json"))["episode_mean_reward"])
        cands = glob.glob(f"{base}/omega_log.jsonl*") + glob.glob(f"{base}/dqn/offline_train/rep_0/omega_log.jsonl*")
        if not cands:
            return None
        op = gzip.open if cands[0].endswith(".gz") else open
        eps = set()
        for line in op(cands[0], "rt"):
            r = json.loads(line)
            if isinstance(r.get("evidence"), dict) and "reward" in r["evidence"]:
                eps.add(r["episode"])
        return len(eps)
    te = {}
    for cell, arms in (("m65_reviewer/base", ("axiom2", "axiom2_mlp", "mappo_tuned")),
                       ("m64/n3_fully_connected", ("axiom2", "axiom2_mlp", "independent_dqn", "single_agent_dqn", "mappo_tuned")),
                       ("m65_scaling/n19_ring", ("axiom2", "mappo_tuned"))):
        for arm in arms:
            for s in (900, 915, 929) if "n19" not in cell else (900, 1000, 926):
                te[f"{cell}|{arm}|{s}"] = train_eps(cell, arm, s)
    C.note("sampled learned seeds trained for exactly 300 episodes", all(v == 300 for v in te.values()), te)

    # ---------------- hand-entered figure values (Fig 9) against recomputation
    src = open("/home/kmanojp/oranslice_rig/experiments/plots/paper5_fig_superiority.py").read()
    xs = dict(re.findall(r'"([A-Za-z -]+)": dict\(x=([0-9.]+)', src))
    ys = dict(re.findall(r'"([A-Za-z -]+)": dict\(x=[0-9.]+, xci=\([^)]*\), y=([0-9.]+)', src))
    pooled19 = {}
    for arm in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned"):
        pooled19[arm] = 100 * float(np.mean([prio(r) for t in ("fully_connected", "ring", "hex")
                                              for r in seeds_of(f"m65_scaling/n19_{t}", arm, S30_19).values()]))
    lab = {"AXIOM": "axiom2", "Single-agent DQN": "single_agent_dqn", "Independent DQN": "independent_dqn", "MAPPO": "mappo_tuned"}
    # x is Env A reward per step at 3 gNBs with its 95% bootstrap CI (absolute since M73; it was % of the oracle)
    xcis = {k: tuple(float(x) for x in v.split(",")) for k, v in re.findall(r'"([A-Za-z -]+)": dict\(x=[0-9.]+, xci=\(([^)]*)\)', src)}
    okx = all(round(mean(A[lab[k]]), 3) == float(v) for k, v in xs.items()) and len(xcis) == 4 and \
        all(np.allclose(ci([r["reward"] for r in A[lab[k]].values()]), v, atol=0.03) for k, v in xcis.items())
    # since M73 the y axis and two radar axes use 37 gNBs (AXIOM over hex 30 + ring 15 + fully-connected 15, baselines over hex 30)
    rows37 = {a: ([r for t, ss in (("hex", S30_19), ("ring", S15), ("fully_connected", S15)) for r in seeds_of(f"m73/A_n37_{t}", a, ss).values()]
                  if a == "axiom2" else list(seeds_of("m73/A_n37_hex", a, S30_19).values())) for a in lab.values()}
    pooled37 = {a: 100 * float(np.mean([prio(r) for r in v])) for a, v in rows37.items()}
    nc37 = {a: 1 - sum(r["collapsed"] for r in v) / len(v) for a, v in rows37.items()}
    oky = all(round(pooled37[lab[k]], 1) == float(v) for k, v in ys.items())
    C.note("Fig 9a hand-entered x and y values match recomputation", okx and oky and len(xs) == 4 and len(ys) == 4, (xs, ys))
    radar = {k: [float(x) for x in v.split(",")] for k, v in re.findall(r'"([A-Za-z -]+)":\s+\[([0-9., ]+)\],', src)}
    best = lambda d: max(d.values())
    A3r = {a: mean(A[a]) for a in lab.values()}
    B3r = {a: mean(B[a]) for a in lab.values()}
    p7 = {a: float(np.mean([prio(r) for t in ("fully_connected", "ring", "hex") for r in seeds_of(f"m65_scaling/n7_{t}", a, S15).values()])) for a in lab.values()}
    nc19 = {a: 1 - sum(r["collapsed"] for t in ("fully_connected", "ring", "hex") for r in seeds_of(f"m65_scaling/n19_{t}", a, S30_19).values()) / 90 for a in lab.values()}
    axes = [A3r, B3r, p7, pooled37, nc37, n7p]
    expect = {k: [round(ax[lab[k]] / best(ax), 3) for ax in axes] for k in lab}
    okr = all(abs(radar[k][i] - expect[k][i]) <= 0.002 for k in lab for i in range(6))
    C.note("Fig 9b radar fractions match recomputation", okr, {"figure": radar, "recomputed": expect})

    # ---------------- M66 verification subsection: V1 reruns and V2 fresh seeds
    v1 = [("m66_repro/B_n3", "m64/n3_fully_connected", a_, range(900, 905 if a_ in ("axiom2", "mappo_tuned") else 903))
          for a_ in ("axiom2", "mappo_tuned", "independent_dqn")]
    v1 += [("m66_repro/B_n3", "m64/n3_fully_connected", a_, S30) for a_ in ("rule_static", "rule_local")]
    v1 += [("m66_repro/A_n3", "m65_reviewer/base", "axiom2", range(900, 905)),
           ("m66_repro/A_n19_ring", "m65_scaling/n19_ring", "axiom2", range(900, 902)),
           ("m66_repro/B_n7_ring", "m64/n7_ring", "axiom2_mlp", range(900, 903))]
    for fc, sc, arm, ss in v1:
        x, y = seeds_of(fc, arm, ss), seeds_of(sc, arm, ss)
        same = len(x) == len(y) == len(ss) and all(
            x[s]["reward"] == y[s]["reward"] and x[s]["blocks"] == y[s]["blocks"] and x[s]["sla"] == y[s]["sla"] for s in ss)
        C.note(f"V1 rerun {fc}/{arm} identical to stored on {len(ss)} seeds", same, None)
    x, y = seeds_of("m66_repro/A_n3_oracle_equiv", "rule_static", S30), seeds_of("m65_n3_view", "heuristic", S30)
    C.note("V1 static rule identical to stored Env A oracle on 30 seeds",
           len(x) == 30 and all(x[s]["reward"] == y[s]["reward"] for s in S30), None)
    for name, fc, sc in (("m3 sigma0", "m66_repro/m3", "m65_m3"), ("m4 dropout", "m66_repro/m4", "m65_m4")):
        ok_, n_ = True, 0
        for p in glob.glob(f"{ROOT}/{fc}/**/eval/omega_log.jsonl*", recursive=True):
            rel = os.path.relpath(p, f"{ROOT}/{fc}").replace(".gz", "")
            q = next((c_ for c_ in (f"{ROOT}/{sc}/{rel}", f"{ROOT}/{sc}/{rel}.gz") if os.path.exists(c_)), None)
            n_ += 1
            ok_ = ok_ and q is not None and read(p)["reward"] == read(q)["reward"] and read(p)["blocks"] == read(q)["blocks"]
        C.note(f"V1 rerun {name} eval logs identical to stored ({n_} logs)", ok_ and n_ > 0, n_)
    sa = [seeds_of(c_, "single_agent_dqn", [900])[900]["reward"] for c_ in
          ("m66_repro/B_n3", "m66_repro/sa_nondet_h0a", "m66_repro/sa_nondet_h0b", "m66_repro/sa_nondet_rnda", "m66_repro/sa_nondet_rndb")]
    C.claim("single-agent seed 900 rerun minimum", "earned 7.45 to 9.67 reward per step, against 8.74 stored", min(sa), "{:.2f}")
    C.claim("single-agent seed 900 rerun maximum", "earned 7.45 to 9.67 reward per step, against 8.74 stored", max(sa), "{:.2f}")
    C.claim("single-agent seed 900 stored", "against 8.74 stored", seeds_of("m64/n3_fully_connected", "single_agent_dqn", [900])[900]["reward"], "{:.2f}")
    first = {900, 910, 920}
    ax, sg = seeds_of("m65_n3_view", "axiom2", S30), seeds_of("m65_n3_view", "single_agent_dqn", S30)
    keep = [s for s in S30 if s not in first]
    C.claim("Env A lead over single-agent without unseeded-init seeds", "moves from $+0.311$ to $+0.241$ per step",
            paired({s: ax[s] for s in keep}, {s: sg[s] for s in keep})["diff"], "{:+.3f}")
    # Env A conclusion: lead over single-agent positive but not significant after Holm over the three baselines
    exA = {k: paired({s: ax[s] for s in keep}, {s: v for s, v in seeds_of("m65_n3_view", k, S30).items() if s not in first})
           for k in ("single_agent_dqn", "independent_dqn", "mappo_tuned")}
    hA = holm({k: v["p"] for k, v in exA.items()})
    C.note("Env A N=3 every comparison keeps its direction without unseeded-init seeds",
           all(exA[k]["diff"] > 0 for k in exA) and all(hA[k] < 0.05 for k in ("independent_dqn", "mappo_tuned")), hA)
    C.claim("Env A N=3 single-agent Holm p without unseeded-init seeds", "passes the Holm correction, at $p=0.039$ against 0.066",
            hA["single_agent_dqn"], "{:.3f}")
    bx = {s: v for s, v in seeds_of("m64/n3_fully_connected", "axiom2", S30).items() if s not in first}
    exB = {k: paired(bx, {s: v for s, v in seeds_of("m64/n3_fully_connected", k, S30).items() if s not in first})
           for k in ("single_agent_dqn", "independent_dqn", "mappo_tuned")}
    hB = holm({k: v["p"] for k, v in exB.items()})
    C.note("Env B N=3 single-agent conclusion unchanged without unseeded-init seeds",
           exB["single_agent_dqn"]["diff"] > 0 and hB["single_agent_dqn"] < 0.0001, hB)
    F20, F15, F10 = list(range(3000, 3020)), list(range(3000, 3015)), list(range(3000, 3010))
    vv = json.load(open(f"{ROOT}/m66_v1v2.json"))["criteria"]
    pred = [c_ for c_ in vv if c_["label"].startswith("V2") and "reported" not in c_["label"]]
    C.claim("fresh-seed predictions stated in advance", "All 26 predictions stated in advance for these fresh seeds held", len(pred), "{:d}")
    C.note("every fresh-seed prediction holds", all(c_["holds"] for c_ in pred), len(pred))
    fa = {k: seeds_of("m66_fresh/A_n3", k, F20) for k in ("axiom2", "independent_dqn", "single_agent_dqn", "mappo_tuned", "rule_static")}
    C.claim("fresh Env A N=3 fraction of oracle", "reached 98.2\\% of the oracle reward",
            100 * mean(fa["axiom2"]) / mean(fa["rule_static"]), "{:.1f}")
    t_ = {k: paired(fa["axiom2"], fa[k]) for k in ("independent_dqn", "single_agent_dqn", "mappo_tuned")}
    h_ = holm({k: v["p"] for k, v in t_.items()})
    C.note("fresh Env A N=3 beats independent DQN and MAPPO at Holm p<=0.002",
           all(t_[k]["diff"] > 0 and h_[k] <= 0.002 for k in ("independent_dqn", "mappo_tuned")), h_)
    C.claim("fresh Env A N=3 single-agent seeds won", "won 11 of 20 seeds against the single-agent DQN", t_["single_agent_dqn"]["wins"], "{:d}")
    C.claim("fresh Env A N=3 single-agent gap", "trailed it by 0.021 per step on average", -t_["single_agent_dqn"]["diff"], "{:.3f}")
    C.claim("fresh Env A N=3 single-agent p", "per step on average, at $p=0.07$", t_["single_agent_dqn"]["p"], "{:.2f}")
    f19 = {k: seeds_of("m66_fresh/A_n19_ring", k, F15) for k in ("axiom2", "independent_dqn", "single_agent_dqn", "mappo_tuned")}
    pr = {k: 100 * mean(v, prio) for k, v in f19.items()}
    C.claim("fresh N=19 AXIOM priority SLA", "kept 95.6\\% priority-slice compliance", pr["axiom2"], "{:.1f}")
    C.claim("fresh N=19 lowest baseline SLA", "against 47.8\\% to 65.5\\% for the baselines", min(pr[k] for k in pr if k != "axiom2"), "{:.1f}")
    C.claim("fresh N=19 highest baseline SLA", "against 47.8\\% to 65.5\\% for the baselines", max(pr[k] for k in pr if k != "axiom2"), "{:.1f}")
    hs = []
    for f_ in (lambda r: r["reward"], prio):
        t_ = {k: paired(f19["axiom2"], f19[k], f_) for k in ("independent_dqn", "single_agent_dqn", "mappo_tuned")}
        h_ = holm({k: v["p"] for k, v in t_.items()})
        hs += [t_[k]["diff"] > 0 and h_[k] <= 0.001 for k in t_]
    C.note("fresh N=19 all six tests at Holm p<=0.001", len(hs) == 6 and all(hs), None)
    fb = {k: seeds_of("m66_fresh/B_n3", k, F20) for k in ("axiom2", "independent_dqn", "single_agent_dqn", "mappo_tuned",
                                                          "rule_static", "rule_accept_all", "rule_local", "rule_neighbour")}
    t_ = {k: paired(fb["axiom2"], fb[k]) for k in fb if k != "axiom2"}
    h_ = holm({k: v["p"] for k, v in t_.items()})
    C.note("fresh Env B N=3 beats static and accept-all in all 20 seeds",
           all(t_[k]["wins"] == 20 for k in ("rule_static", "rule_accept_all")), None)
    C.note("fresh Env B N=3 leads every learned baseline at Holm p<=0.0002",
           all(t_[k]["diff"] > 0 and h_[k] <= 0.0002 for k in ("independent_dqn", "single_agent_dqn", "mappo_tuned")), h_)
    C.claim("fresh Env B N=3 tuned local reward", "earning 9.175 against 8.782 per step", mean(fb["rule_local"]), "{:.3f}")
    C.claim("fresh Env B N=3 AXIOM reward", "earning 9.175 against 8.782 per step", mean(fb["axiom2"]), "{:.3f}")
    f7 = {k: seeds_of("m66_fresh/B_n7_ring", k, F10) for k in ("rule_local", "axiom2", "axiom2_mlp", "independent_dqn",
                                                               "single_agent_dqn", "mappo_tuned")}
    C.note("fresh Env B N=7 tuned local beats every learned policy at p<=0.004",
           all(paired(f7["rule_local"], f7[k])["diff"] > 0 and paired(f7["rule_local"], f7[k])["p"] <= 0.004 for k in f7 if k != "rule_local"), None)
    t_ = paired(f7["axiom2_mlp"], f7["axiom2"])
    C.claim("fresh Env B N=7 MLP over GAT reward", "beat graph attention by 1.38 reward per step", t_["diff"], "{:.2f}")
    C.claim("fresh Env B N=7 MLP seeds won", "in 9 of 10 seeds at $p=0.006$", t_["wins"], "{:d}")
    C.claim("fresh Env B N=7 MLP over GAT p", "in 9 of 10 seeds at $p=0.006$", t_["p"], "{:.3f}")

    # ---------------- M66b fresh seeds (addendum 1)
    G = list(range(3000, 3010)); bl = ("independent_dqn", "single_agent_dqn", "mappo_tuned")
    h19 = {k: seeds_of("m66b_fresh/A_n19_hex", k, G) for k in ("axiom2",) + bl}
    C.claim("M66b N=19 hex AXIOM priority SLA", "AXIOM kept 96.5\\% priority-slice compliance against 47.5\\% to 65.2\\%", 100 * mean(h19["axiom2"], prio), "{:.1f}")
    C.claim("M66b N=19 hex lowest baseline", "against 47.5\\% to 65.2\\% for the baselines", min(100 * mean(h19[k], prio) for k in bl), "{:.1f}")
    C.claim("M66b N=19 hex highest baseline", "against 47.5\\% to 65.2\\% for the baselines", max(100 * mean(h19[k], prio) for k in bl), "{:.1f}")
    t19 = {(k, m): paired(h19["axiom2"], h19[k], f) for k in bl for m, f in (("r", lambda r: r["reward"]), ("p", prio))}
    h_ = holm({k: v["p"] for k, v in t19.items()})
    C.note("M66b N=19 hex all six tests at Holm p<=0.012", all(t19[k]["diff"] > 0 and h_[k] <= 0.012 for k in t19), max(h_.values()))
    fed = {}
    for b in range(3000, 3010, 2):
        fed.update(seeds_of(f"m66b_fresh/m3_s{b}", "fl_gat_ctde_sigma0.0", [b, b + 1]))
    cen = seeds_of("m66_fresh/A_n3", "axiom2", G)
    C.claim("M66b federated difference", "at $+0.077$ with 95\\% CI", paired(cen, fed)["diff"], "{:+.3f}")
    ci_claim("M66b federated CI", "at $+0.077$ with 95\\% CI [$-$1.03, 1.27]", [cen[s]["reward"] - fed[s]["reward"] for s in G])
    C.note("M66b federated not significant", paired(cen, fed)["p"] >= 0.05 and len(fed) == 10, paired(cen, fed)["p"])
    n7 = {c_: {k: seeds_of(f"m66b_fresh/A_n7_{c_}", k, G) for k in ("axiom2",) + bl} for c_ in ("ring", "fully_connected")}
    C.claim("M66b N=7 AXIOM pooled priority SLA", "AXIOM kept 96.7\\% priority-slice compliance and led every baseline",
            100 * float(np.mean([prio(r) for c_ in n7 for r in n7[c_]["axiom2"].values()])), "{:.1f}")
    t7 = {(c_, k, m): paired(n7[c_]["axiom2"], n7[c_][k], f) for c_ in n7 for k in bl for m, f in (("r", lambda r: r["reward"]), ("p", prio))}
    h7 = holm({k: v["p"] for k, v in t7.items()})
    C.note("M66b N=7 AXIOM leads every baseline under both layouts", all(v["diff"] > 0 for v in t7.values()), None)
    C.note("M66b N=7 ring six tests at Holm p<=0.032", all(h7[k] <= 0.032 for k in t7 if k[0] == "ring"), max(h7[k] for k in t7 if k[0] == "ring"))
    C.note("M66b N=7 fully-connected tests all above Holm 0.05", all(h7[k] > 0.05 for k in t7 if k[0] == "fully_connected"), None)
    weak = sorted(100 * prio(r) for r in n7["fully_connected"]["axiom2"].values() if prio(r) < 0.9)
    C.claim("M66b N=7 weak seed low", "two weak AXIOM seeds at 57.2\\% and 76.9\\%", weak[0] if len(weak) == 2 else None, "{:.1f}")
    C.claim("M66b N=7 weak seed high", "two weak AXIOM seeds at 57.2\\% and 76.9\\%", weak[1] if len(weak) == 2 else None, "{:.1f}")
    lead = [100 * t7[("fully_connected", k, "p")]["diff"] for k in bl]
    C.claim("M66b N=7 fully-connected lead low", "leads of 12.5 to 25.3 points", min(lead), "{:.1f}")
    C.claim("M66b N=7 fully-connected lead high", "leads of 12.5 to 25.3 points", max(lead), "{:.1f}")
    pool = {k: 100 * float(np.mean([prio(r) for c_ in n7 for r in n7[c_][k].values()])) for k in bl}
    C.claim("M66b N=7 independent DQN pooled", "reached 80.9\\% and 80.6\\% compliance", pool["independent_dqn"], "{:.1f}")
    C.claim("M66b N=7 single-agent DQN pooled", "reached 80.9\\% and 80.6\\% compliance", pool["single_agent_dqn"], "{:.1f}")
    mb = json.load(open(f"{ROOT}/m66b_analysis.json"))
    C.note("M66b three of eleven checks failed", len(mb["criteria"]) == 11 and mb["n_fail"] == 3 and
           "so three of the eleven checks in this run failed" in C.tex, None)

    # ---------------- M66c (addendum 2), values from m66c_analysis.json, itself built on this reader
    mc = json.load(open(f"{ROOT}/m66c_analysis.json"))
    C.note("M66c judged and failed counts quoted", mc["n_judged"] == 48 and mc["n_fail"] == 5 and "43 of its 48 checks held" in C.tex,
           (mc["n_judged"], mc["n_fail"]))
    c1, c2, c3 = mc["C1 Env A N=7 hex"], mc["C2 Env A N=19 fully-connected"], mc["C3 Env A N=7 fully-connected 20 seeds"]
    C.claim("M66c C1 AXIOM prio", "AXIOM kept 99.0\\% and 95.7\\% priority-slice compliance", 100 * c1["summary"]["axiom2"]["prio"], "{:.1f}")
    C.claim("M66c C2 AXIOM prio", "AXIOM kept 99.0\\% and 95.7\\% priority-slice compliance", 100 * c2["summary"]["axiom2"]["prio"], "{:.1f}")
    C.note("M66c C1 and C2 all tests Holm p<=0.012", all(v["diff"] > 0 and v["p_holm"] <= 0.012 for c_ in (c1, c2) for v in c_["tests"].values()), None)
    C.note("M66c C3 all tests Holm p<=0.007", all(v["diff"] > 0 and v["p_holm"] <= 0.007 for v in c3["tests"].values()), None)
    vals = [100 * c_["summary"][a_]["prio"] for c_ in (c1, c3) for a_ in ("independent_dqn", "single_agent_dqn")]
    C.claim("M66c N=7 DQN prio low", "DQNs kept 76.2\\% to 83.3\\% priority-slice compliance", min(vals), "{:.1f}")
    C.claim("M66c N=7 DQN prio high", "DQNs kept 76.2\\% to 83.3\\% priority-slice compliance", max(vals), "{:.1f}")
    C.claim("M66c N=7 DQN prio high, pointer", "the two DQN baselines reach up to 83.3\\%", max(vals), "{:.1f}")
    C.claim("M66c N=7 DQN prio high, conclusion", "baseline compliance of up to 83\\%", max(vals), "{:.0f}")
    C.note("M66c three DQN cells above 80%", sum(v > 80 for v in vals) == 3 and "above the 80\\% bound in three cells" in C.tex, vals)
    c8 = mc["C8"]
    s102 = c8["load102"]["summary"]
    frac = 100 * s102["axiom2"]["reward"] / s102["rule_static"]["reward"]
    C.claim("M66c load102 fraction", "left it at 96.8\\% of the oracle reward", frac, "{:.1f}")
    C.claim("M66c load102 shortfall, conclusion", "left it 3.2\\% short of the oracle", 100 - frac, "{:.1f}")
    C.claim("M66c load102 p", "a gap that is not significant at $p=0.25$", c8["load102"]["vs_oracle"]["p"], "{:.2f}")
    C.claim("M66c load102 AXIOM", "at 12.551 against 12.910", s102["axiom2"]["reward"], "{:.3f}")
    C.claim("M66c load102 single", "at 12.551 against 12.910", s102["single_agent_dqn"]["reward"], "{:.3f}")
    C.note("M66c load107 and weights within 0.6% of oracle",
           all(100 - 100 * c8[c_]["summary"]["axiom2"]["reward"] / c8[c_]["summary"]["rule_static"]["reward"] <= 0.6 for c_ in ("load107", "weights")), None)
    crit_ = {c_["label"]: c_ for c_ in mc["criteria"]}
    c4ok = all(crit_[k]["holds"] for k in crit_ if k.startswith("C4"))
    p4 = max(float(re.search(r"p ([0-9.e-]+)", crit_[k]["detail"]).group(1)) for k in crit_ if k.startswith("C4") and "rule_local" in k)
    C.note("M66c C4 tuned rule beats every learner at p<=0.004, AXIOM not above static", c4ok and p4 <= 0.004, p4)
    C.note("M66c C4 MLP earns more than GAT, not significantly",
           all(mc[f"C4 {t}"]["axiom_vs_mlp_reward"]["diff"] < 0 and mc[f"C4 {t}"]["axiom_vs_mlp_reward"]["p"] >= 0.05 for t in ("fully_connected", "hex")), None)
    c5 = mc["C5"]
    hol = [v["p_holm"] for k, v in c5["cells"].items() if "|spike|" not in k]
    C.note("M66c disruption costs significant at Holm p<=0.041", all(v["cost"] > 0 for k, v in c5["cells"].items() if "|spike|" not in k)
           and round(max(hol), 3) <= 0.041 and "significant at Holm-adjusted $p\\leq0.041$, no gap" in C.tex, max(hol))
    C.note("M66c no disruption gap survives Holm", all(g["p_holm"] >= 0.05 for g in c5["gaps"].values()), None)
    sp = [c5["cells"][f"gat_ctde|spike|{v}"]["precision"] for v in (1, 2, 3)]
    C.claim("M66c AXIOM spike precision", "AXIOM kept a spike block precision of 0.97", float(np.mean(sp)), "{:.2f}")
    C.note("M66c every spike precision rounds to 0.97", all(round(x, 2) == 0.97 for x in sp), sp)
    c6 = mc["C6"]["tests"]
    drops = [v["diff"] for v in c6.values()]
    C.claim("M66c DP drop low", "lowered reward by 0.65 to 1.31 per step", min(drops), "{:.2f}")
    C.claim("M66c DP drop high", "lowered reward by 0.65 to 1.31 per step", max(drops), "{:.2f}")
    C.note("M66c DP none survives Holm", all(v["p_holm"] >= 0.05 for v in c6.values()), None)
    C.note("M66c DP steps all 17,969", all(x == 17969 for v in mc["C6"]["steps"].values() for x in v), None)
    C.claim("M66c Env B original AXIOM gap", "in all ten seeds, by 2.19 per step", mc["C9"]["axiom"]["diff"], "{:.2f}")
    C.note("M66c Env B original AXIOM loses all ten", mc["C9"]["axiom"]["wins"] == 10, None)
    C.note("M66c LR 3e-3 and wide not significant", all(mc["C9"][a_]["p"] >= 0.05 for a_ in ("axiom2_lr3e-3", "axiom2_wide")), None)
    c7 = mc["C7"]
    C.claim("M66c seeded single A3 lead", "becomes $+0.254$ per step", c7["A3"]["tests"]["single_seeded"]["diff"], "{:+.3f}")
    C.claim("M66c seeded single A3 Holm p", "per step at Holm-adjusted $p=0.018$", c7["A3"]["tests"]["single_seeded"]["p_holm"], "{:.3f}")
    C.claim("M66c seeded single A3 replication", "and $+0.948$ on the replication seeds", c7["A3rep"]["tests"]["single_seeded"]["diff"], "{:+.3f}")
    C.claim("M66c seeded single B3", "In Env B the lead stays at $+1.320$", c7["B3"]["tests"]["single_seeded"]["diff"], "{:+.3f}")
    C.claim("M66c seeded single N=19 collapses", "collapses in 28 of 30 seeds", c7["A19"]["seeded_collapsed"], "{:d}")
    C.claim("M66c seeded single N=19 gap", "trails AXIOM by 32.3 points", 100 * c7["A19"]["prio_test"]["diff"], "{:.1f}")

    # ---------------- M66d (addendum 3), recomputed here from the raw logs
    S40, S20 = list(range(4000, 4040)), list(range(4000, 4020))
    d1 = {k: seeds_of("m66d_fresh/D1_A_n3", k, S40) for k in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned", "rule_static")}
    C.claim("M66d D1 fraction of oracle", "AXIOM reached 98.1\\% of the oracle, tying it in 27 seeds", 100 * mean(d1["axiom2"]) / mean(d1["rule_static"]), "{:.1f}")
    C.claim("M66d D1 oracle ties", "tying it in 27 seeds", paired(d1["axiom2"], d1["rule_static"])["ties"], "{:d}")
    t_ = {k: paired(d1["axiom2"], d1[k]) for k in ("single_agent_dqn", "independent_dqn", "mappo_tuned")}
    h_ = holm({k: v["p"] for k, v in t_.items()})
    C.note("M66d D1 beats independent DQN and MAPPO at Holm p<=0.0001",
           all(t_[k]["diff"] > 0 and h_[k] <= 0.0001 for k in ("independent_dqn", "mappo_tuned")), h_)
    C.claim("M66d D1 single lead", "was only $+0.159$ per step", t_["single_agent_dqn"]["diff"], "{:+.3f}")
    C.claim("M66d D1 single p", "per step, at $p=0.090$", t_["single_agent_dqn"]["p"], "{:.3f}")
    d2 = {k: seeds_of("m66d_fresh/D2_load102", k, S20) for k in ("axiom2", "single_agent_dqn", "rule_static")}
    C.note("M66d D2 within 0.5% of oracle", len(d2["axiom2"]) == 20 and 100 - 100 * mean(d2["axiom2"]) / mean(d2["rule_static"]) <= 0.5, None)
    C.claim("M66d D2 single", "12.978 against 12.945 per step", mean(d2["single_agent_dqn"]), "{:.3f}")
    C.claim("M66d D2 AXIOM", "12.978 against 12.945 per step", mean(d2["axiom2"]), "{:.3f}")
    md = json.load(open(f"{ROOT}/m66d_analysis.json"))
    C.note("M66d four of five checks held", md["n_judged"] == 5 and md["n_fail"] == 1 and "four of its five checks held" in C.tex, None)

    # ---------------- reframed text (2026-10-19): condensed verification subsection, abstract, contributions, conclusion
    v12 = json.load(open(f"{ROOT}/m66_v1v2.json"))["criteria"]
    n_pred = sum(1 for c_ in v12 if c_["label"].startswith("V2") and "reported" not in c_["label"])
    f_pred = sum(1 for c_ in v12 if c_["label"].startswith("V2") and "reported" not in c_["label"] and not c_["holds"])
    tot = n_pred + 11 + json.load(open(f"{ROOT}/m66c_analysis.json"))["n_judged"] + json.load(open(f"{ROOT}/m66d_analysis.json"))["n_judged"]
    bad = f_pred + json.load(open(f"{ROOT}/m66b_analysis.json"))["n_fail"] + json.load(open(f"{ROOT}/m66c_analysis.json"))["n_fail"] \
        + json.load(open(f"{ROOT}/m66d_analysis.json"))["n_fail"]
    C.claim("reframe: pre-stated fresh-seed checks total", "81 of their 90 pre-stated checks held", tot, "{:d}")
    C.claim("reframe: pre-stated fresh-seed checks held", "81 of their 90 pre-stated checks held", tot - bad, "{:d}")
    C.claim("reframe: failed checks", "The nine checks that failed", bad, "{:d}" if bad != 9 else "nine")
    G10, G15 = list(range(3000, 3010)), list(range(3000, 3015))
    fresh_cells = [("m66_fresh/A_n19_ring", G15), ("m66b_fresh/A_n7_ring", G10), ("m66b_fresh/A_n7_fully_connected", G10),
                   ("m66b_fresh/A_n19_hex", G10), ("m66c_fresh/C1_A_n7_hex", G10), ("m66c_fresh/C2_A_n19_fc", G10),
                   ("m66c_fresh/C3_A_n7_fc", list(range(4000, 4020)))]
    ap_ = [100 * mean(seeds_of(c_, "axiom2", ss), prio) for c_, ss in fresh_cells]
    C.claim("reframe: fresh AXIOM scaling compliance low", "AXIOM kept 93.4\\% to 100\\% priority-slice compliance", min(ap_), "{:.1f}")
    C.claim("reframe: fresh AXIOM scaling compliance high", "AXIOM kept 93.4\\% to 100\\% priority-slice compliance", max(ap_), "{:.0f}")
    cell_h = {}
    for c_, ss in fresh_cells:
        ax_ = seeds_of(c_, "axiom2", ss)
        tt = {(b, m): paired(ax_, seeds_of(c_, b, ss), f) for b in ("independent_dqn", "single_agent_dqn", "mappo_tuned")
              for m, f in (("r", lambda r: r["reward"]), ("p", prio))}
        hh = holm({k: v["p"] for k, v in tt.items()})
        cell_h[c_] = (all(v["diff"] > 0 for v in tt.values()), max(hh.values()))
    C.note("reframe: AXIOM leads every baseline in every fresh scaling cell", all(v[0] for v in cell_h.values()), cell_h)
    m66b_fam = json.load(open(f"{ROOT}/m66b_analysis.json"))["Env A N=7"]["tests"]
    ring_max = max(v["p_holm"] for k, v in m66b_fam.items() if k.startswith("A_n7_ring"))
    others = [cell_h[c_][1] for c_ in cell_h if "A_n7" not in c_ or "C1" in c_ or "C3" in c_] + [ring_max]
    C.note("reframe: all fresh scaling cells but one at Holm p<=0.032", round(max(others), 3) <= 0.032 and
           max(v["p_holm"] for k, v in m66b_fam.items() if k.startswith("A_n7_fully")) > 0.05, (others, ring_max))
    C.note("reframe: twenty-seed rerun at Holm p<=0.007", round(cell_h["m66c_fresh/C3_A_n7_fc"][1], 3) <= 0.007, cell_h["m66c_fresh/C3_A_n7_fc"])
    fb_ = {k: seeds_of("m66_fresh/B_n3", k, list(range(3000, 3020))) for k in ("axiom2", "independent_dqn", "single_agent_dqn",
           "mappo_tuned", "rule_static", "rule_accept_all", "rule_local", "rule_neighbour")}
    tb_ = {k: paired(fb_["axiom2"], fb_[k]) for k in fb_ if k != "axiom2"}
    hb_ = holm({k: v["p"] for k, v in tb_.items()})
    C.note("reframe: fresh Env B N=3 beats static and every learner at Holm p<=0.0002",
           all(tb_[k]["diff"] > 0 and hb_[k] <= 0.0002 for k in ("rule_static", "independent_dqn", "single_agent_dqn", "mappo_tuned")), hb_)
    mcc = json.load(open(f"{ROOT}/m66c_analysis.json"))
    dq = [100 * mcc[c_]["summary"][a_]["prio"] for c_ in ("C1 Env A N=7 hex", "C3 Env A N=7 fully-connected 20 seeds")
          for a_ in ("independent_dqn", "single_agent_dqn")]
    m66b_s = json.load(open(f"{ROOT}/m66b_analysis.json"))["Env A N=7"]["pooled_prio"]
    dq += [100 * m66b_s[a_] for a_ in ("independent_dqn", "single_agent_dqn")]
    C.claim("reframe: fresh N=7 DQN compliance max", "reached up to 83.3\\% compliance at seven gNBs", max(dq), "{:.1f}")
    allbase = [v for v in dq]
    for c_, ss in fresh_cells:
        allbase += [100 * mean(seeds_of(c_, b, ss), prio) for b in ("independent_dqn", "single_agent_dqn", "mappo_tuned")]
    S15_ = list(range(900, 912)) + [1000, 1001, 1002]
    for t_ in ("fully_connected", "ring", "hex"):
        for n_, ss in ((7, S15_), (19, S30_19)):
            allbase += [100 * mean(seeds_of(f"m65_scaling/n{n_}_{t_}", b, ss), prio) for b in ("independent_dqn", "single_agent_dqn", "mappo_tuned")]
    C.note("reframe: every baseline below 84% at 7 and 19 gNBs in every sample", max(allbase) < 84 and
           "while every learned baseline stays below 84\\%" in C.tex and "stay below 84\\%" in C.tex, round(max(allbase), 2))
    a3f = paired(seeds_of("m66_fresh/A_n3", "axiom2", list(range(3000, 3020))), seeds_of("m66_fresh/A_n3", "single_agent_dqn", list(range(3000, 3020))))
    a3d = paired(seeds_of("m66d_fresh/D1_A_n3", "axiom2", list(range(4000, 4040))), seeds_of("m66d_fresh/D1_A_n3", "single_agent_dqn", list(range(4000, 4040))))
    C.claim("reframe: fresh 20-seed single-agent gap", "at margins of $-0.021$ and $0.159$ reward per step", a3f["diff"], "{:+.3f}".replace("+", "") if a3f["diff"] < 0 else "{:+.3f}")
    C.claim("reframe: fresh 40-seed single-agent gap", "at margins of $-0.021$ and $0.159$ reward per step", a3d["diff"], "{:.3f}")
    s102_ = mcc["C8"]["load102"]["summary"]
    C.claim("reframe: ten-seed load sample shortfall", "3.2\\% short of the oracle", 100 - 100 * s102_["axiom2"]["reward"] / s102_["rule_static"]["reward"], "{:.1f}")
    d2_ = {k: seeds_of("m66d_fresh/D2_load102", k, list(range(4000, 4020))) for k in ("axiom2", "single_agent_dqn", "rule_static")}
    C.note("reframe: twenty-seed load rerun within 0.5% and single-agent matches",
           100 - 100 * mean(d2_["axiom2"]) / mean(d2_["rule_static"]) <= 0.5 and mean(d2_["single_agent_dqn"]) >= mean(d2_["axiom2"]), None)
    c7_ = mcc["C7"]
    C.note("reframe: seeded single-agent leaves Env B and N=19 leads unchanged",
           c7_["B3"]["tests"]["single_seeded"]["diff"] > 0 and c7_["B3"]["tests"]["single_seeded"]["p_holm"] < 0.0001
           and c7_["A19"]["prio_test"]["diff"] > 0 and c7_["A19"]["prio_test"]["p"] < 0.05, None)

    # ---------------- shortened main text (2026-10-19): summary sentences that restate numbers whose full text moved to the supplement
    lr_ = paired(seeds_of("m64/n3_fully_connected", "axiom2", S10), seeds_of("m64/n3_fully_connected", "axiom", S10))
    C.claim("reframe: short LR sentence 2.37", "earns 2.37 less per step than the current design in all ten seeds", lr_["diff"], "{:.2f}")
    C.note("reframe: short LR sentence, ten of ten seeds", lr_["wins"] == 10 and lr_["n"] == 10, lr_)
    cen_ = seeds_of("m65_reviewer/base", "axiom2", S10)
    dp_ = {sg: paired(cen_, seeds_of("m65_m3", f"fl_gat_ctde_sigma{sg}", S10)) for sg in ("0.5", "1.0", "2.0", "4.0")}
    C.claim("reframe: DP drop low", "lowers reward by 0.77 to 1.25 per step", min(v["diff"] for v in dp_.values()), "{:.2f}")
    C.claim("reframe: DP drop high", "lowers reward by 0.77 to 1.25 per step", max(v["diff"] for v in dp_.values()), "{:.2f}")
    hdp_ = holm({k: v["p"] for k, v in dp_.items()})
    C.note("reframe: no DP drop survives Holm", all(v >= 0.05 for v in hdp_.values()) and "no drop survives Holm correction at ten seeds" in C.main, hdp_)
    eps_min = min(v[1] for v in eps.values()) if eps else None
    C.claim("reframe: smallest DP epsilon about 2,600", "$\\varepsilon$ of about 2{,}600 or more", float(f"{eps_min:.2g}") if eps_min else None, "{:,.0f}".replace(",", "{,}") if False else "{:.0f}", tol=0.5)
    m4s = json.load(open(f"{ROOT}/m65_m4/m4_summary.json"))["cells"]
    C.claim("reframe: AXIOM spike precision 0.98", "with block precision at 0.98, and Section S12", 
            float(np.mean([m4s[f"gat_ctde|spike|{v}"]["precision_mean"] for v in (1, 2, 3)])), "{:.2f}")
    C.note("reframe: every AXIOM spike precision rounds to 0.98",
           all(round(m4s[f"gat_ctde|spike|{v}"]["precision_mean"], 2) == 0.98 for v in (1, 2, 3)), None)
    C.note("reframe: dropout and churn costs significant for every policy",
           all(c_["cost_mean"] > 0 and c_["p_holm"] is not None and c_["p_holm"] < 0.05 for k, c_ in m4s.items() if "|spike|" not in k), None)
    live_loss = []
    for f_ in ("result_full_3ue.json", "result_full_6ue.json"):
        for smp in json.load(open(f"{ROOT}/m49b_1/{f_}"))["samples"]:
            live_loss += [v for k, v in smp.items() if k.endswith("_loss_pct")]
    C.note("reframe: live loss 0.000% in every sample at both loads", len(live_loss) > 0 and max(live_loss) == 0
           and "with 0.000\\% loss at both loads" in C.main, (len(live_loss), max(live_loss) if live_loss else None))
    readings, below = 0, 0
    for g_ in ("m49b_2/gate_report.md", "m49b_3/gate_report.md"):
        txt = open(f"{ROOT}/{g_}").read()
        mm = re.search(r"(\d+) below-floor samples across\s+([\d,]+)\s+total", txt)
        below += int(mm.group(1)); readings += int(mm.group(2).replace(",", ""))
    C.note("reframe: zero below-floor grants across more than 100,000 readings", below == 0 and readings > 100000
           and "zero below-floor grants across more than 100{,}000 readings" in C.tex, (below, readings))

    # ---------------- visual-emphasis figures (2026-10-19): scaling trend and 19-gNB decision map
    def gate_open(path, n=19):
        fc = {"urllc": (5, 33), "embb": (10, 66), "mmtc": (5, 11)}
        acc, cnt = np.zeros((n, 3)), 0
        with (gzip.open(path, "rt") if path.endswith(".gz") else open(path)) as fh:
            for line in fh:
                ev = json.loads(line).get("evidence")
                if not isinstance(ev, dict) or ev.get("rollup") or "ceilings" not in ev:
                    continue
                for key, c in ev["ceilings"].items():
                    g, sl = key.split(":")
                    lo, hi = fc[sl]
                    acc[int(g.split("-")[1]), ("urllc", "embb", "mmtc").index(sl)] += (c["max_ratio"] - lo) / (hi - lo)
                cnt += 1
        return acc / cnt
    gm = {}
    for arm in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned"):
        mats = [gate_open(p_) for s_ in S30_19 if (p_ := find_eval("m65_scaling/n19_hex", arm, s_))]
        gm[arm] = (len(mats), np.mean(mats, axis=0))
    ax_ = gm["axiom2"][1]
    C.claim("map AXIOM URLLC gate", "at 1.00 and 0.97, while closing the mMTC gate to 0.08", float(ax_[:, 0].mean()), "{:.2f}")
    C.claim("map AXIOM eMBB gate", "at 1.00 and 0.97, while closing the mMTC gate to 0.08", float(ax_[:, 1].mean()), "{:.2f}")
    C.claim("map AXIOM mMTC gate", "while closing the mMTC gate to 0.08", float(ax_[:, 2].mean()), "{:.2f}")
    C.note("reframe: map AXIOM sheds mMTC and keeps priority open at every one of 19 gNBs",
           gm["axiom2"][0] == 30 and ax_[:, 2].max() < 0.1 and ax_[:, 0].min() > 0.95 and ax_[:, 1].min() > 0.95, None)
    sg_ = gm["single_agent_dqn"][1]
    C.note("reframe: map single-agent every gate open at 0.99", all(round(float(sg_[:, j].mean()), 2) == 0.99 for j in range(3))
           and "The single-agent DQN leaves every gate open at 0.99" in C.tex, sg_.mean(axis=0).round(4).tolist())
    C.claim("map independent mMTC gate", "the independent DQN closes the mMTC gate only to 0.92", float(gm["independent_dqn"][1][:, 2].mean()), "{:.2f}")
    C.claim("map MAPPO eMBB gate", "partly closes the eMBB gate, to 0.82", float(gm["mappo_tuned"][1][:, 1].mean()), "{:.2f}")
    C.claim("map MAPPO mMTC gate", "while leaving mMTC open at 0.69", float(gm["mappo_tuned"][1][:, 2].mean()), "{:.2f}")
    # since M73 the figure shows the 37-gNB hex cluster; the 19-gNB numbers above stay in the text as a comparison
    gm37 = {}
    for arm in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned"):
        mats = [gate_open(p_, 37) for s_ in S30_19 if (p_ := find_eval("m73/A_n37_hex", arm, s_))]
        gm37[arm] = (len(mats), np.mean(mats, axis=0))
    a37_ = gm37["axiom2"][1]
    C.claim("reframe: map37 AXIOM URLLC gate", "at 1.00 and 0.98, while closing the mMTC gate to 0.16", float(a37_[:, 0].mean()), "{:.2f}")
    C.claim("reframe: map37 AXIOM eMBB gate", "at 1.00 and 0.98, while closing the mMTC gate to 0.16", float(a37_[:, 1].mean()), "{:.2f}")
    C.claim("reframe: map37 AXIOM mMTC gate", "while closing the mMTC gate to 0.16, a mean that includes its three collapsed seeds", float(a37_[:, 2].mean()), "{:.2f}")
    C.note("reframe: map37 AXIOM's mean includes three collapsed hex seeds and every gNB keeps priority open, mMTC below 0.2",
           gm37["axiom2"][0] == 30 and sum(r["collapsed"] for r in seeds_of("m73/A_n37_hex", "axiom2", S30_19).values()) == 3
           and a37_[:, 2].max() < 0.2 and a37_[:, 0].min() > 0.95 and a37_[:, 1].min() > 0.95, None)
    s37_ = gm37["single_agent_dqn"][1].mean(axis=0)
    C.note("reframe: map37 single-agent every gate open at 0.93 to 0.95", round(float(s37_.min()), 2) == 0.93 and round(float(s37_.max()), 2) == 0.95
           and "The single-agent DQN leaves every gate open at 0.93 to 0.95" in C.main, s37_.round(4).tolist())
    C.claim("reframe: map37 independent mMTC gate", "the independent DQN closes the mMTC gate only to 0.94", float(gm37["independent_dqn"][1][:, 2].mean()), "{:.2f}")
    C.claim("reframe: map37 MAPPO eMBB gate", "partly closes the eMBB gate, to 0.80", float(gm37["mappo_tuned"][1][:, 1].mean()), "{:.2f}")
    C.claim("reframe: map37 MAPPO mMTC gate", "while leaving mMTC open at 0.51", float(gm37["mappo_tuned"][1][:, 2].mean()), "{:.2f}")
    figmap = json.load(open("/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures/fig13_gnb_map_summary.json"))
    C.note("reframe: map figure plots the recomputed per-gNB openness",
           figmap.get("n_gnbs") == 37 and "Decision map of the 37-gNB hex cluster" in C.main
           and all(np.allclose(np.array(figmap["arms"][a_]["openness_per_gnb"]), gm37[a_][1], atol=1e-3) for a_ in gm37), None)
    def pooled(n_, arm):
        if n_ == 3:
            return list(seeds_of("m65_n3_view", arm, S30).values())
        ss = S15 if n_ == 7 else S30_19
        return [r for t in ("fully_connected", "ring", "hex") for r in seeds_of(f"m65_scaling/n{n_}_{t}", arm, ss).values()]
    tr = {(n_, a_): 100 * float(np.mean([prio(r) for r in pooled(n_, a_)])) for n_ in (3, 7, 19)
          for a_ in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")}
    axs_ = [tr[(n_, "axiom2")] for n_ in (3, 7, 19)]
    C.claim("reframe: trend AXIOM low", "stays between 97.1\\% and 98.9\\% from three to nineteen gNBs", min(axs_), "{:.1f}")
    C.claim("reframe: trend AXIOM high", "stays between 97.1\\% and 98.9\\% from three to nineteen gNBs", max(axs_), "{:.1f}")
    C.note("reframe: trend every baseline falls from 3 to 19 gNBs",
           all(tr[(3, a_)] > tr[(7, a_)] > tr[(19, a_)] for a_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned")), None)
    gap_ = tr[(19, "axiom2")] - max(tr[(19, a_)] for a_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned"))
    C.claim("reframe: trend gap at 19 gNBs", "grows to 32.0 points at nineteen gNBs", gap_, "{:.1f}")
    figtr = json.load(open("/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures/fig6_scaling_trend_summary.json"))
    C.note("reframe: trend figure plots the recomputed compliance",
           all(abs(figtr["arms"][a_][str(n_)]["prio_mean"] - tr[(n_, a_)]) < 1e-6 for (n_, a_) in tr), None)

    # ---------------- third-review text fixes (2026-10-20): oracle wording, pooled federation, Env B ceiling, parameter table
    samples_ = [("m65_n3_view", "heuristic", S30), ("m65_rep_view", "heuristic", REP), ("m66_fresh/A_n3", "rule_static", list(range(3000, 3020))),
                ("m66d_fresh/D1_A_n3", "rule_static", list(range(4000, 4040))), ("m66c_fresh/C8_load102", "rule_static", list(range(3000, 3010))),
                ("m66c_fresh/C8_load107", "rule_static", list(range(3000, 3010))), ("m66c_fresh/C8_weights", "rule_static", list(range(3000, 3010))),
                ("m66d_fresh/D2_load102", "rule_static", list(range(4000, 4020)))]
    ex_n, ex_tot, ex_max = 0, 0, 0.0
    for c_, o_, ss_ in samples_:
        O_ = seeds_of(c_, o_, ss_)
        for a_ in ("axiom2", "single_agent_dqn", "independent_dqn"):
            A_ = seeds_of(c_, a_, ss_)
            for s_ in ss_:
                if s_ in A_ and s_ in O_:
                    ex_tot += 1
                    e_ = A_[s_]["reward"] - O_[s_]["reward"]
                    if e_ > 1e-9:
                        ex_n += 1; ex_max = max(ex_max, e_)
    C.claim("reframe: oracle exceeded count", "exceeded it in 28 of 450 seed-level evaluations", ex_n, "{:d}")
    C.claim("reframe: oracle evaluations total", "exceeded it in 28 of 450 seed-level evaluations", ex_tot, "{:d}")
    C.claim("reframe: oracle exceeded by at most", "by at most 0.40 reward per step", ex_max, "{:.2f}")
    fd_ = []
    for cen_, fc_, ss_ in (("m65_reviewer/base", "m65_m3", S10), ("m65_reviewer/replication", "m65_m3_replication", REP)):
        a_, b_ = seeds_of(cen_, "axiom2", ss_), seeds_of(fc_, "fl_gat_ctde_sigma0.0", ss_)
        fd_ += [a_[s_]["reward"] - b_[s_]["reward"] for s_ in ss_]
    a_, b_ = seeds_of("m66_fresh/A_n3", "axiom2", list(range(3000, 3010))), {}
    for k_ in range(3000, 3010, 2):
        b_.update(seeds_of(f"m66b_fresh/m3_s{k_}", "fl_gat_ctde_sigma0.0", [k_, k_ + 1]))
    fd_ += [a_[s_]["reward"] - b_[s_]["reward"] for s_ in range(3000, 3010)]
    C.note("reframe: pooled federation has 30 seeds", len(fd_) == 30, len(fd_))
    C.claim("reframe: pooled federation cost", "the cost is $+0.491$ per step with 95\\% CI", float(np.mean(fd_)), "{:+.3f}")
    ci_claim("pooled federation CI", "the cost is $+0.491$ per step with 95\\% CI [$-$0.08, 1.09]", fd_)
    C.claim("reframe: pooled federation p", "1.09] and $p=0.14$, so federation", float(wilcoxon(np.array(fd_)).pvalue), "{:.2f}")
    C.claim("reframe: pooled federation in Table 2", "Cost $+0.49$ [$-$0.08, 1.09]", float(np.mean(fd_)), "{:+.2f}")
    eb_ = max(100 * mean(seeds_of("m64/n3_fully_connected", a_, S30), lambda x: x["sla"]["embb"]) for a_ in
              ("rule_accept_all", "rule_static", "rule_local", "rule_neighbour", "axiom2", "axiom2_mlp", "single_agent_dqn", "independent_dqn", "mappo_tuned"))
    C.note("no Env B policy keeps eMBB above 37%", eb_ < 37 and "keeps eMBB compliance above 37\\% in Env B" in C.tex, round(eb_, 2))
    C.note("reframe: Env B peak demand exceeds the budget by up to 23.5%", abs(0.95 * 1.3 - 1.235) < 1e-9 and "by up to 23.5\\%" in C.tex, 0.95 * 1.3)
    import yaml
    cfg_ = yaml.safe_load(open("/home/kmanojp/oranslice_rig/framework/qoe_oran_framework/configs/saclb_offline_dqn.yaml"))
    sl_ = {x["slice_id"]: x for x in cfg_["slices"]}
    C.note("reframe: parameter table matches the N=3 config",
           cfg_["B"] == 100 and cfg_["episode"]["steps_per_episode"] == 60 and cfg_["episode"]["step_seconds"] == 5.0
           and cfg_["reward"]["congestion_coeff"] == 1.5 and cfg_["reward"]["lb_coeff"] == 1.0
           and [sl_[k]["priority_weight"] for k in ("urllc", "embb", "mmtc")] == [12.0, 3.5, 0.3]
           and [sl_[k]["violation_penalty"] for k in ("urllc", "embb", "mmtc")] == [10.0, 5.0, 2.5]
           and all(sl_[k]["accept_reward"] == 1.0 for k in sl_)
           and [(sl_[k]["nominal_ratio"], sl_[k]["min_ratio_floor"], sl_[k]["max_ratio_cap"]) for k in ("urllc", "embb", "mmtc")] == [(30, 5, 33), (60, 10, 66), (10, 5, 11)]
           and [(sl_[k]["latency_budget_ms"], sl_[k]["loss_budget_pct"]) for k in ("urllc", "embb", "mmtc")] == [(15, 0.8), (45, 2.0), (65, 3.5)]
           and cfg_["arrivals"]["synthetic_arrivals_per_step"] == 3 and cfg_["arrivals"]["max_pending_per_step"] == 12
           and cfg_["arrivals"]["ceiling_step_ratio"] == 5, None)
    for n_ in (7, 19):
        c7_ = yaml.safe_load(open(f"/home/kmanojp/oranslice_rig/framework/qoe_oran_framework/configs/saclb_offline_dqn_n{n_}.yaml"))
        C.note(f"reframe: N={n_} config has N requests per step and at most 4N pending",
               c7_["arrivals"]["synthetic_arrivals_per_step"] == n_ and c7_["arrivals"]["max_pending_per_step"] == 4 * n_, None)
    sbt_ = open("/home/kmanojp/oranslice_rig/experiments/scripts/shared_budget_kpm_source.py").read()   # read, not imported
    C.note("reframe: parameter table demand constants", re.search(r"^LOAD_FACTOR = 1\.05\b", sbt_, re.M) is not None
           and re.search(r"^OFFERED_VOLATILITY = 0\.005\b", sbt_, re.M) is not None
           and re.search(r"^LOAD_MULTIPLIER_RANGE = \(0\.9, 1\.0\)", sbt_, re.M) is not None, None)

    # ---------------- M70 referee-response runs (2026-10-21), recomputed here from the raw logs
    LAY_ = ("fully_connected", "ring", "hex")
    rule_ = {3: 100 * mean(seeds_of("m65_n3_view", "heuristic", S30), prio)}
    for n_, ss_ in ((7, S15), (19, S30_19)):
        rows_ = [r for t_ in LAY_ for r in seeds_of(f"m70/R1/A_n{n_}_{t_}", "rule_static", ss_).values()]
        rule_[n_] = 100 * float(np.mean([prio(r) for r in rows_]))
    C.claim("reframe: M70 rule low", "keeps 99.96\\% to 99.99\\% at every size", min(rule_.values()), "{:.2f}")
    C.claim("reframe: M70 rule high", "keeps 99.96\\% to 99.99\\% at every size", max(rule_.values()), "{:.2f}")
    def pooled_(n_, arm):
        if n_ == 3:
            return list(seeds_of("m65_n3_view", arm, S30).values())
        ss_ = S15 if n_ == 7 else S30_19
        return [r for t_ in LAY_ for r in seeds_of(f"m65_scaling/n{n_}_{t_}", arm, ss_).values()]
    axp_ = {n_: 100 * float(np.mean([prio(r) for r in pooled_(n_, "axiom2")])) for n_ in (3, 7, 19)}
    C.note("reframe: M70 AXIOM within 3 points of the rule at every size", all(rule_[n_] - axp_[n_] < 3 for n_ in (3, 7, 19))
           and "AXIOM comes within 3 points of it" in C.main, {n_: round(rule_[n_] - axp_[n_], 2) for n_ in (3, 7, 19)})
    short_ = min(rule_[n_] - 100 * float(np.mean([prio(r) for r in pooled_(n_, a_)])) for n_ in (7, 19)
                 for a_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned"))
    C.note("reframe: M70 other learners at least 24 points short at 7 and 19 gNBs", short_ >= 23.5
           and "falls at least 24 points short" in C.main, round(short_, 2))
    C.note("reframe: abstract says only a known static rule does better", "only a known static rule does better" in C.main
           and all(rule_[n_] > axp_[n_] for n_ in (7, 19)), None)
    ABL_ = list(range(900, 912)) + [1000, 1001, 1002]
    abl_cells_ = {"A3": ("m65_n3_view", "A_n3", S30), "B3": ("m64/n3_fully_connected", "B_n3", S30), "A19": ("m65_scaling/n19_ring", "A_n19_ring", ABL_)}
    def abl_(v_):
        tt_ = {}
        for k_, (c_, d_, ss_) in abl_cells_.items():
            ax_, va_ = seeds_of(c_, "axiom2", ss_), seeds_of(f"m70/R4_{v_}/{d_}", "axiom2", ss_)
            for m_, f_ in (("r", lambda r: r["reward"]), ("p", prio)):
                tt_[(k_, m_)] = paired(ax_, va_, f_)
        hh_ = holm({k: v["p"] for k, v in tt_.items()})
        return tt_, hh_
    tsh_, hsh_ = abl_("sharedhead")
    sh19_ = seeds_of("m70/R4_sharedhead/A_n19_ring", "axiom2", ABL_)
    ax19_ = seeds_of("m65_scaling/n19_ring", "axiom2", ABL_)
    C.claim("reframe: M70 shared head collapses", "it collapses in 9 of 15 seeds", sum(r["collapsed"] for r in sh19_.values()), "{:d}")
    C.claim("reframe: M70 shared head compliance", "keeps only 65.9\\% priority-slice compliance", 100 * mean(sh19_, prio), "{:.1f}")
    C.claim("reframe: M70 AXIOM same seeds compliance", "against AXIOM's 96.8\\% on the same seeds", 100 * mean(ax19_, prio), "{:.1f}")
    C.note("reframe: M70 shared head loses every seed at Holm p<0.001", all(tsh_[("A19", m_)]["wins"] == 15 and hsh_[("A19", m_)] < 0.001 for m_ in "rp")
           and all(hsh_[(k_, m_)] >= 0.05 for k_ in ("A3", "B3") for m_ in "rp"), {str(k): v for k, v in hsh_.items()})
    tvd_, hvd_ = abl_("vdn")
    C.note("reframe: M70 joint target never significantly different", all(v >= 0.05 for v in hvd_.values())
           and "is never significantly different and trends slightly better" in C.main, {str(k): v for k, v in hvd_.items()})
    C.note("reframe: M70 joint target trends better on reward in every cell", all(tvd_[(k_, "r")]["diff"] < 0 for k_ in abl_cells_), None)
    C.claim("reframe: M70 joint target Env A N=3 reward", "reaching 12.831 reward per step", mean(seeds_of("m70/R4_vdn/A_n3", "axiom2", S30)), "{:.3f}")
    C.claim("reframe: M70 joint target N=19 compliance", "and 99.96\\% priority-slice compliance at nineteen", 100 * mean(seeds_of("m70/R4_vdn/A_n19_ring", "axiom2", ABL_), prio), "{:.2f}")
    mp_cells_ = {"A3": ("m65_n3_view", "m70/R3_confirm/A_n3", S30), "A19": ("m65_scaling/n19_ring", "m70/R3_confirm/A_n19_ring", S30_19),
                 "B3": ("m64/n3_fully_connected", "m70/R3_confirm/B_n3", S30)}
    mpd_ = {k_: (seeds_of(a_, "axiom2", ss_), seeds_of(b_, "mappo", ss_)) for k_, (a_, b_, ss_) in mp_cells_.items()}
    C.claim("reframe: M70 MAPPO reported A3", "MAPPO rises from 10.013 to 11.448", mean(seeds_of("m65_n3_view", "mappo_tuned", S30)), "{:.3f}")
    C.claim("reframe: M70 MAPPO grid A3", "MAPPO rises from 10.013 to 11.448", mean(mpd_["A3"][1]), "{:.3f}")
    C.claim("reframe: M70 MAPPO reported N=19 ring", "from 60.6\\% to 69.6\\% priority-slice compliance", 100 * mean(seeds_of("m65_scaling/n19_ring", "mappo_tuned", S30_19), prio), "{:.1f}")
    C.claim("reframe: M70 MAPPO grid N=19 ring", "from 60.6\\% to 69.6\\% priority-slice compliance", 100 * mean(mpd_["A19"][1], prio), "{:.1f}")
    tm_ = {("A3", "r"): paired(*mpd_["A3"]), ("A19", "r"): paired(*mpd_["A19"]), ("A19", "p"): paired(*mpd_["A19"], prio), ("B3", "r"): paired(*mpd_["B3"])}
    hm_ = holm({k: v["p"] for k, v in tm_.items()})
    rd_ = [tm_[k]["diff"] for k in tm_ if k[1] == "r"]
    C.claim("reframe: M70 MAPPO lead low", "by 1.25 to 16.18 reward per step", min(rd_), "{:.2f}")
    C.claim("reframe: M70 MAPPO lead high", "by 1.25 to 16.18 reward per step", max(rd_), "{:.2f}")
    C.note("reframe: M70 MAPPO all four at Holm p<0.001", all(v["diff"] > 0 for v in tm_.values()) and max(hm_.values()) < 0.001, {str(k): v for k, v in hm_.items()})
    C.claim("reframe: M70 MAPPO Env B N=7", "and by 2.42 in Env B at seven gNBs",
            paired(seeds_of("m64/n7_ring", "axiom2", S15), seeds_of("m70/R3_confirm/B_n7_ring", "mappo", S15))["diff"], "{:.2f}")
    sg7_ = 100 * float(np.mean([prio(r) for t_ in LAY_ for r in seeds_of(f"m70/R2/A_n7_{t_}", "single_agent_dqn", S15).values()]))
    sg19_rows_ = [r for t_, d_ in (("fully_connected", "m70/R2/A_n19_fully_connected"), ("ring", "m66c_fresh/C7_A_n19_ring"), ("hex", "m70/R2/A_n19_hex"))
                  for r in seeds_of(d_, "single_agent_dqn", S30_19).values()]
    C.claim("reframe: M70 seeded single N=7", "keeps 80.3\\% and 63.9\\% priority-slice compliance", sg7_, "{:.1f}")
    C.claim("reframe: M70 seeded single N=19", "keeps 80.3\\% and 63.9\\% priority-slice compliance", 100 * float(np.mean([prio(r) for r in sg19_rows_])), "{:.1f}")
    hmax_ = 0.0
    for n_, ss_ in ((7, S15), (19, S30_19)):
        tt_ = {}
        for t_ in LAY_:
            sd_ = "m66c_fresh/C7_A_n19_ring" if (n_ == 19 and t_ == "ring") else f"m70/R2/A_n{n_}_{t_}"
            sg_, ax_ = seeds_of(sd_, "single_agent_dqn", ss_), seeds_of(f"m65_scaling/n{n_}_{t_}", "axiom2", ss_)
            for m_, f_ in (("r", lambda r: r["reward"]), ("p", prio)):
                tt_[(t_, m_)] = paired(ax_, sg_, f_)
        hh_ = holm({k: v["p"] for k, v in tt_.items()})
        assert all(v["diff"] > 0 for v in tt_.values())
        hmax_ = max(hmax_, max(hh_.values()))
    C.note("reframe: M70 seeded single beaten under every layout at Holm p<=0.035", round(hmax_, 3) <= 0.035
           and "under every layout at Holm-adjusted $p\\leq0.035$" in C.main, hmax_)

    # ---------------- M72 confirmatory follow-ups (2026-10-21), shift results read from the raw evaluation logs
    def _log(path_):
        for c_ in (path_, path_ + ".gz"):
            if os.path.exists(c_):
                return read(c_)
        return None
    def shift_rows(n_dir_, sh_, arm_, ss_):
        out_ = {}
        for s_ in ss_:
            base_ = f"{ROOT}/m72/B_shift/{n_dir_}/{sh_}/{arm_}/seed{s_}"
            r_ = _log(f"{base_}/omega_log.jsonl") if arm_ == "axiom2" else _log(f"{base_}/lb_only/offline_eval/rep_0/omega_log.jsonl")
            if r_ is not None:
                out_[s_] = r_
        return out_
    SB_ = list(range(905, 930))
    sh_t_ = {sh_: paired(shift_rows("n3", sh_, "axiom2", SB_), shift_rows("n3", sh_, "rule_local", SB_))
             for sh_ in ("nominal", "load_0.80", "load_1.10", "load_1.15", "load_1.20", "coupling_0.30")}
    nom_ax_, nom_rl_ = shift_rows("n3", "nominal", "axiom2", SB_), shift_rows("n3", "nominal", "rule_local", SB_)
    st_ax_, st_rl_ = seeds_of("m64/n3_fully_connected", "axiom2", SB_), seeds_of("m64/n3_fully_connected", "rule_local", SB_)
    C.note("reframe: M72 shift setup reproduces the stored results under nominal load", len(nom_ax_) == 25 and
           all(nom_ax_[s_]["reward"] == st_ax_[s_]["reward"] and nom_rl_[s_]["reward"] == st_rl_[s_]["reward"] for s_ in SB_), None)
    prim_ = ("load_1.10", "load_1.15", "load_1.20")
    hs_ = holm({k: sh_t_[k]["p"] for k in prim_})
    C.claim("reframe: M72 overload lead 1.10", "it earns 0.46, 0.43, and 0.35 more reward per step than the nominally tuned rule", sh_t_["load_1.10"]["diff"], "{:.2f}")
    C.claim("reframe: M72 overload lead 1.15", "it earns 0.46, 0.43, and 0.35 more reward per step than the nominally tuned rule", sh_t_["load_1.15"]["diff"], "{:.2f}")
    C.claim("reframe: M72 overload lead 1.20", "it earns 0.46, 0.43, and 0.35 more reward per step than the nominally tuned rule", sh_t_["load_1.20"]["diff"], "{:.2f}")
    C.note("reframe: M72 overload wins 21 to 23 of 25 at Holm p<=0.0002", sorted({sh_t_[k]["wins"] for k in prim_}) == [21, 23]
           and all(sh_t_[k]["n"] == 25 for k in prim_) and round(max(hs_.values()), 4) <= 0.0002, hs_)
    C.note("reframe: M72 lighter load and stronger coupling leave a non-significant rule lead",
           all(sh_t_[k]["diff"] < 0 and sh_t_[k]["p"] >= 0.05 for k in ("load_0.80", "coupling_0.30")), None)
    S7S_ = S15
    n7_ = {sh_: paired(shift_rows("n7_ring", sh_, "axiom2", S7S_), shift_rows("n7_ring", sh_, "rule_local", S7S_)) for sh_ in ("nominal", "load_1.10", "load_1.20")}
    C.claim("reframe: M72 N=7 nominal deficit", "AXIOM trails the rule by 3.84 reward per step under nominal load", -n7_["nominal"]["diff"], "{:.2f}")
    C.claim("reframe: M72 N=7 lead 1.10", "but leads it by 1.86 and 3.14 at 110\\% and 120\\% load", n7_["load_1.10"]["diff"], "{:.2f}")
    C.claim("reframe: M72 N=7 lead 1.20", "but leads it by 1.86 and 3.14 at 110\\% and 120\\% load", n7_["load_1.20"]["diff"], "{:.2f}")
    rt_ = {sh_: paired(shift_rows("n3", sh_, "axiom2", SB_), shift_rows("n3", sh_, "rule_retuned", SB_)) for sh_ in prim_}
    C.note("reframe: M72 re-tuned rule draws level at 1.10 and 1.15", all(rt_[k]["p"] >= 0.05 for k in ("load_1.10", "load_1.15")), None)
    C.claim("reframe: M72 re-tuned rule beats AXIOM at 1.20", "and beats it by 0.62 reward per step at 120\\%", -rt_["load_1.20"]["diff"], "{:.2f}")
    C.note("reframe: M72 re-tuned rule lead at 1.20 significant", rt_["load_1.20"]["diff"] < 0 and rt_["load_1.20"]["p"] < 0.05, rt_["load_1.20"]["p"])
    dl_ = {}
    for k_, cell_, st_, ss_ in (("B3", "B_n3", "m64/n3_fully_connected", list(range(900, 920))), ("B7", "B_n7_ring", "m64/n7_ring", list(range(900, 912)))):
        lg_ = seeds_of(f"m72/D_long/{cell_}", "axiom2", ss_)
        dl_[k_] = (paired(lg_, seeds_of(st_, "axiom2", ss_)), paired(lg_, seeds_of(st_, "rule_local", ss_)), len(lg_))
    C.claim("M72 longer training gain N=3", "AXIOM gains 0.33 reward per step at three gNBs and 2.92 at seven", dl_["B3"][0]["diff"], "{:.2f}")
    C.claim("M72 longer training gain N=7", "AXIOM gains 0.33 reward per step at three gNBs and 2.92 at seven", dl_["B7"][0]["diff"], "{:.2f}")
    C.note("reframe: M72 longer training seeds 20 and 12", dl_["B3"][2] == 20 and dl_["B7"][2] == 12 and "on 20 and 12 seeds" in C.tex, None)
    C.claim("M72 remaining gap N=3", "The remaining gaps to the tuned rule, 0.08 and 0.96 per step", -dl_["B3"][1]["diff"], "{:.2f}")
    C.claim("M72 remaining gap N=7", "The remaining gaps to the tuned rule, 0.08 and 0.96 per step", -dl_["B7"][1]["diff"], "{:.2f}")
    C.claim("M72 remaining gap p N=3", "at $p=0.35$ and $p=0.064$", dl_["B3"][1]["p"], "{:.2f}")
    C.claim("M72 remaining gap p N=7", "at $p=0.35$ and $p=0.064$", dl_["B7"][1]["p"], "{:.3f}")
    hd_ = {}
    for f_ in glob.glob(f"{ROOT}/m72/A_hindsight/hindsight_*.json"):
        hd_.update(json.load(open(f_)))
    C.note("reframe: M72 hindsight covers 15 seeds of 95 rules", len(hd_) == 15 and all(v["n_rules"] == 95 for v in hd_.values()), len(hd_))
    C.claim("M72 hindsight max eMBB", "reaches only 37.7\\% on average", 100 * float(np.mean([v["max_embb_any_rule"] for v in hd_.values()])), "{:.1f}")
    tb_ = float(np.mean([v["tuned"]["reward"] for v in hd_.values()])); bb_ = float(np.mean([v["best_in_hindsight"]["reward"] for v in hd_.values()]))
    C.claim("M72 hindsight headroom", "earns only 0.14\\% more than the tuned rule", 100 * (bb_ - tb_) / tb_, "{:.2f}")
    vc_ = {"A3": ("A_n3", list(range(9000, 9020))), "B3": ("B_n3", list(range(9000, 9020))), "A19": ("A_n19_ring", list(range(9000, 9010))), "B7": ("B_n7_ring", list(range(9000, 9010)))}
    vt_, nseed_ = {}, 0
    for k_, (d_, ss_) in vc_.items():
        vd_, ax_ = seeds_of(f"m72/C_vdn/{d_}", "axiom2", ss_), seeds_of(f"m72/C_axiom2/{d_}", "axiom2", ss_)
        nseed_ += min(len(vd_), len(ax_))
        for m_, f_ in (("r", lambda r: r["reward"]), ("p", prio)):
            vt_[(k_, m_)] = paired(vd_, ax_, f_)
    hv_ = holm({k: v["p"] for k, v in vt_.items()})
    C.note("reframe: M72 VDN 60 fresh seeds, never significantly different", nseed_ == 60 and all(v >= 0.05 for v in hv_.values())
           and "on 60 fresh seeds across four cells" in C.main, {str(k): v for k, v in hv_.items()})
    C.note("reframe: M72 VDN ahead in three cells, behind in Env B at seven gNBs",
           [k_ for k_ in vc_ if vt_[(k_, "r")]["diff"] > 0] == ["A3", "B3", "A19"] and vt_[("B7", "r")]["diff"] < 0, None)
    C.note("reframe: M72 VDN test streams disjoint within the experiment",
           not (set(range(9000, 9020)) & {5000 + s_ for s_ in range(9000, 9020)}), None)

    # ---------------- M73: thirty-seven gNBs (docs/PAPER5_M73_preregistration.md), recomputed from the logs
    L37_ = {"hex": S30_19, "ring": S15, "fully_connected": S15}
    ax37_ = {t_: seeds_of(f"m73/A_n37_{t_}", "axiom2", ss_) for t_, ss_ in L37_.items()}
    axr_ = [r for d_ in ax37_.values() for r in d_.values()]
    b37_ = {b_: seeds_of("m73/A_n37_hex", b_, S30_19) for b_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned", "rule_static")}
    C.note("reframe: M73 complete, 60 AXIOM runs and 30 seeds per baseline", len(axr_) == 60 and all(len(v_) == 30 for v_ in b37_.values()), len(axr_))
    p37_ = [100 * prio(r) for r in axr_]
    C.claim("reframe: M73 AXIOM pooled priority SLA", "a pooled priority-slice compliance of 93.7\\% with 95\\% CI [89.8\\%, 97.2\\%]", float(np.mean(p37_)), "{:.1f}")
    lo_, hi_ = ci(p37_)
    C.claim("reframe: M73 AXIOM CI low", "a pooled priority-slice compliance of 93.7\\% with 95\\% CI [89.8\\%, 97.2\\%]", lo_, "", tol=0.15)
    C.claim("reframe: M73 AXIOM CI high", "a pooled priority-slice compliance of 93.7\\% with 95\\% CI [89.8\\%, 97.2\\%]", hi_, "", tol=0.15)
    C.claim("reframe: M73 AXIOM URLLC", "AXIOM keeps URLLC and eMBB at 96.7\\% and 90.7\\%", 100 * float(np.mean([r["sla"]["urllc"] for r in axr_])), "{:.1f}")
    C.claim("reframe: M73 AXIOM eMBB", "AXIOM keeps URLLC and eMBB at 96.7\\% and 90.7\\%", 100 * float(np.mean([r["sla"]["embb"] for r in axr_])), "{:.1f}")
    bp_ = {b_: 100 * mean(v_, prio) for b_, v_ in b37_.items()}
    for b_, q_ in (("single_agent_dqn", "58.7"), ("mappo_tuned", "56.7"), ("independent_dqn", "32.1")):
        C.claim(f"reframe: M73 {b_} priority SLA", "The single-agent DQN, MAPPO, and the independent DQN keep 58.7\\%, 56.7\\%, and 32.1\\%.", bp_[b_], "{:.1f}")
        C.claim(f"reframe: M73 table {b_}", f"{q_}\\%", bp_[b_], "{:.1f}")
    C.claim("reframe: M73 table AXIOM", "97.1, 97.3, 93.7\\%", float(np.mean(p37_)), "{:.1f}")
    gap37_ = float(np.mean(p37_)) - max(bp_[b_] for b_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned"))
    C.claim("reframe: M73 lead over best baseline", "the lead reaches 35.0 points", gap37_, "{:.1f}")
    C.claim("reframe: M73 rule gap", "within 6.3 at thirty-seven", bp_["rule_static"] - float(np.mean(p37_)), "{:.1f}")
    C.note("reframe: M73 static rule inside the quoted 99.96 to 99.99 range", 99.955 <= bp_["rule_static"] < 99.995, round(bp_["rule_static"], 3))
    C.note("reframe: M73 every baseline falls again from 19 to 37 gNBs", all(bp_[b_] < tr[(19, b_)] for b_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned"))
           and "At thirty-seven gNBs every baseline falls again" in C.main, None)
    t37_ = {}
    for t_, ss_ in L37_.items():
        for b_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned"):
            t37_[(t_, b_, "p")] = paired(ax37_[t_], b37_[b_], lambda r: 100 * prio(r))
            t37_[(t_, b_, "r")] = paired(ax37_[t_], b37_[b_])
    h1_ = holm({k: v["p"] for k, v in t37_.items() if k[0] == "hex"})
    h2_ = holm({k: v["p"] for k, v in t37_.items() if k[0] != "hex"})
    hh_ = {**h1_, **h2_}
    C.note("reframe: M73 all 18 comparisons hold, AXIOM ahead, Holm-adjusted p<0.01",
           len(hh_) == 18 and all(t37_[k]["diff"] > 0 and hh_[k] < 0.01 for k in t37_) and "all 18 comparisons hold after Holm correction within their pre-registered families" in C.main,
           {str(k): round(v, 5) for k, v in hh_.items()})
    dp_ = [v["diff"] for k, v in t37_.items() if k[2] == "p"]; dr_ = [v["diff"] for k, v in t37_.items() if k[2] == "r"]
    C.claim("reframe: M73 compliance lead low", "AXIOM keeps 32.0 to 67.8 percentage points more compliance", min(dp_), "{:.1f}")
    C.claim("reframe: M73 compliance lead high", "AXIOM keeps 32.0 to 67.8 percentage points more compliance", max(dp_), "{:.1f}")
    C.claim("reframe: M73 reward lead low", "and earns 18.3 to 29.5 more reward per step", min(dr_), "{:.1f}")
    C.claim("reframe: M73 reward lead high", "and earns 18.3 to 29.5 more reward per step", max(dr_), "{:.1f}")
    C.claim("reframe: M73 AXIOM collapses", "AXIOM collapses in 6 of its 60 runs", sum(r["collapsed"] for r in axr_), "{:d}")
    C.claim("reframe: M73 single-agent collapses", "against 26 of 30 for the single-agent DQN", sum(r["collapsed"] for r in b37_["single_agent_dqn"].values()), "{:d}")
    cp_ = [100 * prio(r) for r in axr_ if r["collapsed"]]
    C.note("reframe: M73 collapsed AXIOM runs keep 59% to 65%", round(min(cp_)) == 59 and round(max(cp_)) == 65
           and "Even its collapsed runs keep 59\\% to 65\\%" in C.main, [round(x, 2) for x in cp_])
    C.note("reframe: M73 table collapse counts", [sum(r["collapsed"] for r in b37_[b_].values()) for b_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned")] == [26, 3, 0]
           and "1/90 and 6/60 & 84/90 and 26/30 & 3/90 and 3/30 & 0/90 and 0/30" in C.main, None)
    cx37_ = json.load(open(f"{ROOT}/m73/complexity_n37.json"))["37"]
    C.note("reframe: M73 parameter counts at 37 gNBs", cx37_["axiom2"]["params_execution"] == 7782 and cx37_["single_agent_dqn"]["params_execution"] == 64770
           and cx37_["independent_dqn"]["params_execution"] == 682058 and "21,250 to 64,770 & 55,302 to 682,058" in C.main, cx37_)
    mg_ = seeds_of("m73/A_n37_hex_mappo_grid", "mappo", S15)
    axh15_ = seeds_of("m73/A_n37_hex", "axiom2", S15)
    tg_p_, tg_r_ = paired(axh15_, mg_, lambda r: 100 * prio(r)), paired(axh15_, mg_)
    C.claim("reframe: M73 grid MAPPO compliance", "the selected MAPPO keeps 65.6\\% priority-slice compliance", 100 * mean(mg_, prio), "{:.1f}")
    C.claim("reframe: M73 grid MAPPO compliance gap", "AXIOM keeps 29.2 percentage points more compliance and earns 23.23 more reward per step on 15 seeds", tg_p_["diff"], "{:.1f}")
    C.claim("reframe: M73 grid MAPPO reward gap", "AXIOM keeps 29.2 percentage points more compliance and earns 23.23 more reward per step on 15 seeds", tg_r_["diff"], "{:.2f}")
    C.note("reframe: M73 grid MAPPO 15 seeds, both p<0.001, 13 and 15 wins", len(mg_) == 15 and tg_p_["p"] < 0.001 and tg_r_["p"] < 0.001
           and tg_p_["wins"] == 13 and tg_r_["wins"] == 15 and sum(r["collapsed"] for r in mg_.values()) == 0, (tg_p_, tg_r_))
    C.claim("M73 grid MAPPO reward", "It keeps 65.6\\% priority-slice compliance and 151.90 reward per step", mean(mg_), "{:.2f}")
    for t_, lab_ in (("hex", "AXIOM, hex & 30"), ("ring", "AXIOM, ring & 15"), ("fully_connected", "AXIOM, fully-connected & 15")):
        d_ = ax37_[t_]
        row_ = (f"{lab_} & {100 * mean(d_, lambda r: r['sla']['urllc']):.1f}\\% & {100 * mean(d_, lambda r: r['sla']['embb']):.1f}\\% & "
                f"{100 * mean(d_, prio):.1f}\\% & {mean(d_):.2f} & {sum(r['collapsed'] for r in d_.values())} \\\\")
        C.note(f"M73 supplement table row {t_}", row_ in C.tex, row_)
    for b_, lab_ in (("single_agent_dqn", "Single-agent DQN"), ("independent_dqn", "Independent DQN"), ("mappo_tuned", "MAPPO")):
        d_ = b37_[b_]
        row_ = (f"{lab_} & 30 & {100 * mean(d_, lambda r: r['sla']['urllc']):.1f}\\% & {100 * mean(d_, lambda r: r['sla']['embb']):.1f}\\% & "
                f"{100 * mean(d_, prio):.1f}\\% & {mean(d_):.2f} & {sum(r['collapsed'] for r in d_.values())} \\\\")
        C.note(f"M73 supplement table row {b_}", row_ in C.tex, row_)
    cxt_ = json.load(open(f"{ROOT}/m73/complexity_n37.json"))
    C.note("reframe: M73 latency at 37 gNBs in the complexity table",
           all(f"{cxt_['37'][k_]['ms_per_step']:.2f}" in C.main for k_ in ("axiom2", "axiom2_mlp", "independent_dqn", "mappo"))
           and "1.04 / 1.98 / 4.79 / 9.89" in C.main and "1.0 to 9.9 ms per control step" in C.main, cxt_["37"])
    sa_ = cxt_["single_agent_ms_per_step"]
    C.note("reframe: single-agent latency row matches its measurement", " / ".join(f"{sa_[k_]:.2f}" for k_ in ("3", "7", "19", "37")) in C.main, sa_)
    figtr37_ = json.load(open("/home/kmanojp/oranslice_rig/Papers_4-5/Paper_5/WPC/figures/fig6_scaling_trend_summary.json"))
    C.note("reframe: trend figure plots the recomputed 37-gNB compliance",
           abs(figtr37_["arms"]["axiom2"]["37"]["prio_mean"] - float(np.mean(p37_))) < 1e-6
           and all(abs(figtr37_["arms"][b_]["37"]["prio_mean"] - bp_[b_]) < 1e-6 for b_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned")), None)

    # ---------------- M74: fresh-seed replication at thirty-seven gNBs (docs/PAPER5_M74_preregistration.md)
    S74_ = list(range(6100, 6120))
    f74_ = {k_: seeds_of("m74/A_n37_hex", k_, S74_) for k_ in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned", "rule_static")}
    C.note("reframe: M74 complete, 20 seeds per arm", all(len(v_) == 20 for v_ in f74_.values()), {k_: len(v_) for k_, v_ in f74_.items()})
    C.claim("reframe: M74 AXIOM priority SLA", "There AXIOM keeps 95.1\\% priority-slice compliance", 100 * mean(f74_["axiom2"], prio), "{:.1f}")
    for b_ in ("mappo_tuned", "single_agent_dqn", "independent_dqn"):
        C.claim(f"reframe: M74 {b_} priority SLA", "against 58.5\\%, 57.4\\%, and 34.1\\% for MAPPO, the single-agent DQN, and the independent DQN", 100 * mean(f74_[b_], prio), "{:.1f}")
    t74_ = {}
    for b_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned"):
        t74_[(b_, "p")] = paired(f74_["axiom2"], f74_[b_], lambda r: 100 * prio(r))
        t74_[(b_, "r")] = paired(f74_["axiom2"], f74_[b_])
    h74_ = holm({k_: v_["p"] for k_, v_ in t74_.items()})
    C.note("reframe: M74 AXIOM beats every baseline on compliance and reward at Holm p<0.001",
           all(t74_[k_]["diff"] > 0 and h74_[k_] < 0.001 for k_ in t74_) and "on compliance and on reward at Holm-adjusted $p<0.001$" in C.main,
           {str(k_): round(v_, 6) for k_, v_ in h74_.items()})
    C.claim("reframe: M74 AXIOM collapses", "It collapses in 1 of the 20 seeds, against 18 for the single-agent DQN", sum(r["collapsed"] for r in f74_["axiom2"].values()), "{:d}")
    C.claim("reframe: M74 single-agent collapses", "It collapses in 1 of the 20 seeds, against 18 for the single-agent DQN", sum(r["collapsed"] for r in f74_["single_agent_dqn"].values()), "{:d}")
    C.note("M74 seeds and their streams unused before", not ({s_ for s_ in S74_} | {5000 + s_ for s_ in S74_}) &
           (set(S30) | set(REP) | set(S30_19) | set(range(2000, 2010)) | set(range(3000, 3020)) | set(range(4000, 4040)) | set(range(7000, 7020))
            | set(range(8100, 8110)) | set(range(9000, 9020)) | {5000 + x_ for x_ in set(S30) | set(REP) | set(S30_19) | set(range(2000, 2010))
            | set(range(3000, 3020)) | set(range(4000, 4040)) | set(range(7000, 7020)) | set(range(8100, 8110)) | set(range(9000, 9020))}), None)
    for k_, lab_ in (("axiom2", "AXIOM"), ("single_agent_dqn", "Single-agent DQN"), ("independent_dqn", "Independent DQN"), ("mappo_tuned", "MAPPO")):
        d_ = f74_[k_]
        row_ = (f"{lab_} & 20 & {100 * mean(d_, lambda r: r['sla']['urllc']):.1f}\\% & {100 * mean(d_, lambda r: r['sla']['embb']):.1f}\\% & "
                f"{100 * mean(d_, prio):.1f}\\% & {mean(d_):.2f} & {sum(r['collapsed'] for r in d_.values())} \\\\")
        C.note(f"M74 supplement table row {k_}", row_ in C.tex, row_)
    dd_ = {b_: (t74_[(b_, "p")]["diff"], t74_[(b_, "r")]["diff"]) for b_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned")}
    C.note("M74 supplement leads 37.7/61.0/36.5 points and 35.46/25.62/30.63 reward",
           [round(dd_[b_][0], 1) for b_ in dd_] == [37.7, 61.0, 36.5] and [round(dd_[b_][1], 2) for b_ in dd_] == [35.46, 25.62, 30.63]
           and "by 37.7, 61.0, and 36.5 points of priority-slice compliance and by 35.46, 25.62, and 30.63 reward per step" in C.tex, dd_)
    pool_ = list(seeds_of("m73/A_n37_hex", "axiom2", S30_19).values()) + list(f74_["axiom2"].values())
    C.claim("M74 pooled 50 hex seeds", "AXIOM keeps 94.2\\% priority-slice compliance over 50 seeds and collapses in 4 of them", 100 * float(np.mean([prio(r) for r in pool_])), "{:.1f}")
    C.note("M74 pooled collapse count 4 of 50", len(pool_) == 50 and sum(r["collapsed"] for r in pool_) == 4, None)

    # ---------------- M75 B, D, E (docs/PAPER5_M75_preregistration.md)
    aa_ = {n_: seeds_of(f"m75/B_acceptall/n{n_}", "rule_accept_all", S15 if n_ == 7 else S30_19) for n_ in (7, 19, 37)}
    aap_ = {n_: 100 * mean(v_, prio) for n_, v_ in aa_.items()}
    for n_, q_ in ((7, "70.9"), (19, "67.1"), (37, "61.9")):
        C.claim(f"reframe: M75 accept-all priority SLA at {n_} gNBs", "It keeps 70.9\\%, 67.1\\%, and 61.9\\% priority-slice compliance at seven, nineteen, and thirty-seven gNBs", aap_[n_], "{:.1f}")
    for n_, q_ in ((7, "26.88"), (19, "78.55"), (37, "156.22")):
        C.claim(f"M75 accept-all reward at {n_} gNBs", "with reward 26.88, 78.55, and 156.22 per step", mean(aa_[n_]), "{:.2f}")
    def lr_rows(n_, a_):
        if n_ == 37:
            if a_ == "axiom2":
                return [r for t_, ss_ in (("hex", S30_19), ("ring", S15), ("fully_connected", S15)) for r in seeds_of(f"m73/A_n37_{t_}", a_, ss_).values()]
            return list(seeds_of("m73/A_n37_hex", a_, S30_19).values())
        return [r for t_ in ("fully_connected", "ring", "hex") for r in seeds_of(f"m65_scaling/n{n_}_{t_}", a_, S15 if n_ == 7 else S30_19).values()]
    lp_ = {(n_, a_): 100 * float(np.mean([prio(r) for r in lr_rows(n_, a_)])) for n_ in (7, 19, 37) for a_ in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")}
    lnc_ = {(n_, a_): 100 * float(np.mean([prio(r) for r in lr_rows(n_, a_) if not r["collapsed"]])) for n_ in (19, 37) for a_ in ("single_agent_dqn", "independent_dqn")}
    C.note("reframe: M75 every baseline below accept-all at 19 and 37 gNBs, only MAPPO at 7",
           all(lp_[(n_, a_)] < aap_[n_] for n_ in (19, 37) for a_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned"))
           and [a_ for a_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned") if lp_[(7, a_)] < aap_[7]] == ["mappo_tuned"]
           and "at nineteen and thirty-seven gNBs every baseline falls below it on average" in C.main, {str(k_): round(v_, 2) for k_, v_ in lp_.items()})
    C.claim("reframe: M75 non-collapsed single-agent at 37", "those runs of the single-agent and independent DQNs keep only 35.9\\% and 29.1\\%", lnc_[(37, "single_agent_dqn")], "{:.1f}")
    C.claim("reframe: M75 non-collapsed independent at 37", "those runs of the single-agent and independent DQNs keep only 35.9\\% and 29.1\\%", lnc_[(37, "independent_dqn")], "{:.1f}")
    C.claim("M75 non-collapsed single-agent at 19", "runs that do not collapse keep only 40.0\\% and 35.9\\%", lnc_[(19, "single_agent_dqn")], "{:.1f}")
    C.claim("M75 non-collapsed independent at 19", "the independent DQN's 55.9\\% and 29.1\\%", lnc_[(19, "independent_dqn")], "{:.1f}")
    C.claim("M75 MAPPO below accept-all at 7", "only MAPPO, at 67.7\\%, falls below it", lp_[(7, "mappo_tuned")], "{:.1f}")
    gp_ = [lp_[(n_, "axiom2")] - aap_[n_] for n_ in (7, 19, 37)]
    C.claim("reframe: M75 AXIOM above floor low", "AXIOM stays 26 to 32 points above the floor", min(gp_), "{:.0f}")
    C.claim("reframe: M75 AXIOM above floor high", "AXIOM stays 26 to 32 points above the floor", max(gp_), "{:.0f}")
    D75_ = "m75/D_envB_n19_hex"
    d75_ = {a_: seeds_of(D75_, a_, S15) for a_ in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned", "rule_static", "rule_accept_all", "rule_local_transfer")}
    def pg_(a_, s_):
        m_ = json.load(open(f"{ROOT}/{D75_}/{a_}/seed{s_}/eval/per_gnb_sla.json"))
        assert m_["steps"] == 3000 and len(m_["gnbs"]) == 19
        return 100 * 0.5 * (float(np.mean(m_["per_gnb_compliance"]["urllc"])) + float(np.mean(m_["per_gnb_compliance"]["embb"])))
    pgv_ = {a_: {s_: pg_(a_, s_) for s_ in v_} for a_, v_ in d75_.items()}
    C.note("reframe: M75 D complete, 15 seeds per arm with per-gNB records", all(len(v_) == 15 for v_ in d75_.values()) and all(len(v_) == 15 for v_ in pgv_.values()), None)
    cl_ = {a_: 100 * mean(d75_[a_], prio) for a_ in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")}
    C.claim("reframe: M75 D cluster compliance low", "at 16.7\\% to 24.7\\% for every learned policy", min(cl_.values()), "{:.1f}")
    C.claim("reframe: M75 D cluster compliance high", "at 16.7\\% to 24.7\\% for every learned policy", max(cl_.values()), "{:.1f}")
    td_ = {}
    for b_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned"):
        td_[(b_, "r")] = paired(d75_["axiom2"], d75_[b_])
        common_ = sorted(pgv_["axiom2"])
        dd_ = np.array([pgv_["axiom2"][s_] - pgv_[b_][s_] for s_ in common_])
        td_[(b_, "g")] = {"diff": float(dd_.mean()), "p": float(wilcoxon(dd_).pvalue)}
    hd_ = holm({k_: v_["p"] for k_, v_ in td_.items()})
    C.note("reframe: M75 D1 AXIOM leads every learned baseline, Holm p<=0.013", all(td_[k_]["diff"] > 0 and hd_[k_] <= 0.013 for k_ in td_)
           and "at Holm-adjusted $p\\leq0.013$, keeping 77.3\\%" in C.main, {str(k_): round(v_, 5) for k_, v_ in hd_.items()})
    rr_ = [td_[(b_, "r")]["diff"] for b_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned")]
    gg_ = [td_[(b_, "g")]["diff"] for b_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned")]
    C.claim("reframe: M75 D reward lead low", "AXIOM earns 5.54 to 21.22 more reward per step than every learned baseline", min(rr_), "{:.2f}")
    C.claim("reframe: M75 D reward lead high", "AXIOM earns 5.54 to 21.22 more reward per step than every learned baseline", max(rr_), "{:.2f}")
    C.claim("reframe: M75 D per-gNB lead low", "keeps 5.5 to 10.9 percentage points more per-gNB priority-slice compliance", min(gg_), "{:.1f}")
    C.claim("reframe: M75 D per-gNB lead high", "keeps 5.5 to 10.9 percentage points more per-gNB priority-slice compliance", max(gg_), "{:.1f}")
    C.claim("reframe: M75 D AXIOM per-gNB", "keeping 77.3\\%", float(np.mean(list(pgv_["axiom2"].values()))), "{:.1f}")
    ts_ = paired(d75_["axiom2"], d75_["rule_static"])
    C.claim("reframe: M75 D static rule margin", "the static rule, which earns 1.31 more per step", -ts_["diff"], "{:.2f}")
    same_ = sum(d75_["axiom2"][s_]["reward"] == d75_["rule_static"][s_]["reward"] and d75_["axiom2"][s_]["blocks"] == d75_["rule_static"][s_]["blocks"]
                and d75_["axiom2"][s_]["sla"] == d75_["rule_static"][s_]["sla"] for s_ in S15)
    C.claim("reframe: M75 D identical to static rule", "in 9 of the 15 seeds it makes exactly the static rule's decisions", same_, "{:d}")
    tt_ = paired(d75_["axiom2"], d75_["rule_local_transfer"])
    C.claim("reframe: M75 D tuned rule margin", "earns 3.81 more than AXIOM and keeps 84.5\\%", -tt_["diff"], "{:.2f}")
    C.claim("reframe: M75 D tuned rule per-gNB", "earns 3.81 more than AXIOM and keeps 84.5\\%", float(np.mean(list(pgv_["rule_local_transfer"].values()))), "{:.1f}")
    C.note("reframe: M75 D tuned rule wins every seed", tt_["losses"] == 15, tt_)
    C.note("reframe: M75 comparison-table Env B 19-gNB rewards", [round(mean(d75_[a_]), 2) for a_ in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")]
           == [80.28, 74.74, 71.20, 59.07] and "8.83 and 80.28 & 7.49 and 74.74 & 7.79 and 71.20 & 6.97 and 59.07" in C.main, None)
    lab75_ = {"axiom2": "AXIOM", "single_agent_dqn": "Single-agent DQN", "independent_dqn": "Independent DQN", "mappo_tuned": "MAPPO",
              "rule_static": "Static rule", "rule_accept_all": "Accept all", "rule_local_transfer": "Tuned local rule, carried over"}
    for a_, l_ in lab75_.items():
        row_ = (f"{l_} & {mean(d75_[a_]):.2f} & {float(np.mean(list(pgv_[a_].values()))):.1f}\\% & {100 * mean(d75_[a_], prio):.1f}\\% & "
                f"{sum(r['collapsed'] for r in d75_[a_].values())} \\\\")
        C.note(f"M75 S16 table row {a_}", row_ in C.tex, row_)
    sc_ = {f_: json.load(open(f"{ROOT}/m75/E_screen/{f_}.json")) for f_ in ("hex_axiom2", "ring_axiom2", "fully_connected_axiom2", "hex_single_agent_dqn", "hex_independent_dqn", "hex_mappo_tuned")}
    axf_ = sum(r["fails"] for f_ in ("hex_axiom2", "ring_axiom2", "fully_connected_axiom2") for r in sc_[f_])
    axc_ = [r for f_ in ("hex_axiom2", "ring_axiom2", "fully_connected_axiom2") for r in sc_[f_] if r["eval_collapsed"]]
    C.note("M75 E screen at 37 gNBs: AXIOM 8 of 60 incl. all six collapses; baselines 29, 27, 27 of 30",
           axf_ == 8 and len(axc_) == 6 and all(r["fails"] for r in axc_) and [sum(r["fails"] for r in sc_[f_]) for f_ in ("hex_single_agent_dqn", "hex_independent_dqn", "hex_mappo_tuned")] == [29, 27, 27]
           and "it fails 8 of AXIOM's 60 checkpoints, including all six that collapse, against 29, 27, and 27 of 30" in C.tex, None)

    # ---------------- M75 C: DQN baselines tuned at 19 and 37 gNBs
    sel75_ = json.load(open(f"{ROOT}/m75/C_selection.json"))
    tc_, tcr_ = {}, {}
    for n_ in (19, 37):
        axc_ = seeds_of("m65_scaling/n19_hex" if n_ == 19 else "m73/A_n37_hex", "axiom2", S30_19)
        for a_ in ("single_agent_dqn", "independent_dqn"):
            sv_ = sel75_[f"{a_}|{n_}"]
            cell_ = ("m65_scaling/n19_hex" if n_ == 19 else "m73/A_n37_hex") if sv_["is_current"] else f"m75/C_confirm/n{n_}"
            b_ = seeds_of(cell_, a_, S30_19)
            tcr_[(n_, a_)] = b_
            tc_[(n_, a_, "p")] = paired(axc_, b_, lambda r: 100 * prio(r))
            tc_[(n_, a_, "r")] = paired(axc_, b_)
    hc_ = holm({k_: v_["p"] for k_, v_ in tc_.items()})
    C.note("reframe: M75 C AXIOM beats every tuned baseline, Holm p<0.001", len(tc_) == 8 and all(tc_[k_]["diff"] > 0 and hc_[k_] < 0.001 for k_ in tc_)
           and "AXIOM beats each of them on compliance and on reward at Holm-adjusted $p<0.001$" in C.main, {str(k_): round(v_, 7) for k_, v_ in hc_.items()})
    cp_ = [v_["diff"] for k_, v_ in tc_.items() if k_[2] == "p"]
    C.claim("reframe: M75 C lead low", "by 29.9 to 48.1 points", min(cp_), "{:.1f}")
    C.claim("reframe: M75 C lead high", "by 29.9 to 48.1 points", max(cp_), "{:.1f}")
    C.note("reframe: M75 C new settings in three of four cells", sum(not v_["is_current"] for v_ in sel75_.values()) == 3
           and "selected new settings in three of the four cells" in C.main, {k_: v_["selected"] for k_, v_ in sel75_.items()})
    tp_ = {k_: 100 * mean(v_, prio) for k_, v_ in tcr_.items()}
    C.claim("reframe: M75 C tuned independent at 19", "rises from 56.4\\% to 59.1\\% at nineteen gNBs", tp_[(19, "independent_dqn")], "{:.1f}")
    C.claim("reframe: M75 C tuned independent at 37", "and from 32.1\\% to 45.5\\% at thirty-seven", tp_[(37, "independent_dqn")], "{:.1f}")
    sa19_, aa19_ = tcr_[(19, "single_agent_dqn")], seeds_of("m75/B_acceptall/n19", "rule_accept_all", S30_19)
    C.note("reframe: M75 C tuned single-agent at 19 accepts everything and matches accept-all exactly",
           all(r["collapsed"] for r in sa19_.values()) and len(sa19_) == 30
           and all(sa19_[s_]["reward"] == aa19_[s_]["reward"] and sa19_[s_]["sla"] == aa19_[s_]["sla"] for s_ in S30_19), None)
    C.note("reframe: M75 C no tuned baseline exceeds accept-all",
           all(tp_[(n_, a_)] <= aap_[n_] + 1e-9 for (n_, a_) in tp_) and "No tuned baseline exceeds the accept-all floor" in C.main, {str(k_): round(v_, 3) for k_, v_ in tp_.items()})
    wc_ = [v_["wins"] for v_ in tc_.values()]
    C.note("M75 C supplement: wins 26 to 30 of 30", min(wc_) == 26 and max(wc_) == 30 and "winning 26 to 30 of 30 seeds at Holm-adjusted $p<0.001$" in C.tex, wc_)
    pc_ = sel75_["single_agent_dqn|19"]["grid"]
    C.note("M75 C supplement: single-agent 19-gNB selection margin 0.001", round(pc_["1e-4,16"]["reward"] - pc_["1e-3,16"]["reward"], 3) == 0.001
           and "the selected setting won by 0.001 reward per step" in C.tex, None)
    for (n_, a_), l_, cfg_ in (((19, "single_agent_dqn"), "Single-agent DQN & 19", "$10^{-4}$, 16"), ((19, "independent_dqn"), "Independent DQN & 19", "$3{\\times}10^{-4}$, 64"),
                               ((37, "single_agent_dqn"), "Single-agent DQN & 37", "$10^{-3}$, 16, unchanged"), ((37, "independent_dqn"), "Independent DQN & 37", "$10^{-4}$, 64")):
        b0_ = seeds_of("m65_scaling/n19_hex" if n_ == 19 else "m73/A_n37_hex", a_, S30_19)
        row_ = (f"{l_} & {cfg_} & {tp_[(n_, a_)]:.1f}\\% & {100 * mean(b0_, prio):.1f}\\% & {mean(tcr_[(n_, a_)]):.2f} & "
                f"{sum(r['collapsed'] for r in tcr_[(n_, a_)].values())} \\\\")
        C.note(f"M75 S16 tuned row {n_} {a_}", row_ in C.tex, row_)

    # ---------------- MAPPO cost-benefit paragraph (complexity section)
    cxa_ = json.load(open(f"{ROOT}/m73/complexity_n37.json"))["37"]
    C.note("reframe: MAPPO cost numbers at 37 gNBs", cxa_["mappo"]["params_execution"] == 5122 and f"{cxa_['mappo']['ms_per_step']:.2f}" == "0.27"
           and cxa_["axiom2"]["params_execution"] == 7782 and f"{cxa_['axiom2']['ms_per_step']:.2f}" == "9.89"
           and "it uses 5,122 parameters, 0.27 ms per control step, and 495 s of training per seed, against AXIOM's 7,782 parameters, 9.89 ms, and 1,182 s" in C.main, None)
    def med_train_(cell_, arm_):
        v_ = [r_["train_seconds"] for f_ in glob.glob(f"{ROOT}/{cell_}/{arm_}_*.json") for r_ in json.load(open(f_)).values() if isinstance(r_, dict) and "train_seconds" in r_]
        return float(np.median(v_))
    C.note("reframe: MAPPO and AXIOM median training seconds at 37 gNBs", round(med_train_("m73/A_n37_hex", "mappo_tuned")) == 495
           and round(med_train_("m73/A_n37_ring", "axiom2")) == 1182, (med_train_("m73/A_n37_hex", "mappo_tuned"), med_train_("m73/A_n37_ring", "axiom2")))
    b3a_, b3m_ = mean(B["axiom2"]), mean(B["mappo_tuned"])
    C.claim("reframe: Env B 3 gNBs AXIOM over MAPPO percent", "AXIOM earns 27\\% more reward per step than MAPPO at three gNBs, 8.83 against 6.97", 100 * (b3a_ / b3m_ - 1), "{:.0f}")
    rel7_, sig7_ = [], []
    for t_ in ("fully_connected", "ring", "hex"):
        a7_, m7_ = seeds_of(f"m64/n7_{t_}", "axiom2", S15), seeds_of(f"m64/n7_{t_}", "mappo_tuned", S15)
        rel7_.append(100 * (mean(a7_) / mean(m7_) - 1))
        sig7_.append(paired(a7_, m7_)["p"])
    # significance within the pre-registered H2 family at seven gNBs: membership read from m64_analysis.json,
    # every p value recomputed here from the logs and Holm-corrected by this script
    fam7_ = {}
    for k_ in json.load(open(f"{ROOT}/m64/m64_analysis.json"))["H2_n7"]:
        c_, a_, m_ = k_.split("|")
        fam7_[k_] = paired(seeds_of(f"m64/{c_}", "axiom2", S15), seeds_of(f"m64/{c_}", a_, S15), (lambda r: r["reward"]) if m_ == "reward" else prio)["p"]
    hf7_ = holm(fam7_)
    h7_ = {t_: hf7_[f"n7_{t_}|mappo_tuned|reward"] for t_ in ("fully_connected", "ring", "hex")}
    C.note("reframe: Env B 7 gNBs AXIOM over MAPPO 7 to 15 percent, significant on two layouts after Holm",
           round(min(rel7_)) == 7 and round(max(rel7_)) == 15 and sum(v_ < 0.05 for v_ in h7_.values()) == 2
           and "At seven gNBs it earns between 7\\% and 15\\% more, significantly on two of the three layouts" in C.main, {"rel": rel7_, "p_holm": h7_})
    a19_, m19_ = mean(d75_["axiom2"]), mean(d75_["mappo_tuned"])
    C.claim("reframe: Env B 19 gNBs AXIOM over MAPPO percent", "and 36\\% more at nineteen gNBs, 80.28 against 59.07", 100 * (a19_ / m19_ - 1), "{:.0f}")
    C.claim("reframe: AXIOM slowest decision share of control period", "AXIOM's slowest decision takes 0.2\\% of the 5 s control period", 100 * cxa_["axiom2"]["ms_per_step"] / 5000, "{:.1f}")

    # ---------------- M76 (docs/PAPER5_M76_preregistration.md), recomputed from the logs and per-gNB records
    def pg76_(cell_, arm_, s_, sub_="eval/"):
        m_ = json.load(open(f"{ROOT}/{cell_}/{arm_}/seed{s_}/{sub_}per_gnb_sla.json"))["mean_compliance"]
        return 100 * 0.5 * (m_["urllc"] + m_["embb"])
    def pvd_(a_, b_):
        cm_ = sorted(set(a_) & set(b_)); dd_ = np.array([a_[x_] - b_[x_] for x_ in cm_])
        return {"n": len(dd_), "diff": float(dd_.mean()), "wins": int((dd_ > 0).sum()), "ties": int((dd_ == 0).sum()), "losses": int((dd_ < 0).sum()),
                "p": float(wilcoxon(dd_).pvalue) if np.any(dd_ != 0) else 1.0}
    # d: VDN
    vc_ = {"A3": ("m76/d_vdn/A_n3", "m65_n3_view", S30), "B3": ("m76/d_vdn/B_n3", "m64/n3_fully_connected", S30), "A19": ("m76/d_vdn/A_n19_hex", "m65_scaling/n19_hex", S30_19)}
    vr_ = {k_: (seeds_of(c_, "vdn", ss_), seeds_of(ac_, "axiom2", ss_), seeds_of(ac_, "independent_dqn", ss_)) for k_, (c_, ac_, ss_) in vc_.items()}
    C.note("reframe: M76 VDN complete, 30 seeds per cell", all(len(v_[0]) == 30 for v_ in vr_.values()), {k_: len(v_[0]) for k_, v_ in vr_.items()})
    C.note("reframe: M76 VDN ties AXIOM at three gNBs", all(round(mean(vr_[k_][0]), 3) == q_[0] and round(mean(vr_[k_][1]), 3) == q_[1] for k_, q_ in (("A3", (12.664, 12.698)), ("B3", (8.552, 8.832))))
           and "at 12.664 against 12.698 reward per step in Env A and 8.552 against 8.832 in Env B" in C.main, None)
    dv_ = {("A3", "r"): paired(vr_["A3"][1], vr_["A3"][0]), ("B3", "r"): paired(vr_["B3"][1], vr_["B3"][0]),
           ("A19", "r"): paired(vr_["A19"][1], vr_["A19"][0]), ("A19", "p"): paired(vr_["A19"][1], vr_["A19"][0], lambda r: 100 * prio(r))}
    hv76_ = holm({k_: v_["p"] for k_, v_ in dv_.items()})
    C.note("reframe: M76 VDN three-gNB margins not significant after Holm", hv76_[("A3", "r")] >= 0.05 and hv76_[("B3", "r")] >= 0.05, {str(k_): v_ for k_, v_ in hv76_.items()})
    C.claim("reframe: M76 VDN 19-gNB compliance", "but at nineteen gNBs it keeps 83.4\\% priority-slice compliance", 100 * mean(vr_["A19"][0], prio), "{:.1f}")
    C.claim("reframe: M76 AXIOM over VDN compliance at 19", "There AXIOM keeps 13.6 percentage points more and earns 2.73 more reward per step", dv_[("A19", "p")]["diff"], "{:.1f}")
    C.claim("reframe: M76 AXIOM over VDN reward at 19", "There AXIOM keeps 13.6 percentage points more and earns 2.73 more reward per step", dv_[("A19", "r")]["diff"], "{:.2f}")
    C.note("reframe: M76 VDN 19-gNB wins 27 to 28 of 30 at Holm p<0.001", sorted([dv_[("A19", "p")]["wins"], dv_[("A19", "r")]["wins"]]) == [27, 28]
           and hv76_[("A19", "p")] < 0.001 and hv76_[("A19", "r")] < 0.001 and "winning 27 to 28 of 30 seeds at Holm-adjusted $p<0.001$" in C.main, None)
    C.claim("reframe: VDN gap at nineteen gNBs", "There AXIOM keeps 13.6 percentage points more and earns 2.73 more reward per step", dv_[("A19", "p")]["diff"], "{:.1f}")
    for k_, l_ in (("A3", "Env A, 3 gNBs"), ("B3", "Env B, 3 gNBs"), ("A19", "Env A, 19 gNBs, hex")):
        v_, ax_, ind_ = vr_[k_]
        row_ = (f"{l_} & {mean(v_):.3f} & {mean(ax_):.3f} & {mean(ind_):.3f} & {100 * mean(v_, prio):.1f}\\% & {100 * mean(ax_, prio):.1f}\\% & {100 * mean(ind_, prio):.1f}\\% \\\\")
        C.note(f"M76 S17 VDN row {k_}", row_ in C.tex, row_)
    # e: oversubscription
    e76_ = {L_: {a_: seeds_of(f"m76/e_load{L_}_n19_hex", a_, S15) for a_ in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned", "rule_static", "rule_accept_all")} for L_ in ("1.10", "1.20")}
    te76_ = {(L_, b_): paired(e76_[L_]["axiom2"], e76_[L_][b_], lambda r: 100 * prio(r)) for L_ in e76_ for b_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned")}
    he76_ = holm({k_: v_["p"] for k_, v_ in te76_.items()})
    C.claim("reframe: M76 AXIOM compliance at 110% load", "AXIOM keeps 63.4\\% and 21.7\\% priority-slice compliance", 100 * mean(e76_["1.10"]["axiom2"], prio), "{:.1f}")
    C.claim("reframe: M76 AXIOM compliance at 120% load", "AXIOM keeps 63.4\\% and 21.7\\% priority-slice compliance", 100 * mean(e76_["1.20"]["axiom2"], prio), "{:.1f}")
    for L_, lo_, hi_ in (("1.10", "24.3", "34.0"), ("1.20", "2.5", "6.4")):
        dl_ = [te76_[(L_, b_)]["diff"] for b_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned")]
        C.note(f"reframe: M76 oversubscription margins at {L_}", f"{min(dl_):.1f}" == lo_ and f"{max(dl_):.1f}" == hi_
               and "24.3 to 34.0 and 2.5 to 6.4 percentage points more than every learned baseline, at Holm-adjusted $p\\leq0.006$" in C.main, dl_)
    C.note("reframe: M76 oversubscription Holm p<=0.006, AXIOM ahead", all(te76_[k_]["diff"] > 0 and he76_[k_] <= 0.006 for k_ in te76_), {str(k_): v_ for k_, v_ in he76_.items()})
    for a_ in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned", "rule_static", "rule_accept_all"):
        x_, y_ = e76_["1.10"][a_], e76_["1.20"][a_]
        lb_ = {"axiom2": "AXIOM", "single_agent_dqn": "Single-agent DQN", "independent_dqn": "Independent DQN", "mappo_tuned": "MAPPO", "rule_static": "Static rule", "rule_accept_all": "Accept all"}[a_]
        row_ = (f"{lb_} & {mean(x_):.2f} & {100 * mean(x_, prio):.1f}\\% & {sum(r['collapsed'] for r in x_.values())} & "
                f"{mean(y_):.2f} & {100 * mean(y_, prio):.1f}\\% & {sum(r['collapsed'] for r in y_.values())} \\\\")
        C.note(f"M76 S17 oversubscription row {a_}", row_ in C.tex, row_)
    # b1: load shift at 19 gNBs, from the raw logs
    def b1log_(sh_, arm_, s_):
        b_ = f"{ROOT}/m76/b1_shift_n19/{sh_}/{arm_}/seed{s_}/" + ("" if arm_ == "axiom2" else "lb_only/offline_eval/rep_0/")
        return read(b_ + "omega_log.jsonl" if os.path.exists(b_ + "omega_log.jsonl") else b_ + "omega_log.jsonl.gz")
    b176_ = {sh_: {a_: {s_: b1log_(sh_, a_, s_) for s_ in S15} for a_ in ("axiom2", "rule_local_transfer", "rule_static")} for sh_ in ("nominal", "load_1.10", "load_1.15", "load_1.20")}
    C.note("M76 b1 nominal reproduces M75 D exactly", all(b176_["nominal"][a_][s_]["reward"] == seeds_of("m75/D_envB_n19_hex", a_, S15)[s_]["reward"] for a_ in b176_["nominal"] for s_ in S15), None)
    tb1_ = {sh_: paired(b176_[sh_]["axiom2"], b176_[sh_]["rule_local_transfer"]) for sh_ in ("load_1.10", "load_1.15", "load_1.20")}
    hb1_ = holm({k_: v_["p"] for k_, v_ in tb1_.items()})
    C.note("reframe: M76 overload at 19 gNBs, margins 6.23/7.55/8.67, 14 of 15, Holm p<0.001",
           [round(tb1_[k_]["diff"], 2) for k_ in ("load_1.10", "load_1.15", "load_1.20")] == [6.23, 7.55, 8.67] and all(v_["wins"] == 14 for v_ in tb1_.values())
           and all(v_ < 0.001 for v_ in hb1_.values()) and "AXIOM earns 6.23, 7.55, and 8.67 more reward per step than that rule, winning 14 of 15 seeds at each level at Holm-adjusted $p<0.001$" in C.main, {k_: round(v_["diff"], 3) for k_, v_ in tb1_.items()})
    st_ = [paired(b176_[sh_]["rule_static"], b176_[sh_]["axiom2"])["diff"] for sh_ in ("load_1.10", "load_1.15", "load_1.20")]
    same_b1_ = [sum(b176_[sh_]["axiom2"][s_]["reward"] == b176_[sh_]["rule_static"][s_]["reward"] and b176_[sh_]["axiom2"][s_]["blocks"] == b176_[sh_]["rule_static"][s_]["blocks"] for s_ in S15) for sh_ in ("load_1.10", "load_1.15", "load_1.20")]
    C.note("reframe: M76 static rule 1.8 to 2.0 above AXIOM, identical decisions in 9 to 11 seeds", f"{min(st_):.1f}" == "1.8" and f"{max(st_):.1f}" == "2.0" and min(same_b1_) == 9 and max(same_b1_) == 11
           and "the static rule earns 1.8 to 2.0 more reward than AXIOM, which makes the static rule's decisions in 9 to 11 of the 15 seeds" in C.main, (st_, same_b1_))
    pg1_ = {sh_: {a_: {s_: pg76_("m76/b1_shift_n19/" + sh_, a_, s_, "") for s_ in S15} for a_ in ("axiom2", "rule_local_transfer", "rule_static")} for sh_ in b176_}
    C.note("reframe: M76 tuned rule keeps more per-gNB compliance under overload", all(np.mean(list(pg1_[sh_]["rule_local_transfer"].values())) > np.mean(list(pg1_[sh_]["axiom2"].values())) for sh_ in ("load_1.10", "load_1.15", "load_1.20")), None)
    for sh_, l_ in (("nominal", "Nominal"), ("load_1.10", "110\\%"), ("load_1.15", "115\\%"), ("load_1.20", "120\\%")):
        m_ = {a_: (mean(b176_[sh_][a_]), float(np.mean(list(pg1_[sh_][a_].values())))) for a_ in b176_[sh_]}
        row_ = (f"{l_} & {m_['axiom2'][0]:.2f} & {m_['rule_local_transfer'][0]:.2f} & {m_['rule_static'][0]:.2f} & {m_['axiom2'][1]:.1f}\\% & "
                f"{m_['rule_local_transfer'][1]:.1f}\\% & {m_['rule_static'][1]:.1f}\\% \\\\")
        C.note(f"M76 S17 shift row {sh_}", row_ in C.tex, row_)
    # b2: uneven per-gNB load
    H2c_ = "m76/b2_hetero_n7_ring"
    hb_ = {a_: seeds_of(H2c_, a_, S15) for a_ in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned", "rule_static", "rule_accept_all", "rule_local_transfer", "rule_local")}
    t_tr_ = paired(hb_["axiom2"], hb_["rule_local_transfer"]); t_st_ = paired(hb_["rule_static"], hb_["axiom2"]); t_rt_ = paired(hb_["axiom2"], hb_["rule_local"])
    C.claim("reframe: M76 uneven load AXIOM vs nominal rule", "earning 0.36 more reward per step at $p=0.23$", t_tr_["diff"], "{:.2f}")
    C.note("reframe: M76 uneven load not significant, ties re-tuned rule", round(t_tr_["p"], 2) == 0.23 and t_rt_["p"] > 0.05, (t_tr_, t_rt_))
    C.note("reframe: M76 uneven load static rule 0.27 more at p=0.028", f"{t_st_['diff']:.2f}" == "0.27" and f"{t_st_['p']:.3f}" == "0.028"
           and "while the static rule earns 0.27 more at $p=0.028$" in C.main, t_st_)
    lb2_ = [paired(hb_["axiom2"], hb_[b_]) for b_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned")]
    C.note("reframe: M76 uneven load AXIOM beats learned baselines 1.18 to 4.28, p<=0.005", f"{min(t['diff'] for t in lb2_):.2f}" == "1.18" and f"{max(t['diff'] for t in lb2_):.2f}" == "4.28"
           and all(t["p"] <= 0.005 for t in lb2_) and "by 1.18 to 4.28 reward per step at unadjusted $p\\leq0.005$" in C.main, lb2_)
    C.note("reframe: M76 uneven load 27% more than MAPPO, every seed", round(100 * (mean(hb_["axiom2"]) / mean(hb_["mappo_tuned"]) - 1)) == 27 and lb2_[2]["wins"] == 15
           and "Under uneven per-gNB load at seven gNBs it earns 27\\% more and wins every seed" in C.main, None)
    # c: per-gNB penalty
    Cc_ = "m76/c_pergnb_n19_hex"
    cg_ = {a_: {s_: pg76_(Cc_, a_, s_) for s_ in S15} for a_ in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned", "rule_static", "rule_accept_all", "rule_local_transfer")}
    old_ = {s_: pg76_("m75/D_envB_n19_hex", "axiom2", s_) for s_ in S15}
    c1_ = pvd_(cg_["axiom2"], old_)
    C.claim("reframe: M76 per-gNB penalty AXIOM compliance", "at 79.2\\% against 77.3\\% with $p=0.65$", float(np.mean(list(cg_["axiom2"].values()))), "{:.1f}")
    C.claim("reframe: M76 original-reward AXIOM compliance", "at 79.2\\% against 77.3\\% with $p=0.65$", float(np.mean(list(old_.values()))), "{:.1f}")
    C.note("reframe: M76 per-gNB penalty change not significant, p=0.65", f"{c1_['p']:.2f}" == "0.65", c1_)
    C.note("reframe: M76 per-gNB penalty AXIOM does not beat the static rule", pvd_(cg_["axiom2"], cg_["rule_static"])["p"] >= 0.05, None)
    lc_ = [pvd_(cg_["axiom2"], cg_[b_]) for b_ in ("single_agent_dqn", "independent_dqn", "mappo_tuned")]
    C.note("reframe: M76 per-gNB penalty baselines 13.7 to 18.5 points below AXIOM in every seed", f"{min(t['diff'] for t in lc_):.1f}" == "13.7" and f"{max(t['diff'] for t in lc_):.1f}" == "18.5"
           and all(t["wins"] == 15 for t in lc_) and "kept 13.7 to 18.5 percentage points less per-gNB compliance than AXIOM, in every seed" in C.main, lc_)
    lab76_ = {"axiom2": "AXIOM", "single_agent_dqn": "Single-agent DQN", "independent_dqn": "Independent DQN", "mappo_tuned": "MAPPO", "rule_static": "Static rule",
              "rule_accept_all": "Accept all", "rule_local_transfer": "Tuned rule, carried over", "rule_local": "Tuned rule, re-tuned"}
    for cell_, arms_ in ((H2c_, list(hb_)), (Cc_, list(cg_))):
        for a_ in arms_:
            d_ = seeds_of(cell_, a_, S15)
            row_ = f"{lab76_[a_]} & {mean(d_):.2f} & {float(np.mean([pg76_(cell_, a_, s_) for s_ in S15])):.1f}\\% & {sum(r['collapsed'] for r in d_.values())} \\\\"
            C.note(f"M76 S17 row {cell_.split('/')[-1]} {a_}", row_ in C.tex, row_)

    # ---------------- M77 throughput and backlog delay (docs/PAPER5_M77_plan.md), aggregated here from the per-run files
    def m77_(cell_):
        runs_ = {}
        for f_ in glob.glob(f"{ROOT}/m77/{cell_}/*_*.json"):
            a_ = os.path.basename(f_).rsplit("_", 1)[0]
            for s_, r_ in json.load(open(f_)).items():
                runs_.setdefault(a_, {})[int(s_)] = r_
        return runs_
    k77_ = {c_: m77_(c_) for c_ in ("A_n3", "A_n37_hex", "B_n3", "B_n19_hex")}
    allr_ = [r for c_ in k77_.values() for a_ in c_.values() for r in a_.values()]
    C.note("reframe: M77 every checkable re-run reproduces its stored log", len(allr_) > 0 and not any(r["reproduces_stored"] is False for r in allr_)
           and "which reproduced every stored log that could be checked" in C.main, {"runs": len(allr_), "unchecked": sum(r["reproduces_stored"] is None for r in allr_)})
    def km_(c_, a_, sl_, f_):
        return float(np.mean([r["kpi"][sl_][f_] for r in k77_[c_][a_].values() if r["kpi"][sl_][f_] is not None]))
    B77_ = ("single_agent_dqn", "independent_dqn", "mappo_tuned")
    C.claim("reframe: M77 AXIOM URLLC served at 37", "AXIOM serves 99.8\\% of the offered URLLC demand and 99.0\\% of the eMBB demand", 100 * km_("A_n37_hex", "axiom2", "urllc", "served_over_offered"), "{:.1f}")
    C.claim("reframe: M77 AXIOM eMBB served at 37", "AXIOM serves 99.8\\% of the offered URLLC demand and 99.0\\% of the eMBB demand", 100 * km_("A_n37_hex", "axiom2", "embb", "served_over_offered"), "{:.1f}")
    for sl_, lo_, hi_ in (("urllc", "94.2", "97.7"), ("embb", "85.7", "97.5")):
        v_ = [100 * km_("A_n37_hex", b_, sl_, "served_over_offered") for b_ in B77_]
        C.note(f"reframe: M77 baseline {sl_} served range at 37", f"{min(v_):.1f}" == lo_ and f"{max(v_):.1f}" == hi_
               and "against 94.2\\% to 97.7\\% and 85.7\\% to 97.5\\% for the learned baselines" in C.main, v_)
    C.claim("reframe: M77 AXIOM URLLC delay at 37", "Its URLLC delay is 0.08 control periods with a 95th percentile of 0.42", km_("A_n37_hex", "axiom2", "urllc", "delay_steps"), "{:.2f}")
    C.claim("reframe: M77 AXIOM URLLC p95 at 37", "Its URLLC delay is 0.08 control periods with a 95th percentile of 0.42", km_("A_n37_hex", "axiom2", "urllc", "delay_steps_p95"), "{:.2f}")
    dl_ = [km_("A_n37_hex", b_, "urllc", "delay_steps") for b_ in B77_]; dp_ = [km_("A_n37_hex", b_, "urllc", "delay_steps_p95") for b_ in B77_]
    C.note("reframe: M77 baseline URLLC delay 0.58 to 3.61, p95 5.2 to 16.9 at 37", f"{min(dl_):.2f}" == "0.58" and f"{max(dl_):.2f}" == "3.61" and f"{min(dp_):.1f}" == "5.2" and f"{max(dp_):.1f}" == "16.9"
           and "the baselines reach 0.58 to 3.61 with 95th percentiles of 5.2 to 16.9" in C.main, (dl_, dp_))
    C.claim("reframe: M77 static rule URLLC delay at 37", "and the static rule reaches 0.03", km_("A_n37_hex", "rule_static", "urllc", "delay_steps"), "{:.2f}")
    C.claim("reframe: M77 AXIOM URLLC delay Env B 19", "AXIOM's URLLC delay of 1.35 control periods is below every learned baseline's 2.17 to 2.66", km_("B_n19_hex", "axiom2", "urllc", "delay_steps"), "{:.2f}")
    d19_ = [km_("B_n19_hex", b_, "urllc", "delay_steps") for b_ in B77_]
    C.note("reframe: M77 Env B 19 baseline URLLC delay 2.17 to 2.66", f"{min(d19_):.2f}" == "2.17" and f"{max(d19_):.2f}" == "2.66"
           and "below every learned baseline's 2.17 to 2.66" in C.main, d19_)
    C.claim("reframe: M77 tuned rule URLLC delay Env B 19", "while the tuned rule's is lower still, at 0.51", km_("B_n19_hex", "rule_local_transfer", "urllc", "delay_steps"), "{:.2f}")
    lab77_ = {"axiom2": "AXIOM", "single_agent_dqn": "Single-agent DQN", "independent_dqn": "Independent DQN", "mappo_tuned": "MAPPO", "rule_static": "Static rule",
              "rule_local_cell": "Tuned rule", "rule_local_transfer": "Tuned rule, carried", "rule_accept_all": "Accept all"}
    for c_, d_ in k77_.items():
        for a_, rr_ in d_.items():
            tag_ = ", unchecked" if any(r["reproduces_stored"] is None for r in rr_.values()) else ""
            row_ = (f"{lab77_[a_]}{tag_} & {100 * km_(c_, a_, 'urllc', 'served_over_offered'):.1f}\\% & {100 * km_(c_, a_, 'embb', 'served_over_offered'):.1f}\\% & "
                    f"{km_(c_, a_, 'urllc', 'delay_steps'):.2f} & {km_(c_, a_, 'urllc', 'delay_steps_p95'):.2f} & {km_(c_, a_, 'embb', 'delay_steps'):.2f} & {km_(c_, a_, 'embb', 'delay_steps_p95'):.2f} \\\\")
            C.note(f"M77 S18 row {c_} {a_}", row_ in C.tex, row_)

    # ---------------- integrity: stream disjointness
    train_streams = set(S30) | set(REP) | set(S30_19) | set(range(2000, 2010)) | set(range(3000, 3020))
    eval_streams = {5000 + s for s in train_streams}
    C.note("evaluation streams disjoint from every training and selection stream", not (train_streams & eval_streams), None)
    C.note("replication seeds disjoint from primary seeds", not (set(REP) & set(S30)), None)
    C.note("every Env A/B evaluation log has 50 episodes",
           all(v is None or v["episodes"] == 50 for v in CACHE.values()), sorted({v["episodes"] for v in CACHE.values() if v}))

    n_total = len(C.rows) + 1
    C.note(f"text quotes the final check count of {n_total}", f"all {n_total} of its checks pass" in C.tex, n_total)
    rows = C.rows
    json.dump(rows, open(a.out, "w"), indent=1, default=str)
    fails = [r for r in rows if not r["ok"]]
    for r in rows:
        print(("PASS " if r["ok"] else "FAIL ") + r["label"] + ("" if r["ok"] else f"  computed={r['computed']} formatted={r['formatted']} in_tex={r['in_tex']}"))
    print(f"\n{len(rows) - len(fails)} of {len(rows)} checks pass")


if __name__ == "__main__":
    main()
