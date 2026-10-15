#!/usr/bin/env python3
"""M63: test a training-log-only collapse screen against known outcomes.

Screen: in the last 30 training episodes, the share of blocks that target
mMTC. A collapsed policy only blocks through epsilon-random exploration,
which spreads blocks evenly over the three slices (share near 1/3), so
the screen flags a seed when that share falls below 0.5. Only training
logs are read to decide; eval logs are read afterwards to score it.
"""
import collections, gzip, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m62_analysis import eval_log, seed_metrics

def train_share(d, last=30):
    f = [x for x in os.listdir(d) if x.startswith("omega_log")]
    if not f: return None
    p = os.path.join(d, f[0]); op = gzip.open if p.endswith(".gz") else open
    blk = collections.defaultdict(collections.Counter); eps = set()
    for line in op(p, "rt"):
        r = json.loads(line); ev = r.get("evidence", {})
        if ev.get("rollup"):
            blk[r["episode"]].update(ev.get("episode_block_by_slice", {})); eps.add(r["episode"])
    b = collections.Counter()
    for e in sorted(eps)[-last:]: b.update(blk[e])
    return b["mmtc"] / max(1, sum(b.values()))

rows = []
root = "experiments/results/m62_scaling"
for n in (7, 19):
    for topo in ("fully_connected", "ring", "hex"):
        for s in list(range(900, 912)) + [1000, 1001, 1002]:
            d = f"{root}/n{n}_{topo}/gat_ctde/seed{s}/train"
            if not os.path.isdir(d): continue
            sh = train_share(d)
            ev = seed_metrics(eval_log(f"{root}/n{n}_{topo}", "gat_ctde", s))
            rows.append((n, topo, s, sh, ev["collapsed"], 0.5 * (ev["sla"]["urllc"] + ev["sla"]["embb"])))
flag = [r for r in rows if r[3] is not None and r[3] < 0.5]
tp = sum(1 for r in flag if r[4]); fp = len(flag) - tp; fn = sum(1 for r in rows if r[4] and not (r[3] is not None and r[3] < 0.5))
print(f"cells {len(rows)}  collapsed {sum(r[4] for r in rows)}  flagged {len(flag)}  true-pos {tp}  false-pos {fp}  missed {fn}")
for r in sorted(rows, key=lambda r: r[3]):
    if r[3] < 0.6 or r[4]: print(r)
json.dump(rows, open("experiments/results/m63_pilot/collapse_screen_m62.json", "w"), indent=1)
