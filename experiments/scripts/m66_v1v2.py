#!/usr/bin/env python3
"""M66 V1 (reproducibility) and V2 (fresh seeds 3000+) analysis.

Uses the independent reader in m66_verify.py, not the original analysis
pipeline. Criteria are the ones pre-stated in docs/PAPER5_M66_verification_plan.md
(commit c94cf9b). Every criterion is reported as HOLDS or FAILS; nothing is
dropped when it fails.

Usage: m66_v1v2.py --out experiments/results/m66_v1v2.json
"""
import argparse
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import ROOT, S30, holm, paired, prio, seeds_of  # noqa: E402

TOL = 1e-9


def v1_cell(fresh_cell, stored_cell, arm, seeds, stored_arm=None):
    a = seeds_of(fresh_cell, arm, seeds)
    b = seeds_of(stored_cell, stored_arm or arm, seeds)
    rows, worst = [], 0.0
    for s in seeds:
        if s not in a or s not in b:
            rows.append({"seed": s, "missing": [k for k, d in (("rerun", a), ("stored", b)) if s not in d]})
            worst = math.inf
            continue
        x, y = a[s], b[s]
        d = {"reward": abs(x["reward"] - y["reward"]), "blocks": abs(x["blocks"] - y["blocks"]),
             "sla": max(abs(x["sla"][k] - y["sla"][k]) for k in ("urllc", "embb", "mmtc"))}
        worst = max(worst, d["reward"], d["sla"], d["blocks"])
        rows.append({"seed": s, "rerun": x["reward"], "stored": y["reward"], **{"d_" + k: v for k, v in d.items()}})
    return {"fresh": f"{fresh_cell}/{arm}", "stored": f"{stored_cell}/{stored_arm or arm}", "n": len(seeds),
            "exact": worst <= TOL, "max_abs_diff": worst, "rows": rows}


def crit(label, ok, detail):
    print(f"[{'HOLDS' if ok else 'FAILS'}] {label}: {detail}")
    return {"label": label, "holds": bool(ok), "detail": detail}


def summ(rows):
    r = [v["reward"] for v in rows.values()]
    return {"n": len(r), "reward": float(np.mean(r)), "prio": float(np.mean([prio(v) for v in rows.values()])),
            "urllc": float(np.mean([v["sla"]["urllc"] for v in rows.values()])),
            "embb": float(np.mean([v["sla"]["embb"] for v in rows.values()])),
            "collapsed": int(sum(v["collapsed"] for v in rows.values()))}


