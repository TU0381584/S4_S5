#!/usr/bin/env python3
"""M73: run m64_run.py at N=37, the three-ring hex cluster (Env A).

The frozen framework defines the hex layout for 7 and 19 cells only. This
wrapper extends hex_cluster_coords to 37 cells with the framework's own
ring walk (_hex_ring_coords for rings 0..3), leaves 7 and 19 to the original
function, and registers the N=37 config kept in experiments/configs. The
single-agent DQN's initialisation is seeded as in m66c_seeded_single.py.
Nothing in the framework or in m64_run.py is modified. Pre-registered in
docs/PAPER5_M73_preregistration.md.

Usage (cwd = framework/): same arguments as m64_run.py, with --n 37 --env A.
  m73_run.py --check     verifies the patched layout reproduces N=7 and N=19
"""
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m64_run  # noqa: E402  (first: puts the framework on sys.path)
from qoe_oran_framework.marl import topology  # noqa: E402

N37_CONFIG = "/home/kmanojp/oranslice_rig/experiments/configs/saclb_offline_dqn_n37.yaml"
_orig_coords = topology.hex_cluster_coords


def hex_cluster_coords(n_nodes):
    if n_nodes != 37:
        return _orig_coords(n_nodes)
    coords = []
    for ring in range(4):
        coords.extend(topology._hex_ring_coords(ring))
    assert len(coords) == 37
    return coords


def install():
    topology.hex_cluster_coords = hex_cluster_coords
    m64_run.CONFIGS[37] = N37_CONFIG
    orig = m64_run.run_learned

    def seeded_run_learned(arm, cfg, factory, adj, seed, train_eps, out_dir):
        if arm == "single_agent_dqn":
            torch.manual_seed(seed)
        return orig(arm, cfg, factory, adj, seed, train_eps, out_dir)
    m64_run.run_learned = seeded_run_learned


def check():
    import numpy as np
    ref = {n: (_orig_coords(n), topology.hex_grid_edges(n)) for n in (7, 19)}
    install()
    for n, (c, e) in ref.items():
        assert hex_cluster_coords(n) == c and topology.hex_grid_edges(n) == e, n
    c37 = hex_cluster_coords(37)
    assert c37[:19] == ref[19][0] and len(set(c37)) == 37
    adj = topology.build_adjacency(37, topology.hex_grid_edges(37))
    deg = adj.sum(1) - 1
    print(f"N=7 and N=19 reproduce exactly; N=37 has {len(topology.hex_grid_edges(37))} edges, "
          f"degree min {deg.min():.0f} max {deg.max():.0f}, {int((deg == 6).sum())} interior cells")
    assert all(len(topology.hex_grid_edges(n)) == 9 * r * r + 3 * r for n, r in ((7, 1), (19, 2), (37, 3)))
    assert int((deg == 6).sum()) == 19 and np.isclose(adj, adj.T).all()


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    else:
        install()
        mp_cfg = os.environ.get("M70_MAPPO")       # same convention as m70_run.py
        if mp_cfg:
            import m64_mappo
            lr, ep, mb = mp_cfg.split(",")
            m64_mappo.LR_ACTOR, m64_mappo.EPOCHS, m64_mappo.MINIBATCH = float(lr), int(ep), int(mb)
            print(f"[m73] MAPPO actor LR {lr}, epochs {ep}, minibatch {mb}", flush=True)
        m64_run.main()
