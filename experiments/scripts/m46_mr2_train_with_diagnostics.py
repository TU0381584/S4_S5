#!/usr/bin/env python3
"""M46-MR2: identical to train_offline_live_scale.py (same config load,
same kpm_source_factory, same run_mc call -- not reimplemented, imported
and reused) EXCEPT it also captures the DQN training loss/epsilon curve.

oranslice_drl.drl_policy.DQNPolicy.train_step() already computes and
RETURNS {"loss", "grad_norm", "epsilon", "avg_target_q"} on every call
(drl_policy.py:203-208) -- it's just never captured by the frozen
mc_runner.run_mc()/_store_and_train() call path, so no existing pipeline
in this project logs it. Rather than edit frozen source (forbidden) or
report loss as unmeasurable, this non-invasively wraps the class method
at the Python level before training starts -- same technique M41 used to
observe send_control() without touching env.py -- and forwards the
original return value unchanged, so training behavior is byte-identical
to train_offline_live_scale.py; only an out-of-band recording happens.

Diagnostics are indexed by CALL ORDER (the order train_step() actually
fires), not by episode index -- attributing a specific call to a specific
episode would require also tracking warmup/replay-buffer timing, which
this wrapper deliberately does not attempt, to avoid introducing a new
attribution bug under time pressure. Call order alone is sufficient to
compare early-vs-late training (first quartile of calls vs last quartile
of calls), exactly mirroring this project's own established Q1-vs-Q4
reward-curve convergence convention, just indexed by call sequence
instead of episode sequence.

Usage: identical to train_offline_live_scale.py, plus writes
<results-dir>/<mode>/seed<N>/dqn/offline_closed_loop/rep_0/train_diagnostics.jsonl
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/home/kmanojp/oranslice_rig/framework")
sys.path.insert(0, "/home/kmanojp/oranslice_rig/framework/drl_slicing")

from live_scale_offline_env import MEAN_OFFERED_RATIO  # noqa: E402
from qoe_oran_framework.config import load_saclb_config  # noqa: E402
from qoe_oran_framework.mc_runner import run_mc  # noqa: E402
from qoe_oran_framework.replay_kpm_source import ClosedLoopKpmSource  # noqa: E402
from oranslice_drl.drl_policy import DQNPolicy  # noqa: E402

CONFIG_PATH = "/home/kmanojp/oranslice_rig/experiments/configs/m46/saclb_m46_train.yaml"
BACKLOG_CAPACITY = 2000.0

_DIAGNOSTICS = []
_ORIGINAL_TRAIN_STEP = DQNPolicy.train_step


def _wrapped_train_step(self, batch):
    result = _ORIGINAL_TRAIN_STEP(self, batch)
    _DIAGNOSTICS.append({
        "call_idx": len(_DIAGNOSTICS),
        "loss": result.get("loss"),
        "grad_norm": result.get("grad_norm"),
        "epsilon": result.get("epsilon"),
        "avg_target_q": result.get("avg_target_q"),
    })
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--algorithm", required=True, choices=["dqn", "a2c", "rainbow"])
    ap.add_argument("--config", default=CONFIG_PATH)
    ap.add_argument("--episodes", type=int, default=300)
    ap.add_argument("--seed", type=int, default=256)
    ap.add_argument("--results-dir", default="experiments/results/offline_v2")
    ap.add_argument("--reward-mode", choices=["sla", "qoe"], default="qoe")
    ap.add_argument("--backlog-capacity", type=float, default=BACKLOG_CAPACITY)
    args = ap.parse_args()

    assert args.algorithm == "dqn", "loss/epsilon capture is only wired for DQNPolicy.train_step"

    cfg = load_saclb_config(args.config)

    def kpm_source_factory(seed: int):
        sd_for_slice = {slice_id: spec.sd for slice_id, spec in cfg.slice_by_id.items()}
        return ClosedLoopKpmSource(
            seed=seed, gnb_ids=cfg.gnb_ids, slice_ids=list(cfg.slice_by_id),
            B=cfg.B, mean_offered_ratio=MEAN_OFFERED_RATIO,
            backlog_capacity=args.backlog_capacity, sd_for_slice=sd_for_slice,
        )

    out_dir = f"{args.results_dir}/{args.reward_mode}/seed{args.seed}"

    DQNPolicy.train_step = _wrapped_train_step
    try:
        summaries = run_mc(
            cfg, args.algorithm, kpm_source_factory, n_reps=1,
            episodes_per_rep=args.episodes, base_seed=args.seed,
            mode="offline_closed_loop", training=True,
            results_dir=out_dir, reward_mode=args.reward_mode,
        )
    finally:
        DQNPolicy.train_step = _ORIGINAL_TRAIN_STEP

    diag_path = Path(out_dir) / "dqn" / "offline_closed_loop" / "rep_0" / "train_diagnostics.jsonl"
    diag_path.parent.mkdir(parents=True, exist_ok=True)
    with open(diag_path, "w") as fh:
        for row in _DIAGNOSTICS:
            fh.write(json.dumps(row) + "\n")
    print(f"[m46-mr2] captured {len(_DIAGNOSTICS)} train_step() calls -> {diag_path}")

    for s in summaries:
        print(f"[train_with_diagnostics] {args.algorithm}/{args.reward_mode} seed={args.seed}: {s}")


if __name__ == "__main__":
    main()