def tests(ref, others, f=lambda r: r["reward"]):
    t = {k: paired(ref, v, f) for k, v in others.items()}
    ph = holm({k: v["p"] for k, v in t.items()})
    for k in t:
        t[k]["p_holm"] = ph[k]
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = {"v1": {}, "v2": {}, "criteria": []}
    C = out["criteria"]

    # ---------------- V1
    print("== V1 reproducibility")
    R = "m66_repro"
    v1 = [("B_n3 axiom2", f"{R}/B_n3", "m64/n3_fully_connected", "axiom2", range(900, 905), None),
          ("B_n3 mappo_tuned", f"{R}/B_n3", "m64/n3_fully_connected", "mappo_tuned", range(900, 905), None),
          ("B_n3 independent_dqn", f"{R}/B_n3", "m64/n3_fully_connected", "independent_dqn", range(900, 903), None),
          ("B_n3 single_agent_dqn", f"{R}/B_n3", "m64/n3_fully_connected", "single_agent_dqn", range(900, 903), None),
          ("B_n3 rule_static", f"{R}/B_n3", "m64/n3_fully_connected", "rule_static", S30, None),
          ("B_n3 rule_local", f"{R}/B_n3", "m64/n3_fully_connected", "rule_local", S30, None),
          ("A_n3 axiom2", f"{R}/A_n3", "m65_reviewer/base", "axiom2", range(900, 905), None),
          ("A_n19_ring axiom2", f"{R}/A_n19_ring", "m65_scaling/n19_ring", "axiom2", range(900, 902), None),
          ("B_n7_ring axiom2_mlp", f"{R}/B_n7_ring", "m64/n7_ring", "axiom2_mlp", range(900, 903), None),
          ("A_n3 rule_static vs stored heuristic (oracle identity)", f"{R}/A_n3_oracle_equiv", "m65_n3_view",
           "rule_static", S30, "heuristic")]
    for label, fc, sc, arm, seeds, sarm in v1:
        r = v1_cell(fc, sc, arm, list(seeds), sarm)
        out["v1"][label] = r
        nondet = arm == "single_agent_dqn"
        detail = f"max |diff| over reward, blocks, SLA = {r['max_abs_diff']:.3g} on {r['n']} seeds"
        if nondet:
            C.append(crit(f"V1 {label} (not predicted exact; size reported)", True, detail))
        else:
            C.append(crit(f"V1 {label} exact to 1e-9", r["exact"], detail))

    # ---------------- V2
    print("== V2 fresh seeds")
    F = "m66_fresh"
    s20, s15, s10 = list(range(3000, 3020)), list(range(3000, 3015)), list(range(3000, 3010))

    # Env A N=3
    d = {k: seeds_of(f"{F}/A_n3", k, s20) for k in ("axiom2", "independent_dqn", "single_agent_dqn", "mappo_tuned", "rule_static")}
    out["v2"]["A_n3"] = {"summary": {k: summ(v) for k, v in d.items()},
                         "tests": tests(d["axiom2"], {k: d[k] for k in ("independent_dqn", "single_agent_dqn", "mappo_tuned")}),
                         "oracle_gap": paired(d["axiom2"], d["rule_static"])}
    S = out["v2"]["A_n3"]["summary"]; T = out["v2"]["A_n3"]["tests"]
    ratio = S["axiom2"]["reward"] / S["rule_static"]["reward"]
    C.append(crit("V2 Env A N=3 AXIOM within 2% of oracle", ratio >= 0.98,
                  f"{S['axiom2']['reward']:.3f} vs {S['rule_static']['reward']:.3f} = {100 * ratio:.1f}%, ties {out['v2']['A_n3']['oracle_gap']['ties']}/{S['axiom2']['n']}"))
    for k in ("independent_dqn", "mappo_tuned"):
        C.append(crit(f"V2 Env A N=3 AXIOM beats {k} p<0.05", T[k]["diff"] > 0 and T[k]["p"] < 0.05,
                      f"diff {T[k]['diff']:+.3f}, p {T[k]['p']:.2g}, p_holm {T[k]['p_holm']:.2g}, W/T/L {T[k]['wins']}/{T[k]['ties']}/{T[k]['losses']}"))
    k = "single_agent_dqn"
    C.append(crit("V2 Env A N=3 vs single-agent DQN (not predicted, reported)", True,
                  f"diff {T[k]['diff']:+.3f}, p {T[k]['p']:.2g}, W/T/L {T[k]['wins']}/{T[k]['ties']}/{T[k]['losses']}"))

    # Env A N=19 ring
    base = ("independent_dqn", "single_agent_dqn", "mappo_tuned")
    d = {k: seeds_of(f"{F}/A_n19_ring", k, s15) for k in ("axiom2",) + base}
    out["v2"]["A_n19_ring"] = {"summary": {k: summ(v) for k, v in d.items()},
                               "tests_reward": tests(d["axiom2"], {k: d[k] for k in base}),
                               "tests_prio": tests(d["axiom2"], {k: d[k] for k in base}, prio)}
    S = out["v2"]["A_n19_ring"]["summary"]
    C.append(crit("V2 Env A N=19 AXIOM priority SLA >= 90%", S["axiom2"]["prio"] >= 0.90,
                  f"{100 * S['axiom2']['prio']:.1f}% on {S['axiom2']['n']} seeds, collapsed {S['axiom2']['collapsed']}"))
    for k in base:
        C.append(crit(f"V2 Env A N=19 {k} priority SLA <= 75%", S[k]["prio"] <= 0.75,
                      f"{100 * S[k]['prio']:.1f}% on {S[k]['n']} seeds, collapsed {S[k]['collapsed']}"))
        for m in ("reward", "prio"):
            t = out["v2"]["A_n19_ring"]["tests_" + m][k]
            C.append(crit(f"V2 Env A N=19 AXIOM beats {k} on {m} p<0.05", t["diff"] > 0 and t["p"] < 0.05,
                          f"diff {t['diff']:+.4f}, p {t['p']:.2g}, p_holm {t['p_holm']:.2g}, W/T/L {t['wins']}/{t['ties']}/{t['losses']}"))

    # Env B N=3
    learned = ("independent_dqn", "single_agent_dqn", "mappo_tuned")
    rules = ("rule_static", "rule_accept_all", "rule_local", "rule_neighbour")
    d = {k: seeds_of(f"{F}/B_n3", k, s20) for k in ("axiom2",) + learned + rules}
    out["v2"]["B_n3"] = {"summary": {k: summ(v) for k, v in d.items()},
                         "tests": tests(d["axiom2"], {k: d[k] for k in learned + rules})}
    S = out["v2"]["B_n3"]["summary"]; T = out["v2"]["B_n3"]["tests"]
    for k in ("rule_static", "rule_accept_all"):
        C.append(crit(f"V2 Env B N=3 AXIOM beats {k}", T[k]["diff"] > 0 and T[k]["p"] < 0.05,
                      f"diff {T[k]['diff']:+.3f}, p {T[k]['p']:.2g}, W/T/L {T[k]['wins']}/{T[k]['ties']}/{T[k]['losses']}"))
    for k in learned:
        C.append(crit(f"V2 Env B N=3 AXIOM mean reward above {k}", S["axiom2"]["reward"] > S[k]["reward"],
                      f"{S['axiom2']['reward']:.3f} vs {S[k]['reward']:.3f}, p {T[k]['p']:.2g}, p_holm {T[k]['p_holm']:.2g}"))
    C.append(crit("V2 Env B N=3 rule_local beats AXIOM", S["rule_local"]["reward"] > S["axiom2"]["reward"],
                  f"{S['rule_local']['reward']:.3f} vs {S['axiom2']['reward']:.3f}, p {T['rule_local']['p']:.2g}"))

    # Env B N=7 ring
    learned7 = ("axiom2", "axiom2_mlp", "independent_dqn", "single_agent_dqn", "mappo_tuned")
    d = {k: seeds_of(f"{F}/B_n7_ring", k, s10) for k in learned7 + ("rule_static", "rule_local")}
    out["v2"]["B_n7_ring"] = {"summary": {k: summ(v) for k, v in d.items()},
                              "rule_local_vs": {k: paired(d["rule_local"], d[k]) for k in learned7},
                              "axiom_vs_mlp_reward": paired(d["axiom2"], d["axiom2_mlp"]),
                              "axiom_vs_mlp_prio": paired(d["axiom2"], d["axiom2_mlp"], prio),
                              "axiom_vs_static": paired(d["axiom2"], d["rule_static"])}
    S = out["v2"]["B_n7_ring"]["summary"]
    for k in learned7:
        t = out["v2"]["B_n7_ring"]["rule_local_vs"][k]
        C.append(crit(f"V2 Env B N=7 rule_local beats {k}", S["rule_local"]["reward"] > S[k]["reward"],
                      f"{S['rule_local']['reward']:.3f} vs {S[k]['reward']:.3f}, p {t['p']:.2g}"))
    for m in ("reward", "prio"):
        t = out["v2"]["B_n7_ring"]["axiom_vs_mlp_" + m]
        C.append(crit(f"V2 Env B N=7 no significant AXIOM advantage over MLP on {m}", not (t["diff"] > 0 and t["p"] < 0.05),
                      f"diff {t['diff']:+.4f}, p {t['p']:.2g}, W/T/L {t['wins']}/{t['ties']}/{t['losses']}"))
    t = out["v2"]["B_n7_ring"]["axiom_vs_static"]
    C.append(crit("V2 Env B N=7 AXIOM vs static rule (reported)", True, f"diff {t['diff']:+.3f}, p {t['p']:.2g}"))

    n_fail = sum(not c["holds"] for c in C)
    print(f"== {len(C) - n_fail}/{len(C)} hold")
    out["n_criteria"], out["n_fail"] = len(C), n_fail
    json.dump(out, open(a.out, "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
