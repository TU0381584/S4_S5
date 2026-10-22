#!/usr/bin/env python3
"""M75 C: select each DQN baseline's configuration from the pilot grid and write the confirmation jobs.

Selection (docs/PAPER5_M75_preregistration.md): highest mean pilot reward per arm and size;
a tie goes to the current setting (lr 1e-3, minibatch 16). Selected configurations other
than the current one are retrained on seeds 900-926 and 1000-1002, hex layout.

Usage: m75_select.py --jobs experiments/logs/m75/jobs2.txt --out experiments/results/m75/C_selection.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import S30_19, seeds_of  # noqa: E402

LRS, BATCHES, PILOT = ("1e-4", "3e-4", "1e-3"), ("16", "64"), list(range(2000, 2005))
CURRENT = ("1e-3", "16")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    sel, jobs = {}, []
    for arm in ("single_agent_dqn", "independent_dqn"):
        for n in (19, 37):
            grid = {}
            for lr in LRS:
                for b in BATCHES:
                    d = seeds_of(f"m75/C_grid/n{n}/lr{lr}_b{b}", arm, PILOT)
                    grid[f"{lr},{b}"] = {"n": len(d), "reward": sum(r["reward"] for r in d.values()) / len(d) if d else None}
            assert all(v["n"] == 5 for v in grid.values()), (arm, n, grid)
            best = max(grid.values(), key=lambda v: v["reward"])["reward"]
            winners = [k for k, v in grid.items() if v["reward"] == best]
            pick = ",".join(CURRENT) if ",".join(CURRENT) in winners else winners[0]
            sel[f"{arm}|{n}"] = {"grid": grid, "selected": pick, "is_current": pick == ",".join(CURRENT)}
            print(f"{arm} N={n}: selected {pick} (current: {pick == ','.join(CURRENT)})", {k: round(v['reward'], 3) for k, v in grid.items()})
            if pick != ",".join(CURRENT):
                lr, b = pick.split(",")
                for s in S30_19:
                    jobs.append(f"c_{arm}_{n}_{s}|M75_LR={lr} M75_BATCH={b}|../experiments/scripts/m75_run.py --arm {arm} --env A --n {n} "
                                f"--topology hex --out-dir ../experiments/results/m75/C_confirm/n{n} --seeds {s}")
    json.dump(sel, open(a.out, "w"), indent=1)
    # slow arm first
    jobs.sort(key=lambda j: (0 if "independent" in j else 1, j))
    open(a.jobs, "w").write("\n".join(jobs) + ("\n" if jobs else ""))
    print(f"{len(jobs)} confirmation jobs written")


if __name__ == "__main__":
    main()
