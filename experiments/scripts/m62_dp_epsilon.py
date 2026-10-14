#!/usr/bin/env python3
"""Report the (epsilon, delta) differential-privacy bound for every M3 noise
level, from the noisy-step counts the federated runs actually recorded.

Accounting (Bun & Steinke 2016, zero-concentrated DP):
  * Mechanism per client step: the client's minibatch gradient is clipped as
    a whole to norm C and Gaussian noise of standard deviation sigma*C is
    added (marl/dp_sgd.py). Clipping is applied to the batch gradient, not
    per example, so changing any of the client's data in that step moves the
    clipped gradient by at most 2C. Sensitivity is therefore 2C, giving
    rho_step = (2C)^2 / (2 (sigma C)^2) = 2 / sigma^2.
  * Composition over the m recorded noisy steps: rho = m * rho_step.
  * Conversion: epsilon(delta) = rho + 2 sqrt(rho ln(1/delta)).
No privacy amplification by subsampling is credited: minibatches are drawn
from a growing replay buffer that reuses records, which does not meet the
assumptions of the standard amplification theorems. The bound is therefore
an upper bound, and the guarantee covers each client's whole step batch.

Usage:
    venv/bin/python3 experiments/scripts/m62_dp_epsilon.py --m3-dir experiments/results/m62_m3
"""
import argparse
import glob
import json
import math

import torch

DELTA = 1e-5


def epsilon(steps: int, sigma: float, delta: float = DELTA) -> float:
    if sigma <= 0:
        return float("inf")
    rho = steps * 2.0 / sigma ** 2
    return rho + 2.0 * math.sqrt(rho * math.log(1.0 / delta))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m3-dir", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    rows = {}
    for d in sorted(p for p in glob.glob(f"{a.m3_dir}/fl_gat_ctde_sigma*") if not p.endswith(".json")):
        sigma = float(d.rsplit("sigma", 1)[1])
        steps = []
        for ck in sorted(glob.glob(f"{d}/seed*/train/checkpoint.pt")):
            c = torch.load(ck, map_location="cpu", weights_only=False)
            steps.extend(c["dp_step_count"])
        if not steps:
            continue
        m = max(steps)
        rows[sigma] = {"noisy_steps_per_client_max": m, "noisy_steps_per_client_min": min(steps),
                       "epsilon_at_delta_1e-5": epsilon(m, sigma), "n_clients_seen": len(steps)}
        print(f"sigma={sigma:>4}: noisy steps per client={min(steps)}..{m}  epsilon(delta=1e-5)={epsilon(m, sigma):,.0f}")
    if a.out:
        json.dump(rows, open(a.out, "w"), indent=2)


if __name__ == "__main__":
    main()
