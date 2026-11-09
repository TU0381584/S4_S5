#!/usr/bin/env python3
"""Triple check (2026-11-10): the values each runner wrote while it ran against the values re-read from its logs.

Every runner (m64_run.py, m66c_seeded_single.py, m70_run.py, m73_run.py, ...) writes a summary JSON per batch of
seeds, <cell>/<arm>_<first>-<last>.json, holding for each seed the reward per step, the blocked requests and the
blocked mMTC requests, computed in the training process before anything is read back. The verifier and every table
read the evaluation logs instead (m66_verify.read). This script pairs the two for every stored summary in every
campaign: reward must agree to 1e-9 and both block counts exactly. A disagreement would mean a log that does not
belong to its summary, a truncated or replaced log, or a reader error.

Usage: venv/bin/python experiments/scripts/audit_runtime_vs_logs.py --out experiments/results/audit_runtime_vs_logs.json
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m66_verify import ROOT, find_eval, read  # noqa: E402

PAT = re.compile(r"^(?P<arm>.+)_(?P<a>\d+)-(?P<b>\d+)\.json$")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--skip", nargs="*", default=[])
    a = ap.parse_args()
    rows, bad, no_log, files = [], [], 0, 0
    for path in sorted(glob.glob(f"{ROOT}/**/*.json", recursive=True)):
        rel = os.path.relpath(path, ROOT)
        if any(rel.startswith(s) for s in a.skip):
            continue
        m = PAT.match(os.path.basename(path))
        if not m:
            continue
        try:
            d = json.load(open(path))
        except Exception:
            continue
        if not isinstance(d, dict) or not d or not all(k.isdigit() and isinstance(v, dict) and "reward" in v for k, v in d.items()):
            continue
        cell, arm = os.path.dirname(rel), m.group("arm")
        files += 1
        for s, v in d.items():
            p = find_eval(cell, arm, int(s))
            if p is None:
                no_log += 1
                continue
            r = read(p)
            ok_r = abs(r["reward"] - v["reward"]) <= 1e-9 * max(1.0, abs(v["reward"]))
            ok_b = ("blocks" not in v) or r["blocks"] == v["blocks"]
            ok_m = ("mmtc_blocks" not in v) or r["mmtc"] == v["mmtc_blocks"]
            row = {"cell": cell, "arm": arm, "seed": int(s), "runtime_reward": v["reward"], "log_reward": r["reward"],
                   "runtime_blocks": v.get("blocks"), "log_blocks": r["blocks"], "runtime_mmtc": v.get("mmtc_blocks"), "log_mmtc": r["mmtc"],
                   "match": bool(ok_r and ok_b and ok_m)}
            rows.append(row)
            if not row["match"]:
                bad.append(row)
    cells = sorted({(r["cell"], r["arm"]) for r in rows})
    rep = {"summary_files": files, "seed_records_compared": len(rows), "matching": len(rows) - len(bad), "mismatches": bad,
           "records_without_eval_log": no_log, "cells": len(cells), "campaigns": sorted({c.split("/")[0] for c, _ in cells})}
    json.dump(rep, open(a.out, "w"), indent=1)
    print(f"{files} runner summaries, {len(cells)} cell/arm pairs in {len(rep['campaigns'])} campaigns")
    print(f"{len(rows)} seed records compared, {len(rows) - len(bad)} match, {len(bad)} mismatch, {no_log} without an evaluation log")
    for b in bad[:20]:
        print("MISMATCH", b)


if __name__ == "__main__":
    main()
