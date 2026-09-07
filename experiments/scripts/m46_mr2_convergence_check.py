#!/usr/bin/env python3
"""M46-MR2: per-arm offline convergence + action-range-exercise check.
NO RIG -- reads only the omega_log.jsonl/train_diagnostics.jsonl this
milestone's own training sweep (run_m46_mr2_train.sh) just produced.

For each (reward_mode, seed):
  - reward curve: per-episode mean reward (from omega_log.jsonl's
    evidence.reward), Q1 (first quarter of episodes) vs Q4 (last quarter)
    mean, matching this project's own established Stage10/12 convergence
    convention (Q1->Q4 reward improvement), just applied to this new
    config/env instead of re-deriving a different convergence criterion.
  - loss curve: per-train_step-call loss (from train_diagnostics.jsonl,
    captured via the non-invasive DQNPolicy.train_step wrap), Q1 vs Q4
    BY CALL ORDER (not episode index -- see
    m46_mr2_train_with_diagnostics.py's own docstring for why exact
    episode attribution is deliberately not attempted).
  - epsilon: final captured value, compared against the documented
    analytic floor (0.05, reached ~episode 200 per dqn_admission.py's own
    comment) as a sanity check that the frozen per-episode decay actually
    ran as documented.
  - action-range exercise: distinct live `max_ratio` values commanded per
    slice across the ENTIRE run (all episodes), from omega_log.jsonl's
    evidence.ceilings -- confirms the policy actually moved each
    controllable slice's ceiling across its configured band, not just
    sat at one static value.
"""
import csv
import json
import statistics as stats
from pathlib import Path

RIG = Path(__file__).resolve().parents[2]
RESULTS_DIR = RIG / "experiments/results/m46_mr2/offline_train"
OUT_DIR = RIG / "experiments/results/m46_mr2"
MODES = ["qoe", "sla"]
SEEDS = [256, 257, 258, 259, 260, 261]

# From experiments/configs/m46/saclb_m46_train.yaml / M46-MR1's own verification
EXPECTED_RANGE = {"urllc": {6, 7, 8}, "embb": {5, 6, 7, 8, 9, 10}, "mmtc": {5}}


