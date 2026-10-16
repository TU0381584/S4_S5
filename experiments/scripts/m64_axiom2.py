"""AXIOM v2 (M64), the single definition every runner uses.

Two changes from the M63 AXIOM, both chosen on pilot seeds of Env B before
pre-registration (docs/PAPER5_M64_preregistration.md):
  1. A raw-feature skip into the per-slice Q-heads. The encoder's per-node
     LayerNorm rescales each embedding to unit variance, which hides the
     absolute queue and congestion levels a state-dependent admission rule
     needs. Concatenating each node's raw features onto its embedding
     restores them.
  2. Learning rate 1e-3, the DQN baselines' rate, in place of 1e-4. At 1e-4
     AXIOM learned only the static mMTC-shedding rule in Env B's pilot.

install() swaps these classes into the existing campaign runners (m2, m3,
m4, m6) without editing them or the frozen framework.
"""
import torch
import torch.nn as nn

from qoe_oran_framework.marl.ctde_policy import AgentQHead, GatCtdeMarlPolicy
from qoe_oran_framework.marl.fl_ctde_policy import FederatedGatPolicy

LR_V2 = 1e-3
Q_HIDDEN = 32


class SkipEncoder(nn.Module):
    """Concatenate each node's raw features onto its normalised embedding."""

    def __init__(self, inner):
        super().__init__()
        self.inner = inner

    def forward(self, node_features, adjacency):
        return torch.cat([self.inner(node_features, adjacency), node_features], dim=-1)


def _skip_net(net, n_agents, node_dim, ctx_dim, adjacency, device):
    emb = net.encoder(torch.zeros(1, n_agents, node_dim, device=device), adjacency).shape[-1]
    net.encoder = SkipEncoder(net.encoder)
    net.q_head = AgentQHead(emb + node_dim, ctx_dim, 2, hidden_dim=Q_HIDDEN).to(device)
    return net


def add_skip(policy, node_dim, ctx_dim, lr):
    for net in (policy.online, policy.target):
        _skip_net(net, policy.n_agents, node_dim, ctx_dim, policy.adjacency, policy.device)
    policy.target.load_state_dict(policy.online.state_dict())
    policy.optimizer = torch.optim.Adam(policy.online.parameters(), lr=lr)
    return policy


class AxiomV2Policy(GatCtdeMarlPolicy):
    def __init__(self, n_agents, node_feat_dim, context_dim, action_dim, adjacency, learning_rate=LR_V2, **kw):
        super().__init__(n_agents, node_feat_dim, context_dim, action_dim, adjacency, learning_rate=learning_rate, **kw)
        add_skip(self, node_feat_dim, context_dim, learning_rate)


class MlpAxiomV2Policy(GatCtdeMarlPolicy):
    """AXIOM v2 with the graph encoder replaced by a per-node MLP (attention ablation)."""

    def __init__(self, n_agents, node_feat_dim, context_dim, action_dim, adjacency, learning_rate=LR_V2, **kw):
        from m62_reviewer_experiments import PerNodeMlpEncoder
        super().__init__(n_agents, node_feat_dim, context_dim, action_dim, adjacency, learning_rate=learning_rate, **kw)
        self.online.encoder = PerNodeMlpEncoder(node_feat_dim).to(self.device)
        self.target.encoder = PerNodeMlpEncoder(node_feat_dim).to(self.device)
        add_skip(self, node_feat_dim, context_dim, learning_rate)


class FederatedAxiomV2Policy(FederatedGatPolicy):
    def __init__(self, n_agents, node_feat_dim, context_dim, action_dim, adjacency, learning_rate=LR_V2, **kw):
        super().__init__(n_agents, node_feat_dim, context_dim, action_dim, adjacency, learning_rate=learning_rate, **kw)
        for net in self.clients + self.targets:
            _skip_net(net, n_agents, node_feat_dim, context_dim, self.adjacency, self.device)
        init_state = self.clients[0].state_dict()
        for c in self.clients[1:]:
            c.load_state_dict(init_state)
        for t, c in zip(self.targets, self.clients):
            t.load_state_dict(c.state_dict())
            t.eval()
        self.optimizers = [torch.optim.Adam(c.parameters(), lr=learning_rate) for c in self.clients]
        self.global_snapshot = {k: v.clone().detach() for k, v in init_state.items()}


def install(mlp: bool = False):
    import sys
    gat_cls = MlpAxiomV2Policy if mlp else AxiomV2Policy
    for name in ("m2_run_experiment", "m4_run_experiment", "m6_run_experiment", "m4_seed_campaign"):
        mod = sys.modules.get(name)
        if mod is not None and hasattr(mod, "GatCtdeMarlPolicy"):
            mod.GatCtdeMarlPolicy = gat_cls
    for name in ("m3_run_experiment", "m4_run_experiment", "m4_seed_campaign"):
        mod = sys.modules.get(name)
        if mod is not None and hasattr(mod, "FederatedGatPolicy"):
            mod.FederatedGatPolicy = FederatedAxiomV2Policy
    print(f"[m64] AXIOM v2 installed ({'MLP ablation' if mlp else 'GAT'} encoder, skip, LR {LR_V2})", flush=True)
