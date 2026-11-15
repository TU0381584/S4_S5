#!/usr/bin/env python3
"""M109 analysis (docs/PAPER5_M109_preregistration.md), committed with it before any M109 run.

  m109_analysis.py --jobs <path>      write the job list and exit
  m109_analysis.py --out <json>       judge every pre-registered family from the evaluation logs
Run from framework/. Tests are two-sided Wilcoxon signed-rank tests on paired seeds (ties within 1e-9 dropped), with
95% bootstrap CIs of the mean paired difference, the Hodges-Lehmann estimate and the matched-pairs rank-biserial
correlation, Holm-corrected within each family. Priority-slice compliance is the mean of URLLC and eMBB compliance.
"""
import argparse, glob, gzip, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m66_verify as V
from m66_verify import find_eval, read, paired, holm, prio, hodges_lehmann, rank_biserial

R = "m109"
F10 = list(range(13000, 13010))          # fresh seeds; evaluation streams 18000 to 18009
F5 = F10[:5]                             # budget study
ENV = "M63_BACKLOG_RESET=1 M64_AXIOM_V2=1"
SIZES = (7, 19, 37)


def rows(cell, arm, seeds, sub="eval"):
    out = {}
    for s in seeds:
        if sub == "eval":
            p = find_eval(f"{R}/{cell}", arm, s)
        else:
            base = os.path.join(V.ROOT, R, cell, arm, f"seed{s}", sub)
            p = next((q for q in (f"{base}/omega_log.jsonl", f"{base}/dqn/offline_eval/rep_0/omega_log.jsonl") if os.path.exists(q) or os.path.exists(q + ".gz")), None)
        if p:
            out[s] = read(p)
    return out


