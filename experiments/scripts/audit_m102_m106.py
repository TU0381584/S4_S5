#!/usr/bin/env python3
"""Independent audit of M102-M106 (written 2026-11-12, after all five campaigns finished).

Does not import m66_verify or any campaign analysis script. It has its own log reader, statistics (a sign-flip
permutation test besides scipy's Wilcoxon, its own Holm and bootstrap), provenance checks and seed checks, and it
compares every test in each campaign's analysis.json field by field.
Run from the repo root: venv/bin/python experiments/scripts/audit_m102_m106.py --out experiments/results/audit_m102_m106.json
"""
import argparse
import glob
import gzip
import itertools
import json
import os
import re
import subprocess

import numpy as np
from scipy.stats import wilcoxon

REPO = "/home/kmanojp/oranslice_rig"
RES = f"{REPO}/experiments/results"
LOGS = f"{REPO}/experiments/logs"
SUBS = ("omega_log.jsonl", "dqn/offline_eval/rep_0/omega_log.jsonl")
FAIL = []


def check(ok, msg):
    if not ok:
        FAIL.append(msg)
    return ok


# ------------------------------------------------------------------ reading (own implementation)
def opener(p):
    return gzip.open(p, "rt") if p.endswith(".gz") else open(p)


def locate(d):
    for s in SUBS:
        for p in (f"{d}/{s}", f"{d}/{s}.gz"):
            if os.path.exists(p):
                return p
    return None


def load(path):
    steps, blocks, comp = {}, 0, {"urllc": [], "embb": []}
    with opener(path) as fh:
        for line in fh:
            r = json.loads(line)
            e = r.get("evidence")
            if not isinstance(e, dict):
                continue
            if e.get("rollup"):
                blocks += sum((e.get("episode_block_by_slice") or {}).values())
                for k in comp:
                    v = (e.get("episode_sla_compliance_by_slice") or {}).get(k)
                    if v is not None:
                        comp[k].append(v)
            elif "reward" in e:
                steps.setdefault(r["episode"], []).append(e["reward"])
    return {"reward": float(np.mean([np.mean(v) for v in steps.values()])),
            "compliance": 50.0 * (np.mean(comp["urllc"]) + np.mean(comp["embb"])),
            "collapsed": blocks == 0, "blocks": blocks, "episodes": len(steps),
            "rollups": len(comp["urllc"])}


CACHE = {}


def run(d, which="eval"):
    key = (d, which)
    if key not in CACHE:
        p = locate(f"{d}/{which}")
        CACHE[key] = load(p) if p else None
    return CACHE[key]


# ------------------------------------------------------------------ statistics (own implementation)
def signflip_p(d, rng):
    d = np.asarray(d, float)
    obs = abs(d.mean())
    if not np.any(d):
        return 1.0
    n = len(d)
    if n <= 20:
        signs = np.array(list(itertools.product((1, -1), repeat=n)), dtype=np.int8)
    else:
        signs = rng.choice((1, -1), size=(200000, n)).astype(np.int8)
    m = np.abs(signs @ d) / n
    return float(np.mean(m >= obs - 1e-12))


def holm(p):
    ks = sorted(p, key=p.get)
    out, run_ = {}, 0.0
    for i, k in enumerate(ks):
        run_ = max(run_, min(1.0, (len(ks) - i) * p[k]))
        out[k] = run_
    return out


