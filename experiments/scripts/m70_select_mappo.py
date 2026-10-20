#!/usr/bin/env python3
"""M70 R3: pick each environment's MAPPO configuration by mean pilot reward
(seeds 2000-2004), ties to the smaller training budget, and write the
phase-2 confirmation jobs. Rule fixed in docs/PAPER5_M70_preregistration.md."""
import glob, json, os, re, sys
R = "/home/kmanojp/oranslice_rig/experiments/results/m70/R3_pilot"
L = "/home/kmanojp/oranslice_rig/experiments/logs/m70"
M = "../experiments/scripts/m70_run.py"; O = "../experiments/results/m70/R3_confirm"
S30 = " ".join(str(s) for s in range(900, 930)); S15 = " ".join([str(s) for s in range(900, 912)] + ["1000", "1001", "1002"])
S30_19 = " ".join([str(s) for s in range(900, 927)] + ["1000", "1001", "1002"])
out, jobs = {}, []
for env in ("A", "B"):
    rows = []
    for d in sorted(glob.glob(f"{R}/{env}_n3/*")):
        f = glob.glob(f"{d}/mappo_2000-2004.json")
        if not f:
            continue
        res = json.load(open(f[0]))
        vals = [v["reward"] for v in res.values()]
        m = re.match(r"lr(.+)_ep(\d+)_mb(\d+)_te(\d+)", os.path.basename(d))
        rows.append({"cfg": os.path.basename(d), "lr": m.group(1), "ep": int(m.group(2)), "mb": int(m.group(3)),
                     "te": int(m.group(4)), "n": len(vals), "mean": sum(vals) / len(vals)})
    assert len(rows) == 24 and all(r["n"] == 5 for r in rows), (env, len(rows))
    best = max(rows, key=lambda r: (round(r["mean"], 9), -r["te"]))
    out[env] = {"selected": best, "grid": sorted(rows, key=lambda r: -r["mean"])}
    mp = f"M70_MAPPO={best['lr']},{best['ep']},{best['mb']}"
    te = best["te"]
    if env == "A":
        jobs.append(f"R3c_A3|{mp}|{M} --arm mappo --env A --n 3 --train-episodes {te} --out-dir {O}/A_n3 --seeds {S30}")
        for k, half in enumerate((S30_19.split()[:15], S30_19.split()[15:])):
            jobs.append(f"R3c_A19_{k}|{mp}|{M} --arm mappo --env A --n 19 --topology ring --train-episodes {te} --out-dir {O}/A_n19_ring --seeds {' '.join(half)}")
    else:
        jobs.append(f"R3c_B3|{mp}|{M} --arm mappo --env B --n 3 --train-episodes {te} --out-dir {O}/B_n3 --seeds {S30}")
        jobs.append(f"R3c_B7|{mp}|{M} --arm mappo --env B --n 7 --topology ring --train-episodes {te} --out-dir {O}/B_n7_ring --seeds {S15}")
    print(env, "selected", best)
json.dump(out, open(f"{R}/selection.json", "w"), indent=1)
open(f"{L}/jobs_phase2.txt", "w").write("\n".join(jobs) + "\n")
