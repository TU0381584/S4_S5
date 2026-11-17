#!/usr/bin/env python3
"""Gate 3 items 3 to 5: effect sizes and split-sample results, from the stored evaluation logs only.
Run from framework/:  ../venv/bin/python ../experiments/scripts/gate3_effects.py
Writes experiments/results/gate3/effects.json and the LaTeX rows of the two tables
(main paper: acceptance ratios and effect sizes; Online Resource 1: comparisons by sample).

Hodges-Lehmann estimate: the median of the Walsh averages (d_i + d_j) / 2, i <= j, of the paired differences.
Matched-pairs rank-biserial correlation: (W+ - W-) / (W+ + W-) over the ranks of |d|, exact ties dropped,
the same ties the signed-rank test drops (differences rounded to 1e-9, as m66_verify.paired does)."""
import json, os, sys
import numpy as np
from scipy.stats import rankdata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m66_verify as V
from m66_verify import seeds_of, paired, holm, prio, S15, S30, S30_19, tie_round

OUT = "/home/kmanojp/oranslice_rig/experiments/results/gate3"
C30 = list(range(12000, 12030))
NAMES = {"single_agent_dqn": "DQN-SA", "independent_dqn": "DQN-I", "mappo_tuned": "MAPPO", "axiom2_mlp": "MLP encoder", "heuristic": "Static rule",
         "rule_static": "Shed all mMTC", "rule_accept_all": "Accept all", "rule_local": "Tuned local rule", "rule_neighbour": "Tuned neighbour-aware rule"}


def effect(a, b, f=lambda r: r["reward"]):
    k = sorted(set(a) & set(b))
    raw = np.array([f(a[s]) - f(b[s]) for s in k], float)
    w = (raw[:, None] + raw[None, :]) / 2.0
    hl = float(np.median(w[np.triu_indices(len(raw))]))
    d = tie_round(raw); d = d[d != 0]
    if len(d) == 0:
        return hl, 0.0
    r = rankdata(np.abs(d))
    return hl, float((r[d > 0].sum() - r[d < 0].sum()) / r.sum())


def sub(rows, sel):
    return {k: v for k, v in rows.items() if sel(k)}


def family(base, arms, sel, f=lambda r: r["reward"]):
    A = sub(base["axiom2"], sel)
    t = {b: paired(A, sub(base[b], sel), f) for b in arms}
    t = {b: v for b, v in t.items() if v["n"] > 0}
    h = holm({b: v["p"] for b, v in t.items()})
    for b in t:
        t[b]["p_holm"] = h[b]; t[b]["hl"], t[b]["rb"] = effect(A, sub(base[b], sel), f)
    return t


ORIG, ADDED, ALL = (lambda k: k < 11000), (lambda k: 11000 <= k < 12000), (lambda k: True)


