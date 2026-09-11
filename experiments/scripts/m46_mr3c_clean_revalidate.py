#!/usr/bin/env python3
"""M46-MR3c -- clean re-run of MR3's live trust gate with the MR3b-located
fix applied (RANEnv.reset() now pushes each slice's freshly-reset ceiling
via send_control(), closing the gap where the gNB sat at its own boot
default until a slice's first admission request arrived).

MR3b also checked, using each slice's own true first-e2_apply-write
timestamp (not an arbitrary fixed cutoff) against its already-collected
2 runs: 0.00% of post-first-write M41DBG samples are uncapped, in both
runs, both slices -- no separate residual mechanism exists. The earlier
"~15-19% residual" note in MR3b's own report was itself a measurement
artifact of a steady-state cutoff (t>=30s) that was still inside the
true ~93-103s startup gap for some slices/runs -- retracted here, not
carried forward.

Reuses m46_mr3_live_revalidate.run_one() UNCHANGED (same cold-start,
same contention gate, same E4 co-located regime, same 4 checkpoints/
config) -- only OUT_DIR is redirected, per this milestone's own
"--out-dir per run" instruction. This run is the first live use of the
fixed framework/qoe_oran_framework/env.py; MR3's own already-committed
results/m46_mr3/ are untouched.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m46_mr3_live_revalidate as mr3  # noqa: E402

mr3.OUT_DIR = mr3.RIG / "experiments/results/m46_mr3c"
mr3.OUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> int:
    print(f"[m46-mr3c] === clean re-run with reset()-fix: {len(mr3.RUNS)} runs = {mr3.RUNS} === "
          f"out_dir={mr3.OUT_DIR}", file=sys.stderr)
    results = []
    for idx, (mode, train_seed, eval_seed) in enumerate(mr3.RUNS, 1):
        res = mr3.run_one(mode, train_seed, eval_seed, idx, len(mr3.RUNS))
        results.append(res)
        (mr3.OUT_DIR / "all_runs.json").write_text(json.dumps(results, indent=2))
    print(f"[m46-mr3c] === DONE, {len(results)} runs, results in {mr3.OUT_DIR} ===", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
