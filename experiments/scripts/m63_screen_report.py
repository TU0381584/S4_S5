#!/usr/bin/env python3
"""Score the pre-registered M63 validation screen and two-seed protocol.

Reads screen JSONs written by m63_validation_screen.py. For every
(cell, arm) group it reports: seeds, seeds failing the screen, failures
that were bad in eval (collapse, or priority-slice SLA below 0.5), passes
that were bad, mean eval priority SLA over all seeds and over passing
seeds, and the two-seed protocol (seeds paired in ascending order; deploy
the first passing seed, else the first seed).

Usage: m63_screen_report.py <screen_json>... --out <json>
"""
import argparse
import json
from collections import defaultdict

import numpy as np


def bad(r):
    return r["eval_collapsed"] or r["eval_priority_sla"] < 0.5


def summarise(rows):
    rows = sorted(rows, key=lambda r: r["seed"])
    passed = [r for r in rows if not r["fails"]]
    pairs = [(rows[i], rows[i + 1]) for i in range(0, len(rows) - 1, 2)]
    deployed = [b if a["fails"] and not b["fails"] else a for a, b in pairs]
    m = lambda v: float(np.mean(v)) if v else None
    return {
        "seeds": len(rows), "fail": sum(r["fails"] for r in rows),
        "fail_and_bad": sum(bad(r) for r in rows if r["fails"]),
        "pass_but_bad": sum(bad(r) for r in passed),
        "collapsed_all": sum(r["eval_collapsed"] for r in rows),
        "collapsed_passed": sum(r["eval_collapsed"] for r in passed),
        "prio_all": m([r["eval_priority_sla"] for r in rows]),
        "prio_passed": m([r["eval_priority_sla"] for r in passed]),
        "reward_all": m([r["eval_reward"] for r in rows]),
        "reward_passed": m([r["eval_reward"] for r in passed]),
        "pairs": len(pairs),
        "protocol_prio": m([r["eval_priority_sla"] for r in deployed]),
        "protocol_reward": m([r["eval_reward"] for r in deployed]),
        "protocol_collapsed": sum(r["eval_collapsed"] for r in deployed),
        "first_of_pair_prio": m([a["eval_priority_sla"] for a, _ in pairs]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("screens", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    groups = defaultdict(list)
    for f in a.screens:
        for r in json.load(open(f)):
            groups[(r["n"], r["cell"].rstrip("/").split("/")[-1], r["arm"])].append(r)
    out = {}
    for k in sorted(groups):
        s = summarise(groups[k])
        out["|".join(map(str, k))] = s
        fmt = lambda x: "-" if x is None else f"{x:.3f}"
        print(f"N={k[0]:2d} {k[1]:22s} {k[2]:24s} seeds={s['seeds']:2d} fail={s['fail']:2d} "
              f"(bad {s['fail_and_bad']}) pass_bad={s['pass_but_bad']} coll={s['collapsed_all']}->{s['collapsed_passed']} "
              f"prio {fmt(s['prio_all'])}->{fmt(s['prio_passed'])} protocol {fmt(s['protocol_prio'])} "
              f"(coll {s['protocol_collapsed']}/{s['pairs']})")
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