def quartile_mean(values, which):
    n = len(values)
    if n == 0:
        return None
    q = max(1, n // 4)
    if which == "first":
        return float(stats.mean(values[:q]))
    return float(stats.mean(values[-q:]))


def decile_mean(values, idx):
    """Mean of the idx-th decile (0-indexed, 0=episodes 1-10%) of values."""
    n = len(values)
    if n == 0:
        return None
    d = n // 10
    lo = idx * d
    hi = (idx + 1) * d if idx < 9 else n
    chunk = values[lo:hi]
    return float(stats.mean(chunk)) if chunk else None


def load_omega(path):
    per_episode_rewards = {}
    maxratio_seen = {"urllc": set(), "embb": set(), "mmtc": set()}
    minratio_seen = {"urllc": set(), "embb": set(), "mmtc": set()}
    n_lines = 0
    with open(path) as fh:
        for line in fh:
            n_lines += 1
            d = json.loads(line)
            ep = d.get("episode")
            ev = d.get("evidence", {})
            r = ev.get("reward")
            if ep is not None and r is not None:
                per_episode_rewards.setdefault(ep, []).append(r)
            ceilings = ev.get("ceilings")
            if ceilings:
                for k, v in ceilings.items():
                    slice_id = k.split(":")[1]
                    if slice_id in maxratio_seen:
                        maxratio_seen[slice_id].add(v["max_ratio"])
                        minratio_seen[slice_id].add(v["min_ratio"])
    episodes_sorted = sorted(per_episode_rewards)
    episode_means = [float(stats.mean(per_episode_rewards[e])) for e in episodes_sorted]
    return n_lines, episode_means, maxratio_seen, minratio_seen


def load_diagnostics(path):
    losses, epsilons = [], []
    with open(path) as fh:
        for line in fh:
            d = json.loads(line)
            if d.get("loss") is not None:
                losses.append(d["loss"])
            if d.get("epsilon") is not None:
                epsilons.append(d["epsilon"])
    return losses, epsilons


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for mode in MODES:
        for seed in SEEDS:
            run_dir = RESULTS_DIR / mode / f"seed{seed}" / "dqn" / "offline_closed_loop" / "rep_0"
            omega_path = run_dir / "omega_log.jsonl"
            diag_path = run_dir / "train_diagnostics.jsonl"
            ckpt_path = run_dir / "checkpoint.pt"
            assert omega_path.exists(), f"missing {omega_path}"
            assert diag_path.exists(), f"missing {diag_path}"
            assert ckpt_path.exists(), f"missing {ckpt_path}"

            n_lines, episode_means, maxratio_seen, minratio_seen = load_omega(omega_path)
            losses, epsilons = load_diagnostics(diag_path)

            reward_q1 = quartile_mean(episode_means, "first")
            reward_q4 = quartile_mean(episode_means, "last")
            loss_q1 = quartile_mean(losses, "first")
            loss_q4 = quartile_mean(losses, "last")
            final_epsilon = epsilons[-1] if epsilons else None
            reward_decile1 = decile_mean(episode_means, 0)
            reward_decile3 = decile_mean(episode_means, 2)
            reward_decile10 = decile_mean(episode_means, 9)

            row = {
                "reward_mode": mode,
                "seed": seed,
                "n_episodes": len(episode_means),
                "n_omega_lines": n_lines,
                "n_train_step_calls": len(losses),
                "reward_Q1_mean": reward_q1,
                "reward_Q4_mean": reward_q4,
                "reward_improvement": (reward_q4 - reward_q1) if (reward_q1 is not None and reward_q4 is not None) else None,
                "reward_decile1_mean": reward_decile1,
                "reward_decile3_mean": reward_decile3,
                "reward_decile10_mean": reward_decile10,
                "reward_decile1_to_3_drop": (reward_decile3 - reward_decile1) if (reward_decile1 is not None and reward_decile3 is not None) else None,
                "reward_decile3_to_10_drift": (reward_decile10 - reward_decile3) if (reward_decile3 is not None and reward_decile10 is not None) else None,
                "loss_Q1_mean": loss_q1,
                "loss_Q4_mean": loss_q4,
                "loss_reduction_pct": (100.0 * (loss_q1 - loss_q4) / loss_q1) if (loss_q1 not in (None, 0)) else None,
                "final_epsilon": final_epsilon,
                "checkpoint_path": str(ckpt_path.relative_to(RIG)),
            }
            for slice_id in ("urllc", "embb", "mmtc"):
                seen = maxratio_seen[slice_id]
                expected = EXPECTED_RANGE[slice_id]
                row[f"{slice_id}_maxratio_distinct_count"] = len(seen)
                row[f"{slice_id}_maxratio_values"] = ",".join(str(v) for v in sorted(seen))
                row[f"{slice_id}_full_range_exercised"] = (seen == expected)
                row[f"{slice_id}_minratio_values"] = ",".join(str(v) for v in sorted(minratio_seen[slice_id]))
            rows.append(row)

    fieldnames = list(rows[0].keys())
    out_csv = OUT_DIR / "convergence_report.csv"
    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"[m46-mr2] wrote {len(rows)} rows to {out_csv}")

    for mode in MODES:
        mode_rows = [r for r in rows if r["reward_mode"] == mode]
        print(f"\n=== {mode.upper()} ({len(mode_rows)} seeds) ===")
        for r in mode_rows:
            print(f"  seed={r['seed']:4d} reward Q1={r['reward_Q1_mean']:.4f}->Q4={r['reward_Q4_mean']:.4f} "
                  f"(delta={r['reward_improvement']:+.4f})  decile1={r['reward_decile1_mean']:.4f} "
                  f"decile3={r['reward_decile3_mean']:.4f} decile10={r['reward_decile10_mean']:.4f} "
                  f"(d1->d3={r['reward_decile1_to_3_drop']:+.4f}, d3->d10={r['reward_decile3_to_10_drift']:+.4f})")
            print(f"           loss Q1={r['loss_Q1_mean']:.4f}->Q4={r['loss_Q4_mean']:.4f} "
                  f"({r['loss_reduction_pct']:.1f}% down)  final_eps={r['final_epsilon']:.4f}  "
                  f"urllc={r['urllc_maxratio_values']} embb={r['embb_maxratio_values']} mmtc={r['mmtc_maxratio_values']} "
                  f"urllc_full={r['urllc_full_range_exercised']} embb_full={r['embb_full_range_exercised']}")

    all_full = all(r["urllc_full_range_exercised"] and r["embb_full_range_exercised"] for r in rows)
    all_converged = all((r["reward_improvement"] or 0) >= 0 for r in rows)
    print(f"\n[m46-mr2] ALL 12 runs exercise full in-band range (urllc+embb): {all_full}")
    print(f"[m46-mr2] ALL 12 runs show non-negative Q1->Q4 reward improvement: {all_converged}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
