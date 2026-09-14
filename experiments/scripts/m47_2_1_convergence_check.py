#!/usr/bin/env python3
"""M47-2-1 -- reuses m46_mr2_convergence_check.py UNCHANGED (same
reward Q1/Q4, loss Q1/Q4, epsilon, and action-range-exercise checks
MR2's own 6 seeds were judged against) for the 6 NEW seeds
(262-267), only overriding SEEDS and OUT_DIR so this run writes its
own convergence_report.csv under results/m47_2_1/ rather than
overwriting MR2's own already-committed report for seeds 256-261.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m46_mr2_convergence_check as mr2check  # noqa: E402

mr2check.SEEDS = [262, 263, 264, 265, 266, 267]
mr2check.OUT_DIR = mr2check.RIG / "experiments/results/m47_2_1"
mr2check.OUT_DIR.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    raise SystemExit(mr2check.main())
