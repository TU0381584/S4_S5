"""M102 encoder study (docs/PAPER5_M102_preregistration.md): encoder variants for AXIOM's shared encoder, each with
the M64 raw-feature skip, per-slice Q-heads and learning rate (m64_axiom2.add_skip, LR_V2), built as in
m64_axiom2.MlpAxiomV2Policy. Nothing in the framework or in m64_axiom2.py is modified.

Attention family:  gat (the current AXIOM), gated, concat, gat1.
MLP family:        mlp (the current MLP variant), mlp_h32, mlp_deep, mlp_out32.
"""
import os
import sys

import torch
import torch.nn as nn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m64_run  # noqa: E402,F401  (puts the framework on sys.path)
from m64_axiom2 import LR_V2, AxiomV2Policy, MlpAxiomV2Policy, add_skip  # noqa: E402
from m62_reviewer_experiments import PerNodeMlpEncoder  # noqa: E402
from qoe_oran_framework.marl.ctde_policy import GatCtdeMarlPolicy  # noqa: E402
from qoe_oran_framework.marl.gat_encoder import GATEncoder  # noqa: E402


def gat(d, layers=2):
    """AXIOM's encoder as GatCtdeNetwork builds it: hidden 16, output 16, 4 heads."""
    return GATEncoder(d, 16, 16, n_heads=4, n_layers=layers)


class GatedResidualEncoder(nn.Module):
    """Own-node MLP embedding plus a learned scalar gate times the GAT embedding. The gate starts at zero, so the
    encoder starts as the per-node MLP and adds neighbour information only as far as training finds it useful."""

    def __init__(self, d):
        super().__init__()
        self.local, self.graph = PerNodeMlpEncoder(d), gat(d)
        self.gate = nn.Parameter(torch.zeros(1))

    def forward(self, x, adjacency):
        return self.local(x, adjacency) + self.gate * self.graph(x, adjacency)


class ConcatEncoder(nn.Module):
    """Own-node MLP embedding and GAT embedding side by side (width 32)."""

    def __init__(self, d):
        super().__init__()
        self.local, self.graph = PerNodeMlpEncoder(d), gat(d)

    def forward(self, x, adjacency):
        return torch.cat([self.local(x, adjacency), self.graph(x, adjacency)], dim=-1)


class DeepMlpEncoder(nn.Module):
    """Per-node MLP with two hidden layers of 16, LayerNorm after each, as PerNodeMlpEncoder."""

    def __init__(self, d):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d, 16), nn.LayerNorm(16), nn.ELU(), nn.Linear(16, 16), nn.LayerNorm(16), nn.ELU(),
                                 nn.Linear(16, 16), nn.LayerNorm(16))

    def forward(self, x, adjacency):  # adjacency deliberately unused
        return self.net(x)


def _policy(factory, name):
    class P(GatCtdeMarlPolicy):
        def __init__(self, n_agents, node_feat_dim, context_dim, action_dim, adjacency, learning_rate=LR_V2, **kw):
            super().__init__(n_agents, node_feat_dim, context_dim, action_dim, adjacency, learning_rate=learning_rate, **kw)
            self.online.encoder = factory(node_feat_dim).to(self.device)
            self.target.encoder = factory(node_feat_dim).to(self.device)
            add_skip(self, node_feat_dim, context_dim, learning_rate)
    P.__name__ = f"M102_{name}"
    return P


VARIANTS = {
    "gat": AxiomV2Policy,
    "gated": _policy(GatedResidualEncoder, "gated"),
    "concat": _policy(ConcatEncoder, "concat"),
    "gat1": _policy(lambda d: gat(d, layers=1), "gat1"),
    "mlp": MlpAxiomV2Policy,
    "mlp_h32": _policy(lambda d: PerNodeMlpEncoder(d, hidden_dim=32), "mlp_h32"),
    "mlp_deep": _policy(DeepMlpEncoder, "mlp_deep"),
    "mlp_out32": _policy(lambda d: PerNodeMlpEncoder(d, out_dim=32), "mlp_out32"),
}
FAMILY = {"attention": ("gat", "gated", "concat", "gat1"), "mlp": ("mlp", "mlp_h32", "mlp_deep", "mlp_out32")}


def execution_params(policy):
    """Parameters used at execution: encoder and Q-heads (the unused mixer left from an earlier design excluded)."""
    net = policy.online
    return sum(p.numel() for p in net.encoder.parameters()) + sum(p.numel() for p in net.q_head.parameters())
