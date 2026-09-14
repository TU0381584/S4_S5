#!/usr/bin/env python3
"""M47-2-1 -- NO RIG. Confirms seeds 262-267 (the new seeds this
milestone trains) produce a DISTINCT arrival/offered-traffic sequence
from each other AND from the existing 256-261 pool -- a silent
seeding collision would inflate the checkpoint pool's effective n
without adding independent information, exactly the failure mode this
check exists to catch before any training time is spent.

Reuses the EXACT construction this project's own training entrypoint
uses (kpm_source_factory in m46_mr2_train_with_diagnostics.py, not a
re-derived one) so the check tests the real seeded objects, not an
approximation of them: ClosedLoopKpmSource(seed=seed, ...) (its own
np.random.RandomState(seed), independent of RANEnv's) and RANEnv's own
np.random.RandomState via reset()+_synthesize_requests(). Draws a
short, deterministic (all-accept) trajectory from each of the 12 seeds
and hashes the full per-step observation (offered ratios, backlog,
pending-request slice/gNB assignments -- everything poll() actually
returns) to detect a collision at the level that matters (the
resulting environment trajectory), not just the underlying PRNG's raw
output stream.
"""
import hashlib
import sys
from pathlib import Path

RIG = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RIG / "framework"))

from qoe_oran_framework.config import load_saclb_config  # noqa: E402
from qoe_oran_framework.env import RANEnv  # noqa: E402
from qoe_oran_framework.replay_kpm_source import ClosedLoopKpmSource  # noqa: E402

CONFIG = RIG / "experiments/configs/m46/saclb_m46_train.yaml"
MEAN_OFFERED_RATIO = {"embb": 0.5, "urllc": 0.5, "mmtc": 0.5}  # matches m46_mr2_train_with_diagnostics.py's own default
SEEDS = list(range(256, 268))  # existing 256-261 + new 262-267, checked together
N_STEPS = 20


def make_kpm_source(cfg, seed: int) -> ClosedLoopKpmSource:
    sd_for_slice = {slice_id: spec.sd for slice_id, spec in cfg.slice_by_id.items()}
    return ClosedLoopKpmSource(
        seed=seed, gnb_ids=cfg.gnb_ids, slice_ids=list(cfg.slice_by_id),
        B=cfg.B, mean_offered_ratio=MEAN_OFFERED_RATIO,
        backlog_capacity=200.0, sd_for_slice=sd_for_slice,
    )


def trajectory_fingerprint(cfg, seed: int) -> str:
    kpm = make_kpm_source(cfg, seed)
    env = RANEnv(cfg, kpm, seed=seed, reward_mode="sla")
    h = hashlib.sha256()
    env.reset()
    for _ in range(N_STEPS):
        pending = env.pending_requests()
        h.update(f"n_pending={len(pending)}".encode())
        for req in pending:
            h.update(f"{req.gnb_id}:{req.slice_id}".encode())
        cs = env.last_cluster_state
        for gnb_id, slices in sorted(cs.per_gnb.items()):
            for slice_id, agg in sorted(slices.items()):
                h.update(f"{gnb_id}:{slice_id}:{agg.prb_used_ratio:.6f}:{agg.queue_len_norm:.6f}".encode())
        actions = [1] * len(pending)  # deterministic all-accept, isolates the arrival/offered process itself
        env.step(actions)
    return h.hexdigest()


def main() -> int:
    cfg = load_saclb_config(str(CONFIG))
    fingerprints = {}
    for seed in SEEDS:
        fp = trajectory_fingerprint(cfg, seed)
        fingerprints[seed] = fp
        print(f"[seed-independence] seed={seed} fingerprint={fp}", file=sys.stderr)

    seen = {}
    collisions = []
    for seed, fp in fingerprints.items():
        if fp in seen:
            collisions.append((seed, seen[fp]))
        else:
            seen[fp] = seed

    if collisions:
        print(f"[seed-independence] COLLISION(S) FOUND: {collisions}", file=sys.stderr)
        return 1
    print(f"[seed-independence] all {len(SEEDS)} seeds produce distinct {N_STEPS}-step trajectory fingerprints -- no collisions", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
