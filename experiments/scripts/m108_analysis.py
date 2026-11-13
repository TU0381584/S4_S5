#!/usr/bin/env python3
"""M108 analysis (docs/PAPER5_M108_preregistration.md), committed with it before any M108 run.

M108 is a confirmation sample: 30 seeds never used before (12000 to 12029), run exactly as the stored and M107 runs,
for the verdicts that changed when M107 was pooled into the paper and the two leads M107's new seeds did not reproduce.
Each target is judged on the M108 seeds alone. The stored, M107 and M108 seeds pooled are reported for information.
--jobs <path> writes the job list and exits. Run from framework/:
  ../venv/bin/python ../experiments/scripts/m108_analysis.py --out ../experiments/results/m108/analysis.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import S15, S30, holm, paired, prio, seeds_of  # noqa: E402
import m66_verify  # noqa: E402
m66_verify.POOL_MODE = "off"   # this script pools by itself

E30_107, E15_107 = list(range(11000, 11030)), list(range(11000, 11015))
C30 = list(range(12000, 12030))                       # M108 seeds; evaluation streams 17000 to 17029
R = lambda r: r["reward"]
P = lambda r: 100 * prio(r)
ENV = "M63_BACKLOG_RESET=1 M64_AXIOM_V2=1"
SEL = "/home/kmanojp/oranslice_rig/experiments/results/m64/n3_fully_connected"

# cell: (stored cell, stored seeds, stored name of each arm if it differs), M107 cell and seeds, M108 cell
CELLS = {
    "A3": (("m65_n3_view", S30, {"rule_static": "heuristic"}), ("m107/A_n3", E30_107), "m108/A_n3"),
    "B3": (("m64/n3_fully_connected", S30, {}), ("m107/B_n3", E30_107), "m108/B_n3"),
    "A7ring": (("m65_scaling/n7_ring", S15, {}), ("m107/A_n7_ring", E15_107), "m108/A_n7_ring"),
}
# family: cell, baselines (each against AXIOM), per measure; Holm within each family and measure
FAMILIES = {
    "A3": ("A3", ("single_agent_dqn", "independent_dqn", "mappo_tuned", "axiom2_mlp", "rule_static")),
    "B3": ("B3", ("single_agent_dqn", "independent_dqn", "mappo_tuned", "axiom2_mlp",
                  "rule_static", "rule_accept_all", "rule_local", "rule_neighbour")),
    "A7ring": ("A7ring", ("single_agent_dqn",)),
}
# pre-registered targets: (family, baseline, measure, the pooled direction it must show on the M108 seeds alone)
TARGETS = {
    "T1 Env A 3 gNBs, AXIOM ahead of DQN-SA on reward": ("A3", "single_agent_dqn", "reward", "AXIOM ahead"),
    "T2 Env A 3 gNBs, AXIOM ahead of the MLP encoder on reward": ("A3", "axiom2_mlp", "reward", "AXIOM ahead"),
    "T3 Env A 3 gNBs, static rule ahead of AXIOM on reward": ("A3", "rule_static", "reward", "AXIOM behind"),
    "T4 Env B 3 gNBs, neighbour rule ahead of AXIOM on reward": ("B3", "rule_neighbour", "reward", "AXIOM behind"),
    "T5 Env B 3 gNBs, AXIOM ahead of the neighbour rule on compliance": ("B3", "rule_neighbour", "compliance", "AXIOM ahead"),
    "T6 Env A 7 gNBs ring, AXIOM ahead of DQN-SA on reward": ("A7ring", "single_agent_dqn", "reward", "AXIOM ahead"),
    "T7 Env A 7 gNBs ring, AXIOM ahead of DQN-SA on compliance": ("A7ring", "single_agent_dqn", "compliance", "AXIOM ahead"),
}


def ci(d):
    d = np.asarray(d, float)
    m = d[np.random.default_rng(0).integers(0, len(d), size=(10000, len(d)))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def rows(cell, arm, which):
    """which: m108 (confirmation sample) or all (stored + M107 + M108, for information)."""
    (sc, ss, rename), (mc, ms), cc = CELLS[cell]
    out = {("c", s): r for s, r in seeds_of(cc, arm, C30).items()}
    if which == "all":
        out.update({("s", s): r for s, r in seeds_of(sc, rename.get(arm, arm), ss).items()})
        out.update({("n", s): r for s, r in seeds_of(mc, arm, ms).items()})
    return out


def family(fam, which):
    cell, bases = FAMILIES[fam]
    A = rows(cell, "axiom2", which)
    t = {}
    for m, f in (("reward", R), ("compliance", P)):
        tm = {}
        for b in bases:
            B = rows(cell, b, which)
            x = paired(A, B, f)
            d = [f(A[k]) - f(B[k]) for k in sorted(set(A) & set(B))]
            x["ci"] = ci(d) if d else [0.0, 0.0]
            x["collapsed_axiom"] = int(sum(A[k]["collapsed"] for k in A))
            tm[b] = x
        h = holm({k: v["p"] for k, v in tm.items()})
        for b, v in tm.items():
            v["p_holm"] = h[b]
            v["verdict"] = ("AXIOM ahead" if v["diff"] > 0 else "AXIOM behind") if h[b] < 0.05 else "within chance"
        t[m] = tm
    return t


def jobs(path):
    lines = []

    def add(name, args, arms):
        for a in arms:
            if a.startswith("rule_"):
                env = ENV + (f" M107_RULE_SELECTION={SEL}/{a}_selection.json" if a in ("rule_local", "rule_neighbour") else "")
                lines.append(f"{name}_{a}|{env}|../experiments/scripts/m107_run.py --arm {a} {args} --seeds {' '.join(map(str, C30))} "
                             f"--out-dir ../experiments/results/m108/{name}")
            else:
                for s in C30:
                    lines.append(f"{name}_{a}_{s}|{ENV}|../experiments/scripts/m107_run.py --arm {a} {args} --seeds {s} "
                                 f"--out-dir ../experiments/results/m108/{name}")
    learned = ("axiom2", "axiom2_mlp", "independent_dqn", "single_agent_dqn", "mappo_tuned")   # longest first
    add("A_n7_ring", "--env A --n 7 --topology ring", ("axiom2", "single_agent_dqn"))
    add("A_n3", "--env A --n 3", learned + ("rule_static",))
    add("B_n3", "--n 3", learned + ("rule_static", "rule_accept_all", "rule_local", "rule_neighbour"))
    lines.sort(key=lambda l: (not l.split("|")[0].endswith(tuple(f"_{s}" for s in C30)) or "_rule_" in l.split("|")[0],
                              {"axiom2": 0, "axiom2_mlp": 1, "independent_dqn": 2}.get(l.split("--arm ")[1].split()[0], 3)))
    open(path, "w").write("\n".join(lines) + "\n")
    print(len(lines), "jobs ->", path)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out"); ap.add_argument("--jobs"); a = ap.parse_args()
    if a.jobs:
        return jobs(a.jobs)
    out = {"families": {f: {w: family(f, w) for w in ("m108", "all")} for f in FAMILIES}, "targets": {}}
    for name, (fam, b, m, want) in TARGETS.items():
        c = out["families"][fam]["m108"][m][b]
        p = out["families"][fam]["all"][m][b]
        status = "confirmed" if c["verdict"] == want else ("same direction, within chance" if
                 (c["diff"] > 0) == (want == "AXIOM ahead") else "opposite direction" + (", significant" if c["verdict"] != "within chance" else ""))
        out["targets"][name] = {"want": want, "m108": c, "all_pooled": p, "status": status}
        print(f"{name:66s} M108 {c['diff']:+8.3f} CI [{c['ci'][0]:+.3f}, {c['ci'][1]:+.3f}] Holm p {c['p_holm']:.4f} "
              f"(n={c['n']}) -> {status} | all pooled {p['diff']:+8.3f} Holm p {p['p_holm']:.4g} (n={p['n']})")
    for f in FAMILIES:
        for m in ("reward", "compliance"):
            for b, v in out["families"][f]["m108"][m].items():
                print(f"  {f:7s} {m:10s} vs {b:18s} M108 {v['diff']:+8.3f} Holm p {v['p_holm']:.4f} {v['verdict']}")
    json.dump(out, open(a.out, "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
