#!/usr/bin/env python3
"""Run m64_run.py with the single-agent DQN's network initialisation seeded.

The frozen framework's run_mc builds the DQN before run_single calls set_seeds,
so the first seed in each process starts from torch's per-process random
default seed. This wrapper calls torch.manual_seed(seed) immediately before
each single-agent run, which makes every seed's initialisation a function of
the seed alone. The framework itself is not modified.

Usage: same arguments as m64_run.py, with --arm single_agent_dqn.
"""
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m64_run  # noqa: E402

_orig = m64_run.run_learned


def seeded_run_learned(arm, cfg, factory, adj, seed, train_eps, out_dir):
    if arm == "single_agent_dqn":
        torch.manual_seed(seed)
    return _orig(arm, cfg, factory, adj, seed, train_eps, out_dir)


if __name__ == "__main__":
    m64_run.run_learned = seeded_run_learned
    m64_run.main()
