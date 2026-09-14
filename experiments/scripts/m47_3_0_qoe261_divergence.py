#!/usr/bin/env python3
"""M47-3-0 -- NO RIG. Characterizes qoe/seed261's live divergence
(the only QoE checkpoint of 12 that classifies correct_shed rather
than indiscriminate_failure, per M47-2-3) by comparing every offline
training signal across all 12 QoE seeds: reward/loss/epsilon/action-
range (already computed by MR2's/M47-2-1's own convergence_report.csv,
reused not re-derived) plus a new, finer-grained offline ceiling-
position (reject-intensity) analysis -- same normalized-[0,1]-within-
[floor,cap] method PF2-1b applied to LIVE data, applied here to each
seed's own 300-episode OFFLINE omega_log.jsonl -- both whole-run and
last-quartile (closest to what the frozen checkpoint converged to).

No new live time. Writes results/m47_3/manifest.csv.
"""
import csv
import json
from pathlib import Path

RIG = Path(__file__).resolve().parent.parent.parent
FLOOR_CAP = {"urllc": (6, 8), "embb": (5, 10)}
SEEDS = [256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267]


def norm_mean(vals, floor, cap):
    if not vals:
        return None
    return sum((v - floor) / (cap - floor) for v in vals) / len(vals)


def offline_ceiling_pattern(mode: str, seed: int) -> dict:
    path = RIG / f"experiments/results/m46_mr2/offline_train/{mode}/seed{seed}/dqn/offline_closed_loop/rep_0/omega_log.jsonl"
    urllc_ratios, embb_ratios = [], []
    lines = path.read_text().splitlines()
    for line in lines:
        d = json.loads(line)
        for k, v in d.get("evidence", {}).get("ceilings", {}).items():
            slice_id = k.split(":")[1]
            if slice_id == "urllc":
                urllc_ratios.append(v["max_ratio"])
            elif slice_id == "embb":
                embb_ratios.append(v["max_ratio"])
    n = len(lines)
    last_q_u = urllc_ratios[-n // 4:] if urllc_ratios else []
    last_q_e = embb_ratios[-n // 4:] if embb_ratios else []
    return {
        "urllc_reject_intensity_whole": norm_mean(urllc_ratios, *FLOOR_CAP["urllc"]),
        "urllc_reject_intensity_lastq": norm_mean(last_q_u, *FLOOR_CAP["urllc"]),
        "embb_reject_intensity_whole": norm_mean(embb_ratios, *FLOOR_CAP["embb"]),
        "embb_reject_intensity_lastq": norm_mean(last_q_e, *FLOOR_CAP["embb"]),
    }


def load_convergence_row(mode: str, seed: int) -> dict:
    for csvname in ["experiments/results/m46_mr2/convergence_report.csv",
                     "experiments/results/m47_2_1/convergence_report.csv"]:
        p = RIG / csvname
        if not p.exists():
            continue
        for row in csv.DictReader(p.open()):
            if row["reward_mode"] == mode and int(row["seed"]) == seed:
                return row
    raise FileNotFoundError(f"no convergence row for {mode}/{seed}")


def main():
    out_dir = RIG / "experiments/results/m47_3"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for seed in SEEDS:
        conv = load_convergence_row("qoe", seed)
        ceil = offline_ceiling_pattern("qoe", seed)
        rows.append({
            "seed": seed,
            "reward_improvement": conv["reward_improvement"],
            "loss_growth_pct": 100 * (float(conv["loss_Q4_mean"]) - float(conv["loss_Q1_mean"])) / float(conv["loss_Q1_mean"]),
            "final_epsilon": conv["final_epsilon"],
            "urllc_full_range": conv["urllc_full_range_exercised"],
            "embb_full_range": conv["embb_full_range_exercised"],
            **ceil,
        })

    with open(out_dir / "manifest.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        marker = " <-- diverges live (correct_shed)" if r["seed"] == 261 else ""
        print(r, marker)
    print(f"\n[m47-3-0] wrote {out_dir / 'manifest.csv'}")


if __name__ == "__main__":
    main()
