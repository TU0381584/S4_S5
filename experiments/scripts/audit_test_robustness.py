#!/usr/bin/env python3
"""Confidence check (2026-11-10): do the paper's verdicts depend on the choice of test?

Every reported comparison uses the two-sided Wilcoxon signed-rank test (zero_method wilcox), which tests the ranks
of the paired differences, not their mean. This script recomputes each main-text Holm family with a second,
assumption-light test of the mean paired difference: an exact-by-simulation sign-flip permutation test
(200,000 random sign assignments, default_rng(0), two-sided, p = (k + 1) / (B + 1)). Holm is applied within each
family as in the paper. A test "agrees" when both procedures give the same verdict at Holm-adjusted p < 0.05
(significant in the same direction, or not significant). The cells and families are those the verifier and M82
audit check for the corresponding sentences.

Usage (cwd framework/): ../venv/bin/python ../experiments/scripts/audit_test_robustness.py --out ../experiments/results/audit_test_robustness.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/plots")
from m66_verify import S15, S30, S30_19, holm, paired, prio, seeds_of  # noqa: E402

R = lambda r: r["reward"]
P = lambda r: 100 * prio(r)
ARMS = ["axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned"]
LAY = ("fully_connected", "ring", "hex")
B = 200_000


def perm_p(d, rng):
    d = np.asarray(d, float)
    if not np.any(d):
        return 1.0
    obs = abs(d.mean())
    k = 0
    for _ in range(B // 20_000):
        s = rng.choice((-1.0, 1.0), size=(20_000, len(d)))
        k += int((np.abs((s * d).mean(axis=1)) >= obs - 1e-12).sum())
    return (k + 1) / (B + 1)


def family(name, pairs, rng):
    """pairs: {label: (a_rows, b_rows, f)}; returns per-test Wilcoxon and permutation results with Holm in-family."""
    t = {}
    for lab, (a, b, f) in pairs.items():
        w = paired(a, b, f)
        common = sorted(set(a) & set(b))
        d = [f(a[s]) - f(b[s]) for s in common]
        t[lab] = {"n": w["n"], "diff": w["diff"], "p_wilcoxon": w["p"], "p_perm": perm_p(d, rng)}
    hw, hp = holm({k: v["p_wilcoxon"] for k, v in t.items()}), holm({k: v["p_perm"] for k, v in t.items()})
    for k, v in t.items():
        v["holm_wilcoxon"], v["holm_perm"] = hw[k], hp[k]
        sw, sp = hw[k] < 0.05, hp[k] < 0.05
        v["verdict_wilcoxon"] = ("ahead" if v["diff"] > 0 else "behind") if sw else "n.s."
        v["verdict_perm"] = ("ahead" if v["diff"] > 0 else "behind") if sp else "n.s."
        v["agree"] = v["verdict_wilcoxon"] == v["verdict_perm"]
    return t


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    rng = np.random.default_rng(0)
    F = {}
    # Env A, three gNBs (Table 3): AXIOM against each learned baseline, reward per step
    # the seven-test family the verifier forms for the Table 3 sentence (MLP variant, static rule, both DQN learning rates)
    A3 = {x: seeds_of("m65_reviewer/base", x, S30) for x in ("axiom2", "axiom2_mlp", "mappo_tuned")}
    A3.update({x: seeds_of("m63_reviewer/base", x, S30) for x in ("heuristic", "single_agent_dqn", "independent_dqn",
                                                                  "single_agent_dqn_lr1e4", "independent_dqn_lr1e4")})
    F["EnvA_3gNB_table3_family"] = family("A3", {b: (A3["axiom2"], A3[b], R) for b in ("axiom2_mlp", "heuristic", "single_agent_dqn",
                                                 "single_agent_dqn_lr1e4", "independent_dqn", "independent_dqn_lr1e4", "mappo_tuned")}, rng)
    # Env B, three gNBs (Table 5): H1 against the two trivial rules, and the learned baselines, reward per step
    B3 = {x: seeds_of("m64/n3_fully_connected", x, S30) for x in ARMS + ["rule_static", "rule_accept_all", "rule_local"]}
    F["EnvB_3gNB_H1_rules"] = family("B3r", {b: (B3["axiom2"], B3[b], R) for b in ("rule_static", "rule_accept_all")}, rng)
    F["EnvB_3gNB_learned"] = family("B3l", {b: (B3["axiom2"], B3[b], R) for b in ARMS[1:]}, rng)
    F["EnvB_3gNB_tuned_rule"] = family("B3t", {"rule_local": (B3["axiom2"], B3["rule_local"], R)}, rng)
    # Env A scaling families at 7 and 19 gNBs: 3 layouts x 3 baselines x (compliance, reward), 18 tests each
    for n, ss in ((7, S15), (19, S30_19)):
        D = {t: {x: seeds_of(f"m65_scaling/n{n}_{t}", x, ss) for x in ARMS} for t in LAY}
        F[f"EnvA_{n}gNB_scaling"] = family(f"A{n}", {f"{t}|{b}|{m}": (D[t]["axiom2"], D[t][b], f) for t in LAY for b in ARMS[1:]
                                                     for m, f in (("compliance", P), ("reward", R))}, rng)
    # 37 gNBs (M73): AXIOM per layout; the layout-independent baselines ran once, on the hex seeds
    r37 = {t: {x: seeds_of(f"m73/A_n37_{t}", x, S30_19 if t == "hex" else S15) for x in ARMS} for t in LAY}
    for t in ("ring", "fully_connected"):
        for b in ARMS[1:]:
            r37[t][b] = {s: v for s, v in r37["hex"][b].items() if s in S15}
    F["EnvA_37gNB_scaling"] = family("A37", {f"{t}|{b}|{m}": (r37[t]["axiom2"], r37[t][b], f) for t in LAY for b in ARMS[1:]
                                             for m, f in (("compliance", P), ("reward", R))}, rng)
    # Env B, 19 gNBs, past the tuning load: AXIOM against the carried tuned rule (M76)
    from paper5_fig_superiority import shift_row
    F["EnvB_19gNB_loadshift_vs_tuned_rule"] = family("L19", {L: ({s: shift_row("m76/b1_shift_n19", L, "axiom2", s) for s in S15},
                                                                 {s: shift_row("m76/b1_shift_n19", L, "rule_local_transfer", s) for s in S15}, R)
                                                             for L in ("load_1.10", "load_1.15", "load_1.20")}, rng)
    # per-slice heads: AXIOM against the shared-head variant (M70), the ablation family as the verifier forms it
    ABL = list(range(900, 912)) + [1000, 1001, 1002]
    cells = {"A3": ("m65_n3_view", "A_n3", S30), "B3": ("m64/n3_fully_connected", "B_n3", S30), "A19": ("m65_scaling/n19_ring", "A_n19_ring", ABL)}
    pairs = {}
    for k, (c, d, ss) in cells.items():
        ax, va = seeds_of(c, "axiom2", ss), seeds_of(f"m70/R4_sharedhead/{d}", "axiom2", ss)
        pairs[f"{k}|reward"], pairs[f"{k}|compliance"] = (ax, va, R), (ax, va, P)
    F["ablation_shared_head"] = family("SH", pairs, rng)
    n_all = sum(len(v) for v in F.values()); n_agree = sum(t["agree"] for v in F.values() for t in v.values())
    out = {"families": F, "tests": n_all, "agree": n_agree, "disagreements": {f"{fk}:{k}": t for fk, v in F.items() for k, t in v.items() if not t["agree"]}}
    json.dump(out, open(a.out, "w"), indent=1)
    print(f"{n_all} tests in {len(F)} families; Wilcoxon and permutation verdicts agree on {n_agree}")
    for fk, v in F.items():
        print(f"  {fk:38s} {sum(t['agree'] for t in v.values())}/{len(v)} agree; Wilcoxon sig {sum(t['verdict_wilcoxon'] != 'n.s.' for t in v.values())}, "
              f"permutation sig {sum(t['verdict_perm'] != 'n.s.' for t in v.values())}")
    for k, t in out["disagreements"].items():
        print("  DISAGREE", k, {x: (round(y, 5) if isinstance(y, float) else y) for x, y in t.items()})


if __name__ == "__main__":
    main()
