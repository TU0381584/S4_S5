#!/usr/bin/env python3
"""M43-P1B-1: offline ceiling-trajectory replay of the submitted DQN-QoE
checkpoint across all 28 actual submitted seeds (950-977), NO RIG.

Uses live_scale_offline_env.py's make_env()/load_config() (an existing,
heavily-reused helper across this project's M1-M7 history -- NOT a new
simulator), which defaults to experiments/configs/saclb_campaign_v2.yaml
(the SAME config the real live campaign used) with ClosedLoopKpmSource at
its own default backlog_capacity=200 and the real live-observed
MEAN_OFFERED_RATIO -- chosen deliberately over the *_offline_train.yaml
variant used for the checkpoint's own TRAINING (Lmax=1000/backlog_capacity
=2000, a more forgiving regime meant to help learning), since this replay's
purpose is predicting LIVE ceiling behavior, not reproducing training
dynamics.

Seed semantics matter and are easy to get wrong: mc_runner.run_mc()'s own
internal seed arithmetic is `seed = base_seed + rep`, which does NOT match
what the real campaign actually used. run_live_eval_arm.py computes
`batch_seed = args.seed * 1000 + batch_idx` and passes THAT (not the base
seed) to saclb_xapp.py, which threads it into both RANEnv(seed=...) and
run_single(seed=...) identically (confirmed by reading saclb_xapp.py
directly). This script reproduces that exact batch_seed formula (batch_idx=0,
matching each seed's real first/only replayed batch) via a direct loop
calling run_single() itself, not run_mc()'s own (different) convenience
loop.

Does not touch qoe_oran_framework/ (frozen, only imported) or any committed
config/result. Writes to experiments/results/m43_p1b/ only.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/framework")

from live_scale_offline_env import load_config, make_env  # noqa: E402
from qoe_oran_framework.mc_runner import build_policy, run_single  # noqa: E402
from qoe_oran_framework.omega_logger import OmegaLogger  # noqa: E402

REPO_ROOT = Path("/home/kmanojp/oranslice_rig")
CKPT = REPO_ROOT / "experiments/results/offline_v2/qoe/seed256/dqn/offline_closed_loop/rep_0/checkpoint.pt"
OUT_DIR = REPO_ROOT / "experiments/results/m43_p1b"
SUBMITTED_SEEDS = list(range(950, 978))  # 950..977 inclusive, the actual 28 submitted seeds
EPISODES_PER_REP = 2  # matches the real campaign's own batch_size=2, and M43-P1's own live test

N_RB_SCHED_INIT = 106  # M41-cited empirical carrier PRB count
MIN_RBSIZE = 5


def raw_prbs(ratio_pct: int) -> int:
    return (N_RB_SCHED_INIT * ratio_pct) // 100


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=SUBMITTED_SEEDS)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()

    matrix_rows = []
    for base_seed in args.seeds:
        batch_seed = base_seed * 1000  # + batch_idx(0), matching run_live_eval_arm.py exactly
        run_id = f"m43p1b_dqn_qoe_seed{base_seed}"
        rep_dir = OUT_DIR / f"seed{base_seed}"
        rep_dir.mkdir(parents=True, exist_ok=True)
        omega_path = rep_dir / "omega_log.jsonl"

        print(f"[m43-p1b] seed={base_seed} (batch_seed={batch_seed})...", file=sys.stderr)
        env = make_env(seed=batch_seed, reward_mode="qoe")
        policy = build_policy("dqn", cfg)
        policy.load_checkpoint(str(CKPT))
        try:
            with OmegaLogger(str(omega_path)) as omega:
                run_single(
                    env, policy, "dqn", omega, EPISODES_PER_REP, batch_seed, run_id,
                    "m43_p1b_offline_replay", False, cfg,
                )
        finally:
            env.close()

        # Parse this seed's own trajectory and classify.
        per_slice_below = {"embb": 0, "urllc": 0, "mmtc": 0}
        per_slice_total = {"embb": 0, "urllc": 0, "mmtc": 0}
        sd_to_slice = {spec.sd: sid for sid, spec in cfg.slice_by_id.items()}
        with open(omega_path) as fh:
            for line in fh:
                rec = json.loads(line)
                ceilings = rec.get("evidence", {}).get("ceilings")
                if not ceilings:
                    continue
                for key, ratios in ceilings.items():
                    # key format "gnb-0:slice_id"
                    slice_id = key.split(":", 1)[1] if ":" in key else key
                    if slice_id not in per_slice_total:
                        continue
                    cap_raw = raw_prbs(ratios["max_ratio"])
                    per_slice_total[slice_id] += 1
                    if cap_raw < MIN_RBSIZE:
                        per_slice_below[slice_id] += 1

        for slice_id in ("embb", "urllc", "mmtc"):
            total = per_slice_total[slice_id]
            below = per_slice_below[slice_id]
            pct_below = (100.0 * below / total) if total else float("nan")
            if pct_below >= 80.0:
                verdict = "FLOOR-PINNED"
            elif pct_below <= 20.0:
                verdict = "CAP-RIDING"
            else:
                verdict = "MIXED"
            matrix_rows.append({
                "seed": base_seed, "batch_seed": batch_seed, "slice": slice_id,
                "steps_total": total, "steps_below_floor": below,
                "pct_steps_below_floor": round(pct_below, 1), "verdict": verdict,
            })
            print(f"[m43-p1b]   {slice_id}: {below}/{total} ({pct_below:.1f}%) below floor -> {verdict}",
                  file=sys.stderr)

    import csv
    matrix_path = OUT_DIR / "seed_trajectory_matrix.csv"
    with open(matrix_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["seed", "batch_seed", "slice", "steps_total",
                                            "steps_below_floor", "pct_steps_below_floor", "verdict"])
        w.writeheader()
        w.writerows(matrix_rows)
    print(f"[m43-p1b] wrote {len(matrix_rows)} rows to {matrix_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
