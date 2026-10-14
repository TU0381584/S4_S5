#!/usr/bin/env python3
"""Rebuild an M4 campaign_results.json from its per-cell eval omega logs.
Needed because M62 runs the disruption campaign as parallel jobs that share
one output directory, so each job's own copy of the summary file only lists
its own cells. Usage: m62_m4_merge.py <m4_out_dir>"""
import glob, json, statistics, sys
root = sys.argv[1].rstrip("/")
results, seeds = {}, set()
for p in glob.glob(f"{root}/*/*_sev*/seed*/eval/omega_log.jsonl"):
    arm, label, seeddir = p[len(root) + 1:].split("/")[:3]
    kind, sev = label.rsplit("_sev", 1)
    seed = int(seeddir[4:])
    comp = []
    for line in open(p):
        r = json.loads(line); ev = r.get("evidence", r)
        if isinstance(ev, dict) and ev.get("rollup"):
            comp.append(ev["episode_sla_compliance_all_slices"])
    if not comp:
        continue
    seeds.add(seed)
    results[f"{arm}/{label}/{seed}"] = {"arm": arm, "kind": kind, "severity": int(sev), "seed": seed,
                                        "sla_compliance_all_slices": statistics.mean(comp), "n_episodes": len(comp)}
json.dump({"seeds": sorted(seeds), "results": results}, open(f"{root}/campaign_results.json", "w"), indent=2)
print(f"merged {len(results)} cells into {root}/campaign_results.json")
