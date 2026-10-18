#!/usr/bin/env python3
"""M66d analysis against addendum 3 of docs/PAPER5_M66_verification_plan.md (D1, D2).

Usage: m66d_analysis.py --out experiments/results/m66d_analysis.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import holm, mean, paired, prio, seeds_of  # noqa: E402
from m66c_analysis import crit, report, summ  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    C, out = [], {}
    S40, S20 = list(range(4000, 4040)), list(range(4000, 4020))

    d = {k: seeds_of("m66d_fresh/D1_A_n3", k, S40) for k in ("axiom2", "single_agent_dqn", "independent_dqn", "mappo_tuned", "rule_static")}
    s = {k: summ(v) for k, v in d.items()}
    t = {k: paired(d["axiom2"], d[k]) for k in ("single_agent_dqn", "independent_dqn", "mappo_tuned")}
    h = holm({k: v["p"] for k, v in t.items()})
    for k in t:
        t[k]["p_holm"] = h[k]
    out["D1"] = {"summary": s, "tests": t, "oracle_gap": paired(d["axiom2"], d["rule_static"])}
    frac = s["axiom2"]["reward"] / s["rule_static"]["reward"]
    crit(C, "D1 Env A N=3 AXIOM within 2% of oracle", s["axiom2"]["n"] == 40 and frac >= 0.98,
         f"{s['axiom2']['reward']:.3f} vs {s['rule_static']['reward']:.3f} = {100 * frac:.1f}%, ties {out['D1']['oracle_gap']['ties']}/40")
    for k in ("independent_dqn", "mappo_tuned"):
        crit(C, f"D1 AXIOM beats {k} at Holm p<0.05", t[k]["n"] == 40 and t[k]["diff"] > 0 and h[k] < 0.05,
             f"diff {t[k]['diff']:+.3f}, p_holm {h[k]:.3g}, W/T/L {t[k]['wins']}/{t[k]['ties']}/{t[k]['losses']}")
    k = "single_agent_dqn"
    report(C, "D1 AXIOM vs seeded single-agent DQN", f"n={t[k]['n']} diff {t[k]['diff']:+.3f}, p {t[k]['p']:.3g}, p_holm {h[k]:.3g}, "
           f"W/T/L {t[k]['wins']}/{t[k]['ties']}/{t[k]['losses']}, single collapsed {s[k]['collapsed']}")

    d = {k: seeds_of("m66d_fresh/D2_load102", k, S20) for k in ("axiom2", "single_agent_dqn", "independent_dqn", "rule_static")}
    s = {k: summ(v) for k, v in d.items()}
    go = paired(d["axiom2"], d["rule_static"])
    out["D2"] = {"summary": s, "vs_oracle": go, "vs_single": paired(d["axiom2"], d["single_agent_dqn"]),
                 "vs_indep": paired(d["axiom2"], d["independent_dqn"]),
                 "per_seed_axiom_prio": {str(k_): prio(v) for k_, v in d["axiom2"].items()}}
    frac = s["axiom2"]["reward"] / s["rule_static"]["reward"]
    crit(C, "D2 load102 AXIOM within 2% of oracle and not significantly different", s["axiom2"]["n"] == 20 and frac >= 0.98 and go["p"] >= 0.05,
         f"{s['axiom2']['reward']:.3f} vs {s['rule_static']['reward']:.3f} = {100 * frac:.1f}%, p {go['p']:.3g}, ties {go['ties']}/20")
    crit(C, "D2 load102 AXIOM mean reward above both DQN baselines",
         s["axiom2"]["reward"] > s["single_agent_dqn"]["reward"] and s["axiom2"]["reward"] > s["independent_dqn"]["reward"],
         f"AXIOM {s['axiom2']['reward']:.3f}, single {s['single_agent_dqn']['reward']:.3f}, indep {s['independent_dqn']['reward']:.3f}")

    judged = [c for c in C if c["holds"] is not None]
    n_fail = sum(not c["holds"] for c in judged)
    print(f"== {len(judged) - n_fail}/{len(judged)} hold, {len(C) - len(judged)} reported only")
    out["criteria"], out["n_judged"], out["n_fail"] = C, len(judged), n_fail
    json.dump(out, open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
