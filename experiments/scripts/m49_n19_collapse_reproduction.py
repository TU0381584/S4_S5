#!/usr/bin/env python3
"""M49: reproduces the N=19 pooled collapse-rate estimates cited in the
rewritten manuscript's Cluster-Size Scaling section, directly from the
already-committed experiments/results/m6_pilot/ data -- no retraining.

Exact seed accounting, confirmed from docs/PAPER5_M6_topology.md Parts
8-14, not assumed: GAT-CTDE pools THREE batches (primary 900-911,
replication 1000-1002, extension 2000-2048 -- the extension batches
were run gat_ctde-only, confirmed via every m6_gatctde_collapse_rate_
extension*.sh's own --arms gat_ctde flag), 64 seeds total. single_agent_
dqn and independent_dqn have no extension data (never run past the
primary+replication 15 seeds) -- pooling only those two batches for
those two arms is not a shortcut, it is the only data that exists.

Reuses m6_correctness_metrics.py's own per_seed_metrics_per_gnb/
eval_path (the established total_blocks==0 collapse criterion) and
m2_correctness_metrics.py's own bootstrap_ci -- neither reimplemented.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from m6_correctness_metrics import per_seed_metrics_per_gnb, eval_path  # noqa: E402
from m2_correctness_metrics import bootstrap_ci  # noqa: E402

PILOT_DIR = Path(__file__).resolve().parent.parent / "results" / "m6_pilot"
TOPOS = ["fully_connected", "ring", "hex"]

# (arm, [(directory_tag, seed_list), ...])
BATCHES = {
    "gat_ctde": [
        ("n19_{topo}_capfix", list(range(900, 912))),
        ("n19_{topo}_capfix_replication", list(range(1000, 1003))),
        ("n19_{topo}_capfix", list(range(2000, 2049))),
    ],
    "independent_dqn": [
        ("n19_{topo}_capfix", list(range(900, 912))),
        ("n19_{topo}_capfix_replication", list(range(1000, 1003))),
    ],
    "single_agent_dqn": [
        ("n19_{topo}_capfix", list(range(900, 912))),
        ("n19_{topo}_capfix_replication", list(range(1000, 1003))),
    ],
}


def collapse_for_arm(arm: str) -> dict:
    """Point estimate = pooled cells collapsed / total cells (matches the
    manuscript's own '68/192 cells, 35.4%' phrasing exactly). CI = a
    seed-level BLOCK bootstrap: each of the 64 seeds contributes its OWN
    per-seed collapse RATE (collapsed cells / that seed's own cell
    count, i.e. in {0, 1/3, 2/3, 1} when a seed has all 3 topologies) as
    the resampling unit, not a binary collapsed/not-collapsed label --
    resampling whole per-seed rates (not per-cell flags) is what
    'collapse status correlates within a seed' means operationally, and
    the mean of these per-seed rates equals the pooled cell rate exactly
    when every seed has the same cell count, reproducing 35.4% as the
    point estimate. A first version of this script bootstrapped a
    binary per-seed flag (collapsed if ANY of its 3 topologies
    collapsed) instead -- caught because it gave 48.4%, not 35.4%, a
    real, disclosed mismatch (see the M49 gate report), not silently
    corrected without noting it."""
    seed_rates = []
    n_cells_collapsed, n_cells_total = 0, 0
    for tag_template, seeds in BATCHES[arm]:
        for seed in seeds:
            n_collapsed_this_seed, n_cells_this_seed = 0, 0
            for topo in TOPOS:
                combo = tag_template.format(topo=topo)
                p = eval_path(PILOT_DIR, combo, arm, seed)
                if not p.exists():
                    continue
                n_cells_this_seed += 1
                _, _, total_b = per_seed_metrics_per_gnb(str(p), 19)
                n_cells_total += 1
                if total_b == 0:
                    n_collapsed_this_seed += 1
                    n_cells_collapsed += 1
            if n_cells_this_seed == 0:
                print(f"  WARNING: {arm} seed={seed} ({tag_template}) missing all 3 topology cells",
                      file=sys.stderr)
                continue
            seed_rates.append(n_collapsed_this_seed / n_cells_this_seed)
    n = len(seed_rates)
    rate = n_cells_collapsed / n_cells_total if n_cells_total else float("nan")
    lo, hi = bootstrap_ci(seed_rates) if n else (float("nan"), float("nan"))
    return {"n_seeds": n, "rate": rate, "ci_lo": lo, "ci_hi": hi,
            "n_cells_total": n_cells_total, "n_cells_collapsed": n_cells_collapsed,
            "mean_of_seed_rates": sum(seed_rates) / n if n else float("nan")}


def main() -> None:
    for arm in ("gat_ctde", "independent_dqn", "single_agent_dqn"):
        r = collapse_for_arm(arm)
        print(f"{arm:20s} n_seeds={r['n_seeds']:2d} cells={r['n_cells_collapsed']}/{r['n_cells_total']} "
              f"rate={r['rate']:.3f} [{r['ci_lo']:.3f},{r['ci_hi']:.3f}]  "
              f"(mean of per-seed rates={r['mean_of_seed_rates']:.3f}, should equal 'rate' when balanced)")


if __name__ == "__main__":
    main()
