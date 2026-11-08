#!/usr/bin/env python3
"""Figure audit, Phase 2.1: the rows of the Env A and Env B three-gNB results tables (main Tables 3 and 5 after the
audit), recomputed from the evaluation logs with m66_verify's reader, compliance as percentages to one decimal.

Reward CIs are the order-independent bootstrap CIs already printed in the paper (m62_analysis.boot_ci, checked by
m66_ci_recompute.py); they are recomputed here and must equal the printed ones. Prints LaTeX rows.
Run: python audit_table_rows.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m62_analysis import boot_ci  # noqa: E402
from m66_verify import S30, mean, paired, prio, seeds_of  # noqa: E402

pc = lambda x: f"{100 * x:.1f}"


def ci_txt(rows):
    lo, hi = boot_ci([r["reward"] for r in rows.values()])
    return f"[{lo:.2f}, {hi:.2f}]".replace("-", "$-$")


def env_a():
    A = {a: seeds_of("m65_reviewer/base", a, S30) for a in ("axiom2", "mappo_tuned")}
    A.update({a: seeds_of("m63_reviewer/base", a, S30) for a in ("heuristic", "single_agent_dqn", "independent_dqn")})
    names = [("heuristic", "Static rule"), None, ("axiom2", "AXIOM"), ("single_agent_dqn", "DQN-SA"), ("independent_dqn", "DQN-I"),
             ("mappo_tuned", "MAPPO")]
    out = []
    for item in names:
        if item is None:
            out.append("\\midrule")
            continue
        arm, nm = item
        r = A[arm]
        prec = [x["precision"] for x in r.values() if x["precision"] is not None]
        share = 100 * mean(r) / mean(A["heuristic"])
        if arm == "axiom2":
            wtl = "{--}"
        else:
            p = paired(A["axiom2"], r)
            wtl = f"{p['wins']}/{p['ties']}/{p['losses']}"
        out.append(f"{nm} & {mean(r):.3f} & {ci_txt(r)} & {share:.1f} & {wtl} & {sum(prec) / len(prec):.3f} & "
                   f"{sum(x['collapsed'] for x in r.values())}/30 & {pc(mean(r, lambda x: x['sla']['urllc']))} & "
                   f"{pc(mean(r, lambda x: x['sla']['embb']))} & {pc(mean(r, lambda x: x['sla']['mmtc']))} \\\\")
    return out


def env_b():
    B = {a: seeds_of("m64/n3_fully_connected", a, S30) for a in
         ("axiom2", "independent_dqn", "single_agent_dqn", "mappo_tuned", "rule_static", "rule_accept_all", "rule_local", "rule_neighbour")}
    names = [("rule_accept_all", "Accept all"), ("rule_static", "Shed all mMTC"), ("rule_local", "Tuned local rule"),
             ("rule_neighbour", "Tuned neighbour-aware rule"), None, ("axiom2", "AXIOM"), ("single_agent_dqn", "DQN-SA"),
             ("independent_dqn", "DQN-I"), ("mappo_tuned", "MAPPO")]
    out = []
    for item in names:
        if item is None:
            out.append("\\midrule")
            continue
        arm, nm = item
        r = B[arm]
        share = 100 * mean(r) / mean(B["rule_local"])
        if arm == "axiom2":
            w1 = w2 = "{--}"
        else:
            p1, p2 = paired(B["axiom2"], r), paired(B["axiom2"], r, prio)
            w1, w2 = f"{p1['wins']}/{p1['ties']}/{p1['losses']}", f"{p2['wins']}/{p2['ties']}/{p2['losses']}"
        out.append(f"{nm} & {mean(r):.3f} & {ci_txt(r)} & {share:.1f} & {w1} & {w2} & {pc(mean(r, lambda x: x['sla']['urllc']))} & "
                   f"{pc(mean(r, lambda x: x['sla']['embb']))} & {pc(mean(r, lambda x: x['sla']['mmtc']))} \\\\")
    return out


if __name__ == "__main__":
    print("% Env A, three gNBs"); print("\n".join(env_a()))
    print("% Env B, three gNBs"); print("\n".join(env_b()))
