#!/usr/bin/env python3
"""M72 analysis against docs/PAPER5_M72_preregistration.md (A-D).

Usage: m72_analysis.py --out experiments/results/m72/analysis.json
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
from scipy.stats import wilcoxon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import S15, ROOT, holm, mean, paired, prio, seeds_of  # noqa: E402

C = []


def crit(label, ok, detail, kind=None):
    tag = kind or ("HOLDS" if ok else "FAILS")
    print(f"[{tag}] {label}: {detail}")
    C.append({"label": label, "holds": None if kind else bool(ok), "detail": detail})


def fmt(t):
    return f"diff {t['diff']:+.4f}, W/T/L {t['wins']}/{t['ties']}/{t['losses']}, p {t['p']:.3g}" + (f", p_holm {t['p_holm']:.3g}" if "p_holm" in t else "") + f" (n={t['n']})"


def pair_vals(a, b):
    d = np.array(a) - np.array(b)
    p = float(wilcoxon(d).pvalue) if np.any(d != 0) else 1.0
    return {"n": len(d), "diff": float(d.mean()), "wins": int((d > 0).sum()), "ties": int((d == 0).sum()), "losses": int((d < 0).sum()), "p": p}


def part_c(out):
    cells = {"A3": ("A_n3", list(range(9000, 9020))), "B3": ("B_n3", list(range(9000, 9020))),
             "A19": ("A_n19_ring", list(range(9000, 9010))), "B7": ("B_n7_ring", list(range(9000, 9010)))}
    tests, summ = {}, {}
    for k, (d, ss) in cells.items():
        ax, vd = seeds_of(f"m72/C_axiom2/{d}", "axiom2", ss), seeds_of(f"m72/C_vdn/{d}", "axiom2", ss)
        for m, f in (("reward", lambda r: r["reward"]), ("prio", prio)):
            tests[f"{k}/{m}"] = paired(vd, ax, f)          # positive = VDN better
        summ[k] = {"n": (len(ax), len(vd)), "axiom": mean(ax) if ax else None, "vdn": mean(vd) if vd else None,
                   "axiom_prio": 100 * mean(ax, prio) if ax else None, "vdn_prio": 100 * mean(vd, prio) if vd else None,
                   "axiom_collapsed": sum(r["collapsed"] for r in ax.values()), "vdn_collapsed": sum(r["collapsed"] for r in vd.values())}
    h = holm({k: v["p"] for k, v in tests.items()})
    for k in tests:
        tests[k]["p_holm"] = h[k]
    better = [k for k, t in tests.items() if t["diff"] > 0 and t["p_holm"] < 0.05]
    worse = [k for k, t in tests.items() if t["diff"] < 0 and t["p_holm"] < 0.05]
    verdict = "improved variant" if better and not worse else ("equivalent" if not better and not worse else "worse")
    out["C"] = {"tests": tests, "summary": summ, "verdict": verdict}
    crit("C VDN verdict (reported as stated in the plan)", None, f"{verdict}; better {better}, worse {worse}", "REPORT")
    for k, t in tests.items():
        print(f"   {k:12s} VDN minus AXIOM {fmt(t)}")
    for k, s in summ.items():
        print(f"   {k}: {s}")


def load_shift(n_dir):
    res = {}
    for f in glob.glob(f"{ROOT}/m72/B_shift/{n_dir}/*_eval_*.json"):
        sh = os.path.basename(f).split("_eval_")[0]
        for s, v in json.load(open(f))["results"].items():
            res.setdefault(sh, {})[int(s)] = v
    return res


def part_b(out):
    res = load_shift("n3")
    S = list(range(905, 930))
    stored = seeds_of("m64/n3_fully_connected", "axiom2", S), seeds_of("m64/n3_fully_connected", "rule_local", S)
    nom_ok = all(abs(res["nominal"][s]["axiom2"]["reward"] - stored[0][s]["reward"]) < 1e-9 and
                 abs(res["nominal"][s]["rule_local"]["reward"] - stored[1][s]["reward"]) < 1e-9 for s in S)
    crit("B nominal reproduces the stored results exactly", nom_ok, f"{len(res['nominal'])} seeds")
    tests = {}
    for sh in ("load_0.80", "load_1.05", "load_1.10", "load_1.15", "load_1.20", "coupling_0.30", "amplitude_0.50", "nominal"):
        r = res.get(sh, {})
        a = [r[s]["axiom2"]["reward"] for s in S if s in r]
        b = [r[s]["rule_local"]["reward"] for s in S if s in r]
        tests[sh] = pair_vals(a, b)
        tests[sh]["prio"] = pair_vals([r[s]["axiom2"]["prio"] for s in S if s in r], [r[s]["rule_local"]["prio"] for s in S if s in r])
        tests[sh]["means"] = {"axiom2": float(np.mean(a)), "rule_local": float(np.mean(b)),
                              "rule_static": float(np.mean([r[s]["rule_static"]["reward"] for s in S if s in r]))}
    prim = ("load_1.10", "load_1.15", "load_1.20")
    h = holm({k: tests[k]["p"] for k in prim})
    for k in prim:
        tests[k]["p_holm"] = h[k]
    ok = all(tests[k]["n"] == 25 and tests[k]["diff"] > 0 and h[k] < 0.05 for k in prim)
    crit("B primary: AXIOM beats the nominally tuned rule under load 1.10, 1.15, 1.20 at Holm p<0.05", ok,
         "; ".join(f"{k} {fmt(tests[k])}" for k in prim))
    for k in tests:
        if k not in prim:
            crit(f"B reported {k}", None, f"reward {fmt(tests[k])}; prio {fmt(tests[k]['prio'])}", "REPORT")
    ret = {}
    for sh in prim:
        f = f"{ROOT}/m72/B_shift/n3/{sh}_retune.json"
        if os.path.exists(f):
            j = json.load(open(f))
            rr = {int(s): v for s, v in j["results"].items()}
            t = pair_vals([res[sh][s]["axiom2"]["reward"] for s in S], [rr[s]["reward"] for s in S])
            ret[sh] = {"selected": j["selected"], "test": t, "retuned_mean": float(np.mean([rr[s]["reward"] for s in S]))}
            crit(f"B reported {sh}: AXIOM vs rule re-tuned on shifted streams", None, f"{fmt(t)}; selected {j['selected']}", "REPORT")
    r7 = load_shift("n7_ring")
    S7 = S15
    for sh in r7:
        t = pair_vals([r7[sh][s]["axiom2"]["reward"] for s in S7 if s in r7[sh]], [r7[sh][s]["rule_local"]["reward"] for s in S7 if s in r7[sh]])
        crit(f"B reported N=7 ring {sh}: AXIOM vs nominally tuned rule", None, fmt(t), "REPORT")
        tests[f"n7_{sh}"] = t
    out["B"] = {"tests": tests, "retuned": ret}


def part_a(out):
    d = {}
    for f in glob.glob(f"{ROOT}/m72/A_hindsight/hindsight_*.json"):
        d.update(json.load(open(f)))
    t = np.mean([v["tuned"]["reward"] for v in d.values()])
    b = np.mean([v["best_in_hindsight"]["reward"] for v in d.values()])
    emb = max(v["max_embb_any_rule"] for v in d.values())
    emb_mean = float(np.mean([v["max_embb_any_rule"] for v in d.values()]))
    out["A"] = {"n": len(d), "tuned": float(t), "hindsight_best": float(b), "headroom_pct": float(100 * (b - t) / t),
                "max_embb_any_seed": emb, "mean_of_per_seed_max_embb": emb_mean,
                "tuned_is_best_count": sum(v["best_in_hindsight"]["rule"] == {"tau_c": 0.0, "tau_q": None, "tau_e": 0.2} for v in d.values())}
    crit("A hindsight-best within 1% of the tuned rule", len(d) == 15 and (b - t) / t <= 0.01, f"tuned {t:.3f}, hindsight {b:.3f}, headroom {100 * (b - t) / t:.2f}% on {len(d)} seeds")
    crit("A no rule keeps mean eMBB above 37%", emb_mean <= 0.37, f"mean of per-seed max eMBB {emb_mean:.3f}, single-seed max {emb:.3f}")


def part_d(out):
    res = {}
    for k, cell, ss in (("B3", "B_n3", list(range(900, 920))), ("B7", "B_n7_ring", list(range(900, 912)))):
        stored_cell = "m64/n3_fully_connected" if k == "B3" else "m64/n7_ring"
        lg, sh, rl = seeds_of(f"m72/D_long/{cell}", "axiom2", ss), seeds_of(stored_cell, "axiom2", ss), seeds_of(stored_cell, "rule_local", ss)
        t1, t2 = paired(lg, sh), paired(lg, rl)
        res[k] = {"long": mean(lg) if lg else None, "short": mean(sh), "rule": mean(rl), "long_vs_short": t1, "long_vs_rule": t2,
                  "long_prio": 100 * mean(lg, prio) if lg else None}
        crit(f"D {k}: AXIOM 900 episodes vs 300 episodes and vs tuned rule", None, f"long {res[k]['long']}, short {res[k]['short']:.3f}, rule {res[k]['rule']:.3f}; vs short {fmt(t1)}; vs rule {fmt(t2)}", "REPORT")
    out["D"] = res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = {}
    for f in (part_c, part_b, part_a, part_d):
        f(out)
    judged = [c for c in C if c["holds"] is not None]
    n_fail = sum(not c["holds"] for c in judged)
    print(f"== {len(judged) - n_fail}/{len(judged)} hold, {len(C) - len(judged)} reported only")
    out["criteria"], out["n_judged"], out["n_fail"] = C, len(judged), n_fail
    json.dump(out, open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
