#!/usr/bin/env python3
"""Recompute every 95% bootstrap CI quoted in the manuscript with the
order-independent boot_ci (fresh RandomState(0) per interval), and print the
text each should read. --apply rewrites main.tex where a printed value differs."""
import argparse, os, re, sys
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
from m62_analysis import boot_ci, eval_log, seed_metrics
R = "/home/kmanojp/oranslice_rig/experiments/results"
S30, S10, REP = list(range(900, 930)), list(range(900, 910)), list(range(1000, 1010))
S30_19 = list(range(900, 912)) + [1000, 1001, 1002] + list(range(912, 927))
def rows(cell, arm, seeds):
    return {s: seed_metrics(p) for s in seeds if (p := eval_log(f"{R}/{cell}", arm, s))}
def fmt(lo, hi, d=2):
    f = lambda v: (f"$-${abs(v):.{d}f}" if v < 0 else f"{v:.{d}f}")
    return f"[{f(lo)}, {f(hi)}]"
out = []
A = {a: rows("m65_reviewer/base", a, S30) for a in ("axiom2", "axiom2_mlp", "mappo_tuned")}
A.update({a: rows("m63_reviewer/base", a, S30) for a in ("heuristic", "single_agent_dqn", "single_agent_dqn_lr1e4", "independent_dqn", "independent_dqn_lr1e4")})
t3 = [("heuristic", "Oracle rule"), ("axiom2", "AXIOM"), ("axiom2_mlp", "AXIOM, MLP encoder"), ("single_agent_dqn", "DQN-SA"),
      ("single_agent_dqn_lr1e4", "\\quad at LR $10^{-4}$", ), ("independent_dqn", "DQN-I"), ("independent_dqn_lr1e4", "\\quad at LR $10^{-4}$"), ("mappo_tuned", "MAPPO")]
for arm, nm in t3:
    v = [r["reward"] for r in A[arm].values()]
    out.append((f"{sum(v)/len(v):.3f} [", fmt(*boot_ci(v)), "T3 " + arm))
B = {a: rows("m64/n3_fully_connected", a, S30) for a in ("rule_accept_all", "rule_static", "rule_local", "rule_neighbour", "axiom2", "axiom2_mlp", "single_agent_dqn", "independent_dqn", "mappo_tuned")}
for arm, r in B.items():
    v = [x["reward"] for x in r.values()]
    out.append((f"{sum(v)/len(v):.3f} [", fmt(*boot_ci(v)), "T4 " + arm))
def dci(a, b, seeds, label, key):
    d = [a[s]["reward"] - b[s]["reward"] for s in seeds]
    out.append((key, fmt(*boot_ci(d)), label))
dci(A["axiom2"], A["independent_dqn"], S30, "A3 vs indep", "1.110 more reward per step than DQN-I, with 95\\% CI ")
dci(A["axiom2"], A["mappo_tuned"], S30, "A3 vs MAPPO", "It earns 2.685 more than MAPPO, with 95\\% CI ")
dci(A["axiom2"], A["single_agent_dqn"], S30, "A3 vs single", "DQN-SA, 0.311 with 95\\% CI ")
dci(A["axiom2"], A["axiom2_mlp"], S30, "A3 vs MLP", "0.058 more reward per step at three gNBs with 95\\% CI ")
cen = rows("m65_reviewer/base", "axiom2", S10); fed = rows("m65_m3", "fl_gat_ctde_sigma0.0", S10)
dci(cen, fed, S10, "federation", "$+0.427$ with 95\\% CI ")
cr = rows("m65_reviewer/replication", "axiom2", REP); fr = rows("m65_m3_replication", "fl_gat_ctde_sigma0.0", REP)
dci(cr, fr, REP, "federation replication", "$+0.968$, with 95\\% CI ")
pr = [100 * 0.5 * (r["sla"]["urllc"] + r["sla"]["embb"]) for t in ("fully_connected", "ring", "hex") for r in rows(f"m65_scaling/n19_{t}", "axiom2", S30_19).values()]
lo, hi = boot_ci(pr)
out.append(("97.3\\% with 95\\% CI ", f"[{lo:.1f}\\%, {hi:.1f}\\%]", "N19 pooled"))
ap = argparse.ArgumentParser(); ap.add_argument("--tex"); ap.add_argument("--apply", action="store_true"); a = ap.parse_args()
tex = open(a.tex).read() if a.tex else ""
changes = 0
# CIs moved to Online Resource 1 are looked up there too (read only; --apply edits main.tex alone)
supp_path = os.path.join(os.path.dirname(a.tex), "supplementary.tex") if a.tex else ""
supp = open(supp_path).read() if supp_path and os.path.exists(supp_path) else ""
# the MLP variant's table rows were cut from OR1 on 2026-10-31, and only what the documents say is checked
out = [o for o in out if o[2] not in ("T3 axiom2_mlp", "T4 axiom2_mlp")]
for key, ci, label in out:
    # find the CI that follows the key in the tex
    m = re.search(re.escape(key) + r"(\[[^\]]*\])", tex) if key.endswith("[") is False else re.search(re.escape(key[:-1]) + r"(\[[^\]]*\])", tex)
    if m is None and supp:
        ms = re.search(re.escape(key[:-1] if key.endswith("[") else key) + r"(\[[^\]]*\])", supp)
        if ms:
            print(f"{label:28s} text={ms.group(1)} recomputed={ci} {'same' if ms.group(1) == ci else 'DIFF'} (supplementary)")
            continue
    cur = m.group(1) if m else None
    status = "same" if cur == ci else "DIFF"
    print(f"{label:28s} text={cur} recomputed={ci} {status}")
    if a.apply and m and cur != ci:
        tex = tex[:m.start(1)] + ci + tex[m.end(1):]
        changes += 1
if a.apply:
    open(a.tex, "w").write(tex)
    print("applied", changes, "changes")