def ci(d):
    d = np.asarray(d, float)
    m = d[np.random.default_rng(0).integers(0, len(d), size=(10000, len(d)))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def test(a, b, f):
    x = paired(a, b, f)
    k = sorted(set(a) & set(b))
    x["ci"] = ci([f(a[s]) - f(b[s]) for s in k]) if k else [0.0, 0.0]
    x["hl"], x["rb"] = (hodges_lehmann(a, b, f), rank_biserial(a, b, f)) if k else (0.0, 0.0)
    return x


def summary(r):
    if not r:
        return {"n": 0}
    return {"n": len(r), "priority_sla": 100 * float(np.mean([prio(x) for x in r.values()])), "reward": float(np.mean([x["reward"] for x in r.values()])),
            "collapsed": int(sum(x["collapsed"] for x in r.values())), "priority_sla_ci": [100 * c for c in ci([prio(x) for x in r.values()])]}


def fam(tests):
    """tests: {label: (axiom rows, other rows, measure)}; returns per-test results with Holm p within the family."""
    t = {k: test(a, b, (prio if m == "sla" else (lambda r: r["reward"]))) for k, (a, b, m) in tests.items()}
    h = holm({k: v["p"] for k, v in t.items()})
    for k in t:
        t[k]["p_holm"] = h[k]
        t[k]["verdict"] = ("AXIOM ahead" if t[k]["diff"] > 0 else "AXIOM behind") if h[k] < 0.05 else "within chance"
    return t


def jobs(path):
    L = []

    def add(name, variant, arm, args, seeds, out, extra=""):
        for s in seeds:
            L.append(f"{name}_{s}|{ENV}|../experiments/scripts/m109_run.py --variant {variant} {extra}--arm {arm} {args} --seeds {s} --out-dir ../experiments/results/m109/{out}")
    for b, eps in (("independent_dqn", 1500), ("axiom2", 1500), ("single_agent_dqn", 1500)):      # longest first
        add(f"budget_{b}", "none", b, "--env A --n 19 --topology hex --train-episodes 1500", F5, "budget/A_n19_hex", "--budget 300,900 ")
    for eps in (1500, 900, 300):
        add(f"budget_mappo{eps}", "none", "mappo_tuned", f"--env A --n 19 --topology hex --train-episodes {eps}", F5, f"budget/A_n19_hex_mappo{eps}")
    for n in (37, 19, 7):
        a = f"--env A --n {n} --topology hex"
        add(f"parity_A{n}_independent_dqn", "parity", "independent_dqn", a, F10, f"parity/A_n{n}_hex")
        add(f"A{n}_axiom2", "none", "axiom2", a, F10, f"A_n{n}_hex")
        add(f"sharedhead_A{n}", "sharedhead", "axiom2", a, F10, f"sharedhead/A_n{n}_hex")
        add(f"A{n}_axiom2_mlp", "none", "axiom2_mlp", a, F10, f"A_n{n}_hex")
        add(f"paramshared_A{n}", "paramshared", "axiom2", a, F10, f"paramshared/A_n{n}_hex")
        add(f"parity_A{n}_single_agent_dqn", "parity", "single_agent_dqn", a, F10, f"parity/A_n{n}_hex")
    add("qmix_A19", "qmix", "axiom2", "--env A --n 19 --topology hex", F10, "qmix/A_n19_hex")
    add("B3_axiom2", "none", "axiom2", "--n 3", F10, "B_n3")
    add("paramshared_B3", "paramshared", "axiom2", "--n 3", F10, "paramshared/B_n3")
    open(path, "w").write("\n".join(L) + "\n")
    print(len(L), "jobs ->", path)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out"); ap.add_argument("--jobs"); a = ap.parse_args()
    if a.jobs:
        return jobs(a.jobs)
    out = {"summary": {}, "families": {}, "stop_rule": {}, "budget": {}, "qmix": {}}
    AX = {n: rows(f"A_n{n}_hex", "axiom2", F10) for n in SIZES}
    arms = {"parity DQN-SA": lambda n: rows(f"parity/A_n{n}_hex", "single_agent_dqn", F10), "parity DQN-I": lambda n: rows(f"parity/A_n{n}_hex", "independent_dqn", F10),
            "parameter-shared": lambda n: rows(f"paramshared/A_n{n}_hex", "axiom2", F10), "MLP encoder": lambda n: rows(f"A_n{n}_hex", "axiom2_mlp", F10),
            "shared head": lambda n: rows(f"sharedhead/A_n{n}_hex", "axiom2", F10)}
    D = {name: {n: f(n) for n in SIZES} for name, f in arms.items()}
    for n in SIZES:
        out["summary"][f"A{n} AXIOM"] = summary(AX[n])
        for name in D:
            out["summary"][f"A{n} {name}"] = summary(D[name][n])
    AXB, PSB = rows("B_n3", "axiom2", F10), rows("paramshared/B_n3", "axiom2", F10)
    out["summary"]["B3 AXIOM"], out["summary"]["B3 parameter-shared"] = summary(AXB), summary(PSB)
    QM = rows("qmix/A_n19_hex", "axiom2", F10); out["summary"]["A19 QMIX"] = summary(QM)
    # P1 parity (12 tests), P2 parameter-shared (8), P3 MLP encoder and shared head (12), P5 QMIX (2)
    out["families"]["P1 parity"] = fam({f"A{n} {b} {m}": (AX[n], D[b][n], m) for n in SIZES for b in ("parity DQN-SA", "parity DQN-I") for m in ("sla", "reward")})
    p2 = {f"A{n} parameter-shared {m}": (AX[n], D["parameter-shared"][n], m) for n in SIZES for m in ("sla", "reward")}
    p2.update({f"B3 parameter-shared {m}": (AXB, PSB, m) for m in ("sla", "reward")})
    out["families"]["P2 parameter-shared"] = fam(p2)
    out["families"]["P3 ablations"] = fam({f"A{n} {b} {m}": (AX[n], D[b][n], m) for n in SIZES for b in ("MLP encoder", "shared head") for m in ("sla", "reward")})
    out["families"]["P5 QMIX"] = fam({f"A19 QMIX {m}": (AX[19], QM, m) for m in ("sla", "reward")})
    # stop rule (a): a parity or parameter-shared baseline within 5 points of AXIOM's priority-slice compliance at 19 or 37 gNBs
    for n in (19, 37):
        for b in ("parity DQN-SA", "parity DQN-I", "parameter-shared"):
            gap = out["summary"][f"A{n} AXIOM"].get("priority_sla", float("nan")) - out["summary"][f"A{n} {b}"].get("priority_sla", float("nan"))
            out["stop_rule"][f"A{n} {b}"] = {"gap_points": gap, "within_5_points": bool(gap < 5.0)}
    out["stop_rule"]["triggered"] = any(v["within_5_points"] for v in out["stop_rule"].values() if isinstance(v, dict))
    # P4 budget, 5 seeds, descriptive (a five-pair signed-rank test cannot reach p < 0.05)
    for arm in ("axiom2", "single_agent_dqn", "independent_dqn"):
        out["budget"][arm] = {"300": summary(rows("budget/A_n19_hex", arm, F5, "eval300")), "900": summary(rows("budget/A_n19_hex", arm, F5, "eval900")),
                              "1500": summary(rows("budget/A_n19_hex", arm, F5))}
    out["budget"]["mappo_tuned"] = {str(e): summary(rows(f"budget/A_n19_hex_mappo{e}", "mappo_tuned", F5)) for e in (300, 900, 1500)}
    # QMIX stability: no non-finite loss, and the mean loss of the last 20 episodes at most twice the lowest 20-episode mean
    st = {}
    for s in F10:
        p = os.path.join(V.ROOT, R, "qmix/A_n19_hex/axiom2", f"seed{s}", "train", "checkpoint.pt.loss.json")
        if os.path.exists(p):
            c = [x for x in json.load(open(p))["episode_mean_loss"] if x is not None]
            roll = np.convolve(c, np.ones(20) / 20, mode="valid")
            st[s] = {"finite": bool(np.all(np.isfinite(c))), "last20": float(roll[-1]), "best20": float(roll.min()), "stable": bool(np.all(np.isfinite(c)) and roll[-1] <= 2 * roll.min())}
    out["qmix"] = {"per_seed": st, "stable_seeds": int(sum(v["stable"] for v in st.values())), "n": len(st)}
    for k, v in out["summary"].items():
        if v["n"]:
            print(f"{k:28s} n={v['n']:2d} priority SLA {v['priority_sla']:5.1f}% reward {v['reward']:8.3f} collapsed {v['collapsed']}")
    for f_, t in out["families"].items():
        for k, v in t.items():
            print(f"  {f_:20s} {k:34s} diff {v['diff']:+8.3f} HL {v['hl']:+8.3f} r {v['rb']:+.2f} Holm p {v['p_holm']:.4f} (n={v['n']}) {v['verdict']}")
    print("stop rule (a):", {k: v for k, v in out["stop_rule"].items()})
    print("budget:", json.dumps(out["budget"], default=float)[:1500])
    print("qmix stable seeds:", out["qmix"]["stable_seeds"], "of", out["qmix"]["n"])
    json.dump(out, open(a.out, "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