def boot(d):
    d = np.asarray(d, float)
    m = d[np.random.default_rng(0).integers(0, len(d), size=(10000, len(d)))].mean(axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def pair(A, B, meas):
    ks = sorted(set(A) & set(B))
    d = np.array([A[k][meas] - B[k][meas] for k in ks])
    p = float(wilcoxon(d, zero_method="wilcox").pvalue) if np.any(d) else 1.0
    return {"n": len(d), "diff": float(d.mean()), "wins": int((d > 0).sum()), "ties": int((d == 0).sum()),
            "losses": int((d < 0).sum()), "p": p, "ci": boot(d), "median": float(np.median(d)), "d": d}


def family(tests, tag, labels=("ahead", "behind")):
    h = holm({k: v["p"] for k, v in tests.items()})
    rng = np.random.default_rng(1)
    hp = holm({k: signflip_p(v["d"], rng) for k, v in tests.items()})
    for k, v in tests.items():
        v["p_holm"] = h[k]
        v["verdict"] = (labels[0] if v["diff"] > 0 else labels[1]) if h[k] < 0.05 else "within chance"
        v["perm_holm"] = hp[k]
        v["perm_verdict"] = (labels[0] if v["diff"] > 0 else labels[1]) if hp[k] < 0.05 else "within chance"
    return tests


def compare(mine, theirs, name, vmap):
    """Field-by-field match of one recomputed test against the campaign's analysis.json."""
    for f in ("n", "wins", "ties", "losses"):
        check(mine[f] == theirs[f], f"{name}: {f} {mine[f]} != {theirs[f]}")
    for f in ("diff", "p", "p_holm", "median"):
        if f in theirs:
            check(abs(mine[f] - theirs[f]) <= 1e-9 * max(1, abs(theirs[f])), f"{name}: {f} {mine[f]} != {theirs[f]}")
    check(all(abs(a - b) < 1e-9 for a, b in zip(mine["ci"], theirs["ci"])), f"{name}: ci differs")
    check(vmap[mine["verdict"]] == theirs["verdict"], f"{name}: verdict {mine['verdict']} vs {theirs['verdict']}")


# ------------------------------------------------------------------ provenance
def phase_jobs(m):
    jobs = []
    for line in open(f"{LOGS}/{m}/phase1.txt"):
        name, env, cmd = line.rstrip("\n").split("|")
        a = cmd.split()
        g = lambda flag, dflt=None: a[a.index(flag) + 1] if flag in a else dflt
        jobs.append({"name": name, "env": dict(x.split("=") for x in env.split()), "arm": g("--arm"), "envAB": g("--env", "B"),
                     "n": int(g("--n", 3)), "topology": g("--topology", "fully_connected"), "seed": int(g("--seeds")),
                     "out": os.path.normpath(os.path.join(REPO, "framework", g("--out-dir"))), "script": a[0].split("/")[-1]})
    return jobs


def provenance(m, selection):
    done = open(f"{LOGS}/{m}/done.txt").read()
    stats = {"jobs": 0, "log_ok": 0, "eval50": 0, "sel_ok": 0}
    for j in phase_jobs(m):
        stats["jobs"] += 1
        check(f"{j['name']} exit 0" in done, f"{m} {j['name']}: no exit 0 in done.txt")
        log = open(f"{LOGS}/{m}/{j['name']}.log").read()
        hdr = f"[m64] env={j['envAB']} arm={j['arm']} N={j['n']} topology={j['topology']}"
        ok = hdr in log and f"seeds=[{j['seed']}]" in log and "Traceback" not in log
        v = j["env"].get("M102_VARIANT")
        if v and j["arm"] == "axiom2":
            ok &= f"encoder variant {v}" in log
        check(j["env"].get("M63_BACKLOG_RESET") == "1" and j["env"].get("M64_AXIOM_V2") == "1", f"{m} {j['name']}: env flags")
        ok &= "[m63] per-episode backlog reset installed" in log
        stats["log_ok"] += check(ok, f"{m} {j['name']}: log header mismatch")
        d = f"{j['out']}/{j['arm']}/seed{j['seed']}"
        e = run(d)
        good = check(e is not None and e["episodes"] == 50 and e["rollups"] == 50, f"{m} {j['name']}: eval episodes")
        if selection:
            l_ = run(d, "eval_last")
            good &= check(l_ is not None and l_["episodes"] == 50, f"{m} {j['name']}: eval_last episodes")
        stats["eval50"] += good
        if selection:
            s = json.load(open(f"{d}/selection.json"))
            sc = {int(k): v for k, v in s["val_scores"].items()}
            best = max(sc, key=lambda k: (round(sc[k], 9), k))
            ok = best == s["selected_episode"] and sorted(sc) == list(range(100, 301, 25))
            ok &= abs(s["selected_eval"] - e["reward"]) < 1e-9 and abs(s["last_eval"] - run(d, "eval_last")["reward"]) < 1e-9
            snaps = glob.glob(f"{d}/snapshots/ep*.pt")
            ok &= [os.path.basename(x) for x in snaps] == [f"ep{best}.pt"]
            for ep in (100, best):   # spot-check validation logs: 10 episodes and the stored score
                vd = locate(f"{d}/val/ep{ep}")
                vv = load(vd)
                ok &= vv["episodes"] == 10 and abs(vv["reward"] - sc[ep]) < 1e-9
            stats["sel_ok"] += check(ok, f"{m} {j['name']}: selection.json inconsistent")
    return stats


# ------------------------------------------------------------------ campaigns
def rows(root, arm, seeds, which="eval"):
    out = {}
    for s in seeds:
        r = run(f"{RES}/{root}/{arm}/seed{s}", which)
        if r:
            out[s] = r
    return out


def m102():
    sel = json.load(open(f"{RES}/m102/selection.json"))
    out = {}
    for v, t in sel["pilot"].items():
        per = {}
        for s, n in (("B_n7_ring", 7), ("A_n37_hex", 37)):
            R = rows(f"m102/{s}/{v}", "axiom2", range(2100, 2104))
            check(len(R) == 4, f"m102 {v} {s}: {len(R)} runs")
            per[s] = float(np.mean([r["reward"] / n for r in R.values()]))
            check(abs(per[s] - t["settings"][s]["reward_per_gnb"]) < 1e-9, f"m102 {v} {s} per-gNB reward")
            check(sum(r["collapsed"] for r in R.values()) == t["settings"][s]["collapsed"], f"m102 {v} {s} collapsed")
        out[v] = float(np.mean(list(per.values())))
        check(abs(out[v] - t["score"]) < 1e-9, f"m102 {v} score")
    fam = {"attention": ["gat", "gated", "concat", "gat1"], "mlp": ["mlp", "mlp_h32", "mlp_deep", "mlp_out32"]}
    for f, vs in fam.items():
        check(max(vs, key=lambda v: out[v]) == sel["selected"][f], f"m102 selection {f}")
    check(min(out[v] for v in fam["mlp"]) > max(out[v] for v in fam["attention"]), "m102: not every MLP above every attention")
    return out


def generic(m, cells, arms_pairs, seeds, whiches, labels, vmap, json_keys):
    an = json.load(open(f"{RES}/{m}/analysis.json"))
    res = {}
    for which, fam_key in zip(whiches, json_keys):
        tests = {}
        for cell in cells:
            for a, b, key_fn in arms_pairs:
                A, B = rows(f"{m}/{cell}/{a[0]}" if a[0] else f"{m}/{cell}", a[1], seeds, which), \
                    rows(f"{m}/{cell}/{b[0]}" if b[0] else f"{m}/{cell}", b[1], seeds, which)
                check(len(A) == len(seeds) and len(B) == len(seeds), f"{m} {cell} {a} {b} {which}: missing runs")
                for meas in ("reward", "compliance"):
                    tests[key_fn(cell, meas)] = pair(A, B, meas)
        family(tests, which, labels)
        theirs = an[fam_key] if fam_key else an["tests"]
        for k, v in tests.items():
            compare(v, theirs[k], f"{m} {which} {k}", vmap)
        res[which] = {k: {f: v[f] for f in v if f != "d"} for k, v in tests.items()}
    return res


def seeds_fresh():
    """Each campaign's seeds must not appear in any other campaign's result tree (pooled references are read, not rerun)."""
    camp = {"m102": range(2100, 2104), "m103": range(9980, 10000), "m104": range(9940, 9960),
            "m105": range(10000, 10010), "m106": range(10010, 10040)}
    found = {}
    for p in glob.glob(f"{RES}/**/seed*", recursive=True):
        mm = re.search(r"/seed(\d+)$", p)
        if mm and os.path.isdir(p):
            top = os.path.relpath(p, RES).split("/")[0]
            found.setdefault(int(mm.group(1)), set()).add(top)
    out = {}
    for c, ss in camp.items():
        clash = {s: sorted(found.get(s, set()) - {c}) for s in ss if found.get(s, set()) - {c}}
        out[c] = clash
        check(not clash, f"{c}: seeds also used in {clash}")
        streams = {5000 + s for s in ss} | {20000 + s for s in ss}
        hit = sorted(streams & set(found))
        out[c + "_streams_used_as_training_seeds"] = hit
        check(not hit, f"{c}: evaluation/validation streams used as training seeds elsewhere: {hit[:5]}")
    return out


def ordering():
    """Pre-registration and analysis commits must predate each campaign's launch."""
    out = {}
    spec = {"m102": ("docs/PAPER5_M102_preregistration.md", "experiments/scripts/m102_select.py"),
            "m103": ("docs/PAPER5_M102_preregistration.md", "experiments/scripts/m103_analysis.py"),
            "m104": ("docs/PAPER5_M104_preregistration.md", "experiments/scripts/m104_analysis.py"),
            "m105": ("docs/PAPER5_M105_preregistration.md", "experiments/scripts/m105_analysis.py"),
            "m106": ("docs/PAPER5_M106_preregistration.md", "experiments/scripts/m106_analysis.py")}
    for m, files in spec.items():
        launch = re.search(r"launch (\S+ \S+)", open(f"{LOGS}/{m}/done.txt").read()).group(1)
        rec = {"launch": launch}
        for f in files:
            log = subprocess.run(["git", "-C", REPO, "log", "--format=%ci|%h|%s", "--", f], capture_output=True, text=True).stdout.strip().splitlines()
            first, last = log[-1].split("|"), log[0].split("|")
            rec[f] = {"first": first[:2], "last": last[:2], "commits": len(log)}
            # commit and launch ran in one shell command (commit first), so equal timestamps to the second are expected
            check(first[0][:19] <= launch, f"{m}: {f} first committed {first[0]} after launch {launch}")
            if len(log) > 1:
                rec[f]["later_changes"] = [x.split("|")[1:] for x in log[:-1]]
        out[m] = rec
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    V3 = {"ahead": "attention ahead", "behind": "MLP ahead", "within chance": "within chance"}
    VA = {"ahead": "AXIOM ahead", "behind": "baseline ahead", "within chance": "within chance"}
    out = {"m102_scores": m102()}
    sel = json.load(open(f"{RES}/m102/selection.json"))["selected"]
    out["m103"] = generic("m103", ("B_n7_ring", "B_n7_hex", "A_n37_hex"),
                          [((sel["attention"], "axiom2"), (sel["mlp"], "axiom2"), lambda c, m: f"{c}|{m}")],
                          range(9980, 10000), ("eval",), ("ahead", "behind"), V3, (None,))
    out["m104"] = generic("m104", ("A_n37_hex", "B_n7_ring"), [(("gat", "axiom2"), ("mlp", "axiom2"), lambda c, m: f"{c}|{m}")],
                          range(9940, 9960), ("eval", "eval_last"), ("ahead", "behind"), V3, ("G1_selected", "G2_last"))
    base = lambda b: [((None, "axiom2"), (None, b), lambda c, m, b=b: f"{c}|{b}|{m}")]
    out["m105"] = generic("m105", ("A_n37_hex", "A_n19_hex", "B_n19_hex", "A_n7_hex", "B_n7_ring"),
                          base("single_agent_dqn") + base("independent_dqn"), range(10000, 10010),
                          ("eval_last", "eval"), ("ahead", "behind"), VA, ("L_last", "S_selected"))
    m106 = {}
    for cell, ss in (("B_n7_ring", range(10010, 10030)), ("A_n3", range(10010, 10040))):
        m106[cell] = ss
    # M106 has cell-specific seed ranges, so its two cells are assembled here and checked as one family of 8
    an = json.load(open(f"{RES}/m106/analysis.json"))
    for which, key in (("eval", "S_selected"), ("eval_last", "L_last")):
        tests = {}
        for cell, ss in m106.items():
            A = rows(f"m106/{cell}", "axiom2", ss, which)
            for b in ("single_agent_dqn", "independent_dqn"):
                B = rows(f"m106/{cell}", b, ss, which)
                check(len(A) == len(ss) == len(B), f"m106 {cell} {b} {which}: missing runs")
                for meas in ("reward", "compliance"):
                    tests[f"{cell}|{b}|{meas}"] = pair(A, B, meas)
        family(tests, which)
        for k, v in tests.items():
            compare(v, an[key][k], f"m106 {which} {k}", VA)
        out.setdefault("m106", {})[which] = {k: {f: v[f] for f in v if f != "d"} for k, v in tests.items()}
    out["provenance"] = {m: provenance(m, m in ("m104", "m105", "m106")) for m in ("m102", "m103", "m104", "m105", "m106")}
    out["seeds"] = seeds_fresh()
    out["ordering"] = ordering()
    perm_disagree = []
    for m in ("m103", "m104", "m105", "m106"):
        for which, t in out[m].items():
            for k, v in t.items():
                if v["verdict"] != v["perm_verdict"]:
                    perm_disagree.append([m, which, k, v["verdict"], v["perm_verdict"], v["p_holm"], v["perm_holm"]])
    out["wilcoxon_vs_permutation_disagreements"] = perm_disagree
    out["failures"] = FAIL
    json.dump(out, open(a.out, "w"), indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x))
    print("provenance:", json.dumps(out["provenance"]))
    print("ordering:", json.dumps(out["ordering"], indent=0)[:3000])
    print("seed clashes:", {k: v for k, v in out["seeds"].items() if v})
    print("Wilcoxon vs permutation verdict disagreements:", len(perm_disagree))
    for x in perm_disagree:
        print("  ", x)
    print(f"FAILURES: {len(FAIL)}")
    for f in FAIL[:60]:
        print("  ", f)


if __name__ == "__main__":
    main()
