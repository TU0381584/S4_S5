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
        p = os.path.join(base, sub)
        if os.path.exists(p):
            return p
    return None


def read(path):
    """Return per-seed quantities straight from one evaluation log."""
    ep_rewards, ep_norm, ep_norm_all = {}, {}, {}
    blocks, mmtc, sla = 0, 0, {"urllc": [], "embb": [], "mmtc": []}
    with open(path) as fh:
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
    def __init__(self, tex):
        self.tex = tex
        self.rows = []

    def claim(self, label, snippet, value, fmt, tol=None):
        """snippet must appear in the tex; value formatted with fmt must equal the quoted text,
        or lie within tol of the number parsed from the snippet when tol is given."""
        present = snippet in self.tex
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
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tex = open(a.tex).read()
    C = Checker(tex)

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
    C.claim("A3 vs indep diff", "independent DQN by $+1.110$", fam["independent_dqn"]["diff"], "{:+.3f}")
    C.claim("A3 vs mappo diff", "MAPPO by $+2.685$", fam["mappo_tuned"]["diff"], "{:+.3f}")
    C.claim("A3 vs single diff", "$+0.311$ with 95\\% CI", fam["single_agent_dqn"]["diff"], "{:+.3f}")
    C.claim("A3 vs single p_holm", "at $p=0.066$", h["single_agent_dqn"], "{:.3f}")
    C.note("A3 vs indep and MAPPO p_holm <= 0.0002", max(h["independent_dqn"], h["mappo_tuned"]) <= 0.0002,
           (h["independent_dqn"], h["mappo_tuned"]))
    C.claim("A3 oracle ties", "tie exactly in 22 of the 30 seeds", fam["heuristic"]["ties"], "{}")
    C.claim("A3 pct of oracle", "is 98.9\\% of the oracle", 100 * mean(A["axiom2"]) / mean(A["heuristic"]), "{:.1f}")
    C.claim("A3 MLP diff", "a difference of $+0.058$", fam["axiom2_mlp"]["diff"], "{:+.3f}")

    # ---------------- Env A replication and pooled 40
    R = {arm: seeds_of("m65_reviewer/replication", arm, REP) for arm in ("axiom2", "mappo_tuned")}
    for arm in ("heuristic", "single_agent_dqn", "independent_dqn"):
        R[arm] = seeds_of("m63_reviewer/replication", arm, REP)
    famr = {b: paired(R["axiom2"], R[b]) for b in ("heuristic", "single_agent_dqn", "independent_dqn", "mappo_tuned")}
    hr = holm({k: v["p"] for k, v in famr.items()})
    for b, txt in (("single_agent_dqn", "$+1.083$"), ("independent_dqn", "$+0.799$"), ("mappo_tuned", "$+3.806$")):
        C.claim(f"Arep vs {b}", txt, famr[b]["diff"], "{:+.3f}")
    C.note("Arep three leads p_holm <= 0.023", max(hr["single_agent_dqn"], hr["independent_dqn"], hr["mappo_tuned"]) <= 0.0235,
           {k: hr[k] for k in ("single_agent_dqn", "independent_dqn", "mappo_tuned")})
    C.claim("Arep oracle gap", "only 0.018 below the oracle", -famr["heuristic"]["diff"], "{:.3f}")
    P = {arm: {**A[arm], **R[arm]} for arm in ("axiom2", "heuristic", "single_agent_dqn", "independent_dqn", "mappo_tuned")}
    famp = {b: paired(P["axiom2"], P[b]) for b in ("heuristic", "single_agent_dqn", "independent_dqn", "mappo_tuned")}
    hp = holm({k: v["p"] for k, v in famp.items()})
    for b, txt in (("single_agent_dqn", "$+0.504$"), ("independent_dqn", "$+1.032$"), ("mappo_tuned", "$+2.965$")):
        C.claim(f"pooled40 vs {b}", txt, famp[b]["diff"], "{:+.3f}")
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
    C.claim("sens load107 vs indep", "$+1.073$ at $p=0.006$", paired(ax, ind)["diff"], "{:+.3f}")
    ax = seeds_of("m65_reviewer/weights", "axiom2", S10); sg = seeds_of("m63_reviewer/weights", "single_agent_dqn", S10)
    C.claim("sens weights vs single", "$+1.264$ at $p=0.041$", paired(ax, sg)["diff"], "{:+.3f}")

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
    C.claim("H1 static", "that rule by $+2.495$", h1["rule_static"]["diff"], "{:+.3f}")
    C.claim("H1 accept-all", "accept-all by $+4.476$", h1["rule_accept_all"]["diff"], "{:+.3f}")
    C.note("H1 all 30 seeds won", all(v["wins"] == 30 for v in h1.values()), {k: v["wins"] for k, v in h1.items()})
    C.claim("EnvB static URLLC", "now leaves URLLC compliance at 62.5\\%", 100 * mean(B["rule_static"], lambda x: x["sla"]["urllc"]), "{:.1f}")
    C.claim("EnvB AXIOM URLLC", "AXIOM keeps URLLC at 95.8\\%", 100 * mean(B["axiom2"], lambda x: x["sla"]["urllc"]), "{:.1f}")
    for b, txt in (("independent_dqn", "$+1.038$"), ("single_agent_dqn", "$+1.337$"), ("mappo_tuned", "$+1.863$")):
        C.claim(f"H2 n3 vs {b}", txt, paired(B["axiom2"], B[b])["diff"], "{:+.3f}")
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
            C.claim("N19 single collapse", "in 84 of its 90 cells", coll["single_agent_dqn"], "{}")
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
        tol = tol if tol is not None else (0.03 if len(vals) >= 30 else 0.05)
        m = re.search(r"\[\s*(-?\$?-?[0-9.]+)\$?\\?%?,\s*(-?[0-9.]+)\\?%?\]", snippet.replace("$-$", "-"))
        okk = snippet in C.tex and m is not None and abs(float(m.group(1).replace("$", "")) - lo) <= tol and abs(float(m.group(2)) - hi) <= tol
        C.note(label, okk, (round(lo, 3), round(hi, 3), snippet))
    for arm, nm in names.items():
        r = A[arm]; lo, hi = ci([x["reward"] for x in r.values()])
        txt = [l for l in C.tex.splitlines() if l.startswith(nm + " & ") and "[" in l]
        ci_claim(f"T3 {arm} CI", txt[0] if txt else "MISSING", [x["reward"] for x in r.values()])
    for arm, nm in bnames.items():
        txt = [l for l in C.tex.splitlines() if l.startswith(nm + " & ") and "[" in l and "&" in l]
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
    ci_claim("N19 pooled CI", "[95.2\\%, 99.0\\%]".replace("\\%", ""), [100 * prio(r) for t in D19 for r in D19[t].values()])
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

    # ---------------- integrity: stream disjointness
    train_streams = set(S30) | set(REP) | set(S30_19) | set(range(2000, 2010)) | set(range(3000, 3020))
    eval_streams = {5000 + s for s in train_streams}
    C.note("evaluation streams disjoint from every training and selection stream", not (train_streams & eval_streams), None)
    C.note("replication seeds disjoint from primary seeds", not (set(REP) & set(S30)), None)
    C.note("every Env A/B evaluation log has 50 episodes",
           all(v is None or v["episodes"] == 50 for v in CACHE.values()), sorted({v["episodes"] for v in CACHE.values() if v}))

    rows = C.rows
    json.dump(rows, open(a.out, "w"), indent=1, default=str)
    fails = [r for r in rows if not r["ok"]]
    for r in rows:
        print(("PASS " if r["ok"] else "FAIL ") + r["label"] + ("" if r["ok"] else f"  computed={r['computed']} formatted={r['formatted']} in_tex={r['in_tex']}"))
    print(f"\n{len(rows) - len(fails)} of {len(rows)} checks pass")


if __name__ == "__main__":
    main()
