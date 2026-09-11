#!/usr/bin/env python3
"""M46-MR3b -- locate the ORIGIN of MR3's uncapped-ceiling excursions
before choosing retrain (Path A) vs fix. MR3 found M41DBG max_prbs
reading ~106 (cell max) 31-37% of the time with real backlog pending,
despite MR1's action space being confined to {6,7,8}/{5-10} raw PRBs --
the policy cannot itself emit 106, so this is a control-path question,
not a policy-behavior one.

Reuses m46_mr3_live_revalidate.run_one() UNCHANGED (same cold-start,
same contention gate, same E4 co-located regime, same checkpoints/
config) -- only OUT_DIR is redirected here so this diagnostic writes
under its own results/m46_mr3b/ tree, per this milestone's own
"--out-dir per run" instruction, without touching MR3's own script or
its already-committed results/m46_mr3/ output.

New instrumentation (source-reading found the exact candidate
mechanism first, this run is the live confirmation the milestone
requires before trusting it): two new M46DBG log lines, gated behind
the existing M41 rate limiter (~1 sample/10-20ms) to bound volume --
(1) M46DBG e2_apply in apply_slicing_ctrl() (e2_message_handlers.c),
the E2-write side, recording the exact NR_slice_info_t*/mac* the write
landed on; (2) M46DBG sched_read in dl_sched_unit() (the REAL live
scheduler function -- gNB_scheduler_dlsch.c:1464, confirmed via
ninja's own "pf_dl defined but not used" warning that an
earlier-defined, similarly-shaped pf_dl() at line 1223 is dead code
and NOT what produces the M41DBG ceiling/postpf lines this project's
existing parsers already rely on), recording the exact pointers the
scheduler's READ resolved for the same sst/sd. If an uncapped
(min_ratio=0, max_ratio=100 -- confirmed via gnb_config.c to be this
gNB's exact boot-time default, applied before any E2 message ever
arrives) reading corresponds to a DIFFERENT sl_ptr/mac_ptr than the
matching e2_apply write, that's direct proof of a struct-instance
mismatch between the E2 write path and the scheduler's read path --
GATE MR3b classification 1 (command-application break). If pointers
always match yet values still diverge, that rules this out and points
elsewhere (not expected, given the source read, but this run is what
actually decides it, not the source read alone).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m46_mr3_live_revalidate as mr3  # noqa: E402

mr3.OUT_DIR = mr3.RIG / "experiments/results/m46_mr3b"
mr3.OUT_DIR.mkdir(parents=True, exist_ok=True)

# 2 runs, matching MR3's own first two (qoe/256, qoe/257) exactly for
# direct comparability -- same checkpoints, same eval seeds, same
# regime. sla arm not needed: MR3 already showed the uncapped pattern
# is common to both reward modes, so origin-diagnosis doesn't need to
# repeat both.
RUNS = [
    ("qoe", 256, 950),
    ("qoe", 257, 951),
]


def main() -> int:
    print(f"[m46-mr3b] === control-path-origin probe: {len(RUNS)} runs = {RUNS} === "
          f"out_dir={mr3.OUT_DIR}", file=sys.stderr)
    results = []
    for idx, (mode, train_seed, eval_seed) in enumerate(RUNS, 1):
        res = mr3.run_one(mode, train_seed, eval_seed, idx, len(RUNS))
        results.append(res)
        import json
        (mr3.OUT_DIR / "all_runs.json").write_text(json.dumps(results, indent=2))
    print(f"[m46-mr3b] === DONE, {len(results)} runs, results in {mr3.OUT_DIR} ===", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