def main():
    out = {}
    # ---- Env A, three gNBs (Table 3 family: five baselines plus the two learning-rate variants, which have stored seeds only)
    A = {a: seeds_of("m65_reviewer/base", a, S30) for a in ("axiom2", "axiom2_mlp", "mappo_tuned")}
    for a in ("heuristic", "single_agent_dqn", "independent_dqn", "single_agent_dqn_lr1e4", "independent_dqn_lr1e4"):
        A[a] = seeds_of("m63_reviewer/base", a, S30)
    armsA = ("axiom2_mlp", "heuristic", "single_agent_dqn", "single_agent_dqn_lr1e4", "independent_dqn", "independent_dqn_lr1e4", "mappo_tuned")
    out["A3"] = {"original": family(A, armsA, ORIG), "added": family(A, armsA, ADDED), "pooled": family(A, armsA, ALL)}
    cA = {a: seeds_of("m108/A_n3", a, C30, pool=False) for a in ("axiom2", "axiom2_mlp", "rule_static", "single_agent_dqn", "independent_dqn", "mappo_tuned")}
    cA["heuristic"] = cA.pop("rule_static")
    out["A3"]["confirmation"] = family(cA, ("axiom2_mlp", "heuristic", "single_agent_dqn", "independent_dqn", "mappo_tuned"), ALL)
    # ---- Env B, three gNBs, reward: H2 family (learned baselines and tuned rules, reward and compliance) and H1 (the two trivial rules)
    B = {a: seeds_of("m64/n3_fully_connected", a, S30) for a in ("axiom2", "independent_dqn", "single_agent_dqn", "mappo_tuned", "rule_local", "rule_neighbour",
                                                                    "rule_static", "rule_accept_all")}
    def famB(sel):
        A_ = sub(B["axiom2"], sel); t = {}
        for b in ("independent_dqn", "single_agent_dqn", "mappo_tuned", "rule_local", "rule_neighbour"):
            t[b + "|r"] = paired(A_, sub(B[b], sel)); t[b + "|s"] = paired(A_, sub(B[b], sel), prio)
        h = holm({k: v["p"] for k, v in t.items()})
        res = {}
        for b in ("independent_dqn", "single_agent_dqn", "mappo_tuned", "rule_local", "rule_neighbour"):
            x = dict(t[b + "|r"]); x["p_holm"] = h[b + "|r"]; x["hl"], x["rb"] = effect(A_, sub(B[b], sel)); res[b] = x
        h1 = {b: paired(A_, sub(B[b], sel)) for b in ("rule_static", "rule_accept_all")}
        hh = holm({b: v["p"] for b, v in h1.items()})
        for b in h1:
            x = dict(h1[b]); x["p_holm"] = hh[b]; x["hl"], x["rb"] = effect(A_, sub(B[b], sel)); res[b] = x
        return res
    out["B3"] = {"original": famB(ORIG), "added": famB(ADDED), "pooled": famB(ALL)}
    cB = {a: seeds_of("m108/B_n3", a, C30, pool=False) for a in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned", "axiom2_mlp",
                                                                   "rule_static", "rule_accept_all", "rule_local", "rule_neighbour")}
    out["B3"]["confirmation"] = family(cB, tuple(a for a in cB if a != "axiom2"), ALL)
    # ---- Env A scaling, priority-slice compliance: 18 tests per size (three layouts, three baselines, reward and compliance)
    for n, seeds in ((7, S15), (19, S30_19)):
        D = {t: {a: seeds_of(f"m65_scaling/n{n}_{t}", a, seeds) for a in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned")}
             for t in ("fully_connected", "ring", "hex")}
        out[f"A{n}"] = {}
        for name, sel in (("original", ORIG), ("added", ADDED), ("pooled", ALL)):
            t = {}
            for lay in D:
                for b in ("single_agent_dqn", "independent_dqn", "mappo_tuned"):
                    A_ = sub(D[lay]["axiom2"], sel); B_ = sub(D[lay][b], sel)
                    t[f"{lay}|{b}|s"] = paired(A_, B_, prio); t[f"{lay}|{b}|r"] = paired(A_, B_)
                    t[f"{lay}|{b}|s"]["hl"], t[f"{lay}|{b}|s"]["rb"] = effect(A_, B_, prio)
            h = holm({k: v["p"] for k, v in t.items()})
            s = [k for k in t if k.endswith("|s")]
            out[f"A{n}"][name] = {"n": sorted({t[k]["n"] for k in s}), "min_lead": 100 * min(t[k]["diff"] for k in s), "max_lead": 100 * max(t[k]["diff"] for k in s),
                                  "min_hl": 100 * min(t[k]["hl"] for k in s), "min_rb": min(t[k]["rb"] for k in s), "max_p_holm": max(h[k] for k in s)}
    c7 = {a: seeds_of("m108/A_n7_ring", a, C30, pool=False) for a in ("axiom2", "single_agent_dqn")}
    x = paired(c7["axiom2"], c7["single_agent_dqn"], prio); x["hl"], x["rb"] = effect(c7["axiom2"], c7["single_agent_dqn"], prio)
    out["A7"]["confirmation_ring_dqnsa"] = x
    json.dump(out, open(f"{OUT}/effects.json", "w"), indent=1, default=float)

    # ---- LaTeX rows
    adm = json.load(open(f"{OUT}/admission.json"))
    def pf(p):
        return "$<$0.0001" if p < 0.0001 else (f"{p:.4f}" if p < 0.01 else f"{p:.3f}" if p < 0.1 else f"{p:.2f}")
    def sg(x, nd=3):
        return ("$-$" if x < 0 else "") + f"{abs(x):.{nd}f}"
    main_rows = []
    for env, order, fam in (("A3", ("heuristic", "axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned"), out["A3"]["pooled"]),
                            ("B3", ("rule_accept_all", "rule_static", "rule_local", "rule_neighbour", "axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned"), out["B3"]["pooled"])):
        for a in order:
            ac = adm[env][a]["acceptance"]
            cells = f"{100 * ac['urllc']:.1f} & {100 * ac['embb']:.1f} & {100 * ac['mmtc']:.1f}"
            if a == "axiom2":
                main_rows.append(f"AXIOM & {cells} & -- & -- & -- & -- \\\\")
            else:
                v = fam[a]
                main_rows.append(f"{NAMES[a]} & {cells} & {sg(v['diff'])} & {sg(v['hl'])} & {sg(v['rb'], 2)} & {pf(v['p_holm'])} \\\\")
        main_rows.append("%%")
    open(f"{OUT}/table_main_rows.tex", "w").write("\n".join(main_rows) + "\n")
    supp_rows = []
    for env, order in (("A3", ("single_agent_dqn", "independent_dqn", "mappo_tuned", "axiom2_mlp", "heuristic")),
                       ("B3", ("single_agent_dqn", "independent_dqn", "mappo_tuned", "rule_static", "rule_accept_all", "rule_local", "rule_neighbour"))):
        for a in order:
            o, d, p, c = (out[env][k][a] for k in ("original", "added", "pooled", "confirmation"))
            supp_rows.append(f"{NAMES[a]} & {sg(o['diff'])} & {pf(o['p_holm'])} & {sg(d['diff'])} & {pf(d['p_holm'])} & {sg(p['diff'])} & {sg(p['hl'])} & {sg(p['rb'], 2)} & {pf(p['p_holm'])} & {sg(c['diff'])} & {pf(c['p_holm'])} \\\\")
        supp_rows.append("%%")
    for n in (7, 19):
        o, d, p = (out[f"A{n}"][k] for k in ("original", "added", "pooled"))
        supp_rows.append(f"{n} gNBs & {o['min_lead']:.1f} & {pf(o['max_p_holm'])} & {d['min_lead']:.1f} & {pf(d['max_p_holm'])} & {p['min_lead']:.1f} & {p['min_hl']:.1f} & {sg(p['min_rb'], 2)} & {pf(p['max_p_holm'])} & & \\\\")
    open(f"{OUT}/table_supp_rows.tex", "w").write("\n".join(supp_rows) + "\n")
    print(open(f"{OUT}/table_main_rows.tex").read()); print(open(f"{OUT}/table_supp_rows.tex").read())
    print("A7 confirmation ring vs DQN-SA compliance:", out["A7"]["confirmation_ring_dqnsa"])
    print("MLP A3 pooled HL", out["A3"]["pooled"]["axiom2_mlp"]["hl"], "rb", out["A3"]["pooled"]["axiom2_mlp"]["rb"])


if __name__ == "__main__":
    main()
