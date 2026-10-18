#!/usr/bin/env python3
"""M66c analysis against addendum 2 of docs/PAPER5_M66_verification_plan.md (C1-C9).

Uses the independent reader in m66_verify.py throughout. Every criterion is
reported as HOLDS or FAILS, and the per-cell numbers behind it are saved.

Usage: m66c_analysis.py --out experiments/results/m66c_analysis.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import ROOT, find_eval, holm, mean, paired, prio, read, seeds_of  # noqa: E402

F10, F20 = list(range(3000, 3010)), list(range(4000, 4020))
S30, REP = list(range(900, 930)), list(range(1000, 1010))
S30_19 = list(range(900, 927)) + [1000, 1001, 1002]
BASE = ("independent_dqn", "single_agent_dqn", "mappo_tuned")
O = "m66c_fresh"


def crit(C, label, ok, detail):
    print(f"[{'HOLDS' if ok else 'FAILS'}] {label}: {detail}")
    C.append({"label": label, "holds": bool(ok), "detail": detail})


def report(C, label, detail):
    print(f"[REPORT] {label}: {detail}")
    C.append({"label": label, "holds": None, "detail": detail})


def summ(rows):
    return {"n": len(rows), "reward": mean(rows), "prio": mean(rows, prio),
            "urllc": mean(rows, lambda r: r["sla"]["urllc"]), "embb": mean(rows, lambda r: r["sla"]["embb"]),
            "collapsed": int(sum(r["collapsed"] for r in rows.values()))}


def scaling(C, out, cid, cell, seeds, hi_base):
    d = {a: seeds_of(f"{O}/{cell}", a, seeds) for a in ("axiom2",) + BASE}
    s = {a: summ(v) for a, v in d.items()}
    t = {(a, m): paired(d["axiom2"], d[a], f) for a in BASE for m, f in (("reward", lambda r: r["reward"]), ("prio", prio))}
    h = holm({k: v["p"] for k, v in t.items()})
    out[cid] = {"summary": s, "tests": {"/".join(k): {**v, "p_holm": h[k]} for k, v in t.items()}}
    crit(C, f"{cid} AXIOM priority SLA >= 90%", s["axiom2"]["prio"] >= 0.90,
         f"{100 * s['axiom2']['prio']:.1f}% on {s['axiom2']['n']} seeds, collapsed {s['axiom2']['collapsed']}")
    for a in BASE:
        crit(C, f"{cid} {a} priority SLA <= {100 * hi_base:.0f}%", s[a]["prio"] <= hi_base,
             f"{100 * s[a]['prio']:.1f}% on {s[a]['n']} seeds, collapsed {s[a]['collapsed']}")
    worst = max(h.values())
    crit(C, f"{cid} AXIOM beats every baseline on reward and priority SLA, all 6 at Holm p<0.05",
         all(t[k]["diff"] > 0 and h[k] < 0.05 for k in t), f"max p_holm {worst:.3g}, min diff {min(v['diff'] for v in t.values()):+.4f}")
    for a in ("axiom2",) + BASE:
        print(f"   {a:18s} n={s[a]['n']} reward {s[a]['reward']:.3f} prio {100 * s[a]['prio']:.1f}% collapsed {s[a]['collapsed']}")


def envb_n7(C, out):
    learned = ("axiom2", "axiom2_mlp") + BASE
    for t in ("fully_connected", "hex"):
        d = {a: seeds_of(f"{O}/C4_B_n7_{t}", a, F10) for a in learned + ("rule_static", "rule_local")}
        s = {a: summ(v) for a, v in d.items()}
        out[f"C4 {t}"] = {"summary": s}
        for a in learned:
            pt = paired(d["rule_local"], d[a])
            crit(C, f"C4 Env B N=7 {t} rule_local mean reward above {a}", s["rule_local"]["reward"] > s[a]["reward"],
                 f"{s['rule_local']['reward']:.3f} vs {s[a]['reward']:.3f}, p {pt['p']:.2g}")
        for m, f in (("reward", lambda r: r["reward"]), ("prio", prio)):
            pt = paired(d["axiom2"], d["axiom2_mlp"], f)
            out[f"C4 {t}"][f"axiom_vs_mlp_{m}"] = pt
            crit(C, f"C4 Env B N=7 {t} no significant AXIOM advantage over MLP on {m}", not (pt["diff"] > 0 and pt["p"] < 0.05),
                 f"diff {pt['diff']:+.4f}, p {pt['p']:.2g}, W/T/L {pt['wins']}/{pt['ties']}/{pt['losses']}")
        pt = paired(d["axiom2"], d["rule_static"])
        out[f"C4 {t}"]["axiom_vs_static"] = pt
        crit(C, f"C4 Env B N=7 {t} AXIOM not significantly above static rule", not (pt["diff"] > 0 and pt["p"] < 0.05),
             f"diff {pt['diff']:+.3f}, p {pt['p']:.2g}")


def disruption(C, out):
    """Mirror the paper's families: cost tests Holm over every dropout and churn cell; gap tests
    (AXIOM disrupted level minus baseline disrupted level) Holm over every non-AXIOM cell."""
    base_cell = {"gat_ctde": ("m66_fresh/A_n3", "axiom2"), "independent_dqn": ("m66_fresh/A_n3", "independent_dqn"),
                 "single_agent_dqn": ("m66_fresh/A_n3", "single_agent_dqn"), "fl_gat_ctde_sigma0.0": ("m66c_views/m3", "fl_gat_ctde_sigma0.0")}
    base = {arm: {s: r["norm"] for s, r in seeds_of(c, a, F10).items()} for arm, (c, a) in base_cell.items()}
    rows, pc = {}, {}
    for arm in base_cell:
        for kind in ("dropout", "spike", "churn"):
            if arm == "single_agent_dqn" and kind == "churn":
                continue
            for sev in (1, 2, 3):
                lvl, prec = {}, []
                for s in F10:
                    p = None
                    for sub in ("omega_log.jsonl", "omega_log.jsonl.gz"):
                        q = f"{ROOT}/{O}/C5_m4/{arm}/{kind}_sev{sev}/seed{s}/eval/{sub}"
                        if os.path.exists(q):
                            p = q
                    if p is None:
                        continue
                    r = read(p)
                    lvl[s] = r["norm"]
                    if r["precision"] is not None:
                        prec.append(r["precision"])
                cost = np.array([base[arm][s] - lvl[s] for s in sorted(lvl) if s in base[arm]])
                from scipy.stats import wilcoxon
                pv = float(wilcoxon(cost).pvalue) if len(cost) and np.any(cost != 0) else 1.0
                key = f"{arm}|{kind}|{sev}"
                rows[key] = {"n": len(cost), "cost": float(cost.mean()) if len(cost) else None, "hurt": int((cost > 0).sum()),
                             "p": pv, "level": lvl, "precision": float(np.mean(prec)) if prec else None}
                if kind != "spike":
                    pc[key] = pv
    hc = holm(pc)
    for k in pc:
        rows[k]["p_holm"] = hc[k]
    complete = all(r["n"] == 10 for r in rows.values()) and len(rows) == 33
    crit(C, "C5 every dropout and churn cell lowers every arm's normalised reward, Holm p<0.05",
         complete and all(rows[k]["cost"] > 0 and hc[k] < 0.05 for k in pc),
         f"{len(pc)} cells, complete={complete}, max p_holm {max(hc.values()):.3g}, min hurt {min(rows[k]['hurt'] for k in pc)}/10")
    gaps, gp = {}, {}
    from scipy.stats import wilcoxon
    for k, r in rows.items():
        arm, kind, sev = k.split("|")
        ref = rows.get(f"gat_ctde|{kind}|{sev}")
        if arm == "gat_ctde" or ref is None:
            continue
        common = sorted(set(ref["level"]) & set(r["level"]))
        d = np.array([ref["level"][s] - r["level"][s] for s in common])
        gaps[k] = {"n": len(d), "gap": float(d.mean()), "wins": int((d > 0).sum())}
        gp[k] = float(wilcoxon(d).pvalue) if np.any(d != 0) else 1.0
    hg = holm(gp)
    for k in gaps:
        gaps[k]["p"], gaps[k]["p_holm"] = gp[k], hg[k]
    sig = [k for k in gaps if hg[k] < 0.05]
    crit(C, "C5 no gap between AXIOM and any baseline survives Holm", not sig,
         f"{len(gaps)} gaps, min p_holm {min(hg.values()):.3g}, significant: {[(k, round(gaps[k]['gap'], 3)) for k in sig]}")
    sp = [rows[f"gat_ctde|spike|{v}"]["precision"] for v in (1, 2, 3)]
    crit(C, "C5 AXIOM spike block precision >= 0.95", all(x is not None and x >= 0.95 for x in sp), f"{sp}")
    out["C5"] = {"cells": {k: {kk: vv for kk, vv in r.items() if kk != "level"} for k, r in rows.items()}, "gaps": gaps,
                 "baseline": {a: float(np.mean(list(v.values()))) for a, v in base.items()}}


def dp(C, out):
    cen = seeds_of("m66_fresh/A_n3", "axiom2", F10)
    t, steps = {}, {}
    for sg in ("0.5", "1.0", "2.0", "4.0"):
        rows = {}
        for b in range(3000, 3010, 2):
            rows.update(seeds_of(f"{O}/C6_s{sg}_{b}", f"fl_gat_ctde_sigma{sg}", [b, b + 1]))
            f = f"{ROOT}/{O}/C6_s{sg}_{b}/fl_gat_ctde_sigma{sg}_results.json"
            if os.path.exists(f):
                for s, v in json.load(open(f)).items():
                    steps[(sg, s)] = v.get("dp_step_count_per_client")
        t[sg] = paired(cen, rows)
        t[sg]["federated"] = mean(rows) if rows else None
        t[sg]["collapsed"] = int(sum(r["collapsed"] for r in rows.values()))
    h = holm({k: v["p"] for k, v in t.items()})
    for k in t:
        t[k]["p_holm"] = h[k]
    out["C6"] = {"centralised": mean(cen), "tests": t, "steps": {f"{k[0]}/{k[1]}": v for k, v in steps.items()}}
    crit(C, "C6 DP mean reward below centralised at every sigma", all(v["n"] == 10 and v["diff"] > 0 for v in t.values()),
         {k: f"{v['diff']:+.3f}" for k, v in t.items()})
    crit(C, "C6 no DP drop survives Holm", all(v["p_holm"] >= 0.05 for v in t.values()), {k: round(v["p_holm"], 3) for k, v in t.items()})
    flat = [x for v in steps.values() if v for x in v]
    crit(C, "C6 every client takes 17,969 noisy steps", len(steps) == 40 and flat and all(x == 17969 for x in flat),
         f"{len(steps)} seed records, distinct counts {sorted(set(flat))}")


def seeded_single(C, out):
    res = {}
    fam = {"A3": ("m65_n3_view", "C7_A_n3", S30), "A3rep": ("m65_rep_view", "C7_A_n3_rep", REP),
           "B3": ("m64/n3_fully_connected", "C7_B_n3", S30), "B3rep": ("m64/n3_replication", "C7_B_n3_rep", REP)}
    for k, (cell, seeded, ss) in fam.items():
        ax = seeds_of(cell, "axiom2", ss)
        sg = seeds_of(f"{O}/{seeded}", "single_agent_dqn", ss)
        others = {a: seeds_of(cell, a, ss) for a in ("independent_dqn", "mappo_tuned")}
        t = {"single_seeded": paired(ax, sg), **{a: paired(ax, v) for a, v in others.items()}}
        h = holm({a: v["p"] for a, v in t.items()})
        t = {a: {**v, "p_holm": h[a]} for a, v in t.items()}
        stored = paired(ax, seeds_of(cell, "single_agent_dqn", ss))
        res[k] = {"tests": t, "stored_single_diff": stored["diff"], "seeded_single_reward": mean(sg) if sg else None,
                  "seeded_collapsed": int(sum(r["collapsed"] for r in sg.values()))}
        s_ = t["single_seeded"]
        line = (f"n={s_['n']} AXIOM minus seeded single {s_['diff']:+.3f} (stored {stored['diff']:+.3f}), "
                f"p_holm {s_['p_holm']:.3g}, W/T/L {s_['wins']}/{s_['ties']}/{s_['losses']}, collapsed {res[k]['seeded_collapsed']}")
        if k == "B3":
            crit(C, "C7 Env B N=3 AXIOM beats properly seeded single-agent DQN at Holm p<0.05", s_["n"] == 30 and s_["diff"] > 0 and s_["p_holm"] < 0.05, line)
        else:
            report(C, f"C7 {k} properly seeded single-agent DQN", line)
    ax = seeds_of("m65_scaling/n19_ring", "axiom2", S30_19)
    sg = seeds_of(f"{O}/C7_A_n19_ring", "single_agent_dqn", S30_19)
    t = paired(ax, sg, prio)
    res["A19"] = {"prio_test": t, "seeded_prio": mean(sg, prio) if sg else None,
                  "seeded_collapsed": int(sum(r["collapsed"] for r in sg.values()))}
    crit(C, "C7 Env A N=19 ring AXIOM beats properly seeded single-agent DQN on priority SLA, p<0.05",
         t["n"] == 30 and t["diff"] > 0 and t["p"] < 0.05,
         f"n={t['n']} diff {t['diff']:+.3f}, p {t['p']:.3g}; seeded single prio {100 * (res['A19']['seeded_prio'] or 0):.1f}%, "
         f"collapsed {res['A19']['seeded_collapsed']}/{len(sg)}")
    out["C7"] = res


def sensitivity(C, out):
    res = {}
    for c in ("load102", "load107", "weights"):
        d = {a: seeds_of(f"{O}/C8_{c}", a, F10) for a in ("axiom2", "rule_static", "independent_dqn", "single_agent_dqn")}
        s = {a: summ(v) for a, v in d.items()}
        go = paired(d["axiom2"], d["rule_static"])
        res[c] = {"summary": s, "vs_oracle": go, "vs_indep": paired(d["axiom2"], d["independent_dqn"]),
                  "vs_single": paired(d["axiom2"], d["single_agent_dqn"])}
        frac = s["axiom2"]["reward"] / s["rule_static"]["reward"]
        crit(C, f"C8 {c} AXIOM within 2% of oracle and not significantly different", frac >= 0.98 and go["p"] >= 0.05,
             f"{s['axiom2']['reward']:.3f} vs {s['rule_static']['reward']:.3f} = {100 * frac:.1f}%, p {go['p']:.3g}")
        crit(C, f"C8 {c} AXIOM mean reward above both DQN baselines",
             s["axiom2"]["reward"] > s["independent_dqn"]["reward"] and s["axiom2"]["reward"] > s["single_agent_dqn"]["reward"],
             f"AXIOM {s['axiom2']['reward']:.3f}, indep {s['independent_dqn']['reward']:.3f}, single {s['single_agent_dqn']['reward']:.3f}")
    out["C8"] = res


def envb_sensitivity(C, out):
    ref = seeds_of("m66_fresh/B_n3", "axiom2", F10)
    res = {a: paired(ref, seeds_of(f"{O}/C9_B_n3", a, F10)) for a in ("axiom", "axiom2_lr3e-4", "axiom2_lr3e-3", "axiom2_wide")}
    out["C9"] = res
    t = res["axiom"]
    crit(C, "C9 original AXIOM below AXIOM v2 in >=9 of 10 seeds, p<0.05", t["n"] == 10 and t["wins"] >= 9 and t["p"] < 0.05,
         f"v2 minus original {t['diff']:+.3f}, wins {t['wins']}/10, p {t['p']:.3g}")
    for a in ("axiom2_lr3e-3", "axiom2_wide"):
        crit(C, f"C9 {a} not significantly different from AXIOM v2", res[a]["n"] == 10 and res[a]["p"] >= 0.05,
             f"v2 minus {a} {res[a]['diff']:+.3f}, p {res[a]['p']:.3g}")
    report(C, "C9 axiom2_lr3e-4", f"v2 minus lr3e-4 {res['axiom2_lr3e-4']['diff']:+.3f}, p {res['axiom2_lr3e-4']['p']:.3g}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*", default=None, help="subset of C1..C9 to run")
    a = ap.parse_args()
    C, out = [], {}
    run = lambda c: a.only is None or c in a.only
    if run("C1"):
        scaling(C, out, "C1 Env A N=7 hex", "C1_A_n7_hex", F10, 0.80)
    if run("C2"):
        scaling(C, out, "C2 Env A N=19 fully-connected", "C2_A_n19_fc", F10, 0.75)
    if run("C3"):
        scaling(C, out, "C3 Env A N=7 fully-connected 20 seeds", "C3_A_n7_fc", F20, 0.80)
    if run("C4"):
        envb_n7(C, out)
    if run("C5"):
        disruption(C, out)
    if run("C6"):
        dp(C, out)
    if run("C7"):
        seeded_single(C, out)
    if run("C8"):
        sensitivity(C, out)
    if run("C9"):
        envb_sensitivity(C, out)
    judged = [c for c in C if c["holds"] is not None]
    n_fail = sum(not c["holds"] for c in judged)
    print(f"== {len(judged) - n_fail}/{len(judged)} hold, {len(C) - len(judged)} reported only")
    out["criteria"], out["n_judged"], out["n_fail"] = C, len(judged), n_fail
    json.dump(out, open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
