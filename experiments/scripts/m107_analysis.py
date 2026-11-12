#!/usr/bin/env python3
"""M107 analysis (docs/PAPER5_M107_preregistration.md), committed with it before any M107 run.
Each headline family is computed on the stored seeds, on the new seeds alone, and pooled.
--jobs <path> writes the job list and exits. Run from framework/:
  ../venv/bin/python ../experiments/scripts/m107_analysis.py --out ../experiments/results/m107/analysis.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import S15, S30, S30_19, holm, paired, prio, seeds_of, tie_round  # noqa: E402

E30, E15 = list(range(11000, 11030)), list(range(11000, 11015))
LAY = ("fully_connected", "ring", "hex")
LEARN = ("single_agent_dqn", "independent_dqn", "mappo_tuned")
R = lambda r: r["reward"]
P = lambda r: 100 * prio(r)
ENV = "M63_BACKLOG_RESET=1 M64_AXIOM_V2=1"
SEL = "/home/kmanojp/oranslice_rig/experiments/results/m64/n3_fully_connected"


def ci(d):
    d = np.asarray(d, float)
    m = d[np.random.default_rng(0).integers(0, len(d), size=(10000, len(d)))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def rows(stored, ext, arm, which):
    """stored: (cell, seeds) of the original sample; ext: m107 cell; which: stored, new or pooled."""
    arm_s, arm_n = arm if isinstance(arm, tuple) else (arm, arm)   # stored and new arm names can differ
    a = {("s", s): r for s, r in seeds_of(stored[0], arm_s, stored[1]).items()} if which in ("stored", "pooled") else {}
    b = {("n", s): r for s, r in seeds_of(f"m107/{ext[0]}", arm_n, ext[1]).items()} if which in ("new", "pooled") else {}
    return {**a, **b}


def family(spec, which):
    t = {}
    for key, (sa, ea, arm_a), (sb, eb, arm_b) in spec:
        A, B = rows(sa, ea, arm_a, which), rows(sb, eb, arm_b, which)
        for m, f in (("reward", R), ("compliance", P)):
            x = paired(A, B, f)
            d = [f(A[k]) - f(B[k]) for k in sorted(set(A) & set(B))]
            x["ci"] = ci(d) if d else [0.0, 0.0]
            t[f"{key}|{m}"] = x
    h = holm({k: v["p"] for k, v in t.items()})
    for k, v in t.items():
        v["p_holm"] = h[k]
        v["verdict"] = ("AXIOM ahead" if v["diff"] > 0 else "AXIOM behind") if h[k] < 0.05 else "within chance"
    return t


def specs():
    out = {}
    a3 = (("m65_n3_view", S30), ("A_n3", E30))
    arm3 = lambda a: ("heuristic", "rule_static") if a == "rule_static" else a   # stored Env A static rule is named heuristic
    out["A3_table3"] = [(b, (a3[0], a3[1], "axiom2"), ((a3[0][0], S30), a3[1], arm3(b))) for b in LEARN + ("rule_static",)]
    b3 = (("m64/n3_fully_connected", S30), ("B_n3", E30))
    out["B3_H1_table5"] = [(b, (b3[0], b3[1], "axiom2"), (b3[0], b3[1], b)) for b in
                           LEARN + ("rule_static", "rule_accept_all", "rule_local", "rule_neighbour")]
    for n, ss, es in ((7, S15, E15), (19, S30_19, E30)):
        out[f"A{n}_scaling"] = [(f"{t}|{b}", ((f"m65_scaling/n{n}_{t}", ss), (f"A_n{n}_{t}", es), "axiom2"),
                                 ((f"m65_scaling/n{n}_{t}", ss), (f"A_n{n}_{t}", es), b)) for t in LAY for b in LEARN]
    sp = []
    for t in LAY:
        ss, es = (S30_19, E30) if t == "hex" else (S15, E15)
        for b in LEARN:   # the baselines never read the layout and ran once, on the hex seeds
            sp.append((f"{t}|{b}", ((f"m73/A_n37_{t}", ss), (f"A_n37_{t}", es), "axiom2"), (("m73/A_n37_hex", ss), ("A_n37_hex", es), b)))
    out["A37_scaling"] = sp
    return out


def collapse(spec, which):
    out = {}
    for _, (sa, ea, arm_a), (sb, eb, arm_b) in spec:
        for (s_, e_, a_) in ((sa, ea, arm_a), (sb, eb, arm_b)):
            k = f"{e_[0]}|{a_ if isinstance(a_, str) else a_[1]}"
            if k not in out:
                r = rows(s_, e_, a_, which)
                out[k] = {"n": len(r), "collapsed": int(sum(v["collapsed"] for v in r.values())),
                          "reward": float(np.mean([v["reward"] for v in r.values()])) if r else None,
                          "compliance": float(np.mean([P(v) for v in r.values()])) if r else None}
    return out


def jobs(path):
    lines = []
    def add(name, args, seeds, arms, extra=""):
        for a in arms:
            if a.startswith("rule_"):
                env = ENV + (f" M107_RULE_SELECTION={SEL}/{a}_selection.json" if a in ("rule_local", "rule_neighbour") else "")
                lines.append(f"{name}_{a}|{env}|../experiments/scripts/m107_run.py --arm {a} {args} --seeds {' '.join(map(str, seeds))} "
                             f"--out-dir ../experiments/results/m107/{name}")
            else:
                for s in seeds:
                    lines.append(f"{name}_{a}_{s}|{ENV}|../experiments/scripts/m107_run.py --arm {a} {args} --seeds {s} "
                                 f"--out-dir ../experiments/results/m107/{name}")
    learned = ("axiom2",) + LEARN
    add("A_n37_hex", "--env A --n 37 --topology hex", E30, learned + ("rule_static", "rule_accept_all"))
    for t in ("ring", "fully_connected"):
        add(f"A_n37_{t}", f"--env A --n 37 --topology {t}", E15, ("axiom2",))
    for t in LAY:
        add(f"A_n19_{t}", f"--env A --n 19 --topology {t}", E30, learned + ("rule_static",) + (("rule_accept_all",) if t == "hex" else ()))
    for t in LAY:
        add(f"A_n7_{t}", f"--env A --n 7 --topology {t}", E15, learned + ("rule_static",) + (("rule_accept_all",) if t == "hex" else ()))
    add("B_n3", "--n 3", E30, learned + ("axiom2_mlp", "rule_static", "rule_accept_all", "rule_local", "rule_neighbour"))
    add("A_n3", "--env A --n 3", E30, learned + ("axiom2_mlp", "rule_static"))
    open(path, "w").write("\n".join(lines) + "\n")
    print(len(lines), "jobs ->", path)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out"); ap.add_argument("--jobs"); a = ap.parse_args()
    if a.jobs:
        return jobs(a.jobs)
    out = {}
    for name, sp in specs().items():
        out[name] = {w: family(sp, w) for w in ("stored", "new", "pooled")}
        out[name]["collapse"] = {w: collapse(sp, w) for w in ("stored", "new", "pooled")}
        st, nw, po = out[name]["stored"], out[name]["new"], out[name]["pooled"]
        out[name]["not_replicated_by_new"] = [k for k in st if st[k]["verdict"] == "AXIOM ahead" and nw[k]["verdict"] != "AXIOM ahead"]
        out[name]["pooled_verdict_changes"] = {k: [st[k]["verdict"], po[k]["verdict"]] for k in st if st[k]["verdict"] != po[k]["verdict"]}
        print(f"== {name}")
        for k in st:
            print(f"  {k:48s} stored {st[k]['diff']:+8.3f} {st[k]['verdict']:13s} | new {nw[k]['diff']:+8.3f} (n={nw[k]['n']}) {nw[k]['verdict']:13s} "
                  f"| pooled {po[k]['diff']:+8.3f} (n={po[k]['n']}) {po[k]['verdict']}")
        print("  not replicated by new seeds:", out[name]["not_replicated_by_new"])
        print("  pooled verdict changes:", out[name]["pooled_verdict_changes"])
    json.dump(out, open(a.out, "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
