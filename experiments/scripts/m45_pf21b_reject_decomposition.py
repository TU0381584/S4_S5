#!/usr/bin/env python3
"""M45-PF2-1b -- NO RIG. Decomposes each (arm, slice)'s live behavior
into reject-intensity (admission-layer: where the commanded ceiling
sits within its calibrated [floor, cap] band, a direct proxy for how
much AdmissionGate.apply() has been rejecting vs accepting -- see
action_mapping.py: max_ratio only ever moves within [floor, cap] in
steps of step_ratio, so a mean position near floor means "mostly
rejected", near cap means "mostly accepted") and serve-through
(real, downstream delivered/offered traffic x (1-rlc_reject_frac),
already computed per run by m45_priority_weighted_correctness.py as
mean_c_urllc/mean_c_embb -- reused unmodified, not re-derived).

Uses a mechanically-grounded filter (floor<=max_ratio<=cap) rather
than a time-based cutoff to exclude the boot-default (0,100)
contamination from MR3's original runs (which predate MR3b/MR3c's
precise write-timestamp instrumentation) -- any sample outside
[floor,cap] is unambiguously not a real accept/reject decision,
confirmed by reading AdmissionGate.apply() directly (M46-MR3b/MR4).

No new live time. Reads existing gnb_m41_*.log files + already-
committed all_runs.json results from MR3, MR3c, and PF2-1a only.
Writes results/m45_pf21/pf21b/manifest.csv.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m44e2b_ceiling_bind_check as m44e2b  # noqa: E402

RIG = Path(__file__).resolve().parent.parent.parent
FLOOR_CAP = {"urllc": (6, 8), "embb": (5, 10)}
SID = {3: "urllc", 1: "embb"}


def reject_intensity(gnb_log: Path, sid: int, slice_name: str):
    full = m44e2b.parse_m41dbg(gnb_log, 0)
    ceil = sorted([row for row in full["ceiling_rows"] if row["sid"] == sid], key=lambda x: x["t"])
    floor, cap = FLOOR_CAP[slice_name]
    vals = [row["max_ratio"] for row in ceil if floor <= row["max_ratio"] <= cap]
    if not vals:
        return None, 0, len(ceil)
    norm = [(v - floor) / (cap - floor) for v in vals]
    return sum(norm) / len(norm), len(vals), len(ceil)


def main() -> int:
    out_dir = RIG / "experiments/results/m45_pf21/pf21b"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for era, path in [
        ("MR3", "experiments/results/m46_mr3/all_runs.json"),
        ("MR3c", "experiments/results/m46_mr3c/all_runs.json"),
        ("PF21a", "experiments/results/m45_pf21/pf21a/all_runs.json"),
    ]:
        d = json.loads((RIG / path).read_text())
        for r in d:
            gnb_log = RIG / f"experiments/logs/gnb_m41_{r['ts2']}.log"
            for sid, slice_name in SID.items():
                ri, n_valid, n_total = reject_intensity(gnb_log, sid, slice_name)
                serve_through = r["pwc"].get(f"mean_c_{slice_name}")
                rows.append({
                    "era": era, "mode": r["mode"], "train_seed": r["train_seed"],
                    "slice": slice_name, "reject_intensity": ri,
                    "n_valid": n_valid, "n_total": n_total, "serve_through": serve_through,
                    "shed_classification": r["pwc"].get("shedding", {}).get("window_classes", [None])[0],
                })

    with open(out_dir / "manifest.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["era", "mode", "train_seed", "slice", "reject_intensity",
                                            "n_valid", "n_total", "serve_through", "shed_classification"])
        w.writeheader()
        w.writerows(rows)
    for row in rows:
        print(row, file=sys.stderr)
    print(f"[pf21b] wrote {out_dir / 'manifest.csv'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
