#!/usr/bin/env python3
"""M45-PF2-1a -- clean embb responsiveness confirmation, LIVE, bounded.

Pre-registered (M46-MR4): embb's own commanded ceiling should
correlate NEGATIVELY with embb's own backlog (shed-under-contention,
lower priority_weight, same congestion cost as urllc, smaller return
-- see docs/PAPER5_M46_MR4_responsiveness_spec_and_reanalysis.md for
the full derivation from reward.py). MR3's own embb numbers were
diagnosed as very likely startup-excursion-contaminated (pre-dates the
MR3c fix); MR3c's clean numbers (2 seeds/arm) lean negative but aren't
powered. This block adds 3 NEW seeds/arm (258, 259, 260 -- untouched
by MR3/MR3b/MR3c, from MR2's existing 6-seed pool, no new training)
under the fully-fixed stack (MR1 config + MR3c reset-write fix), to
(a) check the negative sign holds independent of the specific seeds
MR3c happened to use, and (b) grow the sample this milestone's own
power calculation needs.

Reuses m46_mr3_live_revalidate.run_one() UNCHANGED (same cold-start,
contention gate, E4 co-located regime, MR1 config) -- only OUT_DIR and
RUNS are overridden here, per this milestone's own "--out-dir per run"
instruction. New eval seeds continue this project's own "eval seeds
start at 950" convention sequentially past MR3's 950-953.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m46_mr3_live_revalidate as mr3  # noqa: E402

mr3.OUT_DIR = mr3.RIG / "experiments/results/m45_pf21/pf21a"
mr3.OUT_DIR.mkdir(parents=True, exist_ok=True)

RUNS = [
    ("qoe", 258, 954),
    ("qoe", 259, 955),
    ("qoe", 260, 956),
    ("sla", 258, 957),
    ("sla", 259, 958),
    ("sla", 260, 959),
]


def main() -> int:
    print(f"[pf21a] === embb confirmation, 3 new seeds/arm: {len(RUNS)} runs = {RUNS} === "
          f"out_dir={mr3.OUT_DIR}", file=sys.stderr)
    results = []
    for idx, (mode, train_seed, eval_seed) in enumerate(RUNS, 1):
        res = mr3.run_one(mode, train_seed, eval_seed, idx, len(RUNS))
        results.append(res)
        (mr3.OUT_DIR / "all_runs.json").write_text(json.dumps(results, indent=2))
    print(f"[pf21a] === DONE, {len(results)} runs, results in {mr3.OUT_DIR} ===", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
