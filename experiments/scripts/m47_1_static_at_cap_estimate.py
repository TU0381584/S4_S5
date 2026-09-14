#!/usr/bin/env python3
"""M47-1 -- NO RIG. Estimates whether static-at-cap would reproduce
DQN-SLA's live behavior, from data already collected across MR3, MR3c,
and PF2-1a (no new live time). For every DQN-SLA run, computes what
fraction of valid (floor<=max_ratio<=cap) M41DBG ceiling samples sit
at the EXACT calibrated cap value for each controllable slice -- the
literal "is this indistinguishable from a policy that never leaves
cap" question, finer-grained than PF2-1b's own [0,1]-normalized mean
position (which can't distinguish "always near cap" from "evenly
split between floor and cap").

Writes results/m47/manifest.csv. Reads existing gnb_m41_*.log files
and already-committed all_runs.json results only.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m44e2b_ceiling_bind_check as m44e2b  # noqa: E402

RIG = Path(__file__).resolve().parent.parent.parent
FLOOR_CAP = {"urllc": (6, 8), "embb": (5, 10)}
SID = {3: "urllc", 1: "embb"}


def main() -> int:
    out_dir = RIG / "experiments/results/m47"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for era, path in [
        ("MR3", "experiments/results/m46_mr3/all_runs.json"),
        ("MR3c", "experiments/results/m46_mr3c/all_runs.json"),
        ("PF21a", "experiments/results/m45_pf21/pf21a/all_runs.json"),
    ]:
        d = json.loads((RIG / path).read_text())
        for r in d:
            if r["mode"] != "sla":
                continue
            gnb_log = RIG / f"experiments/logs/gnb_m41_{r['ts2']}.log"
            full = m44e2b.parse_m41dbg(gnb_log, 0)
            for sid, slice_name in SID.items():
                floor, cap = FLOOR_CAP[slice_name]
                ceil = sorted([row for row in full["ceiling_rows"] if row["sid"] == sid], key=lambda x: x["t"])
                valid = [row["max_ratio"] for row in ceil if floor <= row["max_ratio"] <= cap]
                at_cap = sum(1 for v in valid if v == cap)
                at_floor = sum(1 for v in valid if v == floor)
                dist = Counter(valid)
                rows.append({
                    "era": era, "train_seed": r["train_seed"], "slice": slice_name,
                    "n_valid": len(valid), "pct_at_exact_cap": round(100 * at_cap / len(valid), 2) if valid else None,
                    "n_at_floor": at_floor, "value_distribution": dict(sorted(dist.items())),
                })

    with open(out_dir / "manifest.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["era", "train_seed", "slice", "n_valid", "pct_at_exact_cap",
                                            "n_at_floor", "value_distribution"])
        w.writeheader()
        w.writerows(rows)
    for row in rows:
        print(row, file=sys.stderr)
    print(f"[m47-1] wrote {out_dir / 'manifest.csv'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
