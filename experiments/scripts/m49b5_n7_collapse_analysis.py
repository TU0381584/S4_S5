#!/usr/bin/env python3
"""M49b-5: honest (ClosedLoopKpmSource) N=7 collapse-rate analysis,
primary (900-911) and independent replication (1000-1011) samples.

Reuses m6_correctness_metrics.py's own established collapse criterion
(per_seed_metrics_per_gnb's total_blocks==0) and eval_path resolution
(handles both the flat gat_ctde/independent_dqn eval layout and
single_agent_dqn's own extra dqn/offline_eval/rep_0/ nesting) --
neither reimplemented. Collapse is bootstrapped over the 12 independent
seeds per sample, not the 36 (arm, topology, seed) cells, matching
M27's own convention: collapse status correlates within a seed across
its three topologies for arms that don't consume adjacency, and (this
run confirms directly) largely does even for GAT-CTDE.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from m6_correctness_metrics import per_seed_metrics_per_gnb, eval_path  # noqa: E402
from m2_correctness_metrics import bootstrap_ci  # noqa: E402

PILOT_DIR = Path(__file__).resolve().parent.parent / "results" / "m49b_5"
TOPOS = ["fully_connected", "ring", "hex"]
ARMS = ["gat_ctde", "independent_dqn", "single_agent_dqn"]
PRIMARY_SEEDS = list(range(900, 912))
REPLICATION_SEEDS = list(range(1000, 1012))


def collapse_by_seed(sample_tag: str, seeds: list[int]) -> dict:
    print(f"=== {sample_tag} (n={len(seeds)} seeds) ===")
    results = {}
    for arm in ARMS:
        seed_collapsed = []
        per_topo_counts = {t: 0 for t in TOPOS}
        for seed in seeds:
            any_collapsed, all_missing = False, True
            for topo in TOPOS:
                combo = f"n7_{topo}_{sample_tag}"
                p = eval_path(PILOT_DIR, combo, arm, seed)
                if not p.exists():
                    continue
                all_missing = False
                _, _, total_b = per_seed_metrics_per_gnb(str(p), 7)
                if total_b == 0:
                    any_collapsed = True
                    per_topo_counts[topo] += 1
            if all_missing:
                continue
            seed_collapsed.append(1 if any_collapsed else 0)
        n = len(seed_collapsed)
        n_collapsed = sum(seed_collapsed)
        rate = n_collapsed / n if n else float("nan")
        lo, hi = bootstrap_ci(seed_collapsed) if n else (float("nan"), float("nan"))
        print(f"{arm:20s} n_seeds={n:2d} collapsed={n_collapsed}/{n} rate={rate:.3f} "
              f"[{lo:.3f},{hi:.3f}]  per-topo collapsed cell counts={per_topo_counts}")
        results[arm] = {"n_collapsed": n_collapsed, "n_seeds": n, "rate": rate,
                         "ci_lo": lo, "ci_hi": hi, "per_topo": per_topo_counts}
    return results


def main() -> None:
    r_primary = collapse_by_seed("primary", PRIMARY_SEEDS)
    print()
    r_replication = collapse_by_seed("replication", REPLICATION_SEEDS)
    return r_primary, r_replication


if __name__ == "__main__":
    main()
